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
    
    printer = Printer(0x28e9, 0x0289)
    
  # ---- TEST 1: TEXT ----
    print("Printing text...")
    printer.text("==== TEST PRINT ====\n")
    printer.text("Printer OK!\n\n")

    # ---- TEST 2: TEXT FORMAT ----
    print("Testing text formatting...")
    printer.set(align="center", text_type="B", width=2, height=2)
    printer.text("BIG BOLD TEXT\n")
    printer.set(align="left", text_type="NORMAL", width=1, height=1)
    printer.text("\nFormat reset.\n\n")

    # ---- TEST 3: BARCODE ----
    print("Printing barcode...")
    printer.text("Barcode Test:\n")
    printer.barcode("123456789012", "EAN13", height=80, width=3, pos="BELOW", font="A")
    printer.text("\n\n")

    # ---- TEST 4: QR CODE ----
    print("Printing QR code...")
    try:
        printer._p.qr("https://example.com", size=6)
    except Exception as e:
        print("QR code error:", e)
    printer.text("\n\n")


    # ---- TEST 6: CUT ----
    print("Cutting paper...")
    printer.cut()

    # ---- TEST 7: CLOSE ----
    print("Closing printer...")
    printer.close()

    print("ALL TEST COMPLETED ✓")


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
    