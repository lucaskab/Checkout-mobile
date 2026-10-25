"""Lot-clearing works scene, v1: vehicles and props redone in the city / lots style, drop-in compatible with the
code that animates them (CheckoutWorks*.cs, CheckoutLotSites.cs, CheckoutSkipLoad.cs, CheckoutEraWorks.cs).

Run inside Blender (MCP):
    import sys, importlib; sys.path.insert(0, r"C:\\Checkout-mobile\\scripts\\blender")
    import works_v1 as W; importlib.reload(W)

Convention (kept from the current Resources/CheckoutWorks/*.fbx): every model is built in the frame Blender shows
after importing the current FBX - root `Body` turned 180 deg about Z (rot -pi), the machine's front towards -Y -,
each named part keeps the imported part's origin (its pivot), parent and local transform; the new geometry is
written into the part's local space. Export: same FBX settings as checkout_project.export_unity, without the extra
turn (the root already carries it). Outputs: Temp/qa/works_v1/ (+ export/). One material <file>_Mat, one baked
<file>_BaseColor.png at the current texture size. No letters or words anywhere.
"""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix, Euler
import lots_v3 as V
from lots_v3 import G, C, M, OM, NT, col, show_only

UNITY = V.UNITY
SRC = os.path.join(UNITY, "Assets", "Resources", "CheckoutWorks")
QA = os.path.join(UNITY, "Temp", "qa", "works_v1")
EXPORT = os.path.join(QA, "export")
VIEW = Vector((1.0, -1.25, .95))                  # before / after 3/4 view (front-right, from above)
WM = {}


def render(name):
    os.makedirs(QA, exist_ok=True)
    sc = bpy.context.scene
    sc.render.filepath = os.path.join(QA, name + ".png")
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


# ------------------------------------------------------------------ the current models
def old_model(name):
    """Imports Resources/CheckoutWorks/<name>.fbx into 'OLD <name>' with its own baked texture."""
    cname = "OLD " + name
    c = col(cname)
    if c.objects: return c
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(SRC, name + ".fbx"))
    objs = [o for o in bpy.data.objects if o not in before]
    img = old_tex(name)
    mat = bpy.data.materials.new("OLDMAT_" + name); mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = img
    bs = mat.node_tree.nodes["Principled BSDF"]
    mat.node_tree.links.new(tex.outputs["Color"], bs.inputs["Base Color"]); bs.inputs["Roughness"].default_value = .85
    for o in objs:
        for cc in list(o.users_collection): cc.objects.unlink(o)
        c.objects.link(o); o.name = "OLD_" + name + "_" + o.name.split(".")[0]
        if o.type == 'MESH':
            o.data.materials.clear(); o.data.materials.append(mat)
    return c


def old_tex(name):
    """The current atlas, loaded under its own name (bake() removes every image whose name starts with
    '<file>_BaseColor', which used to delete this one and blank the old models / the kits' kept objects)."""
    im = bpy.data.images.get("OLDTEX_" + name)
    if im is None:
        im = bpy.data.images.load(os.path.join(SRC, name + "_BaseColor.png"), check_existing=False)
        im.name = "OLDTEX_" + name
    return im


def template(name):
    """The current model's parts: {part: (parent part, local matrix, world matrix)} in the imported frame."""
    c = old_model(name)
    bpy.context.view_layer.update()
    pre = "OLD_" + name + "_"
    out = {}
    for o in c.objects:
        part = o.name[len(pre):]
        out[part] = (o.parent.name[len(pre):] if o.parent else None, o.matrix_local.copy(), o.matrix_world.copy())
    return out


def bounds(objs):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        if o.type != 'MESH': continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def shots(prefix, cname, centre, ortho, game=True):
    """Same-camera views: the 3/4 view (and the game's angle) of a collection."""
    show_only(cname)
    out = []
    V.camera(centre, ortho, VIEW); out.append(render(prefix))
    if game:
        V.camera(centre, ortho * 1.05, V.GAME_DIR); out.append(render(prefix + "_game"))
    return out


# ------------------------------------------------------------------ materials (procedural, baked into the one atlas)
def m_machine(name, paint, mud=C("7A5B3E"), mud_z=(.0, .55), scuff=.5, rust=0., rough=.55):
    """Machine paint: flat vivid colour with a very soft tone shift, a few crisp bare-metal scuffs (pale rim), an
    optional crisp rust patch or two, and mud splashed up from the ground (irregular, crisp-ish edge)."""
    t = NT(name, rough)
    p = t.pos; z = t.comp(p, "Z")
    col = t.mul(paint, t.ramp(t.noise(p, .6, 2, .4), .3, .7, .95, 1.04))
    if scuff:
        f = t.math('ADD', t.noise(t.scale(p, 1, 1, 2.5), 2.2, 2, .5), t.math('MULTIPLY', t.noise(p, 14, 2), .05))
        thr = .75 - scuff * .04
        sc = t.ramp(f, thr, thr + .005)
        col = t.mix(col, (paint[0] * .78, paint[1] * .78, paint[2] * .78, 1), t.math('SUBTRACT', t.ramp(f, thr - .025, thr - .02), sc))
        col = t.mix(col, C("9EA3A2"), sc)
    if rust:
        f = t.math('ADD', t.noise(t.scale(p, 1, 1, .6), 1.0, 2, .5), t.math('MULTIPLY', t.noise(p, 9, 2), .04))
        thr = .76 - rust * .08
        r = t.ramp(f, thr, thr + .004)
        col = t.mix(col, t.mix(C("A45A30"), C("7A3E22"), t.ramp(t.noise(p, 14, 2), .4, .6)), r)
    if mud:
        m = t.math('ADD', z, t.math('MULTIPLY', t.noise(p, 3.5, 3, .6), .22))
        mf = t.ramp(m, mud_z[0] + (mud_z[1] - mud_z[0]) * .55, mud_z[1], .85, 0)
        col = t.mix(col, t.mul(mud, t.ramp(t.noise(p, 7, 2), .3, .7, .85, 1.1)), mf)
    return t.done(col, None, 0, ao=.35, ao_dist=.35)


def m_steel(name, base=C("4B5157"), wear=C("8E949A"), mud=C("6E5238"), mud_top=.55, rough=.5):
    """Undercarriage steel: dark, worn bright on the upward-facing edges (grousers, roller tops), caked mud low down."""
    t = NT(name, rough)
    p = t.pos; z = t.comp(p, "Z"); nz = t.comp(t.geo.outputs["Normal"], "Z")
    col = t.mul(base, t.ramp(t.noise(p, 4, 2, .5), .3, .7, .9, 1.08))
    col = t.mix(col, wear, t.math('MULTIPLY', t.ramp(nz, .6, .9), .55))
    if mud:
        m = t.math('ADD', z, t.math('MULTIPLY', t.noise(p, 4, 3, .6), .25))
        col = t.mix(col, t.mul(mud, t.ramp(t.noise(p, 9, 2), .3, .7, .8, 1.15)), t.ramp(m, mud_top * .4, mud_top, .9, 0))
    return t.done(col, None, 0, ao=.4, ao_dist=.3)


def m_hazard(name, a=C("F4C430"), b=C("2B2E33"), pitch=.22):
    """Diagonal hazard stripes (crisp), no text."""
    t = NT(name, .5)
    w = t.n.new("ShaderNodeTexWave"); w.wave_type = 'BANDS'; w.bands_direction = 'DIAGONAL'; w.wave_profile = 'SAW'
    w.inputs["Scale"].default_value = 1.0 / pitch / 1.7; w.inputs["Distortion"].default_value = 0
    t.L.new(t.pos, w.inputs["Vector"])
    col = t.mix(a, b, t.ramp(w.outputs["Fac"], .49, .51))
    return t.done(col, None, 0, ao=.25)


SWATCH_W = ["V3_Glass", "V3_Dark", "V3_Rubber", "V3_Chrome", "V3_Orange", "V3_Headlight", "V3_Seat", "V3_Taillight",
            "V3_RimSteel", "V3_WBrick", "V3_Rebar", "V3_Lever",
            "V3_WLeaf", "V3_WLeafB", "V3_WGrassB", "V3_GrassDry", "V3_WBranch"]     # tiny leaves / blades: flat swatch cells


def mats():
    V.mats()
    if not V.OM: V.ofi_mats()
    WM.clear()
    WM["yellow"] = m_machine("V3_WYellow", C("F5B731"), mud_z=(1.0, 1.55), scuff=.35)
    WM["yellowLow"] = m_machine("V3_WYellowLow", C("F5B731"), mud_z=(.0, .75), scuff=.25)
    WM["orange"] = m_machine("V3_WOrange", C("F08A32"), mud_z=(.0, .6))
    WM["skip"] = m_machine("V3_WSkip", C("EE8A2E"), mud_z=(.0, .5), scuff=.8, rust=.45)
    WM["skipIn"] = m_machine("V3_WSkipIn", C("C9783A"), mud=C("8A7A66"), mud_z=(.0, .9), scuff=1.0, rust=.7)
    WM["teal"] = m_machine("V3_WTeal", C("2E9C8F"), mud=None, scuff=0)
    WM["grey"] = m_machine("V3_WGrey", C("5E656C"), mud=None, scuff=.6, rough=.5)
    WM["steel"] = m_steel("V3_WTrack")
    WM["frame"] = m_steel("V3_WTrackFrame", base=C("3F4449"), wear=C("6E747A"), mud_top=.75)
    WM["hazard"] = m_hazard("V3_WHazard")
    WM["cream"] = m_machine("V3_WCream", C("F3EEE2"), mud_z=(.0, .7), scuff=.12)
    WM["alu"] = m_machine("V3_WAlu", C("C9CFD2"), mud=None, scuff=0, rough=.4)
    WM["deck"] = m_steel("V3_WDeck", base=C("6B7278"), wear=C("A3A9AD"), mud=None)
    WM["ball"] = m_steel("V3_WBall", base=C("3E4348"), wear=C("7B8288"), mud=None)
    WM["container"] = V.m_metal_paint("V3_WContainer", C("2F8C86"), amount=.25)
    WM["contFrame"] = m_machine("V3_WContFrame", C("2A6F6B"), mud_z=(.0, .4), scuff=.3, rust=.5)
    WM["slabW"] = V.m_flat("V3_WSlabWarm", C("E4D3AE"), .05, 2, .9, island=.08, ao=.55)
    WM["plasterT"] = V.m_flat("V3_WPlasterTeal", C("4FA89A"), .05, 3, .9, island=.1, ao=.5)
    WM["plasterC"] = V.m_flat("V3_WPlasterCream", C("F0D9A8"), .05, 3, .9, island=.1, ao=.5)
    WM["mound"] = V.m_flat("V3_WMound", C("8E7253"), .08, 1.5, .95, ao=.5)
    WM["hazRW"] = m_hazard("V3_WHazRW", C("E8483A"), C("F6F0E2"), .26)
    WM["cone"] = m_machine("V3_WCone", C("F27A2E"), mud_z=(.0, .2), scuff=.2, rough=.45)
    WM["white"] = V.m_flat("V3_WReflect", C("F4F1E6"), .03, 4, .4, ao=.3)
    WM["beam"] = V.m_rust("V3_WBeam", C("8C9497"), amount=.45)
    WM["sheet"] = V.m_metal_paint("V3_WSheet", C("B3C2C4"), amount=.35)
    WM["card"] = V.m_flat("V3_WCardboard", C("C9A06A"), .06, 3, .9, ao=.45)
    WM["tape"] = V.m_flat("V3_WTape", C("E2C891"), .04, 6, .6, ao=.3)
    WM["branch"] = V.m_flat("V3_WBranch", C("6B4A31"), .1, 6, .9, island=.1, ao=.5)
    WM["leaf"] = V.m_green("V3_WLeaf", C("3E7A2F"), C("9CCB52"), .0, .9)
    WM["leafB"] = V.m_green("V3_WLeafB", C("3E7A2F"), C("9CCB52"), -.25, .3)
    WM["grassB"] = V.m_green("V3_WGrassB", C("5E8F2E"), C("C9D86A"), -.25, .3)
    WM["sack"] = V.m_flat("V3_WSack", C("DCD3C2"), .06, 4, .9, island=.06, ao=.3)
    WM["slab"] = V.m_flat("V3_WSlab", C("D3CDBF"), .05, 2, .9, island=.08, ao=.55)
    WM["brick"] = V.m_flat("V3_WBrick", C("C4623E"), .06, 8, .85, island=.12, ao=.5)
    WM["rebar"] = V.m_flat("V3_Rebar", C("7A4A33"), .08, 10, .7, ao=.3)
    WM["lever"] = V.m_flat("V3_Lever", C("24272B"), .04, 6, .5, ao=.3)
    return WM


def cfg():
    """lots_v3's export / bake machinery, set up for these models: no city-tree square, our own small swatch row."""
    V.SWATCH = SWATCH_W
    V.TREE_BAND = 0.0
    V.RESERVED = V.SWATCH_CELL + .006
    V.EXPORT = EXPORT


