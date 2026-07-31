"""
Playback & Transport Controller Module for Hedit Pro.
Manages active transport targets (Source Monitor, Program Monitor),
routes shuttle commands (Space, J, K, L), and synchronizes playback state.
"""

from typing import Protocol, Optional, Any
from PySide6.QtCore import QObject, Signal
from core.logger import get_logger

logger = get_logger()


class PlaybackTarget(Protocol):
    """Protocol interface that any monitor widget must implement."""
    def toggle_play(self) -> None: ...
    def shuttle_forward(self) -> None: ...
    def shuttle_reverse(self) -> None: ...
    def shuttle_stop(self) -> None: ...
    @property
    def is_playing(self) -> bool: ...


class PlaybackController(QObject):
    """
    Central Controller for managing playback state, active monitor focus,
    and routing global transport shortcuts (Space, J, K, L).
    """

    target_changed = Signal(object)      # Emits new active PlaybackTarget
    playback_started = Signal(object)    # Emits target when playback starts
    playback_stopped = Signal(object)    # Emits target when playback stops

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_target: Optional[Any] = None
        self._target_name: str = "None"

    @property
    def active_target(self) -> Optional[Any]:
        return self._active_target

    @property
    def target_name(self) -> str:
        return self._target_name

    def set_active_target(self, target: Optional[Any], name: str = "Unknown"):
        """Set the active playback target (e.g. Source Monitor or Program Monitor)."""
        if target != self._active_target:
            # Stop playback on previous target if it was playing
            if self._active_target and getattr(self._active_target, 'is_playing', False):
                self.shuttle_stop()

            self._active_target = target
            self._target_name = name
            logger.info(f"[PLAYBACK CONTROLLER] Active playback target set to: {name}")
            self.target_changed.emit(target)

    def toggle_play(self):
        """Toggle play/pause on the active target."""
        if not self._active_target:
            logger.warning("[PLAYBACK CONTROLLER] toggle_play called with no active target.")
            return

        if hasattr(self._active_target, 'toggle_play'):
            self._active_target.toggle_play()
            if getattr(self._active_target, 'is_playing', False):
                self.playback_started.emit(self._active_target)
            else:
                self.playback_stopped.emit(self._active_target)

    def shuttle_forward(self):
        """L key: Forward shuttle on active target."""
        if self._active_target and hasattr(self._active_target, 'shuttle_forward'):
            logger.info(f"[PLAYBACK CONTROLLER] Shuttle Forward on target '{self._target_name}'.")
            self._active_target.shuttle_forward()
            self.playback_started.emit(self._active_target)

    def shuttle_reverse(self):
        """J key: Reverse shuttle on active target."""
        if self._active_target and hasattr(self._active_target, 'shuttle_reverse'):
            logger.info(f"[PLAYBACK CONTROLLER] Shuttle Reverse on target '{self._target_name}'.")
            self._active_target.shuttle_reverse()
            self.playback_started.emit(self._active_target)

    def shuttle_stop(self):
        """K key / Stop: Stop shuttle on active target."""
        if self._active_target and hasattr(self._active_target, 'shuttle_stop'):
            logger.info(f"[PLAYBACK CONTROLLER] Shuttle Stop on target '{self._target_name}'.")
            self._active_target.shuttle_stop()
            self.playback_stopped.emit(self._active_target)
