"""_lib_J: extra paint recipes + geometry helpers for group J (swing-set, hotdog-cart, topiary-animal, gazebo, carousel).
Import from an item script with:  import dv4, os, sys; sys.path.insert(0, os.path.join(dv4.ROOT, "items")); import _lib_J as J
"""
import math
import bpy, bmesh
from mathutils import Vector
import dv4
from dv4 import MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, paint, RNG


# ================================================================================================= node helpers
def XYZ(nt, x, y, z):
    n = nt.nodes.new("ShaderNodeCombineXYZ")
    dv4._plug(nt, n.inputs[0], x); dv4._plug(nt, n.inputs[1], y); dv4._plug(nt, n.inputs[2], z)
    return n.outputs[0]


def WHITE(nt, vec):
    """Per-cell random 0..1 from an integer-ish vector."""
    n = nt.nodes.new("ShaderNodeTexWhiteNoise"); n.noise_dimensions = "3D"
    dv4._plug(nt, n.inputs["Vector"], vec)
    return n.outputs["Value"]


def SEP(nt, col, ch="Red"):
    n = nt.nodes.new("ShaderNodeSeparateColor"); dv4._plug(nt, n.inputs[0], col)
    return n.outputs[ch]


def angle_u(c, n, center=(0, 0), phase=0.0):
    """u = n * angle / 2pi around the vertical axis through `center` (so a pattern repeats n times)."""
    nt = c.nt
    x = MATH(nt, "SUBTRACT", c.x, center[0]); y = MATH(nt, "SUBTRACT", c.y, center[1])
    ang = MATH(nt, "ARCTAN2", y, x)
    return MATH(nt, "ADD", MATH(nt, "MULTIPLY", ang, n / (2 * math.pi)), phase)


def canvas(nt, col, amt=.08):
    """Fine cloth weave darkening."""
    w = NOISE(nt, COORD(nt, scale=(110, 110, 110)), 1.0, 2.0)
    return MIX(nt, MATH(nt, "MULTIPLY", w, amt), col, "000000")


# ================================================================================================= paint recipes
def paint_stripes(name, cols=("D74A3C", "F4EFE4"), n=12, center=(0, 0), phase=0.0, axis=None, width=.2, soft=.02, weave=.08,
                  shade=.18, **fin):
    """Striped canvas. Radial: n stripes around the vertical axis through `center` (n must be a multiple of len(cols)).
    axis="X"/"Y": straight stripes across that world axis, `width` metres each."""
    k = len(cols)

    def r(c):
        nt = c.nt
        if axis:
            u = MATH(nt, "ADD", MATH(nt, "DIVIDE", {"X": c.x, "Y": c.y}[axis], width), phase)
        else:
            u = angle_u(c, n, center, phase)
        wob = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", NOISE(nt, c.pos, 25.0, 2.0), .5), soft)
        f = MATH(nt, "FRACT", MATH(nt, "ADD", MATH(nt, "DIVIDE", u, k), wob))
        col = RAMP(nt, f, [(i / k, h) for i, h in enumerate(cols)], "CONSTANT")
        if shade > 0:      # soft tonal variation so big cloth areas don't look flat
            t = NOISE(nt, c.pos, 1.5, 2.0)
            col = MIX(nt, MATH(nt, "MULTIPLY", t, shade), col, "6A5040")
        if weave > 0:
            col = canvas(nt, col, weave)
        return col
    return paint(name, r, **fin)


