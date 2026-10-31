#!/usr/bin/python3
"""Root-owned, narrowly scoped hardware helper installed outside the checkout."""

import argparse
import configparser
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def backlight(root: Path = Path("/sys/class/backlight")) -> Path:
    candidates = [
        device for device in root.iterdir()
        if "dsi" in str(device.resolve()).lower()
        or device.name == "rpi_backlight"
        or re.fullmatch(r"\d+-0045", device.name)
    ]
    if len(candidates) != 1:
        raise ValueError(f"Expected one DSI backlight, found {len(candidates)}")
    return candidates[0]


def brightness(percentage: int, root: Path = Path("/sys/class/backlight")) -> dict[str, int]:
    if not 5 <= percentage <= 100:
        raise ValueError("Brightness must be between 5 and 100 percent")
    device = backlight(root)
    maximum = int((device / "max_brightness").read_text())
    if maximum <= 0:
        raise ValueError("Backlight has an invalid maximum")
    value = max(1, round(maximum * percentage / 100))
    (device / "brightness").write_text(str(value))
    return {"brightness": round(value / maximum * 100)}


def status(config: Path = Path("/etc/tpotmobile.ini")) -> dict[str, list[dict[str, str]]]:
    settings = configparser.ConfigParser()
    with config.open() as stream:
        settings.read_file(stream)
    project = settings["tpot"]["project"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", project):
        raise ValueError("Invalid configured compose project")
    result = subprocess.run(
        ["/usr/bin/docker", "ps", "--all", "--filter",
         f"label=com.docker.compose.project={project}", "--format", "{{json .}}"],
        capture_output=True, text=True, timeout=3, check=True,
    )
    containers = []
    for line in result.stdout.splitlines():
        entry = json.loads(line)
        containers.append({
            "name": entry["Names"], "state": entry["State"], "status": entry["Status"],
        })
    return {"containers": containers}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["brightness", "status", "reboot", "poweroff"])
    parser.add_argument("percentage", type=int, nargs="?")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("This helper must be invoked through its installed sudo policy")
    if (args.action == "brightness") != (args.percentage is not None):
        parser.error("Only brightness accepts a percentage, and requires it")
    try:
        if args.action == "brightness":
            result = brightness(args.percentage)
        elif args.action == "status":
            result = status()
        else:
            subprocess.run(["/usr/bin/systemctl", args.action], timeout=3, check=True)
            result = {"requested": args.action}
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError, configparser.Error, subprocess.SubprocessError) as error:
        print(f"T-Pot Mobile control failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
