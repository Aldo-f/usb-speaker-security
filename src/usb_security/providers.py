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


class LinuxProvider(PlatformProvider):
    platform_name = "linux"

    def _records(self) -> list[dict[str, Any]]:
        completed = run_command(["lsblk", "--json", "-o", "NAME,PATH,TYPE,RM,RO,MODEL,TRAN"])
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

    def _read_only(self, device_id: str) -> bool:
        for record in self._records():
            if record.get("path") == device_id:
                return bool(record.get("ro"))
        raise ProviderError("Device disappeared before verification.")

    def protect(self, device_id: str) -> OperationResult:
        self.require_device(device_id)
        run_command(["sudo", "blockdev", "--setro", device_id])
        if not self._read_only(device_id):
            raise ProviderError("Linux did not report the requested read-only state.")
        return OperationResult(
            action="protect",
            device=device_id,
            verified=True,
            scope="Temporary kernel device state for this boot session",
            rollback=f"Run usb-security unprotect --device {device_id}",
            details="The selected removable whole disk is read-only on this host.",
        )

    def unprotect(self, device_id: str) -> OperationResult:
        self.require_device(device_id)
        run_command(["sudo", "blockdev", "--setrw", device_id])
        if self._read_only(device_id):
            raise ProviderError("Linux did not report the requested read-write state.")
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
            "autorun": self._read_dword(winreg.HKEY_CURRENT_USER, self._auto_key, "NoDriveTypeAutoRun", 145),
        }

    def _state_path(self) -> Path:
        root = Path(os.environ.get("PROGRAMDATA", tempfile.gettempdir())) / "USB-Security-CLI"
        root.mkdir(parents=True, exist_ok=True)
        return root / "prior-policy.json"

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

    def protect(self, device_id: str) -> OperationResult:
        self.require_device(device_id)
        before = self._policy_state()
        try:
            winreg = self._winreg()
            self._write_dword(winreg.HKEY_LOCAL_MACHINE, self._write_key, "WriteProtect", 1)
            self._write_dword(winreg.HKEY_CURRENT_USER, self._auto_key, "NoDriveTypeAutoRun", 255)
            after = self._policy_state()
            if after != {"write_protect": 1, "autorun": 255}:
                raise ProviderError("Windows did not report the requested policy values.")
        except Exception:
            winreg = self._winreg()
            self._write_dword(winreg.HKEY_LOCAL_MACHINE, self._write_key, "WriteProtect", before["write_protect"])
            self._write_dword(winreg.HKEY_CURRENT_USER, self._auto_key, "NoDriveTypeAutoRun", before["autorun"])
            raise
        self._state_path().write_text(json.dumps(before), encoding="utf-8")
        return OperationResult(
            action="protect",
            device=device_id,
            verified=True,
            scope="Persistent host-wide Windows policy",
            rollback=f"Run usb-security unprotect --device {device_id}",
            details="USB write protection and AutoPlay/AutoRun blocking are enabled for this host.",
        )

    def unprotect(self, device_id: str) -> OperationResult:
        self.require_device(device_id)
        path = self._state_path()
        before = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"write_protect": 0, "autorun": 145}
        winreg = self._winreg()
        self._write_dword(winreg.HKEY_LOCAL_MACHINE, self._write_key, "WriteProtect", int(before["write_protect"]))
        self._write_dword(winreg.HKEY_CURRENT_USER, self._auto_key, "NoDriveTypeAutoRun", int(before["autorun"]))
        if self._policy_state() != before:
            raise ProviderError("Windows did not restore the saved policy values.")
        if path.exists():
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
            removable = bool(info.get("RemovableMedia") or info.get("Ejectable") or not info.get("Internal", True))
            if not removable:
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
