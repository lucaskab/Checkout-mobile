"""Caramelo, the store dog (Lucas 08/11/2026: "mascote vira-lata caramelo").

Stage 1 - sculpt: a medium mutt in the game's soft cartoon style (like the Tripo chickens): metaball body fused into
one skin, voxel-remeshed and relaid as quads (QuadriFlow) for clean deformation; separate parts for the lower jaw,
tongue, eyes, eyelids, ears and nose so the rig can open the mouth, blink/sleep and flick the ears.
Real-world metres, Z up, the dog faces -Y (like the game's characters). Shoulder height ~0.47 m.

Run inside Blender:
    exec(open("/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/ArtSource/pets/caramelo_model.py").read())
    parts = build_model()
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

ART = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/ArtSource"
HERE = os.path.join(ART, "pets")
V = Vector


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.metaballs, bpy.data.armatures, bpy.data.actions, bpy.data.curves):
        for b in list(coll):
            if b.users == 0:
                coll.remove(b)


def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def ctx_obj(o):
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


# ------------------------------------------------------------------------------------------------ body metaballs
def _quat_x_to(d):
    """Rotation taking +X onto direction d."""
    return V((1, 0, 0)).rotation_difference(d.normalized())


# Blender's metaball surface sits at ~0.575 R (stiffness 2, threshold 0.6): K maps "wanted radius" to R.
K = 1.70


def capsule(mb, a, b, r, stiff=2.0):
    a, b = V(a), V(b)
    r *= K
    e = mb.elements.new(type='CAPSULE')
    e.co = (a + b) / 2
    e.radius = r
    e.size_x = (b - a).length / 2
    e.rotation = _quat_x_to(b - a)
    e.stiffness = stiff
    return e


def ellipsoid(mb, c, size, r=1.0, rot=(0, 0, 0), stiff=2.0):
    e = mb.elements.new(type='ELLIPSOID')
    e.co = V(c)
    e.radius = r * K
    e.size_x, e.size_y, e.size_z = size
    e.rotation = Euler(rot).to_quaternion()
    e.stiffness = stiff
    return e


def ball(mb, c, r, stiff=2.0):
    e = mb.elements.new(type='BALL')
    e.co = V(c); e.radius = r * K; e.stiffness = stiff
    return e


# key points of the skeleton (also used by the rig): one side, mirrored in X
P = dict(
    chest=V((0, -0.17, 0.40)), waist=V((0, 0.03, 0.415)), hips=V((0, 0.19, 0.425)),
    neck0=V((0, -0.27, 0.47)), neck1=V((0, -0.35, 0.60)), head=V((0, -0.395, 0.665)),
    snout=V((0, -0.525, 0.628)), nose=V((0, -0.625, 0.640)), jaw=V((0, -0.44, 0.612)),
    shoulder=V((0.075, -0.205, 0.39)), elbow=V((0.078, -0.175, 0.235)), wrist=V((0.072, -0.20, 0.085)),
    fpaw=V((0.072, -0.225, 0.022)),
    hip=V((0.085, 0.205, 0.40)), knee=V((0.095, 0.135, 0.255)), hock=V((0.085, 0.245, 0.125)),
    hpaw=V((0.080, 0.215, 0.022)),
    tail0=V((0, 0.29, 0.46)),
    ear=V((0.068, -0.37, 0.745)),
    eye=V((0.047, -0.488, 0.692)),
)
TAIL = [V((0, 0.29, 0.46)), V((0, 0.35, 0.50)), V((0, 0.385, 0.565)), V((0, 0.39, 0.63)), V((0, 0.365, 0.685)),
        V((0, 0.33, 0.705))]


def catmull(pts, n):
    """Smooth curve through pts (Catmull-Rom), n samples per span."""
    out = []
    P_ = [pts[0] * 2 - pts[1]] + list(pts) + [pts[-1] * 2 - pts[-2]]
    for i in range(1, len(P_) - 2):
        p0, p1, p2, p3 = P_[i - 1], P_[i], P_[i + 1], P_[i + 2]
        for j in range(n):
            t = j / n; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def body_metaballs():
    mb = bpy.data.metaballs.new("Caramelo_MB")
    mb.resolution = 0.012
    mb.render_resolution = 0.008
    mb.threshold = 0.6
    o = link(bpy.data.objects.new("Caramelo_MB", mb))
    # torso: deep chest, tucked waist, rounded rump
    ellipsoid(mb, P["chest"], (0.125, 0.155, 0.150), r=1.0, stiff=2.2)
    ellipsoid(mb, P["chest"] + V((0, -0.06, 0.03)), (0.10, 0.09, 0.11), r=1.0)        # front of the chest / brisket
    ellipsoid(mb, P["waist"], (0.105, 0.15, 0.105), r=1.0)
    ellipsoid(mb, P["hips"], (0.115, 0.115, 0.12), r=1.0, stiff=2.2)
    ellipsoid(mb, P["waist"] + V((0, 0, 0.04)), (0.09, 0.20, 0.07), r=1.0)          # topline
    # neck and head: rounded skull, clear stop, a medium muzzle (a mutt, not a pug)
    capsule(mb, P["neck0"], P["neck1"], 0.074)
    ellipsoid(mb, (P["neck0"] + P["neck1"]) / 2 + V((0, 0.02, -0.02)), (0.075, 0.07, 0.08), r=1.0)   # scruff
    ball(mb, P["head"], 0.098, stiff=2.4)
    ellipsoid(mb, P["head"] + V((0, 0.025, 0.035)), (0.085, 0.085, 0.065), r=1.0)     # skull dome
    ellipsoid(mb, P["head"] + V((0, 0.02, -0.05)), (0.085, 0.075, 0.055), r=1.0)      # throat
    for s in (-1, 1):
        ellipsoid(mb, V((s * 0.050, -0.455, 0.633)), (0.040, 0.048, 0.036), r=1.0)  # cheeks
        ellipsoid(mb, V((s * 0.036, -0.462, 0.700)), (0.030, 0.032, 0.020), r=1.0)  # brow ridges
    ellipsoid(mb, P["snout"], (0.045, 0.100, 0.042), r=1.0, stiff=2.0)               # muzzle (upper)
    ellipsoid(mb, P["snout"] + V((0, -0.050, 0.010)), (0.034, 0.045, 0.032), r=1.0)  # nose bridge tip
    # legs
    for s in (-1, 1):
        m = V((s, 1, 1))
        sh, el, wr, fp = (P[k] * m for k in ("shoulder", "elbow", "wrist", "fpaw"))
        hp, kn, hk, hpw = (P[k] * m for k in ("hip", "knee", "hock", "hpaw"))
        ellipsoid(mb, sh + V((0, 0.01, -0.03)), (0.055, 0.075, 0.095), r=1.0)        # shoulder blade + upper arm
        capsule(mb, sh + V((0, 0, -0.04)), el, 0.046)
        capsule(mb, el, wr, 0.032)
        capsule(mb, wr, fp + V((0, -0.01, 0.012)), 0.028)
        ellipsoid(mb, fp + V((0, -0.012, 0.0)), (0.036, 0.048, 0.024), r=1.0)       # front paw
        ellipsoid(mb, hp + V((0, -0.01, -0.06)), (0.062, 0.085, 0.11), r=1.0)       # thigh
        capsule(mb, kn, hk, 0.034)
        capsule(mb, hk, hpw + V((0, -0.005, 0.012)), 0.027)
        ellipsoid(mb, hpw + V((0, -0.014, 0.0)), (0.035, 0.050, 0.024), r=1.0)      # hind paw
    # tail: a thick base curling up over the back
    pts = catmull(TAIL, 6)
    for i in range(len(pts) - 1):
        t = i / (len(pts) - 2)
        r = 0.036 * (1 - t) + 0.015 * t
        capsule(mb, pts[i], pts[i + 1], r, stiff=2.0)
    return o


def to_mesh(mb_obj, name):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mb_obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    me.name = name
    o = link(bpy.data.objects.new(name, me))
    bpy.data.objects.remove(mb_obj, do_unlink=True)
    return o


def remesh_quads(o, voxel=0.0055, faces=9000):
    ctx_obj(o)
    o.data.remesh_voxel_size = voxel
    o.data.remesh_voxel_adaptivity = 0
    o.data.use_remesh_fix_poles = True
    o.data.use_remesh_preserve_volume = True
    bpy.ops.object.voxel_remesh()
    # gentle smooth, then relay as quads
    m = o.modifiers.new("smooth", 'CORRECTIVE_SMOOTH'); m.iterations = 6; m.smooth_type = 'LENGTH_WEIGHTED'
    m.use_only_smooth = True
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.quadriflow_remesh(target_faces=faces, use_preserve_sharp=False, use_mesh_symmetry=True,
                                     use_preserve_boundary=False, smooth_normals=False, mode='FACES', seed=7)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# ------------------------------------------------------------------------------------------------ separate parts
def ear_mesh(side):
    """Semi-pricked mutt ear: a rounded triangle, cupped, the soft tip tipping forward/outward."""
    bm = bmesh.new()
    # outline in ear space (u across, v up), then a grid filled inside
    rows, cols = 9, 7
    verts = []
    for j in range(rows):
        t = j / (rows - 1)
        w = 0.047 * (1 - t) ** 0.80 + 0.005            # half width shrinking to the tip
        row = []
        for i in range(cols):
            u = (i / (cols - 1) - 0.5) * 2 * w
            v = t * 0.115
            cup = -0.010 * (1 - (u / max(w, 1e-4)) ** 2) * (1 - t * 0.6)   # hollow in the middle
            row.append(bm.verts.new((u, cup, v)))
        verts.append(row)
    for j in range(rows - 1):
        for i in range(cols - 1):
            bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
    me = bpy.data.meshes.new("Ear_" + side)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new("Caramelo_Ear_" + side, me))
    sol = o.modifiers.new("solid", 'SOLIDIFY'); sol.thickness = 0.015; sol.offset = 1.0
    sub = o.modifiers.new("sub", 'SUBSURF'); sub.levels = 1; sub.render_levels = 1
    ctx_obj(o)
    bpy.ops.object.modifier_apply(modifier="solid"); bpy.ops.object.modifier_apply(modifier="sub")
    # the inner shell (facing forward, -Y) gets a vertex group: the paint pass makes it pink, the back stays coat
    o.data.update()
    inner = [v.index for v in o.data.vertices if v.normal.y < -0.25]
    vg = o.vertex_groups.new(name="ear_inner"); vg.add(inner, 1.0, 'REPLACE')
    # tip folds forward a little (soft ear)
    for v in o.data.vertices:
        h = v.co.z / 0.115
        if h > 0.58:
            k = (h - 0.58) / 0.42
            ang = k * k * 0.7
            v.co.y -= math.sin(ang) * (v.co.z - 0.067)
            v.co.z = 0.067 + math.cos(ang) * (v.co.z - 0.067)
    s = 1 if side == "L" else -1
    # lean outward (+X for the left ear), turned a little to the side, tilted back
    o.rotation_euler = Euler((math.radians(-8), math.radians(s * 30), math.radians(s * -22)))
    o.location = P["ear"] * V((s, 1, 1))
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def jaw_mesh():
    """Lower jaw: a separate rounded wedge under the muzzle, hinged at P['jaw'] (mouth interior painted pink)."""
    mb = bpy.data.metaballs.new("Jaw_MB"); mb.resolution = 0.006; mb.threshold = 0.6
    o = link(bpy.data.objects.new("Jaw_MB", mb))
    ellipsoid(mb, V((0, -0.505, 0.594)), (0.034, 0.070, 0.019), r=1.0)
    ellipsoid(mb, V((0, -0.46, 0.596)), (0.042, 0.05, 0.024), r=1.0)
    me = to_mesh(o, "Caramelo_Jaw")
    remesh_quads(me, voxel=0.003, faces=900)
    return me


def tongue_mesh():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)
    for v in bm.verts:
        v.co = V((v.co.x * 0.026, v.co.y * 0.052, v.co.z * 0.007))
        v.co.z -= 0.004 * (v.co.y / 0.052) ** 2 * 3
    me = bpy.data.meshes.new("Tongue"); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new("Caramelo_Tongue", me))
    o.location = V((0, -0.505, 0.604))
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def eye_meshes():
    out = []
    for s, side in ((1, "L"), (-1, "R")):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=14, radius=0.0205)
        me = bpy.data.meshes.new("Eye_" + side); bm.to_mesh(me); bm.free()
        o = link(bpy.data.objects.new("Caramelo_Eye_" + side, me))
        o.location = P["eye"] * V((s, 1, 1))
        for p in o.data.polygons:
            p.use_smooth = True
        out.append(o)
    return out


def lid_meshes():
    """Upper eyelids: fur-coloured caps just outside the eyeball, rotated down by the Lid bones to close."""
    out = []
    for s, side in ((1, "L"), (-1, "R")):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=14, radius=0.0228)
        # keep the upper back half only (a cap that sits above the eye; rotating it forward-down closes the eye)
        dead = [v for v in bm.verts if v.co.z < 0.004 and v.co.y < 0.008]
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.002 or (v.co.y < -0.004 and v.co.z < 0.010)],
                         context='VERTS')
        me = bpy.data.meshes.new("Lid_" + side); bm.to_mesh(me); bm.free()
        o = link(bpy.data.objects.new("Caramelo_Lid_" + side, me))
        o.location = P["eye"] * V((s, 1, 1))
        sol = o.modifiers.new("solid", 'SOLIDIFY'); sol.thickness = 0.002; sol.offset = 1
        ctx_obj(o); bpy.ops.object.modifier_apply(modifier="solid")
        # open pose: the cap is rolled up and back into the brow (the Lid bone rolls it down over the eye)
        R = Matrix.Rotation(math.radians(-62), 4, 'X')
        for v in o.data.vertices:
            v.co = R @ v.co
        for p in o.data.polygons:
            p.use_smooth = True
        out.append(o)
    return out


def nose_mesh():
    """Wet nose: a rounded wedge with two nostrils, its own part so it reads glossy black."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        z2 = z * (1.0 - 0.25 * max(0, -z))            # flatter bottom
        v.co = V((x * 0.027 * (1 - 0.18 * z), y * 0.020, z2 * 0.019))
    me = bpy.data.meshes.new("Nose"); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new("Caramelo_Nose", me))
    o.location = P["nose"] + V((0, 0.004, 0.0))
    sub = o.modifiers.new("sub", 'SUBSURF'); sub.levels = 1
    ctx_obj(o); bpy.ops.object.modifier_apply(modifier="sub")
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def _bvh(o):
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())


