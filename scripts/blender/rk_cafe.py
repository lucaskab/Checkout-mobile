"""Café do Mercado + área de convivência (hypermarket yard). Blender space: x ±3 (east +), y ±6.5 (north +, towards
the truck yard); the kiosk closes the north end and serves south onto a pergola terrace; lounge and garden to the
south. Unity: exported with the same axes (x east, z north)."""
import math, random, bmesh
from mathutils import Vector
from rk_core import *
from rk_nature import leafy_tree, leafy_hedge, leafy_vine, leafy_plant, leaf_cluster, flower_bed
from rk_products import box_pack

HW, HL = 3.0, 6.5
COFFEE = "5A3521"
DECK0, DECK1 = -1.4, 3.35


def bistro_chair(acc, p, yaw, seat="T_IK_Wicker"):
    """Parisian bistro chair: bent tube frame, woven seat and a curved back."""
    X = Xf(acc, p, (0, 0, yaw))
    for sx in (-1, 1):
        X.add(tube_bm([(sx * .18, -.18, 0), (sx * .17, -.17, .44)], .012, 6), "C_" + NAVY)
        X.add(tube_bm([(sx * .18, .2, 0), (sx * .17, .18, .44), (sx * .17, .2, .7), (sx * .12, .22, .86)], .012, 6, 2), "C_" + NAVY)
    back = [(math.sin(a) * .17, .2 + .05 * math.cos(a), .86 - .02 * abs(math.sin(a))) for a in [-math.pi / 2 + math.pi * i / 10 for i in range(11)]]
    X.add(tube_bm(back, .013, 6, 1), "C_" + NAVY)
    seat_bm = lathe_bm([(0, 0), (.2, 0), (.21, .02), (.2, .035), (0, .035)], 20, 0)
    uv_box(seat_bm, 3)
    place(seat_bm, (0, 0, .44), scale=(1, .95, 1)); X.add(seat_bm, seat)
    band = [(math.sin(a) * .165, .2 + .045 * math.cos(a), .72) for a in [-math.pi / 2 + math.pi * i / 10 for i in range(11)]]
    for dz in (0, .06):
        X.add(tube_bm([(q[0], q[1], q[2] + dz) for q in band], .018, 6, 1), seat)


def bistro_table(acc, p, n_chairs=2, seed=0):
    x, y, z = p
    # cast iron base: 3 curved feet, a turned column
    for k in range(3):
        a = k * 2 * math.pi / 3 + .5
        tube(acc, [(x, y, z + .12), (x + math.cos(a) * .15, y + math.sin(a) * .15, z + .05), (x + math.cos(a) * .24, y + math.sin(a) * .24, z + .01)], .016, "C_" + NAVY, 6, 2)
    lathe(acc, [(0, 0), (.04, 0), (.03, .08), (.022, .2), (.028, .5), (.02, .62), (.05, .66), (.05, .7)], (x, y, z + .05), "C_" + NAVY, 12, 2)
    lathe(acc, [(0, 0), (.37, 0), (.38, .015), (.37, .035), (0, .035)], (x, y, z + .74), "T_IK_Marble", 28, 1)
    lathe(acc, [(.37, 0), (.382, .018), (.37, .036)], (x, y, z + .74), "C_" + GOLD, 28, 0, cap_top=False, cap_bottom=False)
    rnd = random.Random(seed)
    for i in range(n_chairs):
        a = seed * .6 + i * 2 * math.pi / n_chairs
        cx, cy = x + math.sin(a) * .68, y + math.cos(a) * .68
        bistro_chair(acc, (cx, cy, z), math.degrees(-a))   # seat faces the table
        # coffee on the table in front of each chair
        tx, ty = x + math.sin(a) * .2, y + math.cos(a) * .2
        lathe(acc, [(0, 0), (.06, 0), (.065, .008), (.05, .012), (0, .012)], (tx, ty, z + .775), "C_" + WHITE, 16, 0)
        lathe(acc, [(0, 0), (.03, 0), (.042, .06), (.044, .07)], (tx, ty, z + .787), "C_" + WHITE, 16, 1, cap_top=False)
        lathe(acc, [(0, 0), (.041, 0)], (tx, ty, z + .848), "C_A8703E", 14, 0)
        tube(acc, [(tx + .04, ty, z + .83), (tx + .065, ty, z + .82), (tx + .044, ty, z + .8)], .006, "C_" + WHITE, 5, 2)
    # small vase
    lathe(acc, [(0, 0), (.03, 0), (.04, .05), (.02, .1), (.022, .12)], (x, y, z + .775), "G_Glass", 12, 2, cap_top=False)
    for k in range(3):
        blob(acc, (.025, .025, .02), (x + (k - 1) * .02, y, z + .9 + (k % 2) * .02), "C_" + ("E86A9E" if k % 2 else "F2C23F"), 2, .2, k)


