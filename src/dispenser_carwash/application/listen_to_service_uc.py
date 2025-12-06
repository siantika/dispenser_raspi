
from dispenser_carwash.domain.interfaces.hardware.i_input_bool import IInputBool


class ListenToServiceUseCase:
    def __init__(self, driver:IInputBool):
        self.driver = driver
        
    def execute(self):
        return self.driver.read_input()
    