import tkinter as tk
from tkinter import messagebox, scrolledtext
import cv2
import numpy as np
from PIL import Image, ImageTk
import time

from anti_sleepy.core.detector import DrowsinessDetector
from anti_sleepy.core.audio import AudioPlayer
from anti_sleepy.ui.led_widget import LEDWidget, LEDState

class AntiSleepyApp:
    def __init__(self, root: tk.Tk, cap: cv2.VideoCapture, detector: DrowsinessDetector):
        self.root = root
        self.cap = cap
        self.detector = detector
        
        self._btn_press_time = 0.0
        self._btn_after_id = None
        self._frame_count = 0
        self._reg_saved = False
        
        self._last_alert_status = ""
        
        self.build_ui()
        
        self.build_ui()
        
        # Sub-modules
        self.audio = AudioPlayer.get_instance()
        
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
        
        self.lbl_mode = tk.Label(ctrl_frame, text="Mode: BINH THUONG", font=("Arial", 10, "bold"))
        self.lbl_mode.pack(side=tk.LEFT, padx=15)
        
        self.lbl_metrics = tk.Label(ctrl_frame, text="EAR: -- | MAR: -- | PITCH: --", font=("Consolas", 9))
        self.lbl_metrics.pack(side=tk.LEFT, padx=15)
        
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

    def on_closing(self):
        self.detector.stop()
        self.cap.release()
        self.root.destroy()

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
        # Draw UI (Delegated to detector.py OSD)
        
        if is_alert:
            alert_sound = m.get("sound", "")
            if alert_sound:
                self.audio.play(alert_sound, cooldown=5.0)
            current_status = m.get("status", "")
            
            # Use AlertLevel from detector to map to LED State
            alert_level = m.get("alert_level", 0)
            if alert_level == 2:
                self.led.set_state(LEDState.ALERT)
            elif alert_level == 1:
                self.led.set_state(LEDState.RUNNING_UNKNOWN) # Orange/Warning mapping
            else:
                self.led.set_state(LEDState.ALERT)
                
            if current_status != self._last_alert_status:
                self._last_alert_status = current_status
                self._log(f"CANH BAO: {current_status}", "alert")
        else:
            if self._last_alert_status:
                self._log("Binh thuong tro lai", "success")
                self._last_alert_status = ""
            
            if not landmarks:
                self.led.set_state(LEDState.OFF)
            else:
                self.led.set_state(LEDState.RUNNING_OK) # Driver present and normal
                    
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
