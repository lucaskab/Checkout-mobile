"""Inspector (fiscal da vigilância sanitária) for the interactive event 18 - Checklist do fiscal.

The character is one of the game's own customers (Customer_07, the young man in the blue sweater) on the shared
Customer_01_Rig skeleton, dressed with a skinned white lab coat (fitted around the body's rest-pose silhouette),
a navy cap with a shield pictogram (brim curved up so the eyes read from the game's high camera) and a badge on
a lanyard. Clothes are skinned with a smooth Gaussian weight field sampled from the body (coat panel from the
torso / thigh vertices only, set-in sleeves from the arm vertices only), so the shoulders never tear. Two extra bones, Prop_L and Prop_R (children of
the hands, at the palms), carry the clipboard (left) and the pen / stamp / approval seal (right).
Props (own objects, origin at their pivot): Inspector_Clipboard, Inspector_Pen, Inspector_Stamp, Inspector_Seal,
Inspector_WarningNotice, Inspector_FineNotice, Inspector_Marker. Clips (24 fps, IK feet planted):
Inspect_LookAround 96, Inspect_Write 72, Inspect_Point 48, Inspect_Stamp 48, Inspect_Approve 48,
Inspect_HeadShake 48, Inspect_HangSeal 72.  No written words anywhere (pictograms only).

Run inside Blender:
    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\events_interactive\\inspector.py").read())
    arm, body, clothes, P, acts, stats = build(); review(arm, body, clothes, P, acts); check(arm, body, clothes, P, acts); save()
"""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler
from mathutils.kdtree import KDTree

HERE = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\events_interactive"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import importlib, ei_kit
importlib.reload(ei_kit)
from ei_kit import *                       # noqa
E = ei_kit

BASE = "Customer_07"


def mats():
    M = E.mats()
    if "coat_seam" not in M:
        M["coat_seam"] = k.mat("EI_coat_seam", (.80, .79, .76, 1), rough=.8, var=.03, scale=14)
    return M
RIG, BODY = "Inspector_Rig", "Inspector_Body"
FRONT = -math.pi / 2                       # the character faces -Y
V = ch.V


# ============================================================================================ skinning
_FIELD = {}


def body_field(body, groups):
    """Body vertices whose dominant bone is one of `groups`: (names, weights[n, G], KD-tree, index map)."""
    key = (body.name, tuple(groups))
    if key in _FIELD:
        return _FIELD[key]
    me = body.data; n = len(me.vertices)
    names = [g.name for g in body.vertex_groups]
    W = np.zeros((n, len(names)))
    for v in me.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(n, 3)
    dom = W.argmax(1)
    idx = np.nonzero(np.isin(dom, [names.index(g) for g in groups if g in names]))[0]
    kd = KDTree(len(idx))
    for j, i in enumerate(idx):
        kd.insert(co[i], j)
    kd.balance()
    _FIELD[key] = (names, W, kd, idx)
    return _FIELD[key]


def skin_field(obj, arm, body, groups, radius=.07, sigma=.03, passes=2):
    """[weights: smooth field] Armature-deforms `obj` with weights averaged (Gaussian kernel) over the body
    vertices of `groups` around each vertex, then relaxed over the mesh edges: no nearest-surface jumps between
    torso and arm, so the cloth bends like the body underneath without spikes."""
    names, W, kd, idx = body_field(body, groups)
    inv = arm.matrix_world.inverted() @ obj.matrix_world
    me = obj.data; n = len(me.vertices)
    out = np.zeros((n, W.shape[1]))
    for v in me.vertices:
        p = inv @ v.co
        nb = kd.find_range(p, radius)
        if len(nb) < 4:
            nb = kd.find_n(p, 8)
        acc = np.zeros(W.shape[1]); tot = 0.0
        for _, j, dist in nb:
            g = math.exp(-dist * dist / (2 * sigma * sigma)) + 1e-6
            acc += g * W[idx[j]]; tot += g
        out[v.index] = acc / tot
    adj = [[] for _ in range(n)]
    for e in me.edges:
        a, b = e.vertices; adj[a].append(b); adj[b].append(a)
    for _ in range(passes):
        new = out.copy()
        for i in range(n):
            if adj[i]:
                new[i] = 0.5 * out[i] + 0.5 * out[adj[i]].mean(0)
        out = new
    mw = obj.matrix_world.copy()
    for vg in list(obj.vertex_groups):
        obj.vertex_groups.remove(vg)
    for i in range(n):
        top = np.argsort(out[i])[::-1][:4]; s = float(out[i][top].sum())
        for g in top:
            if out[i][g] > 1e-4:
                vg = obj.vertex_groups.get(names[g]) or obj.vertex_groups.new(name=names[g])
                vg.add([i], float(out[i][g] / s), 'REPLACE')
    obj.parent = arm; obj.parent_type = 'OBJECT'
    bpy.context.view_layer.update(); obj.matrix_world = mw
    m = obj.modifiers.new("Armature", 'ARMATURE'); m.object = arm
    return obj


def clean_body_weights(body, below_z=1.65):
    """The character's auto-weights leak Torso into the upper arm well below the armpit (up to 0.5 on the outer
    side, up to 0.8 on the inner side of the sleeve of the sweater, down to the elbow), which stretches a web of
    sweater between the body and a raised arm - it showed through the coat sleeve. On this copy of the body,
    any Torso weight on a vertex that lies out at the arm (|x| beyond the torso's own side) below the deltoid is
    handed to that upper arm."""
    names = [vg.name for vg in body.vertex_groups]
    fixed = 0
    for v in body.data.vertices:
        if not v.groups or v.co.z > below_z or v.co.z < 1.05:
            continue
        ws = {names[g.group]: g.weight for g in v.groups}
        t = ws.get("Torso", 0.0)
        side = "UpperArm_R" if v.co.x > 0 else "UpperArm_L"
        arm_w = sum(w for n, w in ws.items() if n.startswith(("UpperArm", "Forearm", "Hand")))
        if t <= 0.0 or arm_w <= 0.0 or abs(v.co.x) < (0.27 if v.co.z < 1.5 else 0.295):
            continue
        body.vertex_groups["Torso"].remove([v.index])
        body.vertex_groups[side].add([v.index], ws.get(side, 0.0) + t, 'REPLACE')
        fixed += 1
    return fixed


