from abc import ABC, abstractmethod

from dispenser_carwash.domain.entities.ticket import Ticket


class ITicketRepository(ABC):
    @abstractmethod
    async def create(self, ticket: Ticket) -> Ticket:
        """Save and return Ticket with ID set"""
        pass 
