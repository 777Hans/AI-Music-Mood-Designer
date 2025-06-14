import streamlit as st
from mood_analyzer import analyze_mood
from scene_detector import split_video
from music_matcher import get_mood_based_tracks
import cv2
import tempfile
import os
from dotenv import load_dotenv

# Initialize environment
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Music Mood Designer",
    page_icon="🎵",
    layout="wide"
)

# Expanded mood categories with subgenres
MOOD_CATEGORIES = {
    "Happy": ["joyful", "celebratory", "upbeat"],
    "Sad": ["melancholic", "heartbreak", "reflective"],
    "Energetic": ["intense", "powerful", "adrenaline"],
    "Calm": ["peaceful", "meditative", "dreamy"],
    "Neutral": ["ambient", "instrumental"]
}

def display_tracks(mood):
    """Display tracks for each mood subcategory"""
    if mood in MOOD_CATEGORIES:
        for sub_mood in MOOD_CATEGORIES[mood]:
            with st.expander(f"🎧 {sub_mood.capitalize()} tracks"):
                tracks = get_mood_based_tracks(sub_mood)
                if tracks:
                    for track in tracks:
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.audio(track["preview_url"])
                        with col2:
                            st.write(f"**{track['name']}** by {track['artist']}")
                else:
                    st.warning("No tracks found for this mood")

def main():
    st.title("🎵 AI Music Mood Designer")
    uploaded_file = st.file_uploader("Upload a video", type=["mp4", "mov"])

    if uploaded_file:
        video_path = None
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
                tfile.write(uploaded_file.read())
                video_path = tfile.name

            # Scene detection
            scenes = split_video(video_path)
            st.write(f"📹 Detected {len(scenes)} scenes")

            # Mood analysis (first frame only)
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            
            if ret:
                st.image(frame, channels="BGR", caption="Analyzed Frame")
                mood = analyze_mood(frame)
                
                # Display mood with emoji
                mood_emoji = {
                    "Happy": "😊",
                    "Sad": "😢",
                    "Energetic": "⚡",
                    "Calm": "🌿",
                    "Neutral": "🎵"
                }.get(mood, "")
                st.success(f"{mood_emoji} Detected Mood: **{mood}**")
                
                # Get and display tracks
                display_tracks(mood)
            
        except Exception as e:
            st.error(f"Error processing video: {str(e)}")
        
        finally:
            # Clean up temp file
            if video_path and os.path.exists(video_path):
                try:
                    os.unlink(video_path)
                except PermissionError:
                    pass  # Skip if file is locked

if __name__ == "__main__":
    main()