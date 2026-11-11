"""Caramelo, stage 2 - paint: joins the parts into one mesh (a vertex group per part for the rig), unwraps it and
bakes one painted albedo (2048) from a procedural fur shader:
  * colour regions from the anatomy (numpy masks on the rest pose): caramel coat with a darker saddle, cream muzzle,
    chin, chest, belly, inner legs and socks, pink inner ears, black nose and lip line, dark eye rims;
  * fur strands that follow the coat's flow (back along the body, down the legs, out along the tail) - a per-vertex
    'FurUV' map whose U runs across the flow, so stretched noise reads as hair;
  * soft painted depth (baked ambient occlusion) and a gentle top light, like the game's painted textures.
Eyes are glossy dark brown with a big catch-light (cartoon). No text anywhere.

    exec(open(".../pets/caramelo_model.py").read()); exec(open(".../pets/caramelo_paint.py").read())
    parts = build_model(); dog = paint_dog(parts)
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Color

TEX = os.path.join(HERE, "Caramelo_albedo.png")

# sRGB colours -> linear for the vertex colours
def lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

COL = dict(
    caramel=lin((0.84, 0.52, 0.22)), saddle=lin((0.66, 0.36, 0.13)), cream=lin((0.99, 0.91, 0.75)),
    blush=lin((0.95, 0.70, 0.62)), nose=lin((0.10, 0.07, 0.07)), rim=lin((0.20, 0.11, 0.07)),
    mouth=lin((0.50, 0.17, 0.20)), tongue=lin((0.95, 0.48, 0.53)), lip=lin((0.16, 0.10, 0.09)),
    pad=lin((0.24, 0.16, 0.14)),
)


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def join_parts(parts):
    """One mesh, a vertex group named after each part (body parts get their bone weights later)."""
    for key, o in parts.items():
        vg = o.vertex_groups.new(name="part_" + key)
        vg.add(range(len(o.data.vertices)), 1.0, 'REPLACE')
    body = parts["body"]
    for x in bpy.context.selected_objects:
        x.select_set(False)
    for o in parts.values():
        o.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = "Caramelo"; body.data.name = "Caramelo"
    return body


def part_mask(obj, key, n):
    me = obj.data
    names = {g.index: g.name for g in obj.vertex_groups}
    gi = next(i for i, nm in names.items() if nm == "part_" + key)
    m = np.zeros(n, bool)
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi and g.weight > 0.5:
                m[v.index] = True
    return m


def compute_colours(dog):
    me = dog.data; n = len(me.vertices)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(n, 3)
    no = np.empty(n * 3); me.vertices.foreach_get("normal", no); no = no.reshape(n, 3)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    ax = np.abs(x)
    ear_inner = np.zeros(n)
    gi = dog.vertex_groups.get("ear_inner")
    if gi:
        for v in me.vertices:
            for g in v.groups:
                if g.group == gi.index:
                    ear_inner[v.index] = g.weight
    m = {k: part_mask(dog, k, n) for k in ("body", "jaw", "tongue", "nose", "eyeL", "eyeR", "lidL", "lidR", "earL", "earR")}
    C = lambda k: np.array(COL[k])
    col = np.tile(C("caramel"), (n, 1))

    # darker saddle along the back, the top of the head and the tail's top
    saddle = smooth(no[:, 2], 0.25, 0.85) * smooth(z, 0.40, 0.52) * (1 - smooth(-y, 0.42, 0.52))
    col = col * (1 - saddle[:, None] * 0.75) + C("saddle") * (saddle[:, None] * 0.75)

    # cream: muzzle (lower half), chin/throat, chest blaze, belly, inner legs, socks, tail tip
    muzzle = smooth(-y, 0.50, 0.545) * (1 - smooth(z, 0.645, 0.665))
    blaze = smooth(-no[:, 1] - no[:, 2] * 0.3, 0.15, 0.6) * smooth(-y, 0.20, 0.27) * (1 - smooth(z, 0.56, 0.60)) * smooth(z, 0.30, 0.34)
    blaze *= 1 - smooth(ax, 0.055, 0.085)
    throat = smooth(-no[:, 2], 0.1, 0.6) * smooth(-y, 0.33, 0.40) * (1 - smooth(z, 0.64, 0.66))
    belly = smooth(-no[:, 2], 0.30, 0.75) * (1 - smooth(z, 0.40, 0.44)) * smooth(z, 0.28, 0.30)
    inner = smooth(0.06 - ax, -0.01, 0.015) * (1 - smooth(z, 0.30, 0.36)) * smooth(z, 0.07, 0.12)
    socks = (1 - smooth(z, 0.045, 0.07))
    socks *= np.where(y < 0, 1.0, 0.55)                                   # white socks, front a bit taller
    tail_tip = smooth(z, 0.66, 0.70) * smooth(y, 0.30, 0.32)
    cream = np.clip(muzzle + blaze + throat + belly + inner * 0.8 + socks + tail_tip, 0, 1) * m["body"]
    # the cream patches are mixed in the shader, where their edge breaks up along the fur strokes

    # dark rim around the eyes and the lip line on the muzzle's lower edge
    for side in ("L", "R"):
        ec = co[m["eye" + side]].mean(0)
        d = np.linalg.norm(co - ec, axis=1)
        ring = (1 - smooth(d, 0.0215, 0.0255)) * m["body"]
        col = col * (1 - ring[:, None]) + C("rim") * ring[:, None]
    jaw_top = co[m["jaw"]][:, 2].max()
    lipline = smooth(-y, 0.47, 0.50) * (1 - smooth(ax, 0.05, 0.065)) * (1 - smooth(np.abs(z - (jaw_top - 0.004)), 0.003, 0.008)) * m["body"]
    col = col * (1 - lipline[:, None]) + C("lip") * lipline[:, None]

    # parts
    col[m["nose"]] = C("nose")
    for s in ("L", "R"):
        col[m["lid" + s]] = col[m["body"]].mean(0) * 0 + C("caramel")
        ear = m["ear" + s]
        ec = co[ear]; base = ec[:, 2].min()
        h = (z - base) / 0.12
        inside = ear_inner                                   # the inner shell (vertex group from the model)
        inside = inside * smooth(h, 0.06, 0.22) * (1 - smooth(h, 0.70, 0.92)) * 0.8
        e_col = C("caramel") * (1 - smooth(h, 0.4, 1.0)[:, None] * 0.35) + C("saddle") * (smooth(h, 0.4, 1.0)[:, None] * 0.35)
        e_col = e_col * (1 - inside[:, None] * 0.85) + C("blush") * (inside[:, None] * 0.85)
        col[ear] = e_col[ear]
    jaw = m["jaw"]
    jz = co[jaw][:, 2]; jtop = jz.max(); jbot = jz.min()
    top = smooth(z, jtop - 0.006, jtop - 0.002)
    j_col = C("cream") * (1 - top[:, None]) + C("mouth") * top[:, None]
    rimj = smooth(z, jtop - 0.0085, jtop - 0.0055) * (1 - top)
    j_col = j_col * (1 - rimj[:, None]) + C("lip") * rimj[:, None]
    col[jaw] = j_col[jaw]
    tg = m["tongue"]
    groove = 1 - smooth(ax, 0.002, 0.006)
    t_col = C("tongue") * (1 - groove[:, None] * 0.25)
    col[tg] = t_col[tg]
    eye = m["eyeL"] | m["eyeR"]
    col[eye] = np.array(lin((0.25, 0.13, 0.06)))

    # flow of the coat (unit vectors): back along the body, down the legs, along the tail, back on the head
    flow = np.tile(np.array([0.0, 1.0, -0.25]), (n, 1))
    legs = (1 - smooth(z, 0.26, 0.36))
    flow = flow * (1 - legs[:, None]) + np.array([0.0, 0.15, -1.0]) * legs[:, None]
    tail = smooth(y, 0.29, 0.31) * smooth(z, 0.45, 0.47)
    flow = flow * (1 - tail[:, None]) + np.array([0.0, -0.3, 1.0]) * tail[:, None]
    head = smooth(-y, 0.33, 0.38)
    flow = flow * (1 - head[:, None]) + np.array([0.0, 1.0, 0.35]) * head[:, None]
    flow /= np.linalg.norm(flow, axis=1)[:, None]
    across = np.cross(flow, no); across /= np.maximum(np.linalg.norm(across, axis=1), 1e-6)[:, None]
    fu = (co * across).sum(1); fv = (co * flow).sum(1)
    return col, np.stack([fu, fv], 1), m, cream


def write_attributes(dog, col, furuv):
    me = dog.data
    if "Coat" in me.color_attributes:
        me.color_attributes.remove(me.color_attributes["Coat"])
    ca = me.color_attributes.new("Coat", 'FLOAT_COLOR', 'POINT')
    rgba = np.concatenate([col, np.ones((len(col), 1))], 1).ravel()
    ca.data.foreach_set("color", rgba)
    if "FurUV" in me.uv_layers:
        me.uv_layers.remove(me.uv_layers["FurUV"])
    uv = me.uv_layers.new(name="FurUV")
    vi = np.empty(len(me.loops), int); me.loops.foreach_get("vertex_index", vi)
    uv.data.foreach_set("uv", furuv[vi].ravel())


def unwrap(dog):
    me = dog.data
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    me.uv_layers["UVMap"].active = True
    me.uv_layers["UVMap"].active_render = True
    bpy.context.view_layer.objects.active = dog
    for x in bpy.context.selected_objects:
        x.select_set(False)
    dog.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_material(dog, eyes_mask):
    """Emission shader = painted colour (coat x fur strands x baked occlusion x top light); baked to TEX."""
    mat = bpy.data.materials.get("Caramelo_Bake") or bpy.data.materials.new("Caramelo_Bake")
    mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial")
    emi = N("ShaderNodeEmission")
    vc = N("ShaderNodeVertexColor"); vc.layer_name = "Coat"
    furuv = N("ShaderNodeUVMap"); furuv.uv_map = "FurUV"
    # brush strokes: elongated Voronoi cells along the flow, each a slightly different shade (2 sizes)
    def strokes(scale, lo, hi):
        mp = N("ShaderNodeMapping"); mp.inputs["Scale"].default_value = scale
        L(furuv.outputs["UV"], mp.inputs["Vector"])
        vo = N("ShaderNodeTexVoronoi"); vo.feature = 'F1'; vo.inputs["Randomness"].default_value = 1.0
        L(mp.outputs["Vector"], vo.inputs["Vector"])
        sp = N("ShaderNodeSeparateColor"); L(vo.outputs["Color"], sp.inputs["Color"])
        mr = N("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = lo; mr.inputs["To Max"].default_value = hi
        L(sp.outputs["Red"], mr.inputs["Value"])
        return mr, vo
    s1, v1 = strokes((520, 110, 1), 0.90, 1.07)
    s2, v2 = strokes((240, 52, 1), 0.94, 1.05)
    f1, f2 = s1, s2
    fine = N("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 1.0; fine.inputs["Detail"].default_value = 3
    mpf = N("ShaderNodeMapping"); mpf.inputs["Scale"].default_value = (1400, 160, 1)
    L(furuv.outputs["UV"], mpf.inputs["Vector"]); L(mpf.outputs["Vector"], fine.inputs["Vector"])
    fur = N("ShaderNodeMath"); fur.operation = 'MULTIPLY'
    L(f1.outputs["Result"], fur.inputs[0]); L(f2.outputs["Result"], fur.inputs[1])
    fineR = N("ShaderNodeMapRange"); fineR.inputs["To Min"].default_value = 0.94; fineR.inputs["To Max"].default_value = 1.05
    L(fine.outputs["Fac"], fineR.inputs["Value"])
    fur2 = N("ShaderNodeMath"); fur2.operation = 'MULTIPLY'
    L(fur.outputs["Value"], fur2.inputs[0]); L(fineR.outputs["Result"], fur2.inputs[1])
    fur = fur2
    # parts without fur (nose, eyes, tongue, mouth): attribute 'NoFur' = 1 there
    nf = N("ShaderNodeAttribute"); nf.attribute_name = "NoFur"
    furmix = N("ShaderNodeMix"); furmix.data_type = 'FLOAT'
    L(nf.outputs["Fac"], furmix.inputs["Factor"]); L(fur.outputs["Value"], furmix.inputs["A"])
    furmix.inputs["B"].default_value = 1.0
    ao = N("ShaderNodeAmbientOcclusion"); ao.samples = 24; ao.inputs["Distance"].default_value = 0.06
    aom = N("ShaderNodeMapRange"); aom.inputs["To Min"].default_value = 0.62; aom.inputs["To Max"].default_value = 1.0
    L(ao.outputs["AO"], aom.inputs["Value"])
    geo = N("ShaderNodeNewGeometry")
    sep = N("ShaderNodeSeparateXYZ"); L(geo.outputs["Normal"], sep.inputs["Vector"])
    top = N("ShaderNodeMapRange"); top.inputs["From Min"].default_value = -1; top.inputs["From Max"].default_value = 1
    top.inputs["To Min"].default_value = 0.94; top.inputs["To Max"].default_value = 1.06
    L(sep.outputs["Z"], top.inputs["Value"])
    m1 = N("ShaderNodeMath"); m1.operation = 'MULTIPLY'; L(furmix.outputs["Result"], m1.inputs[0]); L(aom.outputs["Result"], m1.inputs[1])
    m2 = N("ShaderNodeMath"); m2.operation = 'MULTIPLY'; L(m1.outputs["Value"], m2.inputs[0]); L(top.outputs["Result"], m2.inputs[1])
    tint = N("ShaderNodeMix"); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'
    tint.inputs["Factor"].default_value = 1.0
    cr = N("ShaderNodeAttribute"); cr.attribute_name = "Cream"
    # edge = mask + (stroke shade - 0.5) -> sharpened: the patch border breaks up into fur tufts
    vsep = N("ShaderNodeSeparateColor"); L(v2.outputs["Color"], vsep.inputs["Color"])
    jit = N("ShaderNodeMath"); jit.operation = 'MULTIPLY_ADD'      # (rand - 0.5) * 0.5 = rand*0.5 - 0.25
    L(vsep.outputs["Red"], jit.inputs[0]); jit.inputs[1].default_value = 0.5; jit.inputs[2].default_value = -0.25
    edge = N("ShaderNodeMath"); edge.operation = 'ADD'
    L(cr.outputs["Fac"], edge.inputs[0]); L(jit.outputs["Value"], edge.inputs[1])
    sharp = N("ShaderNodeMapRange"); sharp.inputs["From Min"].default_value = 0.42; sharp.inputs["From Max"].default_value = 0.58
    L(edge.outputs["Value"], sharp.inputs["Value"])
    creamMix = N("ShaderNodeMix"); creamMix.data_type = 'RGBA'
    L(sharp.outputs["Result"], creamMix.inputs["Factor"]); L(vc.outputs["Color"], creamMix.inputs["A"])
    creamMix.inputs["B"].default_value = (*COL["cream"], 1)
    L(creamMix.outputs["Result"], tint.inputs["A"]); L(m2.outputs["Value"], tint.inputs["B"])
    # eyes: iris + pupil + catch-light from the eye's own coordinates (attribute EyeUV = local direction)
    eyeA = N("ShaderNodeAttribute"); eyeA.attribute_name = "EyeDir"
    eyeSep = N("ShaderNodeSeparateXYZ"); L(eyeA.outputs["Vector"], eyeSep.inputs["Vector"])
    iris = N("ShaderNodeMapRange"); iris.inputs["From Min"].default_value = 0.55; iris.inputs["From Max"].default_value = 0.98
    iris.inputs["To Min"].default_value = 0.0; iris.inputs["To Max"].default_value = 1.0
    L(eyeSep.outputs["X"], iris.inputs["Value"])          # X = facing outward along the eye's look direction
    ramp = N("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (*lin((0.06, 0.04, 0.03)), 1)
    ramp.color_ramp.elements[1].position = 0.45; ramp.color_ramp.elements[1].color = (*lin((0.36, 0.19, 0.08)), 1)
    e3 = ramp.color_ramp.elements.new(0.70); e3.color = (*lin((0.22, 0.11, 0.05)), 1)
    e4 = ramp.color_ramp.elements.new(0.80); e4.color = (*lin((0.03, 0.02, 0.02)), 1)
    L(iris.outputs["Result"], ramp.inputs["Fac"])
    hl = N("ShaderNodeMapRange"); hl.inputs["From Min"].default_value = 0.955; hl.inputs["From Max"].default_value = 0.965
    L(eyeSep.outputs["Y"], hl.inputs["Value"])            # Y = towards the catch-light direction
    eyecol = N("ShaderNodeMix"); eyecol.data_type = 'RGBA'
    L(hl.outputs["Result"], eyecol.inputs["Factor"]); L(ramp.outputs["Color"], eyecol.inputs["A"])
    eyecol.inputs["B"].default_value = (1, 1, 1, 1)
    isEye = N("ShaderNodeAttribute"); isEye.attribute_name = "IsEye"
    final = N("ShaderNodeMix"); final.data_type = 'RGBA'
    L(isEye.outputs["Fac"], final.inputs["Factor"]); L(tint.outputs["Result"], final.inputs["A"]); L(eyecol.outputs["Result"], final.inputs["B"])
    L(final.outputs["Result"], emi.inputs["Color"])
    L(emi.outputs["Emission"], out.inputs["Surface"])
    img = bpy.data.images.get("Caramelo_albedo") or bpy.data.images.new("Caramelo_albedo", 2048, 2048, alpha=False)
    tex = N("ShaderNodeTexImage"); tex.image = img
    nt.nodes.active = tex
    dog.data.materials.clear(); dog.data.materials.append(mat)
    return mat, img


def eye_attributes(dog, m):
    """EyeDir: for eye vertices, (dot with look dir, dot with catch-light dir, 0); IsEye / NoFur flags."""
    me = dog.data; n = len(me.vertices)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(n, 3)
    ed = np.zeros((n, 3)); is_eye = np.zeros(n); nofur = np.zeros(n)
    for s, side in ((1, "L"), (-1, "R")):
        e = m["eye" + side]; c = co[e].mean(0)
        look = np.array([s * 0.45, -0.88, 0.12]); look /= np.linalg.norm(look)
        light = np.array([s * 0.10, -0.75, 0.65]); light /= np.linalg.norm(light)
        d = co - c; d /= np.maximum(np.linalg.norm(d, axis=1), 1e-9)[:, None]
        ed[e, 0] = (d[e] * look).sum(1); ed[e, 1] = (d[e] * light).sum(1)
        is_eye[e] = 1
    nofur[m["nose"] | m["tongue"] | m["eyeL"] | m["eyeR"]] = 1
    # inside of the mouth (top of the jaw) has no fur either
    jz = co[m["jaw"]][:, 2].max() if m["jaw"].any() else 0
    nofur[m["jaw"] & (co[:, 2] > jz - 0.006)] = 1
    for name, data, kind in (("EyeDir", ed, 'FLOAT_VECTOR'), ("IsEye", is_eye, 'FLOAT'), ("NoFur", nofur, 'FLOAT')):
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
        a = me.attributes.new(name, kind, 'POINT')
        if kind == 'FLOAT_VECTOR':
            a.data.foreach_set("vector", data.ravel())
        else:
            a.data.foreach_set("value", data)


def bake(dog, img, samples=48):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'GPU'
    sc.cycles.samples = samples
    sc.render.bake.margin = 8
    sc.render.bake.use_clear = True
    for x in bpy.context.selected_objects:
        x.select_set(False)
    dog.select_set(True); bpy.context.view_layer.objects.active = dog
    bpy.ops.object.bake(type='EMIT')
    img.filepath_raw = TEX; img.file_format = 'PNG'; img.save()
    return TEX


def game_material(dog):
    """What the game uses: the baked albedo on a soft Principled (the preview renders use this too)."""
    mat = bpy.data.materials.get("Caramelo_Mat") or bpy.data.materials.new("Caramelo_Mat")
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(TEX, check_existing=True)
    tex.image.reload()
    uvm = nt.nodes.new("ShaderNodeUVMap"); uvm.uv_map = "UVMap"
    nt.links.new(uvm.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.78
    b.inputs["Specular IOR Level"].default_value = 0.25
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    dog.data.materials.clear(); dog.data.materials.append(mat)
    return mat


def paint_dog(parts, samples=48):
    dog = join_parts(parts)
    col, furuv, m, cream = compute_colours(dog)
    write_attributes(dog, col, furuv)
    a = dog.data.attributes.get("Cream")
    if a:
        dog.data.attributes.remove(a)
    a = dog.data.attributes.new("Cream", 'FLOAT', 'POINT'); a.data.foreach_set("value", cream)
    eye_attributes(dog, m)
    unwrap(dog)
    mat, img = bake_material(dog, m)
    bake(dog, img, samples)
    game_material(dog)
    print("baked", TEX, "verts", len(dog.data.vertices), "tris", sum(len(p.vertices) - 2 for p in dog.data.polygons))
    return dog