def restrict_groups(obj, keep, below_z=None):
    """Drops every vertex group not in `keep` (renormalising the rest) for the vertices with rest z <= below_z."""
    names = [vg.name for vg in obj.vertex_groups]
    for v in obj.data.vertices:
        if below_z is not None and v.co.z > below_z:
            continue
        ws = {names[g.group]: g.weight for g in v.groups if names[g.group] in keep}
        tot = sum(ws.values())
        if tot <= 1e-6:
            continue
        for g in list(v.groups):
            if names[g.group] not in keep:
                obj.vertex_groups[g.group].remove([v.index])
        for n, w in ws.items():
            obj.vertex_groups[n].add([v.index], w / tot, 'REPLACE')


TORSO_GROUPS = ("Torso", "Thigh_L", "Thigh_R")
ARM_GROUPS = {1: ("UpperArm_R", "Forearm_R", "Hand_R"), -1: ("UpperArm_L", "Forearm_L", "Hand_L")}


# ============================================================================================ clothes
def polar(ring, centre):
    a = np.array([math.atan2(p.y - centre.y, p.x - centre.x) for p in ring])
    r = np.array([(p.xy - centre.xy).length for p in ring])
    return a, r


def fair_radii(a, r0, harmonics=4):
    """Least-squares trig polynomial through the per-angle radii, pushed out so it never cuts into the raw
    silhouette: a smooth fabric cross-section instead of the mesh's bumps."""
    cols = [np.ones_like(a)]
    for h in range(1, harmonics + 1):
        cols += [np.cos(h * a), np.sin(h * a)]
    A = np.stack(cols, 1)
    coef = np.linalg.lstsq(A, r0, rcond=None)[0]
    r = A @ coef
    return r + max(0.0, float((r0 - r).max()))


def fair_stack(raw, centres, harmonics=4, vertical=2):
    """Fairs a stack of silhouette rings (same vertex count): around each ring, then up and down the columns,
    always keeping at least the raw radius. -> list of rings"""
    A, R0 = zip(*[polar(ring, c) for ring, c in zip(raw, centres)])
    A = np.array(A); R0 = np.array(R0)
    R = np.array([fair_radii(a, r, harmonics) for a, r in zip(A, R0)])
    for _ in range(vertical):
        Rn = R.copy()
        for i in range(1, len(R) - 1):
            Rn[i] = 0.25 * R[i - 1] + 0.5 * R[i] + 0.25 * R[i + 1]
        R = Rn
    R = np.maximum(R, R0)
    out = []
    for i, (ring, c) in enumerate(zip(raw, centres)):
        # one more pass around the ring after the floor, so a single touching point does not leave a pimple
        r = fair_radii(A[i], R[i], harmonics)
        out.append([Vector((c.x + math.cos(A[i][j]) * r[j], c.y + math.sin(A[i][j]) * r[j], ring[j].z)) for j in range(len(ring))])
    return out


