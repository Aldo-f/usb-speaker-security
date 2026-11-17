# Native Acceptance Testing

Run these checks only with a disposable removable USB drive. The CLI provides
host-side controls; it does not provide hardware-enforced write blocking.

## Common checks

1. Install from source with `python -m pip install .`.
2. Run `usb-security --json status` and confirm the target drive is listed as
   a removable whole disk.
3. Confirm that an internal disk, a partition, and a missing identifier are
   rejected by `protect`.
4. Confirm that declining the interactive prompt makes no change.
5. Run `usb-security protect --device <id>`, verify the success response, and
   attempt a write to the disposable drive.
6. Run `usb-security unprotect --device <id>`, verify the success response,
   and confirm the write succeeds.
7. Repeat after reconnecting the device and after rebooting. Record whether the
   platform reports a persistent or session-only scope.

## Windows 11

- Run an elevated PowerShell session; protect must fail clearly without the
  required registry permission.
- Confirm `WriteProtect=1` and `NoDriveTypeAutoRun=255` after protection.
- Confirm the original values are restored after unprotect.
- Reconnect the drive before testing writes because Windows device drivers may
  cache the policy state.

## Linux

- Run the tool against a removable whole disk, never a partition.
- Confirm `lsblk -dn -o RO <device>` changes to `1` after protection and
  `0` after unprotect.
- Confirm that disconnecting the drive before verification produces a clear
  error and no other device is changed.

## macOS

- Confirm the selected `/dev/diskN` is external/removable and not internal.
- Confirm all selected volumes mount read-only after protection and are
  writable after unprotect.
- Confirm a failed read-only remount attempts to return the disk to a normal
  mount state and reports the failure.

Attach command output and the operating-system version to the release test
record before promoting an unsigned prerelease artifact.
