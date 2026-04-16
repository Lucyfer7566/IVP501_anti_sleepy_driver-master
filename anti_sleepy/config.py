from dataclasses import dataclass
from typing import Tuple
from enum import Enum

class DriverState(Enum):
    NORMAL = 0
    DISTRACTED = 1
    HEAD_DOWN_CANDIDATE = 2
    YAWN_CANDIDATE = 3
    DROWSINESS_SUSPECTED = 4
    DROWSINESS_CONFIRMED = 5

class AlertLevel(Enum):
    NONE = 0
    EARLY_WARNING = 1
    HIGH_RISK = 2

@dataclass
class DetectorConfig:
    # Original Base Parameters
    ear_thresh: float = 0.20
    ear_consec_frames: int = 30 # 1.0s hard rule = Instant 100 Risk
    ear_recovery_frames: int = 15
    mar_thresh: float = 0.60
    mar_consec_frames: int = 30 # 1.0s to detect yawn
    mar_recovery_frames: int = 3
    pitch_drop_thresh: float = 30.0
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

    # New Risk and State machine parameters
    perclos_window_frames: int = 90
    perclos_thresh: float = 0.30          # 30% closure over ~3 seconds (normal blinking is ~15%)
    
    risk_max: float = 100.0
    risk_decay_rate: float = 1.0           # Decay per frame (always active)
    risk_suspected_thresh: float = 50.0   # Enters EARLY_WARNING
    risk_confirmed_thresh: float = 85.0   # Enters HIGH_RISK
    
    risk_penalty_blink_long: float = 25.0 # For brief abnormal closure
    risk_penalty_nodding: float = 30.0    # Pitch drop + centered yaw
    risk_penalty_yawn: float = 25.0       
    risk_penalty_perclos: float = 2.0     # Applied per frame if PERCLOS is high (must exceed decay_rate)
    
    yaw_distraction_thresh: float = 30.0  # Angle threshold for left/right looking
    abnormal_blink_frames: int = 15       # ~500ms closure (microsleep indication)

