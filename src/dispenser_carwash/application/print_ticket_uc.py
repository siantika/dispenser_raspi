from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from dispenser_carwash.domain.entities.service_type import ServiceType
from dispenser_carwash.domain.entities.ticket import Ticket
from dispenser_carwash.domain.exception import PrinterUnavailable
from dispenser_carwash.domain.interfaces.hardware.i_printer import IPrinter
from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class PayloadToPrinter:
    ticket_number: str
    entry_time: str     
    service_name: str
    price: Decimal


def convert_to_wita(dt: datetime) -> datetime:
    """Konversi datetime ke WITA (Asia/Makassar, UTC+8)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(ZoneInfo("Asia/Makassar"))


def generate_printer_payload(ticket: Ticket,
                             service_type: ServiceType) -> PayloadToPrinter:

    dt_wita = convert_to_wita(ticket.entry_time)

    # Format tampilan untuk printer:
    formatted_time = dt_wita.strftime("%d-%m-%Y  %H:%M:%S")

    return PayloadToPrinter(
        ticket_number=ticket.ticket_number,
        entry_time=formatted_time,
        service_name=service_type.name,
        price=service_type.price
    )
    

class PrintTicketUseCase:
    def __init__(self, driver:IPrinter):
        self.driver = driver 
        
    def execute(self,  data: PayloadToPrinter) -> bool:
        """
        returns: bool -> True means printer is working, False means printer is not working.
        """
        try:
           
            # ============================
            # Header: WELCOME + nama usaha
            # ============================
            self.driver.set(font="b", bold=True, width=2, height=2, align="center")
            self.driver.text("WELCOME\n")
            self.driver.text("BALI DRIVE THRU CARWASH\n")

            # ============================
            # Alamat (font normal)
            # ============================
            self.driver.set(font="b", bold=False, width=1, height=1, align="center")
            self.driver.text("Jl. Mahendradata Selatan No.19 Denpasar, Bali\n\n")

            # ============================
            # Info waktu
            # ============================
            self.driver.set(font="b", bold=False, width=1, height=1, align="center")
            self.driver.text(str(data.entry_time))
            self.driver.text("\n")

            # ============================
            # Barcode
            # ============================
            self.driver.barcode(
                str(data.ticket_number),
                "EAN13",
                height=64,
                width=2,
                pos="BELOW"
            )
            self.driver.text("\n")

            # ============================
            # Nama paket
            # ============================
            self.driver.set(font="b", bold=True, width=2, height=2, align="center")
            self.driver.text(str(data.service_name))
            self.driver.text("\n")

            # ============================
            # Harga
            # ============================
            self.driver.set(font="b", bold=False, width=1, height=1, align="center")
            self.driver.text("Rp.")
            self.driver.text(str(data.price))
            self.driver.text("\n")

            # ============================
            # Cut kertas
            # ============================
            self.driver.cut()
            return True
        
        except PrinterUnavailable as e:
            logger.exception(f"Failed to print. Please check the printer! {e}")
            return False
        
        except Exception as e:
            logger.exception(f"Unexpected error from printer: {e}")
            return False
