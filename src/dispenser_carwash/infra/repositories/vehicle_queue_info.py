from httpx import HTTPStatusError, RequestError

from dispenser_carwash.domain.entities.vehicle_queue import VehicleQueueInfo
from dispenser_carwash.domain.exception import VehicleQueueInfoRepositoryError
from dispenser_carwash.domain.interfaces.repositories.i_vehicle_queue_info_repo import (
    IVehicleQueueInfoRepository,
)
from dispenser_carwash.infra.http_client import AsyncHttpClient
from dispenser_carwash.infra.mappers import VehicleQueueInfoMapper
from dispenser_carwash.utils.logger import setup_logger


class VehicleQueueInfoRepository(IVehicleQueueInfoRepository):
    def __init__(self, http:AsyncHttpClient):
        self._http = http 
        self.logger = setup_logger("Vehicle Queue")
        
    async def get(self):
        try:
            resp = await self._http.get("/vehicle-queue-info")
            body = resp.json()       
            payload = body.get("data") 
            self.logger.info(f"Ini payload dari queue: {payload}")
            if payload is None:
                raise VehicleQueueInfoRepositoryError(
                    "Invalid response: 'data' field is missing"
                )
            
            return VehicleQueueInfoMapper.from_response(
                resp
            )

        except HTTPStatusError as e:
            status = e.response.status_code
            raise VehicleQueueInfoRepositoryError(
                f"Server error when fetching VehicleQueueInfo: {status}"
            ) from e

        except RequestError as e:
            raise VehicleQueueInfoRepositoryError(
                "Network unreachable when fetching ticket"
            ) from e
            
