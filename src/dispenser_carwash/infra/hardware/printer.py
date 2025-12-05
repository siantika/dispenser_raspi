
import usb.core  # dari pyusb
from escpos.printer import Usb

from dispenser_carwash.domain.interfaces.i_printer import IPrinter
from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)


class PrinterUnavailable(Exception):
    """Dipakai saat printer tidak terhubung / hilang."""
    pass


class UsbEscposDriver(IPrinter):
    def __init__(self, vid: int, pid: int, timeout: int = 1):
        self._vid = vid
        self._pid = pid
        self._timeout = timeout
        self._p: Usb | None = None
        self._connect()

    def _connect(self):
        """Coba konek ke printer. Kalau gagal, _p tetap None."""
        try:
            logger.info(
                f"🖨️  Connecting ESC/POS USB printer {hex(self._vid)}:{hex(self._pid)}"
            )
            self._p = Usb(
                idVendor=self._vid,
                idProduct=self._pid,
                timeout=self._timeout,
                in_ep=0x81,
                out_ep=0x01,
            )
        except usb.core.USBError as e:
            logger.error(f"❌ Tidak bisa konek ke printer: {e}")
            self._p = None
        except Exception as e:
            # jaga-jaga kalau escpos lempar error lain
            logger.error(f"❌ Gagal konek ke printer (Exception): {e}")
            self._p = None

    def _ensure_connected(self):
        """
        Pastikan self._p ada.
        Kalau tidak ada -> coba connect.
        Kalau masih gagal -> raise PrinterUnavailable.
        """
        if self._p is None:
            self._connect()
        if self._p is None:
            raise PrinterUnavailable("Printer tidak terhubung")

    def _safe_call(self, method_name: str, *args, **kwargs):
        """
        Jalankan fungsi low-level ESC/POS dengan auto-reconnect.
        Kalau printer mati / dicabut:
          - coba reconnect sekali
          - kalau masih gagal -> raise PrinterUnavailable
        NOTE: kita pakai nama method, bukan bound func, supaya setelah reconnect
              method dipanggil dari objek Usb yang baru.
        """
        # Dua percobaan: pertama pakai koneksi sekarang, kedua setelah reconnect
        for attempt in (1, 2):
            self._ensure_connected()

            try:
                if self._p is None:
                    raise PrinterUnavailable("Printer tidak terhubung")

                method = getattr(self._p, method_name)
                return method(*args, **kwargs)

            except usb.core.USBError as e:
                # 19 = ENODEV: "No such device (it may have been disconnected)"
                if e.errno == 19:
                    logger.warning(
                        f"⚠ Printer USB hilang (USBError 19), attempt {attempt}. "
                        "Coba reconnect..."
                    )
                    # anggap koneksi lama sudah mati
                    self._p = None

                    if attempt == 2:
                        logger.error("❌ Reconnect gagal, printer masih tidak ditemukan")
                        raise PrinterUnavailable("Printer terputus (USBError 19)")

                    # attempt 1 -> lanjut ke iterasi berikutnya (akan _ensure_connected() lagi)
                    continue

                # error USB lain → bungkus sebagai PrinterUnavailable
                logger.error(f"❌ Error USB printer: {e}")
                raise PrinterUnavailable(f"Error USB printer: {e}")

            except OSError as e:
                # Beberapa platform pakai OSError errno 19
                if getattr(e, "errno", None) == 19:
                    logger.warning(
                        f"⚠ OSError 19: printer hilang, attempt {attempt}. "
                        "Coba reconnect..."
                    )
                    self._p = None

                    if attempt == 2:
                        raise PrinterUnavailable("Printer terputus (OSError 19)")

                    continue

                logger.error(f"❌ OSError printer: {e}")
                raise PrinterUnavailable(f"Error OS printer: {e}")

            except Exception as e:
                # Error lain yang tidak kita kenali -> bungkus saja
                logger.error(f"❌ Error tidak dikenal pada printer: {e}")
                self._p = None
                raise PrinterUnavailable(f"Error printer tidak dikenal: {e}")

        # Kalau entah bagaimana keluar loop tanpa return/raise, anggap tidak tersedia
        raise PrinterUnavailable("Printer tidak tersedia (unknown)")

    # ==== Wrapper method publik ====
    def text(self, txt: str) -> None:
        self._safe_call("text", txt)

    def barcode(
        self,
        code: str,
        bc_type: str,
        height: int = 64,
        width: int = 3,
        pos: str = "BELOW",
    ) -> None:
        self._safe_call("barcode", code, bc_type, height, width, pos)

    def cut(self) -> None:
        self._safe_call("cut")

    def set(self, **kwargs):
        self._safe_call("set", **kwargs)

    def close(self) -> None:
        if self._p is not None:
            try:
                self._p.close()
            except Exception as e:
                logger.error(f"❌ Error closing printer: {e}")
            self._p = None
