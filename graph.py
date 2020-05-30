import seaborn as sns
import matplotlib.pyplot as plt

f = open("sorting_mmr_diff.txt", 'r')
sorting_mmr_diff = f.read().split('\n');
f.close()

f = open("sorting_waiting_time.txt", 'r')
sorting_waiting_time = f.read().split('\n');
f.close()

f = open("clustering_mmr_diff.txt", 'r')
clustering_mmr_diff = f.read().split('\n');
f.close()

f = open("clustering_waiting_time.txt", 'r')
clustering_waiting_time = f.read().split('\n');
f.close()

sns.distplot(sorting_mmr_diff,kde=False,rug=False)
sns.distplot(clustering_mmr_diff,kde=False,rug=False,color="r")
plt.show()

sns.distplot(sorting_waiting_time,kde=False,rug=False)
sns.distplot(clustering_waiting_time,kde=False,rug=False,color="r")
plt.show()
