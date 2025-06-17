# app.py - Enhanced Version
import streamlit as st
from mood_analyzer import analyze_mood
from music_matcher import search_youtube_tracks, get_preferred_track_name, log_user_selection
from video_editor import add_music_to_video
from scene_detector import split_video
import cv2
import tempfile
import os
import logging
import json
import uuid
import webbrowser

logging.basicConfig(filename="debug.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

st.set_page_config(page_title="AI Music Mood Designer", page_icon="🎵", layout="wide")

# Specific song recommendations for each mood
MOOD_SONG_RECOMMENDATIONS = {
    "Happy": {
        "joyful": ["Happy - Pharrell Williams", "Good as Hell - Lizzo", "Can't Stop the Feeling - Justin Timberlake"],
        "celebratory": ["Celebration - Kool & The Gang", "I Gotta Feeling - Black Eyed Peas", "Uptown Funk - Bruno Mars"],
        "upbeat": ["Cheap Thrills - Sia", "Shut Up and Dance - Walk the Moon", "Best Day of My Life - American Authors"],
        "elated": ["On Top of the World - Imagine Dragons", "Walking on Sunshine - Katrina and the Waves", "Good Time - Owl City"],
        "cheerful": ["Count on Me - Bruno Mars", "Three Little Birds - Bob Marley", "Here Comes the Sun - The Beatles"]
    },
    "Sad": {
        "melancholic": ["Mad World - Gary Jules", "Hurt - Johnny Cash", "Black - Pearl Jam"],
        "heartbreak": ["Someone Like You - Adele", "All Too Well - Taylor Swift", "Before You Go - Lewis Capaldi"],
        "reflective": ["Let Me Down Slowly - Alec Benjamin", "Arcade - Duncan Laurence", "Fix You - Coldplay"],
        "grieving": ["Tears in Heaven - Eric Clapton", "Angel - Sarah McLachlan", "See You Again - Wiz Khalifa"],
        "lonely": ["Alone - Marshmello", "Boulevard of Broken Dreams - Green Day", "Mad About You - Sting"]
    },
    "Energetic": {
        "intense": ["Till I Collapse - Eminem", "Eye of the Tiger - Survivor", "Thunderstruck - AC/DC"],
        "powerful": ["Stronger - Kelly Clarkson", "Roar - Katy Perry", "Fight Song - Rachel Platten"],
        "adrenaline": ["Pump It - Black Eyed Peas", "Can't Hold Us - Macklemore", "Animals - Martin Garrix"],
        "motivated": ["Lose Yourself - Eminem", "Hall of Fame - The Script", "Champion - Fall Out Boy"],
        "amped": ["Bangarang - Skrillex", "Levels - Avicii", "Titanium - David Guetta"]
    },
    "Calm": {
        "peaceful": ["Weightless - Marconi Union", "Clair de Lune - Debussy", "River Flows in You - Yiruma"],
        "meditative": ["Om Mani Padme Hum", "Tibetan Singing Bowls", "Deep Meditation - Liquid Mind"],
        "dreamy": ["Mad World - Gary Jules", "Breathe Me - Sia", "Hide and Seek - Imogen Heap"],
        "soothing": ["Aqueous Transmission - Incubus", "Porcelain - Moby", "Teardrop - Massive Attack"],
        "serene": ["Spiegel im Spiegel - Arvo Pärt", "The Blue Notebooks - Max Richter", "Elegy for Dunkirk - Dario Marianelli"]
    },
    "Neutral": {
        "ambient": ["Music for Airports - Brian Eno", "Discreet Music - Brian Eno", "Stars of the Lid"],
        "instrumental": ["Experience - Ludovico Einaudi", "Nuvole Bianche - Ludovico Einaudi", "Comptine d'un autre été"],
        "background": ["Lofi Hip Hop", "Study Music", "Coffee Shop Ambience"],
        "cinematic": ["Time - Hans Zimmer", "Lux Aeterna - Clint Mansell", "On Earth as It Is in Heaven - Angels & Airwaves"]
    },
    "Angry": {
        "furious": ["Break Stuff - Limp Bizkit", "Bodies - Drowning Pool", "Chop Suey - System of a Down"],
        "aggressive": ["B.Y.O.B. - System of a Down", "Killing in the Name - Rage Against the Machine", "Down with the Sickness - Disturbed"],
        "heavy": ["Enter Sandman - Metallica", "Master of Puppets - Metallica", "Ace of Spades - Motörhead"],
        "explosive": ["TNT - AC/DC", "Sabotage - Beastie Boys", "Seven Nation Army - The White Stripes"]
    },
    "Romantic": {
        "loving": ["All of Me - John Legend", "Perfect - Ed Sheeran", "A Thousand Years - Christina Perri"],
        "sensual": ["Earned It - The Weeknd", "Partition - Beyoncé", "Pony - Ginuwine"],
        "passionate": ["Crazy in Love - Beyoncé", "I Want to Know What Love Is - Foreigner", "Love Me Like You Do - Ellie Goulding"],
        "flirty": ["Blurred Lines - Robin Thicke", "Can't Feel My Face - The Weeknd", "Sugar - Maroon 5"]
    },
    "Anxious": {
        "tense": ["Paranoid Android - Radiohead", "Creep - Radiohead", "Anxiety - Julia Michaels"],
        "nervous": ["Stressed Out - Twenty One Pilots", "Heavy - Linkin Park", "Breathe - Telepopmusik"],
        "uncertain": ["Mad Hatter - Melanie Martinez", "Control - Halsey", "Scars to Your Beautiful - Alessia Cara"]
    },
    "Hopeful": {
        "inspirational": ["Rise Up - Andra Day", "Stronger - Kelly Clarkson", "Believer - Imagine Dragons"],
        "uplifting": ["Viva La Vida - Coldplay", "Dog Days Are Over - Florence + The Machine", "Shake It Out - Florence + The Machine"],
        "faithful": ["Amazing Grace", "I Can Only Imagine - MercyMe", "Oceans - Hillsong United"]
    },
    "Surprised": {
        "shocked": ["Oh My God - Adele", "Somebody That I Used to Know - Gotye", "Radioactive - Imagine Dragons"],
        "amazed": ["Fireworks - Katy Perry", "Speechless - Dan + Shay", "A Million Dreams - The Greatest Showman"],
        "excited": ["Uptown Funk - Bruno Mars", "24K Magic - Bruno Mars", "Good 4 U - Olivia Rodrigo"]
    }
}

def initialize_state():
    # Initialize dictionary-type session state variables
    dict_keys = ["segments", "assignments", "track_cache", "local_tracks", "track_map", "track_selection", "manual_segments"]
    for key in dict_keys:
        if key not in st.session_state:
            st.session_state[key] = {}
    
    # Initialize single-value session state variables
    single_keys = ["video_path", "main_mood", "sub_mood", "video_duration", "manual_mode"]
    for key in single_keys:
        if key not in st.session_state:
            st.session_state[key] = None
    
    # Initialize boolean flags
    if "manual_mode" not in st.session_state:
        st.session_state.manual_mode = False

def get_video_duration(video_path):
    """Get video duration in seconds"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    return duration

def format_time(seconds):
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def video_upload_tab():
    st.header("1. Upload and Analyze Video")
    uploaded = st.file_uploader("Upload video (MP4)", type=["mp4"])
    if uploaded:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded.read())
        st.session_state.video_path = tfile.name

        cap = cv2.VideoCapture(tfile.name)
        ret, frame = cap.read()
        if ret:
            st.image(frame, channels="BGR", caption="First Frame")
            main_mood, sub_mood = analyze_mood(frame)
            st.session_state.main_mood = main_mood
            st.session_state.sub_mood = sub_mood
            st.session_state.video_duration = get_video_duration(tfile.name)
            
            st.success(f"Mood Detected: {main_mood} → {sub_mood}")
            st.info(f"Video Duration: {format_time(st.session_state.video_duration)}")
            
            # Scene detection mode selection
            st.subheader("Scene Assignment Mode")
            mode_choice = st.radio(
                "Choose how to assign music to your video:",
                ["Automatic Scene Detection", "Manual Timeline Selection"],
                key="assignment_mode"
            )
            
            if mode_choice == "Automatic Scene Detection":
                st.session_state.manual_mode = False
                segments = split_video(tfile.name)
                st.session_state.segments = segments
                st.write(f"Detected {len(segments)} automatic scenes")
                for i, (start, end) in enumerate(segments):
                    st.write(f"Scene {i+1}: {format_time(start)} - {format_time(end)}")
            else:
                st.session_state.manual_mode = True
                st.info("You can manually define segments in the Music Selection tab.")
                
        cap.release()

def music_tab():
    st.header("2. Music Selection and Assignment")

    if not st.session_state.sub_mood:
        st.warning("Please upload and analyze a video first.")
        return

    # Get sub_mood and ensure it's not None
    sub_mood = st.session_state.sub_mood
    if sub_mood is None:
        st.warning("No mood detected. Please upload and analyze a video first.")
        return

    st.subheader("Upload Local Music")
    uploaded_tracks = st.file_uploader("Upload audio files (mp3/wav)", type=["mp3", "wav"], accept_multiple_files=True)
    if uploaded_tracks:
        for track in uploaded_tracks:
            # Use filename as consistent ID to avoid regenerating UUIDs
            track_id = f"local_{track.name}_{track.size}"
            
            # Only process if we haven't seen this track before
            if track_id not in st.session_state.local_tracks:
                path = os.path.join(tempfile.gettempdir(), f"{track_id}_{track.name}")
                with open(path, "wb") as f:
                    f.write(track.read())
                st.session_state.local_tracks[track_id] = {
                    "id": track_id,
                    "name": track.name,
                    "artist": "Local File",
                    "path": path,
                    "source": "local"
                }

    main_mood = st.session_state.main_mood
    st.info(f"Detected mood category: {main_mood}, sub-mood: {sub_mood}")

    # Show specific song recommendations
    st.subheader("🎵 Recommended Songs for Your Mood")
    if main_mood in MOOD_SONG_RECOMMENDATIONS and sub_mood in MOOD_SONG_RECOMMENDATIONS[main_mood]:
        recommendations = MOOD_SONG_RECOMMENDATIONS[main_mood][sub_mood]
        st.write(f"**Perfect matches for '{sub_mood}' mood:**")
        for song in recommendations:
            st.write(f"• {song}")
        st.info("💡 Tip: Search for these songs on YouTube or upload them as local files!")

    st.subheader("Search for Music on YouTube")
    search_query = st.text_input("Search a song by name", placeholder="e.g., Cheap Thrills Sia")
    if search_query:
        url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}+download"
        if st.button("Open in Browser"):
            webbrowser.open_new_tab(url)
            st.info("Use a YouTube downloader and upload the file above after download.")

    # Ensure all local tracks are in track_map
    for track in st.session_state.local_tracks.values():
        st.session_state.track_map[track["id"]] = track
    
    # Create all_tracks_map from track_map (single source of truth)
    all_tracks_map = dict(st.session_state.track_map)
    
    if not all_tracks_map:
        st.warning("No tracks available. Please upload local files first.")
        return

    # Manual or Automatic Assignment
    if st.session_state.manual_mode:
        manual_assignment_interface(all_tracks_map)
    else:
        automatic_assignment_interface(all_tracks_map, sub_mood)

def manual_assignment_interface(all_tracks_map):
    st.subheader("🎬 Manual Timeline Assignment")
    
    if not st.session_state.video_duration:
        st.warning("Video duration not available. Please re-upload your video.")
        return
    
    duration = st.session_state.video_duration
    st.write(f"Video Duration: {format_time(duration)}")
    
    # Add new segment
    st.write("**Add New Music Segment:**")
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        start_time = st.number_input("Start Time (seconds)", min_value=0.0, max_value=duration, value=0.0, step=0.1, key="new_start")
    with col2:
        end_time = st.number_input("End Time (seconds)", min_value=start_time, max_value=duration, value=min(start_time + 10, duration), step=0.1, key="new_end")
    with col3:
        if st.button("Add Segment", key="add_segment"):
            segment_id = len(st.session_state.manual_segments)
            st.session_state.manual_segments[segment_id] = {
                "start_time": start_time,
                "end_time": end_time,
                "track": None,
                "effects": []
            }
            st.success(f"Added segment: {format_time(start_time)} - {format_time(end_time)}")
            st.rerun()

    # Display and edit existing segments
    if st.session_state.manual_segments:
        st.write("**Your Music Segments:**")
        
        segments_to_remove = []
        for segment_id, segment in st.session_state.manual_segments.items():
            with st.container():
                st.markdown(f"### Segment {segment_id + 1}: {format_time(segment['start_time'])} - {format_time(segment['end_time'])}")
                
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    # Track selection
                    current_track_id = segment.get("track", {}).get("id") if segment.get("track") else None
                    track_options = list(all_tracks_map.keys())
                    
                    if current_track_id and current_track_id in all_tracks_map:
                        default_index = track_options.index(current_track_id)
                    else:
                        default_index = 0
                    
                    selected_track_id = st.selectbox(
                        f"Select track for segment {segment_id + 1}",
                        options=track_options,
                        format_func=lambda tid: all_tracks_map[tid]["name"],
                        key=f"manual_track_{segment_id}",
                        index=default_index
                    )
                    
                    # Update segment with selected track
                    st.session_state.manual_segments[segment_id]["track"] = all_tracks_map[selected_track_id]
                
                with col2:
                    # Effects selection
                    effects = st.multiselect(
                        f"Effects for segment {segment_id + 1}",
                        ["Fade In", "Fade Out", "Reverse", "Echo", "Volume Ramp Up", "Volume Ramp Down", "Pitch Shift Up", "Pitch Shift Down"],
                        default=segment.get("effects", []),
                        key=f"manual_effects_{segment_id}"
                    )
                    st.session_state.manual_segments[segment_id]["effects"] = effects
                
                with col3:
                    if st.button(f"Remove", key=f"remove_{segment_id}"):
                        segments_to_remove.append(segment_id)
        
        # Remove segments that were marked for removal
        for segment_id in segments_to_remove:
            del st.session_state.manual_segments[segment_id]
            st.rerun()
        
        # Copy manual segments to assignments for rendering
        st.session_state.assignments = dict(st.session_state.manual_segments)
    
    else:
        st.info("No segments added yet. Add your first music segment above!")

def automatic_assignment_interface(all_tracks_map, sub_mood):
    st.subheader("🤖 Automatic Scene Assignment")
    
    # Check if we have segments
    if not st.session_state.segments:
        st.warning("No video segments detected. Please upload and analyze a video first.")
        return
        
    for i, (start, end) in enumerate(st.session_state.segments):
        st.markdown(f"### Scene {i+1} - {format_time(start)} to {format_time(end)}")

        # Get the current selection from session state or use first track as default
        current_selection = st.session_state.track_selection.get(i)
        if current_selection is None or current_selection not in all_tracks_map:
            current_selection = list(all_tracks_map.keys())[0]
            st.session_state.track_selection[i] = current_selection

        # Find the index of the current selection
        track_ids = list(all_tracks_map.keys())
        current_index = track_ids.index(current_selection) if current_selection in track_ids else 0

        # Create selectbox with proper index
        selected_id = st.selectbox(
            f"Select track for scene {i+1}",
            options=track_ids,
            format_func=lambda tid: all_tracks_map[tid]["name"],
            key=f"track_select_{i}",
            index=current_index
        )

        # Update session state with the new selection
        if selected_id != st.session_state.track_selection.get(i):
            st.session_state.track_selection[i] = selected_id

        effects = st.multiselect(
            f"Audio Effects for scene {i+1}",
            ["Fade In", "Fade Out", "Reverse", "Echo", "Volume Ramp Up", "Volume Ramp Down", "Pitch Shift Up", "Pitch Shift Down"],
            default=st.session_state.assignments.get(i, {}).get("effects", []),
            key=f"effects_{i}"
        )

        # Always use the selected_id for assignment
        st.session_state.assignments[i] = {
            "start_time": start,
            "end_time": end,
            "track": all_tracks_map[selected_id],
            "effects": effects
        }

        if st.button(f"Save assignment for scene {i+1}", key=f"save_{i}"):
            log_user_selection(sub_mood, all_tracks_map[selected_id])
            st.success(f"Scene {i+1} assignment saved")

def render_tab():
    st.header("3. Render Final Video")
    
    # Check what assignments we have
    assignments_source = "manual segments" if st.session_state.manual_mode else "automatic scenes"
    
    if not st.session_state.video_path or not st.session_state.assignments:
        st.warning("Complete earlier steps first")
        return
    
    st.write(f"**Ready to render with {len(st.session_state.assignments)} {assignments_source}**")
    
    # Show summary of assignments
    st.subheader("Assignment Summary")
    for i, assignment in st.session_state.assignments.items():
        start = assignment["start_time"]
        end = assignment["end_time"]
        track_name = assignment["track"]["name"]
        effects = assignment.get("effects", [])
        
        st.write(f"**Segment {i+1}:** {format_time(start)} - {format_time(end)}")
        st.write(f"  • Track: {track_name}")
        if effects:
            st.write(f"  • Effects: {', '.join(effects)}")
    
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    if st.button("🎬 Render Video", type="primary"):
        with st.spinner("Rendering video... This may take a few minutes."):
            success = add_music_to_video(
                st.session_state.video_path,
                st.session_state.assignments,
                output
            )
        if success:
            st.video(output)
            st.success("🎉 Video rendered successfully!")
            
            # Provide download link info
            st.info(f"💾 Your video has been saved temporarily. You can right-click the video above to save it.")
        else:
            st.error("❌ Failed to render video. Check the debug.log for details.")

def main():
    initialize_state()
    
    # Sidebar for current status
    with st.sidebar:
        st.header("📊 Current Status")
        if st.session_state.video_path:
            st.success("✅ Video uploaded")
            if st.session_state.video_duration:
                st.write(f"Duration: {format_time(st.session_state.video_duration)}")
        else:
            st.warning("❌ No video uploaded")
            
        if st.session_state.main_mood:
            st.success(f"✅ Mood: {st.session_state.main_mood}")
        else:
            st.warning("❌ No mood detected")
            
        if st.session_state.local_tracks:
            st.success(f"✅ {len(st.session_state.local_tracks)} local tracks")
        else:
            st.info("ℹ️ No local tracks uploaded")
            
        assignment_count = len(st.session_state.assignments) if st.session_state.assignments else 0
        if assignment_count > 0:
            mode = "Manual" if st.session_state.manual_mode else "Auto"
            st.success(f"✅ {assignment_count} {mode.lower()} assignments")
        else:
            st.warning("❌ No music assignments")
    
    tabs = st.tabs(["📹 Upload Video", "🎵 Select Music", "🎬 Render Video"])
    with tabs[0]:
        video_upload_tab()
    with tabs[1]:
        music_tab()
    with tabs[2]:
        render_tab()

if __name__ == "__main__":
    main()