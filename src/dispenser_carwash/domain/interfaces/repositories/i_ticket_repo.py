
# class Ticket:
#     id: int | None
#     service_type_id: int 
#     ticket_number: str 
#     entry_time: datetime 

from abc import ABC, abstractmethod

from dispenser_carwash.domain.entities.ticket import Ticket


class ITicketRepository(ABC):
    @abstractmethod
    async def create(self, ticket: Ticket) -> Ticket:
        """Save and return Ticket with ID set"""
        pass 
