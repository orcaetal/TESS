import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import json
import re
from operator import itemgetter
import os
import time
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
logFolder = os.path.abspath('../logs')
dumpsFolder = os.path.abspath('../dumps')

varFilePath = dumpsFolder+'\1\\varDump.json'
agentFilePath = dumpsFolder+'\1\\agentDump.json'
orderFilePath = dumpsFolder+'\1\\orderDump.json'
historyFilePath = dumpsFolder+'\1\\historyDump.json'

def order_plot(ax):
	while True:
		try:
			varFile = open(varFilePath,'r')
			for lines in varFile:
				jsonTemp = json.loads(lines)
			currentPrice=jsonTemp[0][0]['price']
			
			orderFile = open(orderFilePath,'r')
			for lines2 in orderFile:
				orders = json.loads(lines2)
				
			columns = ('Agent ID','Trade Type','Side','Trigger Price','Size(USD)')
			data_list=[]
			green = '#d4f7d5'
			red = '#f7d6d4'
			
			for order in orders:
				
				capt = re.search('(.+)time=.+', order['order_link_id'])
		
				if capt:
					linkID=capt.group(1)
				else:
					linkID = 'X-5X'
		
				splitter = linkID.split('-')
				agentID = splitter[0]
				tradeType = splitter[1][0]
				side = splitter[1][1]
				
				dataListRow=[]
				dataListRow.append(agentID)
				
				if tradeType == '1':
					dataListRow.append('opening')
				else:
					dataListRow.append('closing')
					
				dataListRow.append(order['side'])
				dataListRow.append(float(order['price']))
				dataListRow.append(order['qty'])
				data_list.append(dataListRow)
				
			data_list.append(('X','current','price',float(currentPrice),'----'))
		
			iterer = sorted(data_list, key=itemgetter(3))
			iterer.reverse()
			
			data_list_sorted=[]
			color_list=[]
			for each in iterer:
				data_list_sorted.append(each)
				if each[2] == 'Buy':
					color_list.append((green,green,green,green,green))
				elif each[2] == 'Sell':
					color_list.append((red,red,red,red,red))
				else:
					color_list.append(('w','w','w','w','w'))
			#Table - orders
			ax.table(cellText=data_list_sorted,
					cellColours=color_list,
					colLabels=columns, loc="upper center")
			ax.set_title("Open Orders",color="chartreuse")
			ax.axis("off")
			
			break
		except:
			time.sleep(1)
	
def bar_plot(ax):
	while True:
		try:
			inFile = open(agentFilePath,'r')
			for lines2 in inFile:
				agents = json.loads(lines2)
		
			
			green = '#d4f7d5'
			red = '#f7d6d4'
			
			xlabelsList=[]
			ulList=[]
			usList=[]
			rlList=[]
			rsList=[]
			
			for each in agents:
				
				xlabelsList.append(each['entry_id'] + '\n' + str(each['buys_counter'] + each['sells_counter']))
				ulList.append(each['upnl_long'])
				usList.append(each['upnl_short'])
				rlList.append(each['rpnl_long'])
				rsList.append(each['rpnl_short'])
				
				if each['upnl_long'] == 0:
					color_long='w'
				else:
					upnl_long = '{:.8f}'.format(each['upnl_long'])
					if float(upnl_long) > 0:
						color_long = green
					else:
						color_long = red
						
				if each['upnl_short'] == 0:
					color_short = 'w'
				else:
					upnl_short = '{:.8f}'.format(each['upnl_short'])
					if float(upnl_short) > 0:
						color_short = green
					else:
						color_short = red
			
			bwidth = 0.25
			z0 = np.arange(len(xlabelsList))
			z1 = [x for x in z0]
			z2 = [x - 2*bwidth for x in z0]
			z3 = [x + bwidth for x in z0]
			z4 = [x - bwidth for x in z0]
		
			
			ax.bar(z1,ulList,color='white',width=bwidth,label='u_pnl buy side',alpha=0.25)
			ax.bar(z2,rlList,color='white',width=bwidth,label='r_pnl buy side')
			ax.bar(z3,usList,color='black',width=bwidth,label='u_pnl sell side',alpha=0.25)
			ax.bar(z4,rsList,color='black',width=bwidth,label='r_pnl sell side')
			
			ax.set_xticks(z4,)
			ax.set_xticklabels(xlabelsList,color="chartreuse")
			ax.set_title('Agent Profits',color="chartreuse")
			ax.tick_params(axis='y', colors='chartreuse')
			ax.legend(loc=1, prop={'size': 6}, framealpha=0.25)
			ax.set_facecolor("gray")
			ax.spines['bottom'].set_color('chartreuse')
			ax.spines['top'].set_color('chartreuse')
			ax.spines['left'].set_color('chartreuse')
			ax.spines['right'].set_color('chartreuse')
			break
		
		except:
			time.sleep(0.1)
	
