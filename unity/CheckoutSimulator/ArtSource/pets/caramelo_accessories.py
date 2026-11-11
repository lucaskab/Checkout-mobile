"""Caramelo's cosmetics (Lucas 08/11/2026) and the export to Unity.

  * Collar: a leather band around the neck (its colour is set by the game per collar), a gold bone-shaped tag.
  * Bandanas (3): a cloth triangle draped over the chest, knotted behind the neck: navy with gold dots, red plaid,
    cream with little flowers (textures/bandana_<id>.png).
  * PetBed: a round bolster bed in the market's navy with a cream cushion and gold piping.
  * PetBowls: two steel bowls on a wooden mat, kibble in one, water in the other.
Everything is skinned to Caramelo_Rig (collar/tag rigid on Neck, bandanas from the coat's weights) and exported with
the clips: Assets/Resources/CheckoutPets/Caramelo.fbx (+ PetBed.fbx, PetBowls.fbx and the PNGs).

    (open caramelo.blend)  exec(model, paint, rig, anim, accessories)  build_accessories(); export_all()
"""
import bpy, bmesh, math, os, shutil
import numpy as np
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

UNITY_RES = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/Assets/Resources/CheckoutPets"
TEX = os.path.join(HERE, "textures")
os.makedirs(TEX, exist_ok=True)


