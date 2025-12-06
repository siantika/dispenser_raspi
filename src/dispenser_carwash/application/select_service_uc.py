from typing import List, Optional

from dispenser_carwash.domain.entities.service_type import ServiceType
from dispenser_carwash.domain.exception import InitialServicesAreNotInitialize


class SelectServiceUseCase:
    def __init__(self, services: List[ServiceType]):
        if not services:  
            raise InitialServicesAreNotInitialize(
                "Initial services are not initialize. Check the server connection!"
            )
        self.list_of_services = services
    
    def execute(self, service_id: int) -> Optional[ServiceType]:
        return next(
            (item for item in self.list_of_services if item.id == service_id),
            None
        )
