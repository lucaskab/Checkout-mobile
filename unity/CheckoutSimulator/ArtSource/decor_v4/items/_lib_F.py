"""_lib_F: extra paint recipes + geometry helpers for group F (popcorn-cart, ice-cream-cart, parasol-table, kiddie-ride, billboard).
All recipes use WORLD coordinates (parts are joined / transforms applied before the bake)."""
import math
import dv4
from dv4 import MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, paint, RNG


# ------------------------------------------------------------------------------------------------- small node utils
def dist2d(nt, a, b, ca, cb):
    """Euclidean distance between the sockets (a, b) and the constant point (ca, cb)."""
    da = MATH(nt, "SUBTRACT", a, ca); db = MATH(nt, "SUBTRACT", b, cb)
    return MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", da, da), MATH(nt, "MULTIPLY", db, db)))


def circle(nt, a, b, ca, cb, r, soft=.004):
    """1 inside the circle, 0 outside (soft anti-aliased edge)."""
    return SMOOTH(nt, dist2d(nt, a, b, ca, cb), r + soft, r - soft)


def ellipse(nt, a, b, ca, cb, ra, rb, ang=0.0, soft=.004):
    u, v = rot2d(nt, a, b, ca, cb, ang)
    d = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "POWER", MATH(nt, "DIVIDE", u, ra), 2.0), MATH(nt, "POWER", MATH(nt, "DIVIDE", v, rb), 2.0)))
    return SMOOTH(nt, d, 1.0 + soft / min(ra, rb), 1.0 - soft / min(ra, rb))


def rot2d(nt, a, b, ca, cb, ang):
    """Coordinates relative to (ca, cb) rotated by -ang degrees -> (u, v) sockets."""
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    da = MATH(nt, "SUBTRACT", a, ca); db = MATH(nt, "SUBTRACT", b, cb)
    u = MATH(nt, "ADD", MATH(nt, "MULTIPLY", da, c), MATH(nt, "MULTIPLY", db, s))
    v = MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", db, c), MATH(nt, "MULTIPLY", da, s))
    return u, v


def rect(nt, a, b, ca, cb, hw, hh, ang=0.0, round_=0.0, soft=.004):
    """Rounded rectangle mask."""
    u, v = rot2d(nt, a, b, ca, cb, ang)
    qu = MATH(nt, "SUBTRACT", MATH(nt, "ABSOLUTE", u), hw - round_)
    qv = MATH(nt, "SUBTRACT", MATH(nt, "ABSOLUTE", v), hh - round_)
    qu0 = MATH(nt, "MAXIMUM", qu, 0.0); qv0 = MATH(nt, "MAXIMUM", qv, 0.0)
    outside = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", qu0, qu0), MATH(nt, "MULTIPLY", qv0, qv0)))
    inside = MATH(nt, "MINIMUM", MATH(nt, "MAXIMUM", qu, qv), 0.0)
    d = MATH(nt, "SUBTRACT", MATH(nt, "ADD", outside, inside), round_)
    return SMOOTH(nt, d, soft, -soft)


def star(nt, a, b, ca, cb, r0, amp, n, ang=0.0, soft=.004):
    """Star burst: radius r0 + amp*cos(n*theta)."""
    da = MATH(nt, "SUBTRACT", a, ca); db = MATH(nt, "SUBTRACT", b, cb)
    d = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", da, da), MATH(nt, "MULTIPLY", db, db)))
    th = MATH(nt, "ARCTAN2", db, da)
    rr = MATH(nt, "ADD", r0, MATH(nt, "MULTIPLY", MATH(nt, "COSINE", MATH(nt, "ADD", MATH(nt, "MULTIPLY", th, float(n)), math.radians(ang))), amp))
    return SMOOTH(nt, MATH(nt, "SUBTRACT", d, rr), soft, -soft)


def star5(nt, a, b, ca, cb, r, ang=0.0, soft=.004):
    """Classic 5-point star (sharp)."""
    da = MATH(nt, "SUBTRACT", a, ca); db = MATH(nt, "SUBTRACT", b, cb)
    d = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", da, da), MATH(nt, "MULTIPLY", db, db)))
    th = MATH(nt, "ADD", MATH(nt, "ARCTAN2", db, da), math.radians(ang))
    # polar star: r(theta) = r * cos(pi/5) / cos((theta mod 2pi/5) - pi/5)
    m = MATH(nt, "MODULO", MATH(nt, "ADD", th, 20.0 * math.pi), 2 * math.pi / 5)
    rr = MATH(nt, "DIVIDE", r * math.cos(math.pi / 5) * .62, MATH(nt, "COSINE", MATH(nt, "SUBTRACT", m, math.pi / 5)))
    # mix between pentagon (inner) and spikes: use inner radius formula with sharp tips
    k = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", m, math.pi / 5))         # 0 at the middle of a side .. pi/5 at a tip
    tip = MATH(nt, "DIVIDE", k, math.pi / 5)                                  # 0..1
    rr2 = MATH(nt, "ADD", MATH(nt, "MULTIPLY", rr, MATH(nt, "SUBTRACT", 1.0, tip)), MATH(nt, "MULTIPLY", tip, r))
    return SMOOTH(nt, MATH(nt, "SUBTRACT", d, rr2), soft, -soft)


