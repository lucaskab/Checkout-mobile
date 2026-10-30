"""RENDER-ONLY preview textures for the sector price panels and the ticket display (round 4).

The game draws the real screens at runtime (product pictograms + live prices, multilingual), so the exported FBX keeps
blank emissive slots "E_PriceScreen" / "E_TicketScreen". These images only exist so the concept renders show the
supermarket vibe: pictograms and digits, no words.

    python3 sector_screens_preview.py <out_dir> <font.ttf>
"""
import sys, os, math
from PIL import Image, ImageDraw, ImageFont

out, font_path = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
NAVY, NAVY2, GOLD, CREAM, RED, WHITE = (29, 43, 79), (38, 58, 104), (211, 165, 61), (244, 235, 216), (200, 48, 44), (250, 248, 240)
W, H = 1024, 576


def steak(d, x, y, s, col=(196, 60, 58)):
    d.ellipse([x - 40 * s, y - 26 * s, x + 40 * s, y + 26 * s], fill=col)
    d.ellipse([x - 40 * s, y - 26 * s, x + 40 * s, y + 26 * s], outline=(248, 236, 214), width=int(6 * s))
    d.arc([x - 22 * s, y - 12 * s, x + 18 * s, y + 14 * s], 200, 340, fill=(248, 230, 220), width=int(3 * s))


def tbone(d, x, y, s):
    steak(d, x, y, s)
    d.rectangle([x - 4 * s, y - 24 * s, x + 4 * s, y + 24 * s], fill=(244, 238, 222))
    d.rectangle([x - 22 * s, y - 24 * s, x + 22 * s, y - 16 * s], fill=(244, 238, 222))


def sausage(d, x, y, s):
    for k in range(3):
        d.ellipse([x - 44 * s + k * 30 * s, y - 12 * s, x - 14 * s + k * 30 * s, y + 12 * s], fill=(176, 72, 52))


def drum(d, x, y, s):
    d.ellipse([x - 38 * s, y - 24 * s, x + 14 * s, y + 24 * s], fill=(232, 168, 86))
    d.line([x + 8 * s, y + 6 * s, x + 40 * s, y + 22 * s], fill=(244, 238, 222), width=int(10 * s))
    d.ellipse([x + 34 * s, y + 14 * s, x + 48 * s, y + 30 * s], fill=(244, 238, 222))


def ribs(d, x, y, s):
    d.rounded_rectangle([x - 44 * s, y - 20 * s, x + 44 * s, y + 20 * s], int(10 * s), fill=(176, 64, 48))
    for k in range(5):
        d.line([x - 34 * s + k * 17 * s, y - 20 * s, x - 34 * s + k * 17 * s, y + 20 * s], fill=(244, 238, 222), width=int(4 * s))


def ground(d, x, y, s):
    d.ellipse([x - 40 * s, y - 22 * s, x + 40 * s, y + 22 * s], fill=(200, 80, 84))
    for k in range(14):
        a = k * 2.4
        d.ellipse([x + 26 * s * math.cos(a) - 3 * s, y + 14 * s * math.sin(a) - 3 * s, x + 26 * s * math.cos(a) + 3 * s, y + 14 * s * math.sin(a) + 3 * s], fill=(244, 210, 206))


def loaf(d, x, y, s):
    d.ellipse([x - 44 * s, y - 24 * s, x + 44 * s, y + 24 * s], fill=(214, 150, 78))
    for k in range(3):
        d.line([x - 22 * s + k * 18 * s, y - 14 * s, x - 10 * s + k * 18 * s, y + 14 * s], fill=(240, 210, 150), width=int(5 * s))


def baguette(d, x, y, s):
    d.rounded_rectangle([x - 50 * s, y - 10 * s, x + 50 * s, y + 10 * s], int(10 * s), fill=(226, 170, 92))
    for k in range(4):
        d.line([x - 34 * s + k * 22 * s, y - 7 * s, x - 26 * s + k * 22 * s, y + 7 * s], fill=(244, 214, 156), width=int(4 * s))


def croissant(d, x, y, s):
    d.arc([x - 42 * s, y - 24 * s, x + 42 * s, y + 40 * s], 200, 340, fill=(220, 150, 64), width=int(20 * s))


