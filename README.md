# USB Security Tool

## Overview
A single Batch script to toggle USB security settings on Windows, with future Linux support.

## Features
- Toggle USB Write-Protection (Read-Only)
- Toggle Autoplay / Autorun
- Quick Protect: Enable both protections at once
- Start Windows Sandbox
- Install Toolwiz Time Freeze

## Installation
```bash
curl -sSL https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/usb-beveiligen.bat -o usb-beveiligen.bat && usb-beveiligen.bat
```

## Usage
1. Run the script as Administrator
2. Select an option from the menu
3. Follow the on-screen instructions

## Requirements
- Windows 10/11
- Administrator privileges
- Internet connection for Toolwiz Time Freeze installation

## Notes
- This script is part of the [USB Speaker Security](https://github.com/Aldo-f/usb-speaker-security) project
- For Linux support, use the equivalent `.sh` script

## License
MIT