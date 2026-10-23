"""_lib_G: extra geometry helpers and paint recipes for group G (umbrella-stand, monstera, can-pyramid, fruit-pyramid, tasting-table).
Everything here builds on dv4 (never edits it). Paint recipes read the Paint attribute (R, G, B) that the helpers below write:
  lathe_uv : R = angle around the axis 0..1 (0 = +X, .25 = +Y), G = height 0..1, B = per-part random
  pie      : R = 0 rim / .5 caps / 1 cut faces, G = height 0..1, B = random
  big_leaf : R = along the midrib, G = across (0..1), B = random (same convention as dv4.leaf, so dv4.paint_leaf works)
"""
import math
import bpy, bmesh
from mathutils import Vector
import dv4
from dv4 import RNG, MATH, VMATH, MIX, RAMP, COORD, NOISE, VORO, WAVE, ATTR, SMOOTH, paint


def E(x):
    """bmesh byte-colour layers store the value as sRGB and the Color Attribute node returns linear: encode so that the
    paint recipes read exactly the value we wrote (u, v coordinates)."""
    x = min(1.0, max(0.0, x))
    return x * 12.92 if x <= .0031308 else 1.055 * x ** (1 / 2.4) - .055


# ================================================================================================= geometry
def lathe_uv(name, profile, seg=24, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", cap=True, scallop=None, rnd=None, **kw):
    """Lathe (profile [(r, z)] bottom to top) that writes the Paint attribute: R = angle 0..1, G = height 0..1, B = random."""
    bm = bmesh.new(); lay = bm.loops.layers.color.new("Paint")
    z0 = profile[0][1]; z1 = profile[-1][1]; dz = max(1e-6, z1 - z0)
    b = RNG.random() if rnd is None else rnd
    rings = []
    for r, z in profile:
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            rr = r * (1 + scallop[1] * math.cos(scallop[0] * a)) if scallop and r > 1e-5 else r
            ring.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        vi0 = (profile[i][1] - z0) / dz; vi1 = (profile[i + 1][1] - z0) / dz
        for k in range(seg):
            a_, b_ = rings[i][k], rings[i][(k + 1) % seg]
            c_, d_ = rings[i + 1][(k + 1) % seg], rings[i + 1][k]
            try:
                f = bm.faces.new((a_, b_, c_, d_)); f.smooth = True
            except ValueError:
                continue
            us = (k / seg, (k + 1) / seg, (k + 1) / seg, k / seg)
            vs = (vi0, vi0, vi1, vi1)
            for lo, u, v in zip(f.loops, us, vs):
                lo[lay] = (E(u), E(v), b, 1.0)
    if cap:
        if profile[-1][0] > 1e-4:
            f = bm.faces.new(rings[-1]); f.smooth = False
            for lo in f.loops:
                lo[lay] = (E(.5), 1.0, b, 1.0)
        if profile[0][0] > 1e-4:
            f = bm.faces.new(list(reversed(rings[0]))); f.smooth = False
            for lo in f.loops:
                lo[lay] = (E(.5), 0.0, b, 1.0)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return dv4.from_bm(name, bm, paint, out, loc, rot, **kw)


def pie(name, r, h, a0=0.0, a1=360.0, seg=24, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", rnd=None, r_in=0.0, **kw):
    """Cylinder sector (cheese wheel with a wedge cut out, a wedge, a half-disk bread slice). Local Z up, base at z=0.
    Paint attribute: R = 0 rim / .5 caps / 1 cut faces, G = height, B = random."""
    bm = bmesh.new(); lay = bm.loops.layers.color.new("Paint")
    b = RNG.random() if rnd is None else rnd
    full = abs(a1 - a0) >= 359.9
    n = seg if full else seg + 1
    rings = []
    for z in (0.0, h):
        ring = []
        for k in range(n):
            a = math.radians(a0 + (a1 - a0) * k / seg)
            ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        rings.append(ring)
    def setattr_(f, R, G):
        for lo in f.loops:
            lo[lay] = (E(R), E(G), b, 1.0)
    for k in range(seg):
        k2 = (k + 1) % n
        f = bm.faces.new((rings[0][k], rings[0][k2], rings[1][k2], rings[1][k])); f.smooth = True
        for lo, g in zip(f.loops, (0, 0, 1, 1)):
            lo[lay] = (0.0, E(float(g)), b, 1.0)
    if full:
        f = bm.faces.new(rings[1]); f.smooth = False; setattr_(f, .5, 1.0)
        f = bm.faces.new(list(reversed(rings[0]))); f.smooth = False; setattr_(f, .5, 0.0)
    else:
        c0 = bm.verts.new((0, 0, 0)); c1 = bm.verts.new((0, 0, h))
        f = bm.faces.new([c1] + rings[1]); f.smooth = False; setattr_(f, .5, 1.0)
        f = bm.faces.new([c0] + list(reversed(rings[0]))); f.smooth = False; setattr_(f, .5, 0.0)
        f = bm.faces.new((c0, rings[0][0], rings[1][0], c1)); f.smooth = False
        for lo, g in zip(f.loops, (0, 0, 1, 1)):
            lo[lay] = (1.0, E(float(g)), b, 1.0)
        f = bm.faces.new((rings[0][-1], c0, c1, rings[1][-1])); f.smooth = False
        for lo, g in zip(f.loops, (0, 0, 1, 1)):
            lo[lay] = (1.0, E(float(g)), b, 1.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return dv4.from_bm(name, bm, paint, out, loc, rot, **kw)


def big_leaf(name, L, W, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", lobes=5, slit=.14, holes=True, bend=.3, cup=.1,
             droop=.0, thickness=.006, nl=26, nw=6, rnd=None, **kw):
    """Monstera deliciosa leaf: heart base, deep rounded lobes separated by slits to `slit` of the width, optional holes
    near the midrib. Local: base at origin, grows along +Y, Z up. Writes the Paint attribute like dv4.leaf."""
    b = RNG.random() if rnd is None else rnd
    t_lobe0 = .14          # the base is entire (no slits) up to here
    bounds = [t_lobe0 + (1 - t_lobe0) * (k / lobes) ** 1.15 for k in range(lobes + 1)]
    bounds = [round(t * nl) / nl for t in bounds]        # snap the slits to grid rows so every slit is sampled at full depth
    t_lobe0 = bounds[0]

    def width(t):
        # overall cordate outline: wide base, widest at .32, pointed tip
        if t < .32:
            w = .62 + .38 * math.sin(math.pi * .5 * t / .32)
        else:
            w = max(0.0, math.cos(math.pi * .5 * (t - .32) / .68)) ** .8
        w = max(w, .04)
        if t >= t_lobe0:
            for k in range(lobes):
                a, c = bounds[k], bounds[k + 1]
                if a <= t <= c:
                    u = (t - a) / max(1e-6, c - a)
                    e = min(1.0, min(u, 1 - u) / .2)            # broad flat lobe, narrow V slit at each boundary
                    lobe = slit + (1 - slit) * e ** .5
                    w *= lobe
                    break
        return w

    bm = bmesh.new(); lay = bm.loops.layers.color.new("Paint")
    rows = []
    for i in range(nl + 1):
        t = i / nl
        w = width(t) * W * .5
        y = t * L
        z = -bend * L * t ** 2.2 - droop * L * t
        row = []
        for j in range(nw + 1):
            s = -1 + 2 * j / nw
            x = s * w
            zz = z + cup * abs(s) ** 1.6 * w
            row.append(bm.verts.new((x, y, zz)))
        rows.append(row)
    # holes: skip grid cells near the midrib in the middle of the lower lobes
    skip = set()
    if holes:
        for k in range(1, min(lobes, 3)):
            a, c = bounds[k], bounds[k + 1]
            tm = (a + c) * .5
            im = int(round(tm * nl))
            for jj in (1, nw - 2):
                skip.add((im, jj))
    for i in range(nl):
        for j in range(nw):
            if (i, j) in skip:
                continue
            f = bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])); f.smooth = True
            for lo, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                lo[lay] = (ii / nl, jj / nw, b, 1.0)
    # the midrib row of the tip and base verts with w ~ 0 would make degenerate faces: merge them
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint, out, loc, rot, **kw)
    if thickness > 0:
        dv4.mod_solidify(ob, thickness, offset=0.0)
    return ob


