from dataclasses import dataclass
from typing import Tuple

@dataclass
class DetectorConfig:
    ear_thresh: float = 0.20
    ear_consec_frames: int = 45
    ear_recovery_frames: int = 15
    mar_thresh: float = 0.45
    mar_consec_frames: int = 15
    mar_recovery_frames: int = 10
    pitch_drop_thresh: float = 20.0
    max_num_faces: int = 4
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    camera_scan_limit: int = 5
    frame_width: int = 960
    frame_height: int = 720
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: Tuple[int, int] = (8, 8)
    bbox_padding: int = 10
    driver_zone_ratio: float = 0.5
