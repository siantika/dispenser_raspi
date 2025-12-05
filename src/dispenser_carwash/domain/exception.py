class DomainError(Exception):
    """Base domain exception"""

class InvalidTicketNumberError(DomainError):
    """Ticket number violates EAN-13 rule"""