# ------------------------------------------------------------------ geometry helpers
def side_frame(x):
    """Local (u, v) of a side profile -> world: u = distance towards the front (-Y), v = height; extruded along X,
    centred at x."""
    return Matrix(((0, 1, 0, x), (-1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))


def band(cl, half):
    """Closed outline of a strip around the centreline cl [(u, v)] with half-height half[i] (offset along the
    normals), for G.prism in a side frame."""
    top, bot = [], []
    n = len(cl)
    for i, (u, v) in enumerate(cl):
        a = Vector(cl[max(0, i - 1)]); b = Vector(cl[min(n - 1, i + 1)])
        d = (b - a).normalized(); nrm = Vector((-d.y, d.x))
        top.append(tuple(Vector((u, v)) + nrm * half[i])); bot.append(tuple(Vector((u, v)) - nrm * half[i]))
    return bot + list(reversed(top))


def pin(g, p, r, w, verts=12):
    """A pin / boss along X through point p."""
    g.cyl(r, w, tuple(p), rot=(0, math.pi / 2, 0), verts=verts)


def ram(gb, gr, a, b, rb, rr, frac=.58, eye=None):
    """Hydraulic ram from a (barrel end) to b (rod end): barrel, gland ring, chrome rod, eyes."""
    a, b = Vector(a), Vector(b); m = a + (b - a) * frac
    gb.tube(a, m, rb, verts=10)
    gb.tube(m - (b - a).normalized() * .04, m + (b - a).normalized() * .03, rb * 1.18, verts=10)
    gr.tube(m, b, rr, verts=8)
    if eye is not None:
        for q in (a, b): pin(eye, q, rb * .9, rb * 1.6, verts=8)


def track_loop(g, gx, y0, y1, r, zc, w, pitch=.2, plate_t=.055, grouser=.045, rubber=False):
    """A crawler track around a stadium path (two rounds of radius r centred at (y0, zc) and (y1, zc)), along Y at
    x = gx, w wide: plates with a grouser bar each (rubber: tread lugs)."""
    straight = y1 - y0; L = 2 * straight + 2 * math.pi * r
    n = int(L / pitch); step = L / n
    for i in range(n):
        s_ = i * step
        if s_ < straight:                                  # bottom run, front -> back
            p = Vector((gx, y0 + s_, zc - r)); ang = 0.0
        elif s_ < straight + math.pi * r:                  # round the back
            a = (s_ - straight) / r; p = Vector((gx, y1 + math.sin(a) * r, zc - math.cos(a) * r)); ang = a
        elif s_ < 2 * straight + math.pi * r:              # top run, back -> front
            p = Vector((gx, y1 - (s_ - straight - math.pi * r), zc + r)); ang = math.pi
        else:
            a = (s_ - 2 * straight - math.pi * r) / r; p = Vector((gx, y0 - math.sin(a) * r, zc + math.cos(a) * r)); ang = math.pi + a
        Mp = Matrix.Translation(p) @ Matrix.Rotation(ang, 4, 'X')       # local -Z = outward normal of the loop
        g.box((w, step - .02, plate_t), (0, 0, -plate_t / 2), M=Mp)
        if rubber:
            for sx in (-1, 1): g.box((w * .4, .07, grouser), (sx * w * .24, 0, -plate_t - grouser / 2 + .01), rot=(0, 0, sx * .25), M=Mp)
        else:
            g.box((w, .045, grouser), (0, 0, -plate_t - grouser / 2 + .01), M=Mp)


def wheel_x(g, c, r, w, verts=16):
    g.cyl(r, w, tuple(c), rot=(0, math.pi / 2, 0), verts=verts)


# ###################################################################################################################
# Works_Dumpster (skip): Body (root) + Fill (child, pivot (0, 0, .23)). CheckoutSkipLoad reads the Body's bounds
# (rim = top, inside = 74 % of the footprint) and hides Fill; CheckoutEraWorks grows Fill from its pivot.
# Current: 2.1 x 3.7 x 1.37 m, long side along Y.
# ###################################################################################################################
DUMP = "W1 Works_Dumpster"
DUMP_GROUPS = [("DUMP_Body", ("DUMP_Body",)), ("DUMP_Fill", ("DUMP_Fill",))]
DUMP_PARTS = {"DUMP_Body": "Body", "DUMP_Fill": "Fill"}


def build_dumpster():
    c = col(DUMP); show_only(DUMP)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    rnd = random.Random(3)
    H, T = 1.37, .06                               # rim height, wall
    xb, xt = .9, .95                              # half width at the floor / at the rim
    yb, yt = 1.28, 1.80                            # half length at the floor / at the rim
    zf = .13                                       # floor level (on the runners)
    sh = G("DUMP_Body_shell", WM["skip"], c, bevel=.012, seg=1, smooth=False)
    # side walls (trapezoids in the Y-Z plane), slightly leaning out
    for sx in (-1, 1):
        sh.prism([(-yb, zf), (yb, zf), (yt, H - .06), (-yt, H - .06)], T, M=Matrix.Translation((sx * (xb + xt) / 2, 0, 0)) @ Matrix(((0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))))
    # sloped end walls
    ang = math.atan2(yt - yb, H - zf); Lend = math.hypot(yt - yb, H - zf)
    for sy in (-1, 1):
        Me = Matrix.Translation((0, sy * (yb + yt) / 2, (zf + H - .06) / 2)) @ Matrix.Rotation(-sy * ang, 4, 'X')
        sh.box((2 * xb + .06, T, Lend - .04), (0, 0, 0), M=Me)
    sh.box((2 * xb, 2 * yb, T), (0, 0, zf + T / 2))
    sh.done()
    ins = G("DUMP_Body_inside", WM["skipIn"], c, smooth=False)
    for sx in (-1, 1):
        ins.prism([(-yb + .05, zf + T), (yb - .05, zf + T), (yt - .07, H - .08), (-yt + .07, H - .08)], .01, M=Matrix.Translation((sx * (xb + xt) / 2 - sx * (T / 2 + .006), 0, 0)) @ Matrix(((0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))))
    for sy in (-1, 1):
        Me = Matrix.Translation((0, sy * ((yb + yt) / 2 - (T / 2 + .006) / math.cos(ang)), (zf + H - .06) / 2)) @ Matrix.Rotation(-sy * ang, 4, 'X')
        ins.box((2 * xb - .04, .01, Lend - .1), (0, 0, 0), M=Me)
    ins.box((2 * xb - .04, 2 * yb - .04, .01), (0, 0, zf + T + .005))
    ins.done()
    # top rim: a rounded channel all round
    rim = G("DUMP_Body_rim", WM["skip"], c, bevel=.025, seg=1)
    for sx in (-1, 1): rim.box((.12, 2 * yt + .1, .11), (sx * (xt + .02), 0, H - .055))
    for sy in (-1, 1): rim.box((2 * xt + .16, .12, .11), (0, sy * (yt + .02), H - .055))
    rim.done()
    # ribs: vertical on the sides, sloped on the ends; floor runners and cross-members
    rb = G("DUMP_Body_ribs", WM["skip"], c, bevel=.012, seg=1)
    for sx in (-1, 1):
        for y in (-.62, 0, .62):
            rb.box((.07, .1, H - zf - .12), (sx * ((xb + xt) / 2 + .05), y, (zf + H - .1) / 2), rot=(0, -sx * math.atan2(xt - xb, H - zf), 0))
        rb.box((.07, 2 * yb + .2, .1), (sx * (xb + .06), 0, zf + .1))
    for sy in (-1, 1):
        for x in (-.5, .5):
            Me = Matrix.Translation((x, sy * ((yb + yt) / 2 + .05 / math.cos(ang)), (zf + H - .06) / 2)) @ Matrix.Rotation(-sy * ang, 4, 'X')
            rb.box((.1, .07, Lend - .14), (0, 0, 0), M=Me)
    rb.done()
    ru = G("DUMP_Body_runners", WM["grey"], c, bevel=.01, seg=1)
    for x in (-.62, .62): ru.box((.16, 2 * yb + .1, zf), (x, 0, zf / 2), open_bottom=True)
    for y in (-.9, 0, .9): ru.box((1.42, .1, .07), (0, y, zf - .04))
    ru.done()
    # lifting pins (trunnions) on the sides near the ends + their gusset plates
    lp = G("DUMP_Body_lugs", WM["grey"], c, bevel=.008, seg=1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            y = sy * 1.12; xw = (xb + xt) / 2 + .06
            lp.box((.05, .3, .34), (sx * xw, y, .95), rot=(0, -sx * math.atan2(xt - xb, H - zf), 0))
            lp.cyl(.06, .12, (sx * (xw + .06), y, .97), rot=(0, math.pi / 2, 0), verts=10)
            lp.cyl(.09, .03, (sx * (xw + .12), y, .97), rot=(0, math.pi / 2, 0), verts=10)
    lp.done()
    # hazard plates on both sloped ends (diagonal stripes, no text)
    hz = G("DUMP_Body_hazard", WM["hazard"], c, bevel=.005, seg=1)
    for sy in (-1, 1):
        for x in (-.74, .74):
            zz = H - .34; yw = yb + (zz - zf) / (H - .06 - zf) * (yt - yb)
            Me = Matrix.Translation((x, sy * (yw + .045 / math.cos(ang)), zz)) @ Matrix.Rotation(-sy * ang, 4, 'X')
            hz.box((.34, .02, .3), (0, 0, 0), M=Me)
    hz.done()
    # ---- Fill: rubble heaped on the floor (concrete chunks, bricks, a plank, bent rebar), under the rim
    fl = G("DUMP_Fill_slabs", WM["slab"], c, bevel=.02, seg=1)
    for k in range(16):
        x = rnd.uniform(-.65, .65); y = rnd.uniform(-1.15, 1.15)
        hgt = .55 + .35 * (1 - (abs(y) / 1.3) ** 2) * (1 - (abs(x) / .8) ** 2)
        sx_, sy_, sz_ = rnd.uniform(.3, .6), rnd.uniform(.25, .5), rnd.uniform(.12, .22)
        fl.box((sx_, sy_, sz_), (x, y, zf + .05 + rnd.uniform(.25, 1) * (hgt - .1)), rot=(rnd.uniform(-.5, .5), rnd.uniform(-.5, .5), rnd.uniform(0, 3)))
    fl.done()
    mound = G("DUMP_Fill_mound", WM["slab"], c)
    mound.ball(1.0, (0, 0, zf + .1), scale=(.78, 1.35, .58), sub=2); mound.clip = zf + T + .01
    mound.done()
    bk = G("DUMP_Fill_bricks", WM["brick"], c, bevel=.008, seg=1)
    for k in range(10):
        bk.box((.22, .11, .07), (rnd.uniform(-.55, .55), rnd.uniform(-1.0, 1.0), zf + rnd.uniform(.45, .8)), rot=(rnd.uniform(-.6, .6), rnd.uniform(-.6, .6), rnd.uniform(0, 3)))
    bk.done()
    pl = G("DUMP_Fill_plank", M["wood"], c, bevel=.01, seg=1)
    pl.box((.16, 1.7, .04), (.2, -.1, zf + .78), rot=(.18, -.12, .35))
    pl.box((.12, 1.1, .04), (-.35, .5, zf + .7), rot=(-.1, .2, -.5))
    pl.done()
    rr = G("DUMP_Fill_rebar", WM["rebar"], c)
    for (a, b) in (((-.2, -.7, .7), (-.05, -.35, 1.12)), ((-.05, -.35, 1.12), (.25, -.3, 1.05)), ((.4, .7, .75), (.55, .95, 1.08))):
        rr.tube(Vector(a) + Vector((0, 0, zf)), Vector(b) + Vector((0, 0, zf)), .016, verts=4)
    rr.done()
    return V.stats(c)



# ###################################################################################################################
# Works_Excavator / Works_MiniExcavator: Body (root: undercarriage) > Cab (slew, turns about world up) > Boom >
# Arm > Bucket (each turned about the cab's right axis at its own origin by CheckoutWorks.Digger). Imported frame:
# front -Y, boom on the -X side, operator on the +X side. In side profiles u = -y (towards the front), v = z.
# ###################################################################################################################
EXC = "W1 Works_Excavator"
MINI = "W1 Works_MiniExcavator"
EXC_PARTS = {"EXC_Body": "Body", "EXC_Cab": "Cab", "EXC_Boom": "Boom", "EXC_Arm": "Arm", "EXC_Bucket": "Bucket"}
MINI_PARTS = {"MINI_Body": "Body", "MINI_Cab": "Cab", "MINI_Boom": "Boom", "MINI_Arm": "Arm", "MINI_Bucket": "Bucket"}
EXC_GROUPS = [(g, (g,)) for g in EXC_PARTS]
MINI_GROUPS = [(g, (g,)) for g in MINI_PARTS]

BIG = dict(
    paint="yellow", low="yellowLow", accent="teal", k=1.0,
    cab_z=1.045, bx=-.57, boom=(.855, 1.9), arm=(3.135, 3.61), bkt=(4.18, 1.425),
    gx=1.6, tw=.68, ty=(-1.45, 1.45), tr=.38, tz=.46, rubber=False, pitch=.2,
    car=(1.3, .75, .4, .88), ring=.95,
    deck=(-1.4, 1.45, -1.5, 1.6, 1.06, 1.36), cwt=(1.38, 2.15, 2.2), hood=(.05, 1.45, 2.15),
    cab=(.3, 1.42, -1.5, -.1, 3.0), canopy=False, box=(-1.35, -.95, -1.45, -.1, 2.0),
    foot=[(.32, 1.36), (1.3, 1.36), (1.08, 1.98), (.62, 2.04)], foot_dx=.27,
    boom_cl=[(.855, 1.9), (1.35, 2.85), (1.95, 3.72), (2.6, 3.93), (3.135, 3.61)], boom_h=[.2, .26, .3, .26, .19], boom_w=.44,
    arm_cl=[(2.86, 4.02), (3.135, 3.61), (3.7, 2.5), (4.18, 1.425)], arm_h=[.17, .22, .18, .13], arm_w=.36,
    bkt_prof=[(4.06, 1.74), (4.3, 1.42), (4.33, 1.06), (4.2, .8), (3.92, .7), (3.5, .72), (3.0, .86)], bkt_w=1.1,
    boom_ram=((1.22, 1.5), (1.92, 3.38), .09, .055, .29), arm_ram=((1.72, 4.13), (2.86, 4.18), .085, .05),
    bkt_ram=((3.05, 3.98), (3.98, 1.98), .075, .045),
)
SMALL = dict(
    paint="orange", low="orange", accent="teal", k=.5,
    cab_z=.55, bx=-.3, boom=(.45, 1.0), arm=(1.65, 1.9), bkt=(2.2, .75),
    gx=.6, tw=.3, ty=(-.68, .68), tr=.2, tz=.27, rubber=True, pitch=.13,
    car=(.45, .45, .2, .45), ring=.45,
    deck=(-.66, .7, -.62, .8, .56, .74), cwt=(.62, 1.16, 1.2), hood=(.02, .9, 1.18),
    cab=(0.0, .9, -.8, .3, 2.06), canopy=False, box=None,
    foot=[(.14, .74), (.66, .74), (.56, 1.04), (.34, 1.08)], foot_dx=.13,
    boom_cl=[(.45, 1.0), (.7, 1.52), (1.05, 1.98), (1.4, 2.08), (1.65, 1.9)], boom_h=[.1, .13, .14, .12, .1], boom_w=.2,
    arm_cl=[(1.5, 2.12), (1.65, 1.9), (1.95, 1.3), (2.2, .75)], arm_h=[.09, .11, .09, .07], arm_w=.17,
    bkt_prof=[(2.12, .95), (2.27, .8), (2.29, .56), (2.2, .43), (2.03, .38), (1.8, .39), (1.5, .47)], bkt_w=.58,
    boom_ram=((.66, .78), (1.0, 1.72), .05, .03, .14), arm_ram=((.9, 2.18), (1.5, 2.2), .045, .028),
    bkt_ram=((1.6, 2.15), (2.06, 1.06), .04, .025),
)


def U(u, z, x=0.0):
    """Side-profile point (u forwards, z up) at lateral x -> world."""
    return Vector((x, -u, z))


def excavator(cname, pre, P):
    c = col(cname); show_only(cname)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    k = P["k"]; paint, low, acc = WM[P["paint"]], WM[P["low"]], WM[P["accent"]]
    bx = P["bx"]
    # ---------------------------------------------------------------- Body: undercarriage
    B = pre + "_Body"
    tr = G(B + "_track", OM["rubber"] if P["rubber"] else WM["steel"], c, smooth=False)
    fr = G(B + "_frame", WM["frame"], c, bevel=.03 * k, seg=1)
    rl = G(B + "_rollers", WM["frame"], c)
    for sx in (-1, 1):
        gx = sx * P["gx"]
        track_loop(tr, gx, P["ty"][0], P["ty"][1], P["tr"], P["tz"], P["tw"], pitch=P["pitch"],
                   plate_t=.055 * k if not P["rubber"] else .04, grouser=.045 * k if not P["rubber"] else .03, rubber=P["rubber"])
        fr.box((P["tw"] * .62, (P["ty"][1] - P["ty"][0]) * .86, P["tr"] * 1.15), (gx, 0, P["tz"] + .02 * k))
        wheel_x(rl, (gx, P["ty"][0], P["tz"]), P["tr"] * .86, P["tw"] * .7, verts=18)             # idler (front)
        wheel_x(rl, (gx, P["ty"][1], P["tz"]), P["tr"] * .84, P["tw"] * .7, verts=18)             # sprocket (back)
        for t_ in range(12):
            a = 2 * math.pi * t_ / 12
            rl.box((P["tw"] * .5, .07 * k, .07 * k), (gx, P["ty"][1] + math.sin(a) * P["tr"] * .9, P["tz"] + math.cos(a) * P["tr"] * .9), rot=(-a, 0, 0))
        wheel_x(rl, (gx + sx * P["tw"] * .37, P["ty"][1], P["tz"]), P["tr"] * .45, .05 * k, verts=12)          # final drive hub
        n_r = 5 if not P["rubber"] else 3
        for i in range(n_r):
            y = P["ty"][0] * .75 + (P["ty"][1] - P["ty"][0]) * .75 * i / (n_r - 1)
            wheel_x(rl, (gx, y, P["tz"] - P["tr"] + .1 * k), .1 * k, P["tw"] * .55, verts=10)
        for y in (P["ty"][0] * .4, P["ty"][1] * .4):
            wheel_x(rl, (gx, y, P["tz"] + P["tr"] - .05 * k), .07 * k, P["tw"] * .4, verts=10)
        fr.box((.06 * k, (P["ty"][1] - P["ty"][0]) * .5, .05 * k), (gx + sx * P["tw"] * .36, 0, P["tz"] + P["tr"] * .3))   # step
    hx, hy, cz0, cz1 = P["car"]
    fr.box((2 * hx, 2 * hy, cz1 - cz0), (0, 0, (cz0 + cz1) / 2))
    fr.box((2 * P["gx"] - P["tw"] * .4, hy * .9, (cz1 - cz0) * .55), (0, 0, (cz0 + cz1) / 2 - (cz1 - cz0) * .1))   # cross beam
    tr.done(); fr.done(); rl.done()
    sr = G(B + "_ring", WM["grey"], c, bevel=.01 * k, seg=1)
    sr.cyl(P["ring"], P["cab_z"] - cz1 - .01, (0, 0, (cz1 + P["cab_z"]) / 2), verts=28)
    sr.done()
    if P["rubber"]:      # mini: dozer blade at the front (one curved plate), its two push arms and the lift ram
        bl = G(B + "_blade", paint, c, bevel=.015, seg=1)
        prof = [(1.13, .03), (1.075, .12), (1.06, .22), (1.075, .32), (1.13, .4), (1.07, .43), (1.0, .33), (.985, .22),
                (1.0, .1), (1.05, .02)]
        bl.prism(prof, 1.56, M=side_frame(0))
        for sx in (-1, 1):
            bl.prism(band([(.36, .33), (1.0, .2)], [.05, .05]), .08, M=side_frame(sx * .4))
            bl.box((.06, .1, .38), U(1.03, .22, sx * .8))
        bl.done()
        be = G(B + "_bladeEdge", WM["grey"], c, bevel=.006, seg=1)
        be.box((1.58, .07, .045), U(1.11, .035))
        be.done()
        rb, rr = G(B + "_bladeRam", paint, c), G(B + "_bladeRod", OM["chrome"], c)
        ram(rb, rr, U(.42, .46), U(.99, .34), .04, .024)
        rb.done(); rr.done()
    # ---------------------------------------------------------------- Cab: the upper structure (slews)
    Cn = pre + "_Cab"
    x0, x1, y0, y1, z0, z1 = P["deck"]
    dk = G(Cn + "_deck", WM[P["paint"]], c, bevel=.05 * k, seg=1)
    dk.box((x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    dk.done()
    cw0, cw1, cwz = P["cwt"]
    cw = G(Cn + "_cwt", paint, c, bevel=.22 * k, seg=3)
    cw.box((x1 - x0, cw1 - cw0, cwz - z0), ((x0 + x1) / 2, (cw0 + cw1) / 2, (z0 + cwz) / 2))
    cw.done()
    hz = G(Cn + "_hazard", WM["hazard"], c, bevel=.006, seg=1)
    hz.box(((x1 - x0) * .55, .02, (cwz - z0) * .26), ((x0 + x1) / 2, cw1 + .005, z0 + (cwz - z0) * .45))
    hz.done()
    h0, h1, hz1 = P["hood"]
    hd = G(Cn + "_hood", paint, c, bevel=.08 * k, seg=2)
    hd.box((x1 - x0 - .06, h1 - h0, hz1 - z1), ((x0 + x1) / 2, (h0 + h1) / 2, (z1 + hz1) / 2))
    hd.done()
    lv = G(Cn + "_louvres", M["dark"], c)
    for sx in (-1, 1):
        for i in range(5):
            lv.box((.02, (h1 - h0) * .5, .035 * k), (sx * ((x1 - x0) / 2 + .0) + (x0 + x1) / 2, (h0 + h1) / 2 + (h1 - h0) * .1, z1 + (hz1 - z1) * (.3 + .1 * i)), rot=(.35, 0, 0))
    lv.done()
    ex = G(Cn + "_exhaust", WM["grey"], c)
    ex.tube((x1 - .45 * k, h0 + (h1 - h0) * .55, hz1 - .02), (x1 - .45 * k, h0 + (h1 - h0) * .55, hz1 + .45 * k), .05 * k, verts=10)
    ex.cyl(.075 * k, .03 * k, (x1 - .45 * k, h0 + (h1 - h0) * .55, hz1 + .46 * k), rot=(.4, 0, 0), verts=10)
    ex.cyl(.12 * k, .22 * k, (x0 + .45 * k, h0 + (h1 - h0) * .35, hz1 + .1 * k), verts=14)      # air filter
    ex.done()
    rail = G(Cn + "_rails", acc, c)
    for xr in (x0 + .12 * k, x1 - .12 * k):
        ya, yb = h0 + .12 * k, h1 - .1 * k
        rail.tube((xr, ya, hz1 + .3 * k), (xr, yb, hz1 + .3 * k), .022 * k, verts=6)
        for y in (ya, (ya + yb) / 2, yb): rail.tube((xr, y, hz1 - .02), (xr, y, hz1 + .3 * k), .02 * k, verts=6)
    rail.done()
    if P["box"]:
        bxx0, bxx1, by0, by1, bz1 = P["box"]
        tb = G(Cn + "_toolbox", paint, c, bevel=.05 * k, seg=1)
        tb.box((bxx1 - bxx0, by1 - by0, bz1 - z1), ((bxx0 + bxx1) / 2, (by0 + by1) / 2, (z1 + bz1) / 2))
        tb.done()
        cap = G(Cn + "_tankCap", M["dark"], c)
        cap.cyl(.07, .06, ((bxx0 + bxx1) / 2, by0 + .3, bz1 + .02), verts=10)
        cap.box((.04, (by1 - by0) * .6, .03), (bxx1 + .01, (by0 + by1) / 2, bz1 - .15))
        cap.done()
    # boom foot: two plates up to the boom pin
    ft = G(Cn + "_foot", paint, c, bevel=.02 * k, seg=1)
    for sx in (-1, 1):
        ft.prism(P["foot"], .06 * k, M=side_frame(bx + sx * P["foot_dx"]))
    ft.done()
    # operator: a glazed cab (big) or a ROPS canopy (mini)
    cx0, cx1, cy0, cy1, cz1 = P["cab"]
    pil = G(Cn + "_pillars", WM["grey"], c, bevel=.012 * k, seg=1)
    gl = G(Cn + "_glass", M["glass"], c)
    zl = z1 + (cz1 - z1) * (.0 if P["canopy"] else .28)
    if not P["canopy"]:
        lo = G(Cn + "_cabLow", paint, c, bevel=.04 * k, seg=1)
        lo.box((cx1 - cx0, cy1 - cy0, zl - z1), ((cx0 + cx1) / 2, (cy0 + cy1) / 2, (z1 + zl) / 2))
        lo.done()
        for (px, py) in ((cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1), (cx1, (cy0 + cy1) / 2 - .1)):
            pil.box((.08, .08, cz1 - zl), (px + (.04 if px == cx0 else -.04), py + (.04 if py == cy0 else (-.04 if py == cy1 else 0)), (zl + cz1) / 2))
        ins = .03
        gl.box((cx1 - cx0 - .14, .02, cz1 - zl - .08), ((cx0 + cx1) / 2, cy0 + ins, (zl + cz1) / 2))           # front
        gl.box((cx1 - cx0 - .14, .02, cz1 - zl - .08), ((cx0 + cx1) / 2, cy1 - ins, (zl + cz1) / 2))           # back
        for xx in (cx0 + ins, cx1 - ins): gl.box((.02, cy1 - cy0 - .14, cz1 - zl - .08), (xx, (cy0 + cy1) / 2, (zl + cz1) / 2))
        pil.box((.03, .03, (cz1 - zl) * .55), ((cx0 + cx1) / 2 + .1, cy0 + .005, zl + (cz1 - zl) * .5), rot=(0, .5, 0))   # wiper
        pil.box((.04, .12, .03), (cx1 + .005, (cy0 + cy1) / 2 + .15, zl + .1))                                          # door handle
        pil.box((cx1 - cx0 + .06, .05, .06), ((cx0 + cx1) / 2, cy0, zl))                                             # sill bar
    else:
        for (px, py) in ((cx0 + .05, cy0 + .05), (cx1 - .05, cy0 + .05), (cx1 - .05, cy1 - .05), (cx0 + .05, cy1 - .05)):
            pil.box((.06, .06, cz1 - z1), (px, py, (z1 + cz1) / 2))
        pil.box((.05, cy1 - cy0 - .1, .05), (cx1 - .05, (cy0 + cy1) / 2, z1 + (cz1 - z1) * .45))
        pil.box((.05, cy1 - cy0 - .1, .05), (cx0 + .05, (cy0 + cy1) / 2, z1 + (cz1 - z1) * .45))
    pil.done(); gl.done()
    rf = G(Cn + "_roof", acc, c, bevel=.03 * k, seg=1)
    rf.box((cx1 - cx0 + .1 * k, cy1 - cy0 + .1 * k, .1 * k), ((cx0 + cx1) / 2, (cy0 + cy1) / 2, cz1 + .05 * k))
    rf.done()
    fl = G(Cn + "_floor", WM["grey"], c)
    fl.box((cx1 - cx0 - .1, cy1 - cy0 - .1, .02), ((cx0 + cx1) / 2, (cy0 + cy1) / 2, z1 + .01))
    fl.done()
    st = G(Cn + "_seat", OM["seat"], c, bevel=.03 * k, seg=1)
    sxc, syc = (cx0 + cx1) / 2, (cy0 + cy1) / 2 + (cy1 - cy0) * .12
    st.box((.45 * k + .1, .45 * k + .1, .14 * k), (sxc, syc, z1 + .42 * k + .1))
    st.box((.45 * k + .1, .12 * k, .55 * k + .05), (sxc, syc + .25 * k + .04, z1 + .78 * k + .1), rot=(-.15, 0, 0))
    st.box((.16 * k, .16 * k, .32 * k + .05), (sxc, syc, z1 + .22 * k))
    st.done()
    lvr = G(Cn + "_levers", WM["lever"], c)
    for sx in (-1, 1):
        lvr.box((.1 * k, .25 * k, .2 * k), (sxc + sx * (.32 * k + .07), syc - .05, z1 + .45 * k))
        lvr.tube((sxc + sx * (.32 * k + .07), syc - .15 * k, z1 + .55 * k), (sxc + sx * (.32 * k + .07), syc - .22 * k, z1 + .78 * k), .02 * k + .005, verts=6)
        lvr.ball(.035 * k + .01, (sxc + sx * (.32 * k + .07), syc - .22 * k, z1 + .8 * k), sub=1)
    lvr.tube((sxc - .12 * k, cy0 + .15 * k, z1 + .1), (sxc - .12 * k, cy0 + .3 * k, z1 + .55 * k), .02 * k + .005, verts=6)   # travel levers
    lvr.tube((sxc + .12 * k, cy0 + .15 * k, z1 + .1), (sxc + .12 * k, cy0 + .3 * k, z1 + .55 * k), .02 * k + .005, verts=6)
    lvr.done()
    bc = G(Cn + "_beacon", M["dark"], c)
    bc.cyl(.07 * k + .02, .05 * k, (cx0 + .2 * k, cy1 - .2 * k, cz1 + .12 * k), verts=12)
    bc.done()
    bo = G(Cn + "_beaconDome", M["fruit"], c)
    bo.ball(.065 * k + .02, (cx0 + .2 * k, cy1 - .2 * k, cz1 + .17 * k), scale=(1, 1, 1.15), sub=2)
    bo.done()
    wl = G(Cn + "_lights", OM["headlight"], c, bevel=.01, seg=1)
    for xx in (cx0 + .2 * k, cx1 - .2 * k): wl.box((.14 * k, .06 * k, .1 * k), (xx, cy0 - .04 * k, cz1 + .02 * k))
    wl.done()
    mr = G(Cn + "_mirrors", M["dark"], c)
    for (xx, sxm) in ((cx1, 1), (cx0, -1)):
        if P["canopy"] and sxm < 0: continue
        mr.tube((xx, cy0 + .1, zl + .2 * k), (xx + sxm * .2 * k, cy0 - .05, zl + .35 * k), .015 * k + .004, verts=4)
        mr.box((.04 * k + .01, .12 * k + .02, .2 * k + .02), (xx + sxm * .22 * k, cy0 - .06, zl + .42 * k), rot=(0, 0, sxm * .3))
    mr.done()
    # ---------------------------------------------------------------- Boom
    Bm = pre + "_Boom"
    bm = G(Bm + "_main", low, c, bevel=.04 * k, seg=1)
    bm.prism(band(P["boom_cl"], P["boom_h"]), P["boom_w"], M=side_frame(bx))
    bm.done()
    pins = G(Bm + "_pins", WM["grey"], c, bevel=.008, seg=1)
    pin(pins, U(*P["boom"], bx), .09 * k + .01, P["boom_w"] + 2 * P["foot_dx"] - .1 * k, verts=14)
    pin(pins, U(*P["arm"], bx), .08 * k + .01, P["boom_w"] + .1 * k, verts=14)
    pins.done()
    hs = G(Bm + "_hoses", M["dark"], c)
    for sx in (-1, 1):
        cl = P["boom_cl"]
        pts = [U(u, z + .02 * k, bx + sx * (P["boom_w"] / 2 + .025 * k)) for (u, z) in cl[1:]]
        for a_, b_ in zip(pts, pts[1:]): hs.tube(a_, b_, .022 * k + .004, verts=6)
    hs.done()
    (ua, za), (ub, zb), rb_, rr_, dx = P["boom_ram"]
    br, brr = G(Bm + "_ram", low, c), G(Bm + "_rod", OM["chrome"], c)
    bk = G(Bm + "_ramPins", WM["grey"], c)
    for sx in (-1, 1):
        ram(br, brr, U(ua, za, bx + sx * dx), U(ub, zb, bx + sx * dx), rb_, rr_, eye=bk)
    (ua, za), (ub, zb), rb_, rr_ = P["arm_ram"]
    ram(br, brr, U(ua, za, bx), U(ub, zb, bx), rb_, rr_, eye=bk)
    br.done(); brr.done(); bk.done()
    bt = G(Bm + "_brackets", low, c, bevel=.01, seg=1)
    (ub, zb) = P["boom_ram"][1]
    bt.box((P["boom_w"] + 2 * dx, .12 * k, .25 * k), U(ub, zb + .1 * k, bx))                     # ram rod lugs under the boom
    (ua, za) = P["arm_ram"][0]
    bt.box((.12 * k + .05, .25 * k, .3 * k), U(ua, za - .12 * k, bx))                            # arm ram base on top
    bt.done()
    if k == 1.0:
        lt = G(Bm + "_lights", OM["headlight"], c, bevel=.008, seg=1)
        for sx in (-1, 1): lt.box((.06, .14, .1), U(1.5, 3.05, bx + sx * (P["boom_w"] / 2 + .04)))
        lt.done()
    # ---------------------------------------------------------------- Arm
    Am = pre + "_Arm"
    am = G(Am + "_main", low, c, bevel=.035 * k, seg=1)
    am.prism(band(P["arm_cl"], P["arm_h"]), P["arm_w"], M=side_frame(bx))
    am.done()
    ap = G(Am + "_pins", WM["grey"], c, bevel=.006, seg=1)
    pin(ap, U(*P["arm_cl"][0], bx), .07 * k + .01, P["arm_w"] + .08 * k, verts=12)               # heel (arm ram eye)
    (ua, za), (ub, zb), rb_, rr_ = P["bkt_ram"]
    ar, arr = G(Am + "_ram", low, c), G(Am + "_rod", OM["chrome"], c)
    ram(ar, arr, U(ua, za, bx), U(ub, zb, bx), rb_, rr_, eye=ap)
    ar.done(); arr.done()
    lk = G(Am + "_links", WM["grey"], c, bevel=.008, seg=1)
    bu, bz = P["bkt"]
    for sx in (-1, 1):
        lk.tube(U(ub, zb, bx + sx * .1 * k), U(bu - .25 * k, bz + .35 * k, bx + sx * .1 * k), .035 * k + .005, verts=6)     # dogbone to the arm
        lk.tube(U(ub, zb, bx + sx * .13 * k), U(bu - .02 * k, bz + .42 * k, bx + sx * .13 * k), .03 * k + .005, verts=6)     # H-link to the bucket ear
    ap.done(); lk.done()
    # ---------------------------------------------------------------- Bucket
    Bk = pre + "_Bucket"
    w = P["bkt_w"]; prof = P["bkt_prof"]
    sp = G(Bk + "_sides", low, c, bevel=.015 * k, seg=1)
    for sx in (-1, 1): sp.prism(prof, .05 * k, M=side_frame(bx + sx * (w / 2 - .02 * k)))
    sp.done()
    sh = G(Bk + "_shell", low, c, bevel=.01, seg=1)
    back = prof[1:]
    for (u0, z0_), (u1_, z1_) in zip(back, back[1:]):
        a_, b_ = Vector((u0, z0_)), Vector((u1_, z1_)); d = b_ - a_; m = (a_ + b_) / 2
        sh.box((w - .02, d.length + .02, .05 * k), (0, 0, 0), M=Matrix.Translation(U(m.x, m.y, bx)) @ Matrix.Rotation(math.atan2(d.y, -d.x), 4, 'X'))
    sh.done()
    ed = G(Bk + "_edge", WM["grey"], c, bevel=.008, seg=1)
    lu, lz = prof[-1]; pu, pz = prof[-2]
    d = Vector((lu - pu, lz - pz)).normalized()
    Me = Matrix.Translation(U(lu, lz, bx)) @ Matrix.Rotation(math.atan2(d.y, -d.x), 4, 'X')
    ed.box((w + .02, .12 * k, .07 * k), (0, -.02 * k, 0), M=Me)
    nt = 5 if w > .8 else 4
    for i in range(nt):
        xx = -w / 2 + .1 * k + (w - .2 * k) * i / (nt - 1)
        ed.box((.09 * k, .2 * k, .06 * k), (xx, .14 * k, 0), M=Me)
        ed.box((.06 * k, .08 * k, .04 * k), (xx, .27 * k, 0), M=Me)
    ears_u, ears_z = P["bkt"]
    for sx in (-1, 1):
        ed.box((.04 * k, .3 * k, .38 * k), U(ears_u - .06 * k, ears_z + .12 * k, bx + sx * (P["arm_w"] / 2 + .04 * k)))
    pin(ed, U(*P["bkt"], bx), .07 * k + .008, P["arm_w"] + .2 * k, verts=12)
    ed.done()
    return V.stats(c)


def build_excavator(): return excavator(EXC, "EXC", BIG)


def build_mini(): return excavator(MINI, "MINI", SMALL)



# ###################################################################################################################
# batch 2: Works_Pickup, Works_TowTruck, Works_WreckingCrane
# ###################################################################################################################
def arc(cu, cz, r, z_cut, n=7, rev=False):
    """Points of a wheel-arch arc (centre (cu, cz), radius r) above the line z = z_cut, from front to back."""
    t0 = math.asin(max(-1, min(1, (z_cut - cz) / r)))
    ts = [t0 + (math.pi - 2 * t0) * i / n for i in range(n + 1)]
    pts = [(cu + r * math.cos(t), cz + r * math.sin(t)) for t in ts]       # front (u big) -> back
    return list(reversed(pts)) if rev else pts


def wheel(c, name, centre, outer, width, dual=False, lugs=5, rim_col=None):
    """A road wheel at `centre` (axis X): tread tyre (like the Oficina ones) + steel rim with hub and nuts.
    dual: two tyres side by side (truck rear axle)."""
    tg = G(name + "_tyre", OM["rubber"], c)
    rg = G(name + "_rim", rim_col or OM["rimSteel"], c)
    r = width * .42 if not dual else width * .22
    R = outer - r
    xs = [0.0] if not dual else [-width * .25, width * .25]
    for dx in xs:
        Mw = Matrix.Translation(Vector(centre) + Vector((dx, 0, 0))) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
        tg.tyre(R=R - .01, r=r, w=(width / len(xs)) * .46, M=Mw, seg=30, rseg=8, worn=.3)
    sx = 1 if centre[0] > 0 else -1
    Mr = Matrix.Translation(Vector(centre) + Vector((sx * (width * .5 - .06 if dual else 0), 0, 0))) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
    rg.rim(R=R * .72, w=width * .3, M=Mr, lugs=lugs)
    tg.done(); rg.done()


def glass_side(g, poly, x, t=.012):
    g.prism(poly, t, M=side_frame(x))


def windscreen(c, name, a, b, w, out=.03, x=0.0, frame_mat=None, wipers=True):
    """A big front windscreen between side-profile points a (bottom) and b (top), w wide: glass pane set just
    proud of the cab face (offset `out` along the face normal), a dark rubber frame all round and two wipers."""
    A, B = Vector(a), Vector(b); d = B - A; L = d.length
    n = Vector((d.y, -d.x)).normalized()                         # outward (forwards / up) in the (u, z) profile
    ca, cb = A + n * out, B + n * out
    P0, P1 = U(*ca, x), U(*cb, x); dw = P1 - P0
    Mp = Matrix.Translation((P0 + P1) / 2) @ Matrix.Rotation(math.atan2(dw.z, dw.y), 4, 'X')
    gl = G(name + "_windscreen", M["glass"], c)
    gl.box((w - .08, L - .08, .02), (0, 0, 0), M=Mp)
    gl.done()
    fr = G(name + "_wsFrame", frame_mat or M["dark"], c, bevel=.01, seg=1)
    for sy in (-1, 1): fr.box((w, .06, .05), (0, sy * (L / 2 - .03), .005), M=Mp)
    for sx in (-1, 1): fr.box((.06, L, .05), (sx * (w / 2 - .03), 0, .005), M=Mp)
    fr.done()
    if wipers:
        wp = G(name + "_wipers", M["dark"], c)
        for sx in (-1, 1):
            wp.box((.025, L * .5, .015), (sx * w * .22 - .05, -L / 2 + L * .27, .03), rot=(0, 0, -.35), M=Mp)
            wp.cyl(.025, .03, (sx * w * .22 - .05 + L * .085, -L / 2 + .06, .03), verts=8, M=Mp)
        wp.done()


def tilted_pane(g, a, b, w, t=.015, x=0.0):
    """A flat pane between side-profile points a and b (u, z), w wide across X."""
    A, B = U(*a, x), U(*b, x); d = B - A
    g.box((w, d.length, t), (0, 0, 0), M=Matrix.Translation((A + B) / 2) @ Matrix.Rotation(math.atan2(d.z, d.y), 4, 'X'))


# ---------------------------------------------------------------- Works_Pickup
PICK = "W1 Works_Pickup"
PICK_PARTS = {"PICK_Body": "Body", "PICK_Wheel_0": "Wheel_0", "PICK_Wheel_1": "Wheel_1", "PICK_Wheel_2": "Wheel_2", "PICK_Wheel_3": "Wheel_3"}
PICK_GROUPS = [(g, (g,)) for g in PICK_PARTS]


def build_pickup():
    """Work pickup (cream with an orange stripe): cab with glass, mirrors, beacon bar, a crossbed toolbox, a ladder
    on its rack, cement sacks and planks in the bed. Wheels at the current pivots: front u 1.55, rear u -1.5,
    x +-.8, centre z .37 (outer radius .36)."""
    c = col(PICK); show_only(PICK)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    rnd = random.Random(5)
    paint = WM["cream"]; W_ = 1.88
    fu, ru, wz, wr = 1.55, -1.5, .37, .47
    cab = [(-.45, .5)] + [(u, z) for (u, z) in reversed(arc(fu, wz, wr, .5))] + [(2.5, .5), (2.6, .6), (2.63, .86), (2.57, 1.05),
           (1.45, 1.13), (1.3, 1.17), (.78, 1.79), (-.3, 1.82), (-.42, 1.74), (-.45, 1.2)]
    b = G("PICK_Body_cab", paint, c, bevel=.05, seg=2)
    b.prism(cab, W_, M=side_frame(0))
    b.done()
    st = G("PICK_Body_stripe", WM["orange"], c)
    for sx in (-1, 1):
        st.prism([(-2.6, .86), (2.62, .86), (2.62, .96), (-2.6, .96)], .01, M=side_frame(sx * (W_ / 2 + .004)))
    st.done()
    # bed: floor, sides with the rear arch, front wall, tailgate, rail caps
    bd = G("PICK_Body_bed", paint, c, bevel=.025, seg=1)
    side = [(-.48, .5)] + [p for p in arc(ru, wz, wr, .5)] + [(-2.6, .5), (-2.62, 1.2), (-.48, 1.2)]
    for sx in (-1, 1): bd.prism(side, .08, M=side_frame(sx * (W_ / 2 - .04)))
    bd.box((W_ - .1, .08, .45), U(-.52, .99))
    bd.box((W_ - .1, .07, .5), U(-2.58, .95))
    bd.done()
    fl = G("PICK_Body_bedFloor", WM["grey"], c, bevel=.01, seg=1)
    fl.box((W_ - .14, 2.04, .05), U(-1.55, .76))
    for k in range(5): fl.box((.05, 2.0, .025), U(-1.55, .79, -.6 + .3 * k))
    fl.box((W_ - .1, .2, .14), U(-2.62, .52))                                        # rear bumper step
    for sx in (-1, 1): fl.box((.1, 2.12, .05), U(-1.54, 1.22, sx * (W_ / 2 - .04)))   # rail caps
    fl.done()
    # chassis, bumpers, grille, lights
    dk = G("PICK_Body_dark", M["dark"], c, bevel=.01, seg=1)
    for sx in (-1, 1): dk.box((.12, 4.4, .14), U(0, .45, sx * .45))
    dk.box((1.2, .05, .28), U(2.64, .9))                                             # grille
    for z in (.84, .92, .99): dk.box((1.16, .02, .02), U(2.665, z))
    for (u0, u1) in ((1.27, .45), (.4, -.38)):                                       # door seams
        for sx in (-1, 1): dk.box((.01, .012, .62), U(u0, .82, sx * (W_ / 2 + .004)))
    for sx in (-1, 1):
        dk.box((.03, .14, .04), U(.6, 1.05, sx * (W_ / 2 + .015)))                  # handles
        dk.box((.03, .12, .04), U(-.25, 1.05, sx * (W_ / 2 + .015)))
    dk.tube(U(-2.45, .42, .6), U(-2.72, .42, .6), .04, verts=8)                      # exhaust
    dk.done()
    bp = G("PICK_Body_bumpers", WM["grey"], c, bevel=.03, seg=1)
    bp.box((W_ + .06, .16, .22), U(2.68, .55))
    bp.box((W_ + .06, .16, .2), U(-2.68, .55))
    bp.done()
    ll = G("PICK_Body_head", OM["headlight"], c, bevel=.01, seg=1)
    for sx in (-1, 1): ll.box((.26, .04, .14), U(2.645, .93, sx * .74))
    ll.done()
    tl = G("PICK_Body_tail", OM["taillight"], c, bevel=.008, seg=1)
    for sx in (-1, 1): tl.box((.12, .04, .26), U(-2.635, 1.02, sx * .86))
    tl.done()
    ind = G("PICK_Body_ind", M["fruit"], c)
    for sx in (-1, 1): ind.box((.1, .04, .06), U(2.62, .78, sx * .82))
    ind.done()
    # glass
    gl = G("PICK_Body_glass", M["glass"], c)
    windscreen(c, "PICK_Body", (1.27, 1.22), (.8, 1.76), W_ - .16, out=.025)
    gl.box((W_ - .3, .015, .5), U(-.455, 1.5))
    for sx in (-1, 1):
        glass_side(gl, [(1.2, 1.2), (.8, 1.72), (.45, 1.72), (.45, 1.2)], sx * (W_ / 2 + .004))
        glass_side(gl, [(.38, 1.2), (.38, 1.72), (-.28, 1.72), (-.36, 1.2)], sx * (W_ / 2 + .004))
    gl.done()
    mr = G("PICK_Body_mirrors", M["dark"], c, bevel=.01, seg=1)
    for sx in (-1, 1):
        mr.tube(U(1.22, 1.2, sx * (W_ / 2)), U(1.2, 1.28, sx * (W_ / 2 + .15)), .015, verts=4)
        mr.box((.05, .1, .18), U(1.18, 1.32, sx * (W_ / 2 + .17)))
    mr.done()
    # beacon bar on the roof
    bb = G("PICK_Body_beaconBar", M["dark"], c, bevel=.01, seg=1)
    bb.box((1.2, .2, .06), U(.35, 1.86))
    bb.done()
    bo = G("PICK_Body_beacons", M["fruit"], c)
    for sx in (-1, 1): bo.ball(.09, U(.35, 1.92, sx * .45), scale=(1, 1, .8), sub=2)
    bo.box((.5, .16, .08), U(.35, 1.92))
    bo.done()
    # ladder rack over the bed, ladder, crossbed toolbox, sacks, planks
    rk = G("PICK_Body_rack", WM["grey"], c)
    for u in (-.62, -2.45):
        for sx in (-1, 1): rk.tube(U(u, 1.2, sx * (W_ / 2 - .04)), U(u, 1.95, sx * (W_ / 2 - .04)), .03, verts=6)
        rk.tube(U(u, 1.95, -(W_ / 2 - .04)), U(u, 1.95, W_ / 2 - .04), .03, verts=6)
    for sx in (-1, 1): rk.tube(U(-.62, 1.95, sx * (W_ / 2 - .04)), U(.2, 1.86, sx * (W_ / 2 - .04)), .025, verts=6)
    rk.done()
    ld = G("PICK_Body_ladder", WM["alu"], c)
    for sx in (-1, 1): ld.box((.05, 2.9, .06), U(-1.25, 2.01, .1 + sx * .2))
    for k in range(9): ld.tube(U(-2.6 + .33 * k, 2.01, -.1), U(-2.6 + .33 * k, 2.01, .3), .02, verts=4)
    ld.done()
    tb = G("PICK_Body_toolbox", WM["grey"], c, bevel=.02, seg=1)
    tb.box((W_ - .16, .5, .32), U(-.8, .96))
    tb.done()
    sk = G("PICK_Body_sacks", WM["sack"], c, bevel=.05, seg=2)
    for (u, x, z, a) in ((-1.6, -.45, .78, .1), (-1.65, .1, .78, -.05), (-1.62, -.15, 1.0, .3), (-2.2, .5, .78, 1.3)):
        sk.box((.62, .42, .22), U(u, z + .11, x), rot=(0, 0, a))
    sk.done()
    pl = G("PICK_Body_planks", M["wood"], c, bevel=.008, seg=1)
    for k in range(3): pl.box((.18, 2.4, .04), U(-1.65 + .02 * k, 1.12 + .045 * k, .58 - .03 * k), rot=(.12, 0, .02))
    pl.done()
    # wheels (at the current pivots) + dark wheel-arch liners
    for i, (u, sx) in enumerate(((fu, 1), (fu, -1), (ru, 1), (ru, -1))):
        wheel(c, f"PICK_Wheel_{i}", (sx * .8, -u, wz), .36, .26)
    lin = G("PICK_Body_liners", M["dark"], c)
    for cu in (fu, ru):
        for sx in (-1, 1):
            lin.prism(band(arc(cu, wz, wr - .01, .52), [.025] * 8), .3, M=side_frame(sx * .78))
    lin.done()
    return V.stats(c)


# ---------------------------------------------------------------- Works_TowTruck
TOW = "W1 Works_TowTruck"
TOW_PARTS = {"TOW_Body": "Body", "TOW_Bed": "Bed", "TOW_Hook": "Hook", "TOW_Wheel_0": "Wheel_0", "TOW_Wheel_1": "Wheel_1",
             "TOW_Wheel_2": "Wheel_2", "TOW_Wheel_3": "Wheel_3"}
TOW_GROUPS = [(g, (g,)) for g in TOW_PARTS]


def build_towtruck():
    """Flatbed tow truck: orange cab-over with a teal stripe, light bar, mirrors; chassis with toolboxes, tank and
    fenders; tilting steel bed (pivot at its rear, (u -3.15, z 1.02)) with hazard-striped edges, stake pockets,
    headboard, winch and rear ramps; the hook hangs from its own pivot (u -2.9, z 1.64)."""
    c = col(TOW); show_only(TOW)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    paint = WM["orange"]
    fu, ru = 2.1, -1.4
    # cab-over
    cab = [(1.72, .95), (3.12, .95), (3.27, 1.12), (3.29, 1.95), (3.2, 2.33), (3.0, 2.42), (1.75, 2.42)]
    b = G("TOW_Body_cab", paint, c, bevel=.09, seg=2)
    b.prism(cab, 2.1, M=side_frame(0))
    b.done()
    st = G("TOW_Body_stripe", WM["teal"], c)
    for sx in (-1, 1): st.prism([(1.74, 1.18), (3.25, 1.18), (3.27, 1.3), (1.74, 1.3)], .01, M=side_frame(sx * 1.055))
    st.box((1.9, .01, .12), U(3.292, 1.24))
    st.done()
    gl = G("TOW_Body_glass", M["glass"], c)
    windscreen(c, "TOW_Body", (3.29, 1.58), (3.2, 2.3), 1.86, out=.035)
    for sx in (-1, 1): glass_side(gl, [(3.05, 1.62), (2.95, 2.3), (2.1, 2.3), (2.1, 1.62)], sx * 1.054)
    gl.done()
    dk = G("TOW_Body_dark", M["dark"], c, bevel=.01, seg=1)
    dk.box((1.2, .05, .34), U(3.28, 1.3))                                            # grille
    for z in (1.18, 1.28, 1.38): dk.box((1.15, .02, .025), U(3.31, z))
    for sx in (-1, 1):
        dk.box((.012, .012, 1.2), U(2.05, 1.6, sx * 1.054))                          # door seams
        dk.box((.03, .16, .04), U(2.3, 1.5, sx * 1.07))
    for sx in (-1, 1): dk.box((.14, 6.2, .3), U(-.05, .72, sx * .45))                # chassis rails
    for u in (1.4, -.5, -2.6): dk.box((.9, .12, .2), U(u, .72))
    dk.done()
    bp = G("TOW_Body_bumper", WM["grey"], c, bevel=.03, seg=1)
    bp.box((2.16, .24, .3), U(3.2, .96))                                              # bumper against the cab, under the grille
    bp.box((1.9, .1, .1), U(3.12, .78))                                               # lower valance
    for sx in (-1, 1):
        bp.box((.3, .3, .05), U(2.55, .6, sx * .92)); bp.box((.3, .3, .05), U(2.55, .82, sx * .92))   # steps
    bp.box((1.8, .1, .12), U(-3.22, .45))                                             # underride bar
    for sx in (-1, 1): bp.box((.08, .08, .35), U(-3.15, .6, sx * .7))
    bp.done()
    ll = G("TOW_Body_head", OM["headlight"], c, bevel=.01, seg=1)
    for sx in (-1, 1): ll.box((.3, .04, .16), U(3.33, .97, sx * .72))                # headlights set in the bumper
    ll.done()
    tl = G("TOW_Body_tail", OM["taillight"], c, bevel=.008, seg=1)
    for sx in (-1, 1): tl.box((.3, .05, .12), U(-3.22, .62, sx * .7))
    tl.done()
    lb = G("TOW_Body_lightbar", M["dark"], c, bevel=.01, seg=1)
    lb.box((1.5, .25, .07), U(2.4, 2.46))
    lb.done()
    lo = G("TOW_Body_lightDomes", M["fruit"], c)
    for sx in (-1, 0, 1): lo.ball(.1, U(2.4, 2.53, sx * .55), scale=(1.3 if sx == 0 else 1, 1, .75), sub=2)
    lo.done()
    mr = G("TOW_Body_mirrors", M["dark"], c, bevel=.01, seg=1)
    for sx in (-1, 1):
        mr.tube(U(3.0, 2.0, sx * 1.05), U(3.05, 2.05, sx * 1.25), .02, verts=4)
        mr.tube(U(3.0, 1.55, sx * 1.05), U(3.05, 1.65, sx * 1.25), .02, verts=4)
        mr.box((.06, .1, .45), U(3.05, 1.85, sx * 1.27))
    mr.done()
    # chassis kit: toolboxes, fuel tank, fenders, bed subframe and the tilt ram
    tb = G("TOW_Body_boxes", WM["grey"], c, bevel=.02, seg=1)
    for sx in (-1, 1): tb.box((.4, .9, .45), U(.6, .78, sx * .82))
    tb.done()
    ft = G("TOW_Body_tank", WM["alu"], c)
    ft.cyl(.22, .7, U(-.35, .7, .78), rot=(math.pi / 2, 0, 0), verts=16)
    ft.done()
    fe = G("TOW_Body_fenders", M["dark"], c)
    for sx in (-1, 1):
        fe.prism(band(arc(fu, .45, .54, .95), [.03] * 8), .42, M=side_frame(sx * 1.0))
        fe.prism(band(arc(ru, .45, .55, .62), [.03] * 8), .6, M=side_frame(sx * 1.0))
    fe.done()
    sf = G("TOW_Body_subframe", WM["grey"], c, bevel=.01, seg=1)
    for sx in (-1, 1): sf.box((.12, 4.5, .12), U(-1.0, .93, sx * .5))
    sf.box((1.1, .25, .18), U(1.3, .96))
    sf.done()
    rm, rr = G("TOW_Body_ram", WM["grey"], c), G("TOW_Body_rod", OM["chrome"], c)
    ram(rm, rr, U(.9, .9), U(-.6, 1.02), .07, .04)
    rm.done(); rr.done()
    # bed (pivot u -3.15, z 1.02)
    bd = G("TOW_Bed_deck", WM["deck"], c, bevel=.015, seg=1)
    bd.box((2.2, 4.4, .1), U(-1.08, 1.07))
    for k in range(9): bd.box((.04, 4.3, .02), U(-1.08, 1.13, -.96 + .24 * k))
    bd.done()
    hz = G("TOW_Bed_hazard", WM["hazard"], c, bevel=.006, seg=1)
    for sx in (-1, 1): hz.box((.1, 4.4, .18), U(-1.08, 1.2, sx * 1.07))
    hz.box((2.24, .1, .2), U(-3.27, 1.1))
    hz.done()
    sp = G("TOW_Bed_pockets", WM["grey"], c, bevel=.008, seg=1)
    for sx in (-1, 1):
        for k in range(5): sp.box((.08, .1, .2), U(-2.9 + 1.0 * k, 1.12, sx * 1.12))
    sp.done()
    hb = G("TOW_Bed_headboard", WM["grey"], c, bevel=.015, seg=1)
    hb.box((2.0, .1, .6), U(1.12, 1.38))
    for sx in (-1, 0, 1): hb.box((.08, .12, .62), U(1.13, 1.38, sx * .95))
    hb.done()
    wn = G("TOW_Bed_winch", M["dark"], c, bevel=.01, seg=1)
    wn.cyl(.14, .5, U(.85, 1.28), rot=(0, math.pi / 2, 0), verts=14)
    wn.box((.18, .25, .25), U(.85, 1.28, .38))
    wn.done()
    wc = G("TOW_Bed_cable", WM["lever"], c)
    wc.tube(U(.85, 1.28), U(-3.1, 1.22), .015, verts=4)
    wc.done()
    rp = G("TOW_Bed_ramps", WM["grey"], c, bevel=.01, seg=1)
    for sx in (-1, 1): rp.box((.42, .5, .05), U(-3.5, .98, sx * .7), rot=(-.32, 0, 0))
    rp.done()
    # hook (pivot at its top: u -2.9, z 1.64)
    hk = G("TOW_Hook_hook", WM["yellow"], c, bevel=.008, seg=1)
    hk.box((.1, .1, .1), U(-2.9, 1.59))
    hk.tube(U(-2.9, 1.55), U(-2.9, 1.3), .03, verts=8)
    hk.torus(.1, .028, U(-2.9, 1.18, 0), rot=(0, math.pi / 2, 0), seg=14, rseg=5)
    hk.done()
    hc = G("TOW_Hook_chain", M["dark"], c)
    hc.box((.05, .05, .05), U(-2.9, 1.08))
    hc.done()
    for i, (u, sx, dual) in enumerate(((fu, 1, False), (fu, -1, False), (ru, 1, True), (ru, -1, True))):
        wheel(c, f"TOW_Wheel_{i}", (sx * 1.0, -u, .45), .45, .4 if not dual else .54, dual=dual, lugs=8)
    return V.stats(c)


# ---------------------------------------------------------------- Works_WreckingCrane
CRANE = "W1 Works_WreckingCrane"
CRANE_PARTS = {"CRN_Body": "Body", "CRN_Cab": "Cab", "CRN_Boom": "Boom", "CRN_BoomTip": "BoomTip", "CRN_Ball": "Ball"}
CRANE_GROUPS = [(g, (g,)) for g in CRANE_PARTS]


def build_crane():
    """Crawler crane with a lattice boom and a wrecking ball: tracks (Body), upper works with the operator cab,
    machinery house, counterweight and A-frame gantry with pendant lines (Cab, slews), lattice boom (Boom), sheave
    head (BoomTip: the code reads its position for the cable), the ball with its swivel (Ball: the code sets its
    position; the cable is drawn from BoomTip to the ball + .5 m up)."""
    c = col(CRANE); show_only(CRANE)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    paint = WM["yellow"]
    # ---- Body: crawler (tracks along Y, +-3 m), car body, slew ring under the Cab pivot (z 1.18)
    tr = G("CRN_Body_track", WM["steel"], c, smooth=False)
    fr = G("CRN_Body_frame", WM["frame"], c, bevel=.04, seg=1)
    rl = G("CRN_Body_rollers", WM["frame"], c)
    for sx in (-1, 1):
        gx = sx * 1.62
        track_loop(tr, gx, -2.45, 2.45, .5, .6, .8, pitch=.3, plate_t=.07, grouser=.06)
        fr.box((.5, 4.3, .55), (gx, 0, .62))
        wheel_x(rl, (gx, -2.45, .6), .42, .56, verts=18); wheel_x(rl, (gx, 2.45, .6), .42, .56, verts=18)
        for t_ in range(12):
            a = 2 * math.pi * t_ / 12
            rl.box((.4, .1, .1), (gx, 2.45 + math.sin(a) * .45, .6 + math.cos(a) * .45), rot=(-a, 0, 0))
        for k in range(6): wheel_x(rl, (gx, -1.9 + .76 * k, .2), .13, .45, verts=10)
        for y in (-1.0, 1.0): wheel_x(rl, (gx, y, 1.05), .09, .3, verts=10)
    fr.box((2.6, 1.6, .55), (0, 0, .7))
    tr.done(); fr.done(); rl.done()
    sr = G("CRN_Body_ring", WM["grey"], c, bevel=.01, seg=1)
    sr.cyl(1.05, .2, (0, 0, 1.08), verts=28)
    sr.done()
    # ---- Cab: upper works
    dk = G("CRN_Cab_deck", paint, c, bevel=.05, seg=1)
    dk.box((3.1, 5.2, .32), (0, .9, 1.36))
    dk.done()
    hs = G("CRN_Cab_house", paint, c, bevel=.1, seg=2)
    hs.box((2.3, 3.3, 1.75), (-.35, 1.45, 1.52 + .875))
    hs.done()
    cw = G("CRN_Cab_cwt", WM["grey"], c, bevel=.18, seg=3)
    cw.box((3.0, .75, 1.55), (0, 3.3, 1.52 + .775))
    cw.done()
    hz = G("CRN_Cab_hazard", WM["hazard"], c, bevel=.006, seg=1)
    hz.box((2.2, .02, .4), (0, 3.68, 2.2))
    hz.done()
    lv = G("CRN_Cab_louvres", M["dark"], c)
    for i in range(6): lv.box((.02, 1.5, .05), (.81, 1.6, 2.3 + .12 * i), rot=(0, -.35, 0))
    for i in range(6): lv.box((.02, 1.5, .05), (-1.51, 1.6, 2.3 + .12 * i), rot=(0, .35, 0))
    lv.done()
    ex = G("CRN_Cab_exhaust", WM["grey"], c)
    ex.tube((-.9, 2.4, 3.27), (-.9, 2.4, 3.9), .07, verts=10)
    ex.cyl(.1, .04, (-.9, 2.4, 3.92), rot=(.4, 0, 0), verts=10)
    ex.done()
    # operator cab, front right (+X)
    cx0, cx1, cy0, cy1 = .95, 1.85, -1.9, -.2
    cl = G("CRN_Cab_cabLow", paint, c, bevel=.04, seg=1)
    cl.box((cx1 - cx0, cy1 - cy0, .55), ((cx0 + cx1) / 2, (cy0 + cy1) / 2, 1.52 + .275))
    cl.done()
    pil = G("CRN_Cab_pillars", WM["grey"], c, bevel=.012, seg=1)
    zl, zt = 2.07, 3.3
    for (px, py) in ((cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1), (cx1, -1.05)):
        pil.box((.08, .08, zt - zl), (px + (.04 if px == cx0 else -.04), py + (.04 if py == cy0 else (-.04 if py == cy1 else 0)), (zl + zt) / 2))
    pil.box((.03, .03, .7), (1.45, cy0 + .005, 2.7), rot=(0, .5, 0))
    pil.done()
    gl = G("CRN_Cab_glass", M["glass"], c)
    gl.box((cx1 - cx0 - .14, .02, zt - zl - .08), ((cx0 + cx1) / 2, cy0 + .03, (zl + zt) / 2))
    for xx in (cx0 + .03, cx1 - .03): gl.box((.02, cy1 - cy0 - .14, zt - zl - .08), (xx, (cy0 + cy1) / 2, (zl + zt) / 2))
    gl.done()
    rf = G("CRN_Cab_roof", WM["teal"], c, bevel=.03, seg=1)
    rf.box((cx1 - cx0 + .1, cy1 - cy0 + .1, .1), ((cx0 + cx1) / 2, (cy0 + cy1) / 2, zt + .05))
    rf.done()
    se = G("CRN_Cab_seat", OM["seat"], c, bevel=.03, seg=1)
    se.box((.45, .45, .12), (1.4, -.8, 2.1)); se.box((.45, .1, .55), (1.4, -.55, 2.4), rot=(-.15, 0, 0))
    se.done()
    bc = G("CRN_Cab_beacon", M["fruit"], c)
    bc.ball(.09, (1.1, -.4, 3.45), scale=(1, 1, 1.2), sub=2)
    bc.done()
    wl = G("CRN_Cab_lights", OM["headlight"], c, bevel=.01, seg=1)
    for xx in (1.15, 1.65): wl.box((.14, .06, .1), (xx, -1.97, 3.3))
    wl.done()
    # A-frame gantry + pendant lines to the boom tip + boom hoist drum
    af = G("CRN_Cab_gantry", WM["grey"], c, bevel=.012, seg=1)
    apex = Vector((0, 1.0, 5.25))
    for sx in (-1, 1):
        af.tube((sx * .95, -.2, 1.52), apex + Vector((sx * .25, 0, 0)), .07, verts=8)
        af.tube((sx * .95, 2.9, 1.52), apex + Vector((sx * .25, 0, 0)), .07, verts=8)
    af.tube(apex + Vector((-.35, 0, 0)), apex + Vector((.35, 0, 0)), .09, verts=8)
    af.done()
    dr = G("CRN_Cab_drum", M["dark"], c)
    dr.cyl(.32, .9, (0, 1.8, 3.5), rot=(0, math.pi / 2, 0), verts=16)
    dr.done()
    rails = G("CRN_Cab_rails", WM["teal"], c)
    for y0, y1 in ((-.15, 2.95),):
        rails.tube((-1.45, y0, 3.55), (-1.45, y1, 3.55), .025, verts=6)
        for y in (y0, (y0 + y1) / 2, y1): rails.tube((-1.45, y, 3.27), (-1.45, y, 3.55), .022, verts=6)
    rails.done()
    # ---- Boom: lattice from the foot (u .95, z 1.95) to the tip (u 7.523, z 14.311)
    foot = Vector((0, -.95, 1.95)); tip = Vector((0, -7.523, 14.311))
    ax = (tip - foot); L = ax.length; ax.normalize()
    side = Vector((1, 0, 0)); nrm = ax.cross(side).normalized()             # boom 'up' (towards the back / top)
    def chord_pt(t, sx, sn):
        w = .55 - .3 * t; d = .45 - .25 * t
        return foot + ax * (t * L) + side * (sx * w) + nrm * (sn * d)
    ch = G("CRN_Boom_chords", paint, c)
    la = G("CRN_Boom_lacing", paint, c)
    n = 20
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for (sx, sn) in corners: ch.tube(chord_pt(.02, sx, sn), chord_pt(.985, sx, sn), .055, verts=6)
    for k in range(n):
        t0, t1 = .02 + .965 * k / n, .02 + .965 * (k + 1) / n
        for f in range(4):
            a0, a1 = corners[f], corners[(f + 1) % 4]
            p, q = (chord_pt(t0, *a0), chord_pt(t1, *a1)) if k % 2 == 0 else (chord_pt(t0, *a1), chord_pt(t1, *a0))
            la.tube(p, q, .026, verts=4)
            if k % 2 == 0: la.tube(chord_pt(t0, *a0), chord_pt(t0, *a1), .022, verts=4)
    ch.done(); la.done()
    ft = G("CRN_Boom_foot", paint, c, bevel=.02, seg=1)
    for sx in (-1, 1): ft.box((.08, .7, .6), foot + Vector((sx * .58, -.1, .05)))
    ft.done()
    pn = G("CRN_Boom_pins", WM["grey"], c)
    pin(pn, foot, .12, 1.4, verts=12)
    pn.done()
    pl = G("CRN_Boom_pendants", WM["lever"], c)
    for sx in (-1, 1): pl.tube(apex + Vector((sx * .25, 0, 0)), chord_pt(.985, sx, 1), .022, verts=4)
    pl.done()
    hzb = G("CRN_Boom_hazard", WM["hazard"], c, bevel=.005, seg=1)
    for sx in (-1, 1): hzb.box((.02, .8, .4), foot + ax * 1.2 + side * (sx * .62))
    hzb.done()
    # ---- BoomTip: sheave head
    tp = G("CRN_BoomTip_head", paint, c, bevel=.02, seg=1)
    tp.box((.5, .55, .38), tip + Vector((0, .05, -.02)))
    tp.done()
    sh = G("CRN_BoomTip_sheaves", M["dark"], c)
    for sx in (-1, 1): sh.cyl(.2, .06, tip + Vector((sx * .1, -.22, -.1)), rot=(0, math.pi / 2, 0), verts=14)
    pin(sh, tip + Vector((0, -.22, -.1)), .05, .42, verts=8)
    sh.done()
    # ---- Ball: wrecking ball + swivel + shackle (pivot = ball centre (0, -7.523, 1.3))
    bc_ = Vector((0, -7.523, 1.3))
    bl = G("CRN_Ball_ball", WM["ball"], c)
    bl.ball(.6, bc_, sub=3)
    bl.done()
    sw = G("CRN_Ball_swivel", WM["grey"], c, bevel=.01, seg=1)
    sw.cyl(.18, .14, bc_ + Vector((0, 0, .62)), verts=12)
    sw.cyl(.07, .2, bc_ + Vector((0, 0, .78)), verts=8)
    sw.torus(.11, .03, bc_ + Vector((0, 0, .98)), rot=(math.pi / 2, 0, 0), seg=12, rseg=5)
    sw.done()
    return V.stats(c)



# ###################################################################################################################
# batch 3: Works_Forklift, Works_SkidLoader, Works_CraneTruck, Works_Container
# ###################################################################################################################
FORK = "W1 Works_Forklift"
FORK_PARTS = {"FORK_Body": "Body", "FORK_Mast": "Mast", "FORK_Forks": "Forks"}
FORK_GROUPS = [(g, (g,)) for g in FORK_PARTS]


def build_forklift():
    """Counterbalance forklift. Body (root): chassis, rounded counterweight with a hazard plate, seat, steering,
    overhead guard with lights and beacon, tilt rams, wheels. Mast (pivot u .8, z .15; the code does not turn it):
    outer + inner channels, lift cylinder, chains. Forks (pivot u .92, z .25; the code slides it up .6 m in the
    Mast's frame): carriage, load backrest, two L tines."""
    c = col(FORK); show_only(FORK)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    paint = WM["yellowLow"]
    fu, ru = .42, -.95
    b = G("FORK_Body_chassis", paint, c, bevel=.04, seg=1)
    pts = [(.72, .2)] + arc(fu, .3, .37, .2) + [(-.2, .2)] + arc(ru, .25, .31, .2) + [(-.95, .2), (-.95, .8), (.72, .8)]
    b.prism(pts, 1.06, M=side_frame(0))
    b.done()
    cw = G("FORK_Body_cwt", paint, c, bevel=.16, seg=3)
    cw.box((1.12, .55, .95), U(-1.02, .7))
    cw.done()
    hz = G("FORK_Body_hazard", WM["hazard"], c, bevel=.005, seg=1)
    hz.box((.8, .02, .22), U(-1.3, .78))
    hz.done()
    hd = G("FORK_Body_hood", paint, c, bevel=.06, seg=2)
    hd.box((.96, .7, .2), U(-.45, .9))
    hd.done()
    dk = G("FORK_Body_dark", M["dark"], c, bevel=.01, seg=1)
    dk.box((.9, .5, .02), U(.25, .815))                                               # floor mat
    for k in range(4): dk.box((.02, .5, .03), U(-.45, 1.0, -.3 + .2 * k))           # hood vents
    dk.box((.5, .08, .05), U(-1.3, .42))                                             # tow pin slot
    dk.done()
    se = G("FORK_Body_seat", OM["seat"], c, bevel=.03, seg=1)
    se.box((.46, .42, .1), U(-.4, 1.06)); se.box((.46, .1, .45), U(-.64, 1.3), rot=(.15, 0, 0))
    se.done()
    sw = G("FORK_Body_steer", WM["lever"], c)
    sw.box((.3, .14, .32), U(.45, .96))                                              # dash
    sw.tube(U(.42, 1.1), U(.3, 1.35), .025, verts=6)
    sw.torus(.15, .018, (0, 0, 0), seg=16, rseg=4, M=Matrix.Translation(U(.29, 1.37)) @ Matrix.Rotation(.6, 4, 'X'))
    for k in range(2): sw.tube(U(.5, 1.05, -.12 + .08 * k), U(.42, 1.28, -.12 + .08 * k), .012, verts=4)
    sw.done()
    gd = G("FORK_Body_guard", WM["grey"], c, bevel=.012, seg=1)
    for sx in (-1, 1):
        gd.tube(U(.6, .8, sx * .48), U(.38, 2.18, sx * .48), .04, verts=8)
        gd.tube(U(-.95, 1.1, sx * .48), U(-.92, 2.18, sx * .48), .04, verts=8)
    gd.box((1.04, 1.45, .06), U(-.27, 2.2))
    gd.done()
    gs = G("FORK_Body_guardSlats", M["dark"], c)
    for k in range(5): gs.box((.94, .06, .02), U(-.85 + .3 * k, 2.24))
    gs.done()
    lt = G("FORK_Body_lights", OM["headlight"], c, bevel=.008, seg=1)
    for sx in (-1, 1): lt.box((.1, .06, .08), U(.42, 1.95, sx * .52))
    lt.done()
    tl = G("FORK_Body_tail", OM["taillight"], c, bevel=.006, seg=1)
    for sx in (-1, 1): tl.box((.1, .03, .06), U(-1.3, 1.0, sx * .42))
    tl.done()
    bc = G("FORK_Body_beacon", M["fruit"], c)
    bc.ball(.07, U(-.85, 2.3, .38), scale=(1, 1, 1.2), sub=2)
    bc.done()
    rm, rr = G("FORK_Body_ram", WM["grey"], c), G("FORK_Body_rod", OM["chrome"], c)
    for sx in (-1, 1): ram(rm, rr, U(.3, .6, sx * .38), U(.76, .95, sx * .38), .035, .02)
    rm.done(); rr.done()
    wheel(c, "FORK_Body_wheelF0", (.5, -fu, .3), .3, .22); wheel(c, "FORK_Body_wheelF1", (-.5, -fu, .3), .3, .22)
    wheel(c, "FORK_Body_wheelR0", (.46, -ru, .25), .25, .18); wheel(c, "FORK_Body_wheelR1", (-.46, -ru, .25), .25, .18)
    # ---- Mast
    ms = G("FORK_Mast_channels", WM["grey"], c, bevel=.01, seg=1)
    for sx in (-1, 1):
        ms.box((.09, .12, 1.95), U(.8, 1.1, sx * .44))
        ms.box((.07, .1, 1.9), U(.86, 1.12, sx * .33))
    for z in (.18, 1.0, 2.07): ms.box((.94, .1, .08), U(.81, z))
    ms.done()
    mc, mr_ = G("FORK_Mast_cyl", paint, c), G("FORK_Mast_rod", OM["chrome"], c)
    ram(mc, mr_, U(.78, .22), U(.78, 1.95), .05, .03, frac=.55)
    mc.done(); mr_.done()
    mh = G("FORK_Mast_chain", M["dark"], c)
    for sx in (-1, 1):
        mh.box((.05, .03, 1.5), U(.9, 1.25, sx * .18))
        mh.cyl(.06, .05, U(.86, 2.02, sx * .18), rot=(0, math.pi / 2, 0), verts=10)
    mh.done()
    # ---- Forks
    fc = G("FORK_Forks_carriage", WM["grey"], c, bevel=.01, seg=1)
    for z in (.32, .72): fc.box((.96, .06, .1), U(.95, z))
    for sx in (-1, 1): fc.box((.06, .06, .5), U(.95, .52, sx * .45))
    for k in range(5): fc.box((.03, .03, .45), U(.96, .98, -.4 + .2 * k))           # load backrest
    fc.box((.9, .04, .04), U(.96, 1.2))
    fc.done()
    ft = G("FORK_Forks_tines", WM["frame"], c, bevel=.008, seg=1)
    for sx in (-1, 1):
        ft.box((.1, .05, .52), U(.98, .5, sx * .25))
        ft.prism([(.95, .23), (1.88, .23), (1.88, .25), (1.0, .29), (.95, .29)], .1, M=side_frame(sx * .25))
    ft.done()
    fh = G("FORK_Forks_hazard", WM["hazard"], c, bevel=.004, seg=1)
    fh.box((.9, .015, .08), U(.985, .72))
    fh.done()
    return V.stats(c)


SKID = "W1 Works_SkidLoader"
SKID_PARTS = {"SKID_Body": "Body", "SKID_Arms": "Arms", "SKID_Bucket": "Bucket"}
SKID_GROUPS = [(g, (g,)) for g in SKID_PARTS]


def build_skidloader():
    """Skid-steer loader. Body (root): chassis, four wheels, side towers, ROPS cab with mesh sides and glass door,
    engine at the back with a grille, seat and levers, beacon. Arms (pivot at the towers' top, u -.95, z 1.88; the
    code raises it up to 45 deg): two arms with a cross tube and lift rams. Bucket (pivot at the arm noses, u 1.52,
    z .6; the code tips it -30..50 deg): bucket with side plates, back, floor and cutting edge."""
    c = col(SKID); show_only(SKID)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    paint = WM["yellowLow"]
    fu, ru, wr = .5, -.55, .34
    b = G("SKID_Body_chassis", paint, c, bevel=.05, seg=1)
    b.box((1.04, 1.95, .55), U(-.1, .58))
    b.done()
    tw = G("SKID_Body_towers", paint, c, bevel=.04, seg=1)
    for sx in (-1, 1):
        tw.prism([(-1.12, .4), (-.45, .4), (-.62, 1.0), (-.85, 1.95), (-1.12, 1.95)], .14, M=side_frame(sx * .62))
    tw.done()
    en = G("SKID_Body_engine", paint, c, bevel=.08, seg=2)
    en.box((1.0, .55, .6), U(-.88, 1.12))
    en.done()
    gr = G("SKID_Body_dark", M["dark"], c, bevel=.006, seg=1)
    gr.box((.7, .03, .4), U(-1.16, 1.0))
    for k in range(5): gr.box((.66, .035, .025), U(-1.18, .85 + .07 * k))
    gr.done()
    ca = G("SKID_Body_cage", WM["grey"], c, bevel=.012, seg=1)
    for (u, sx) in ((.48, 1), (.48, -1), (-.55, 1), (-.55, -1)): ca.box((.07, .07, 1.32), U(u, 1.5, sx * .44))
    ca.box((.96, 1.12, .08), U(-.04, 2.18))
    for sx in (-1, 1):                                                  # window frames on the sides
        for z in (.93, 2.12): ca.box((.05, 1.0, .05), U(-.04, z, sx * .455))
        ca.box((.05, .05, 1.15), U(-.02, 1.52, sx * .455))
    for z in (1.45, 2.12): ca.box((.9, .05, .05), U(-.555, z))                # back window frame
    ca.done()
    rf = G("SKID_Body_roof", WM["teal"], c, bevel=.03, seg=1)
    rf.box((1.0, 1.16, .07), U(-.04, 2.22))
    rf.done()
    gl = G("SKID_Body_glass", M["glass"], c)
    gl.box((.82, .015, 1.0), U(.5, 1.45))
    for sx in (-1, 1):
        gl.box((.015, .44, 1.12), U(.22, 1.52, sx * .45)); gl.box((.015, .44, 1.12), U(-.27, 1.52, sx * .45))
    gl.box((.82, .015, .62), U(-.56, 1.79))
    gl.done()
    dr = G("SKID_Body_doorFrame", WM["grey"], c, bevel=.006, seg=1)
    dr.box((.86, .04, .05), U(.51, .95)); dr.box((.86, .04, .05), U(.51, 1.96))
    dr.box((.04, .04, .9), U(.52, 1.45, .1))
    dr.done()
    se = G("SKID_Body_seat", OM["seat"], c, bevel=.03, seg=1)
    se.box((.46, .4, .1), U(-.2, 1.05)); se.box((.46, .1, .5), U(-.42, 1.32), rot=(.12, 0, 0))
    se.done()
    lv = G("SKID_Body_levers", WM["lever"], c)
    for sx in (-1, 1):
        lv.box((.1, .3, .15), U(.05, 1.0, sx * .3))
        lv.tube(U(.15, 1.05, sx * .3), U(.25, 1.35, sx * .3), .02, verts=6); lv.ball(.035, U(.25, 1.37, sx * .3), sub=1)
    lv.done()
    bc = G("SKID_Body_beacon", M["fruit"], c)
    bc.ball(.07, U(-.45, 2.32, .35), scale=(1, 1, 1.2), sub=2)
    bc.done()
    lt = G("SKID_Body_lights", OM["headlight"], c, bevel=.008, seg=1)
    for sx in (-1, 1): lt.box((.1, .06, .08), U(.5, 2.12, sx * .38))
    lt.done()
    hz = G("SKID_Body_hazard", WM["hazard"], c, bevel=.004, seg=1)
    hz.box((.8, .015, .14), U(-1.165, .58))
    hz.done()
    for i, (u, sx) in enumerate(((fu, 1), (fu, -1), (ru, 1), (ru, -1))):
        wheel(c, f"SKID_Body_wheel{i}", (sx * .7, -u, wr), wr, .3, lugs=8)
    # ---- Arms (pivot u -.95, z 1.88)
    am = G("SKID_Arms_arms", paint, c, bevel=.03, seg=1)
    cl = [(-.98, 1.9), (-.2, 1.96), (.65, 1.68), (1.3, .95), (1.52, .62)]
    for sx in (-1, 1): am.prism(band(cl, [.1, .11, .11, .09, .08]), .12, M=side_frame(sx * .8))
    am.tube(U(.9, 1.42, -.8), U(.9, 1.42, .8), .06, verts=10)
    am.done()
    ap = G("SKID_Arms_pins", WM["grey"], c)
    for sx in (-1, 1):
        pin(ap, U(-.95, 1.88, sx * .8), .08, .2, verts=10); pin(ap, U(1.52, .6, sx * .8), .06, .18, verts=10)
    ap.done()
    ar, arr = G("SKID_Arms_ram", WM["grey"], c), G("SKID_Arms_rod", OM["chrome"], c)
    for sx in (-1, 1): ram(ar, arr, U(-.62, .62, sx * .7), U(.15, 1.72, sx * .7), .05, .03)
    ar.done(); arr.done()
    # ---- Bucket (pivot u 1.52, z .6)
    side = [(1.55, .74), (1.6, .12), (1.72, .06), (2.46, .06), (2.46, .14), (2.05, .45), (1.82, .74)]
    bs = G("SKID_Bucket_sides", paint, c, bevel=.012, seg=1)
    for sx in (-1, 1): bs.prism(side, .05, M=side_frame(sx * .84))
    bs.done()
    bb = G("SKID_Bucket_shell", paint, c, bevel=.01, seg=1)
    bb.box((1.68, .05, .66), U(1.58, .42), rot=(.06, 0, 0))
    bb.box((1.68, .74, .05), U(2.06, .08))
    bb.box((1.68, .3, .05), U(1.72, .7), rot=(-.45, 0, 0))
    bb.done()
    be = G("SKID_Bucket_edge", WM["grey"], c, bevel=.006, seg=1)
    be.box((1.72, .14, .04), U(2.42, .075))
    for sx in (-1, 1): be.box((.04, .22, .3), U(1.48, .62, sx * .55))                  # quick-attach brackets
    be.box((1.2, .06, .1), U(1.5, .74))
    be.done()
    return V.stats(c)


CRT = "W1 Works_CraneTruck"
CRT_PARTS = {"CRT_Body": "Body", "CRT_CraneBase": "CraneBase", "CRT_CraneArm": "CraneArm", "CRT_CraneTip": "CraneTip",
             "CRT_Hook": "Hook", **{f"CRT_Wheel_{i}": f"Wheel_{i}" for i in range(6)}}
CRT_GROUPS = [(g, (g,)) for g in CRT_PARTS]


def build_cranetruck():
    """Truck-mounted loader crane (munck). Body (root): teal cab-over, chassis, plank deck with stake pockets and
    hazard ends, outriggers with pads, toolboxes, tank, fenders. CraneBase (pivot u 1.45, z 1.17; slews about up):
    slewing column with the control stand. CraneArm (pivot u 1.45, z 2.25; rests pointing back over the deck, the
    code raises it 8..33 deg): two telescopic boom sections + lift ram. CraneTip (u -2.317, z 3.259): sheave head
    (the cable is drawn from here to Hook). Hook (root, the code moves it): hook block and hook. Wheel_0..5: front,
    then the rear tandem (the code spins them about X)."""
    c = col(CRT); show_only(CRT)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    cab_p = WM["teal"]; crane_p = WM["yellow"]
    fu, r1, r2, wz = 2.9, -.9, -2.25, .5
    cab = [(2.35, 1.05), (3.86, 1.05), (4.0, 1.22), (4.02, 2.05), (3.93, 2.5), (3.75, 2.62), (2.38, 2.62)]
    b = G("CRT_Body_cab", cab_p, c, bevel=.09, seg=2)
    b.prism(cab, 2.2, M=side_frame(0))
    b.done()
    st = G("CRT_Body_stripe", WM["orange"], c)
    for sx in (-1, 1): st.prism([(2.37, 1.28), (3.99, 1.28), (4.01, 1.4), (2.37, 1.4)], .01, M=side_frame(sx * 1.105))
    st.box((2.0, .01, .12), U(4.025, 1.34))
    st.done()
    gl = G("CRT_Body_glass", M["glass"], c)
    windscreen(c, "CRT_Body", (4.02, 1.7), (3.93, 2.46), 1.96, out=.035)
    for sx in (-1, 1): glass_side(gl, [(3.78, 1.72), (3.68, 2.45), (2.85, 2.45), (2.85, 1.72)], sx * 1.104)
    gl.done()
    dk = G("CRT_Body_dark", M["dark"], c, bevel=.01, seg=1)
    dk.box((1.3, .05, .34), U(4.01, 1.32))
    for z in (1.22, 1.32, 1.42): dk.box((1.25, .02, .025), U(4.04, z))
    for sx in (-1, 1):
        dk.box((.012, .012, 1.25), U(2.8, 1.75, sx * 1.104)); dk.box((.03, .16, .04), U(3.05, 1.65, sx * 1.12))
        dk.box((.14, 8.0, .3), U(-.05, .78, sx * .5))
    for u in (2.2, .2, -1.6, -3.4): dk.box((1.0, .12, .2), U(u, .78))
    dk.done()
    bp = G("CRT_Body_bumper", WM["grey"], c, bevel=.03, seg=1)
    bp.box((2.24, .24, .3), U(3.95, 1.05))
    bp.box((2.0, .1, .1), U(3.86, .86))
    for sx in (-1, 1): bp.box((.3, .3, .05), U(3.3, .72, sx * .98))
    bp.box((1.9, .1, .12), U(-4.0, .55))
    bp.done()
    ll = G("CRT_Body_head", OM["headlight"], c, bevel=.01, seg=1)
    for sx in (-1, 1): ll.box((.3, .04, .16), U(4.08, 1.06, sx * .76))
    ll.done()
    tl = G("CRT_Body_tail", OM["taillight"], c, bevel=.008, seg=1)
    for sx in (-1, 1): tl.box((.3, .05, .12), U(-4.06, .72, sx * .75))
    tl.done()
    lb = G("CRT_Body_lightbar", M["dark"], c, bevel=.01, seg=1)
    lb.box((1.4, .22, .07), U(3.1, 2.66))
    lb.done()
    lo = G("CRT_Body_lightDomes", M["fruit"], c)
    for sx in (-1, 1): lo.ball(.1, U(3.1, 2.73, sx * .5), scale=(1, 1, .8), sub=2)
    lo.done()
    mr = G("CRT_Body_mirrors", M["dark"], c, bevel=.01, seg=1)
    for sx in (-1, 1):
        mr.tube(U(3.7, 2.1, sx * 1.1), U(3.75, 2.15, sx * 1.3), .02, verts=4)
        mr.tube(U(3.7, 1.65, sx * 1.1), U(3.75, 1.75, sx * 1.3), .02, verts=4)
        mr.box((.06, .1, .45), U(3.75, 1.95, sx * 1.32))
    mr.done()
    # deck (u -4.0 .. .7, z 1.2)
    dd = G("CRT_Body_deck", M["wood"], c, bevel=.008, seg=1)
    for k in range(10): dd.box((.21, 4.7, .06), U(-1.65, 1.23, -.99 + .22 * k))
    dd.done()
    dr = G("CRT_Body_deckFrame", WM["grey"], c, bevel=.012, seg=1)
    for sx in (-1, 1): dr.box((.1, 4.75, .2), U(-1.65, 1.15, sx * 1.12))
    dr.box((2.34, .12, .2), U(-4.02, 1.15)); dr.box((2.34, .12, .2), U(.72, 1.15))
    for sx in (-1, 1):
        for k in range(5): dr.box((.08, .1, .2), U(-3.6 + 1.0 * k, 1.12, sx * 1.18))
    dr.done()
    hz = G("CRT_Body_hazard", WM["hazard"], c, bevel=.005, seg=1)
    hz.box((2.2, .02, .18), U(-4.085, 1.15))
    for sx in (-1, 1): hz.box((.02, .5, .3), U(1.0, .75, sx * 1.66))
    hz.done()
    # outriggers (deployed) behind the cab, under the crane
    og = G("CRT_Body_outriggers", crane_p, c, bevel=.02, seg=1)
    og.box((2.4, .4, .3), U(1.0, .8))
    for sx in (-1, 1):
        og.box((.62, .26, .2), U(1.0, .8, sx * 1.42))
        og.box((.18, .18, .65), U(1.0, .45, sx * 1.6))
    og.done()
    pd = G("CRT_Body_pads", WM["grey"], c, bevel=.01, seg=1)
    for sx in (-1, 1): pd.box((.42, .42, .06), U(1.0, .03, sx * 1.6))
    pd.done()
    tb = G("CRT_Body_boxes", WM["grey"], c, bevel=.02, seg=1)
    for sx in (-1, 1): tb.box((.38, .8, .42), U(-.05, .82, sx * .82))
    tb.done()
    ftk = G("CRT_Body_tank", WM["alu"], c)
    ftk.cyl(.22, .7, U(1.85, .75, .78), rot=(math.pi / 2, 0, 0), verts=16)
    ftk.done()
    fe = G("CRT_Body_fenders", M["dark"], c)
    for sx in (-1, 1):
        fe.prism(band(arc(fu, wz, .58, 1.05), [.03] * 8), .42, M=side_frame(sx * 1.0))
        fe.box((.6, 1.95, .04), U(-1.58, 1.08, sx * 1.0))
    fe.done()
    # ---- CraneBase (pivot u 1.45, z 1.17)
    cb = G("CRT_CraneBase_column", crane_p, c, bevel=.03, seg=1)
    cb.cyl(.42, .2, U(1.45, 1.27), verts=20)
    cb.box((.62, .62, 1.0), U(1.45, 1.85))
    cb.done()
    ch = G("CRT_CraneBase_hazard", WM["hazard"], c, bevel=.004, seg=1)
    ch.box((.64, .02, .22), U(1.765, 1.55))
    ch.done()
    cs = G("CRT_CraneBase_controls", WM["lever"], c)
    for sx in (-1, 1):
        cs.box((.12, .3, .2), U(1.45, 1.55, sx * .4))
        for k in range(3): cs.tube(U(1.42 + .07 * (k - 1), 1.62, sx * .44), U(1.42 + .07 * (k - 1), 1.82, sx * .5), .012, verts=4)
    cs.done()
    # ---- CraneArm (pivot u 1.45, z 2.25 -> tip u -2.317, z 3.259)
    A = Vector((1.45, 2.25)); T = Vector((-2.317, 3.259)); d = (T - A); L = d.length; dn = d.normalized()
    def AP(t, off=0.0, x=0.0):
        p = A + d * t + Vector((-dn.y, dn.x)) * off
        return U(p.x, p.y, x)
    ang = math.atan2(d.y, -d.x)
    Ma = lambda t: Matrix.Translation(AP(t)) @ Matrix.Rotation(ang, 4, 'X')
    s1 = G("CRT_CraneArm_boom1", crane_p, c, bevel=.03, seg=1)
    s1.box((.4, L * .62, .42), (0, 0, 0), M=Ma(.29))
    s1.box((.52, .4, .5), (0, 0, 0), M=Ma(.02))
    s1.done()
    s2 = G("CRT_CraneArm_boom2", crane_p, c, bevel=.02, seg=1)
    s2.box((.3, L * .45, .32), (0, 0, 0), M=Ma(.76))
    s2.done()
    ah = G("CRT_CraneArm_hazard", WM["hazard"], c, bevel=.004, seg=1)
    for sx in (-1, 1): ah.box((.01, .6, .3), (sx * .156, 0, 0), M=Ma(.88))
    ah.done()
    ap = G("CRT_CraneArm_pins", WM["grey"], c)
    pin(ap, AP(0), .1, .62, verts=12)
    ap.done()
    hs = G("CRT_CraneArm_hoses", M["dark"], c)
    for sx in (-1, 1): hs.tube(AP(.05, .24, sx * .12), AP(.6, .23, sx * .12), .02, verts=5)
    hs.done()
    rm, rr = G("CRT_CraneArm_ram", crane_p, c), G("CRT_CraneArm_rod", OM["chrome"], c)
    ram(rm, rr, U(1.62, 1.6), AP(.28, -.22), .085, .05, frac=.5)
    rm.done(); rr.done()
    # ---- CraneTip (u -2.317, z 3.259)
    tp = G("CRT_CraneTip_head", crane_p, c, bevel=.02, seg=1)
    tp.box((.34, .3, .3), U(-2.24, 3.26))
    tp.done()
    sv = G("CRT_CraneTip_sheave", M["dark"], c)
    sv.cyl(.14, .1, U(-2.317, 3.2), rot=(0, math.pi / 2, 0), verts=14)
    pin(sv, U(-2.317, 3.2), .04, .38, verts=8)
    sv.done()
    # ---- Hook (root at u -2.317, z 1.95)
    hk = G("CRT_Hook_block", crane_p, c, bevel=.02, seg=1)
    hk.box((.24, .2, .3), U(-2.317, 1.8))
    hk.done()
    hh = G("CRT_Hook_hook", WM["grey"], c)
    hh.tube(U(-2.317, 1.65), U(-2.317, 1.52), .03, verts=8)
    hh.torus(.1, .028, U(-2.317, 1.42, 0), rot=(0, math.pi / 2, 0), seg=14, rseg=5)
    hh.done()
    hd = G("CRT_Hook_hazard", WM["hazard"], c, bevel=.003, seg=1)
    for sx in (-1, 1): hd.box((.01, .2, .2), U(-2.317, 1.82, sx * .125))
    hd.done()
    for i, (u, sx, dual) in enumerate(((fu, 1, False), (fu, -1, False), (r1, 1, True), (r1, -1, True), (r2, 1, True), (r2, -1, True))):
        wheel(c, f"CRT_Wheel_{i}", (sx * 1.0, -u, wz), .5, .42 if not dual else .56, dual=dual, lugs=8)
    return V.stats(c)


CONT = "W1 Works_Container"
CONT_PARTS = {"CONT_Body": "Body"}
CONT_GROUPS = [("CONT_Body", ("CONT_Body",))]


def build_container():
    """Old 20 ft shipping container, faded teal with crisp rust: corrugated sides and end, flat roof with low ribs,
    corner posts and castings, top and bottom rails, double doors at the +Y end with four lock bars, handles and
    hinges. No markings or text. 2.44 x 6.13 x 2.6 m like the current one (long side along Y)."""
    c = col(CONT); show_only(CONT)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    X, Y0, Y1, H = 1.22, -3.03, 3.1, 2.6
    paint = WM["container"]
    wl = G("CONT_Body_walls", paint, c)
    Ls = (Y1 - Y0) - .3; Hs = H - .34
    for sx in (-1, 1):
        Mw = Matrix(((0, 0, sx, sx * (X - .05)), (1, 0, 0, (Y0 + Y1) / 2), (0, 1, 0, H / 2), (0, 0, 0, 1)))
        wl.corrugated(Ls, Hs, M=Mw, pitch=.28, amp=.04, seg=4, t=.02)
    Me = Matrix(((1, 0, 0, 0), (0, 0, -1, Y0 + .1), (0, 1, 0, H / 2), (0, 0, 0, 1)))
    wl.corrugated(2 * X - .3, Hs, M=Me, pitch=.28, amp=.04, seg=4, t=.02)
    wl.done()
    rf = G("CONT_Body_roof", paint, c, bevel=.01, seg=1)
    rf.box((2 * X - .1, Y1 - Y0 - .1, .04), (0, (Y0 + Y1) / 2, H - .05))
    for k in range(9): rf.box((2 * X - .2, .12, .025), (0, Y0 + .4 + k * (Y1 - Y0 - .8) / 8, H - .02))
    rf.done()
    fr = G("CONT_Body_frame", WM["contFrame"], c, bevel=.02, seg=1)
    for sx in (-1, 1):
        for y in (Y0 + .08, Y1 - .08):
            fr.box((.16, .16, H), (sx * (X - .08), y, H / 2), open_bottom=True)
            for z in (.09, H - .09): fr.box((.2, .2, .18), (sx * (X - .1), y, z))         # corner castings
        for z in (.1, H - .08): fr.box((.14, Y1 - Y0 - .3, .16 if z < 1 else .12), (sx * (X - .07), (Y0 + Y1) / 2, z))
    for y in (Y0 + .08, Y1 - .08):
        for z in (.12, H - .1): fr.box((2 * X - .3, .14, .2 if z < 1 else .14), (0, y, z))
    fr.done()
    dc = G("CONT_Body_doors", paint, c, bevel=.01, seg=1)
    for sx in (-1, 1):
        dc.box((X - .17, .05, H - .42), (sx * (X / 2 - .04), Y1 - .04, H / 2))
        for z in (.55, 1.3, 2.05): dc.box((X - .3, .04, .05), (sx * (X / 2 - .04), Y1 - .005, z))
    dc.done()
    lb = G("CONT_Body_lockbars", WM["contFrame"], c)
    for xx in (-.85, -.3, .3, .85):
        lb.tube((xx, Y1 + .03, .3), (xx, Y1 + .03, H - .3), .025, verts=6)
        for z in (.35, H - .35): lb.box((.1, .06, .08), (xx, Y1 + .02, z))
        lb.box((.05, .1, .3), (xx + (.07 if xx > 0 else -.07), Y1 + .06, 1.15), rot=(0, 0, 0))
    for sx in (-1, 1):
        for z in (.45, 1.3, 2.15): lb.box((.12, .06, .1), (sx * (X - .2), Y1 + .01, z))
    lb.done()
    sh = G("CONT_Body_shadowGap", M["dark"], c)
    sh.box((.03, .02, H - .45), (0, Y1, H / 2))
    sh.done()
    return V.stats(c)


# ###################################################################################################################
# export: one atlas (lots_v3 make_export / fixed bake), then the parts rebuilt on the current model's skeleton
# ###################################################################################################################
MODELS = {   # file: (source collection, groups, group -> part, texture size, texel weights)
    "Works_Dumpster": (DUMP, DUMP_GROUPS, DUMP_PARTS, 1024, {"V3_WSkip": 1.0, "V3_WSkipIn": .7, "V3_WSlab": .5, "V3_WHazard": 1.2}),
    "Works_Excavator": (EXC, EXC_GROUPS, EXC_PARTS, 2048, {"V3_WYellow": 1.0, "V3_WYellowLow": 1.0, "V3_WTrack": .45, "V3_WTrackFrame": .5,
                                                          "V3_WGrey": .6, "V3_WTeal": .7, "V3_WHazard": 1.4, "V3_Seat": .8}),
    "Works_Pickup": (PICK, PICK_GROUPS, PICK_PARTS, 2048, {"V3_WCream": 1.0, "V3_WOrange": .6, "V3_WGrey": .5, "V3_WAlu": .4, "V3_Planks": .4, "V3_WSack": .4}),
    "Works_TowTruck": (TOW, TOW_GROUPS, TOW_PARTS, 2048, {"V3_WOrange": 1.0, "V3_WDeck": .8, "V3_WHazard": 1.2, "V3_WGrey": .6, "V3_WTeal": .6, "V3_WAlu": .5, "V3_WYellow": .5}),
    "Works_WreckingCrane": (CRANE, CRANE_GROUPS, CRANE_PARTS, 2048, {"V3_WYellow": .9, "V3_WTrack": .4, "V3_WTrackFrame": .4, "V3_WGrey": .7, "V3_WHazard": 1.2, "V3_WBall": .8, "V3_WTeal": .6}),
    "Works_Forklift": (FORK, FORK_GROUPS, FORK_PARTS, 1024, {"V3_WYellowLow": 1.0, "V3_WGrey": .7, "V3_WTrackFrame": .6, "V3_WHazard": 1.4}),
    "Works_SkidLoader": (SKID, SKID_GROUPS, SKID_PARTS, 1024, {"V3_WYellowLow": 1.0, "V3_WGrey": .6, "V3_WTeal": .7, "V3_WHazard": 1.4}),
    "Works_CraneTruck": (CRT, CRT_GROUPS, CRT_PARTS, 2048, {"V3_WTeal": 1.0, "V3_WYellow": .9, "V3_WGrey": .6, "V3_WHazard": 1.2, "V3_WAlu": .4, "V3_Planks": .5, "V3_WOrange": .6}),
    "Works_Container": (CONT, CONT_GROUPS, CONT_PARTS, 2048, {"V3_WContainer": 1.0, "V3_WContFrame": .8}),
    "Works_MiniExcavator": (MINI, MINI_GROUPS, MINI_PARTS, 1024, {"V3_WOrange": 1.0, "V3_WTrackFrame": .5, "V3_WGrey": .6,
                                                                  "V3_WTeal": .8, "V3_WHazard": 1.4}),
}


def prepare(name):
    """Export copies + atlas UVs (X_<group> objects in '<name> Export'). Returns the bakeable count."""
    cfg()
    src, groups, parts, size, texel = MODELS[name]
    V.make_export(src, name, groups=groups, default=groups[0][0], inside=(99, -99, 99, -99), walls=(), texel=texel,
                  cut=name not in KIT_REBUILD)
    for o in bpy.data.collections[name + " Export"].objects:      # bake target = the new atlas UVs
        if o.type == 'MESH' and "UVMap" in o.data.uv_layers:
            o.data.uv_layers.active = o.data.uv_layers["UVMap"]; o.data.uv_layers["UVMap"].active_render = True
    return len([o for o in bpy.data.collections[name + " Export"].objects if not o.hide_render])


def bake_step(name, part, parts, samples=32):
    cfg()
    show_only(name + " Export")
    return V.bake(name, size=MODELS[name][3], part=part, parts=parts, samples=samples)


def assemble(name):
    """'FINAL <name>': objects named exactly like the current model's parts, same parents and local transforms
    (so the same pivots / axes), each holding its group's baked geometry in its own local space."""
    cfg()
    src, groups, parts, size, texel = MODELS[name]
    tm = template(name)
    c = col("FINAL " + name)
    for o in list(c.objects): bpy.data.objects.remove(o)
    exp = {o.name[2:].split(".")[0]: o for o in bpy.data.collections[name + " Export"].objects}
    made = {}
    def depth(k):
        d = 0
        while tm[k][0] is not None: k = tm[k][0]; d += 1
        return d
    order = sorted(tm, key=depth)
    for part in order:
        parent, Ml, Mw = tm[part]
        grp = next(g for g, p in parts.items() if p == part)
        me = exp[grp].data.copy(); me.name = "W1_" + name + "_" + part
        for l in [l for l in me.uv_layers if l.name != "UVMap"]: me.uv_layers.remove(l)
        if me.attributes.get("olduv"): me.attributes.remove(me.attributes["olduv"])
        me.transform(Mw.inverted())
        o = bpy.data.objects.new("F_" + name + "_" + part, me); c.objects.link(o)
        if parent: o.parent = made[parent]
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = Ml.copy()
        made[part] = o
    bpy.context.view_layer.update()
    return {p: [round(x, 3) for x in o.matrix_world.translation] for p, o in made.items()}


def export(name):
    """FBX with the exact part names; then re-imports it and checks names / parents / transforms against the
    current model."""
    import checkout_project as cp
    c = bpy.data.collections["FINAL " + name]
    objs = list(c.objects)
    show_only("FINAL " + name)
    pre = "F_" + name + "_"
    for o in objs: o.name = o.name[len(pre):]
    try:
        path = cp.export_unity(objs, name, folder=EXPORT, turn=False)
    finally:
        for o in objs: o.name = pre + o.name
    # check
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    tm = template(name)
    rep = {}; tris = 0
    for o in new:
        n = o.name.split(".")[0]
        if o.type == 'MESH': tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
        if n not in tm: rep[n] = "EXTRA"; continue
        par = o.parent.name.split(".")[0] if o.parent else None
        dl = (o.matrix_world.translation - tm[n][2].translation).length
        dr = o.matrix_world.to_quaternion().rotation_difference(tm[n][2].to_quaternion()).angle
        rep[n] = {"parent_ok": par == tm[n][0], "dpos": round(dl, 5), "drot": round(dr, 5)}
    for p in tm:
        if p not in rep: rep[p] = "MISSING"
    lo, hi = bounds(new); olo, ohi = bounds(list(bpy.data.collections["OLD " + name].objects))
    for o in new: bpy.data.objects.remove(o)
    return {"fbx": path, "kb": os.path.getsize(path) // 1024, "tris": tris, "check": rep,
            "size_new": [round(x, 2) for x in (hi - lo)], "size_old": [round(x, 2) for x in (ohi - olo)]}


def pose_test(name, prefix, centre, ortho, poses=((0, 0, 0, 0), (20, 25, -40, 35), (-18, -10, 45, -35))):
    """The assembled model posed like CheckoutWorks.Digger does (cab yaw about up, boom / arm / bucket about the
    cab's right axis at their own origins); renders each pose and puts the model back."""
    c = bpy.data.collections["FINAL " + name]
    P = {o.name.split("_")[-1]: o for o in c.objects}
    rest = {k: o.matrix_basis.copy() for k, o in P.items()}
    out = []
    try:
        for i, (b, a, kk, yaw) in enumerate(poses):
            for k, o in P.items(): o.matrix_basis = rest[k].copy()
            bpy.context.view_layer.update()
            def turn(o, ang, axis):
                if not o or not ang: return
                W_ = o.matrix_world.copy(); piv = W_.translation.copy()
                R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(ang), 4, axis) @ Matrix.Translation(-piv)
                o.matrix_world = R @ W_
                bpy.context.view_layer.update()
            turn(P.get("Cab"), yaw, Vector((0, 0, 1)))
            right = (P["Cab"].matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized() if "Cab" in P else Vector((1, 0, 0))
            turn(P.get("Boom"), b, right); turn(P.get("Arm"), a, right); turn(P.get("Bucket"), kk, right)
            show_only("FINAL " + name)
            V.camera(centre, ortho, VIEW); out.append(render(f"{prefix}_pose{i}"))
    finally:
        for k, o in P.items(): o.matrix_basis = rest[k]
    return out


# ###################################################################################################################
# batch 4: the small lot-clearing props inside the kit FBXs (Works_Site, Works_Carry). Every other object of a kit
# is kept: same mesh, its old look re-baked from the old atlas into the new one through its old UVs ("OldUV").
# ###################################################################################################################
KIT_REBUILD = {
    "Works_Site": ["Prop_Barrier", "Prop_Cone", "Prop_DebrisPile", "Prop_Generator", "Prop_GreenWaste", "Prop_Pallet",
                   "Prop_SteelBeams", "Prop_TireStack", "Prop_WheelbarrowFull"],
    "Works_Carry": ["Prop_Box", "Prop_GrassBundle", "Prop_Rubble", "Prop_Sheet", "Prop_Tire"],
}
KIT_SIZE = {"Works_Site": 2048, "Works_Carry": 1024}


def old_kit_material(kit):
    name = "V3_OLDKIT_" + kit
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs["Surface"]); bs.inputs["Roughness"].default_value = .85
    uv = nt.nodes.new("ShaderNodeAttribute"); uv.attribute_name = "olduv"
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = old_tex(kit)
    nt.links.new(uv.outputs["Vector"], tx.inputs["Vector"]); nt.links.new(tx.outputs["Color"], bs.inputs["Base Color"])
    return m


def tile_sheet(out, items, cols=5, tile=420, hide_stage=True):
    """items: [(collection, object name)]: each object rendered alone (3/4 view, framed on its bounds), the tiles
    put together in a grid PNG."""
    import numpy as np
    sc = bpy.context.scene
    stage = [o for o in bpy.data.collections["Stage"].objects if o.type == 'MESH']
    keep = {o: o.hide_render for o in stage}
    paths = []
    try:
        if hide_stage:
            for o in stage: o.hide_render = True
        for i, (cn, on) in enumerate(items):
            show_only(cn)
            c = bpy.data.collections[cn]
            hidden = {o: o.hide_render for o in c.objects}
            sel = [o for o in c.objects if o.name == on or o.name.startswith(on + "_")]
            for o in c.objects: o.hide_render = o not in sel
            lo, hi = bounds(sel); ctr = (lo + hi) / 2; size = max((hi - lo).length, .3)
            V.camera(ctr, size * 1.15, VIEW, res=(tile, tile))
            paths.append(render(f"_tile_{i}"))
            for o, h in hidden.items(): o.hide_render = h
    finally:
        for o, h in keep.items(): o.hide_render = h
        V.camera((0, 0, 0), 5, VIEW)
    rows = (len(paths) + cols - 1) // cols
    big = np.ones((rows * tile, cols * tile, 4), np.float32)
    for i, p in enumerate(paths):
        im = bpy.data.images.load(p, check_existing=False)
        a = np.empty(tile * tile * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(tile, tile, 4)
        r, cc = i // cols, i % cols
        big[(rows - 1 - r) * tile:(rows - r) * tile, cc * tile:(cc + 1) * tile] = a
        bpy.data.images.remove(im); os.remove(p)
    o = bpy.data.images.new("sheet_tmp", cols * tile, rows * tile, alpha=False)
    o.pixels.foreach_set(big.ravel()); o.filepath_raw = os.path.join(QA, out + ".png"); o.file_format = 'PNG'; o.save()
    bpy.data.images.remove(o)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1600, 1000
    return os.path.join(QA, out + ".png")


def _chunks(c, name, O, n, area, zfun, seed, scale=1.0, rebar=2, colours=("slab", "slabW", "plasterT", "plasterC"), bricks=.5):
    """Chunky broken concrete / plaster pieces spread over `area` (x0, x1, y0, y1) around O, resting at zfun(x, y),
    a few bricks between them and bent rebar out of the bigger ones."""
    rnd = random.Random(seed)
    gs = {k: G(name + "_" + k, WM[k], c, bevel=.025 * scale, seg=1) for k in colours}
    br = G(name + "_bricks", WM["brick"], c, bevel=.01 * scale, seg=1)
    rb = G(name + "_rebar", WM["rebar"], c)
    x0, x1, y0, y1 = area
    for i in range(n):
        x = rnd.uniform(x0, x1); y = rnd.uniform(y0, y1); z = zfun(x, y)
        big = rnd.random() < .4
        sx, sy, sz = ((rnd.uniform(.45, .8), rnd.uniform(.3, .55), rnd.uniform(.12, .2)) if big else (rnd.uniform(.2, .35), rnd.uniform(.16, .3), rnd.uniform(.12, .25)))
        sx, sy, sz = sx * scale, sy * scale, sz * scale
        M0 = Matrix.Translation(O + Vector((x, y, z + sz * .2))) @ Euler((rnd.uniform(-.5, .5), rnd.uniform(-.5, .5), rnd.uniform(0, 3.14))).to_matrix().to_4x4()
        k = colours[0] if rnd.random() < .4 else rnd.choice(colours)
        gs[k].box((sx, sy, sz), (0, 0, 0), M=M0)
        if big and rebar > 0:
            rebar -= 1
            p0 = M0 @ Vector((sx * .2, 0, sz / 2)); mid = p0 + Vector((rnd.uniform(-.08, .08), rnd.uniform(-.08, .08), .3 * scale))
            tip = mid + Vector((rnd.uniform(-.25, .25), rnd.uniform(-.2, .2), .05)) * scale
            rb.tube(p0, mid, .015 * scale + .004, verts=5); rb.tube(mid, tip, .015 * scale + .004, verts=5)
        if rnd.random() < bricks:
            bx = x + rnd.uniform(-.25, .25) * scale; by = y + rnd.uniform(-.2, .2) * scale
            br.box((.22 * scale, .11 * scale, .07 * scale), O + Vector((bx, by, zfun(bx, by) + .04 * scale)), rot=(rnd.uniform(-.4, .4), rnd.uniform(-.4, .4), rnd.uniform(0, 3)))
    for g in gs.values(): g.done()
    br.done(); rb.done()


def kp_debris(c, n, O):
    """Debris pile 2.4 x 1.7 x 1.07 m: earth mound, chunky multi-coloured concrete / plaster, bricks, rebar, a plank."""
    md = G(n + "_mound", WM["mound"], c)
    md.ball(1.0, O + Vector((-.2, .04, 0)), scale=(1.1, .78, .82), sub=3); md.clip = 0.0
    md.done()
    def zat(x, y):
        d = math.hypot((x + .2) / 1.1, (y - .04) / .78)
        return max(0., .82 * math.sqrt(max(0, 1 - d * d)) - .1)
    _chunks(c, n, O, 26, (-1.15, .8, -.6, .66), zat, 4, scale=1.0, rebar=3)
    pl = G(n + "_plank", M["wood"], c, bevel=.008, seg=1)
    pl.box((1.3, .14, .04), O + Vector((.1, -.35, .5)), rot=(.1, -.35, .4))
    pl.done()


def kp_rubble(c, n, O):
    """The carried lump (hauled to the skip): 0.69 x 0.28 x 0.49 m, centred: two concrete pieces, a teal plaster
    chunk, bricks, a short bent rebar."""
    a = G(n + "_slab", WM["slab"], c, bevel=.025, seg=1)
    a.box((.42, .24, .2), O + Vector((-.08, 0, -.1)), rot=(.08, .12, .1))
    a.done()
    b = G(n + "_slabW", WM["slabW"], c, bevel=.02, seg=1)
    b.box((.26, .2, .18), O + Vector((.2, .01, -.08)), rot=(-.1, -.3, -.2))
    b.done()
    t = G(n + "_plaster", WM["plasterT"], c, bevel=.02, seg=1)
    t.box((.22, .16, .12), O + Vector((-.02, -.01, .1)), rot=(.2, .25, .6))
    t.done()
    br = G(n + "_bricks", WM["brick"], c, bevel=.008, seg=1)
    br.box((.22, .11, .07), O + Vector((.17, .02, .1)), rot=(.1, -.25, .4))
    br.box((.2, .1, .07), O + Vector((-.24, .03, .05)), rot=(-.2, .3, -.3))
    br.done()
    rb = G(n + "_rebar", WM["rebar"], c)
    rb.tube(O + Vector((-.12, 0, .0)), O + Vector((-.16, .02, .22)), .013, verts=5)
    rb.tube(O + Vector((-.16, .02, .22)), O + Vector((-.3, .05, .27)), .013, verts=5)
    rb.done()


def leaf_sprig(c, name, at, width, rz=0., tris=160):
    """A small leafy sprig: the city tree's crown (its own leaf clusters), decimated and scaled to `width`, painted
    with the procedural leaf green (it bakes into the kit atlas like any other part)."""
    o = V.city_tree(name, c, (0, 0, 0), 1, rot_z=rz, tris=tris, crown_only=True, width=width)
    o.location = at
    o.data.materials.clear(); o.data.materials.append(WM["leaf"])
    if "TreeUV" in o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers["TreeUV"])
    bm = bmesh.new(); bm.from_mesh(o.data)                                    # no loose verts, triangles only
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(o.data); bm.free()
    return o


def branch(g, a, d, L, r, rnd, depth=2):
    """A cut branch from a along d (length L, radius r) with a couple of side twigs; returns the twig tips."""
    b = a + d * L
    g.tube(a, b, r, verts=6, r2=r * .55)
    tips = [b]
    if depth:
        for k in range(2):
            t = rnd.uniform(.35, .75); p = a + d * (L * t)
            side = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(.2, .9))).normalized()
            nd = (d + side * .9).normalized()
            tips += branch(g, p, nd, L * rnd.uniform(.35, .5), r * .55, rnd, depth - 1)
    return tips


def kp_greenwaste(c, n, O):
    """Cut green waste 1.66 x 1.65 x 0.86 m: a loose heap of cut branches (bark, forked twigs, sawn ends) lying
    criss-cross, leafy sprigs (city-tree leaf clusters) along them, cut-grass tufts tucked in and around: an
    irregular silhouette, no smooth blobs."""
    rnd = random.Random(12)
    br = G(n + "_branches", WM["branch"], c, smooth=True)
    ends = G(n + "_cutEnds", WM["plasterC"], c)
    tips = []
    for i in range(12):
        layer = i // 4
        a = rnd.uniform(0, 6.28)
        start = O + Vector((math.cos(a) * rnd.uniform(.6, .82), math.sin(a) * rnd.uniform(.6, .82), .06 + layer * .14))
        tgt = O + Vector((rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), .25 + layer * .17))
        d = (tgt - start); d.z = max(d.z, .05); d.normalize()
        L = rnd.uniform(.8, 1.25); r = rnd.uniform(.03, .05)
        tips += branch(br, start, d, L, r, rnd, depth=2)
        ends.cyl(r * .95, .012, tuple(start - d * .005), rot=d.to_track_quat('Z', 'Y').to_euler(), verts=6)   # sawn end
    br.done(); ends.done()
    rnd.shuffle(tips)
    for k, t in enumerate(tips[:22]):
        leaf_sprig(c, f"{n}_sprig{k}", t + Vector((0, 0, -.12)), rnd.uniform(.42, .62), rz=rnd.uniform(0, 6.28), tris=140)
    for k in range(5):                                                   # leafy cuttings packed into the heap core
        a = rnd.uniform(0, 6.28); d = rnd.uniform(0, .35)
        leaf_sprig(c, f"{n}_core{k}", O + Vector((math.cos(a) * d, math.sin(a) * d, .12)), rnd.uniform(.6, .8), rz=rnd.uniform(0, 6.28), tris=160)
    gr = G(n + "_grass", WM["grassB"], c, smooth=False)
    dr = G(n + "_grassDry", M["grassdry"], c, smooth=False)
    for i in range(16):
        a = rnd.uniform(0, 6.28); d = rnd.uniform(.25, .8)
        (gr if i % 3 else dr).blades(O + Vector((math.cos(a) * d, math.sin(a) * d, rnd.uniform(0, .25) * (1 - d))), n=7,
                                     h=rnd.uniform(.25, .4), w=.05, seed=4300 + i, spread=.1, lean=(.5, 1.1))
    gr.done(); dr.done()


