"""decor_v4: build-mode decoration pipeline (modelled with real Blender modifiers, one baked hand-painted atlas per asset).

Run headless, one or more items per process:
    blender -b --factory-startup --python dv4_run.py -- <id> [<id> ...]
Each item is ArtSource/decor_v4/items/<id>.py: it imports dv4, defines build() that creates parts with the helpers below
(cube, lathe, tube, leaf, sphere, torus, ...; every part carries its paint material and its output node) and returns a
config dict:  {"name": "PlantSmall", "tex": 512, "budget": 6000, "floor": "F4EFE4", "ao_dist": .25}

Contracts (CheckoutInteriorKitBuilder / CheckoutInteriorLife in Unity):
  * metres, Blender Z up, origin at the floor centre of the footprint, the customer side (front) faces Blender +Y.
    The FBX export (axis_forward -Z, axis_up Y) turns that into Unity -Z = front, like build_interior_kit.py.
  * materials by NAME: T_IK_D4_<Name> -> Assets/Art/Interior/Textures/IK_D4_<Name>_albedo.png (tiling 1).
    Optional extra slots: C_RRGGBB flat paint, E_RRGGBB glow, G_Glass. Parts get them through mat_override=.
  * static parts are merged into one object "Body"; moving parts are objects "Anim Sway" / "Anim Bob" / "Anim Spin" /
    "Anim Blink" / "Anim Scroll" (+ ".001" ...) whose origin is their pivot (out=..., pivot=...).
Outputs (all under ArtSource/decor_v4, nothing is written into Assets):
  fbx/<id>.fbx, tex/IK_D4_<Name>_albedo.png, thumbs/<id>.png (256, transparent, like build_interior_kit.thumbnail),
  previews/<id>_game.png, previews/<id>_close.png, previews/<id>_old_close.png, previews/<id>_old_game.png, report.json.
"""
import os, sys, math, json, time, random
import bpy, bmesh
from mathutils import Vector, Matrix, Euler

ROOT = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\decor_v4"
ASSETS = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets"
OLD_MODELS = os.path.join(ASSETS, "Art", "Interior", "Models")
ASSET_TEX = os.path.join(ASSETS, "Art", "Interior", "Textures")
D = {k: os.path.join(ROOT, k) for k in ("fbx", "tex", "thumbs", "previews", "items", "logs")}
for _d in D.values():
    os.makedirs(_d, exist_ok=True)

# Market palette (sRGB hex).
NAVY, GOLD, GOLDL, CREAM, WHITE = "1D2B4F", "E0B040", "FFD97A", "F4EFE4", "FBF8F1"
TEAL, TEALD, RED, ORANGE, PINK = "1F9A8E", "17655D", "D74A3C", "EC862E", "EE8FAE"
WOOD, WOODL, WOODD, STEEL, DARK = "AB6537", "D69C53", "6B4128", "C9D2D6", "2F3A40"
GREEN, LEAF, LEAFD, BLUE, TERRACOTTA = "5A9D33", "5DAE3E", "2F6F2C", "3E8FD6", "C4673D"

PARTS = []        # objects created by the helpers (bpy objects); each has ["dv4_out"]
PIVOTS = {}       # output object name -> pivot (Blender space)
RNG = random.Random(4)


def log(*a):
    print("[dv4]", *a, flush=True)


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c)


def rgba(h, a=1.0):
    if isinstance(h, str):
        return (*srgb(h), a)
    return tuple(h) if len(h) == 4 else (*h, a)


def rad(a):
    return math.radians(a)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    PARTS.clear(); PIVOTS.clear()
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"; sc.unit_settings.scale_length = 1
    return sc


# ================================================================================================= node helpers
def _mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt


def N(nt, kind, **kw):
    n = nt.nodes.new("ShaderNode" + kind)
    for k, v in kw.items():
        key = k.replace("_", " ") if k.replace("_", " ") in n.inputs else k
        if key in n.inputs and not hasattr(n, k):
            _plug(nt, n.inputs[key], v)
        else:
            setattr(n, k, v)
    return n


def _plug(nt, sock, v):
    if isinstance(v, bpy.types.NodeSocket):
        nt.links.new(v, sock)
    elif isinstance(v, str):
        sock.default_value = rgba(v)
    elif sock.type == "RGBA" and isinstance(v, (int, float)):
        sock.default_value = (v, v, v, 1)
    else:
        sock.default_value = v


def MATH(nt, op, a, b=0.0, c=0.0, clamp=False):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
    _plug(nt, n.inputs[0], a); _plug(nt, n.inputs[1], b); _plug(nt, n.inputs[2], c)
    return n.outputs[0]


def VMATH(nt, op, a, b=(0, 0, 0)):
    n = nt.nodes.new("ShaderNodeVectorMath"); n.operation = op
    _plug(nt, n.inputs[0], a); _plug(nt, n.inputs[1], b)
    return n.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs[0]


def MIX(nt, fac, a, b, blend="MIX"):
    n = nt.nodes.new("ShaderNodeMix"); n.data_type = "RGBA"; n.blend_type = blend
    _plug(nt, n.inputs[0], fac); _plug(nt, n.inputs[6], a); _plug(nt, n.inputs[7], b)
    return n.outputs[2]


def RAMP(nt, fac, stops, interp="LINEAR"):
    """stops: [(pos, hex|rgba)]"""
    n = nt.nodes.new("ShaderNodeValToRGB"); n.color_ramp.interpolation = interp
    el = n.color_ramp.elements
    while len(el) > 1:
        el.remove(el[-1])
    el[0].position = stops[0][0]; el[0].color = rgba(stops[0][1])
    for p, c in stops[1:]:
        e = el.new(p); e.color = rgba(c)
    _plug(nt, n.inputs[0], fac)
    return n.outputs[0]


