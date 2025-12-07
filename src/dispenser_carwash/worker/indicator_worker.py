import multiprocessing as mp
import time
from queue import Empty

from dispenser_carwash.application.set_device_indicator_status_uc import (
    DeviceIndicatorStatus,
    Fine,
    NetworkError,
    PrinterError,
    ShutDown,
)
from dispenser_carwash.domain.entities.device import DeviceStatus
from dispenser_carwash.domain.interfaces.hardware.i_output_bool import IOutputBool
from dispenser_carwash.worker.dto.queue_dto import MessageKind, QueueMessage


class IndicatorWorker:
    def __init__(
        self,
        driver: IOutputBool,
        queue_in: mp.Queue,              # cuma satu queue masuk
        poll_interval: float = 0.05,
    ):
        self.driver = driver
        self.queue_in = queue_in

        self._status: DeviceIndicatorStatus = ShutDown(driver)
        self._poll_interval = poll_interval
        self._running = True

    def set_status(self, status: DeviceIndicatorStatus):
        self._status = status

    def stop(self):
        self._running = False

    def _handle_one_message(self, msg: QueueMessage) -> None:
        # Hanya respon ke EVENT
        if msg.kind != MessageKind.EVENT:
            return

        payload = msg.payload or {}
        dev_status = payload.get("device_status")
        if dev_status is None:
            return

        if dev_status == DeviceStatus.FINE:
            self.set_status(Fine(self.driver))
        elif dev_status == DeviceStatus.NET_ERROR:
            self.set_status(NetworkError(self.driver))
        elif dev_status == DeviceStatus.PRINTER_ERROR:
            self.set_status(PrinterError(self.driver))
        elif dev_status == DeviceStatus.SHUTDOWN:
            self.set_status(ShutDown(self.driver))

    def _drain_queue(self) -> None:
        """
        Drain semua pesan di queue_in sekarang.
        Tujuannya: kalau banyak EVENT, yang dipakai status terakhir.
        """
        while True:
            try:
                msg: QueueMessage = self.queue_in.get_nowait()
            except Empty:
                break
            self._handle_one_message(msg)

    def run(self):
        """
        Loop ringan:
        - baca semua pesan yang ada (non-blocking)
        - eksekusi state sekarang (non-blocking)
        - sleep sebentar
        """
        while self._running:
            now = time.monotonic()

            self._drain_queue()
            self._status.execute(now)

            time.sleep(self._poll_interval)