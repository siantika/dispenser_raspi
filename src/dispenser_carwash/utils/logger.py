import logging
import logging.handlers
import multiprocessing as mp
from typing import Optional

# Queue global untuk logging antar proses
_log_queue: Optional[mp.Queue] = None


def get_queue() -> mp.Queue:
    global _log_queue
    if _log_queue is None:
        _log_queue = mp.Queue(-1)  # unlimited size
    return _log_queue


def listener_configurer():
    root = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(processName)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def listener_process(queue: mp.Queue):
    listener_configurer()
    while True:
        try:
            record = queue.get()
            if record is None:  # sinyal shutdown
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)
        except Exception:
            pass


def worker_configurer(queue: mp.Queue):
    h = logging.handlers.QueueHandler(queue)
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(logging.INFO)


def setup_logger(name: str = "app", queue: Optional[mp.Queue] = None):
    if queue is None:
        q = get_queue()
        worker_configurer(q)
    else:
        worker_configurer(queue)
    return logging.getLogger(name)