def cloth_box(name, w, d, z_top, drop, loc=(0, 0, 0), paint=None, out="Body", nx=14, ny=8, nz=4, waves=5, amp=.015, flare=.03, **kw):
    """Table cloth: flat top w x d at z_top with a skirt hanging `drop`, flaring slightly and ending in a wavy hem."""
    bm = bmesh.new(); lay = bm.loops.layers.color.new("Paint")
    b = RNG.random()
    top = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            top[(i, j)] = bm.verts.new((-w / 2 + w * i / nx, -d / 2 + d * j / ny, z_top))
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new((top[(i, j)], top[(i + 1, j)], top[(i + 1, j + 1)], top[(i, j + 1)])); f.smooth = True
    # perimeter loop (counter-clockwise seen from above), starting at (-w/2, -d/2)
    per = []
    for i in range(nx):
        per.append(top[(i, 0)])
    for j in range(ny):
        per.append(top[(nx, j)])
    for i in range(nx, 0, -1):
        per.append(top[(i, ny)])
    for j in range(ny, 0, -1):
        per.append(top[(0, j)])
    n = len(per)
    rings = [per]
    for k in range(1, nz + 1):
        t = k / nz
        ring = []
        for idx, v in enumerate(per):
            x, y = v.co.x, v.co.y
            fx = flare * t * (1 if abs(x) > w / 2 - 1e-6 else 0) * (1 if x > 0 else -1)
            fy = flare * t * (1 if abs(y) > d / 2 - 1e-6 else 0) * (1 if y > 0 else -1)
            # hem wave along the perimeter + soft folds in the middle of the drop
            ph = idx / n * waves * 2 * math.pi
            fold = math.sin(ph * 2.0) * amp * 1.2 * math.sin(math.pi * t)
            zz = z_top - drop * t + (math.sin(ph) * amp if k == nz else 0.0)
            ring.append(bm.verts.new((x + fx + fold * (0 if abs(x) < w / 2 - 1e-6 else 1), y + fy + fold * (0 if abs(y) < d / 2 - 1e-6 else 1), zz)))
        rings.append(ring)
    for k in range(nz):
        for idx in range(n):
            a_, b_ = rings[k][idx], rings[k][(idx + 1) % n]
            c_, d_ = rings[k + 1][(idx + 1) % n], rings[k + 1][idx]
            f = bm.faces.new((a_, d_, c_, b_)); f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        for lo in f.loops:
            lo[lay] = (0.0, 0.0, b, 1.0)
    ob = dv4.from_bm(name, bm, paint, out, loc, **kw)
    dv4.mod_solidify(ob, .006, offset=-1.0)
    return ob


