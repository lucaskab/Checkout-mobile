# PLACEHOLDER art for rankings v1 until the painted 2D division badges arrive (league-*.png): the game's own medal
# icon recoloured per division. Same file names as the real art, so dropping it in is a copy.
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
# (the globe of Mundo is the game's own painted desk globe, Icons/globe.png, already used by Opções › Idioma: not drawn here)
print("ok")
