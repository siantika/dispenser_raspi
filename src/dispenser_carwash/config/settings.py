import os
from pathlib import Path

from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)

# # Directory of main.py
# BASE_DIR = Path(__file__).resolve().parents[2]

# # Go two levels up to project root
# PROJECT_ROOT = BASE_DIR.parents[2]

# # Path to the sounds folder
# SOUNDS_DIR = os.path.join(PROJECT_ROOT, "assets", "sounds")

class FilePath:
    CURRENT_PATH = Path(__file__).resolve()
    logger.info(f"ini Current path {CURRENT_PATH}")
    @staticmethod
    def get_base() -> Path:
        return FilePath.CURRENT_PATH.parents[2]

    @staticmethod
    def get_root() -> Path:
        return FilePath.get_base().parents[2]
    
    @staticmethod
    def get_sounds():
        sound_path = FilePath.get_root() / "assets" / "sounds"
        logger.info(f"Ini sound path{sound_path}")

        if not sound_path.exists():
            raise FileNotFoundError(f"Sound directory not found: {sound_path}")

        sounds = {
            f.stem: str(f.resolve())
            for f in sound_path.iterdir()
            if f.is_file() and f.suffix.lower() in (".mp3", ".wav")
        }
        if not sounds:
            logger.error(f"⚠ No sound files found in: {sounds}")
            raise FileNotFoundError(f"Sound files not found {sounds}")
        
        logger.info(f"🎵 Loaded {len(sounds)} sound files from {sounds}")
        return sounds


class Settings:
    class Hardware:
        GPIO_MODE = "BCM"
        LOOP_SENSOR_PIN = 5
        BUTTON_PINS = {
            "service_1": 6,
            "service_2": 13,
            "service_3": 19,
            "service_4": 26,
        }
        GATE_CONTROLLER_PIN = 23 
        LED_PINS = 24

    class Server:
        SEND_URL = "http://192.168.100.29:8000/api/tickets"
        INIT_DATA_URL = "http://192.168.100.29:8000/api/init-data"

        TIMEOUT = 5
        RETRY_INTERVAL = 3

    class System:
        LOGGER_NAME = "dispenser_parkir"
        LOG_LEVEL = "INFO"
        LOG_FILE = Path(__file__).resolve().parent.parent / "log.txt"

    class Interval:
        SENSOR_POLL = 0.1
        UPLOAD = 5