def COORD(nt, scale=(1, 1, 1), rot=(0, 0, 0), loc=(0, 0, 0), kind="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.vector_type = "POINT"
    mp.inputs["Scale"].default_value = scale; mp.inputs["Rotation"].default_value = [rad(a) for a in rot]
    mp.inputs["Location"].default_value = loc
    nt.links.new(tc.outputs[kind], mp.inputs[0])
    return mp.outputs[0]


def NOISE(nt, vec, scale=5.0, detail=3.0, rough=.5, dist=0.0):
    n = nt.nodes.new("ShaderNodeTexNoise")
    _plug(nt, n.inputs["Vector"], vec); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = dist
    return n.outputs["Fac"]


def VORO(nt, vec, scale=8.0, feature="F1", out="Distance", rand=1.0):
    n = nt.nodes.new("ShaderNodeTexVoronoi"); n.feature = feature
    _plug(nt, n.inputs["Vector"], vec); n.inputs["Scale"].default_value = scale; n.inputs["Randomness"].default_value = rand
    return n.outputs[out]


def WAVE(nt, vec, scale=2.0, dist=4.0, detail=2.0, dscale=1.0, direction="X", kind="BANDS", profile="SIN"):
    n = nt.nodes.new("ShaderNodeTexWave"); n.wave_type = kind; n.wave_profile = profile
    if kind == "BANDS":
        n.bands_direction = direction
    _plug(nt, n.inputs["Vector"], vec); n.inputs["Scale"].default_value = scale; n.inputs["Distortion"].default_value = dist
    n.inputs["Detail"].default_value = detail; n.inputs["Detail Scale"].default_value = dscale
    return n.outputs["Fac"]


def ATTR(nt, name="Paint"):
    """Per-vertex paint attribute (R = along, G = across, B = per-part random)."""
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = name
    sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(vc.outputs["Color"], sp.inputs[0])
    return sp.outputs["Red"], sp.outputs["Green"], sp.outputs["Blue"]


def SMOOTH(nt, x, lo, hi):
    n = nt.nodes.new("ShaderNodeMapRange"); n.interpolation_type = "SMOOTHSTEP"; n.clamp = True
    _plug(nt, n.inputs["Value"], x); n.inputs["From Min"].default_value = lo; n.inputs["From Max"].default_value = hi
    return n.outputs[0]


class Ctx:
    """Everything a paint recipe may want: node tree, geometry, AO."""
    def __init__(self, nt, ao_dist):
        self.nt = nt
        self.geo = nt.nodes.new("ShaderNodeNewGeometry")
        self.aon = nt.nodes.new("ShaderNodeAmbientOcclusion"); self.aon.samples = 10; self.aon.inputs["Distance"].default_value = ao_dist
        self.ao = self.aon.outputs["AO"]                     # 1 open .. 0 occluded
        sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(self.geo.outputs["Normal"], sp.inputs[0])
        self.nz = sp.outputs["Z"]
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sp2 = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sp2.inputs[0])
        self.x, self.y, self.z = sp2.outputs["X"], sp2.outputs["Y"], sp2.outputs["Z"]
        self.pos = tc.outputs["Object"]
        self.crev = MATH(nt, "SUBTRACT", 1.0, self.ao)      # crevice mask 0..1


FINISH = {"ao": .62, "ao_dist": .3, "light": .34, "light_dir": (.25, .45, .86)}


def finish(ctx, color, k_ao=None, k_light=None, edge=None, edge_r=.012, edge_k=1.0):
    """Multiplies the paint by baked AO and a soft top/front light, optional edge-wear tint, wires an Emission output.
    k_ao / k_light override FINISH["ao"] / FINISH["light"] for one paint (0..1)."""
    nt = ctx.nt
    ao = FINISH["ao"] if k_ao is None else k_ao
    light = FINISH["light"] if k_light is None else k_light
    col = color
    if edge is not None:
        bev = nt.nodes.new("ShaderNodeBevel"); bev.samples = 4; bev.inputs["Radius"].default_value = edge_r
        d = VMATH(nt, "DOT_PRODUCT", bev.outputs["Normal"], ctx.geo.outputs["Normal"])
        e = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, d), 5.0 * edge_k, clamp=True)
        col = MIX(nt, e, col, edge)
    ao_f = MATH(nt, "ADD", MATH(nt, "MULTIPLY", ctx.ao, ao), 1.0 - ao)
    ao_f = MATH(nt, "POWER", ao_f, 1.4)
    L = Vector(FINISH["light_dir"]).normalized()
    ndl = VMATH(nt, "DOT_PRODUCT", ctx.geo.outputs["Normal"], tuple(L))
    ndl01 = MATH(nt, "ADD", MATH(nt, "MULTIPLY", ndl, .5), .5)
    lf = MATH(nt, "ADD", MATH(nt, "MULTIPLY", ndl01, light * 1.3), 1.0 - light * .75)
    col = MIX(nt, 1.0, col, ao_f, "MULTIPLY")
    col = MIX(nt, 1.0, col, lf, "MULTIPLY")
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    nt.links.new(col, em.inputs["Color"])
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs[0])


def paint(name, recipe, ao_dist=None, **fin):
    """recipe(ctx) -> color socket. Returns the material (procedural, to be baked)."""
    m, nt = _mat("P_" + name)
    ctx = Ctx(nt, FINISH["ao_dist"] if ao_dist is None else ao_dist)
    finish(ctx, recipe(ctx), **fin)
    m["dv4_paint"] = True
    return m


