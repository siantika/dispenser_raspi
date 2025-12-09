from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EstimationModeEnum(str, Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"
    OFF = "OFF"
    
    
@dataclass
class VehicleQueueInfo:
    queue_in_front: int
    mode: EstimationModeEnum
    est_min: int
    est_max: int
    time_per_vehicle:Optional[int] 
    

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        if self.queue_in_front < 0:
            raise ValueError(f"queue_in_front must be >= 0, got {self.queue_in_front}")

        if self.est_min < 0:
            raise ValueError(f"est_min must be >= 0, got {self.est_min}")

        if self.est_max < 0:
            raise ValueError(f"est_max must be >= 0, got {self.est_max}")

        if self.est_max < self.est_min:
            raise ValueError(
                f"est_max must be >= est_min "
                f"(got est_min={self.est_min}, est_max={self.est_max})"
            )
