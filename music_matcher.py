import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import streamlit as st
import random

load_dotenv()

# More flexible mood-to-genre mapping
MOOD_GENRES = {
    "neutral": {
        "ambient": ["ambient", "chill", "atmospheric"],
        "instrumental": ["instrumental", "post-rock", "classical"]
    },
    "happy": {
        "joyful": ["indie pop", "happy electronic"],
        "celebratory": ["dance pop", "disco"]
    },
    "sad": {
        "melancholic": ["sad indie", "blues"],
        "heartbreak": ["piano ballads", "r&b"]
    }
}

@st.cache_resource
def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="http://127.0.0.1:3000/callback",
        scope="user-library-read",
        cache_path=".spotify_cache"
    ))

def get_mood_based_tracks(sub_mood):
    try:
        sp = get_spotify_client()
        
        # Find matching genres for the sub-mood
        genres = []
        for mood_category in MOOD_GENRES.values():
            if sub_mood.lower() in mood_category:
                genres.extend(mood_category[sub_mood.lower()])
        
        if not genres:
            genres = [sub_mood.lower()]  # Fallback to direct search
        
        # Try different genre combinations
        for attempt in range(3):
            search_query = f"genre:{random.choice(genres)} year:2020-2024"
            results = sp.search(
                q=search_query,
                limit=5,
                type="track",
                market="US"
            )
            
            if results['tracks']['items']:
                return [{
                    "name": track['name'],
                    "artist": track['artists'][0]['name'],
                    "preview_url": track['preview_url'],
                    "url": track['external_urls']['spotify']
                } for track in results['tracks']['items'] if track['preview_url']]
        
        return []  # Return empty if all attempts fail
        
    except Exception as e:
        st.error(f"Spotify Error: {str(e)}")
        return []