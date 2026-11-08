"""Title overlays (1920x1080 RGBA) for the trailer, in the game's font and palette."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys, os
A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
NAVY = (31, 45, 92); GOLD = (230, 174, 52); CREAM = (255, 246, 228); WHITE = (255, 255, 255)
W, H = 1920, 1080
def font(name, size): return ImageFont.truetype(os.path.join(A, name), size)

def stroked(draw, xy, text, f, fill, stroke, sw, anchor="ms"):
    draw.text(xy, text, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)

def title(kicker, headline, out, y=930):
    """Kicker on a gold pill, headline in white with a navy outline and a soft shadow, bottom centre."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # soft dark band behind for legibility
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
    for i in range(260):
        a = int(150 * (i / 260) ** 1.6)
        bd.line([(0, H - 260 + i), (W, H - 260 + i)], fill=(14, 20, 44, a))
    im = Image.alpha_composite(im, band)
    fk = font("Fredoka_700Bold.ttf", 40); fh = font("Fredoka_700Bold.ttf", 92)
    d = ImageDraw.Draw(im)
    # headline shadow
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    sd.text((W // 2 + 4, y + 8), headline, font=fh, fill=(0, 0, 0, 150), stroke_width=10, stroke_fill=(0, 0, 0, 150), anchor="ms")
    sh = sh.filter(ImageFilter.GaussianBlur(8)); im = Image.alpha_composite(im, sh); d = ImageDraw.Draw(im)
    stroked(d, (W // 2, y), headline, fh, WHITE, NAVY, 9)
    if kicker:
        tw = d.textlength(kicker, font=fk); px, py = 28, 14
        top = y - 92 - 70
        box = [W // 2 - tw / 2 - px, top, W // 2 + tw / 2 + px, top + 40 + py * 2]
        d.rounded_rectangle([box[0], box[1] + 5, box[2], box[3] + 5], radius=34, fill=(150, 100, 20, 255))
        d.rounded_rectangle(box, radius=34, fill=GOLD + (255,), outline=NAVY + (255,), width=4)
        d.text((W // 2, top + py + 34), kicker, font=fk, fill=NAVY, anchor="ms")
    im.save(out)

def chip(text, out):
    """A small stage name chip, bottom left (the growth montage)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = font("Fredoka_700Bold.ttf", 46); tw = d.textlength(text, font=f)
    x, y = 70, 70
    d.rounded_rectangle([x, y + 6, x + tw + 60, y + 86], radius=40, fill=(10, 16, 40, 200))
    d.rounded_rectangle([x, y, x + tw + 60, y + 80], radius=40, fill=CREAM + (255,), outline=NAVY + (255,), width=5)
    d.text((x + 30, y + 57), text, font=f, fill=NAVY, anchor="ls")
    im.save(out)

if __name__ == "__main__":
    title("COMECE PEQUENO", "Uma mesinha na calçada", sys.argv[1] if len(sys.argv) > 1 else "/tmp/t.png")
