class DomainError(Exception):
    """Base domain exception"""

class InvalidTicketNumberError(DomainError):
    """Ticket number violates EAN-13 rule"""

class InvalidServicePriceError(DomainError):
    """ServiceType price must be a positive decimal number"""
    pass

class InvalidDeviceError(DomainError):
    """Device error"""
    pass 
