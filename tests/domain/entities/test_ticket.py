from datetime import datetime

import pytest

from dispenser_carwash.domain.entities.ticket import Ticket
from dispenser_carwash.domain.exception import InvalidTicketNumberError


class TestTicketValidation:

    def test_valid_ticket_should_pass(self):
        ticket = Ticket(None, 1, "5901234123457", datetime.now())
        assert ticket.validate_ticket() is True

    def test_invalid_length_should_raise(self):
        ticket = Ticket(None, 1, "123", datetime.now())

        with pytest.raises(InvalidTicketNumberError):
            ticket.validate_ticket()

    def test_non_digit_should_raise(self):
        ticket = Ticket(None, 1, "89912AB567896", datetime.now())

        with pytest.raises(InvalidTicketNumberError):
            ticket.validate_ticket()

    def test_invalid_checksum_should_raise(self):
        ticket = Ticket(None, 1, "8991234567890", datetime.now())

        with pytest.raises(InvalidTicketNumberError) as exc:
            ticket.validate_ticket()

        assert "check-digit" in str(exc.value)
