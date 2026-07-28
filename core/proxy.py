"""
Proxy Transcoding Engine for Hedit Pro.
Processes a queue of video files encoding them as ProRes proxy media via ffmpeg.
Files are processed sequentially (one at a time) with real-time progress reporting.
"""

import os
import subprocess
import tempfile
from typing import List

from PySide6.QtCore import QThread, Signal

from core.logger import get_logger

logger = get_logger()


# --- Codec presets -----------------------------------------------------------

PROXY_CODECS = {
    "ProRes Proxy": {
        "profile": "0",
        "description": "Apple ProRes Proxy — Smallest file, ideal for editing on slow drives",
    },
    "ProRes 422": {
        "profile": "2",
        "description": "Apple ProRes 422 — Standard quality, broader compatibility",
    },
}

# Longest-side pixel values offered in the dialog
PROXY_DIMENSIONS = {
    "1280px  (longest side)": 1280,
    " 720px  (longest side)": 720,
    " 640px  (longest side)": 640,
}


# --- Helpers -----------------------------------------------------------------

def get_video_frame_count(path: str) -> int:
    """Returns total frame count of a video file via ffprobe. Returns 0 on failure."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=nb_frames,duration,r_frame_rate",
            "-of", "default=noprint_wrappers=1",
            path,
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10
        )
        nb_frames = None
        duration = None
        r_frame_rate = None

        for line in result.stdout.splitlines():
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            val = val.strip()
            if key == "nb_frames" and val.isdigit():
                nb_frames = int(val)
            elif key == "duration":
                try:
                    duration = float(val)
                except ValueError:
                    pass
            elif key == "r_frame_rate":
                r_frame_rate = val

        if nb_frames and nb_frames > 0:
            return nb_frames

        if duration and r_frame_rate:
            parts = r_frame_rate.split("/")
            if len(parts) == 2:
                num, den = float(parts[0]), float(parts[1])
                if den > 0:
                    return int(duration * num / den)
    except Exception as e:
        logger.warning(f"[PROXY] Could not get frame count for '{path}': {e}")
    return 0


def _proxy_candidate_path(source_path: str, longest_side: int, codec_name: str) -> str:
    """
    Returns the *expected* proxy file path for a given source + settings
    WITHOUT creating any directories on disk (pure computation).
    """
    source_dir = os.path.dirname(os.path.abspath(source_path))
    proxies_dir = os.path.join(source_dir, "Proxies")
    base = os.path.splitext(os.path.basename(source_path))[0]
    tag = "proxy" if "Proxy" in codec_name else "422"
    out_name = f"{base}_{tag}_{longest_side}.mov"
    return os.path.join(proxies_dir, out_name)


def get_proxy_output_path(source_path: str, longest_side: int, codec_name: str) -> str:
    """
    Returns the output path for a proxy file and creates the Proxies/ directory.
    Example: /footage/C0159.MP4  →  /footage/Proxies/C0159_proxy_1280.mov
    """
    path = _proxy_candidate_path(source_path, longest_side, codec_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def find_proxy_for_source(source_path: str) -> str | None:
    """
    Scans all codec/dimension combinations and returns the path of the first
    existing proxy file for *source_path*, or None if no proxy has been created yet.
    Does NOT create any directories.
    """
    for codec_name in PROXY_CODECS:
        for longest_side in PROXY_DIMENSIONS.values():
            candidate = _proxy_candidate_path(source_path, longest_side, codec_name)
            if os.path.exists(candidate):
                return candidate
    return None


def _build_scale_filter(longest_side: int) -> str:
    """Returns an ffmpeg scale filter that preserves aspect ratio."""
    n = longest_side
    return (
        f"scale='if(gt(iw,ih),{n},-2)':'if(gt(iw,ih),-2,{n})'"
    )


# --- Worker thread -----------------------------------------------------------

class ProxyWorkerThread(QThread):
    """
    Encodes a list of video files as ProRes proxy media.
    Files are processed strictly one at a time (queue).
    Real ffmpeg -progress output is parsed for per-frame progress.
    """

    queue_started   = Signal(int)            # total file count
    file_started    = Signal(int, str)       # file_index (1-based), filename
    file_progress   = Signal(int, int, float)  # file_index, percent 0-100, fps
    file_completed  = Signal(int, str, str)  # file_index, source_path, output_path
    file_failed     = Signal(int, str, str)  # file_index, source_path, error_msg
    queue_completed = Signal(int, int)       # completed_count, failed_count

    def __init__(
        self,
        file_paths: List[str],
        codec_name: str,
        longest_side: int,
        parent=None,
    ):
        super().__init__(parent)
        self.file_paths   = file_paths
        self.codec_name   = codec_name
        self.longest_side = longest_side
        self._process     = None
        self._cancelled   = False

    def cancel(self):
        """Request cancellation. Terminates the current ffmpeg process if running."""
        self._cancelled = True
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception:
                pass

    def run(self):
        total = len(self.file_paths)
        self.queue_started.emit(total)

        codec_profile = PROXY_CODECS[self.codec_name]["profile"]
        completed = 0
        failed    = 0

        for idx, source_path in enumerate(self.file_paths, start=1):
            if self._cancelled:
                self.file_failed.emit(idx, source_path, "Cancelled")
                failed += 1
                continue

            filename = os.path.basename(source_path)
            self.file_started.emit(idx, filename)
            logger.info(f"[PROXY] [{idx}/{total}] Starting: {source_path}")

            try:
                output_path  = get_proxy_output_path(source_path, self.longest_side, self.codec_name)
                total_frames = get_video_frame_count(source_path)
                scale_filter = _build_scale_filter(self.longest_side)

                cmd = [
                    "ffmpeg", "-y",
                    "-i", source_path,
                    "-c:v", "prores_ks",
                    "-profile:v", codec_profile,
                    "-vendor", "apl0",
                    "-pix_fmt", "yuv422p10le",
                    "-c:a", "pcm_s16le",
                    "-vf", scale_filter,
                    "-progress", "pipe:1",
                    "-nostats",
                    output_path,
                ]

                # stderr goes to a temp file to avoid deadlocks while reading stdout
                with tempfile.TemporaryFile(mode="w+", suffix=".log") as stderr_tmp:
                    self._process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=stderr_tmp,
                        text=True,
                        bufsize=1,
                    )

                    current_frame = 0
                    current_fps   = 0.0

                    for line in self._process.stdout:
                        if self._cancelled:
                            self._process.terminate()
                            break

                        line = line.strip()
                        if "=" not in line:
                            continue
                        key, _, val = line.partition("=")
                        if key == "frame":
                            try:
                                current_frame = int(val)
                            except ValueError:
                                pass
                        elif key == "fps":
                            try:
                                v = float(val)
                                if v > 0:
                                    current_fps = v
                            except ValueError:
                                pass

                        percent = (
                            min(100, int(current_frame / total_frames * 100))
                            if total_frames > 0 else 0
                        )
                        self.file_progress.emit(idx, percent, current_fps)

                    self._process.wait()

                    if self._cancelled:
                        logger.warning(f"[PROXY] Cancelled: {source_path}")
                        self.file_failed.emit(idx, source_path, "Cancelled by user")
                        failed += 1
                    elif self._process.returncode == 0:
                        self.file_progress.emit(idx, 100, current_fps)
                        logger.info(f"[PROXY] [{idx}/{total}] Done → {output_path}")
                        self.file_completed.emit(idx, source_path, output_path)
                        completed += 1
                    else:
                        stderr_tmp.seek(0)
                        err_text = stderr_tmp.read()
                        last_err = "\n".join(err_text.splitlines()[-6:])
                        logger.error(f"[PROXY] Failed [{idx}]: {last_err}")
                        self.file_failed.emit(idx, source_path, last_err)
                        failed += 1

            except Exception as exc:
                logger.error(f"[PROXY] Exception on '{source_path}': {exc}")
                self.file_failed.emit(idx, source_path, str(exc))
                failed += 1

        self.queue_completed.emit(completed, failed)