def kp_grassbundle(c, n, O):
    """Bundle of cut grass carried on the shoulder: 0.96 x 0.5 x 0.46 m, centred (x -.41 .. .55): a tied sheaf of
    long blades, the cut ends square at the back, the tips fanning out and drooping at the front, two twine bands."""
    rnd = random.Random(3)
    gb = G(n + "_sheaf", WM["grassB"], c, smooth=False)
    dr = G(n + "_sheafDry", M["grassdry"], c, smooth=False)
    for i in range(70):
        ang = rnd.uniform(0, 6.28); rr = math.sqrt(rnd.random()) * .12
        y, z = math.cos(ang) * rr, math.sin(ang) * rr
        a = O + Vector((-.4, y, z))
        m = O + Vector((.12, y * 1.05, z * 1.05))
        fan = Vector((0, math.cos(ang), math.sin(ang))) * rnd.uniform(.08, .22)
        tip = O + Vector((.55, y * 1.4, z * 1.3 - rnd.uniform(.0, .08))) + fan
        g = dr if i % 5 == 0 else gb
        g.tube(a, m, .018, verts=3, r2=.016); g.tube(m, tip, .016, verts=3, r2=.002)
    gb.cyl(.1, .5, O + Vector((-.15, 0, 0)), rot=(0, math.pi / 2, 0), verts=10)                 # packed core
    gb.done(); dr.done()
    ce = G(n + "_cutEnds", WM["leafB"], c)
    ce.cyl(.115, .02, O + Vector((-.405, 0, 0)), rot=(0, math.pi / 2, 0), verts=12)
    ce.done()
    tw = G(n + "_twine", M["rope"], c)
    for x in (-.25, .05): tw.torus(.125, .016, O + Vector((x, 0, 0)), rot=(0, math.pi / 2, 0), seg=14, rseg=4)
    tw.done()


