"""Build-mode decorations v3 (19 Oct 2026): Lucas's feedback on decor_v2.
    coffee-kiosk     bigger cafe cart with espresso machine, grinder, pastry case, syrups, menu board, stools
    flower-stand     florist corner (2.2 x 1.2 x 2.4) with tiered stands, buckets, pots, pergola top, wrapping counter
    claw-machine     more plush (30), chute door, big joystick/button, LED trim, side art panels
    vending-machine  glass vitrine front with lit shelves, bottles/cans, coils, keypad column, pickup tray
    photo-booth      curtain on its own "Anim Curtain" node (pivot on the rail end, scale local X 1 -> .25 opens it)
    cart-corral, atm, gumball, festoon-pergola: unchanged from v2.
Same material contract as build_interior_kit.py. Unity space (metres, +Y up, customer at -Z).
    blender -b --factory-startup --python build_decor_v3.py -- [--install] [names...]
Outputs go to ArtSource/decor_v2/v3/{fbx,previews,thumbs}; --install copies to Assets (with backups).
"""
import sys, os, json, math, time, shutil, uuid, random
sys.path.insert(0, r"C:\Checkout-mobile\scripts\blender")
sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\decor_v2")
import bpy, bmesh
from mathutils import Vector, Matrix
import build_interior_kit as K
import build_decor_v2 as V2
from build_interior_kit import (Model, box, cyl, lathe, lathe_s, ball, bar, torus, torus_arc, prism, quad, rounded_panel, awning, Local,
                                arc_points, pergola_lights, uv_fit, box_bm, _place, NAVY, GOLD, GOLDL, CREAM, WHITE, TEAL, TEALD, RED, ORANGE,
                                PINK, WOOD, WOODL, WOODD, STEEL, DARK, GREEN, LEAF, LEAFD, BLUE, PURPLE)
from build_decor_v2 import tube, wheel_caster, flower, led_strip, star_pts, CHROME, BRUSH, PLANKS

Q = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\decor_v2"
Q3 = os.path.join(Q, "v3")
K.OUT = os.path.join(Q3, "fbx"); K.THUMBS = os.path.join(Q3, "thumbs"); PRE = os.path.join(Q3, "previews"); TEX2 = os.path.join(Q, "tex")
for d in (K.OUT, K.THUMBS, PRE): os.makedirs(d, exist_ok=True)
ZINC = "T_IK_V3_Zinc"; WOODR = "T_IK_R_Wood"; WOODDK = "T_IK_R_WoodDark"; MARBLE = "T_IK_Marble"; KRAFT = "T_IK_V3_KraftDots"


def load_tex(name):
    """decor_v2/tex first, then Assets. Re-loads an image whose file is missing (the old-FBX import leaves broken images)."""
    fn = name + "_albedo.png"
    p = os.path.join(TEX2, fn)
    if not os.path.exists(p): p = os.path.join(K.TEX, fn)
    if not os.path.exists(p): return None
    img = bpy.data.images.get(fn)
    if img is not None and not os.path.exists(bpy.path.abspath(img.filepath)):
        img.name = "broken_" + fn; img = None
    if img is None: img = bpy.data.images.load(p)
    return img
K.load_tex = load_tex


def realize(m):
    """K.realize + explicit pivots (m.pivots[name] = Unity point) for nodes such as 'Anim Curtain'."""
    sc = bpy.context.scene; objs = []
    pivots = getattr(m, "pivots", {})
    for name, (bm, mats) in m.objects.items():
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.00002)
        me = bpy.data.meshes.new(m.name + "_" + name); bm.to_mesh(me); bm.free()
        for key in mats: me.materials.append(K.material(key))
        ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
        if name != "Body" and me.vertices:
            if name in pivots:
                pivot = K.U(*pivots[name])
            else:
                xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
                pivot = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs) if name.startswith("Anim Sway") else (min(zs) + max(zs)) / 2))
            me.transform(Matrix.Translation(-pivot)); ob.location = pivot
        for p in me.polygons:
            if not p.use_smooth: p.use_smooth = True
        wn = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL"); wn.keep_sharp = True; wn.weight = 100
        objs.append(ob)
    return objs
K.realize = realize

V3 = {}
def model(name):
    def wrap(fn): V3[name] = fn; return fn
    return wrap

# ------------------------------------------------------------------------------------------------- shared bits
def card(m, w, h, center, key, yaw=0, pitch=0, obj="Body", thick=.004):
    """Printed card with 0..1 UVs computed before placing (so it also works on side walls, yaw=+-90)."""
    bm = box_bm((w, h, thick), 0)
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    uv_fit(bm, uvl)
    m.add(_place(bm, center, pitch, yaw), key, obj, uv="none")

def open_box(m, size, center, key, bevel=.02, seg=2, obj="Body"):
    """Bevelled box without its customer-side (-Z) face: a cabinet shell with an opening, bevel ring kept."""
    bm = box_bm(size, bevel, seg); bm.normal_update()
    front = [f for f in bm.faces if f.normal.y > .95]   # Blender +Y = Unity -Z
    bmesh.ops.delete(bm, geom=front, context="FACES")
    m.add(_place(bm, center), key, obj)

def blink_nodes(m, n=3):
    return [m.anim("Anim Blink") for _ in range(n)]

def leds(m, pts, nodes, cols=("E_FFE066", "E_FF6FA8", "E_7BD3F7"), r=.016):
    for i, p in enumerate(pts):
        obj = nodes[i % len(nodes)] if (i % 2 == 0) else "Body"
        ball(m, p, (r * 2, r * 2, r * 1.5), cols[i % len(cols)], 6, 4, obj)

def leaf(m, pos, size, yaw, pitch, key="C_" + LEAF, obj="Body"):
    prism(m, [(-size * .22, 0), (size * .22, 0), (size * .42, size * .5), (0, size), (-size * .42, size * .5)], .003, pos, key, pitch=pitch, yaw=yaw, obj=obj)

def flower_lite(m, top, kind, col, obj="Body", s=1.0):
    L = Local(m, top, obj=obj)
    if kind == "rose":
        ball(L, (0, .03 * s, 0), (.07 * s, .066 * s, .07 * s), col, 8, 5); torus(L, .026 * s, .011 * s, (0, .052 * s, 0), col, seg=8, minor=3)
    elif kind == "tulip":
        lathe(L, [(0, 0), (.018 * s, 0), (.031 * s, .035 * s), (.025 * s, .065 * s), (.011 * s, .078 * s), (0, .074 * s)], (0, 0, 0), col, 7)
    elif kind == "lavender":
        lathe(L, [(0, 0), (.013 * s, 0), (.015 * s, .05 * s), (.009 * s, .09 * s), (0, .105 * s)], (0, 0, 0), col, 6)
    elif kind == "peony":
        ball(L, (0, .035 * s, 0), (.085 * s, .07 * s, .085 * s), col, 8, 6); ball(L, (0, .055 * s, 0), (.05 * s, .04 * s, .05 * s), "C_FFF1E0", 6, 4)
    elif kind == "hydrangea":
        for k in range(5):
            a = k * 1.26; ball(L, (math.cos(a) * .03 * s, .03 * s + (k % 2) * .015 * s, math.sin(a) * .03 * s), (.045 * s, .04 * s, .045 * s), col, 6, 4)
    else:
        flower(L, (0, 0, 0), kind, col, s=s)

def bunch_lite(m, base, kinds, cols, obj, n=5, h=.4, spread=.07, seed=0, s=1.0):
    r = (seed * 7919) % 97
    for k in range(n):
        a = k * 2.399 + r; rad_ = spread * math.sqrt((k + .5) / n); hh = h + ((k * 37 + r) % 5) * .02
        top = (base[0] + math.cos(a) * rad_, base[1] + hh, base[2] + math.sin(a) * rad_)
        bar(m, (base[0] + math.cos(a) * rad_ * .3, base[1], base[2] + math.sin(a) * rad_ * .3), top, .005, "C_" + LEAFD, 4, obj)
        flower_lite(m, top, kinds[k % len(kinds)], cols[k % len(cols)], obj, s)
        if k % 2 == 0:
            leaf(m, (top[0] + .02, base[1] + hh * .55, top[2]), .08, a * 57, -35, obj=obj)

