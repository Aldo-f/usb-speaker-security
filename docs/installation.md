# Installation

Install the `usb-security` command on Linux, Windows, or macOS with a one-click
installer, or install from source.

## Requirements

| Platform | Supported |
| --- | --- |
| Windows | Windows 10 or newer |
| Linux | Any Linux distribution that provides `lsblk` (util-linux) |
| macOS | Any macOS release supported by the tool (it uses `diskutil`/`plistlib` for device listing) |

All platforms require:

- Python 3.11 or newer with `pip`. On Windows, install Python from
  [python.org/downloads](https://www.python.org/downloads/). Apple's bundled
  `python3` on macOS is older than 3.11, so install a newer Python from
  [python.org/downloads/macos](https://www.python.org/downloads/macos/) or via
  Homebrew/Xcode Command Line Tools.
- Internet access to GitHub (`raw.githubusercontent.com` and
  `codeload.github.com`).

## One-click install

### Linux and macOS

```bash
curl -fsSL https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/install.sh | bash
```

Or download the script first and run it:

```bash
curl -fsSL https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/install.sh -o install-usb-security.sh
bash install-usb-security.sh
```

The installer:

- Detects the OS (`uname -s`: Linux or macOS).
- Verifies Python 3.11+ and `pip`.
- Installs the package with `python -m pip install --user` from the GitHub
  source archive
  `https://github.com/Aldo-f/usb-speaker-security/archive/refs/heads/main.zip`.
- Prints the next command: `usb-security status`.

The script is inspectable:
https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/install.sh

If `usb-security` is not on your `PATH` after installing (for example
`~/Library/Python/3.11/bin` on macOS), the installer prints the command that
still works, such as `python -m usb_security.cli status`.

### Windows (PowerShell 5.1 or later)

```powershell
iwr -useb https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/install.ps1 | iex
```

The installer:

- Requires Windows 10 or newer.
- Verifies Python 3.11+ (`python` or `python3`) and `pip`.
- Installs with `python -m pip install --user` from the same GitHub source
  archive URL as above.
- Prints the next command: `usb-security status`.

If `usb-security` is not found on your `PATH` after installing, the installer
prints the user Scripts directory and the fallback
`python -m usb_security.cli status`.

No UAC prompt appears and nothing is written outside your user Python
environment: the installer does not elevate.

Note: `iwr -useb ... | iex` executes the script from the pipe, so the default
PowerShell execution policy is not changed. If you save the script as a file
and run it that way, you may need
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` first.

## What the installers change

- The `usb-security` package is installed into your user Python environment:
  - Linux: `~/.local/lib/python3.X/site-packages/` plus the `usb-security`
    script in `~/.local/bin/`.
  - macOS: `~/Library/Python/3.X/site-packages/` plus
    `~/Library/Python/3.X/bin/`.
  - Windows: `%APPDATA%\Python\PythonXX\site-packages\` plus the
    `usb-security.exe` script in the user Scripts directory.
- Nothing else is installed or modified: no scheduled tasks, startup entries,
  or system services.
- Protecting or unprotecting a device later
  (`usb-security protect --device <id>` / `usb-security unprotect --device <id>`)
  writes host policy per the platform rules in the README: host-wide HKLM
  policy on Windows (requires elevation), temporary kernel device state on
  Linux, and temporary mount state on macOS.

Note that the installers fetch the current `main` branch, so they install the
latest development version of the tool.

## Upgrade

Re-run the one-click command, or:

```bash
python -m pip install --user --upgrade usb-security
```

## Uninstall / cleanup

```bash
python -m pip uninstall -y usb-security
```

The one-click installers leave no other residue: they are plain scripts and
consume the source archive with `pip`. On Windows, uninstall with the same
`pip` command; the installer creates no HKLM or ProgramData files.

If you previously ran `install_usb_trigger.bat /uninstall` (the retired
startup launcher), that is unrelated to this package.

## Troubleshooting

- `Error: usb-security requires Python 3.11 or newer ...` — install Python 3.11+
  from https://www.python.org/downloads/, then re-run the installer.
- `pip is not available for ...` — install `pip` for the Python you have
  (`python -m ensurepip --user`, or via your system package manager, for
  example `apt install python3-pip` or `brew install python`).
- On Linux, if `usb-security` is not on your `PATH`: check `ls ~/.local/bin`
  and run `echo $PATH`.
- Offline environments: clone the repository and run `python -m pip install .`.

## Security notes

- All URLs use HTTPS; the installers download from GitHub only.
- The installers require no elevation and change nothing outside the user's
  Python environment.
- Review the scripts before running:
  - https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/install.sh
  - https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/install.ps1