def paint_hedge(name="Hedge", base="4E9A3A", dark="21531F", light="97D45C", scale=55.0, tip="C8EE8A", **fin):
    """Clipped box hedge: dense little leaves (voronoi cells with a dark rim and per-leaf tone), lit from the top."""
    def r(c):
        nt = c.nt
        d = VORO(nt, c.pos, scale, "F1", "Distance")
        rnd = SEP(nt, VORO(nt, c.pos, scale, "F1", "Color"), "Red")
        col = RAMP(nt, rnd, [(0, dark), (.45, base), (1, light)])
        shade = RAMP(nt, d, [(.0, "FFFFFF"), (.45, "C8C8C8"), (.75, "5A5A5A"), (1.0, "303030")])
        col = MIX(nt, 1.0, col, shade, "MULTIPLY")
        # second, finer layer of leaf tips catching light
        d2 = VORO(nt, COORD(nt, loc=(.37, .11, .23)), scale * 2.1, "F1", "Distance")
        tips = SMOOTH(nt, d2, .3, .05)
        col = MIX(nt, MATH(nt, "MULTIPLY", tips, .35), col, tip)
        # big soft variation + darker in the crevices + top light
        big = NOISE(nt, c.pos, 3.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", big, .3), col, dark)
        col = MIX(nt, MATH(nt, "MULTIPLY", c.crev, .6), col, dark)
        top = SMOOTH(nt, c.nz, .1, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", top, .25), col, light)
        return col
    return paint(name, r, k_ao=.5, k_light=.3, **fin)


def paint_shingles(name="Shingles", base="A0513E", dark="6E3328", light="C97A5E", gap="3E1D16", row_h=.09, n_around=48,
                   center=(0, 0), z0=0.0, **fin):
    """Rows of rounded shingles on a conical/pyramid roof: rows by height, staggered half a shingle every other row."""
    def r(c):
        nt = c.nt
        v = MATH(nt, "DIVIDE", MATH(nt, "SUBTRACT", c.z, z0), row_h)
        row = MATH(nt, "FLOOR", v); fv = MATH(nt, "FRACT", v)
        u = MATH(nt, "ADD", angle_u(c, n_around, center), MATH(nt, "MULTIPLY", MATH(nt, "MODULO", row, 2.0), .5))
        fu = MATH(nt, "FRACT", u); du = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", fu, .5))
        # rounded lower edge: the gap under a shingle rises toward its sides
        bottom = MATH(nt, "MULTIPLY", MATH(nt, "POWER", MATH(nt, "MULTIPLY", du, 2.0), 2.0), .3)
        gap_m = SMOOTH(nt, MATH(nt, "SUBTRACT", fv, bottom), .10, .04)
        side_m = SMOOTH(nt, du, .45, .48)
        idv = XYZ(nt, MATH(nt, "FLOOR", u), row, 0.0)
        rnd = WHITE(nt, idv)
        col = RAMP(nt, rnd, [(0, dark), (.5, base), (1, light)])
        grain = NOISE(nt, c.pos, 40.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", grain, .18), col, dark)
        # lighter toward the exposed lower part of each shingle (it catches the light), shadow just above the row below
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, fv, .9, .3), .18), col, light)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, fv, .8, 1.0), .5), col, dark)
        return MIX(nt, MATH(nt, "MAXIMUM", gap_m, side_m), col, gap)
    return paint(name, r, edge=light, edge_k=.5, edge_r=.01, **fin)


def paint_steel(name="Steel", base="B4BDC3", dark="7A858D", light="EAF0F3", brush="X", **fin):
    """Brushed stainless: fine lines along `brush`, mottling, a bright top highlight."""
    def r(c):
        nt = c.nt
        s = {"X": (1, 60, 60), "Y": (60, 1, 60), "Z": (60, 60, 1)}[brush]
        lines = NOISE(nt, COORD(nt, scale=s), 2.0, 2.0)
        mot = NOISE(nt, c.pos, 4.0, 2.0)
        col = RAMP(nt, mot, [(.25, dark), (.5, base), (.9, light)])
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .0), col, dark)
        col = MIX(nt, MATH(nt, "MULTIPLY", lines, .14), col, dark)
        hl = SMOOTH(nt, c.nz, .3, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .35), col, light)
        return col
    return paint(name, r, edge=light, edge_k=1.0, edge_r=.008, **fin)


def paint_gloss(name, base, dark=None, light=None, variation=.12, highlight=.3, edge=None, **fin):
    """Painted / enamel surface: gentle mottling, a lit top, light edges (toy-like)."""
    dark = dark or "000000"; light = light or "FFFFFF"

    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 7.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, variation), base, dark)
        hl = SMOOTH(nt, c.nz, .2, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, highlight), col, light)
        return col
    return paint(name, r, edge=edge or light, edge_k=.7, edge_r=.006, **fin)


def paint_dapple(name, base="F4EFE4", spot="C9CCD0", dark="9A9EA3", scale=28.0, amt=.6, **fin):
    """Dapple-grey horse coat: round soft spots over a light coat."""
    def r(c):
        nt = c.nt
        d = VORO(nt, c.pos, scale, "F1", "Distance")
        sp = SMOOTH(nt, d, .55, .2)
        col = MIX(nt, MATH(nt, "MULTIPLY", sp, amt), base, spot)
        mot = NOISE(nt, c.pos, 5.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .18), col, dark)
        hl = SMOOTH(nt, c.nz, .2, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .25), col, "FFFFFF")
        return col
    return paint(name, r, edge="FFFFFF", edge_k=.6, edge_r=.006, **fin)


