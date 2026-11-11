"""The thief's bandana (Lucas 08/11: "coloque aquelas balaclava ou bandana de ladrões").

A classic outlaw bandana over the nose and mouth of Lucas's Tripo thief (model space of the GLB: 1.0 tall,
faces -Y): it starts just under the eyes, drapes straight down from the nose tip and the cheeks like real cloth
(it never sinks into the hollows), ends in a point under the chin, and wraps round the head to a knot at the back
with two short tails. Red cotton with a cream paisley-ish print and a hem border, soft folds, baked occlusion.

    exec(open(".../pets/thief_bandana.py").read()); band = build_bandana()
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ART = globals().get("ART", "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/ArtSource")
BANDANA_TEX = os.path.join(ART, "NPCs/incoming/Thief_Bandana.png")
C = dict(cy=-0.006, z0=0.775, z1=0.905, nt=160, nz=70, offset=0.0011, thick=0.0014,
         top_front=0.899, top_band=0.892, bot_front=0.792, bot_side=0.858, bot_band=0.866,
         red=(0.075, 0.075, 0.085), red_dark=(0.03, 0.03, 0.035), cream=(0.30, 0.30, 0.33))   # black, a dark-grey print


def _lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def _smooth(a, lo, hi):
    t = np.clip((a - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def edges(th):
    """Top and bottom edge heights at angle th (0 = front, +-pi = back)."""
    a = abs(math.atan2(math.sin(th), math.cos(th)))
    d = math.degrees(a)
    top = C["top_front"] + (C["top_band"] - C["top_front"]) * float(_smooth(np.array(d), 30, 100))
    if d < 75:
        bot = C["bot_front"] + (C["bot_side"] - C["bot_front"]) * (d / 75) ** 1.25
    else:
        bot = C["bot_side"] + (C["bot_band"] - C["bot_side"]) * float(_smooth(np.array(d), 75, 105))
    return top, bot


def head_radius_field(objs):
    """r_hit[i, j]: distance from the head axis to the outermost surface at angle i, height j (rays inwards)."""
    dg = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(o, dg) for o in objs]
    nt, nz = C["nt"], C["nz"]
    ths = np.linspace(-math.pi, math.pi, nt, endpoint=False)
    zs = np.linspace(C["z0"], C["z1"], nz)
    R = np.zeros((nt, nz))
    for i, th in enumerate(ths):
        d = Vector((math.sin(th), -math.cos(th), 0.0))          # th = 0 -> -Y (the face)
        for j, z in enumerate(zs):
            o = Vector((0, C["cy"], z)) + d * 0.3
            best = 0.0
            for t in trees:
                hit = t.ray_cast(o, -d, 0.3)
                if hit[0] is not None:
                    best = max(best, 0.3 - hit[3])
            R[i, j] = best
    return ths, zs, R


def drape(ths, zs, R):
    """Cloth radius: close to the skin (Lucas: "mais próxima da pele"); it only bridges the small hollows (beside
    the nose, the corners of the mouth) and hangs a little under the nose tip and the chin, then smoothed."""
    nt, nz = R.shape
    D = R.copy()
    for j in range(nz - 2, -1, -1):                      # from the top down: a short hang under what sticks out
        D[:, j] = np.maximum(D[:, j], D[:, j + 1] * 0.90 + R[:, j] * 0.10 - 0.0006)
    D = np.max([np.roll(D, k, axis=0) for k in (-1, 0, 1)], axis=0)    # bridge sideways, one bin
    for _ in range(3):
        D = (np.roll(D, 1, 0) + np.roll(D, -1, 0) + 2 * D) / 4
        D[:, 1:-1] = (D[:, :-2] + D[:, 2:] + 2 * D[:, 1:-1]) / 4
    D = np.maximum(D, R + 0.0008)                         # never through the skin / beanie
    return D + C["offset"]


def bandana_mesh(ths, zs, D, ns=44):
    """Grid in (angle, s): each column runs from its bottom edge to its top edge, so the hems are clean lines."""
    nt = len(ths)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid = {}
    for i, th in enumerate(ths):
        top, bot = edges(th)
        a = abs(math.atan2(math.sin(th), math.cos(th)))
        for j in range(ns + 1):
            sj = j / ns
            zc = bot + (top - bot) * sj
            r = float(np.interp(zc, zs, D[i]))
            hang = max(0.0, (C["top_front"] - 0.02 - zc) / 0.08) * max(0.0, 1 - a / 1.3)
            r += 0.0007 * hang * math.sin(th * 23.0 + zc * 40.0) + 0.0005 * hang * math.sin(th * 41.0 - zc * 70.0)
            grid[(i, j)] = bm.verts.new((math.sin(th) * r, C["cy"] - math.cos(th) * r, zc))
    for i in range(nt):
        i2 = (i + 1) % nt
        for j in range(ns):
            q = [grid[(i, j)], grid[(i2, j)], grid[(i2, j + 1)], grid[(i, j + 1)]]
            f = bm.faces.new(q)
            for lp, (u, v) in zip(f.loops, [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]):
                lp[uvl].uv = (u / nt, (v / ns) * 0.5)
    me = bpy.data.meshes.new("Thief_Bandana"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Thief_Bandana", me); bpy.context.scene.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    bm = bmesh.new(); bm.from_mesh(me)
    for f in bm.faces:
        c = f.calc_center_median(); out = Vector((c.x, c.y - C["cy"], 0))
        if f.normal.dot(out) < 0:
            f.normal_flip()
    bm.to_mesh(me); bm.free()
    return o


def knot_and_tails(back_y=0.106):
    """Knot at the back of the head (over the beanie's cuff) and two tails hanging over the hood."""
    objs = []
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=14, radius=1.0)
    k = bpy.context.active_object; k.name = "Thief_Bandana_Knot"
    k.scale = (0.016, 0.011, 0.012); k.location = (0.0, back_y + 0.004, 0.879)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    objs.append(k)
    for side in (-1, 1):
        bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
        n = 10; w0, w1 = 0.011, 0.016
        rows = []
        for t in range(n + 1):
            s = t / n
            z = 0.874 - 0.055 * s
            x = side * (0.004 + 0.018 * s + 0.004 * math.sin(s * 3.0))
            y = back_y + 0.008 + 0.010 * s + 0.005 * math.sin(s * 2.2)
            w = w0 + (w1 - w0) * s
            tip = 1.0 if t < n else 0.25
            rows.append((bm.verts.new((x - w / 2 * tip, y, z)), bm.verts.new((x + w / 2 * tip, y, z))))
        for t in range(n):
            f = bm.faces.new([rows[t][0], rows[t][1], rows[t + 1][1], rows[t + 1][0]])
            for lp, uv in zip(f.loops, [(0.0, t / n), (0.1, t / n), (0.1, (t + 1) / n), (0.0, (t + 1) / n)]):
                lp[uvl].uv = (uv[0] * 0.5 + (0.0 if side < 0 else 0.5), 0.55 + uv[1] * 0.4)
        me = bpy.data.meshes.new("Thief_Bandana_Tail"); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new("Thief_Bandana_Tail", me); bpy.context.scene.collection.objects.link(o)
        for p in me.polygons:
            p.use_smooth = True
        objs.append(o)
    # knot UVs into the upper band of the atlas
    me = k.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    for lp in me.loops:
        uv = me.uv_layers.active.data[lp.index].uv
        me.uv_layers.active.data[lp.index].uv = (uv.x, 0.55 + uv.y * 0.4)
    return objs


