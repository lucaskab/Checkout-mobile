
# lot_kit2.py - the second family of "unbought lot" obstacle models (Lots_v2):
#   Lot_Loja, Lot_Sobrado, Lot_Oficina, Lot_Posto, Lot_Garagem, Lot_Mato, Lot_Fabrica, Lot_Patio
# Same conventions as lot_kit / lot_build / lot_pipe: metres, front faces -Y, origin at ground centre,
# one baked BaseColor atlas per model, exported with checkout_project.export_unity (Unity local = Blender (x, y->z)).
# Footprint budget per lot: 10.0 m (X) x 11.5 m (Y), height 2-8 m.
#
#   import sys; sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
#   import lot_kit2 as L2; L2.build_all()              # sources under the "Lots_v2" collection
#   L2.pipeline("Lot_Loja")                            # export copy + bake atlas + FBX
#   L2.preview("Lot_Loja"); L2.contact_sheet()        # PNGs in ArtSource/Review/lots_v2
import bpy, bmesh, math, random, sys, os
sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
sys.path.insert(0, r"C:\Checkout-mobile\scripts\blender")
import era_kit as k, lot_kit as L, checkout_project as cp
from mathutils import Vector, Matrix

ROOT_COL = "Lots_v2"
EXPORT_COL = "Lots_v2 Export"
OUT = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets\Resources\CheckoutLots"
REVIEW = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\lots_v2"
LOTS = {"LOT Loja": "Lot_Loja", "LOT Sobrado": "Lot_Sobrado", "LOT Oficina": "Lot_Oficina", "LOT Posto": "Lot_Posto",
        "LOT Garagem": "Lot_Garagem", "LOT Mato": "Lot_Mato", "LOT Fabrica": "Lot_Fabrica", "LOT Patio": "Lot_Patio"}
FOOT = (10.0, 11.5)

# ------------------------------------------------------------------ materials (all names LOT2_*)
def cracked(name, base=(.66, .64, .59, 1), crack_scale=1.3, crack_amount=.6, stains=0.0, stain=(.22, .20, .18, 1), var=.14):
    """Concrete / asphalt slab with voronoi hairline cracks and optional dark stain blotches."""
    m, nt, bsdf, obj = L._start(name, .95)
    if nt is None:
        return m
    col, g = L.grime(nt, base, var, 6)
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs["Scale"].default_value = crack_scale
    nt.links.new(obj, vor.inputs["Vector"])
    crack = L.ramp(nt, vor.outputs["Distance"], .003, .011)
    region = L.ramp(nt, L.noise(nt, obj, .9, 2), .60 - crack_amount * .14, .64 - crack_amount * .10)
    vis = L.fmath(nt, 'MAXIMUM', crack, L.fmath(nt, 'SUBTRACT', 1.0, region))
    col = L.mix(nt, (.36, .34, .31, 1), col, vis)
    if stains:
        sm = L.ramp(nt, L.noise(nt, obj, 1.1, 3, .6), .64 - stains * .10, .70 - stains * .06)
        col = L.mix(nt, col, stain, sm)
    L._finish(nt, bsdf, col, g, .25)
    return m

def asphalt(name, base=(.33, .33, .34, 1), lines_x=(), lines_y=(), line_col=(.78, .70, .32, 1), line_w=.10, fade=.55, crack_amount=.5):
    """Dark asphalt with cracks and faded painted lines (lines_x: lines parallel to Y at those X; lines_y: parallel to X)."""
    m, nt, bsdf, obj = L._start(name, .9)
    if nt is None:
        return m
    col, g = L.grime(nt, base, .12, 5)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(obj, sep.inputs[0])
    wear = L.ramp(nt, L.noise(nt, obj, 2.5, 4), .40, .70, 0.0, 1.0)
    for axis, lst in (("X", lines_x), ("Y", lines_y)):
        for pos in lst:
            d = L.fmath(nt, 'ABSOLUTE', L.fmath(nt, 'SUBTRACT', sep.outputs[axis], pos))
            msk = L.ramp(nt, d, line_w / 2, line_w / 2 + .02, 1.0, 0.0)
            msk = L.fmath(nt, 'MULTIPLY', msk, L.fmath(nt, 'MULTIPLY', wear, fade))
            col = L.mix(nt, col, line_col, msk)
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs["Scale"].default_value = 2.0
    nt.links.new(obj, vor.inputs["Vector"])
    crack = L.ramp(nt, vor.outputs["Distance"], .003, .010)
    region = L.ramp(nt, L.noise(nt, obj, .8, 2), .58 - crack_amount * .14, .62 - crack_amount * .10)
    vis = L.fmath(nt, 'MAXIMUM', crack, L.fmath(nt, 'SUBTRACT', 1.0, region))
    col = L.mix(nt, (.16, .16, .16, 1), col, vis)
    L._finish(nt, bsdf, col, g, .2)
    return m

def blocks(name, c1=(.62, .61, .58, 1), c2=(.56, .55, .52, 1), mortar=(.48, .47, .44, 1)):
    """Grey concrete-block wall (bigger units than the brick material)."""
    m, nt, bsdf, obj = L._start(name, .9)
    if nt is None:
        return m
    col, fac = L.brick_socket(nt, obj, c1, c2, mortar, scale=2.5, bw=.5, rh=.25, msize=.05)
    col, g = L.grime(nt, col, .14, 8)
    L._finish(nt, bsdf, col, fac, .3)
    return m

def paint_faded(name, paint, rust=(.50, .26, .12, 1), rustiness=.5, rough=.65):
    return L.rustmetal(name, paint, rust, rustiness, rough)

M2 = {}
def reset_mats(prefix="LOT2_"):
    """Drop the cached v2 materials so edited material builders take effect on the next build."""
    M2.clear()
    for m in list(bpy.data.materials):
        if m.name.startswith(prefix): bpy.data.materials.remove(m)

def mats():
    """Shared v2 materials (plus everything in lot_kit.mats())."""
    if M2:
        return M2
    M2.update(L.mats())
    M2["sidewalk"] = cracked("LOT2_Sidewalk", (.62, .60, .55, 1), 2.6, .55)
    M2["apron"] = cracked("LOT2_Apron", (.60, .59, .56, 1), 2.2, .45, stains=.6, stain=(.16, .15, .14, 1))
    M2["asphalt"] = asphalt("LOT2_Asphalt")
    M2["blocks"] = blocks("LOT2_Blocks")
    M2["brickD"] = L.brickwall("LOT2_BrickDark", (.52, .26, .19, 1), (.44, .22, .16, 1), (.62, .58, .52, 1))
    M2["tiles"] = L.rooftiles("LOT2_Tiles", (.56, .33, .25, 1), (.48, .28, .22, 1))
    M2["steel"] = k.mat("LOT2_Steel", (.22, .24, .27, 1), rough=.6, var=.08, scale=10)
    M2["chrome"] = k.mat("LOT2_Chrome", (.55, .56, .58, 1), rough=.35, var=.06, scale=10, metallic=.6)
    M2["green"] = k.mat("LOT2_Green", (.33, .52, .20, 1), rough=.85, var=.20, scale=6)
    M2["greenD"] = k.mat("LOT2_GreenDark", (.22, .40, .16, 1), rough=.85, var=.20, scale=6)
    M2["grasspatch"] = k.mat("LOT2_GrassPatch", (.46, .58, .22, 1), rough=.9, var=.22, scale=4, bump=.3)
    M2["puddle"] = k.mat("LOT2_Puddle", (.30, .34, .36, 1), rough=.12, var=.05, scale=3)
    M2["oil"] = k.mat("LOT2_Oil", (.10, .10, .10, 1), rough=.3, var=.05, scale=3)
    M2["cardboard"] = k.mat("LOT2_Cardboard", (.70, .54, .34, 1), rough=.95, var=.12, scale=12)
    M2["mattress"] = k.stripes("LOT2_Mattress", (.86, .84, .76, 1), (.60, .66, .74, 1), width=.14, axis='Y', rough=.95)
    M2["cream"] = L.plaster("LOT2_Cream", (.92, .88, .76, 1), under=(.60, .50, .42, 1), damage=.4, crack_scale=2.0)
    M2["signpanel"] = L.plaster("LOT2_SignPanel", (.95, .93, .86, 1), under=(.80, .76, .68, 1), damage=.35, cracks=False)
    return M2

# ------------------------------------------------------------------ geometry helpers
def flat(o):
    for p in o.data.polygons: p.use_smooth = False
    return o

def puddle(name, loc, m, sx=1.2, sy=.8, rot=0., c=None, z=.05):
    o = k.ball(name, 1.0, (loc[0], loc[1], z), m, sub=2, scale=(sx * .55, sy * .55, .008), rot=(0, 0, rot), c=c)
    return o

def grass_patch(name, loc, m, sx=1.5, sy=1.1, rot=0., c=None):
    return flat(k.ball(name, 1.0, (loc[0], loc[1], .04), m, sub=2, scale=(sx, sy, .05), rot=(0, 0, rot), c=c))

def cblock(name, loc, m, rot=(0, 0, 0), c=None):
    """Concrete block 0.39 x 0.19 x 0.19."""
    return k.box(name, (.39, .19, .19), loc, m, rot=rot, bevel=.008, seg=1, c=c)

def tire_stack(prefix, x, y, n, m, c, seed=0):
    rnd = random.Random(seed)
    for i in range(n):
        L.tire(f"{prefix}{i}", (x + rnd.uniform(-.03, .03), y + rnd.uniform(-.03, .03), .10 + .20 * i), m, rot=(0, rnd.uniform(-.05, .05), rnd.uniform(0, 3)), c=c)

def box_pile(prefix, loc, m, c, seed=0, n=3):
    rnd = random.Random(seed)
    x, y, _ = loc
    out = []
    for i in range(n):
        w, d, h = rnd.uniform(.45, .7), rnd.uniform(.35, .55), rnd.uniform(.3, .45)
        o = k.box(f"{prefix}{i}", (w, d, h), (x + rnd.uniform(-.25, .25), y + rnd.uniform(-.2, .2), 0), m, rot=(0, 0, rnd.uniform(0, 1.5)), bevel=.012, seg=2, c=c)
        o.data.transform(Matrix.Translation((0, 0, h / 2)))
        if i == n - 1 and n > 1:
            o.location.z = rnd.uniform(.3, .4); o.rotation_euler = (rnd.uniform(-.2, .2), rnd.uniform(-.15, .15), rnd.uniform(0, 1.5))
        out.append(o)
    return out

def bench_broken(name, loc, m_wood, m_conc, rot=0., c=None):
    parts = [k.box(f"{name}_leg", (.08, .45, .42), (-.75, 0, .21), m_conc, bevel=.01, seg=2),
             k.box(f"{name}_leg", (.08, .45, .42), (.75, 0, .21), m_conc, bevel=.01, seg=2),
             k.box(f"{name}_slat", (1.7, .11, .04), (0, -.15, .44), m_wood, bevel=.004, seg=1),
             k.box(f"{name}_slat", (1.7, .11, .04), (0, .15, .44), m_wood, bevel=.004, seg=1)]
    s = k.box(f"{name}_slatB", (1.1, .11, .04), (0, 0, 0), m_wood, bevel=.004, seg=1)
    s.data.transform(Matrix.Translation((.55, 0, 0))); s.location = (-.8, 0, .44); s.rotation_euler = (0, math.radians(28), .05)
    parts.append(s)
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = (0, 0, rot)
    k.link(o, c)
    return L.ground(o)