def _cast(bvh, target, d, back=0.4):
    d = V(d).normalized()
    hit, n, i, dist = bvh.ray_cast(V(target) + d * back, -d)
    return hit, n


def _shift(o, delta):
    for v in o.data.vertices:
        v.co += delta


def place_parts(parts):
    """Sits the eyes, lids, nose, jaw, tongue and ears on the sculpted skin (ray casts), so edits to the head
    proportions never bury or float them."""
    body = parts["body"]; bvh = _bvh(body)
    for s, side in ((1, "L"), (-1, "R")):
        hit, n = _cast(bvh, (s * 0.040, -0.478, 0.688), (s * 0.55, -0.80, 0.22))
        c = hit - n * 0.0125
        for key in ("eye" + side, "lid" + side):
            parts[key].location = c
        hit, n = _cast(bvh, (s * 0.064, -0.392, 0.70), (s * 0.45, 0.0, 1.0))
        parts["ear" + side].location = hit - n * 0.016
    hit, n = _cast(bvh, (0, -0.58, 0.642), (0, -1, 0.05))
    parts["nose"].location = hit + V((0, 0.010, 0.002))
    nose_y = hit.y
    hit, n = _cast(bvh, (0, -0.525, 0.62), (0, 0, -1))
    jaw = parts["jaw"]
    zs = [v.co.z for v in jaw.data.vertices]; ys = [v.co.y for v in jaw.data.vertices]
    _shift(jaw, V((0, (nose_y + 0.034) - min(ys), (hit.z + 0.010) - max(zs))))
    zt = max(v.co.z for v in jaw.data.vertices)
    parts["tongue"].location = V((0, nose_y + 0.07, zt - 0.006))


def build_model():
    clear_scene()
    body = to_mesh(body_metaballs(), "Caramelo_Body")
    remesh_quads(body, voxel=0.0048, faces=10000)
    parts = dict(body=body, jaw=jaw_mesh(), tongue=tongue_mesh(), nose=nose_mesh())
    parts["eyeL"], parts["eyeR"] = eye_meshes()
    parts["lidL"], parts["lidR"] = lid_meshes()
    parts["earL"], parts["earR"] = ear_mesh("L"), ear_mesh("R")
    place_parts(parts)
    for o in parts.values():
        ctx_obj(o)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts.values())
    print("caramelo parts", {k: len(o.data.polygons) for k, o in parts.items()}, "tris", tris)
    return parts
