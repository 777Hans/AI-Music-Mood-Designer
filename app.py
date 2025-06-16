import streamlit as st
from mood_analyzer import analyze_mood
from scene_detector import split_video
from music_matcher import get_mood_based_tracks, log_user_selection
from video_editor import add_music_to_video
import cv2
import tempfile
import os
from dotenv import load_dotenv
import time
import webbrowser
import logging

logging.basicConfig(filename="debug.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

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

def display_tracks(mood, scenes, scene_assignments, language):
    """Display tracks for each mood subcategory and allow scene assignment"""
    logging.debug(f"Displaying tracks for mood: {mood}, language: {language}")
    if mood in MOOD_CATEGORIES:
        for sub_mood in MOOD_CATEGORIES[mood]:
            with st.expander(f"🎧 {sub_mood.capitalize()} tracks"):
                tracks = get_mood_based_tracks(sub_mood, language)
                if tracks:
                    for track in tracks:
                        col1, col2, col3, col4 = st.columns([1, 3, 2, 1])
                        with col1:
                            if track.get("preview_url"):
                                try:
                                    st.audio(track["preview_url"], format="audio/mp3")
                                except Exception as e:
                                    st.write(f"🎵 Playback error: {str(e)}")
                                    logging.error(f"Playback error for {track['name']}: {str(e)}")
                            else:
                                st.write("🎵 Preview not available")
                        with col2:
                            st.write(f"**{track['name']}** by {track['artist']} ([Listen on Spotify]({track['url']}))")
                        with col3:
                            scene_options = [f"Scene {i+1} ({s[0]:.1f}s - {s[1]:.1f}s)" for i, s in enumerate(scenes)]
                            selected_scene = st.selectbox("Assign to scene", ["None"] + scene_options, key=f"scene_{sub_mood}_{track['id']}")
                            start_frame = st.number_input("Start frame", min_value=0, value=0, key=f"start_frame_{sub_mood}_{track['id']}")
                            effects = st.multiselect("Effects", ["Fade In", "Fade Out", "Crossfade"], key=f"effects_{sub_mood}_{track['id']}")
                            if selected_scene != "None" and st.button("Assign", key=f"assign_{sub_mood}_{track['id']}"):
                                try:
                                    scene_idx = scene_options.index(selected_scene)
                                    scene_assignments[scene_idx] = {
                                        "track": track,
                                        "sub_mood": sub_mood,
                                        "start_time": scenes[scene_idx][0],
                                        "end_time": scenes[scene_idx][1],
                                        "start_frame": start_frame,
                                        "effects": effects
                                    }
                                    log_user_selection(sub_mood, track['id'], track['name'], track['artist'])
                                    st.success(f"Assigned {track['name']} to {selected_scene}")
                                    logging.info(f"Assigned {track['name']} to Scene {scene_idx+1}")
                                except Exception as e:
                                    st.error(f"Assignment failed: {str(e)}")
                                    logging.error(f"Assignment failed for {track['name']}: {str(e)}")
                        with col4:
                            if st.button("Download", key=f"download_{sub_mood}_{track['id']}"):
                                webbrowser.open(track['url'])
                                st.info("Opened Spotify link in browser. Note: Downloading requires a Spotify Premium account or third-party tools.")
                                logging.info(f"Opened download link for {track['name']}")
                else:
                    st.warning(f"No tracks found for {sub_mood}. Try deleting .spotify_auth_cache and restarting the app.")
                    if st.button("Report Issue", key=f"report_{sub_mood}"):
                        st.info("Issue reported. Check debug.log for details.")
                        logging.info(f"Issue reported for {sub_mood}")
    else:
        st.error(f"Invalid mood detected: {mood}. Please check video input or mood analyzer.")
        logging.error(f"Invalid mood detected: {mood}")

def main():
    st.title("🎵 AI Music Mood Designer")
    st.markdown("""
        Upload a video to analyze its mood, assign music to scenes, and export the edited video.
        Features: AI-driven mood matching, frame-accurate music assignment, Tamil/English songs, and audio effects.
    """)
    
    # Initialize session state
    if "scene_assignments" not in st.session_state:
        st.session_state.scene_assignments = {}
    if "video_path" not in st.session_state:
        st.session_state.video_path = None
    if "scenes" not in st.session_state:
        st.session_state.scenes = []

    # Language selection
    language = st.selectbox("Select Language", ["All", "Tamil", "English"], key="language_select")

    uploaded_file = st.file_uploader("Upload a video", type=["mp4", "mov"])

    if uploaded_file:
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
                tfile.write(uploaded_file.read())
                st.session_state.video_path = tfile.name

            # Scene detection
            st.session_state.scenes = split_video(st.session_state.video_path)
            st.write(f"📹 Detected {len(st.session_state.scenes)} scenes: {', '.join([f'Scene {i+1}: {s[0]:.1f}s - {s[1]:.1f}s' for i, s in enumerate(st.session_state.scenes)])}")
            
            # Mood analysis
            cap = cv2.VideoCapture(st.session_state.video_path)
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
                }.get(mood, "❓")
                st.success(f"{mood_emoji} Detected Mood: **{mood}**")
                logging.info(f"Detected mood: {mood}")
                
                # Display tracks and allow scene assignment
                display_tracks(mood, st.session_state.scenes, st.session_state.scene_assignments, language)
                
                # Show assigned tracks
                if st.session_state.scene_assignments:
                    st.subheader("Assigned Tracks")
                    for scene_idx, assignment in sorted(st.session_state.scene_assignments.items()):
                        st.write(f"Scene {scene_idx+1} ({assignment['start_time']:.1f}s - {assignment['end_time']:.1f}s): **{assignment['track']['name']}** by {assignment['track']['artist']} (Frame: {assignment['start_frame']}, Effects: {', '.join(assignment['effects'])})")
                
                # Render and download video
                if st.session_state.scene_assignments and st.button("Render Video"):
                    output_path = f"output_{int(time.time())}.mp4"
                    success = add_music_to_video(st.session_state.video_path, st.session_state.scene_assignments, output_path)
                    if success:
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="Download Edited Video",
                                data=f,
                                file_name=output_path,
                                mime="video/mp4"
                            )
                        st.success("Video rendered successfully!")
                        logging.info(f"Video rendered to {output_path}")
                    else:
                        st.error("Failed to render video. Check debug.log for details.")
                        logging.error("Video rendering failed")
            
        except Exception as e:
            st.error(f"Error processing video: {str(e)}")
            logging.error(f"Video processing failed: {str(e)}")
        
        finally:
            # Clean up temp file
            if st.session_state.video_path and os.path.exists(st.session_state.video_path):
                try:
                    os.unlink(st.session_state.video_path)
                except PermissionError:
                    pass
                st.session_state.video_path = None

if __name__ == "__main__":
    main()