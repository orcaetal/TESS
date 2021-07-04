#! usr/env/bin python
import live_functions as localLib
import socketio
import sys
import traceback
from adapterFactory import loadAdapter
import time
import logging
import datetime
import time
import websockets
import asyncio
import hmac
import hashlib
import json
import math
import html
import http.client
import os
import re
import shutil
import threading
import pickle
import pandas as pd


class Bot(threading.Thread):

	# ----------------------------------------------------------------------------------------------------------------------
	# Thead init mandatory override
	def __init__(self, uuid, gatsSocket, offsetTable, botNumber, instance, user_id):
		threading.Thread.__init__(self)
		tableName = offsetTable.split('\\')[-1][:-4]
		
		self.thisFolder = os.path.dirname(os.path.abspath(__file__))
		self.logFolder = os.path.abspath('../logs')
		self.dumpsFolder = os.path.abspath('../dumps')
		## user variables
		self.user = user_id
		self.running = False
		self.config = localLib.loadConfig()
		self.key = self.config["key"]
		self.private = self.config["private"]
		self.email = self.config['license']['email']
		self.licenseKey = self.config['license']['key']
		self.leverageConfig = self.config['leverage']
		self.instance = instance
		self.adapter = loadAdapter(self.config, self.user)
		self.logger = localLib.setupLogger('live'+str(botNumber), f'../logs/live-{tableName}.log', logging.DEBUG)
		self.uuid = uuid
		self.gatsSocket = gatsSocket
		self.exchange = self.config['exchange']
		self.network = self.config['network']
		self.asset = self.config['asset']
		self.version = self.config['version']
		self.stopTradingTrigger = self.config['stopTradingTrigger']
		self.killEmergencyTrigger = self.config['killEmergencyTrigger']
		self.botNumber = botNumber
		self.profit = 0
		self.upnlTotal = 0
		self.currentTime = int(datetime.datetime.now().timestamp() * 1000)
		self.orderActionLimit = 100
		self.leverage = 0
		self.side = ''
		self.leverageTimer = self.currentTime
		self.newPrice = False
		self.orderList = []
		self.avgEntry = {}
		self.paused = False
		self.primary = False
		self.primaryCounter = 0
		self.globalStarted = False
		self.stopTradingTriggered = False
		with open('../dumps/instance.pickle', 'rb') as handle:
			instance = pickle.load(handle)
		self.instance = instance

		if not os.path.isdir(self.dumpsFolder + '/' + str(self.botNumber)):
			os.makedirs(self.dumpsFolder + '/' + str(self.botNumber), )
		
		if not os.path.isfile(self.dumpsFolder + '/' + 'equity.csv'):
			with open('../dumps/equity.csv','w') as eqf:
				returnInfo = self.adapter.fetchLeverage()
				initLev = returnInfo[0]
				initSide = returnInfo[1]
				initSize = returnInfo[2]
				initEntry = returnInfo[3]
				initEquity = self.adapter.fetchEquity(self.asset.upper())
				initTime = self.currentTime
				eqf.write('leverage,side,size,entry,equity,time\n')
				eqf.write(str(initLev)+','+initSide+','+str(initSize)+','+str(initEntry)+','+str(initEquity)+','+str(initTime)+'\n')
		
		
		self.outputFiles = ['../dumps/' + str(self.botNumber) + '/agentDump.json',
							'../dumps/' + str(self.botNumber) + '/orderDump.json',
							'../dumps/' + str(self.botNumber) + '/varDump.json',
							'../dumps/' + str(self.botNumber) + '/historyDump.json']

		self.outputStrings = ['None', 'None', 'None', 'None']
		self.orderHistory = []
		# Declare globals
		self.currentRSI = {'price': 'NotInitialized'}
		pd.DataFrame(self.orderList).to_csv('../dumps/' + str(self.botNumber) + '/orderDump.csv')
		with open('../dumps/' + str(self.botNumber) + '/state.pickle', 'wb+') as handle:
			pickle.dump({'state': 'stop', 'executed': True}, handle)

		with open('../dumps/' + str(self.botNumber) + '/name.pickle', 'wb+') as handle:
			pickle.dump(offsetTable, handle)

		with open(f'../dumps/{self.botNumber}/avgEntry.pickle', 'wb+') as handle:
			pickle.dump({'avgEntry': 0, 'pos': 0}, handle)

		tempPrice = {'rpnl': 0, 'upnl': 0, 'net': 0, 'price': 0, 'leverage': 1}
		# botinit
		with open(f'../dumps/{self.botNumber}/pnls.pickle', 'wb+') as handle:
			pickle.dump(tempPrice, handle)
		
		availBalance = self.adapter.fetchBalance()
		initPrice = self.adapter.fetchPrice()
		if not os.path.isfile(self.dumpsFolder + '/' + str(self.botNumber) + '/runningTable.csv'):
			self.offsetTable = localLib.offsetTable(offsetTable,availBalance,initPrice)
			pd.DataFrame(self.offsetTable).to_csv(
				self.dumpsFolder + '/' + str(self.botNumber) + '/runningTable.csv', index=False)
		else:
			self.offsetTable = pd.read_csv(
				self.dumpsFolder + '/' + str(self.botNumber) + '/runningTable.csv').to_dict('records')
		
		#round amounts and offsets
		for initAgents in self.offsetTable:
			initAgents['offset'] = localLib.roundHalf(self,initAgents['offset'])
			initAgents['amount'] = round(initAgents['amount'])
			if initAgents['amount'] == 0:
				initAgents['amount'] = 1
		
		# check minion/tier format
		chi = []
		par = []
		gpar = []
		gch = []
		pop = []
		for fTree in self.offsetTable:
			if fTree['parent'] != 'None':
				chi.append(fTree['entry_id'])
				par.append(fTree['parent'])
			if fTree['grandparent'] != 'None':
				gch.append(fTree['entry_id'])
				gpar.append(fTree['grandparent'])
			pop.append(fTree['entry_id'])
		
		missingChild = False
		for chis in chi:
			if chis not in pop:
				missingChild = True
		for pars in par:
			if pars not in pop:
				missingChild = True
		for gchs in gch:
			if gchs not in pop:
				missingChild = True
		for gpars in gpar:
			if gpars not in pop:
				missingChild = True
		
		if missingChild:
			print('ERROR: PLEASE VISIT CUSTOMER SERVICE TO CLAIM LOST CHILD')
			exit()

		# find rsi periods
		self.rsiPeriods = []
		# check duplicate name
		nameList = []
		for agentz in self.offsetTable:
			if agentz['rsiPeriod'] not in self.rsiPeriods:
				self.rsiPeriods.append(agentz['rsiPeriod'])
			if agentz['entry_id'] not in nameList:
				nameList.append(agentz['entry_id'])
			else:
				print('DUPLICATE AGENT ID DETECTED. SELF DESTRUCT')
				exit()

		##fill initial hundred candles to candle DB for each period
		self.rsiCandleDBs = []
		for rsiPeriod in self.rsiPeriods:
			self.rsiCandleDBs.append(self.adapter.rsiReading(rsiPeriod))

		#test call
		self.adapter.testCall()
	# ----------------------------------------------------------------------------------------------------------------------

	# ----------------------------------------------------------------------------------------------------------------------
	# Connect to oracle layer for metrics and other events
	# TODO revisit if this is actually needed (possibly needed for metric logging and upates to running bot information)
	def connectOracle(self, callback):
		self.sio = socketio.Client()

		@self.sio.event
		def connect():
			self.logger.info('Successfully connected to Oracle layer!')
			self.running = True
			callback()
			return True

		@self.sio.event
		def connect_error(data):
			self.logger.error('Failed to connect to Oracle layer!')
			self.logger.debug(data)
			self.logger.info("Exiting in 30 seconds...")
			time.sleep(30)
			return False

		try:
			self.sio.connect('http://localhost:9999?connectionName=rsi')

		except Exception as e:
			print(e, 'from sioconnect')
			self.logger.error(str(e) + '_____from sioconnectt')
			self.logger.error(traceback.format_exc())
			self.logger.info("Exiting in 30 seconds...")
			time.sleep(30)
			return False

	# ----------------------------------------------------------------------------------------------------------------------

	# ----------------------------------------------------------------------------------------------------------------------
	# Run "listenOrders" functionality
	# ----------------------------------------------------------------------------------------------------------------------
	## handle filled orders
	def listenOrders(self, data):
		# Note: This function is also called from the listenExecution pathway
		filledOrder = data['side'][0]
		filledSide = data['side'][1]
		tfSMA = ['5', '15', '60', '240']
		tfEMA = ['15', '120', '360']
		self.currentTime = int(datetime.datetime.now().timestamp() * 1000)

		# check each agent
		rows = []
		for agent in self.offsetTable:
			if agent['entry_id'] == data['id']:
				if filledOrder == '2' and filledSide == 'b':
					if agent['opening_sell_price'] == 0:
						agent['opening_sell_price'] = float(data['price'])
						agent['opening_sell_timestamp'] = self.currentTime - (1000 * 120)
						self.logger.error(agent['entry_id'] + ' opening trade info missing on trade completion')

					agent['closing_buy_timestamp'] = self.currentTime
					agent['closing_buy_price'] = float(data['price'])
					agent['time_total_trade'] = (agent['closing_buy_timestamp'] - agent['init_sell_timestamp']) / (
							1000 * 3600)

					if agent['trailing_tp'] == 0:
						rebate = localLib.rebate(agent['amount'], agent['closing_buy_price'], True)
						agent['rpnl_short'] += rebate
						self.profit += rebate
						agent['trade_profit_short'] += rebate
					else:
						rebate = localLib.rebate(agent['amount'], agent['closing_buy_price'], False)
						agent['rpnl_short'] += rebate
						self.profit += rebate
						agent['trade_profit_short'] += rebate

					rpnl = localLib.upnl('short', agent['opening_sell_price'], agent['closing_buy_price'],
										 agent['amount'], agent['entry_id'])
					if rpnl > 0:
						agent['recent_close_type'] = 'profit_sell'
					else:
						agent['recent_close_type'] = 'stop_sell'

					agent['rpnl_short'] += rpnl
					self.profit += rpnl
					agent['trade_profit_short'] += rpnl

					if agent['max_drawdown_short'] == 0:
						agent['max_drawdown_short'] = 0.000001

					if agent['time_total_trade'] <= 0:
						agent['time_total_trade'] = 1
					agent['fitness_score'] = localLib.fitnessScore(agent['trade_profit_short'],
																   agent['max_drawdown_short'],
																   agent['time_total_trade'], agent['amount'])

					agent['offset_ratio'] = (agent['exit_multiplier'] * agent['offset']) / (
							agent['closing_buy_price'] + agent['exit_multiplier'] * agent['offset'])

					self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
						'entry_id'] + ' | ' + '[SHORT] CLOSING BUY FILLED' + ' | ' + 'fill price: ' + str(
						agent['closing_buy_price']) + ' | ' + 'buy status:' + agent[
										 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])
					print(agent['entry_id'], 'Closing Buy Filled')
					# build ribbons for metric
					priceDictSMA = {}
					priceDictEMA = {}
					for timeframe in tfSMA:
						prices = localLib.fetchPriceList(self, timeframe, int(agent['opening_sell_timestamp']))
						priceDictSMA[timeframe] = prices
					for timeframe in tfEMA:
						prices = localLib.fetchPriceList(self, timeframe, int(agent['opening_sell_timestamp']))
						priceDictEMA[timeframe] = prices
					ribbons = localLib.buildRibbons(self, priceDictEMA)
					SMAribbons = localLib.buildSMARibbons(self, priceDictSMA)
					variances = localLib.buildVariances(self, priceDictSMA)
					#stochRsi = localLib.buildStochs(self, priceDictSMA)
					threeRibbon = localLib.buildSingleRibbon(self, '3', agent['opening_sell_timestamp'])
					#midnightCandle = localLib.buildMidnightCandle(self, agent['opening_sell_timestamp'])
					# priceHistory = localLib.buildPriceHistory(self,tf,agent['opening_sell_timestamp'])
					metric = {}
					metric['agent_info'] = agent
					metric['trend'] = localLib.binaryString(ribbons)
					metric['binary_SMA'] = localLib.binaryStringSMA(SMAribbons)
					metric['percent_SMA'] = localLib.percentSMA(agent['opening_sell_price'], SMAribbons)
					metric['3min_ribbon'] = threeRibbon
					metric['std_price'] = variances
					#metric['stoch_RSI'] = stochRsi
					# commented out to prevent index out of range errors occasionally; if we need it again, that needs to be debugged/addressed
					# metric['midnight_candle'] = float(midnightCandle[0]['close']) / float(midnightCandle[0]['open'])
					metric['side'] = 'Short'

					# metric['price_history'] = priceHistory
					self.gatsSocket.emit('log_metric',
										 {'metrics': metric, 'version': self.version, 'exchange': self.exchange,
										  'asset': self.asset, 'network': self.network, 'instance': self.instance})

					rows.append([agent['entry_id'], agent['amount'], metric['side'], agent['opening_sell_timestamp'],
								 agent['closing_buy_timestamp'], agent['opening_sell_price'],
								 agent['closing_buy_price'], agent['trade_profit_short'], agent['fitness_score'],
								 self.instance])
					agent['sell_status'] = 'looking_to_open'
					agent['opening_sell_price'] = 0.
					agent['opening_sell_timestamp'] = 0
					agent['closing_buy_timestamp'] = 0
					agent['closing_buy_timed'] = 'False'
					agent['closing_buy_price'] = 0
					agent['upnl_short'] = 0
					agent['init_sell_timestamp'] = self.currentTime
					agent['time_of_close_sell'] = self.currentTime
					agent['sells_counter'] += 1
					agent['max_drawdown_short'] = 0
					agent['short_tp_price'] = 100000000
					agent['short_te_price'] = 0
					agent['trade_profit_short'] = 0
					if agent['parent'] != 'None':
						agent['sell_status'] = 'not_active'
					#unsure why this was here for received switch	
					#if agent['trailing_tp'] != 0:
					agent['received'] = True
					
				if filledOrder == '2' and filledSide == 's':
					if agent['opening_buy_price'] == 0:
						agent['opening_buy_price'] = float(data['price'])
						agent['opening_buy_timestamp'] = self.currentTime - (1000 * 120)
						self.logger.error(agent['entry_id'] + ' opening trade info missing on trade completion')

					agent['closing_sell_timestamp'] = self.currentTime
					agent['closing_sell_price'] = float(data['price'])
					agent['time_total_trade'] = (agent['closing_sell_timestamp'] - agent['init_buy_timestamp']) / (
							1000 * 3600)

					rpnl = localLib.upnl('long', agent['opening_buy_price'], agent['closing_sell_price'],
										 agent['amount'], agent['entry_id'])
					if rpnl > 0:
						agent['recent_close_type'] = 'profit_buy'
					else:
						agent['recent_close_type'] = 'stop_buy'

					agent['rpnl_long'] += rpnl
					self.profit += rpnl
					agent['trade_profit_long'] += rpnl

					if agent['trailing_tp'] == 0:
						rebate = localLib.rebate(agent['amount'], agent['closing_sell_price'], True)
						agent['rpnl_long'] += rebate
						self.profit += rebate
						agent['trade_profit_long'] += rebate
					else:
						rebate = localLib.rebate(agent['amount'], agent['closing_sell_price'], False)
						agent['rpnl_long'] += rebate
						self.profit += rebate
						agent['trade_profit_long'] += rebate

					if agent['max_drawdown_long'] == 0:
						agent['max_drawdown_long'] = 0.000001

					if agent['time_total_trade'] <= 0:
						agent['time_total_trade'] = 1

					agent['fitness_score'] = localLib.fitnessScore(agent['trade_profit_long'],
																   agent['max_drawdown_long'],
																   agent['time_total_trade'], agent['amount'])

					agent['offset_ratio'] = (agent['exit_multiplier'] * agent['offset']) / (
							agent['closing_sell_price'] - agent['exit_multiplier'] * agent['offset'])

					self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
						'entry_id'] + ' | ' + '[LONG] CLOSING SELL FILLED' + ' | ' + 'fill price: ' + str(
						agent['closing_sell_price']) + ' | ' + 'buy status:' + agent[
										 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])
					print(agent['entry_id'], 'Closing Sell Filled')

					# build ribbons for metric
					priceDictSMA = {}
					priceDictEMA = {}
					for timeframe in tfSMA:
						prices = localLib.fetchPriceList(self, timeframe, int(agent['opening_buy_timestamp']))
						priceDictSMA[timeframe] = prices
					for timeframe in tfEMA:
						prices = localLib.fetchPriceList(self, timeframe, int(agent['opening_buy_timestamp']))
						priceDictEMA[timeframe] = prices

					ribbons = localLib.buildRibbons(self, priceDictEMA)
					SMAribbons = localLib.buildSMARibbons(self, priceDictSMA)
					variances = localLib.buildVariances(self, priceDictSMA)
					#stochRsi = localLib.buildStochs(self, priceDictSMA)
					threeRibbon = localLib.buildSingleRibbon(self, '3', agent['opening_buy_timestamp'])
					#midnightCandle = localLib.buildMidnightCandle(self, agent['opening_buy_timestamp'])
					# priceHistory = localLib.buildPriceHistory(self,tf,agent['opening_sell_timestamp'])

					metric = {}
					metric['agent_info'] = agent
					metric['trend'] = localLib.binaryString(ribbons)
					metric['binary_SMA'] = localLib.binaryStringSMA(SMAribbons)
					metric['percent_SMA'] = localLib.percentSMA(agent['opening_buy_price'], SMAribbons)
					metric['std_price'] = variances
					metric['3min_ribbon'] = threeRibbon
					#metric['stoch_RSI'] = stochRsi
					# commented out to prevent index out of range errors occasionally; if we need it again, that needs to be debugged/addressed
					# metric['midnight_candle'] = float(midnightCandle[0]['close']) / float(midnightCandle[0]['open'])
					metric['side'] = 'Long'

					# metric['price_history'] = priceHistory

					self.gatsSocket.emit('log_metric',
										 {'metrics': metric, 'version': self.version, 'exchange': self.exchange,
										  'asset': self.asset, 'network': self.network, 'instance': self.instance})

					# self.orderHistory.append([agent['closing_sell_timestamp'],agent['entry_id'],'closing','sell',agent['closing_sell_price'],agent['amount']])
					# if len(self.orderHistory) > 10:
					# 	self.orderHistory.pop(0)

					rows.append([agent['entry_id'], agent['amount'], metric['side'], agent['opening_buy_timestamp'],
								 agent['closing_sell_timestamp'], agent['opening_buy_price'],
								 agent['closing_sell_price'], agent['trade_profit_long'], agent['fitness_score'],
								 self.instance])

					agent['buy_status'] = 'looking_to_open'
					agent['opening_buy_price'] = 0.
					agent['opening_buy_timestamp'] = 0
					agent['closing_sell_timestamp'] = 0
					agent['closing_sell_timed'] = 'False'
					agent['closing_sell_price'] = 0
					agent['upnl_long'] = 0
					agent['time_of_close_buy'] = self.currentTime
					agent['init_buy_timestamp'] = self.currentTime
					agent['buys_counter'] += 1
					agent['max_drawdown_long'] = 0
					agent['long_tp_price'] = 0
					agent['long_te_price'] = 100000000
					agent['trade_profit_long'] = 0
					if agent['parent'] != 'None':
						agent['buy_status'] = 'not_active'
					#idk why this was here
					#if agent['trailing_tp'] != 0:
					agent['received'] = True
						
				if agent['prevent_exits'] == 'True' and filledOrder == '1' and filledSide == 'b':

					agent['opening_buy_price'] = float(data['price'])
					agent['opening_buy_timestamp'] = self.currentTime
					
					if agent['trailing_entry'] == 0:
						rebate = localLib.rebate(agent['amount'], agent['opening_buy_price'], True)
						agent['rpnl_long'] += rebate
						self.profit += rebate
						agent['trade_profit_long'] += rebate
					else:
						rebate = localLib.rebate(agent['amount'], agent['opening_buy_price'], False)
						agent['rpnl_long'] += rebate
						self.profit += rebate
						agent['trade_profit_long'] += rebate

					# self.orderHistory.append([agent['opening_buy_timestamp'],agent['entry_id'],'opening','buy',agent['opening_buy_price'],agent['amount']])
					# if len(self.orderHistory) > 10:
					# 	self.orderHistory.pop(0)

					agent['buy_status'] = 'looking_to_close'
					agent['lte_target'] = 'None'
					agent['long_te_price'] = 1000000000

					self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
						'entry_id'] + ' | ' + '[LONG] OPENING BUY FILLED' + ' | ' + 'fill price: ' + str(
						agent['opening_buy_price']) + ' | ' + 'buy status:' + agent[
										 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])
					print(agent['entry_id'], 'Opening Buy Filled')
					#if agent['trailing_entry'] != 0:
					agent['received'] = True

				if agent['prevent_exits'] == 'True' and filledOrder == '1' and filledSide == 's':

					agent['opening_sell_price'] = float(data['price'])
					agent['opening_sell_timestamp'] = self.currentTime
					
					if agent['trailing_entry'] == 0:
						rebate = localLib.rebate(agent['amount'], agent['opening_sell_price'], True)
						agent['rpnl_short'] += rebate
						self.profit += rebate
						agent['trade_profit_short'] += rebate
					else:
						rebate = localLib.rebate(agent['amount'], agent['opening_sell_price'], False)
						agent['rpnl_short'] += rebate
						self.profit += rebate
						agent['trade_profit_short'] += rebate
						
					agent['sell_status'] = 'looking_to_close'
					agent['ste_target'] = 'None'
					agent['short_te_price'] = 0

					self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
						'entry_id'] + ' | ' + '[SHORT] OPENING SELL FILLED' + ' | ' + 'fill price: ' + str(
						agent['opening_sell_price']) + ' | ' + 'buy status:' + agent[
										 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])
					print(agent['entry_id'], 'Opening Sell Filled')
					#if agent['trailing_tp'] != 0:
					agent['received'] = True
						
				#place closing pair
				if agent['prevent_exits'] == 'False' and filledOrder == '1':

					# place closing sell
					if filledSide == 'b':

						print(agent['entry_id'], 'Opening Buy Filled')
						agent['opening_buy_price'] = float(data['price'])
						agent['opening_buy_timestamp'] = self.currentTime
						
						if agent['trailing_entry'] == 0:
							rebate = localLib.rebate(agent['amount'], agent['opening_buy_price'], True)
							agent['rpnl_long'] += rebate
							self.profit += rebate
							agent['trade_profit_long'] += rebate
						else:
							rebate = localLib.rebate(agent['amount'], agent['opening_buy_price'], False)
							agent['rpnl_long'] += rebate
							self.profit += rebate
							agent['trade_profit_long'] += rebate
							agent['lte_target'] = 'None'
							agent['long_te_price'] = 10000000

						self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
							'entry_id'] + ' | ' + '[LONG] OPENING BUY FILLED' + ' | ' + 'fill price: ' + str(
							agent['opening_buy_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

						if agent['trailing_tp'] == 0:
							returnDict = self.adapter.placeLimitOrder(agent,agent['opening_buy_price'] + (agent['offset']*agent['exit_multiplier']), 'Sell', 'Close')
							self.orderActionLimit = returnDict['rate_limit_status']
							#agent['buy_status'] = 'close_placed'
							agent['closing_sell_price'] = agent['opening_buy_price'] + (
										agent['offset'] * agent['exit_multiplier'])
							agent['closing_sell_timestamp'] = self.currentTime
							self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
								'entry_id'] + ' | ' + '[LONG] CLOSING SELL PLACED' + ' | ' + 'target price: ' + str(
								agent['closing_sell_price']) + ' | ' + 'buy status:' + agent[
												 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

						else:
							agent['buy_status'] = 'looking_to_close'
							
						
						#if agent['trailing_entry'] != 0:
						agent['received'] = True
						
					# place closing buy
					elif filledSide == 's':

						print(agent['entry_id'], 'Opening Sell Filled')
						agent['opening_sell_price'] = float(data['price'])
						agent['opening_sell_timestamp'] = self.currentTime
						
						if agent['trailing_entry'] == 0:
							rebate = localLib.rebate(agent['amount'], agent['opening_sell_price'], True)
							agent['rpnl_short'] += rebate
							self.profit += rebate
							agent['trade_profit_short'] += rebate
						else:
							rebate = localLib.rebate(agent['amount'], agent['opening_sell_price'], False)
							agent['rpnl_short'] += rebate
							self.profit += rebate
							agent['trade_profit_short'] += rebate
							agent['ste_target'] = 'None'
							agent['short_te_price'] = 0

						self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
							'entry_id'] + ' | ' + '[SHORT] OPENING SELL FILLED' + ' | ' + 'fill price: ' + str(
							agent['opening_sell_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

						if agent['trailing_tp'] == 0:
							returnDict = self.adapter.placeLimitOrder(agent,agent['opening_sell_price'] - (agent['offset']*agent['exit_multiplier']), 'Buy', 'Close')
							self.orderActionLimit = returnDict['rate_limit_status']
							#agent['sell_status'] = 'close_placed'
							agent['closing_buy_price'] = agent['opening_sell_price'] - (
										agent['offset'] * agent['exit_multiplier'])
							agent['closing_buy_timestamp'] = self.currentTime
							self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
								'entry_id'] + ' | ' + '[SHORT] CLOSING BUY PLACED' + ' | ' + 'target price: ' + str(
								agent['closing_buy_price']) + ' | ' + 'buy status:' + agent[
												 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

						else:
							agent['sell_status'] = 'looking_to_close'
							
						
						#if agent['trailing_entry'] != 0:
						agent['received'] = True
				
				
		if rows:
			df = pd.read_csv('../dumps/tradelog.csv')
			df = df.append(pd.DataFrame(rows,
				columns=['Agent', 'Amount', 'Side', 'OST', 'CBT', 'OSP', 'CBP', 'RPNL', 'Fitness', 'Instance']))
			df.to_csv('../dumps/tradelog.csv', index=False)
			
		
	## async function to read data and trigger listenOrders events
	async def socketHandlerListenOrders(self, connStr):
		async with websockets.connect(connStr) as websocket:
			await websocket.send(self.adapter.subscribeOrder())

			async for messages in websocket:
				data = self.adapter.orderData(messages)
				
				####detect filled orders
				if data:

					if data['order_status'] == 'Filled':
						# MarketOrders don't return correct pricing data in the 'orders' subscription so must be handled
						# From the 'execution' subscription, see socketHandlerListenExecution below
						if data['order_type'] != 'Market':
							while True:
								fails = 0
								try:
									self.listenOrders(data)
									break
								except Exception as e:
									fails+=1
									print('listMain ', e)
									self.logger.error(str(e)+'_____from _runListen'+str(data['order_link_id']))
									self.logger.error(traceback.format_exc())
									time.sleep(1)
									if fails > 2:
										break

					####detect post-only orphans and cancels
					elif data['order_status'] == 'Cancelled':

						capt = re.search('(.+)\-(.+)=(.+)', data['order_link_id'])
						if capt:

							if re.search('1b', capt.group(2)):
								for rows in self.offsetTable:
									if rows['entry_id'] == capt.group(1):
										print(capt.group(1), 'Opening Buy Cancelled')
										rows['buy_status'] = 'looking_to_open'
										self.logger.info(str(self.currentRSI['price']) + ' | ' + rows[
											'entry_id'] + ' | ' + '[LONG] OPENING BUY CANCEL CONFIRMED' + ' | ' + 'buy status:' +
														 rows['buy_status'] + ' | ' + 'sell status:' + rows[
															 'sell_status'])
										rows['received'] = True

							elif re.search('1s', capt.group(2)):
								for rows in self.offsetTable:
									if rows['entry_id'] == capt.group(1):
										print(capt.group(1), 'Opening Sell Cancelled')
										rows['sell_status'] = 'looking_to_open'
										self.logger.info(str(self.currentRSI['price']) + ' | ' + rows[
											'entry_id'] + ' | ' + '[SHORT] OPENING SELL CANCEL CONFIRMED' + ' | ' + 'buy status:' +
														 rows['buy_status'] + ' | ' + 'sell status:' + rows[
															 'sell_status'])
										rows['received'] = True

							elif re.search('2b', capt.group(2)):
								for rows in self.offsetTable:
									if rows['entry_id'] == capt.group(1):
										print(capt.group(1), 'Closing Buy Cancelled')
										self.logger.info(str(self.currentRSI['price']) + ' | ' + rows[
											'entry_id'] + ' | ' + 'status before SL block' + ' | ' + 'buy status:' +
														 rows['buy_status'] + ' | ' + 'sell status:' + rows[
															 'sell_status'])

										# distinguish sl cancels from resets
										if rows['sell_status'] == 'stop_loss' or rows[
											'sell_status'] == 'looking_to_open':
											rows['sell_status'] = 'looking_to_open'
										else:
											rows['sell_status'] = 'looking_to_close'
										self.logger.info(str(self.currentRSI['price']) + ' | ' + rows[
											'entry_id'] + ' | ' + 'status after SL block' + ' | ' + 'buy status:' +
														 rows['buy_status'] + ' | ' + 'sell status:' + rows[
															 'sell_status'])

										self.logger.info(str(self.currentRSI['price']) + ' | ' + rows[
											'entry_id'] + ' | ' + '[SHORT] CLOSING BUY CANCEL CONFIRMED' + ' | ' + 'buy status:' +
														 rows['buy_status'] + ' | ' + 'sell status:' + rows[
															 'sell_status'])
										rows['received'] = True

							elif re.search('2s', capt.group(2)):
								for rows in self.offsetTable:
									if rows['entry_id'] == capt.group(1):
										print(capt.group(1), 'Closing Sell Cancelled')
										self.logger.info(str(self.currentRSI['price']) + ' | ' + rows[
											'entry_id'] + ' | ' + 'status before SL block' + ' | ' + 'buy status:' +
														 rows['buy_status'] + ' | ' + 'sell status:' + rows[
															 'sell_status'])

										# distinguish sl cancels from resets
										if rows['buy_status'] == 'stop_loss' or rows['buy_status'] == 'looking_to_open':
											rows['buy_status'] = 'looking_to_open'
										else:
											rows['buy_status'] = 'looking_to_close'
										self.logger.info(str(self.currentRSI['price']) + ' | ' + rows[
											'entry_id'] + ' | ' + 'status after SL block' + ' | ' + 'buy status:' +
														 rows['buy_status'] + ' | ' + 'sell status:' + rows[
															 'sell_status'])

										self.logger.info(str(self.currentRSI['price']) + ' | ' + rows[
											'entry_id'] + ' | ' + '[LONG] CLOSING SELL CANCEL CONFIRMED' + ' | ' + 'buy status:' +
														 rows['buy_status'] + ' | ' + 'sell status:' + rows[
															 'sell_status'])
										rows['received'] = True

					###detect placed orders
					elif data['order_status'] == 'New':

						capt = re.search('(.+)\-(.+)=(.+)', data['order_link_id'])
						if capt:

							if re.search('1b', capt.group(2)):
								for rows in self.offsetTable:
									if rows['entry_id'] == capt.group(1):
										if rows['trailing_entry'] == 0:
											print(capt.group(1), 'Opening Buy Placed')
											rows['buy_status'] = 'open_placed'
											self.logger.info(str(self.currentRSI['price'])+' | '+rows['entry_id']+' | '+'[LONG] OPENING BUY PLACED CONFIRMED'+' | ' +'buy status:'+rows['buy_status']+' | '+'sell status:'+rows['sell_status'])
											rows['received'] = True
											
							elif re.search('1s',capt.group(2)):
								for rows in self.offsetTable:
									if rows['entry_id'] == capt.group(1):
										if rows['trailing_entry'] == 0:
											print(capt.group(1), 'Opening Sell Placed')
											rows['sell_status'] = 'open_placed'
											self.logger.info(str(self.currentRSI['price'])+' | '+rows['entry_id']+' | '+'[SHORT] OPENING SELL PLACED CONFIRMED'+' | ' +'buy status:'+rows['buy_status']+' | '+'sell status:'+rows['sell_status'])
											rows['received'] = True
											
							elif re.search('2b',capt.group(2)):
								for rows in self.offsetTable:
									if rows['entry_id'] == capt.group(1):
										if rows['trailing_tp'] == 0:
											print(capt.group(1), 'Closing Buy Placed')
											rows['sell_status'] = 'close_placed'
											self.logger.info(str(self.currentRSI['price'])+' | '+rows['entry_id']+' | '+'[SHORT] CLOSING BUY PLACED CONFIRMED'+' | ' +'buy status:'+rows['buy_status']+' | '+'sell status:'+rows['sell_status'])
											rows['received'] = True

							elif re.search('2s', capt.group(2)):
								for rows in self.offsetTable:
									if rows['entry_id'] == capt.group(1):
										if rows['trailing_tp'] == 0:
											print(capt.group(1), 'Closing Sell Placed')
											rows['buy_status'] = 'close_placed'
											self.logger.info(str(self.currentRSI['price'])+' | '+rows['entry_id']+' | '+'[LONG] CLOSING SELL PLACED CONFIRMED'+' | ' +'buy status:'+rows['buy_status']+' | '+'sell status:'+rows['sell_status'])
											rows['received'] = True
											
					elif data['order_status'] == 'PartiallyFilled':
						capt = re.search('(.+)\-(.+)=(.+)', data['order_link_id'])
						if capt:
							print(capt.group(1), 'Order partially filled')
					else:
						print(data)

											
	## "private" function to continue listen functionality threading for orders
	def _runListenOrders(self):
		loop = asyncio.new_event_loop()

		while True:
			try:
				connStr = self.adapter.authenticate(5000)
				loop.run_until_complete(self.socketHandlerListenOrders(connStr))
			
			except Exception as e:
				if re.search('.+1006.+',str(e)):
					print('connection lost, please wait for reconnect')
				else:
					self.logger.error(str(e)+'_____from runListenOrders')
					self.logger.error(traceback.format_exc())
					time.sleep(1)

	## "public" function to set off listen functionality threading
	def runListenOrders(self):
		try:
			self._runListenOrders()
			
		except Exception as e:
			print('listen',e)
			self.logger.error(str(e)+'_____from _runListenOrders')
			self.logger.error(traceback.format_exc())
			self.logger.warning("Exiting in 30 seconds...")
			time.sleep(30)


	# ----------------------------------------------------------------------------------------------------------------------
	# Run "listenExecution" functionality
	# ----------------------------------------------------------------------------------------------------------------------
	async def socketHandlerListenExecution(self, connStr):
		async with websockets.connect(connStr) as websocket:
			await websocket.send(self.adapter.subscribeExecution())

			async for messages in websocket:
				# Data returned from 'execution' is close enough to that from 'order' that we can
				# use the same function to handle the message
				data = self.adapter.orderData(messages)

				####detect filled orders
				# Actually exec_type == 'Trade' since this is the execution pathway
				# Limit orders are handled in the 'order' subscription, market orders here.
				if data and data['order_status'] == 'Filled' and data['order_type'] == 'Market':
					while True:
						fails = 0
						try:
							self.listenOrders(data)
							break
						except Exception as e:
							fails+=1
							print('listMain ', e)
							self.logger.error(str(e)+'_____from _runListenExecution'+str(data['order_link_id']))
							self.logger.error(traceback.format_exc())
							time.sleep(1)
							if fails > 2:
								break


	## "private" function to continue listen functionality threading for orders
	def _runListenExecution(self):
		loop = asyncio.new_event_loop()
		
		while True:
			try:
				connStr = self.adapter.authenticate(5000)
				loop.run_until_complete(self.socketHandlerListenExecution(connStr))
			except Exception as e:
				if re.search('.+1006.+',str(e)):
					print('connection lost, please wait for reconnect')
				else:
					self.logger.error(str(e)+'_____from runListenExecution')
					self.logger.error(traceback.format_exc())
					time.sleep(1)

	## "public" function to set off listen functionality threading
	def runListenExecution(self):
		try:
			self._runListenExecution()
			
		except Exception as e:
			print('listen',e)
			self.logger.error(str(e)+'_____from _runListenExecution')
			self.logger.error(traceback.format_exc())
			self.logger.warning("Exiting in 30 seconds...")
			time.sleep(30)

	# ----------------------------------------------------------------------------------------------------------------------

	# ----------------------------------------------------------------------------------------------------------------------
	# Run "rsi" functionality
	# ----------------------------------------------------------------------------------------------------------------------
	## async function to read data and handle rsi updates from the websockets
	async def socketHandlerRsi(self, connStr):
		prevSeq = 0
		prevPrice = 0
		# connect to bybit websocket
		async with websockets.connect(connStr) as websocket:
			# subscribe kline topic
			await websocket.send(self.adapter.subscribeAsset())

			# process incoming data.
			async for messages in websocket:

				data = self.adapter.priceAction(messages)
				if data:
					self.currentTime = int(datetime.datetime.now().timestamp() * 1000)
					# if new candle close
					if data['confirm'] == True and data['cross_seq'] != prevSeq:

						prevSeq = data['cross_seq']
						prevPrice = data['close']
						
						while True:
							try:
								#update candles.csv
								with open('../dumps/candles.csv','a') as myCandles:
									myCandles.write(self.asset.upper() + ',1,' + str(data['start']) + ',' + str(data['open']) + ',' + str(data['high']) + ',' + str(data['low']) + ',' + str(data['close']) + ',' + str(data['volume']) + ',' + str(data['turnover']) + '\n')
								break
							except:
								time.sleep(0.1)
								
						# init dict with price
						self.currentRSI = {'price': data['close']}

						# calc rsi and add rsi to database
						for i in range(len(self.rsiCandleDBs)):
							self.rsiCandleDBs[i].append(data)
							self.rsiCandleDBs[i][-1]['trs'] = localLib.rsiFunc(self.rsiCandleDBs[i], int(self.rsiPeriods[i]))
							self.currentRSI[self.rsiPeriods[i]] = self.rsiCandleDBs[i][-1]['trs']

							##trim DB
							if len(self.rsiCandleDBs[i]) > 200:
								self.rsiCandleDBs[i].pop(0)

						self.newPrice = True

					# snapshot data, same as above without adding to database
					elif data['close'] != prevPrice:

						prevPrice = data['close']

						self.currentRSI = {'price': data['close']}
						fakeDBs = self.rsiCandleDBs

						for i in range(len(fakeDBs)):
							fakeDBs[i].append(data)
							fakeDBs[i][-1]['rsi'] = localLib.rsiFunc(fakeDBs[i], int(self.rsiPeriods[i]))
							self.currentRSI[self.rsiPeriods[i]] = fakeDBs[i][-1]['rsi']

							fakeDBs[i].pop()

						self.newPrice = True

	## "private" functoin to continue rsi functionality threading
	def _runRsi(self):
		loop = asyncio.new_event_loop()
		while True:
			if not self.running:
				pass
			else:
				try:
					connStr = self.adapter.authenticate(10000)
					loop.run_until_complete(self.socketHandlerRsi(connStr))
				except Exception as e:
					if re.search('.+1006.+',str(e)):
						print('connection lost, please wait for reconnect')
					else:
						#traceback.print_exc()
						self.logger.error(str(e) + '_____from _runRsi')
						self.logger.error(traceback.format_exc())
						time.sleep(1)

	## "public" function to set off rsi functionality threading
	def runRsi(self):
		try:
			self._runRsi()

		except Exception as e:
			self.logger.error(str(e)+'_____from runRsi')
			self.logger.error(traceback.format_exc())
			self.logger.info("Exiting in 30 seconds...")
			time.sleep(30)

	# ----------------------------------------------------------------------------------------------------------------------

	# ----------------------------------------------------------------------------------------------------------------------
	# Run "live" functionality
	# ----------------------------------------------------------------------------------------------------------------------
	## look to place orders
	def liveOrders(self):
		if self.currentRSI == {'price': 'NotInitialized'}:
			print('Loading....')
			return
		self.currentTime = int(datetime.datetime.now().timestamp() * 1000)
		pricePrint = {'price': self.currentRSI['price'], 'rpnl': self.profit, 'upnl': self.upnlTotal,
					  'net': (self.profit + self.upnlTotal)}
		while True:
			try:
				with open(f'../dumps/{self.botNumber}/pnls.pickle', 'wb+') as handle:
					pickle.dump(pricePrint, handle)
				break
			except:
				time.sleep(0.1)
				
		# avoid rate limit for v2/private/order/create (shared endpoint)
		if self.orderActionLimit > 50:
			pass
		# print(self.orderActionLimit, ' pause for ', 0)
		elif 30 < self.orderActionLimit < 50:
			# print(self.orderActionLimit, ' pause for ', 1)
			time.sleep(1)
		elif 15 < self.orderActionLimit < 30:
			# print(self.orderActionLimit, ' pause for ', 3)
			time.sleep(3)
		elif 0 < self.orderActionLimit < 15:
			# print(self.orderActionLimit, ' pause for ', 5)
			time.sleep(5)

		# fetch orders from all bots
		self.adapter.fetchOrders()
		#fetch orders from this bot
		self.orderList=[]
		for ords in self.adapter.orderList:
			extractID = re.search("(.+)-.+-.+",ords['order_link_id'])
			if extractID:
				for targets in self.offsetTable:
					if extractID.group(1) == targets['entry_id']:
						self.orderList.append(ords)

		##process each agent individually
		self.upnlTotal = 0

		currentPrice = self.currentRSI['price']
		for agent in self.offsetTable:
			self.avgEntry[agent['entry_id']] = {'long': {'amount': 0, 'price': 0}, 'short': {'amount': 0, 'price': 0}}
			if agent['buy_status'] in ['looking_to_close', 'close_placed', 'trailing_tp']:
				self.avgEntry[agent['entry_id']]['long']['amount'] = agent['amount']
				self.avgEntry[agent['entry_id']]['long']['price'] = agent['opening_buy_price']
			if agent['sell_status'] in ['looking_to_close', 'close_placed', 'trailing_tp']:
				self.avgEntry[agent['entry_id']]['short']['amount'] = agent['amount']
				self.avgEntry[agent['entry_id']]['short']['price'] = agent['opening_sell_price']
			if agent['buy_status'] not in ['looking_to_close', 'close_placed', 'trailing_tp']:
				self.avgEntry[agent['entry_id']]['long']['amount'] = 0
				self.avgEntry[agent['entry_id']]['long']['price'] = 0
			if agent['sell_status'] not in ['looking_to_close', 'close_placed', 'trailing_tp']:
				self.avgEntry[agent['entry_id']]['short']['amount'] = 0
				self.avgEntry[agent['entry_id']]['short']['price'] = 0

			# init timestamps on first execution
			if agent['init_buy_timestamp'] == 0:
				agent['init_buy_timestamp'] = self.currentTime
			if agent['init_sell_timestamp'] == 0:
				agent['init_sell_timestamp'] = self.currentTime
			
			#check for parent status to trigger minions
			#lets get parent status
			if agent['parent'] != 'None':
				for familyTree in self.offsetTable:
					if familyTree['entry_id'] == agent['parent']:
						parentBS = familyTree['buy_status']
						parentSS = familyTree['sell_status']
					if familyTree['entry_id'] == agent['grandparent']:
						grampBS = familyTree['buy_status']
						grampSS = familyTree['sell_status']
				#permission from parent to start
				if (parentBS in ['looking_to_close', 'close_placed', 'trailing_tp']) or (
								parentSS in ['looking_to_close', 'close_placed', 'trailing_tp']):
					#permission from gramp to start
					if (agent['grandparent'] == 'None') or (grampBS in ['looking_to_close', 'close_placed', 'trailing_tp']) or (
							grampSS in ['looking_to_close', 'close_placed', 'trailing_tp']):
						#permission granted -> start
						if agent['buy_status'] == 'not_active' and agent['buys_allowed'] == 'True':
							agent['buy_status'] = 'looking_to_open'
						if agent['sell_status'] == 'not_active' and agent['sells_allowed'] == 'True':
							agent['sell_status'] = 'looking_to_open'
							
				#does child need to stop?
				elif (parentBS in ['looking_to_open', 'open_placed', 'trailing_entry',
						'stop_delay', 'profit_delay', 'not_active']) and (
								parentSS in ['looking_to_open', 'open_placed', 'trailing_entry',
										'stop_delay', 'profit_delay', 'not_active']) or (
					grampBS in ['looking_to_open', 'open_placed', 'trailing_entry',
						'stop_delay', 'profit_delay', 'not_active']) and (
								grampSS in ['looking_to_open', 'open_placed', 'trailing_entry',
										'stop_delay', 'profit_delay', 'not_active']):
					#yes
					if agent['buy_status'] in ['looking_to_open', 'open_placed', 'trailing_entry']:
						if agent['buy_status'] == 'open_placed':
							#cancel hangning order
							for order in self.orderList:
								if re.match(agent['entry_id'] + '\-1b.+', order['order_link_id']):
									x = order['order_link_id'].split('=')[1]
									prevTime = int(x.split('-')[0])
									timestamp = self.currentTime
									#check 5 sec elapsed
									if timestamp - prevTime > (1000 * 2):
										#cancel order
														
										agent['received'] = False
										self.adapter.cancelOrder(order)
										start = self.currentTime
										while agent['received'] == False:
											if self.currentTime - start > 10000:
												self.logger.error(agent['entry_id']+' message never received61')
												break
											pass
										
										if order in self.orderList:
											self.orderList.remove(order)
										self.logger.info(str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] CANCEL OPENING BUY'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
										
						agent['buy_status'] = 'not_active'

					if agent['sell_status'] in ['looking_to_open', 'open_placed', 'trailing_entry']:
						if agent['sell_status'] == 'open_placed':
							#cancel hanging order
							for order in self.orderList:
								if re.match(agent['entry_id'] + '\-1s.+', order['order_link_id']):
									x = order['order_link_id'].split('=')[1]
									prevTime = int(x.split('-')[0])
									timestamp = self.currentTime
									#check 5 sec elapsed
									if timestamp - prevTime > (1000 * 2):
										#cancel order
										
										agent['received'] = False
										self.adapter.cancelOrder(order)
										start = self.currentTime
										while agent['received'] == False:
											if self.currentTime - start > 10000:
												self.logger.error(agent['entry_id']+' message never received62')
												break
											pass
										
										if order in self.orderList:
											self.orderList.remove(order)
										self.logger.info(str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] CANCEL OPENING BUY'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
									
						agent['sell_status'] = 'not_active'
								
								
			#check for delays
			if agent['recent_close_type'] == 'profit_buy' and (self.currentTime - agent['time_of_close_buy'] < (agent['delay_profit'] * 60000)):
				agent['buy_status'] = 'profit_delay'
			elif agent['buy_status'] == 'profit_delay':
				agent['buy_status'] = 'looking_to_open'
				
			if agent['recent_close_type'] == 'stop_buy' and (self.currentTime - agent['time_of_close_buy'] < (agent['delay_stop'] * 60000)):
				agent['buy_status'] = 'stop_delay'
			elif agent['buy_status'] == 'stop_delay':
				agent['buy_status'] = 'looking_to_open'
				
			if agent['recent_close_type'] == 'profit_sell' and (self.currentTime - agent['time_of_close_sell'] < (agent['delay_profit'] * 60000)):
				agent['sell_status'] = 'profit_delay'
			elif agent['sell_status'] == 'profit_delay':
				agent['sell_status'] = 'looking_to_open'
				
			if agent['recent_close_type'] == 'stop_sell' and (self.currentTime - agent['time_of_close_sell'] < (agent['delay_stop'] * 60000)):
				agent['sell_status'] = 'stop_delay'
			elif agent['sell_status'] == 'stop_delay':
				agent['sell_status'] = 'looking_to_open'

			# init lists for fetching orders
			orderIDList = []
			timeIDList = []

			##locate active orders for this agent
			for order in self.orderList:
				#look for agent
				
				#ignore orders without link id
				if len(order['order_link_id']) > 1:
					agent_id, x, user = order['order_link_id'].split("-")
				else:
					break
				ordertype, unix = x.split("=")
				if agent_id + '-' + ordertype not in orderIDList:
					orderIDList.append(agent_id + '-' + ordertype[:2])
					timeIDList.append(unix)
				# remove double entries
				else:
					agent['received'] = False
					self.adapter.cancelOrder(order)
					start = self.currentTime
					while agent['received'] == False:
						if self.currentTime - start > 10000:
							self.logger.error(agent['entry_id']+' message never received63')
							break
						pass
							
					self.logger.info(str(self.currentRSI['price'])+' | '+agent['entry_id']+' | '+'DOUBLE ENTRY CANCEL'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					if order in self.orderList:
						self.orderList.remove(order)
			
			#occasionally get key error on this call
			if agent['rsiPeriod'] in self.currentRSI: 
				rsiPerAgent = self.currentRSI[agent['rsiPeriod']]
			else:
				break
			
			##calculate unrealized pnl

			if agent['buy_status'] == 'looking_to_close' or agent['buy_status'] == 'close_placed' or agent[
				'buy_status'] == 'trailing_tp':
				agent['upnl_long'] = localLib.upnl('long', agent['opening_buy_price'], currentPrice, agent['amount'],
												   agent['entry_id'])
				self.upnlTotal += agent['upnl_long']
				if agent['upnl_long'] < agent['max_drawdown_long']:
					agent['max_drawdown_long'] = agent['upnl_long']
			else:
				agent['upnl_long'] = 0

			if agent['sell_status'] == 'looking_to_close' or agent['sell_status'] == 'close_placed' or agent[
				'sell_status'] == 'trailing_tp':
				agent['upnl_short'] = localLib.upnl('short', agent['opening_sell_price'], currentPrice, agent['amount'],
													agent['entry_id'])

				self.upnlTotal += agent['upnl_short']

				if agent['upnl_short'] < agent['max_drawdown_short']:
					agent['max_drawdown_short'] = agent['upnl_short']
			else:
				agent['upnl_short'] = 0

			if self.running:
				##check for trailing entries
				if agent['buy_status'] == 'trailing_entry':
					# trail
					if agent['long_te_price'] > (currentPrice + agent['trailing_entry']):
						agent['long_te_price'] = currentPrice + agent['trailing_entry']
						print('updating long entry', agent['entry_id'], agent['long_te_price'])
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[LONG] NEW TRAILING ENTRY TARGET' + ' | ' + 'te target:' + str(
							agent['long_te_price']) + ' | ' + 'buy status:' + agent['buy_status'] + ' | ' + 'sell status:' +
										 agent['sell_status'])

					# enter
					if currentPrice >= agent['long_te_price']:
						agent['opening_buy_price'] = currentPrice

						agent['received'] = False
						returnDict = self.adapter.placeMarketOrder(agent, 'Buy', 'Open')
						start = self.currentTime
						while agent['received'] == False:
							if self.currentTime - start > 10000:
								self.logger.error(agent['entry_id'] + ' message never received5')
								break
							pass

						self.orderActionLimit = returnDict['rate_limit_status']
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[LONG] TRAILING ENTRY TRIGGERED' + ' | ' + 'target price: ' + str(
							agent['opening_buy_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

				if agent['sell_status'] == 'trailing_entry':
					# trail
					if agent['short_te_price'] < (currentPrice - agent['trailing_entry']):
						agent['short_te_price'] = currentPrice - agent['trailing_entry']
						print('updating short entry', agent['entry_id'], agent['short_te_price'])
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[SHORT] NEW TRAILING ENTRY TARGET' + ' | ' + 'te target:' + str(
							agent['short_te_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

					# enter
					if currentPrice <= agent['short_te_price']:
						agent['opening_sell_price'] = currentPrice

						agent['received'] = False
						returnDict = self.adapter.placeMarketOrder(agent, 'Sell', 'Open')
						start = self.currentTime
						while agent['received'] == False:
							if self.currentTime - start > 10000:
								self.logger.error(agent['entry_id'] + ' message never received64')
								break
							pass

						self.orderActionLimit = returnDict['rate_limit_status']
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[SHORT] TRAILING ENTRY TRIGGERED' + ' | ' + 'target price: ' + str(
							agent['opening_sell_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

			##check for take profits
			if agent['buy_status'] == 'trailing_tp':
				# trail
				if agent['long_tp_price'] < (currentPrice - agent['trailing_tp']):
					agent['long_tp_price'] = currentPrice - agent['trailing_tp']
					print('updating long tp', agent['entry_id'], agent['long_tp_price'])
					self.logger.info(str(currentPrice) + ' | ' + agent[
						'entry_id'] + ' | ' + '[LONG] NEW TRAILING TAKE PROFIT TARGET' + ' | ' + 'ttp target:' + str(
						agent['long_tp_price']) + ' | ' + 'buy status:' + agent['buy_status'] + ' | ' + 'sell status:' +
									 agent['sell_status'])

				# take profit
				if currentPrice <= agent['long_tp_price'] and currentPrice > agent[
					'opening_buy_price'] and localLib.upnl('long', agent['opening_buy_price'], currentPrice,
														   agent['amount'], agent['entry_id']) > -1 * (
						localLib.rebate(agent['amount'], agent['opening_buy_price'], False) + localLib.rebate(
						agent['amount'], currentPrice, False)):
					agent['closing_sell_price'] = currentPrice
					
					agent['received'] = False
					returnDict = self.adapter.placeMarketOrder(agent,'Sell','Close')
					start = self.currentTime
					while agent['received'] == False:
						if self.currentTime - start > 15000:
							self.logger.error(agent['entry_id']+' message never received7')
							break
						pass
					
					self.orderActionLimit = returnDict['rate_limit_status']
					self.logger.info(str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] TAKE PROFIT TRIGGERED'+' | '+'target price: '+ str(agent['closing_sell_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					

			if agent['sell_status'] == 'trailing_tp':
				# trail
				if agent['short_tp_price'] > (currentPrice + agent['trailing_tp']):
					agent['short_tp_price'] = currentPrice + agent['trailing_tp']
					print('updating short tp', agent['entry_id'], agent['short_tp_price'])
					self.logger.info(str(currentPrice) + ' | ' + agent[
						'entry_id'] + ' | ' + '[SHORT] NEW TRAILING TAKE PROFIT TARGET' + ' | ' + 'ttp target:' + str(
						agent['short_tp_price']) + ' | ' + 'buy status:' + agent[
										 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

				# take profit
				if currentPrice >= agent['short_tp_price'] and currentPrice < agent[
					'opening_sell_price'] and localLib.upnl('short', agent['opening_sell_price'], currentPrice,
															agent['amount'], agent['entry_id']) > -1 * (
						localLib.rebate(agent['amount'], agent['opening_sell_price'], False) + localLib.rebate(
						agent['amount'], currentPrice, False)):
					agent['closing_buy_price'] = currentPrice
					
					agent['received'] = False
					returnDict = self.adapter.placeMarketOrder(agent,'Buy','Close')
					start = self.currentTime
					while agent['received'] == False:
						if self.currentTime - start > 15000:
							self.logger.error(agent['entry_id']+' message never received65')
							break
						pass
					
					self.orderActionLimit = returnDict['rate_limit_status'] 
					self.logger.info(str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] TAKE PROFIT TRIGGERED'+' | '+'target price: '+ str(agent['closing_buy_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
					
			###Place orders###############
			##CLOSES
			# closing buys with prevent exits or failed closes
			if (agent['prevent_exits'] == 'True' and rsiPerAgent <= agent['rsiOS'] and agent[
				'sell_status'] == 'looking_to_close' and currentPrice <= agent['opening_sell_price']) or agent[
				'sell_status'] == 'failed_close' or (
					agent['sell_status'] == 'looking_to_close' and agent['prevent_exits'] == 'False'):

				if agent['trailing_tp'] == 0:
					agent['received'] = False
					returnDict = self.adapter.placeLimitOrder(agent,currentPrice - (agent['offset']*agent['exit_multiplier']), 'Buy', 'Close')
					start = self.currentTime
					recd=True
					while agent['received'] == False:
						if self.currentTime - start > 10000:
							self.logger.error(agent['entry_id']+' message never received2')
							recd=False
							break
						pass
					self.orderActionLimit = returnDict['rate_limit_status']
					if recd:
						agent['closing_buy_price'] = currentPrice - (agent['offset']*agent['exit_multiplier'])
						agent['closing_buy_timestamp'] = self.currentTime
						#agent['sell_status'] = 'close_placed'
						self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
							'entry_id'] + ' | ' + '[SHORT] CLOSING BUY PLACED' + ' | ' + 'target price: ' + str(
							agent['closing_buy_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

				elif currentPrice <= agent['opening_sell_price'] - (agent['offset'] * agent['exit_multiplier']) - agent[
					'trailing_tp']:
					agent['sell_status'] = 'trailing_tp'
					agent['short_tp_price'] = currentPrice + agent['trailing_tp']
					self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
						'entry_id'] + ' | ' + '[SHORT] TRAILING TAKE PROFIT INITIATED' + ' | ' + 'target price: ' + str(
						agent['short_tp_price']) + ' | ' + 'buy status:' + agent[
										 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

			# reset failed trails
			elif agent['sell_status'] == 'trailing_tp' and currentPrice > agent['opening_sell_price']:
				agent['sell_status'] = 'looking_to_close'
				self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
					'entry_id'] + ' | ' + '[SHORT] CANCEL CLOSING BUY TTP' + ' | ' + 'buy status:' + agent[
									 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

			# closing sells with prevent exits or failed closes
			if (agent['prevent_exits'] == 'True' and rsiPerAgent >= agent['rsiOB'] and agent[
				'buy_status'] == 'looking_to_close' and currentPrice >= agent['opening_buy_price']) or agent[
				'buy_status'] == 'failed_close' or (
					agent['buy_status'] == 'looking_to_close' and agent['prevent_exits'] == 'False'):

				if agent['trailing_tp'] == 0:
					agent['received'] = False
					returnDict = self.adapter.placeLimitOrder(agent,currentPrice + (agent['offset']*agent['exit_multiplier']), 'Sell', 'Close')
					start = self.currentTime
					recd=True
					while agent['received'] == False:
						if self.currentTime - start > 10000:
							self.logger.error(agent['entry_id']+' message never received3')
							recd=False
							break
						pass
					self.orderActionLimit = returnDict['rate_limit_status']
					if recd:
						agent['closing_sell_price'] = currentPrice + (agent['offset']*agent['exit_multiplier'])
						agent['closing_sell_timestamp'] = self.currentTime
						#agent['buy_status'] = 'close_placed'
						self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
							'entry_id'] + ' | ' + '[LONG] CLOSING SELL PLACED' + ' | ' + 'target price: ' + str(
							agent['closing_sell_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

				elif currentPrice >= agent['opening_buy_price'] + (agent['offset'] * agent['exit_multiplier']) + agent[
					'trailing_tp']:
					agent['buy_status'] = 'trailing_tp'
					agent['long_tp_price'] = currentPrice - agent['trailing_tp']
					self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
						'entry_id'] + ' | ' + '[LONG] TRAILING TAKE PROFIT INITIATED' + ' | ' + 'target price: ' + str(
						agent['long_tp_price']) + ' | ' + 'buy status:' + agent['buy_status'] + ' | ' + 'sell status:' +
									 agent['sell_status'])

			# reset failed trails
			elif agent['buy_status'] == 'trailing_tp' and currentPrice < agent['opening_buy_price']:
				agent['buy_status'] = 'looking_to_close'
				self.logger.info(str(currentPrice) + ' | ' + agent[
					'entry_id'] + ' | ' + '[LONG] CANCEL OFFSET RANGE DUE TO RSI. RECALIBRATING' + ' | ' + 'buy status:' +
								 agent['buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

			##OPENING BUYS
			if self.running:
				# opening buys with prevent entries
				if agent['prevent_entries'] == 'True' and rsiPerAgent <= agent['rsiOS'] and agent[
					'buy_status'] == 'looking_to_open':

					if agent['trailing_entry'] == 0:
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
								int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['received'] = False
							recd=True
							returnDict = self.adapter.placeLimitOrder(agent, currentPrice - (
										agent['offset'] * agent['entry_multiplier']), 'Buy', 'Open')
							start = self.currentTime
							while agent['received'] == False:
								if self.currentTime - start > 10000:
									self.logger.error(agent['entry_id'] + ' message never received31')
									recd=False
									break
								pass
							self.orderActionLimit = returnDict['rate_limit_status']
							#agent['buy_status'] = 'open_placed'
							if recd:
								agent['opening_buy_price'] = currentPrice - (agent['offset'] * agent['entry_multiplier'])
								agent['opening_buy_timestamp'] = self.currentTime
								self.logger.info(str(currentPrice) + ' | ' + agent[
									'entry_id'] + ' | ' + '[LONG] OPENING BUY PLACED' + ' | ' + 'target price: ' + str(
									agent['opening_buy_price']) + ' | ' + 'buy status:' + agent[
													 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

					elif agent['lte_target'] == 'None':
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
								int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['lte_target'] = currentPrice - (agent['entry_multiplier'] * agent['offset']) - agent[
								'trailing_entry']
							agent['lte_timestamp'] = self.currentTime
							self.logger.info(str(currentPrice) + ' | ' + agent[
								'entry_id'] + ' | ' + '[LONG] OFFSET RANGE ESTABLISHED' + ' | ' + 'base target:' + str(
								agent['lte_target']) + ' | ' + 'buy status:' + agent[
												 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

					elif currentPrice <= agent['lte_target']:
						agent['buy_status'] = 'trailing_entry'
						agent['long_te_price'] = currentPrice + agent['trailing_entry']
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[LONG] TRAILING ENTRY INITIATED' + ' | ' + 'te target:' + str(
							agent['long_te_price']) + ' | ' + 'buy status:' + agent['buy_status'] + ' | ' + 'sell status:' +
										 agent['sell_status'])

				# opening buys without prevent entries
				if agent['prevent_entries'] == 'False' and agent['buy_status'] == 'looking_to_open':

					if agent['trailing_entry'] == 0:
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
								int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['received'] = False
							recd=True
							returnDict = self.adapter.placeLimitOrder(agent, currentPrice - (
										agent['offset'] * agent['entry_multiplier']), 'Buy', 'Open')
							start = self.currentTime
							while agent['received'] == False:
								if self.currentTime - start > 10000:
									self.logger.error(agent['entry_id'] + ' message never received33')
									recd=False
									break
								pass
							self.orderActionLimit = returnDict['rate_limit_status']
							#agent['buy_status'] = 'open_placed'
							if recd:
								agent['opening_buy_price'] = currentPrice - (agent['offset'] * agent['entry_multiplier'])
								agent['opening_buy_timestamp'] = self.currentTime
								self.logger.info(str(currentPrice) + ' | ' + agent[
									'entry_id'] + ' | ' + '[LONG] OPENING BUY PLACED' + ' | ' + 'target price: ' + str(
									agent['opening_buy_price']) + ' | ' + 'buy status:' + agent[
													 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

					elif agent['lte_target'] == 'None':
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
								int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['lte_target'] = currentPrice - (agent['entry_multiplier'] * agent['offset']) - agent[
								'trailing_entry']
							agent['lte_timestamp'] = self.currentTime
							self.logger.info(str(currentPrice) + ' | ' + agent[
								'entry_id'] + ' | ' + '[LONG] OFFSET RANGE ESTABLISHED' + ' | ' + 'base target:' + str(
								agent['lte_target']) + ' | ' + 'buy status:' + agent[
												 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])


					elif currentPrice <= agent['lte_target']:
						agent['buy_status'] = 'trailing_entry'
						agent['long_te_price'] = currentPrice + agent['trailing_entry']
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[LONG] TRAILING ENTRY INITIATED' + ' | ' + 'te target:' + str(
							agent['long_te_price']) + ' | ' + 'buy status:' + agent['buy_status'] + ' | ' + 'sell status:' +
										 agent['sell_status'])

				# cancel unfilled buys
				if agent['prevent_entries'] == 'True' and rsiPerAgent > agent['rsiOS'] and (
						agent['buy_status'] == 'open_placed' or agent['buy_status'] == 'looking_to_open'):

					if agent['trailing_entry'] == 0:
						# locate order
						for order in self.orderList:
							if re.match(agent['entry_id'] + '\-1b.+', order['order_link_id']):
								x = order['order_link_id'].split('=')[1]
								prevTime = int(x.split('-')[0])
								timestamp = self.currentTime
								# check 5 sec elapsed
								if timestamp - prevTime > (1000 * 5):
									# cancel order

									agent['received'] = False
									self.adapter.cancelOrder(order)
									start = self.currentTime
									while agent['received'] == False:
										if self.currentTime - start > 10000:
											self.logger.error(agent['entry_id'] + ' message never received66')
											break
										pass

									self.logger.info(str(currentPrice) + ' | ' + agent[
										'entry_id'] + ' | ' + '[LONG] CANCEL OPENING BUY' + ' | ' + 'buy status:' + agent[
														 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])
									if order in self.orderList:
										self.orderList.remove(order)

					elif agent['lte_target'] != 'None':
						agent['buy_status'] = 'looking_to_open'
						agent['long_te_price'] = 100000000
						agent['lte_target'] = 'None'
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[LONG] CANCEL OFFSET RANGE DUE TO RSI. RECALIBRATING' + ' | ' + 'buy status:' +
										 agent['buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

				##OPENING SELLS

				# opening sells with prevent entries
				if agent['prevent_entries'] == 'True' and rsiPerAgent >= agent['rsiOB'] and agent[
					'sell_status'] == 'looking_to_open':

					if agent['trailing_entry'] == 0:
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
								int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['received'] = False
							recd=True
							returnDict = self.adapter.placeLimitOrder(agent, currentPrice + (
										agent['offset'] * agent['entry_multiplier']), 'Sell', 'Open')
							start = self.currentTime
							while agent['received'] == False:
								if self.currentTime - start > 10000:
									self.logger.error(agent['entry_id'] + ' message never received34')
									recd=False
									break
								pass
							self.orderActionLimit = returnDict['rate_limit_status']
							#agent['sell_status'] = 'open_placed'
							if recd:
								agent['opening_sell_price'] = currentPrice + (agent['offset'] * agent['entry_multiplier'])
								agent['opening_sell_timestamp'] = self.currentTime
								self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
									'entry_id'] + ' | ' + '[SHORT] OPENING SELL PLACED' + ' | ' + 'target price: ' + str(
									agent['opening_sell_price']) + ' | ' + 'buy status:' + agent[
													 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

					elif agent['ste_target'] == 'None':
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
								int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['ste_target'] = currentPrice + (agent['entry_multiplier'] * agent['offset']) + agent[
								'trailing_entry']
							agent['ste_timestamp'] = self.currentTime
							self.logger.info(str(currentPrice) + ' | ' + agent[
								'entry_id'] + ' | ' + '[SHORT] OFFSET RANGE ESTABLISHED' + ' | ' + 'base target:' + str(
								agent['ste_target']) + ' | ' + 'buy status:' + agent[
												 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])


					elif currentPrice >= agent['ste_target']:
						agent['sell_status'] = 'trailing_entry'
						agent['short_te_price'] = currentPrice - agent['trailing_entry']
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[SHORT] TRAILING ENTRY INITIATED' + ' | ' + 'te target:' + str(
							agent['short_te_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

				# opening sells without prevent entries
				if agent['prevent_entries'] == 'False' and agent['sell_status'] == 'looking_to_open':

					if agent['trailing_entry'] == 0:
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
								int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['received'] = False
							recd=True
							returnDict = self.adapter.placeLimitOrder(agent, currentPrice + (
										agent['offset'] * agent['entry_multiplier']), 'Sell', 'Open')
							start = self.currentTime
							while agent['received'] == False:
								if self.currentTime - start > 10000:
									self.logger.error(agent['entry_id'] + ' message never received1')
									recd=False
									break
								pass
							self.orderActionLimit = returnDict['rate_limit_status']
							#agent['sell_status'] = 'open_placed'
							if recd:
								agent['opening_sell_price'] = currentPrice + (agent['offset'] * agent['entry_multiplier'])
								agent['opening_sell_timestamp'] = self.currentTime
								self.logger.info(str(currentPrice) + ' | ' + agent[
									'entry_id'] + ' | ' + '[SHORT] OPENING SELL PLACED' + ' | ' + 'target price: ' + str(
									agent['opening_sell_price']) + ' | ' + 'buy status:' + agent[
													 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

					elif agent['ste_target'] == 'None':
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
								int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['ste_target'] = currentPrice + (agent['entry_multiplier'] * agent['offset']) + agent[
								'trailing_entry']
							agent['ste_timestamp'] = self.currentTime
							self.logger.info(str(currentPrice) + ' | ' + agent[
								'entry_id'] + ' | ' + '[SHORT] OFFSET RANGE ESTABLISHED' + ' | ' + 'base target:' + str(
								agent['ste_target']) + ' | ' + 'buy status:' + agent[
												 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

					elif currentPrice >= agent['ste_target']:
						agent['sell_status'] = 'trailing_entry'
						agent['short_te_price'] = currentPrice - agent['trailing_entry']
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[SHORT] TRAILING ENTRY INITIATED' + ' | ' + 'te target:' + str(
							agent['short_te_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

				# cancel unfilled sells
				if agent['prevent_entries'] == 'True' and rsiPerAgent < agent['rsiOB'] and (
						agent['sell_status'] == 'open_placed' or agent['sell_status'] == 'looking_to_open'):

					if agent['trailing_entry'] == 0:
						# check all orders
						for order in self.orderList:
							# order exists
							if re.match(agent['entry_id'] + '\-1s.+', order['order_link_id']):
								x = order['order_link_id'].split('=')[1]
								prevTime = int(x.split('-')[0])
								timestamp = self.currentTime
								# check 5 sec elapsed
								if timestamp - prevTime > (1000 * 5):

									# cancel order

									agent['received'] = False
									self.adapter.cancelOrder(order)
									start = self.currentTime
									while agent['received'] == False:
										if self.currentTime - start > 10000:
											self.logger.error(agent['entry_id'] + ' message never received67')
											break
										pass

									self.logger.info(str(currentPrice) + ' | ' + agent[
										'entry_id'] + ' | ' + '[SHORT] CANCEL OPENING SELL' + ' | ' + 'buy status:' + agent[
														 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])
									if order in self.orderList:
										self.orderList.remove(order)

					elif agent['ste_target'] != 'None':

						agent['sell_status'] = 'looking_to_open'
						agent['short_te_price'] = 0
						agent['ste_target'] = 'None'
						self.logger.info(str(currentPrice) + ' | ' + agent[
							'entry_id'] + ' | ' + '[SHORT] CANCEL OFFSET RANGE DUE TO RSI. RECALIBRATING' + ' | ' + 'buy status:' +
										 agent['buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

				# opening buy timeout
				##locate active orders for this agent

				if agent['entry_id'] + '-1b' in orderIDList:
					# map index to timeIDList
					mapIndex = orderIDList.index(agent['entry_id'] + '-1b')

					if agent['entry_timeout'] != 0 and (agent['entry_timeout'] * 60000) < (
							self.currentTime - agent['opening_buy_timestamp']):

						# find order
						for order in self.orderList:
							if re.match(agent['entry_id'] + '\-1b.+', order['order_link_id']):

								# replace method only accepts generic order id
								genericOrderID = order['order_id']

								if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
										int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
									
									#commented out because when params not modified er30076, get no confirm on listen
									#agent['received'] = False
									self.adapter.replaceOrder(agent, currentPrice, genericOrderID, '1b')
									time.sleep(1)
									#start = self.currentTime
									#while agent['received'] == False:
									#	if self.currentTime - start > 10000:
									#		self.logger.error(agent['entry_id'] + ' message never received69')
									#		break
									#	pass

									agent['opening_buy_price'] = currentPrice - (
												agent['offset'] * agent['entry_multiplier'])
									agent['opening_buy_timestamp'] = self.currentTime
									self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
										'entry_id'] + ' | ' + '[LONG] TIMEOUT OPENING BUY' + ' | ' + 'buy status:' + agent[
														 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])
								else:

									agent['received'] = False
									self.adapter.cancelOrder(order)
									start = self.currentTime
									while agent['received'] == False:
										if self.currentTime - start > 10000:
											self.logger.error(agent['entry_id'] + ' message never received68')
											break
										pass

									if order in self.orderList:
										self.orderList.remove(order)

				# reset offset target
				elif agent['buy_status'] == 'looking_to_open' and agent['lte_target'] != 'None' and currentPrice > agent[
					'lte_target']:
					if (agent['entry_timeout'] * 60000) < (self.currentTime - agent['lte_timestamp']):
						agent['lte_target'] = 'None'
						agent['long_te_price'] = 100000000
						self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
							'entry_id'] + ' | ' + '[LONG] OFFSET TARGET TIMED OUT. RECALIBRATING' + ' | ' + 'buy status:' +
										 agent['buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

				# opening sell timeout
				if agent['entry_id'] + '-1s' in orderIDList:

					# map index to timeIDList
					mapIndex = orderIDList.index(agent['entry_id'] + '-1s')

					if agent['entry_timeout'] != 0 and (agent['entry_timeout'] * 60000) < (
							self.currentTime - agent['opening_sell_timestamp']):

						# find order
						for order in self.orderList:
							if re.match(agent['entry_id'] + '\-1s.+', order['order_link_id']):

								# replace method only accepts generic order id
								genericOrderID = order['order_id']

								if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (
										int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):

									#commented out because when params not modified er30076, get no confirm on listen
									#agent['received'] = False
									self.adapter.replaceOrder(agent, currentPrice, genericOrderID, '1s')
									time.sleep(1)
									#start = self.currentTime
									#while agent['received'] == False:
									#	if self.currentTime - start > 10000:
									#		self.logger.error(agent['entry_id'] + ' message never received60')
									#		break
									#	pass

									agent['opening_sell_price'] = currentPrice + (
												agent['offset'] * agent['entry_multiplier'])
									agent['opening_sell_timestamp'] = self.currentTime
									self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
										'entry_id'] + ' | ' + '[SHORT] TIMEOUT OPENING SELL' + ' | ' + 'buy status:' +
													 agent['buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])
								else:

									agent['received'] = False
									self.adapter.cancelOrder(order)
									start = self.currentTime
									while agent['received'] == False:
										if self.currentTime - start > 10000:
											self.logger.error(agent['entry_id'] + ' message never received6x')
											break
										pass

									if order in self.orderList:
										self.orderList.remove(order)

				# reset offset target
				elif agent['sell_status'] == 'looking_to_open' and agent['ste_target'] != 'None' and currentPrice < agent[
					'ste_target']:
					if (agent['entry_timeout'] * 60000) < (self.currentTime - agent['ste_timestamp']):
						agent['ste_target'] = 'None'
						agent['short_te_price'] = 0
						self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
							'entry_id'] + ' | ' + '[SHORT] OFFSET TARGET TIMED OUT. RECALIBRATING' + ' | ' + 'buy status:' +
										 agent['buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

			# closing buy timeout
			if agent['entry_id'] + '-2b' in orderIDList:

				# map index to timeIDList
				mapIndex = orderIDList.index(agent['entry_id'] + '-2b')
				
				if agent['exit_timeout'] != 0 and (agent['exit_timeout'] * 60000) < (self.currentTime - int(timeIDList[mapIndex])) and agent['closing_buy_timed'] == 'False':
					
				
					for order in self.orderList:
						if re.match(agent['entry_id'] + '\-2b.+', order['order_link_id']):

							# replace method only accepts generic order id
							genericOrderID = order['order_id']
							agent['received'] = False
							recd=True
							self.adapter.replaceOrder(agent, currentPrice, genericOrderID, '2b')
							start = self.currentTime
							while agent['received'] == False:
								if self.currentTime - start > 10000:
									self.logger.error(agent['entry_id'] + ' message never received6e')
									recd=False
									break
								pass
							
							if recd:
								agent['closing_buy_timed'] = 'True'
								agent['closing_buy_price'] = agent['opening_sell_price']
								self.logger.info(str(self.currentRSI['price']) + ' | ' + agent['entry_id'] + ' | ' + '[SHORT] TIMEOUT CLOSING BUY' + ' | ' + 'buy status:' + agent['buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

			# closing sell timeout
			if agent['entry_id'] + '-2s' in orderIDList:

				# map index to timeIDList
				mapIndex = orderIDList.index(agent['entry_id'] + '-2s')
				
				if agent['exit_timeout'] != 0 \
					and (agent['exit_timeout'] * 60000) < (self.currentTime - int(timeIDList[mapIndex])) \
					and	agent['closing_sell_timed'] == 'False':
					
					for order in self.orderList:
						if re.match(agent['entry_id'] + '\-2s.+', order['order_link_id']):

							# replace method only accepts generic order id
							genericOrderID = order['order_id']
							agent['received'] = False
							recd=True
							self.adapter.replaceOrder(agent,currentPrice,genericOrderID, '2s')
							start = self.currentTime
							while agent['received'] == False:
								if self.currentTime - start > 10000:
									self.logger.error(agent['entry_id']+' message never received6j')
									recd=False
									break
								pass
							
							if recd:
								agent['closing_sell_timed'] = 'True'
								agent['closing_sell_price'] = agent['opening_buy_price']
								self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
									'entry_id'] + ' | ' + '[LONG] TIMEOUT CLOSING SELL' + ' | ' + 'buy status:' + agent[
													 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

			# check for stop losses
			if agent['stop_loss'] != 0:
				
				if agent['buy_status'] in ['looking_to_close', 'close_placed' , 'trailing_tp']:
					if currentPrice < agent['opening_buy_price'] - agent['stop_loss']:
						
						#cancel exit if close placed
						if agent['buy_status'] == 'close_placed':
							agent['buy_status'] = 'stop_loss'
							for order in self.orderList:
								if re.match(agent['entry_id'] + '\-2s.+', order['order_link_id']):
									
									agent['received'] = False
									self.adapter.cancelOrder(order)
									start = self.currentTime
									while agent['received'] == False:
										if self.currentTime - start > 10000:
											self.logger.error(agent['entry_id']+' message never received6q')
											break
										pass
									
									if order in self.orderList:
										self.orderList.remove(order)
									self.logger.info(str(self.currentRSI['price'])+' | '+agent['entry_id']+' | '+'[LONG] STOP LOSS DETECTED. MUST CANCEL EXISTING ORDER'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])

						agent['closing_sell_price'] = currentPrice
						agent['received'] = False
						returnDict = self.adapter.placeMarketOrder(agent,'Sell', 'Close')
						start = self.currentTime
						while agent['received'] == False:
							if self.currentTime - start > 15000:
								self.logger.error(agent['entry_id']+' message never received4')
								break
							pass
						self.orderActionLimit = returnDict['rate_limit_status']
						self.logger.info(str(self.currentRSI['price'])+' | '+agent['entry_id']+' | '+'[LONG] CLOSING SELL STOP LOSS'+' | '+'target price: '+ str(agent['closing_sell_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
						
						
						
									
				if agent['sell_status'] in ['looking_to_close', 'close_placed' , 'trailing_tp']:
					if currentPrice > agent['opening_sell_price'] + agent['stop_loss']:
						
						#cancel exit if close placed
						if agent['sell_status'] == 'close_placed':
							agent['sell_status'] = 'stop_loss'
							for order in self.orderList:
								if re.match(agent['entry_id'] + '\-2b.+', order['order_link_id']):
									
									agent['received'] = False
									self.adapter.cancelOrder(order)
									start = self.currentTime
									while agent['received'] == False:
										if self.currentTime - start > 10000:
											self.logger.error(agent['entry_id'] + ' message never received6r')
											break
										pass

									if order in self.orderList:
										self.orderList.remove(order)
									self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
										'entry_id'] + ' | ' + '[SHORT] STOP LOSS DETECTED. MUST CANCEL EXISTING ORDER' + ' | ' + 'buy status:' +
													 agent['buy_status'] + ' | ' + 'sell status:' + agent[
														 'sell_status'])

						agent['closing_buy_price'] = currentPrice

						agent['received'] = False
						returnDict = self.adapter.placeMarketOrder(agent, 'Buy', 'Close')
						start = self.currentTime
						while agent['received'] == False:
							if self.currentTime - start > 20000:
								self.logger.error(agent['entry_id'] + ' message never received41')
								break
							pass

						self.orderActionLimit = returnDict['rate_limit_status']
						self.logger.info(str(self.currentRSI['price']) + ' | ' + agent[
							'entry_id'] + ' | ' + '[SHORT] CLOSING BUY STOP LOSS' + ' | ' + 'target price: ' + str(
							agent['closing_buy_price']) + ' | ' + 'buy status:' + agent[
											 'buy_status'] + ' | ' + 'sell status:' + agent['sell_status'])

		###print to stdout
		
		if self.primary and self.stopTradingTriggered == False:
			subD = {}
			self.primaryCounter+=1
			for theKeys in self.currentRSI:
				if theKeys != 'price':
					subD[theKeys] = round(self.currentRSI[theKeys],2)
			print('Price: ', self.currentRSI['price'], ' ||   TRS Values: ', subD)
			
			#fetch equity for pnl calc
			if self.primaryCounter % 5 == 0:
				while True:
					try:
						with open('../dumps/equity.csv','a') as eqf:
							returnInfo = self.adapter.fetchLeverage()
							newLev = returnInfo[0]
							newSide = returnInfo[1]
							newSize = returnInfo[2]
							newEntry = returnInfo[3]
							newEquity = self.adapter.fetchEquity(self.asset.upper())
							newTime = self.currentTime
							eqf.write(str(newLev)+','+newSide+','+str(newSize)+','+str(newEntry)+','+str(newEquity)+','+str(newTime)+'\n')
							
						break
					except:
						time.sleep(0.1)
		avgEntryLongAmount = []
		avgEntryLongPrice = []
		avgEntryShortAmount = []
		avgEntryShortPrice = []
		for k in self.avgEntry:
			if self.avgEntry[k]['long']['amount'] != 0:
				avgEntryLongAmount.append(self.avgEntry[k]['long']['amount'])
				avgEntryLongPrice.append(self.avgEntry[k]['long']['price'])
			if self.avgEntry[k]['short']['amount'] != 0:
				avgEntryShortAmount.append(self.avgEntry[k]['short']['amount'])
				avgEntryShortPrice.append(self.avgEntry[k]['short']['price'])
		if len(avgEntryLongAmount) != 0:
			entryCumLong = [x * y for x, y in zip(avgEntryLongAmount, avgEntryLongPrice)]
		else:
			entryCumLong = []
		if len(avgEntryShortAmount) != 0:
			entryCumShort = [x * y for x, y in zip(avgEntryShortAmount, avgEntryShortPrice)]
		else:
			entryCumShort = []

		if sum(avgEntryLongAmount + avgEntryShortAmount) != 0:
			entryAvg = sum(entryCumLong + entryCumShort) / sum(avgEntryLongAmount + avgEntryShortAmount)
		else:
			entryAvg = 0
		
		while True:
			try:
				with open(f'../dumps/{self.botNumber}/avgEntry.pickle', 'wb+') as handle:
					pickle.dump({'avgEntry': entryAvg,
								 'pos': -sum(avgEntryShortAmount) + sum(avgEntryLongAmount)}, handle)
				break
			except:
				time.sleep(0.1)
		pd.DataFrame(self.offsetTable).to_csv('../dumps/' + str(self.botNumber) + '/runningTable.csv', index=False)
		pd.DataFrame(self.orderList).to_csv('../dumps/' + str(self.botNumber) + '/orderDump.csv', index=False)
		levResponse =self.adapter.fetchLeverage()
		self.leverage = levResponse[0]
		self.side = levResponse[1]

		while True:
			try:
				with open(f'../dumps/{self.botNumber}/pnls.pickle', 'rb') as handle:
					price = pickle.load(handle)
				break
			except:
				time.sleep(0.1)

		price['rpnl'] = self.profit
		price['upnl'] = self.upnlTotal
		price['net'] = self.profit + self.upnlTotal
		
		while True:
			try:
				with open('../dumps/pnls.pickle', 'wb+') as handle:
					pickle.dump(price, handle)
				break
			except:
				time.sleep(0.1)
				
		if self.leverageConfig == 0 and self.stopTradingTrigger != 0 and self.leverage > self.stopTradingTrigger and self.stopTradingTriggered == False:
			self.adapter.fetchOrders()
			self.adapter.cancelHalf()
			print('stop trading trigger activated... final leverage recorded:   ' + str(self.leverage))
			self.logger.error('stop trading trigger activated... final leverage recorded:   ' + str(self.leverage))
			time.sleep(5)
			for agents in self.offsetTable:
				agents['sell_status'] = 'not_active'
				agents['buy_status'] = 'not_active'
			self.stopTradingTriggered = True
			
		if self.leverageConfig == 0 and self.killEmergencyTrigger != 0 and self.leverage > self.killEmergencyTrigger:

			self.adapter.cancelAll()
			print('kill switch activated... final leverage recorded:   ' + str(self.leverage))
			self.logger.error('kill switch activated... final leverage recorded:   ' + str(self.leverage))

			curRet = self.adapter.fetchPosition()
			curPos = curRet[0]
			curSide = curRet[1]
			if curSide == 'Buy':
				curSide = 'Sell'
			elif curSide == 'Sell':
				curSide = 'Buy'
			if self.primary:
				self.adapter.closePosMarket(curPos, curSide)
			sys.exit()

	def _runLive(self):
		while True:
			if not self.running:
				pass
			else:
				if self.newPrice == True:
					try:
						self.liveOrders()
						self.newPrice = False

					except Exception as e:
						if re.search('.+1006.+',str(e)):
							print('connection lost, please wait for reconnect')
						else:
							self.logger.error(traceback.format_exc())
							self.logger.error(str(e) + '_____from _runLive')
							time.sleep(1)
	
	def runLive(self):
		try:
			self._runLive()
		except Exception as e:
			print('live', e)
			self.logger.error(str(e) + '_____from runLive')
			self.logger.error(traceback.format_exc())
			self.logger.warning("Exiting in 30 seconds...")
			time.sleep(30)

	# ----------------------------------------------------------------------------------------------------------------------

	# ----------------------------------------------------------------------------------------------------------------------
	# Bot "run" functionality
	def runCallback(self):
		#  spawn off threads for each specific task
		if self.primary and not self.globalStarted:
			
			
			self.adapter.cancelAll()
			
			startingLev = self.adapter.fetchLeverage()[0]
			#switch from iso to cross or cross to iso
			if (startingLev != 0 and self.leverageConfig == 0) or (startingLev == 0 and self.leverageConfig != 0):
				self.adapter.switchLeverage(self.leverageConfig)
			if self.leverageConfig != 0:
				self.adapter.setLeverage(self.leverageConfig)
		threads = [self.runRsi, self.runLive, self.runListenOrders, self.runListenExecution]
		for thread in threads:
			t = threading.Thread(target=thread, args=())
			t.start()

	# ----------------------------------------------------------------------------------------------------------------------

	# ----------------------------------------------------------------------------------------------------------------------
	# Bot start
	# Thread start mandatory override
	def start(self):
		self.paused = True
		self.connectOracle(self.runCallback)

	# ----------------------------------------------------------------------------------------------------------------------
	def globalStart(self,message):
		self.globalStarted = message
		
	def resume(self):
		self.running = True
	
	def makePrimary(self):
		self.primary = True
	
	def makeSecondary(self):
		self.primary = False
	# ----------------------------------------------------------------------------------------------------------------------
	# Bot stop
	def stop(self):
		self.running = False
		self.primary = False
		self.logger.info("Shut down requested.")
		time.sleep(3)
		self.adapter.fetchOrders()
		self.offsetTable = self.adapter.cancelOpens(self.offsetTable)
		for agent in self.offsetTable:
			if agent['sell_status'] in ['trailing_entry','looking_to_close']:
				agent['sell_status'] = 'looking_to_open'
			if agent['buy_status'] in ['trailing_entry','looking_to_close']:
				agent['buy_status'] = 'looking_to_open'
		pd.DataFrame(self.offsetTable).to_csv('../dumps/' + str(self.botNumber) + '/runningTable.csv', index=False)
		pd.DataFrame(self.orderList).to_csv('../dumps/' + str(self.botNumber) + '/orderDump.csv', index=False)
