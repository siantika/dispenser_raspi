class DomainError(Exception):
    """Base domain exception"""

class UseCaseError(Exception):
    pass 

class RepositoryError(DomainError):
    pass 

class InvalidTicketNumberError(DomainError):
    """Ticket number violates EAN-13 rule"""

class InvalidServicePriceError(DomainError):
    """ServiceType price must be a positive decimal number"""
    pass

class InvalidDeviceError(DomainError):
    """Device error"""
    pass 

class InitialServicesAreNotInitialize(UseCaseError):
    pass     

class ServiceTypeRepositoryError(RepositoryError):
    pass

class TicketRepositoryError(RepositoryError):
    pass

class PrinterUnavailable(Exception):
    pass

class LastTicketNumberRepositoryError(RepositoryError):
    pass 