def _lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def flat_mat(name, color, rough=0.6, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*_lin(color), 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def neck_frame():
    rig = bpy.data.objects["Caramelo_Rig"]
    b = rig.data.bones["Neck"]
    h, t = b.head_local.copy(), b.tail_local.copy()
    return h, t, (t - h).normalized()


def dog_bvh():
    dog = bpy.data.objects["Caramelo"]
    rig = dog.parent
    rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    return dog, BVHTree.FromObject(dog, bpy.context.evaluated_depsgraph_get())


def collar():
    dog, bvh = dog_bvh()
    h, t, ax = neck_frame()
    c = h.lerp(t, 0.30)
    u = ax.orthogonal().normalized(); v = ax.cross(u).normalized()
    pts = []
    n = 40
    for k in range(n):
        a = math.tau * k / n
        d = u * math.cos(a) + v * math.sin(a)
        loc, nn, i, dist = bvh.ray_cast(c + d * 0.4, -d)
        pts.append((loc if loc is not None else c + d * 0.07) + d * 0.006)
    bm = bmesh.new(); rows = []
    for off in (-0.012, 0.012):
        for out in (0.0, 0.009):
            row = [bm.verts.new(p + ax * off + (p - c).normalized() * out) for p in pts]
            rows.append(row)
    lo_in, lo_out, hi_in, hi_out = rows
    for k in range(n):
        j = (k + 1) % n
        bm.faces.new((lo_out[k], lo_out[j], hi_out[j], hi_out[k])); bm.faces.new((hi_in[k], hi_in[j], lo_in[j], lo_in[k]))
        bm.faces.new((hi_out[k], hi_out[j], hi_in[j], hi_in[k])); bm.faces.new((lo_in[k], lo_in[j], lo_out[j], lo_out[k]))
    me = bpy.data.meshes.new("Caramelo_Collar"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Caramelo_Collar", me); bpy.context.scene.collection.objects.link(o)
    bv = o.modifiers.new("b", 'BEVEL'); bv.width = 0.003; bv.segments = 2
    ctx_obj(o); bpy.ops.object.modifier_apply(modifier="b")
    for p in me.polygons:
        p.use_smooth = True
    o.data.materials.append(flat_mat("Collar_Mat", (0.12, 0.18, 0.36), 0.45))
    # the tag: a gold bone shape hanging from a little ring at the lowest front point of the collar
    front = min(pts, key=lambda p: p.z + 0.5 * p.y)
    ring = bpy.data.meshes.new("Ring"); bmr = bmesh.new()
    bmesh.ops.create_circle(bmr, segments=16, radius=0.008); bmr.to_mesh(ring); bmr.free()
    r = bpy.data.objects.new("Caramelo_TagRing", ring); bpy.context.scene.collection.objects.link(r)
    r.location = front + Vector((0, -0.006, -0.008)); r.rotation_euler = (0, math.radians(90), 0)
    sk = r.modifiers.new("skin", 'SKIN'); ctx_obj(r)
    for sv in r.data.skin_vertices[0].data:
        sv.radius = (0.0018, 0.0018)
    bpy.ops.object.modifier_apply(modifier="skin")
    bone = bpy.data.metaballs.new("TagMB"); bone.resolution = 0.002; bone.threshold = 0.6
    mo = bpy.data.objects.new("TagMB", bone); bpy.context.scene.collection.objects.link(mo)
    for dx in (-0.013, 0.013):
        for dz in (-0.006, 0.006):
            e = bone.elements.new(type='BALL'); e.co = (dx, 0, dz); e.radius = 0.0105
    e = bone.elements.new(type='CAPSULE'); e.co = (0, 0, 0); e.radius = 0.010; e.size_x = 0.012
    me2 = bpy.data.meshes.new_from_object(mo.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(mo, do_unlink=True)
    tag = bpy.data.objects.new("Caramelo_Tag", me2); bpy.context.scene.collection.objects.link(tag)
    for vtx in me2.vertices:
        vtx.co.y *= 0.25
    tag.location = front + Vector((0, -0.010, -0.032))
    for p in me2.polygons:
        p.use_smooth = True
    gold = flat_mat("Tag_GoldMat", (0.92, 0.72, 0.30), 0.28, 0.9)
    tag.data.materials.append(gold); r.data.materials.append(gold)
    for x in (r, tag):
        ctx_obj(x); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    tag = join_objs([tag, r], "Caramelo_Tag")
    return o, tag


def join_objs(objs, name):
    ctx_obj(objs[0])
    for o in objs[1:]:
        o.select_set(True)
    bpy.ops.object.join(); objs[0].name = name; objs[0].data.name = name
    return objs[0]


def bandana(variant):
    """Cloth triangle over the chest: the coat's surface between the collar and the chest, grown out a little."""
    dog, bvh = dog_bvh()
    h, t, ax = neck_frame()
    c = h.lerp(t, 0.22)
    me = dog.data
    keep = []
    for v in me.vertices:
        if not any(dog.vertex_groups[g.group].name == "part_body" and g.weight > 0.5 for g in v.groups):
            continue
        p = v.co
        rel = p - c
        below = -rel.dot(ax)                      # distance down the neck axis from the collar
        front = -(p.y - c.y)                       # towards the chest
        if -0.015 < below < 0.23 and front > -0.045:
            # triangle: narrower further down
            width = 0.135 * (1 - below / 0.23) + 0.018
            if abs(p.x) < width:
                keep.append(v.index)
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    ks = set(keep)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in ks], context='VERTS')
    nm = bpy.data.meshes.new("Caramelo_Bandana_" + variant); bm.to_mesh(nm); bm.free()
    o = bpy.data.objects.new("Caramelo_Bandana_" + variant, nm); bpy.context.scene.collection.objects.link(o)
    for v in nm.vertices:
        v.co += v.normal * 0.013
    sm = o.modifiers.new("s", 'SMOOTH'); sm.iterations = 4; sm.factor = 0.5
    so = o.modifiers.new("t", 'SOLIDIFY'); so.thickness = 0.004; so.offset = 1
    ctx_obj(o); bpy.ops.object.modifier_apply(modifier="s"); bpy.ops.object.modifier_apply(modifier="t")
    for p in nm.polygons:
        p.use_smooth = True
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    for l in list(o.data.uv_layers):
        o.data.uv_layers.remove(l)
    o.data.uv_layers.new(name="UVMap")
    ctx_obj(o)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=0.25); bpy.ops.object.mode_set(mode='OBJECT')
    o.data.materials.append(bandana_material(variant))
    return o


