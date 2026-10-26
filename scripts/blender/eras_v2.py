"""eras_v2.py - second generation of the first expansion models (Lucas 26/10: the early stages looked unlike the rest
of the game). Same approach, materials and bake as the approved lot ruins (lots_v3.py); built one era at a time and
shown as pictures before anything goes into Assets/.

Run inside Blender (MCP); works from the repo on any machine (paths are derived from this file):

    import sys, importlib; sys.path.insert(0, "<repo>/scripts/blender")
    import eras_v2 as E; importlib.reload(E)
    E.old_era("Era0_Mesinha"); E.render_before("Era0_Mesinha")
    E.build_mesinha(); E.render_era("Era0_Mesinha")          # -> Temp/qa/eras_v2/era0_mesinha_v1_*.png
    E.export_era("Era0_Mesinha")                             # -> Temp/qa/eras_v2/export/Era0_Mesinha.fbx + _BaseColor.png

Conventions (the same as the current Assets/Resources/CheckoutEras/*.fbx, read by CheckoutStall.cs):
  * modelled in metres, front (customers, Unity -Z) facing Blender -Y, ground at z = 0;
  * export_unity(turn=True): FBX -Z forward / Y up, objects turned 180 deg -> Blender (x, y) == Unity model (x, z);
  * one material <EraN_Name>_Mat, the colour baked into <EraN_Name>_BaseColor.png (2048) - CheckoutStall.Load()
    puts it on a Standard material (a material whose name contains "Glass" becomes the see-through glass:
    EraGlass); objects named CUT_* are hidden in the game (roofs / upper walls of the shops), ERA1_Bread* too;
  * the game scales the model by 1.2, centres its renderer bounds on Centre.x and puts their min z on the front
    line; the key points (crates, register, click box) are then fixed offsets from those bounds (see keypoints());
  * no letters or words anywhere (the game is multilingual): signs carry pictograms only.
"""
import bpy, bmesh, math, os, random, sys, importlib
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
UNITY = os.path.join(ROOT, "unity", "CheckoutSimulator")
ART = os.path.join(UNITY, "ArtSource")
SRC = os.path.join(UNITY, "Assets", "Resources", "CheckoutEras")
QA = os.path.join(UNITY, "Temp", "qa", "eras_v2")
EXPORT = os.path.join(QA, "export")
BLEND = os.path.join(ART, "eras_v2", "eras_v2.blend")
for p in (HERE, ART):
    if p not in sys.path: sys.path.insert(0, p)

import checkout_project as cp


def _repath():
    """lots_v3 / checkout_project carry the Windows paths of the PC: point them at this checkout."""
    cp.ROOT = ROOT; cp.UNITY = UNITY; cp.ASSETS = os.path.join(UNITY, "Assets"); cp.ART_SOURCE = ART
    cp.MAP_MODELS = os.path.join(cp.ASSETS, "Art", "Models", "MapModels")
    cp.INTERIOR_MODELS = os.path.join(cp.ASSETS, "Art", "Interior", "Models")
    cp.INTERIOR_TEXTURES = os.path.join(cp.ASSETS, "Art", "Interior", "Textures")
    cp.PREVIEWS = os.path.join(UNITY, "Temp", "qa"); cp.WORKSPACE = os.path.join(ART, "Checkout_Workspace.blend")
    V.ROOT = ROOT; V.UNITY = UNITY; V.ART = ART; V.QA = QA; V.EXPORT = EXPORT
    V.CITY_TREE = os.path.join(UNITY, "Assets", "Art", "Models", "MapModels", "StylizedTree")


import lots_v3 as V
from lots_v3 import G, C, NT, col, show_only, camera, GAME_DIR
_repath()

SCALE = 1.2                                   # CheckoutStall.Scale
CRATE_X = (-1.3, -.65, 0., .65, 1.3)          # CheckoutStall.CrateX


# ================================================================== the current models
def old_era(name):
    """Imports Resources/CheckoutEras/<name>.fbx into 'OLD <name>', turned back into the modelling frame (front -Y),
    with its own baked texture."""
    cname = "OLD " + name
    c = col(cname)
    if c.objects: return c
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(SRC, name + ".fbx"))
    objs = [o for o in bpy.data.objects if o not in before]
    img = bpy.data.images.load(os.path.join(SRC, name + "_BaseColor.png"), check_existing=False)
    img.name = "OLDTEX_" + name
    m = bpy.data.materials.new("OLDMAT_" + name); m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = img
    bs = m.node_tree.nodes["Principled BSDF"]; bs.inputs["Roughness"].default_value = .85
    m.node_tree.links.new(t.outputs["Color"], bs.inputs["Base Color"])
    root = bpy.data.objects.new("OLDROOT_" + name, None); c.objects.link(root)
    for o in objs:
        for cc in list(o.users_collection): cc.objects.unlink(o)
        c.objects.link(o); o.name = "OLD_" + o.name
        if o.parent is None: o.parent = root
        if o.type == 'MESH':
            mats = [mm.name for mm in o.data.materials]
            o.data.materials.clear(); o.data.materials.append(m)
            o["old_mats"] = ",".join(mats)
    root.rotation_euler = (0, 0, math.pi)          # undo export_unity's turn
    bpy.context.view_layer.update()
    return c


def bounds(objs):
    bpy.context.view_layer.update()
    lo = Vector((1e9,) * 3); hi = -lo
    for o in objs:
        if o.type != 'MESH' or o.hide_render: continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co; lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


CUT_SRC = ("CON_shellTop", "CON_awn", "CON_signTop")      # source names that become CUT_* objects in the export


def game_objs(cname):
    """What the game draws of a collection (CUT_* and ERA1_Bread* are switched off by CheckoutStall.Load)."""
    out = []
    for o in bpy.data.collections[cname].all_objects:
        if o.type != 'MESH' or o.hide_render: continue
        n = o.name[4:] if o.name.startswith(("OLD_", "NEW_")) else o.name[2:] if o.name.startswith("X_") else o.name
        if n.startswith("CUT_") or n.startswith("ERA1_Bread") or n.startswith(CUT_SRC): continue
        out.append(o)
    return out


def keypoints(lo, hi):
    """CheckoutStall's points for a stall era (0-3), in model metres (modelling frame), from the model's bounds:
    Place(): bounds centre x on Centre.x, bounds min z (Unity) on FrontLine; Centre.z = FrontLine + 1.4; y = .1."""
    cx = (lo.x + hi.x) / 2; fy = lo.y
    crates = [Vector((cx + k, fy + 1.0 / SCALE, (1.1 - .1) / SCALE)) for k in CRATE_X]
    register = Vector((cx + 1.1 / SCALE, fy + .8 / SCALE, (.9 - .1) / SCALE))
    click = Vector((1.25, -.6, .8))              # 'Stall checkout' collider, model-local (size 1.2 x 1.6 x 1.2)
    approach = [Vector((p.x, fy - .85 / SCALE, 0)) for p in crates]   # where the shoppers stand (FrontZ)
    queue0 = Vector((cx + 1.9 / SCALE, fy + (-.85 - .1) / SCALE, 0))
    return {"cx": cx, "front": fy, "crates": crates, "register": register, "click": click, "approach": approach,
            "queue0": queue0, "size": hi - lo}


def report(cname):
    lo, hi = bounds(game_objs(cname))
    k = keypoints(lo, hi)
    r = lambda v: [round(x, 3) for x in v]
    return {"lo": r(lo), "hi": r(hi), "size": r(hi - lo), "cx": round(k["cx"], 3), "front": round(k["front"], 3),
            "crates": [r(p) for p in k["crates"]], "register": r(k["register"]),
            "tris": sum(len(o.data.loop_triangles) if o.data.loop_triangles else sum(len(p.vertices) - 2 for p in o.data.polygons)
                        for o in game_objs(cname))}


# ================================================================== stage, cameras, renders
def stage():
    """Light pavers like the sidewalk / lot A1 paving around the stalls, the lots' soft sun."""
    c = col("Stage")
    for o in list(c.objects):
        if o.type == 'MESH': bpy.data.objects.remove(o)
    cp.studio()
    sc = bpy.context.scene
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (.80, .84, .86, 1)
    sun = bpy.data.objects["Studio Sun"]
    sun.data.energy = 3.6
    sun.rotation_euler = (math.radians(48), math.radians(0), math.radians(35))
    import era_kit as k
    pav = k.pavers("ERA_Pavers")
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -.002))
    g = bpy.context.active_object; g.name = "STAGE_Pavers"; g.scale = (60, 60, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    g.data.materials.append(pav); k.link(g, c)
    sc.render.engine = "BLENDER_EEVEE"
    try:
        sc.eevee.use_shadows = True; sc.eevee.use_raytracing = True; sc.eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = -.1
    return c


def render(name):
    os.makedirs(QA, exist_ok=True)
    sc = bpy.context.scene
    sc.render.filepath = os.path.join(QA, name + ".png")
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


def frame(cname, view="iso", pad=1.25, res=(1600, 1100)):
    """Camera on a collection: 'iso' = the game camera direction (ortho), 'close' = closer 3/4 perspective-like
    ortho from lower down, 'top' = straight down."""
    lo, hi = bounds(game_objs(cname))
    c = (lo + hi) / 2; s = hi - lo
    if view == "iso":
        camera((c.x, c.y, c.z * .8), max(s.x, s.y, s.z) * 1.9 * pad, GAME_DIR, res=res)
    elif view == "close":
        camera((c.x + s.x * .08, c.y, c.z * .75), max(s.x, s.y) * 1.25 * pad, Vector((.75, -1.25, .62)), res=res)
    elif view == "top":
        camera((c.x, c.y, 0), max(s.x, s.y) * 1.55 * pad, Vector((0, -.0001, 1)), res=(1400, 1400))
    elif view == "front":
        camera((c.x, c.y, c.z), max(s.x, s.z) * 1.4 * pad, Vector((0, -1, .2)), res=res)


# ------------------------------------------------------------------ key-point markers for the top views
def _emit(name, rgb):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        if n.bl_idname != "ShaderNodeOutputMaterial": nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Color"].default_value = rgb; e.inputs["Strength"].default_value = 1.0
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


def _outline(g, x0, y0, x1, y1, z, w=.025):
    g.box((x1 - x0 + w, w, w), ((x0 + x1) / 2, y0, z)); g.box((x1 - x0 + w, w, w), ((x0 + x1) / 2, y1, z))
    g.box((w, y1 - y0 + w, w), (x0, (y0 + y1) / 2, z)); g.box((w, y1 - y0 + w, w), (x1, (y0 + y1) / 2, z))


def markers(cname, old=None, tag="MK"):
    """Small coloured markers for the code's key points over the model (on top of everything for the top view):
    orange discs = crate points (1.1 m world), red = register point, magenta box = click collider, cyan line = front
    line, white rect = this model's bounds, yellow rect = the old model's bounds, blue dots = where shoppers stand."""
    mc = col("Markers")
    for o in list(mc.objects): bpy.data.objects.remove(o)
    lo, hi = bounds(game_objs(cname)); k = keypoints(lo, hi)
    top = hi.z + .2
    g = G(tag + "_crates", _emit("MK_Orange", (1, .45, 0, 1)), mc, smooth=False)
    for p in k["crates"]:
        g.cyl(.075, .02, (p.x, p.y, top), verts=20); g.cyl(.02, p.z, (p.x, p.y, p.z / 2), verts=6)
    g.done()
    g = G(tag + "_shoppers", _emit("MK_Blue", (.1, .35, 1, 1)), mc, smooth=False)
    for p in k["approach"]: g.cyl(.06, .02, (p.x, p.y, top), verts=12)
    g.cyl(.06, .02, (k["queue0"].x, k["queue0"].y, top), verts=4)
    g.done()
    g = G(tag + "_register", _emit("MK_Red", (1, .05, .1, 1)), mc, smooth=False)
    r = k["register"]; g.box((.12, .12, .02), (r.x, r.y, top)); g.cyl(.02, r.z, (r.x, r.y, r.z / 2), verts=6); g.done()
    g = G(tag + "_click", _emit("MK_Magenta", (1, .1, 1, 1)), mc, smooth=False)
    cl = k["click"]; _outline(g, cl.x - .6, cl.y - .6, cl.x + .6, cl.y + .6, top, .015); g.done()
    g = G(tag + "_front", _emit("MK_Cyan", (0, .9, 1, 1)), mc, smooth=False)
    g.box((8, .02, .02), (k["cx"], k["front"], .01)); g.done()
    g = G(tag + "_bounds", _emit("MK_White", (1, 1, 1, 1)), mc, smooth=False)
    _outline(g, lo.x, lo.y, hi.x, hi.y, .012, .02); g.done()
    if old:
        olo, ohi = bounds(game_objs(old))
        # the old model placed like the game places it: same centre x, same front line
        dx = k["cx"] - (olo.x + ohi.x) / 2; dy = k["front"] - olo.y
        g = G(tag + "_oldbounds", _emit("MK_Yellow", (1, .9, 0, 1)), mc, smooth=False)
        _outline(g, olo.x + dx, olo.y + dy, ohi.x + dx, ohi.y + dy, .02, .015); g.done()
    return k


def game_hidden(cname):
    """Objects the game switches off (CUT_* roofs / upper walls, ERA1_Bread*)."""
    out = []
    for o in bpy.data.collections[cname].all_objects:
        n = o.name[4:] if o.name.startswith(("OLD_", "NEW_")) else o.name
        if n.startswith("CUT_") or n.startswith("ERA1_Bread") or n.startswith(CUT_SRC): out.append(o)
    return out


def render_before(name):
    """<era>_before.png (game angle, as the game shows it: CUT_* parts off), _before_full.png when the model has
    CUT_ parts, and <era>_before_top.png (top, with the key points)."""
    old_era(name); stage(); stage_pavers()
    tag = name.split("_")[0].lower() + "_" + name.split("_")[1].lower()
    cname = "OLD " + name
    show_only(cname)
    hid = game_hidden(cname)
    out = []
    if hid:
        frame(cname, "iso"); out.append(render(tag + "_before_full"))
    for o in hid: o.hide_render = True
    try:
        frame(cname, "iso"); out.append(render(tag + "_before"))
        markers(cname)
        show_only(cname, "Markers")
        top_camera(cname); out.append(render(tag + "_before_top"))
    finally:
        for o in hid: o.hide_render = False
    return out


# ================================================================== materials (lots_v3 node style: clean paint, crisp wear)
EM = {}


def m_gingham(name, a=C("FBF3E1"), b=C("2FA597"), w=.075):
    """Picnic gingham: woven teal checks on cream, mapped per face direction (top: x/y, front: x/z, sides: y/z)."""
    t = NT(name, .9)
    p = t.pos; n = t.geo.outputs["Normal"]
    ax = t.ramp(t.math('ABSOLUTE', t.comp(n, "X")), .55, .65)
    ay = t.ramp(t.math('ABSOLUTE', t.comp(n, "Y")), .55, .65)
    x, y, z = t.comp(p, "X"), t.comp(p, "Y"), t.comp(p, "Z")
    U = t.math('ADD', t.math('MULTIPLY', x, t.math('SUBTRACT', 1.0, ax)), t.math('MULTIPLY', y, ax))
    side = t.math('MAXIMUM', ax, ay)
    V = t.math('ADD', t.math('MULTIPLY', y, t.math('SUBTRACT', 1.0, side)), t.math('MULTIPLY', z, side))
    A = t.ramp(t.math('FRACT', t.math('DIVIDE', U, w)), .49, .51)
    B = t.ramp(t.math('FRACT', t.math('DIVIDE', V, w)), .49, .51)
    half = t.math('ADD', A, B)                                        # 0 cream, 1 light teal, 2 teal
    light = (a[0] * .45 + b[0] * .55, a[1] * .45 + b[1] * .55, a[2] * .45 + b[2] * .55, 1)
    col = t.mix(a, light, t.ramp(half, .5, .6))
    col = t.mix(col, b, t.ramp(half, 1.5, 1.6))
    col = t.mul(col, t.ramp(t.noise(p, 40, 2, .5), .3, .7, .95, 1.03))         # weave grain
    return t.done(col, t.noise(p, 60, 2), .08, ao=.45, ao_dist=.3)


def m_canvas(name, col, var=.05):
    """Parasol / tent canvas: clean colour, faint weave, slightly lighter towards the sun-facing top."""
    t = NT(name, .85)
    p = t.pos
    c = t.mul(col, t.ramp(t.noise(p, 1.2, 2, .4), .3, .7, 1 - var, 1 + var))
    c = t.mul(c, t.ramp(t.noise(t.scale(p, 1, 1, 1), 55, 2, .5), .3, .7, .96, 1.03))
    c = t.mul(c, t.ramp(t.comp(t.geo.outputs["Normal"], "Z"), -.2, .9, .86, 1.04))
    return t.done(c, ao=.35, ao_dist=.4)


def mats_era():
    V.mats()
    EM.clear()
    EM["pine"] = V.m_wood("E2_Pine", C("EDCB91"), C("D2A468"), C("D9BE92"), rough=.8)
    EM["wood"] = V.m_wood("E2_Wood", C("C98E55"), C("A8703F"), C("B49372"), rough=.8)
    EM["teal"] = V.m_paint_wood("E2_TealPaint", C("23A08D"), C("C9A170"), .18)
    EM["orangeP"] = V.m_paint_wood("E2_OrangePaint", C("F08A2C"), C("C9A170"), .15)
    EM["cream"] = V.m_paint_wood("E2_CreamPaint", C("F6ECD4"), C("C9A170"), .15)
    EM["gingham"] = m_gingham("E2_Gingham")
    EM["canA"] = m_canvas("E2_CanvasTeal", C("1FA392"))
    EM["canB"] = m_canvas("E2_CanvasCream", C("FBF1DB"), .03)
    EM["canO"] = m_canvas("E2_CanvasOrange", C("F28A2E"))
    EM["pole"] = V.m_flat("E2_Pole", C("F2EEE4"), .03, 4, .4, ao=.3)
    EM["metalT"] = V.m_metal_paint("E2_CashTin", C("2F9C8C"), amount=.15)
    EM["bucket"] = V.m_flat("E2_Bucket", C("F28A2E"), .05, 5, .5, ao=.35)
    EM["concrete"] = V.m_flat("E2_ConcreteTop", C("BDB5A6"), .1, 12, .9, ao=.5)
    EM["styro"] = V.m_flat("E2_Styro", C("F3F1EA"), .02, 6, .9, ao=0)      # (no painted AO: its bake noise speckled the white)
    EM["board"] = V.m_flat("E2_Chalkboard", C("2E4F46"), .06, 3, .85, ao=.3)
    EM["chalk"] = V.m_flat("E2_ChalkLine", C("F4EFE4"), .05, 9, .9, ao=0)
    EM["card"] = V.m_flat("E2_Cardboard", C("C99A62"), .08, 6, .9, ao=.5)
    # produce and small flat-colour bits (swatch cells)
    EM["tomato"] = V.m_flat("E2_Tomato", C("E43B2C"), .06, 9, .35, island=.08, ao=.15)
    EM["orange"] = V.m_flat("E2_OrangeFruit", C("F7962A"), .06, 14, .45, island=.07, ao=.15)
    EM["lime"] = V.m_flat("E2_Lime", C("7DBB38"), .06, 14, .45, island=.08, ao=.15)
    EM["apple"] = V.m_flat("E2_Apple", C("D93436"), .07, 9, .35, island=.1, ao=.15)
    EM["banana"] = V.m_flat("E2_Banana", C("F8D748"), .05, 8, .5, island=.05, ao=.15)
    EM["stem"] = V.m_flat("E2_Stem", C("4F8B2D"), .06, 9, .7, ao=0)
    EM["brown"] = V.m_flat("E2_StemBrown", C("6B4A2B"), .05, 9, .8, ao=0)
    EM["melonD"] = V.m_flat("E2_MelonDark", C("2F6B2B"), .06, 9, .5, ao=.15)
    EM["melonL"] = V.m_flat("E2_MelonLight", C("8DC257"), .05, 9, .5, ao=.15)
    EM["ice"] = V.m_flat("E2_Ice", C("DDF2FA"), .04, 9, .2, ao=.2)
    EM["canR"] = V.m_flat("E2_CanRed", C("E2453A"), .03, 9, .35, ao=.1)
    EM["canT"] = V.m_flat("E2_CanTeal", C("27A795"), .03, 9, .35, ao=.1)
    EM["canY"] = V.m_flat("E2_CanYellow", C("F5C437"), .03, 9, .35, ao=.1)
    EM["alu"] = V.m_flat("E2_Alu", C("CDD2D6"), .03, 9, .3, ao=.1)
    EM["bottle"] = V.m_flat("E2_BottleGreen", C("4DAE6A"), .04, 9, .2, ao=.1)
    EM["cap"] = V.m_flat("E2_Cap", C("F04E3C"), .03, 9, .4, ao=0)
    EM["dark"] = V.m_flat("E2_Dark", C("3B302B"), .04, 3, .9, ao=0)
    EM["coin"] = V.m_flat("E2_Coin", C("E7C35A"), .05, 9, .3, ao=0)
    EM["note"] = V.m_flat("E2_Note", C("8FCB9B"), .05, 9, .8, ao=0)
    EM["rubber"] = V.m_flat("E2_Rubber", C("3C3B40"), .05, 8, .8, ao=.2)
    # tenda
    EM["frame"] = V.m_flat("E2_Frame", C("EEF0EE"), .03, 4, .4, ao=.35)
    EM["sand"] = V.m_flat("E2_Sandbag", C("D8C39A"), .06, 7, .9, island=.06, ao=.45)
    EM["pepper"] = V.m_flat("E2_PepperY", C("F6C431"), .05, 9, .3, island=.06, ao=.15)
    EM["potato"] = V.m_flat("E2_Potato", C("C9975E"), .1, 12, .9, island=.1, ao=.2)
    EM["onion"] = V.m_flat("E2_Onion", C("9C3B6B"), .06, 9, .5, island=.08, ao=.15)
    EM["carrot"] = V.m_flat("E2_Carrot", C("F37A22"), .05, 9, .6, island=.05, ao=.15)
    EM["bulb"] = V.m_flat("E2_Bulb", C("FFF1C2"), .02, 9, .2, ao=0)
    EM["cord"] = V.m_flat("E2_Cord", C("3B3A3A"), .02, 9, .6, ao=0)
    EM["regBody"] = V.m_metal_paint("E2_RegBody", C("2A9C8C"), amount=.12)
    EM["regKey"] = V.m_flat("E2_RegKey", C("F7EEDB"), .03, 9, .4, ao=.2)
    EM["coolerT"] = V.m_flat("E2_CoolerTeal", C("1F9C8B"), .03, 5, .45, ao=.45)
    EM["coolerW"] = V.m_flat("E2_CoolerWhite", C("F2EFE6"), .02, 5, .5, ao=0)
    EM["burlap"] = V.m_flat("E2_Burlap", C("BE9A64"), .08, 25, .95, ao=.4)
    EM["pot"] = V.m_flat("E2_Terracotta", C("D9774A"), .05, 8, .8, ao=.4)
    return EM


# flat-colour parts: one swatch square each (lots_v3 make_export reads V.SWATCH)
SWATCH = ["E2_Tomato", "E2_OrangeFruit", "E2_Lime", "E2_Apple", "E2_Banana", "E2_Stem", "E2_StemBrown", "E2_MelonDark",
          "E2_MelonLight", "E2_Ice", "E2_CanRed", "E2_CanTeal", "E2_CanYellow", "E2_Alu", "E2_BottleGreen", "E2_Cap",
          "E2_Dark", "E2_Coin", "E2_Note", "E2_Rubber", "E2_ChalkLine", "E2_Pole", "E2_ConcreteTop", "E2_Frame",
          "E2_PepperY", "E2_Potato", "E2_Onion", "E2_Carrot", "E2_Bulb", "E2_Cord", "E2_RegKey", "E2_Terracotta"]
# (big flat-colour parts - ice boxes, cardboard, sandbags, sack, bucket - are packed like the painted ones, so their
#  painted AO bakes per face instead of smearing in one shared swatch cell)
TEXEL = {"E2_Gingham": 2.4, "E2_CanvasTeal": 1.5, "E2_CanvasCream": 1.5, "E2_CanvasOrange": 1.4, "E2_Pine": 1.3,
         "E2_Wood": 1.1, "E2_TealPaint": 1.0, "E2_OrangePaint": 1.0, "E2_CreamPaint": 1.0, "E2_CashTin": 1.2,
         "E2_Chalkboard": 1.4, "E2_Styro": .8, "E2_CoolerTeal": .9, "E2_CoolerWhite": .8, "E2_Cardboard": .6,
         "E2_Sandbag": .6, "E2_Burlap": .6, "E2_Bucket": .6}


# ================================================================== geometry helpers
def sweep(g, pts, radii, verts=6, closed_ends=True, M=None, roll=0.):
    """Tube along a polyline with per-point radius (bananas, ribs, stems): rings + quads, capped ends."""
    pts = [Vector(p) for p in pts]; rings = []; allv = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < .9 else Vector((1, 0, 0))
        a = d.cross(up).normalized(); b = d.cross(a).normalized()
        ring = []
        for k in range(verts):
            t = 2 * math.pi * k / verts + roll
            v = g.bm.verts.new(p + (a * math.cos(t) + b * math.sin(t)) * radii[i]); ring.append(v); allv.append(v)
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(verts):
            g.bm.faces.new((A[k], A[(k + 1) % verts], B[(k + 1) % verts], B[k]))
    if closed_ends:
        g.bm.faces.new(list(reversed(rings[0]))); g.bm.faces.new(rings[-1])
    g._put(allv, M or Matrix.Identity(4))
    return g


def ellipsoid(g, c, r, sectors=12, rings=8, M=None, pick=None):
    """UV ellipsoid (radii r = (rx, ry, rz)) whose long axis is X; pick(i) -> keep longitudinal sector i
    (watermelon stripes are two meshes built from alternate sectors)."""
    allv = []
    for i in range(sectors):
        if pick and not pick(i): continue
        a0, a1 = 2 * math.pi * i / sectors, 2 * math.pi * (i + 1) / sectors
        grid = []
        for j in range(rings + 1):
            th = math.pi * j / rings
            row = []
            for a in (a0, a1):
                p = Vector((c[0] - r[0] * math.cos(th), c[1] + r[1] * math.sin(th) * math.cos(a), c[2] + r[2] * math.sin(th) * math.sin(a)))
                v = g.bm.verts.new(p); row.append(v); allv.append(v)
            grid.append(row)
        for j in range(rings):
            q = (grid[j][0], grid[j][1], grid[j + 1][1], grid[j + 1][0])
            g.bm.faces.new(q)
    g._put(allv, M or Matrix.Identity(4))
    return g


def crate_rect(g, M0, w=.42, d=.32, h=.2, slats=2, post=.035, t=.016):
    """Open fruit crate (feira style): slatted sides with gaps, corner posts, slatted bottom; base at z=0."""
    sh = (h - .01) / (slats * 1.45)
    for k in range(slats):
        z = .012 + sh / 2 + k * sh * 1.45
        for sy in (-1, 1): g.box((w - .004, t, sh), (0, sy * (d / 2 - t / 2), z), M=M0)
        for sx in (-1, 1): g.box((t, d - 2 * t - .002, sh), (sx * (w / 2 - t / 2), 0, z), M=M0)
    for sx in (-1, 1):
        for sy in (-1, 1): g.box((post, post, h), (sx * (w / 2 - post / 2 - t * .4), sy * (d / 2 - post / 2 - t * .4), h / 2), M=M0)
    n = 4
    for k in range(n):
        g.box((w - 2 * t, d / n - .012, .012), (0, -d / 2 + t * .2 + (k + .5) * (d - t * .4) / n, .006), M=M0)
    return g


def produce(g, M0, w, d, z0, r, seed, mound=.035, scale=(1, 1, 1), subs=(1, 2, 2), g_low=None, layers=3):
    """Fills a crate's inside (w x d, floor z0) with a heap of fruit: a full bottom layer, then smaller layers
    nested in the hollows (the bottom one coarser, it is mostly hidden). Neighbours may touch, the crate is never
    touched (wall margin = stretched radius + jitter). Returns the upper fruits' (centre, half height) for stems."""
    rnd = random.Random(seed); tops = []
    rx, ry = r * scale[0] * 1.05 + .005, r * scale[1] * 1.05 + .005
    px, py = 2 * r * scale[0] * .99, 2 * r * scale[1] * .99
    nx0 = max(1, int((w - 2 * rx) / px) + 1); ny0 = max(1, int((d - 2 * ry) / py) + 1)
    sx = (w - 2 * rx) / max(1, nx0 - 1) if nx0 > 1 else 0; sy = (d - 2 * ry) / max(1, ny0 - 1) if ny0 > 1 else 0
    for layer in range(layers):
        nx, ny = max(1, nx0 - layer), max(1, ny0 - layer)
        if layer and nx0 - layer < 1 and ny0 - layer < 1: break
        for i in range(nx):
            for j in range(ny):
                u = (i - (nx - 1) / 2) * sx; v = (j - (ny - 1) / 2) * sy
                z = z0 + r * scale[2] * (1 + 1.3 * layer)
                if layer == layers - 1: z += mound * .3
                p = Vector((u + rnd.uniform(-.004, .004), v + rnd.uniform(-.004, .004), z))
                k = rnd.uniform(.93, 1.04) if layer else .97
                gg = g if layer or g_low is None else g_low
                gg.ball(r * k, p, scale=scale, rot=(rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), rnd.uniform(0, 6.3)), sub=subs[min(layer, len(subs) - 1)], M=M0)
                if layer: tops.append((M0 @ p, r * k * scale[2]))
    return tops


