import json
from types import SimpleNamespace

import pytest

from usb_security.models import Device
from usb_security.providers import (
    LinuxProvider,
    MacProvider,
    PlatformProvider,
    ProviderError,
    WindowsProvider,
)


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


@pytest.mark.parametrize("provider_class", [LinuxProvider, WindowsProvider, MacProvider])
@pytest.mark.parametrize("device_id", ["internal", "partition", "missing"])
def test_real_providers_reject_devices_before_running_commands(monkeypatch, provider_class, device_id):
    provider = provider_class()
    monkeypatch.setattr(provider, "list_devices", RejectingProvider().list_devices)

    def unexpected_command(_args):
        raise AssertionError("a platform command must not run for an unconfirmed device")

    monkeypatch.setattr("usb_security.providers.run_command", unexpected_command)
    for operation in (provider.protect, provider.unprotect):
        with pytest.raises(ProviderError):
            operation(device_id)


@pytest.fixture
def windows_env(tmp_path, monkeypatch):
    provider = WindowsProvider()
    values = {"write_protect": 0, "autorun": 145}
    events = []

    class FakeWinreg:
        HKEY_LOCAL_MACHINE = "HKLM"

    def fake_write(hive, key, name, value):
        assert hive == "HKLM"
        events.append((name, value))
        if name == "WriteProtect":
            values["write_protect"] = value
        else:
            values["autorun"] = value

    monkeypatch.setattr(provider, "_winreg", lambda: FakeWinreg())
    monkeypatch.setattr(provider, "_policy_state", lambda: dict(values))
    monkeypatch.setattr(provider, "_write_dword", fake_write)
    monkeypatch.setattr(provider, "list_devices", lambda: [Device("usb-disk", "USB", True, True, None)])
    state_path = tmp_path / "prior-policy.json"
    monkeypatch.setattr(provider, "_state_path", lambda: state_path)
    return provider, values, events, state_path


def test_windows_baseline_is_persisted_before_policy_changes(windows_env, monkeypatch):
    provider, values, events, state_path = windows_env

    def cannot_persist(_path, _before):
        raise OSError("no space left")

    monkeypatch.setattr(provider, "_write_baseline", cannot_persist)
    with pytest.raises(OSError):
        provider.protect("usb-disk")
    assert values == {"write_protect": 0, "autorun": 145}
    assert events == []
    assert not state_path.exists()


def test_windows_failed_change_rolls_back_and_removes_new_baseline(windows_env, monkeypatch):
    provider, values, events, state_path = windows_env
    original_write = provider._write_dword

    def fail_second_write(hive, key, name, value):
        if name == "NoDriveTypeAutoRun" and value == 255:
            raise OSError("access denied")
        original_write(hive, key, name, value)

    monkeypatch.setattr(provider, "_write_dword", fail_second_write)
    with pytest.raises(OSError):
        provider.protect("usb-disk")
    assert values == {"write_protect": 0, "autorun": 145}
    assert not state_path.exists()


def test_windows_repeat_protect_preserves_original_baseline(windows_env):
    provider, values, events, state_path = windows_env
    provider.protect("usb-disk")
    provider.protect("usb-disk")
    assert json.loads(state_path.read_text(encoding="utf-8")) == {"write_protect": 0, "autorun": 145}
    provider.unprotect("usb-disk")
    assert values == {"write_protect": 0, "autorun": 145}
    assert not state_path.exists()


def test_windows_unprotect_requires_saved_state(windows_env):
    provider, values, events, state_path = windows_env
    with pytest.raises(ProviderError, match="No saved Windows policy state"):
        provider.unprotect("usb-disk")
    assert events == []


def test_windows_protect_writes_both_policy_values(windows_env):
    provider, values, events, state_path = windows_env
    assert provider.policy_state() == {"write_protect": 0, "autorun": 145}
    provider.protect("usb-disk")
    assert all(name in {"WriteProtect", "NoDriveTypeAutoRun"} for name, _ in events)
    assert values == {"write_protect": 1, "autorun": 255}


