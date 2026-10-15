"""paint_prints.py -- paints the two framed pictures of the REPOR backdrop as image textures (no letters):
  tex/still_life.png   a painterly still life: teal bowl with apples, pears and grapes on a wooden table
  tex/poster.png       a vintage market poster: a big orange slice on a sunburst, teal / cream / orange
Pure Pillow + numpy, deterministic. Run from anywhere:  python paint_prints.py [out_dir]
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
rng = np.random.default_rng(7)

def noise(w, h, scale, octaves=4):
    """Value noise in 0..1 (sum of upsampled random grids)."""
    acc = np.zeros((h, w), np.float32); amp = 1; tot = 0
    for o in range(octaves):
        s = max(2, int(scale / (2 ** o)))
        g = rng.random((h // s + 2, w // s + 2)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w + s, h + s), Image.BICUBIC).crop((0, 0, w, h))
        acc += np.asarray(im, np.float32) / 255 * amp; tot += amp; amp *= .5
    return acc / tot

def canvas_grain(img, strength=.10, weave=3):
    """Linen weave + paint grain multiplied over the picture."""
    w, h = img.size
    y, x = np.mgrid[0:h, 0:w]
    weave_f = (np.sin(x * math.pi / weave) * np.sin(y * math.pi / weave)) * .5 + .5
    n = noise(w, h, 24, 3)
    m = 1 - strength + strength * (weave_f * .5 + n * .5)
    a = np.asarray(img.convert("RGB"), np.float32) * m[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def brushy(img, amount=2.2):
    """Smears the image along slightly varying directions so edges look painted, not vector."""
    w, h = img.size
    a = np.asarray(img, np.float32)
    dx = (noise(w, h, 40, 2) - .5) * amount * 4; dy = (noise(w, h, 40, 2) - .5) * amount * 4
    yy, xx = np.mgrid[0:h, 0:w]
    sx = np.clip(xx + dx, 0, w - 1).astype(int); sy = np.clip(yy + dy, 0, h - 1).astype(int)
    out = a[sy, sx]
    return Image.fromarray(out.astype(np.uint8)).filter(ImageFilter.GaussianBlur(.6))

def shaded_blob(size, color, light=(-.45, -.55), rim=.55, hl=(.22, .20), hl_r=.18, squash=1.0, dark=.42):
    """An RGBA sprite of a round fruit: base colour, a darker terminator away from the light, a soft rim, a highlight."""
    s = size; y, x = np.mgrid[0:s, 0:s]
    u = (x - s / 2) / (s / 2); v = (y - s / 2) / (s / 2) / squash
    r = np.sqrt(u * u + v * v)
    mask = np.clip((1 - r) * s * .5, 0, 1)
    nz = np.sqrt(np.clip(1 - r * r, 0, 1))
    lx, ly = light; ln = math.sqrt(lx * lx + ly * ly + .6 * .6)
    lam = (u * lx + v * ly + nz * .6) / ln
    lam = np.clip(lam, 0, 1) ** .9
    shade = dark + (1 - dark) * lam
    rimf = np.clip((r - rim) / (1 - rim), 0, 1) ** 2 * .35
    col = np.array(color, np.float32)[None, None, :]
    rgb = col * shade[..., None] * (1 - rimf[..., None]) + np.array([30, 10, 20], np.float32) * rimf[..., None] * .4
    # specular highlight
    hx, hy = hl; d = np.sqrt((u - hx) ** 2 + (v - hy) ** 2)
    spec = np.clip(1 - d / hl_r, 0, 1) ** 2 * .75
    rgb = rgb + (255 - rgb) * spec[..., None]
    out = np.zeros((s, s, 4), np.float32); out[..., :3] = np.clip(rgb, 0, 255); out[..., 3] = mask * 255
    return Image.fromarray(out.astype(np.uint8), "RGBA")

def paste(img, sprite, cx, cy, angle=0):
    if angle: sprite = sprite.rotate(angle, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(sprite, (int(cx - sprite.width / 2), int(cy - sprite.height / 2)))

def shadow(img, box, blur=14, alpha=110):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse(box, fill=(40, 25, 15, alpha))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))

def pear(size, color=(196, 190, 70)):
    """A pear = a small blob on top of a bigger one, blended, with a stem."""
    s = size; im = Image.new("RGBA", (s, int(s * 1.35)), (0, 0, 0, 0))
    paste(im, shaded_blob(int(s * .62), color, hl=(.18, .25), hl_r=.2), s / 2, s * .45)
    paste(im, shaded_blob(s, color, hl=(.2, .15), hl_r=.2), s / 2, s * .85)
    d = ImageDraw.Draw(im); d.line([(s / 2, s * .16), (s * .56, s * .02)], fill=(85, 55, 30, 255), width=max(3, s // 22))
    return im

def apple(size, color=(205, 48, 42)):
    s = size; im = Image.new("RGBA", (s, int(s * 1.1)), (0, 0, 0, 0))
    paste(im, shaded_blob(s, color, hl=(.22, .2), hl_r=.2, squash=.92), s / 2, s * .58)
    # dimple + stem + leaf
    d = ImageDraw.Draw(im)
    d.ellipse([s * .42, s * .13, s * .58, s * .22], fill=(120, 25, 25, 160))
    d.line([(s / 2, s * .18), (s * .54, s * .02)], fill=(90, 60, 30, 255), width=max(3, s // 24))
    leaf = Image.new("RGBA", (s // 2, s // 4), (0, 0, 0, 0)); ImageDraw.Draw(leaf).ellipse([0, 0, s // 2 - 1, s // 4 - 1], fill=(70, 130, 60, 255))
    ImageDraw.Draw(leaf).line([(2, s // 8), (s // 2 - 3, s // 8)], fill=(45, 95, 40, 255), width=2)
    paste(im, leaf, s * .66, s * .09, angle=25)
    return im

def grapes(size, color=(96, 56, 120)):
    s = size; im = Image.new("RGBA", (s, int(s * 1.25)), (0, 0, 0, 0))
    r = s * .13; rows = [(s * .20, 5), (s * .40, 4), (s * .60, 3), (s * .80, 2), (s * .98, 1)]
    for yc, n in rows:
        for k in range(n):
            xc = s / 2 + (k - (n - 1) / 2) * r * 1.9
            paste(im, shaded_blob(int(r * 2.1), color, hl=(.25, .25), hl_r=.22), xc, yc)
    d = ImageDraw.Draw(im); d.line([(s / 2, s * .06), (s * .58, -2)], fill=(85, 60, 35, 255), width=max(3, s // 24))
    return im

def still_life(w=1024, h=820):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # wall: warm cream with a soft vignette; table: wood with grain
    bg = np.zeros((h, w, 3), np.float32); bg[...] = (236, 220, 186)
    n = noise(w, h, 160, 3); bg *= (0.9 + 0.12 * n)[..., None]
    y, x = np.mgrid[0:h, 0:w]; vign = 1 - .28 * (((x - w / 2) / (w / 2)) ** 2 + ((y - h * .4) / (h * .7)) ** 2)
    bg *= vign[..., None]
    img.paste(Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)))
    ty = int(h * .66)
    grain = noise(w, h - ty, 60, 3); grain2 = np.sin((y[ty:] * .9 + grain * 30) * .18) * .5 + .5
    wood = np.zeros((h - ty, w, 3), np.float32); wood[...] = (150, 92, 52)
    wood *= (0.82 + .20 * grain2 + .08 * grain)[..., None]; wood *= (1 - .35 * ((y[ty:] - ty) / (h - ty)))[..., None]
    img.paste(Image.fromarray(np.clip(wood, 0, 255).astype(np.uint8)), (0, ty))
    ImageDraw.Draw(img).rectangle([0, ty - 6, w, ty + 4], fill=(110, 68, 38, 255))
    # bowl: shadow, back rim, body (teal, glazed), front rim
    bx, by, bw_, bh_ = w * .52, h * .72, w * .50, h * .22
    shadow(img, [bx - bw_ * .55, by - bh_ * .1, bx + bw_ * .62, by + bh_ * .35], blur=18, alpha=140)
    bowl = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(bowl)
    d.ellipse([bx - bw_ / 2, by - bh_ * .95, bx + bw_ / 2, by - bh_ * .35], fill=(26, 100, 95, 255))      # back rim / inside
    d.ellipse([bx - bw_ / 2 + 14, by - bh_ * .9, bx + bw_ / 2 - 14, by - bh_ * .4], fill=(16, 70, 68, 255))  # inside dark
    img.alpha_composite(bowl)
    # fruit (back to front)
    paste(img, pear(int(w * .17)), bx - bw_ * .22, by - bh_ * .78)
    paste(img, apple(int(w * .17), (210, 60, 45)), bx + bw_ * .05, by - bh_ * .70)
    paste(img, grapes(int(w * .16)), bx + bw_ * .28, by - bh_ * .62)
    paste(img, apple(int(w * .18), (195, 40, 38)), bx - bw_ * .12, by - bh_ * .55)
    paste(img, pear(int(w * .16), (205, 170, 60)), bx + bw_ * .17, by - bh_ * .50)
    # bowl front
    front = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(front)
    d.chord([bx - bw_ / 2, by - bh_ * 1.5, bx + bw_ / 2, by + bh_ * .3], 0, 180, fill=(30, 118, 110, 255))
    d.ellipse([bx - bw_ / 2, by - bh_ * .95, bx + bw_ / 2, by - bh_ * .35], outline=(60, 160, 150, 255), width=10)
    # glaze: lighter left side, darker right, a vertical highlight
    g = np.asarray(front, np.float32)
    shade = 1 - .35 * np.clip((x - bx) / (bw_ / 2), 0, 1) + .12 * np.clip((bx - x) / (bw_ / 2), 0, 1)
    g[..., :3] *= shade[..., None]
    hlx = bx - bw_ * .30; hl = np.clip(1 - np.abs(x - hlx) / (bw_ * .05), 0, 1) ** 2 * .5
    g[..., :3] += (255 - g[..., :3]) * hl[..., None]
    front = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGBA"); img.alpha_composite(front)
    # a loose apple and a lemon on the table in front
    shadow(img, [w * .13, by + bh_ * .02, w * .33, by + bh_ * .2], blur=10, alpha=120)
    paste(img, apple(int(w * .16), (200, 52, 40)), w * .23, by + bh_ * .0)
    shadow(img, [w * .76, by + bh_ * .05, w * .94, by + bh_ * .2], blur=10, alpha=110)
    paste(img, shaded_blob(int(w * .13), (232, 196, 60), hl=(.2, .2), hl_r=.18, squash=.78), w * .85, by + bh_ * .06, angle=12)
    out = brushy(img.convert("RGB"), 2.0)
    return canvas_grain(out, .07, weave=2)

def poster(w=820, h=1024):
    """Vintage market poster: sunburst, a big orange slice, a teal band top and bottom, a cream frame. No text."""
    img = Image.new("RGB", (w, h), (244, 226, 180))
    d = ImageDraw.Draw(img)
    cx, cy = w / 2, h * .50
    for k in range(24):   # sunburst
        a0 = k * 15; a1 = a0 + 7.5
        d.pieslice([cx - w * 1.2, cy - w * 1.2, cx + w * 1.2, cy + w * 1.2], a0, a1, fill=(238, 200, 140))
    d.rectangle([0, 0, w, h * .11], fill=(20, 100, 96)); d.rectangle([0, h * .89, w, h], fill=(20, 100, 96))
    d.rectangle([0, h * .11, w, h * .125], fill=(230, 120, 40)); d.rectangle([0, h * .875, w, h * .89], fill=(230, 120, 40))
    # orange slice: peel ring, pith, segments
    R = w * .36
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(236, 120, 30))
    d.ellipse([cx - R * .93, cy - R * .93, cx + R * .93, cy + R * .93], fill=(252, 232, 190))
    for k in range(10):
        a0 = k * 36 + 2; a1 = a0 + 32
        d.pieslice([cx - R * .86, cy - R * .86, cx + R * .86, cy + R * .86], a0, a1, fill=(246, 150, 40))
        a = math.radians((a0 + a1) / 2)
        for t in np.linspace(.25, .8, 4):   # juice vesicle streaks
            px, py = cx + math.cos(a) * R * .86 * t, cy + math.sin(a) * R * .86 * t
            d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(252, 190, 90))
    d.ellipse([cx - R * .08, cy - R * .08, cx + R * .08, cy + R * .08], fill=(252, 232, 190))
    # two leaves
    for ang, dx in ((-30, -R * .55), (20, R * .35)):
        leaf = Image.new("RGBA", (int(R * .9), int(R * .4)), (0, 0, 0, 0)); ld = ImageDraw.Draw(leaf)
        ld.ellipse([0, 0, leaf.width - 1, leaf.height - 1], fill=(40, 120, 70, 255)); ld.line([(6, leaf.height / 2), (leaf.width - 6, leaf.height / 2)], fill=(25, 85, 50, 255), width=4)
        rl = leaf.rotate(ang, resample=Image.BICUBIC, expand=True)
        img.paste(rl, (int(cx + dx - rl.width / 2), int(cy - R * 1.02 - rl.height / 2)), rl)
    # small dots row (decorative, no glyphs)
    for k in range(9):
        px = w * .15 + k * w * .0875; d.ellipse([px - 9, h * .83 - 9, px + 9, h * .83 + 9], fill=(230, 120, 40))
    # paper grain + faded corners
    a = np.asarray(img, np.float32); n = noise(w, h, 6, 2); a *= (.92 + .10 * n)[..., None]
    y, x = np.mgrid[0:h, 0:w]; a *= (1 - .18 * (((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2))[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    still_life().save(os.path.join(OUT, "still_life.png")); poster().save(os.path.join(OUT, "poster.png"))
    print("wrote", OUT)