def union(nt, *masks):
    m = masks[0]
    for k in masks[1:]:
        m = MATH(nt, "MAXIMUM", m, k)
    return m


def sub(nt, a, b):
    return MATH(nt, "MULTIPLY", a, MATH(nt, "SUBTRACT", 1.0, b), clamp=True)


def inter(nt, a, b):
    return MATH(nt, "MULTIPLY", a, b)


def weave(nt, pos, scale=120.0, amt=.08, dark="000000"):
    """Fabric weave shading factor to mix dark into a colour."""
    w1 = WAVE(nt, pos, scale=scale, dist=0.0, detail=0.0, direction="X")
    w2 = WAVE(nt, pos, scale=scale, dist=0.0, detail=0.0, direction="Y")
    w3 = WAVE(nt, pos, scale=scale, dist=0.0, detail=0.0, direction="Z")
    w = MATH(nt, "MULTIPLY", MATH(nt, "ADD", MATH(nt, "ADD", w1, w2), w3), 1 / 3)
    return MATH(nt, "MULTIPLY", w, amt)


# ------------------------------------------------------------------------------------------------- paint recipes
def paint_enamel(name, base, dark=None, light=None, variation=.14, scratch=.12, hl=.18, **fin):
    """Painted metal / plastic body: soft colour mottle, light top sheen, faint scratches, lighter bevel edges."""
    dark = dark or "000000"; light = light or "FFFFFF"
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 6.0, 3.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, variation), base, dark)
        sc = SMOOTH(nt, NOISE(nt, COORD(nt, scale=(2, 60, 60)), 3.0, 2.0), .6, .68)
        col = MIX(nt, MATH(nt, "MULTIPLY", sc, scratch), col, light)
        sheen = SMOOTH(nt, c.nz, .3, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", sheen, hl), col, light)
        return col
    fin.setdefault("edge", light); fin.setdefault("edge_k", .7); fin.setdefault("edge_r", .008)
    return paint(name, r, **fin)


def paint_chrome(name="Chrome", base="C9D2D6", dark="6F7C86", light="F6FAFC", sky="DCE9F2", **fin):
    """Polished steel: vertical environment gradient (sky above, floor below) with a bright band and dark mottle."""
    def r(c):
        nt = c.nt
        g = MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.nz, .5), .5)
        col = RAMP(nt, g, [(.0, dark), (.35, base), (.5, light), (.62, base), (.8, sky), (1.0, light)])
        mot = NOISE(nt, c.pos, 12.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .18), col, dark)
        return col
    fin.setdefault("k_ao", .5); fin.setdefault("k_light", .3)
    return paint(name, r, edge=light, edge_k=1.0, edge_r=.006, **fin)


def paint_brass(name="Brass", base="D9A441", dark="8E6418", light="FFE59A", **fin):
    return dv4.paint_gold(name, base=base, dark=dark, light=light, **fin)


def paint_stripes(name, cols, period, axis="X", origin=0.0, cloth=True, dark="000000", edge=None, **fin):
    """Linear stripes along `axis` (world) - awnings, paper bags, tablecloths. cols cycle every `period` metres."""
    def r(c):
        nt = c.nt
        v = {"X": c.x, "Y": c.y, "Z": c.z}[axis]
        f = MATH(nt, "FRACT", MATH(nt, "DIVIDE", MATH(nt, "SUBTRACT", v, origin), period))
        n = len(cols)
        stops = []
        for i, h in enumerate(cols):
            stops.append((i / n, h))
        col = RAMP(nt, f, stops, "CONSTANT")
        if cloth:
            col = MIX(nt, weave(nt, c.pos, 140.0, .09), col, dark)
            mot = NOISE(nt, c.pos, 4.0, 2.0)
            col = MIX(nt, MATH(nt, "MULTIPLY", mot, .08), col, dark)
        return col
    return paint(name, r, edge=edge, **fin)


def paint_stripes_radial(name, cols, n, center=(0, 0), cloth=True, dark="000000", a0=0.0, edge=None, **fin):
    """Stripes by angle around the vertical axis through `center` - parasols, canopies, carousel roofs."""
    def r(c):
        nt = c.nt
        ang = MATH(nt, "ARCTAN2", MATH(nt, "SUBTRACT", c.y, center[1]), MATH(nt, "SUBTRACT", c.x, center[0]))
        u = MATH(nt, "FRACT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", ang, n / (2 * math.pi)), a0))
        m = len(cols)
        col = RAMP(nt, u, [(i / m, h) for i, h in enumerate(cols)], "CONSTANT")
        if cloth:
            col = MIX(nt, weave(nt, c.pos, 140.0, .09), col, dark)
            mot = NOISE(nt, c.pos, 3.0, 2.0)
            col = MIX(nt, MATH(nt, "MULTIPLY", mot, .08), col, dark)
        return col
    return paint(name, r, edge=edge, **fin)