def banana_bunch(g, gs, M0, n=5, L=.2, seed=0):
    """A hand of bananas: n curved five-sided fingers from one crown, lying on its side; gs gets the dark tips."""
    rnd = random.Random(seed)
    crown = Vector((0, 0, .03))
    for k in range(n):
        a = (k - (n - 1) / 2) * .2
        pts = []; radii = []
        for s in range(9):
            t = s / 8
            ang = a + rnd.uniform(-.02, .02)
            x = math.cos(ang) * t * L; y = math.sin(ang) * t * L
            z = .03 + .055 * math.sin(math.pi * t * .9) + (k % 2) * .012 - .02 * t
            pts.append(crown + Vector((x, y, z - .03)))
            radii.append(.0185 * (.45 + .55 * math.sin(math.pi * min(1, .12 + t * .95))))
        sweep(g, pts, radii, verts=5, M=M0)
        tip = pts[-1]; d = (pts[-1] - pts[-2]).normalized()
        gs.tube(M0 @ (tip - d * .002), M0 @ (tip + d * .012), .006, verts=5)
    gs.cyl(.017, .05, (0, 0, 0), rot=(0, math.pi / 2, 0), verts=6, M=M0 @ Matrix.Translation((-.02, 0, .03)))


def skirt(g, x0, x1, y0, y1, ztop, zbot, rc=.04, amp=.01, pitch=.11, thick=.008):
    """Hanging tablecloth skirt: a closed loop around a rounded rectangle, gently waved, with a hem."""
    loop = []
    w, d = x1 - x0, y1 - y0
    per = 2 * (w + d - 4 * rc) + 2 * math.pi * rc
    n = max(24, int(per / (pitch / 4)))
    for i in range(n):
        s = per * i / n
        # walk: bottom edge (y0), right corner, right edge, ...
        segs = [(w - 2 * rc, 'S'), (math.pi * rc / 2, 'C1'), (d - 2 * rc, 'E'), (math.pi * rc / 2, 'C2'),
                (w - 2 * rc, 'N'), (math.pi * rc / 2, 'C3'), (d - 2 * rc, 'W'), (math.pi * rc / 2, 'C4')]
        acc = s
        for L, kind in segs:
            if acc <= L or kind == 'C4': break
            acc -= L
        if kind == 'S': p, nrm = Vector((x0 + rc + acc, y0)), Vector((0, -1))
        elif kind == 'E': p, nrm = Vector((x1, y0 + rc + acc)), Vector((1, 0))
        elif kind == 'N': p, nrm = Vector((x1 - rc - acc, y1)), Vector((0, 1))
        elif kind == 'W': p, nrm = Vector((x0, y1 - rc - acc)), Vector((-1, 0))
        else:
            cc = {'C1': (x1 - rc, y0 + rc, -math.pi / 2), 'C2': (x1 - rc, y1 - rc, 0), 'C3': (x0 + rc, y1 - rc, math.pi / 2), 'C4': (x0 + rc, y0 + rc, math.pi)}[kind]
            a = cc[2] + acc / rc
            nrm = Vector((math.cos(a), math.sin(a))); p = Vector((cc[0], cc[1])) + nrm * rc
        loop.append((p, nrm, s))
    rows = []
    zs = [ztop, ztop - (ztop - zbot) * .5, zbot + .012, zbot]
    for zi, z in enumerate(zs):
        f = zi / (len(zs) - 1)
        outer, inner = [], []
        for p, nrm, s in loop:
            wv = amp * f * math.sin(2 * math.pi * s / pitch)
            o = p + nrm * (wv + .004 + .006 * f + (.004 if zi == 2 else 0))
            outer.append(g.bm.verts.new((o.x, o.y, z)))
            ii = o - nrm * thick
            inner.append(g.bm.verts.new((ii.x, ii.y, z)))
        rows.append((outer, inner))
    m = len(loop)
    for r in range(len(rows) - 1):
        (oa, ia), (ob, ib) = rows[r], rows[r + 1]
        for i in range(m):
            j = (i + 1) % m
            g.bm.faces.new((oa[i], ob[i], ob[j], oa[j]))
            g.bm.faces.new((ia[j], ib[j], ib[i], ia[i]))
    ob, ib = rows[-1]
    for i in range(m):
        j = (i + 1) % m
        g.bm.faces.new((ob[j], ob[i], ib[i], ib[j]))
    return g


def canopy(gs, gtrim, apex, R, H, n=8, drop=.42, sag=.035, valance=.085, thick=.014, start=0., rib_g=None):
    """Market parasol canopy: n panels (alternating gs[0] / gs[1]) that sag between the ribs, a scalloped valance
    per panel, orange piping along the rim (gtrim), ribs + tips underneath (rib_g)."""
    NR, NA = 7, 7
    cx, cy, cz = apex
    def surf(r, ph, k0):
        t = (ph - k0) / (2 * math.pi / n)
        z = cz - drop * (r / R) ** 1.35 - sag * (r / R) * math.sin(math.pi * t)
        rr = r * (1 - .03 * math.sin(math.pi * t))
        return Vector((cx + rr * math.cos(ph), cy + rr * math.sin(ph), z))
    for k in range(n):
        g = gs[k % 2]
        k0 = start + 2 * math.pi * k / n; k1 = start + 2 * math.pi * (k + 1) / n
        top = []; bot = []
        for i in range(NR + 1):
            r = R * (i / NR) ** .9
            rt, rb = [], []
            for j in range(NA + 1):
                ph = k0 + (k1 - k0) * j / NA
                p = surf(max(r, .001), ph, k0)
                rt.append(g.bm.verts.new(p)); rb.append(g.bm.verts.new(p - Vector((0, 0, thick))))
            top.append(rt); bot.append(rb)
        for i in range(NR):
            for j in range(NA):
                g.bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
                g.bm.faces.new((bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j], bot[i][j]))
        # valance flap hanging from the rim, scalloped hem
        rim_t = top[NR]; rim_b = bot[NR]
        hem_o, hem_i = [], []
        for j in range(NA + 1):
            t = j / NA
            p = rim_t[j].co.copy(); out = Vector((p.x - cx, p.y - cy, 0)).normalized()
            depth = valance * (.55 + .45 * math.sin(math.pi * t))
            hem_o.append(g.bm.verts.new(p + out * .006 - Vector((0, 0, depth))))
            hem_i.append(g.bm.verts.new(p + out * (.006 - thick * .7) - Vector((0, 0, depth))))
        for j in range(NA):
            g.bm.faces.new((rim_t[j], rim_t[j + 1], hem_o[j + 1], hem_o[j]))
            g.bm.faces.new((rim_b[j + 1], rim_b[j], hem_i[j], hem_i[j + 1]))
            g.bm.faces.new((hem_o[j], hem_o[j + 1], hem_i[j + 1], hem_i[j]))
        # piping along the rim
        pts = [surf(R, k0 + (k1 - k0) * j / NA, k0) + Vector((0, 0, -.004)) for j in range(NA + 1)]
        pts = [p + Vector((p.x - cx, p.y - cy, 0)).normalized() * .006 for p in pts]
        sweep(gtrim, pts, [.011] * len(pts), verts=5, closed_ends=True)
        if rib_g is not None:
            rp = [surf(R * f, k0, k0) - Vector((0, 0, thick + .008)) for f in (.05, .3, .55, .8, 1.0)]
            sweep(rib_g, rp, [.007] * len(rp), verts=4)
            tip = surf(R, k0, k0) + Vector((math.cos(k0), math.sin(k0), 0)) * .02 - Vector((0, 0, .01))
            gtrim.ball(.018, tip, sub=1)


def _T(x, y, z=0., rz=0., rx=0., ry=0.):
    return Matrix.Translation((x, y, z)) @ Euler((rx, ry, rz)).to_matrix().to_4x4()


def stems(g, tops, h=.012, r=.006):
    for p, hz in tops:
        g.cyl(r, h, p + Vector((0, 0, hz + h * .3)), verts=5)


def tag(gc, gp, M0):
    """Blank price card hung on the crate's front slat (the game writes prices on screen, never on the art).
    M0: crate frame at the outer face of the front slat, z = top of the crate."""
    gc.box((.075, .004, .052), (0, -.006, -.012), rot=(.06, 0, 0), M=M0)


def cash_tin(gm, gd, gcoin, gnote, M0, w=.26, d=.18, h=.075, lid=1.1):
    """Little painted metal cash box, lid open towards the back, coin tray and a few notes inside."""
    t = .008
    gm.box((w, d, t), (0, 0, t / 2), M=M0)
    for sy in (-1, 1): gm.box((w, t, h), (0, sy * (d / 2 - t / 2), h / 2), M=M0)
    for sx in (-1, 1): gm.box((t, d - 2 * t, h), (sx * (w / 2 - t / 2), 0, h / 2), M=M0)
    Ml = M0 @ Matrix.Translation((0, d / 2, h)) @ Matrix.Rotation(-lid, 4, 'X')
    gm.box((w + .006, d + .006, t), (0, -d / 2, t / 2), M=Ml)
    gm.box((w + .006, t, .02), (0, -d - .003 + t / 2, .01 + t / 2), M=Ml)
    gm.box((.06, .012, .012), (0, -d - .012, .004), M=Ml)                       # handle
    for k in range(4):                                                           # coin tray dividers
        gd.box((t * .6, d * .45, h * .55), (-w / 2 + (k + 1) * w / 5 - .001, -d * .2, h * .3), M=M0)
    rnd = random.Random(5)
    for k in range(5):
        for c in range(3):
            gcoin.cyl(.012, .004, (-w / 2 + (k + .5) * w / 5 + rnd.uniform(-.006, .006), -d * .2 + rnd.uniform(-.02, .02), .012 + c * .005), verts=10, M=M0)
    for k in range(3):
        gnote.box((.2, .075, .004), (rnd.uniform(-.01, .01), d * .27, .014 + k * .005), rot=(0, 0, rnd.uniform(-.08, .08)), M=M0)


def cooler(g, glid, gice, gcans, M0, w=.56, d=.38, h=.36, t=.035, lid_at=None, seed=3):
    """Styrofoam ice box (open), ice and drinks inside; its lid leaning on the right side."""
    g.box((w, d, t), (0, 0, t / 2), M=M0)
    for sy in (-1, 1): g.box((w, t, h), (0, sy * (d / 2 - t / 2), h / 2), M=M0)
    for sx in (-1, 1): g.box((t, d - 2 * t + .002, h), (sx * (w / 2 - t / 2), 0, h / 2), M=M0)
    iw, idp = w - 2 * t - .006, d - 2 * t - .006
    gice.box((iw, idp, .2), (0, 0, t + .1), M=M0)
    rnd = random.Random(seed)
    for k in range(16):
        s = rnd.uniform(.03, .045)
        gice.box((s, s, s), (rnd.uniform(-iw / 2 + .03, iw / 2 - .03), rnd.uniform(-idp / 2 + .03, idp / 2 - .03), t + .2 + rnd.uniform(-.005, .01)),
                 rot=(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3)), M=M0)
    cans = gcans
    spots = [(-.17, -.07, 'canR'), (-.09, .06, 'canT'), (-.01, -.06, 'canY'), (.07, .07, 'canR'), (.15, -.05, 'canT')]
    for x, y, m in spots:
        cans[m].cyl(.033, .12, (x, y, t + .17 + .06), verts=14, M=M0 @ Matrix.Rotation(rnd.uniform(-.12, .12), 4, 'X'))
        cans["alu"].cyl(.029, .006, (x, y, t + .17 + .123), verts=14, M=M0 @ Matrix.Rotation(rnd.uniform(-.0, .0), 4, 'X'))
    for x, y in ((.02, .1), (-.2, .1)):
        Mb = M0 @ Matrix.Translation((x, y, t + .14)) @ Matrix.Rotation(rnd.uniform(-.15, .15), 4, 'Y')
        cans["bottle"].cyl(.034, .16, (0, 0, .08), verts=14, M=Mb)
        cans["bottle"].cyl(.034, .05, (0, 0, .185), r2=.014, verts=14, M=Mb)
        cans["bottle"].cyl(.014, .05, (0, 0, .235), verts=10, M=Mb)
        cans["cap"].cyl(.016, .014, (0, 0, .265), verts=10, M=Mb)
    if lid_at is not None:
        glid.box((.045, d + .02, w + .02), (0, 0, 0), M=lid_at)
        glid.box((.03, d - .06, w - .08), (.03, 0, 0), M=lid_at)


def ab_board(gf, gb, gp, M0, w=.36, h=.52, splay=.2, picto="apple"):
    """A-frame chalkboard (wooden frame, slate panel) with a painted pictogram on the front face - no words."""
    for side in (-1, 1):
        Ms = M0 @ Matrix.Rotation(side * splay / 2, 4, 'X')        # hinged at the top
        Mb = Ms @ Matrix.Translation((0, 0, -h))                   # board space: z up from the foot
        fr = .03; th = .022
        for sx in (-1, 1): gf.box((fr, th, h), (sx * (w / 2 - fr / 2), 0, h / 2), M=Mb)
        gf.box((w, th, fr), (0, 0, h - fr / 2), M=Mb); gf.box((w, th, fr), (0, 0, fr * 1.5), M=Mb)
        gb.box((w - 2 * fr + .004, th * .5, h - fr * 3 + .004), (0, 0, h / 2 + fr * .25), M=Mb)
        if side == -1 and picto:
            Mp = Mb @ Matrix.Translation((0, -th * .25 - .002, h / 2 + .02)) @ Matrix.Rotation(math.pi / 2, 4, 'X')
            pict(gp, Mp, picto)
    Mt = M0 @ Matrix.Translation((0, 0, -.005))
    gf.cyl(.012, w - .02, (0, 0, 0), rot=(0, math.pi / 2, 0), verts=8, M=Mt)


def pict(gp, Mp, kind, s=1.0):
    """Painted pictogram, flat on the board (local x right, y up, -z out of the board)."""
    if kind == "apple":
        gp["red"].cyl(.075 * s, .004, (0, 0, -.002), verts=24, M=Mp @ Matrix.Diagonal((1.08, 1, 1, 1)))
        gp["green"].cyl(.03 * s, .004, (.035 * s, .095 * s, -.003), verts=12, M=Mp @ Matrix.Rotation(-.5, 4, 'Z') @ Matrix.Diagonal((1, .5, 1, 1)))
        gp["brown"].box((.012 * s, .045 * s, .004), (.0, .085 * s, -.003), rot=(0, 0, .2), M=Mp)
        gp["white"].cyl(.016 * s, .004, (-.03 * s, .03 * s, -.004), verts=10, M=Mp)
    elif kind == "milk":                                  # milk bottle: body, shoulder, neck, cap, a band
        gp["white"].box((.09 * s, .12 * s, .004), (0, -.03 * s, -.002), M=Mp)
        gp["white"].cyl(.045 * s, .004, (0, .03 * s, -.002), verts=16, M=Mp)
        gp["white"].box((.04 * s, .05 * s, .004), (0, .07 * s, -.002), M=Mp)
        gp["red"].box((.05 * s, .018 * s, .004), (0, .1 * s, -.003), M=Mp)
        gp["blue"].box((.092 * s, .03 * s, .004), (0, -.04 * s, -.003), M=Mp)
    elif kind == "cheese":                                # cheese wedge with holes
        gp["yellow"].cyl(.085 * s, .004, (0, 0, -.002), verts=3, M=Mp @ Matrix.Rotation(math.pi / 2, 4, 'Z'))
        for (x, y, r) in ((-.012, .01, .012), (.02, -.025, .009), (-.03, -.03, .007)):
            gp["brown"].cyl(r * s, .004, (x * s, y * s, -.003), verts=10, M=Mp)
    elif kind == "carrot":
        gp["orange"].cyl(.09 * s, .004, (0, -.02 * s, -.002), verts=3, M=Mp @ Matrix.Rotation(-math.pi / 2, 4, 'Z') @ Matrix.Diagonal((1, .45, 1, 1)))
        for a in (-.4, 0, .4):
            gp["green"].cyl(.025 * s, .004, (math.sin(a) * .03 * s, .07 * s + math.cos(a) * .02 * s, -.003), verts=10, M=Mp @ Matrix.Diagonal((.6, 1, 1, 1)))


def folding_chair(g, gs, M0):
    """Little folding wooden chair, painted; slatted seat and back."""
    sw, sd, sz = .38, .36, .44
    for sx in (-1, 1):
        g.box((.032, .032, .86), (sx * (sw / 2 - .02), sd / 2 - .02, .43), rot=(-.08, 0, 0), M=M0)        # back legs
        g.box((.032, .032, sz), (sx * (sw / 2 - .02), -sd / 2 + .03, sz / 2), rot=(.1, 0, 0), M=M0)       # front legs
        g.box((.025, sd - .04, .03), (sx * (sw / 2 - .02), 0, .16), M=M0)
    g.box((sw - .02, .025, .03), (0, -sd / 2 + .04, .16), M=M0)
    for k in range(4):
        gs.box((sw, sd / 4 - .012, .022), (0, -sd / 2 + (k + .5) * sd / 4, sz + .011), M=M0)
    for k in range(2):
        gs.box((sw - .02, .022, .075), (0, sd / 2 - .02 + .018, .62 + k * .12), rot=(-.08, 0, 0), M=M0)


def tied_box(gc, gt, M0, w, d, h, tape=True):
    gc.box((w, d, h), (0, 0, h / 2), M=M0)
    gc.box((w + .006, d * .5, .006), (0, -d * .25, h + .003), rot=(.06, 0, 0), M=M0)
    if tape: gt.box((w + .008, .05, .002), (0, 0, h + .001), M=M0)


def melon(gd, gl, M0, r=(.19, .135, .135), sectors=14):
    ellipsoid(gd, (0, 0, 0), r, sectors, 8, M=M0, pick=lambda i: i % 2 == 0)
    ellipsoid(gl, (0, 0, 0), r, sectors, 8, M=M0, pick=lambda i: i % 2 == 1)


# ================================================================== ERA 0 - MESINHA (sidewalk table)
MES = "E2 Mesinha"
MES_GROUPS = [
    ("ERA0_Table", ("MES_table", "MES_cloth", "MES_legs", "MES_box")),
    ("ERA0_Produce", ("MES_crate", "MES_fruit", "MES_banana", "MES_wedge", "MES_melon", "MES_tag")),
    ("ERA0_Cooler", ("MES_cooler",)),
    ("ERA0_Register", ("MES_cash", "MES_stack")),
    ("ERA0_Umbrella", ("MES_umb",)),
    ("ERA0_Chair", ("MES_chair",)),
    ("ERA0_Sign", ("MES_sign",)),
]