def roll(d, x, y, s):
    d.ellipse([x - 26 * s, y - 20 * s, x + 26 * s, y + 20 * s], fill=(222, 160, 80))
    d.line([x - 12 * s, y, x + 12 * s, y], fill=(244, 214, 156), width=int(4 * s))


def cake(d, x, y, s):
    d.rectangle([x - 36 * s, y - 12 * s, x + 36 * s, y + 24 * s], fill=(246, 226, 190))
    d.rectangle([x - 36 * s, y - 22 * s, x + 36 * s, y - 8 * s], fill=(244, 166, 193))
    d.ellipse([x - 6 * s, y - 34 * s, x + 6 * s, y - 22 * s], fill=(200, 48, 44))


def cheese_ball(d, x, y, s):
    for k in range(3):
        d.ellipse([x - 40 * s + k * 26 * s, y - 13 * s, x - 14 * s + k * 26 * s, y + 13 * s], fill=(236, 196, 96))


def wedge(d, x, y, s):
    d.polygon([(x - 40 * s, y + 22 * s), (x + 40 * s, y + 22 * s), (x + 40 * s, y - 22 * s)], fill=(246, 206, 90))
    for (a, b) in ((14, 8), (26, -4), (30, 14)):
        d.ellipse([x + a * s - 5 * s, y + b * s - 5 * s, x + a * s + 5 * s, y + b * s + 5 * s], fill=(214, 168, 64))


def wheel(d, x, y, s):
    d.ellipse([x - 42 * s, y - 22 * s, x + 42 * s, y + 22 * s], fill=(232, 182, 60))
    d.ellipse([x - 42 * s, y - 22 * s, x + 42 * s, y + 6 * s], fill=(246, 210, 100))


def ham(d, x, y, s):
    d.ellipse([x - 40 * s, y - 24 * s, x + 40 * s, y + 24 * s], fill=(240, 160, 160))
    d.ellipse([x - 40 * s, y - 24 * s, x + 40 * s, y + 24 * s], outline=(250, 236, 226), width=int(5 * s))


def salami(d, x, y, s):
    d.ellipse([x - 26 * s, y - 26 * s, x + 26 * s, y + 26 * s], fill=(176, 52, 56))
    for k in range(7):
        a = k * 2.3
        d.ellipse([x + 15 * s * math.cos(a) - 4 * s, y + 15 * s * math.sin(a) - 4 * s, x + 15 * s * math.cos(a) + 4 * s, y + 15 * s * math.sin(a) + 4 * s], fill=(246, 228, 214))


def yogurt(d, x, y, s):
    d.polygon([(x - 22 * s, y - 24 * s), (x + 22 * s, y - 24 * s), (x + 16 * s, y + 26 * s), (x - 16 * s, y + 26 * s)], fill=(250, 248, 240))
    d.rectangle([x - 22 * s, y - 30 * s, x + 22 * s, y - 22 * s], fill=(62, 143, 214))


def fish(d, x, y, s):
    d.ellipse([x - 44 * s, y - 18 * s, x + 24 * s, y + 18 * s], fill=(150, 170, 190))
    d.polygon([(x + 18 * s, y), (x + 46 * s, y - 20 * s), (x + 46 * s, y + 20 * s)], fill=(110, 130, 150))
    d.ellipse([x - 34 * s, y - 6 * s, x - 26 * s, y + 2 * s], fill=(20, 20, 24))


def shrimp(d, x, y, s):
    d.arc([x - 30 * s, y - 26 * s, x + 30 * s, y + 30 * s], 30, 280, fill=(250, 140, 110), width=int(14 * s))


def salmon(d, x, y, s):
    d.ellipse([x - 36 * s, y - 26 * s, x + 36 * s, y + 26 * s], fill=(250, 136, 92))
    for k in range(3):
        d.arc([x - 26 * s, y - 18 * s + k * 10 * s, x + 26 * s, y + 18 * s + k * 10 * s], 200, 340, fill=(255, 220, 200), width=int(3 * s))


