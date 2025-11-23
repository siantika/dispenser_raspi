from pathlib import Path

from dispenser_carwash.utils.logger import setup_logger

# # Directory of main.py
# BASE_DIR = Path(__file__).resolve().parent

# # Go two levels up to project root
# PROJECT_ROOT = BASE_DIR.parent.parent.parent

# # Path to the sounds folder
# # SOUNDS_DIR = os.path.join(PROJECT_ROOT, "assets", "sounds")

# print("Sounds folder path:", SOUNDS_DIR)

logger = setup_logger(__name__)
from pathlib import Path
from typing import Dict

logger = setup_logger(__name__)

class FilePath:
    CURRENT_PATH = Path(__file__).resolve().parent

    @staticmethod
    def get_base() -> Path:
        return FilePath.CURRENT_PATH
    
    @staticmethod
    def get_root() -> Path:
        """ index 0 is count"""
        return FilePath.get_base().parents[2]
    
    @staticmethod
    def get_sounds() -> Dict[str, str]:
        SOUNDS_DIR = FilePath.get_root()/ "assets"/ "sounds"
        print(SOUNDS_DIR)
        if not SOUNDS_DIR.exists() or not SOUNDS_DIR.is_dir():
            logger.error(f"🚨 Sound directory not found: {SOUNDS_DIR}")
            raise FileNotFoundError("Sound dir is not exist!")

        sounds = {
            f.stem: str(f.resolve())
            for f in SOUNDS_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in (".mp3", ".wav")
        }

        if not sounds:
            print(f"⚠ No sound files found in: {SOUNDS_DIR}")

        print(f"🎵 Loaded {len(sounds)} sound files from {SOUNDS_DIR}")
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
