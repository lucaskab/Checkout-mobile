"""compose_mock_v3.py -- screen mock of the RECEIVING mini-game from the render_v3 layers, laid out the way
CheckoutReceivingGame.cs lays them out with v3 art: every crop at its "stage" rect over the backdrop, boxes on the slot
quads (foot at 42 % of the depth, sprite = width x 1.35, pivot .5/.14), the clipboard over the dock.
Usage: python compose_mock_v3.py <render_v3 dir> <render_v2 dir (clipboard)> <out dir>"""
import json, os, sys, random
from PIL import Image, ImageDraw, ImageFont

SRC, SRC2, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; os.makedirs(OUT, exist_ok=True)
BOX_SCALE = 1.35
def load(d, n): return Image.open(os.path.join(d, n)).convert("RGBA")
def js(d, n): return json.load(open(os.path.join(d, n)))
def font(sz, bold=True):
    f = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(f, sz)

bd = load(SRC, "receiving_backdrop.jpg"); SW, SH = bd.size
stage = bd.copy()
boxes = {k: load(SRC, f"box_{k}.png") for k in ("carton", "crate", "bread", "pack", "water", "milk", "frozen", "tray")}
def lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
def dist(a, b): return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5
def rect_of(st): return (st[0] * SW, (1 - st[3]) * SH, (st[2] - st[0]) * SW, (st[3] - st[1]) * SH)
def P(a, r): return (r[0] + a[0] * r[2], r[1] + (1 - a[1]) * r[3])
def draw_box(kind, foot, width):
    sz = max(8, round(width * BOX_SCALE)); im = boxes[kind].resize((sz, sz), Image.LANCZOS)
    stage.alpha_composite(im, (round(foot[0] - sz / 2), round(foot[1] - sz * .86)))

# truck: back layer, then the cargo (back rows first)
tj = js(SRC, "receiving_truck.json"); tr = rect_of(tj["stage"])
stage.alpha_composite(load(SRC, "receiving_truck_back.png").resize((round(tr[2]), round(tr[3])), Image.LANCZOS), (round(tr[0]), round(tr[1])))
q = tj["cargo"]; fl, fr, bl, br = (P(q[k], tr) for k in ("fl", "fr", "bl", "br"))
cols, rows = tj["cargoColumns"], tj["cargoRows"]
load_kinds = ["water", "crate", "milk", "carton", "bread", "pack", "frozen"]
cells = []
for i in range(len(load_kinds)):
    layer, cell = divmod(i, cols * rows); row = rows - 1 - cell // cols; col = cell % cols
    u = (col + .5) / cols; t = (row + .5) / (rows + .2)
    foot = lerp(lerp(fl, fr, u), lerp(bl, br, u), t); w = (dist(fl, fr) * (1 - t) + dist(bl, br) * t) / (cols + .3)
    cells.append((layer, -foot[1], load_kinds[i], (foot[0], foot[1] - layer * w * .92), w))
for layer, _, kind, foot, w in sorted(cells, key=lambda c: (c[1], c[0])): draw_box(kind, foot, w)

FIX = {"rack": ["carton", "tray", "carton", None, "carton", "carton", None, "tray"],
       "drinks": ["water", "water", "pack", None, "pack", "water", None, None],
       "produce": ["crate", "crate", "crate", None, None, None, "bread", "bread", None],
       "coldroom": ["milk", "frozen", "milk", None, "frozen", None, None, None]}