def bandana_material():
    m = bpy.data.materials.get("Thief_BandanaBake") or bpy.data.materials.new("Thief_BandanaBake")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); emi = N("ShaderNodeEmission")
    tc = N("ShaderNodeTexCoord")
    # paisley-ish print in object space (continuous across the knot / tails): voronoi teardrops + little dots
    mp = N("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (42, 42, 42); L(tc.outputs["Object"], mp.inputs["Vector"])
    vo = N("ShaderNodeTexVoronoi"); vo.feature = 'F1'; vo.inputs["Randomness"].default_value = 0.7; L(mp.outputs["Vector"], vo.inputs["Vector"])
    big = N("ShaderNodeMapRange"); big.inputs["From Min"].default_value = 0.30; big.inputs["From Max"].default_value = 0.22
    L(vo.outputs["Distance"], big.inputs["Value"])                                 # cream blobs
    ring = N("ShaderNodeMapRange"); ring.inputs["From Min"].default_value = 0.40; ring.inputs["From Max"].default_value = 0.33
    L(vo.outputs["Distance"], ring.inputs["Value"])                                # dark ring around them
    eye = N("ShaderNodeMapRange"); eye.inputs["From Min"].default_value = 0.10; eye.inputs["From Max"].default_value = 0.06
    L(vo.outputs["Distance"], eye.inputs["Value"])                                 # red dot in the middle
    mp2 = N("ShaderNodeMapping"); mp2.inputs["Scale"].default_value = (120, 120, 120); L(tc.outputs["Object"], mp2.inputs["Vector"])
    vo2 = N("ShaderNodeTexVoronoi"); L(mp2.outputs["Vector"], vo2.inputs["Vector"])
    dots = N("ShaderNodeMapRange"); dots.inputs["From Min"].default_value = 0.16; dots.inputs["From Max"].default_value = 0.10
    L(vo2.outputs["Distance"], dots.inputs["Value"])
    # weave
    wv = N("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 900; wv.inputs["Distortion"].default_value = 0.0
    L(tc.outputs["Object"], wv.inputs["Vector"])
    # hem border along the cloth's edges (uv v near 0 or top) - bandana mesh only: uv.y in [0, 0.5]
    uvn = N("ShaderNodeUVMap"); sep = N("ShaderNodeSeparateXYZ"); L(uvn.outputs["UV"], sep.inputs["Vector"])

    def mix(fac, a, b, blend='MIX'):
        n = N("ShaderNodeMix"); n.data_type = 'RGBA'; n.blend_type = blend
        if isinstance(fac, float):
            n.inputs[0].default_value = fac
        else:
            L(fac, n.inputs[0])
        for k, v in ((6, a), (7, b)):
            if isinstance(v, tuple):
                n.inputs[k].default_value = v
            else:
                L(v, n.inputs[k])
        return n.outputs[2]
    col = mix(ring.outputs["Result"], _lin(C["red"]), _lin(C["red_dark"]))
    col = mix(big.outputs["Result"], col, _lin(C["cream"]))
    col = mix(eye.outputs["Result"], col, _lin(C["red"]))
    dmul = N("ShaderNodeMath"); dmul.operation = 'MULTIPLY'; L(dots.outputs["Result"], dmul.inputs[0]); dmul.inputs[1].default_value = 0.8
    col = mix(dmul.outputs[0], col, _lin(C["cream"]))
    wmul = N("ShaderNodeMapRange"); L(wv.outputs["Fac"], wmul.inputs["Value"]); wmul.inputs["To Min"].default_value = 0.90; wmul.inputs["To Max"].default_value = 1.05
    col = mix(1.0, col, wmul.outputs["Result"], 'MULTIPLY')
    hb1 = N("ShaderNodeMapRange"); L(sep.outputs["Y"], hb1.inputs["Value"]); hb1.inputs["From Min"].default_value = 0.022; hb1.inputs["From Max"].default_value = 0.016
    hb2 = N("ShaderNodeMapRange"); L(sep.outputs["Y"], hb2.inputs["Value"]); hb2.inputs["From Min"].default_value = 0.478; hb2.inputs["From Max"].default_value = 0.484
    hb3 = N("ShaderNodeMapRange"); L(sep.outputs["Y"], hb3.inputs["Value"]); hb3.inputs["From Min"].default_value = 0.53; hb3.inputs["From Max"].default_value = 0.51
    hem = N("ShaderNodeMath"); hem.operation = 'MAXIMUM'; L(hb1.outputs["Result"], hem.inputs[0]); L(hb2.outputs["Result"], hem.inputs[1])
    hem2 = N("ShaderNodeMath"); hem2.operation = 'MULTIPLY'; L(hem.outputs[0], hem2.inputs[0]); L(hb3.outputs["Result"], hem2.inputs[1])
    col = mix(hem2.outputs[0], col, _lin(C["red_dark"]))
    # a thin cream line just inside the hem
    ln1 = N("ShaderNodeMapRange"); L(sep.outputs["Y"], ln1.inputs["Value"]); ln1.inputs["From Min"].default_value = 0.034; ln1.inputs["From Max"].default_value = 0.030
    ln1b = N("ShaderNodeMapRange"); L(sep.outputs["Y"], ln1b.inputs["Value"]); ln1b.inputs["From Min"].default_value = 0.024; ln1b.inputs["From Max"].default_value = 0.028
    lnm = N("ShaderNodeMath"); lnm.operation = 'MULTIPLY'; L(ln1.outputs["Result"], lnm.inputs[0]); L(ln1b.outputs["Result"], lnm.inputs[1])
    col = mix(lnm.outputs[0], col, _lin(C["cream"]))
    ao = N("ShaderNodeAmbientOcclusion"); ao.samples = 16; ao.inputs["Distance"].default_value = 0.012
    aom = N("ShaderNodeMapRange"); L(ao.outputs["AO"], aom.inputs["Value"]); aom.inputs["To Min"].default_value = 0.55
    col = mix(1.0, col, aom.outputs["Result"], 'MULTIPLY')
    L(col, emi.inputs["Color"]); L(emi.outputs["Emission"], out.inputs["Surface"])
    return m


def bake(objs, size=1024):
    img = bpy.data.images.get("Thief_Bandana") or bpy.data.images.new("Thief_Bandana", size, size, alpha=False)
    m = bandana_material()
    tn = m.node_tree.nodes.new("ShaderNodeTexImage"); tn.image = img; m.node_tree.nodes.active = tn
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(m)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 8; sc.render.bake.margin = 6
    for x in bpy.context.selected_objects:
        x.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type='EMIT')
    img.filepath_raw = BANDANA_TEX; img.file_format = 'PNG'; img.save()
    pm = bpy.data.materials.get("Thief_Bandana") or bpy.data.materials.new("Thief_Bandana"); pm.use_nodes = True
    g = pm.node_tree; g.nodes.clear()
    o_ = g.nodes.new("ShaderNodeOutputMaterial"); b = g.nodes.new("ShaderNodeBsdfPrincipled")
    t = g.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(BANDANA_TEX, check_existing=True); t.image.reload()
    g.links.new(t.outputs["Color"], b.inputs["Base Color"]); g.links.new(b.outputs["BSDF"], o_.inputs["Surface"])
    b.inputs["Roughness"].default_value = 0.85; b.inputs["Specular IOR Level"].default_value = 0.2
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(pm)


def build_bandana():
    for n in [o.name for o in bpy.data.objects if o.name.startswith("Thief_Bandana")]:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("tripo_node"))
    bean = bpy.data.objects["Thief_Beanie"]
    ths, zs, R = head_radius_field([body, bean])
    D = drape(ths, zs, R)
    band = bandana_mesh(ths, zs, D)
    sol = band.modifiers.new("thick", 'SOLIDIFY'); sol.thickness = C["thick"]; sol.offset = 1.0; sol.use_even_offset = False
    bpy.context.view_layer.objects.active = band
    for x in bpy.context.selected_objects:
        x.select_set(False)
    band.select_set(True); bpy.ops.object.modifier_apply(modifier="thick")
    jb = int(np.argmin(np.abs(zs - 0.879)))
    ib = int(np.argmin(np.abs(np.abs(ths) - math.pi)))
    back_y = C["cy"] + float(D[ib, jb])
    print("back of the band at y", round(back_y, 4))
    extra = knot_and_tails(back_y)
    for o in extra:
        if o.name.startswith("Thief_Bandana_Tail"):
            s = o.modifiers.new("thick", 'SOLIDIFY'); s.thickness = 0.0012
            bpy.context.view_layer.objects.active = o
            for x in bpy.context.selected_objects:
                x.select_set(False)
            o.select_set(True); bpy.ops.object.modifier_apply(modifier="thick")
    objs = [band] + extra
    bake(objs)
    for x in bpy.context.selected_objects:
        x.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = band
    bpy.ops.object.join()
    band.name = "Thief_Bandana"
    print("bandana", len(band.data.polygons), "faces")
    return band
