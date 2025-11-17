from escpos.printer import Usb
from typing import Protocol


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
    def __init__(self, vid: int, pid: int,timeout: int = 1):
        self._p = Usb(
            idVendor=vid,
            idProduct=pid,
            timeout=timeout,
            in_ep=0x81,   
            out_ep=0x01 
        )


    def text(self, txt: str) -> None:
        self._p.text(txt)

    def barcode(
        self,
        code: str,
        bc_type: str,
        height: int = 64,
        width: int = 3,
        pos: str = "BELOW",
        font: str = "A",
    ) -> None:
        self._p.barcode(code, bc_type, height, width, pos, font)

    def cut(self) -> None:
        self._p.cut()

    def close(self) -> None:
        self._p.close()
        
    def set(self, **kwargs):
        self._p.set(**kwargs)
        
        