def greenery(m, base, obj, n=4, h=.45, seed=0):
    """Eucalyptus / fern stems: stem + paired leaves."""
    r = (seed * 31) % 23
    for k in range(n):
        a = k * 2.1 + r; top = (base[0] + math.cos(a) * .04, base[1] + h + (k % 2) * .06, base[2] + math.sin(a) * .04)
        bar(m, base, top, .004, "C_" + LEAFD, 4, obj)
        for j in range(4):
            t = .45 + j * .15; p = (base[0] + (top[0] - base[0]) * t, base[1] + (top[1] - base[1]) * t, base[2] + (top[2] - base[2]) * t)
            leaf(m, p, .06, a * 57 + j * 70, -60 + (j % 2) * 120, "C_" + (LEAF if j % 2 else "8FBF6A"), obj)

def bucket(m, c, r=.1, h=.26, key=ZINC, obj="Body"):
    """Galvanised bucket, light: 12-seg lathe, one hoop, wire handle."""
    L = Local(m, c, obj=obj)
    lathe(L, [(0, 0), (r * .8, 0), (r, h - .015), (r + .01, h - .015), (r + .01, h), (0, h)], (0, 0, 0), key, 10)
    if r >= .1: torus(L, r + .003, .005, (0, h * .45, 0), key, seg=10, minor=4)
    for sx in (-1, 1): bar(L, (sx * (r + .008), h - .035, 0), (sx * (r + .008), h + .015, 0), .004, key, 4)
    torus_arc(L, r + .008, .005, (0, h + .015, 0), "C_" + DARK, 0, 180, roll=90, seg=8, minor=4)

def pot(m, c, r=.08, h=.14, key="T_IK_Terracotta", obj="Body", soil=True):
    L = Local(m, c, obj=obj)
    lathe(L, [(0, 0), (r * .72, 0), (r * .96, h - .03), (r + .008, h - .03), (r + .008, h), (r * .9, h), (r * .72, .02), (0, .02)], (0, 0, 0), key, 10)
    if soil: cyl(L, r * .88, .012, (0, h - .03, 0), "C_5A3A1E", 10)

def potted_plant(m, c, s=1.0, kind="bush", obj="Body", seed=0):
    pot(m, c, .085 * s, .15 * s)
    top = (c[0], c[1] + .15 * s, c[2])
    if kind == "bush":
        ball(m, (top[0], top[1] + .11 * s, top[2]), (.3 * s, .26 * s, .3 * s), "T_IK_R_Hedge", 10, 6, obj)
        for k in range(4):
            a = k * 1.5 + seed; leaf(m, (top[0] + math.cos(a) * .1 * s, top[1] + .18 * s, top[2] + math.sin(a) * .1 * s), .09 * s, a * 57, -40 + (k % 2) * 20, obj=obj)
    elif kind == "fern":
        for k in range(7):
            a = k * .9 + seed; leaf(m, (top[0] + math.cos(a) * .03, top[1], top[2] + math.sin(a) * .03), .22 * s, a * 57, -55, "C_" + (LEAF if k % 2 else "8FBF6A"), obj)
    elif kind == "succulent":
        for layer, (rr, n, yy, sz) in enumerate(((.045, 6, 0, .07), (.025, 5, .02, .055), (.01, 4, .04, .04))):
            for k in range(n):
                a = k * 2 * math.pi / n + layer * .5
                prism(m, [(-sz * .3, 0), (sz * .3, 0), (sz * .35, sz * .6), (0, sz), (-sz * .35, sz * .6)], .006, (top[0] + math.cos(a) * rr * s, top[1] + yy * s, top[2] + math.sin(a) * rr * s),
                      "C_" + ("7FB069" if layer else "5C8F4F"), pitch=-70 + layer * 15, yaw=math.degrees(a) + 90, obj=obj)

def hanging_basket(m, c, obj="Body", seed=0):
    """Wicker half-bowl on three chains from c (the hook), trailing greenery, flowers on top."""
    x, y, z = c; by = y - .32
    lathe(m, [(0, 0), (.06, 0), (.12, .08), (.14, .13), (.145, .14), (0, .14)], (x, by, z), "T_IK_Wicker", 10, cap=True)
    torus(m, .145, .008, (x, by + .14, z), "C_8A5A34", seg=10, minor=4)
    for k in range(3):
        a = k * 2.094 + .5; bar(m, (x, y, z), (x + math.cos(a) * .13, by + .13, z + math.sin(a) * .13), .004, "C_" + DARK, 4)
    ball(m, (x, by + .18, z), (.3, .14, .3), "T_IK_R_Hedge", 10, 5)
    for k in range(7):
        a = k * .9 + seed; ex, ez = math.cos(a) * .14, math.sin(a) * .14; drop = .16 + (k % 3) * .05
        bar(m, (x + ex, by + .12, z + ez), (x + ex * 1.35, by + .12 - drop, z + ez * 1.35), .004, "C_" + LEAFD, 4)
        for j in range(4):
            t = (j + .5) / 4; leaf(m, (x + ex * (1 + .35 * t), by + .12 - drop * t, z + ez * (1 + .35 * t)), .07, a * 57 + (j % 2) * 180, -110 + (j % 2) * 40, "C_" + (LEAF if j % 2 else "8FBF6A"))
    for k in range(3):
        a = k * 2.1 + seed; flower_lite(m, (x + math.cos(a) * .08, by + .22, z + math.sin(a) * .08), "daisy" if k % 2 else "rose", ("C_F4EFE4", "C_E86A9E", "C_F2C23F")[k], s=.85)

def cone_bouquet(m, c, kind, col, pitch=0, yaw=0, obj="Body", paper=KRAFT):
    L = Local(m, c, pitch=pitch, yaw=yaw, obj=obj)
    lathe(L, [(0, 0), (.02, 0), (.085, .3), (.095, .32), (.08, .32), (.015, .02)], (0, 0, 0), paper, 10)
    torus(L, .05, .007, (0, .2, 0), "C_" + GOLD, seg=10, minor=4)
    for k in range(4):
        a = k * 1.6; flower_lite(L, (math.cos(a) * .04, .3 + (k % 2) * .025, math.sin(a) * .04), kind, col if k != 3 else "C_F4EFE4", s=.95)
    leaf(L, (.05, .28, -.03), .09, 20, -50); leaf(L, (-.05, .27, .02), .09, 200, -50)

def plush_lite(m, c, kind="bear", col="C_D9A066", obj="Body", s=1.0, yaw=0, pitch=0, roll=0):
    """Low-poly plush (about 400 tris) for the claw pile."""
    L = Local(m, c, yaw=yaw, pitch=pitch, roll=roll, obj=obj); ink = "C_" + DARK; cream = "C_F6E7C8"
    ball(L, (0, .07 * s, 0), (.17 * s, .14 * s, .14 * s), col, 8, 5)
    ball(L, (0, .17 * s, -.01 * s), (.13 * s, .12 * s, .12 * s), col, 8, 5)
    for sx in (-1, 1):
        ball(L, (sx * .095 * s, .07 * s, -.03 * s), (.055 * s, .05 * s, .07 * s), col, 6, 4)
        ball(L, (sx * .06 * s, .015 * s, -.07 * s), (.065 * s, .045 * s, .08 * s), col, 6, 4)
        ball(L, (sx * .032 * s, .185 * s, -.062 * s), (.014 * s, .016 * s, .01 * s), ink, 5, 3)
    if kind == "bear":
        for sx in (-1, 1): ball(L, (sx * .05 * s, .235 * s, 0), (.045 * s, .045 * s, .03 * s), col, 6, 4)
        ball(L, (0, .155 * s, -.06 * s), (.055 * s, .04 * s, .035 * s), cream, 6, 4); ball(L, (0, .165 * s, -.08 * s), (.018 * s, .014 * s, .012 * s), ink, 5, 3)
    elif kind == "bunny":
        for sx in (-1, 1):
            ball(L, (sx * .035 * s, .29 * s, .01 * s), (.04 * s, .15 * s, .03 * s), col, 6, 4); ball(L, (sx * .035 * s, .29 * s, -.004 * s), (.018 * s, .1 * s, .02 * s), "C_F2B8C6", 5, 3)
        ball(L, (0, .15 * s, -.06 * s), (.018 * s, .014 * s, .012 * s), "C_F28CA8", 5, 3)
    elif kind == "cat":
        for sx in (-1, 1): prism(L, [(-.025 * s, 0), (.025 * s, 0), (0, .05 * s)], .02 * s, (sx * .045 * s, .215 * s, 0), col)
        ball(L, (0, .15 * s, -.06 * s), (.018 * s, .013 * s, .012 * s), "C_F28CA8", 5, 3)
        bar(L, (.07 * s, .03 * s, .05 * s), (.13 * s, .09 * s, .08 * s), .013 * s, col, 5)
    elif kind == "duck":
        prism(L, [(-.03 * s, .16 * s), (.03 * s, .16 * s), (0, .13 * s)], .045 * s, (0, 0, -.08 * s), "C_" + ORANGE)
        ball(L, (0, .02 * s, -.02 * s), (.18 * s, .05 * s, .15 * s), "C_" + ORANGE, 8, 4)
    elif kind == "pig":
        ball(L, (0, .155 * s, -.065 * s), (.05 * s, .035 * s, .03 * s), "C_F2A0B8", 6, 4)
        for sx in (-1, 1): prism(L, [(-.022 * s, 0), (.022 * s, 0), (0, .04 * s)], .015 * s, (sx * .045 * s, .22 * s, 0), col)
    elif kind == "frog":
        for sx in (-1, 1):
            ball(L, (sx * .04 * s, .225 * s, -.02 * s), (.045 * s, .045 * s, .045 * s), col, 6, 4); ball(L, (sx * .04 * s, .23 * s, -.04 * s), (.02 * s, .02 * s, .012 * s), ink, 5, 3)
        ball(L, (0, .15 * s, -.06 * s), (.06 * s, .02 * s, .02 * s), "C_F28CA8", 6, 3)
    elif kind == "panda":
        for sx in (-1, 1):
            ball(L, (sx * .05 * s, .235 * s, 0), (.045 * s, .045 * s, .03 * s), ink, 6, 4); ball(L, (sx * .032 * s, .185 * s, -.055 * s), (.03 * s, .036 * s, .015 * s), ink, 6, 4)
        ball(L, (0, .155 * s, -.065 * s), (.02 * s, .015 * s, .012 * s), ink, 5, 3)

