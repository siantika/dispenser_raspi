class DomainError(Exception):
    """Base domain exception"""

class InvalidTicketNumberError(DomainError):
    """Ticket number violates EAN-13 rule"""

class InvalidServicePriceError(Exception):
    """ServiceType price must be a positive decimal number"""
    pass