def coat(arm, body):
    """[weights: smooth field from the torso / thigh vertices; sleeves from the arm vertices]
    Thin fitted cotton lab coat, worn open: faired silhouette rings close around the torso (opening widening into
    a V at the collar), straight hem at mid-thigh, set-in sleeves with a shoulder cap, flat lapels, stand-up
    collar, chest pocket with a pen, two lower patch pockets and a centre vent seam down the back."""
    m = mats(); B = Body(body)
    torso = B.pts(["Torso", "Thigh_L", "Thigh_R"])
    upper = B.pts(["Torso", "Head"])                     # shoulders + neck, the arms are the sleeves' business
    N = 33                                               # odd: vertex 16 is the centre back (vent seam)
    gap = lambda z: rad(8) + rad(16) * blend(z, 1.30, 1.96)
    PAD = .020
    levels = [(0.80, torso, PAD), (0.90, torso, PAD), (1.00, torso, PAD), (1.10, torso, PAD), (1.22, torso, PAD), (1.34, torso, PAD),
              (1.46, torso, PAD), (1.58, torso, PAD), (1.70, upper, .018), (1.78, upper, .020),
              (1.86, upper, .024), (1.93, upper, .032), (1.99, upper, .038), (2.03, upper, .046)]
    ymid = float(B.pts(["Torso"])[:, 1].mean())
    raw, centres = [], []
    for i, (z, pts, pad) in enumerate(levels):
        g = gap(z)
        zs = min(z, 1.99)
        up = levels[i + 1][0] - z if i + 1 < len(levels) else 0.04
        dn = z - levels[i - 1][0] if i > 0 else 0.04
        band = max(0.035, max(up, dn) * 0.6)          # the coat clears the body between the rings too
        c = Vector((0, ymid, zs))
        ring = B.ring(pts, zs, band, N, centre=c, pad=pad, start=FRONT + g, span=2 * math.pi - 2 * g)
        for p in ring:
            p.z = z
        raw.append(ring); centres.append(Vector((0, ymid, z)))
    rings = fair_stack(raw, centres, harmonics=4, vertical=2)
    # straight hem: below the hips the coat hangs, it does not follow the thighs
    hip = [i for i, l in enumerate(levels) if l[0] <= 1.10][-1]
    for i, (z, _, _) in enumerate(levels):
        if z < levels[hip][0]:
            for p, q in zip(rings[i], rings[hip]):
                p.x, p.y = q.x, q.y
    o = mesh_from_rings("Inspector_Coat", rings)
    sol = o.modifiers.new("Solidify", 'SOLIDIFY'); sol.thickness = .010; sol.offset = 0
    parts = [o]
    # flat lapels along the V edges (chest to collar), lying on the coat
    for side in (0, N - 1):
        inner, outer = [], []
        for ring, (z, pts, pad) in zip(rings, levels):
            if z < 1.30 or z > 2.0:
                continue
            p = ring[side]; c = Vector((0, ymid, z))
            a = math.atan2(p.y - c.y, p.x - c.x); r = (p.xy - c.xy).length
            da = rad(13) * (1 if side == 0 else -1)
            inner.append(Vector((c.x + math.cos(a - da * 0.15) * (r + .006), c.y + math.sin(a - da * 0.15) * (r + .006), z)))
            outer.append(Vector((c.x + math.cos(a + da) * (r + .008), c.y + math.sin(a + da) * (r + .008), z)))
        lp = mesh_from_rings(f"lapel_{side}", [inner, outer] if side == 0 else [outer, inner])
        sm = lp.modifiers.new("Solidify", 'SOLIDIFY'); sm.thickness = .008; sm.offset = 0
        parts.append(lp)
    # centre vent seam: a narrow strip on the back (vertex N//2), from the small of the back to the hem
    back = N // 2
    strip_l, strip_r = [], []
    for ring, (z, _, _) in zip(rings, levels):
        if z > 1.36:
            continue
        p = ring[back]; c = Vector((0, ymid, z))
        d = (p.xy - c.xy).normalized(); q = Vector((p.x + d.x * .006, p.y + d.y * .006, z))
        side_v = Vector((-d.y, d.x, 0)) * .005
        strip_l.append(q - side_v); strip_r.append(q + side_v)
    vent = mesh_from_rings("coat_vent", [strip_l, strip_r])
    vm = vent.modifiers.new("Solidify", 'SOLIDIFY'); vm.thickness = .004; vm.offset = 0
    vent.data.materials.append(m["coat_seam"])
    parts.append(vent)
    # pockets: chest (with a pen) on the left (+X), two patch pockets at the hips
    def on_front(z, ang, out=.004):
        ring = rings[[i for i, l in enumerate(levels) if abs(l[0] - z) < 1e-6][0]]
        c = Vector((0, ymid, z)); a = FRONT + ang
        aa, rr = polar(ring, c); aa = np.unwrap(aa)
        if a < aa[0]:
            a += 2 * math.pi
        r = float(np.interp(a, aa, rr)) + out      # the pocket sits on the faired coat surface
        a -= 2 * math.pi if a > math.pi else 0.0
        return Vector((c.x + math.cos(a) * r, c.y + math.sin(a) * r, z)), a
    p, a = on_front(1.46, -rad(30))
    rz = a + math.pi / 2
    parts.append(k.box("pocket_chest", (.10, .010, .11), (p.x, p.y, 1.47), m["coat"], rot=(0, 0, rz), bevel=.003, seg=2))
    parts.append(k.box("pocket_chest_hem", (.102, .012, .016), (p.x, p.y, 1.47 + .055), m["coat"], rot=(0, 0, rz), bevel=.003, seg=1))
    parts.append(k.cyl("pocket_pen", .007, .08, (p.x + .03 * math.cos(a), p.y + .03 * math.sin(a) - .0, 1.53), m["navy"], verts=8, bevel=.001, seg=1))
    parts.append(k.cyl("pocket_pen_clip", .009, .03, (p.x + .03 * math.cos(a), p.y + .03 * math.sin(a), 1.55), m["chrome"], verts=8))
    for ang in (-rad(34), rad(34)):
        p, a = on_front(1.00, ang)
        rz = a + math.pi / 2
        parts.append(k.box("pocket_hip", (.13, .010, .14), (p.x, p.y, 0.98), m["coat"], rot=(0, 0, rz), bevel=.003, seg=2))
        parts.append(k.box("pocket_hip_hem", (.132, .012, .018), (p.x, p.y, 0.98 + .07), m["coat"], rot=(0, 0, rz), bevel=.003, seg=1))
    for part in parts:
        if not part.data.materials:
            part.data.materials.append(m["coat"])
    for part in parts:
        skin_field(part, arm, body, TORSO_GROUPS)
        restrict_groups(part, TORSO_GROUPS, below_z=1.62)     # the panel never follows the arms below the yoke
    # set-in sleeves: closed tube around the arm with a shoulder cap over the deltoid, faired like the panel
    for s, ua, fa, hd in ((1, "UpperArm_R", "Forearm_R", "Hand_R"), (-1, "UpperArm_L", "Forearm_L", "Hand_L")):
        allp = np.vstack([B.pts([ua]), B.pts([fa]), B.pts([hd])])
        zs = [1.80, 1.74, 1.68, 1.60, 1.52, 1.44, 1.39, 1.34, 1.29, 1.22, 1.14, 1.08, 1.03]   # cuff just above the wrist
        raw, centres = [], []
        for i, z in enumerate(zs):
            up = zs[i - 1] - z if i > 0 else 0.04
            dn = z - zs[i + 1] if i + 1 < len(zs) else 0.03
            band = max(0.035, max(up, dn) * 0.6)
            sl = allp[np.abs(allp[:, 2] - z) < band]
            c = Vector((float(sl[:, 0].mean()), float(sl[:, 1].mean()), z))
            pad = .022 if z >= 1.72 else .032 if 1.26 <= z <= 1.46 else .018     # ease at the elbow (deep bends)
            raw.append(B.ring(allp, z, band, 16, centre=c, pad=pad, start=0, span=2 * math.pi)); centres.append(c)
        rr = fair_stack(raw, centres, harmonics=2, vertical=2)
        # ease on the crease side of the elbow (front of the arm at rest): the sweater's elbow fold bulges
        # into the sleeve's crease when the forearm folds up to ~110 degrees
        for ring, c in zip(rr, centres):
            w = max(0.0, 1.0 - abs(c.z - 1.36) / 0.13)
            for p in ring:
                dv = (p.xy - c.xy).normalized()
                e = .024 * w * max(0.0, -dv.y)
                p.x += dv.x * e; p.y += dv.y * e
        top = rr[0]; c = centres[0]
        cap_ring = [Vector((c.x + (p.x - c.x) * .5, c.y + (p.y - c.y) * .5, 1.845)) for p in top]   # under the panel's shoulder
        rr = [cap_ring] + rr
        so = mesh_from_rings(f"sleeve_{s}", rr, close=True, cap_bottom=True)
        sm = so.modifiers.new("Solidify", 'SOLIDIFY'); sm.thickness = .010; sm.offset = 0
        so.data.materials.append(m["coat"])
        # tight kernel: the sleeve must bend exactly where the body does, or the forearm shows at the elbow
        skin_field(so, arm, body, ARM_GROUPS[s], radius=.045, sigma=.018, passes=1)
        parts.append(so)
        # armpit gussets: the body mesh has the sweater sleeve fused to the torso side down to z 1.45, so a raised
        # arm stretches a web of sweater between body and arm. Three strips run from the panel's armhole (torso
        # weights) to the sleeve's inner wall (arm weights), from the side round to the front: hidden inside
        # the coat at rest, they stretch with the web and bracket it.
        side = "UpperArm_R" if s > 0 else "UpperArm_L"
        for tag, da, sa in (("side", 0.0, math.pi), ("mid", -rad(16), math.pi + rad(19)), ("front", -rad(32), math.pi + rad(38))):
            T, S = [], []
            for z in (1.40, 1.46, 1.52, 1.58, 1.64, 1.70, 1.76):
                li = min(range(len(levels)), key=lambda i: abs(levels[i][0] - z))
                c = Vector((0, ymid, levels[li][0]))
                aa, rad_ = polar(rings[li], c); aa = np.unwrap(aa)
                a_side = (0.0 + da) if s > 0 else (math.pi - da)
                while a_side < aa[0]:
                    a_side += 2 * math.pi
                r = float(np.interp(a_side, aa, rad_)) - .004
                T.append(Vector((c.x + math.cos(a_side) * r, c.y + math.sin(a_side) * r, z)))
                ri = min(range(len(rr)), key=lambda i: abs(rr[i][0].z - z))
                cs = centres[min(range(len(centres)), key=lambda i: abs(centres[i].z - z))]
                want = Vector((math.cos(sa) * s, math.sin(sa)))
                inner = max(rr[ri], key=lambda p: (p.xy - cs.xy).normalized().dot(want))
                S.append(Vector((inner.x - s * .004, inner.y, z)))
            gs = mesh_from_rings(f"gusset_{tag}_{s}", [T, S] if s > 0 else [S, T])
            gs.data.materials.append(m["coat"])
            n = len(T); torso_first = s > 0
            rk.skin(gs, arm, lambda co, i: {"Torso": 1.0} if (i < n) == torso_first else {side: 1.0})
            parts.append(gs)
    return parts


