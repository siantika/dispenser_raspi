from dataclasses import dataclass
from datetime import datetime

from dispenser_carwash.domain.exception import InvalidTicketNumberError


@dataclass 
class Ticket:
    id: int | None
    service_type_id: int 
    ticket_number: str 
    entry_time: datetime 

    def validate_ticket(self) -> bool:
        """
        Validate EAN-13 ticket number
        """
        code = self.ticket_number

        if len(code) != 13 or not code.isdigit():
            raise InvalidTicketNumberError(
                f"Ticket number '{self.ticket_number}' is not a valid EAN-13 format! "
                "Must be exactly 13 digits."
            )

        digits = [int(d) for d in code]
        data = digits[:-1]   # 12 digit pertama
        check_digit = digits[-1]

        s = 0
        for i, d in enumerate(data):
            # index genap (0,2,4,...) → weight 1
            # index ganjil (1,3,5,...) → weight 3
            s += d if i % 2 == 0 else d * 3

        calc_check_digit = (10 - (s % 10)) % 10

        if calc_check_digit != check_digit:
            raise InvalidTicketNumberError(
                f"Ticket number '{self.ticket_number}' has invalid check-digit! "
                f"Expected {calc_check_digit}, got {check_digit}"
            )

        return True