def flag(name, w, h, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", nx=6, ny=8, swallow=.3, wave=.02, **kw):
    """Hanging banner: top edge at the local origin along X, hangs down -Z, optional swallow-tail cut at the bottom.
    Paint attribute: R = across 0..1, G = 1 at the top .. 0 at the bottom."""
    bm = bmesh.new(); lay = bm.loops.layers.color.new("Paint")
    b = RNG.random()
    grid = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            u, v = i / nx, j / ny
            x = -w / 2 + w * u
            z = -h * v
            y = math.sin(v * math.pi * 1.5) * wave * math.sin(u * math.pi) + math.sin(u * 6.0 + v * 3.0) * wave * .4 * v
            grid[(i, j)] = bm.verts.new((x, y, z))
    for i in range(nx):
        for j in range(ny):
            if swallow > 0 and j == ny - 1:
                # cut the swallow tail: skip the central cells of the last row progressively
                cu = abs((i + .5) / nx - .5) * 2      # 0 centre .. 1 edge
                if cu < 1 - (1 - swallow) * 1.0 and cu < .67:
                    continue
            f = bm.faces.new((grid[(i, j)], grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)])); f.smooth = True
            for lo, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lo[lay] = (E(ii / nx), E(1 - jj / ny), b, 1.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = dv4.from_bm(name, bm, paint, out, loc, rot, **kw)
    dv4.mod_solidify(ob, .004, offset=0.0)
    return ob


def wedge(name, r, h, ang=40.0, loc=(0, 0, 0), rot=(0, 0, 0), paint=None, out="Body", **kw):
    """Cheese wedge: a pie sector with the point at the local origin (helper around pie())."""
    return pie(name, r, h, -ang / 2, ang / 2, seg=max(3, int(ang / 10)), loc=loc, rot=rot, paint=paint, out=out, **kw)


# ================================================================================================= paint recipes
def _hl_angle(c, light_az=110.0, width=.35):
    """0..1 highlight band around a vertical axis facing the light azimuth (fake cylindrical reflection)."""
    nt = c.nt
    nx = VMATH(nt, "DOT_PRODUCT", c.geo.outputs["Normal"], (math.cos(math.radians(light_az)), math.sin(math.radians(light_az)), 0.0))
    return SMOOTH(nt, nx, 1 - width - .25, 1 - width + .25)


def paint_brass(name="Brass", base="B8812C", dark="4F3608", light="F0CC6A", hammered=.5, **fin):
    """Warm polished brass with hammered dents, a vertical reflection band and bright edges."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 7.0, 2.0)
        col = RAMP(nt, mot, [(.2, dark), (.55, base), (.9, light)])
        if hammered > 0:
            dent = VORO(nt, c.pos, 38.0, "F1", "Distance")
            dsh = SMOOTH(nt, dent, .25, .02)
            col = MIX(nt, MATH(nt, "MULTIPLY", dsh, hammered * .35), col, light)
            col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, dent, .02, .25), hammered * .25), col, dark)
        hl = _hl_angle(c, 120.0, .3)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .35), col, light)
        hl2 = _hl_angle(c, 250.0, .2)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl2, .18), col, light)
        sh = _hl_angle(c, 330.0, .3)
        col = MIX(nt, MATH(nt, "MULTIPLY", sh, .5), col, dark)
        top = SMOOTH(nt, c.nz, .3, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", top, .15), col, light)
        return col
    return paint(name, r, k_light=.25, edge=light, edge_k=.8, edge_r=.004, **fin)


def paint_steel(name="Steel", base="AEB8BE", dark="6E7A82", light="EEF3F5", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 12.0, 2.0)
        col = RAMP(nt, mot, [(.25, dark), (.6, base), (.95, light)])
        hl = _hl_angle(c, 120.0, .35)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .5), col, light)
        top = SMOOTH(nt, c.nz, .3, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", top, .35), col, light)
        return col
    return paint(name, r, edge=light, edge_k=1.0, edge_r=.004, **fin)


def paint_canopy(name, a="D74A3C", b="F4EFE4", panels=8, strap="2A2E3A", strap_v=(.80, .86), pattern="panels", dots="FBF8F1", **fin):
    """Furled umbrella canopy on a lathe_uv: alternating panel colours (or stripes / polka dots), pleat shading, a strap band."""
    def r(c):
        nt = c.nt
        u, v, rnd = ATTR(nt)
        weave = NOISE(nt, c.pos, 160.0, 2.0)
        if pattern == "panels":
            idx = MATH(nt, "FRACT", MATH(nt, "MULTIPLY", MATH(nt, "ADD", MATH(nt, "MULTIPLY", u, panels), .5), .5))
            m = SMOOTH(nt, idx, .48, .52)
            col = MIX(nt, m, a, b)
        elif pattern == "stripes":
            s = MATH(nt, "FRACT", MATH(nt, "MULTIPLY", v, 7.0))
            col = MIX(nt, SMOOTH(nt, s, .45, .55), a, b)
        elif pattern == "dots":
            d = VORO(nt, VMATH(nt, "MULTIPLY", c.pos, (1, 1, 1)), 55.0, "F1", "Distance")
            col = MIX(nt, SMOOTH(nt, d, .22, .14), a, dots)
        else:
            col = a
        # seams between panels (dark thin lines at the pleat valleys)
        ph = MATH(nt, "FRACT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", u, panels), .5))
        seam = SMOOTH(nt, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", ph, .5)), .06, .025)
        col = MIX(nt, MATH(nt, "MULTIPLY", seam, .35), col, "1A1A22")
        # pleat shading: darker in the valleys
        valley = MATH(nt, "ADD", MATH(nt, "MULTIPLY", MATH(nt, "COSINE", MATH(nt, "MULTIPLY", u, panels * 2 * math.pi)), .5), .5)
        col = MIX(nt, MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, valley), .22), col, "000000")
        col = MIX(nt, MATH(nt, "MULTIPLY", weave, .08), col, "000000")
        # strap
        sm = MATH(nt, "MULTIPLY", SMOOTH(nt, v, strap_v[0] - .01, strap_v[0] + .01), SMOOTH(nt, v, strap_v[1] + .01, strap_v[1] - .01))
        col = MIX(nt, sm, col, strap)
        return col
    return paint(name, r, k_ao=.55, k_light=.4, **fin)


def paint_speckle(name="Ceramic", base="F1E9D8", dark="D9CDB6", speck="7A5A42", speck_amt=.5, glaze_z=None, raw="C8805A", raw_dark="9A5A3A", **fin):
    """Speckled stoneware glaze (oatmeal with brown flecks, glossy top highlight); unglazed clay below glaze_z."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 6.0, 3.0)
        col = RAMP(nt, mot, [(.3, dark), (.75, base)])
        d = VORO(nt, c.pos, 60.0, "F1", "Distance")
        dens = NOISE(nt, c.pos, 9.0, 2.0)
        sp = MATH(nt, "MULTIPLY", SMOOTH(nt, d, .2, .1), SMOOTH(nt, dens, .3, .55))
        col = MIX(nt, MATH(nt, "MULTIPLY", sp, speck_amt), col, speck)
        d2 = VORO(nt, VMATH(nt, "ADD", c.pos, (3.1, 1.7, .3)), 110.0, "F1", "Distance")
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, d2, .14, .07), speck_amt * .6), col, "5A4332")
        hl = SMOOTH(nt, c.nz, .25, .9)
        col = MIX(nt, MATH(nt, "MULTIPLY", hl, .25), col, "FFFFFF")
        if glaze_z is not None:
            cmot = NOISE(nt, c.pos, 12.0, 3.0)
            clay = RAMP(nt, cmot, [(.3, raw_dark), (.75, raw)])
            gm = SMOOTH(nt, c.z, glaze_z - .004, glaze_z + .004)
            col = MIX(nt, gm, clay, col)
        return col
    return paint(name, r, edge="FFFFFF", edge_k=.6, edge_r=.006, **fin)