# ------------------------------------------------------------------------------------------------- paint recipes
def paint_wood(name="Wood", base="B9743F", dark="6B4128", light="DDA55F", scale=3.0, along="X", edge="E2B57A", dist=4.0, tint=.2,
               stretch=9.0, **fin):
    """Grain runs along `along`; tint = per-part random lightening (uses the Paint attribute, so each plank differs)."""
    def r(c):
        nt = c.nt
        s = {"X": (1, stretch, stretch), "Y": (stretch, 1, stretch), "Z": (stretch, stretch, 1)}[along]
        v = COORD(nt, scale=s)
        dr = {"X": "Y", "Y": "X", "Z": "X"}[along]
        grain = WAVE(nt, v, scale=scale, dist=dist, detail=2.0, dscale=1.2, direction=dr)
        lines = WAVE(nt, v, scale=scale * 3.1, dist=dist * .7, detail=1.0, dscale=1.0, direction=dr)
        fine = NOISE(nt, COORD(nt, scale=(40, 40, 40)), 1.0, 2.0)
        g = MATH(nt, "ADD", MATH(nt, "MULTIPLY", grain, .62), MATH(nt, "ADD", MATH(nt, "MULTIPLY", lines, .26), MATH(nt, "MULTIPLY", fine, .12)))
        col = RAMP(nt, g, [(.0, dark), (.12, base), (.34, light), (.5, base), (.57, dark), (.62, dark), (.7, base), (.86, light), (1.0, base)])
        knots = SMOOTH(nt, lines, .9, .97)
        col = MIX(nt, MATH(nt, "MULTIPLY", knots, .5), col, dark)
        tone = NOISE(nt, COORD(nt, scale=(.6, .6, .6)), 1.0, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", tone, .3), col, dark)
        if tint > 0:
            t, s_, rnd = ATTR(nt)
            col = MIX(nt, MATH(nt, "MULTIPLY", rnd, tint), col, light)
        return col
    return paint(name, r, edge=edge, edge_k=.8, **fin)


def paint_iron(name="Iron", base="222A33", mid="343F4A", edge="8A949C", rust="7E4524", rust_amt=.35, **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 14.0, 4.0, .6)
        col = RAMP(nt, mot, [(.3, base), (.7, mid)])
        spk = NOISE(nt, c.pos, 90.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", spk, .25), col, mid)
        rm = MATH(nt, "MULTIPLY", SMOOTH(nt, NOISE(nt, c.pos, 7.0, 3.0), .55, .8), MATH(nt, "ADD", c.crev, .35), clamp=True)
        col = MIX(nt, MATH(nt, "MULTIPLY", rm, rust_amt), col, rust)
        return col
    return paint(name, r, edge=edge, edge_k=1.2, edge_r=.01, **fin)


def paint_terracotta(name="Pot", base="CC6E44", dark="9A4F31", glaze=TEAL, glaze_light="5BC2B4", glaze_z=.22, drip=.07, **fin):
    """Terracotta body, glossy glaze poured from the top with drips (glaze_z = height where drips end, Blender z)."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 9.0, 3.0)
        col = RAMP(nt, mot, [(.25, dark), (.75, base)])
        spk = NOISE(nt, c.pos, 60.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", spk, .2), col, dark)
        ang = MATH(nt, "ARCTAN2", c.y, c.x)
        dr = NOISE(nt, VMATH(nt, "MULTIPLY", VMATH(nt, "ADD", c.pos, (0, 0, 0)), (1, 1, .15)), 6.0, 2.0)
        drip_edge = MATH(nt, "ADD", glaze_z, MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", dr, .5), drip * 2))
        gm = SMOOTH(nt, MATH(nt, "SUBTRACT", c.z, drip_edge), -.004, .004)
        gshade = NOISE(nt, c.pos, 5.0, 2.0)
        gcol = RAMP(nt, gshade, [(.3, glaze), (.8, glaze_light)])
        # glossy highlight band near the top light
        hl = SMOOTH(nt, c.nz, .15, .75)
        gcol = MIX(nt, MATH(nt, "MULTIPLY", hl, .35), gcol, "BFEDE6")
        # darker glaze rim just above the drip edge (thicker pooled glaze)
        pool = SMOOTH(nt, MATH(nt, "SUBTRACT", c.z, drip_edge), .0, .03)
        gcol = MIX(nt, MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, pool), .5), gcol, "157A70")
        return MIX(nt, gm, col, gcol)
    return paint(name, r, edge="E8A076", edge_k=.5, edge_r=.006, **fin)


def paint_stone(name="Stone", base="E3D5BC", dark="B09A78", light="F4ECDC", moss="5E7E3C", moss_amt=.6, moss_z=None,
                blocks=None, groove="8E7C60", **fin):
    """Mottled carved stone, moss in the crevices (AO) and optionally below moss_z.
    blocks=(n_around, [z of horizontal joints], z0, z1) paints masonry joints on the wall between z0 and z1."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 5.0, 4.0, .6)
        col = RAMP(nt, mot, [(.2, dark), (.5, base), (.85, light)])
        spk = VORO(nt, c.pos, 45.0, "F1", "Distance")
        col = MIX(nt, MATH(nt, "MULTIPLY", spk, .3), col, dark)
        pits = SMOOTH(nt, NOISE(nt, c.pos, 18.0, 2.0), .62, .72)
        col = MIX(nt, MATH(nt, "MULTIPLY", pits, .35), col, dark)
        veins = SMOOTH(nt, NOISE(nt, c.pos, 2.5, 3.0, .5, 1.5), .48, .515)
        col = MIX(nt, MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, veins), .3), col, dark)
        if blocks:
            n, zs, z0, z1 = blocks
            ang = MATH(nt, "ARCTAN2", c.y, c.x)
            u = MATH(nt, "MULTIPLY", ang, n / (2 * math.pi))
            du = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "FRACT", u), .5))     # .5 at joint
            gv = SMOOTH(nt, du, .5 - .035, .5 - .012)
            gm = gv
            for z in zs:
                dz = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", c.z, z))
                gm = MATH(nt, "MAXIMUM", gm, SMOOTH(nt, dz, .012, .004))
            band = MATH(nt, "MULTIPLY", SMOOTH(nt, c.z, z0 - .01, z0 + .01), SMOOTH(nt, c.z, z1 + .01, z1 - .01))
            gm = MATH(nt, "MULTIPLY", gm, band)
            wobble = MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 30.0, 2.0), .5)
            gm = MATH(nt, "MULTIPLY", gm, MATH(nt, "ADD", .6, wobble), clamp=True)
            col = MIX(nt, gm, col, groove)
        mm = MATH(nt, "MULTIPLY", MATH(nt, "POWER", c.crev, 2.2), NOISE(nt, c.pos, 8.0, 3.0))
        mm = MATH(nt, "MULTIPLY", mm, moss_amt * 4.0, clamp=True)
        if moss_z is not None:
            mm = MATH(nt, "MULTIPLY", mm, SMOOTH(nt, c.z, moss_z + .2, moss_z))
        mcol = RAMP(nt, NOISE(nt, c.pos, 25.0, 2.0), [(.3, "3F5E2A"), (.8, moss)])
        return MIX(nt, mm, col, mcol)
    return paint(name, r, edge="FBF8F1", edge_k=.7, edge_r=.015, **fin)


