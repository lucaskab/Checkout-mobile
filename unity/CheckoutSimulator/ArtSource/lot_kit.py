
# lot_kit.py - builders for the "unbought lot" obstacle models (Lot_Casa, Lot_Galpao, Lot_Entulho, Lot_Armazem)
import bpy, bmesh, math, random, sys, os
sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
import era_kit as k
from mathutils import Vector, Matrix

# ------------------------------------------------------------------ node helpers
def plug(nt, sock, val):
    if isinstance(val, bpy.types.NodeSocket):
        nt.links.new(val, sock)
    else:
        sock.default_value = val

def noise(nt, vec, scale, detail=4, rough=.5):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    nt.links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]

def ramp(nt, fac, lo, hi, to_lo=0., to_hi=1.):
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = lo
    mr.inputs["From Max"].default_value = hi
    mr.inputs["To Min"].default_value = to_lo
    mr.inputs["To Max"].default_value = to_hi
    plug(nt, mr.inputs["Value"], fac)
    return mr.outputs[0]

def mix(nt, a, b, fac, blend='MIX'):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = 'RGBA'
    m.blend_type = blend
    plug(nt, m.inputs[6], a)
    plug(nt, m.inputs[7], b)
    plug(nt, m.inputs[0], fac)
    return m.outputs[2]

def fmath(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    plug(nt, n.inputs[0], a)
    if b is not None:
        plug(nt, n.inputs[1], b)
    return n.outputs[0]

def sepz(nt, vec):
    s = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(vec, s.inputs[0])
    return s.outputs["Z"]

def mul(nt, col, f):
    """col * f (f: float socket)."""
    return mix(nt, col, f, 1.0, 'MULTIPLY')

def grime(nt, col, var=.10, scale=30.):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    g = noise(nt, tc.outputs["Object"], scale, 5)
    f = ramp(nt, g, .35, .65, 1 - var, 1 + var)
    return mul(nt, col, f), g

def _start(name, rough=.85):
    m, nt = k._new(name)
    if nt is None:
        return m, None, None, None
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return m, nt, bsdf, tc.outputs["Object"]

def _finish(nt, bsdf, col, bump_src=None, bump=.25):
    nt.links.new(col, bsdf.inputs["Base Color"])
    if bump_src is not None and bump:
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        nt.links.new(bump_src, b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])

def brick_socket(nt, vec, c1=(.66, .36, .27, 1), c2=(.58, .30, .22, 1), mortar=(.72, .68, .62, 1), scale=4.0, bw=.5, rh=.25, msize=.04):
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = scale
    br.inputs["Mortar Size"].default_value = msize
    br.inputs["Mortar Smooth"].default_value = .3
    br.inputs["Color1"].default_value = c1
    br.inputs["Color2"].default_value = c2
    br.inputs["Mortar"].default_value = mortar
    br.inputs["Brick Width"].default_value = bw
    br.inputs["Row Height"].default_value = rh
    br.inputs["Bias"].default_value = 0
    # bricks courses run along X in object space: map (x, z) -> (u, v)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(vec, sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    add = fmath(nt, 'ADD', sep.outputs["X"], sep.outputs["Y"])  # walls along X use x, walls along Y use y
    nt.links.new(add, comb.inputs["X"]); nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], br.inputs["Vector"])
    return br.outputs["Color"], br.outputs["Fac"]

