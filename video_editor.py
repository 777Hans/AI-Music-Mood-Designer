import subprocess
import os
import tempfile
import requests
from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_audioclips
import logging

logging.basicConfig(filename="debug.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def download_audio(url, output_path):
    """Download audio from URL"""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Downloaded audio to {output_path}")
            return True
        else:
            logging.error(f"Failed to download audio from {url}, status code: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error downloading audio from {url}: {str(e)}")
        return False

def apply_audio_effects(audio_path, output_path, effects, duration_ms):
    """Apply audio effects using pydub"""
    try:
        audio = AudioSegment.from_file(audio_path)
        if "Fade In" in effects:
            audio = audio.fade_in(2000)  # 2-second fade-in
        if "Fade Out" in effects:
            audio = audio.fade_out(2000)  # 2-second fade-out
        audio = audio[:duration_ms]  # Trim to required duration
        audio.export(output_path, format="mp3")
        logging.info(f"Applied effects {effects} to {output_path}")
        return True
    except Exception as e:
        logging.error(f"Error applying effects to {audio_path}: {str(e)}")
        return False

def add_music_to_video(video_path, scene_assignments, output_path):
    """Add music to video with frame-accurate placement and effects"""
    try:
        video = VideoFileClip(video_path)
        fps = video.fps
        audio_clips = []
        temp_files = []

        for scene_idx, assignment in sorted(scene_assignments.items()):
            track = assignment["track"]
            start_time = assignment["start_time"]
            end_time = assignment["end_time"]
            start_frame = assignment["start_frame"]
            effects = assignment.get("effects", [])
            
            # Convert start_frame to seconds
            start_offset = start_frame / fps if start_frame else 0
            duration = (end_time - start_time) * 1000  # Duration in ms
            
            if track.get("preview_url"):
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                if download_audio(track["preview_url"], temp_audio):
                    temp_processed = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                    if apply_audio_effects(temp_audio, temp_processed, effects, duration):
                        audio_clip = AudioFileClip(temp_processed)
                        audio_clip = audio_clip.set_start(start_time + start_offset)
                        audio_clips.append(audio_clip)
                        temp_files.extend([temp_audio, temp_processed])
                    else:
                        logging.error(f"Failed to process audio for track {track['name']}")
                else:
                    logging.error(f"Failed to download audio for track {track['name']}")
            else:
                logging.warning(f"No preview URL for track {track['name']}")

        if audio_clips:
            # Handle crossfade
            for i in range(len(audio_clips) - 1):
                if "Crossfade" in scene_assignments[i].get("effects", []):
                    audio_clips[i] = audio_clips[i].crossfadein(2.0)
            
            final_audio = concatenate_audioclips(audio_clips)
            final_video = video.set_audio(final_audio)
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
            logging.info(f"Video rendered successfully to {output_path}")
            
            # Clean up
            video.close()
            for clip in audio_clips:
                clip.close()
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            return True
        else:
            logging.error("No audio clips to add to video")
            return False
    
    except Exception as e:
        logging.error(f"Error rendering video: {str(e)}")
        return False