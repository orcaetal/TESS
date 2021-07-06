import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
import live_functions as live
from tradehist import sort_trades
import os
import time
import glob
import pickle
import pandas as pd
from dataframes import *
import datetime
from decimal import Decimal

config = live.loadConfig()
network = config['network']
version = config['version']
asset = config['asset']
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
logFolder = os.path.abspath('../logs')
dumpsFolder = os.path.abspath('../dumps')
interval = 1
dynamicInterval = 6000
dfIndicator = 0
start = int(time.time())
start -= 60*200
url = 0
dfOrders = 0
value = {}
currentPrice = 0
botNumber = 1
dataFrame = pd.DataFrame()

if network == 'testnet':
    url = 'https://api-testnet.bybit.com/v2/public/kline/list'
elif network == 'mainnet':
    url = 'https://api.bybit.com/v2/public/kline/list'
while True:
    try:
        with open('../dumps/user.pickle', 'rb') as handle:
            data = pickle.load(handle)
            user = data['id']
        with open('../dumps/instance.pickle', 'rb') as handle:
            instance = pickle.load(handle)
        break
    except(FileNotFoundError):
        print('...Loading')
        time.sleep(1)
        

while True:
    try:
        dataFrame = pd.read_csv('../dumps/candles.csv')
        dataFrame['open_time'] = dataFrame['open_time']
        timeAxis = pd.to_datetime(dataFrame['open_time'], unit='s')
        threads = glob.glob(os.path.abspath(os.path.join(os.getcwd(), os.pardir))+'\\active-tables\\*.csv')
        status = tradeStatus(botNumber)
        bots = getFolders(dumpsFolder, numbers=True)[1:]
        agents = agentFrame(dumpsFolder, botNumber)
        equity = equityFrame(dumpsFolder)
        dfTradesShort = pd.DataFrame()
        dfTradesLong = pd.DataFrame()
        info = infoFrame(n=1)
        print(f"ID:{instance}")
        break
    except Exception as e:
        #traceback.print_exc()
        print('waiting for candles to init')
        time.sleep(5)


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])


app.title = 'Live trading with TESS'


# important order
button3 = html.Button('Stop', id='btn3', n_clicks=0, style={'background-color': 'rgb(220, 0, 0)', 'border-color': 'rgb(255, 255, 255)', 'border-width': 'medium'})
button1 = html.Button('Run', id='btn1', n_clicks=0, style={'background-color': 'rgb(0, 220, 0)'})

equityLineChart = go.Figure(
    data=go.Scatter(x=equity['time'], y=equity['equity'],mode='lines'), layout=dict(
        uirevision=3, barmode='group', margin=dict(
            l=60, r=100, b=70, t=10
        ), plot_bgcolor='rgb(19, 23, 34)', paper_bgcolor='rgb(6, 6, 6)', xaxis=dict(
            tickformat='e', showgrid=False, visible=False
        ), font=dict(family="Helvetica", size=12, color='rgb(190, 190, 190)'
        )
    )
)

agentBarChart = go.Figure(
    data=[go.Bar(y=agents['rpnl_short'] * 10**8, x=agents['entry_id'], name='RPNL short'),
            go.Bar(y=agents['upnl_short'] * 10**8, x=agents['entry_id'], name='UPNL short'),
            go.Bar(y=agents['rpnl_long'] * 10**8, x=agents['entry_id'], name='RPNL long'),
            go.Bar(y=agents['upnl_long'] * 10**8, x=agents['entry_id'], name='UPNL long')], layout=dict(
        uirevision=3, barmode='group', margin=dict(
            l=60, r=30, b=70, t=10
        ), plot_bgcolor='rgb(19, 23, 34)', paper_bgcolor='rgb(6, 6, 6)', xaxis=dict(
            tickformat='e'
        ), font=dict(family="Helvetica", size=12, color='rgb(190, 190, 190)'
        ), legend=dict(yanchor="top",y=0.99,xanchor="left",x=-.2
        )
    )
)

countsBarChart = go.Figure(
    data=[go.Bar(
        x=agents['entry_id'], y=agents['buys_counter'], name='Longs', marker_color='rgb(0, 220, 0)',
        marker_line_color='rgb(100, 100, 100)'
    ), go.Bar(
        x=agents['entry_id'], y=agents['sells_counter'], name='Shorts', marker_color='rgb(220, 0, 0)',
        marker_line_color='rgb(100, 100, 100)'
    )], layout=dict(
        uirevision=7, barmode='stack', margin=dict(
            l=60, r=100, b=70, t=10
        ), plot_bgcolor='rgb(19, 23, 34)', paper_bgcolor='rgb(6, 6, 6)', xaxis=dict(
            tickformat='e'
        ), yaxis=dict(
            showgrid=False
        ), font=dict(
        family="Helvetica", size=12, color='rgb(190, 190, 190)'
        )
    )
)

