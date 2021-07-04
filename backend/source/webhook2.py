import time
from flask import Flask, request
import ast
import os
import live_functions as localLib
import pickle
import re

config = localLib.loadConfig()
licenseKey = config["license"]["key"]


## Flask app to recieve webhooks

app = Flask(__name__)

def parse_webhook(webhook_data):

    """
    This function takes the string from tradingview and turns it into a python dict.
    takes in POST data from tradingview, as a string
    returns Dictionary version of string
    """

    data = ast.literal_eval(webhook_data)
    return data

@app.route('/')
def root():

    return 'online'

'''
For each folder in dumps, check the name.pickle to find Bull and Bear tables.
Append to dictionary {bull directory: folder #, bear csv directory: folder #, etc}
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
    except:
        #print("exception")
        time.sleep(0.1)

#print('name_dict:       ' + str(name_dict))

#print(name_dict)

def bullish():
    for table in name_dict:
        bear_match = re.search("Bear", table)
        bull_match = re.search("Bull", table)
        if bull_match:
            print("Table " + table + " has been found to be the Bull table")
            # run bull table
            filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
            new_state = {'state': 'run', 'executed': False}
            pickle.dump(new_state, filehand)
        if bear_match:
            print("Table " + table + " has been found to be the Bear table")
            filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
            new_state = {'state': 'stop', 'executed': False}
            pickle.dump(new_state, filehand)
    return

def bearish():
    for table in name_dict:
        bear_match = re.search("Bear", table)
        bull_match = re.search("Bull", table)
        if bull_match:
            print("Table " + table + " has been found to be the Bull table")
            # stop bull table
            filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
            new_state = {'state': 'stop', 'executed': False}
            pickle.dump(new_state, filehand)
        if bear_match:
            print("Table " + table + " has been found to be the Bear table")
            filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
            new_state = {'state': 'run', 'executed': False}
            pickle.dump(new_state, filehand)
    return

def decreasePosition_BULL():
    for table in name_dict:
        add_match = re.search("decreaseBull", table)
        if add_match:
            print("Table " + table + " has been found to be the decrease position (BULL) table")
            filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
            new_state = {'state': 'stop', 'executed': False}
            pickle.dump(new_state, filehand)
    return

def increasePosition_BULL():
    for table in name_dict:
        add_match = re.search("increaseBull", table)
        if add_match:
            print("Table " + table + " has been found to be the increase position (BULL) table")
            filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
            new_state = {'state': 'stop', 'executed': False}
            pickle.dump(new_state, filehand)
    return

def decreasePosition_BEAR():
    for table in name_dict:
        add_match = re.search("decreaseBear", table)
        if add_match:
            print("Table " + table + " has been found to be the decrease position (BEAR) table")
            filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
            new_state = {'state': 'stop', 'executed': False}
            pickle.dump(new_state, filehand)
    return

def increasePosition_BEAR():
    for table in name_dict:
        add_match = re.search("increaseBear", table)
        if add_match:
            print("Table " + table + " has been found to be the increase position (BEAR) table")
            filehand=open(f'../dumps/{name_dict[table]}/state.pickle', 'wb')
            new_state = {'state': 'stop', 'executed': False}
            pickle.dump(new_state, filehand)
    return



# webhooks          
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        if request.method == 'POST':
            data = parse_webhook(request.get_data(as_text=True))
            licenseKey = data['key']
            if licenseKey == licenseKey:
                if data['flag'] == "bull":
                    print("BULL ALERT RECIEVED")
                    print(data)
                    bullish()

                if data['flag'] == "bear":
                    print("BEAR ALERT RECIEVED")
                    print(data)
                    bearish()
                
                if data['flag'] == "decreasePosBULL":
                    print("DECREASE POSITION BULL ALERT RECIEVED")
                    print(data)
                    decreasePosition_BULL()
                                
                if data['flag'] == "increasePosBULL":
                    print("INCREASE POSITION BULL ALERT RECIEVED")
                    print(data)
                    increasePosition_BULL()
                
                if data['flag'] == "decreasePosBEAR":
                    print("DECREASE POSITION BEAR ALERT RECIEVED")
                    print(data)
                    decreasePosition_BEAR()
                                
                if data['flag'] == "increasePosBEAR":
                    print("INCREASE POSITION BEAR ALERT RECIEVED")
                    print(data)
                    increasePosition_BEAR()
                
            else:
                print("UNKNOWN ALERT RECIEVED")
                print(data)

            return 'Recieved alert', 200

        else:
            print('[X] Alert Received & Refused! (Wrong Key)')
            return 'Refused alert', 400

    except Exception as e:
        print('[X] Error:\n>', e)
        return 'Error', 400


if __name__ == '__main__':
    app.run(debug=True, port=80)      
                                






