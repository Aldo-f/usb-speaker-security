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

The tool never auto-selects a device. It rejects internal disks and partitions,
requires confirmation unless `--yes` is supplied, and verifies each requested
state after changing it.

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

On Windows, commands that change policy must be run from an elevated terminal.
On Linux and macOS, the platform may request administrator credentials only when
a state change is made.

## Legacy scripts

`usb-beveiligen.bat` and `usb_security_tool.sh` are temporary compatibility
wrappers. The startup trigger and its installer are retired; use
`usb-security status` directly.

## Testing and prereleases

- Automated unit tests run on Windows, Linux, and macOS runners.
- Build artifacts are unsigned prereleases until Windows signing and Apple
  notarization credentials are available.
- Follow [native acceptance testing](docs/acceptance-testing.md) with a
  disposable physical USB drive before promoting a release.

## License

MIT