def paint_sausage(name="Sausage", base="C4542C", dark="7F2E14", light="E8875A", axis="Y", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 30.0, 2.0)
        col = RAMP(nt, mot, [(.3, dark), (.55, base), (.85, light)])
        s = {"X": (1, 30, 30), "Y": (30, 1, 30)}[axis]
        char = WAVE(nt, COORD(nt, scale=s), scale=1.1, dist=1.0, detail=1.0, direction="X" if axis == "Y" else "Y")
        char = SMOOTH(nt, char, .05, .0)
        col = MIX(nt, MATH(nt, "MULTIPLY", char, .55), col, dark)
        hl = SMOOTH(nt, c.nz, .3, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .4), col, light)
        return col
    return paint(name, r, edge=light, edge_k=.5, edge_r=.006, **fin)


def paint_bun(name="Bun", base="D9A35C", dark="A8702F", light="F3D79B", seed="F8EAC8", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 18.0, 3.0)
        col = RAMP(nt, mot, [(.3, dark), (.6, base), (.9, light)])
        top = SMOOTH(nt, c.nz, .0, .9)
        col = MIX(nt, MATH(nt, "MULTIPLY", top, .45), col, light)
        seeds = SMOOTH(nt, VORO(nt, c.pos, 140.0, "F1", "Distance"), .22, .12)
        col = MIX(nt, MATH(nt, "MULTIPLY", seeds, SMOOTH(nt, c.nz, .4, .9)), col, seed)
        return col
    return paint(name, r, k_light=.25, **fin)


def paint_rope(name="Rope", base="C8A46A", dark="8A6A3C", light="E8CC94", axis="Z", **fin):
    """Twisted hemp rope: tight diagonal-ish bands across the rope axis."""
    def r(c):
        nt = c.nt
        s = {"Z": (30, 30, 1), "X": (1, 30, 30), "Y": (30, 1, 30)}[axis]
        w = WAVE(nt, COORD(nt, scale=s), scale=22.0, dist=.6, detail=1.0, direction={"Z": "Z", "X": "X", "Y": "Y"}[axis])
        col = RAMP(nt, w, [(.1, dark), (.5, base), (.95, light)])
        fz = NOISE(nt, c.pos, 80.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", fz, .2), col, dark)
        return col
    return paint(name, r, k_ao=.4, **fin)


def paint_griddle(name="Griddle", base="3A3E42", dark="1E2124", light="6C7378", grease="8A6A3A", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 12.0, 3.0)
        col = RAMP(nt, mot, [(.3, dark), (.6, base), (.9, light)])
        sm = SMOOTH(nt, NOISE(nt, c.pos, 7.0, 2.0, .6), .5, .75)
        col = MIX(nt, MATH(nt, "MULTIPLY", sm, .3), col, grease)
        hl = SMOOTH(nt, c.nz, .5, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .2), col, light)
        return col
    return paint(name, r, edge=light, edge_k=.8, edge_r=.006, **fin)


def _wood(c, base, dark, light, scale, along, dist, tint, stretch):
    """Same look as dv4.paint_wood, returned as a colour socket so recipes can add things on top."""
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


def paint_planks(name="Planks", base="B9743F", dark="6B4128", light="DDA55F", width=.12, axis="Y", along="X", groove="35200F",
                 groove_w=.012, scale=3.0, dist=4.0, tint=.0, stretch=9.0, phase=0.0, edge="E2B57A", **fin):
    """Decking: wood grain along `along`, plank joints every `width` metres across `axis`, random tone per plank."""
    def r(c):
        nt = c.nt
        col = _wood(c, base, dark, light, scale, along, dist, tint, stretch)
        u = MATH(nt, "ADD", MATH(nt, "DIVIDE", {"X": c.x, "Y": c.y, "Z": c.z}[axis], width), phase)
        fu = MATH(nt, "FRACT", u); du = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", fu, .5))
        rnd = WHITE(nt, XYZ(nt, MATH(nt, "FLOOR", u), 0.0, 0.0))
        col = MIX(nt, MATH(nt, "MULTIPLY", rnd, .35), col, light)
        half = groove_w / width * .5
        gm = SMOOTH(nt, du, .5 - half * 1.6, .5 - half * .6)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, du, .5 - half * 4, .5 - half * 1.6), .25), col, dark)   # worn edge
        return MIX(nt, gm, col, groove)
    return paint(name, r, edge=edge, edge_k=.8, **fin)


