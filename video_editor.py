# video_editor.py
import os
import tempfile
import logging
from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
from music_matcher import download_youtube_audio

logging.basicConfig(filename="debug.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def apply_audio_effects(audio_path, output_path, effects_list, duration_ms):
    try:
        try:
            audio = AudioSegment.from_file(audio_path)
        except Exception as e:
            logging.error(f"Pydub failed to read audio: {e}")
            return False

        if "Fade In" in effects_list:
            audio = audio.fade_in(2000)
        if "Fade Out" in effects_list:
            audio = audio.fade_out(2000)
        if "Reverse" in effects_list:
            audio = audio.reverse()
        if "Echo" in effects_list:
            audio = audio + audio - 6
        if "Volume Ramp Up" in effects_list:
            audio = audio.fade(from_gain=-15.0, start=0, duration=duration_ms)
        if "Volume Ramp Down" in effects_list:
            audio = audio.fade(to_gain=-15.0, start=0, duration=duration_ms)
        if "Pitch Shift Up" in effects_list:
            audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * 1.1)}).set_frame_rate(audio.frame_rate)
        if "Pitch Shift Down" in effects_list:
            audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * 0.9)}).set_frame_rate(audio.frame_rate)

        audio = audio[:duration_ms]
        audio.export(output_path, format="mp3")
        return os.path.exists(output_path)

    except Exception as e:
        logging.error(f"Audio processing failed: {str(e)}")
        return False

def add_music_to_video(video_path, scene_assignments, output_path):
    try:
        video = VideoFileClip(video_path)
        audio_clips = []

        for idx, assignment in sorted(scene_assignments.items()):
            start = assignment["start_time"]
            end = assignment["end_time"]
            duration = int((end - start) * 1000)
            track = assignment["track"]
            effects = assignment.get("effects", [])

            raw_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
            processed_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

            success = False
            if track["source"] == "youtube":
                success = download_youtube_audio(track["audio_url"], raw_path)
                if not success:
                    logging.warning(f"Skipping scene {idx+1}: failed to download {track['name']}")
                    continue
            elif track["source"] == "local":
                try:
                    local_audio = AudioSegment.from_file(track["path"])
                    local_audio.export(raw_path, format="mp3")
                    success = True
                except Exception as e:
                    logging.warning(f"Skipping scene {idx+1}: failed to re-encode local audio: {e}")
                    continue

            if not success:
                continue

            effect_success = apply_audio_effects(raw_path, processed_path, effects, duration)
            if not effect_success:
                logging.warning(f"Skipping scene {idx+1}: failed to apply effects to {track['name']}")
                continue

            try:
                audio_clip = AudioFileClip(processed_path).set_start(start)
                audio_clips.append(audio_clip)
            except Exception as e:
                logging.warning(f"Skipping scene {idx+1}: MoviePy couldn't load audio - {str(e)}")

        if not audio_clips:
            logging.error("No audio clips were successfully created.")
            return False

        final_audio = CompositeAudioClip(audio_clips)
        final_video = video.set_audio(final_audio)
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        return True

    except Exception as e:
        logging.error(f"Rendering failed: {str(e)}")
        return False
