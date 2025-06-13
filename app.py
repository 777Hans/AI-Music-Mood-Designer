import streamlit as st
from mood_analyzer import analyze_mood
from scene_detector import split_video
from music_matcher import get_mood_based_tracks
import cv2
import tempfile
import webbrowser
import os

# Expanded mood mapping with subcategories
MOOD_CATEGORIES = {
    "Happy": ["joyful", "celebratory", "playful", "upbeat"],
    "Sad": ["melancholic", "heartbroken", "lonely", "reflective"], 
    "Energetic": ["intense", "adrenaline", "dynamic", "powerful"],
    "Calm": ["peaceful", "serene", "meditative", "dreamy"],
    "Neutral": ["ambient", "background", "instrumental"]
}

# Page config
st.set_page_config(
    page_title="AI Music Mood Designer",
    page_icon="🎵",
    layout="wide"
)

def display_tracks(mood):
    """Handle all mood categories with sub-genres"""
    if mood in MOOD_CATEGORIES:
        st.subheader(f"🎧 {mood} Mood Recommendations")
        
        # Get tracks for each subcategory
        for sub_mood in MOOD_CATEGORIES[mood]:
            with st.expander(f"🔊 {sub_mood.capitalize()}"):
                tracks = get_mood_based_tracks(sub_mood)
                if tracks:
                    for track in tracks[:3]:  # Show top 3 per subcategory
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.audio(track["preview_url"])
                        with col2:
                            st.markdown(f"**{track['name']}** by {track['artist']}")
                            st.markdown(f"[Listen on Spotify]({track['url']})")
                else:
                    st.warning(f"No {sub_mood} tracks found")

def main():
    st.title("🎵 AI Music Mood Designer")
    uploaded_file = st.file_uploader("Upload video", type=["mp4", "mov"])

    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False) as tfile:
            tfile.write(uploaded_file.read())
            video_path = tfile.name

        try:
            # Scene analysis
            scenes = split_video(video_path)
            st.write(f"📹 Detected {len(scenes)} scenes")
            
            # Mood detection (first scene only)
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            
            if ret:
                st.image(frame, channels="BGR", caption="Analyzed Frame")
                mood = analyze_mood(frame)
                
                # Enhanced mood display
                mood_emoji = {
                    "Happy": "😊",
                    "Sad": "😢", 
                    "Energetic": "⚡",
                    "Calm": "🌿",
                    "Neutral": "🎼"
                }.get(mood, "")
                
                st.success(f"{mood_emoji} Detected Mood: **{mood}**")
                display_tracks(mood)
                
        finally:
            os.unlink(video_path)

if __name__ == "__main__":
    main()