def paint_checker(name, a, b, size=.08, axis="XY", **fin):
    def r(c):
        nt = c.nt
        p, q = {"XY": (c.x, c.y), "XZ": (c.x, c.z), "YZ": (c.y, c.z)}[axis]
        fp = MATH(nt, "FLOOR", MATH(nt, "DIVIDE", p, size)); fq = MATH(nt, "FLOOR", MATH(nt, "DIVIDE", q, size))
        k = MATH(nt, "MODULO", MATH(nt, "ADD", fp, fq), 2.0)
        k = MATH(nt, "ABSOLUTE", k)
        col = RAMP(nt, k, [(0.0, a), (.5, b)], "CONSTANT")
        mot = NOISE(nt, c.pos, 10.0, 2.0)
        return MIX(nt, MATH(nt, "MULTIPLY", mot, .08), col, "000000")
    return paint(name, r, **fin)


def paint_popcorn(name="Popcorn", base="FFF8E0", butter="F7CF62", dark="D1AA5E", **fin):
    """Puffy kernels: cream with buttery yellow patches, darker in the creases, per-kernel tint."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        bl = NOISE(nt, c.pos, 30.0, 2.0)
        col = RAMP(nt, bl, [(.3, base), (.75, butter)])
        col = MIX(nt, MATH(nt, "MULTIPLY", rnd, .35), col, butter)
        col = MIX(nt, MATH(nt, "MULTIPLY", c.crev, .35), col, dark)
        return col
    return paint(name, r, k_ao=.28, k_light=.3, edge="FFFFFF", edge_k=.5, edge_r=.006, **fin)


def paint_icecream(name, cols, sprinkles=True, **fin):
    """Scoop: per-scoop random flavour from `cols`, soft blotches, optional multicolour sprinkles."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        n = len(cols)
        col = RAMP(nt, MATH(nt, "MULTIPLY", rnd, .999), [(i / n, h) for i, h in enumerate(cols)], "CONSTANT")
        bl = NOISE(nt, c.pos, 25.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", bl, .18), col, "000000")
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, .95), .18), col, "FFFFFF")
        if sprinkles:
            d = VORO(nt, VMATH(nt, "MULTIPLY", c.pos, (1, 1, 1.0)), 90.0, "F1", "Distance")
            dot = SMOOTH(nt, d, .22, .14)
            cc = VORO(nt, c.pos, 90.0, "F1", "Color")
            scol = RAMP(nt, VMATH(nt, "DOT_PRODUCT", cc, (1, 0, 0)), [(0, "EE3E6A"), (.25, "FFD23F"), (.5, "3FB7E8"), (.75, "6BD36B"), (1.0, "FFFFFF")], "CONSTANT")
            keep = SMOOTH(nt, VMATH(nt, "DOT_PRODUCT", cc, (0, 1, 0)), .55, .65)
            col = MIX(nt, MATH(nt, "MULTIPLY", dot, keep), col, scol)
        return col
    fin.setdefault("k_ao", .5); fin.setdefault("k_light", .3)
    return paint(name, r, edge="FFFFFF", edge_k=.3, edge_r=.005, **fin)


def paint_waffle(name="Waffle", base="D9A05B", dark="9A5F2A", light="F0C98A", scale=55.0, axis="Z", **fin):
    """Waffle cone: diagonal grid of darker grooves on a toasted tan."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 12.0, 2.0)
        col = RAMP(nt, mot, [(.25, base), (.8, light)])
        v1 = COORD(nt, rot=(0, 0, 45) if axis == "Z" else (45, 0, 0))
        g1 = WAVE(nt, v1, scale=scale, dist=0.0, detail=0.0, direction="X")
        g2 = WAVE(nt, v1, scale=scale, dist=0.0, detail=0.0, direction="Y")
        g3 = WAVE(nt, v1, scale=scale, dist=0.0, detail=0.0, direction="Z")
        g = MATH(nt, "MAXIMUM", SMOOTH(nt, g1, .75, .9), MATH(nt, "MAXIMUM", SMOOTH(nt, g2, .75, .9), SMOOTH(nt, g3, .75, .9)))
        col = MIX(nt, MATH(nt, "MULTIPLY", g, .7), col, dark)
        col = MIX(nt, MATH(nt, "MULTIPLY", c.crev, .4), col, dark)
        return col
    return paint(name, r, k_ao=.6, edge=light, edge_k=.4, edge_r=.004, **fin)


def paint_marble(name="Marble", base="F1ECE2", vein="B9B0A3", light="FFFFFF", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 3.0, 2.0)
        col = RAMP(nt, mot, [(.3, base), (.8, light)])
        veins = SMOOTH(nt, NOISE(nt, c.pos, 2.0, 4.0, .6, 2.0), .49, .505)
        col = MIX(nt, MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, veins), .55), col, vein)
        veins2 = SMOOTH(nt, NOISE(nt, COORD(nt, scale=(1.3, 1.3, 1.3), rot=(0, 0, 40)), 2.5, 3.0, .6, 1.5), .49, .502)
        col = MIX(nt, MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, veins2), .35), col, vein)
        return col
    return paint(name, r, edge=light, edge_k=.4, edge_r=.006, **fin)


def paint_rubber(name="Rubber", base="2B2F33", light="5B6368", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 20.0, 2.0)
        col = RAMP(nt, mot, [(.3, base), (.9, light)])
        return col
    return paint(name, r, k_ao=.7, edge=light, edge_k=.9, edge_r=.006, **fin)


def paint_petal(name, cols, dark="000000", **fin):
    """Flower petals / blossoms: random colour per part from `cols`, darker towards the centre (crevices)."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        n = len(cols)
        col = RAMP(nt, MATH(nt, "MULTIPLY", rnd, .999), [(i / n, h) for i, h in enumerate(cols)], "CONSTANT")
        col = MIX(nt, MATH(nt, "MULTIPLY", c.crev, .4), col, dark)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .3, 1.0), .2), col, "FFFFFF")
        return col
    return paint(name, r, k_ao=.4, k_light=.3, **fin)


