from typing import List, Optional

from dispenser_carwash.domain.entities.service_type import ServiceType


class SelectServiceUseCase:
    def __init__(self):
        self.list_of_services:List[ServiceType]= None 
        
    def set_list_of_services(self, value:List[ServiceType]):
        self.list_of_services = value
    
    def execute(self, service_id: int) -> Optional[ServiceType]:
        return next(
            (item for item in self.list_of_services if item.id == service_id),
            None
        )
