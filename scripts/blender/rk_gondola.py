"""Gôndola de corredor: a long, double-sided supermarket aisle gondola (both faces stocked), with end panels,
category header, price channels and kick plates. Rows of them form the market's aisles.
Blender space: length along X (2.4 m), faces towards -Y and +Y, 1.72 m tall."""
import math, random, bmesh
from rk_core import *
from rk_products import box_pack, chip_bag, pet_bottle, can, carton

L, D, H = 2.0, .9, 1.72
LEVELS = [.14, .5, .84, 1.18, 1.5]


def shelf_face(acc, side, rnd, fills, theme):
    """One stocked face: side = -1 (front, -Y) or +1 (back, +Y). Products fill each level's height and depth."""
    s = side
    tops = LEVELS[1:] + [H + .08]
    for li, z in enumerate(LEVELS):
        depth = .44 if li == 0 else .38
        yc = s * (.05 + depth / 2)
        rbox(acc, (L - .08, depth, .025), (0, yc, z), "C_" + WHITE, .006, 1)
        # price channel with tags
        rbox(acc, (L - .08, .018, .045), (0, s * (.05 + depth + .005), z + .005), "C_" + NAVY, .006, 2)
        for k in range(8):
            rbox(acc, (.09, .004, .032), (-L / 2 + .2 + k * .29, s * (.05 + depth + .016), z + .006), "C_" + ("F2C23F" if k % 3 else WHITE), .004, 1)
        kind = theme[li % len(theme)]
        avail = tops[li] - z - .06
        # only the top level shows its back rows from the game camera; lower levels keep two rows deep
        stock_row(acc, kind, s, z + .013, depth if li == len(LEVELS) - 1 else min(depth, .2), avail, fills)


def stock_row(acc, kind, s, z, depth, avail, fills):
    """Packs the whole shelf: facings side by side along the run, as many rows deep as fit, as tall as the gap."""
    x = -L / 2 + .05
    k = 0
    end = L / 2 - .05
    while x < end - .04:
        grp = fills[min(3, int((x + L / 2) / (L / 4)))]
        if kind[0] == "box":
            w, d = kind[1], kind[2]
            h = min(avail * .92, kind[3] * 1.35)
            if x + w > end:
                break
            rows = max(1, int((depth - .02) / (d + .004)))
            for row in range(rows):
                y = s * (.07 + d / 2 + row * (d + .004))
                box_pack(acc, (x + w / 2, y, z), w, d, h, kind[4][k % len(kind[4])], grp)
            x += w + .004
        elif kind[0] == "bag":
            w = .15
            if x + w > end:
                break
            for row in range(max(1, min(3, int(depth / .12)))):
                chip_bag(acc, (x + w / 2, s * (.1 + row * .12), z), w, avail * .9, .07, kind[1][k % len(kind[1])], grp)
            x += w + .004
        elif kind[0] == "bottle":
            r = .036
            if x + 2 * r > end:
                break
            h = min(avail * .95, .32)
            for row in range(int((depth - .02) / (2 * r + .004))):
                pet_bottle(acc, (x + r, s * (.07 + r + row * (2 * r + .004)), z), h, r, "C_" + kind[2][k % len(kind[2])], kind[1][k % len(kind[1])], "C_" + kind[3], grp, 8)
            x += 2 * r + .004
        elif kind[0] == "jar":
            r = .045
            if x + 2 * r > end:
                break
            for row in range(int((depth - .02) / (2 * r + .004))):
                for st in range(2 if avail > .34 else 1):
                    zz = z + st * .165
                    yy = s * (.07 + r + row * (2 * r + .004))
                    lathe(acc, [(0, 0), (.04, 0), (.045, .02), (.045, .1), (.035, .13), (.035, .15)], (x + r, yy, zz), "C_" + kind[2], 10, 1, cap_top=False, grp=grp)
                    lathe(acc, [(.046, .03), (.046, .09)], (x + r, yy, zz), LAB, 10, 0, uv_cell=kind[1], u_rep=2, v_range=(.03, .09), cap_top=False, cap_bottom=False, grp=grp)
                    lathe(acc, [(0, 0), (.04, 0), (.041, .025), (0, .027)], (x + r, yy, zz + .15), "C_" + kind[3], 10, 1, grp=grp)
            x += 2 * r + .004
        elif kind[0] == "carton":
            w = .075
            if x + w > end:
                break
            h = min(avail * .95, .26)
            for row in range(int((depth - .02) / (w + .004))):
                carton(acc, (x + w / 2, s * (.07 + w / 2 + row * (w + .004)), z), w, w, h, kind[1][k % len(kind[1])], grp)
            x += w + .004
        k += 1


