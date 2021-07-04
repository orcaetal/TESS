#! usr/env/bin python
import json
import numpy as np
import requests
import math
import time
import random
import string
import socketio
import logging
#import tulipy
import pandas as pd
import ta
import traceback
import re
from PIL import Image, ImageDraw, ImageFont
message = 0

def coolASCII():
	text = "Genesis Algo"
	myfont = ImageFont.truetype("verdanab.ttf", 12)
	size = myfont.getsize(text)
	img = Image.new("1", size, "black")
	draw = ImageDraw.Draw(img)
	draw.text((0, 0), text, "white", font=myfont)
	pixels = np.array(img, dtype=np.uint8)
	chars = np.array([' ', '#'], dtype="U1")[pixels]
	strings = chars.view('U' + str(chars.shape[1])).flatten()
	print("\n".join(strings))
	print('Enjoy trading with the power of TESS !')
	pass

#read offset table from csv
def offsetTable(filename,balance,price):
		dataFile = open(filename,'r')
		keyNames = []
		offsetList = []
		
		#loop through agents
		for lines in dataFile:
			lines = lines.rstrip().split(',')
			
			#capture headers for dictionary key names
			if lines[0] == 'offset':
				for each in lines:
					keyNames.append(each)
					
			#capture data
			else:
				
				#for addition to offsetList at end of loop
				tempDict={}
				
				#fill dict
				for i in range(len(lines)):
					#numeric type conversion
					if lines[i].isdigit() or lines[i].replace(".", "", 1).isdigit():
						tempDict[keyNames[i]]=float(lines[i])
					
					else:
						#convert various boolean forms to string
						if str(lines[i]) in ['true','True','TRUE']:
							tempDict[keyNames[i]] = 'True'
						elif str(lines[i]) in ['false','False','FALSE']:
						    tempDict[keyNames[i]] = 'False'
						
						#string as is
						else:
						    tempDict[keyNames[i]]=str(lines[i])
				
				if len(tempDict) != 21:
					print('OFFSET TABLE FORMAT INCORRECT')
					exit()
				
				#add flags for agent monitoring
				tempDict['offset_ratio'] = 0

				tempDict['opening_sell_price'] = 0.
				tempDict['opening_buy_price'] = 0.
				tempDict['closing_buy_price'] = 0.
				tempDict['closing_sell_price'] = 0.
				
				tempDict['init_buy_timestamp'] = 0
				tempDict['init_sell_timestamp'] = 0

				tempDict['time_total_trade'] = 0
				tempDict['fitness_score'] = 0

				tempDict['opening_buy_timestamp'] = 0
				tempDict['opening_sell_timestamp'] = 0
				tempDict['closing_sell_timestamp'] = 0
				tempDict['closing_buy_timestamp'] = 0
				
				tempDict['opening_buy_times_replaced'] = 1
				tempDict['opening_sell_times_replaced'] = 1
				
				tempDict['closing_buy_timed'] = 'False'
				tempDict['closing_sell_timed'] = 'False'
				
				tempDict['buys_counter'] = 0
				tempDict['sells_counter'] = 0
				
				tempDict['max_drawdown_long'] = 0
				tempDict['max_drawdown_short'] = 0
				
				tempDict['upnl_long'] = 0
				tempDict['upnl_short'] = 0
				
				tempDict['rpnl_long'] = 0
				tempDict['rpnl_short'] = 0
				tempDict['trade_profit_long'] = 0
				tempDict['trade_profit_short'] = 0
				
				tempDict['long_tp_price'] = 0
				tempDict['short_tp_price'] = 1000000000000
				
				tempDict['long_te_price'] = 1000000000000
				tempDict['short_te_price'] = 0
				
				tempDict['lte_target'] = 'None'
				tempDict['ste_target'] = 'None'
				tempDict['ltp_target'] = 'None'
				tempDict['stp_target'] = 'None'
				
				tempDict['lte_timestamp'] = 'None'
				tempDict['ste_timestamp'] = 'None'
				
				tempDict['mark_placed_entry_long'] = False
				tempDict['mark_placed_entry_short'] = False
				tempDict['mark_placed_exit_long'] = False
				tempDict['mark_placed_exit_short'] = False
				tempDict['mark_placed_sl_long'] = False
				tempDict['mark_placed_sl_short'] = False
				
				tempDict['time_of_close_buy'] = 0
				tempDict['time_of_close_sell'] = 0
				tempDict['recent_close_type'] = 'None'
				
				if tempDict['buys_allowed'] == 'False':
				    tempDict['buy_status'] = 'not_active'
				else:
					tempDict['buy_status'] = 'looking_to_open'
				
				if tempDict['sells_allowed'] == 'False':
				    tempDict['sell_status'] = 'not_active'
				else:
					tempDict['sell_status'] = 'looking_to_open'
				
				#add tiers/minions (parents only)
				#tierCapt = re.search("(.+)\.\d+$",tempDict['entry_id'])
				#if tierCapt:
				#	tempDict['parent'] = tierCapt.group(1)
				#	tempDict['buy_status'] = 'not_active'
				#	tempDict['sell_status'] = 'not_active'
				#else:
				#	tempDict['parent'] = 'None'
				
				#add tiers/minions
				#tierCapt = re.search("(.+)\.\d+$",tempDict['entry_id'])
				lineage = tempDict['entry_id'].split('.')
				
				#grandkiddies
				if len(lineage) == 3:
					tempDict['grandparent'] = lineage[0] 
					tempDict['parent'] = lineage[0] + '.' + lineage[1]
					tempDict['buy_status'] = 'not_active'
					tempDict['sell_status'] = 'not_active'
				elif len(lineage) == 2:
					tempDict['grandparent'] = 'None'
					tempDict['parent'] = lineage[0]
					tempDict['buy_status'] = 'not_active'
					tempDict['sell_status'] = 'not_active'
				else:
					tempDict['grandparent'] = 'None'
					tempDict['parent'] = 'None'
					
					
				#ensure listen received order flag
				tempDict['received'] = True
				
				#convert percents
				if price != 0: #ignore for backtester
					if re.match('.+%$',str(tempDict['offset'])):
						newOffset = (float(tempDict['offset'][:-1]) * price)/100
						tempDict['offset'] = newOffset
				if balance != 1:
					if re.match('.+%$',str(tempDict['amount'])):
						newAmount = ((float(tempDict['amount'][:-1]) * balance)/100)*price
						tempDict['amount'] = newAmount
				elif re.match('.+%$',str(tempDict['amount'])):
					tempDict['amount'] = float(tempDict['amount'][:-1])
					
				#to be returned
				offsetList.append(tempDict)
			
		return(offsetList)