def paint_coir(name="Coir", base="8A6A48", dark="5A4128", light="B89468", moss="6D8E3C", twine="D6B47C", twine_pitch=.11, twine_w=.012, cx=0.0, cy=0.0, **fin):
    """Moss pole: coir fibres wound around the pole, patches of moss, a helix of twine (Blender z / angle, pole axis = world Z at x=y=0)."""
    def r(c):
        nt = c.nt
        v = COORD(nt, scale=(1, 1, 18))
        fib = WAVE(nt, v, scale=14.0, dist=6.0, detail=3.0, dscale=1.5, direction="Z")
        col = RAMP(nt, fib, [(.15, dark), (.55, base), (.9, light)])
        fine = NOISE(nt, c.pos, 120.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", fine, .2), col, dark)
        mm = SMOOTH(nt, NOISE(nt, c.pos, 7.0, 3.0), .5, .66)
        mcol = RAMP(nt, NOISE(nt, c.pos, 40.0, 2.0), [(.3, "4E6E2A"), (.8, moss)])
        col = MIX(nt, mm, col, mcol)
        if twine_pitch > 0:
            ang = MATH(nt, "ARCTAN2", MATH(nt, "SUBTRACT", c.y, cy), MATH(nt, "SUBTRACT", c.x, cx))
            ph = MATH(nt, "ADD", MATH(nt, "DIVIDE", c.z, twine_pitch), MATH(nt, "DIVIDE", ang, 2 * math.pi))
            d = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "FRACT", ph), .5))
            tw = SMOOTH(nt, d, twine_w / twine_pitch + .01, twine_w / twine_pitch - .01)
            tcol = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 80.0, 2.0), .35), twine, "9E7F4E")
            col = MIX(nt, tw, col, tcol)
        return col
    return paint(name, r, k_ao=.6, k_light=.3, **fin)