# ------------------------------------------------------------------ materials
def plaster(name, paint, under=(.60, .50, .42, 1), damage=.5, cracks=True, brick_under=False, zband=None, band=None, crack_scale=1.1, crack_amount=.5):
    """Faded painted plaster with peeling patches (`under` shows through), hairline cracks, dirt."""
    m, nt, bsdf, obj = _start(name, .9)
    if nt is None:
        return m
    n1 = noise(nt, obj, 1.4, 4, .55)
    z = sepz(nt, obj)
    low = ramp(nt, z, 0.0, 1.6, .06, 0.)       # more damage near the ground
    f = fmath(nt, 'ADD', n1, low)
    mask = ramp(nt, f, .60 - damage * .12, .66 - damage * .08)
    u = under
    if brick_under:
        u, _ = brick_socket(nt, obj)
    col = mix(nt, paint, u, mask)
    if band is not None and zband is not None:   # painted base band ('brick' = exposed brick band)
        bz = ramp(nt, z, zband - .01, zband + .01)
        bandcol = u if band == 'brick' else mix(nt, band, u, mask)
        col = mix(nt, bandcol, col, bz)
    if cracks:
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.feature = 'DISTANCE_TO_EDGE'
        vor.inputs["Scale"].default_value = crack_scale
        nt.links.new(obj, vor.inputs["Vector"])
        crack = ramp(nt, vor.outputs["Distance"], .004, .016)
        region = ramp(nt, noise(nt, obj, .9, 2), .56 - crack_amount * .12, .60 - crack_amount * .08)
        vis = fmath(nt, 'MAXIMUM', crack, fmath(nt, 'SUBTRACT', 1.0, region))
        col = mix(nt, (.30, .26, .22, 1), col, vis)
    col, g = grime(nt, col, .12, 25)
    _finish(nt, bsdf, col, g, .3)
    return m

def corrugated(name, base=(.70, .72, .70, 1), rust=(.52, .27, .12, 1), rustiness=.35, ribs=True, pitch=.076, axis='X', rough=.6):
    """Galvanised sheet with rust streaks; ribs are shaded stripes along `axis` (object space)."""
    m, nt, bsdf, obj = _start(name, rough)
    if nt is None:
        return m
    # rust: blotches stretched vertically (streaks running down from the top / bolts)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, .28)
    nt.links.new(obj, mp.inputs["Vector"])
    n1 = noise(nt, mp.outputs[0], 2.6, 5, .6)
    n2 = noise(nt, obj, 1.2, 3, .5)
    z = sepz(nt, obj)
    low = ramp(nt, z, 0.0, 1.0, .09, 0.)
    f = fmath(nt, 'ADD', fmath(nt, 'ADD', fmath(nt, 'MULTIPLY', n1, .6), fmath(nt, 'MULTIPLY', n2, .4)), low)
    mask = ramp(nt, f, .60 - rustiness * .16, .70 - rustiness * .10)
    rust_dark = (rust[0] * .55, rust[1] * .55, rust[2] * .55, 1)
    rustcol = mix(nt, rust, rust_dark, ramp(nt, noise(nt, obj, 9, 3), .4, .6))
    col = mix(nt, base, rustcol, mask)
    # light rust tint around the strong rust (halo)
    halo = ramp(nt, f, .50 - rustiness * .16, .62 - rustiness * .12, 0, .35)
    col = mix(nt, col, rust, halo)
    bump_src = None
    if ribs:
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = 'BANDS'; w.bands_direction = axis; w.wave_profile = 'SIN'
        w.inputs["Scale"].default_value = (2 * math.pi / 10.0) / pitch
        w.inputs["Distortion"].default_value = 0
        nt.links.new(obj, w.inputs["Vector"])
        shade = ramp(nt, w.outputs["Fac"], 0, 1, .66, 1.08)
        col = mul(nt, col, shade)
        bump_src = w.outputs["Fac"]
    col, g = grime(nt, col, .08, 30)
    _finish(nt, bsdf, col, bump_src, .35)
    return m

def rustmetal(name, base=(.45, .47, .46, 1), rust=(.50, .26, .12, 1), rustiness=.5, rough=.7):
    return corrugated(name, base, rust, rustiness, ribs=False, rough=rough)