def fetchPriceList(self, timeframe, timestamp):
	prices = []
	resDict = self.adapter.priceCandles(timeframe, int(timestamp / 1000))
	for candles in resDict['result']:
		for keys in candles:
			if keys == 'close':
				prices.append(float(candles[keys]))
	return prices

def orderLinkId(agent, side, openOrClose, limitOrMarket, timestamp, user):
	if side == 'Buy' and openOrClose == 'Close':
		agent['tag'] = '-2b'
	elif side == 'Sell' and openOrClose == 'Close':
		agent['tag'] = '-2s'
	elif side == 'Buy' and openOrClose == 'Open':
		agent['tag'] = '-1b'
	elif side == 'Sell' and openOrClose == 'Open':
		agent['tag'] = '-1s'
	return agent['entry_id'] + agent['tag'] + limitOrMarket + '=' + timestamp + '-' + str(user)

##build ribbons for metrics
def buildRibbons(self, prices):
	try:
		megaRibbon = {}
		for tf, price in prices.items():
			megaRibbon[tf + 'min']=bigRibbon(price)
		return(megaRibbon)
	except:
		self.logger.error('buildRibbons')

##build ribbons for metrics
def buildSingleRibbon(self, tf, timestampOI):
	try:
		megaRibbon = {}
		prices = fetchPriceList(self,tf,int(timestampOI/1000))
		megaRibbon[tf + 'min']=bigRibbon(prices)
		return(megaRibbon)
	except:
		self.logger.error('buildSingleRibbon')
		
##build sma ribbons for metrics
def buildSMARibbons(self, prices):
	try:
		megaRibbon = {}
		for tf, price in prices.items():
			megaRibbon[tf+'min']=samRibbon(price)
		return(megaRibbon)
	except:
		self.logger.error('buildSMARibbons')
		
