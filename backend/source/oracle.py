#! usr/env/bin python
import live_functions as localLib
#import srLevels
import socketio
import sys
import time
import eventlet
import threading
from bot import Bot
import logging
import glob
import pickle
import os
import shutil
import pandas as pd
from dataframes import getFolders
import traceback
import requests
import http
import json
import websockets
from websocket import create_connection
from adapterFactory import loadAdapter
import asyncio
import re


##check system time vs bybit server
localTime = int(time.time())       
connection = http.client.HTTPSConnection("api.bybit.com", 443, timeout=10)
connection.request('GET','/v2/public/time',headers={'Host': 'api.bybit.com','Content-Type': 'application/x-www-form-urlencoded'})
response = connection.getresponse()
resDict = json.loads(response.read())
connection.close()
servTime = float(resDict['time_now'])
if abs(servTime - localTime) > 5:
	print('\nTIME SYNC ERROR: Please sync your machine time before starting')
	exit()


## Global variables
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
config = localLib.loadConfig()
#user_id=0 #wont know until authenticated
adapter='None' #wont know until auth


# Leverage manager variables
useLM = config['leverageManager']['useLM']
if useLM == 'True':
	maximumLeverage = config['leverageManager']['maximumLeverage']
	aggressive_tablesSHORT = config['leverageManager']['aggressive_tablesSHORT']
	aggressive_tablesLONG = config['leverageManager']['aggressive_tablesLONG']
	delevTriggered = 0

# SR variables
currentCandle = 'None'
useSR = config['supportResistance']['useSR']
if useSR == 'True':
	
	supportLevel = config['supportResistance']['support']['support_price']
	support_breakout = config['supportResistance']['support']['support_breakout']
	support_flip = config['supportResistance']['support']['support_flip']
	
	resistanceLevel = config['supportResistance']['resistance']['resistance_price']
	resistance_breakout = config['supportResistance']['resistance']['resistance_breakout']
	resistance_flip = config['supportResistance']['resistance']['resistance_flip']
	
	supportTrigger =  supportLevel + ((resistanceLevel - supportLevel)*0.15)
	resistanceTrigger = resistanceLevel - ((resistanceLevel - supportLevel)*0.15)
	
	supportCrossed = False
	resistanceCrossed = False

# misc config globals
email = config['license']['email']
licenseKey = config['license']['key']

uuid = (sys.argv[1])
runningThreads = []
botDict = {}
states = {}
instance = localLib.randomString()
allAgentNames = []
globalStarter = False
botNumber = 1
 
try:
	if not os.path.exists('../dumps'):
		os.makedirs('../dumps')
	else:
		shutil.rmtree('../dumps')
		os.makedirs('../dumps')
	
	if not os.path.exists('../logs'):
		os.makedirs('../logs')
	else:
		shutil.rmtree('../logs')
		os.makedirs('../logs')
except PermissionError:
	print('\nWARNING:\nCannot access files because they are open in another program.\n Close all logs\ or dumps\ files and try again')
	time.sleep(30)
	exit()
	
with open('../dumps/instance.pickle', 'wb+') as handle:
	pickle.dump(instance, handle)

## Logging config
logger = localLib.setupLogger('oracle', '../logs/oracle.log', logging.DEBUG)
socketioLogger = localLib.setupLogger('socketio', '../logs/socketio.log')


