import random
import datetime

queue = []

class Party:
    def __init__(_self, dist):
        _self.player_stat = []
        if(dist == "uniform"):
            _self.party_size = random.randrange(1, 6)
        elif(dist == "skew"):
            _self.party_size = random.randrange(1, 6) #FIXME!
        for i in range(0, _self.party_size-1):
            _self.player_stat.append(Player(dist))
        _self.gentime = datetime.now()


class Player:
    def __init__(_self, dist):
        if(dist == "uniform"):
            _self.mmr = random.randrange(1, 1000) #FIXME!
            _self.exp = random.randrange(1, 100000) #FIXME!
        else(dist == "skew"):
            _self.mmr = random.randrange(1, 1000) #FIXME!
            _self.exp = random.randrange(1, 100000) #FIXME!

def generation(period, dist):
    for i in range(1, period):
        queue.append(Party(dist))

def matchmaking():
    while(1):
        if(party == None):
            for i in range(0, len(queue)-1):
                party = queue[i].pop

def print_status():

def main()