##build ribbons for metrics
def buildVariances(self, prices):
	try:
		megaVariances = {}
		for tf, price in prices.items():
			megaVariances[tf+'min']= varRibbon(price)
		
		return(megaVariances)
	except:
		self.logger.error('buildVariances')
		
##build ribbons for metrics
#def buildStochs(self, prices):
#	try:
#		megaStochs = {}
#		for tf, price in prices.items():
#			kList = tulipy.sma(tulipy.stochrsi(np.array(price),14),3)
#			dList = tulipy.sma(tulipy.sma(tulipy.stochrsi(np.array(price),14),3),3)
#			
#			#find index of most recent cross
#			if kList[-1] > dList[-1]:
#				orientation = 'Up'
#				prevOrientation = 'Up'
#			else:
#				orientation = 'Down'
#				prevOrientation = 'Down'
#			
#			i = -1
#			while orientation == prevOrientation and i >= -165:
#				i-=1
#				if kList[i] > dList[i]:
#					prevOrientation = 'Up'
#				else:
#					prevOrientation = 'Down'
#			subStoch={}
#			subStoch['K'] = kList[-1]
#			subStoch['D'] = dList[-1]
#			if i == -166:
#				subStoch['cross'] = -1
#			else:
#				subStoch['cross'] = (kList[i+1]+dList[i+1])/2
#			megaStochs[tf+'min'] = subStoch
#		return(megaStochs)
#	except:
#		self.logger.error('buildStochs')

##build ribbons for metrics
def buildPriceHistory(self, prices):
	try:
		megaPH = {}
		for tf, price in prices.items():
			megaPH[tf+'min']= price
		
		return(megaPH)
	except:
		self.logger.error('buildPriceHistory')

def buildMidnightCandle(self, timestamp):
	resDict = self.adapter.midnightCandle(timestamp)
	return resDict['result']

##convert list of prices and period length to ema value, return latest ema
def buildEMA(priceList, length):
	try:
		##build initial EMA [take first i prices from beginning of list]
		# sum = 0.0
		# for i in range(length):
		# 	sum = sum+ float(priceList[i])
		if length == 0:
			initEMA = 50
		else:
			initEMA = sum(priceList)/len(priceList)
		
		#build EMA array up to point z
		EMAz=[0.0]
		for z in range(len(priceList)):
			if z<length-1:
				EMAz.append(0.0)
			elif z == length-1:
				EMAz.append(initEMA)
			else:
				if EMAz[z-1] != 0.0:
					newEMA = (priceList[z] - EMAz[z-1]) * (2/(length+1)) + EMAz[z-1]
					EMAz.append(newEMA)
		
		return(EMAz[-1])	
	except:
		print('buildEMA')
		
##convert list of prices and period length to sma value
def buildSMA(priceList, length):
	try:
		# for i in range(length):
		# 	sum = sum+ float(priceList[-i])
		if length == 0:
			return(0)
		else:
			return(sum(priceList)/len(priceList))
	except:
		print('buildSMA')
		
##return a list of EMA values [ribbon] for current timepoint
def bigRibbon(workingPriceList):
	
	try:
		ribbon = {}
		ribbon['3'] = buildEMA(workingPriceList, 3)
		ribbon['8'] = buildEMA(workingPriceList, 8)
		ribbon['13'] = buildEMA(workingPriceList, 13)
		ribbon['34'] = buildEMA(workingPriceList, 34)
		ribbon['89'] = buildEMA(workingPriceList, 89)
		ribbon['144'] = buildEMA(workingPriceList, 144)
		
		return(ribbon)
	except:
		print('bigRibbon')

##return a list of variance values [ribbon] for current timepoint
def varRibbon(workingPriceList):
	try:
		priceRibbon = {}
	
		priceRibbon['5'] = np.std(np.array(workingPriceList[-5:]))
		priceRibbon['8'] = np.std(np.array(workingPriceList[-8:]))
		priceRibbon['13'] = np.std(np.array(workingPriceList[-13:]))
		priceRibbon['21'] = np.std(np.array(workingPriceList[-21:]))
		priceRibbon['34'] = np.std(np.array(workingPriceList[-34:]))
		priceRibbon['55'] = np.std(np.array(workingPriceList[-55:]))
		priceRibbon['89'] = np.std(np.array(workingPriceList[-89:]))
		
		return(priceRibbon)
	except:
		print('varRibbon')
		