def paint_leaf(name="Leaf", base="3F8F3A", dark="23602A", light="8CCB55", vein="B9E08A", veins=7, **fin):
    """Uses the Paint attribute written by leaf(): R along the midrib, G across, B random per leaf."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        sc = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", s, .5))      # 0 midrib .. .5 edge
        grad = MATH(nt, "ADD", MATH(nt, "MULTIPLY", t, .5), MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 12.0, 2.0), .5))
        col = RAMP(nt, grad, [(.1, dark), (.5, base), (.95, light)])
        col = MIX(nt, MATH(nt, "MULTIPLY", rnd, .3), col, light)
        col = MIX(nt, MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, sc), .25), col, dark)   # darker toward the edge
        mid = SMOOTH(nt, sc, .035, .012)
        # side veins: diagonal lines running from the midrib to the edge
        ph = MATH(nt, "ADD", MATH(nt, "MULTIPLY", t, veins), MATH(nt, "MULTIPLY", sc, -3.0))
        sv = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "FRACT", ph), .5))
        sv = SMOOTH(nt, sv, .46, .5)
        sv = MATH(nt, "MULTIPLY", sv, SMOOTH(nt, sc, .03, .07))
        sv = MATH(nt, "MULTIPLY", sv, SMOOTH(nt, sc, .46, .38))
        vm = MATH(nt, "ADD", mid, MATH(nt, "MULTIPLY", sv, .55), clamp=True)
        col = MIX(nt, vm, col, vein)
        return col
    return paint(name, r, k_ao=.45, k_light=.4, **fin)


def paint_soil(name="Soil", base="4A3322", dark="2E1E14", light="6E4C33", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 25.0, 4.0, .65)
        col = RAMP(nt, mot, [(.25, dark), (.6, base), (.9, light)])
        crumbs = VORO(nt, c.pos, 90.0, "F1", "Distance")
        col = MIX(nt, MATH(nt, "MULTIPLY", crumbs, .35), col, light)
        return col
    return paint(name, r, k_ao=.7, k_light=.25, **fin)


def paint_pebbles(name="Pebbles", cols=("F1E9DC", "D9CFC0", "BFB4A6", "F6F1E8", "C8BBA6"), **fin):
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        stops = [(i / (len(cols) - 1), h) for i, h in enumerate(cols)]
        col = RAMP(nt, rnd, stops, "CONSTANT")
        mot = NOISE(nt, c.pos, 40.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .2), col, "9E9183")
        return col
    return paint(name, r, edge="FFFFFF", edge_k=.5, edge_r=.004, **fin)


def paint_water(name="Water", deep="2A8FB8", shallow="6FCDE3", foam="F2FBFD", scale=6.0, flow=(1, 1, 1), caustic=.55, **fin):
    """Still water: blue gradient with two layers of fine caustic lines."""
    def r(c):
        nt = c.nt
        v = COORD(nt, scale=flow)
        d = VORO(nt, v, scale, "DISTANCE_TO_EDGE", "Distance")
        caus = SMOOTH(nt, d, .07, .015)
        d2 = VORO(nt, COORD(nt, scale=flow, rot=(0, 0, 30)), scale * 1.9, "DISTANCE_TO_EDGE", "Distance")
        caus2 = SMOOTH(nt, d2, .06, .018)
        base = RAMP(nt, NOISE(nt, v, 2.5, 2.0), [(.25, deep), (.8, shallow)])
        base = MIX(nt, MATH(nt, "MULTIPLY", c.crev, .5), base, deep)       # darker near the walls
        col = MIX(nt, MATH(nt, "MULTIPLY", caus, caustic), base, foam)
        col = MIX(nt, MATH(nt, "MULTIPLY", caus2, caustic * .5), col, shallow)
        return col
    return paint(name, r, k_ao=.2, k_light=.15, **fin)


def paint_stream(name="Stream", deep="4FB8DA", shallow="9BE0F0", foam="FFFFFF", streaks=18.0, axis="Z", **fin):
    """Running water: bright streaks along the flow axis with white foam edges (for jets and falling sheets)."""
    def r(c):
        nt = c.nt
        sc = {"Z": (12, 12, 1), "X": (1, 12, 12), "Y": (12, 1, 12)}[axis]
        v = COORD(nt, scale=sc)
        w = WAVE(nt, v, scale=streaks * .15, dist=2.5, detail=2.0, dscale=1.0, direction={"Z": "X", "X": "Y", "Y": "X"}[axis])
        col = RAMP(nt, w, [(.2, deep), (.55, shallow), (.85, foam)])
        bub = SMOOTH(nt, NOISE(nt, c.pos, 40.0, 2.0), .62, .72)
        col = MIX(nt, MATH(nt, "MULTIPLY", bub, .6), col, foam)
        return col
    return paint(name, r, k_ao=.15, k_light=.25, edge=foam, edge_k=.8, edge_r=.01, **fin)


def paint_flat(name, hex, dark=None, variation=.12, scale=8.0, edge=None, **fin):
    def r(c):
        nt = c.nt
        col = hex
        if variation > 0:
            mot = NOISE(nt, c.pos, scale, 3.0)
            col = MIX(nt, MATH(nt, "MULTIPLY", mot, variation), hex, dark or "000000")
        return col
    return paint(name, r, edge=edge, **fin)


def paint_gold(name="Gold", base="E0B040", dark="A8781F", light="FFE38A", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 10.0, 2.0)
        col = RAMP(nt, mot, [(.2, dark), (.55, base), (.9, light)])
        hl = SMOOTH(nt, c.nz, .2, .9)
        return MIX(nt, MATH(nt, "MULTIPLY", hl, .4), col, light)
    return paint(name, r, edge=light, edge_k=1.0, edge_r=.006, **fin)


# ================================================================================================= geometry helpers
def _attr_paint(me, rnd=None):
    """Adds the Paint color attribute (per-part random in B) to a mesh if missing."""
    if "Paint" in me.color_attributes:
        return
    ca = me.color_attributes.new("Paint", "BYTE_COLOR", "CORNER")
    b = RNG.random() if rnd is None else rnd
    vals = [0.0, 0.0, b, 1.0] * len(me.loops)
    ca.data.foreach_set("color_srgb", vals)


def _obj(name, me, paint=None, out="Body", loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), smooth=True, mat_override=None):
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = [rad(a) for a in rot]; ob.scale = scale
    ob["dv4_out"] = out
    if mat_override:
        ob["dv4_mat"] = mat_override
    if paint is not None and hasattr(me, "materials"):
        me.materials.append(paint)
    if hasattr(me, "polygons"):
        for p in me.polygons:
            p.use_smooth = smooth
    PARTS.append(ob)
    return ob


def from_bm(name, bm, paint=None, out="Body", loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), smooth=True, mat_override=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return _obj(name, me, paint, out, loc, rot, scale, smooth, mat_override)


def cube(name, size, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", bevel=.01, segs=2, **kw):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    ob = from_bm(name, bm, paint, out, loc, rot, smooth=False, **kw)
    if bevel > 0:
        mod_bevel(ob, min(bevel, min(size) * .45), segs)
    return ob


def lathe_bm(profile, seg=32, cap=True, scallop=None, smooth=True):
    """profile [(r, z)] bottom to top around Z. scallop=(n, amp) modulates the radius with cos(n*theta)."""
    bm = bmesh.new(); rings = []
    for r, z in profile:
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            rr = r * (1 + scallop[1] * math.cos(scallop[0] * a)) if scallop and r > 1e-5 else r
            ring.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(seg):
            a, b = rings[i][k], rings[i][(k + 1) % seg]
            c, d = rings[i + 1][(k + 1) % seg], rings[i + 1][k]
            try:
                f = bm.faces.new((a, b, c, d)); f.smooth = smooth
            except ValueError:
                pass
    if cap:
        if profile[-1][0] > 1e-4:
            f = bm.faces.new(rings[-1]); f.smooth = False
        if profile[0][0] > 1e-4:
            f = bm.faces.new(list(reversed(rings[0]))); f.smooth = False
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def lathe(name, profile, seg=32, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", cap=True, scallop=None, **kw):
    bm = lathe_bm(profile, seg, cap, scallop)
    return from_bm(name, bm, paint, out, loc, rot, **kw)


def cylinder(name, r, h, loc=(0, 0, 0), rot=(0, 0, 0), seg=24, paint=None, out="Body", bevel=0.0, **kw):
    b = min(bevel, r * .45, h * .45)
    if b > 0:
        prof = [(0, 0), (r - b, 0), (r - b * .3, b * .3), (r, b), (r, h - b), (r - b * .3, h - b * .3), (r - b, h), (0, h)]
    else:
        prof = [(0, 0), (r, 0), (r, h), (0, h)]
    return lathe(name, prof, seg, loc, rot, paint, out, cap=True, **kw)


def sphere(name, r, loc=(0, 0, 0), scale=(1, 1, 1), seg=16, rings=10, paint=None, out="Body", rot=(0, 0, 0), **kw):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    return from_bm(name, bm, paint, out, loc, rot, scale, **kw)


def icosphere(name, r, loc=(0, 0, 0), scale=(1, 1, 1), subdiv=2, paint=None, out="Body", rot=(0, 0, 0), **kw):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
    return from_bm(name, bm, paint, out, loc, rot, scale, **kw)


def torus(name, R, r, loc=(0, 0, 0), rot=(0, 0, 0), seg=32, minor=10, paint=None, out="Body", arc=360.0, **kw):
    bm = bmesh.new(); verts = []
    n = seg if arc >= 360 else seg + 1
    for i in range(n):
        a = rad(arc) * i / seg
        ring = []
        for j in range(minor):
            b = 2 * math.pi * j / minor
            ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        verts.append(ring)
    for i in range(seg):
        for j in range(minor):
            a_, b_ = verts[i][j], verts[(i + 1) % n][j]
            c_, d_ = verts[(i + 1) % n][(j + 1) % minor], verts[i][(j + 1) % minor]
            f = bm.faces.new((a_, b_, c_, d_)); f.smooth = True
    if arc < 360:
        bm.faces.new(list(reversed(verts[0]))); bm.faces.new(verts[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bm(name, bm, paint, out, loc, rot, **kw)


def tube(name, points, radius=.02, res=8, paint=None, out="Body", loc=(0, 0, 0), rot=(0, 0, 0), cyclic=False, kind="BEZIER",
         resolution=10, taper=None, caps=True, **kw):
    """Round tube along a smooth curve through `points` (Bezier auto handles). taper: [(t, scale)] optional radius profile."""
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = radius; cu.bevel_resolution = max(0, (res - 4) // 2)   # sides = 4 + 2 * bevel_resolution; cu.resolution_u = resolution; cu.use_fill_caps = caps
    sp = cu.splines.new(kind)
    if kind == "BEZIER":
        sp.bezier_points.add(len(points) - 1)
        for bp, p in zip(sp.bezier_points, points):
            bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"
    else:
        sp.points.add(len(points) - 1)
        for sp_, p in zip(sp.points, points):
            sp_.co = (*p, 1.0)
        sp.use_endpoint_u = True; sp.order_u = min(4, len(points))
    sp.use_cyclic_u = cyclic; sp.use_smooth = True; sp.resolution_u = resolution   # the spline value is the one that counts
    if taper:
        tc = bpy.data.curves.new(name + "_taper", "CURVE"); tc.dimensions = "2D"
        ts = tc.splines.new("POLY"); ts.points.add(len(taper) - 1)
        for tp, (t, s) in zip(ts.points, taper):
            tp.co = (t, s, 0, 1)
        tob = bpy.data.objects.new(name + "_taper", tc); bpy.context.scene.collection.objects.link(tob)
        cu.taper_object = tob; tob["dv4_skip"] = True
    ob = _obj(name, cu, paint, out, loc, rot, smooth=True, **kw)
    return ob


def spiral(center, r0, r1, turns, n=24, a0=0.0, plane="YZ", ccw=True):
    """Points of a flat Archimedean spiral (for cast-iron scrolls). plane 'YZ' (side frames) or 'XZ' or 'XY'."""
    pts = []
    for i in range(n + 1):
        t = i / n
        a = a0 + (1 if ccw else -1) * t * turns * 2 * math.pi
        r = r0 + (r1 - r0) * t
        u, v = math.cos(a) * r, math.sin(a) * r
        if plane == "YZ":
            pts.append((center[0], center[1] + u, center[2] + v))
        elif plane == "XZ":
            pts.append((center[0] + u, center[1], center[2] + v))
        else:
            pts.append((center[0] + u, center[1] + v, center[2]))
    return pts


def leaf(name, L, W, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", shape="fiddle", bend=.35, cup=.18, twist=0.0,
         thickness=.004, nl=7, nw=4, rnd=None, wave=0.0, **kw):
    """A leaf blade with real thickness. Local: base at origin, grows along +Y, Z up; writes the Paint attribute."""
    def width(t):
        if shape == "fiddle":       # violin shape: waist near the base, broad round top
            if t < .72:
                w = (t / .72) ** .35 * (1 - .22 * math.exp(-((t - .3) / .12) ** 2))
            else:
                w = max(0.0, 1 - ((t - .72) / .28) ** 2) ** .5
        elif shape == "heart":      # pothos / philodendron
            w = (1 - t) ** .45 * math.sin(math.pi * min(1, t * 1.6 + .05)) ** .5
        elif shape == "spade":      # peace lily / rubber fig
            w = math.sin(math.pi * t) ** .75
        else:                       # pointed ellipse
            w = math.sin(math.pi * t) ** .85
        return max(.015, w)
    bm = bmesh.new()
    lay = bm.loops.layers.color.new("Paint")
    rows = []
    b = RNG.random() if rnd is None else rnd
    for i in range(nl + 1):
        t = i / nl
        w = width(t) * W * .5
        y = t * L
        z = -bend * L * (t ** 2) + wave * L * .03 * math.sin(t * 9)
        row = []
        for j in range(nw + 1):
            s = -1 + 2 * j / nw
            x = s * w
            zz = z + cup * abs(s) ** 1.5 * w + twist * s * t * .05
            v = bm.verts.new((x, y, zz)); row.append(v)
        rows.append(row)
    for i in range(nl):
        for j in range(nw):
            f = bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])); f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        for lo in f.loops:
            i = min(range(len(rows)), key=lambda k: abs(rows[k][0].co.y - lo.vert.co.y))
            t = i / nl
            w = width(t) * W * .5
            s = (lo.vert.co.x / w) * .5 + .5 if w > 1e-6 else .5
            lo[lay] = (t, min(1, max(0, s)), b, 1.0)
    ob = from_bm(name, bm, paint, out, loc, rot, **kw)
    if thickness > 0:
        mod_solidify(ob, thickness, offset=0.0)
    return ob


def patch(name, w, d, nx=12, ny=12, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", disk=False, **kw):
    """Grid plane (optionally clipped to a disk of diameter w) for soil / ground pads; displace it with mod_displace."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=.5)
    bmesh.ops.scale(bm, vec=Vector((w, d, 1)), verts=bm.verts)
    if disk:
        r = w * .5
        for v in bm.verts:
            l = math.hypot(v.co.x, v.co.y)
            if l > r:
                v.co.x *= r / l; v.co.y *= r / l
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    return from_bm(name, bm, paint, out, loc, rot, **kw)


