"""Painted, seamless 512px textures for the detailed sector counters (1 texture tile = 1 metre, metric UVs).

Output: IK_<Name>_albedo.png, same hand-painted look as the existing Interior Kit textures (soft grout shadows,
warm colour variation, light baked in because the Soft Painted shader has no normal maps).
"""
import os
import sys
import numpy as np
from PIL import Image

N = 512
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def noise(scale, seed=0, n=N):
    """Periodic smooth noise in 0..1; scale = feature size in pixels."""
    r = np.random.default_rng(seed)
    w = r.standard_normal((n, n))
    fx = np.fft.fftfreq(n)[:, None]; fy = np.fft.fftfreq(n)[None, :]
    g = np.exp(-(fx ** 2 + fy ** 2) * (scale ** 2) * 2 * np.pi ** 2)
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
    out -= out.min(); out /= max(out.max(), 1e-9)
    return out


def fbm(seed, scales=(64, 24, 8, 3), weights=(.5, .28, .15, .07)):
    return sum(w * noise(s, seed + i) for i, (s, w) in enumerate(zip(scales, weights)))


def hexc(h):
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255


def lerp(a, b, t):
    t = t[..., None] if np.ndim(t) == 2 else t
    return a + (b - a) * t


def save(name, img):
    img = np.clip(img, 0, 1)
    Image.fromarray((img * 255 + .5).astype(np.uint8)).save(os.path.join(OUT, "IK_%s_albedo.png" % name))


Y, X = np.mgrid[0:N, 0:N].astype(float)
# NB: PNG row 0 is the top of the texture (v = 1). Features are symmetric enough that it does not matter.


def bevel_mask(d, width):
    """d: distance to the joint in px -> 0 at joint .. 1 inside."""
    return np.clip(d / width, 0, 1)


def bricks(name, rows, cols, base, alt, mortar, seed, jitter=.08, soot=0):
    img = np.zeros((N, N, 3))
    rh = N / rows; cw = N / cols
    row = np.floor(Y / rh).astype(int)
    off = (row % 2) * cw / 2
    col = np.floor(((X + off) % N) / cw).astype(int)
    r = np.random.default_rng(seed)
    tone = r.random((rows, cols + 1))
    t = tone[row % rows, col % (cols + 1)]
    colr = lerp(hexc(base), hexc(alt), t)
    colr *= (1 - jitter + 2 * jitter * r.random((rows, cols + 1))[row % rows, col % (cols + 1)])[..., None]
    grain = fbm(seed + 3, (10, 4, 1.5), (.4, .35, .25))
    colr *= (.85 + .3 * grain)[..., None]
    dy = np.minimum(Y % rh, rh - Y % rh)
    dx = np.minimum((X + off) % cw, cw - (X + off) % cw)
    d = np.minimum(dx, dy)
    m = bevel_mask(d - 2.2, 3.5)
    # Light from the top-left: the lower/right edge of each brick is a bit darker.
    shade = 1 - .12 * np.clip(1 - (rh - Y % rh) / 5, 0, 1) + .08 * np.clip(1 - (Y % rh) / 4, 0, 1)
    colr *= shade[..., None]
    mort = hexc(mortar) * (.9 + .15 * fbm(seed + 9, (6, 2), (.6, .4)))[..., None]
    img = lerp(mort, colr, m)
    if soot:
        s = fbm(seed + 20, (90, 30), (.7, .3))
        img *= (1 - soot * np.clip(s - .45, 0, 1) * 2)[..., None]
    return img


