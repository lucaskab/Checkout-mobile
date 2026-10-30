"""Evoluções dos móveis (fixture tiers) — concept showcase, phase 1 (not imported into Unity yet).

Two fixtures in all their tiers, built with the Realistic Kit helpers (rk_core / rk_products):
  * Prateleira / gôndola  T1 estante de madeira pequena -> T2 estante de madeira grande -> T3 gôndola de metal
                          -> T4 gôndola dupla iluminada (vidro + LED)
  * Caixa                 T1 caixinha no balcão de madeira -> T2 caixa registradora clássica -> T3 caixa com esteira
                          e leitor -> T4 caixa premium (inox, vidro, LED, tela dupla, carrossel de sacolas)
Each tier is SMALLER than today's 1.9 m fixtures at the start and grows with the tiers (footprints on the 0.25 m
build grid are in TIERS below). Run inside Blender (Blender MCP or the Text editor):

    exec(open(REPO + "/scripts/blender/fixture_tiers.py").read(), {"__name__": "__main__", "REPO": REPO})

Modelling space and material contract are rk_core's (front/customers on -Y, C_/E_/G_Glass/T_IK_ material names so
CheckoutInteriorKitBuilder.KitRemap and CheckoutMarketPaint.Classify understand them):
  * navy parts: flat C_1D2B4F / C_2E4A7D or the T_IK_V2_PaintNavy texture (WholeNavy) -> repainted by "Cores do mercado"
  * gold trims: flat C_D3A53D (thin trims only) -> repainted as the accent colour
  * wood, steel, glass, LED (E_), products (T_FT_Labels: name contains "Labels") -> never repainted
No written words anywhere: product labels use FT_Labels_albedo.png, the textless twin of IK_Labels (pictograms only);
sign plates are blank for the game to write on.
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix

REPO = globals().get("REPO") or "/Users/lucas-furini/repos/checkout"
sys.path.insert(0, os.path.join(REPO, "scripts", "blender"))
import rk_core
import rk_products
ASSETS = os.path.join(REPO, "unity", "CheckoutSimulator", "Assets")
rk_core.TEX = os.path.join(ASSETS, "Art", "Interior", "Textures")
rk_core.FONT = os.path.join(ASSETS, "Resources", "CheckoutDesktop", "Fonts", "Fredoka_700Bold.ttf")
ART = os.path.join(REPO, "unity", "CheckoutSimulator", "ArtSource", "fixture_tiers")
QA = os.path.join(REPO, "unity", "CheckoutSimulator", "Temp", "qa", "fixture_tiers")
from rk_core import Acc, Xf, rbox, rbox_bm, lathe, lathe_bm, tube, blob, blob_bm, panel_bm, frame_bm, place, uv_box, text, material, srgb
from rk_products import pet_bottle, water_bottle, can, carton, box_pack, chip_bag, longneck, wine_bottle

# ------------------------------------------------------------------------------------------------ palette (brand)
NAVY, BLUE, CREAM, GOLD = "1D2B4F", "2E4A7D", "F4EBD8", "D3A53D"
WHITE, INK, STEEL, CHROME = "FBF8F1", "232A33", "C9D2D6", "DCE3E8"
C = lambda h: "C_" + h
PAINT_NAVY, WOOD, PLANKS, WOOD_L, WOOD_D = "T_IK_V2_PaintNavy", "T_IK_R_Wood", "T_IK_R_Planks", "T_IK_WoodLight", "T_IK_R_WoodDark"
BRUSHED, PEG, CRATE, WICKER, BELT, MARBLE = "T_IK_R_Brushed", "T_IK_Pegboard", "T_IK_Crate", "T_IK_Wicker", "T_IK_Belt", "T_IK_Marble"
LED, LED_COOL, GLASS = "E_FFE6B8", "E_CFEFFF", "G_Glass"
LAB = "T_FT_Labels"

# Footprint (x width, y depth) in metres on the 0.25 m build grid, with the cashier's side for the checkouts.
TIERS = {
    "shelf": [
        ("T1", "Estante de madeira", 1.00, 0.50, 1.45),
        ("T2", "Estante grande de madeira", 1.50, 0.50, 1.75),
        ("T3", "Gôndola de metal", 2.00, 0.75, 1.88),
        ("T4", "Gôndola iluminada", 2.50, 1.00, 2.08),
    ],
    "checkout": [
        ("T1", "Caixinha no balcão", 1.25, 1.25, 1.10),
        ("T2", "Caixa registradora", 1.75, 1.50, 1.30),
        ("T3", "Caixa com esteira", 2.50, 1.75, 2.10),
        ("T4", "Caixa premium", 3.00, 1.75, 2.20),
    ],
}


def setup_materials():
    """Labels atlas + a little more sheen on the metals and stone (preview only; Unity uses KitRemap)."""
    m = bpy.data.materials.get(LAB) or bpy.data.materials.new(LAB)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    t = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(ART, "textures", "FT_Labels_albedo.png"), check_existing=True)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = .45
    rk_core.LAB = LAB
    rk_products.LAB = LAB
    rk_core.METALLIC.add(C(GOLD))
    for key, metal, rough in ((BRUSHED, .75, .32), ("T_IK_V2_Chrome", .9, .18), (MARBLE, 0, .22), (C(GOLD), .8, .3), (C(CHROME), .9, .15)):
        mm = material(key)
        bb = mm.node_tree.nodes.get("Principled BSDF")
        bb.inputs["Metallic"].default_value = metal
        bb.inputs["Roughness"].default_value = rough
    g = material(GLASS)
    g.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value = .18
    for key, s in ((LED, 4.0), (LED_COOL, 3.0)):
        material(key).node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = s


# ------------------------------------------------------------------------------------------------ small helpers
def side_panel(acc, x, depth, h, t, r, key, y=0, z0=0):
    """Rounded board standing in the YZ plane (a shelf side)."""
    bm, _ = panel_bm(depth, h, t, r, 5)
    uv_box(bm)
    place(bm, (x, y, z0 + h / 2), (0, 0, 90))
    acc.add(bm, key)


def plate(acc, w, h, loc, key, t=.02, r=.04, rot=(0, 0, 0)):
    bm, _ = panel_bm(w, h, t, r, 5)
    uv_box(bm)
    place(bm, loc, rot)
    acc.add(bm, key)


def open_box(acc, w, d, h, loc, key, t=.012, r=.006, uv=1.0):
    """Crate / basket: floor and four walls."""
    x, y, z = loc
    rbox(acc, (w, d, t), (x, y, z + t / 2), key, r, 1, uv=uv)
    for s in (-1, 1):
        rbox(acc, (w, t, h), (x, y + s * (d / 2 - t / 2), z + h / 2), key, r, 1, uv=uv)
        rbox(acc, (t, d - 2 * t, h), (x + s * (w / 2 - t / 2), y, z + h / 2), key, r, 1, uv=uv)


def jar(acc, loc, label="pack_9", glass="D74A3C", lid="E0B040", grp="Body", h=.15):
    x, y, z = loc
    k = h / .15
    lathe(acc, [(0, 0), (.042, 0), (.045, .02 * k), (.045, .11 * k), (.036, .14 * k), (.036, .15 * k)], loc, C(glass), 8, 0, cap_top=False, grp=grp)
    lathe(acc, [(.046, .03 * k), (.046, .09 * k)], loc, LAB, 8, 0, uv_cell=label, u_rep=2, v_range=(.03 * k, .09 * k), cap_top=False, cap_bottom=False, grp=grp)
    lathe(acc, [(.039, 0), (.039, .025), (0, .026)], (x, y, z + .15 * k), C(lid), 8, 0, grp=grp, cap_bottom=False)


# ---- light products: same silhouettes and labels as rk_products, fewer sides (the game camera is 3-6 m away)
def pet_bottle(acc, loc, h=.30, r=.036, liquid="C_4A1C10", label="soda_0", cap="C_D74A3C", grp="Body", seg=8):
    prof = [(0, 0), (r * .8, 0), (r, h * .06), (r, h * .6), (r * .55, h * .79), (r * .35, h * .91)]
    lathe(acc, prof, loc, liquid, seg, 0, grp=grp, cap_top=False)
    lathe(acc, [(r * 1.02, h * .26), (r * 1.02, h * .52)], loc, LAB, seg, 0, grp=grp, uv_cell=label, u_rep=2, v_range=(h * .26, h * .52), cap_top=False, cap_bottom=False)
    lathe(acc, [(r * .4, h * .9), (r * .4, h), (0, h)], loc, cap, 6, 0, grp=grp, cap_bottom=False)


def can(acc, loc, r=.033, h=.122, label="can_0", grp="Body", seg=8):
    lathe(acc, [(r * .8, 0), (r, h * .06), (r, h * .92), (r * .85, h)], loc, LAB, seg, 0, grp=grp, uv_cell=label, u_rep=2, v_range=(0, h), cap_top=False, cap_bottom=False)
    lathe(acc, [(r * .86, h * .995), (0, h * .995)], loc, C(CHROME), seg, 0, grp=grp, cap_top=False, cap_bottom=False)


def chip_bag(acc, loc, w=.16, h=.22, d=.06, label="pack_6", grp="Body"):
    box_pack(acc, loc, w, d, h, label, grp, r=min(d * .45, .028))


def coin(acc, loc, key, r=.012):
    lathe(acc, [(0, 0), (r, 0), (r, .003), (0, .003)], loc, key, 10, 0)


def fills_for(x, L):
    return "Anim Fill %d" % min(3, max(0, int((x + L / 2) / (L / 4))))


def stock(acc, kind, x0, x1, side, front, back, z, avail, seed=0, L=None, grp=None):
    """Fills one shelf level between x0..x1: front = distance of the shelf lip from the spine plane along `side`
    (side -1 = customers on -Y), back = distance of the back stop. Rows go from the lip backwards."""
    rnd = random.Random(seed)
    L = L or (x1 - x0)
    x = x0 + .02
    k = 0
    tp = kind[0]
    while True:
        g = grp or fills_for(x, L)
        if tp == "box":
            _, w, d, h, labs = kind
            h = min(h, avail * .92)
            if x + w > x1:
                break
            rows = max(1, int((front - back - .02) / (d + .004)))
            for row in range(rows):
                box_pack(acc, (x + w / 2, side * (front - .015 - d / 2 - row * (d + .004)), z), w, d, h, labs[k % len(labs)], g, 0)
            x += w + .006
        elif tp == "bag":
            labs = kind[1]
            w = .15
            if x + w > x1:
                break
            for row in range(max(1, min(3, int((front - back) / .11)))):
                chip_bag(acc, (x + w / 2, side * (front - .05 - row * .11), z), w, min(.24, avail * .88), .07, labs[k % len(labs)], g)
            x += w + .006
        elif tp == "jar":
            _, labs, glass, lid = kind
            r = .045
            if x + 2 * r > x1:
                break
            for row in range(max(1, int((front - back - .02) / (2 * r + .004)))):
                for st in range(2 if avail > .36 else 1):
                    jar(acc, (x + r, side * (front - .015 - r - row * (2 * r + .006)), z + st * .168), labs[k % len(labs)], glass[k % len(glass)], lid, g)
            x += 2 * r + .006
        elif tp == "bottle":
            _, labs, liquids, cap = kind
            r = .034
            if x + 2 * r > x1:
                break
            h = min(avail * .93, .31)
            for row in range(max(1, int((front - back - .02) / (2 * r + .004)))):
                pet_bottle(acc, (x + r, side * (front - .015 - r - row * (2 * r + .004)), z), h, r, C(liquids[k % len(liquids)]), labs[k % len(labs)], C(cap), g, 10)
            x += 2 * r + .005
        elif tp == "carton":
            labs = kind[1]
            w = .075
            if x + w > x1:
                break
            h = min(avail * .93, .25)
            for row in range(max(1, int((front - back - .02) / (w + .004)))):
                carton(acc, (x + w / 2, side * (front - .015 - w / 2 - row * (w + .004)), z), w, w, h, labs[k % len(labs)], g)
            x += w + .005
        elif tp == "can":
            labs = kind[1]
            r = .033
            if x + 2 * r > x1:
                break
            for row in range(max(1, int((front - back - .02) / (2 * r + .004)))):
                for st in range(min(3, max(1, int(avail / .13)))):
                    can(acc, (x + r, side * (front - .015 - r - row * (2 * r + .004)), z + st * .124), r, .122, labs[(k + st) % len(labs)], g)
            x += 2 * r + .004
        k += 1


def price_tags(acc, x0, x1, y, z, key=C(WHITE), n=None, side=-1, w=.07):
    """Blank tags on a price rail (the game writes the price)."""
    n = n or max(2, int((x1 - x0) / .32))
    for i in range(n):
        x = x0 + (i + .5) * (x1 - x0) / n
        rbox(acc, (w, .004, .03), (x, y + side * .003, z), key, .003, 1)


THEMES = {
    "mercearia": [("box", .12, .07, .26, ["pack_0", "pack_1"]), ("jar", ["pack_9", "pack_10"], ["D74A3C", "E8B23A"], "1D2B4F"),
                  ("bag", ["pack_6", "pack_15", "pack_14"]), ("box", .1, .07, .17, ["pack_4", "pack_3", "pack_7"]),
                  ("bottle", ["pack_8", "pack_8"], ["C9A227", "B58B1C"], "2E7D32"), ("carton", ["juice_0", "milk", "juice_1"])],
}


# ================================================================================================ SHELF TIERS
def shelf_t1(acc):
    """Estante de madeira: 1.0 x 0.5 m, 3 levels, navy painted sides, natural wood boards, slatted back,
    two wicker baskets at the bottom and a blank chalk slate hanging on the side."""
    W, D, H = .96, .42, 1.45
    y0 = .02  # body sits slightly back in its 0.5 m cell
    for s in (-1, 1):
        side_panel(acc, s * (W / 2 - .018), D, H, .036, .05, PAINT_NAVY, y0)
        # little turned feet under the sides
        for fy in (-1, 1):
            lathe(acc, [(0, 0), (.022, 0), (.026, .015), (.02, .03), (.024, .045), (0, .046)], (s * (W / 2 - .018), y0 + fy * (D / 2 - .04), -.0), C("6B4128"), 10, 0)
    inner = W - .072
    levels = [.12, .55, .98]
    for z in levels:
        rbox(acc, (inner, D - .02, .03), (0, y0, z), WOOD, .008, 2)
        rbox(acc, (inner, .014, .04), (0, y0 - D / 2 + .012, z + .012), C(CREAM), .005, 1)
        price_tags(acc, -inner / 2, inner / 2, y0 - D / 2 + .003, z + .012, C(WHITE), 3)
    rbox(acc, (W + .03, D + .03, .035), (0, y0, H + .017), WOOD, .012, 2)
    rbox(acc, (W + .03, .008, .01), (0, y0 - (D + .03) / 2 - .002, H + .017), C(GOLD), .003, 1)
    for z in (.32, .75, 1.18):
        rbox(acc, (inner, .018, .15), (0, y0 + D / 2 - .012, z), PLANKS, .005, 1, uv=1.2)
    rbox(acc, (inner, .02, .1), (0, y0 - D / 2 + .03, .06), WOOD_D, .006, 1)
    # bottom: two wicker baskets with bags
    for bx in (-.22, .22):
        open_box(acc, .4, .33, .17, (bx, y0 - .02, .135), "T_IK_Wicker", .014, .006, 3)
        for k in range(3):
            chip_bag(acc, (bx - .12 + k * .12, y0 - .06 + (k % 2) * .06, .15), .12, .19, .06, ["pack_6", "pack_15", "pack_14"][k], "Anim Fill %d" % (0 if bx < 0 else 3))
    stock(acc, ("jar", ["pack_9", "pack_10", "pack_8"], ["D74A3C", "E8B23A", "6E8B3D"], NAVY), -inner / 2, inner / 2, -1, D / 2 - y0, D / 2 - y0 - .17, .55 + .015, .4, 1, L=inner)
    stock(acc, ("box", .12, .075, .3, ["pack_0", "pack_2", "pack_1"]), -inner / 2, inner / 2, -1, D / 2 - y0, D / 2 - y0 - .17, .98 + .015, .4, 2, L=inner)
    # hanging chalk slate (blank, the game writes on it) with twine
    sx = W / 2 + .004
    frame = frame_bm(.24, .18, .016, .02, .02)
    place(frame, (sx + .002, y0 - .05, 1.12), (0, 0, 90)); acc.add(frame, WOOD)
    plate(acc, .21, .15, (sx, y0 - .05, 1.12), C("2F3A40"), .008, .015, (0, 0, 90))
    tube(acc, [(sx + .004, y0 - .14, 1.21), (sx + .006, y0 - .05, 1.33), (sx + .004, y0 + .04, 1.21)], .003, C("C9A06A"), 5)
    # a small potted herb on top (warmth)
    lathe(acc, [(0, 0), (.05, 0), (.065, .1), (.07, .11), (0, .11)], (-.3, y0, H + .035), "T_IK_Terracotta", 12, 1)
    for k in range(7):
        a = k * 2.4
        blob(acc, (.03, .02, .045), (-.3 + .03 * math.cos(a), y0 + .03 * math.sin(a), H + .17 + .02 * (k % 3)), C("4E9A3A" if k % 2 else "6DB84A"), 2, .2, k)


def shelf_t2(acc):
    """Estante grande de madeira: 1.5 x 0.5 m, 4 levels, wood corner posts + navy side panels, plank back,
    navy crown with a gold-trimmed blank plaque, cream price rails, crates at the bottom."""
    W, D, H = 1.46, .44, 1.62
    y0 = .02
    for s in (-1, 1):
        for fy in (-1, 1):
            rbox(acc, (.055, .055, H + .05), (s * (W / 2 - .028), y0 + fy * (D / 2 - .028), (H + .05) / 2), WOOD, .012, 2)
        rbox(acc, (.02, D - .1, H - .1), (s * (W / 2 - .028), y0, H / 2 + .02), PAINT_NAVY, .006, 1)
    inner = W - .1
    rbox(acc, (inner, .02, H - .1), (0, y0 + D / 2 - .03, H / 2 + .02), PLANKS, .005, 1, uv=1.4)
    levels = [.14, .52, .9, 1.28]
    for z in levels:
        rbox(acc, (inner + .04, D - .05, .032), (0, y0, z), WOOD, .008, 2)
        rbox(acc, (inner + .04, .016, .045), (0, y0 - D / 2 + .028, z + .014), C(CREAM), .006, 1)
        price_tags(acc, -inner / 2, inner / 2, y0 - D / 2 + .018, z + .014, C(WHITE), 4)
    rbox(acc, (W + .04, D + .02, .04), (0, y0, H + .03), WOOD, .014, 2)
    # kick plinth
    rbox(acc, (inner + .04, .03, .12), (0, y0 - D / 2 + .04, .06), PAINT_NAVY, .008, 2)
    rbox(acc, (inner + .04, .006, .01), (0, y0 - D / 2 + .024, .118), C(GOLD), .003, 1)
    # crown: arched navy board with gold trim and a blank cream plaque for the category pictogram
    plate(acc, W + .02, .3, (0, y0 - D / 2 + .05, H + .2), PAINT_NAVY, .03, .12)
    fr = frame_bm(W - .04, .26, .012, .1, .014)
    place(fr, (0, y0 - D / 2 + .033, H + .2)); acc.add(fr, C(GOLD))
    plate(acc, .46, .17, (0, y0 - D / 2 + .03, H + .2), C(CREAM), .012, .08)
    # bottom: three crates of bags/boxes
    for i, bx in enumerate((-.47, 0, .47)):
        open_box(acc, .42, .34, .16, (bx, y0 - .02, .156), CRATE, .016, .006, 2.5)
        for k in range(3):
            if i == 1:
                box_pack(acc, (bx - .12 + k * .12, y0 - .05, .17), .1, .08, .2, ["pack_4", "pack_7", "pack_3"][k], "Anim Fill %d" % min(3, i + 1))
            else:
                chip_bag(acc, (bx - .12 + k * .12, y0 - .06 + (k % 2) * .06, .17), .12, .2, .06, ["pack_6", "pack_15", "pack_14"][(k + i) % 3], "Anim Fill %d" % (0 if i == 0 else 3))
    front = D / 2 - y0 + .01
    back = front - .17
    stock(acc, ("jar", ["pack_9", "pack_10", "pack_8"], ["D74A3C", "E8B23A", "6E8B3D"], NAVY), -inner / 2, inner / 2, -1, front, back, .52 + .016, .36, 3, L=inner)
    stock(acc, ("bottle", ["pack_8", "soda_1"], ["C9A227", "B58B1C"], "2E7D32"), -inner / 2, inner / 2, -1, front, back, .9 + .016, .36, 4, L=inner)
    stock(acc, ("box", .12, .075, .3, ["pack_0", "pack_2", "pack_1"]), -inner / 2, inner / 2, -1, front, back, 1.28 + .016, .32, 5, L=inner)


def shelf_t3(acc):
    """Gôndola de metal: 2.0 x 0.75 m wall gondola, navy powder-coated frame, pegboard back, brushed steel shelves
    with navy price channels, gold kick line, end frames and a header with a blank plaque."""
    W, D, H = 1.9, .74, 1.8
    yb = D / 2 - .05  # spine plane (back)
    rbox(acc, (W - .02, D - .04, .12), (0, 0, .06), C(NAVY), .02, 3)
    rbox(acc, (W - .04, .02, .1), (0, -D / 2 + .03, .06), C(BLUE), .01, 2)
    rbox(acc, (W - .04, .006, .012), (0, -D / 2 + .018, .1), C(GOLD), .003, 1)
    rbox(acc, (W - .06, .014, H - .16), (0, yb, H / 2 + .04), PEG, .004, 1, uv=2)
    rbox(acc, (W, .06, H - .1), (0, yb + .035, H / 2 + .02), C(NAVY), .01, 2)
    for x in (-W / 2 + .03, 0, W / 2 - .03):
        rbox(acc, (.05, .07, H), (x, yb - .02, H / 2), C(NAVY), .012, 2)
    rbox(acc, (W + .04, .16, .05), (0, yb - .02, H + .03), C(NAVY), .018, 3)
    levels = [(.12, .58), (.5, .44), (.86, .42), (1.22, .4), (1.56, .38)]
    for li, (z, d) in enumerate(levels):
        y = yb - .03 - d / 2
        if li:
            rbox(acc, (W - .1, d, .028), (0, y, z), BRUSHED, .006, 1, uv=2)
            for x in (-W / 2 + .03, W / 2 - .03, 0):
                bm = bmesh.new()
                vs = [bm.verts.new(v) for v in ((0, 0, 0), (0, -d * .8, 0), (0, 0, -.12))]
                bm.faces.new(vs)
                bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.012)
                place(bm, (x, yb - .03, z - .014))
                acc.add(bm, C(NAVY))
        rbox(acc, (W - .1, .022, .05), (0, yb - .03 - d - .004, z + .008), C(BLUE), .007, 2)
        price_tags(acc, -W / 2 + .1, W / 2 - .1, yb - .03 - d - .016, z + .008, C(CREAM), 6)
    # end frames with cream infill
    for e in (-1, 1):
        fr = frame_bm(D - .02, H + .02, .045, .14, .045)
        place(fr, (e * (W / 2 + .02), 0, (H + .02) / 2), (0, 0, 90)); acc.add(fr, C(NAVY))
        rbox(acc, (.02, D - .1, H - .1), (e * (W / 2 + .015), 0, H / 2 + .02), "T_IK_V2_PaintCream", .006, 1)
    # header: rounded navy plaque, gold rim, blank cream disc for the category pictogram
    plate(acc, 1.1, .34, (0, yb - .05, H + .26), C(NAVY), .05, .14)
    fr = frame_bm(1.06, .3, .014, .12, .014)
    place(fr, (0, yb - .078, H + .26)); acc.add(fr, C(GOLD))
    lathe(acc, [(0, 0), (.11, 0), (.11, .012), (0, .012)], (0, yb - .078, H + .26), C(CREAM), 24, 0, rot=(90, 0, 0))
    for x in (-.4, .4):
        rbox(acc, (.03, .03, .08), (x, yb - .05, H + .08), C(NAVY), .01, 2)
    th = THEMES["mercearia"]
    tops = [z for z, _ in levels[1:]] + [H - .02]
    for li, (z, d) in enumerate(levels):
        front = -(yb - .03 - d - .01) if True else 0
        front = -(yb - .03 - d)
        stock(acc, th[li % len(th)], -W / 2 + .06, W / 2 - .06, -1, front, front - (.2 if li == 4 else .095), z + .014, tops[li] - z - .05, 10 + li, L=W)


def shelf_t4(acc):
    """Gôndola iluminada: 2.5 x 1.0 m double-sided island, brushed inox spine, glass shelf lips, warm LED under every
    shelf, electronic shelf labels, LED kick light, lit canopy and glass light-box headers on the end caps."""
    W, D, H = 2.5, .98, 1.98
    L = W - .32
    rbox(acc, (L, D - .06, .13), (0, 0, .065), C(NAVY), .02, 3)
    for s in (-1, 1):
        rbox(acc, (L - .04, .02, .03), (0, s * (D / 2 - .045), .03), LED, .008, 1)
        rbox(acc, (L, .008, .012), (0, s * (D / 2 - .03), .126), C(GOLD), .003, 1)
    rbox(acc, (L, .1, H - .14), (0, 0, H / 2 + .05), BRUSHED, .02, 2, uv=1.5)
    for x in (-L / 2 + .02, 0, L / 2 - .02):
        rbox(acc, (.06, .14, H), (x, 0, H / 2), C(NAVY), .015, 2)
    # canopy with LED strips both sides, gold trims
    rbox(acc, (L + .06, .62, .1), (0, 0, H + .05), C(NAVY), .04, 3)
    for s in (-1, 1):
        rbox(acc, (L, .03, .012), (0, s * .27, H - .004), LED, .006, 1)
        rbox(acc, (L + .06, .008, .012), (0, s * .312, H + .06), C(GOLD), .003, 1)
    levels = [(.14, .45), (.5, .4), (.86, .4), (1.22, .38), (1.58, .36)]
    tops = [z for z, _ in levels[1:]] + [H - .06]
    th = THEMES["mercearia"]
    th2 = [("can", ["can_0", "can_1", "can_2", "can_6"]), ("bottle", ["soda_0", "soda_1", "soda_2"], ["3A120A", "1E7A32", "F28C28"], "D74A3C"),
           ("carton", ["juice_0", "juice_2", "milk"]), ("bag", ["pack_6", "pack_15"]), ("box", .11, .07, .22, ["pack_7", "pack_14"])]
    for s, theme in ((-1, th), (1, th2)):
        for li, (z, d) in enumerate(levels):
            if li:
                rbox(acc, (L - .08, d, .026), (0, s * (.05 + d / 2), z), BRUSHED, .006, 1, uv=2)
                rbox(acc, (L - .08, .008, .05), (0, s * (.05 + d + .002), z + .02), GLASS, .003, 1)
                rbox(acc, (L - .12, .03, .008), (0, s * (.05 + d - .03), z - .018), LED, .003, 1)
            # electronic shelf labels on a navy rail
            rbox(acc, (L - .08, .018, .036), (0, s * (.05 + d + .012), z - .004), C(NAVY), .006, 2)
            for i in range(7):
                x = -L / 2 + .12 + i * (L - .24) / 6
                rbox(acc, (.075, .006, .03), (x, s * (.05 + d + .022), z - .004), C(INK), 0, 1)
                rbox(acc, (.06, .004, .02), (x, s * (.05 + d + .026), z - .004), C("E3E8E4"), 0, 1)
            stock(acc, theme[li % len(theme)], -L / 2 + .06, L / 2 - .06, s, .05 + d, .05 + d - .095, z + .013, tops[li] - z - .06, 20 + li + (s > 0) * 7, L=L)
    # end caps: rounded navy frames, promo shelves with bottles, glass light-box header
    for e in (-1, 1):
        ex = e * (L / 2 + .02)
        fr = frame_bm(D, H + .02, .05, .18, .055)
        place(fr, (ex, 0, (H + .02) / 2), (0, 0, 90)); acc.add(fr, C(NAVY))
        rbox(acc, (.03, D - .12, H - .1), (ex - e * .005, 0, H / 2 + .02), BRUSHED, .01, 1, uv=2)
        for li, z in enumerate((.14, .52, .9, 1.28)):
            rbox(acc, (.12, D - .14, .026), (ex + e * .075, 0, z), BRUSHED, .006, 1)
            rbox(acc, (.008, D - .14, .05), (ex + e * .135, 0, z + .02), GLASS, .003, 1)
            rbox(acc, (.03, D - .2, .008), (ex + e * .1, 0, z - .018), LED, .003, 1)
            n = 4
            for k in range(n):
                yy = -D / 2 + .2 + k * (D - .4) / (n - 1)
                pet_bottle(acc, (ex + e * .075, yy, z + .013), .3, .034, C(["3A120A", "1E7A32", "F28C28"][li % 3]), ["soda_0", "soda_1", "soda_2", "soda_3"][(k + li) % 4], C("D74A3C"), "Anim Fill %d" % (0 if e < 0 else 3))
        # end-cap header: a rounded navy flag standing on the frame, a lit cream disc on its outer face (the game
        # puts the category pictogram there) and a thin gold rim
        plate(acc, D - .14, .34, (ex, 0, H + .27), C(NAVY), .06, .15, (0, 0, 90))
        fr = frame_bm(D - .18, .3, .012, .13, .012)
        place(fr, (ex + e * .032, 0, H + .27), (0, 0, 90)); acc.add(fr, C(GOLD))
        lathe(acc, [(0, 0), (.1, 0), (.1, .01), (0, .01)], (ex + e * .03, 0, H + .27), LED, 24, 0, rot=(0, 90 * e, 0))
        lathe(acc, [(.1, 0), (.113, 0), (.113, .012), (.1, .012)], (ex + e * .032, 0, H + .27), C(GOLD), 24, 0, rot=(0, 90 * e, 0), cap_top=False, cap_bottom=False)


# ================================================================================================ CHECKOUT TIERS
# Customers stand on -Y (the queue runs along X), the cashier on +Y.
def stool(acc, loc, seat_h=.62, key_seat=WOOD, key_leg=C("6B4128"), r=.17):
    x, y, z = loc
    lathe(acc, [(0, 0), (r, 0), (r, .035), (r - .01, .045), (0, .045)], (x, y, seat_h), key_seat, 20, 1)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        tube(acc, [(x + .1 * math.cos(a), y + .1 * math.sin(a), seat_h), (x + .16 * math.cos(a), y + .16 * math.sin(a), 0)], .016, key_leg, 6)
    lathe(acc, [(.12, 0), (.125, 0), (.125, .015), (.12, .015)], (x, y, seat_h * .35), key_leg, 16, 0)


def cash_tray(acc, loc, w=.28, d=.2):
    x, y, z = loc
    rbox(acc, (w, d, .03), (x, y, z + .015), C(INK), .006, 1)
    for i in range(4):
        cx = x - w / 2 + .04 + i * (w - .08) / 3
        for k in range(3):
            coin(acc, (cx + (k - 1) * .008, y - .045, z + .03 + k * .003), C("C8A23C" if i % 2 else "BFC5C9"), .011)
    for i, col in enumerate(("7DB37A", "6FA8D6", "E39A5B")):
        rbox(acc, (.07, .12, .004 + .002 * i), (x - w / 2 + .05 + i * .08, y + .03, z + .03 + .003 * i), C(col), .002, 1)


def checkout_t1(acc):
    """Caixinha no balcão: small wooden counter (1.25 x 0.6 m), navy painted body with wood slats, a blue metal
    cash box with an open lid, calculator, candy jar, paper bags and a wooden stool for the clerk."""
    W, D, H = 1.25, .6, .9
    y = -.3
    rbox(acc, (W - .04, D - .06, H - .06), (0, y, (H - .06) / 2), PAINT_NAVY, .02, 2)
    for k in range(6):
        rbox(acc, (.16, .022, H - .14), (-W / 2 + .12 + k * (W - .24) / 5, y - D / 2 + .022, (H - .06) / 2 + .02), WOOD, .008, 2)
    for s in (-1, 1):
        rbox(acc, (.05, .05, H - .04), (s * (W / 2 - .03), y - D / 2 + .035, (H - .04) / 2), WOOD_D, .01, 2)
    rbox(acc, (W + .04, D + .04, .045), (0, y, H - .02), WOOD, .012, 2)
    rbox(acc, (W + .04, .006, .01), (0, y - D / 2 - .024, H - .03), C(GOLD), .003, 1)
    top = H + .003
    # cash box (support blue tin) with open lid and coin tray
    cx, cy = .25, y + .08
    rbox(acc, (.32, .24, .09), (cx, cy, top + .045), C(BLUE), .014, 2)
    rbox(acc, (.3, .22, .012), (cx, cy, top + .085), C(INK), .004, 1)
    cash_tray(acc, (cx, cy, top + .06), .28, .2)
    lid = rbox_bm((.32, .24, .014), .008, 2)
    uv_box(lid)
    bmesh.ops.translate(lid, verts=lid.verts, vec=Vector((0, -.12, 0)))
    place(lid, (cx, cy + .12, top + .092), (-105, 0, 0))
    acc.add(lid, C(BLUE))
    rbox(acc, (.06, .02, .015), (cx, cy - .125, top + .07), C(CHROME), .005, 1)
    # calculator (pictogram keys only)
    kx, ky = -.05, y + .1
    rbox(acc, (.12, .16, .022), (kx, ky, top + .011), C(CREAM), .008, 2, rot=(-8, 0, 0))
    rbox(acc, (.09, .035, .004), (kx, ky + .045, top + .028), C("8FA392"), .002, 1, rot=(-8, 0, 0))
    for i in range(4):
        for j in range(4):
            rbox(acc, (.017, .015, .006), (kx - .033 + i * .022, ky - .058 + j * .022, top + .022 + j * .003), C(NAVY if i < 3 else "E07A3A"), .003, 1, rot=(-8, 0, 0))
    # candy jar on the customer side
    jx, jy = -.42, y - .12
    lathe(acc, [(0, 0), (.07, 0), (.08, .03), (.08, .17), (.06, .2), (.06, .22)], (jx, jy, top), GLASS, 18, 1, cap_top=False)
    lathe(acc, [(0, 0), (.066, 0), (.066, .02), (.05, .03), (.02, .045), (0, .05)], (jx, jy, top + .215), C(GOLD), 18, 1)
    rnd = random.Random(3)
    cols = ["E8505B", "F2C23F", "5FB548", "3E8FD6", "F28C28", "E86A9E"]
    for k in range(26):
        a, rr = rnd.random() * 6.28, rnd.random() * .055
        blob(acc, (.016, .016, .013), (jx + rr * math.cos(a), jy + rr * math.sin(a), top + .02 + (k // 7) * .028 + rnd.random() * .01), C(cols[k % 6]), 1, 0, k)
    # paper bags: a flat stack and one open
    for k in range(4):
        rbox(acc, (.2, .13, .006), (-.3, y + .14, top + .003 + k * .006), C("C9A06A"), .002, 1, rot=(0, 0, 4 * k))
    open_box(acc, .16, .1, .24, (.52, y + .12, top), C("C9A06A"), .004, .002)
    # stool behind (cashier side) and a little hand bell
    stool(acc, (.0, .32, 0))
    lathe(acc, [(0, 0), (.045, 0), (.045, .006), (.035, .02), (.02, .05), (.01, .06), (.012, .075), (0, .08)], (.05, y - .2, top), C(CHROME), 16, 1)


def register_classic(acc, loc, yaw=180):
    """Classic cash register: drawer base, sloped key deck with round keys, pop-up display flag, side crank."""
    x, y, z = loc
    X = Xf(acc, (x, y, z), (0, 0, yaw))
    rbox(X, (.42, .4, .12), (0, 0, .06), C(NAVY), .02, 3)
    rbox(X, (.38, .012, .08), (0, -.2, .06), C(BLUE), .008, 2)
    lathe(X, [(0, 0), (.012, 0), (.012, .018), (0, .02)], (0, -.208, .06), C(CHROME), 10, 0, rot=(90, 0, 0))
    deck = rbox_bm((.4, .26, .14), .025, 3)
    uv_box(deck)
    place(deck, (0, .02, .17), (-22, 0, 0)); X.add(deck, C(CREAM))
    for i in range(5):
        for j in range(4):
            px_, pz = -.14 + i * .07, -.08 + j * .055
            v = Matrix.Rotation(math.radians(-22), 4, "X") @ Vector((px_, pz, .075))
            lathe(X, [(0, 0), (.018, 0), (.02, .012), (.016, .02), (0, .021)], (v.x, .02 + v.y, .17 + v.z), C(INK if (i + j) % 3 else "C0392B"), 10, 1, rot=(-22, 0, 0))
    # pop-up display flag (blank window, the game shows the total)
    rbox(X, (.24, .06, .12), (0, .14, .33), C(NAVY), .02, 3)
    rbox(X, (.2, .006, .06), (0, .108, .335), C("8FA392"), .004, 1)
    rbox(X, (.2, .006, .06), (0, .172, .335), C("8FA392"), .004, 1)
    rbox(X, (.25, .004, .008), (0, .108, .39), C(GOLD), .002, 1)
    # side crank
    tube(X, [(.21, .05, .14), (.27, .05, .14), (.27, .05, .07)], .01, C(CHROME), 8)
    lathe(X, [(0, 0), (.018, 0), (.018, .04), (0, .04)], (.27, .05, .03), C(INK), 10, 1)


def checkout_t2(acc):
    """Caixa registradora: 1.75 x 0.7 m counter, navy body with framed wooden panels, cream top with a wood edge and
    a thin gold line; classic register, card machine for the customer, impulse wire basket, produce scale, stool."""
    W, D, H = 1.75, .7, .92
    y = -.4
    rbox(acc, (W - .04, D - .06, H - .07), (0, y, (H - .07) / 2), PAINT_NAVY, .02, 2)
    for k in range(3):
        px_ = -W / 2 + .3 + k * (W - .6) / 2
        fr = frame_bm(.46, .56, .025, .04, .045)
        place(fr, (px_, y - D / 2 + .02, .44)); acc.add(fr, WOOD)
        plate(acc, .38, .48, (px_, y - D / 2 + .028, .44), PAINT_NAVY, .012, .02)
    rbox(acc, (W - .04, .03, .09), (0, y - D / 2 + .035, .045), WOOD_D, .01, 2)
    rbox(acc, (W + .04, D + .04, .04), (0, y, H - .02), C(CREAM), .01, 2)
    rbox(acc, (W + .05, .03, .045), (0, y - D / 2 - .02, H - .02), WOOD, .012, 2)
    rbox(acc, (W + .05, .006, .008), (0, y - D / 2 - .036, H - .028), C(GOLD), .002, 1)
    top = H
    register_classic(acc, (.25, y + .12, top))
    # card machine on a little stand, facing the customer
    rbox(acc, (.09, .16, .03), (-.05, y - .14, top + .02), C(INK), .01, 2, rot=(25, 0, 0))
    rbox(acc, (.07, .05, .004), (-.05, y - .18, top + .05), C("7BD3F7"), .002, 1, rot=(25, 0, 0))
    for i in range(3):
        for j in range(3):
            rbox(acc, (.014, .012, .005), (-.072 + i * .022, y - .14 + j * .02, top + .04 + j * .009), C(CREAM), .002, 1, rot=(25, 0, 0))
    # produce scale (chrome dish on a navy base)
    rbox(acc, (.26, .24, .07), (-.55, y + .05, top + .035), C(NAVY), .02, 2)
    rbox(acc, (.16, .006, .05), (-.55, y - .068, top + .038), C("8FA392"), .003, 1)
    lathe(acc, [(0, 0), (.12, 0), (.15, .03), (.152, .036), (0, .02)], (-.55, y + .05, top + .075), C(CHROME), 24, 1)
    # impulse: wire basket of candy bars on the customer's end of the counter
    bx, by = -.66, y - .16
    for z in (top + .005, top + .07):
        tube(acc, [(bx - .15, by - .1, z), (bx + .15, by - .1, z), (bx + .15, by + .1, z), (bx - .15, by + .1, z), (bx - .15, by - .1, z)], .005, C(CHROME), 6)
    for s_ in (-1, 1):
        for t_ in (-1, 1):
            tube(acc, [(bx + s_ * .15, by + t_ * .1, top), (bx + s_ * .15, by + t_ * .1, top + .07)], .004, C(CHROME), 5)
    for i in range(4):
        for j in range(3):
            box_pack(acc, (bx - .105 + i * .07, by - .065 + j * .065, top + .006 + .012 * (j % 2)), .06, .055, .02, ["pack_14", "pack_7", "pack_6"][(i + j) % 3], "Anim Fill 0", yaw=8 * ((i + j) % 3 - 1))
    stool(acc, (.25, .32, 0), .7, C(NAVY), C(CHROME), .18)
    # bag hooks (folded paper bags) on the cashier side
    for k in range(3):
        rbox(acc, (.18, .006, .26), (.65 - k * .02, y + .2 + k * .012, top + .14), C("C9A06A"), .003, 1, rot=(0, 0, -5 + 5 * k))


def checkout_t3(acc):
    """Caixa com esteira: 2.5 x 0.9 m navy cabinet, wooden front, gold band, stone top, conveyor belt with chrome
    rails and end rollers, flatbed scanner, POS screen, card terminal, bagging well, lane light, impulse rack, chair."""
    W, D, H = 2.5, .9, .88
    y = -.45
    rbox(acc, (W - .02, D - .02, H - .04), (0, y, (H - .04) / 2), C(NAVY), .025, 3)
    plate(acc, W - .3, .6, (-.1, y - D / 2 - .005, .44), WOOD, .02, .03)
    for k in range(5):
        rbox(acc, (.012, .01, .56), (-W / 2 + .35 + k * .44, y - D / 2 - .014, .44), C(NAVY), .004, 1)
    rbox(acc, (W, .02, .04), (0, y - D / 2 - .012, .8), C(GOLD), .006, 1)
    rbox(acc, (W + .04, D + .04, .04), (0, y, H - .02), MARBLE, .01, 2, uv=.8)
    top = H
    # belt + rails + rollers
    bx0, bx1 = -1.18, .1
    rbox(acc, (bx1 - bx0, .42, .02), ((bx0 + bx1) / 2, y - .08, top + .015), BELT, .006, 1, uv=2)
    for s in (-1, 1):
        rbox(acc, (bx1 - bx0 + .02, .025, .045), ((bx0 + bx1) / 2, y - .08 + s * .225, top + .02), C(CHROME), .008, 2)
    for xr in (bx0, bx1):
        lathe(acc, [(0, -.21), (.016, -.21), (.016, .21), (0, .21)], (xr, y - .08, top + .015), C(CHROME), 12, 0, rot=(90, 0, 0))
    rbox(acc, (.03, .42, .04), (-.7, y - .08, top + .045), C("E15533"), .01, 2)
    for i, lab in enumerate(("pack_0", "pack_14", "pack_7")):
        box_pack(acc, (-1.0 + i * .2, y - .1, top + .025), .12, .08, .16 - .03 * i, lab, "Anim Fill 0")
    # flatbed scanner
    rbox(acc, (.32, .32, .03), (.32, y - .08, top + .012), C(INK), .008, 2)
    rbox(acc, (.2, .2, .004), (.32, y - .08, top + .028), "E_FF4A3A", .002, 1)
    # bagging well
    rbox(acc, (.48, .66, .03), (.95, y, top + .005), BRUSHED, .01, 2)
    for k in range(2):
        open_box(acc, .2, .14, .26, (.86 + k * .2, y - .1, top + .02), C("C9A06A"), .004, .002)
    # POS screen facing the cashier and cash drawer
    tube(acc, [(.62, y + .3, top), (.62, y + .3, top + .26)], .02, C(CHROME), 10)
    rbox(acc, (.38, .04, .26), (.62, y + .3, top + .36), C(INK), .02, 2, rot=(-12, 0, 0))
    rbox(acc, (.33, .006, .21), (.62, y + .322, top + .36), LED_COOL, .006, 1, rot=(-12, 0, 0))
    rbox(acc, (.44, .06, .12), (.62, y + .42, top - .1), C(INK), .01, 2)
    # card terminal on a swivel post facing the customer
    tube(acc, [(.12, y - .36, top), (.12, y - .36, top + .1)], .012, C(CHROME), 8)
    rbox(acc, (.09, .16, .03), (.12, y - .36, top + .12), C(INK), .01, 2, rot=(30, 0, 0))
    rbox(acc, (.07, .05, .004), (.12, y - .4, top + .145), "E_7BD3F7", .002, 1, rot=(30, 0, 0))
    # lane light (the game shows the lane number on the blank disc)
    tube(acc, [(-1.15, y + .38, top), (-1.15, y + .38, top + 1.0)], .025, C(CHROME), 10)
    lathe(acc, [(.02, 0), (.12, .04), (.12, .2), (.02, .24)], (-1.15, y + .38, top + 1.0), LED, 16, 1)
    rbox(acc, (.26, .02, .012), (-1.15, y + .38, top + 1.0), C(GOLD), .004, 1)
    lathe(acc, [(0, 0), (.08, 0), (.08, .01), (0, .01)], (-1.15, y + .245, top + 1.12), C(NAVY), 18, 0, rot=(90, 0, 0))
    # impulse rack at the start of the lane
    ix, iy = -1.05, y - D / 2 - .2
    rbox(acc, (.34, .3, 1.15), (ix, iy, .575), C(NAVY), .02, 2)
    for li, z in enumerate((.32, .58, .84)):
        rbox(acc, (.32, .2, .015), (ix, iy - .12, z), BRUSHED, .004, 1)
        for i in range(4):
            box_pack(acc, (ix - .11 + i * .072, iy - .14, z + .008), .06, .1, .1 + .02 * (i % 2), ["pack_14", "pack_6", "pack_15", "pack_7"][(i + li) % 4], "Anim Fill 0")
    rbox(acc, (.36, .03, .14), (ix, iy - .13, 1.22), C(NAVY), .02, 2)
    rbox(acc, (.3, .006, .1), (ix, iy - .146, 1.22), C(CREAM), .01, 1)
    # cashier chair
    lathe(acc, [(0, 0), (.24, 0), (.24, .02), (0, .03)], (.45, .32, 0), C(INK), 5, 0)
    tube(acc, [(.45, .32, .02), (.45, .32, .5)], .025, C(CHROME), 10)
    rbox(acc, (.42, .4, .07), (.45, .32, .53), C(NAVY), .03, 3)
    rbox(acc, (.4, .07, .38), (.45, .52, .78), C(NAVY), .03, 3, rot=(-8, 0, 0))


def checkout_t4(acc):
    """Caixa premium: 3.0 x 1.0 m rounded counter, navy body with LED kick light and glass front insets, inox top,
    LED-edged belt, bi-optic scanner tower, cashier screen + customer display, contactless terminal, bag carousel,
    glowing lane pylon with a gold ring, ergonomic chair."""
    W, D, H = 3.0, .95, .9
    y = -.42
    body, _ = panel_bm(W, D, H - .05, .32, 8)
    # panel_bm lies in XZ; rotate so the rounded rectangle lies on the floor (XY) and is extruded up
    bmesh.ops.rotate(body, verts=body.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    bmesh.ops.bevel(body, geom=[e for e in body.edges if e.calc_face_angle(0) > .8], offset=.02, segments=2, affect="EDGES", clamp_overlap=True)
    uv_box(body)
    place(body, (0, y, (H - .05) / 2 + .04))
    acc.add(body, C(NAVY))
    rbox(acc, (W - .3, D - .1, .04), (0, y, .02), C(INK), .01, 1)
    rbox(acc, (W - .34, .02, .02), (0, y - D / 2 + .06, .03), LED, .006, 1)
    # "ripado": a band of light-wood slats across the flat front, framed by two thin gold lines
    flat = W - 2 * .34
    n = 34
    for k in range(n):
        rbox(acc, (.034, .02, .5), (-flat / 2 + .02 + k * (flat - .04) / (n - 1), y - D / 2 - .006, .47), WOOD_L, .006, 1, uv=2)
    for z in (.21, .73):
        rbox(acc, (flat + .02, .012, .01), (0, y - D / 2 - .01, z), C(GOLD), .003, 1)
    tb, _ = panel_bm(W + .04, D + .04, .04, .34, 8)
    bmesh.ops.rotate(tb, verts=tb.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    uv_box(tb, 2)
    place(tb, (0, y, H - .01)); acc.add(tb, BRUSHED)
    top = H + .01
    bx0, bx1 = -1.35, .05
    rbox(acc, (bx1 - bx0, .46, .02), ((bx0 + bx1) / 2, y - .1, top + .012), BELT, .006, 1, uv=2)
    for s in (-1, 1):
        rbox(acc, (bx1 - bx0 + .02, .03, .04), ((bx0 + bx1) / 2, y - .1 + s * .245, top + .02), C(INK), .01, 2)
        rbox(acc, (bx1 - bx0, .006, .01), ((bx0 + bx1) / 2, y - .1 + s * .262, top + .03), LED_COOL, .003, 1)
    for i, (lab, kind) in enumerate((("soda_1", "b"), ("pack_0", "x"), ("juice_0", "c"), ("pack_15", "g"))):
        px_ = -1.2 + i * .3
        if kind == "b":
            pet_bottle(acc, (px_, y - .1, top + .022), .3, .034, C("1E7A32"), lab, C("D74A3C"), "Anim Fill 0")
        elif kind == "c":
            carton(acc, (px_, y - .1, top + .022), .075, .075, .22, lab, "Anim Fill 0")
        elif kind == "g":
            chip_bag(acc, (px_, y - .1, top + .022), .15, .22, .07, lab, "Anim Fill 0")
        else:
            box_pack(acc, (px_, y - .1, top + .022), .14, .08, .24, lab, "Anim Fill 0")
    # bi-optic scanner: flat window + vertical tower
    rbox(acc, (.36, .36, .03), (.3, y - .08, top + .01), C(INK), .01, 2)
    rbox(acc, (.2, .2, .004), (.3, y - .08, top + .027), C("3A1A1E"), .003, 1)
    rbox(acc, (.12, .12, .002), (.3, y - .08, top + .03), "E_FF4A3A", .002, 1)
    rbox(acc, (.36, .1, .26), (.3, y + .14, top + .14), C(INK), .03, 3)
    rbox(acc, (.22, .006, .14), (.3, y + .088, top + .15), C("3A1A1E"), .004, 1)
    rbox(acc, (.12, .004, .05), (.3, y + .084, top + .15), "E_FF4A3A", .002, 1)
    rbox(acc, (.36, .008, .01), (.3, y + .088, top + .27), C(GOLD), .003, 1)
    # bag carousel (three arms with paper bags)
    cx, cy = 1.0, y - .02
    lathe(acc, [(0, 0), (.16, 0), (.16, .02), (0, .03)], (cx, cy, top), C(INK), 20, 1)
    tube(acc, [(cx, cy, top), (cx, cy, top + .45)], .018, C(CHROME), 10)
    for k in range(3):
        a = k * 2 * math.pi / 3 + .4
        tube(acc, [(cx, cy, top + .42), (cx + .2 * math.cos(a), cy + .2 * math.sin(a), top + .42)], .008, C(CHROME), 6)
        bxx, byy = cx + .17 * math.cos(a), cy + .17 * math.sin(a)
        open_box(acc, .2, .13, .3, (bxx, byy, top + .06), C("C9A06A"), .004, .002)
    # cashier screen + customer display
    tube(acc, [(.66, y + .32, top), (.66, y + .32, top + .28)], .022, C(CHROME), 10)
    rbox(acc, (.44, .035, .28), (.66, y + .33, top + .4), C(INK), .02, 3, rot=(-10, 0, 0))
    rbox(acc, (.4, .006, .24), (.66, y + .35, top + .4), LED_COOL, .008, 1, rot=(-10, 0, 0))
    rbox(acc, (.24, .03, .16), (.66, y + .29, top + .34), C(INK), .015, 3, rot=(14, 0, 0))
    rbox(acc, (.21, .006, .13), (.66, y + .272, top + .34), LED_COOL, .006, 1, rot=(14, 0, 0))
    # contactless terminal (waves pictogram drawn as arcs)
    tx, ty = .0, y - .4
    tube(acc, [(tx, ty, top), (tx, ty, top + .1)], .014, C(CHROME), 8)
    rbox(acc, (.1, .17, .03), (tx, ty, top + .13), C(INK), .012, 2, rot=(30, 0, 0))
    rbox(acc, (.075, .06, .004), (tx, ty - .04, top + .155), LED_COOL, .002, 1, rot=(30, 0, 0))
    for k in range(3):
        pts = [(tx - .02 + .01 * k + .012 * math.cos(t) * (k + 1), ty + .02 + .012 * math.sin(t) * (k + 1) * .8, top + .155 + .02 * (k + 1) * math.sin(t) * .3) for t in (-.8, -.4, 0, .4, .8)]
        tube(acc, pts, .0025, C(WHITE), 5)
    # lane pylon: glowing column, gold ring, blank number disc
    px_, py = -1.38, y + .4
    lathe(acc, [(0, 0), (.1, 0), (.1, .04), (.05, .05), (0, .05)], (px_, py, top), C(NAVY), 20, 1)
    lathe(acc, [(.045, 0), (.045, 1.0)], (px_, py, top + .05), LED, 16, 0)
    lathe(acc, [(.06, 0), (.07, .02), (.07, .04), (.06, .06)], (px_, py, top + .75), C(GOLD), 20, 1)
    rbox(acc, (.3, .3, .3), (px_, py, top + 1.2), C(NAVY), .14, 4)
    lathe(acc, [(0, 0), (.1, 0), (.1, .01), (0, .01)], (px_, py - .155, top + 1.2), C(CREAM), 20, 0, rot=(90, 0, 0))
    lathe(acc, [(.1, 0), (.112, 0), (.112, .012), (.1, .012)], (px_, py - .158, top + 1.2), C(GOLD), 20, 0, rot=(90, 0, 0), cap_top=False, cap_bottom=False)
    # ergonomic chair
    lathe(acc, [(0, 0), (.26, 0), (.26, .02), (0, .03)], (.5, .3, 0), C(INK), 5, 0)
    tube(acc, [(.5, .3, .02), (.5, .3, .5)], .028, C(CHROME), 10)
    rbox(acc, (.46, .44, .08), (.5, .3, .54), C(NAVY), .035, 3)
    rbox(acc, (.44, .08, .46), (.5, .52, .84), C(NAVY), .035, 3, rot=(-10, 0, 0))
    rbox(acc, (.44, .006, .012), (.5, .48, 1.06), C(GOLD), .003, 1, rot=(-10, 0, 0))


BUILDERS = {"shelf": [shelf_t1, shelf_t2, shelf_t3, shelf_t4], "checkout": [checkout_t1, checkout_t2, checkout_t3, checkout_t4]}


# ================================================================================================ scene, sheets, renders
def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c


def build_item(kind, i, offset=(0, 0, 0)):
    tid, name, fw, fd, h = TIERS[kind][i]
    acc = Acc("%s_%s" % (kind, tid))
    BUILDERS[kind][i](acc)
    c = coll("FT %s %s" % (kind, tid), coll("Fixture tiers"))
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    root = bpy.data.objects.new("%s-%s" % (kind, tid.lower()), None)
    c.objects.link(root)
    root.empty_display_size = .3
    objs = acc.realize(c)
    for o in objs:
        o.name = "%s_%s %s" % (kind, tid, o.name)
        o.parent = root
    root.location = offset
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    root["tris"] = tris
    root["footprint_m"] = (fw, fd)
    return root, tris


def mannequin(loc, name="Pessoa 1.75 m"):
    acc = Acc(name)
    x, y, z = loc
    k = C("B9B2A6")
    for s in (-1, 1):
        tube(acc, [(x + s * .09, y, .0), (x + s * .1, y, .45), (x + s * .1, y, .86)], .065, k, 10, 2)
        tube(acc, [(x + s * .21, y, 1.38), (x + s * .26, y, 1.1), (x + s * .27, y + .02, .82)], .045, k, 8, 2)
    lathe(acc, [(.0, .82), (.17, .84), (.2, .95), (.19, 1.2), (.22, 1.38), (.16, 1.45), (.06, 1.48), (0, 1.48)], (x, y, 0), k, 16, 2)
    blob(acc, (.1, .11, .125), (x, y, 1.62), k, 3)
    for s in (-1, 1):
        rbox(acc, (.1, .2, .06), (x + s * .1, y - .04, .03), k, .025, 2)
    c = coll("FT sheet", coll("Fixture tiers"))
    return acc.realize(c)


def sheet_floor(x0, x1, y0, y1, footprints):
    """Floor with a 1 m grid (dark) and 0.25 m build grid (light), and the build-mode green outline of each footprint."""
    acc = Acc("Sheet floor")
    rbox(acc, (x1 - x0, y1 - y0, .02), ((x0 + x1) / 2, (y0 + y1) / 2, -.011), C("E9E3D6"), 0, 1)
    for gx in [x0 + i * .25 for i in range(int((x1 - x0) / .25) + 1)]:
        major = abs(gx - round(gx)) < 1e-6
        rbox(acc, (.012 if major else .005, y1 - y0, .002), (gx, (y0 + y1) / 2, .001), C("8D8678" if major else "CFC7B6"), 0, 1)
    for gy in [y0 + i * .25 for i in range(int((y1 - y0) / .25) + 1)]:
        major = abs(gy - round(gy)) < 1e-6
        rbox(acc, (x1 - x0, .012 if major else .005, .002), ((x0 + x1) / 2, gy, .0012), C("8D8678" if major else "CFC7B6"), 0, 1)
    for (cx, cy, w, d) in footprints:
        for s in (-1, 1):
            rbox(acc, (w, .03, .004), (cx, cy + s * (d / 2 - .015), .003), C("3FBF6A"), 0, 1)
            rbox(acc, (.03, d, .004), (cx + s * (w / 2 - .015), cy, .003), C("3FBF6A"), 0, 1)
    c = coll("FT sheet", coll("Fixture tiers"))
    return acc.realize(c)


def caption(value, loc, size=.17, key=C(NAVY)):
    acc = Acc("Caption")
    text(acc, value, size, loc, key, .004, rot=(-90, 0, 0), bevel=0)
    c = coll("FT sheet", coll("Fixture tiers"))
    return acc.realize(c)


CHECKOUT_CY = [.025, 0, -.025, -.02]
# Lineups with things standing in front of the footprint (the cold room's loading area): captions move down.
FRONT_APRON = {"coldroom": 1.1}
# Each lineup has its own strip of floor in this file (y of its centre line).
BASE_Y = {"shelf": 0.0, "checkout": -9.0, "drinks": -18.0, "dairy": -27.0, "freezer": -36.0, "icecream": -45.0,
          "bakery": -54.0, "produce": -63.0, "coldroom": -74.0, "sector": -86.0, "atm": -97.0, "machines": -106.0, "carts": -115.0}


def lineup(kind, gap=.9, base_y=0.0):
    """All tiers of `kind` side by side on the grid with their footprints, a person for scale and captions."""
    xs, x = [], 0.0
    for tid, name, fw, fd, h in TIERS[kind]:
        xs.append(x + fw / 2)
        x += fw + gap
    total = x - gap
    roots, prints, tris = [], [], []
    for i, cx in enumerate(xs):
        tid, name, fw, fd, h = TIERS[kind][i]
        root, t = build_item(kind, i, (cx - total / 2, base_y, 0))
        roots.append(root)
        tris.append(t)
        # shelves: the cell is centred on the model; checkouts: from the counter's front to behind the cashier
        prints.append((cx - total / 2, base_y + (0 if kind == "shelf" else CHECKOUT_CY[i]), fw, fd))
    return roots, prints, tris, total, [x - total / 2 for x in xs]


def set_jpg(sc, path, size):
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 90
    sc.render.filepath = path


def camera(target, direction, dist, lens=40, ortho=None):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("FT_Cam") or bpy.data.objects.new("FT_Cam", bpy.data.cameras.new("FT_Cam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    d = Vector(direction).normalized()
    cam.data.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        cam.data.ortho_scale = ortho
    cam.data.lens = lens
    cam.data.clip_end = 400
    cam.location = Vector(target) + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    return cam


def render(name, size=(2048, 1100)):
    os.makedirs(QA, exist_ok=True)
    sc = bpy.context.scene
    set_jpg(sc, os.path.join(QA, name + ".jpg"), size)
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


GAP = {"gumball": 2.2, "atm": 1.3, "carts": 1.2}


def lineup_sheet(kind, base_y, title_name):
    """Builds the lineup of `kind` at y = base_y and renders the sheet plus a close-up of every tier."""
    roots, prints, tris, total, xs = lineup(kind, GAP.get(kind, .9), base_y)
    ext = max(fd for (_, _, _, fd) in prints) + 2 * FRONT_APRON.get(kind, 0)
    x0, x1 = -total / 2 - 1.6, total / 2 + .6
    sheet_floor(math.floor(x0), math.ceil(x1), base_y - ext / 2 - 1.25, base_y + ext / 2 + .75, prints)
    mannequin((-total / 2 - .8, base_y + .1, 0), "Pessoa " + kind)
    for i, (cx, cy, fw, fd) in enumerate(prints):
        tid, name, _, _, h = TIERS[kind][i]
        caption(name if kind in globals().get("NO_TIER_KINDS", ()) else "%s  %s" % (tid, name), (cx, base_y - ext / 2 - .45, .004), .17)
        caption(("%.2f x %.2f m" % (fw, fd)).replace(".", ","), (cx, base_y - ext / 2 - .8, .004), .15, C("5E6B7D"))
    return roots, prints, tris, total


def isolate(base_y, half=3.4):
    """Only what stands around y = base_y renders (the other lineup is hidden)."""
    for o in bpy.context.scene.objects:
        if o.type in ("MESH", "EMPTY"):
            if o.type == "EMPTY" or o.parent:
                y = o.matrix_world.translation.y
            else:
                y = sum((o.matrix_world @ Vector(c)).y for c in o.bound_box) / 8
            o.hide_render = abs(y - base_y) > half


def shots(kind, base_y, prints, total):
    isolate(base_y, 4.6 if kind == "coldroom" else 3.4)
    ext = max(fd for (_, _, _, fd) in prints)
    hmax = max(t[4] for t in TIERS[kind])
    d = Vector((-.32, -1, .78))
    big = kind == "coldroom"
    camera((0 - .5, base_y - (1.0 if big else .3), hmax * .4), d, 40, ortho=total + (4.2 if big else 3.0))
    out = [render("%s_lineup" % kind, (2048, 1024))]
    for i, (cx, cy, fw, fd) in enumerate(prints):
        tid, name, _, _, h = TIERS[kind][i]
        dist = max(fw * 1.15, h * 1.5) + 1.8
        camera((cx, cy, h * .5), (-.5, -1, .62), dist, 42)
        out.append(render("%s_%s_closeup" % (kind, tid), (1400, 1000)))
    return out


def run(what=("shelf", "checkout"), do_render=True):
    sc = bpy.context.scene
    rk_core.studio(floor=False, bg=(.86, .85, .83))
    sc.render.engine = "BLENDER_EEVEE"
    setup_materials()
    report = {}
    for kind in what:
        base_y = BASE_Y[kind]
        roots, prints, tris, total = lineup_sheet(kind, base_y, kind)
        report[kind] = {"tris": tris, "prints": prints}
        if do_render:
            report[kind]["files"] = shots(kind, base_y, prints, total)
    return report


# ================================================================================================ Conveniência fit shot
CONV_AT = Vector((30, 0, 0))   # where the shop stands in this file (away from the lineups)
CONV_SCALE = 1.2               # the eras' models are scaled 1.2 in the game (CheckoutStall.Scale)
# Floor and counter of the Conveniência in model metres (CheckoutStall plan "Era4_Spati": floor, counter).
CONV_FLOOR = (-3.25, -1.12, 3.85, 2.95)
CONV_COUNTER = (1.3, 0.0, 3.03, 1.4)


def load_conveniencia():
    """Appends the navy Conveniência (collection 'NEW Era4_Spati' of eras_v2.blend), scaled like in the game, with
    the roof, awning and sign hidden so the camera sees inside."""
    if bpy.data.objects.get("CONV root"):
        return bpy.data.objects["CONV root"]
    path = os.path.join(REPO, "unity", "CheckoutSimulator", "ArtSource", "eras_v2", "eras_v2.blend")
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = ["NEW Era4_Spati"]
    c = coll("FT conveniencia", coll("Fixture tiers"))
    root = bpy.data.objects.new("CONV root", None)
    c.objects.link(root)
    for col in dst.collections:
        c.children.link(col)
        for o in list(col.all_objects):
            if o.parent is None:
                o.parent = root
            if any(k in o.name for k in ("FacadeTop", "Awning", "_Sign", "winTop")):
                o.hide_render = o.hide_viewport = True
    root.scale = (CONV_SCALE,) * 3
    root.location = CONV_AT
    return root


def ghost(name, w, d, h, loc, rot, col):
    """Clay stand-in for a fixture not modelled yet (true size), with a rounded top edge."""
    acc = Acc(name)
    rbox(acc, (w - .02, d - .02, h), (0, 0, h / 2), C(col), .05, 3)
    c = coll("FT conveniencia", coll("Fixture tiers"))
    objs = acc.realize(c)
    for o in objs:
        o.name = name
        o.location = loc
        o.rotation_euler = (0, 0, math.radians(rot))
    return objs


def outline(name, w, d, loc, rot, col, collection="FT conveniencia"):
    acc = Acc(name)
    for s in (-1, 1):
        rbox(acc, (w, .035, .006), (0, s * (d / 2 - .018), .004), C(col), 0, 1)
        rbox(acc, (.035, d, .006), (s * (w / 2 - .018), 0, .004), C(col), 0, 1)
    c = coll(collection, coll("Fixture tiers"))
    for o in acc.realize(c):
        o.name = name
        o.location = loc
        o.rotation_euler = (0, 0, math.radians(rot))


def instance(kind, tier, loc, rot, name, collection="FT conveniencia"):
    """Linked copy of a built tier (shares its meshes)."""
    src = bpy.data.objects["%s-%s" % (kind, tier.lower())]
    c = coll(collection, coll("Fixture tiers"))
    root = bpy.data.objects.new(name, None)
    c.objects.link(root)
    for ch in src.children:
        o = bpy.data.objects.new(ch.name + " " + name, ch.data)
        c.objects.link(o)
        o.parent = root
        for m in ch.modifiers:
            if m.type == "WEIGHTED_NORMAL":
                wn = o.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
                wn.keep_sharp = True
                wn.weight = 100
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(rot))
    return root


def conv_layout(mode):
    """Puts the six fixtures of the Conveniência (produce, drinks, bakery, dairy, snacks, grocery) in the shop:
    mode 'hoje' = today's sizes (clay), mode 'tiers' = the proposed starting tiers (T1/T2 shelves modelled, the others
    as clay at their proposed T1 size). Footprints: red = today, green = proposal."""
    load_conveniencia()
    k = CONV_SCALE
    x0, y0, x1, y1 = (v * k for v in CONV_FLOOR)
    O = CONV_AT
    for o in list(bpy.data.collections["FT conveniencia"].objects):
        if o.name.startswith(("FIX ", "OUT ")) or (o.parent and o.parent.name.startswith("FIX ")):
            bpy.data.objects.remove(o, do_unlink=True)
    back = y1
    if mode == "hoje":
        red = "D9534F"
        spots = [  # (name, w, d, h, x, y, rot, colour)
            ("produce", 1.9, 1.1, .95, x0 + .55, y0 + 1.25, 270, "7DB35A"),
            ("dairy", 1.9, .92, 1.4, x0 + .46, y0 + 3.25, 270, "9CC9E8"),
            ("snacks", 2.84, .96, 1.72, x0 + 1.0 + 1.42, back - .48, 0, "E8A0B8"),
            ("coffee", 2.84, .96, 1.72, x0 + 1.0 + 1.42 + 2.9, back - .48, 0, "E8C27A"),
            ("bakery", 1.9, .85, 1.6, x0 + 4.42, y0 + 1.75, 0, "D9A06A"),  # no wall left: it stands in the way
            ("drinks", 1.9, .84, 1.95, x0 + 2.4, y0 + 1.6, 0, "6FA8D6"),
        ]
        for name, w, d, h, x, y, rot, col in spots:
            ghost("FIX " + name, w, d, h, O + Vector((x, y, 0)), rot, col)
            outline("OUT " + name, w, d, O + Vector((x, y, 0)), rot, red)
    else:
        green = "3FBF6A"
        instance("shelf", "T1", O + Vector((x0 + .7, back - .25, 0)), 0, "FIX snacks T1")
        outline("OUT snacks", 1.0, .5, O + Vector((x0 + .7, back - .25, 0)), 0, green)
        instance("shelf", "T2", O + Vector((x0 + 2.05, back - .25, 0)), 0, "FIX coffee T2")
        outline("OUT coffee", 1.5, .5, O + Vector((x0 + 2.05, back - .25, 0)), 0, green)
        instance("shelf", "T1", O + Vector((x0 + 3.4, back - .25, 0)), 0, "FIX bakery T1")
        outline("OUT bakery", 1.0, .5, O + Vector((x0 + 3.4, back - .25, 0)), 0, green)
        for name, w, d, h, x, y, rot, col in (
            ("dairy", 1.0, .75, 1.3, x0 + 4.6, back - .375, 0, "9CC9E8"),
            ("drinks", .75, .75, 1.85, x1 - .45, back - .375, 0, "6FA8D6"),
            ("produce", 1.0, .75, .95, x0 + .375, y0 + 1.6, 90, "7DB35A"),
        ):
            ghost("FIX " + name, w, d, h, O + Vector((x, y, 0)), rot, col)
            outline("OUT " + name, w, d, O + Vector((x, y, 0)), rot, green)


def conv_shots():
    """Renders the shop with today's sizes and with the proposed tiers; everything else in the file is hidden."""
    sc = bpy.context.scene
    out = []
    for mode in ("hoje", "tiers"):
        conv_layout(mode)
        bpy.context.view_layer.update()
        for o in sc.objects:
            if o.type not in ("MESH", "EMPTY") or o.hide_viewport:
                continue
            cx = sum((o.matrix_world @ Vector(c)).x for c in o.bound_box) / 8 if o.type == "MESH" else o.matrix_world.translation.x
            o.hide_render = abs(cx - CONV_AT.x) > 12
        camera(CONV_AT + Vector((.4, 1.0, .3)), (-.1, -1, 1.45), 13.5, 34)
        out.append(render("conveniencia_fit_%s" % mode, (1800, 1200)))
    return out


