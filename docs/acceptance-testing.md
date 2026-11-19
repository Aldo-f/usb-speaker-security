# Native Acceptance Testing

Run these checks only with a disposable removable USB drive. The CLI provides
host-side controls; it does not provide hardware-enforced write blocking.

## Common checks

1. Install the tool with `python -m pip install .` or the one-click installer
   (see [installation.md](installation.md)).
2. Run `usb-security --json status` and confirm the target drive is listed as
   a removable whole disk. On Windows, also confirm the reported policy values.
3. Confirm that an internal disk, a partition, and a missing identifier are
   rejected by `protect`.
4. Confirm that declining the interactive prompt makes no change.
5. Run `usb-security protect --device <id>` and verify the success response.
6. Complete the platform-specific steps below, including any reconnect that
   the platform requires for policy changes to take effect.
7. Attempt a write to the disposable drive. The write **must be rejected** while
   the device is protected; record the operating-system error text.
8. Run `usb-security unprotect --device <id>`, verify the success response,
   reconnect the drive if required by the platform, and confirm the write
   succeeds.
9. Repeat after reconnecting the device and after rebooting. Record whether the
   platform reports a persistent or session-only scope.

## Windows 11

- In an elevated PowerShell session, confirm that `protect` succeeds.
- From a non-elevated session, confirm that `protect` fails with a clear
  permission error instead of a traceback.
- Confirm `HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies\WriteProtect=1`
  and
  `HKLM\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\NoDriveTypeAutoRun=255`
  after protection.
- Confirm the original HKLM values are restored after unprotect.
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