def tiles(name, rows, cols, colors, grout, seed, gloss=True, gap=2.0, edge=4.0, weights=None):
    rh = N / rows; cw = N / cols
    row = np.floor(Y / rh).astype(int); col = np.floor(X / cw).astype(int)
    r = np.random.default_rng(seed)
    pick = r.choice(len(colors), size=(rows, cols), p=weights)
    pal = np.array([hexc(c) for c in colors])
    colr = pal[pick[row, col]]
    colr = colr * (.94 + .1 * r.random((rows, cols)))[row, col][..., None]
    colr *= (.95 + .08 * fbm(seed + 1, (20, 5), (.6, .4)))[..., None]
    dy = np.minimum(Y % rh, rh - Y % rh); dx = np.minimum(X % cw, cw - X % cw)
    d = np.minimum(dx, dy)
    m = bevel_mask(d - gap, edge)
    if gloss:
        # soft highlight towards the top-left of each tile
        u = (X % cw) / cw; v = (Y % rh) / rh
        hl = np.clip(1 - np.hypot(u - .3, v - .28) * 2.2, 0, 1) ** 2 * .12
        colr = colr + hl[..., None]
        colr *= (1 - .1 * np.clip(1 - (rh - Y % rh) / edge / 1.5, 0, 1))[..., None]
    g = hexc(grout) * (.9 + .15 * fbm(seed + 5, (4, 2), (.5, .5)))[..., None]
    return lerp(g, colr, m)


# ---------------------------------------------------------------------------------------------- 1 brick (oven)
save("Brick", bricks("Brick", 12, 4, "B5563A", "D0784A", "E6D6BE", 11, soot=.35))

# ---------------------------------------------------------------------------------------------- 2 red/white checker tiles
def checker():
    rows = cols = 10
    rh = N / rows
    row = np.floor(Y / rh).astype(int); col = np.floor(X / rh).astype(int)
    red = (row + col) % 2 == 0
    img = tiles("x", rows, cols, ["FBF7EF"], "C9BFB0", 21)
    img2 = tiles("x", rows, cols, ["C8352D", "D2443A", "B83029"], "C9BFB0", 22)
    return np.where(red[..., None], img2, img)
save("Checker", checker())

# ---------------------------------------------------------------------------------------------- 3 white square tiles (butcher/fish walls)
save("TileSquare", tiles("TileSquare", 7, 7, ["FBFAF6", "F4F2EC", "EEF1F2"], "BFC6C8", 31, weights=[.5, .3, .2]))

# ---------------------------------------------------------------------------------------------- 4 blue mosaic (fish market)
save("TileBlue", tiles("TileBlue", 16, 16, ["2E86DE", "3D9BE8", "6CC4E8", "1F6FB8", "A9E0F5", "FBFAF6"], "E6EEF0", 41,
                       gap=1.3, edge=2.5, weights=[.26, .22, .18, .14, .1, .1]))

# ---------------------------------------------------------------------------------------------- 5 dark walnut planks (cheese shop)
def planks(base, light, dark, seed, rows=6, swirl=1.0):
    rh = N / rows
    row = np.floor(Y / rh).astype(int)
    r = np.random.default_rng(seed)
    shift = r.random(rows)[row] * N
    ends = r.random((rows, 2))
    # grain: stretched noise along X
    g1 = np.zeros((N, N))
    for k, (sx, sy, w) in enumerate(((140, 6, .55), (60, 2.5, .3), (20, 1.2, .15))):
        rr = np.random.default_rng(seed + k)
        w0 = rr.standard_normal((N, N))
        fx = np.fft.fftfreq(N)[:, None]; fy = np.fft.fftfreq(N)[None, :]
        gg = np.exp(-((fx * sy) ** 2 + (fy * sx) ** 2) * 2 * np.pi ** 2)
        o = np.real(np.fft.ifft2(np.fft.fft2(w0) * gg)); o = (o - o.min()) / (o.max() - o.min())
        g1 += w * o
    warp = noise(40, seed + 9) * 30 * swirl
    rings = .5 + .5 * np.sin((g1 * 14 + warp / 10) * np.pi)
    t = np.clip(rings * .75 + (g1 - .5) * 1.2 + .1, 0, 1)
    col = lerp(hexc(dark), hexc(light), t)
    col = lerp(col, hexc(base), .15)
    col *= (.9 + .2 * r.random(rows))[row][..., None]
    xs = (X + shift) % N
    # plank ends at two random points per row
    end = np.minimum(np.abs(xs - ends[row, 0] * N), np.abs(xs - ends[row, 1] * N))
    joint = np.minimum(np.minimum(Y % rh, rh - Y % rh), end)
    m = bevel_mask(joint - 1.2, 2.5)
    col *= (1 - .15 * np.clip(1 - (rh - Y % rh) / 4, 0, 1))[..., None]
    return lerp(hexc(dark) * .6, col, m)
