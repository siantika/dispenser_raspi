import multiprocessing as mp
import time
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional

import requests

from dispenser_carwash.config.settings import Settings
from dispenser_carwash.hardware.input_bool import InputBool
from dispenser_carwash.hardware.out_bool import OutputBool
from dispenser_carwash.hardware.printer import PrinterDriver, PrinterUnavailable
from dispenser_carwash.hardware.sound import Sound
from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)

""" Uji sistem crash : eg printer dicabut atau koneksi mati.
Untuk sekarang coba satu thread (net work di thread ini).
button juga dicek saat noise
"""

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
    VEHICLE_STAYING = auto()
    
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
    VEHICLE_ENTER = auto()

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
            (State.GATE_OPEN, Event.GATE_OPENED): State.VEHICLE_STAYING,
            (State.VEHICLE_STAYING, Event.VEHICLE_ENTER): State.IDLE,
            
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
    def print_ticket(driver: PrinterDriver, data: Dict[str, Any]) -> bool:
        """
        Struktur data yang benar:
        data = {
            "ticket_number": "1234567890123",   # EAN13 (13 digit)
            "time_in": "2025-11-20 15:45:01",
            "service_name": "Complete",
            "price": "25000"
        }
        """
        
        try:

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
            driver.set(font="b", bold=False, width=1, height=1, align="center")
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
            driver.text("\n")

            # ============================
            # Nama paket
            # ============================
            driver.set(font="b", bold=True, width=2, height=2, align="center")
            driver.text(str(data["service_name"]))
            driver.text("\n")

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
            return True
        
        except PrinterUnavailable as e:
            # Di sini program TIDAK crash, hanya log error.
            logger.error(f"❌ Gagal print tiket (printer tidak siap): {e}")
            # Di sini kamu bisa:
            # - nyalakan LED error
            # - kirim status ke network
            # - simpan state "tiket belum tercetak"
            # Tapi jangan raise lagi kalau memang ingin program tetap jalan.
            return False
        
        except Exception as e:
            logger.error(f"error: {e}")
            return False