def rooftiles(name, tile=(.66, .36, .27, 1), tile2=(.58, .31, .24, 1), moss=(.52, .56, .30, 1), tw=.33, th=.26):
    """Clay tile rows (object-space: X along the row, Y up the slope)."""
    m, nt, bsdf, obj = _start(name, .85)
    if nt is None:
        return m
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = .025
    br.inputs["Mortar Smooth"].default_value = .4
    br.inputs["Color1"].default_value = tile
    br.inputs["Color2"].default_value = tile2
    br.inputs["Mortar"].default_value = (.40, .24, .18, 1)
    br.inputs["Brick Width"].default_value = tw
    br.inputs["Row Height"].default_value = th
    br.inputs["Bias"].default_value = 0
    nt.links.new(obj, br.inputs["Vector"])
    # shade each row darker at its lower edge so the overlap reads
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(obj, sep.inputs[0])
    rowf = fmath(nt, 'FRACT', fmath(nt, 'DIVIDE', sep.outputs["Y"], th))
    shade = ramp(nt, rowf, 0.0, .5, .78, 1.0)
    col = mul(nt, br.outputs["Color"], shade)
    mossm = ramp(nt, noise(nt, obj, 1.6, 4), .56, .64)
    col = mix(nt, col, moss, mossm)
    col, g = grime(nt, col, .12, 20)
    _finish(nt, bsdf, col, br.outputs["Fac"], .3)
    return m

def brickwall(name, c1=(.66, .36, .27, 1), c2=(.58, .30, .22, 1), mortar=(.70, .66, .60, 1)):
    m, nt, bsdf, obj = _start(name, .9)
    if nt is None:
        return m
    col, fac = brick_socket(nt, obj, c1, c2, mortar)
    col, g = grime(nt, col, .14, 12)
    _finish(nt, bsdf, col, fac, .3)
    return m

def oldwood(name="LOT_Wood", light=(.55, .45, .33, 1), dark=(.33, .26, .19, 1), axis='X', scale=10):
    return k.wood(name, light, dark, scale=scale, axis=axis, rough=.8, bump=.3)

def dirt(name="LOT_Dirt"):
    return k.mat(name, (.56, .46, .33, 1), rough=.95, var=.18, scale=2.5, bump=.4)

def fabric(name, a=(.72, .66, .56, 1), b=(.55, .58, .66, 1), width=.12, axis='X'):
    m = k.stripes(name, a, b, width=width, axis=axis, rough=.9)
    return m

M = {}
def mats():
    if M:
        return M
    M["dirt"] = dirt()
    M["dark"] = k.mat("LOT_Dark", (.08, .07, .07, 1), rough=.95, var=.0)
    M["shadow"] = k.mat("LOT_Shadow", (.14, .12, .11, 1), rough=.95, var=.05, scale=5)
    M["wood"] = oldwood("LOT_Wood")
    M["woodZ"] = oldwood("LOT_WoodZ", axis='Z')
    M["woodY"] = oldwood("LOT_WoodY", axis='Y')
    M["grass"] = k.mat("LOT_Grass", (.52, .62, .24, 1), rough=.8, var=.22, scale=8)
    M["grassdry"] = k.mat("LOT_GrassDry", (.74, .68, .36, 1), rough=.8, var=.18, scale=8)
    M["twig"] = k.mat("LOT_Twig", (.36, .27, .18, 1), rough=.9, var=.12, scale=20)
    M["tire"] = k.mat("LOT_Tire", (.13, .13, .14, 1), rough=.75, var=.06, scale=10)
    M["concrete"] = k.mat("LOT_Concrete", (.66, .64, .59, 1), rough=.95, var=.14, scale=12, bump=.4)
    M["concreteD"] = k.mat("LOT_ConcreteD", (.52, .51, .48, 1), rough=.95, var=.14, scale=12, bump=.4)
    M["brick"] = k.mat("LOT_Brick", (.70, .36, .26, 1), rough=.9, var=.12, scale=30)
    M["rebar"] = rustmetal("LOT_Rebar", (.35, .33, .30, 1), (.48, .24, .10, 1), .7)
    M["rust"] = rustmetal("LOT_Rust", (.50, .52, .50, 1), (.50, .26, .12, 1), .55)
    M["drum"] = rustmetal("LOT_Drum", (.20, .40, .55, 1), (.50, .26, .12, 1), .45)
    M["gutter"] = rustmetal("LOT_Gutter", (.72, .74, .72, 1), (.50, .26, .12, 1), .45)
    M["glass"] = k.mat("LOT_Pane", (.30, .40, .46, 1), rough=.25, var=.10, scale=4)
    M["frame"] = k.mat("LOT_Frame", (.86, .84, .76, 1), rough=.8, var=.10, scale=20)
    M["door"] = rustmetal("LOT_Door", (.36, .50, .48, 1), (.50, .26, .12, 1), .45)
    M["fabric"] = fabric("LOT_Fabric", (.68, .62, .52, 1), (.50, .54, .58, 1), width=.10)
    M["foam"] = k.mat("LOT_Foam", (.86, .80, .56, 1), rough=.95, var=.15, scale=20)
    return M

