from abc import ABC, abstractmethod

from dispenser_carwash.domain.entities.last_ticket_number import LastTicketNumber


class ILastTicketNumberRepository(ABC):
    @abstractmethod
    def get(self) -> LastTicketNumber:
        pass 