def paint_label(name, base="D74A3C", stripe="F4EFE4", fruit="F2B233", fruit_dark="C9821A", leaf="4E9A3C", r=.045, h=.12, rim=.1,
                metal=("AEB8BE", "6E7A82", "EEF3F5"), fruit_v=.5, fruit_r=.021, band=.14, **fin):
    """Tin can on a lathe_uv (R = angle, G = height): steel rims, a colourful paper label with cream bands and a round fruit
    pictogram (with a leaf) on the front (+Y) and the back."""
    circ = 2 * math.pi * r
    def r_(c):
        nt = c.nt
        u, v, rnd = ATTR(nt)
        # metal
        mot = NOISE(nt, c.pos, 12.0, 2.0)
        met = RAMP(nt, mot, [(.25, metal[1]), (.6, metal[0]), (.95, metal[2])])
        hl = _hl_angle(c, 120.0, .35)
        met = MIX(nt, MATH(nt, "MULTIPLY", hl, .5), met, metal[2])
        met = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .3, .95), .35), met, metal[2])
        # label
        grain = NOISE(nt, c.pos, 90.0, 2.0)
        lab = MIX(nt, MATH(nt, "MULTIPLY", grain, .08), base, "000000")
        for v0 in (band, 1 - band):
            m = SMOOTH(nt, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", v, v0)), .035, .02)
            lab = MIX(nt, m, lab, stripe)
        # fruit pictogram front and back: a disc with a darker lower half, a highlight and a leaf
        for uc in (.25, .75):
            du = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", u, uc), circ)
            dv = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", v, fruit_v), h)
            d = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", du, du), MATH(nt, "MULTIPLY", dv, dv)))
            disc = SMOOTH(nt, d, fruit_r + .002, fruit_r - .002)
            fcol = MIX(nt, SMOOTH(nt, dv, .004, -.012), fruit, fruit_dark)
            # highlight dot
            dh = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "POWER", MATH(nt, "ADD", du, fruit_r * .4), 2.0), MATH(nt, "POWER", MATH(nt, "SUBTRACT", dv, fruit_r * .4), 2.0)))
            fcol = MIX(nt, SMOOTH(nt, dh, fruit_r * .32, fruit_r * .2), fcol, "FFF6DC")
            # cream outline ring
            ring = SMOOTH(nt, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", d, fruit_r + .003)), .004, .0015)
            lab = MIX(nt, ring, lab, stripe)
            lab = MIX(nt, disc, lab, fcol)
            # leaf: tilted ellipse above the fruit
            lx = MATH(nt, "SUBTRACT", du, fruit_r * .35); ly = MATH(nt, "SUBTRACT", dv, fruit_r * 1.15)
            ex = MATH(nt, "ADD", MATH(nt, "MULTIPLY", lx, .8), MATH(nt, "MULTIPLY", ly, .6))
            ey = MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", ly, .8), MATH(nt, "MULTIPLY", lx, .6))
            el = MATH(nt, "ADD", MATH(nt, "POWER", MATH(nt, "DIVIDE", ex, fruit_r * .62), 2.0), MATH(nt, "POWER", MATH(nt, "DIVIDE", ey, fruit_r * .3), 2.0))
            lab = MIX(nt, SMOOTH(nt, el, 1.15, .9), lab, leaf)
        # the label is a paper sleeve: slight AO-ish darkening near the rims
        lab = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", v, .5)), .3, .42), .25), lab, "000000")
        lab = MIX(nt, MATH(nt, "MULTIPLY", hl, .18), lab, "FFFFFF")
        lab = MIX(nt, MATH(nt, "MULTIPLY", rnd, .12), lab, "FFFFFF")
        inlab = MATH(nt, "MULTIPLY", SMOOTH(nt, v, rim - .01, rim + .01), SMOOTH(nt, v, 1 - rim + .01, 1 - rim - .01))
        return MIX(nt, inlab, met, lab)
    return paint(name, r_, k_ao=.5, k_light=.3, edge=metal[2], edge_k=.6, edge_r=.003, **fin)


def paint_fruit(name, base, dark, light, blush=None, blush_amt=.5, pores=0.0, speck=0.0, hl="FFFFFF", hl_amt=.3, tint=.18, **fin):
    """Fruit skin: mottled base, optional blush side (noise), pores (orange) or lenticel specks (apple), top highlight, per-fruit tint."""
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        mot = NOISE(nt, c.pos, 9.0, 3.0)
        col = RAMP(nt, mot, [(.2, dark), (.5, base), (.98, light)])
        if blush is not None:
            bm = SMOOTH(nt, NOISE(nt, VMATH(nt, "ADD", c.pos, (7.3, 2.1, 5.5)), 4.5, 2.0), .42, .62)
            col = MIX(nt, MATH(nt, "MULTIPLY", bm, blush_amt), col, blush)
        if pores > 0:
            d = VORO(nt, c.pos, 220.0, "F1", "Distance")
            col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, d, .3, .1), pores), col, dark)
        if speck > 0:
            d = VORO(nt, VMATH(nt, "ADD", c.pos, (1.3, 4.1, .7)), 160.0, "F1", "Distance")
            col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, d, .09, .04), speck), col, "FFF3D0")
        col = MIX(nt, MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", rnd, .5), tint), col, light)
        top = SMOOTH(nt, c.nz, .5, 1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", top, hl_amt), col, hl)
        return col
    return paint(name, r, k_ao=.6, k_light=.28, **fin)


def paint_gingham(name="Cloth", base="F6F1E6", check="D9574A", scale=12.0, amt=.85, **fin):
    """Gingham: two overlapping stripe families on cream linen, with a woven thread texture."""
    def r(c):
        nt = c.nt
        def checks(a, b):
            sx = MATH(nt, "FRACT", MATH(nt, "MULTIPLY", a, scale)); sy = MATH(nt, "FRACT", MATH(nt, "MULTIPLY", b, scale))
            mx = SMOOTH(nt, sx, .48, .52); my = SMOOTH(nt, sy, .48, .52)
            return MATH(nt, "MULTIPLY", MATH(nt, "ADD", mx, my), .5)
        # top faces: checks in x/y; hanging skirt: checks in (x + y)/z so the pattern keeps running down the sides
        m = MIX(nt, SMOOTH(nt, MATH(nt, "ABSOLUTE", c.nz), .4, .7), checks(MATH(nt, "ADD", c.x, c.y), c.z), checks(c.x, c.y))
        col = MIX(nt, MATH(nt, "MULTIPLY", m, amt), base, check)
        weave = MATH(nt, "MULTIPLY", WAVE(nt, c.pos, scale=160.0, dist=0.0, detail=0.0, direction="X"), WAVE(nt, c.pos, scale=160.0, dist=0.0, detail=0.0, direction="Y"))
        col = MIX(nt, MATH(nt, "MULTIPLY", weave, .12), col, "000000")
        return col
    return paint(name, r, k_ao=.65, k_light=.35, **fin)


def paint_linen(name="Linen", base="F4EFE4", dark="DED5C4", stripe=None, stripe_w=.025, stripe_z=None, **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 8.0, 3.0)
        col = RAMP(nt, mot, [(.3, dark), (.8, base)])
        weave = MATH(nt, "MULTIPLY", WAVE(nt, c.pos, scale=170.0, dist=0.0, detail=0.0, direction="X"), WAVE(nt, c.pos, scale=170.0, dist=0.0, detail=0.0, direction="Y"))
        col = MIX(nt, MATH(nt, "MULTIPLY", weave, .1), col, "000000")
        return col
    return paint(name, r, k_ao=.65, k_light=.35, **fin)


def paint_cheese(name="Cheese", paste="F3C75A", paste_dark="D9A33A", hole="B8832A", holes=.6, rind="E8B64B", rind_dark="B98A2C", wax=None, **fin):
    """Cheese on pie(): paste with round holes on the cut faces (R=1) and caps, rind (or wax colour) on the rim (R=0)."""
    def r(c):
        nt = c.nt
        R, G, rnd = ATTR(nt)
        mot = NOISE(nt, c.pos, 14.0, 2.0)
        pc = RAMP(nt, mot, [(.3, paste_dark), (.8, paste)])
        if holes > 0:
            d = VORO(nt, c.pos, 70.0, "F1", "Distance")
            dens = NOISE(nt, VMATH(nt, "ADD", c.pos, (2.0, 5.0, 1.0)), 20.0, 2.0)
            hm = MATH(nt, "MULTIPLY", SMOOTH(nt, d, .3, .18), SMOOTH(nt, dens, .4, .55))
            pc = MIX(nt, MATH(nt, "MULTIPLY", hm, holes), pc, hole)
        rc = RAMP(nt, NOISE(nt, c.pos, 10.0, 3.0), [(.3, rind_dark), (.8, rind)])
        if wax:
            rc = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .3, .95), .3), wax, "FFFFFF")
            rc = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 20.0, 2.0), .12), rc, "000000")
        col = MIX(nt, SMOOTH(nt, R, .2, .4), rc, pc)
        if wax:
            # waxed wheel: caps are wax too, only the cut faces (R = 1) show the paste
            col = MIX(nt, SMOOTH(nt, R, .7, .9), rc, pc)
        return col
    return paint(name, r, k_ao=.55, k_light=.35, edge="FFF2C8", edge_k=.5, edge_r=.004, **fin)