def paint_painted_wood(name, base, dark, light, scale=3.0, along="X", wear="8A6A4A", wear_amt=.5, **fin):
    """Painted timber: flat paint colour with the grain showing through softly and worn lighter edges."""
    def r(c):
        nt = c.nt
        s = {"X": (1, 9, 9), "Y": (9, 1, 9), "Z": (9, 9, 1)}[along]
        v = COORD(nt, scale=s)
        grain = WAVE(nt, v, scale=scale, dist=3.0, detail=2.0, dscale=1.2, direction={"X": "Y", "Y": "X", "Z": "X"}[along])
        col = RAMP(nt, grain, [(.0, dark), (.4, base), (1.0, light)])
        chips = SMOOTH(nt, NOISE(nt, c.pos, 20.0, 2.0), .68, .74)
        col = MIX(nt, MATH(nt, "MULTIPLY", chips, wear_amt), col, wear)
        return col
    return paint(name, r, edge=light, edge_k=.9, edge_r=.01, **fin)


def paint_cream_stone(name="Plinth", base="E6DCC6", dark="BFB096", light="F6F1E6", blocks=None, **fin):
    return dv4.paint_stone(name, base=base, dark=dark, light=light, moss_amt=.15, blocks=blocks, **fin)


# ================================================================================================= geometry helpers
def valance_ring(name, R, z_top, drop=.1, n=24, per=6, paint=None, out="Body", thickness=.008, loc=(0, 0, 0), rot=(0, 0, 0), flare=.02):
    """Hanging scalloped fabric edge around a circle: n round lobes hanging `drop` below z_top."""
    bm = bmesh.new(); seg = n * per
    top, bot = [], []
    for k in range(seg + 1):
        a = 2 * math.pi * k / seg
        t = (k % per) / per
        lobe = math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2))
        ca, sa = math.cos(a), math.sin(a)
        top.append(bm.verts.new((R * ca, R * sa, z_top)))
        bot.append(bm.verts.new(((R + flare) * ca, (R + flare) * sa, z_top - drop * (.35 + .65 * lobe))))
    for k in range(seg):
        f = bm.faces.new((top[k], top[k + 1], bot[k + 1], bot[k])); f.smooth = True
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint, out, loc, rot)
    if thickness:
        dv4.mod_solidify(ob, thickness, offset=0.0)
    return ob


def valance_line(name, p0, p1, drop=.1, n=6, per=6, paint=None, out="Body", thickness=.008, flare=.015):
    """Scalloped fabric strip hanging from the segment p0-p1 (its outward side is the right of p0->p1 seen from above)."""
    bm = bmesh.new(); seg = n * per
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0; d.z = 0
    nrm = Vector((d.y, -d.x, 0)).normalized() * flare
    top, bot = [], []
    for k in range(seg + 1):
        u = k / seg; t = (k % per) / per
        lobe = math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2))
        p = p0.lerp(p1, u)
        top.append(bm.verts.new(p))
        bot.append(bm.verts.new(p + nrm + Vector((0, 0, -drop * (.35 + .65 * lobe)))))
    for k in range(seg):
        f = bm.faces.new((top[k], top[k + 1], bot[k + 1], bot[k])); f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint, out)
    if thickness:
        dv4.mod_solidify(ob, thickness, offset=0.0)
    return ob