# -----------------------------------------------------------------------------------------------------
# Setup GATS websocket client for authentication and metric gathering
def configureGatsClient():
	gatsSocket = socketio.Client()
	connInfo = 'email=' + email + '&license=' + licenseKey + '&uuid=' + uuid

	@gatsSocket.event
	def connect():
		logger.info('Successfully connected to Genesis Algo Trade Servers!')
		
		global globalStarter
		if globalStarter == False:
			gatsSocket.emit('authenticate')
			localLib.coolASCII()
			
	@gatsSocket.event
	def connect_error(data):
		logger.error('Failed to connect to Genesis Algo Trade Servers!')
		logger.debug(data)
		logger.info("Exiting in 30 seconds...")
		time.sleep(30)

	@gatsSocket.event
	def authenticated(response):
		global adapter
		logger.info('Successfully authenticated! Starting bot scripts...')
		thisFolder = os.path.dirname(os.path.abspath(__file__))
		logFolder = os.path.abspath('../logs')
		dumpsFolder = os.path.abspath('../dumps')
		
		#init tradelog
		df = pd.DataFrame(
			columns=['Agent', 'Amount', 'Side', 'OST', 'CBT', 'OSP', 'CBP', 'RPNL', 'Fitness', 'Instance'])
		df.to_csv('../dumps/tradelog.csv', index=False)

		user_id = response['data']['id']
		adapter = loadAdapter(config, user_id)
		prevOpen = adapter.fetchPrice()
		
		#if not disconnect
		global runningThreads
		
		if len(runningThreads) == 0:
			with open('../dumps/user.pickle', 'wb+') as handle:
				pickle.dump(response['data'], handle)
			with open(f'../dumps/buttons.pickle', 'wb+') as handle:
				pickle.dump(None, handle)

		
		while True:
			try:
				#global runningThreads
				global botDict
				global states
				global botNumber
				global globalStarter
				global delevTriggered
				threads = glob.glob(os.path.abspath(os.path.join(os.getcwd(), os.pardir))+'\\active-tables\\*.csv')
				
				
				#execute once on first startup (init all bots and botdict)
				if botNumber == 1:
					for offsetTable in threads:
						if offsetTable not in runningThreads:
							bot = Bot(uuid, gatsSocket, offsetTable, botNumber, instance, user_id)
							for agentNames in bot.offsetTable:
								if agentNames['entry_id'] not in allAgentNames:
									allAgentNames.append(agentNames['entry_id'])
								else:
									print('FATAL ERROR: duplicate agent name ', agentNames['entry_id'])
									time.sleep(20)
									exit()
							botDict[offsetTable] = [botNumber, bot, False]
							runningThreads.append(offsetTable) 
							print('Added bot', str(botNumber)+'/'+str(len(threads)), offsetTable.split('\\')[-1])
							botNumber += 1
					print('\nAll bots are ready to go!\n')
				
				# Activates or deactivates bots given list of table names
				def handle_tables(tableList, action):
					if tableList == 'NONE':
						print('No tables will be handled')
						return
					if tableList == 'ALLTABLES':
						print('All tables will be handled')
						# Iterate through each table in currently running
						for matchTables in threads:
							botNom = botDict[matchTables][0]
							if action == 'run':
								print('Activating tables ' + matchTables.split('\\')[-1])
							else:
								print('Deactivating tables ' + matchTables.split('\\')[-1])
							while True:
								try:
									with open(f'../dumps/{botNom}/state.pickle', 'wb+') as handle:
										pickle.dump({'state':action,'executed':True}, handle)
									break
								except:
									time.sleep(0.1)

					# For each table in the bots currently running,
					else:
						print('Handling tables ' , action, tableList)
						for matchTables in threads:
						# If its in our defined tableList,
							if matchTables.split('\\')[-1].rstrip('.csv') in tableList:
								# Retieve its respective number
								botNom = botDict[matchTables][0]
								if action == 'run':
									print('Activating table ' + matchTables)
								else:
									print('Deactivating table ' + matchTables)
								# Update the pickle file
								while True:
									try:
										with open(f'../dumps/{botNom}/state.pickle', 'wb+') as handle:
											pickle.dump({'state':action,'executed':True}, handle)
										break
									except FileNotFoundError:
										print("Handled table does not exist")
										time.sleep(0.1)
										break
									except:
										time.sleep(0.1)
				
				# Support and resistance
				
				global supportCrossed
				global resistanceCrossed
				# If enabled in config,
				if useSR == "True":
					currentCandle = adapter.fetchCandle()
					if currentCandle is not None:
						
						#check for end of minute missed crosses
						if float(currentCandle['open']) != prevOpen:
							if prevOpen < resistanceTrigger and float(currentCandle['open']) > resistanceTrigger and resistanceCrossed == False:
								resistanceCrossed = True
								handle_tables(resistance_flip, 'run')
								print('resistance triggered')
							if prevOpen > supportTrigger and float(currentCandle['open']) < supportTrigger and supportCrossed == False:
								supportCrossed = True
								handle_tables(support_flip, 'run')
								print('support triggered')
							prevOpen = float(currentCandle['open'])
							
						#check for normal crosses
						if float(currentCandle['open']) < resistanceTrigger and float(currentCandle['high']) > resistanceTrigger and resistanceCrossed == False:
							resistanceCrossed = True
							handle_tables(resistance_flip, 'run')
							print('resistance triggered')
						if float(currentCandle['open']) > supportTrigger and float(currentCandle['low']) < supportTrigger and supportCrossed == False:
							supportCrossed = True
							handle_tables(support_flip, 'run')
							print('support triggered')
							
				
				# leverage manager
				if useLM == "True":
					posInfo = adapter.fetchLeverage()
					currentLev = posInfo[0]
					currentSide = posInfo[1]
						
					##if leverage exceeds maximum
					if int(currentLev) >= maximumLeverage and delevTriggered == 0:
						if currentSide == 'Buy':
							print("Now deleveraging...")
							# Run aggressive short table to deleverage overexposed long position
							handle_tables(aggressive_tablesSHORT, 'run')
									
						if currentSide == 'Sell':
							print("Now deleveraging...")
							# Run aggressive long table to deleverage overexposed short position
							handle_tables(aggressive_tablesLONG, 'run')
						delevTriggered = 1
						
					# After we have deleveraged our positions from the opposite side aggressive table,
					# deactivate those aggressive tables
					if int(currentLev) < maximumLeverage and delevTriggered != 0:
						if currentSide == 'Buy':
							print("Deleveraging complete...")
							handle_tables(aggressive_tablesSHORT, 'stop')
						if currentSide == 'Sell':
							print("Deleveraging complete...")
							handle_tables(aggressive_tablesLONG, 'stop')
						delevTriggered = 0
					
					
				#load states
				bots = getFolders(dumpsFolder, numbers=True)
				for bot in bots[1:]:
					while True:
						try:
							with open(f'../dumps/{bot}/state.pickle', 'rb') as handle:
								states[int(bot)] = pickle.load(handle)
							break
						except:
							time.sleep(0.1)

				# check for stopped bots 
				for oldTable in threads:
					if oldTable in runningThreads:
						botNo = botDict[oldTable][0]
						if states[botNo]['state'] == 'stop' and botDict[oldTable][2]:
							print(oldTable.split('\\')[-1], 'cancelling opens and stopping bot')
							botDict[oldTable][1].stop()
							botDict[oldTable][2] = False
							time.sleep(1)
							print(f'Bot {oldTable} has been shut down.')
							states[botNo]['executed'] = True
							
							#shuffle primary responsibilities
							foundNew = False
							for secondaryTable in runningThreads:
								if botDict[secondaryTable][1].running and foundNew == False:
									botDict[secondaryTable][1].makePrimary()
									foundNew = True
									
										
								
				
				if len(runningThreads) <= 10:
					
					#
					# check for tables removed dragon drop
					for oldTable in runningThreads:
						if oldTable not in threads and botDict[oldTable][2]:
							print('file remove detected', oldTable.split('\\')[-1], 'cancelling opens and stopping bot')
							botDict[oldTable][1].stop()
							botDict[oldTable][2] = False

					
					for offsetTable in threads:
						# check for tables added dragon drop (init bot and adjust botdict)
						if offsetTable not in runningThreads:
							runningThreads.append(offsetTable)
							bot = Bot(uuid, gatsSocket, offsetTable, botNumber, instance, user_id)
							for agentNames in bot.offsetTable:
								if agentNames['entry_id'] not in allAgentNames:
									allAgentNames.append(agentNames['entry_id'])
								else:
									print('\nWARNING\nduplicate agent name: ', agentNames['entry_id'])
									print('Do not start this table')
							bot.globalStart(globalStarter)
							botDict[offsetTable] = [botNumber, bot, False]
							print('Added bot', botNumber, offsetTable.split('\\')[-1])
							states[botNumber] = {}
							states[botNumber]['state'] = "stop"  # hier
							botNumber += 1
						
						# check tables that were already initialized (start and resume)
						if offsetTable in botDict:
							botNo = botDict[offsetTable][0]
							if states[botNo]['state'] == 'run' and not botDict[offsetTable][2]:
								botDict[offsetTable][2] = True
								# resume paused bot
								if botDict[offsetTable][1].paused:
									
									#assign new primary if necessary
									primaryExists = False
									for otherTable in botDict:
										if botDict[otherTable][1].primary:
											primaryExists = True
									if not primaryExists:
										botDict[offsetTable][1].makePrimary()
										
									botDict[offsetTable][1].resume()
									print('resuming bot', botDict[offsetTable][0], offsetTable.split('\\')[-1])
								
								#start bot for first time
								else:
									#assign new primary if necessary
									primaryExists = False
									for otherTable in botDict:
										if botDict[otherTable][1].primary:
											primaryExists = True
									if not primaryExists:
										botDict[offsetTable][1].makePrimary()
									botDict[offsetTable][1].start()
									print('starting bot', botDict[offsetTable][0], offsetTable.split('\\')[-1])
										
									#tell all bots we have started
									if globalStarter == False:
										for offsetTable2 in botDict:
											globalStarter = True
											botDict[offsetTable2][1].globalStart(globalStarter)
								
								time.sleep(1)
								

							   
							states[botNo]['executed'] = True

					for bot in bots[1:]:
						while True:
							try:
								with open(f'../dumps/{bot}/state.pickle', 'wb+') as handle:
									pickle.dump(states[int(bot)], handle)
								break
							except:
								print('err')
								time.sleep(0.1)

				else:
					print('WARNING: too many bots. LIMIT is 10')
					logger.error('WARNING: too many bots. LIMIT is 10')
					

				time.sleep(5)

			except SystemExit:
				sys.exit()
			except Exception as e:
				print(e, "from auth")
				traceback.print_exc()
				time.sleep(1)

	@gatsSocket.event
	def disconnect_with_message(message):
		logger.warning(message)
		gatsSocket.emit('force_disconnect')
		logger.info("Exiting in 30 seconds...")
		time.sleep(30)

	try:
		gatsSocket.email = email
		gatsSocket.connect('http://188.166.30.177:5430?' + connInfo)

	except Exception as ex:
		print(ex, "oracle sio")
		logger.error(ex)
		logger.info("Exiting in 30 seconds...")
		time.sleep(30)


# -----------------------------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------------------------
# Setting up wsgi to act as Oracle layer
def configureOracleServer():
	sioServer = socketio.Server(logger=False)
	app = socketio.WSGIApp(sioServer)

	@sioServer.event
	def connect(sid, environm):
		logger.info('Socket connected with sid ' + sid)

	@sioServer.event
	def disconnect(sid):
		logger.info('Lost connection to ' + sid)

	if __name__ == '__main__':
		eventlet.wsgi.server(eventlet.listen(('', 9999)), app, log_output=False, log=socketioLogger)


configureGatsClient()

configureOracleServer()

