import multiprocessing as mp
import signal
import sys

from dispenser_carwash.boot.composition_root import build_app
from dispenser_carwash.utils.logger import setup_logger

logger =setup_logger(__name__)

def _install_signal_handlers(ctx, processes: list[mp.Process]) -> None:
    """
    Pasang handler CTRL+C / SIGTERM supaya semua worker bisa stop dengan rapi.
    """

    def handle_stop(signum, frame):
        logger.info(f"[runtime] Caught signal {signum}, stopping workers...")

        # Minta tiap worker berhenti (kalau punya .stop())
        for attr in ("primary_worker", "indicator_worker", "network_worker"):
            worker = getattr(ctx, attr, None)
            if worker is not None and hasattr(worker, "stop"):
                try:
                    worker.stop()
                except Exception as exc:
                    logger.info(f"[runtime] error when stopping {attr}: {exc}")

        # Kasih kesempatan join dulu
        for p in processes:
            p.join(timeout=3)

        # Kalau masih hidup, paksa terminate
        for p in processes:
            if p.is_alive():
                logger.info(f"[runtime] force terminate {p.name}")
                p.terminate()

        sys.exit(0)

    signal.signal(signal.SIGINT, handle_stop)   # ctrl + c
    signal.signal(signal.SIGTERM, handle_stop)  # kill / systemd stop


def run() -> None:
    """
    Entry point untuk ngejalanin semua worker dengan multiprocessing.
    Dipanggil dari main.py
    """
    # Optional tapi bagus di Linux/RPi:
    try:
        mp.set_start_method("fork")
    except RuntimeError:
        # start method sudah di-set sebelumnya, abaikan
        pass

    # Build seluruh dependency + worker
    ctx = build_app()

    # Definisikan process untuk tiap worker
    p_primary = mp.Process(
        target=ctx.primary_worker.run,
        name="primary-worker",
        daemon=False,   # proses utama, jangan daemon
    )

    p_indicator = mp.Process(
        target=ctx.indicator_worker.run,
        name="indicator-worker",
        daemon=True,    # ikut mati kalau main process mati
    )

    p_network = mp.Process(
        target=ctx.network_worker.run,
        name="network-worker",
        daemon=True,
    )

    processes = [p_primary, p_indicator, p_network]

    # Start semua process
    for p in processes:
        p.start()
        print(f"[runtime] started {p.name} pid={p.pid}")

    # Pasang handler CTRL+C / SIGTERM
    _install_signal_handlers(ctx, processes)

    # Block di primary. Selama primary jalan, program hidup.
    p_primary.join()
    logger.info("[runtime] primary-worker exited, shutting down others...")

    # Fallback cleanup kalau sampai di sini tanpa signal
    for p in (p_indicator, p_network):
        if p.is_alive():
            p.terminate()

    logger.info("[runtime] shutdown complete")
