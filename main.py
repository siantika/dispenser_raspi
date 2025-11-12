#!/usr/bin/env python3
import multiprocessing as mp
from utils.logger import setup_logger, get_queue, listener_process

def worker(name):
    log = setup_logger(name, get_queue())
    log.info(f"Hello from {name}!")

if __name__ == '__main__':
    # Start listener
    listener = mp.Process(target=listener_process, args=(get_queue(),), daemon=True)
    listener.start()

    # Setup main logger
    log = setup_logger("MAIN")
    log.info("Main process started")

    # Spawn workers
    p1 = mp.Process(target=worker, args=("Worker-1",))
    p2 = mp.Process(target=worker, args=("Worker-2",))
    p1.start(); p2.start()
    p1.join(); p2.join()

    # Stop listener
    get_queue().put(None)
    listener.join()