"""Adega: a full wall of wine (cubby bays of lying bottles, a lit arched showcase in the middle) and the tasting
barrel with glasses, decanter and a cheese board in front. No side walls, no crates on the floor."""
import math, random, bmesh
from rk_core import *
from rk_products import wine_bottle

BACK, HW, H = 1.5, 1.6, 2.5
WINE = "8E2240"
GLASSES = ["2A3B22", "3A1520", "2F4A2A", "4A2A2E", "1E2A1A", "D9D2A0"]
FOILS = ["7A1E2E", "E0B040", "1D2B4F", "2F3A40", "8E2240", "F4EFE4"]


def cubby_bay(acc, x0, x1, fill, seed):
    """Square cubbies, one bottle each, lying neck-out."""
    cols = 4
    cw = (x1 - x0) / cols
    rows = 12
    z0, z1 = .3, 2.14
    ch = (z1 - z0) / rows
    depth = .38
    yf = BACK - .05 - depth
    rbox(acc, (x1 - x0, .02, z1 - z0 + .04), ((x0 + x1) / 2, BACK - .05, (z0 + z1) / 2), "T_IK_R_WoodDark", .005, 1, uv=1.5)
    for c in range(cols + 1):
        rbox(acc, (.018, depth, z1 - z0 + .02), (x0 + c * cw, BACK - .05 - depth / 2, (z0 + z1) / 2), "T_IK_R_Wood", .004, 1, uv=2)
    for r in range(rows + 1):
        rbox(acc, (x1 - x0, depth, .016), ((x0 + x1) / 2, BACK - .05 - depth / 2, z0 + r * ch), "T_IK_R_Wood", .004, 1, uv=2)
    rnd = random.Random(seed)
    for c in range(cols):
        for r in range(rows):
            x = x0 + (c + .5) * cw
            z = z0 + (r + .5) * ch - .01
            k = rnd.randrange(len(GLASSES))
            wine_bottle(acc, (x, BACK - .13, z), .31, .037, "C_" + GLASSES[k], "wine_%d" % rnd.randrange(4), "C_" + FOILS[k], fill, 8, rot=(90, 0, 0))
    # brass label strip every 3 rows
    for r in range(0, rows, 3):
        rbox(acc, (x1 - x0 - .02, .008, .02), ((x0 + x1) / 2, yf - .004, z0 + r * ch + .01), "C_" + GOLD, .004, 1)


