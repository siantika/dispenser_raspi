import multiprocessing as mp
import time

from dispenser_carwash.application.get_initial_data import GetInitialDataUseCase
from dispenser_carwash.application.register_ticket_uc import RegisterTicketUseCase
from dispenser_carwash.domain.entities.device import DeviceStatus
from dispenser_carwash.domain.entities.ticket import Ticket
from dispenser_carwash.worker.dto.queue_dto import (
    MessageKind,
    QueueMessage,
    QueueTopic,
)


class NetworkWorker:
    def __init__(
        self,
        register_ticket_uc: RegisterTicketUseCase,
        get_initial_data_uc: GetInitialDataUseCase,
        to_primary: mp.Queue,
        from_primary: mp.Queue,
        to_indicator: mp.Queue,
        poll_interval: float = 0.05,
    ):
        self.reg_ticket_uc = register_ticket_uc
        self.get_init_data_uc = get_initial_data_uc
        self.queue_to_primary = to_primary
        self.queue_from_primary = from_primary
        self.queue_to_indicator = to_indicator
        self._poll_interval = poll_interval
        self._running = True

    def stop(self) -> None:
        self._running = False

    # ------------ queue handling ------------ #

    def _handle_one_message(self, msg: QueueMessage) -> None:
        # hanya proses message untuk NETWORK
        if msg.topic != QueueTopic.NETWORK:
            return

        if msg.kind == MessageKind.EVENT:
            self._handle_event(msg)
        elif msg.kind == MessageKind.COMMAND:
            self._handle_command(msg)
        # RESPONSE biasanya dari network ke primary, bukan kebalik

    def _handle_event(self, msg: QueueMessage) -> None:
        payload = msg.payload or {}

        # contoh: event kirim ticket baru
        if "ticket_number" in payload:
            ticket = Ticket(**payload)
            try:
                self.reg_ticket_uc.execute(ticket)
                # kalau berhasil, kasih tahu indikator FINE (optional)
                ok_msg = QueueMessage.new(
                    kind=MessageKind.EVENT,
                    topic=QueueTopic.INDICATOR,
                    payload={"device_status": DeviceStatus.FINE},
                )
                self.queue_to_indicator.put(ok_msg)
            except Exception:
                # kalau gagal (network/printer/server error),
                # kirim status NET_ERROR ke indikator
                err_msg = QueueMessage(
                    kind=MessageKind.EVENT,
                    topic=QueueTopic.INDICATOR,
                    payload={"device_status": DeviceStatus.NET_ERROR},
                )
                self.queue_to_indicator.put(err_msg, timeout=3)


    def _handle_command(self, msg: QueueMessage) -> None:
        """
        Contoh: Primary minta initial data dari server
        """
        payload = msg.payload or {}
        cmd = payload.get("command")

        if cmd == "GET_INITIAL_DATA":
            data = self.get_init_data_uc.execute()
            # kirim balik ke primary
            resp = QueueMessage.new(
                kind=MessageKind.RESPONSE,
                topic=QueueTopic.PRIMARY,
                payload=data,
            )
            self.queue_to_primary.put(resp, timeout=3)

    # ------------ main loop ------------ #

    def run(self) -> None:
        while self._running:
            msg: QueueMessage = self.queue_from_primary.get_nowait()
            self._handle_one_message(msg)
           
            # di sini kamu juga bisa:
            # - cek status koneksi
            # - retry deferred request, dll

            time.sleep(self._poll_interval)
