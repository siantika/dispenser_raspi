
from dispenser_carwash.domain.interfaces.hardware.i_output_bool import IOutputBool


class OpenGateUseCase:
    
    def __init__(self, driver:IOutputBool):
        self.gate_driver =  driver
        #init state
        self.close()
        
    def open(self):
        self.gate_driver.firePulse(0.5)
        
    def close(self):
        self.gate_driver.turn_off()