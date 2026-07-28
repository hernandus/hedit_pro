"""
Effect Wrappers & Keyframe Animation Model for Hedit Pro.
Supports keyframe interpolation (Linear, Ease-In, Ease-Out, Bezier) and property animation for MLT filters.
"""

from typing import List, Dict, Any, Optional
import math


class Keyframe:
    """Represents a single keyframe point on the timeline."""

    def __init__(self, frame: int, value: float, interp_type: str = "linear"):
        self.frame = frame
        self.value = value
        self.interp_type = interp_type # "linear", "ease_in", "ease_out", "bezier"


class AnimatableProperty:
    """Property with keyframing capabilities (e.g. Position X, Scale, Opacity)."""

    def __init__(self, name: str, default_value: float, min_val: float = -9999.0, max_val: float = 9999.0):
        self.name = name
        self.default_value = default_value
        self.min_val = min_val
        self.max_val = max_val
        self.keyframes: List[Keyframe] = []

    def set_keyframe(self, frame: int, value: float, interp_type: str = "linear"):
        """Add or update a keyframe at the given frame."""
        for k in self.keyframes:
            if k.frame == frame:
                k.value = value
                k.interp_type = interp_type
                return
        self.keyframes.append(Keyframe(frame, value, interp_type))
        self.keyframes.sort(key=lambda k: k.frame)

    def remove_keyframe(self, frame: int):
        self.keyframes = [k for k in self.keyframes if k.frame != frame]

    def has_keyframe_at(self, frame: int) -> bool:
        return any(k.frame == frame for k in self.keyframes)

    def get_value_at(self, frame: int) -> float:
        """Evaluate property value at specific frame (with interpolation)."""
        if not self.keyframes:
            return self.default_value

        if frame <= self.keyframes[0].frame:
            return self.keyframes[0].value

        if frame >= self.keyframes[-1].frame:
            return self.keyframes[-1].value

        # Find keyframe segment
        for i in range(len(self.keyframes) - 1):
            k1 = self.keyframes[i]
            k2 = self.keyframes[i + 1]
            if k1.frame <= frame <= k2.frame:
                t = (frame - k1.frame) / float(k2.frame - k1.frame)
                
                if k1.interp_type == "ease_in":
                    t = t * t
                elif k1.interp_type == "ease_out":
                    t = 1 - (1 - t) * (1 - t)
                elif k1.interp_type == "bezier":
                    t = t * t * (3 - 2 * t)

                return k1.value + t * (k2.value - k1.value)

        return self.default_value


class MotionEffect:
    """Standard Premiere Pro Motion & Opacity Effect stack for clips."""

    def __init__(self):
        self.position_x = AnimatableProperty("Position X", 960.0)
        self.position_y = AnimatableProperty("Position Y", 540.0)
        self.scale = AnimatableProperty("Scale", 100.0, min_val=0.0, max_val=1000.0)
        self.rotation = AnimatableProperty("Rotation", 0.0, min_val=-360.0, max_val=360.0)
        self.opacity = AnimatableProperty("Opacity", 100.0, min_val=0.0, max_val=100.0)

    def to_mlt_geometry(self, frame: int) -> str:
        """Convert interpolated motion values to MLT qtblend geometry string."""
        x = self.position_x.get_value_at(frame)
        y = self.position_y.get_value_at(frame)
        s = self.scale.get_value_at(frame) / 100.0
        w = int(1920 * s)
        h = int(1080 * s)
        return f"{int(x)}/{int(y)}:{w}x{h}"
