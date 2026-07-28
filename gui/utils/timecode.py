"""
SMPTE Timecode utility functions for frame <-> timecode string conversion (HH:MM:SS:FF).
"""


def frames_to_timecode(frames: int, fps: float = 60.0) -> str:
    """Convert frame count to HH:MM:SS:FF SMPTE string."""
    if frames < 0:
        frames = 0

    fps_int = int(round(fps))
    total_seconds = int(frames // fps_int)
    frame_rem = int(frames % fps_int)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frame_rem:02d}"


def timecode_to_frames(timecode_str: str, fps: float = 60.0) -> int:
    """Convert HH:MM:SS:FF SMPTE string to frame count."""
    try:
        parts = [int(p) for p in timecode_str.strip().split(":")]
        if len(parts) != 4:
            return 0
        h, m, s, f = parts
        fps_int = int(round(fps))
        total_seconds = (h * 3600) + (m * 60) + s
        return (total_seconds * fps_int) + f
    except Exception:
        return 0


def seconds_to_frames(seconds: float, fps: float = 60.0) -> int:
    """Convert seconds to integer frame count."""
    return int(round(seconds * fps))


def frames_to_seconds(frames: int, fps: float = 60.0) -> float:
    """Convert frame count to seconds float."""
    return frames / fps
