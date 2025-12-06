from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from dispenser_carwash.domain.entities.service_type import ServiceType
from dispenser_carwash.domain.entities.ticket import Ticket

# UTC+8 (WITA)
WITA = timezone(timedelta(hours=8))


@dataclass 
class PayloadToPrinter:
    ticket_number: str
    entry_time: datetime  # UTC
    service_name: str
    price: str

def convert_time_to_wita(time:datetime) -> str:
    """
    Convert entry_time from UTC to WITA timezone
    and format into 'dd-mm-YYYY HH:MM' for printing.
    """
    local_dt = time.astimezone(WITA)
    return local_dt.strftime("%d-%m-%Y %H:%M:%S")
    

def generate_printer_payload(payload:Ticket, service_type:ServiceType)->PayloadToPrinter:
    return PayloadToPrinter(
        ticket_number = payload.ticket_number,
        entry_time = convert_time_to_wita(payload.entry_time),
        service_name = service_type.name,
        price = service_type.price         
    )
    