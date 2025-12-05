from abc import ABC, abstractmethod


class IPrinter(ABC):
    @abstractmethod
    def text(self, txt: str) -> None: 
        pass 
    
    @abstractmethod
    def barcode(
        self,
        code: str,
        bc_type: str,
        height: int = 64,
        width: int = 3,
        pos: str = "BELOW",
        font: str = "A",
    ) -> None:
        pass 
    
    @abstractmethod
    def cut(self) -> None:
        pass 
    
    @abstractmethod
    def close(self) -> None:
        pass 
    
    @abstractmethod
    def set(self, **kwargs): 
        pass 
