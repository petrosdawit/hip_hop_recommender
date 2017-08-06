import spotipy
import json
from spotipy import oauth2
import operator
from pprint import pprint
from sklearn import preprocessing
import numpy as np
from mapreduce import mapreduce
import sqlite3
import copy
import sys

class kmeans(object):

	def __init__(self, numClusters, numIterations):
		'''
			Create our number of clusters we want, our number of iterations for kmeans and the list
			which will have the centroid random node values
		'''
		self._numClusters = numClusters
		self._numIterations = numIterations
		self._centroidRandomNodes = []

	def run_mapreduce(self):
		'''
        Parameters:
            Input: None
            Output: Clusters
        Purpose:
            This function fetches all the data from the database. From here it formats in a way that will
            run on mapreduce. It then runs the maps and reducers the amount of iterations you set. It then
            returns the clusters
        '''
		conn = sqlite3.connect('data/playlist_data.db')
		conn.text_factory = lambda x: str(x, 'latin1')
		c = conn.cursor()
		c.execute("""select * from songs;""")
		d = c.fetchall()
		data = []
		for i in range(len(d)):
			key = [d[i][0],d[i][1],d[i][2], d[i][3], d[i][4], d[i][5], d[i][6], d[i][7]]
			values = []
			for y in range(8,len(d[i])):
				values.append(d[i][y])
			data.append([key,values])
		for i in range(len(data)):
			data[i] = [(0),data[i]]
		data2 = copy.deepcopy(data)
		for i in range(self._numClusters):
			self._centroidRandomNodes.append([(i),data2[i][1][1]])
		sc = mapreduce()
		output = []
		new_data = data
		result = []
		for i in range(self._numIterations):
			result = (sc.parallelize(data,128).map(self.mapper1) \
											  .reduceByKey(self.reducer) \
											  .map(self.mapper2) \
			 								  .collect())
		sc.stop()
		return result

	def k_means_check(self, record):
		'''
        Parameters:
            Input: Record
            Output: Cluster index where the record should be
        Purpose:
            Finds the cluster index by gettin the cluster index whose feature values are
            closest to it by distance to the record
        '''
		k_index = 0
		min_calc = float('inf')
		for node in self._centroidRandomNodes:
			i = node[0]
			centroid_data = node[1]
			val = self.k_means_check_calc(record[1],centroid_data)
			if val < min_calc:
				min_calc = val
				k_index = i
		return k_index

	def k_means_check_calc(self, record, data):
		'''
        Parameters:
            Input: Record, data
            Output: Summation of differences between centroid data values and record values
        Purpose:
            helper function for k_means_check
        '''
		val = 0
		for i in range(len(record)):
			val += abs(record[i] - data[i])**2
		return val

	def calc_new_centroid_index(self, record):
		'''
        Parameters:
            Input: Record that is grouped from reducer
            Output: None
        Purpose:
            calculates the new centroid index feature values by getting the average values
            from the cluster
        '''
		index = record[0]
		values = record[1]
		n = len(values)
		centroid = self._centroidRandomNodes[index]
		for i in range(10):
			_sum = 0
			for value in values:
				v = value[1]
				_sum += v[i]
			centroid[1][i] = _sum/n

	def mapper1(self, record):
		'''
        Parameters:
            Input: Record
            Output: ((key), [record[1]]) --> (key for index, [song data, features for song])
        Purpose:
            calculate the index for the record and set is as the key. return a tuple of the key and
            the song data
        '''
		key = self.k_means_check(record[1])
		output = ((key),[record[1]])
		return output

	def reducer(self, a, b):
		'''
        Parameters:
            Input: record a and record b which had the same cluster index
            Output: a + b
        Purpose:
            Group the two records
        '''
		return a + b

	def mapper2(self, record):
		'''
        Parameters:
            Input: grouped up record values with the same cluster index
            Output: list of lists which have the first index by a tuple of the cluster index and the
            second index the song data
        Purpose:
            Calculate the new centroid index for the cluster. Then return the data in the same format it
            came in so we can run the mapreduce algo our number of iterations we set it.
        '''
		self.calc_new_centroid_index(record)
		index = record[0]
		output = []
		for value in record[1]:
			output.append([(index), value])
		return output

if __name__ == '__main__':
	k = kmeans(100,10)
	clusters = k.run_mapreduce()
	conn = sqlite3.connect('data/playlist_data.db')
	conn.text_factory = lambda x: str(x, 'latin1')
	c = conn.cursor()
	t = True
	for cluster in clusters:
		for song_info in cluster:
			cluster_id = song_info[0]
			song_id = song_info[1][0][0]
			c.execute(''' UPDATE songs
      			SET cluster = ?
      			WHERE song_id = ?''', (str(cluster_id), song_id))
	conn.commit()