# ------------------------------------------------------------------ geometry helpers
def gbox(name, size, loc, m, rot=(0, 0, 0), bevel=.01, seg=2, c=None, flat=False):
    """Box whose origin sits at its XY centre on z=0 (object Z == world Z for the materials)."""
    o = k.box(name, size, loc, m, rot=rot, bevel=bevel, seg=seg, c=c)
    if rot == (0, 0, 0):
        o.data.transform(Matrix.Translation((0, 0, loc[2])))
        o.location = (loc[0], loc[1], 0)
    if flat:
        for p in o.data.polygons: p.use_smooth = False
    return o

def poly_prism(name, pts, thick, loc, m, axis='Y', c=None, bevel=.01):
    """Extrude a 2D polygon. pts in (u, z); u -> X when axis='Y' (extruded along Y), u -> Y when axis='X'."""
    bm = bmesh.new()
    verts = []
    for (u, z) in pts:
        p = (u, -thick / 2, z) if axis == 'Y' else (-thick / 2, u, z)
        verts.append(bm.verts.new(p))
    f = bm.faces.new(verts)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    vs = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
    d = (0, thick, 0) if axis == 'Y' else (thick, 0, 0)
    bmesh.ops.translate(bm, verts=vs, vec=d)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    k.link(o, c)
    k.finish(o, m, bevel, 2)
    return o

def _cut_rects(rects, hole):
    hx0, hy0, hx1, hy1 = hole
    out = []
    for (x0, y0, x1, y1) in rects:
        if hx1 <= x0 or hx0 >= x1 or hy1 <= y0 or hy0 >= y1:
            out.append((x0, y0, x1, y1)); continue
        ix0, ix1 = max(x0, hx0), min(x1, hx1)
        if hy0 > y0: out.append((x0, y0, x1, hy0))
        if hy1 < y1: out.append((x0, hy1, x1, y1))
        iy0, iy1 = max(y0, hy0), min(y1, hy1)
        if hx0 > x0: out.append((x0, iy0, hx0, iy1))
        if hx1 < x1: out.append((hx1, iy0, x1, iy1))
    return out