save("WoodDark", planks("7A4A2C", "A06A3E", "4A2C1A", 51))

# ---------------------------------------------------------------------------------------------- 6 butcher block (end grain)
def butcher():
    rows, cols = 8, 5
    rh = N / rows; cw = N / cols
    row = np.floor(Y / rh).astype(int)
    off = (row % 2) * cw / 2
    col = np.floor(((X + off) % N) / cw).astype(int)
    r = np.random.default_rng(61)
    cx = (col + .3 + .4 * r.random((rows, cols + 1))[row, col]) * cw - off
    cy = (row + .2 + .6 * r.random((rows, cols + 1))[row, col]) * rh + r.choice([-1, 1], (rows, cols + 1))[row, col] * rh * .9
    dist = np.hypot(X - cx, Y - cy)
    ring = .5 + .5 * np.sin(dist / 2.6 + noise(12, 62) * 5)
    tone = r.random((rows, cols + 1))[row, col]
    colr = lerp(lerp(hexc("C98A4B"), hexc("E0B57A"), tone), lerp(hexc("A86A34"), hexc("C98A4B"), tone), ring * .8)
    colr *= (.9 + .15 * fbm(63, (6, 2), (.5, .5)))[..., None]
    knife = np.zeros((N, N))
    for k in range(60):  # knife scores
        a = r.random() * np.pi; x0, y0 = r.random(2) * N; L = 20 + r.random() * 60
        t = (X - x0) * np.cos(a) + (Y - y0) * np.sin(a); s = -(X - x0) * np.sin(a) + (Y - y0) * np.cos(a)
        knife = np.maximum(knife, (np.abs(s) < .7) * (np.abs(t) < L) * (.4 + .6 * r.random()))
    colr *= (1 - .18 * knife)[..., None]
    dy = np.minimum(Y % rh, rh - Y % rh); dx = np.minimum((X + off) % cw, cw - (X + off) % cw)
    m = bevel_mask(np.minimum(dx, dy) - .6, 1.6)
    return lerp(hexc("7A4A22"), colr, m)
save("ButcherBlock", butcher())

# ---------------------------------------------------------------------------------------------- 7 meat (marbled)
def meat():
    base = fbm(71, (30, 10, 3), (.5, .3, .2))
    col = lerp(hexc("8E1F22"), hexc("C7403B"), base)
    v = np.abs(np.sin((noise(25, 72) * 9 + noise(8, 73) * 2.5) * np.pi))
    fat = np.clip((.06 - v) / .06, 0, 1) ** .7
    v2 = np.abs(np.sin((noise(14, 74) * 12) * np.pi)); fat2 = np.clip((.06 - v2) / .06, 0, 1) * .7
    f = np.maximum(fat, fat2)
    col = lerp(col, hexc("F6E6DA"), f)
    col *= (.92 + .12 * noise(3, 75))[..., None]
    return col
save("Meat", meat())

