#!/usr/bin/env python3
"""Idempotent boot and environment edits with an original-file backup."""

import argparse
from pathlib import Path
import shutil

BEGIN = "# BEGIN T-Pot Mobile display"
END = "# END T-Pot Mobile display"
OVERLAYS = {
    "dtoverlay=vc4-kms-v3d",
    "dtoverlay=vc4-kms-dsi-7inch",
    "dtoverlay=vc4-kms-dsi-waveshare-panel,8_0_inch",
}


def save(path: Path, content: str) -> None:
    backup = path.with_name(path.name + ".tpotmobile.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
    temporary = path.with_name(path.name + ".tpotmobile.tmp")
    temporary.write_text(content)
    shutil.copymode(path, temporary)
    temporary.replace(path)


def boot_config(path: Path, display: str, overlays: Path) -> None:
    panel = "vc4-kms-dsi-7inch" if display == "43" else "vc4-kms-dsi-waveshare-panel"
    for name in ("vc4-kms-v3d", panel):
        if not (overlays / f"{name}.dtbo").is_file():
            raise ValueError(f"Kernel overlay missing: {name}.dtbo; update Trixie before installation")
    lines = []
    managed = False
    for line in path.read_text().splitlines():
        if line == BEGIN:
            if managed:
                raise ValueError("Nested mobile display configuration")
            managed = True
        elif line == END:
            if not managed:
                raise ValueError("Unmatched mobile display configuration")
            managed = False
        elif not managed and line.strip() not in OVERLAYS:
            if line.strip().startswith(("dtoverlay=vc4-kms-dsi", "dtoverlay=vc4-kms-v3d")):
                raise ValueError(f"Conflicting display overlay; review manually: {line}")
            lines.append(line)
    if managed:
        raise ValueError("Unterminated mobile display configuration")
    selected = "dtoverlay=vc4-kms-dsi-7inch" if display == "43" else "dtoverlay=vc4-kms-dsi-waveshare-panel,8_0_inch"
    while lines and not lines[-1].strip():
        lines.pop()
    lines += ["", BEGIN, "[all]", "dtoverlay=vc4-kms-v3d", selected, END]
    save(path, "\n".join(lines) + "\n")


def environment(path: Path) -> None:
    values = {"TPOT_TYPE": "MOBILE", "TPOT_PULL_POLICY": "missing"}
    lines = []
    for line in path.read_text().splitlines():
        key = line.partition("=")[0]
        if key not in values:
            lines.append(line)
    lines.extend(f"{key}={value}" for key, value in values.items())
    save(path, "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["boot", "env"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--display", choices=["43", "8"])
    parser.add_argument("--overlays", type=Path, default=Path("/boot/firmware/overlays"))
    args = parser.parse_args()
    if args.mode == "boot" and not args.display:
        parser.error("boot requires --display")
    if args.mode == "boot":
        boot_config(args.path, args.display, args.overlays)
    else:
        environment(args.path)


if __name__ == "__main__":
    main()
