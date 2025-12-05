from httpx import HTTPStatusError, RequestError

from dispenser_carwash.domain.exception import ServiceTypeRepositoryError
from dispenser_carwash.domain.interfaces.repositories.i_service_type_repo import (
    IServiceTypeRepository,
)
from infra.http_client import AsyncHttpClient
from infra.mappers import ServiceTypeNetworkMapper


class ServiceTypeRepoHttp(IServiceTypeRepository):
    def __init__(self, http: AsyncHttpClient):
        self.http = http
        
    async def list_all(self):
        try:
            resp = await self.http.get("/service-types")
            data = resp.json()
            return ServiceTypeNetworkMapper.from_response(data)

        except HTTPStatusError as e:
            status = e.response.status_code
            raise ServiceTypeRepositoryError(
                f"Server error when fetching service types: {status}"
            ) from e

        except RequestError as e:
            raise ServiceTypeRepositoryError(
                "Network unreachable when fetching service types"
            ) from e
