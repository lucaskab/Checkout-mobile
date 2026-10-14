"""compose_mock.py -- screen mock of the RECEIVING mini-game from the render_v2 layers, laid out the way
CheckoutReceivingGame.cs will lay them out (backdrop cover, truck on the dock, 4 fixtures side by side, boxes on the
slot quads, clipboard with 3 example lines). Usage: python compose_mock.py <render_v2 dir> <out dir>"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SW, SH = 1920, 960
BOX_SCALE = 1.35

def load(name): return Image.open(os.path.join(SRC, name)).convert("RGBA")
def js(name): return json.load(open(os.path.join(SRC, name)))
def font(sz, bold=True):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        if os.path.exists(f): return ImageFont.truetype(f, sz)
    return ImageFont.load_default()

stage = Image.new("RGBA", (SW, SH))
# 1. backdrop: cover
bd = load("receiving_backdrop.jpg"); s = max(SW / bd.width, SH / bd.height); bd = bd.resize((round(bd.width * s), round(bd.height * s)), Image.LANCZOS)
stage.alpha_composite(bd, ((SW - bd.width) // 2, (SH - bd.height) // 2))
bdj = js("receiving_backdrop.json")

boxes = {k: load(f"box_{k}.png") for k in ("carton", "crate", "pack", "frozen", "tray")}
def draw_box(kind, foot, width):
    """foot = stage px (x, y from top); square sprite of width*BOX_SCALE with pivot (.5, .14)."""
    sz = max(8, round(width * BOX_SCALE)); im = boxes[kind].resize((sz, sz), Image.LANCZOS)
    stage.alpha_composite(im, (round(foot[0] - sz / 2), round(foot[1] - sz * .86)))

# helpers: normalised (bottom-left origin) -> stage px for an image placed at rect (x, y, w, h) (top-left origin)
def P(a, rect): x, y, w, h = rect; return (x + a[0] * w, y + (1 - a[1]) * h)
def lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
def dist(a, b): return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5

# 2. truck: its dockRect lands on the backdrop's dock rect
tj = js("receiving_truck.json"); tb, tf = load("receiving_truck_back.png"), load("receiving_truck_front.png")
dock = bdj["dock"]; dk = [(SW - bd.width) / 2 + dock[0] * bd.width, (SH - bd.height) / 2 + (1 - dock[3]) * bd.height, (dock[2] - dock[0]) * bd.width, (dock[3] - dock[1]) * bd.height]
dr = tj["dockRect"]; sc = dk[2] / ((dr[2] - dr[0]) * tb.width)
tw, th = round(tb.width * sc), round(tb.height * sc)
tx = dk[0] - dr[0] * tw; ty = dk[1] - (1 - dr[3]) * th
trect = (tx, ty, tw, th)
stage.alpha_composite(tb.resize((tw, th), Image.LANCZOS), (round(tx), round(ty)))
q = tj["cargo"]; fl, fr, bl, br = (P(q[k], trect) for k in ("fl", "fr", "bl", "br"))
cols, rows = 2, 3; order = []
for r in range(rows - 1, -1, -1):
    for c in range(cols): order.append((r, c))
kinds = ["carton", "pack", "crate", "frozen", "tray", "carton"]
for i, (r, c) in enumerate(order[:5]):
    u = (c + .5) / cols; t = (r + .5) / (rows + .2)
    foot = lerp(lerp(fl, fr, u), lerp(bl, br, u), t); w = (dist(fl, fr) * (1 - t) + dist(bl, br) * t) / (cols + .3)
    draw_box(kinds[i], foot, w)
stage.alpha_composite(tf.resize((tw, th), Image.LANCZOS), (round(tx), round(ty)))
truck_frac = tw / SW

# 3. fixtures: 4 across, bodies sized to the slot, bottoms on a common floor line
left, right = SW * .228, SW * .995; floor_y = SH * .915
FIX = [("rack", ["SECOS"], ["carton", "carton", None, "carton", None, "tray", None, "carton"]),
       ("drinks", ["BEBIDAS"], ["pack", None, "pack", "pack", None, "pack", None, None]),
       ("produce", ["HORTIFRÚTI", "PÃES"], ["crate", None, "crate", None, "tray", None, "tray", "tray"]),
       ("coldroom", ["CÂMARA FRIA"], ["frozen", None, "frozen", None, "frozen", "frozen", None, None])]
ZONE_COL = {"SECOS": "#D9A032", "BEBIDAS": "#F28C28", "HORTIFRÚTI": "#5DA637", "PÃES": "#5DA637", "CÂMARA FRIA": "#4FA3D9"}
report = {"truckWidthFrac": round(truck_frac, 3)}
# one pixels-per-metre for every fixture: the bodies (in metres) share the width between the truck and the right edge
datas = {key: js(f"receiving_{key}.json") for key, _, _ in FIX}
gap = SW * .006; ppm = (right - left - gap * (len(FIX) - 1)) / sum(d["bodyWidthM"] for d in datas.values()); report["ppm"] = round(ppm, 1)
cursor = left
for i, (key, names, fill) in enumerate(FIX):
    d = datas[key]; back, front = load(f"receiving_{key}_back.png"), load(f"receiving_{key}_front.png")
    body = d["body"]; bw = (body[2] - body[0]) * back.width
    sc = ppm * d["bodyWidthM"] / bw; w, h = round(back.width * sc), round(back.height * sc)
    x = cursor - body[0] * w; cursor += ppm * d["bodyWidthM"] + gap; y = floor_y - (1 - body[1]) * h
    rect = (x, y, w, h); report[key] = dict(imgW=w, imgH=h, heightFrac=round(h / SH, 3))
    stage.alpha_composite(back.resize((w, h), Image.LANCZOS), (round(x), round(y)))
    slots = sorted(d["slots"], key=lambda q: (-q["level"], q["bay"], q["index"]))
    for q, kind in zip(slots, fill):
        if not kind: continue
        fl, fr, bl, br = (P(q[k], rect) for k in ("fl", "fr", "bl", "br"))
        foot = lerp(lerp(fl, fr, .5), lerp(bl, br, .5), .42); width = dist(fl, fr) * .58 + dist(bl, br) * .42
        draw_box(kind, foot, width)
    stage.alpha_composite(front.resize((w, h), Image.LANCZOS), (round(x), round(y)))
    if "sign" in d:
        sg = d["sign"]; x0, y0 = P((sg[0], sg[3]), rect); x1, y1 = P((sg[2], sg[1]), rect)
        dr_ = ImageDraw.Draw(stage); txt = "  ·  ".join(names); fs = int((y1 - y0) * .55)
        f = font(fs); tw_ = dr_.textlength(txt, font=f)
        while tw_ > (x1 - x0) * .9 and fs > 8: fs -= 1; f = font(fs); tw_ = dr_.textlength(txt, font=f)
        xx = (x0 + x1) / 2 - tw_ / 2
        for n_, name in enumerate(names):
            if n_: dr_.text((xx, (y0 + y1) / 2), "  ·  ", font=f, fill="#0F5F59", anchor="lm"); xx += dr_.textlength("  ·  ", font=f)
            dr_.text((xx, (y0 + y1) / 2), name, font=f, fill=ZONE_COL[name], anchor="lm"); xx += dr_.textlength(name, font=f)

# 4. clipboard, bottom-left, h = .42 H, rotated 4 deg, with 3 example lines written like Unity does
cj = js("receiving_clipboard.json"); cb = load("receiving_clipboard.png")
ch = round(SH * .34); cw = round(ch * cb.width / cb.height); cb = cb.resize((cw, ch), Image.LANCZOS)
dr_ = ImageDraw.Draw(cb); sheet = cj["sheet"]
f = font(int(ch * .05)); dr_.text((cw * (sheet[0] + sheet[2]) / 2, ch * (1 - sheet[3] + .042)), "NOTA DE ENTREGA", font=f, fill="white", anchor="mm")
lines = cj["lines"]; fl_ = font(int(ch * .04), bold=False)
for k, (name, n) in enumerate((("Leite integral", 5), ("Pão francês", 5), ("Banana", 5))):
    L = lines[k]; yy = ch * (1 - L["y"] - .0325); x0 = cw * L["x0"]
    dr_.text((x0, yy), name, font=fl_, fill="#4A3624", anchor="lm")
    dr_.text((x0 + cw * (L["x1"] - L["x0"]) * .80, yy), f"{0 if k else 2}/{n}", font=font(int(ch * .04)), fill="#4A3624", anchor="mm")
cb = cb.rotate(4, resample=Image.BICUBIC, expand=True)
stage.alpha_composite(cb, (round(SW * .012), round(SH - cb.height - SH * .02)))

stage.convert("RGB").save(os.path.join(OUT, "screen_mock.png"))
# 5. contact sheet of the layers
items = ["receiving_backdrop.jpg", "receiving_truck_back.png", "receiving_truck_front.png"]
for k in ("rack", "drinks", "produce", "coldroom"): items += [f"receiving_{k}_back.png", f"receiving_{k}_front.png"]
items += ["receiving_clipboard.png", "stamp_conferido.png"] + [f"box_{k}.png" for k in ("carton", "crate", "pack", "frozen", "tray")]
cell = 360; cols = 6; rows = (len(items) + cols - 1) // cols
sheet_img = Image.new("RGB", (cols * cell, rows * (cell + 28)), (70, 72, 74)); d2 = ImageDraw.Draw(sheet_img); fs = font(16, bold=False)
for i, nm in enumerate(items):
    im = load(nm); s_ = min((cell - 16) / im.width, (cell - 16) / im.height); im = im.resize((round(im.width * s_), round(im.height * s_)), Image.LANCZOS)
    cx, cy = (i % cols) * cell, (i // cols) * (cell + 28)
    tile = Image.new("RGBA", (cell, cell), (120, 122, 124, 255)); tile.alpha_composite(im, ((cell - im.width) // 2, (cell - im.height) // 2))
    sheet_img.paste(tile.convert("RGB"), (cx, cy)); d2.text((cx + 8, cy + cell + 6), f"{nm}  {load(nm).width}x{load(nm).height}", font=fs, fill="white")
sheet_img.save(os.path.join(OUT, "contact_sheet.png"))
json.dump(report, open(os.path.join(OUT, "mock_layout.json"), "w"), indent=1); print(json.dumps(report))