def espresso_machine(acc, x, y, z):
    rbox(acc, (.62, .45, .42), (x, y, z + .21), "T_IK_R_Brushed", .05, 4)
    rbox(acc, (.64, .47, .05), (x, y, z + .445), "C_" + COFFEE, .02, 3)
    rbox(acc, (.5, .02, .12), (x, y - .23, z + .34), "C_" + NAVY, .02, 3)
    for k in range(2):
        gx = x - .13 + k * .26
        lathe(acc, [(0, 0), (.045, 0), (.05, .03), (.03, .05)], (gx, y - .2, z + .28), "C_" + CHROME, 14, 1, rot=(180, 0, 0))
        tube(acc, [(gx, y - .24, z + .24), (gx, y - .36, z + .23)], .011, "C_" + DARK, 8)
        lathe(acc, [(0, 0), (.028, 0), (.035, .055), (.036, .06)], (gx, y - .2, z + .06), "C_" + WHITE, 12, 0, cap_top=False)
    tube(acc, [(x + .26, y - .2, z + .38), (x + .28, y - .26, z + .3), (x + .28, y - .27, z + .16)], .007, "C_" + CHROME, 6, 2)
    for k in range(3):
        lathe(acc, [(0, 0), (.03, 0), (.038, .06), (.04, .065)], (x - .18 + k * .18, y + .05, z + .47), "C_" + WHITE, 12, 0, cap_top=False)
    lathe(acc, [(0, 0), (.022, 0), (.02, .03), (0, .035)], (x - .2, y - .235, z + .34), "C_" + GOLD, 10, 0, rot=(90, 0, 0))
    lathe(acc, [(0, 0), (.022, 0), (.02, .03), (0, .035)], (x + .2, y - .235, z + .34), "C_" + GOLD, 10, 0, rot=(90, 0, 0))
    rbox(acc, (.56, .18, .03), (x, y - .23, z + .02), "C_" + DARK, .01, 2)


def grinder(acc, x, y, z):
    rbox(acc, (.16, .22, .3), (x, y, z + .15), "C_" + NAVY, .04, 4)
    lathe(acc, [(.03, 0), (.08, .05), (.1, .18), (.09, .2)], (x, y, z + .3), "G_Glass", 14, 2, cap_top=False)
    lathe(acc, [(0, 0), (.07, .02), (.09, .1), (0, .12)], (x, y, z + .32), "C_" + COFFEE, 14, 2)
    lathe(acc, [(0, 0), (.095, 0), (.09, .02), (0, .03)], (x, y, z + .5), "C_" + DARK, 14, 1)


