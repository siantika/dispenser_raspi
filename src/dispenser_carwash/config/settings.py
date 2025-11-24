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
        LOOP_SENSOR_PIN = 5
        BUTTON_PINS = {
            "service_1": 6,
            "service_2": 13,
            "service_3": 19,
            "service_4": 26,
        }
        GATE_CONTROLLER_PIN = 24 
        LED_PINS = 23

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