# ------------------------------------------------------------------------------------------------- modifiers
def mod_bevel(ob, width=.01, segs=2, angle=30.0, profile=.5):
    m = ob.modifiers.new("Bevel", "BEVEL"); m.width = width; m.segments = segs; m.limit_method = "ANGLE"; m.angle_limit = rad(angle)
    m.profile = profile; m.harden_normals = False
    return m


def mod_subsurf(ob, levels=1):
    m = ob.modifiers.new("Subsurf", "SUBSURF"); m.levels = m.render_levels = levels
    return m


def mod_solidify(ob, thickness=.004, offset=0.0, rim=True):
    m = ob.modifiers.new("Solidify", "SOLIDIFY"); m.thickness = thickness; m.offset = offset; m.use_rim = rim; m.use_even_offset = True
    return m


def mod_displace(ob, strength=.02, size=.3, mid=.5, depth=2, direction="NORMAL", seed=None):
    tex = bpy.data.textures.new(ob.name + "_noise", "CLOUDS"); tex.noise_scale = size; tex.noise_depth = depth
    if seed is not None:
        tex.noise_basis = "ORIGINAL_PERLIN"
    m = ob.modifiers.new("Displace", "DISPLACE"); m.texture = tex; m.strength = strength; m.mid_level = mid; m.direction = direction
    m.texture_coords = "GLOBAL"
    return m


