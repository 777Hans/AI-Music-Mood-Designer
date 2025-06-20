# video_editor.py - Enhanced Version with Fixed Audio Effects
import os
import tempfile
import logging
import numpy as np
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
from music_matcher import download_youtube_audio

logging.basicConfig(filename="debug.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def create_echo_effect(audio_segment, delay_ms=300, decay_factor=0.5, num_echoes=3):
    """Create a proper echo effect with multiple delayed repetitions"""
    try:
        result = audio_segment
        
        for i in range(1, num_echoes + 1):
            # Create delayed version with decreasing volume
            delay = delay_ms * i
            volume_reduction = -(6 * i * decay_factor)  # Each echo gets quieter
            
            # Create silence padding
            silence = AudioSegment.silent(duration=delay)
            
            # Create echo with reduced volume
            echo = audio_segment + volume_reduction
            delayed_echo = silence + echo
            
            # Ensure both segments have the same length for overlay
            max_length = max(len(result), len(delayed_echo))
            if len(result) < max_length:
                result = result + AudioSegment.silent(duration=max_length - len(result))
            if len(delayed_echo) < max_length:
                delayed_echo = delayed_echo + AudioSegment.silent(duration=max_length - len(delayed_echo))
            
            # Overlay the echo
            result = result.overlay(delayed_echo)
        
        return result
    except Exception as e:
        logging.error(f"Echo effect failed: {e}")
        return audio_segment

def create_pitch_shift(audio_segment, shift_factor):
    """Create pitch shift effect by changing playback speed and resampling"""
    try:
        # Change the frame rate to shift pitch
        shifted = audio_segment._spawn(
            audio_segment.raw_data,
            overrides={"frame_rate": int(audio_segment.frame_rate * shift_factor)}
        )
        # Resample back to original frame rate to maintain duration
        return shifted.set_frame_rate(audio_segment.frame_rate)
    except Exception as e:
        logging.error(f"Pitch shift failed: {e}")
        return audio_segment

def create_volume_ramp(audio_segment, start_gain_db, end_gain_db, duration_ms):
    """Create smooth volume ramp effect"""
    try:
        # Create gain curve
        samples = len(audio_segment.get_array_of_samples())
        
        if audio_segment.channels == 2:
            samples = samples // 2
        
        # Create linear interpolation for gain
        gain_curve = np.linspace(start_gain_db, end_gain_db, samples)
        
        # Convert to linear scale (from dB)
        linear_curve = np.power(10, gain_curve / 20)
        
        # Apply gain curve
        audio_array = np.array(audio_segment.get_array_of_samples())
        
        if audio_segment.channels == 2:
            # Stereo
            audio_array = audio_array.reshape((-1, 2))
            audio_array = audio_array * linear_curve.reshape((-1, 1))
            audio_array = audio_array.flatten()
        else:
            # Mono
            audio_array = audio_array * linear_curve
        
        # Convert back to AudioSegment
        audio_array = audio_array.astype(np.int16)
        return audio_segment._spawn(audio_array.tobytes())
    
    except Exception as e:
        logging.error(f"Volume ramp failed: {e}")
        # Fallback to simple fade
        if start_gain_db < end_gain_db:
            return audio_segment.fade_in(duration_ms // 2)
        else:
            return audio_segment.fade_out(duration_ms // 2)

def create_reverb_effect(audio_segment, room_size=0.5, damping=0.5, wet_level=0.3):
    """Create a simple reverb effect using multiple delayed echoes"""
    try:
        # Create multiple short echoes to simulate reverb
        reverb_delays = [50, 75, 125, 150, 200, 250, 300, 375, 450]
        result = audio_segment
        
        for delay in reverb_delays:
            # Create silence padding
            silence = AudioSegment.silent(duration=delay)
            
            # Create reverb tail with reduced volume
            volume_reduction = -(10 + (delay * 0.02))  # Progressive volume reduction
            reverb_tail = (silence + audio_segment + volume_reduction)
            
            # Apply damping (high-frequency reduction)
            if damping > 0:
                # Simple high-frequency damping by reducing treble
                reverb_tail = reverb_tail.low_pass_filter(8000 - int(damping * 3000))
            
            # Ensure same length for overlay
            max_length = max(len(result), len(reverb_tail))
            if len(result) < max_length:
                result = result + AudioSegment.silent(duration=max_length - len(result))
            if len(reverb_tail) < max_length:
                reverb_tail = reverb_tail + AudioSegment.silent(duration=max_length - len(reverb_tail))
            
            # Mix reverb with original
            result = result.overlay(reverb_tail, gain_during_overlay=-(20 - int(wet_level * 10)))
        
        return result
    except Exception as e:
        logging.error(f"Reverb effect failed: {e}")
        return audio_segment

def apply_audio_effects(audio_path, output_path, effects_list, duration_ms, music_start_ms=0, music_end_ms=None):
    """Apply audio effects to a segment with proper timing controls and enhanced effects"""
    try:
        try:
            audio = AudioSegment.from_file(audio_path)
            logging.info(f"Loaded audio file: {len(audio)}ms duration, {audio.channels} channels, {audio.frame_rate}Hz")
        except Exception as e:
            logging.error(f"Pydub failed to read audio: {e}")
            return False

        # Extract the specific portion of the music track
        if music_end_ms is None:
            music_end_ms = len(audio)
        
        # Ensure we don't exceed the audio file length
        music_start_ms = min(music_start_ms, len(audio))
        music_end_ms = min(music_end_ms, len(audio))
        
        if music_start_ms >= music_end_ms:
            logging.warning(f"Invalid music timing: start {music_start_ms}ms >= end {music_end_ms}ms")
            music_start_ms = 0
            music_end_ms = min(duration_ms, len(audio))
        
        # Extract the desired portion of the music
        audio = audio[music_start_ms:music_end_ms]
        logging.info(f"Extracted audio segment: {len(audio)}ms")
        
        # If the extracted audio is shorter than needed duration, loop it
        original_length = len(audio)
        while len(audio) < duration_ms:
            audio = audio + audio
            logging.info(f"Looped audio, new length: {len(audio)}ms")
        
        # Trim to exact duration needed
        audio = audio[:duration_ms]
        logging.info(f"Final audio length: {len(audio)}ms for target: {duration_ms}ms")

        # Apply effects in optimal order
        logging.info(f"Applying effects: {effects_list}")
        
        # 1. Pitch effects first (they can change timing)
        if "Pitch Shift Up" in effects_list:
            logging.info("Applying pitch shift up")
            audio = create_pitch_shift(audio, 1.2)  # 20% higher pitch
            
        if "Pitch Shift Down" in effects_list:
            logging.info("Applying pitch shift down")
            audio = create_pitch_shift(audio, 0.8)  # 20% lower pitch

        # 2. Reverse effect
        if "Reverse" in effects_list:
            logging.info("Applying reverse effect")
            audio = audio.reverse()

        # 3. Volume effects
        if "Volume Ramp Up" in effects_list:
            logging.info("Applying volume ramp up")
            audio = create_volume_ramp(audio, -20, 0, duration_ms)
            
        if "Volume Ramp Down" in effects_list:
            logging.info("Applying volume ramp down")
            audio = create_volume_ramp(audio, 0, -20, duration_ms)

        # 4. Spatial effects (Echo, Reverb)
        if "Echo" in effects_list:
            logging.info("Applying echo effect")
            audio = create_echo_effect(audio, delay_ms=250, decay_factor=0.6, num_echoes=3)
            
        if "Reverb" in effects_list:
            logging.info("Applying reverb effect")
            audio = create_reverb_effect(audio, room_size=0.6, damping=0.4, wet_level=0.3)

        # 5. Fade effects (applied last to avoid interfering with other effects)
        if "Fade In" in effects_list:
            fade_duration = min(3000, duration_ms // 3)  # Max 3 seconds or 1/3 of duration
            logging.info(f"Applying fade in: {fade_duration}ms")
            audio = audio.fade_in(fade_duration)
            
        if "Fade Out" in effects_list:
            fade_duration = min(3000, duration_ms // 3)
            logging.info(f"Applying fade out: {fade_duration}ms")
            audio = audio.fade_out(fade_duration)

        # 6. Final processing
        try:
            # Normalize audio to prevent clipping
            audio = normalize(audio, headroom=1.0)
            
            # Apply gentle compression to even out dynamics
            audio = compress_dynamic_range(audio, threshold=-20.0, ratio=2.0)
            
            logging.info("Applied normalization and compression")
        except Exception as e:
            logging.warning(f"Failed to apply final processing: {e}")

        # Export processed audio
        logging.info(f"Exporting processed audio to: {output_path}")
        audio.export(output_path, format="mp3", bitrate="192k")
        
        success = os.path.exists(output_path)
        if success:
            file_size = os.path.getsize(output_path)
            logging.info(f"Successfully exported audio: {file_size} bytes")
        else:
            logging.error("Export failed: output file not created")
        
        return success

    except Exception as e:
        logging.error(f"Audio processing failed: {str(e)}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return False

def add_music_to_video(video_path, scene_assignments, output_path):
    """
    Add music to video based on scene assignments.
    Works with both automatic scenes and manual segments.
    """
    try:
        logging.info(f"Starting video rendering with {len(scene_assignments)} assignments")
        video = VideoFileClip(video_path)
        audio_clips = []
        
        # Keep track of successful clips for debugging
        successful_clips = 0
        temp_files = []  # Track temp files for cleanup

        for idx, assignment in sorted(scene_assignments.items()):
            start = assignment["start_time"]
            end = assignment["end_time"]
            duration_ms = int((end - start) * 1000)
            
            # Get music timing (for manual segments)
            music_start = assignment.get("music_start", 0)
            music_end = assignment.get("music_end", end - start)
            music_start_ms = int(music_start * 1000)
            music_end_ms = int(music_end * 1000)
            
            track = assignment["track"]
            effects = assignment.get("effects", [])

            logging.info(f"Processing segment {idx}: {start:.2f}s-{end:.2f}s, track: {track['name']}, effects: {effects}")

            # Create temporary files
            raw_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
            processed_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
            temp_files.extend([raw_path, processed_path])

            success = False
            
            # Handle different audio sources
            if track["source"] == "youtube":
                success = download_youtube_audio(track["audio_url"], raw_path)
                if not success:
                    logging.warning(f"Skipping segment {idx}: failed to download {track['name']}")
                    continue
            elif track["source"] == "local":
                try:
                    # Copy local file to temp location for processing
                    local_audio = AudioSegment.from_file(track["path"])
                    local_audio.export(raw_path, format="mp3", bitrate="192k")
                    success = True
                    logging.info(f"Successfully loaded local file: {track['name']}")
                except Exception as e:
                    logging.warning(f"Skipping segment {idx}: failed to process local audio: {e}")
                    continue
            else:
                logging.warning(f"Skipping segment {idx}: unknown source type: {track.get('source', 'unknown')}")
                continue

            if not success:
                logging.warning(f"Skipping segment {idx}: failed to prepare audio")
                continue

            # Apply effects and timing
            effect_success = apply_audio_effects(
                raw_path, 
                processed_path, 
                effects, 
                duration_ms,
                music_start_ms,
                music_end_ms
            )
            
            if not effect_success:
                logging.warning(f"Skipping segment {idx}: failed to apply effects to {track['name']}")
                continue

            # Create MoviePy audio clip
            try:
                audio_clip = AudioFileClip(processed_path).set_start(start).set_duration(end - start)
                audio_clips.append(audio_clip)
                successful_clips += 1
                logging.info(f"Successfully created audio clip for segment {idx}")
            except Exception as e:
                logging.warning(f"Skipping segment {idx}: MoviePy couldn't load audio - {str(e)}")
                continue

        logging.info(f"Created {successful_clips} successful audio clips out of {len(scene_assignments)} assignments")

        if not audio_clips:
            logging.error("No audio clips were successfully created.")
            return False

        # Combine all audio clips
        try:
            if len(audio_clips) == 1:
                final_audio = audio_clips[0]
            else:
                final_audio = CompositeAudioClip(audio_clips)
            
            # Create final video with music
            # Keep original video audio and mix with new music
            if video.audio is not None:
                # Mix original audio with music (reduce original volume)
                original_audio = video.audio.volumex(0.3)  # Reduce original to 30%
                final_audio = CompositeAudioClip([original_audio, final_audio.volumex(0.8)])
            
            final_video = video.set_audio(final_audio)
            
            # Write the final video with optimized settings
            logging.info(f"Writing final video to: {output_path}")
            final_video.write_videofile(
                output_path, 
                codec="libx264", 
                audio_codec="aac",
                temp_audiofile=tempfile.NamedTemporaryFile(delete=False, suffix=".m4a").name,
                remove_temp=True,
                verbose=False,
                logger=None  # Reduce verbose output
            )
            
            # Clean up MoviePy objects
            final_video.close()
            final_audio.close()
            for clip in audio_clips:
                clip.close()
            video.close()
            
            logging.info("Video rendering completed successfully")
            return True

        except Exception as e:
            logging.error(f"Failed to create final video: {str(e)}")
            import traceback
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return False

    except Exception as e:
        logging.error(f"Video rendering failed: {str(e)}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return False
    finally:
        # Clean up temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logging.warning(f"Failed to clean up temp file {temp_file}: {e}")
        
        # Additional cleanup for any remaining temp files
        try:
            temp_dir = tempfile.gettempdir()
            for temp_file in os.listdir(temp_dir):
                if temp_file.startswith("tmp") and (temp_file.endswith(".mp3") or temp_file.endswith(".m4a")):
                    try:
                        full_path = os.path.join(temp_dir, temp_file)
                        # Only delete files older than 1 hour to avoid conflicts
                        if os.path.getctime(full_path) < (time.time() - 3600):
                            os.unlink(full_path)
                    except:
                        pass
        except:
            pass