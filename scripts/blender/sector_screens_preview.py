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


ICONS = [steak, tbone, ribs, sausage, drum, ground]
PRICES = [["49,90", "64,90", "32,90", "21,90"], ["27,90", "18,90", "39,90", "58,90"], ["34,90", "44,90", "15,90", "29,90"]]


def price_board(variant):
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(font_path, 78)
    small = ImageFont.truetype(font_path, 34)
    d.rectangle([0, 0, W, 70], fill=NAVY2)
    d.rectangle([0, 66, W, 72], fill=GOLD)
    for k in range(3):                                   # header: pictogram strip, no words
        ICONS[(variant + k) % 6](d, 420 + k * 95, 36, .55)
    for r in range(4):
        y = 125 + r * 112
        if r % 2:
            d.rectangle([0, y - 52, W, y + 52], fill=(33, 50, 92))
        ICONS[(variant * 2 + r) % 6](d, 110, y, 1.15)
        for j in range(16):
            d.ellipse([210 + j * 26, y + 8, 218 + j * 26, y + 16], fill=(120, 136, 170))
        price = PRICES[variant][r]
        d.text((900, y), price, font=big, fill=WHITE if r != 1 else GOLD, anchor="rm")
        d.text((925, y + 18), "", font=small, fill=CREAM)
        if r == 1:
            d.rounded_rectangle([640, y - 40, 690, y + 40], 10, fill=RED)
            d.polygon([(652, y + 18), (665, y - 24), (678, y + 18)], fill=WHITE)   # down-arrow-ish promo badge
    return im


def ticket(number):
    im = Image.new("RGB", (512, 256), (18, 18, 20))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font_path, 190)
    d.text((256, 128), number, font=f, fill=(255, 64, 48), anchor="mm")
    return im


for v in range(3):
    price_board(v).save(os.path.join(out, "FT_PricePreview_%d.png" % v))
ticket("27").save(os.path.join(out, "FT_TicketPreview.png"))
print("ok")
