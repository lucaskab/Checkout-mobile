"""Bebidas: a bank of four upright glass-door coolers against the wall (no walls, no floor)."""
import math, bmesh
from rk_core import *
from rk_products import *

W, D, H = .8, .74, 2.02          # one cooler: width, depth, cabinet height
HEAD = .3                         # lit header on top
BACK = 1.5                        # Blender +Y = back wall
BODY, TRIM, ACCENT, SECTOR = NAVY, WHITE, GOLD, "27AE60"


def cooler(acc, cx, fill, kind):
    y0 = BACK - D                  # front plane
    yc = BACK - D / 2
    # Cabinet: rounded side walls, top and plinth; a light back panel inside.
    for s in (-1, 1):
        rbox(acc, (.05, D, H), (cx + s * (W / 2 - .025), yc, H / 2 + .1), "C_" + BODY, .02, 3)
    rbox(acc, (W, D, .1), (cx, yc, .05), "C_" + NAVY, .02, 2)
    rbox(acc, (W, .03, H), (cx, BACK - .015, H / 2 + .1), "C_" + BODY, .01, 1)
    rbox(acc, (W - .1, .01, H - .22), (cx, BACK - .04, H / 2 + .1), "E_F2FAFF", .004, 1)
    for s in (-1, 1):  # LED strips down the door jambs
        rbox(acc, (.012, .012, H - .25), (cx + s * (W / 2 - .07), y0 + .06, H / 2 + .1), "E_FFFFFF", .004, 1)
    # Plinth: vent grille with rounded slots and levelling feet.
    rbox(acc, (W - .04, .02, .09), (cx, y0 + .005, .05), "C_" + DARK, .01, 2)
    for k in range(7):
        rbox(acc, (.07, .006, .018), (cx - .27 + k * .09, y0 - .006, .05), "C_111820", .008, 2)
    for s in (-1, 1):
        lathe(acc, [(0, 0), (.022, 0), (.02, .012), (.008, .02), (.008, .03)], (cx + s * (W / 2 - .08), y0 + .08, -.02), "C_" + DARK, 10, 0)
    # Shelves: wire decks with a price channel, stocked with the cooler's line of drinks.
    levels = [.18, .5, .82, 1.14, 1.46, 1.78]
    for i, z in enumerate(levels):
        rbox(acc, (W - .12, D - .12, .012), (cx, yc + .02, z), "C_" + CHROME, .004, 1)
        for k in range(9):
            tube(acc, [(cx - (W - .12) / 2, y0 + .09 + k * .065, z + .008), (cx + (W - .12) / 2, y0 + .09 + k * .065, z + .008)], .003, "C_" + CHROME, 5, caps=False)
        rbox(acc, (W - .12, .012, .035), (cx, y0 + .065, z + .01), "C_" + WHITE, .005, 2)
        for k in range(3):
            rbox(acc, (.07, .004, .026), (cx - .22 + k * .22, y0 + .058, z + .01), "C_" + ("F2C23F" if k % 2 else SECTOR), .004, 1)
        if i == len(levels) - 1:
            # top shelf: a row of cans (two deep) so the cooler looks full to the top
            n = int((W - .16) / .07)
            for row in range(2):
                for k in range(n):
                    can(acc, (cx - (n - 1) * .035 + k * .07, y0 + .14 + row * .2, z + .015), .031, .12, "can_%d" % ((k + i + row) % 8), fill)
            break
        stock(acc, kind, i, cx, y0, z + .015, fill)
    # Door: rounded frame, full glass, vertical chrome bar handle on stand-offs, hinge caps.
    fr = frame_bm(W - .02, H - .12, .045, .045, .055)
    place(fr, (cx, y0 - .01, H / 2 + .12)); acc.add(fr, "C_" + TRIM)
    g = rbox_bm((W - .12, .01, H - .22), .02, 2); uv_box(g)
    place(g, (cx, y0 - .01, H / 2 + .12)); acc.add(g, "G_Glass")
    hx = cx + W / 2 - .09
    tube(acc, [(hx, y0 - .06, .72), (hx, y0 - .075, 1.0), (hx, y0 - .075, 1.3), (hx, y0 - .06, 1.58)], .014, "C_" + CHROME, 10, 3)
    for z in (.72, 1.58):
        tube(acc, [(hx, y0 - .035, z), (hx, y0 - .065, z)], .011, "C_" + CHROME, 8)
    for z in (.2, H):
        lathe(acc, [(0, 0), (.018, 0), (.018, .03), (0, .034)], (cx - W / 2 + .05, y0 - .03, z), "C_" + CHROME, 10, 0)
    # Header: curved cream canopy with a lit sign panel and an orange stripe.
    hb = rbox_bm((W, D + .04, HEAD), .05, 4); uv_box(hb)
    place(hb, (cx, yc - .02, H + .1 + HEAD / 2)); acc.add(hb, "C_" + BODY)
    rbox(acc, (W + .002, D + .05, .035), (cx, yc - .02, H + .12), "C_" + SECTOR, .016, 3)
    rbox(acc, (W - .1, .02, HEAD - .12), (cx, y0 - .04, H + .1 + HEAD / 2 + .01), "E_EAF7EE", .03, 3)
    text(acc, "GELADAS", .085, (cx, y0 - .055, H + .1 + HEAD / 2 + .01), "C_" + SECTOR, .012, bevel=0)


