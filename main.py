import matplotlib.pyplot as plt
import seaborn as sns
import numpy
import random
import threading
import time
import hdbscan
from scipy.stats import skewnorm
from sklearn.cluster import DBSCAN

DEBUG_waittime = []
games = []
queue = []
novice = []
search_window = 400

class Party:
    def __init__(_self, dist):
        _self.player_stat = []
        _self.avg_mmr = 0
        _self.avg_exp = 0
        _self.position = 0b00000 #[Top, Mid, Bottom, Jungle, Support]

        if(dist == "uniform"):
            _self.party_size = random.randrange(1, 6) #FIXME
        elif(dist == "skew"):
            _self.party_size = random.randrange(1, 6)
        
        for i in random.sample([0,1,2,3,4], _self.party_size):
            _self.position |= 0b00001<<i

        for i in range(0, _self.party_size):
            _self.player_stat.append(Player(dist))
            _self.avg_mmr += _self.player_stat[i].mmr
            _self.avg_exp += _self.player_stat[i].exp
        _self.avg_mmr /= _self.party_size
        _self.avg_exp /= _self.party_size
        _self.gentime = time.time()
        #Tracking party
        _self.waitingtime = 0


class Player:
    def __init__(_self, dist):
        if(dist == "uniform"):
            _self.mmr = random.randrange(1, 3000) #assume highest MMR is 3000
            _self.exp = random.randrange(1, 30000) #highest playtime is 27000 games (http://ifi.gg/leaderboards)
        elif(dist == "skew"):
            _self.mmr = skewnorm.rvs(5, 1000, 500, 1)#FIXME: don't know this is correct distribution
            _self.exp = skewnorm.rvs(100, 10, 8000, 1)#FIXME: don't know this is correct distribution


def generation(period, dist):
    global queue
    for i in range(1, period):
        queue.append(Party(dist))

#get party list and make games_match considering position & the number of players
def games_match(candidate):
    #divide candidate by the number of players
    user_multiqueue = [[] for _ in range(5)] #user_muliqueue[0] : user_solo
    for user_group in candidate:
        idx = user_group.position.count(1) - 1
        user_multiqueue[idx].append(user_group)
    #sort multiqueue by mmr
    for _ in user_multiqueue:
        queue.sort(key=lambda x: x.avg_mmr)

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

def normal_sorting(candidate, games):
    mmr_sorted = candidate[0:len(candidate)]
    mmr_sorted.sort(key=lambda x: x.avg_mmr,reverse=True)

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

def set_waitingtime(team1,team2):
    global DEBUG_waittime
    for party in team1:
        party.waitingtime = time.time() - party.gentime
        DEBUG_waittime.append(party.waitingtime)
    for party in team2:
        party.waitingtime = time.time() - party.gentime
        DEBUG_waittime.append(party.waitingtime)

