from __future__ import annotations

import json
import os
import platform
import plistlib
import re
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import Device, OperationResult


class ProviderError(RuntimeError):
    """Raised when a platform control cannot be safely completed."""


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, check=True, text=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        raise ProviderError(detail) from exc


class PlatformProvider(ABC):
    platform_name: str

    @abstractmethod
    def list_devices(self) -> list[Device]:
        raise NotImplementedError

    @abstractmethod
    def protect(self, device_id: str) -> OperationResult:
        raise NotImplementedError

    @abstractmethod
    def unprotect(self, device_id: str) -> OperationResult:
        raise NotImplementedError

    def require_device(self, device_id: str) -> Device:
        for device in self.list_devices():
            if device.identifier == device_id:
                if not device.removable or not device.whole_disk:
                    raise ProviderError("Choose a confirmed removable whole-disk device.")
                return device
        raise ProviderError("Device was not found among confirmed removable whole disks.")

    def policy_state(self) -> dict[str, Any] | None:
        """Return current platform policy values, when the platform has any."""
        return None


class LinuxProvider(PlatformProvider):
    platform_name = "linux"

    def _records(self) -> list[dict[str, Any]]:
        completed = run_command(
            ["lsblk", "--json", "-o", "NAME,PATH,TYPE,RM,RO,MODEL,TRAN,SERIAL,SIZE"]
        )
        return json.loads(completed.stdout).get("blockdevices", [])

    def list_devices(self) -> list[Device]:
        devices: list[Device] = []
        for record in self._records():
            if record.get("type") != "disk" or not bool(record.get("rm")):
                continue
            devices.append(
                Device(
                    identifier=record["path"],
                    name=(record.get("model") or record["name"]).strip(),
                    removable=True,
                    whole_disk=True,
                    read_only=bool(record.get("ro")),
                    transport=record.get("tran"),
                )
            )
        return devices

    def _device_record(self, device_id: str) -> dict[str, Any]:
        for record in self._records():
            if record.get("path") == device_id:
                return record
        raise ProviderError("Device disappeared before the operation could be completed.")

    @staticmethod
    def _identity(record: dict[str, Any]) -> tuple[object, ...]:
        """Fields that identify the physical disk without including its write state."""
        return (
            str(record.get("path") or ""),
            str(record.get("name") or ""),
            str(record.get("model") or ""),
            str(record.get("serial") or ""),
            str(record.get("size") or ""),
            str(record.get("tran") or ""),
            bool(record.get("rm")),
        )

    def _confirmed_record(self, device_id: str) -> dict[str, Any]:
        self.require_device(device_id)
        identity = self._identity(self._device_record(device_id))
        record = self._device_record(device_id)
        if self._identity(record) != identity:
            raise ProviderError("Removable device identity changed; refusing to change state.")
        return record

    def _verify(self, device_id: str, identity: tuple[object, ...], read_only: bool) -> None:
        record = self._device_record(device_id)
        if self._identity(record) != identity:
            raise ProviderError("Removable device identity changed during the operation.")
        if bool(record.get("ro")) != read_only:
            state = "read-only" if read_only else "read-write"
            raise ProviderError(f"Linux did not report the requested {state} state.")

    def protect(self, device_id: str) -> OperationResult:
        record = self._confirmed_record(device_id)
        identity = self._identity(record)
        run_command(["sudo", "blockdev", "--setro", device_id])
        self._verify(device_id, identity, True)
        return OperationResult(
            action="protect",
            device=device_id,
            verified=True,
            scope="Temporary kernel device state for this boot session",
            rollback=f"Run usb-security unprotect --device {device_id}",
            details="The selected removable whole disk is read-only on this host.",
        )

    def unprotect(self, device_id: str) -> OperationResult:
        record = self._confirmed_record(device_id)
        identity = self._identity(record)
        run_command(["sudo", "blockdev", "--setrw", device_id])
        self._verify(device_id, identity, False)
        return OperationResult(
            action="unprotect",
            device=device_id,
            verified=True,
            scope="Temporary kernel device state for this boot session",
            rollback=f"Run usb-security protect --device {device_id}",
            details="The selected removable whole disk is writable on this host.",
        )


