import os
from pprint import pprint
from flask import Flask, render_template, abort, redirect, url_for, g, request, session
import sqlite3
import base64
import urllib.parse
import requests
import json
from autocomplete import Trie
from flask_socketio import SocketIO
from flask import jsonify
import ast
from datetime import datetime
from classifier import Classifier

app = Flask(__name__)
app.secret_key = 'secret_key'

#  Client Keys
CLIENT_ID = 'client_id'
CLIENT_SECRET = 'secret_key'
app.secret_key = 'secret_key

# Spotify URLS
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_BASE_URL = 'https://api.spotify.com'
API_VERSION = 'v1'
SPOTIFY_API_URL = '{}/{}'.format(SPOTIFY_API_BASE_URL, API_VERSION)

CLIENT_SIDE_URL = 'http://127.0.0.1'
PORT = 8080
REDIRECT_URI = '{}:{}/callback/q'.format(CLIENT_SIDE_URL, PORT)
SCOPE = 'playlist-modify-public playlist-modify-private'
refresh = False

auth_query_parameters = {
    'response_type': 'code',
    'redirect_uri': REDIRECT_URI,
    'scope': SCOPE,
    'client_id': CLIENT_ID
}

template_folder = os.path.dirname('templates')
user_html = os.path.join(template_folder, 'users.html')
four_o_four_html = os.path.join(template_folder, '404.html')
db_html = os.path.join(template_folder, 'db.html')
form_html = os.path.join(template_folder, 'form.html')

def connect_db():
    conn = sqlite3.connect('data/playlist_data.db')
    return conn

def refresh_access():
    code_payload = {
        'grant_type': 'refresh_token',
        'refresh_token': session['refresh_token']
    }
    base64encoded = base64.b64encode('{}:{}'.format(CLIENT_ID, CLIENT_SECRET).encode())
    headers = {'Authorization': 'Basic {}'.format(base64encoded.decode())}
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)
    response_data = json.loads(post_request.text)
    access_token = response_data['access_token']
    session['authorization_header'] = {'Authorization':'Bearer {}'.format(access_token)}

@app.before_request
def before_request():
    g.db = connect_db()
    if refresh:
        if (session['access_time']-datetime.now()).total_seconds() >= 3600:
            session['access_time'] = datetime.now()
            refresh_access()

@app.route('/')
def login():
    url_args = '&'.join(['{}={}'.format(key,urllib.parse.quote(val)) for key,val in auth_query_parameters.items()])
    auth_url = '{}/?{}'.format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)


@app.route('/callback/q', methods=['POST', 'GET'])
def callback():
    auth_token = request.args['code']
    code_payload = {
        'grant_type': 'authorization_code',
        'code': str(auth_token),
        'redirect_uri': REDIRECT_URI
    }
    base64encoded = base64.b64encode('{}:{}'.format(CLIENT_ID, CLIENT_SECRET).encode())
    headers = {'Authorization': 'Basic {}'.format(base64encoded.decode())}
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)
    response_data = json.loads(post_request.text)
    access_token = response_data['access_token']
    session['refresh_token'] = response_data['refresh_token']
    session['access_time'] = datetime.now()
    refresh = True
    session['authorization_header'] = {'Authorization':'Bearer {}'.format(access_token)}
    user_profile_api_endpoint = '{}/me'.format(SPOTIFY_API_URL)
    profile_response = requests.get(user_profile_api_endpoint, headers=session['authorization_header'])
    profile_data = json.loads(profile_response.text)
    print(profile_data)
    if not profile_data['display_name']:
        profile_data['display_name'] = profile_data['id']
    if not profile_data['images']:
        profile_data['images'] = [{'url':'../static/images/generic_profile.png'}]
    session['id'] = profile_data['id']
    session['profile_data'] = profile_data
    c = g.db.cursor()
    g.db.commit()
    return render_template(os.path.join(os.path.dirname('templates'), 'index.html'), profile_info=profile_data)

@app.route('/unsupervised', methods=['POST', 'GET'])
def unsupervised():
    autocomplete_list = []
    c = g.db.cursor()
    songs = c.execute('''select * from songs;''').fetchall()
    song_dic = {}
    trie_dic = {}
    t = Trie()
    for line in songs:
        song_key = line[0]
        t.insert(song_key.lower())
        if song_key not in trie_dic:
            autocomplete_list.append(song_key)
            trie_dic[song_key.lower()] = [song_key]
            song_dic[song_key] = line[0]
    g.db.commit()
    return render_template(os.path.join(os.path.dirname('templates'), 'unsupervised.html'), profile_info=session['profile_data'])

