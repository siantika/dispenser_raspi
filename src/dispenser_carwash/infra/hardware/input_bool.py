from gpiozero import Button

from dispenser_carwash.domain.interfaces.hardware.i_input_bool import IInputBool


class InputGpio(IInputBool):
    def __init__(self, hw_driver:Button):
        self._hw_driver = hw_driver
        
    def read_input(self) -> bool:
        return self._hw_driver.is_pressed
