"""RENDER-ONLY preview of the sector name written on the E_NamePanel quad (the game writes it at runtime with
TextMeshPro, auto-sized into 90% x 84% of the quad, navy on cream). One image per quad aspect.

    python3 sector_name_preview.py <out_dir> <font.ttf> <NAME> <aspect> <file_stem>
"""
import sys
from PIL import Image, ImageDraw, ImageFont

out, font_path, name, aspect, stem = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5]
H = 160
W = int(H * aspect)
im = Image.new("RGB", (W, H), (244, 235, 216))
d = ImageDraw.Draw(im)
size = H
while size > 8:
    f = ImageFont.truetype(font_path, size)
    l, t, r, b = d.textbbox((0, 0), name, font=f)
    if r - l <= W * .9 and b - t <= H * .62:
        break
    size -= 2
l, t, r, b = d.textbbox((0, 0), name, font=f)
d.text(((W - (r - l)) / 2 - l, (H - (b - t)) / 2 - t), name, font=f, fill=(28, 43, 79))
im.save("%s/%s.png" % (out, stem))
