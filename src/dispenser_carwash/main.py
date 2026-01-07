import os
import threading
import time

import psutil

from dispenser_carwash.boot.runtime import run


def monitor(interval: float = 1.0):
    process = psutil.Process(os.getpid())

    while True:
        cpu = process.cpu_percent(interval=None)
        mem = process.memory_info().rss / (1024 ** 2)

        print(f"[MONITOR] CPU={cpu:.1f}% | RAM={mem:.1f} MB")
        time.sleep(interval)


if __name__ == "__main__":
    t = threading.Thread(target=monitor, daemon=True)
    t.start()

    run()
