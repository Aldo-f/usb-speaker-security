import pytest

from usb_security.models import Device
from usb_security.providers import PlatformProvider, ProviderError


class RejectingProvider(PlatformProvider):
    platform_name = "test"

    def list_devices(self):
        return [
            Device("internal", "Internal disk", False, True, False),
            Device("partition", "USB partition", True, False, False),
        ]

    def protect(self, device_id):
        self.require_device(device_id)

    def unprotect(self, device_id):
        self.require_device(device_id)


@pytest.mark.parametrize("device_id", ["internal", "partition", "missing"])
def test_unconfirmed_or_non_disk_devices_are_rejected(device_id):
    with pytest.raises(ProviderError):
        RejectingProvider().protect(device_id)
