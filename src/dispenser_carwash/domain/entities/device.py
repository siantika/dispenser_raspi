from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from dispenser_carwash.domain.exception import InvalidDeviceError


class DeviceStatus(Enum):
    """ for status operation """
    NET_ERROR = "NET_ERROR"
    PRINTER_ERROR = "PRINTER_ERROR"
    FINE = "FINE"
    SHUTDOWN = "SHUTDOWN"   
    

@dataclass
class Device:
    code: str                  # misal: "DSP-01-CBG"
    name: str                  # misal: "Dispenser Pintu Masuk"
    desc: str                  # misal: "Dispenser gerbang utama cabang Cibinong"
    location: str              # opsional tapi praktis: "Cibinong - Gate 1"
    model: str                 # "Raspberry Pi 3B"
    firmware_version: str      # "v1.0.0"
    registered_at: datetime    # kapan pertama kali register ke server

    def validate(self) -> bool:
        if not self.code or not self.code.strip():
            raise InvalidDeviceError("Device code cannot be empty")

        if not self.name or not self.name.strip():
            raise InvalidDeviceError("Device name cannot be empty")

        if not self.model or not self.model.strip():
            raise InvalidDeviceError("Device model cannot be empty")

        if not self.firmware_version or not self.firmware_version.strip():
            raise InvalidDeviceError("Firmware version cannot be empty")

        return True
