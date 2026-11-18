import json

import pytest

from usb_security.cli import main
from usb_security.models import Device, OperationResult
from usb_security.providers import PlatformProvider, ProviderError


class FakeProvider(PlatformProvider):
    platform_name = "test"

    def __init__(self):
        self.devices = [Device("disk-test", "Test USB", True, True, False)]
        self.actions = []
        self.failure = None

    def list_devices(self):
        return self.devices

    def protect(self, device_id):
        self.actions.append(("protect", device_id))
        if self.failure:
            raise self.failure
        return OperationResult("protect", device_id, True, "temporary", "unprotect", "protected")

    def unprotect(self, device_id):
        self.actions.append(("unprotect", device_id))
        if self.failure:
            raise self.failure
        return OperationResult("unprotect", device_id, True, "temporary", "protect", "unprotected")


class PolicyProvider(FakeProvider):
    def policy_state(self):
        return {"write_protect": 1, "autorun": 255}


def test_status_json(capsys):
    assert main(["--json", "status"], FakeProvider()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["platform"] == "test"
    assert payload["devices"][0]["identifier"] == "disk-test"


def test_status_includes_policy(capsys):
    assert main(["--json", "status"], PolicyProvider()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == {"write_protect": 1, "autorun": 255}


def test_protect_requires_confirmation(capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt="": "n")
    provider = FakeProvider()
    assert main(["protect", "--device", "disk-test"], provider) == 2
    assert provider.actions == []
    assert "Cancelled" in capsys.readouterr().out


def test_declining_json_keeps_stdout_machine_readable(capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt="": "n")
    provider = FakeProvider()
    assert main(["--json", "protect", "--device", "disk-test"], provider) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"cancelled": True, "device": "disk-test"}
    assert "This changes host-side USB controls" in captured.err


def test_closed_stdin_is_a_refusal(monkeypatch):
    provider = FakeProvider()

    def refuse(_prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", refuse)
    assert main(["--json", "protect", "--device", "disk-test"], provider) == 2
    assert provider.actions == []


def test_protect_yes_calls_provider(capsys):
    provider = FakeProvider()
    assert main(["--json", "protect", "--device", "disk-test", "--yes"], provider) == 0
    assert provider.actions == [("protect", "disk-test")]
    assert json.loads(capsys.readouterr().out)["verified"] is True


@pytest.mark.parametrize("error", [ProviderError("blocked"), OSError("denied"), ValueError("bad state")])
def test_provider_errors_produce_json_error(capsys, error):
    provider = FakeProvider()
    provider.failure = error
    assert main(["--json", "protect", "--device", "disk-test", "--yes"], provider) == 1
    assert json.loads(capsys.readouterr().out) == {"error": str(error)}
