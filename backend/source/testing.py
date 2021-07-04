import requests
import json
import live_functions as localLib
import websockets
import time
import asyncio
import pickle
from adapterFactory import loadAdapter

config = localLib.loadConfig()

while True:
    try:
        with open('../dumps/user.pickle', 'rb') as handle:
            data = pickle.load(handle)
            user = data['id']
        break
    except(FileNotFoundError):
        print('...Loading')
        time.sleep(1)

adapter = loadAdapter(config, user)

webhook_url = 'http://127.0.0.1:80/webhook'

data = {
    'Buy': {
        'activate_tables' : ['NONE'], 'deactivate_tables': ['NONE'], 'closePos': 'True'
    },
    'Sell' :
    {
        'activate_tables' : ['NONE'], 'deactivate_tables': ['NONE'], 'closePos': 'True'
    },
    'None' :
    {
        'activate_tables' : ['NONE'], 'deactivate_tables': ['NONE'], 'closePos': 'True'
    },

    'key' : 'ah^~p8-/NxF%DSY'
}

# async def query():
#     uri = adapter.authenticate(5000)
#     print(uri)
#     async with websockets.connect(uri) as websocket:
#         await websocket.send(adapter.subscribePosition())
#         async for messages in websocket:
#             position = adapter.positionData(messages)
#             print(position)

# asyncio.get_event_loop().run_until_complete(query())
print("sending webhook. .")
r = requests.post(webhook_url, data=json.dumps(data))

