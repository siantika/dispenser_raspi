from dataclasses import dataclass

from httpx import HTTPStatusError, RequestError

from dispenser_carwash.domain.entities.vehicle_queue import VehicleQueueInfo
from dispenser_carwash.domain.exception import VehicleQueueInfoRepositoryError
from dispenser_carwash.domain.interfaces.repositories.i_vehicle_queue_info_repo import (
    IVehicleQueueInfoRepository,
)
from dispenser_carwash.infra.http_client import AsyncHttpClient


@dataclass
class EstimationResponseDTO:
    est_min:int 
    est_max:int 
    

class VehicleQueueInfoRepository(IVehicleQueueInfoRepository):
    def __init__(self, http:AsyncHttpClient):
        self._http = http 
        
    async def get_estimation(self) ->EstimationResponseDTO:
        try:
            resp = await self._http.post("/estimation")
            body = resp.json()       
            payload = body.get("data") 
            if payload is None:
                raise VehicleQueueInfoRepositoryError(
                    "Invalid response: 'data' field is missing"
                )
            return payload

        except HTTPStatusError as e:
            status = e.response.status_code
            raise VehicleQueueInfoRepositoryError(
                f"Server error when creating VehicleQueueInfo: {status}"
            ) from e

        except RequestError as e:
            raise VehicleQueueInfoRepositoryError(
                "Network unreachable when creating ticket"
            ) from e
            
    
    async def get_vehicle_queue_info(self):
        try:
            resp = await self._http.post("/ticket/vehicle-queue") # dari COUNT(ticket where PEDNING) 
            body = resp.json()       
            payload = body.get("data") 
            if payload is None:
                raise VehicleQueueInfoRepositoryError(
                    "Invalid response: 'data' field is missing"
                )
            return payload

        except HTTPStatusError as e:
            status = e.response.status_code
            raise VehicleQueueInfoRepositoryError(
                f"Server error when creating VehicleQueueInfo: {status}"
            ) from e

        except RequestError as e:
            raise VehicleQueueInfoRepositoryError(
                "Network unreachable when creating ticket"
            ) from e
            
    
