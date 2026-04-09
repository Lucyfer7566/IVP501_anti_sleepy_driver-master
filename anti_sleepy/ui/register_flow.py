import time
from enum import Enum
from datetime import datetime
from typing import List, Tuple, Optional

import numpy as np

from anti_sleepy.core.detector import DrowsinessDetector
from anti_sleepy.ui.led_widget import LEDWidget, LEDState
from anti_sleepy.core.face_id import extract_face_signature, average_signatures
from anti_sleepy.core.audio import AudioPlayer

class RegPhase(Enum):
    IDLE = 0
    FACE_SIG = 1
    EAR_OPEN = 2
    EAR_CLOSED = 3
    PITCH_CAL = 4
    SUCCESS = 5

class RegisterFlow:
    def __init__(self, detector: DrowsinessDetector, led: LEDWidget):
        self.detector = detector
        self.led = led
        self.audio = AudioPlayer.get_instance()
        
        self.phase = RegPhase.IDLE
        self.time_in_phase = 0.0
        self.last_update_time = 0.0
        self.face_missing_timer = 0.0
        
        self.sig_list: List[List[float]] = []
        self.ear_open_list: List[float] = []
        self.ear_closed_list: List[float] = []
        self.pitch_list: List[float] = []
        self.mar_list: List[float] = []
        self.face_histograms: List[np.ndarray] = []
        
        self._profile: Optional[dict] = None

    def _reset_accumulators(self):
        self.sig_list.clear()
        self.ear_open_list.clear()
        self.ear_closed_list.clear()
        self.pitch_list.clear()
        self.mar_list.clear()
        self.face_histograms.clear()

    def start(self):
        self._reset_accumulators()
        self.phase = RegPhase.FACE_SIG
        self.time_in_phase = 0.0
        self.last_update_time = time.time()
        self.face_missing_timer = 0.0
        self._profile = None
        
        self.led.set_state(LEDState.REGISTERING)
        self.audio.play("reg_start.wav", force=True)
        print("[REG] === BAT DAU DANG KY ===")

    def cancel(self):
        if self.phase != RegPhase.IDLE:
            self.phase = RegPhase.IDLE
            self.led.set_state(LEDState.OFF)
            self.audio.stop()
            print("[REG] Ket thuc dang ky")

    def is_complete(self) -> bool:
        return self.phase == RegPhase.SUCCESS

    def get_profile(self) -> dict:
        return self._profile or {}
        
    def feed_frame(self, landmarks: List[Tuple[int, int]], ear: float, mar: float, pitch: float,
                   face_hist: Optional[np.ndarray] = None) -> str:
        if self.phase == RegPhase.IDLE:
            return ""
        if self.phase == RegPhase.SUCCESS:
            return "Dang ky thanh cong!"
            
        now = time.time()
        if self.last_update_time == 0.0:
            self.last_update_time = now
            
        dt = now - self.last_update_time
        self.last_update_time = now

        if not landmarks:
            self.face_missing_timer += dt
            if self.face_missing_timer > 1.0:
                self.audio.play("reg_no_face.wav", cooldown=4.0)
                return "Khong thay khuon mat"
            return "Dang tim khuon mat..."
            
        self.face_missing_timer = 0.0
        
        if self.phase == RegPhase.FACE_SIG and ear < 0.15:
            self.audio.play("reg_remove_glasses.wav", cooldown=4.0)
            return "Hay bo kinh ram khi dang ky"

        self.time_in_phase += dt
        
        if self.phase == RegPhase.FACE_SIG:
            if self.time_in_phase < 3.0:
                sig = extract_face_signature(landmarks)
                if sig:
                    self.sig_list.append(sig)
                # Collect face histograms for identity matching
                if face_hist is not None:
                    self.face_histograms.append(face_hist)
                return f"Nhin thang vao camera... ({len(self.sig_list)} mau)"
            else:
                print(f"[REG] FACE_SIG: {len(self.sig_list)} mau, {len(self.face_histograms)} hist")
                self.phase = RegPhase.EAR_OPEN
                self.time_in_phase = 0.0
                self.led.set_state(LEDState.EAR_OPEN)
                self.audio.play("reg_eyes_open.wav", force=True)
                
        elif self.phase == RegPhase.EAR_OPEN:
            if self.time_in_phase < 3.0:
                self.ear_open_list.append(ear)
                self.mar_list.append(mar)
                return "Mo mat binh thuong, nhin thang"
            else:
                avg = sum(self.ear_open_list) / max(1, len(self.ear_open_list))
                print(f"[REG] EAR_OPEN: {len(self.ear_open_list)} mau, avg={avg:.3f}")
                self.phase = RegPhase.EAR_CLOSED
                self.time_in_phase = 0.0
                self.led.set_state(LEDState.EAR_CLOSED)
                self.audio.play("reg_eyes_closed.wav", force=True)
                
        elif self.phase == RegPhase.EAR_CLOSED:
            if self.time_in_phase < 3.0:
                self.ear_closed_list.append(ear)
                return "Nham mat lai"
            else:
                avg = sum(self.ear_closed_list) / max(1, len(self.ear_closed_list))
                print(f"[REG] EAR_CLOSED: {len(self.ear_closed_list)} mau, avg={avg:.3f}")
                self.phase = RegPhase.PITCH_CAL
                self.time_in_phase = 0.0
                self.led.set_state(LEDState.PITCH_CAL)
                self.audio.play("reg_pitch_cal.wav", force=True)
                
        elif self.phase == RegPhase.PITCH_CAL:
            if self.time_in_phase < 2.0:
                self.pitch_list.append(pitch)
                return "Nhin thang ve phia truoc"
            else:
                avg = sum(self.pitch_list) / max(1, len(self.pitch_list))
                print(f"[REG] PITCH_CAL: {len(self.pitch_list)} mau, avg={avg:.1f}")
                self._compute_profile()
                self.phase = RegPhase.SUCCESS
                self.led.set_state(LEDState.SUCCESS)
                self.audio.play("reg_success.wav", force=True)
                return "Dang ky thanh cong!"
                
        return ""

    def _compute_profile(self):
        ear_open = sum(self.ear_open_list) / max(1, len(self.ear_open_list))
        ear_closed = sum(self.ear_closed_list) / max(1, len(self.ear_closed_list))
        
        if len(self.ear_closed_list) == 0 or ear_closed >= ear_open:
            ear_closed = ear_open * 0.5 
            
        ear_thresh = (ear_open + ear_closed) / 2.0
        
        mar_base = sum(self.mar_list) / max(1, len(self.mar_list))
        mar_thresh = max(mar_base * 2.5, 0.45)
        
        pitch_base = sum(self.pitch_list) / max(1, len(self.pitch_list))
        
        face_sig = average_signatures(self.sig_list) if self.sig_list else []
        
        # Average face histograms for robust identity baseline
        face_hist_avg = None
        if self.face_histograms:
            face_hist_avg = np.mean(self.face_histograms, axis=0)
        
        self._profile = {
            "registered_at": datetime.now().isoformat(),
            "face_signature": face_sig,
            "face_histogram": face_hist_avg.tolist() if face_hist_avg is not None else [],
            "ear_open_baseline": round(ear_open, 3),
            "ear_closed_baseline": round(ear_closed, 3),
            "ear_thresh": round(ear_thresh, 3),
            "mar_baseline": round(mar_base, 3),
            "mar_thresh": round(mar_thresh, 3),
            "pitch_base": round(pitch_base, 3),
            "sunglasses_ear_cutoff": 0.15
        }
        
        print(f"[REG] === PROFILE ===")
        print(f"  sig: {len(face_sig)} features, hist: {'Yes' if face_hist_avg is not None else 'No'}")
        print(f"  ear: open={ear_open:.3f} closed={ear_closed:.3f} thresh={ear_thresh:.3f}")
        print(f"  mar: base={mar_base:.3f} thresh={mar_thresh:.3f}")
        print(f"  pitch: {pitch_base:.1f}")