def paint_bread(name="Bread", crust="C9803E", crust_dark="8E4D1C", crust_light="E8B36A", crumb="F0DFB8", crumb_dark="D6BE8C", flour=.25, slashes=0.0, **fin):
    """Bread on pie()/tubes: crust with flour dusting (top), crumb on cut faces (R = 1 or caps R = .5) for slices."""
    def r(c):
        nt = c.nt
        R, G, rnd = ATTR(nt)
        mot = NOISE(nt, c.pos, 10.0, 3.0)
        cr = RAMP(nt, mot, [(.2, crust_dark), (.5, crust), (.9, crust_light)])
        cr = MIX(nt, MATH(nt, "MULTIPLY", c.crev, .35), cr, crust_dark)
        fl = MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .4, .95), SMOOTH(nt, NOISE(nt, c.pos, 30.0, 2.0), .45, .7))
        cr = MIX(nt, MATH(nt, "MULTIPLY", fl, flour), cr, "FBF3E2")
        if slashes > 0:
            ph = MATH(nt, "FRACT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", c.x, slashes), MATH(nt, "MULTIPLY", c.y, slashes * .6)))
            sl = SMOOTH(nt, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", ph, .5)), .1, .05)
            sl = MATH(nt, "MULTIPLY", sl, SMOOTH(nt, c.nz, .5, .9))
            cr = MIX(nt, sl, cr, crumb)
        cm = RAMP(nt, NOISE(nt, c.pos, 60.0, 3.0), [(.3, crumb_dark), (.7, crumb)])
        d = VORO(nt, c.pos, 160.0, "F1", "Distance")
        cm = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, d, .25, .12), .5), cm, crumb_dark)
        return MIX(nt, SMOOTH(nt, R, .2, .4), cr, cm)
    return paint(name, r, k_ao=.55, k_light=.35, **fin)


