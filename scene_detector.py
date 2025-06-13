from scenedetect import detect, ContentDetector

def split_video(video_path):
    scene_list = detect(video_path, ContentDetector())
    return [(start.get_seconds(), end.get_seconds()) for (start, end) in scene_list]