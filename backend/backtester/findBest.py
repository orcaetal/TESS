import glob
import re
myAgents=[]

with open("agents.csv","r") as agents:
	for lines in agents:
		if re.match('.+\\n',lines):
			lines = lines.rstrip()
		line = lines.split(',')
		if line[0] != 'offset':
			myAgents.append(lines)
		else:
			header = lines


print(myAgents)
resultsFiles = glob.glob('results/result*')
profits={}
for fileNames in resultsFiles:
	with open(fileNames,"r") as results:
		for lines in results:
			line=lines.rstrip().split(',')
			if line[0] not in ['agent_id','total profit','max cumulative drawdown']:
				if line[0] in profits:
					profits[line[0]]+=float(line[1])
				else:
					profits[line[0]]=float(line[1])
						
						
transList = []
for alls in profits:
	transList.append([alls, profits[alls]])
transList.sort(key=lambda x: x[1], reverse=True)

top = transList[:7]
nextGen = open('bestAgents.csv','w')
nextGen.write(header+'\n')
for each in top:
	for agents in myAgents:
		tempAgent = agents.rstrip().split(',')
		print(tempAgent[-1])
		if each[0] == tempAgent[-1]:
			nextGen.write(agents+'\n')
		