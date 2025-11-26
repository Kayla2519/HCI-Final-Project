import os
import random
import logging
import requests
from flask import jsonify
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', os.urandom(32))

CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID', '1aaf8e65994a48f78edc3b37c950deea')
CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET', '0e19bc6af9c542dfa724961b643d854b')
REDIRECT_URI = os.environ.get('SPOTIPY_REDIRECT_URI', 'https://musu-ypu7.onrender.com/callback')
SCOPE = "user-read-private user-read-email playlist-read-private playlist-modify-public playlist-modify-private"

cache_handler = FlaskSessionCacheHandler(session)

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_handler=cache_handler,
    show_dialog=True
)

def get_spotify_client():
    token_info = cache_handler.get_cached_token()
    if not token_info:
        return None
    
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    return Spotify(auth=token_info['access_token'])

def ensure_authorized():
    token_info = cache_handler.get_cached_token()
    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return None

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/')
def index():
    token_check = cache_handler.get_cached_token()
    if not token_check:
        return render_template('index.html', authenticated=False)
    return render_template('index.html', authenticated=True)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    error = request.args.get('error')
    if error:
        logging.error("Spotify callback returned error: %s", error)
        return "Spotify authentication error: " + str(error), 400
    if not code:
        logging.error("Callback hit but no code in query string.")
        return "Missing code in callback.", 400

    try:
        token_info = sp_oauth.get_access_token(code)
    except Exception as e:
        logging.exception("Failed to exchange code for token")
        return "Failed to complete authentication with Spotify.", 500

    if not token_info:
        logging.error("No token returned on callback.")
        return "Authentication failed (no token).", 500

    # token saved via cache_handler inside SpotifyOAuth implementation
    logging.info("Spotify auth successful, token cached.")
    return redirect(url_for('select_moods'))

@app.route('/select_moods', methods=['GET', 'POST'])
def select_moods():
    maybe = ensure_authorized()
    if maybe:
        return maybe

    moods = ["Happy", "Sad", "Chill", "Energetic", "Angry"]
    if request.method == "POST":
        selected = request.form.getlist('moods')
        session['moods'] = selected
        return redirect(url_for('select_genres'))
    return render_template('select_moods.html', moods=moods)

mood_to_genres = {
    "Happy": ["Pop", "Dance"],
    "Sad": ["Acoustic", "Indie", "Blues"],
    "Chill": ["Lo-Fi", "Jazz", "Ambient"],
    "Energetic": ["Rock", "Hip-Hop", "EDM"],
    "Angry": ["Metal", "Hard Rock", "Punk"],
}

@app.route('/select_genres', methods=['GET', 'POST'])
def select_genres():
    maybe = ensure_authorized()
    if maybe:
        return maybe

    selected_moods = session.get('moods', [])
    if not selected_moods:
        return redirect(url_for('select_moods'))

    genres = []
    for m in selected_moods:
        genres.extend(mood_to_genres.get(m, []))
    genres = sorted(set(genres))

    if request.method == "POST":
        selected_genres = request.form.getlist('genres')
        session['genres'] = selected_genres
        return redirect(url_for('song_result'))
    return render_template('select_genres.html', genres=genres)

@app.route('/song_result')
def song_result():
    maybe = ensure_authorized()
    if maybe:
        return maybe
    return render_template('song_result.html')

@app.route('/api/get_song', methods=['GET'])
def api_get_song():
    sp = get_spotify_client()
    if not sp:
        return jsonify({"error": "not_authenticated", "message": "Please login first."}), 401

    selected_genres = session.get('genres', [])
    if not selected_genres:
        return jsonify({"error": "no_genres_selected", "message": "No genres selected! Please select one or more genres."}), 400

    genre = random.choice(selected_genres)
    
    try:
        results = sp.search(q=genre, type="artist", limit=15)
    except Exception as e:
        logging.exception("Spotify search failed")
        return jsonify({"error": "spotify_error", "message": "Error querying Spotify API."}), 500

    artists = results.get('artists', {}).get('items', [])
    if not artists:
        return jsonify({"error": "no_artists", "message": f"No artists found for genre {genre}."}), 404

    artist = random.choice(artists)

    try:
        top_tracks_resp = sp.artist_top_tracks(artist['id'], country='US')
    except Exception as e:
        logging.exception("Failed to get artist top tracks")
        return jsonify({"error": "spotify_error", "message": "Error fetching top tracks."}), 500

    top_tracks = top_tracks_resp.get('tracks', [])
    if not top_tracks:
        return jsonify({"error": "no_top_tracks", "message": f"No top tracks found for artist {artist.get('name','') }."}), 404

    track = random.choice(top_tracks)
    preview_url = track.get('preview_url')
    album_images = track.get('album', {}).get('images', [])
    album_cover = album_images[0]['url'] if album_images else ''

    response = {
        "name": track.get('name'),
        "artist": artist.get('name'),
        "album_cover": album_cover,
        "spotify_url": track.get('external_urls', {}).get('spotify'),
        "preview_url": preview_url,
        "genre_used": genre
    }
    return jsonify(response)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/api/get_preview", methods = ["POST"])
def get_preview():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.json
    query = f"{data['artist']} {data['name']}"
    url = f"https://api.deezer.com/search?q={query}"

    r = requests.get(url).json()
    
    if "data" in r:
        data = r["data"][0]
        preview = data.get("preview")
        print(data)
        return jsonify({"preview_url": preview})

    return jsonify({"preview_url": None})
if __name__ == '__main__':
    app.run(debug=True)
