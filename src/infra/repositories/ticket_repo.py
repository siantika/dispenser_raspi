from dispenser_carwash.config.settings import Settings
from dispenser_carwash.domain.entities.ticket import Ticket
from dispenser_carwash.domain.interfaces.repositories.i_ticket_repo import (
    ITicketRepository,
)
from infra.http_client import HttpClient
from infra.mappers import TicketNetworkMapper


class TicketRepositoryRemote(ITicketRepository):
    def __init__(self, http_client:HttpClient):
        self.http = http_client

    async def create(self, ticket: Ticket) -> Ticket:
        payload = TicketNetworkMapper.to_payload(ticket)

        resp = await self.http.post("/tickets", json=payload)
        data = resp.json()

        return TicketNetworkMapper.from_response(data)