# ================================================================================================ BATCH A: chilled, bakery, produce
# Same rules as the shelves: T1/T2 fit the Conveniência and the Quitanda, T3 the Minimercado, T4 from the Mercadinho.
TIERS.update({
    "drinks": [
        ("T1", "Geladeira de 1 porta", .75, .75, 1.85),
        ("T2", "Geladeira de 2 portas", 1.25, .75, 1.95),
        ("T3", "Geladeira de 3 portas", 2.00, .75, 2.05),
        ("T4", "Parede de portas com LED", 2.50, 1.00, 2.20),
    ],
    "dairy": [
        ("T1", "Expositor refrigerado pequeno", 1.00, .75, 1.30),
        ("T2", "Balcão refrigerado", 1.50, .75, 1.35),
        ("T3", "Expositor aberto (multideck)", 2.00, 1.00, 2.00),
        ("T4", "Multideck com portas de vidro", 2.50, 1.00, 2.15),
    ],
    "freezer": [
        ("T1", "Freezer horizontal pequeno", 1.00, .75, .92),
        ("T2", "Freezer horizontal grande", 1.50, .75, .95),
        ("T3", "Freezer vertical de 2 portas", 1.50, .90, 2.05),
        ("T4", "Ilha de congelados", 2.50, 1.25, 1.75),
    ],
    "icecream": [
        ("T1", "Freezer de sorvetes", 1.00, .75, .95),
        ("T2", "Freezer de sorvetes grande", 1.50, .75, 1.0),
        ("T3", "Ilha de sorvetes", 2.00, 1.00, 1.0),
        ("T4", "Vitrine de gelato", 2.50, 1.00, 1.45),
    ],
    "bakery": [
        ("T1", "Estante de pães", 1.00, .50, 1.50),
        ("T2", "Estante de cestos inclinados", 1.50, .50, 1.80),
        ("T3", "Vitrine de acrílico", 2.00, .75, 1.85),
        ("T4", "Vitrine aquecida iluminada", 2.00, 1.00, 1.90),
    ],
    "produce": [
        ("T1", "Banca de caixotes", 1.00, .75, 1.00),
        ("T2", "Banca inclinada de madeira", 1.50, .75, 1.55),
        ("T3", "Banca de metal com espelho", 2.00, 1.00, 1.95),
        ("T4", "Ilha refrigerada com névoa", 2.50, 1.25, 2.05),
    ],
})

ICE = "E_DDF4FF"      # cold white LED inside the fridges
FROST = "C_EAF6FB"    # frost on the freezer rims