def bandana_material(variant):
    """Painted pattern in object space, baked later into textures/bandana_<variant>.png."""
    m = bpy.data.materials.new("bandana_" + variant + "_Bake"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); emi = N("ShaderNodeEmission"); tc = N("ShaderNodeTexCoord")
    base = {"navy": (0.11, 0.17, 0.36), "plaid": (0.78, 0.16, 0.14), "flowers": (0.97, 0.92, 0.80)}[variant]
    col = N("ShaderNodeRGB"); col.outputs[0].default_value = (*_lin(base), 1); cur = col.outputs[0]
    if variant == "navy":                          # gold polka dots
        vo = N("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 70; vo.inputs["Randomness"].default_value = 0.0
        L(tc.outputs["Object"], vo.inputs["Vector"])
        dot = N("ShaderNodeMath"); dot.operation = 'LESS_THAN'; L(vo.outputs["Distance"], dot.inputs[0]); dot.inputs[1].default_value = 0.22
        g = N("ShaderNodeRGB"); g.outputs[0].default_value = (*_lin((0.95, 0.76, 0.32)), 1)
        mx = N("ShaderNodeMix"); mx.data_type = 'RGBA'; L(dot.outputs[0], mx.inputs["Factor"]); L(cur, mx.inputs["A"]); L(g.outputs[0], mx.inputs["B"]); cur = mx.outputs["Result"]
    elif variant == "plaid":                       # red tartan: dark bands both ways + thin cream lines
        sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs["Vector"])
        acc = None
        for axis in ("X", "Z"):
            w = N("ShaderNodeMath"); w.operation = 'PINGPONG'; L(sep.outputs[axis], w.inputs[0]); w.inputs[1].default_value = 0.012
            band = N("ShaderNodeMath"); band.operation = 'LESS_THAN'; L(w.outputs[0], band.inputs[0]); band.inputs[1].default_value = 0.005
            acc = band.outputs[0] if acc is None else acc
            dk = N("ShaderNodeMix"); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'
            L(band.outputs[0], dk.inputs["Factor"]); L(cur, dk.inputs["A"]); dk.inputs["B"].default_value = (0.35, 0.3, 0.3, 1)
            cur = dk.outputs["Result"]
            thin = N("ShaderNodeMath"); thin.operation = 'LESS_THAN'; L(w.outputs[0], thin.inputs[0]); thin.inputs[1].default_value = 0.0007
            cl = N("ShaderNodeMix"); cl.data_type = 'RGBA'; L(thin.outputs[0], cl.inputs["Factor"]); L(cur, cl.inputs["A"])
            cl.inputs["B"].default_value = (*_lin((0.97, 0.90, 0.75)), 1); cur = cl.outputs["Result"]
    else:                                          # small flowers: petals around a centre on a cream ground
        vo = N("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 45
        L(tc.outputs["Object"], vo.inputs["Vector"])
        petal = N("ShaderNodeMath"); petal.operation = 'LESS_THAN'; L(vo.outputs["Distance"], petal.inputs[0]); petal.inputs[1].default_value = 0.28
        center = N("ShaderNodeMath"); center.operation = 'LESS_THAN'; L(vo.outputs["Distance"], center.inputs[0]); center.inputs[1].default_value = 0.10
        ramp = N("ShaderNodeValToRGB"); L(vo.outputs["Color"], ramp.inputs["Fac"])
        ramp.color_ramp.elements[0].color = (*_lin((0.93, 0.42, 0.55)), 1); ramp.color_ramp.elements[1].color = (*_lin((0.25, 0.60, 0.85)), 1)
        e = ramp.color_ramp.elements.new(0.5); e.color = (*_lin((0.98, 0.70, 0.25)), 1)
        mx = N("ShaderNodeMix"); mx.data_type = 'RGBA'; L(petal.outputs[0], mx.inputs["Factor"]); L(cur, mx.inputs["A"]); L(ramp.outputs["Color"], mx.inputs["B"])
        y = N("ShaderNodeMix"); y.data_type = 'RGBA'; L(center.outputs[0], y.inputs["Factor"]); L(mx.outputs["Result"], y.inputs["A"])
        y.inputs["B"].default_value = (*_lin((0.99, 0.85, 0.30)), 1); cur = y.outputs["Result"]
    # cloth weave + soft occlusion
    wv = N("ShaderNodeTexNoise"); wv.inputs["Scale"].default_value = 900; L(tc.outputs["Object"], wv.inputs["Vector"])
    wr = N("ShaderNodeMapRange"); wr.inputs["To Min"].default_value = 0.93; wr.inputs["To Max"].default_value = 1.05; L(wv.outputs["Fac"], wr.inputs["Value"])
    ao = N("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.03
    ar = N("ShaderNodeMapRange"); ar.inputs["To Min"].default_value = 0.7; L(ao.outputs["AO"], ar.inputs["Value"])
    f = N("ShaderNodeMath"); f.operation = 'MULTIPLY'; L(wr.outputs["Result"], f.inputs[0]); L(ar.outputs["Result"], f.inputs[1])
    mm = N("ShaderNodeMix"); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs["Factor"].default_value = 1
    L(cur, mm.inputs["A"]); L(f.outputs[0], mm.inputs["B"]); L(mm.outputs["Result"], emi.inputs["Color"]); L(emi.outputs["Emission"], out.inputs["Surface"])
    return m


def bake_emit(o, name, size=512):
    img = bpy.data.images.get(name) or bpy.data.images.new(name, size, size, alpha=False)
    m = o.data.materials[0]; tn = m.node_tree.nodes.new("ShaderNodeTexImage"); tn.image = img; m.node_tree.nodes.active = tn
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'GPU'; sc.cycles.samples = 16; sc.render.bake.margin = 4
    ctx_obj(o); bpy.ops.object.bake(type='EMIT')
    path = os.path.join(TEX, name + ".png"); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    gm = bpy.data.materials.new(name); gm.use_nodes = True
    t = gm.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True)
    gm.node_tree.links.new(t.outputs["Color"], gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    o.data.materials.clear(); o.data.materials.append(gm)
    return path


def skin_to_dog(o, rigid=None):
    rig = bpy.data.objects["Caramelo_Rig"]; dog = bpy.data.objects["Caramelo"]
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    if rigid:
        vg = o.vertex_groups.new(name=rigid); vg.add(range(len(o.data.vertices)), 1.0, 'REPLACE')
    else:
        me = dog.data
        co = np.array([v.co[:] for v in me.vertices]); names = [g.name for g in dog.vertex_groups]
        deform = {b.name for b in rig.data.bones if b.use_deform}
        kd = KDTree(len(co))
        for i, c in enumerate(co):
            kd.insert(c, i)
        kd.balance()
        groups = {}
        for v in o.data.vertices:
            acc = {}
            hits = kd.find_n(v.co, 6)
            tot = 0
            for c, i, d in hits:
                w = 1 / (d + 0.005); tot += w
                for g in me.vertices[i].groups:
                    nm = names[g.group]
                    if nm in deform:
                        acc[nm] = acc.get(nm, 0) + g.weight * w
            for nm, wv in acc.items():
                if nm not in groups:
                    groups[nm] = o.vertex_groups.new(name=nm)
                groups[nm].add([v.index], wv / tot, 'REPLACE')
    m = o.modifiers.get("Armature") or o.modifiers.new("Armature", 'ARMATURE'); m.object = rig
    o.parent = rig


def pet_bed():
    """Round bolster bed (0.95 m): navy bolster with gold piping, cream cushion, little stitched tufts."""
    parts = []
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, segments=48, radius=0.40)
    me = bpy.data.meshes.new("BolsterPath"); bm.to_mesh(me); bm.free()
    ring = bpy.data.objects.new("PetBed_Bolster", me); bpy.context.scene.collection.objects.link(ring)
    sk = ring.modifiers.new("skin", 'SKIN'); ctx_obj(ring)
    for sv in ring.data.skin_vertices[0].data:
        sv.radius = (0.10, 0.12)
    ring.modifiers.new("sub", 'SUBSURF').levels = 2
    bpy.ops.object.modifier_apply(modifier="skin"); bpy.ops.object.modifier_apply(modifier="sub")
    # the front dips so the dog steps in
    for v in ring.data.vertices:
        a = math.atan2(v.co.y, v.co.x)
        dip = math.exp(-((a + math.pi / 2) / 0.6) ** 2)
        v.co.z *= 1 - 0.45 * dip
    ring.data.transform(Matrix.Translation((0, 0, 0.11)))          # (join keeps mesh data only)
    parts.append(ring)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=0.36, radius2=0.33, depth=0.07)
    me = bpy.data.meshes.new("Cushion"); bm.to_mesh(me); bm.free()
    cush = bpy.data.objects.new("PetBed_Cushion", me); bpy.context.scene.collection.objects.link(cush)
    bv = cush.modifiers.new("b", 'BEVEL'); bv.width = 0.03; bv.segments = 4
    ctx_obj(cush); bpy.ops.object.modifier_apply(modifier="b")
    cush.data.transform(Matrix.Translation((0, 0, 0.065)))
    parts.append(cush)
    # gold piping along the top of the bolster (following the dip at the front)
    bm = bmesh.new(); bmesh.ops.create_circle(bm, segments=96, radius=0.40)
    me = bpy.data.meshes.new("PipePath"); bm.to_mesh(me); bm.free()
    pipe = bpy.data.objects.new("PetBed_Piping", me); bpy.context.scene.collection.objects.link(pipe)
    sk = pipe.modifiers.new("skin", 'SKIN'); ctx_obj(pipe)
    for sv in pipe.data.skin_vertices[0].data:
        sv.radius = (0.014, 0.014)
    pipe.modifiers.new("sub", 'SUBSURF').levels = 1
    bpy.ops.object.modifier_apply(modifier="skin"); bpy.ops.object.modifier_apply(modifier="sub")
    for v in pipe.data.vertices:
        a = math.atan2(v.co.y, v.co.x)
        dip = math.exp(-((a + math.pi / 2) / 0.6) ** 2)
        v.co.z = (v.co.z + 0.118) * (1 - 0.45 * dip) + 0.11
    pipe.data.materials.append(flat_mat("PetBed_Gold", (0.93, 0.72, 0.28), 0.35, 0.6))
    parts.append(pipe)
    pipe_path = [Vector((math.cos(a) * 0.40, math.sin(a) * 0.40, 0.11 + 0.105)) for a in np.linspace(0, math.tau, 49)]
    for o in parts:
        for p in o.data.polygons:
            p.use_smooth = True
    ring.data.materials.append(flat_mat("PetBed_Navy", (0.12, 0.18, 0.38), 0.85))
    cush.data.materials.append(flat_mat("PetBed_Cream", (0.96, 0.90, 0.76), 0.9))
    bed = join_objs(parts, "PetBed")
    bed.location = (2.0, 0, 0)
    return bed


