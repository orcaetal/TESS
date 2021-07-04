import pandas as pd # glorious panda
import time # time as you know it
import json # enables working with JSON data
import requests # enables HTTP
import os # for the dangerous people
from datetime import datetime # time for own use
import pickle  # store information for later use
import os # delete as double
import traceback #gives all the information regarding the exception so it becomes easier to track one and fix it

pd.options.mode.chained_assignment = None  # default='warn' -> enables setting values on a copy of a slice
agentFilePath = '\\agentDump.json'
varFilePath = '\\varDump.json'
orderFilePath = '\\orderDump.csv'
historyFilePath = '\\historyDump.json'
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
logFolder = os.path.abspath('../logs')
dumpsFolder = os.path.abspath('../dumps')
api_url_base = 'http://188.166.30.177:5430/api/v1/metrics?token=MwT5xh1yay'
prevPrice = 0

# return list with subfolders
def getFolders(thisFolder, numbers=False):
    if numbers:
        folders = [x[0][-1] for x in os.walk(thisFolder)] # if there are two or more tables present
    else:
        folders = [x[0] for x in os.walk(thisFolder)] # if there is one table present
    return folders


# returns latest candle given time interval
def updateCandle(timenow, url, interval, asset):
    while True:
        try:
            candle = pd.read_csv('../dumps/candles.csv') # returns the "result" column 
            candle = candle.iloc[-1] # returns the last row of the "result" column
            #print('candle',candle)
            break
        except:
            print('waiting on candles.csv')
            time.sleep(1)
    return candle


# # run once to fill OHLC chart
# def initialize(start, url, interval, asset):
#     print('initialized')
#     params = {"symbol": asset.upper(), 'interval': interval, 'from': start, 'limit': 200}
#     data = requests.get(url, params=params).json()
#     dataframe = pd.DataFrame(data['result'])
#     dataframe['open_time'] = dataframe['open_time']
#     timeAxis = pd.to_datetime(dataframe['open_time'], unit='s')
#     return dataframe, timeAxis


# return the agents
def agentFrame(thisFolder, botNumber):
    while True:
        try:
            df = pd.read_csv(thisFolder + f'\\{botNumber}\\runningTable.csv')
            break
        except:
            #traceback.print_exc()
            time.sleep(0.1)
    return df

# return the agents
def tradesFrame(thisFolder):
    while True:
        try:
            df = pd.read_csv(thisFolder + f'\\tradelog.csv')
            dfLong = df[df['Side']=='Long']
            dfShort = df[df['Side']=='Short']
            break
        except Exception as e:
            #traceback.print_exc()
            print('trades issue',e)
            time.sleep(0.1)
    return dfShort, dfLong

#return the equity data
def equityFrame(thisFolder):
    while True:
        try:
            df = pd.read_csv(thisFolder + f'\\equity.csv')
            startEq = df.iloc[0]['equity']
            #print('start',startEq)
            df['equity'] = (df['equity'] - startEq) * 10**8
            #print('dfeq',df['equity'])
            df['time'] = df['time']/100
            startTime = df.iloc[0]['time']
            df['time'] = df['time']-startTime
            break
        except Exception as e:
            #print('equity issue',e)
            time.sleep(1)
    return df