# ---------------------------------------------------------------------------------------------- 8 cheese (eyes + speckles)
def cheese():
    col = lerp(hexc("F2C94A"), hexc("F7D96E"), fbm(81, (40, 12), (.6, .4)))
    r = np.random.default_rng(82)
    out = col.copy()
    for k in range(70):
        x0, y0 = r.random(2) * N; rad = 3 + r.random() ** 2 * 12
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                d = np.hypot(X - x0 - ox, Y - y0 - oy)
                hole = np.clip((rad - d) / 1.5, 0, 1)
                inner = np.clip((d - (rad * .2)) / rad, 0, 1)  # darker bottom-right inside the eye
                shade = .72 + .2 * np.clip(((X - x0 - ox) + (Y - y0 - oy)) / (rad + 1e-6), -1, 1)
                out = lerp(out, col * shade[..., None] * .92, hole * .9)
    out *= (.95 + .07 * noise(2, 83))[..., None]
    return out
save("Cheese", cheese())

# ---------------------------------------------------------------------------------------------- 9 cheese rind (aged, darker orange with mould dots)
def rind():
    col = lerp(hexc("C98A2E"), hexc("E3A948"), fbm(91, (30, 8, 2), (.5, .3, .2)))
    spots = np.clip((noise(3, 92) - .72) * 6, 0, 1)
    col = lerp(col, hexc("F4EFE4"), spots * .6)
    cracks = np.clip((.015 - np.abs(noise(30, 93) - .5)) / .015, 0, 1)
    col *= (1 - .15 * cracks)[..., None]
    return col
save("Rind", rind())

# ---------------------------------------------------------------------------------------------- 10 fish scales
def scales():
    s = 12.0  # px per scale (~2.3 cm)
    row = np.floor(Y / (s * .6))
    xo = X + (row % 2) * s / 2
    cx = (np.floor(xo / s) + .5) * s - (row % 2) * s / 2
    cy = (row + 1) * s * .6
    d = np.hypot(X - cx, (Y - cy) * 1.1) / (s * .62)
    edge = np.clip((d - .78) / .22, 0, 1)
    body = lerp(hexc("9DB4C4"), hexc("D8E4EC"), fbm(101, (60, 20), (.7, .3)))
    iri = .5 + .5 * np.sin(noise(40, 102) * 8)
    body = lerp(body, hexc("B8D0E8"), iri * .3)
    body *= (1.08 - .25 * d.clip(0, 1))[..., None]
    col = lerp(body, hexc("5A7488"), edge * .6)
    return col
save("FishScale", scales())

# ---------------------------------------------------------------------------------------------- 11 wicker basket weave
def wicker():
    s = 16.0
    u = (X / s) % 2; v = (Y / s) % 2
    cu = np.floor(X / s); cv = np.floor(Y / s)
    over = ((cu + cv) % 2 == 0)
    # horizontal strand: shade across v; vertical: shade across u
    fu = (X / s) % 1; fv = (Y / s) % 1
    hs = np.sin(fv * np.pi) ** .6; vs = np.sin(fu * np.pi) ** .6
    shade = np.where(over, hs, vs)
    base = lerp(hexc("B07A3E"), hexc("E0B06C"), fbm(111, (30, 6), (.6, .4)))
    col = base * (.55 + .5 * shade)[..., None]
    strands = .5 + .5 * np.sin(np.where(over, Y, X) * 1.4 + noise(4, 112) * 3)
    col *= (.92 + .1 * strands)[..., None]
    return col
save("Wicker", wicker())

# ---------------------------------------------------------------------------------------------- 12 chalkboard
def chalk():
    col = lerp(hexc("243129"), hexc("2F3E34"), fbm(121, (80, 20), (.7, .3)))
    smudge = np.clip(noise(50, 122) - .55, 0, 1) * .5
    col = lerp(col, hexc("6E7E74"), smudge)
    col *= (.96 + .06 * noise(2, 123))[..., None]
    return col
save("Chalk", chalk())

# ---------------------------------------------------------------------------------------------- 13 bread crust (golden, flour dust)
def crust():
    col = lerp(hexc("A8612A"), hexc("D9A04E"), fbm(131, (26, 8, 2), (.5, .3, .2)))
    flour = np.clip((noise(3, 132) - .6) * 4, 0, 1) * np.clip(noise(40, 133) * 1.6 - .5, 0, 1)
    col = lerp(col, hexc("F4EAD8"), flour * .8)
    cracks = np.clip((.012 - np.abs(noise(16, 134) - .5)) / .012, 0, 1)
    col *= (1 - .2 * cracks)[..., None]
    return col
