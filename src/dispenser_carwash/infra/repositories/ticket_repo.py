from httpx import HTTPStatusError, RequestError

from dispenser_carwash.domain.entities.ticket import Ticket
from dispenser_carwash.domain.exception import TicketRepositoryError
from dispenser_carwash.domain.interfaces.repositories.i_ticket_repo import (
    ITicketRepository,
)
from dispenser_carwash.infra.http_client import AsyncHttpClient
from dispenser_carwash.infra.mappers import TicketNetworkMapper


class TicketRepositoryHttp(ITicketRepository):
    def __init__(self, http_client: AsyncHttpClient):
        self._http = http_client

    async def create(self, ticket: Ticket) -> Ticket:
        payload = TicketNetworkMapper.to_payload(ticket)

        try:
            resp = await self._http.post("/tickets", json=payload)
            body = resp.json()       
            payload = body.get("data") 
            if payload is None:
                raise TicketRepositoryError(
                    "Invalid response: 'data' field is missing"
                )
            return TicketNetworkMapper.from_response(payload)

        except HTTPStatusError as e:
            status = e.response.status_code
            raise TicketRepositoryError(
                f"Server error when creating ticket: {status}"
            ) from e

        except RequestError as e:
            raise TicketRepositoryError(
                "Network unreachable when creating ticket"
            ) from e