candleChart = go.Figure(
    data=go.Candlestick(
        x=timeAxis, open=dataFrame['open'], high=dataFrame['high'], low=dataFrame['low'],
        close=dataFrame['close'], name='OHLC'
    ), layout=dict(
        uirevision=1, font=dict(
            family="Helvetica", size=12, color='rgb(190, 190, 190)'
        ), yaxis=dict(title=f'{asset.upper()} price'), xaxis=dict(rangeslider=dict(visible=False)), margin=dict(
            l=70, r=20, b=40, t=10
        ), plot_bgcolor='rgb(19, 23, 34)', paper_bgcolor='rgb(6, 6, 6)'
    )
)

if not dfTradesShort.empty:
    candleChart.add_trace(go.Scatter(dict(x=dfTradesShort['Time'], y=dfTradesShort['Price'], name='Short trade',
                                          line=dict(color='red', width=1, dash='dot'),
                                          connectgaps=False)))
if not dfTradesLong.empty:
    candleChart.add_trace(go.Scatter(dict(x=dfTradesLong['Time'], y=dfTradesLong['Price'], name='Long trade',
                                          line=dict(color='green', width=1, dash='dot'),
                                          connectgaps=False)))


infoString = f"Bot: {threads[0][:-4]} ------- Realized PNL: {info['realized pnl']:.8f}" \
             f"------- Unrealized PNL: {info['unrealized pnl']:.8f} ------- " \
             f"Net PNL:{ info['net pnl']:.8f}"
infoFig = dcc.Markdown(str(infoString))


statusTable = go.Figure(
        data=go.Table(
            header=dict(
                values=['Agent', 'Long status', 'Short status', 'Time Opening Long', 'Time Opening Short',
                        'UPNL-L', 'RPNL-L', 'UPNL-S', 'RPNL-S'],
                line_color=' black', fill_color='black',
                align=['left', 'center'], font=dict(
                    color='white', size=12
                )
            ), cells=dict(
                values=[status['entry_id'], status['buy_status'], status['sell_status'],
                        status['opening_buy_timestamp'], status['opening_sell_timestamp'], status['upnl_long'], status['rpnl_long'],
                        status['upnl_short'], status['rpnl_short']], line_color='darkslategray',
                fill_color=['rgb(19, 23, 34)'], align=['left', 'center'],
                font=dict(
                    color='rgb(190, 190, 190)', size=11
                )
            )
        ), layout=dict(uirevision=2, margin=dict(l=20, r=0, b=30, t=10), paper_bgcolor='rgb(6, 6, 6)')
    )

text1 = html.H1(
                children='Live Trading with TESS', style={'font-family': 'Helvetica', 'margin-left': 20,
                                                          'margin-right': -30, 'margin-bottom': '0px'}
)
text2 = html.H1(
    id='gen', children='by Genesis Algo ©', style={'font-family': 'Helvetica',
                                                   'font-size': 10, 'margin-left': 0,
                                                   'margin-top': 50, 'color': 'rgb(43, 191, 163)'}
)


inputText = dcc.Textarea(
    id='indics', value='{"ema1": 5, "sma1": 5}',
    style={'width': 350, 'margin': '0px', 'height': 30,
           'margin-left': '20px', 'margin-right': '40px'}
)

dropDown = dcc.Dropdown(id='dropdown', options=[{'label': bots[0], 'value': 0}], value=1,
                        style={'margin-right': '5px', 'margin-top': '15px', 'height': '30px', 'width': '250px',
                               'display': 'inline-block', 'font-size': 11})



