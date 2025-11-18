import time
from pathlib import Path

import pygame

from dispenser_carwash.hardware.sound import PyGameSound

# ------------------------------
# 1. Determine sound folder
# ------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent.parent
SOUNDS_DIR = PROJECT_ROOT / "assets" / "sounds"

print("ini Root folder: ", PROJECT_ROOT)
# ------------------------------
# 2. Map all MP3 files
# ------------------------------
sound_files = {f.stem: str(f) for f in SOUNDS_DIR.iterdir() if f.suffix.lower() == ".mp3"}

# ------------------------------
# 3. Initialize pygame and load sounds
# ------------------------------
pygame.init()
pygame.mixer.init()

sounds = {}
for name, path in sound_files.items():
    s = PyGameSound(hw_driver=pygame)
    s.load(path)
    sounds[name] = s

# ------------------------------
# 4. Play each sound one by one
# ------------------------------
for name, sound_obj in sounds.items():
    print(f"Playing: {name}")
    sound_obj.play()
    # Wait until sound finishes
    while sound_obj.is_busy():
        time.sleep(0.1)
