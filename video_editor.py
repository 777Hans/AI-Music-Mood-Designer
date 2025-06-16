import ffmpeg
import urllib.request
import os
import tempfile
from music_matcher import debug_log

def download_audio(url, output_path):
    """Download audio from URL"""
    try:
        urllib.request.urlretrieve(url, output_path)
        debug_log(f"Downloaded audio to {output_path}")
        return True
    except Exception as e:
        debug_log(f"Failed to download audio {url}: {str(e)}")
        return False

def add_music_to_video(video_path, scene_assignments, output_path):
    """Add music to video scenes with crossfades"""
    try:
        # Create temporary directory for audio files
        temp_dir = tempfile.mkdtemp()
        
        # Download audio files for assigned tracks
        audio_files = {}
        for scene_idx, assignment in scene_assignments.items():
            if assignment["track"]["preview_url"]:
                audio_path = os.path.join(temp_dir, f"track_{scene_idx}.mp3")
                if download_audio(assignment["track"]["preview_url"], audio_path):
                    audio_files[scene_idx] = {
                        "path": audio_path,
                        "start_time": assignment["start_time"],
                        "duration": assignment["end_time"] - assignment["start_time"]
                    }
        
        if not audio_files:
            debug_log("No valid audio files downloaded")
            return False
        
        # Create FFmpeg input stream for video
        video_stream = ffmpeg.input(video_path)
        
        # Prepare audio streams with trimming and delays
        audio_streams = []
        for scene_idx, audio_info in audio_files.items():
            audio_stream = ffmpeg.input(audio_info["path"]).filter(
                "atrim", start=0, duration=audio_info["duration"]
            ).filter(
                "adelay", delays=int(audio_info["start_time"] * 1000)
            )
            audio_streams.append(audio_stream)
        
        # Merge audio streams with crossfades
        if len(audio_streams) > 1:
            merged_audio = ffmpeg.filter(
                audio_streams, "amix", inputs=len(audio_streams), duration="longest"
            )
        else:
            merged_audio = audio_streams[0]
        
        # Combine video and audio, replace original audio
        output = ffmpeg.output(
            video_stream.video, merged_audio,
            output_path,
            c_v="copy",  # Copy video stream without re-encoding
            c_a="aac",   # Encode audio as AAC
            map_metadata=-1
        )
        
        # Run FFmpeg command
        ffmpeg.run(output, overwrite_output=True)
        debug_log(f"Video rendered successfully to {output_path}")
        return True
    
    except Exception as e:
        debug_log(f"Video rendering failed: {str(e)}")
        return False
    
    finally:
        # Clean up temporary audio files
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                try:
                    os.unlink(os.path.join(temp_dir, file))
                except Exception:
                    pass
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass