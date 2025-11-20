import multiprocessing as mp
import time
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict

import requests

from dispenser_carwash.config import settings
from dispenser_carwash.hardware.input_bool import InputBool
from dispenser_carwash.hardware.out_bool import OutputBool
from dispenser_carwash.hardware.printer import PrinterDriver
from dispenser_carwash.hardware.sound import Sound
from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)



class Peripheral:
    input_loop: InputBool
    service_1: InputBool
    service_2: InputBool
    service_3: InputBool
    service_4: InputBool
    gate_controller: OutputBool
    indicator_status: OutputBool
    printer: PrinterDriver
    sound: Sound

class State(Enum):
    IDLE = auto()
    GREETING = auto()
    SELECTING_SERVICE = auto()
    GENERATING_TICKET = auto()
    SENDING_DATA = auto()
    PRINTING_TICKET = auto()
    GATE_OPEN = auto()
    
class Event(Enum):
    ARRIVED = auto()
    LEAVE_WITHOUT_SELECTING = auto()
    TIMEOUT = auto()
    GREETING_DONE = auto()
    SERVICE_SELECTED = auto()
    TICKET_GENERATED = auto()
    DATA_SENT = auto()
    PRINT_DONE = auto()
    GATE_OPENED = auto()



class MainFSM:
    def __init__(self):
        self.state = State.IDLE
        self.transitions = {
            (State.IDLE, Event.ARRIVED): State.GREETING,
            (State.GREETING, Event.GREETING_DONE): State.SELECTING_SERVICE,
            (State.SELECTING_SERVICE, Event.SERVICE_SELECTED) : State.GENERATING_TICKET,
            (State.SELECTING_SERVICE, Event.LEAVE_WITHOUT_SELECTING) : State.IDLE,
            (State.SELECTING_SERVICE, Event.TIMEOUT) : State.IDLE,
            (State.GENERATING_TICKET, Event.TICKET_GENERATED) : State.SENDING_DATA,
            (State.SENDING_DATA, Event.DATA_SENT) : State.PRINTING_TICKET,
            (State.PRINTING_TICKET, Event.PRINT_DONE) : State.GATE_OPEN,
            (State.GATE_OPEN, Event.GATE_OPENED): State.IDLE,
        }
        
    def trigger(self, event: Event)-> None:
        key = (self.state, event)
        if  key not in self.transitions:
            logger.warning(f"⚠ Transisi tidak valid: {self.state.name} + {event.name}")
            return
            
        next_state = self.transitions[key]
        logger.info(f"{self.state.name} --({event.name})--> {next_state.name}")
        self.state = next_state



""" Utils """
class TicketGenerator:
    def __init__(self, last_barcode_number: int):
        self._last_ticket_number = last_barcode_number

    def _checksum_ean_13(self, number: str) -> int:
        """
        Hitung checksum EAN-13 untuk 12 digit input.
        """
        if len(number) != 12 or not number.isdigit():
            raise ValueError("EAN-13 checksum calculation requires exactly 12 digits")

        sum_odd = sum(int(number[i]) for i in range(0, 12, 2))      # Posisi 1,3,5,...
        sum_even = sum(int(number[i]) for i in range(1, 12, 2))     # Posisi 2,4,6,...

        checksum = (10 - ((sum_odd + 3 * sum_even) % 10)) % 10
        return checksum

    def create_ean_ticket(self, service_id: int) -> str:
        """
        Generate full 13-digit EAN code (string).
        """
        self._last_ticket_number += 1
        
        prefix = "899"  # GS1 Indonesia
        service_id_str = f"{service_id:02d}"  # Selalu 2 digit
        sequential = f"{self._last_ticket_number:07d}"  # 7 digit incremental

        raw_number = f"{prefix}{service_id_str}{sequential}"

        # Pastikan tetap 12 digit sebelum checksum
        if len(raw_number) != 12:
            raise ValueError(f"EAN base must be 12 digits, got {len(raw_number)} → {raw_number}")

        checksum = self._checksum_ean_13(raw_number)
        full_ean = f"{raw_number}{checksum}"
        return full_ean


class PrintTicket:
    @staticmethod
    def _validate_data(data: dict) -> None:
        required = {"ticket_number", "time_in", "service_name", "price"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"Missing keys: {missing}")

    @staticmethod
    def print_ticket(driver: PrinterDriver, data: Dict[str, Any]) -> None:
        """
        Struktur data yang benar:
        data = {
            "ticket_number": "1234567890123",   # EAN13 (13 digit)
            "time_in": "2025-11-20 15:45:01",
            "service_name": "Complete",
            "price": "25000"
        }
        """

        # 🔍 Validasi data
        PrintTicket._validate_data(data)

        # ============================
        # Header: WELCOME + nama usaha
        # ============================
        driver.set(font="b", bold=True, width=2, height=2, align="center")
        driver.text("WELCOME\n")
        driver.text("BALI DRIVE THRU CARWASH\n")

        # ============================
        # Alamat (font normal)
        # ============================
        driver.set(font="b", bold=False, width=1, height=1, align="center")
        driver.text("Jl. Mahendradata Selatan No.19 Denpasar, Bali\n\n")

        # ============================
        # Info waktu
        # ============================
        driver.set(font="b", bold=False, width=1, height=1, align="left")
        driver.text(str(data["time_in"]))
        driver.text("\n")

        # ============================
        # Barcode
        # ============================
        driver.barcode(
            str(data["ticket_number"]),
            "EAN13",
            height=64,
            width=2,
            pos="BELOW"
        )
        driver.text("\n\n")

        # ============================
        # Nama paket
        # ============================
        driver.set(font="b", bold=True, width=2, height=2, align="center")
        driver.text(str(data["service_name"]))
        driver.text("\n\n")

        # ============================
        # Harga
        # ============================
        driver.set(font="b", bold=False, width=1, height=1, align="center")
        driver.text("Rp.")
        driver.text(str(data["price"]))
        driver.text("\n")

        # ============================
        # Cut kertas
        # ============================
        driver.cut()



class InitData:
    def __init__(self, retries: int = 3, delay: int = 2):
        """
        retries -> jumlah percobaan ulang jika gagal
        delay   -> waktu tunggu (detik) antar percobaan
        """
        self._data = None
        self._retries = retries
        self._delay = delay
        self._get_init_data()

    def _get_init_data(self):
        for attempt in range(1, self._retries + 1):
            try:
                logger.info(f"🔍 Fetch init data (attempt {attempt}/{self._retries})...")
                response = requests.get(settings.INIT_DATA_URL, timeout=5)
                response.raise_for_status()

                self._data = response.json()

                if not isinstance(self._data, dict):
                    raise ValueError("Response harus dict")

                logger.info("✔ Init data berhasil diperoleh")
                return  # stop retry jika sukses

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠ Koneksi gagal: {e}")
            except requests.exceptions.HTTPError as e:
                logger.warning(f"🚨 HTTP Error: {e}")
            except (requests.exceptions.JSONDecodeError, ValueError):
                logger.warning("⚠ Response tidak valid JSON atau format tidak sesuai")
            except Exception as e:
                logger.warning(f"❗ Error tak terduga: {e}")

            if attempt < self._retries:
                logger.info(f"⏳ Retry dalam {self._delay} detik...")
                time.sleep(self._delay)

        logger.error("❌ Gagal mendapatkan init data setelah semua percobaan")
        self._data = None  # pastikan None jika gagal total

    def get_last_ticket_number(self):
        if self._data and "last_ticket_number" in self._data:
            return self._data["last_ticket_number"]
        logger.warning("⚠ last_ticket_number tidak tersedia")
        return None

    def get_service_data(self):
        if not self._data:
            logger.warning("⚠ Belum ada init data (request gagal)")
            return None

        data = self._data.get("service_data")
        if not isinstance(data, list):
            logger.warning("⚠ service_data tidak valid (harus list)")
            return None

        # Optional: cek service_id valid
        for item in data:
            if "id" not in item:
                logger.warning(f"⚠ service_data tanpa id: {item}")

        return data


class Utils:
    @staticmethod    
    def get_service(data, service_id):
        return next((item for item in data if item["id"] == service_id), None)


""" Process """        
class MainProcess:
    def __init__(self, to_net: mp.Queue, from_net: mp.Queue, lock: mp.Lock,
                 periph: Peripheral, fsm: "MainFSM"):
        self._to_net = to_net
        self._from_net = from_net
        self._service_data = None
        self._last_ticket_number = None
        self._selected_service = None
        self._payload: Dict[str, Any] = {}
        self._lock = lock
        self._periph = periph
        self._fsm = fsm
        self._ticket_gen = None 
        self._init_data = InitData()

    def run(self):
        # Ambil data awal dari server
        self._last_ticket_number = self._init_data.get_last_ticket_number()
        self._service_data = self._init_data.get_service_data()

        if self._last_ticket_number is None or self._service_data is None:
            logger.error("Init data gagal, tidak bisa menjalankan main loop")
            return

        # Sinkronkan generator dengan nomor terakhir dari server
        self._ticket_gen = TicketGenerator(self._last_ticket_number)

        while True:
            # Baca loop detector sekali per iterasi
            loop_active = self._periph.input_loop.read_input()

            # RESET kontekstual saat IDLE
            if self._fsm.state == State.IDLE:
                self._selected_service = None
                self._payload = {}

            # Deteksi kedatangan hanya dari IDLE
            if self._fsm.state == State.IDLE and loop_active:
                self._fsm.trigger(Event.ARRIVED)

            # GREETING
            if self._fsm.state == State.GREETING:
                self._periph.sound.play("welcome")
                self._fsm.trigger(Event.GREETING_DONE)

            # PEMILIHAN SERVICE
            if self._fsm.state == State.SELECTING_SERVICE:
                # Jika mobil keluar dan tidak jadi pilih servis
                if not loop_active:
                    self._fsm.trigger(Event.LEAVE_WITHOUT_SELECTING)
                else:
                    if self._periph.service_1.read_input():
                        self._selected_service = Utils.get_service(self._service_data, 1)
                        self._periph.sound.play("service_basic")
                    elif self._periph.service_2.read_input():
                        self._selected_service = Utils.get_service(self._service_data, 2)
                        self._periph.sound.play("service_complete")
                    elif self._periph.service_3.read_input():
                        self._selected_service = Utils.get_service(self._service_data, 3)
                        self._periph.sound.play("service_perfect")
                    elif self._periph.service_4.read_input():
                        self._selected_service = Utils.get_service(self._service_data, 4)
                        self._periph.sound.play("service_cuci_motor")

            # Hanya sekali trigger SERVICE_SELECTED (saat masih di SELECTING_SERVICE)
            if self._selected_service is not None and self._fsm.state == State.SELECTING_SERVICE:
                self._fsm.trigger(Event.SERVICE_SELECTED)
                

            # GENERATE TICKET
            if self._fsm.state == State.GENERATING_TICKET:
                service_id = self._selected_service.get("id")
                ticket_number = self._ticket_gen.create_ean_ticket(service_id)

                time_in = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                self._payload.update(
                    {
                        "ticket_number": ticket_number,
                        "time_in": time_in,
                        "service_name": self._selected_service.get("name"),
                        "price": self._selected_service.get("price"),
                    }
                )

                self._fsm.trigger(Event.TICKET_GENERATED)

            # KIRIM DATA KE SERVER
            if self._fsm.state == State.SENDING_DATA:
                with self._lock:
                    self._to_net.put(self._payload, timeout=3)
                self._fsm.trigger(Event.DATA_SENT)

            # PRINT TICKET
            if self._fsm.state == State.PRINTING_TICKET:
                PrintTicket.print_ticket(self._periph.printer, self._payload)
                self._fsm.trigger(Event.PRINT_DONE)

            # BUKA GATE
            if self._fsm.state == State.GATE_OPEN:
                self._periph.gate_controller.firePulse(0.5)
                self._periph.sound.stop()
                self._periph.sound.play("enter")
                self._fsm.trigger(Event.GATE_OPENED)

            # Biar CPU ga 100%
            time.sleep(0.01)
