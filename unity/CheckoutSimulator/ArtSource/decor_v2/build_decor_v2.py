"""Build-mode decorations v2 (Oct 2026): detailed, textured remakes of the interior-kit decorations, same material
contract (C_RRGGBB / T_<tex> / S_ / E_ / G_Glass, Anim * nodes) and the same footprints as build_interior_kit.py.

Preview only: exports FBX to ArtSource/decor_v2/fbx and thumbnails/previews to ArtSource/decor_v2 (nothing under Assets).
    blender -b --factory-startup --python build_decor_v2.py -- [names...]
New painted textures live in ArtSource/decor_v2/tex as IK_V2_<name>_albedo.png (to be copied to Assets/Art/Interior/Textures
at install time).
"""
import sys, os, json, math, time
sys.path.insert(0, r"C:\Checkout-mobile\scripts\blender")
import bpy, bmesh
from mathutils import Vector, Matrix
import build_interior_kit as K
from build_interior_kit import (Model, box, cyl, lathe, lathe_s, ball, bar, torus, torus_arc, prism, quad, rounded_panel, awning, Local,
                                arc_points, pergola_lights, NAVY, GOLD, GOLDL, CREAM, WHITE, TEAL, TEALD, RED, ORANGE, PINK, WOOD, WOODL,
                                WOODD, STEEL, DARK, GREEN, LEAF, LEAFD, BLUE, PURPLE)

Q = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\decor_v2"
K.OUT = os.path.join(Q, "fbx"); K.THUMBS = os.path.join(Q, "thumbs"); PRE = os.path.join(Q, "previews"); TEX2 = os.path.join(Q, "tex")
for d in (K.OUT, K.THUMBS, PRE): os.makedirs(d, exist_ok=True)
_orig_load = K.load_tex
def load_tex(name):
    p = os.path.join(TEX2, name + "_albedo.png")
    if os.path.exists(p):
        return bpy.data.images.get(name + "_albedo.png") or bpy.data.images.load(p)
    return _orig_load(name)
K.load_tex = load_tex
_orig_material = K.material
def material(key):
    fresh = bpy.data.materials.get(key) is None
    mat = _orig_material(key)
    if fresh and key in ("T_IK_V2_Chrome", "T_IK_R_Brushed", "T_IK_Steel"):   # preview shading only; Unity uses its own shader
        bsdf = mat.node_tree.nodes.get("Principled BSDF"); bsdf.inputs["Metallic"].default_value = .85; bsdf.inputs["Roughness"].default_value = .3
    return mat
K.material = material

def clear_scene():
    """Headless-safe version of the kit's clear_scene (no window in -b mode)."""
    sc = bpy.data.scenes.get("IK")
    if sc is None:
        sc = bpy.context.scene; sc.name = "IK"
    if bpy.context.window is not None and bpy.context.window.scene is not sc:
        bpy.context.window.scene = sc
    for o in list(sc.objects): bpy.data.objects.remove(o)
    for me in list(bpy.data.meshes):
        if me.users == 0: bpy.data.meshes.remove(me)
    return sc
K.clear_scene = clear_scene

CHROME = "T_IK_V2_Chrome"; BRUSH = "T_IK_R_Brushed"; PLANKS = "T_IK_R_Planks"; ZINC = "T_IK_Steel"
V2 = {}
def model(name):
    def wrap(fn): V2[name] = fn; return fn
    return wrap

# ------------------------------------------------------------------------------------------------- shared bits
def tube(m, pts, r, key, seg=8, obj="Body"):
    for a, b in zip(pts, pts[1:]): bar(m, a, b, r, key, seg, obj)
    for p in pts[1:-1]: ball(m, p, (r * 2, r * 2, r * 2), key, 8, 5, obj)

def wheel_caster(m, c, r=.05, w=.03, key_t="C_" + DARK, key_f="C_" + STEEL, obj="Body", swivel=True):
    x, y, z = c
    cyl(m, r, w, (x - w / 2, y, z), key_t, 14, .006, roll=90, obj=obj)
    cyl(m, r * .4, w + .01, (x - w / 2 - .005, y, z), key_f, 10, 0, roll=90, obj=obj)
    for s in (-1, 1): box(m, (.006, r * 1.1, r * .9), (x + s * (w / 2 + .004), y + r * .35, z), key_f, .002, 1, obj=obj)
    box(m, (w + .02, .02, .05), (x, y + r + .02, z), key_f, .004, 1, obj=obj)
    if swivel: cyl(m, .012, .05, (x, y + r + .03, z), key_f, 8, obj=obj)

def plush(m, c, kind="bear", col="C_D9A066", obj="Body", s=1.0, yaw=0):
    L = Local(m, c, yaw=yaw, obj=obj); fur = col; cream = "C_F6E7C8"; ink = "C_" + DARK
    body = (.18 * s, .15 * s, .14 * s); ball(L, (0, .075 * s, 0), body, fur, 12, 8)
    ball(L, (0, .19 * s, -.01 * s), (.14 * s, .13 * s, .13 * s), fur, 12, 8)
    for sx in (-1, 1):   # arms + legs
        ball(L, (sx * .1 * s, .08 * s, -.03 * s), (.06 * s, .05 * s, .08 * s), fur, 8, 6)
        ball(L, (sx * .06 * s, .02 * s, -.07 * s), (.07 * s, .05 * s, .09 * s), fur, 8, 6)
        ball(L, (sx * .035 * s, .2 * s, -.065 * s), (.016 * s, .018 * s, .01 * s), ink, 6, 4)   # eyes
    if kind == "bear":
        for sx in (-1, 1): ball(L, (sx * .055 * s, .245 * s, 0), (.05 * s, .05 * s, .03 * s), fur, 8, 6)
        ball(L, (0, .17 * s, -.065 * s), (.06 * s, .045 * s, .04 * s), cream, 8, 6); ball(L, (0, .18 * s, -.085 * s), (.02 * s, .015 * s, .012 * s), ink, 6, 4)
    elif kind == "bunny":
        for sx in (-1, 1): ball(L, (sx * .04 * s, .3 * s, .01 * s), (.045 * s, .16 * s, .03 * s), fur, 8, 6); ball(L, (sx * .04 * s, .3 * s, -.004 * s), (.02 * s, .11 * s, .02 * s), "C_F2B8C6", 6, 5)
        ball(L, (0, .165 * s, -.065 * s), (.02 * s, .015 * s, .012 * s), "C_F28CA8", 6, 4)
    elif kind == "cat":
        for sx in (-1, 1): lathe(L, [(.03 * s, 0), (0, .06 * s)], (sx * .05 * s, .23 * s, 0), fur, 8)
        ball(L, (0, .165 * s, -.065 * s), (.02 * s, .014 * s, .012 * s), "C_F28CA8", 6, 4)
        bar(L, (.08 * s, .03 * s, .05 * s), (.14 * s, .09 * s, .09 * s), .014 * s, fur, 6)
    elif kind == "duck":
        prism(L, [(-.03 * s, .17 * s), (.03 * s, .17 * s), (0, .14 * s)], .05 * s, (0, 0, -.085 * s), "C_" + ORANGE)
        ball(L, (0, .03 * s, 0), (.2 * s, .08 * s, .16 * s), "C_" + ORANGE, 10, 5)   # feet pad
    elif kind == "pig":
        ball(L, (0, .17 * s, -.07 * s), (.05 * s, .035 * s, .03 * s), "C_F2A0B8", 8, 6)
        for sx in (-1, 1): lathe(L, [(.025 * s, 0), (0, .04 * s)], (sx * .05 * s, .24 * s, 0), fur, 6)

