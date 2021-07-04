import tulipy as ti
import pandas as pd
import random
import numpy as np
import ast


def get_prices(minn, maxx, interval):
    df = pd.DataFrame()
    step_size = (interval * 60 * 200)
    for i in range(int(math.ceil((maxx-minn)/1000) / step_size)):
        step = int(math.ceil((minn / 1000) + i * step_size))
        if step > current:
            break
        params = {"symbol": 'BTCUSD', 'interval': interval, 'from': step, 'limit': 200}
        api_url_base = 'https://api.bybit.com/v2/public/kline/list'
        full = requests.get(api_url_base, params=params).json()
        data = full['result']
        df2 = pd.DataFrame(data)
        df2['Timeframe'] = interval
        df = df.append(df2)
    df['open_time'] = df['open_time'] + 60
    df['open_time'] = pd.to_datetime(df['open_time'], unit='s')
    return df


def select_indicators(dataframe, value):
    prices = 0
    df = pd.DataFrame(columns=['Values', 'Indicator', 'P1', 'P2'])
    dataframe['close'] = pd.to_numeric(dataframe['close'])
    if not any(value):
        return df
    try:
        value = ast.literal_eval(value)
    except:
        return False, False

    for k, v in value.items():
        df_prices = pd.DataFrame(columns=['Indicator', 'P1', 'P2'])
        if k[:-1] == 'ema':
            try:
                df_prices['Values'] = ti.ema(dataframe['close'].to_numpy(), int(v))
                df_prices['Indicator'] = k
                df_prices['P1'] = v
                df_prices['P2'] = 0
            except:
                return False, False
        if k[:-1] == 'sma':
            try:
                df_prices['Values'] = ti.sma(dataframe['close'].to_numpy(), int(v))
                df_prices['Indicator'] = k
                df_prices['P1'] = v
                df_prices['P2'] = 0
            except:
                return False, False
        if k[:-1] == 'st':
            try:
                dataframe = dataframe[['open', 'high', 'low', 'close']]
                dataframe = dataframe.apply(pd.to_numeric)
                prices = st(dataframe, v[1], v[0])
                df_prices['Values'] = prices['SuperTrend']
                df_prices['Indicator'] = k
                df_prices['P1'] = v[1]
                df_prices['P2'] = v[0]
            except:
                return False, False

        df = df.append(df_prices)
    df = df.reset_index()
    return df, value

def st(df, f, n): #df is the dataframe, n is the period, f is the factor; f=3, n=7 are commonly used.
    #Calculation of ATR
    df['H-L']=abs(df['high']-df['low'])
    df['H-PC']=abs(df['high']-df['close'].shift(1))
    df['L-PC']=abs(df['low']-df['close'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1)
    df['ATR'] = np.nan
    df.loc[n-1,'ATR']=df['TR'][:n-1].mean() #.ix is deprecated from pandas verion- 0.19
    for i in range(n, len(df)):
        df['ATR'].iloc[i]=(df['ATR'].iloc[i-1]*(n-1)+ df['TR'].iloc[i])/n

    #Calculation of SuperTrend
    df['Upper Basic']=(df['high']+df['low'])/2+(f*df['ATR'])
    df['Lower Basic']=(df['high']+df['low'])/2-(f*df['ATR'])
    df['Upper Band']=df['Upper Basic']
    df['Lower Band']=df['Lower Basic']

    for i in range(n, len(df)):
        if df['close'].iloc[i-1]<=df['Upper Band'].iloc[i-1]:
            df['Upper Band'].iloc[i]=min(df['Upper Basic'].iloc[i],df['Upper Band'].iloc[i-1])
        else:
            df['Upper Band'].iloc[i]=df['Upper Basic'].iloc[i]
    for i in range(n,len(df)):
        if df['close'].iloc[i-1]>=df['Lower Band'].iloc[i-1]:
            df['Lower Band'].iloc[i]=max(df['Lower Basic'].iloc[i], df['Lower Band'].iloc[i-1])
        else:
            df['Lower Band'].iloc[i]=df['Lower Basic'].iloc[i]
    df['SuperTrend']=np.nan
    for i in df['SuperTrend']:
        if df['close'].iloc[n-1]<=df['Upper Band'].iloc[n-1]:
            df['SuperTrend'].iloc[n-1]=df['Upper Band'].iloc[n-1]
        elif df['Close'].iloc[n-1]>df['Upper Band'].iloc[i]:
            df['SuperTrend'].iloc[n-1]=df['Lower Band'].iloc[n-1]
    for i in range(n,len(df)):
        if df['SuperTrend'].iloc[i-1]==df['Upper Band'].iloc[i-1] and df['close'].iloc[i]<=df['Upper Band'].iloc[i]:
            df['SuperTrend'].iloc[i]=df['Upper Band'].iloc[i]
        elif  df['SuperTrend'].iloc[i-1]==df['Upper Band'].iloc[i-1] and df['close'].iloc[i]>=df['Upper Band'].iloc[i]:
            df['SuperTrend'].iloc[i]=df['Lower Band'].iloc[i]
        elif df['SuperTrend'].iloc[i-1]==df['Lower Band'].iloc[i-1] and df['close'].iloc[i]>=df['Lower Band'].iloc[i]:
            df['SuperTrend'].iloc[i]=df['Lower Band'].iloc[i]
        elif df['SuperTrend'].iloc[i-1]==df['Lower Band'].iloc[i-1] and df['close'].iloc[i]<=df['Lower Band'].iloc[i]:
            df['SuperTrend'].iloc[i]=df['Upper Band'].iloc[i]
    return df