app.layout = html.Div(
    [dcc.Interval(
    id='interval-component2', interval=dynamicInterval, n_intervals=0), html.Div([
        dbc.Row([
            dbc.Col(
                text1, width="auto"
            ), dbc.Col(
                text2
            ), dbc.Col(
                dropDown
            ), dbc.Col(
                html.Div([button1, button3], style={'margin-top': '30px'})
            ),
            dcc.Checklist(
                id = 'Checkbox',
                options=[
                    {'label': ' Show all tables', 'value': 'show_all'}
                ],
                value=['show_all'], style={'margin-top': '30px','margin-right': '300px'}
            ),  
        ]), dbc.Row(
                html.P(
                id="info", children=[infoFig], style={'margin-left': '50px', 'margin-top': '0px',
                                                      'margin-bottom': '0px', "color":'rgb(190, 190, 190)'}
                )
        )
    ]),
    html.Div([
        dcc.Graph(
            id='GraphBot-1', style={'height': '500px'}, figure=candleChart, config={'scrollZoom': True}
        )
    ]), html.Div(

    ), 
    html.Div(
        dbc.Row([
            dbc.Col(
                html.Div(
                    dcc.Graph(
                        id='equity_line', style={'height': '300px', 'margin-left': '20px'},
                        figure=equityLineChart
                    )
                ), width=5
            ), 
            dbc.Col(
                html.Div([
                    dcc.Graph(
                        id='agent_bar', style={'height': '300px', 'margin-right': '20px'},
                        figure=agentBarChart, config={'scrollZoom': True}
                    ),
                ]), width=7
            )
        ])
    ),html.Div(dcc.Graph(style={'overflow': 'visible', 'margin': '0px', 'width': '100%'}, id='status_table', figure=statusTable))]
)

buttonDict = {}
oldValue = None
@app.callback([Output('btn3', 'style'),
               Output('btn1', 'style'),
               Output('btn3', 'disabled'),
               Output('btn1', 'disabled'),
               Output('dropdown', 'disabled')],
              [Input('btn3', 'n_clicks'),
               Input('btn1', 'n_clicks'),
               Input('dropdown', 'value'),
               Input('interval-component2', 'n_intervals')])
def displayClick(btn3, btn1, value, n):
    
    while True:
        try:
            with open(f'../dumps/{value}/state.pickle', 'rb') as handle:
                state = pickle.load(handle)
            with open(f'../dumps/buttons.pickle', 'rb') as handle:
                buttonDict = pickle.load(handle)
            with open(f'../dumps/{value}/name.pickle', 'rb') as handle:
                name = pickle.load(handle)
                name = name.split('\\')[-1].rstrip('.csv')
            break
        except:
            #print('loading buttons')
            time.sleep(1)
    
    #grab list of sr and lm tables
    specialTables = live.specialTables(config)
    
    global oldValue
    style3 = None
    style1 = None
    cc = dash.callback_context
    ctx = [p for p in dash.callback_context.triggered]
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    
    if buttonDict is None:
        buttonDict = {}
        style1 = {'background-color': 'rgb(0, 220, 0)'}
        style3 = {'background-color': 'rgb(220, 0, 0)', 'border-color': 'rgb(255, 255, 255)', 'border-width': 'medium'}
        state['state'] = 'stop'
    if value not in buttonDict:
        style1 = {'background-color': 'rgb(0, 220, 0)'}
        style3 = {'background-color': 'rgb(220, 0, 0)', 'border-color': 'rgb(255, 255, 255)', 'border-width': 'medium'}
        #why was this here?  - breaks leverage manager activating table from oracle
        #state['state'] = 'stop'
    elif 'btn3' in changed_id and value in buttonDict and state != 'stop':
        style1 = {'background-color': 'rgb(0, 220, 0)'}
        style3 = {'background-color': 'rgb(220, 0, 0)', 'border-color': 'rgb(255, 255, 255)', 'border-width': 'medium'}
        state['state'] = 'stop'
        state['executed'] = False
    elif 'btn1' in changed_id and value in buttonDict and state != 'run':
        style1 = {'background-color': 'rgb(0, 220, 0)', 'border-color': 'rgb(255, 255, 255)', 'border-width': 'medium'}
        style3 = {'background-color': 'rgb(220, 0, 0)'}
        state['state'] = 'run'
        state['executed'] = False
    elif value in buttonDict:
        style3 = buttonDict[value][0]
        style1 = buttonDict[value][1]

    buttonDict[value] = [style3, style1]

    if state is not None:
        with open(f'../dumps/{value}/state.pickle', 'wb+') as handle:
            pickle.dump(state, handle)

    if buttonDict is not None:
        with open(f'../dumps/buttons.pickle', 'wb+') as handle:
            pickle.dump(buttonDict, handle)
    
    if name in specialTables:
        return buttonDict[value][0], buttonDict[value][1], True, True, False
    elif not state['executed']:
        return buttonDict[value][0], buttonDict[value][1], True, True, True
    else:
        return buttonDict[value][0], buttonDict[value][1], False, False, False