save("Crust", crust())

# ---------------------------------------------------------------------------------------------- 14 cream plaster wall
def plaster():
    col = lerp(hexc("EFE3CC"), hexc("F8F0DF"), fbm(141, (70, 20, 4), (.5, .3, .2)))
    return col
save("Plaster", plaster())

# ---------------------------------------------------------------------------------------------- 15 rope (braided, for nets and cheese)
def rope():
    s = 10.0
    t = ((X + Y) / s) % 1
    shade = np.sin(t * np.pi) ** .7
    base = lerp(hexc("C9A46A"), hexc("E6CB94"), noise(20, 151))
    return base * (.6 + .45 * shade)[..., None]
save("Rope", rope())

print("ok", sorted(os.listdir(OUT)))

# ============================================================================================== staff assets
def knit(base, dark, light, seed, scale=6.0):
    # fine knit: small vertical V rows
    v = (np.sin(X / scale * np.pi) ** 2) * .5 + (np.sin((Y + (np.floor(X / scale) % 2) * scale * .5) / (scale * .8) * np.pi) ** 2) * .5
    col = lerp(hexc(dark), hexc(light), v)
    col = lerp(col, hexc(base), .55)
    col *= (.93 + .1 * fbm(seed, (40, 10), (.6, .4)))[..., None]
    return col
save("Polo", knit("1D2B4F", "15203B", "2C3F6B", 161))
save("Scrubs", knit("1F9A8E", "147368", "36B5A7", 162, 5.0))

def twill(base, dark, light, seed):
    t = ((X + Y) / 5.0) % 1
    shade = np.sin(t * np.pi) ** 1.5
    col = lerp(hexc(dark), hexc(light), shade)
    col = lerp(col, hexc(base), .5)
    col *= (.92 + .12 * fbm(seed, (50, 12), (.6, .4)))[..., None]
    return col
save("Khaki", twill("8A7A5A", "6E6046", "A89773", 171))
save("Jeans", twill("33496E", "243757", "4A6394", 172))

def cardboard():
    col = lerp(hexc("C08A4E"), hexc("D6A466"), fbm(181, (60, 14, 3), (.5, .3, .2)))
    flutes = .5 + .5 * np.sin(Y / 3.0 * np.pi)
    col *= (.94 + .06 * flutes)[..., None]
    # packing tape band across the middle and printed arrows / stamps
    tape = (np.abs(X - N / 2) < 38)
    col = np.where(tape[..., None], lerp(col, hexc("E8C98A"), .55) * 1.03, col)
    ink = np.zeros((N, N))
    for cx, cy in ((110, 120), (400, 380)):
        ink = np.maximum(ink, ((np.abs(X - cx) < 10) & (Y > cy - 40) & (Y < cy + 30)).astype(float))
        ink = np.maximum(ink, ((np.abs(Y - (cy - 40) - (np.abs(X - cx))) < 5) & (np.abs(X - cx) < 26)).astype(float))
    stamp = (np.abs(np.hypot(X - 380, Y - 110) - 45) < 4).astype(float)
    ink = np.maximum(ink, stamp * .8)
    col = lerp(col, hexc("5B3A1E"), ink * .75)
    return col
save("Cardboard", cardboard())

def styro():
    col = lerp(hexc("EEF2F2"), hexc("FFFFFF"), fbm(191, (8, 3), (.5, .5)))
    beads = np.clip((noise(2.5, 192) - .55) * 5, 0, 1)
    col *= (1 - .07 * beads)[..., None]
    return col
save("Styrofoam", styro())