def pet_bowls():
    parts = []
    mat_steel = flat_mat("PetBowls_Steel", (0.80, 0.82, 0.84), 0.22, 0.95)
    for i, x in enumerate((-0.13, 0.13)):
        bm = bmesh.new()
        prof = [(0.05, 0.0), (0.085, 0.0), (0.11, 0.055), (0.105, 0.06), (0.08, 0.012), (0.0, 0.012)]
        verts = []
        segs = 40
        for k in range(segs):
            a = math.tau * k / segs
            verts.append([bm.verts.new((x + r * math.cos(a), r * math.sin(a), z)) for r, z in prof])
        for k in range(segs):
            j = (k + 1) % segs
            for q in range(len(prof) - 1):
                bm.faces.new((verts[k][q], verts[j][q], verts[j][q + 1], verts[k][q + 1]))
        me = bpy.data.meshes.new("Bowl%d" % i); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new("Bowl%d" % i, me); bpy.context.scene.collection.objects.link(o)
        for p in me.polygons:
            p.use_smooth = True
        o.data.materials.append(mat_steel); parts.append(o)
    # kibble in the left bowl, water in the right
    kib = bpy.data.metaballs.new("Kibble"); kib.resolution = 0.004
    ko = bpy.data.objects.new("KibbleMB", kib); bpy.context.scene.collection.objects.link(ko)
    rng = np.random.default_rng(3)
    for _ in range(60):
        r = 0.075 * math.sqrt(rng.random()); a = rng.random() * math.tau
        e = kib.elements.new(type='BALL'); e.co = (-0.13 + r * math.cos(a), r * math.sin(a), 0.03 + rng.random() * 0.02); e.radius = 0.016
    km = bpy.data.meshes.new_from_object(ko.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(ko, do_unlink=True)
    k = bpy.data.objects.new("Kibble", km); bpy.context.scene.collection.objects.link(k)
    k.data.materials.append(flat_mat("PetBowls_Kibble", (0.52, 0.30, 0.14), 0.8)); parts.append(k)
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, segments=40, radius=0.095)
    wm = bpy.data.meshes.new("Water"); bm.to_mesh(wm); bm.free()
    w = bpy.data.objects.new("Water", wm); bpy.context.scene.collection.objects.link(w); w.location = (0.13, 0, 0.045)
    w.data.materials.append(flat_mat("PetBowls_Water", (0.55, 0.80, 0.95), 0.05)); parts.append(w)
    mat = bpy.data.meshes.new("Mat"); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.52, v.co.y * 0.30, v.co.z * 0.012 + 0.006))
    bm.to_mesh(mat); bm.free()
    mo = bpy.data.objects.new("Mat", mat); bpy.context.scene.collection.objects.link(mo)
    bv = mo.modifiers.new("b", 'BEVEL'); bv.width = 0.03; bv.segments = 4; ctx_obj(mo); bpy.ops.object.modifier_apply(modifier="b")
    mo.data.materials.append(flat_mat("PetBowls_Wood", (0.62, 0.42, 0.24), 0.7)); parts.append(mo)
    for o in parts:
        ctx_obj(o); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bowls = join_objs(parts, "PetBowls")
    bowls.location = (2.0, 1.2, 0)
    return bowls


