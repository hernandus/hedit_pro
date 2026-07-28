"""
Color Correction & Grading Engine for Hedit Pro (Lumetri equivalent).
Supports Lift/Gamma/Gain color wheels, RGB curves, and 3D LUT (.cube) Frei0r filter mapping.
"""

from typing import Dict, List, Tuple


class ColorGradingModel:
    """Stores color grading parameters for a clip or sequence."""

    def __init__(self):
        # Basic Correction
        self.temperature = 0.0  # -100 to 100
        self.tint = 0.0         # -100 to 100
        self.exposure = 0.0     # -5.0 to +5.0 EV
        self.contrast = 0.0     # -100 to 100
        self.highlights = 0.0   # -100 to 100
        self.shadows = 0.0      # -100 to 100
        self.saturation = 100.0 # 0 to 200%

        # Color Wheels (RGB offsets: -1.0 to +1.0)
        self.lift = [0.0, 0.0, 0.0]   # Shadows
        self.gamma = [0.0, 0.0, 0.0]  # Midtones
        self.gain = [0.0, 0.0, 0.0]   # Highlights

        # Active LUT file path
        self.lut_path = ""

    def reset(self):
        self.temperature = 0.0
        self.tint = 0.0
        self.exposure = 0.0
        self.contrast = 0.0
        self.highlights = 0.0
        self.shadows = 0.0
        self.saturation = 100.0
        self.lift = [0.0, 0.0, 0.0]
        self.gamma = [0.0, 0.0, 0.0]
        self.gain = [0.0, 0.0, 0.0]
        self.lut_path = ""

    def to_frei0r_lift_gamma_gain(self) -> Dict[str, float]:
        """Convert lift/gamma/gain wheel values to Frei0r / MLT filter parameters."""
        return {
            "lift_r": self.lift[0], "lift_g": self.lift[1], "lift_b": self.lift[2],
            "gamma_r": self.gamma[0], "gamma_g": self.gamma[1], "gamma_b": self.gamma[2],
            "gain_r": self.gain[0], "gain_g": self.gain[1], "gain_b": self.gain[2],
        }
