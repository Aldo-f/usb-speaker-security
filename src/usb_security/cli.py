from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Sequence

from .providers import PlatformProvider, ProviderError, get_provider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="usb-security",
        description="Host-side safety controls for explicitly selected removable media.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("status", help="List confirmed removable whole disks and platform policy state.")
    for command, help_text in (
        ("protect", "Protect one explicitly selected removable whole disk."),
        ("unprotect", "Restore one explicitly selected removable whole disk."),
    ):
        subparser = subcommands.add_parser(command, help=help_text)
        subparser.add_argument("--device", required=True, help="Exact device identifier returned by status.")
        subparser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation.")
    return parser


def emit(value: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    if isinstance(value, dict) and "devices" in value:
        print(f"Platform: {value['platform']}")
        print(f"Protection scope: {value['scope']}")
        devices = value["devices"]
        if not devices:
            print("No confirmed removable whole-disk devices found.")
        for device in devices:
            state = "unknown" if device["read_only"] is None else ("read-only" if device["read_only"] else "read-write")
            print(f"- {device['identifier']}: {device['name']} ({state})")
        return
    if isinstance(value, dict):
        print(value["details"])
        print(f"Scope: {value['scope']}")
        print(f"Rollback: {value['rollback']}")


def confirm(command: str, device: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    answer = input(f"{command.title()} {device}? This changes host-side USB controls. [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def execute(args: argparse.Namespace, provider: PlatformProvider) -> tuple[int, object]:
    if args.command == "status":
        return 0, {
            "platform": provider.platform_name,
            "scope": "Host-side controls only; this tool does not provide hardware-enforced write blocking.",
            "devices": [device.as_dict() for device in provider.list_devices()],
        }
    if not confirm(args.command, args.device, args.yes):
        return 2, {"cancelled": True, "device": args.device}
    result = provider.protect(args.device) if args.command == "protect" else provider.unprotect(args.device)
    return 0, result.as_dict()


def main(argv: Sequence[str] | None = None, provider: PlatformProvider | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code, result = execute(args, provider or get_provider())
    except (ProviderError, PermissionError) as exc:
        if args.as_json:
            print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    emit(result, args.as_json)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
