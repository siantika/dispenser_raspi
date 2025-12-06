from dispenser_carwash.domain.interfaces.repositories.i_last_ticket_number import (
    ILastTicketNumberRepository,
)


class GetInitialDataUseCase:
    def __init__(self, repo:ILastTicketNumberRepository):
        self.repo = repo 
        
    async def execute(self):
        return await self.repo.get()