def showcase(acc, x0, x1):
    """Arched, back-lit niche with three shelves of standing bottles, labels to the front."""
    cx, w = (x0 + x1) / 2, x1 - x0
    # back glow and arch
    rbox(acc, (w - .06, .02, 1.6), (cx, BACK - .06, 1.25), "E_FFE2B0", .01, 1)
    # Header with an arched underside (polygon in XZ, extruded along Y, ear-clipped).
    pts = [(cx - w / 2 - .02, 2.2), (cx + w / 2 + .02, 2.2), (cx + w / 2 + .02, 1.86)]
    pts += [(cx + math.cos(a) * w / 2, 1.86 + math.sin(a) * .22) for a in [math.pi * i / 16 for i in range(17)]]
    pts += [(cx - w / 2 - .02, 1.86)]
    bm = bmesh.new()
    fv = [bm.verts.new((x, BACK - .44, z)) for x, z in pts]
    bv = [bm.verts.new((x, BACK - .06, z)) for x, z in pts]
    ff = bm.faces.new(list(reversed(fv))); bf = bm.faces.new(bv)
    n = len(pts)
    for k in range(n):
        bm.faces.new((fv[k], fv[(k + 1) % n], bv[(k + 1) % n], bv[k]))
    bmesh.ops.triangulate(bm, faces=[ff, bf], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv_box(bm, 1.5)
    acc.add(bm, "T_IK_R_WoodDark", smooth=False)
    tube(acc, [(cx + math.cos(a) * (w / 2 - .01), BACK - .445, 1.86 + math.sin(a) * .21) for a in [math.pi * i / 16 for i in range(17)]], .012, "C_" + GOLD, 8)
    for s in (-1, 1):
        rbox(acc, (.03, .4, 1.9), (cx + s * w / 2, BACK - .25, 1.4), "T_IK_R_WoodDark", .01, 2, uv=1.5)
    # shelves with brass edge and standing bottles
    for i, z in enumerate((.62, 1.08, 1.54)):
        rbox(acc, (w - .02, .34, .03), (cx, BACK - .24, z), "T_IK_R_Wood", .008, 2, uv=2)
        rbox(acc, (w - .02, .01, .025), (cx, BACK - .415, z + .005), "C_" + GOLD, .004, 1)
        rbox(acc, (w - .1, .012, .012), (cx, BACK - .4, z + .4), "E_FFF1D0", .004, 1)
        n = 5
        for k in range(n):
            x = cx - (w - .16) / 2 + k * (w - .16) / (n - 1)
            kk = (i * 3 + k) % len(GLASSES)
            wine_bottle(acc, (x, BACK - .22, z + .015), .33, .038, "C_" + GLASSES[kk], "wine_%d" % ((i + k) % 4), "C_" + FOILS[kk], "Body", 14)
    # drawer below with brass pulls
    for i in range(2):
        rbox(acc, (w - .04, .36, .17), (cx, BACK - .23, .15 + i * .19), "T_IK_R_Wood", .015, 3, uv=2)
        tube(acc, [(cx - .08, BACK - .43, .16 + i * .19), (cx - .08, BACK - .45, .16 + i * .19), (cx + .08, BACK - .45, .16 + i * .19), (cx + .08, BACK - .43, .16 + i * .19)], .007, "C_" + GOLD, 6)


def wine_wall(acc):
    # Plinth, crown moulding and the sign.
    rbox(acc, (2 * HW, .5, .28), (0, BACK - .25, .14), "T_IK_R_WoodDark", .02, 3, uv=1.5)
    rbox(acc, (2 * HW + .04, .52, .02), (0, BACK - .25, .29), "C_" + GOLD, .006, 1)
    crown = [(BACK, 2.2), (BACK - .5, 2.2), (BACK - .52, 2.24), (BACK - .56, 2.3), (BACK - .56, 2.38), (BACK - .52, 2.42), (BACK, 2.42)]
    bm = bmesh.new()
    a = [bm.verts.new((-HW - .02, y, z)) for y, z in crown]
    b = [bm.verts.new((HW + .02, y, z)) for y, z in crown]
    bm.faces.new(a); bm.faces.new(list(reversed(b)))
    for j in range(len(crown)):
        bm.faces.new((a[j], a[(j + 1) % len(crown)], b[(j + 1) % len(crown)], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); uv_box(bm, 1.5)
    acc.add(bm, "T_IK_R_WoodDark")
    rbox(acc, (2 * HW + .06, .58, .03), (0, BACK - .28, 2.2), "C_" + GOLD, .008, 1)
    # Vertical pilasters between the bays.
    for x in (-HW, -.8, -.4, .4, .8, HW):
        rbox(acc, (.07, .44, 1.94), (x, BACK - .22, 1.25), "T_IK_R_WoodDark", .015, 3, uv=1.5)
    bays = [(-HW + .035, -.835, 0), (-.765, -.435, 1), (.435, .765, 2), (.835, HW - .035, 3)]
    for x0, x1, i in bays:
        cubby_bay(acc, x0, x1, "Anim Fill %d" % i, 11 + i * 5)
    showcase(acc, -.365, .365)
    # Sign over the wall.
    rbox(acc, (1.9, .08, .42), (0, BACK - .3, 2.72), "C_" + WINE, .05, 4)
    rbox(acc, (1.96, .09, .04), (0, BACK - .3, 2.5), "C_" + GOLD, .015, 2)
    rbox(acc, (1.96, .09, .04), (0, BACK - .3, 2.94), "C_" + GOLD, .015, 2)
    text(acc, "ADEGA", .24, (0, BACK - .35, 2.72), "C_" + GOLDL, .04, bevel=.006)
    for s in (-1, 1):  # bunches of grapes on the sign ends
        for k in range(9):
            r = (k % 3) * .032 - .032; row = k // 3
            blob(acc, (.028, .028, .028), (s * .78 + r * (1 - row * .3), BACK - .36, 2.75 - row * .045), "C_6A2A5A", 2, .05, k)
        rbox(acc, (.06, .01, .035), (s * .78 + .03, BACK - .355, 2.8), "C_4E9A3A", .01, 2, rot=(0, 30, 0))


def barrel(acc, loc, r=.32, h=.9):
    """Standing cask: bulged staves (textured), dark iron hoops, a round top board."""
    x, y, z = loc
    prof = [(0, 0)] + [(r * (.86 + .14 * math.sin(math.pi * t)), h * t) for t in [i / 12 for i in range(13)]] + [(r * .82, h), (0, h - .01)]
    lathe(acc, prof, loc, "T_IK_Staves", 24, 0)
    for t in (.06, .22, .78, .94):
        rr = r * (.86 + .14 * math.sin(math.pi * t)) + .006
        lathe(acc, [(rr, h * t - .018), (rr + .004, h * t), (rr, h * t + .018)], loc, "C_2F2A26", 24, 0, cap_top=False, cap_bottom=False)
        for k in range(6):
            a = k * math.pi / 3 + .3
            blob(acc, (.007, .007, .007), (x + math.cos(a) * (rr + .004), y + math.sin(a) * (rr + .004), z + h * t), "C_4A4440", 1, 0, k)


def wine_glass(acc, x, y, z, wine=True):
    lathe(acc, [(0, 0), (.036, 0), (.036, .004), (.005, .012), (.004, .09), (.02, .1), (.036, .13), (.04, .17), (.034, .2)], (x, y, z), "G_Glass", 14, 2, cap_top=False)
    if wine:
        lathe(acc, [(0, .103), (.025, .106), (.034, .125), (.036, .135), (0, .135)], (x, y, z), "C_6A0F24", 14, 1)


def tasting(acc, cx, cy):
    barrel(acc, (cx, cy, 0), .33, .92)
    lathe(acc, [(0, 0), (.46, 0), (.48, .02), (.48, .045), (.46, .05), (0, .05)], (cx, cy, .92), "T_IK_R_WoodDark", 32, 0)
    for (dx, dy, w) in ((-.2, -.14, True), (-.05, -.28, True), (.14, -.2, False)):
        wine_glass(acc, cx + dx, cy + dy, .97, w)
    # decanter
    lathe(acc, [(0, 0), (.1, 0), (.12, .04), (.1, .1), (.04, .15), (.025, .26), (.035, .28)], (cx + .02, cy + .05, .97), "G_Glass", 20, 3, cap_top=False)
    lathe(acc, [(0, 0), (.1, 0), (.118, .04), (.1, .085), (0, .085)], (cx + .02, cy + .05, .975), "C_6A0F24", 20, 2)
    wine_bottle(acc, (cx + .22, cy + .08, .97), .31, .037, "C_3A1520", "wine_1", "C_7A1E2E", "Body", 14)
    # cheese board with wedges and grapes
    rbox(acc, (.26, .16, .02), (cx - .17, cy + .14, .98), "T_IK_ButcherBlock", .01, 2)
    for k in range(3):
        bm = bmesh.new()
        pts = [(0, 0), (.06, -.02), (.06, .02)]
        vs0 = [bm.verts.new((cx - .24 + k * .06 + px, cy + .12 + py, .99)) for px, py in pts]
        vs1 = [bm.verts.new((cx - .24 + k * .06 + px, cy + .12 + py, 1.02)) for px, py in pts]
        bm.faces.new(vs0); bm.faces.new(list(reversed(vs1)))
        for j in range(3):
            bm.faces.new((vs0[j], vs0[(j + 1) % 3], vs1[(j + 1) % 3], vs1[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces); uv_box(bm)
        acc.add(bm, "C_F2C94C", smooth=False)
    for k in range(7):
        blob(acc, (.012, .012, .012), (cx - .08 + (k % 3) * .02, cy + .18 + (k // 3) * .018, 1.005), "C_7A3B8C", 1, 0, k)
    # two cask stools
    for s in (-1, 1):
        sx, sy = cx + s * .62, cy - .05
        lathe(acc, [(0, 0), (.16, 0), (.18, .3), (.16, .6), (0, .6)], (sx, sy, 0), "T_IK_Staves", 18, 2)
        lathe(acc, [(0, 0), (.19, 0), (.2, .03), (.18, .06), (0, .06)], (sx, sy, .6), "C_" + WINE, 18, 1)


def champagne_stand(acc, x, y):
    tube(acc, [(x, y, 0), (x, y, .72)], .014, "C_" + GOLD, 8)
    for k in range(3):
        a = k * 2.094
        tube(acc, [(x, y, .02), (x + math.cos(a) * .18, y + math.sin(a) * .18, 0)], .01, "C_" + GOLD, 6)
    lathe(acc, [(0, 0), (.1, 0), (.13, .2), (.135, .22), (.125, .22)], (x, y, .72), "C_" + CHROME, 20, 1, cap_top=False)
    for k in range(12):
        blob(acc, (.03, .03, .022), (x + math.cos(k) * .07, y + math.sin(k) * .07, .92), "C_E8F6FB", 1, .2, k)
    wine_bottle(acc, (x + .02, y, .78), .34, .04, "C_2F4A2A", "wine_2", "C_E0B040", "Body", 14, rot=(12, 0, 0))


def build(name="sector-adega"):
    acc = Acc(name)
    wine_wall(acc)
    tasting(acc, -.55, .15)
    champagne_stand(acc, 1.1, .35)
    return acc
