from typing import Protocol

import usb.core
from escpos.printer import Usb

from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)


class PrinterUnavailable(Exception):
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
            """ It is mandatory to put in_ep and out_ep"""
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
            """ General Exception for handling uncovered error """
            logger.error(f"❌ Gagal konek ke printer (Exception): {e}")
            self._p = None

    def _ensure_connected(self):
        """
        if printer is connected (stored in self._p), it will return the object otherwise it will return None.
        Here we try to connect if it is not connected and rasie Exception it if still not connected
        """
        if self._p is None:
            self._connect()
        if self._p is None:
            raise PrinterUnavailable("Printer is not connected")

    def _safe_call(self, method_name: str, *args, **kwargs):
        """
        wrapper for low-function printer. It make sure to check printer's connection \
        whenever we call the printer function. So that, it prevents crash. It also provide reconnect mechanism
 
        """
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
                        f"USB printer is  disconnected (USBError 19), attempt {attempt}. "
                        "Trying to reconnect..."
                    )
                    # Since it goes to this exception, we assume the old connection is broken
                    # so we assign it as None for make it sure
                    self._p = None

                    if attempt == 2:
                        logger.error("Failed to reconnect, Printer still disconnect")
                        raise PrinterUnavailable("Printer disconnect (USBError 19)")

                    # attempt 1 -> continue to  _ensure_connected() again
                    continue

                # Another USB error (uncovered)
                logger.error(f"USB error printer: {e}")
                raise PrinterUnavailable(f"Error USB printer: {e}")

            except OSError as e:
                # For another paltform, it uses OSError errno 19
                if getattr(e, "errno", None) == 19:
                    logger.warning(
                        f"⚠ OSError 19: printer disconnect, attempt {attempt}. "
                        "Trying to reconnect..."
                    )
                    self._p = None

                    if attempt == 2:
                        raise PrinterUnavailable("Printer disconect (OSError 19)")

                    continue

                logger.error(f"OSError printer: {e}")
                raise PrinterUnavailable(f"Error OS printer: {e}")

            except Exception as e:
                # uncovered error
                logger.error(f" Unidentified error: {e}")
                self._p = None
                raise PrinterUnavailable("Unidentified error")

        # Whatever it goes out the loop or something, it is categorized as disconnected
        raise PrinterUnavailable("Printer tidak tersedia (unknown)")

    # ==== Wrapper Public Method ====
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
