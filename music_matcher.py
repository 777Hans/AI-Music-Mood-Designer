import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import streamlit as st
import json
import time
import requests
import random
import logging

logging.basicConfig(filename="debug.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

# Map sub-moods to Spotify-compatible genres and audio features
MOOD_TO_GENRE = {
    "joyful": {"genres": ["pop", "dance-pop", "tamil-pop"], "min_valence": 0.7, "min_energy": 0.6},
    "celebratory": {"genres": ["dance-pop", "party", "tamil-cinema"], "min_valence": 0.8, "min_energy": 0.7},
    "upbeat": {"genres": ["pop", "dance-pop", "tamil-pop"], "min_valence": 0.7, "min_energy": 0.8},
    "melancholic": {"genres": ["indie-pop", "singer-songwriter", "tamil-ballad"], "min_valence": 0.0, "max_valence": 0.4, "max_energy": 0.5},
    "heartbreak": {"genres": ["ballad", "pop", "tamil-ballad"], "min_valence": 0.0, "max_valence": 0.3, "max_energy": 0.4},
    "reflective": {"genres": ["ambient", "folk", "tamil-folk"], "min_valence": 0.2, "max_valence": 0.5, "max_energy": 0.4},
    "intense": {"genres": ["edm", "industrial"], "min_valence": 0.5, "min_energy": 0.8},
    "powerful": {"genres": ["rock", "epic"], "min_valence": 0.4, "min_energy": 0.7},
    "adrenaline": {"genres": ["electronic", "drum-and-bass"], "min_valence": 0.5, "min_energy": 0.9},
    "peaceful": {"genres": ["chill", "acoustic", "tamil-acoustic"], "min_valence": 0.1, "max_valence": 0.6, "max_energy": 0.4},
    "meditative": {"genres": ["ambient", "new-age"], "min_valence": 0.3, "max_valence": 0.5, "max_energy": 0.3},
    "dreamy": {"genres": ["dream-pop", "shoegaze"], "min_valence": 0.4, "max_valence": 0.6, "max_energy": 0.6},
    "ambient": {"genres": ["ambient", "chill"], "min_valence": 0.1, "max_valence": 0.5, "min_energy": 0.3, "max_energy": 0.5},
    "instrumental": {"genres": ["classical", "piano"], "min_valence": 0.3, "max_valence": 0.7, "max_energy": 0.5}
}

# Fallback genres
FALLBACK_GENRES = ["pop", "chill", "rock", "electronic", "tamil-pop"]

# Verified track IDs with previews (tested 6/16/2025)
GUARANTEED_TRACKS = {
    "ambient": [
        {"id": "7JnxZVv3n3Nkw7DhY8A8R5", "name": "Thursday Afternoon", "artist": "Brian Eno"},
        {"id": "4bK0uJ3nD3X4c8cObo0aFS", "name": "Collider", "artist": "Jon Hopkins"}
    ],
    "instrumental": [
        {"id": "5l0B8G0I0dWzVu0Z17jdg0", "name": "Time", "artist": "Ludovico Einaudi"},
        {"id": "0pneVTFUYe3E1uH2D1P3uI", "name": "River Flows in You", "artist": "Yiruma"}
    ],
    "joyful": [
        {"id": "60nZcImufyMA1MKQY3dcCH", "name": "Happy", "artist": "Pharrell Williams"},
        {"id": "2RzdvV2jBPGgoz3HQz86cS", "name": "I Gotta Feeling", "artist": "The Black Eyed Peas"}
    ],
    "melancholic": [
        {"id": "2VjkZfRJgAEoGfW7T3iG0B", "name": "My Heart Will Go On", "artist": "Celine Dion"},
        {"id": "4mU5iXHeLgbR94q8B3FjOP", "name": "Hurt", "artist": "Johnny Cash"}
    ],
    "upbeat": [
        {"id": "0FDzzruyi7gD6JqP6vg77W", "name": "Can't Stop the Feeling!", "artist": "Justin Timberlake"},
        {"id": "1vYXt7VSjUtAxsJ7CUPfzX", "name": "Sweet Child O' Mine", "artist": "Guns N' Roses"}
    ],
    "peaceful": [
        {"id": "3T6uTNAiSrsRsaWFs2WKHX", "name": "Clair de Lune", "artist": "Claude Debussy"},
        {"id": "2nvh2WOBt6SI56u1yfyxPs", "name": "Gymnopédie No.1", "artist": "Erik Satie"}
    ],
    "tamil-pop": [
        {"id": "5r1tQzi3W1gUqF62uM0S64", "name": "Vaathi Coming", "artist": "Anirudh Ravichander"},
        {"id": "2kR3T1sWOUZfYQbEu0TNB3", "name": "Maruvaarthai", "artist": "Sid Sriram"}
    ]
}

def debug_log(message):
    """Write debug messages to log file"""
    logging.debug(message)

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

def fetch_track_details(sp, track_id, name, artist, retries=2):
    """Fetch track details with retry logic"""
    for attempt in range(retries + 1):
        try:
            track = sp.track(track_id)
            return {
                "id": track_id,
                "name": name,
                "artist": artist,
                "preview_url": track.get("preview_url"),
                "url": track["external_urls"]["spotify"]
            }
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e.response, "status_code") else None
            if status_code == 429:
                wait_time = int(e.response.headers.get("Retry-After", 1))
                debug_log(f"Rate limit hit, retrying after {wait_time} seconds")
                time.sleep(wait_time)
            elif status_code in [401, 403, 404]:
                debug_log(f"HTTP {status_code} error, forcing re-authentication")
                if os.path.exists(".spotify_auth_cache"):
                    os.remove(".spotify_auth_cache")
                return None
            else:
                debug_log(f"Failed to fetch track {track_id}: {str(e)}")
                break
        except Exception as e:
            debug_log(f"Error fetching track {track_id}: {str(e)}")
            break
        time.sleep(random.uniform(0.5, 1.5))
    return {
        "id": track_id,
        "name": name,
        "artist": artist,
        "preview_url": None,
        "url": f"https://open.spotify.com/track/{track_id}"
    }

