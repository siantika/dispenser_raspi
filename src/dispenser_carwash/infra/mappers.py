from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from dispenser_carwash.domain.entities.last_ticket_number import LastTicketNumber
from dispenser_carwash.domain.entities.service_type import ServiceType
from dispenser_carwash.domain.entities.ticket import Ticket
from dispenser_carwash.domain.entities.vehicle_queue import (
    EstimationModeEnum,
    VehicleQueueInfo,
)


@dataclass
class TicketResponseDTO:
    id:int 
    ticket_number:str 
    service_name:str 
    entry_time:datetime
    
    
    
class TicketNetworkMapper:

    @staticmethod
    def to_payload(ticket: Ticket) -> dict:
        """
        Convert Domain Ticket -> JSON payload for API
        """
        return {
            "ticket_number": ticket.ticket_number,
            "service_type_id": ticket.service_type_id,
            "entry_time": ticket.entry_time,
        }

    @staticmethod
    def from_response(data:  Dict[str, Any]) -> Ticket:
        """
        Convert JSON response -> Domain Ticket
        """
        return TicketResponseDTO(
            id=data.get("id"),
            ticket_number=data["ticket_number"],
            service_name=data["service_name"],
            entry_time=datetime.fromisoformat(data["entry_time"]),
        )



class ServiceTypeNetworkMapper:
    @staticmethod
    def from_response(data: List[Dict[str, Any]]) -> list[ServiceType]:
        return [
            ServiceType(
                id=item["id"],
                name=item["name"],
                desc=item.get("desc"),
                price=item["price"],
            )
            for item in data
        ]


class VehicleQueueInfoMapper:
    @staticmethod
    def from_response(data: Dict[str, Any]) -> "VehicleQueueInfo":
        return VehicleQueueInfo(
            queue_in_front=data.get("queue_in_front"),
            mode=EstimationModeEnum(data.get("mode")),  # Convert string → Enum
            est_min=data.get("est_min"),
            est_max=data.get("est_max"),
            time_per_vehicle=data.get("time_per_vehicle"),
        )
        
        
class LastTicketNumberNetworkMapper:
    def from_response(data:  Dict[str, Any]) -> LastTicketNumber:
        return LastTicketNumber(
            sequence_number=data['sequence_number']
        )