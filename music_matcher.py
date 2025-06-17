import os
import logging
import json
from collections import Counter
from dotenv import load_dotenv
from googleapiclient.discovery import build
import yt_dlp

load_dotenv()
logging.basicConfig(filename="debug.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
SELECTIONS_FILE = "user_selections.json"

def search_youtube_tracks(mood_query, max_results=5):
    try:
        request = YOUTUBE.search().list(
            part="snippet",
            maxResults=max_results,
            q=f"{mood_query} music",
            type="video",
            videoCategoryId="10"
        )
        response = request.execute()
        tracks = []

        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            artist = item["snippet"]["channelTitle"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            tracks.append({
                "name": title,
                "artist": artist,
                "url": url,
                "audio_url": url,
                "source": "youtube"
            })

        return tracks
    except Exception as e:
        logging.error(f"YouTube API search failed: {str(e)}")
        return []

def download_youtube_audio(youtube_url, output_path):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'quiet': True,
            'nocheckcertificate': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'postprocessor_args': [
                '-fflags', '+genpts',
                '-loglevel', 'error'
            ]
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        return os.path.exists(output_path)
    except Exception as e:
        logging.error(f"yt_dlp failed to download or extract audio: {e}")
        return False

def log_user_selection(mood, track):
    try:
        if os.path.exists(SELECTIONS_FILE):
            with open(SELECTIONS_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"mood_history": {}}

        mood_history = data.get("mood_history", {})
        mood_history.setdefault(mood, [])
        mood_history[mood].append(track["name"])
        data["mood_history"] = mood_history

        with open(SELECTIONS_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to log user selection: {str(e)}")

def get_preferred_track_name(mood):
    try:
        if not os.path.exists(SELECTIONS_FILE):
            return None
        with open(SELECTIONS_FILE, "r") as f:
            data = json.load(f)
        mood_list = data.get("mood_history", {}).get(mood, [])
        if not mood_list:
            return None
        most_common = Counter(mood_list).most_common(1)
        return most_common[0][0] if most_common else None
    except Exception as e:
        logging.error(f"Failed to get preferred track: {str(e)}")
        return None
