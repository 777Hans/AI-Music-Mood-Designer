import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import streamlit as st
import webbrowser

# Load environment variables
load_dotenv()

# Spotify authentication manager with enhanced settings
def get_spotify_client():
    @st.experimental_singleton  # Persists auth across Streamlit reruns
    def init_client():
        return spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri="http://localhost:3000/callback",
            scope="user-library-read playlist-modify-private",
            cache_path=".spotify_auth_cache",
            show_dialog=True  # Forces login prompt if token expires
        ))
    return init_client()

# Enhanced track recommendation with mood subcategories
def get_mood_based_tracks(mood):
    """Get tracks matching mood with fallback logic"""
    MOOD_MAPPING = {
        "Happy": ["upbeat pop", "happy indie", "joyful electronic"],
        "Sad": ["sad indie", "melancholic piano", "heartbreak songs"],
        "Energetic": ["high energy workout", "power rock", "intense electronic"],
        "Calm": ["calm meditation", "peaceful guitar", "soft piano"],
        "Neutral": ["background study", "ambient electronic", "instrumental jazz"]
    }
    
    try:
        sp = get_spotify_client()
        
        # Try exact mood match first
        results = sp.search(
            q=f"mood:{mood.lower()} year:2020-2024",
            limit=5,
            type="track",
            market="US"
        )
        
        # Fallback to subgenres if no results
        if not results['tracks']['items'] and mood in MOOD_MAPPING:
            for subgenre in MOOD_MAPPING[mood]:
                results = sp.search(
                    q=f"genre:{subgenre} year:2020-2024",
                    limit=5,
                    type="track",
                    market="US"
                )
                if results['tracks']['items']:
                    break
        
        # Process results
        tracks = []
        for track in results['tracks']['items']:
            if track['preview_url']:  # Only include tracks with previews
                tracks.append({
                    "name": track['name'],
                    "artist": track['artists'][0]['name'],
                    "preview_url": track['preview_url'],
                    "url": track['external_urls']['spotify'],
                    "image": track['album']['images'][0]['url'] if track['album']['images'] else None
                })
        
        return tracks[:5]  # Return max 5 tracks
        
    except Exception as e:
        st.error(f"Spotify API Error: {str(e)}")
        return []

# Debug function for testing
if __name__ == "__main__":
    st.write("## Spotify Connection Test")
    if st.button("Test Spotify API"):
        tracks = get_mood_based_tracks("happy")
        if tracks:
            st.success(f"Found {len(tracks)} tracks!")
            st.json(tracks[0])  # Show first track details
        else:
            st.error("No tracks found or API failed")