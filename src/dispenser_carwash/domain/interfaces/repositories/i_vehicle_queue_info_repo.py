from abc import ABC, abstractmethod


class IVehicleQueueInfoRepository (ABC):
    @abstractmethod
    async def get(self):
        pass 
    