def rolldoor():
    rows = 26
    rh = N / rows
    v = (Y % rh) / rh
    profile = np.where(v < .5, .82 + .3 * np.sin(v * np.pi * 2) ** 2, .74 + .2 * np.sin(v * np.pi))
    col = lerp(hexc("7F95A3"), hexc("A9BCC6"), fbm(201, (80, 20), (.6, .4)))
    col *= profile[..., None]
    rust = np.clip((fbm(202, (30, 8, 2), (.5, .3, .2)) - .66) * 5, 0, 1)
    col = lerp(col, hexc("8A5A3A"), rust * .45)
    grime = np.clip(1 - Y / N * 1.2, 0, 1) * 0 + np.clip((Y / N - .8) * 3, 0, 1)
    col *= (1 - .18 * grime)[..., None]
    return col
save("RollDoor", rolldoor())

def pavers():
    rows, cols = 8, 4
    rh = N / rows; cw = N / cols
    row = np.floor(Y / rh).astype(int)
    off = (row % 2) * cw / 2
    r = np.random.default_rng(211)
    tone = r.random((rows, cols + 1))[row, (np.floor(((X + off) % N) / cw)).astype(int)]
    col = lerp(hexc("B9B3A6"), hexc("D2CCBE"), tone)
    col *= (.9 + .15 * fbm(212, (20, 5, 2), (.5, .3, .2)))[..., None]
    dy = np.minimum(Y % rh, rh - Y % rh); dx = np.minimum((X + off) % cw, cw - (X + off) % cw)
    m = bevel_mask(np.minimum(dx, dy) - 1.5, 3)
    return lerp(hexc("6F6A60"), col, m)
save("Paver", pavers())

def hazard():
    t = ((X + Y) / 64.0) % 1
    col = np.where((t < .5)[..., None], hexc("F2C23F"), hexc("2A2A2A"))
    col = col * (.9 + .12 * fbm(221, (30, 6), (.6, .4)))[..., None]
    wear = np.clip((noise(10, 222) - .7) * 4, 0, 1)
    return lerp(col, hexc("8C8578"), wear * .5)
save("Hazard", hazard())

def diamond():
    s = 22.0
    u = (X / s) % 1; v = (Y / s) % 1
    lug = np.clip(1 - np.abs((u - .5) + (v - .5) * 1.0) * 6 - np.abs((u - .5) - (v - .5)) * 1.6, 0, 1)
    lug2 = np.clip(1 - np.abs(((u + .5) % 1 - .5) - ((v + .5) % 1 - .5)) * 6 - np.abs(((u + .5) % 1 - .5) + ((v + .5) % 1 - .5)) * 1.6, 0, 1)
    base = lerp(hexc("8E969C"), hexc("B2BAC0"), fbm(231, (40, 8), (.6, .4)))
    return base * (.85 + .35 * np.maximum(lug, lug2))[..., None]
save("Diamond", diamond())

def skin(base, seed):
    col = lerp(hexc(base) * .94, hexc(base) * 1.04, fbm(seed, (40, 10, 3), (.5, .3, .2)))
    return col
save("SkinA", skin("B07A55", 241))
save("SkinB", skin("E2B08C", 242))

def hair(base, seed):
    g = np.zeros((N, N))
    for k, (sx, w) in enumerate(((2, .5), (5, .3), (12, .2))):
        rr = np.random.default_rng(seed + k)
        w0 = rr.standard_normal((N, N))
        fx = np.fft.fftfreq(N)[:, None]; fy = np.fft.fftfreq(N)[None, :]
        gg = np.exp(-((fx * 40) ** 2 + (fy * sx) ** 2) * 2 * np.pi ** 2)
        o = np.real(np.fft.ifft2(np.fft.fft2(w0) * gg)); o = (o - o.min()) / (o.max() - o.min())
        g += w * o
    return hexc(base) * (.7 + .6 * g)[..., None]
save("HairDark", hair("2A1D16", 251))
save("HairBrown", hair("5A3A22", 252))

