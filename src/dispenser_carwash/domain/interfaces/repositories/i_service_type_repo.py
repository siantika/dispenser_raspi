from abc import ABC, abstractmethod
from typing import List, Optional

from dispenser_carwash.domain.entities.service_type import ServiceType


class IServiceTypeRepository(ABC):
    @abstractmethod
    async def list_all(self) -> Optional[List[ServiceType]]:
        pass 