class BaseRequester:
    """
    Kelas dasar untuk handle:
    - retry
    - delay
    - logging
    - parsing JSON -> dict
    """

    def __init__(self, retries: int = 3, delay: int = 2):
        self._retries = retries
        self._delay = delay

    def _request_json(
        self,
        label: str,
        method: str,
        url: str,
        timeout: int = 5,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        method: "GET" / "POST" / dst
        label : nama operasi untuk log (misal: 'init data', 'send data')
        url   : endpoint
        kwargs: diteruskan ke requests.request (json=..., data=..., params=..., dll)
        """
        for attempt in range(1, self._retries + 1):
            try:
                logger.info(
                    f"🔄 {label} (attempt {attempt}/{self._retries})..."
                )

                response = requests.request(
                    method=method.upper(),
                    url=url,
                    timeout=timeout,
                    **kwargs,
                )
                response.raise_for_status()

                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("Response JSON harus berupa dict")

                logger.info(f"✔ {label} berhasil")
                return data

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠ {label} - Koneksi gagal: {e}")
            except requests.exceptions.HTTPError as e:
                logger.warning(f"🚨 {label} - HTTP Error: {e}")
            except (requests.exceptions.JSONDecodeError, ValueError) as e:
                logger.warning(f"⚠ {label} - Response tidak valid: {e}")
            except Exception as e:
                logger.warning(f"❗ {label} - Error tak terduga: {e}")

            if attempt < self._retries:
                logger.info(f"⏳ {label} - Retry dalam {self._delay} detik...")
                time.sleep(self._delay)

        logger.error(f"❌ {label} - Gagal setelah semua percobaan")
        return None


class InitData(BaseRequester):
    def __init__(
        self,
        url: str,
        retries: int = 3,
        delay: int = 2,
    ):
        """
        Init data dari endpoint:
        - last_ticket_number
        - service_data
        """
        super().__init__(retries=retries, delay=delay)

        self._url = url
        self._data: Optional[Dict[str, Any]] = None

        # langsung fetch saat inisialisasi
        self._fetch_init_data()

    def _fetch_init_data(self) -> None:
        data = self._request_json(
            label="Fetch init data",
            method="GET",
            url=self._url,
        )
        self._data = data  # bisa None kalau gagal

    def get_last_ticket_number(self) -> Optional[int]:
        if self._data and "last_ticket_number" in self._data:
            return self._data["last_ticket_number"]
        logger.warning("⚠ last_ticket_number tidak tersedia")
        return None

    def get_service_data(self) -> Optional[list]:
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


class NetworkManager(BaseRequester):
    def __init__(
        self,
        url: str,
        retries: int = 3,
        delay: int = 2,
    ):
        """
        Kirim data ke server dengan POST + retry.
        """
        super().__init__(retries=retries, delay=delay)

        self._url = url
        self._last_response: Optional[Dict[str, Any]] = None

    def send_data(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Kirim payload ke server.
        Return:
            dict -> response JSON
            None -> kalau gagal
        """
        data = self._request_json(
            label="Kirim data ke server",
            method="POST",
            url=self._url,
            json=payload,  # ganti ke data=payload kalau server pakai form-url-encoded
        )
        self._last_response = data
        return data

    def get_last_response(self) -> Optional[Dict[str, Any]]:
        if self._last_response is None:
            logger.warning("⚠ Belum ada response yang tersimpan")
        return self._last_response

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
        self._init_data = InitData(Settings.Server.INIT_DATA_URL)
        self._network = NetworkManager(Settings.Server.SEND_URL)

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
                self._periph.sound.stop()
                self._periph.gate_controller.turn_off()
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
            if self._fsm.state == State.SELECTING_SERVICE and self._selected_service is None:
                # Jika mobil keluar dan tidak jadi pilih servis
                if not loop_active:
                    self._fsm.trigger(Event.LEAVE_WITHOUT_SELECTING)
                else:
                    if self._periph.service_1.read_input():
                        self._selected_service = Utils.get_service(self._service_data, 1)
                        self._periph.sound.stop()
                        self._periph.sound.play("service_basic")
                    elif self._periph.service_2.read_input():
                        self._selected_service = Utils.get_service(self._service_data, 2)
                        self._periph.sound.stop()
                        self._periph.sound.play("service_complete")
                    elif self._periph.service_3.read_input():
                        self._selected_service = Utils.get_service(self._service_data, 3)
                        self._periph.sound.stop()
                        self._periph.sound.play("service_perfect")
                    elif self._periph.service_4.read_input():
                        self._selected_service = Utils.get_service(self._service_data, 4)
                        self._periph.sound.stop()
                        self._periph.sound.play("service_cuci_motor")

            # Hanya sekali trigger SERVICE_SELECTED (saat masih di SELECTING_SERVICE)
            if self._selected_service is not None and self._fsm.state == State.SELECTING_SERVICE:
                if not self._periph.sound.is_busy():
                    self._periph.sound.stop()
                    self._fsm.trigger(Event.SERVICE_SELECTED)
                else:
                    logger.info(f"suara sedang: {self._periph.sound.is_busy()}")
                
                
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
                """ Bisa pakai multiprocessing tapi sekarang single thread dulu"""
                with self._lock:
                    self._to_net.put(self._payload, timeout=5)
                self._fsm.trigger(Event.DATA_SENT)
                # if self._payload is not None:
                #     self._network.send_data(self._payload)
                #     self._fsm.trigger(Event.DATA_SENT)
                # else:
                #     logger.warning(f"Payload is None. data:{self._payload}")
                #     self._fsm.state = State.IDLE
    

            # PRINT TICKET
            if self._fsm.state == State.PRINTING_TICKET:
                ok = PrintTicket.print_ticket(self._periph.printer, self._payload)
                if not ok:
                    # misal: set indikator error, atau kirim info ke server
                    # tapi JANGAN raise Exception lagi
                    logger.warning("⚠ Tiket tidak tercetak karena printer tidak tersedia")
                self._fsm.trigger(Event.PRINT_DONE)
                
            # BUKA GATE
            if self._fsm.state == State.GATE_OPEN:
                self._periph.gate_controller.firePulse(0.5)
                self._periph.sound.stop()
                self._periph.sound.play("taking_ticket")
                self._fsm.trigger(Event.GATE_OPENED)
            
            if self._fsm.state == State.VEHICLE_STAYING:
                if not self._periph.input_loop.read_input():
                    self._fsm.trigger(Event.VEHICLE_ENTER)
                

            # Biar CPU ga 100%
            time.sleep(0.01)
