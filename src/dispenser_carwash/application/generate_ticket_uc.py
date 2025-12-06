from datetime import UTC, datetime  # Python 3.11+

from dispenser_carwash.domain.entities.ticket import Ticket


class TicketEan13Generator:
    @staticmethod
    def _checksum_ean_13(number: str) -> int:
        """
        Calculate an EAN-13 checksum for 12-digit input.
        """
        if len(number) != 12 or not number.isdigit():
            raise ValueError("EAN-13 checksum calculation requires exactly 12 digits")

        sum_odd = sum(int(number[i]) for i in range(0, 12, 2))   # Posisi 1,3,5,...
        sum_even = sum(int(number[i]) for i in range(1, 12, 2))  # Posisi 2,4,6,...

        checksum = (10 - ((sum_odd + 3 * sum_even) % 10)) % 10
        return checksum

    @staticmethod
    def create_ean_ticket(service_id: int, sequence: int) -> str:
        """
        Generate a full 13-digit EAN code (string) based on service id + sequence.
        """
        prefix = "899"  # GS1 Indonesia
        service_id_str = f"{service_id:02d}"
        sequential_str = f"{sequence:07d}"

        raw_number = f"{prefix}{service_id_str}{sequential_str}"

        if len(raw_number) != 12:
            raise ValueError(
                f"EAN base must be 12 digits, got {len(raw_number)} → {raw_number}"
            )

        checksum = TicketEan13Generator._checksum_ean_13(raw_number)
        return f"{raw_number}{checksum}"




class GenerateTicketUseCase:
    def __init__(self):
        self._sequence = 0
        
    def set_initial_sequence(self, value:int):
        if not isinstance(value, int):
            raise ValueError(f"Got instance type {type(value)} instead of 'int' ")
        self._sequence = value

    def execute(self, service_id: int) -> Ticket:
        """
        Generate next ticket entity with EAN-13 ticket number for a given service type.
        """
        gen_ticket_number = TicketEan13Generator.create_ean_ticket(
            service_id, self._sequence
        )
        self._sequence += 1

        return Ticket(
            service_type_id=service_id,
            ticket_number=gen_ticket_number,
            entry_time=datetime.now(UTC),
        )