# ---------------------------------------------------------------- fridge parts
def glass_door(acc, cx, y, z0, w, h, frame_key, handle_side=1, frame=.04):
    """Hinged glass door facing -Y: rounded frame, glass, a long chrome pull."""
    fr = frame_bm(w, h, .035, .03, frame)
    place(fr, (cx, y, z0 + h / 2)); acc.add(fr, frame_key)
    rbox(acc, (w - 2 * frame + .01, .008, h - 2 * frame + .01), (cx, y + .004, z0 + h / 2), GLASS, .004, 1)
    hx = cx + handle_side * (w / 2 - frame - .03)
    tube(acc, [(hx, y - .02, z0 + h * .32), (hx, y - .045, z0 + h * .34), (hx, y - .045, z0 + h * .66), (hx, y - .02, z0 + h * .68)], .011, C(CHROME), 8)


def fridge_body(acc, W, D, H, key=C(NAVY), inner=C(WHITE), base_h=.12, top_h=.16, y0=0):
    """Upright cabinet open at the front: sides, back, top and a ventilated plinth, white inside."""
    for s in (-1, 1):
        rbox(acc, (.05, D, H), (s * (W / 2 - .025), y0, H / 2), key, .025, 3)
    rbox(acc, (W - .08, .04, H - base_h - top_h), (0, y0 + D / 2 - .02, base_h + (H - base_h - top_h) / 2), inner, .01, 1)
    rbox(acc, (W, D, top_h), (0, y0, H - top_h / 2), key, .03, 3)
    rbox(acc, (W - .02, D - .02, base_h), (0, y0, base_h / 2), C(INK), .02, 2)
    for k in range(int((W - .2) / .05)):
        rbox(acc, (.025, .01, base_h * .5), (-W / 2 + .14 + k * .05, y0 - D / 2 - .002, base_h * .5), C("3A4450"), .004, 1)
    rbox(acc, (W - .1, .01, .012), (0, y0 - D / 2 - .004, base_h + .004), C(GOLD), .003, 1)
    for s in (-1, 1):
        rbox(acc, (.012, D - .1, H - base_h - top_h), (s * (W / 2 - .056), y0, base_h + (H - base_h - top_h) / 2), inner, .004, 1)


def fridge_header(acc, W, y, z, h=.2, lit=True):
    """Lit header panel over the doors: navy, a thin gold line and a blank glowing plaque (the game draws on it)."""
    plate(acc, W - .08, h, (0, y, z), C(NAVY), .03, .05)
    rbox(acc, (W - .12, .006, .01), (0, y - .016, z - h / 2 + .03), C(GOLD), .003, 1)
    if lit:
        plate(acc, min(.5, W * .45), h * .55, (0, y - .017, z + .01), LED, .006, .04)


def drinks_stock(acc, x0, x1, y_front, depth, levels, seed=0, grp=None):
    """Bottles, cans and cartons on the wire shelves of an upright fridge (front row facing -Y)."""
    kinds = [("bottle", ["soda_0", "soda_1", "soda_2", "soda_3"], ["3A120A", "1E7A32", "F28C28", "6A2B8C"], "D74A3C"),
             ("can", ["can_0", "can_1", "can_3", "can_4", "can_6"]),
             ("bottle", ["water_0", "water_1", "juice_1"], ["BFE3F0", "9FD0E6", "E25555"], "3E8FD6"),
             ("carton", ["juice_0", "juice_2", "juice_3", "milk"]),
             ("bottle", ["soda_4", "soda_5", "soda_7"], ["F2C23F", "E8F0D0", "1C1C1C"], "D74A3C")]
    for li, (z, avail) in enumerate(levels):
        rbox(acc, (x1 - x0, depth, .012), ((x0 + x1) / 2, y_front + depth / 2, z - .006), C(CHROME), .004, 1)
        stock(acc, kinds[(li + seed) % len(kinds)], x0, x1, -1, -y_front, -y_front - min(depth - .02, .16), z, avail, seed + li, L=None, grp=grp)


def upright_fridge(acc, W, D, H, doors, key=C(NAVY), frame_key=C(NAVY), led=False, seed=0, stock_fn=drinks_stock, nlev=5):
    fridge_body(acc, W, D, H, key)
    base, top = .12, .16
    inner_w = W - .12
    z0, z1 = base + .03, H - top - .03
    levels, step = [], (z1 - z0) / nlev
    for i in range(nlev):
        levels.append((z0 + i * step + .01, step - .04))
    stock_fn(acc, -inner_w / 2 + .02, inner_w / 2 - .02, -D / 2 + .08, D - .16, levels, seed)
    dw = (W - .06) / doors
    for k in range(doors):
        cx = -W / 2 + .03 + dw * (k + .5)
        glass_door(acc, cx, -D / 2 + .02, base, dw - .01, H - base - top, frame_key, 1 if k % 2 == 0 else -1)
        if led:
            rbox(acc, (.012, .01, H - base - top - .1), (cx - dw / 2 + .012, -D / 2 + .05, base + (H - base - top) / 2), ICE, .004, 1)
    fridge_header(acc, W, -D / 2 - .005, H - top / 2, top * .9)


# ---------------------------------------------------------------- DRINKS
def drinks_t1(acc):
    """Geladeira de 1 porta: a classic upright bottle cooler, navy with cream inside, lit header, five shelves."""
    upright_fridge(acc, .7, .68, 1.85, 1, seed=0)
    for s in (-1, 1):
        lathe(acc, [(0, 0), (.025, 0), (.025, .03), (0, .03)], (s * .28, -.26, -.0), C(INK), 8, 0)


def drinks_t2(acc):
    """Geladeira de 2 portas: wider, a cream door frame, gold trims on the sides."""
    upright_fridge(acc, 1.2, .7, 1.95, 2, frame_key=C(CREAM), seed=1)
    for s in (-1, 1):
        rbox(acc, (.008, .7, .012), (s * .6, 0, 1.0), C(GOLD), .003, 1)


def drinks_t3(acc):
    """Geladeira de 3 portas: steel-framed doors, LED edges, side panels with a navy wrap and cream band."""
    upright_fridge(acc, 1.96, .72, 2.05, 3, frame_key="T_IK_R_Brushed", led=True, seed=2, nlev=6)
    for s in (-1, 1):
        rbox(acc, (.012, .6, .3), (s * (1.96 / 2 + .002), 0, 1.5), C(CREAM), .006, 1)


def drinks_t4(acc):
    """Parede de portas com LED: four frameless doors under a lit navy bulkhead, inox base, cool LED inside."""
    W, D, H = 2.48, .96, 2.2
    upright_fridge(acc, W, D, H - .2, 4, frame_key="T_IK_R_Brushed", led=True, seed=3, nlev=6)
    rbox(acc, (W + .04, D + .04, .24), (0, 0, H - .1), C(NAVY), .05, 3)
    rbox(acc, (W - .04, .02, .02), (0, -D / 2 - .01, H - .21), LED, .006, 1)
    rbox(acc, (W + .04, .01, .012), (0, -D / 2 - .022, H - .02), C(GOLD), .003, 1)
    rbox(acc, (W + .02, .02, .1), (0, -D / 2 + .01, .05), BRUSHED, .01, 1)
    for k in range(4):
        plate(acc, .36, .11, (-W / 2 + W / 8 + k * W / 4, -D / 2 - .025, H - .1), LED, .006, .05)


# ---------------------------------------------------------------- DAIRY / FRIOS
def yogurt(acc, loc, grp, label="yogurt", r=.03, h=.055):
    lathe(acc, [(r * .8, 0), (r, h), (r * 1.02, h)], loc, LAB, 8, 0, grp=grp, uv_cell=label, u_rep=2, v_range=(0, h), cap_bottom=False, cap_top=False)
    lathe(acc, [(r * 1.04, 0), (0, 0)], (loc[0], loc[1], loc[2] + h), C(WHITE), 8, 0, grp=grp, cap_top=False, cap_bottom=False)


def cheese_wheel(acc, loc, r=.09, h=.07, grp="Body", cut=False):
    lathe(acc, [(0, 0), (r * .95, 0), (r, h * .2), (r, h * .8), (r * .95, h), (0, h)], loc, "T_IK_Cheese", 12, 0, grp=grp)


def salami(acc, loc, L=.24, r=.025, rot=0, grp="Body"):
    x, y, z = loc
    a = math.radians(rot)
    dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2
    tube(acc, [(x - dx, y - dy, z + r), (x, y, z + r * 1.05), (x + dx, y + dy, z + r)], lambda t: r * (.75 + .25 * math.sin(math.pi * t)), C("8E2F2A"), 8)


def dairy_stock(acc, x0, x1, y_front, depth, levels, seed=0, grp=None):
    rnd = random.Random(seed)
    for li, (z, avail) in enumerate(levels):
        rbox(acc, (x1 - x0, depth, .012), ((x0 + x1) / 2, y_front + depth / 2, z - .006), C(WHITE), .004, 1)
        k = (li + seed) % 4
        if k == 0:
            stock(acc, ("carton", ["milk", "juice_0", "milk"]), x0, x1, -1, -y_front, -y_front - .17, z, avail, li)
        elif k == 1:
            x = x0 + .04
            while x < x1 - .04:
                for row in range(2):
                    for st in range(2):
                        yogurt(acc, (x, y_front + .04 + row * .07, z + st * .057), grp or fills_for(x, x1 - x0))
                x += .068
        elif k == 2:
            x = x0 + .1
            while x < x1 - .1:
                cheese_wheel(acc, (x, y_front + .1, z), .085, .065, grp or fills_for(x, x1 - x0))
                x += .19
        else:
            stock(acc, ("box", .1, .07, .06, ["pack_8", "pack_10", "pack_4"]), x0, x1, -1, -y_front, -y_front - .17, z, avail, li)


def deli_counter(acc, W, D, H, wood_front=True, seed=0):
    """Low refrigerated counter with a curved glass front (frios e queijos), trays of cheese and cold cuts."""
    rbox(acc, (W, D, .82), (0, 0, .41), C(NAVY), .03, 3)
    if wood_front:
        plate(acc, W - .14, .5, (0, -D / 2 - .004, .42), WOOD, .016, .04)
        rbox(acc, (W - .1, .008, .012), (0, -D / 2 - .016, .7), C(GOLD), .003, 1)
    rbox(acc, (W - .04, D - .3, .03), (0, .1, .83), C(WHITE), .01, 1)
    # curved glass: a quarter cylinder along X
    bm = bmesh.new()
    prof = [(0, 0), (.08, .05), (.16, .16), (.2, .3), (.21, .42)]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        v = [bm.verts.new((-W / 2 + .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -b[0], b[1])), bm.verts.new((-W / 2 + .03, -b[0], b[1]))]
        bm.faces.new(v)
    uv_box(bm)
    place(bm, (0, -D / 2 + .3, .84)); acc.add(bm, GLASS)
    rbox(acc, (W - .04, .3, .012), (0, -D / 2 + .55, 1.27), GLASS, .004, 1)
    rbox(acc, (W, .26, .03), (0, D / 2 - .13, 1.28), C(NAVY), .01, 2)
    rbox(acc, (W - .1, .02, .01), (0, D / 2 - .25, 1.26), ICE, .004, 1)
    for s in (-1, 1):
        rbox(acc, (.03, D - .05, .5), (s * (W / 2 - .015), 0, 1.07), C(NAVY), .015, 2)
    x = -W / 2 + .14
    i = 0
    while x < W / 2 - .12:
        g = fills_for(x, W)
        rbox(acc, (.2, .26, .02), (x + .03, -.05, .86), BRUSHED, .006, 1)
        if i % 3 == 0:
            cheese_wheel(acc, (x + .03, -.05, .87), .08, .07, g)
        elif i % 3 == 1:
            for k in range(3):
                salami(acc, (x + .03, -.12 + k * .07, .87), .2, .022, 0, g)
        else:
            for k in range(4):
                rbox(acc, (.15, .045, .012), (x + .03, -.14 + k * .055, .875 + k * .004), C("E89A9A"), .005, 1, rot=(10, 0, 0), grp=g)
        if i % 2 == 0:
            rbox(acc, (.2, .2, .02), (x + .03, .2, .88), BRUSHED, .006, 1)
            for k in range(3):
                blob(acc, (.06, .05, .03), (x - .03 + k * .06, .2, .91), C(["F2D27A", "E89A9A", "F6E7C8"][(i + k) % 3]), 1, .1, i + k, grp=g)
        x += .24
        i += 1


def dairy_t1(acc):
    """Expositor refrigerado pequeno: a small glass-topped chilled display on a navy cabinet, two stepped trays."""
    W, D = .98, .72
    rbox(acc, (W, D, .7), (0, 0, .35), C(NAVY), .03, 3)
    rbox(acc, (W - .1, .01, .012), (0, -D / 2 - .004, .66), C(GOLD), .003, 1)
    plate(acc, W - .2, .42, (0, -D / 2 - .004, .36), WOOD, .014, .03)
    for i, (z, y) in enumerate(((.72, -.12), (.92, .14))):
        rbox(acc, (W - .08, .3, .03), (0, y, z), C(WHITE), .008, 1)
        dairy_stock(acc, -W / 2 + .06, W / 2 - .06, y - .14, .28, [(z + .015, .2)], seed=i)
    for s in (-1, 1):
        rbox(acc, (.03, D - .04, .58), (s * (W / 2 - .015), 0, 1.0), GLASS, .006, 1)
    rbox(acc, (W, .03, .58), (0, D / 2 - .015, 1.0), C(NAVY), .01, 1)
    rbox(acc, (W - .06, .02, .3), (0, -D / 2 + .02, .86), GLASS, .006, 1)
    rbox(acc, (W + .02, D + .02, .04), (0, 0, 1.3), C(NAVY), .015, 2)
    rbox(acc, (W - .1, .02, .01), (0, -D / 2 + .1, 1.275), ICE, .004, 1)


def dairy_t2(acc):
    """Balcão refrigerado: wood-fronted deli counter with curved glass, cheese wheels, salamis and sliced ham."""
    deli_counter(acc, 1.48, .72, 1.35)


def multideck(acc, W, D, H, doors=0, seed=0):
    """Open multideck (air curtain) or with glass doors: tall navy cabinet, sloped shelves stepping forward."""
    fridge_body(acc, W, D, H, C(NAVY), C(WHITE), .16, .22)
    nlev = 5
    z0, z1 = .3, H - .3
    for i in range(nlev):
        z = z0 + i * (z1 - z0) / nlev
        depth = D - .2 - (nlev - 1 - i) * 0 - i * .05
        dairy_stock(acc, -W / 2 + .08, W / 2 - .08, D / 2 - .06 - depth, depth, [(z, (z1 - z0) / nlev - .04)], seed + i)
        rbox(acc, (W - .12, .02, .035), (0, D / 2 - .06 - depth - .01, z - .01), C(BLUE), .006, 2)
        price_tags(acc, -W / 2 + .1, W / 2 - .1, D / 2 - .06 - depth - .022, z - .01, C(CREAM), 5)
    # front deck with the air-curtain grille
    rbox(acc, (W - .04, .16, .24), (0, -D / 2 + .08, .12), C(NAVY), .03, 3)
    rbox(acc, (W - .1, .1, .006), (0, -D / 2 + .1, .245), C("3A4450"), .003, 1)
    rbox(acc, (W - .1, .012, .012), (0, -D / 2 - .004, .2), C(GOLD), .003, 1)
    rbox(acc, (W - .14, .03, .015), (0, -D / 2 + .25, H - .235), ICE, .004, 1)
    if doors:
        dw = (W - .06) / doors
        for k in range(doors):
            glass_door(acc, -W / 2 + .03 + dw * (k + .5), -D / 2 + .02, .25, dw - .01, H - .5, "T_IK_R_Brushed", 1 if k % 2 == 0 else -1)
    else:
        # night blind roll under the canopy
        lathe(acc, [(.035, 0), (.035, W - .12)], (-W / 2 + .06, -D / 2 + .06, H - .26), C(INK), 10, 0, rot=(0, 90, 0))
    fridge_header(acc, W, -D / 2 - .01, H - .11, .2)


def dairy_t3(acc):
    multideck(acc, 1.98, .96, 2.0, 0, 1)


def dairy_t4(acc):
    multideck(acc, 2.48, .96, 2.15, 4, 2)
    rbox(acc, (2.5, .02, .02), (0, -.49, .03), LED, .006, 1)


# ---------------------------------------------------------------- FROZEN / ICE CREAM
def pizza_box(acc, loc, w=.3, h=.04, label="pack_4", grp="Body", yaw=0):
    box_pack(acc, loc, w, w, h, label, grp, .004, yaw)


def frozen_fill(acc, x0, x1, y0, y1, z, rnd, grp=None, kind="frozen"):
    """Fills a freezer well (from above): pizza stacks, frozen bags and boxes, or ice-cream tubs."""
    x = x0 + .02
    while x < x1 - .14:
        y = y0 + .02
        while y < y1 - .14:
            g = grp or fills_for(x, x1 - x0)
            if kind == "frozen":
                k = rnd.randrange(3)
                if k == 0:
                    for st in range(rnd.randrange(2, 5)):
                        pizza_box(acc, (x + .14, y + .14, z + st * .042), .26, .04, ["pack_4", "pack_10", "pack_1"][st % 3], g, rnd.uniform(-8, 8))
                elif k == 1:
                    for st in range(2):
                        box_pack(acc, (x + .14, y + .14, z + st * .07), .24, .17, .07, ["pack_15", "pack_6", "pack_12"][(st + int(x * 10)) % 3], g, .02, rnd.uniform(-20, 20))
                else:
                    for st in range(2):
                        box_pack(acc, (x + .14, y + .14, z + st * .09), .2, .14, .09, ["pack_7", "pack_13"][st], g, .004, rnd.uniform(-10, 10))
            else:
                tub(acc, (x + .13, y + .13, z), "gelato_%d" % rnd.randrange(8), g)
            y += .29
        x += .29


def tub(acc, loc, flavour, grp="Body", r=.11, h=.12):
    """Ice-cream tub: a coloured pot with the flavour mounded on top (gelato texture cells of the atlas)."""
    x, y, z = loc
    lathe(acc, [(r * .85, 0), (r, h), (r * 1.04, h + .005)], loc, C(CREAM), 10, 0, grp=grp, cap_top=False)
    lathe(acc, [(r, h), (r * .95, h + .02), (r * .6, h + .05), (0, h + .055)], loc, LAB, 10, 0, grp=grp, uv_cell=flavour, u_rep=1, v_range=(h, h + .055), cap_bottom=False)


def chest_freezer(acc, W, D, H, seed=0, kind="frozen", lid="slide", big=False):
    """Chest freezer: rounded navy tub on a kick plinth, chrome bumper rail, frosty rim, glass lids, goods inside."""
    rnd = random.Random(seed)
    t = .08
    hb = H - .32  # solid lower body up to the floor of the well
    rbox(acc, (W, D, hb), (0, 0, hb / 2 + .03), C(NAVY), .05, 3)
    for s_ in (-1, 1):
        rbox(acc, (W, t, H - .05 - hb + .04), (0, s_ * (D / 2 - t / 2), hb + (H - .05 - hb) / 2 + .01), C(NAVY), .03, 3)
        rbox(acc, (t, D - 2 * t + .02, H - .05 - hb + .04), (s_ * (W / 2 - t / 2), 0, hb + (H - .05 - hb) / 2 + .01), C(NAVY), .03, 3)
    rbox(acc, (W - .06, D - .06, .06), (0, 0, .03), C(INK), .02, 2)
    for s_ in (-1, 1):
        rbox(acc, (W - 2 * t, .008, .27), (0, s_ * (D / 2 - t - .004), H - .17), C(WHITE), .003, 1)
        rbox(acc, (.008, D - 2 * t, .27), (s_ * (W / 2 - t - .004), 0, H - .17), C(WHITE), .003, 1)
    for s in (-1, 1):
        rbox(acc, (W + .02, .03, .05), (0, s * (D / 2 + .005), .42), C(CHROME), .02, 3)
    rbox(acc, (W - .08, .01, .012), (0, -D / 2 - .002, H - .2), C(GOLD), .003, 1)
    if big:
        plate(acc, W - .3, .34, (0, -D / 2 - .004, .66), WOOD_L, .012, .04)
    for s_ in (-1, 1):
        rbox(acc, (W - .06, .05, .02), (0, s_ * (D / 2 - .045), H - .03), FROST, .01, 2)
        rbox(acc, (.05, D - .1, .02), (s_ * (W / 2 - .045), 0, H - .03), FROST, .01, 2)
    rbox(acc, (W - .16, D - .16, .02), (0, 0, H - .3), C(WHITE), .01, 1)
    frozen_fill(acc, -W / 2 + .08, W / 2 - .08, -D / 2 + .08, D / 2 - .08, H - .29, rnd, kind=kind)
    if lid == "slide":
        for k, y in enumerate((-.1, .1)):
            rbox(acc, (W - .1, D / 2 - .04, .012), (0, y * (D / .75) * .9 + (-.02 if k == 0 else .02), H + .006 + k * .012), GLASS, .005, 1)
        rbox(acc, (W - .06, .03, .02), (0, 0, H + .02), C(CHROME), .008, 1)
    else:  # curved glass hood (gelato chest)
        bm = bmesh.new()
        n = 6
        for i in range(n):
            a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
            v = [bm.verts.new((-W / 2 + .05, (D / 2 - .05) * math.cos(a0), .12 * math.sin(a0))), bm.verts.new((W / 2 - .05, (D / 2 - .05) * math.cos(a0), .12 * math.sin(a0))),
                 bm.verts.new((W / 2 - .05, (D / 2 - .05) * math.cos(a1), .12 * math.sin(a1))), bm.verts.new((-W / 2 + .05, (D / 2 - .05) * math.cos(a1), .12 * math.sin(a1)))]
            bm.faces.new(v)
        uv_box(bm); place(bm, (0, 0, H)); acc.add(bm, GLASS)
        for s in (-1, 1):
            rbox(acc, (.03, D - .06, .03), (s * (W / 2 - .05), 0, H + .015), C(CHROME), .01, 1)


def freezer_t1(acc):
    chest_freezer(acc, .98, .72, .9, 1)


def freezer_t2(acc):
    chest_freezer(acc, 1.48, .74, .92, 2, big=True)


def freezer_t3(acc):
    """Freezer vertical de 2 portas: upright, frosted door edges, frozen boxes and bags on the shelves."""
    def frozen_shelves(acc, x0, x1, y_front, depth, levels, seed=0, grp=None):
        for li, (z, avail) in enumerate(levels):
            rbox(acc, (x1 - x0, depth, .012), ((x0 + x1) / 2, y_front + depth / 2, z - .006), C(CHROME), .004, 1)
            stock(acc, [("box", .19, .045, .27, ["pack_4", "pack_10", "pack_1"]), ("bag", ["pack_15", "pack_6", "pack_12"]), ("box", .14, .1, .18, ["pack_7", "pack_13"])][(li + seed) % 3],
                  x0, x1, -1, -y_front, -y_front - .15, z, avail, li)
    upright_fridge(acc, 1.48, .86, 2.05, 2, frame_key="T_IK_R_Brushed", led=True, seed=3, stock_fn=frozen_shelves, nlev=5)
    for s in (-1, 1):
        rbox(acc, (.02, .012, 1.6), (s * .02, -.86 / 2 + .005, .98), FROST, .006, 1)


def freezer_t4(acc):
    """Ilha de congelados: a long island chest with sliding glass lids on both sides, an inox bumper, wood
    slat cladding and a lit navy canopy on two posts."""
    W, D = 2.48, 1.2
    chest_freezer(acc, W, D, .9, 4, big=False)
    for s in (-1, 1):
        n = 26
        for k in range(n):
            rbox(acc, (.034, .016, .36), (-W / 2 + .18 + k * (W - .36) / (n - 1), s * (D / 2 + .004), .6), WOOD_L, .006, 1)
    for x in (-W / 2 + .12, W / 2 - .12):
        tube(acc, [(x, 0, .9), (x, 0, 1.6)], .025, C(CHROME), 10)
    rbox(acc, (W - .1, .5, .1), (0, 0, 1.66), C(NAVY), .04, 3)
    for s in (-1, 1):
        rbox(acc, (W - .2, .02, .015), (0, s * .2, 1.605), ICE, .005, 1)
        rbox(acc, (W - .1, .008, .012), (0, s * .252, 1.7), C(GOLD), .003, 1)


def icecream_t1(acc):
    """Freezer de sorvetes: a small chest with a curved glass hood, tubs of every flavour and a cone emblem."""
    chest_freezer(acc, .98, .72, .82, 5, kind="tubs", lid="hood")
    cone(acc, (0, -.37, .45), .16)


def icecream_t2(acc):
    chest_freezer(acc, 1.48, .74, .85, 6, kind="tubs", lid="hood", big=True)
    cone(acc, (-.45, -.38, .46), .14)
    cone(acc, (.45, -.38, .46), .14)


def icecream_t3(acc):
    """Ilha de sorvetes: island with the hood on both sides, popsicle boxes at the ends, cone emblems."""
    chest_freezer(acc, 1.98, .96, .88, 7, kind="tubs", lid="hood")
    for s in (-1, 1):
        cone(acc, (0, s * .49, .46), .16, s)


def cone(acc, loc, size, side=-1):
    """Pictogram emblem: a waffle cone with two scoops (no text), standing proud of a front panel."""
    x, y, z = loc
    plate(acc, size * 1.25, size * 1.6, (x, y + side * .004, z), C(CREAM), .012, size * .3)
    k = size / .16
    bm = bmesh.new()
    v = [bm.verts.new((x - .045 * k, y + side * .012, z + .0)), bm.verts.new((x + .045 * k, y + side * .012, z + .0)), bm.verts.new((x, y + side * .012, z - .1 * k))]
    bm.faces.new(v)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.006)
    uv_box(bm, 6); acc.add(bm, "T_IK_Waffle")
    blob(acc, (.04 * k, .008, .035 * k), (x - .015 * k, y + side * .014, z + .03 * k), C("F4A6C1"), 2)
    blob(acc, (.04 * k, .008, .035 * k), (x + .02 * k, y + side * .016, z + .06 * k), C("7A4A2E"), 2)


def icecream_t4(acc):
    """Vitrine de gelato: curved-glass gelato display, rows of steel pans with mounded flavours and paddles,
    a navy body with light-wood slats, cones stacked on top, warm LED."""
    W, D = 2.48, .96
    rbox(acc, (W, D, .9), (0, 0, .45), C(NAVY), .04, 3)
    n = 28
    for k in range(n):
        rbox(acc, (.034, .016, .5), (-W / 2 + .16 + k * (W - .32) / (n - 1), -D / 2 - .004, .45), WOOD_L, .006, 1)
    for z in (.18, .72):
        rbox(acc, (W - .26, .01, .01), (0, -D / 2 - .012, z), C(GOLD), .003, 1)
    rbox(acc, (W - .06, D - .3, .04), (0, .1, .9), BRUSHED, .01, 1)
    rnd = random.Random(9)
    cols = 8
    for r_ in range(2):
        for c in range(cols):
            x = -W / 2 + .2 + c * (W - .4) / (cols - 1)
            y = -.12 + r_ * .26
            g = fills_for(x, W)
            rbox(acc, (.26, .22, .08), (x, y, .9), BRUSHED, .01, 1, grp=g)
            bm = blob_bm((.12, .1, .07), 2, .15, c + r_ * 9)
            uv = bm.loops.layers.uv.get("UVMap")
            for f in bm.faces:
                for l in f.loops:
                    l[uv].uv = rk_core.cell_uv("gelato_%d" % ((c + r_ * 3) % 8), (l.vert.co.x / .24 + .5) % 1, (l.vert.co.y / .2 + .5) % 1)
            place(bm, (x, y, .95)); acc.add(bm, LAB, g)
            if c % 3 == 0:
                rbox(acc, (.03, .2, .012), (x + .05, y, 1.0), C(CHROME), .005, 1, rot=(0, -30, 0), grp=g)
    # curved glass front and top
    bm = bmesh.new()
    prof = [(0, 0), (.07, .1), (.12, .22), (.14, .36), (.12, .45)]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        v = [bm.verts.new((-W / 2 + .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -b[0], b[1])), bm.verts.new((-W / 2 + .03, -b[0], b[1]))]
        bm.faces.new(v)
    uv_box(bm); place(bm, (0, -D / 2 + .3, .92)); acc.add(bm, GLASS)
    rbox(acc, (W - .04, .5, .012), (0, -.03, 1.37), GLASS, .004, 1)
    rbox(acc, (W, .26, .05), (0, D / 2 - .13, 1.38), C(NAVY), .015, 2)
    rbox(acc, (W - .1, .02, .012), (0, D / 2 - .25, 1.35), LED, .004, 1)
    for s in (-1, 1):
        rbox(acc, (.04, D - .02, .5), (s * (W / 2 - .02), 0, 1.15), C(NAVY), .02, 2)
    for k in range(3):
        for st in range(5):
            lathe(acc, [(.0, 0), (.03, .1)], (.6 + k * .12, .32, 1.405 + st * .02), "T_IK_Waffle", 8, 0, cap_top=False)


# ---------------------------------------------------------------- BAKERY
def baguette(acc, loc, L=.5, r=.035, yaw=0, pitch=0, grp="Body"):
    bm = blob_bm((L / 2, r, r * .85), 2, .05, int(L * 100))
    for v in bm.verts:
        v.co.z += .003 * math.sin(v.co.x * 40) * (v.co.z > 0)
    uv_box(bm, 3)
    place(bm, loc, (0, pitch, yaw)); acc.add(bm, "T_IK_Crust", grp)


def roll(acc, loc, r=.045, grp="Body", seed=0):
    bm = blob_bm((r, r * .9, r * .7), 1, .08, seed)
    uv_box(bm, 3); place(bm, loc); acc.add(bm, "T_IK_Crust", grp)


def loaf(acc, loc, grp="Body", yaw=0):
    bm = rbox_bm((.24, .12, .1), .045, 2)
    uv_box(bm, 3); place(bm, (loc[0], loc[1], loc[2] + .05), (0, 0, yaw)); acc.add(bm, "T_IK_Crust", grp)


def croissant(acc, loc, s=1.0, yaw=0, grp="Body"):
    x, y, z = loc
    pts = []
    for i in range(7):
        a = math.radians(-70 + i * 140 / 6 + yaw)
        pts.append((x + .06 * s * math.sin(a), y - .03 * s * math.cos(a), z + .022 * s))
    bm = rk_core.tube_bm(pts, lambda t: .026 * s * (.45 + .55 * math.sin(math.pi * t)), 7, 0)
    uv_box(bm, 3); acc.add(bm, "T_IK_Crust", grp)


def cake(acc, loc, r=.11, h=.09, top="F4A6C1", grp="Body"):
    lathe(acc, [(0, 0), (r, 0), (r, h), (r * .96, h + .012), (0, h + .015)], loc, C("F6E7C8"), 14, 0, grp=grp)
    lathe(acc, [(r * 1.01, h * .45), (r * 1.01, h * .6)], loc, C(top), 14, 0, grp=grp, cap_top=False, cap_bottom=False)
    lathe(acc, [(0, h + .012), (r * .97, h + .012), (r * .9, h + .03), (0, h + .035)], loc, C(top), 14, 0, grp=grp)
    for k in range(6):
        a = k * math.pi / 3
        blob(acc, (.012, .012, .012), (loc[0] + r * .7 * math.cos(a), loc[1] + r * .7 * math.sin(a), loc[2] + h + .045), C("C0392B"), 1, 0, k, grp=grp)


def basket(acc, w, d, h, loc, tilt=0, grp="Body"):
    """Wicker bread basket, optionally tilted towards the customer."""
    x, y, z = loc
    X = Xf(acc, (x, y, z), (tilt, 0, 0))
    open_box(X, w, d, h, (0, 0, 0), "T_IK_Wicker", .014, .006, 3)
    return X