@app.callback(Output('GraphBot-1', 'figure'),
                [Input('interval-component2', 'n_intervals'),
                 Input('dropdown', 'value'),
                 Input('Checkbox','value')])
def updateLiveGraph(n,value,showAll):
    
    if len(showAll) > 0:
        showAllTables = True
    else:
        showAllTables = False
        
    global dynamicInterval
    currentTime = int(time.time())
    candle = updateCandle(currentTime, url, interval, asset)
    
    while True:
        try:
            dataFrame = pd.read_csv('../dumps/candles.csv')
            break
        except:
            #print('...Loading candles')
            time.sleep(1)
            
    if float(candle['open_time']) == dataFrame['open_time'].iloc[-1]:
        dataFrame.iloc[-1, :] = candle
    elif float(candle['open_time']) > dataFrame['open_time'].iloc[-1]:
        dataFrame = dataFrame.append(candle)
        
    
    agents = agentFrame(dumpsFolder, value)
    agents = agents['entry_id']
    positionFrame = equityFrame(dumpsFolder)
    while True:
        try:
            openShort, openLong, filledShort, filledLong, exitShort, exitLong = openings()
            
            # inefficient recalculates whole array, can be fixed but overcomplicates code. Revisit this later
            dfTradesShort, dfTradesLong = sort_trades(network, user, version, instance=instance)
            
            timeAxis = pd.to_datetime(dataFrame['open_time'], unit='s')
            latestCandle = dataFrame.iloc[-1]
            currentPrice = latestCandle['close']
            
            truncDF = dataFrame
            minSeries = truncDF.min()
            maxSeries = truncDF.max()
            minVal = minSeries['low'] - 200
            maxVal = maxSeries['high'] + 200
            minTime = timeAxis.iloc[0] 
            maxTime = timeAxis.iloc[-1] + datetime.timedelta(hours=1, minutes=00)
            data = [dict(type='candlestick', x=timeAxis, open=dataFrame['open'], high=dataFrame['high'],
                         low=dataFrame['low'], close=dataFrame['close'], name='OHLC',hoverinfo='skip')]
            layout = dict(uirevision=1, showlegend=False, font=dict(
                family="Helvetica",
                size=12,
                color='rgb(190, 190, 190)'
            ), yaxis=dict(title=f'{asset.upper()} price',range=[minVal,maxVal]), xaxis=dict(range = [minTime,maxTime],rangeslider=dict(visible=False)), margin=dict(
                l=70,
                r=20,
                b=40,
                t=10), hovermode = 'closest',plot_bgcolor='rgb(19, 23, 34)', paper_bgcolor='rgb(6, 6, 6)', textfont=dict(
                family="sans serif",
                size=18,
                color="white"
            )
                          )
            
            if not openShort.empty:
                
                for index, row in openShort.iterrows():
                    if showAllTables:
                        currentTime = timeAxis.iloc[-1] + datetime.timedelta(hours=100, minutes=30)
                        longestTime = timeAxis.iloc[0] - datetime.timedelta(hours=100, minutes=30)
                        tradeTime = pd.to_datetime(row['opening_sell_timestamp']/1000,unit='s')
                        ydata = [row['opening_sell_price'],row['opening_sell_price'],row['opening_sell_price']] 
                        xdata = [longestTime,tradeTime,currentTime]
                        
                        if row['opening_sell_price'] > currentPrice:
                            data.append(go.Scatter(
                                dict(x=xdata, y=ydata, mode='lines+markers', marker_symbol = 'line-ns-open',
                                 name='Open short', marker_line_width=1,
                                 line=dict(color='rgb(255,0,0)', width=0.5, dash='dash'),
                                 marker=dict(color='rgb(255,0,0)', size=5),
                                 text="Agent: " + row['entry_id'] + "<br> order price: " +
                                      str(row['opening_sell_price']))))
                            
                    elif row['entry_id'] in agents.values:
                        currentTime = timeAxis.iloc[-1] + datetime.timedelta(hours=100, minutes=30)
                        longestTime = timeAxis.iloc[0] - datetime.timedelta(hours=100, minutes=30)
                        tradeTime = pd.to_datetime(row['opening_sell_timestamp']/1000,unit='s')
                        ydata = [row['opening_sell_price'],row['opening_sell_price'],row['opening_sell_price']] 
                        xdata = [longestTime,tradeTime,currentTime]
                        
                        if row['opening_sell_price'] > currentPrice:
                            data.append(go.Scatter(
                                dict(x=xdata, y=ydata, mode='lines+markers', marker_symbol = 'line-ns-open',
                                 name='Open short', marker_line_width=1,
                                 line=dict(color='rgb(255,0,0)', width=0.5, dash='dash'),
                                 marker=dict(color='rgb(255,0,0)', size=5),
                                 text="Agent: " + row['entry_id'] + "<br> order price: " +
                                      str(row['opening_sell_price']))))
            
            if not openLong.empty:
                
                for index, row in openLong.iterrows():
                    if showAllTables:
                        currentTime = timeAxis.iloc[-1] + datetime.timedelta(hours=100, minutes=30)
                        longestTime = timeAxis.iloc[0] - datetime.timedelta(hours=100, minutes=30)
                        tradeTime = pd.to_datetime(row['opening_buy_timestamp']/1000,unit='s')
                        ydata = [row['opening_buy_price'],row['opening_buy_price'],row['opening_buy_price']] 
                        xdata = [longestTime,tradeTime,currentTime]
                        
                        if row['opening_buy_price'] < currentPrice:
                            data.append(go.Scatter(
                                dict(x=xdata, y=ydata, mode='lines+markers', marker_symbol = 'line-ns-open',
                                 name='Open long', marker_line_width=1,
                                 line=dict(color='rgb(22, 217, 0)', width=0.5, dash='dash'),
                                 marker=dict(color='rgb(22, 217, 0)', size=5),
                                 text="Agent: " + row['entry_id'] + "<br> order price: " +
                                      str(row['opening_buy_price']))))
                    elif row['entry_id'] in agents.values:
                        currentTime = timeAxis.iloc[-1] + datetime.timedelta(hours=100, minutes=30)
                        longestTime = timeAxis.iloc[0] - datetime.timedelta(hours=100, minutes=30)
                        tradeTime = pd.to_datetime(row['opening_buy_timestamp']/1000,unit='s')
                        ydata = [row['opening_buy_price'],row['opening_buy_price'],row['opening_buy_price']] 
                        xdata = [longestTime,tradeTime,currentTime]
                        
                        if row['opening_buy_price'] < currentPrice:
                            data.append(go.Scatter(
                                dict(x=xdata, y=ydata, mode='lines+markers', marker_symbol = 'line-ns-open',
                                 name='Open long', marker_line_width=1,
                                 line=dict(color='rgb(22, 217, 0)', width=0.5, dash='dash'),
                                 marker=dict(color='rgb(22, 217, 0)', size=5),
                                 text="Agent: " + row['entry_id'] + "<br> order price: " +
                                      str(row['opening_buy_price']))))
            
            valueList = agents.values.tolist()
            if not filledShort.empty:
                if not showAllTables:
                    filledShort = filledShort[filledShort['entry_id'].isin(valueList)]
                data.append(go.Scatter(
                        dict(x=filledShort['time'], y=filledShort['opening_sell_price'], mode='markers', 
                             name='Filled short', marker=dict(color='rgb(75,2,29)', size=10), hovertemplate='%{text}',
                             text="Agent: " + filledShort['entry_id'].astype(str) + "<br> order price: " +
                                  filledShort['opening_sell_price'].astype(str))))
            
            if not filledLong.empty:
                if not showAllTables:
                    filledLong = filledLong[filledLong['entry_id'].isin(valueList)]
                data.append(go.Scatter(
                        dict(x=filledLong['time'], y=filledLong['opening_buy_price'], mode='markers', 
                             name='Filled long', marker=dict(color='rgb(2,75,48)', size=10), hovertemplate='%{text}',
                             text="Agent: " + filledLong['entry_id'].astype(str) + "<br> order price: " +
                                  filledLong['opening_buy_price'].astype(str))))
            
            if not exitShort.empty:
                
                for index, row in exitShort.iterrows():
                    if showAllTables:
                        currentTime = timeAxis.iloc[-1] + datetime.timedelta(hours=100, minutes=30)
                        longestTime = timeAxis.iloc[0] - datetime.timedelta(hours=100, minutes=30)
                        tradeTime = pd.to_datetime(row['closing_buy_timestamp']/1000,unit='s')
                        ydata = [row['closing_buy_price'],row['closing_buy_price'],row['closing_buy_price']] 
                        xdata = [longestTime,tradeTime,currentTime]
                        
                        if row['closing_buy_price'] < currentPrice:
                            data.append(go.Scatter(
                                dict(x=xdata, y=ydata, mode='lines+markers', marker_symbol = 'line-ns-open',
                                 name='Close short', marker_line_width=1,
                                 line=dict(color='rgb(22, 217, 0)', width=0.5, dash='dashdot'),
                                 marker=dict(color='rgb(22, 217, 0)', size=5),
                                 text="Agent: " + row['entry_id'] + "<br> order price: " +
                                      str(row['closing_buy_price']))))
                            
                    elif row['entry_id'] in agents.values:
                        currentTime = timeAxis.iloc[-1] + datetime.timedelta(hours=100, minutes=30)
                        longestTime = timeAxis.iloc[0] - datetime.timedelta(hours=100, minutes=30)
                        tradeTime = pd.to_datetime(row['closing_buy_timestamp']/1000,unit='s')
                        ydata = [row['closing_buy_price'],row['closing_buy_price'],row['closing_buy_price']] 
                        xdata = [longestTime,tradeTime,currentTime]
                        
                        if row['closing_buy_price'] < currentPrice:
                            data.append(go.Scatter(
                                dict(x=xdata, y=ydata, mode='lines+markers', marker_symbol = 'line-ns-open',
                                 name='Close short', marker_line_width=1,
                                 line=dict(color='rgb(22, 217, 0)', width=0.5, dash='dashdot'),
                                 marker=dict(color='rgb(22, 217, 0)', size=5),
                                 text="Agent: " + row['entry_id'] + "<br> order price: " +
                                      str(row['closing_buy_price']))))
                    
            if not exitLong.empty:
                
                for index, row in exitLong.iterrows():
                    if showAllTables:
                        currentTime = timeAxis.iloc[-1] + datetime.timedelta(hours=100, minutes=30)
                        longestTime = timeAxis.iloc[0] - datetime.timedelta(hours=100, minutes=30)
                        tradeTime = pd.to_datetime(row['closing_sell_timestamp']/1000,unit='s')
                        ydata = [row['closing_sell_price'],row['closing_sell_price'],row['closing_sell_price']] 
                        xdata = [longestTime,tradeTime,currentTime]
                        
                        if row['closing_sell_price'] > currentPrice:
                            data.append(go.Scatter(
                                dict(x=xdata, y=ydata, mode='lines+markers', marker_symbol = 'line-ns-open',
                                 name='Close long', marker_line_width=1,
                                 line=dict(color='rgb(255, 0, 0)', width=0.5, dash='dashdot'),
                                 marker=dict(color='rgb(255,0,0)', size=5),
                                 text="Agent: " + row['entry_id'] + "<br> order price: " +
                                      str(row['closing_sell_price']))))
                    elif row['entry_id'] in agents.values:
                        currentTime = timeAxis.iloc[-1] + datetime.timedelta(hours=100, minutes=30)
                        longestTime = timeAxis.iloc[0] - datetime.timedelta(hours=100, minutes=30)
                        tradeTime = pd.to_datetime(row['closing_sell_timestamp']/1000,unit='s')
                        ydata = [row['closing_sell_price'],row['closing_sell_price'],row['closing_sell_price']] 
                        xdata = [longestTime,tradeTime,currentTime]
                        
                        if row['closing_sell_price'] > currentPrice:
                            data.append(go.Scatter(
                                dict(x=xdata, y=ydata, mode='lines+markers', marker_symbol = 'line-ns-open',
                                 name='Close long', marker_line_width=1,
                                 line=dict(color='rgb(255, 0, 0)', width=0.5, dash='dashdot'),
                                 marker=dict(color='rgb(255,0,0)', size=5),
                                 text="Agent: " + row['entry_id'] + "<br> order price: " +
                                      str(row['closing_sell_price']))))
                    
            
            if not dfTradesShort.empty:
                if not showAllTables:
                    dfTradesShort = dfTradesShort[(dfTradesShort['ID'].isin(valueList)) | (dfTradesShort['ID'].isnull())]
                data.append(go.Scatter(
                    dict(x=dfTradesShort['Time'], y=dfTradesShort['Price'], mode='lines+markers', marker_line_width=0.2,
                         name='Trade pair', line=dict(color='rgb(255, 255, 255)', width=1, dash='dashdot'), marker=dict(
                    color='rgb(75,2,29)', size=10), hovertemplate='%{text}',
                         text="Agent: " + dfTradesShort['ID'].astype(str) + "\n score: " +
                              round(dfTradesShort['score'], 5).astype(str) + "\n order price: " +
                              dfTradesShort['Price'].astype(str))))
            
            if not dfTradesLong.empty:
                if not showAllTables:
                    dfTradesLong = dfTradesLong[(dfTradesLong['ID'].isin(valueList)) | (dfTradesLong['ID'].isnull())]
                data.append(go.Scatter(
                    dict(x=dfTradesLong['Time'], y=dfTradesLong['Price'], mode='lines+markers', marker_line_width=0.2,
                         name='Trade pair', line=dict(color='rgb(255, 255, 255)', width=1, dash='dashdot'), marker=dict(
                    color='rgb(2,75,48)', size=10), hovertemplate='%{text}',
                         text="Agent: " + dfTradesLong['ID'].astype(str) + "\n score: " +
                              round(dfTradesLong['score'], 5).astype(str) + "\n order price: " +
                              dfTradesLong['Price'].astype(str))))
            
            #add position line
            if not positionFrame.iloc[-1]['size'] == 0:
                
                    currentTime = timeAxis.iloc[-1] + datetime.timedelta(hours=0, minutes=30)
                    youngestTime = timeAxis.iloc[-1] + datetime.timedelta(hours=100, minutes=30)
                    longestTime = timeAxis.iloc[0] - datetime.timedelta(hours=100, minutes=30)
                    #tradeTime = pd.to_datetime(row['closing_sell_timestamp']/1000,unit='s')
                    ydata = [positionFrame.iloc[-1]['entry'],positionFrame.iloc[-1]['entry'],positionFrame.iloc[-1]['entry']] 
                    xdata = [longestTime,currentTime,youngestTime]
                    
                    if positionFrame.iloc[-1]['side'] == "Sell":
                        data.append(go.Scatter(
                            dict(x=xdata, y=ydata, mode='lines+markers', marker_symbol = 'triangle-down',
                             name='Position', marker_line_width=0.2,
                             line=dict(color='rgb(255, 0, 0)', width=1.5, dash='dashdot'),
                             marker=dict(color='rgb(255,0,0)', size=15),
                             text="Sell " + str(positionFrame.iloc[-1]['size']) + " at " + str(round(positionFrame.iloc[-1]['entry'],2)))))
                    
                    if positionFrame.iloc[-1]['side'] == "Buy":
                        data.append(go.Scatter(
                            dict(x=xdata, y=ydata, mode='lines+markers',marker_symbol = 'triangle-up',
                             name='Position', marker_line_width=0.2,
                             line=dict(color='rgb(22, 217, 0)', width=1.5, dash='dashdot'),
                             marker=dict(color='rgb(22, 217, 0)', size=15),
                             text="Buy " + str(positionFrame.iloc[-1]['size']) + " at " + str(positionFrame.iloc[-1]['entry']))))
                        
            return {'data': data, 'layout': layout}
        except Exception as e:
            #print('this',e)
            time.sleep(1)