def slab(name, w, L, t, m, mat_world, holes=(), c=None, purlins=True, m_purlin=None, bevel=.01):
    """Rectangle [-w/2,w/2]x[0,L] (local XY) with rect holes, thickness t, placed with `mat_world`.
    All pieces share the same local origin so texture rows stay continuous across the pieces."""
    rects = [(-w / 2, 0, w / 2, L)]
    for h in holes:
        rects = _cut_rects(rects, h)
    out = []
    for i, (x0, y0, x1, y1) in enumerate(rects):
        o = k.box(f"{name}_p{i}", (x1 - x0, y1 - y0, t), ((x0 + x1) / 2, (y0 + y1) / 2, 0), m, bevel=bevel, seg=2, c=c)
        o.data.transform(Matrix.Translation(o.location)); o.location = (0, 0, 0)
        o.matrix_world = mat_world
        out.append(o)
    if purlins and holes:
        mp = m_purlin or mats()["woodY"]
        for j, (hx0, hy0, hx1, hy1) in enumerate(holes):
            # rafters running up the slope (local Y) and one purlin across, under the hole
            for xx in (hx0 + (hx1 - hx0) * .3, hx0 + (hx1 - hx0) * .7):
                o = k.box(f"{name}_raft{j}", (.07, hy1 - hy0 + .3, .10), (xx, (hy0 + hy1) / 2, -t / 2 - .07), mp, bevel=.004, seg=1, c=c)
                o.data.transform(Matrix.Translation(o.location)); o.location = (0, 0, 0); o.matrix_world = mat_world; out.append(o)
            o = k.box(f"{name}_purl{j}", (hx1 - hx0 + .3, .07, .07), ((hx0 + hx1) / 2, (hy0 + hy1) / 2, -t / 2 - .16), mp, bevel=.004, seg=1, c=c)
            o.data.transform(Matrix.Translation(o.location)); o.location = (0, 0, 0); o.matrix_world = mat_world; out.append(o)
    return out

def gable_roof(name, cx, cy, w_along, d_across, z_eave, z_ridge, t, m, holes_f=(), holes_b=(), ridge='X', c=None, m_purlin=None, ridge_cap=None):
    """Two slopes. ridge='X': ridge runs along X, front slope faces -Y. ridge='Y': rotated 90deg (front slope faces -X)."""
    L = math.hypot(d_across / 2, z_ridge - z_eave)
    pitch = math.atan2(z_ridge - z_eave, d_across / 2)
    R = Matrix.Rotation(math.radians(-90), 4, 'Z') if ridge == 'Y' else Matrix.Identity(4)
    T0 = Matrix.Translation((cx, cy, 0))
    Mf = T0 @ R @ Matrix.Translation((0, -d_across / 2, z_eave)) @ Matrix.Rotation(pitch, 4, 'X')
    Mb = T0 @ R @ Matrix.Translation((0, d_across / 2, z_eave)) @ Matrix.Rotation(math.pi - pitch, 4, 'X')
    out = slab(name + "_F", w_along, L, t, m, Mf, holes_f, c, m_purlin=m_purlin)
    out += slab(name + "_B", w_along, L, t, m, Mb, holes_b, c, m_purlin=m_purlin)
    if ridge_cap is not None:
        rot = (0, 0, math.radians(90)) if ridge == 'Y' else (0, 0, 0)
        o = k.box(name + "_ridge", (w_along + .02, .22, .10), (cx, cy, z_ridge + .02), ridge_cap, rot=rot, bevel=.03, seg=2, c=c)
        out.append(o)
    return out, pitch, L

def tuft(name, loc, m, n=7, h=.5, spread=.12, c=None, seed=0, blade=.035):
    rnd = random.Random(seed)
    parts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-.3, .3)
        tilt = rnd.uniform(.35, .75)
        hh = h * rnd.uniform(.6, 1.1)
        o = k.cyl(f"{name}_b", blade, hh, (0, 0, 0), m, verts=3, bevel=0, r2=0.0)
        o.data.transform(Matrix.Translation((0, 0, hh / 2)))
        o.rotation_euler = (tilt * math.cos(a), tilt * math.sin(a), rnd.uniform(0, 6))
        for p in o.data.polygons: p.use_smooth = False
        parts.append(o)
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc
    k.link(o, c)
    return o

def dead_bush(name, loc, m, r=.45, n=16, c=None, seed=1):
    rnd = random.Random(seed)
    parts = []
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi); el = rnd.uniform(.25, 1.2); ln = r * rnd.uniform(.6, 1.0)
        tip = (ln * math.cos(a) * math.cos(el), ln * math.sin(a) * math.cos(el), ln * math.sin(el) + .02)
        parts.append(k.tube(f"{name}_t", (0, 0, .02), tip, .012, m, verts=4))
        if rnd.random() < .6:
            a2 = a + rnd.uniform(-.8, .8); ln2 = ln * rnd.uniform(.4, .7)
            tip2 = (tip[0] + ln2 * math.cos(a2) * .6, tip[1] + ln2 * math.sin(a2) * .6, tip[2] + ln2 * .5)
            parts.append(k.tube(f"{name}_t", tip, tip2, .008, m, verts=4))
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc
    k.link(o, c)
    return o

