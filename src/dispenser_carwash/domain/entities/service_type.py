from dataclasses import dataclass
from decimal import Decimal

from dispenser_carwash.domain.exception import InvalidServicePriceError


@dataclass
class ServiceType:
    name: str
    desc: str
    price: Decimal
    
    def validate_price(self) -> bool:
        """
        Validate service price:
        - Must be Decimal
        - Must be > 0
        - Must have at most 2 decimal places
        """
        if not isinstance(self.price, Decimal):
            raise InvalidServicePriceError(
                f"Price must be Decimal, got {type(self.price).__name__}"
            )

        if self.price <= Decimal("0.00"):
            raise InvalidServicePriceError(
                f"Price must be greater than 0, got {self.price}"
            )

        # Check scale: max 2 decimal digits
        if abs(self.price.as_tuple().exponent) > 2:
            raise InvalidServicePriceError(
                f"Price cannot have more than 2 decimal places: {self.price}"
            )

        return True
