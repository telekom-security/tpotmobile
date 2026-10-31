"""Render the already extracted canonical ANSI pixels as offline PNG assets."""

import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def main() -> None:
    data = (ROOT / "tools/design/splash-data.js").read_text()
    payload = json.loads(data.split("window.tpotSplash = ", 1)[1].rstrip().removesuffix(";"))
    for variant, name in (("80x24", "43"), ("120", "8")):
        grid = payload["grids"][variant]
        width, height = grid["width"], grid["height"]
        if len(grid["pixels"]) != width * height:
            raise ValueError("Invalid canonical pixel dimensions")
        pixels = bytearray()
        for y in range(height):
            pixels.append(0)
            for x in range(width):
                index = grid["pixels"][y * width + x]
                pixels.extend([*payload["palette"][index], 255 if index else 0])
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(bytes(pixels))) + chunk(b"IEND", b"")
        (ROOT / f"images/splash_{name}.png").write_bytes(png)


if __name__ == "__main__":
    main()