def car_wreck(name, loc, m_body, m_dark, m_tire, m_block, rot=0., c=None, hood_open=True):
    """Hatchback on concrete blocks, no wheels, bonnet open."""
    parts = [k.box(f"{name}_body", (3.8, 1.65, .55), (0, 0, .70), m_body, bevel=.06, seg=3),
             k.box(f"{name}_cab", (2.1, 1.5, .60), (.25, 0, 1.25), m_body, bevel=.10, seg=3),
             k.box(f"{name}_glassF", (.32, 1.3, .42), (-.85, 0, 1.22), m_dark, bevel=.02, seg=1, rot=(0, math.radians(-30), 0)),
             k.box(f"{name}_glassB", (.30, 1.3, .42), (1.32, 0, 1.22), m_dark, bevel=.02, seg=1, rot=(0, math.radians(35), 0)),
             k.box(f"{name}_glassL", (1.5, .06, .40), (.25, -.75, 1.25), m_dark, bevel=.01, seg=1),
             k.box(f"{name}_glassR", (1.5, .06, .40), (.25, .75, 1.25), m_dark, bevel=.01, seg=1),
             k.box(f"{name}_bumpF", (.16, 1.7, .14), (-1.92, 0, .55), m_dark, bevel=.02, seg=2),
             k.box(f"{name}_bumpB", (.16, 1.7, .14), (1.92, 0, .55), m_dark, bevel=.02, seg=2)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(k.box(f"{name}_arch", (.9, .18, .50), (sx * 1.25, sy * .78, .62), m_dark, bevel=.03, seg=2))
    if hood_open:
        h = k.box(f"{name}_hood", (1.3, 1.5, .05), (0, 0, 0), m_body, bevel=.01, seg=1)
        h.data.transform(Matrix.Translation((-.65, 0, 0))); h.location = (-.55, 0, .98); h.rotation_euler = (0, math.radians(-50), 0)
        parts.append(h)
        parts.append(k.box(f"{name}_engine", (1.2, 1.3, .35), (-1.2, 0, .78), m_dark, bevel=.02, seg=1))
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = (0, 0, rot)
    k.link(o, c)
    R = Matrix.Rotation(rot, 4, 'Z')
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = R @ Vector((sx * 1.25, sy * .70, .0))
            cblock(f"{name}_blk", (loc[0] + p.x, loc[1] + p.y, .095), m_block, rot=(0, 0, rot), c=c)
            cblock(f"{name}_blk", (loc[0] + p.x, loc[1] + p.y, .285), m_block, rot=(0, 0, rot + math.radians(90)), c=c)
    return o

def shopping_cart(name, loc, m, rot=(0, 0, 0), c=None):
    parts = []
    w, d, h = .55, .85, .50
    for z, name2 in ((0.0, "b"), (h, "t")):
        parts += [k.box(f"{name}_{name2}", (w, .02, .02), (0, -d / 2, z), m, bevel=0, seg=1), k.box(f"{name}_{name2}", (w, .02, .02), (0, d / 2, z), m, bevel=0, seg=1),
                  k.box(f"{name}_{name2}", (.02, d, .02), (-w / 2, 0, z), m, bevel=0, seg=1), k.box(f"{name}_{name2}", (.02, d, .02), (w / 2, 0, z), m, bevel=0, seg=1)]
    for x in (-w / 2, w / 2):
        for y in (-d / 2, d / 2):
            parts.append(k.box(f"{name}_v", (.02, .02, h), (x, y, h / 2), m, bevel=0, seg=1))
    for i in range(1, 5):
        x = -w / 2 + w * i / 5
        parts.append(k.box(f"{name}_w", (.012, d, .012), (x, 0, 0), m, bevel=0, seg=1))
        parts.append(k.box(f"{name}_w", (.012, .012, h), (x, -d / 2, h / 2), m, bevel=0, seg=1))
        parts.append(k.box(f"{name}_w", (.012, .012, h), (x, d / 2, h / 2), m, bevel=0, seg=1))
    for j in range(1, 6):
        y = -d / 2 + d * j / 6
        parts.append(k.box(f"{name}_w", (w, .012, .012), (0, y, 0), m, bevel=0, seg=1))
        parts.append(k.box(f"{name}_w", (.012, .012, h), (-w / 2, y, h / 2), m, bevel=0, seg=1))
        parts.append(k.box(f"{name}_w", (.012, .012, h), (w / 2, y, h / 2), m, bevel=0, seg=1))
    parts.append(k.box(f"{name}_handle", (w + .1, .03, .03), (0, d / 2 + .12, h + .15), m, bevel=.004, seg=1))
    for x in (-w / 2, w / 2):
        parts.append(k.box(f"{name}_hb", (.025, .2, .025), (x, d / 2 + .05, h + .12), m, bevel=0, seg=1, rot=(math.radians(-40), 0, 0)))
        for y in (-d / 2 + .05, d / 2 - .05):
            parts.append(k.box(f"{name}_leg", (.025, .025, .22), (x, y, -.11), m, bevel=0, seg=1))
    for x in (-w / 2, w / 2):
        for y in (-d / 2 + .05, d / 2 - .05):
            if (x < 0 and y < 0): continue  # one wheel missing
            parts.append(k.cyl(f"{name}_wheel", .04, .03, (x, y, -.24), mats()["dark"], rot=(0, math.radians(90), 0), verts=8))
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = rot
    k.link(o, c)
    return o

def crooked_tree(name, loc, m_trunk, m_leaf, m_leaf2, c=None, seed=0, h=3.6, lean=.35):
    rnd = random.Random(seed)
    parts = []
    top = Vector((lean * h, lean * .4 * h, h))
    mid = top * .5 + Vector((.15, -.1, 0))
    parts.append(k.tube(f"{name}_t0", (0, 0, 0), mid, .16, m_trunk, verts=7))
    parts.append(k.tube(f"{name}_t1", mid, top, .11, m_trunk, verts=7))
    parts.append(k.ball(f"{name}_j", .15, mid, m_trunk, sub=1))
    b1 = mid + Vector((-.9, .5, 1.0)); b2 = top + Vector((.7, -.6, .6))
    parts.append(k.tube(f"{name}_b1", mid, b1, .07, m_trunk, verts=6))
    parts.append(k.tube(f"{name}_b2", top, b2, .06, m_trunk, verts=6))
    parts.append(k.tube(f"{name}_b3", mid + Vector((0, 0, .4)), mid + Vector((.3, 1.0, 1.2)), .05, m_trunk, verts=5))
    trunk = k.join(parts, name + "_trunk", origin=(0, 0, 0))
    leaves = []
    for i, (p, r, m) in enumerate(((top + Vector((0, 0, .5)), 1.25, m_leaf), (b1 + Vector((0, 0, .3)), .85, m_leaf2), (b2 + Vector((0, 0, .2)), .8, m_leaf),
                                   (top + Vector((-.5, .7, .1)), .8, m_leaf2))):
        leaves.append(flat(k.ball(f"{name}_l{i}", r, p, m, sub=1, scale=(1.0 + rnd.uniform(-.15, .2), 1.0 + rnd.uniform(-.15, .2), .72), rot=(rnd.uniform(0, 1), rnd.uniform(0, 1), 0))))
    o = k.join([trunk] + leaves, name, origin=(0, 0, 0))
    o.location = loc
    k.link(o, c)
    return o

def bush(name, loc, m, m2=None, r=.6, c=None, seed=0):
    rnd = random.Random(seed)
    parts = []
    for i in range(4):
        rr = r * rnd.uniform(.55, .9)
        p = (rnd.uniform(-r, r) * .5, rnd.uniform(-r, r) * .5, rr * .78)
        parts.append(flat(k.ball(f"{name}_{i}", rr, p, (m2 if (i % 2 and m2) else m), sub=1, scale=(1.1, 1.0, .75), rot=(rnd.uniform(0, 1), 0, rnd.uniform(0, 3)))))
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc
    k.link(o, c)
    return o

def chainlink(name, a, b, h, m_post, m_wire, c=None, sag=0.0, lean=0.0, spacing=.32, n_posts=3):
    """Chain-link panel between points a and b (ground), posts + top rail + diamond lattice of thin wires."""
    a, b = Vector(a), Vector(b)
    d = b - a; Ln = d.length; ang = math.atan2(d.y, d.x)
    parts = []
    for i in range(n_posts):
        t = i / (n_posts - 1)
        parts.append(k.cyl(f"{name}_post", .035, h + .05, (Ln * t, 0, (h + .05) / 2), m_post, verts=8))
    parts.append(k.box(f"{name}_rail", (Ln, .03, .03), (Ln / 2, 0, h), m_post, bevel=0, seg=1))
    nd = int((Ln + h) / spacing)
    for i in range(nd + 1):
        s = -h + i * spacing
        for sgn in (1, -1):
            x0, z0 = s, 0.0
            x1, z1 = s + h, h
            if sgn < 0:
                x0, x1 = Ln - x0, Ln - x1
            # clip to [0, Ln]
            pts = []
            for (x, z) in ((x0, z0), (x1, z1)):
                pts.append(Vector((x, 0, z)))
            p0, p1 = pts
            if sgn > 0:
                if p0.x < 0: p0 = Vector((0, 0, (0 - x0) / (x1 - x0) * h))
                if p1.x > Ln: p1 = Vector((Ln, 0, (Ln - x0) / (x1 - x0) * h))
            else:
                if p0.x > Ln: p0 = Vector((Ln, 0, (x0 - Ln) / (x0 - x1) * h))
                if p1.x < 0: p1 = Vector((0, 0, (x0 - 0) / (x0 - x1) * h))
            if (p1 - p0).length < .15: continue
            parts.append(k.cyl(f"{name}_w", .007, (p1 - p0).length, (p0 + p1) / 2, m_wire, verts=3, bevel=0))
            parts[-1].rotation_euler = (p1 - p0).to_track_quat('Z', 'Y').to_euler()
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = a; o.rotation_euler = (lean, sag, ang)
    k.link(o, c)
    return o

def pump(name, loc, m_body, m_dark, m_panel, rot=0., c=None):
    parts = [k.box(f"{name}_base", (.6, 1.0, .12), (0, 0, .06), m_dark, bevel=.01, seg=1),
             k.box(f"{name}_body", (.5, .9, 1.55), (0, 0, .12 + .775), m_body, bevel=.025, seg=2),
             k.box(f"{name}_top", (.56, .96, .12), (0, 0, 1.73), m_dark, bevel=.02, seg=2),
             k.box(f"{name}_panel", (.03, .6, .35), (-.26, 0, 1.35), m_panel, bevel=.004, seg=1),
             k.box(f"{name}_panel", (.03, .6, .35), (.26, 0, 1.35), m_panel, bevel=.004, seg=1),
             k.box(f"{name}_nozzle", (.08, .14, .22), (-.28, .3, .95), m_dark, bevel=.01, seg=1)]
    parts.append(k.tube(f"{name}_hose", (-.28, .3, .85), (-.33, .35, .25), .02, m_dark, verts=6))
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = (0, 0, rot)
    k.link(o, c)
    return o

def railing(name, x0, x1, y, z, h, m, c=None, n=None, broken=()):
    parts = [k.box(f"{name}_top", (x1 - x0, .05, .05), ((x0 + x1) / 2, y, z + h), m, bevel=.004, seg=1)]
    n = n or int((x1 - x0) / .18)
    for i in range(n + 1):
        if i in broken: continue
        x = x0 + (x1 - x0) * i / n
        parts.append(k.box(f"{name}_bar", (.025, .025, h), (x, y, z + h / 2), m, bevel=0, seg=1))
    o = k.join(parts, name, origin=(0, 0, 0))
    k.link(o, c)
    return o

def new_col(name):
    root = k.col(ROOT_COL)
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if c.name not in root.children:
        for p in bpy.data.collections:
            if c.name in p.children: p.children.unlink(c)
        if c.name in bpy.context.scene.collection.children: bpy.context.scene.collection.children.unlink(c)
        root.children.link(c)
    for o in list(c.objects):
        bpy.data.objects.remove(o)
    return c

def show(*names):
    """Include only the named collections (any depth) + Studio in the view layer."""
    keep = set(names) | {"Studio", ROOT_COL, EXPORT_COL}
    def hit(lc):
        return lc.name in keep or any(hit(ch) for ch in lc.children)
    def walk(lc, parent_named):
        want = hit(lc) or parent_named
        lc.exclude = not want
        named = (lc.name in keep and lc.name not in (ROOT_COL, EXPORT_COL)) or parent_named
        for ch in lc.children:
            walk(ch, named)
    for ch in bpy.context.view_layer.layer_collection.children:
        walk(ch, False)
    for ch in bpy.context.view_layer.layer_collection.children:   # second pass: parents toggled first
        walk(ch, False)

def within(c):
    lo, hi = bounds(list(c.objects))
    return {"lo": [round(v, 2) for v in lo], "hi": [round(v, 2) for v in hi], "dims": [round(v, 2) for v in (hi - lo)],
            "ok": abs(lo.x) <= FOOT[0] / 2 + .01 and abs(hi.x) <= FOOT[0] / 2 + .01 and abs(lo.y) <= FOOT[1] / 2 + .01 and abs(hi.y) <= FOOT[1] / 2 + .01,
            "tris": k.tris(c)}

def bounds(objs):
    lo = Vector((1e9,) * 3); hi = -lo
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != 'MESH': continue
        me = o.evaluated_get(dg).data
        for v in me.vertices:
            w = o.matrix_world @ v.co; lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi

# ================================================================== 1. LOJA - closed corner shop
def build_loja():
    c = new_col("LOT Loja"); M = mats(); show("LOT Loja")
    bpy.context.scene.cursor.location = (0, 0, 0)
    m_wall = L.plaster("LOT2_LojaWall", (.90, .55, .45, 1), under=(.62, .50, .42, 1), damage=.5, brick_under=True, zband=.6, band=(.55, .40, .36, 1))
    m_shut = L.corrugated("LOT2_Shutter", (.62, .64, .62, 1), (.50, .26, .12, 1), .55, axis='Z', pitch=.09)
    m_awn = k.stripes("LOT2_Awning", (.78, .32, .28, 1), (.90, .86, .78, 1), width=.38, axis='X', rough=.9)
    m_awnB = k.stripes("LOT2_AwningB", (.68, .28, .25, 1), (.82, .78, .70, 1), width=.38, axis='X', rough=.9)
    m_signB = k.mat("LOT2_LojaSignBorder", (.50, .28, .24, 1), rough=.85, var=.10, scale=10)
    W, D, H, T = 7.6, 6.2, 3.3, .25
    yF = -D / 2 + .9  # building sits back; sidewalk in front
    # sidewalk pad (cracked concrete) + kerb step
    L.gbox("LOJA_pad", (9.6, 11.0, .05), (0, 0, .02), M["sidewalk"], bevel=.02, c=c)
    L.gbox("LOJA_kerb", (9.6, .25, .14), (0, -5.38, .07), M["concreteD"], bevel=.015, c=c)
    L.gbox("LOJA_wallF", (W, T, H), (0, yF + T / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("LOJA_wallB", (W, T, H), (0, yF + D - T / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("LOJA_wallL", (T, D - 2 * T, H), (-W / 2 + T / 2, yF + D / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("LOJA_wallR", (T, D - 2 * T, H), (W / 2 - T / 2, yF + D / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("LOJA_roof", (W + .1, D + .1, .18), (0, yF + D / 2, H), M["concreteD"], bevel=.015, c=c)
    L.gbox("LOJA_inner", (W - .5, D - .5, H - .3), (0, yF + D / 2, (H - .3) / 2), M["shadow"], bevel=0, c=c)
    # parapet with a raised centre (platibanda)
    L.gbox("LOJA_parapet", (W + .1, .22, .7), (0, yF + .11, H + .35), m_wall, bevel=.012, c=c)
    L.gbox("LOJA_parapetC", (3.2, .26, .5), (0, yF + .13, H + .95), m_wall, bevel=.012, c=c)
    for x in (-W / 2 + .3, W / 2 - .3):
        L.gbox("LOJA_parapetP", (.5, .3, .9), (x, yF + .15, H + .45), m_wall, bevel=.012, c=c)
    # water tank on the roof (caixa d'agua) - blue, faded
    k.cyl("LOJA_tank", .55, .75, (2.2, yF + 4.4, H + .18 + .375), M["drum"], verts=14, bevel=.02, c=c)
    k.cyl("LOJA_tankLid", .60, .08, (2.2, yF + 4.4, H + .18 + .78), M["drum"], verts=14, bevel=.02, c=c)
    # rolled-down shutter (front, centre) with its roll box, rails and padlock bar
    sw, sh = 3.4, 2.6
    k.box("LOJA_shutHole", (sw, .12, sh), (0, yF + .05, sh / 2), M["dark"], bevel=0, c=c)
    L.gbox("LOJA_shutter", (sw - .06, .05, sh - .1), (0, yF - .02, (sh - .1) / 2 + .05), m_shut, bevel=.004, seg=1, c=c)
    L.gbox("LOJA_shutBox", (sw + .3, .36, .36), (0, yF - .12, sh + .18), M["rust"], bevel=.03, c=c)
    for x in (-sw / 2 - .04, sw / 2 + .04):
        L.gbox("LOJA_rail", (.08, .10, sh), (x, yF - .03, sh / 2), M["steel"], bevel=.004, seg=1, c=c)
    k.box("LOJA_bottomBar", (sw, .08, .10), (0, yF - .06, .09), M["steel"], bevel=.006, seg=1, c=c)
    # awning over the shutter: sloped striped sheet, torn corner, two slim poles
    aw = k.box("LOJA_awning", (sw + 1.2, 1.5, .04), (0, 0, 0), m_awn, bevel=.006, seg=1, c=c)
    aw.data.transform(Matrix.Translation((0, -.75, 0))); aw.location = (0, yF - .02, sh + .62); aw.rotation_euler = (math.radians(18), 0, 0)
    fl = k.box("LOJA_awningFlap", (.9, .9, .04), (0, 0, 0), m_awnB, bevel=.006, seg=1, c=c)
    fl.data.transform(Matrix.Translation((.45, -.45, 0))); fl.location = (sw / 2 - .3, yF - 1.4, sh + .15); fl.rotation_euler = (math.radians(70), math.radians(10), .2)
    k.box("LOJA_awningBar", (sw + 1.2, .05, .05), (0, yF - 1.42, sh + .17), M["rust"], bevel=.004, seg=1, c=c)
    k.tube("LOJA_pole", (-sw / 2 - .5, yF - 1.4, .05), (-sw / 2 - .5, yF - 1.4, sh + .15), .03, M["rust"], verts=8, c=c)
    k.tube("LOJA_pole2", (sw / 2 + .5, yF - 1.4, .05), (sw / 2 + .7, yF - 1.1, sh + .15), .03, M["rust"], verts=8, c=c)
    # blank faded sign board on the parapet
    k.box("LOJA_sign", (3.0, .05, .8), (0, yF - .05, H + .55), M["signpanel"], bevel=.01, seg=1, c=c)
    for x, z, w, h in ((0, .40, 3.0, .08), (0, -.40, 3.0, .08), (-1.5, 0, .08, .8), (1.5, 0, .08, .8)):
        k.box("LOJA_signB", (w + .06, .04, h + .06), (x, yF - .08, H + .55 + z), m_signB, bevel=0, c=c)
    # side door (left, boarded) and small boarded window (right)
    k.box("LOJA_doorHole", (.9, .12, 2.1), (-2.9, yF + .05, 1.05), M["dark"], bevel=0, c=c)
    L.boarded_window("LOJA_door", .9, 2.0, (-2.9, yF, 1.05), M["door"], M["frame"], M["wood"], (0, -1, 0), c=c, seed=3, n_planks=2, frame=False)
    L.boarded_window("LOJA_win", 1.0, .9, (2.9, yF, 1.75), M["glass"], M["frame"], M["wood"], (0, -1, 0), c=c, seed=6)
    L.boarded_window("LOJA_winL", 1.1, .9, (-W / 2, yF + 3.8, 1.9), M["glass"], M["frame"], M["wood"], (-1, 0, 0), c=c, seed=7, n_planks=2)
    L.boarded_window("LOJA_winR", 1.1, .9, (W / 2, yF + 3.8, 1.9), M["glass"], M["frame"], M["wood"], (1, 0, 0), c=c, seed=8)
    # drain pipe + gutter
    k.tube("LOJA_down", (W / 2 + .06, yF + .2, H + .3), (W / 2 + .06, yF + .3, .2), .045, M["gutter"], verts=8, c=c)
    # props: broken bench, boxes, crates, bin, weeds in the cracks
    bench_broken("LOJA_bench", (-3.2, yF - 1.0, 0), M["wood"], M["concreteD"], rot=.08, c=c)
    box_pile("LOJA_box", (2.6, yF - .9, 0), M["cardboard"], c, seed=4, n=3)
    k.crate("LOJA_crate0", (3.6, yF - 1.6, 0), m=M["wood"], c=c, rot_z=.4)
    k.crate("LOJA_crate1", (3.6, yF - 1.6, .26), m=M["wood"], c=c, rot_z=.2)
    k.cyl("LOJA_bin", .28, .80, (-4.1, yF - .3, .40), M["rust"], verts=12, bevel=.012, c=c)
    L.ground(k.cyl("LOJA_bin2", .25, .65, (4.1, yF + 2.5, .25), M["drum"], rot=(math.radians(95), 0, 1.2), verts=12, bevel=.012, c=c))
    L.tire("LOJA_tire0", (-4.1, yF + 3.2, .10), M["tire"], rot=(0, 0, .2), c=c)
    L.dead_bush("LOJA_bush", (4.1, yF + 4.6, 0), M["twig"], r=.5, n=18, c=c, seed=21)
    pts = [(-4.3, -4.6), (-3.0, -4.9), (-1.2, -4.7), (.8, -4.85), (2.0, -4.6), (4.2, -4.8), (4.3, -2.6), (-4.4, -2.0), (-4.3, .5), (-4.4, 2.0),
           (4.35, .2), (4.3, 1.5), (-4.3, 4.6), (-1.5, 5.0), (1.0, 5.1), (3.0, 4.9), (4.3, 4.0), (-2.2, -3.7), (3.3, -3.5)]
    L.scatter_tufts("LOJA", pts, c, seed=51, size=.9)
    for i, (x, y, a) in enumerate(((-2.0, -4.3, .3), (-1.8, -4.15, 1.0), (3.9, -3.3, .8))):
        L.brick(f"LOJA_brick{i}", (x, y, .095), M["brick"], rot=(0, 0, a), c=c)
    return c

# ================================================================== 2. SOBRADO - 2-storey townhouse
def build_sobrado():
    c = new_col("LOT Sobrado"); M = mats(); show("LOT Sobrado")
    bpy.context.scene.cursor.location = (0, 0, 0)
    m_wall = L.plaster("LOT2_SobWall", (.62, .78, .80, 1), under=(.60, .50, .42, 1), damage=.5, brick_under=True, zband=.5, band=(.40, .50, .52, 1), crack_scale=1.6)
    m_trim = L.plaster("LOT2_SobTrim", (.94, .92, .86, 1), under=(.70, .62, .54, 1), damage=.3, cracks=False)
    m_gable = L.plaster("LOT2_SobGable", (.62, .78, .80, 1), under=(.60, .50, .42, 1), damage=.35, brick_under=True, crack_scale=1.6)
    m_lowwall = L.plaster("LOT2_SobLowWall", (.94, .92, .86, 1), under=(.60, .50, .42, 1), damage=.6, brick_under=True, crack_scale=2.0)
    m_gate = L.rustmetal("LOT2_Gate", (.20, .24, .26, 1), (.50, .26, .12, 1), .5)
    W, D, H, T = 6.6, 6.4, 5.9, .25
    yF = -D / 2 + 1.7   # yard in front
    L.pad("SOB_pad", 9.6, 11.0, c)
    L.gbox("SOB_wallF", (W, T, H), (0, yF + T / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("SOB_wallB", (W, T, H), (0, yF + D - T / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("SOB_wallL", (T, D - 2 * T, H), (-W / 2 + T / 2, yF + D / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("SOB_wallR", (T, D - 2 * T, H), (W / 2 - T / 2, yF + D / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("SOB_inner", (W - .5, D - .5, H - .3), (0, yF + D / 2, (H - .3) / 2), M["shadow"], bevel=0, c=c)
    # floor band + corner pilasters (white trim)
    L.gbox("SOB_band", (W + .08, D + .08, .22), (0, yF + D / 2, 3.0), m_trim, bevel=.01, c=c)
    for x in (-W / 2, W / 2):
        for y in (yF, yF + D):
            L.gbox("SOB_pil", (.32, .32, H), (x, y, H / 2), m_trim, bevel=.01, c=c)
    # gables (ridge along X) + tiled roof with missing tiles
    ZR = 7.6
    for x, nm in ((-W / 2 + T / 2, "L"), (W / 2 - T / 2, "R")):
        L.poly_prism("SOB_gable" + nm, [(-D / 2, H - .02), (D / 2, H - .02), (0, ZR)], T, (x, yF + D / 2, 0), m_gable, axis='X', c=c)
    roof, pitch, Ls = L.gable_roof("SOB_roof", 0, yF + D / 2, W + .9, D + .9, H + .05, ZR + .1, .09, M["tiles"],
                                   holes_f=[(1.1, 1.0, 2.4, 2.3)], holes_b=[(-2.4, .6, -1.4, 1.8), (1.5, 2.4, 2.3, 3.2)], c=c, ridge_cap=bpy.data.materials.get("LOT_CasaRidge") or k.mat("LOT_CasaRidge", (.58, .32, .24, 1), rough=.85, var=.12, scale=10))
    Mf = roof[0].matrix_world
    m_ridge = bpy.data.materials["LOT_CasaRidge"]
    for i, (u, v, a) in enumerate(((0.6, 0.5, .3), (2.7, 0.8, -.4), (-1.0, 2.3, .2))):
        o = k.box(f"SOB_tile{i}", (.3, .24, .03), (u, v, .07), m_ridge, rot=(0, 0, a), bevel=.004, seg=1, c=c)
        o.matrix_world = Mf @ o.matrix_world
    # balcony on the upper floor (front), sagging railing
    bz = 3.1
    L.gbox("SOB_balcony", (3.4, 1.1, .18), (-.6, yF - .55, bz - .09), M["concreteD"], bevel=.015, c=c)
    railing("SOB_rail", -2.3, 1.1, yF - 1.05, bz, .95, M["steel"], c=c, broken=(5, 6, 11))
    railing("SOB_railL", 0, 1.05, 0, bz, .95, M["steel"], c=c, n=5)
    bpy.data.objects["SOB_railL"].location = (-2.3, yF - 1.05, 0); bpy.data.objects["SOB_railL"].rotation_euler = (0, 0, math.radians(90))
    railing("SOB_railR", 0, 1.05, 0, bz, .95, M["steel"], c=c, n=5)
    bpy.data.objects["SOB_railR"].location = (1.1, yF - 1.05, 0); bpy.data.objects["SOB_railR"].rotation_euler = (0, 0, math.radians(90))
    for x in (-2.2, 1.0):
        k.box("SOB_balcBr", (.12, .9, .5), (x, yF - .5, bz - .45), M["concreteD"], bevel=.01, seg=1, rot=(math.radians(-25), 0, 0), c=c)
    # balcony door (open dark) + upper windows boarded
    k.box("SOB_bdoorHole", (1.1, .12, 2.1), (-.6, yF + .05, bz + 1.05), M["dark"], bevel=0, c=c)
    k.box("SOB_bdoorFrame", (1.3, .06, .1), (-.6, yF - .02, bz + 2.15), m_trim, bevel=.006, seg=1, c=c)
    L.boarded_window("SOB_winU1", 1.0, 1.3, (2.0, yF, bz + 1.4), M["glass"], M["frame"], M["wood"], (0, -1, 0), c=c, seed=11)
    L.boarded_window("SOB_winU2", 1.0, 1.3, (-2.3, yF + D, bz + 1.4), M["glass"], M["frame"], M["wood"], (0, 1, 0), c=c, seed=12)
    L.boarded_window("SOB_winU3", 1.0, 1.3, (1.3, yF + D, bz + 1.4), M["glass"], M["frame"], M["wood"], (0, 1, 0), c=c, seed=13, n_planks=2)
    L.boarded_window("SOB_winUL", 1.0, 1.2, (-W / 2, yF + 2.2, bz + 1.4), M["glass"], M["frame"], M["wood"], (-1, 0, 0), c=c, seed=14)
    L.boarded_window("SOB_winUR", 1.0, 1.2, (W / 2, yF + 4.2, bz + 1.4), M["glass"], M["frame"], M["wood"], (1, 0, 0), c=c, seed=15, n_planks=2)
    # ground floor: tall door (boarded) + 2 windows, step
    k.box("SOB_doorHole", (1.1, .12, 2.4), (1.6, yF + .05, 1.2), M["dark"], bevel=0, c=c)
    L.boarded_window("SOB_door", 1.1, 2.3, (1.6, yF, 1.2), M["door"], m_trim, M["wood"], (0, -1, 0), c=c, seed=16, n_planks=3)
    k.box("SOB_step", (1.6, .5, .16), (1.6, yF - .3, .08), M["concrete"], bevel=.02, seg=2, c=c)
    L.boarded_window("SOB_winG1", 1.1, 1.3, (-1.4, yF, 1.65), M["glass"], M["frame"], M["wood"], (0, -1, 0), c=c, seed=17)
    L.boarded_window("SOB_winGL", 1.0, 1.2, (-W / 2, yF + 4.4, 1.65), M["glass"], M["frame"], M["wood"], (-1, 0, 0), c=c, seed=18, n_planks=2)
    L.boarded_window("SOB_winGR", 1.0, 1.2, (W / 2, yF + 1.8, 1.65), M["glass"], M["frame"], M["wood"], (1, 0, 0), c=c, seed=19)
    # low front wall with pillars + crooked gate (front of the yard)
    yW = -5.2
    for x0, x1 in ((-4.75, -1.2), (1.2, 4.75)):
        L.gbox("SOB_lowwall", (x1 - x0, .22, 1.1), ((x0 + x1) / 2, yW, .55), m_lowwall, bevel=.012, c=c)
    for x in (-4.75, -1.2, 1.2, 4.75):
        L.gbox("SOB_pillar", (.36, .36, 1.4), (x, yW, .7), m_trim, bevel=.012, c=c)
        L.gbox("SOB_pillarCap", (.44, .44, .08), (x, yW, 1.42), M["concreteD"], bevel=.01, c=c)
    for x0, x1 in ((-4.75, -1.2), (1.2, 4.75)):
        L.gbox("SOB_lowwallCap", (x1 - x0, .3, .06), ((x0 + x1) / 2, yW, 1.12), M["concreteD"], bevel=.01, c=c)
    # side walls of the yard (left & right, lower)
    for x in (-4.75, 4.75):
        L.gbox("SOB_sidewall", (.2, 3.8, .9), (x, yW + 2.0, .45), m_lowwall, bevel=.012, c=c)
    # gate: two iron leaves, one hanging off the hinge
    g1 = railing("SOB_gate1", 0, 1.1, 0, .05, 1.25, m_gate, c=c, n=7)
    g1.location = (-1.0, yW, 0); g1.rotation_euler = (0, 0, math.radians(25))
    g2 = railing("SOB_gate2", 0, 1.1, 0, .05, 1.25, m_gate, c=c, n=7, broken=(3,))
    g2.location = (1.0, yW, .0); g2.rotation_euler = (math.radians(8), math.radians(-18), math.radians(150))
    L.ground(g2, .0)
    # overgrown yard: grass patches, bushes, big tufts, a tyre, bricks fallen from the wall
    grass_patch("SOB_grass0", (-2.0, -3.4, 0), M["grasspatch"], 2.2, 1.4, .3, c=c)
    grass_patch("SOB_grass1", (2.3, -3.8, 0), M["grasspatch"], 1.8, 1.2, -.4, c=c)
    grass_patch("SOB_grass2", (3.6, 1.5, 0), M["grasspatch"], 1.1, 2.4, .1, c=c)
    bush("SOB_bush0", (-3.4, -3.6, 0), M["green"], M["greenD"], r=.75, c=c, seed=3)
    bush("SOB_bush1", (3.4, -2.9, 0), M["green"], M["greenD"], r=.6, c=c, seed=4)
    bush("SOB_bush2", (-3.9, 2.0, 0), M["greenD"], M["green"], r=.55, c=c, seed=5)
    L.dead_bush("SOB_dead", (.2, -4.1, 0), M["twig"], r=.55, n=18, c=c, seed=6)
    pts = [(-4.2, -4.6), (-3.0, -4.7), (-1.6, -4.0), (-.5, -3.3), (.8, -3.6), (2.0, -4.6), (3.9, -4.5), (4.3, -4.0), (-4.3, -2.6), (4.3, -1.5),
           (-1.0, -2.6), (1.0, -2.4), (2.8, -2.3), (-2.6, -2.5), (4.3, 3.0), (-4.3, 3.4), (-4.2, 4.6), (-1.0, 5.0), (2.0, 5.0), (4.2, 4.8), (-4.3, .3), (4.4, 1.0)]
    L.scatter_tufts("SOB", pts, c, seed=61, dry_every=4, size=1.15)
    L.tire("SOB_tire0", (-3.0, -4.3, .10), M["tire"], rot=(0, 0, .2), c=c)
    for i, (x, y, a) in enumerate(((-.7, -4.7, .3), (-.4, -4.55, 1.0), (4.0, -3.3, .8), (-4.3, 4.0, .4))):
        L.brick(f"SOB_brick{i}", (x, y, .035), M["brick"], rot=(0, 0, a), c=c)
    return c

# ================================================================== 3. OFICINA - car repair garage
def build_oficina():
    c = new_col("LOT Oficina"); M = mats(); show("LOT Oficina")
    bpy.context.scene.cursor.location = (0, 0, 0)
    m_sign = L.plaster("LOT2_OfSign", (.90, .72, .22, 1), under=(.74, .60, .22, 1), damage=.4, cracks=False)
    m_signB = k.mat("LOT2_OfSignBorder", (.20, .20, .22, 1), rough=.85, var=.08, scale=10)
    mDoor = L.corrugated("LOT2_OfDoor", (.42, .50, .54, 1), (.52, .27, .12, 1), .5, axis='Z', pitch=.11)
    m_car = paint_faded("LOT2_CarPaint", (.70, .30, .22, 1), rustiness=.55)
    W, D, H, T = 8.2, 6.0, 3.8, .25
    yF = -D / 2 + 2.0
    # stained concrete apron + building
    L.gbox("OF_pad", (9.6, 11.0, .05), (0, 0, .02), M["apron"], bevel=.02, c=c)
    L.gbox("OF_wallF", (W, T, H), (0, yF + T / 2, H / 2), M["blocks"], bevel=.012, c=c)
    L.gbox("OF_wallB", (W, T, H), (0, yF + D - T / 2, H / 2), M["blocks"], bevel=.012, c=c)
    L.gbox("OF_wallL", (T, D - 2 * T, H), (-W / 2 + T / 2, yF + D / 2, H / 2), M["blocks"], bevel=.012, c=c)
    L.gbox("OF_wallR", (T, D - 2 * T, H), (W / 2 - T / 2, yF + D / 2, H / 2), M["blocks"], bevel=.012, c=c)
    L.gbox("OF_inner", (W - .5, D - .5, H - .3), (0, yF + D / 2, (H - .3) / 2), M["shadow"], bevel=0, c=c)
    L.gbox("OF_roof", (W + .4, D + .4, .16), (0, yF + D / 2, H), M["concreteD"], bevel=.015, c=c)
    L.gbox("OF_parapet", (W + .4, .2, .45), (0, yF + .1, H + .22), M["blocks"], bevel=.012, c=c)
    L.gbox("OF_parapetB", (W + .4, .2, .45), (0, yF + D - .1, H + .22), M["blocks"], bevel=.012, c=c)
    # wide bay opening with a hanging corrugated door (one corner still on its rail)
    bw, bh = 4.6, 3.0
    k.box("OF_bayHole", (bw, .12, bh), (-.8, yF + .05, bh / 2), M["dark"], bevel=0, c=c)
    L.gbox("OF_bayLintel", (bw + .4, .3, .35), (-.8, yF + .12, bh + .17), M["concreteD"], bevel=.012, c=c)
    k.box("OF_rail", (bw + .6, .08, .10), (-.8, yF - .14, bh + .12), M["steel"], bevel=.006, seg=1, c=c)
    door = k.box("OF_door", (bw - .2, .05, bh - .25), (0, 0, 0), mDoor, bevel=.006, seg=1, c=c)
    door.data.transform(Matrix.Translation((bw / 2 - .1, 0, -(bh - .25) / 2)))   # hang from the top-left corner
    door.location = (-.8 - bw / 2 + .1, yF - .22, bh + .18); door.rotation_euler = (math.radians(-4), math.radians(6), math.radians(3))
    for z in (.3, 1.4, 2.5):
        b = k.box("OF_doorBar", (bw - .2, .05, .08), (bw / 2 - .1, -.05, -(bh - .25) + z), M["steel"], bevel=.004, seg=1, c=c); b.parent = door
    # side door + small window, blank yellow sign over the bay
    k.box("OF_sdoorHole", (.9, .12, 2.1), (2.9, yF + .05, 1.05), M["dark"], bevel=0, c=c)
    k.box("OF_sdoor", (.84, .05, 2.0), (3.15, yF - .05, 1.02), M["door"], bevel=.01, seg=2, rot=(0, 0, math.radians(-35)), c=c)
    L.boarded_window("OF_winR", 1.0, .8, (W / 2, yF + 3.5, 2.3), M["glass"], M["frame"], M["wood"], (1, 0, 0), c=c, seed=31, n_planks=2)
    k.box("OF_sign", (4.4, .06, .9), (-.8, yF - .06, H - .05 + .5), m_sign, bevel=.01, seg=1, c=c)
    for x, z, w, h in ((0, .45, 4.4, .07), (0, -.45, 4.4, .07), (-2.2, 0, .07, .9), (2.2, 0, .07, .9)):
        k.box("OF_signB", (w + .05, .05, h + .05), (-.8 + x, yF - .09, H + .45 + z), m_signB, bevel=0, c=c)
    k.box("OF_signPlate", (1.6, .06, .5), (3.0, yF - .06, 2.9), M["signpanel"], bevel=.01, seg=1, rot=(0, 0, 0), c=c)
    # car on blocks in front of the bay, tyre stacks, drums, hoist beam, tool rack
    car_wreck("OF_car", (-1.0, yF - 2.3, 0), m_car, M["dark"], M["tire"], M["concreteD"], rot=math.radians(-78), c=c)
    tire_stack("OF_tireA", 3.6, yF - 1.0, 4, M["tire"], c, seed=1)
    tire_stack("OF_tireB", 4.2, yF - 1.9, 3, M["tire"], c, seed=2)
    tire_stack("OF_tireC", 3.2, yF - 2.0, 2, M["tire"], c, seed=3)
    L.tire("OF_tireLoose", (-3.8, yF - 3.2, .32), M["tire"], rot=(math.radians(85), 0, .9), c=c)
    L.drum("OF_drum0", (-4.1, yF - .8, 0), M["drum"], rot=(0, 0, .4), c=c)
    L.drum("OF_drum1", (-4.1, yF + .0, 0), M["rust"], rot=(0, 0, 1.1), c=c)
    L.ground(L.drum("OF_drum2", (-3.6, yF - 1.6, .29), M["drum"], rot=(math.radians(90), 0, .4), c=c))
    puddle("OF_oil0", (-1.4, yF - 2.4, 0), M["oil"], 1.4, .9, .3, c=c)
    puddle("OF_oil1", (1.4, yF - 1.0, 0), M["oil"], .8, .6, 1.2, c=c)
    puddle("OF_oil2", (-3.9, yF - 1.0, 0), M["oil"], .7, .5, .4, c=c)
    L.pallet("OF_pallet", (4.0, yF + 3.8, 0), M["wood"], rot=(0, 0, .2), c=c)
    k.crate("OF_crate", (4.0, yF + 3.8, .15), m=M["wood"], c=c, rot_z=.6)
    L.dead_bush("OF_bush", (-4.2, yF + 4.6, 0), M["twig"], r=.5, n=16, c=c, seed=33)
    pts = [(-4.4, -4.5), (-2.6, -4.9), (.5, -4.8), (2.2, -4.6), (4.4, -4.3), (4.4, -3.0), (-4.5, -2.6), (4.4, 1.0), (-4.5, 2.6), (4.4, 3.0),
           (-4.4, 4.6), (-1.0, 5.1), (1.5, 5.0), (3.6, 4.9), (-1.8, -3.9), (4.5, 2.0)]
    L.scatter_tufts("OF", pts, c, seed=71, size=.85)
    for o in c.objects:
        if o.name.startswith(("OF_tire", "OF_pallet")): L.ground(o)
    for i, (x, y, a) in enumerate(((2.3, -3.9, .3), (2.6, -3.75, 1.0))):
        L.brick(f"OF_brick{i}", (x, y, .095), M["brick"], rot=(0, 0, a), c=c)
    return c

# ================================================================== 4. POSTO - derelict gas station
def build_posto():
    c = new_col("LOT Posto"); M = mats(); show("LOT Posto")
    bpy.context.scene.cursor.location = (0, 0, 0)
    m_fascia = k.stripes("LOT2_PostoFascia", (.80, .26, .22, 1), (.92, .90, .84, 1), width=1.2, axis='X', rough=.85)
    m_fasciaY = k.stripes("LOT2_PostoFasciaY", (.80, .26, .22, 1), (.92, .90, .84, 1), width=1.2, axis='Y', rough=.85)
    m_kiosk = L.plaster("LOT2_Kiosk", (.92, .90, .84, 1), under=(.60, .50, .42, 1), damage=.45, brick_under=True, zband=.8, band=(.80, .26, .22, 1))
    m_pump = paint_faded("LOT2_Pump", (.82, .80, .74, 1), rustiness=.45)
    m_pumpR = paint_faded("LOT2_PumpRed", (.78, .28, .22, 1), rustiness=.5)
    m_totem = paint_faded("LOT2_Totem", (.78, .28, .22, 1), rustiness=.45)
    m_asph = asphalt("LOT2_PostoAsphalt", lines_y=(-2.1, 2.1), fade=.4)
    # forecourt
    L.gbox("PST_pad", (9.6, 11.0, .05), (0, 0, .02), m_asph, bevel=.02, c=c)
    # canopy on 4 pillars
    cz, cw, cd, ct = 4.6, 8.4, 5.6, .5
    cy = -1.4
    for x in (-3.0, 3.0):
        for y in (cy - 1.7, cy + 1.7):
            L.gbox("PST_pillar", (.42, .42, cz), (x, y, cz / 2), M["concreteD"], bevel=.015, c=c)
            L.gbox("PST_pillarB", (.6, .6, .5), (x, y, .25), M["concrete"], bevel=.015, c=c)
    L.gbox("PST_canopy", (cw, cd, ct - .2), (0, cy, cz + (ct - .2) / 2 + .1), M["concreteD"], bevel=.02, c=c)
    L.gbox("PST_canopyTop", (cw + .2, cd + .2, .12), (0, cy, cz + ct + .06), M["gutter"], bevel=.01, c=c)
    # fascia strips (faded red/white)
    L.gbox("PST_fasciaF", (cw + .2, .12, ct + .25), (0, cy - cd / 2 - .02, cz + ct / 2 + .05), m_fascia, bevel=.01, c=c)
    L.gbox("PST_fasciaB", (cw + .2, .12, ct + .25), (0, cy + cd / 2 + .02, cz + ct / 2 + .05), m_fascia, bevel=.01, c=c)
    L.gbox("PST_fasciaL", (.12, cd + .2, ct + .25), (-cw / 2 - .02, cy, cz + ct / 2 + .05), m_fasciaY, bevel=.01, c=c)
    L.gbox("PST_fasciaR", (.12, cd + .2, ct + .25), (cw / 2 + .02, cy, cz + ct / 2 + .05), m_fasciaY, bevel=.01, c=c)
    # a fascia panel hanging loose at the front right corner
    hp = k.box("PST_fasciaLoose", (1.6, .1, ct + .25), (0, 0, 0), m_fascia, bevel=.01, seg=1, c=c)
    hp.data.transform(Matrix.Translation((.8, 0, -(ct + .25) / 2))); hp.location = (2.6, cy - cd / 2 - .16, cz + ct + .12); hp.rotation_euler = (math.radians(-12), math.radians(18), 0)
    # 2 pump islands
    for ix, x in enumerate((-1.9, 1.9)):
        L.gbox(f"PST_island{ix}", (1.4, 4.2, .18), (x, cy, .09), M["concrete"], bevel=.03, c=c)
        pump(f"PST_pump{ix}a", (x, cy - 1.1, .18), m_pump if ix == 0 else m_pumpR, M["dark"], M["signpanel"], rot=0, c=c)
        pump(f"PST_pump{ix}b", (x, cy + 1.1, .18), m_pumpR if ix == 0 else m_pump, M["dark"], M["signpanel"], rot=math.radians(180), c=c)
        L.gbox(f"PST_bollard{ix}", (.14, .14, .9), (x - .55, cy - 1.95, .45), M["rust"], bevel=.01, c=c)
        L.gbox(f"PST_bollard{ix}b", (.14, .14, .9), (x + .55, cy + 1.95, .45), M["rust"], bevel=.01, c=c)
    # kiosk at the back
    kw, kd, kh = 4.6, 3.2, 3.0
    ky = 3.6
    L.gbox("PST_kiosk", (kw, kd, kh), (0, ky, kh / 2), m_kiosk, bevel=.015, c=c)
    L.gbox("PST_kioskRoof", (kw + .5, kd + .5, .16), (0, ky, kh + .08), M["concreteD"], bevel=.015, c=c)
    L.gbox("PST_kioskParapet", (kw + .5, .18, .35), (0, ky - kd / 2 - .16, kh + .33), m_kiosk, bevel=.01, c=c)
    k.box("PST_kioskDoorHole", (.95, .12, 2.1), (1.4, ky - kd / 2 + .05, 1.05), M["dark"], bevel=0, c=c)
    k.box("PST_kioskDoor", (.9, .05, 2.0), (1.1, ky - kd / 2 - .08, 1.02), M["door"], bevel=.01, seg=2, rot=(0, 0, math.radians(30)), c=c)
    L.boarded_window("PST_kioskWin", 2.0, 1.2, (-.9, ky - kd / 2, 1.7), M["glass"], M["frame"], M["wood"], (0, -1, 0), c=c, seed=41, n_planks=2)
    L.boarded_window("PST_kioskWinR", 1.0, .9, (kw / 2, ky + .3, 1.8), M["glass"], M["frame"], M["wood"], (1, 0, 0), c=c, seed=42)
    k.cyl("PST_tank", .45, .65, (1.5, ky + .6, kh + .16 + .325), M["drum"], verts=14, bevel=.02, c=c)
    # totem sign at the front-left corner: pole + blank panel + price box, leaning a little
    tx, ty = -4.1, -4.6
    L.gbox("PST_totemBase", (.9, .9, .3), (tx, ty, .15), M["concreteD"], bevel=.02, c=c)
    pole = k.box("PST_totemPole", (.36, .36, 5.6), (0, 0, 0), M["rust"], bevel=.012, seg=2, c=c)
    pole.data.transform(Matrix.Translation((0, 0, 2.8))); pole.location = (tx, ty, .3); pole.rotation_euler = (0, math.radians(-4), 0)
    sign = k.box("PST_totemSign", (1.9, .32, 1.9), (0, 0, 0), m_totem, bevel=.03, seg=2, c=c)
    sign.location = (tx + .3, ty, 6.6); sign.rotation_euler = (0, math.radians(-4), 0)
    k.box("PST_totemPanel", (1.5, .05, 1.4), (0, -.19, 0), M["signpanel"], bevel=.01, seg=1, c=c).parent = sign
    k.box("PST_totemPanelB", (1.5, .05, 1.4), (0, .19, 0), M["signpanel"], bevel=.01, seg=1, c=c).parent = sign
    k.box("PST_price", (1.3, .26, .8), (0, 0, -1.5), M["signpanel"], bevel=.02, seg=2, c=c).parent = sign
    k.box("PST_priceB", (1.38, .22, .1), (0, 0, -1.05), M["rust"], bevel=.01, seg=1, c=c).parent = sign
    # props: drums, a tyre, puddles, weeds through the cracks, bricks, bins
    L.drum("PST_drum0", (4.2, 1.3, 0), M["drum"], rot=(0, 0, .3), c=c)
    L.drum("PST_drum1", (4.1, 2.0, 0), M["rust"], rot=(0, 0, 1.0), c=c)
    L.tire("PST_tire0", (-4.0, 2.5, .10), M["tire"], rot=(0, 0, .2), c=c)
    L.tire("PST_tire1", (-4.0, 2.5, .30), M["tire"], rot=(0, .06, 1.1), c=c)
    puddle("PST_pud0", (1.0, -4.0, 0), M["puddle"], 1.6, 1.0, .2, c=c)
    puddle("PST_pud1", (-2.6, .9, 0), M["puddle"], 1.1, .8, -.5, c=c)
    puddle("PST_oil", (1.9, -2.6, 0), M["oil"], .7, .5, .4, c=c)
    k.cyl("PST_bin", .26, .75, (3.6, -3.8, .375), M["rust"], verts=12, bevel=.012, c=c)
    L.ground(L.drum("PST_drum2", (-3.0, -3.3, .29), M["drum"], rot=(math.radians(90), 0, 1.2), c=c))
    pts = [(-4.4, -3.0), (-4.4, -1.0), (-4.4, 4.2), (-3.2, 4.9), (-1.0, 5.2), (2.4, 5.1), (4.3, 4.6), (4.4, -1.2), (4.4, -2.6), (2.8, -4.9),
           (-1.6, -5.0), (.3, -4.9), (-4.3, .6), (-2.9, 3.8), (3.6, 3.6), (4.3, .2)]
    L.scatter_tufts("PST", pts, c, seed=81, size=.8)
    L.dead_bush("PST_bush", (-3.6, 4.4, 0), M["twig"], r=.5, n=16, c=c, seed=43)
    for i, (x, y, a) in enumerate(((3.4, -4.6, .3), (3.7, -4.45, 1.0))):
        L.brick(f"PST_brick{i}", (x, y, .095), M["brick"], rot=(0, 0, a), c=c)
    return c

# ================================================================== 5. GARAGEM - row of 4 lock-up garages
def build_garagem():
    c = new_col("LOT Garagem"); M = mats(); show("LOT Garagem")
    bpy.context.scene.cursor.location = (0, 0, 0)
    m_wall = L.plaster("LOT2_GarWall", (.80, .78, .70, 1), under=(.60, .50, .42, 1), damage=.5, brick_under=True, zband=.4, band='brick', crack_scale=2.0)
    cols = (((.30, .45, .62, 1), "Blue"), ((.36, .56, .36, 1), "Green"), ((.74, .30, .24, 1), "Red"), ((.84, .66, .22, 1), "Yellow"))
    m_doors = [L.corrugated(f"LOT2_GarDoor{n}", col, (.50, .26, .12, 1), .45 + .05 * i, axis='Z', pitch=.10) for i, (col, n) in enumerate(cols)]
    m_drive = cracked("LOT2_Drive", (.64, .62, .58, 1), 2.2, .45, stains=.4, stain=(.30, .28, .26, 1))
    W, D, H, T = 9.4, 5.2, 2.9, .22
    yF = -D / 2 + 1.6
    L.gbox("GAR_pad", (9.6, 11.0, .05), (0, 0, .02), m_drive, bevel=.02, c=c)
    L.gbox("GAR_wallB", (W, T, H), (0, yF + D - T / 2, H / 2), m_wall, bevel=.012, c=c)
    L.gbox("GAR_wallL", (T, D, H), (-W / 2 + T / 2, yF + D / 2, H / 2), m_wall, bevel=.012, c=c)
    L.gbox("GAR_wallR", (T, D, H), (W / 2 - T / 2, yF + D / 2, H / 2), m_wall, bevel=.012, c=c)
    L.gbox("GAR_inner", (W - .4, D - .4, H - .2), (0, yF + D / 2, (H - .2) / 2), M["shadow"], bevel=0, c=c)
    L.gbox("GAR_roof", (W + .3, D + .3, .16), (0, yF + D / 2, H), M["concreteD"], bevel=.015, c=c)
    L.gbox("GAR_parapet", (W + .3, .18, .4), (0, yF + .09, H + .2), m_wall, bevel=.01, c=c)
    L.gbox("GAR_parapetB", (W + .3, .18, .4), (0, yF + D - .09, H + .2), m_wall, bevel=.01, c=c)
    L.gbox("GAR_lintel", (W, .26, .32), (0, yF + .13, H - .16), M["concreteD"], bevel=.012, c=c)
    n = 4; pw = W / n
    for i in range(n):
        x = -W / 2 + pw * (i + .5)
        L.gbox(f"GAR_pier{i}", (.36, T + .05, H - .3), (x - pw / 2 + .18 if i == 0 else x - pw / 2, yF + T / 2, (H - .3) / 2), m_wall, bevel=.01, c=c)
        dw, dh = pw - .42, H - .36
        k.box(f"GAR_doorHole{i}", (dw, .10, dh), (x, yF + .04, dh / 2), M["dark"], bevel=0, c=c)
        if i == 2:   # red door half open, bent
            L.gbox(f"GAR_door{i}", (dw - .04, .05, dh * .45), (x, yF - .02, dh - dh * .45 / 2), m_doors[i], bevel=.004, seg=1, c=c)
            cb = k.box(f"GAR_doorBent{i}", (dw - .04, .05, .5), (0, 0, 0), m_doors[i], bevel=.004, seg=1, c=c)
            cb.data.transform(Matrix.Translation((0, 0, -.25))); cb.location = (x, yF - .04, dh * .55); cb.rotation_euler = (math.radians(-28), 0, 0)
            k.cyl(f"GAR_roll{i}", .14, dw, (x, yF - .08, dh + .02), M["rust"], rot=(0, math.radians(90), 0), verts=12, bevel=.01, c=c)
        else:
            L.gbox(f"GAR_door{i}", (dw - .04, .05, dh - .05), (x, yF - .02, (dh - .05) / 2 + .03), m_doors[i], bevel=.004, seg=1, c=c)
            k.box(f"GAR_doorBar{i}", (dw - .04, .06, .08), (x, yF - .06, .10), M["steel"], bevel=.004, seg=1, c=c)
            k.box(f"GAR_handle{i}", (.22, .05, .05), (x, yF - .07, .95), M["steel"], bevel=.006, seg=1, c=c)
        if i in (0, 3):
            k.box(f"GAR_num{i}", (.26, .03, .32), (x - pw / 2 + .18 + (.0 if i == 0 else .0), yF - .02, H - .9), M["signpanel"], bevel=.004, seg=1, c=c)
    L.gbox("GAR_pierEnd", (.36, T + .05, H - .3), (W / 2 - .18, yF + T / 2, (H - .3) / 2), m_wall, bevel=.01, c=c)
    # weeds on the flat roof + a loose tyre and bricks up there, drain pipes
    pts_roof = [(-4.0, yF + 1.0), (-2.2, yF + 3.8), (.6, yF + 2.2), (2.8, yF + 4.2), (4.2, yF + 1.5), (-.9, yF + 4.4), (3.9, yF + 3.0)]
    for i, (x, y) in enumerate(pts_roof):
        L.tuft(f"GAR_rooftuft{i}", (x, y, H + .16), M["grassdry"] if i % 2 else M["grass"], n=7, h=.45, c=c, seed=90 + i)
    L.tire("GAR_rooftire", (1.8, yF + 1.2, H + .26), M["tire"], rot=(0, 0, .4), c=c)
    for s in (-1, 1):
        k.tube("GAR_down", (s * (W / 2 + .06), yF + D - .3, H + .2), (s * (W / 2 + .06), yF + D - .3, .2), .045, M["gutter"], verts=8, c=c)
    # ground: broken shopping cart on its side, puddles, boxes, a drum, weeds along the edges
    cart = shopping_cart("GAR_cart", (2.2, yF - 2.4, 0), M["chrome"], rot=(math.radians(90), 0, math.radians(35)), c=c)
    L.ground(cart, .02)
    puddle("GAR_pud0", (-2.2, yF - 2.2, 0), M["puddle"], 1.7, 1.0, .3, c=c)
    puddle("GAR_pud1", (.4, yF - 3.2, 0), M["puddle"], 1.0, .7, -.6, c=c)
    puddle("GAR_pud2", (3.8, yF - .6, 0), M["puddle"], .9, .6, .9, c=c)
    L.tire("GAR_tire0", (-4.1, yF - 1.4, .10), M["tire"], rot=(0, 0, .2), c=c)
    L.tire("GAR_tire1", (-4.1, yF - 1.4, .30), M["tire"], rot=(0, .06, 1.1), c=c)
    L.drum("GAR_drum", (4.2, yF + 5.6, 0), M["drum"], rot=(0, 0, .5), c=c)
    box_pile("GAR_box", (-3.6, yF - 3.0, 0), M["cardboard"], c, seed=9, n=2)
    L.dead_bush("GAR_bush", (-4.0, yF + 5.7, 0), M["twig"], r=.45, n=16, c=c, seed=53)
    pts = [(-4.4, -4.6), (-2.8, -4.9), (-1.2, -4.7), (.6, -5.0), (2.6, -4.8), (4.3, -4.5), (4.4, -3.4), (-4.5, -3.6), (-4.4, .2), (4.4, 1.0),
           (-4.4, 4.0), (-2.0, 5.0), (.5, 5.1), (2.5, 4.9), (4.3, 4.3), (-4.3, 2.4), (4.4, 2.8)]
    L.scatter_tufts("GAR", pts, c, seed=91, size=.85)
    for i, (x, y, a) in enumerate(((-.6, -4.3, .3), (-.3, -4.15, 1.0), (3.4, -3.9, .8))):
        L.brick(f"GAR_brick{i}", (x, y, .095), M["brick"], rot=(0, 0, a), c=c)
    return c

# ================================================================== 6. MATO - overgrown empty plot
def build_mato():
    c = new_col("LOT Mato"); M = mats(); show("LOT Mato")
    bpy.context.scene.cursor.location = (0, 0, 0)
    rnd = random.Random(7)
    m_path = k.mat("LOT2_Path", (.66, .56, .40, 1), rough=.95, var=.15, scale=3)
    L.pad("MATO_pad", 9.6, 11.0, c)
    # grass patches over most of the plot
    for i, (x, y, sx, sy, a) in enumerate(((-2.6, -3.2, 2.4, 1.8, .3), (2.2, -2.4, 2.6, 1.9, -.4), (-2.4, 1.2, 2.5, 2.2, .8), (2.6, 2.4, 2.2, 2.2, .2),
                                           (0.0, 4.2, 3.2, 1.2, .0), (-3.6, 3.9, 1.1, 1.2, .5), (3.9, -4.4, 1.0, .9, .1), (-.2, -1.0, 1.6, 1.3, 1.0))):
        grass_patch(f"MATO_grass{i}", (x, y, 0), M["grasspatch"], sx, sy, a, c=c)
    # dirt path winding from the front to the back-right
    for i, (x, y, L_, a) in enumerate(((-.2, -4.2, 2.1, .25), (.7, -2.2, 2.4, -.35), (.4, 0.0, 2.2, .3), (1.4, 1.9, 2.4, -.5), (2.6, 3.6, 2.2, -.9))):
        p = k.box(f"MATO_path{i}", (1.1, L_, .03), (x, y, .055), m_path, rot=(0, 0, a), bevel=.01, seg=1, c=c)
    # crumbling brick wall along the back and the left side, with gaps and fallen bricks
    segs = [((-4.7, 5.3), (-2.2, 5.3), 1.9), ((-2.2, 5.3), (-.6, 5.3), 1.1), ((-.6, 5.3), (2.4, 5.3), 1.8), ((2.4, 5.3), (4.7, 5.3), 1.3),
            ((-4.7, 5.3), (-4.7, 2.6), 1.6), ((-4.7, 2.6), (-4.7, .4), 1.0), ((-4.7, .4), (-4.7, -2.4), 1.5)]
    for i, (a, b, h) in enumerate(segs):
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy); ang = math.atan2(dy, dx)
        o = k.box(f"MATO_wall{i}", (ln, .24, h), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, h / 2), M["brickD"], rot=(0, 0, ang), bevel=.012, seg=1, c=c)
        flat(o)
    for i in range(16):
        x = rnd.uniform(-4.4, 4.4); y = 5.3 - rnd.uniform(.2, 1.2)
        if i > 10: x = -4.7 + rnd.uniform(.2, 1.0); y = rnd.uniform(-2.2, 4.8)
        L.brick(f"MATO_brick{i}", (x, y, .035 + (.07 if i % 5 == 0 else 0)), M["brick"], rot=(rnd.uniform(-.2, .2), rnd.uniform(-.2, .2), rnd.uniform(0, 3)), c=c)
    for i, (x, y, s) in enumerate(((-1.4, 4.6, .22), (-4.1, 1.6, .2), (3.6, 4.5, .18))):
        L.chunk(f"MATO_chunk{i}", (x, y, .08), M["brick"], s=s, c=c, seed=i + 3)
    # crooked tree, bushes, lots of tall tufts
    crooked_tree("MATO_tree", (2.0, 2.4, 0), M["twig"], M["green"], M["greenD"], c=c, seed=2, h=3.9, lean=.22)
    bush("MATO_bush0", (-3.2, 3.9, 0), M["green"], M["greenD"], r=.85, c=c, seed=1)
    bush("MATO_bush1", (-3.5, -1.2, 0), M["greenD"], M["green"], r=.7, c=c, seed=2)
    bush("MATO_bush2", (3.6, -1.6, 0), M["green"], M["greenD"], r=.6, c=c, seed=3)
    bush("MATO_bush3", (-1.0, 2.8, 0), M["greenD"], M["green"], r=.55, c=c, seed=4)
    L.dead_bush("MATO_dead0", (3.9, .6, 0), M["twig"], r=.6, n=20, c=c, seed=5)
    L.dead_bush("MATO_dead1", (-2.2, -4.6, 0), M["twig"], r=.5, n=16, c=c, seed=6)
    pts = []
    for i in range(44):
        x, y = rnd.uniform(-4.3, 4.3), rnd.uniform(-4.9, 4.6)
        if abs(x - (.3 + y * .18)) < .75 and y < 2.0: continue   # keep the path clear
        pts.append((x, y))
    L.scatter_tufts("MATO", pts, c, seed=101, dry_every=3, size=1.35)
    # old mattress leaning on the back wall, tyres, a bucket
    mt = k.box("MATO_mattress", (1.9, .24, 1.4), (0, 0, 0), M["mattress"], bevel=.05, seg=3, c=c)
    mt.data.transform(Matrix.Translation((0, 0, .7))); mt.location = (1.0, 4.85, 0); mt.rotation_euler = (math.radians(-12), 0, .1)
    L.tire("MATO_tire0", (-3.6, 2.0, .10), M["tire"], rot=(0, 0, .2), c=c)
    L.tire("MATO_tire1", (-3.6, 2.0, .30), M["tire"], rot=(0, .05, 1.1), c=c)
    L.tire("MATO_tire2", (2.2, -4.0, .32), M["tire"], rot=(math.radians(80), 0, .6), c=c)
    L.tire("MATO_tire3", (-1.2, 1.0, .10), M["tire"], rot=(0, 0, .9), c=c)
    L.ground(k.cyl("MATO_bucket", .13, .30, (-2.6, -3.0, .13), M["drum"], rot=(math.radians(100), 0, .7), verts=12, bevel=.01, r2=.11, c=c))
    for o in c.objects:
        if o.name.startswith(("MATO_tire", "MATO_chunk", "MATO_bush")): L.ground(o)
    return c

# ================================================================== 7. FABRICA - small old factory
def build_fabrica():
    c = new_col("LOT Fabrica"); M = mats(); show("LOT Fabrica")
    bpy.context.scene.cursor.location = (0, 0, 0)
    m_brick = M["brickD"]
    mR = L.corrugated("LOT2_FabRoof", (.62, .64, .62, 1), (.52, .27, .12, 1), .35, axis='X')
    m_sign = L.plaster("LOT2_FabSign", (.92, .90, .84, 1), under=(.74, .70, .62, 1), damage=.4, cracks=False)
    W, D, H, T = 8.6, 7.2, 4.4, .3
    yF = -D / 2 + .8
    L.gbox("FAB_pad", (9.6, 11.0, .05), (0, 0, .02), M["apron"], bevel=.02, c=c)
    L.gbox("FAB_wallF", (W, T, H), (0, yF + T / 2, H / 2), m_brick, bevel=.015, c=c)
    L.gbox("FAB_wallB", (W, T, H), (0, yF + D - T / 2, H / 2), m_brick, bevel=.015, c=c)
    L.gbox("FAB_wallL", (T, D - 2 * T, H), (-W / 2 + T / 2, yF + D / 2, H / 2), m_brick, bevel=.015, c=c)
    L.gbox("FAB_wallR", (T, D - 2 * T, H), (W / 2 - T / 2, yF + D / 2, H / 2), m_brick, bevel=.015, c=c)
    L.gbox("FAB_inner", (W - .6, D - .6, H + .8), (0, yF + D / 2, (H + .8) / 2), M["shadow"], bevel=0, c=c)
    # brick pilasters + concrete band
    for x in (-W / 2 + .25, -W / 2 + W / 3, W / 2 - W / 3, W / 2 - .25):
        for y, s in ((yF, -1), (yF + D, 1)):
            L.gbox("FAB_pil", (.5, .16, H), (x, y + s * .08, H / 2), m_brick, bevel=.012, c=c)
    L.gbox("FAB_bandF", (W + .2, .12, .25), (0, yF - .06, 3.0), M["concreteD"], bevel=.01, c=c)
    L.gbox("FAB_cap", (W + .2, D + .2, .12), (0, yF + D / 2, H), M["concreteD"], bevel=.012, c=c)
    # saw-tooth roof: 3 teeth across the depth (slopes face -Y, glazed faces look +Y / back)
    nt_ = 3; dt = D / nt_; rise = 1.3
    for i in range(nt_):
        y0 = yF + dt * i
        Lslope = math.hypot(dt, rise); pitch = math.atan2(rise, dt)
        Mw = Matrix.Translation((0, y0 + dt, H + .06)) @ Matrix.Rotation(math.pi - pitch, 4, 'X')
        holes = [(1.0, .6, 2.2, 1.4)] if i == 1 else ([(-3.3, 1.0, -2.3, 1.9)] if i == 2 else [])
        L.slab(f"FAB_tooth{i}", W + .3, Lslope, .06, mR, Mw, holes, c, m_purlin=M["steel"])
        # vertical glazed face at the high (front) end facing -Y, with missing panes
        gy = y0
        L.pane_window(f"FAB_sky{i}", W - 1.0, rise - .25, (0, gy - .04, H + .06 + rise / 2 - .02), M["glass"], M["frame"], (0, -1, 0), c=c, cols=5, rows=1,
                      missing=[(1, 0), (4, 0)] if i == 0 else ([(2, 0), (3, 0)] if i == 1 else [(0, 0), (3, 0)]))
        L.gbox(f"FAB_toothBeam{i}", (W + .3, .14, .14), (0, gy, H + .06 + rise), M["steel"], bevel=.008, c=c)
        # triangular ends on both sides
        for x, nm in ((-W / 2 + T / 2, "L"), (W / 2 - T / 2, "R")):
            L.poly_prism(f"FAB_toothEnd{i}{nm}", [(y0 - (yF + D / 2), H - .02), (y0 + dt - (yF + D / 2), H - .02), (y0 - (yF + D / 2), H + rise)], T, (x, yF + D / 2, 0), m_brick, axis='X', c=c)
    # tall brick chimney (back-right), with iron bands and a broken crown
    cx, cy = 3.2, yF + D - 1.3
    L.gbox("FAB_chimBase", (1.3, 1.3, .9), (cx, cy, H + .45), m_brick, bevel=.015, c=c)
    k.cyl("FAB_chim", .50, 7.65 - H - .9, (cx, cy, H + .9 + (7.65 - H - .9) / 2), m_brick, verts=14, bevel=.01, r2=.38, c=c)
    k.cyl("FAB_chimCrown", .48, .25, (cx, cy, 7.65 + .1), M["concreteD"], verts=14, bevel=.02, c=c)
    for z in (5.6, 6.8):
        k.cyl("FAB_chimBand", .49, .08, (cx, cy, z), M["rust"], verts=14, bevel=.0, c=c)
    L.chunk("FAB_chimChunk", (cx + .3, cy - .2, 7.72), M["brick"], s=.14, c=c, seed=8)
    # rusty pipes along the right wall and over to the chimney, valve wheel
    px = W / 2 + .14
    k.tube("FAB_pipe0", (px, yF + .6, .4), (px, yF + .6, 3.6), .09, M["rust"], verts=8, c=c)
    k.tube("FAB_pipe1", (px, yF + .6, 3.6), (px, yF + D - .4, 3.6), .09, M["rust"], verts=8, c=c)
    k.ball("FAB_pipeJ0", .11, (px, yF + .6, 3.6), M["rust"], sub=1, c=c)
    k.tube("FAB_pipe2", (px, yF + 2.4, 3.6), (px, yF + 2.4, .5), .07, M["rust"], verts=8, c=c)
    k.tube("FAB_pipe3", (px, yF + 2.4, 1.2), (px + .4, yF + 2.4, 1.2), .07, M["rust"], verts=8, c=c)
    k.tube("FAB_pipe4", (px + .4, yF + 2.4, 1.2), (px + .4, yF + 2.4, .0), .07, M["rust"], verts=8, c=c)
    k.cyl("FAB_valve", .16, .04, (px + .4, yF + 2.4, .7), M["rust"], rot=(0, math.radians(90), 0), verts=12, c=c)
    k.tube("FAB_pipe5", (px, yF + D - .4, 3.6), (px, yF + D - .4, .3), .09, M["rust"], verts=8, c=c)
    k.tube("FAB_pipeTop", (-W / 2 - .2, yF + .45, 5.0), (W / 2 + .2, yF + .45, 5.0), .08, M["rust"], verts=8, c=c)
    for x in (-3.0, 0.0, 3.0):
        k.box("FAB_pipeBr", (.12, .12, .5), (x, yF + .45, H + .45), M["steel"], bevel=.004, seg=1, c=c)
    # front: big arched-ish door (dark + leaning timber door), windows with missing panes, blank sign
    k.box("FAB_doorHole", (2.4, .14, 3.0), (-2.0, yF + .05, 1.5), M["dark"], bevel=0, c=c)
    L.gbox("FAB_doorLintel", (2.8, .24, .3), (-2.0, yF + .12, 3.15), M["concreteD"], bevel=.012, c=c)
    dr = k.box("FAB_door", (1.15, .06, 2.9), (0, 0, 0), M["woodZ"], bevel=.01, seg=1, c=c)
    dr.data.transform(Matrix.Translation((.575, 0, 1.45))); dr.location = (-3.2, yF - .05, .05); dr.rotation_euler = (0, math.radians(3), math.radians(-30))
    L.gbox("FAB_door2", (1.15, .06, 2.9), (-1.4, yF - .04, 1.45), M["woodZ"], bevel=.01, c=c)
    for i, x in enumerate((1.0, 2.9)):
        L.pane_window(f"FAB_winF{i}", 1.3, 1.6, (x, yF, 2.0), M["glass"], M["frame"], (0, -1, 0), c=c, cols=2, rows=2, missing=[(0, 1), (1, 1)] if i else [(1, 0)])
    for i, y in enumerate((yF + 1.5, yF + 3.6, yF + 5.7)):
        L.pane_window(f"FAB_winL{i}", 1.3, 1.6, (-W / 2, y, 2.0), M["glass"], M["frame"], (-1, 0, 0), c=c, cols=2, rows=2, missing=[(0, 1)] if i == 1 else [(1, 1), (0, 0)])
    k.box("FAB_sign", (3.6, .06, .9), (1.9, yF - .06, 3.75), m_sign, bevel=.01, seg=1, c=c)
    for x, z, w, h in ((0, .45, 3.6, .07), (0, -.45, 3.6, .07), (-1.8, 0, .07, .9), (1.8, 0, .07, .9)):
        k.box("FAB_signB", (w + .05, .05, h + .05), (1.9 + x, yF - .09, 3.75 + z), M["steel"], bevel=0, c=c)
    # props: pallet stack, drums, crates, tufts, bricks
    for i in range(2):
        L.pallet(f"FAB_pallet{i}", (3.4, yF - 1.6, .15 * i), M["wood"], rot=(0, 0, .05 * i), broken=(i == 1), c=c)
    L.ground(L.pallet("FAB_palletLean", (4.3, yF + 0.0, .55), M["wood"], rot=(0, math.radians(75), .3), c=c))
    L.drum("FAB_drum0", (-3.9, yF - 1.4, 0), M["drum"], rot=(0, 0, .4), c=c)
    L.ground(L.drum("FAB_drum2", (-4.0, yF + 3.0, .29), M["drum"], rot=(math.radians(90), 0, .3), c=c))
    box_pile("FAB_box", (1.0, yF - 1.3, 0), M["cardboard"], c, seed=14, n=2)
    L.dead_bush("FAB_bush", (-4.2, yF + 5.5, 0), M["twig"], r=.5, n=16, c=c, seed=63)
    pts = [(-4.4, -4.8), (-2.4, -5.0), (-.6, -4.7), (1.6, -5.0), (3.4, -4.8), (4.4, -4.2), (4.4, -2.8), (-4.5, -2.8), (-4.5, .5), (4.4, 1.6),
           (-4.4, 2.8), (4.4, 3.8), (-2.6, 5.1), (.0, 5.1), (2.6, 5.0), (-4.3, 4.5), (2.0, -3.6), (-1.8, -3.5)]
    L.scatter_tufts("FAB", pts, c, seed=111, size=.9)
    for i, (x, y, a) in enumerate(((-1.6, -4.1, .3), (-1.3, -3.95, 1.0), (3.9, -3.6, .8))):
        L.brick(f"FAB_brick{i}", (x, y, .095), M["brick"], rot=(0, 0, a), c=c)
    return c

# ================================================================== 8. PATIO - old truck yard
def build_patio():
    c = new_col("LOT Patio"); M = mats(); show("LOT Patio")
    bpy.context.scene.cursor.location = (0, 0, 0)
    m_asph = asphalt("LOT2_PatioAsphalt", lines_x=(-3.2, -.6, 2.0), lines_y=(-4.6,), fade=.5)
    m_cont = L.corrugated("LOT2_Container", (.72, .34, .22, 1), (.45, .22, .10, 1), .55, axis='X', pitch=.25)
    m_contEnd = L.corrugated("LOT2_ContainerEnd", (.72, .34, .22, 1), (.45, .22, .10, 1), .55, axis='Y', pitch=.25)
    m_truckBox = paint_faded("LOT2_TruckBox", (.86, .86, .82, 1), rustiness=.4)
    m_truckCab = paint_faded("LOT2_TruckCab", (.30, .48, .62, 1), rustiness=.5)
    m_booth = L.plaster("LOT2_Booth", (.92, .88, .76, 1), under=(.60, .50, .42, 1), damage=.5, brick_under=True, zband=.5, band=(.40, .50, .56, 1))
    L.gbox("PAT_pad", (9.6, 11.0, .05), (0, 0, .02), m_asph, bevel=.02, c=c)
    # box truck on blocks (no wheels), parked diagonally at the left
    tx, ty, ta = -2.6, .9, math.radians(100)
    parts = [k.box("PAT_chassis", (6.6, 1.1, .25), (0, 0, .78), M["dark"], bevel=.02, seg=1),
             k.box("PAT_box", (4.6, 2.4, 2.5), (1.0, 0, .9 + 1.25), m_truckBox, bevel=.04, seg=2),
             k.box("PAT_boxBand", (4.64, 2.44, .18), (1.0, 0, 1.5), m_truckCab, bevel=.02, seg=1),
             k.box("PAT_boxPanel", (2.0, .04, .9), (1.0, -1.23, 2.4), M["signpanel"], bevel=.01, seg=1),
             k.box("PAT_cab", (2.0, 2.3, 1.9), (-2.3, 0, .9 + .95), m_truckCab, bevel=.10, seg=3),
             k.box("PAT_cabWin", (.3, 2.0, .8), (-3.2, 0, 2.3), M["dark"], bevel=.02, seg=1, rot=(0, math.radians(-12), 0)),
             k.box("PAT_cabWinL", (1.0, .06, .7), (-2.1, -1.17, 2.3), M["dark"], bevel=.01, seg=1),
             k.box("PAT_cabWinR", (1.0, .06, .7), (-2.1, 1.17, 2.3), M["dark"], bevel=.01, seg=1),
             k.box("PAT_bumper", (.2, 2.3, .3), (-3.4, 0, .95), M["dark"], bevel=.03, seg=2),
             k.box("PAT_boxDoor", (.06, 2.3, 2.3), (3.32, 0, 2.15), m_truckBox, bevel=.01, seg=1)]
    for sx in (-2.0, 1.4):
        for sy in (-1, 1):
            parts.append(k.box("PAT_arch", (1.0, .2, .55), (sx, sy * 1.1, .85), M["dark"], bevel=.03, seg=2))
    truck = k.join(parts, "PAT_truck", origin=(0, 0, 0))
    truck.location = (tx, ty, 0); truck.rotation_euler = (0, 0, ta); k.link(truck, c)
    R = Matrix.Rotation(ta, 4, 'Z')
    for sx in (-2.0, 1.4):
        for sy in (-1, 1):
            p = R @ Vector((sx, sy * .9, 0))
            for z, a in ((.095, 0), (.285, math.radians(90)), (.475, 0)):
                cblock("PAT_blk", (tx + p.x, ty + p.y, z), M["concreteD"], rot=(0, 0, ta + a), c=c)
    # rusty container along the back, doors ajar
    cxp, cyp = 1.2, 4.3
    L.gbox("PAT_cont", (6.0, 2.4, 2.55), (cxp, cyp, 1.3), m_cont, bevel=.02, c=c)
    L.gbox("PAT_contEndL", (.06, 2.44, 2.5), (cxp - 3.0, cyp, 1.32), m_contEnd, bevel=.01, c=c)
    L.gbox("PAT_contRoof", (6.04, 2.44, .08), (cxp, cyp, 2.58), M["rust"], bevel=.01, c=c)
    L.gbox("PAT_contBase", (6.1, 2.5, .22), (cxp, cyp, .11), M["dark"], bevel=.01, c=c)
    for sx in (-1, 1):
        for sy in (-1, 1):
            L.gbox("PAT_contCorner", (.2, .2, 2.62), (cxp + sx * 2.95, cyp + sy * 1.15, 1.31), M["dark"], bevel=.01, c=c)
    k.box("PAT_contHole", (.1, 2.2, 2.3), (cxp + 2.98, cyp, 1.3), M["dark"], bevel=0, c=c)
    cd = k.box("PAT_contDoor", (.06, 1.12, 2.3), (0, 0, 0), m_contEnd, bevel=.01, seg=1, c=c)
    cd.data.transform(Matrix.Translation((0, .56, 1.15))); cd.location = (cxp + 3.03, cyp - 1.15, .12); cd.rotation_euler = (0, 0, math.radians(-35))
    L.gbox("PAT_contDoor2", (.06, 1.12, 2.3), (cxp + 3.03, cyp + .58, 1.27), m_contEnd, bevel=.01, c=c)
    for y in (cyp + .3, cyp + .9):
        k.box("PAT_contLock", (.05, .05, 2.1), (cxp + 3.08, y, 1.3), M["steel"], bevel=0, c=c)
    # guard booth at the front right with a broken window and a barrier arm
    bx, by = 3.6, -3.8
    L.gbox("PAT_booth", (1.7, 1.7, 2.5), (bx, by, 1.25), m_booth, bevel=.015, c=c)
    L.gbox("PAT_boothRoof", (2.2, 2.2, .12), (bx, by, 2.56), M["concreteD"], bevel=.012, c=c)
    L.gbox("PAT_boothInner", (1.4, 1.4, 2.3), (bx, by, 1.15), M["shadow"], bevel=0, c=c)
    L.pane_window("PAT_boothWinF", 1.0, .8, (bx, by - .85, 1.6), M["glass"], M["frame"], (0, -1, 0), c=c, cols=2, rows=1, missing=[(0, 0)])
    L.pane_window("PAT_boothWinL", 1.0, .8, (bx - .85, by, 1.6), M["glass"], M["frame"], (-1, 0, 0), c=c, cols=2, rows=1, missing=[(1, 0)])
    k.box("PAT_boothDoorHole", (.8, .12, 2.0), (bx, by + .8, 1.0), M["dark"], bevel=0, c=c)
    k.box("PAT_boothDoor", (.76, .05, 1.95), (bx + .3, by + .95, 1.0), M["door"], bevel=.01, seg=2, rot=(0, 0, math.radians(-40)), c=c)
    k.cyl("PAT_barrierPost", .09, 1.0, (bx - 1.3, by - .2, .5), M["rust"], verts=10, bevel=.01, c=c)
    arm = k.box("PAT_barrierArm", (3.2, .08, .14), (0, 0, 0), k.stripes("LOT2_Barrier", (.78, .28, .22, 1), (.90, .88, .82, 1), width=.35, axis='X', rough=.85), bevel=.01, seg=1, c=c)
    arm.data.transform(Matrix.Translation((-1.6, 0, 0))); arm.location = (bx - 1.3, by - .2, .95); arm.rotation_euler = (0, math.radians(14), 0)
    # sagging chain-link section along the front-left, one post leaning
    chainlink("PAT_fence", (-4.6, -5.3, 0), (-.4, -5.35, 0), 1.9, M["rust"], M["chrome"], c=c, sag=0.0, lean=math.radians(10))
    k.cyl("PAT_fencePostDown", .035, 2.0, (0.6, -4.6, .05), M["rust"], rot=(math.radians(88), 0, .5), verts=8, c=c)
    # props: tyres, drums, pallets, puddles, bricks, weeds through the cracks
    tire_stack("PAT_tireA", 4.1, 1.2, 3, M["tire"], c, seed=4)
    L.tire("PAT_tireLoose", (-4.2, -3.6, .32), M["tire"], rot=(math.radians(85), 0, .3), c=c)
    L.drum("PAT_drum0", (-4.2, 4.6, 0), M["drum"], rot=(0, 0, .4), c=c)
    L.drum("PAT_drum1", (-3.5, 4.8, 0), M["rust"], rot=(0, 0, 1.1), c=c)
    L.pallet("PAT_pallet0", (4.0, 2.9, 0), M["wood"], rot=(0, 0, .1), c=c)
    L.pallet("PAT_pallet1", (4.0, 2.9, .15), M["wood"], rot=(0, 0, -.1), broken=False, c=c)
    puddle("PAT_pud0", (1.0, -1.6, 0), M["puddle"], 1.8, 1.1, .3, c=c)
    puddle("PAT_pud1", (-.6, 2.0, 0), M["puddle"], 1.1, .7, -.6, c=c)
    puddle("PAT_oil", (-2.6, -1.2, 0), M["oil"], 1.0, .6, .2, c=c)
    L.dead_bush("PAT_bush", (4.3, -1.2, 0), M["twig"], r=.5, n=16, c=c, seed=73)
    pts = [(-4.5, -2.4), (-4.5, -.5), (-4.5, 1.8), (-4.4, 3.2), (-2.4, 5.2), (0.0, 5.3), (4.4, 5.0), (4.5, 4.2), (4.5, -.2), (2.2, -5.0),
           (1.4, -4.6), (-1.6, -4.8), (-3.0, -4.7), (4.5, -2.6), (-1.0, 3.2), (.6, -3.3)]
    L.scatter_tufts("PAT", pts, c, seed=121, size=.85)
    for o in c.objects:
        if o.name.startswith(("PAT_tire", "PAT_pallet")): L.ground(o)
    for i, (x, y, a) in enumerate(((-3.6, -4.3, .3), (-3.3, -4.15, 1.0))):
        L.brick(f"PAT_brick{i}", (x, y, .095), M["brick"], rot=(0, 0, a), c=c)
    return c

BUILDERS = {"LOT Loja": build_loja, "LOT Sobrado": build_sobrado, "LOT Oficina": build_oficina, "LOT Posto": build_posto,
            "LOT Garagem": build_garagem, "LOT Mato": build_mato, "LOT Fabrica": build_fabrica, "LOT Patio": build_patio}

def build_all():
    out = {}
    for cname, fn in BUILDERS.items():
        c = fn(); out[cname] = within(c)
    return out

# ================================================================== pipeline (export copy -> bake -> fbx), nested-collection aware
def make_export(cname, name):
    root = k.col(EXPORT_COL)
    d = bpy.data.collections.get(name + " Export")
    if d is None:
        d = bpy.data.collections.new(name + " Export")
    if d.name not in root.children:
        for p in bpy.data.collections:
            if d.name in p.children: p.children.unlink(d)
        if d.name in bpy.context.scene.collection.children: bpy.context.scene.collection.children.unlink(d)
        root.children.link(d)
    for o in list(d.objects): bpy.data.objects.remove(o)
    show(cname, name + " Export")
    out = []
    for o in bpy.data.collections[cname].objects:
        if o.type != 'MESH': continue
        n = o.copy(); n.data = o.data.copy(); n.name = "X_" + o.name; d.objects.link(n)
        n.parent = None; n.matrix_world = o.matrix_world.copy(); k.bake(n); out.append(n)
    bpy.ops.object.select_all(action='DESELECT')
    for o in out: o.select_set(True)
    bpy.context.view_layer.objects.active = out[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.001, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    return out

def bake(name, size=2048, batches=1, part=None):
    """Same as lot_pipe.bake (diffuse colour -> one atlas, one material), on the nested export collection."""
    sc = bpy.context.scene
    show(name + " Export")
    allobjs = [o for o in bpy.data.collections[name + " Export"].objects]
    objs = allobjs if part is None else allobjs[part::batches]
    img_name = name + "_BaseColor"
    first = part in (None, 0)
    if first:
        for im in list(bpy.data.images):
            if im.name.startswith(img_name): bpy.data.images.remove(im)
        img = bpy.data.images.new(img_name, size, size)
    else:
        img = bpy.data.images[img_name]
    mats_ = {m for o in objs for m in o.data.materials if m}; added = []
    for m in mats_:
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; m.node_tree.nodes.active = n; added.append((m, n))
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 1
    b = sc.render.bake
    b.use_pass_direct = False; b.use_pass_indirect = False; b.use_pass_color = True; b.margin = 4; b.use_clear = first
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type='DIFFUSE')
    for m, n in added: m.node_tree.nodes.remove(n)
    if part is not None and part < batches - 1:
        sc.render.engine = 'BLENDER_EEVEE'
        return None
    objs = allobjs
    os.makedirs(OUT, exist_ok=True)
    img.filepath_raw = os.path.join(OUT, img_name + ".png"); img.file_format = 'PNG'; img.save()
    am = bpy.data.materials.get(name + "_Mat") or bpy.data.materials.new(name + "_Mat")
    am.use_nodes = True; nt = am.node_tree
    for n in list(nt.nodes):
        if n.bl_idname == "ShaderNodeTexImage": nt.nodes.remove(n)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(am)
        for p in o.data.polygons: p.material_index = 0
    sc.render.engine = 'BLENDER_EEVEE'
    return img.filepath_raw

def export(cname, name):
    show(name + " Export")
    objs = [o for o in bpy.data.collections[name + " Export"].objects]
    originals = {o.name: o for o in bpy.data.collections[cname].objects}
    for o in originals.values(): o.name = o.name + "~"
    for o in objs: o.name = o.name[2:]
    lo, hi = bounds(objs)
    try:
        path = cp.export_unity(objs, name, folder=OUT)
    finally:
        for o in objs: o.name = "X_" + o.name
        for o in originals.values(): o.name = o.name[:-1]
    tris = sum(len(o.data.loop_triangles) for o in objs)
    return {"fbx": path, "kb": os.path.getsize(path) // 1024, "lo": [round(x, 2) for x in lo], "hi": [round(x, 2) for x in hi],
            "dims": [round(x, 2) for x in (hi - lo)], "tris": tris, "objs": len(objs)}

def pipeline(name, batches=2):
    cname = [cn for cn, n in LOTS.items() if n == name][0]
    make_export(cname, name)
    for p in range(batches):
        bake(name, 2048, batches, p)
    return export(cname, name)

# ================================================================== previews
def shot(target, direction, dist, lens=40, name="x", res=(1100, 720), ortho=None):
    sc = bpy.context.scene
    cp.studio(); sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.exposure = -0.2
    cam = bpy.data.objects["Studio Cam"]; cam.data.lens = lens
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho; cam.data.clip_end = 2000
    else:
        cam.data.type = 'PERSP'
    d = Vector(direction).normalized(); t = Vector(target)
    cam.location = t + d * dist; cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    os.makedirs(REVIEW, exist_ok=True)
    path = os.path.join(REVIEW, name + ".png"); sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path

ISO = (1.0, -1.25, 1.1)   # from the front-right, ~35 deg down (game camera)

def preview(name, baked=True, direction=ISO):
    cname = (name + " Export") if baked else [cn for cn, n in LOTS.items() if n == name][0]
    show(cname)
    objs = list(bpy.data.collections[cname].objects)
    lo, hi = bounds(objs); ctr = (lo + hi) / 2; size = (hi - lo).length
    g = k.box("LOT_Ground", (80, 80, .02), (0, 0, -.015), k.pavers("ERA_Pavers"), bevel=0)
    p = shot((ctr.x, ctr.y, (hi.z - lo.z) * .35), direction, size * 1.5, lens=38, name=name)
    bpy.data.objects.remove(g)
    return p

def contact_sheet(name="lots_v2_contact", baked=True, direction=ISO, res=(4000, 1150)):
    order = [LOTS[cn] + " Export" if baked else cn for cn in LOTS]
    show(*order)
    offs = {}
    x = 0.0
    for cname in order:
        objs = list(bpy.data.collections[cname].objects)
        for o in objs:
            if o.parent is None: o.location.x += x + 5.0
        offs[cname] = x + 5.0
        x += 12.0
    g = k.box("LOT_Ground", (160, 160, .02), (x / 2, 0, -.015), k.pavers("ERA_Pavers"), bevel=0)
    p = shot((x / 2, 0, 2.0), (0.22, -1.0, .72), 300, lens=40, name=name, res=res, ortho=x + 10)
    bpy.data.objects.remove(g)
    for cname, dx in offs.items():
        for o in bpy.data.collections[cname].objects:
            if o.parent is None: o.location.x -= dx
    return p
