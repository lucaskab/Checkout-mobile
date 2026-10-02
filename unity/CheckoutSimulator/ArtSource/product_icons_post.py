import os, sys
from PIL import Image, ImageDraw
import numpy as np

REN = "/mnt/user-data/uploads/Checkout-mobile/unity/CheckoutSimulator/ArtSource/Review/icons_v1/render"
OLD = "/mnt/user-data/uploads/Checkout-mobile/unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Products"
OUT = "/mnt/user-data/outputs/icons128"
SHEET = "/mnt/user-data/outputs/contact.png"
os.makedirs(OUT, exist_ok=True)
NEW = [f"product-{i:03d}" for i in range(46, 62)]
OLDS = ["product-001", "product-005", "product-009", "product-021", "product-026", "product-035"]


def downscale(src, dst, size=128, fill=0.88):
    im = Image.open(src).convert("RGBA")
    # crop to alpha bbox and re-centre so the longest side fills `fill` of the icon
    al = np.asarray(im)[..., 3]
    ys, xs = np.where(al > 8)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    w, h = x1 - x0, y1 - y0
    side = int(round(max(w, h) / fill))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im.crop((x0, y0, x1, y1)), ((side - w) // 2, (side - h) // 2))
    im = canvas
    a = np.asarray(im).astype(np.float32) / 255.0
    rgb = a[..., :3] * a[..., 3:4]
    pm = np.concatenate([rgb, a[..., 3:4]], axis=-1)
    small = Image.fromarray((pm * 255).round().astype(np.uint8), "RGBA").resize((size, size), Image.LANCZOS)
    s = np.asarray(small).astype(np.float32) / 255.0
    al = np.clip(s[..., 3:4], 1e-4, 1.0)
    rgb = np.clip(s[..., :3] / al, 0, 1)
    # match the old icons: a touch more saturation and contrast
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    rgb = np.clip(lum[..., None] + (rgb - lum[..., None]) * 1.22, 0, 1)
    rgb = np.clip((rgb - 0.5) * 1.08 + 0.5, 0, 1)
    out = np.concatenate([rgb, s[..., 3:4]], axis=-1)
    out[..., 3][s[..., 3] < 0.004] = 0
    Image.fromarray((out * 255).round().astype(np.uint8), "RGBA").save(dst, optimize=True)


for n in NEW:
    downscale(os.path.join(REN, n + ".png"), os.path.join(OUT, n + ".png"))

# contact sheet: icons at 2x, new (16) then old (6)
cell = 300
cols = 6
items = [(n, os.path.join(OUT, n + ".png"), "new") for n in NEW] + [(n, os.path.join(OLD, n + ".png"), "old") for n in OLDS]
rows = (len(items) + cols - 1) // cols
sheet = Image.new("RGBA", (cols * cell, rows * cell + 10), (205, 205, 205, 255))
d = ImageDraw.Draw(sheet)
for i, (n, p, kind) in enumerate(items):
    x = (i % cols) * cell; y = (i // cols) * cell
    im = Image.open(p).convert("RGBA").resize((256, 256), Image.LANCZOS)
    if kind == "old":
        d.rectangle([x + 4, y + 4, x + cell - 4, y + cell - 4], outline=(120, 120, 120, 255), width=2)
    sheet.alpha_composite(im, (x + 22, y + 14))
    d.text((x + 24, y + cell - 24), n + (" (old)" if kind == "old" else ""), fill=(40, 40, 40, 255))
sheet.convert("RGB").save(SHEET)
print("ok")
