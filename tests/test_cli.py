import json

from usb_security.cli import main
from usb_security.models import Device, OperationResult
from usb_security.providers import PlatformProvider


class FakeProvider(PlatformProvider):
    platform_name = "test"

    def __init__(self):
        self.devices = [Device("disk-test", "Test USB", True, True, False)]
        self.actions = []

    def list_devices(self):
        return self.devices

    def protect(self, device_id):
        self.actions.append(("protect", device_id))
        return OperationResult("protect", device_id, True, "temporary", "unprotect", "protected")

    def unprotect(self, device_id):
        self.actions.append(("unprotect", device_id))
        return OperationResult("unprotect", device_id, True, "temporary", "protect", "unprotected")


def test_status_json(capsys):
    assert main(["--json", "status"], FakeProvider()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["platform"] == "test"
    assert payload["devices"][0]["identifier"] == "disk-test"


def test_protect_requires_confirmation(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert main(["protect", "--device", "disk-test"], provider) == 2
    assert provider.actions == []


def test_protect_yes_calls_provider(capsys):
    provider = FakeProvider()
    assert main(["--json", "protect", "--device", "disk-test", "--yes"], provider) == 0
    assert provider.actions == [("protect", "disk-test")]
    assert json.loads(capsys.readouterr().out)["verified"] is True
