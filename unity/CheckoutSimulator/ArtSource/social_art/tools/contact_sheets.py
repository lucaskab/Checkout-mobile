"""Builds the two QA contact sheets (decorations: 3/4 close + game view with tris/budget; icons: light, dark and 64 px).
SRC defaults to this social_art folder, OUT to its previews/ folder."""
import json, os, shutil
from PIL import Image, ImageDraw, ImageFont
SRC = os.environ.get("SOCIAL_ART_SRC", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.environ.get("SOCIAL_ART_OUT", os.path.join(SRC, "previews"))
os.makedirs(OUT, exist_ok=True)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf"
fb = lambda s: ImageFont.truetype(F % "-Bold", s)
fr = lambda s: ImageFont.truetype(F % "", s)
NAVY, GOLD, CREAM, INK = (29, 43, 79), (211, 165, 61), (246, 235, 214), (40, 40, 48)
rep = json.load(open(os.path.join(SRC, "report.json")))

# ---------------------------------------------------------------- decorations: 3/4 close + game view per id
ids = [("invite-reward-1", "1 amigo convidado", "bench planter"),
       ("invite-reward-3", "3 amigos convidados", "kiosk street lamp"),
       ("invite-reward-5", "5 amigos convidados", "friends statue")]
CW, PAD, HEAD = 640, 24, 120
W = PAD + len(ids) * (CW + PAD)
H = HEAD + 70 + CW + PAD + CW + 70 + PAD
sheet = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(sheet)
d.rectangle([0, 0, W, HEAD - 20], fill=NAVY)
d.text((PAD, 22), "Social v1 - invite reward decorations (preview for approval)", font=fb(34), fill=CREAM)
d.text((PAD, 66), "decor_v4 pipeline - 1024 px atlas each - navy #1D2B4F, gold #D3A53D trims - no text in models/textures", font=fr(20), fill=(220, 210, 190))
for i, (id_, unlock, what) in enumerate(ids):
    e = rep[id_]
    x = PAD + i * (CW + PAD)
    y = HEAD
    d.text((x, y), id_, font=fb(26), fill=NAVY)
    d.text((x, y + 34), "%s - %s" % (what, unlock), font=fr(19), fill=INK)
    y += 70
    for k, view in enumerate(("close", "game")):
        im = Image.open(os.path.join(SRC, "previews", "%s_%s.png" % (id_, view))).convert("RGB").resize((CW, CW), Image.LANCZOS)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + CW - 1, y + CW - 1], outline=(200, 190, 170), width=2)
        d.rounded_rectangle([x + 10, y + 10, x + 150, y + 42], 8, fill=NAVY)
        d.text((x + 20, y + 14), "3/4 close" if view == "close" else "game view", font=fb(18), fill=CREAM)
        y += CW + PAD
    sx, sy, sz = e["size_xyz"]
    ok = "OK" if e["within_budget"] else "OVER"
    d.text((x, y - PAD + 8), "%d / %d tris (%s)" % (e["tris"], e["budget"], ok), font=fb(20), fill=NAVY if e["within_budget"] else (190, 40, 40))
    anim = (" - sways: " + ", ".join(e["anim"])) if e["anim"] else ""
    d.text((x, y - PAD + 36), "%.2f x %.2f x %.2f m%s" % (sx, sy, sz, anim), font=fr(18), fill=INK)
sheet.save(os.path.join(OUT, "decorations_sheet.png"), optimize=True)

# ---------------------------------------------------------------- icons: 8 icons on light and dark backgrounds
icons = [("friends", "amigos"), ("gift", "presente"), ("help", "dar uma mão"), ("like", "curtir"),
         ("request", "pedido de ajuda"), ("share", "compartilhar"), ("invite", "convidar"), ("visit", "visitar")]
C, P2, HEAD2 = 300, 24, 110
cols = 4
rows = 2
W2 = P2 + cols * (C + P2)
H2 = HEAD2 + 2 * rows * (C + 56) + 40 + P2 + 120
sh = Image.new("RGB", (W2, H2), CREAM)
d = ImageDraw.Draw(sh)
d.rectangle([0, 0, W2, HEAD2 - 20], fill=NAVY)
d.text((P2, 20), "Social v1 - friends page UI icons", font=fb(32), fill=CREAM)
d.text((P2, 60), "512 px transparent sources (build_ui_sprites pipeline) - shown on light and dark", font=fr(19), fill=(220, 210, 190))

def checker(w, h, a, b, s=16):
    im = Image.new("RGB", (w, h), a)
    dd = ImageDraw.Draw(im)
    for yy in range(0, h, s):
        for xx in range(0, w, s):
            if (xx // s + yy // s) % 2:
                dd.rectangle([xx, yy, xx + s - 1, yy + s - 1], fill=b)
    return im

y0 = HEAD2
for band, (bg_a, bg_b, txt) in enumerate((((250, 247, 240), (236, 230, 218), NAVY), ((34, 46, 78), (28, 38, 66), CREAM))):
    for n, (name, pt) in enumerate(icons):
        r, c = divmod(n, cols)
        x = P2 + c * (C + P2)
        y = y0 + r * (C + 56)
        bg = checker(C, C, bg_a, bg_b)
        ic = Image.open(os.path.join(SRC, "icons", name + ".png")).convert("RGBA")
        assert ic.size == (512, 512), (name, ic.size)
        ic = ic.resize((C, C), Image.LANCZOS)
        bg.paste(ic, (0, 0), ic)
        sh.paste(bg, (x, y))
        d.text((x, y + C + 6), "%s  (%s)" % (name, pt), font=fb(18), fill=NAVY)
    y0 += rows * (C + 56)
    if band == 0:
        y0 += 20
# small-size readability row (64 px, as on a HUD button)
y = y0 + 10
d.text((P2, y), "at 64 px:", font=fb(18), fill=NAVY)
for n, (name, _) in enumerate(icons):
    ic = Image.open(os.path.join(SRC, "icons", name + ".png")).convert("RGBA").resize((64, 64), Image.LANCZOS)
    tile = Image.new("RGB", (80, 80), (34, 46, 78))
    tile.paste(ic, (8, 8), ic)
    sh.paste(tile, (P2 + 110 + n * 96, y - 4))
sh = sh.crop((0, 0, W2, y + 96))
sh.save(os.path.join(OUT, "icons_sheet.png"), optimize=True)

if OUT != os.path.join(SRC, "previews"):
    for sub in ("previews", "icons", "thumbs"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
        for f in sorted(os.listdir(os.path.join(SRC, sub))):
            shutil.copy2(os.path.join(SRC, sub, f), os.path.join(OUT, sub, f))
    shutil.copy2(os.path.join(SRC, "report.json"), os.path.join(OUT, "report.json"))
print(sorted(os.listdir(OUT)), sheet.size, sh.size)