def flower(m, c, kind, col, obj="Body", s=1.0):
    """A flower head at c (top of its stem)."""
    L = Local(m, c, obj=obj)
    if kind == "rose":
        lathe(L, [(0, 0), (.028 * s, 0), (.04 * s, .03 * s), (.036 * s, .06 * s), (.02 * s, .075 * s), (0, .07 * s)], (0, 0, 0), col, 10)
        torus(L, .034 * s, .012 * s, (0, .025 * s, 0), col, seg=10, minor=5); torus(L, .024 * s, .01 * s, (0, .05 * s, 0), col, seg=8, minor=5)
    elif kind == "tulip":
        lathe(L, [(0, 0), (.02 * s, 0), (.032 * s, .04 * s), (.026 * s, .07 * s), (.012 * s, .08 * s), (0, .078 * s)], (0, 0, 0), col, 8)
        for i in range(3):
            a = i * 120; prism(L, [(-.014 * s, .05 * s), (.014 * s, .05 * s), (0, .095 * s)], .004, (math.sin(math.radians(a)) * .022 * s, 0, math.cos(math.radians(a)) * .022 * s), col, yaw=a)
    elif kind == "sunflower":
        cyl(L, .03 * s, .012 * s, (0, 0, 0), "C_5A3A1E", 10, .003, pitch=-90)
        for i in range(10):
            a = i * 36; prism(L, [(-.012 * s, .03 * s), (.012 * s, .03 * s), (.004 * s, .075 * s), (-.004 * s, .075 * s)], .004, (0, .006 * s, 0), "C_F2C23F", pitch=-90, yaw=a)
    elif kind == "lily":
        for i in range(6):
            a = i * 60; prism(L, [(-.012 * s, .0), (.012 * s, 0), (.006 * s, .07 * s), (-.006 * s, .07 * s)], .004, (0, .01 * s, 0), col, pitch=-60, yaw=a)
        cyl(L, .008 * s, .03 * s, (0, 0, 0), "C_F2C23F", 6)
    elif kind == "daisy":
        cyl(L, .016 * s, .01 * s, (0, 0, 0), "C_F2C23F", 8, 0, pitch=-90)
        for i in range(8):
            a = i * 45; prism(L, [(-.009 * s, .015 * s), (.009 * s, .015 * s), (.005 * s, .05 * s), (-.005 * s, .05 * s)], .004, (0, .004 * s, 0), col, pitch=-90, yaw=a)

def bunch(m, base, kinds, cols, obj, n=7, h=.42, spread=.075, seed=0):
    r = (seed * 7919) % 97
    for k in range(n):
        a = k * 2.399 + r; rad_ = spread * math.sqrt((k + .5) / n); hh = h + ((k * 37 + r) % 5) * .018
        top = (base[0] + math.cos(a) * rad_, base[1] + hh, base[2] + math.sin(a) * rad_)
        bar(m, (base[0] + math.cos(a) * rad_ * .3, base[1], base[2] + math.sin(a) * rad_ * .3), top, .005, "C_" + LEAFD, 5, obj)
        flower(m, top, kinds[k % len(kinds)], cols[k % len(cols)], obj)
        if k % 2 == 0:
            prism(m, [(-.012, 0), (.012, 0), (.02, .05), (0, .09), (-.02, .05)], .003, (top[0] + .02, base[1] + hh * .55, top[2]), "C_" + LEAF, pitch=-30, yaw=a * 57, obj=obj)

def bucket(m, c, r=.11, h=.28, key=ZINC, obj="Body"):
    L = Local(m, c, obj=obj)
    lathe(L, [(0, 0), (r * .8, 0), (r * .82, .01), (r, h - .02), (r + .012, h - .02), (r + .012, h), (r - .006, h), (r * .85, .02), (0, .02)], (0, 0, 0), key, 18)
    torus(L, r + .004, .006, (0, h * .5, 0), key, seg=18, minor=5); torus(L, r + .004, .006, (0, h * .15, 0), key, seg=18, minor=5)
    for sx in (-1, 1): bar(L, (sx * (r + .01), h - .04, 0), (sx * (r + .01), h + .02, 0), .005, key, 5)
    torus_arc(L, r + .01, .006, (0, h + .02, 0), "C_" + DARK, 0, 180, roll=90, seg=10, minor=5)

def led_strip(m, x0, x1, y, z, n, key_a="E_FFE066", key_b="E_FF6FA8", r=.022, blink=True, yaw=0):
    for i in range(n):
        t = (i + .5) / n; x = x0 + (x1 - x0) * t
        c = (x * math.cos(math.radians(yaw)) + z * math.sin(math.radians(yaw)), y, z * math.cos(math.radians(yaw)) - x * math.sin(math.radians(yaw))) if yaw else (x, y, z)
        obj = m.anim("Anim Blink") if blink and i % 3 == 0 else "Body"
        ball(m, c, (r * 2, r * 2, r * 1.4), key_a if i % 2 == 0 else key_b, 8, 5, obj)

def star_pts(r_out, r_in, n=5):
    return [((r_out if k % 2 == 0 else r_in) * math.cos(math.pi / 2 + k * math.pi / n), (r_out if k % 2 == 0 else r_in) * math.sin(math.pi / 2 + k * math.pi / n)) for k in range(2 * n)]