def stock(acc, kind, level, cx, y0, z, fill):
    """Two rows of a drink across one shelf, labels facing the door."""
    lines = {
        "soda": [("pet", "soda_%d" % k) for k in (0, 1, 2, 5, 3, 4)],
        "cans": [("can", "can_%d" % k) for k in (0, 1, 2, 3, 6, 7)],
        "water": [("water", "water_0"), ("carton", "juice_0"), ("water", "water_1"), ("carton", "juice_1"), ("carton", "juice_2"), ("carton", "juice_3")],
        "beer": [("beer", "beer_%d" % k) for k in (0, 1, 2, 3, 0, 1)],
    }[kind]
    what, label = lines[level % len(lines)]
    step = {"pet": .085, "water": .082, "can": .072, "beer": .07, "carton": .082}[what]
    n = int((W - .16) / step)
    x0 = cx - (n - 1) * step / 2
    for row in range(2):
        yy = y0 + .14 + row * .2
        for k in range(n):
            x = x0 + k * step + (row * step * .5 if what == "can" else 0)
            if x > cx + (W - .16) / 2:
                continue
            if what == "pet":
                liquids = {"soda_0": "C_3A120A", "soda_1": "C_7A4A12", "soda_2": "C_F28C28", "soda_5": "C_1E0A06", "soda_3": "C_D8EFA0", "soda_4": "C_6A2A7A"}
                caps = {"soda_0": RED, "soda_1": "2F8F3A", "soda_2": ORANGE, "soda_5": "1B1B1B", "soda_3": "B8D93A", "soda_4": "7B3FA0"}
                pet_bottle(acc, (x, yy, z), .27, .034, liquids.get(label, "C_3A120A"), label, "C_" + caps.get(label, RED), fill)
            elif what == "water":
                water_bottle(acc, (x, yy, z), .27, .033, label, fill)
            elif what == "can":
                can(acc, (x, yy, z), .031, .12, label, fill)
                if row == 0 and level % 2 == 0:
                    can(acc, (x, yy, z + .121), .031, .12, label, fill)
            elif what == "beer":
                longneck(acc, (x, yy, z), .25, .03, "C_5A3312" if k % 3 else "C_2E5A24", label, fill)
            elif what == "carton":
                carton(acc, (x, yy, z), .068, .068, .21, label, fill)


def build(name="sector-bebidas"):
    acc = Acc(name)
    for i, (cx, kind) in enumerate(zip((-1.2, -.4, .4, 1.2), ("soda", "cans", "water", "beer"))):
        cooler(acc, cx, "Anim Fill %d" % i, kind)
    # Continuous crown over the bank with the department name, and end panels.
    rbox(acc, (3.24, .08, .06), (0, BACK - D - .04, H + .1 + HEAD + .03), "C_" + ACCENT, .025, 3)
    for s in (-1, 1):
        rbox(acc, (.04, D + .06, H + HEAD + .12), (s * 1.62, BACK - D / 2 - .02, (H + HEAD + .12) / 2), "C_" + NAVY, .02, 3)
        rbox(acc, (.05, .03, H + HEAD + .1), (s * 1.62, BACK - D - .02, (H + HEAD + .12) / 2), "C_" + ACCENT, .012, 2)
    return acc
