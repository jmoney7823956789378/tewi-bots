import os
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack import WebClient
from slack_bolt import App
import re
import requests


SLACK_APP_TOKEN='xapp-token'
SLACK_BOT_TOKEN = "xoxb-token"
# Load character prompt at startup
CHAR_CONTENT = ""
with open("char.txt", "r") as file:
    CHAR_CONTENT = file.read().strip()

# Function to read content from "char.txt" file
def get_char_content():
    global CHAR_CONTENT
    return CHAR_CONTENT

# Custom text generation endpoint
GENERATION_ENDPOINT = "http://127.0.0.1:5000/api/v1/generate"

# Initialize Socket Mode app
app = App(token=SLACK_BOT_TOKEN)
client = WebClient(SLACK_BOT_TOKEN)

bot_name = "tewi"
latest_typing_message_ts = None

def fetch_thread_history(channel, thread_ts, limit=10):
    conversation_history = []
    cursor = None
    while True:
        response = client.conversations_replies(channel=channel, ts=thread_ts)
        messages = response.data.get('messages', [])
        conversation_history.extend([(m['text'], m['user']) for m in messages])
        if len(messages) < limit or not response.data.get('has_more'):
            break
        cursor = response.data.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break
    #print(conversation_history)
    # Convert user IDs to usernames
    users_dict = {}
    for i in range(len(conversation_history)):
        user_id = conversation_history[i][1]
        if user_id not in users_dict:
            #print(user_id)
            user_info = client.users_info(user=user_id)
            #print(user_info)
            username = user_info.data["user"]["profile"].get("real_name")
            #print(username)
            users_dict[user_id] = username

        conversation_history[i] = (conversation_history[i][0], users_dict[user_id])
    print(conversation_history)
    return conversation_history[-limit:]

# This gets activated when the bot is tagged in a channel
@app.event("app_mention")
def handle_initial_message_events(body, logger):
    global latest_typing_message_ts
    # Get username by user ID
    user_id = body["event"].get("user")
    if user_id:
        user_info = client.users_info(user=user_id)
        username = user_info.data["user"]["profile"].get("real_name")
    else:
        username = None

    # Log message
    message = str(body["event"]["text"]).split(">")[1].strip()
    # print(username, "says:", message)

    # Fetch thread history
    thread_ts = body.get("event").get("thread_ts")
    if thread_ts:
        thread_history = fetch_thread_history(body["event"]["channel"], thread_ts)
    else:
        thread_history = [(body["event"]["text"], body["event"]["user"])]

    chat_history = [f"{msg[1]}: {msg[0]}" for msg in thread_history[:9]] + [f"{username}: {message}"]
    #print(chat_history)
    # Remove leading and trailing white spaces
    chat_history = [line.strip() for line in chat_history]

    # Create prompt for custom text generation endpoint
    prompt = get_char_content() + "\n" + '\n'.join(chat_history) + f"\nTewi says:"
    print(prompt)

    # Let the user know that we are busy with the request
    response = client.chat_postMessage(
        channel=body["event"]["channel"],
        thread_ts=body["event"]["event_ts"],
        text="Tewi is thinking..."
    )
    latest_typing_message_ts = response.data['ts']

    # Call the custom text generation endpoint
    request = {
        'prompt': prompt,
        'max_new_tokens': 350,
        'auto_max_new_tokens': False,
        'preset': 'simple-1'
    }
    response = requests.post(GENERATION_ENDPOINT, json=request)

    if response.status_code == 200:
        result = response.json()['results'][0]['text']

        # Update the previous message with the generated text
        client.chat_update(
            channel=body["event"]["channel"],
            ts=latest_typing_message_ts,
            text=f"{result}",
            parse="full"
        )

# This gets activated whenever a new message is posted in any channel where the bot exists
@app.event("message")
def handle_followup_message_events(body, logger):
    # Check if the message contains the bot's name
    if not re.search(rf'\b{bot_name}\b', body["event"]["text"]):
        return

    # Get username by user ID
    user_id = body["event"].get("user")
    if user_id:
        user_info = client.users_info(user=user_id)
        username = user_info.data["user"]["profile"].get("real_name")
    else:
        username = None

    # Log message
    message = str(body["event"]["text"]).replace(f"<@{bot_name}> ", "")
    # print(username, "says:", message)

    # Fetch thread history
    thread_ts = body.get("event").get("thread_ts")
    if thread_ts:
        thread_history = fetch_thread_history(body["event"]["channel"], thread_ts)
    else:
        thread_history = [(body["event"]["text"], body["event"]["user"])]

    chat_history = [f"{msg[1]}: {msg[0]}" for msg in thread_history[:9]] + [f"{username}: {message}"]
    #print(chat_history)
    # Remove leading and trailing white spaces
    chat_history = [line.strip() for line in chat_history]

    # Create prompt for custom text generation endpoint
    prompt = get_char_content() + "\n" + '\n'.join(chat_history) + f"\nTewi says:"
    print(prompt)

    # Let the user know that we are busy with the request
    response = client.chat_postMessage(
        channel=body["event"]["channel"],
        thread_ts=body["event"]["event_ts"],
        text="Tewi is typing..."
    )
    latest_typing_message_ts = response.data['ts']

    # Call the custom text generation endpoint
    request = {
        'prompt': prompt,
        'max_new_tokens': 350,
        'auto_max_new_tokens': False,
        'preset': 'simple-1'
    }
    response = requests.post(GENERATION_ENDPOINT, json=request)

    if response.status_code == 200:
        result = response.json()['results'][0]['text']

        # Update the previous message with the generated text
        client.chat_update(
            channel=body["event"]["channel"],
            ts=latest_typing_message_ts,
            text=f"{result}",
            parse="full"
        )

if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
