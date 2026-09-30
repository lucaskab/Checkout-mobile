"""Product label atlas for the realistic kit: IK_Labels_albedo.png (2048², 8x8 cells of 256 px).
Cells are addressed by name in LABELS (col, row); row 0 is the TOP row of the image."""
import math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/mnt/user-data/uploads/Checkout-mobile/unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Fonts/Fredoka_700Bold.ttf"
S = 256
img = Image.new("RGB", (S * 8, S * 8), (240, 236, 228))
LABELS = {}


def font(sz):
    return ImageFont.truetype(FONT, sz)


def cell(name, col, row):
    LABELS[name] = (col, row)
    c = Image.new("RGB", (S, S))
    return c, ImageDraw.Draw(c)


def put(c, col, row):
    img.paste(c, (col * S, row * S))


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def ctext(d, xy, txt, sz, fill, stroke=None, sw=0):
    f = font(sz)
    d.text(xy, txt, font=f, fill=fill, anchor="mm", stroke_width=sw, stroke_fill=stroke)


def fruit(d, cx, cy, r, kind):
    cols = {"orange": "F28C28", "lemon": "F2D43F", "grape": "7B3F9E", "apple": "D93B30", "straw": "E0304A",
            "mango": "F6A623", "cola": "5A2A1A", "guarana": "D9362B", "peach": "F7A072", "leaf": "4E9A3A"}
    if kind == "grape":
        for i, (dx, dy) in enumerate(((0, 0), (-.5, -.5), (.5, -.5), (0, -1), (-1, -1), (1, -1), (-.5, -1.5), (.5, -1.5))):
            d.ellipse((cx + dx * r * .6 - r * .35, cy - dy * r * .55 - r * .35 - r * .5, cx + dx * r * .6 + r * .35, cy - dy * r * .55 + r * .35 - r * .5), fill=hexc(cols["grape"]), outline=(60, 20, 70), width=2)
    else:
        col = hexc(cols.get(kind, "F28C28"))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col, outline=shade(col, .6), width=3)
        d.ellipse((cx - r * .55, cy - r * .6, cx - r * .15, cy - r * .2), fill=shade(col, 1.35))
    d.ellipse((cx + r * .05, cy - r * 1.25, cx + r * .75, cy - r * .85), fill=hexc(cols["leaf"]))


# ---------------------------------------------------------------- row 0: soda bottle wraps (wrap around x)
sodas = [("COLA", "C8102E", "FFFFFF", "cola"), ("GUARANÁ", "1E8C3A", "FFE14D", "guarana"), ("LARANJA", "F28C28", "FFFFFF", "orange"),
         ("LIMÃO", "7DBE3C", "FFFFFF", "lemon"), ("UVA", "6B2C91", "FFFFFF", "grape"), ("TÔNICA", "E9E4D4", "1F5FA8", "lemon"),
         ("ZERO", "1B1B1B", "E3263A", "cola"), ("CHÁ", "C98B2E", "FFFFFF", "peach")]
for i, (t, bg, fg, fr) in enumerate(sodas):
    c, d = cell("soda_%d" % i, i, 0)
    bgc = hexc(bg)
    d.rectangle((0, 0, S, S), fill=bgc)
    for k in range(2):
        y0 = 40 + k * 150
        d.polygon([(x, y0 + 14 * math.sin(x / 40 + k)) for x in range(0, S + 8, 8)] + [(S, y0 + 30), (0, y0 + 30)], fill=hexc(fg) if k == 0 else shade(bgc, .75))
    ctext(d, (S / 2, S / 2 + 6), t, 62 if len(t) < 7 else 46, hexc(fg), shade(bgc, .5), 3)
    fruit(d, 40, 200, 20, fr)
    fruit(d, 216, 200, 20, fr)
    put(c, i, 0)

# ---------------------------------------------------------------- row 1: water wraps (0-1), juice cartons (2-5), milk (6), yogurt (7)
for i, (t, bg) in enumerate((("ÁGUA", "2F8FD8"), ("COM GÁS", "1B6FB0"))):
    c, d = cell("water_%d" % i, i, 1)
    d.rectangle((0, 0, S, S), fill=(235, 247, 255))
    d.polygon([(0, 190), (60, 110), (100, 150), (150, 80), (210, 150), (256, 120), (256, 256), (0, 256)], fill=hexc(bg))
    d.polygon([(135, 98), (150, 80), (165, 98)], fill=(255, 255, 255))
    ctext(d, (S / 2, 60), t, 54 if i == 0 else 40, hexc(bg))
    ctext(d, (S / 2, 220), "MINERAL", 26, (255, 255, 255))
    put(c, i, 1)