def build_accessories():
    for n in ("Caramelo_Collar", "Caramelo_Tag", "Caramelo_Bandana_navy", "Caramelo_Bandana_plaid", "Caramelo_Bandana_flowers", "PetBed", "PetBowls"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    col, tag = collar()
    skin_to_dog(col, "Neck"); skin_to_dog(tag, "Neck")
    bands = []
    for v in ("navy", "plaid", "flowers"):
        b = bandana(v); bake_emit(b, "bandana_" + v); skin_to_dog(b); bands.append(b)
    bed = pet_bed(); bowls = pet_bowls()
    bpy.data.objects["Caramelo_Rig"].data.pose_position = 'POSE'
    return col, tag, bands, bed, bowls


def export_all():
    os.makedirs(UNITY_RES, exist_ok=True)
    rig = bpy.data.objects["Caramelo_Rig"]
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    meshes = [o for o in bpy.data.objects if o.parent == rig and o.type == 'MESH']
    for x in bpy.context.selected_objects:
        x.select_set(False)
    rig.select_set(True)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=os.path.join(UNITY_RES, "Caramelo.fbx"), use_selection=True,
                             object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=True,
                             bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                             bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y', path_mode='STRIP')
    for name in ("PetBed", "PetBowls"):
        o = bpy.data.objects[name]
        loc = o.location.copy(); o.location = (0, 0, 0)
        for x in bpy.context.selected_objects:
            x.select_set(False)
        o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.export_scene.fbx(filepath=os.path.join(UNITY_RES, name + ".fbx"), use_selection=True, object_types={'MESH'},
                                 axis_forward='-Z', axis_up='Y', path_mode='STRIP', bake_anim=False)
        o.location = loc
    shutil.copy(os.path.join(HERE, "Caramelo_albedo.png"), os.path.join(UNITY_RES, "Caramelo_albedo.png"))
    for v in ("navy", "plaid", "flowers"):
        shutil.copy(os.path.join(TEX, "bandana_%s.png" % v), os.path.join(UNITY_RES, "bandana_%s.png" % v))
    print("exported", sorted(os.listdir(UNITY_RES)))