# return the orders placed
#def orderFrame(this_folder, bot_no):
#    global prevPrice
#    while True:
#        try:
#            currentPrice = pd.read_csv(this_folder + f'\\candles.csv')
#            currentPrice = currentPrice['close'].iloc[-1]
#            folders = getFolders(this_folder)
#            if os.path.isfile(folders[bot_no] + orderFilePath):
#                df = pd.read_csv(folders[bot_no] + orderFilePath)
#            break
#
        # except pd.errors.EmptyDataError:
        #     # no open orders
        #     time.sleep(0.1)
        # except IndexError:
        #     # length of botlist too small while oracle loads bots (bad user)
        #     print('...Loading..')
        #     time.sleep(1)
        # except FileNotFoundError:
        #     #attempt at second instance by bad user briefly deletes files
        #     print('...Loading...')
        #     time.sleep(1)
        # except:
        #     print("\nOrder Frame exception: ["+traceback.format_exc()+"]")
    #     #     time.sleep(1)
    #     # 
    # 
    # try:
    #     df['order_link_id'] = df['order_link_id'].str.split(pat='-')
    #     df['side'] = df['order_link_id'].apply(lambda x: "order" if not x[0] else x[1][1])
    #     df['open/close'] = df['order_link_id'].apply(lambda x: "order" if not x[0] else x[1][0]).apply(
    #         lambda x: 'opening' if x == '1' else 'closing' if x=='2' else "order") # if x = 1 then order is opening, if x = 2 then order is closing 
    #     df['agent'] = df['order_link_id'].apply(lambda x: "Manual" if not x[0] else x[0])
    #     df['color'] = df['side'].apply(
    #         lambda x: 'rgb(200, 0, 0)' if x=='s' else 'rgb(0, 200, 0)' if x=='b' else 'rgb(180, 180, 180)')
    #     # the thing below leaves only the "order_id", "side", "price" & "qty" from the bybit api
    #     df = df.drop(['user_id', 'symbol', 'order_type', 'time_in_force', 'order_status', 'ext_fields',
    #                   'last_exec_time', 'last_exec_price', 'leaves_qty', 'leaves_value', 'cum_exec_qty',
    #                   'cum_exec_value', 'cum_exec_fee', 'reject_reason', 'order_link_id', 'created_at', 'updated_at',
    #                   'order_id'], axis=1)
    #     division = list(df.ne(df.shift()).filter(like='side').apply(lambda x: x.index[x].tolist()))[0][-1]
    #     df = df.reset_index()
    # except Exception as e:
    #     pass
    # 
    # # putting a blank line down
    # try:
    #     whiteLine = pd.DataFrame(
    #         {'side': 'price', 'price': float(currentPrice), 'qty': '----', 'open/close': 'current', 'agent': 'XXX',
    #                 'color': 'rgb(255, 255, 255)'}, index=[0])
    #     prevPrice = currentPrice
    # except:
    #     print('whiteline failure')
    #     time.sleep(0.1)
    # 
    # 
    # try:
    #     df['color'] = df['side'].apply(
    #         lambda x: 'rgb(200, 0, 0)' if x == 's' else 'rgb(0, 200, 0)' if x=='b' else 'rgb(180, 180, 180)')
    #     df = pd.concat([df.iloc[:division], whiteLine, df.iloc[division:]]) # ? Concatenate pandas objects along a particular axis with optional set logic along the other axes.
    #     df = df.sort_values(by=['price', 'side'], ascending=[False, False])
    # except:
    #     try:
    #         df['color'] = df['side'].apply(
    #             lambda x: 'rgb(200, 0, 0)' if x == 's' else 'rgb(0, 200, 0)' if x=='b' else 'rgb(180, 180, 180)')
    #         df = df.append(whiteLine)
    #         df = df.sort_values(by=['price', 'side'], ascending=[False, False])
    #     except:
    #         df = whiteLine
    # return df



# return pnl and leverage information
def infoFrame(n): # n is the botnumber
    while True:
        try:
            temp = {}
            with open(f'../dumps/{n}/pnls.pickle', 'rb') as handle:
                pnlsDict = pickle.load(handle)
            with open(f'../dumps/{n}/avgEntry.pickle', 'rb') as handle:
                avgEntry = pickle.load(handle)
            temp['realized pnl'] = pnlsDict['rpnl']
            temp['unrealized pnl'] = pnlsDict['upnl']
            temp['net pnl'] = pnlsDict['net']
            temp['avgEntry'] = avgEntry['avgEntry']
            temp['pos'] = avgEntry['pos']
            break
        except:
            #print('infoframe issue')
            time.sleep(0.1)
    return temp


# get the reponse into pandas format
def preprocessResponse(resp):
    try:
        full = resp.json()
        data = full['data']
        df = pd.DataFrame(data)
        df = pd.DataFrame(list(df['metrics']))
        return df
    except:
        return pd.DataFrame()

def tradeStatus(botNo, preprocc=True):
    while True:
        try:
            status = pd.read_csv(dumpsFolder + f'\\{botNo}\\runningTable.csv')
            break
        except:
            #print('...loading runningtable.csv')
            time.sleep(0.1)

    while True:
        try:
            if preprocc:
                status['opening_buy_timestamp'] = status['opening_buy_timestamp'].apply(
                    lambda x: datetime.utcfromtimestamp(x / 1000).strftime("%Y-%m-%d %H:%M:%S") if x != 0 else 0)
                status['opening_sell_timestamp'] = status['opening_sell_timestamp'].apply(
                    lambda x: datetime.utcfromtimestamp(x / 1000).strftime("%Y-%m-%d %H:%M:%S") if x != 0 else 0)
                status['upnl_long'] = (status['upnl_long']).round(6)
                status['upnl_long_c'] = (status['upnl_long']).apply(
                    lambda x: 'rgb(139,0,0)' if x < 0 else 'rgb(0,139,70)' if x > 0 else 'rgb(190, 190, 190)')
                status['rpnl_long'] = (status['rpnl_long']).round(6)
                status['rpnl_long_c'] = (status['rpnl_long']).apply(
                    lambda x: 'rgb(139,0,0)' if x < 0 else 'rgb(0,139,70)' if x > 0 else 'rgb(190, 190, 190)')
                
                status['upnl_short'] = (status['upnl_short']).round(6)
                status['upnl_short_c'] = (status['upnl_short']).apply(
                    lambda x: 'rgb(139,0,0)' if x < 0 else 'rgb(0,139,70)' if x > 0 else 'rgb(190, 190, 190)')
                status['rpnl_short'] = (status['rpnl_short']).round(6)
                status['rpnl_short_c'] = (status['rpnl_short']).apply(
                    lambda x: 'rgb(139,0,0)' if x < 0 else 'rgb(0,139,70)' if x > 0 else 'rgb(190, 190, 190)')
                status['buy_status'] = status['buy_status'].apply(lambda x: x.replace('_', " "))
                status['buy_status_c'] = status['buy_status'].apply(
                    lambda
                        x: 'rgb(255, 255, 255)' if x == 'trailing tp' or x == 'trailing entry' else 'rgb(190, 190, 190)')
                status['sell_status'] = status['sell_status'].apply(lambda x: x.replace('_', " "))
                status['sell_status_c'] = status['sell_status'].apply(
                    lambda
                        x: 'rgb(255, 255, 255)' if x == 'trailing tp' or x == 'trailing entry' else 'rgb(190, 190, 190)')
                break
            else:
                break
        except Exception as e:
            #print('tradestatus issue',e)
            time.sleep(1)
    return status
        

