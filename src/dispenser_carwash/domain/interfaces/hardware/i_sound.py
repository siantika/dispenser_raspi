from abc import ABC, abstractmethod
from typing import Dict


class ISound(ABC):

    @abstractmethod
    def load(self, file_path: str) -> None:
        """Load a single audio file"""
        pass 

    @abstractmethod
    def load_many(self, files: Dict[str, str]) -> None:
        """Load many files with title mapping"""
        pass 

    @abstractmethod
    def play(self, title: str) -> None:
        """Play by title loaded before"""
        pass 

    @abstractmethod
    def stop(self) -> None:
        """Stop current audio"""
        pass 

    @abstractmethod
    def is_busy(self) -> bool:
        """Return True if currently playing sound"""
        pass 
