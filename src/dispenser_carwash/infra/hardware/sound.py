from typing import Dict, Optional

import pygame

from dispenser_carwash.domain.interfaces.hardware.i_sound import ISound
from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger(__name__)


class PyGameSound(ISound):
    def __init__(self, hw_driver: pygame):
        self._hw_driver = hw_driver

        # pastikan mixer sudah di-init
        if not self._hw_driver.mixer.get_init():
            self._hw_driver.mixer.init()

        # tidak perlu _sound kalau semua lewat load_many
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._channel: Optional[pygame.mixer.Channel] = None

    def load(self, file_path: str) -> None:
        """
        Implementasi minimal supaya tetap memenuhi interface.
        Misalnya: treat sebagai lagu bernama 'default'.
        """
        sound = self._hw_driver.mixer.Sound(file_path)
        self._sounds["default"] = sound

    def load_many(self, files: Dict[str, str]) -> None:
        """
        files: dict {nama_lagu: path_file}
        """
        self._sounds = {}  # reset dulu kalau perlu

        for name, path in files.items():
            self._sounds[name] = self._hw_driver.mixer.Sound(path)

    def play(self, title: str) -> None:
        if title not in self._sounds:
            logger.warning("%s is not in playlist", title)
            return

        sound = self._sounds[title]
        self._channel = sound.play()

    def stop(self) -> None:
        if self._channel:
            self._channel.stop()

    def is_busy(self) -> bool:
        return self._channel.get_busy() if self._channel else False