@st.cache_data(ttl=3600)
def get_mood_based_tracks(sub_mood, language="all"):
    """Fetch tracks for a given sub-mood using Spotify API"""
    debug_log(f"Fetching tracks for: {sub_mood}, language: {language}")
    
    lower_mood = sub_mood.lower()
    
    try:
        sp = get_spotify_client()
        if not sp:
            debug_log("Spotify client not initialized, falling back to guaranteed tracks")
            if lower_mood in GUARANTEED_TRACKS:
                tracks = [fetch_track_details(sp, t["id"], t["name"], t["artist"]) for t in GUARANTEED_TRACKS[lower_mood]]
                return [t for t in tracks if t.get("preview_url")] or tracks[:5]
            return []
        
        # Get valid genres
        try:
            available_genres = sp.recommendation_genre_seeds()["genres"]
            debug_log(f"Available Spotify genres: {available_genres}")
        except Exception as e:
            debug_log(f"Failed to fetch available genres: {str(e)}")
            available_genres = FALLBACK_GENRES
        
        # Get genre and audio features
        mood_config = MOOD_TO_GENRE.get(lower_mood, {"genres": FALLBACK_GENRES, "min_valence": 0.3, "max_valence": 0.7, "min_energy": 0.3, "max_energy": 0.7})
        genres = mood_config.get("genres", FALLBACK_GENRES)
        valid_genres = [g for g in genres if g in available_genres]
        valid_genres = [g for g in valid_genres if language == "all" or (language == "tamil" and "tamil" in g) or (language == "english" and "tamil" not in g)]
        if not valid_genres:
            valid_genres = [g for g in FALLBACK_GENRES if language == "all" or (language == "tamil" and "tamil" in g) or (language == "english" and "tamil" not in g)]
        
        params = {
            "seed_genres": ",".join(valid_genres[:5]),
            "limit": 20,
            "min_valence": mood_config.get("min_valence", 0.3),
            "max_valence": mood_config.get("max_valence", 0.7),
            "min_energy": mood_config.get("min_energy", 0.3),
            "max_energy": mood_config.get("max_energy", 0.7)
        }
        
        debug_log(f"Fetching recommendations for genres: {valid_genres}, params: {params}")
        try:
            results = sp.recommendations(**params)
            tracks = []
            for track in results["tracks"]:
                if track.get("preview_url"):
                    tracks.append({
                        "name": track["name"],
                        "artist": track["artists"][0]["name"],
                        "preview_url": track.get("preview_url"),
                        "url": track["external_urls"]["spotify"],
                        "id": track["id"]
                    })
            if len(tracks) >= 5:
                debug_log(f"Found {len(tracks)} tracks via recommendations for {sub_mood}")
                return tracks[:5]
        except Exception as e:
            debug_log(f"Recommendations failed for {sub_mood}: {str(e)}")
        
        # Fallback to search
        debug_log(f"Falling back to search for {sub_mood}")
        tracks = []
        for genre in valid_genres:
            try:
                query = f"genre:\"{genre}\" year:2018-2025"
                if language == "tamil":
                    query += " language:tamil"
                results = sp.search(q=query, limit=20, type="track")
                for track in results["tracks"]["items"]:
                    if track.get("preview_url"):
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
            except Exception as e:
                debug_log(f"Search failed for genre {genre}: {str(e)}")
        
        if tracks:
            debug_log(f"Found {len(tracks)} tracks via search for {sub_mood}")
            return tracks[:5]
        
        debug_log(f"No tracks found for {sub_mood}, using guaranteed tracks")
        if lower_mood in GUARANTEED_TRACKS:
            tracks = [fetch_track_details(sp, t["id"], t["name"], t["artist"]) for t in GUARANTEED_TRACKS[lower_mood]]
            return [t for t in tracks if t.get("preview_url")] or tracks[:5]
        return []
    
    except Exception as e:
        debug_log(f"Spotify API error for {sub_mood}: {str(e)}")
        st.error(f"Failed to fetch tracks for {sub_mood}. Error: {str(e)}")
        if lower_mood in GUARANTEED_TRACKS:
            tracks = [fetch_track_details(sp, t["id"], t["name"], t["artist"]) for t in GUARANTEED_TRACKS[lower_mood]]
            return [t for t in tracks if t.get("preview_url")] or tracks[:5]
        return []