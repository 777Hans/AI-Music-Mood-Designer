from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

def split_video(video_path, threshold=30.0, min_scene_len=15):
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len))

    base_timecode = video_manager.get_base_timecode()
    video_manager.set_downscale_factor()
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    scene_list = scene_manager.get_scene_list(base_timecode)
    return [(scene[0].get_seconds(), scene[1].get_seconds()) for scene in scene_list]