# ------------------------------------------------------------------------------------------------- 1. cart corral
def cart2(m, z0, obj="Body", first=False):
    L = Local(m, (0, 0, z0), obj=obj); st = BRUSH; wire = "C_D8DEE2"; red = "C_" + RED
    y0, y1 = .50, .86; wf, wr = .21, .28; zf, zr = -.37, .37   # basket: front narrower, floor y0, rim y1
    def side(sx):
        # rim + floor rails, verticals, horizontals
        tube(L, [(sx * wf, y1, zf), (sx * wr, y1, zr)], .011, st, 6)
        bar(L, (sx * wf, y0, zf), (sx * wr, y0, zr), .006, wire, 5)
        for i in range(11):
            t = (i + .5) / 11; x = sx * (wf + (wr - wf) * t); z = zf + (zr - zf) * t
            bar(L, (x, y0, z), (x, y1, z), .004, wire, 4)
        for yy in (.62, .74):
            bar(L, (sx * wf, yy, zf), (sx * wr, yy, zr), .004, wire, 4)
    side(-1); side(1)
    for zz, w in ((zf, wf), (zr, wr)):   # front and rear walls
        tube(L, [(-w, y1, zz), (w, y1, zz)], .011, st, 6); bar(L, (-w, y0, zz), (w, y0, zz), .006, wire, 5)
        n = 7 if zz < 0 else 9
        for i in range(n):
            x = -w + 2 * w * (i + .5) / n; bar(L, (x, y0, zz), (x, y1, zz), .004, wire, 4)
        for yy in (.62, .74): bar(L, (-w, yy, zz), (w, yy, zz), .004, wire, 4)
    for i in range(7):   # floor grid
        t = (i + .5) / 7; bar(L, (-wf + 2 * wf * t, y0, zf), (-wr + 2 * wr * t, y0, zr), .004, wire, 4)
    for i in range(5):
        t = (i + .5) / 5; z = zf + (zr - zf) * t; w = wf + (wr - wf) * t; bar(L, (-w, y0, z), (w, y0, z), .004, wire, 4)
    # child seat: folded flap + leg plate on the rear wall, red plastic
    box(L, (.3, .14, .02), (0, .74, zr - .05), red, .008, 2, pitch=-20); box(L, (.3, .02, .14), (0, .66, zr - .1), red, .008, 2)
    box(L, (.3, .04, .02), (0, .84, zr - .02), red, .008, 2)
    # handle: uprights from the rim, bar with a red grip
    for sx in (-1, 1):
        tube(L, [(sx * wr, y1, zr), (sx * .3, .98, zr + .09), (sx * .3, 1.0, zr + .1)], .011, st, 6)
    bar(L, (-.3, 1.0, zr + .1), (.3, 1.0, zr + .1), .011, st, 8)
    cyl(L, .018, .34, (-.17, 1.0, zr + .1), red, 10, .006, roll=90)
    # chassis: two tubes from the rear rim corners down to the wheels, lower tray, casters
    for sx in (-1, 1):
        tube(L, [(sx * wr, y0, zr - .02), (sx * .25, .18, zr - .08), (sx * .25, .1, zr - .08)], .011, st, 6)
        tube(L, [(sx * (wf + .02), y0, zf + .04), (sx * .2, .14, zf + .06)], .011, st, 6)
        bar(L, (sx * .25, .2, zr - .08), (sx * .2, .2, zf + .08), .008, st, 6)
        wheel_caster(L, (sx * .2, .05, zf + .08), swivel=True); wheel_caster(L, (sx * .25, .05, zr - .08), swivel=False)
    for i in range(4):
        t = (i + .5) / 4; z = zf + .08 + (zr - zf - .16) * t; w = .2 + .05 * t; bar(L, (-w, .2, z), (w, .2, z), .004, wire, 4)
    bar(L, (-.22, .2, zf + .08), (-.22, .2, zr - .08), .004, wire, 4); bar(L, (.22, .2, zf + .08), (.22, .2, zr - .08), .004, wire, 4)
    # front bumper corners
    for sx in (-1, 1): box(L, (.06, .05, .06), (sx * wf, y1, zf), red, .012, 2)

@model("cart-corral")
def cart_corral(m):
    st = BRUSH
    for sx in (-1, 1):
        tube(m, [(sx * .4, 0, -.95), (sx * .4, .62, -.95), (sx * .4, .62, .95), (sx * .4, 0, .95)], .022, st, 10)
        bar(m, (sx * .4, .28, -.95), (sx * .4, .28, .95), .016, st, 8)
        for z in (-.95, .95): cyl(m, .06, .015, (sx * .4, 0, z), "C_" + DARK, 12, .004)
    bar(m, (-.4, .62, .95), (.4, .62, .95), .022, st, 10)
    box(m, (.86, .04, .08), (0, .02, -.97), "C_" + GOLD, .01)   # painted floor stop
    cyl(m, .024, 1.3, (0, 0, .99), st, 10); cyl(m, .07, .02, (0, 0, .99), "C_" + DARK, 12, .004)
    rounded_panel(m, .56, .56, (0, 1.32, .99), "C_" + NAVY, .03, .08); quad(m, .5, .5, (0, 1.32, .968), "T_IK_V2_SignCart")
    rounded_panel(m, .6, .6, (0, 1.32, 1.0), "C_" + GOLD, .012, .09)
    for i in range(5):
        cart2(m, -.6 + i * .28, first=(i == 0))

# ------------------------------------------------------------------------------------------------- 2. ATM
@model("atm")
def atm(m):
    teal = "T_IK_V2_PaintTeal"; navy = "T_IK_V2_PaintNavy"
    box(m, (.72, .1, .62), (0, .05, .04), "C_" + DARK, .02)
    box(m, (.7, 1.52, .6), (0, .86, .04), BRUSH, .04, 3)
    box(m, (.66, .72, .06), (0, 1.2, -.255), teal, .02, 2)                 # upper fascia
    box(m, (.66, .5, .05), (0, .42, -.25), navy, .02, 2)                   # service door
    box(m, (.6, .012, .012), (0, .66, -.277), "C_" + DARK, .003, 1); box(m, (.012, .46, .012), (.27, .42, -.277), "C_" + DARK, .003, 1)
    cyl(m, .016, .01, (.2, .36, -.28), CHROME, 10, pitch=-90)             # lock
    box(m, (.68, .04, .62), (0, 1.62, .04), "C_" + GOLD, .01, 1)           # trim band
    # privacy hood
    box(m, (.52, .04, .22), (0, 1.45, -.37), "C_" + DARK, .012, 2)
    for sx in (-1, 1): box(m, (.03, .36, .22), (sx * .245, 1.27, -.37), "C_" + DARK, .01, 2)
    # screen + side keys
    box(m, (.46, .36, .03), (0, 1.26, -.29), "C_" + DARK, .01, 2, pitch=-8)
    quad(m, .4, .3, (0, 1.26, -.308), "T_IK_V2_ATMScreen", pitch=-8)
    for sx in (-1, 1):
        for i in range(4): box(m, (.03, .02, .018), (sx * .27, 1.14 + i * .07, -.29), CHROME, .004, 1)
    # keypad tray
    box(m, (.34, .035, .2), (-.1, .985, -.36), "C_" + DARK, .01, 2, pitch=-22)
    keys = [(i, j) for j in range(4) for i in range(3)]
    for i, j in keys:
        key = "C_F4EFE4" if not (j == 3 and i != 1) else ("C_" + RED if i == 0 else "C_" + GREEN)
        box(m, (.05, .012, .04), (-.19 + i * .06, 1.03 - j * .035 * math.cos(math.radians(22)) - .0, -.44 + j * .05 - .02 * j), key, .004, 1, pitch=-22)
    box(m, (.05, .012, .04), (-.01, 1.03, -.44), "C_" + GOLD, .004, 1, pitch=-22)
    # card slot (lit), receipt slot, cash slot with flap, speaker
    box(m, (.14, .05, .02), (.2, 1.06, -.29), "E_7CE08A", .006, 1); box(m, (.1, .018, .03), (.2, 1.06, -.295), "C_" + DARK, .003, 1)
    box(m, (.16, .03, .02), (.2, .95, -.29), "C_" + DARK, .006, 1); box(m, (.12, .008, .022), (.2, .95, -.3), "C_F4EFE4", .002, 1)
    box(m, (.4, .08, .04), (0, .78, -.29), "C_" + DARK, .01, 2); box(m, (.34, .022, .05), (0, .8, -.3), "C_" + GOLD, .006, 2, pitch=-55)
    for i in range(4):
        for j in range(3): cyl(m, .004, .006, (-.26 + i * .018, .9 + j * .018, -.29), "C_" + DARK, 6, pitch=-90)
    ball(m, (.27, 1.5, -.29), (.02, .02, .012), "E_7CE08A", 8, 5)
    # lit top panel with a card + banknote pictogram
    box(m, (.7, .26, .5), (0, 1.75, .0), navy, .03, 2)
    box(m, (.64, .2, .03), (0, 1.75, -.255), "E_FFF1C8", .01, 2)
    rounded_panel(m, .16, .11, (-.12, 1.75, -.278), "C_" + NAVY, .012, .02); box(m, (.16, .025, .006), (-.12, 1.775, -.286), "C_" + GOLD, .002, 1)
    rounded_panel(m, .2, .1, (.1, 1.75, -.278), "C_" + GREEN, .012, .012); cyl(m, .03, .008, (.1, 1.75, -.29), "C_F4EFE4", 12, pitch=-90)
    box(m, (.74, .04, .54), (0, 1.9, 0), "C_" + GOLD, .012, 2)
    box(m, (.68, .06, .04), (0, .1, -.28), "C_" + DARK, .01, 1)           # kick plate

