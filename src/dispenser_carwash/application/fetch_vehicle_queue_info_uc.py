from dispenser_carwash.domain.entities.vehicle_queue import VehicleQueueInfo
from dispenser_carwash.domain.exception import VehicleQueueNotExist
from dispenser_carwash.infra.repositories.vehicle_queue_info import (
    VehicleQueueInfoRepository,
)


class FetchVehicleQueueInfoUseCase:
    def __init__(self, repo:VehicleQueueInfoRepository):
        self.repo =  repo
        
    async def execute(self) -> VehicleQueueInfo:
        vehicle_queue = await self.repo.get()
        
        if vehicle_queue is  None :
            raise VehicleQueueNotExist(f"Got vehicle_queue: {vehicle_queue}. That is none-type")
                
        return VehicleQueueInfo(
            queue_in_front= vehicle_queue.queue_in_front,
            est_min= vehicle_queue.est_min,
            est_max= vehicle_queue.est_max,
            mode = vehicle_queue.mode,
            time_per_vehicle = vehicle_queue.time_per_vehicle
        ) 