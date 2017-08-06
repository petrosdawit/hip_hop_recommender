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
from kmeans import kmeans

def find_cluster_from_trackID(clusters, trackID, clusterSet):
	clusterLookup = 0
	for cluster in clusters:
		clusterID = cluster[0]
		for song in cluster:
			songID = song[1][0][0]
			if trackID == songID:
				clusterLookup = clusterID
	clusterArray = []
	for cluster in clusters:
		for song in cluster:
			if clusterLookup == cluster[0]:
				if song[1][0][0] not in clusterSet:
					clusterArray.append(song[1][0][0])
					clusterSet.add(song[1][0][0])
	return clusterArray

def main():
	print('Setting up kmeans and calculations')
	k = kmeans(100,30)
	clusters = k.run_mapreduce()
	clusterArr = []
	clusterSet = set()
	print('All done you may now write in command line')
	while(1):
		argv = input('Type in command: ')
		argv = argv.split()
		if len(argv) == 2:
			if argv[0] == 'f':
				trackID = argv[1]
				clusterSet = set()
				clusterArr = find_cluster_from_trackID(clusters, trackID, clusterSet)
				pprint(clusterArr)
			if argv[0] == 'a':
				trackID = argv[1]
				if trackID in clusterSet:
					print('Already in playList')
				else:
					clusterArr.extend(find_cluster_from_trackID(clusters, trackID, clusterSet))
					pprint(clusterArr)
			if argv[0] == 'd':
				trackID = argv[1]
				if trackID in clusterSet:
					clusterSet.remove(trackID)
					clusterArr.remove(trackID)
				else:
					print('Song isn\'t in playlist')

if __name__ == '__main__':
	main()
