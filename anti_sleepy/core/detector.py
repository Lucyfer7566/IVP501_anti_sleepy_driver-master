import math
from typing import List, Optional, Sequence, Tuple, Dict, Any

import cv2
import mediapipe as mp
import numpy as np
import collections

from ..config import DetectorConfig, DriverState, AlertLevel

Point = Tuple[int, int]
BBox = Tuple[int, int, int, int]

# Eye contour indices
RIGHT_EYE_CONTOUR = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
LEFT_EYE_CONTOUR = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_IRIS = [468, 469, 470, 471, 472]
LEFT_IRIS = [473, 474, 475, 476, 477]

# Face oval contour (jawline + forehead outline)
FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109
]

# Nose bridge + tip
NOSE_BRIDGE = [168, 6, 197, 195, 5, 4]

# Outer lips
LIPS_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]

class DrowsinessDetector:
    RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]
    LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
    MOUTH_IDX = [78, 308, 13, 14]
    HEAD_POSE_IDX = [1, 152, 226, 446, 57, 287]

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        self.config = config or DetectorConfig()
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=self.config.max_num_faces,
            refine_landmarks=True,
            min_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
        )

        self.sleep_frame_counter = 0
        self.yawn_frame_counter = 0
        self.sleep_recovery_counter = 0
        self.yawn_recovery_counter = 0
        self._is_drowsy = False
        self._is_yawning = False
        self.base_pitch: Optional[float] = None
        self.base_yaw: float = 0.0
        self._ear_history = collections.deque(maxlen=60)
        
        # New State Machine and Risk Handling
        self.risk_score = 0.0
        self.current_state = DriverState.NORMAL
        self._perclos_buffer = collections.deque(maxlen=self.config.perclos_window_frames if hasattr(self.config, 'perclos_window_frames') else 90)
        self.blink_duration = 0
        self.nod_duration = 0

        self.last_metrics: Dict[str, Any] = {}
        self.clahe = cv2.createCLAHE(
            clipLimit=self.config.clahe_clip_limit,
            tileGridSize=self.config.clahe_tile_grid_size,
        )

        self.model_points = np.array(
            [
                (0.0, 0.0, 0.0),
                (0.0, -330.0, -65.0),
                (-225.0, 170.0, -135.0),
                (225.0, 170.0, -135.0),
                (-150.0, -150.0, -125.0),
                (150.0, -150.0, -125.0),
            ],
            dtype=np.float64,
        )
        
        self.sunglasses_mode = False

    def preprocess_image(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe_gray = self.clahe.apply(gray)
        return cv2.cvtColor(clahe_gray, cv2.COLOR_GRAY2RGB)

    @staticmethod
    def euclidean_distance(p1: Point, p2: Point) -> float:
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def get_ear(self, landmarks: Sequence[Point], indices: Sequence[int]) -> float:
        p1, p2, p3 = landmarks[indices[0]], landmarks[indices[1]], landmarks[indices[2]]
        p4, p5, p6 = landmarks[indices[3]], landmarks[indices[4]], landmarks[indices[5]]
        dist_vert1 = self.euclidean_distance(p2, p6)
        dist_vert2 = self.euclidean_distance(p3, p5)
        dist_horz = self.euclidean_distance(p1, p4)
        if dist_horz <= 1e-6:
            return 0.0
        return (dist_vert1 + dist_vert2) / (2.0 * dist_horz)

    def get_mar(self, landmarks: Sequence[Point]) -> float:
        left_mouth, right_mouth = landmarks[self.MOUTH_IDX[0]], landmarks[self.MOUTH_IDX[1]]
        top_mouth, bottom_mouth = landmarks[self.MOUTH_IDX[2]], landmarks[self.MOUTH_IDX[3]]
        dist_vert = self.euclidean_distance(top_mouth, bottom_mouth)
        dist_horz = self.euclidean_distance(left_mouth, right_mouth)
        if dist_horz <= 1e-6:
            return 0.0
        return dist_vert / dist_horz

    def get_head_pose(self, landmarks: Sequence[Point], frame_width: int, frame_height: int) -> Tuple[float, float, float]:
        image_points = np.array([landmarks[i] for i in self.HEAD_POSE_IDX], dtype=np.float64)
        focal_length = frame_width
        center = (frame_width / 2.0, frame_height / 2.0)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]],
            dtype=np.float64,
        )
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        success, rotation_vec, translation_vec = cv2.solvePnP(
            self.model_points, image_points, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            raise RuntimeError("solvePnP failed")
        rmat, _ = cv2.Rodrigues(rotation_vec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        return float(angles[0]), float(angles[1]), float(angles[2])

    def _extract_faces(self, results, width: int, height: int) -> List[dict]:
        faces: List[dict] = []
        if not results.multi_face_landmarks:
            return faces
        for face_landmarks in results.multi_face_landmarks:
            landmarks: List[Point] = []
            x_coords: List[int] = []
            y_coords: List[int] = []
            for lm in face_landmarks.landmark:
                x = int(lm.x * width)
                y = int(lm.y * height)
                landmarks.append((x, y))
                x_coords.append(x)
                y_coords.append(y)
            x_min = max(0, min(x_coords) - self.config.bbox_padding)
            y_min = max(0, min(y_coords) - self.config.bbox_padding)
            x_max = min(width, max(x_coords) + self.config.bbox_padding)
            y_max = min(height, max(y_coords) + self.config.bbox_padding)
            area = max(0, x_max - x_min) * max(0, y_max - y_min)
            center_x = (x_min + x_max) / 2.0
            faces.append({
                "landmarks": landmarks,
                "bbox": (x_min, y_min, x_max, y_max),
                "area": area,
                "center_x": center_x,
            })
        faces.sort(key=lambda item: item["area"], reverse=True)
        return faces

    def _choose_driver_index(self, faces: List[dict], frame_width: int) -> int:
        if not faces:
            return -1
        driver_zone_x = frame_width * self.config.driver_zone_ratio
        for idx, face in enumerate(faces):
            if face["center_x"] < driver_zone_x:
                return idx
        return 0

    def _draw_face_mesh(self, frame: np.ndarray, landmarks: List[Point], is_alert: bool) -> None:
        """Draw face contours: oval, eyes, nose, lips, iris."""
        eye_color = (0, 0, 255) if is_alert else (0, 255, 0)
        mesh_color = (0, 0, 200) if is_alert else (0, 200, 0)
        
        n = len(landmarks)
        
        # Face oval (jawline + forehead)
        if n > max(FACE_OVAL):
            pts = np.array([landmarks[i] for i in FACE_OVAL], dtype=np.int32)
            cv2.polylines(frame, [pts], isClosed=True, color=mesh_color, thickness=1)
        
        # Eyes
        for contour in [RIGHT_EYE_CONTOUR, LEFT_EYE_CONTOUR]:
            if n > max(contour):
                pts = np.array([landmarks[i] for i in contour], dtype=np.int32)
                cv2.polylines(frame, [pts], isClosed=True, color=eye_color, thickness=1)
        
        # Nose bridge
        if n > max(NOSE_BRIDGE):
            pts = np.array([landmarks[i] for i in NOSE_BRIDGE], dtype=np.int32)
            cv2.polylines(frame, [pts], isClosed=False, color=mesh_color, thickness=1)
        
        # Lips
        if n > max(LIPS_OUTER):
            pts = np.array([landmarks[i] for i in LIPS_OUTER], dtype=np.int32)
            cv2.polylines(frame, [pts], isClosed=True, color=mesh_color, thickness=1)
        
        # Iris
        if n > 477:
            for iris_indices in [RIGHT_IRIS, LEFT_IRIS]:
                center = landmarks[iris_indices[0]]
                radius_pts = [landmarks[i] for i in iris_indices[1:]]
                radius = int(np.mean([self.euclidean_distance(center, p) for p in radius_pts]))
                cv2.circle(frame, center, radius, (255, 255, 0), 1)
                cv2.circle(frame, center, 2, (0, 255, 255), -1)

    def _evaluate_state(self, avg_ear: float, mar: float, pitch: float, yaw: float) -> Tuple[str, Tuple[int, int, int], bool, str, int]:
        status_text = "TINH TAO (AWAKE)"
        alert_color = (0, 255, 0)
        is_alert = False
        alert_sound = ""
        alert_level = AlertLevel.NONE.value

        # Auto-detect sunglasses
        if len(self._ear_history) == self._ear_history.maxlen:
            ear_max = max(self._ear_history)
            ear_min = min(self._ear_history)
            ear_mean = sum(self._ear_history) / len(self._ear_history)
            if (ear_max - ear_min < 0.04) and (0.09 < ear_mean < 0.18):
                self.sunglasses_mode = True
            elif ear_mean > 0.22:
                self.sunglasses_mode = False
                
            # Self-calibrating dynamic EAR threshold (60% of relaxed open eyes)
            if not self.sunglasses_mode:
                if not hasattr(self, 'dynamic_ear_open'):
                    self.dynamic_ear_open = ear_max
                elif ear_max > self.dynamic_ear_open:
                    self.dynamic_ear_open = ear_max # jump up immediately
                else:
                    self.dynamic_ear_open = self.dynamic_ear_open * 0.995 + ear_max * 0.005 # adapt slowly
                self.config.ear_thresh = max(0.12, self.dynamic_ear_open * 0.60)

        # Evidence tracking
        eyes_closed = avg_ear < self.config.ear_thresh if not self.sunglasses_mode else False
        yawning = mar > self.config.mar_thresh
        
        # PERCLOS tracking (Ignore squinting during yawning)
        eyes_for_perclos = eyes_closed and not yawning
        self._perclos_buffer.append(1 if eyes_for_perclos else 0)
        perclos_ready = len(self._perclos_buffer) == (self.config.perclos_window_frames if hasattr(self.config, 'perclos_window_frames') else 90)
        perclos = sum(self._perclos_buffer) / len(self._perclos_buffer) if perclos_ready else 0.0
        
        nodding = False
        distracted = False
        
        self.debug_flags = f"E:{int(eyes_closed)} Y:{int(yawning)} Th:{self.config.ear_thresh:.2f}"
        
        if self.base_pitch is not None:
            # Short-term pitch (moving avg of last few frames) vs long-term base_pitch
            if not hasattr(self, 'short_pitch'):
                self.short_pitch = pitch
            self.short_pitch = self.short_pitch * 0.5 + pitch * 0.5
            
            pitch_delta = self.base_pitch - self.short_pitch
            yaw_delta = abs(self.base_yaw - yaw if hasattr(self, 'base_yaw') else yaw)
            
            # Veto False Microsleeps on extreme head pitch up or yaw
            if pitch_delta < -25.0 or yaw_delta > 30.0:
                eyes_closed = False  # Overrule EAR, view is geometrically squashed
                eyes_for_perclos = False # Also exclude from PERCLOS

            # Smoothen Head Movement: Ignore pitch drop if looking far away (yaw > thresh)
            if yaw_delta > self.config.yaw_distraction_thresh:
                distracted = True
            elif pitch_delta >= self.config.pitch_drop_thresh:
                nodding = True
                
        self.debug_flags += f" N:{int(nodding)}"

        # Temporal Eye Logic (Blink duration vs True closure)
        # Suppress eye closure penalties if the driver is actively yawning (natural squint)
        if eyes_closed and not yawning:
            self.blink_duration += 1
            if self.blink_duration == self.config.abnormal_blink_frames:
                # Add penalty once per long blink
                self.risk_score += self.config.risk_penalty_blink_long
        else:
            self.blink_duration = 0
            
        # Hard Rule fallback
        if self.blink_duration >= self.config.ear_consec_frames:
            self.risk_score = self.config.risk_max
            
        # Yawn logic with hysteresis
        if yawning:
            self.yawn_frame_counter += 1
            self.yawn_recovery_counter = 0
            if self.yawn_frame_counter == self.config.mar_consec_frames:
                self.risk_score += self.config.risk_penalty_yawn
        else:
            self.yawn_recovery_counter += 1
            if self.yawn_recovery_counter >= self.config.mar_recovery_frames:
                self.yawn_frame_counter = 0

        # Nodding Risk (Only penalize if eyes are closed/drowsy)
        # Avoid penalizing sudden braking or looking down at dash with wide-open eyes.
        perclos_ready = len(self._perclos_buffer) == (self.config.perclos_window_frames if hasattr(self.config, 'perclos_window_frames') else 90)
        perclos = sum(self._perclos_buffer) / len(self._perclos_buffer) if perclos_ready else 0.0
        
        if nodding and (eyes_closed or perclos > 0.10):
            self.nod_duration += 1
            if self.nod_duration == 15: # Trigger penalty once after half-second
                self.risk_score += self.config.risk_penalty_nodding
        else:
            self.nod_duration = 0
            
        # PERCLOS Risk (only penalize sustained drowsy closure, not normal blinks)
        if perclos > self.config.perclos_thresh:
            self.risk_score += self.config.risk_penalty_perclos
            
        # Continuous Posture Adaptation
        if self.base_pitch is not None:
            # Continually adapt base posture so it never gets permanently stuck
            self.base_pitch = self.base_pitch * 0.995 + pitch * 0.005
            if hasattr(self, 'base_yaw'):
                self.base_yaw = self.base_yaw * 0.995 + yaw * 0.005
                
        # Risk Decay — ALWAYS active so risk naturally drains back to zero
        # Penalties outpace decay only when truly drowsy (sustained closure/yawning)
        self.risk_score -= self.config.risk_decay_rate
            
        # Clamp Risk Score
        self.risk_score = max(0.0, min(self.config.risk_max, self.risk_score))
        
        # State Machine Transitions
        new_state = DriverState.NORMAL
        
        if self.risk_score >= self.config.risk_confirmed_thresh:
            new_state = DriverState.DROWSINESS_CONFIRMED
        elif self.risk_score >= self.config.risk_suspected_thresh:
            new_state = DriverState.DROWSINESS_SUSPECTED
        elif self.yawn_frame_counter >= self.config.mar_consec_frames * 0.8:
            new_state = DriverState.YAWN_CANDIDATE
        elif nodding:
            new_state = DriverState.HEAD_DOWN_CANDIDATE
        elif distracted:
            new_state = DriverState.DISTRACTED
            
        self.current_state = new_state
        
        # Alert mapping
        if new_state == DriverState.DROWSINESS_CONFIRMED:
            status_text = "NGU GAT! (CONFIRMED)"
            alert_color = (0, 0, 255) # Red
            is_alert = True
            alert_level = AlertLevel.HIGH_RISK.value
            alert_sound = "alert_drowsy.wav"
        elif new_state == DriverState.DROWSINESS_SUSPECTED:
            status_text = "DANG BUON NGU (SUSPECTED)"
            alert_color = (0, 165, 255) # Orange
            is_alert = True
            alert_level = AlertLevel.EARLY_WARNING.value
            # Removed the annoying short beep ("sys_unknown_driver.wav") for suspected state
        elif new_state == DriverState.YAWN_CANDIDATE:
            status_text = "DANG NGAP (YAWNING)"
            alert_color = (0, 255, 255) # Yellow
            is_alert = True
            alert_level = AlertLevel.EARLY_WARNING.value
            alert_sound = "alert_yawning.wav"
        elif new_state == DriverState.HEAD_DOWN_CANDIDATE:
            status_text = "GAT GU (NODDING)"
            alert_color = (255, 0, 0)
        elif new_state == DriverState.DISTRACTED:
            status_text = "XAO LANG (DISTRACTED)"
            alert_color = (255, 255, 0) # Cyan

        return status_text, alert_color, is_alert, alert_sound, alert_level

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        rgb_frame = self.preprocess_image(frame)
        results = self.face_mesh.process(rgb_frame)

        is_alert = False

        cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 255), 1)

        faces = self._extract_faces(results, w, h)
        driver_index = self._choose_driver_index(faces, w)

        if driver_index == -1:
            self.sleep_frame_counter = 0
            self.sleep_recovery_counter = 0
            self._is_drowsy = False
            self.last_metrics = {"is_alert": False, "landmarks": []}
            return frame

        for index, face in enumerate(faces):
            x_min, y_min, x_max, y_max = face["bbox"]
            landmarks = face["landmarks"]

            if index != driver_index:
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 255), 1)
                cv2.putText(frame, "HANH KHACH", (x_min, max(15, y_min - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                continue

            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.putText(frame, "TAI XE", (x_min, max(15, y_min - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            right_ear = self.get_ear(landmarks, self.RIGHT_EYE_IDX)
            left_ear = self.get_ear(landmarks, self.LEFT_EYE_IDX)
            avg_ear = (right_ear + left_ear) / 2.0
            mar = self.get_mar(landmarks)

            try:
                pitch, yaw, roll = self.get_head_pose(landmarks, w, h)
            except Exception:
                pitch, yaw, roll = 0.0, 0.0, 0.0

            self._ear_history.append(avg_ear)
            
            # Auto-calibrate head pose after calibration window fills
            if self.base_pitch is None and len(self._ear_history) == self._ear_history.maxlen:
                self.base_pitch = pitch
                self.base_yaw = yaw
                
            status_text, alert_color, is_alert, alert_sound, alert_level = self._evaluate_state(avg_ear, mar, pitch, yaw)

            # Draw full face mesh contours
            self._draw_face_mesh(frame, landmarks, is_alert)

            self.last_metrics = {
                "ear": avg_ear,
                "mar": mar,
                "pitch": pitch,
                "yaw": yaw,
                "roll": roll,
                "base_pitch": self.base_pitch,
                "landmarks": landmarks,
                "bbox": (x_min, y_min, x_max, y_max),
                "is_alert": is_alert,
                "alert_level": alert_level,
                "status": status_text,
                "sound": alert_sound
            }

            # Minimal OSD on camera feed
            cv2.putText(frame, f"EAR:{avg_ear:.2f} MAR:{mar:.2f}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"STATUS: {status_text} | RISK: {self.risk_score:.0f}/100", (10, h - 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, alert_color, 2)
            if hasattr(self, 'debug_flags'):
                cv2.putText(frame, f"DEBUG: {self.debug_flags}", (10, h - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            if self.sunglasses_mode:
                cv2.putText(frame, "SUNGLASSES", (w - 160, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            break

        if is_alert:
            cv2.rectangle(frame, (0, 0), (w, h), alert_color, 8)
        return frame

    def close(self) -> None:
        self.face_mesh.close()
