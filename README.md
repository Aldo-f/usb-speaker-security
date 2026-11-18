# USB Security CLI

Cross-platform, host-side safety controls for explicitly selected removable
media. It reduces accidental writes from the current computer; it does **not**
provide hardware-enforced write blocking.

## Supported platforms

| Platform | Controls | Scope |
| --- | --- | --- |
| Windows 10/11 | USB write protection plus AutoPlay/AutoRun blocking | Persistent host policy |
| Linux | Per-device read-only/read-write control | Current boot session |
| macOS | Per-disk read-only/read-write mounting | Current mount session |

The tool never auto-selects a device and requires confirmation unless `--yes`
is supplied. On Linux and macOS it enumerates removable whole disks and rejects
internal disks and partitions. On Windows it lists USB-attached disks; confirm
the physical device before changing host policy. Every requested state is
verified after the change.

## Install from source

Python 3.11 or newer is required.

```bash
python -m pip install .
usb-security status
```

Use `usb-security --json status` when integrating with another tool.

## Protect and restore a device

First identify the exact removable whole-disk identifier:

```bash
usb-security status
```

Then protect or restore it:

```bash
usb-security protect --device <device-id>
usb-security unprotect --device <device-id>
```

Use `--yes` only for non-interactive automation after the exact device
identifier has been independently validated.

On Windows, `--device` selects which disk is confirmed but the resulting policy
is host-wide: `WriteProtect` and `NoDriveTypeAutoRun` are written under `HKLM`
and affect every USB storage device attached to the machine. Commands that
change policy must run from an elevated terminal. On Linux and macOS, the
platform may request administrator credentials only when a state change is
made.

## Legacy scripts

`usb-beveiligen.bat` and `usb_security_tool.sh` are temporary compatibility
wrappers that forward to the CLI. The Windows Sandbox and Toolwiz Time Freeze
menu actions are retired; use Windows settings or `winget` directly. The
startup trigger and its installer are also retired: run
`install_usb_trigger.bat /uninstall` once to remove files from an earlier
installation, then use `usb-security status` when needed.

## Testing and prereleases

- Automated unit tests run on Windows, Linux, and macOS runners.
- Build artifacts are unsigned prereleases until Windows signing and Apple
  notarization credentials are available.
- Follow [native acceptance testing](docs/acceptance-testing.md) with a
  disposable physical USB drive before promoting a release.

## License

MIT; see [LICENSE](LICENSE).
