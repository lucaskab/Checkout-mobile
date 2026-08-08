"""Convert generated green-screen product sheets into the game's individual sprites."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED_ROOT = Path(
	"/Users/lucas-furini/.codex/generated_images/019fc817-065c-75e0-a2e2-58dd427a1fa9"
)
SOURCE_ROOT = PROJECT_ROOT / "assets" / "game-art-source" / "product-sheets"
OUTPUT_ROOT = PROJECT_ROOT / "assets" / "game-art" / "products"
WORK_ROOT = Path("/private/tmp") / "product-imagegen-processing"
REMOVE_CHROMA_KEY = Path(
	"/Users/lucas-furini/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
)
FRAME_SIZE = 512

SHEETS = [
	("sheet-001-004-source.png", "exec-ab4d5046-aa3c-45f8-8cf2-8fa57b8f2b4e.png", (1, 5, 9, 24)),
	("sheet-002-006-source.png", "exec-ddf3104f-7d79-4ae5-b940-f4d731c4c5ad.png", (2, 3, 4, 6)),
	("sheet-003-011-source.png", "exec-5bd7d8e9-80f9-4ae5-83ec-6e6a86215a6c.png", (7, 8, 10, 11)),
	("sheet-004-015-source.png", "exec-5105c0ab-a12d-4e63-b345-9d63d52e5614.png", (12, 13, 14, 15)),
	("sheet-005-019-source.png", "exec-fc1be5f4-fadf-4d7a-9d62-bd43fd8fc661.png", (16, 17, 18, 19)),
	("sheet-006-023-source.png", "exec-87931737-191f-4744-8499-e45435512809.png", (20, 21, 22, 23)),
	("sheet-007-028-source.png", "exec-694e63f2-99bf-4fcf-aa40-6ba73285458b.png", (25, 26, 27, 28)),
	("sheet-008-032-source.png", "exec-dab9f134-659b-494d-966a-5852e94218cf.png", (29, 30, 31, 32)),
	("sheet-009-036-source.png", "exec-981f99b1-95e0-4190-8830-a6b4b589a118.png", (33, 34, 35, 36)),
	("sheet-010-040-source.png", "exec-cce089c1-0efa-4b5f-808b-5dc6250c41b4.png", (37, 38, 39, 40)),
	("sheet-011-044-source.png", "exec-fa2c093a-68cc-47d0-b8ed-9163a1872b99.png", (41, 42, 43, 44)),
	("sheet-012-103-source.png", "exec-cd6589f4-bda3-4ecc-bfc3-76c8c52b991e.png", (45, 101, 102, 103)),
	("sheet-013-107-source.png", "exec-dbae950e-a6df-4fce-aed1-a417cb6e1fe7.png", (104, 105, 106, 107)),
	("sheet-014-111-source.png", "exec-f0ef8c5a-daef-450d-aabb-fbcd5a4d97bb.png", (108, 109, 110, 111)),
]
SINGLE = ("product-112-source.png", "exec-4d0e3642-11e7-4162-bdbf-2908ab38869a.png", 112)


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


def write_tile(image: Image.Image, product_id: int, box: tuple[int, int, int, int] | None = None) -> None:
	if box:
		image = image.crop(box)
	image = image.resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.LANCZOS)
	# The generator can leave a thin white grid line at a sheet edge. Remove
	# that outer matte without changing the product silhouette.
	image = image.crop((12, 12, FRAME_SIZE - 12, FRAME_SIZE - 12)).resize(
		(FRAME_SIZE, FRAME_SIZE), Image.Resampling.LANCZOS
	)
	pixels = image.load()
	for y in range(FRAME_SIZE):
		for x in range(FRAME_SIZE):
			red, green, blue, alpha = pixels[x, y]
			if alpha < 32:
				pixels[x, y] = (0, 0, 0, 0)
	image.save(OUTPUT_ROOT / f"product-{product_id:03d}.png", format="PNG")


def process_sheet(source_name: str, generated_name: str, product_ids: tuple[int, ...]) -> None:
	source = SOURCE_ROOT / source_name
	generated = GENERATED_ROOT / generated_name
	shutil.copy2(generated, source)
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
	for product_id, box in zip(product_ids, boxes):
		write_tile(image, product_id, box)


def process_single(source_name: str, generated_name: str, product_id: int) -> None:
	source = SOURCE_ROOT / source_name
	generated = GENERATED_ROOT / generated_name
	shutil.copy2(generated, source)
	alpha_path = WORK_ROOT / f"{source.stem}-alpha.png"
	remove_background(source, alpha_path)
	image = Image.open(alpha_path).convert("RGBA")
	write_tile(image, product_id)


def main() -> None:
	SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
	OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
	WORK_ROOT.mkdir(parents=True, exist_ok=True)
	for source_name, generated_name, product_ids in SHEETS:
		process_sheet(source_name, generated_name, product_ids)
	process_single(*SINGLE)
	print("Processed 57 generated product sprites.")


if __name__ == "__main__":
	main()
