"""Post-process for product_icons_v2 (run outside Blender):
    python3 product_icons_v2_post.py <render_dir> <out_products_dir> <existing_products_dir> <sheet.jpg>
Crops each render to its alpha bounds, re-centres it so the longest side fills 86 % of the icon, downsizes to 512 px
(premultiplied Lanczos), adds a touch of saturation / contrast like the v1 icons, and writes product-NNN.png (RGBA).
Then builds a contact sheet: the 50 new icons next to ten existing ones (marked) for the style check.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REN, OUT, OLD, SHEET = sys.argv[1:5]
NEW = ["product-%03d" % i for i in range(122, 172)]
OLDS = ["product-001", "product-005", "product-033", "product-045", "product-062", "product-103", "product-105",
        "product-115", "product-119", "product-121"]
NAMES = {122: "Morango", 123: "Abacate", 124: "Cogumelos", 125: "Frutas exóticas", 126: "Água de coco", 127: "Kombucha",
         128: "Cerveja artesanal", 129: "Espumante rosé", 130: "Bisnaguinha", 131: "Pão integral", 132: "Fermentação natural",
         133: "Brioche", 134: "Requeijão", 135: "Iogurte grego", 136: "Gorgonzola", 137: "Salame italiano", 138: "Pipoca doce",
         139: "Brigadeiro gourmet", 140: "Macarons", 141: "Bombons belgas", 142: "Molho de tomate", 143: "Azeite extravirgem",
         144: "Café em cápsulas", 145: "Azeite trufado", 146: "Sabonete", 147: "Amaciante", 148: "Perfume", 149: "Kit spa",
         150: "Nuggets", 151: "Polpa de fruta", 152: "Risoto congelado", 153: "Pizza napolitana", 154: "Picolé de frutas",
         155: "Açaí na tigela", 156: "Picolé gourmet", 157: "Bolo de sorvete", 158: "Pão de queijo", 159: "Torta de morango",
         160: "Burrata", 161: "Canastra maturado", 162: "Linguiça artesanal", 163: "Picanha wagyu", 164: "Limonada suíça",
         165: "Smoothie de açaí", 166: "Ceviche", 167: "Lagosta grelhada", 168: "Milkshake", 169: "Gelato de pistache",
         170: "Vinho rosé da casa", 171: "Espumante da casa"}
os.makedirs(OUT, exist_ok=True)


def finish(src, dst, size=512, fill=.86):
    im = Image.open(src).convert("RGBA")
    al = np.asarray(im)[..., 3]
    ys, xs = np.where(al > 8)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    w, h = x1 - x0, y1 - y0
    side = int(round(max(w, h) / fill))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im.crop((x0, y0, x1, y1)), ((side - w) // 2, (side - h) // 2))
    a = np.asarray(canvas).astype(np.float32) / 255.0
    pm = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], axis=-1)
    small = Image.fromarray((pm * 255).round().astype(np.uint8), "RGBA").resize((size, size), Image.LANCZOS)
    s = np.asarray(small).astype(np.float32) / 255.0
    al = np.clip(s[..., 3:4], 1e-4, 1.0)
    rgb = np.clip(s[..., :3] / al, 0, 1)
    lum = rgb @ np.array([.299, .587, .114], dtype=np.float32)
    rgb = np.clip(lum[..., None] + (rgb - lum[..., None]) * 1.22, 0, 1)
    rgb = np.clip((rgb - .5) * 1.06 + .5, 0, 1)
    out = np.concatenate([rgb, s[..., 3:4]], axis=-1)
    out[..., 3][s[..., 3] < .004] = 0
    Image.fromarray((out * 255).round().astype(np.uint8), "RGBA").save(dst, optimize=True)


for n in NEW:
    p = os.path.join(REN, n + ".png")
    if os.path.exists(p):
        finish(p, os.path.join(OUT, n + ".png"))

# contact sheet: 10 existing icons (grey frame) on the first row, then the 50 new ones
cell, cols = 220, 10
items = [(n, os.path.join(OLD, n + ".png"), "old") for n in OLDS] + [(n, os.path.join(OUT, n + ".png"), "new") for n in NEW]
rows = (len(items) + cols - 1) // cols
sheet = Image.new("RGBA", (cols * cell, rows * cell + 40), (214, 214, 214, 255))
d = ImageDraw.Draw(sheet)
try:
    f = ImageFont.truetype(os.path.join(os.path.dirname(OLD), "..", "..", "unity", "CheckoutSimulator", "Assets", "Resources", "CheckoutDesktop", "Fonts", "Fredoka_600SemiBold.ttf"), 15)
except Exception:
    f = ImageFont.load_default()
d.text((10, 8), "Row 1: existing icons (framed) for comparison.  Rows 2-6: new exclusive products 122-171.", fill=(40, 40, 40, 255), font=f)
for i, (n, p, kind) in enumerate(items):
    x = (i % cols) * cell; y = (i // cols) * cell + 40
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGBA").resize((180, 180), Image.LANCZOS)
    if kind == "old":
        d.rectangle([x + 3, y + 3, x + cell - 3, y + cell - 3], outline=(120, 120, 120, 255), width=2)
    sheet.alpha_composite(im, (x + 20, y + 6))
    num = int(n[-3:])
    label = "%03d %s" % (num, NAMES.get(num, "(existing)"))
    d.text((x + 8, y + cell - 28), label, fill=(30, 30, 30, 255), font=f)
sheet.convert("RGB").save(SHEET, quality=88)
print("ok", len(NEW))