def hist_plot(ax):
	while True:
		try:
			inFile4 = open(historyFilePath,'r')
			for lines4 in inFile4:
				filled = json.loads(lines4)
				
			columns4 = ('timestamp','agent','type','side','price','amount')
			
			if len(filled) > 0:
				
				ax.set_title("Trade History",color="chartreuse")
				ax.axis("off")
				colList=[]
				rows = []
				for sets in filled:
					colList.append(['lightgray','lightgray','lightgray','lightgray','lightgray','lightgray'])
					rows.append("filled")
				tab4 = ax.table(cellText=filled,
						cellColours=colList,
						colLabels=columns4,
						loc="upper center",
						)
				
				tab4.set_fontsize(10)
				ax.table = tab4
				
				
				break
			else:
				ax.set_title("Trade History",color="chartreuse")
				ax.axis("off")
				break
		except Exception as e:
			print(e)
			time.sleep(1)

def info_plot(ax):
	while True:
		try:
			varFile = open(varFilePath,'r')
			for lines in varFile:
				jsonTemp = json.loads(lines)
				
			currentRSIParam=jsonTemp[0][0]
			currentRSIParam['realized pnl']=jsonTemp[1]
			currentRSIParam['unrealized pnl']=jsonTemp[2]
			currentRSIParam['net pnl'] = jsonTemp[1]+jsonTemp[2]
			
			if jsonTemp[3] == 100:
				currentRSIParam['leverage']=0
			else:
				currentRSIParam['leverage']='{:.3f}'.format(jsonTemp[3])
			
			
			data_list3=[]
			colors_list3=[]
			
			columns3=('Attribute','Value')
			for keys in currentRSIParam:
				if keys == 'price' or keys == 'leverage':
					data_list3.append((keys,currentRSIParam[keys]))
				elif keys == 'realized pnl' or keys == 'unrealized pnl' or keys == 'net pnl':
					data_list3.append((keys,'{:.9f}'.format(currentRSIParam[keys])))
				elif re.match(".+\.0",keys):
					data_list3.append(('rsi('+keys+')','{:.2f}'.format(currentRSIParam[keys])))
				colors_list3.append(('lightgray','lightgray'))
			
			
			table3 = ax.table(cellText=data_list3,
					cellColours=colors_list3,
					colLabels=columns3,
					loc="center",
					)
			table3.set_fontsize(10)
			ax.table = table3
			ax.set_title("User Info",color="chartreuse")
			
			ax.axis("off")
			break
		except:
			time.sleep(0.1)
	
def update(frame):
	
	#assign ax
	ax1 = plt.subplot2grid((6, 6), (0, 0), colspan=2, rowspan=2)
	ax2 = plt.subplot2grid((6, 6), (0, 2), colspan=4, rowspan=2)
	ax3 = plt.subplot2grid((6, 6), (2, 0), colspan=3, rowspan=4)
	ax4 = plt.subplot2grid((6, 6), (2, 3), colspan=3, rowspan=4)
	
	info_plot(ax1)
	bar_plot(ax2)
	order_plot(ax3)
	hist_plot(ax4)
	
	plt.tight_layout()
	return plt.plot()

##wait for init of bot
while True:
	try:
		if not os.path.isdir(dumpsFolder):
			time.sleep(1)
			print('Loading....')
		else:
			time.sleep(1)
			break
	except:
		time.sleep(1)
#init fig
fig, ax = plt.subplots(figsize=(10,6))
fig.patch.set_facecolor('black')
while True:
	try:
		ani = FuncAnimation(fig, update, frames = 10000, interval=5000, blit=True, repeat = True)
		plt.show()
	except Exception as e:
		print('exception raised in table main',e)
		time.sleep(0.5)