# ------------------------------------------------------------------------------------------------- unchanged (v2)
V3["cart-corral"] = V2.V2["cart-corral"]
V3["atm"] = V2.V2["atm"]
V3["gumball"] = V2.V2["gumball"]
V3["festoon-pergola"] = V2.V2["festoon-pergola"]

# ------------------------------------------------------------------------------------------------- claw machine
@model("claw-machine")
def claw_machine(m):
    pink = "T_IK_V2_PaintPink"; navy = "T_IK_V2_PaintNavy"; nodes = blink_nodes(m, 3)
    box(m, (.86, .1, .86), (0, .05, 0), "C_" + DARK, .02)
    box(m, (.82, .86, .82), (0, .53, 0), pink, .04, 3)
    for sx in (-1, 1):
        for sz in (-1, 1): bar(m, (sx * .4, .1, sz * .4), (sx * .4, .95, sz * .4), .016, CHROME, 8)
    box(m, (.84, .03, .84), (0, .95, 0), CHROME, .01, 1)
    # side art panels (both sides) + front lower panel
    for sx in (-1, 1):
        rounded_panel(m, .62, .6, (sx * .415, .52, 0), "C_" + GOLD, .012, .06, yaw=90)
        card(m, .56, .54, (sx * .425, .52, 0), "T_IK_V3_ClawArt", yaw=90)
    # coin door (left) with lit slot, chute door (right): chrome frame, dark recess, flap with window + handle, star pictogram
    box(m, (.16, .22, .02), (-.27, .6, -.415), CHROME, .006, 1); box(m, (.03, .06, .01), (-.27, .64, -.428), "E_7CE08A", .002, 1)
    cyl(m, .022, .01, (-.27, .52, -.425), "C_" + DARK, 10, pitch=-90); cyl(m, .012, .01, (-.27, .52, -.43), CHROME, 8, pitch=-90)
    box(m, (.34, .34, .03), (.17, .44, -.415), CHROME, .008, 1); box(m, (.3, .3, .02), (.17, .44, -.428), "C_" + DARK, .006, 1)
    box(m, (.26, .24, .015), (.17, .42, -.436), navy, .006, 1, pitch=6); box(m, (.2, .1, .012), (.17, .47, -.446), "G_Glass", .003, 1, pitch=6)
    bar(m, (.07, .33, -.455), (.27, .33, -.455), .012, CHROME, 8)
    prism(m, star_pts(.03, .013), .012, (.17, .64, -.42), "E_FFE066"); prism(m, [(-.04, -.012), (.04, -.012), (.04, .012), (-.04, .012)], .01, (.17, .6, -.42), "C_" + GOLD)
    # control deck: big joystick (red ball top) and two big buttons on a navy panel
    box(m, (.76, .1, .26), (0, .99, -.36), navy, .02, 2, pitch=-18)
    cyl(m, .05, .022, (-.16, 1.015, -.4), CHROME, 14, .004, pitch=-18); cyl(m, .04, .03, (-.16, 1.02, -.4), "C_" + DARK, 12, .006, pitch=-18)
    bar(m, (-.16, 1.04, -.405), (-.16, 1.15, -.44), .014, CHROME, 8); ball(m, (-.16, 1.17, -.445), (.09, .09, .09), "C_" + RED, 12, 8)
    for i, (col, r) in enumerate((("C_F2B03D", .06), ("C_" + GREEN, .045))):
        x = .08 + i * .2
        cyl(m, r + .014, .012, (x, 1.012, -.4), CHROME, 16, pitch=-18); cyl(m, r, .018, (x, 1.016, -.4), col, 16, .005, pitch=-18)
        ball(m, (x, 1.03, -.405), (r * 1.9, r * .9, r * 1.9), col, 12, 6)
    # case: gold posts, glass on three sides, painted back, cream floor, ceiling light
    for sx in (-1, 1):
        for sz in (-1, 1): box(m, (.05, 1.0, .05), (sx * .395, 1.47, sz * .395), "C_" + GOLD, .012, 2)
    box(m, (.76, .96, .012), (0, 1.47, -.39), "G_Glass", .002, 1)
    for sx in (-1, 1): box(m, (.012, .96, .76), (sx * .39, 1.47, 0), "G_Glass", .002, 1)
    box(m, (.76, .96, .03), (0, 1.47, .385), pink, .006, 1)
    box(m, (.78, .04, .78), (0, 1.0, 0), "C_" + CREAM, .01, 1); box(m, (.5, .03, .02), (0, 1.94, -.3), "E_FFF7D8", .006, 1)
    # LED trim: vertical runs on the two front posts and under the marquee
    for sx in (-1, 1):
        leds(m, [(sx * .395, 1.05 + k * .09, -.42) for k in range(10)], nodes, r=.012)
        leds(m, [(sx * .42, 1.05 + k * .09, -.395) for k in range(10)], nodes, r=.012)
    # plush pile: 30 toys, two layers, natural lean
    kinds = ("bear", "bunny", "cat", "duck", "pig", "frog", "panda")
    cols = ("C_D9A066", "C_F4EFE4", "C_8D8D93", "C_F2C23F", "C_F2A0B8", "C_7FBF6A", "C_F4EFE4", "C_6F4A2E", "C_B9A7DE", "C_7BD3F7", "C_E86A9E", "C_F28C38")
    rng = random.Random(19)
    k = 0
    for i in range(5):
        for j in range(4):
            x = -.27 + i * .135 + rng.uniform(-.03, .03); z = -.2 + j * .14 + rng.uniform(-.03, .03)
            plush_lite(m, (x, 1.02, z), kinds[k % 7], cols[(k * 5) % 12], s=.82, yaw=rng.uniform(-50, 50), pitch=rng.uniform(-12, 12), roll=rng.uniform(-12, 12)); k += 1
    for i in range(4):
        for j in range(3):
            if (i + j) % 2 and k >= 30: continue
            x = -.2 + i * .135 + rng.uniform(-.03, .03); z = -.12 + j * .14 + rng.uniform(-.03, .03)
            plush_lite(m, (x, 1.15, z), kinds[(k + 3) % 7], cols[(k * 7 + 1) % 12], s=.78, yaw=rng.uniform(-90, 90), pitch=rng.uniform(-35, 35), roll=rng.uniform(-35, 35)); k += 1
    # gantry + claw (Anim Spin)
    for sz in (-.28, .28): bar(m, (-.36, 1.9, sz), (.36, 1.9, sz), .012, CHROME, 8)
    bar(m, (.1, 1.9, -.28), (.1, 1.9, .28), .012, CHROME, 8); box(m, (.14, .07, .14), (.1, 1.88, .02), "C_" + DARK, .012, 2)
    bar(m, (.1, 1.85, .02), (.1, 1.66, .02), .005, "C_" + DARK, 5)
    spin = m.anim("Anim Spin")
    cyl(m, .04, .05, (.1, 1.62, .02), CHROME, 12, .006, obj=spin); cyl(m, .02, .03, (.1, 1.66, .02), "C_" + DARK, 8, obj=spin)
    for q in range(3):
        a = math.radians(q * 120 + 30); dx, dz = math.cos(a), math.sin(a)
        tube(m, [(.1 + dx * .03, 1.63, .02 + dz * .03), (.1 + dx * .085, 1.56, .02 + dz * .085), (.1 + dx * .07, 1.49, .02 + dz * .07), (.1 + dx * .03, 1.45, .02 + dz * .03)], .007, CHROME, 6, spin)
    # marquee: pink crown with star pictograms, LED rows all round
    box(m, (.9, .2, .9), (0, 2.08, 0), pink, .04, 3)
    for yaw, z in ((0, -.46), (180, .46)):
        rounded_panel(m, .44, .16, (0, 2.08, z), "C_" + NAVY, .02, .04, yaw=yaw)
        prism(m, star_pts(.065, .03), .015, (0, 2.08, z - .018 if z < 0 else z + .018), "E_FFE066", yaw=yaw)
        for sx in (-1, 1): prism(m, star_pts(.035, .016), .015, (sx * .15, 2.08, z - .018 if z < 0 else z + .018), "E_FF6FA8", yaw=yaw)
    for sx in (-1, 1):
        rounded_panel(m, .44, .16, (sx * .46, 2.08, 0), "C_" + NAVY, .02, .04, yaw=90)
        prism(m, star_pts(.05, .022), .015, (sx * .48, 2.08, 0), "E_FFE066", yaw=90)
    leds(m, [(-.38 + k * .069, 2.19, -.45) for k in range(12)] + [(-.38 + k * .069, 2.19, .45) for k in range(12)], nodes, r=.02)
    leds(m, [(-.45, 2.19, -.36 + k * .072) for k in range(11)] + [(.45, 2.19, -.36 + k * .072) for k in range(11)], nodes, r=.02)
    box(m, (.94, .04, .94), (0, 2.2, 0), "C_" + GOLD, .012, 2)

