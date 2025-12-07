from httpx import HTTPStatusError, RequestError

from dispenser_carwash.domain.entities.last_ticket_number import LastTicketNumber
from dispenser_carwash.domain.exception import LastTicketNumberRepositoryError
from dispenser_carwash.domain.interfaces.repositories.i_last_ticket_number import (
    ILastTicketNumberRepository,
)
from dispenser_carwash.infra.http_client import AsyncHttpClient
from dispenser_carwash.infra.mappers import LastTicketNumberNetworkMapper


class LastTicketNumberRepository(ILastTicketNumberRepository):
    def __init__(self, http: AsyncHttpClient):
        self.http = http
        
    async def get(self) -> LastTicketNumber:
        try:
            resp = await self.http.get("/last-ticket-number")
            body = resp.json()          # {status, message, data: {...}}

            payload = body.get("data")  
            if payload is None:
                raise LastTicketNumberRepositoryError(
                    "Invalid response: 'data' field is missing"
                )

            return LastTicketNumberNetworkMapper.from_response(payload)


        except HTTPStatusError as e:
            status = e.response.status_code
            raise LastTicketNumberRepositoryError(
                f"Server error when fetching last ticket number: {status}"
            ) from e

        except RequestError as e:
            raise LastTicketNumberRepositoryError(
                "Network unreachable when fetching last ticket number"
            ) from e
