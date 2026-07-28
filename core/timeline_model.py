"""
Timeline Data Model for Hedit Pro.
Wraps MLT Tractor / Multitrack / Playlist concepts into a pythonic sequence model.
"""

from typing import List, Dict, Optional
import os
import uuid

from core.engine import MLTEngine, HAS_MLT, mlt


class ClipItem:
    """Represents a clip placed on a timeline track."""

    def __init__(
        self,
        clip_id: str,
        name: str,
        file_path: str,
        start_frame: int,
        mark_in: int,
        mark_out: int,
        track_index: int,
        is_audio: bool = False
    ):
        self.id = clip_id
        self.name = name
        self.file_path = file_path
        self.start_frame = start_frame
        self.mark_in = mark_in
        self.mark_out = mark_out
        self.track_index = track_index
        self.is_audio = is_audio
        self.color = "#2a52be" if not is_audio else "#2e7d32" # Video blue, Audio green

    @property
    def duration(self) -> int:
        return max(1, self.mark_out - self.mark_in)

    @property
    def end_frame(self) -> int:
        return self.start_frame + self.duration


class TrackModel:
    """Represents a single track lane (e.g. V1, V2, A1, A2)."""

    def __init__(self, name: str, is_audio: bool = False):
        self.name = name
        self.is_audio = is_audio
        self.clips: List[ClipItem] = []
        self.is_muted = False
        self.is_solo = False
        self.is_locked = False

    def add_clip(self, clip: ClipItem):
        self.clips.append(clip)
        self.clips.sort(key=lambda c: c.start_frame)

    def remove_clip(self, clip_id: str) -> Optional[ClipItem]:
        for i, c in enumerate(self.clips):
            if c.id == clip_id:
                return self.clips.pop(i)
        return None

    def get_clip_at(self, frame: int) -> Optional[ClipItem]:
        for c in self.clips:
            if c.start_frame <= frame < c.end_frame:
                return c
        return None


class SequenceModel:
    """Main Sequence Model managing multiple video & audio tracks, playhead, and snapping."""

    def __init__(self, name: str = "Main Sequence", fps: float = 60.0):
        self.name = name
        self.fps = fps
        self.playhead_frame = 0

        # Video tracks (V3, V2, V1) and Audio tracks (A1, A2, A3)
        self.video_tracks = [
            TrackModel("V3"),
            TrackModel("V2"),
            TrackModel("V1"),
        ]
        self.audio_tracks = [
            TrackModel("A1", is_audio=True),
            TrackModel("A2", is_audio=True),
            TrackModel("A3", is_audio=True),
        ]

        # MLT Tractor instance
        self.engine = MLTEngine()
        self.tractor = None
        self.multitrack = None
        self._init_mlt_sequence()

    def _init_mlt_sequence(self):
        if HAS_MLT and self.engine.is_available():
            try:
                profile = self.engine.profile or mlt.Profile("atsc_1080p_60")
                self.tractor = mlt.Tractor(profile)
                self.multitrack = self.tractor.multitrack()
            except Exception as e:
                print(f"[TimelineModel] Error initializing MLT Tractor: {e}")

    def add_clip_to_track(
        self,
        file_path: str,
        start_frame: int,
        mark_in: int,
        mark_out: int,
        track_index: int = 2, # V1 track by default
        is_audio: bool = False
    ) -> ClipItem:
        clip_id = str(uuid.uuid4())[:8]
        name = os.path.basename(file_path)
        clip = ClipItem(
            clip_id=clip_id,
            name=name,
            file_path=file_path,
            start_frame=start_frame,
            mark_in=mark_in,
            mark_out=mark_out,
            track_index=track_index,
            is_audio=is_audio
        )

        tracks = self.audio_tracks if is_audio else self.video_tracks
        if 0 <= track_index < len(tracks):
            tracks[track_index].add_clip(clip)

        return clip

    def razor_clip_at(self, track_index: int, frame: int, is_audio: bool = False) -> bool:
        """Split a clip at the given frame position (Razor Tool 'C')."""
        tracks = self.audio_tracks if is_audio else self.video_tracks
        if not (0 <= track_index < len(tracks)):
            return False

        track = tracks[track_index]
        clip = track.get_clip_at(frame)
        if not clip or frame <= clip.start_frame or frame >= clip.end_frame:
            return False

        # Split frame offset inside clip
        split_offset = frame - clip.start_frame

        # Clip 1 right mark_out
        orig_out = clip.mark_out
        clip.mark_out = clip.mark_in + split_offset

        # Clip 2 left mark_in & start_frame
        clip2_id = str(uuid.uuid4())[:8]
        clip2 = ClipItem(
            clip_id=clip2_id,
            name=f"{clip.name}_cut",
            file_path=clip.file_path,
            start_frame=frame,
            mark_in=clip.mark_in + split_offset,
            mark_out=orig_out,
            track_index=track_index,
            is_audio=is_audio
        )
        track.add_clip(clip2)
        return True

    def get_snap_points(self, tolerance_frames: int = 5) -> List[int]:
        """Returns all magnetic snap frames (clip start/end edges, 0, playhead)."""
        snaps = {0, self.playhead_frame}
        for track in self.video_tracks + self.audio_tracks:
            for c in track.clips:
                snaps.add(c.start_frame)
                snaps.add(c.end_frame)
        return sorted(list(snaps))

    def snap_frame(self, target_frame: int, tolerance_frames: int = 5) -> int:
        """Find closest snap point within tolerance."""
        points = self.get_snap_points(tolerance_frames)
        best_point = target_frame
        min_diff = tolerance_frames + 1

        for p in points:
            diff = abs(p - target_frame)
            if diff <= tolerance_frames and diff < min_diff:
                min_diff = diff
                best_point = p

        return best_point
