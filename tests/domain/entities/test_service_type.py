from decimal import Decimal

import pytest

from dispenser_carwash.domain.entities.service_type import ServiceType
from dispenser_carwash.domain.exception import InvalidServicePriceError


class TestServiceTypePriceValidation:

    def test_valid_price_indonesia_style_should_pass(self):
        """
        Harga normal Indonesia, misal 50.000 rupiah → 50000.00
        """
        service = ServiceType(
            name="Cuci Basic",
            desc="Cuci luar biasa",
            price=Decimal("50000.00"),
        )

        assert service.validate_price() is True

    def test_valid_price_with_two_decimals_should_pass(self):
        """
        Kalau suatu saat ada format yang butuh 2 desimal (misal akuntansi),
        tetap boleh selama max 2 digit.
        """
        service = ServiceType(
            name="Cuci Wax",
            desc="Cuci + Wax",
            price=Decimal("12345.50"),
        )

        assert service.validate_price() is True

    def test_zero_price_should_raise_error(self):
        """
        Harga 0 tidak diperbolehkan (tidak masuk akal secara bisnis).
        """
        service = ServiceType(
            name="Cuci Gratis",
            desc="Harusnya promo, tapi di domain kita larang 0",
            price=Decimal("0.00"),
        )

        with pytest.raises(InvalidServicePriceError) as exc:
            service.validate_price()

        assert "greater than 0" in str(exc.value)

    def test_negative_price_should_raise_error(self):
        """
        Harga minus jelas tidak valid.
        """
        service = ServiceType(
            name="Cuci Aneh",
            desc="Harga negatif",
            price=Decimal("-1000.00"),
        )

        with pytest.raises(InvalidServicePriceError) as exc:
            service.validate_price()

        assert "greater than 0" in str(exc.value)

    def test_price_with_more_than_two_decimal_places_should_raise_error(self):
        """
        Walaupun Indonesia tidak pakai sen, secara digital kita batasi 2 desimal.
        123.456 → 3 digit desimal → harus error.
        """
        service = ServiceType(
            name="Cuci Detail",
            desc="Terlalu detail sampai 3 desimal 🤣",
            price=Decimal("123.456"),
        )

        with pytest.raises(InvalidServicePriceError) as exc:
            service.validate_price()

        assert "more than 2 decimal places" in str(exc.value)

    def test_price_not_decimal_type_should_raise_error(self):
        """
        Kalau ada yang isinya int/float (bukan Decimal), harus ditolak
        supaya tidak ada masalah pembulatan.
        """
        service = ServiceType(
            name="Cuci Basic",
            desc="Tipe price salah",
            price=50000,  # int, bukan Decimal
        )

        with pytest.raises(InvalidServicePriceError) as exc:
            service.validate_price()

        assert "must be Decimal" in str(exc.value)

    def test_valid_price_string_converted_to_decimal_outside_entity(self):
        """
        Pastikan konversi dari string '50000.00' ke Decimal dilakukan
        DI LUAR entity, supaya entity selalu menerima Decimal bersih.
        """
        raw_price = "50000.00"
        price = Decimal(raw_price)  # konversi di layer lain (schema/usecase)

        service = ServiceType(
            name="Cuci Premium",
            desc="Konversi dari string",
            price=price,
        )

        assert service.validate_price() is True
        assert service.price == Decimal("50000.00")