def mod_mirror(ob, axis=0, merge=True):
    m = ob.modifiers.new("Mirror", "MIRROR"); m.use_axis = [axis == 0, axis == 1, axis == 2]; m.use_mirror_merge = merge
    return m


def mod_array(ob, count=2, offset=(1, 0, 0), relative=False):
    m = ob.modifiers.new("Array", "ARRAY"); m.count = count
    if relative:
        m.use_relative_offset = True; m.relative_offset_displace = offset
    else:
        m.use_relative_offset = False; m.use_constant_offset = True; m.constant_offset_displace = offset
    return m


def mod_simple_deform(ob, method="BEND", angle=30.0, axis="Z"):
    m = ob.modifiers.new("Deform", "SIMPLE_DEFORM"); m.deform_method = method; m.angle = rad(angle); m.deform_axis = axis
    return m


def pivot(out, p):
    PIVOTS[out] = Vector(p)


# ================================================================================================= realize
def _select(objs, active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def realize(cfg):
    """Applies modifiers, merges parts per output object, marks sharp edges, weighted normals, returns the output objects."""
    sc = bpy.context.scene
    parts = [o for o in PARTS if o.name in sc.objects and not o.get("dv4_skip")]
    _select(parts)
    bpy.ops.object.convert(target="MESH")
    for o in list(sc.objects):
        if o.get("dv4_skip"):
            bpy.data.objects.remove(o)
    parts = [o for o in sc.objects if o.type == "MESH" and o.get("dv4_out")]
    groups = {}
    for o in parts:
        groups.setdefault(o["dv4_out"], []).append(o)
    outs = []
    for name, objs in groups.items():
        for o in objs:
            _attr_paint(o.data)
            if o.get("dv4_mat"):
                for i in range(len(o.data.materials)):
                    o.data.materials[i] = override_material(o["dv4_mat"])
                if not o.data.materials:
                    o.data.materials.append(override_material(o["dv4_mat"]))
        _select(objs)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if len(objs) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = name; ob.data.name = cfg["id"] + "_" + name
        # smooth everything, sharp where the angle says so
        bm = bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
        sharp = rad(cfg.get("sharp_angle", 52))
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            if len(e.link_faces) == 2:
                e.smooth = e.calc_face_angle(0.0) < sharp
            else:
                e.smooth = False
        bm.to_mesh(ob.data); bm.free()
        wn = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL"); wn.keep_sharp = True; wn.weight = 100
        _select([ob]); bpy.ops.object.modifier_apply(modifier=wn.name)
        outs.append(ob)
    outs.sort(key=lambda o: (o.name != "Body", o.name))
    return outs


def override_material(key):
    m = bpy.data.materials.get("OV_" + key)
    if m:
        return m
    m, nt = _mat("OV_" + key)
    em = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs[0])
    if key.startswith("C_") or key.startswith("E_"):
        em.inputs["Color"].default_value = rgba(key[2:8])
    else:
        em.inputs["Color"].default_value = (.8, .92, 1, 1)
    m["dv4_override"] = key
    return m


# ================================================================================================= UV + bake
def unwrap(outs, size=1024, bake_margin=4):
    margin = (bake_margin + 3) / size
    for ob in outs:
        _select([ob])
        if not ob.data.uv_layers:
            ob.data.uv_layers.new(name="UVMap")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=rad(76), island_margin=.003, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    _select(outs)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, rotate_method="ANY", scale=True, merge_overlap=False,
                            margin_method="FRACTION", margin=margin, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")


def gpu():
    sc = bpy.context.scene
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for t in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = t
            except Exception:
                continue
            prefs.get_devices()
            n = 0
            for d in prefs.devices:
                d.use = d.type != "CPU"; n += d.use
            if n:
                sc.cycles.device = "GPU"; log("bake device", t, [d.name for d in prefs.devices if d.use])
                return True
    except Exception as e:
        log("gpu setup failed, CPU bake:", e)
    sc.cycles.device = "CPU"
    return False


BAKE_MARGIN = 4