def clustering(candidate, games):
    def makenewparty(party_list):
        OR_2b = party_list[0].position
        SUM_2b = party_list[0].position
        for party in party_list[1:]:
            OR_2b |= party.position
        for party in party_list[1:]:
            SUM_2b += party.position
        return OR_2b == SUM_2b


    #reconfigure party queue for clustering by gentime,avg_mmr
    candidate_feature_arr = []
    for party in candidate:
        candidate_feature_arr.append([party.gentime,party.avg_mmr])
    
    #clustering start, min_cluster_size is 10 parties
    candidate_labeled = hdbscan.HDBSCAN(min_cluster_size=10).fit_predict(candidate_feature_arr)
    
    #classify clustered_queue into same array with same label (0, ...... , max(queue_labeled))
    clustered_candidate = [[] for _ in range(max(candidate_labeled)+1)]
    noise_candidate = [] #TO DO
    for party,label in zip(candidate,candidate_labeled):
        if(label==-1): #noise party
            noise_candidate.append(party)
        else: 
            #add party with same label into game groups
            clustered_candidate[label].append(party)
    
    #game_matching start
    deleted_party = [] #otherwise defined, remove error
    for same_labeled_group in clustered_candidate: 
        #maintain two datastructure : same_labeled_group multiqueue_poisition (by position)
        same_labeled_group.sort(key=lambda x: x.gentime,reverse=True)
        multiqueue_position = [[] for _ in range(0b11111+1)] #multiqueue_poistion[0b00001] ~ multiqueue_poistion[0b11111]

        # divide same labeled parties by the number of position
        for user_group in same_labeled_group:
            idx_position = user_group.position
            multiqueue_position[idx_position].append(user_group)

        # match making
        full_team = []
        # 1 or 2 or 3
        try_team_1 = []
        try_team_2 = []
        try_team_num = 0


        for party in same_labeled_group:
            if party not in multiqueue_position[party.position]:
                continue

            # O(same_labeled_group)
            num = party.party_size
            idx = 0b11111^party.position
            # [5]
            if party.position == 0b11111:
                deleted_party.append(party)
                full_team.append([party])
                if len(full_team) >= 2:
                    games.append([full_team[0],full_team[1]])
                    set_waitingtime(full_team[0],full_team[1])
                    del full_team[0:2]
                multiqueue_position[party.position].remove(party) #delete
            
            # [1,4] [2,3] pair exists
            elif len(multiqueue_position[idx])>0:
                full_team.append([party,multiqueue_position[idx][0]])
                if len(full_team) >= 2:
                    games.append([full_team[0],full_team[1]])
                    set_waitingtime(full_team[0],full_team[1])
                    del full_team[0:2]
                deleted_party.append(party) #delete in candidate at outer loop
                deleted_party.append(multiqueue_position[idx][0]) #delete in candidate at outer loop
                del multiqueue_position[idx][0] #delete
                multiqueue_position[party.position].remove(party) #delete

            else: # pair doesnt exists
                if num==4:
                    multiqueue_position[party.position].remove(party) #delete
                elif num == 2:
                    try_team_2.append(party)
                    multiqueue_position[party.position].remove(party) #delete
                    try_team_num += 1
                elif num == 1:
                    try_team_1.append(party)
                    multiqueue_position[party.position].remove(party) #delete
                    try_team_num += 1
                

            #### (1,2)
            if len(try_team_1) >= 1 and len(try_team_2) >= 1:
                try_team_1.sort(key=lambda x: x.gentime,reverse=True)
                try_team_2.sort(key=lambda x: x.gentime,reverse=True)
                for solo in try_team_1:
                    OR_2b = solo.position
                    SUM_2b = solo.position

                    for duo in try_team_2:
                        OR_2b |= duo.position
                    for duo in try_team_2:
                        SUM_2b |= duo.position

                    if OR_2b == SUM_2b:
                        #check
                        idx = 0b11111^(OR_2b)
                        if len(multiqueue_position[idx])>0:
                            makepair = True
                            full_team.append([solo,duo,multiqueue_position[idx][0]])
                            if len(full_team) >= 2:
                                games.append([full_team[0],full_team[1]])
                                set_waitingtime(full_team[0],full_team[1])
                                del full_team[0:2]
                            try_team_num -= 2
                            deleted_party.append(solo)
                            deleted_party.append(duo)
                            deleted_party.append(multiqueue_position[idx][0])
                            try_team_1.remove(solo)
                            try_team_2.remove(duo)
                            del multiqueue_position[idx][0] #delete
            
            #(1,1,1,1)
            elif len(try_team_1) >= 4 :
                for solo_1 in try_team_1:
                    for solo_2 in try_team_1:
                        for solo_3 in try_team_1:
                            for solo_4 in try_team_1:
                                if makenewparty([solo_1,solo_2,solo_3,solo_4]) == True:
                                    idx = 0b11111^(solo_1.position | solo_2.position | solo_3.position | solo_4.position)
                                    if len(multiqueue_position[idx])>0:    
                                        full_team.append([solo_1,solo_2,solo_3,solo_4,multiqueue_position[idx][0]])
                                        if len(full_team) >= 2:
                                            games.append([full_team[0],full_team[1]])
                                            set_waitingtime(full_team[0],full_team[1])
                                            del full_team[0:2]                                        
                                        try_team_num -= 4
                                        try_team_1.remove(solo_1)
                                        try_team_1.remove(solo_2)
                                        try_team_1.remove(solo_3)
                                        try_team_1.remove(solo_4)
                                        deleted_party.append(solo_1)
                                        deleted_party.append(solo_2)
                                        deleted_party.append(solo_3)
                                        deleted_party.append(solo_4)
                                        deleted_party.append(multiqueue_position[idx][0])
                                        del multiqueue_position[idx][0] #delete
            #(1,1,1)
            elif len(try_team_1) >= 3 :
                for solo_1 in try_team_1:
                    for solo_2 in try_team_1:
                        for solo_3 in try_team_1:
                            if makenewparty([solo_1,solo_2,solo_3]) == True:
                                idx = 0b11111^(solo_1.position | solo_2.position | solo_3.position)
                                if len(multiqueue_position[idx])>0:    
                                    full_team.append([solo_1,solo_2,solo_3,multiqueue_position[idx][0]])
                                    if len(full_team) >= 2:
                                        games.append([full_team[0],full_team[1]])
                                        set_waitingtime(full_team[0],full_team[1])
                                        del full_team[0:2]
                                    try_team_num -= 3
                                    try_team_1.remove(solo_1)
                                    try_team_1.remove(solo_2)
                                    try_team_1.remove(solo_3)
                                    deleted_party.append(solo_1)
                                    deleted_party.append(solo_2)
                                    deleted_party.append(solo_3)
                                    deleted_party.append(multiqueue_position[idx][0])
                                    del multiqueue_position[idx][0] #delete
            #(1,1)
            elif len(try_team_1) >=2:
                for solo_1 in try_team_1:
                    for solo_2 in try_team_1:
                        if makenewparty([solo_1,solo_2]) == True:
                            idx = 0b11111^(solo_1.position | solo_2.position)
                            if len(multiqueue_position[idx])>0:    
                                full_team.append([solo_1,solo_2,multiqueue_position[idx][0]])
                                if len(full_team) >= 2:
                                    games.append([full_team[0],full_team[1]])
                                    set_waitingtime(full_team[0],full_team[1])
                                    del full_team[0:2]

                                try_team_num -= 2
                                try_team_1.remove(solo_1)
                                try_team_1.remove(solo_2)
                                deleted_party.append(solo_1)
                                deleted_party.append(solo_2)
                                deleted_party.append(multiqueue_position[idx][0])
                                del multiqueue_position[idx][0] #delete
  
                ###
            
    for party in deleted_party:
            candidate.remove(party)
            
    #############################################################################
    