def pastry_case(acc, x, y, z, w=.9):
    rbox(acc, (w, .5, .06), (x, y, z + .03), "T_IK_R_WoodDark", .015, 2)
    arc = [(y - .25 + .2 * (1 - math.cos(a)), z + .06 + .36 * math.sin(a)) for a in [k * math.pi / 2 / 6 for k in range(7)]]
    bm = bmesh.new()
    rows = [[bm.verts.new((xx, yy, zz)) for yy, zz in arc] for xx in (x - w / 2 + .02, x + w / 2 - .02)]
    for j in range(len(arc) - 1):
        bm.faces.new((rows[0][j], rows[1][j], rows[1][j + 1], rows[0][j + 1]))
    uv_box(bm); acc.add(bm, "G_Glass")
    rbox(acc, (w - .04, .3, .02), (x, y + .08, z + .42), "G_Glass", .005, 1)
    for s in (-1, 1):
        rbox(acc, (.02, .5, .42), (x + s * (w / 2 - .01), y, z + .24), "T_IK_R_WoodDark", .008, 2)
    for r, zz in enumerate((.08, .25)):
        rbox(acc, (w - .08, .4, .01), (x, y + .02, z + zz), "C_" + CHROME, .003, 1)
        for i in range(4):
            px = x - w / 2 + .14 + i * (w - .28) / 3
            if (i + r) % 2:
                # croissant: curved tapered tube
                pts = [(px - .06 * math.cos(a), y + .02 + .05 * math.sin(a), z + zz + .025) for a in [k * math.pi / 6 for k in range(7)]]
                tube(acc, pts, lambda s: .012 + .02 * math.sin(math.pi * s), "C_D9953E", 8, 2)
            else:
                lathe(acc, [(0, 0), (.07, 0), (.07, .05), (.06, .06), (0, .06)], (px, y + .02, z + zz + .01), "C_" + ("F4A6C1" if r else "6B3E26"), 16, 1)
                lathe(acc, [(0, 0), (.072, 0), (.072, .012), (0, .012)], (px, y + .02, z + zz + .07), "C_" + WHITE, 16, 0)
                blob(acc, (.012, .012, .012), (px, y + .02, z + zz + .09), "C_D74A3C", 1, 0, i)


def cup_sign(acc, x, y, z):
    """Giant coffee cup with saucer and curling steam on the roof."""
    lathe(acc, [(0, 0), (.55, 0), (.6, .02), (.56, .05), (.2, .06)], (x, y, z), "C_" + WHITE, 32, 1)
    lathe(acc, [(.28, .05), (.34, .15), (.42, .45), (.44, .55), (.41, .56)], (x, y, z), "C_" + WHITE, 32, 2, cap_top=False)
    lathe(acc, [(0, .04), (.28, .05)], (x, y, z + .01), "C_" + WHITE, 32, 0)
    lathe(acc, [(0, 0), (.4, 0)], (x, y, z + .52), "C_" + COFFEE, 28, 0)
    lathe(acc, [(.425, .2), (.43, .32)], (x, y, z), "C_" + NAVY, 32, 0, cap_top=False, cap_bottom=False)
    handle = [(x + .41 + .13 * math.sin(a), y, z + .32 + .13 * math.cos(a)) for a in [k * math.pi / 8 for k in range(9)]]
    tube(acc, handle, .04, "C_" + WHITE, 10, 2)
    for i, dx in enumerate((-.12, .06, .2)):
        pts = [(x + dx + .06 * math.sin(t * 5 + i), y + .04 * math.cos(t * 4 + i), z + .6 + t * .55) for t in [k / 10 for k in range(11)]]
        tube(acc, pts, lambda s: .045 * (1 - .6 * s), "C_F7F4EE", 8, 2)


