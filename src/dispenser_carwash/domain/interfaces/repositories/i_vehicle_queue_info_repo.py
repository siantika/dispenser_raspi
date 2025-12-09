from abc import ABC, abstractmethod


class IVehicleQueueInfoRepository (ABC):
    @abstractmethod
    async def get_estimation(self):
        pass 
    
    @abstractmethod
    async def get_vehicle_queue_info(self):
        pass 