def bake(outs, name, size, samples=64):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    gpu()
    sc.cycles.samples = samples; sc.cycles.use_denoising = False; sc.cycles.use_adaptive_sampling = False
    if not sc.world:
        sc.world = bpy.data.worlds.new("W")
    img = bpy.data.images.new("IK_D4_" + name + "_albedo", size, size, alpha=False)
    img.generated_color = (.5, .5, .5, 1)
    for ob in outs:
        for mat in ob.data.materials:
            nt = mat.node_tree
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.name = "BAKE"
            nt.nodes.active = tex
    b = sc.render.bake
    b.use_selected_to_active = False; b.use_clear = True; b.margin = BAKE_MARGIN; b.margin_type = "EXTEND"; b.target = "IMAGE_TEXTURES"
    _select(outs)
    t0 = time.time()
    bpy.ops.object.bake(type="EMIT")
    log("baked %s %dpx in %.1fs" % (name, size, time.time() - t0))
    path = os.path.join(D["tex"], "IK_D4_" + name + "_albedo.png")
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.color_depth = "8"
    # save_render applies the scene's view transform: the factory default (AgX) greys the whites (~197) and
    # desaturates the paint. The atlas must keep the painted colours as they are.
    vs = sc.view_settings
    vs.view_transform = "Standard"; vs.look = "None"; vs.exposure = 0; vs.gamma = 1
    img.save_render(path, scene=sc)
    img.filepath = path; img.source = "FILE"; img.reload()
    return img, path


def final_materials(outs, name, img):
    """Replaces the procedural paints by the contract materials: T_IK_D4_<Name> (baked atlas) + overrides."""
    tex_mat, nt = _mat("T_IK_D4_" + name)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.inputs["Roughness"].default_value = .62
    try:
        bsdf.inputs["Specular IOR Level"].default_value = .25
    except Exception:
        pass
    ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = img; ti.interpolation = "Linear"
    nt.links.new(ti.outputs["Color"], bsdf.inputs["Base Color"])
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(bsdf.outputs[0], out.inputs[0])
    overrides = {}
    for ob in outs:
        slots = list(ob.data.materials)
        remap = []
        for m in slots:
            key = m.get("dv4_override")
            if key:
                if key not in overrides:
                    overrides[key] = preview_material(key)
                remap.append(overrides[key])
            else:
                remap.append(tex_mat)
        uniq = []
        for m in remap:
            if m not in uniq:
                uniq.append(m)
        idx = [uniq.index(m) for m in remap]
        # Blender 5.2 drops the material_index attribute when the last slot is cleared: keep the new indices aside
        # and apply them after the slots are rebuilt (otherwise every override face lands on the baked atlas).
        faces = [idx[p.material_index] if p.material_index < len(idx) else 0 for p in ob.data.polygons]
        ob.data.materials.clear()
        for m in uniq:
            ob.data.materials.append(m)
        ob.data.polygons.foreach_set("material_index", faces)
        ob.data.update()
    return [tex_mat] + list(overrides.values())


def preview_material(key):
    """Flat contract materials for the preview renders (C_/E_/G_Glass), like build_interior_kit.material()."""
    m = bpy.data.materials.get(key)
    if m:
        return m
    m = bpy.data.materials.new(key); m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF"); bsdf.inputs["Roughness"].default_value = .7
    if key.startswith("C_"):
        bsdf.inputs["Base Color"].default_value = rgba(key[2:8])
    elif key.startswith("E_"):
        bsdf.inputs["Base Color"].default_value = rgba(key[2:8]); bsdf.inputs["Emission Color"].default_value = rgba(key[2:8])
        bsdf.inputs["Emission Strength"].default_value = 2.5
    elif key == "G_Glass":
        bsdf.inputs["Base Color"].default_value = (.8, .92, 1, 1); bsdf.inputs["Alpha"].default_value = .3; bsdf.inputs["Roughness"].default_value = .05
        m.surface_render_method = "BLENDED"
    elif key.startswith("T_"):
        tex = key[2:]
        for folder in (D["tex"], ASSET_TEX):
            p = os.path.join(folder, tex + "_albedo.png")
            if os.path.exists(p):
                img = bpy.data.images.load(p)
                ti = m.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = img
                m.node_tree.links.new(ti.outputs["Color"], bsdf.inputs["Base Color"])
                break
        else:
            bsdf.inputs["Base Color"].default_value = (.75, .7, .62, 1)
    return m


# ================================================================================================= export + stats
def set_pivots(outs):
    for ob in outs:
        if ob.name == "Body":
            continue
        me = ob.data
        if ob.name in PIVOTS:
            p = Vector(PIVOTS[ob.name])
        else:
            xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
            base = ob.name.startswith("Anim Sway")
            p = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs) if base else (min(zs) + max(zs)) / 2))
            if ob.name.startswith("Anim Spin"):
                p.x = p.y = 0.0
        me.transform(Matrix.Translation(-p)); ob.location = p


def export_fbx(outs, path):
    _select(outs)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, axis_forward="-Z", axis_up="Y", bake_anim=False,
                             path_mode="STRIP", use_mesh_modifiers=True, mesh_smooth_type="OFF", apply_scale_options="FBX_SCALE_ALL",
                             use_tspace=False)


def tri_count(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == "MESH")


def bounds(objs):
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


