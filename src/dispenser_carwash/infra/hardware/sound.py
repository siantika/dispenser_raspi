import subprocess
from pathlib import Path
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



class AlsaSoundDriver(ISound):
    """
    Implementasi termudah: pakai `aplay` via subprocess.
    Tidak pakai pygame, jadi aman di multiprocessing worker.
    """

    def __init__(self, base_path: Path):
        # folder tempat file suara kamu (misal: /home/pi/sounds)
        self.base_path = Path(base_path)
        self._sounds: Dict[str, Path] = {}
        self._default: Optional[Path] = None

    def load(self, file_path: str) -> None:
        """
        Versi paling simpel: set 1 file default.
        Kalau interface kamu perlu banyak sound, pakai load_many() di bawah.
        """
        path = self.base_path / file_path
        if not path.exists():
            raise FileNotFoundError(f"Sound file not found: {path}")
        self._default = path

    def load_many(self, mapping: Dict[str, Path]) -> None:
        """
        Misal kamu mau mapping nama -> file:
        { "welcome": "welcome.wav", "service_1": "svc1.wav" }
        """
        self._sounds.clear()
        for key, filename in mapping.items():
            path = self.base_path / filename
            if not path.exists():
                raise FileNotFoundError(f"Sound file not found: {path}")
            self._sounds[key] = path

    def play(self, title:str ) -> None:
        """
        - Kalau pakai mapping: play("welcome")
        - Kalau tidak pakai mapping: play() akan pakai file default dari load()
        """

        if title is not None:
            path = self._sounds.get(title)
        else:
            path = self._default

        if path is None:
            # tidak ada file yang diset, diam saja
            return

        # Jalankan `aplay` tanpa blocking & tanpa spam log
        subprocess.Popen(
            ["aplay", "-q", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        # Implementasi termudah: biarkan suara selesai sendiri.
        # Kalau benar-benar perlu stop paksa:
        subprocess.Popen(["pkill", "-f", "aplay"])
        