def bakery_t1(acc):
    """Estante de pães: wooden rack, navy sides, two tilted wicker baskets of rolls, a basket of baguettes."""
    W, D, H = .96, .44, 1.5
    y0 = .02
    for s in (-1, 1):
        side_panel(acc, s * (W / 2 - .018), D, H, .036, .05, PAINT_NAVY, y0)
    inner = W - .072
    for z in (.1, .55, 1.0):
        rbox(acc, (inner, D - .02, .03), (0, y0, z), WOOD, .008, 2)
    rbox(acc, (W + .03, D + .03, .035), (0, y0, H + .017), WOOD, .012, 2)
    rbox(acc, (W + .03, .008, .01), (0, y0 - (D + .03) / 2 - .002, H + .017), C(GOLD), .003, 1)
    rbox(acc, (inner, .02, H - .1), (0, y0 + D / 2 - .012, H / 2), PLANKS, .005, 1, uv=1.3)
    for i, z in enumerate((.57, 1.02)):
        for bx in (-.21, .21):
            X = basket(acc, .4, .32, .12, (bx, y0 - .02, z + .03), 12)
            for r_ in range(2):
                for c in range(4):
                    roll(X, (-.14 + c * .093, -.07 + r_ * .13, .065), .042, "Anim Fill %d" % (0 if bx < 0 else 3), c + r_ * 4 + i)
    X = basket(acc, .84, .3, .2, (0, y0 - .02, .12), 0)
    for k in range(7):
        baguette(acc, (-.3 + k * .1, y0 - .04 + (k % 2) * .05, .26), .5, .03, 90, -70 + (k % 3) * 8, "Anim Fill %d" % (k * 4 // 7))
    lathe(acc, [(0, 0), (.04, 0), (.05, .08), (0, .08)], (.3, y0, H + .035), "T_IK_Terracotta", 10, 0)
    for k in range(5):
        tube(acc, [(.3 + .01 * math.cos(k), y0 + .01 * math.sin(k), H + .1), (.3 + .04 * math.cos(k * 1.3), y0 + .04 * math.sin(k * 1.3), H + .2)], .004, C("6DB84A"), 4)


def bakery_t2(acc):
    """Estante de cestos inclinados: bigger rack, three tiers of tilted baskets, baguettes upright in a tall
    basket, a navy crown with a blank plaque."""
    W, D, H = 1.46, .46, 1.62
    y0 = .02
    for s in (-1, 1):
        for fy in (-1, 1):
            rbox(acc, (.055, .055, H + .05), (s * (W / 2 - .028), y0 + fy * (D / 2 - .028), (H + .05) / 2), WOOD, .012, 2)
        rbox(acc, (.02, D - .1, H - .1), (s * (W / 2 - .028), y0, H / 2 + .02), PAINT_NAVY, .006, 1)
    inner = W - .1
    rbox(acc, (inner, .02, H - .1), (0, y0 + D / 2 - .03, H / 2 + .02), PLANKS, .005, 1, uv=1.4)
    for z in (.1, .5, .9, 1.3):
        rbox(acc, (inner + .04, D - .05, .032), (0, y0, z), WOOD, .008, 2)
    rbox(acc, (W + .04, D + .02, .04), (0, y0, H + .03), WOOD, .014, 2)
    plate(acc, W + .02, .3, (0, y0 - D / 2 + .05, H + .2), PAINT_NAVY, .03, .12)
    fr = frame_bm(W - .04, .26, .012, .1, .014)
    place(fr, (0, y0 - D / 2 + .033, H + .2)); acc.add(fr, C(GOLD))
    plate(acc, .46, .17, (0, y0 - D / 2 + .03, H + .2), C(CREAM), .012, .08)
    for i, z in enumerate((.52, .92, 1.32)):
        for j, bx in enumerate((-.45, 0, .45)):
            X = basket(acc, .42, .34, .11, (bx, y0 - .02, z + .03), 14)
            g = "Anim Fill %d" % min(3, j + (1 if bx > 0 else 0))
            if (i + j) % 3 == 0:
                for c in range(3):
                    croissant(X, (-.12 + c * .12, -.02, .025), 1.0, 0, g)
            elif (i + j) % 3 == 1:
                for r_ in range(2):
                    for c in range(4):
                        roll(X, (-.15 + c * .1, -.07 + r_ * .13, .06), .043, g, c + r_ * 5 + i)
            else:
                for c in range(3):
                    loaf(X, (-.13 + c * .13, 0, .012), g, 90)
    X = basket(acc, 1.3, .32, .22, (0, y0 - .02, .12), 0)
    for k in range(11):
        baguette(acc, (-.55 + k * .11, y0 - .04 + (k % 2) * .06, .28), .52, .03, 90, -72 + (k % 3) * 6, "Anim Fill %d" % (k * 4 // 11))


def bakery_t3(acc):
    """Vitrine de acrílico: navy cabinet with wood top, a wall of clear acrylic bins with flip lids (bread rolls
    inside), cakes under glass domes on top."""
    W, D, H = 1.96, .7, 1.85
    rbox(acc, (W, D, .7), (0, 0, .35), C(NAVY), .03, 3)
    plate(acc, W - .2, .44, (0, -D / 2 - .004, .36), WOOD, .016, .04)
    rbox(acc, (W - .1, .01, .012), (0, -D / 2 - .012, .64), C(GOLD), .003, 1)
    rbox(acc, (W + .02, D + .02, .04), (0, 0, .72), WOOD, .012, 2)
    rbox(acc, (W, .3, H - .74), (0, D / 2 - .15, .74 + (H - .74) / 2), C(NAVY), .03, 3)
    rbox(acc, (W - .1, .01, H - .9), (0, D / 2 - .31, .74 + (H - .74) / 2), "T_IK_V2_PaintCream", .006, 1)
    cols, rows = 6, 3
    bw, bh = (W - .14) / cols, .3
    for r_ in range(rows):
        for c in range(cols):
            x = -W / 2 + .07 + bw * (c + .5)
            z = .76 + r_ * (bh + .04)
            y = D / 2 - .5 + r_ * .04
            g = fills_for(x, W)
            rbox(acc, (bw - .02, .34, bh), (x, y, z + bh / 2), GLASS, .012, 1)
            rbox(acc, (bw - .02, .02, .025), (x, y - .17, z + bh - .02), C(CHROME), .006, 1, rot=(-12, 0, 0))
            for k in range(5):
                if (c + r_) % 2:
                    roll(acc, (x - .05 + (k % 3) * .05, y - .07 + (k // 3) * .09, z + .05), .035, g, k + c)
                else:
                    croissant(acc, (x - .03 + (k % 2) * .06, y - .08 + (k // 2) * .07, z + .005), .7, 20 * k, g)
    for k, x in enumerate((-.6, .0, .6)):
        cake(acc, (x, D / 2 - .15, H + .0), .1, .08, ["F4A6C1", "7A4A2E", "F2C23F"][k])
        lathe(acc, [(.13, 0), (.13, .16), (.08, .22), (0, .24)], (x, D / 2 - .15, H), GLASS, 12, 1, cap_bottom=False)
        lathe(acc, [(0, 0), (.015, 0), (.015, .03), (0, .03)], (x, D / 2 - .15, H + .24), C(GOLD), 8, 0)


def bakery_t4(acc):
    """Vitrine aquecida iluminada: a long heated glass case on a navy base with wood slats; warm LED over three
    trays (croissants, rolls, loaves) and a cake shelf on top; gold trims."""
    W, D = 1.98, .96
    rbox(acc, (W, D, .82), (0, 0, .41), C(NAVY), .04, 3)
    n = 22
    for k in range(n):
        rbox(acc, (.034, .016, .5), (-W / 2 + .16 + k * (W - .32) / (n - 1), -D / 2 - .004, .42), WOOD_L, .006, 1)
    for z in (.15, .69):
        rbox(acc, (W - .26, .01, .01), (0, -D / 2 - .012, z), C(GOLD), .003, 1)
    for s in (-1, 1):
        rbox(acc, (.04, D - .04, .96), (s * (W / 2 - .02), 0, .82 + .48), C(NAVY), .02, 2)
    rbox(acc, (W - .06, .012, .9), (0, -D / 2 + .06, 1.27), GLASS, .006, 1, rot=(-6, 0, 0))
    rbox(acc, (W - .06, D - .08, .012), (0, 0, 1.78), GLASS, .004, 1)
    rbox(acc, (W, D, .1), (0, 0, 1.84), C(NAVY), .04, 3)
    rbox(acc, (W + .01, .008, .012), (0, -D / 2 - .002, 1.86), C(GOLD), .003, 1)
    for i, z in enumerate((.84, 1.18, 1.5)):
        rbox(acc, (W - .1, D - .2, .016), (0, .02, z), BRUSHED, .004, 1)
        rbox(acc, (W - .14, .02, .01), (0, -.05, z + .3), LED, .004, 1)
        x = -W / 2 + .12
        k = 0
        while x < W / 2 - .1:
            g = fills_for(x, W)
            if i == 0:
                loaf(acc, (x + .06, -.05 + (k % 2) * .16, z + .008), g, 10 * (k % 3 - 1))
                x += .2
            elif i == 1:
                croissant(acc, (x + .05, -.08 + (k % 2) * .14, z + .008), 1.0, 15 * (k % 3), g)
                croissant(acc, (x + .05, .14, z + .008), 1.0, -15 * (k % 2), g)
                x += .14
            else:
                cake(acc, (x + .09, .02, z + .008), .085, .07, ["F4A6C1", "7A4A2E", "F2C23F", "E8F0D0"][k % 4], g)
                x += .24
            k += 1


# ---------------------------------------------------------------- PRODUCE
FRUIT = {
    "apple": ("D8352A", (.036, .036, .034), .05), "orange": ("F28C28", (.038, .038, .036), .03), "lemon": ("E8D23A", (.03, .03, .036), .05),
    "tomato": ("E2422E", (.034, .034, .028), .04), "lime": ("6DB84A", (.028, .028, .028), .04), "pepper": ("C0392B", (.035, .035, .045), .15),
    "onion": ("C98A4A", (.035, .035, .033), .05), "potato": ("B89260", (.04, .03, .028), .2),
}


def fruit(acc, kind, loc, grp, seed=0):
    col, size, noise = FRUIT[kind]
    blob(acc, size, loc, C(col), 1, noise, seed, grp=grp)


def produce_pile(acc, w, d, loc, kind, grp, seed=0, tilt=0, mound=.08):
    """A crate's worth of one produce: a mound in the produce's colour topped with whole fruits."""
    rnd = random.Random(seed)
    x, y, z = loc
    X = Xf(acc, (x, y, z), (tilt, 0, 0))
    if kind in FRUIT:
        col, size, _ = FRUIT[kind]
        blob(X, (w * .48, d * .46, mound), (0, 0, 0), C(col), 2, .05, seed, grp=grp)
        nx, ny = max(1, int(w / (size[0] * 2.1))), max(1, int(d / (size[1] * 2.1)))
        for i in range(nx):
            for j in range(ny):
                px_ = -w / 2 + (i + .5) * w / nx + rnd.uniform(-.005, .005)
                py = -d / 2 + (j + .5) * d / ny + rnd.uniform(-.005, .005)
                h = mound * (1 - (2 * px_ / w) ** 2 * .5 - (2 * py / d) ** 2 * .5)
                fruit(X, kind, (px_, py, h), grp, seed * 31 + i * 7 + j)
    elif kind == "banana":
        for k in range(int(w / .1)):
            for j in range(2):
                bx = -w / 2 + .06 + k * .1
                pts = [(bx + .03 * math.sin(t * 1.2), -d / 3 + j * d / 2.2 + (t - .5) * .14, .03 + .03 * math.sin(math.pi * t)) for t in (0, .25, .5, .75, 1)]
                for f in range(3):
                    tube(X, [(p[0] + f * .022, p[1], p[2] + f * .006) for p in pts], lambda t: .016 * (.5 + .5 * math.sin(math.pi * t)), C("F2CF3A"), 6, 0)
    elif kind == "lettuce":
        for i in range(max(1, int(w / .14))):
            for j in range(max(1, int(d / .14))):
                blob(X, (.065, .065, .055), (-w / 2 + .07 + i * .14, -d / 2 + .07 + j * .14, .04), C("6DB84A" if (i + j) % 2 else "8CCB5E"), 2, .3, i * 5 + j, grp=grp)
    elif kind == "carrot":
        for k in range(int(w / .045)):
            for j in range(2):
                cx, cy = -w / 2 + .03 + k * .045, -d / 4 + j * d / 2
                lathe(X, [(0, 0), (.016, .02), (.014, .13), (0, .15)], (cx, cy, .03), C("F07C1E"), 6, 0, rot=(90, 0, 0))
                blob(X, (.02, .02, .012), (cx, cy + .09, .04), C("4E9A3A"), 1, .3, k, grp=grp)
    elif kind == "melon":
        for i in range(max(1, int(w / .2))):
            for j in range(max(1, int(d / .2))):
                blob(X, (.1, .09, .085), (-w / 2 + .1 + i * .2, -d / 2 + .1 + j * .2, .07), C("D8D06A" if (i + j) % 2 else "8FB24A"), 2, .04, i + j * 3, grp=grp)
    return X


def crate(acc, w, d, h, loc, tilt=0):
    x, y, z = loc
    X = Xf(acc, (x, y, z), (tilt, 0, 0))
    open_box(X, w, d, h, (0, 0, 0), CRATE, .016, .006, 2.5)
    return X


def produce_t1(acc):
    """Banca de caixotes: a little wooden trestle stand with three tilted crates and two baskets underneath,
    a blank chalk slate on a stick."""
    W, D = .98, .72
    for s in (-1, 1):
        for fy in (-1, 1):
            rbox(acc, (.045, .045, .72 + fy * .12), (s * (W / 2 - .03), fy * (D / 2 - .05), (.72 + fy * .12) / 2), WOOD, .01, 2)
    rbox(acc, (W, .05, .05), (0, -D / 2 + .05, .58), WOOD, .01, 2)
    rbox(acc, (W, .05, .05), (0, D / 2 - .05, .82), WOOD, .01, 2)
    for s in (-1, 1):
        rbox(acc, (.04, D, .05), (s * (W / 2 - .03), 0, .7), WOOD, .01, 2, rot=(18, 0, 0))
    kinds = ["apple", "orange", "lemon"]
    for i, x in enumerate((-.31, 0, .31)):
        X = crate(acc, .3, .52, .15, (x, 0, .72), 18)
        produce_pile(X, .26, .48, (0, 0, .03), kinds[i], "Anim Fill %d" % min(3, i + (i > 0)), i)
    rbox(acc, (W - .1, .5, .02), (0, .02, .14), WOOD, .008, 1)
    for i, (x, kind) in enumerate(((-.22, "potato"), (.22, "onion"))):
        open_box(acc, .38, .34, .12, (x, .02, .15), "T_IK_Wicker", .014, .006, 3)
        produce_pile(acc, .34, .3, (x, .02, .17), kind, "Anim Fill %d" % (0 if i == 0 else 3), 7 + i, mound=.06)
    tube(acc, [(W / 2 - .05, -D / 2 + .02, .58), (W / 2 - .05, -D / 2 + .02, 1.0)], .008, WOOD, 6)
    fr = frame_bm(.2, .15, .014, .015, .018)
    place(fr, (W / 2 - .05, -D / 2 + .01, 1.0)); acc.add(fr, WOOD)
    plate(acc, .18, .13, (W / 2 - .05, -D / 2 + .016, 1.0), C("2F3A40"), .006, .012)


def produce_t2(acc):
    """Banca inclinada de madeira: stepped stand of six tilted crates on a navy-painted frame, scalloped navy
    canopy with a gold edge and a blank plaque."""
    W, D = 1.48, .74
    rbox(acc, (W - .04, D - .04, .5), (0, 0, .25), PAINT_NAVY, .02, 2)
    plate(acc, W - .2, .32, (0, -D / 2 + .016, .26), WOOD, .016, .03)
    rbox(acc, (W - .1, .01, .012), (0, -D / 2 + .006, .46), C(GOLD), .003, 1)
    rbox(acc, (W, D * .55, .3), (0, D / 4, .62), PAINT_NAVY, .02, 2)
    kinds = [["tomato", "pepper", "lime"], ["banana", "apple", "orange"]]
    for row, (y, z) in enumerate(((-.17, .52), (.17, .79))):
        for i, x in enumerate((-.47, 0, .47)):
            X = crate(acc, .44, .32, .14, (x, y, z), 16)
            produce_pile(X, .4, .28, (0, 0, .03), kinds[row][i], "Anim Fill %d" % (i + (i > 0)), row * 3 + i)
    for s in (-1, 1):
        rbox(acc, (.05, .05, 1.5), (s * (W / 2 - .025), D / 2 - .05, .75), WOOD, .012, 2)
    rbox(acc, (W + .06, .5, .04), (0, .02, 1.5), PAINT_NAVY, .02, 2, rot=(12, 0, 0))
    for k in range(9):
        x = -W / 2 + .08 + k * (W - .16) / 8
        blob(acc, (.085, .02, .06), (x, -.24, 1.42), C(NAVY), 2, 0)
    rbox(acc, (W + .06, .01, .012), (0, -.24, 1.46), C(GOLD), .003, 1)
    plate(acc, .5, .15, (0, .25, 1.62), C(CREAM), .02, .07)


def produce_t3(acc):
    """Banca de metal com espelho: steel stand with two stepped rows of angled bins, a mirror back panel that
    doubles the display, navy canopy with lights, gold trims."""
    W, D = 1.98, .98
    rbox(acc, (W, D - .1, .4), (0, -.05, .2), C(NAVY), .03, 3)
    rbox(acc, (W - .06, .02, .1), (0, -D / 2 + .01, .06), C(BLUE), .01, 2)
    rbox(acc, (W - .1, .01, .012), (0, -D / 2 + .002, .36), C(GOLD), .003, 1)
    rbox(acc, (W, .1, 1.95), (0, D / 2 - .05, .975), C(NAVY), .03, 3)
    rbox(acc, (W - .12, .01, .95), (0, D / 2 - .105, 1.05), "T_IK_V2_Chrome", .004, 1)
    kinds = [["apple", "orange", "lemon", "lime"], ["lettuce", "tomato", "carrot", "melon"]]
    for row, (y, z, t) in enumerate(((-.22, .44, 18), (.16, .66, 22))):
        for i in range(4):
            x = -W / 2 + .26 + i * (W - .52) / 3
            X = Xf(acc, (x, y, z), (t, 0, 0))
            open_box(X, .44, .36, .1, (0, 0, 0), BRUSHED, .012, .006, 2)
            rbox(X, (.44, .012, .04), (0, -.186, .07), C(BLUE), .004, 1)
            produce_pile(X, .4, .32, (0, 0, .02), kinds[row][i], "Anim Fill %d" % i, row * 4 + i)
    rbox(acc, (W + .04, .4, .08), (0, D / 2 - .2, 1.98), C(NAVY), .03, 3)
    for k in range(4):
        x = -W / 2 + .3 + k * (W - .6) / 3
        lathe(acc, [(0, 0), (.06, 0), (.08, -.06), (0, -.07)], (x, D / 2 - .3, 1.94), C(INK), 12, 0)
        lathe(acc, [(.06, -.06), (0, -.065)], (x, D / 2 - .3, 1.94), LED, 12, 0, cap_top=False)
    rbox(acc, (W + .05, .008, .012), (0, D / 2 - .405, 2.0), C(GOLD), .003, 1)
    plate(acc, .6, .18, (0, D / 2 - .41, 1.84), C(CREAM), .012, .08)


def produce_t4(acc):
    """Ilha refrigerada com névoa: double-sided chilled island, angled bins both sides, a chrome misting bar,
    light-wood slat cladding, a lit navy canopy on posts."""
    W, D = 2.46, 1.2
    rbox(acc, (W, D, .55), (0, 0, .275), C(NAVY), .04, 3)
    for s in (-1, 1):
        n = 28
        for k in range(n):
            rbox(acc, (.034, .016, .34), (-W / 2 + .16 + k * (W - .32) / (n - 1), s * (D / 2 + .004), .27), WOOD_L, .006, 1)
        rbox(acc, (W - .26, .01, .01), (0, s * (D / 2 + .012), .48), C(GOLD), .003, 1)
        rbox(acc, (W - .3, .02, .02), (0, s * (D / 2 - .03), .03), LED, .006, 1)
    rbox(acc, (W - .06, .2, .3), (0, 0, .7), C(NAVY), .03, 3)
    kinds = [["apple", "orange", "lemon", "tomato", "lime"], ["lettuce", "pepper", "carrot", "melon", "onion"]]
    for si, s in enumerate((-1, 1)):
        for i in range(5):
            x = -W / 2 + .25 + i * (W - .5) / 4
            X = Xf(acc, (x, s * .3, .58), (16 if s < 0 else -16, 0, 0))
            open_box(X, .44, .44, .1, (0, 0, 0), BRUSHED, .012, .006, 2)
            produce_pile(X, .4, .4, (0, 0, .02), kinds[si][i], "Anim Fill %d" % min(3, i * 4 // 5), si * 5 + i)
    tube(acc, [(-W / 2 + .1, 0, .9), (W / 2 - .1, 0, .9)], .015, C(CHROME), 8)
    for k in range(10):
        x = -W / 2 + .2 + k * (W - .4) / 9
        for s in (-1, 1):
            lathe(acc, [(0, 0), (.008, 0), (.006, .02), (0, .02)], (x, s * .02, .885), C(CHROME), 6, 0, rot=(90 * s + 180, 0, 0))
    for x in (-W / 2 + .1, W / 2 - .1):
        tube(acc, [(x, 0, .85), (x, 0, 1.85)], .03, C(NAVY), 10)
    rbox(acc, (W + .02, .6, .12), (0, 0, 1.9), C(NAVY), .05, 3)
    for s in (-1, 1):
        rbox(acc, (W - .1, .03, .015), (0, s * .24, 1.835), LED, .005, 1)
        rbox(acc, (W + .02, .008, .012), (0, s * .302, 1.92), C(GOLD), .003, 1)
    plate(acc, .7, .18, (0, -.305, 2.06), C(CREAM), .02, .08)


BUILDERS.update({
    "drinks": [drinks_t1, drinks_t2, drinks_t3, drinks_t4],
    "dairy": [dairy_t1, dairy_t2, dairy_t3, dairy_t4],
    "freezer": [freezer_t1, freezer_t2, freezer_t3, freezer_t4],
    "icecream": [icecream_t1, icecream_t2, icecream_t3, icecream_t4],
    "bakery": [bakery_t1, bakery_t2, bakery_t3, bakery_t4],
    "produce": [produce_t1, produce_t2, produce_t3, produce_t4],
})


# ================================================================================================ CÂMARA FRIA (cold room)
# Lives in the stock area (stockroom / depósito, then the central warehouse), not on the sales floor.
TIERS.update({
    "coldroom": [
        ("T1", "Freezer de estoque", 1.25, .75, .95),
        ("T2", "Mini câmara fria", 2.00, 2.00, 2.55),
        ("T3", "Câmara fria", 3.00, 2.50, 2.85),
        ("T4", "Câmara frigorífica", 5.00, 4.00, 3.50),
    ],
})
PANEL = "T_IK_V2_PaintCream"   # insulated panels (cream, never repainted)
CARDBOARD = "T_IK_Cardboard"


def supplier_box(acc, loc, w=.4, d=.3, h=.25, yaw=0, grp="Body"):
    """Plain cardboard case with a tape strip (no print)."""
    x, y, z = loc
    bm = rbox_bm((w, d, h), .008, 1); uv_box(bm, 2); place(bm, (x, y, z + h / 2), (0, 0, yaw)); acc.add(bm, CARDBOARD, grp)
    bm = rbox_bm((w + .002, .06, .004), 0, 1); uv_box(bm); place(bm, (x, y, z + h + .001), (0, 0, yaw)); acc.add(bm, C("C9A06A"), grp)


def condenser(acc, loc, w=.8, d=.5, h=.45, yaw=0):
    """Condensing unit: navy cabinet, round fan grille with blades, copper pipes."""
    x, y, z = loc
    X = Xf(acc, (x, y, z), (0, 0, yaw))
    rbox(X, (w, d, h), (0, 0, h / 2), C(NAVY), .03, 3)
    r = min(h, w) * .38
    lathe(X, [(0, 0), (r + .02, 0), (r + .02, .02), (0, .02)], (-w * .12, -d / 2 - .0, h / 2), C(INK), 20, 0, rot=(90, 0, 0))
    for k in range(4):
        rbox(X, (r * 2, .006, .012), (-w * .12, -d / 2 - .025, h / 2), C("3A4450"), 0, 1, rot=(0, 45 * k, 0))
    for k in range(5):
        lathe(X, [(r * (k + 1) / 5, 0), (r * (k + 1) / 5 + .006, 0)], (-w * .12, -d / 2 - .03, h / 2), C(CHROME), 20, 0, rot=(90, 0, 0), cap_top=False, cap_bottom=False)
    for k in range(6):
        rbox(X, (.16, .01, .02), (w * .3, -d / 2 - .004, .1 + k * (h - .2) / 5), C("3A4450"), 0, 1)
    tube(X, [(w / 2 - .05, d / 2 - .1, .12), (w / 2 + .08, d / 2 - .1, .12), (w / 2 + .08, d / 2 - .1, -.2)], .014, C("C87533"), 8)
    tube(X, [(w / 2 - .05, d / 2 - .2, .2), (w / 2 + .14, d / 2 - .2, .2), (w / 2 + .14, d / 2 - .2, -.2)], .01, C("C87533"), 8)
    rbox(X, (w + .02, .008, .01), (0, -d / 2 - .002, h - .03), C(GOLD), .003, 1)


def panel_box(acc, W, D, H, door_x=0, door_w=.9, door_h=2.0, seam=.6):
    """Walk-in insulated box: cream sandwich panels with seams, coved navy kick band and corner guards, a gold
    line under the roof edge. Leaves the door opening free on the front (-Y) wall."""
    t = .1
    # walls
    for s in (-1, 1):
        rbox(acc, (t, D, H), (s * (W / 2 - t / 2), 0, H / 2), PANEL, .02, 2, uv=1.2)
    rbox(acc, (W, t, H), (0, D / 2 - t / 2, H / 2), PANEL, .02, 2, uv=1.2)
    left = door_x - door_w / 2 - .06
    right = door_x + door_w / 2 + .06
    if left > -W / 2:
        rbox(acc, (left + W / 2, t, H), ((left - W / 2) / 2, -D / 2 + t / 2, H / 2), PANEL, .02, 2, uv=1.2)
    if right < W / 2:
        rbox(acc, (W / 2 - right, t, H), ((right + W / 2) / 2, -D / 2 + t / 2, H / 2), PANEL, .02, 2, uv=1.2)
    rbox(acc, (right - left, t, H - door_h - .1), (door_x, -D / 2 + t / 2, door_h + .1 + (H - door_h - .1) / 2), PANEL, .02, 2, uv=1.2)
    rbox(acc, (W + .04, D + .04, .08), (0, 0, H + .04), PANEL, .03, 3)
    # panel seams
    for s in (-1, 1):
        n = int(D / seam)
        for k in range(1, n + 1):
            y = -D / 2 + k * D / (n + 1)
            rbox(acc, (.006, .012, H - .3), (s * (W / 2 + .001), y, H / 2 + .1), C("D9CFB8"), 0, 1)
    n = int(W / seam)
    for k in range(1, n + 1):
        x = -W / 2 + k * W / (n + 1)
        if not (left - .02 < x < right + .02):
            rbox(acc, (.012, .006, H - .3), (x, -D / 2 - .001, H / 2 + .1), C("D9CFB8"), 0, 1)
        rbox(acc, (.012, .006, H - .3), (x, D / 2 + .001, H / 2 + .1), C("D9CFB8"), 0, 1)
    # navy kick band and corner guards, gold line
    for s in (-1, 1):
        rbox(acc, (.03, D + .02, .28), (s * (W / 2 + .012), 0, .14), C(NAVY), .01, 2)
        if s > 0:
            rbox(acc, (W + .02, .03, .28), (0, s * (D / 2 + .012), .14), C(NAVY), .01, 2)
        for fy in (-1, 1):
            rbox(acc, (.08, .08, H - .1), (s * (W / 2 + .01), fy * (D / 2 + .01), H / 2), C(NAVY), .03, 3)
    for (a, b) in ((-W / 2, left), (right, W / 2)):
        if b - a > .05:
            rbox(acc, (b - a, .03, .28), ((a + b) / 2, -D / 2 - .012, .14), C(NAVY), .01, 2)
    for s in (-1, 1):
        rbox(acc, (W + .04, .01, .012), (0, s * (D / 2 + .022), H - .06), C(GOLD), .003, 1)
        rbox(acc, (.01, D + .04, .012), (s * (W / 2 + .022), 0, H - .06), C(GOLD), .003, 1)
    return left, right


def insulated_door(acc, x, y, w, h, open_frac=0.0, slide=False):
    """Thick insulated door with a navy frame, a chunky lever handle and frost round its seal."""
    fr = frame_bm(w + .16, h + .1, .06, .03, .08)
    place(fr, (x, y - .02, (h + .1) / 2)); acc.add(fr, C(NAVY))
    for s in (-1, 1):
        rbox(acc, (.012, .02, h), (x + s * (w / 2 + .005), y - .055, h / 2 + .02), FROST, .004, 1)
    rbox(acc, (w + .02, .02, .012), (x, y - .055, h + .02), FROST, .004, 1)
    if slide:
        dx = w * open_frac
        rbox(acc, (w + .1, .1, h + .02), (x + dx, y - .12, h / 2 + .02), PANEL, .03, 3)
        rbox(acc, (w + .3 + dx, .06, .08), (x + dx / 2 + .1, y - .1, h + .1), BRUSHED, .02, 2)
        for k in range(2):
            lathe(acc, [(0, 0), (.04, 0), (.04, .03), (0, .03)], (x + dx - w / 2 + .15 + k * (w - .3), y - .15, h + .08), C(INK), 12, 0, rot=(90, 0, 0))
        tube(acc, [(x + dx - w / 2 + .08, y - .19, h * .4), (x + dx - w / 2 + .08, y - .19, h * .6)], .02, C(CHROME), 8)
        rbox(acc, (w + .06, .012, .012), (x + dx, y - .176, h * .9), C(GOLD), .003, 1)
    else:
        rbox(acc, (w, .1, h), (x, y - .06, h / 2 + .02), PANEL, .03, 3)
        rbox(acc, (w - .1, .012, .012), (x, y - .116, h * .88), C(GOLD), .003, 1)
        for z in (h * .2, h * .8):
            rbox(acc, (.1, .06, .14), (x - w / 2 + .02, y - .12, z), C(CHROME), .02, 2)
        rbox(acc, (.08, .06, .22), (x + w / 2 - .12, y - .14, h * .5), C(CHROME), .02, 2)
        tube(acc, [(x + w / 2 - .12, y - .18, h * .5 + .06), (x + w / 2 - .32, y - .2, h * .5 + .06)], .02, C(CHROME), 8)
        lathe(acc, [(0, 0), (.11, 0), (.11, .02), (0, .02)], (x, y - .11, h * .7), C(NAVY), 20, 0, rot=(90, 0, 0))
        lathe(acc, [(0, 0), (.09, 0), (.09, .006), (0, .006)], (x, y - .13, h * .7), GLASS, 20, 0, rot=(90, 0, 0))
        blob(acc, (.07, .004, .03), (x - .01, y - .133, h * .7 - .05), FROST, 1, .3, 3)


def strip_curtain(acc, x, y, w, h, n=None):
    n = n or int(w / .2)
    for k in range(n):
        rbox(acc, (w / n - .01, .006, h), (x - w / 2 + (k + .5) * w / n, y, h / 2 + .02), GLASS, .002, 1)
    rbox(acc, (w + .06, .05, .06), (x, y, h + .05), BRUSHED, .01, 1)


def temp_display(acc, x, y, z):
    rbox(acc, (.18, .05, .12), (x, y, z), C(INK), .015, 2)
    rbox(acc, (.13, .006, .05), (x, y - .026, z + .01), "E_7BD3F7", 0, 1)
    for k in range(3):
        rbox(acc, (.02, .006, .015), (x - .04 + k * .04, y - .026, z - .035), C(CREAM), 0, 1)


def interior_glimpse(acc, x, y_open, w, d, h):
    """What shows through an open door: a dark cold interior, steel racks with cases, a blue-white light."""
    rbox(acc, (w + .4, .02, h), (x, y_open + d, h / 2), C("2B3A55"), 0, 1)
    rbox(acc, (w + .4, d, .02), (x, y_open + d / 2, h - .01), "E_DDF4FF", 0, 1)
    for k in range(3):
        z = .3 + k * .55
        rbox(acc, (w + .3, .5, .03), (x, y_open + d - .3, z), BRUSHED, .005, 1)
        for i in range(int((w + .2) / .42)):
            supplier_box(acc, (x - (w + .2) / 2 + .21 + i * .42, y_open + d - .3, z + .015), .36, .4, .26 + .05 * ((i + k) % 2), 0)


def coldroom_t1(acc):
    """Freezer de estoque: a cream stockroom chest freezer with a navy lid trim, frost seal, compressor grille,
    a dial thermometer and two cases on the lid."""
    W, D, H = 1.22, .72, .88
    rbox(acc, (W, D, H - .08), (0, 0, (H - .08) / 2 + .04), PANEL, .05, 3)
    rbox(acc, (W - .06, D - .06, .06), (0, 0, .03), C(INK), .02, 2)
    rbox(acc, (W + .01, D + .01, .07), (0, 0, H - .02), C(NAVY), .03, 3)
    rbox(acc, (W - .04, .01, .015), (0, -D / 2 - .002, H - .07), FROST, .004, 1)
    rbox(acc, (W - .1, .008, .01), (0, -D / 2 - .004, H - .12), C(GOLD), .003, 1)
    rbox(acc, (.3, .04, .05), (0, -D / 2 - .02, H - .05), C(CHROME), .015, 2)
    for k in range(7):
        rbox(acc, (.012, .3, .02), (W / 2 + .004, -.0, .12 + k * .05), C("3A4450"), 0, 1)
    lathe(acc, [(0, 0), (.06, 0), (.06, .02), (0, .02)], (-W / 2 + .18, -D / 2 - .0, H * .55), C(CHROME), 16, 0, rot=(90, 0, 0))
    lathe(acc, [(0, 0), (.05, 0), (.05, .004), (0, .004)], (-W / 2 + .18, -D / 2 - .02, H * .55), C(WHITE), 16, 0, rot=(90, 0, 0))
    rbox(acc, (.006, .004, .04), (-W / 2 + .19, -D / 2 - .024, H * .55 + .01), C("C0392B"), 0, 1, rot=(0, 30, 0))
    supplier_box(acc, (-.25, .02, H + .015), .42, .32, .22, 4)
    supplier_box(acc, (.22, .0, H + .015), .36, .3, .18, -6)


def coldroom_t2(acc):
    """Mini câmara fria: a 2 x 2 m walk-in box with a hinged insulated door, round frosted window, a condensing
    unit on the roof, temperature display, frost at the seals."""
    W, D, H = 2.0, 2.0, 2.3
    l, r = panel_box(acc, W, D, H, -.15, .85, 1.95)
    insulated_door(acc, -.15, -D / 2, .85, 1.95)
    temp_display(acc, .62, -D / 2 - .03, 1.55)
    condenser(acc, (.25, .1, H + .08), .9, .55, .45)
    for k in range(2):
        tube(acc, [(-.2 + k * .1, .3, H + .08), (-.2 + k * .1, .3, H + .2), (-.2 + k * .1, .1, H + .2)], .014, C("C87533"), 8)
    rbox(acc, (.9, .4, .03), (-.15, -D / 2 - .2, .015), BRUSHED, .01, 1)
    lathe(acc, [(0, 0), (.08, 0), (.06, .06), (0, .07)], (-.15, -D / 2 - .06, 2.12), LED_COOL, 12, 0, rot=(0, 0, 0))
    rbox(acc, (.2, .06, .05), (-.15, -D / 2 - .04, 2.17), C(NAVY), .02, 2)


def coldroom_t3(acc):
    """Câmara fria: 3 x 2.5 m with a sliding insulated door half open on its rail, PVC strip curtain, racks of
    cases inside, two roof condensers, steel threshold ramp, door light, bumper rails."""
    W, D, H = 3.0, 2.5, 2.6
    dx, dw, dh = -.35, 1.1, 2.1
    interior_glimpse(acc, dx, -D / 2 + .1, dw, 1.2, dh)
    l, r = panel_box(acc, W, D, H, dx, dw, dh)
    strip_curtain(acc, dx, -D / 2 + .12, dw, dh)
    insulated_door(acc, dx, -D / 2, dw, dh, .55, slide=True)
    temp_display(acc, r + .25, -D / 2 - .03, 1.6)
    for s in (-1, 1):
        rbox(acc, (.03, D + .06, .1), (s * (W / 2 + .04), 0, .5), C(BLUE), .02, 2)
    for x in (-.7, .7):
        condenser(acc, (x, .2, H + .08), .9, .55, .45)
    rbox(acc, (dw + .2, .5, .04), (dx, -D / 2 - .25, .02), BRUSHED, .01, 1, rot=(-3, 0, 0))
    rbox(acc, (.3, .07, .06), (dx, -D / 2 - .05, dh + .32), C(NAVY), .02, 2)
    rbox(acc, (.24, .02, .02), (dx, -D / 2 - .09, dh + .29), LED_COOL, .006, 1)


def coldroom_t4(acc):
    """Câmara frigorífica: the big chamber of the central warehouse: sectional insulated dock door half raised
    with a black seal and strip curtain, a personnel door, three condensers on the roof, bollards, a pallet of
    cases and a pallet jack in front, frost and cold light."""
    W, D, H = 5.0, 4.0, 3.2
    dx, dw, dh = -.6, 2.4, 2.7
    interior_glimpse(acc, dx, -D / 2 + .1, dw, 2.0, dh)
    l, r = panel_box(acc, W, D, H, dx, dw, dh, .75)
    strip_curtain(acc, dx, -D / 2 + .12, dw, dh)
    # sectional door raised to 60%: panels stacked above the opening, the lowest ones still down
    raised = .6
    for k in range(5):
        z = dh * raised + k * .27
        rbox(acc, (dw + .1, .07, .25), (dx, -D / 2 - .05, min(z, dh - .1) + .14), PANEL, .02, 2)
        rbox(acc, (dw + .08, .075, .012), (dx, -D / 2 - .05, min(z, dh - .1) + .27), C("D9CFB8"), 0, 1)
    for s in (-1, 1):
        rbox(acc, (.12, .18, dh + .3), (dx + s * (dw / 2 + .1), -D / 2 - .09, (dh + .3) / 2), C(INK), .04, 3)
        rbox(acc, (.012, .02, dh), (dx + s * (dw / 2 + .03), -D / 2 - .19, dh / 2), FROST, .004, 1)
    rbox(acc, (dw + .44, .2, .3), (dx, -D / 2 - .1, dh + .2), C(INK), .04, 3)
    rbox(acc, (dw + .44, .01, .012), (dx, -D / 2 - .205, dh + .12), C(GOLD), .003, 1)
    rbox(acc, (.3, .07, .06), (dx, -D / 2 - .22, dh + .42), C(NAVY), .02, 2)
    rbox(acc, (.24, .02, .02), (dx, -D / 2 - .26, dh + .39), LED_COOL, .006, 1)
    temp_display(acc, 1.0, -D / 2 - .03, 1.6)
    for x in (-1.6, 0, 1.6):
        condenser(acc, (x, .6, H + .08), 1.1, .6, .5)
    # bollards and a pallet with cases + pallet jack
    for x in (dx - dw / 2 - .35, dx + dw / 2 + .35):
        lathe(acc, [(0, 0), (.08, 0), (.08, 1.0), (.06, 1.05), (0, 1.06)], (x, -D / 2 - .45, 0), C(NAVY), 14, 0)
        lathe(acc, [(.081, .82), (.081, .88)], (x, -D / 2 - .45, 0), C(GOLD), 14, 0, cap_top=False, cap_bottom=False)
    px_, py = dx + dw / 2 + 1.05, -D / 2 - .7
    for k in range(3):
        rbox(acc, (1.2, .1, .1), (px_, py - .45 + k * .45, .05), WOOD_L, .01, 1)
    rbox(acc, (1.2, 1.0, .03), (px_, py, .115), WOOD_L, .006, 1)
    for i in range(3):
        for j in range(2):
            for st in range(2):
                supplier_box(acc, (px_ - .4 + i * .4, py - .25 + j * .5, .13 + st * .3), .38, .46, .28, 0)
    rbox(acc, (.55, .2, .08), (px_ - .95, py - .25, .07), C(NAVY), .02, 2)
    tube(acc, [(px_ - 1.2, py - .25, .1), (px_ - 1.35, py - .25, .9)], .02, C(INK), 8)
    rbox(acc, (.2, .05, .05), (px_ - 1.37, py - .25, .93), C(INK), .02, 2)


BUILDERS.update({"coldroom": [coldroom_t1, coldroom_t2, coldroom_t3, coldroom_t4]})


# ================================================================================================ Quitanda fit shot
QUIT_AT = Vector((30, -30, 0))
QUIT_FLOOR = (-4.1, -2.4, 4.1, 4.1)      # CheckoutStall plan "Era5_Quitanda" (model metres)
QUIT_COUNTER = (1.35, -1.7, 3.15, -.3)
QUIT_QUEUE_X = 3.65                       # the line runs along the east wall


def load_shop(collection, at, root_name, hide=("FacadeTop", "ShellTop", "Awning", "_Sign", "winTop", "Roof", "roof")):
    """Appends one of the eras' shop models (eras_v2.blend), scaled like in the game, roof and sign hidden."""
    if bpy.data.objects.get(root_name):
        return bpy.data.objects[root_name]
    path = os.path.join(REPO, "unity", "CheckoutSimulator", "ArtSource", "eras_v2", "eras_v2.blend")
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [collection]
    c = coll("FT " + root_name, coll("Fixture tiers"))
    root = bpy.data.objects.new(root_name, None)
    c.objects.link(root)
    for col in dst.collections:
        c.children.link(col)
        for o in list(col.all_objects):
            if o.parent is None:
                o.parent = root
            if any(k in o.name for k in hide):
                o.hide_render = o.hide_viewport = True
    root.scale = (CONV_SCALE,) * 3
    root.location = at
    tex = os.path.join(ASSETS, "Resources", "CheckoutEras")
    for im in bpy.data.images:
        if im.filepath and not os.path.exists(bpy.path.abspath(im.filepath)):
            cand = os.path.join(tex, os.path.basename(im.filepath))
            if os.path.exists(cand):
                im.filepath = cand
                im.reload()
    return root


def load_shop_fbx(name, at, root_name, hide=("ShellTop", "FacadeTop", "Awning", "_Sign", "winTop")):
    """Imports the shop exactly as the game ships it (Assets/Resources/CheckoutEras/<name>.fbx, same atlas). The FBX
    comes in turned 180° (Blender -x, -y = Unity x, z): the root turns it back and scales it like the game (1.2)."""
    if bpy.data.objects.get(root_name):
        return bpy.data.objects[root_name]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ASSETS, "Resources", "CheckoutEras", name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    c = coll("FT " + root_name, coll("Fixture tiers"))
    root = bpy.data.objects.new(root_name, None)
    c.objects.link(root)
    for o in new:
        for uc in list(o.users_collection):
            uc.objects.unlink(o)
        c.objects.link(o)
        if o.parent is None:
            o.parent = root
        if any(k in o.name for k in hide):
            o.hide_render = o.hide_viewport = True
    root.rotation_euler = (0, 0, math.pi)
    root.scale = (CONV_SCALE,) * 3
    root.location = at
    return root


def quitanda_layout():
    """The seven fixtures of the Quitanda at their proposed small tiers (T1/T2 only), against the walls, the
    east lane left free for the queue, the counter untouched."""
    load_shop_fbx("Era5_Quitanda", QUIT_AT, "QUIT root")
    k = CONV_SCALE
    x0, y0, x1, y1 = (v * k for v in QUIT_FLOOR)
    O = QUIT_AT
    c = coll("FT QUIT root", coll("Fixture tiers"))
    for o in list(c.objects):
        if o.name.startswith(("FIX ", "OUT ")) or (o.parent and o.parent.name.startswith("FIX ")):
            bpy.data.objects.remove(o, do_unlink=True)
    green = "3FBF6A"
    back = y1
    lane = QUIT_QUEUE_X * k - .45   # keep x > lane free (queue)
    place_list = [  # (kind, tier, w, d, x, y, rot)
        ("shelf", "T2", 1.5, .5, x0 + .8, back - .25, 0),
        ("shelf", "T1", 1.0, .5, x0 + 2.15, back - .25, 0),
        ("bakery", "T2", 1.5, .5, x0 + 3.5, back - .25, 0),
        ("dairy", "T2", 1.5, .75, x0 + 5.15, back - .375, 0),
        ("freezer", "T2", 1.5, .75, x0 + 6.85, back - .375, 0),
        ("drinks", "T2", 1.25, .75, x0 + .375, back - 1.9, 90),
        ("produce", "T2", 1.5, .75, x0 + .375, back - 3.3, 90),
    ]
    for kind, tier, w, d, x, y, rot in place_list:
        loc = O + Vector((x, y, 0))
        instance(kind, tier, loc, rot, "FIX %s %s" % (kind, tier), "FT QUIT root")
        outline("OUT %s" % kind, w, d, loc, rot, green, "FT QUIT root")
    return lane


def quitanda_shot():
    sc = bpy.context.scene
    quitanda_layout()
    bpy.context.view_layer.update()
    for o in sc.objects:
        if o.type not in ("MESH", "EMPTY") or o.hide_viewport:
            continue
        if o.type == "MESH":
            ctr = sum((o.matrix_world @ Vector(cc) for cc in o.bound_box), Vector()) / 8
        else:
            ctr = o.matrix_world.translation
        o.hide_render = (ctr - QUIT_AT).xy.length > 9
    camera(QUIT_AT + Vector((.3, 1.4, .3)), (-.1, -1, 1.45), 15.5, 34)
    return render("quitanda_fit_tiers", (1800, 1200))


# ================================================================================================ BATCH B: sectors, ATM, machines, carts
# Sector counters keep TODAY's footprint in every tier (they only arrive in the big shops); the tiers change the
# finish and the equipment: T1 balcão simples -> T2 balcão com vitrine -> T3 balcão gourmet.
SECTORS = {  # id: (name, footprint w, d)
    "padaria": ("Padaria", 4.0, 3.25), "acougue": ("Açougue", 4.0, 3.25), "queijaria": ("Queijaria", 4.0, 3.25),
    "peixaria": ("Peixaria", 4.0, 3.25), "sorvetes": ("Sorveteria", 3.25, 2.5), "adega": ("Adega", 3.25, 2.0),
    "sucos": ("Sucos", 3.25, 1.75),
}
for _sid, (_nm, _w, _d) in SECTORS.items():
    TIERS["sector-" + _sid] = [
        ("T1", "%s: balcão simples" % _nm, _w, _d, 2.4),
        ("T2", "%s: balcão com vitrine" % _nm, _w, _d, 2.6),
        ("T3", "%s: balcão gourmet" % _nm, _w, _d, 2.9),
    ]
TIERS.update({
    "atm": [("T1", "Caixa eletrônico", .75, .85, 1.95), ("T2", "Caixa eletrônico duplo", 1.5, .85, 2.2),
            ("T3", "Mini agência", 2.0, 1.25, 2.6)],
    "gumball": [("T1", "Máquina de chiclete", .5, .5, 1.25), ("T2", "Máquina dupla", 1.0, .5, 1.4),
                ("T3", "Torre de chicletes", 1.0, 1.0, 2.1)],
    "claw": [("T1", "Máquina de pelúcia", .75, .75, 1.95), ("T2", "Máquina de pelúcia dupla", 1.5, .85, 2.05),
             ("T3", "Pelúcia gigante", 1.5, 1.5, 2.45)],
    "carts": [("T1", "Cestinhas", .75, .5, .95), ("T2", "Carrinhos", 1.5, .75, 1.1),
              ("T3", "Carrinhos grandes", 2.0, 1.0, 2.2)],
})
BASE_Y.update({"sector-padaria": -86.0, "sector-acougue": -95.0, "sector-queijaria": -104.0, "sector-peixaria": -113.0,
               "sector-sorvetes": -122.0, "sector-adega": -130.0, "sector-sucos": -138.0,
               "atm": -146.0, "gumball": -154.0, "claw": -162.0, "carts": -170.0})
TILE = "T_IK_Tile"


# ---------------------------------------------------------------- goods of each sector
def steak(acc, loc, s=1.0, yaw=0, grp="Body"):
    bm = blob_bm((.075 * s, .05 * s, .014), 2, .12, int(loc[0] * 100) % 50)
    uv_box(bm, 4); place(bm, loc, (0, 0, yaw)); acc.add(bm, "T_IK_Meat", grp)


def fish_body(acc, loc, L=.36, yaw=0, grp="Body", col="T_IK_FishScale"):
    x, y, z = loc
    X = Xf(acc, (x, y, z), (0, 0, yaw))
    bm = blob_bm((L * .42, L * .15, L * .07), 2, .02, 1); uv_box(bm, 6); place(bm, (0, 0, L * .06)); X.add(bm, col, grp)
    bm = bmesh.new()
    v = [bm.verts.new((L * .36, 0, L * .06)), bm.verts.new((L * .55, L * .14, L * .07)), bm.verts.new((L * .55, -L * .14, L * .07))]
    bm.faces.new(v); bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.006); uv_box(bm); X.add(bm, C("6F8FA6"), grp)
    blob(X, (.012, .012, .008), (-L * .3, L * .06, L * .11), C(INK), 1, 0, 0, grp=grp)


def ice_bed(acc, w, d, loc):
    x, y, z = loc
    blob(acc, (w / 2, d / 2, .04), (x, y, z), C("EEF8FC"), 2, .15, 4)


def sector_goods(acc, sid, x0, x1, y, z, depth=.3, rows=2, grp=None):
    """The sector's own goods on a display surface from x0 to x1 (centre line y, top z)."""
    rnd = random.Random(len(sid) + int(z * 10))
    x = x0 + .08
    k = 0
    while x < x1 - .08:
        g = grp or fills_for(x - (x0 + x1) / 2, x1 - x0)
        if sid == "padaria":
            for r_ in range(rows):
                if k % 3 == 0:
                    loaf(acc, (x + .05, y - depth / 3 + r_ * depth / 2, z), g, 90)
                elif k % 3 == 1:
                    croissant(acc, (x + .05, y - depth / 3 + r_ * depth / 2, z), 1.0, 20 * r_, g)
                else:
                    cake(acc, (x + .05, y - depth / 4 + r_ * depth / 2, z), .08, .07, ["F4A6C1", "7A4A2E", "F2C23F"][r_ % 3], g)
            x += .2
        elif sid == "acougue":
            for r_ in range(rows):
                steak(acc, (x + .06, y - depth / 3 + r_ * depth / 2, z + .012), 1.0, rnd.uniform(-20, 20), g)
            x += .17
        elif sid == "queijaria":
            if k % 2 == 0:
                cheese_wheel(acc, (x + .09, y, z), .09, .08, g)
                x += .21
            else:
                for r_ in range(rows):
                    salami(acc, (x + .05, y - depth / 3 + r_ * depth / 2, z), .18, .022, 90, g)
                x += .12
        elif sid == "peixaria":
            fish_body(acc, (x + .2, y - depth / 4, z + .03), .34, rnd.uniform(-15, 15), g, ["T_IK_FishScale", C("D74A3C"), C("8FA3AE")][k % 3])
            if rows > 1:
                fish_body(acc, (x + .2, y + depth / 4, z + .03), .3, 180 + rnd.uniform(-15, 15), g, ["T_IK_FishScale", C("8FA3AE"), C("D74A3C")][k % 3])
            fruit(acc, "lemon", (x + .38, y, z + .04), g, k)
            x += .42
        elif sid == "sorvetes":
            rbox(acc, (.24, .2, .06), (x + .12, y, z + .03), BRUSHED, .01, 1, grp=g)
            bm = blob_bm((.11, .09, .06), 2, .15, k)
            uvl = bm.loops.layers.uv.get("UVMap")
            for f in bm.faces:
                for l in f.loops:
                    l[uvl].uv = rk_core.cell_uv("gelato_%d" % (k % 8), (l.vert.co.x / .22 + .5) % 1, (l.vert.co.y / .18 + .5) % 1)
            place(bm, (x + .12, y, z + .07)); acc.add(bm, LAB, g)
            x += .27
        elif sid == "adega":
            for r_ in range(2):
                wine_bottle(acc, (x + .04, y - .06 + r_ * .12, z), .31, .037, C(["2A3B22", "4A1C24", "E8E0B0"][k % 3]), "wine_%d" % (k % 4), C(["7A1E2E", "D3A53D", "1D2B4F"][k % 3]), g, 8)
            x += .1
        elif sid == "sucos":
            lathe(acc, [(0, 0), (.05, 0), (.06, .14), (0, .14)], (x + .06, y, z), GLASS, 10, 0, cap_top=False)
            lathe(acc, [(0, .005), (.048, .005), (.057, .12), (0, .12)], (x + .06, y, z), C(["F28C28", "E25555", "6DB84A", "F2C23F"][k % 4]), 10, 0)
            tube(acc, [(x + .07, y, z + .1), (x + .08, y, z + .2)], .004, C(["E8505B", "3E8FD6"][k % 2]), 4)
            x += .14
        k += 1


def sector_back(acc, sid, tier, W, y, H=2.2):
    """Back wall unit of the sector (staff side): tiled/wood/marble wall, shelves and the sector's equipment."""
    wall = {1: PLANKS, 2: TILE, 3: MARBLE}[tier]
    rbox(acc, (W, .12, H), (0, y, H / 2), wall, .02, 2, uv=1.5)
    rbox(acc, (W, .5, .9), (0, y - .3, .45), WOOD if tier == 1 else C(NAVY), .02, 2)
    rbox(acc, (W + .02, .54, .04), (0, y - .3, .92), WOOD if tier == 1 else (BRUSHED if tier == 2 else MARBLE), .01, 2)
    for z in (1.35, 1.75):
        rbox(acc, (W - .2, .3, .03), (0, y - .2, z), WOOD if tier < 3 else C(NAVY), .008, 1)
    shelf_y = y - .2
    if sid == "padaria":
        # deck oven: steel box, glowing window, chrome handles
        for k in range(min(tier, 2)):
            ox = -W / 2 + .7 + k * 1.1
            rbox(acc, (.95, .55, .9), (ox, y - .33, 1.0 + .45), BRUSHED if tier > 1 else C(INK), .03, 2)
            rbox(acc, (.75, .01, .25), (ox, y - .61, 1.5), "E_F2A23A", .01, 1)
            rbox(acc, (.7, .03, .03), (ox, y - .63, 1.68), C(CHROME), .01, 1)
        for z in (1.35, 1.75):
            for i in range(int((W - 2.4) / .16)):
                roll(acc, (W / 2 - .3 - i * .16, shelf_y, z + .02), .045, "Body", i)
    elif sid == "acougue":
        rbox(acc, (.9, .5, .1), (-W / 2 + .7, y - .3, .97), "T_IK_ButcherBlock", .02, 2)
        tube(acc, [(-W / 2 + .3, y - .25, 2.0), (W / 2 - .3, y - .25, 2.0)], .015, C(CHROME), 8)
        for i in range(int((W - .8) / .3) if tier > 1 else 3):
            hx = -W / 2 + .5 + i * .3
            tube(acc, [(hx, y - .25, 2.0), (hx, y - .25, 1.9)], .004, C(CHROME), 4)
            lathe(acc, [(0, 0), (.04, .03), (.05, .2), (.03, .3), (0, .32)], (hx, y - .25, 1.58), C("8E2F2A"), 8, 0)
        if tier > 1:  # meat slicer blade
            lathe(acc, [(0, 0), (.13, 0), (.13, .02), (0, .02)], (W / 2 - .7, y - .3, 1.1), C(CHROME), 16, 0, rot=(90, 0, 0))
            rbox(acc, (.35, .3, .14), (W / 2 - .7, y - .3, .99), C(CHROME), .03, 2)
    elif sid == "queijaria":
        for z in (1.35, 1.75):
            for i in range(int((W - .4) / .26)):
                cheese_wheel(acc, (-W / 2 + .3 + i * .26, shelf_y, z + .015), .1, .09)
        rbox(acc, (.4, .35, .3), (W / 2 - .5, y - .3, 1.09), C(CHROME), .04, 2)
        lathe(acc, [(0, 0), (.13, 0), (.13, .015), (0, .015)], (W / 2 - .5, y - .48, 1.12), C(CHROME), 16, 0, rot=(90, 0, 0))
    elif sid == "peixaria":
        rbox(acc, (.7, .45, .25), (-W / 2 + .6, y - .3, 1.05), BRUSHED, .02, 2)
        lathe(acc, [(0, -.0), (.2, .0), (.2, -.12), (0, -.13)], (-W / 2 + .6, y - .3, 1.18), BRUSHED, 16, 0)
        tube(acc, [(-W / 2 + .9, y - .2, 1.0), (-W / 2 + .9, y - .2, 1.35), (-W / 2 + .75, y - .3, 1.35)], .012, C(CHROME), 8)
        rbox(acc, (W - .6, .02, .5), (0, y - .07, 1.6), C("2F6F8F"), .01, 1)
    elif sid == "sorvetes":
        rbox(acc, (.45, .45, .6), (-W / 2 + .5, y - .3, 1.24), C(CREAM), .06, 3)
        tube(acc, [(-W / 2 + .5, y - .5, 1.3), (-W / 2 + .5, y - .6, 1.2)], .03, C(CHROME), 8)
        for z in (1.35, 1.75):
            for i in range(int((W - 1.2) / .12)):
                lathe(acc, [(0, 0), (.045, 0), (.05, .15), (0, .16)], (W / 2 - .3 - i * .12, shelf_y, z + .015), GLASS, 8, 0)
                blob(acc, (.035, .035, .05), (W / 2 - .3 - i * .12, shelf_y, z + .07), C(["F4A6C1", "7A4A2E", "F2C23F", "6DB84A", "E8505B"][i % 5]), 1, .2, i)
    elif sid == "adega":
        # diamond wine rack wall and a barrel
        for i in range(int(W / .5)):
            bx = -W / 2 + .25 + i * .5
            fr = frame_bm(.46, 1.1, .3, .02, .03)
            place(fr, (bx, y - .2, 1.55)); acc.add(fr, WOOD_D)
            for r_ in range(4):
                for c_ in range(3):
                    lathe(acc, [(0, 0), (.035, 0), (.035, .02), (0, .02)], (bx - .12 + c_ * .12, y - .35, 1.12 + r_ * .26), C(["2A3B22", "4A1C24"][(r_ + c_) % 2]), 8, 0, rot=(90, 0, 0))
        if tier > 1:  # oak barrel
            lathe(acc, [(.0, 0), (.28, 0), (.32, .3), (.28, .6), (0, .6)], (W / 2 - .45, y - .75, .0), "T_IK_Staves", 14, 1)
    elif sid == "sucos":
        for k in range(1 + tier):
            dx = -W / 2 + .5 + k * .55
            rbox(acc, (.4, .3, .12), (dx, y - .3, .98), BRUSHED, .02, 2)
            lathe(acc, [(0, 0), (.14, 0), (.15, .35), (0, .35)], (dx, y - .3, 1.04), GLASS, 12, 0, cap_top=False)
            lathe(acc, [(0, .01), (.135, .01), (.145, .3), (0, .3)], (dx, y - .3, 1.04), C(["F28C28", "E25555", "6DB84A", "F2C23F"][k % 4]), 12, 0)
            rbox(acc, (.3, .3, .06), (dx, y - .3, 1.42), BRUSHED, .02, 2)
        for i in range(5):
            fruit(acc, ["orange", "lemon", "lime", "apple", "orange"][i], (W / 2 - .3 - i * .1, y - .35, .98), "Body", i)
    # a blank plaque on the wall (the game writes the sector's name / pictogram)
    plate(acc, min(1.4, W * .45), .3, (0, y - .065, H - .2), C(NAVY) if tier < 3 else C(INK), .03, .1)
    plate(acc, min(1.2, W * .38), .2, (0, y - .085, H - .2), C(CREAM) if tier < 3 else LED, .012, .08)


def sector_front(acc, sid, tier, W, y, D=.85, glass=True):
    """Customer counter of the sector: wood (T1), navy with a curved vitrine (T2), rounded ripado + inox + LED (T3)."""
    cw = W - .3 if sid != "sucos" else W
    if tier == 1:
        rbox(acc, (cw, D, .88), (0, y, .44), PLANKS, .02, 2, uv=1.3)
        rbox(acc, (cw + .04, D + .04, .05), (0, y, .9), WOOD, .015, 2)
        rbox(acc, (cw - .1, .01, .012), (0, y - D / 2 - .004, .8), C(NAVY), .004, 1)
        for i in range(int(cw / .5)):
            rbox(acc, (.36, .26, .02), (-cw / 2 + .3 + i * .5, y - .1, .93), "T_IK_Wicker" if sid in ("padaria", "sucos") else BRUSHED, .01, 1)
        sector_goods(acc, sid, -cw / 2 + .1, cw / 2 - .1, y - .1, .95, .26, 1)
    elif tier == 2:
        rbox(acc, (cw, D, .85), (0, y, .425), C(NAVY), .03, 3)
        n = max(2, int(cw / .9))
        for k in range(n):
            px_ = -cw / 2 + cw / n * (k + .5)
            fr = frame_bm(cw / n - .14, .52, .02, .04, .04); place(fr, (px_, y - D / 2 - .004, .43)); acc.add(fr, WOOD)
        rbox(acc, (cw + .02, .01, .012), (0, y - D / 2 - .006, .78), C(GOLD), .003, 1)
        rbox(acc, (cw + .04, D + .04, .04), (0, y, .86), BRUSHED, .01, 2)
        if glass:
            bm = bmesh.new()
            prof = [(0, 0), (.06, .1), (.12, .22), (.14, .34), (.12, .42)]
            for i in range(len(prof) - 1):
                a, b = prof[i], prof[i + 1]
                v = [bm.verts.new((-cw / 2 + .04, -a[0], a[1])), bm.verts.new((cw / 2 - .04, -a[0], a[1])), bm.verts.new((cw / 2 - .04, -b[0], b[1])), bm.verts.new((-cw / 2 + .04, -b[0], b[1]))]
                bm.faces.new(v)
            uv_box(bm); place(bm, (0, y - D / 2 + .22, .88)); acc.add(bm, GLASS)
            rbox(acc, (cw - .04, .4, .012), (0, y + .02, 1.3), GLASS, .004, 1)
            rbox(acc, (cw - .1, .02, .01), (0, y + .2, 1.28), ICE if sid not in ("padaria",) else LED, .004, 1)
            for s in (-1, 1):
                rbox(acc, (.03, D - .1, .44), (s * (cw / 2 - .015), y, 1.08), C(NAVY), .015, 2)
        if sid == "peixaria":
            ice_bed(acc, cw - .2, .4, (0, y - .05, .9))
        sector_goods(acc, sid, -cw / 2 + .1, cw / 2 - .1, y - .05, .92 if sid != "peixaria" else .94, .4, 2)
    else:
        body, _ = panel_bm(cw, D, .82, .3, 8)
        bmesh.ops.rotate(body, verts=body.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
        uv_box(body); place(body, (0, y, .45)); acc.add(body, C(NAVY))
        flat = cw - .62
        n = int(flat / .07)
        for k in range(n):
            rbox(acc, (.034, .02, .52), (-flat / 2 + .02 + k * (flat - .04) / (n - 1), y - D / 2 - .006, .45), WOOD_L, .006, 1, uv=2)
        for z in (.18, .72):
            rbox(acc, (flat + .02, .012, .01), (0, y - D / 2 - .01, z), C(GOLD), .003, 1)
        rbox(acc, (cw - .4, .02, .02), (0, y - D / 2 + .05, .03), LED, .006, 1)
        tb, _ = panel_bm(cw + .04, D + .04, .04, .32, 8)
        bmesh.ops.rotate(tb, verts=tb.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
        uv_box(tb, 2); place(tb, (0, y, .88)); acc.add(tb, MARBLE)
        if glass:
            bm = bmesh.new()
            prof = [(0, 0), (.08, .12), (.13, .26), (.15, .4), (.13, .48)]
            for i in range(len(prof) - 1):
                a, b = prof[i], prof[i + 1]
                v = [bm.verts.new((-cw / 2 + .3, -a[0], a[1])), bm.verts.new((cw / 2 - .3, -a[0], a[1])), bm.verts.new((cw / 2 - .3, -b[0], b[1])), bm.verts.new((-cw / 2 + .3, -b[0], b[1]))]
                bm.faces.new(v)
            uv_box(bm); place(bm, (0, y - D / 2 + .24, .9)); acc.add(bm, GLASS)
            rbox(acc, (cw - .6, .42, .012), (0, y + .03, 1.38), GLASS, .004, 1)
            rbox(acc, (cw - .64, .03, .015), (0, y + .2, 1.36), LED, .005, 1)
            for s in (-1, 1):
                rbox(acc, (.03, D - .2, .5), (s * (cw / 2 - .3), y, 1.14), BRUSHED, .015, 2)
        if sid == "peixaria":
            ice_bed(acc, cw - .7, .42, (0, y - .04, .92))
        sector_goods(acc, sid, -cw / 2 + .32, cw / 2 - .32, y - .04, .92 if sid != "peixaria" else .95, .42, 2)


def sector_canopy(acc, tier, W, D, H):
    """Header over the sector: T1 a small blank board on posts, T2 a navy fascia with a gold line, T3 a suspended
    frame with pendant lamps and a lit blank sign."""
    if tier == 1:
        return
    if tier == 2:
        rbox(acc, (W, .1, .3), (0, -D / 2 + .5, H - .15), C(NAVY), .03, 3)
        rbox(acc, (W - .1, .01, .012), (0, -D / 2 + .444, H - .25), C(GOLD), .003, 1)
        for s in (-1, 1):
            tube(acc, [(s * (W / 2 - .05), -D / 2 + .5, H - .3), (s * (W / 2 - .05), -D / 2 + .5, 0)], .03, C(NAVY), 10)
        return
    fw, fd = W - .1, D - .6
    for sy in (-1, 1):
        rbox(acc, (fw, .09, .09), (0, .1 + sy * (fd / 2 - .045), H), C(NAVY), .03, 3)
        rbox(acc, (fw - .2, .02, .012), (0, .1 + sy * (fd / 2 - .095), H - .04), LED, .005, 1)
    for sx in (-1, 1):
        rbox(acc, (.09, fd, .09), (sx * (fw / 2 - .045), .1, H), C(NAVY), .03, 3)
    rbox(acc, (fw, .01, .012), (0, .1 - fd / 2 - .006, H - .02), C(GOLD), .003, 1)
    plate(acc, 1.1, .26, (0, .1 - fd / 2 - .01, H + .2), C(NAVY), .03, .11)
    plate(acc, .9, .17, (0, .1 - fd / 2 - .03, H + .2), LED, .012, .07)
    for k in range(4):
        x = -W / 2 + .5 + k * (W - 1.0) / 3
        tube(acc, [(x, -D / 2 + .55, H), (x, -D / 2 + .55, H - .5)], .004, C(INK), 4)
        lathe(acc, [(0, 0), (.04, 0), (.13, -.12), (.14, -.14), (0, -.12)], (x, -D / 2 + .55, H - .5), C(NAVY), 14, 0)
        lathe(acc, [(.13, -.13), (0, -.125)], (x, -D / 2 + .55, H - .5), LED, 14, 0, cap_top=False)
        lathe(acc, [(.13, -.12), (.142, -.12), (.142, -.13), (.13, -.13)], (x, -D / 2 + .55, H - .5), C(GOLD), 14, 0, cap_top=False, cap_bottom=False)
    for s in (-1, 1):
        tube(acc, [(s * (W / 2 - .1), .1, H), (s * (W / 2 - .1), .1, H + .5)], .01, C(INK), 6)


def make_sector(sid):
    _, W, D = SECTORS[sid]
    fns = []
    for tier in (1, 2, 3):
        def build(acc, tier=tier):
            H = 2.2 if tier == 1 else 2.4
            front_d = .85 if sid != "sucos" else .75
            front_y = -D / 2 + front_d / 2 + (.15 if sid != "sucos" else .05)
            if sid == "sucos":
                # a single wall-side juice bar: equipment on the counter's back, no separate back wall
                sector_front(acc, sid, tier, W, front_y, front_d, glass=False)
                sector_back(acc, sid, tier, W, D / 2 - .06, 2.0 + .2 * tier)
            else:
                sector_front(acc, sid, tier, W, front_y, front_d)
                sector_back(acc, sid, tier, W, D / 2 - .06, H)
            sector_canopy(acc, tier, W, D, H + .3)
            if tier == 1 and sid != "sucos":
                for s in (-1, 1):
                    tube(acc, [(s * (W / 2 - .2), front_y, .9), (s * (W / 2 - .2), front_y, 1.7)], .02, WOOD, 6)
                plate(acc, 1.0, .26, (0, front_y, 1.82), PAINT_NAVY, .03, .1)
                plate(acc, .8, .17, (0, front_y - .02, 1.82), C(CREAM), .012, .07)
        fns.append(build)
    return fns


for _sid in SECTORS:
    BUILDERS["sector-" + _sid] = make_sector(_sid)


# ---------------------------------------------------------------- ATM
def atm_unit(acc, x, y, glow=True, surround=True):
    """One cash machine facing -Y: navy body, lit screen (blank), keypad, card and cash slots, gold trim."""
    rbox(acc, (.62, .62, 1.55), (x, y, .775), C(NAVY), .05, 3)
    rbox(acc, (.56, .2, .5), (x, y - .33, 1.12), C(INK), .04, 3, rot=(12, 0, 0))
    rbox(acc, (.36, .01, .26), (x, y - .445, 1.21), LED_COOL, .01, 1, rot=(12, 0, 0))
    for i in range(3):
        for j in range(4):
            rbox(acc, (.04, .012, .03), (x - .05 + i * .05, y - .37, .93 + j * .04), C(CREAM if j else "C0392B"), .005, 1, rot=(30, 0, 0))
    rbox(acc, (.12, .02, .03), (x + .17, y - .34, .98), C(INK), .005, 1)
    rbox(acc, (.07, .006, .006), (x + .17, y - .351, .98), LED, 0, 1)
    rbox(acc, (.28, .03, .04), (x, y - .31, .78), C(CHROME), .01, 1)
    rbox(acc, (.62, .012, .012), (x, y - .316, 1.5), C(GOLD), .003, 1)
    lathe(acc, [(0, 0), (.07, 0), (.07, .012), (0, .012)], (x, y - .312, 1.62), C(CREAM), 16, 0, rot=(90, 0, 0))
    coin(acc, (x, y - .325, 1.62), C(GOLD), .045)


def atm_t1(acc):
    atm_unit(acc, 0, .05)
    rbox(acc, (.74, .8, .12), (0, .0, 1.62), C(NAVY), .04, 3)
    rbox(acc, (.7, .01, .015), (0, -.405, 1.6), LED, .005, 1)


def atm_t2(acc):
    rbox(acc, (1.48, .7, .08), (0, .05, .04), C(INK), .02, 2)
    for x in (-.36, .36):
        atm_unit(acc, x, .08)
    rbox(acc, (1.5, .82, .28), (0, .0, 1.86), C(NAVY), .05, 3)
    rbox(acc, (1.44, .01, .015), (0, -.415, 1.73), LED, .005, 1)
    plate(acc, .7, .16, (0, -.42, 1.88), C(CREAM), .012, .07)
    rbox(acc, (1.5, .01, .012), (0, -.414, 1.98), C(GOLD), .003, 1)
    for s in (-1, 1):
        rbox(acc, (.06, .8, 1.72), (s * .72, .0, .86), C(NAVY), .03, 3)


def atm_t3(acc):
    """Mini agência: a back wall with three ATMs, glass side screens, a lit canopy, a small bench and a plant."""
    W, D = 2.0, 1.2
    rbox(acc, (W, .14, 2.4), (0, D / 2 - .07, 1.2), "T_IK_V2_PaintCream", .02, 2)
    for x in (-.66, 0, .66):
        atm_unit(acc, x, D / 2 - .45)
    for s in (-1, 1):
        rbox(acc, (.03, D - .1, 2.1), (s * (W / 2 - .02), 0, 1.05), GLASS, .01, 1)
        rbox(acc, (.05, D - .05, .06), (s * (W / 2 - .02), 0, 2.13), C(NAVY), .02, 2)
    rbox(acc, (W, D, .14), (0, 0, 2.37), C(NAVY), .05, 3)
    rbox(acc, (W - .1, .02, .015), (0, -D / 2 + .06, 2.29), LED, .005, 1)
    plate(acc, .9, .22, (0, -D / 2 - .005, 2.5), C(CREAM), .03, .1)
    rbox(acc, (W, .01, .012), (0, -D / 2 - .006, 2.32), C(GOLD), .003, 1)
    rbox(acc, (W - .1, D - .1, .02), (0, 0, .01), C(BLUE), .02, 1)


# ---------------------------------------------------------------- gumball machines
def gumball_globe(acc, x, y, z, r=.17, seed=0):
    rnd = random.Random(seed)
    cols = ["E8505B", "F2C23F", "5FB548", "3E8FD6", "F28C28", "E86A9E", "FBF8F1"]
    for i in range(int(18 * (r / .17) ** 2)):
        a, b = rnd.random() * 6.28, rnd.random() * .9
        rr = r * .75 * math.sqrt(rnd.random())
        blob(acc, (.022, .022, .022), (x + rr * math.cos(a), y + rr * math.sin(a), z - r * .55 + b * r * .9), C(cols[i % 7]), 1, 0, i)
    lathe(acc, [(0, -r), (r * .7, -r * .7), (r, 0), (r * .7, r * .7), (0, r)], (x, y, z), GLASS, 18, 2)
    lathe(acc, [(r * .3, r * .85), (r * .35, r * 1.05), (0, r * 1.12)], (x, y, z), C(NAVY), 14, 1, cap_bottom=False)
    lathe(acc, [(r * .32, r * .88), (r * .34, r * .9)], (x, y, z), C(GOLD), 14, 0, cap_top=False, cap_bottom=False)


def gumball_head(acc, x, y, z):
    rbox(acc, (.2, .18, .2), (x, y, z), C(NAVY), .04, 3)
    lathe(acc, [(0, 0), (.04, 0), (.04, .02), (0, .02)], (x, y - .09, z + .03), C(CHROME), 12, 0, rot=(90, 0, 0))
    rbox(acc, (.05, .03, .05), (x, y - .1, z - .06), C(CHROME), .01, 1)
    rbox(acc, (.2, .006, .01), (x, y - .092, z + .085), C(GOLD), .003, 1)


def gumball_t1(acc):
    lathe(acc, [(0, 0), (.2, 0), (.2, .04), (.05, .06), (.04, .7), (0, .7)], (0, 0, 0), C(NAVY), 16, 1)
    gumball_head(acc, 0, 0, .8)
    gumball_globe(acc, 0, 0, 1.07, .17, 1)


def gumball_t2(acc):
    rbox(acc, (.9, .4, .05), (0, 0, .025), C(NAVY), .02, 2)
    for x in (-.25, .25):
        tube(acc, [(x, 0, .05), (x, 0, .7)], .04, C(NAVY), 10)
        gumball_head(acc, x, 0, .8)
        gumball_globe(acc, x, 0, 1.08, .18, int(x * 10) + 5)
    tube(acc, [(-.25, 0, .4), (.25, 0, .4)], .015, C(GOLD), 6)


def gumball_t3(acc):
    """Torre de chicletes: a big globe over a tall navy column with a spiral chute (balls roll down it), gold rings."""
    lathe(acc, [(0, 0), (.45, 0), (.45, .06), (.3, .1), (.22, .14), (0, .14)], (0, 0, 0), C(NAVY), 20, 1)
    lathe(acc, [(.2, .14), (.16, .4), (.16, 1.25), (.22, 1.3), (0, 1.32)], (0, 0, 0), C(NAVY), 16, 1, cap_bottom=False)
    for z in (.4, 1.25):
        lathe(acc, [(.165, z), (.175, z), (.175, z + .02), (.165, z + .02)], (0, 0, 0), C(GOLD), 16, 0, cap_top=False, cap_bottom=False)
    pts = [(.3 * math.cos(t * .5), .3 * math.sin(t * .5), 1.3 - t * .07) for t in range(16)]
    tube(acc, pts, .035, GLASS, 10, 0)
    for i in range(0, 16, 2):
        blob(acc, (.022, .022, .022), pts[i], C(["E8505B", "F2C23F", "5FB548", "3E8FD6"][i % 4]), 1, 0, i)
    gumball_head(acc, 0, -.12, .32)
    gumball_globe(acc, 0, 0, 1.62, .32, 9)


# ---------------------------------------------------------------- claw machines
def plush(acc, loc, s=1.0, col="F4A6C1", seed=0):
    x, y, z = loc
    blob(acc, (.07 * s, .06 * s, .07 * s), (x, y, z + .06 * s), C(col), 2, .05, seed)
    blob(acc, (.055 * s, .05 * s, .05 * s), (x, y - .01, z + .16 * s), C(col), 2, .03, seed + 1)
    for e in (-1, 1):
        blob(acc, (.02 * s, .015 * s, .025 * s), (x + e * .04 * s, y, z + .21 * s), C(col), 1, 0, seed + 2)
        blob(acc, (.008 * s, .006, .008 * s), (x + e * .018 * s, y - .055 * s, z + .17 * s), C(INK), 1, 0, 0)


def art_panel(acc, w, h, loc, key, t=.012, r=.03):
    """Rounded panel showing a whole texture (0..1) on its front, like a printed decal."""
    bm, _ = panel_bm(w, h, t, r, 5)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = ((l.vert.co.x + w / 2) / w, (l.vert.co.z + h / 2) / h)
    place(bm, loc)
    acc.add(bm, key, smooth=False)


def claw_cabinet(acc, x, W=.72, D=.72, H=1.9, seed=0, big=False):
    rnd = random.Random(seed)
    rbox(acc, (W, D, .8), (x, 0, .4), C(NAVY), .04, 3)
    art_panel(acc, min(.5, W - .2), min(.5, W - .2) * .9, (x, -D / 2 - .006, .42), "T_IK_V3_ClawArt")
    rbox(acc, (W, .01, .012), (x, -D / 2 - .005, .78), C(GOLD), .003, 1)
    # control panel
    rbox(acc, (W - .04, .2, .1), (x, -D / 2 + .05, .85), C(INK), .02, 2, rot=(-15, 0, 0))
    lathe(acc, [(0, 0), (.012, 0), (.012, .08), (.03, .1), (0, .13)], (x - .12, -D / 2 + .02, .88), C("E8505B"), 10, 1)
    lathe(acc, [(0, 0), (.035, 0), (.035, .02), (0, .025)], (x + .12, -D / 2 + .02, .88), C("F2C23F"), 12, 0)
    # glass box, corner posts
    for sx in (-1, 1):
        for sy in (-1, 1):
            rbox(acc, (.04, .04, H - .95), (x + sx * (W / 2 - .02), sy * (D / 2 - .02), .8 + (H - .95) / 2), C(NAVY), .015, 2)
    for sx in (-1, 1):
        rbox(acc, (.01, D - .06, H - 1.0), (x + sx * (W / 2 - .03), 0, .8 + (H - 1.0) / 2), GLASS, .004, 1)
    rbox(acc, (W - .06, .01, H - 1.0), (x, -D / 2 + .03, .8 + (H - 1.0) / 2), GLASS, .004, 1)
    rbox(acc, (W - .06, .01, H - 1.0), (x, D / 2 - .03, .8 + (H - 1.0) / 2), "T_IK_V2_PaintCream", .004, 1)
    rbox(acc, (W, D, .2), (x, 0, H - .1), C(NAVY), .05, 3)
    rbox(acc, (W - .1, .01, .1), (x, -D / 2 - .002, H - .1), LED, .02, 1)
    rbox(acc, (W - .04, .012, .012), (x, -D / 2 - .006, H - .2), C(GOLD), .003, 1)
    # prize pile and the claw
    cols = ["F4A6C1", "F2C23F", "7DB3E8", "B9E8D2", "E8A06A", "C9A0E8"]
    for i in range(10 if not big else 22):
        plush(acc, (x + rnd.uniform(-W / 2 + .12, W / 2 - .12), rnd.uniform(-D / 2 + .12, D / 2 - .12), .8 + rnd.uniform(0, .12)), rnd.uniform(.8, 1.1) * (1.4 if big else 1), cols[i % 6], i + seed)
    cx, cy = x + rnd.uniform(-.1, .1), rnd.uniform(-.1, .1)
    tube(acc, [(cx, cy, H - .2), (cx, cy, H - .45)], .006, C(CHROME), 5)
    lathe(acc, [(0, 0), (.04, 0), (.04, .05), (0, .06)], (cx, cy, H - .5), C(CHROME), 10, 0)
    for k in range(3):
        a = k * 2.09
        tube(acc, [(cx + .03 * math.cos(a), cy + .03 * math.sin(a), H - .5), (cx + .07 * math.cos(a), cy + .07 * math.sin(a), H - .58), (cx + .045 * math.cos(a), cy + .045 * math.sin(a), H - .65)], .006, C(CHROME), 5)


def claw_t1(acc):
    claw_cabinet(acc, 0, .72, .72, 1.9, 1)


def claw_t2(acc):
    for i, x in enumerate((-.37, .37)):
        claw_cabinet(acc, x, .72, .8, 1.95, 3 + i)
    rbox(acc, (1.5, .84, .1), (0, 0, 2.0), C(NAVY), .04, 3)
    plate(acc, .6, .14, (0, -.43, 2.0), C(CREAM), .012, .06)


def claw_t3(acc):
    claw_cabinet(acc, 0, 1.44, 1.44, 2.3, 7, big=True)
    for s in (-1, 1):
        rbox(acc, (.02, 1.4, .02), (s * .73, 0, 2.18), LED, .006, 1)
    plate(acc, .9, .2, (0, -.73, 2.38), C(CREAM), .02, .09)


# ---------------------------------------------------------------- carts and baskets
def hand_basket(acc, loc, yaw=0, col=NAVY):
    x, y, z = loc
    X = Xf(acc, (x, y, z), (0, 0, yaw))
    open_box(X, .42, .3, .2, (0, 0, 0), C(col), .012, .008)
    tube(X, [(-.12, 0, .2), (-.1, 0, .32), (.1, 0, .32), (.12, 0, .2)], .01, C(GOLD if col != NAVY else CREAM), 6, 2)


def cart(acc, loc, yaw=0, s=1.0, col=NAVY):
    """Shopping cart: chrome wire basket (bars), navy plastic handle and corners, four castors."""
    x, y, z = loc
    X = Xf(acc, (x, y, z), (0, 0, yaw))
    L, W, Hh = .8 * s, .5 * s, .45 * s
    z0 = .35 * s
    # basket bars
    for i in range(7):
        t = i / 6
        xx = -L / 2 + t * L
        tube(X, [(xx, -W / 2, z0), (xx, -W / 2, z0 + Hh)], .005, C(CHROME), 4)
        tube(X, [(xx, W / 2, z0), (xx, W / 2, z0 + Hh)], .005, C(CHROME), 4)
    for zz in (z0, z0 + Hh * .5, z0 + Hh):
        tube(X, [(-L / 2, -W / 2, zz), (L / 2, -W / 2, zz), (L / 2, W / 2, zz), (-L / 2, W / 2, zz), (-L / 2, -W / 2, zz)], .006, C(CHROME), 4)
    for j in range(5):
        yy = -W / 2 + j * W / 4
        tube(X, [(-L / 2, yy, z0), (L / 2, yy, z0)], .005, C(CHROME), 4)
        tube(X, [(L / 2, yy, z0), (L / 2, yy, z0 + Hh)], .005, C(CHROME), 4)
    # chassis and castors
    for sy in (-1, 1):
        tube(X, [(-L / 2 - .05, sy * W * .4, z0 + Hh + .05), (-L / 2, sy * W * .4, z0), (-L / 2 + .05, sy * W * .35, .08), (L / 2 - .05, sy * W * .35, .08)], .012, C(CHROME), 6)
        for xx in (-L / 2 + .07, L / 2 - .07):
            lathe(X, [(0, 0), (.04 * s, 0), (.04 * s, .03), (0, .03)], (xx, sy * W * .35, .04 * s), C(INK), 10, 0, rot=(90, 0, 0))
    rbox(X, (.05, W * .95, .04), (-L / 2 - .06, 0, z0 + Hh + .07), C(col), .018, 2)
    for sy in (-1, 1):
        rbox(X, (.06, .04, .1), (L / 2, sy * W / 2, z0 + Hh - .04), C(col), .015, 2)


def carts_t1(acc):
    """Cestinhas: a navy stand with a stack of hand baskets and a second short stack beside it."""
    rbox(acc, (.62, .44, .06), (-.03, 0, .03), C(NAVY), .02, 2)
    for k in range(5):
        hand_basket(acc, (-.12, 0, .06 + k * .07), 0)
    for k in range(3):
        hand_basket(acc, (.17, .0, .06 + k * .07), 90, "2E4A7D")
    tube(acc, [(-.33, .2, .06), (-.33, .2, .9)], .015, C(CHROME), 6)
    plate(acc, .2, .14, (-.33, .19, .88), C(CREAM), .012, .05, (0, 0, 0))


def carts_t2(acc):
    """Carrinhos: a corral of chrome rails with four nested carts and a navy end post with a blank plaque."""
    for s in (-1, 1):
        tube(acc, [(-.72, s * .32, .02), (-.72, s * .32, .9), (.72, s * .32, .9), (.72, s * .32, .02)], .02, C(CHROME), 8)
        tube(acc, [(-.72, s * .32, .5), (.72, s * .32, .5)], .015, C(CHROME), 6)
    for k in range(4):
        cart(acc, (.3 - k * .16, 0, 0), 180, .82)
    rbox(acc, (.1, .7, 1.05), (.76, 0, .525), C(NAVY), .03, 3)
    plate(acc, .5, .3, (.82, 0, .8), C(CREAM), .012, .05, (0, 0, 90))
    rbox(acc, (.012, .72, .012), (.815, 0, .62), C(GOLD), .003, 1)


def carts_t3(acc):
    """Carrinhos grandes: a covered corral (navy roof on posts, LED edge), big carts and two kids' carts, a basket stand."""
    W, D = 1.96, .96
    for s in (-1, 1):
        tube(acc, [(-W / 2 + .05, s * .4, .02), (-W / 2 + .05, s * .4, .9), (W / 2 - .25, s * .4, .9), (W / 2 - .25, s * .4, .02)], .02, C(CHROME), 8)
    for k in range(4):
        cart(acc, (.35 - k * .2, -.1, 0), 180, 1.0)
    for k in range(2):
        cart(acc, (-.55 + k * .14, .26, 0), 180, .6, "D74A3C")
    for x in (-W / 2 + .05, W / 2 - .05):
        for y in (-D / 2 + .05, D / 2 - .05):
            tube(acc, [(x, y, 0), (x, y, 2.0)], .025, C(NAVY), 10)
    for sy in (-1, 1):
        rbox(acc, (W + .1, .08, .1), (0, sy * (D / 2 + .01), 2.05), C(NAVY), .03, 3)
    for sx in (-1, 0, 1):
        rbox(acc, (.06, D + .1, .08), (sx * (W / 2 + .02), 0, 2.05), C(NAVY), .02, 2)
    rbox(acc, (W + .06, D + .06, .012), (0, 0, 2.1), GLASS, .004, 1)
    rbox(acc, (W + .1, .01, .012), (0, -D / 2 - .056, 2.05), C(GOLD), .003, 1)
    rbox(acc, (W - .1, .02, .015), (0, -D / 2 + .02, 1.99), LED, .005, 1)
    plate(acc, .8, .2, (0, -D / 2 - .06, 2.22), C(CREAM), .02, .09)
    for k in range(3):
        hand_basket(acc, (W / 2 - .2, .2, .0 + k * .07), 90)


BUILDERS.update({
    "atm": [atm_t1, atm_t2, atm_t3],
    "gumball": [gumball_t1, gumball_t2, gumball_t3],
    "claw": [claw_t1, claw_t2, claw_t3],
    "carts": [carts_t1, carts_t2, carts_t3],
})


# ================================================================================================ ROUND 2 (Lucas 30/10): sectors v2
# Every sector keeps its own identity from today's game (Decor/sector-*.png): padaria = brick and a dome oven,
# açougue = white tile, steel rail with hanging cuts, butcher block, queijaria = plaster cellar with wheel racks and
# hanging cheeses, peixaria = blue-and-white tile, inclined ice bed, crates, sorveteria = parlour with a gelato case and
# cones, adega = dark wood wine wall, barrels, tasting counter, sucos = fruit display and dispensers. The tiers grow
# the same sector: T1 2.5 x 2.0 m, T2 3.25 x 2.5 m, T3 4.0 x 3.25 m (today's counters are 3.96 x 3.36).
SECTOR_SIZES = [(2.5, 2.0, 2.4), (3.25, 2.5, 2.7), (4.0, 3.25, 3.0)]
SECTOR_NAMES = {"padaria": "Padaria", "acougue": "Açougue", "queijaria": "Queijaria", "peixaria": "Peixaria",
                "sorvetes": "Sorveteria", "adega": "Adega", "sucos": "Sucos"}
SECTOR_TIER_NAMES = {
    "padaria": ("forno a lenha", "padaria de bairro", "padaria artesanal"),
    "acougue": ("balcão do açougueiro", "açougue completo", "açougue com câmara de maturação"),
    "queijaria": ("banca de queijos", "queijaria", "cave de queijos"),
    "peixaria": ("bancada de gelo", "peixaria", "peixaria com aquário"),
    "sorvetes": ("carrinho de gelato", "sorveteria", "gelateria"),
    "adega": ("estante de vinhos", "adega", "cave de vinhos"),
    "sucos": ("barraca de sucos", "casa de sucos", "bar de sucos"),
}
for _sid in SECTOR_NAMES:
    TIERS["sector-" + _sid] = [("T%d" % (i + 1), "%s: %s" % (SECTOR_NAMES[_sid], SECTOR_TIER_NAMES[_sid][i]), w, d, h)
                               for i, (w, d, h) in enumerate(SECTOR_SIZES)]
BRICK, PLASTER, STONE, TILE_W, TILE_B, ROPE = "T_IK_Brick", "T_IK_Plaster", "T_IK_Stone", "T_IK_TileSquare", "T_IK_TileBlue", "T_IK_Rope"


def pendant(acc, x, y, ztop, zlamp, r=.13):
    tube(acc, [(x, y, ztop), (x, y, zlamp)], .005, C(INK), 4)
    lathe(acc, [(0, 0), (.03, 0), (r, -.11), (r + .01, -.13), (0, -.11)], (x, y, zlamp), C(NAVY), 14, 0)
    lathe(acc, [(r - .005, -.125), (0, -.12)], (x, y, zlamp), LED, 14, 0, cap_top=False)
    lathe(acc, [(r, -.12), (r + .013, -.12), (r + .013, -.132), (r, -.132)], (x, y, zlamp), C(GOLD), 14, 0, cap_top=False, cap_bottom=False)


def back_wall(acc, W, y, H, key, wains=None, wh=1.0, trim=True, uv=1.3):
    rbox(acc, (W, .12, H), (0, y, H / 2), key, .02, 2, uv=uv)
    if wains:
        rbox(acc, (W + .01, .13, wh), (0, y - .01, wh / 2), wains, .015, 2, uv=uv)
    if trim:
        rbox(acc, (W + .02, .05, .05), (0, y - .07, wh if wains else .1), C(NAVY), .015, 2)
        rbox(acc, (W + .02, .01, .012), (0, y - .1, (wh if wains else .1) + .03), C(GOLD), .003, 1)
        rbox(acc, (W + .04, .16, .08), (0, y - .02, H + .04), C(NAVY), .03, 3)


def name_board(acc, x, y, z, w=1.1, h=.3):
    """Blank arched board for the sector's name / pictogram (the game writes it, translated)."""
    plate(acc, w, h, (x, y, z), C(NAVY), .05, h * .45)
    fr = frame_bm(w - .04, h - .04, .012, h * .4, .014)
    place(fr, (x, y - .028, z)); acc.add(fr, C(GOLD))
    plate(acc, w * .8, h * .62, (x, y - .03, z), C(CREAM), .01, h * .3)


def dome_oven(acc, x, y, r, z0=0):
    """Wood-fired dome oven: brick base, brick dome, glowing arched mouth with a gold rim, chimney."""
    rbox(acc, (r * 2.3, r * 2.0, .75), (x, y, z0 + .375), BRICK, .03, 2, uv=2)
    rbox(acc, (r * 2.4, r * 2.1, .05), (x, y, z0 + .77), STONE, .015, 2, uv=2)
    dome = lathe_bm([(0, 0), (r, 0), (r * 1.02, r * .25), (r * .9, r * .6), (r * .6, r * .88), (r * .2, r), (0, r * 1.01)], 18, 2)
    uv_box(dome, 2.2)
    place(dome, (x, y, z0 + .79)); acc.add(dome, BRICK)
    mw, mh = r * .9, r * .55
    plate(acc, mw + .1, mh + .1, (x, y - r * .92, z0 + .79 + mh / 2), STONE, .1, mh * .5)
    plate(acc, mw, mh, (x, y - r * .97, z0 + .79 + mh / 2), "E_FF8A2A", .02, mh * .48)
    fr = frame_bm(mw + .04, mh + .04, .02, mh * .48, .025)
    place(fr, (x, y - r * .99, z0 + .79 + mh / 2)); acc.add(fr, C(GOLD))
    rbox(acc, (.18, .18, .6), (x + r * .3, y + r * .3, z0 + .79 + r + .2), BRICK, .03, 2, uv=2)
    rbox(acc, (.22, .22, .05), (x + r * .3, y + r * .3, z0 + .79 + r + .52), C(INK), .015, 2)


def flour_sack(acc, loc, s=1.0, yaw=0):
    x, y, z = loc
    bm = blob_bm((.18 * s, .13 * s, .24 * s), 2, .05, int(x * 10) % 9)
    for v in bm.verts:
        if v.co.z > .1 * s:
            v.co.x *= .8; v.co.y *= .8
    uv_box(bm, 3); place(bm, (x, y, z + .2 * s), (0, 0, yaw)); acc.add(bm, "T_IK_R_Fabric")
    tube(acc, [(x - .07 * s, y, z + .38 * s), (x + .07 * s, y, z + .38 * s)], .012 * s, ROPE, 5)


def bread_wall(acc, x, y, w, h, z0=.9, rows=3):
    """Wooden bread wall (paneleira): slanted shelves full of loaves, baguettes upright in the top row."""
    rbox(acc, (w, .3, h), (x, y + .05, z0 + h / 2), WOOD_D, .02, 2)
    for r_ in range(rows):
        z = z0 + .1 + r_ * h / rows
        X = Xf(acc, (x, y - .08, z), (14, 0, 0))
        rbox(X, (w - .08, .26, .02), (0, 0, 0), WOOD, .006, 1)
        rbox(X, (w - .08, .02, .06), (0, -.13, .03), WOOD, .006, 1)
        n = int((w - .1) / .2)
        for i in range(n):
            if r_ == rows - 1:
                baguette(X, (-w / 2 + .12 + i * .2, .02, .2), .45, .03, 90, -75, "Body")
            elif r_ % 2:
                loaf(X, (-w / 2 + .14 + i * .2, 0, .01), "Body", 90)
            else:
                for k in range(2):
                    roll(X, (-w / 2 + .1 + i * .2 + k * .08, -.03 + k * .04, .04), .042, "Body", i + k)


def wood_counter(acc, W, y, D=.7, front=PLANKS, top=WOOD_L, H=.9):
    rbox(acc, (W, D, H - .05), (0, y, (H - .05) / 2), front, .02, 2, uv=1.3)
    rbox(acc, (W + .04, D + .04, .05), (0, y, H - .025), top, .015, 2)
    rbox(acc, (W - .1, .01, .012), (0, y - D / 2 - .004, H - .1), C(GOLD), .003, 1)
    rbox(acc, (W - .04, .03, .08), (0, y - D / 2 + .01, .04), C(NAVY), .01, 2)


def bakery_case(acc, W, y, H=.9):
    """Heated glass case for cakes and pastries, on a wood/navy base."""
    rbox(acc, (W, .7, H - .05), (0, y, (H - .05) / 2), C(NAVY), .03, 3)
    n = int(W / .06)
    for k in range(n):
        rbox(acc, (.034, .016, H - .3), (-W / 2 + .05 + k * (W - .1) / (n - 1), y - .356, H / 2), WOOD_L, .006, 1)
    rbox(acc, (W + .02, .74, .04), (0, y, H), WOOD, .01, 2)
    rbox(acc, (W - .06, .012, .4), (0, y - .3, H + .22), GLASS, .004, 1, rot=(-10, 0, 0))
    rbox(acc, (W - .06, .55, .012), (0, y - .02, H + .44), GLASS, .004, 1)
    rbox(acc, (W - .1, .02, .012), (0, y + .2, H + .42), LED, .004, 1)
    for s in (-1, 1):
        rbox(acc, (.03, .6, .44), (s * (W / 2 - .02), y, H + .22), C(NAVY), .01, 1)
    x = -W / 2 + .15
    k = 0
    while x < W / 2 - .12:
        if k % 2:
            cake(acc, (x, y - .05, H + .02), .08, .07, ["F4A6C1", "7A4A2E", "F2C23F"][k % 3])
        else:
            croissant(acc, (x, y - .1, H + .02), 1, 10 * k)
            croissant(acc, (x, y + .08, H + .02), 1, -10 * k)
        x += .22
        k += 1


def padaria(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, BRICK, "T_IK_WoodLight" if tier > 1 else None, .9, uv=1.6)
    if tier == 1:
        dome_oven(acc, -W / 2 + .7, yb - .55, .48)
        bread_wall(acc, .55, yb - .2, 1.1, 1.0, .25, 3)
        wood_counter(acc, W - .3, -D / 2 + .45)
        for i, x in enumerate((-.75, -.15, .45)):
            X = basket(acc, .5, .34, .1, (x, -D / 2 + .42, .9), 10)
            for k in range(4):
                if i == 1:
                    loaf(X, (-.17 + k * .11, 0, 0), "Body", 90)
                else:
                    roll(X, (-.17 + k * .11, 0, .05), .042, "Body", k)
        for k in range(2):
            flour_sack(acc, (W / 2 - .2, yb - .6 - k * .35, 0), 1.0, 20 * k)
        rbox(acc, (.18, .02, 1.3), (-W / 2 + .2, yb - .9, .65), WOOD, .01, 1, rot=(0, 12, 0))
        name_board(acc, 0, yb - .08, H - .2)
    elif tier == 2:
        # brick arch around a bigger dome oven, bread walls both sides, counter with baskets + cake case
        dome_oven(acc, 0, yb - .7, .62)
        bread_wall(acc, -W / 2 + .62, yb - .2, 1.0, 1.4, .9, 3)
        bread_wall(acc, W / 2 - .62, yb - .2, 1.0, 1.4, .9, 3)
        Xw = Xf(acc, (-W * .2, 0, 0))
        wood_counter(Xw, W * .55, -D / 2 + .45, .7)
        for i, x in enumerate((-.55, 0, .55)):
            Bk = basket(Xw, .48, .34, .1, (x, -D / 2 + .42, .9), 10)
            for k in range(4):
                roll(Bk, (-.16 + k * .1, 0, .05), .042, "Body", k + i)
        Xc = Xf(acc, (W * .3, 0, 0))
        bakery_case(Xc, W * .36, -D / 2 + .45)
        for k in range(3):
            flour_sack(acc, (-W / 2 + .25 + (k % 2) * .3, -D / 2 + 1.1 + k * .05, 0), 1.0, 30 * k)
        name_board(acc, 0, yb - .08, H - .15, 1.3)
        pendant(acc, -.8, -D / 2 + .45, H + .3, 1.95)
        pendant(acc, .8, -D / 2 + .45, H + .3, 1.95)
    else:
        # artisan bakery: brick arch wall, grand oven with a gold rim, two bread walls, bread racks on wheels,
        # a long ripado counter with a heated case, sack pyramid, pendants
        dome_oven(acc, 0, yb - .8, .72)
        arch = frame_bm(2.0, 2.4, .2, .6, .18)
        place(arch, (0, yb - .14, 1.2)); acc.add(arch, BRICK)
        bread_wall(acc, -W / 2 + .75, yb - .2, 1.3, 1.6, .9, 4)
        bread_wall(acc, W / 2 - .75, yb - .2, 1.3, 1.6, .9, 4)
        Xc = Xf(acc, (-.55, 0, 0))
        bakery_case(Xc, 2.0, -D / 2 + .5)
        Xw = Xf(acc, (1.25, 0, 0))
        wood_counter(Xw, 1.1, -D / 2 + .5, .7, PLANKS, WOOD_L)
        for i, x in enumerate((-.3, .3)):
            Bk = basket(Xw, .48, .36, .1, (x, -D / 2 + .48, .9), 10)
            for k in range(4):
                if i:
                    baguette(Bk, (-.18 + k * .12, 0, .05), .42, .03, 0, 0, "Body")
                else:
                    roll(Bk, (-.16 + k * .1, 0, .05), .042, "Body", k)
        for side in (-1, 1):
            rx = side * (W / 2 - .45)
            for z in (.25, .55, .85, 1.15):
                rbox(acc, (.5, .4, .02), (rx, -D / 2 + 1.3, z), BRUSHED, .005, 1)
                for k in range(3):
                    roll(acc, (rx - .15 + k * .15, -D / 2 + 1.3, z + .03), .04, "Body", k)
            for sx in (-1, 1):
                tube(acc, [(rx + sx * .24, -D / 2 + 1.12, .05), (rx + sx * .24, -D / 2 + 1.12, 1.35)], .012, C(CHROME), 6)
                tube(acc, [(rx + sx * .24, -D / 2 + 1.48, .05), (rx + sx * .24, -D / 2 + 1.48, 1.35)], .012, C(CHROME), 6)
        for k, (x, z) in enumerate(((-.35, 0), (.0, 0), (.35, 0), (-.17, .38), (.17, .38))):
            flour_sack(acc, (x - W / 2 + 1.0, -D / 2 + 1.0 + (k % 2) * .05, z), .9, 15 * k)
        name_board(acc, 0, yb - .1, H - .1, 1.6, .4)
        for x in (-1.2, 0, 1.2):
            pendant(acc, x, -D / 2 + .5, H + .4, 2.0)


def meat_cut(acc, loc, s=1.0):
    """Hanging cured ham / beef cut on a hook."""
    x, y, z = loc
    tube(acc, [(x, y, z), (x, y, z - .08)], .004, C(CHROME), 4)
    lathe(acc, [(0, 0), (.04 * s, -.03 * s), (.08 * s, -.13 * s), (.09 * s, -.25 * s), (.06 * s, -.34 * s), (0, -.36 * s)], (x, y, z - .08), "T_IK_Meat", 12, 1)
    lathe(acc, [(.0, 0), (.012, 0), (.012, .05), (0, .05)], (x, y, z - .08 - .36 * s), C(CREAM), 6, 0)


def sausage_string(acc, x, y, z, n=4):
    for k in range(n):
        lathe(acc, [(0, 0), (.022, -.02), (.024, -.1), (.02, -.13), (0, -.14)], (x, y, z - k * .145), C("8E2F2A"), 8, 0)


def meat_case(acc, W, y, H=.9, D=.75):
    """Refrigerated serve-over meat case: steel and navy body, straight front glass, steaks on angled trays."""
    rbox(acc, (W, D, H - .05), (0, y, (H - .05) / 2), C(NAVY), .03, 3)
    rbox(acc, (W - .1, .01, .3), (0, y - D / 2 - .004, .45), BRUSHED, .01, 1)
    rbox(acc, (W + .02, D + .02, .04), (0, y, H), BRUSHED, .01, 2)
    rbox(acc, (W - .06, .012, .42), (0, y - D / 2 + .08, H + .21), GLASS, .004, 1, rot=(-18, 0, 0))
    rbox(acc, (W - .06, .4, .012), (0, y + .05, H + .42), GLASS, .004, 1)
    for s in (-1, 1):
        rbox(acc, (.03, D - .1, .44), (s * (W / 2 - .02), y, H + .22), BRUSHED, .01, 1)
    rbox(acc, (W - .1, .02, .012), (0, y + .22, H + .4), ICE, .004, 1)
    X = Xf(acc, (0, y, H + .02), (12, 0, 0))
    rbox(X, (W - .1, .5, .02), (0, 0, 0), C(WHITE), .005, 1)
    x = -W / 2 + .14
    k = 0
    while x < W / 2 - .1:
        rbox(X, (.2, .4, .015), (x + .05, 0, .015), BRUSHED, .005, 1)
        for j in range(2):
            steak(X, (x + .05, -.1 + j * .2, .03), 1.0, 15 * (k + j))
        x += .24
        k += 1


def butcher_block(acc, x, y, w=.7, d=.55):
    rbox(acc, (w, d, .25), (x, y, .72), "T_IK_ButcherBlock", .03, 2, uv=3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rbox(acc, (.07, .07, .62), (x + sx * (w / 2 - .06), y + sy * (d / 2 - .06), .31), WOOD_D, .015, 2)
    rbox(acc, (w - .1, d - .1, .03), (x, y, .2), WOOD_D, .01, 1)
    rbox(acc, (.14, .006, .1), (x + .1, y, .9), C(CHROME), .003, 1, rot=(0, 0, 20))
    rbox(acc, (.04, .02, .1), (x + .2, y + .04, .87), WOOD_D, .008, 1, rot=(0, 0, 20))
    steak(acc, (x - .12, y, .86), 1.3, 30)


def acougue(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, TILE_W, C(NAVY) if tier > 1 else None, 1.0, uv=1.5)
    # steel rail with the cuts and sausages
    n = {1: 3, 2: 6, 3: 9}[tier]
    rw = W - .6
    tube(acc, [(-rw / 2, yb - .3, H - .35), (rw / 2, yb - .3, H - .35)], .018, C(CHROME), 8)
    for sx in (-1, 1):
        tube(acc, [(sx * rw / 2, yb - .3, H - .35), (sx * rw / 2, yb - .08, H - .35)], .012, C(CHROME), 6)
    for i in range(n):
        x = -rw / 2 + .15 + i * (rw - .3) / max(1, n - 1)
        if i % 3 == 1:
            sausage_string(acc, x, yb - .3, H - .37, 4)
        else:
            meat_cut(acc, (x, yb - .3, H - .37), 1.0 if tier < 3 else 1.15)
    if tier == 1:
        butcher_block(acc, -W / 2 + .55, yb - .75)
        meat_case(acc, W - .5, -D / 2 + .42, .9, .7)
        lathe(acc, [(0, 0), (.15, 0), (.17, .04), (0, .04)], (W / 2 - .4, yb - .4, .95), C(CHROME), 14, 0)
        rbox(acc, (.3, .25, .25), (W / 2 - .4, yb - .4, .8), C(NAVY), .03, 2)
        name_board(acc, 0, yb - .08, H - .15, 1.0)
    elif tier == 2:
        butcher_block(acc, -W / 2 + .6, yb - .8)
        butcher_block(acc, .1, yb - .8)
        meat_case(acc, W - .4, -D / 2 + .42)
        # grinder and a knife magnet
        rbox(acc, (.35, .3, .3), (W / 2 - .45, yb - .5, 1.05), C(CHROME), .04, 2)
        lathe(acc, [(0, 0), (.1, 0), (.12, .2), (0, .2)], (W / 2 - .45, yb - .5, 1.2), C(CHROME), 12, 0)
        rbox(acc, (.9, .03, .05), (W / 2 - .7, yb - .08, 1.5), C(INK), .01, 1)
        for k in range(5):
            rbox(acc, (.03, .01, .22), (W / 2 - 1.05 + k * .12, yb - .1, 1.4), C(CHROME), .003, 1)
        name_board(acc, 0, yb - .08, H - .15, 1.2)
        pendant(acc, -.8, -D / 2 + .42, H + .3, 1.95)
        pendant(acc, .8, -D / 2 + .42, H + .3, 1.95)
    else:
        # dry-ageing cabinet: tall glass-door cabinet, lit, two beef sides
        cx = W / 2 - .55
        rbox(acc, (.9, .7, 2.2), (cx, yb - .42, 1.1), C(NAVY), .04, 3)
        rbox(acc, (.74, .02, 1.8), (cx, yb - .78, 1.15), GLASS, .01, 1)
        rbox(acc, (.7, .5, 1.75), (cx, yb - .45, 1.15), "E_FFE0D0", .01, 1)
        for k in range(2):
            lathe(acc, [(0, 0), (.08, -.1), (.13, -.45), (.12, -.9), (.07, -1.2), (0, -1.25)], (cx - .15 + k * .3, yb - .5, 1.95), "T_IK_Meat", 14, 1)
        rbox(acc, (.9, .01, .012), (cx, yb - .78, 2.1), C(GOLD), .003, 1)
        butcher_block(acc, -W / 2 + .7, yb - .85, .9, .6)
        Xc = Xf(acc, (-.35, 0, 0))
        meat_case(Xc, W - 1.1, -D / 2 + .45)
        tile_arch = frame_bm(2.2, 2.3, .14, .7, .12)
        place(tile_arch, (-.45, yb - .1, 1.15)); acc.add(tile_arch, C(NAVY))
        name_board(acc, -.45, yb - .2, H - .1, 1.4, .36)
        for x in (-1.4, -.45, .5):
            pendant(acc, x, -D / 2 + .45, H + .4, 2.0)


def provolone(acc, x, y, z, s=1.0):
    tube(acc, [(x, y, z), (x, y, z - .12)], .004, ROPE, 4)
    lathe(acc, [(0, 0), (.03 * s, -.02 * s), (.065 * s, -.12 * s), (.07 * s, -.22 * s), (.05 * s, -.3 * s), (0, -.32 * s)], (x, y, z - .12), C("E8C46A"), 12, 1)


def wheel_rack(acc, x, y, w, h, levels=4, d=.42):
    """Wooden cheese rack: dark-wood frame, slatted shelves, wheels of different sizes."""
    for sx in (-1, 1):
        rbox(acc, (.06, d, h), (x + sx * (w / 2 - .03), y, h / 2), WOOD_D, .015, 2)
    rbox(acc, (w, .03, h), (x, y + d / 2 - .015, h / 2), WOOD_D, .01, 1)
    for i in range(levels):
        z = .15 + i * (h - .2) / levels
        for k in range(4):
            rbox(acc, (w - .1, .08, .02), (x, y - d / 2 + .06 + k * .1, z), WOOD, .006, 1)
        n = int((w - .14) / .26)
        for j in range(n):
            r = .1 if (i + j) % 3 else .12
            cheese_wheel(acc, (x - w / 2 + .17 + j * .26, y, z + .012), r, .08 + .02 * ((i + j) % 2))


def cloche(acc, x, y, z, r=.13):
    rbox(acc, (r * 2.4, r * 2.4, .03), (x, y, z + .015), WOOD, .01, 1)
    blob(acc, (r * .7, r * .5, .05), (x, y, z + .06), C("F2D27A"), 1, .1, 2)
    lathe(acc, [(r, 0), (r, .1), (r * .8, .2), (r * .3, .25), (0, .26)], (x, y, z + .03), GLASS, 14, 1, cap_bottom=False)
    lathe(acc, [(0, 0), (.02, 0), (.02, .03), (0, .035)], (x, y, z + .29), C(GOLD), 8, 0)


def queijaria(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, PLASTER, WOOD_D, .9, uv=1.5)
    if tier == 1:
        wheel_rack(acc, -W / 2 + .7, yb - .3, 1.2, 1.9, 4)
        wood_counter(acc, W - .4, -D / 2 + .45, .7, WOOD_D, WOOD)
        for k, x in enumerate((-.6, -.25, .1)):
            cheese_wheel(acc, (x, -D / 2 + .45, .9), .12, .1)
        cloche(acc, .55, -D / 2 + .45, .9)
        beam_y = yb - .7
        for sx in (-1, 1):
            rbox(acc, (.08, .08, 2.1), (W / 2 - .2 + (sx - 1) * .45, beam_y, 1.05), WOOD_D, .02, 2)
        rbox(acc, (1.0, .08, .08), (W / 2 - .65, beam_y, 2.1), WOOD_D, .02, 2)
        for k in range(4):
            provolone(acc, W / 2 - 1.0 + k * .22, beam_y, 2.06, 1.0 - .1 * (k % 2))
        name_board(acc, .35, yb - .08, H - .15, .9)
    elif tier == 2:
        arch = frame_bm(W - .4, H - .1, .14, .8, .16)
        place(arch, (0, yb - .1, (H - .1) / 2)); acc.add(arch, STONE)
        wheel_rack(acc, -.7, yb - .35, 1.3, 2.1, 5)
        wheel_rack(acc, .7, yb - .35, 1.3, 2.1, 5)
        # dark wood counter with a flat glass case
        rbox(acc, (W - .5, .7, .85), (0, -D / 2 + .45, .425), WOOD_D, .03, 2)
        for k in range(3):
            fr = frame_bm((W - .7) / 3 - .1, .5, .02, .04, .05); place(fr, (-(W - .7) / 3 + k * (W - .7) / 3, -D / 2 + .095, .42)); acc.add(fr, WOOD)
        rbox(acc, (W - .48, .74, .04), (0, -D / 2 + .45, .87), WOOD, .01, 2)
        rbox(acc, (W - .6, .5, .3), (0, -D / 2 + .5, 1.04), GLASS, .01, 1)
        x = -W / 2 + .5
        k = 0
        while x < W / 2 - .4:
            if k % 2:
                cheese_wheel(acc, (x, -D / 2 + .5, .89), .1, .08)
            else:
                blob(acc, (.09, .06, .05), (x, -D / 2 + .5, .93), C("F2D27A"), 1, .1, k)
            x += .25
            k += 1
        beam_y = -D / 2 + 1.0
        rbox(acc, (W - .3, .08, .08), (0, beam_y, 2.2), WOOD_D, .02, 2)
        for sx in (-1, 1):
            rbox(acc, (.08, .08, 2.2), (sx * (W / 2 - .15), beam_y, 1.1), WOOD_D, .02, 2)
        for k in range(7):
            provolone(acc, -W / 2 + .5 + k * (W - 1) / 6, beam_y, 2.16, 1.0 - .12 * (k % 2))
        name_board(acc, 0, yb - .2, H - .1, 1.2)
    else:
        # vaulted cellar: stone arch + barrel vault ribs, floor-to-ceiling racks, wheel pyramid, tasting counter
        arch = frame_bm(W - .2, H + .1, .16, 1.4, .2)
        place(arch, (0, yb - .12, (H + .1) / 2)); acc.add(arch, STONE)
        rbox(acc, (W, .14, .9), (0, yb - .02, .45), STONE, .02, 2, uv=1.5)
        for x in (-1.3, 0, 1.3):
            wheel_rack(acc, x, yb - .3, 1.2, 2.4, 6)
        wood_counter(acc, W - .8, -D / 2 + .5, .75, WOOD_D, WOOD)
        for k, x in enumerate((-1.1, -.4, .3, 1.0)):
            rbox(acc, (.45, .3, .03), (x, -D / 2 + .5, .92), WOOD, .01, 1, rot=(0, 0, 8 * (k % 2)))
            for j in range(3):
                rbox(acc, (.08, .06, .05), (x - .12 + j * .12, -D / 2 + .5, .96), C("F2D27A"), .01, 1, rot=(0, 0, 30 * j))
            for j in range(5):
                blob(acc, (.012, .012, .012), (x + .15, -D / 2 + .44 + j * .025, .955), C("6A2B5C"), 1, 0, j)
        # pyramid of wheels at the front corner
        for lvl, n in enumerate((3, 2, 1)):
            for j in range(n):
                cheese_wheel(acc, (W / 2 - .5 + (j - (n - 1) / 2) * .27, -D / 2 + 1.3, lvl * .1), .13, .1)
        for k in range(9):
            provolone(acc, -W / 2 + .5 + k * (W - 1) / 8, -D / 2 + 1.1, 2.6, 1.0 - .12 * (k % 2))
        rbox(acc, (W - .4, .08, .08), (0, -D / 2 + 1.1, 2.64), WOOD_D, .02, 2)
        name_board(acc, 0, yb - .25, H - .2, 1.4, .36)
        for x in (-1.2, 0, 1.2):
            pendant(acc, x, -D / 2 + .5, H + .4, 2.1)


def ice_slope(acc, w, d, loc, tilt=18, fish_n=None, seed=0):
    """Inclined ice bed (crushed ice mound on a steel tray tilted towards the customer) with fish and lemons."""
    rnd = random.Random(seed)
    x, y, z = loc
    X = Xf(acc, (x, y, z), (tilt, 0, 0))
    open_box(X, w, d, .1, (0, 0, 0), BRUSHED, .015, .006, 2)
    blob(X, (w / 2 - .02, d / 2 - .02, .05), (0, 0, .06), C("EEF8FC"), 2, .12, seed)
    n = fish_n or max(2, int(w / .3))
    for i in range(n):
        fx = -w / 2 + .18 + i * (w - .36) / max(1, n - 1)
        for row in range(2 if d > .45 else 1):
            fish_body(X, (fx, -d / 4 + row * d / 2, .09), .42, 60 + rnd.uniform(-12, 12), "Body", ["T_IK_FishScale", C("8FA3AE"), C("D74A3C")][(i + row) % 3])
        fruit(X, "lemon", (fx + .13, 0, .1), "Body", i)


def fish_crate(acc, loc, yaw=0, seed=0):
    x, y, z = loc
    X = Xf(acc, (x, y, z), (0, 0, yaw))
    open_box(X, .5, .34, .14, (0, 0, 0), CRATE, .016, .006, 2.5)
    blob(X, (.22, .14, .04), (0, 0, .07), C("EEF8FC"), 1, .1, seed)
    for k in range(3):
        fish_body(X, (-.12 + k * .12, 0, .08), .26, 90, "Body", ["T_IK_FishScale", C("8FA3AE")][k % 2])


def hanging_scale(acc, x, y, z):
    tube(acc, [(x, y, z), (x, y, z - .3)], .006, C(CHROME), 4)
    lathe(acc, [(0, 0), (.1, 0), (.1, .04), (0, .04)], (x, y - .002, z - .45), C(CHROME), 16, 0, rot=(90, 0, 0))
    lathe(acc, [(0, 0), (.085, 0), (.085, .005), (0, .005)], (x, y - .045, z - .45), C(WHITE), 16, 0, rot=(90, 0, 0))
    for k in range(3):
        a = k * 2.09
        tube(acc, [(x, y, z - .5), (x + .14 * math.cos(a), y + .14 * math.sin(a), z - .72)], .003, C(CHROME), 3)
    lathe(acc, [(0, 0), (.16, 0), (.18, .05), (0, .02)], (x, y, z - .76), C(CHROME), 16, 0)


def fishing_net(acc, x0, x1, y, z0, z1):
    for k in range(int((x1 - x0) / .12) + 1):
        tube(acc, [(x0 + k * .12, y, z1), (x0 + k * .12 + .03, y, (z0 + z1) / 2), (x0 + k * .12, y, z0)], .004, ROPE, 3)
    for k in range(int((z1 - z0) / .12) + 1):
        z = z0 + k * .12
        tube(acc, [(x0, y, z), ((x0 + x1) / 2, y, z - .04 * math.sin(k)), (x1, y, z)], .004, ROPE, 3)
    for k in range(3):
        blob(acc, (.05, .03, .05), (x0 + .2 + k * (x1 - x0 - .4) / 2, y - .02, z0 + .05), C(CREAM), 1, 0, k)


def peixaria(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, TILE_W, TILE_B, 1.1, uv=1.5)
    if tier == 1:
        rbox(acc, (W - .4, .75, .75), (0, -D / 2 + .5, .375), BRUSHED, .03, 2)
        ice_slope(acc, W - .5, .65, (0, -D / 2 + .5, .76), 16, None, 1)
        for k in range(2):
            fish_crate(acc, (W / 2 - .4, yb - .5, k * .15), 10 * k, k)
        fish_crate(acc, (-W / 2 + .45, yb - .5, 0), -5, 3)
        hanging_scale(acc, 0, yb - .5, 2.1)
        fishing_net(acc, -W / 2 + .3, -.3, yb - .07, 1.25, 2.1)
        name_board(acc, .6, yb - .08, H - .2, .9)
    elif tier == 2:
        rbox(acc, (W - .3, .8, .78), (0, -D / 2 + .5, .39), BRUSHED, .03, 2)
        rbox(acc, (W - .4, .01, .3), (0, -D / 2 + .09, .4), TILE_B, .01, 1)
        ice_slope(acc, W - .4, .72, (0, -D / 2 + .5, .79), 18, None, 2)
        rbox(acc, (1.0, .55, .9), (W / 2 - .7, yb - .4, .45), BRUSHED, .03, 2)
        lathe(acc, [(0, 0), (.22, 0), (.22, -.14), (0, -.15)], (W / 2 - .7, yb - .4, .9), C(CHROME), 16, 0)
        tube(acc, [(W / 2 - .5, yb - .2, .9), (W / 2 - .5, yb - .2, 1.25), (W / 2 - .65, yb - .3, 1.25)], .012, C(CHROME), 8)
        for k in range(3):
            fish_crate(acc, (-W / 2 + .45, yb - .5, k * .15), 8 * k, k)
        hanging_scale(acc, -.2, yb - .6, 2.3)
        fishing_net(acc, -W / 2 + .3, .3, yb - .07, 1.35, 2.4)
        name_board(acc, .2, yb - .1, H - .15, 1.1)
        pendant(acc, -.8, -D / 2 + .5, H + .3, 1.95)
        pendant(acc, .8, -D / 2 + .5, H + .3, 1.95)
    else:
        # ice island in two steps + lobster tank + full tile wall
        rbox(acc, (W - .4, 1.1, .7), (0, -D / 2 + .7, .35), BRUSHED, .04, 2)
        rbox(acc, (W - .5, .01, .3), (0, -D / 2 + .149, .36), TILE_B, .01, 1)
        ice_slope(acc, W - .5, .55, (0, -D / 2 + .5, .72), 14, None, 3)
        ice_slope(acc, W - .5, .5, (0, -D / 2 + .98, .88), 20, None, 4)
        tx = -W / 2 + .75
        rbox(acc, (1.1, .55, .7), (tx, yb - .4, .35), C(NAVY), .03, 2)
        rbox(acc, (1.1, .55, .6), (tx, yb - .4, 1.0), GLASS, .02, 1)
        rbox(acc, (1.04, .5, .5), (tx, yb - .4, .97), C("2F6F8F"), .02, 1)
        for k in range(3):
            blob(acc, (.09, .04, .03), (tx - .3 + k * .3, yb - .4, .76), C("C0392B"), 1, .15, k)
        rbox(acc, (1.12, .57, .05), (tx, yb - .4, 1.32), C(NAVY), .02, 2)
        for k in range(2):
            for j in range(2):
                fish_crate(acc, (W / 2 - .45, yb - .45 - j * .4, k * .15), 10 * (j + k), j + k)
        hanging_scale(acc, .5, -D / 2 + .5, 2.55)
        fishing_net(acc, -.1, W / 2 - .3, yb - .07, 1.4, 2.6)
        name_board(acc, -.6, yb - .2, H - .15, 1.3, .36)
        for x in (-1.3, 0, 1.3):
            pendant(acc, x, -D / 2 + .7, H + .4, 2.05)


def gelato_case(acc, W, y, H=.95, rows=2, seed=0):
    """Curved-glass gelato case: navy body, light-wood slats, steel pans with mounded flavours and paddles."""
    rbox(acc, (W, .8, H - .05), (0, y, (H - .05) / 2), C(NAVY), .04, 3)
    n = int(W / .07)
    for k in range(n):
        rbox(acc, (.034, .016, H - .4), (-W / 2 + .1 + k * (W - .2) / (n - 1), y - .406, H / 2), WOOD_L, .006, 1)
    rbox(acc, (W - .1, .01, .01), (0, y - .41, H - .15), C(GOLD), .003, 1)
    rbox(acc, (W + .02, .82, .04), (0, y, H), BRUSHED, .01, 2)
    cols = int((W - .2) / .27)
    for r_ in range(rows):
        for c in range(cols):
            x = -W / 2 + .2 + c * (W - .4) / max(1, cols - 1)
            yy = y - .12 + r_ * .25
            rbox(acc, (.25, .2, .06), (x, yy, H + .03), BRUSHED, .01, 1)
            bm = blob_bm((.11, .085, .06), 2, .15, c + r_ * 7 + seed)
            uvl = bm.loops.layers.uv.get("UVMap")
            for f in bm.faces:
                for l in f.loops:
                    l[uvl].uv = rk_core.cell_uv("gelato_%d" % ((c + r_ * 3 + seed) % 8), (l.vert.co.x / .22 + .5) % 1, (l.vert.co.y / .17 + .5) % 1)
            place(bm, (x, yy, H + .07)); acc.add(bm, LAB)
            if (c + r_) % 3 == 0:
                rbox(acc, (.025, .18, .01), (x + .05, yy, H + .12), C(CHROME), .004, 1, rot=(0, -25, 0))
    bm = bmesh.new()
    prof = [(0, 0), (.07, .1), (.12, .22), (.14, .34), (.12, .42)]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        v = [bm.verts.new((-W / 2 + .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -b[0], b[1])), bm.verts.new((-W / 2 + .03, -b[0], b[1]))]
        bm.faces.new(v)
    uv_box(bm); place(bm, (0, y - .25, H + .02)); acc.add(bm, GLASS)
    rbox(acc, (W - .04, .45, .012), (0, y + .02, H + .44), GLASS, .004, 1)
    rbox(acc, (W - .1, .02, .012), (0, y + .22, H + .42), LED, .004, 1)


def cone_stand(acc, x, y, z=0, h=1.1):
    """Wooden cone stand: a post with three round trays of waffle cones standing in holes."""
    lathe(acc, [(0, 0), (.18, 0), (.18, .04), (.04, .06), (.03, h), (0, h)], (x, y, z), WOOD, 12, 1)
    for k, zz in enumerate((h * .5, h * .75, h)):
        lathe(acc, [(0, 0), (.16 - k * .03, 0), (.16 - k * .03, .03), (0, .03)], (x, y, z + zz), WOOD_L, 14, 0)
        n = 6 - k
        for j in range(n):
            a = j * 2 * math.pi / n
            r = .11 - k * .025
            lathe(acc, [(0, -.06), (.025, .06)], (x + r * math.cos(a), y + r * math.sin(a), z + zz + .03), "T_IK_Waffle", 8, 0, cap_top=False)


def striped_awning(acc, W, y, z, depth=.6, n=None):
    n = n or int(W / .25)
    for k in range(n):
        x = -W / 2 + (k + .5) * W / n
        rbox(acc, (W / n, depth, .02), (x, y - depth / 2, z), C(NAVY if k % 2 else CREAM), .004, 1, rot=(-20, 0, 0))
        blob(acc, (W / n / 2, .02, .05), (x, y - depth * .95, z - depth * .34 - .02), C(NAVY if k % 2 else CREAM), 1, 0, k)
    rbox(acc, (W + .04, .04, .04), (0, y - .02, z + .02), C(GOLD), .01, 1)


def sorvetes(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, "T_IK_V2_PaintCream", C(NAVY), .9, uv=1.5)
    if tier == 1:
        gelato_case(acc, 1.6, -D / 2 + .5, .95, 2, 0)
        cone_stand(acc, W / 2 - .3, -D / 2 + .45)
        striped_awning(acc, W - .2, yb - .06, 2.05, .55)
        for k in range(4):
            lathe(acc, [(0, 0), (.05, 0), (.06, .14), (0, .14)], (-W / 2 + .4 + k * .2, yb - .25, 1.3), GLASS, 8, 0)
            blob(acc, (.045, .045, .05), (-W / 2 + .4 + k * .2, yb - .25, 1.38), C(["F4A6C1", "7A4A2E", "F2C23F", "B9E8D2"][k]), 1, .2, k)
        rbox(acc, (1.2, .25, .03), (-W / 2 + .7, yb - .2, 1.28), WOOD, .01, 1)
        name_board(acc, .5, yb - .08, 1.6, .9)
    elif tier == 2:
        gelato_case(acc, W - .8, -D / 2 + .5, .95, 2, 3)
        cone_stand(acc, W / 2 - .3, -D / 2 + .5)
        striped_awning(acc, W - .1, yb - .06, 2.25, .6)
        # soft-serve machine and topping jars on the back counter
        rbox(acc, (W - .2, .5, .9), (0, yb - .3, .45), C(NAVY), .03, 2)
        rbox(acc, (W - .18, .54, .04), (0, yb - .3, .92), "T_IK_V2_PaintCream", .01, 1)
        rbox(acc, (.5, .45, .6), (W / 2 - .5, yb - .32, 1.24), C(CREAM), .06, 3)
        for k in range(2):
            tube(acc, [(W / 2 - .6 + k * .2, yb - .55, 1.3), (W / 2 - .6 + k * .2, yb - .6, 1.18)], .025, C(CHROME), 8)
        for k in range(6):
            lathe(acc, [(0, 0), (.05, 0), (.06, .16), (0, .16)], (-W / 2 + .35 + k * .17, yb - .3, .94), GLASS, 8, 0)
            blob(acc, (.045, .045, .06), (-W / 2 + .35 + k * .17, yb - .3, 1.03), C(["F4A6C1", "7A4A2E", "F2C23F", "B9E8D2", "E8505B", "FBF8F1"][k]), 1, .2, k)
        name_board(acc, -.3, yb - .08, 1.75, 1.1)
    else:
        gelato_case(acc, W - 1.3, -D / 2 + .5, .95, 2, 5)
        cone_stand(acc, W / 2 - .45, -D / 2 + .5, 0, 1.25)
        striped_awning(acc, W - .1, yb - .06, 2.5, .7)
        rbox(acc, (W - .2, .5, .9), (0, yb - .3, .45), C(NAVY), .03, 2)
        rbox(acc, (W - .18, .54, .04), (0, yb - .3, .92), "T_IK_V2_PaintCream", .01, 1)
        for k in range(2):
            mx = W / 2 - .5 - k * .6
            rbox(acc, (.5, .45, .6), (mx, yb - .32, 1.24), C(CREAM), .06, 3)
            tube(acc, [(mx, yb - .55, 1.3), (mx, yb - .6, 1.18)], .025, C(CHROME), 8)
        # arched lit niches with sundae cups
        for k in range(3):
            nx = -W / 2 + .6 + k * .55
            fr = frame_bm(.42, .6, .06, .2, .04); place(fr, (nx, yb - .07, 1.6)); acc.add(fr, C(GOLD))
            plate(acc, .36, .54, (nx, yb - .055, 1.6), LED, .01, .17)
            lathe(acc, [(0, 0), (.03, 0), (.01, .06), (.06, .12), (.07, .16), (0, .16)], (nx, yb - .15, 1.38), GLASS, 10, 0)
            blob(acc, (.05, .05, .05), (nx, yb - .15, 1.56), C(["F4A6C1", "7A4A2E", "F2C23F"][k]), 1, .2, k)
        # parlour corner: a round table with two wire chairs
        tx, ty = -W / 2 + .55, -D / 2 + 1.35
        lathe(acc, [(0, 0), (.22, 0), (.22, .03), (.03, .05), (.03, .72), (.32, .72), (.32, .76), (0, .76)], (tx, ty, 0), C(NAVY), 16, 1)
        lathe(acc, [(.32, .76), (.325, .76), (.325, .77), (.32, .77)], (tx, ty, 0), C(GOLD), 16, 0, cap_top=False, cap_bottom=False)
        for s in (-1, 1):
            cx = tx + s * .45
            lathe(acc, [(0, 0), (.18, 0), (.18, .03), (0, .04)], (cx, ty, .45), C(CREAM), 14, 0)
            for k in range(4):
                a = k * math.pi / 2 + .78
                tube(acc, [(cx + .14 * math.cos(a), ty + .14 * math.sin(a), .45), (cx + .17 * math.cos(a), ty + .17 * math.sin(a), 0)], .008, C(NAVY), 4)
            tube(acc, [(cx + s * .16, ty - .12, .48), (cx + s * .2, ty, .85), (cx + s * .16, ty + .12, .48)], .01, C(NAVY), 5, 2)
        name_board(acc, .3, yb - .08, 2.0, 1.3, .36)


def barrel(acc, loc, r=.3, L=.8, lying=False, yaw=0):
    """Oak barrel with dark iron hoops (standing or lying)."""
    x, y, z = loc
    prof = [(0, 0), (r * .86, 0), (r, L * .5), (r * .86, L), (0, L)]
    rot = (0, 90, yaw) if lying else (0, 0, yaw)
    base = (x, y, z + (r if lying else 0))
    if lying:
        base = (x - L / 2 * math.cos(math.radians(yaw)), y - L / 2 * math.sin(math.radians(yaw)), z + r)
    lathe(acc, prof, base, "T_IK_Staves", 16, 2, rot=rot)
    for t in (.12, .38, .62, .88):
        rr = r * (.86 + .14 * math.sin(math.pi * t)) + .004
        bm = lathe_bm([(rr, L * t - .015), (rr, L * t + .015)], 16, 0, cap_top=False, cap_bottom=False)
        place(bm, base, rot); acc.add(bm, C(INK))


def wine_niches(acc, x, y, w, h, z0=0, lit=False, cols=None):
    """Wine wall bay: dark-wood frame, diamond lattice, bottle ends in every niche."""
    rbox(acc, (w, .4, h), (x, y, z0 + h / 2), WOOD_D, .02, 2)
    if lit:
        rbox(acc, (w - .1, .01, h - .1), (x, y - .14, z0 + h / 2), LED, .01, 1)
    n = cols or max(2, int(w / .3))
    cw = (w - .08) / n
    for i in range(n + 1):
        xx = x - w / 2 + .04 + i * cw
        rbox(acc, (.025, .32, h - .08), (xx, y - .2, z0 + h / 2), WOOD, .006, 1)
    rows = int((h - .1) / .14)
    for r_ in range(rows):
        z = z0 + .1 + r_ * (h - .14) / rows
        rbox(acc, (w - .08, .32, .02), (x, y - .2, z - .04), WOOD, .004, 1)
        for i in range(n):
            for j in range(max(1, int(cw / .085))):
                bx = x - w / 2 + .04 + i * cw + (j + .5) * cw / max(1, int(cw / .085))
                lathe(acc, [(0, 0), (.035, 0), (.035, .03), (0, .03)], (bx, y - .33, z + .01), C(["2A3B22", "4A1C24", "3A2A1A"][(i + j + r_) % 3]), 8, 0, rot=(90, 0, 0))


def wine_glass(acc, x, y, z, wine=True):
    lathe(acc, [(0, 0), (.035, 0), (.035, .004), (.004, .01), (.004, .09), (.03, .11), (.04, .16), (.035, .2)], (x, y, z), GLASS, 10, 1, cap_top=False)
    if wine:
        lathe(acc, [(0, .11), (.03, .115), (.036, .14), (0, .14)], (x, y, z), C("6A1A2A"), 10, 0)


def adega(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, BRICK if tier == 3 else "T_IK_WoodDark", WOOD_D, .9, uv=1.5)
    if tier == 1:
        wine_niches(acc, -.3, yb - .26, 1.6, 2.0, 0, False, 5)
        barrel(acc, (W / 2 - .45, -D / 2 + .55, 0), .32, .85)
        lathe(acc, [(0, 0), (.36, 0), (.36, .04), (0, .04)], (W / 2 - .45, -D / 2 + .55, .86), WOOD_D, 16, 0)
        for k in range(2):
            wine_glass(acc, W / 2 - .55 + k * .2, -D / 2 + .5, .9)
        wine_bottle(acc, (W / 2 - .4, -D / 2 + .65, .9), .31, .037, C("4A1C24"), "wine_0", C("7A1E2E"), "Body", 8)
        open_box(acc, .5, .34, .3, (-W / 2 + .5, -D / 2 + .55, 0), CRATE, .016, .006, 2.5)
        for k in range(4):
            wine_bottle(acc, (-W / 2 + .35 + k * .1, -D / 2 + .55, .02), .31, .037, C(["2A3B22", "4A1C24"][k % 2]), "wine_%d" % k, C("D3A53D"), "Body", 8)
        name_board(acc, -.3, yb - .3, 2.2, .9)
    elif tier == 2:
        for k, x in enumerate((-1.05, 0, 1.05)):
            wine_niches(acc, x, yb - .26, .95, 2.2, 0, False, 3)
        # tasting counter: a dark wood top on two standing barrels
        ty = -D / 2 + .55
        for x in (-.75, .75):
            barrel(acc, (x, ty, 0), .3, .85)
        rbox(acc, (2.2, .55, .06), (0, ty, .88), WOOD_D, .02, 2)
        rbox(acc, (2.2, .01, .012), (0, ty - .28, .88), C(GOLD), .003, 1)
        for k in range(4):
            wine_glass(acc, -.6 + k * .4, ty - .05, .91, k % 2 == 0)
        for k in range(2):
            wine_bottle(acc, (-.2 + k * .4, ty + .1, .91), .31, .037, C(["2A3B22", "4A1C24"][k]), "wine_%d" % (k + 1), C("7A1E2E"), "Body", 8)
        # two barrels lying on a cradle
        for k in range(2):
            barrel(acc, (W / 2 - .45, -D / 2 + 1.25 + k * .0, .08 + k * .5), .25, .7, True, 90)
        rbox(acc, (.6, .7, .1), (W / 2 - .45, -D / 2 + 1.25, .05), WOOD_D, .02, 2)
        name_board(acc, 0, yb - .35, 2.45, 1.1)
    else:
        # brick cellar with backlit niches, barrel pyramid, long tasting counter with stools, glass rack
        arch = frame_bm(W - .3, H + .1, .3, 1.3, .25)
        place(arch, (0, yb - .2, (H + .1) / 2)); acc.add(arch, BRICK)
        for x in (-1.15, 0, 1.15):
            wine_niches(acc, x, yb - .26, 1.05, 2.3, 0, True, 3)
        ty = -D / 2 + .5
        rbox(acc, (W - 1.3, .6, .9), (-.45, ty, .45), WOOD_D, .03, 2)
        n = 18
        for k in range(n):
            rbox(acc, (.034, .016, .6), (-.45 - (W - 1.4) / 2 + k * (W - 1.4) / (n - 1), ty - .306, .45), WOOD, .006, 1)
        rbox(acc, (W - 1.26, .66, .05), (-.45, ty, .92), MARBLE, .01, 2)
        for k in range(5):
            wine_glass(acc, -1.4 + k * .45, ty - .05, .945, k % 2 == 0)
        for k in range(3):
            sx = -1.3 + k * .85
            lathe(acc, [(0, 0), (.18, 0), (.18, .03), (.03, .05), (.03, .62), (.17, .65), (.17, .7), (0, .7)], (sx, ty - .55, 0), C(NAVY), 12, 1)
        for lvl, n in enumerate((3, 2)):
            for j in range(n):
                barrel(acc, (W / 2 - .55, -D / 2 + .6 + (j - (n - 1) / 2) * .55, .02 + lvl * .48), .26, .7, True, 90)
        rbox(acc, (1.6, .35, .05), (-.45, ty, 2.05), WOOD_D, .02, 2)
        for k in range(8):
            lathe(acc, [(0, 0), (.035, 0), (.04, -.05), (.004, -.09), (.004, -.17), (.03, -.2)], (-1.15 + k * .2, ty, 2.02), GLASS, 8, 0)
        for s in (-1, 1):
            tube(acc, [(-.45 + s * .75, ty, 2.07), (-.45 + s * .75, ty, H + .3)], .006, C(INK), 4)
        name_board(acc, 0, yb - .45, H - .05, 1.4, .36)


def dispenser(acc, x, y, z, col, r=.13, h=.38):
    rbox(acc, (r * 2.6, r * 2.3, .1), (x, y, z + .05), BRUSHED, .02, 2)
    lathe(acc, [(0, 0), (r, 0), (r * 1.05, h), (0, h)], (x, y, z + .1), GLASS, 12, 0, cap_top=False)
    lathe(acc, [(0, .01), (r * .95, .01), (r, h * .8), (0, h * .8)], (x, y, z + .1), C(col), 12, 0)
    lathe(acc, [(0, 0), (r * 1.08, 0), (r * 1.08, .04), (0, .05)], (x, y, z + .1 + h), C(NAVY), 12, 0)
    rbox(acc, (.04, .05, .06), (x, y - r - .02, z + .17), C(CHROME), .01, 1)


def blender_(acc, x, y, z, col="F28C28"):
    rbox(acc, (.16, .16, .12), (x, y, z + .06), C(NAVY), .03, 2)
    lathe(acc, [(.05, 0), (.07, .25), (.072, .26)], (x, y, z + .12), GLASS, 10, 0, cap_top=False)
    lathe(acc, [(0, 0), (.05, 0), (.065, .16), (0, .16)], (x, y, z + .12), C(col), 10, 0)
    lathe(acc, [(0, 0), (.075, 0), (.075, .03), (0, .03)], (x, y, z + .38), C(INK), 10, 0)


def fruit_front(acc, W, y, z0=.15, rows=2, kinds=("orange", "lemon", "apple", "lime", "orange", "tomato")):
    """Slanted fruit display on the customer face of a juice counter: bins stepping up, full of fruit."""
    n = max(2, int(W / .42))
    for r_ in range(rows):
        for i in range(n):
            x = -W / 2 + (i + .5) * W / n
            X = Xf(acc, (x, y - .05 - (rows - 1 - r_) * .16, z0 + r_ * .3), (22, 0, 0))
            open_box(X, W / n - .04, .3, .1, (0, 0, 0), WOOD, .014, .006, 2)
            produce_pile(X, W / n - .08, .26, (0, 0, .02), kinds[(i + r_ * 2) % len(kinds)], "Body", i + r_ * 5, mound=.05)


def sucos(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, PLANKS if tier == 1 else "T_IK_V2_PaintCream", C(NAVY) if tier > 1 else None, .9, uv=1.4)
    cols = ["F28C28", "E25555", "6DB84A", "F2C23F"]
    if tier == 1:
        cw = W - .3
        cy = -D / 2 + .55
        rbox(acc, (cw, .65, .9), (0, cy, .45), WOOD, .02, 2)
        rbox(acc, (cw + .04, .69, .04), (0, cy, .92), WOOD_L, .01, 2)
        fruit_front(acc, cw - .1, cy - .33, .15, 2)
        for k in range(2):
            dispenser(acc, -.5 + k * .45, cy + .05, .94, cols[k])
        blender_(acc, .5, cy + .05, .94)
        for k in range(6):
            lathe(acc, [(0, 0), (.035, 0), (.04, .12), (0, .12)], (.2 + k * .08, cy - .15, .94), C(cols[k % 4]), 8, 0)
        rbox(acc, (W - .4, .3, .03), (0, yb - .2, 1.4), WOOD, .01, 1)
        for k in range(3):
            Bk = basket(acc, .4, .26, .1, (-.7 + k * .7, yb - .2, 1.42), 0)
            produce_pile(Bk, .36, .22, (0, 0, .02), ["orange", "lemon", "apple"][k], "Body", k, mound=.05)
        name_board(acc, 0, yb - .08, 1.9, .9)
    elif tier == 2:
        cw = W - .3
        cy = -D / 2 + .55
        rbox(acc, (cw, .7, .95), (0, cy, .475), C(NAVY), .03, 2)
        fruit_front(acc, cw - .1, cy - .36, .2, 2)
        rbox(acc, (cw + .04, .74, .04), (0, cy, .97), WOOD_L, .01, 2)
        for k in range(3):
            dispenser(acc, -1.0 + k * .45, cy + .08, .99, cols[k])
        for k in range(2):
            blender_(acc, .6 + k * .3, cy + .08, .99, cols[k + 2])
        for k in range(10):
            lathe(acc, [(0, 0), (.035, 0), (.04, .12), (0, .12)], (-1.2 + k * .25, cy - .2, .99), C(cols[k % 4]), 8, 0)
        for z in (1.25, 1.65):
            rbox(acc, (W - .4, .35, .03), (0, yb - .22, z), WOOD, .01, 1)
            for k in range(4):
                Bk = crate(acc, .55, .3, .12, (-1.05 + k * .7, yb - .22, z + .015), 0)
                produce_pile(Bk, .5, .26, (0, 0, .02), ["orange", "lemon", "apple", "lime"][(k + int(z * 2)) % 4], "Body", k, mound=.05)
        for k in range(3):
            tube(acc, [(-.8 + k * .8, -D / 2 + 1.25, H + .2), (-.8 + k * .8, -D / 2 + 1.25, 2.1)], .004, ROPE, 4)
            blob(acc, (.12, .12, .16), (-.8 + k * .8, -D / 2 + 1.25, 1.95), C(["F28C28", "E8D23A", "F28C28"][k]), 2, .3, k)
        name_board(acc, 0, yb - .08, H - .2, 1.1)
    else:
        # island juice bar: horseshoe counter with stools, dispenser row, fruit cascade, canopy with lamps
        cy = -D / 2 + .7
        rbox(acc, (W - .6, .9, 1.0), (0, cy, .5), C(NAVY), .04, 3)
        n = int((W - .7) / .07)
        for k in range(n):
            rbox(acc, (.034, .016, .6), (-(W - .7) / 2 + k * (W - .7) / (n - 1), cy - .456, .5), WOOD_L, .006, 1)
        rbox(acc, (W - .56, .94, .05), (0, cy, 1.02), MARBLE, .01, 2)
        rbox(acc, (W - .7, .01, .012), (0, cy - .462, .82), C(GOLD), .003, 1)
        for k in range(4):
            dispenser(acc, -1.05 + k * .5, cy + .2, 1.045, cols[k])
        blender_(acc, 1.15, cy + .25, 1.045)
        for k in range(12):
            lathe(acc, [(0, 0), (.035, 0), (.04, .13), (0, .13)], (-1.35 + k * .24, cy - .3, 1.045), C(cols[k % 4]), 8, 0)
        for k in range(4):
            sx = -1.2 + k * .8
            lathe(acc, [(0, 0), (.18, 0), (.18, .03), (.03, .05), (.03, .7), (.17, .73), (.17, .78), (0, .78)], (sx, cy - .75, 0), C(NAVY), 12, 1)
        # fruit cascade on the back wall
        for r_ in range(3):
            X = Xf(acc, (0, yb - .3 - r_ * .05, .9 + r_ * .35), (22, 0, 0))
            for i in range(5):
                x = -W / 2 + .5 + i * (W - 1) / 4
                open_box(X, .62, .3, .1, (x, 0, 0), WOOD, .014, .006, 2)
                produce_pile(X, .58, .26, (x, 0, .02), ["orange", "lemon", "apple", "lime", "tomato"][(i + r_) % 5], "Body", i + r_ * 7, mound=.05)
        fw, fd = W - .5, .9
        for sy in (-1, 1):
            rbox(acc, (fw, .07, .07), (0, cy + sy * fd / 2, H), C(NAVY), .02, 2)
        for sx in (-1, 1):
            rbox(acc, (.07, fd, .07), (sx * fw / 2, cy, H), C(NAVY), .02, 2)
            tube(acc, [(sx * fw / 2, cy, H), (sx * fw / 2, cy, H + .5)], .008, C(INK), 4)
        for x in (-1.1, 0, 1.1):
            pendant(acc, x, cy, H, 2.2, .12)
        name_board(acc, 0, yb - .08, H - .2, 1.3, .36)


def make_sector_v2(sid, fn):
    return [lambda acc, t=t: fn(acc, t) for t in (1, 2, 3)]


for _sid, _fn in (("padaria", padaria), ("acougue", acougue), ("queijaria", queijaria), ("peixaria", peixaria),
                  ("sorvetes", sorvetes), ("adega", adega), ("sucos", sucos)):
    BUILDERS["sector-" + _sid] = make_sector_v2(_sid, _fn)


def clear_lineup(kind, half=4.0):
    """Removes a lineup (its tier collections and the floor, captions and person of its strip) before a rebuild."""
    by = BASE_Y[kind]
    for i in range(len(TIERS[kind])):
        c = bpy.data.collections.get("FT %s T%d" % (kind, i + 1))
        if c:
            for o in list(c.objects):
                bpy.data.objects.remove(o, do_unlink=True)
    sheet = bpy.data.collections.get("FT sheet")
    if sheet:
        for o in list(sheet.objects):
            ys = [(o.matrix_world @ Vector(cc)).y for cc in o.bound_box]
            if abs(sum(ys) / 8 - by) < half:
                bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        if m.users == 0:
            bpy.data.meshes.remove(m)


def rebuild(kind):
    clear_lineup(kind)
    roots, prints, tris, total = lineup_sheet(kind, BASE_Y[kind], kind)
    return tris


def sheet(kind):
    by = BASE_Y[kind]
    n = len(TIERS[kind])
    prints = [(bpy.data.objects["%s-t%d" % (kind, i + 1)].location.x, by, TIERS[kind][i][2], TIERS[kind][i][3]) for i in range(n)]
    total = sum(t[2] for t in TIERS[kind]) + GAP.get(kind, .9) * (n - 1)
    return shots(kind, by, prints, total)


# ================================================================================================ cold room placement (outside)
# The storages are the game's own meshes (Assets/Art/Storage/Meshes/*.asset, converted by unity_mesh_to_obj.py into
# ArtSource/fixture_tiers/context/*.obj), shown in clay so the new cold room (in colour) stands out.
CTX = os.path.join(ART, "context")
PLACE = {  # shot: (storage obj, where it stands in this file, cold room tier, its spot relative to the storage, yaw)
    "T2": ("Depot_74x71", Vector((60, -20, 0)), "T2", (5.0, -.6), 270),
    "T3": ("Depot_74x71", Vector((60, -40, 0)), "T3", (5.25, -.4), 270),
    "T4": ("CentralWarehouse", Vector((120, -30, 0)), "T4", (-13.1, 8.9), 180),
}


def clay(name="FT_Clay2", col=(.42, .45, .5)):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = col + (1,)
    b.inputs["Roughness"].default_value = .8
    return m


def context_building(obj, at, name):
    if bpy.data.objects.get(name):
        return bpy.data.objects[name]
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(CTX, obj + ".obj"), forward_axis="Y", up_axis="Z")
    new = [o for o in bpy.data.objects if o not in before]
    c = coll("FT placement", coll("Fixture tiers"))
    for o in new:
        for uc in list(o.users_collection):
            uc.objects.unlink(o)
        c.objects.link(o)
        o.name = name
        o.location = at
        o.data.materials.clear()
        o.data.materials.append(clay())
    return new[0]


def coldroom_placement_shots():
    c = coll("FT placement", coll("Fixture tiers"))
    out = []
    for shot, (obj, at, tier, (dx, dy), yaw) in PLACE.items():
        b = context_building(obj, at, "CTX %s %s" % (obj, shot))
        if not bpy.data.objects.get("FIX cold %s" % shot):
            instance("coldroom", tier, at + Vector((dx, dy, 0)), yaw, "FIX cold %s" % shot, "FT placement")
            acc = Acc("Yard " + shot)
            rbox(acc, (34, 30, .02), (0, 0, -.012), C("B9B4AA"), 0, 1)
            for k in range(-16, 17, 2):
                rbox(acc, (.03, 30, .003), (k, 0, .001), C("A9A39A"), 0, 1)
            for o in acc.realize(c):
                o.name = "Yard " + shot
                o.location = at
        bpy.context.view_layer.update()
        for o in bpy.context.scene.objects:
            if o.type in ("MESH", "EMPTY") and not o.hide_viewport:
                ctr = o.matrix_world.translation if o.type == "EMPTY" or o.parent else sum((o.matrix_world @ Vector(cc) for cc in o.bound_box), Vector()) / 8
                o.hide_render = (ctr - at).xy.length > 17
        d = Vector((.75, -1, 1.25)) if shot != "T4" else Vector((-.55, 1, 1.25))
        camera(at + Vector((dx * .5, dy * .5, 1.0)), d, 40 if shot != "T4" else 50, 34)
        out.append(render("coldroom_place_%s" % shot, (1800, 1200)))
    return out


# ================================================================================================ ROUND 2: carts, produce, dairy T4, ATM, gumball
NO_TIER_KINDS = {"carts"}   # three separate stations, not tiers: captions show only the name
TIERS["carts"] = [
    ("T1", "Cestinhas (suporte)", .75, .6, 1.1),
    ("T2", "Carrinhos (baia)", 1.75, .75, 1.15),
    ("T3", "Carrinhos grandes (baia)", 2.25, 1.0, 1.25),
]
TIERS["gumball"] = [("T1", "Máquina de chiclete", .5, .5, 1.35), ("T2", "Máquina de chiclete dupla", 1.0, .5, 1.45)]
TIERS["produce"][2] = ("T3", "Banca em degraus (madeira e metal)", 2.0, 1.0, 1.95)
TIERS["dairy"][3] = ("T4", "Ilha de laticínios e frios", 2.5, 1.0, 1.9)
TIERS["atm"] = [("T1", "Caixa eletrônico", .75, .85, 2.0), ("T2", "Dois caixas na parede", 1.5, .85, 2.3),
                ("T3", "Sala de autoatendimento bancário", 2.25, 1.5, 2.6)]


def hand_basket_v2(acc, loc, yaw=0, col=NAVY, handles_up=False, slots=True):
    """Plastic hand basket: tapered body with slots, a cream rim, two folding handles lying on the rim."""
    x, y, z = loc
    X = Xf(acc, (x, y, z), (0, 0, yaw))
    w0, d0, w1, d1, h = .36, .24, .42, .3, .2
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-w0 / 2, -d0 / 2, 0), (w0 / 2, -d0 / 2, 0), (w0 / 2, d0 / 2, 0), (-w0 / 2, d0 / 2, 0),
                                    (-w1 / 2, -d1 / 2, h), (w1 / 2, -d1 / 2, h), (w1 / 2, d1 / 2, h), (-w1 / 2, d1 / 2, h))]
    bm.faces.new((vs[0], vs[1], vs[2], vs[3]))
    for i in range(4):
        bm.faces.new((vs[i], vs[(i + 1) % 4], vs[4 + (i + 1) % 4], vs[4 + i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.008)
    uv_box(bm); X.add(bm, C(col))
    for sy in (-1, 1) if slots else ():
        for k in range(5):
            rbox(X, (.04, .004, .07), (-.12 + k * .06, sy * (d0 / 2 + (d1 - d0) / 4 + .006), h * .55), C(INK), 0, 1, rot=(sy * -8, 0, 0))
    for sy in (-1, 1):
        rbox(X, (w1 + .02, .02, .02), (0, sy * (d1 / 2 + .002), h), C(CREAM), .006, 1)
        rbox(X, (.02, d1 + .02, .02), (sy * (w1 / 2 + .002), 0, h), C(CREAM), .006, 1)
    for sx in (-1, 1):
        if handles_up:
            tube(X, [(sx * .14, -.12, h), (sx * .14, -.08, h + .14), (sx * .14, .08, h + .14), (sx * .14, .12, h)], .009, C(GOLD), 6, 2)
        else:
            tube(X, [(sx * .2, -.12, h + .01), (sx * .23, -.06, h + .015), (sx * .23, .06, h + .015), (sx * .2, .12, h + .01)], .009, C(GOLD), 5, 0)


def carts_t1(acc):
    """Suporte de cestinhas: a navy stand with a base tray, a pole with a blank plaque and two tall nested stacks."""
    rbox(acc, (.72, .52, .06), (0, 0, .03), C(NAVY), .02, 2)
    rbox(acc, (.72, .01, .012), (0, -.262, .05), C(GOLD), .003, 1)
    for k in range(9):
        hand_basket_v2(acc, (-.17, -.02, .06 + k * .055), 0, NAVY, slots=k == 8)
    for k in range(5):
        hand_basket_v2(acc, (.2, .02, .06 + k * .055), 90, BLUE, slots=k == 4)
    tube(acc, [(-.33, .22, .06), (-.33, .22, 1.0)], .016, C(CHROME), 8)
    plate(acc, .3, .2, (-.33, .2, 1.02), C(NAVY), .02, .06)
    plate(acc, .24, .14, (-.33, .188, 1.02), C(CREAM), .01, .04)


def carts_t2(acc):
    """Baia de carrinhos: chrome rails, a row of five nested carts, a navy end post with a blank plaque."""
    for s in (-1, 1):
        tube(acc, [(-.82, s * .34, .02), (-.82, s * .34, .95), (.78, s * .34, .95), (.78, s * .34, .02)], .022, C(CHROME), 8)
        tube(acc, [(-.82, s * .34, .5), (.78, s * .34, .5)], .016, C(CHROME), 6)
    for k in range(5):
        cart(acc, (.42 - k * .17, 0, 0), 180, .85)
    rbox(acc, (.12, .74, 1.1), (.84, 0, .55), C(NAVY), .03, 3)
    plate(acc, .5, .32, (.905, 0, .85), C(CREAM), .012, .05, (0, 0, 90))
    rbox(acc, (.012, .76, .012), (.902, 0, .62), C(GOLD), .003, 1)


def kids_cart(acc, loc, yaw=0, s=.62):
    """Kids' cart: a small cart (handle towards local -X) with a cream toy-car front, blue seat and black wheels."""
    X = Xf(acc, loc, (0, 0, yaw))
    cart(X, (0, 0, 0), 0, s, BLUE)
    L = .8 * s
    cx = L / 2 + .15
    rbox(X, (.32, .34, .2), (cx, 0, .24), C(CREAM), .07, 3)
    rbox(X, (.2, .3, .1), (cx - .02, 0, .39), C(BLUE), .04, 2)
    rbox(X, (.33, .35, .02), (cx, 0, .14), C(GOLD), .008, 1)
    rbox(X, (.02, .26, .1), (cx + .1, 0, .46), GLASS, .008, 1, rot=(0, -20, 0))
    lathe(X, [(0, 0), (.045, 0), (.045, .012), (0, .012)], (cx - .08, 0, .5), C(INK), 12, 0, rot=(0, -60, 0))
    for sx in (-1, 1):
        for sy in (-1, 1):
            lathe(X, [(0, 0), (.055, 0), (.055, .04), (0, .04)], (cx + sx * .1, sy * .19, .055), C(INK), 12, 0, rot=(90, 0, 0))
    for sy in (-1, 1):
        lathe(X, [(0, 0), (.025, 0), (.025, .01), (0, .01)], (cx + .165, sy * .1, .27), "E_FFE6B8", 8, 0, rot=(0, 90, 0))


def carts_t3(acc):
    """Baia de carrinhos grandes: a taller corral, three nested BIG carts (1.3x the normal cart, with a bottom rack)
    and, in their own bay by the post, two kids' carts whose cream toy-car fronts face the aisle."""
    for s in (-1, 1):
        tube(acc, [(-1.08, s * .46, .02), (-1.08, s * .46, 1.18), (.3, s * .46, 1.18), (.3, s * .46, .02)], .024, C(CHROME), 8)
        tube(acc, [(-1.08, s * .46, .6), (.3, s * .46, .6)], .016, C(CHROME), 6)
    for k in range(3):
        x = .3 - .55 - k * .16
        cart(acc, (x, -.02, 0), 180, 1.3)
        rbox(acc, (.86, .44, .012), (x + .02, -.02, .16), C(STEEL), .004, 1)
    # kids' bay: low navy rail, two kids' carts side by side, handles to the customers
    rbox(acc, (.62, .9, .04), (.63, 0, .02), C(BLUE), .015, 2)
    for x in (.48, .79):
        kids_cart(acc, (x, .16, 0), -90, .62)   # toy-car fronts face the aisle
    tube(acc, [(.32, .46, .5), (.94, .46, .5)], .02, C(CHROME), 8)
    rbox(acc, (.12, .96, 1.3), (1.02, 0, .65), C(NAVY), .03, 3)
    plate(acc, .6, .36, (1.085, 0, 1.0), C(CREAM), .012, .05, (0, 0, 90))
    rbox(acc, (.012, .98, .012), (1.082, 0, .76), C(GOLD), .003, 1)
    rbox(acc, (.01, .9, .02), (1.085, 0, 1.27), LED, .005, 1)


def herb_bunch(acc, x, y, z):
    tube(acc, [(x, y, z), (x, y, z - .1)], .003, ROPE, 3)
    for k in range(5):
        a = k * 1.25
        tube(acc, [(x, y, z - .1), (x + .04 * math.cos(a), y + .03 * math.sin(a), z - .28)], .005, C("4E9A3A"), 4)
        blob(acc, (.03, .02, .05), (x + .04 * math.cos(a), y + .03 * math.sin(a), z - .3), C("6DB84A" if k % 2 else "4E9A3A"), 1, .3, k)


def produce_t3(acc):
    """Banca em degraus: navy base, three steps of tilted wooden bins (fruit and veg), a light-wood slat back panel
    with hanging herbs and two wicker baskets, bulk bins with potatoes and onions at the ends, a navy crown."""
    W, D = 1.98, .98
    rbox(acc, (W - .5, D - .1, .35), (0, -.05, .175), C(NAVY), .03, 3)
    rbox(acc, (W - .56, .01, .012), (0, -D / 2 + .002, .3), C(GOLD), .003, 1)
    steps = [(-.3, .38, ["apple", "orange", "lemon"]), (-.02, .62, ["tomato", "lettuce", "pepper"]), (.25, .86, ["banana", "lime", "melon"])]
    for r_, (y, z, kinds) in enumerate(steps):
        if r_:
            rbox(acc, (W - .5, .3, z - .3), (0, y, (z - .3) / 2 + .3), WOOD_D, .015, 2)
        for i in range(3):
            x = -(W - .5) / 2 + (i + .5) * (W - .5) / 3
            X = crate(acc, (W - .5) / 3 - .04, .3, .13, (x, y, z), 18)
            produce_pile(X, (W - .5) / 3 - .08, .26, (0, 0, .03), kinds[i], "Anim Fill %d" % min(3, i + (i > 0)), r_ * 3 + i, mound=.06)
    # bulk bins at the ends
    for s, kind in ((-1, "potato"), (1, "onion")):
        bx = s * (W / 2 - .13)
        open_box(acc, .24, .5, .62, (bx, -.15, 0), WOOD, .02, .008, 2)
        rbox(acc, (.24, .5, .3), (bx, -.15, .15), WOOD_D, .01, 1)
        produce_pile(acc, .2, .45, (bx, -.15, .55), kind, "Body", 11 + s, mound=.05)
        rbox(acc, (.24, .02, .04), (bx, -.4, .64), C(NAVY), .006, 1)
    # slatted back panel with herbs and baskets
    rbox(acc, (W, .08, 1.95), (0, D / 2 - .04, .975), C(NAVY), .02, 2)
    n = 24
    for k in range(n):
        rbox(acc, (.05, .02, 1.0), (-W / 2 + .07 + k * (W - .14) / (n - 1), D / 2 - .09, 1.35), WOOD_L, .006, 1)
    tube(acc, [(-W / 2 + .15, D / 2 - .2, 1.72), (W / 2 - .15, D / 2 - .2, 1.72)], .012, C(CHROME), 6)
    for k in range(6):
        herb_bunch(acc, -W / 2 + .3 + k * (W - .6) / 5, D / 2 - .2, 1.7)
    for x in (-.5, .5):
        Bk = basket(acc, .38, .2, .14, (x, D / 2 - .2, 1.15), 0)
        produce_pile(Bk, .34, .16, (0, 0, .03), "lemon" if x < 0 else "lime", "Body", 3, mound=.04)
    rbox(acc, (W + .04, .3, .1), (0, D / 2 - .12, 2.0), C(NAVY), .03, 3)
    rbox(acc, (W + .05, .008, .012), (0, D / 2 - .275, 2.0), C(GOLD), .003, 1)
    plate(acc, .6, .18, (0, D / 2 - .28, 1.88), C(CREAM), .012, .08)


def produce_t4(acc):
    """Ilha refrigerada com névoa: double-sided chilled island, abundant mounds in mixed wood crates, steel bins and
    wicker baskets, a central tier with melons and pineapple-like fruit, misting bar with visible mist cones, light
    wood slats and gold lines, an arched navy canopy with pendant lights."""
    W, D = 2.46, 1.2
    rbox(acc, (W, D, .55), (0, 0, .275), C(NAVY), .05, 3)
    for s in (-1, 1):
        n = 30
        for k in range(n):
            rbox(acc, (.034, .016, .36), (-W / 2 + .14 + k * (W - .28) / (n - 1), s * (D / 2 + .004), .27), WOOD_L, .006, 1)
        for z in (.08, .47):
            rbox(acc, (W - .24, .01, .01), (0, s * (D / 2 + .012), z), C(GOLD), .003, 1)
        rbox(acc, (W - .3, .02, .02), (0, s * (D / 2 - .03), .03), LED, .006, 1)
    rbox(acc, (W - .1, .3, .38), (0, 0, .74), C(NAVY), .04, 3)
    kinds = [["apple", "orange", "lemon", "tomato", "lime"], ["lettuce", "pepper", "carrot", "banana", "onion"]]
    for si, s in enumerate((-1, 1)):
        for i in range(5):
            x = -W / 2 + .25 + i * (W - .5) / 4
            X = Xf(acc, (x, s * .34, .58), (16 if s < 0 else -16, 0, 0))
            style = (i + si) % 3
            if style == 0:
                open_box(X, .44, .42, .1, (0, 0, 0), CRATE, .016, .006, 2.5)
            elif style == 1:
                open_box(X, .44, .42, .1, (0, 0, 0), BRUSHED, .012, .006, 2)
            else:
                open_box(X, .44, .42, .1, (0, 0, 0), "T_IK_Wicker", .014, .006, 3)
            produce_pile(X, .4, .38, (0, 0, .03), kinds[si][i], "Anim Fill %d" % min(3, i * 4 // 5), si * 5 + i, mound=.11)
    # central tier: melons and a crown of oranges
    for i in range(5):
        x = -W / 2 + .25 + i * (W - .5) / 4
        produce_pile(acc, .4, .24, (x, 0, .93), ["melon", "orange", "apple", "melon", "orange"][i], "Body", 20 + i, mound=.09)
    # misting bar with nozzles and soft mist cones
    for s in (-1, 1):
        tube(acc, [(-W / 2 + .1, s * .2, 1.45), (W / 2 - .1, s * .2, 1.45)], .012, C(CHROME), 8)
        for k in range(8):
            x = -W / 2 + .25 + k * (W - .5) / 7
            lathe(acc, [(0, 0), (.008, 0), (.006, -.02), (0, -.02)], (x, s * .2, 1.44), C(CHROME), 6, 0)
            lathe(acc, [(0, 0), (.01, 0), (.12, -.45), (0, -.47)], (x, s * .26, 1.42), GLASS, 10, 0, rot=(s * 20, 0, 0))
    # arched canopy on four posts, pendant lights, gold edge
    for x in (-W / 2 + .12, W / 2 - .12):
        for y in (-.12, .12):
            tube(acc, [(x, y, .9), (x, y, 1.9)], .025, C(NAVY), 10)
    bm = bmesh.new()
    n = 8
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        v = [bm.verts.new((-W / 2, .45 * math.cos(a0), 1.9 + .18 * math.sin(a0))), bm.verts.new((W / 2, .45 * math.cos(a0), 1.9 + .18 * math.sin(a0))),
             bm.verts.new((W / 2, .45 * math.cos(a1), 1.9 + .18 * math.sin(a1))), bm.verts.new((-W / 2, .45 * math.cos(a1), 1.9 + .18 * math.sin(a1)))]
        bm.faces.new(v)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.03)
    uv_box(bm); acc.add(bm, C(NAVY))
    for s in (-1, 1):
        rbox(acc, (W + .02, .012, .02), (0, s * .45, 1.9), C(GOLD), .004, 1)
        rbox(acc, (W - .2, .02, .015), (0, s * .38, 1.88), LED, .005, 1)
    for x in (-.8, 0, .8):
        pendant(acc, x, 0, 1.92, 1.72, .1)
    plate(acc, .7, .2, (0, -.47, 2.12), C(CREAM), .02, .09)


def dairy_t4(acc):
    """Ilha de laticínios e frios: a low, open, double-sided island (not a door wall): three open steps on each side
    stepping up to the centre, cheese wheels and cold cuts on top, a deli end with a curved glass dome, LED canopy."""
    W, D = 2.46, .98
    rbox(acc, (W, D, .45), (0, 0, .225), C(NAVY), .05, 3)
    for s in (-1, 1):
        n = 30
        for k in range(n):
            rbox(acc, (.034, .016, .3), (-W / 2 + .14 + k * (W - .28) / (n - 1), s * (D / 2 + .004), .23), WOOD_L, .006, 1)
        rbox(acc, (W - .24, .01, .01), (0, s * (D / 2 + .012), .4), C(GOLD), .003, 1)
        rbox(acc, (W - .2, .1, .012), (0, s * (D / 2 - .07), .455), C("3A4450"), .003, 1)
    L = W - .6
    for si, s in enumerate((-1, 1)):
        for step in range(3):
            y = s * (D / 2 - .14 - step * .13)
            z = .47 + step * .24
            rbox(acc, (L, .16, .03), (-.15, y, z), C(WHITE), .006, 1)
            rbox(acc, (L, .012, .06), (-.15, y + s * .085, z + .02), GLASS, .003, 1)
            rbox(acc, (L, .02, .03), (-.15, y + s * .09, z - .02), C(BLUE), .006, 1)
            x = -.15 - L / 2 + .08
            k = 0
            while x < -.15 + L / 2 - .08:
                g = fills_for(x, W)
                if (step + si) % 3 == 0:
                    for st in range(2):
                        yogurt(acc, (x, y, z + .015 + st * .057), g)
                    x += .07
                elif (step + si) % 3 == 1:
                    carton(acc, (x, y, z + .015), .07, .07, .2, ["milk", "juice_0"][k % 2], g)
                    x += .08
                else:
                    cheese_wheel(acc, (x + .05, y, z + .015), .07, .06, g)
                    x += .15
                k += 1
    # top tier: cheese wheels and salami on boards
    rbox(acc, (L, .2, .04), (-.15, 0, 1.2), WOOD, .01, 1)
    for k in range(6):
        if k % 2:
            cheese_wheel(acc, (-.15 - L / 2 + .2 + k * (L - .4) / 5, 0, 1.22), .09, .08)
        else:
            salami(acc, (-.15 - L / 2 + .2 + k * (L - .4) / 5, 0, 1.22), .2, .024, 90)
    # deli end: a glass dome over a ham and cheese board
    ex = W / 2 - .3
    rbox(acc, (.56, D - .1, .02), (ex, 0, .9), WOOD, .01, 1)
    lathe(acc, [(.0, 0), (.2, 0), (.22, .06), (.1, .1), (0, .1)], (ex, 0, .92), "T_IK_Meat", 14, 1)
    lathe(acc, [(.26, 0), (.26, .15), (.2, .28), (.08, .34), (0, .35)], (ex, 0, .92), GLASS, 16, 1, cap_bottom=False)
    lathe(acc, [(0, 0), (.025, 0), (.025, .04), (0, .045)], (ex, 0, 1.27), C(GOLD), 8, 0)
    # canopy
    for x in (-W / 2 + .1, W / 2 - .62):
        tube(acc, [(x, 0, 1.2), (x, 0, 1.85)], .025, C(NAVY), 10)
    rbox(acc, (W - .3, .5, .08), (-.15, 0, 1.88), C(NAVY), .04, 3)
    for s in (-1, 1):
        rbox(acc, (W - .4, .02, .015), (-.15, s * .2, 1.835), LED, .005, 1)
        rbox(acc, (W - .3, .008, .012), (-.15, s * .252, 1.9), C(GOLD), .003, 1)
    plate(acc, .7, .18, (-.15, -.255, 2.04), C(CREAM), .02, .08)


def atm_v2(acc, x, y, wall=False):
    """Cash machine facing -Y: navy cabinet, slanted hood over a recessed lit screen (blank), card slot with a green
    light, receipt slot, keypad under a privacy shield, wide cash dispenser, side privacy wings, lit header."""
    if not wall:
        rbox(acc, (.66, .6, 1.42), (x, y, .71), C(NAVY), .05, 3)
        rbox(acc, (.7, .64, .06), (x, y, .03), C(INK), .02, 2)
    # fascia (the machine's face)
    rbox(acc, (.62, .08, .95), (x, y - .3, 1.0), "T_IK_V2_PaintCream", .03, 3)
    # hood + recessed screen
    rbox(acc, (.62, .24, .05), (x, y - .4, 1.5), C(NAVY), .02, 2, rot=(-12, 0, 0))
    rbox(acc, (.44, .06, .3), (x, y - .34, 1.3), C(INK), .02, 2, rot=(-14, 0, 0))
    rbox(acc, (.36, .01, .23), (x, y - .375, 1.3), LED_COOL, .006, 1, rot=(-14, 0, 0))
    for k in range(4):
        rbox(acc, (.04, .012, .03), (x + (-.25 if k < 2 else .25), y - .37, 1.36 - (k % 2) * .1), C(INK), .006, 1)
    # card slot with a green light, receipt slot
    rbox(acc, (.12, .03, .04), (x + .19, y - .35, 1.08), C(CHROME), .01, 1)
    rbox(acc, (.07, .006, .006), (x + .19, y - .366, 1.08), "E_37D067", 0, 1)
    rbox(acc, (.1, .02, .015), (x - .19, y - .345, 1.08), C(INK), .004, 1)
    # keypad under a privacy shield
    X = Xf(acc, (x - .02, y - .37, .98), (35, 0, 0))
    rbox(X, (.2, .02, .16), (0, 0, 0), C(INK), .01, 1)
    for i in range(3):
        for j in range(4):
            rbox(X, (.045, .012, .03), (-.055 + i * .055, -.012, -.05 + j * .036), C(CREAM if j else CHROME), .006, 1)
    for k, col in enumerate(("C0392B", "F2C23F", "37D067")):
        rbox(X, (.04, .012, .03), (.13, -.012, -.05 + k * .045), C(col), .006, 1)
    rbox(acc, (.26, .1, .02), (x - .02, y - .42, 1.08), C(NAVY), .006, 1, rot=(-20, 0, 0))
    # cash dispenser
    rbox(acc, (.32, .04, .06), (x, y - .35, .78), C(CHROME), .015, 2)
    rbox(acc, (.26, .02, .015), (x, y - .37, .78), C(INK), .004, 1)
    # privacy wings and lit header
    for s in (-1, 1):
        bm, _ = panel_bm(.3, 1.05, .03, .06, 5)
        uv_box(bm); place(bm, (x + s * .34, y - .45, 1.05), (0, 0, 90 + s * 10)); acc.add(bm, C(NAVY))
    rbox(acc, (.7, .3, .22), (x, y - .25, 1.72), C(NAVY), .04, 3)
    plate(acc, .5, .13, (x, y - .401, 1.72), LED, .01, .06)
    rbox(acc, (.7, .01, .012), (x, y - .4, 1.62), C(GOLD), .003, 1)


def atm_t1(acc):
    atm_v2(acc, 0, .1)


def atm_t2(acc):
    """Through-the-wall pair: a navy wall panel with a lit header, two machines set into it, a small counter shelf."""
    rbox(acc, (1.5, .3, 2.25), (0, .28, 1.125), C(NAVY), .04, 3)
    rbox(acc, (1.5, .01, .012), (0, .125, 2.0), C(GOLD), .003, 1)
    for x in (-.37, .37):
        atm_v2(acc, x, .4, wall=True)
    plate(acc, 1.1, .2, (0, .125, 2.12), LED, .012, .08)
    rbox(acc, (1.4, .2, .03), (0, -.05, .85), WOOD, .01, 1)


def atm_t3(acc):
    """Sala de autoatendimento bancário: three machines in a cream wall, glass side screens, a navy canopy with LED,
    a blank cream plaque and a blue floor mat."""
    W, D = 2.2, 1.45
    rbox(acc, (W, .3, 2.5), (0, D / 2 - .15, 1.25), "T_IK_V2_PaintCream", .03, 2)
    for x in (-.72, 0, .72):
        atm_v2(acc, x, D / 2 - .05, wall=True)
    for s in (-1, 1):
        rbox(acc, (.04, D - .3, 2.2), (s * (W / 2 - .02), .1, 1.1), GLASS, .01, 1)
        rbox(acc, (.06, D - .25, .06), (s * (W / 2 - .02), .1, 2.23), C(NAVY), .02, 2)
    rbox(acc, (W + .04, D, .14), (0, 0, 2.5), C(NAVY), .05, 3)
    rbox(acc, (W - .1, .02, .015), (0, -D / 2 + .06, 2.42), LED, .005, 1)
    plate(acc, 1.0, .22, (0, -D / 2 - .005, 2.62), C(CREAM), .03, .1)
    rbox(acc, (W + .04, .01, .012), (0, -D / 2 - .006, 2.45), C(GOLD), .003, 1)
    rbox(acc, (W - .1, D - .1, .02), (0, 0, .01), C(BLUE), .02, 1)


def gumball_globe_v2(acc, x, y, z, r=.17, seed=0):
    rnd = random.Random(seed)
    cols = ["E8505B", "F2C23F", "5FB548", "3E8FD6", "F28C28", "E86A9E", "FBF8F1"]
    n = int(40 * (r / .17) ** 3)
    for i in range(n):
        a = rnd.random() * 6.28
        zz = rnd.random()
        rr = r * .82 * math.sqrt(max(0, 1 - (2 * zz - 1) ** 2)) * math.sqrt(rnd.random())
        blob(acc, (.02, .02, .02), (x + rr * math.cos(a), y + rr * math.sin(a), z - r * .8 + zz * r * 1.2), C(cols[i % 7]), 1, 0, i)
    lathe(acc, [(0, -r), (r * .7, -r * .7), (r, 0), (r * .7, r * .7), (r * .35, r * .93)], (x, y, z), GLASS, 20, 2, cap_top=False, cap_bottom=False)
    lathe(acc, [(r * .36, r * .9), (r * .4, r * .98), (r * .32, r * 1.08), (0, r * 1.1)], (x, y, z), C(NAVY), 16, 1, cap_bottom=False)
    lathe(acc, [(0, 0), (.012, 0), (.012, .05), (.025, .06), (0, .07)], (x, y, z + r * 1.1), C(GOLD), 10, 1)
    lathe(acc, [(r * .37, r * .92), (r * .39, r * .94)], (x, y, z), C(GOLD), 16, 0, cap_top=False, cap_bottom=False)


def gumball_body(acc, x, y, z):
    """Cast metal body: rounded navy housing, coin plate with a chrome crank, chute with a flap, gold bands."""
    lathe(acc, [(0, 0), (.13, 0), (.15, .04), (.15, .17), (.12, .21), (.1, .22), (0, .22)], (x, y, z), C(NAVY), 16, 1)
    for zz in (.04, .17):
        lathe(acc, [(.152, zz), (.156, zz), (.156, zz + .012), (.152, zz + .012)], (x, y, z), C(GOLD), 16, 0, cap_top=False, cap_bottom=False)
    rbox(acc, (.12, .02, .1), (x, y - .145, z + .12), C(CHROME), .01, 1)
    lathe(acc, [(0, 0), (.03, 0), (.03, .015), (0, .02)], (x, y - .16, z + .13), C(CHROME), 12, 0, rot=(90, 0, 0))
    rbox(acc, (.012, .012, .05), (x + .02, y - .17, z + .13), C(CHROME), .004, 1)
    rbox(acc, (.06, .05, .05), (x, y - .14, z + .04), C(INK), .01, 1)
    rbox(acc, (.06, .006, .04), (x, y - .166, z + .045), C(CHROME), .003, 1, rot=(-20, 0, 0))


def gumball_t1(acc):
    """Máquina de chiclete: cast-iron style pedestal with three feet, navy body, glass globe full of gumballs."""
    for k in range(3):
        a = k * 2 * math.pi / 3 + math.pi / 2
        tube(acc, [(0, 0, .25), (.16 * math.cos(a), .16 * math.sin(a), .04), (.22 * math.cos(a), .22 * math.sin(a), 0)], .02, C(NAVY), 8, 2)
        blob(acc, (.03, .03, .015), (.22 * math.cos(a), .22 * math.sin(a), .01), C(GOLD), 1, 0, k)
    lathe(acc, [(0, .2), (.05, .2), (.035, .3), (.03, .78), (.06, .82), (0, .82)], (0, 0, 0), C(NAVY), 14, 1)
    lathe(acc, [(.031, .5), (.036, .5), (.036, .52), (.031, .52)], (0, 0, 0), C(GOLD), 14, 0, cap_top=False, cap_bottom=False)
    gumball_body(acc, 0, 0, .82)
    gumball_globe_v2(acc, 0, 0, 1.2, .17, 1)


def gumball_t2(acc):
    """Dupla: a twin stand (curved navy arms from one column) carrying two machines, a blank plaque between them."""
    lathe(acc, [(0, 0), (.24, 0), (.24, .05), (.06, .08), (.045, .6), (0, .6)], (0, 0, 0), C(NAVY), 16, 1)
    lathe(acc, [(.241, .02), (.245, .02), (.245, .035), (.241, .035)], (0, 0, 0), C(GOLD), 16, 0, cap_top=False, cap_bottom=False)
    for s in (-1, 1):
        tube(acc, [(0, 0, .58), (s * .12, 0, .66), (s * .25, 0, .72), (s * .27, 0, .82)], .035, C(NAVY), 10, 2)
        gumball_body(acc, s * .27, 0, .82)
        gumball_globe_v2(acc, s * .27, 0, 1.22, .18, 4 + s)
    plate(acc, .22, .16, (0, -.03, .78), C(CREAM), .012, .05)
    fr = frame_bm(.24, .18, .01, .05, .012); place(fr, (0, -.04, .78)); acc.add(fr, C(GOLD))


BUILDERS.update({
    "carts": [carts_t1, carts_t2, carts_t3],
    "gumball": [gumball_t1, gumball_t2],
    "atm": [atm_t1, atm_t2, atm_t3],
})
BUILDERS["produce"][2] = produce_t3
BUILDERS["produce"][3] = produce_t4
BUILDERS["dairy"][3] = dairy_t4


# ================================================================================================ Unity export (round 3)
# One FBX per tier at ArtSource/fixture_tiers/export/<kind>_T<n>.fbx, kit convention (rk_core.export): mesh turned
# 180° about Z so the customer side ends at Unity -Z, FBX axis -Z forward / Y up, metres, pivot = footprint centre on
# the floor. Child objects keep the kit names ("Body", "Anim Fill 0..3") so CheckoutInteriorKitBuilder finds them.
# Flat colours get a role suffix (C_RRGGBB_<Role>): KitRemap still reads the hex from chars 2..8, and the role says
# what "Cores do mercado" may repaint (Navy, Blue, Gold) and what it must leave alone (Cream, Metal, Wood, Product).
EXPORT = os.path.join(ART, "export")
APPROVED = ["shelf", "checkout", "drinks", "dairy", "freezer", "icecream", "bakery", "produce", "coldroom",
            "carts", "atm", "gumball", "claw"]
ROLE = {"1D2B4F": "Navy", "2E4A7D": "Blue", "2B3A55": "Blue", "D3A53D": "Gold",
        "F4EBD8": "Cream", "F6E7C8": "Cream", "D9CFB8": "Cream", "FBF8F1": "White", "E3E8E4": "White",
        "DCE3E8": "Metal", "C9D2D6": "Metal", "BFC5C9": "Metal", "EAF6FB": "Metal", "3A4450": "Metal",
        "232A33": "Dark", "2F3A40": "Dark", "6B4128": "Wood", "C9A06A": "Wood"}


def export_role(mat_name, fill):
    if not mat_name.startswith("C_"):
        return mat_name
    hexv = mat_name[2:8]
    return "C_%s_%s" % (hexv, "Product" if fill else ROLE.get(hexv, "Product"))


def export_tier(kind, i, folder=EXPORT):
    """Writes <folder>/<kind>_T<i>.fbx from the lineup collection 'FT <kind> T<i>'. Returns a report dict."""
    os.makedirs(folder, exist_ok=True)
    col = bpy.data.collections["FT %s T%d" % (kind, i)]
    src = [o for o in col.all_objects if o.type == "MESH"]
    dg = bpy.context.evaluated_depsgraph_get()
    R = Matrix.Rotation(math.pi, 4, "Z")
    parked, temps, mats = [], [], {}
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in src:
        nm = "Body" if "Body" in o.name else o.name.split(" ", 1)[1] if o.name.split(" ", 1)[1].startswith("Anim Fill") else o.name
        clash = bpy.data.objects.get(nm)
        if clash:
            parked.append((clash, nm)); clash.name = nm + " (parked)"
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        for v in me.vertices:   # bounds in the modelling space (= Unity x, z, y after export)
            lo = Vector(map(min, lo, v.co)); hi = Vector(map(max, hi, v.co))
        me.transform(R)
        fill = nm.startswith("Anim Fill")
        for k, m in enumerate(me.materials):
            if not m:
                continue
            new = export_role(m.name, fill)
            if new != m.name:
                if new not in mats:
                    mats[new] = bpy.data.materials.get(new) or m.copy()
                    mats[new].name = new
                me.materials[k] = mats[new]
        t = bpy.data.objects.new(nm, me)
        bpy.context.scene.collection.objects.link(t)
        temps.append(t)
    tris = 0; slots = set()
    for t in temps:
        t.data.calc_loop_triangles(); tris += len(t.data.loop_triangles)
        slots |= {m.name for m in t.data.materials if m}
    path = os.path.join(folder, "%s_T%d.fbx" % (kind, i))
    try:
        bpy.ops.object.select_all(action="DESELECT")
        for t in temps:
            t.select_set(True)
        bpy.context.view_layer.objects.active = temps[0]
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, axis_forward="-Z", axis_up="Y",
                                 bake_anim=False, path_mode="STRIP", use_mesh_modifiers=True, mesh_smooth_type="OFF",
                                 apply_scale_options="FBX_SCALE_ALL", use_tspace=False)
    finally:
        for t in temps:
            me = t.data
            bpy.data.objects.remove(t, do_unlink=True)
            bpy.data.meshes.remove(me)
        for m in mats.values():
            bpy.data.materials.remove(m)
        for o, nm in parked:
            o.name = nm
    # Unity bounds: Unity (x, y, z) = modelling (x, z, y); the customer side is Unity -Z
    return {"file": os.path.basename(path), "tris": tris, "objects": [t for t in sorted({("Body" if "Body" in o.name else o.name.split(" ", 1)[1]) for o in src})],
            "size": (round(hi.x - lo.x, 3), round(hi.z - lo.z, 3), round(hi.y - lo.y, 3)),
            "min": (round(lo.x, 3), round(lo.z, 3), round(lo.y, 3)), "max": (round(hi.x, 3), round(hi.z, 3), round(hi.y, 3)),
            "footprint": TIERS[kind][i - 1][2:4], "name": TIERS[kind][i - 1][1], "materials": sorted(slots)}


def export_all(kinds=APPROVED):
    out = []
    for kind in kinds:
        for i in range(1, len(TIERS[kind]) + 1):
            out.append(export_tier(kind, i))
    return out
