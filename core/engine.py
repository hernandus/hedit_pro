"""
Core MLT Engine context and profile manager for Hedit Pro.
Handles initialisation, profile configuration (1080p 60fps / 4K), and MLT factory wrappers.
"""

import sys
from core.logger import get_logger

logger = get_logger()

HAS_MLT = False
mlt = None

try:
    import mlt
    HAS_MLT = True
    logger.info("[ENGINE] MLT Framework Python bindings successfully loaded.")
except ImportError:
    logger.warning("[ENGINE] MLT Python module ('mlt') not found. Engine running in simulated/UI preview mode.")


class MLTEngine:
    """Singleton Engine Manager for MLT Factory, Profile and Global Settings."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLTEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.profile = None
        self.factory_active = False

        if HAS_MLT:
            try:
                # Initialize MLT Factory
                self.factory_active = mlt.Factory.init()
                if self.factory_active:
                    logger.info("[ENGINE] MLT Factory initialized successfully.")
                    # Default Profile: 1080p 60fps
                    self.profile = mlt.Profile("atsc_1080p_60")
                    logger.info("[ENGINE] Default MLT Profile set to 'atsc_1080p_60'.")
                else:
                    logger.error("[ENGINE] Failed to initialize MLT Factory.")
            except Exception as e:
                logger.error(f"[ENGINE] Error initializing MLT Engine: {e}")
        else:
            logger.info("[ENGINE] MLT Engine initialized in Fallback Preview Mode.")

    def set_profile(self, profile_name: str = "atsc_1080p_60"):
        """Change current MLT Profile (e.g. 'atsc_1080p_60', 'atsc_1080p_2997', 'hdv_720_50p')."""
        if HAS_MLT and self.factory_active:
            try:
                self.profile = mlt.Profile(profile_name)
                logger.info(f"[ENGINE] MLT Profile updated to: {profile_name}")
            except Exception as e:
                logger.error(f"[ENGINE] Failed to set profile '{profile_name}': {e}")

    def is_available(self) -> bool:
        """Returns True if MLT framework is fully active and loaded."""
        return HAS_MLT and self.factory_active

    def close(self):
        """Shutdown MLT Factory cleanly on app exit."""
        if HAS_MLT and self.factory_active:
            try:
                mlt.Factory.close()
                self.factory_active = False
                logger.info("[ENGINE] MLT Factory closed cleanly.")
            except Exception as e:
                logger.error(f"[ENGINE] Error closing MLT Factory: {e}")
