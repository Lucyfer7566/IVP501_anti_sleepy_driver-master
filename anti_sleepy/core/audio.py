import os
import time
import winsound

class AudioPlayer:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AudioPlayer()
        return cls._instance

    def __init__(self):
        # Base directory points to anti_sleepy/assets/sounds
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'sounds'))
        self.last_audio = None
        self.last_play_time = 0.0

    def play(self, filename: str, cooldown: float = 3.0, force: bool = False):
        """
        Plays a WAV file asynchronously without blocking the main OpenCV/Tkinter thread.
        cooldown: prevents spamming the same/different sound if called repeatedly in a loop.
        force: overrides cooldown (useful for immediate state transitions).
        """
        now = time.time()
        if not force and now - self.last_play_time < cooldown:
            return
            
        path = os.path.join(self.base_dir, filename)
        if os.path.exists(path):
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            self.last_audio = filename
            self.last_play_time = now
        else:
            print(f"Warning: Audio file not found at {path}")
            
    def stop(self):
        """Stops any currently playing asynchronous audio."""
        winsound.PlaySound(None, winsound.SND_PURGE)
        self.last_audio = None
        self.last_play_time = 0.0
