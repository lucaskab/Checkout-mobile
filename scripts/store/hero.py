"""App Store cover screenshot (Lucas 08/11: "uma imagem mostrando o jogo lá no final já... com tudo liberado, o mercado
lotado, para chamar a atenção"): a Unity still of the full chain (2778x1284) with the title in the trailer's style.

usage: python3 hero.py <still.jpg> <pt|en> <out.png> [clean]
"""
import sys
from PIL import Image, ImageDraw, ImageFilter
import titles

src, lang, out = sys.argv[1:4]
clean = len(sys.argv) > 4 and sys.argv[4] == "clean"
im = Image.open(src).convert("RGB")
W, H = im.size
im = Image.eval(im, lambda v: v)  # (as rendered)
if clean:
    im.save(out); raise SystemExit

KICK = "SUA REDE DE SUPERMERCADOS" if lang == "pt" else "YOUR OWN SUPERMARKET CHAIN"
HEAD = ["Da mesinha ao", "hipermercado!"] if lang == "pt" else ["From street stall", "to megastore!"]

import os
k = W / 2778 * float(os.environ.get("TEXT_SCALE", "1"))
base = im.convert("RGBA")
# a soft navy shade in the top-left corner, under the words
shade = Image.new("L", (W, H), 0); sd = ImageDraw.Draw(shade)
sd.ellipse([int(-900 * k), int(-760 * k), int(1650 * k), int(760 * k)], fill=190)
shade = shade.filter(ImageFilter.GaussianBlur(170 * k))
navy = Image.new("RGBA", (W, H), (14, 20, 44, 255)); navy.putalpha(shade)
base = Image.alpha_composite(base, navy)

fh = titles.font("Fredoka_700Bold.ttf", int(158 * k)); fk = titles.font("Fredoka_700Bold.ttf", int(64 * k))
x0, y0, gap = int(120 * k), int(330 * k), int(168 * k)
# headline shadow, then the words (white, the last line gold) with a thick navy outline
sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(sh)
for j, line in enumerate(HEAD):
    d.text((x0 + 8 * k, y0 + j * gap + 14 * k), line, font=fh, fill=(0, 0, 0, 170), stroke_width=int(18 * k), stroke_fill=(0, 0, 0, 170), anchor="ls")
base = Image.alpha_composite(base, sh.filter(ImageFilter.GaussianBlur(14 * k)))
d = ImageDraw.Draw(base)
for j, line in enumerate(HEAD):
    d.text((x0, y0 + j * gap), line, font=fh, fill=(255, 226, 120) if j == len(HEAD) - 1 else titles.WHITE,
           stroke_width=int(16 * k), stroke_fill=titles.NAVY, anchor="ls")
# the gold kicker pill above
tw = d.textlength(KICK, font=fk); px, py = int(44 * k), int(22 * k)
top = y0 - int(276 * k)
box = [x0, top, x0 + tw + px * 2, top + int(64 * k) + py * 2]
d.rounded_rectangle([box[0], box[1] + 9 * k, box[2], box[3] + 9 * k], radius=56 * k, fill=(150, 100, 20, 255))
d.rounded_rectangle(box, radius=56 * k, fill=titles.GOLD + (255,), outline=titles.NAVY + (255,), width=max(3, int(7 * k)))
d.text((x0 + px, top + py + int(55 * k)), KICK, font=fk, fill=titles.NAVY, anchor="ls")
base.convert("RGB").save(out, quality=95)
print(out, base.size)
