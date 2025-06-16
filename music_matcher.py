import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import streamlit as st
import json
import time

load_dotenv()

# Map sub-moods to Spotify-compatible genres and audio features
MOOD_TO_GENRE = {
    "joyful": {"genres": ["pop", "dance-pop"], "min_valence": 0.7, "min_energy": 0.6},
    "celebratory": {"genres": ["dance-pop", "party"], "min_valence": 0.8, "min_energy": 0.7},
    "upbeat": {"genres": ["pop", "dance-pop"], "min_valence": 0.7, "min_energy": 0.8},
    "melancholic": {"genres": ["indie-pop", "singer-songwriter"], "min_valence": 0.0, "max_valence": 0.4, "max_energy": 0.5},
    "heartbreak": {"genres": ["ballad", "pop"], "min_valence": 0.0, "max_valence": 0.3, "max_energy": 0.4},
    "reflective": {"genres": ["ambient", "folk"], "min_valence": 0.2, "max_valence": 0.5, "max_energy": 0.4},
    "intense": {"genres": ["edm", "hard-rock"], "min_valence": 0.5, "min_energy": 0.8},
    "powerful": {"genres": ["rock", "epic"], "min_valence": 0.4, "min_energy": 0.7},
    "adrenaline": {"genres": ["electronic", "drum-and-bass"], "min_valence": 0.5, "min_energy": 0.9},
    "peaceful": {"genres": ["chill", "acoustic"], "min_valence": 0.4, "max_valence": 0.6, "max_energy": 0.4},
    "meditative": {"genres": ["ambient", "new-age"], "min_valence": 0.3, "max_valence": 0.5, "max_energy": 0.3},
    "dreamy": {"genres": ["dream-pop", "shoegaze"], "min_valence": 0.4, "max_valence": 0.6, "max_energy": 0.5},
    "ambient": {"genres": ["ambient", "chill"], "min_valence": 0.3, "max_valence": 0.5, "min_energy": 0.3, "max_energy": 0.5},
    "instrumental": {"genres": ["instrumental", "classical"], "min_valence": 0.3, "max_valence": 0.7, "max_energy": 0.5}
}

# Fallback genres
FALLBACK_GENRES = ["pop", "chill", "rock", "electronic"]

# Hardcoded tracks as last resort
GUARANTEED_TRACKS = {
    "ambient": [
        {"id": "2JSpTinIqzVXeqyDHselnO", "name": "Stars", "artist": "Hans Zimmer"},
        {"id": "3iJ8GX9QYNDd6zjg8OQTaS", "name": "Weightless", "artist": "Marconi Union"}
    ],
    "instrumental": [
        {"id": "6PZYj3Z3wJ8Hl4VYfz4i5x", "name": "River Flows In You", "artist": "Yiruma"},
        {"id": "3W3qGw1KfKDVQ2XkAZZ5f2", "name": "Experience", "artist": "Ludovico Einaudi"}
    ],
    "joyful": [
        {"id": "3n3Ppam7vgaVa1iaRUc9Lp", "name": "Happy", "artist": "Pharrell Williams"},
        {"id": "6NPVjNh8Jhru9xOmyQigds", "name": "Walking on Sunshine", "artist": "Katrina and The Waves"}
    ],
    "melancholic": [
        {"id": "2P5A0gz5yL1rV3WrdF3bX3", "name": "My Heart Will Go On", "artist": "Celine Dion"},
        {"id": "0c1gT2QzQ7k6c1bK4rTGFV", "name": "Hurt", "artist": "Johnny Cash"}
    ],
    "upbeat": [
        {"id": "7ouMYWpwJ422jRcDASZB7P", "name": "Can't Stop the Feeling!", "artist": "Justin Timberlake"},
        {"id": "4kLLWz7srcuLKA7Et40cWR", "name": "Sweet Child O' Mine", "artist": "Guns N' Roses"}
    ],
    "peaceful": [
        {"id": "3Dy5Yd9GG2zRDE3hFNSZBj", "name": "Clair de Lune", "artist": "Claude Debussy"},
        {"id": "5W7cgc7XjOIBTwv7kD2q6G", "name": "Gymnopédie No.1", "artist": "Erik Satie"}
    ]
}

