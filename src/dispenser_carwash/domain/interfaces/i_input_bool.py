from abc import ABC, abstractmethod


class IInputBool(ABC):
    @abstractmethod
    def read_input(self) -> bool:
        pass 