# ---------------------------------------------------------------------------------------------- side sectors (sorvetes, bebidas, adega)
save("TilePink", bricks("TilePink", 16, 6, "F6CFDC", "F9E3EA", "FFFFFF", 311, jitter=.03))
save("TileMint", bricks("TileMint", 16, 6, "BFE8DA", "D6F1E7", "FFFFFF", 312, jitter=.03))

def terrazzo(base, chips, seed):
    img = lerp(hexc(base) * .97, hexc(base) * 1.03, fbm(seed, (30, 8), (.6, .4)))
    r = np.random.default_rng(seed)
    for c in chips:
        for _ in range(260):
            cx, cy, rad = r.random() * N, r.random() * N, 2 + r.random() * 5
            d = np.hypot(((X - cx + N / 2) % N) - N / 2, ((Y - cy + N / 2) % N) - N / 2)
            img = np.where((d < rad)[..., None], hexc(c) * (.9 + .2 * r.random()), img)
    return img
save("Terrazzo", terrazzo("F7EDE4", ["F4A6C1", "8FD3C0", "F2C23F", "7FB6E6"], 321))

def stone():
    rows = 7
    img = np.zeros((N, N, 3)); rh = N / rows
    r = np.random.default_rng(331)
    row = np.floor(Y / rh).astype(int)
    widths = [r.uniform(.6, 1.4) for _ in range(40)]
    out = np.zeros((N, N)); edge = np.full((N, N), 99.0); tone = np.zeros((N, N))
    for ri in range(rows):
        xs = [0.0]; k = ri * 5
        while xs[-1] < N: xs.append(xs[-1] + N / 4 * widths[(k + len(xs)) % 40])
        xs[-1] = N
        mask = row == ri
        for a, b in zip(xs[:-1], xs[1:]):
            m2 = mask & (X >= a) & (X < b)
            tone[m2] = r.random()
            dx = np.minimum(X - a, b - X); dy = np.minimum(Y - ri * rh, (ri + 1) * rh - Y)
            edge = np.where(m2, np.minimum(dx, dy), edge)
    col = lerp(hexc("A38C6E"), hexc("C9B695"), tone)
    col *= (.8 + .35 * fbm(333, (14, 5, 2), (.45, .35, .2)))[..., None]
    m = bevel_mask(edge - 3 - 3 * fbm(334, (6, 2), (.6, .4)), 5)
    return lerp(hexc("6B5B48"), col, m)
save("Stone", stone())

def cork():
    base = lerp(hexc("B9875A"), hexc("D2A676"), fbm(341, (6, 2, 1), (.4, .35, .25)))
    dots = noise(1.2, 342) > .72
    return np.where(dots[..., None], hexc("7A5134"), base)
save("Cork", cork())

def waffle():
    s = 32.0
    u = ((X + Y) / s) % 1; v = ((X - Y) / s) % 1
    ridge = np.clip(np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) * 6, 0, 1)
    base = lerp(hexc("C98A3D"), hexc("E8B266"), ridge)
    return base * (.9 + .15 * fbm(351, (10, 3), (.6, .4)))[..., None]
save("Waffle", waffle())

save("Terracotta", tiles("Terracotta", 5, 5, ["B8643C", "C4744A", "A95A36", "CF8458"], "D9CBB6", 361, gap=2.5, edge=5))

def staves():
    cw = N / 8
    col = np.floor(X / cw).astype(int)
    r = np.random.default_rng(371)
    tone = r.random(8)[col % 8]
    base = lerp(hexc("7A4A2A"), hexc("9C6238"), tone)
    grain = fbm(372, (3, 40), (.5, .5))
    base *= (.82 + .3 * grain)[..., None]
    d = np.minimum(X % cw, cw - X % cw)
    return base * (.55 + .45 * bevel_mask(d - 1, 3))[..., None]
save("Staves", staves())