def kp_cone(c, n, O):
    """Traffic cone 0.38 x 0.38 x 0.65 m: square base, cone with two white reflective bands."""
    b = G(n + "_base", M["dark"], c, bevel=.02, seg=1)
    b.box((.38, .38, .04), O + Vector((0, 0, .02)), open_bottom=True)
    b.done()
    k = G(n + "_body", WM["cone"], c)
    k.cyl(.15, .6, O + Vector((0, 0, .34)), verts=18, r2=.035)
    k.done()
    w = G(n + "_bands", WM["white"], c)
    rz = lambda z: .15 - (.15 - .035) * ((z - .04) / .6)
    for (z, h) in ((.42, .08), (.26, .07)):
        w.cyl(rz(z - h / 2) + .007, h, O + Vector((0, 0, z)), verts=18, r2=rz(z + h / 2) + .007)
    w.done()


def kp_barrier(c, n, O):
    """Plastic road barrier 1.22 x 0.56 x 0.9 m: red/white striped panel on two feet, a top rail, a warning lamp."""
    p = G(n + "_panel", WM["hazRW"], c, bevel=.03, seg=1)
    p.box((1.18, .07, .36), O + Vector((0, 0, .6)))
    p.done()
    f = G(n + "_frame", WM["grey"], c, bevel=.015, seg=1)
    for sx in (-1, 1):
        f.box((.05, .05, .82), O + Vector((sx * .54, 0, .43)))
        f.box((.08, .56, .06), O + Vector((sx * .54, 0, .03)), open_bottom=True)
    f.box((1.16, .05, .05), O + Vector((0, 0, .36)))
    f.done()
    l = G(n + "_lamp", M["fruit"], c)
    l.cyl(.06, .08, O + Vector((.42, 0, .86)), verts=12); l.ball(.06, O + Vector((.42, 0, .9)), scale=(1, 1, .5), sub=1)
    l.done()