#return sams ribbon
def samRibbon(workingPriceList):
	try:
		ribbon = {}
		ribbon['20'] = buildSMA(workingPriceList, 20)
		ribbon['50'] = buildSMA(workingPriceList, 50)
		ribbon['200'] = buildSMA(workingPriceList, 200)
		
		return(ribbon)
	except:
		print('samRibbon')

#return binary string representing fib ribbon
def binaryString(ribbons):
	try:
		megaString = {}
		for timeFrame in ribbons:
			binString = []
			if timeFrame == '15min':
				if ribbons[timeFrame]['3'] > ribbons[timeFrame]['13']:
					binString.append(0)
				else:
					binString.append(1)
	
				if ribbons[timeFrame]['13'] > ribbons[timeFrame]['34']:
					binString.append(0)
				else:
					binString.append(1)
	
				if ribbons[timeFrame]['34'] > ribbons[timeFrame]['89']:
					binString.append(0)
				else:
					binString.append(1)
	
			if timeFrame == '120min':
				if ribbons[timeFrame]['3'] > ribbons[timeFrame]['8']:
					binString.append(0)
				else:
					binString.append(1)
	
				if ribbons[timeFrame]['8'] > ribbons[timeFrame]['34']:
					binString.append(0)
				else:
					binString.append(1)
	
				if ribbons[timeFrame]['34'] > ribbons[timeFrame]['89']:
					binString.append(0)
				else:
					binString.append(1)
	
			if timeFrame == '360min':
				if ribbons[timeFrame]['3'] > ribbons[timeFrame]['8']:
					binString.append(0)
				else:
					binString.append(1)
	
				if ribbons[timeFrame]['8'] > ribbons[timeFrame]['34']:
					binString.append(0)
				else:
					binString.append(1)
	
				if ribbons[timeFrame]['34'] > ribbons[timeFrame]['144']:
					binString.append(0)
				else:
					binString.append(1)
	
			megaString[timeFrame] = binString
		return (megaString)
	except:
		print('binaryString')
		
#return binary string of 20,50,200 sma
def binaryStringSMA(ribbons):
	try:
		megaString = {}
		for timeFrame in ribbons:
			binString = []
			
			if ribbons[timeFrame]['20'] > ribbons[timeFrame]['50']:
				binString.append(0)
			else:
				binString.append(1)
				
			if ribbons[timeFrame]['20'] > ribbons[timeFrame]['200']:
				binString.append(0)
			else:
				binString.append(1)
			
			if ribbons[timeFrame]['50'] > ribbons[timeFrame]['200']:
				binString.append(0)
			else:
				binString.append(1)
			
			megaString[timeFrame] = binString
			
		return(megaString)
	except:
		print('binarySMA')
		
#return percentual difference of currentprice to various MAs
def percentSMA(openingPrice,megaRibbon):
	try:
		megaReturn = {}
		for timeFrames in megaRibbon:
			percentDifs = {}
			percentDifs['20'] = ((openingPrice - megaRibbon[timeFrames]['20'])/openingPrice) * 100
			percentDifs['50'] = ((openingPrice - megaRibbon[timeFrames]['50'])/openingPrice) * 100
			percentDifs['200'] = ((openingPrice - megaRibbon[timeFrames]['200'])/openingPrice) * 100
			megaReturn[timeFrames] = percentDifs
		return(megaReturn)
	except:
		print('percentSMA')
		
##calculate upnl
def upnl(side,firstPrice,secondPrice,size,agentID):
	try:
		if firstPrice == 0:
			raise Exception('first price is zero',agentID)
		if secondPrice == 0:
			raise Exception('second price is zero',agentID)
		if side == 'long':
			upnl = size*((1/firstPrice)-(1/secondPrice))
		if side == 'short':
			upnl = size*((1/secondPrice)-(1/firstPrice))
		return(upnl)
	except Exception as e:
		print('upnl',agentID)
		return(0.000000001)
		
##calculate fees
def rebate(size,currentPrice,maker):
	try:
		if currentPrice == 0:
			raise Exception('current price is zero dummy')
		if maker:
			return((size/currentPrice) * .00025)
		else:
			return((size/currentPrice) * -.00075)
	except:
		print('rebate')
		
