Welcome TESS Users!
Here are a few instructions to help you get started.


AUTHENTICATION

Before starting your bot, make sure to fill in your `config.json` file with your API keys and
your unique email/key provided by the Genesis team. Your unique email and key
combination will allow you to run a single instance of the bot.

The config will look similar to the following:

```
{
    "key" : "",
    "private": "",
    "exchange": "bybit",
    "network": "testnet",
    "asset": "btcusd",
    "version": "2.0.1",
    "stopTradingTrigger": 40,
    "killEmergencyTrigger": 70,
    "leverage": 0,
    "license" : {
        "email": "",
        "key": ""
    }
}
```
and should be changed to:

```
{
    "key" : "your_API_public_key",
    "private": "your_API_private_key",
    "exchange": "bybit",
    "network": "testnet",
    "asset": "btcusd",
    "version": "2.0.1",
    "stopTradingTrigger":40,
    "killEmergencyTrigger":70,
    "leverage": 0,
    "license" : {
        "email": "your_genesis_email",
        "key": "your_genesis_password"
    }
}
```

Below is a description of important config parameters, adjust to your preferences:

network ------------------- "testnet" for practice, "mainnet" for live trading
asset --------------------- "btcusd", "ethusd", "xrpusd", or "eosusd"
leverage ------------------ 0 for cross, 1-100 for isolated 
stopTradingTrigger -------- when on cross, the effective leverage at which the bot will stop placing orders
killEmergencyTrigger ------ when on cross, the effective leverage at which the bot will close the entire position


OFFSET TABLES

Check #tess-tables on Discord for pre-made offset tables, or make your own. Load up to 10 tables in the 
`active-tables` folder.

Here is a brief description of the table parameters:

offset --------------- [float] distance from current price to place order.
			       (can be USD e.g. 100 or percent of btc price e.g. 1%) 
entry_multiplier ----- [float] multiplied to offset for entry orders  
exit_multiplier ------ [float] multiplied to offset for exit orders  
amount --------------- [float] contract size of order.
			     (can be USD e.g. 100 or percent of available balance e.g. 1%)
entry_timeout -------- [float] number of minutes before replacing entry order  
exit_timeout --------- [float] number of minutes before replacing exit order  
prevent_entries ------ [bool] wait for TRS signal before entering?  
prevent_exits -------- [bool] wait for TRS signal before exiting?  
buys_allowed --------- [bool] can buy?  
sells_allowed -------- [bool] can sell?  
rsiOS ---------------- [float] trs value above which sells can occur  
rsiOB ---------------- [float] trs value below which buys can occur  
rsiPeriod ------------ [int] lookback period for rsi to calculate trs 
trailing_entry ------- [float] distance from current price to enter by trailing
			       (set as 0 to enter without trail)  
trailing_tp ---------- [float] distance from current price to exit by trailing  
			       (set as 0 to exit without trail)  
delay_profit --------- [float] number of minutes to delay trading after profitable trade  
delay_stop ----------- [float] number of minutes to delay trading after stop loss  
active_above --------- [float] price above which trade can be entered  
active_below --------- [float] price below which trade can be entered  
entry_id ------------- [str] name of agent  



DEPENDENCIES

TESS requires exactly Python `3.7.5`, no other versions will work at this time. Download here, and be sure to mark the checkbox
next to "Add Python to PATH":
https://www.python.org/downloads/release/python-375/

Also, please install Visual Studios Build Tools, found here:
Be sure to download the Desktop tools 
https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019



RUNNING THE BOT

Sync your OS time before you do anything. For windows this is moving your cursor to the bottom right corner,
right clicking on time and date --> adjust date/time --> sync now!

When your config file is updated, python is installed, and you have at least one offset table in /active-tables,
you can double click the `run_windows.bat` file. On startup
the bot will check that everything is installed. If all dependencies are met, several windows will open.

In the first window, you can monitor the price and get notifications of agent actions.
The second window will spawn a UI in your default web browser. On the UI, select the table you want to run
from the dropdown menu and click "run"

You can toggle between tables with the dropdown menu and start or stop additional tables with the "run"/"stop" buttons. 


USING THE BACKTESTER

Inside the folder 'backtester' you will find tools for running tests on historical price data.

Load your test agents into the file 'agents.csv' No other file name is currently accepted.

Download historical price data by requesting it in our Discord. Rename the file as "time1.csv" and 
save it in the "time" folder. To test multiple time series concurrently, add files to the "time" folder
with the naming convention "time1.csv", "time2.csv", "time3.csv" etc

To run a backtest, double click backtester.py and let the program run to completion. Depending on the time series
and offset table you are testing, this could take seconds, minutes, or hours. When the program has finished running, 
you can double click "graphResults.py" to visualize the results of the backtest. Green lines represent profitable longs,
red lines represent profitable shorts, and orange lines represent unprofitable trades. To view more details of the test,
examine the "results" folder. 

Happy trading!
