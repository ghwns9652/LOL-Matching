import random
import threading
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import skewnorm

games = []
queue = []
novice = []
mqueue = [[]]*31
search_window = 200
insert_cnt = 0
mmr_diff = 100
matching_time = 30

class Party:
    def __init__(_self, dist):
        _self.player_stat = []
        _self.avg_mmr = 0
        _self.avg_exp = 0
        _self.position = [0, 0, 0, 0, 0] #[Top, Mid, Bottom, Jungle, Support]

        if(dist == "uniform"):
            _self.party_size = random.randrange(1, 6) #FIXME
        elif(dist == "skew"):
            _self.party_size = random.randrange(1, 6)
        
        for i in random.sample(range(0, 5), _self.party_size):
            _self.position[i] = 1

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
            _self.mmr = random.randrange(1, 3000) #assume highest MMR is 3000
            _self.exp = random.randrange(1, 30000) #highest playtime is 27000 games (http://ifi.gg/leaderboards)
        elif(dist == "skew"):
            _self.mmr = skewnorm.rvs(5, 1000, 500, 1)#FIXME: don't know this is correct distribution
            _self.exp = skewnorm.rvs(100, 10, 8000, 1)#FIXME: don't know this is correct distribution

def make_mq_idx(position):
    mq_idx = position[0]*1 + position[1]*2 + position[2]*4 + position[3]*8 + position[4]*16
    return mq_idx - 1

def generation(period, dist, qtype):
    global queue
    global mqueue
    global insert_cnt
    
    if(qtype == "sq"):
        for i in range(1, period):
            queue.append(Party(dist))
    elif(qtype == "mq"):
        for i in range(1, period):
            p = Party(dist)
            mq_idx = make_mq_idx(p.position)
            mqueue[mq_idx].append(p)
            insert_cnt += 1

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

def find_min_diff(mmr_diff, target_q):
    if(len(target_q) < 2):
        return [0, 0]

    min_total_mmr_diff = 4*mmr_diff + target_q[1].avg_mmr - target_q[0].avg_mmr
    ret = [0, 1]
    for i in range(1, len(target_q)-1):
        total_mmr_diff = 4*mmr_diff + target_q[i+1].avg_mmr - target_q[i].avg_mmr
        if(min_total_mmr_diff > total_mmr_diff):
            min_total_mmr_diff = total_mmr_diff
            ret = [i, i+1]
    
    return ret

def mq_match_5(cur_queue, games):
    team_a, team_b = [], []
    pair_len = len(cur_queue)//2
    for i in range(0, pair_len):
        team_a.append(cur_queue[2*i])
        team_b.append(cur_queue[2*i+1])
        games.append([team_a, team_b, time.time()])
        team_a, team_b = [], []
    del cur_queue[0:2*pair_len]
    
def mq_match_234(queue0, queue1, games):
    team_a, team_b = [], []
    min_len = len(queue0) if len(queue0) < len(queue1) else len(queue1)
    pair_len = min_len//2

    for i in range(0, pair_len):
        q1_idx = find_min_diff(queue0[2*i].avg_mmr - queue0[2*i+1].avg_mmr, queue1)
        team_a = [queue0[2*i], queue1[q1_idx[1]]]
        del queue1[q1_idx[1]]
        team_b = [queue0[2*i+1], queue1[q1_idx[0]]]
        del queue1[q1_idx[0]]
        games.append([team_a, team_b, time.time()])
    del queue0[0:2*pair_len]

def mq_match_1(p0, p1, p2, p3, p4, games):
    team_a, team_b = [], []
    min_len = min([len(p0), len(p1), len(p2), len(p3), len(p4)])
    pair_len = min_len//2

    for i in range(0, pair_len):
        team_a = [p0[2*i], p1[2*i+1], p2[2*i], p3[2*i+1], p4[2*i]]
        team_b = [p0[2*i+1], p1[2*i], p2[2*i+1], p3[2*i], p4[2*i+1]]
        games.append([team_a, team_b, time.time()])
    
    del p0[0:2*pair_len], p1[0:2*pair_len], p2[0:2*pair_len], p3[0:2*pair_len], p4[0:2*pair_len]

def pos_inverse(position):
    ret = [0,0,0,0,0]
    for i in range(0, 5):
        ret[i] = 1 - position[i]
    return ret

