"""
Core MLT Engine context and profile manager for Hedit Pro.
Handles initialisation, profile configuration (1080p 60fps / 4K), and MLT factory wrappers.
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format="[HeditPro Engine] %(levelname)s: %(message)s")

HAS_MLT = False
mlt = None

try:
    import mlt
    HAS_MLT = True
    logging.info("MLT Framework Python bindings successfully loaded.")
except ImportError:
    logging.warning("MLT Python module ('mlt') not found. Engine running in simulated/UI preview mode.")


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
                    logging.info("MLT Factory initialized successfully.")
                    # Default Profile: 1080p 60fps
                    self.profile = mlt.Profile("atsc_1080p_60")
                else:
                    logging.error("Failed to initialize MLT Factory.")
            except Exception as e:
                logging.error(f"Error initializing MLT Engine: {e}")
        else:
            logging.info("MLT Engine initialized in Fallback Mode.")

    def set_profile(self, profile_name: str = "atsc_1080p_60"):
        """Change current MLT Profile (e.g. 'atsc_1080p_60', 'atsc_1080p_2997', 'hdv_720_50p')."""
        if HAS_MLT and self.factory_active:
            try:
                self.profile = mlt.Profile(profile_name)
                logging.info(f"MLT Profile set to: {profile_name}")
            except Exception as e:
                logging.error(f"Failed to set profile '{profile_name}': {e}")

    def is_available(self) -> bool:
        """Returns True if MLT framework is fully active and loaded."""
        return HAS_MLT and self.factory_active

    def close(self):
        """Shutdown MLT Factory cleanly on app exit."""
        if HAS_MLT and self.factory_active:
            try:
                mlt.Factory.close()
                self.factory_active = False
                logging.info("MLT Factory closed cleanly.")
            except Exception as e:
                logging.error(f"Error closing MLT Factory: {e}")