def build_mesinha():
    mats_v2()
    c = col(MES)
    for o in list(c.objects): bpy.data.objects.remove(o)
    E = EM
    todo = []

    def NG(name, mat, **kw):
        g = G(name, mat, c, **kw); todo.append(g); return g
    # ---- folding table under a gingham cloth: top x -0.75..0.65, y -0.29..0.43, z .74
    x0, x1, y0, y1, zt = -.75, .65, -.29, .43, .74
    g = G("MES_tableTop", E["wood"], c, bevel=.006)
    for k in range(6):
        g.box((x1 - x0, (y1 - y0) / 6 - .006, .024), ((x0 + x1) / 2, y0 + (k + .5) * (y1 - y0) / 6, zt - .012))
    g.box((x1 - x0 - .08, .025, .055), ((x0 + x1) / 2, y0 + .0125, zt - .0515)); g.box((x1 - x0 - .08, .025, .055), ((x0 + x1) / 2, y1 - .0125, zt - .0515))
    g.done()
    g = G("MES_legs", E["wood"], c, bevel=.005)
    L = math.hypot(.59, .67); ang = math.atan2(.67, .59)
    for lx in (-.62, .52):
        for sgn, dx in ((1, -.022), (-1, .022)):
            g.box((.028, L, .042), (lx + dx, (y0 + y1) / 2, .335), rot=(sgn * ang, 0, 0))
        g.cyl(.014, .1, (lx, (y0 + y1) / 2, .335), rot=(0, math.pi / 2, 0), verts=8)
    g.box((1.14 - .1, .03, .03), (-.05, (y0 + y1) / 2 + .045, .335))
    g.done()
    g = G("MES_cloth", E["ginghamB"], c, bevel=.004)
    g.box((x1 - x0 + .03, y1 - y0 + .03, .012), ((x0 + x1) / 2, (y0 + y1) / 2, zt + .0075))
    skirt(g, x0 - .016, x1 + .016, y0 - .016, y1 + .016, zt + .009, .5, rc=.035, amp=.009, pitch=.12)
    o = g.done(); o.modifiers["Bevel"].limit_method = 'ANGLE'; o.modifiers["Bevel"].angle_limit = math.radians(60)
    zc = zt + .0135                                              # top of the cloth
    # ---- spare stock box under the table
    tied_box(NG("MES_box", E["card"], bevel=.006), None, _T(.12, .2, 0, .08), .4, .3, .28, tape=False)
    # ---- three crates tilted towards the customers on wooden wedges
    gcr = NG("MES_crate", E["crateN" if PALETTE == "navy" else "pine"], bevel=.004, seg=1)
    crates = {"pine": gcr, "plG": NG("MES_crateGreen", E["plG"], bevel=.005, seg=1), "plR": NG("MES_crateRed", E["plR"], bevel=.005, seg=1),
              "plB": NG("MES_crateBlue", E["plB"], bevel=.005, seg=1)}
    PG = pg_factory(NG, "MES_fruit")
    gw = NG("MES_wedge", E["wood"], bevel=.003)
    gst = NG("MES_fruitStem", E["stem"])
    gtg = NG("MES_tagCard", E["chalk"]); gtp = NG("MES_tagPick", E["wood"])
    gsb = NG("MES_fruitStemB", E["brown"])
    tilt = math.radians(8); cw, cd, ch = .40, .32, .19
    for k, (x, kind, cm, n, lod) in enumerate(((-.49, "tomato", "pine", 22, 1), (-.04, "orange", "plG", 19, 1), (.41, "lime", "plR", 26, 0))):
        yf = -.04
        M0 = _T(x, yf, zc + .002) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Translation((0, cd / 2, 0))
        crate_rect(crates[cm], M0, cw, cd, ch)
        gw.box((cw - .1, .03, .031), (x, yf + cd - .018, zc + .0155 + .001))
        gw.box((cw - .09, cd - .046, .012), (0, 0, .044), M=M0)                         # false bottom: heaped crates
        heap(PG, M0, cw - .044, cd - .044, .05, kind, 10 + k, n, lod=lod)
        tag(gtg, gtp, M0 @ Matrix.Translation((cw / 2 - .085, -cd / 2, ch)))
    # ---- two hands of bananas on the cloth in front of the crates
    gbn = NG("MES_banana", E["banana"]); gbt = NG("MES_bananaTip", E["brown"])
    banana_bunch(gbn, gbt, _T(-.36, -.2, zc + .002, -.15), 5, .19, 1)
    banana_bunch(gbn, gbt, _T(.12, -.19, zc + .002, .25), 4, .18, 2)
    # ---- ground crate of red apples (front left) and a watermelon
    M0 = _T(-.98, -.38, 0, .2)
    crate_rect(crates["plB"], M0, .46, .34, .22)
    gw.box((.37, .294, .012), (0, 0, .08), M=M0)
    heap(PG, M0, .46 - .044, .34 - .044, .086, "apple", 21, 22, lod=0)
    tag(gtg, gtp, M0 @ Matrix.Translation((.13, -.17, .22)))
    gml = NG("MES_melonD", E["melonD"]); gmd = NG("MES_melonL", E["melonL"])
    melon(gml, gmd, _T(-1.0, .06, .134, .35) @ Matrix.Rotation(.05, 4, 'X'), (.19, .135, .128))
    # ---- right: the cash tin on two stacked upturned crates, the ice box with drinks in front of it
    gs = NG("MES_stack", E["pine"], bevel=.004, seg=1)
    for k in range(2):
        Mk = _T(1.07, .14, .26 * (k + 1), .14 + k * .06) @ Matrix.Rotation(math.pi, 4, 'X')
        crate_rect(gs, Mk, .42, .32, .26)
    gm = NG("MES_cashTin", E["metalT"], bevel=.003); gd = NG("MES_cashTray", E["dark"])
    gco = NG("MES_cashCoin", E["coin"]); gno = NG("MES_cashNote", E["note"])
    cash_tin(gm, gd, gco, gno, _T(1.06, .12, .522, .2))
    gco2 = NG("MES_coolerBox", E["coolR"], bevel=.012, seg=3)
    gli = NG("MES_coolerLid", E["creamF" if PALETTE == "navy" else "coolR"], bevel=.012, seg=3)
    gic = NG("MES_coolerIce", E["ice"])
    cans = {k: NG("MES_coolerCan" + k.capitalize(), E[k]) for k in ("canR", "canT", "canY", "alu", "bottle", "cap")}
    Mc = _T(1.0, -.4, 0, -.12)
    cooler(gco2, gli, gic, cans, Mc, lid_at=Mc @ Matrix.Translation((.425, 0, .28)) @ Matrix.Rotation(math.radians(-20), 4, 'Y'))
    # ---- folding chair for the seller (back left)
    folding_chair(NG("MES_chairFrame", E["yelP"], bevel=.006), NG("MES_chairSlats", E["yelP"], bevel=.005), _T(-1.0, .58, 0, -.35))
    # ---- parasol in a concrete-filled bucket (back right)
    px, py = .62, .7
    gbk = NG("MES_umbBucket", E["bucketB"], bevel=.006)
    gbk.cyl(.17, .26, (px, py, .13), r2=.2, verts=24); gbk.torus(.2, .012, (px, py, .26), seg=24, rseg=6)
    G("MES_umbFill", E["concrete"], c).cyl(.185, .02, (px, py, .245), verts=24).done()
    gbk.tube((px - .19, py, .25), (px - .12, py - .05, .36), .006, verts=5)
    gpo = NG("MES_umbPole", E["pole"])
    gpo.cyl(.022, 2.02, (px, py, 1.25), verts=12); gpo.cyl(.035, .1, (px, py, 1.55), verts=12)
    apex = (px, py, 2.28)
    gA = NG("MES_umbRed", E["canR"]); gB = NG("MES_umbWhite", E["canW"])
    gT = NG("MES_umbTrim", E["canY"]); gR = NG("MES_umbRibs", E["pole"])
    canopy((gA, gB), gT, apex, .97, 2.28, n=8, drop=.4, rib_g=gR, start=math.radians(10))
    gT.ball(.04, (px, py, apex[2] + .03), sub=2); gT.cyl(.015, .06, (px, py, apex[2]), verts=8)
    for k in range(8):                                            # struts from the runner to the ribs
        a = math.radians(10) + 2 * math.pi * k / 8
        gR.tube((px + .03 * math.cos(a), py + .03 * math.sin(a), 1.62), (px + .5 * math.cos(a), py + .5 * math.sin(a), 2.12), .005, verts=4)
    # ---- A-frame board with a painted apple in front
    pm = picto_mats()
    gp = {k: NG("MES_sign" + k.capitalize(), pm[k]) for k in ("red", "green", "brown", "white")}
    ab_board(NG("MES_signFrame", E["wood"], bevel=.004), NG("MES_signBoard", E["board"]), gp, _T(.2, -.6, .54, -.1))
    for gg in todo:
        if len(gg.bm.verts): gg.done()
        else: gg.bm.free()
    for o in c.objects:
        if o.type == 'MESH' and any(k in o.name for k in ("fruit", "melon", "banana", "can", "stem", "ice", "cash")):
            for p in o.data.polygons: p.use_smooth = True
    return V.stats(c)


# ================================================================== QA renders
def stage_pavers():
    """Sidewalk pavers a little darker than era_kit's so the light stalls read against them."""
    m = bpy.data.materials.get("E2_StagePavers")
    if not m:
        import era_kit as k
        m = k.pavers("ERA_Pavers").copy(); m.name = "E2_StagePavers"
        br = [n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeTexBrick"][0]
        br.inputs["Color1"].default_value = (.66, .64, .59, 1); br.inputs["Color2"].default_value = (.60, .58, .53, 1)
        br.inputs["Mortar"].default_value = (.47, .45, .41, 1)
    o = bpy.data.objects.get("STAGE_Pavers")
    if o: o.data.materials.clear(); o.data.materials.append(m)


def top_camera(cname, pad=1.5, extra=0.):
    lo, hi = bounds(game_objs(cname))
    c = (lo + hi) / 2; s = hi - lo
    camera((c.x, c.y, 0), max(s.x, s.y) * pad + extra, Vector((0, -.0001, 1)), res=(1400, 1400))
    cam = bpy.context.scene.camera; cam.location = (c.x, c.y, 60); cam.rotation_euler = (0, 0, 0)


def render_era(cname, tag, old=None, hide_top=(), close_dir=None):
    """<tag>_v1_iso / _close / _top (key-point markers, roof-like parts hidden) for a collection, as the game shows
    it (CUT_* off); with CUT_ parts also <tag>_full (everything on)."""
    stage(); stage_pavers()
    out = []
    show_only(cname)
    cut = game_hidden(cname)
    if cut:
        frame(cname, "iso"); out.append(render(tag + "_full"))
    for o in cut: o.hide_render = True
    try:
        frame(cname, "iso"); out.append(render(tag + "_iso"))
        frame(cname, "close"); out.append(render(tag + "_close"))
    finally:
        for o in cut: o.hide_render = False
    for o in cut: o.hide_render = True
    markers(cname, old)
    show_only(cname, "Markers")
    hid = [o for o in bpy.data.collections[cname].all_objects if any(k in o.name for k in hide_top)]
    for o in hid: o.hide_render = True
    try:
        top_camera(cname); out.append(render(tag + "_top"))
    finally:
        for o in hid + cut: o.hide_render = False
    return out


def vs_city(cname, tag, house_at=(-6.2, 2.4), tree_at=(4.0, .2), look=(-1.0, .8, 1.6), ortho=14.0):
    """The stall next to a city house and the city tree at the same scale (city sizes divided by the stall's 1.2)."""
    c = bpy.data.collections.get("REF City")
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o)
    k = 1 / SCALE
    info = [V.reference("StylizedHouse", house_at, fit=(8 * k, 7.8 * k, 8 * k)),
            V.reference("StylizedTree", tree_at, fit=(3.65 * k, 4.6 * k, 3.8 * k))]
    stage(); stage_pavers()
    show_only(cname, "REF City")
    camera(look, ortho, GAME_DIR, res=(1800, 1100))
    cut = game_hidden(cname)
    for o in cut: o.hide_render = True
    try:
        render(tag + "_vs_city")
    finally:
        for o in cut: o.hide_render = False
    return info


def overlaps(cname, min_pairs=1, skip=()):
    """lots_v3.overlaps() (one name family = one assembly) plus where each clash is, from an exact triangle BVH
    built in world space (FromPolygons on the evaluated loop triangles)."""
    from mathutils.bvhtree import BVHTree
    import re
    dg = bpy.context.evaluated_depsgraph_get()
    fam = lambda n: re.match(r"[A-Z0-9]+_[a-z]+", n).group(0) if re.match(r"[A-Z0-9]+_[a-z]+", n) else n
    objs = [o for o in bpy.data.collections[cname].all_objects if o.type == 'MESH' and not any(k in o.name for k in skip)]
    trees = {}
    for o in objs:
        m = o.evaluated_get(dg).to_mesh(); m.calc_loop_triangles()
        vs = [o.matrix_world @ v.co for v in m.vertices]; ts = [tuple(t.vertices) for t in m.loop_triangles]
        trees[o.name] = (BVHTree.FromPolygons(vs, ts, all_triangles=True), vs, ts)
        o.evaluated_get(dg).to_mesh_clear()
    out = []
    names = list(trees)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if fam(a) == fam(b): continue
            pr = trees[a][0].overlap(trees[b][0])
            if len(pr) >= min_pairs:
                va, ta = trees[a][1], trees[a][2]
                at = sum((va[k] for k in ta[pr[0][0]]), Vector()) / 3
                out.append((a, b, len(pr), tuple(round(x, 2) for x in at)))
    return out


# ================================================================== ERA 1 - TENDA (fair tent)
TEN = "E2 Tenda"
TEN_GROUPS = [
    ("ERA1_Tent", ("TEN_roof", "TEN_frame", "TEN_weight", "TEN_lights")),
    ("ERA1_Counter", ("TEN_table", "TEN_skirt")),
    ("ERA1_Produce", ("TEN_crate", "TEN_fruit", "TEN_wedge", "TEN_tag", "TEN_banana")),
    ("ERA1_Register", ("TEN_reg", "TEN_stand")),
    ("ERA1_Cooler", ("TEN_cooler",)),
    ("ERA1_Stock", ("TEN_stock", "TEN_sack", "TEN_stool", "TEN_melon")),
    ("ERA1_Sign", ("TEN_sign",)),
]
TX, TY, TE, TR = 1.88, 1.2, 2.12, 2.86          # pole x / y, eave height, ridge height


