# vehicles.py - event vehicles v3 (Oct 2026): the v2 vehicles rebuilt in the style of the game's own traffic cars
# (MapModels CartoonCar / StylizedCar / ToyVan): rounded subdivided bodies with a crisp shoulder line, windows set
# INTO the body in a dark rubber seal, chunky tyres with tread + cream rims, round lamps, fat cream bumpers.
# Same contracts as events_v2/vehicles.py: builders model at the origin, ground z=0, drive along +X, camera side -Y,
# same prop names / sizes / signs; wheels, bus door leaves and the driver's pane stay separate islands for the rigs.
# Loaded by run_v3.py as module "vehicles3" (events_v2/vehicles.py keeps the name "vehicles" for works_power).
import bpy, bmesh, math, os, sys, importlib, importlib.util
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
V2DIR = os.path.join(ART, "events_v2")
for pth in (ART, V2DIR):
    if pth not in sys.path: sys.path.insert(0, pth)
import events_kit as E
import era_kit as k
if "vehicles" not in sys.modules or not getattr(sys.modules["vehicles"], "hatchback", None):
    _spec = importlib.util.spec_from_file_location("vehicles", os.path.join(V2DIR, "vehicles.py"))
    V2 = importlib.util.module_from_spec(_spec); sys.modules["vehicles"] = V2; _spec.loader.exec_module(V2)
else:
    V2 = sys.modules["vehicles"]
import works_power as WP
rad = math.radians
C = E.C
P, put, ROT = V2.P, V2.put, V2.ROT

XM = {}
def mats():
    m = V2.mats()
    if XM: return XM
    XM.update(m); XM.update(WP.mats())
    XM["tyre"] = k.mat("EV3_Tyre", (.11, .11, .12, 1), rough=.92, var=.05, scale=12, bump=.15)
    XM["tyreside"] = k.mat("EV3_TyreSide", (.17, .17, .18, 1), rough=.85, var=.05, scale=10)
    XM["rimC"] = k.mat("EV3_RimCream", (.93, .87, .70, 1), rough=.45, var=.05, scale=8)
    XM["seal"] = k.mat("EV3_Seal", (.07, .07, .08, 1), rough=.8, var=.03, scale=10)
    XM["interior"] = k.mat("EV3_Interior", (.20, .19, .18, 1), rough=.9, var=.08, scale=8)
    XM["line"] = k.mat("EV3_PanelLine", (.30, .28, .28, 1), rough=.7, var=.0, scale=8)
    XM["orangeL"] = k.mat("EV3_OrangeLamp", (.98, .55, .18, 1), rough=.4, var=.05, scale=6)
    for n in ("red", "blue", "yellow", "white", "teal", "green", "purple", "cream", "orange", "lime", "navy"):
        XM["p_" + n] = k.mat("EV3_Paint_" + n, C[n], rough=.45, var=.025, scale=4)   # smooth paint (less mottle than EV_*)
    XM["p_yellowS"] = k.mat("EV3_Paint_school", (.98, .72, .10, 1), rough=.45, var=.025, scale=4)
    return XM

def paint_m(name):
    return mats().get("p_" + name, mats()[name])

# ====================================================================== kit
def ring_of(pts):
    """Half profile (+Y side, bottom centre -> top centre) -> full ring (counter-clockwise seen from +X)."""
    return list(pts) + [(-y, z) for (y, z) in reversed(pts[1:-1])]

def loft(p, name, stations, m, subdiv=2, ring_crease=None, long_crease=None, face_mat=None, mats_list=(), dissolve=1.2):
    """Subdivided body: `stations` = [(x, half_profile)] (same point count), lofted with quads, n-gon caps.
    ring_crease(i, band) / long_crease(i, pt) give edge creases (0..1); face_mat(i, band) -> material index
    (0 = m, 1.. = mats_list). The subdivision is applied (baked) so booleans can cut the smooth body."""
    bm = bmesh.new()
    cl = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
    npts = len(stations[0][1])
    pi = lambda j: j if j < npts else 2 * npts - 2 - j
    rings = [[bm.verts.new((x, y, z)) for (y, z) in ring_of(pts)] for x, pts in stations]
    n = len(rings[0])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(n):
            f = bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
            band = min(pi(j), pi((j + 1) % n))
            if face_mat: f.material_index = face_mat(i, band)
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bm.edges.ensure_lookup_table()
    for i, r in enumerate(rings):
        for j in range(n):
            e = bm.edges.get((r[j], r[(j + 1) % n]))
            if e is not None and ring_crease:
                e[cl] = ring_crease(i, min(pi(j), pi((j + 1) % n)))
    for i in range(len(rings) - 1):
        for j in range(n):
            e = bm.edges.get((rings[i][j], rings[i + 1][j]))
            if e is not None and long_crease:
                e[cl] = long_crease(i, pi(j))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); p.c.objects.link(o)
    me.materials.append(m)
    for mm in mats_list: me.materials.append(mm)
    for f in me.polygons: f.use_smooth = True
    sd = o.modifiers.new("Subd", 'SUBSURF'); sd.levels = subdiv; sd.render_levels = subdiv; sd.use_creases = True
    bpy.context.view_layer.update()
    k.bake(o)
    if dissolve:
        # flat runs of the smooth surface (roof, flanks) are merged into n-gons: same look, far fewer tris
        md = o.modifiers.new("Dissolve", 'DECIMATE'); md.decimate_type = 'DISSOLVE'; md.angle_limit = rad(dissolve); md.delimit = {'MATERIAL'}
        k.bake(o)
        for f in o.data.polygons: f.use_smooth = True
    p.o.append(o)
    return o

def profile_at(stations, x):
    """Half profile linearly interpolated between stations at x."""
    xs = [s[0] for s in stations]
    if x >= xs[0]: return stations[0][1]
    if x <= xs[-1]: return stations[-1][1]
    for (xa, pa), (xb, pb) in zip(stations, stations[1:]):
        if xb <= x <= xa:
            t = (xa - x) / (xa - xb)
            return [(ya + (yb - ya) * t, za + (zb - za) * t) for (ya, za), (yb, zb) in zip(pa, pb)]
    return stations[-1][1]

def hit(body, origin, direction, dist=5.0):
    """Ray cast on the baked body (local = world here); returns (location, normal) or None."""
    bpy.context.view_layer.update()
    ok, loc, nrm, _ = body.ray_cast(Vector(origin), Vector(direction).normalized(), distance=dist)
    return (loc.copy(), nrm.copy()) if ok else None

def front_point(body, y, z, s=1, fallback_x=0.0):
    """Point on the nose (s=+1) or tail (s=-1) surface at (y, z)."""
    h = hit(body, (s * 6.0, y, z), (-s, 0, 0), dist=12.0)
    return h if h else (Vector((s * fallback_x, y, z)), Vector((s, 0, 0)))

def side_point(body, x, z, s, fallback_y):
    """Point on the body side at (x, z) seen from the side s (-1 / +1), with the surface normal."""
    h = hit(body, (x, s * 3.0, z), (0, -s, 0))
    return h if h else (Vector((x, s * fallback_y, z)), Vector((0, s, 0)))

def frame_matrix(center, normal, up):
    n = Vector(normal).normalized(); u = Vector(up); u = (u - n * u.dot(n)).normalized(); r = u.cross(n).normalized()
    M = Matrix.Identity(4)
    M.col[0][:3] = r; M.col[1][:3] = u; M.col[2][:3] = n; M.col[3][:3] = Vector(center)
    return M

