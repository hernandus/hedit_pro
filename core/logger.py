"""
Centralized Logging Subsystem for Hedit Pro.
Logs application lifecycle, engine state, media operations, timeline events, and export rendering to console and log files inside /logs.
"""

import os
import sys
import logging
import platform
from datetime import datetime

# Project root directory and logs folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

SESSION_LOG_FILE = os.path.join(LOG_DIR, f"hedit_pro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
LATEST_LOG_FILE = os.path.join(LOG_DIR, "hedit_pro_latest.log")


class HeditLogger:
    """Thread-safe application logger manager."""

    _logger = None
    _is_configured = False

    @classmethod
    def get_logger(cls) -> logging.Logger:
        if not cls._is_configured:
            cls.setup_logging()
        return cls._logger

    @classmethod
    def setup_logging(cls):
        if cls._is_configured:
            return

        cls._logger = logging.getLogger("HeditPro")
        cls._logger.setLevel(logging.DEBUG)
        cls._logger.handlers.clear()

        formatter = logging.Formatter(
            "[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(threadName)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File Handler (Session log inside project /logs)
        file_handler = logging.FileHandler(SESSION_LOG_FILE, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # File Handler (Latest log inside project /logs)
        latest_handler = logging.FileHandler(LATEST_LOG_FILE, mode="w", encoding="utf-8")
        latest_handler.setLevel(logging.DEBUG)
        latest_handler.setFormatter(formatter)

        # Console Handler (Stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        cls._logger.addHandler(file_handler)
        cls._logger.addHandler(latest_handler)
        cls._logger.addHandler(console_handler)
        cls._is_configured = True

        cls._logger.info("==================================================")
        cls._logger.info(" HEDIT PRO NLE - APPLICATION SESSION STARTED")
        cls._logger.info(f" Time: {datetime.now().isoformat()}")
        cls._logger.info(f" System OS: {platform.system()} {platform.release()} ({platform.machine()})")
        cls._logger.info(f" Python Executable: {sys.executable} ({platform.python_version()})")
        cls._logger.info(f" Project Log File: {SESSION_LOG_FILE}")
        cls._logger.info("==================================================")

    @classmethod
    def shutdown(cls):
        if cls._logger:
            cls._logger.info("Hedit Pro application shutting down cleanly.")
            cls._logger.info("==================================================")
            logging.shutdown()


def get_logger() -> logging.Logger:
    return HeditLogger.get_logger()