@app.callback(Output('equity_line', 'figure'),
              [Input('interval-component2', 'n_intervals')])
def updateEquityGraph(n):
    positionFrame = equityFrame(dumpsFolder)
    if positionFrame.iloc[-1]['equity'] >= 0:
        tag = '+'
    else:
        tag = ''
    sciNotEquity = positionFrame.iloc[-1]['equity']
    currentEquity = tag + str(Decimal(positionFrame.iloc[-1]['equity']) * Decimal(10**-8))
    if float(currentEquity[0:11]) < .00000001 and float(currentEquity[0:11]) > -.00000001:
        currentEquity = '0'
    else:
        currentEquity = currentEquity[0:11]
    
    side = ''
    if positionFrame.iloc[-1]['side'] == "Buy":
        side = '+'
    elif positionFrame.iloc[-1]['side'] == "Sell":
        side = '-'
    data=[dict(x=positionFrame['time'], y=positionFrame['equity'],mode='lines')]
    layout=dict(
        title=dict(text='Overall Equity Earned= '+ currentEquity ,xanchor='left',x=.125,y=-.2),
        uirevision=3, barmode='group', margin=dict(
            l=60, r=100, b=70, t=70
        ), plot_bgcolor='rgb(19, 23, 34)', paper_bgcolor='rgb(6, 6, 6)', xaxis=dict(
            tickformat='e', showgrid=False, visible=False
        ), font=dict(family="Helvetica", size=12, color='rgb(190, 190, 190)'
        )
    )
    return {'data' : data, 'layout': layout}

