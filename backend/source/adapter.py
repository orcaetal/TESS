from abc import ABC, abstractmethod

# Majority of conventions and formats are derived form the Bybit exchange. If you are stuck you can always refer
# to the Bybit API to check the what the returned values should adhere to.
# xxx Vzer

class Adapter(ABC):
    @abstractmethod
    # Returns connection string to set up websocket connection
    def authenticate(self, v):
        pass

    @abstractmethod
    # Must return dict of a single order given message. Required keys:
    # 'status' key must be 'Filled', 'Cancelled' or 'PartiallyFilled'
    # 'id' of the agent
    # 'type' that is denoted in the orca style (1s, 1b, 2s, 2b)
    def orderData(self, message):
        pass
    
    @abstractmethod
    # Returns dict of position data from websocket subscription
    def positionData(self, message):
        pass

    @abstractmethod
    # Returns pricedata given message. A dict with keys
    # final (confirmation of last candle update),
    # cross_seq, close (closing price) and timestamp
    def priceAction(self, message):
        pass

    @abstractmethod
    # Return asset subscription string
    def subscribeAsset(self):
        pass

    @abstractmethod
    # Return order subscription string
    def subscribeOrder(self):
        pass

    @abstractmethod
    # Return execution subscription string
    def subscribeExecution(self):
        pass

    @abstractmethod
    def subscribePosition(self):
    # Return position subscription string
        pass

    @abstractmethod
    # Make connection with order (string containing e.g. "/v2/public/kline/list?")
    # and a signed message. This function will choose test- or mainnet given config file.
    # Returns connection
    def subNetwork(self, call, order, signedMessage):
        pass

    @abstractmethod
    # Send message to public API (e.g. /v2/public/kline/list?" for bybit)
    def sendPublicMessage(self, call, message):
        pass

    @abstractmethod
    # Send order. Is never explicitly called in bot.py
    def sendOrder(self, message):
        pass

    @abstractmethod
    # Return 200 candles in dict (format: https://bybit-exchange.github.io/docs/inverse/#t-querykline)
    # given timestamp and timeframe
    def priceCandles(self, timestamp, timeFrame):
        pass

    @abstractmethod
    # Return dict (format: https://bybit-exchange.github.io/docs/inverse/#t-querykline)
    # containing single candle of latest 4 hour 00:00 midnight candle Amsterdam time.
    def midnightCandle(self, midnightTime):
        pass

    @abstractmethod
    # Place market order
    def placeMarketOrder(self, agent, side, openOrClose):
        pass

    @abstractmethod
    # Place limit order
    def placeLimitOrder(self, agent, currentPrice, side, openOrClose):
        pass

    @abstractmethod
    # Cancel all pending orders
    def cancelAll(self):
        pass

    @abstractmethod
    # Cancel a single order
    def cancelOrder(self, agent):
        pass

    @abstractmethod
    # Cancel half of your orders (?)
    def cancelHalf(self):
        pass

    @abstractmethod
    # Replace a order given agent, price, orderID and side (orca style)
    def replaceOrder(self, agent, currentPrice, genericOrderID, side):
        pass

    @abstractmethod
    # fetch orders and return dict (format https://bybit-exchange.github.io/docs/inverse/#t-getactive)
    def fetchOrders(self):
        pass

    @abstractmethod
    # return dict, never explicitly called in bot.py
    # takes the connection as argument
    def returnData(self, connection):
        pass

    @abstractmethod
    # Set leverage
    def setLeverage(self):
        pass

    @abstractmethod
    # Return current position and side (format https://bybit-exchange.github.io/docs/inverse/#t-position)
    def fetchPosition(self):
        pass

    @abstractmethod
    # Return leverage (format https://bybit-exchange.github.io/docs/inverse/#t-position)
    def fetchLeverage(self):
        pass

    @abstractmethod
    # Close position
    def closePosMarket(self, size, side):
        pass

    @abstractmethod
    # Return rsi given rsiPeriod. More details on format ...
    def rsiReading(self, rsiPeriod):
        pass

    @abstractmethod
    # Cancel all open entry orders, this is the same as cancelAll but iterated over all orders
    def cancelOpens(self, offset):
        pass


