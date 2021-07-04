import math

time = 1.7077322222222222
drawdown = 1.9305407727566355e-7
rpnl = 1.6491746333397326e-7
amount = 3
#factor of time for fitness score
def timeFactor(time):
	return 1 / (0.125 * time + 0.1)

#factor of drawdown for fitness score
def drawdownFactor(rpnl, drawdown):
	ratio = abs(drawdown / rpnl)
	return 10.5 * math.exp(ratio * -3.12)

# Calculate fitness score
def fitnessScore(rpnl, drawdown, time, amount):
	return 10 ** 8 * ((rpnl * drawdownFactor(rpnl, drawdown) * timeFactor(time)) / amount)

print(fitnessScore(rpnl, drawdown, time, amount))