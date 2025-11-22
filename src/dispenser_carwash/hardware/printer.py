from typing import Protocol

import usb.core  # dari pyusb
from escpos.printer import Usb

from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)


class PrinterUnavailable(Exception):
    """Dipakai saat printer tidak terhubung / hilang."""
    pass


class PrinterDriver(Protocol):
    def text(self, txt: str) -> None: ...
    def barcode(
        self,
        code: str,
        bc_type: str,
        height: int = 64,
        width: int = 3,
        pos: str = "BELOW",
        font: str = "A",
    ) -> None: ...
    def cut(self) -> None: ...
    def close(self) -> None: ...
    def set(self, **kwargs): ...


class UsbEscposDriver(PrinterDriver):
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

    def _ensure_connected(self):
        """Pastikan self._p ada. Kalau tidak ada -> coba connect, kalau masih gagal -> raise PrinterUnavailable."""
        if self._p is None:
            self._connect()
        if self._p is None:
            raise PrinterUnavailable("Printer tidak terhubung")

    def _safe_call(self, func, *args, **kwargs):
        """
        Jalankan fungsi low-level ESC/POS dengan auto-reconnect.
        Kalau printer mati / dicabut:
          - coba reconnect sekali
          - kalau masih gagal -> raise PrinterUnavailable
        """
        self._ensure_connected()

        try:
            return func(*args, **kwargs)

        except usb.core.USBError as e:
            # 19 = ENODEV: "No such device (it may have been disconnected)"
            if e.errno == 19:
                logger.warning(
                    "⚠ Printer USB hilang (Errno 19). Coba reconnect sekali..."
                )
                self._p = None
                self._connect()
                if self._p is not None:
                    # retry sekali lagi
                    return func(*args, **kwargs)
                else:
                    logger.error("❌ Reconnect printer gagal setelah USBError 19")
                    raise PrinterUnavailable("Printer terputus")
            else:
                # error USB lain, tetap kita lempar ke atas
                raise

        except OSError as e:
            # Kadang error OS juga bisa muncul kalau device hilang
            if getattr(e, "errno", None) == 19:
                logger.warning("⚠ OSError 19: printer hilang, reconnect gagal")
                self._p = None
                raise PrinterUnavailable("Printer terputus (OSError 19)")
            else:
                raise

    # === wrapper method yang dipakai di luar ===
    def text(self, txt: str) -> None:
        self._safe_call(self._p.text, txt)

    def barcode(
        self,
        code: str,
        bc_type: str,
        height: int = 64,
        width: int = 3,
        pos: str = "BELOW",
    ) -> None:
        self._safe_call(self._p.barcode, code, bc_type, height, width, pos)

    def cut(self) -> None:
        self._safe_call(self._p.cut)

    def set(self, **kwargs):
        self._safe_call(self._p.set, **kwargs)

    def close(self) -> None:
        if self._p is not None:
            try:
                self._p.close()
            except Exception as e:
                logger.error(f"❌ Error closing printer: {e}")
            self._p = None
