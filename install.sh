#!/usr/bin/env bash
# One-click installer for usb-security on Linux and macOS.
#
# Usage (Linux or macOS):
#   curl -fsSL https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/install.sh | bash
# Direct script link:
#   https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/install.sh
set -euo pipefail

repo_zip="https://github.com/Aldo-f/usb-speaker-security/archive/refs/heads/main.zip"
minimum_python="3.11"
minor_floor="${minimum_python#3.}"

fail() {
    echo "Error: $*" >&2
    exit 1
}

uname_s="$(uname -s)"
case "$uname_s" in
    Darwin | Linux) ;;
    *) fail "Unsupported operating system ($uname_s). This installer supports Linux and macOS." ;;
esac

python_bin=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        python_bin="$candidate"
        break
    fi
done
if [[ -z "$python_bin" ]]; then
    fail "Python $minimum_python or newer is required. Install Python from https://www.python.org/downloads/ and re-run this script."
fi

version=""
if ! version="$("$python_bin" --version 2>&1)"; then
    fail "Could not run $python_bin --version to check the Python version."
fi
version_regex='^Python[[:space:]]+([0-9]+)\.([0-9]+)'
if [[ ! "$version" =~ $version_regex ]]; then
    fail "Could not determine the Python version from '$version'. Install Python $minimum_python or newer."
fi
major="${BASH_REMATCH[1]}"
minor="${BASH_REMATCH[2]}"
if (( major < 3 )) || (( major == 3 && minor < minor_floor )); then
    fail "usb-security requires Python $minimum_python or newer; found $version."
fi

if ! "$python_bin" -m pip --version >/dev/null 2>&1; then
    fail "pip is not available for $python_bin. Install it with: $python_bin -m ensurepip --user"
fi

# PEP 668: Debian and its derivatives (including Raspberry Pi OS) mark the
# system Python with an EXTERNALLY-MANAGED file in the stdlib directory.
# pip refuses to install anything there (even with --user), so the installer
# retries with --break-system-packages when that marker is present. The
# override only lifts the check; the install still goes to the user site.
externally_managed() {
    local marker
    marker="$("$python_bin" -c 'import sysconfig, os; print(os.path.join(sysconfig.get_path("stdlib"), "EXTERNALLY-MANAGED"))' 2>/dev/null)" || return 1
    [[ -n "$marker" && -f "$marker" ]]
}

echo "Installing usb-security (user-level install; requires network)..."
if ! "$python_bin" -m pip install --user "$repo_zip"; then
    if externally_managed; then
        echo "The Python environment is externally managed; retrying with --user --break-system-packages..." >&2
        "$python_bin" -m pip install --user --break-system-packages "$repo_zip"
    else
        "$python_bin" -m pip install "$repo_zip"
    fi
fi

echo
echo "usb-security installed."
echo "Run: usb-security status"
if ! command -v usb-security >/dev/null 2>&1; then
    echo "If 'usb-security' is not found on your PATH, run:"
    echo "  $python_bin -m usb_security.cli status"
fi
