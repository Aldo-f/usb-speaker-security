# Test Plan

## Automated checks

- GitHub Actions runs unit tests on Windows, Linux, and macOS runners.
- The build job produces source and wheel distributions plus an unsigned
  one-file executable on each platform.

## Windows manual checks

Run these from an elevated Command Prompt or PowerShell unless a step says
otherwise. Use a disposable USB drive.

1. Run `usb-security status`; confirm the USB disk is listed and the HKLM
   policy values are reported.
2. Run `usb-security protect --device <id>`; confirm success,
   `WriteProtect=1`, and `NoDriveTypeAutoRun=255` under HKLM. Reconnect the
   drive and confirm writes are rejected.
3. Run `usb-security unprotect --device <id>`; confirm success and that the
   original HKLM values are restored. Reconnect the drive and confirm writes
   succeed.
4. Confirm declining the confirmation prompt makes no change, and that a
   non-elevated session reports a clear permission error.
5. Run `install_usb_trigger.bat /uninstall` twice: both runs must succeed, and
   the Startup copy, both desktop shortcuts, and the ProgramData directory
   must be gone.

## Linux manual checks

Use only a disposable removable drive.

1. Run `usb-security status` and confirm removable whole disks are listed.
2. Run `usb-security protect --device /dev/sdX` using the exact removable
   whole-disk path; confirm `lsblk -dn -o RO /dev/sdX` returns `1`.
3. Run `usb-security unprotect --device /dev/sdX` and confirm the value returns
   to `0`.
4. Verify that a partition path, a non-removable disk, and a nonexistent path
   are rejected without a state change.
5. Verify that replacing or disconnecting the device before verification
   produces a clear error and leaves other disks untouched.

## macOS manual checks

Use only a disposable removable disk.

1. Run `usb-security status` and confirm the external whole disk is listed.
2. Protect and unprotect it, confirming every mounted volume becomes read-only
   and then writable again.
3. Verify that internal disks and partitions are rejected.

See [native acceptance testing](docs/acceptance-testing.md) for the full
release test record.