juices = [("SUCO", "F28C28", "orange"), ("SUCO", "E0304A", "straw"), ("SUCO", "F6A623", "mango"), ("SUCO", "7B3F9E", "grape")]
for i, (t, bg, fr) in enumerate(juices):
    c, d = cell("juice_%d" % i, 2 + i, 1)
    bgc = hexc(bg)
    d.rectangle((0, 0, S, S), fill=(255, 250, 238))
    d.rectangle((0, 150, S, S), fill=bgc)
    d.ellipse((-40, 120, 296, 190), fill=bgc)
    fruit(d, S / 2, 95, 52, fr)
    ctext(d, (S / 2, 212), t, 48, (255, 255, 255), shade(bgc, .6), 2)
    put(c, 2 + i, 1)
c, d = cell("milk", 6, 1)
d.rectangle((0, 0, S, S), fill=(250, 252, 255))
d.rectangle((0, 170, S, S), fill=hexc("2F7DD8"))
for x in range(0, S, 64):
    d.ellipse((x - 10, 150, x + 54, 196), fill=(250, 252, 255))
d.ellipse((70, 40, 186, 130), fill=(255, 255, 255), outline=(40, 40, 40), width=4)
d.ellipse((95, 70, 125, 100), fill=(40, 40, 40))
ctext(d, (S / 2, 218), "LEITE", 50, (255, 255, 255))
put(c, 6, 1)
c, d = cell("yogurt", 7, 1)
d.rectangle((0, 0, S, S), fill=hexc("F7C6D9"))
fruit(d, S / 2, 110, 55, "straw")
ctext(d, (S / 2, 215), "IOGURTE", 40, hexc("B0224A"))
put(c, 7, 1)

# ---------------------------------------------------------------- row 2: can wraps
cans = [("COLA", "C8102E", "FFFFFF"), ("GUARANÁ", "1E8C3A", "FFE14D"), ("LARANJA", "F28C28", "FFFFFF"), ("ENERGY", "1B1B1B", "8CE63A"),
        ("PILSEN", "E8C24A", "8C1A10"), ("LAGER", "1F4F9A", "FFFFFF"), ("ICE TEA", "C98B2E", "FFFFFF"), ("TÔNICA", "E9E4D4", "1F5FA8")]
for i, (t, bg, fg) in enumerate(cans):
    c, d = cell("can_%d" % i, i, 2)
    bgc = hexc(bg)
    d.rectangle((0, 0, S, S), fill=bgc)
    d.rectangle((0, 0, S, 26), fill=(200, 205, 210))
    d.rectangle((0, S - 26, S, S), fill=(200, 205, 210))
    for x in range(-S, S, 18):
        d.line((x, 26, x + S, S - 26), fill=shade(bgc, 1.12), width=6)
    d.ellipse((30, 70, 226, 186), fill=hexc(fg))
    ctext(d, (S / 2, 128), t, 44 if len(t) < 7 else 34, bgc)
    put(c, i, 2)

# ---------------------------------------------------------------- row 3: beer labels (0-3), wine labels (4-7)
beers = [("PILSEN", "E8C24A", "8C1A10"), ("PUROMALTE", "F5ECD0", "1F4F9A"), ("IPA", "2F6B3A", "F2E3A0"), ("STOUT", "2A1A12", "E0B040")]
for i, (t, bg, fg) in enumerate(beers):
    c, d = cell("beer_%d" % i, i, 3)
    d.rectangle((0, 0, S, S), fill=shade(hexc(bg), .8))
    d.ellipse((20, 40, 236, 216), fill=hexc(bg), outline=hexc(fg), width=8)
    d.ellipse((40, 60, 216, 196), outline=hexc(fg), width=2)
    ctext(d, (S / 2, 118), t, 40 if len(t) < 7 else 30, hexc(fg))
    ctext(d, (S / 2, 165), "CERVEJA", 20, hexc(fg))
    put(c, i, 3)
