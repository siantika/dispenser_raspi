import time
from typing import Protocol

from gpiozero import LED


class OutputBool(Protocol):
    def turn_on(self) -> None:
        ...
    def turn_off(self) -> None:
        ...
    def firePulse(self, periode: float) -> None:
        ...
    def readState(self) -> bool:
        ...

class OutputGpio(OutputBool):
    def __init__(self, hw_driver: LED):
        self._hw_driver = hw_driver

    def turn_on(self) -> None:
        self._hw_driver.on() 

    def turn_off(self) -> None:
        self._hw_driver.off() 

    def firePulse(self, periode: float) -> None:
        
        self.turn_on()
        time.sleep(periode)
        self.turn_off()

    def readState(self) -> bool:
        return self._hw_driver.is_lit
