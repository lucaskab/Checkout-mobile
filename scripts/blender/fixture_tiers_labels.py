"""Textless twin of IK_Labels_albedo.png (same 8x8 cell layout): every written word replaced by pictograms."""
import sys
from PIL import Image, ImageDraw
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
S = im.size[0] // 8
d = ImageDraw.Draw(im)
def px(c, r, u, v): return im.getpixel((int(c * S + u * S), int(r * S + v * S)))
def R(c, r, u0, v0, u1, v1): return (c * S + u0 * S, r * S + v0 * S, c * S + u1 * S, r * S + v1 * S)
def fill(c, r, u0, v0, u1, v1, col): d.rectangle(R(c, r, u0, v0, u1, v1), fill=col)
def oval(c, r, u0, v0, u1, v1, col, outline=None, w=0): d.ellipse(R(c, r, u0, v0, u1, v1), fill=col, outline=outline, width=w)
def fruit(c, r, u, v, rad, col, leaf=(80, 160, 60)):
    oval(c, r, u - rad, v - rad, u + rad, v + rad, col, (40, 30, 30), max(2, S // 90))
    oval(c, r, u - rad * .45, v - rad * .6, u - rad * .05, v - rad * .25, tuple(min(255, x + 70) for x in col))
    d.polygon([((c + u + rad * .1) * S, (r + v - rad * .95) * S), ((c + u + rad * .7) * S, (r + v - rad * 1.35) * S), ((c + u + rad * .55) * S, (r + v - rad * .85) * S)], fill=leaf)
def dots(c, r, v, col, n=3, rad=.035):
    for k in range(n):
        u = .5 + (k - (n - 1) / 2) * .14
        oval(c, r, u - rad, v - rad, u + rad, v + rad, col)
def wave(c, r, v, col, w=.025):
    pts = [((c + u / 20) * S, (r + v + .03 * ((-1) ** u)) * S) for u in range(2, 19)]
    d.line(pts, fill=col, width=int(w * S), joint="curve")
WHITE = (250, 247, 240)
# row 0: soda wraps -> white oval with the flavour fruit
for c in range(8):
    band = px(c, 0, .04, .5)
    fill(c, 0, 0, .3, 1, .72, band)
    fr = px(c, 0, .155, .77)
    oval(c, 0, .2, .33, .8, .67, WHITE, band, S // 60)
    fruit(c, 0, .5, .51, .12, fr)
# row 1: water / juice / milk / yogurt: wipe the words, add pictogram rows
for c in range(8):
    top, bot = px(c, 1, .04, .22), px(c, 1, .04, .86)
    if c < 2:
        fill(c, 1, 0, .1, 1, .38, top); dots(c, 1, .24, (60, 140, 220) if c == 0 else (255, 255, 255), 3 if c == 0 else 5, .03)
    fill(c, 1, 0, .74, 1, .99, bot)
    wave(c, 1, .86, WHITE if c != 7 else (200, 40, 60))
# row 2: cans -> oval with an icon in the can's stripe colour
for c in range(8):
    ring = px(c, 2, .135, .5)
    stripe = px(c, 2, .03, .3)
    if sum(abs(a - b) for a, b in zip(stripe, WHITE)) < 90: stripe = px(c, 2, .06, .35)
    oval(c, 2, .12, .2, .88, .8, ring)
    if c in (4, 5):   # beer cans: wheat
        for k in range(4):
            oval(c, 2, .43 + (k % 2) * .08, .3 + k * .1, .52 + (k % 2) * .08, .4 + k * .1, stripe)
        d.line([((c + .5) * S, (2 + .3) * S), ((c + .5) * S, (2 + .74) * S)], fill=stripe, width=S // 40)
    elif c == 3:      # energy: bolt
        d.polygon([((c + .55) * S, (2 + .25) * S), ((c + .38) * S, (2 + .54) * S), ((c + .5) * S, (2 + .54) * S), ((c + .44) * S, (2 + .77) * S), ((c + .64) * S, (2 + .45) * S), ((c + .52) * S, (2 + .45) * S)], fill=stripe)
    elif c == 6:      # ice tea: leaf
        oval(c, 2, .38, .32, .62, .7, (120, 170, 60)); d.line([((c + .4) * S, (2 + .68) * S), ((c + .6) * S, (2 + .34) * S)], fill=(70, 110, 40), width=S // 60)
    else:
        fruit(c, 2, .5, .52, .15, stripe if c != 7 else (240, 210, 70))
# row 3: beer ovals (wheat) and wine labels (no year, no word)
for c in range(4):
    inner = px(c, 3, .5, .3)
    ink = px(c, 3, .03, .5)
    if sum(abs(a - b) for a, b in zip(ink, inner)) < 80: ink = (90, 50, 20)
    oval(c, 3, .155, .25, .845, .75, inner)
    for k in range(4):
        oval(c, 3, .43 + (k % 2) * .08, .3 + k * .09, .52 + (k % 2) * .08, .39 + k * .09, ink)
for c in range(4, 8):
    bg = px(c, 3, .5, .2)
    fill(c, 3, .14, .52, .86, .86, bg)
    grape = px(c, 3, .5, .3)
    d.line([((c + .3) * S, (3 + .66) * S), ((c + .7) * S, (3 + .66) * S)], fill=grape, width=S // 50)
    d.line([((c + .38) * S, (3 + .74) * S), ((c + .62) * S, (3 + .74) * S)], fill=grape, width=S // 80)
# rows 5-6: pack headers -> plain band with three dots
for r in (5, 6):
    for c in range(8):
        band = px(c, r, .03, .12)
        fill(c, r, 0, 0, 1, .235, band)
        ico = px(c, r, .5, .55)
        if sum(abs(a - b) for a, b in zip(ico, band)) < 60: ico = WHITE
        dots(c, r, .118, ico, 3, .04)
# row 7: menus and the 'bebidas geladas' card -> pictogram boards
for c in (3, 4):
    bg = (40, 44, 44)
    fill(c, 7, 0, 0, 1, 1, bg)
    oval(c, 7, .4, .07, .6, .2, (240, 190, 70))
    for k in range(5):
        v = .32 + k * .13
        oval(c, 7, .1, v - .03, .16, v + .03, WHITE)
        d.line([((c + .22) * S, (7 + v) * S), ((c + .66) * S, (7 + v) * S)], fill=(200, 200, 190), width=S // 70)
        oval(c, 7, .76, v - .035, .88, v + .035, (240, 160, 80))
bg = px(7, 7, .05, .05)
fill(7, 7, 0, 0, 1, 1, bg)
d.rounded_rectangle(R(7, 7, .4, .2, .6, .8), radius=S // 12, fill=WHITE)
d.rectangle(R(7, 7, .45, .1, .55, .22), fill=WHITE)
for k in range(3):
    oval(7, 7, .2 + k * .25, .82, .3 + k * .25, .92, (240, 220, 90))
im.resize((im.size[0] // 2, im.size[1] // 2), Image.LANCZOS).save(dst)
print("ok", dst)
