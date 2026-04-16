import os
import sys
import time
from typing import Optional, List

import cv2

# Add the project root to sys.path so we can run this file directly via "python anti_sleepy/main.py"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from anti_sleepy.config import DetectorConfig
from anti_sleepy.core.detector import DrowsinessDetector

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
    
    print("\n=== KHOI DONG HE THONG GIAO DIEN ===")
    
    import tkinter as tk
    from anti_sleepy.ui.app import AntiSleepyApp

    root = tk.Tk()
    app = AntiSleepyApp(root, cap, detector)
    
    try:
        root.mainloop()
    except Exception as e:
        print(f"Loi giao dien: {e}")
        detector.close()
        cap.release()


if __name__ == "__main__":
    main()
