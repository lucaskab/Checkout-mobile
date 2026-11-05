"""Writes Unity .meta files for new textures with the import settings the game needs (Unity would make default ones).

usage: python3 scripts/art/unity_meta.py [--mask] [--readable] <png> [<png> ...]
  --readable  Read/Write on (the brand tints these pictures on the CPU, CheckoutBrand.cs)
  --mask      also no compression and linear-ish use (masks must keep exact values)
An existing .meta keeps its guid (only the flags change).
"""
import re
import sys
import uuid
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / "unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Products/product-171.png.meta"


def write(png: Path, readable: bool, mask: bool):
    meta = png.with_name(png.name + ".meta")
    text = TEMPLATE.read_text()
    guid = None
    if meta.exists():
        m = re.search(r"^guid: ([0-9a-f]{32})", meta.read_text(), re.M)
        guid = m.group(1) if m else None
    text = re.sub(r"^guid: [0-9a-f]{32}", f"guid: {guid or uuid.uuid4().hex}", text, flags=re.M)
    text = text.replace("  isReadable: 0", f"  isReadable: {1 if readable else 0}")
    text = text.replace("  alphaIsTransparency: 0", "  alphaIsTransparency: 1")
    if mask:
        text = text.replace("    textureCompression: 1", "    textureCompression: 0")
        text = text.replace("    enableMipMap: 1", "    enableMipMap: 0")
    meta.write_text(text)


def main():
    args = sys.argv[1:]
    readable = "--readable" in args
    mask = "--mask" in args
    for a in args:
        if a.startswith("--"):
            continue
        write(Path(a), readable or mask, mask)
        print("meta", a)


if __name__ == "__main__":
    main()