def rect_canopy(name, W, D, z_edge, peak, nx=16, ny=10, sag=.05, paint=None, out="Body", thickness=.01):
    """Rectangular umbrella cloth (half sizes W x D): ridge from the centre pole, edges sagging between the 4 rib tips."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=.5)
    for v in bm.verts:
        x, y = v.co.x * 2 * W, v.co.y * 2 * D
        ax, ay = abs(x) / W, abs(y) / D
        m = max(ax, ay)                              # 0 centre .. 1 edge (square-ish ridge lines to the corners)
        h = peak * (1 - m) ** 1.15
        # cloth sags between the 4 ribs (which run from the pole to the corners, ax == ay)
        n = (min(ax, ay) / m) if m > 1e-6 else 1.0
        s = sag * m * (1 - n * n)
        v.co = Vector((x, y, z_edge + h - s))
    for f in bm.faces:
        f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint, out)
    if thickness:
        dv4.mod_solidify(ob, thickness, offset=-1.0)
    return ob


def bulb(name, loc, r=.03, out="Anim Blink", color="FFE9B0", cap_paint=None, socket=True, hang=0.0):
    """Teardrop light bulb hanging from loc (the socket). Glass is an E_ override, the socket is baked."""
    if socket and cap_paint is not None:
        dv4.lathe(name + "Cap", [(0, 0), (r * .6, 0), (r * .55, -r * .9), (0, -r * .9)], seg=6, loc=loc, paint=cap_paint)
    prof = [(0, -r * .8), (r * .6, -r * .95), (r, -r * 1.9), (r * .7, -r * 2.75), (0, -r * 3.05)]
    return dv4.lathe(name, prof, seg=8, loc=loc, paint=None, out=out, mat_override="E_" + color)


def horse(prefix, loc, yaw, p_body, p_mane, p_saddle, p_blanket, p_hoof, p_eye, p_gold, out="Body", s=1.0):
    """Carousel horse galloping along local +Y (then yawed by `yaw` degrees). Hooves near local z 0, back at ~.42*s."""
    kw = dict(loc=loc, rot=(0, 0, yaw), out=out)
    S = lambda *p: tuple(v * s for v in p)
    W = lambda p: _w(loc, yaw, p)
    # body: chest to rump
    dv4.tube(prefix + "Body", [S(0, .20, .36), S(0, .05, .385), S(0, -.12, .375), S(0, -.23, .34)], radius=.098 * s, res=10, paint=p_body,
             resolution=3, taper=[(0, .55), (.18, 1.0), (.8, 1.0), (1, .55)], **kw)
    # neck + head
    dv4.tube(prefix + "Neck", [S(0, .15, .40), S(0, .25, .52), S(0, .31, .63)], radius=.06 * s, res=8, paint=p_body, resolution=3,
             taper=[(0, 1.15), (1, .8)], **kw)
    dv4.sphere(prefix + "Skull", .065 * s, loc=W(S(0, .31, .635)), rot=(0, 0, yaw), scale=(1, 1.05, 1), seg=10, rings=6, paint=p_body, out=out)
    dv4.tube(prefix + "Muzzle", [S(0, .33, .63), S(0, .40, .605), S(0, .455, .565)], radius=.052 * s, res=8, paint=p_body, resolution=3,
             taper=[(0, 1.0), (.6, .9), (1, .62)], **kw)
    for sx in (-1, 1):
        ear = dv4.lathe(prefix + "Ear%d" % sx, [(0, 0), (.017 * s, 0), (.013 * s, .028 * s), (0, .05 * s)], seg=8, paint=p_body, out=out)
        ear.location = W(S(sx * .03, .29, .67)); ear.rotation_euler = (math.radians(-20), math.radians(sx * 22), math.radians(yaw))
        dv4.sphere(prefix + "Eye%d" % sx, .014 * s, loc=W(S(sx * .052, .355, .645)), seg=6, rings=4, paint=p_eye, out=out)
    # mane: ridge along the neck + forelock
    dv4.tube(prefix + "Mane", [S(0, .17, .45), S(0, .25, .58), S(0, .30, .68), S(0, .35, .67)], radius=.036 * s, res=6, paint=p_mane, resolution=3,
             taper=[(0, .5), (.5, 1.0), (1, .45)], **kw)
    # tail
    dv4.tube(prefix + "Tail", [S(0, -.24, .36), S(0, -.33, .31), S(0, -.36, .18), S(0, -.33, .08)], radius=.036 * s, res=6, paint=p_mane, resolution=3,
             taper=[(0, .5), (.35, 1.0), (1, .25)], **kw)
    # legs (gallop: front legs reaching forward, hind legs stretched back)
    legs = [((.045, .14, .33), (.05, .19, .22), (.05, .26, .10)), ((-.045, .14, .33), (-.05, .15, .20), (-.05, .12, .06)),
            ((.045, -.16, .32), (.05, -.24, .20), (.05, -.33, .11)), ((-.045, -.16, .32), (-.05, -.19, .19), (-.05, -.17, .05))]
    for i, pts in enumerate(legs):
        pts = [S(*p) for p in pts]
        dv4.tube(prefix + "Leg%d" % i, pts, radius=.033 * s, res=6, paint=p_body, resolution=3, taper=[(0, 1.15), (.5, .85), (1, .8)], **kw)
        hp = pts[-1]
        hoof = dv4.lathe(prefix + "Hoof%d" % i, [(0, 0), (.034 * s, 0), (.034 * s, .03 * s), (.025 * s, .04 * s), (0, .04 * s)], seg=6, paint=p_hoof, out=out)
        hoof.location = W((hp[0], hp[1], hp[2] - .035 * s)); hoof.rotation_euler = (0, 0, math.radians(yaw))
    # tack: blanket, saddle, pommel, bridle ring, rein
    dv4.cube(prefix + "Blanket", (.24 * s, .24 * s, .02 * s), loc=W(S(0, -.03, .42)), rot=(0, 0, yaw), paint=p_blanket, bevel=.006, segs=1, out=out)
    dv4.cube(prefix + "Saddle", (.17 * s, .18 * s, .05 * s), loc=W(S(0, -.03, .45)), rot=(0, 0, yaw), paint=p_saddle, bevel=.016, segs=1, out=out)
    dv4.sphere(prefix + "Pommel", .026 * s, loc=W(S(0, .06, .47)), seg=8, rings=5, paint=p_gold, out=out)
    dv4.torus(prefix + "Bridle", .048 * s, .006 * s, loc=W(S(0, .41, .60)), rot=(65, 0, yaw), seg=10, minor=4, paint=p_gold, out=out)
    dv4.tube(prefix + "Rein", [S(0, .40, .58), S(.0, .30, .50), S(0, .12, .455)], radius=.006 * s, res=5, paint=p_saddle, resolution=4, **kw)


def _w(loc, yaw, p):
    a = math.radians(yaw)
    x, y, z = p
    return (loc[0] + x * math.cos(a) - y * math.sin(a), loc[1] + x * math.sin(a) + y * math.cos(a), loc[2] + z)


def spoke_wheel(prefix, loc, R=.3, rim=.03, spokes=10, paint_tire=None, paint_rim=None, paint_hub=None, out="Body", axis="X"):
    """Spoked cart wheel in the plane normal to `axis` (X: wheel on the left/right side of a cart)."""
    rot = (0, 90, 0) if axis == "X" else (90, 0, 0)
    dv4.torus(prefix + "Tire", R, rim, loc=loc, rot=rot, seg=24, minor=6, paint=paint_tire, out=out)
    dv4.torus(prefix + "Rim", R - rim * 1.1, rim * .55, loc=loc, rot=rot, seg=24, minor=5, paint=paint_rim, out=out)
    dv4.lathe(prefix + "Hub", [(0, -.05), (.05, -.05), (.06, -.03), (.06, .03), (.05, .05), (0, .05)], seg=12, loc=loc, rot=rot, paint=paint_hub, out=out)
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        if axis == "X":
            p0 = (loc[0], loc[1] + math.cos(a) * .05, loc[2] + math.sin(a) * .05)
            p1 = (loc[0], loc[1] + math.cos(a) * (R - rim), loc[2] + math.sin(a) * (R - rim))
        else:
            p0 = (loc[0] + math.cos(a) * .05, loc[1], loc[2] + math.sin(a) * .05)
            p1 = (loc[0] + math.cos(a) * (R - rim), loc[1], loc[2] + math.sin(a) * (R - rim))
        dv4.tube(prefix + "Spoke%d" % i, [p0, p1], radius=.009, res=6, paint=paint_rim, kind="POLY", resolution=1, out=out)


def swag(name, p0, p1, sag=.12, n=8, radius=.006, paint=None, out="Body"):
    """Hanging wire/garland between two points (parabolic sag). Returns the list of points for hanging things."""
    pts = []
    for i in range(n + 1):
        t = i / n
        p = Vector(p0).lerp(Vector(p1), t)
        p.z -= sag * 4 * t * (1 - t)
        pts.append(tuple(p))
    dv4.tube(name, pts, radius=radius, res=6, paint=paint, kind="POLY", resolution=1, out=out)
    return pts
