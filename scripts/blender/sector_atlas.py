"""Painted product atlas for the special sectors (round 3): FT_Sector_albedo.png, 8x8 cells, no words or letters.

Run with plain Python (PIL + numpy + scipy):  python3 sector_atlas.py <out.png>
Cell layout (column, row; row 0 is the top of the image) is CELLS below; sector_detail.py maps UVs into it.
Inside a cell, v = 0 is the BOTTOM edge (Blender UV), so "the top of an object" is painted at the top of the cell.
"""
import sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

S = 256                      # cell size in pixels
N = 8
CELLS = [
    ["loaf", "boule", "baguette", "croissant", "roll", "cake_choc", "cake_straw", "cake_cream"],
    ["steak", "tbone", "ribs", "chop", "sausage", "chicken", "ham", "salami"],
    ["rind_wax", "rind_natural", "cheese_cut", "blue_cut", "provolone", "brie", "parmesan", "ground"],
    ["fish_blue", "fish_red", "salmon", "shrimp", "lobster", "squid", "lemon_cut", "ice"],
    ["gelato_pistachio", "gelato_choc", "gelato_straw", "gelato_cream", "gelato_mint", "gelato_mango", "gelato_berry", "sprinkles"],
    ["waffle", "wl_grape", "wl_glass", "bottle_wall", "wl_leaf", "wl_star", "cork", "burlap"],
    ["orange_cut", "lime_cut", "kiwi_cut", "melon_cut", "strawberry", "pineapple", "apple", "melon_skin"],
    ["chalk_bread", "chalk_meat", "chalk_cheese", "chalk_fish", "chalk_ice", "chalk_wine", "chalk_juice", "leaf"],
]
INDEX = {n: (c, r) for r, row in enumerate(CELLS) for c, n in enumerate(row)}
rng = np.random.default_rng(7)


def noise(scale, octaves=3, seed=0):
    """Smooth value noise in 0..1 over one cell (scale = blobs across)."""
    r = np.random.default_rng(seed)
    out = np.zeros((S, S))
    amp, tot = 1.0, 0
    for o in range(octaves):
        n = max(2, int(scale * 2 ** o))
        g = r.random((n + 3, n + 3))
        z = ndimage.zoom(g, (S + 3 * S / n) / (n + 3), order=3)[:S, :S]
        out += z * amp
        tot += amp
        amp *= .5
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-9)


def lerp(a, b, t):
    a, b = np.array(a, float), np.array(b, float)
    return a + (b - a) * t[..., None]


def grid():
    y, x = np.mgrid[0:S, 0:S] / (S - 1)
    return x, y                                     # x: 0 left .. 1 right, y: 0 top .. 1 bottom


class Cell:
    def __init__(self, name, base=(200, 200, 200)):
        self.name = name
        self.a = np.zeros((S, S, 3)) + np.array(base, float)

    def img(self):
        return Image.fromarray(np.clip(self.a, 0, 255).astype(np.uint8))

    def put(self, im):
        self.a = np.array(im.convert("RGB"), float)

    def draw(self):
        im = self.img()
        return im, ImageDraw.Draw(im)

    def blend(self, col, mask):
        self.a = self.a * (1 - mask[..., None]) + np.array(col, float) * mask[..., None]

    def shade(self, t, k=.25):
        self.a *= (1 - k / 2 + k * t)[..., None]


def mask_from(draw_fn, blur=0):
    m = Image.new("L", (S, S), 0)
    draw_fn(ImageDraw.Draw(m))
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    return np.array(m, float) / 255


P = lambda u, v: (u * S, v * S)                    # u, v in 0..1 image space (v from top)


# ------------------------------------------------------------------------------------------------ bakery
def crust(cell, light, dark, seed):
    x, y = grid()
    n = noise(5, 4, seed)
    cell.a = lerp(light, dark, np.clip(.25 + .9 * (1 - np.abs(y - .5) * 1.6) * .6 + (n - .5) * .5, 0, 1))
    speck = noise(40, 1, seed + 3) > .82
    cell.blend((235, 220, 190), speck * .35)


