"""The thief's beanie (Lucas 08/11: "cobre a cabeça com o gorro, para deixar claro que ele é o ladrão").

A snug knit beanie on Lucas's Tripo thief (model space of the GLB: 1.0 tall, faces -Y): a round dome over the skull,
its lower edge just above the eyebrows at the front, over the tops of the ears at the sides and down to the nape at
the back, a folded ribbed cuff, vertical rib knit on the body, very dark charcoal. The hair under it is tucked in
(those vertices are pulled inside the dome) so nothing pokes through. Texture: textures/Thief_Beanie.png (baked).

    exec(open(".../pets/thief_beanie.py").read()); beanie = build_beanie()
"""
import bpy, bmesh, math, os
from mathutils import Vector

BEANIE_TEX = os.path.join(ART, "NPCs/incoming/Thief_Beanie.png")
B = dict(cx=0.0, cy=0.002, cz=0.926, rx=0.080, ry=0.101, rz=0.091,
         z_front=0.938, z_back=0.850, ear_dip=0.012, y_front=-0.10, y_back=0.09, cuff=0.030, thick=0.0045,
         color=(0.12, 0.12, 0.14), rib=(0.09, 0.09, 0.105))


def edge_z(y, x=0.0):
    """Lower edge of the beanie: just over the brows in front, down to the nape at the back, dipping a little over
    the ears at the sides."""
    side = min(1.0, abs(x) / B["rx"]) ** 2
    t = (y - B["y_front"]) / (B["y_back"] - B["y_front"])
    return B["z_front"] + (B["z_back"] - B["z_front"]) * t - B["ear_dip"] * side * math.sin(math.pi * max(0.0, min(1.0, t))) ** 0.5


def _edge_linear(y):
    t = (y - B["y_front"]) / (B["y_back"] - B["y_front"])
    return B["z_front"] + (B["z_back"] - B["z_front"]) * t


def inside_scale(p):
    q = Vector(((p.x - B["cx"]) / B["rx"], (p.y - B["cy"]) / B["ry"], (p.z - B["cz"]) / B["rz"]))
    return q.length


def tuck_hair(o, margin=0.94):
    """Pull every head vertex that would poke out of the beanie back inside the dome."""
    c = Vector((B["cx"], B["cy"], B["cz"]))
    moved = 0
    for v in o.data.vertices:
        p = v.co
        if p.z < edge_z(p.y, p.x) - 0.002 or p.z < 0.85:
            continue
        k = inside_scale(p)
        if k > margin:
            v.co = c + (p - c) * (margin / k)
            moved += 1
    o.data.update()
    return moved


def vertex_colours(o):
    """Original Tripo base colour under each vertex (numpy n x 3)."""
    import numpy as np
    me = o.data; n = len(me.vertices)
    img = next(i for i in bpy.data.images if "basecolor" in i.name.lower())
    W, H = img.size; px = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(H, W, 4)
    li = np.empty(len(me.loops), int); me.loops.foreach_get("vertex_index", li)
    uv = np.empty(len(me.loops) * 2); me.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    vuv = np.zeros((n, 2)); vuv[li] = uv
    return px[np.clip((vuv[:, 1] * H).astype(int), 0, H - 1), np.clip((vuv[:, 0] * W).astype(int), 0, W - 1), :3]


def tuck_lock(o, x0=-0.085, x1=0.025, z0=0.912):
    """The hair lock that hung over the right eyebrow below the hem: its (non-skin) vertices sink behind the
    forehead, so only skin shows between the brow and the beanie."""
    import numpy as np, colorsys
    col = vertex_colours(o)
    c = Vector((B["cx"], B["cy"], B["cz"]))
    moved = 0
    for v in o.data.vertices:
        p = v.co
        if not (x0 < p.x < x1 and z0 < p.z < edge_z(p.y, p.x) + 0.004 and p.y < -0.065):
            continue
        h, s_, val = colorsys.rgb_to_hsv(*col[v.index])
        skinlike = 0.0 <= h < 0.12 and s_ > 0.30 and val > 0.55
        if skinlike:
            continue
        k = inside_scale(p)
        if k > 0.86:
            v.co = c + (p - c) * (0.86 / k)
            moved += 1
    o.data.update()
    return moved


