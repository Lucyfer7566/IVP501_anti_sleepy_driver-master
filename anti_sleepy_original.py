from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple
import math
import time

import cv2
import mediapipe as mp
import numpy as np

Point = Tuple[int, int]
BBox = Tuple[int, int, int, int]


@dataclass
class DetectorConfig:
    ear_thresh: float = 0.20
    ear_consec_frames: int = 25
    mar_thresh: float = 0.45
    pitch_drop_thresh: float = 20.0
    max_num_faces: int = 4
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    camera_scan_limit: int = 5
    frame_width: int = 640
    frame_height: int = 480
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: Tuple[int, int] = (8, 8)
    bbox_padding: int = 10
    driver_zone_ratio: float = 0.5


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
        self.base_pitch: Optional[float] = None
        self.last_metrics = {}
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
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            raise RuntimeError("solvePnP failed")

        rmat, _ = cv2.Rodrigues(rotation_vec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        pitch, yaw, roll = (float(angles[0]), float(angles[1]), float(angles[2]))
        _ = translation_vec
        return pitch, yaw, roll

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

            faces.append(
                {
                    "landmarks": landmarks,
                    "bbox": (x_min, y_min, x_max, y_max),
                    "area": area,
                    "center_x": center_x,
                }
            )

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

    def _evaluate_state(self, avg_ear: float, mar: float, pitch: float) -> Tuple[str, Tuple[int, int, int], bool]:
        status_text = "TINH TAO (AWAKE)"
        alert_color = (0, 255, 0)
        is_alert = False

        if avg_ear < self.config.ear_thresh:
            self.sleep_frame_counter += 1
        else:
            self.sleep_frame_counter = 0

        if self.sleep_frame_counter >= self.config.ear_consec_frames:
            status_text = "NGU GAT! (DROWSY)"
            alert_color = (0, 0, 255)
            is_alert = True

        if mar > self.config.mar_thresh:
            status_text = "DANG NGAP (YAWNING)"
            alert_color = (0, 165, 255)
            is_alert = True

        if self.base_pitch is not None:
            pitch_delta = self.base_pitch - pitch
            if pitch_delta >= self.config.pitch_drop_thresh:
                status_text = "GAT GU (NODDING)"
                alert_color = (0, 0, 255)
                is_alert = True
        return status_text, alert_color, is_alert

    def process_frame(self, frame: np.ndarray, do_calibrate: bool = False) -> np.ndarray:
        h, w = frame.shape[:2]
        rgb_frame = self.preprocess_image(frame)
        results = self.face_mesh.process(rgb_frame)

        status_text = "TINH TAO (AWAKE)"
        alert_color = (0, 255, 0)
        is_alert = False

        cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 255), 1)
        cv2.putText(frame, "DRIVER ZONE", (10, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        faces = self._extract_faces(results, w, h)
        driver_index = self._choose_driver_index(faces, w)

        if driver_index == -1:
            self.sleep_frame_counter = 0
            cv2.putText(frame, "KHONG TIM THAY KHUON MAT", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            return frame

        for index, face in enumerate(faces):
            x_min, y_min, x_max, y_max = face["bbox"]
            landmarks = face["landmarks"]

            if index != driver_index:
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 255), 2)
                cv2.putText(frame, "PASSENGER", (x_min, max(20, y_min - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                continue

            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.putText(frame, "DRIVER", (x_min, max(20, y_min - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            right_ear = self.get_ear(landmarks, self.RIGHT_EYE_IDX)
            left_ear = self.get_ear(landmarks, self.LEFT_EYE_IDX)
            avg_ear = (right_ear + left_ear) / 2.0
            mar = self.get_mar(landmarks)

            try:
                pitch, yaw, roll = self.get_head_pose(landmarks, w, h)
            except Exception:
                pitch, yaw, roll = 0.0, 0.0, 0.0

            if do_calibrate:
                self.base_pitch = pitch
                print(f"Da bat & hieu chuan goc Pitch thanh cong: {self.base_pitch:.2f} do")

            status_text, alert_color, is_alert = self._evaluate_state(avg_ear, mar, pitch)

            self.last_metrics = {
                "ear": avg_ear,
                "mar": mar,
                "pitch": pitch,
                "yaw": yaw,
                "roll": roll,
                "base_pitch": self.base_pitch,
            }

            cv2.putText(frame, f"EAR: {avg_ear:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"MAR: {mar:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"PITCH: {pitch:.1f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            if self.base_pitch is None:
                cv2.putText(frame, "NHAN 'C' DE HIEU CHUAN GOC DAU", (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                base_str = "CHUA BAT"
            else:
                base_str = f"{self.base_pitch:.1f}"

            cv2.putText(frame, f"BASE PITCH: {base_str}", (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
            cv2.putText(frame, f"STATUS: {status_text}", (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.0, alert_color, 3)
            break

        if is_alert:
            cv2.rectangle(frame, (0, 0), (w, h), alert_color, 10)
        return frame

    def close(self) -> None:
        self.face_mesh.close()


def select_camera(scan_limit: int = 5) -> Optional[int]:
    print("=======================================")
    print("Dang quet cac camera kha dung tren may...")
    print("=======================================")

    available_cameras: List[int] = []
    for i in range(scan_limit):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                available_cameras.append(i)
        cap.release()

    if not available_cameras:
        print("Khong tim thay camera hoat dong!")
        return None

    print("\nDanh sach camera kha dung:")
    for cam_idx in available_cameras:
        print(f"  [{cam_idx}] Camera ID {cam_idx}")

    if len(available_cameras) == 1:
        selected = available_cameras[0]
        print(f"\nTu dong chon camera duy nhat: {selected}")
        return selected

    while True:
        try:
            choice = int(input("\nNhap ID camera ban muon dung: "))
            if choice in available_cameras:
                return choice
            print("ID khong hop le. Vui long chon lai.")
        except ValueError:
            print("Vui long nhap mot so nguyen.")


def main() -> None:
    config = DetectorConfig()
    camera_index = select_camera(config.camera_scan_limit)
    if camera_index is None:
        return

    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.frame_height)

    if not cap.isOpened():
        print(f"Khong the mo camera ID {camera_index}")
        return

    detector = DrowsinessDetector(config)
    calibrate_flag = False
    last_calibration_feedback = 0.0

    print("\n=== HUONG DAN SU DUNG ===")
    print("- Nhan 'c' de hieu chuan / tat goc dau chuan")
    print("- Nhan 'q' de thoat")

    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("Khong doc duoc frame tu camera.")
                break

            frame = cv2.flip(frame, 1)
            processed_frame = detector.process_frame(frame, do_calibrate=calibrate_flag)

            if calibrate_flag:
                last_calibration_feedback = time.time()
                calibrate_flag = False

            if detector.base_pitch is not None and (time.time() - last_calibration_feedback) < 1.5:
                cv2.putText(processed_frame, "DA HIEU CHUAN THANH CONG", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("Anti Sleepy Driver - Optimized", processed_frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            if key == ord('c'):
                if detector.base_pitch is None:
                    calibrate_flag = True
                else:
                    detector.base_pitch = None
                    detector.sleep_frame_counter = 0
                    print("Da tat hieu chuan goc dau.")
    finally:
        detector.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()