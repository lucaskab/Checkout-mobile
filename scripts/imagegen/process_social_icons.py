"""Cut the Codex social icon sheet (2x2 on #00FF00) into game icons, like scripts/imagegen/process_game_icon_sheets.py.

Usage: python3 process_social_icons.py <sheet.png> <outdir>
Writes <outdir>/512/<name>.png (assets/game-art/icons) and <outdir>/128/<name>.png (Resources/CheckoutDesktop/Icons).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

NAMES = ("friends", "like", "share", "invite")


def key_green(img: Image.Image) -> Image.Image:
	a = np.asarray(img.convert("RGB")).astype(np.float32)
	r, g, b = a[..., 0], a[..., 1], a[..., 2]
	# How much greener than the other channels: 0 = not green, high = background.
	excess = g - np.maximum(r, b)
	alpha = 1.0 - np.clip((excess - 24.0) / (110.0 - 24.0), 0.0, 1.0)
	# Despill: clamp green to the max of red/blue where it leaks.
	spill = g > np.maximum(r, b)
	g2 = np.where(spill, np.maximum(r, b) + (g - np.maximum(r, b)) * 0.15, g)
	out = np.dstack([r, g2, b, alpha * 255.0]).clip(0, 255).astype(np.uint8)
	return Image.fromarray(out, "RGBA")


def fit(tile: Image.Image, size: int, margin: float = 0.07) -> Image.Image:
	bbox = tile.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
	if bbox:
		tile = tile.crop(bbox)
	inner = int(size * (1 - 2 * margin))
	scale = inner / max(tile.width, tile.height)
	tile = tile.resize((max(1, round(tile.width * scale)), max(1, round(tile.height * scale))), Image.Resampling.LANCZOS)
	frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))
	frame.alpha_composite(tile, ((size - tile.width) // 2, (size - tile.height) // 2))
	px = np.asarray(frame).copy()
	px[px[..., 3] < 32] = 0
	return Image.fromarray(px, "RGBA")


def main() -> None:
	sheet = Image.open(sys.argv[1]).convert("RGBA")
	out = Path(sys.argv[2])
	(out / "512").mkdir(parents=True, exist_ok=True)
	(out / "128").mkdir(parents=True, exist_ok=True)
	keyed = key_green(sheet)
	w, h = keyed.size
	alpha = np.asarray(keyed.getchannel("A")) > 24

	def gap(profile, centre):
		# The empty line nearest the centre (icons may cross the exact middle a little).
		empty = np.where(~profile)[0]
		return int(empty[np.argmin(np.abs(empty - centre))]) if len(empty) else centre

	hh = gap(alpha.any(axis=1), h // 2)
	boxes = []
	for y0, y1 in ((0, hh), (hh, h)):
		hw = gap(alpha[y0:y1].any(axis=0), w // 2)
		boxes += [(0, y0, hw, y1), (hw, y0, w, y1)]
	for name, box in zip(NAMES, boxes):
		tile = keyed.crop(box)
		big = fit(tile, 512)
		big.save(out / "512" / f"{name}.png")
		big.resize((128, 128), Image.Resampling.LANCZOS).save(out / "128" / f"{name}.png")
	print("ok", [n for n in NAMES])


if __name__ == "__main__":
	main()
