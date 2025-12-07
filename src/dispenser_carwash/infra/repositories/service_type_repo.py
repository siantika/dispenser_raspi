from httpx import HTTPStatusError, RequestError

from dispenser_carwash.domain.exception import ServiceTypeRepositoryError
from dispenser_carwash.domain.interfaces.repositories.i_service_type_repo import (
    IServiceTypeRepository,
)
from dispenser_carwash.infra.http_client import AsyncHttpClient
from dispenser_carwash.infra.mappers import ServiceTypeNetworkMapper


class ServiceTypeRepoHttp(IServiceTypeRepository):
    def __init__(self, http_client: AsyncHttpClient):
        self.http = http_client
        
    async def list_all(self):
        try:
            resp = await self.http.get("/service-types")
            body = resp.json()
            
            payload = body.get("data") 
            if payload is None:
                raise ServiceTypeRepositoryError(
                    "Invalid response: 'data' field is missing"
                )
            return ServiceTypeNetworkMapper.from_response(payload)

        except HTTPStatusError as e:
            status = e.response.status_code
            raise ServiceTypeRepositoryError(
                f"Server error when fetching service types: {status}"
            ) from e

        except RequestError as e:
            raise ServiceTypeRepositoryError(
                "Network unreachable when fetching service types"
            ) from e
