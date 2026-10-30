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
from rk_core import Acc, Xf, rbox, rbox_bm, lathe, lathe_bm, tube, blob, panel_bm, frame_bm, place, uv_box, text, material, srgb
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
    lathe(acc, [(0, 0), (.04, 0), (.045, .02 * k), (.045, .1 * k), (.035, .13 * k), (.035, .15 * k)], loc, C(glass), 10, 1, cap_top=False, grp=grp)
    lathe(acc, [(.046, .03 * k), (.046, .09 * k)], loc, LAB, 10, 0, uv_cell=label, u_rep=2, v_range=(.03 * k, .09 * k), cap_top=False, cap_bottom=False, grp=grp)
    lathe(acc, [(0, 0), (.038, 0), (.039, .025), (0, .027)], (x, y, z + .15 * k), C(lid), 10, 1, grp=grp)


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
                box_pack(acc, (x + w / 2, side * (front - .015 - d / 2 - row * (d + .004)), z), w, d, h, labs[k % len(labs)], g)
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
    stock(acc, ("jar", ["pack_9", "pack_10", "pack_8"], ["D74A3C", "E8B23A", "6E8B3D"], NAVY), -inner / 2, inner / 2, -1, D / 2 - y0, -(D / 2 + y0) + .1, .55 + .015, .4, 1, L=inner)
    stock(acc, ("box", .12, .075, .3, ["pack_0", "pack_2", "pack_1"]), -inner / 2, inner / 2, -1, D / 2 - y0, -(D / 2 + y0) + .1, .98 + .015, .4, 2, L=inner)
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
    front, back = D / 2 - y0 + .01, -(D / 2 + y0) + .08
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
        stock(acc, th[li % len(th)], -W / 2 + .06, W / 2 - .06, -1, front, front - (.36 if li == 4 else .2), z + .014, tops[li] - z - .05, 10 + li, L=W)


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
                rbox(acc, (.075, .006, .03), (x, s * (.05 + d + .022), z - .004), C(INK), .004, 1)
                rbox(acc, (.06, .004, .02), (x, s * (.05 + d + .026), z - .004), C("E3E8E4"), .002, 1)
            stock(acc, theme[li % len(theme)], -L / 2 + .06, L / 2 - .06, s, .05 + d, .06 if li == 4 else .05 + d - .2, z + .013, tops[li] - z - .06, 20 + li + (s > 0) * 7, L=L)
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
            n = 9
            for k in range(n):
                yy = -D / 2 + .12 + k * (D - .24) / (n - 1)
                pet_bottle(acc, (ex + e * .075, yy, z + .013), .3, .034, C(["3A120A", "1E7A32", "F28C28"][li % 3]), ["soda_0", "soda_1", "soda_2", "soda_3"][(k + li) % 4], C("D74A3C"), "Anim Fill %d" % (0 if e < 0 else 3), 10)
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


def lineup_sheet(kind, base_y, title_name):
    """Builds the lineup of `kind` at y = base_y and renders the sheet plus a close-up of every tier."""
    roots, prints, tris, total, xs = lineup(kind, .9, base_y)
    ext = max(fd for (_, _, _, fd) in prints)
    x0, x1 = -total / 2 - 1.6, total / 2 + .6
    sheet_floor(math.floor(x0), math.ceil(x1), base_y - ext / 2 - 1.25, base_y + ext / 2 + .75, prints)
    mannequin((-total / 2 - .8, base_y + .1, 0), "Pessoa " + kind)
    for i, (cx, cy, fw, fd) in enumerate(prints):
        tid, name, _, _, h = TIERS[kind][i]
        caption("%s  %s" % (tid, name), (cx, base_y - ext / 2 - .45, .004), .17)
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
    isolate(base_y)
    ext = max(fd for (_, _, _, fd) in prints)
    hmax = max(t[4] for t in TIERS[kind])
    d = Vector((-.32, -1, .78))
    camera((0 - .5, base_y - .3, hmax * .4), d, 40, ortho=total + 3.0)
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
        base_y = 0.0 if kind == "shelf" else -9.0
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


def outline(name, w, d, loc, rot, col):
    acc = Acc(name)
    for s in (-1, 1):
        rbox(acc, (w, .035, .006), (0, s * (d / 2 - .018), .004), C(col), 0, 1)
        rbox(acc, (.035, d, .006), (s * (w / 2 - .018), 0, .004), C(col), 0, 1)
    c = coll("FT conveniencia", coll("Fixture tiers"))
    for o in acc.realize(c):
        o.name = name
        o.location = loc
        o.rotation_euler = (0, 0, math.radians(rot))


def instance(kind, tier, loc, rot, name):
    """Linked copy of a built tier (shares its meshes)."""
    src = bpy.data.objects["%s-%s" % (kind, tier.lower())]
    c = coll("FT conveniencia", coll("Fixture tiers"))
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
            ("produce", 1.0, .75, .95, x0 + .375, y0 + 1.6, 270, "7DB35A"),
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