def flatten_lock(o, box=(-0.080, 0.006, 0.922, 0.952), fit=(-0.075, 0.075, 0.905, 0.95)):
    """The hair lock over the right eyebrow: everything in the box that stands in front of the forehead is laid
    back onto it. The forehead is a smooth surface y = f(x, z) fitted (least squares, quadratic) to the skin
    around the lock, so the lock disappears into a clean brow-to-beanie forehead."""
    import numpy as np, colorsys
    col = vertex_colours(o)
    me = o.data; n = len(me.vertices)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(n, 3)
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in col])
    skin = (hsv[:, 0] < 0.12) & (hsv[:, 1] > 0.30) & (hsv[:, 2] > 0.55)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    inbox = (x > box[0]) & (x < box[1]) & (z > box[2]) & (z < box[3]) & (y < -0.06)
    region = (x > fit[0]) & (x < fit[1]) & (z > fit[2]) & (z < fit[3]) & (y < -0.06) & skin & ~inbox
    A = np.stack([np.ones(region.sum()), x[region], z[region], x[region] ** 2, z[region] ** 2, x[region] * z[region]], 1)
    coef, *_ = np.linalg.lstsq(A, y[region], rcond=None)
    def f(px, pz):
        return coef[0] + coef[1] * px + coef[2] * pz + coef[3] * px * px + coef[4] * pz * pz + coef[5] * px * pz
    moved = 0
    for i in np.nonzero(inbox)[0]:
        fy = f(x[i], z[i])
        if y[i] < fy + 0.001:
            me.vertices[i].co.y = fy + 0.006           # well behind the skin: no z-fighting with the forehead
            moved += 1
    me.update()
    print("forehead fit from", int(region.sum()), "skin verts; lock verts laid back:", moved)
    return moved


def beanie_mesh():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=1.0)
    for v in bm.verts:
        v.co = Vector((B["cx"] + v.co.x * B["rx"], B["cy"] + v.co.y * B["ry"], B["cz"] + v.co.z * B["rz"]))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < edge_z(v.co.y, v.co.x)], context='VERTS')
    # a clean hem: the open border is laid exactly on the edge curve (no stair steps from the sphere's rows)
    for v in bm.verts:
        if v.is_boundary:
            v.co.z = edge_z(v.co.y, v.co.x)
    # the cuff: the lower band stands a little proud, with a fold groove at its top
    c = Vector((B["cx"], B["cy"], B["cz"]))
    for v in bm.verts:
        dz = v.co.z - edge_z(v.co.y, v.co.x)
        radial = Vector((v.co.x - c.x, v.co.y - c.y, 0)).normalized()
        if dz < B["cuff"]:
            v.co += radial * B["thick"] * min(1.0, dz / 0.004 + 0.4)
        elif dz < B["cuff"] + 0.006:
            v.co -= radial * 0.0015 * math.sin(math.pi * (dz - B["cuff"]) / 0.006)
        # a slight slouch at the back of the crown
        if v.co.z > B["cz"] + 0.04 and v.co.y > c.y:
            v.co.y += 0.008 * (v.co.z - B["cz"] - 0.04) / (B["rz"] - 0.04) * (v.co.y - c.y) / B["ry"]
    me = bpy.data.meshes.new("Thief_Beanie"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Thief_Beanie", me); bpy.context.scene.collection.objects.link(o)
    a = me.attributes.new("above", 'FLOAT', 'POINT')         # height above the hem (cuff / fold in the texture)
    a.data.foreach_set("value", [v.co.z - edge_z(v.co.y, v.co.x) for v in me.vertices])
    s = o.modifiers.new("knit", 'SOLIDIFY'); s.thickness = 0.004; s.offset = -1; s.use_rim = True
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    bpy.ops.object.modifier_apply(modifier="knit")
    for p in me.polygons:
        p.use_smooth = True
    me.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.01)
    bpy.ops.object.mode_set(mode='OBJECT')
    return o