def paint_grape(name="Grape", base="6B3F8E", dark="3E2358", light="9A6CC0", bloom="C8B4DC", **fin):
    def r(c):
        nt = c.nt
        t, s, rnd = ATTR(nt)
        mot = NOISE(nt, c.pos, 30.0, 2.0)
        col = RAMP(nt, mot, [(.3, dark), (.8, base)])
        col = MIX(nt, MATH(nt, "MULTIPLY", rnd, .35), col, light)
        top = SMOOTH(nt, c.nz, .2, .95)
        col = MIX(nt, MATH(nt, "MULTIPLY", top, .4), col, bloom)
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .75, 1.0), .5), col, "FFFFFF")
        return col
    return paint(name, r, k_ao=.6, k_light=.35, **fin)


def paint_chalkboard(name="Chalk", slate="2E3A3A", slate_dark="1F2929", chalk="F6F2E4", drawing=None, **fin):
    """Dark slate with a chalk drawing: drawing(c) -> mask socket (0..1) in world coords."""
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 15.0, 3.0)
        col = RAMP(nt, mot, [(.3, slate_dark), (.8, slate)])
        dust = MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 60.0, 2.0), .12)
        col = MIX(nt, dust, col, chalk)
        if drawing is not None:
            m = drawing(c)
            rough = MATH(nt, "ADD", .7, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 200.0, 1.0), .3))
            col = MIX(nt, MATH(nt, "MULTIPLY", m, rough, clamp=True), col, chalk)
        return col
    return paint(name, r, k_ao=.5, k_light=.3, **fin)


