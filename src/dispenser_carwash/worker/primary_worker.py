import json
import multiprocessing as mp
import time as time_sleep
from dataclasses import asdict, dataclass
from enum import Enum, auto

from dispenser_carwash.application.detect_vehicle_uc import (
    DetectVehicleUseCase,
)
from dispenser_carwash.application.generate_ticket_uc import GenerateTicketUseCase
from dispenser_carwash.application.listen_to_service_uc import ListenToServiceUseCase
from dispenser_carwash.application.open_gate_uc import OpenGateUseCase
from dispenser_carwash.application.play_prompt_sound_uc import PlayPromptSoundUseCase
from dispenser_carwash.application.print_ticket_uc import (
    PrintTicketUseCase,
    generate_printer_payload,
)
from dispenser_carwash.application.select_service_uc import SelectServiceUseCase
from dispenser_carwash.config.settings import Settings
from dispenser_carwash.domain.entities.device import DeviceStatus
from dispenser_carwash.domain.entities.service_type import ServiceType
from dispenser_carwash.domain.entities.ticket import Ticket
from dispenser_carwash.utils.logger import setup_logger
from dispenser_carwash.worker.dto.queue_dto import MessageKind, QueueMessage, QueueTopic


@dataclass
class PrimaryUseCase:
    detect_vehicle:DetectVehicleUseCase
    generate_ticket:GenerateTicketUseCase
    open_gate: OpenGateUseCase
    listen_service_1: ListenToServiceUseCase
    listen_service_2: ListenToServiceUseCase
    listen_service_3: ListenToServiceUseCase
    listen_service_4: ListenToServiceUseCase
    select_service: SelectServiceUseCase
    print_ticket: PrintTicketUseCase
    play_prompt: PlayPromptSoundUseCase


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


class PrimaryFiniteStateMachine:
    def __init__(self):
        self.logger = setup_logger("PrimaryFiniteStateMachine")
        
        self.state = State.IDLE
        """ Format:
        (current state, trigger event): future state after trigger-event is called
        
        """
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
            self.logger.warning(f"⚠ Not a valid transition: {self.state.name} + {event.name}")
            return
            
        next_state = self.transitions[key]
        self.logger.info(f"{self.state.name} --({event.name})--> {next_state.name}")
        self.state = next_state