def mq_sorting(mq_window):
    global games

    # match 5-person party
    mq_match_5(mq_window[make_mq_idx([1]*5)], games)

    # match 4-person party with a person
    pos0 = [[0,1,1,1,1], [1,0,1,1,1], [1,1,0,1,1], [1,1,1,0,1], [1,1,1,1,0]]
    pos1 = []
    for i in pos0:
        pos1.append(pos_inverse(i))
    for i in range(0, len(pos0)):
        mq_match_234(mq_window[make_mq_idx(pos0[i])], mq_window[make_mq_idx(pos1[i])], games)

    # match 3-person party with 2-person party
    pos0 = [[0,0,1,1,1], [0,1,0,1,1], [0,1,1,0,1], [0,1,1,1,0], [1,0,0,1,1], [1,0,1,0,1], [1,0,1,1,0], [1,1,0,0,1], [1,1,0,1,0], [1,1,1,0,0]]
    pos1 = []
    for i in pos0:
        pos1.append(pos_inverse(i))
    for i in range(0, len(pos0)):
        mq_match_234(mq_window[make_mq_idx(pos0[i])], mq_window[make_mq_idx(pos1[i])], games)

    # match 1-person party
    p0 = mq_window[make_mq_idx([1,0,0,0,0])]
    p1 = mq_window[make_mq_idx([0,1,0,0,0])]
    p2 = mq_window[make_mq_idx([0,0,1,0,0])]
    p3 = mq_window[make_mq_idx([0,0,0,1,0])]
    p4 = mq_window[make_mq_idx([0,0,0,0,1])]
    mq_match_1(p0, p1, p2, p3, p4, games)

def normal_sorting(candidate, games):
    mmr_sorted = candidate[0:]
    mmr_sorted.sort(key=lambda x: x.avg_mmr)

    #num_game = len(mmr_sorted)//10
    size_a, size_b = 0, 0
    team_a, team_b = [], []
    for i in mmr_sorted:
        # FIXME: deviation of mmr can be not good, starvation for high mmr gamer
        if(i.party_size <= 5-size_a):
            team_a.append(i)
            size_a += i.party_size
        elif(i.party_size <= 5-size_b):
            team_b.append(i)
            size_b += i.party_size

        if(size_a == 5 and size_b == 5):
            games.append([team_a[0:], team_b[0:]]) 
            for j in team_a:
                candidate.remove(j)
            for j in team_b:
                candidate.remove(j)
            size_a, size_b = 0, 0
            team_a, team_b = [], []

def clustering(candidiate, games):
    '''

    implement here
    

    '''

def ns_matchmaking(queue):
    if(len(queue) >= search_window):
        candidate = queue[0:search_window]
        del queue[0:search_window]
        #remove_novice(candidate, novice)
        normal_sorting(candidate, games)
        queue = candidate + queue

def mq_matchmaking(mqueue, insert_cnt):
    mqueue_window = []
    if(insert_cnt >= search_window):
        for i in range(0, 31):
            temp = mqueue[i][0:]
            del mqueue[i][0:]
            temp.sort(key=lambda x: x.avg_mmr)
            mqueue_window.append(temp)
        mq_sorting(mqueue_window)
        for i in range(0, 31):
            mqueue[i] = mqueue_window[i] + mqueue[i]

def matchmaking(execution_time):
    global queue
    global games
    global novice
    global mqueue
    global insert_cnt
    start_ts = time.time()
    func="mq_sorting"

    if(func == "normal_sorting"):
        while(time.time() - start_ts < execution_time):
            ns_matchmaking(queue)
    elif(func == "mq_sorting"):
        while(time.time() - start_ts < execution_time):
            mq_matchmaking(mqueue, insert_cnt)

def main():
    t0 = threading.Thread(target=generation, args=(10000, "uniform", "mq"))
    t1 = threading.Thread(target=matchmaking, args=[matching_time])
    t0.start()
    t1.start()

def analyze():
    global games
    duration = []
    diff = []
    mmr_a = 0
    mmr_b = 0
    for i in range(0, len(games)):
        cur_game = games[i]
        for j in range(0, len(cur_game[0])):
            mmr_a += cur_game[0][j].party_size*cur_game[0][j].avg_mmr
            duration.append(cur_game[2] - cur_game[0][j].gentime)
        for j in range(0, len(cur_game[1])):
            mmr_b += cur_game[1][j].party_size*cur_game[1][j].avg_mmr
            duration.append(cur_game[2] - cur_game[1][j].gentime)
        diff.append(abs(mmr_a - mmr_b)/5)
        mmr_a, mmr_b = 0, 0
    
    counts, bins = np.histogram(np.array(diff), np.arange(10, 3020, 10))
    hist = plt.hist(bins[:-1], bins, weights=counts) #range=(x0.min(), x0.max()), linewidth=1.2)
    plt.show()

    counts, bins = np.histogram(np.array(duration), np.arange(0, 0.5, 0.01))
    hist = plt.hist(bins[:-1], bins, weights=counts) #range=(x0.min(), x0.max()), linewidth=1.2)
    plt.show()

main()
time.sleep(matching_time)

print("matched games")
print(len(games))

analyze()