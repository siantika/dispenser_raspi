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
import time

from gpiozero import LED, Button

from .hardware.input_bool import InputGpio
from .hardware.out_bool import OutputGpio
from .hardware.printer import UsbEscposDriver as Printer
from .utils.logger import get_queue, listener_process, setup_logger

input_btn_1 = Button(pin=5, pull_up=True, bounce_time=0.1)
out_pin = LED(pin=23, initial_value=False)
input_service_1 = InputGpio(input_btn_1)
gate_controller = OutputGpio(out_pin)


def worker(name):
    log = setup_logger(name, get_queue())
    log.info(f"Hello from {name}!")


def test_all_barcodes(printer: Printer):
    # -------------------
    # EAN13 (12 digit input)
    # -------------------
    printer.text("=== TEST EAN13 ===\n")
    printer.barcode("123456789012", "EAN13")
    printer.text("\n\n")
    time.sleep(0.5)

    # -------------------
    # EAN8 (7 digit input)
    # -------------------
    printer.text("=== TEST EAN8 ===\n")
    printer.barcode("5512345", "EAN8")
    printer.text("\n\n")
    time.sleep(0.5)

    # -------------------
    # UPC-A (11 digit input)
    # -------------------
    printer.text("=== TEST UPC-A ===\n")
    printer.barcode("12345678901", "UPCA")
    printer.text("\n\n")
    time.sleep(0.5)

    # -------------------
    # CODE39 (bisa alphanumeric)
    # -------------------
    printer.text("=== TEST CODE39 ===\n")
    printer.barcode("ABC12345", "CODE39")
    printer.text("\n\n")
    time.sleep(0.5)

    # -------------------
    # ITF / Interleaved 2 of 5 (harus genap digit)
    # -------------------
    printer.text("=== TEST ITF ===\n")
    printer.barcode("12345678", "ITF")  # 8 digit (genap)
    printer.text("\n\n")
    time.sleep(0.5)

    # -------------------
    # CODABAR (A-D allowed)
    # -------------------
    printer.text("=== TEST CODABAR ===\n")
    printer.barcode("A123456A", "CODABAR")
    printer.text("\n\n")
    time.sleep(0.5)

    # CUT
    printer.cut()
    printer.close()
    print("ALL BARCODE TEST DONE ✔")


if __name__ == "__main__":

    printer = Printer(0x28E9, 0x0289)
    while True:
        print("Turn ON")
        gate_controller.turn_on()        # <- harus ada ()
        time.sleep(1)

        print("Turn OFF")
        gate_controller.turn_off()       # <- harus ada ()
        time.sleep(1)

        print("Fire Pulse 0.5 detik")
        gate_controller.firePulse(0.5)  # <- harus ada () dan beri parameter periode
        time.sleep(0.5)

        state = gate_controller.readState()  # <- harus ada ()
        print("State sekarang:", state)

    # # ---- TEST 1: TEXT ----
    # print("Printing text...")
    # printer.text("==== TEST PRINT ====\n")
    # printer.text("Printer OK!\n\n")

    # # ---- TEST 2: TEXT FORMAT ----
    # print("Testing text formatting...")
    # printer.set(align="center", width=2, height=2)
    # printer.text("BIG BOLD TEXT\n")
    # printer.set(align="left", width=1, height=1)
    # printer.text("\nFormat reset.\n\n")

    # # ---- TEST 3: BARCODE ----
    # # print("Printing barcode...")
    # # printer.text("Barcode Test:\n")
    # # printer.barcode("123456789012", "CODE128", height=80, width=3, pos="BELOW")
    # # printer.text("\n\n")
    # test_all_barcodes(printer)

    # # ---- TEST 4: QR CODE ----
    # print("Printing QR code...")
    # try:
    #     printer._p.qr("https://example.com", size=6)
    # except Exception as e:
    #     print("QR code error:", e)
    # printer.text("\n\n")

    # # ---- TEST 6: CUT ----
    # print("Cutting paper...")
    # printer.cut()

    # # ---- TEST 7: CLOSE ----
    # print("Closing printer...")
    # printer.close()

    # print("ALL TEST COMPLETED ✓")

    # # Start listener
    # # listener = mp.Process(target=listener_process, args=(get_queue(),), daemon=True)
    # # listener.start()

    # # # Setup main logger
    # # log = setup_logger("MAIN")
    # # log.info("Main process started")

    # # # Spawn workers
    # # p1 = mp.Process(target=worker, args=("Worker-1",))
    # # p2 = mp.Process(target=worker, args=("Worker-2",))
    # # p1.start(); p2.start()
    # # p1.join(); p2.join()

    # # # Stop listener
    # # get_queue().put(None)
    # # listener.join()