def paint_foliage(name="Foliage", base="4F9A36", dark="245A22", light="8CCB55", **fin):
    """Dense bush (for sphere blobs): leafy noise mottle, dark creases, lit top."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        n = VORO(nt, c.pos, 40.0, "F1", "Distance")
        col = RAMP(nt, n, [(.1, light), (.35, base), (.8, dark)])
        col = MIX(nt, MATH(nt, "MULTIPLY", rnd, .25), col, light)
        col = MIX(nt, MATH(nt, "MULTIPLY", c.crev, .5), col, dark)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, 1.0), .25), col, light)
        return col
    return paint(name, r, k_ao=.5, **fin)


# ------------------------------------------------------------------------------------------------- geometry helpers
def spoked_wheel(prefix, center, R, rim_r, hub_r, spokes, rim_p, hub_p, spoke_p, axis="X", out="Body", rim_minor=6, tyre_p=None, rim_seg=28):
    """Big cart wheel in the plane perpendicular to `axis` ("X": wheel in YZ, axle along X)."""
    cx, cy, cz = center
    rot = (0, 90, 0) if axis == "X" else (90, 0, 0)
    if tyre_p is not None:
        dv4.torus(prefix + "Tyre", R, rim_r * 1.35, loc=center, rot=rot, seg=36, minor=rim_minor, paint=tyre_p, out=out)
        dv4.torus(prefix + "Rim", R - rim_r * 1.1, rim_r, loc=center, rot=rot, seg=36, minor=rim_minor, paint=rim_p, out=out)
    else:
        dv4.torus(prefix + "Rim", R, rim_r, loc=center, rot=rot, seg=rim_seg, minor=rim_minor, paint=rim_p, out=out)
    hub_len = rim_r * 3.2
    hub_rot = (0, 90, 0) if axis == "X" else (-90, 0, 0)
    hub_loc = (cx - hub_len / 2, cy, cz) if axis == "X" else (cx, cy - hub_len / 2, cz)
    dv4.cylinder(prefix + "Hub", hub_r, hub_len, loc=hub_loc, rot=hub_rot, seg=14, paint=hub_p, out=out, bevel=hub_r * .3)
    dv4.sphere(prefix + "HubCap", hub_r * .7, loc=(cx + (hub_len * .5 if axis == "X" else 0), cy + (0 if axis == "X" else hub_len * .5), cz),
               seg=8, rings=5, paint=hub_p, out=out)
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        if axis == "X":
            p0 = (cx, cy + math.cos(a) * hub_r * .8, cz + math.sin(a) * hub_r * .8)
            p1 = (cx, cy + math.cos(a) * (R - rim_r * .5), cz + math.sin(a) * (R - rim_r * .5))
        else:
            p0 = (cx + math.cos(a) * hub_r * .8, cy, cz + math.sin(a) * hub_r * .8)
            p1 = (cx + math.cos(a) * (R - rim_r * .5), cy, cz + math.sin(a) * (R - rim_r * .5))
        dv4.tube(prefix + "Spoke%d" % i, [p0, p1], radius=rim_r * .45, res=6, paint=spoke_p, out=out, kind="POLY", resolution=1)


def helix(center, r, z0, z1, turns, n_per_turn=14):
    pts = []
    n = int(turns * n_per_turn)
    for i in range(n + 1):
        t = i / n
        a = t * turns * 2 * math.pi
        pts.append((center[0] + math.cos(a) * r, center[1] + math.sin(a) * r, z0 + (z1 - z0) * t))
    return pts


def scallop_strip(name, pts_fn, n, drop, loc_z, paint_, out="Body", thickness=.006, segs_per=6, depth=.0):
    """Scalloped valance hanging from a path: pts_fn(t) -> (x, y) along the edge (t 0..1), n scallops, each hangs `drop`.
    Built as a vertical ribbon whose bottom edge is a chain of half-circles."""
    import bmesh
    bm = bmesh.new()
    top = []; bot = []
    total = n * segs_per
    for i in range(total + 1):
        t = i / total
        x, y = pts_fn(t)
        k = (i % segs_per) / segs_per
        d = drop * (.35 + .65 * math.sin(math.pi * k)) if i not in (0, total) else drop * .35
        top.append(bm.verts.new((x, y, loc_z)))
        bot.append(bm.verts.new((x, y, loc_z - d)))
    for i in range(total):
        f = bm.faces.new((top[i], top[i + 1], bot[i + 1], bot[i])); f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint_, out)
    dv4.mod_solidify(ob, thickness, offset=0.0)
    return ob


def dome_bm(R, h, seg=32, rings=8, scallop=None, rise_pow=1.0):
    """Parasol / canopy skin: profile from rim (R, 0) to the top (0, h); scallop=(n, amp) adds radial waves."""
    prof = []
    for i in range(rings + 1):
        t = i / rings
        r = R * (1 - t)
        z = h * (1 - (1 - t) ** 2) ** rise_pow if t < 1 else h
        prof.append((r, z))
    return prof


def cone_scoop(prefix, loc, cone_h, cone_r, scoops, cone_p, scoop_p, out="Body", tilt=0.0, cherry_p=None):
    """Upright waffle cone with stacked scoops. loc = tip of the cone."""
    x, y, z = loc
    prof = [(0, 0), (cone_r * .2, cone_h * .08), (cone_r * .7, cone_h * .55), (cone_r, cone_h), (cone_r * 1.06, cone_h + cone_r * .15), (cone_r * .95, cone_h + cone_r * .2), (0, cone_h + cone_r * .2)]
    dv4.lathe(prefix + "Cone", prof, seg=14, loc=loc, rot=(tilt, 0, 0), paint=cone_p, out=out)
    zz = cone_h + cone_r * .35
    for i, s in enumerate(scoops):
        rr = cone_r * s
        dv4.sphere(prefix + "Scoop%d" % i, rr, loc=(x + RNG.uniform(-.1, .1) * rr, y + RNG.uniform(-.1, .1) * rr, z + zz + rr * .72),
                   seg=14, rings=9, paint=scoop_p, out=out, scale=(1, 1, .92))
        zz += rr * 1.35
    if cherry_p is not None:
        dv4.sphere(prefix + "Cherry", cone_r * .22, loc=(x, y, z + zz + cone_r * .05), seg=10, rings=6, paint=cherry_p, out=out)
        dv4.tube(prefix + "CherryStem", [(x, y, z + zz + cone_r * .2), (x + cone_r * .1, y, z + zz + cone_r * .45), (x + cone_r * .25, y, z + zz + cone_r * .55)],
                 radius=cone_r * .03, res=5, paint=cone_p, out=out, resolution=3)


def arched_roof(name, x0, x1, y0, y1, z0, rise, paint_, out="Body", nx=2, ny=14, thickness=.016, bow="Y", sag=0.0):
    """Awning / canopy skin: rectangle bowed upward along `bow` axis (arc rise), optional cloth sag between the ends."""
    import bmesh
    bm = bmesh.new()
    rows = []
    for i in range(nx + 1):
        tx = i / nx
        x = x0 + (x1 - x0) * tx
        row = []
        for j in range(ny + 1):
            ty = j / ny
            y = y0 + (y1 - y0) * ty
            u = (ty if bow == "Y" else tx) * 2 - 1
            z = z0 + rise * (1 - u * u) - sag * math.sin(math.pi * (tx if bow == "Y" else ty))
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])); f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint_, out)
    dv4.mod_solidify(ob, thickness, offset=0.0)
    return ob


def rect_path(x0, x1, y0, y1):
    """pts_fn for scallop_strip: walks the rectangle (x0..x1, y0..y1) clockwise from the front-left corner."""
    w, d = x1 - x0, y1 - y0
    P = 2 * (w + d)
    def f(t):
        s = t * P
        if s < w:
            return (x0 + s, y1)
        s -= w
        if s < d:
            return (x1, y1 - s)
        s -= d
        if s < w:
            return (x1 - s, y0)
        s -= w
        return (x0, y0 + s)
    return f


def scallop_strip_rect(name, x0, x1, y0, y1, z, drop, paint_, n_w=7, n_d=4, out="Body", thickness=.006, segs_per=6):
    """Scalloped valance around a rectangle, with the scallops lined up on each side."""
    import bmesh
    bm = bmesh.new()
    sides = [((x0, y1), (x1, y1), n_w), ((x1, y1), (x1, y0), n_d), ((x1, y0), (x0, y0), n_w), ((x0, y0), (x0, y1), n_d)]
    for (ax, ay), (bx, by), n in sides:
        top = []; bot = []
        total = n * segs_per
        for i in range(total + 1):
            t = i / total
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            k = (i % segs_per) / segs_per
            d = drop * (.3 + .7 * math.sin(math.pi * k)) if i % segs_per else drop * .3
            top.append(bm.verts.new((x, y, z)))
            bot.append(bm.verts.new((x, y, z - d)))
        for i in range(total):
            f = bm.faces.new((top[i], top[i + 1], bot[i + 1], bot[i])); f.smooth = True
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint_, out)
    if thickness > 0:
        dv4.mod_solidify(ob, thickness, offset=0.0)
    return ob


def pennant(name, base, h, L, paint_, out="Anim Sway", rot_z=0.0):
    """Small triangular pennant flag: base = top of the pole, flag streams toward +X (rotated rot_z)."""
    import bmesh
    bm = bmesh.new()
    x, y, z = base
    c, s = math.cos(math.radians(rot_z)), math.sin(math.radians(rot_z))
    def P(u, v):
        return (x + u * c, y + u * s, z + v)
    a = bm.verts.new(P(0, 0)); b = bm.verts.new(P(0, -h)); d = bm.verts.new(P(L * .55, -h * .5 + .006)); e = bm.verts.new(P(L, -h * .45))
    f = bm.faces.new((a, b, d)); f.smooth = True
    f = bm.faces.new((b, e, d)); f.smooth = True
    f = bm.faces.new((a, d, e)); f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint_, out)
    dv4.mod_solidify(ob, .004, offset=0.0)
    return ob


def circle_path(cx, cy, R, a0=0.0):
    def f(t):
        a = a0 + 2 * math.pi * t
        return (cx + math.cos(a) * R, cy + math.sin(a) * R)
    return f


def scallop_ring(name, cx, cy, R, n, drop, z, paint_, out="Body", thickness=.006, segs_per=5, flare=.0, ry=None):
    """Scalloped round valance hanging from a parasol rim at (cx, cy, z) with radius R; flare pushes the hem outward."""
    import bmesh
    bm = bmesh.new()
    top = []; bot = []
    total = n * segs_per
    for i in range(total):
        t = i / total
        a = 2 * math.pi * t
        k = (i % segs_per) / segs_per
        d = drop * (.3 + .7 * math.sin(math.pi * k)) if i % segs_per else drop * .3
        RY = R if ry is None else ry
        top.append(bm.verts.new((cx + math.cos(a) * R, cy + math.sin(a) * RY, z)))
        bot.append(bm.verts.new((cx + math.cos(a) * (R + flare), cy + math.sin(a) * (RY + flare), z - d)))
    for i in range(total):
        j = (i + 1) % total
        f = bm.faces.new((top[i], top[j], bot[j], bot[i])); f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint_, out)
    if thickness > 0:
        dv4.mod_solidify(ob, thickness, offset=0.0)
    return ob


def paint_icon_cone(name, base="F4EFE4", scoop="EE8FAE", scoop2="A8E6CF", cone="D9A05B", dark="C9BFA8", at=(0.0, 0.5), size=.12, **fin):
    """Cream panel with an ice-cream-cone pictogram (two scoops on a waffle triangle) drawn at world (x, z) = at."""
    def r(c):
        nt = c.nt
        ax, az = at
        col = base
        mot = NOISE(nt, c.pos, 6.0, 3.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .1), col, dark)
        # cone: triangle pointing down = rect clipped by two diagonals -> use a rotated square (diamond) lower half
        u, v = rot2d(nt, c.x, c.z, ax, az - size * .25, 0.0)
        tri = SMOOTH(nt, MATH(nt, "SUBTRACT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", MATH(nt, "ABSOLUTE", u), 1.6), MATH(nt, "MULTIPLY", v, -1.0)), size * .55), .004, -.004)
        tri = inter(nt, tri, SMOOTH(nt, v, -size * .6 - .004, -size * .6 + .004))
        # waffle lines on the cone
        g1 = WAVE(nt, COORD(nt, rot=(0, 45, 0)), scale=90.0, dist=0.0, detail=0.0, direction="X")
        g2 = WAVE(nt, COORD(nt, rot=(0, -45, 0)), scale=90.0, dist=0.0, detail=0.0, direction="X")
        g = MATH(nt, "MAXIMUM", SMOOTH(nt, g1, .8, .92), SMOOTH(nt, g2, .8, .92))
        ccol = MIX(nt, MATH(nt, "MULTIPLY", g, .6), cone, "8B5A2B")
        col = MIX(nt, tri, col, ccol)
        s1 = circle(nt, c.x, c.z, ax, az + size * .06, size * .36)
        s2 = circle(nt, c.x, c.z, ax, az + size * .5, size * .3)
        col = MIX(nt, s1, col, scoop)
        col = MIX(nt, s2, col, scoop2)
        # highlights
        col = MIX(nt, MATH(nt, "MULTIPLY", circle(nt, c.x, c.z, ax - size * .13, az + size * .14, size * .07), .6), col, "FFFFFF")
        col = MIX(nt, MATH(nt, "MULTIPLY", circle(nt, c.x, c.z, ax - size * .1, az + size * .56, size * .06), .6), col, "FFFFFF")
        return col
    fin.setdefault("edge", "FFFFFF"); fin.setdefault("edge_k", .6); fin.setdefault("edge_r", .006)
    return paint(name, r, **fin)


def paint_poster(name, x0, x1, z0, z1, base="F4EFE4", band="1F9A8E", **fin):
    """Sale poster (no letters/numbers): teal bands top & bottom, pink price tag with a star, gold starburst with a red %,
    and a row of fruit pictograms (apple, orange, banana, grapes, watermelon slice). Drawn in world (x, z) over the plate."""
    W, H = x1 - x0, z1 - z0
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    def r(c):
        nt = c.nt
        X, Z = c.x, c.z
        mot = NOISE(nt, c.pos, 8.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .06), base, "C9BFA8")
        # soft radial glow behind the burst
        glow = SMOOTH(nt, dist2d(nt, X, Z, cx + W * .27, cz + H * .14), W * .32, W * .05)
        col = MIX(nt, MATH(nt, "MULTIPLY", glow, .35), col, "FFE9B0")
        # bands
        top = SMOOTH(nt, Z, z1 - H * .085 - .004, z1 - H * .085 + .004)
        bot = SMOOTH(nt, Z, z0 + H * .085 + .004, z0 + H * .085 - .004)
        bandm = union(nt, top, bot)
        # little white dots along the bands
        dots = circle(nt, MATH(nt, "FRACT", MATH(nt, "DIVIDE", MATH(nt, "SUBTRACT", X, x0), W / 14)), MATH(nt, "FRACT", MATH(nt, "DIVIDE", MATH(nt, "SUBTRACT", Z, z0), H * .085)), .5, .5, .13, soft=.03)
        col = MIX(nt, bandm, col, MIX(nt, dots, band, "FBF8F1"))
        # ---------------- price tag (top-left): rotated rounded rect with a hole and a white star
        tx, tz = cx - W * .27, cz + H * .16
        tag = rect(nt, X, Z, tx, tz, W * .105, H * .115, ang=28.0, round_=.02)
        u, v = rot2d(nt, X, Z, tx, tz, 28.0)
        # pointed left end: cut the rectangle corners by two diagonals
        tip = SMOOTH(nt, MATH(nt, "SUBTRACT", MATH(nt, "ABSOLUTE", v), MATH(nt, "ADD", MATH(nt, "MULTIPLY", u, 1.25), W * .105 * 1.25 + H * .115 * .15)), .004, -.004)
        tag = inter(nt, tag, tip)
        hole = circle(nt, u, v, -W * .105 + .045, 0.0, .016)
        tag = sub(nt, tag, hole)
        tagcol = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, v, -.08, .08), .25), "D74A3C", "F06A5C")
        col = MIX(nt, tag, col, tagcol)
        col = MIX(nt, inter(nt, tag, circle(nt, u, v, -W * .105 + .045, 0.0, .024)), col, "FBF8F1")
        col = MIX(nt, hole, col, base)
        st = star5(nt, u, v, W * .02, 0.0, H * .075, ang=90.0)
        col = MIX(nt, st, col, "FFF1C4")
        # string from the hole up to the band
        # ---------------- starburst (top-right) with a red %
        bx, bz = cx + W * .27, cz + H * .14
        burst = star(nt, X, Z, bx, bz, H * .22, H * .035, 16)
        burst_in = star(nt, X, Z, bx, bz, H * .185, H * .03, 16, ang=180.0)
        col = MIX(nt, burst, col, "E0B040")
        col = MIX(nt, burst_in, col, "FFD97A")
        pu, pv = rot2d(nt, X, Z, bx, bz, 0.0)
        ring1 = sub(nt, circle(nt, pu, pv, -H * .075, H * .07, H * .048), circle(nt, pu, pv, -H * .075, H * .07, H * .022))
        ring2 = sub(nt, circle(nt, pu, pv, H * .075, -H * .07, H * .048), circle(nt, pu, pv, H * .075, -H * .07, H * .022))
        bar = rect(nt, X, Z, bx, bz, H * .02, H * .15, ang=-32.0, round_=.008)
        col = MIX(nt, union(nt, ring1, ring2, bar), col, "D74A3C")
        # ---------------- fruit row (bottom)
        fz = cz - H * .24
        # apple
        ax = cx - W * .36
        apple = sub(nt, circle(nt, X, Z, ax, fz, H * .11), circle(nt, X, Z, ax, fz + H * .11, H * .03))
        apple = union(nt, apple, circle(nt, X, Z, ax - H * .05, fz + H * .02, H * .085), circle(nt, X, Z, ax + H * .05, fz + H * .02, H * .085))
        acol = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, dist2d(nt, X, Z, ax - H * .03, fz + H * .03), H * .12, 0.0), .3), "C8362B", "F26C5A")
        col = MIX(nt, apple, col, acol)
        col = MIX(nt, rect(nt, X, Z, ax, fz + H * .12, H * .012, H * .035, round_=.004), col, "6B4128")
        col = MIX(nt, ellipse(nt, X, Z, ax + H * .05, fz + H * .13, H * .055, H * .022, ang=25.0), col, "5A9D33")
        col = MIX(nt, MATH(nt, "MULTIPLY", ellipse(nt, X, Z, ax - H * .045, fz + H * .045, H * .028, H * .045, ang=20.0), .7), col, "FFFFFF")
        # orange
        ox = cx - W * .18
        orange = circle(nt, X, Z, ox, fz, H * .10)
        spk = SMOOTH(nt, NOISE(nt, c.pos, 120.0, 1.0), .5, .62)
        ocol = MIX(nt, MATH(nt, "MULTIPLY", spk, .25), "EC862E", "C25F17")
        ocol = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, dist2d(nt, X, Z, ox - H * .03, fz + H * .03), H * .11, 0.0), .25), ocol, "FFB36B")
        col = MIX(nt, orange, col, ocol)
        col = MIX(nt, circle(nt, X, Z, ox, fz + H * .10, H * .016), col, "5A9D33")
        col = MIX(nt, ellipse(nt, X, Z, ox + H * .045, fz + H * .11, H * .05, H * .02, ang=20.0), col, "5A9D33")
        col = MIX(nt, MATH(nt, "MULTIPLY", ellipse(nt, X, Z, ox - H * .04, fz + H * .04, H * .025, H * .04, ang=20.0), .6), col, "FFFFFF")
        # banana: crescent
        bnx = cx
        bu, bv = rot2d(nt, X, Z, bnx, fz, -15.0)
        ban = sub(nt, circle(nt, bu, bv, 0.0, 0.0, H * .13), circle(nt, bu, bv, 0.0, H * .075, H * .125))
        ban = inter(nt, ban, SMOOTH(nt, bv, H * .02, H * .0))
        bcol = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, bv, -H * .13, -H * .02), .3), "E8B52A", "FFD95A")
        col = MIX(nt, ban, col, bcol)
        tips = union(nt, circle(nt, bu, bv, -H * .118, -H * .02, H * .022), circle(nt, bu, bv, H * .118, -H * .02, H * .022))
        col = MIX(nt, inter(nt, ban, tips), col, "6B4128")
        # grapes
        gx = cx + W * .18
        gr = None
        pos = [(0, .09), (-.05, .05), (.05, .05), (0, .0), (-.05, -.045), (.05, -.045), (0, -.09), (-.1, .005), (.1, .005)]
        for (dx, dz) in pos:
            m = circle(nt, X, Z, gx + dx * H, fz + dz * H, H * .035)
            gr = m if gr is None else union(nt, gr, m)
        gcol = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, dist2d(nt, X, Z, gx - H * .04, fz + H * .05), H * .15, 0.0), .35), "6A3C9C", "A77BD6")
        col = MIX(nt, gr, col, gcol)
        col = MIX(nt, rect(nt, X, Z, gx, fz + H * .14, H * .01, H * .035, round_=.004), col, "6B4128")
        col = MIX(nt, ellipse(nt, X, Z, gx + H * .05, fz + H * .15, H * .05, H * .022, ang=20.0), col, "5A9D33")
        # watermelon slice (half disk, flat side up)
        wx = cx + W * .36
        half = SMOOTH(nt, Z, fz + H * .02, fz + H * .0)
        wm = inter(nt, circle(nt, X, Z, wx, fz, H * .125), half)
        col = MIX(nt, wm, col, "3E8A2E")
        col = MIX(nt, inter(nt, circle(nt, X, Z, wx, fz, H * .108), half), col, "DDEFD0")
        col = MIX(nt, inter(nt, circle(nt, X, Z, wx, fz, H * .095), half), col, "E9455A")
        seeds = None
        for (dx, dz) in ((-.045, -.03), (.0, -.055), (.045, -.03), (-.02, -.01), (.025, -.01)):
            m = ellipse(nt, X, Z, wx + dx * H, fz + dz * H, H * .012, H * .018, ang=dx * 200)
            seeds = m if seeds is None else union(nt, seeds, m)
        col = MIX(nt, seeds, col, "2A1A14")
        # confetti stars
        for (dx, dz, s) in ((-.44, .32, .025), (-.1, .36, .02), (.1, .3, .018), (.44, .34, .022), (-.3, -.42, .018), (.3, -.42, .018)):
            col = MIX(nt, star5(nt, X, Z, cx + dx * W, cz + dz * H, H * s, ang=90.0), col, "E0B040")
        return col
    fin.setdefault("k_ao", .35); fin.setdefault("k_light", .15)
    return paint(name, r, **fin)


def paint_enamel_star(name, base, dark, light, star_at=(0, 0, 0), star_r=.08, star_col="E0B040", **fin):
    """Enamel body with a gold five-point star decal on the top surface around world point star_at (x, y)."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 6.0, 3.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .14), base, dark)
        sheen = SMOOTH(nt, c.nz, .3, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", sheen, .18), col, light)
        st = star5(nt, c.x, c.y, star_at[0], star_at[1], star_r, ang=90.0)
        st = inter(nt, st, SMOOTH(nt, c.nz, .6, .9))
        st = inter(nt, st, SMOOTH(nt, c.z, star_at[2] - .04, star_at[2] - .01))
        col = MIX(nt, st, col, star_col)
        col = MIX(nt, inter(nt, st, star5(nt, c.x, c.y, star_at[0], star_at[1], star_r * .55, ang=90.0)), col, "FFE38A")
        return col
    fin.setdefault("edge", light); fin.setdefault("edge_k", .7); fin.setdefault("edge_r", .008)
    return paint(name, r, **fin)


def paint_navy_stars(name, base="1D2B4F", dark="0C1328", light="6C7FB0", stars=(), star_r=.04, **fin):
    """Navy enamel sprinkled with gold stars at the given world (x, y) points (top faces only)."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 6.0, 3.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", mot, .14), base, dark)
        sheen = SMOOTH(nt, c.nz, .3, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", sheen, .15), col, light)
        m = None
        for (sx, sy) in stars:
            k = star5(nt, c.x, c.y, sx, sy, star_r, ang=90.0)
            m = k if m is None else union(nt, m, k)
        if m is not None:
            m = inter(nt, m, SMOOTH(nt, c.nz, .6, .9))
            col = MIX(nt, m, col, "E0B040")
        return col
    fin.setdefault("edge", light); fin.setdefault("edge_k", .7); fin.setdefault("edge_r", .008)
    return paint(name, r, **fin)