def kp_generator(c, n, O):
    """Site generator 1.3 x 0.66 x 0.9 m (wheels at -x, handle to +x): orange housing on a grey tube frame, panel
    with sockets, fuel cap, exhaust, two wheels and a fold-out handle."""
    fr = G(n + "_frame", WM["grey"], c)
    for sy in (-1, 1):
        fr.tube(O + Vector((-.5, sy * .28, .18)), O + Vector((.5, sy * .28, .18)), .025, verts=6)
        fr.tube(O + Vector((-.5, sy * .28, .82)), O + Vector((.5, sy * .28, .82)), .025, verts=6)
        for x in (-.5, .5): fr.tube(O + Vector((x, sy * .28, .18)), O + Vector((x, sy * .28, .82)), .025, verts=6)
        fr.tube(O + Vector((.5, sy * .2, .7)), O + Vector((.74, sy * .2, .85)), .02, verts=6)
    fr.tube(O + Vector((.74, -.2, .85)), O + Vector((.74, .2, .85)), .02, verts=6)
    fr.tube(O + Vector((.4, -.28, .18)), O + Vector((.4, .28, .18)), .02, verts=6)
    for sy in (-1, 1): fr.box((.06, .06, .18), O + Vector((.4, sy * .26, .09)), open_bottom=True)    # feet
    fr.done()
    h = G(n + "_housing", WM["orange"], c, bevel=.06, seg=2)
    h.box((.88, .46, .5), O + Vector((0, 0, .47)))
    h.done()
    dk = G(n + "_panel", M["dark"], c, bevel=.01, seg=1)
    dk.box((.3, .02, .2), O + Vector((.15, -.235, .5)))
    dk.cyl(.05, .05, O + Vector((-.25, .1, .74)), verts=10)                         # fuel cap
    dk.tube(O + Vector((-.38, .15, .6)), O + Vector((-.38, .15, .8)), .03, verts=8)  # exhaust
    for k in range(4): dk.box((.02, .02, .3), O + Vector((-.25 + .05 * k, -.235, .48)))
    dk.done()
    sk = G(n + "_sockets", WM["teal"], c, bevel=.005, seg=1)
    for k in range(2): sk.cyl(.035, .03, O + Vector((.1 + .1 * k, -.25, .45)), rot=(math.pi / 2, 0, 0), verts=10)
    sk.done()
    tg = G(n + "_tyres", OM["rubber"], c); rg = G(n + "_rims", OM["rimSteel"], c)
    for sy in (-1, 1):
        Mw = Matrix.Translation(O + Vector((-.42, sy * .31, .15))) @ Matrix.Rotation(math.pi / 2, 4, 'X')
        tg.tyre(R=.1, r=.05, w=.04, M=Mw, seg=20, rseg=6); rg.rim(R=.07, w=.03, M=Mw, lugs=4)
    tg.done(); rg.done()


