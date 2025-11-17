"""Bussiness Process 
Init:
 1. Baca data tiket terakhir
 2. Baca servis dan deskripsinya
 3. Baca file-suara

1. baca sensor open loops
2a. jika ada mobil,
    + Putar musik
    + Baca tombol servis
3. Pilih tombol servis
4. putar suara tombol servis
5. cetak tiket, kirim data, buka portal, Suara "Silakan Masuk"

indikator: LED 
inget isi watchdog

"""



#!sourc
import datetime
import multiprocessing as mp
from utils.logger import setup_logger, get_queue, listener_process
from hardware.printer import UsbEscposDriver as Printer

def worker(name):
    log = setup_logger(name, get_queue())
    log.info(f"Hello from {name}!")

if __name__ == '__main__':
    
    printer = Printer()
    
    printer.text("==== TEST PRINT ====\n")
    printer.text(f"Datetime: {datetime.datetime.now()}\n")
    printer.text("--------------------\n")

    # Print text
    printer.text("Hello from Python ESC/POS driver!\n")
    printer.text("Ini adalah test printing.\n\n")

    # Print barcode
    printer.text("Barcode (CODE128):\n")
    printer.barcode("123456789012", "CODE128")

    # Cutting paper
    printer.cut()

    # Close
    printer.close()
    print("Berhasil print test ke printer!")

    # Start listener
    # listener = mp.Process(target=listener_process, args=(get_queue(),), daemon=True)
    # listener.start()

    # # Setup main logger
    # log = setup_logger("MAIN")
    # log.info("Main process started")

    # # Spawn workers
    # p1 = mp.Process(target=worker, args=("Worker-1",))
    # p2 = mp.Process(target=worker, args=("Worker-2",))
    # p1.start(); p2.start()
    # p1.join(); p2.join()

    # # Stop listener
    # get_queue().put(None)
    # listener.join()
    