# ------------------------------------------------------------------------------------------------- 3. claw machine
@model("claw-machine")
def claw_machine(m):
    pink = "T_IK_V2_PaintPink"; navy = "T_IK_V2_PaintNavy"
    box(m, (.86, .1, .86), (0, .05, 0), "C_" + DARK, .02)
    box(m, (.82, .86, .82), (0, .53, 0), pink, .04, 3)
    for sx in (-1, 1):
        for sz in (-1, 1): bar(m, (sx * .4, .1, sz * .4), (sx * .4, .95, sz * .4), .016, CHROME, 8)
    box(m, (.84, .03, .84), (0, .95, 0), CHROME, .01, 1)
    # coin door, prize chute with window and handle
    box(m, (.16, .2, .02), (-.26, .56, -.415), CHROME, .006, 1); box(m, (.03, .06, .01), (-.26, .6, -.428), "C_" + DARK, .002, 1)
    cyl(m, .02, .01, (-.26, .49, -.425), "C_" + DARK, 10, pitch=-90)
    box(m, (.3, .26, .03), (.18, .5, -.415), navy, .01, 2); box(m, (.22, .12, .012), (.18, .55, -.432), "G_Glass", .003, 1)
    bar(m, (.08, .42, -.44), (.28, .42, -.44), .012, CHROME, 8)
    # control panel: joystick + 2 buttons
    box(m, (.76, .1, .26), (0, .99, -.36), navy, .02, 2, pitch=-18)
    cyl(m, .035, .02, (-.15, 1.02, -.4), "C_" + DARK, 12, .004, pitch=-18); cyl(m, .011, .1, (-.15, 1.03, -.4), CHROME, 8, pitch=-18)
    ball(m, (-.15, 1.14, -.42), (.07, .07, .07), "C_" + RED, 12, 8)
    for i, col in enumerate(("C_F2B03D", "C_" + GREEN)):
        cyl(m, .045, .012, (.1 + i * .14, 1.015, -.4), CHROME, 14, pitch=-18); cyl(m, .036, .022, (.1 + i * .14, 1.02, -.4), col, 14, .006, pitch=-18)
    # case: gold posts, glass on three sides, painted back, cream floor, ceiling light
    for sx in (-1, 1):
        for sz in (-1, 1): box(m, (.05, 1.0, .05), (sx * .395, 1.47, sz * .395), "C_" + GOLD, .012, 2)
    box(m, (.76, .96, .012), (0, 1.47, -.39), "G_Glass", .002, 1)
    for sx in (-1, 1): box(m, (.012, .96, .76), (sx * .39, 1.47, 0), "G_Glass", .002, 1)
    box(m, (.76, .96, .03), (0, 1.47, .385), pink, .006, 1)
    box(m, (.78, .04, .78), (0, 1.0, 0), "C_" + CREAM, .01, 1); box(m, (.5, .03, .02), (0, 1.94, -.3), "E_FFF7D8", .006, 1)
    # plush toys
    toys = (("bear", "C_D9A066", (-.22, -.2), 20), ("bunny", "C_F4EFE4", (.1, -.22), -15), ("cat", "C_8D8D93", (.26, .05), 40), ("duck", "C_F2C23F", (-.05, .08), -30),
            ("pig", "C_F2A0B8", (-.26, .2), 60), ("bear", "C_6F4A2E", (.22, .26), -50), ("bunny", "C_B9A7DE", (-.02, .25), 10), ("duck", "C_F2C23F", (.08, -.02), 100))
    for kind, col, (x, z), yaw in toys:
        plush(m, (x, 1.02, z), kind, col, s=.85, yaw=yaw)
    # gantry + claw (Anim Spin)
    for sz in (-.28, .28): bar(m, (-.36, 1.9, sz), (.36, 1.9, sz), .012, CHROME, 8)
    bar(m, (.1, 1.9, -.28), (.1, 1.9, .28), .012, CHROME, 8); box(m, (.14, .07, .14), (.1, 1.88, .02), "C_" + DARK, .012, 2)
    bar(m, (.1, 1.85, .02), (.1, 1.66, .02), .005, "C_" + DARK, 5)
    spin = m.anim("Anim Spin")
    cyl(m, .04, .05, (.1, 1.62, .02), CHROME, 12, .006, obj=spin); cyl(m, .02, .03, (.1, 1.66, .02), "C_" + DARK, 8, obj=spin)
    for k in range(3):
        a = math.radians(k * 120 + 30); dx, dz = math.cos(a), math.sin(a)
        tube(m, [(.1 + dx * .03, 1.63, .02 + dz * .03), (.1 + dx * .085, 1.56, .02 + dz * .085), (.1 + dx * .07, 1.49, .02 + dz * .07), (.1 + dx * .03, 1.45, .02 + dz * .03)], .007, CHROME, 6, spin)
    # marquee: pink crown with star pictogram front and back, LED strips on the sides
    box(m, (.9, .2, .9), (0, 2.08, 0), pink, .04, 3)
    for yaw, z in ((0, -.46), (180, .46)):
        rounded_panel(m, .44, .16, (0, 2.08, z), "C_" + NAVY, .02, .04, yaw=yaw)
        prism(m, star_pts(.065, .03), .015, (0, 2.08, z - .018 if z < 0 else z + .018), "E_FFE066", yaw=yaw)
        for sx in (-1, 1): prism(m, star_pts(.035, .016), .015, (sx * .15, 2.08, z - .018 if z < 0 else z + .018), "E_FF6FA8", yaw=yaw)
    led_strip(m, -.38, .38, 2.19, -.45, 12); led_strip(m, -.38, .38, 2.19, .45, 12)
    led_strip(m, -.38, .38, 2.19, -.45, 10, yaw=90); led_strip(m, -.38, .38, 2.19, .45, 10, yaw=90)
    box(m, (.94, .04, .94), (0, 2.2, 0), "C_" + GOLD, .012, 2)

