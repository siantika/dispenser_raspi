import multiprocessing as mp
from pathlib import Path
from typing import Dict

import pygame
from gpiozero import LED, Button

from dispenser_carwash.config.settings import Settings
from dispenser_carwash.hardware.input_bool import InputGpio
from dispenser_carwash.hardware.out_bool import OutputGpio
from dispenser_carwash.hardware.printer import UsbEscposDriver
from dispenser_carwash.hardware.sound import PyGameSound
from dispenser_carwash.processes.main_process import (
    MainFSM,
    MainProcess,
    Peripheral,
)
from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_sound() -> Dict[str, str]:
    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = BASE_DIR.parent.parent
    SOUNDS_DIR = PROJECT_ROOT / "assets" / "sounds"
    logger.info(f"base dir {BASE_DIR}")
    logger.info(f"project root {PROJECT_ROOT}")

    if not SOUNDS_DIR.exists() or not SOUNDS_DIR.is_dir():
        logger.error(f"🚨 Sound directory not found: {SOUNDS_DIR}")
        return {}

    sounds = {
        f.stem: str(f.resolve())
        for f in SOUNDS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in (".mp3", ".wav")
    }

    if not sounds:
        logger.warning(f"⚠ No sound files found in: {SOUNDS_DIR}")

    logger.info(f"🎵 Loaded {len(sounds)} sound files from {SOUNDS_DIR}")
    return sounds


def setup_peripheral() -> Peripheral:
    """
    Inisialisasi semua perangkat keras.
    Sesuaikan pin / device dengan hardware aslinya.
    """
    periph = Peripheral()

    # ==== INPUT ====
    # loop detector
    loop_pin = Settings.Hardware.LOOP_SENSOR_PIN
    loop_button = Button(pin=loop_pin)

    # tombol service
    button_pins = Settings.Hardware.BUTTON_PINS  # diasumsikan dict
    service_1_btn = Button(pin=button_pins.get("service_1"))
    service_2_btn = Button(pin=button_pins.get("service_2"))
    service_3_btn = Button(pin=button_pins.get("service_3"))
    service_4_btn = Button(pin=button_pins.get("service_4"))

    # bungkus ke wrapper InputGpio
    # catatan: ini mengasumsikan InputGpio menerima object Button,
    # kalau implementasi kamu maunya pin int, ganti jadi pin=loop_pin, dll.
    periph.input_loop = InputGpio(loop_button)

    periph.service_1 = InputGpio(service_1_btn)
    periph.service_2 = InputGpio(service_2_btn)
    periph.service_3 = InputGpio(service_3_btn)
    periph.service_4 = InputGpio(service_4_btn)

    # ==== OUTPUT ====
    gate_pin = Settings.Hardware.GATE_CONTROLLER_PIN
    gate_led = LED(pin=gate_pin)

    led_pins = Settings.Hardware.LED_PINS  
    status_led = LED(pin=led_pins)

    # bungkus ke wrapper OutputGpio
    # sama seperti di atas, ini mengasumsikan OutputGpio menerima object LED
    periph.gate_controller = OutputGpio(gate_led)
    periph.indicator_status = OutputGpio(status_led)

    # ==== PRINTER & SOUND ====
    pygame.mixer.init()  # kalau PyGameSound belum inisialisasi mixer di dalam

    periph.printer = UsbEscposDriver(vid=0x28e9, pid=0x0289)
    periph.sound = PyGameSound(pygame)
    sound_files = get_sound()
    periph.sound.load_many(sound_files)

    return periph


def main():
    # Kalau di Linux biasanya tidak perlu, di Windows sering perlu:
    # mp.set_start_method("spawn", force=True)

    to_net: mp.Queue = mp.Queue()
    from_net: mp.Queue = mp.Queue()
    lock = mp.Lock()

    periph = setup_peripheral()
    fsm = MainFSM()

    main_process = MainProcess(
        to_net=to_net,
        from_net=from_net,
        lock=lock,
        periph=periph,
        fsm=fsm,
    )

    logger.info("🚗 Dispenser carwash starting...")

    try:
        main_process.run()
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.exception(f"❗ Unhandled error in main: {e}")


if __name__ == "__main__":
    main()
