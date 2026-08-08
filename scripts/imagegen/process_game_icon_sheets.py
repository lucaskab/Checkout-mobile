"""Convert generated green-screen UI icon sheets into individual game PNGs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "assets" / "game-art-source" / "icon-sheets"
OUTPUT_ROOT = PROJECT_ROOT / "assets" / "game-art" / "icons"
WORK_ROOT = Path("/private/tmp") / "game-icon-imagegen-processing"
REMOVE_CHROMA_KEY = Path(
	"/Users/lucas-furini/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
)
FRAME_SIZE = 512

SHEETS: tuple[tuple[str, tuple[str, str, str, str]], ...] = (
	("core.png", ("coin", "diamond", "market", "clipboard")),
	("operations.png", ("package", "shelf", "delivery-truck", "warehouse")),
	("technology.png", ("computer", "scanner", "robot", "ai-brain")),
	("equipment.png", ("cart", "basket", "refrigerator", "freezer")),
	("marketing.png", ("banner", "billboard", "radio", "television")),
	("logistics.png", ("forklift", "pallet", "distribution-center", "conveyor")),
	("goals.png", ("manager", "customers", "trophy", "target")),
	("status.png", ("lock", "key", "warning", "success")),
	("decor.png", ("plant", "garden", "fountain", "light")),
	("events.png", ("smartphone", "festival", "price-tag", "lightning")),
	("events-2.png", ("graduation", "receipt", "rain", "construction")),
	("events-3.png", ("calculator", "fuel-pump", "car", "toolbox")),
	("extra-core.png", ("bank", "gift", "crown", "drone")),
	("extra-ui.png", ("ticket", "broom", "controller", "medal")),
	("extra-actions.png", ("sleepy", "handshake", "hammer", "flame")),
)


def remove_background(source: Path, destination: Path) -> None:
	command = [
		sys.executable,
		str(REMOVE_CHROMA_KEY),
		"--input",
		str(source),
		"--out",
		str(destination),
		"--auto-key",
		"none",
		"--key-color",
		"#00ff00",
		"--soft-matte",
		"--transparent-threshold",
		"24",
		"--opaque-threshold",
		"220",
		"--despill",
		"--force",
	]
	subprocess.run(command, check=True)


def write_tile(image: Image.Image, icon_name: str, box: tuple[int, int, int, int]) -> None:
	tile = image.crop(box).resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.LANCZOS)
	# Remove the thin white separator generated between quadrants.
	tile = tile.crop((12, 12, FRAME_SIZE - 12, FRAME_SIZE - 12)).resize(
		(FRAME_SIZE, FRAME_SIZE), Image.Resampling.LANCZOS
	)
	pixels = tile.load()
	for y in range(FRAME_SIZE):
		for x in range(FRAME_SIZE):
			red, green, blue, alpha = pixels[x, y]
			if alpha < 32:
				pixels[x, y] = (0, 0, 0, 0)
	tile.save(OUTPUT_ROOT / f"{icon_name}.png", format="PNG")


def process_sheet(source_name: str, icon_names: tuple[str, str, str, str]) -> None:
	source = SOURCE_ROOT / source_name
	alpha_path = WORK_ROOT / f"{source.stem}-alpha.png"
	remove_background(source, alpha_path)
	image = Image.open(alpha_path).convert("RGBA")
	width, height = image.size
	half_width, half_height = width // 2, height // 2
	boxes = (
		(16, 16, half_width - 16, half_height - 16),
		(half_width + 16, 16, width - 16, half_height - 16),
		(16, half_height + 16, half_width - 16, height - 16),
		(half_width + 16, half_height + 16, width - 16, height - 16),
	)
	for icon_name, box in zip(icon_names, boxes):
		write_tile(image, icon_name, box)


def main() -> None:
	OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
	WORK_ROOT.mkdir(parents=True, exist_ok=True)
	for source_name, icon_names in SHEETS:
		process_sheet(source_name, icon_names)
	print(f"Processed {len(SHEETS) * 4} generated game icons.")


if __name__ == "__main__":
	main()
