# PLACEHOLDER art for rankings v1 until the painted 2D icons arrive (league-*.png, globe.png): the game's own medal
# icon recoloured per division, and a simple drawn globe. Same file names as the real art, so dropping it in is a copy.
import colorsys, sys, os, math
from PIL import Image, ImageDraw, ImageFilter
repo = sys.argv[1]
src = Image.open(os.path.join(repo, "assets/game-art/icons/medal.png")).convert("RGBA")
divisions = {  # target hue (0-1), saturation factor, value factor
    "bronze": (0.075, 1.0, 0.82), "silver": (0.6, 0.08, 1.05), "gold": (None, 1, 1), "sapphire": (0.60, 1.0, 0.95),
    "ruby": (0.97, 1.0, 0.92), "emerald": (0.40, 1.0, 0.85), "diamond": (0.52, 0.55, 1.12),
}
out_art = os.path.join(repo, "assets/game-art/icons"); out_unity = os.path.join(repo, "unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Icons")
def save(img, name):
    img.save(os.path.join(out_art, name + ".png"), optimize=True)
    img.resize((128, 128), Image.LANCZOS).save(os.path.join(out_unity, name + ".png"), optimize=True)
px = src.load()
for name, (hue, sf, vf) in divisions.items():
    img = src.copy(); p = img.load()
    if hue is not None:
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = p[x, y]
                if a == 0: continue
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if 0.07 <= h <= 0.17 and s > 0.25:  # the gold of the medal (the blue ribbons stay)
                    r2, g2, b2 = colorsys.hsv_to_rgb(hue, min(1, s * sf), min(1, v * vf))
                    p[x, y] = (int(r2 * 255), int(g2 * 255), int(b2 * 255), a)
    save(img, "league-" + name)
# globe: an ocean disc with soft light, meridians and two green land blobs, a dark rim (painted look, no text)
S = 512; g = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
c, R = S // 2, 208
for i in range(R, 0, -1):
    t = i / R; col = (int(40 + 60 * (1 - t)), int(120 + 80 * (1 - t)), int(200 + 40 * (1 - t)), 255)
    d.ellipse([c - i - 18 * (1 - t), c - i - 22 * (1 - t), c + i - 18 * (1 - t), c + i - 22 * (1 - t)], fill=col)
land = Image.new("L", (S, S), 0); ld = ImageDraw.Draw(land)
ld.polygon([(170, 140), (250, 120), (290, 170), (260, 230), (280, 300), (230, 330), (200, 270), (150, 230)], fill=255)
ld.polygon([(310, 260), (370, 240), (400, 300), (360, 370), (320, 340)], fill=255)
land = land.filter(ImageFilter.GaussianBlur(10)).point(lambda v: 255 if v > 110 else 0)
mask = Image.new("L", (S, S), 0); ImageDraw.Draw(mask).ellipse([c - R, c - R, c + R, c + R], fill=255)
from PIL import ImageChops
land = ImageChops.multiply(land, mask)
g.paste(Image.new("RGBA", (S, S), (96, 176, 86, 255)), (0, 0), land)
lines = Image.new("RGBA", (S, S), (0, 0, 0, 0)); ln = ImageDraw.Draw(lines)
for k in (-2, -1, 0, 1, 2):
    w = abs(k) * 70; ln.ellipse([c - (R - w), c - R, c + (R - w), c + R], outline=(255, 255, 255, 70), width=5)
for k in (-2, -1, 1, 2):
    y = c + k * 70; half = int(math.sqrt(max(0, R * R - (k * 70) ** 2))); ln.line([c - half, y, c + half, y], fill=(255, 255, 255, 70), width=5)
ln.line([c - R, c, c + R, c], fill=(255, 255, 255, 70), width=5)
g = Image.alpha_composite(g, Image.composite(lines, Image.new("RGBA", (S, S), (0, 0, 0, 0)), mask))
d = ImageDraw.Draw(g); d.ellipse([c - R, c - R, c + R, c + R], outline=(24, 52, 96, 255), width=14)
d.ellipse([c - 120, c - 160, c - 40, c - 110], fill=(255, 255, 255, 90))
save(g, "globe")
print("ok")
