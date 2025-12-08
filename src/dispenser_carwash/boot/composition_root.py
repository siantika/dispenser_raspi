import multiprocessing as mp
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from gpiozero import LED, Button

from dispenser_carwash.application.detect_vehicle_uc import DetectVehicleUseCase
from dispenser_carwash.application.generate_ticket_uc import GenerateTicketUseCase
from dispenser_carwash.application.get_initial_data import GetInitialDataUseCase
from dispenser_carwash.application.listen_to_service_uc import ListenToServiceUseCase
from dispenser_carwash.application.open_gate_uc import OpenGateUseCase
from dispenser_carwash.application.play_prompt_sound_uc import PlayPromptSoundUseCase
from dispenser_carwash.application.print_ticket_uc import PrintTicketUseCase
from dispenser_carwash.application.register_ticket_uc import RegisterTicketUseCase
from dispenser_carwash.application.select_service_uc import SelectServiceUseCase
from dispenser_carwash.config.settings import Settings
from dispenser_carwash.infra.hardware.input_bool import InputGpio
from dispenser_carwash.infra.hardware.out_bool import OutputGpio
from dispenser_carwash.infra.hardware.printer import UsbEscposDriver
from dispenser_carwash.infra.hardware.sound import AlsaSoundDriver
from dispenser_carwash.infra.http_client import AsyncHttpClient
from dispenser_carwash.infra.repositories.last_ticket_number_repo import (
    LastTicketNumberRepository,
)
from dispenser_carwash.infra.repositories.service_type_repo import ServiceTypeRepoHttp
from dispenser_carwash.infra.repositories.ticket_repo import TicketRepositoryHttp
from dispenser_carwash.utils.logger import setup_logger
from dispenser_carwash.worker.indicator_worker import IndicatorWorker
from dispenser_carwash.worker.network_worker import NetworkWorker
from dispenser_carwash.worker.primary_worker import (
    PrimaryFiniteStateMachine,
    PrimaryUseCase,
    PrimaryWorker,
)

logger = setup_logger(__name__)

def get_sound_path():
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    logger.info(f"📁 Project root: {PROJECT_ROOT}")
    return PROJECT_ROOT / "assets" / "sounds"

    
def get_sound() -> Dict[str, str]:
    SOUNDS_DIR = get_sound_path()
    logger.info(f"🎧 Sounds dir: {SOUNDS_DIR}")

    if not SOUNDS_DIR.exists() or not SOUNDS_DIR.is_dir():
        logger.error(f"🚨 Sound directory not found: {SOUNDS_DIR}")
        return {}

    sounds = {
        f.stem: str(f.resolve())
        for f in SOUNDS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in (".wav")
    }

    if not sounds:
        logger.warning(f"⚠ No sound files found in: {SOUNDS_DIR}")
    else:
        logger.info(f"🎵 Loaded {len(sounds)} sound files from {SOUNDS_DIR}")

    return sounds


@dataclass
class AppContext:
    primary_worker: PrimaryWorker
    indicator_worker: IndicatorWorker
    network_worker: NetworkWorker


def build_app() -> AppContext:
    settings = Settings()    
    lock = mp.Lock()

    # --- IPC queues ---
    q_primary_to_network: mp.Queue = mp.Queue()
    q_network_to_primary: mp.Queue = mp.Queue()
    q_to_indicator: mp.Queue = mp.Queue()

    # --- Infra (HTTP + hardware) ---
    http_client = AsyncHttpClient(
        base_url=settings.Server.BASE_URL,        
        timeout=settings.TIMEOUT_ASC_HTTP,
    )

    # GPIO Zero hardware 
    gpio_loop_sensor = Button(pin=settings.Hardware.LOOP_SENSOR_PIN)
    button_pins = settings.Hardware.BUTTON_PINS 
    gpio_service_1 = Button(pin=button_pins.get("service_1"))
    gpio_service_2 = Button(pin=button_pins.get("service_2"))
    gpio_service_3 = Button(pin=button_pins.get("service_3"))
    gpio_service_4 = Button(pin=button_pins.get("service_4"))
    
    gate_pin = settings.Hardware.GATE_CONTROLLER_PIN
    gpio_gate_controller = LED(pin=gate_pin)
    led_pin = settings.Hardware.LED_PINS  
    gpio_led = LED(pin=led_pin)
    printer = UsbEscposDriver(vid=settings.VID,
                              pid= settings.PID)
    
    sound_player = AlsaSoundDriver(get_sound_path())
    #load sounds 
    sound_files = get_sound()
    sound_player.load_many(sound_files)
     
    
    # Hardware Interface 
    loop_sensor = InputGpio(gpio_loop_sensor)
    input_service_1 = InputGpio(gpio_service_1)
    input_service_2 = InputGpio(gpio_service_2)
    input_service_3 = InputGpio(gpio_service_3)
    input_service_4 = InputGpio(gpio_service_4)
    
    gate_controller = OutputGpio(gpio_gate_controller)
    indicator_driver = OutputGpio(gpio_led)

    
  
    # --- Repositories ---
    ticket_repo = TicketRepositoryHttp(http_client)
    service_type_repo = ServiceTypeRepoHttp(http_client)
    last_ticket_number_repo =LastTicketNumberRepository(http_client)
   
    # --- Use cases ---
    detect_vehicle_uc = DetectVehicleUseCase(loop_sensor)
    play_prompt_sound_uc = PlayPromptSoundUseCase(sound_player)
    print_ticket_uc = PrintTicketUseCase(printer)
    generate_ticket_uc = GenerateTicketUseCase()
    listen_to_service_uc_1 = ListenToServiceUseCase(input_service_1)
    listen_to_service_uc_2 = ListenToServiceUseCase(input_service_2)
    listen_to_service_uc_3 = ListenToServiceUseCase(input_service_3)
    listen_to_service_uc_4 = ListenToServiceUseCase(input_service_4)

    open_gate_uc = OpenGateUseCase(gate_controller)
    select_service_uc = SelectServiceUseCase()

    get_initial_data_uc = GetInitialDataUseCase(last_ticket_number_repo,
                                                service_type_repo)
    register_ticket_uc = RegisterTicketUseCase(ticket_repo)

    # --- Facade usecases utk primary ---
    facade_primary_usecases = PrimaryUseCase(
        detect_vehicle=detect_vehicle_uc,
        generate_ticket=generate_ticket_uc,
        open_gate=open_gate_uc,
        listen_service_1=listen_to_service_uc_1,
        listen_service_2=listen_to_service_uc_2,
        listen_service_3=listen_to_service_uc_3,
        listen_service_4=listen_to_service_uc_4,
        select_service=select_service_uc,
        print_ticket=print_ticket_uc,
        play_prompt=play_prompt_sound_uc,
    )

    # --- Workers ---
    primary_worker = PrimaryWorker(
        to_net= q_primary_to_network,
        from_net=q_network_to_primary,
        lock=lock, usecase=facade_primary_usecases,
        fsm=PrimaryFiniteStateMachine(),
        to_status= q_to_indicator
    )

    indicator_worker = IndicatorWorker(
        driver=indicator_driver,
        queue_in= q_to_indicator
    )

    network_worker = NetworkWorker(
        register_ticket_uc=register_ticket_uc,
        get_initial_data_uc=get_initial_data_uc,
        to_primary=q_network_to_primary,
        from_primary=q_primary_to_network,
        to_indicator=q_to_indicator,
    )

    return AppContext(
        primary_worker=primary_worker,
        indicator_worker=indicator_worker,
        network_worker=network_worker,
    )
