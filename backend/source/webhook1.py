import time
from flask import Flask, request
import ast
import os
import live_functions as localLib
import pickle
import re
import logging
from adapterFactory import loadAdapter
import requests
import json
import asyncio
import websockets

config = localLib.loadConfig()
licenseKey = 'ah^~p8-/NxF%DSY'

logger = localLib.setupLogger('webhook', '../logs/webhook.log', logging.DEBUG)

person_list= {'https://7e223285801a.ngrok.io/webhook' : 'Zek'}

person_name = dict((v,k) for v,k in person_list.items())


## Flask app to recieve webhooks

app = Flask(__name__)

def parse_webhook(webhook_data):

    """
    This function takes the string from tradingview and turns it into a python dict.
    takes in POST data from tradingview, as a string
    returns Dictionary version of string
    """

    data = eval(str(webhook_data))
    return data

@app.route('/')
def root():

    return 'online'

'''
For each folder in dumps, check the name.pickle to find Bull and Bear tables.
Append to dictionary {table's directory: folder #, other table's directory: folder #, etc}
'''
name_dict = {}
for file in os.listdir('../dumps/'):
    try:
        with open(f'../dumps/{file}/state.pickle', 'rb') as handle:
            state = pickle.load(handle)
            #print(state)
        with open(f'../dumps/{file}/name.pickle', 'rb') as handle:
            name = pickle.load(handle)
            #print("file: " + file)
            name_dict[name] = file
            #logger.info("Name dict: " + str(name_dict))
    except:
        print("exception")
        time.sleep(0.1)

'''
User defines which tables they want to be activated/deactivated in their webhook.
For each table in data[activate_tables], pickle dump their states to be state:run

We also want to make sure that when we activate/deactivate tables there are no currently running positions from the opposite side.

'''

while True:
    try:
        with open('../dumps/user.pickle', 'rb') as handle:
            data = pickle.load(handle)
            user = data['id']
        break
    except(FileNotFoundError):
        print('..z.Loading')
        time.sleep(1)

adapter = loadAdapter(config, user)

def positionAdjustment():
    posInfo = adapter.fetchPosition()
    print(posInfo)
    # posInfo = ({currentSide}, {currentSide})
    if posInfo[1] == "Buy":
        adapter.closePosMarket(posInfo[0], "Sell")
    if posInfo[1] == "Sell":
        adapter.closePosMarket(posInfo[0], "Buy")
    logger.info("Closing position " + str(posInfo[0]) + " on side " + str(posInfo[1]))
    return print("Closing position " + str(posInfo[0]) + " on side " + str(posInfo[1]))

def changeLev(leverage):
    adapter.setLeverage(leverage)
    logger.info("Switching leverage to " + str(leverage))
    return print("Switching leverage to " + str(leverage))


def activate_tables(tableNames):
    print("Tables to activate: " + str(tableNames))
    for item in tableNames:
        for table in name_dict:
            table_match = re.search(item, table)
            if table_match:
                print("Table " + table + " will be activated")
                logger.info("Table " + table + " will be activated")
                filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
                new_state = {'state': 'run', 'executed': False}
                pickle.dump(new_state, filehand)

def deactivate_tables(tableNames):
    print("Tables to deactivate: " + str(tableNames))
    for item in tableNames:
        for table in name_dict:
            table_match = re.search(item, table)
            if table_match:
                print("Table " + table + " will be deactivated")
                logger.info("Table " + table + " will be deactivated")
                filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
                new_state = {'state': 'stop', 'executed': False}
                pickle.dump(new_state, filehand)
    if tableNames[0] == "ALLTABLES":
        print("ALL TABLES WILL BE DEACTIVATED")
        logger.info("ALL TABLES WILL BE DEACTIVATED")
        for table in name_dict:
            print("Table " + table + " will be deactivated")
            logger.info("Table " + table + " will be deactivated")
            filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
            new_state = {'state': 'stop', 'executed': False}
            pickle.dump(new_state, filehand)

def echoAlert():
    # Echo alerts to everyone in person_list
    for url in person_list:
        r = requests.post(url, data=json.dumps(data))
        print("Sending alert to " + str(person_name[url]) + " | " + str(url))


'''
The tradingview signal should include currentSide

{
    Buy
        {
            activate_tables : []
            deactivate_tables : []
            closePos : 
            changeLev :
            lev : 
        }
    Sell
        {

        }
    None
        {

        }
}

adapter.fetchposition() returns --> 
(0, 'None') No current position
(int, 'Buy') or (int, 'Sell')

First, fetch current position. 
If fetchPosition()[1] == data['currentSide']:, echo the signal, closePos, changeLev, deactivate/activate the tables depending on our current leverage

'''

# webhooks          
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        if request.method == 'POST':
            data = parse_webhook(request.get_data(as_text=True))
            licenseKey = data['key']
            if licenseKey == licenseKey:
                print("RECIEVED ALERT:" + str(data))
                logger.info("RECIEVED ALERT:" + str(data))
                
                # Echo the alert
                echoAlert()
                
                # Fetch current side and use the logic for that side from the webhook
                currentSide = adapter.fetchPosition()[1]
                # Fetch current leverage
                currentLeverage = adapter.fetchLeverage()
                
                print('The current side is ' + currentSide)
                logger.info('Current side is ' + str(currentSide))
                print('Current leverage is ' + str(currentLeverage))
                logger.info('Current leverage is ' + str(currentLeverage))
                
                # If we want to, close position with market sale
                if data[currentSide]['closePos'] == 'True':
                    positionAdjustment()
                # Change leverage to whatever we want (from cross to isolated etc)
                #if data[currentSide['changeLev'] == 'True':
                    #changeLev(data[currentSide]['lev'])
                
                deactivate_tables(data[currentSide]['deactivate_tables'])
                activate_tables(data[currentSide]['activate_tables'])
                
            else:
                print("UNKNOWN ALERT RECIEVED")
                logger.error("UNKNOWN ALERT RECIEVED")
                print(data)
            return 'Recieved alert', 200
        
        
        else:
            print('[X] Alert Received & Refused! (Wrong Key)')
            logger.error('[X] Alert Received & Refused! (Wrong Key)')
            return 'Refused alert', 400

    except Exception as e:
        print('[X] Error:\n>', e)
        logger.error('[X] Error:\n>', e)
        return 'Error', 400


if __name__ == '__main__':
    app.run(debug=True, port=80)
                                

# Check drawdown per signal
# 10% drawdown in price before higher highs
# on balance volume