# ------------------------------------------------------------------------------------------------- 4. gumball
@model("gumball")
def gumball(m):
    red = "T_IK_V2_PaintRed"; navy = "T_IK_V2_PaintNavy"
    lathe(m, [(0, 0), (.2, 0), (.21, .02), (.2, .04), (.12, .06), (.09, .1), (.075, .3), (.09, .34), (.075, .38), (.065, .62), (.1, .68), (.1, .7), (0, .7)], (0, 0, 0), navy, 26)
    for i in range(8):   # fluting ridges on the column
        a = i * 45; bar(m, (math.cos(math.radians(a)) * .07, .4, math.sin(math.radians(a)) * .07), (math.cos(math.radians(a)) * .062, .6, math.sin(math.radians(a)) * .062), .006, navy, 5)
    torus(m, .1, .012, (0, .7, 0), CHROME, seg=24, minor=6)
    lathe(m, [(0, 0), (.14, 0), (.16, .03), (.16, .24), (.14, .27), (0, .27)], (0, .7, 0), red, 26)          # housing
    torus(m, .158, .012, (0, .97, 0), CHROME, seg=24, minor=6); torus(m, .158, .01, (0, .72, 0), CHROME, seg=24, minor=6)
    # coin mechanism with crank, chute flap
    box(m, (.12, .1, .025), (0, .86, -.155), CHROME, .006, 2); box(m, (.03, .004, .006), (0, .9, -.17), "C_" + DARK, .001, 1)
    cyl(m, .032, .025, (0, .855, -.168), CHROME, 14, .004, pitch=-90); bar(m, (0, .855, -.195), (.03, .83, -.2), .007, CHROME, 6); ball(m, (.03, .83, -.205), (.022, .022, .022), "C_" + DARK, 8, 6)
    rounded_panel(m, .08, .07, (0, .765, -.165), CHROME, .01, .015); bar(m, (-.04, .8, -.165), (.04, .8, -.165), .006, "C_" + DARK, 6)
    # globe with gumballs, chrome collar and crown
    lathe(m, [(0, 0), (.17, 0), (.185, .02), (.185, .05), (.16, .06), (0, .06)], (0, .97, 0), CHROME, 26)
    cols = ("C_E15533", "C_F2B03D", "C_2E8CAE", "C_5DA637", "C_E86A9E", "C_F4EFE4", "C_8E6CCF")
    k = 0
    for layer, (n, rr, yy) in enumerate(((9, .085, 1.055), (15, .13, 1.1), (18, .15, 1.15), (15, .13, 1.2), (10, .09, 1.25), (4, .04, 1.29))):
        for i in range(n):
            a = i * 2 * math.pi / n + layer * .4; r_ = rr * (.92 + .08 * ((i * 7) % 3) / 2)
            ball(m, (math.cos(a) * r_, yy, math.sin(a) * r_), (.05, .05, .05), cols[k % 7], 8, 6); k += 1
    ball(m, (0, 1.17, 0), (.4, .4, .4), "G_Glass", 24, 16)
    lathe(m, [(.11, 0), (.12, .02), (.1, .05), (.06, .07), (.055, .1), (0, .1)], (0, 1.33, 0), CHROME, 20)
    for i in range(6):
        a = i * 60; bar(m, (math.cos(math.radians(a)) * .05, 1.4, math.sin(math.radians(a)) * .05), (math.cos(math.radians(a)) * .035, 1.47, math.sin(math.radians(a)) * .035), .006, CHROME, 5)
    ball(m, (0, 1.47, 0), (.04, .04, .04), CHROME, 10, 6)

# ------------------------------------------------------------------------------------------------- 5. flower stand
@model("flower-stand")
def flower_stand(m):
    wood = PLANKS; dark = "T_IK_R_WoodDark"
    box(m, (1.16, .46, .7), (0, .47, 0), wood, .02, 2)
    for y in (.27, .68): box(m, (1.2, .05, .74), (0, y, 0), dark, .012, 1)
    for x in (-.58, .58): box(m, (.06, .5, .74), (x, .45, 0), dark, .012, 1)
    box(m, (1.22, .04, .76), (0, .72, 0), dark, .01, 1)
    # wheels (spoked) + axle + rear handles + front legs
    for sx in (-1, 1):
        torus(m, .26, .035, (sx * .63, .3, .05), dark, roll=90, seg=22, minor=8)
        for i in range(8):
            a = math.radians(i * 45); bar(m, (sx * .63, .3, .05), (sx * .63, .3 + math.cos(a) * .24, .05 + math.sin(a) * .24), .012, dark, 6)
        cyl(m, .05, .05, (sx * .63 - .025, .3, .05), "C_" + DARK, 12, .01, roll=90)
        bar(m, (sx * .5, .22, .34), (sx * .5, .0, .34), .02, dark, 8); bar(m, (sx * .5, .6, .3), (sx * .55, .95, .62), .02, dark, 8)
    bar(m, (-.63, .3, .05), (.63, .3, .05), .018, "C_" + DARK, 8)
    # raised rear tier
    box(m, (1.1, .05, .3), (0, .88, .18), dark, .01, 1)
    for x in (-.5, .5): box(m, (.05, .16, .05), (x, .8, .22), dark, .01, 1)
    # buckets with bunches (front row on the deck, back row on the tier)
    plan = ((-.4, .74, -.15, ("rose",), ("C_D7343A", "C_E86A9E"), 0), (0, .74, -.15, ("tulip",), ("C_F2B03D", "C_F28C38", "C_E15533"), 1), (.4, .74, -.15, ("lily",), ("C_F4EFE4",), 2),
            (-.36, .9, .18, ("sunflower",), ("C_F2C23F",), 3), (.0, .9, .18, ("daisy",), ("C_F4EFE4", "C_F2B8C6"), 4), (.36, .9, .18, ("rose", "tulip"), ("C_8E6CCF", "C_B9A7DE"), 5))
    for x, y, z, kinds, cols, seed in plan:
        bucket(m, (x, y, z), .11, .27)
        sway = m.anim("Anim Sway")
        bunch(m, (x, y + .2, z), kinds, cols, sway, n=7 if kinds[0] != "sunflower" else 5, h=.36 if kinds[0] == "sunflower" else .3, seed=seed)
    # wrapped bouquets in a crate at the front left of the deck
    box(m, (.34, .16, .28), (-.42, .82, .22), "T_IK_Crate", .01, 1)
    for i, (kind, col) in enumerate((("rose", "C_D7343A"), ("tulip", "C_F2B03D"), ("daisy", "C_F4EFE4"))):
        L = Local(m, (-.5 + i * .09, .86, .3 - i * .03), pitch=-25 + i * 10, yaw=-20 + i * 15)
        lathe(L, [(0, 0), (.025, 0), (.09, .32), (.1, .34), (.085, .34), (.02, .02)], (0, 0, 0), "T_IK_V2_Kraft", 12)
        torus(L, .05, .008, (0, .22, 0), "C_" + GOLD, seg=12, minor=5)
        for k in range(5):
            a = k * 1.3; flower(L, (math.cos(a) * .045, .34 + (k % 2) * .02, math.sin(a) * .045), kind, col, s=.9)
    # chalkboard easel on the right front corner
    for sx in (-1, 1): bar(m, (.52 + sx * .18, .72, -.26), (.52 + sx * .1, 1.3, -.3), .012, dark, 6)
    bar(m, (.34, .95, -.265), (.7, .95, -.265), .01, dark, 6)
    box(m, (.42, .5, .025), (.52, 1.06, -.285), dark, .006, 1); quad(m, .38, .46, (.52, 1.06, -.3), "T_IK_V2_ChalkFlowers")
    # awning posts, striped canopy, festoon bulbs
    for x in (-.62, .62): box(m, (.05, 1.1, .05), (x, 1.02, .32), dark, .012, 2)
    box(m, (1.3, .05, .05), (0, 1.56, .32), dark, .012, 2)
    awning(m, 1.42, .6, 1.58, -.14, "S_E86A9E", 14)
    pergola_lights(m, (-.66, 1.4, -.12), (.66, 1.4, -.12), .05, 8)

