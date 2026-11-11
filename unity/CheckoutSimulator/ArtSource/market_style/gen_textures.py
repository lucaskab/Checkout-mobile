"""Procedural, painted-style tileable textures for "Estilo do mercado" (floors and walls).
Each texture: <Name>_albedo.png (RGBA, A = smoothness), <Name>_normal.png (RGB tangent normal),
and for tintable ones <Name>_mask.png (L, white = takes the player's colour; the albedo there is neutral grey).
Run: python3 gen_textures.py OUTDIR"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

N = 1024
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)

def hexc(h):
    h = h.lstrip("#"); return np.array([int(h[i:i+2], 16) / 255 for i in (0, 2, 4)], np.float32)

def tnoise(scale, seed, octaves=4):
    """Tileable value noise in [0,1] (periodic grid)."""
    r = np.random.default_rng(seed)
    out = np.zeros((N, N), np.float32); amp = 1; tot = 0
    for o in range(octaves):
        g = int(scale * 2 ** o)
        grid = r.random((g, g)).astype(np.float32)
        img = Image.fromarray((grid * 255).astype(np.uint8))
        # periodic upscale: tile 3x3, resize, crop center
        big = Image.new("L", (g * 3, g * 3))
        for i in range(3):
            for j in range(3): big.paste(img, (i * g, j * g))
        big = big.resize((N * 3, N * 3), Image.BICUBIC)
        out += np.asarray(big.crop((N, N, 2 * N, 2 * N)), np.float32) / 255 * amp
        tot += amp; amp *= .5
    return out / tot

def blur(a, r):
    """Periodic gaussian blur of a float map (FFT)."""
    if r <= 0: return a
    f = np.fft.fftfreq(N)
    g = np.exp(-2 * (math.pi * r) ** 2 * (f[:, None] ** 2 + f[None, :] ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g)).astype(np.float32)

def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return ((n * .5 + .5) * 255).clip(0, 255).astype(np.uint8)

def save(name, rgb, smooth, height, strength=6, mask=None):
    rgb = np.clip(rgb, 0, 1)
    a = np.clip(smooth, 0, 1)
    if np.ndim(a) == 0: a = np.full((N, N), a, np.float32)
    rgba = np.dstack([rgb, a[..., None]])
    Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(f"{OUT}/{name}_albedo.png", optimize=True)
    nm = normal_from_height(blur(height, .8), strength)
    Image.fromarray(nm, "RGB").resize((512, 512), Image.LANCZOS).save(f"{OUT}/{name}_normal.png", optimize=True)
    if mask is not None:
        Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), "L").resize((512, 512), Image.LANCZOS).save(f"{OUT}/{name}_mask.png", optimize=True)
    print("saved", name)

def lerp(a, b, t): return a + (b - a) * t
def col(c, shade): return np.asarray(c)[None, None, :] * shade[..., None]
def fill(c): return np.ones((N, N, 3), np.float32) * hexc(c)

def grid_tiles(nx, ny, grout, offset_rows=0.0):
    """Returns (tile id x, tile id y, distance to edge in px, row index) for a brick/tile grid."""
    tw, th = N / nx, N / ny
    row = np.floor(yy / th)
    xo = xx + (row % 2) * offset_rows * tw
    cx = np.floor(xo / tw) % nx
    lx = np.mod(xo, tw); ly = np.mod(yy, th)
    d = np.minimum(np.minimum(lx, tw - lx), np.minimum(ly, th - ly))
    return cx, row, d, (lx, ly, tw, th)

def edge_profile(d, grout, bevel):
    """Height: 0 in the grout, ramps up over `bevel` px."""
    return np.clip((d - grout) / max(bevel, 1), 0, 1)

def per_tile_rand(cx, cy, seed, n=1):
    r = np.random.default_rng(seed).random((256, 256, n)).astype(np.float32)
    return r[cx.astype(int) % 256, cy.astype(int) % 256]

# ------------------------------------------------------------------ FLOORS

def floor_madeira_clara():
    # 8 planks across (20 cm at 1.6 m tiling), plank ends staggered, light oak.
    nx = 8; pw = N / nx
    px = np.floor(xx / pw)
    offs = per_tile_rand(px, np.zeros_like(px), 11)[..., 0] * N
    ly = np.mod(yy + offs, N / 2)   # two boards per column per tile
    seg = np.floor(np.mod(yy + offs, N) / (N / 2))
    lx = np.mod(xx, pw)
    d = np.minimum(np.minimum(lx, pw - lx), np.minimum(ly, N / 2 - ly))
    h = edge_profile(d, 1.5, 4)
    tone = per_tile_rand(px, seg, 12)[..., 0]
    grain = tnoise(6, 3, 5)
    streak = np.sin((xx / pw * 2 * math.pi * 3) + grain * 9 + tone * 6) * .5 + .5
    base = lerp(hexc("D9B07A"), hexc("C99C66"), tone[..., None])
    shade = .9 + .12 * streak + .06 * (grain - .5)
    rgb = base * shade[..., None]
    rgb = lerp(rgb * .55, rgb, h[..., None])
    save("Floor_madeira-clara", rgb, .45 * h + .05, h * .6 + streak * .08)

def floor_taco():
    # Herringbone of 2×1 blocks: cells with (i-j) mod 4 in {0,1} belong to a horizontal block, {2,3} to a vertical one.
    C = 12; c = N / C
    gx = xx / c; gy = yy / c
    i = np.floor(gx); j = np.floor(gy); fx = gx - i; fy = gy - j
    m = np.mod(i - j, 4)
    horiz = m < 2
    # local coords inside the block (length 2 along its axis)
    lx = np.where(horiz, np.where(m == 0, fx, 1 + fx), fx)       # 0..2 along x for H, 0..1 for V
    ly = np.where(horiz, fy, np.where(m == 3, fy, 1 + fy))       # 0..1 for H, 0..2 along y for V
    W = np.where(horiz, 2, 1); H = np.where(horiz, 1, 2)
    d = np.minimum(np.minimum(lx, W - lx), np.minimum(ly, H - ly)) * c
    h = edge_profile(d, 1.2, 3)
    bi = np.where(horiz, np.where(m == 0, i, i - 1), i); bj = np.where(horiz, j, np.where(m == 3, j, j - 1))
    tone = per_tile_rand(np.mod(bi, C), np.mod(bj, C) + horiz * 64, 21)[..., 0]
    grain = tnoise(8, 5, 3)
    along = np.where(horiz, ly, lx)
    streak = np.sin(along * 9 + grain * 5 + tone * 10) * .5 + .5
    base = lerp(hexc("B0743F"), hexc("80502C"), tone[..., None])
    rgb = base * (.88 + .14 * streak + .05 * (grain - .5))[..., None]
    rgb = lerp(rgb * .5, rgb, h[..., None])
    save("Floor_taco", rgb, .5 * h + .05, h * .6 + streak * .06)

def floor_porcelanato():
    cx, cy, d, _ = grid_tiles(2, 2, 2)
    h = edge_profile(d, 2, 3)
    tone = per_tile_rand(cx, cy, 31)[..., 0]
    n = tnoise(10, 7, 5)
    base = lerp(hexc("B9BCBE"), hexc("A9ADB0"), tone[..., None]) * (.95 + .1 * n)[..., None]
    rgb = lerp(hexc("8C8F92") * np.ones_like(base), base, h[..., None])
    save("Floor_porcelanato", rgb, .85 * h + .1, h * .5)

def floor_xadrez():
    cx, cy, d, _ = grid_tiles(4, 4, 2)
    h = edge_profile(d, 1.5, 2.5)
    dark = ((cx + cy) % 2 == 1).astype(np.float32)
    n = tnoise(10, 8, 4)
    light = hexc("F1ECE2") * (.96 + .06 * n)[..., None]
    tintbase = hexc("C8C8C8") * (.95 + .08 * n)[..., None]  # tinted by the player's colour
    rgb = lerp(light, tintbase, dark[..., None])
    rgb = lerp(hexc("9A968E") * np.ones_like(rgb), rgb, h[..., None])
    save("Floor_xadrez", rgb, .7 * h + .1, h * .5, mask=dark * h)

def floor_cimento():
    n1 = tnoise(3, 9, 6); n2 = tnoise(14, 10, 3)
    cloud = blur(n1, 6)
    base = lerp(hexc("9FA3A3"), hexc("B9BBB8"), cloud[..., None]) * (.97 + .05 * n2)[..., None]
    # saw-cut joints at the tile edge (every 1.5 m when tiling 3 m: two per tile)
    d = np.minimum(np.minimum(np.mod(xx, N / 2), N / 2 - np.mod(xx, N / 2)), np.minimum(np.mod(yy, N / 2), N / 2 - np.mod(yy, N / 2)))
    h = edge_profile(d, 1, 2)
    rgb = lerp(base * .7, base, h[..., None])
    save("Floor_cimento", rgb, .55 + .25 * cloud, h * .4 + n2 * .05)

def floor_ladrilho():
    # 4×4 hydraulic tiles; each tile: a four-petal flower meeting its neighbours to make a bigger pattern.
    nt = 4; t = N / nt
    cx = np.floor(xx / t); cy = np.floor(yy / t)
    lx = np.mod(xx, t) / t; ly = np.mod(yy, t) / t
    d = np.minimum(np.minimum(lx, 1 - lx), np.minimum(ly, 1 - ly)) * t
    h = edge_profile(d, 1.2, 2)
    cream = hexc("EFE3C8"); terra = hexc("B5532F"); blue = hexc("2F5D7C"); ochre = hexc("D6A243")
    rgb = np.ones((N, N, 3), np.float32) * cream
    px = lx - .5; py = ly - .5
    r = np.hypot(px, py); ang = np.arctan2(py, px)
    # corner quarter-circles (blue) -> big circles across 4 tiles
    rc = np.hypot(np.minimum(lx, 1 - lx), np.minimum(ly, 1 - ly))
    rgb = np.where((rc < .30)[..., None], blue, rgb)
    rgb = np.where((rc < .20)[..., None], cream, rgb)
    rgb = np.where((rc < .12)[..., None], ochre, rgb)
    # centre petals
    petal = r < (.20 + .12 * np.abs(np.cos(2 * ang)))
    rgb = np.where(petal[..., None], terra, rgb)
    rgb = np.where((r < .07)[..., None], ochre, rgb)
    # diamond outline
    dia = np.abs(np.abs(px) + np.abs(py) - .42) < .018
    rgb = np.where(dia[..., None], blue, rgb)
    n = tnoise(12, 12, 4)
    rgb = rgb * (.93 + .1 * n)[..., None]
    rgb = lerp(hexc("8E8578") * np.ones_like(rgb), rgb, h[..., None])
    save("Floor_ladrilho", rgb, .35 * h + .05, h * .5)

def floor_granilite():
    base = fill("E8DFCF") * (.97 + .04 * tnoise(6, 13, 3))[..., None]
    rgb = base.copy()
    img = Image.new("RGB", (N * 3, N * 3)); dr = ImageDraw.Draw(img)
    r = np.random.default_rng(14)
    chips = [hexc(c) for c in ["3B3B3B", "8E8E8E", "C8B79A", "A7744D", "FFFFFF", "6E7F80", "D9C9A8"]]
    layer = np.zeros((N, N, 3), np.float32); cover = np.zeros((N, N), np.float32)
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    for _ in range(2600):
        x, y = r.random() * N, r.random() * N; s = r.random() ** 2 * 9 + 2
        c = chips[r.integers(len(chips))]; fillc = tuple(int(v * 255) for v in c) + (255,)
        pts = [(x + math.cos(a) * s * (0.6 + r.random() * .6), y + math.sin(a) * s * (0.6 + r.random() * .6)) for a in np.linspace(0, 2 * math.pi, 6, endpoint=False) + r.random()]
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                dr.polygon([(px + ox, py + oy) for px, py in pts], fill=fillc)
    a = np.asarray(im, np.float32) / 255
    rgb = lerp(rgb, a[..., :3], a[..., 3:4])
    # brass divider strips every half tile (1 m at 2 m tiling)
    d = np.minimum(np.minimum(np.mod(xx, N / 2), N / 2 - np.mod(xx, N / 2)), np.minimum(np.mod(yy, N / 2), N / 2 - np.mod(yy, N / 2)))
    strip = d < 2.2
    rgb = np.where(strip[..., None], hexc("C9A15A"), rgb)
    save("Floor_granilite", rgb, np.where(strip, .9, .7), a[..., 3] * .15 + strip * .3)

def floor_terracota():
    # hexagon tiles (Provence style)
    s = N / 8  # hex size so the pattern tiles: width = sqrt(3)*s ... use rectangular approximation with offset rows
    nx, ny = 6, 4
    tw, th = N / nx, N / ny
    best = np.full((N, N), 1e9, np.float32); sec = np.full((N, N), 1e9, np.float32); idx = np.zeros((N, N), np.int32)
    centers = []
    for j in range(ny * 2):
        for i in range(nx):
            centers.append(((i + (j % 2) * .5) * tw, j * th / 2))
    k = 0
    for (cxp, cyp) in centers:
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                dx = np.abs(xx - cxp - ox) / tw; dy = np.abs(yy - cyp - oy) / (th / 2)
                dist = np.maximum(dx * .5 + dy * .5 * 1.0, dx * 1.0) if False else np.hypot(dx, dy * .87)
                m = dist < best
                sec = np.where(m, best, np.minimum(sec, dist)); best = np.where(m, dist, best); idx = np.where(m, k, idx)
        k += 1
    d = (sec - best) * tw * .5
    h = edge_profile(d, 2.2, 4)
    tone = np.random.default_rng(41).random(k).astype(np.float32)[idx]
    n = tnoise(9, 15, 4)
    base = lerp(hexc("C0673D"), hexc("A9512E"), tone[..., None]) * (.92 + .12 * n)[..., None]
    rgb = lerp(hexc("CFC3AE") * np.ones_like(base), base, h[..., None])
    save("Floor_terracota", rgb, .3 * h + .05, h * .6 + n * .05)

def floor_vinil():
    cx, cy, d, _ = grid_tiles(4, 4, 1)
    h = edge_profile(d, 1, 2)
    alt = ((cx + cy) % 2).astype(np.float32)
    n = tnoise(16, 16, 5)
    speck = (tnoise(64, 17, 1) > .78).astype(np.float32)
    g = (.80 + .06 * alt + .06 * n - .08 * speck)
    rgb = np.ones((N, N, 3), np.float32) * g[..., None]
    rgb = lerp(rgb * .75, rgb, h[..., None])
    save("Floor_vinil", rgb, .6 * h + .1, h * .3, mask=np.ones((N, N)))

def floor_marmore_escuro():
    cx, cy, d, _ = grid_tiles(4, 4, 1.5)
    h = edge_profile(d, 1.2, 2)
    n = tnoise(3, 18, 3)
    warp = blur(tnoise(2, 19, 2), 8)
    v = np.abs(np.sin((xx + yy * .6) / N * 2 * math.pi * 2 + warp * 9 + n * 4))
    vein = np.clip(1 - v / .06, 0, 1) * np.clip((blur(tnoise(3, 20, 2), 6) - .4) * 5, 0, 1)
    fine = np.clip(1 - np.abs(np.sin((xx * .7 - yy) / N * 2 * math.pi * 3 + warp * 7)) / .025, 0, 1) * .35
    tone = per_tile_rand(cx, cy, 51)[..., 0]
    base = lerp(hexc("1F2A28"), hexc("2C3835"), (n * .6 + tone * .4)[..., None])
    rgb = lerp(base, hexc("D8D6CC") * np.ones_like(base), np.clip(vein + fine * .6, 0, 1)[..., None])
    rgb = lerp(hexc("111613") * np.ones_like(rgb), rgb, h[..., None])
    save("Floor_marmore-escuro", rgb, .9 * h + .05, h * .5)

# ------------------------------------------------------------------ WALLS

def wall_tinta():
    n = tnoise(5, 31, 6); f = tnoise(40, 32, 2)
    g = .86 + .05 * (n - .5) + .03 * (f - .5)
    rgb = np.ones((N, N, 3), np.float32) * g[..., None]
    save("Wall_tinta", rgb, .25, n * .3 + f * .25, strength=3, mask=np.ones((N, N)))

def wall_metro():
    cx, cy, d, _ = grid_tiles(4, 8, 2, offset_rows=.5)
    h = edge_profile(d, 2.5, 7)
    hump = np.sqrt(np.clip(h, 0, 1))
    tone = per_tile_rand(cx, cy, 33)[..., 0]
    g = (.86 + .05 * tone) * (.97 + .05 * hump)
    tile = np.ones((N, N, 3), np.float32) * g[..., None]
    grout = hexc("8E8C88") * np.ones_like(tile)
    rgb = lerp(grout, tile, np.clip(h * 3, 0, 1)[..., None])
    save("Wall_metro", rgb, .9 * np.clip(h * 3, 0, 1) + .05, hump * .8, strength=8, mask=np.clip(h * 3, 0, 1))

def wall_tijolinho():
    cx, cy, d, (lx, ly, tw, th) = grid_tiles(4, 16, 3, offset_rows=.5)
    h = edge_profile(d, 3, 5)
    tone = per_tile_rand(cx, cy, 35, 2)
    n = tnoise(24, 36, 3)
    base = lerp(hexc("C8714F"), hexc("A9533A"), tone[..., 0:1]) * (.9 + .15 * n)[..., None]
    base = lerp(base, hexc("D9A07F") * np.ones_like(base), (tone[..., 1:2] > .85) * .5)
    mortar = hexc("E3DACB") * (.95 + .08 * tnoise(30, 37, 2))[..., None]
    rgb = lerp(mortar, base, h[..., None])
    save("Wall_tijolinho", rgb, .12, h * .7 + n * .1, strength=7)

def wall_ripado():
    ns = 10; sw = N / ns
    lx = np.mod(xx, sw); sid = np.floor(xx / sw)
    gap = 9
    inside = (lx > gap / 2) & (lx < sw - gap / 2)
    d = np.minimum(lx - gap / 2, sw - gap / 2 - lx)
    h = np.where(inside, np.clip(d / 4, 0, 1), 0)
    tone = per_tile_rand(sid, np.zeros_like(sid), 38)[..., 0]
    grain = tnoise(8, 39, 5)
    streak = np.sin(yy / N * 2 * math.pi * 6 + grain * 10 + tone * 8 + lx / sw * 2) * .5 + .5
    base = lerp(hexc("B98352"), hexc("94623A"), tone[..., None]) * (.88 + .14 * streak)[..., None]
    rgb = np.where(inside[..., None], base, hexc("2A2622") * np.ones_like(base))
    save("Wall_ripado", rgb, .35 * h + .05, h, strength=10)

def wall_pastilha():
    cx, cy, d, _ = grid_tiles(16, 16, 2)
    h = edge_profile(d, 2.4, 6)
    tone = per_tile_rand(cx, cy, 40)[..., 0]
    g = .62 + .3 * tone
    tile = np.ones((N, N, 3), np.float32) * g[..., None]
    rgb = lerp(hexc("D8D4CC") * np.ones_like(tile), tile, h[..., None])
    save("Wall_pastilha", rgb, .95 * h + .05, h, strength=8, mask=h)

def wall_listrado():
    period = N / 6
    lx = np.mod(xx, period) / period
    stripe = ((lx > .1) & (lx < .55)).astype(np.float32)
    thin = (np.abs(lx - .78) < .02).astype(np.float32)
    n = tnoise(30, 41, 2)
    cream = hexc("F2EBDC") * (.97 + .04 * n)[..., None]
    tint = np.ones((N, N, 3), np.float32) * (.80 + .04 * n)[..., None]
    m = np.clip(stripe + thin, 0, 1)
    rgb = lerp(cream, tint, m[..., None])
    save("Wall_listrado", rgb, .2, n * .1, strength=2, mask=m)

def wall_floral():
    img = Image.new("L", (N, N), 0); dr = ImageDraw.Draw(img)
    def flower(cx, cy, s):
        for k in range(5):
            a = k / 5 * 2 * math.pi
            px, py = cx + math.cos(a) * s * .55, cy + math.sin(a) * s * .55
            for ox in (-N, 0, N):
                for oy in (-N, 0, N):
                    dr.ellipse([px - s * .38 + ox, py - s * .38 + oy, px + s * .38 + ox, py + s * .38 + oy], fill=255)
    def leaf(cx, cy, s, a):
        pts = []
        for t in np.linspace(0, 1, 12):
            w = math.sin(t * math.pi) * s * .35
            pts.append((t * s, w))
        pts += [(t * s, -math.sin(t * math.pi) * s * .35) for t in np.linspace(1, 0, 12)]
        rot = [(cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)) for x, y in pts]
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                dr.polygon([(x + ox, y + oy) for x, y in rot], fill=150)
    for j in range(4):
        for i in range(4):
            cx = (i + (j % 2) * .5) * N / 4; cy = j * N / 4 + N / 8
            leaf(cx, cy, N / 9, .8); leaf(cx, cy, N / 10, 2.6)
            flower(cx, cy, N / 14)
            # small dot flowers between
            flower(cx + N / 8, cy + N / 8, N / 40)
    a = np.asarray(img, np.float32) / 255
    petals = (a > .9).astype(np.float32); leaves = ((a > .5) & (a <= .9)).astype(np.float32)
    n = tnoise(30, 43, 2)
    cream = hexc("F3EEDF") * (.97 + .04 * n)[..., None]
    rgb = cream.copy()
    rgb = lerp(rgb, hexc("7FA27A") * np.ones_like(rgb), (leaves * .85)[..., None])
    tint = np.ones((N, N, 3), np.float32) * .85
    rgb = lerp(rgb, tint, petals[..., None])
    # flower centres
    save("Wall_floral", rgb, .2, a * .1, strength=2, mask=petals)

def wall_concreto():
    n1 = tnoise(4, 45, 6); n2 = tnoise(30, 46, 2)
    base = lerp(hexc("A6A7A3"), hexc("C2C2BD"), blur(n1, 5)[..., None]) * (.97 + .05 * n2)[..., None]
    # formwork panels 2×2 per tile with tie holes
    lx = np.mod(xx, N / 2); ly = np.mod(yy, N / 2)
    d = np.minimum(np.minimum(lx, N / 2 - lx), np.minimum(ly, N / 2 - ly))
    seam = d < 1.5
    rgb = np.where(seam[..., None], base * .75, base)
    holes = np.zeros((N, N), bool)
    for hx in (N / 8, N * 3 / 8):
        for hy in (N / 8, N * 3 / 8):
            holes |= np.hypot(np.mod(xx, N / 2) - hx, np.mod(yy, N / 2) - hy) < 6
    rgb = np.where(holes[..., None], base * .45, rgb)
    hgt = 1 - seam * .5 - holes * 1.0
    save("Wall_concreto", rgb, .18, hgt.astype(np.float32) + n2 * .1, strength=4)

def wall_lousa():
    n = tnoise(4, 47, 6); f = tnoise(30, 48, 3)
    base = lerp(hexc("27332E"), hexc("33423B"), n[..., None])
    smudge = np.clip(blur(tnoise(3, 49, 4), 10) * 1.6 - .9, 0, 1) * .25
    rgb = lerp(base, hexc("9AA59E") * np.ones_like(base), smudge[..., None])
    rgb = rgb * (.97 + .05 * f)[..., None]
    save("Wall_lousa", rgb, .15, f * .1, strength=2)

def wall_pedra():
    # horizontal stacked slate strips of random lengths ("canjiquinha")
    rows = 14; rh = N / rows
    r = np.random.default_rng(50)
    rgb = np.zeros((N, N, 3), np.float32); hgt = np.zeros((N, N), np.float32)
    palette = [hexc(c) for c in ["9C8C77", "B3A28A", "857663", "C2B59E", "7A6E60", "A99278"]]
    for j in range(rows):
        y0 = int(j * rh); y1 = int((j + 1) * rh)
        x = r.random() * N; start = x
        while x < start + N:
            w = r.random() * 120 + 50
            c = palette[r.integers(len(palette))] * (0.9 + r.random() * .2)
            depth = r.random()
            xs = np.arange(int(x), int(x + w)) % N
            seg_y = slice(y0 + 2, y1 - 2)
            lxp = (np.arange(len(xs)) / len(xs))[None, :]
            rgb[seg_y, xs] = c
            hgt[seg_y, xs] = .6 + depth * .4
            x += w + 3
    n = tnoise(24, 51, 4)
    rgb = rgb * (.85 + .25 * n)[..., None]
    mortar = hgt == 0
    rgb[mortar] = hexc("3E3832")
    save("Wall_pedra", rgb, .1, hgt + n * .15, strength=9)

for fn in [floor_madeira_clara, floor_taco, floor_porcelanato, floor_xadrez, floor_cimento, floor_ladrilho, floor_granilite,
           floor_terracota, floor_vinil, floor_marmore_escuro, wall_tinta, wall_metro, wall_tijolinho, wall_ripado,
           wall_pastilha, wall_listrado, wall_floral, wall_concreto, wall_lousa, wall_pedra]:
    if len(sys.argv) > 2 and fn.__name__ not in sys.argv[2:]: continue
    fn()
