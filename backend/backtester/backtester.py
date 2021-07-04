
import live_functions as localLib
#import tulipy
import time
import numpy as np
import logging
import os
import glob
import pandas as pd
import ta
if os.path.exists('results'):
	os.system('rmdir -r results')
os.system('mkdir results')

if os.path.exists('logs'):
	os.system('rmdir -r logs')
os.system('mkdir logs')
inputs = glob.glob('time/*')
index = 0
for ins in inputs:
	
	index+=1
	if os.path.exists('logs/log_file'+str(index)+'.log'):
		os.remove('logs/log_file'+str(index)+'.log')
	logFormatter = logging.Formatter('%(asctime)s | %(thread)x | %(name)5s | %(levelname)5s | %(message)s')
	handler = logging.FileHandler('logs/log_file'+str(index)+'.log')        
	handler.setFormatter(logFormatter)
	logger = logging.getLogger('main')
	logger.setLevel(logging.INFO)
	logger.addHandler(handler)

	timePriceOut = open('results/timePriceSeries'+str(index)+'.csv','w')
	completedTrades = open('results/completedTrades'+str(index)+'.csv','w')
	
	#load historical data
	timeSeries = []
	with open(ins,'r') as timeFile:
		for lines in timeFile:
			lines = lines.rstrip().split(',')
			if lines[4] != 'close':
				item = {}
				item['time'] = int(lines[0])
				item['close'] = float(lines[4])
				item['open'] = float(lines[1])
				item['low'] = float(lines[3])
				item['high'] = float(lines[2])
				if lines[5] != 'NaN':
					item['volume'] = float(lines[5])
				else:
					item['volume'] = 1000
				timeSeries.append(item)
		
		
	#load current agents
	initPrice = timeSeries[0]['open']
	offsetTable = localLib.offsetTable('agents.csv',1,initPrice)
	
		
	#extract rsi periods and convert time to seconds
	rsiPeriods = []
	for agents in offsetTable:
		if agents['rsiPeriod'] not in rsiPeriods:
			rsiPeriods.append(agents['rsiPeriod'])
		agents['entry_timeout'] = agents['entry_timeout'] * 60
		agents['exit_timeout'] = agents['exit_timeout'] * 60
			
	#init metrics for ml
	for agents in offsetTable:
		agents['avg_drawdown'] = 0
		agents['avg_spread'] = 0
		agents['avg_duration'] = 0
		agents['trade_counter'] = 0
		
		
	#loop through time
	currentTime=0
	currentTRS = {}
	for periods in rsiPeriods:
		currentTRS[periods] = 50
	orderList = []
	totalProfit = 0
	maxCumDD = 0
	minVol = 0
	minHigh = 0
	minLow = 1000000
	minClose = 0
	minOpen = 0
	minuteCandles = []
	for timePoint in timeSeries:#[200:]:
		currentTime+=1
		currentPrice = timePoint['close']
		timePriceOut.write(str(currentTime) + ',' + str(currentPrice) + '\n')
		
		#new minute candle, calculate trs
		if timePoint['time']%60 == 0:
			#print('new minute',timePoint['time'], minClose)
			minuteCandles.append([minOpen,minHigh,minLow,minClose,minVol])
			if len(minuteCandles) > 300:
				minuteCandles.pop(0)
			highs = [time[1] for time in minuteCandles]
			lows = [time[2] for time in minuteCandles]
			closes = [time[3] for time in minuteCandles]
			volumes = [time[4] for time in minuteCandles]
			taInput1 = pd.Series(highs)
			taInput2 = pd.Series(lows)
			taInput3 = pd.Series(closes)
			taInput4 = pd.Series(volumes)
			
			for periods in rsiPeriods:
				if len(minuteCandles) > periods:
					taRSI = ta.momentum.RSIIndicator(taInput3, int(periods), True).rsi()
					taMFI = ta.volume.MFIIndicator(taInput1, taInput2, taInput3, taInput4, int(periods), True).money_flow_index()
					trs = (taRSI.iloc[-1] + taMFI.iloc[-1]) / 2
					currentTRS[periods] = trs
				else:
					currentTRS[periods] = 50
					
			#print('trs values',currentTRS)
			minVol = timePoint['volume']
			minOpen = timePoint['close']
			minClose = timePoint['close']
			minHigh = timePoint['close']
			minLow = timePoint['close']
		else:
			minVol += timePoint['volume']
			minClose = timePoint['close']
			if timePoint['high'] > minHigh:
				minHigh = timePoint['high']
			if timePoint['low'] < minLow:
				minLow = timePoint['low']
		
			
		##check for filled limit orders
		for orders in orderList:
				if orders[2] == 'Buy' and timePoint['low'] < orders[3]:
					for agents in offsetTable:
						if agents['entry_id'] == orders[0]:
							#opening buy filled
							if orders[1] == 'Open':
								agents['opening_buy_price'] = currentPrice
								agents['opening_buy_timestamp'] = currentTime
								if agents['trailing_entry'] == 0:
									rebate = localLib.rebate(agents['amount'],agents['opening_buy_price'],True)
									agents['rpnl_long'] += rebate
									totalProfit += rebate
									agents['trade_profit_long'] += rebate
								else:
									rebate = localLib.rebate(agents['amount'],agents['opening_buy_price'],False)
									agents['rpnl_long'] += rebate
									totalProfit += rebate
									agents['trade_profit_long'] += rebate
								agents['buy_status'] = 'looking_to_close'
								agents['lte_target'] = 'None'
								agents['long_te_price'] = 1000000000
								orderList.remove(orders)
								print('opening buy filled',agents['entry_id'])
								logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agents['entry_id']+' | '+'[LONG] OPENING BUY FILLED'+' | '+'fill price: '+ str(agents['opening_buy_price']) + ' | ' +'buy status:'+agents['buy_status']+' | '+'sell status:'+agents['sell_status'])
								
							#closing buy filled
							elif orders[1] == 'Close':
								agents['closing_buy_timestamp'] = currentTime
								agents['closing_buy_price'] = orders[3]
								agents['time_total_trade'] = (agents['closing_buy_timestamp'] - agents['init_sell_timestamp'])
			
								if agents['trailing_tp'] == 0:
									rebate = localLib.rebate(agents['amount'], agents['closing_buy_price'], True)
									agents['rpnl_short'] += rebate
									totalProfit += rebate
									agents['trade_profit_short'] += rebate
								else:
									rebate = localLib.rebate(agents['amount'], agents['closing_buy_price'], False)
									agents['rpnl_short'] += rebate
									totalProfit += rebate
									agents['trade_profit_short'] += rebate
								rpnl = localLib.upnl('short', agents['opening_sell_price'], agents['closing_buy_price'],
													 agents['amount'], agents['entry_id'])
								
								if rpnl > 0:
									agents['recent_close_type'] = 'profit_sell'
								else:
									agents['recent_close_type'] = 'stop_sell'
								agents['rpnl_short'] += rpnl
								totalProfit += rpnl
								agents['trade_profit_short'] += rpnl
								if agents['max_drawdown_short'] == 0:
									agents['max_drawdown_short'] = 0.000001
								if agents['time_total_trade'] <= 0:
									agents['time_total_trade'] = 1
								
								agents['fitness_score'] = localLib.fitnessScore(agents['trade_profit_short'],
																			   agents['max_drawdown_short'],
																			   agents['time_total_trade'], agents['amount'])
								
								agents['offset_ratio'] = (agents['exit_multiplier'] * agents['offset']) / (
										agents['closing_buy_price'] + agents['exit_multiplier'] * agents['offset'])
								
								agents['trade_counter'] = agents['trade_counter'] + 1
								agents['avg_drawdown'] = (agents['avg_drawdown'] + agents['max_drawdown_short'])/ (agents['trade_counter'])
								agents['avg_spread'] = (agents['avg_spread'] + ((abs(agents['opening_sell_price'] - agents['closing_buy_price']) / ((agents['opening_sell_price'] + agents['closing_buy_price']) /2))*100)) / (agents['trade_counter'])
								agents['avg_duration'] = (agents['avg_duration'] + agents['time_total_trade'] )/ (agents['trade_counter'])
								
								completedTrades.write(agents['entry_id'] + ',' + 'Short' + ',' + str(agents['opening_sell_price']) + ',' + str(agents['opening_sell_timestamp']) + ',' + str(agents['closing_buy_price']) + ',' + str(currentTime) + ',' + str(agents['fitness_score']) + '\n')
								logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agents['entry_id']+' | '+'[SHORT] CLOSING BUY FILLED'+' | '+'fill price: '+ str(agents['closing_buy_price']) + ' | ' +'buy status:'+agents['buy_status']+' | '+'sell status:'+agents['sell_status'])
								print('closing buy filled',agents['entry_id'])
								
								agents['sell_status'] = 'looking_to_open'
								agents['opening_sell_price'] = 0.
								agents['opening_sell_timestamp'] = 0
								agents['closing_buy_timestamp'] = 0
								agents['closing_buy_timed'] = 'False'
								agents['closing_buy_price'] = 0
								agents['upnl_short'] = 0
								agents['init_sell_timestamp'] = currentTime
								agents['time_of_close_sell'] = currentTime
								agents['sells_counter'] += 1
								agents['max_drawdown_short'] = 0
								agents['short_tp_price'] = 100000000
								agents['short_te_price'] = 0
								agents['trade_profit_short'] = 0
								if agents['parent'] != 'None':
									agents['sell_status'] = 'not_active'
								orderList.remove(orders)
								
				elif orders[2] == 'Sell' and timePoint['high'] > orders[3]:
					for agents in offsetTable:
						if agents['entry_id'] == orders[0]:
							#openiong sell filled
							if orders[1] == 'Open':
								agents['opening_sell_price'] = currentPrice
								agents['opening_sell_timestamp'] = currentTime
								if agents['trailing_entry'] == 0:
									rebate = localLib.rebate(agents['amount'],agents['opening_sell_price'],True)
									agents['rpnl_short'] += rebate
									totalProfit += rebate
									agents['trade_profit_short'] += rebate
								else:
									rebate = localLib.rebate(agents['amount'],agents['opening_sell_price'],False)
									agents['rpnl_short'] += rebate
									totalProfit += rebate
									agents['trade_profit_short'] += rebate
									
								agents['sell_status'] = 'looking_to_close'
								agents['ste_target'] = 'None'
								agents['short_te_price'] = 0
								orderList.remove(orders)
								logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agents['entry_id']+' | '+'[SHORT] OPENING SELL FILLED'+' | '+'fill price: '+ str(agents['opening_sell_price']) + ' | ' +'buy status:'+agents['buy_status']+' | '+'sell status:'+agents['sell_status'])
								print('opening sell filled',agents['entry_id'])
								
							#closing sell filled
							elif orders[1] == 'Close':
								agents['closing_sell_timestamp'] = currentTime
								agents['closing_sell_price'] = orders[3]
								agents['time_total_trade'] = (agents['closing_sell_timestamp'] - agents['init_buy_timestamp']) 
								rpnl = localLib.upnl('long', agents['opening_buy_price'], agents['closing_sell_price'],
													 agents['amount'], agents['entry_id'])
								if rpnl > 0:
									agents['recent_close_type'] = 'profit_buy'
								else:
									agents['recent_close_type'] = 'stop_buy'
								agents['rpnl_long'] += rpnl
								totalProfit += rpnl
								agents['trade_profit_long'] += rpnl
								if agents['trailing_tp'] == 0:
									rebate = localLib.rebate(agents['amount'], agents['closing_sell_price'], True)
									agents['rpnl_long'] += rebate
									totalProfit += rebate
									agents['trade_profit_long'] += rebate
								else:
									rebate = localLib.rebate(agents['amount'], agents['closing_sell_price'], False)
									agents['rpnl_long'] += rebate
									totalProfit += rebate
									agents['trade_profit_long'] += rebate
								if agents['max_drawdown_long'] == 0:
									agents['max_drawdown_long'] = 0.000001
								if agents['time_total_trade'] <= 0:
									agents['time_total_trade'] = 1
								
								agents['fitness_score'] = localLib.fitnessScore(agents['trade_profit_long'],
																			   agents['max_drawdown_long'],
																			   agents['time_total_trade'], agents['amount'])
								
								agents['offset_ratio'] = (agents['exit_multiplier'] * agents['offset']) / (
										agents['closing_sell_price'] - agents['exit_multiplier'] * agents['offset'])
								
								agents['trade_counter'] = agents['trade_counter'] + 1
								agents['avg_drawdown'] = (agents['avg_drawdown'] + agents['max_drawdown_long'])/ (agents['trade_counter'])
								agents['avg_spread'] = (agents['avg_spread'] + ((abs(agents['opening_buy_price'] - agents['closing_sell_price']) / ((agents['opening_buy_price'] + agents['closing_sell_price']) /2))*100)) / (agents['trade_counter'])
								agents['avg_duration'] = (agents['avg_duration'] + agents['time_total_trade'] )/ (agents['trade_counter'])
								
								completedTrades.write(agents['entry_id'] + ',' + 'Long' + ',' + str(agents['opening_buy_price']) + ',' + str(agents['opening_buy_timestamp']) + ',' + str(agents['closing_sell_price']) + ',' + str(currentTime) + ',' + str(agents['fitness_score']) + '\n')
								logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agents['entry_id']+' | '+'[LONG] CLOSING SELL FILLED'+' | '+'fill price: '+ str(agents['closing_sell_price']) + ' | ' +'buy status:'+agents['buy_status']+' | '+'sell status:'+agents['sell_status'])
								print('closing sell filled',agents['entry_id'])
								
								agents['buy_status'] = 'looking_to_open'
								agents['opening_buy_price'] = 0.
								agents['opening_buy_timestamp'] = 0
								agents['closing_sell_timestamp'] = 0
								agents['closing_sell_timed'] = 'False'
								agents['closing_sell_price'] = 0
								agents['upnl_long'] = 0
								agents['time_of_close_buy'] = currentTime
								agents['init_buy_timestamp'] = currentTime
								agents['buys_counter'] += 1
								agents['max_drawdown_long'] = 0
								agents['long_tp_price'] = 0
								agents['long_te_price'] = 100000000
								agents['trade_profit_long'] = 0
								if agents['parent'] != 'None':
									agents['buy_status'] = 'not_active'
								orderList.remove(orders)
		
		print(currentPrice,currentTime)
		
		#is this max cumulative dropdown?
		mcdd = 0
		for holders in offsetTable:
			mcdd += (holders['upnl_short']+holders['upnl_long'])
		if mcdd < maxCumDD:
			maxCumDD = mcdd
			
			
		#individual agent actions
		for agent in offsetTable:
			rsiPerAgent = currentTRS[agent['rsiPeriod']]
			
			
			#init timestamps on first execution
			if agent['init_buy_timestamp'] == 0:
				agent['init_buy_timestamp'] = currentTime
			if agent['init_sell_timestamp'] == 0:
				agent['init_sell_timestamp'] = currentTime
					
			#check for parent status to trigger minions
			
			#check for parent status to trigger minions
			#lets get parent status
			if agent['parent'] != 'None':
				for familyTree in offsetTable:
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
							for orders in orderList:
								if orders[0] == agent['entry_id'] and orders[1] == 'Open':
									orderList.remove(orders)
						agent['buy_status'] = 'not_active'

					if agent['sell_status'] in ['looking_to_open', 'open_placed', 'trailing_entry']:
						if agent['sell_status'] == 'open_placed':
							#cancel hanging order
							for orders in orderList:
								if orders[0] == agent['entry_id'] and orders[1] == 'Open':
									orderList.remove(orders)
						agent['sell_status'] = 'not_active'
						
			
			#check for delays
			if agent['recent_close_type'] == 'profit_buy' and (currentTime - agent['time_of_close_buy'] < (agent['delay_profit'])):
				agent['buy_status'] = 'profit_delay'
			elif agent['buy_status'] == 'profit_delay':
				agent['buy_status'] = 'looking_to_open'
				
			if agent['recent_close_type'] == 'stop_buy' and (currentTime - agent['time_of_close_buy'] < (agent['delay_stop'])):
				agent['buy_status'] = 'stop_delay'
			elif agent['buy_status'] == 'stop_delay':
				agent['buy_status'] = 'looking_to_open'
				
			if agent['recent_close_type'] == 'profit_sell' and (currentTime - agent['time_of_close_sell'] < (agent['delay_profit'])):
				agent['sell_status'] = 'profit_delay'
			elif agent['sell_status'] == 'profit_delay':
				agent['sell_status'] = 'looking_to_open'
				
			if agent['recent_close_type'] == 'stop_sell' and (currentTime - agent['time_of_close_sell'] < (agent['delay_stop'])):
				agent['sell_status'] = 'stop_delay'
			elif agent['sell_status'] == 'stop_delay':
				agent['sell_status'] = 'looking_to_open'
			
			
			##calculate unrealized pnl
			
			if agent['buy_status'] == 'looking_to_close' or agent['buy_status'] == 'close_placed' or agent['buy_status'] == 'trailing_tp':
				agent['upnl_long'] = localLib.upnl('long',agent['opening_buy_price'],currentPrice,agent['amount'],agent['entry_id'])
				if agent['upnl_long'] < agent['max_drawdown_long']:
					agent['max_drawdown_long'] = agent['upnl_long']
			else:
				agent['upnl_long'] = 0
				
			if agent['sell_status'] == 'looking_to_close' or agent['sell_status'] == 'close_placed' or agent['sell_status'] == 'trailing_tp':
				agent['upnl_short'] = localLib.upnl('short',agent['opening_sell_price'],currentPrice,agent['amount'],agent['entry_id'])
				if agent['upnl_short'] < agent['max_drawdown_short']:
					agent['max_drawdown_short'] = agent['upnl_short']
			else:
				agent['upnl_short'] = 0
			
			
			##check for trailing entries
			if agent['buy_status'] == 'trailing_entry':
				#trail
				if agent['long_te_price'] > (currentPrice + agent['trailing_entry']):
					agent['long_te_price'] = currentPrice + agent['trailing_entry']
					print('updating long entry',agent['entry_id'],agent['long_te_price'])
					logger.info(str(currentTime) +  '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] NEW TRAILING ENTRY TARGET'+' | '+'te target:'+str(agent['long_te_price']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					#enter
				if currentPrice >= agent['long_te_price']:
					agent['opening_buy_price'] = currentPrice
					agent['opening_buy_timestamp'] = currentTime
					
					rebate = localLib.rebate(agent['amount'],agent['opening_buy_price'],False)
					agent['rpnl_long'] += rebate
					totalProfit += rebate
					agent['trade_profit_long'] += rebate
					agent['buy_status'] = 'looking_to_close'
					agent['lte_target'] = 'None'
					agent['long_te_price'] = 1000000000
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] TRAILING ENTRY TRIGGERED'+' | '+'target price: '+ str(agent['opening_buy_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
					
			if agent['sell_status'] == 'trailing_entry':
				#trail
				if agent['short_te_price']  < (currentPrice - agent['trailing_entry']):
					agent['short_te_price'] = currentPrice - agent['trailing_entry']
					print('updating short entry',agent['entry_id'],agent['short_te_price'])
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] NEW TRAILING ENTRY TARGET'+' | '+'te target:'+str(agent['short_te_price']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					#enter
				if currentPrice <= agent['short_te_price']:
					agent['opening_sell_price'] = currentPrice
					agent['opening_sell_timestamp'] = currentTime
					
					rebate = localLib.rebate(agent['amount'],agent['opening_sell_price'],False)
					agent['rpnl_short'] += rebate
					totalProfit += rebate
					agent['trade_profit_short'] += rebate
									
					agent['sell_status'] = 'looking_to_close'
					agent['ste_target'] = 'None'
					agent['short_te_price'] = 0
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] TRAILING ENTRY TRIGGERED'+' | '+'target price: '+ str(agent['opening_sell_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
			
			##check for take profits
			if agent['buy_status'] == 'trailing_tp':
				#trail
				if agent['long_tp_price'] < (currentPrice - agent['trailing_tp']):
					agent['long_tp_price'] = currentPrice - agent['trailing_tp']
					print('updating long tp',agent['entry_id'],agent['long_tp_price'])
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] NEW TRAILING TAKE PROFIT TARGET'+' | '+'ttp target:'+str(agent['long_tp_price']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
				
				#take profit
				if currentPrice <= agent['long_tp_price'] and currentPrice > agent['opening_buy_price'] and localLib.upnl('long',agent['opening_buy_price'],currentPrice,agent['amount'],agent['entry_id']) > -1*(localLib.rebate(agent['amount'],agent['opening_buy_price'],False)+localLib.rebate(agent['amount'],currentPrice,False)):
					agent['closing_sell_timestamp'] = currentTime
					agent['closing_sell_price'] = currentPrice
					agent['time_total_trade'] = (agent['closing_sell_timestamp'] - agent['init_buy_timestamp'])
					rpnl = localLib.upnl('long', agent['opening_buy_price'], agent['closing_sell_price'],
									 agent['amount'], agent['entry_id'])
					if rpnl > 0:
						agent['recent_close_type'] = 'profit_buy'
					else:
						agent['recent_close_type'] = 'stop_buy'
					agent['rpnl_long'] += rpnl
					totalProfit += rpnl
					agent['trade_profit_long'] += rpnl
					
					rebate = localLib.rebate(agent['amount'], agent['closing_sell_price'], False)
					agent['rpnl_long'] += rebate
					totalProfit += rebate
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
					
					agent['trade_counter'] = agent['trade_counter'] + 1
					agent['avg_drawdown'] = (agent['avg_drawdown'] + agent['max_drawdown_long'])/ (agent['trade_counter'])
					agent['avg_spread'] = (agent['avg_spread'] + ((abs(agent['opening_buy_price'] - agent['closing_sell_price']) / ((agent['opening_buy_price'] + agent['closing_sell_price']) /2))*100)) / (agent['trade_counter'])
					agent['avg_duration'] = (agent['avg_duration'] + agent['time_total_trade'] )/ (agent['trade_counter'])
					
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] TAKE PROFIT TRIGGERED'+' | '+'target price: '+ str(agent['closing_sell_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					completedTrades.write(agent['entry_id'] + ',' + 'Long' + ',' + str(agent['opening_buy_price']) + ',' + str(agent['opening_buy_timestamp']) + ',' + str(agent['closing_sell_price']) + ',' + str(currentTime) + ',' + str(agent['fitness_score']) +'\n')
					
					agent['buy_status'] = 'looking_to_open'
					agent['opening_buy_price'] = 0.
					agent['opening_buy_timestamp'] = 0
					agent['closing_sell_timestamp'] = 0
					agent['closing_sell_timed'] = 'False'
					agent['closing_sell_price'] = 0
					agent['upnl_long'] = 0
					agent['time_of_close_buy'] = currentTime
					agent['init_buy_timestamp'] = currentTime
					agent['buys_counter'] += 1
					agent['max_drawdown_long'] = 0
					agent['long_tp_price'] = 0
					agent['long_te_price'] = 100000000
					agent['trade_profit_long'] = 0
					if agent['parent'] != 'None':
						agent['buy_status'] = 'not_active'
					
			if agent['sell_status'] == 'trailing_tp':
				#trail
				if agent['short_tp_price']  > (currentPrice + agent['trailing_tp']):
					agent['short_tp_price'] = currentPrice + agent['trailing_tp']
					print('updating short tp',agent['entry_id'],agent['short_tp_price'])
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] NEW TRAILING TAKE PROFIT TARGET'+' | '+'ttp target:'+str(agent['short_tp_price']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
				
				#take profit
				if currentPrice >= agent['short_tp_price'] and currentPrice < agent['opening_sell_price'] and localLib.upnl('short',agent['opening_sell_price'],currentPrice,agent['amount'],agent['entry_id']) > -1*(localLib.rebate(agent['amount'],agent['opening_sell_price'],False)+localLib.rebate(agent['amount'],currentPrice,False)):
					
					agent['closing_buy_timestamp'] = currentTime
					agent['closing_buy_price'] = currentPrice
					agent['time_total_trade'] = (agent['closing_buy_timestamp'] - agent['init_sell_timestamp'])
			
					
					rebate = localLib.rebate(agent['amount'], agent['closing_buy_price'], False)
					agent['rpnl_short'] += rebate
					totalProfit += rebate
					agent['trade_profit_short'] += rebate
					rpnl = localLib.upnl('short', agent['opening_sell_price'], agent['closing_buy_price'],
										 agent['amount'], agent['entry_id'])
					if rpnl > 0:
						agent['recent_close_type'] = 'profit_sell'
					else:
						agent['recent_close_type'] = 'stop_sell'
					agent['rpnl_short'] += rpnl
					totalProfit += rpnl
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
					
					agent['trade_counter'] = agent['trade_counter'] + 1
					agent['avg_drawdown'] = (agent['avg_drawdown'] + agent['max_drawdown_short'])/ (agent['trade_counter'])
					agent['avg_spread'] = (agent['avg_spread'] + ((abs(agent['opening_sell_price'] - agent['closing_buy_price']) / ((agent['opening_sell_price'] + agent['closing_buy_price']) /2))*100)) / (agent['trade_counter'])
					agent['avg_duration'] = (agent['avg_duration'] + agent['time_total_trade'] )/ (agent['trade_counter'])
					
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] TAKE PROFIT TRIGGERED'+' | '+'target price: '+ str(agent['closing_buy_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					completedTrades.write(agent['entry_id'] + ',' + 'Short' + ',' + str(agent['opening_sell_price']) + ',' + str(agent['opening_sell_timestamp']) + ',' + str(agent['closing_buy_price']) + ',' + str(currentTime) + ',' + str(agent['fitness_score']) +'\n')
					
					agent['sell_status'] = 'looking_to_open'
					agent['opening_sell_price'] = 0.
					agent['opening_sell_timestamp'] = 0
					agent['closing_buy_timestamp'] = 0
					agent['closing_buy_timed'] = 'False'
					agent['closing_buy_price'] = 0
					agent['upnl_short'] = 0
					agent['init_sell_timestamp'] = currentTime
					agent['time_of_close_sell'] = currentTime
					agent['sells_counter'] += 1
					agent['max_drawdown_short'] = 0
					agent['short_tp_price'] = 100000000
					agent['short_te_price'] = 0
					agent['trade_profit_short'] = 0
					if agent['parent'] != 'None':
						agent['sell_status'] = 'not_active'
			
			###Place orders###############
			##CLOSES
		
			#closing buys with prevent exits or failed closes
			if (agent['prevent_exits'] == 'True' and rsiPerAgent <= agent['rsiOS'] and agent['sell_status'] == 'looking_to_close' and currentPrice <= agent['opening_sell_price']) or agent['sell_status'] == 'failed_close' or (agent['sell_status'] == 'looking_to_close' and agent['prevent_exits'] == 'False'):
				
				if agent['trailing_tp'] == 0:
					agent['closing_buy_price'] = currentPrice - (agent['offset']*agent['exit_multiplier'])
					agent['closing_buy_timestamp'] = currentTime
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] CLOSING BUY PLACED'+' | '+'target price: '+ str(agent['closing_buy_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					agent['sell_status'] = 'close_placed'
					newOrder = [agent['entry_id'],'Close','Buy',agent['closing_buy_price'],currentTime]
					orderList.append(newOrder)
					
				elif currentPrice <= agent['opening_sell_price'] - (agent['offset']*agent['exit_multiplier']) - agent['trailing_tp']:
					agent['sell_status'] = 'trailing_tp'
					agent['short_tp_price'] = currentPrice + agent['trailing_tp']
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] TRAILING TAKE PROFIT INITIATED'+' | '+'target price: '+ str(agent['short_tp_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
			
			#reset failed trails
			elif agent['sell_status'] == 'trailing_tp' and currentPrice > agent['opening_sell_price']:
				agent['sell_status'] = 'looking_to_close'
				logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] CANCEL CLOSING BUY TTP'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
			
			#closing sells with prevent exits or failed closes
			if (agent['prevent_exits'] == 'True' and rsiPerAgent >= agent['rsiOB'] and agent['buy_status'] == 'looking_to_close' and currentPrice >= agent['opening_buy_price']) or agent['buy_status'] == 'failed_close' or (agent['buy_status'] == 'looking_to_close' and agent['prevent_exits'] == 'False'):
				
				if agent['trailing_tp'] == 0:
					agent['closing_sell_price'] = currentPrice + (agent['offset']*agent['exit_multiplier'])
					agent['buy_status'] = 'close_placed'
					newOrder = [agent['entry_id'],'Close','Sell',agent['closing_sell_price'],currentTime]
					orderList.append(newOrder)
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] CLOSING SELL PLACED'+' | '+'target price: '+ str(agent['closing_sell_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
				elif currentPrice >= agent['opening_buy_price'] + (agent['offset']*agent['exit_multiplier']) + agent['trailing_tp']:
					agent['buy_status'] = 'trailing_tp'
					agent['long_tp_price'] = currentPrice - agent['trailing_tp']
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] TRAILING TAKE PROFIT INITIATED'+' | '+'target price: '+ str(agent['long_tp_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
			
			#reset failed trails
			elif agent['buy_status'] == 'trailing_tp' and currentPrice < agent['opening_buy_price']:
				agent['buy_status'] = 'looking_to_close'
				logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] CANCEL OFFSET RANGE DUE TO RSI. RECALIBRATING'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
			
			
			
			##OPENING BUYS
			#opening buys with prevent entries
			if agent['prevent_entries'] == 'True' and rsiPerAgent <= agent['rsiOS'] and agent['buy_status'] == 'looking_to_open':
				
				if agent['trailing_entry'] == 0:
					if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
						agent['buy_status'] = 'open_placed'
						agent['opening_buy_price'] = currentPrice - (agent['offset'] * agent['entry_multiplier'])
						agent['opening_buy_timestamp'] = currentTime
						newOrder = [agent['entry_id'],'Open','Buy',agent['opening_buy_price'],currentTime]
						orderList.append(newOrder)
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] OPENING BUY PLACED'+' | '+'target price: '+ str(agent['opening_buy_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
				elif agent['lte_target'] == 'None':
					if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
						agent['lte_target'] = currentPrice - (agent['entry_multiplier'] * agent['offset']) - agent['trailing_entry']
						agent['lte_timestamp'] = currentTime
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] OFFSET RANGE ESTABLISHED'+' | '+'base target:'+str(agent['lte_target']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
				
				elif currentPrice <= agent['lte_target']:
					agent['buy_status'] = 'trailing_entry'
					agent['long_te_price'] = currentPrice + agent['trailing_entry']
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] TRAILING ENTRY INITIATED'+' | '+'te target:'+str(agent['long_te_price']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
							
			#opening buys without prevent entries
			if agent['prevent_entries'] == 'False' and agent['buy_status'] == 'looking_to_open':
				
				if agent['trailing_entry'] == 0:
					if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
						agent['buy_status'] = 'open_placed'
						agent['opening_buy_price'] = currentPrice - (agent['offset'] * agent['entry_multiplier'])
						agent['opening_buy_timestamp'] = currentTime
						newOrder = [agent['entry_id'],'Open','Buy',agent['opening_buy_price'],currentTime]
						orderList.append(newOrder)
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] OPENING BUY PLACED'+' | '+'target price: '+ str(agent['opening_buy_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
				elif agent['lte_target'] == 'None':
					if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
						agent['lte_target'] = currentPrice - (agent['entry_multiplier'] * agent['offset']) - agent['trailing_entry']
						agent['lte_timestamp'] = currentTime
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] OFFSET RANGE ESTABLISHED'+' | '+'base target:'+str(agent['lte_target']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
						
				elif currentPrice <= agent['lte_target']:
					agent['buy_status'] = 'trailing_entry'
					agent['long_te_price'] = currentPrice + agent['trailing_entry']
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] TRAILING ENTRY INITIATED'+' | '+'te target:'+str(agent['long_te_price']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
			
			#cancel unfilled buys
			if agent['prevent_entries'] == 'True' and rsiPerAgent > agent['rsiOS'] and (agent['buy_status'] == 'open_placed' or agent['buy_status'] == 'looking_to_open'):
				
				if agent['trailing_entry'] == 0 and agent['buy_status'] == 'open_placed':
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] CANCEL OPENING BUY'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					agent['buy_status'] = 'looking_to_open'
					for orders in orderList:
						if orders[0] == agent['entry_id'] and orders[1] == 'Open' and orders[2] == 'Buy':
							orderList.remove(orders)
					###***
									
				elif agent['lte_target'] != 'None':
					agent['buy_status'] = 'looking_to_open'
					agent['long_te_price'] = 100000000
					agent['lte_target'] = 'None'
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] CANCEL OFFSET RANGE DUE TO RSI. RECALIBRATING'+' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
	
			
			##OPENING SELLS
			
			#opening sells with prevent entries
			if agent['prevent_entries'] == 'True' and rsiPerAgent >= agent['rsiOB'] and agent['sell_status'] == 'looking_to_open':
				
				if agent['trailing_entry'] == 0:
					if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
						agent['sell_status'] = 'open_placed'
						agent['opening_sell_price'] = currentPrice + (agent['offset'] * agent['entry_multiplier'])
						agent['opening_sell_timestamp'] = currentTime
						newOrder = [agent['entry_id'],'Open','Sell',agent['opening_sell_price'],currentTime]
						orderList.append(newOrder)
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] OPENING SELL PLACED'+' | '+'target price: '+ str(agent['opening_sell_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
				elif agent['ste_target'] == 'None':
					if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
						agent['ste_target'] = currentPrice + (agent['entry_multiplier'] * agent['offset']) + agent['trailing_entry']
						agent['ste_timestamp'] = currentTime
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] OFFSET RANGE ESTABLISHED'+' | '+'base target:'+str(agent['ste_target']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
				elif currentPrice >= agent['ste_target']:
					agent['sell_status'] = 'trailing_entry'
					agent['short_te_price'] = currentPrice - agent['trailing_entry']
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] TRAILING ENTRY INITIATED'+' | '+'te target:'+str(agent['short_te_price']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
						
			#opening sells without prevent entries
			if agent['prevent_entries'] == 'False' and agent['sell_status'] == 'looking_to_open':
				
				if agent['trailing_entry'] == 0:
					if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
						agent['sell_status'] = 'open_placed'
						agent['opening_sell_price'] = currentPrice + (agent['offset'] * agent['entry_multiplier'])
						agent['opening_sell_timestamp'] = currentTime
						newOrder = [agent['entry_id'],'Open','Sell',agent['opening_sell_price'],currentTime]
						orderList.append(newOrder)
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] OPENING SELL PLACED'+' | '+'target price: '+ str(agent['opening_sell_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
				elif agent['ste_target'] == 'None':
					if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
						agent['ste_target'] = currentPrice + (agent['entry_multiplier'] * agent['offset']) + agent['trailing_entry']
						agent['ste_timestamp'] = currentTime
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] OFFSET RANGE ESTABLISHED'+' | '+'base target:'+str(agent['ste_target']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
							
				elif currentPrice >= agent['ste_target']:
					agent['sell_status'] = 'trailing_entry'
					agent['short_te_price'] = currentPrice - agent['trailing_entry']
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] TRAILING ENTRY INITIATED'+' | '+'te target:'+str(agent['short_te_price']) + ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					
			#cancel unfilled sells
			if agent['prevent_entries'] == 'True' and rsiPerAgent < agent['rsiOB'] and (agent['sell_status'] == 'open_placed' or agent['sell_status'] == 'looking_to_open'):
				
				if agent['trailing_entry'] == 0 and agent['sell_status'] == 'open_placed':
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] CANCEL OPENING SELL'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
					agent['sell_status'] = 'looking_to_open'
					for orders in orderList:
						if orders[0] == agent['entry_id'] and orders[1] == 'Open' and orders[2] == 'Sell':
							orderList.remove(orders)
					###***
				elif agent['ste_target'] != 'None':
					agent['sell_status'] = 'looking_to_open'
					agent['short_te_price'] = 0
					agent['ste_target'] = 'None'
					logger.info(str(currentTime) +str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] CANCEL OFFSET RANGE DUE TO RSI. RECALIBRATING'+ ' | ' + 'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
	
			# timeout
			for orders in orderList:
				if agent['entry_id'] == orders[0] and orders[1] == 'Open' and orders[2] == 'Buy':
					if agent['entry_timeout'] != 0 and agent['entry_timeout'] < (currentTime - orders[4]):
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['opening_buy_price'] = currentPrice - (agent['offset'] * agent['entry_multiplier'])
							agent['opening_buy_timestamp'] = currentTime
							orders[3] = agent['opening_buy_price']
							orders[4] = currentTime
							logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] TIMEOUT OPENING BUY'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
				
				elif agent['entry_id'] == orders[0] and orders[1] == 'Open' and orders[2] == 'Sell':
					if agent['entry_timeout'] != 0 and agent['entry_timeout'] < (currentTime - orders[4]):
						if (int(agent['active_below']) == 0 or currentPrice < int(agent['active_below'])) and (int(agent['active_above']) == 0 or currentPrice > int(agent['active_above'])):
							agent['opening_sell_price'] = currentPrice + (agent['offset'] * agent['entry_multiplier'])
							agent['opening_sell_timestamp'] = currentTime
							orders[3] = agent['opening_sell_price']
							orders[4] = currentTime
							logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] TIMEOUT OPENING SELL'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
				
				elif agent['entry_id'] == orders[0] and orders[1] == 'Close' and orders[2] == 'Buy':
					if agent['exit_timeout'] != 0 and agent['exit_timeout'] < (currentTime - orders[4]):
						
						agent['closing_buy_timestamp'] = currentTime
						if agent['opening_sell_price'] > currentPrice:
							agent['closing_buy_price'] = currentPrice
						else:
							agent['closing_buy_price'] = agent['opening_sell_price']
						orders[3] = agent['closing_buy_price']
						orders[4] = currentTime
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] TIMEOUT CLOSING BUY'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
				
				elif agent['entry_id'] == orders[0] and orders[1] == 'Close' and orders[2] == 'Sell':
					if agent['exit_timeout'] != 0 and agent['exit_timeout'] < (currentTime - orders[4]):
						
						agent['closing_sell_timestamp'] = currentTime
						if agent['opening_buy_price'] < currentPrice:
							agent['closing_sell_price'] = currentPrice
						else:
							agent['closing_sell_price'] = agent['opening_buy_price']
						orders[3] = agent['closing_sell_price']
						orders[4] = currentTime
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] TIMEOUT CLOSING SELL'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
						
			#reset offset target due to timeout
			if agent['buy_status'] == 'looking_to_open' and agent['lte_target'] != 'None' and currentPrice > agent['lte_target']:
				if (agent['entry_timeout']) < (currentTime - agent['lte_timestamp']):
					agent['lte_target'] = 'None'
					agent['long_te_price'] = 100000000
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] OFFSET TARGET TIMED OUT. RECALIBRATING'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
	
			if agent['sell_status'] == 'looking_to_open' and agent['ste_target'] != 'None' and currentPrice < agent['ste_target']:
				if (agent['entry_timeout']) < (currentTime - agent['ste_timestamp']):
					agent['ste_target'] = 'None'
					agent['short_te_price'] = 0
					logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] OFFSET TARGET TIMED OUT. RECALIBRATING'+' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
		
				
			#check for stop losses
			if agent['stop_loss'] != 0:
				
				if agent['buy_status'] in ['looking_to_close', 'close_placed' , 'trailing_tp']:
					if currentPrice < agent['opening_buy_price'] - agent['stop_loss']:
						agent['closing_sell_timestamp'] = currentTime
						agent['closing_sell_price'] = currentPrice
						agent['time_total_trade'] = (agent['closing_sell_timestamp'] - agent['init_buy_timestamp']) 
						rpnl = localLib.upnl('long', agent['opening_buy_price'], agent['closing_sell_price'],
										 agent['amount'], agent['entry_id'])
						if rpnl > 0:
							agent['recent_close_type'] = 'profit_buy'
						else:
							agent['recent_close_type'] = 'stop_buy'
						agent['rpnl_long'] += rpnl
						totalProfit += rpnl
						agent['trade_profit_long'] += rpnl
						
						rebate = localLib.rebate(agent['amount'], agent['closing_sell_price'], False)
						agent['rpnl_long'] += rebate
						totalProfit += rebate
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
						
						agent['trade_counter'] = agent['trade_counter'] + 1
						agent['avg_drawdown'] = (agent['avg_drawdown'] + agent['max_drawdown_long'])/ (agent['trade_counter'])
						agent['avg_spread'] = (agent['avg_spread'] + ((abs(agent['opening_buy_price'] - agent['closing_sell_price']) / ((agent['opening_buy_price'] + agent['closing_sell_price']) /2))*100)) / (agent['trade_counter'])
						agent['avg_duration'] = (agent['avg_duration'] + agent['time_total_trade'] )/ (agent['trade_counter'])
						
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[LONG] CLOSING SELL STOP LOSS'+' | '+'target price: '+ str(agent['closing_sell_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
						completedTrades.write(agent['entry_id'] + ',' + 'Long' + ',' + str(agent['opening_buy_price']) + ',' + str(agent['opening_buy_timestamp']) + ',' + str(agent['closing_sell_price']) + ',' + str(currentTime) + ',' + str(agent['trade_profit_long']) +'\n')
						
						agent['buy_status'] = 'looking_to_open'
						agent['opening_buy_price'] = 0.
						agent['opening_buy_timestamp'] = 0
						agent['closing_sell_timestamp'] = 0
						agent['closing_sell_timed'] = 'False'
						agent['closing_sell_price'] = 0
						agent['upnl_long'] = 0
						agent['time_of_close_buy'] = currentTime
						agent['init_buy_timestamp'] = currentTime
						agent['buys_counter'] += 1
						agent['max_drawdown_long'] = 0
						agent['long_tp_price'] = 0
						agent['long_te_price'] = 100000000
						agent['trade_profit_long'] = 0
						if agent['parent'] != 'None':
							agent['buy_status'] = 'not_active'
						
						for orders in orderList:
							if orders[0] == agent['entry_id'] and orders[1] == 'Close' and orders[2] == 'Sell':
								orderList.remove(orders)
							
								
				if agent['sell_status'] in ['looking_to_close', 'close_placed' , 'trailing_tp']:
					if currentPrice > agent['opening_sell_price'] + agent['stop_loss']:
						agent['closing_buy_timestamp'] = currentTime
						agent['closing_buy_price'] = currentPrice
						agent['time_total_trade'] = (agent['closing_buy_timestamp'] - agent['init_sell_timestamp'])
			
						rebate = localLib.rebate(agent['amount'], agent['closing_buy_price'], False)
						agent['rpnl_short'] += rebate
						totalProfit += rebate
						
						agent['trade_profit_short'] += rebate
						rpnl = localLib.upnl('short', agent['opening_sell_price'], agent['closing_buy_price'],
											 agent['amount'], agent['entry_id'])
						if rpnl > 0:
							agent['recent_close_type'] = 'profit_sell'
						else:
							agent['recent_close_type'] = 'stop_sell'
						agent['rpnl_short'] += rpnl
						totalProfit += rpnl
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
						
						agent['trade_counter'] = agent['trade_counter'] + 1
						agent['avg_drawdown'] = (agent['avg_drawdown'] + agent['max_drawdown_short'])/ (agent['trade_counter'])
						agent['avg_spread'] = (agent['avg_spread'] + ((abs(agent['opening_sell_price'] - agent['closing_buy_price']) / ((agent['opening_sell_price'] + agent['closing_buy_price']) /2))*100)) / (agent['trade_counter'])
						agent['avg_duration'] = (agent['avg_duration'] + agent['time_total_trade'] )/ (agent['trade_counter'])
						
						logger.info(str(currentTime) + '|' + str(currentPrice)+' | '+agent['entry_id']+' | '+'[SHORT] CLOSING BUY STOP LOSS'+' | '+'target price: '+ str(agent['closing_buy_price']) + ' | '+'buy status:'+agent['buy_status']+' | '+'sell status:'+agent['sell_status'])
						completedTrades.write(agent['entry_id'] + ',' + 'Short' + ',' + str(agent['opening_sell_price']) + ',' + str(agent['opening_sell_timestamp']) + ',' + str(agent['closing_buy_price']) + ',' + str(currentTime) + ',' +str(agent['fitness_score']) + '\n')
					
						agent['sell_status'] = 'looking_to_open'
						agent['opening_sell_price'] = 0.
						agent['opening_sell_timestamp'] = 0
						agent['closing_buy_timestamp'] = 0
						agent['closing_buy_timed'] = 'False'
						agent['closing_buy_price'] = 0
						agent['upnl_short'] = 0
						agent['init_sell_timestamp'] = currentTime
						agent['time_of_close_sell'] = currentTime
						agent['sells_counter'] += 1
						agent['max_drawdown_short'] = 0
						agent['short_tp_price'] = 100000000
						agent['short_te_price'] = 0
						agent['trade_profit_short'] = 0
						if agent['parent'] != 'None':
							agent['sell_status'] = 'not_active'
						for orders in orderList:
							if orders[0] == agent['entry_id'] and orders[1] == 'Close' and orders[2] == 'Buy':
								orderList.remove(orders)
								
			
	#check open positions before finishing
	for agents in offsetTable:
		if agents['buy_status'] in ['trailing_tp','looking_to_close','close_placed']:
			rpnl = localLib.upnl('long', agents['opening_buy_price'], currentPrice,
													 agents['amount'], agents['entry_id'])
			agents['rpnl_long'] += rpnl
			totalProfit += rpnl
			

		if agents['sell_status'] in ['trailing_tp','looking_to_close','close_placed']:
			rpnl = localLib.upnl('short', agents['opening_sell_price'], currentPrice,
													 agents['amount'], agents['entry_id'])
			agents['rpnl_short'] += rpnl
			totalProfit += rpnl
			
	with open('results/results'+str(index)+'.csv','w') as fitnessFile:
		fitnessFile.write('agent_id,profit,avg_drawdown,avg_spread,avg_duration,num_trades\n')
		for agents in offsetTable:
			fitnessFile.write(agents['entry_id']+','+str(float(agents['rpnl_short'])+float(agents['rpnl_long']))+','+str(agents['avg_drawdown'])+','+str(agents['avg_spread'])+','+str(agents['avg_duration'])+','+str(agents['trade_counter'])+'\n')
		fitnessFile.write('total profit, '+ str(totalProfit)+'\n')
		fitnessFile.write('max cumulative drawdown, '+ str(maxCumDD))