from abc import ABC, abstractmethod


class IOutputBool(ABC):
    @abstractmethod
    def turn_on(self) -> None:
        pass 
    
    @abstractmethod
    def turn_off(self) -> None:
        pass 
    
    @abstractmethod
    def firePulse(self, periode: float) -> None:
        pass 
    
    @abstractmethod
    def readState(self) -> bool:
        pass 
