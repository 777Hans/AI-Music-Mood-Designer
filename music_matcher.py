import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
))

def get_mood_based_tracks(mood):
    results = sp.search(q=f"mood:{mood}", limit=5, type="track")
    return [{
        "name": track["name"],
        "artist": track["artists"][0]["name"],
        "preview_url": track["preview_url"]
    } for track in results["tracks"]["items"]]