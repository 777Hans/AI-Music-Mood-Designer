import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Spotify with your exact redirect URI
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri="http://127.0.0.1:3000/callback",  # Must match exactly
    scope="user-library-read playlist-modify-private"
))

def get_mood_based_tracks(mood):
    try:
        results = sp.search(
            q=f"mood:{mood}",
            limit=5,
            type="track",
            market="US"
        )
        return [{
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "preview_url": track["preview_url"],
            "url": track["external_urls"]["spotify"]
        } for track in results["tracks"]["items"] if track["preview_url"]]
    except Exception as e:
        print(f"Spotify Error: {e}")
        return []  # Return empty list if API fails