def crab(d, x, y, s):
    d.ellipse([x - 30 * s, y - 18 * s, x + 30 * s, y + 18 * s], fill=(214, 70, 50))
    for sx in (-1, 1):
        d.ellipse([x + sx * 36 * s - 10 * s, y - 30 * s, x + sx * 36 * s + 10 * s, y - 12 * s], fill=(214, 70, 50))


def squid(d, x, y, s):
    d.polygon([(x - 10 * s, y - 34 * s), (x + 14 * s, y + 6 * s), (x - 34 * s, y + 6 * s)], fill=(236, 210, 220))
    for k in range(4):
        d.line([x - 26 * s + k * 10 * s, y + 6 * s, x - 30 * s + k * 10 * s, y + 30 * s], fill=(236, 210, 220), width=int(4 * s))


def cone(d, x, y, s):
    d.polygon([(x - 18 * s, y - 4 * s), (x + 18 * s, y - 4 * s), (x, y + 34 * s)], fill=(226, 170, 96))
    d.ellipse([x - 20 * s, y - 34 * s, x + 20 * s, y + 4 * s], fill=(244, 166, 193))


def cup(d, x, y, s):
    d.polygon([(x - 26 * s, y - 6 * s), (x + 26 * s, y - 6 * s), (x + 18 * s, y + 28 * s), (x - 18 * s, y + 28 * s)], fill=(250, 248, 240))
    d.ellipse([x - 24 * s, y - 30 * s, x, y - 2 * s], fill=(176, 206, 120))
    d.ellipse([x, y - 30 * s, x + 24 * s, y - 2 * s], fill=(118, 70, 46))


def pop(d, x, y, s):
    d.rounded_rectangle([x - 16 * s, y - 30 * s, x + 16 * s, y + 14 * s], int(10 * s), fill=(242, 140, 40))
    d.line([x, y + 14 * s, x, y + 32 * s], fill=(214, 170, 112), width=int(5 * s))


def tub(d, x, y, s):
    d.polygon([(x - 30 * s, y - 18 * s), (x + 30 * s, y - 18 * s), (x + 24 * s, y + 24 * s), (x - 24 * s, y + 24 * s)], fill=(250, 248, 240))
    d.rectangle([x - 32 * s, y - 26 * s, x + 32 * s, y - 16 * s], fill=(232, 80, 91))


def scoop(d, x, y, s):
    for k, c in enumerate(((244, 166, 193), (186, 232, 210), (118, 70, 46))):
        d.ellipse([x - 40 * s + k * 26 * s, y - 14 * s, x - 14 * s + k * 26 * s, y + 14 * s], fill=c)


def bottle(d, x, y, s, col=(42, 59, 34)):
    d.rounded_rectangle([x - 12 * s, y - 14 * s, x + 12 * s, y + 34 * s], int(5 * s), fill=col)
    d.rectangle([x - 5 * s, y - 36 * s, x + 5 * s, y - 14 * s], fill=col)
    d.rectangle([x - 6 * s, y - 38 * s, x + 6 * s, y - 28 * s], fill=(122, 30, 46))
    d.rectangle([x - 10 * s, y + 2 * s, x + 10 * s, y + 20 * s], fill=(244, 235, 216))


def red_bottle(d, x, y, s):
    bottle(d, x, y, s, (74, 28, 36))


def wglass(d, x, y, s):
    d.polygon([(x - 18 * s, y - 30 * s), (x + 18 * s, y - 30 * s), (x + 12 * s, y), (x - 12 * s, y)], fill=(150, 30, 50))
    d.line([x, y, x, y + 26 * s], fill=(220, 220, 230), width=int(4 * s))
    d.line([x - 14 * s, y + 28 * s, x + 14 * s, y + 28 * s], fill=(220, 220, 230), width=int(4 * s))


def grapes(d, x, y, s):
    for (a, b) in ((-14, -14), (0, -14), (14, -14), (-7, -1), (7, -1), (0, 12)):
        d.ellipse([x + a * s - 9 * s, y + b * s - 9 * s, x + a * s + 9 * s, y + b * s + 9 * s], fill=(120, 50, 110))


def sparkle(d, x, y, s):
    bottle(d, x, y, s, (30, 50, 40))
    d.rectangle([x - 7 * s, y - 40 * s, x + 7 * s, y - 24 * s], fill=(211, 165, 61))


