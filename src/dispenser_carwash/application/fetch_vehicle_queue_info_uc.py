from typing import Dict

from dispenser_carwash.domain.entities.vehicle_queue import VehicleQueueInfo
from dispenser_carwash.domain.exception import VehicleQueueNotExist
from dispenser_carwash.infra.repositories.vehicle_queue_info import (
    VehicleQueueInfoRepository,
)


class FetchVehicleQueueInfoUseCase:
    def __init__(self, repo:VehicleQueueInfoRepository):
        self.repo =  repo
        
    async def execute(self) -> VehicleQueueInfo:
        est:Dict = await self.repo.get_estimation()
        vehicle_queue:Dict = await self.repo.get_vehicle_queue()
        
        if est is  None or vehicle_queue is None:
            raise VehicleQueueNotExist(f"Got est: {est} and vehicle_queue: {vehicle_queue}. These are none-type")
        
        
        return VehicleQueueInfo(
            queue_in_front= vehicle_queue.get("vehicle_queue_info"),
            est_min= est.get("est_min"),
            est_max= est.get("est_max"),
            mode = est.get("mode"),
            time_per_car = est.get("time_per_vehicle", None )
        ) 