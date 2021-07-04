# libraries
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import glob

sets = glob.glob('results/complete*')

for i in range(1,len(sets)+1):
	# Data
	x_values = []
	y_values = []
	plt.style.use('dark_background')
	fig, ax = plt.subplots()
	
	with open('results/timePriceSeries'+str(i)+'.csv','r') as timeSeries:
		for lines in timeSeries:
			lines = lines.rstrip().split(',')
			x_values.append(float(lines[0]))
			y_values.append(float(lines[1]))
		#print(x_values)
		#print(y_values)
	ax.plot(x_values,y_values,linewidth=.5)
	
	
	with open('results/completedTrades'+str(i)+'.csv','r') as completedTrades:
		traded = 0
		for lines in completedTrades:
			traded+=1
			prices = []
			times = []
			lines = lines.rstrip().split(',')
			prices = [float(lines[2]),float(lines[4])]
			times = [float(lines[3]),float(lines[5])]
			if lines[1] == 'Long':
				myColor = 'lime'
			else:
				myColor = 'red'
				
			if float(lines[6]) < 0:
				myColor = 'orange'
				
			ax.plot(times,prices,marker='+',linewidth=1,markersize=2,color = myColor,gid = lines[0] + ' --- ' + lines[1]+' --- Open = '+lines[2]+' --- Close = '+lines[4]+' --- Fitness = '+lines[6])
			#print('plotted trade',traded)
	
	def on_plot_hover(event):
		for curve in ax.get_lines():
			if curve.contains(event)[0]:
				if curve.get_gid() is not None:
					print(curve.get_gid())
	
	fig.canvas.mpl_connect('motion_notify_event', on_plot_hover)      
	# show legend
	#plt.legend()
	
	# show graph
	plt.show()