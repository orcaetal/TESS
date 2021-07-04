from flask import Flask, request
import ast
import requests
import json



'''
Recieves webhooks from tradingview
Have a list of people to echo to
For each person in list of webhook URLs, send a post request of the message from tradingview 
'''


person_list= {'http://e9a405fc9405.ngrok.io/' : 'Zek', 'http://2d9c66740d5d.ngrok.io': 'Chloe'}

person_name = dict((v,k) for v,k in person_list.items())


## Flask app to recieve webhooks from tradingview

app = Flask(__name__)

def parse_webhook(webhook_data):

    """
    This function takes the string from tradingview and turns it into a python dict.
    takes in POST data from tradingview, as a string
    returns Dictionary version of string
    """

    data = ast.literal_eval(str(webhook_data))
    return data

@app.route('/')
def root():

    return 'online'

# webhooks          
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        if request.method == 'POST':
            data = parse_webhook(request.get_data(as_text=True))
            print("Recieved alert : " + str(data))
            
            for url in person_list:
                r = requests.post(url, data=json.dumps(data))
                print("Sending alert to " + str(person_name[url]) + " | " + str(url))
            return 'Recieved alert', 200
        
        else:
            print('[X] Alert Received & Refused')
            return 'Refused alert', 400

    except Exception as e:
        print('[X] Error:\n>', e)
        return 'Error', 400


if __name__ == '__main__':
    app.run(debug=True, port=80)   