# This tells the ui at which timeframes the agents have opened their trades
def openings():
    while True:
        try:
            bots = getFolders(dumpsFolder, True)
            break
        except:
            print('get folders issue')
            time.sleep(0.1)
    
    df_short = pd.DataFrame()
    df_long = pd.DataFrame()
    df_short_filled = pd.DataFrame()
    df_long_filled = pd.DataFrame()
    df_short_exit = pd.DataFrame()
    df_long_exit = pd.DataFrame()
    
    for bot in bots[1:]:
        while True:
            try:
                status = pd.read_csv(dumpsFolder + f'\\{bot}\\runningTable.csv')
                break
            except:
                #print('searching for runningtables.csv')
                time.sleep(1)
        try:
            status_short = status[
                (status['opening_sell_timestamp'] != 0) & (status['sell_status'] == 'open_placed')]
            status_short_filled = status[
                 (status['opening_sell_timestamp'] != 0) & ((status['sell_status'] == 'looking_to_close') | (status['sell_status'] == 'close_placed') | (status['sell_status'] == 'trailing_tp'))]
            
            status_long = status[
                (status['opening_buy_timestamp'] != 0) & (status['buy_status'] == 'open_placed')]
            status_long_filled = status[
                 (status['opening_buy_timestamp'] != 0) & ((status['buy_status'] == 'looking_to_close') | (status['buy_status'] == 'close_placed') | (status['buy_status'] == 'trailing_tp'))]
            
            status_short_exit = status[
                (status['sell_status'] == 'close_placed') & (status['closing_buy_timestamp'] != 0)]
            status_long_exit = status[
                (status['closing_sell_timestamp'] != 0) & (status['buy_status'] == 'close_placed')]
            
            status_short['time'] = (status_short['opening_sell_timestamp'] / 1000).astype(float).apply(
                lambda x: pd.to_datetime(x, unit='s') if x != 0 else 0)
            status_long['time'] = (status_long['opening_buy_timestamp'] / 1000).astype(float).apply(
                lambda x: pd.to_datetime(x, unit='s') if x != 0 else 0)
            
            status_short_filled['time'] = (status_short_filled['opening_sell_timestamp'] / 1000).astype(float).apply(
                lambda x: pd.to_datetime(x, unit='s') if x != 0 else 0)
            status_long_filled['time'] = (status_long_filled['opening_buy_timestamp'] / 1000).astype(float).apply(
                lambda x: pd.to_datetime(x, unit='s') if x != 0 else 0)
            
            status_short_exit['time'] = (status_short_exit['closing_buy_timestamp'] / 1000).astype(float).apply(
                lambda x: pd.to_datetime(x, unit='s') if x != 0 else 0)
            status_long_exit['time'] = (status_long_exit['closing_sell_timestamp'] / 1000).astype(float).apply(
                lambda x: pd.to_datetime(x, unit='s') if x != 0 else 0)
            
        except Exception as e:
            #print('status issue',e)
            break
            
        df_short = df_short.append(status_short)
        df_long = df_long.append(status_long)
        df_short_filled = df_short_filled.append(status_short_filled)
        df_long_filled = df_long_filled.append(status_long_filled) 
        df_short_exit = df_short_exit.append(status_short_exit)
        df_long_exit = df_long_exit.append(status_long_exit)
        
    return df_short, df_long, df_short_filled, df_long_filled, df_short_exit, df_long_exit