def kiosk(acc, y0):
    """Coffee kiosk from y0 (serving front) to the north end."""
    w, d, h = 5.0, 2.9, 2.75
    yc = y0 + d / 2
    rbox(acc, (w + .1, d + .1, .16), (0, yc, .08), "T_IK_R_StoneWall", .02, 2, uv=1.5)
    # lower walls: vertical timber cladding; upper walls: white plaster; navy corner posts
    rbox(acc, (w, d, 1.0), (0, yc, .66), "T_IK_R_PlanksDark", .02, 2, uv=1.0, rot=(0, 0, 0))
    for sx in (-1, 1):
        rbox(acc, (.2, d, h - 1.16), (sx * (w / 2 - .1), yc, 1.16 + (h - 1.16) / 2), "T_IK_Plaster", .02, 2, uv=1.5)
        rbox(acc, (.16, .16, h + .05), (sx * (w / 2 - .02), y0 + .02, h / 2), "C_" + NAVY, .03, 3)
    rbox(acc, (w, .2, h - 1.16), (0, y0 + d - .1, 1.16 + (h - 1.16) / 2), "T_IK_Plaster", .02, 2, uv=1.5)
    rbox(acc, (w - .36, .2, .42), (0, y0 + .1, h - .21), "T_IK_Plaster", .02, 2, uv=1.5)
    # roof with overhang and gold fascia
    rbox(acc, (w + .4, d + .4, .2), (0, yc, h + .1), "C_" + NAVY, .05, 4)
    for dz in (0, .19):
        for sy in (-1, 1):
            rbox(acc, (w + .44, .03, .03), (0, yc + sy * (d / 2 + .21), h + dz), "C_" + GOLD, .01, 2)
        for sx in (-1, 1):
            rbox(acc, (.03, d + .44, .03), (sx * (w / 2 + .21), yc, h + dz), "C_" + GOLD, .01, 2)
    # serving window: counter ledge, inner bar, machines and cakes
    rbox(acc, (w - .3, .4, .06), (0, y0 - .1, 1.13), "T_IK_R_Wood", .02, 3)
    rbox(acc, (w - .4, .5, .9), (0, y0 + .55, .7), "T_IK_R_Wood", .02, 2)
    rbox(acc, (w - .36, .56, .04), (0, y0 + .55, 1.17), "T_IK_Marble", .01, 2)
    espresso_machine(acc, -.9, y0 + .62, 1.19)
    grinder(acc, -.28, y0 + .7, 1.19)
    pastry_case(acc, .75, y0 + .5, 1.19)
    for i in range(5):
        lathe(acc, [(0, 0), (.035, 0), (.045, .11), (.047, .12)], (-1.95 + i * .1, y0 + .7, 1.19), "C_" + ("F2E3C6" if i % 2 else WHITE), 12, 0, cap_top=False)
    # back shelves with jars of beans and bags of coffee
    for zz in (1.5, 1.85):
        rbox(acc, (3.4, .24, .04), (0, y0 + d - .32, zz), "T_IK_R_Wood", .01, 2)
        for i in range(8):
            px = -1.5 + i * .42
            if i % 2:
                box_pack(acc, (px, y0 + d - .32, zz + .02), .14, .08, .2, "pack_4")
            else:
                lathe(acc, [(0, 0), (.06, 0), (.065, .15), (.045, .18), (.045, .2)], (px, y0 + d - .32, zz + .02), "G_Glass", 14, 2, cap_top=False)
                lathe(acc, [(0, 0), (.058, 0), (.058, .12), (0, .13)], (px, y0 + d - .32, zz + .025), "C_" + COFFEE, 12, 1)
                lathe(acc, [(0, 0), (.05, 0), (.05, .02), (0, .025)], (px, y0 + d - .32, zz + .2), "C_" + GOLD, 12, 0)
    # menu board over the window
    label_panel(acc, 1.8, .5, (0, y0 - .02, 2.28), "coffee_menu", .03, .05)
    # striped awning with scalloped edge
    n = 14
    for k in range(n):
        x = -(w + .2) / 2 + (k + .5) * (w + .2) / n
        col = "C_" + (NAVY if k % 2 else WHITE)
        bm = bmesh.new()
        prof = [(y0 + .02, 2.05), (y0 - .45, 1.9), (y0 - .9, 1.72)]
        rows = [[bm.verts.new((xx, yy, zz)) for yy, zz in prof] for xx in (x - (w + .2) / n / 2, x + (w + .2) / n / 2)]
        for j in range(2):
            bm.faces.new((rows[0][j], rows[1][j], rows[1][j + 1], rows[0][j + 1]))
        uv_box(bm); acc.add(bm, col)
        pts = [(x + math.cos(a) * (w + .2) / n / 2, 1.72 - math.sin(a) * .08) for a in [math.pi * i / 8 for i in range(9)]]
        vb = bmesh.new()
        fv = [vb.verts.new((px, y0 - .905, pz)) for px, pz in pts]
        bv = [vb.verts.new((px, y0 - .89, pz)) for px, pz in pts]
        vb.faces.new(fv); vb.faces.new(list(reversed(bv)))
        for j in range(len(pts)):
            vb.faces.new((fv[j], fv[(j + 1) % len(pts)], bv[(j + 1) % len(pts)], bv[j]))
        bmesh.ops.recalc_face_normals(vb, faces=vb.faces); uv_box(vb); acc.add(vb, col)
    tube(acc, [(-(w + .2) / 2, y0 - .9, 1.72), ((w + .2) / 2, y0 - .9, 1.72)], .014, "C_" + GOLD, 8)
    for sx in (-1, 1):
        tube(acc, [(sx * (w / 2 - .1), y0 - .88, 1.72), (sx * (w / 2 - .1), y0, 2.35)], .012, "C_" + GOLD, 6)
    # pendant lamps under the awning
    for x in (-1.6, -.55, .55, 1.6):
        tube(acc, [(x, y0 - .3, 1.95), (x, y0 - .3, 1.72)], .004, "C_" + DARK, 4)
        lathe(acc, [(0, 0), (.11, 0), (.09, .07), (.03, .11), (0, .12)], (x, y0 - .3, 1.6), "C_" + GOLD, 16, 1)
        lathe(acc, [(0, 0), (.09, 0)], (x, y0 - .3, 1.595), "E_FFE6A8", 14, 0)
    # roof sign
    rbox(acc, (3.1, .12, .62), (-.6, y0 + .25, h + .6), "C_" + NAVY, .06, 4)
    rbox(acc, (3.16, .13, .04), (-.6, y0 + .25, h + .3), "C_" + GOLD, .015, 2)
    rbox(acc, (3.16, .13, .04), (-.6, y0 + .25, h + .9), "C_" + GOLD, .015, 2)
    text(acc, "CAFÉ DO MERCADO", .24, (-.6, y0 + .18, h + .6), "C_" + GOLDL, .035, bevel=.005)
    for x in (-1.9, .7):
        tube(acc, [(x, y0 + .3, h + .2), (x, y0 + .3, h + .32)], .025, "C_" + DARK, 6)
    cup_sign(acc, 1.55, y0 + 1.4, h + .2)
    # side door, lamp, coffee sacks
    rbox(acc, (.05, .9, 2.0), (w / 2 + .01, y0 + 1.8, 1.16), "C_" + "1F9A8E", .02, 3)
    blob(acc, (.03, .03, .03), (w / 2 + .05, y0 + 1.45, 1.05), "C_" + GOLD, 2, 0, 0)
    for i in range(3):
        blob(acc, (.28, .22, .2), (w / 2 + .32, y0 + .5 + (i % 2) * .5, .22 + (i // 2) * .32), "T_IK_Wicker", 3, .12, i)


def sofa(acc, p, yaw):
    X = Xf(acc, p, (0, 0, yaw))
    for part, key in ((((1.9, .78, .36), (0, .0, .22), .08), "T_IK_R_Wood"), (((1.8, .66, .16), (0, -.03, .45), .07), "T_IK_R_Fabric"),
                      (((1.9, .18, .5), (0, .33, .6), .08), "T_IK_R_Wood"), (((1.76, .16, .42), (0, .24, .72), .08), "T_IK_R_Fabric")):
        (size, loc, r), k = part, key
        bm = rbox_bm(size, r, 4); uv_box(bm, 2); place(bm, loc); X.add(bm, k)
    for sx in (-1, 1):
        bm = rbox_bm((.14, .74, .56), .06, 4); uv_box(bm, 2); place(bm, (sx * .95, 0, .3)); X.add(bm, "T_IK_R_Wood")
        bm = rbox_bm((.42, .14, .38), .07, 4); uv_box(bm, 2); place(bm, (sx * .45, .18, .78), (-12, 0, sx * 6)); X.add(bm, "T_IK_R_FabricMustard")
    for sx in (-1, 1):
        for sy in (-1, 1):
            lathe_ = lathe_bm([(0, 0), (.025, 0), (.03, .06)], 10, 0); place(lathe_, (sx * .85, sy * .3, 0)); X.add(lathe_, "C_" + DARK)


def armchair(acc, p, yaw):
    """Rattan lounge armchair: woven tub base, a curved woven back, rounded arms and a mustard cushion."""
    X = Xf(acc, p, (0, 0, yaw))
    for size, loc, r, key in (((.76, .74, .34), (0, 0, .19), .09, "T_IK_Wicker"), ((.62, .6, .12), (0, -.03, .42), .06, "T_IK_R_FabricMustard"),
                              ((.74, .16, .42), (0, .3, .6), .08, "T_IK_Wicker"), ((.56, .12, .3), (0, .22, .62), .06, "T_IK_R_FabricMustard")):
        bm = rbox_bm(size, r, 4); uv_box(bm, 3); place(bm, loc); X.add(bm, key)
    for sx in (-1, 1):
        bm = rbox_bm((.12, .7, .22), .055, 4); uv_box(bm, 3); place(bm, (sx * .33, -.01, .45)); X.add(bm, "T_IK_Wicker")


def build(name="plaza-cafe"):
    acc = Acc(name)
    # Ground: pavers with a stone kerb; timber deck under the pergola, with a step.
    rbox(acc, (2 * HW, 2 * HL, .06), (0, 0, .03), "T_IK_Paver", .01, 1, uv=.8)
    for sx in (-1, 1):
        rbox(acc, (.12, 2 * HL, .1), (sx * (HW - .06), 0, .05), "T_IK_R_StoneWall", .02, 2, uv=2)
    rbox(acc, (2 * HW, .12, .1), (0, -HL + .06, .05), "T_IK_R_StoneWall", .02, 2, uv=2)
    dz = DECK1 - DECK0
    rbox(acc, (2 * HW - .5, dz, .14), (0, (DECK0 + DECK1) / 2, .13), "T_IK_R_Planks", .015, 2, uv=.5)
    rbox(acc, (1.6, .32, .08), (0, DECK0 - .2, .08), "T_IK_R_PlanksDark", .015, 2, uv=.5)
    # Pergola: posts, beams, rafters, climbing vines and strings of bulbs.
    posts = [(x, y) for x in (-HW + .45, HW - .45) for y in (DECK0 + .2, (DECK0 + DECK1) / 2, DECK1 - .1)]
    for x, y in posts:
        rbox(acc, (.16, .16, 2.75), (x, y, .2 + 1.375), "T_IK_R_WoodDark", .025, 3, uv=1)
        rbox(acc, (.26, .26, .12), (x, y, .26), "T_IK_R_StoneWall", .02, 2)
        # vine climbing the post
        pts = [(x + .1 * math.cos(t * 5), y + .1 * math.sin(t * 5), .3 + t * 2.7) for t in [k / 14 for k in range(15)]]
        leafy_vine(acc, pts, int(x * 10 + y * 7))
    for x in (-HW + .45, HW - .45):
        rbox(acc, (.14, dz + .5, .24), (x, (DECK0 + DECK1) / 2, 2.95), "T_IK_R_WoodDark", .02, 3, uv=1)
    for i in range(13):
        y = DECK0 - .1 + i * (dz + .2) / 12
        rbox(acc, (2 * HW - .4, .07, .1), (0, y, 3.1), "T_IK_R_Wood", .015, 2, uv=1)
    # vines running along the beams and rafters, trailing a little over the edges
    rnd = random.Random(5)
    for x in (-HW + .45, HW - .45):
        pts = [(x + .08 * math.sin(k * 1.3), DECK0 - .2 + k * (dz + .4) / 12, 3.1 + .05 * math.sin(k * 2.1)) for k in range(13)]
        leafy_vine(acc, pts, 40 + int(x), every=.07, size=1.2)
    for i in range(0, 13, 3):
        y = DECK0 - .1 + i * (dz + .2) / 12
        pts = [(-HW + .5 + k * (2 * HW - 1) / 10, y + .04 * math.sin(k), 3.17) for k in range(11)]
        leafy_vine(acc, pts, 60 + i, every=.1, size=1.1)
        for s in (-1, 1):  # a trailing strand hanging off the beam
            xh = s * (HW - .45)
            leafy_vine(acc, [(xh, y, 3.05), (xh + s * .05, y + .05, 2.75), (xh + s * .03, y, 2.45)], 80 + i + s, every=.08)
    for x in (-1.5, 0, 1.5):
        n = 9
        pts = [(x, DECK0 + dz * t, 3.0 - .28 * math.sin(math.pi * t)) for t in [k / n for k in range(n + 1)]]
        tube(acc, pts, .005, "C_" + DARK, 4, 2)
        for q in pts[1:-1]:
            lathe(acc, [(0, 0), (.02, .01), (.03, .05), (.022, .08), (0, .09)], (q[0], q[1], q[2] - .1), "E_FFE6A8", 10, 2)
            lathe(acc, [(0, 0), (.014, 0), (.014, .02)], (q[0], q[1], q[2] - .02), "C_" + DARK, 8, 0)
    # Terrace: bistro tables and a long communal table with benches.
    # tables kept clear of the hedges and pergola posts (chairs included)
    for i, (x, y, n) in enumerate(((-1.2, -.5, 3), (1.1, -.55, 2), (-1.2, 1.35, 3))):
        bistro_table(acc, (x, y, .2), n, i)
    X = Xf(acc, (1.4, 1.9, .2), (0, 0, 90))
    for part in (((2.2, .72, .06), (0, 0, .74), "T_IK_R_Wood"),):
        bm = rbox_bm(part[0], .02, 3); uv_box(bm, 1); place(bm, part[1]); X.add(bm, part[2])
    for sx in (-.9, .9):
        X.add(tube_bm([(sx, -.3, 0), (sx, 0, .72), (sx, .3, 0)], .03, 8, 1), "C_" + NAVY)
    for sy in (-.62, .62):
        bm = rbox_bm((2.1, .3, .05), .02, 3); uv_box(bm, 1); place(bm, (0, sy, .44)); X.add(bm, "T_IK_R_Wood")
        for sx in (-.85, .85):
            bm = rbox_bm((.05, .26, .42), .015, 2); uv_box(bm); place(bm, (sx, sy, .21)); X.add(bm, "C_" + NAVY)
    for k in range(4):
        leafy_plant(Xf(acc, (1.4, 1.9, .2), (0, 0, 90)), (-.7 + k * .47, 0, .77), .45, k)
    # The kiosk closes the north end.
    kiosk(acc, HL - 2.95)
    # Lounge on an outdoor rug (clear of the west hedge), a floor lamp, and a tree with a ring bench.
    LX, LY = -.95, -3.05
    rbox(acc, (2.5, 1.9, .012), (LX, LY, .066), "T_IK_R_Fabric", .004, 1, uv=1.5)
    sofa(acc, (LX, LY + .6, .06), 0)            # faces the coffee table (south)
    armchair(acc, (LX - .98, LY - .3, .06), 80)  # both armchairs turned in towards the table
    armchair(acc, (LX + .98, LY - .3, .06), -80)
    rbox(acc, (.9, .5, .05), (LX, LY - .15, .42), "T_IK_R_WoodDark", .02, 3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(acc, [(LX + sx * .38, LY - .15 + sy * .18, .06), (LX + sx * .38, LY - .15 + sy * .18, .4)], .02, "C_" + NAVY, 6)
    leafy_plant(acc, (LX + .15, LY - .2, .445), .5, 9)
    # floor lamp beside the sofa: weighted base, slim pole, linen drum shade with a warm bulb
    lx, ly = LX + 1.2, LY + .75
    lathe(acc, [(0, 0), (.17, 0), (.18, .015), (.15, .04), (.03, .05), (0, .05)], (lx, ly, .06), "C_" + NAVY, 24, 1)
    tube(acc, [(lx, ly, .1), (lx, ly, 1.45)], .012, "C_" + GOLD, 8)
    lathe(acc, [(.2, 0), (.2, .3)], (lx, ly, 1.3), "T_IK_R_FabricMustard", 28, 0, cap_top=False, cap_bottom=False)
    for zz in (1.3, 1.6):
        lathe(acc, [(.195, 0), (.205, .01)], (lx, ly, zz), "C_" + GOLD, 28, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(0, 0), (.05, .02), (.055, .07), (.03, .11), (0, .12)], (lx, ly, 1.36), "E_FFE9B0", 14, 1)
    for k in range(3):
        a = k * 2.094
        tube(acc, [(lx, ly, 1.47), (lx + math.cos(a) * .19, ly + math.sin(a) * .19, 1.58)], .004, "C_" + GOLD, 4)
    TX, TY = 1.22, -2.95
    leafy_tree(acc, (TX, TY, .06), 3.4, 1.3, 3)
    lathe(acc, [(0, 0), (.6, 0), (.62, .05), (.62, .4), (.66, .43), (.66, .46), (.52, .46), (0, .44)], (TX, TY, .06), "T_IK_R_StoneWall", 32, 1)
    # continuous ring bench hugging the planter: slatted timber seat on a navy skirt
    lathe(acc, [(.66, 0), (.98, 0), (.98, .4), (.66, .4)], (TX, TY, .06), "C_" + NAVY, 40, 0, cap_top=False, cap_bottom=False)
    for k in range(4):
        r0 = .66 + k * .085
        lathe(acc, [(r0 + .005, 0), (r0 + .075, 0), (r0 + .075, .045), (r0 + .005, .045)], (TX, TY, .46), "T_IK_R_Wood", 40, 0, cap_top=False, cap_bottom=False)
    # Hedges: west side (staff walkway), east side (street) with the entrance gap, and the south end facing
    # the shop's back wall closed off.
    EY0, EY1 = -5.75, -4.15                       # entrance gap on the east (sidewalk) side
    leafy_hedge(acc, (-HW + .3, -6.1, 0), (-HW + .3, DECK1 + .1, 0), .5, .55, 1)
    leafy_hedge(acc, (HW - .3, EY1 + .05, 0), (HW - .3, DECK1 + .1, 0), .5, .55, 2)
    leafy_hedge(acc, (HW - .3, -HL + .2, 0), (HW - .3, EY0 - .05, 0), .5, .55, 3)
    # South end: two flower beds and the recycling bins against the shop side.
    flower_bed(acc, (-1.55, -HL + .55, 0), (2.2, .8), 3)
    flower_bed(acc, (.95, -HL + .55, 0), (2.2, .8), 5)
    for i, c in enumerate(("2E86DE", "F2C23F", "27AE60", "D74A3C")):
        rbox(acc, (.4, .34, .8), (-2.3, -5.35 + i * .38, .46), "C_" + c, .06, 4)
        rbox(acc, (.43, .37, .06), (-2.3, -5.35 + i * .38, .88), "C_" + c, .03, 3)
        rbox(acc, (.06, .2, .02), (-2.1, -5.35 + i * .38, .9), "C_" + DARK, .01, 2)
    # Entrance arch on the east side, facing the sidewalk, with its sign readable from the street.
    ey = (EY0 + EY1) / 2
    ex = HW - .3
    arch = [(ex, ey + math.cos(a) * .8, 2.3 + math.sin(a) * .35) for a in [math.pi * i / 12 for i in range(13)]]
    for sy in (-1, 1):
        tube(acc, [(ex, ey + sy * .8, 0), (ex, ey + sy * .8, 2.3)], .045, "C_" + NAVY, 10)
        lathe(acc, [(0, 0), (.08, 0), (.08, .05), (0, .06)], (ex, ey + sy * .8, 0), "C_" + GOLD, 12, 0)
        leafy_vine(acc, [(ex + .06 + .05 * math.cos(k * 1.4), ey + sy * (.8 + .06 * math.sin(k * 1.4)), .1 + k * .3) for k in range(9)], 90 + sy, every=.07, size=1.2)
    tube(acc, arch, .045, "C_" + NAVY, 10, 1)
    rbox(acc, (.06, 1.75, .36), (ex + .05, ey, 2.34), "C_" + GOLD, .05, 4)
    rbox(acc, (.07, 1.67, .3), (ex + .06, ey, 2.34), "C_" + NAVY, .05, 4)
    text(acc, "CONVIVÊNCIA", .14, (ex + .1, ey, 2.34), "C_" + GOLDL, .025, rot=(0, 0, 90), bevel=.004)
    # welcome mat of pavers leading in, and a bike rack just inside, along the east hedge
    rbox(acc, (1.2, 1.4, .012), (ex - .5, ey, .066), "T_IK_R_StoneWall", .004, 1, uv=2)
    for k in range(5):  # bike rack
        y = -3.7 + k * .36
        pts = [(HW - .6, y - .12, 0)] + [(HW - .6, y + math.cos(math.radians(a)) * .12, .55 + math.sin(math.radians(a)) * .12) for a in range(180, -1, -30)] + [(HW - .6, y + .12, 0)]
        tube(acc, pts, .02, "C_" + NAVY, 8, 1)
    for x, y in ((-2.15, -1.62), (HW - .3, DECK1 + .4)):
        lathe(acc, [(0, 0), (.18, 0), (.18, .08), (.1, .14), (.07, .4), (0, .4)], (x, y, .06), "C_" + NAVY, 16, 1)
        tube(acc, [(x, y, .4), (x, y, 3.0)], .045, "C_" + NAVY, 10)
        lathe(acc, [(.06, 0), (.16, .12), (.16, .42), (.2, .46), (.02, .62), (0, .62)], (x, y, 3.0), "C_" + NAVY, 16, 1)
        lathe(acc, [(.07, 0), (.14, .12), (.14, .4), (0, .4)], (x, y, 3.03), "E_FFE6A8", 16, 0)
    return acc