def kp_tirestack(c, n, O):
    """Four tyres stacked 0.86 x 0.86 x 0.88 m (Oficina-style tread tyres + rims on the top one)."""
    rnd = random.Random(5)
    tg = G(n + "_tyres", OM["rubber"], c)
    for k in range(4):
        tg.tyre(R=.3, r=.12, w=.1, loc=tuple(O + Vector((rnd.uniform(-.02, .02), rnd.uniform(-.02, .02), .11 + k * .22))), rot=(rnd.uniform(-.03, .03), rnd.uniform(-.03, .03), rnd.uniform(0, 3)), seg=56, rseg=10, worn=0., deep=1.7)
    tg.done()
    rg = G(n + "_rim", OM["rimSteel"], c)
    rg.rim(R=.2, w=.08, loc=tuple(O + Vector((0, 0, .77))), lugs=5)
    rg.done()


def kp_tire(c, n, O):
    """A single carried tyre 0.8 x 0.2 x 0.8 m standing (axis Y), centred."""
    tg = G(n + "_tyre", OM["rubber"], c)
    tg.tyre(R=.29, r=.11, w=.1, loc=tuple(O), rot=(math.pi / 2, 0, 0), seg=56, rseg=10, worn=0., deep=1.7)
    tg.done()


def kp_pallet(c, n, O):
    """EUR-style pallet 1.2 x 1.1 x 0.11 m (as the current one): top boards, three stringer rows of blocks, bottom boards."""
    rnd = random.Random(8)
    g = G(n + "_boards", M["wood"], c, bevel=.004, seg=1)
    for k in range(7):
        x = -.55 + k * (1.1 / 6)
        g.box((.13 if k in (0, 3, 6) else .1, 1.1, .022), O + Vector((x, 0, .099)), rot=(0, 0, rnd.uniform(-.01, .01)))
    for y in (-.5, 0, .5):
        g.box((1.2, .1, .022), O + Vector((0, y, .077)))
        for x in (-.52, 0, .52): g.box((.13, .1, .055), O + Vector((x, y, .0385)))
        g.box((1.2, .1, .011), O + Vector((0, y, .0055)))
    g.done()


