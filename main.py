import random
import threading
import time

games = []
queue = []
novice = []
search_window = 50

class Party:
    def __init__(_self, dist):
        _self.player_stat = []
        _self.avg_mmr = 0
        _self.avg_exp = 0
        if(dist == "uniform"):
            _self.party_size = 1 #FIXME!
        elif(dist == "skew"):
            _self.party_size = random.randrange(1, 6) #FIXME!
        for i in range(0, _self.party_size):
            _self.player_stat.append(Player(dist))
            _self.avg_mmr += _self.player_stat[i].mmr
            _self.avg_exp += _self.player_stat[i].exp
        _self.avg_mmr /= _self.party_size
        _self.avg_exp /= _self.party_size
        _self.gentime = time.time()


class Player:
    def __init__(_self, dist):
        if(dist == "uniform"):
            _self.mmr = random.randrange(1, 1000) #FIXME!
            _self.exp = random.randrange(1, 100000) #FIXME!
        elif(dist == "skew"):
            _self.mmr = random.randrange(1, 1000) #FIXME!
            _self.exp = random.randrange(1, 100000) #FIXME!

def generation(period, dist):
    global queue
    for i in range(1, period):
        queue.append(Party(dist))

# move unexperience noobies to novice list
# return length of the list
def remove_novice(candidate, novice):
    cnt = 0
    i = 0

    while(cnt != search_window):
        if(candidate[i].avg_exp < 15):
            novice.append(candidate[i])
            del candidate[i]
        else:
            i+=1
        cnt+=1

    return i 

def make_matches(candidate, games):
    mmr_sorted = candidate[0:len(candidate)]
    mmr_sorted.sort(key=lambda x: x.avg_mmr)

    num_game = len(mmr_sorted)//10
    for i in range(0, num_game):
        # FIXME: deviation of mmr can be not good, starvation for high mmr gamer
        games.append(mmr_sorted[10*i:10*(i+1)]) 
    
    for i in range(0, 10*num_game):
        candidate.remove(mmr_sorted[i])

def matchmaking(execution_time):
    global queue
    global games
    global novice
    start_ts = time.time()

    while(time.time() - start_ts < execution_time):
        if(len(novice) >= 10):
            make_matches(novice, games)
        if(len(queue) >= search_window):
            candidate = queue[0:search_window]
            del queue[0:search_window]
            remove_novice(candidate, novice)
            make_matches(candidate, games)
            queue = candidate + queue
    

def main():
    t0 = threading.Thread(target=generation, args=(10000, "uniform"))
    t1 = threading.Thread(target=matchmaking, args=[20])
    t0.start()
    t1.start()


main()
time.sleep(20)

print(len(games))
print(games[0][0].avg_mmr)
print(games[0][0].avg_exp)
print(games[0][0].gentime)