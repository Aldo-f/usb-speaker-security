# USB Security Tool

A small, defensive USB-security utility for Windows and Linux. It helps reduce
the risk of writing to removable media unintentionally and of automatically
handling media content.

## Supported platforms

- **Windows 10/11:** USB write protection and AutoPlay/AutoRun policy controls.
  Administrator rights are required to make policy changes.
- **Linux:** status inspection plus an explicit, temporary read-only/read-write
  switch for a removable whole-disk device. The tool never selects a device for
  you.

Windows Sandbox and Toolwiz Time Freeze are Windows-only optional features.

## Windows

Download the repository, open PowerShell as Administrator, then run:

```powershell
.\usb-beveiligen.bat
```

The menu can:

1. Toggle the Windows USB write-protection registry policy.
2. Block AutoPlay and AutoRun for all drive types, or restore the standard
   Windows AutoPlay policy.
3. Enable both protections together.
4. Start or enable Windows Sandbox when the edition supports it.
5. Install Toolwiz Time Freeze through `winget`, after confirmation.

After changing USB write protection, reconnect removable drives. These policies
reduce risk but cannot guarantee that every device, driver, or application will
honor the setting.

### Optional status launcher

```powershell
.\install_usb_trigger.bat
```

This installs a one-time status launcher in the current user's Startup folder
and creates a desktop shortcut. It reports the policy state and exits; it does
not repeatedly open programs or create background loops.

Remove it with:

```powershell
.\install_usb_trigger.bat /uninstall
```

## Linux

Inspect removable devices:

```bash
chmod +x usb_security_tool.sh
./usb_security_tool.sh --status
```

Temporarily make one removable whole-disk device read-only:

```bash
./usb_security_tool.sh --set-readonly /dev/sdX
```

Restore that device to read-write mode:

```bash
./usb_security_tool.sh --set-writable /dev/sdX
```

Replace `/dev/sdX` with the exact device shown by `--status`. Do not use a
partition such as `/dev/sdX1`. The Linux setting is temporary and may reset
after reconnecting the device or rebooting.

Linux generally does not execute USB media automatically by default. For
untrusted media, mount it with `noexec,nodev,nosuid` where appropriate.

## Verification

- Run the Windows menu from an elevated Command Prompt or PowerShell and
  confirm each policy state after making a change.
- Run `usb_security_tool.sh --status` before any Linux device change, then
  verify the device read-only flag after the command completes.
- Use the included GitHub Actions workflow to check Bash syntax and guard
  against regressions in the status launcher.

## License

MIT
