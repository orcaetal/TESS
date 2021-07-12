from adapter import Adapter
import live_functions as localLib
import datetime
import hmac
import hashlib
import websockets
import json
import pandas as pd
import logging
import re
import time
import pickle
import sys
import os
import http.client
import live_functions as localib
from dateutil.tz import gettz
import csv


class Bybit(Adapter):
	def __init__(self, config, user):
		self.network = config['network']
		self.exchange = config['exchange']
		self.asset = config['asset']
		self.private = config["private"]
		self.key = config["key"]
		self.version = config['version']
		self.logger = localLib.setupLogger('live', f'../logs/live-{self.network}-adapter.log', logging.DEBUG)
		self.orderList = []
		self.user = user

		if self.network == "mainnet":
			self.connStr = 'wss://stream.bybit.com/realtime?'
		elif self.network == "testnet":
			self.connStr = 'wss://stream-testnet.bybit.com/realtime?'

	def authenticate(self, v):
		timestamp = int(datetime.datetime.now().timestamp())
		expires = int(timestamp * 1000) + v  # changed 5000 to 10000
		handshake = 'GET/realtime' + str(expires)
		signature = hmac.new(self.private.encode(), handshake.encode(), digestmod=hashlib.sha256).hexdigest()
		params = 'api_key=' + self.key + '&expires=' + str(expires) + '&signature=' + signature
		return self.connStr + params

	def orderData(self, message):
		subscription = json.loads(message)
		order = {}
		##candle data
		if 'data' in subscription:
			data = subscription['data'][0]
			if len(data['order_link_id']) <= 1:
				return
			if 'order_status' in data:
				order['order_status'] = data['order_status']
			else:
				# Handle order status for the 'execution' subscription:
				if data['exec_type'] == 'Trade':
					order['order_status'] = 'Filled'
				else:
					order['order_status'] = 'Other'

			agent_id, x, user = data['order_link_id'].split("-")
			ordertype, unix = x.split("=")
			order['price'] = data['price']
			order['order_link_id'] = data['order_link_id']
			order['id'] = agent_id
			order['side'] = ordertype[:2]
			order['user'] = user
			order['time'] = unix
			order['order_type'] = 'Market' if ordertype[2] == 'm' else 'Limit'
			return order
	
	def positionData(self, message):
		subscription = json.loads(message)
		position = {}
		##candle data
		if 'data' in subscription:
			position = subscription['data']
			return position

	def priceAction(self, message):
		subscription = json.loads(message)
		priceData = {}
		if 'data' in subscription:
			data = subscription['data'][0]
			# priceData['final'] = data['final']
			priceData['cross_seq'] = data['cross_seq']
			priceData['high'] = data['high']
			priceData['open'] = data['open']
			priceData['turnover'] = data['turnover']
			priceData['start'] = data['start']
			priceData['low'] = data['low']
			priceData['close'] = data['close']
			priceData['volume'] = data['volume']
			priceData['timestamp'] = data['timestamp']
			priceData['confirm'] = data['confirm']

			return priceData
		else:
			return None

	def subscribeAsset(self):
		return f'{{"op":"subscribe","args":["klineV2.1.{self.asset.upper()}"]}}' # curly brackets for f string

	def subscribeOrder(self):
		return '{"op":"subscribe","args":["order"]}'
	
	def subscribeExecution(self):
		return '{"op":"subscribe","args":["execution"]}'

	def subscribePosition(self):
		return '{"op":"subscribe","args":["position"]}'
	
	def subNetwork(self, call, order, signedMessage=''):
		connection = None
		if self.network == 'mainnet':
			connection = http.client.HTTPSConnection("api.bybit.com", 443, timeout=10)
			connection.request(
				call,
				order + signedMessage,
				headers={
					'Host': 'api.bybit.com',
					'Content-Type': 'application/x-www-form-urlencoded',
					'Referer': 'GenesisAlgo'})

		if self.network == 'testnet':
			connection = http.client.HTTPSConnection("api-testnet.bybit.com", 443, timeout=10)
			connection.request(call, order + signedMessage,
							   headers={'Host': 'api-testnet.bybit.com',
										'Content-Type': 'application/x-www-form-urlencoded'})
		
		return connection

	def sendPublicMessage(self, call, message):
		fails = 0
		while True:
			try:
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature

				# connect and send request
				connection = self.subNetwork(call, "/v2/public/kline/list?", signedMessage)
				resDict = self.returnData(connection)
				if resDict['ret_code'] != 0:
					raise Exception(resDict)
				else:
					return resDict

			except Exception as e:
				fails += 1
				self.logger.error('failed public message' + str(e))
				time.sleep(1)
				if fails > 2:
					return
				
	def fetchCandle(self):
		fails = 0
		while True:
			try:
				#signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				#signedMessage = message + "&sign=" + signature
				timestamp = str(int(datetime.datetime.now().timestamp()) -60)
				# connect and send request
				connection = self.subNetwork('GET', "/v2/public/kline/list?from="+timestamp+"&interval=1&symbol="+self.asset.upper())#, signedMessage)
				resDict = self.returnData(connection)
				if resDict['ret_code'] != 0:
					raise Exception(resDict)
				elif len(resDict['result'])>0:
					return resDict['result'][0]
				else:
					return
			except Exception as e:
				fails += 1
				self.logger.error('failed public message' + str(e))
				time.sleep(1)
				if fails > 2:
					return
				
	def sendOrder(self, message):
		fails = 0
		while True:
			try:
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature

				# connect and send request
				connection = self.subNetwork("POST", "/v2/private/order/create?", signedMessage)
				resDict = self.returnData(connection)
				if resDict['ret_code'] != 0:
					
					raise Exception(resDict)
				else:
					return resDict

			except Exception as e:
				fails += 1
				self.logger.error('failed sending order' + str(e))
				time.sleep(1)
				if fails > 2:
					return

	def priceCandles(self, timeFrame, timestamp):
		message = 'api_key=' + self.key + '&from=' + str(timestamp - (200 * 60 * int(timeFrame))) + '&interval=' + str(
			timeFrame) + '&symbol=' + self.asset.upper()
		resDict = self.sendPublicMessage("GET", message)
		if resDict['ret_code'] != 0:
			raise Exception('error')

		return resDict

	def midnightCandle(self, midnightTime):
		midnightTime = datetime.datetime.fromtimestamp(int(midnightTime / 1000))
		# find midnight
		readableDate = midnightTime.strftime('%Y-%m-%d %H:%M:%S').split('-')
		midnightTime = int(
			datetime.datetime(int(readableDate[0]), int(readableDate[1]), int(readableDate[2].split(' ')[0]),
							  tzinfo=datetime.timezone.utc).astimezone(gettz("Europe/Madrid")).timestamp())
		# construct message for bybit
		message = 'api_key=' + self.key + '&from=' + str(midnightTime) + '&interval=60&limit=1&symbol=' + self.asset.upper()
		resDict = self.sendPublicMessage("GET", message)
		if resDict['ret_code'] != 0:
			raise Exception('error')

		return resDict

	def placeMarketOrder(self, agent, side, openOrClose):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				orderLinkId = localLib.orderLinkId(agent, side, openOrClose, 'm', timestamp, self.user)
				message = 'api_key=' + self.key + '&order_link_id=' + orderLinkId + \
						  '&order_type=Market&qty=' + str(int(agent['amount'])) + \
						  '&recv_window=10000000000000&side=' + side + \
						  '&symbol=' + self.asset.upper() + '&time_in_force=GoodTillCancel&timestamp=' + str(timestamp)
				resDict = self.sendOrder(message)
				return resDict
			except Exception as e:
				fails += 1
				self.logger.error('failed market order' + str(e) + agent['entry_id'])
				time.sleep(1)
				if fails > 2:
					return resDict

	def placeLimitOrder(self, agent, currentPrice, side, openOrClose):
		fails = 0
		targetPrice = localLib.roundHalf(self,currentPrice)
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				orderLinkId = localLib.orderLinkId(agent, side, openOrClose, 'l', timestamp, self.user)
				message = 'api_key=' + self.key + '&order_link_id=' + orderLinkId + '&order_type=Limit&price=' + str(targetPrice) + '&qty=' + str(int(agent[
						'amount'])) + '&recv_window=10000000000000&side=' + side + '&symbol=' + self.asset.upper() +'&time_in_force=PostOnly&timestamp=' + timestamp
				resDict = self.sendOrder(message)
				return resDict
			except Exception as e:
				fails += 1
				self.logger.error('failed limit order' + str(e) + agent['entry_id'])
				time.sleep(1)
				if fails > 2:
					return resDict

	def cancelAll(self):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				# connect and send request
				connection = self.subNetwork("POST", "/v2/private/order/cancelAll?", signedMessage)
				# check response
				resDict = self.returnData(connection)
				
				break
			except Exception as e:
				fails += 1
				self.logger.error('failed cancelAll' + str(e))
				time.sleep(1)
				if fails > 2:
					return resDict

	def cancelOrder(self, agent):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&order_link_id=' + agent['order_link_id'] \
						  + '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				# connect and send request
				connection = self.subNetwork("POST", "/v2/private/order/cancel?", signedMessage)

				# check response
				resDict = self.returnData(connection)

				if resDict and ('reject_reason' in resDict) and resDict['reject_reason'] :
					message = 'Cancel for {0} rejected with reason "{1}"'.format(agent['order_link_id'], resDict['reject_reason'])
					self.logger.warning(agent['entry_id'] + '| CANCEL REJECTED |' + message)
				break
			except Exception as e:
				fails += 1
				self.logger.error('failed cancelOrder ' + str(e) + agent['order_link_id'])
				time.sleep(1)
				if fails > 2:
					return resDict

	def cancelHalf(self):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				# connect and send request
				connection = self.subNetwork("GET", "/v2/private/position/list?", signedMessage)
				# check response
				resDict = self.returnData(connection)

				currentSide = resDict['result']['side']
				if currentSide == 'Buy':
					for openOrder in self.orderList:
						if re.match('.+\db.+', openOrder['order_link_id']):
							self.cancelOrder(openOrder)
				if currentSide == 'Sell':
					for openOrder in self.orderList:
						if re.match('.+\ds.+', openOrder['order_link_id']):
							self.cancelOrder(openOrder)
				break
			except Exception as e:
				fails += 1
				self.logger.error('failed cancelHalf' + str(e))
				time.sleep(1)
				if fails > 2:
					return resDict

	def replaceOrder(self, agent, currentPrice, genericOrderID, side):
		fails = 0
		price = ''
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				if side == '1b':
					price = str(localLib.roundHalf(self, currentPrice - (agent['offset'] * agent['entry_multiplier'])))
				elif side == '1s':
					price = str(localLib.roundHalf(self, currentPrice + (agent['offset'] * agent['entry_multiplier'])))
				elif side == '2b':
					if agent['closing_sell_price'] < currentPrice:
						price = str(localLib.roundHalf(self, agent['opening_sell_price']))
					else:
						price = str(localLib.roundHalf(self, agent['opening_sell_price'] - (agent['offset'] * agent['exit_multiplier'])))
				elif side == '2s':
					if agent['opening_buy_price'] > currentPrice:
						price = str(localLib.roundHalf(self, agent['opening_buy_price']))
					else:
						price = str(localLib.roundHalf(self, agent['opening_buy_price'] + (agent['offset'] * agent['exit_multiplier'])))

				message = 'api_key=' + self.key + '&order_id=' + genericOrderID + '&p_r_price=' + price +\
						   '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature

				# connect and send request
				connection = self.subNetwork("POST", "/v2/private/order/replace?", signedMessage)
				resDict = self.returnData(connection)
				break
			except Exception as e:
				fails += 1
				self.logger.error('failed cancel' + str(e) + agent['entry_id'])
				time.sleep(1)
				if fails > 2:
					return resDict

	def fetchOrders(self):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				connection = self.subNetwork("GET", "/v2/private/order?", signedMessage)
				response = connection.getresponse()
				resDict = json.loads(response.read())
				connection.close()
				if resDict['ret_code'] != 0:
					raise Exception(resDict)

				elif len(resDict['result']) > 0:
					self.orderList = resDict['result']
					break
				else:
					self.orderList = []
					break
			except Exception as e:
				fails += 1
				self.logger.error('failed order fetch' + str(e))
				time.sleep(1)
				if fails > 2:
					self.orderList = []
					return []

	def fetchBalance(self):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				connection = self.subNetwork("GET", "/v2/private/wallet/balance?", signedMessage)
				response = connection.getresponse()
				resDict = json.loads(response.read())
				connection.close()
				if resDict['ret_code'] != 0:
					raise Exception(resDict)

				else:
					return float(resDict['result'][self.asset.upper()[:3]]['available_balance'])
			except Exception as e:
				fails += 1
				self.logger.error('failed balance fetch' + str(e))
				time.sleep(1)
				if fails > 2:
					self.orderList = []
					return []
		
	def testCall(self):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				connection = self.subNetwork("GET", "/v2/private/wallet/balance?", signedMessage)
				response = connection.getresponse()
				resDict = json.loads(response.read())
				connection.close()
				if resDict['ret_code'] == 10004:
					print('CONFIG ERROR: incorrect private key')
					print(resDict)
					time.sleep(30)
					exit()
				elif resDict['ret_code'] == 10003:
					print('CONFIG ERROR: incorrect public key')
					print(resDict)
					time.sleep(30)
					exit()
				elif resDict['ret_code'] != 0:
					raise Exception(resDict)
				else:
					return resDict
			except Exception as e:
				print('failed init test\n')
				print(e)
				time.sleep(30)
				exit()
				
	def fetchPrice(self):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				connection = self.subNetwork("GET", "/v2/public/tickers?", signedMessage)
				response = connection.getresponse()
				resDict = json.loads(response.read())
				connection.close()
				if resDict['ret_code'] != 0:
					raise Exception(resDict)

				else:
					return float(resDict['result'][0]['last_price'])
			except Exception as e:
				fails += 1
				self.logger.error('failed balance fetch' + str(e))
				time.sleep(1)
				if fails > 2:
					self.orderList = []
					return []
				
	def returnData(self, connection):
		response = connection.getresponse()
		resDict = json.loads(response.read())
		connection.close()

		# check response
		if resDict['ret_code'] == 33004:
			print('API key is expired!')
			exit()
		elif resDict['ret_code'] == 30032:
			#order already filled
			self.logger.info('resdict from returndata()'+ str(resDict))
			return resDict
		elif resDict['ret_code'] == 30084:
			#leverage already isolated
			self.logger.info('resdict from returndata()'+ str(resDict))
			return resDict
		elif resDict['ret_code'] == 30037:
			#order already cancelled
			self.logger.info('resdict from returndata()'+ str(resDict))
			return resDict
		elif resDict['ret_code'] == 30021:
			print('INSUFFICIENT BALANCE FOR ORDER. REDUCE ORDER SIZE')
			exit()
		elif resDict['ret_code'] == 34015:
			self.logger.info('resdict from returndata()'+ str(resDict))
			return resDict
		elif resDict['ret_code'] == 34036:
			#leverage not modified
			#self.logger.info('resdict from returndata()'+ str(resDict))
			return resDict
		elif resDict['ret_code'] == 30076:
			#replace order with same params
			#self.logger.info('resdict from returndata()'+ str(resDict))
			return resDict
		elif resDict['ret_code'] != 0:
			self.logger.info('resdict from returndata()'+ str(resDict))
			return resDict
		else:
			return resDict

	def switchLeverage(self,lev):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				#switch to cross
				if lev == 0:
					IsoCross=False
				#switch to iso
				else:
					IsoCross=True
				message = 'api_key=' + self.key + '&buy_leverage='+str(lev)+'&is_isolated='+str(IsoCross)+'&recv_window=10000000000000&sell_leverage='+str(lev)+'&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				connection = self.subNetwork("POST", "/v2/private/position/switch-isolated?", signedMessage)
				resDict = self.returnData(connection)
				break

			except Exception as e:
				fails += 1
				self.logger.error('failed switch leverage' + str(e))
				time.sleep(1)
				if fails > 4:
					return resDict
				
				
	def setLeverage(self,lev):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				if lev == 0:
					message = 'api_key=' + self.key + '&leverage='+str(lev)+'&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
					signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
					signedMessage = message + "&sign=" + signature
					connection = self.subNetwork("POST", "/v2/private/position/leverage/save?", signedMessage)
					resDict = self.returnData(connection)
				else:
					message = 'api_key=' + self.key + '&leverage='+str(lev)+'&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
					signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
					signedMessage = message + "&sign=" + signature
					connection = self.subNetwork("POST", "/v2/private/position/leverage/save?", signedMessage)
					resDict = self.returnData(connection)
				break

			except Exception as e:
				fails += 1
				self.logger.error('failed set leverage' + str(e))
				time.sleep(1)
				if fails > 4:
					return resDict

	def fetchPosition(self):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				connection = self.subNetwork("GET", "/v2/private/position/list?", signedMessage)
				resDict = self.returnData(connection)
				currentPos = resDict['result']['size']
				currentSide = resDict['result']['side']

				return currentPos, currentSide

			except Exception as e:
				fails += 1
				self.logger.error('failed fetch position' + str(e))
				time.sleep(1)
				if fails > 4:
					return 0, 'None'
	

	def fetchLeverage(self):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				connection = self.subNetwork("GET", "/v2/private/position/list?", signedMessage)
				resDict = self.returnData(connection)
				side = str(resDict['result']['side'])
				size = int(resDict['result']['size'])
				avgEntry = float(resDict['result']['entry_price'])
				positionValue = float(resDict['result']['position_value'])
				orderMargin = float(resDict['result']['order_margin'])
				walletBalance = float(resDict['result']['wallet_balance'])
				availableMarginTotal = walletBalance - orderMargin
				effectiveLeverage = float(resDict['result']['effective_leverage'])
				if availableMarginTotal == 0:
					print('no available margin')
				
				if resDict['result']['is_isolated'] == False and effectiveLeverage == 100:
					return([0,side,size,avgEntry])
				else:
					return([effectiveLeverage,side,size,avgEntry])

			except Exception as e:
				fails += 1
				self.logger.error('failed fetch leverage' + str(e))
				time.sleep(1)
				if fails > 4:
					return 0

	def fetchEquity(self,asset):
		fails = 0
		while True:
			try:
				timestamp = str(int(datetime.datetime.now().timestamp() * 1000) - 2000)
				message = 'api_key=' + self.key + '&coin='+asset[:3].upper()+'&recv_window=10000000000000&symbol=' + self.asset.upper() + '&timestamp=' + timestamp
				signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
				signedMessage = message + "&sign=" + signature
				connection = self.subNetwork("GET", "/v2/private/wallet/balance?", signedMessage)
				resDict = self.returnData(connection)
				equity = float(resDict['result'][asset[:3].upper()]['equity'])
				return equity
			
			except Exception as e:
				fails += 1
				self.logger.error('failed fetch leverage' + str(e))
				time.sleep(1)
				if fails > 4:
					return 0

	def closePosMarket(self, size, side):
		timestamp = int(datetime.datetime.now().timestamp() * 1000) - 2000
		message = 'api_key=' + self.key + '&order_type=Market&qty=' + str(
			size) + '&recv_window=10000000000000&side=' + side + '&symbol=' + self.asset.upper() + '&time_in_force=GoodTillCancel&timestamp=' + str(
			timestamp)
		signature = hmac.new(self.private.encode(), message.encode(), digestmod=hashlib.sha256).hexdigest()
		signedMessage = message + "&sign=" + signature
		resDict = self.sendOrder(signedMessage)

	def rsiReading(self, rsiPeriod):
		timestamp = int(datetime.datetime.now().timestamp())
		resDict = self.priceCandles('1', timestamp)
		candleDB = []
		# loop through last 100 candles
		for candles in resDict['result']:
			for keys in candles:
				# type convert
				if str(candles[keys]).isdigit() or str(candles[keys]).replace(".", "", 1).isdigit():
					candles[keys] = float(candles[keys])
			# add data to DB
			candleDB.append(candles)

			# calc rsi and fill in DB
			candleDB[-1]['rsi'] = localLib.rsiFunc(candleDB, int(rsiPeriod))

		with open("../dumps/candles.csv", "w", newline='\n') as f:
			candleList = csv.writer(f)
			candleList.writerow(["symbol", "interval", "open_time", "open", "high", "low", "close", "volume", "turnover"])
			for eachCandle in candleDB:
				coolList=[]
				coolList.append(eachCandle['symbol'])
				coolList.append(eachCandle['interval'])
				coolList.append(eachCandle['open_time'])
				coolList.append(eachCandle['open'])
				coolList.append(eachCandle['high'])
				coolList.append(eachCandle['low'])
				coolList.append(eachCandle['close'])
				coolList.append(eachCandle['volume'])
				coolList.append(eachCandle['turnover'])
				candleList.writerow(coolList)
		return candleDB

	def cancelOpens(self, offset):
		delList =[]
		for idx, order in enumerate(self.orderList):
			if len(order['order_link_id'].split("-")) == 3:
				agent_id, x, user = order['order_link_id'].split("-")
				ordertype, unix = x.split("=")
				if ordertype[0] == '1':
					for entry in offset:
						if entry['entry_id'] == agent_id:
							self.cancelOrder(order)
							if ordertype[1] == 's':
								entry['sell_status'] = 'looking_to_open'
							if ordertype[1] == 'b':
								entry['buy_status'] = 'looking_to_open'
							delList.append(idx)
		self.orderList = [i for j, i in enumerate(self.orderList) if j not in delList]
		return offset

	# def errorDecorator(self, func):
	#     def errorWrapper(*args, **kwargs):
	#         fails = 0
	#         while True:
	#             try:
	#                 resDict = func(*args, **kwargs)
	#                 break
	#             except Exception as e:
	#                 fails += 1
	#                 self.logger.error('failed sending order' + str(e))
	#                 time.sleep(1)
	#                 if fails > 2:
	#                     return
	#         return resDict
	#     return errorWrapper()
