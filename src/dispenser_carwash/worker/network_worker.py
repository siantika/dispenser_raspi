import asyncio
import multiprocessing as mp
import time
from queue import Empty

from dispenser_carwash.application.get_initial_data import GetInitialDataUseCase
from dispenser_carwash.application.register_ticket_uc import RegisterTicketUseCase
from dispenser_carwash.domain.entities.device import DeviceStatus
from dispenser_carwash.domain.entities.ticket import Ticket
from dispenser_carwash.utils.logger import setup_logger
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
        self.logger = setup_logger("net_worker")
        self.logger.info("NetWorker successfully started")

    def stop(self) -> None:
        self._running = False

    # ------------ queue handling (ASYNC) ------------ #

    async def _handle_one_message(self, msg: QueueMessage) -> None:
        # hanya proses message untuk NETWORK
        if msg.topic != QueueTopic.NETWORK:
            return

        if msg.kind == MessageKind.EVENT:
            await self._handle_event(msg)
        elif msg.kind == MessageKind.COMMAND:
            await self._handle_command(msg)
        # RESPONSE biasanya dari network ke primary, bukan kebalik

    async def _handle_event(self, msg: QueueMessage) -> None:
        payload = msg.payload or {}

        # contoh: event kirim ticket baru
        if "ticket_number" in payload:
            ticket = Ticket(**payload)
            msg = None
            try:
                response = await self.reg_ticket_uc.execute(ticket)
                self.logger.info(f"response from server: {response}")
                print(f"response from server: {response}")
                # kalau berhasil, kasih tahu indikator FINE (optional)
                if not response:
                    msg = QueueMessage.new(
                        topic=QueueTopic.INDICATOR,
                        kind=MessageKind.EVENT,
                        payload={"device_status" : DeviceStatus.NET_ERROR}
                    )
                msg = QueueMessage.new(
                    kind=MessageKind.EVENT,
                    topic=QueueTopic.INDICATOR,
                    payload={"device_status": DeviceStatus.FINE},
                )
                self.queue_to_indicator.put(msg)
            except Exception:
                # kalau gagal (network/server error),
                # kirim status NET_ERROR ke indikator
                err_msg = QueueMessage.new(
                    kind=MessageKind.EVENT,
                    topic=QueueTopic.INDICATOR,
                    payload={"device_status": DeviceStatus.NET_ERROR},
                )
                self.queue_to_indicator.put(err_msg, timeout=3)

    async def _handle_command(self, msg: QueueMessage) -> None:
        """
        Contoh: Primary minta initial data dari server
        """
        payload = msg.payload or {}
        cmd = payload.get("command")

        if cmd == "GET_INITIAL_DATA":
            data = await self.get_init_data_uc.execute()
            # pastikan data adalah dict/list primitif, bukan coroutine/objek aneh
            resp = QueueMessage.new(
                kind=MessageKind.RESPONSE,
                topic=QueueTopic.PRIMARY,
                payload=data,
            )
            self.queue_to_primary.put(resp, timeout=3)

    # ------------ main loop ------------ #

    async def _main_loop(self) -> None:
        while self._running:
            try:
                # blocking call di thread main, tapi ini bukan masalah besar
                msg: QueueMessage = self.queue_from_primary.get(
                    timeout=self._poll_interval
                )
            except Empty:
                continue

            await self._handle_one_message(msg)
            time.sleep(self._poll_interval)

    def run(self) -> None:
        """
        Entry point untuk multiprocessing.Process(target=worker.run).
        """
        asyncio.run(self._main_loop())
