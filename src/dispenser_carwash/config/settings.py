import os
from pathlib import Path

# Directory of main.py
BASE_DIR = Path(__file__).resolve().parent

# Go two levels up to project root
PROJECT_ROOT = BASE_DIR.parent.parent.parent

# Path to the sounds folder
SOUNDS_DIR = os.path.join(PROJECT_ROOT, "assets", "sounds")

print("Sounds folder path:", SOUNDS_DIR)


class Settings:
    class Hardware:
        GPIO_MODE = "BCM"
        BUTTON_PINS = {
            "service_1": 17,
            "service_2": 27,
            "service_3": 22,
            "service_4": 23,
        }
        LED_PINS = {"ready": 5, "processing": 6, "error": 13}

    class Server:
        URL = "https://example.com/api/parking"
        TIMEOUT = 5
        RETRY_INTERVAL = 3

    class System:
        LOGGER_NAME = "dispenser_parkir"
        LOG_LEVEL = "INFO"
        LOG_FILE = Path(__file__).resolve().parent.parent / "log.txt"

    class Interval:
        SENSOR_POLL = 0.1
        UPLOAD = 5