@app.callback([Output('agent_bar', 'figure'),
               Output('status_table', 'figure')],
              [Input('interval-component2', 'n_intervals'),
               Input('dropdown', 'value')])
def updateAgents(n, value):
    agents = agentFrame(dumpsFolder, value)
    stats = tradeStatus(value)
    data = [go.Bar(y=agents['rpnl_short'] * 10**8, x=agents['entry_id'], name='RPNL short'),
            go.Bar(y=agents['upnl_short'] * 10**8, x=agents['entry_id'], name='UPNL short'),
            go.Bar(y=agents['rpnl_long'] * 10**8, x=agents['entry_id'], name='RPNL long'),
            go.Bar(y=agents['upnl_long'] * 10**8, x=agents['entry_id'], name='UPNL long')]
    layout = dict(
        uirevision=3, barmode='group', margin=dict(
            l=60, r=30, b=70, t=10
        ), plot_bgcolor='rgb(19, 23, 34)', paper_bgcolor='rgb(6, 6, 6)', xaxis=dict(
            tickformat='e'
        ), font=dict(
            family="Helvetica", size=12, color='rgb(190, 190, 190)'
        ),legend=dict(
    yanchor="top",
    y=0.99,
    xanchor="left",
    x=-.2
)
    )
    data3 = [go.Table(columnwidth = [2,2,2,2,2,1,1,1,1,1,1],
            header=dict(
                values=['Agent', 'Long status', 'Short status', 'Time Opening Long', 'Time Opening Short',
                        'UPNL-L', 'RPNL-L', 'UPNL-S', 'RPNL-S', '# Longs', '# Shorts'],
                line_color='rgb(120, 120, 120)', fill_color='black',
                align=['left', 'center'], font=dict(
                    color='white', size=11
                )
            ), cells=dict(
                values=[stats['entry_id'], stats['buy_status'], stats['sell_status'],
                        stats['opening_buy_timestamp'], stats['opening_sell_timestamp'], stats['upnl_long'], stats['rpnl_long'],
                        stats['upnl_short'], stats['rpnl_short'], stats['buys_counter'], stats['sells_counter']], line_color='darkslategray',
                fill_color=['rgb(19, 23, 34)'], align=['left', 'center'],
                font=dict(
                    color=['rgb(190, 190, 190)', stats['buy_status_c'], stats['sell_status_c'], 'rgb(190, 190, 190)',
                           'rgb(190, 190, 190)', stats['upnl_long_c'], stats['rpnl_long_c'],
                        stats['upnl_short_c'], stats['rpnl_short_c'], 'rgb(190, 190, 190)', 'rgb(190, 190, 190)'], size=11
                )
            )
        )]
    layout3 = dict(
        uirevision=2, margin=dict(l=20, r=20, b=0, t=0), paper_bgcolor='rgb(6, 6, 6)', height = (len(stats['entry_id']) + 2) * 21)
    
    return {'data': data, 'layout': layout}, {'data': data3, 'layout': layout3}