def debug_log(message):
    """Write debug messages to log file"""
    with open("debug.log", "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def log_user_selection(sub_mood, track_id, track_name, artist):
    """Log user-selected tracks for adaptive learning"""
    try:
        user_selections = []
        if os.path.exists("user_selections.json"):
            with open("user_selections.json", "r") as f:
                user_selections = json.load(f)
        user_selections.append({
            "sub_mood": sub_mood,
            "track_id": track_id,
            "track_name": track_name,
            "artist": artist,
            "timestamp": time.time()
        })
        with open("user_selections.json", "w") as f:
            json.dump(user_selections, f, indent=2)
        debug_log(f"Logged user selection: {track_name} for {sub_mood}")
    except Exception as e:
        debug_log(f"Failed to log user selection: {str(e)}")

@st.cache_resource
def get_spotify_client():
    """Initialize Spotify client with authentication"""
    try:
        debug_log("Initializing Spotify client...")
        auth_manager = SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri="http://127.0.0.1:3000/callback",
            scope="user-library-read",
            cache_path=".spotify_auth_cache",
            show_dialog=True
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        sp.current_user()
        debug_log("Client initialized and authenticated successfully")
        return sp
    except Exception as e:
        debug_log(f"Client init failed: {str(e)}")
        st.error(f"Spotify connection failed: {str(e)}. Please check credentials, delete .spotify_auth_cache, and restart the app.")
        return None

def fetch_track_details(sp, track_id, name, artist):
    """Fetch track details including preview_url from Spotify API"""
    try:
        track = sp.track(track_id, market="US")
        return {
            "id": track_id,
            "name": name,
            "artist": artist,
            "preview_url": track.get("preview_url"),
            "url": track["external_urls"]["spotify"]
        }
    except Exception as e:
        debug_log(f"Failed to fetch details for track {track_id}: {str(e)}")
        return {
            "id": track_id,
            "name": name,
            "artist": artist,
            "preview_url": None,
            "url": f"https://open.spotify.com/track/{track_id}"
        }

@st.cache_data(ttl=3600)
def get_mood_based_tracks(sub_mood):
    """Fetch tracks for a given sub-mood using Spotify API"""
    debug_log(f"Fetching tracks for: {sub_mood}")
    
    lower_mood = sub_mood.lower()
    
    try:
        sp = get_spotify_client()
        if not sp:
            debug_log("Spotify client not initialized, falling back to guaranteed tracks")
            if lower_mood in GUARANTEED_TRACKS:
                return [fetch_track_details(sp, t["id"], t["name"], t["artist"]) for t in GUARANTEED_TRACKS[lower_mood]]
            return []
        
        # Get genre and audio features
        mood_config = MOOD_TO_GENRE.get(lower_mood, {"genres": FALLBACK_GENRES, "min_valence": 0.3, "max_valence": 0.7, "min_energy": 0.3, "max_energy": 0.7})
        genres = mood_config.get("genres", FALLBACK_GENRES)
        params = {
            "seed_genres": ",".join([g for g in genres[:5] if g]),  # Ensure valid genres
            "limit": 10,
            "market": "US",
            "min_valence": mood_config.get("min_valence", 0.3),
            "max_valence": mood_config.get("max_valence", 0.7),
            "min_energy": mood_config.get("min_energy", 0.3),
            "max_energy": mood_config.get("max_energy", 0.7)
        }
        
        debug_log(f"Fetching recommendations for genres: {genres}, params: {params}")
        results = sp.recommendations(**params)
        
        tracks = []
        for track in results["tracks"]:
            tracks.append({
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "preview_url": track.get("preview_url"),
                "url": track["external_urls"]["spotify"],
                "id": track["id"]
            })
        
        if len(tracks) >= 5:
            debug_log(f"Found {len(tracks)} tracks via recommendations for {sub_mood}")
            return tracks
        
        # Fallback to search
        debug_log(f"Insufficient tracks from recommendations, falling back to search for {sub_mood}")
        for genre in genres + FALLBACK_GENRES:
            results = sp.search(
                q=f"genre:\"{genre}\" year:2020-2024",
                limit=10,
                type="track",
                market="US"
            )
            for track in results["tracks"]["items"]:
                tracks.append({
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "preview_url": track.get("preview_url"),
                    "url": track["external_urls"]["spotify"],
                    "id": track["id"]
                })
                if len(tracks) >= 5:
                    break
            if len(tracks) >= 5:
                break
        
        if tracks:
            debug_log(f"Found {len(tracks)} tracks via search for {sub_mood}")
            return tracks
        
        debug_log(f"No tracks found for {sub_mood}, using guaranteed tracks")
        if lower_mood in GUARANTEED_TRACKS:
            return [fetch_track_details(sp, t["id"], t["name"], t["artist"]) for t in GUARANTEED_TRACKS[lower_mood]]
        return []
    
    except Exception as e:
        debug_log(f"Spotify API error for {sub_mood}: {str(e)}")
        st.error(f"Failed to fetch tracks for {sub_mood}. Error: {str(e)}")
        if lower_mood in GUARANTEED_TRACKS:
            return [fetch_track_details(sp, t["id"], t["name"], t["artist"]) for t in GUARANTEED_TRACKS[lower_mood]]
        return []