def make_matches(func, candidate, games):
    if(func=="normal_sorting"):
        normal_sorting(candidate, games)
    elif(func=="clustering"):
        clustering(candidate, games)

    '''
    add some functions
    '''

def matchmaking(execution_time):
    global queue
    global games
    global novice
    start_ts = time.time()
    func = "clustering"

    while(time.time() - start_ts < execution_time):
        print(time.time() - start_ts)

        #if(len(novice) >= 10):
        #    make_matches(novice, games)
        if(len(queue) >= search_window):
            candidate = queue[0:search_window]
            del queue[0:search_window]
            #remove_novice(candidate, novice)
            make_matches(func, candidate, games)
            queue = candidate + queue
    

def main():
    t0 = threading.Thread(target=generation, args=(10000, "uniform"))
    t1 = threading.Thread(target=matchmaking, args=[3])
    t0.start()
    t1.start()


if __name__ == "__main__":
    t0 = threading.Thread(target=generation, args=(10000, "uniform"))
    t1 = threading.Thread(target=matchmaking, args=[3])
    t0.start()
    t1.start()
    t0.join()
    t1.join()

    
    

    
    print("\n\ntotal games: ",len(games))
    print("match succuess: ",len(games)*2/len(queue)*100,"%")
    print("waiting time avg: ", sum(DEBUG_waittime)/len(DEBUG_waittime))
    sns.distplot(DEBUG_waittime,kde=False,rug=True)
    plt.show(sns)
    x = numpy.linspace(0,20,100)
    plt.plot(x,numpy.sin(x))
    plt.show()

    

    