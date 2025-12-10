import json
import multiprocessing as mp
import time as time_sleep
from dataclasses import asdict, dataclass
from enum import Enum, auto
from queue import Empty
from typing import Any, Dict, Optional

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
from dispenser_carwash.domain.entities.vehicle_queue import (
    EstimationModeEnum,
    VehicleQueueInfo,
)
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
    FAILED_TO_PRINT = auto()
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
    PRINTER_ERROR = auto()
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
            (State.PRINTING_TICKET, Event.PRINTER_ERROR): State.FAILED_TO_PRINT,
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
            self._usecase.play_prompt.execute("service_1", True)
            return self._usecase.select_service.execute(1)

        if self._usecase.listen_service_2.execute():
            self._usecase.play_prompt.execute("service_2", True)
            return self._usecase.select_service.execute(2)

        if self._usecase.listen_service_3.execute():
            self._usecase.play_prompt.execute("service_3", True)
            return self._usecase.select_service.execute(3)

        if self._usecase.listen_service_4.execute():
            self._usecase.play_prompt.execute("service_4", True)
            return self._usecase.select_service.execute(4)

        return None


    def get_services_update(self)->Optional[QueueMessage]:
        try:
            return self._from_net.get_nowait()
        except Empty:
            return None
        
    def _initialize_init_data(self)-> None :
        self._to_net.put(
            QueueMessage.new(
                topic=QueueTopic.NETWORK,
                kind=MessageKind.COMMAND,
                payload={"command": "GET_INITIAL_DATA"},
            )
        )
        try:
            initial_data: QueueMessage = self._from_net.get()# blocking until get init data

            self._last_ticket_number = initial_data.payload.get("last_ticket_number").sequence_number
            self._service_data = initial_data.payload.get("list_of_services")
        
            self.logger.info(f"Last ticket number from server: {self._last_ticket_number}")
            self.logger.info(f"List of services: {self._service_data}")
            
            self._usecase.select_service.set_list_of_services(self._service_data)
            self._usecase.generate_ticket.set_initial_sequence(self._last_ticket_number)       

            self._to_status.put(
                QueueMessage.new(
                    topic=QueueTopic.INDICATOR,
                    kind=MessageKind.EVENT,
                    payload={"device_status": DeviceStatus.FINE},
                ), timeout=Settings.TIMEOUT_PUT_QUEUE
            )
            self.logger.info("Initial Primary Worker success")

        except Empty:            
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
    """
    memutar selamat datang dan jumlah antrian dan estimasi dipanggil.
    update setiap 10 detik di net, di sini kirim payload request aja
    args:
    jumlah antrian, optional per_car_minute, estimasi waktu antrian (min_max)
    bahkan bisa OFF juga
    Response
            {
            "mode": "AUTO",
            "per_car_minutes": 7 | None 
            "est_min": 2
            "est_max": 5
            }
    """
    def _play_interruptible(self, title: str) -> bool:
        """
        Play sound but allow interruption if service is selected.
        Return True jika interrupted (service sudah dipilih).
        """
        try:
            self._usecase.play_prompt.execute(title)

            # selama suara masih berjalan, cek input tombol
            while self._usecase.play_prompt.sound_player.is_busy():
                service = self.selecting_service()
                if service is not None:
                    self._selected_service = service
                    self.logger.info(f"Interrupted by service selection: {service}")
                    self._usecase.play_prompt.sound_player.stop()  # stop suara langsung
                    return True  # interrupted!
                
                time_sleep.sleep(0.05)

        except Exception as e:
            self.logger.error(f"Sound error: {e}")

        return False

    def _estimate_waiting_time(
        self,
        mode: EstimationModeEnum,
        queue_in_front: int,
        est_min_const: int,
        est_max_const: int,
        time_per_vehicle: Optional[int],
    ) -> Dict[str, int]:
        """Hitung estimasi waktu tunggu dalam menit."""

        # # mode tidak diketahui / OFF
        # if mode not in {"AUTO", "MANUAL"}:
        #     return {
        #         "queue_in_front": max(queue_in_front, 0),
        #         "est_min": 0,
        #         "est_max": 0,
        #     }

        if mode == "AUTO":
            if time_per_vehicle is None:
                raise ValueError("time_per_vehicle wajib ada kalau mode=AUTO")

            estimated = queue_in_front * time_per_vehicle
            if estimated < 0:
                raise ValueError(
                    "Estimated harus positif. "
                    f"queue_in_front={queue_in_front}, time_per_vehicle={time_per_vehicle}"
                )

            est_min = estimated - est_min_const
            est_max = estimated + est_max_const
        else:  # MANUAL
            est_min = est_min_const
            est_max = est_max_const

        if est_min < 1 or est_max < 1:
            est_min = est_max = 0

        return {
            "mode":mode,
            "queue_in_front": max(queue_in_front, 0),
            "est_min": est_min,
            "est_max": est_max,
        }


    def _get_queue_info_from_network(self) -> Optional[VehicleQueueInfo]:
        """Minta info antrian ke NetworkWorker, return payload atau None kalau timeout."""
        msg = QueueMessage.new(
            topic=QueueTopic.NETWORK,
            kind=MessageKind.COMMAND,
            payload={"command": "GET_QUEUE_VEHICLE_INFO"},
        )
        self._to_net.put_nowait(msg)
        self.logger.info("Mengirim GET_QUEUE_VEHICLE_INFO command ke NetworkWorker")

        try:
            resp: QueueMessage = self._from_net.get(timeout=Settings.TIMEOUT_PUT_QUEUE)
            self.logger.info(f"Menerima response queue info dari NetworkWorker {resp.payload}")
            return resp.payload or {}
        except Empty:
            self.logger.warning(
                "Timeout menunggu queue info dari NetworkWorker, pakai fallback manual"
            )
            return None


    def generate_queue_and_estimation(self) -> Dict[str,Any]:
        """Flow greeting + pengumuman jumlah antrian + estimasi waktu."""

        # 1. Ambil data antrian dari network / pakai fallback manual
        payload = self._get_queue_info_from_network()

        if not payload:
            self.logger.warning(f"Payload is empty, value: {payload}")
            return
        
        mode = payload.mode
        queue_in_front = payload.queue_in_front
        est_min_const = payload.est_min
        est_max_const = payload.est_max
        time_per_vehicle = payload.time_per_vehicle  # dipakai saat AUTO

        self.logger.info(f"Ini modenya: {mode}")
        # 2. Hitung estimasi
        return  self._estimate_waiting_time(
            mode=mode,
            queue_in_front=queue_in_front,
            est_min_const=est_min_const,
            est_max_const=est_max_const,
            time_per_vehicle=time_per_vehicle,
        )

    def greet_and_queue_info(
        self,
        mode: EstimationModeEnum,
        queue_in_front: int,
        est_min: int,
        est_max: int
    ):
        # Welcome
        if self._play_interruptible("new_welcome"):
            return  # langsung keluar

        if mode != EstimationModeEnum.OFF:
            if self._play_interruptible("saat_ini"): return
            if self._play_interruptible(str(queue_in_front)): return
            if self._play_interruptible("kendaraan_dalam_antr"): return

            if self._play_interruptible("estimasi_waktu"): return
            if self._play_interruptible(str(est_min)): return
            if self._play_interruptible("hingga"): return
            if self._play_interruptible(str(est_max)): return
            if self._play_interruptible("menit"): return

        if self._play_interruptible("pilih_jenis_cuci"):
            return

        
    def run(self):
       
        self._initialize_init_data()
        self._usecase.play_prompt.execute("system_ready")
        time_sleep.sleep(2) # buffer for sound 
        
        self._fsm.state = State.IDLE
        last_state: Optional[State] = None
        new_payload_of_service = None 
        while True:
            update_service = self.get_services_update()
            if update_service is not None:
                payload = update_service.payload or {}
                new_payload_of_service = payload.get("list_of_services")

                if new_payload_of_service:
                    self._usecase.select_service.set_list_of_services(new_payload_of_service)
                    self.logger.info(
                        "Updated list of services: %s",
                        new_payload_of_service,
                    )

                
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
                # self._usecase.play_prompt.execute("welcome")
                queue_info = self.generate_queue_and_estimation()
                self._fsm.trigger(Event.GREETING_DONE)
                self.logger.info(f"Ini queue infonya {queue_info}")
                if queue_info:
                    mode_raw = queue_info.get("mode")
                    # convert string -> Enum
                    mode = (
                        EstimationModeEnum(mode_raw)
                        if isinstance(mode_raw, str)
                        else mode_raw
                    )

                    self.greet_and_queue_info(
                        mode,
                        queue_info.get("queue_in_front"),
                        queue_info.get("est_min"),
                        queue_info.get("est_max"),
                    )
                

            # SELECTING_SERVICE
            if self._fsm.state == State.SELECTING_SERVICE and self._selected_service is None:
                if not is_vehicle_present:
                    # Kabur sebelum pilih service
                    self._fsm.trigger(Event.LEAVE_WITHOUT_SELECTING)
                else:
                    service = self.selecting_service()
                    
                    if service is not None:
                        self.logger.info(f"Ini service yang dipilih: {service}")
                        self._selected_service = service
            
            
            # Pastikan suara pilihan service selesai dulu
            if (
                self._selected_service is not None
                and self._fsm.state == State.SELECTING_SERVICE
            ):
                if not self._usecase.play_prompt.sound_player.is_busy():
                    self._usecase.play_prompt.stop()
                    self._fsm.trigger(Event.SERVICE_SELECTED)

            # GENERATING_TICKET
            if self._fsm.state == State.GENERATING_TICKET:
                self.generated_ticket = self._usecase.generate_ticket.execute(
                    self._selected_service.id
                )
                self.logger.info(f"ticket generated, number:{self.generated_ticket}")
                self._payload_to_net_worker.update(
                    json.loads(
                        json.dumps(asdict(self.generated_ticket), default=str)
                    )
                )
                self.logger.info(f"Payalod to be sent: {self._payload_to_net_worker}")
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
                        timeout=Settings.TIMEOUT_PUT_QUEUE,  
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
                    self._fsm.trigger(Event.PRINTER_ERROR)
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
                self._usecase.play_prompt.execute("taking_ticket", False)
                self._fsm.trigger(Event.GATE_OPENED)

            # VEHICLE_STAYING
            if self._fsm.state == State.VEHICLE_STAYING:
                if not self._usecase.detect_vehicle.execute():
                    self._fsm.trigger(Event.VEHICLE_ENTER)

            # FAILED TO PRINT
            """ We don't allow the customer to enter, so we go back to vehicle staying"""
            if self._fsm.state == State.FAILED_TO_PRINT:
                self._usecase.play_prompt.execute("printer_error", True)
                time_sleep.sleep(5) ## blocking
            
                self._fsm.state = State.VEHICLE_STAYING
            
            # Biar CPU tidak 100%
            time_sleep.sleep(0.01)
