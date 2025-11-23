import multiprocessing as mp
import os
import signal
import sys
from pathlib import Path
from typing import Dict

import pygame
from gpiozero import LED, Button, Device

from dispenser_carwash.config.settings import FilePath, Settings
from dispenser_carwash.hardware.input_bool import InputGpio
from dispenser_carwash.hardware.out_bool import OutputGpio
from dispenser_carwash.hardware.printer import UsbEscposDriver
from dispenser_carwash.hardware.sound import PyGameSound
from dispenser_carwash.processes.main_process import (
    MainFSM,
    MainProcess,
    NetworkManager,
    Peripheral,
)
from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)

PID_FILE = "/tmp/dispenser_carwash.pid"


# =====================================================
#  Single instance guard (biar gak jalan dobel)
# =====================================================
def ensure_single_instance():
    if os.path.exists(PID_FILE):
        logger.error("⚠ Program sudah berjalan (pidfile ada). Keluar.")
        sys.exit(1)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    logger.info(f"📌 PID file dibuat: {PID_FILE}")


def remove_pidfile():
    try:
        os.remove(PID_FILE)
        logger.info("🧹 PID file dihapus")
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.error(f"❌ Gagal hapus pidfile: {e}")



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

# =====================================================
#  Setup peripheral
# =====================================================
def setup_peripheral() -> Peripheral:
    """
    Inisialisasi semua perangkat keras.
    Sesuaikan pin / device dengan hardware aslinya.
    """
    periph = Peripheral()

    # ==== INPUT ====
    loop_pin = Settings.Hardware.LOOP_SENSOR_PIN
    loop_button = Button(pin=loop_pin)

    button_pins = Settings.Hardware.BUTTON_PINS  # diasumsikan dict
    service_1_btn = Button(pin=button_pins.get("service_1"))
    service_2_btn = Button(pin=button_pins.get("service_2"))
    service_3_btn = Button(pin=button_pins.get("service_3"))
    service_4_btn = Button(pin=button_pins.get("service_4"))

    periph.input_loop = InputGpio(loop_button)
    periph.service_1 = InputGpio(service_1_btn)
    periph.service_2 = InputGpio(service_2_btn)
    periph.service_3 = InputGpio(service_3_btn)
    periph.service_4 = InputGpio(service_4_btn)

    # ==== OUTPUT ====
    gate_pin = Settings.Hardware.GATE_CONTROLLER_PIN
    gate_led = LED(pin=gate_pin)

    led_pin = Settings.Hardware.LED_PINS  # kalau dict, ganti sesuai
    status_led = LED(pin=led_pin)

    periph.gate_controller = OutputGpio(gate_led)
    periph.indicator_status = OutputGpio(status_led)
    logger.info("GPIO init ")

    # # ==== PRINTER & SOUND ====
    # pygame.mixer.init()

    # periph.printer = UsbEscposDriver(vid=0x28E9, pid=0x0289)
    # periph.sound = PyGameSound(pygame)

    # sound_files = FilePath.get_sounds()
    # periph.sound.load_many(sound_files)
    
    # try:
    #     sound_files = get_sound()
    #     periph.sound.load_many(sound_files)
    # except Exception:
    #     logger.exception("Failed to intialize sounds")
    
    # logger.info("SOund init ")

    return periph


