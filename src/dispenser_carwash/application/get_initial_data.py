from typing import Any, Dict

from dispenser_carwash.domain.interfaces.repositories.i_last_ticket_number import (
    ILastTicketNumberRepository,
)
from dispenser_carwash.domain.interfaces.repositories.i_service_type_repo import (
    IServiceTypeRepository,
)


class GetInitialDataUseCase:
    def __init__(self, last_ticket_repo:ILastTicketNumberRepository,
                 service_type_repo:IServiceTypeRepository):
        self.last_ticket_repo = last_ticket_repo
        self.service_type_repo = service_type_repo 
        
    async def execute(self)-> Dict[str, Any]:
        last_ticket = await self.last_ticket_repo.get()
        list_of_services = await self.service_type_repo.list_all()
        
        return {
            "last_ticket": last_ticket,
            "list_of_services": list_of_services 
        }
        