def chalk_apple(cx, cz, R, plane="XZ"):
    """Drawing callback for paint_chalkboard: apple outline + stem + leaf, centred at (cx, cz) in the given world plane."""
    def d(c):
        nt = c.nt
        a = c.x if plane == "XZ" else c.y
        dx = MATH(nt, "SUBTRACT", a, cx); dz = MATH(nt, "SUBTRACT", c.z, cz)
        # apple body: two overlapping circles side by side, slightly flattened
        rs = []
        for ox in (-R * .32, R * .32):
            rs.append(MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "POWER", MATH(nt, "SUBTRACT", dx, ox), 2.0), MATH(nt, "POWER", MATH(nt, "MULTIPLY", dz, 1.08), 2.0))))
        m = None
        for r_ in rs:
            ring = SMOOTH(nt, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", r_, R * .7)), R * .16, R * .07)
            m = ring if m is None else MATH(nt, "MAXIMUM", m, ring)
        # erase the arcs that fall inside the other circle (one closed apple outline)
        for r_ in rs:
            m = MATH(nt, "MULTIPLY", m, SMOOTH(nt, r_, R * .5, R * .6))
        # stem: short vertical line above
        st = MATH(nt, "MULTIPLY", SMOOTH(nt, MATH(nt, "ABSOLUTE", dx), R * .09, R * .04), MATH(nt, "MULTIPLY", SMOOTH(nt, dz, R * .6, R * .7), SMOOTH(nt, dz, R * 1.15, R * 1.05)))
        m = MATH(nt, "MAXIMUM", m, st)
        # leaf: small ellipse to the right of the stem
        lx = MATH(nt, "SUBTRACT", dx, R * .32); lz = MATH(nt, "SUBTRACT", dz, R * .95)
        ex = MATH(nt, "ADD", MATH(nt, "MULTIPLY", lx, .8), MATH(nt, "MULTIPLY", lz, .6)); ey = MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", lz, .8), MATH(nt, "MULTIPLY", lx, .6))
        el = MATH(nt, "ADD", MATH(nt, "POWER", MATH(nt, "DIVIDE", ex, R * .3), 2.0), MATH(nt, "POWER", MATH(nt, "DIVIDE", ey, R * .14), 2.0))
        m = MATH(nt, "MAXIMUM", m, SMOOTH(nt, el, 1.2, .9))
        return m
    return d


def paint_percent(name, base="D74A3C", ink="F4EFE4", border=True, **fin):
    """Banner on flag(): base colour, a cream border and a big '%' pictogram (two discs and a diagonal bar) drawn in attribute space."""
    def r(c):
        nt = c.nt
        u, v, rnd = ATTR(nt)
        cloth = NOISE(nt, c.pos, 120.0, 2.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", cloth, .1), base, "000000")
        if border:
            bx = MATH(nt, "MINIMUM", u, MATH(nt, "SUBTRACT", 1.0, u))
            edge = SMOOTH(nt, bx, .12, .09)
            edge = MATH(nt, "MULTIPLY", edge, SMOOTH(nt, v, .05, .1))
            tb = SMOOTH(nt, v, .92, .95)
            col = MIX(nt, MATH(nt, "MAXIMUM", edge, tb), col, ink)
        # '%' : x spans -.3..+.3, y .25..1 (in units of the width); v = 1 top
        x = MATH(nt, "SUBTRACT", u, .5); y = MATH(nt, "SUBTRACT", v, .6)
        def disc(cx, cy, rr):
            d = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "POWER", MATH(nt, "SUBTRACT", x, cx), 2.0), MATH(nt, "POWER", MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", y, cy), .75), 2.0)))
            return MATH(nt, "MULTIPLY", SMOOTH(nt, d, rr + .015, rr - .015), SMOOTH(nt, d, rr * .45 - .015, rr * .45 + .015))
        m = MATH(nt, "MAXIMUM", disc(-.17, .17, .11), disc(.17, -.17, .11))
        # diagonal bar from bottom-left to top-right
        dist = MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", y, .75), MATH(nt, "MULTIPLY", x, 1.35)))
        bar = MATH(nt, "MULTIPLY", SMOOTH(nt, dist, .06, .035), MATH(nt, "MULTIPLY", SMOOTH(nt, y, -.34, -.28), SMOOTH(nt, y, .34, .28)))
        m = MATH(nt, "MAXIMUM", m, bar)
        col = MIX(nt, m, col, ink)
        return col
    return paint(name, r, k_ao=.5, k_light=.4, **fin)


def paint_wax(name="Wax", base="C43A2E", dark="8E2420", light="E8705F", **fin):
    def r(c):
        nt = c.nt
        mot = NOISE(nt, c.pos, 12.0, 2.0)
        col = RAMP(nt, mot, [(.3, dark), (.7, base)])
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .3, .95), .35), col, light)
        return col
    return paint(name, r, k_ao=.55, k_light=.4, edge=light, edge_k=.5, edge_r=.004, **fin)
