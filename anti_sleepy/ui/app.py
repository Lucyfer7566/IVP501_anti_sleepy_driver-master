import tkinter as tk
from tkinter import messagebox, scrolledtext
import cv2
import numpy as np
from PIL import Image, ImageTk
import time

from anti_sleepy.core.detector import DrowsinessDetector
from anti_sleepy.core.profile import profile_exists, load_profile, save_profile, delete_profile
from anti_sleepy.core.audio import AudioPlayer
from anti_sleepy.ui.led_widget import LEDWidget, LEDState
from anti_sleepy.ui.register_flow import RegisterFlow, RegPhase
from anti_sleepy.core.face_id import (
    extract_face_signature, compare_signatures, is_owner,
    extract_face_crop, compute_face_histogram, save_face_descriptor
)

class AntiSleepyApp:
    def __init__(self, root: tk.Tk, cap: cv2.VideoCapture, detector: DrowsinessDetector):
        self.root = root
        self.cap = cap
        self.detector = detector
        
        self._btn_press_time = 0.0
        self._btn_after_id = None
        self._frame_count = 0
        self._reg_saved = False
        
        # Identity tracking
        self._identity_buffer = []
        self._identity_stable = "CHUA RO"
        self._last_alert_status = ""
        self._saved_hist = None  # numpy array for histogram comparison
        
        self.build_ui()
        
        # Sub-modules
        self.reg_flow = RegisterFlow(detector, self.led)
        self.saved_profile = load_profile() if profile_exists() else None
        self.audio = AudioPlayer.get_instance()
        self.last_identity = None
        self.has_greeted = False
        
        if self.saved_profile:
            self.detector.load_owner_profile(self.saved_profile)
            sig = self.saved_profile.get("face_signature", [])
            hist_data = self.saved_profile.get("face_histogram", [])
            if hist_data:
                self._saved_hist = np.array(hist_data, dtype=np.float32)
            self._log(f"Da tai profile ({len(sig)} sig, hist={'Co' if hist_data else 'Khong'})", "info")
        else:
            self.root.after(1000, lambda: self.audio.play("sys_no_profile.wav"))
            self._log("Chua co profile. Vui long dang ky!", "warn")
        
        self._update_ui_labels()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        if not getattr(self.root, "mock_mode", False):
            self.root.after(30, self._update)

    def build_ui(self):
        self.root.title("Anti Sleepy Driver")
        try:
            self.root.state('zoomed')
        except tk.TclError:
            self.root.geometry("1280x800")
        
        # ===== TOP: Camera (large) =====
        self.video_label = tk.Label(self.root)
        self.video_label.pack(side=tk.TOP, pady=5, fill=tk.X)
        
        # ===== MIDDLE: Controls (horizontal bar) =====
        ctrl_frame = tk.Frame(self.root, relief=tk.GROOVE, borderwidth=1)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=3)
        
        # LED
        self.led = LEDWidget(ctrl_frame, canvas_size=40)
        self.led.pack(side=tk.LEFT, padx=10)
        
        # Register button
        self.reg_btn = tk.Button(ctrl_frame, text="Dang ky", font=("Arial", 9, "bold"), width=10)
        self.reg_btn.pack(side=tk.LEFT, padx=5)
        self.reg_btn.bind("<ButtonPress-1>", self.on_btn_press)
        self.reg_btn.bind("<ButtonRelease-1>", self.on_btn_release)
        
        # Status labels (horizontal)
        self.lbl_owner_status = tk.Label(ctrl_frame, text="Owner: --", font=("Arial", 10, "bold"))
        self.lbl_owner_status.pack(side=tk.LEFT, padx=15)
        
        self.lbl_identity = tk.Label(ctrl_frame, text="Nhan dang: --", font=("Arial", 10, "bold"))
        self.lbl_identity.pack(side=tk.LEFT, padx=15)
        
        self.lbl_mode = tk.Label(ctrl_frame, text="Mode: BINH THUONG", font=("Arial", 10, "bold"))
        self.lbl_mode.pack(side=tk.LEFT, padx=15)
        
        self.lbl_metrics = tk.Label(ctrl_frame, text="EAR: -- | MAR: -- | PITCH: --", font=("Consolas", 9))
        self.lbl_metrics.pack(side=tk.LEFT, padx=15)
        
        self.lbl_similarity = tk.Label(ctrl_frame, text="Sim: --", font=("Consolas", 9))
        self.lbl_similarity.pack(side=tk.LEFT, padx=10)
        
        # ===== BOTTOM: Log panel (horizontal, short) =====
        log_frame = tk.LabelFrame(self.root, text=" Nhat ky su kien ", font=("Arial", 9, "bold"))
        log_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=3)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=6, font=("Consolas", 9), state=tk.DISABLED,
            bg="#1a1a2e", fg="#e0e0e0", insertbackground="white"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        self.log_text.tag_config("alert", foreground="#ff4444", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("success", foreground="#44ff44")
        self.log_text.tag_config("info", foreground="#88aaff")
        self.log_text.tag_config("warn", foreground="#ffaa44")
        self.log_text.tag_config("system", foreground="#aaaaaa")

    def _log(self, message: str, tag: str = "system"):
        ts = time.strftime("%H:%M:%S")
        full = f"[{ts}] {message}"
        print(full)
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, full + "\n", tag)
            self.log_text.see(tk.END)
            lines = int(self.log_text.index('end-1c').split('.')[0])
            if lines > 100:
                self.log_text.delete('1.0', f'{lines - 100}.0')
            self.log_text.config(state=tk.DISABLED)
        except tk.TclError:
            pass

    def _update_ui_labels(self):
        if self.saved_profile:
            self.lbl_owner_status.config(text="Owner: DA DANG KY", fg="green")
        else:
            self.lbl_owner_status.config(text="Owner: CHUA DANG KY", fg="red")

    def on_btn_press(self, event):
        self._btn_press_time = time.time()
        self._btn_after_id = self.root.after(2000, self.on_btn_long_press)

    def on_btn_release(self, event):
        if self._btn_after_id is not None:
            self.root.after_cancel(self._btn_after_id)
            self._btn_after_id = None
            duration = time.time() - self._btn_press_time
            if duration < 2.0:
                if self.saved_profile is None:
                    self.start_registration()
                else:
                    if messagebox.askyesno("Dang ky lai", "Xoa dang ky va dang ky lai?"):
                        delete_profile()
                        self.saved_profile = None
                        self._saved_hist = None
                        self.detector.using_personal_profile = False
                        self._identity_buffer.clear()
                        self._identity_stable = "CHUA RO"
                        self.has_greeted = False
                        self.last_identity = None
                        self._update_ui_labels()
                        self._log("Da xoa profile.", "warn")
                        self.start_registration()

    def on_btn_long_press(self):
        self._btn_after_id = None
        self.start_registration()

    def start_registration(self):
        if self.reg_flow.phase == RegPhase.IDLE:
            self._reg_saved = False
            self.reg_flow.start()
            self._log("Bat dau dang ky khuon mat...", "info")

    def _update(self):
        success, frame = self.cap.read()
        if not success:
            if not getattr(self.root, "mock_mode", False):
                self.root.after(30, self._update)
            return
            
        frame = cv2.flip(frame, 1)
        self._frame_count += 1
        
        processed_frame = self.detector.process_frame(frame)
        
        m = self.detector.last_metrics
        ear = m.get("ear", 0.0)
        mar = m.get("mar", 0.0)
        pitch = m.get("pitch", 0.0)
        yaw = m.get("yaw", 0.0)
        landmarks = m.get("landmarks", [])
        bbox = m.get("bbox", None)
        is_alert = m.get("is_alert", False)
        
        in_registration = self.reg_flow.phase != RegPhase.IDLE
        
        if in_registration:
            # Extract histogram from current frame for registration
            face_hist = None
            if bbox and self.reg_flow.phase == RegPhase.FACE_SIG:
                crop = extract_face_crop(frame, bbox)
                if crop is not None:
                    face_hist = compute_face_histogram(crop)
            
            reg_text = self.reg_flow.feed_frame(landmarks, ear, mar, pitch, face_hist)
            cv2.putText(processed_frame, reg_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            if self.reg_flow.is_complete() and not self._reg_saved:
                self._reg_saved = True
                self.saved_profile = self.reg_flow.get_profile()
                save_profile(self.saved_profile)
                self.detector.load_owner_profile(self.saved_profile)
                
                hist_data = self.saved_profile.get("face_histogram", [])
                if hist_data:
                    self._saved_hist = np.array(hist_data, dtype=np.float32)
                
                self._identity_buffer.clear()
                self._identity_stable = "CHUA RO"
                self.has_greeted = False
                self.last_identity = None
                self._update_ui_labels()
                
                self._log("Dang ky thanh cong!", "success")
                self._log(f"  EAR thresh: {self.saved_profile['ear_thresh']}", "info")
                
                self.root.after(2000, self.reg_flow.cancel)
        else:
            # --- Face identity check ---
            combined_score = 0.0
            if landmarks and self.saved_profile and self.saved_profile.get("face_signature"):
                current_sig = extract_face_signature(landmarks)
                saved_sig = self.saved_profile["face_signature"]
                
                # Get current face histogram
                current_hist = None
                if bbox:
                    crop = extract_face_crop(frame, bbox)
                    if crop is not None:
                        current_hist = compute_face_histogram(crop)
                
                if current_sig:
                    owner_match, combined_score = is_owner(
                        current_sig, saved_sig,
                        current_hist=current_hist,
                        saved_hist=self._saved_hist,
                        yaw=yaw
                    )
                    
                    self._identity_buffer.append(owner_match)
                    if len(self._identity_buffer) > 25:
                        self._identity_buffer.pop(0)
                    
                    if len(self._identity_buffer) >= 12:
                        owner_votes = sum(self._identity_buffer)
                        total = len(self._identity_buffer)
                        if owner_votes > total * 0.55:
                            self._identity_stable = "CHU XE"
                        elif owner_votes < total * 0.3:
                            self._identity_stable = "LA"
                else:
                    self._identity_buffer.clear()
                    self._identity_stable = "CHUA RO"
            elif not landmarks:
                self._identity_buffer.clear()
                self._identity_stable = "CHUA RO"
            
            self.lbl_similarity.config(text=f"Sim: {combined_score:.3f}")
            
            if is_alert:
                self.led.set_state(LEDState.ALERT)
                alert_sound = m.get("sound", "")
                if alert_sound:
                    self.audio.play(alert_sound, cooldown=5.0)
                current_status = m.get("status", "")
                if current_status != self._last_alert_status:
                    self._last_alert_status = current_status
                    self._log(f"CANH BAO: {current_status}", "alert")
            else:
                if self._last_alert_status:
                    self._log("Binh thuong tro lai", "success")
                    self._last_alert_status = ""
                
                if not landmarks:
                    self.led.set_state(LEDState.OFF)
                    self.lbl_identity.config(text="Nhan dang: --", fg="black")
                else:
                    if self._identity_stable == "CHU XE":
                        self.led.set_state(LEDState.RUNNING_OK)
                        self.lbl_identity.config(text="Nhan dang: CHU XE", fg="green")
                        if not self.has_greeted or self.last_identity != "CHU XE":
                            self.audio.play("sys_welcome_owner.wav")
                            self._log("Nhan dang: CHU XE", "success")
                            self.has_greeted = True
                            self.last_identity = "CHU XE"
                    elif self._identity_stable == "LA":
                        self.led.set_state(LEDState.RUNNING_UNKNOWN)
                        self.lbl_identity.config(text="Nhan dang: NGUOI LA", fg="red")
                        if not self.has_greeted or self.last_identity != "LA":
                            self.audio.play("sys_unknown_driver.wav")
                            self._log("Nhan dang: NGUOI LA", "warn")
                            self.has_greeted = True
                            self.last_identity = "LA"
                    else:
                        self.led.set_state(LEDState.OFF)
                        self.lbl_identity.config(text="Nhan dang: ...", fg="gray")
                        
        mode_text = "KINH RAM" if self.detector.sunglasses_mode else "BINH THUONG"
        self.lbl_mode.config(text=f"Mode: {mode_text}")
        self.lbl_metrics.config(text=f"EAR:{ear:.2f} | MAR:{mar:.2f} | P:{pitch:.0f}")

        # Display frame
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_frame)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        
        if not getattr(self.root, "mock_mode", False):
            self.root.after(30, self._update)

    def on_closing(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'detector'):
            self.detector.close()
        self.root.destroy()