def kp_beams(c, n, O):
    """Steel I-beams 3.1 x 0.8 x 0.45 m: three beams on two timber bearers, one across the top."""
    tb = G(n + "_bearers", M["wood"], c, bevel=.01, seg=1)
    for x in (-1.0, 1.0): tb.box((.12, .8, .1), O + Vector((x - .05, 0, .05)), open_bottom=True)
    tb.done()
    bm = G(n + "_beams", WM["beam"], c, bevel=.004, seg=1)
    def ibeam(cx, cy, z, L, h=.16, w=.12, rot=0.):
        Mb = Matrix.Translation(O + Vector((cx, cy, z))) @ Matrix.Rotation(rot, 4, 'Z')
        bm.box((L, w, .018), (0, 0, h / 2 - .009), M=Mb); bm.box((L, w, .018), (0, 0, -h / 2 + .009), M=Mb)
        bm.box((L, .014, h - .03), (0, 0, 0), M=Mb)
    for y in (-.25, 0, .25): ibeam(-.05, y, .18, 3.0)
    ibeam(-.1, .1, .35, 2.9, rot=.06)
    bm.done()


def kp_sheet(c, n, O):
    """A corrugated metal sheet 2 x 1 m (carried flat), centred."""
    g = G(n + "_sheet", WM["sheet"], c)
    g.corrugated(1.0, 2.0, tuple(O), rot=(0, 0, math.pi / 2), pitch=.13, amp=.012, seg=4, t=.006)
    g.done()


