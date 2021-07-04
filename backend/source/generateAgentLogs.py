import re
import os
inputFile = open('logs/live.log','r')

agents = {}

for lines in inputFile:
	splitLines=lines.rstrip().split('|')
	print(splitLines)
	
	if len(splitLines) > 5:
		if re.search('.*INFO.*',splitLines[3]):
			if splitLines[5] not in agents:
				agents[splitLines[5]] = [lines]
			else:
				agents[splitLines[5]].append(lines)
				
	if re.search('.*ERROR.*',splitLines[3]):
		for each in agents:
			agents[each].append(lines)
			
if not os.path.exists('logs/agentLogs'):
	os.makedirs('logs/agentLogs')
else:
	shutil.rmtree('logs/agentLogs')
	os.makedirs('logs/agentLogs')
	
for each in agents:
	outFile = open('logs/agentLogs/'+each+'.log','w')
	for lines in agents[each]:
		outFile.write(lines)