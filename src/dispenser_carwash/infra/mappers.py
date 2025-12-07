from datetime import datetime
from typing import Any, Dict, List

from dispenser_carwash.domain.entities.last_ticket_number import LastTicketNumber
from dispenser_carwash.domain.entities.service_type import ServiceType
from dispenser_carwash.domain.entities.ticket import Ticket


class TicketNetworkMapper:

    @staticmethod
    def to_payload(ticket: Ticket) -> dict:
        """
        Convert Domain Ticket -> JSON payload for API
        """
        return {
            "ticket_number": ticket.ticket_number,
            "service_type_id": ticket.service_type_id,
            "entry_time": ticket.entry_time.isoformat(),
            "status": "PENDING", 
        }

    @staticmethod
    def from_response(data: dict) -> Ticket:
        """
        Convert JSON response -> Domain Ticket
        """
        return Ticket(
            id=data.get("id"),
            ticket_number=data["ticket_number"],
            service_type_id=data["service_type_id"],
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


class LastTicketNumberNetworkMapper:
    def from_response(data: dict) -> LastTicketNumber:
        return LastTicketNumber(
            sequence_number=data['sequence_number']
        )