def kp_box(c, n, O):
    """A 0.5 m cardboard box, taped, centred."""
    g = G(n + "_box", WM["card"], c, bevel=.015, seg=1)
    g.box((.5, .5, .5), tuple(O))
    g.done()
    t = G(n + "_tape", WM["tape"], c)
    t.box((.12, .506, .506), tuple(O)); t.box((.506, .12, .506), tuple(O + Vector((0, 0, .0))))
    t.done()


def kp_wheelbarrow(c, n, O):
    """A full wheelbarrow 0.65 x 1.67 x 0.8 m (wheel at -y, handles at +y): orange tray heaped with rubble, grey
    tube frame and legs, a tyred wheel."""
    tr = G(n + "_tray", WM["orange"], c, bevel=.02, seg=1)
    tr.prism([(-.3, .3), (.36, .3), (.52, .64), (-.6, .64)], .6, M=Matrix.Translation(O + Vector((0, .08, 0))) @ side_frame(0))
    tr.done()
    fr = G(n + "_frame", WM["grey"], c)
    for sx in (-1, 1):
        fr.tube(O + Vector((sx * .14, -.6, .22)), O + Vector((sx * .26, .86, .62)), .022, verts=6)
        fr.tube(O + Vector((sx * .22, .4, .45)), O + Vector((sx * .24, .5, 0)), .02, verts=6)
    fr.tube(O + Vector((-.14, -.6, .22)), O + Vector((.14, -.6, .22)), .02, verts=6)
    fr.done()
    gr = G(n + "_grips", M["dark"], c)
    for sx in (-1, 1): gr.tube(O + Vector((sx * .25, .72, .59)), O + Vector((sx * .265, .86, .62)), .032, verts=6)
    gr.done()
    tg = G(n + "_tyre", OM["rubber"], c); rg = G(n + "_rim", OM["rimSteel"], c)
    Mw = Matrix.Translation(O + Vector((0, -.6, .2))) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
    tg.tyre(R=.15, r=.06, w=.05, M=Mw, seg=22, rseg=6); rg.rim(R=.1, w=.04, M=Mw, lugs=0)
    tg.done(); rg.done()
    md = G(n + "_load", WM["mound"], c)
    md.ball(1.0, O + Vector((0, .02, .6)), scale=(.27, .5, .15), sub=2)
    md.done()
    _chunks(c, n, O, 8, (-.14, .14, -.25, .3), lambda x, y: .62 + .08 * max(0, 1 - (y / .35) ** 2), 9, scale=.45, rebar=1)


KIT_BUILDERS = {"Prop_DebrisPile": kp_debris, "Prop_Rubble": kp_rubble, "Prop_GreenWaste": kp_greenwaste,
                "Prop_GrassBundle": kp_grassbundle, "Prop_Cone": kp_cone, "Prop_Barrier": kp_barrier,
                "Prop_Generator": kp_generator, "Prop_TireStack": kp_tirestack, "Prop_Tire": kp_tire,
                "Prop_Pallet": kp_pallet, "Prop_SteelBeams": kp_beams, "Prop_Sheet": kp_sheet, "Prop_Box": kp_box,
                "Prop_WheelbarrowFull": kp_wheelbarrow}


def build_kit(kit):
    """'W1 <kit>': the untouched objects copied as they are (old UVs kept as 'OldUV', old atlas as their material),
    the listed props rebuilt at their old origin."""
    cn = "W1 " + kit
    c = col(cn); show_only(cn)
    for o in list(c.objects): bpy.data.objects.remove(o)
    mats()
    tm = template(kit)
    om = old_kit_material(kit)
    for part, (parent, Ml, Mw) in tm.items():
        n = f"KIT_{part}"
        if part in KIT_REBUILD[kit]:
            KIT_BUILDERS[part](c, n, Mw.translation.copy())
        else:
            src = bpy.data.objects["OLD_" + kit + "_" + part]
            me = src.data.copy()
            # the old UVs kept as a plain corner vector attribute (not a UV map: the object then gets a fresh,
            # selected 'UVMap' from smart_project like the new parts, so pack_islands packs it too)
            old = [tuple(d.uv) for d in me.uv_layers[0].data]
            while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
            at = me.attributes.new("olduv", 'FLOAT_VECTOR', 'CORNER')
            for i, (u_, v_) in enumerate(old): at.data[i].vector = (u_, v_, 0.0)
            me.materials.clear(); me.materials.append(om)
            o = bpy.data.objects.new(n + "_old", me); c.objects.link(o); o.matrix_world = Mw.copy()
    return V.stats(c)


def kit_register(kit):
    tm = template(kit)
    parts = {f"KIT_{p}": p for p in tm}
    groups = [(g, (g + "_",)) for g in parts]
    MODELS[kit] = ("W1 " + kit, groups, parts, KIT_SIZE[kit], {"V3_OLDKIT_" + kit: 1.0, "V3_WLeaf": .5, "V3_WBranch": .4})
    return len(parts)


def kit_others_sheet(kit):
    items = []
    for p in template(kit):
        if p in KIT_REBUILD[kit]: continue
        items += [("OLD " + kit, "OLD_" + kit + "_" + p), ("FINAL " + kit, "F_" + kit + "_" + p)]
    return tile_sheet(f"works_{kit[6:].lower()}_others_cmp", items, cols=6, tile=360)
# w36
