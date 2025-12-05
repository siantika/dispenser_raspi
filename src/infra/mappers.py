from datetime import datetime

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