# ------------------------------------------------------------------------------------------------- vending machine
@model("vending-machine")
def vending_machine(m):
    red = "T_IK_V2_PaintRed"; navy = "T_IK_V2_PaintNavy"; nodes = blink_nodes(m, 2)
    box(m, (.88, .1, .78), (0, .05, 0), "C_" + DARK, .02)
    # cabinet shell open at the front; front plates (header, footer, left pillar, right column) sit 5 mm inside the bevel ring
    open_box(m, (.9, 1.8, .8), (0, 1.0, .02), red, .03, 3)
    box(m, (.84, .25, .04), (0, 1.745, -.355), red, .006, 1)
    box(m, (.84, .39, .04), (0, .325, -.355), red, .006, 1)
    box(m, (.06, 1.1, .04), (-.39, 1.07, -.355), red, .006, 1)
    box(m, (.3, 1.1, .04), (.27, 1.07, -.355), red, .006, 1)
    for y in (.52, 1.62): box(m, (.84, .03, .02), (0, y, -.385), "C_" + GOLD, .004, 1)
    box(m, (.86, .06, .76), (0, 1.9, .02), "C_" + DARK, .012, 2)
    # vitrine cavity x -.36..+.12, y .52..1.62: cream walls, lit ceiling, 6 shelves with lit front edges
    X0, X1, Y0, Y1 = -.36, .12, .52, 1.62; xc = (X0 + X1) / 2; w = X1 - X0
    box(m, (w, Y1 - Y0, .02), (xc, (Y0 + Y1) / 2, .3), "C_F7F3EA", .004, 1)
    for x in (X0, X1): box(m, (.02, Y1 - Y0, .66), (x, (Y0 + Y1) / 2, -.03), "C_F7F3EA", .004, 1)
    box(m, (w, .02, .66), (xc, Y1, -.03), "C_F7F3EA", .004, 1); box(m, (w - .08, .012, .5), (xc, Y1 - .012, -.05), "E_FFF4DC", .003, 1)
    box(m, (w, .02, .66), (xc, Y0, -.03), "C_F7F3EA", .004, 1)
    cols = ("C_2F1B12", "C_F28C38", "C_5DA637", "C_3E8FD6", "C_F2C23F", "C_D7343A", "C_8E6CCF", "C_1F9A8E")
    for sh in range(6):
        y = Y0 + .02 + sh * .18
        box(m, (w - .03, .014, .36), (xc, y, -.14), "C_DDE3E6", .003, 1)
        box(m, (w - .03, .022, .01), (xc, y + .004, -.325), "E_FFF1C8", .002, 1)
        for i in range(5):
            x = X0 + .05 + i * .095; col = cols[(i * 3 + sh) % 8]
            if sh < 3:
                lathe(m, [(0, 0), (.026, 0), (.03, .02), (.03, .1), (.019, .125), (.015, .15), (.016, .158), (0, .158)], (x, y + .008, -.2), col, 8)
                cyl(m, .016, .014, (x, y + .158, -.2), "C_" + DARK if i % 2 else "C_F4EFE4", 8)
                lathe(m, [(.031, .035), (.031, .09)], (x, y + .008, -.2), "C_F4EFE4" if i % 3 else "C_" + GOLDL, 8, cap=False)   # label band
            else:
                cyl(m, .028, .11, (x, y + .008, -.2), col, 10, .004); cyl(m, .025, .006, (x, y + .118, -.2), CHROME, 10)
                lathe(m, [(.029, .03), (.029, .08)], (x, y + .008, -.2), "C_F4EFE4" if i % 2 else "C_" + DARK, 10, cap=False)
            for q in range(2):   # coil in front of each product (rings with their axis towards the customer)
                torus(m, .03, .004, (x, y + .04, -.27 - q * .04), "C_B9C2C8", seg=8, minor=3, pitch=90)
    # glass pane + chrome frame
    box(m, (w + .06, Y1 - Y0 + .06, .012), (xc, (Y0 + Y1) / 2, -.395), "G_Glass", .002, 1)
    for x in (X0 - .03, X1 + .03): bar(m, (x, Y0 - .03, -.4), (x, Y1 + .03, -.4), .012, CHROME, 8)
    for y in (Y0 - .03, Y1 + .03): bar(m, (X0 - .03, y, -.4), (X1 + .03, y, -.4), .012, CHROME, 8)
    # right column: screen, keypad, coin slot, bill acceptor, coin return
    box(m, (.22, .1, .02), (.285, 1.48, -.395), "C_" + DARK, .006, 1); box(m, (.18, .06, .01), (.285, 1.48, -.405), "E_7BD3F7", .003, 1)
    rounded_panel(m, .24, .3, (.285, 1.24, -.395), navy, .012, .03)
    for i in range(3):
        for j in range(4): box(m, (.045, .04, .014), (.235 + i * .05, 1.33 - j * .058, -.405), "C_F4EFE4", .005, 1)
    box(m, (.08, .025, .012), (.285, 1.02, -.4), CHROME, .003, 1); box(m, (.012, .04, .012), (.285, 1.02, -.405), "C_" + DARK, .002, 1)
    box(m, (.14, .05, .014), (.285, .92, -.4), CHROME, .004, 1); box(m, (.1, .008, .016), (.285, .92, -.406), "C_" + DARK, .001, 1)
    lathe(m, [(0, 0), (.035, 0), (.04, .03), (.04, .06), (0, .06)], (.285, .74, -.4), "C_" + DARK, 10, pitch=-90)
    ball(m, (.37, 1.48, -.405), (.025, .025, .018), "E_7CE08A", 8, 5, nodes[0])
    # pickup tray: dark recess, navy flap with chrome handle, chrome lip
    box(m, (.52, .26, .06), (xc, .3, -.39), "C_" + DARK, .01, 2)
    box(m, (.46, .19, .016), (xc, .29, -.41), navy, .008, 2, pitch=-10); bar(m, (xc - .18, .36, -.43), (xc + .18, .36, -.43), .01, CHROME, 8)
    box(m, (.52, .03, .05), (xc, .17, -.395), CHROME, .006, 1)
    # lit top sign with bottle / droplet / can pictograms
    box(m, (.84, .2, .04), (0, 1.75, -.395), "E_FFF1C8", .01, 2)
    lathe(m, [(0, 0), (.035, 0), (.04, .1), (.02, .14), (.018, .17), (.02, .18), (0, .18)], (-.22, 1.66, -.42), "C_" + TEAL, 10)
    prism(m, [(0, -.06), (.035, 0), (0, .06), (-.035, 0)], .012, (0, 1.75, -.42), "C_" + BLUE); cyl(m, .035, .012, (0, 1.75, -.42), "C_" + BLUE, 12, pitch=-90)
    cyl(m, .035, .12, (.22, 1.69, -.42), "C_" + RED, 12, .004); cyl(m, .031, .006, (.22, 1.81, -.42), CHROME, 12)
    box(m, (.4, .3, .012), (.0, 1.15, .42), "C_F4EFE4", .004, 1)   # back service panel

