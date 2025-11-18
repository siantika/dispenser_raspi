from typing import Protocol


class InputBool(Protocol):
    def read_input(self) -> bool:
        ...

class InputGpio(InputBool):
    def __init__(self, hw_driver):
        self._hw_driver = hw_driver
        
    def read_input(self) -> bool:
        return self._hw_driver._is_pressed
