set id=%RANDOM%

REM Install dependencies
start /wait "genesis-bot-install-%id%" cmd /c pip install -r source/requirements.txt
if errorlevel 1 ( 
    echo Issues installing dependencies. Shutting down bot start up...
    pause
    exit
)

REM Run bot scripts
cd source
start "genesis-bot-oracle-%id%" python oracle.py "%id%"
ping 192.0.2.2 -n 1 -w 3000 > nul
start "genesis-bot-livechart-%id%" python livechartMain.py "%id%"
ping 192.0.2.2 -n 1 -w 5000 > nul
start "" http://127.0.0.1:8050