@app.callback(Output('info', 'children'),
              [Input('interval-component2', 'n_intervals'),
               Input('dropdown', 'value')])
def updateInfo(n, value):
    global info
    threads = glob.glob(os.path.abspath(os.path.join(os.getcwd(), os.pardir))+'\\active-tables\\*.csv')
    info = infoFrame(value)
    botName = threads[value-1][:-4].split('\\')[-1]
    infoString = f"Bot: {botName} ------- Realized PNL: {info['realized pnl']:.8f}" \
                 f"------- Unrealized PNL: {info['unrealized pnl']:.8f} ------- Net PNL:{ info['net pnl']:.8f} " \
                 f"------- Avg Entry: {info['avgEntry']:.2f} ------- Position: {info['pos']}"

    return infoString

@app.callback(Output('dropdown', 'options'),
              [Input('interval-component2', 'n_intervals')])
def updateCsv(n):
    bots = getFolders(dumpsFolder, numbers=True)[1:]
    options = []
    
            
    for i in bots:
        while True:
            try:
                with open('../dumps/' + str(i) + '/name.pickle', 'rb') as handle:
                    name = pickle.load(handle)
                with open(f'../dumps/' + str(i) + '/state.pickle', 'rb') as handle2:
                    state = pickle.load(handle2)
                tag = ''
                if state['state'] == 'stop':
                    tag += ' (waiting)'
                if state['state'] == 'run':
                    tag += ' (running)'
                options.append({'label': name.split('\\')[-1]+tag, 'value': int(i)})
                break
            except:
                #print('csvp')
                time.sleep(0.1)
    return options


# debug False when deploying!
if __name__ == "__main__":
    app.run_server(debug=True)



