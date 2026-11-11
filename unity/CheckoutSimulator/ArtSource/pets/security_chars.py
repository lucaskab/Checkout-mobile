"""Thief (ladrão) and security guard (segurança) for the shoplifting feature (Lucas 08/11/2026).

Both are the game's own customers on the shared 14-bone customer skeleton (character space: 2.4 m tall, facing -Y,
the game scales them to 0.72), so the market's Walking / Idle / GetFromShelf clips keep working on them:
  * Thief  = Customer_02 (the bearded young man) in a charcoal hoodie with the hood up, round dark sunglasses and a
             cross-body bag where the stolen goods go.
  * Guard  = Customer_09 (the bearded man) in a navy uniform shirt (gold badge, shoulder boards, arm patch), a navy
             cap with a gold emblem, and a black duty belt with a radio and a flashlight.
Clothes are shells grown from the body itself (same vertices, so they inherit the body's skin weights and deform
exactly like it), smoothed into fabric, pushed safely outside the body and given hems; caps / hoods are fitted with
a shrink-wrap to the head. Every garment gets its own painted texture (baked from procedural fabric shaders with
seams, ribbing, stitching and soft occlusion). No written words anywhere (pictograms only).

    exec(open(".../pets/security_chars.py").read())
    thief = build_thief(); guard = build_guard()
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

UNITY = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator"
CHARS = os.path.join(UNITY, "Assets/Art/Characters/Meshy")
OUT = os.path.join(UNITY, "ArtSource/pets")
TEXDIR = os.path.join(OUT, "textures")
os.makedirs(TEXDIR, exist_ok=True)
V = Vector
PNG = {"Customer_02": "Customer_Plaid", "Customer_03": "Customer_Elder", "Customer_04": "Customer_Jacket"}


def lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def link(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


def ctx_obj(o):
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


# ------------------------------------------------------------------------------------------------ characters
def load_character(base, tag):
    """Imports a customer: keeps the armature + body (no basket, no clips), paints its albedo. -> (rig, body)"""
    before = set(bpy.data.objects); acts = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CHARS, base + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == 'ARMATURE')
    body = next(o for o in new if o.type == 'MESH' and o.name.endswith("_Body"))
    for o in new:
        if o is not rig and o is not body:
            bpy.data.objects.remove(o, do_unlink=True)
    for a in list(bpy.data.actions):
        if a not in acts:
            bpy.data.actions.remove(a)
    rig.animation_data_clear()
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    rig.name = tag + "_Rig"; rig.data.name = tag + "_Rig"
    body.name = tag + "_Body"; body.data.name = tag + "_Body"
    rig.location = (0, 0, 0)
    png = os.path.join(CHARS, PNG.get(base, base) + ".png")
    m = bpy.data.materials.new(tag + "_BodyMat"); m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(png, check_existing=True)
    b = m.node_tree.nodes["Principled BSDF"]
    m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.7
    body.data.materials.clear(); body.data.materials.append(m)
    return rig, body


class BodyInfo:
    def __init__(self, body):
        me = body.data; n = len(me.vertices)
        self.co = np.empty(n * 3); me.vertices.foreach_get("co", self.co); self.co = self.co.reshape(n, 3)
        self.no = np.empty(n * 3); me.vertices.foreach_get("normal", self.no); self.no = self.no.reshape(n, 3)
        self.names = [g.name for g in body.vertex_groups]
        self.W = np.zeros((n, len(self.names)))
        for v in me.vertices:
            for g in v.groups:
                self.W[v.index, g.group] = g.weight
        self.dom = np.array(self.names)[self.W.argmax(1)]
        self.bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
        self.body = body

    def w(self, name):
        return self.W[:, self.names.index(name)] if name in self.names else np.zeros(len(self.co))

    def head_box(self):
        c = self.co[self.dom == "Head"]
        return c.min(0), c.max(0)


# ------------------------------------------------------------------------------------------------ shells
_ENV = {}


def envelope(info, voxel=0.011):
    """One clean, single-layer skin around the whole body (the scanned customers have overlapping cloth layers:
    an open shirt over a tee...). Garments are grown from this envelope, never from the raw layers."""
    key = info.body.name
    if key in _ENV and _ENV[key].name in bpy.data.objects:
        return _ENV[key]
    me = info.body.data.copy(); me.name = key + "_Env"
    o = link(bpy.data.objects.new(key + "_Env", me))
    for m in list(o.modifiers):
        o.modifiers.remove(m)
    ctx_obj(o)
    me.remesh_voxel_size = voxel; me.remesh_voxel_adaptivity = 0.0
    bpy.ops.object.voxel_remesh()
    sm = o.modifiers.new("relax", 'CORRECTIVE_SMOOTH'); sm.iterations = 4; sm.use_only_smooth = True
    bpy.ops.object.modifier_apply(modifier=sm.name)
    o.hide_render = True; o.hide_viewport = True
    _ENV[key] = o
    return o


def shell_from_body(info, name, keep, offset=0.022, smooth=12, push=0.016, thickness=0.010, faces=3500):
    """Garment: the part of the envelope over the `keep` body vertices, grown outward, relaxed into cloth, kept
    outside the skin, decimated to a mobile budget, given thickness."""
    body = info.body
    env = envelope(info)
    kd = KDTree(len(info.co))
    for i, c in enumerate(info.co):
        kd.insert(c, i)
    kd.balance()
    me = env.data.copy(); me.name = name
    o = link(bpy.data.objects.new(name, me))
    o.parent = body.parent
    bm = bmesh.new(); bm.from_mesh(me)
    dead = []
    for v in bm.verts:
        co, j, d = kd.find(v.co)
        if not keep[j]:
            dead.append(v)
    bmesh.ops.delete(bm, geom=dead, context='VERTS')
    bm.to_mesh(me); bm.free()
    drop_small_islands(o, 60)
    for v in me.vertices:
        v.co = v.co + v.normal * offset
    if smooth:
        m = o.modifiers.new("relax", 'SMOOTH'); m.iterations = smooth; m.factor = 0.6
        ctx_obj(o); bpy.ops.object.modifier_apply(modifier=m.name)
    if faces and len(me.polygons) > faces:
        d = o.modifiers.new("budget", 'DECIMATE'); d.ratio = faces / len(me.polygons)
        ctx_obj(o); bpy.ops.object.modifier_apply(modifier=d.name)
    for v in me.vertices:
        loc, n, i, dd = info.bvh.find_nearest(v.co)
        if loc is None:
            continue
        if (v.co - loc).dot(n) < push:
            v.co = loc + n * push
    if thickness:
        s = o.modifiers.new("cloth", 'SOLIDIFY'); s.thickness = thickness; s.offset = -1; s.use_rim = True
        s.use_even_offset = False; s.use_quality_normals = True; s.thickness_clamp = 0.5
        ctx_obj(o); bpy.ops.object.modifier_apply(modifier=s.name)
    for p in me.polygons:
        p.use_smooth = True
    drop_small_islands(o, 40)
    arm = o.modifiers.new("Armature", 'ARMATURE'); arm.object = body.parent
    o["keep_mask"] = 1
    SHELL_KEEP[name] = keep.copy()
    return o


SHELL_KEEP = {}


def drop_small_islands(o, min_verts):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    seen = set(); dead = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]; comp = []
        seen.add(v.index)
        while stack:
            a = stack.pop(); comp.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); stack.append(b)
        if len(comp) < min_verts:
            dead += comp
    if dead:
        bmesh.ops.delete(bm, geom=dead, context='VERTS')
    bm.to_mesh(o.data); bm.free()


def hide_under(body, keep, erode=2):
    """Deletes the body faces fully covered by a garment (keep mask eroded by `erode` edge rings, so the skin still
    runs a little under the garment's edges): no poke-through, fewer triangles."""
    me = body.data
    k = keep.copy()
    adj = [[] for _ in range(len(me.vertices))]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b); adj[b].append(a)
    for _ in range(erode):
        nk = k.copy()
        for i in np.nonzero(k)[0]:
            if any(not k[j] for j in adj[i]):
                nk[i] = False
        k = nk
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    dead = [f for f in bm.faces if all(k[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(me); bm.free()
    return len(dead)


def torso_bvh(info, exclude=("UpperArm_L", "UpperArm_R", "Forearm_L", "Forearm_R", "Hand_L", "Hand_R")):
    """BVH of the body without the arms (belts and straps must wrap the torso, not the hanging arms)."""
    me = info.body.data
    bad = np.isin(info.dom, list(exclude))
    verts = [v.co.copy() for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons if not any(bad[i] for i in p.vertices)]
    return BVHTree.FromPolygons(verts, polys)


def fit_cap(info, name, center, radii, cut, offset=0.02, smooth=6, segs=(48, 24)):
    """An ellipsoid around the head, cut by `cut(co) -> bool` (True = remove), shrink-wrapped OUTSIDE the head
    (+offset) so it follows the skull/hair, then relaxed."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
    for v in bm.verts:
        v.co = V((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2])) + V(center)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if cut(v.co)], context='VERTS')
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.parent = info.body.parent
    sw = o.modifiers.new("fit", 'SHRINKWRAP'); sw.target = info.body; sw.wrap_method = 'NEAREST_SURFACEPOINT'
    sw.wrap_mode = 'OUTSIDE_SURFACE'; sw.offset = offset
    ctx_obj(o); bpy.ops.object.modifier_apply(modifier="fit")
    if smooth:
        m = o.modifiers.new("relax", 'SMOOTH'); m.iterations = smooth; m.factor = 0.5
        bpy.ops.object.modifier_apply(modifier=m.name)
    for p in me.polygons:
        p.use_smooth = True
    return o


def weights_rigid(o, rig, bone):
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    vg = o.vertex_groups.new(name=bone); vg.add(range(len(o.data.vertices)), 1.0, 'REPLACE')
    m = o.modifiers.get("Armature") or o.modifiers.new("Armature", 'ARMATURE'); m.object = rig
    o.parent = rig


def weights_from_body(o, info, rig, max_dist=0.25):
    """Each vertex takes the skin weights of the nearest body vertex (smooth: 6 nearest, inverse distance)."""
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    kd = KDTree(len(info.co))
    for i, c in enumerate(info.co):
        kd.insert(c, i)
    kd.balance()
    groups = [o.vertex_groups.new(name=n) for n in info.names]
    for v in o.data.vertices:
        hits = kd.find_n(v.co, 6)
        acc = np.zeros(len(info.names)); tot = 0
        for co, i, d in hits:
            w = 1.0 / (d + 0.01); acc += info.W[i] * w; tot += w
        acc /= max(tot, 1e-9)
        for gi, wv in enumerate(acc):
            if wv > 0.01:
                groups[gi].add([v.index], float(wv), 'REPLACE')
    m = o.modifiers.get("Armature") or o.modifiers.new("Armature", 'ARMATURE'); m.object = rig
    o.parent = rig


# ------------------------------------------------------------------------------------------------ texture bake
def unwrap(o, angle=66, margin=0.006):
    ctx_obj(o)
    if not o.data.uv_layers:
        o.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0)
    bpy.ops.object.mode_set(mode='OBJECT')


def fabric_nodes(mat, base, weave_scale=420, weave_amt=0.08, mottle=0.10, bands=(), ao=True, extra=None):
    """Emission = painted fabric: base colour x weave x mottling x baked AO; `bands` = list of
    (axis 'z'|'y'|'x', lo, hi, colour, rib) stripes in object space (hems, cuffs, belts, piping); `extra(nt, col_socket)`
    can add more layers and must return the new colour socket."""
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); emi = N("ShaderNodeEmission")
    tc = N("ShaderNodeTexCoord")
    col = N("ShaderNodeRGB"); col.outputs[0].default_value = (*lin(base), 1)
    cur = col.outputs[0]
    for axis, lo, hi, bc, rib in bands:
        sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs["Vector"])
        a = sep.outputs[axis.upper()]
        g1 = N("ShaderNodeMath"); g1.operation = 'GREATER_THAN'; L(a, g1.inputs[0]); g1.inputs[1].default_value = lo
        g2 = N("ShaderNodeMath"); g2.operation = 'LESS_THAN'; L(a, g2.inputs[0]); g2.inputs[1].default_value = hi
        m = N("ShaderNodeMath"); m.operation = 'MULTIPLY'; L(g1.outputs[0], m.inputs[0]); L(g2.outputs[0], m.inputs[1])
        bcn = N("ShaderNodeRGB"); bcn.outputs[0].default_value = (*lin(bc), 1)
        bcol = bcn.outputs[0]
        if rib:
            # vertical ribbing: stripes around the band (angle around the body's centre)
            wave = N("ShaderNodeTexWave"); wave.wave_type = 'BANDS'; wave.bands_direction = 'X'
            wave.inputs["Scale"].default_value = rib; wave.inputs["Distortion"].default_value = 0
            L(tc.outputs["Object"], wave.inputs["Vector"])
            rr = N("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.82; rr.inputs["To Max"].default_value = 1.06
            L(wave.outputs["Fac"], rr.inputs["Value"])
            mm = N("ShaderNodeMix"); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs["Factor"].default_value = 1
            L(bcol, mm.inputs["A"]); L(rr.outputs["Result"], mm.inputs["B"]); bcol = mm.outputs["Result"]
        mx = N("ShaderNodeMix"); mx.data_type = 'RGBA'
        L(m.outputs[0], mx.inputs["Factor"]); L(cur, mx.inputs["A"]); L(bcol, mx.inputs["B"]); cur = mx.outputs["Result"]
    if extra:
        cur = extra(nt, cur, tc)
    # weave + mottle
    wv = N("ShaderNodeTexNoise"); wv.inputs["Scale"].default_value = weave_scale; wv.inputs["Detail"].default_value = 2
    L(tc.outputs["Object"], wv.inputs["Vector"])
    wr = N("ShaderNodeMapRange"); wr.inputs["To Min"].default_value = 1 - weave_amt; wr.inputs["To Max"].default_value = 1 + weave_amt
    L(wv.outputs["Fac"], wr.inputs["Value"])
    mo = N("ShaderNodeTexNoise"); mo.inputs["Scale"].default_value = 9; mo.inputs["Detail"].default_value = 3
    L(tc.outputs["Object"], mo.inputs["Vector"])
    mr = N("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 1 - mottle; mr.inputs["To Max"].default_value = 1 + mottle
    L(mo.outputs["Fac"], mr.inputs["Value"])
    f = N("ShaderNodeMath"); f.operation = 'MULTIPLY'; L(wr.outputs["Result"], f.inputs[0]); L(mr.outputs["Result"], f.inputs[1])
    if ao:
        aon = N("ShaderNodeAmbientOcclusion"); aon.samples = 16; aon.inputs["Distance"].default_value = 0.12
        ar = N("ShaderNodeMapRange"); ar.inputs["To Min"].default_value = 0.58; ar.inputs["To Max"].default_value = 1.0
        L(aon.outputs["AO"], ar.inputs["Value"])
        f2 = N("ShaderNodeMath"); f2.operation = 'MULTIPLY'; L(f.outputs[0], f2.inputs[0]); L(ar.outputs["Result"], f2.inputs[1])
        f = f2
    mm = N("ShaderNodeMix"); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs["Factor"].default_value = 1
    L(cur, mm.inputs["A"]); L(f.outputs[0], mm.inputs["B"])
    L(mm.outputs["Result"], emi.inputs["Color"]); L(emi.outputs["Emission"], out.inputs["Surface"])
    return nt


def bake_to_texture(o, mat, tex_name, size=1024, samples=16, hide=()):
    """Bake the emission of `mat` on `o` (rest pose) into textures/<tex_name>.png and swap to a game material."""
    o.data.materials.clear(); o.data.materials.append(mat)
    img = bpy.data.images.get(tex_name) or bpy.data.images.new(tex_name, size, size, alpha=False)
    if tuple(img.size) != (size, size):
        img.scale(size, size)
    nt = mat.node_tree
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img; nt.nodes.active = tn
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'GPU'; sc.cycles.samples = samples
    sc.render.bake.margin = 6
    rig = o.parent
    if rig and rig.type == 'ARMATURE':
        rig.data.pose_position = 'REST'
    ctx_obj(o)
    bpy.ops.object.bake(type='EMIT')
    if rig and rig.type == 'ARMATURE':
        rig.data.pose_position = 'POSE'
    path = os.path.join(TEXDIR, tex_name + ".png")
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    gm = bpy.data.materials.get(tex_name + "_Mat") or bpy.data.materials.new(tex_name + "_Mat")
    gm.use_nodes = True; g = gm.node_tree; g.nodes.clear()
    out = g.nodes.new("ShaderNodeOutputMaterial"); b = g.nodes.new("ShaderNodeBsdfPrincipled")
    t = g.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True); t.image.reload()
    g.links.new(t.outputs["Color"], b.inputs["Base Color"]); g.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    b.inputs["Roughness"].default_value = 0.8; b.inputs["Specular IOR Level"].default_value = 0.25
    o.data.materials.clear(); o.data.materials.append(gm)
    return path


def simple_mat(name, color, rough=0.5, metal=0.0, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(color), 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(color), 1); b.inputs["Emission Strength"].default_value = emit
    return m


# ------------------------------------------------------------------------------------------------ small props
def rounded_box(name, size, bevel=0.01, segs=3):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = V((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    b = o.modifiers.new("bevel", 'BEVEL'); b.width = bevel; b.segments = segs; b.limit_method = 'NONE'
    ctx_obj(o); bpy.ops.object.modifier_apply(modifier="bevel")
    for p in me.polygons:
        p.use_smooth = True
    return o


def tube(name, pts, radius, sides=10, flat=1.0, up=V((0, 0, 1))):
    """A tube (or a flat strap when flat < 1) through points."""
    bm = bmesh.new(); rings = []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
        t = (b - a).normalized()
        n1 = t.cross(up)
        if n1.length < 1e-4:
            n1 = t.cross(V((1, 0, 0)))
        n1.normalize(); n2 = t.cross(n1).normalized()
        ring = []
        for k in range(sides):
            ang = math.tau * k / sides
            ring.append(bm.verts.new(p + n1 * math.cos(ang) * radius + n2 * math.sin(ang) * radius * flat))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    for p in me.polygons:
        p.use_smooth = True
    return o


def join(objs, name):
    ctx_obj(objs[0])
    for o in objs[1:]:
        o.select_set(True)
    bpy.ops.object.join()
    objs[0].name = name; objs[0].data.name = name
    return objs[0]


def surface_path(info, pts, lift, n=24):
    """Points along a polyline, projected onto the body surface and lifted off it (straps, belts)."""
    out = []
    for i in range(len(pts) - 1):
        for k in range(n):
            p = pts[i].lerp(pts[i + 1], k / n)
            loc, nrm, idx, d = info.bvh.find_nearest(p)
            out.append(loc + nrm * lift)
    loc, nrm, idx, d = info.bvh.find_nearest(pts[-1]); out.append(loc + nrm * lift)
    return out


def ring_around(info, z, lift, n=36, cx=0.0, cy=0.0, bvh=None):
    """Closed silhouette ring of the body at height z (ray casts from outside inwards)."""
    bvh = bvh or info.bvh
    pts = []
    for k in range(n):
        a = math.tau * k / n
        d = V((math.cos(a), math.sin(a), 0))
        origin = V((cx, cy, z)) + d * 1.5
        loc, nrm, idx, dist = bvh.ray_cast(origin, -d)
        if loc is None:
            continue
        pts.append(loc + d * lift)
    return pts


def ring_mesh(name, pts, height, thick):
    bm = bmesh.new(); n = len(pts); rows = []
    c = sum(pts, V()) / n
    for dz in (-height / 2, height / 2):
        for out in (0, thick):
            row = []
            for p in pts:
                r = (V((p.x, p.y, 0)) - V((c.x, c.y, 0))).normalized()
                row.append(bm.verts.new(p + r * out + V((0, 0, dz))))
            rows.append(row)
    lo_in, lo_out, hi_in, hi_out = rows
    for k in range(n):
        j = (k + 1) % n
        bm.faces.new((lo_out[k], lo_out[j], hi_out[j], hi_out[k]))
        bm.faces.new((hi_in[k], hi_in[j], lo_in[j], lo_in[k]))
        bm.faces.new((hi_out[k], hi_out[j], hi_in[j], hi_in[k]))
        bm.faces.new((lo_in[k], lo_in[j], lo_out[j], lo_out[k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    b = o.modifiers.new("bevel", 'BEVEL'); b.width = min(height, thick) * 0.3; b.segments = 2
    ctx_obj(o); bpy.ops.object.modifier_apply(modifier="bevel")
    for p in me.polygons:
        p.use_smooth = True
    return o