class WindowsProvider(PlatformProvider):
    platform_name = "windows"
    _write_key = r"SYSTEM\CurrentControlSet\Control\StorageDevicePolicies"
    _auto_key = r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"

    def _winreg(self) -> Any:
        try:
            import winreg
        except ImportError as exc:
            raise ProviderError("Windows registry APIs are unavailable.") from exc
        return winreg

    def _read_dword(self, hive: Any, key: str, name: str, default: int) -> int:
        winreg = self._winreg()
        try:
            with winreg.OpenKey(hive, key) as opened:
                return int(winreg.QueryValueEx(opened, name)[0])
        except FileNotFoundError:
            return default

    def _write_dword(self, hive: Any, key: str, name: str, value: int) -> None:
        winreg = self._winreg()
        with winreg.CreateKeyEx(hive, key, 0, winreg.KEY_SET_VALUE) as opened:
            winreg.SetValueEx(opened, name, 0, winreg.REG_DWORD, value)

    def _policy_state(self) -> dict[str, int]:
        winreg = self._winreg()
        return {
            "write_protect": self._read_dword(winreg.HKEY_LOCAL_MACHINE, self._write_key, "WriteProtect", 0),
            "autorun": self._read_dword(winreg.HKEY_LOCAL_MACHINE, self._auto_key, "NoDriveTypeAutoRun", 145),
        }

    def policy_state(self) -> dict[str, Any] | None:
        return self._policy_state()

    def _state_path(self) -> Path:
        root = Path(os.environ.get("PROGRAMDATA", tempfile.gettempdir())) / "USB-Security-CLI"
        root.mkdir(parents=True, exist_ok=True)
        return root / "prior-policy.json"

    @staticmethod
    def _write_baseline(path: Path, before: dict[str, int]) -> None:
        """Persist the baseline atomically so a failed write cannot leave partial state."""
        temporary = path.with_name(f".{path.name}.tmp")
        try:
            temporary.write_text(json.dumps(before), encoding="utf-8")
            os.replace(temporary, path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _read_baseline(path: Path) -> dict[str, int]:
        """Read and validate a saved baseline so an unreadable one cannot strand protection."""
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            return {
                "write_protect": int(saved["write_protect"]),
                "autorun": int(saved["autorun"]),
            }
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ProviderError("The saved Windows policy state could not be read.") from exc

    def list_devices(self) -> list[Device]:
        script = (
            "Get-CimInstance Win32_DiskDrive | "
            "Where-Object { $_.InterfaceType -eq 'USB' } | "
            "Select-Object DeviceID,Model,Index | ConvertTo-Json -Compress"
        )
        completed = run_command(["powershell", "-NoProfile", "-Command", script])
        payload = json.loads(completed.stdout or "[]")
        records = payload if isinstance(payload, list) else [payload]
        return [
            Device(
                identifier=str(record["DeviceID"]),
                name=str(record.get("Model") or record["DeviceID"]).strip(),
                removable=True,
                whole_disk=True,
                read_only=None,
                transport="USB",
            )
            for record in records
        ]

    def _restore(self, before: dict[str, int]) -> None:
        winreg = self._winreg()
        self._write_dword(winreg.HKEY_LOCAL_MACHINE, self._write_key, "WriteProtect", before["write_protect"])
        self._write_dword(winreg.HKEY_LOCAL_MACHINE, self._auto_key, "NoDriveTypeAutoRun", before["autorun"])

    def protect(self, device_id: str) -> OperationResult:
        self.require_device(device_id)
        before = self._policy_state()
        path = self._state_path()
        if path.exists():
            # Refuse to change policy if the saved baseline cannot be restored later.
            self._read_baseline(path)
            created_baseline = False
        else:
            self._write_baseline(path, before)
            created_baseline = True
        try:
            winreg = self._winreg()
            self._write_dword(winreg.HKEY_LOCAL_MACHINE, self._write_key, "WriteProtect", 1)
            self._write_dword(winreg.HKEY_LOCAL_MACHINE, self._auto_key, "NoDriveTypeAutoRun", 255)
            if self._policy_state() != {"write_protect": 1, "autorun": 255}:
                raise ProviderError("Windows did not report the requested policy values.")
        except Exception:
            try:
                self._restore(before)
            except Exception:
                pass
            if created_baseline:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        return OperationResult(
            action="protect",
            device=device_id,
            verified=True,
            scope="Persistent host-wide Windows policy",
            rollback=f"Run usb-security unprotect --device {device_id}",
            details="USB write protection and host-wide AutoPlay/AutoRun blocking are enabled for this host.",
        )

    def unprotect(self, device_id: str) -> OperationResult:
        self.require_device(device_id)
        path = self._state_path()
        if not path.exists():
            raise ProviderError("No saved Windows policy state was found; run protect before unprotect.")
        before = self._read_baseline(path)
        self._restore(before)
        if self._policy_state() != before:
            raise ProviderError("Windows did not restore the saved policy values.")
        path.unlink()
        return OperationResult(
            action="unprotect",
            device=device_id,
            verified=True,
            scope="Persistent host-wide Windows policy",
            rollback=f"Run usb-security protect --device {device_id}",
            details="The prior Windows USB and AutoPlay/AutoRun policy values were restored.",
        )


class MacProvider(PlatformProvider):
    platform_name = "macos"

    def _info(self, identifier: str) -> dict[str, Any]:
        completed = run_command(["diskutil", "info", "-plist", identifier])
        return plistlib.loads(completed.stdout.encode())

    def _disk_ids(self) -> list[str]:
        completed = run_command(["diskutil", "list", "-plist"])
        payload = plistlib.loads(completed.stdout.encode())
        return [str(value) for value in payload.get("AllDisks", []) if re.fullmatch(r"disk[0-9]+", str(value))]

    def list_devices(self) -> list[Device]:
        devices: list[Device] = []
        for identifier in self._disk_ids():
            info = self._info(identifier)
            if not (info.get("RemovableMedia") or info.get("Ejectable")):
                continue
            devices.append(
                Device(
                    identifier=f"/dev/{identifier}",
                    name=str(info.get("MediaName") or identifier),
                    removable=True,
                    whole_disk=True,
                    read_only=None,
                    transport="USB or external media",
                )
            )
        return devices

    def _disk_identifier(self, device_id: str) -> str:
        return Path(device_id).name

    def _volume_writable(self, disk_id: str) -> list[bool]:
        completed = run_command(["diskutil", "list", "-plist", disk_id])
        payload = plistlib.loads(completed.stdout.encode())
        values: list[bool] = []
        for identifier in payload.get("AllDisks", []):
            if str(identifier) == disk_id:
                continue
            info = self._info(str(identifier))
            if "WritableVolume" in info:
                values.append(bool(info["WritableVolume"]))
        return values

    def protect(self, device_id: str) -> OperationResult:
        self.require_device(device_id)
        disk_id = self._disk_identifier(device_id)
        try:
            run_command(["diskutil", "unmountDisk", disk_id])
            run_command(["diskutil", "mountDisk", "readOnly", disk_id])
            writable = self._volume_writable(disk_id)
            if not writable or any(writable):
                raise ProviderError("macOS did not report every mounted volume as read-only.")
        except Exception:
            run_command(["diskutil", "mountDisk", disk_id])
            raise
        return OperationResult(
            action="protect",
            device=device_id,
            verified=True,
            scope="Current macOS mount session",
            rollback=f"Run usb-security unprotect --device {device_id}",
            details="The selected external disk was remounted read-only on this host.",
        )

    def unprotect(self, device_id: str) -> OperationResult:
        self.require_device(device_id)
        disk_id = self._disk_identifier(device_id)
        run_command(["diskutil", "unmountDisk", disk_id])
        run_command(["diskutil", "mountDisk", disk_id])
        writable = self._volume_writable(disk_id)
        if not writable or not all(writable):
            raise ProviderError("macOS did not report every mounted volume as writable.")
        return OperationResult(
            action="unprotect",
            device=device_id,
            verified=True,
            scope="Current macOS mount session",
            rollback=f"Run usb-security protect --device {device_id}",
            details="The selected external disk was remounted read-write on this host.",
        )


def get_provider(system_name: str | None = None) -> PlatformProvider:
    name = (system_name or platform.system()).lower()
    if name == "linux":
        return LinuxProvider()
    if name == "windows":
        return WindowsProvider()
    if name == "darwin":
        return MacProvider()
    raise ProviderError(f"Unsupported platform: {system_name or platform.system()}.")
