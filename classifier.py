from sklearn.svm import LinearSVC
from sklearn.neighbors import KNeighborsClassifier
import numpy as np
import random
import sqlite3
from pprint import pprint
import math
from operator import itemgetter


class Classifier(object):

    def __init__(self, playlist, k=0):
        self._k = k
        self._playlist = playlist

    def feature_transform(self, feats):
        newFeats = []
        for f in feats:
            newFeats.append(f)
        assert len(feats) == len(newFeats), 'Feature transform deleted/created new records!'
        return newFeats

    def train_classifier(self, rawTrainingFeats,trainingLabels, classifier):
        feats = self.feature_transform(rawTrainingFeats)
        c = classifier
        c.fit(feats, trainingLabels)
        return c

    def get_results(self):
        conn = sqlite3.connect('data/playlist_data.db')
        conn.text_factory = lambda x: str(x, 'latin1')
        c = conn.cursor()
        c.execute("""select * from songs;""")
        d = c.fetchall()

        allFeats = []
        allLabels = []
        for i in range(len(d)):
            allLabels.append(random.randrange(6))
            allFeats.append(list(d[i][8:]))
        trainFeats = allFeats[:50]
        print(trainFeats[0])
        trainLabels = allLabels[:50]
        testFeats = allFeats[50:]
        clf = self.train_classifier(trainFeats, trainLabels, LinearSVC())
        knn = self.train_classifier(trainFeats, trainLabels, KNeighborsClassifier())
        testLabelsKNN = knn.predict(testFeats)
        testLabelsSVM = clf.predict(testFeats)

        results = []
        k = -1
        a = np.array(trainLabels)
        median = np.median(a)
        if median > 3:
            k = 1
        for i in range(len(testFeats)):
            if k == 1:
                results.append([math.ceil((testLabelsSVM[i] + testLabelsKNN[i])/2), testFeats[i]])
            else:
                results.append([int((testLabelsSVM[i] + testLabelsKNN[i])/2), testFeats[i]])
        results.sort(key=itemgetter(0), reverse=True)
        return results

    def get_next_playlist_songs(self, results):
        n = len(results)
        i = self._k
        c = 0
        songs = []
        while i < n and c < 50:
            songs.append(results[i])
            i += 1
            c += 1
        if i >= n:
            y = i - n
            for j in range(n-1,n-y,-1):
                songs.append(results[j])
            return songs
        self._k += 50
        for song in songs:
            self._playlist.add((song[0],tuple(song[1])))
        return songs


if __name__=='__main__':
    c = Classifier(set())
    results = c.get_results()
    c.get_next_playlist_songs(results)
    c.get_next_playlist_songs(results)
    print(c._playlist)
