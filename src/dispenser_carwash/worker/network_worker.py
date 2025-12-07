from __future__ import annotations

import asyncio
import multiprocessing as mp
from queue import Empty
from typing import Optional

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
        self._unsend_tickets_queue:mp.Queue = mp.Queue(50)

        # Logger khusus untuk worker ini
        self.logger = setup_logger("net_worker")
        self.logger.info("NetworkWorker successfully created")

    def stop(self) -> None:
        self._running = False
        self.logger.info("NetworkWorker stop() called. Stopping main loop soon...")

    # ------------ helper kecil ------------ #

    def _send_indicator_status(self, status: DeviceStatus) -> None:
        """Kirim status device ke IndicatorWorker."""
        msg = QueueMessage.new(
            kind=MessageKind.EVENT,
            topic=QueueTopic.INDICATOR,
            payload={"device_status": status},
        )
        try:
            self.queue_to_indicator.put(msg, timeout=3)
            self.logger.info(f"Sent indicator status: {status}")
        except Exception:
            self.logger.exception("Failed to send indicator status")

    # ------------ queue handling (ASYNC) ------------ #

    async def _handle_one_message(self, msg: QueueMessage) -> None:
        # hanya proses message untuk NETWORK
        if msg.topic != QueueTopic.NETWORK:
            self.logger.debug(f"Ignoring message for topic {msg.topic}")
            return

        if msg.kind == MessageKind.EVENT:
            await self._handle_event(msg)
        elif msg.kind == MessageKind.COMMAND:
            await self._handle_command(msg)
        else:
            self.logger.warning(f"Unknown message kind: {msg.kind}")

    async def _handle_event(self, msg: QueueMessage) -> None:
        payload = msg.payload or {}
        self.logger.info(f"Handling EVENT in NetworkWorker. Payload: {payload}")

        # contoh: event kirim ticket baru (dari primary)
        if "ticket_number" in payload:
            try:
                ticket = Ticket(**payload)
            except Exception:
                self.logger.exception(
                    "Failed to construct Ticket from payload in NetworkWorker"
                )
                self._send_indicator_status(DeviceStatus.NET_ERROR)
                return

            try:
                response = await self.reg_ticket_uc.execute(ticket)
                self.logger.info(f"Response from server (register_ticket): {response}")
                print(f"[NetworkWorker] response from server: {response}", flush=True)

                # kalau response dianggap gagal (None / False), kirim NET_ERROR
                if not response:
                    self._send_indicator_status(DeviceStatus.NET_ERROR)
                else:
                    self._send_indicator_status(DeviceStatus.FINE)

            except Exception:
                # log error lengkap, jangan ditelan
                self.logger.exception(
                    "Exception while calling reg_ticket_uc.execute(ticket)"
                )
                self._send_indicator_status(DeviceStatus.NET_ERROR)

        else:
            self.logger.warning(
                "EVENT received by NetworkWorker without 'ticket_number' in payload"
            )

    async def _handle_command(self, msg: QueueMessage) -> None:
        """
        Contoh: Primary minta initial data dari server.
        """
        payload = msg.payload or {}
        cmd: Optional[str] = payload.get("command")

        self.logger.info(f"Handling COMMAND in NetworkWorker. Command: {cmd}")

        if cmd == "GET_INITIAL_DATA":
            try:
                data = await self.get_init_data_uc.execute()
                self.logger.info("GET_INITIAL_DATA executed successfully")

                resp = QueueMessage.new(
                    kind=MessageKind.RESPONSE,
                    topic=QueueTopic.PRIMARY,
                    payload=data,
                )
                self.queue_to_primary.put(resp, timeout=3)
                self.logger.info("Initial data sent back to PRIMARY")
            except Exception:
                self.logger.exception("Failed to execute GET_INITIAL_DATA command")

        else:
            self.logger.warning(f"Unknown command for NetworkWorker: {cmd}")

    # ------------ main loop ------------ #

    async def _main_loop(self) -> None:
        self.logger.info("NetworkWorker main loop started")
        while self._running:
            try:
                msg: QueueMessage = self.queue_from_primary.get(
                    timeout=self._poll_interval
                )
                self.logger.info(f"Got message from PRIMARY: {msg}")
            except Empty:
                # tidak ada message, lanjut loop
                await asyncio.sleep(self._poll_interval)
                continue
            except Exception:
                self.logger.exception("Unexpected error while reading from queue_from_primary")
                await asyncio.sleep(self._poll_interval)
                continue

            try:
                await self._handle_one_message(msg)
            except Exception:
                self._unsend_tickets_queue.put(msg)
                self.logger.exception("Unexpected error while handling message in NetworkWorker")

            # beri sedikit jeda supaya loop tidak terlalu agresif
            await asyncio.sleep(self._poll_interval)

        self.logger.info("NetworkWorker main loop exited")
        
    async def _check_connection_loop_and_update(self) -> None:
        """
        Loop terpisah untuk:
        - cek konektivitas server (via get_init_data_uc.execute())
        - update init data ke PRIMARY kalau berubah
        - coba kirim ulang tiket yang sempat gagal (unsent_tickets_queue)
        """
        last_init_data = None
        self.logger.info("NetworkWorker health-check loop started and init data")

        while self._running:
            # 1) Cek koneksi + ambil init data
            try:
                new_init_data = await self.get_init_data_uc.execute()

                # kalau ada perubahan data, kirim ke PRIMARY
                if new_init_data != last_init_data:
                    try:
                        self.queue_to_primary.put(
                            QueueMessage.new(
                                topic=QueueTopic.PRIMARY,
                                kind=MessageKind.EVENT,
                                payload=new_init_data,
                            ),
                            timeout=3,
                        )
                        self.logger.info("Sent updated init data to PRIMARY from health check")
                        last_init_data = new_init_data
                    except Exception:
                        # ini error di queue / serialisasi, BUKAN network
                        self.logger.exception("Failed to send init data to PRIMARY in health check")

                # kalau sampai sini sukses → jaringan dianggap FINE
                self._send_indicator_status(DeviceStatus.FINE)

            except Exception:
                # hanya kalau get_init_data_uc.execute() gagal (timeout, refused, dsb.)
                self.logger.warning(
                    "Network unreachable during health check and update init data"
                )
                self._send_indicator_status(DeviceStatus.NET_ERROR)
                # kalau network down, langsung tidur dan lanjut loop berikutnya
                await asyncio.sleep(10)
                continue

            # 2) Kalau networknya FINE, coba kirim ulang tiket yang tertunda
            try:
                while True:
                    pending_msg: QueueMessage = self._unsend_tickets_queue.get_nowait()
                    self.logger.info(f"Retrying unsent ticket: {pending_msg}")
                    # ini async → WAJIB di-`await`
                    await self._handle_one_message(pending_msg)
            except Empty:
                # tidak ada tiket pending, aman
                pass
            except Exception:
                self.logger.exception("Error while processing unsent tickets in health check loop")

            # 3) jeda sebelum iterasi berikutnya
            await asyncio.sleep(10)

        self.logger.info("NetworkWorker health-check loop exited")


    def run(self) -> None:
        self.logger.info("NetworkWorker.run() started (asyncio event loop)")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Jalankan main loop + health check dalam 2 task paralel
        tasks = [
            loop.create_task(self._main_loop()),
            loop.create_task(self._check_connection_loop_and_update())
        ]

        loop.run_until_complete(asyncio.gather(*tasks))
        self.logger.info("NetworkWorker.run() finished")
