from pathlib import Path

class Settings:
    BASE_DIR = Path(__file__).resolve().parent.parent

    class Hardware:
        GPIO_MODE = "BCM"
        BUTTON_PINS = {"service_1": 17, "service_2": 27, "service_3": 22, "service_4": 23}
        LED_PINS = {"ready": 5, "processing": 6, "error": 13}

    class Server:
        URL = "https://example.com/api/parking"
        TIMEOUT = 5
        RETRY_INTERVAL = 3

    class System:
        LOGGER_NAME = "dispenser_parkir"
        LOG_LEVEL = "INFO"
        LOG_FILE = Path(__file__).resolve().parent.parent/"log.txt"

    class Interval:
        SENSOR_POLL = 0.1
        UPLOAD = 5
