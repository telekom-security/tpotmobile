"""Extract the public, pinned T-Pot ANSI pixel data without executing its code."""

import ast
import base64
import json
from pathlib import Path
import subprocess
import zlib

COMMIT = "0df39a8752df8d2849359998ad7b14f59ce66e1c"


def main() -> None:
    source = subprocess.run(
        ["gh", "api", f"repos/telekom-security/tpotce/contents/tpotctl/splash_art.py?ref={COMMIT}", "--jq", ".content"],
        capture_output=True, text=True, check=True,
    )
    tree = ast.parse(base64.b64decode(source.stdout).decode())
    data = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("PALETTE", "GRIDS"):
                    data[target.id] = ast.literal_eval(node.value)
    grids = {}
    for name in ("80x24", "120"):
        width, height, packed = data["GRIDS"][name]
        pixels = zlib.decompress(base64.b64decode(packed))
        if len(pixels) != width * height or max(pixels) >= len(data["PALETTE"]):
            raise ValueError("Invalid canonical splash grid")
        grids[name] = {"width": width, "height": height, "pixels": list(pixels)}
    output = {"source": f"telekom-security/tpotce@{COMMIT}/tpotctl/splash_art.py",
              "palette": data["PALETTE"], "grids": grids}
    (Path(__file__).parent / "splash-data.js").write_text(
        "// Generated canonical T-Pot ANSI pixel data; upstream GPL-3.0.\nwindow.tpotSplash = "
        + json.dumps(output, separators=(",", ":")) + ";\n",
    )


if __name__ == "__main__":
    main()
