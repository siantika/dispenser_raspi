from datetime import UTC, datetime, timedelta

import pytest

from dispenser_carwash.application.generate_ticket_uc import (
    GenerateTicketUc,
    TicketEan13Generator,
)
from dispenser_carwash.domain.entities.ticket import Ticket


class TestChecksumEAN13:
    def test_checksum_valid_known_values(self):
        """
        Pastikan perhitungan checksum sesuai contoh known values.
        raw_12_digit → expected_checksum
        """
        cases = [
            ("899010000001", 2),
            ("899010000042", 5),
            ("899011234567", 5),
            ("899120000001", 8),
            ("899120000042", 1),
            ("899121234567", 1),
        ]

        for raw, expected in cases:
            checksum = TicketEan13Generator._checksum_ean_13(raw)
            assert checksum == expected, f"{raw} expected {expected}, got {checksum}"

    def test_checksum_raises_if_length_not_12(self):
        with pytest.raises(ValueError):
            TicketEan13Generator._checksum_ean_13("123")  # too short

        with pytest.raises(ValueError):
            TicketEan13Generator._checksum_ean_13("1234567890123")  # too long

    def test_checksum_raises_if_not_all_digits(self):
        with pytest.raises(ValueError):
            TicketEan13Generator._checksum_ean_13("ABCDEFGHIJKL")

        with pytest.raises(ValueError):
            TicketEan13Generator._checksum_ean_13("12345678901A")


class TestCreateEanTicket:
    def test_generate_correct_length_and_digits(self):
        ean = TicketEan13Generator.create_ean_ticket(service_id=3, sequence=1)

        # 13 digit numeric
        assert isinstance(ean, str)
        assert len(ean) == 13
        assert ean.isdigit()

    def test_generate_prefix_and_embedding_parts(self):
        service_id = 3
        sequence = 42

        ean = TicketEan13Generator.create_ean_ticket(service_id, sequence)

        # 1) prefix harus 899 (GS1 Indonesia)
        assert ean.startswith("899")

        # 2) service_id di digit 4-5 (index 3-4)
        assert ean[3:5] == f"{service_id:02d}"

        # 3) sequence di digit 6-12 (index 5-11)
        assert ean[5:12] == f"{sequence:07d}"

    def test_checksum_of_generated_ean_is_valid(self):
        service_id = 1
        sequence = 42

        ean = TicketEan13Generator.create_ean_ticket(service_id, sequence)

        base12 = ean[:12]
        last_digit = int(ean[-1])

        expected_checksum = TicketEan13Generator._checksum_ean_13(base12)
        assert last_digit == expected_checksum

    def test_different_sequence_produce_different_ean(self):
        service_id = 1

        ean1 = TicketEan13Generator.create_ean_ticket(service_id, sequence=1)
        ean2 = TicketEan13Generator.create_ean_ticket(service_id, sequence=2)

        assert ean1 != ean2
        # prefix + service_id sama
        assert ean1[:5] == ean2[:5]
        # sequence part beda
        assert ean1[5:12] != ean2[5:12]

    def test_invalid_too_long_service_or_sequence_raises(self):
        """
        Kalau service_id atau sequence terlalu besar, format akan memproduksi base > 12 digit,
        dan seharusnya ValueError terangkat.
        """
        # service_id jadi 3 digit → raw_number panjangnya > 12
        with pytest.raises(ValueError):
            TicketEan13Generator.create_ean_ticket(service_id=123, sequence=1)

        # sequence jadi >7 digit → raw_number panjangnya > 12
        with pytest.raises(ValueError):
            TicketEan13Generator.create_ean_ticket(service_id=1, sequence=10_000_000)


class TestGenerateTicketUc:
    def test_execute_returns_ticket_entity(self):
        uc = GenerateTicketUc(initial_sequence=1)
        service_id = 3

        ticket = uc.execute(service_id)

        assert isinstance(ticket, Ticket)
        assert ticket.service_type_id == service_id
        assert isinstance(ticket.ticket_number, str)
        assert len(ticket.ticket_number) == 13
        assert ticket.ticket_number.isdigit()

    def test_execute_ticket_number_is_valid_ean13(self):
        uc = GenerateTicketUc(initial_sequence=1)
        service_id = 3

        ticket = uc.execute(service_id)
        ean = ticket.ticket_number

        base12 = ean[:12]
        last_digit = int(ean[-1])
        expected_checksum = TicketEan13Generator._checksum_ean_13(base12)

        assert last_digit == expected_checksum

    def test_sequence_increments_between_calls_and_reflected_in_ticket_number(self):
        uc = GenerateTicketUc(initial_sequence=1)
        service_id = 3

        t1 = uc.execute(service_id)
        t2 = uc.execute(service_id)
        t3 = uc.execute(service_id)

        e1, e2, e3 = t1.ticket_number, t2.ticket_number, t3.ticket_number

        # Ticket number harus berbeda
        assert e1 != e2 != e3

        # prefix + service_id sama
        assert e1[:5] == e2[:5] == e3[:5]

        # Sequence part (digit 6-12) naik 1 tiap kali
        seq1 = int(e1[5:12])
        seq2 = int(e2[5:12])
        seq3 = int(e3[5:12])

        assert seq1 + 1 == seq2
        assert seq2 + 1 == seq3

    def test_entry_time_is_utc_and_close_to_now(self):
        uc = GenerateTicketUc(initial_sequence=1)
        service_id = 3

        before = datetime.now(UTC)
        ticket = uc.execute(service_id)
        after = datetime.now(UTC)

        assert isinstance(ticket.entry_time, datetime)
        # timezone-aware & UTC
        assert ticket.entry_time.tzinfo is not None
        assert ticket.entry_time.tzinfo == UTC

        # Masih dalam rentang waktu eksekusi (± beberapa detik)
        # (kalau takut flaky, bisa longgarin delta waktunya)
        assert before - timedelta(seconds=1) <= ticket.entry_time <= after + timedelta(
            seconds=1
        )
