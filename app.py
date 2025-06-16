import streamlit as st
from mood_analyzer import analyze_mood
from scene_detector import split_video
from music_matcher import get_mood_based_tracks, log_user_selection
from video_editor import add_music_to_video
import cv2
import tempfile
import os
from dotenv import load_dotenv
import urllib.request
import time

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

def download_audio(url, output_path):
    """Download audio from URL"""
    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        st.error(f"Failed to download audio: {str(e)}")
        return False

def display_tracks(mood, scenes, scene_assignments):
    """Display tracks for each mood subcategory and allow scene assignment"""
    if mood in MOOD_CATEGORIES:
        for sub_mood in MOOD_CATEGORIES[mood]:
            with st.expander(f"🎧 {sub_mood.capitalize()} tracks"):
                tracks = get_mood_based_tracks(sub_mood)
                if tracks:
                    for track in tracks:
                        col1, col2, col3 = st.columns([1, 3, 2])
                        with col1:
                            if track["preview_url"]:
                                st.audio(track["preview_url"], format="audio/mp3")
                            else:
                                st.write("🎵 Preview not available")
                        with col2:
                            st.write(f"**{track['name']}** by {track['artist']} ([Listen on Spotify]({track['url']}))")
                        with col3:
                            scene_options = [f"Scene {i+1} ({s[0]:.1f}s - {s[1]:.1f}s)" for i, s in enumerate(scenes)]
                            selected_scene = st.selectbox("Assign to scene", ["None"] + scene_options, key=f"scene_{sub_mood}_{track['id']}")
                            if selected_scene != "None" and st.button("Assign", key=f"assign_{sub_mood}_{track['id']}"):
                                scene_idx = scene_options.index(selected_scene)
                                scene_assignments[scene_idx] = {
                                    "track": track,
                                    "sub_mood": sub_mood,
                                    "start_time": scenes[scene_idx][0],
                                    "end_time": scenes[scene_idx][1]
                                }
                                log_user_selection(sub_mood, track['id'], track['name'], track['artist'])
                                st.success(f"Assigned {track['name']} to {selected_scene}")
                else:
                    st.warning(f"No tracks found for {sub_mood}. Try refreshing or checking Spotify credentials.")
                    if st.button("Report Issue", key=f"report_{sub_mood}"):
                        st.info("Issue reported. Check debug.log for details.")

def main():
    st.title("🎵 AI Music Mood Designer")
    st.markdown("""
        Upload a video to analyze its mood, assign music to scenes, and export the edited video.
        Features: AI-driven mood matching, frame-accurate music assignment, and copyright-safe options (coming soon).
    """)
    
    # Initialize session state for scene assignments
    if "scene_assignments" not in st.session_state:
        st.session_state.scene_assignments = {}

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
            st.write(f"📹 Detected {len(scenes)} scenes: {', '.join([f'Scene {i+1}: {s[0]:.1f}s - {s[1]:.1f}s' for i, s in enumerate(scenes)])}")
            
            # Mood analysis (first frame for now)
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
                
                # Display tracks and allow scene assignment
                display_tracks(mood, scenes, st.session_state.scene_assignments)
                
                # Show assigned tracks
                if st.session_state.scene_assignments:
                    st.subheader("Assigned Tracks")
                    for scene_idx, assignment in st.session_state.scene_assignments.items():
                        st.write(f"Scene {scene_idx+1} ({assignment['start_time']:.1f}s - {assignment['end_time']:.1f}s): **{assignment['track']['name']}** by {assignment['track']['artist']}")
                
                # Render and download video
                if st.session_state.scene_assignments and st.button("Render Video"):
                    output_path = f"output_{int(time.time())}.mp4"
                    success = add_music_to_video(video_path, st.session_state.scene_assignments, output_path)
                    if success:
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="Download Edited Video",
                                data=f,
                                file_name=output_path,
                                mime="video/mp4"
                            )
                        st.success("Video rendered successfully!")
                    else:
                        st.error("Failed to render video. Check debug.log for details.")
            
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