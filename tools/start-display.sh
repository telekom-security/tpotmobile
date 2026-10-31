#!/usr/bin/env bash
set -euo pipefail

for ((attempt = 0; attempt < 100; attempt++)); do
    if [[ -S /run/tpotmobile/wayland-0 ]]; then
        exec /opt/tpotmobile/.venv/bin/python3 /opt/tpotmobile/display.py
    fi
    sleep 0.1
done
echo "Weston did not create /run/tpotmobile/wayland-0 within 10 seconds." >&2
exit 1
