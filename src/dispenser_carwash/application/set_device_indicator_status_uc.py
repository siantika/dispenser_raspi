from abc import ABC, abstractmethod
from typing import Optional

from dispenser_carwash.domain.interfaces.hardware.i_output_bool import IOutputBool


class DeviceIndicatorStatus(ABC):
    """Base class untuk status indikator (non-blocking)."""

    def __init__(self, driver: IOutputBool):
        self.driver = driver

    @abstractmethod
    def execute(self, now: float) -> None:
        """
        Dipanggil berkala oleh worker.
        Tidak boleh blocking (tidak pakai sleep).
        """
        ...


class ShutDown(DeviceIndicatorStatus):
    def execute(self, now: float) -> None:
        self.driver.turn_off()


class Fine(DeviceIndicatorStatus):
    def execute(self, now: float) -> None:
        self.driver.turn_on()


class _BlinkStatus(DeviceIndicatorStatus):
    """Base untuk status blink (error)."""

    def __init__(self, driver: IOutputBool, interval: float):
        """
        interval: detik antara toggle LED
        """
        super().__init__(driver)
        self.interval = interval
        self._last_toggle: Optional[float] = None
        self._is_on: bool = False

    def execute(self, now: float) -> None:
        # set initial value
        if self._last_toggle is None:
            self._last_toggle = now
            self._is_on = True
            self.driver.turn_on()
            return

        # hanya toggle kalau sudah cukup lama
        if now - self._last_toggle >= self.interval:
            self._is_on = not self._is_on
            if self._is_on:
                self.driver.turn_on()
            else:
                self.driver.turn_off()
            self._last_toggle = now


class NetworkError(_BlinkStatus):
    """Blink pelan → error network."""
    def __init__(self, driver: IOutputBool):
        super().__init__(driver, interval=0.5)  # 0.5 detik


class PrinterError(_BlinkStatus):
    """Blink cepat → error printer."""
    def __init__(self, driver: IOutputBool):
        super().__init__(driver, interval=0.2)  # 0.2 detik