# ------------------------------------------------------------------------------------------------- new: vending machine
@model("vending-machine")
def vending_machine(m):
    red = "T_IK_V2_PaintRed"; navy = "T_IK_V2_PaintNavy"
    box(m, (.88, .1, .78), (0, .05, 0), "C_" + DARK, .02)
    box(m, (.9, 1.8, .8), (0, 1.0, .02), red, .03, 3)
    box(m, (.86, .06, .76), (0, 1.9, .02), "C_" + DARK, .012, 2)
    # lit top panel with a bottle + droplet pictogram
    box(m, (.84, .26, .04), (0, 1.7, -.38), "E_FFF1C8", .01, 2)
    lathe(m, [(0, 0), (.035, 0), (.04, .1), (.02, .14), (.018, .18), (.02, .19), (0, .19)], (-.1, 1.6, -.405), "C_" + TEAL, 12)
    prism(m, [(0, -.06), (.035, 0), (0, .06), (-.035, 0)], .012, (.08, 1.7, -.405), "C_" + BLUE)
    cyl(m, .035, .012, (.08, 1.7, -.405), "C_" + BLUE, 14, pitch=-90)
    # fridge door: navy frame, glass, lit interior with 5 shelves of bottles and cans
    box(m, (.62, 1.26, .04), (-.12, 1.0, -.39), navy, .012, 2)
    box(m, (.56, 1.2, .3), (-.12, 1.0, -.2), "C_F4EFE4", .01, 1)
    box(m, (.54, 1.18, .012), (-.12, 1.0, -.39), "G_Glass", .002, 1)
    box(m, (.012, .6, .03), (.14, 1.0, -.4), CHROME, .003, 1)
    cols = ("C_2F1B12", "C_F28C38", "C_5DA637", "C_3E8FD6", "C_F2C23F", "C_D7343A")
    for sh in range(5):
        y = .46 + sh * .24
        box(m, (.52, .02, .28), (-.12, y, -.2), "C_" + CREAM, .004, 1)
        for i in range(6):
            x = -.34 + i * .088; col = cols[(i + sh) % 6]
            if sh < 3:
                lathe(m, [(0, 0), (.028, 0), (.032, .02), (.032, .12), (.02, .15), (.016, .19), (.017, .2), (0, .2)], (x, y + .01, -.26), col, 10)
                cyl(m, .017, .018, (x, y + .2, -.26), "C_" + DARK if i % 2 else "C_F4EFE4", 8)
            else:
                cyl(m, .03, .12, (x, y + .01, -.26), col, 12, .004); cyl(m, .027, .008, (x, y + .13, -.26), CHROME, 12)
    # vending column: display, keypad, coin + bill slots, pick-up flap
    box(m, (.2, .09, .02), (.3, 1.4, -.395), "C_" + DARK, .006, 1); box(m, (.16, .05, .01), (.3, 1.4, -.405), "E_7BD3F7", .003, 1)
    for i in range(3):
        for j in range(4): box(m, (.04, .035, .014), (.26 + i * .045, 1.26 - j * .05, -.4), "C_F4EFE4", .004, 1)
    box(m, (.06, .02, .012), (.3, .98, -.4), "C_" + DARK, .002, 1); box(m, (.12, .04, .012), (.3, .9, -.4), CHROME, .003, 1); box(m, (.08, .008, .014), (.3, .9, -.405), "C_" + DARK, .001, 1)
    cyl(m, .03, .012, (.3, .8, -.4), "C_" + DARK, 12, pitch=-90)
    box(m, (.56, .22, .03), (-.12, .25, -.395), "C_" + DARK, .01, 2); box(m, (.5, .14, .02), (-.12, .25, -.41), navy, .008, 2); bar(m, (-.34, .3, -.425), (.1, .3, -.425), .01, CHROME, 8)
    box(m, (.4, .3, .012), (.0, 1.15, .42), "C_F4EFE4", .004, 1)   # back service panel
    ball(m, (.38, 1.7, -.4), (.03, .03, .02), "E_7CE08A", 8, 5, m.anim("Anim Blink"))

