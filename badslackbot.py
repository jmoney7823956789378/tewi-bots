import os
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack import WebClient
from slack_bolt import App
import requests
SLACK_APP_TOKEN='xapp-tokenstuff'
SLACK_BOT_TOKEN = "xoxb-tokenstuff"

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

def fetch_thread_history(channel, ts, limit=10): # this doesnt really work idk
    conversation_history = []
    cursor = None
    while True:
        response = client.conversations_replies(channel=channel, ts=ts, cursor=cursor)
        messages = response.data.get('messages')
        conversation_history.extend([m['text'] for m in messages])
        if len(messages) < limit or not response.data.get('has_more'):
            break
        cursor = response.data.get('response_metadata').get('next_cursor')
    return conversation_history[-limit:]

# This gets activated when the bot is tagged in a channel
@app.event("app_mention")
def handle_message_events(body, logger):
    # Get username by user ID
    user_id = body["event"].get("user")
    if user_id:
        user_info = client.users_info(user=user_id)
        username = user_info.data["user"]["real_name"]
    else:
        username = None

    # Log message
    message = str(body["event"]["text"]).split(">")[1].strip()
    # print(username, "says:", message)

    # Fetch thread history
    thread_history = fetch_thread_history(body["event"]["channel"], body["event"]["event_ts"])
    chat_history = [' '.join(msg.split(' :')[1:]).strip() for msg in thread_history[:9]] + [f"{username}: {message}"]

    # Remove leading and trailing white spaces
    chat_history = [line.strip() for line in chat_history]

    # Create prompt for custom text generation endpoint
    prompt = get_char_content() + "\n" + '\n'.join(chat_history) + f"\nBot: " # replace Bot: with your bot's name 
    print(prompt)

    # Let the user know that we are busy with the request
    response = client.chat_postMessage(
        channel=body["event"]["channel"],
        thread_ts=body["event"]["event_ts"],
        text=f"Bot is typing..." # replace Bot with your bot's name 
    )

    # Call the custom text generation endpoint
    request = {
        'prompt': prompt,
        'max_new_tokens': 450,
        'auto_max_new_tokens': False,
        'preset': 'None',
        'do_sample': True,
        'temperature': 0.99,
        'top_p': 0.99,
        'typical_p': 0.99,
        'epsilon_cutoff': 0,  # In units of 1e-4
        'eta_cutoff': 0,  # In units of 1e-4
        'tfs': 1,
        'top_a': 0,
        'repetition_penalty': 1.11,
        'repetition_penalty_range': 0,
        'top_k': 40,
        'min_length': 0,
        'no_repeat_ngram_size': 0,
        'num_beams': 1,
        'penalty_alpha': 0,
        'length_penalty': 1,
        'early_stopping': False,
        'mirostat_mode': 0,
        'mirostat_tau': 5,
        'mirostat_eta': 0.1,
        'seed': -1,
        'add_bos_token': True,
        'truncation_length': 4096,
        'ban_eos_token': False,
        'skip_special_tokens': True,
        'stopping_strings': []
    }
    response = requests.post(GENERATION_ENDPOINT, json=request)

    if response.status_code == 200:
        result = response.json()['results'][0]['text']
        #print(result)

        # Reply to thread with the generated text
        response = client.chat_postMessage(
            channel=body["event"]["channel"],
            thread_ts=body["event"]["event_ts"],
            text=f"{result}"
        )

if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
