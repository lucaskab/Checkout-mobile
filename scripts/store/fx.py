"""Animated overlays for the trailer (v3, Lucas 08/11: "coloque mais efeito no vídeo... mais coisa chamativa... uau,
olha que legal quando o mercado fica super grande"): titles that pop in with a bounce (and count up), a big centre
caption for the reveals, confetti bursts, and the synthesized riser / impact sounds. Every frame is a 1920x1080 RGBA
PNG that ffmpeg overlays as an image sequence."""
import math, os, random, subprocess
from PIL import Image, ImageDraw, ImageFilter
import titles

W, H = titles.W, titles.H
NAVY, GOLD, CREAM, WHITE = titles.NAVY, titles.GOLD, titles.CREAM, titles.WHITE


def ease_out_back(t, k=1.9):
    t = max(0.0, min(1.0, t)) - 1
    return 1 + (k + 1) * t ** 3 + k * t ** 2


def ease_out(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


def band(out):
    """The soft dark band behind the lower titles (static: only the words pop)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i in range(280):
        d.line([(0, H - 280 + i), (W, H - 280 + i)], fill=(14, 20, 44, int(160 * (i / 280) ** 1.6)))
    im.save(out)


def title_words(kicker, headline, y=930):
    """The lower title without its band: gold kicker pill and the white headline (as titles.title)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fk = titles.font("Fredoka_700Bold.ttf", 42); fh = titles.font("Fredoka_700Bold.ttf", 96)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    sd.text((W // 2 + 4, y + 8), headline, font=fh, fill=(0, 0, 0, 160), stroke_width=10, stroke_fill=(0, 0, 0, 160), anchor="ms")
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(8))); d = ImageDraw.Draw(im)
    titles.stroked(d, (W // 2, y), headline, fh, WHITE, NAVY, 10)
    if kicker:
        tw = d.textlength(kicker, font=fk); px, py = 30, 14
        top = y - 96 - 72
        box = [W // 2 - tw / 2 - px, top, W // 2 + tw / 2 + px, top + 42 + py * 2]
        d.rounded_rectangle([box[0], box[1] + 6, box[2], box[3] + 6], radius=36, fill=(150, 100, 20, 255))
        d.rounded_rectangle(box, radius=36, fill=GOLD + (255,), outline=NAVY + (255,), width=4)
        d.text((W // 2, top + py + 36), kicker, font=fk, fill=NAVY, anchor="ms")
    return im


def scaled(im, s, alpha, centre):
    """`im` scaled by s about `centre`, with its opacity times alpha."""
    if s <= 0.01 or alpha <= 0: return Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bb = im.getbbox()
    if not bb: return im
    part = im.crop(bb)
    w, h = max(1, int(part.width * s)), max(1, int(part.height * s))
    part = part.resize((w, h), Image.LANCZOS)
    if alpha < 1:
        a = part.getchannel("A").point(lambda v: int(v * alpha)); part.putalpha(a)
    cx, cy = centre
    ox = cx + (bb[0] - cx) * s; oy = cy + (bb[1] - cy) * s
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); out.alpha_composite(part, (int(round(ox)), int(round(oy))))
    return out


def title_anim(prefix, kicker, headline, count=None, frames=24):
    """Pop-in frames prefix_000.png.. (and prefix_static.png, the settled title). `count` = (number, template with
    {n}): the kicker counts up to the number while it pops in."""
    centre = (W // 2, 930 - 70)
    for i in range(frames):
        t = i / (frames - 1)
        k = kicker
        if count:
            n, tpl = count; k = tpl.format(n=int(round(n * ease_out(min(1, t * 1.15)))))
        s = .55 + .45 * ease_out_back(min(1, i / 11))
        scaled(title_words(k, headline), s, min(1, i / 4), centre).save(f"{prefix}_{i:03d}.png")
    final = kicker if not count else count[1].format(n=count[0])
    title_words(final, headline).save(f"{prefix}_static.png")
    return frames


def big_caption(prefix, lines, frames=16):
    """A big centre caption for the reveals: gold words with a thick navy outline and a glow, popping in."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f = titles.font("Fredoka_700Bold.ttf", 148)
    gap = 160; y0 = H // 2 - (len(lines) - 1) * gap // 2 + 40
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    for j, line in enumerate(lines):
        gd.text((W // 2, y0 + j * gap), line, font=f, fill=(255, 220, 120, 170), stroke_width=26, stroke_fill=(255, 210, 90, 170), anchor="ms")
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(22)))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    for j, line in enumerate(lines):
        sd.text((W // 2 + 6, y0 + j * gap + 12), line, font=f, fill=(0, 0, 0, 170), stroke_width=14, stroke_fill=(0, 0, 0, 170), anchor="ms")
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(10))); d = ImageDraw.Draw(im)
    for j, line in enumerate(lines):
        d.text((W // 2, y0 + j * gap), line, font=f, fill=(255, 236, 160) if j == len(lines) - 1 else WHITE, stroke_width=14, stroke_fill=NAVY, anchor="ms")
    centre = (W // 2, H // 2)
    for i in range(frames):
        s = .3 + .7 * ease_out_back(min(1, i / 12), 2.4)
        scaled(im, s, min(1, i / 3), centre).save(f"{prefix}_{i:03d}.png")
    im.save(f"{prefix}_static.png")
    return frames


CONFETTI = [(230, 174, 52), (43, 179, 166), (240, 136, 62), (255, 246, 228), (229, 72, 77), (95, 176, 74), (77, 132, 230)]


def confetti(prefix, frames=75, n=240, seed=3):
    """A confetti burst from two cannons at the bottom corners, falling and fluttering."""
    rnd = random.Random(seed); parts = []
    for k in range(n):
        side = -1 if k % 2 == 0 else 1
        x = W / 2 + side * (W / 2 + 20); y = H + 30
        ang = math.radians(rnd.uniform(62, 84)); sp = rnd.uniform(2700, 3800)
        parts.append(dict(x=x, y=y, vx=-side * math.cos(ang) * sp, vy=-math.sin(ang) * sp, r=rnd.uniform(0, 6.28), vr=rnd.uniform(-9, 9),
                          ph=rnd.uniform(0, 6.28), fl=rnd.uniform(7, 14), w=rnd.uniform(12, 20), h=rnd.uniform(20, 32),
                          c=CONFETTI[rnd.randrange(len(CONFETTI))], delay=rnd.uniform(0, .18)))
    dt = 1 / 30
    for i in range(frames):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        t = i * dt
        for p in parts:
            tt = t - p["delay"]
            if tt < 0: continue
            # integrate with drag: closed form per axis for vx (drag), vy (drag + gravity)
            k = 2.1; g = 1300
            ex = math.exp(-k * tt)
            x = p["x"] + p["vx"] / k * (1 - ex)
            # (screen y grows downwards: gravity pulls +y; dv/dt = g - k v)
            y = p["y"] + (p["vy"] - g / k) / k * (1 - ex) + (g / k) * tt
            if y > H + 60 or x < -60 or x > W + 60: continue
            a = p["r"] + p["vr"] * tt
            flip = abs(math.cos(p["ph"] + p["fl"] * tt))
            hw, hh = p["w"] / 2 * (.25 + .75 * flip), p["h"] / 2
            ca, sa = math.cos(a), math.sin(a)
            pts = [(x + ca * dx - sa * dy, y + sa * dx + ca * dy) for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
            shade = .75 + .25 * flip
            col = tuple(int(c * shade) for c in p["c"])
            alpha = 255 if t < frames * dt - .5 else int(255 * max(0, (frames * dt - t) / .5))
            d.polygon(pts, fill=col + (alpha,))
        im.save(f"{prefix}_{i:03d}.png")
    return frames


def sounds(out_dir):
    """A riser (1.6 s, building into a reveal) and an impact (a low boom with a noise crack)."""
    riser = os.path.join(out_dir, "riser.wav"); impact = os.path.join(out_dir, "impact.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "aevalsrc='0.35*(t/1.6)^2*(sin(2*PI*(180*t+380*t*t))+0.6*sin(2*PI*(360*t+760*t*t)))+0.25*(t/1.6)^3*(random(0)*2-1)':s=48000:d=1.6",
                    "-af", "highpass=f=120,afade=t=out:st=1.55:d=0.05", riser], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "aevalsrc='0.95*sin(2*PI*(60-25*t)*t)*exp(-3.2*t)+0.5*(random(0)*2-1)*exp(-14*t)':s=48000:d=1.4",
                    "-af", "lowpass=f=5000", impact], check=True)
    return riser, impact