def score_lines(cell, lines, w=14, col=(236, 206, 150)):
    m = mask_from(lambda d: [d.line([P(*a), P(*b)], fill=255, width=w) for a, b in lines], 3)
    cell.blend(col, m * .9)
    m2 = mask_from(lambda d: [d.line([P(a[0], a[1] + .03), P(b[0], b[1] + .03)], fill=255, width=w // 3) for a, b in lines], 2)
    cell.blend((110, 60, 25), m2 * .5)


def cell_loaf(c):
    crust(c, (214, 150, 78), (140, 78, 32), 1)
    score_lines(c, [((.12 + k * .2, .32), (.28 + k * .2, .68)) for k in range(4)])


def cell_boule(c):
    crust(c, (220, 160, 88), (150, 86, 38), 2)
    score_lines(c, [((.2, .5), (.8, .5)), ((.5, .2), (.5, .8))], 18)
    m = mask_from(lambda d: d.ellipse([P(.15, .15), P(.85, .85)], outline=255, width=6), 4)
    c.blend((240, 228, 205), m * .4)                 # flour dusting ring


def cell_baguette(c):
    crust(c, (226, 170, 92), (160, 96, 40), 3)
    score_lines(c, [((.06 + k * .18, .35), (.2 + k * .18, .65)) for k in range(5)], 12)


def cell_croissant(c):
    x, y = grid()
    base = lerp((228, 160, 70), (156, 82, 28), np.clip(.5 + .5 * np.sin(x * math.pi * 10) ** 2 * .9 - .3 + noise(6, 2, 4) * .4, 0, 1))
    c.a = base
    c.shade(1 - np.abs(y - .5) * 2, .5)
    c.blend((250, 220, 160), np.clip(np.sin(x * math.pi * 10 + 1.2), 0, 1) ** 8 * .6)


def cell_roll(c):
    crust(c, (226, 160, 80), (160, 90, 34), 5)
    x, y = grid()
    c.blend((255, 240, 210), np.clip(1 - ((x - .38) ** 2 + (y - .35) ** 2) * 18, 0, 1) * .5)   # egg-wash gloss
    score_lines(c, [((.3, .5), (.7, .5))], 10)


def cell_cake(c, sponge, frost, deco):
    x, y = grid()
    c.a[:] = sponge
    for k, z in enumerate((.42, .7)):                # cream layers
        c.blend(frost, ((y > z - .035) & (y < z + .035)).astype(float))
    drip = .26 + .08 * np.sin(x * math.pi * 14) ** 2 + .05 * np.sin(x * 37) * (np.sin(x * math.pi * 14) > .6)
    c.blend(frost, (y < drip).astype(float))
    c.blend(tuple(min(255, v + 40) for v in frost), np.clip(1 - np.abs(y - drip * .5) * 30, 0, 1) * .3)
    im, d = c.draw()
    for k in range(7):
        u = .07 + k * .143
        d.ellipse([P(u - .035, .78), P(u + .035, .85)], fill=deco)
    c.put(im)
    c.shade(noise(6, 2, 9), .12)


# ------------------------------------------------------------------------------------------------ butcher
def marbling(c, red, seed, fat_side=True, density=.68):
    x, y = grid()
    n = noise(9, 4, seed)
    c.a = lerp(red, tuple(v * .72 for v in red), noise(4, 3, seed + 1))
    veins = np.clip((np.abs(noise(7, 3, seed + 2) - .5) < .014).astype(float) + (noise(30, 2, seed + 5) > density + .2) * .8, 0, 1)
    c.blend((246, 222, 214), ndimage.gaussian_filter(veins, .8) * .6)
    if fat_side:
        edge = .1 + .03 * np.sin(x * 9 + seed)
        c.blend((248, 236, 214), np.clip((edge - y) * 40, 0, 1))
        c.blend((236, 196, 170), np.clip(1 - np.abs(y - edge) * 40, 0, 1) * .5)


def cell_steak(c):
    marbling(c, (176, 38, 40), 11)


def cell_tbone(c):
    marbling(c, (170, 40, 40), 12)
    im, d = c.draw()
    d.rectangle([P(.47, .12), P(.55, .9)], fill=(244, 238, 222))
    d.rectangle([P(.22, .12), P(.8, .22)], fill=(244, 238, 222))
    d.ellipse([P(.46, .82), P(.56, .94)], fill=(244, 238, 222))
    c.put(im.filter(ImageFilter.GaussianBlur(.8)))


def cell_ribs(c):
    marbling(c, (160, 44, 38), 13, False, .62)
    x, y = grid()
    c.blend((132, 54, 30), np.clip(np.sin(x * math.pi * 6) ** 16, 0, 1) * .6)       # bone grooves
    c.blend((168, 74, 34), np.clip((y - .7) * 6, 0, 1) * .4)                         # seared bark


def cell_chop(c):
    marbling(c, (226, 140, 136), 14, True, .78)


def cell_sausage(c):
    x, y = grid()
    c.a = lerp((172, 64, 46), (110, 34, 26), noise(8, 3, 15))
    c.blend((235, 200, 180), (noise(30, 1, 16) > .8) * .5)                           # fat specks
    c.blend((255, 230, 220), np.clip(1 - np.abs(y - .3) * 12, 0, 1) * .35)            # casing sheen


def cell_chicken(c):
    x, y = grid()
    c.a = lerp((236, 176, 90), (172, 98, 36), np.clip(noise(5, 4, 17) * .9 + (1 - y) * .2, 0, 1))
    c.blend((120, 60, 20), (noise(40, 1, 18) > .86) * .5)                             # herbs / pepper
    c.blend((255, 236, 190), np.clip(1 - np.abs(y - .35) * 8, 0, 1) * np.clip(np.sin(x * 9), 0, 1) * .4)


def cell_ham(c):
    x, y = grid()
    c.a = lerp((150, 48, 42), (96, 28, 26), noise(4, 4, 19))
    c.blend((236, 214, 186), np.clip((y - .8) * 12, 0, 1))                           # fat cap at the shank end
    c.blend((215, 180, 140), (np.abs(noise(12, 2, 20) - .5) < .025) * .5)


def cell_salami(c):
    x, y = grid()
    c.a = lerp((172, 52, 56), (130, 34, 42), noise(6, 2, 21))
    c.blend((246, 228, 214), (noise(26, 1, 22) > .74).astype(float))
    c.blend((90, 30, 30), (np.hypot(x - .5, y - .5) > .47).astype(float))


# ------------------------------------------------------------------------------------------------ cheese
def cell_rind_wax(c):
    x, y = grid()
    c.a = lerp((236, 188, 60), (204, 150, 36), noise(5, 4, 23))
    c.blend((250, 222, 120), np.clip(1 - np.abs(y - .25) * 10, 0, 1) * .4)
    c.blend((170, 120, 30), (np.abs(noise(10, 2, 24) - .5) < .02) * .4)


def cell_rind_natural(c):
    c.a = lerp((196, 160, 104), (128, 96, 58), noise(7, 4, 25))
    c.blend((232, 220, 196), (noise(20, 2, 26) > .74) * .5)


def holes(c, n, seed, col_in, col_rim, rmin=.025, rmax=.07):
    r = random.Random(seed)
    im, d = c.draw()
    for _ in range(n):
        u, v, rr = r.random(), r.random(), r.uniform(rmin, rmax)
        d.ellipse([P(u - rr, v - rr * .9), P(u + rr, v + rr * .9)], fill=col_rim)
        d.ellipse([P(u - rr * .82, v - rr * .72), P(u + rr * .82, v + rr * .78)], fill=col_in)
    c.put(im)


def cell_cheese_cut(c):
    c.a = lerp((252, 220, 120), (240, 198, 92), noise(4, 3, 27))
    holes(c, 14, 28, (214, 168, 64), (255, 236, 160))
    x, y = grid()
    c.blend((214, 160, 50), np.clip((y - .9) * 30, 0, 1))                            # rind line at the bottom edge


def cell_blue_cut(c):
    c.a = lerp((246, 240, 222), (232, 224, 200), noise(4, 2, 29))
    v = ndimage.gaussian_filter(((np.abs(noise(9, 3, 30) - .5) < .04) | (noise(22, 2, 31) > .8)).astype(float), 1.5)
    c.blend((70, 96, 110), np.clip(v * 1.6, 0, 1) * .85)


def cell_provolone(c):
    x, y = grid()
    c.a = lerp((236, 186, 76), (196, 136, 40), noise(4, 3, 32))
    c.blend((255, 230, 140), np.clip(1 - np.abs(x - .35) * 8, 0, 1) * .35)


def cell_brie(c):
    c.a = lerp((248, 246, 236), (226, 220, 200), noise(10, 4, 33))
    c.blend((214, 196, 150), (noise(30, 1, 34) > .82) * .35)


def cell_parmesan(c):
    c.a = lerp((240, 212, 140), (214, 176, 96), noise(14, 3, 35))
    c.blend((255, 244, 210), (noise(50, 1, 36) > .7) * .45)                            # crystals
    x, y = grid()
    c.blend((170, 120, 50), np.clip((y - .86) * 20, 0, 1))
    im, d = c.draw()
    for k in range(6):                                                                 # pin-dot rind marks (no letters)
        for j in range(3):
            d.ellipse([P(.1 + k * .15, .9 + j * .03), P(.115 + k * .15, .915 + j * .03)], fill=(120, 80, 30))
    c.put(im)


def cell_ground(c):
    n = noise(36, 2, 37)
    c.a = lerp((196, 66, 70), (140, 36, 42), n)
    c.blend((240, 200, 196), (noise(40, 1, 38) > .78) * .6)


# ------------------------------------------------------------------------------------------------ fish
def fish_side(c, back, side, belly, seed, spots=None):
    """u (x) runs nose (0) -> tail (1); v (y) runs back (top) -> belly (bottom)."""
    x, y = grid()
    t = np.clip(y * 1.25 - .1, 0, 1)
    c.a = np.where((t < .5)[..., None], lerp(back, side, t * 2), lerp(side, belly, (t - .5) * 2))
    c.shade(noise(6, 2, seed), .15)
    scale = ((np.sin(x * math.pi * 46 + np.floor(y * 22) * 1.57) * np.sin(y * math.pi * 22)) > .6)
    c.blend((255, 255, 255), scale * .14)
    c.blend((40, 40, 50), ((np.abs(y - .47 - .03 * np.sin(x * 6)) < .008) & (x > .2)) * .45)   # lateral line
    gill = mask_from(lambda d: d.arc([P(.06, .2), P(.26, .8)], -70, 70, fill=255, width=5), 1)
    c.blend(tuple(v * .5 for v in side), gill * .7)
    if spots:
        r = random.Random(seed)
        im, d = c.draw()
        for _ in range(26):
            u, v = r.uniform(.25, .95), r.uniform(.12, .45)
            d.ellipse([P(u - .012, v - .012), P(u + .012, v + .012)], fill=spots)
        c.put(im)
    c.blend((255, 255, 255), np.clip(1 - np.abs(y - .62) * 14, 0, 1) * .25)                  # wet sheen


def cell_fish_blue(c):
    fish_side(c, (54, 82, 112), (176, 192, 204), (240, 244, 246), 40, (40, 60, 80))


def cell_fish_red(c):
    fish_side(c, (198, 60, 56), (232, 128, 112), (246, 222, 214), 41)


def cell_salmon(c):
    x, y = grid()
    c.a = lerp((250, 136, 92), (232, 104, 68), noise(4, 2, 42))
    r = np.hypot(x - .5, y - .62)
    ang = np.arctan2(y - .62, x - .5)
    w = np.abs(np.sin((y + .25 * np.abs(x - .5) * 2) * math.pi * 7))
    c.blend((255, 222, 204), (w < .1) * .75)
    c.blend((190, 190, 196), np.clip((y - .9) * 20, 0, 1))                                 # skin edge


def cell_shrimp(c):
    x, y = grid()
    c.a = lerp((250, 150, 120), (232, 98, 72), np.clip(1 - y + noise(5, 2, 43) * .3, 0, 1))
    c.blend((255, 228, 214), (np.abs(np.sin(x * math.pi * 7)) < .18) * .55)              # shell segments
    c.blend((200, 70, 50), np.clip(1 - np.abs(y - .15) * 14, 0, 1) * .4)


def cell_lobster(c):
    c.a = lerp((200, 48, 34), (128, 26, 24), noise(6, 4, 44))
    c.blend((240, 140, 90), (noise(24, 1, 45) > .8) * .45)
    x, y = grid()
    c.blend((90, 20, 20), (np.abs(np.sin(x * math.pi * 6)) < .1) * .4)


def cell_squid(c):
    c.a = lerp((246, 230, 232), (228, 206, 214), noise(4, 2, 46))
    c.blend((168, 96, 128), (noise(30, 1, 47) > .7) * .7)
    c.blend((130, 70, 100), (noise(12, 1, 48) > .86) * .5)


def citrus_cut(c, rind, pith, flesh, segs=10, seed=0, center=(.5, .5)):
    x, y = grid()
    r = np.hypot(x - center[0], y - center[1]) * 2
    ang = np.arctan2(y - center[1], x - center[0])
    c.a[:] = flesh
    c.shade(noise(18, 2, seed), .25)
    c.blend(pith, (np.abs(np.sin(ang * segs / 2)) < .06) * (r < .86) * 1.0)
    c.blend(pith, (r < .12) * 1.0)
    c.blend(tuple(min(255, v + 50) for v in flesh), ((noise(40, 1, seed + 1) > .75) & (r < .8)) * .4)
    c.blend(pith, ((r > .84) & (r < .92)) * 1.0)
    c.blend(rind, (r >= .92) * 1.0)


def cell_lemon_cut(c):
    citrus_cut(c, (244, 210, 40), (252, 246, 214), (248, 228, 110), 10, 49)


def cell_ice(c):
    n = noise(16, 4, 50)
    c.a = lerp((236, 246, 252), (196, 222, 236), n)
    c.blend((255, 255, 255), ndimage.gaussian_filter((np.abs(noise(20, 1, 51) - .5) < .03).astype(float), 1) * .9)
    c.blend((170, 206, 226), (noise(26, 1, 52) > .8) * .4)


# ------------------------------------------------------------------------------------------------ gelato
def gelato(c, a, b, seed, bits=None, bitc=None, ripple=None):
    x, y = grid()
    ang = np.arctan2(y - .5, x - .5)
    r = np.hypot(x - .5, y - .5)
    sw = np.sin(r * 30 - ang * 2 + noise(3, 2, seed) * 6)
    c.a = lerp(a, b, np.clip(.5 + .5 * sw, 0, 1) * .6 + noise(8, 2, seed + 1) * .4)
    c.blend((255, 255, 255), np.clip(sw - .8, 0, 1) * 2 * .35)                              # glossy ridges
    if ripple:
        c.blend(ripple, ndimage.gaussian_filter((np.abs(np.sin(r * 18 - ang * 3 + noise(3, 2, seed + 2) * 5)) < .12).astype(float), 1) * .9)
    if bits:
        rr = random.Random(seed)
        im, d = c.draw()
        for _ in range(bits):
            u, v, s = rr.random(), rr.random(), rr.uniform(.012, .03)
            d.ellipse([P(u - s, v - s), P(u + s, v + s * .7)], fill=bitc)
        c.put(im)


def cell_sprinkles(c):
    c.a[:] = (246, 230, 214)
    rr = random.Random(53)
    im, d = c.draw()
    cols = [(232, 80, 91), (242, 194, 63), (95, 181, 72), (62, 143, 214), (244, 166, 193), (250, 248, 240), (122, 74, 46)]
    for _ in range(420):
        u, v, a = rr.random(), rr.random(), rr.random() * math.pi
        du, dv = .022 * math.cos(a), .022 * math.sin(a)
        d.line([P(u - du, v - dv), P(u + du, v + dv)], fill=rr.choice(cols), width=6)
    c.put(im)


# ------------------------------------------------------------------------------------------------ cones, wine, burlap
def cell_waffle(c):
    x, y = grid()
    c.a = lerp((226, 170, 96), (186, 124, 58), noise(6, 2, 54))
    g = (np.abs(np.sin((x + y) * math.pi * 7)) < .16) | (np.abs(np.sin((x - y) * math.pi * 7)) < .16)
    c.blend((150, 92, 40), ndimage.gaussian_filter(g.astype(float), 1) * .8)


def wine_label(c, icon, paper=(244, 236, 216), ink=(29, 43, 79), band=(211, 165, 61)):
    """Wraps around a bottle: the front (middle of the cell) carries a pictogram, framed, no text."""
    c.a[:] = paper
    c.shade(noise(10, 2, 55), .08)
    im, d = c.draw()
    d.rectangle([P(0, .06), P(1, .1)], fill=band)
    d.rectangle([P(0, .9), P(1, .94)], fill=band)
    d.rectangle([P(.3, .2), P(.7, .8)], outline=ink, width=4)
    icon(d, ink, band)
    for k in range(3):                                                                         # "text" as plain bars
        d.rectangle([P(.38, .66 + k * .04), P(.62 - k * .05, .675 + k * .04)], fill=(150, 140, 120))
    c.put(im)


def ico_grape(d, ink, band):
    for k, (u, v) in enumerate([(.44, .3), (.5, .3), (.56, .3), (.47, .38), (.53, .38), (.5, .46)]):
        d.ellipse([P(u - .035, v - .035), P(u + .035, v + .035)], fill=(110, 40, 90))
    d.line([P(.5, .24), P(.53, .2)], fill=(80, 120, 50), width=4)


def ico_glass(d, ink, band):
    d.polygon([P(.42, .26), P(.58, .26), P(.56, .4), P(.44, .4)], fill=(150, 30, 50))
    d.line([P(.5, .4), P(.5, .52)], fill=ink, width=4)
    d.line([P(.44, .53), P(.56, .53)], fill=ink, width=4)


def ico_barrel(d, ink, band):
    d.ellipse([P(.4, .26), P(.6, .54)], fill=(150, 96, 52))
    for v in (.32, .48):
        d.line([P(.41, v), P(.59, v)], fill=ink, width=3)


def ico_leaf(d, ink, band):
    d.polygon([P(.5, .24), P(.6, .34), P(.56, .5), P(.5, .54), P(.44, .5), P(.4, .34)], fill=(90, 140, 60))
    d.line([P(.5, .26), P(.5, .54)], fill=(60, 100, 40), width=3)


def ico_star(d, ink, band):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = .1 if k % 2 == 0 else .045
        pts.append(P(.5 + rr * math.cos(a), .4 + rr * math.sin(a)))
    d.polygon(pts, fill=band)


def cell_bottle_wall(c):
    """Wine rack seen from the front: 4 x 4 bottle ends (dark glass, coloured foil) on dark wood shelves."""
    c.a = lerp((52, 34, 24), (36, 22, 16), noise(5, 2, 90))
    im, d = c.draw()
    rr = random.Random(91)
    glass = [(38, 58, 34), (70, 28, 36), (58, 42, 26), (30, 44, 30)]
    foil = [(122, 30, 46), (211, 165, 61), (29, 43, 79), (40, 40, 40), (232, 220, 190)]
    for j in range(4):
        v = (j + .5) / 4
        d.rectangle([P(0, v + .1), P(1, v + .125)], fill=(120, 84, 52))
        for i in range(4):
            u = (i + .5) / 4
            g = rr.choice(glass)
            d.ellipse([P(u - .1, v - .1), P(u + .1, v + .1)], fill=g, outline=(20, 16, 12), width=3)
            d.ellipse([P(u - .07, v - .075), P(u - .02, v - .03)], fill=tuple(min(255, x + 60) for x in g))
            d.ellipse([P(u - .045, v - .045), P(u + .045, v + .045)], fill=rr.choice(foil))
    c.put(im)


def cell_cork(c):
    c.a = lerp((214, 170, 112), (176, 128, 74), noise(30, 2, 56))
    c.blend((120, 80, 40), (noise(40, 1, 57) > .8) * .6)
    x, y = grid()
    c.blend((128, 30, 50), np.clip((y - .82) * 8, 0, 1) * .7)                                # wine-stained end


def cell_burlap(c):
    x, y = grid()
    w = (np.sin(x * math.pi * 64) * np.sin(y * math.pi * 64))
    c.a = lerp((206, 172, 120), (158, 124, 78), np.clip(.5 + .5 * w, 0, 1) * .6 + noise(6, 3, 58) * .4)
    c.blend((120, 90, 56), (np.abs(np.sin(y * math.pi * 64)) < .15) * .2)
    m = mask_from(lambda d: (d.rounded_rectangle([P(.3, .3), P(.7, .7)], .04 * S, outline=255, width=7),
                             d.ellipse([P(.42, .4), P(.58, .56)], outline=255, width=6)), 1)        # stencilled wheat-sheaf ring
    c.blend((29, 43, 79), m * .55)


# ------------------------------------------------------------------------------------------------ fruit
def cell_orange_cut(c):
    citrus_cut(c, (240, 140, 30), (252, 236, 200), (248, 150, 40), 11, 60)


def cell_lime_cut(c):
    citrus_cut(c, (70, 150, 50), (232, 246, 206), (176, 218, 96), 10, 61)


def cell_kiwi_cut(c):
    x, y = grid()
    r = np.hypot(x - .5, y - .5) * 2
    ang = np.arctan2(y - .5, x - .5)
    c.a = lerp((120, 186, 50), (160, 212, 80), np.clip(r, 0, 1))
    c.blend((240, 246, 220), (r < .32) * 1.0)
    c.blend((246, 250, 230), (np.abs(np.sin(ang * 18)) < .05) * (r < .85) * .6)
    seeds = (np.abs(r - .42) < .05) & (np.abs(np.sin(ang * 16)) > .7)
    c.blend((30, 24, 20), seeds * 1.0)
    c.blend((130, 96, 56), (r > .92) * 1.0)


def cell_melon_cut(c):
    """Watermelon cut face: v up = the rind (bottom of the cell) to the flesh tip (top)."""
    x, y = grid()
    c.a = lerp((236, 70, 80), (220, 46, 60), noise(10, 2, 62))
    c.blend((250, 210, 210), (noise(40, 1, 63) > .8) * .25)
    c.blend((248, 246, 220), ((y > .82) & (y < .88)) * 1.0)
    c.blend((60, 130, 50), (y >= .88) * 1.0)
    rr = random.Random(64)
    im, d = c.draw()
    for _ in range(14):
        u, v = rr.uniform(.1, .9), rr.uniform(.25, .7)
        d.ellipse([P(u - .012, v - .02), P(u + .012, v + .02)], fill=(30, 22, 20))
    c.put(im)


def cell_strawberry(c):
    x, y = grid()
    c.a = lerp((232, 40, 50), (190, 20, 36), noise(5, 2, 65))
    c.blend((255, 170, 170), np.clip((y - .55) * -3, 0, 1) * 0)
    seeds = (np.sin(x * math.pi * 16 + np.floor(y * 12) * 1.57) * np.sin(y * math.pi * 12)) > .85
    c.blend((246, 214, 90), seeds * 1.0)


def cell_pineapple(c):
    x, y = grid()
    a = np.abs(np.sin((x * 1.0 + y * .9) * math.pi * 7)) < .14
    b = np.abs(np.sin((x * 1.0 - y * .9) * math.pi * 7)) < .14
    c.a = lerp((214, 160, 52), (170, 112, 30), noise(8, 2, 66))
    c.blend((112, 76, 24), ndimage.gaussian_filter((a | b).astype(float), 1) * .8)
    c.blend((120, 150, 60), (noise(30, 1, 67) > .82) * .35)


def cell_apple(c):
    x, y = grid()
    c.a = lerp((214, 44, 42), (150, 22, 30), noise(4, 3, 68))
    streak = np.clip(np.sin(x * math.pi * 18 + noise(3, 2, 69) * 4) * .5 + .5, 0, 1) * np.clip(y * 1.6 - .5, 0, 1)
    c.blend((236, 170, 70), streak * .45)
    c.blend((250, 220, 180), (noise(50, 1, 70) > .9) * .3)
    c.blend((255, 255, 255), np.clip(1 - np.hypot(x - .35, y - .4) * 6, 0, 1) * .3)


def cell_melon_skin(c):
    x, y = grid()
    s = np.sin(x * math.pi * 12 + np.sin(y * 9) * .8)
    c.a = lerp((70, 140, 60), (30, 84, 36), np.clip(.5 + .5 * s, 0, 1))
    c.shade(noise(6, 2, 71), .2)


# ------------------------------------------------------------------------------------------------ chalkboards and leaf
def chalkboard(c, icons):
    """Slate menu: a wood-free chalk surface with 3 pictogram rows and dotted price lines (no digits or words)."""
    c.a = lerp((48, 58, 54), (34, 40, 38), noise(6, 3, 72))
    c.blend((90, 100, 96), (noise(30, 1, 73) > .78) * .25)
    im, d = c.draw()
    chalk = (236, 232, 220)
    d.rectangle([P(.05, .05), P(.95, .95)], outline=chalk, width=3)
    for k, ic in enumerate(icons):
        v = .2 + k * .28
        ic(d, .2, v, chalk)
        for j in range(7):
            d.ellipse([P(.38 + j * .055, v + .02), P(.395 + j * .055, v + .035)], fill=chalk)
        d.rounded_rectangle([P(.8, v - .03), P(.9, v + .06)], 6, outline=(242, 194, 63), width=3)
    c.put(im)


def _bread(d, u, v, col):
    d.ellipse([P(u - .1, v - .05), P(u + .1, v + .06)], outline=col, width=4)
    for k in range(3):
        d.line([P(u - .05 + k * .05, v - .03), P(u - .02 + k * .05, v + .03)], fill=col, width=3)


def _croissant(d, u, v, col):
    d.arc([P(u - .1, v - .07), P(u + .1, v + .1)], 200, 340, fill=col, width=8)


def _cake(d, u, v, col):
    d.rectangle([P(u - .08, v - .03), P(u + .08, v + .07)], outline=col, width=4)
    d.ellipse([P(u - .015, v - .09), P(u + .015, v - .05)], fill=(232, 80, 91))


def _cow(d, u, v, col):
    d.ellipse([P(u - .07, v - .05), P(u + .07, v + .07)], outline=col, width=4)
    d.line([P(u - .07, v - .04), P(u - .11, v - .08)], fill=col, width=4)
    d.line([P(u + .07, v - .04), P(u + .11, v - .08)], fill=col, width=4)


def _pig(d, u, v, col):
    d.ellipse([P(u - .07, v - .06), P(u + .07, v + .07)], outline=col, width=4)
    d.ellipse([P(u - .03, v), P(u + .03, v + .04)], outline=(244, 166, 193), width=3)


def _drum(d, u, v, col):
    d.ellipse([P(u - .07, v - .06), P(u + .03, v + .05)], outline=col, width=4)
    d.line([P(u + .02, v + .03), P(u + .09, v + .08)], fill=col, width=5)


def _wedge(d, u, v, col):
    d.polygon([P(u - .09, v + .06), P(u + .09, v + .06), P(u + .09, v - .04)], outline=col)
    d.line([P(u - .09, v + .06), P(u + .09, v - .04)], fill=col, width=4)
    d.line([P(u - .09, v + .06), P(u + .09, v + .06)], fill=col, width=4)
    d.ellipse([P(u + .02, v + .01), P(u + .05, v + .04)], fill=(242, 194, 63))


def _wheel(d, u, v, col):
    d.ellipse([P(u - .09, v - .05), P(u + .09, v + .07)], outline=col, width=4)
    d.arc([P(u - .09, v - .07), P(u + .09, v + .03)], 180, 360, fill=col, width=4)


def _goat(d, u, v, col):
    d.ellipse([P(u - .05, v - .04), P(u + .05, v + .08)], outline=col, width=4)
    d.arc([P(u - .08, v - .1), P(u - .01, v - .02)], 180, 300, fill=col, width=3)
    d.arc([P(u + .01, v - .1), P(u + .08, v - .02)], 240, 360, fill=col, width=3)


def _fish(d, u, v, col):
    d.ellipse([P(u - .09, v - .04), P(u + .05, v + .05)], outline=col, width=4)
    d.polygon([P(u + .04, v), P(u + .1, v - .05), P(u + .1, v + .05)], outline=col)
    d.ellipse([P(u - .06, v - .015), P(u - .04, v + .005)], fill=col)


def _shrimp(d, u, v, col):
    d.arc([P(u - .08, v - .07), P(u + .08, v + .08)], 30, 260, fill=(250, 150, 120), width=7)


def _crab(d, u, v, col):
    d.ellipse([P(u - .06, v - .03), P(u + .06, v + .05)], outline=col, width=4)
    for s in (-1, 1):
        d.arc([P(u + s * .06 - .04, v - .09), P(u + s * .06 + .04, v - .01)], 0, 360, fill=col, width=3)


def _cone(d, u, v, col):
    d.polygon([P(u - .05, v - .01), P(u + .05, v - .01), P(u, v + .1)], outline=(226, 170, 96))
    d.ellipse([P(u - .055, v - .09), P(u + .055, v + .01)], fill=(244, 166, 193))


def _cup(d, u, v, col):
    d.polygon([P(u - .07, v - .01), P(u + .07, v - .01), P(u + .05, v + .08), P(u - .05, v + .08)], outline=col)
    d.ellipse([P(u - .06, v - .07), P(u + .0, v - .0)], fill=(162, 214, 140))
    d.ellipse([P(u - .0, v - .07), P(u + .06, v - .0)], fill=(122, 74, 46))


def _pop(d, u, v, col):
    d.rounded_rectangle([P(u - .04, v - .08), P(u + .04, v + .05)], 8, fill=(242, 140, 40))
    d.line([P(u, v + .05), P(u, v + .1)], fill=(214, 170, 112), width=5)


def _bottle(d, u, v, col):
    d.rounded_rectangle([P(u - .03, v - .03), P(u + .03, v + .09)], 4, outline=col, width=4)
    d.rectangle([P(u - .012, v - .1), P(u + .012, v - .03)], outline=col, width=3)


def _wglass(d, u, v, col):
    d.polygon([P(u - .05, v - .08), P(u + .05, v - .08), P(u + .03, v + .01), P(u - .03, v + .01)], fill=(150, 30, 50))
    d.line([P(u, v + .01), P(u, v + .08)], fill=col, width=4)


def _grapes(d, u, v, col):
    for k, (a, b) in enumerate([(-.04, -.04), (0, -.04), (.04, -.04), (-.02, .01), (.02, .01), (0, .06)]):
        d.ellipse([P(u + a - .025, v + b - .025), P(u + a + .025, v + b + .025)], fill=(160, 80, 150))


def _orange(d, u, v, col):
    d.ellipse([P(u - .07, v - .06), P(u + .07, v + .08)], outline=(242, 140, 40), width=5)
    d.polygon([P(u, v - .07), P(u + .06, v - .11), P(u + .04, v - .05)], fill=(95, 181, 72))


def _juice(d, u, v, col):
    d.polygon([P(u - .05, v - .06), P(u + .05, v - .06), P(u + .04, v + .08), P(u - .04, v + .08)], outline=col)
    d.rectangle([P(u - .04, v - .02), P(u + .04, v + .07)], fill=(242, 140, 40))
    d.line([P(u + .01, v - .06), P(u + .05, v - .12)], fill=(232, 80, 91), width=3)


def _blender(d, u, v, col):
    d.polygon([P(u - .05, v - .08), P(u + .05, v - .08), P(u + .03, v + .04), P(u - .03, v + .04)], outline=col)
    d.rectangle([P(u - .05, v + .04), P(u + .05, v + .09)], fill=col)


def cell_leaf(c):
    c.a[:] = (60, 130, 50)
    im, d = c.draw()
    d.polygon([P(.5, .02), P(.82, .3), P(.78, .7), P(.5, .98), P(.22, .7), P(.18, .3)], fill=(92, 168, 66))
    d.line([P(.5, .04), P(.5, .96)], fill=(170, 210, 120), width=5)
    for k in range(5):
        v = .2 + k * .15
        d.line([P(.5, v + .06), P(.25, v - .04)], fill=(150, 200, 110), width=3)
        d.line([P(.5, v + .06), P(.75, v - .04)], fill=(150, 200, 110), width=3)
    c.put(im)


PAINT = {
    "loaf": cell_loaf, "boule": cell_boule, "baguette": cell_baguette, "croissant": cell_croissant, "roll": cell_roll,
    "cake_choc": lambda c: cell_cake(c, (110, 64, 40), (90, 48, 30), (232, 80, 91)),
    "cake_straw": lambda c: cell_cake(c, (246, 226, 190), (244, 166, 193), (232, 60, 70)),
    "cake_cream": lambda c: cell_cake(c, (244, 214, 150), (250, 244, 228), (211, 165, 61)),
    "steak": cell_steak, "tbone": cell_tbone, "ribs": cell_ribs, "chop": cell_chop, "sausage": cell_sausage,
    "chicken": cell_chicken, "ham": cell_ham, "salami": cell_salami,
    "rind_wax": cell_rind_wax, "rind_natural": cell_rind_natural, "cheese_cut": cell_cheese_cut, "blue_cut": cell_blue_cut,
    "provolone": cell_provolone, "brie": cell_brie, "parmesan": cell_parmesan, "ground": cell_ground,
    "fish_blue": cell_fish_blue, "fish_red": cell_fish_red, "salmon": cell_salmon, "shrimp": cell_shrimp,
    "lobster": cell_lobster, "squid": cell_squid, "lemon_cut": cell_lemon_cut, "ice": cell_ice,
    "gelato_pistachio": lambda c: gelato(c, (176, 206, 120), (150, 186, 96), 80, 30, (120, 150, 70)),
    "gelato_choc": lambda c: gelato(c, (118, 70, 46), (86, 48, 30), 81, 24, (60, 34, 22)),
    "gelato_straw": lambda c: gelato(c, (246, 170, 186), (232, 136, 160), 82, 20, (200, 40, 60)),
    "gelato_cream": lambda c: gelato(c, (250, 240, 212), (238, 222, 186), 83, 0, None, (120, 74, 46)),
    "gelato_mint": lambda c: gelato(c, (186, 232, 210), (160, 216, 190), 84, 60, (60, 36, 26)),
    "gelato_mango": lambda c: gelato(c, (250, 190, 70), (240, 160, 40), 85, 10, (250, 220, 120)),
    "gelato_berry": lambda c: gelato(c, (150, 90, 160), (120, 64, 136), 86, 16, (80, 40, 100), (240, 220, 240)),
    "sprinkles": cell_sprinkles,
    "waffle": cell_waffle,
    "wl_grape": lambda c: wine_label(c, ico_grape), "wl_glass": lambda c: wine_label(c, ico_glass, (29, 43, 79), (244, 235, 216)),
    "bottle_wall": lambda c: cell_bottle_wall(c), "wl_leaf": lambda c: wine_label(c, ico_leaf, (250, 248, 240), (46, 74, 125)),
    "wl_star": lambda c: wine_label(c, ico_star, (29, 43, 79), (244, 235, 216)),
    "cork": cell_cork, "burlap": cell_burlap,
    "orange_cut": cell_orange_cut, "lime_cut": cell_lime_cut, "kiwi_cut": cell_kiwi_cut, "melon_cut": cell_melon_cut,
    "strawberry": cell_strawberry, "pineapple": cell_pineapple, "apple": cell_apple, "melon_skin": cell_melon_skin,
    "chalk_bread": lambda c: chalkboard(c, [_bread, _croissant, _cake]),
    "chalk_meat": lambda c: chalkboard(c, [_cow, _pig, _drum]),
    "chalk_cheese": lambda c: chalkboard(c, [_wedge, _wheel, _goat]),
    "chalk_fish": lambda c: chalkboard(c, [_fish, _shrimp, _crab]),
    "chalk_ice": lambda c: chalkboard(c, [_cone, _cup, _pop]),
    "chalk_wine": lambda c: chalkboard(c, [_bottle, _wglass, _grapes]),
    "chalk_juice": lambda c: chalkboard(c, [_orange, _juice, _blender]),
    "leaf": cell_leaf,
}


def build(out):
    atlas = Image.new("RGB", (S * N, S * N), (128, 128, 128))
    for name, (c, r) in INDEX.items():
        cell = Cell(name)
        PAINT[name](cell)
        atlas.paste(cell.img(), (c * S, r * S))
    atlas.save(out, optimize=True)
    return out


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else "FT_Sector_albedo.png"))
