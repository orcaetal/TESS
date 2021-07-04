
from webhook1 import activate_tables, deactivate_tables
from adapterFactory import loadAdapter
import live_functions as localLib
import asyncio
import websockets
import logging
import pickle
import contextvars

config = localLib.loadConfig()
licenseKey = config["license"]["key"]

while True:
    try:
        with open('../dumps/user.pickle', 'rb') as handle:
            data = pickle.load(handle)
            user = data['id']
        break
    except(FileNotFoundError):
        print('...Loading')
        time.sleep(1)

logger = localLib.setupLogger('leverageManager', '../logs/leverageManager.log', logging.DEBUG)
adapter = loadAdapter(config, user)

'''
This websocket sends a message every time a new position is added
We use this to asynchronously check the leverage and side from there to ensure we are not overleveraged
'''
global authenticated
authenticated = False
global counter
counter = 0
global websocket


async def authenticate():
    global authenticated
    global counter
    global websocket
    uri = adapter.authenticate(5000)
    print("Authenticating websocket...")
    async with websockets.connect(uri) as websocket:
        await websocket.send(adapter.subscribePosition())
        print("Authenticated.")
        authenticated = True
        counter += 1
        print(counter)
        print(authenticated)
        return websocket

async def positionUpdate(metric):
    global websocket
    if authenticated == False:
        websocket = await authenticate()
    elif authenticated == True:
        #print(authenticated)
        async for messages in websocket:
            print(messages)
            positionUpdate = adapter.positionData(messages)
            if positionUpdate is not None:
                print('Position update: current side is now ' + positionUpdate[0]['side'])
                return positionUpdate[0][metric]

'''
We monitor our current leverage to see if we get above a certain maximumLeverage amount.
If it goes above a certain amount, depending on our current side, we activate the aggressive tables.

maximumLeverage and aggressive tables are hardcoded and not be able to be changed by the webhook.
They are values definied in config.json
'''


async def leverageManager():
    print(counter)
    maximumLeverage = config['maximumLeverage']
    aggressive_tablesLONG = config['aggressive_tablesLONG']
    aggressive_tablesSHORT = config['aggressive_tablesSHORT']
    while True:
        checkSide = await positionUpdate('side')
        triggered = 0
        if checkSide != None and authenticated == True:
            # This is a get request so we need to wait
            currentLeverage = adapter.fetchLeverage()
            currentSide = adapter.fetchPosition()[1]
            time.sleep(100)

            # When our leverage from our open position is greater than our definied maximum leverage,
            # activate tables in the opposite side to deleverage us
            if currentLeverage.floor() >= maximumLeverage:
                if currentSide == 'Buy':
                    activate_tables(aggressive_tablesSHORT)
                if currentSide == 'Sell':
                    activate_tables(aggressive_tablesLONG)
                triggered = 1
            # After we have deleveraged our positions from the opposite side aggressive table,
            # deactivate those aggressive tables
            if currentLeverage.floor() <= maximumLeverage and triggered != 0:
                if currentSide == 'Buy':
                    deactivate_tables(aggressive_tablesSHORT)
                if currentSide == 'Sell':
                    deactivate_tables(aggressive_tablesLONG)
                triggered = 0



asyncio.get_event_loop().run_until_complete(leverageManager())