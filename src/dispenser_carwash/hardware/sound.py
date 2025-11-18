from typing import Protocol

import pygame


class Sound(Protocol):
    def load(self, file_path: str): ...
    def play(self): ...
    def stop(self): ...
    def is_busy(self) -> bool: ...


class PyGameSound(Sound):
    def __init__(self, hw_driver:pygame):
        """
        hw_driver: the pygame module (or a mock for testing)
        """
        self._hw_driver = hw_driver
        if not self._hw_driver.mixer.get_init():
            self._hw_driver.mixer.init()
        self._sound = None
        self._channel = None

    def load(self, file_path: str):
        self._sound = self._hw_driver.mixer.Sound(file_path)

    def play(self):
        if self._sound:
            self._channel = self._sound.play()

    def stop(self):
        if self._channel:
            self._channel.stop()

    def is_busy(self) -> bool:
        return self._channel.get_busy() if self._channel else False