@app.route('/unsupervised/autocomplete', methods=['GET', 'POST'])
def autocomplete():
    autocomplete_list = []
    session['playlist_songs'] = []
    session['removed_songs'] = {}
    c = g.db.cursor()
    songs = c.execute('''SELECT *
        FROM songs
        WHERE song_name LIKE ?
        OR first_artist LIKE ?;''', (request.form['word']+'%', request.form['word']+'%')).fetchall()
    for line in songs:
        song_key = line[0]
        autocomplete_list.append(song_key)
    return jsonify(autocomplete_list)

@app.route('/unsupervised/cluster', methods=['GET', 'POST'])
def cluster():
    song_id = request.form.get('song')
    c = g.db.cursor()
    cluster = c.execute('''SELECT cluster
        FROM songs
        WHERE song_id = ?''', (song_id,) ).fetchall()
    if cluster:
        songs = c.execute('''SELECT *
            FROM songs
            WHERE cluster = ?''', (str(cluster[0][0]),) ).fetchall()
        for song in songs:
            if song not in session['removed_songs']:
                session['playlist_songs'].append(song)
        return render_template(os.path.join(os.path.dirname('templates'), 'table_list.html'), playlist=session['playlist_songs'])

@app.route('/unsupervised/remove', methods=['GET', 'POST'])
def remove_unsupervised():
    removed_song = ast.literal_eval(request.form.get('song').strip())
    playlist = ast.literal_eval(request.form.get('playlist').strip())
    session['removed_songs'][removed_song[0]] = removed_song
    output = []
    for song in playlist:
        if song[0] not in session['removed_songs']:
            output.append(song)
    if not output:
        return '<br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br> <br>'
    return render_template(os.path.join(os.path.dirname('templates'), 'table_list.html'), playlist=output)

@app.route('/create_playlist', methods=['GET', 'POST'])
def create_playlist():
    playlist = ast.literal_eval(request.form.get('playlist').strip())
    spotify_ids = []
    for song in playlist:
        spotify_ids.append(song[1])
    if not spotify_ids:
        return render_template(os.path.join(os.path.dirname('templates'), 'empty_playlist.html'), profile_info=session['profile_data'])
    head = session['authorization_header'].copy()
    head['Content-Type'] = 'application/json'
    #create playlist
    CREATE_PLAYLIST_URL = '{}/{}/{}'.format('https://api.spotify.com/v1/users',session['profile_data']['id'],'playlists')
    kwargs=json.dumps({'name': "Petros Dawit's Kmeans Hip Hop Playlist", 'public': True})
    new_playlist_data = requests.post(CREATE_PLAYLIST_URL, headers=head, data=kwargs).json()
    playlist_id = new_playlist_data['id']
    #add tracks to playlist
    ADD_TRACKS_TO_PLAYLIST_URL = '{}/{}/{}/{}/{}'.format('https://api.spotify.com/v1/users',session['profile_data']['id'],'playlists',playlist_id,'tracks')
    kwargs=json.dumps({'uris': spotify_ids})
    add_songs_to_playlist = requests.post(ADD_TRACKS_TO_PLAYLIST_URL, headers=head, data=kwargs)
    c = g.db.cursor()
    c.execute('''INSERT INTO playlists
		VALUES (?, ?, ?)''', ('{}/{}'.format(session['profile_data']['id'], playlist_id), session['profile_data']['id'], playlist_id))
    g.db.commit()
    return render_template(os.path.join(os.path.dirname('templates'), 'create_playlist.html'), profile_info=session['profile_data'], link=new_playlist_data['external_urls']['spotify'])

@app.route('/supervised', methods=['POST', 'GET'])
def supervised():
    c = g.db.cursor()
    sample_songs = c.execute('''SELECT *
        FROM songs
        WHERE song_preview != 'N/A' LIMIT 50;''').fetchall()

    return render_template(os.path.join(os.path.dirname('templates'), 'supervised.html'), profile_info=session['profile_data'], sample_songs=sample_songs)

@app.route('/created_playlists', methods=['POST', 'GET'])
def created_playlists():
    c = g.db.cursor()
    created_playlists = c.execute('''SELECT playlist_id
        FROM playlists
        WHERE user_id = ?;''', (session['profile_data']['id'],)).fetchall()
    GET_USER_PLAYLISTS = '{}/{}/{}'.format('https://api.spotify.com/v1/users',session['profile_data']['id'],'playlists')
    user_playlists = requests.get(url=GET_USER_PLAYLISTS, headers=session['authorization_header']).json()
    playlists = []
    for x in user_playlists['items']:
        for y in created_playlists:
            if x['id'] == y[0]:
                playlists.append([x['name'], x['external_urls']['spotify'], x['images'][0]['url']])
    return render_template(os.path.join(os.path.dirname('templates'), 'created_playlists.html'), profile_info=session['profile_data'], playlists=playlists)

@app.errorhandler(404)
def not_found(error):
    return render_template(four_o_four_html), 404

if __name__ == '__main__':
    app.debug = True
    app.run(port=PORT)