wines = [("TINTO", "F2EAD8", "6B1020"), ("RESERVA", "1E1E22", "D9B25A"), ("BRANCO", "F7F3E6", "B08A2A"), ("ROSÉ", "F9E4E4", "B0405A")]
for i, (t, bg, fg) in enumerate(wines):
    c, d = cell("wine_%d" % i, 4 + i, 3)
    bgc, fgc = hexc(bg), hexc(fg)
    d.rectangle((0, 0, S, S), fill=bgc)
    d.rectangle((14, 14, S - 14, S - 14), outline=fgc, width=4)
    d.rectangle((24, 24, S - 24, S - 24), outline=fgc, width=1)
    for k, (dx, dy) in enumerate(((0, 0), (-12, -14), (12, -14), (0, -28), (-24, -28), (24, -28), (-12, -42), (12, -42))):
        d.ellipse((S / 2 + dx - 11, 118 + dy - 11 - 20, S / 2 + dx + 11, 118 + dy + 11 - 20), fill=fgc)
    d.line((S / 2, 50, S / 2 + 10, 36), fill=hexc("4E7A2A"), width=4)
    ctext(d, (S / 2, 150), t, 40, fgc)
    ctext(d, (S / 2, 196), "2019", 26, fgc)
    put(c, 4 + i, 3)

# ---------------------------------------------------------------- row 4: gelato flavours (surface textures)
gel = [("F4A6C1", "D9336B"), ("A8D48A", "5E8F3A"), ("F6EBC8", "E8D9A8"), ("6B3E26", "3E2214"), ("F7B733", "E08A1A"),
       ("B9E8D2", "2A1A12"), ("F7F2E6", "3E2214"), ("9C7BD1", "5A3A9A")]
random.seed(4)
for i, (base, acc) in enumerate(gel):
    c, d = cell("gelato_%d" % i, i, 4)
    bc, ac = hexc(base), hexc(acc)
    d.rectangle((0, 0, S, S), fill=bc)
    for k in range(9):
        y = k * 30 + 10
        d.line([(x, y + 10 * math.sin(x / 22 + k)) for x in range(0, S + 4, 4)], fill=shade(bc, 1.1), width=8)
        d.line([(x, y + 6 + 10 * math.sin(x / 22 + k)) for x in range(0, S + 4, 4)], fill=shade(bc, .88), width=3)
    for k in range(60 if i in (5, 6) else 20):
        x, y = random.randint(0, S), random.randint(0, S)
        r = random.randint(3, 7)
        d.ellipse((x - r, y - r, x + r, y + r * .7), fill=ac)
    c = c.filter(ImageFilter.GaussianBlur(1.2))
    put(c, i, 4)

# ---------------------------------------------------------------- rows 5-6: grocery packs (box fronts)
packs = [("CEREAL", "F2C23F", "C8102E", "bowl"), ("MACARRÃO", "1F5FA8", "F2C23F", "pasta"), ("BISCOITO", "8C4A1E", "F2E3C6", "cookie"),
         ("ARROZ", "F7F3E6", "1E8C3A", "rice"), ("CAFÉ", "3E2214", "E0B040", "bean"), ("SABÃO", "2F8FD8", "FFFFFF", "bubble"),
         ("CHIPS", "E0304A", "F2C23F", "chip"), ("FEIJÃO", "7A2E1E", "F2E3C6", "bean"), ("AZEITE", "3F6B2A", "E8D27A", "olive"),
         ("MOLHO", "C8102E", "FFFFFF", "tomato"), ("AÇÚCAR", "F7F7F2", "2F7DD8", "cube"), ("FARINHA", "F2E6CC", "C87A2A", "wheat"),
         ("DETERG.", "7DBE3C", "FFFFFF", "bubble"), ("PAPEL", "F2F2F2", "2F8FD8", "roll"), ("CHOCOLATE", "5A2A1A", "F2C23F", "bar"),
         ("SNACK", "F28C28", "1B1B1B", "chip")]