def gondola(acc, cx=0, cy=0, header="MERCEARIA", theme=None, seed=0, fills=None, accent="E0B040"):
    fills = fills or ["Anim Fill %d" % i for i in range(4)]
    X = Xf(acc, (cx, cy, 0)) if (cx or cy) else acc
    rnd = random.Random(seed)
    theme = theme or [
        ("box", .12, .07, .26, ["pack_0", "pack_5"]),
        ("bag", ["pack_6", "pack_15", "pack_14"]),
        ("jar", "pack_9", "D74A3C", "E0B040"),
        ("box", .09, .06, .2, ["pack_1", "pack_2", "pack_3"]),
        ("box", .1, .07, .15, ["pack_7", "pack_13", "pack_4"]),
    ]
    # base deck and kick plates (navy), spine with pegboard both sides, top cap
    rbox(X, (L, D, .1), (0, 0, .05), "C_" + NAVY, .02, 3)
    for s in (-1, 1):
        rbox(X, (L - .02, .02, .1), (0, s * (D / 2 - .01), .05), "C_" + accent, .01, 2)
    rbox(X, (L - .04, .1, H - .1), (0, 0, H / 2 + .05), "C_" + WHITE, .02, 2)
    for s in (-1, 1):
        rbox(X, (L - .06, .012, H - .2), (0, s * .052, H / 2 + .02), "T_IK_Pegboard", .004, 1, uv=2)
    rbox(X, (L + .02, .16, .05), (0, 0, H + .1), "C_" + NAVY, .02, 3)
    # uprights
    for x in (-L / 2 + .02, 0, L / 2 - .02):
        rbox(X, (.04, .1, H), (x, 0, H / 2 + .05), "C_" + NAVY, .01, 2)
    for s in (-1, 1):
        shelf_face(X, s, rnd, fills, theme if s < 0 else theme[1:] + theme[:1])
    # End caps: rounded side frames, a lit category header on top and a short promo shelf unit stocked with
    # stacked packs (like the ends of a real aisle).
    for e in (-1, 1):
        ex = e * (L / 2 + .03)
        fr = frame_bm(D, H + .35, .05, .16, .05)
        place(fr, (ex, 0, (H + .35) / 2), (0, 0, 90)); X.add(fr, "C_" + NAVY)
        rbox(X, (.03, D - .1, H - .1), (ex - e * .01, 0, H / 2 + .05), "C_" + WHITE, .01, 1)
        hb, _ = panel_bm(D - .06, .3, .06, .1, 6); uv_box(hb)
        place(hb, (ex + e * .02, 0, H + .17), (0, 0, 90)); X.add(hb, "C_" + accent)
        text(X, header, .1, (ex + e * .055, 0, H + .17), "C_" + WHITE, .02, rot=(0, 0, 90 if e > 0 else -90), bevel=.003)
        # four promo shelves right up to the header, each packed full
        levels = (.12, .5, .88, 1.26)
        for li, z in enumerate(levels):
            rbox(X, (.34, D - .12, .025), (ex + e * .19, 0, z), "C_" + WHITE, .006, 1)
            rbox(X, (.02, D - .12, .04), (ex + e * .36, 0, z + .005), "C_D74A3C", .006, 2)
            lab = ("pack_0", "pack_14", "pack_4", "pack_12")[li]
            top = levels[li + 1] if li + 1 < len(levels) else H - .02
            hh = top - z - .05
            n = 7
            for k in range(n):
                yy = -D / 2 + .1 + k * (D - .2) / (n - 1)
                for row in range(2):
                    box_pack(X, (ex + e * (.1 + row * .15), yy, z + .013), .12, .13, hh, lab, fills[0 if e < 0 else 3], yaw=90 * e)
        rbox(X, (.03, .5, .12), (ex + e * .37, 0, H - .03), "C_D74A3C", .03, 3)
        text(X, "OFERTA", .06, (ex + e * .39, 0, H - .03), "C_" + WHITE, .012, rot=(0, 0, 90 if e > 0 else -90), bevel=0)

