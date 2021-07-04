import live_functions as localLib
import random
import sys
import re
gen = sys.argv[1]
print(gen)

offsetTable = localLib.offsetTable('bestAgents.csv',0,0)
newOffsetTable = []
for agents in offsetTable:
	mutants = 0
	newOffsetTable.append(agents)
	while mutants < 12:
		newAgents = agents.copy()
		if re.match('.+%$', str(newAgents['offset'])):
			newAgents['offset'] = str(float(random.triangular(1,float(agents['offset'][:-1])* 5,float(agents['offset'][:-1]))))+'%'
		else:
			newAgents['offset'] = str(int(random.triangular(1,float(agents['offset'])* 4,float(agents['offset']))))
		newAgents['entry_multiplier'] = str(random.triangular(1,float(agents['entry_multiplier']) * 4,float(agents['entry_multiplier'])))
		newAgents['exit_multiplier'] = str(random.triangular(1,float(agents['exit_multiplier']) * 4,float(agents['exit_multiplier'])))
		newAgents['entry_timeout'] = str(int(random.triangular(0,float(agents['entry_timeout']) * 4,float(agents['entry_timeout']))))
		newAgents['exit_timeout'] = str(int(random.triangular(0,float(agents['exit_timeout']) * 4,float(agents['exit_timeout']))))
		newAgents['rsiOS'] = str(int(random.triangular(2,50,float(agents['rsiOS']))))
		newAgents['rsiOB'] = str(int(random.triangular(50,98,float(agents['rsiOB']))))
		newAgents['rsiPeriod'] = str(int(random.triangular(4,float(agents['rsiPeriod']) * 2)))
		newAgents['entry_id'] = agents['entry_id'] + 'gen' + str(gen) + str(mutants)
		newAgents['stop_loss'] = str(int(random.triangular(0,float(agents['stop_loss'])* 4,float(agents['stop_loss']))))
		newOffsetTable.append(newAgents)
		mutants+=1
		
with open('mutants.csv','w') as mutants:
	mutants.write('offset,entry_multiplier,exit_multiplier,amount,entry_timeout,exit_timeout,prevent_entries,prevent_exits,buys_allowed,sells_allowed,rsiOS,rsiOB,rsiPeriod,trailing_entry,stop_loss,trailing_tp,delay_profit,delay_stop,active_above,active_below,entry_id\n')
	for agents in newOffsetTable:
		mutants.write(str(agents['offset'])+','+str(agents['entry_multiplier'])+','+str(agents['exit_multiplier'])+','+str(agents['amount'])+','+str(agents['entry_timeout'])+','+str(agents['exit_timeout'])+','+str(agents['prevent_entries'])+','+str(agents['prevent_exits'])+','+str(agents['buys_allowed'])+','+str(agents['sells_allowed'])+','+str(agents['rsiOS'])+','+str(agents['rsiOB'])+','+str(agents['rsiPeriod'])+','+str(agents['trailing_entry'])+','+str(agents['stop_loss'])+','+str(agents['trailing_tp'])+','+str(agents['delay_profit'])+','+str(agents['delay_stop'])+','+str(agents['active_above'])+','+str(agents['active_below'])+','+agents['entry_id']+'\n')