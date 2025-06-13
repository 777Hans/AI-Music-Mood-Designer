import streamlit as st
from mood_analyzer import analyze_mood
from scene_detector import split_video
from music_matcher import get_mood_based_tracks
import cv2
import tempfile

st.title("🎵 AI Music Mood Designer")
uploaded_file = st.file_uploader("Upload Video", type=["mp4", "mov"])

if uploaded_file:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    scenes = split_video(tfile.name)
    st.write(f"Detected {len(scenes)} scenes.")
    
    cap = cv2.VideoCapture(tfile.name)
    ret, frame = cap.read()
    mood = analyze_mood(frame)
    st.write(f"Overall Mood: {mood}")
    
    tracks = get_mood_based_tracks(mood.lower())
    st.write("Recommended Tracks:")
    for track in tracks:
        st.write(f"{track['name']} by {track['artist']}")
        st.audio(track["preview_url"])