##return RSI(n)
def rsiFunc(priceDict, n):
	try:
		#convert dict to list
		highs = []
		lows = []
		closes = []
		volumes = []
		for candles in priceDict:
			highs.append(candles['high'])
			lows.append(candles['low'])
			closes.append(candles['close'])
			volumes.append(candles['volume'])
		if len(closes) <= n:
			return(50)
		else:
			tuInput1 = np.array(highs, dtype='float64')
			taInput1 = pd.Series(highs)
			tuInput2 = np.array(lows, dtype='float64')
			taInput2 = pd.Series(lows)
			tuInput3 = np.array(closes, dtype='float64')
			taInput3 = pd.Series(closes)
			tuInput4 = np.array(volumes, dtype='float64')
			taInput4 = pd.Series(volumes)
			
			#rsi = tulipy.rsi(real=tuInput3, period=int(n))
			taRSI = ta.momentum.RSIIndicator(taInput3, int(n), True).rsi()
			#mfi = tulipy.mfi(tuInput1, tuInput2, tuInput3, tuInput4, period=int(n))
			taMFI = ta.volume.MFIIndicator(taInput1, taInput2, taInput3, taInput4, int(n), True).money_flow_index()
			trs = (taRSI.iloc[-1] + taMFI.iloc[-1]) / 2
			return trs
	except:
		print('rsiFunc')
		traceback.print_exc()
		
##round to nearest point 5
def roundHalf(self, x):
	if self.asset == 'btcusd':
		return round(.5 * round(float(x)/.5),1)
	elif self.asset == 'ethusd':
		return round(round(.5 * round(float(x) * 10 / .5), 2) / 10, 2)
	elif self.asset == 'eosusd':
		return round(float(x), 3)
	elif self.asset == 'xrpusd':
		return round(float(x), 4)

#factor of time for fitness score
def timeFactor(time):
	return 1 / (0.125 * time + 0.1)

#factor of drawdown for fitness score
def drawdownFactor(rpnl, drawdown):
	ratio = abs(drawdown / rpnl)
	return 10.5 * math.exp(ratio * -3.12)

# Calculate fitness score
def fitnessScore(rpnl, drawdown, time, amount):
	return 10 ** 8 * ((rpnl * drawdownFactor(rpnl, drawdown) * timeFactor(time)) / amount)

# Random ID generator
def randomString():
	letters = string.ascii_lowercase
	return ''.join(random.choice(letters) for i in range(8))

##make request to genesis-algo licensing server
def makeHttpRequest(endpoint, data):
	##can pass in endpoint in the future to determine post, get, put, delete
	response = requests.post(endpoint, data)
	return response

##common json loader
def loadJsonFile(filepath):
	with open(filepath) as jsonData:
		return json.load(jsonData)

##common licensing loading
def loadConfig():
	return loadJsonFile('config.json')

##startup websocket and authenticate session
def loadClient(email, license, uuid, callback):
	sio = socketio.Client()
	connInfo = 'email=' + email + '&license=' + license + '&uuid=' + uuid

	@sio.event
	def connect():
		print('Successfully connected to Genesis Algo Trade Servers!')
		sio.emit('authenticate')

	@sio.event
	def connect_error(data):
		print('Failed to connect to Genesis Algo Trade Servers!')
		print(data)
		print("Exiting in 30 seconds...")
		time.sleep(30)

	@sio.event
	def authenticated(message):
		print('Successfully authenticated!')
		callback()

	@sio.event
	def disconnect_with_message(message):
		print("disconnect message:",message)
		sio.emit('force_disconnect')
		print("Exiting in 30 seconds...")
		time.sleep(30)

	try:
		sio.email = email
		sio.connect('http://188.166.30.177:5430?' + connInfo)
	except Exception as ex:
		print(ex,"from sio")
		print("Exiting in 30 seconds...")
		time.sleep(30)

def setupLogger(name, log_file, level=logging.INFO):
    logFormatter = logging.Formatter('%(asctime)s | %(thread)x | %(name)5s | %(levelname)5s | %(message)s')
    handler = logging.FileHandler(log_file)        
    handler.setFormatter(logFormatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