class PrimaryWorker:
    def __init__(
        self,
        to_net: mp.Queue,
        from_net: mp.Queue,
        lock: mp.Lock,
        usecase: PrimaryUseCase,
        fsm: "PrimaryFiniteStateMachine",
        to_status: mp.Queue,
        # settings: Settings,  # opsional kalau mau diinject
    ):
        self._to_net = to_net
        self._from_net = from_net
        self._to_status = to_status
        self._service_data = None
        self._last_ticket_number = None
        self._selected_service: ServiceType | None = None
        self._payload_to_net_worker: dict = {}
        self._lock = lock
        self._usecase = usecase
        self._fsm = fsm
        self.generated_ticket: Ticket | None = None
        # self._settings = settings

        self.logger = setup_logger("PrimaryWorker")

        # Device awal dianggap FINE
        self._to_status.put(
            QueueMessage.new(
                topic=QueueTopic.INDICATOR,
                kind=MessageKind.EVENT,
                payload={"device_status": DeviceStatus.FINE},
            )
        )

    def selecting_service(self) -> ServiceType | None:
        """Cek tombol service mana yang ditekan, None kalau belum ada."""
        if self._usecase.listen_service_1.execute():
            self._usecase.play_prompt.execute("service_basic", True)
            return self._usecase.select_service.execute()

        if self._usecase.listen_service_2.execute():
            self._usecase.play_prompt.execute("service_complete", True)
            return self._usecase.select_service.execute(21)

        if self._usecase.listen_service_3.execute():
            self._usecase.play_prompt.execute("service_perfect", True)
            return self._usecase.select_service.execute(19)

        if self._usecase.listen_service_4.execute():
            self._usecase.play_prompt.execute("service_cuci_motor", True)
            return self._usecase.select_service.execute()

        return None

    def run(self):
        # --- 1. Minta initial data ke NetworkWorker ---
        self._to_net.put(
            QueueMessage.new(
                topic=QueueTopic.NETWORK,
                kind=MessageKind.COMMAND,
                payload={"command": "GET_INITIAL_DATA"},
            ),
            True,
            3,
        )

        # TODO: sebaiknya pakai timeout + handling error
        initial_data: QueueMessage = self._from_net.get()

        if initial_data is None:
            self.logger.error(
                "Failed to get initial data! Please restart the device!"
            )
            self._to_status.put(
                QueueMessage.new(
                    topic=QueueTopic.INDICATOR,
                    kind=MessageKind.COMMAND,
                    payload={"device_status": DeviceStatus.NET_ERROR},
                )
            )
            # Untuk saat ini, hang di sini (nanti bisa diganti reboot)
            while True:
                time_sleep.sleep(1)

        # --- 2. Set initial data ---
        self._last_ticket_number = initial_data.payload.get("last_ticket_number").sequence_number
        self._service_data = initial_data.payload.get("list_of_services")
    
        self.logger.info(f"Last ticket number: {self._last_ticket_number}")
        self.logger.info(f"List of services: {self._service_data}")
          
        self._usecase.select_service.set_list_of_services(self._service_data)
        self._usecase.generate_ticket.set_initial_sequence(self._last_ticket_number)       

        self._to_status.put(
            QueueMessage.new(
                topic=QueueTopic.INDICATOR,
                kind=MessageKind.EVENT,
                payload={"device_status": DeviceStatus.FINE},
            ),
            True,
            3,
        )

        self.logger.info("Initial Primary Worker success")

        # --- 3. Mulai FSM utama ---
        self._fsm.state = State.IDLE
        last_state: State | None = None

        while True:
            cur_state: State = self._fsm.state
            if cur_state != last_state:
                last_state = cur_state
                self.logger.info(f"Current State: {cur_state.name}")

            is_vehicle_present = self._usecase.detect_vehicle.execute()

            # Reset ketika IDLE
            if self._fsm.state == State.IDLE:
                self._usecase.play_prompt.stop()
                self._usecase.open_gate.close()
                self._selected_service = None
                self._payload_to_net_worker = {}
                self.generated_ticket = None

            # Vehicle baru datang
            if self._fsm.state == State.IDLE and is_vehicle_present:
                self._fsm.trigger(Event.ARRIVED)

            # GREETING
            if self._fsm.state == State.GREETING:
                self._usecase.play_prompt.execute("welcome")
                self.logger.info(f"Nilai driver sound: {self._usecase.play_prompt.sound_player}")
                self._fsm.trigger(Event.GREETING_DONE)
              

            # SELECTING_SERVICE
            if self._fsm.state == State.SELECTING_SERVICE and self._selected_service is None:
                if not is_vehicle_present:
                    # Kabur sebelum pilih service
                    self._fsm.trigger(Event.LEAVE_WITHOUT_SELECTING)
                else:
                    service = self.selecting_service()
                    self.logger.info(f"Ini service yang dipiliih: {service}")
                    if service is not None:
                        self._selected_service = service
            
            
            # Pastikan suara pilihan service selesai dulu
            if (
                self._selected_service is not None
                and self._fsm.state == State.SELECTING_SERVICE
            ):
                self.logger.info(f"Sedang sibuk?:{self._usecase.play_prompt.sound_player.is_busy()}")
                if not self._usecase.play_prompt.sound_player.is_busy():
                    self._usecase.play_prompt.stop()
                    self._fsm.trigger(Event.SERVICE_SELECTED)

            # GENERATING_TICKET
            if self._fsm.state == State.GENERATING_TICKET:
                self.generated_ticket = self._usecase.generate_ticket.execute(
                    self._selected_service
                )
                self._payload_to_net_worker.update(
                    json.loads(
                        json.dumps(asdict(self.generated_ticket), default=str)
                    )
                )
                self._fsm.trigger(Event.TICKET_GENERATED)

            # SENDING_DATA
            if self._fsm.state == State.SENDING_DATA:
                with self._lock:
                    self._to_net.put(
                        QueueMessage.new(
                            topic=QueueTopic.NETWORK,
                            kind=MessageKind.EVENT,
                            payload=self._payload_to_net_worker,
                        ),
                        timeout=Settings.TIMEOUT_PUT_QUEUE,  # atau self._settings...
                    )
                self._fsm.trigger(Event.DATA_SENT)

            # PRINTING_TICKET
            if self._fsm.state == State.PRINTING_TICKET:
                print_format = generate_printer_payload(
                    self.generated_ticket, self._selected_service
                )
                ok = self._usecase.print_ticket.execute(print_format)
                if not ok:
                    self._to_status.put(
                        QueueMessage.new(
                            topic=QueueTopic.INDICATOR,
                            kind=MessageKind.COMMAND,
                            payload={"device_status": DeviceStatus.PRINTER_ERROR},
                        )
                    )
                    self.logger.warning(
                        "⚠ Ticket is not printed due to printer error. "
                        "Please check the printer!"
                    )
                    # TODO: nanti bisa bikin state khusus PRINTER_ERROR
                    self._fsm.trigger(Event.PRINT_DONE)
                else:
                    self._to_status.put(
                        QueueMessage.new(
                            topic=QueueTopic.INDICATOR,
                            kind=MessageKind.EVENT,
                            payload={"device_status": DeviceStatus.FINE},
                        )
                    )
                    self._fsm.trigger(Event.PRINT_DONE)

            # GATE_OPEN
            if self._fsm.state == State.GATE_OPEN:
                self._usecase.open_gate.open()
                self._usecase.play_prompt.execute("taking_ticket", True)
                self._fsm.trigger(Event.GATE_OPENED)

            # VEHICLE_STAYING
            if self._fsm.state == State.VEHICLE_STAYING:
                if not self._usecase.detect_vehicle.execute():
                    self._fsm.trigger(Event.VEHICLE_ENTER)

            # Biar CPU tidak 100%
            time_sleep.sleep(0.01)