def tire(name, loc, m, rot=(0, 0, 0), R=.30, r=.10, c=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=16, minor_segments=8, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    k.link(o, c)
    k.finish(o, m, 0)
    return o

def chunk(name, loc, m, s=.3, c=None, seed=0, flat=True):
    rnd = random.Random(seed)
    o = k.ball(name, s, loc, m, sub=1, scale=(rnd.uniform(.7, 1.3), rnd.uniform(.7, 1.3), rnd.uniform(.4, .8)), rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 6)), c=c)
    if flat:
        for p in o.data.polygons: p.use_smooth = False
    return o

def brick(name, loc, m, rot=(0, 0, 0), c=None):
    return k.box(name, (.22, .11, .07), loc, m, rot=rot, bevel=.006, seg=1, c=c)

def drum(name, loc, m, rot=(0, 0, 0), c=None):
    parts = [k.cyl(f"{name}_b", .29, .88, (0, 0, .44), m, verts=18, bevel=.012, seg=2),
             k.cyl(f"{name}_r1", .305, .05, (0, 0, .28), m, verts=18, bevel=.01),
             k.cyl(f"{name}_r2", .305, .05, (0, 0, .60), m, verts=18, bevel=.01)]
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = rot
    k.link(o, c)
    return o

def pallet(name, loc, m, rot=(0, 0, 0), broken=True, c=None):
    parts = []
    for y in (-.5, 0, .5):
        parts.append(k.box(f"{name}_run", (1.2, .10, .09), (0, y, .045), m, bevel=.004, seg=1))
    for i, y in enumerate((-.42, -.21, 0, .21, .42)):
        parts.append(k.box(f"{name}_bot", (1.2, .10, .02), (0, y, .01), m, bevel=.003, seg=1))
    for i, x in enumerate((-.52, -.26, 0, .26, .52)):
        if broken and i == 1:
            parts.append(k.box(f"{name}_top", (.10, .55, .02), (x, -.3, .10), m, bevel=.003, seg=1, rot=(0, 0, 0)))
            parts.append(k.box(f"{name}_top", (.10, .45, .02), (x + .05, .42, .06), m, bevel=.003, seg=1, rot=(.5, .1, .15)))
        else:
            parts.append(k.box(f"{name}_top", (.10, 1.1, .02), (x, 0, .10), m, bevel=.003, seg=1))
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = rot
    k.link(o, c)
    return o

def boarded_window(name, w, h, loc, m_pane, m_frame, m_wood, facing=(0, -1, 0), c=None, n_planks=3, seed=0, frame=True):
    """Window on a wall: `loc` is the centre on the wall surface; facing = outward normal."""
    rnd = random.Random(seed)
    nx, ny, _ = facing
    rz = math.atan2(ny, nx) + math.pi / 2  # local -Y -> facing
    parts = [k.box(f"{name}_pane", (w, .04, h), (0, .01, 0), m_pane, bevel=0)]
    if frame:
        ft = .07
        parts += [k.box(f"{name}_fr", (w + 2 * ft, .05, ft), (0, -.01, h / 2 + ft / 2), m_frame, bevel=.006, seg=1),
                  k.box(f"{name}_fr", (w + 2 * ft, .05, ft), (0, -.01, -h / 2 - ft / 2), m_frame, bevel=.006, seg=1),
                  k.box(f"{name}_fr", (ft, .05, h), (-w / 2 - ft / 2, -.01, 0), m_frame, bevel=.006, seg=1),
                  k.box(f"{name}_fr", (ft, .05, h), (w / 2 + ft / 2, -.01, 0), m_frame, bevel=.006, seg=1)]
    for i in range(n_planks):
        z = -h / 2 + h * (i + .5) / n_planks
        ang = rnd.uniform(-.14, .14) if i % 2 == 0 else rnd.uniform(-.08, .08)
        parts.append(k.box(f"{name}_pl", (w + .30, .03, .14), (rnd.uniform(-.05, .05), -.05, z), m_wood, rot=(0, ang, 0), bevel=.004, seg=1))
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = (0, 0, rz)
    k.link(o, c)
    return o

