#!/usr/bin/env bash
# Compatibility wrapper for the legacy shell flags.
set -eo pipefail

echo "usb_security_tool.sh is a compatibility wrapper. Use usb-security instead." >&2

json_flag=""
yes_flag=""
declare -a rest=()
while (($#)); do
  case "$1" in
    --json) json_flag="--json"; shift ;;
    --yes) yes_flag="--yes"; shift ;;
    *) rest+=("$1"); shift ;;
  esac
done

if ((${#rest[@]} == 0)); then
  mode="status"
else
  mode="${rest[0]}"
  rest=("${rest[@]:1}")
fi

case "$mode" in
  --status) mode="status" ;;
  --set-readonly) mode="protect" ;;
  --set-writable) mode="unprotect" ;;
esac

declare -a args=()
if [[ -n "$json_flag" ]]; then args+=("$json_flag"); fi
args+=("$mode")
if [[ "$mode" == "protect" || "$mode" == "unprotect" ]]; then
  if ((${#rest[@]} == 0)); then
    printf 'Error: %s requires a device identifier.\n' "$mode" >&2
    exit 2
  fi
  args+=(--device "${rest[0]}")
  rest=("${rest[@]:1}")
  if [[ -n "$yes_flag" ]]; then args+=("$yes_flag"); fi
fi
args+=("${rest[@]}")

if command -v usb-security >/dev/null 2>&1; then
  exec usb-security "${args[@]}"
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$script_dir/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m usb_security.cli "${args[@]}"