def tent_roof(gs, gtrim, gend, x0, x1, yh, ze, zr, n=12, valance=.15, thick=.014, hem=False):
    """Pitched canvas roof, ridge along x: n stripes across (alternating gs[0] / gs[1]) that sag a little between
    the ridge and the eaves, a scalloped valance along the front and back eaves, cream gable ends, orange
    piping on every edge (gtrim)."""
    def z_at(x, y):
        f = abs(y) / yh
        sag = .035 * abs(math.sin(math.pi * x / TX)) * math.sin(math.pi * min(1, f))
        return zr - (zr - ze) * f - sag
    NA, NB = 4, 12
    for k in range(n):
        g = gs[k % 2]
        xa, xb = x0 + (x1 - x0) * k / n, x0 + (x1 - x0) * (k + 1) / n
        top, bot = [], []
        for i in range(NB + 1):
            y = -yh + 2 * yh * i / NB
            rt, rb = [], []
            for j in range(NA + 1):
                x = xa + (xb - xa) * j / NA
                p = Vector((x, y, z_at(x, y)))
                rt.append(g.bm.verts.new(p)); rb.append(g.bm.verts.new(p - Vector((0, 0, thick))))
            top.append(rt); bot.append(rb)
        for i in range(NB):
            for j in range(NA):
                g.bm.faces.new((top[i][j], top[i][j + 1], top[i + 1][j + 1], top[i + 1][j]))
                g.bm.faces.new((bot[i][j], bot[i + 1][j], bot[i + 1][j + 1], bot[i][j + 1]))
        for side, i in ((-1, 0), (1, NB)):               # valance (scalloped), one scallop per stripe
            rt, rb = top[i], bot[i]
            ho, hi = [], []
            for j in range(NA + 1):
                t = j / NA
                p = rt[j].co.copy(); dep = valance * (.6 + .4 * math.sin(math.pi * t))
                ho.append(g.bm.verts.new(p + Vector((0, side * .004, -dep))))
                hi.append(g.bm.verts.new(p + Vector((0, side * (.004 - thick * .7), -dep))))
            if hem:                                       # trim piping along the scalloped hem
                sweep(gtrim, [v.co + Vector((0, side * .002, -.004)) for v in ho], [.008] * len(ho), verts=4)
            for j in range(NA):
                if side < 0:
                    g.bm.faces.new((rt[j], ho[j], ho[j + 1], rt[j + 1])); g.bm.faces.new((rb[j + 1], hi[j + 1], hi[j], rb[j]))
                    g.bm.faces.new((ho[j], hi[j], hi[j + 1], ho[j + 1]))
                else:
                    g.bm.faces.new((rt[j + 1], ho[j + 1], ho[j], rt[j])); g.bm.faces.new((rb[j], hi[j], hi[j + 1], rb[j + 1]))
                    g.bm.faces.new((ho[j + 1], hi[j + 1], hi[j], ho[j]))
        for side in (-1, 1):                              # piping along the eave
            pts = [Vector((xa + (xb - xa) * j / NA, side * (yh + .006), z_at(xa + (xb - xa) * j / NA, side * yh) - .006)) for j in range(NA + 1)]
            sweep(gtrim, pts, [.012] * len(pts), verts=5)
    for sx in (-1, 1):                                    # gable ends + piping up the rakes
        x = x0 if sx < 0 else x1
        pts = [(-yh, ze - thick), (0, zr - thick), (yh, ze - thick)]
        gend.prism([(p[0], p[1]) for p in pts], .012, M=Matrix.Translation((x - sx * .01, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'))
        for a, b in ((-yh, 0), (0, yh)):
            pts = [Vector((x + sx * .004, a + (b - a) * t / 8, z_at(x, a + (b - a) * t / 8) + .004)) for t in range(9)]
            sweep(gtrim, pts, [.012] * 9, verts=5)
        # scalloped flap under the gable end, between the eaves
    gtrim.ball(.045, (x0 - .02, 0, zr + .01), sub=2); gtrim.ball(.045, (x1 + .02, 0, zr + .01), sub=2)


def retro_register(gb, gk, gd, gc, gn, M0):
    """Little retro cash register, no markings: body with a stepped key deck (keys towards the clerk, +y), a
    blank flag window on top, side crank, the cash drawer pulled out with coins and notes."""
    W, D = .34, .3
    gb.box((W, D, .09), (0, 0, .045), M=M0)                                   # drawer housing
    gd.box((W - .04, D * .7, .05), (0, .07, .055), M=M0)                      # drawer (open towards the clerk)
    gb.box((W - .03, .014, .07), (0, .07 + D * .35, .05), M=M0)               # drawer front
    for i in range(4):
        gc.cyl(.024, .012, (-.105 + i * .07, .14, .086), verts=10, M=M0)
    for i in range(2):
        gn.box((.1, .07, .012), (-.06 + i * .12, .03, .086), M=M0)
    gb.box((W, D * .62, .2), (0, -D * .19, .19), M=M0)                        # body
    for r in range(3):                                                         # stepped key rows
        yb = .055 - r * .06; zb = .29 + r * .035
        gb.box((W - .04, .06, .02 + r * .035), (0, yb, zb - (r * .035) / 2), M=M0)
        for i in range(5):
            gk.box((.045, .04, .02), (-.12 + i * .06, yb, zb + .02), M=M0)
    gb.box((W - .08, .1, .1), (0, -.1, .4), M=M0)                             # flag window housing
    gk.box((W - .12, .006, .055), (0, -.152, .405), M=M0)                      # blank flag window (towards customers)
    gb.cyl(.022, .02, (W / 2 + .01, -.02, .24), rot=(0, math.pi / 2, 0), verts=12, M=M0)
    gb.tube(M0 @ Vector((W / 2 + .022, -.02, .24)), M0 @ Vector((W / 2 + .022, .03, .33)), .007, verts=6)
    gd.tube(M0 @ Vector((W / 2 + .022, .03, .33)), M0 @ Vector((W / 2 + .07, .03, .33)), .012, verts=8)


def picnic_cooler(gt, gw, gice, cans, M0, w=.6, d=.38, h=.4, seed=7):
    """Teal picnic cooler, white lid tipped open backwards, ice and drinks inside, side handles."""
    t = .04
    gt.box((w, d, t), (0, 0, t / 2), M=M0)
    for sy in (-1, 1): gt.box((w, t, h), (0, sy * (d / 2 - t / 2), h / 2), M=M0)
    for sx in (-1, 1): gt.box((t, d - 2 * t + .002, h), (sx * (w / 2 - t / 2), 0, h / 2), M=M0)
    for sx in (-1, 1):
        gw.box((.03, .14, .03), (sx * (w / 2 + .02), 0, h * .78), M=M0)
        gw.box((.03, .02, .06), (sx * (w / 2 + .012), -.06, h * .78 - .015), M=M0); gw.box((.03, .02, .06), (sx * (w / 2 + .012), .06, h * .78 - .015), M=M0)
    Ml = M0 @ Matrix.Translation((0, d / 2, h + .004)) @ Matrix.Rotation(-1.95, 4, 'X')
    gw.box((w + .01, d + .01, .05), (0, -d / 2 - .005, .025), M=Ml)
    iw, idp = w - 2 * t - .006, d - 2 * t - .006
    gice.box((iw, idp, .22), (0, 0, t + .11), M=M0)
    rnd = random.Random(seed)
    for k in range(16):
        s = rnd.uniform(.03, .045)
        gice.box((s, s, s), (rnd.uniform(-iw / 2 + .03, iw / 2 - .03), rnd.uniform(-idp / 2 + .03, idp / 2 - .03), t + .22 + rnd.uniform(-.004, .01)),
                 rot=(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3)), M=M0)
    for x, y, m in [(-.2, -.07, 'canR'), (-.12, .07, 'canY'), (-.04, -.06, 'canT'), (.04, .07, 'canR'), (.12, -.06, 'canY'), (.2, .06, 'canT')]:
        cans[m].cyl(.033, .12, (x, y, t + .2 + .06), verts=14, M=M0)
        cans["alu"].cyl(.029, .006, (x, y, t + .2 + .123), verts=14, M=M0)
    for x, y in ((-.04, .1), (.2, -.1)):
        Mb = M0 @ Matrix.Translation((x, y, t + .16))
        cans["bottle"].cyl(.034, .16, (0, 0, .08), verts=14, M=Mb)
        cans["bottle"].cyl(.034, .05, (0, 0, .185), r2=.014, verts=14, M=Mb)
        cans["bottle"].cyl(.014, .05, (0, 0, .235), verts=10, M=Mb)
        cans["cap"].cyl(.016, .014, (0, 0, .265), verts=10, M=Mb)


def trestle_table(gt, gl, x0, x1, y0, y1, h=.8):
    """Fair trestle table: plank top on two A-trestles, a front apron plank."""
    n = 5
    for k in range(n):
        gt.box((x1 - x0, (y1 - y0) / n - .006, .028), ((x0 + x1) / 2, y0 + (k + .5) * (y1 - y0) / n, h - .014))
    gt.box((x1 - x0 - .02, .022, .1), ((x0 + x1) / 2, y0 + .011, h - .078))
    for xt in (x0 + .16, x1 - .16):
        for sy in (-1, 1):
            a = Vector((xt, (y0 + y1) / 2 + sy * .26, 0)); b = Vector((xt, (y0 + y1) / 2 + sy * .07, h - .03))
            d = b - a; L = d.length
            gl.box((.05, .035, L), ((a + b) / 2), rot=(-sy * math.atan2(abs(d.y), d.z), 0, 0))
        gl.box((.05, (y1 - y0) - .08, .04), (xt, (y0 + y1) / 2, h - .055))
        gl.box((.03, .4, .03), (xt, (y0 + y1) / 2, .25))


def tent_gables(gs, x0, x1, yh, ze, zr, n=8, thick=.012):
    """Gable ends in the canvas stripes (no blank slab): vertical bands clipped to the roof line."""
    zl = lambda y: zr - (zr - ze) * abs(y) / yh - .012
    for sx, x in ((-1, x0), (1, x1)):
        for k in range(n):
            ya, yb = -yh + 2 * yh * k / n, -yh + 2 * yh * (k + 1) / n
            pts = [(ya, ze - .012), (yb, ze - .012), (yb, zl(yb))]
            if ya < 0 < yb: pts.append((0, zl(0)))
            pts.append((ya, zl(ya)))
            gs[k % 2].prism(pts, thick, M=Matrix.Translation((x - sx * .012, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'))


def side_curtain(gs, groll, gtie, x, y0, y1, ztop, zroll, n=8, thick=.01):
    """Side wall of the tent rolled up to zroll: striped canvas hanging from the side beam, the roll and its ties."""
    for k in range(n):
        ya, yb = y0 + (y1 - y0) * k / n, y0 + (y1 - y0) * (k + 1) / n
        g = gs[k % 2]
        vs = []
        for (yy, zz) in ((ya, zroll), (yb, zroll), (yb, ztop), (ya, ztop)):
            vs.append(g.bm.verts.new((x - thick / 2, yy, zz))); vs.append(g.bm.verts.new((x + thick / 2, yy, zz)))
        o = vs[0::2]; i = vs[1::2]
        g.bm.faces.new(o); g.bm.faces.new(list(reversed(i)))
        for a in range(4):
            b = (a + 1) % 4; g.bm.faces.new((o[a], o[b], i[b], i[a]))
        g._put([], Matrix.Identity(4))
    rr = .055
    for k in range(n):                                  # the roll keeps the stripes
        ya, yb = y0 + (y1 - y0) * k / n, y0 + (y1 - y0) * (k + 1) / n
        groll[k % 2].cyl(rr, yb - ya, (x, (ya + yb) / 2, zroll - rr + .01), rot=(math.pi / 2, 0, 0), verts=14)
    for yy in (y0 + .35, (y0 + y1) / 2, y1 - .35):     # ties around the roll, up to the beam
        gtie.torus(rr + .006, .006, (x, yy, zroll - rr + .01), rot=(math.pi / 2, 0, 0), seg=14, rseg=4)
        gtie.box((.006, .03, ztop - zroll + .02), (x + thick / 2 + .004, yy, (ztop + zroll) / 2 + .01))



def build_tenda(scheme="N"):
    mats_v2()
    c = col(TEN)
    for o in list(c.objects): bpy.data.objects.remove(o)
    E = EM
    todo = []
    ca, cb, ct = {"A": ("canOr", "canY", "canR"), "B": ("canR", "canW", "canY"), "N": ("navy", "creamB", "gold")}[scheme]
    fr = "gold" if scheme == "N" else "frameB"                # (navy canvas: gold poles, never navy on navy)

    def NG(name, mat, **kw):
        g = G(name, mat, c, **kw); todo.append(g); return g
    # ---- frame: 4 legs, eave beams, rafters, ridge; weights (sandbags) on the feet
    gf = NG("TEN_frame", E[fr])
    for sx in (-1, 1):
        for sy in (-1, 1):
            gf.cyl(.026, TE + .02, (sx * TX, sy * TY, (TE + .02) / 2), verts=12)
            gf.cyl(.034, .12, (sx * TX, sy * TY, .06), verts=12)
            gf.box((.07, .07, .06), (sx * TX, sy * TY, TE - .02))
    for sy in (-1, 1): gf.tube((-TX, sy * TY, TE), (TX, sy * TY, TE), .02, verts=10)
    for sx in (-1, 1):
        gf.tube((sx * TX, -TY, TE), (sx * TX, TY, TE), .02, verts=10)
        gf.tube((sx * TX, -TY, TE), (sx * TX, 0, TR - .05), .018, verts=8); gf.tube((sx * TX, TY, TE), (sx * TX, 0, TR - .05), .018, verts=8)
    gf.tube((-TX, 0, TR - .05), (TX, 0, TR - .05), .02, verts=10)
    gwt = NG("TEN_weight", E["sand"], bevel=.03, seg=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            gwt.box((.32, .2, .1), (sx * TX - sx * .2, sy * TY, .05), rot=(0, 0, .15 * sx * sy))
            gwt.box((.3, .19, .1), (sx * TX - sx * .2, sy * TY, .148), rot=(0, 0, -.2 * sx * sy))
    # ---- roof
    gA = NG("TEN_roofA", E[ca]); gB = NG("TEN_roofB", E[cb])
    gT = NG("TEN_roofTrim", E[ct]); gEnd = NG("TEN_roofEnd", E[cb])
    tent_roof((gA, gB), gT, gEnd, -TX - .1, TX + .1, TY + .1, TE + .02, TR, hem=(scheme == "N"))
    gEnd.bm.clear()                                           # (the plain gable triangles are replaced by striped ones)
    tent_gables((gA, gB), -TX - .1, TX + .1, TY + .1, TE + .02, TR)
    # rolled-up striped side walls on both gable sides, ties, guy ropes to pegs
    gSA = NG("TEN_roofSideA", E[ca]); gSB = NG("TEN_roofSideB", E[cb]); gtie = NG("TEN_roofTie", E["rope"])
    for sx in (-1, 1):
        side_curtain((gSA, gSB), (gSA, gSB), gtie, sx * (TX + .045), -TY + .05, TY - .05, TE - .02, 1.62)
    grp = NG("TEN_roofRope", E["rope"]); gpg = NG("TEN_roofPeg", E["peg"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            yy = sy * .62; zr_ = TR - (TR - TE - .02) * abs(yy) / (TY + .1) - .02
            a = Vector((sx * (TX + .1), yy, zr_)); b = Vector((sx * 2.012, sy * .8, .12))
            grp.tube(a, b, .006, verts=4)
            gpg.cyl(.012, .16, (sx * 2.04, sy * .8, .05), rot=(0, -sx * .35, 0), verts=6)
            gpg.cyl(.02, .015, (sx * 2.012, sy * .8, .132), verts=8)
    # ---- string of bulbs under the front eave
    gc_ = NG("TEN_lightsCord", E["cord"]); gbu = NG("TEN_lightsBulb", E["bulb"])
    for a, b in ((-TX + .03, 0.), (0., TX - .03)):
        pts = []
        for i in range(13):
            t = i / 12; x = a + (b - a) * t
            pts.append(Vector((x, -TY + .03, TE - .06 - .16 * math.sin(math.pi * t))))
        sweep(gc_, pts, [.005] * len(pts), verts=4)
        for i in range(1, 12, 2):
            p = pts[i]; gbu.ball(.028, p - Vector((0, 0, .04)), scale=(1, 1, 1.25), sub=1); gc_.cyl(.012, .025, p - Vector((0, 0, .012)), verts=8)
    # ---- counter: two trestle tables along the front
    gtt = NG("TEN_tableTop", E["wood"], bevel=.006); gtl = NG("TEN_tableLegs", E["wood"], bevel=.005, seg=1)
    trestle_table(gtt, gtl, -1.8, -.28, -1.0, -.4, .8)
    trestle_table(gtt, gtl, -.2, .62, -1.0, -.4, .8)
    # ---- crates tilted towards the customers on wedges; a hanging hand of bananas
    gcr = NG("TEN_crate", E["crateN" if PALETTE == "navy" else "pine"], bevel=.004, seg=1); gw = NG("TEN_wedge", E["wood"], bevel=.003, seg=1)
    crates = {"pine": gcr, "plB": NG("TEN_crateBlue", E["plB"], bevel=.005, seg=1), "plG": NG("TEN_crateGreen", E["plG"], bevel=.005, seg=1),
              "plY": NG("TEN_crateYellow", E["plY"], bevel=.005, seg=1)}
    PG = pg_factory(NG, "TEN_fruit")
    gtg = NG("TEN_tagCard", E["chalk"])
    tilt = math.radians(12); cw, cd, ch = .44, .34, .19
    zc = .8
    spots = [(-1.53, "tomato", "pine", 20), (-1.04, "orange", "plB", 17), (-.55, "pepper", "plG", 12),
             (.0, "potato", "pine", 14), (.42, "onion", "plY", 16)]
    for k, (x, kind, cm, n) in enumerate(spots):
        w_ = cw if x < -.2 else .38
        yf = -.93
        M0 = _T(x, yf, zc + .002) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Translation((0, cd / 2, 0))
        crate_rect(crates[cm], M0, w_, cd, ch)
        gw.box((w_ - .1, .03, .058), (x, yf + cd - .02, zc + .001 + .029))
        gw.box((w_ - .09, cd - .046, .012), (0, 0, .044), M=M0)
        heap(PG, M0, w_ - .044, cd - .044, .05, kind, 30 + k, n if w_ > .4 else n - 3, lod=1 if kind in ("pepper", "potato") else 0)
        tag(gtg, None, M0 @ Matrix.Translation((w_ / 2 - .085, -cd / 2, ch)))
    gbn = NG("TEN_banana", E["banana"]); gbt = NG("TEN_bananaTip", E["brown"]); gh = NG("TEN_bananaHook", E["cord"])
    for bx in (-1.235, -.615):                      # between the bulbs; strings tied under the eave beam
        gh.tube((bx, -TY, TE - .021), (bx, -TY, 1.72), .004, verts=4)
        gh.cyl(.02, .03, (bx, -TY, 1.715), verts=8)
        for k in range(3):
            banana_bunch(gbn, gbt, _T(bx, -TY, 1.70, .6 + k * 2.1) @ Matrix.Rotation(math.pi / 2 - .25, 4, 'Y'), 4, .17, 5 + k + int(abs(bx) * 10))
    # ---- register on a painted stand, right of the counter (CheckoutStall.Register ~ (.87, -.65, .67))
    gsd = NG("TEN_stand", E["grnP"], bevel=.008)
    gsd.box((.42, .4, .54), (.9, -.66, .27)); gsd.box((.46, .44, .03), (.9, -.66, .555))
    gsc = NG("TEN_standTrim", E["cream"], bevel=.004)
    Mf = _T(.9, -.66, 0, 0) @ Matrix.Translation((0, -.2 - .006, 0))
    for z in (.08, .46): gsc.box((.34, .012, .025), (0, 0, z), M=Mf)
    for x in (-.158, .158): gsc.box((.025, .012, .405), (x, 0, .27), M=Mf)
    rb = NG("TEN_regBody", E["regBody"], bevel=.008); rk = NG("TEN_regKey", E["regKey"], bevel=.004, seg=1)
    rd = NG("TEN_regDark", E["dark"], bevel=.004); rc = NG("TEN_regCoin", E["coin"]); rn = NG("TEN_regNote", E["note"])
    retro_register(rb, rk, rd, rc, rn, _T(.9, -.66, .574, math.pi + .12))
    # ---- drinks: teal picnic cooler at the front right
    gct = NG("TEN_coolerBody", E["coolB"], bevel=.015, seg=2); gcw = NG("TEN_coolerLid", E["creamF" if PALETTE == "navy" else "coolB"], bevel=.012, seg=2)
    gci = NG("TEN_coolerIce", E["ice"])
    cans = {k: NG("TEN_coolerCan" + k.capitalize(), E[k]) for k in ("canR", "canT", "canY", "alu", "bottle", "cap")}
    picnic_cooler(gct, gcw, gci, cans, _T(1.5, -.78, 0, -.1))
    # ---- back: stock (boxes, a sack, a crate of watermelons), a stool for the seller
    gbx = NG("TEN_stockBox", E["card"], bevel=.008)
    for (x, y, z, w_, d_, h_, rz) in ((-1.4, .85, 0, .5, .4, .36, .08), (-1.38, .86, .36, .44, .36, .3, -.1), (-.85, .95, 0, .44, .34, .34, -.05)):
        gbx.box((w_, d_, h_), (x, y, z + h_ / 2), rot=(0, 0, rz))
        gbx.box((w_ + .006, d_ * .5, .006), (x, y, z + h_ + .003), rot=(.05, 0, rz))
    gsk = NG("TEN_sack", E["burlap"], bevel=.06, seg=3)
    gsk.box((.4, .3, .42), (-.25, .95, .21), rot=(0, 0, .3)); gsk.box((.12, .1, .1), (-.25, .95, .46), rot=(0, 0, .3))
    gs2 = NG("TEN_stockCrate", E["plR"], bevel=.005, seg=1)
    gml = NG("TEN_melonD", E["melonD"]); gmd = NG("TEN_melonL", E["melonL"])
    for k, (x, y) in enumerate(((1.15, .85), (.62, .9))):
        Mk = _T(x, y, 0, .1 - k * .2)
        crate_rect(gs2, Mk, .5, .38, .26)
        for j in range(2):
            melon(gml, gmd, Mk @ Matrix.Translation((-.11 + .22 * j, 0, .03 + .125)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'), (.165, .11, .115))
    gsl = NG("TEN_stool", E["redP"])
    gsl.cyl(.17, .04, (.2, .15, .48), verts=20)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        gsl.tube((.2 + .15 * math.cos(a), .15 + .15 * math.sin(a), 0), (.2 + .1 * math.cos(a), .15 + .1 * math.sin(a), .46), .018, verts=6)
    # ---- A-frame board with a painted apple at the left front corner
    pm = picto_mats()
    gp = {k: NG("TEN_sign" + k.capitalize(), pm[k]) for k in ("red", "green", "brown", "white")}
    ab_board(NG("TEN_signFrame", E["wood"], bevel=.004), NG("TEN_signBoard", E["board"]), gp, _T(-1.98, -.25, .54, -.35))
    for gg in todo:
        if len(gg.bm.verts): gg.done()
        else: gg.bm.free()
    for o in c.objects:
        if o.type == 'MESH' and any(k in o.name for k in ("fruit", "melon", "banana", "Can", "Bulb", "Ice", "reg")):
            for p in o.data.polygons: p.use_smooth = True
    return V.stats(c)


# ================================================================== export (stepwise: each MCP call stays short)
def export_era(src, name, groups, default, step):
    """step 'uv' (copies, atlas), 'bake0'..'bake2' (3-part bake, saves the PNG), 'fbx'.
    No city tree in the stalls: the tree square of the atlas band is given back to the swatches / parts."""
    V.SWATCH = SWATCH_V2
    tree = any(_mat_name(o) == "V3_CityTree" for o in bpy.data.collections[src].objects if o.type == 'MESH')
    V.TREE_BAND = .25 if tree else 0.
    rows = math.ceil(len(SWATCH_V2) / int((1 - V.TREE_BAND - .006) / V.SWATCH_CELL))
    V.RESERVED = max(V.TREE_BAND, rows * V.SWATCH_CELL) + .004
    try:
        if step == "uv":
            return V.make_export(src=src, name=name, groups=groups, default=default, inside=(100, 100.1, 100, 100.1), walls=("__none__",), texel=TEXEL_V2)
        if step.startswith("bake"):
            return V.bake(name=name, size=2048, part=int(step[4:]), parts=3)
        if step == "fbx":
            return V.export(name=name)
    finally:
        V.TREE_BAND = .25; V.RESERVED = V.TREE_BAND + .004


def _mat_name(o):
    m = o.data.materials[0] if o.data.materials else None
    return m.name.split(".")[0] if m else ""


def import_export(name):
    """The exported FBX + baked PNG back into 'NEW <name>' (modelling frame) to check the result."""
    p = os.path.join(EXPORT, name + ".fbx")
    cname = "NEW " + name
    c = col(cname)
    for o in list(c.objects): bpy.data.objects.remove(o)
    lc = bpy.context.view_layer.layer_collection.children.get(cname)
    if lc: lc.exclude = False          # (an excluded collection is not evaluated: stale matrix_world)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=p)
    objs = [o for o in bpy.data.objects if o not in before]
    img = bpy.data.images.load(os.path.join(EXPORT, name + "_BaseColor.png"), check_existing=False); img.name = "NEWTEX_" + name
    m = bpy.data.materials.new("NEWMAT_" + name); m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = img
    bs = m.node_tree.nodes["Principled BSDF"]; bs.inputs["Roughness"].default_value = .85
    m.node_tree.links.new(t.outputs["Color"], bs.inputs["Base Color"])
    root = bpy.data.objects.new("NEWROOT_" + name, None); c.objects.link(root)
    info = []
    for o in objs:
        for cc in list(o.users_collection): cc.objects.unlink(o)
        c.objects.link(o)
        if o.type == 'MESH':
            info.append((o.name, [mm.name for mm in o.data.materials], [u.name for u in o.data.uv_layers], round(o.rotation_euler.z, 3)))
            glassy = any(mm and "Glass" in mm.name for mm in o.data.materials)        # as the game: see-through
            o.data.materials.clear(); o.data.materials.append(m_eraglass() if glassy else m)
        o.name = "NEW_" + o.name
        if o.parent is None: o.parent = root
    bpy.context.view_layer.update()
    root.rotation_euler = (0, 0, math.pi)
    bpy.context.view_layer.update()
    return info


# ================================================================== glass (EraGlass) - kept out of the bake
def m_eraglass():
    """The game swaps any material whose name contains "Glass" for its see-through glass (CheckoutStall.Glass());
    this one only makes the previews look like that."""
    m = bpy.data.materials.get("EraGlass") or bpy.data.materials.new("EraGlass")
    m.use_nodes = True; nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (.75, .88, .95, 1); b.inputs["Alpha"].default_value = .18
    b.inputs["Roughness"].default_value = .05
    try: m.surface_render_method = 'BLENDED'
    except Exception: m.blend_method = 'BLEND'
    return m


def glass_col(src):
    """Child collection of a source collection for its glass panes: make_export() only reads the source's own
    objects, so the panes skip the atlas and the bake; add_glass() puts them into the export afterwards."""
    return col(src + " Glass", bpy.data.collections[src])


def add_glass(src, name, names):
    """Copies of the glass panes (modifiers applied, world space) into '<name> Export' as X_<names[part]>, material
    EraGlass, so export() writes them next to the baked parts. names: {source prefix: export object name}."""
    d = bpy.data.collections[name + " Export"]
    for o in list(d.objects):
        if o.name.startswith("X_") and o.data.materials and o.data.materials[0].name.startswith("EraGlass"):
            bpy.data.objects.remove(o)
    gm = m_eraglass()
    gc = bpy.data.collections.get(src + " Glass")
    if not gc: return []
    groups = {}
    for o in gc.objects:
        key = next((k for k in names if o.name.startswith(k)), None)
        if key is None: continue
        n = o.copy(); n.data = o.data.copy(); d.objects.link(n); V._apply(n)
        n.data.transform(n.matrix_world); n.matrix_world = Matrix.Identity(4)
        n.data.materials.clear(); n.data.materials.append(gm)
        groups.setdefault(names[key], []).append(n)
    out = []
    for nm, objs in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = "X_" + nm; j.data.name = "X_" + nm
        j.hide_render = False; out.append(j.name)
    return out


def slope_awning(gs, gtrim, x0, x1, yb, zb, yf, zf, n=10, valance=.16, thick=.014, sag=.03, hem=False):
    """Single-slope stall awning (back high -> front low), n stripes running front to back (gs[0] / gs[1]) with a
    little sag between the rafters, a scalloped valance along the front and the two sides' edges piped (gtrim)."""
    NA, NB = 4, 10
    def z_at(x, y):
        t = (y - yf) / (yb - yf)
        s = sag * abs(math.sin(math.pi * (x - x0) / ((x1 - x0) / 2))) * math.sin(math.pi * t)
        return zf + (zb - zf) * t - s
    for k in range(n):
        g = gs[k % 2]
        xa, xb = x0 + (x1 - x0) * k / n, x0 + (x1 - x0) * (k + 1) / n
        top, bot = [], []
        for i in range(NB + 1):
            y = yf + (yb - yf) * i / NB
            rt, rb = [], []
            for j in range(NA + 1):
                x = xa + (xb - xa) * j / NA
                p = Vector((x, y, z_at(x, y)))
                rt.append(g.bm.verts.new(p)); rb.append(g.bm.verts.new(p - Vector((0, 0, thick))))
            top.append(rt); bot.append(rb)
        for i in range(NB):
            for j in range(NA):
                g.bm.faces.new((top[i][j], top[i][j + 1], top[i + 1][j + 1], top[i + 1][j]))
                g.bm.faces.new((bot[i][j], bot[i + 1][j], bot[i + 1][j + 1], bot[i][j + 1]))
        rt, rb = top[0], bot[0]
        ho, hi = [], []
        for j in range(NA + 1):
            t = j / NA; p = rt[j].co.copy(); dep = valance * (.6 + .4 * math.sin(math.pi * t))
            ho.append(g.bm.verts.new(p + Vector((0, -.004, -dep)))); hi.append(g.bm.verts.new(p + Vector((0, -.004 + thick * .7, -dep))))
        if hem:
            sweep(gtrim, [v.co + Vector((0, -.002, -.004)) for v in ho], [.008] * len(ho), verts=5)
        for j in range(NA):
            g.bm.faces.new((rt[j], ho[j], ho[j + 1], rt[j + 1])); g.bm.faces.new((rb[j + 1], hi[j + 1], hi[j], rb[j]))
            g.bm.faces.new((ho[j], hi[j], hi[j + 1], ho[j + 1]))
        pts = [Vector((xa + (xb - xa) * j / NA, yf - .006, z_at(xa + (xb - xa) * j / NA, yf) - .006)) for j in range(NA + 1)]
        sweep(gtrim, pts, [.012] * len(pts), verts=5)
    for x in (x0, x1):
        pts = [Vector((x, yf + (yb - yf) * i / 8, z_at(x, yf + (yb - yf) * i / 8) - .006)) for i in range(9)]
        sweep(gtrim, pts, [.012] * 9, verts=5)
    return z_at


def gable_carton(gw, gb, M0, w=.07, d=.07, h=.16):
    """Gable-top milk carton, plain (white body, a coloured band; no print)."""
    gw.box((w, d, h), (0, 0, h / 2), M=M0)
    gw.prism([(-w / 2, h), (w / 2, h), (0, h + .035)], d * .98, M=M0)
    gw.box((w * .9, .008, .02), (0, 0, h + .042), M=M0)
    gb.box((w + .003, d + .003, h * .35), (0, 0, h * .42), M=M0)


def dairy_chest(gb, gt, gk, gin, gglass, gx, M0, w=1.16, d=.55, h=.82, seed=4):
    """Refrigerated dairy chest (feira style): white enamel body, teal band, dark rubber rim, ice-blue well; two
    sliding glass lids (gglass, EraGlass) over milk cartons, cheese wheels, butter and yoghurt cups (gx: dict of
    G by kind)."""
    t = .05
    gb.box((w, d, .12), (0, 0, .06), M=M0)                                        # plinth
    for sy in (-1, 1): gb.box((w, t, h - .12), (0, sy * (d / 2 - t / 2), .12 + (h - .12) / 2), M=M0)
    for sx in (-1, 1): gb.box((t, d - 2 * t + .002, h - .12), (sx * (w / 2 - t / 2), 0, .12 + (h - .12) / 2), M=M0)
    gt.box((w + .006, d + .006, .1), (0, 0, .42), M=M0)                            # teal band
    gk.box((w + .01, .04, .03), (0, -d / 2 + .015, h + .012), M=M0); gk.box((w + .01, .04, .03), (0, d / 2 - .015, h + .012), M=M0)
    for sx in (-1, 0, 1): gk.box((.04, d - .06, .03), (sx * (w / 2 - .015), 0, h + .012), M=M0)
    gk.box((.1, .02, .05), (-w / 2 + .14, -d / 2 - .01, h - .06), M=M0)            # thermostat knob plate
    iw, idp = w - 2 * t - .004, d - 2 * t - .004
    gin.box((iw, idp, .02), (0, 0, h - .3), M=M0)                                  # well floor (contents stand on it)
    lt = .006                                                                       # light liner on the inner walls
    for sy in (-1, 1): gin.box((iw, lt, .28), (0, sy * (idp / 2 - lt / 2), h - .15), M=M0)
    for sx in (-1, 1): gin.box((lt, idp - 2 * lt, .28), (sx * (iw / 2 - lt / 2), 0, h - .15), M=M0)
    iw, idp = iw - 2 * lt, idp - 2 * lt
    zf = h - .29
    rnd = random.Random(seed)
    # left half: milk cartons in two rows
    for r in range(2):
        for k in range(5):
            gable_carton(gx["milk"], gx["milkBand" if (k + r) % 2 else "milkBand2"], M0 @ Matrix.Translation((-iw / 2 + .06 + k * .088, -idp / 2 + .07 + r * .13, zf)) @ Matrix.Rotation(rnd.uniform(-.1, .1), 4, 'Z'))
    # right half: cheese wheels (one cut), butter, yoghurt cups
    for k, (x, y) in enumerate(((.12, .1), (.3, .1))):
        gx["cheese"].cyl(.075, .07, (x, y, zf + .035), verts=20, M=M0)
    gx["cheese"].prism([(0, 0), (.07, 0), (.05, .05)], .06, M=M0 @ Matrix.Translation((.44, .1, zf + .031)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    for k in range(3):
        gx["butter"].box((.09, .05, .04), (.46, -.13 + k * .055, zf + .02), M=M0)
    for k in range(4):
        for j in range(2):
            gx["yog" if (k + j) % 2 else "yog2"].cyl(.028, .055, (.06 + k * .065, -.13 + j * .065, zf + .028), r2=.022, verts=12, M=M0)
            gx["lid"].cyl(.03, .006, (.06 + k * .065, -.13 + j * .065, zf + .058), verts=12, M=M0)
    # glass lids (two, overlapping like sliding lids), in thin frames
    for k, (x, z) in enumerate(((-w / 4 + .01, h + .03), (w / 4 - .01, h + .045))):
        gglass.box((w / 2 + .02, d - .08, .006), (x, 0, z), M=M0)
        for sy in (-1, 1): gk.box((w / 2 + .02, .02, .016), (x, sy * (d / 2 - .05), z), M=M0)
        for sx in (-1, 1): gk.box((.02, d - .12, .016), (x + sx * (w / 4 + .01), 0, z), M=M0)


def hanging_scale(gm, gd, gf, gc, top, low=1.35):
    """Feira hanging scale: hook, round dial (blank cream face, red needle), chains and the pan."""
    x, y, zt = top
    gm.tube((x, y, zt), (x, y, low + .52), .005, verts=4)
    gm.torus(.02, .004, (x, y, low + .5), rot=(math.pi / 2, 0, 0), seg=10, rseg=4)
    gm.cyl(.075, .045, (x, y, low + .38), rot=(math.pi / 2, 0, 0), verts=20)            # dial housing
    gf.cyl(.062, .004, (x, y - .024, low + .38), rot=(math.pi / 2, 0, 0), verts=20)      # blank face
    gc.box((.006, .003, .05), (x + .01, y - .028, low + .395), rot=(0, .5, 0))          # needle
    gm.tube((x, y, low + .33), (x, y, low + .24), .006, verts=6)
    for k in range(3):
        a = 2 * math.pi * k / 3
        gm.tube((x, y, low + .24), (x + .13 * math.cos(a), y + .13 * math.sin(a), low + .02), .003, verts=4)
    gd.cyl(.15, .03, (x, y, low), r2=.13, verts=24)


# ================================================================== v2 (Lucas 26/10 19:13): livelier colours, real produce
LIGHT = Vector((.35, -.55, .76)).normalized()          # towards the sun / game camera: painted gloss highlight


def _dot(t, a, b):
    n = t.n.new("ShaderNodeVectorMath"); n.operation = 'DOT_PRODUCT'
    t.plug(n.inputs[0], a); t.plug(n.inputs[1], b); return n.outputs["Value"]


def m_fruit(name, base, shade, light, kind="", gloss=.55, tint=.07):
    """Produce skin, clean and readable from the game camera: soft dark-to-light shading, a painted gloss highlight
    (baked: the game's material is matte), per-fruit tint (Random Per Island = per loose fruit) and per-kind detail:
    orange pores, apple blush streaks, potato eyes, onion papery streaks, banana freckles, lime pores."""
    t = NT(name, .45)
    p = t.pos; nrm = t.geo.outputs["Normal"]
    up = t.ramp(t.comp(nrm, "Z"), -.6, .8)
    col = t.mix(shade, base, up)
    if kind == "apple":                                  # red blush over yellow-green, streaky
        st = t.noise(t.scale(p, 70, 70, 9), 1, 3, .6)
        blush = t.ramp(t.math('ADD', t.math('MULTIPLY', t.comp(nrm, "Z"), .5), t.math('MULTIPLY', st, .7)), .25, .55)
        col = t.mix(C("B9C84A"), col, blush)
    if kind in ("orange", "lime"):                       # pitted peel
        pore = t.vor(p, 520 if kind == "orange" else 650, 'F1', 'Distance')
        col = t.mul(col, t.ramp(pore, .0, .35, .86, 1.0))
    if kind == "potato":                                 # eyes + earthy speckle
        eye = t.vor(p, 34, 'F1', 'Distance')
        col = t.mul(col, t.ramp(t.noise(p, 90, 2), .3, .7, .88, 1.08))
        col = t.mix(col, C("6E4A2A"), t.ramp(eye, .085, .05))
    if kind == "onion":                                  # papery skin: fine streaks along the bulb, light papery top
        st = t.noise(t.scale(p, 130, 130, 6), 1, 3, .5)
        col = t.mul(col, t.ramp(st, .3, .7, .78, 1.12))
        col = t.mix(col, C("D9B48A"), t.ramp(t.comp(nrm, "Z"), .72, .92, 0, .7))
    if kind == "banana":                                 # freckles + green near the stalk end (dark tip separate)
        fr = t.vor(p, 160, 'F1', 'Distance')
        mask = t.ramp(t.noise(p, 9, 2), .55, .7)
        col = t.mix(col, C("8A5A22"), t.math('MULTIPLY', t.ramp(fr, .06, .03), mask))
    if kind == "tomato":                                 # riper deep red at the shoulders, a touch of orange
        col = t.mix(col, C("F2652E"), t.ramp(t.noise(p, 25, 2), .62, .75, 0, .35))
    col = t.tint(col, tint)
    if gloss:
        hl = t.ramp(_dot(t, nrm, LIGHT), .9, .985)
        col = t.mix(col, light, t.math('MULTIPLY', hl, gloss))
    return t.done(col, ao=.25, ao_dist=.06)


def m_plastic(name, col):
    """Coloured plastic fruit crate: clean glossy plastic, slightly lighter on the rims."""
    t = NT(name, .4)
    c = t.mul(col, t.ramp(t.noise(t.pos, 6, 2), .3, .7, .96, 1.03))
    c = t.mix(c, (min(1, col[0] * 1.25), min(1, col[1] * 1.25), min(1, col[2] * 1.25), 1), t.ramp(t.comp(t.geo.outputs["Normal"], "Z"), .7, .95, 0, .5))
    return t.done(c, ao=.4, ao_dist=.15)


def mats_v2():
    """The livelier v2 palette (red / white / yellow / orange / blue / green, natural wood; teal only as an
    accent) and the textured produce skins. Fills EM on top of mats_era()."""
    mats_era()
    E = EM
    E["canR"] = m_canvas("E2_CanvasRed", C("E2382D"), .04)
    E["canW"] = m_canvas("E2_CanvasWhite", C("FFF7EA"), .02)
    E["canY"] = m_canvas("E2_CanvasYellow", C("FFC22E"), .04)
    E["canOr"] = m_canvas("E2_CanvasOrangeV2", C("F7801C"), .04)
    E["canBl"] = m_canvas("E2_CanvasBlue", C("2C6FD1"), .04)
    E["ginghamB"] = m_gingham("E2_GinghamBlue", a=C("FFF8EE"), b=C("2A6CD0"), w=.07)
    E["ginghamR"] = m_gingham("E2_GinghamRed", a=C("FFF8EE"), b=C("D93A2F"), w=.07)
    E["plR"] = m_plastic("E2_PlasticRed", C("E03A2F")); E["plB"] = m_plastic("E2_PlasticBlue", C("2D74D6"))
    E["plG"] = m_plastic("E2_PlasticGreen", C("3FA548")); E["plY"] = m_plastic("E2_PlasticYellow", C("F7C531"))
    E["redP"] = V.m_paint_wood("E2_RedPaint", C("DD3B2F"), C("C9A170"), .12)
    E["yelP"] = V.m_paint_wood("E2_YellowPaint", C("F6C033"), C("C9A170"), .12)
    E["bluP"] = V.m_paint_wood("E2_BluePaint", C("2E6FC4"), C("C9A170"), .12)
    E["grnP"] = V.m_paint_wood("E2_GreenPaint", C("3E9E4A"), C("C9A170"), .12)
    E["coolR"] = V.m_flat("E2_CoolerRed", C("D93A30"), .03, 5, .45, ao=.4)
    E["coolB"] = V.m_flat("E2_CoolerBlue", C("2E73CF"), .03, 5, .45, ao=.4)
    E["frameB"] = V.m_flat("E2_FrameBlue", C("2F6CC0"), .03, 4, .4, ao=.3)
    E["bucketB"] = V.m_flat("E2_BucketBlue", C("2E73CF"), .05, 5, .5, ao=.35)
    E["rope"] = V.m_flat("E2_Rope", C("E6D3A3"), .05, 20, .9, ao=0)
    # the market's brand colours (CheckoutMarketStagesBuilder Navy() / Gold(): MS_NavyPanel #1D2B4F, MS_Gold #D3A53D)
    E["navy"] = m_canvas("E2_CanvasNavy", C("1D2B4F"), .04)
    E["creamB"] = m_canvas("E2_CanvasCreamBrand", C("F7F3EA"), .02)
    E["gold"] = V.m_flat("E2_Gold", C("D6A83E"), .05, 6, .35, ao=0)
    E["navyP"] = V.m_paint_wood("E2_NavyPaint", C("1D2B4F"), C("C9A170"), .1)
    E["navyF"] = V.m_flat("E2_NavyFlat", C("1D2B4F"), .03, 3, .45, ao=.3)
    E["peg"] = V.m_flat("E2_Peg", C("8C9196"), .03, 9, .4, ao=0)
    # produce skins (packed in the atlas, not swatches: they carry detail)
    E["tomato"] = m_fruit("E2_Tomato", C("E3311F"), C("A51E14"), C("FFC7B0"), "tomato", .6)
    E["orange"] = m_fruit("E2_OrangeFruit", C("FA9420"), C("D66A0E"), C("FFE2B0"), "orange", .35)
    E["lime"] = m_fruit("E2_Lime", C("72B835"), C("3F7E1E"), C("E2F7B8"), "lime", .55)
    E["apple"] = m_fruit("E2_Apple", C("D8262C"), C("8E1418"), C("FFD3CF"), "apple", .5)
    E["banana"] = m_fruit("E2_Banana", C("FFD844"), C("D9A41E"), C("FFF6C8"), "banana", .25)
    E["pepper"] = m_fruit("E2_PepperY", C("FFC21F"), C("D98B0B"), C("FFF4C9"), "", .7)
    E["pepperR"] = m_fruit("E2_PepperR", C("E8291D"), C("A11510"), C("FFC9BE"), "", .7)
    E["potato"] = m_fruit("E2_Potato", C("D2A26A"), C("9E7246"), C("EBD3AF"), "potato", 0, .1)
    E["onion"] = m_fruit("E2_Onion", C("A7376E"), C("6A1F47"), C("E7B9CF"), "onion", .25)
    E["calyx"] = V.m_flat("E2_Calyx", C("3F8A2A"), .06, 9, .7, ao=0)
    E["leafO"] = V.m_flat("E2_FruitLeaf", C("3C8F33"), .06, 9, .6, ao=0)
    E["onionTop"] = V.m_flat("E2_OnionTop", C("C9A26E"), .05, 9, .9, ao=0)
    if PALETTE == "navy": mats_navy(E)
    return E


SWATCH_V2 = ["E2_Gold", "E2_PictoRed", "E2_PictoGreen", "E2_PictoBrown", "E2_PictoWhite", "E2_PictoYellow", "E2_PictoBlue",
             "E2_PictoOrange"] + [s for s in SWATCH if s not in ("E2_Tomato", "E2_OrangeFruit", "E2_Lime", "E2_Apple", "E2_Banana", "E2_PepperY",
                                             "E2_Potato", "E2_Onion")] + ["E2_Calyx", "E2_FruitLeaf", "E2_OnionTop", "E2_Rope", "E2_Peg"]
TEXEL_V2 = dict(TEXEL, **{"E2_Tomato": 1.1, "E2_OrangeFruit": 1.1, "E2_Lime": 1.1, "E2_Apple": 1.1, "E2_Banana": 1.0,
                          "E2_PepperY": 1.1, "E2_PepperR": 1.1, "E2_Potato": 1.0, "E2_Onion": 1.1, "E2_CanvasRed": 1.4,
                          "E2_CanvasWhite": 1.4, "E2_CanvasYellow": 1.4, "E2_CanvasOrangeV2": 1.4, "E2_CanvasBlue": 1.3,
                          "E2_GinghamBlue": 2.4, "E2_GinghamRed": 2.4, "E2_PlasticRed": .9, "E2_PlasticBlue": .9,
                          "E2_PlasticGreen": .9, "E2_PlasticYellow": .9, "E2_CoolerRed": .9, "E2_CoolerBlue": .9,
                          "E2_FrameBlue": .6, "E2_BucketBlue": .6, "E2_RedPaint": 1.0, "E2_YellowPaint": 1.0,
                          "E2_BluePaint": 1.0, "E2_GreenPaint": 1.0, "E2_CanvasNavy": 1.4, "E2_CanvasCreamBrand": 1.4,
                          "E2_NavyPaint": 1.0, "E2_NavyFlat": 1.0, "E2_ContainerYellow": 1.0, "E2_ContainerNavy": .8,
                          "E2_LinerCream": .5})


# ------------------------------------------------------------------ the brand palette (v4)
PALETTE = "navy"            # Lucas 26/10 19:57: everything navy-led; "v2" restores the multi-colour palette
NAVY, NAVY2, CREAM, GOLD = C("1D2B4F"), C("2E4A7D"), C("F4EBD8"), C("D3A53D")


def mats_navy(E):
    """Closed palette: navy #1D2B4F dominant, a mid navy #2E4A7D for volumes, cream, gold #D3A53D only on thin details,
    natural wood for tables and racks. Produce keeps its natural colours (the only colour allowed). Drinks / dairy
    in soft tones of the same family. The keys keep their old names so every builder picks the new colours."""
    nf = V.m_flat("E2N_Navy", NAVY, .03, 3, .45, ao=.35)
    n2f = V.m_flat("E2N_Navy2", NAVY2, .03, 3, .45, ao=.35)
    crf = V.m_flat("E2N_Cream", CREAM, .02, 3, .6, ao=0)
    E["navyF"] = nf; E["navy2F"] = n2f; E["creamF"] = crf
    E["navy"] = m_canvas("E2_CanvasNavy", NAVY, .04)
    E["creamB"] = m_canvas("E2_CanvasCreamBrand", CREAM, .02)
    E["canR"] = E["navy"]; E["canW"] = E["creamB"]                       # (also the cooler's cans: navy / cream / gold)
    E["canY"] = m_canvas("E2N_CanvasGold", GOLD, .03)
    E["canOr"] = E["canBl"] = m_canvas("E2N_CanvasNavy2", NAVY2, .04)
    E["canT"] = V.m_flat("E2N_CanCream", C("EDE3CF"), .02, 9, .35, ao=.1)
    E["ginghamB"] = E["ginghamR"] = m_gingham("E2N_GinghamNavy", a=CREAM, b=NAVY, w=.07)
    crate = m_plastic("E2N_CrateNavy", NAVY2)
    for k in ("plR", "plB", "plG", "plY", "crateN"): E[k] = crate
    np_ = V.m_paint_wood("E2_NavyPaint", NAVY, C("C9A170"), .06)
    E["navyP"] = np_
    for k in ("redP", "grnP", "teal"): E[k] = np_
    E["yelP"] = E["cream"] = V.m_paint_wood("E2N_CreamPaint", CREAM, C("C9A170"), .06)
    E["bluP"] = E["orangeP"] = V.m_paint_wood("E2N_Navy2Paint", NAVY2, C("C9A170"), .06)
    for k in ("coolR", "coolB", "bucketB", "bucket", "frameB"): E[k] = nf
    E["regBody"] = E["metalT"] = V.m_metal_paint("E2N_RegNavy", NAVY, amount=.04)
    E["board"] = V.m_flat("E2N_Slate", C("22325A"), .04, 3, .85, ao=.3)
    E["bottle"] = V.m_flat("E2N_BottleSoft", C("A9BCD4"), .03, 9, .2, ao=.1)
    E["cap"] = E["gold"]
    E["sand"] = V.m_flat("E2N_Sandbag", C("E4D9C1"), .05, 7, .9, island=.05, ao=.45)
    E["pot"] = n2f
    E["note"] = V.m_flat("E2N_Note", C("E9DFC8"), .03, 9, .8, ao=0)
    E["chestBody"] = nf
    E["yog"] = V.m_flat("E2N_Yoghurt", C("C9D5E6"), .03, 9, .4, ao=0)
    E["milkBand"] = n2f
    return E


# ------------------------------------------------------------------ produce geometry
def blob(g, M, r, nseg=12, nring=8, mod=None, top_dent=0., bot_dent=0., lump=0., seed=0):
    """Closed fruit body: UV sphere (radii r) with radial modulation mod(theta, phi) (ribs, lobes), dents at the
    top / bottom (stem cavities) and optional noise lumps (potatoes). theta 0 = top."""
    from mathutils import noise
    verts = []
    def P(th, ph):
        m = mod(th, ph) if mod else 1.0
        s, c = math.sin(th), math.cos(th)
        v = Vector((r[0] * s * math.cos(ph) * m, r[1] * s * math.sin(ph) * m, r[2] * c))
        if top_dent: v.z -= top_dent * r[2] * math.exp(-(th / .42) ** 2)
        if bot_dent: v.z += bot_dent * r[2] * math.exp(-((math.pi - th) / .42) ** 2)
        if lump:
            nv = noise.noise(v * (6 / max(r)) + Vector((seed * 3.1, seed * 1.7, seed * .9)))
            v *= 1 + lump * nv
        return v
    top = g.bm.verts.new(P(0, 0)); bot = g.bm.verts.new(P(math.pi, 0))
    rings = []
    for j in range(1, nring):
        th = math.pi * j / nring
        rings.append([g.bm.verts.new(P(th, 2 * math.pi * k / nseg)) for k in range(nseg)])
    for k in range(nseg):
        k1 = (k + 1) % nseg
        g.bm.faces.new((top, rings[0][k], rings[0][k1]))
        g.bm.faces.new((bot, rings[-1][k1], rings[-1][k]))
        for j in range(len(rings) - 1):
            g.bm.faces.new((rings[j][k], rings[j + 1][k], rings[j + 1][k1], rings[j][k1]))
    allv = [top, bot] + [v for rg in rings for v in rg]
    g._put(allv, M)
    return g


def star(g, M, R=.02, r=.008, n=5, t=.004):
    pts = []
    for k in range(2 * n):
        a = math.pi * k / n; rr = R if k % 2 == 0 else r
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    top = [g.bm.verts.new((x, y, t / 2)) for x, y in pts]; bot = [g.bm.verts.new((x, y, -t / 2)) for x, y in pts]
    g.bm.faces.new(top); g.bm.faces.new(list(reversed(bot)))
    for k in range(len(pts)):
        k1 = (k + 1) % len(pts); g.bm.faces.new((top[k], bot[k], bot[k1], top[k1]))
    g._put(top + bot, M)


def leaf(g, M, L=.045, W=.02, t=.003):
    """A single fruit leaf (citrus): pointed oval, slightly folded."""
    pts = []
    for k in range(12):
        a = 2 * math.pi * k / 12
        pts.append(Vector((L / 2 * math.cos(a), W / 2 * math.sin(a) * (1 - .35 * abs(math.cos(a)) ** 3), abs(math.sin(a)) * .004)))
    top = [g.bm.verts.new(p + Vector((0, 0, t / 2))) for p in pts]; bot = [g.bm.verts.new(p - Vector((0, 0, t / 2))) for p in pts]
    g.bm.faces.new(top); g.bm.faces.new(list(reversed(bot)))
    for k in range(12):
        k1 = (k + 1) % 12; g.bm.faces.new((top[k], bot[k], bot[k1], top[k1]))
    g._put(top + bot, M)


FRUIT = {   # kind: (radius, radii scale (x, y, z), material key)
    "tomato": (.041, (1, 1, .8), "tomato"), "orange": (.045, (1, 1, .96), "orange"), "lime": (.032, (1.15, .97, .97), "lime"),
    "apple": (.042, (1, 1, .9), "apple"), "pepper": (.042, (.95, .95, 1.05), "pepper"), "pepperR": (.042, (.95, .95, 1.05), "pepperR"),
    "potato": (.038, (1.3, .95, .78), "potato"), "onion": (.04, (1, 1, .92), "onion"),
}


def fruit(PG, kind, M, r, rnd, lod=1):
    """One piece of produce at frame M (local z up, fruit centre at the origin); PG(key) -> G by material.
    lod 1: 12 x 8 segments, lod 0: 10 x 6 (the stalls with many crates stay in their triangle budget)."""
    _, sc, mk = FRUIT[kind]
    S, Rg = (12, 8) if lod else (10, 6)
    R = (r * sc[0], r * sc[1], r * sc[2])
    if kind == "tomato":
        blob(PG(mk), M, R, 12 if lod else 10, 7 if lod else 6, mod=lambda th, ph: 1 + .055 * math.cos((6 if lod else 5) * ph) * math.sin(th) ** 2, top_dent=.18, bot_dent=.05)
        star(PG("calyx"), M @ Matrix.Translation((0, 0, R[2] * .8)) @ Matrix.Rotation(rnd.uniform(0, 6), 4, 'Z'), R=r * .5, r=r * .16)
        PG("calyx").cyl(.0045, .016, (0, 0, R[2] * .8 + .008), verts=5, M=M)
    elif kind in ("orange", "lime"):
        blob(PG(mk), M, R, S, Rg, top_dent=.04, bot_dent=.03)
        if kind == "orange":
            PG("brown").cyl(.006, .004, (0, 0, R[2] - .001), verts=6, M=M)
            if rnd.random() < .25:
                leaf(PG("leafO"), M @ Matrix.Translation((.018, 0, R[2] + .002)) @ Matrix.Rotation(rnd.uniform(0, 6), 4, 'Z') @ Matrix.Rotation(-.25, 4, 'Y'))
        else:
            PG("calyx").cyl(.006, .01, (R[0] + .002, 0, 0), rot=(0, math.pi / 2, 0), r2=.003, verts=6, M=M)
    elif kind == "apple":
        blob(PG(mk), M, R, S, Rg, mod=lambda th, ph: 1 + .07 * math.cos(th), top_dent=.28, bot_dent=.12)
        PG("brown").tube(M @ Vector((0, 0, R[2] * .7)), M @ Vector((.006, .004, R[2] + .018)), .0028, verts=5)
    elif kind in ("pepper", "pepperR"):
        blob(PG(mk), M, R, 12 if lod else 8, Rg, mod=lambda th, ph: 1 + .09 * math.cos(4 * ph) * math.sin(th), top_dent=.22, bot_dent=.18)
        PG("calyx").cyl(.014, .012, (0, 0, R[2] * .78), verts=8, M=M)
        PG("calyx").tube(M @ Vector((0, 0, R[2] * .8)), M @ Vector((.008, 0, R[2] + .026)), .006, verts=6)
    elif kind == "potato":
        blob(PG(mk), M, R, 10 if lod else 8, 7 if lod else 6, lump=.12, seed=rnd.random() * 50)
    elif kind == "onion":
        blob(PG(mk), M, R, S, Rg, mod=lambda th, ph: 1 + .02 * math.cos(9 * ph) * math.sin(th))
        PG("onionTop").cyl(.012, .03, (0, 0, R[2] + .01), r2=.003, verts=6, M=M @ Matrix.Rotation(rnd.uniform(-.25, .25), 4, 'X'))
        PG("onionTop").cyl(.011, .006, (0, 0, -R[2] + .001), verts=6, M=M)


def heap(PG, M0, w, d, z0, kind, seed, n, zmax=None, scale_var=.12, lod=1, cands=22, sink=.0015):
    """Natural heap with real settling (Lucas 26/10 19:31: no floating fruit). Each piece (its real mesh, built once
    at the origin with its turn) is tried at a few random spots; at each spot it is dropped straight down until
    its first vertex touches the crate floor (exactly) or a piece already placed (rays against a BVH of the placed
    pieces' real meshes, sunk `sink` into them), and the lowest resting spot wins - so lower layers fill first.
    Pieces never reach the crate walls."""
    from mathutils.bvhtree import BVHTree
    rnd = random.Random(seed)
    r0, sc, _ = FRUIT[kind]
    PV, PF = [], []                                   # placed pieces (crate-local): verts, polys
    bvh = None
    down = Vector((0, 0, -1))
    placed = 0
    for i in range(n):
        r = r0 * rnd.uniform(1 - scale_var, 1 + scale_var * .6)
        R = Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z') @ Matrix.Rotation(rnd.uniform(-.25, .25), 4, 'X')
        state = rnd.getstate()
        tmp = {}
        def PT(key):
            if key not in tmp: tmp[key] = G("tmp", None, None)
            return tmp[key]
        fruit(PT, kind, R, r, rnd, lod)
        lv, lf = [], []
        for g in tmp.values():
            g.bm.verts.index_update(); base = len(lv)
            lv += [v.co.copy() for v in g.bm.verts]
            lf += [[base + v.index for v in f.verts] for f in g.bm.faces]
            g.bm.free()
        ex = max(max(abs(v.x) for v in lv), max(abs(v.y) for v in lv)) + .004
        if 2 * ex >= w or 2 * ex >= d: continue
        Z0 = z0 + 2.0
        best = None
        for _ in range(cands):
            x = rnd.uniform(-w / 2 + ex, w / 2 - ex); y = rnd.uniform(-d / 2 + ex, d / 2 - ex)
            drop = 1e9
            for v in lv:
                o = Vector((x + v.x, y + v.y, Z0 + v.z))
                drop = min(drop, o.z - z0 - .0008)                          # floor (touching, 0.8 mm clear)
                if bvh is not None:
                    hit = bvh.ray_cast(o, down)
                    if hit[0] is not None: drop = min(drop, hit[3] + sink)    # resting on a piece below
            zc = Z0 - drop
            if best is None or zc < best[2]: best = (x, y, zc)
        x, y, zc = best
        if zmax is not None and zc > zmax: continue
        rnd.setstate(state)                                                  # same piece, now for real
        fruit(PG, kind, M0 @ Matrix.Translation((x, y, zc)) @ R, r, rnd, lod)
        base = len(PV)
        PV += [Vector((x + v.x, y + v.y, zc + v.z)) for v in lv]
        PF += [[base + k for k in f] for f in lf]
        bvh = BVHTree.FromPolygons(PV, PF)
        placed += 1
    return placed


def pg_factory(NG, prefix):
    cache = {}
    def PG(key):
        if key not in cache:
            cache[key] = NG(prefix + key[0].upper() + key[1:], EM[key])
        return cache[key]
    return PG


# ================================================================== ERA 2 - BANCA (wooden fair stall)
# Frame as Works_BancaBuild builds it (works_banca.py): posts x +-1.65, front y -.95, back y .92; awning back high
# (2.44) -> front low (2.18) with the valance at y -1.15; counter x +-1.42, y -.75 .. +.04, .88 high; the dairy
# chest (built-in "shelf:dairy" from era 2) in front of the counter on the right, like the old ERA2_Freezer.
BAN = "E2 Banca"
BAN_GROUPS = [
    ("ERA2_Stall", ("BAN_post", "BAN_beam", "BAN_awn", "BAN_sign")),
    ("ERA2_Counter", ("BAN_counter",)),
    ("ERA2_Produce", ("BAN_crate", "BAN_fruit", "BAN_wedge", "BAN_tag", "BAN_banana")),
    ("ERA2_Dairy", ("BAN_dairy",)),
    ("ERA2_Register", ("BAN_reg", "BAN_scale")),
    ("ERA2_Stock", ("BAN_stock", "BAN_sack", "BAN_stool", "BAN_melon")),
    ("ERA2_Board", ("BAN_board",)),
]
BAN_GLASS = {"BAN_dairyGlass": "ERA2_DairyGlass"}
BPX, BYF, BYB = 1.65, -.95, .92


def picto_mats():
    """Clean flat colours for painted pictograms (swatch cells, no painted AO: no speckles). Navy palette: the
    pictograms are painted in cream and gold only (no colour outside the brand on signs)."""
    if PALETTE == "navy":
        cr, gd, n2 = C("F4EBD8"), C("D3A53D"), C("2E4A7D")
        return {"red": V.m_flat("E2_PictoRed", cr, .0, 9, .6, ao=0), "green": V.m_flat("E2_PictoGreen", gd, .0, 9, .6, ao=0),
                "brown": V.m_flat("E2_PictoBrown", gd, .0, 9, .6, ao=0), "white": V.m_flat("E2_PictoWhite", cr, .0, 9, .6, ao=0),
                "yellow": V.m_flat("E2_PictoYellow", gd, .0, 9, .6, ao=0), "blue": V.m_flat("E2_PictoBlue", n2, .0, 9, .6, ao=0),
                "orange": V.m_flat("E2_PictoOrange", gd, .0, 9, .6, ao=0)}
    return {"red": V.m_flat("E2_PictoRed", C("E23B2E"), .0, 9, .6, ao=0), "green": V.m_flat("E2_PictoGreen", C("3FA548"), .0, 9, .6, ao=0),
            "brown": V.m_flat("E2_PictoBrown", C("7A4E2A"), .0, 9, .6, ao=0), "white": V.m_flat("E2_PictoWhite", C("FBF8F0"), .0, 9, .6, ao=0),
            "yellow": V.m_flat("E2_PictoYellow", C("F7C531"), .0, 9, .6, ao=0), "blue": V.m_flat("E2_PictoBlue", C("2E73CF"), .0, 9, .6, ao=0),
            "orange": V.m_flat("E2_PictoOrange", C("F7861E"), .0, 9, .6, ao=0)}


def build_banca(scheme="N"):
    mats_v2()
    E = EM
    E["milk"] = V.m_flat("E2_Milk", C("F7F4EC"), .02, 9, .5, ao=0)
    E["cheese"] = m_fruit("E2_Cheese", C("F7C548"), C("D99A22"), C("FFF0BE"), "", .2, .04)
    E["butter"] = V.m_flat("E2_Butter", C("F8E28C"), .03, 9, .5, ao=0)
    E["yog"] = V.m_flat("E2_Yoghurt", C("F29BB4"), .03, 9, .4, ao=0)
    E["well"] = V.m_flat("E2_DairyWell", C("BFE3F2"), .03, 9, .5, ao=.3)
    E["chestBody"] = V.m_flat("E2_ChestRed", C("D93A30"), .03, 5, .45, ao=.4)
    if PALETTE == "navy": mats_navy(E)
    c = col(BAN)
    for o in list(c.all_objects): bpy.data.objects.remove(o)
    gcl = glass_col(BAN)
    todo = []

    def NG(name, mat, **kw):
        g = G(name, mat, c, **kw); todo.append(g); return g
    ca, cb, ct = {"A": ("grnP", "creamB", "gold"), "B": ("canR", "canW", "gold"), "N": ("navy", "creamB", "gold")}[scheme]
    if scheme == "A": E["awnGreen"] = m_canvas("E2_CanvasGreen", C("2E9E4A"), .04); ca = "awnGreen"
    # ---- frame: posts, beams, rafters (natural wood)
    gpo = NG("BAN_post", E["wood"], bevel=.008)
    x0, x1, yf, zf, yb, zb = -1.78, 1.78, -1.15, 2.18, .98, 2.44
    zl = lambda y: zf + (zb - zf) * (y - yf) / (yb - yf)
    for sx in (-1, 1):
        for y, top in ((BYF, zl(BYF) - .1), (BYB, zl(BYB) - .1)):
            gpo.box((.09, .09, top), (sx * BPX, y, top / 2))
        gpo.box((.06, BYB - BYF + .1, .07), (sx * BPX, (BYF + BYB) / 2, (zl(BYF) + zl(BYB)) / 2 - .065), rot=(math.atan2(zb - zf, yb - yf), 0, 0))
    gpo.box((2 * BPX + .12, .07, .08), (0, BYF, zl(BYF) - .06)); gpo.box((2 * BPX + .12, .07, .08), (0, BYB, zl(BYB) - .06))
    for sx in (-1, 1):                                            # knee braces
        gpo.tube((sx * BPX, BYF, 1.7), (sx * (BPX - .35), BYF, zl(BYF) - .1), .02, verts=6)
    # ---- awning (stripes, scalloped valance, piping)
    gA = NG("BAN_awnA", E[ca]); gB = NG("BAN_awnB", E[cb]); gT = NG("BAN_awnTrim", E[ct])
    slope_awning((gA, gB), gT, x0, x1, yb, zb, yf, zf, n=10, sag=.0, hem=True)
    # ---- counter: plank front painted blue, yellow frame, red kick plate, natural wood top, inner shelf
    gcb = NG("BAN_counterBody", E["wood"], bevel=.006, seg=1); gcy = NG("BAN_counterTrim", E["navyP" if PALETTE == "navy" else "yelP"], bevel=.004, seg=1)
    gcr_ = NG("BAN_counterKick", E["wood" if PALETTE == "navy" else "redP"], bevel=.004, seg=1); gct = NG("BAN_counterTop", E["wood"], bevel=.008)
    CX, CY0, CY1, CH = 1.42, -.75, .04, .88
    n = 12
    for k in range(n):
        x = -CX + (k + .5) * 2 * CX / n
        gcb.box((2 * CX / n - .008, .03, CH - .17), (x, CY0 + .015, .1 + (CH - .17) / 2 + .01))
    for sx in (-1, 1):
        gcb.box((.03, CY1 - CY0, CH - .06), (sx * (CX - .015), (CY0 + CY1) / 2, (CH - .06) / 2))
    gcr_.box((2 * CX, .035, .1), (0, CY0 + .0175, .05))
    for z in (.125, CH - .085): gcy.box((2 * CX + .01, .012, .035), (0, CY0 - .006, z))
    for x in (-CX + .02, -CX / 3, CX / 3, CX - .02): gcy.box((.035, .012, CH - .25), (x, CY0 - .006, .125 + (CH - .21) / 2))
    gct.box((2 * CX + .06, CY1 - CY0 + .08, .05), (0, (CY0 + CY1) / 2 - .02, CH - .025))
    gct.box((2 * CX - .1, .3, .025), (0, -.12, .36))                          # inner shelf (stock side)
    # ---- crates tilted towards the customers on wedges, heaped produce
    tilt = math.radians(12); cw, cd, ch = .48, .34, .19
    crates = {"pine": NG("BAN_crate", E["crateN" if PALETTE == "navy" else "pine"], bevel=.004, seg=1), "plG": NG("BAN_crateGreen", E["plG"], bevel=.005, seg=1),
              "plB": NG("BAN_crateBlue", E["plB"], bevel=.005, seg=1), "plY": NG("BAN_crateYellow", E["plY"], bevel=.005, seg=1)}
    gw = NG("BAN_wedge", E["wood"], bevel=.003, seg=1); gtg = NG("BAN_tagCard", E["chalk"])
    PG = pg_factory(NG, "BAN_fruit")
    for k, (x, kind, cm, nn, lod) in enumerate(((-1.17, "tomato", "pine", 22, 1), (-.65, "orange", "plG", 20, 0),
                                                (-.13, "lime", "plB", 24, 0), (.39, "pepperR", "plY", 15, 1))):
        yf_ = -.74
        M0 = _T(x, yf_, CH + .002) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Translation((0, cd / 2, 0))
        crate_rect(crates[cm], M0, cw, cd, ch)
        gw.box((cw - .1, .03, .058), (x, yf_ + cd - .02, CH + .001 + .029))
        gw.box((cw - .09, cd - .046, .012), (0, 0, .044), M=M0)
        heap(PG, M0, cw - .044, cd - .044, .05, kind, 50 + k, nn, lod=lod)
        tag(gtg, None, M0 @ Matrix.Translation((cw / 2 - .085, -cd / 2, ch)))
    # ---- register on the counter (right end), keys towards the clerk
    rb = NG("BAN_regBody", E["regBody"], bevel=.008); rk = NG("BAN_regKey", E["regKey"], bevel=.004, seg=1)
    rd = NG("BAN_regDark", E["dark"], bevel=.004); rc = NG("BAN_regCoin", E["coin"]); rn = NG("BAN_regNote", E["note"])
    retro_register(rb, rk, rd, rc, rn, _T(1.02, -.5, CH + .002, math.pi + .1))
    # ---- dairy chest in front of the counter (right), glass lids in EraGlass
    gx = {"milk": NG("BAN_dairyMilk", E["milk"]), "milkBand": NG("BAN_dairyBandB", E["coolB"]), "milkBand2": NG("BAN_dairyBandR", E["coolR"]),
          "cheese": NG("BAN_dairyCheese", E["cheese"]), "butter": NG("BAN_dairyButter", E["butter"]), "yog": NG("BAN_dairyYog", E["yog"]),
          "yog2": NG("BAN_dairyYogW", E["milk"]), "lid": NG("BAN_dairyLid", E["alu"])}
    gglass = G("BAN_dairyGlass", m_eraglass(), gcl); todo.append(gglass)
    dairy_chest(NG("BAN_dairyBody", E["chestBody"], bevel=.012, seg=2), NG("BAN_dairyBand", E["yelP"], bevel=.006, seg=1),
                NG("BAN_dairyRim", E["rubber"], bevel=.004, seg=1), NG("BAN_dairyWell", E["well"]), gglass, gx, _T(.8, -1.095, 0))
    # ---- hanging scale over the dairy chest, bananas, the hanging sign with pictograms (no words)
    hanging_scale(NG("BAN_scaleMetal", E["pole"]), NG("BAN_scalePan", E["alu"]), NG("BAN_scaleFace", E["chalk"]), NG("BAN_scaleNeedle", E["coolR"]),
                  (1.18, BYF - .02, zl(BYF) - .1), 1.36)
    gbn = NG("BAN_banana", E["banana"]); gbt = NG("BAN_bananaTip", E["brown"]); gh = NG("BAN_bananaHook", E["cord"])
    for bx in (-1.12, -.78):                                  # strings from the front beam (3 mm under it)
        gh.tube((bx, BYF, zl(BYF) - .103), (bx, BYF, 1.72), .004, verts=4)
        gh.cyl(.02, .03, (bx, BYF, 1.715), verts=8)
        for k in range(3):
            banana_bunch(gbn, gbt, _T(bx, BYF, 1.70, .6 + k * 2.1) @ Matrix.Rotation(math.pi / 2 - .25, 4, 'Y'), 4, .17, 61 + k + int(abs(bx) * 10))
    gsf = NG("BAN_signFrame", E["gold"], bevel=.006); gsb = NG("BAN_signBoard", E["navyF"], bevel=.004)
    gsr = NG("BAN_postRope", E["rope"])
    sx0, sx1, sz0, sz1, sy = -.45, .75, 1.42, 1.7, BYF - .02
    gsb.box((sx1 - sx0, .025, sz1 - sz0), ((sx0 + sx1) / 2, sy, (sz0 + sz1) / 2))
    for z in (sz0, sz1): gsf.box((sx1 - sx0 + .04, .035, .03), ((sx0 + sx1) / 2, sy, z))
    for x in (sx0, sx1): gsf.box((.03, .035, sz1 - sz0), (x, sy, (sz0 + sz1) / 2))
    for x in (sx0 + .12, sx1 - .12): gsr.tube((x, sy, sz1 + .02), (x, BYF, zl(BYF) - .095), .005, verts=4)
    pm = picto_mats()
    gp = {k: NG("BAN_sign" + k.capitalize(), pm[k]) for k in pm}
    for k, kind in enumerate(("apple", "carrot", "milk", "cheese")):
        Mp = Matrix.Translation((sx0 + (k + .5) * (sx1 - sx0) / 4, sy - .0125, (sz0 + sz1) / 2)) @ Matrix.Rotation(math.pi / 2, 4, 'X')
        pict(gp, Mp, kind, 1.05)
    # ---- A-frame board (front left) with a cheese pictogram... an apple
    gp2 = {k: NG("BAN_board" + k.capitalize(), pm[k]) for k in ("red", "green", "brown", "white")}
    ab_board(NG("BAN_boardFrame", E["wood"], bevel=.004), NG("BAN_boardSlate", E["board"]), gp2, _T(-1.0, -.98, .54, -.12))
    # ---- back: stock crates with watermelons (right), box + sack (left), stool for the seller
    gs2 = NG("BAN_stockCrate", E["plR"], bevel=.005, seg=1)
    gml = NG("BAN_melonD", E["melonD"]); gmd = NG("BAN_melonL", E["melonL"])
    Mk = _T(1.32, .5, 0, .08); crate_rect(gs2, Mk, .5, .38, .26)
    for j in range(2):
        melon(gml, gmd, Mk @ Matrix.Translation((-.11 + .22 * j, 0, .03 + .125)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'), (.165, .11, .115))
    gbx = NG("BAN_stockBox", E["card"], bevel=.008)
    gbx.box((.48, .38, .34), (-1.38, .5, .17), rot=(0, 0, -.06)); gbx.box((.486, .19, .006), (-1.38, .5, .343), rot=(.05, 0, -.06))
    gsk = NG("BAN_sack", E["burlap"], bevel=.06, seg=3)
    gsk.box((.36, .28, .4), (-.8, .62, .2), rot=(0, 0, .25)); gsk.box((.11, .09, .09), (-.8, .62, .44), rot=(0, 0, .25))
    gsl = NG("BAN_stool", E["redP"])
    gsl.cyl(.17, .04, (.25, .45, .48), verts=20)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        gsl.tube((.25 + .15 * math.cos(a), .45 + .15 * math.sin(a), 0), (.25 + .1 * math.cos(a), .45 + .1 * math.sin(a), .46), .018, verts=6)
    for gg in todo:
        if len(gg.bm.verts): gg.done()
        else: gg.bm.free()
    for o in c.all_objects:
        if o.type == 'MESH' and any(k in o.name for k in ("fruit", "melon", "banana", "Can", "reg", "dairy", "scale")):
            for p in o.data.polygons: p.use_smooth = True
    return V.stats(c)


ERAS = {"Era0_Mesinha": ("E2 Mesinha", "MES_GROUPS", "ERA0_Produce", None), "Era1_Tenda": ("E2 Tenda", "TEN_GROUPS", "ERA1_Stock", None),
        "Era2_Banca": ("E2 Banca", "BAN_GROUPS", "ERA2_Stock", "BAN_GLASS"),
        "Era3_Conteiner": ("E2 Conteiner", "CON_GROUPS", "ERA3_Stock", "CON_GLASS"),
        "Era4_Spati": ("E2 Spati", "SPA_GROUPS", "ERA4_Facade", "SPA_GLASS")}


def step(name, st):
    """export_era() for a registered era, plus its glass panes (EraGlass) right before the FBX is written."""
    src, groups, default, glass = ERAS[name]
    if st == "fbx" and glass:
        print("glass:", add_glass(src, name, globals()[glass]))
    return export_era(src, name, globals()[groups], default, st)


# ================================================================== ERA 3 - CONTÊINER (container kiosk)
# Same plan as the old Era3_Conteiner: a 3.04 x 2.04 container (x +-1.52, y -.67 .. 1.37) on the lot, service hatch
# in the front wall over a counter (y -.9 .. -.42, top 1.03), produce rack under the counter outside, snacks shelf
# (built-in "shelf:snacks" from era 3), a drinks fridge and a dairy chest inside. As the old model: everything
# above 1.1 m (upper walls, roof, awning, sign) is CUT_* so the game hides it and the camera sees inside.
CON = "E2 Conteiner"
CON_GROUPS = [
    ("ERA3_Shell", ("CON_shell",)),
    ("CUT_ERA3_ShellTop", ("CON_shellTop",)),
    ("CUT_ERA3_Awning", ("CON_awn",)),
    ("CUT_ERA3_Sign", ("CON_signTop",)),
    ("ERA3_Counter", ("CON_counter",)),
    ("ERA3_Register", ("CON_reg",)),
    ("ERA3_Produce", ("CON_rack", "CON_crate", "CON_fruit", "CON_wedge", "CON_tag")),
    ("ERA3_Shelf", ("CON_snack",)),
    ("ERA3_Fridge", ("CON_fridge",)),
    ("ERA3_Dairy", ("CON_dairy",)),
    ("ERA3_Plants", ("CON_bush",)),
    ("ERA3_Stock", ("CON_stool", "CON_box")),
]
CON_GLASS = {"CON_fridgeGlass": "ERA3_FridgeGlass", "CON_dairyGlass": "ERA3_DairyGlass"}
CX0, CX1, CY0, CY1, CFL, CCUT, CTOP = -1.52, 1.52, -.67, 1.37, .14, 1.1, 2.6


def snack_bag(g, gw, M, w=.11, h=.15, d=.045):
    """Crinkly snack bag (pillow) standing up; gw: the white window stripe (no print)."""
    g.box((w, d, h), (0, 0, h / 2), M=M)
    g.box((w * 1.02, d * .5, .012), (0, 0, h + .004), M=M)
    gw.box((w * .55, .004, h * .22), (0, -d / 2 - .001, h * .5), M=M)


def build_conteiner():
    mats_v2()
    E = EM
    E["contY"] = V.m_flat("E2_ContainerYellow", C("F4B532"), .03, 2, .45, ao=.4)      # clean paint (no rust blotches)
    E["contN"] = V.m_flat("E2_ContainerNavy", C("1D2B4F"), .03, 3, .45, ao=.3)
    E["liner"] = V.m_flat("E2_LinerCream", C("F3E7CF"), .03, 3, .8, ao=.45)
    E["fridgeIn"] = V.m_flat("E2_FridgeInside", C("D8ECF4"), .02, 6, .4, ao=.35)
    E["milk"] = V.m_flat("E2_Milk", C("F7F4EC"), .02, 9, .5, ao=0)
    E["cheese"] = m_fruit("E2_Cheese", C("F7C548"), C("D99A22"), C("FFF0BE"), "", .2, .04)
    E["butter"] = V.m_flat("E2_Butter", C("F8E28C"), .03, 9, .5, ao=0)
    E["yog"] = V.m_flat("E2_Yoghurt", C("F29BB4"), .03, 9, .4, ao=0)
    E["well"] = V.m_flat("E2_DairyWell", C("BFE3F2"), .03, 9, .5, ao=.3)
    snack = [m_plastic("E2_Snack" + k, C(h)) for k, h in (("Red", "E5372C"), ("Yellow", "F8C531"), ("Blue", "2E6FD6"),
                                                           ("Green", "3DAA47"), ("Orange", "F7841D"), ("Purple", "8B4BB8"))]
    if PALETTE == "navy":
        mats_navy(E)
        E["contY"] = V.m_flat("E2N_ContainerNavy", NAVY, .03, 2, .45, ao=.4)
        E["contN"] = V.m_flat("E2N_ContainerCream", C("EFE5CF"), .02, 3, .5, ao=.3)
        snack = [m_plastic("E2N_Snack" + k, C(h)) for k, h in (("Navy", "2E4A7D"), ("Cream", "F1E6CF"), ("Gold", "D3A53D"),
                                                                ("NavyB", "3A5890"), ("CreamB", "E6D8BA"), ("GoldB", "C8993A"))]
    c = col(CON)
    for o in list(c.all_objects): bpy.data.objects.remove(o)
    lc = bpy.context.view_layer.layer_collection.children.get(CON)
    if lc: lc.exclude = False          # (city_tree() applies its Decimate through the depsgraph: must be evaluated)
    gcl = glass_col(CON)
    todo = []

    def NG(name, mat, **kw):
        g = G(name, mat, c, **kw); todo.append(g); return g
    # ---- container: navy base rails, corner posts and castings, corrugated yellow walls (lower / upper CUT),
    #      cream liner inside, plank floor, a gold cap on the low walls (the edge the game shows)
    gb = NG("CON_shellBase", E["contN"], bevel=.01)
    for y in (CY0 + .05, CY1 - .05): gb.box((CX1 - CX0 - .26, .1, CFL - .03), (0, y, (CFL - .03) / 2))
    for x in (CX0 + .05, CX1 - .05): gb.box((.1, CY1 - CY0 - .26, CFL - .03), (x, (CY0 + CY1) / 2, (CFL - .03) / 2))
    gpo = NG("CON_shellPost", E["contN"], bevel=.01); gpt = NG("CON_shellTopPost", E["contN"], bevel=.01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (CX1 - .06), (CY1 - .06) if sy > 0 else (CY0 + .06)
            gpo.box((.12, .12, CCUT - .01), (x, y, (CCUT - .01) / 2))
            gpt.box((.12, .12, CTOP - CCUT - .01), (x, y, CCUT + .005 + (CTOP - CCUT - .01) / 2))
    gS = NG("CON_shellWall", E["contY"]); gST = NG("CON_shellTopWall", E["contY"])
    gL = NG("CON_shellLiner", E["liner"]); gLT = NG("CON_shellTopLiner", E["liner"])
    def wall(gw, gl, axis, pos, a0, a1, z0, z1, side):
        L = z1 - z0; w = a1 - a0; mid = (a0 + a1) / 2
        if axis == 'y':        # front / back wall (normal +-y)
            gw.corrugated(w, L, (mid, pos, (z0 + z1) / 2), rot=(math.pi / 2, 0, 0), pitch=.16, amp=.018, seg=3, t=.01)
            gl.box((w, .02, L), (mid, pos - side * .05, (z0 + z1) / 2))
        else:
            gw.corrugated(w, L, (pos, mid, (z0 + z1) / 2), rot=(math.pi / 2, 0, math.pi / 2), pitch=.16, amp=.018, seg=3, t=.01)
            gl.box((.02, w, L), (pos - side * .05, mid, (z0 + z1) / 2))
    ox, oy0, oy1 = CX1 - .02, CY0 + .02, CY1 - .02
    for gw, gl, z0, z1 in ((gS, gL, CFL - .03, CCUT - .01), (gST, gLT, CCUT + .01, CTOP - .14)):
        wall(gw, gl, 'y', oy1, CX0 + .13, CX1 - .13, z0, z1, 1)                                 # back
        for sx in (-1, 1): wall(gw, gl, 'x', sx * ox, CY0 + .13, CY1 - .13, z0, z1, sx)        # sides
    wall(gS, gL, 'y', oy0, CX0 + .13, CX1 - .13, CFL - .03, .965, -1)                            # front, under the hatch
    for sx in (-1, 1):                                                                          # beside the hatch
        a0, a1 = (CX0 + .13, -1.3) if sx < 0 else (1.3, CX1 - .13)
        wall(gS, gL, 'y', oy0, a0, a1, .965, CCUT - .01, -1); wall(gST, gLT, 'y', oy0, a0, a1, CCUT + .01, 2.1, -1)
    wall(gST, gLT, 'y', oy0, CX0 + .13, CX1 - .13, 2.1, CTOP - .14, -1)                           # over the hatch
    gST.corrugated(CX1 - CX0 - .04, CY1 - CY0 - .04, (0, (CY0 + CY1) / 2, CTOP - .06), pitch=.2, amp=.02, seg=4, t=.01)   # roof
    gtr = NG("CON_shellTopRail", E["contN"], bevel=.01)
    for y in (CY0 + .05, CY1 - .05): gtr.box((CX1 - CX0 - .24, .1, .1), (0, y, CTOP - .09))
    for x in (CX0 + .05, CX1 - .05): gtr.box((.1, CY1 - CY0 - .2, .1), (x, (CY0 + CY1) / 2, CTOP - .09))
    gcap = NG("CON_shellCap", E["gold"], bevel=.004)                                                 # cap of the low walls
    for y in (CY1 - .035,): gcap.box((CX1 - CX0 - .26, .05, .014), (0, y, CCUT + .0005))
    for sx in (-1, 1): gcap.box((.05, CY1 - CY0 - .26, .014), (sx * (CX1 - .05), (CY0 + CY1) / 2, CCUT + .0005))
    for a0, a1 in ((CX0 + .13, -1.3), (1.3, CX1 - .13)): gcap.box((a1 - a0, .05, .014), ((a0 + a1) / 2, CY0 + .045, CCUT + .0005))
    gfl = NG("CON_shellFloor", E["wood"], bevel=.004, seg=1)
    for k in range(10):
        y0_ = CY0 + .1 + k * (CY1 - CY0 - .2) / 10
        gfl.box((CX1 - CX0 - .2, (CY1 - CY0 - .2) / 10 - .006, .03), (0, y0_ + (CY1 - CY0 - .2) / 20, CFL - .016))
    # ---- hatch counter + register
    gct = NG("CON_counterTop", E["wood"], bevel=.008); gce = NG("CON_counterEdge", E["gold"], bevel=.003)
    gct.box((2.58, .48, .06), (0, -.66, 1.0))
    gce.box((2.6, .012, .03), (0, -.906, 1.0))
    rb = NG("CON_regBody", E["regBody"], bevel=.008); rk = NG("CON_regKey", E["regKey"], bevel=.004, seg=1)
    rd = NG("CON_regDark", E["dark"], bevel=.004); rc = NG("CON_regCoin", E["coin"]); rn = NG("CON_regNote", E["note"])
    retro_register(rb, rk, rd, rc, rn, _T(.86, -.6, 1.031, math.pi + .1))
    # ---- produce rack under the counter, outside (front left), three tilted crates with heaped produce
    gra = NG("CON_rack", E["wood"], bevel=.005, seg=1)
    rx0, rx1, ry0, ry1, rz = -1.12, .4, -1.27, -.92, .4
    for x in (rx0 + .03, rx1 - .03):
        for y in (ry0 + .03, ry1 - .03): gra.box((.045, .045, rz), (x, y, rz / 2))
    for k in range(5): gra.box((rx1 - rx0, (ry1 - ry0) / 5 - .01, .02), ((rx0 + rx1) / 2, ry0 + (k + .5) * (ry1 - ry0) / 5, rz + .01))
    gra.box((rx1 - rx0 - .06, .03, .03), ((rx0 + rx1) / 2, ry0 + .03, .12)); gra.box((rx1 - rx0 - .06, .03, .03), ((rx0 + rx1) / 2, ry1 - .03, .12))
    crates = {"pine": NG("CON_crate", E["crateN" if PALETTE == "navy" else "pine"], bevel=.004, seg=1), "plR": NG("CON_crateRed", E["plR"], bevel=.005, seg=1),
              "plB": NG("CON_crateBlue", E["plB"], bevel=.005, seg=1)}
    gw = NG("CON_wedge", E["wood"], bevel=.003, seg=1); gtg = NG("CON_tagCard", E["chalk"])
    PG = pg_factory(NG, "CON_fruit")
    tilt = math.radians(12); cw, cd, ch = .46, .32, .18
    for k, (x, kind, cm, nn, lod) in enumerate(((-.85, "tomato", "pine", 20, 0), (-.36, "orange", "plB", 18, 0), (.13, "lime", "plR", 22, 0))):
        yf_ = ry0 + .025
        M0 = _T(x, yf_, rz + .021) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Translation((0, cd / 2, 0))
        crate_rect(crates[cm], M0, cw, cd, ch)
        gw.box((cw - .1, .03, .058), (x, yf_ + cd - .02, rz + .021 + .029))
        gw.box((cw - .09, cd - .046, .012), (0, 0, .044), M=M0)
        heap(PG, M0, cw - .044, cd - .044, .05, kind, 70 + k, nn, lod=lod)
        tag(gtg, None, M0 @ Matrix.Translation((cw / 2 - .085, -cd / 2, ch)))
    # ---- inside: snacks shelf on the back wall (left), drinks fridge (right), dairy chest (left), stool, boxes
    gsh = NG("CON_snackShelf", E["pine"], bevel=.005, seg=1); glp = NG("CON_snackLip", E["redP"], bevel=.003, seg=1)
    sx0, sx1, sy0, sy1 = -1.36, .1, 1.02, 1.28
    for x in (sx0, sx1): gsh.box((.03, sy1 - sy0, 1.68), (x, (sy0 + sy1) / 2, CFL + .84))
    gsh.box((sx1 - sx0, .02, 1.68), ((sx0 + sx1) / 2, sy1 - .01, CFL + .84))
    levels = [CFL + .08, .52, .88, 1.24, 1.6]
    for z in levels:
        gsh.box((sx1 - sx0 - .03, sy1 - sy0 - .02, .025), ((sx0 + sx1) / 2, (sy0 + sy1) / 2 - .01, z))
        glp.box((sx1 - sx0 - .03, .012, .04), ((sx0 + sx1) / 2, sy0 - .004, z + .005))
    rnd = random.Random(9)
    gsn = [NG("CON_snack" + str(i), snack[i], bevel=.014, seg=1) for i in range(len(snack))]
    gwin = NG("CON_snackWindow", E["milk"])
    for li, z in enumerate(levels[:-1]):
        x = sx0 + .07
        while x < sx1 - .08:
            kind = rnd.random()
            if kind < .7:
                w = rnd.uniform(.09, .12); i = rnd.randrange(len(snack))
                for r in range(1):
                    snack_bag(gsn[i], gwin, _T(x + w / 2, sy0 + .08, z + .013, rnd.uniform(-.08, .08)) @ Matrix.Rotation(-.1, 4, 'X'), w, rnd.uniform(.14, .18), .085)
                x += w + .015
            else:
                w = .1; i = rnd.randrange(len(snack))
                gsn[i].box((w, .16, .22), (x + w / 2, sy0 + .11, z + .013 + .11))
                gwin.box((w * .5, .004, .05), (x + w / 2, sy0 + .029, z + .013 + .13))
                x += w + .015
    # drinks fridge: red body, yellow header, light inside, glass door (EraGlass), bottles and cans on 4 shelves
    fx0, fx1, fy0, fy1, fz1 = .58, 1.34, .52, 1.28, 1.86
    gfb = NG("CON_fridgeBody", E["coolR"], bevel=.012); gfh = NG("CON_fridgeHeader", E["creamF" if PALETTE == "navy" else "contY"], bevel=.006)
    gfi = NG("CON_fridgeIn", E["fridgeIn"]); gfg = NG("CON_fridgeHandle", E["gold"], bevel=.004)
    t = .05
    gfb.box((fx1 - fx0, t, fz1 - CFL), ((fx0 + fx1) / 2, fy1 - t / 2, (fz1 + CFL) / 2))
    for x in (fx0 + t / 2, fx1 - t / 2): gfb.box((t, fy1 - fy0 - t, fz1 - CFL), (x, (fy0 + fy1) / 2 - t / 2 + .0, (fz1 + CFL) / 2))
    gfb.box((fx1 - fx0 - 2 * t, fy1 - fy0 - t, .12), ((fx0 + fx1) / 2, (fy0 + fy1) / 2 - t / 2, CFL + .06))
    gfh.box((fx1 - fx0, fy1 - fy0, .14), ((fx0 + fx1) / 2, (fy0 + fy1) / 2, fz1 - .07))
    gfi.box((fx1 - fx0 - 2 * t, .01, fz1 - CFL - .26), ((fx0 + fx1) / 2, fy1 - t - .005, CFL + .12 + (fz1 - CFL - .26) / 2))
    shelves = [CFL + .12 + .02, .62, .98, 1.33]
    canm = {k: NG("CON_fridgeCan" + k.capitalize(), E[k]) for k in ("canR", "canT", "canY", "alu", "bottle", "cap")}
    for z in shelves[1:]: gfi.box((fx1 - fx0 - 2 * t - .004, fy1 - fy0 - t - .08, .015), ((fx0 + fx1) / 2, (fy0 + fy1) / 2 - t / 2 + .02, z))
    for si, z in enumerate(shelves):
        zz = z + .008 + (.0 if si == 0 else .0)
        for k in range(5):
            x = fx0 + t + .06 + k * .125
            for r in range(2):
                y = fy0 + .14 + r * .2
                if (si + k) % 2 == 0:
                    Mb = Matrix.Translation((x, y, zz + .0))
                    canm["bottle"].cyl(.032, .17, (0, 0, .085), verts=10, M=Mb)
                    canm["bottle"].cyl(.032, .05, (0, 0, .195), r2=.013, verts=10, M=Mb)
                    canm["cap"].cyl(.015, .02, (0, 0, .23), verts=8, M=Mb)
                else:
                    canm[("canR", "canT", "canY")[(k + r + si) % 3]].cyl(.033, .12, (x, y, zz + .06), verts=12)
                    canm["alu"].cyl(.029, .006, (x, y, zz + .123), verts=12)
    gglass = G("CON_fridgeGlass", m_eraglass(), gcl); todo.append(gglass)
    gglass.box((fx1 - fx0 - .1, .012, fz1 - CFL - .3), ((fx0 + fx1) / 2, fy0 + .01, CFL + .14 + (fz1 - CFL - .3) / 2))
    for z in (CFL + .13, fz1 - .155): gfb.box((fx1 - fx0, .03, .03), ((fx0 + fx1) / 2, fy0 + .01, z))
    for x in (fx0 + .03, fx1 - .03): gfb.box((.05, .03, fz1 - CFL - .3), (x, fy0 + .01, CFL + .14 + (fz1 - CFL - .3) / 2))
    gfg.box((.025, .03, .5), (fx0 + .09, fy0 - .02, 1.0))
    # dairy chest (built-in from era 2) inside on the left
    gx = {"milk": NG("CON_dairyMilk", E["milk"]), "milkBand": NG("CON_dairyBandB", E["coolB"]), "milkBand2": NG("CON_dairyBandR", E["coolR"]),
          "cheese": NG("CON_dairyCheese", E["cheese"]), "butter": NG("CON_dairyButter", E["butter"]), "yog": NG("CON_dairyYog", E["yog"]),
          "yog2": NG("CON_dairyYogW", E["milk"]), "lid": NG("CON_dairyLid", E["alu"])}
    gdg = G("CON_dairyGlass", m_eraglass(), gcl); todo.append(gdg)
    dairy_chest(NG("CON_dairyBody", E["coolB"], bevel=.012, seg=2), NG("CON_dairyBand", E["yelP"], bevel=.006, seg=1),
                NG("CON_dairyRim", E["rubber"], bevel=.004, seg=1), NG("CON_dairyWell", E["well"]), gdg, gx,
                _T(-1.0, .42, CFL) @ Matrix.Diagonal((.72, .9, 1, 1)))
    gsl = NG("CON_stool", E["redP"])
    gsl.cyl(.15, .04, (.15, -.05, .62), verts=20)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        gsl.tube((.15 + .13 * math.cos(a), -.05 + .13 * math.sin(a), CFL + .002), (.15 + .09 * math.cos(a), -.05 + .09 * math.sin(a), .6), .016, verts=6)
    gbx = NG("CON_box", E["card"], bevel=.008)
    gbx.box((.38, .3, .3), (.34, .98, CFL + .15), rot=(0, 0, .05)); gbx.box((.34, .28, .26), (.34, .98, CFL + .3 + .131), rot=(0, 0, -.08))
    # ---- potted bushes at the front corners (the city tree's crown)
    gpot = NG("CON_bushPot", E["pot"], bevel=.01, seg=1); gsoil = NG("CON_bushSoil", V.M["dirt"])
    for k, sx in enumerate((-1, 1)):
        px, py = sx * 1.36, -1.04
        gpot.cyl(.15, .28, (px, py, .14), r2=.18, verts=20); gpot.torus(.18, .015, (px, py, .28), seg=20, rseg=5)
        gsoil.cyl(.165, .02, (px, py, .265), verts=20)
        V.city_tree("CON_bush" + str(k), c, (px, py, .24), 1, rot_z=k * 2.1, tris=1200, crown_only=True, width=.46)
    # ---- CUT_: awning over the hatch (red / white stripes, gold piping) on two gold arms, the sign on the roof
    gA = NG("CON_awnRed", E["canR"]); gB = NG("CON_awnWhite", E["canW"]); gT = NG("CON_awnTrim", E["gold"])
    slope_awning((gA, gB), gT, -1.42, 1.42, CY0 - .03, 2.3, -1.27, 1.98, n=8, sag=0., hem=True)
    for x in (-1.3, 1.3): gT.tube((x, CY0 - .035, 1.95), (x, -1.2, 2.0), .012, verts=6)
    gsg = NG("CON_signTopBoard", E["navyF" if PALETTE == "navy" else "contN"], bevel=.006); gsf = NG("CON_signTopFrame", E["gold"], bevel=.005)
    gsg.box((2.3, .05, .5), (0, CY0 + .2, CTOP + .32)); gsf.box((2.36, .06, .04), (0, CY0 + .2, CTOP + .06)); gsf.box((2.36, .06, .04), (0, CY0 + .2, CTOP + .58))
    for x in (-1.16, 1.16): gsf.box((.04, .06, .56), (x, CY0 + .2, CTOP + .32))
    for x in (-.8, .8): gsf.box((.05, .3, .08), (x, CY0 + .32, CTOP + .01))
    pm = picto_mats()
    gp = {k: NG("CON_signTop" + k.capitalize(), pm[k]) for k in pm}
    for k, kind in enumerate(("apple", "milk", "carrot", "cheese")):
        pict(gp, Matrix.Translation((-.75 + k * .5, CY0 + .2 - .026, CTOP + .32)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), kind, 1.6)
    for gg in todo:
        if len(gg.bm.verts): gg.done()
        else: gg.bm.free()
    for o in c.all_objects:
        if o.type == 'MESH' and any(k in o.name for k in ("fruit", "Can", "reg", "dairy", "snack", "Wall", "awn")):
            for p in o.data.polygons: p.use_smooth = True
    return V.stats(c)


def sheet(names=("Era0_Mesinha", "Era1_Tenda", "Era2_Banca", "Era3_Conteiner"), out="eras_palette_navy_all", gap=1.4):
    """The re-imported exports side by side (fronts on one line, as the game shows them: CUT_* off), one iso camera."""
    stage(); stage_pavers()
    show_only(*["NEW " + n for n in names])
    roots = []; x = 0.
    for n in names:
        objs = game_objs("NEW " + n); lo, hi = bounds(objs)
        r = bpy.data.objects["NEWROOT_" + n]
        r.location = (r.location.x + x - lo.x, r.location.y - lo.y, 0); roots.append((r, n))
        x += (hi.x - lo.x) + gap
    bpy.context.view_layer.update()
    show_only(*["NEW " + n for n in names])
    cut = [o for n in names for o in game_hidden("NEW " + n)]
    for o in cut: o.hide_render = True
    try:
        allo = [o for n in names for o in game_objs("NEW " + n)]
        lo, hi = bounds(allo); cc = (lo + hi) / 2
        camera((cc.x, cc.y, .9), (hi.x - lo.x) * .9, GAME_DIR, res=(2600, 1300))
        p = render(out)
    finally:
        for o in cut: o.hide_render = False
        for r, n in roots: r.location = (0, 0, 0)
    return p


# ================================================================== ERA 4 - CONVENIÊNCIA (Späti): a small walk-in shop
# CheckoutStall.Plans["Era4_Spati"] (model metres, x right, y = Unity z, front -y): inner floor x -2.85..2.85,
# y -1.12..2.25 (wall to wall), door opening x .72..1.62 in the front wall, the fixed counter in x 1.3..3.03,
# y 0..1.4 (register + clerk's stool), pay point (2.15, -.35), queue towards -x, floor top .06. The model's bounds
# must stay x +-3.03, y -2.12..2.42 (Place() puts their min y on the front line and centres them in x): the produce
# stand outside the shop window reaches y -2.12 as the old table did. Everything above 1.1 m is CUT_* (hidden in the
# game so the camera sees the interior, which stays empty for the player's shelves).
SPA = "E2 Spati"
SPA_PLAN = {"floor": (-2.85, -1.12, 2.85, 2.25), "door": (.72, 1.62), "counter": (1.3, 0., 3.03, 1.4), "pay": (2.15, -.35),
            "queue": (-.75, 0.), "floorY": .06}
SPA_GROUPS = [
    ("ERA4_Facade", ("SPA_wall", "SPA_base", "SPA_cap", "SPA_floor", "SPA_frame", "SPA_door", "SPA_mat", "SPA_bush")),
    ("CUT_ERA4_FacadeTop", ("SPA_top",)),
    ("CUT_ERA4_Awning", ("SPA_awn",)),
    ("CUT_ERA4_Sign", ("SPA_sign",)),
    ("ERA4_Counter", ("SPA_counter",)),
    ("ERA4_Counter_Register", ("SPA_reg",)),
    ("ERA4_Counter_Stool", ("SPA_stool",)),
    ("ERA4_Table", ("SPA_stand", "SPA_crate", "SPA_fruit", "SPA_wedge", "SPA_tag")),
]
SPA_GLASS = {"SPA_glassWin": "ERA4_Glass_win", "SPA_glassDoor": "ERA4_Glass_door", "SPA_topGlass": "CUT_ERA4_Glass_winTop"}
CUT_SRC = CUT_SRC + ("SPA_top", "SPA_awn", "SPA_sign")


def m_plaster_navy(name, paint):
    """Clean painted plaster for the shop walls (lots_v3 plaster without chips), world-space soft tone shift."""
    return V.m_plaster(name, paint, chips=0., fine=.012)


def build_spati():
    mats_v2()
    E = EM
    E["wallN"] = V.m_flat("E2N_SpatiWallNavy", NAVY, .03, 1.2, .8, ao=.35)       # clean new paint, no chips
    E["wallC"] = V.m_flat("E2N_SpatiWallCream", CREAM, .02, 1.2, .8, ao=.35)
    E["stone"] = V.m_flat("E2N_SpatiBase", C("ECE1CA"), .04, 2, .85, island=.03, ao=.35)
    E["tile"] = V.m_flat("E2N_FloorTile", C("F1E8D5"), .03, 3, .7, island=.05, ao=.35)
    E["tileN"] = V.m_flat("E2N_FloorTileNavy", NAVY2, .03, 3, .7, island=.05, ao=.35)
    E["mat"] = V.m_flat("E2N_Doormat", C("3A4F78"), .05, 30, .95, ao=.3)
    c = col(SPA)
    for o in list(c.all_objects): bpy.data.objects.remove(o)
    lc = bpy.context.view_layer.layer_collection.children.get(SPA)
    if lc: lc.exclude = False
    gcl = glass_col(SPA)
    todo = []

    def NG(name, mat, **kw):
        g = G(name, mat, c, **kw); todo.append(g); return g
    fx0, fy0, fx1, fy1 = SPA_PLAN["floor"]; d0, d1 = SPA_PLAN["door"]
    T = .15                                            # wall thickness: outer faces x +-3.0 (+ the stone base to 3.03)
    ox0, ox1, oy0, oy1 = fx0 - T, fx1 + T, fy0 - T, fy1 + T
    LOW, TOP = 1.1, 2.75
    FL = SPA_PLAN["floorY"]
    # ---- floor: slab under everything, cream tiles with a navy border row inside
    gfs = NG("SPA_floorSlab", E["stone"], bevel=.01)
    gfs.box((ox1 - ox0, oy1 - oy0, FL - .002), (0, (oy0 + oy1) / 2, (FL - .002) / 2))
    gft = NG("SPA_floorTile", E["tile"]); gfn = NG("SPA_floorTileNavy", E["tileN"])
    ts = .4; nx = int(round((fx1 - fx0) / ts)); ny = int(round((fy1 - fy0) / ts))
    sx, sy = (fx1 - fx0) / nx, (fy1 - fy0) / ny
    for i in range(nx):
        for j in range(ny):
            g = gfn if (i in (0, nx - 1) or j in (0, ny - 1)) else gft
            g.box((sx - .008, sy - .008, .004), (fx0 + (i + .5) * sx, fy0 + (j + .5) * sy, FL - .002))
    gfs.box((d1 - d0, T, .004), ((d0 + d1) / 2, fy0 - T / 2, FL - .002))                       # threshold
    # ---- walls: navy outside, cream inside, a cream stone base outside, a thin gold cap at the cut (1.1 m)
    gw = NG("SPA_wallNavy", E["wallN"]); gwi = NG("SPA_wallCream", E["wallC"])
    gtw = NG("SPA_topWallNavy", E["wallN"]); gtwi = NG("SPA_topWallCream", E["wallC"])
    gb = NG("SPA_baseStone", E["stone"], bevel=.006)
    gcap = NG("SPA_capStone", E["stone"], bevel=.004)                   # cream coping with a thin gold bead outside
    gbead = NG("SPA_capBead", E["gold"], bevel=.002)
    win = (-2.8, .6, .55)                              # shop window x range and sill height (front wall)
    def seg(x0, x1, y0, y1, z0, z1, top=False):
        """A wall block: its outer skin navy, inner skin cream (two boxes)."""
        gO, gI = (gtw, gtwi) if top else (gw, gwi)
        if abs(x1 - x0) > abs(y1 - y0):            # runs along x
            ym = (y0 + y1) / 2; inner_up = ym < (fy0 + fy1) / 2
            yo, yi = (y0 + .02, y1 - .02) if inner_up else (y1 - .02, y0 + .02)
            t_ = abs(y1 - y0)
            gO.box((x1 - x0, t_ * .55, z1 - z0), ((x0 + x1) / 2, (ym - t_ * .225) if inner_up else (ym + t_ * .225), (z0 + z1) / 2))
            gI.box((x1 - x0 - (0 if top else 0), t_ * .45, z1 - z0), ((x0 + x1) / 2, (ym + t_ * .275) if inner_up else (ym - t_ * .275), (z0 + z1) / 2))
        else:
            xm = (x0 + x1) / 2; inner_right = xm < 0
            t_ = abs(x1 - x0)
            gO.box((t_ * .55, y1 - y0, z1 - z0), ((xm - t_ * .225) if inner_right else (xm + t_ * .225), (y0 + y1) / 2, (z0 + z1) / 2))
            gI.box((t_ * .45, y1 - y0, z1 - z0), ((xm + t_ * .275) if inner_right else (xm - t_ * .275), (y0 + y1) / 2, (z0 + z1) / 2))
    # back wall and sides (full length; the corners are owned by the side walls)
    for (z0, z1, top) in ((FL, LOW, False), (LOW + .04, TOP, True)):
        seg(ox0 + T, ox1 - T, fy1, oy1, z0, z1, top)
        seg(ox0, fx0, oy0, oy1, z0, z1, top); seg(fx1, ox1, oy0, oy1, z0, z1, top)
        # front: left of the window, under the window (low only), between window and door, right of the door
        seg(fx0, win[0], oy0, fy0, z0, z1, top)
        seg(win[1], d0 - .06, oy0, fy0, z0, z1, top)
        seg(d1 + .06, fx1, oy0, fy0, z0, z1, top)
    seg(win[0], win[1], oy0, fy0, FL, win[2], False)
    gtw.box((d1 - d0 + .02, T * .55, TOP - 2.2), ((d0 + d1) / 2, oy0 + T * .275, (2.2 + TOP) / 2))   # over the door
    gtwi.box((d1 - d0 + .02, T * .45, TOP - 2.2), ((d0 + d1) / 2, fy0 - T * .225, (2.2 + TOP) / 2))
    gtw.box((win[1] - win[0] + .02, T * .55, TOP - 2.3), ((win[0] + win[1]) / 2, oy0 + T * .275, (2.3 + TOP) / 2))
    gtwi.box((win[1] - win[0] + .02, T * .45, TOP - 2.3), ((win[0] + win[1]) / 2, fy0 - T * .225, (2.3 + TOP) / 2))
    # stone base outside (front and right side, the sides the camera sees) and the gold cap at the cut
    for (x0, x1) in ((ox0, d0 - .075), (d1 + .075, ox1)):
        gb.box((x1 - x0, .03, .32), ((x0 + x1) / 2, oy0 - .0155, FL + .16))
    for sxx in (-1, 1): gb.box((.03, oy1 - oy0 + .062, .32), (sxx * (ox1 + .0155), (oy0 + oy1) / 2, FL + .16))
    gb.box((ox1 - ox0, .03, .32), (0, oy1 + .0155, FL + .16))
    capz = LOW + .008
    for (x0, x1) in ((ox0 + T, win[0]), (win[1], d0 - .06), (d1 + .06, ox1 - T)): gcap.box((x1 - x0, T + .02, .016), ((x0 + x1) / 2, (oy0 + fy0) / 2, capz))
    for sxx in (-1, 1): gcap.box((T + .02, oy1 - oy0 + .02, .016), (sxx * (fx1 + T / 2), (oy0 + oy1) / 2, capz))
    gcap.box((ox1 - ox0 - 2 * T, T + .02, .016), (0, (fy1 + oy1) / 2, capz))
    bz = capz + .008 + .009                                                     # the bead sits on the coping's outer edge
    for (x0, x1) in ((ox0 + T, win[0]), (win[1], d0 - .06), (d1 + .06, ox1 - T)): gbead.box((x1 - x0, .018, .018), ((x0 + x1) / 2, oy0 + .0, bz))
    for sxx in (-1, 1): gbead.box((.018, oy1 - oy0 + .02, .018), (sxx * (ox1 + .0), (oy0 + oy1) / 2, bz))
    gbead.box((ox1 - ox0 - 2 * T, .018, .018), (0, oy1, bz))
    # ---- shop window (navy frame, gold sill), the glass in EraGlass (visible below 1.1 m, CUT above)
    gfr = NG("SPA_frameNavy", E["navyF"], bevel=.006); gtf = NG("SPA_topFrame", E["navyF"], bevel=.006)
    gsill = NG("SPA_capSill", E["stone"], bevel=.004)
    wy = (oy0 + fy0) / 2
    gsill.box((win[1] - win[0] - .006, T + .04, .03), ((win[0] + win[1]) / 2, wy - .04, win[2] + .03))
    for x in (win[0] + .03, win[1] - .03, (win[0] + win[1]) / 2):
        gfr.box((.05, .07, LOW - win[2] - .06), (x, wy, (win[2] + .045 + LOW) / 2))
        gtf.box((.05, .07, 2.3 - LOW), (x, wy, (LOW + 2.3) / 2))
    gtf.box((win[1] - win[0], .07, .06), ((win[0] + win[1]) / 2, wy, 2.27))
    gtf.box((win[1] - win[0], .05, .04), ((win[0] + win[1]) / 2, wy, 1.75))
    gwg = G("SPA_glassWin", m_eraglass(), gcl); todo.append(gwg)
    gwg.box((win[1] - win[0] - .06, .012, LOW - win[2] - .05), ((win[0] + win[1]) / 2, wy, (win[2] + .045 + LOW) / 2))
    gtg = G("SPA_topGlass", m_eraglass(), gcl); todo.append(gtg)
    gtg.box((win[1] - win[0] - .06, .012, 2.24 - LOW), ((win[0] + win[1]) / 2, wy, (LOW + 2.24) / 2))
    # ---- door: navy frame posts (lower part visible), the glass leaf swung open inside against the right jamb
    for x in (d0 - .03, d1 + .03):
        gfr.box((.06, T + .04, LOW - FL), (x, wy, (FL + LOW) / 2)); gtf.box((.06, T + .04, 2.2 - LOW), (x, wy, (LOW + 2.2) / 2))
    gtf.box((d1 - d0 + .1, T + .04, .08), ((d0 + d1) / 2, wy, 2.2))
    # the leaf is swung all the way open, flat against the inside of the front wall right of the door (out of the
    # customers' way: the pay point and the queue are at y -.35)
    gdl = NG("SPA_doorLeaf", E["navyF"], bevel=.006); gdh = NG("SPA_doorHandle", E["gold"], bevel=.003)
    ly = fy0 + .045; lx0, lx1 = d1 + .02, d1 + .02 + (d1 - d0) - .04
    for x in (lx0 + .025, lx1 - .025): gdl.box((.05, .045, LOW - FL - .02), (x, ly, (FL + .02 + LOW) / 2))
    gdl.box((lx1 - lx0, .045, .1), ((lx0 + lx1) / 2, ly, FL + .07))
    gdh.box((.02, .02, .3), (lx1 - .08, ly + .035, .95))
    gdg = G("SPA_glassDoor", m_eraglass(), gcl); todo.append(gdg)
    gdg.box((lx1 - lx0 - .1, .012, LOW - FL - .16), ((lx0 + lx1) / 2, ly, (FL + .12 + LOW) / 2))
    gtd = NG("SPA_topDoorLeaf", E["navyF"], bevel=.006)
    for x in (lx0 + .025, lx1 - .025): gtd.box((.05, .045, 2.12 - LOW - .04), (x, ly, (LOW + .04 + 2.12) / 2))
    gtd.box((lx1 - lx0, .045, .06), ((lx0 + lx1) / 2, ly, 2.1))
    gmat = NG("SPA_mat", E["mat"], bevel=.006)
    gmat.box((d1 - d0 - .1, .5, .014), ((d0 + d1) / 2, oy0 - .3, .007))
    # ---- counter: wood top, navy front panels with a gold kick strip; retro register; navy stool behind
    cx0, cy0, cx1, cy1 = 1.36, .06, fx1 - .01, .8
    gcb = NG("SPA_counterBody", E["navyF"], bevel=.006, seg=1); gct = NG("SPA_counterTop", E["wood"], bevel=.008)
    gck = NG("SPA_counterKick", E["gold"], bevel=.003)
    gcb.box((cx1 - cx0, cy1 - cy0 - .02, .9), ((cx0 + cx1) / 2, (cy0 + .02 + cy1) / 2, FL + .45))
    for k in range(4):
        x0 = cx0 + .06 + k * (cx1 - cx0 - .12) / 4
        gcb.box(((cx1 - cx0 - .12) / 4 - .04, .02, .6), (x0 + (cx1 - cx0 - .12) / 8, cy0 + .009, FL + .45))
    gck.box((cx1 - cx0, .02, .05), ((cx0 + cx1) / 2, cy0 + .009, FL + .07))
    gct.box((cx1 - cx0 + .03, cy1 - cy0 + .06, .05), ((cx0 - .03 + cx1) / 2, (cy0 + cy1) / 2 - .02, FL + .925))
    rb = NG("SPA_regBody", E["regBody"], bevel=.008); rk = NG("SPA_regKey", E["regKey"], bevel=.004, seg=1)
    rd = NG("SPA_regDark", E["dark"], bevel=.004); rc = NG("SPA_regCoin", E["coin"]); rn = NG("SPA_regNote", E["note"])
    retro_register(rb, rk, rd, rc, rn, _T(2.45, .42, FL + .951, math.pi + .1))
    gsl = NG("SPA_stool", E["navyF"])
    gsl.cyl(.16, .04, (2.4, 1.12, FL + .7), verts=20)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        gsl.tube((2.4 + .14 * math.cos(a), 1.12 + .14 * math.sin(a), FL + .002), (2.4 + .1 * math.cos(a), 1.12 + .1 * math.sin(a), FL + .68), .016, verts=6)
    # ---- produce stand outside under the window (front left, reaching y -2.12 like the old table)
    gst = NG("SPA_stand", E["wood"], bevel=.005, seg=1)
    sx0, sx1, sy0, sy1, sz = -2.8, -1.0, -2.12, -1.52, .62
    tilt = math.atan2(.12, sy1 - sy0); bt = .03
    ym = (sy0 + sy1) / 2; zb = sz + .06                                         # board centre
    ztop = lambda y: zb + bt / 2 / math.cos(tilt) + (y - ym) * math.tan(tilt)  # board top along y
    gst.box((sx1 - sx0, (sy1 - sy0) / math.cos(tilt), bt), ((sx0 + sx1) / 2, ym, zb), rot=(tilt, 0, 0))
    for x in (sx0 + .04, sx1 - .04):
        for y in (sy0 + .05, sy1 - .05):
            h = ztop(y) - bt / math.cos(tilt) - .002; gst.box((.05, .05, h), (x, y, h / 2))
    gst.box((sx1 - sx0 - .14, .03, .03), ((sx0 + sx1) / 2, sy0 + .05, .15)); gst.box((sx1 - sx0 - .14, .03, .03), ((sx0 + sx1) / 2, sy1 - .05, .15))
    crates = NG("SPA_crate", E["crateN"], bevel=.005, seg=1); gwd = NG("SPA_wedge", E["wood"], bevel=.003, seg=1)
    gtc = NG("SPA_tagCard", E["chalk"]); PG = pg_factory(NG, "SPA_fruit")
    cw, cd, ch = .54, .5, .17
    for k, (x, kind, n, lod) in enumerate(((-2.5, "apple", 24, 0), (-1.9, "orange", 22, 0), (-1.3, "lime", 30, 0))):
        yb = sy0 + .04
        M0 = _T(x, yb, ztop(yb) + .002) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Translation((0, cd / 2, 0))
        crate_rect(crates, M0, cw, cd, ch)
        gwd.box((cw - .09, cd - .046, .012), (0, 0, .044), M=M0)
        heap(PG, M0, cw - .044, cd - .044, .05, kind, 90 + k, n, lod=lod)
        tag(gtc, None, M0 @ Matrix.Translation((cw / 2 - .085, -cd / 2, ch)))
    # ---- potted bushes beside the door (the city tree's crown), navy pots
    gpot = NG("SPA_bushPot", E["pot"], bevel=.01, seg=1); gsoil = NG("SPA_bushSoil", V.M["dirt"])
    for k, (px, py) in enumerate(((d0 - .3, oy0 - .32), (d1 + .55, oy0 - .32))):
        gpot.cyl(.16, .34, (px, py, .17), r2=.2, verts=20); gpot.torus(.2, .015, (px, py, .34), seg=20, rseg=5)
        gsoil.cyl(.185, .02, (px, py, .325), verts=20)
        V.city_tree("SPA_bush" + str(k), c, (px, py, .3), 1, rot_z=k * 2.4, tris=1200, crown_only=True, width=.5)
    # ---- CUT_: flat roof with a parapet and gold coping, awning over the window, the sign over the door
    gro = NG("SPA_topRoof", E["creamF"], bevel=.01)
    gro.box((ox1 - ox0, oy1 - oy0, .12), (0, (oy0 + oy1) / 2, TOP + .06))
    gco = NG("SPA_topCoping", E["gold"], bevel=.004)
    gco.box((ox1 - ox0 + .04, .06, .05), (0, oy0 - .01, TOP + .145)); gco.box((ox1 - ox0 + .04, .06, .05), (0, oy1 + .01, TOP + .145))
    for sxx in (-1, 1): gco.box((.06, oy1 - oy0 + .04, .05), (sxx * (ox1 + .01), (oy0 + oy1) / 2, TOP + .145))
    gA = NG("SPA_awnNavy", E["navy"]); gB = NG("SPA_awnCream", E["creamB"]); gT = NG("SPA_awnTrim", E["gold"])
    slope_awning((gA, gB), gT, win[0] - .05, win[1] + .05, oy0 - .02, 2.48, oy0 - .72, 2.12, n=8, sag=0., hem=True)
    for x in (win[0] + .05, win[1] - .05): gT.tube((x, oy0 - .025, 2.05), (x, oy0 - .66, 2.1), .012, verts=6)
    gsg = NG("SPA_signBoard", E["navyF"], bevel=.006); gsf = NG("SPA_signFrame", E["gold"], bevel=.005)
    sx0_, sx1_, sz0_, sz1_ = d0 + .02, d1 + .95, 2.32, 2.66
    gsg.box((sx1_ - sx0_, .05, sz1_ - sz0_), ((sx0_ + sx1_) / 2, oy0 - .04, (sz0_ + sz1_) / 2))
    for z in (sz0_, sz1_): gsf.box((sx1_ - sx0_ + .05, .06, .035), ((sx0_ + sx1_) / 2, oy0 - .045, z))
    for x in (sx0_, sx1_): gsf.box((.035, .06, sz1_ - sz0_), (x, oy0 - .045, (sz0_ + sz1_) / 2))
    pm = picto_mats(); gp = {k: NG("SPA_sign" + k.capitalize(), pm[k]) for k in pm}
    for k, kind in enumerate(("apple", "milk", "cheese")):
        pict(gp, Matrix.Translation((sx0_ + (k + .5) * (sx1_ - sx0_) / 3, oy0 - .066, (sz0_ + sz1_) / 2)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), kind, 1.2)
    for gg in todo:
        if len(gg.bm.verts): gg.done()
        else: gg.bm.free()
    for o in c.all_objects:
        if o.type == 'MESH' and any(k in o.name for k in ("fruit", "reg", "Pot")):
            for p in o.data.polygons: p.use_smooth = True
    return V.stats(c)


def shop_markers(cname, plan, old=None, tag="MK"):
    """Top-view markers for a walk-in shop (CheckoutStall.Plans): white = inner floor, cyan = door gap, magenta =
    counter rect, red = pay point, blue = queue spots, yellow = the model's bounds (and the old model's in orange)."""
    mc = col("Markers")
    for o in list(mc.objects): bpy.data.objects.remove(o)
    lo, hi = bounds(game_objs(cname)); top = hi.z + .3
    x0, y0, x1, y1 = plan["floor"]
    g = G(tag + "_floor", _emit("MK_White", (1, 1, 1, 1)), mc, smooth=False); _outline(g, x0, y0, x1, y1, top, .03); g.done()
    g = G(tag + "_door", _emit("MK_Cyan", (0, .9, 1, 1)), mc, smooth=False)
    d0, d1 = plan["door"]; g.box((d1 - d0, .08, .03), ((d0 + d1) / 2, y0, top + .01)); g.done()
    if plan.get("counter"):
        cx0, cy0, cx1, cy1 = plan["counter"]
        g = G(tag + "_counter", _emit("MK_Magenta", (1, .1, 1, 1)), mc, smooth=False); _outline(g, cx0, cy0, cx1, cy1, top + .02, .025); g.done()
    g = G(tag + "_pay", _emit("MK_Red", (1, .05, .1, 1)), mc, smooth=False)
    px, py = plan["pay"]; g.cyl(.1, .03, (px, py, top + .03), verts=20); g.done()
    g = G(tag + "_queue", _emit("MK_Blue", (.1, .35, 1, 1)), mc, smooth=False)
    qx, qy = plan["queue"]
    for k in range(1, 4): g.cyl(.07, .03, (px + qx * k, py + qy * k, top + .03), verts=12)
    g.done()
    g = G(tag + "_bounds", _emit("MK_Yellow", (1, .9, 0, 1)), mc, smooth=False); _outline(g, lo.x, lo.y, hi.x, hi.y, .02, .02); g.done()
    if old:
        olo, ohi = bounds(game_objs(old))
        g = G(tag + "_oldbounds", _emit("MK_Orange", (1, .45, 0, 1)), mc, smooth=False); _outline(g, olo.x, olo.y, ohi.x, ohi.y, .03, .015); g.done()


def shop_check(cname, plan):
    """The plan against the geometry the game shows: inner wall faces (rays from the floor centre at 0.5 m), the
    door gap (rays along the front wall line), the floor top, what stands on the pay point / queue spots, and the
    counter's footprint against its rect."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    objs = game_objs(cname)
    vs, ts = [], []
    for o in objs:
        m = o.evaluated_get(dg).to_mesh(); m.calc_loop_triangles(); b = len(vs)
        vs += [o.matrix_world @ v.co for v in m.vertices]; ts += [tuple(b + i for i in t.vertices) for t in m.loop_triangles]
        o.evaluated_get(dg).to_mesh_clear()
    bvh = BVHTree.FromPolygons(vs, ts, all_triangles=True)
    x0, y0, x1, y1 = plan["floor"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    out = {}
    def ray(o, d):
        h = bvh.ray_cast(Vector(o), Vector(d)); return None if h[0] is None else round(h[3], 3)
    yr = y1 - .2                                    # (behind the counter and the open door leaf)
    out["wall -x"] = round(cx - (ray((cx, yr, .5), (-1, 0, 0)) or float('nan')), 3)
    out["wall +x"] = round(cx + (ray((cx, yr, .5), (1, 0, 0)) or float('nan')), 3)
    # an x clear of the door gap and of the counter, for the front / back / floor rays
    d0_, d1_ = plan["door"]; cr = plan.get("counter") or (99, 99, 99, 99)
    xs = [x0 + .3 + .1 * i for i in range(int((x1 - x0 - .6) / .1))]
    xf = next(x for x in xs if not (d0_ - .2 < x < d1_ + .2) and not (cr[0] - .2 < x < cr[2] + .2))
    r_ = lambda o, d: ray(o, d) if ray(o, d) is not None else float('nan')
    out["ray x"] = round(xf, 2)
    out["wall back"] = round(cy + r_((xf, cy, .5), (0, 1, 0)), 3)
    out["wall front"] = round(cy - r_((xf, cy, .5), (0, -1, 0)), 3)
    out["floor top"] = round(.5 - r_((xf, cy, .5), (0, 0, -1)), 3)
    # door gap: march along x on the front wall's centre line at 0.5 m
    fy = y0 - .09; free = []
    for i in range(int((x1 - x0) / .01) + 1):
        x = x0 + i * .01
        h = ray((x, fy, 1.4), (0, 0, -1))
        if h is None or 1.4 - h < .1: free.append(round(x, 2))
    out["door gap"] = (free[0], free[-1]) if free else None
    out["door gap runs"] = len([1 for a, b in zip(free, free[1:]) if b - a > .015]) + (1 if free else 0)
    pts = {"pay": plan["pay"]}
    qx, qy = plan["queue"]
    for k in range(1, 4): pts["queue%d" % k] = (plan["pay"][0] + qx * k, plan["pay"][1] + qy * k)
    for k, (x, y) in pts.items():
        h = ray((x, y, 2.0), (0, 0, -1)); out[k] = round(2.0 - h, 3) if h is not None else None     # height of what is there
    return out


# ================================================================== ERA 5 - QUITANDA (greengrocer): a bigger walk-in shop
# CheckoutStall.Plans["Era5_Quitanda"] (model metres): inner floor x -4.1..4.1, y -2.4..2.6; door (a wide open shop
# front, the shutter rolled up) x -3.45..0.55 in the front wall; counter rect x 1.35..3.15, y -1.7..-.3 (behind the
# shop window); pay point (2.25, -2.0), queue towards -x; floor top .06. Bounds as the old model: x +-4.29,
# y -3.25..2.79 (a paved apron in front, the produce rack under the window outside). Walls below 1.28 m show in the
# game (as the old model), everything above is CUT_*.
QUI = "E2 Quitanda"
QUI_PLAN = {"floor": (-4.1, -2.4, 4.1, 2.6), "door": (-3.45, .55), "counter": (1.35, -1.7, 3.15, -.3), "pay": (2.25, -2.0),
            "queue": (-.75, 0.), "floorY": .06}
QUI_GROUPS = [
    ("ERA5_Shell", ("QUI_wall", "QUI_base", "QUI_cap", "QUI_floor", "QUI_frame", "QUI_apron", "QUI_bush", "QUI_pier")),
    ("CUT_ERA5_ShellTop", ("QUI_top",)),
    ("CUT_ERA5_Awning", ("QUI_awn",)),
    ("CUT_ERA5_Sign", ("QUI_sign",)),
    ("ERA5_Counter", ("QUI_counter",)),
    ("ERA5_Counter_Register", ("QUI_reg",)),
    ("ERA5_Counter_Stool", ("QUI_stool",)),
    ("ERA5_Produce", ("QUI_rack", "QUI_crate", "QUI_fruit", "QUI_wedge", "QUI_tag", "QUI_banana")),
]
QUI_GLASS = {"QUI_glassWin": "ERA5_Glass_win", "QUI_topGlass": "CUT_ERA5_Glass_winTop"}
CUT_SRC = CUT_SRC + ("QUI_top", "QUI_awn", "QUI_sign")


def build_quitanda():
    mats_v2()
    E = EM
    E["wallN"] = V.m_flat("E2N_SpatiWallNavy", NAVY, .03, 1.2, .8, ao=.35)
    E["wallC"] = V.m_flat("E2N_SpatiWallCream", CREAM, .02, 1.2, .8, ao=.35)
    E["stone"] = V.m_flat("E2N_SpatiBase", C("ECE1CA"), .04, 2, .85, island=.03, ao=.35)
    E["tile"] = V.m_flat("E2N_FloorTile", C("F1E8D5"), .03, 3, .7, island=.05, ao=.35)
    E["tileN"] = V.m_flat("E2N_FloorTileNavy", NAVY2, .03, 3, .7, island=.05, ao=.35)
    E["apron"] = V.m_flat("E2N_ApronPaver", C("E2D7BF"), .05, 3, .9, island=.06, ao=.4)
    E["shutter"] = V.m_metal_paint("E2N_Shutter", C("2B3E66"), amount=0., ribs=('Z', .08))
    c = col(QUI)
    for o in list(c.all_objects): bpy.data.objects.remove(o)
    lc = bpy.context.view_layer.layer_collection.children.get(QUI)
    if lc: lc.exclude = False
    gcl = glass_col(QUI)
    todo = []

    def NG(name, mat, **kw):
        g = G(name, mat, c, **kw); todo.append(g); return g
    fx0, fy0, fx1, fy1 = QUI_PLAN["floor"]; d0, d1 = QUI_PLAN["door"]
    T = .19
    ox0, ox1, oy0, oy1 = fx0 - T, fx1 + T, fy0 - T, fy1 + T          # x +-4.29, y -2.59..2.79
    LOW, TOP = 1.28, 3.1
    FL = QUI_PLAN["floorY"]
    win = (.81, 3.49, .9)
    # ---- floor: slab, tiles (cream with a navy checker band all round), apron pavers in front
    gfs = NG("QUI_floorSlab", E["stone"], bevel=.01)
    gfs.box((ox1 - ox0, oy1 - oy0, FL - .002), (0, (oy0 + oy1) / 2, (FL - .002) / 2))
    gft = NG("QUI_floorTile", E["tile"]); gfn = NG("QUI_floorTileNavy", E["tileN"])
    nx, ny = 20, 12; sx, sy = (fx1 - fx0) / nx, (fy1 - fy0) / ny
    for i in range(nx):
        for j in range(ny):
            band = i in (0, nx - 1) or j in (0, ny - 1)
            g = gfn if band and (i + j) % 2 == 0 else gft                          # navy / cream checker band
            g.box((sx - .008, sy - .008, .004), (fx0 + (i + .5) * sx, fy0 + (j + .5) * sy, FL - .002))
    gfs.box((d1 - d0, T, .004), ((d0 + d1) / 2, fy0 - T / 2, FL - .002))                       # threshold
    gap = NG("QUI_apronPaver", E["apron"])
    ay0, ay1 = -3.25, oy0 - .005
    n = int((ox1 - ox0) / .5)
    for i in range(n):
        for j in range(2):
            gap.box(((ox1 - ox0) / n - .01, (ay1 - ay0) / 2 - .01, .02), (ox0 + (i + .5) * (ox1 - ox0) / n, ay0 + (j + .5) * (ay1 - ay0) / 2, .01))
    # ---- walls: navy outside, cream inside (lower part shown, upper CUT), cream piers framing the open front
    gw = NG("QUI_wallNavy", E["wallN"]); gwi = NG("QUI_wallCream", E["wallC"])
    gtw = NG("QUI_topWallNavy", E["wallN"]); gtwi = NG("QUI_topWallCream", E["wallC"])
    def run(axis, a0, a1, outer, inner, z0, z1, top=False):
        gO, gI = (gtw, gtwi) if top else (gw, gwi)
        t_ = abs(outer - inner); mid = (outer + inner) / 2
        if axis == 'x':          # along x, the outer face at y = outer
            gO.box((a1 - a0, t_ * .55, z1 - z0), ((a0 + a1) / 2, outer + (inner - outer) * .275, (z0 + z1) / 2))
            gI.box((a1 - a0, t_ * .45, z1 - z0), ((a0 + a1) / 2, inner - (inner - outer) * .225, (z0 + z1) / 2))
        else:
            gO.box((t_ * .55, a1 - a0, z1 - z0), (outer + (inner - outer) * .275, (a0 + a1) / 2, (z0 + z1) / 2))
            gI.box((t_ * .45, a1 - a0, z1 - z0), (inner - (inner - outer) * .225, (a0 + a1) / 2, (z0 + z1) / 2))
    for (z0, z1, top) in ((FL, LOW, False), (LOW + .04, TOP, True)):
        run('x', ox0 + T, ox1 - T, oy1, fy1, z0, z1, top)                                         # back
        run('y', oy0, oy1, ox0, fx0, z0, z1, top); run('y', oy0, oy1, ox1, fx1, z0, z1, top)        # sides
        run('x', d1 + .06, win[0], oy0, fy0, z0, z1, top); run('x', win[1], fx1, oy0, fy0, z0, z1, top)
        run('x', fx0, d0 - .06, oy0, fy0, z0, z1, top)
    run('x', win[0], win[1], oy0, fy0, FL, win[2], False)
    run('x', d0 - .06, d1 + .06, oy0, fy0, 2.45, TOP, True)                                       # over the open front
    run('x', win[0], win[1], oy0, fy0, 2.3, TOP, True)                                           # over the window
    # cream piers at the corners and both sides of the open front (pilasters), split at the cut
    gpi = NG("QUI_pierStone", E["stone"], bevel=.01); gpt = NG("QUI_topPier", E["stone"], bevel=.01)
    piers = [(ox0 + .12, .3), (d0 - .06 - .12, .3), ((d1 + win[0]) / 2 - .03, .2), (ox1 - .12, .3)]      # (x, width) on the front
    pz0 = .022                                                                     # standing on the apron pavers
    for x, w in piers:
        gpi.box((w, .07, LOW - .02 - pz0), (x, oy0 - .037, (pz0 + LOW - .02) / 2)); gpt.box((w, .07, TOP - LOW - .06), (x, oy0 - .037, (LOW + .04 + TOP) / 2))
        gpi.box((w + .04, .11, .03), (x, oy0 - .057, LOW - .005))                    # pier cap
    for sxx in (-1, 1):
        for y in (oy0 + .12, oy1 - .12):
            gpi.box((.07, .3, LOW - .02), (sxx * (ox1 + .037), y, (LOW - .02) / 2)); gpt.box((.07, .3, TOP - LOW - .06), (sxx * (ox1 + .037), y, (LOW + .04 + TOP) / 2))
            gpi.box((.11, .34, .03), (sxx * (ox1 + .057), y, LOW - .005))
    # stone base and a cream coping with a thin gold bead at the cut
    gb = NG("QUI_baseStone", E["stone"], bevel=.006)
    for (x0, x1) in ((ox0 + .275, d0 - .06 - .275), ((d1 + win[0]) / 2 + .075, ox1 - .275)): gb.box((x1 - x0, .03, .3), ((x0 + x1) / 2, oy0 - .0155, .022 + .15))
    for sxx in (-1, 1): gb.box((.03, oy1 - oy0 - .55, .32), (sxx * (ox1 + .0155), (oy0 + oy1) / 2, FL + .16))
    gcap = NG("QUI_capStone", E["stone"], bevel=.004); gbead = NG("QUI_capBead", E["gold"], bevel=.002)
    capz = LOW + .01
    segs = [((ox0 + .275, d0 - .335), 'f'), ((win[1], ox1 - .275), 'f')]
    for (x0, x1), _ in segs:
        gcap.box((x1 - x0, T, .016), ((x0 + x1) / 2, (oy0 + fy0) / 2, capz)); gbead.box((x1 - x0, .018, .018), ((x0 + x1) / 2, oy0 - .009, capz + .017))
    for sxx in (-1, 1):
        gcap.box((T, oy1 - oy0 - .55, .016), (sxx * (fx1 + T / 2), (oy0 + oy1) / 2, capz)); gbead.box((.018, oy1 - oy0 - .55, .018), (sxx * (ox1 + .009), (oy0 + oy1) / 2, capz + .017))
    gcap.box((ox1 - ox0 - .55, T, .016), (0, (fy1 + oy1) / 2, capz)); gbead.box((ox1 - ox0 - .55, .018, .018), (0, oy1 + .009, capz + .017))
    # ---- shop window over the counter (navy frame, cream sill), glass EraGlass
    gfr = NG("QUI_frameNavy", E["navyF"], bevel=.006); gtf = NG("QUI_topFrame", E["navyF"], bevel=.006)
    gsill = NG("QUI_frameSill", E["stone"], bevel=.004)
    wy = (oy0 + fy0) / 2
    gsill.box((win[1] - win[0] - .006, T + .04, .03), ((win[0] + win[1]) / 2, wy - .04, win[2] + .015))
    for x in (win[0] + .03, win[1] - .03, (win[0] + win[1]) / 2):
        gfr.box((.05, .07, LOW - win[2] - .03), (x, wy, (win[2] + .03 + LOW) / 2))
        gtf.box((.05, .07, 2.3 - LOW - .04), (x, wy, (LOW + .04 + 2.3) / 2))
    gtf.box((win[1] - win[0], .07, .06), ((win[0] + win[1]) / 2, wy, 2.27))
    gwg = G("QUI_glassWin", m_eraglass(), gcl); todo.append(gwg)
    gwg.box((win[1] - win[0] - .06, .012, LOW - win[2] - .04), ((win[0] + win[1]) / 2, wy, (win[2] + .03 + LOW) / 2))
    gtg = G("QUI_topGlass", m_eraglass(), gcl); todo.append(gtg)
    gtg.box((win[1] - win[0] - .06, .012, 2.24 - LOW - .04), ((win[0] + win[1]) / 2, wy, (LOW + .04 + 2.24) / 2))
    # ---- the open front: a rolled-up navy shutter in its box and the guide rails (above the cut)
    gsh = NG("QUI_topShutter", E["shutter"], bevel=.01)
    gsh.box((d1 - d0 + .2, .32, .32), ((d0 + d1) / 2, oy0 - .1, 2.6))
    # ---- counter behind the window: wood top, navy front with a gold kick strip; register; stool
    cx0, cy0, cx1, cy1 = 1.42, -1.62, 3.08, -.9
    gcb = NG("QUI_counterBody", E["navyF"], bevel=.006, seg=1); gct = NG("QUI_counterTop", E["wood"], bevel=.008)
    gck = NG("QUI_counterKick", E["gold"], bevel=.003)
    gcb.box((cx1 - cx0, cy1 - cy0 - .02, .9), ((cx0 + cx1) / 2, (cy0 + .02 + cy1) / 2, FL + .45))
    for k in range(4):
        x0 = cx0 + .06 + k * (cx1 - cx0 - .12) / 4
        gcb.box(((cx1 - cx0 - .12) / 4 - .04, .02, .6), (x0 + (cx1 - cx0 - .12) / 8, cy0 + .009, FL + .45))
    gck.box((cx1 - cx0, .02, .05), ((cx0 + cx1) / 2, cy0 + .009, FL + .07))
    gct.box((cx1 - cx0 + .04, cy1 - cy0 + .06, .05), ((cx0 + cx1) / 2, (cy0 + cy1) / 2 - .02, FL + .925))
    rb = NG("QUI_regBody", E["regBody"], bevel=.008); rk = NG("QUI_regKey", E["regKey"], bevel=.004, seg=1)
    rd = NG("QUI_regDark", E["dark"], bevel=.004); rc = NG("QUI_regCoin", E["coin"]); rn = NG("QUI_regNote", E["note"])
    retro_register(rb, rk, rd, rc, rn, _T(2.6, -1.22, FL + .951, math.pi + .1))
    gsl = NG("QUI_stool", E["navyF"])
    gsl.cyl(.16, .04, (2.7, -.52, FL + .7), verts=20)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        gsl.tube((2.7 + .14 * math.cos(a), -.52 + .14 * math.sin(a), FL + .002), (2.7 + .1 * math.cos(a), -.52 + .1 * math.sin(a), FL + .68), .016, verts=6)
    # ---- outside under the window: a stepped wooden rack of vegetable crates on the apron (natural colours)
    grk = NG("QUI_rack", E["wood"], bevel=.005, seg=1)
    rx0, rx1, ry0, ry1 = .78, 3.52, -3.22, -2.66
    tilt = math.radians(14); zb_ = .5
    ym = (ry0 + ry1) / 2; bt = .03
    ztop = lambda y: zb_ + bt / 2 / math.cos(tilt) + (y - ym) * math.tan(tilt)
    grk.box((rx1 - rx0, (ry1 - ry0) / math.cos(tilt), bt), ((rx0 + rx1) / 2, ym, zb_), rot=(tilt, 0, 0))
    for x in (rx0 + .04, (rx0 + rx1) / 2, rx1 - .04):
        for y in (ry0 + .05, ry1 - .05):
            h = ztop(y) - bt / math.cos(tilt) - .002; grk.box((.05, .05, h - .022), (x, y, .022 + (h - .022) / 2))
    for y in (ry0 + .05, ry1 - .05):
        for (xa, xb) in ((rx0 + .065, (rx0 + rx1) / 2 - .025), ((rx0 + rx1) / 2 + .025, rx1 - .065)): grk.box((xb - xa, .03, .03), ((xa + xb) / 2, y, .16))
    crates = NG("QUI_crate", E["crateN"], bevel=.005, seg=1); gwd = NG("QUI_wedge", E["wood"], bevel=.003, seg=1)
    gtc = NG("QUI_tagCard", E["chalk"]); PG = pg_factory(NG, "QUI_fruit")
    cw, cd, ch = .62, .5, .17
    for k, (kind, n, lod) in enumerate((("tomato", 26, 0), ("pepperR", 18, 0), ("onion", 22, 0), ("potato", 18, 0))):
        x = rx0 + .05 + cw / 2 + k * (cw + .045)
        yb = ry0 + .03
        M0 = _T(x, yb, ztop(yb) + .002) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Translation((0, cd / 2, 0))
        crate_rect(crates, M0, cw, cd, ch)
        gwd.box((cw - .09, cd - .046, .012), (0, 0, .044), M=M0)
        heap(PG, M0, cw - .044, cd - .044, .05, kind, 110 + k, n, lod=lod)
        tag(gtc, None, M0 @ Matrix.Translation((cw / 2 - .085, -cd / 2, ch)))
    # ---- potted bushes at the two outer corners of the front
    gpot = NG("QUI_bushPot", E["pot"], bevel=.01, seg=1); gsoil = NG("QUI_bushSoil", V.M["dirt"])
    for k, (px, py) in enumerate(((-4.0, -2.95), (.25, -2.95))):
        gpot.cyl(.16, .34, (px, py, .17 + .022), r2=.2, verts=20); gpot.torus(.2, .015, (px, py, .362), seg=20, rseg=5)
        gsoil.cyl(.185, .02, (px, py, .345), verts=20)
        V.city_tree("QUI_bush" + str(k), c, (px, py, .32), 1, rot_z=k * 2.4, tris=1200, crown_only=True, width=.5)
    # ---- CUT_: roof with gold coping, the awning over the window and rack, the sign over the open front
    gro = NG("QUI_topRoof", E["creamF"], bevel=.01)
    gro.box((ox1 - ox0, oy1 - oy0, .12), (0, (oy0 + oy1) / 2, TOP + .06))
    gco = NG("QUI_topCoping", E["gold"], bevel=.004)
    gco.box((ox1 - ox0 + .04, .06, .05), (0, oy0 - .01, TOP + .145)); gco.box((ox1 - ox0 + .04, .06, .05), (0, oy1 + .01, TOP + .145))
    for sxx in (-1, 1): gco.box((.06, oy1 - oy0 + .04, .05), (sxx * (ox1 + .01), (oy0 + oy1) / 2, TOP + .145))
    gA = NG("QUI_awnNavy", E["navy"]); gB = NG("QUI_awnCream", E["creamB"]); gT = NG("QUI_awnTrim", E["gold"])
    slope_awning((gA, gB), gT, win[0] - .01, win[1] + .12, oy0 - .02, 2.42, -3.25 + .02, 2.0, n=10, sag=0., hem=True)
    for x in (win[0] + .04, win[1] + .05): gT.tube((x, oy0 - .025, 1.95), (x, -3.15, 2.02), .012, verts=6)
    gsg = NG("QUI_signBoard", E["navyF"], bevel=.006); gsf = NG("QUI_signFrame", E["gold"], bevel=.005)
    sx0_, sx1_, sz0_, sz1_ = d0 + .4, d1 - .4, 2.86, 3.0
    gsg.box((sx1_ - sx0_, .05, sz1_ - sz0_ + .14), ((sx0_ + sx1_) / 2, oy0 - .04, (sz0_ + sz1_) / 2))
    for z in (sz0_ - .07, sz1_ + .07): gsf.box((sx1_ - sx0_ + .05, .06, .035), ((sx0_ + sx1_) / 2, oy0 - .045, z))
    for x in (sx0_, sx1_): gsf.box((.035, .06, sz1_ - sz0_ + .14), (x, oy0 - .045, (sz0_ + sz1_) / 2))
    pm = picto_mats(); gp = {k: NG("QUI_sign" + k.capitalize(), pm[k]) for k in pm}
    for k, kind in enumerate(("apple", "carrot", "cheese", "milk")):
        pict(gp, Matrix.Translation((sx0_ + (k + .5) * (sx1_ - sx0_) / 4, oy0 - .066, (sz0_ + sz1_) / 2)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), kind, 1.2)
    for gg in todo:
        if len(gg.bm.verts): gg.done()
        else: gg.bm.free()
    for o in c.all_objects:
        if o.type == 'MESH' and any(k in o.name for k in ("fruit", "reg", "Pot", "banana")):
            for p in o.data.polygons: p.use_smooth = True
    return V.stats(c)


ERAS["Era5_Quitanda"] = ("E2 Quitanda", "QUI_GROUPS", "ERA5_Shell", "QUI_GLASS")
