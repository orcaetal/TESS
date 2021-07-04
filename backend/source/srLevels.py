from webhook1 import activate_tables, deactivate_tables
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



def tolerance(variable, percent):
    bump_up = variable * (1 + percent)
    bump_down = variable * (1 - percent)    
    return bump_up, bump_down

def supportResistance(currentPrice):

    '''
    Monitor currentPrice with websocket
    Each time we get some price data from the websocket, check the following:

    If currentPrice = supportLevel +- tolerance%, we hit a support level
    If currentPrice = resistenceLevel +- tolerance%, we hit a resistance level

    A breach or breakout is defined as after touching support/resistance level, currentPrice > supportLevel + 2(tolerance%)
    A touch or flip is defined as after touching support/resistance level, currentPrice < supportLevel + 2(tolerance%)
    '''

    touched_support = False
    touched_resistance = False
    tolerancePercent = config["supportResistance"]['tolerance']

    supportLevel = config['supportResistance']['support']['support_price']
    #support_tables = config['supportResistance']['support']['support_tables']
    #deactivate_support = config['supportResistance']['support']['deactivate_support']

    resistanceLevel = config['supportResistance']['support']['resistance_price']
    #resistance_tables = config['supportResistance']['support']['resistance_tables']
    #deactivate_resistance = config['supportResistance']['support']['deactivate_resistance']

    if currentPrice == tolerance(supportLevel, tolerancePercent)['bump_up'] or currentPrice == tolerance(supportLevel, tolerancePercent)['bump_down']:
        touched_support == True

    if currentPrice == tolerance(resistanceLevel, tolerancePercent)['bump_up'] or currentPrice == tolerance(resistanceLevel, tolerancePercent)['bump_down']:
        touched_resistance == True


async def srLevels():
    global closedPrice
    closedPrice = 0
    while True:
        uri = adapter.authenticate(5000)
        print("Authenticating with " + uri)
        async with websockets.connect(uri) as websocket:
            await websocket.send(adapter.subscribeAsset())
            # Subscribe asset gets kLine information
            async for messages in websocket:
                priceData = adapter.priceAction(messages)
                if priceData['confirm'] == 'True':
                    priceData['close'] = closedPrice
                    supportResistance(closedPrice)



asyncio.get_event_loop().run_until_complete(srLevels())
