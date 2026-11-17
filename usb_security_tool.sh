#!/usr/bin/env bash
# Linux USB Security Tool
# This tool changes only an explicitly named block device.

set -u

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

require_linux() {
  [[ "$(uname -s)" == "Linux" ]] || die "This script supports Linux only."
}

list_removable() {
  printf '%-12s %-8s %-8s %s\n' "DEVICE" "READ-ONLY" "MOUNTED" "MODEL"
  lsblk -dn -o NAME,RM,RO,MODEL | awk '$2 == 1 {model = $0; sub(/^[^ ]+ +[^ ]+ +[^ ]+ */, "", model); printf "/dev/%-7s %-8s %-8s %s\n", $1, ($3 == 1 ? "yes" : "no"), "-", model}'
}

status() {
  require_linux
  echo "Removable block devices:"
  list_removable
  echo
  echo "Linux does not execute programs from USB media automatically by default."
  echo "For additional protection, mount untrusted media with noexec,nodev,nosuid."
}

validate_device() {
  local device="$1"
  [[ -b "$device" ]] || die "$device is not a block device."
  [[ "$(lsblk -dn -o TYPE "$device" 2>/dev/null)" == "disk" ]] || die "Choose a whole disk such as /dev/sdb, not a partition."
  [[ "$(lsblk -dn -o RM "$device" 2>/dev/null)" == "1" ]] || die "$device is not reported as removable."
}

set_read_only() {
  local device="$1"
  validate_device "$device"
  sudo blockdev --setro "$device"
  [[ "$(lsblk -dn -o RO "$device")" == "1" ]] || die "The kernel did not report $device as read-only."
  echo "$device is read-only for this boot session. Reconnect the device before use."
}

set_writable() {
  local device="$1"
  validate_device "$device"
  sudo blockdev --setrw "$device"
  [[ "$(lsblk -dn -o RO "$device")" == "0" ]] || die "The kernel did not report $device as writable."
  echo "$device is writable for this boot session."
}

usage() {
  cat <<'EOF'
Usage:
  usb_security_tool.sh --status
  usb_security_tool.sh --set-readonly /dev/sdX
  usb_security_tool.sh --set-writable /dev/sdX

The script never chooses a device for you. Read-only changes are temporary
kernel settings and may be reset after reconnecting or rebooting.
EOF
}

main() {
  require_linux
  case "${1:---status}" in
    --status) status ;;
    --set-readonly) [[ $# -eq 2 ]] || die "--set-readonly requires a device path."; set_read_only "$2" ;;
    --set-writable) [[ $# -eq 2 ]] || die "--set-writable requires a device path."; set_writable "$2" ;;
    --help|-h) usage ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