NAMES = {"rack": "SECOS", "drinks": "BEBIDAS", "produce": "HORTIFRÚTI · PÃES", "coldroom": "CÂMARA FRIA"}
COL = {"rack": "#D9A032", "drinks": "#F28C28", "produce": "#5DA637", "coldroom": "#4FA3D9"}
for key, fill in FIX.items():
    d = js(SRC, f"receiving_{key}.json"); r = rect_of(d["stage"]); size = (round(r[2]), round(r[3]))
    stage.alpha_composite(load(SRC, f"receiving_{key}_back.png").resize(size, Image.LANCZOS), (round(r[0]), round(r[1])))
    # Unity's order: by level desc, bay, index -- the fill list follows that order
    slots = sorted(d["slots"], key=lambda s: (-s["level"], s["bay"], s["index"]))
    placed = []
    for s, kind in zip(slots, fill):
        if not kind: continue
        a, b_, c, e = (P(s[k], r) for k in ("fl", "fr", "bl", "br"))
        foot = lerp(lerp(a, b_, .5), lerp(c, e, .5), .42); width = dist(a, b_) * .58 + dist(c, e) * .42
        placed.append((foot, width, kind))
    for foot, width, kind in sorted(placed, key=lambda p: (-p[0][1], p[0][0])): draw_box(kind, foot, width)
    stage.alpha_composite(load(SRC, f"receiving_{key}_front.png").resize(size, Image.LANCZOS), (round(r[0]), round(r[1])))
    sg = d["sign"]; x0, y0 = P((sg[0], sg[3]), r); x1, y1 = P((sg[2], sg[1]), r)
    dr = ImageDraw.Draw(stage); txt = NAMES[key]; fs = int((y1 - y0) * .62)
    while fs > 8 and dr.textlength(txt, font=font(fs)) > (x1 - x0) * .9: fs -= 1
    dr.text(((x0 + x1) / 2, (y0 + y1) / 2), txt, font=font(fs), fill=COL[key], anchor="mm")

# clipboard over the dock (top centre), 3 example lines
cj = js(SRC2, "receiving_clipboard.json"); cb = load(SRC2, "receiving_clipboard.png")
dk = js(SRC, "receiving_backdrop.json")["dock"]; ch = round(SH * .30); cw = round(ch * cb.width / cb.height)
cb = cb.resize((cw, ch), Image.LANCZOS); cx = round((dk[0] + dk[2]) / 2 * SW - cw / 2); cy = round(SH * .012)
stage.alpha_composite(cb, (cx, cy)); dr = ImageDraw.Draw(stage)
sheet = cj["sheet"]
dr.text((cx + cw * (sheet[0] + sheet[2]) / 2, cy + ch * (1 - sheet[3]) + ch * .028), "NOTA DE ENTREGA", font=font(int(ch * .036)), fill="white", anchor="mm")
for line, (name, qty) in zip(cj["lines"], (("Leite integral", "2/5"), ("Pão francês", "0/5"), ("Banana prata", "5/5"))):
    lx0, lx1 = cx + line["x0"] * cw, cx + line["x1"] * cw; ly = cy + (1 - line["y"]) * ch; span = lx1 - lx0
    dr.text((lx0 + span * .01, ly), name, font=font(int(ch * .034), False), fill="#2A3140", anchor="lm")
    dr.text((lx0 + span * .86, ly), qty, font=font(int(ch * .034)), fill="#1D2B4F", anchor="rm")
    if qty == "5/5": dr.text((lx0 + span * .93, ly), "✓", font=font(int(ch * .04)), fill="#2E9E44", anchor="mm")
stage.convert("RGB").save(os.path.join(OUT, "screen_mock_v3.jpg"), quality=90)

# contact sheet of the boxes
names = list(boxes); tile = 360; sheet_im = Image.new("RGBA", (4 * tile, 2 * tile), (205, 208, 210, 255))
d2 = ImageDraw.Draw(sheet_im)
for i, n in enumerate(names):
    sheet_im.alpha_composite(boxes[n].resize((tile, tile), Image.LANCZOS), ((i % 4) * tile, (i // 4) * tile))
    d2.text(((i % 4) * tile + 10, (i // 4) * tile + 8), n, font=font(20), fill="#333")
sheet_im.convert("RGB").save(os.path.join(OUT, "boxes_v3.jpg"), quality=90)
print("ok")