def beanie_material():
    m = bpy.data.materials.get("Thief_BeanieBake") or bpy.data.materials.new("Thief_BeanieBake")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); emi = N("ShaderNodeEmission"); tc = N("ShaderNodeTexCoord")
    sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs["Vector"])
    # angle around the head -> rib stripes (the same count all round), height above the edge -> cuff / body
    at = N("ShaderNodeMath"); at.operation = 'ARCTAN2'
    dy = math_node(nt, 'SUBTRACT', sep.outputs["Y"], B["cy"]); dx = math_node(nt, 'SUBTRACT', sep.outputs["X"], B["cx"])
    L(dy, at.inputs[0]); L(dx, at.inputs[1])
    ribs_body = math_node(nt, 'SINE', math_node(nt, 'MULTIPLY', at.outputs[0], 70.0))
    ribs_cuff = math_node(nt, 'SINE', math_node(nt, 'MULTIPLY', at.outputs[0], 110.0))
    # knit "V" stitches on the body: a zigzag along the height
    zz = math_node(nt, 'SINE', math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', sep.outputs["Z"], 900.0),
                                         math_node(nt, 'MULTIPLY', math_node(nt, 'ABSOLUTE', ribs_body), 2.2)))
    ab = N("ShaderNodeAttribute"); ab.attribute_name = "above"
    above = ab.outputs["Fac"]
    cuff = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, above, B["cuff"] - 0.002, B["cuff"] + 0.002))
    base = N("ShaderNodeRGB"); base.outputs[0].default_value = lin(B["color"])
    body_v = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', ribs_body, 0.10), math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', zz, 0.05), 1.0))
    cuff_v = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', ribs_cuff, 0.16), 1.0)
    v = N("ShaderNodeMix"); v.data_type = 'FLOAT'; L(cuff, v.inputs["Factor"]); L(body_v, v.inputs["A"]); L(cuff_v, v.inputs["B"])
    fold = math_node(nt, 'SUBTRACT', 1.0, math_node(nt, 'MULTIPLY', smoothstep_node(nt, above, B["cuff"] - 0.003, B["cuff"]),
                                                     math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, above, B["cuff"] + 0.002, B["cuff"] + 0.006))))
    fold = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', fold, 0.45), 0.55)
    ao = N("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.02
    aor = smoothstep_node(nt, ao.outputs["AO"], -0.6, 1.0)
    f = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', v.outputs["Result"], fold), aor)
    fuzz = N("ShaderNodeTexNoise"); fuzz.inputs["Scale"].default_value = 600; L(tc.outputs["Object"], fuzz.inputs["Vector"])
    f = math_node(nt, 'MULTIPLY', f, math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', fuzz.outputs["Fac"], 0.16), 0.92))
    col = mix_rgb(nt, 1.0, base.outputs[0], f, 'MULTIPLY')
    L(col, emi.inputs["Color"]); L(emi.outputs["Emission"], out.inputs["Surface"])
    return m


def build_beanie(head=None):
    old = bpy.data.objects.get("Thief_Beanie")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    o = head or thief_mesh()
    print("hair tucked", tuck_hair(o))
    bean = beanie_mesh()
    mat = beanie_material(); bean.data.materials.append(mat)
    img = bpy.data.images.get("Thief_Beanie") or bpy.data.images.new("Thief_Beanie", 1024, 1024, alpha=False)
    tn = mat.node_tree.nodes.new("ShaderNodeTexImage"); tn.image = img; mat.node_tree.nodes.active = tn
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'GPU'; sc.cycles.samples = 8
    for x in bpy.context.selected_objects:
        x.select_set(False)
    bean.select_set(True); bpy.context.view_layer.objects.active = bean
    bpy.ops.object.bake(type='EMIT')
    img.filepath_raw = BEANIE_TEX; img.file_format = 'PNG'; img.save()
    gm = bpy.data.materials.get("Thief_Beanie") or bpy.data.materials.new("Thief_Beanie"); gm.use_nodes = True
    g = gm.node_tree; g.nodes.clear()
    oo = g.nodes.new("ShaderNodeOutputMaterial"); b = g.nodes.new("ShaderNodeBsdfPrincipled")
    t = g.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(BEANIE_TEX, check_existing=True); t.image.reload()
    g.links.new(t.outputs["Color"], b.inputs["Base Color"]); g.links.new(b.outputs["BSDF"], oo.inputs["Surface"])
    b.inputs["Roughness"].default_value = 0.92; b.inputs["Specular IOR Level"].default_value = 0.2
    bean.data.materials.clear(); bean.data.materials.append(gm)
    return bean
