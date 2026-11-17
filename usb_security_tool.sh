#!/usr/bin/env bash
set -euo pipefail
echo "usb_security_tool.sh is a compatibility wrapper. Use usb-security instead." >&2
exec python3 -m usb_security.cli "$@"
