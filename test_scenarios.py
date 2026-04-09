import os
import sys
import json
import time

sys.path.insert(0, r"d:\IVP501_anti_sleepy_driver-master")

import tkinter as tk
import numpy as np
import cv2

# Mock messagebox and face_id before application imports
import tkinter.messagebox
tkinter.messagebox.showinfo = lambda title, message: None
tkinter.messagebox.askyesno = lambda title, message: True

import anti_sleepy.core.face_id
anti_sleepy.core.face_id.extract_face_signature = lambda l: [0.5] * 15

from anti_sleepy.core.profile import delete_profile
from anti_sleepy.ui.app import AntiSleepyApp
from anti_sleepy.core.detector import DrowsinessDetector
from anti_sleepy.ui.led_widget import LEDState
from anti_sleepy.config import DetectorConfig
import anti_sleepy.ui.register_flow as reg_mod

class DummyCap:
    def read(self):
        return True, np.zeros((480, 640, 3), dtype=np.uint8)
    def isOpened(self): return True
    def release(self): pass

def mock_extract_faces(self, results, w, h):
    landmarks = [(100, 100)] * 468
    landmarks[226] = (100, 100)
    landmarks[446] = (200, 100)
    return [{
        "landmarks": landmarks,
        "bbox": (50, 50, 250, 250),
        "area": 40000,
        "center_x": 150
    }]
DrowsinessDetector._extract_faces = mock_extract_faces
DrowsinessDetector.get_ear = lambda self, l, idx: 0.35
DrowsinessDetector.get_mar = lambda self, l: 0.0
DrowsinessDetector.get_head_pose = lambda self, l, w, h: (0.0, 0.0, 0.0)

delete_profile()

root = tk.Tk()
root.mock_mode = True
cap = DummyCap()
config = DetectorConfig()
detector = DrowsinessDetector(config)
app = AntiSleepyApp(root, cap, detector)

issues = []

print("\n--- SCENARIO 1: FIRST LAUNCH ---")
app._update()
root.update()
owner_txt = app.lbl_owner_status.cget("text")
print("Owner state:", owner_txt)
print("LED State:", app.led.state.name)
if owner_txt != "Owner: CHƯA ĐĂNG KÝ": issues.append("Scenario 1 Owner Text Failed")
if app.led.state != LEDState.OFF: issues.append("Scenario 1 LED Failed")

print("\n--- SCENARIO 2: REGISTRATION FLOW ---")
app.start_registration()

orig_time = time.time
current_mock_time = orig_time()
def mock_time(): return current_mock_time
reg_mod.time.time = mock_time
time.time = mock_time

print("Phase Start:", app.reg_flow.phase.name)

def advance_time(seconds):
    global current_mock_time
    # Advance in tiny 0.1 increments to trigger phase changes
    steps = int(seconds / 0.1)
    for _ in range(steps):
        current_mock_time += 0.1
        app._update()
        root.update()

advance_time(0.5)
print("LED 1 (FACE_SIG):", app.led.state.name)
if app.led.state != LEDState.REGISTERING: issues.append("Phase 1 LED mismatch")

advance_time(3.0)
print("LED 2 (EAR_OPEN):", app.led.state.name)
if app.led.state != LEDState.EAR_OPEN: issues.append(f"Phase 2 LED mismatch, is {app.led.state.name}")

advance_time(3.0)
print("LED 3 (EAR_CLOSED):", app.led.state.name)
if app.led.state != LEDState.EAR_CLOSED: issues.append(f"Phase 3 LED mismatch, is {app.led.state.name}")

advance_time(2.0)
print("LED 4 (PITCH_CAL):", app.led.state.name)
if app.led.state != LEDState.PITCH_CAL: issues.append(f"Phase 4 LED mismatch, is {app.led.state.name}")

advance_time(2.0)
print("LED 5 (SUCCESS):", app.led.state.name)
if app.led.state != LEDState.SUCCESS: issues.append(f"Phase 5 LED mismatch, is {app.led.state.name}")

if not os.path.exists("data/owner_profile.json"):
    issues.append("Profile JSON not created")
else:
    print("Profile JSON successfully created.")

root.destroy()

print("\n--- SCENARIO 3: SECOND LAUNCH (LOAD PROFILE) ---")
root2 = tk.Tk()
app2 = AntiSleepyApp(root2, cap, DrowsinessDetector(DetectorConfig()))
app2._update()
root2.update()
owner_txt2 = app2.lbl_owner_status.cget("text")
print("Owner state 2:", owner_txt2)
print("LED State 2:", app2.led.state.name)
if app2.led.state != LEDState.RUNNING_OK: issues.append(f"Scenario 3 LED mismatch, expected RUNNING_OK, got {app2.led.state.name}")

print("\n--- SCENARIO 4: UNKNOWN DRIVER ---")
import anti_sleepy.ui.app as ui_app
orig_is_owner = ui_app.is_owner
ui_app.is_owner = lambda c, s, t=0.92: False

app2._update()
root2.update()
id_text = app2.lbl_identity.cget("text")
print("Identity text:", id_text)
print("LED State 4:", app2.led.state.name)
if id_text != "Nhận dạng: LẠ": issues.append("Scenario 4 Label mismatch")
if app2.led.state != LEDState.RUNNING_UNKNOWN: issues.append("Scenario 4 LED mismatch")

print("\n--- SCENARIO 5: SUNGLASSES MODE ---")
ui_app.is_owner = orig_is_owner
app2.detector.sunglasses_mode = False

DrowsinessDetector.get_ear = lambda self, l, idx: 0.10
app2._update()
root2.update()
print("Sunglasses mode enabled?", app2.detector.sunglasses_mode)
if not app2.detector.sunglasses_mode: issues.append("Sunglasses mode not tripped by low EAR")

if not issues:
    print("\nALL 5 SCENARIOS PASSED WITH NO BUGS FOUND! 🎉")
else:
    print("\nBUGS FOUND:")
    for b in issues: print("-", b)
