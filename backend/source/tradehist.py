import requests
import pandas as pd
import numpy as np
from dataframes import preprocessResponse
import time
 
apiUrl = 'http://188.166.30.177:5430/api/v1/metrics?token=MwT5xh1yay'


# return agent information of trades
def getAgentInfo(network, user, version, instance):  # ADD FILTER INSTANCE
    while True:
        try:
            params = {'version': version, 'network': network, 'user_id': user, 'instance': instance}
            resp = requests.get(apiUrl, params)
            df = preprocessResponse(resp)
            
            if not df.empty:
                dfAgents = pd.DataFrame(list(df['agent_info']))
                dfAgents = dfAgents[['rsiOB', 'rsiOS', 'entry_id', 'closing_buy_price', 'opening_buy_price',
                                     'closing_sell_price', 'opening_sell_price', 'closing_buy_timestamp',
                                     'opening_buy_timestamp', 'closing_sell_timestamp', 'opening_sell_timestamp',
                                     'fitness_score','tag']]
                
                dfAgents=dfAgents.dropna()
                return dfAgents
            else:
                return pd.DataFrame()
        except:
            print('failed gats call')
            time.sleep(2)

# return min and max timestamps of logged trades
def timings(df_long, df_short):
    minS = min(df_short['Time'])
    maxS = max(df_short['Time'])
    minL = min(df_long['Time'])
    maxL = max(df_long['Time'])
    if minS < minL:
        minn = minS
    else:
        minn = minL
    if maxS > maxL:
        maxx = maxS
    else:
        maxx = maxL
    return minn, maxx


# process returning dataframe that will allow plotly to neatly plot
def sort_trades(network, user, version, instance, returnRange=False):
    dfAgent = getAgentInfo(network, user, version, instance)
    if not dfAgent.empty:
        dfShort = dfAgent[(dfAgent['closing_buy_timestamp'] != 0) & (dfAgent['tag'] == '-2b')]
        dfShortOpen = dfShort[
            ['rsiOB', 'rsiOS', 'entry_id', 'opening_sell_price', 'opening_sell_timestamp', 'fitness_score']]
        dfShortClose = dfShort[
            ['rsiOB', 'rsiOS', 'entry_id', 'closing_buy_price', 'closing_buy_timestamp', 'fitness_score']]
        dfLong = dfAgent[(dfAgent['closing_sell_timestamp'] != 0) & (dfAgent['tag'] == '-2b')]
        dfLongOpen = dfLong[
            ['rsiOB', 'rsiOS', 'entry_id', 'opening_buy_price', 'opening_buy_timestamp', 'fitness_score']]
        dfLongClose = dfLong[
            ['rsiOB', 'rsiOS', 'entry_id', 'closing_sell_price', 'closing_sell_timestamp', 'fitness_score']]

        for dfs in [dfShortOpen, dfShortClose, dfLongOpen, dfLongClose]:
            dfs.columns = ['OB', 'OS', 'ID', 'Price', 'Time', 'score']

        dfShort = pd.concat([dfShortOpen, dfShortClose]).sort_index(kind='merge')
        dfLong = pd.concat([dfLongOpen, dfLongClose]).sort_index(kind='merge')
        dfShort['Time'] = (dfShort['Time'] / 1000).astype(float).apply(
            lambda x: pd.to_datetime(x, unit='s') if x != 0 else 0)
        dfLong['Time'] = (dfLong['Time'] / 1000).astype(float).apply(
            lambda x: pd.to_datetime(x, unit='s') if x != 0 else 0)
        placeholderS = pd.Series(np.nan, dfShort.columns)
        placeholdeL = pd.Series(np.nan, dfLong.columns)
        groupL = np.arange(len(dfLong)) // 2
        groupS = np.arange(len(dfShort)) // 2
        dfShort = dfShort.groupby(groupS, group_keys=False).apply(lambda d: d.append(placeholderS, ignore_index=True))\
            .reset_index(drop=True)
        dfLong = dfLong.groupby(groupL, group_keys=False).apply(lambda d: d.append(placeholdeL, ignore_index=True))\
            .reset_index(drop=True)
        if returnRange:
            minn, maxx = timings(dfLong, dfShort)
            
            return dfShort, dfLong, minn, maxx
        else:
            return dfShort, dfLong
    else:
        return pd.DataFrame(), pd.DataFrame()