def obox(p, name, size, M, m, bevel=.006, seg=2):
    """Box of `size` (x = right, y = up, z = normal) placed with the orthonormal frame M."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); p.c.objects.link(o); o.matrix_world = M
    k.finish(o, m, bevel, seg); p.o.append(o); return o

def rounded_plate(p, name, w, h, t, r, M, m=None, segs=4, bevel=0.0, taper=1.0):
    """Rounded-corner rectangle (w x h, corner radius r) extruded to thickness t, placed with frame M."""
    r = max(.001, min(r, w / 2 - .002, h / 2 - .002)); bm = bmesh.new(); pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(segs + 1):
            a = rad(a0 + 90 * i / segs); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    verts = [bm.verts.new((x * (1 - (1 - taper) * (y + h / 2) / h), y, -t / 2)) for x, y in pts]   # taper: narrower top
    f = bm.faces.new(verts)
    res = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0, t))
    if m is not None and f.is_valid:   # window plates: no hidden bottom face (it only wastes atlas space and can bleed into the bake)
        bmesh.ops.delete(bm, geom=[f], context='FACES_ONLY')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # triangulated caps: clean FLOAT booleans for the cutters, clean UV/bake/FBX for the seal and glass plates
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); p.c.objects.link(o); o.matrix_world = M
    if m is not None: k.finish(o, m, bevel, 1, smooth=False); p.o.append(o)
    return o

def cutter_box(p, size, M):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    me = bpy.data.meshes.new("cutter"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("cutter", me); p.c.objects.link(o); o.matrix_world = M
    return o

def pocket(p, body, center, normal, up, w, h, depth=.025, round_=0.0, taper=1.0):
    """Recess of w x h, `depth` deep, into `body` around `center` on the plane (normal, up). The cutters of one
    body are collected and applied in ONE exact boolean by flush_pockets() (many sequential cuts made the exact
    solver collapse some bodies; the float solver left torn pockets)."""
    big = .6
    M = frame_matrix(Vector(center) + Vector(normal).normalized() * (big / 2 - depth), normal, up)
    cutter = rounded_plate(p, "cutter", w, h, big, round_, M, segs=3, taper=taper) if round_ else cutter_box(p, (w, h, big), M)
    PENDING.setdefault(body.name, []).append(cutter)

PENDING = {}

def flush_pockets(p):
    """Applies the pending window pockets: all cutters of a body joined into one object, one EXACT difference."""
    for bname, cutters in list(PENDING.items()):
        body = bpy.data.objects.get(bname)
        if body is None or not cutters:
            continue
        bm = bmesh.new()
        for cobj in cutters:
            tmp = cobj.data.copy(); tmp.transform(cobj.matrix_world); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
            bpy.data.objects.remove(cobj, do_unlink=True)
        me = bpy.data.meshes.new("cutters"); bm.to_mesh(me); bm.free()
        joined = bpy.data.objects.new("cutters", me); p.c.objects.link(joined)
        md = body.modifiers.new("pockets", 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = joined; md.solver = 'EXACT'
        bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active = body
        bpy.ops.object.modifier_move_to_index(modifier=md.name, index=0)
        bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.data.objects.remove(joined, do_unlink=True)
    PENDING.clear()

def cut_fast(p, o, cutter):
    """Boolean difference with the FLOAT solver; the cutter is deleted."""
    md = o.modifiers.new("cut", 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'FLOAT'
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_move_to_index(modifier=md.name, index=0)
    bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return o

def window(p, body, center, normal, up, w, h, depth=.024, seal=.028, name="win", mg=None, round_=.035, glass_bevel=.018, taper=1.0):
    """Window set into the body: pocket, dark rubber seal plate, glass pane standing in the seal (~1 cm under the paint)."""
    m = mats(); n = Vector(normal).normalized(); c = Vector(center)
    rc = max(round_, .05)                      # corner radius of the opening (soft, like the cabin corners)
    pocket(p, body, c, n, up, w, h, depth, round_=rc, taper=taper)
    rounded_plate(p, name + "_seal", w - .036, h - .036, .012, rc - .018, frame_matrix(c - n * (depth - .006), n, up), m["seal"], segs=3, taper=taper)
    return rounded_plate(p, name, w - 2 * seal, h - 2 * seal, .014, max(.012, rc - seal), frame_matrix(c - n * (depth - .015), n, up), mg or m["glass"], segs=3, taper=taper)

def arc_tube(p, name, center, R, r, a0, a1, m, segs=12, verts=8, surf=None, inset=None, taper=False):
    """Tube bent along an arc in the XZ plane around `center`, from angle a0 to a1 (degrees, 0 = +X, 90 = +Z).
    With surf=(body, s) each ring sits on the body's side surface (arch lips that hug a curved flank)."""
    bm = bmesh.new(); rings = []; last_y = center[1]
    cx, cy, cz = center
    for i in range(segs + 1):
        a = rad(a0 + (a1 - a0) * i / segs); c = Vector((cx + math.cos(a) * R, cy, cz + math.sin(a) * R))
        if surf:
            body, s = surf; h = hit(body, (c.x, s * 3.0, c.z), (0, -s, 0))
            if h: c.y = h[0].y - s * (r * .4 if inset is None else inset); last_y = c.y
            elif rings: c.y = last_y
        t = Vector((-math.sin(a), 0, math.cos(a))); n1 = Vector((0, 1, 0)); n2 = t.cross(n1)
        ri = r * (.3 + .7 * math.sin(math.pi * i / segs)) if taper else r
        rings.append([bm.verts.new(c + (n1 * math.cos(j * math.tau / verts) + n2 * math.sin(j * math.tau / verts)) * ri) for j in range(verts)])
    for ra, rb in zip(rings, rings[1:]):
        for j in range(verts):
            bm.faces.new((ra[j], ra[(j + 1) % verts], rb[(j + 1) % verts], rb[j]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); p.c.objects.link(o); k.finish(o, m, 0); p.o.append(o)
    return o

def wheel3(p, loc, R=.31, w=.22, side=-1, rim="rimC", hub="orange", verts=20, tread=0, holes=4, lugs=0):
    """Fat soft road tyre (big rounded shoulders, a shallow groove ring, lighter sidewall), cream rim dish with holes and
    a coloured hub cap on both sides. `lugs` adds tractor lugs (backhoe only). One tyre island + islands inside its
    circle (the rig takes them as the wheel)."""
    m = mats(); x, y, z = loc; rot = (rad(90), 0, 0)
    p.cyl("tyre", R, w, loc, m["tyre"], rot=rot, verts=verts, bevel=min(R * .42, w * .46), seg=3)
    p.cyl("tyre_groove", R + .002, w * .18, loc, m["tyreside"], rot=rot, verts=verts)
    for i in range(lugs):
        a_ = i * math.tau / lugs
        p.box("lug", (R * .17, w * .9, .06), (x + math.cos(a_) * R, y, z + math.sin(a_) * R), m["tyre"], rot=(0, rad(90) - a_, 0), bevel=0)
    for s in (-1, 1):
        yy = y + s * (w / 2 + .002)
        if s == side: p.cyl("sidewall", R * .78, .010, (x, yy, z), m["tyreside"], rot=rot, verts=verts)
        p.cyl("rim", R * .60, .05, (x, yy + s * .012, z), m[rim], rot=rot, verts=14)
        for i in range(holes):
            a_ = i * math.tau / holes + math.pi / 4
            p.cyl("rimhole", R * .11, .016, (x + math.cos(a_) * R * .36, yy + s * .04, z + math.sin(a_) * R * .36), m["seal"], rot=rot, verts=5)
        p.cyl("hubcap", R * .20, .05, (x, yy + s * .04, z), m[hub], rot=rot, verts=9)

def arch_flare(p, body, ax, R, s, m, hw, rr=.05, extra=.13):
    """Rounded fender flare around the wheel arch: a fat body-coloured torus section half sunk into the flank, so the
    arch reads as part of the silhouette (no gap, no dark seam)."""
    return arc_tube(p, "arch_flare", (ax, s * hw, R + .02), R + extra, rr, 6, 174, m, segs=10, verts=6, surf=(body, s), inset=rr * .5, taper=True)

def round_lamp(p, loc, R, m_lens, face="+X", ring="cream", depth=.04, normal=None):
    """Round lamp with a cream ring, lens standing proud, axis along +-X (or along `normal`: the body surface)."""
    m = mats(); x, y, z = loc; d = 1 if face == "+X" else -1
    n = Vector(normal).normalized() if normal is not None else Vector((d, 0, 0))
    M = frame_matrix(loc, n, (0, 0, 1))
    r = p.cyl("lamp_ring", R, depth, (0, 0, 0), m[ring], verts=16, bevel=.012, seg=1); r.matrix_world = M
    l = p.cyl("lamp", R * .70, depth + .02, (0, 0, 0), m_lens, verts=14, bevel=.01, seg=1); l.matrix_world = M @ Matrix.Translation((0, 0, .012))

def body_lamp(p, body, y, z, R, m_lens, s=1, ring="cream", sink=.004):
    """Round lamp set on the nose (s=+1) / tail (s=-1) surface at (y, z), following the surface normal."""
    loc, n = front_point(body, y, z, s, 0.0)
    round_lamp(p, loc - n * sink, R, m_lens, "+X" if s > 0 else "-X", ring=ring, normal=n)

def body_box(p, body, name, size, y, z, m, s=1, sink=.01, bevel=.012):
    """Small box (indicator, lamp) set on the nose / tail surface at (y, z), aligned with the surface."""
    loc, n = front_point(body, y, z, s, 0.0)
    return obox(p, name, (size[1], size[2], size[0]), frame_matrix(loc - n * sink + n * size[0] / 2, n, (0, 0, 1)), m, bevel=bevel, seg=2)

def bumper(p, x, W, z, h=.22, d=.20, m=None, face="+X", inserts=True, slot=True):
    """Fat rounded bumper bar with orange indicator inserts and a dark slot."""
    mm = mats(); m = m or mm["cream"]; s = 1 if face == "+X" else -1
    p.box("bumper", (d, W, h), (x, 0, z), m, bevel=min(h, d) * .42, seg=3)
    if inserts:
        for sy in (-1, 1):
            p.box("bumper_ind", (.03, W * .16, h * .40), (x + s * (d / 2 - .006), sy * W * .36, z), mm["orangeL"], bevel=.012, seg=2)
    if slot:
        p.box("bumper_slot", (.03, W * .42, h * .28), (x + s * (d / 2 - .006), 0, z - h * .05), mm["seal"], bevel=.01, seg=2)

def mirror3(p, loc, s, m=None, arm=.08, size=(.07, .12, .09)):
    mm = mats(); x, y, z = loc; m = m or mm["orangeL"]
    p.cyl("mirror_stalk", .012, arm + .02, (x, y + s * arm / 2, z - .01), mm["seal"], rot=(rad(90), 0, 0), verts=6)
    p.box("mirror", size, (x, y + s * (arm + size[1] / 2 - .01), z), m, bevel=.028, seg=2)
    p.box("mirror_glass", (.012, size[1] - .03, size[2] - .03), (x + .036, y + s * (arm + size[1] / 2 - .01), z), mm["glassL"], bevel=0)

def handle3(p, body, x, z, s, m=None):
    loc, n = side_point(body, x, z, s, .85)
    obox(p, "handle", (.14, .03, .018), frame_matrix(loc + n * .009, n, (0, 0, 1)), m or mats()["chrome"], bevel=.005, seg=1)

def seam3(p, body, x, z0, z1, s, m=None, step=.12, w=.009):
    """Door seam following the curved side: short thin plates on the surface from z0 to z1 (subtle grey line)."""
    n = max(2, int((z1 - z0) / step)); mm = m or mats()["line"]
    for i in range(n):
        za, zb = z0 + (z1 - z0) * i / n, z0 + (z1 - z0) * (i + 1) / n
        a, na = side_point(body, x, za, s, .85); b, nb = side_point(body, x, zb, s, .85)
        c = (a + b) / 2; nn = (na + nb).normalized(); up = (b - a).normalized()
        obox(p, "seam", (w, (b - a).length + .01, .006), frame_matrix(c + nn * .001, nn, up), mm, bevel=0)

def side_plate(p, body, name, x, z, w, h, s, m, t=.012, proud=.004, bevel=.004, flat=False, avoid=(), res=.24):
    """Thin plate on the flank at (x, z). Small plates / `flat` boards are one bevelled box; long stripes are a grid
    shrink-wrapped onto the body (they follow its curvature), split around the wheel arches given in `avoid`."""
    if flat or w * h < .06:
        loc, n = side_point(body, x, z, s, .85)
        return obox(p, name, (w, h, t), frame_matrix(loc + n * (proud + t / 2 - .006), n, (0, 0, 1)), m, bevel=bevel, seg=1)
    pieces = [(x - w / 2, x + w / 2)]
    for ax, r in avoid:
        nxt = []
        for xa, xb in pieces:
            if xb <= ax - r or xa >= ax + r: nxt.append((xa, xb)); continue
            if xa < ax - r: nxt.append((xa, ax - r))
            if xb > ax + r: nxt.append((ax + r, xb))
        pieces = nxt
    out = None
    for xa, xb in pieces:
        if xb - xa < .12: continue
        out = conform_plate(p, body, name, xa, xb, z - h / 2, z + h / 2, s, m, t=t, offset=proud, res=res)
    return out

def conform_plate(p, body, name, xa, xb, za, zb, s, m, t=.012, offset=.004, res=.10):
    """Grid in the XZ plane shrink-wrapped onto the body's flank (offset outward) and solidified: a stripe that hugs the
    rounded body. Modifiers are evaluated by the exporter / renderer."""
    nx = max(1, int(math.ceil((xb - xa) / res))); nz = max(1, int(math.ceil((zb - za) / res)))
    loc, n = side_point(body, (xa + xb) / 2, (za + zb) / 2, s, .85)
    y0 = loc.y + s * .15
    bm = bmesh.new()
    vs = [[bm.verts.new((xa + (xb - xa) * i / nx, y0, za + (zb - za) * j / nz)) for j in range(nz + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(nz):
            f = bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
            if s < 0: f.normal_flip()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); p.c.objects.link(o); me.materials.append(m)
    sw = o.modifiers.new("Wrap", 'SHRINKWRAP'); sw.target = body; sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.offset = offset
    so = o.modifiers.new("Solid", 'SOLIDIFY'); so.thickness = t; so.offset = 1.0; so.use_even_offset = True
    p.o.append(o); return o

def side_text(p, body, s_, size, x, z, s, m, res=2, spacing=1.0, proud=.03):
    """Lettering on the flank: flat text shrink-wrapped onto the body (offset `proud`), so long words stay fully
    visible on the curved side (each letter is its own thin island for rig_kit.mirror_vehicle)."""
    loc, n = side_point(body, x, z, s, .85)
    o = p.txt(s_, size, (loc.x, loc.y + s * proud, loc.z), m, face="-Y" if s < 0 else "+Y", res=res, extrude=0.0, spacing=spacing)
    sw = o.modifiers.new("Wrap", 'SHRINKWRAP'); sw.target = body; sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.offset = proud
    return o

def front_text(p, body, s_, size, y, z, s, m, proud=.012, res=2):
    """Lettering on the nose (s=+1) / tail (s=-1), oriented with the surface."""
    loc, n = front_point(body, y, z, s, 0.0)
    o = p.txt(s_, size, (0, 0, 0), m, face="+X", res=res, extrude=0.0)
    o.matrix_world = frame_matrix(loc + n * proud, n, (0, 0, 1))
    return o

def bus_mirror(p, body, x, z, s, arm=.40, head=(.08, .22, .48)):
    """Coach mirror on an arm growing out of the A-pillar (attached to the body, not floating)."""
    m = mats(); loc, n = side_point(body, x, z, s, .9)
    p.box("mirror_arm", (.05, arm + .04, .05), (loc.x, loc.y + s * arm / 2, loc.z), m["ink"], bevel=.006)
    p.box("mirror_arm2", (.05, arm * .6, .05), (loc.x, loc.y + s * arm * .7, loc.z - .3), m["ink"], rot=(rad(-40 * s), 0, 0), bevel=.006)
    p.box("mirror_h", head, (loc.x + .02, loc.y + s * (arm + head[1] / 2 - .02), loc.z - .22), m["ink"], bevel=.03, seg=2)
    p.box("mirror_g", (.012, head[1] - .05, head[2] - .06), (loc.x + .02 + head[0] / 2 - .006, loc.y + s * (arm + head[1] / 2 - .02), loc.z - .22), m["glassL"], bevel=0)

def plate3(p, x, y, z, face="+X", s="ABC 1D23"):
    p.plate(x, y, z, face, s)

# ====================================================================== cars
def car_body(p, L, W, H, m_paint, kind="hatch", z0=.30, belt=.76, shoulder=.92, hood=1.00, roof_front=.30, roof_rear=-1.0,
             cowl=.70, tail_base=-1.60, boot=None, tumble=.14, roof_m=None, low_m=None, axles=(), flare=.04):
    """Rounded car body (lower body + greenhouse in one subdivided loft). Returns (body, stations, idx).
    kind 'hatch': hatch tail; 'sedan': boot (x where the boot lid starts) and a notch at tail_base.
    `axles`: x of the wheels -> the sides bulge a little there (fenders)."""
    m = mats(); hw = W / 2; fx, bx = L / 2, -L / 2
    yb, ys, yt = hw - .07, hw - .03, hw - .03 - tumble
    S = []; idx = {}
    def st(x, zb, ybb, ybelt, zbelt, ysh, zsh, yrf, zrf, zr, tag=None):
        if tag: idx[tag] = len(S)
        S.append((x, [(0, zb), (ybb, zb), (ybelt, zbelt), (ysh, zsh), (yrf, zrf), (0, zr)]))
    st(fx, z0 + .12, yb - .22, hw - .12, belt - .14, hw - .16, belt + .02, hw - .36, belt + .10, belt + .12)
    st(fx - .22, z0 + .02, yb - .02, hw - .02, belt - .03, hw - .05, belt + .10, hw - .25, hood - .05, hood - .03)
    st(fx - .55, z0, yb, hw, belt, hw - .04, hood - .08, hw - .22, hood - .02, hood)
    st(cowl, z0, yb, hw, belt, ys, shoulder, yt, hood + .02, hood + .04, "cowl")
    st(roof_front, z0, yb, hw, belt, ys, shoulder, yt, H - .04, H, "roof_f")
    st(roof_rear, z0, yb, hw, belt, ys, shoulder, yt, H - .04, H, "roof_r")
    if kind == "hatch":
        st(tail_base, z0, yb, hw, belt, ys, shoulder, yt - .02, hood + .04, hood + .06, "tail_base")
        st(bx + .22, z0 + .02, yb - .02, hw - .02, belt - .02, hw - .05, belt + .10, hw - .25, hood - .03, hood - .01)
        st(bx, z0 + .12, yb - .22, hw - .12, belt - .14, hw - .16, belt + .02, hw - .36, belt + .12, belt + .14)
    else:
        st(tail_base, z0, yb, hw, belt, ys, shoulder, yt - .02, hood + .02, hood + .04, "tail_base")
        st(boot, z0, yb, hw, belt, hw - .04, hood - .08, hw - .22, hood - .02, hood, "boot")
        st(bx + .22, z0 + .02, yb - .02, hw - .02, belt - .04, hw - .05, belt + .08, hw - .25, belt + .16, belt + .18)
        st(bx, z0 + .12, yb - .22, hw - .12, belt - .16, hw - .16, belt - .06, hw - .36, belt + .02, belt + .04)
    # fender flares: extra stations around each axle, interpolated from the neighbours, pushed out at the sill/belt
    base = list(S); extra = []
    for ax in axles:
        for dx, f in ((.45, 0.0), (0.0, flare), (-.45, 0.0)):
            x = ax + dx
            if any(abs(x - sx) < .08 for sx, _ in base + extra): continue
            pts = [list(pt) for pt in profile_at(base, x)]
            pts[1][0] += f; pts[2][0] += f; pts[3][0] += f * .3
            extra.append((x, [tuple(pt) for pt in pts]))
    S += extra
    order = sorted(range(len(S)), key=lambda i: -S[i][0])
    remap = {old: new for new, old in enumerate(order)}
    S = [S[i] for i in order]; idx = {k_: remap[i] for k_, i in idx.items()}
    ic, irf, irr, itb = idx["cowl"], idx["roof_f"], idx["roof_r"], idx["tail_base"]
    def ring_crease(i, band):
        if i == ic and band == 4: return .5          # windscreen base
        if i == irf and band >= 3: return .35        # roof front edge
        if i == irr and band >= 3: return .35
        if i == itb and band == 4: return .55        # rear glass base
        return 0.0
    def long_crease(i, pt):
        if pt == 3 and ic <= i < itb: return .5      # shoulder line (soft)
        if pt == 3 and i == ic - 1: return .2
        if pt == 1: return .2                        # rocker
        if pt == 4 and ic <= i < itb: return .35
        return 0.0
    roof_m = roof_m or m["cream"]
    def face_mat(i, band):
        if band == 4 and irf <= i < irr: return 1
        if band == 0: return 2
        if low_m is not None and band <= 1: return 3
        return 0
    body = loft(p, "body", S, m_paint, subdiv=2, ring_crease=ring_crease, long_crease=long_crease, face_mat=face_mat,
                mats_list=(roof_m, m["seal"], low_m or m["seal"]))
    return body, S, idx

def car_windows(p, body, S, idx, side_wins, mg=None):
    """Windscreen + rear glass on the loft planes, side windows (x0, x1) on the tumblehome plane."""
    def pt(i, j): x, pts = S[i]; return Vector((x, pts[j][0], pts[j][1]))
    # windscreen plane: through the cowl top (pt 5) and the roof front top (pt 5)
    a, b = pt(idx["cowl"], 5), pt(idx["roof_f"], 5); d = b - a; n = Vector((d.z, 0, -d.x)).normalized()
    c = (a + b) / 2; h0 = hit(body, c + n * 1.0, -n); c = h0[0] if h0 else c
    wdt = 2 * pt(idx["cowl"], 4).y - .30
    window(p, body, c - d.normalized() * .03, n, d.normalized(), wdt, d.length - .22, name="windscreen", mg=mg, round_=.07, depth=.05, taper=.88)
    a, b = pt(idx["tail_base"], 5), pt(idx["roof_r"], 5); d = b - a; n = Vector((-d.z, 0, d.x)).normalized()
    c = (a + b) / 2; h0 = hit(body, c + n * 1.0, -n); c = h0[0] if h0 else c
    window(p, body, c - d.normalized() * .07, n, d.normalized(), 2 * pt(idx["tail_base"], 4).y - .34, d.length - .30, name="rear_glass", mg=mg, round_=.07, depth=.05, taper=.88)
    # side windows on the shoulder->roof-edge plane
    p3, p4 = pt(idx["roof_f"], 3), pt(idx["roof_f"], 4)
    up = (p4 - p3).normalized(); n = Vector((0, up.z, -up.y)).normalized()   # outward (+Y side)
    zc = (p3.z + p4.z) / 2 - .02; hgt = (p4 - p3).length - .16
    panes = []
    for s in (-1, 1):
        for name, (x0, x1) in side_wins.items():
            xc = (x0 + x1) / 2
            c0 = Vector((xc, s * (p3.y + p4.y) / 2, zc)); nn = Vector((0, s * n.y, n.z))
            h0 = hit(body, c0 + nn * 1.0, -nn)
            if h0: c0 = h0[0]
            panes.append(window(p, body, c0, nn, (0, 0, 1), x0 - x1, hgt, name=name + ("_L" if s > 0 else "_R"), mg=mg))
    return panes

def hatchback(c, paint="red"):
    """Compact hatchback 3.95 x 1.80 x 1.50 m, Mini-like: rounded body, cream roof, round lamps, cream bumpers."""
    p = P(c); m = mats(); L, W, H = 3.95, 1.80, 1.68; hw = W / 2; fx, bx = L / 2, -L / 2; R = .35
    mp = paint_m(paint); BODY_M = mp
    axles = (fx - .66, bx + .66)
    body, S, idx = car_body(p, L, W, H, mp, kind="hatch", z0=.34, belt=.82, shoulder=.96, hood=1.04, cowl=.62, roof_front=.20, roof_rear=-1.02, tail_base=-1.62, axles=axles)
    for s in (-1, 1):
        for ax in axles:
            p.arch(body, ax, s * hw, R + .085, R + .02, w=.46)
    p.o.append(body) if body not in p.o else None
    car_windows(p, body, S, idx, {"win_front": (.12, -.44), "win_rear": (-.54, -1.02)})
    for s in (-1, 1):
        for ax in axles:
            p.cyl("archliner", R + .07, .12, (ax, s * (hw - .46), R + .02), m["seal"], rot=(rad(90), 0, 0), verts=16)
            arch_flare(p, body, ax, R, s, BODY_M, hw)
            wheel3(p, (ax, s * (hw - .17), R + .02), R=R, w=.22, side=s, hub="orangeL" if paint != "orange" else "teal")
        seam3(p, body, -.33, .36, .90, s); seam3(p, body, -1.04, .36, .90, s); seam3(p, body, .50, .36, .90, s)
        handle3(p, body, -.50, .86, s); handle3(p, body, -1.18, .86, s)
        loc, n = side_point(body, .40, 1.02, s, hw); mirror3(p, (loc.x, loc.y - s * .01, loc.z), s, size=(.09, .15, .11))
        body_lamp(p, body, s * .52, .82, .155, m["lamp"], 1)
        body_box(p, body, "indicator_f", (.04, .12, .06), s * .68, .58, m["orangeL"], 1)
        body_box(p, body, "taillamp_ring", (.03, .14, .26), s * (hw - .24), .86, m["cream"], -1)
        body_box(p, body, "taillamp", (.05, .10, .22), s * (hw - .24), .86, m["tail"], -1)
        p.box("wiper", (.02, .42, .02), (.60, s * .28, 1.03), m["seal"], rot=(0, rad(-50), rad(-20 * s)), bevel=0)
    # grille: cream oval with dark slots and a badge
    gx = front_point(body, 0, .74, 1, fx - .05)[0].x
    p.box("grille_ring", (.05, .74, .18), (gx - .005, 0, .74), m["cream"], bevel=.07, seg=3)
    p.box("grille_in", (.03, .62, .10), (gx + .015, 0, .74), m["seal"], bevel=.04, seg=2)
    for i in range(2): p.box("grille_bar", (.02, .56, .018), (gx + .03, 0, .71 + i * .06), m["cream"], bevel=0)
    p.cyl("badge", .045, .03, (gx + .035, 0, .74), m["orangeL"], rot=(0, rad(90), 0), verts=12, bevel=.008, seg=2)
    bumper(p, fx - .04, W - .06, .43, h=.22, d=.22, face="+X", slot=False)
    bumper(p, bx + .04, W - .06, .43, h=.22, d=.22, face="-X", inserts=False, slot=False)
    plate3(p, fx + .075, 0, .42, "+X", "CAR 1A23"); plate3(p, bx - .075, 0, .42, "-X", "CAR 1A23")
    p.box("hatch_line", (.02, W - .9, .012), (bx + .30, 0, .98), m["seal"], bevel=0)
    p.cyl("antenna", .008, .22, (-.9, .55, H + .09), m["seal"], verts=6)
    p.cyl("antenna_base", .025, .03, (-.9, .55, H - .01), m["orangeL"], verts=8)
    p.box("exhaust", (.18, .05, .05), (bx + .05, -.52, .24), m["chrome"], bevel=.012)
    flush_pockets(p)
    return p.o


# ====================================================================== generic windows / loft helpers
def plane_window(p, body, S, i0, j0, i1, j1, width, name, mg=None, inset=.06, round_=.04, flip=False, shift=0.0):
    """Window on the quad strip between station i0 (point j0) and i1 (point j1): plane through both centre-line points."""
    def pt(i, j): x, pts = S[i]; return Vector((x, pts[j][0], pts[j][1]))
    a, b = pt(i0, j0), pt(i1, j1); d = b - a
    n = Vector((d.z, 0, -d.x)).normalized()
    if flip: n = -n
    c = (a + b) / 2 + d.normalized() * shift; h0 = hit(body, c + n * 1.5, -n)
    if h0: c = h0[0]
    return window(p, body, c, n, d.normalized(), width, d.length - inset, name=name, mg=mg, round_=round_)

def side_windows(p, body, S, i_ref, wins, mg=None, inset=.08, seal=.028, zc_off=.02, name="win"):
    """Side windows on the shoulder->roof-edge plane of station i_ref: wins = {name: (x_front, x_back)}."""
    def pt(i, j): x, pts = S[i]; return Vector((x, pts[j][0], pts[j][1]))
    p3, p4 = pt(i_ref, 3), pt(i_ref, 4)
    up = (p4 - p3).normalized(); n = Vector((0, up.z, -up.y)).normalized()
    zc = (p3.z + p4.z) / 2 + zc_off; hgt = (p4 - p3).length - inset
    out = []
    for s in (-1, 1):
        for nm, (x0, x1) in wins.items():
            c0 = Vector(((x0 + x1) / 2, s * (p3.y + p4.y) / 2, zc)); nn = Vector((0, s * n.y, n.z))
            h0 = hit(body, c0 + nn * 1.5, -nn)
            if h0: c0 = h0[0]
            out.append(window(p, body, c0, nn, (0, 0, 1), x0 - x1, hgt, name=nm + ("_L" if s > 0 else "_R"), mg=mg, seal=seal))
    return out

def flat_side_window(p, body, x, z, w, h, s, name="win", mg=None, seal=.03, depth=.024):
    """Window on a (nearly) vertical side at (x, z)."""
    loc, n = side_point(body, x, z, s, .9)
    return window(p, body, loc, n, (0, 0, 1), w, h, depth=depth, seal=seal, name=name + ("_L" if s > 0 else "_R"), mg=mg)

def box_body(p, name, L, W, H, m, x0, z0, r=.12, subdiv=2, face_mat=None, mats_list=()):
    """Rounded box (cargo bodies, lockers): loft with chamfered corners + one subdivision."""
    hw = W / 2; fx, bx = x0 + L / 2, x0 - L / 2
    prof = [(0, z0), (hw - r, z0), (hw, z0 + r), (hw, z0 + H - r), (hw - r, z0 + H), (0, z0 + H)]
    S = [(fx, [(y * (1 - r / hw * .6), z) for y, z in prof]), (fx - r, prof), (bx + r, prof), (bx, [(y * (1 - r / hw * .6), z) for y, z in prof])]
    def rc(i, band): return .5 if i in (0, 3) else 0.0
    def lc(i, pt): return .4 if pt in (1, 2, 3, 4) else 0.0
    return loft(p, name, S, m, subdiv=subdiv, ring_crease=rc, long_crease=lc, face_mat=face_mat, mats_list=mats_list)

# ====================================================================== 4. VIGILANCIA SANITARIA (sedan)
def sedan_vigilancia(c):
    """White compact sedan 4.45 x 1.78 x 1.52 m, green stripe, VIGILANCIA SANITARIA, roof sign, door emblem."""
    p = P(c); m = mats(); L, W, H = 4.45, 1.78, 1.52; hw = W / 2; fx, bx = L / 2, -L / 2; R = .33; Wt = paint_m("white"); BODY_M = Wt
    axles = (fx - .78, bx + .80)
    body, S, idx = car_body(p, L, W, H, Wt, kind="sedan", z0=.32, belt=.76, shoulder=.92, hood=.98, cowl=.78, roof_front=.36,
                            roof_rear=-.72, tail_base=-1.22, boot=-1.55, axles=axles, tumble=.15)
    for s in (-1, 1):
        for ax in axles:
            p.arch(body, ax, s * hw, R + .085, R + .02, w=.46)
    car_windows(p, body, S, idx, {"win_front": (.28, -.28), "win_rear": (-.38, -.86)})
    for s in (-1, 1):
        for ax in axles:
            p.cyl("archliner", R + .07, .12, (ax, s * (hw - .46), R + .02), m["seal"], rot=(rad(90), 0, 0), verts=16)
            arch_flare(p, body, ax, R, s, BODY_M, hw)
            wheel3(p, (ax, s * (hw - .17), R + .02), R=R, w=.22, side=s, hub="green")
        seam3(p, body, -.20, .36, .90, s); seam3(p, body, -.86, .36, .90, s); seam3(p, body, .62, .36, .90, s)
        handle3(p, body, -.36, .86, s); handle3(p, body, -1.00, .86, s)
        loc, n = side_point(body, .56, 1.02, s, hw); mirror3(p, (loc.x, loc.y - s * .01, loc.z), s, m=Wt, size=(.09, .15, .11))
        body_lamp(p, body, s * .52, .80, .15, m["lamp"], 1)
        body_box(p, body, "indicator_f", (.04, .12, .06), s * .70, .58, m["orangeL"], 1)
        body_box(p, body, "taillamp_ring", (.03, .30, .18), s * (hw - .28), .84, m["cream"], -1)
        body_box(p, body, "taillamp", (.05, .26, .14), s * (hw - .28), .84, m["tail"], -1)
        p.box("wiper", (.02, .42, .02), (.76, s * .28, 1.01), m["seal"], rot=(0, rad(-50), rad(-20 * s)), bevel=0)
        # livery: green stripe along the flank, lettering, emblem
        side_plate(p, body, "stripe", .0, .62, 2.05, .15, s, m["green"])
        side_plate(p, body, "stripe_thin", .0, .73, 2.05, .035, s, m["greenD"])
        side_text(p, body, "VIGILÂNCIA SANITÁRIA", .10, .0, .84, s, m["greenD"])
        loc, n = side_point(body, -.95, .95, s, hw)
        p.cyl("emblem", .13, .02, (loc.x, loc.y + s * .008, loc.z), m["green"], rot=(rad(90), 0, 0), verts=18)
        p.cyl("emblem_in", .095, .02, (loc.x, loc.y + s * .016, loc.z), Wt, rot=(rad(90), 0, 0), verts=18)
        p.box("emblem_cross_v", (.03, .02, .11), (loc.x, loc.y + s * .024, loc.z), m["green"], bevel=0)
        p.box("emblem_cross_h", (.11, .02, .03), (loc.x, loc.y + s * .024, loc.z), m["green"], bevel=0)
    gx = front_point(body, 0, .74, 1, fx - .05)[0].x
    p.box("grille_ring", (.05, .80, .18), (gx - .005, 0, .74), m["cream"], bevel=.07, seg=3)
    p.box("grille_in", (.03, .68, .10), (gx + .015, 0, .74), m["seal"], bevel=.04, seg=2)
    for i in range(2): p.box("grille_bar", (.02, .62, .018), (gx + .03, 0, .71 + i * .06), m["cream"], bevel=0)
    bumper(p, fx - .04, W - .06, .43, h=.22, d=.22, face="+X", slot=False)
    bumper(p, bx + .04, W - .06, .43, h=.22, d=.22, face="-X", inserts=False, slot=False)
    plate3(p, fx + .075, 0, .42, "+X", "VIG 1S23"); plate3(p, bx - .075, 0, .42, "-X", "VIG 1S23")
    p.box("boot_line", (.02, W - .9, .012), (bx + .36, 0, .985), m["seal"], bevel=0)
    # roof sign + beacon + antenna
    z1 = H
    p.box("roof_sign_base", (.9, .32, .03), (-.25, 0, z1 - .005), m["seal"], bevel=.006)
    p.box("roof_sign", (.86, .28, .24), (-.25, 0, z1 + .12), m["green"], bevel=.035, seg=2)
    p.txt("VIGILÂNCIA", .08, (-.25, -.152, z1 + .12), Wt, face="-Y"); p.txt("VIGILÂNCIA", .08, (-.25, .152, z1 + .12), Wt, face="+Y")
    p.cyl("roof_beacon_base", .08, .025, (-.25, 0, z1 + .25), m["seal"], verts=12)
    p.cyl("roof_beacon", .065, .09, (-.25, 0, z1 + .30), m["amber"], verts=12, bevel=.015, seg=2)
    p.cyl("antenna", .008, .28, (-1.0, .45, z1 + .08), m["seal"], verts=6)
    p.box("exhaust", (.18, .05, .05), (bx + .05, -.52, .24), m["chrome"], bevel=.012)
    flush_pockets(p)
    return p.o

# ====================================================================== 5. CARRO DE SOM (Kombi)
def sound_van(c):
    """Retro one-box van 4.3 x 1.8 x 1.95 m (Kombi-like): purple below the beltline, cream above, split windscreen,
    big round lamps, 4 horn speakers on a roof rack, banners on both sides."""
    p = P(c); m = mats(); L, W, H = 4.3, 1.8, 1.95; hw = W / 2; fx, bx = L / 2, -L / 2; R = .32
    Pu, Cr = paint_m("purple"), paint_m("cream"); z0, belt, sh = .34, 1.02, 1.28; BODY_M = Pu
    yb, ys, yt = hw - .06, hw - .03, hw - .12
    S = []; idx = {}
    def st(x, pts, tag=None):
        if tag: idx[tag] = len(S)
        S.append((x, pts))
    st(fx, [(0, z0 + .10), (yb - .22, z0 + .10), (hw - .12, belt - .12), (hw - .14, belt + .02), (hw - .34, belt + .12), (0, belt + .15)])
    st(fx - .10, [(0, z0 + .02), (yb - .03, z0 + .02), (hw - .02, belt - .02), (hw - .04, belt + .12), (hw - .20, belt + .26), (0, belt + .30)], "cowl")
    st(fx - .36, [(0, z0), (yb, z0), (hw, belt), (ys, sh), (yt, H - .06), (0, H)], "roof_f")
    st(bx + .30, [(0, z0), (yb, z0), (hw, belt), (ys, sh), (yt, H - .06), (0, H)], "roof_r")
    st(bx + .08, [(0, z0 + .02), (yb - .03, z0 + .02), (hw - .02, belt - .02), (hw - .05, belt + .14), (hw - .22, belt + .30), (0, belt + .34)], "tail_base")
    st(bx, [(0, z0 + .10), (yb - .22, z0 + .10), (hw - .12, belt - .12), (hw - .14, belt + .02), (hw - .34, belt + .14), (0, belt + .17)])
    axles = (fx - .80, bx + .85)
    base = list(S); extra = []
    for ax in axles:
        for dx, f in ((.42, 0.0), (0.0, .035), (-.42, 0.0)):
            x = ax + dx
            if any(abs(x - sx) < .08 for sx, _ in base + extra): continue
            pts = [list(pt) for pt in profile_at(base, x)]; pts[1][0] += f; pts[2][0] += f
            extra.append((x, [tuple(pt) for pt in pts]))
    S += extra
    order = sorted(range(len(S)), key=lambda i: -S[i][0]); remap = {o: n for n, o in enumerate(order)}
    S = [S[i] for i in order]; idx = {k_: remap[i] for k_, i in idx.items()}
    ic, irf, irr, itb = idx["cowl"], idx["roof_f"], idx["roof_r"], idx["tail_base"]
    def rc(i, band):
        if i in (ic, itb) and band == 4: return .6
        if i in (irf, irr) and band >= 3: return .35
        return 0.0
    def lc(i, pt):
        if pt == 2: return .7      # beltline (colour split)
        if pt == 3 and ic <= i < itb: return .4
        if pt == 4 and ic <= i < itb: return .3
        if pt == 1: return .2
        return 0.0
    def fm(i, band): return 1 if band <= 1 else (2 if band == 0 else 0)
    body = loft(p, "body", S, Cr, subdiv=2, ring_crease=rc, long_crease=lc, face_mat=lambda i, b: 2 if b == 0 else (1 if b == 1 else 0), mats_list=(Pu, m["seal"]))
    for s in (-1, 1):
        for ax in axles:
            p.arch(body, ax, s * hw, R + .08, R + .02, w=.46)
    # windscreen: split in two, on the cowl -> roof front strip
    def pt(i, j): x, pts = S[i]; return Vector((x, pts[j][0], pts[j][1]))
    a, b = pt(ic, 5), pt(irf, 5); d = b - a; n = Vector((d.z, 0, -d.x)).normalized(); cc = (a + b) / 2
    for s in (-1, 1):
        c0 = cc + Vector((0, s * .36, 0)); h0 = hit(body, c0 + n * 1.5, -n)
        if h0: c0 = h0[0]
        window(p, body, c0, n, d.normalized(), .64, d.length - .10, name="ws_half", round_=.03)
    plane_window(p, body, S, itb, 5, irr, 5, 1.10, "rear_glass", flip=True, inset=.10)
    side_windows(p, body, S, irf, {"win_door": (fx - .50, fx - 1.12), "win_mid": (fx - 1.24, fx - 2.16), "win_rear": (bx + 1.30, bx + .40)}, inset=.10)
    for s in (-1, 1):
        for ax in axles:
            p.cyl("archliner", R + .07, .12, (ax, s * (hw - .46), R + .02), m["seal"], rot=(rad(90), 0, 0), verts=16)
            arch_flare(p, body, ax, R, s, BODY_M, hw)
            wheel3(p, (ax, s * (hw - .17), R + .02), R=R, w=.22, side=s, hub="purple")
        body_lamp(p, body, s * .55, 1.14, .15, m["lamp"], 1, ring="chrome")
        body_box(p, body, "indicator", (.04, .14, .08), s * .58, .80, m["orangeL"], 1)
        loc, n = side_point(body, fx - .40, 1.40, s, hw); mirror3(p, (loc.x, loc.y - s * .01, loc.z), s, m=m["chrome"], arm=.16, size=(.07, .14, .11))
        seam3(p, body, fx - 1.18, .40, 1.22, s); seam3(p, body, bx + 1.40, .40, 1.22, s)
        handle3(p, body, fx - .98, 1.08, s); handle3(p, body, fx - 1.40, 1.08, s)
        p.box("wiper", (.02, .36, .02), (fx - .16, s * .40, 1.36), m["seal"], rot=(0, rad(-70), rad(-25 * s)), bevel=0)
        body_box(p, body, "tail_bezel", (.03, .16, .26), s * .58, .92, m["chrome"], -1)
        body_box(p, body, "taillamp", (.045, .12, .22), s * .58, .92, m["tail"], -1)
        # banners
        side_plate(p, body, "banner", -.10, .70, 2.3, .42, s, m["yellow"], t=.025, proud=.012, bevel=.006, flat=True)
        side_plate(p, body, "banner_border", -.10, .70, 2.36, .48, s, m["red"], t=.016, proud=.004, bevel=.006, flat=True)
        side_text(p, body, "SUPER LEVA MAIS", .17, -.10, .76, s, Pu, res=1, proud=.045)
        side_text(p, body, "TUDO EM OFERTA!", .12, -.10, .56, s, m["red"], res=1, proud=.045)
    gx = front_point(body, 0, 1.20, 1, fx - .05)[0].x
    p.cyl("emblem", .11, .03, (gx + .01, 0, 1.22), m["chrome"], rot=(0, rad(90), 0), verts=16)
    p.box("belt_trim", (.03, W - .5, .035), (gx + .005, 0, belt), m["chrome"], bevel=.01, seg=2)
    bumper(p, fx - .02, W - .02, .50, h=.16, d=.16, m=m["chrome"], face="+X", inserts=False, slot=False)
    bumper(p, bx + .02, W - .02, .50, h=.16, d=.16, m=m["chrome"], face="-X", inserts=False, slot=False)
    plate3(p, fx + .07, 0, .66, "+X", "SOM 4D44"); plate3(p, bx - .07, 0, .66, "-X", "SOM 4D44")
    # rear engine lid louvres
    tx = front_point(body, 0, .80, -1, bx + .05)[0].x
    for i in range(4): p.box("louvre", (.03, 1.0, .03), (tx + .004, 0, .66 + i * .10), m["purpleD"], bevel=0)
    # roof rack with 4 horn speakers
    for s in (-1, 1):
        p.box("rack_rail", (2.2, .05, .05), (0, s * .62, H + .14), m["steel"], bevel=.006)
        for xx in (-1.0, 1.0): p.box("rack_leg", (.05, .05, .16), (xx, s * .62, H + .06), m["steel"], bevel=0)
    for xx in (-.9, .9): p.box("rack_x", (.05, 1.3, .05), (xx, 0, H + .14), m["steel"], bevel=.006)
    p.box("amp_box", (.6, .5, .3), (0, 0, H + .32), m["dark"], bevel=.03)
    for (hx, hy, ry, rz) in ((-.75, -.3, 90, 0), (.75, -.3, -90, 0), (-.35, .35, 90, -90), (.35, .35, -90, -90)):
        R_ = Matrix.Rotation(rad(rz), 4, 'Z') @ Matrix.Rotation(rad(ry), 4, 'Y')
        ax_ = (R_ @ Vector((0, 0, 1))).normalized(); base_ = Vector((hx, hy, H + .42))
        h = p.cyl("horn", .07, .45, base_ + ax_ * .12, m["white"], r2=.26, verts=14); h.matrix_world = Matrix.Translation(base_ + ax_ * .12) @ R_
        d_ = p.cyl("horn_driver", .10, .16, base_ - ax_ * .2, m["dark"], verts=10); d_.matrix_world = Matrix.Translation(base_ - ax_ * .2) @ R_
        p.box("horn_bracket", (.07, .07, .24), (hx, hy, H + .28), m["steel"], bevel=0)
    flush_pockets(p)
    return p.o

# ====================================================================== 6. MAQUININHA (telecom van)
def telecom_van(c):
    """White panel van 5.2 x 2.0 x 2.3 m: short rounded nose, tall body, orange stripe, roof rack with a ladder, beacon."""
    p = P(c); m = mats(); L, W, H = 5.2, 2.0, 2.3; hw = W / 2; fx, bx = L / 2, -L / 2; R = .34
    Wt = paint_m("white"); z0, belt, sh, hood = .40, .92, 1.16, 1.14; BODY_M = Wt
    yb, ys, yt = hw - .07, hw - .03, hw - .16
    S = []; idx = {}
    def st(x, pts, tag=None):
        if tag: idx[tag] = len(S)
        S.append((x, pts))
    st(fx, [(0, z0 + .12), (yb - .24, z0 + .12), (hw - .14, belt - .18), (hw - .18, belt - .02), (hw - .40, belt + .06), (0, belt + .08)])
    st(fx - .22, [(0, z0 + .02), (yb - .02, z0 + .02), (hw - .02, belt - .04), (hw - .05, belt + .10), (hw - .26, hood - .06), (0, hood - .04)])
    st(fx - .62, [(0, z0), (yb, z0), (hw, belt), (hw - .04, hood - .06), (hw - .22, hood - .01), (0, hood)])
    st(fx - 1.10, [(0, z0), (yb, z0), (hw, belt), (ys, sh), (yt, hood + .03), (0, hood + .05)], "cowl")
    st(fx - 1.62, [(0, z0), (yb, z0), (hw, belt), (ys, sh), (yt, H - .05), (0, H)], "roof_f")
    st(bx + .28, [(0, z0), (yb, z0), (hw, belt), (ys, sh), (yt, H - .05), (0, H)], "roof_r")
    st(bx + .08, [(0, z0 + .02), (yb - .02, z0 + .02), (hw - .02, belt), (ys - .03, sh), (yt - .04, H - .12), (0, H - .08)], "tail_base")
    st(bx, [(0, z0 + .10), (yb - .18, z0 + .10), (hw - .12, belt - .06), (ys - .12, sh - .02), (yt - .14, H - .22), (0, H - .18)])
    axles = (fx - 1.0, bx + 1.0)
    base = list(S); extra = []
    for ax in axles:
        for dx, f in ((.45, 0.0), (0.0, .035), (-.45, 0.0)):
            x = ax + dx
            if any(abs(x - sx) < .08 for sx, _ in base + extra): continue
            pts = [list(pt) for pt in profile_at(base, x)]; pts[1][0] += f; pts[2][0] += f
            extra.append((x, [tuple(pt) for pt in pts]))
    S += extra
    order = sorted(range(len(S)), key=lambda i: -S[i][0]); remap = {o: n for n, o in enumerate(order)}
    S = [S[i] for i in order]; idx = {k_: remap[i] for k_, i in idx.items()}
    ic, irf, irr, itb = idx["cowl"], idx["roof_f"], idx["roof_r"], idx["tail_base"]
    def rc(i, band):
        if i == ic and band == 4: return .6
        if i == irf and band >= 3: return .35
        if i in (irr, itb) and band >= 3: return .5
        return 0.0
    def lc(i, pt):
        if pt == 3 and ic <= i <= itb: return .5
        if pt == 4 and irf <= i <= itb: return .4
        if pt == 1: return .2
        return 0.0
    body = loft(p, "body", S, Wt, subdiv=2, ring_crease=rc, long_crease=lc, face_mat=lambda i, b: 1 if b == 0 else 0, mats_list=(m["seal"],))
    for s in (-1, 1):
        for ax in axles:
            p.arch(body, ax, s * hw, R + .09, R + .02, w=.46)
    plane_window(p, body, S, ic, 5, irf, 5, 2 * yt - .20, "windscreen", inset=.22)
    for s in (-1, 1): flat_side_window(p, body, fx - 2.11, 1.80, .86, .62, s, name="win_door")
    for s in (-1, 1):
        for ax in axles:
            p.cyl("archliner", R + .07, .12, (ax, s * (hw - .46), R + .02), m["seal"], rot=(rad(90), 0, 0), verts=16)
            arch_flare(p, body, ax, R, s, BODY_M, hw)
            wheel3(p, (ax, s * (hw - .18), R + .02), R=R, w=.24, side=s, hub="orangeL")
        body_lamp(p, body, s * .60, .82, .14, m["lamp"], 1)
        body_box(p, body, "indicator", (.04, .14, .07), s * .62, .58, m["orangeL"], 1)
        loc, n = side_point(body, fx - 1.62, 1.42, s, hw); mirror3(p, (loc.x, loc.y - s * .01, loc.z), s, m=m["dark"], arm=.14, size=(.08, .16, .22))
        seam3(p, body, fx - 1.60, .46, 1.12, s); seam3(p, body, fx - 2.62, .46, 2.05, s)
        handle3(p, body, fx - 2.40, 1.06, s)
        if s < 0:
            seam3(p, body, bx + 1.55, .46, 2.05, s); handle3(p, body, bx + 1.72, 1.06, s)
            side_plate(p, body, "slide_rail", bx + 1.25, 1.98, 1.5, .03, s, m["seal"])
        side_plate(p, body, "stripe", -.55, 1.0, L - 1.7, .20, s, m["orange"], avoid=[(ax, R + .30) for ax in axles])
        side_plate(p, body, "stripe2", -.55, .86, L - 1.7, .045, s, m["navy"], avoid=[(ax, R + .30) for ax in axles])
        side_text(p, body, "TELECOM - ASSISTÊNCIA TÉCNICA", .10, -.9, 1.30, s, m["navy"])
        p.box("wiper", (.02, .5, .02), (fx - 1.12, s * .32, 1.22), m["seal"], rot=(0, rad(-42), rad(-25 * s)), bevel=0)
        tx = front_point(body, s * (hw - .18), 1.1, -1, bx + .05)[0].x
        p.box("taillamp", (.04, .14, .46), (tx - .004, s * (hw - .18), 1.1), m["tail"], bevel=.015, seg=2)
        p.box("tail_bezel", (.03, .18, .50), (tx + .006, s * (hw - .18), 1.1), m["seal"], bevel=.012, seg=2)
        p.box("rear_win", (.025, .68, .46), (tx + .0, s * .42, 1.70), m["glass"], bevel=.02)
        p.box("rear_handle", (.025, .04, .18), (tx - .006, s * .12, 1.15), m["chrome"], bevel=.005)
        p.box("rack_rail", (3.0, .05, .06), (-.6, s * .72, H + .06), m["dark"], bevel=.006)
        for xx in (-1.9, -.6, .7): p.box("rack_leg", (.06, .05, .12), (xx, s * .72, H - .01), m["dark"], bevel=0)
    for xx in (-1.9, -.6, .7): p.box("rack_x", (.05, 1.5, .05), (xx, 0, H + .07), m["dark"], bevel=.004)
    tx = front_point(body, 0, 1.3, -1, bx + .05)[0].x
    p.box("rear_door_line", (.012, .022, 1.6), (tx + .002, 0, 1.3), m["seal"], bevel=0)
    gx = front_point(body, 0, .80, 1, fx - .05)[0].x
    p.box("grille_ring", (.05, .96, .20), (gx - .005, 0, .80), m["cream"], bevel=.08, seg=3)
    p.box("grille_in", (.03, .82, .11), (gx + .015, 0, .80), m["seal"], bevel=.04, seg=2)
    for i in range(2): p.box("grille_bar", (.02, .76, .02), (gx + .03, 0, .77 + i * .06), m["cream"], bevel=0)
    bumper(p, fx - .04, W - .06, .50, h=.24, d=.24, m=m["dark"], face="+X", slot=False)
    bumper(p, bx + .04, W - .06, .50, h=.24, d=.24, m=m["dark"], face="-X", inserts=False, slot=False)
    p.box("step_r", (.3, 1.2, .04), (bx - .1, 0, .34), m["steel"], bevel=.01)
    plate3(p, fx + .085, 0, .50, "+X", "TEL 3C33"); plate3(p, bx - .085, 0, .50, "-X", "TEL 3C33")
    lz = H + .16
    for s in (-1, 1): p.box("ladder_rail", (3.4, .04, .07), (-.5, s * .2, lz), m["steel"], bevel=.005)
    for i in range(10): p.box("ladder_rung", (.035, .4, .03), (-2.05 + i * .35, 0, lz), m["steel"], bevel=0)
    p.box("ladder_strap", (.04, .5, .1), (.2, 0, lz + .01), m["orange"], bevel=.005)
    p.cyl("beacon_base", .09, .03, (fx - 1.5, 0, H + .02), m["dark"], verts=10)
    p.cyl("beacon", .07, .12, (fx - 1.5, 0, H + .09), m["amber"], verts=10, bevel=.01)
    p.cyl("antenna", .008, .35, (fx - 1.8, -.6, H + .17), m["seal"], verts=6)
    flush_pockets(p)
    return p.o

# ====================================================================== cab-over cab (box truck, bucket truck)
def cab_over(p, cx, cabL, Wt, m_cab, z0=.55, belt=1.12, sh=1.42, H=2.50, R=.46, ax=None, wheels=True, hub="orangeL", stripe=None):
    """Rounded cab-over cab centred at cx (length cabL): big windscreen, door windows, round lamps, dark bumper."""
    m = mats(); hw = Wt / 2; fx, bx = cx + cabL / 2, cx - cabL / 2
    yb, ys, yt = hw - .08, hw - .03, hw - .14
    S = []; idx = {}
    def st(x, pts, tag=None):
        if tag: idx[tag] = len(S)
        S.append((x, pts))
    st(fx, [(0, z0 + .12), (yb - .26, z0 + .12), (hw - .14, belt - .22), (hw - .16, belt - .04), (hw - .40, belt + .02), (0, belt + .05)])
    st(fx - .10, [(0, z0 + .02), (yb - .02, z0 + .02), (hw - .02, belt - .02), (ys - .03, sh - .02), (yt - .02, sh + .02), (0, sh + .05)], "cowl")
    st(fx - .42, [(0, z0), (yb, z0), (hw, belt), (ys, sh), (yt, H - .06), (0, H)], "roof_f")
    st(bx + .10, [(0, z0), (yb, z0), (hw, belt), (ys, sh), (yt, H - .06), (0, H)], "roof_r")
    st(bx, [(0, z0 + .02), (yb - .04, z0 + .02), (hw - .04, belt), (ys - .04, sh), (yt - .04, H - .10), (0, H - .06)])
    ic, irf, irr = idx["cowl"], idx["roof_f"], idx["roof_r"]
    def rc(i, band):
        if i == ic and band == 4: return .6
        if i == irf and band >= 3: return .35
        if i == irr and band >= 1: return .55
        return 0.0
    def lc(i, pt):
        if pt == 3 and i >= ic: return .45
        if pt == 4 and i >= irf: return .35
        if pt in (1, 2): return .2
        return 0.0
    cab = loft(p, "cab", S, m_cab, subdiv=2, ring_crease=rc, long_crease=lc, face_mat=lambda i, b: 1 if b == 0 else 0, mats_list=(m["seal"],))
    ax = ax if ax is not None else fx - 1.0
    for s in (-1, 1): p.arch(cab, ax, s * hw, R + .10, R + .02, w=.5)
    plane_window(p, cab, S, ic, 5, irf, 5, 2 * yt - .14, "windscreen", inset=.10, round_=.05)
    side_windows(p, cab, S, irf, {"win_door": (bx + 1.22, bx + .28)}, inset=.22, zc_off=.06)
    for s in (-1, 1):
        p.cyl("archliner", R + .08, .14, (ax, s * (hw - .50), R + .02), m["seal"], rot=(rad(90), 0, 0), verts=16)
        arch_flare(p, cab, ax, R, s, m_cab, hw, rr=.06, extra=.16)
        if wheels: wheel3(p, (ax, s * (hw - .20), R + .02), R=R, w=.28, side=s, hub=hub, verts=20)
        seam3(p, cab, bx + .22, .80, 2.1, s); seam3(p, cab, bx + 1.30, .80, 2.1, s)
        handle3(p, cab, bx + .42, 1.30, s)
        body_lamp(p, cab, s * .72, .98, .15, m["lamp"], 1)
        body_box(p, cab, "indicator", (.04, .14, .08), s * .48, .98, m["orangeL"], 1)
        loc, n = side_point(cab, fx - .40, 1.95, s, hw)
        p.box("mirror_arm", (.04, .22, .04), (loc.x, loc.y + s * .11, loc.z), m["dark"], bevel=.005)
        p.box("mirror_h", (.07, .10, .40), (loc.x, loc.y + s * .25, loc.z - .05), m["dark"], bevel=.025, seg=2)
        p.box("mirror_g", (.012, .07, .34), (loc.x + .036, loc.y + s * .25, loc.z - .05), m["glassL"], bevel=0)
        p.box("step", (.5, .3, .05), (cx, s * (hw - .06), .55), m["steel"], bevel=.01)
        p.box("step2", (.5, .3, .05), (cx, s * (hw - .06), .9), m["steel"], bevel=.01)
        p.box("wiper", (.02, .7, .025), (fx - .14, s * .5, sh + .08), m["seal"], rot=(0, rad(-78), rad(-25 * s)), bevel=0)
        if stripe:
            side_plate(p, cab, "cab_stripe", cx - .1, 1.24, cabL - .7, .16, s, stripe[0])
            side_plate(p, cab, "cab_stripe2", cx - .1, 1.12, cabL - .7, .045, s, stripe[1])
    gx = front_point(cab, 0, 1.22, 1, fx - .05)[0].x
    p.box("grille", (.05, 1.3, .32), (gx - .005, 0, 1.22), m["seal"], bevel=.03, seg=2)
    for i in range(3): p.box("grille_bar", (.02, 1.18, .035), (gx + .02, 0, 1.10 + i * .11), m["cream"], bevel=0)
    bumper(p, fx - .02, Wt + .02, .55, h=.30, d=.22, m=m["dark"], face="+X", inserts=True, slot=False)
    plate3(p, fx + .10, 0, .55, "+X", "TRK 2B25")
    flush_pockets(p)
    return cab

def truck_rear_wheels(p, x, hw, R, s, dual=True, hub="rimC"):
    wheel3(p, (x, s * (hw - .18), R + .02), R=R, w=.28, side=s, hub=hub, verts=20)
    if dual: wheel3(p, (x, s * (hw - .48), R + .02), R=R, w=.28, side=s, hub=hub, verts=20, holes=0)

# ====================================================================== 2. CAMINHAO DE OFERTAS
def box_truck(c, paint_="orange", stripe="red"):
    """Cab-over supplier truck 7.6 x 2.4 x 3.5 m: rounded orange cab, aluminium ribbed box, roll-up rear door, banner on -Y."""
    p = P(c); m = mats(); Lt, Wt = 7.6, 2.4; hw = Wt / 2; fx, bx = Lt / 2, -Lt / 2
    cabL = 2.1; cx = fx - cabL / 2; R = .46
    p.box("chassis", (Lt - .4, 1.0, .22), (-.1, 0, .62), m["ink"], bevel=.02)
    p.box("chassis_rail_l", (Lt - 1.0, .08, .18), (-.3, -.5, .62), m["dark"], bevel=.01)
    cab_over(p, cx, cabL, Wt, paint_m(paint_), R=R, ax=fx - 1.0)
    p.cyl("beacon", .07, .1, (cx - .5, -.6, 2.52), m["amber"], verts=10)
    p.cyl("fuel_tank", .3, 1.0, (bx + 2.6, -(hw - .3), .62), m["chrome"], rot=(0, rad(90), 0), verts=16, bevel=.03)
    for dx in (-.35, .35): p.box("tank_strap", (.05, .64, .64), (bx + 2.6 + dx, -(hw - .3), .62), m["dark"], bevel=.01)
    p.box("battery_box", (.7, .35, .4), (bx + 3.6, -(hw - .25), .62), m["dark"], bevel=.03)
    p.cyl("exhaust", .05, 1.0, (bx + 1.4, -(hw - .2), .4), m["grey"], rot=(0, rad(90), 0), verts=8)
    bl = Lt - cabL - .25; bcx = bx + bl / 2
    box_body(p, "cargo", bl, Wt + .08, 2.5, m["alu"], bcx, .80, r=.22, face_mat=lambda i, b: 1 if b >= 4 else 0, mats_list=(m["white"],))
    p.box("cargo_floor", (bl + .04, Wt + .12, .08), (bcx, 0, .82), m["dark"], bevel=.015)
    for s in (-1, 1):
        for xx in (bx + .06, bx + bl - .06): p.box("cargo_post", (.08, .05, 2.4), (xx, s * (hw + .055), 2.05), m["steel"], bevel=.008)
        p.box("rub_rail", (bl - .2, .04, .1), (bcx, s * (hw + .07), 1.05), m[stripe], bevel=.005)
        p.box("top_rail", (bl - .2, .04, .12), (bcx, s * (hw + .07), 3.18), m[stripe], bevel=.005)
        p.box("marker", (.12, .03, .05), (bx + .3, s * (hw + .08), 3.1), m["amber"], bevel=.006)
    p.box("banner", (bl - .6, .03, 1.1), (bcx, -(hw + .08), 2.0), m["yellow"], bevel=.01)
    p.box("banner_border", (bl - .5, .02, 1.2), (bcx, -(hw + .07), 2.0), m["red"], bevel=.01)
    p.txt("OFERTA", .48, (bcx - .55, -(hw + .105), 2.22), m["red"], face="-Y", res=2)
    p.txt("-25%", .50, (bcx + 1.5, -(hw + .105), 2.22), m["navy"], face="-Y", res=2)
    p.txt("DIRETO DO FORNECEDOR", .16, (bcx, -(hw + .105), 1.68), m["navy"], face="-Y", res=2)
    p.box("roll_door", (.04, Wt - .3, 2.25), (bx - .02, 0, 1.98), m["steel"], bevel=.01)
    for i in range(8): p.box("roll_slat", (.02, Wt - .34, .015), (bx - .045, 0, .98 + i * .27), m["dark"], bevel=0)
    p.box("roll_bar", (.05, Wt - .2, .08), (bx - .04, 0, 1.1), m["dark"], bevel=.01)
    p.box("roll_latch", (.06, .14, .22), (bx - .05, .3, 1.0), m["dark"], bevel=.01)
    p.box("roll_drum", (.3, Wt - .2, .3), (bx + .1, 0, 3.0), m["dark"], bevel=.08, seg=3)
    for s in (-1, 1):
        p.box("rear_lamp", (.05, .12, .4), (bx - .03, s * (hw - .25), .78), m["tail"], bevel=.015)
        p.box("rear_lamp_bezel", (.03, .16, .46), (bx - .015, s * (hw - .25), .78), m["ink"], bevel=.006)
        p.box("mudguard", (1.1, .36, .06), (bx + 1.5, s * (hw - .25), R * 2 + .12), m["ink"], bevel=.015)
        arc_tube(p, "mudguard_arc", (bx + 1.5, s * (hw - .25), R + .02), R + .12, .03, 10, 170, m["ink"], segs=12, verts=5)
        p.box("mudflap", (.06, .3, .4), (bx + 1.5 - .5, s * (hw - .25), .3), m["rubber"], bevel=.005)
        truck_rear_wheels(p, bx + 1.5, hw, R, s)
    p.box("underride", (.08, Wt - .4, .14), (bx - .02, 0, .48), m["hazard"], bevel=.01)
    plate3(p, bx - .07, 0, .6, "-X", "OFE 2B25")
    flush_pockets(p)
    return p.o

# ====================================================================== 1. HORA DO RUSH (city bus)
def bus_body(p, L, W, H, z0, m_body, nose=.45, tail=.45, corner=.28, x0=0.0):
    """Rounded bus body: flat flanks, big corner radii, rounded nose and tail, nearly vertical windscreen."""
    hw = W / 2; fx, bx = L / 2, -L / 2
    S = []; idx = {}
    def st(x, pts, tag=None):
        if tag: idx[tag] = len(S)
        S.append((x + x0, pts))
    base = [(0, z0), (hw - corner, z0), (hw, z0 + corner), (hw, 1.70), (hw - corner * .6, H - corner), (0, H)]
    st(fx, [(0, z0 + .16), (hw - .40, z0 + .16), (hw - .22, z0 + .42), (hw - .20, 1.10), (hw - .42, 1.18), (0, 1.22)])
    st(fx - .14, [(0, z0 + .03), (hw - .20, z0 + .03), (hw - .05, z0 + .22), (hw - .04, 1.26), (hw - .22, 1.34), (0, 1.38)], "cowl")
    st(fx - nose, [(0, z0), (hw - corner, z0), (hw, z0 + corner), (hw, 1.70), (hw - corner * .6 - .02, H - corner - .02), (0, H - .02)], "roof_f")
    st(bx + tail, base, "roof_r")
    st(bx + .12, [(0, z0 + .03), (hw - .20, z0 + .03), (hw - .05, z0 + .22), (hw - .05, 1.70), (hw - .24, H - .20), (0, H - .16)], "tail_base")
    st(bx, [(0, z0 + .16), (hw - .40, z0 + .16), (hw - .22, z0 + .42), (hw - .22, 1.60), (hw - .42, H - .40), (0, H - .36)])
    ic, irf, irr, itb = idx["cowl"], idx["roof_f"], idx["roof_r"], idx["tail_base"]
    def rc(i, band):
        if i == ic and band == 4: return .6
        if i in (irf, irr) and band >= 2: return .4
        if i == itb and band >= 3: return .4
        return 0.0
    def lc(i, pt):
        if pt in (1, 2, 3, 4) and irf <= i < irr: return .45
        if pt in (2, 3) and i < irf: return .2
        return 0.0
    body = loft(p, "bus_body", S, m_body, subdiv=2, ring_crease=rc, long_crease=lc, face_mat=lambda i, b: 1 if b == 0 else 0, mats_list=(mats()["seal"],))
    return body, S, idx

def city_bus(c, body="white", stripe="teal", accent="yellow", sign="123 CENTRO", num="123"):
    """Brazilian low-floor city bus: 11 x 2.5 x 3.05 m, doors on +Y (sidewalk), livery on -Y (camera)."""
    p = P(c); m = mats(); Lb, Wb, H, z0 = 11.0, 2.5, 3.05, .34
    fx, bx = Lb / 2, -Lb / 2; hw = Wb / 2
    axles = (fx - 2.5, bx + 2.8); R = .55
    body_o, S, idx = bus_body(p, Lb, Wb, H, z0, paint_m(body))
    for s in (-1, 1):
        for ax in axles: p.arch(body_o, ax, s * hw, R + .14, R + .02, w=.7)
    # windows: window band pockets with 7 panes per side (door openings skipped on +Y), windscreen, rear glass
    plane_window(p, body_o, S, idx["cowl"], 5, idx["roof_f"], 5, Wb - .50, "windscreen", inset=.16, round_=.06)
    plane_window(p, body_o, S, idx["tail_base"], 5, idx["roof_r"], 5, Wb - .7, "rear_glass", flip=True, inset=.30)
    n = 7; band = Lb - 1.3; w0 = band / n
    for s in (-1, 1):
        for i in range(n):
            px = -.35 - band / 2 + w0 * (i + .5)
            if s == 1 and (abs(px - (fx - 1.3)) < .9 or abs(px - .1) < .9): continue
            flat_side_window(p, body_o, px, 2.22, w0 - .10, 1.10, s, name="win", seal=.035)
            p.box("win_slider", (w0 - .22, .012, .02), (px, s * (hw - .012), 2.22), m["seal"], bevel=0)
    for s in (-1, 1):
        for ax in axles:
            p.cyl("archliner", R + .1, .14, (ax, s * (hw - .52), R + .02), m["seal"], rot=(rad(90), 0, 0), verts=16)
            arch_flare(p, body_o, ax, R, s, paint_m(body), hw, rr=.065, extra=.20)
            wheel3(p, (ax, s * (hw - .17), R + .02), R=R, w=.32, side=s, hub="teal", verts=22)
        p.box("underbody", (Lb - 1.2, .1, .22), (0, s * (hw - .18), .22), m["ink"], bevel=.01)
        side_plate(p, body_o, "skirt_stripe", -.2, .72, Lb - 1.2, .36, s, m[stripe], avoid=[(ax, R + .32) for ax in axles])
    p.box("chassis", (Lb - .6, Wb - .9, .34), (0, 0, .2), m["ink"], bevel=.02)
    # livery, camera side (-Y)
    side_plate(p, body_o, "stripe_main", -.2, 1.42, Lb - .9, .32, -1, m[stripe], avoid=[(ax, R + .32) for ax in axles])
    side_plate(p, body_o, "stripe_thin", -.1, 1.12, Lb - .6, .07, -1, m[accent], avoid=[(ax, R + .32) for ax in axles])
    side_text(p, body_o, "TRANSPORTE URBANO", .21, -.55, 1.42, -1, m["white"], spacing=1.05)
    side_text(p, body_o, num, .34, fx - 1.2, .66, -1, m["white"])
    side_text(p, body_o, "LINHA 123 - CENTRO", .11, bx + 1.25, .66, -1, m["white"])
    # doors on +Y: double leaves (separate islands for the rig) in dark frames
    for dx in (fx - 1.3, .1):
        side_plate(p, body_o, "door_frame", dx, 1.5, 1.5, 2.3, 1, m["ink"], t=.03, proud=.0, bevel=.01, flat=True)
        for lx in (-.36, .36):
            p.box("door_leaf", (.62, .03, 2.3), (dx + lx, hw + .035, 1.6), paint_m(body), bevel=.01)
            p.box("door_glass", (.5, .02, 1.3), (dx + lx, hw + .052, 2.05), m["glass"], bevel=.015)
            p.box("door_glass_low", (.5, .02, .55), (dx + lx, hw + .052, .95), m["glassD"], bevel=.015)
        p.box("door_lamp", (.4, .04, .08), (dx, hw - .01, 2.78), m["amber"], bevel=.01)
    # front: destination LED, lamps, grille, bumper, wipers, mirrors
    gloc, gn = front_point(body_o, 0, 2.58, 1, fx - .3)
    body_box(p, body_o, "dest_box", (.08, Wb - .7, .32), 0, 2.58, m["ink"], 1, sink=.06, bevel=.02)
    body_box(p, body_o, "dest_led", (.03, Wb - .9, .24), 0, 2.58, m["ledOff"], 1, sink=-.018, bevel=.004)
    front_text(p, body_o, sign, .17, 0, 2.57, 1, m["amber"], proud=.012)
    gx = gloc.x
    for s in (-1, 1):
        wl, wn = front_point(body_o, s * .55, 1.40, 1, fx - .3)
        p.box("wiper", (.03, .75, .03), (wl.x - .01, s * .55, 1.40), m["ink"], rot=(rad(-30 * s), 0, 0), bevel=0)
        body_lamp(p, body_o, s * .80, .98, .16, m["lamp"], 1)
        body_box(p, body_o, "indicator", (.04, .16, .09), s * .50, .98, m["orangeL"], 1)
        body_box(p, body_o, "foglamp", (.03, .14, .10), s * .95, .62, m["lamp"], 1)
        bus_mirror(p, body_o, fx - .55, 2.45, s)
    gx2 = front_point(body_o, 0, .78, 1, fx - .1)[0].x
    p.box("grille", (.05, 1.1, .22), (gx2 - .005, 0, .78), m["seal"], bevel=.03, seg=2)
    for i in range(3): p.box("grille_bar", (.02, 1.0, .03), (gx2 + .02, 0, .70 + i * .07), m["cream"], bevel=0)
    bumper(p, fx - .06, Wb - .1, .46, h=.30, d=.24, m=m["dark"], face="+X", inserts=True, slot=False)
    p.box("bumper_f_lip", (.12, Wb - .5, .08), (fx + .02, 0, .33), m[stripe], bevel=.02)
    plate3(p, fx + .08, 0, .50, "+X", "BUS 2A26")
    front_text(p, body_o, "CHECKOUT", .08, 0, 2.93, 1, m[stripe], proud=.006, res=1)
    # rear
    tx = front_point(body_o, 0, 1.0, -1, bx + .1)[0].x
    p.box("engine_hatch", (.03, 1.7, .9), (tx + .004, 0, 1.0), paint_m(body), bevel=.01)
    for i in range(5): p.box("louvre", (.03, 1.5, .05), (tx - .01, 0, .65 + i * .16), m["ink"], bevel=0)
    body_box(p, body_o, "rear_sign", (.06, 1.0, .26), 0, 2.56, m["ink"], -1, sink=.05, bevel=.01)
    front_text(p, body_o, num, .16, 0, 2.55, -1, m["amber"], proud=.014)
    for s in (-1, 1):
        txx = front_point(body_o, s * 1.0, 1.33, -1, bx + .1)[0].x
        for i, col in enumerate(("tail", "amber", "white")):
            p.box("taillamp", (.05, .16, .16), (txx - .012, s * 1.0, 1.52 - i * .19), m[col], bevel=.02)
        p.box("tail_bezel", (.03, .2, .62), (txx + .0, s * 1.0, 1.33), m["ink"], bevel=.01)
    bumper(p, bx + .06, Wb - .1, .46, h=.30, d=.24, m=m["dark"], face="-X", inserts=False, slot=False)
    plate3(p, bx - .08, 0, .50, "-X", "BUS 2A26")
    # roof: AC unit, hatches, antenna
    p.box("roof_ac", (2.4, 1.6, .28), (bx + 3.0, 0, H + .08), paint_m(body), bevel=.08, seg=3)
    for i in range(4): p.box("ac_vent", (.35, 1.3, .03), (bx + 2.2 + i * .5, 0, H + .23), m["grey"], bevel=.005)
    for hx in (fx - 2.6, .9):
        p.box("roof_hatch", (.8, .8, .07), (hx, 0, H), m["grey"], bevel=.02)
        p.box("roof_hatch_lid", (.7, .7, .03), (hx, 0, H + .05), paint_m(body), bevel=.01)
    p.cyl("antenna", .012, .4, (fx - .6, -.6, H + .16), m["ink"], verts=6)
    flush_pockets(p)
    return p.o

# ====================================================================== 7. EXCURSAO DA ESCOLA (school bus)
def school_bus(c):
    """Classic yellow school bus 9.0 x 2.4 x 3.0 m with a rounded hood, black stripes, ESCOLAR, stop arm on -Y, door on +Y."""
    p = P(c); m = mats(); Lb, Wb, H, z0 = 9.0, 2.4, 3.0, .55; hw = Wb / 2; fx, bx = Lb / 2, -Lb / 2; R = .48
    Y = paint_m("yellowS"); hoodL = 1.7; bodyL = Lb - hoodL; bcx = bx + bodyL / 2; bf = bx + bodyL
    body, S, idx = bus_body(p, bodyL, Wb, H, z0, Y, nose=.40, tail=.45, corner=.26, x0=bcx)
    for s in (-1, 1): p.arch(body, bx + 2.3, s * hw, R + .14, R + .02, w=.7)
    plane_window(p, body, S, idx["cowl"], 5, idx["roof_f"], 5, Wb - .50, "windscreen", inset=.56, round_=.06, shift=-.22)
    plane_window(p, body, S, idx["tail_base"], 5, idx["roof_r"], 5, Wb - 1.2, "rear_glass", inset=.9, flip=True)
    # hood: its own small loft (rounded, sloped), yellow
    hw2 = hw - .30
    HS = [(fx, [(0, .70), (hw2 - .30, .70), (hw2 - .12, .95), (hw2 - .14, 1.30), (hw2 - .40, 1.44), (0, 1.48)]),
          (fx - .25, [(0, .62), (hw2 - .05, .62), (hw2, .95), (hw2 - .02, 1.42), (hw2 - .22, 1.56), (0, 1.60)]),
          (bf + .15, [(0, .62), (hw2, .62), (hw2 + .04, .95), (hw2 + .02, 1.52), (hw2 - .20, 1.70), (0, 1.74)]),
          (bf - .20, [(0, .62), (hw2, .62), (hw2 + .04, .95), (hw2 + .02, 1.52), (hw2 - .20, 1.72), (0, 1.76)])]
    hood = loft(p, "hood", HS, Y, subdiv=2, ring_crease=lambda i, b: .7 if i == 3 else 0.0, long_crease=lambda i, pt: .6 if pt in (1, 3) else 0.0)
    for s in (-1, 1):
        p.box("fender", (1.5, .50, .14), (fx - 1.95, s * (hw - .25), R * 2 + .20), Y, bevel=.06, seg=2)
        arc_tube(p, "fender_arc", (fx - 1.95, s * (hw - .25), R + .02), R + .20, .07, 0, 180, Y, segs=14, verts=8)
        wheel3(p, (fx - 1.95, s * (hw - .22), R + .02), R=R, w=.30, side=s, hub="orangeL", verts=20)
        p.cyl("archliner", R + .1, .14, (bx + 2.3, s * (hw - .52), R + .02), m["seal"], rot=(rad(90), 0, 0), verts=16)
        arch_flare(p, body, bx + 2.3, R, s, Y, hw, rr=.065, extra=.20)
        truck_rear_wheels(p, bx + 2.3, hw, R, s, hub="orangeL")
        if s > 0: p.box("step", (.5, .3, .05), (bf + .3, s * (hw - .5), .62), m["steel"], bevel=.01)
    p.box("chassis", (Lb - .8, Wb - .9, .4), (-.2, 0, .45), m["ink"], bevel=.02)
    p.box("front_frame", (hoodL, 1.1, .5), (fx - hoodL / 2, 0, .5), m["ink"], bevel=.02)
    n = 8; band = bodyL - .8; w0 = band / n
    for s in (-1, 1):
        for i in range(n):
            px = bcx - .1 - band / 2 + w0 * (i + .5)
            if s == 1 and i == n - 1: continue
            flat_side_window(p, body, px, 2.15, w0 - .10, .92, s, name="win", seal=.035)
            p.box("win_split", (w0 - .22, .012, .02), (px, s * (hw - .012), 2.25), m["seal"], bevel=0)
        side_plate(p, body, "stripe_black", bcx, 1.52, bodyL - .3, .14, s, m["ink"], avoid=[(bx + 2.3, R + .32)])
        side_plate(p, body, "stripe_black2", bcx, .98, bodyL - .3, .14, s, m["ink"], avoid=[(bx + 2.3, R + .32)])
        side_text(p, body, "ESCOLAR", .36, bcx - .4, 1.26, s, m["ink"])
        side_text(p, body, "ESCOLA MUNICIPAL", .085, bcx + 1.8, 1.62, s, m["ink"])
        p.box("marker_f", (.12, .03, .06), (bf - .3, s * (hw - .02), 2.78), m["amber"], bevel=.006)
        p.box("marker_r", (.12, .03, .06), (bx + .3, s * (hw - .02), 2.78), m["tail"], bevel=.006)
    dx = bf - .62
    side_plate(p, body, "door_frame", dx, 1.62, 1.06, 2.0, 1, m["ink"], t=.03, proud=.0, bevel=.01, flat=True)
    for lx in (-.24, .24):
        p.box("door_leaf", (.44, .03, 2.05), (dx + lx, hw + .035, 1.75), Y, bevel=.01)
        p.box("door_glass", (.34, .02, .8), (dx + lx, hw + .052, 2.15), m["glass"], bevel=.012)
        p.box("door_glass2", (.34, .02, .5), (dx + lx, hw + .052, 1.35), m["glass"], bevel=.012)
    gx = front_point(body, 0, 2.66, 1, bf)[0].x
    body_box(p, body, "roof_sign", (.1, 1.3, .28), 0, 2.56, m["ink"], 1, sink=.07, bevel=.02)
    front_text(p, body, "ESCOLAR", .16, 0, 2.55, 1, m["amber"], proud=.035)
    gx2 = front_point(hood, 0, 1.0, 1, fx - .05)[0].x
    p.box("grille", (.05, 1.0, .46), (gx2 - .005, 0, 1.02), m["seal"], bevel=.04, seg=2)
    for i in range(5): p.box("grille_bar", (.03, .9, .03), (gx2 + .02, 0, .84 + i * .09), m["cream"], bevel=0)
    bumper(p, fx - .02, Wb - .3, .50, h=.30, d=.24, m=m["dark"], face="+X", inserts=True, slot=False)
    bumper(p, bx + .04, Wb + .02, .50, h=.30, d=.24, m=m["dark"], face="-X", inserts=False, slot=False)
    for s in (-1, 1):
        body_lamp(p, hood, s * .52, 1.16, .15, m["lamp"], 1, ring="chrome")
        body_box(p, hood, "indicator", (.04, .18, .1), s * .52, .84, m["orangeL"], 1)
        bus_mirror(p, body, bf - .45, 2.35, s, arm=.36, head=(.07, .2, .42))
        wl, wn = front_point(body, s * .5, 2.1, 1, bf)
        p.box("wiper", (.03, .6, .03), (wl.x - .01, s * .5, 2.1), m["ink"], rot=(rad(-30 * s), 0, 0), bevel=0)
        p.cyl("roof_flash", .08, .1, (bf - .5, s * .6, H + .03), m["tail"] if s < 0 else m["amber"], verts=12)
        p.cyl("roof_flash_r", .08, .1, (bx + .7, s * .6, H + .03), m["tail"], verts=12)
        txx = front_point(body, s * .9, 1.2, -1, bx + .1)[0].x
        p.box("taillamp", (.05, .16, .16), (txx - .01, s * .9, 1.3), m["tail"], bevel=.02)
        p.box("taillamp2", (.05, .16, .16), (txx - .01, s * .9, 1.1), m["amber"], bevel=.02)
    plate3(p, fx + .10, 0, .78, "+X", "ESC 5E55"); plate3(p, bx - .10, 0, .78, "-X", "ESC 5E55")
    tx = front_point(body, 0, 1.75, -1, bx + .1)[0].x
    p.box("rear_door", (.04, 1.1, 1.8), (tx + .004, 0, 1.75), Y, bevel=.01)
    p.box("rear_glass_d", (.04, .9, .7), (tx - .006, 0, 2.2), m["glass"], bevel=.03)
    front_text(p, body, "SAÍDA DE EMERGÊNCIA", .07, 0, 1.6, -1, m["ink"], proud=.03, res=1)
    p.box("roof_hatch", (.7, .7, .06), (bcx + .5, 0, H), Y, bevel=.02)
    p.box("roof_hatch2", (.7, .7, .06), (bcx - 2.0, 0, H), Y, bevel=.02)
    p.cyl("exhaust", .05, .9, (bx + .8, -(hw - .25), .32), m["grey"], rot=(0, rad(90), 0), verts=8)
    sx_ = bf - 1.0; sy = -(hw + .01)
    p.box("arm_hinge", (.1, .06, .5), (sx_, sy, 1.95), m["ink"], bevel=.008)
    p.box("arm_bar", (.05, .55, .05), (sx_, sy - .3, 1.95), m["ink"], bevel=.005)
    p.cyl("stop_sign", .28, .03, (sx_, sy - .6, 1.95), m["red"], rot=(rad(90), 0, 0), verts=8)
    p.cyl("stop_sign_rim", .3, .02, (sx_, sy - .59, 1.95), m["white"], rot=(rad(90), 0, 0), verts=8)
    p.txt("PARE", .13, (sx_, sy - .62, 1.95), m["white"], face="-Y")
    for s in (-1, 1): p.cyl("stop_led", .035, .02, (sx_, sy - .625, 1.95 + s * .19), m["ledR"], rot=(rad(90), 0, 0), verts=8)
    flush_pockets(p)
    return p.o

# ====================================================================== QUEDA DE ENERGIA (bucket truck body)
def bucket_truck(c):
    """Power-company truck 7.4 x 2.3 m: rounded white cab-over cab, orange stripes, aerial-device body with tool lockers,
    outriggers and the turret pedestal. Boom is a separate prop (Energia_BucketBoom) pivoting at WP.BT_TURRET."""
    p = P(c); m = mats(); Lt, Wt = 7.4, 2.3; hw = Wt / 2; fx, bx = Lt / 2, -Lt / 2
    Wh, O, D, I, S_, Ch = paint_m("white"), m["orange"], m["dark"], m["ink"], m["steel"], m["chrome"]
    cabL = 2.1; cx = fx - cabL / 2; R = .46
    p.box("chassis", (Lt - .4, 1.0, .22), (-.1, 0, .62), I, bevel=.02)
    for s in (-1, 1): p.box("chassis_rail", (Lt - .8, .08, .2), (-.2, s * .5, .62), D, bevel=.01)
    cab = cab_over(p, cx, cabL, Wt, Wh, R=R, ax=fx - 1.0, stripe=(O, m["navy"]))
    side_text(p, cab, "ENERGIA", .12, cx - .1, 1.42, -1, m["navy"])
    p.box("lightbar_base", (.3, 1.1, .05), (cx, 0, 2.50), D, bevel=.006)
    p.box("lightbar", (.26, 1.0, .11), (cx, 0, 2.57), m["amber"], bevel=.03, seg=2)
    p.cyl("fuel_tank", .3, 1.0, (bx + 2.6, -(hw - .3), .62), Ch, rot=(0, rad(90), 0), verts=16, bevel=.03)
    for dx in (-.35, .35): p.box("tank_strap", (.05, .64, .64), (bx + 2.6 + dx, -(hw - .3), .62), D, bevel=.01)
    p.cyl("exhaust", .05, 1.0, (bx + 1.4, (hw - .2), .4), m["grey"], rot=(0, rad(90), 0), verts=8)
    bl = Lt - cabL - .3; bcx = bx + bl / 2
    p.box("deck", (bl, Wt + .06, .08), (bcx, 0, 1.3), D, bevel=.012)
    p.box("deck_tread", (bl - .2, Wt - .1, .012), (bcx, 0, 1.345), m["rubberM"], bevel=0)
    box_body(p, "lockers", bl - .1, Wt + .02, .5, Wh, bcx, .77, r=.12)
    for s in (-1, 1):
        p.box("locker_stripe", (bl - .2, .012, .16), (bcx, s * (hw + .018), 1.0), O, bevel=.004)
        for i in range(4):
            xx = bx + .5 + i * (bl - .6) / 3.2
            p.seam(xx, s * (hw + .012), .8, 1.24, face=s, m=I)
            if i % 2: p.handle((xx - .5, s * (hw + .02), 1.15), face=s)
        p.box("tall_locker", (.9, .4, 1.2), (bx + bl - .5, s * (hw - .2), 1.95), Wh, bevel=.05, seg=3)
        p.seam(bx + bl - .5, s * (hw + .002), 1.4, 2.5, face=s, m=I)
        p.box("tl_stripe", (.9, .012, .16), (bx + bl - .5, s * (hw + .006), 1.9), O, bevel=.004)
        for xx in (bx + .45, bx + bl - 1.3):
            p.box("outrigger", (.26, .5, .24), (xx, s * (hw - .05), 1.12), m["hazard"], bevel=.012)
            p.box("outr_leg", (.12, .12, .62), (xx, s * (hw + .05), .5), D, bevel=0)
            p.box("outr_pad", (.4, .4, .07), (xx, s * (hw + .05), .04), D, bevel=.012)
            p.tube("outr_ram", (xx, s * (hw + .05), 1.1), (xx, s * (hw + .05), .6), .035, Ch, verts=8)
        p.box("rear_lamp", (.05, .12, .4), (bx - .03, s * (hw - .25), .78), m["tail"], bevel=.015)
        p.box("rear_lamp_bezel", (.03, .16, .46), (bx - .015, s * (hw - .25), .78), I, bevel=.006)
        p.box("mudguard", (1.1, .36, .06), (bx + 1.5, s * (hw - .25), R * 2 + .12), I, bevel=.015)
        arc_tube(p, "mudguard_arc", (bx + 1.5, s * (hw - .25), R + .02), R + .12, .03, 10, 170, I, segs=12, verts=5)
        truck_rear_wheels(p, bx + 1.5, hw, R, s)
        p.box("cone_rack", (.25, .25, .5), (bx + .3, s * (hw - .35), 1.6), O, bevel=.02)
    p.txt("ENERGIA", .2, (bcx - .3, -(hw + .028), 1.05), m["navy"], face="-Y")
    p.box("underride", (.08, Wt - .4, .14), (bx - .02, 0, .48), m["hazard"], bevel=.01)
    p.box("rear_bumper", (.14, Wt, .2), (bx - .04, 0, .62), D, bevel=.03)
    plate3(p, bx - .11, 0, .62, "-X", "ENE 7E12")
    p.box("rear_hazard", (.03, 1.4, .2), (bx - .05, 0, 1.0), m["hazardR"], bevel=0)
    T = WP.BT_TURRET
    p.cyl("pedestal", .48, .3, (T.x, T.y, 1.34 + .15), m["greyD"], verts=18, bevel=.02)
    p.box("ped_stripe", (.98, .98, .1), (T.x, T.y, 1.4), m["hazard"], bevel=.0)
    p.box("ladder_rail", (.04, .04, 1.0), (bx + bl - .05, -(hw - .5), 1.8), S_, bevel=0)
    p.box("ladder_rail", (.04, .04, 1.0), (bx + bl - .05, -(hw - .9), 1.8), S_, bevel=0)
    for i in range(4): p.box("ladder_rung", (.03, .4, .03), (bx + bl - .05, -(hw - .7), 1.45 + i * .25), S_, bevel=0)
    p.cyl("beacon_r", .07, .12, (bx + .3, 0, 1.4 + .06), m["amber"], verts=10, bevel=.012)
    flush_pockets(p)
    return WP.set_pivot(p.o)

# ====================================================================== RUA EM OBRAS (backhoe body)
def backhoe(c):
    """Retroescavadeira 5.9 x 2.3 x 2.95 m: rounded yellow hood, cab with a rounded roof, front loader, rear kingpost,
    chunky tyres (big lugged rears). Same footprint and arm hinge (WP.BH_HINGE) as v2."""
    p = P(c); m = mats(); Y, D, I, S_, Ch, G = paint_m("yellow"), m["dark"], m["ink"], m["steel"], m["chrome"], m["glass"]
    Rf, Rr, yf, yr = .50, .74, .88, .95
    p.box("frame", (4.3, .9, .40), (-.05, 0, .82), I, bevel=.02)
    p.box("frame_low", (3.2, 1.15, .14), (.2, 0, .60), D, bevel=.01)
    p.box("axle_f", (.18, 1.9, .14), (1.65, 0, Rf + .02), D, bevel=.01)
    p.box("axle_r", (.3, 2.0, .3), (-1.25, 0, Rr + .02), D, bevel=.03)
    # engine hood: rounded loft from the grille up to the cab
    HS = [(2.55, [(0, .95), (.40, .95), (.52, 1.15), (.54, 1.45), (.36, 1.58), (0, 1.62)]),
          (2.35, [(0, .92), (.58, .92), (.66, 1.10), (.66, 1.62), (.46, 1.80), (0, 1.86)]),
          (1.0, [(0, .92), (.62, .92), (.68, 1.10), (.68, 1.70), (.50, 1.88), (0, 1.94)]),
          (.40, [(0, .92), (.62, .92), (.68, 1.10), (.68, 1.72), (.50, 1.90), (0, 1.96)])]
    hood = loft(p, "hood", HS, Y, subdiv=2, ring_crease=lambda i, b: .8 if i == 3 else (.5 if i == 0 else 0.0), long_crease=lambda i, pt: .6 if pt in (1, 3, 4) else 0.0)
    for s in (-1, 1):
        for i in range(5): side_plate(p, hood, "louver", .75 + i * .33, 1.26, .18, .30, s, I, t=.01, proud=.002)
        body_lamp(p, hood, s * .34, 1.42, .11, m["lamp"], 1, ring="chrome")
        side_plate(p, hood, "hood_stripe", 1.85, 1.0, .9, .07, s, I, t=.01, proud=.002)
    gx = front_point(hood, 0, 1.12, 1, 2.5)[0].x
    p.box("grille", (.05, .80, .44), (gx - .005, 0, 1.12), I, bevel=.03, seg=2)
    for i in range(4): p.box("grille_bar", (.025, .72, .035), (gx + .02, 0, .96 + i * .11), m["grey"], bevel=0)
    p.box("bumper_f_pad", (.2, 1.3, .22), (2.5, 0, .72), D, bevel=.06, seg=3)
    p.cyl("exhaust", .045, .95, (.62, .50, 2.3), D, verts=8)
    p.cyl("exhaust_cap", .07, .09, (.62, .50, 2.78), D, verts=8)
    p.cyl("air_filter", .12, .42, (.95, -.48, 2.05), D, rot=(0, rad(90), 0), verts=10)
    p.box("filter_bracket", (.08, .18, .22), (1.1, -.48, 1.93), I, bevel=0)
    # cab: x -1.05..0.3, floor 1.32, roof 2.95; ROPS pillars black, glass all round, rounded roof cap
    cx, cw, z0, z1 = -.38, .66, 1.32, 2.95; cl = 1.35
    p.box("cab_floor", (cl, cw * 2, .12), (cx, 0, z0), D, bevel=.01)
    p.box("cab_skirt_f", (.06, cw * 2, .5), (cx + cl / 2 - .03, 0, z0 + .3), Y, bevel=.015, seg=2)
    p.box("cab_skirt_b", (.06, cw * 2, .55), (cx - cl / 2 + .03, 0, z0 + .32), Y, bevel=.015, seg=2)
    for s in (-1, 1):
        p.box("cab_skirt_s", (cl, .06, .5), (cx, s * (cw - .03), z0 + .3), Y, bevel=.015, seg=2)
        for xx in (cx - cl / 2 + .035, cx + cl / 2 - .035):
            p.box("pillar", (.08, .08, z1 - z0), (xx, s * (cw - .04), (z0 + z1) / 2), I, bevel=.02, seg=2)
        p.box("cab_side_glass", (cl - .16, .03, 1.0), (cx, s * (cw + .005), 2.33), G, bevel=.012)
        p.seam(cx + .05, s * (cw + .018), z0 + .55, z1 - .15, face=s)
        p.handle((cx - .3, s * (cw + .03), 2.0), face=s)
        p.mirror((cx + .45, s * (cw + .02), 2.4), s, arm=.22, h=.3, w=.16)
        p.box("cab_step", (.42, .22, .04), (cx + .1, s * 1.05, .95), S_, bevel=.008)
        p.box("cab_step2", (.42, .22, .04), (cx + .1, s * 1.0, 1.3), S_, bevel=.008)
        p.box("step_hanger", (.04, .04, .4), (cx + .3, s * 1.1, 1.12), I, bevel=0)
        p.box("roof_lamp", (.16, .1, .12), (cx + .5, s * .4, z1 + .1), m["lamp"], bevel=.01)
        p.box("roof_lamp_bz", (.18, .12, .14), (cx + .49, s * .4, z1 + .1), I, bevel=.006)
    p.box("cab_glass_f", (.03, cw * 2 - .16, 1.0), (cx + cl / 2 + .005, 0, 2.33), G, bevel=.012)
    p.box("cab_glass_b", (.03, cw * 2 - .16, 1.0), (cx - cl / 2 - .005, 0, 2.33), G, bevel=.012)
    p.box("cab_roof", (cl + .22, cw * 2 + .22, .16), (cx, 0, z1 + .04), Y, bevel=.07, seg=3)
    p.box("cab_roof_trim", (cl + .18, cw * 2 + .18, .04), (cx, 0, z1 - .035), I, bevel=.006)
    p.box("seat", (.5, .5, .5), (cx - .15, 0, 1.68), D, bevel=.05, seg=2)
    p.box("seat_back", (.12, .5, .55), (cx - .38, 0, 2.08), D, bevel=.04, seg=2)
    p.box("dash", (.25, 1.1, .28), (cx + .45, 0, 1.55), I, bevel=.02)
    p.cyl("wheel_col", .02, .35, (cx + .25, 0, 1.78), I, rot=(0, rad(-50), 0), verts=6)
    p.cyl("steer", .15, .025, (cx + .12, 0, 1.9), I, rot=(0, rad(-50), 0), verts=12)
    p.box("wiper", (.02, .45, .02), (cx + cl / 2 + .03, .15, 2.6), I, rot=(rad(-30), 0, 0), bevel=0)
    p.cyl("beacon_base", .09, .03, (cx - .4, 0, z1 + .13), D, verts=10)
    p.cyl("beacon", .07, .13, (cx - .4, 0, z1 + .21), m["amber"], verts=10, bevel=.012)
    # rear: kingpost mount + stabilisers
    p.box("rear_frame", (.55, 1.2, .65), (-2.15, 0, 1.08), Y, bevel=.06, seg=3)
    p.box("rear_hazard", (.03, 1.1, .2), (-2.43, 0, .9), m["hazard"], bevel=0)
    p.box("kingpost", (.32, .4, .85), (-2.42, 0, 1.25), D, bevel=.03)
    p.box("kingpost_top", (.4, .5, .12), (-2.42, 0, 1.7), D, bevel=.015)
    p.box("hyd_tank", (.6, .55, .55), (-1.75, -.0, 1.65), Y, bevel=.07, seg=3)
    p.box("tank_cap", (.1, .1, .06), (-1.6, .1, 1.95), I, bevel=.01)
    for s in (-1, 1):
        p.tube("stab", (-2.15, s * .55, 1.05), (-2.15, s * 1.42, .22), .085, Y, verts=8)
        p.tube("stab_ram", (-2.15, s * .45, 1.35), (-2.15, s * 1.1, .55), .04, Ch, verts=8)
        p.tube("stab_ram_c", (-2.15, s * .45, 1.35), (-2.15, s * .8, .92), .055, D, verts=8)
        p.box("stab_pad", (.42, .36, .08), (-2.15, s * 1.45, .06), D, bevel=.012)
        p.box("stab_pad_h", (.44, .06, .09), (-2.15, s * 1.6, .06), m["hazard"], bevel=0)
        p.box("fender", (1.75, .52, .08), (-1.25, s * yr, 2 * Rr + .12), Y, bevel=.03, seg=2)
        arc_tube(p, "fender_arc", (-1.25, s * yr, Rr + .02), Rr + .14, .06, 0, 180, Y, segs=14, verts=8)
        p.box("fender_brace", (.06, .4, .4), (-.4, s * (yr - .05), 1.3), I, bevel=0)
        p.box("taillamp", (.05, .14, .14), (-2.44, s * .45, 1.42), m["tail"], bevel=.01)
        p.box("plate_bracket", (.03, .3, .1), (-2.44, 0, 1.15), I, bevel=0)
    plate3(p, -2.47, 0, 1.15, "-X", "OBR 4A12")
    # front loader arms (pivot beside the cab) -> knee -> bucket
    A0, K0, B0 = Vector((-.15, 0, 1.78)), Vector((1.95, 0, 1.12)), Vector((3.05, 0, .62))
    for s in (-1, 1):
        off = Vector((0, s * .82, 0))
        WP.bar(p, "larm1", A0 + off, K0 + off, .13, .22, Y, bevel=.03, seg=2)
        WP.bar(p, "larm2", K0 + off, B0 + off, .13, .19, Y, bevel=.03, seg=2)
        p.box("larm_knee", (.3, .15, .3), K0 + off, Y, bevel=.04, seg=2)
        WP.pin(p, "larm_pin", A0 + off, r=.06, w=.2)
        WP.ram(p, "lift_ram", Vector((.35, s * .95, .98)), Vector((1.5, s * .95, 1.1)), .05, D, Ch)
        WP.ram(p, "tilt_ram", Vector((.75, s * .82, 1.72)), Vector((2.7, s * .82, 1.02)), .045, D, Ch)
        p.box("arm_mount", (.5, .12, .5), (-.15, s * .76, 1.6), Y, bevel=.03)
    p.cyl("larm_x", .08, 1.72, K0, Y, rot=(rad(90), 0, 0), verts=10)
    p.cyl("larm_x2", .06, 1.72, A0 + Vector((.5, 0, -.1)), D, rot=(rad(90), 0, 0), verts=8)
    bw, bd, bh = 2.3, .85, .78
    p.box("fb_back", (.07, bw, bh), (3.05, 0, .5), Y, rot=(0, rad(-22), 0), bevel=.01)
    p.box("fb_bottom", (bd, bw, .07), (3.42, 0, .1), Y, bevel=.01)
    p.box("fb_top", (.45, bw, .06), (3.3, 0, .88), Y, rot=(0, rad(-30), 0), bevel=.01)
    for s in (-1, 1):
        p.prism("fb_side", 3.1, 3.85, 2.95, 3.3, .035, .08, .9, Y, bevel=.01, seg=1).location.y = s * (bw / 2 - .035)
        p.box("fb_stripe", (.6, .03, .12), (3.2, s * (bw / 2 + .02), .78), m["hazard"], rot=(0, rad(-30), 0), bevel=0)
    p.box("fb_lip", (.12, bw + .02, .07), (3.86, 0, .1), D, bevel=.008)
    for i in range(5): p.box("fb_tooth", (.2, .14, .06), (3.95, -bw / 2 + bw * (i + .5) / 5, .1), D, bevel=0)
    p.box("fb_brace", (.5, bw - .4, .08), (3.2, 0, .55), D, rot=(0, rad(-22), 0), bevel=.01)
    # wheels: chunky, lugged rears
    for s in (-1, 1):
        wheel3(p, (1.65, s * yf, Rf + .02), R=Rf, w=.30, side=s, hub="yellow", verts=18, lugs=8)
        wheel3(p, (-1.25, s * yr, Rr + .02), R=Rr, w=.48, side=s, hub="yellow", verts=22, holes=6, lugs=10)
    p.box("counterweight", (.3, 1.2, .35), (2.62, 0, .75), D, bevel=.03)
    p.box("toolbox", (.6, .3, .35), (.55, -1.0, .85), D, bevel=.02)
    flush_pockets(p)
    return WP.set_pivot(p.o)

PROPS = {"Transito_Car": (hatchback, 2048), "Vigilancia_Car": (sedan_vigilancia, 2048), "Som_Van": (sound_van, 2048),
         "Maquininha_TelecomVan": (telecom_van, 2048), "Ofertas_BoxTruck": (box_truck, 2048), "Rush_CityBus": (city_bus, 2048),
         "Excursao_SchoolBus": (school_bus, 2048), "Energia_BucketTruck": (bucket_truck, 2048), "Obras_Backhoe": (backhoe, 2048)}
for _paint in ("blue", "yellow", "white", "teal", "green"):
    PROPS["Transito_Car" + _paint.capitalize()] = ((lambda paint: (lambda c: hatchback(c, paint=paint)))(_paint), 1024)

def export(names=None):
    out = {}
    for n in (names or PROPS):
        fn, size = PROPS[n]
        c = E.prop_collection(n); mats(); fn(c)
        out[n] = E.export_prop(n, size=size)
        print("EXPORTED", n, out[n], flush=True)
    return out
