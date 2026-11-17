# USB Security Tool Roadmap

## Current implementation

- Windows: toggle USB write protection and AutoPlay/AutoRun protection, with
  elevated-rights checks and state verification.
- Windows: optional Windows Sandbox and Toolwiz Time Freeze actions.
- Windows: one-time sign-in status launcher with installation and removal.
- Linux: explicit removable-device inspection and temporary read-only/read-write
  control for a user-supplied whole disk.

## Safety principles

1. Never select or modify a Linux device automatically.
2. Require confirmation before Windows policy or feature changes.
3. Verify a requested policy change after writing it.
4. Prefer a controlled, one-time launcher over persistent process loops.
5. Clearly distinguish Windows-only functionality from Linux behavior.

## Future work

1. Add automated Windows integration tests on a self-hosted or disposable VM.
2. Add a packaged installer with code signing for Windows distribution.
3. Add optional Linux mount profiles using `noexec,nodev,nosuid`, with explicit
   mount-point and device selection.
4. Add localization and accessibility review for the interactive Windows menu.
5. Document enterprise policy interactions, Group Policy precedence, and
   supported Windows editions.