# ------------------------------------------------------------------------------------------------- coffee kiosk
def espresso_machine(L):
    box(L, (.64, .36, .44), (0, .18, 0), CHROME, .02, 3); box(L, (.66, .06, .46), (0, .39, 0), "C_" + DARK, .012, 2)
    box(L, (.62, .12, .1), (0, .3, -.3), "C_" + RED, .02, 2); box(L, (.6, .18, .02), (0, .12, -.23), "C_" + DARK, .006, 1)
    box(L, (.6, .02, .16), (0, .01, -.27), "C_" + DARK, .004, 1); box(L, (.54, .008, .13), (0, .025, -.27), CHROME, .002, 1)   # drip tray + grille
    for x in (-.18, .18):
        cyl(L, .048, .05, (x, .15, -.26), CHROME, 14, .006)
        cyl(L, .042, .02, (x, .13, -.26), "C_" + DARK, 12, .004); bar(L, (x, .14, -.26), (x, .11, -.5), .013, "C_" + DARK, 8); ball(L, (x, .11, -.5), (.032, .032, .032), "C_" + DARK, 8, 5)
        lathe(L, [(0, 0), (.026, 0), (.032, .05), (.03, .06), (0, .06)], (x, .035, -.26), "C_F4EFE4", 8)
    for sx in (-1, 1): bar(L, (sx * .3, .28, -.12), (sx * .4, .12, -.32), .008, CHROME, 6); ball(L, (sx * .4, .12, -.32), (.02, .02, .02), "C_" + DARK, 6, 4)
    cyl(L, .03, .01, (0, .3, -.355), "C_F4EFE4", 12, pitch=-90); bar(L, (0, .3, -.362), (.018, .315, -.362), .003, "C_" + RED, 4)
    for x in (-.1, .1): cyl(L, .024, .014, (x, .3, -.355), "C_" + DARK, 10, pitch=-90)
    for i in range(8): lathe(L, [(0, 0), (.026, 0), (.032, .05), (.03, .06), (0, .06)], (-.24 + (i % 4) * .14, .42, .08 - (i // 4) * .12), "C_F4EFE4" if i % 2 else "C_F2C23F", 8)

def grinder(L):
    cyl(L, .07, .3, (0, 0, 0), "C_" + DARK, 14, .012)
    lathe(L, [(0, 0), (.05, 0), (.085, .12), (.08, .13), (0, .13)], (0, .3, 0), "G_Glass", 12); ball(L, (0, .34, 0), (.13, .07, .13), "C_5A3521", 8, 5)
    cyl(L, .05, .02, (0, .43, 0), "C_" + DARK, 12)
    box(L, (.08, .05, .1), (0, .14, -.1), CHROME, .006, 1); cyl(L, .012, .006, (.055, .22, -.06), "C_" + RED, 8, pitch=-90)

def pastry_case(L, w=.8):
    box(L, (w, .05, .5), (0, .025, 0), WOODDK, .01, 1)
    box(L, (w - .04, .36, .46), (0, .25, 0), "G_Glass", .015, 1)
    box(L, (w, .025, .5), (0, .44, 0), WOODDK, .008, 1)
    for sx in (-1, 1): bar(L, (sx * (w / 2 - .02), .05, -.22), (sx * (w / 2 - .02), .43, -.22), .008, "C_" + GOLD, 6)
    for r, y in enumerate((.07, .25)):
        box(L, (w - .08, .01, .4), (0, y, 0), "C_" + STEEL, .003, 1)
        for i in range(4):
            x = -w / 2 + .12 + i * (w - .24) / 3; kind = (i + r) % 3
            if kind == 0: K.croissant(L, (x, y + .03, -.02), 1.0, 20 * i + 30 * r)
            elif kind == 1:
                prism(L, [(-.06, 0), (.06, 0), (.0, .13)], .07, (x, y + .04, 0), ("C_F4A6C1", "C_6B3E26", "C_F2E3C6")[(i + r) % 3], pitch=90, yaw=20 * i)
                ball(L, (x, y + .08, 0), (.03, .02, .03), "C_D7343A", 6, 4)
            else:
                for q in range(3):
                    cyl(L, .032, .012, (x - .03 + q * .03, y + .008 + q * .012, (q % 2) * .04 - .02), "C_D9A066", 9)
                    for c in range(3): ball(L, (x - .03 + q * .03 + math.cos(c * 2.1) * .015, y + .022 + q * .012, (q % 2) * .04 - .02 + math.sin(c * 2.1) * .015), (.01, .006, .01), "C_5A3521", 5, 3)
            if r == 1 and i == 3:
                lathe(L, [(0, 0), (.03, 0), (.04, .05), (.03, .05), (0, .05)], (x, y + .012, .1), "C_D9A066", 8); ball(L, (x, y + .06, .1), (.08, .05, .08), "C_B5703A", 8, 4)

@model("coffee-kiosk")
def coffee_kiosk(m):
    wood = PLANKS; dark = WOODDK; W, D = 2.0, .9; nodes = blink_nodes(m, 2)
    box(m, (W, .8, D), (0, .5, 0), wood, .02, 2)
    for y in (.14, .86): box(m, (W + .04, .05, D + .04), (0, y, 0), dark, .012, 1)
    for x in (-W / 2, W / 2): box(m, (.06, .84, D + .04), (x, .5, 0), dark, .012, 1)
    for x in (-.5, .5): box(m, (.05, .7, .03), (x, .5, -D / 2 - .01), dark, .008, 1)
    box(m, (W + .1, .05, D + .1), (0, .92, 0), MARBLE, .012, 2)
    # front sign (cup pictogram card on a gold board)
    rounded_panel(m, .86, .4, (0, .5, -D / 2 - .025), "C_" + GOLD, .02, .06); card(m, .8, .36, (0, .5, -D / 2 - .04), "T_IK_V3_CupSign")
    # bar ledge for the stools, on two timber brackets
    box(m, (W + .1, .04, .34), (0, .9, -D / 2 - .14), dark, .01, 2)
    for x in (-.7, .7): prism(m, [(0, 0), (.22, .2), (0, .2)], .05, (x, .68, -D / 2), dark, pitch=0, yaw=90)
    # wheels (rear) + front legs
    for sx in (-1, 1):
        torus(m, .22, .03, (sx * (W / 2 + .05), .25, .2), dark, roll=90, seg=18, minor=6)
        for i in range(6):
            a = math.radians(i * 60); bar(m, (sx * (W / 2 + .05), .25, .2), (sx * (W / 2 + .05), .25 + math.cos(a) * .2, .2 + math.sin(a) * .2), .012, dark, 5)
        cyl(m, .045, .05, (sx * (W / 2 + .05) - .025, .25, .2), "C_" + DARK, 10, .01, roll=90)
        bar(m, (sx * .8, .18, -.3), (sx * .8, 0, -.3), .02, dark, 8)
    bar(m, (-(W / 2 + .05), .25, .2), (W / 2 + .05, .25, .2), .018, "C_" + DARK, 8)
    # counter top: espresso machine, grinder, cup stacks, syrups, pastry case, napkins, sugar jar, small plant
    espresso_machine(Local(m, (-.6, .945, .12)))
    grinder(Local(m, (-.14, .945, .22)))
    for i in range(5): lathe(m, [(0, 0), (.033, 0), (.043, .09), (.038, .1), (0, .1)], (0, .945 + i * .024, -.25), "C_F4EFE4", 8)
    for i in range(4): lathe(m, [(0, 0), (.033, 0), (.043, .1), (.038, .11), (0, .11)], (.1, .945 + i * .026, -.32), KRAFT, 8)
    for i, col in enumerate(("C_C8781E", "C_B9342C", "C_5A9D33", "C_5A3521")):
        x = .02 + i * .085
        lathe(m, [(0, 0), (.028, 0), (.03, .13), (.017, .16), (.014, .22), (0, .22)], (x, .945, .3), col, 8)
        lathe(m, [(.029, .04), (.029, .1)], (x, .945, .3), "C_F4EFE4", 8, cap=False)
        cyl(m, .01, .04, (x, 1.165, .3), CHROME, 8); bar(m, (x, 1.2, .3), (x + .03, 1.2, .28), .005, CHROME, 5)
    pastry_case(Local(m, (.58, .945, -.02)))
    box(m, (.1, .09, .08), (-.3, .99, -.32), CHROME, .006, 1); box(m, (.08, .07, .05), (-.3, 1.0, -.32), "C_F4EFE4", .003, 1)
    lathe(m, [(0, 0), (.035, 0), (.04, .07), (.03, .085), (0, .085)], (-.18, .945, -.32), "G_Glass", 8); cyl(m, .03, .05, (-.18, .95, -.32), "C_F4EFE4", 8)
    potted_plant(m, (.92, .945, .3), .55, "succulent")
    # back posts + beam, menu board, awning, bulb string
    for x in (-.95, .95): box(m, (.07, 1.45, .07), (x, 1.65, .4), dark, .012, 2)
    box(m, (W + .04, .07, .07), (0, 2.35, .4), dark, .012, 2)
    for x in (-.95, .95): bar(m, (x, 2.36, .38), (x, 2.1, -.56), .02, dark, 6)   # sloped rafters under the awning
    # menu board (drink pictograms only) as a roof sign on the back beam, so the awning never hides it
    for x in (-.34, .34): box(m, (.05, .2, .05), (x, 2.45, .4), dark, .008, 1)
    rounded_panel(m, .9, .66, (0, 2.8, .4), "C_" + GOLD, .04, .06); box(m, (.84, .6, .03), (0, 2.8, .4), dark, .006, 1); card(m, .78, .54, (0, 2.8, .378), "T_IK_V3_MenuDrinks")
    # small tabletop chalk easel at the right end of the counter
    L = Local(m, (.95, .945, -.37), yaw=-20)
    for sx in (-1, 1): bar(L, (sx * .07, 0, .03), (sx * .05, .22, -.02), .005, dark, 4)
    box(L, (.16, .2, .012), (0, .12, -.02), dark, .003, 1, pitch=-12); card(L, .14, .18, (0, .12, -.028), "T_IK_V3_MenuDrinks", pitch=-12)
    awning(m, W + .2, 1.0, 2.25, -.56, "S_D98E2B", 16)
    pergola_lights(m, (-1.02, 2.0, -.5), (1.02, 2.0, -.5), .06, 10)
    pergola_lights(m, (-.95, 2.3, .38), (.95, 2.3, .38), .06, 8)
    leds(m, [(-.306, 1.896, -.5), (.306, 1.896, -.5)], nodes, ("E_FFE6A8",), r=.03)
    # two stools in front
    for sx in (-1, 1):
        L = Local(m, (sx * .55, 0, -.76))
        lathe(L, [(0, 0), (.15, 0), (.165, .02), (.15, .05), (0, .05)], (0, .66, 0), WOODR, 12)
        for dx in (-1, 1):
            for dz in (-1, 1): bar(L, (dx * .1, .66, dz * .1), (dx * .15, 0, dz * .15), .012, "C_" + DARK, 6)
        torus(L, .13, .007, (0, .22, 0), "C_" + DARK, seg=12, minor=4)

# ------------------------------------------------------------------------------------------------- flower stand (florist corner)
@model("flower-stand")
def flower_stand(m):
    dark = WOODDK; planks = PLANKS; W, D = 2.2, 1.2; rng = random.Random(5)
    # pergola top: 4 posts, beams, slats, pink scalloped valance on the front beam, bulb string, hanging baskets
    for sx in (-1, 1):
        for sz in (-1, 1): box(m, (.08, 2.3, .08), (sx * 1.06, 1.15, sz * .56), dark, .01, 2)
    for sz in (-1, 1): box(m, (W + .04, .09, .07), (0, 2.33, sz * .56), dark, .01, 1)
    for i in range(5): box(m, (.04, .07, D), (-.9 + i * .45, 2.4, 0), dark, .006, 1)
    box(m, (W + .06, .1, .02), (0, 2.24, -.6), "S_E86A9E", .004, 1); K.scallops(m, W + .06, (0, 2.19, -.6), "S_E86A9E", .07)
    pergola_lights(m, (-1.06, 2.14, -.62), (1.06, 2.14, -.62), .07, 10)
    for i, x in enumerate((-.72, 0, .72)): hanging_basket(m, (x, 2.36, -.1 + (i % 2) * .22), seed=i)
    # rear tiered stand: three solid plank tiers across the back
    tiers = ((.3, .16, .2), (.6, .36, .2), (.9, .55, .18))
    for h, zc, dp in tiers:
        box(m, (1.8, h, dp), (0, h / 2, zc), planks, .01, 1); box(m, (1.82, .04, dp + .02), (0, h - .02, zc), dark, .006, 1)
    def filler(base, obj, s=1.0):
        ball(m, (base[0], base[1] + .05 * s, base[2]), (.21 * s, .11 * s, .21 * s), "T_IK_R_Hedge", 8, 5, obj)
        for k in range(3):
            a = k * 2.1 + base[0] * 7; leaf(m, (base[0] + math.cos(a) * .09 * s, base[1] + .06 * s, base[2] + math.sin(a) * .09 * s), .09 * s, a * 57, -75, "C_" + (LEAF if k % 2 else "8FBF6A"), obj)
    # tier 1: roses, tulips, peonies ... (6 buckets); tier 2: lilies, lavender, hydrangea, daisies (6); tier 3: sunflowers + potted plants
    plan1 = (("rose", ("C_D7343A", "C_E86A9E")), ("tulip", ("C_F2B03D", "C_F28C38", "C_E15533")), ("peony", ("C_F4A6C1", "C_F7D1DC")), ("rose", ("C_F4EFE4", "C_F2C23F")),
             ("tulip", ("C_8E6CCF", "C_B9A7DE")), ("peony", ("C_E86A9E",)))
    for i, (kind, cols) in enumerate(plan1):
        x = -.75 + i * .3; bucket(m, (x, .3, .14), .09, .24); sway = m.anim("Anim Sway")
        filler((x, .5, .14), sway); bunch_lite(m, (x, .5, .14), (kind,), cols, sway, n=6, h=.26, spread=.08, seed=i, s=1.25)
    plan2 = (("lily", ("C_F4EFE4", "C_FFD2A6")), ("lavender", ("C_8E6CCF", "C_A98BE0")), ("hydrangea", ("C_7BAFE0", "C_C9A2E8")), ("daisy", ("C_F4EFE4", "C_F2B8C6")),
             ("rose", ("C_F28C38", "C_F2C23F")), ("lavender", ("C_8E6CCF",)))
    for i, (kind, cols) in enumerate(plan2):
        x = -.75 + i * .3; bucket(m, (x, .6, .34), .09, .24); sway = m.anim("Anim Sway")
        filler((x, .8, .34), sway); bunch_lite(m, (x, .8, .34), (kind,), cols, sway, n=5 if kind != "hydrangea" else 4, h=.25 if kind != "lavender" else .32, spread=.08, seed=i + 5, s=1.25)
    for i in range(5):
        x = -.72 + i * .36
        if i % 2 == 0:
            bucket(m, (x, .9, .54), .1, .28); sway = m.anim("Anim Sway")
            filler((x, 1.12, .54), sway, 1.1); bunch_lite(m, (x, 1.12, .54), ("sunflower",), ("C_F2C23F",), sway, n=4, h=.36, spread=.07, seed=i + 10, s=1.3)
            greenery(m, (x, 1.12, .54), sway, n=3, h=.46, seed=i)
        else:
            potted_plant(m, (x, .9, .54), 1.0, "bush" if i == 1 else "fern", seed=i)
    # front-left: crates on the floor with terracotta pots (succulents + small plants)
    box(m, (.62, .14, .3), (-.78, .07, -.2), "T_IK_Crate", .008, 1)
    for i in range(3): potted_plant(m, (-1.0 + i * .22, .14, -.2 + (i % 2) * .03), .5, "succulent" if i % 2 else "bush", seed=i * 3)
    box(m, (.62, .14, .3), (-.78, .07, -.48), "T_IK_Crate", .008, 1); box(m, (.62, .14, .3), (-.78, .21, -.48), "T_IK_Crate", .008, 1)
    for i in range(3): potted_plant(m, (-1.0 + i * .22, .28, -.48), .55, ("fern", "succulent", "bush")[i], seed=i + 7)
    # front-centre: two big floor buckets, lush, and a watering can
    for i, (x, kinds, cols) in enumerate(((-.32, ("rose", "peony"), ("C_D7343A", "C_F2B03D", "C_F4A6C1")), (.02, ("tulip", "lily"), ("C_F4EFE4", "C_E86A9E", "C_F28C38")))):
        bucket(m, (x, 0, -.42), .13, .32); sway = m.anim("Anim Sway")
        filler((x, .28, -.42), sway, 1.4); bunch_lite(m, (x, .28, -.42), kinds, cols, sway, n=6, h=.4, spread=.1, seed=20 + i, s=1.3); greenery(m, (x, .28, -.42), sway, n=3, h=.52, seed=i + 4)
    L = Local(m, (-.15, 0, -.1), yaw=30)
    lathe(L, [(0, 0), (.08, 0), (.09, .14), (.07, .18), (.04, .2), (0, .2)], (0, 0, 0), ZINC, 10); bar(L, (.07, .1, 0), (.2, .2, 0), .01, ZINC, 6); torus_arc(L, .07, .008, (0, .2, 0), ZINC, 0, 180, roll=90, seg=8, minor=4)
    # front-right: wrapping counter with paper rolls on a rod, ribbon spools, kraft cone bouquets in a tall bucket
    L = Local(m, (.78, 0, -.32))
    box(L, (.56, .86, .5), (0, .43, 0), planks, .015, 2); box(L, (.6, .04, .54), (0, .88, 0), dark, .008, 1)
    for y in (.16, .72): box(L, (.58, .04, .52), (0, y, 0), dark, .006, 1)
    for sx in (-1, 1): bar(L, (sx * .25, .9, .18), (sx * .25, 1.28, .18), .014, dark, 6)
    bar(L, (-.27, 1.25, .18), (.27, 1.25, .18), .01, CHROME, 8); bar(L, (-.27, 1.05, .18), (.27, 1.05, .18), .01, CHROME, 8)
    cyl(L, .065, .22, (-.13, 1.25, .18), KRAFT, 12, roll=90); cyl(L, .055, .18, (.12, 1.25, .18), "T_IK_V3_WrapPink", 12, roll=90)
    cyl(L, .06, .2, (-.11, 1.05, .18), "C_F4EFE4", 12, roll=90); cyl(L, .05, .16, (.12, 1.05, .18), "C_7BD3F7", 12, roll=90)
    for i, col in enumerate(("C_" + GOLD, "C_E86A9E", "C_1F9A8E", "C_F4EFE4")):
        cyl(L, .032, .03, (-.2 + i * .11, .9, -.15), col, 10); cyl(L, .011, .034, (-.2 + i * .11, .9, -.15), "C_F4EFE4", 6)
    cone_bouquet(L, (.14, .9, .06), "rose", "C_D7343A", pitch=-70, yaw=-20)
    bar(L, (-.11, 1.17, .17), (.02, 1.08, .0), .004, "C_" + GOLD, 4)   # ribbon end hanging
    bucket(m, (.36, 0, -.48), .11, .36)
    for i, (kind, col) in enumerate((("rose", "C_E86A9E"), ("tulip", "C_F2B03D"), ("peony", "C_F4A6C1"))):
        cone_bouquet(m, (.3 + (i % 2) * .11, .24, -.52 + (i // 2) * .1), kind, col, pitch=-14 + (i % 2) * 10, yaw=-25 + i * 20)
    # chalkboard with flower pictograms hanging from the front beam on the left, a tall lavender pot at the left end
    box(m, (.42, .46, .025), (-.86, 1.9, -.54), dark, .006, 1); card(m, .38, .42, (-.86, 1.9, -.555), "T_IK_V2_ChalkFlowers")
    for x in (-1.02, -.7): bar(m, (x, 2.29, -.56), (x, 2.13, -.54), .005, "C_" + DARK, 4)
    pot(m, (-1.0, 0, .12), .12, .22); sway = m.anim("Anim Sway")
    filler((-1.0, .22, .12), sway, 1.1); bunch_lite(m, (-1.0, .22, .12), ("lavender",), ("C_8E6CCF", "C_A98BE0"), sway, n=7, h=.38, spread=.07, seed=33, s=1.3)
    # a few fallen petals on the floor
    for i in range(6):
        prism(m, arc_points(.018, 0, 360, 6), .003, (rng.uniform(-.9, .9), .002, rng.uniform(-.55, -.25)), ("C_E86A9E", "C_F2C23F", "C_D7343A")[i % 3], pitch=90)

# ------------------------------------------------------------------------------------------------- photo booth
def curtain_bm(width, height, waves, amp, thick, cols=36, rows=4):
    """Gathered fabric panel in Unity local space: top edge along -X from the pivot (0,0,0), hanging down (-Y)."""
    bm = bmesh.new(); grid = []
    for i in range(cols + 1):
        t = i / cols; x = -width * t
        col_f, col_b = [], []
        for j in range(rows + 1):
            u = j / rows; y = -height * u
            z = amp * (.55 + .45 * u) * math.sin(2 * math.pi * waves * t) + .012 * u   # pleats deepen towards the hem
            col_f.append(bm.verts.new(K.U(x, y, z - thick / 2))); col_b.append(bm.verts.new(K.U(x, y, z + thick / 2)))
        grid.append((col_f, col_b))
    for i in range(cols):
        (f0, b0), (f1, b1) = grid[i], grid[i + 1]
        for j in range(rows):
            bm.faces.new((f0[j], f1[j], f1[j + 1], f0[j + 1])); bm.faces.new((b0[j + 1], b1[j + 1], b1[j], b0[j]))
        bm.faces.new((f0[0], b0[0], b1[0], f1[0])); bm.faces.new((f0[rows], f1[rows], b1[rows], b0[rows]))
    for (f, b) in (grid[0], grid[-1]):
        for j in range(rows): bm.faces.new((f[j], f[j + 1], b[j + 1], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for fc in bm.faces: fc.smooth = True
    return bm

@model("photo-booth")
def photo_booth(m):
    navy = "T_IK_V2_PaintNavy"; cream = "T_IK_V2_PaintCream"; nodes = blink_nodes(m, 3)
    box(m, (.96, .08, .96), (0, .04, 0), "C_" + DARK, .02)
    box(m, (.96, 1.9, .05), (0, 1.03, .455), navy, .02, 2); box(m, (.05, 1.9, .96), (-.455, 1.03, 0), navy, .02, 2)
    box(m, (.05, 1.9, .96), (.455, 1.03, 0), navy, .02, 2)
    box(m, (.34, 1.9, .05), (-.31, 1.03, -.455), cream, .02, 2)
    box(m, (.96, .12, .96), (0, 2.04, 0), navy, .03, 3); box(m, (1.0, .04, 1.0), (0, 2.12, 0), "C_" + GOLD, .012, 2)
    # curtain rail (Body) and the curtain on its own node, pivot at the rail end on the +X wall
    bar(m, (-.14, 1.86, -.44), (.44, 1.86, -.44), .012, CHROME, 8)
    for x in (-.14, .44): box(m, (.03, .03, .04), (x, 1.86, -.44), CHROME, .004, 1)
    PIV = (.44, 1.86, -.44); cur = "Anim Curtain"; m.pivots = {cur: PIV}
    bm = curtain_bm(.56, 1.52, 7, .034, .012)
    bmesh.ops.translate(bm, vec=K.U(*PIV), verts=bm.verts); m.add(bm, "C_" + RED, cur)
    for i in range(8): torus(m, .018, .005, (.42 - i * .077, 1.86, -.44), "C_" + GOLD, roll=90, obj=cur, seg=8, minor=4)
    box(m, (.56, .05, .02), (.16, 1.835, -.44), "C_" + GOLD, .004, 1, obj=cur)   # header tape
    # inside: bench, screen panel with camera + flash
    box(m, (.86, .06, .3), (0, .5, .3), "C_" + RED, .02, 2); box(m, (.86, .3, .05), (0, .32, .42), "C_" + RED, .02, 2)
    box(m, (.05, .9, .5), (-.42, 1.2, 0), cream, .01, 1)
    box(m, (.04, .5, .44), (-.425, 1.25, .0), "C_" + DARK, .008, 2); box(m, (.012, .3, .38), (-.4, 1.3, 0), "E_7BD3F7", .003, 1)
    cyl(m, .05, .03, (-.4, 1.58, 0), "C_" + DARK, 14, .006, roll=90); cyl(m, .03, .01, (-.385, 1.58, 0), "G_Glass", 12, roll=90)
    box(m, (.02, .1, .14), (-.39, 1.58, .22), "E_FFF7D8", .004, 1)
    # outside front-left panel: sample strip, coin slot, photo slot, camera pictogram sign on the crown
    rounded_panel(m, .26, .66, (-.31, 1.3, -.482), "C_" + GOLD, .012, .03); card(m, .22, .62, (-.31, 1.3, -.49), "T_IK_V2_PhotoStrip")
    box(m, (.2, .1, .02), (-.31, .82, -.485), CHROME, .006, 1); box(m, (.05, .006, .01), (-.33, .82, -.497), "C_" + DARK, .001, 1); cyl(m, .02, .01, (-.26, .82, -.49), "C_" + DARK, 10, pitch=-90)
    box(m, (.24, .04, .02), (-.31, .62, -.485), "C_" + DARK, .006, 1); box(m, (.2, .01, .022), (-.31, .62, -.49), "C_F4EFE4", .002, 1)
    rounded_panel(m, .6, .18, (0, 2.04, -.49), "C_" + GOLD, .015, .04)
    rounded_panel(m, .18, .11, (-.02, 2.03, -.505), "C_" + NAVY, .012, .02); cyl(m, .035, .012, (-.02, 2.03, -.515), "C_F4EFE4", 14, pitch=-90); cyl(m, .02, .014, (-.02, 2.03, -.52), "C_" + NAVY, 12, pitch=-90)
    box(m, (.05, .03, .012), (.06, 2.085, -.51), "C_" + NAVY, .003, 1)
    for sx in (-1, 1): prism(m, star_pts(.03, .013), .012, (sx * .22, 2.04, -.505), "E_FFE066")
    leds(m, [(-.42 + k * .0764, 2.14, -.47) for k in range(12)], nodes, r=.016)

# ------------------------------------------------------------------------------------------------- build / preview
def tri_count(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == "MESH")

def bounds(objs):
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi

def render_views(objs, out_base, tag, views=(("game", 32, 38, 1.75), ("close", 38, 17, 1.45))):
    sc = bpy.context.scene
    lo, hi = bounds(objs); center = (lo + hi) / 2; radius = max((hi - lo).length * .5, .3)
    cam = bpy.data.objects.get("V3_Cam") or bpy.data.objects.new("V3_Cam", bpy.data.cameras.new("V3_Cam"))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    cam.data.type = "PERSP"; cam.data.lens = 45; cam.data.clip_end = 100; sc.camera = cam
    sun = bpy.data.objects.get("V3_Sun") or bpy.data.objects.new("V3_Sun", bpy.data.lights.new("V3_Sun", "SUN"))
    if sun.name not in sc.collection.objects: sc.collection.objects.link(sun)
    sun.data.energy = 2.6; sun.data.angle = math.radians(15); sun.rotation_euler = (math.radians(42), math.radians(8), math.radians(150))
    fill = bpy.data.objects.get("V3_Fill") or bpy.data.objects.new("V3_Fill", bpy.data.lights.new("V3_Fill", "SUN"))
    if fill.name not in sc.collection.objects: sc.collection.objects.link(fill)
    fill.data.energy = .9; fill.rotation_euler = (math.radians(60), 0, math.radians(-40))
    sc.render.engine = "BLENDER_EEVEE"; sc.render.film_transparent = False
    try: sc.eevee.taa_render_samples = 24
    except Exception: pass
    sc.render.resolution_x = sc.render.resolution_y = 800; sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
    if not sc.world: sc.world = bpy.data.worlds.new("V3_World")
    sc.world.use_nodes = True; bg = sc.world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value = (.84, .87, .9, 1); bg.inputs["Strength"].default_value = .8
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = -.1
    outs = []
    for name, az, el, k in views:
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
        cam.location = center + d * radius * k * 1.7
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = f"{out_base}_{tag}_{name}.png"; bpy.ops.render.render(write_still=True); outs.append(sc.render.filepath)
    return outs

def render_old(name):
    """The FBX that is in Assets today, re-materialised through the kit's material() by slot name, rendered under its own id."""
    path = os.path.join(K.UNITY, "Art", "Interior", "Models", name + ".fbx")
    if not os.path.exists(path): return 0
    K.clear_scene()
    before = set(bpy.data.materials.keys()); imgs_before = set(bpy.data.images.keys())
    bpy.ops.import_scene.fbx(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    keys = {}
    for mname in [n for n in bpy.data.materials.keys() if n not in before]:
        mat = bpy.data.materials[mname]; keys["old_" + mname] = mname.split(".")[0]; mat.name = "old_" + mname
    for img_name in [n for n in bpy.data.images.keys() if n not in imgs_before]:
        bpy.data.images.remove(bpy.data.images[img_name])
    for o in objs:
        for i, mat in enumerate(o.data.materials):
            if mat is None: continue
            o.data.materials[i] = K.material(keys.get(mat.name, mat.name.split(".")[0]))
    tris = tri_count(objs)
    render_views(objs, os.path.join(PRE, name), "old")
    return tris

def textures_used(objs):
    out = set()
    for o in objs:
        for mat in o.data.materials:
            if mat and mat.name.startswith("T_"): out.add(mat.name[2:].split(".")[0])
    return out

def meta_for(path):
    if not os.path.exists(path + ".meta"):
        with open(path + ".meta", "w") as f: f.write("fileFormatVersion: 2\nguid: %s\n" % uuid.uuid4().hex)

def install(report, backup_dir):
    """Copy FBX, thumbnails and textures into Assets, backing up what gets replaced (same relative path)."""
    written = []; backed = []
    def put(src, dst):
        rel = os.path.relpath(dst, K.UNITY)
        if os.path.exists(dst):
            b = os.path.join(backup_dir, rel); os.makedirs(os.path.dirname(b), exist_ok=True)
            if not os.path.exists(b): shutil.copy2(dst, b); backed.append(rel)
            if os.path.exists(dst + ".meta") and not os.path.exists(b + ".meta"): shutil.copy2(dst + ".meta", b + ".meta")
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst); meta_for(dst); written.append(rel)
    texs = set()
    for name, r in report.items():
        put(os.path.join(K.OUT, name + ".fbx"), os.path.join(K.UNITY, "Art", "Interior", "Models", name + ".fbx"))
        put(os.path.join(K.THUMBS, name + ".png"), os.path.join(K.UNITY, "Resources", "CheckoutDesktop", "Decor", name + ".png"))
        texs |= set(r["textures"])
    for t in sorted(texs):
        src = os.path.join(TEX2, t + "_albedo.png")
        if os.path.exists(src): put(src, os.path.join(K.TEX, t + "_albedo.png"))
    return written, backed

def main(names, do_install):
    report = {}
    for name in names:
        t0 = time.time()
        tris_old = render_old(name) if name in ("cart-corral", "atm", "claw-machine", "gumball", "flower-stand") else 0
        m = Model(name); V3[name](m)
        objs = K.export(m); K.thumbnail(name, objs)
        tris = tri_count(objs)
        render_views(objs, os.path.join(PRE, name), "new")
        extra = {}
        if name == "photo-booth":
            cur = bpy.data.objects["Anim Curtain"]; cur.scale.x = .25
            bpy.context.view_layer.update()
            render_views(objs, os.path.join(PRE, name), "open")
            cur.scale.x = 1.0
            extra = {"curtain_pivot_unity": [.44, 1.86, -.44], "curtain_axis": "local X (scale 1 closed -> 0.25 open, bunches to the +X wall)"}
        lo, hi = bounds(objs); size = hi - lo
        report[name] = {"tris_old": tris_old, "tris": tris, "footprint_x_z_h": [round(size.x, 2), round(size.y, 2), round(size.z, 2)],
                        "objects": [o.name for o in objs], "anim": sorted({o.name.split(".")[0] for o in objs if o.name.startswith("Anim")}),
                        "textures": sorted(textures_used(objs)), "secs": round(time.time() - t0, 1), **extra}
        print("V3DONE " + json.dumps({name: report[name]}), flush=True)
    rp = os.path.join(Q3, "report.json")
    old = json.load(open(rp)) if os.path.exists(rp) else {}
    old.update(report); json.dump(old, open(rp, "w"), indent=1)
    if do_install:
        written, backed = install(old, os.path.join(Q, "backup_20261019"))
        json.dump({"written": written, "backed_up": backed}, open(os.path.join(Q3, "install.json"), "w"), indent=1)
        print("INSTALLED " + json.dumps({"written": len(written), "backed_up": len(backed)}), flush=True)
    print("ALLDONE", flush=True)

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_install = "--install" in args; args = [a for a in args if a != "--install"]
    main(args or list(V3), do_install)