def visor(name, cx, cy, cz, r0, r1, half_angle, m, lift=.045, curl=.016):
    """Curved cap brim: a polar grid from the crown radius r0 out to r1, rising towards the tip (the eyes stay
    visible from the game's high camera) and curling down a little at the sides."""
    bm = bmesh.new(); rows = []
    na, nr = 14, 5
    for i in range(nr + 1):
        t = i / nr; r = mix(r0, r1, t)
        row = []
        for j in range(na + 1):
            a = FRONT + mix(-half_angle, half_angle, j / na)
            side = abs(mix(-1, 1, j / na))
            z = cz + lift * t - curl * side * side * t
            row.append(bm.verts.new((cx + math.cos(a) * r, cy + math.sin(a) * r, z)))
        rows.append(row)
    for ra, rb in zip(rows, rows[1:]):
        for j in range(na):
            bm.faces.new((ra[j], ra[j + 1], rb[j + 1], rb[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    sm = o.modifiers.new("Solidify", 'SOLIDIFY'); sm.thickness = .011; sm.offset = 0
    return o


def cap(arm, body):
    """Navy cap, 15 % narrower than the first pass, sitting on the hair (bottom edge at z 2.29, the eyebrows are
    at 2.21): the dome clears the hair everywhere and the short brim rises ~35 degrees, so the eyes stay visible
    from the game's high camera even with the head nodded 20 degrees (Inspect_Write / Inspect_Stamp)."""
    m = mats()
    S, SZ = 0.87, 0.78                                   # radial / vertical scale of the first cap
    cx, cy, cz = 0.0, -0.02, 2.32
    prof = [(0, .17), (.08, .168), (.15, .145), (.195, .09), (.212, .02), (.212, -.03), (.205, -.04)]
    dome = lathe("Inspector_Cap", [(r * S, z * SZ) for r, z in prof], (cx, cy, cz), m["navy"], seg=24)
    vis = visor("cap_visor", cx, cy, cz - .022, .212 * S * 0.92, .240, rad(52), m["navy"], lift=.048, curl=.014)
    btn = k.ball("cap_button", .014, (cx, cy, cz + .17 * SZ), m["navy"], sub=1)
    band = k.cyl("cap_band", .212 * S + .002, .026, (cx, cy, cz - .022), m["teal"], verts=24, bevel=.004, seg=1)
    fy, fz = cy - .206 * S, cz + .062 * SZ
    sh = shield(None, (cx, fy, fz), .075 * S, .085 * S, m["cream"], depth=.008, name="cap_shield")
    sh.rotation_euler = (rad(-14), 0, 0)
    chk = pictogram_check(None, (cx, fy - .010, fz), .045 * S, m["green"], thick=.008, depth=.006, name="cap_check")
    for o in chk:
        o.matrix_world = Matrix.Translation((cx, fy, fz)) @ Euler((rad(-14), 0, 0)).to_matrix().to_4x4() @ Matrix.Translation((-cx, -fy, -fz)) @ o.matrix_world
    parts = [dome, vis, btn, band, sh] + chk
    for p in parts:
        skin_const(p, arm, "Head")
    return parts


def badge(arm, body):
    m = mats()
    pts = [(0, .18, 1.985), (.09, .13, 1.995), (.13, .02, 1.985), (.105, -.11, 1.90), (.05, -.20, 1.78), (.012, -.235, 1.66)]
    pts = [Vector(p) for p in pts]
    parts = []
    for s in (1, -1):
        for a, b in zip(pts, pts[1:]):
            A, Bv = Vector((a.x * s, a.y, a.z)), Vector((b.x * s, b.y, b.z))
            parts.append(k.tube("lanyard", A, Bv, .007, m["teal"], verts=6))
    parts.append(k.cyl("badge_clip", .012, .02, (0, -.238, 1.645), m["chrome"], rot=(rad(90), 0, 0), verts=10))
    parts.append(k.box("badge_card", (.10, .010, .13), (0, -.246, 1.575), m["white"], bevel=.005, seg=2))
    parts.append(k.box("badge_head", (.10, .004, .028), (0, -.254, 1.625), m["navy"], bevel=.002, seg=1))
    parts.append(k.box("badge_photo", (.036, .004, .046), (-.024, -.254, 1.56), m["skin"], bevel=.002, seg=1))
    parts.append(k.box("badge_line1", (.036, .004, .008), (.022, -.254, 1.572), m["grey"], bevel=.001, seg=1))
    parts.append(k.box("badge_line2", (.036, .004, .008), (.022, -.254, 1.553), m["grey"], bevel=.001, seg=1))
    parts.append(k.cyl("badge_seal", .012, .004, (.03, -.254, 1.53), m["green"], rot=(rad(90), 0, 0), verts=10))
    for p in parts:
        skin_const(p, arm, "Torso")
    return parts


# ============================================================================================ props
def clipboard():
    """Teal clipboard with a steel clip and a checklist sheet: three check boxes (one ticked) with grey bars.
    Local frame: lying in XY, face +Z, long axis +Y, origin at the centre of the back face."""
    m = mats(); W, L = .32, .45
    parts = [k.box("board", (W, L, .012), (0, 0, .006), m["teal"], bevel=.006, seg=3)]
    parts.append(k.box("clip_base", (.12, .05, .020), (0, L / 2 - .045, .018), m["chrome"], bevel=.004, seg=2))
    parts.append(k.box("clip_lever", (.10, .034, .012), (0, L / 2 - .030, .032), m["chrome"], rot=(rad(-18), 0, 0), bevel=.003, seg=2))
    parts.append(k.box("paper", (W - .05, L - .10, .004), (0, -.02, .014), m["paper"], bevel=0))
    for i in range(3):
        y = .10 - i * .11
        parts.append(k.box(f"cbox_{i}", (.044, .044, .004), (-.10, y, .0175), m["ink"], bevel=0))
        parts.append(k.box(f"cbox_in_{i}", (.034, .034, .004), (-.10, y, .0185), m["paper"], bevel=0))
        for j, w in enumerate((.14, .10)):
            parts.append(k.box(f"bar_{i}_{j}", (w, .012, .003), (-.045 + w / 2, y + .012 - j * .024, .0185), m["grey"], bevel=0))
    parts += pictogram_check(None, (-.10, .10, .021), .04, m["green"], thick=.008, depth=.004, plane='XY', name="tick")
    return join(parts, "Inspector_Clipboard", origin=(0, 0, 0))


def pen():
    m = mats()
    parts = [k.cyl("pen_body", .010, .17, (0, 0, 0), m["navy"], verts=10, bevel=.002, seg=1),
             k.cyl("pen_tip", .010, .025, (0, 0, -.095), m["chrome"], r2=.002, verts=10),
             k.cyl("pen_cap", .011, .04, (0, 0, .065), m["cream"], verts=10, bevel=.002, seg=1),
             k.box("pen_clip", (.006, .005, .04), (0, -.012, .06), m["chrome"], bevel=.001, seg=1)]
    return join(parts, "Inspector_Pen", origin=(0, 0, 0))


def stamp():
    """Rubber stamp: wooden handle, navy base. Origin at the bottom (the face that stamps)."""
    m = mats()
    handle = lathe("stamp_handle", [(0, .16), (.020, .158), (.030, .145), (.028, .125), (.018, .10), (.015, .07), (.022, .05), (.040, .036), (.040, .03), (0, .03)], (0, 0, 0), m["wood"], seg=16)
    base = k.box("stamp_base", (.095, .06, .030), (0, 0, .016), m["navy"], bevel=.006, seg=3)
    rub = k.box("stamp_rubber", (.085, .05, .004), (0, 0, .001), m["red"], bevel=.001, seg=1)
    return join([handle, base, rub], "Inspector_Stamp", origin=(0, 0, 0))


def seal():
    """Round green approval seal (world scale, 26 cm) with a cream rim, a tick and a star; a loop to hang it.
    Face -Y, origin at the centre."""
    m = mats(); R = .13
    parts = [k.cyl("seal_disc", R, .014, (0, 0, 0), m["green"], rot=(rad(90), 0, 0), verts=36, bevel=.004, seg=2),
             k.cyl("seal_rim", R - .018, .006, (0, -.009, 0), m["cream"], rot=(rad(90), 0, 0), verts=36),
             k.cyl("seal_inner", R - .030, .006, (0, -.012, 0), m["green"], rot=(rad(90), 0, 0), verts=36)]
    parts += pictogram_check(None, (0, -.018, -.02), .12, m["cream"], thick=.024, depth=.008, name="seal_check")
    parts.append(star(None, (0, -.016, R - .048), .03, m["gold"], depth=.008, name="seal_star"))
    for sx in (-1, 1):
        parts.append(star(None, (sx * (R - .06), -.016, .005), .018, m["gold"], depth=.008, name="seal_star_s"))
    bpy.ops.mesh.primitive_torus_add(major_radius=.018, minor_radius=.005, major_segments=16, minor_segments=6, location=(0, 0, R + .012), rotation=(0, 0, 0))
    ring = bpy.context.active_object; ring.name = "seal_loop"; k.finish(ring, m["chrome"], bevel=0)
    parts.append(ring)
    parts.append(k.tube("seal_string", (0, 0, R + .02), (0, 0, R + .075), .004, m["cream"], verts=6))
    return join(parts, "Inspector_Seal", origin=(0, 0, 0))


def notice(kind):
    """Yellow warning card with an exclamation mark, or red fine card with a cross (world scale, 30 x 40 cm).
    Face -Y, origin at the centre of the back."""
    m = mats(); W, H = .30, .40
    col, ink, name = ("yellow", "ink", "Inspector_WarningNotice") if kind == "warning" else ("red", "white", "Inspector_FineNotice")
    parts = [k.box("card", (W, .010, H), (0, 0, 0), m[col], bevel=.004, seg=2),
             k.box("border_t", (W - .03, .004, .012), (0, -.007, H / 2 - .02), m[ink], bevel=0),
             k.box("border_b", (W - .03, .004, .012), (0, -.007, -H / 2 + .02), m[ink], bevel=0),
             k.box("border_l", (.012, .004, H - .03), (-W / 2 + .02, -.007, 0), m[ink], bevel=0),
             k.box("border_r", (.012, .004, H - .03), (W / 2 - .02, -.007, 0), m[ink], bevel=0)]
    if kind == "warning":
        parts.append(k.cyl("tri", .125, .006, (0, -.009, -.01), m[ink], rot=(rad(90), 0, 0), verts=3))
        parts.append(k.cyl("tri_in", .105, .006, (0, -.011, -.01), m[col], rot=(rad(90), 0, 0), verts=3))
        parts += pictogram_bang(None, (0, -.016, -.04), .13, m[ink], thick=.028, depth=.008)
    else:
        parts.append(k.cyl("disc", .115, .006, (0, -.009, 0), m[ink], rot=(rad(90), 0, 0), verts=32))
        parts.append(k.cyl("disc_in", .098, .006, (0, -.011, 0), m[col], rot=(rad(90), 0, 0), verts=32))
        parts += pictogram_cross(None, (0, -.016, 0), .13, m[ink], thick=.03, depth=.008)
    for sx in (-1, 1):
        parts.append(k.cyl("hole", .010, .004, (sx * (W / 2 - .035), -.008, H / 2 - .035), m["grey"], rot=(rad(90), 0, 0), verts=10))
    return join(parts, name, origin=(0, 0, 0))


def marker():
    """Floating inspection marker: a magnifying glass with an orange "!" (world scale, ~45 cm). Origin at the
    bottom of the handle; faces -Y."""
    m = mats()
    bpy.ops.mesh.primitive_torus_add(major_radius=.11, minor_radius=.022, major_segments=28, minor_segments=8, location=(0, 0, .30), rotation=(rad(90), 0, 0))
    ring = bpy.context.active_object; ring.name = "lens_ring"; k.finish(ring, m["navy"], bevel=0)
    parts = [ring, k.cyl("lens", .095, .012, (0, 0, .30), m["glass"], rot=(rad(90), 0, 0), verts=28)]
    parts.append(k.box("lens_shine", (.05, .006, .012), (-.045, -.008, .34), m["white"], rot=(0, rad(45), 0), bevel=.004, seg=2))
    parts.append(k.cyl("handle", .026, .20, (0.0, 0, .11), m["navy"], r2=.030, verts=12, bevel=.004, seg=2))
    parts.append(k.cyl("handle_cap", .032, .02, (0, 0, .01), m["navy"], verts=12, bevel=.004, seg=2))
    parts.append(k.cyl("ferrule", .030, .02, (0, 0, .20), m["chrome"], verts=12))
    bang = pictogram_bang(None, (0, -.03, .30), .17, m["orange"], thick=.04, depth=.014)
    for b in bang:   # rounded bar
        if b.name.startswith("bang_bar"):
            b.modifiers["Bevel"].width = .012
    parts += bang
    o = join(parts, "Inspector_Marker", origin=(0, 0, 0))
    o.rotation_euler = (0, 0, 0)
    return o


def props():
    out = {"clipboard": clipboard(), "pen": pen(), "stamp": stamp(), "seal": seal(),
           "warning": notice("warning"), "fine": notice("fine"), "marker": marker()}
    for o in out.values():
        for p in o.data.polygons:
            p.use_smooth = True
    return out


# ============================================================================================ clips
CLIPS = {}
ss, mix, TAU = ch.ss, ch.mix, ch.TAU


def clip(name, frames):
    def deco(fn):
        CLIPS[name] = (frames, fn, False)
        return fn
    return deco


def board_hold(p, lift=0.0, side=0.0):
    """Left hand (bone Hand_L, -X) holding the clipboard in front of the belly."""
    return p.hand_at(-1, 0.06 + side, -0.40, 1.44 + lift, pole=V(-1.0, 0.2, -0.6))


def board_hip(p):
    """Clipboard hanging by the left hip."""
    return p.hand_at(-1, 0.40, -0.24, 1.06, pole=V(-0.9, 0.5, -1.0))


def pen_rest(p):
    return p.hand_at(1, 0.29, -0.06, 1.08, pole=V(0.9, 0.6, -1.0), bend=-8)


@clip("Inspect_LookAround", 96)
def look_around(r, f):
    t = (f - 1) / 96.0
    turn = 34 * math.sin(TAU * t) * (0.6 + 0.4 * math.cos(TAU * 2 * t) ** 2)
    p = ch.Pose(r).head(turn=turn, nod=-4 + 6 * math.sin(TAU * 2 * t) ** 2, tilt=2 * math.sin(TAU * t)).torso(turn=9 * math.sin(TAU * t))
    board_hold(p, lift=-0.14, side=0.08); pen_rest(p)
    for s in (1, -1): p.planted(s)
    return p


@clip("Inspect_Write", 72)
def write(r, f):
    look = ss(44, 52, f) * (1 - ss(62, 70, f))
    jx = 0.028 * math.sin(TAU * (f - 1) / 9) * (1 - look)
    jz = 0.010 * math.sin(TAU * (f - 1) / 4.5) * (1 - look)
    p = ch.Pose(r).head(nod=16 - 14 * look, turn=20 * look).torso(lean=4)      # <= 20 deg total: eyes under the brim
    board_hold(p)
    p.hand_at(1, 0.11 + jx, -0.50, 1.61 + jz - 0.04 * look, pole=V(1.0, 0.3, -0.7), bend=-12)
    for s in (1, -1): p.planted(s)
    return p


@clip("Inspect_Point", 48)
def point(r, f):
    up = ss(1, 11, f) * (1 - ss(36, 46, f))
    bob = 0.015 * math.sin(TAU * (f - 12) / 10) * ss(12, 16, f) * (1 - ss(30, 36, f))
    p = ch.Pose(r).head(nod=-8 * up, turn=-6 * up).torso(lean=6 * up, turn=-7 * up)
    board_hip(p)
    p.hand_at(1, mix(0.29, 0.24, up), mix(-0.06, -0.74, up), mix(1.08, 1.82, up) + bob, pole=V(1.0, 0.5, -0.5), bend=-6 * up)
    for s in (1, -1): p.planted(s)
    return p


@clip("Inspect_Stamp", 48)
def stamp_clip(r, f):
    down = ss(8, 15, f) * (1 - ss(20, 28, f))
    press = 0.012 * math.sin(TAU * (f - 15) / 10) * ss(15, 17, f) * (1 - ss(20, 22, f))
    p = ch.Pose(r).head(nod=13 + 3 * down).torso(lean=3 + 2 * down)
    p.hand_at(-1, 0.10, -0.44, 1.36, pole=V(-1.0, 0.3, -0.6))                        # board held flat
    p.hand_at(1, mix(0.12, 0.09, down), -0.50, mix(1.78, 1.52, down) - press, pole=V(1.0, 0.4, -0.6), bend=-20)
    for s in (1, -1): p.planted(s)
    return p


@clip("Inspect_Approve", 48)
def approve(r, f):
    up = ss(1, 10, f) * (1 - ss(38, 46, f))
    nod = 9 * math.sin(TAU * (f - 10) / 14) * ss(10, 14, f) * (1 - ss(30, 36, f))     # two friendly nods
    p = ch.Pose(r).head(nod=-4 * up + nod, tilt=-6 * up, turn=4 * up).torso(lean=-3 * up, tilt=2 * up)
    board_hip(p)
    # open hand raised beside the shoulder, palm forward ("tudo certo"); elbow ~110 deg so the sleeve stays closed
    p.hand_at(1, mix(0.29, 0.50, up), mix(-0.06, -0.42, up), mix(1.08, 1.76, up), pole=V(1.0, 0.7, -0.4), bend=-35 * up)
    for s in (1, -1): p.planted(s)
    return p


@clip("Inspect_HeadShake", 48)
def head_shake(r, f):
    env = ss(1, 7, f) * (1 - ss(40, 48, f))
    p = ch.Pose(r).head(turn=22 * math.sin(TAU * (f - 1) / 16) * env, nod=8).torso(lean=2)
    board_hold(p, lift=-0.10, side=0.06)
    p.hand_at(1, 0.33, 0.02, 1.12, pole=V(1.0, 0.8, 0.0))                             # hand on the hip
    for s in (1, -1): p.planted(s)
    return p


@clip("Inspect_HangSeal", 72)
def hang_seal(r, f):
    up = ss(1, 22, f) * (1 - ss(48, 66, f))
    push = 0.05 * ss(28, 34, f) * (1 - ss(40, 46, f))
    p = ch.Pose(r).head(nod=-16 * up).torso(lean=5 * up, lift=0.0)
    board_hip(p)
    p.hand_at(1, mix(0.29, 0.08, up), mix(-0.06, -0.62, up) - push, mix(1.08, 2.08, up), pole=V(1.0, 0.5, -0.5), bend=-10 * up)
    for s in (1, -1): p.planted(s, dx=0.0)
    return p


# ============================================================================================ build
def add_prop_bones(arm):
    bpy.context.view_layer.objects.active = arm
    with bpy.context.temp_override(**ctx(), active_object=arm, object=arm):
        bpy.ops.object.mode_set(mode='EDIT')
        eb = arm.data.edit_bones
        for side in ("L", "R"):
            h = eb["Hand_" + side]
            b = eb.new("Prop_" + side)
            b.head = h.head + Vector((0, 0.01, -0.10)); b.tail = b.head + Vector((0, 0, -0.08)); b.roll = 0
            b.parent = h; b.use_connect = False; b.use_deform = False
        bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'


def place_props(arm, P, acts):
    """Parents the hand props to Prop_L / Prop_R so they sit right in the Inspect_Write / Inspect_Stamp /
    Inspect_HangSeal poses (the offsets are fixed, so they follow the hands in every clip)."""
    acts = {a.name: a for a in acts}
    # clipboard: on the left palm, nearly flat, tilted towards the face
    set_action(arm, acts["Inspect_Write"], 1)
    palm = bone_world(arm, "Prop_L").translation
    long_axis = Vector((0, -0.96, 0.28)); normal = Vector((0, 0.28, 0.96)); across = Vector((1, 0, 0))
    Rm = Matrix((across, long_axis, normal)).transposed().to_4x4()
    centre = palm + across * 0.17 + normal * 0.045 - long_axis * 0.03
    attach_to_bone(P["clipboard"], arm, "Prop_L", Matrix.Translation(centre) @ Rm)
    # pen: through the right fist, tip towards the sheet
    palm = bone_world(arm, "Prop_R").translation
    axis = (normal * 0.8 + across * 0.5 + long_axis * 0.15).normalized()     # writing grip, leaning right
    tip = palm - normal * 0.07
    pen_m = Matrix.Translation(tip + axis * 0.085) @ axis.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    attach_to_bone(P["pen"], arm, "Prop_R", pen_m)
    # stamp: in the right fist (Inspect_Stamp), standing on the board's normal, its base below the fist
    set_action(arm, acts["Inspect_Stamp"], 16)
    palm = bone_world(arm, "Prop_R").translation
    n = (P["clipboard"].matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    attach_to_bone(P["stamp"], arm, "Prop_R", Matrix.Translation(palm - n * 0.06) @ n.to_track_quat('Z', 'Y').to_matrix().to_4x4())
    # seal: hanging from the right hand (string pinched between the fingers), facing the door in front
    set_action(arm, acts["Inspect_HangSeal"], 36)
    palm = bone_world(arm, "Prop_R").translation
    attach_to_bone(P["seal"], arm, "Prop_R", Matrix.Translation(palm + Vector((0, -0.01, -0.205))))
    arm.animation_data.action = None
    bpy.context.scene.frame_set(1)


def build():
    rk.reset()
    bpy.context.scene.frame_set(1)
    arm, body = load_character(os.path.join(CHARS, BASE + ".fbx"), os.path.join(CHARS, BASE + ".png"), RIG, BODY)
    arm.matrix_world = Matrix.Identity(4); body.matrix_world = Matrix.Identity(4)
    clean_body_weights(body)
    add_prop_bones(arm)
    clothes = coat(arm, body) + cap(arm, body) + badge(arm, body)
    P = props()
    acts = bake_clips(arm, CLIPS)
    place_props(arm, P, acts)
    for o in (P["warning"], P["fine"], P["marker"], P["seal"]):
        pass
    stats = {"body_tris": tris([body]), "clothes_tris": tris(clothes), "props": {n: tris([o]) for n, o in P.items()},
             "bones": [b.name for b in arm.data.bones], "clips": {a.name: (int(a.frame_start), int(a.frame_end)) for a in acts}}
    return arm, body, clothes, P, acts, stats


# ============================================================================================ review renders
def review(arm, body, clothes, P, acts, res=(700, 900)):
    os.makedirs(TMP, exist_ok=True); os.makedirs(REVIEW, exist_ok=True)
    sc = studio(res=res)
    world_props = [P["warning"], P["fine"], P["marker"], P["seal"]]
    hide = lambda objs, h: [setattr(o, "hide_render", h) for o in objs]
    # 1. turnaround (rest pose, props in the hands)
    arm.animation_data.action = None; sc.frame_set(1)
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
    hide([P["stamp"], P["seal"], P["warning"], P["fine"], P["marker"]], True)
    shots = []
    for name, d in (("front", (0, -1, 0.18)), ("3/4", (0.8, -1, 0.22)), ("side", (1, 0, 0.18)), ("back", (0, 1, 0.18))):
        aim((0, 0, 1.22), d, 5.6, lens=60)
        label("Inspector - " + name, 0.035)
        shots.append(render(os.path.join(TMP, f"insp_turn_{len(shots)}.png")))
    contact_sheet(shots, os.path.join(REVIEW, "inspector_turnaround.png"), cols=4)
    # 2. props on the floor
    hide([body] + clothes + [P["clipboard"], P["pen"], P["stamp"], P["seal"]], True)
    arm.hide_render = True
    sc.render.resolution_x, sc.render.resolution_y = 700, 700
    shots = []
    spots = [("Clipboard", P["clipboard"], (0, 0, .25), Euler((rad(55), 0, rad(10))), (.25, -.9, .9), 1.1),
             ("Stamp", P["stamp"], (0, 0, 0), Euler((0, 0, rad(20))), (.9, -.9, .55), 1.3),
             ("Approval seal", P["seal"], (0, 0, .14), Euler((0, 0, 0)), (.15, -1, .5), 1.1),
             ("Warning notice", P["warning"], (0, 0, .20), Euler((0, 0, 0)), (.15, -1, .5), 1.1),
             ("Fine notice", P["fine"], (0, 0, .20), Euler((0, 0, 0)), (.15, -1, .5), 1.1),
             ("Inspection marker", P["marker"], (0, 0, .05), Euler((0, 0, rad(10))), (.5, -1, .45), 1.1)]
    for name, o, loc, rot, d, pad in spots:
        keep = (o.parent, o.parent_type, o.parent_bone, o.matrix_parent_inverse.copy(), o.matrix_world.copy())
        o.parent = None; o.hide_render = False
        o.matrix_world = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
        bpy.context.view_layer.update()
        frame_objects([o], direction=d, lens=55, pad=pad)
        label(name, 0.035)
        shots.append(render(os.path.join(TMP, f"insp_prop_{len(shots)}.png")))
        o.hide_render = True
        o.parent, o.parent_type, o.parent_bone = keep[0], keep[1], keep[2]
        o.matrix_parent_inverse = keep[3]; o.matrix_world = keep[4]
    contact_sheet(shots, os.path.join(REVIEW, "inspector_props.png"), cols=3)
    # 3. poses: one key frame per clip
    hide([body] + clothes, False); arm.hide_render = False
    sc.render.resolution_x, sc.render.resolution_y = 600, 800
    keys = {"Inspect_LookAround": 26, "Inspect_Write": 20, "Inspect_Point": 22, "Inspect_Stamp": 16,
            "Inspect_Approve": 24, "Inspect_HeadShake": 20, "Inspect_HangSeal": 36}
    shots = []
    order = {n: i for i, n in enumerate(CLIPS)}
    for a in sorted(acts, key=lambda a: order.get(a.name, 99)):
        set_action(arm, a, keys.get(a.name, 1))
        hide([P["clipboard"]], False)
        P["pen"].hide_render = a.name not in ("Inspect_Write", "Inspect_LookAround", "Inspect_HeadShake")
        P["stamp"].hide_render = a.name != "Inspect_Stamp"
        P["seal"].hide_render = a.name != "Inspect_HangSeal"
        aim((0.0, -0.15, 1.42), (0.55, -1, 0.25), 4.4, lens=60)
        label(f"{a.name}  f{keys.get(a.name, 1)}/{int(a.frame_end)}", 0.035)
        shots.append(render(os.path.join(TMP, f"insp_pose_{len(shots)}.png")))
    arm.animation_data.action = None; sc.frame_set(1)
    hide(world_props, False); P["stamp"].hide_render = False; P["pen"].hide_render = False
    hide_label()
    return contact_sheet(shots, os.path.join(REVIEW, "inspector_poses.png"), cols=4)


def check(arm, body, clothes, P, acts, res=(480, 640)):
    """Verification sheet (Temp/qa/interactive/inspector_check.png): three frames of every clip from the game's
    high 3/4 camera - eyes under the brim, sleeves at the shoulder, nothing of the shirt showing through."""
    os.makedirs(TMP, exist_ok=True)
    sc = studio(res=res)
    for o in (P["warning"], P["fine"], P["marker"]):
        o.hide_render = True
    hide = lambda objs, h: [setattr(o, "hide_render", h) for o in objs]
    shots = []
    order = {n: i for i, n in enumerate(CLIPS)}
    for a in sorted(acts, key=lambda a: order.get(a.name, 99)):
        n = int(a.frame_end)
        for f in (max(1, round(n * .25)), round(n * .5), round(n * .75)):
            set_action(arm, a, f)
            hide([P["clipboard"]], False)
            P["pen"].hide_render = a.name not in ("Inspect_Write", "Inspect_LookAround", "Inspect_HeadShake")
            P["stamp"].hide_render = a.name != "Inspect_Stamp"
            P["seal"].hide_render = a.name != "Inspect_HangSeal"
            aim((0.0, -0.10, 1.40), (0.6, -1, 0.75), 4.3, lens=50)
            label(f"{a.name}  f{f}/{n}", 0.035)
            shots.append(render(os.path.join(TMP, f"insp_chk_{len(shots)}.png")))
    arm.animation_data.action = None; sc.frame_set(1)
    for o in (P["warning"], P["fine"], P["marker"], P["stamp"], P["pen"], P["seal"]):
        o.hide_render = False
    hide_label()
    return contact_sheet(shots, os.path.join(TMP, "inspector_check.png"), cols=6)


def save():
    return save_as(os.path.join(HERE, "inspector.blend"))
