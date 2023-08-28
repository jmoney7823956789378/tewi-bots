import os
import discord
import requests

TOKEN = 'yourtokenhere'
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

PRESET_PROMPT = open("prompt.txt", "r").read().strip()
HISTORY_LENGTH = 50
URI = "http://127.0.0.1:5000/api/v1/generate"

def generate_response(prompt):
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
        'stopping_strings': ['</s>']
    }
    print(prompt)
    response = requests.post(URI, json=request)

    if response.status_code == 200:
        return response.json()['results'][0]['text'].strip()
        print(results)
    else:
        return None

@client.event
async def on_message(message):
    if message.author == client.user or not message.content.startswith('!gpt'): # change !gpt to whatever you want
        return

    history = []
    limit = HISTORY_LENGTH
    counter = 0
    async for msg in message.channel.history():
        if counter >= limit:
            break
        if msg.author != client.user and msg.content.startswith('!gpt'): # change !gpt to whatever you want
            continue
        history.append(f'{msg.author}: {msg.content}')
        counter += 1

    prompt = PRESET_PROMPT + "\n" + '\n'.join([f'> {m}' for m in reversed(history)] + [f'**{message.author}:** {message.content}']) + "\n" + "Bot: " # change Bot: to your bot's name
    response = generate_response(prompt)
    await message.channel.send(response)

client.run(TOKEN)