for i, (t, bg, fg, ic) in enumerate(packs):
    col, row = i % 8, 5 + i // 8
    c, d = cell("pack_%d" % i, col, row)
    bgc, fgc = hexc(bg), hexc(fg)
    d.rectangle((0, 0, S, S), fill=bgc)
    d.rectangle((0, 0, S, 58), fill=fgc)
    ctext(d, (S / 2, 30), t, 36 if len(t) < 8 else 28, bgc)
    cx, cy = S / 2, 150
    if ic == "bowl":
        d.chord((50, 90, 206, 230), 0, 180, fill=(255, 255, 255))
        for k in range(8):
            d.ellipse((70 + k * 15, 140 + (k % 2) * 8, 92 + k * 15, 160 + (k % 2) * 8), fill=hexc("E8A53A"))
    elif ic == "pasta":
        d.rounded_rectangle((60, 90, 196, 220), 20, fill=(255, 255, 255))
        for k in range(6):
            d.line((75 + k * 20, 100, 85 + k * 20, 210), fill=hexc("F2C23F"), width=7)
    elif ic == "cookie":
        for k in range(3):
            d.ellipse((50 + k * 50, 100 + k * 15, 150 + k * 50, 200 + k * 15), fill=hexc("C98B4E"), outline=hexc("8C5A2A"), width=3)
            for q in range(5):
                d.ellipse((70 + k * 50 + q * 14, 130 + k * 15 + (q % 2) * 20, 80 + k * 50 + q * 14, 140 + k * 15 + (q % 2) * 20), fill=hexc("3E2214"))
    elif ic == "bean":
        for k in range(9):
            x, y = 70 + (k % 3) * 45, 100 + (k // 3) * 40
            d.ellipse((x, y, x + 36, y + 24), fill=shade(fgc, .8) if t == "CAFÉ" else hexc("5A1A12"))
    elif ic == "bubble":
        for k in range(7):
            r = 12 + (k * 7) % 26
            x, y = 50 + (k * 37) % 150, 90 + (k * 53) % 120
            d.ellipse((x, y, x + r * 2, y + r * 2), outline=(255, 255, 255), width=4)
    elif ic == "chip":
        for k in range(4):
            d.ellipse((50 + k * 40, 100 + (k % 2) * 30, 130 + k * 40, 170 + (k % 2) * 30), fill=hexc("F2C23F"), outline=hexc("D98E2B"), width=3)
    elif ic == "olive":
        for k in range(4):
            d.ellipse((60 + k * 35, 120 + (k % 2) * 20, 100 + k * 35, 170 + (k % 2) * 20), fill=hexc("6B8E23"))
    elif ic == "tomato":
        fruit(d, cx, cy, 55, "apple")
    elif ic == "cube":
        for k in range(3):
            d.rectangle((60 + k * 50, 120 - k * 10, 110 + k * 50, 170 - k * 10), fill=(255, 255, 255), outline=(200, 200, 200), width=3)
    elif ic == "wheat":
        for k in range(3):
            x = 90 + k * 40
            d.line((x, 220, x, 100), fill=hexc("C87A2A"), width=4)
            for q in range(5):
                d.ellipse((x - 14, 100 + q * 18, x, 116 + q * 18), fill=hexc("E0B040"))
                d.ellipse((x, 100 + q * 18, x + 14, 116 + q * 18), fill=hexc("E0B040"))
    elif ic == "roll":
        for k in range(2):
            d.rounded_rectangle((55 + k * 75, 90, 125 + k * 75, 220), 25, fill=(255, 255, 255), outline=(190, 200, 210), width=3)
    elif ic == "bar":
        d.rounded_rectangle((50, 100, 206, 210), 10, fill=hexc("7A3E1E"))
        for k in range(3):
            for q in range(2):
                d.rectangle((60 + k * 50, 110 + q * 50, 100 + k * 50, 150 + q * 50), outline=hexc("5A2A1A"), width=3)
    elif ic == "rice":
        d.ellipse((50, 90, 206, 220), fill=(255, 255, 255))
        for k in range(40):
            x, y = 70 + (k * 29) % 110, 110 + (k * 17) % 90
            d.ellipse((x, y, x + 12, y + 6), fill=hexc("F2EAD0"), outline=(200, 190, 160))
    d.rectangle((0, S - 24, S, S), fill=shade(bgc, .8))
    put(c, col, row)

# ---------------------------------------------------------------- row 7: materials — wood, leaf, cork-board menu, fabric, cone waffle, chalk menu
c, d = cell("wood", 0, 7)
d.rectangle((0, 0, S, S), fill=hexc("B97A45"))
for k in range(40):
    y = k * 6.4
    d.line([(x, y + 3 * math.sin(x / 30 + k * .7)) for x in range(0, S + 4, 4)], fill=shade(hexc("B97A45"), .82 + .2 * (k % 3) / 2), width=2)
put(c, 0, 7)
c, d = cell("leaf", 1, 7)
d.rectangle((0, 0, S, S), fill=hexc("3F8A2E"))
random.seed(7)
for k in range(140):
    x, y = random.randint(-10, S), random.randint(-10, S)
    a = random.random() * math.pi
    L = random.randint(14, 26)
    col = random.choice(("5DAE3E", "4E9A3A", "76C04F", "2F6F2C", "8BCB5A"))
    pts = [(x + math.cos(a) * L, y + math.sin(a) * L), (x + math.cos(a + 1.6) * L * .35, y + math.sin(a + 1.6) * L * .35), (x - math.cos(a) * L, y - math.sin(a) * L), (x + math.cos(a - 1.6) * L * .35, y + math.sin(a - 1.6) * L * .35)]
    d.polygon(pts, fill=hexc(col))
put(c, 1, 7)
c, d = cell("waffle", 2, 7)
d.rectangle((0, 0, S, S), fill=hexc("D9A05B"))
for k in range(-S, 2 * S, 28):
    d.line((k, 0, k + S, S), fill=hexc("B9793A"), width=6)
    d.line((k, S, k + S, 0), fill=hexc("B9793A"), width=6)
put(c, 2, 7)
c, d = cell("menu", 3, 7)
d.rectangle((0, 0, S, S), fill=hexc("2B2F2E"))
ctext(d, (S / 2, 34), "SORVETES", 34, hexc("FFD97A"))
for k, (a, b) in enumerate((("1 BOLA", "8,00"), ("2 BOLAS", "14,00"), ("CASCÃO", "5,00"), ("MILK-SHAKE", "15,00"), ("SUNDAE", "12,00"))):
    d.text((22, 70 + k * 36), a, font=font(24), fill=(250, 248, 240))
    d.text((234, 70 + k * 36), b, font=font(24), fill=hexc("F4A6C1"), anchor="ra")
put(c, 3, 7)
c, d = cell("coffee_menu", 4, 7)
d.rectangle((0, 0, S, S), fill=hexc("2B2F2E"))
ctext(d, (S / 2, 34), "CAFÉ", 38, hexc("FFD97A"))
for k, (a, b) in enumerate((("EXPRESSO", "5,00"), ("CAPUCCINO", "8,00"), ("LATTE", "9,00"), ("PÃO DE QUEIJO", "4,00"), ("BOLO", "7,00"))):
    d.text((18, 70 + k * 36), a, font=font(22), fill=(250, 248, 240))
    d.text((238, 70 + k * 36), b, font=font(22), fill=hexc("F2B06B"), anchor="ra")
put(c, 4, 7)
c, d = cell("fabric", 5, 7)
for k in range(0, S, 32):
    d.rectangle((k, 0, k + 16, S), fill=hexc("E9E1CF"))
    d.rectangle((k + 16, 0, k + 32, S), fill=hexc("1F9A8E"))
put(c, 5, 7)
c, d = cell("bark", 6, 7)
d.rectangle((0, 0, S, S), fill=hexc("7A5236"))
for k in range(30):
    x = k * 9
    d.line([(x + 3 * math.sin(y / 17 + k), y) for y in range(0, S + 4, 4)], fill=shade(hexc("7A5236"), .75), width=3)
put(c, 6, 7)
c, d = cell("brand", 7, 7)
d.rectangle((0, 0, S, S), fill=hexc("1F9A8E"))
ctext(d, (S / 2, 100), "BEBIDAS", 46, (255, 255, 255), hexc("0F5F57"), 3)
ctext(d, (S / 2, 165), "GELADAS", 46, hexc("FFE14D"), hexc("0F5F57"), 3)
put(c, 7, 7)

img.save("/home/claude/real/IK_Labels_albedo.png")
img.resize((1024, 1024)).save("/tmp/claude-0/labels_preview.png")
import json
json.dump(LABELS, open("/home/claude/real/labels.json", "w"))
print(len(LABELS))
