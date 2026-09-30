"""Painted textures for the detailed ("real") kit: a 2048 product-label atlas and tileable materials.
Output: tex/IK_R_<name>_albedo.png  (copied to Assets/Art/Interior/Textures)."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/mnt/user-data/uploads/Checkout-mobile/unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Fonts/Fredoka_700Bold.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
rng = np.random.default_rng(7)


def font(size, serif=False):
    return ImageFont.truetype(SERIF if serif else FONT, size)


def hexc(h, a=255):
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def noise(n, octaves=5, seed=0, base=4):
    """Tileable fbm value noise in [0,1], shape (n,n)."""
    r = np.random.default_rng(seed)
    out = np.zeros((n, n)); amp = 1; tot = 0
    for o in range(octaves):
        g = base * 2 ** o
        grid = r.random((g, g))
        x = np.linspace(0, g, n, endpoint=False)
        i0 = np.floor(x).astype(int); f = x - i0; f = f * f * (3 - 2 * f)
        i1 = (i0 + 1) % g
        a = grid[i0][:, i0]; b = grid[i0][:, i1]; c = grid[i1][:, i0]; d = grid[i1][:, i1]
        fx = f[None, :]; fy = f[:, None]
        v = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
        out += v * amp; tot += amp; amp *= .5
    return out / tot


def colorize(v, stops):
    """v in [0,1] -> RGB via list of (t, hex)."""
    v = np.clip(v, 0, 1)
    ts = [s[0] for s in stops]; cs = np.array([hexc(s[1])[:3] for s in stops], float)
    out = np.zeros(v.shape + (3,))
    for ch in range(3):
        out[..., ch] = np.interp(v, ts, cs[:, ch])
    return Image.fromarray(out.astype(np.uint8), "RGB")


# ------------------------------------------------------------------ tileables
def planks(n=1024, light=("C9975B", "A87140", "7E4F2B"), rows=6, name="Planks"):
    grain = noise(n, 6, 1, 3)
    y = np.linspace(0, 1, n, endpoint=False)[:, None]
    x = np.linspace(0, 1, n, endpoint=False)[None, :]
    streak = noise(n, 4, 2, 2)
    fibres = np.sin((x * 60 + streak * 18 + grain * 3) * math.pi) * .5 + .5
    v = .45 + .35 * (fibres * .6 + grain * .4) - .1
    row = np.floor(y * rows)
    tint = (np.random.default_rng(5).random(rows)[row.astype(int)] - .5) * .18
    v = v + tint
    img = colorize(v, [(0, light[2]), (.5, light[1]), (1, light[0])])
    d = ImageDraw.Draw(img)
    h = n / rows
    for r in range(rows):
        d.line([(0, r * h), (n, r * h)], fill=hexc("4A2E1A"), width=5)
        off = (r * 0.37 % 1) * n
        for k in range(2):
            xx = (off + k * n / 2) % n
            d.line([(xx, r * h), (xx, (r + 1) * h)], fill=hexc("4A2E1A"), width=4)
            for s in (-1, 1):
                d.ellipse([xx + s * 18 - 5, r * h + h * .25 - 5, xx + s * 18 + 5, r * h + h * .25 + 5], fill=hexc("5A3A22"))
                d.ellipse([xx + s * 18 - 5, r * h + h * .75 - 5, xx + s * 18 + 5, r * h + h * .75 + 5], fill=hexc("5A3A22"))
    return img.filter(ImageFilter.GaussianBlur(.6)), name


def woodgrain(n=1024, cols=("E2B57A", "C08A52", "9A6536"), name="Wood"):
    g = noise(n, 6, 11, 2)
    x = np.linspace(0, 1, n, endpoint=False)[None, :]
    y = np.linspace(0, 1, n, endpoint=False)[:, None]
    rings = np.sin((y * 14 + g * 5 + np.sin(x * 2 * math.pi) * .3) * 2 * math.pi) * .5 + .5
    v = rings * .55 + noise(n, 5, 12, 8) * .45
    return colorize(v, [(0, cols[2]), (.55, cols[1]), (1, cols[0])]), name


def grain(n=1024, cols=("D9A56A", "C08A52", "A87444"), name="Wood", seed=11):
    """Long, calm grain (cabinetry): straight streaks with fine fibre noise."""
    g = noise(n, 5, seed, 2); fine = noise(n, 4, seed + 1, 32)
    x = np.linspace(0, 1, n, endpoint=False)[None, :]; y = np.linspace(0, 1, n, endpoint=False)[:, None]
    streak = np.sin((y * 22 + g * 2.2 + np.sin(x * 2 * math.pi) * .15) * 2 * math.pi) * .5 + .5
    v = .5 + .22 * (streak - .5) + .28 * (fine - .5) + .18 * (g - .5)
    return colorize(v, [(0, cols[2]), (.5, cols[1]), (1, cols[0])]), name


def bark(n=1024):
    g = noise(n, 6, 21, 4)
    x = np.linspace(0, 1, n, endpoint=False)[None, :]
    ridges = np.abs(np.sin((x * 9 + g * 2.2) * math.pi)) ** .6
    v = ridges * .7 + noise(n, 5, 22, 16) * .3
    return colorize(v, [(0, "3B2616"), (.45, "6B4428"), (.8, "8E6440"), (1, "A7825A")]), "Bark"


def leaves(n=1024, pal=("2F6B2A", "3F8A33", "5DAE3E", "8CCB5A", "B5DD7A"), name="Leaves", seed=31):
    img = Image.new("RGB", (n, n), hexc(pal[0])[:3])
    d = ImageDraw.Draw(img)
    r = random.Random(seed)
    for layer in range(5):
        col = pal[min(4, layer)]
        for _ in range(900 if layer < 3 else 500):
            cx, cy = r.random() * n, r.random() * n
            L = r.uniform(26, 46) * (1 - layer * .08); W = L * r.uniform(.42, .55); a = r.random() * math.tau
            pts = []
            for t in np.linspace(0, math.pi * 2, 18):
                px = math.cos(t) * L / 2; py = math.sin(t) * W / 2 * (1 - .35 * math.cos(t))
                pts.append((px, py))
            for dx in (-n, 0, n):
                for dy in (-n, 0, n):
                    poly = [(cx + dx + px * math.cos(a) - py * math.sin(a), cy + dy + px * math.sin(a) + py * math.cos(a)) for px, py in pts]
                    shade = r.uniform(.85, 1.1)
                    c = tuple(min(255, int(ch * shade)) for ch in hexc(col)[:3])
                    d.polygon(poly, fill=c)
                    d.line([poly[0], poly[9]], fill=tuple(int(ch * .75) for ch in c), width=2)
    return img.filter(ImageFilter.GaussianBlur(.5)), name


def brushed(n=512):
    g = noise(n, 3, 41, 2)
    x = np.random.default_rng(3).random((1, n)).repeat(n, 0)
    v = .55 + .25 * g + .12 * (np.repeat(np.random.default_rng(4).random((n, 1)), n, 1) - .5)
    v = v * .85 + x * .15
    img = colorize(v, [(0, "8C969C"), (.5, "C3CBCF"), (1, "E8EDEF")])
    return img.filter(ImageFilter.GaussianBlur((2, 0))), "Brushed"


def fabric(n=512, a="3A9C8F", b="2E8074", name="Fabric"):
    img = Image.new("RGB", (n, n), hexc(a)[:3])
    d = ImageDraw.Draw(img)
    for i in range(0, n, 4):
        d.line([(0, i), (n, i)], fill=hexc(b)[:3], width=1)
        d.line([(i, 0), (i, n)], fill=tuple(min(255, c + 18) for c in hexc(a)[:3]), width=1)
    arr = np.array(img).astype(float) * (0.9 + 0.2 * noise(n, 4, 51, 8)[..., None])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), name


def stone_wall(n=1024):
    img = Image.new("RGB", (n, n), hexc("9E9282")[:3])
    d = ImageDraw.Draw(img)
    r = random.Random(61)
    rows = 10; h = n / rows
    for row in range(rows):
        x = -r.random() * 80
        while x < n:
            w = r.uniform(80, 170)
            base = r.choice(["C9B79C", "BFA98A", "D8C8AE", "B39C7E", "CDBB9E"])
            for dx in (-n, 0, n):
                d.rounded_rectangle([x + dx + 3, row * h + 3, x + dx + w - 3, row * h + h - 3], 12, fill=hexc(base)[:3])
            x += w
    arr = np.array(img).astype(float) * (0.85 + 0.3 * noise(n, 5, 62, 8)[..., None])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)), "StoneWall"


def gelato(n=256, base="F4A6C1", flecks=None, swirl=None, seed=0):
    g = noise(n, 5, 70 + seed, 3)
    x = np.linspace(0, 1, n, endpoint=False)[None, :]; y = np.linspace(0, 1, n, endpoint=False)[:, None]
    ridge = np.sin((x * 3 + y * 5 + g * 2.5) * 2 * math.pi) * .5 + .5
    b = np.array(hexc(base)[:3], float)
    v = (0.82 + 0.25 * ridge[..., None] + 0.08 * g[..., None]) * b
    if swirl:
        s = np.array(hexc(swirl)[:3], float)
        m = (np.sin((x * 2 - y * 3 + g * 3) * 2 * math.pi) > .72)[..., None]
        v = np.where(m, s * (0.9 + .2 * ridge[..., None]), v)
    img = Image.fromarray(np.clip(v, 0, 255).astype(np.uint8), "RGB")
    if flecks:
        d = ImageDraw.Draw(img); r = random.Random(seed)
        for _ in range(90):
            cx, cy = r.random() * n, r.random() * n; s = r.uniform(2, 5)
            d.ellipse([cx - s, cy - s * .7, cx + s, cy + s * .7], fill=hexc(flecks)[:3])
    return img


# ------------------------------------------------------------------ label atlas
C = 256


def cell(atlas, cx, cy):
    return atlas.crop((cx * C, cy * C, cx * C + C, cy * C + C)), (cx * C, cy * C)


def centered(d, text, y, size, fill, box=(0, C), serif=False, stroke=0, stroke_fill=None):
    f = font(size, serif)
    w = d.textlength(text, font=f)
    while w > (box[1] - box[0]) * .92 and size > 10:
        size -= 2; f = font(size, serif); w = d.textlength(text, font=f)
    d.text(((box[0] + box[1]) / 2 - w / 2, y - size * .6), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


def soda(img, bg, fg, name, sub, accent):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=hexc(bg))
    for i in range(0, C, 16):
        d.line([(0, i), (C, i)], fill=tuple(min(255, c + 12) for c in hexc(bg)[:3]), width=1)
    d.ellipse([C * .18, C * .16, C * .82, C * .84], fill=hexc(accent))
    d.ellipse([C * .22, C * .2, C * .78, C * .8], fill=hexc(bg))
    d.arc([C * .05, C * .35, C * .95, C * .9], 200, 340, fill=hexc(fg), width=10)
    centered(d, name, C * .48, 58, hexc(fg), stroke=3, stroke_fill=hexc(accent))
    centered(d, sub, C * .74, 26, hexc(fg))


def can_wrap(img, bg, fg, name, band):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=hexc(bg))
    d.polygon([(0, C * .62), (C, C * .38), (C, C * .56), (0, C * .8)], fill=hexc(band))
    d.rectangle([0, 0, C, C * .07], fill=hexc("D8DDE0")); d.rectangle([0, C * .93, C, C], fill=hexc("D8DDE0"))
    centered(d, name, C * .34, 64, hexc(fg), stroke=2, stroke_fill=hexc(band))
    for k in range(5):
        x = C * (.15 + k * .17)
        d.ellipse([x - 5, C * .85 - 5, x + 5, C * .85 + 5], fill=hexc(fg))


def water(img, bg, name):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=hexc("FFFFFF"))
    d.polygon([(0, C * .7), (C * .3, C * .38), (C * .5, C * .55), (C * .72, C * .3), (C, C * .65), (C, C), (0, C)], fill=hexc(bg))
    d.polygon([(C * .63, C * .38), (C * .72, C * .3), (C * .8, C * .4)], fill=hexc("FFFFFF"))
    centered(d, name, C * .2, 54, hexc("1E5FA8"))
    centered(d, "MINERAL", C * .85, 26, hexc("FFFFFF"))


def juice(img, bg, fruit, name):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=hexc(bg))
    d.rounded_rectangle([C * .08, C * .08, C * .92, C * .92], 20, outline=hexc("FFFFFF"), width=6)
    d.ellipse([C * .28, C * .36, C * .72, C * .8], fill=hexc(fruit))
    d.ellipse([C * .36, C * .44, C * .5, C * .56], fill=hexc("FFFFFF", 150))
    d.polygon([(C * .5, C * .36), (C * .62, C * .22), (C * .66, C * .3)], fill=hexc("4E9A3A"))
    centered(d, name, C * .2, 44, hexc("FFFFFF"))


def beer(img, bg, fg, name):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=hexc("00000000"[:6]))
    d.rectangle([0, 0, C, C], fill=hexc(bg))
    d.ellipse([C * .12, C * .12, C * .88, C * .88], fill=hexc("F5E9C8"), outline=hexc(fg), width=8)
    centered(d, name, C * .5, 50, hexc(fg), serif=True)
    centered(d, "PILSEN", C * .7, 22, hexc(fg))
    for k in range(3):
        d.polygon([(C * (.4 + k * .1), C * .3), (C * (.45 + k * .1), C * .22), (C * (.5 + k * .1), C * .3)], fill=hexc("C9A227"))


def wine(img, paper, ink, name, sub, crest):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=hexc(paper))
    d.rectangle([C * .06, C * .06, C * .94, C * .94], outline=hexc(ink), width=3)
    d.rectangle([C * .09, C * .09, C * .91, C * .91], outline=hexc(crest), width=2)
    d.polygon([(C * .5, C * .14), (C * .62, C * .22), (C * .6, C * .36), (C * .5, C * .42), (C * .4, C * .36), (C * .38, C * .22)], fill=hexc(crest))
    for k in range(6):
        x = C * (.45 + (k % 3) * .05); y = C * (.24 + (k // 3) * .06)
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=hexc(ink))
    centered(d, name, C * .6, 40, hexc(ink), serif=True)
    centered(d, sub, C * .78, 22, hexc(crest), serif=True)


def package(img, bg, fg, name, art, accent):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=hexc(bg))
    d.rectangle([0, 0, C, C * .28], fill=hexc(accent))
    centered(d, name, C * .14, 44, hexc(fg))
    cx, cy = C * .5, C * .62
    if art == "cereal":
        d.ellipse([cx - 80, cy - 40, cx + 80, cy + 60], fill=hexc("FFFFFF"))
        for k in range(14):
            x = cx - 60 + (k * 37) % 120; y = cy - 25 + (k * 23) % 60
            d.ellipse([x - 12, y - 9, x + 12, y + 9], fill=hexc("E3A33A"), outline=hexc("B8751E"), width=2)
    elif art == "pasta":
        for k in range(9):
            d.line([(cx - 70 + k * 18, cy - 60), (cx - 50 + k * 18, cy + 70)], fill=hexc("F2D27A"), width=9)
    elif art == "rice":
        for k in range(60):
            x = cx - 70 + (k * 53) % 140; y = cy - 50 + (k * 29) % 100
            d.ellipse([x - 6, y - 3, x + 6, y + 3], fill=hexc("FFFFFF"))
    elif art == "beans":
        for k in range(30):
            x = cx - 70 + (k * 53) % 140; y = cy - 50 + (k * 31) % 100
            d.ellipse([x - 9, y - 6, x + 9, y + 6], fill=hexc("3B1E14"))
    elif art == "coffee":
        d.ellipse([cx - 60, cy - 30, cx + 60, cy + 50], fill=hexc("FFFFFF"))
        d.ellipse([cx - 48, cy - 22, cx + 48, cy + 20], fill=hexc("5A3521"))
        for k in range(3):
            d.arc([cx - 30 + k * 20, cy - 90, cx - 10 + k * 20, cy - 40], 90, 270, fill=hexc("FFFFFF"), width=5)
    elif art == "cookies":
        for k in range(5):
            x = cx - 70 + k * 35; d.ellipse([x - 30, cy - 30, x + 30, cy + 30], fill=hexc("C98A4B"), outline=hexc("8A5A2A"), width=3)
            for j in range(4): d.ellipse([x - 12 + j * 7, cy - 10 + (j % 2) * 12, x - 6 + j * 7, cy - 4 + (j % 2) * 12], fill=hexc("4A2A16"))
    elif art == "milk":
        d.polygon([(cx - 70, cy + 60), (cx - 40, cy - 20), (cx, cy + 10), (cx + 40, cy - 30), (cx + 70, cy + 60)], fill=hexc("5DAE3E"))
        d.ellipse([cx - 25, cy - 5, cx + 25, cy + 30], fill=hexc("FFFFFF"), outline=hexc("222222"), width=3)
    elif art == "soap":
        for k in range(6):
            x = cx - 60 + (k * 41) % 120; y = cy - 40 + (k * 27) % 90; s = 14 + k * 3
            d.ellipse([x - s, y - s, x + s, y + s], outline=hexc("FFFFFF"), width=4)
    elif art == "chips":
        for k in range(7):
            x = cx - 60 + (k * 41) % 120; y = cy - 40 + (k * 29) % 90
            d.ellipse([x - 26, y - 18, x + 26, y + 18], fill=hexc("F2C94C"), outline=hexc("D9A032"), width=3)
    elif art == "choco":
        for i in range(3):
            for j in range(2):
                d.rounded_rectangle([cx - 66 + i * 45, cy - 40 + j * 45, cx - 26 + i * 45, cy + j * 45], 6, fill=hexc("5A3521"), outline=hexc("3B2216"), width=3)
    elif art == "sauce":
        d.ellipse([cx - 55, cy - 55, cx + 55, cy + 55], fill=hexc("D74A3C"))
        d.polygon([(cx - 10, cy - 55), (cx + 10, cy - 55), (cx, cy - 80)], fill=hexc("4E9A3A"))
    elif art == "oil":
        d.ellipse([cx - 50, cy - 60, cx + 50, cy + 60], fill=hexc("F2C23F"))
        d.ellipse([cx - 20, cy - 30, cx + 5, cy], fill=hexc("FFF3B0"))
    elif art == "tissue":
        for i in range(2):
            for j in range(2):
                d.ellipse([cx - 70 + i * 70, cy - 55 + j * 55, cx + i * 70, cy + j * 55], fill=hexc("FFFFFF"), outline=hexc("C8D8E8"), width=4)
    d.rectangle([0, C * .9, C, C], fill=hexc(accent))


def build_atlas():
    atlas = Image.new("RGBA", (C * 8, C * 8), (255, 255, 255, 255))
    jobs = {}
    sodas = [("D62B2B", "FFFFFF", "FIZZ", "COLA", "F2C94C"), ("2F8F3A", "FFFFFF", "TUPI", "GUARANÁ", "F2C94C"),
             ("F28C28", "FFFFFF", "LARANJITA", "LARANJA", "FFE08A"), ("B8D93A", "1E5D1E", "LIMÃO+", "LIMÃO", "FFFFFF"),
             ("7B3FA0", "FFFFFF", "UVINHA", "UVA", "F2C94C"), ("1B1B1B", "E03030", "FIZZ", "ZERO", "E03030"),
             ("E8E1C7", "2C6E49", "TÔNICA", "ÁGUA TÔNICA", "2C6E49"), ("C98A2E", "FFFFFF", "CHÁ GELADO", "PÊSSEGO", "F7D08A")]
    for i, s in enumerate(sodas):
        jobs[(i, 0)] = lambda im, s=s: soda(im, *s)
    cans = [("E03A3A", "FFFFFF", "FIZZ", "B81F1F"), ("1E88C8", "FFFFFF", "BRISA", "FFFFFF"), ("2FA84F", "FFFFFF", "TUPI", "F2C94C"),
            ("222831", "7CF03A", "VOLT", "7CF03A"), ("F2C94C", "7A3B00", "OURO", "C98A2E"), ("E86A9E", "FFFFFF", "POP", "FFFFFF"),
            ("F28C28", "FFFFFF", "SOL", "D95F1A"), ("C9D2D6", "D74A3C", "LIGHT", "D74A3C")]
    for i, s in enumerate(cans):
        jobs[(i, 1)] = lambda im, s=s: can_wrap(im, *s)
    jobs[(0, 2)] = lambda im: water(im, "5CB8E6", "SERRA")
    jobs[(1, 2)] = lambda im: water(im, "7FD1C7", "FONTE")
    jobs[(2, 2)] = lambda im: juice(im, "F28C28", "F7A12A", "SUCO")
    jobs[(3, 2)] = lambda im: juice(im, "7B3FA0", "9B59C6", "SUCO")
    jobs[(4, 2)] = lambda im: beer(im, "1F5E2E", "1F5E2E", "OURO")
    jobs[(5, 2)] = lambda im: beer(im, "8A1C1C", "8A1C1C", "BRAVA")
    jobs[(6, 2)] = lambda im: can_wrap(im, "101820", "F2C94C", "RAIO", "F2C94C")
    jobs[(7, 2)] = lambda im: juice(im, "E8C547", "F2E05A", "LIMONADA")
    wines = [("F3EBD8", "5B1A28", "QUINTA", "RESERVA 2019", "8E2240"), ("EFE6CF", "2F3A40", "VALE ALTO", "CABERNET", "7A1E2E"),
             ("FFF9EA", "20456B", "BRISA", "SAUVIGNON", "C9A227"), ("F6E3E3", "8E2240", "ROSÉ", "PROVENCE", "E86A9E"),
             ("1E1E1E", "E0B040", "GRAN", "MALBEC", "E0B040"), ("F3EBD8", "3B5E2B", "SERRA", "MERLOT", "8E2240"),
             ("FFFFFF", "C9A227", "ESPUMANTE", "BRUT", "C9A227"), ("EADBC0", "5B1A28", "DOURO", "TINTO", "8A5A20")]
    for i, s in enumerate(wines):
        jobs[(i, 3)] = lambda im, s=s: wine(im, *s)
    packs = [("F2C23F", "FFFFFF", "FLOCOS", "cereal", "D74A3C"), ("FFFFFF", "1D4E89", "MASSA", "pasta", "1D4E89"),
             ("FFFFFF", "D74A3C", "ARROZ", "rice", "D74A3C"), ("F4EFE4", "5A3521", "FEIJÃO", "beans", "8A5A20"),
             ("5A3521", "FFFFFF", "CAFÉ", "coffee", "C9A227"), ("3E8FD6", "FFFFFF", "BISCOITO", "cookies", "F2C23F"),
             ("FFFFFF", "1D4E89", "LEITE", "milk", "3E8FD6"), ("E86A9E", "FFFFFF", "SABÃO", "soap", "B83A74")]
    for i, s in enumerate(packs):
        jobs[(i, 4)] = lambda im, s=s: package(im, *s)
    packs2 = [("D74A3C", "FFFFFF", "CHIPS", "chips", "F2C23F"), ("5A3521", "F2C23F", "CHOCO", "choco", "8A5A20"),
              ("FFFFFF", "D74A3C", "MOLHO", "sauce", "4E9A3A"), ("FFF3B0", "8A5A20", "ÓLEO", "oil", "4E9A3A"),
              ("DCEBF7", "1D4E89", "PAPEL", "tissue", "3E8FD6"), ("2FA84F", "FFFFFF", "CHIPS", "chips", "1E6B32"),
              ("8E6CCF", "FFFFFF", "BALAS", "soap", "5B3E9E"), ("1F9A8E", "FFFFFF", "DETERGENTE", "soap", "17655D")]
    for i, s in enumerate(packs2):
        jobs[(i, 5)] = lambda im, s=s: package(im, *s)
    flavours = [("F4A6C1", "D6336C", None), ("B5D98A", "6B4E2E", None), ("F7EFD8", None, None), ("6B3E26", None, "3E2215"),
                ("F7B733", None, None), ("A8E6CF", "3E2215", None), ("F7F2E6", "3E2215", None), ("9C7BD8", "5B3E9E", None)]
    for i, (b, fl, sw) in enumerate(flavours):
        jobs[(i, 6)] = lambda im, b=b, fl=fl, sw=sw, i=i: im.paste(gelato(C, b, fl, sw, i))
    for (cx, cy), fn in jobs.items():
        im, pos = cell(atlas, cx, cy)
        im = im.convert("RGB")
        fn(im)
        atlas.paste(im, pos)
    # row 7: misc signs
    im = Image.new("RGB", (C * 2, C), hexc("1D2B4F")[:3]); d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 8, C * 2 - 8, C - 8], 30, outline=hexc("E0B040")[:3], width=10)
    centered(d, "GELADAS", C * .45, 110, hexc("FFFFFF")[:3], box=(0, C * 2))
    atlas.paste(im, (0, 7 * C))
    im = Image.new("RGB", (C, C), hexc("2B2B2B")[:3]); d = ImageDraw.Draw(im)
    for k in range(0, C, 22):
        d.rounded_rectangle([10, k + 4, C - 10, k + 14], 5, fill=hexc("111111")[:3])
    atlas.paste(im, (2 * C, 7 * C))  # vent grille
    im = Image.new("RGB", (C, C), hexc("FFFFFF")[:3]); d = ImageDraw.Draw(im)
    for k in range(4):
        x0 = k * C / 4
        d.rectangle([x0 + 4, 40, x0 + C / 4 - 4, 216], fill=hexc(["F2C23F", "FFFFFF", "F2C23F", "FFFFFF"][k])[:3], outline=hexc("D74A3C")[:3], width=3)
        centered(d, "4,99", 128, 34, hexc("D74A3C")[:3], box=(x0, x0 + C / 4))
    atlas.paste(im, (3 * C, 7 * C))  # price rail
    im = Image.new("RGB", (C * 2, C), hexc("2E3B33")[:3]); d = ImageDraw.Draw(im)
    centered(d, "GELATO", 50, 60, hexc("FFD97A")[:3], box=(0, C * 2))
    for i, line in enumerate(["1 BOLA  8,00", "2 BOLAS 14,00", "CASCÃO 5,00", "MILK-SHAKE 15,00"]):
        centered(d, line, 110 + i * 38, 30, hexc("FBF8F1")[:3], box=(0, C * 2))
    atlas.paste(im, (4 * C, 7 * C))  # gelato menu
    im = Image.new("RGB", (C * 2, C), hexc("2E3B33")[:3]); d = ImageDraw.Draw(im)
    centered(d, "CAFÉ", 48, 60, hexc("FFD97A")[:3], box=(0, C * 2))
    for i, line in enumerate(["ESPRESSO 5,00", "CAPPUCCINO 8,00", "PÃO DE QUEIJO 4,00", "BOLO 7,00"]):
        centered(d, line, 110 + i * 38, 30, hexc("FBF8F1")[:3], box=(0, C * 2))
    atlas.paste(im, (6 * C, 7 * C))  # café menu
    return atlas


if __name__ == "__main__":
    out = {}
    build_atlas().convert("RGB").save("tex/IK_R_Labels_albedo.png")
    for img, name in (planks(), planks(light=("8A5A3A", "6B4128", "4A2C18"), name="PlanksDark"), grain(),
                      grain(cols=("8A4E30", "6E3B22", "56301C"), name="WoodDark", seed=15), bark(), leaves(),
                      leaves(pal=("2A5A24", "336B2A", "437F34", "5B9A40", "7DB356"), name="Hedge", seed=33), brushed(),
                      fabric(), fabric(a="E0B35A", b="C9973E", name="FabricMustard"), stone_wall()):
        img.save("tex/IK_R_%s_albedo.png" % name)
    print("ok")
