import random
import threading
import time
import hdbscan
from scipy.stats import skewnorm
from sklearn.cluster import DBSCAN

games = []
queue = []
novice = []
search_window = 100

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

def clustering(candidate, games):
  
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
    '''
    #game_matching start
    deleted_party = [] #otherwise defined, remove error
    for same_labeled_group in clustered_candidate: # -> O(n)
        iter = len(same_labeled_group)//10
        for i in range(iter):
            games.append(same_labeled_group[10*i:10*(i+1)])
            for party in same_labeled_group[10*i:10*(i+1)]:
                deleted_party.append(party)              

    for party in deleted_party:
        candidate.remove(party)
    '''

    #############################################################################
    #game_matching start
    deleted_party = [] #otherwise defined, remove error
    # O(n)
    for same_labeled_group in clustered_candidate: 
        #maintain two datastructure : same_labeled_group, multiqueue_player (by players), multiqueue_poisition (by position)
        same_labeled_group.sort(key=lambda x: x.gentime,reverse=True)
        multiqueue_players = [[] for _ in range(5+1)] #muliqueue_player[1] ~ multiqueue_player[5]
        multiqueue_position = [[] for _ in range(0b11111+1)] #multiqueue_poistion[0b00001] ~ multiqueue_poistion[0b11111]

        # divide same labeled parties 
        # by the number of players
        # by the number of position
        for user_group in same_labeled_group:
        # O(same_labeled_group)
            idx_player = len(user_group.player_stat)
            idx_position = user_group.position
            multiqueue_players[idx_player].append(user_group)
            multiqueue_position[idx_position].append(user_group)

        # match making
        full_team = []
        # 1 or 2 or 3
        try_team = [[] for _ in range(0b11111+1)] #multiqueue_poistion[0b00001] ~ multiqueue_poistion[0b11111]
        try_team_num = 0
        # 4
        not_team = []
        for party in same_labeled_group:
        # O(same_labeled_group)
            num = len(party.player_stat)
            idx = 0b11111^party.position
            # [5]
            if party.position == 0b11111:
                full_team.append(party)
            
            # [1,4] [2,3] pair exists
            elif len(multiqueue_position[idx])>0:
                full_team.append([party,multiqueue_position[idx][0]])
                deleted_party.append(party) #deleted outer loop
                deleted_party.append(multiqueue_position[idx][0]) #deleted outer loop
                del multiqueue_position[idx][0] #delete
            
            else: # pair doesnt exists
                if num==4:
                    not_team.append(party)
                else:
                    try_team[party.position].append(party)
                    try_team_num += 1

            # make new pair
            # they are 1 or 2 or 3 and they has no exact partner
            if try_team_num >= 2: # at least one pair can be made
                pick = []           # O(try_team_num)
                for same_pos_party_list in try_team: 
                    if len(same_pos_party_list) != 0:
                        for party in same_pos_party_list:
                            pick.append(party)
                for i in range(len(pick)):
                    for j in range(len(pick[i:])):
                        #make pairs
                        if pick[i].position & pick.position[i+j] == 0b00000:
                            #check
                            idx = pick[i].position | pick.position[i+j]
                            if len(multiqueue_position[idx])>0:
                                full_team.append([pick[i],pick[i+j],multiqueue_position[idx][0]])
                                deleted_party.append(pick[i])   #deleted outer loop
                                deleted_party.append(pick[i+j]) #deleted outer loop
                                del multiqueue_position[idx][0] #delete
                        else:
                            pass

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
    func="clustering"
    

    while(time.time() - start_ts < execution_time):
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


main()
time.sleep(3)

print(len(games))
print(games[0][0].avg_mmr)
print(games[0][0].avg_exp)
print(games[0][0].gentime)