# ================================================================================================= rendering
def _light_rig(warm=True):
    sc = bpy.context.scene
    for n in ("DV4_Sun", "DV4_Fill", "DV4_Rim", "DV4_Cam", "DV4_Floor"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o)
    sun = bpy.data.objects.new("DV4_Sun", bpy.data.lights.new("DV4_Sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 2.6; sun.data.angle = rad(6); sun.rotation_euler = (rad(40), rad(10), rad(150)); sun.data.color = (1, .96, .9)
    fill = bpy.data.objects.new("DV4_Fill", bpy.data.lights.new("DV4_Fill", "SUN")); sc.collection.objects.link(fill)
    fill.data.energy = .9; fill.data.angle = rad(40); fill.rotation_euler = (rad(55), 0, rad(-50)); fill.data.color = (.85, .92, 1)
    fill.data.use_shadow = False
    rim = bpy.data.objects.new("DV4_Rim", bpy.data.lights.new("DV4_Rim", "SUN")); sc.collection.objects.link(rim)
    rim.data.energy = 1.2; rim.data.angle = rad(20); rim.rotation_euler = (rad(60), 0, rad(-150)); rim.data.use_shadow = False
    cam = bpy.data.objects.new("DV4_Cam", bpy.data.cameras.new("DV4_Cam")); sc.collection.objects.link(cam); sc.camera = cam
    if not sc.world:
        sc.world = bpy.data.worlds.new("DV4_World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (1, .97, .9, 1) if warm else (.84, .87, .9, 1); bg.inputs["Strength"].default_value = .55 if warm else .8
    sc.render.engine = "BLENDER_EEVEE"
    try:
        sc.eevee.taa_render_samples = 48; sc.eevee.use_shadows = True; sc.eevee.shadow_ray_count = 2; sc.eevee.shadow_step_count = 4
        sc.eevee.use_fast_gi = True; sc.eevee.fast_gi_method = "GLOBAL_ILLUMINATION"; sc.eevee.fast_gi_distance = 1.0
    except Exception as e:
        log("eevee settings:", e)
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = -.15
    sc.render.image_settings.file_format = "PNG"
    return cam


def _aim(cam, center, d, dist):
    cam.location = center + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()


def thumbnail(objs, path, size=256):
    """Like build_interior_kit.thumbnail(): ortho 3/4 from (.55, 1, .75), warm world, transparent film."""
    sc = bpy.context.scene
    cam = _light_rig(True)
    lo, hi = bounds(objs); center = (lo + hi) / 2; radius = max((hi - lo).length * .5, .3)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = radius * 2.1; cam.data.clip_end = radius * 30
    d = Vector((.55, 1, .75)).normalized(); _aim(cam, center, d, radius * 6)
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = size; sc.render.resolution_percentage = 100
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)


def previews(objs, base, floor="F4EFE4", views=(("game", 28, 52, 3.3, 40), ("close", 36, 22, 1.55, 45))):
    """<base>_game.png: perspective from the game camera, small on screen; <base>_close.png: beauty shot. 800x800."""
    sc = bpy.context.scene
    cam = _light_rig(False)
    lo, hi = bounds(objs); center = (lo + hi) / 2; radius = max((hi - lo).length * .5, .3)
    fl = None
    if floor:
        me = bpy.data.meshes.new("DV4_Floor"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=400)
        bm.to_mesh(me); bm.free(); fl = bpy.data.objects.new("DV4_Floor", me); sc.collection.objects.link(fl); fl.location = (0, 0, lo.z - .001)
        fm = bpy.data.materials.new("DV4_FloorMat"); fm.use_nodes = True
        fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = rgba(floor); fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .9
        me.materials.append(fm)
    cam.data.type = "PERSP"; cam.data.clip_end = 200
    sc.render.film_transparent = False; sc.render.resolution_x = sc.render.resolution_y = 800; sc.render.resolution_percentage = 100
    sc.render.image_settings.color_mode = "RGB"
    outs = []
    for name, az, el, k, lens in views:
        a, e = rad(az), rad(el)
        d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
        cam.data.lens = lens
        _aim(cam, center, d, radius * k * 1.7)
        sc.render.filepath = base + "_" + name + ".png"; bpy.ops.render.render(write_still=True); outs.append(sc.render.filepath)
    if fl:
        bpy.data.objects.remove(fl)
    return outs


def render_old(id_, floor):
    """Imports the FBX that is in Assets today, colours it by material name, renders previews/<id>_old_{game,close}.png."""
    path = os.path.join(OLD_MODELS, id_ + ".fbx")
    if not os.path.exists(path):
        log("no old model", path); return None
    reset()
    before = set(bpy.data.materials.keys()); imgs = set(bpy.data.images.keys())
    bpy.ops.import_scene.fbx(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for n in [n for n in bpy.data.images.keys() if n not in imgs]:
        bpy.data.images.remove(bpy.data.images[n])
    keys = {}
    for mname in [n for n in bpy.data.materials.keys() if n not in before]:
        mat = bpy.data.materials[mname]; keys["old_" + mname] = mname.split(".")[0]; mat.name = "old_" + mname
    for o in objs:
        for i, mat in enumerate(o.data.materials):
            if mat is not None:
                o.data.materials[i] = preview_material(keys.get(mat.name, mat.name.split(".")[0]))
    tris = tri_count(objs); lo, hi = bounds(objs)
    previews(objs, os.path.join(D["previews"], id_ + "_old"), floor)
    return {"tris": tris, "footprint": [round(max(abs(lo.x), abs(hi.x)), 3), round(max(abs(lo.y), abs(hi.y)), 3), round(hi.z, 3)]}


# ================================================================================================= driver
def run_item(id_, module):
    t0 = time.time()
    cfg0 = getattr(module, "CONFIG", {})
    old = render_old(id_, cfg0.get("floor", "F4EFE4"))
    reset()
    RNG.seed(cfg0.get("seed", 4))
    cfg = module.build() or {}
    cfg.setdefault("id", id_); cfg.setdefault("name", "".join(w.capitalize() for w in id_.split("-")))
    cfg.setdefault("tex", 1024); cfg.setdefault("budget", 15000); cfg.setdefault("floor", "F4EFE4")
    name = cfg["name"]
    outs = realize(cfg)
    tris = tri_count(outs)
    log("realized", [o.name for o in outs], "tris", tris)
    unwrap(outs, cfg["tex"], BAKE_MARGIN)
    img, tex_path = bake(outs, name, cfg["tex"], cfg.get("samples", 64))
    mats = final_materials(outs, name, img)
    set_pivots(outs)
    lo, hi = bounds(outs)
    fbx = os.path.join(D["fbx"], id_ + ".fbx"); export_fbx(outs, fbx)
    thumbnail(outs, os.path.join(D["thumbs"], id_ + ".png"))
    pv = previews(outs, os.path.join(D["previews"], id_), cfg["floor"])
    entry = {"name": name, "tris": tris, "budget": cfg["budget"], "within_budget": tris <= cfg["budget"],
             "footprint_half_x_half_z_height": [round(max(abs(lo.x), abs(hi.x)), 3), round(max(abs(lo.y), abs(hi.y)), 3), round(hi.z, 3)],
             "size_xyz": [round(hi.x - lo.x, 3), round(hi.y - lo.y, 3), round(hi.z - lo.z, 3)],
             "objects": [o.name for o in outs], "anim": [o.name for o in outs if o.name.startswith("Anim")],
             "pivots": {o.name: [round(c, 4) for c in o.location] for o in outs if o.name != "Body"},
             "materials": [m.name for m in mats], "texture": os.path.basename(tex_path), "texture_size": cfg["tex"],
             "fbx": fbx, "thumb": os.path.join(D["thumbs"], id_ + ".png"), "previews": pv,
             "old": old, "secs": round(time.time() - t0, 1), "date": time.strftime("%Y-%m-%d %H:%M")}
    rp = os.path.join(ROOT, "report.json")
    for _ in range(5):
        try:
            rep = json.load(open(rp)) if os.path.exists(rp) else {}
            rep[id_] = entry
            json.dump(rep, open(rp, "w"), indent=1)
            break
        except Exception as e:
            log("report retry", e); time.sleep(.5)
    print("DV4DONE " + json.dumps({id_: entry}), flush=True)
    return entry