# =====================================================
#  Cleanup peripheral & resource
# =====================================================
def cleanup_peripheral(periph: Peripheral | None):
    logger.info("🔻 Cleanup peripheral & GPIO...")
    if periph is None:
        return

    # Tutup input/output wrapper kalau punya .close()
    for attr_name in [
        "input_loop",
        "service_1",
        "service_2",
        "service_3",
        "service_4",
        "gate_controller",
        "indicator_status",
    ]:
        dev = getattr(periph, attr_name, None)
        if dev is None:
            continue

        try:
            # Kalau wrapper punya .close()
            if hasattr(dev, "close") and callable(getattr(dev, "close")):
                dev.close()
        except Exception as e:
            logger.error(f"❌ Gagal close {attr_name}: {e}")

    # Printer
    try:
        printer = getattr(periph, "printer", None)
        if printer and hasattr(printer, "close"):
            printer.close()
    except Exception as e:
        logger.error(f"❌ Gagal close printer: {e}")

    # Sound / pygame
    try:
        snd = getattr(periph, "sound", None)
        if snd and hasattr(snd, "stop"):
            snd.stop()
    except Exception as e:
        logger.error(f"❌ Gagal stop sound: {e}")

    try:
        if pygame.mixer.get_init():
            pygame.mixer.quit()
            logger.info("🔇 pygame.mixer.quit() dipanggil")
    except Exception as e:
        logger.error(f"❌ Gagal quit mixer: {e}")

    # Tutup semua pin gpiozero
    try:
        Device.pin_factory.close()
        logger.info("📴 Device.pin_factory.close() dipanggil (GPIO released)")
    except Exception as e:
        logger.error(f"❌ Gagal close pin_factory: {e}")


# =====================================================
#  Network process
# =====================================================
def network_process(net: NetworkManager, to_net: mp.Queue, from_net: mp.Queue):
    REQUIRED_KEYS = {"ticket_number", "time_in", "service_name", "price"}

    while True:
        payload = to_net.get()

        if payload == "__STOP__":
            logger.info("🛑 Network process stopping...")
            break

        if not isinstance(payload, dict):
            logger.error(f"❌ Payload bukan dict: {payload}")
            continue

        missing_keys = REQUIRED_KEYS - payload.keys()
        if missing_keys:
            logger.error(f"⚠ Payload kurang key: {missing_keys} -> {payload}")
            continue

        if any(v in (None, "") for v in payload.values()):
            logger.warning(f"⚠ Ada data None/kosong: {payload}")

        try:
            logger.info(f"📡 Mengirim ke server: {payload}")
            net.send_data(payload)
            logger.info(net.get_last_response())
        except Exception as e:
            logger.error(f"🚨 Gagal kirim data ke server: {e}")
            from_net.put({"status": "error", "detail": str(e)})


# =====================================================
#  Main
# =====================================================
def main():
    # Biar gak jalan dobel
    ensure_single_instance()

    to_net: mp.Queue = mp.Queue()
    from_net: mp.Queue = mp.Queue()
    lock = mp.Lock()

    periph: Peripheral | None = None
    net_proc: mp.Process | None = None

    # Handler SIGTERM (kalau nanti kamu pakai systemd)
    def handle_sigterm(signum, frame):
        logger.info("⚠ SIGTERM diterima, keluar dengan rapi...")
        # biar finally tetap jalan, kita raise KeyboardInterrupt saja
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, handle_sigterm)
    
    logger.info("Ini mau ini MainFSM")

    try:
        periph = setup_peripheral()
        fsm = MainFSM()

        main_process = MainProcess(
            to_net=to_net,
            from_net=from_net,
            lock=lock,
            periph=periph,
            fsm=fsm,
        )

        network = NetworkManager(Settings.Server.SEND_URL)

        net_proc = mp.Process(
            target=network_process,
            args=(network, to_net, from_net),
            daemon=False,  # biar bisa kita join di finally
        )
        net_proc.start()

        logger.info("🚗 Dispenser carwash starting...")
        main_process.run()

    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user (KeyboardInterrupt)")

    except Exception as e:
        logger.exception(f"❗ Unhandled error in main: {e}")

    finally:
        logger.info("🧹 FINALIZE: cleanup mulai...")

        # Hentikan network process
        try:
            if net_proc is not None and net_proc.is_alive():
                to_net.put("__STOP__")
                net_proc.join(timeout=2)
                if net_proc.is_alive():
                    logger.warning("⚠ Network process masih hidup, terminate paksa")
                    net_proc.terminate()
        except Exception as e:
            logger.error(f"❌ Error saat stop network process: {e}")

        # Bersihkan peripheral & GPIO
        cleanup_peripheral(periph)

        # Hapus pidfile
        remove_pidfile()

        logger.info("✅ Cleanup selesai, exit.")


if __name__ == "__main__":
    main()
