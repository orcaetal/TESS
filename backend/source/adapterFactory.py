from bybit import Bybit


def loadAdapter(config, user):
    if config['exchange'] == 'bybit':
        return Bybit(config, user)
