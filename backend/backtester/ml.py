import os
import time
totalGens=20
gen = 1

if os.path.exists('GAGA'):
	os.system('rmdir -r GAGA')
	
while gen<totalGens:
	if gen==1:
		os.system("mkdir GAGA")
		os.system("mkdir GAGA\gen"+str(gen))
		os.system("copy agents.csv GAGA\gen"+str(gen))
		os.system("copy backtester.py GAGA\gen"+str(gen))
		os.system("copy live_functions.py GAGA\gen"+str(gen))
		os.system("mkdir GAGA\gen"+str(gen)+"\\time")
		os.system("copy time GAGA\gen"+str(gen)+"\\time")
		os.system("copy mutator.py GAGA\gen"+str(gen))
		os.system("copy findBest.py GAGA\gen"+str(gen))
		os.system("copy graphResults.py GAGA\gen"+str(gen))
		os.chdir("GAGA\gen1")
		os.system("python backtester.py")
		time.sleep(2)
		os.system("python findBest.py")
		time.sleep(2)
		os.system("python mutator.py " + str(gen))
		time.sleep(2)
		os.chdir('..\..')
	else:
		os.system("mkdir GAGA\gen"+str(gen))
		print("copy GAGA\gen"+str(gen-1)+"\mutants.csv GAGA\gen"+str(gen)+"\\agents.csv")
		os.system("copy GAGA\gen"+str(gen-1)+"\mutants.csv GAGA\gen"+str(gen)+"\\agents.csv")
		os.system("copy backtester.py GAGA\gen"+str(gen))
		os.system("copy live_functions.py GAGA\gen"+str(gen))
		os.system("mkdir GAGA\gen"+str(gen)+"\\time")
		os.system("copy time GAGA\gen"+str(gen)+"\\time")
		os.system("copy mutator.py GAGA\gen"+str(gen))
		os.system("copy findBest.py GAGA\gen"+str(gen))
		os.system("copy graphResults.py GAGA\gen"+str(gen))
		os.chdir("GAGA\gen"+str(gen))
		os.system("python backtester.py")
		time.sleep(2)
		os.system("python findBest.py")
		time.sleep(2)
		os.system("python mutator.py " + str(gen))
		time.sleep(2)
		os.chdir('..\..')
	gen+=1