from typing import List, Optional

from dispenser_carwash.domain.entities.service_type import ServiceType
from dispenser_carwash.utils.logger import setup_logger

logger = setup_logger("select service - uc")

class SelectServiceUseCase:
    def __init__(self):
        self.list_of_services:List[ServiceType]= None 
        
    def set_list_of_services(self, value:List[ServiceType]):
        self.list_of_services = value
    
    def execute(self, service_id: str) -> Optional[ServiceType]:
        if service_id is None:
            logger.info(f" service with id:{service_id} is empty/not registered, check the init data")
            return 
        return next(
            (item for item in self.list_of_services if item.id == service_id),
            None
        )