# ------------------------------------------------------------------------------------------------- new: coffee kiosk
@model("coffee-kiosk")
def coffee_kiosk(m):
    wood = PLANKS; dark = "T_IK_R_WoodDark"; marble = "T_IK_Marble"
    box(m, (1.5, .8, .8), (0, .5, 0), wood, .02, 2)
    for y in (.16, .86): box(m, (1.54, .05, .84), (0, y, 0), dark, .012, 1)
    for x in (-.75, .75): box(m, (.06, .84, .84), (x, .5, 0), dark, .012, 1)
    box(m, (1.6, .05, .9), (0, .92, 0), marble, .012, 2)
    box(m, (1.4, .18, .04), (0, .56, -.42), "C_" + NAVY, .01, 1)   # front sign band (plain)
    for sx in (-1, 1):
        torus(m, .22, .03, (sx * .8, .25, .2), dark, roll=90, seg=20, minor=8)
        for i in range(6):
            a = math.radians(i * 60); bar(m, (sx * .8, .25, .2), (sx * .8, .25 + math.cos(a) * .2, .2 + math.sin(a) * .2), .012, dark, 6)
        cyl(m, .045, .05, (sx * .8 - .025, .25, .2), "C_" + DARK, 12, .01, roll=90)
        bar(m, (sx * .5, .18, -.3), (sx * .5, 0, -.3), .02, dark, 8)
    bar(m, (-.8, .25, .2), (.8, .25, .2), .018, "C_" + DARK, 8)
    # espresso machine
    L = Local(m, (-.35, .945, .1))
    box(L, (.6, .36, .44), (0, .18, 0), CHROME, .02, 3); box(L, (.62, .06, .46), (0, .39, 0), "C_" + DARK, .012, 2)
    box(L, (.6, .1, .14), (0, .3, -.3), "C_" + RED, .02, 2); box(L, (.56, .18, .02), (0, .12, -.23), "C_" + DARK, .006, 1)
    for i, x in enumerate((-.16, .16)):
        cyl(L, .045, .04, (x, .16, -.26), CHROME, 14, .006); bar(L, (x, .17, -.26), (x, .12, -.5), .012, "C_" + DARK, 8); ball(L, (x, .12, -.5), (.03, .03, .03), "C_" + DARK, 8, 5)
        lathe(L, [(0, 0), (.028, 0), (.034, .05), (.03, .06), (0, .06)], (x, .02, -.25), "C_F4EFE4", 10)
    bar(L, (.3, .3, -.1), (.42, .1, -.3), .008, CHROME, 6)   # steam wand
    cyl(L, .03, .01, (.0, .32, -.3), "E_7CE08A", 10, pitch=-90); cyl(L, .03, .012, (.1, .32, -.3), "C_" + DARK, 12, pitch=-90)
    for i in range(6): lathe(L, [(0, 0), (.028, 0), (.034, .05), (.03, .06), (0, .06)], (-.22 + i * .09, .42, .05), "C_F4EFE4", 10)
    # grinder, cup stack, pastry dome, napkins
    L2 = Local(m, (.2, .945, .15))
    cyl(L2, .06, .3, (0, 0, 0), "C_" + DARK, 14, .01); lathe(L2, [(.04, 0), (.08, .12), (.075, .13), (0, .13)], (0, .3, 0), "G_Glass", 14)
    box(L2, (.08, .04, .1), (0, .12, -.08), CHROME, .006, 1)
    for i in range(5): lathe(m, [(0, 0), (.035, 0), (.045, .09), (.04, .1), (0, .1)], (.5, .945 + i * .025, .1), "C_F4EFE4", 10)
    ball(m, (.52, .97, -.2), (.3, .22, .3), "G_Glass", 16, 8); cyl(m, .15, .01, (.52, .945, -.2), CHROME, 20)
    for i in range(3): torus_arc(m, .06, .02, (.45 + i * .06, .975, -.22 + (i % 2) * .04), "C_D98E2B", 200, 340, pitch=90, seg=8, minor=5)
    box(m, (.12, .08, .12), (-.6, .99, -.28), "C_F4EFE4", .004, 1); box(m, (.1, .02, .1), (-.6, 1.04, -.28), "C_" + RED, .004, 1)
    # posts, menu chalkboard hanging from the frame, striped awning, festoon bulbs
    for x in (-.72, .72): box(m, (.06, 1.3, .06), (x, 1.55, .38), dark, .012, 2)
    box(m, (1.5, .06, .06), (0, 2.2, .38), dark, .012, 2)
    box(m, (.5, .4, .03), (.45, 1.75, .2), dark, .006, 1); quad(m, .46, .36, (.45, 1.75, .18), "T_IK_V2_ChalkCoffee")
    for x in (.25, .65): bar(m, (x, 2.17, .3), (x, 1.95, .22), .005, "C_" + DARK, 4)
    awning(m, 1.7, .7, 2.22, -.28, "S_D98E2B", 14)
    pergola_lights(m, (-.78, 2.05, -.3), (.78, 2.05, -.3), .06, 9)

# ------------------------------------------------------------------------------------------------- new: photo booth
@model("photo-booth")
def photo_booth(m):
    navy = "T_IK_V2_PaintNavy"; cream = "T_IK_V2_PaintCream"
    box(m, (.96, .08, .96), (0, .04, 0), "C_" + DARK, .02)
    # cabin: closed back + left wall + left third of the front; curtain on the right two thirds
    box(m, (.96, 1.9, .05), (0, 1.03, .455), navy, .02, 2); box(m, (.05, 1.9, .96), (-.455, 1.03, 0), navy, .02, 2)
    box(m, (.05, 1.9, .96), (.455, 1.03, 0), navy, .02, 2)
    box(m, (.34, 1.9, .05), (-.31, 1.03, -.455), cream, .02, 2)
    box(m, (.96, .12, .96), (0, 2.04, 0), navy, .03, 3); box(m, (1.0, .04, 1.0), (0, 2.12, 0), "C_" + GOLD, .012, 2)
    # curtain: pleats (half-cylinders) in red cloth, tied back a little
    for i in range(7):
        x = -.1 + i * .085; r = .035 if i % 2 == 0 else .03
        lathe(m, [(r, 0), (r, 1.52)], (x, .32, -.44), "C_" + RED, 10)
    bar(m, (-.14, 1.86, -.44), (.46, 1.86, -.44), .012, CHROME, 8)
    # inside: bench, screen panel with camera + flash
    box(m, (.86, .06, .3), (0, .5, .3), "C_" + RED, .02, 2); box(m, (.86, .3, .05), (0, .32, .42), "C_" + RED, .02, 2)
    box(m, (.05, .9, .5), (-.42, 1.2, 0), cream, .01, 1)
    box(m, (.04, .5, .44), (-.425, 1.25, .0), "C_" + DARK, .008, 2); box(m, (.012, .3, .38), (-.4, 1.3, 0), "E_7BD3F7", .003, 1)
    cyl(m, .05, .03, (-.4, 1.58, 0), "C_" + DARK, 14, .006, roll=90); cyl(m, .03, .01, (-.385, 1.58, 0), "G_Glass", 12, roll=90)
    box(m, (.02, .1, .14), (-.39, 1.58, .22), "E_FFF7D8", .004, 1)
    # outside front-left panel: sample strip, coin slot, photo slot, camera pictogram sign on the crown
    rounded_panel(m, .26, .66, (-.31, 1.3, -.482), "C_" + GOLD, .012, .03); quad(m, .22, .62, (-.31, 1.3, -.49), "T_IK_V2_PhotoStrip")
    box(m, (.2, .1, .02), (-.31, .82, -.485), CHROME, .006, 1); box(m, (.05, .006, .01), (-.33, .82, -.497), "C_" + DARK, .001, 1); cyl(m, .02, .01, (-.26, .82, -.49), "C_" + DARK, 10, pitch=-90)
    box(m, (.24, .04, .02), (-.31, .62, -.485), "C_" + DARK, .006, 1); box(m, (.2, .01, .022), (-.31, .62, -.49), "C_F4EFE4", .002, 1)
    rounded_panel(m, .6, .18, (0, 2.04, -.49), "C_" + GOLD, .015, .04)
    rounded_panel(m, .18, .11, (-.02, 2.03, -.505), "C_" + NAVY, .012, .02); cyl(m, .035, .012, (-.02, 2.03, -.515), "C_F4EFE4", 14, pitch=-90); cyl(m, .02, .014, (-.02, 2.03, -.52), "C_" + NAVY, 12, pitch=-90)
    box(m, (.05, .03, .012), (.06, 2.085, -.51), "C_" + NAVY, .003, 1)
    for sx in (-1, 1): prism(m, star_pts(.03, .013), .012, (sx * .22, 2.04, -.505), "E_FFE066")
    led_strip(m, -.42, .42, 2.14, -.47, 12, r=.016)