def orange(d, x, y, s):
    d.ellipse([x - 28 * s, y - 26 * s, x + 28 * s, y + 28 * s], fill=(242, 140, 40))
    d.polygon([(x, y - 26 * s), (x + 22 * s, y - 40 * s), (x + 16 * s, y - 20 * s)], fill=(95, 181, 72))


def juice(d, x, y, s, col=(242, 140, 40)):
    d.polygon([(x - 20 * s, y - 28 * s), (x + 20 * s, y - 28 * s), (x + 15 * s, y + 30 * s), (x - 15 * s, y + 30 * s)], fill=(230, 240, 248))
    d.polygon([(x - 18 * s, y - 14 * s), (x + 18 * s, y - 14 * s), (x + 15 * s, y + 28 * s), (x - 15 * s, y + 28 * s)], fill=col)
    d.line([x + 6 * s, y - 28 * s, x + 16 * s, y - 44 * s], fill=(232, 80, 91), width=int(4 * s))


def green_juice(d, x, y, s):
    juice(d, x, y, s, (125, 184, 74))


def red_juice(d, x, y, s):
    juice(d, x, y, s, (216, 53, 74))


def pineapple(d, x, y, s):
    d.ellipse([x - 20 * s, y - 16 * s, x + 20 * s, y + 32 * s], fill=(214, 160, 52))
    for k in range(3):
        d.polygon([(x - 4 * s + k * 4 * s, y - 16 * s), (x - 12 * s + k * 12 * s, y - 42 * s), (x + 2 * s + k * 4 * s, y - 16 * s)], fill=(80, 150, 70))


ICON_SETS = {
    "acougue": [steak, tbone, ribs, sausage, drum, ground],
    "padaria": [loaf, baguette, croissant, roll, cake, cheese_ball],
    "queijaria": [wedge, wheel, ham, salami, yogurt, cheese_ball],
    "peixaria": [fish, shrimp, salmon, crab, squid, fish],
    "sorvetes": [cone, cup, scoop, pop, tub, cone],
    "adega": [bottle, red_bottle, wglass, grapes, sparkle, bottle],
    "sucos": [orange, juice, green_juice, red_juice, pineapple, juice],
}
PRICES = [["49,90", "64,90", "32,90", "21,90"], ["27,90", "18,90", "39,90", "58,90"], ["34,90", "44,90", "15,90", "29,90"]]


def price_board(variant, icons):
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(font_path, 78)
    d.rectangle([0, 0, W, 70], fill=NAVY2)
    d.rectangle([0, 66, W, 72], fill=GOLD)
    for k in range(3):                                   # header: pictogram strip, no words
        icons[(variant + k) % 6](d, 420 + k * 95, 36, .55)
    for r in range(4):
        y = 125 + r * 112
        if r % 2:
            d.rectangle([0, y - 52, W, y + 52], fill=(33, 50, 92))
        icons[(variant * 2 + r) % 6](d, 110, y, 1.15)
        for j in range(16):
            d.ellipse([210 + j * 26, y + 8, 218 + j * 26, y + 16], fill=(120, 136, 170))
        d.text((900, y), PRICES[variant][r], font=big, fill=WHITE if r != 1 else GOLD, anchor="rm")
        if r == 1:
            d.rounded_rectangle([640, y - 40, 690, y + 40], 10, fill=RED)
            d.polygon([(652, y - 18), (678, y - 18), (665, y + 24)], fill=WHITE)
    return im


def ticket(number):
    im = Image.new("RGB", (512, 256), (18, 18, 20))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font_path, 190)
    d.text((256, 128), number, font=f, fill=(255, 64, 48), anchor="mm")
    return im


# one image per sector, three boards stacked (variant 0 at the top); the screens pick a third by UV
for sid, icons in ICON_SETS.items():
    sheet = Image.new("RGB", (W, H * 3), NAVY)
    for v in range(3):
        sheet.paste(price_board(v, icons), (0, v * H))
    sheet.save(os.path.join(out, "FT_PricePreview_%s.png" % sid))
ticket("27").save(os.path.join(out, "FT_TicketPreview.png"))
print("ok")
