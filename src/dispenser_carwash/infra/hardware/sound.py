import subprocess
from pathlib import Path
from typing import Dict, Optional, Union

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
    Driver sound sederhana pakai `aplay` (ALSA).
    – Tidak pakai pygame, aman dipakai di multiprocessing worker.
    – File dikelola pakai pathlib.Path.
    """

    def __init__(self, base_path: Union[str, Path]):
        # Base folder kalau nanti mau pakai path relatif
        self.base_path = Path(base_path)
        self._sounds: Dict[str, Path] = {}     # "system_ready" -> Path(.../system_ready.wav)
        self._default: Optional[Path] = None   # optional default sound
        self._current_proc: Optional[subprocess.Popen] = None

    # -------------
    # Helper internal
    # -------------

    def _cleanup_finished(self) -> None:
        """
        Bersihkan referensi kalau proses sudah selesai (supaya tidak jadi zombie).
        """
        if self._current_proc is not None:
            # poll() akan memanggil waitpid(WNOHANG) -> proses jadi reaped
            if self._current_proc.poll() is not None:
                self._current_proc = None

    # ------------------------
    # Implementasi dari ISound
    # ------------------------

    def load(self, name: str, file_path: Union[str, Path]) -> None:
        """
        Load satu file suara.
        name: key yang nanti dipakai saat play(), misal "system_ready"
        file_path: path absolut / relatif ke base_path
        """
        p = Path(file_path)
        if not p.is_absolute():
            p = self.base_path / p

        if not p.exists():
            logger.error(f"🚨 Sound file not found for '{name}': {p}")
            return

        self._sounds[name] = p
        logger.info(f"🎵 Loaded sound '{name}' -> {p}")

        if self._default is None:
            self._default = p

    def load_many(self, sounds: Dict[str, Path]) -> None:
        """
        Load banyak file sekaligus, mapping name -> Path.
        Biasanya dipakai bersama get_sounds().
        """
        for name, p in sounds.items():
            if not isinstance(p, Path):
                p = Path(p)

            if not p.exists():
                logger.warning(f"⚠ Sound file not found for '{name}': {p}")
                continue

            self._sounds[name] = p

        if self._default is None and self._sounds:
            # kalau ada key "system_ready" pakai itu, kalau tidak pakai entri pertama
            self._default = self._sounds.get("system_ready") or self._sounds[next(iter(self._sounds.keys()))]

        logger.info(f"✅ Total sounds loaded: {len(self._sounds)}")

    def play(self, name: Optional[str] = None) -> None:
        """
        Play suara berdasarkan name. Kalau name None, pakai default.
        Non-blocking ke proses utama (subprocess jalan sendiri).
        """
        # bersihkan referensi proses lama yang sudah selesai
        self._cleanup_finished()

        if name is None:
            path = self._default
        else:
            path = self._sounds.get(name)

        if path is None:
            logger.error(f"🚨 Sound key not found: {name}")
            return

        # Stop dulu kalau ada proses sebelumnya yang MASIH hidup
        self.stop()

        try:
            # Popen supaya non-blocking
            self._current_proc = subprocess.Popen(
                ["aplay", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"▶️ Playing sound '{name or 'default'}' -> {path}")
        except Exception as e:
            logger.exception(f"Failed to play sound '{name}': {e}")

    def stop(self) -> None:
        """
        Hentikan suara yang sedang diputar (kalau ada).
        """
        if self._current_proc is None:
            return

        try:
            # kalau masih hidup, terminate lalu tunggu sebentar agar reaped
            if self._current_proc.poll() is None:
                self._current_proc.terminate()
                try:
                    self._current_proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    self._current_proc.kill()
                    self._current_proc.wait(timeout=1.0)
            self._current_proc = None
            logger.info("⏹ Sound stopped")
        except Exception as e:
            logger.exception(f"Failed to stop sound: {e}")
            self._current_proc = None

    def is_busy(self) -> bool:
        """
        Return True kalau masih ada proses `aplay` yang hidup.
        """
        if self._current_proc is None:
            return False

        ret = self._current_proc.poll()  # None = masih jalan, selain itu = selesai & reaped
        if ret is None:
            return True

        # sudah selesai
        self._current_proc = None
        return False