# ------------------------------------------------------------------------------------------------- new: festoon pergola
@model("festoon-pergola")
def festoon_pergola(m):
    wood = "T_IK_R_WoodDark"; W = 1.15; H = 2.45
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(m, (.1, H, .1), (sx * W, H / 2, sz * W), wood, .012, 2); cyl(m, .12, .08, (sx * W, 0, sz * W), "C_9A9A94", 12, .01)
            box(m, (.14, .02, .14), (sx * W, H - .1, sz * W), "C_" + DARK, .004, 1)
    for sz in (-1, 1): box(m, (2.6, .12, .08), (0, H + .04, sz * W), wood, .012, 2)
    for i in range(6): box(m, (.06, .1, 2.5), (-W + .06 + i * (2 * W - .12) / 5, H + .14, 0), wood, .01, 1)
    # festoon strings: three across, two along the beams
    for z in (-.75, 0, .75): pergola_lights(m, (-W, H - .02, z), (W, H - .02, z), .14, 11)
    for sx in (-1, 1): pergola_lights(m, (sx * (W - .05), H - .04, -W), (sx * (W - .05), H - .04, W), .1, 10)
    for i, (x, z) in enumerate(((-.6, -.4), (.5, .3), (0, .75))):   # a few blinking bulbs
        ball(m, (x, H - .2, z), (.06, .08, .06), "E_FFE6A8", 8, 5, m.anim("Anim Blink"))
    # planters at two posts with hedge + flowers, a hanging lantern
    for sx in (-1, 1):
        L = Local(m, (sx * (W - .05), 0, -W + .45))
        box(L, (.5, .36, .4), (0, .18, 0), "T_IK_Terracotta", .02, 2); box(L, (.46, .04, .36), (0, .36, 0), "C_5A3A1E", .006, 1)
        ball(L, (0, .5, 0), (.46, .34, .38), "T_IK_R_Hedge", 12, 8)
        for k, col in enumerate(("C_E15533", "C_F2B03D", "C_E86A9E", "C_F4EFE4")):
            a = k * 1.6; flower(L, (math.cos(a) * .14, .64 + (k % 2) * .03, math.sin(a) * .12), "daisy" if k % 2 else "tulip", col, s=1.1)
    bar(m, (0, H + .02, -W), (0, H - .32, -W), .006, "C_" + DARK, 4); lathe(m, [(0, 0), (.05, 0), (.07, .02), (.07, .12), (.05, .14), (0, .14)], (0, H - .46, -W), "E_FFD98A", 10)

# ------------------------------------------------------------------------------------------------- build / preview
def tri_count(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == "MESH")

def render_views(objs, out_base, tag):
    sc = bpy.context.scene
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    center = (lo + hi) / 2; radius = max((hi - lo).length * .5, .3)
    cam = bpy.data.objects.get("V2_Cam") or bpy.data.objects.new("V2_Cam", bpy.data.cameras.new("V2_Cam"))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    cam.data.type = "PERSP"; cam.data.lens = 45; cam.data.clip_end = 100; sc.camera = cam
    sun = bpy.data.objects.get("V2_Sun") or bpy.data.objects.new("V2_Sun", bpy.data.lights.new("V2_Sun", "SUN"))
    if sun.name not in sc.collection.objects: sc.collection.objects.link(sun)
    sun.data.energy = 2.6; sun.data.angle = math.radians(15); sun.rotation_euler = (math.radians(42), math.radians(8), math.radians(150))
    fill = bpy.data.objects.get("V2_Fill") or bpy.data.objects.new("V2_Fill", bpy.data.lights.new("V2_Fill", "SUN"))
    if fill.name not in sc.collection.objects: sc.collection.objects.link(fill)
    fill.data.energy = .9; fill.rotation_euler = (math.radians(60), 0, math.radians(-40))
    sc.render.engine = "BLENDER_EEVEE"; sc.render.film_transparent = False
    try: sc.eevee.taa_render_samples = 24
    except Exception: pass
    sc.render.resolution_x = sc.render.resolution_y = 800; sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
    if not sc.world: sc.world = bpy.data.worlds.new("V2_World")
    sc.world.use_nodes = True; bg = sc.world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value = (.84, .87, .9, 1); bg.inputs["Strength"].default_value = .8
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = -.1
    outs = []
    for name, az, el, k in (("game", 32, 50, 1.9), ("close", 38, 16, 1.55)):
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
        cam.location = center + d * radius * k * 1.7
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = f"{out_base}_{tag}_{name}.png"; bpy.ops.render.render(write_still=True); outs.append(sc.render.filepath)
    return outs

def render_old(name):
    """The FBX that is in Assets today, re-materialised through the kit's material() by slot name."""
    path = os.path.join(K.UNITY, "Art", "Interior", "Models", name + ".fbx")
    if not os.path.exists(path): return None, 0
    K.clear_scene()
    before = set(bpy.data.materials.keys())
    bpy.ops.import_scene.fbx(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    imported = {mat.name: mat for mat in bpy.data.materials if mat.name not in before}
    keys = {}
    for name, mat in imported.items():
        keys[name] = name.split(".")[0]; mat.name = "old_" + name
    for o in objs:
        for i, mat in enumerate(o.data.materials):
            if mat is None: continue
            key = keys.get(mat.name[4:], mat.name.split(".")[0]) if mat.name.startswith("old_") else mat.name.split(".")[0]
            o.data.materials[i] = K.material(key)
    tris = tri_count(objs)
    render_views(objs, os.path.join(PRE, name), "old")
    return objs, tris

def main(names):
    report = {}
    for name in names:
        t0 = time.time()
        objs_old, tris_old = render_old(name)
        m = Model(name); V2[name](m)
        objs = K.export(m); K.thumbnail(name, objs)
        tris = tri_count(objs)
        render_views(objs, os.path.join(PRE, name), "new")
        lo = Vector((1e9, 1e9, 1e9)); hi = -lo
        for o in objs:
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        size = hi - lo
        report[name] = {"tris_old": tris_old, "tris_new": tris, "footprint_xz_h": [round(size.x, 2), round(size.y, 2), round(size.z, 2)],
                        "objects": [o.name for o in objs], "fbx": os.path.join(K.OUT, name + ".fbx"), "secs": round(time.time() - t0, 1)}
        print("V2DONE " + json.dumps({name: report[name]}), flush=True)
    json.dump(report, open(os.path.join(Q, "report.json"), "w"), indent=1)
    print("ALLDONE", flush=True)

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(args or list(V2))
