"""Builds the QA contact sheet of the invite reward decorations: 3/4 close view + game view per item, with tris / budget,
size and a status tag. Only writes the sheet (never touches the previews).

    SOCIAL_ART_SRC  social_art folder with previews/ and report.json (default: this tool's parent folder)
    SOCIAL_ART_OUT  output folder (default: SRC/previews)
    SHEET_NAME      file name (default: decorations_sheet.png)
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

SRC = os.environ.get("SOCIAL_ART_SRC", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.environ.get("SOCIAL_ART_OUT", os.path.join(SRC, "previews"))
NAME = os.environ.get("SHEET_NAME", "decorations_sheet.png")
os.makedirs(OUT, exist_ok=True)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf"
fb = lambda s: ImageFont.truetype(F % "-Bold", s)
fr = lambda s: ImageFont.truetype(F % "", s)
NAVY, CREAM, INK, OKC, NEWC = (29, 43, 79), (246, 235, 214), (40, 40, 48), (46, 125, 70), (196, 120, 20)

# id, unlock (pt-BR, as the player sees it), what it is, status tag
ITEMS = [("invite-reward-1", "1 amigo convidado", "bench planter", "approved"),
         ("invite-reward-3", "3 amigos convidados", "kiosk street lamp", "approved"),
         ("invite-reward-5", "5 amigos convidados", "friends statue", "v2 - full colour figures")]


def build():
    rep = json.load(open(os.path.join(SRC, "report.json")))
    CW, PAD, HEAD = 640, 24, 120
    W = PAD + len(ITEMS) * (CW + PAD)
    H = HEAD + 70 + CW + PAD + CW + 70 + PAD
    sheet = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, W, HEAD - 20], fill=NAVY)
    d.text((PAD, 22), "Social v1 - invite reward decorations (preview for approval)", font=fb(34), fill=CREAM)
    d.text((PAD, 66), "decor_v4 pipeline - 1024 px atlas each - navy #1D2B4F, gold #D3A53D trims - no text in models/textures",
           font=fr(20), fill=(220, 210, 190))
    for i, (id_, unlock, what, status) in enumerate(ITEMS):
        e = rep[id_]
        x = PAD + i * (CW + PAD)
        y = HEAD
        d.text((x, y), id_, font=fb(26), fill=NAVY)
        tw = d.textlength(id_, font=fb(26))
        col = OKC if status == "approved" else NEWC
        sw = d.textlength(status, font=fb(16))
        d.rounded_rectangle([x + tw + 14, y + 4, x + tw + 34 + sw, y + 30], 8, fill=col)
        d.text((x + tw + 24, y + 7), status, font=fb(16), fill=(255, 255, 255))
        d.text((x, y + 34), "%s - %s" % (what, unlock), font=fr(19), fill=INK)
        y += 70
        for view in ("close", "game"):
            im = Image.open(os.path.join(SRC, "previews", "%s_%s.png" % (id_, view))).convert("RGB").resize((CW, CW), Image.LANCZOS)
            sheet.paste(im, (x, y))
            d.rectangle([x, y, x + CW - 1, y + CW - 1], outline=(200, 190, 170), width=2)
            d.rounded_rectangle([x + 10, y + 10, x + 150, y + 42], 8, fill=NAVY)
            d.text((x + 20, y + 14), "3/4 close" if view == "close" else "game view", font=fb(18), fill=CREAM)
            y += CW + PAD
        sx, sy, sz = e["size_xyz"]
        ok = "OK" if e["within_budget"] else "OVER"
        d.text((x, y - PAD + 8), "%d / %d tris (%s)" % (e["tris"], e["budget"], ok), font=fb(20),
               fill=NAVY if e["within_budget"] else (190, 40, 40))
        anim = (" - sways: " + ", ".join(e["anim"])) if e["anim"] else ""
        d.text((x, y - PAD + 36), "%.2f x %.2f x %.2f m%s" % (sx, sy, sz, anim), font=fr(18), fill=INK)
    path = os.path.join(OUT, NAME)
    sheet.save(path, optimize=True)
    return path


if __name__ == "__main__":
    print(build())
