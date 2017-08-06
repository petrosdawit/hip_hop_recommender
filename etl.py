import spotipy
import json
from spotipy import oauth2
import operator
from pprint import pprint
from sklearn import preprocessing
import numpy as np
from mapreduce import mapreduce
import sqlite3
import sys


class ETL(object):

	def __init__(self):
		'''
			Create our sp which allows us to utilize spotify api with our client id and secret.
		'''
		client_id = 'e7a0d1b5196e47778815263f04ae4379'
		client_secret = '5907fe8be8fc4fa8bd93a03b17031afe'
		client_credentials_manager = oauth2.SpotifyClientCredentials(client_id, client_secret)
		self._sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
		self._song_id = set()

	def clean_features(self, featureSet):
		featuresToKeep = {
			'valence',
			'danceability',
			'loudness',
			'acousticness',
			'mode',
			'energy',
			'instrumentalness',
			'speechiness',
			'liveness',
			'tempo'
		}
		for key in list(featureSet.keys()):
			if key not in featuresToKeep:
				del featureSet[key]
		return featureSet

	def store_track_features(self, featuresByTrack, tracks):
		'''
		Parameters:
			Input: featuresByTrack set and 'tracks' value we get from api which got from the playlist
			Output: None
		Purpose:
			We update the featuresByTrack by going through the 'tracks' value data. We obtain the featureSet
			values and the key which consists of song id, song name and artist name. We run the featureSet through
			a helper function which only keeps the tracks we want. We then update our featuresByTrack set.
		'''
		trackIds = [item['track']['id'] for item in tracks['items']]
		featureSets = self._sp.audio_features(trackIds)
		for i, (item, featureSet) in enumerate(zip(tracks['items'], featureSets)):
			track = item['track']
			cleanFeatureSet = self.clean_features(featureSet)
			preview_url = 'N/A'
			album_image = '..static/images/generic_album.png'
			if track['preview_url']:
				preview_url = track['preview_url']
			if track['album']['images'][0]['url']:
				album_image = track['album']['images'][0]['url']
			if track['name'] + ' by ' + track['artists'][0]['name'] not in self._song_id:
				featuresByTrack[track['name'] + ' by ' + track['artists'][0]['name'],track['uri'], track['name'], track['artists'][0]['name'], track['album']['name'], album_image, preview_url, 0] = cleanFeatureSet
				self._song_id.add(track['name'] + ' by ' + track['artists'][0]['name'])

	def get_features_by_track(self):
		'''
		Parameters:
			Input: None
			Output: dictionary of keys made of song name, track id and song id with the values being its
			feature set which we handpick
		Purpose:
			Have sp get the results table from the user's playlists. Then go through the results and pass
			in the 'tracks' value into the store track by features. We have created a set of featuresByTrack
			that is passed in as well to which we will add the features and its key in store_track_features
			function
		'''
		results = []
		# #TEST RESULTS
		# results.append(self._sp.user_playlist('spotify', '5FJXhjdILmRA2z5bvz4nzf', fields="tracks,next"))
		#CURRENT HIP HOP SPOTIFY PLAYLISTS
		results.append(self._sp.user_playlist('113275810', '67O96UwjvdMQY5cIFtBZUb', fields="tracks,next"))
		results.append(self._sp.user_playlist('spotify', '06KmJWiQhL0XiV6QQAHsmw', fields="tracks,next"))
		results.append(self._sp.user_playlist('gingertyunited', '21sgjLGbnEgNMTpjnaO2b6', fields="tracks,next"))
		results.append(self._sp.user_playlist('1210132854', '6iWogCnTKuubCG6JNxiLjq', fields="tracks,next"))
		# print('Appending from playlist id 67O96UwjvdMQY5cIFtBZUb')
		# print('Appending from playlist id 06KmJWiQhL0XiV6QQAHsmw')
		# print('Appending from playlist id 21sgjLGbnEgNMTpjnaO2b6')
		# print('Appending from playlist id 6iWogCnTKuubCG6JNxiLjq')
		featuresByTrack = {}
		for result in results:
			tracks = result['tracks']
			self.store_track_features(featuresByTrack, tracks)
			while tracks['next']:
				tracks = self._sp.next(tracks)
				self.store_track_features(featuresByTrack, tracks)
		return featuresByTrack

	def drop_and_load(self, featuresByTrack):
		'''
		Parameters:
			Input: list of list which contains in the first index, a tuple of the key which is the song id,
			song name and artist name and the second index being a list of all the features and its value
			Output: None
		Purpose:
			In this function, we drop the table of songs if it doesn't exist and insert all the values
			and keys into a table called songs
		'''
		conn = sqlite3.connect('data/playlist_data.db')
		conn.text_factory = lambda x: str(x, 'latin1')
		c = conn.cursor()
		c.execute('DROP TABLE IF EXISTS "songs";')
		c.execute('DROP TABLE IF EXISTS "playlists";')
		c.execute('''
	            CREATE TABLE songs(
	                song_id text not null,
					spotify_id text not null,
	                song_name text,
					first_artist text,
					album_name text,
					album_image text,
					song_preview text,
					cluster real,
					valence real,
					danceability real,
					loudness real,
					acousticness real,
					mode real,
					energy real,
					instrumentalness real,
					speechiness real,
					liveness real,
					tempo real,
	                PRIMARY KEY(song_id))
	                ''')
		c.execute('''
	            CREATE TABLE playlists(
					id text not null,
	                user_id text not null,
					playlist_id text not null,
	                PRIMARY KEY(id))
	                ''')
		conn.commit()
		print('The song table recorded ' + str(len(featuresByTrack)) + ' songs')
		with open('data/song_names.txt', 'w') as f:
			for data in featuresByTrack:
				key = data[0]
				value = {}
				for x in data[1]:
					value[x[0]] = x[1]
				song_id = key[0]
				spotify_id = key[1]
				song_name = key[2]
				first_artist = key[3]
				album_name = key[4]
				album_image = key[5]
				song_preview = key[6]
				cluster = key[7]
				valence = value['valence']
				danceability = value['danceability']
				loudness = value['loudness']
				acousticness = value['acousticness']
				mode = value['mode']
				energy = value['energy']
				instrumentalness = value['instrumentalness']
				speechiness = value['speechiness']
				liveness = value['liveness']
				tempo = value['tempo']
				c.execute('''
		            INSERT INTO songs
		            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (song_id, spotify_id, song_name,
		            	first_artist, album_name, album_image, song_preview, cluster, valence, danceability, loudness, acousticness, mode,
		            	energy, instrumentalness, speechiness, liveness, tempo))
				#file writing the song information
				f.write(song_id.lower() + ',' + song_name+ ',' + first_artist + '\n')
		conn.commit()
		print('Succesfully created new table song with loaded data')

	def update(self, featuresByTrack):
		'''
		Parameters:
			Input: list of list which contains in the first index, a tuple of the key which is the song id,
			song name and artist name and the second index being a list of all the features and its value
			Output: None
		Purpose:
			Update our database if any song is not in the database yet. It also creates that table songs again
			if the table doesn't exist.
		'''
		conn = sqlite3.connect('data/playlist_data.db')
		conn.text_factory = lambda x: str(x, 'latin1')
		c = conn.cursor()
		c.execute('''
	            CREATE TABLE IF NOT EXISTS songs(
	                song_id text not null,
					spotify_id text not null,
	                song_name text,
					first_artist text,
					album_name text,
					album_image text,
					song_preview text,
					cluster real,
					valence real,
					danceability real,
					loudness real,
					acousticness real,
					mode real,
					energy real,
					instrumentalness real,
					speechiness real,
					liveness real,
					tempo real,
	                PRIMARY KEY(song_id))
	                ''')
		c.execute("""select song_id, spotify_id, song_name, first_artist, album_name, album_image, song_preview, cluster from songs;""")
		data = c.fetchall()
		song_ids = set()
		for song in data:
			song_ids.add(song[0])
		insert = []
		for song in featuresByTrack:
			if song[0][0] not in song_ids:
				insert.append(song)
		print('Inserting ' + str(len(insert)) + ' more songs to the database')
		with open('data/song_names.txt', 'a') as f:
			for data in insert:
				key = data[0]
				value = {}
				for x in data[1]:
					value[x[0]] = x[1]
				song_id = key[0]
				spotify_id = key[1]
				song_name = key[2]
				first_artist = key[3]
				album_name = key[4]
				album_image = key[5]
				song_preview = key[6]
				cluster = key[7]
				valence = value['valence']
				danceability = value['danceability']
				loudness = value['loudness']
				acousticness = value['acousticness']
				mode = value['mode']
				energy = value['energy']
				instrumentalness = value['instrumentalness']
				speechiness = value['speechiness']
				liveness = value['liveness']
				tempo = value['tempo']
				c.execute('''
		            INSERT OR REPLACE INTO songs
		            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (song_id, spotify_id, song_name,
		            	first_artist, album_name, album_image, song_preview, cluster, valence, danceability, loudness, acousticness, mode,
		            	energy, instrumentalness, speechiness, liveness, tempo))
				f.write(song_id.lower() + ',' + song_name+ ',' + first_artist + '\n')
		conn.commit()
		print('Successfully updated the songs table')

	def format_data_for_db(self, featuresByTrack):
		'''
		Parameters:
			Input: dictionary of keys made of song name, track id and song id with the values being its
			feature set which we handpick
			Output: list of list which contains in the first index, a tuple of the key which is the song id,
			song name and artist name and the second index being a list of all the features and its value
		Purpose:
			Formats the data in a way which makes it easy to load our data into the database.
		'''
		data = []
		for track, feature in featuresByTrack.items():
			data_song = []
			data_song.append((track))
			k = []
			for f, score in feature.items():
				k.append([f, score])
			data_song.append(k)
			data.append(data_song)
		for data_song in data:
			unscaled = []
			for features in data_song[1]:
				if features[1]:
					unscaled.append(features[1])
				else:
					unscaled.append(0)
			np_scaled = preprocessing.scale(np.array(unscaled))
			n = len(data_song[1])
			for i in range(n):
				features = data_song[1][i]
				features[1] = float("{0:.3f}".format(np_scaled[i]))
		return data

if __name__ == '__main__':
	if len(sys.argv) != 2:
		print('The commands are load and update')
		print('Load deletes the song table and creates a new song table with the song data from the playlists')
		print('Update retains the current song table and updates any new song from the playlists to the song table')
	elif sys.argv[1] != 'load' and sys.argv[1] != 'update':
		print('The commands are load and update')
		print('Load deletes the song table and creates a new song table with the song data from the playlists')
		print('Update retains the current song table and updates any new song from the playlists to the song table')
	else:
		etl = ETL()
		featuresByTrack = etl.get_features_by_track()
		data = etl.format_data_for_db(featuresByTrack)
		if sys.argv[1] == 'load':
			etl.drop_and_load(data)
		elif sys.argv[1] == 'update':
			etl.update(data)
