from dispenser_carwash.domain.entities.ticket import Ticket
from dispenser_carwash.domain.interfaces.repositories.i_ticket_repo import (
    ITicketRepository,
)


class RegisterTicketUseCase:
    def __init__(self, repo:ITicketRepository):
        self.repo = repo 
        
    async def execute(self, ticket:Ticket):
        await self.repo.create(ticket)
        