def build(name="shelf-gondola"):
    if name in VARIANTS:
        return build_variant(name)
    acc = Acc(name)
    gondola(acc)
    return acc


def build_aisle(name="aisle-preview"):
    """Preview only: three gondolas making two aisles."""
    acc = Acc(name)
    themes = [None,
              [("bottle", ["soda_0", "soda_1", "soda_2"], ["3A120A", "7A4A12", "F28C28"], "D74A3C"), ("carton", ["juice_0", "juice_1", "milk"]),
               ("bottle", ["water_0", "water_1"], ["BFE3F0", "BFE3F0"], "3E8FD6"), ("carton", ["juice_2", "juice_3"]), ("bag", ["pack_6", "pack_15"])],
              [("box", .12, .08, .22, ["pack_7", "pack_14"]), ("box", .1, .08, .28, ["pack_12", "pack_7"]), ("bag", ["pack_14", "pack_6"]),
               ("jar", "pack_10", "F2C23F", "1D2B4F"), ("box", .14, .1, .18, ["pack_12"])]]
    headers = ["MERCEARIA", "BEBIDAS", "LIMPEZA"]
    accents = ["E0B040", "27AE60", "3E8FD6"]
    for i in range(3):
        gondola(acc, 0, -2.3 + i * 2.3, headers[i], themes[i], i, accent=accents[i])
    return acc


VARIANTS = {
    "shelf-grocery": ("MERCEARIA", "E0B040", [
        ("box", .12, .07, .26, ["pack_0", "pack_2"]),
        ("box", .1, .06, .2, ["pack_1", "pack_3", "pack_7"]),
        ("jar", "pack_9", "D74A3C", "E0B040"),
        ("box", .1, .07, .15, ["pack_4", "pack_10", "pack_11"]),
        ("bottle", ["soda_0", "soda_1", "soda_2"], ["3A120A", "7A4A12", "F28C28"], "D74A3C"),
    ]),
    "shelf-snacks": ("DOCES & SNACKS", "E86A9E", [
        ("bag", ["pack_6", "pack_15"]),
        ("box", .13, .05, .2, ["pack_14", "pack_2"]),
        ("bag", ["pack_15", "pack_6"]),
        ("box", .1, .06, .14, ["pack_14"]),
        ("jar", "pack_14", "6B3E26", "E86A9E"),
    ]),
    "shelf-cleaning": ("LIMPEZA", "3E8FD6", [
        ("box", .14, .1, .22, ["pack_13"]),
        ("bottle", ["pack_12", "pack_5"], ["2FA84F", "3E8FD6"], "FFFFFF"),
        ("box", .1, .07, .18, ["pack_5", "pack_12"]),
        ("box", .12, .08, .22, ["pack_13", "pack_5"]),
        ("box", .09, .06, .16, ["pack_12"]),
    ]),
}


def build_variant(name):
    header, accent, theme = VARIANTS[name]
    acc = Acc(name)
    gondola(acc, 0, 0, header, theme, len(name) * 7, accent=accent)
    return acc