def pane_window(name, w, h, loc, m_pane, m_frame, facing=(0, -1, 0), cols=3, rows=2, missing=(), c=None):
    nx, ny, _ = facing
    rz = math.atan2(ny, nx) + math.pi / 2
    ft, bt = .08, .04
    parts = [k.box(f"{name}_bk", (w, .04, h), (0, .03, 0), mats()["dark"], bevel=0),
             k.box(f"{name}_fr", (w + 2 * ft, .06, ft), (0, 0, h / 2 + ft / 2), m_frame, bevel=.006, seg=1),
             k.box(f"{name}_fr", (w + 2 * ft, .06, ft), (0, 0, -h / 2 - ft / 2), m_frame, bevel=.006, seg=1),
             k.box(f"{name}_fr", (ft, .06, h), (-w / 2 - ft / 2, 0, 0), m_frame, bevel=.006, seg=1),
             k.box(f"{name}_fr", (ft, .06, h), (w / 2 + ft / 2, 0, 0), m_frame, bevel=.006, seg=1)]
    for i in range(1, cols):
        parts.append(k.box(f"{name}_bar", (bt, .05, h), (-w / 2 + w * i / cols, 0, 0), m_frame, bevel=0))
    for j in range(1, rows):
        parts.append(k.box(f"{name}_bar", (w, .05, bt), (0, 0, -h / 2 + h * j / rows), m_frame, bevel=0))
    pw, ph = w / cols, h / rows
    for i in range(cols):
        for j in range(rows):
            if (i, j) in missing:
                continue
            parts.append(k.box(f"{name}_pn", (pw - bt, .02, ph - bt), (-w / 2 + pw * (i + .5), .0, -h / 2 + ph * (j + .5)), m_pane, bevel=0))
    o = k.join(parts, name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = (0, 0, rz)
    k.link(o, c)
    return o

def scatter_tufts(prefix, pts, c, seed=0, dry_every=3, size=1.0):
    rnd = random.Random(seed)
    out = []
    for i, (x, y) in enumerate(pts):
        m = mats()["grassdry"] if i % dry_every == 0 else mats()["grass"]
        out.append(tuft(f"{prefix}_tuft{i}", (x, y, 0), m, n=rnd.randint(6, 8), h=rnd.uniform(.4, .65) * size, c=c, seed=seed + i, blade=.035 * size))
    return out

def clear(cname):
    c = k.col(cname)
    for o in list(c.objects):
        bpy.data.objects.remove(o)
    return c

def pad(name, w, d, c, t=.05):
    return gbox(name, (w, d, t), (0, 0, t / 2 - .005), mats()["dirt"], bevel=.02, seg=2, c=c)


def ground(o, z=0.0):
    """Shift the object up/down so its lowest evaluated vertex sits at `z`."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = o.evaluated_get(dg).data
    lo = min((o.matrix_world @ v.co).z for v in me.vertices)
    o.location.z += z - lo
    return o

def clip_below(o, z=0.0):
    """Remove geometry below world z (flat cut), close the cut."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    mw = o.matrix_world
    pco = mw.inverted() @ Vector((0, 0, z))
    pno = (mw.to_3x3().inverted().transposed() @ Vector((0, 0, 1))).normalized()
    r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=pco, plane_no=pno, clear_inner=True)
    edges = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges)
    bm.to_mesh(o.data); bm.free()
    return o
