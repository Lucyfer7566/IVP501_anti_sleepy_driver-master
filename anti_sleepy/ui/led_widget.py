import tkinter as tk
from enum import Enum, auto

class LEDState(Enum):
    OFF = auto()
    RUNNING_OK = auto()
    RUNNING_UNKNOWN = auto()
    ALERT = auto()

STATE_CONFIG = {
    LEDState.OFF:             ("gray", "", "solid", 0),
    LEDState.RUNNING_OK:      ("green", "lightgreen", "pulse", 500),
    LEDState.RUNNING_UNKNOWN: ("yellow", "lightyellow", "pulse", 500),
    LEDState.ALERT:           ("red", "#ff6666", "blink", 100)
}

class LEDWidget(tk.Frame):
    def __init__(self, parent, canvas_size=60, **kwargs):
        """
        Creates a 40x40 LED centered inside a slightly larger frame to accommodate 
        the label and glow.
        """
        super().__init__(parent, **kwargs)
        
        # Match parent's background color
        # Some generic containers do not have 'cget', so we safely default to system standard
        bg_color = parent.cget('bg') if hasattr(parent, 'cget') else '#f0f0f0'
        self.configure(bg=bg_color)
        
        self.state = LEDState.OFF
        
        self.canvas = tk.Canvas(self, width=canvas_size, height=canvas_size, bg=bg_color, highlightthickness=0)
        self.canvas.pack()
        
        self.label = tk.Label(self, text=self.state.name, font=("Arial", 8, "bold"), bg=bg_color)
        self.label.pack()
        
        # Center coordinates
        center = canvas_size / 2
        # Requested LED geometric size is 40x40 -> radius = 20
        radius = 20
        glow_radius = 26
        
        # The glow is technically a slightly expanded oval with no outline
        self.glow = self.canvas.create_oval(
            center - glow_radius, center - glow_radius,
            center + glow_radius, center + glow_radius,
            fill="", outline=""
        )
        
        # The core physical LED indicator
        self.core = self.canvas.create_oval(
            center - radius, center - radius,
            center + radius, center + radius,
            fill="gray", outline="black", width=2
        )
        
        self._anim_id = None
        self._is_on = True
        
        self._update_visuals()
        
    def set_state(self, state: LEDState):
        """
        Safely transitions the widget to any newly assigned LEDState configuration.
        """
        if self.state == state:
            return
            
        self.state = state
        self.label.config(text=state.name)
        
        if self._anim_id is not None:
            self.after_cancel(self._anim_id)
            self._anim_id = None
            
        self._is_on = True
        self._update_visuals()

    def _update_visuals(self):
        base_color, glow_color, anim_mode, delay = STATE_CONFIG[self.state]
        
        if anim_mode == "solid":
            self.canvas.itemconfig(self.glow, fill=glow_color)
            self.canvas.itemconfig(self.core, fill=base_color)
            
        elif anim_mode in ["blink", "pulse"]:
            if self._is_on:
                self.canvas.itemconfig(self.glow, fill=glow_color)
                self.canvas.itemconfig(self.core, fill=base_color)
            else:
                self.canvas.itemconfig(self.glow, fill="")
                
                if anim_mode == "blink":
                    self.canvas.itemconfig(self.core, fill="gray")
                else: 
                    # Pulse mode generates a distinctly "breathing/dimming" logic rather than total blackout
                    dim_color = "darkgreen" if base_color == "green" else "orange" if base_color == "yellow" else "gray"
                    self.canvas.itemconfig(self.core, fill=dim_color)
                
            self._is_on = not self._is_on
            self._anim_id = self.after(delay, self._update_visuals)
