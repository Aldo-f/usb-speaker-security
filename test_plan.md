# Test Plan

## Windows manual checks

Run `usb-beveiligen.bat` from an elevated Command Prompt or PowerShell.

1. **USB write protection**
   - Enable write protection and confirm the registry value is
     `HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies\WriteProtect = 1`.
   - Reconnect a disposable USB drive and confirm writes are blocked.
   - Disable write protection and confirm the value becomes `0`.

2. **AutoPlay/AutoRun protection**
   - Enable protection and confirm
     `HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\NoDriveTypeAutoRun = 255`.
   - Restore standard behavior and confirm the value becomes `145`.
   - Reconnect a test drive after each state change.

3. **Windows Sandbox**
   - On a supported Windows edition, test starting Sandbox when already enabled.
   - Test enabling it and verify the restart requirement is shown.

4. **Status launcher**
   - Run `install_usb_trigger.bat` twice and confirm installation remains
     successful.
   - Sign out and back in; the status launcher should display once and exit.
   - Run `install_usb_trigger.bat /uninstall` and verify the Startup copy and
     desktop shortcut are removed.

5. **Toolwiz installation**
   - Test on a system with `winget`; decline the confirmation once and accept
     it once.
   - Test on a system without `winget` and confirm the script provides a
     clear error.

## Linux manual checks

Use only a disposable removable drive.

1. Run `./usb_security_tool.sh --status` and confirm removable devices are
   listed.
2. Run `./usb_security_tool.sh --set-readonly /dev/sdX` using the exact
   removable whole-disk path. Confirm `lsblk -dn -o RO /dev/sdX` returns
   `1`.
3. Run `./usb_security_tool.sh --set-writable /dev/sdX` and confirm the
   value returns to `0`.
4. Verify that a partition path, a non-removable disk, and a nonexistent path
   are rejected without a state change.

## Automated checks

GitHub Actions verifies Bash syntax and checks that the status launcher remains
single-run rather than an infinite process loop.