def test_windows_policy_state_reads_hklm(monkeypatch):
    provider = WindowsProvider()
    read_calls = []

    class FakeWinreg:
        HKEY_LOCAL_MACHINE = "HKLM"

    def fake_read(hive, key, name, default):
        read_calls.append((hive, key, name, default))
        return default

    monkeypatch.setattr(provider, "_winreg", lambda: FakeWinreg())
    monkeypatch.setattr(provider, "_read_dword", fake_read)

    assert provider.policy_state() == {"write_protect": 0, "autorun": 145}
    assert len(read_calls) == 2
    assert all(hive == "HKLM" for hive, _, _, _ in read_calls)
    assert read_calls[0][1:3] == (WindowsProvider._write_key, "WriteProtect")
    assert read_calls[1][1:3] == (WindowsProvider._auto_key, "NoDriveTypeAutoRun")


def test_windows_protect_refuses_corrupt_baseline(windows_env):
    provider, values, events, state_path = windows_env
    state_path.write_text("not json", encoding="utf-8")
    with pytest.raises(ProviderError, match="saved Windows policy state could not be read"):
        provider.protect("usb-disk")
    assert values == {"write_protect": 0, "autorun": 145}
    assert events == []
    assert state_path.read_text(encoding="utf-8") == "not json"


def _linux_record(**overrides):
    record = {
        "name": "sdb",
        "path": "/dev/sdb",
        "type": "disk",
        "rm": 1,
        "ro": 0,
        "model": "USB Drive",
        "tran": "usb",
        "serial": "SERIAL-1",
        "size": "8G",
    }
    record.update(overrides)
    return record


def test_linux_rejects_device_swap_before_changing_state(monkeypatch):
    provider = LinuxProvider()
    commands = []
    records = [_linux_record(), _linux_record(), _linux_record(serial="SERIAL-2")]

    monkeypatch.setattr(provider, "_records", lambda: [records.pop(0)] if records else [_linux_record(serial="SERIAL-2")])
    monkeypatch.setattr(
        "usb_security.providers.run_command",
        lambda args: commands.append(args) or SimpleNamespace(stdout="{}"),
    )
    with pytest.raises(ProviderError, match="identity changed"):
        provider.protect("/dev/sdb")
    assert commands == []


def test_linux_protect_verifies_write_state(monkeypatch):
    provider = LinuxProvider()
    commands = []
    state = {"ro": 0}

    monkeypatch.setattr(provider, "_records", lambda: [_linux_record(ro=state["ro"])])

    def fake_command(args):
        commands.append(args)
        state["ro"] = 1
        return SimpleNamespace(stdout="{}")

    monkeypatch.setattr("usb_security.providers.run_command", fake_command)
    result = provider.protect("/dev/sdb")
    assert result.verified is True
    assert commands == [["sudo", "blockdev", "--setro", "/dev/sdb"]]


def test_linux_protect_rejects_when_write_state_did_not_change(monkeypatch):
    provider = LinuxProvider()
    state = {"ro": 0}
    monkeypatch.setattr(provider, "_records", lambda: [_linux_record(ro=state["ro"])])
    monkeypatch.setattr(
        "usb_security.providers.run_command",
        lambda _args: SimpleNamespace(stdout="{}"),
    )
    with pytest.raises(ProviderError, match="did not report the requested read-only state"):
        provider.protect("/dev/sdb")


def test_linux_missing_device_is_reported(monkeypatch):
    provider = LinuxProvider()
    monkeypatch.setattr(provider, "_records", lambda: [])
    with pytest.raises(ProviderError):
        provider.protect("/dev/sdb")


def test_macos_rejects_non_removable_external_disk(monkeypatch):
    provider = MacProvider()
    monkeypatch.setattr(provider, "_disk_ids", lambda: ["disk2"])
    monkeypatch.setattr(
        provider,
        "_info",
        lambda _identifier: {
            "MediaName": "External SSD",
            "Internal": False,
            "RemovableMedia": False,
            "Ejectable": False,
        },
    )
    assert provider.list_devices() == []


def test_macos_lists_ejectable_external_disk(monkeypatch):
    provider = MacProvider()
    monkeypatch.setattr(provider, "_disk_ids", lambda: ["disk2"])
    monkeypatch.setattr(
        provider,
        "_info",
        lambda _identifier: {
            "MediaName": "USB Drive",
            "Internal": False,
            "RemovableMedia": True,
            "Ejectable": True,
        },
    )
    devices = provider.list_devices()
    assert len(devices) == 1
    assert devices[0].identifier == "/dev/disk2"
