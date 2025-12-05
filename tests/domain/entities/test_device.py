from datetime import datetime

import pytest

from dispenser_carwash.domain.entities.device import Device
from dispenser_carwash.domain.exception import InvalidDeviceError


class TestDeviceValidation:

    def test_valid_device_should_pass(self):
        device = Device(
            code="DSP-01-CBG",
            name="Dispenser Pintu Masuk",
            desc="Dispenser utama cabang Cibinong",
            location="Cibinong - Gate 1",
            model="Raspberry Pi 3B",
            firmware_version="v1.0.0",
            registered_at=datetime.now(),
        )

        assert device.validate() is True

    def test_device_code_cannot_be_empty(self):
        device = Device(
            code="  ",
            name="Dispenser",
            desc="Test",
            location="X",
            model="Raspberry Pi 3B",
            firmware_version="v1.0.0",
            registered_at=datetime.now(),
        )

        with pytest.raises(InvalidDeviceError) as exc:
            device.validate()

        assert "code" in str(exc.value).lower()



