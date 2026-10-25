"""Sector puzzle art: queijaria, acougue, peixaria, sucos, sorvetes, adega (PREVIEW ONLY, nothing goes into Unity).

Same house look as puzzle_padaria.py (Cycles GPU + OIDN, orthographic camera, warm sun from the top-left ~18 deg,
dim warm world, shadow catcher for a soft baked contact shadow, Khronos PBR Neutral + Medium High Contrast).

    import sys; sys.path.insert(0, r"C:\\Checkout-mobile\\scripts\\blender")
    import importlib, puzzle_sectors as ps; importlib.reload(ps)
    ps.run("queijaria")            # build + render every sprite, the bench and the mockup of one sector, save .blend
    ps.run_all()                   # every sector
    ps.build("queijaria"); ps.render_piece("queijaria", "brie")       # one sprite while iterating

Outputs: unity/CheckoutSimulator/Temp/qa/puzzle_sectors/ ; source: ArtSource/puzzle_sectors/sectors_puzzle.blend
No text / letters / numbers anywhere.
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import puzzle_padaria as pp  # noqa: E402
from puzzle_padaria import (NB, srgb, smooth, col, wipe_collection, link, mesh_object, cube_sphere, lathe_bm,  # noqa: E402
                            spline, xform, rounded_slab, quad_bm, wood_material, simple_material, towel_material,
                            img_load, img_save, img_resize, over, blur, rounded_mask)

ROOT = r"C:\Checkout-mobile"
UNITY = os.path.join(ROOT, "unity", "CheckoutSimulator")
OUT = os.path.join(UNITY, "Temp", "qa", "puzzle_sectors")
BLEND = os.path.join(UNITY, "ArtSource", "puzzle_sectors", "sectors_puzzle.blend")
SCENE = "Sectors"
VIEW = pp.VIEW
SECTORS = ["queijaria", "acougue", "peixaria", "sucos", "sorvetes", "adega"]
BENCH_SIZE = (1.25, 1.25 * 9 / 16)
MPX = 2000.0          # mockup parts: pixels per metre


def O(sector):
    """World origin of a sector's working area (pieces row at y=0, bench at y=-2, mockup parts at y=-4)."""
    return Vector((SECTORS.index(sector) * 12.0, 0.0, 0.0))


# ============================================================================================ file / scene
def ensure_file():
    """Work in our own .blend (never touch the padaria one)."""
    if bpy.data.filepath and os.path.normcase(bpy.data.filepath) == os.path.normcase(BLEND):
        return
    if os.path.exists(BLEND):
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    else:
        bpy.ops.wm.read_homefile(use_empty=True)
        os.makedirs(os.path.dirname(BLEND), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND)


def save():
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


def setup_scene():
    sc = bpy.context.scene
    sc.name = SCENE
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.refresh_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception:
        pass
    sc.cycles.samples = 160
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = .015
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 8
    sc.cycles.transmission_bounces = 8
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.render.film_transparent = True
    sc.cycles.film_transparent_glass = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = VIEW[0]
    sc.view_settings.look = VIEW[1]
    sc.view_settings.exposure = VIEW[2]
    sc.unit_settings.system = "METRIC"
    set_world("warm")
    gc = col("Studio")
    for name, d in (("Sun_TopLeft", Vector((1.0, -1.15, -2.9))),       # top-down shots: light travels right/down/into
                    ("Sun_Front", Vector((.7, 1.1, -2.6)))):            # front shots: from upper-left, mostly above (short shadow)
        sun = bpy.data.objects.get(name)
        if not sun:
            sun = link(bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN")), gc)
        sun.data.energy = 3.0
        sun.data.color = (1.0, .93, .82)
        sun.data.angle = math.radians(18)
        sun.rotation_euler = d.normalized().to_track_quat("-Z", "Y").to_euler()
    cam = bpy.data.objects.get("Cam")
    if not cam:
        cam = link(bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")), gc)
    cam.data.type = "ORTHO"
    cam.data.clip_start = .01
    cam.data.clip_end = 20
    sc.camera = cam
    os.makedirs(OUT, exist_ok=True)
    return sc


def set_world(mode="warm", strength=.5):
    """warm: the padaria ambient. glass: camera and refracted rays see black, reflections see the warm ambient
    (used to render the additive reflection layer of the glass sprites)."""
    sc = bpy.context.scene
    w = bpy.data.worlds.get("Sectors") or bpy.data.worlds.new("Sectors")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    env = nt.nodes.new("ShaderNodeBackground")
    env.inputs[0].default_value = srgb("F2E6D6")
    env.inputs[1].default_value = strength
    if mode == "warm":
        nt.links.new(env.outputs[0], out.inputs[0])
        return
    # vertical gradient so reflections are not flat: brighter above
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = .35
    ramp.color_ramp.elements[0].color = srgb("2A2622")
    ramp.color_ramp.elements[1].position = .75
    ramp.color_ramp.elements[1].color = srgb("F6EEE2")
    nt.links.new(sep.outputs[2], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], env.inputs[0])
    black = nt.nodes.new("ShaderNodeBackground")
    black.inputs[0].default_value = (0, 0, 0, 1)
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Glossy Ray"], mix.inputs[0])
    nt.links.new(black.outputs[0], mix.inputs[1])
    nt.links.new(env.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])


def catcher(sector, at, size=(4.0, 1.4), name=None):
    name = name or "Catcher_" + sector
    sh = bpy.data.objects.get(name)
    if not sh:
        sh = mesh_object(name, quad_bm(*size), None, col("Studio"), subsurf=0)
    sh.location = at
    sh.is_shadow_catcher = True
    return sh


def shoot(center, size_m, res, path, transparent=True, visible=(), view="top", tilt=0.0, sun=None, world=None):
    """Orthographic render of the `size_m` rectangle around `center` (top: XY plane; front: XZ plane, camera on -Y,
    tilted `tilt` degrees down). Only objects named in `visible` (plus the matching sun) render."""
    sc = bpy.context.scene
    cam = bpy.data.objects["Cam"]
    c = Vector(center) if len(center) == 3 else Vector((center[0], center[1], 0))
    if view == "top":
        cam.location = c + Vector((0, 0, 4.0))
        cam.rotation_euler = (0, 0, 0)
        sun = sun or "Sun_TopLeft"
    else:
        t = math.radians(tilt)
        d = Vector((0, math.cos(t), -math.sin(t)))
        cam.location = c - d * 5.0
        cam.rotation_euler = (math.pi / 2 - t, 0, 0)
        sun = sun or "Sun_Front"
    cam.data.ortho_scale = max(size_m)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = transparent
    keep = set(visible)
    if sun:
        keep.add(sun)
    saved = {}
    for o in sc.objects:
        if o.type in {"MESH", "CURVE", "LIGHT"}:
            saved[o.name] = o.hide_render
            o.hide_render = o.name not in keep
    sc.render.filepath = path
    try:
        bpy.ops.render.render(write_still=True)
    finally:
        for n, v in saved.items():
            bpy.data.objects[n].hide_render = v
    if transparent and any(n.startswith("Catcher") for n in keep):
        clean_shadow(path)
    return path


def clean_shadow(path, edge=.14):
    """Shadow-catcher pixels (black + alpha) fade out towards the frame so no shadow is clipped by the border,
    and the faint ambient haze on the ground is dropped."""
    a = img_load(path)
    h, w = a.shape[:2]
    sh = a[..., :3].max(-1) < .035
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / (edge * min(w, h))
    fall = np.clip(d, 0, 1)
    fall = fall * fall * (3 - 2 * fall)
    al = a[..., 3]
    al = np.where(sh, np.minimum(np.clip((al - .04) / .96, 0, 1) * fall, .45), al)    # shadows never count as 'opaque'
    a[..., 3] = al
    img_save(a, path)


# ============================================================================================ generic geometry
def bm_join(dst, src):
    me = bpy.data.meshes.new("_t")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)
    return dst


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    me.name = ob.name
    return ob


def ellipsoid(rx, ry, rz, sub=3, flat=0.0, seed=0, lump=0.0, lump_f=3.0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1)
    off = Vector((seed * 1.7, seed * 2.3, seed * .9))
    for v in bm.verts:
        k = 1 + lump * noise.noise(v.co * lump_f + off)
        z = v.co.z
        if flat and z < -1 + flat:
            z = -1 + flat - (-1 + flat - z) * .15
        v.co = Vector((v.co.x * rx * k, v.co.y * ry * k, z * rz * k))
    return bm


def tube_bm(pts, radius, seg=12, cap=True, twist=0.0):
    """Sweeps a circle along pts (list of 3-tuples). radius: float or callable(t)."""
    bm = bmesh.new()
    P = [Vector(p) for p in pts]
    n = len(P)
    rings = []
    prev = None
    for i, p in enumerate(P):
        tan = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        ref = prev if prev is not None else (Vector((0, 0, 1)) if abs(tan.z) < .9 else Vector((1, 0, 0)))
        nrm = (ref - tan * ref.dot(tan)).normalized()
        prev = nrm
        bi = tan.cross(nrm)
        t = i / (n - 1)
        r = radius(t) if callable(radius) else radius
        rings.append([bm.verts.new(p + (nrm * math.cos(2 * math.pi * j / seg + twist * t) + bi * math.sin(2 * math.pi * j / seg + twist * t)) * r)
                      for j in range(seg)])
    uvl = bm.loops.layers.uv.new("UVMap")
    acc = [0.0]
    for i in range(1, n):
        acc.append(acc[-1] + (P[i] - P[i - 1]).length)
    for i in range(n - 1):
        for j in range(seg):
            f = bm.faces.new((rings[i][j], rings[i][(j + 1) % seg], rings[i + 1][(j + 1) % seg], rings[i + 1][j]))
            for l, (u, v) in zip(f.loops, ((acc[i], j / seg), (acc[i], (j + 1) / seg), (acc[i + 1], (j + 1) / seg), (acc[i + 1], j / seg))):
                l[uvl].uv = (u, v)
    if cap:
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / seg)
            for j in range(seg):
                f = (ring[j], ring[(j + 1) % seg], c)
                bm.faces.new(tuple(reversed(f)) if rev else f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def outline_slab(pts, t, bevel=.004, segs=4):
    """Extrudes a closed 2D outline (list of (x, y), CCW) to thickness t and bevels its edges."""
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, 0)) for x, y in pts]
    top = [bm.verts.new((x, y, t)) for x, y in pts]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    n = len(pts)
    for i in range(n):
        bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bevel:
        bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.calc_face_angle(0) > .6], offset=min(bevel, t * .45), segments=segs,
                        profile=.5, affect="EDGES", clamp_overlap=True)
    return bm


def round_outline(pts, r, seg=6):
    """Rounds the corners of a closed polygon (fillet radius r)."""
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        a, b = (p0 - p1), (p2 - p1)
        la, lb = a.length, b.length
        rr = min(r, la * .45, lb * .45)
        a.normalize()
        b.normalize()
        s = p1 + a * rr
        e = p1 + b * rr
        for k in range(seg + 1):
            t = k / seg
            q = (1 - t) ** 2 * s + 2 * (1 - t) * t * p1 + t * t * e
            out.append((q.x, q.y))
    return out


def set_uv_planar(ob, scale=1.0, axes=("x", "y")):
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for li, l in enumerate(me.loops):
        co = me.vertices[l.vertex_index].co
        uv.data[li].uv = (getattr(co, axes[0]) * scale, getattr(co, axes[1]) * scale)


# ============================================================================================ shared materials
def mat_get(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def metal_material(name="M_steel", hexcol="C9D1D8", rough=.22, brushed=True):
    mat = mat_get(name)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    sv = nb.node("ShaderNodeMapping", Vector=tc, Scale=(4, 900, 1)).outputs[0]
    br = nb.noise(sv, 1.0, 3, .5)
    n = nb.noise(tc, 30, 4, .6)
    base = nb.ramp(nb.add(nb.mul(br, .6), nb.mul(n, .4)), [(0, srgb(hexcol)), (1, srgb("EEF2F5"))])
    nb.bsdf(**{"Base Color": base, "Metallic": 1.0, "Roughness": nb.add(rough, nb.mul(br, .12 if brushed else 0)),
               "Normal": nb.node("ShaderNodeBump", Height=br, Strength=.15 if brushed else 0, Distance=.0004).outputs[0]})
    return mat


def grape_material(name, c0, c1, bloom=.7):
    mat = mat_get(name)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    rnd = nb.node("ShaderNodeObjectInfo").outputs["Random"]
    n = nb.noise(tc, 120, 4, .6)
    base = nb.ramp(nb.add(nb.mul(n, .5), nb.mul(rnd, .5)), [(0, srgb(c0)), (1, srgb(c1))])
    fog = nb.mapr(nb.noise(tc, 60, 5, .6), .4, .7)
    base = nb.mix(nb.mul(fog, .35 * bloom), base, srgb("B9B6C9"))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.25, nb.mul(fog, .35 * bloom)), "Subsurface Weight": .35,
               "Subsurface Radius": (1, .3, .3), "Subsurface Scale": .004, "Coat Weight": .3, "Coat Roughness": .2,
               "Sheen Weight": .3 * bloom, "Sheen Roughness": .5})
    return mat


def emission_mask_material(name="M_mask"):
    mat = mat_get(name)
    nb = NB(mat)
    lw = nb.node("ShaderNodeLayerWeight", Blend=.5)
    em = nb.node("ShaderNodeEmission", Color=(1, 1, 1, 1), Strength=1.0)
    o = nb.node("ShaderNodeOutputMaterial")
    nb.nt.links.new(em.outputs[0], o.inputs["Surface"])
    return mat


def grape_bunch(c, name, at, mat, n=26, seed=4, r=.0105, spread=(.05, .085), rot=0.0, stem_mat=None):
    """A bunch of grapes lying on its side (top view): tapered cluster, one object, plus a woody stem."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    placed = []
    tries = 0
    while len(placed) < n and tries < 2000:
        tries += 1
        t = rnd.random()
        w = spread[0] * (1 - .75 * t) + .004
        x = rnd.uniform(-w, w)
        y = spread[1] * (.5 - t) * 2
        rr = r * rnd.uniform(.85, 1.08)
        ok = all((Vector((x, y)) - Vector((px, py))).length > (rr + pr) * .92 for px, py, pr, _ in placed)
        if not ok:
            continue
        z = rr * .9 + (1 - abs(x) / (w + 1e-6)) * r * .8 * rnd.random()
        placed.append((x, y, rr, z))
    for x, y, rr, z in placed:
        g = ellipsoid(rr, rr * 1.08, rr, 3, seed=rnd.randint(0, 99), lump=.02)
        xform(g, loc=(x, y, z), rot=(0, 0, rnd.uniform(0, 360)))
        bm_join(bm, g)
    xform(bm, rot=(0, 0, rot))
    ob = mesh_object(name, bm, mat, c, subsurf=1)
    ob.location = at
    if stem_mat:
        a = math.radians(rot)
        pts = [(0, spread[1] * 1.0, .02), (.006, spread[1] * 1.15, .024), (.0, spread[1] * 1.32, .02), (-.012, spread[1] * 1.42, .014)]
        pts = [(p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a), p[2]) for p in pts]
        st = mesh_object(name + "_stem", tube_bm(spline(pts, 5), lambda t: .0032 * (1 - .4 * t), 8), stem_mat, c, subsurf=1)
        st.location = at
    return ob


def stem_material():
    return simple_material("M_stem", "6B5232", .7, var="8A6B3E", bump_scale=300)


def linen(c, name, at, size, rot=0.0, folds=3, mat=None, seed=0):
    bm = bmesh.new()
    nu, nv = 48, 36
    tw, th = size
    vs = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            x, y = (i / nu - .5) * tw, (j / nv - .5) * th
            z = .002 + .005 * max(0, math.sin(i / nu * math.pi * folds + j * .12 + seed)) + .002 * noise.noise(Vector((x * 18, y * 18, seed)))
            vs[i, j] = bm.verts.new((x, y, z))
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    ob = mesh_object(name, bm, mat or towel_material(), c, subsurf=1)
    ob.location = at
    ob.rotation_euler.z = math.radians(rot)
    me = ob.data
    uv = me.uv_layers.new(name="UVMap")
    for li, l in enumerate(me.loops):
        co = me.vertices[l.vertex_index].co
        uv.data[li].uv = (co.x / tw + .5, co.y / th + .5)
    return ob


def knife(c, name, at, rot, blade_len=.16, blade_w=.026, handle_len=.11, kind="chef", blade_mat=None, handle_mat=None):
    """Top view knife lying flat: blade towards +X before rotation."""
    bm_out = []
    L, W = blade_len, blade_w
    if kind == "cleaver":
        pts = [(0, -W * .5), (L, -W * .5), (L, W * .5), (0, W * .5)]
        pts = round_outline(pts, .006)
        t = .004
    elif kind == "cheese":
        pts = [(0, -W * .35), (L * .78, -W * .5), (L, -W * .15), (L * .94, 0), (L * 1.0, W * .18), (L * .86, W * .42), (0, W * .42)]
        pts = round_outline(pts, .003)
        t = .0025
    else:   # chef / fish knife: straight spine, curved edge to the tip
        pts = [(0, -W * .5)] + [(L * k / 10, -W * .5 + W * .95 * (k / 10) ** 3) for k in range(1, 11)] + [(L * .9, W * .42), (0, W * .5)]
        t = .0022
    blade = outline_slab(pts, t, bevel=.0009, segs=2)
    if kind == "cheese":     # holes in the blade
        pass
    ob = mesh_object(name + "_blade", blade, blade_mat or metal_material(), c, subsurf=0)
    ob.location = at + Vector((0, 0, .0035))
    ob.rotation_euler.z = math.radians(rot)
    hw = W * (.55 if kind != "cleaver" else .4)
    hp = round_outline([(-handle_len, -hw * .5), (0, -hw * .5), (0, hw * .5), (-handle_len, hw * .5)], hw * .45, 6)
    hb = outline_slab(hp, hw * .8, bevel=hw * .3, segs=4)
    # rivets
    h = mesh_object(name + "_handle", hb, handle_mat or wood_material("M_knife_handle", light="7A4A2A", dark="3E2414", plank=10, seam=False, scale=6), c, subsurf=1)
    h.location = at
    h.rotation_euler.z = math.radians(rot)
    rv = bmesh.new()
    for k in (.25, .55, .82):
        s = ellipsoid(.0032, .0032, .0012, 2)
        xform(s, loc=(-handle_len * k, 0, hw * .8))
        bm_join(rv, s)
    r = mesh_object(name + "_rivets", rv, metal_material("M_rivet", "D7DCE0", .18, False), c, subsurf=1)
    r.location = at
    r.rotation_euler.z = math.radians(rot)
    return [ob.name, h.name, r.name]


# ============================================================================================ 2D helpers
def blank(w, h, rgb=(0, 0, 0), a=0.0):
    im = np.zeros((h, w, 4), np.float32)
    im[..., 0], im[..., 1], im[..., 2], im[..., 3] = rgb[0], rgb[1], rgb[2], a
    return im


def soft_shadow(dst, mask, x, y, r=12, dx=8, dy=10, strength=.45):
    pp.shadow(dst, mask, x, y, r, dx, dy, strength)


def place(dst, src, cx, cy, w=None, h=None, rot=0):
    """Pastes `src` centred at (cx, cy) (pixels, top-left origin), resized to w x h (keeps aspect if one is None)."""
    if rot:
        src = np.rot90(src, rot).copy()
    sh, sw = src.shape[:2]
    if w and not h:
        h = int(round(sh * w / sw))
    if h and not w:
        w = int(round(sw * h / sh))
    if w and h and (w != sw or h != sh):
        src = img_resize(src, int(w), int(h))
    sh, sw = src.shape[:2]
    over(dst, src, int(round(cx - sw / 2)), int(round(cy - sh / 2)))
    return src


def load(name):
    return img_load(os.path.join(OUT, name))


def save_png(a, name):
    img_save(a, os.path.join(OUT, name))
    return os.path.join(OUT, name)


def srgb_f(hexs):
    """sRGB hex -> 0..1 sRGB floats (what the PNG stores)."""
    return tuple(int(hexs[i:i + 2], 16) / 255 for i in (0, 2, 4))


def manifest_update(key, data):
    p = os.path.join(OUT, "manifest.json")
    m = {}
    if os.path.exists(p):
        with open(p) as f:
            m = json.load(f)
    m[key] = data
    with open(p, "w") as f:
        json.dump(m, f, indent=2, sort_keys=True)
    return m


# ============================================================================================ QUEIJARIA
CHEESES = ["minas", "prato", "brie", "azul", "parmesao"]
CHEESE_R = .1           # wheel radius (m): 0.2 m diameter in a 0.235 m frame = 85 %
CHEESE_FRAME = .235


def wheel_profile(R, H, bev, dome=0.0, bulge=0.0, top_rings=64, top_bev=None):
    tb = top_bev if top_bev is not None else bev
    prof = [(0.0, 0.0)]
    for i in range(1, 10):
        prof.append(((R - bev) * i / 10, 0.0))
    for i in range(0, 9):
        a = -math.pi / 2 + math.pi / 2 * i / 8
        prof.append((R - bev + bev * math.cos(a), bev + bev * math.sin(a)))
    for i in range(1, 8):
        t = i / 8
        z = bev + (H - bev - tb) * t
        prof.append((R + bulge * math.sin(math.pi * (1 - t) ** 1.4), z))
    for i in range(0, 13):
        a = math.pi / 2 * i / 12
        prof.append((R - tb + tb * math.cos(a), H - tb + tb * math.sin(a)))
    rt = R - tb
    for i in range(1, top_rings):
        r = rt * (1 - i / top_rings)
        prof.append((r, H + dome * (1 - (r / rt) ** 2)))
    prof.append((0.0, H + dome))
    out = []
    for p in prof:          # drop duplicates
        if not out or (abs(p[0] - out[-1][0]) > 1e-7 or abs(p[1] - out[-1][1]) > 1e-7):
            out.append(p)
    return out


def lathe_arc(profile, a0, span, seg, lean=0.0, H=1.0, apex_back=0.0):
    """Revolves `profile` [(r, z)] over the arc centred on a0 (deg) of `span` degrees (the rest is a cut wedge).
    lean: extra degrees the cut faces open at the top (so they show from above). Caps get material index 1."""
    bm = bmesh.new()
    mid = math.radians(a0)
    rows = []
    for (r, z) in profile:
        sp = math.radians(span) - 2 * math.radians(lean) * max(0.0, min(1.0, z / H))
        if r < 1e-7:
            v = bm.verts.new((0, 0, z))
            rows.append([v] * (seg + 1))
            continue
        row = []
        for j in range(seg + 1):
            th = mid + (j / seg - .5) * sp
            row.append(bm.verts.new((r * math.cos(th), r * math.sin(th), z)))
        rows.append(row)
    for i in range(len(rows) - 1):
        for j in range(seg):
            q = [rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]]
            u = []
            for v in q:
                if v not in u:
                    u.append(v)
            if len(u) >= 3:
                try:
                    bm.faces.new(u)
                except ValueError:
                    pass
    caps = []
    for j in (0, seg):
        vs = []
        for row in rows:
            if row[j] not in vs:
                vs.append(row[j])
        try:
            f = bm.faces.new(vs)
            f.material_index = 1
            caps.append(f)
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if caps:
        res = bmesh.ops.triangulate(bm, faces=caps, quad_method="BEAUTY", ngon_method="BEAUTY")
        for f in res["faces"]:
            f.material_index = 1
    return bm


def wheel_bm(R, H, bev, dome=0.0, bulge=0.0, seg=192, top_rings=64, lump=0.0, seed=0, top_bev=None, cut=None):
    """cut = (a0, width, lean): leave out a wedge centred on a0 (deg), its faces leaning open by `lean` deg."""
    prof = wheel_profile(R, H, bev, dome, bulge, top_rings, top_bev)
    if cut:
        a0, width, lean = cut
        bm = lathe_arc(prof, a0 + 180, 360 - width, seg, lean, H)
    else:
        bm = lathe_bm(prof, seg)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    if lump:
        off = Vector((seed * 3.3, seed * 1.1, seed * 2.7))
        for v in bm.verts:
            p = v.co
            k = 1 + lump * noise.fractal(Vector((p.x * 14, p.y * 14, p.z * 6)) + off, .6, 2.0, 3)
            v.co = Vector((p.x * k, p.y * k, p.z * (1 + (k - 1) * .6)))
    return bm


def dimples(bm, holes, H, name="eye"):
    le = bm.verts.layers.float.get(name) or bm.verts.layers.float.new(name)
    for v in bm.verts:
        if v.co.z < H * .7:
            continue
        for cx, cy, r, d in holes:
            dd = math.hypot(v.co.x - cx, v.co.y - cy)
            t = dd / r
            if t < 1:
                v.co.z -= d * math.sqrt(1 - t * t)
                v[le] = max(v[le], 1.0)
            elif t < 1.35:
                v.co.z += d * .12 * math.sin(math.pi * (t - 1) / .35)
                v[le] = max(v[le], .35 * (1.35 - t) / .35)
    return bm


def cheese_material(kind):
    mat = mat_get("M_cheese_" + kind)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    geo = nb.node("ShaderNodeNewGeometry")
    nz = nb.sep(geo.outputs["Normal"])[2]
    rad = nb.math("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    n_b = nb.noise(tc, 18, 5, .6, .3)
    n_m = nb.noise(tc, 80, 6, .6)
    n_f = nb.noise(tc, 600, 6, .65)
    kw = {"Subsurface Weight": .3, "Subsurface Radius": (1, .8, .5), "Subsurface Scale": .004, "Specular IOR Level": .45}
    R = CHEESE_R
    if kind == "minas":
        # fresh white cheese; the basket-mould weave is pressed in hardest near the rim
        u = nb.mul(nb.add(x, y), .7071 * 2 * math.pi / .0085)
        v = nb.mul(nb.math("SUBTRACT", x, y), .7071 * 2 * math.pi / .0085)
        wv = nb.mul(nb.math("SINE", nb.add(u, nb.mul(n_b, 1.5))), nb.math("SINE", nb.add(v, nb.mul(n_b, 1.5))))
        cells = nb.mapr(wv, -.1, .9)
        holes = nb.mapr(wv, -.45, -.95)
        edge = nb.mapr(rad, R * .35, R * .92)
        fade = nb.mul(nb.add(nb.mul(edge, .75), .25), nb.mapr(nb.add(n_b, nb.mul(n_m, .3)), .1, .35))
        base = nb.ramp(nb.add(nb.mul(n_b, .7), nb.mul(n_f, .3), -.15), [(0, srgb("FFFFFF")), (1, srgb("F7F7F3"))])
        base = nb.mix(nb.mul(nb.mul(holes, fade), .75), base, srgb("D3D2CB"))
        base = nb.mix(nb.mul(nb.mapr(rad, R * .86, R * 1.02), .3), base, srgb("F4F0E2"))
        h = nb.add(nb.mul(cells, .45), nb.mul(holes, -1.0), nb.mul(n_f, .2))
        h = nb.mul(h, fade)
        kw.update({"Base Color": base, "Roughness": nb.add(.38, nb.mul(holes, .3)), "Coat Weight": .3, "Coat Roughness": .22,
                   "Subsurface Weight": .25, "Subsurface Radius": (1, 1, 1), "Specular IOR Level": .5,
                   "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.85, Distance=.0018).outputs[0]})
    elif kind == "prato":
        eye = nb.node("ShaderNodeAttribute", _attribute_name="eye").outputs["Factor"]
        base = nb.ramp(nb.add(nb.mul(n_b, .7), nb.mul(n_m, .3), -.12, nb.mul(nb.mapr(rad, R * .75, R * 1.0), .35)),
                       [(0, srgb("FBC94E")), (.5, srgb("F5B23A")), (1, srgb("E39424"))])
        base = nb.mix(nb.mapr(eye, .5, 1.0), base, srgb("E79B2C"))
        h = nb.add(nb.mul(n_f, .25), nb.mul(n_m, .2))
        kw.update({"Base Color": base, "Roughness": .3, "Coat Weight": .65, "Coat Roughness": .12, "Subsurface Weight": .35,
                   "Subsurface Radius": (1, .55, .2), "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.12, Distance=.001).outputs[0]})
    elif kind in ("brie", "brie_paste"):
        if kind == "brie":
            mott = nb.mapr(nb.add(n_b, nb.mul(n_m, .4)), .52, .8)
            base = nb.ramp(nb.add(nb.mul(n_m, .6), nb.mul(n_f, .4), -.1), [(0, srgb("FFFFFB")), (1, srgb("F7F3EA"))])
            base = nb.mix(nb.mul(mott, .4), base, srgb("EEDCBC"))
            base = nb.mix(nb.mul(nb.mapr(nz, .7, .2), .35), base, srgb("E8D6B6"))
            fuzz = nb.noise(tc, 1800, 3, .6)
            h = nb.add(nb.mul(fuzz, .6), nb.mul(n_m, .5), nb.mul(mott, .3))
            kw.update({"Base Color": base, "Roughness": .85, "Sheen Weight": .8, "Sheen Roughness": .35,
                       "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.35, Distance=.0008).outputs[0]})
        else:
            base = nb.ramp(nb.add(nb.mul(n_m, .6), nb.mul(n_f, .3), -.1), [(0, srgb("F8E7AE")), (1, srgb("EDCF83"))])
            kw.update({"Base Color": base, "Roughness": .28, "Coat Weight": .4, "Coat Roughness": .1, "Subsurface Weight": .5,
                       "Subsurface Radius": (1, .7, .3),
                       "Normal": nb.node("ShaderNodeBump", Height=n_m, Strength=.1, Distance=.001).outputs[0]})
    elif kind == "azul":
        # wheel cut flat across the top: veined paste inside, natural grey-ochre rind on the rounded edge
        inner = nb.mul(nb.mapr(rad, R * .86 + .0, R * .80), nb.mapr(nz, .9, .97))
        inner = nb.mapr(nb.add(inner, nb.mul(nb.math("SUBTRACT", n_m, .5), .5)), .35, .6)
        warp = nb.node("ShaderNodeTexNoise", Vector=tc, Scale=30, Detail=4.0, Roughness=.6).outputs["Color"]
        dn = nb.node("ShaderNodeVectorMath", Vector=warp, _operation="MULTIPLY_ADD")
        dn.inputs[1].default_value = (.06, .06, .06)
        nb.nt.links.new(tc, dn.inputs[2])
        dv = nb.node("ShaderNodeVectorMath", Vector=dn.outputs[0], _operation="SUBTRACT")
        dv.inputs[1].default_value = (.03, .03, .03)
        dv = dv.outputs[0]
        vor = nb.node("ShaderNodeTexVoronoi", Vector=dv, Scale=38, Randomness=1.0, _feature="DISTANCE_TO_EDGE").outputs["Distance"]
        veins = nb.mul(nb.mapr(vor, .085, .0), nb.mapr(nb.noise(tc, 22, 4), .3, .48))
        halo = nb.mul(nb.mapr(vor, .22, .02), nb.mapr(nb.noise(tc, 22, 4), .3, .48))
        pock = nb.mapr(nb.noise(dv, 30, 7, .72, .4), .53, .64)
        blue = nb.math("MAXIMUM", veins, pock)
        speck = nb.mapr(nb.noise(tc, 260, 4, .7), .64, .72)
        blue = nb.math("MAXIMUM", blue, nb.mul(speck, .75))
        paste = nb.ramp(n_f, [(0, srgb("F7F2E1")), (1, srgb("ECE4CB"))])
        vein_c = nb.ramp(nb.add(nb.mul(n_m, .7), nb.mul(n_f, .3)), [(0, srgb("1C4458")), (.5, srgb("2C6676")), (1, srgb("4E8A80"))])
        paste = nb.mix(nb.mul(halo, .5), paste, srgb("BCD0C4"))
        paste = nb.mix(blue, paste, vein_c)
        mold = nb.mapr(nb.noise(tc, 70, 5, .65), .55, .7)
        rind = nb.ramp(nb.add(nb.mul(n_m, .6), nb.mul(n_b, .4)), [(0, srgb("D9D8CC")), (.6, srgb("C4C2AE")), (1, srgb("A9A386"))])
        rind = nb.mix(nb.mul(mold, .9), rind, srgb("6D8E92"))
        base = nb.mix(inner, rind, paste)
        crumb = nb.noise(tc, 260, 5, .7)
        h = nb.add(nb.mul(crumb, .5), nb.mul(blue, -.8), nb.mul(nb.math("SUBTRACT", 1.0, inner), nb.mul(n_m, .6)))
        kw.update({"Base Color": base, "Roughness": nb.add(.62, nb.mul(blue, -.2)), "Subsurface Weight": .25,
                   "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.4, Distance=.001).outputs[0]})
    elif kind in ("parmesao", "parmesao_paste"):
        # opened drum: rough crystalline paste on top, a thick golden-straw rind ring around it
        gran = nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=520, Randomness=1.0, _feature="F1").outputs["Distance"]
        grain = nb.mapr(gran, .3, .05)
        crys = nb.mapr(nb.noise(tc, 700, 2, .5), .66, .72)
        flake = nb.mapr(nb.node("ShaderNodeTexVoronoi", Vector=nb.add(tc, nb.mul(n_m, .01)) if False else tc, Scale=70, Randomness=1.0, _feature="DISTANCE_TO_EDGE").outputs["Distance"], .04, .0)
        paste = nb.ramp(nb.add(nb.mul(n_m, .6), nb.mul(n_f, .3), nb.mul(grain, .2)), [(0, srgb("FBEBB8")), (.5, srgb("F2D78E")), (1, srgb("E3BE6A"))])
        paste = nb.mix(nb.mul(crys, .8), paste, srgb("FFF8E2"))
        paste = nb.mix(nb.mul(nb.mul(flake, nb.mapr(nb.noise(tc, 30, 3), .45, .65)), .25), paste, srgb("C9A04E"))
        h_p = nb.add(nb.mul(grain, .6), nb.mul(n_f, .5), nb.mul(flake, -.9), nb.mul(crys, .3))
        if kind == "parmesao_paste":
            kw.update({"Base Color": paste, "Roughness": .72, "Subsurface Weight": .1,
                       "Normal": nb.node("ShaderNodeBump", Height=h_p, Strength=.6, Distance=.0012).outputs[0]})
        else:
            ring = nb.mapr(nb.add(rad, nb.mul(nb.math("SUBTRACT", n_m, .5), .004)), R * .8, R * .83)
            outer = nb.mapr(rad, R * .9, R * 1.0)
            rind = nb.ramp(nb.add(nb.mul(n_m, .5), nb.mul(n_f, .3), nb.mul(outer, .6)),
                           [(0, srgb("F2D27A")), (.45, srgb("E6BC5C")), (.8, srgb("CC9C46")), (1, srgb("9C6E2E"))])
            # pin-dot ring stamped in the rind (dots only, no lettering)
            ang = nb.math("ARCTAN2", y, x)
            da = nb.math("SUBTRACT", nb.math("FRACT", nb.mul(ang, 72 / (2 * math.pi))), .5)
            dr = nb.math("SUBTRACT", rad, R * .885)
            dd = nb.math("SQRT", nb.add(nb.mul(nb.mul(da, R * .077), nb.mul(da, R * .077)), nb.mul(dr, dr)))
            dot = nb.mul(nb.mapr(dd, .0013, .0007), nb.mapr(nz, .8, .95))
            rind = nb.mix(nb.mul(dot, .6), rind, srgb("6E4518"))
            base = nb.mix(ring, paste, rind)
            lip = nb.mul(nb.mapr(rad, R * .8, R * .815), nb.mapr(rad, R * .84, R * .825))
            base = nb.mix(nb.mul(lip, .45), base, srgb("9A6A2A"))
            h = nb.add(nb.mul(h_p, nb.math("SUBTRACT", 1.0, ring)), nb.mul(nb.mul(n_m, .6), ring), nb.mul(dot, -.6), nb.mul(lip, -.5), nb.mul(ring, .25))
            kw.update({"Base Color": base, "Roughness": nb.add(.72, nb.mul(ring, -.2)), "Coat Weight": nb.mul(ring, .3), "Coat Roughness": .3,
                       "Subsurface Weight": .1, "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.6, Distance=.0012).outputs[0]})
    nb.bsdf(**kw)
    return mat


def wedge_cutter(H, a0, width, tilt, back=.012, L=.2):
    """Prism removing a wedge pointing at angle a0 (deg); its faces lean outwards by `tilt` so they show from above."""
    a0 = math.radians(a0)
    w = math.radians(width) / 2
    tl = math.radians(tilt)
    d = Vector((math.cos(a0), math.sin(a0), 0))
    bm = bmesh.new()
    lo, hi = -.02, H + .05
    def ring(z, ww, apex_back):
        apex = -d * apex_back
        return [bm.verts.new(apex + Vector((0, 0, z))),
                bm.verts.new(Vector((math.cos(a0 - ww) * L, math.sin(a0 - ww) * L, z))),
                bm.verts.new(Vector((math.cos(a0 + ww) * L, math.sin(a0 + ww) * L, z)))]
    b = ring(lo, w, -.001)
    t = ring(hi, w + tl, back)
    bm.faces.new(b[::-1])
    bm.faces.new(t)
    for i in range(3):
        bm.faces.new((b[i], b[(i + 1) % 3], t[(i + 1) % 3], t[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def build_cheeses():
    o = O("queijaria")
    c = col("Queijaria pieces")
    wipe_collection(c.name)
    R = CHEESE_R
    for i, kind in enumerate(CHEESES):
        at = o + Vector((i * .4, 0, .0005))
        name = "cheese_" + kind
        if kind == "minas":
            bm = wheel_bm(R * .985, .07, .02, dome=.008, bulge=.004, lump=.014, seed=2, top_bev=.022)
        elif kind == "prato":
            bm = wheel_bm(R, .06, .012, dome=.004, lump=.006, seed=5)
            rnd = random.Random(8)
            holes = [(.032, .028, .0075, .004), (-.041, -.012, .0058, .0035), (.004, -.052, .0066, .004), (-.018, .046, .0045, .003), (.055, -.03, .0042, .0025)]
            dimples(bm, holes, .06)
        elif kind == "brie":
            bm = wheel_bm(R, .036, .011, dome=.004, bulge=.0015, lump=.006, seed=9, top_bev=.013, cut=(-50, 38, 11))
        elif kind == "azul":
            bm = wheel_bm(R * .985, .075, .014, dome=0, lump=.008, seed=12, top_bev=.009)
        else:
            bm = wheel_bm(R, .1, .016, dome=.0, bulge=.002, lump=.004, seed=15, top_bev=.016, cut=(-40, 34, 13))
        for nm in ("eye",):
            if bm.verts.layers.float.get(nm) is None:
                bm.verts.layers.float.new(nm)
        ob = mesh_object(name, bm, cheese_material(kind), c, subsurf=0)
        ob.location = at
        if kind == "parmesao":
            ob.data.materials.append(cheese_material("parmesao_paste"))
        if kind == "brie":
            ob.data.materials.append(cheese_material("brie_paste"))
            # ripe paste bulging out of both cut faces
            a0 = math.radians(-50)
            bmo = bmesh.new()
            for side in (-1, 1):
                aa = a0 + side * math.radians(20.5)
                b = ellipsoid(.042, .0062, .0145, 4, seed=3 + side, lump=.08, lump_f=1.5)
                for v in b.verts:            # fatter towards the rind, thin at the centre
                    t = (v.co.x + .042) / .084
                    v.co.y *= .55 + .6 * t
                    v.co.z *= .7 + .4 * t
                xform(b, loc=(.054 * math.cos(aa), .054 * math.sin(aa), .0145), rot=(0, 0, math.degrees(aa)))
                bm_join(bmo, b)
            oz = mesh_object("cheese_brie_ooze", bmo, cheese_material("brie_paste"), c, subsurf=2)
            oz.location = at
    catcher("queijaria", o + Vector((.8, 0, 0)), (2.6, .8))


def render_piece_queijaria(kind):
    ob = bpy.data.objects["cheese_" + kind]
    vis = [ob.name, "Catcher_queijaria"] + (["cheese_brie_ooze"] if kind == "brie" else [])
    return shoot(ob.location, (CHEESE_FRAME, CHEESE_FRAME), (400, 400), os.path.join(OUT, "pz_cheese_%s.png" % kind), True, vis)


def slate_material():
    mat = mat_get("M_slate")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    sv = nb.node("ShaderNodeMapping", Vector=tc, Scale=(1.5, 9, 1)).outputs[0]
    lam = nb.noise(sv, 3.0, 6, .62, .4)              # cleft layers, stretched along X
    n1 = nb.noise(tc, 4, 6, .6, .2)
    n2 = nb.noise(tc, 40, 6, .62)
    n3 = nb.noise(tc, 500, 4, .6)
    t = nb.add(nb.mul(lam, .5), nb.mul(n1, .35), nb.mul(n2, .2), nb.mul(n3, .1), -.1)
    base = nb.ramp(t, [(0, srgb("3D4852")), (.45, srgb("4D5A64")), (.75, srgb("5A6872")), (1, srgb("6C7A82"))])
    chalk = nb.mul(nb.mapr(nb.noise(sv, 7.0, 5, .65), .6, .72), .35)
    base = nb.mix(chalk, base, srgb("8E9AA0"))
    ridges = nb.mapr(lam, .45, .62)
    h = nb.add(nb.mul(ridges, .6), nb.mul(n2, .3), nb.mul(n3, .25))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.55, nb.mul(n2, .2)), "Specular IOR Level": .4,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.22, Distance=.001).outputs[0]})
    return mat


def wedge_bm(R, H, ang, bev=.004, seg=24):
    """Cheese wedge lying on the board: sector outline (apex at origin, opening towards +X), extruded."""
    pts = [(0, 0)]
    for i in range(seg + 1):
        a = math.radians(-ang / 2 + ang * i / seg)
        pts.append((R * math.cos(a), R * math.sin(a)))
    pts = round_outline(pts[:1], .0) if False else pts
    return outline_slab(pts, H, bevel=bev, segs=4)


def wedge_material():
    """Top face: pale cut paste with small eyes; rind band near the arc."""
    mat = mat_get("M_wedge")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    rad = nb.math("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    n_m = nb.noise(tc, 70, 5, .6)
    paste = nb.ramp(n_m, [(0, srgb("F8D978")), (1, srgb("EEC45A"))])
    vor = nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=55, Randomness=1.0, _feature="F1").outputs["Distance"]
    hole = nb.mul(nb.mapr(vor, .16, .1), nb.mapr(nb.node("ShaderNodeTexWhiteNoise", Vector=nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=55, Randomness=1.0, _feature="F1").outputs["Position"]).outputs[0], .7, .75))
    paste = nb.mix(nb.mul(hole, .8), paste, srgb("D9A63C"))
    rind = nb.mapr(nb.add(rad, nb.mul(n_m, .004)), .108, .114)
    base = nb.mix(rind, paste, nb.ramp(n_m, [(0, srgb("E58F2B")), (1, srgb("C9701A"))]))
    h = nb.add(nb.mul(hole, -1.0), nb.mul(nb.noise(tc, 400, 4), .3))
    nb.bsdf(**{"Base Color": base, "Roughness": .45, "Subsurface Weight": .3, "Subsurface Radius": (1, .6, .3), "Subsurface Scale": .004,
               "Coat Weight": nb.mul(rind, .5),
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.35, Distance=.0012).outputs[0]})
    return mat


def build_bench_queijaria():
    o = O("queijaria") + Vector((0, -2.0, 0))
    c = col("Queijaria bench")
    wipe_collection(c.name)
    W, H = BENCH_SIZE
    top = mesh_object("QB_Top", quad_bm(W * 1.04, H * 1.04), slate_material(), c, subsurf=0)
    top.location = o
    # linen with a bunch of red grapes, top-left
    linen(c, "QB_Linen", o + Vector((-.5, .27, 0)), (.36, .26), rot=14, seed=1)
    grape_bunch(c, "QB_Grapes", o + Vector((-.5, .25, .006)), grape_material("M_grape_red", "4A1630", "8A2E4E"), n=28, seed=3,
                rot=-62, stem_mat=stem_material())
    # wooden board with a cheese wedge, top-right
    bw = wood_material("M_qboard", light="E2AE6E", dark="AE6F38", plank=10, seam=False, scale=2.5)
    bm = rounded_slab(.26, .2, .018, .03)
    hb = rounded_slab(.09, .04, .018, .018)
    xform(hb, loc=(-.16, 0, 0))
    bm_join(bm, hb)
    hole = None
    xform(bm, rot=(0, 0, -8))
    mesh_object("QB_Board", bm, bw, c, subsurf=1).location = o + Vector((.52, .25, 0))
    wd = mesh_object("QB_Wedge", wedge_bm(.12, .05, 40, bev=.007), wedge_material(), c, subsurf=1)
    wd.location = o + Vector((.47, .22, .018))
    wd.rotation_euler.z = math.radians(20)
    g2 = grape_bunch(c, "QB_Grapes2", o + Vector((.6, .33, .018)), grape_material("M_grape_red", "4A1630", "8A2E4E"), n=5, seed=8,
                     spread=(.02, .02), rot=30)
    # cheese knife, bottom-left
    kn = knife(c, "QB_Knife", o + Vector((-.47, -.27, 0)), 24, blade_len=.2, blade_w=.044, handle_len=.13, kind="cheese",
               blade_mat=metal_material("M_steel_q", "9EA8B0", .28))
    bl = bpy.data.objects[kn[0]]
    hb = bmesh.new()                     # holes faked with discs of the counter's own slate
    for hx, hy in ((.06, .002), (.105, .004), (.15, .002)):
        d = lathe_bm([(0, 0), (.0072, 0), (.0075, .0003), (0, .0003)], 32)
        xform(d, loc=(hx, hy, .0026))
        bm_join(hb, d)
    ho = mesh_object("QB_KnifeHoles", hb, slate_material(), c, subsurf=0)
    ho.location, ho.rotation_euler = bl.location.copy(), bl.rotation_euler.copy()
    # small honey dish with dipper, bottom-right
    prof = [(0, 0), (.03, 0), (.045, .006), (.05, .022), (.047, .024), (.042, .01), (.03, .006), (0, .006)]
    dish = mesh_object("QB_Dish", lathe_bm(spline(prof, 3), 48), simple_material("M_qdish", "1F8F85", .25, coat=.6, var="25A193"), c, subsurf=1)
    dish.location = o + Vector((.5, -.29, 0))
    honey = lathe_bm([(0, .014), (.038, .014), (.043, .016), (0, .0165)], 48)
    mesh_object("QB_Honey", honey, honey_material(), c, subsurf=1).location = dish.location
    # walnuts scattered near the dish
    rnd = random.Random(4)
    wbm = bmesh.new()
    for k, (wx, wy) in enumerate(((.39, -.31), (.42, -.25), (.34, -.28), (.60, -.2))):
        w = walnut_bm(seed=k)
        xform(w, loc=(wx, wy, 0), rot=(0, 0, rnd.uniform(0, 360)))
        bm_join(wbm, w)
    mesh_object("QB_Walnuts", wbm, walnut_material(), c, subsurf=1).location = o


def honey_material():
    mat = mat_get("M_honey")
    nb = NB(mat)
    nb.bsdf(**{"Base Color": srgb("E08A12"), "Roughness": .08, "Coat Weight": 1.0, "Coat Roughness": .03,
               "Subsurface Weight": .25, "Subsurface Radius": (1, .45, .1), "Subsurface Scale": .004})
    return mat


def walnut_bm(seed=0, r=.021):
    bm = ellipsoid(r, r * 1.2, r * .85, 4, seed=seed)
    off = Vector((seed * 4.1, seed, 0))
    for v in bm.verts:
        p = v.co
        k = 1 - .12 * abs(noise.noise(p * 260 + off)) - .05 * abs(noise.noise(p * 600 + off))
        seam = math.exp(-(p.x / .0016) ** 2) * .002
        v.co = Vector((p.x * k, p.y * k, max(0.0, (p.z + r * .85) * k - seam)))
    return bm


def walnut_material():
    return simple_material("M_walnut", "B98450", .7, var="8E5D33", bump_scale=500)


def build_rack_queijaria():
    """Mockup only: the dark wood ageing rack (3x3, 272 px cells -> 0.136 m), frame 856 px."""
    o = O("queijaria") + Vector((0, -4.0, 0))
    c = col("Queijaria parts")
    wipe_collection(c.name)
    cell = 272 / MPX
    side = cell * 3
    dark = wood_material("M_rack_frame", light="7A4E2A", dark="4A2D17", plank=.04, seam=True, scale=2.0)
    back = wood_material("M_rack_back", light="4A3220", dark="2C1D12", plank=.045, along="Y", seam=True, scale=2.0)
    shelf = wood_material("M_rack_shelf", light="C58C4E", dark="94602E", plank=10, seam=False, scale=3.0)
    f = rounded_slab(side + 40 / MPX, side + 40 / MPX, .02, 20 / MPX)
    mesh_object("QR_Frame", f, dark, c, subsurf=0).location = o
    b = rounded_slab(side + 14 / MPX, side + 14 / MPX, .022, 10 / MPX)
    mesh_object("QR_Back", b, back, c, subsurf=0).location = o + Vector((0, 0, .001))
    sb = bmesh.new()
    for r in range(3):
        s = rounded_slab(side + 10 / MPX, 14 / MPX, .012, 5 / MPX)
        xform(s, loc=(0, side / 2 - (r + 1) * cell + 7 / MPX, 0))
        bm_join(sb, s)
    mesh_object("QR_Shelves", sb, shelf, c, subsurf=0).location = o + Vector((0, 0, .023))
    # cheese crate (285 px)
    cr = 285 / MPX
    crate_m = wood_material("M_crate", light="D9A469", dark="B07A42", plank=.035, seam=True, scale=2.0)
    inner_m = wood_material("M_crate_in", light="F0D29C", dark="DDB57A", plank=.035, seam=True, scale=2.0)
    bm = rounded_slab(cr, cr, .03, 14 / MPX)
    mesh_object("QR_Crate", bm, crate_m, c, subsurf=0).location = o + Vector((.7, 0, 0))
    bm = rounded_slab(cr - 18 / MPX, cr - 18 / MPX, .031, 10 / MPX)
    mesh_object("QR_CrateIn", bm, inner_m, c, subsurf=0).location = o + Vector((.7, 0, .001))
    catcher("queijaria", o + Vector((.4, 0, 0)), (2.0, 1.0), "Catcher_qparts")


def render_parts_queijaria():
    o = O("queijaria") + Vector((0, -4.0, 0))
    s = 900 / MPX
    a = shoot(o, (s, s), (900, 900), os.path.join(OUT, "mockup_part_rack.png"), True, ["QR_Frame", "QR_Back", "QR_Shelves", "Catcher_qparts"])
    s2 = 320 / MPX
    b = shoot(o + Vector((.7, 0, 0)), (s2, s2), (320, 320), os.path.join(OUT, "mockup_part_crate.png"), True, ["QR_Crate", "QR_CrateIn", "Catcher_qparts"])
    return [a, b]


def mockup_queijaria():
    bench = load("pz_bench_queijaria.png")
    bench[..., 3] = 1
    rack = load("mockup_part_rack.png")
    place(bench, rack, 478, 450)
    cell = 272
    side = cell * 3
    rack_kinds = [["prato", None, "azul"], [None, "azul", None], ["azul", "brie", None]]
    for r in range(3):
        for cc in range(3):
            k = rack_kinds[r][cc]
            if not k:
                continue
            cx = 478 - side / 2 + (cc + .5) * cell
            cy = 450 - (side / 2 - (r + .5) * cell + 4)
            place(bench, load("pz_cheese_%s.png" % k), cx, cy, int(cell * .78), int(cell * .78))
    crate = load("mockup_part_crate.png")
    kinds = ["prato", "brie", "azul", "minas", "parmesao"]
    for k in range(4):
        cx = 946 + 634 * (.27 if k % 2 == 0 else .73)
        cy = 450 - (20 + (.5 - k // 2) * (285 + 16))
        place(bench, crate, cx, cy)
        place(bench, load("pz_cheese_%s.png" % kinds[k]), cx, cy, int(285 * .72), int(285 * .72))
    bench[..., 3] = 1
    return save_png(bench, "mockup_queijaria.png")



# ============================================================================================ ACOUGUE
TILE_SRC = os.path.join(OUT, "_src")


def pnoise(w, h, seed, fmin, fmax, beta=1.0, size=(1.0, 1.0), stretch=1.0):
    """Perfectly tileable band-limited noise (w x h), 0..1. Frequencies in cycles per metre of a tile of `size`;
    stretch > 1 elongates features along X."""
    rng = np.random.default_rng(seed)
    kx = np.fft.fftfreq(w) * w / size[0]
    ky = np.fft.fftfreq(h) * h / size[1]
    KX, KY = np.meshgrid(kx, ky)
    k = np.sqrt((KX * stretch) ** 2 + KY ** 2)
    amp = np.where((k >= fmin) & (k <= fmax), 1.0 / np.maximum(k, 1e-3) ** beta, 0.0)
    spec = amp * np.exp(1j * rng.uniform(0, 2 * np.pi, KX.shape))
    f = np.real(np.fft.ifft2(spec))
    lo, hi = np.percentile(f, 1), np.percentile(f, 99)
    return np.clip((f - lo) / (hi - lo), 0, 1).astype(np.float32)


def save_data_image(name, chans):
    """chans: 4 arrays (h, w) -> float image (Non-Color) saved as EXR, reloaded for the shader."""
    os.makedirs(TILE_SRC, exist_ok=True)
    h, w = chans[0].shape
    a = np.stack(chans, -1)[::-1].astype(np.float32)
    path = os.path.join(TILE_SRC, name + ".exr")
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    im.pixels.foreach_set(a.ravel())
    im.filepath_raw = path
    im.file_format = "OPEN_EXR"
    im.save()
    bpy.data.images.remove(im)
    im = bpy.data.images.load(path)
    im.name = name
    im.colorspace_settings.name = "Non-Color"
    return im


MEAT_T = .16      # metres per meat tile
FAT_T = (.16, .04)


def meat_fields():
    W = H = 512
    sz = (MEAT_T, MEAT_T)
    lines = pnoise(W, H, 11, 22, 60, 1.2, sz, stretch=2.8)
    ridge = 1 - np.abs(lines - .5) * 2
    patch = pnoise(W, H, 12, 8, 25, 1.0, sz, stretch=1.5)
    marble = np.clip((ridge - .955) / .03, 0, 1) * np.clip((patch - .42) / .2, 0, 1)
    lines2 = pnoise(W, H, 15, 50, 140, 1.0, sz, stretch=3.5)
    ridge2 = 1 - np.abs(lines2 - .5) * 2
    marble = np.maximum(marble, np.clip((ridge2 - .965) / .025, 0, 1) * np.clip((patch - .5) / .2, 0, 1) * .85)
    fleck = pnoise(W, H, 13, 120, 260, .8, sz)
    marble = np.maximum(marble, np.clip((fleck - .9) / .04, 0, 1) * np.clip((patch - .45) / .25, 0, 1) * .9)
    marble = np.clip(marble, 0, 1)
    fiber = pnoise(W, H, 14, 150, 600, .6, sz, stretch=6.0)
    tone = pnoise(W, H, 16, 6, 30, 1.2, sz, stretch=1.3)
    return [marble, fiber, tone, pnoise(W, H, 17, 40, 120, 1.0, sz)]


def fat_fields():
    W, H = 512, 128
    sz = FAT_T
    layers = pnoise(W, H, 21, 20, 90, 1.0, sz, stretch=7.0)
    tone = pnoise(W, H, 22, 10, 40, 1.0, sz, stretch=2.0)
    vein = 1 - np.abs(pnoise(W, H, 23, 40, 120, 1.0, sz, stretch=3.0) - .5) * 2
    vein = np.clip((vein - .9) / .08, 0, 1) * np.clip((tone - .45) / .2, 0, 1)
    fine = pnoise(W, H, 24, 150, 500, .7, sz, stretch=2.0)
    return [layers, tone, vein, fine]


def meat_material(img):
    mat = mat_get("M_meat_tile")
    nb = NB(mat)
    uv = nb.node("ShaderNodeTexCoord").outputs["UV"]
    tex = nb.node("ShaderNodeTexImage", Vector=uv, _image=img, _extension="REPEAT", _interpolation="Cubic")
    sp = nb.node("ShaderNodeSeparateColor", Color=tex.outputs["Color"]).outputs
    marble, fiber, tone = sp[0], sp[1], sp[2]
    mv = tex.outputs["Alpha"]
    meat = nb.ramp(nb.add(nb.mul(tone, .75), nb.mul(fiber, .35), -.08),
                   [(0, srgb("C93A36")), (.35, srgb("B02A2E")), (.7, srgb("8E1E26")), (1, srgb("6A141C"))])
    fatc = nb.ramp(mv, [(0, srgb("FBEFE3")), (1, srgb("F1DCCB"))])
    halo = nb.mapr(marble, .0, .35)
    base = nb.mix(nb.mul(halo, .45), meat, srgb("E07A6E"))
    base = nb.mix(nb.mapr(marble, .3, .75), base, fatc)
    h = nb.add(nb.mul(marble, .6), nb.mul(fiber, .5), nb.mul(mv, .2))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.32, nb.mul(fiber, .15)), "Coat Weight": .35, "Coat Roughness": .15,
               "Subsurface Weight": .15, "Subsurface Radius": (1, .3, .2), "Subsurface Scale": .003, "Specular IOR Level": .5,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.35, Distance=.0006).outputs[0]})
    return mat


def fat_material(img):
    mat = mat_get("M_fat_tile")
    nb = NB(mat)
    uv = nb.node("ShaderNodeTexCoord").outputs["UV"]
    tex = nb.node("ShaderNodeTexImage", Vector=uv, _image=img, _extension="REPEAT", _interpolation="Cubic")
    sp = nb.node("ShaderNodeSeparateColor", Color=tex.outputs["Color"]).outputs
    layers, tone, vein = sp[0], sp[1], sp[2]
    fine = tex.outputs["Alpha"]
    base = nb.ramp(nb.add(nb.mul(layers, .5), nb.mul(tone, .5), nb.mul(fine, .15), -.05),
                   [(0, srgb("FFF6E6")), (.5, srgb("F8E6CC")), (1, srgb("EDD2B0"))])
    base = nb.mix(nb.mul(vein, .22), base, srgb("ECB4A4"))
    h = nb.add(nb.mul(layers, .4), nb.mul(fine, .4), nb.mul(vein, -.3))
    nb.bsdf(**{"Base Color": base, "Roughness": .38, "Coat Weight": .3, "Coat Roughness": .2, "Subsurface Weight": .4,
               "Subsurface Radius": (1, .85, .6), "Subsurface Scale": .004,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.25, Distance=.0006).outputs[0]})
    return mat


def tile_plane(name, size, mat, at, c):
    """3x3 tiles of `size`, UV = tiles, so the middle tile renders without edge effects."""
    W, H = size
    bm = quad_bm(3 * W, 3 * H)
    ob = mesh_object(name, bm, mat, c, subsurf=0)
    ob.location = at
    me = ob.data
    uv = me.uv_layers.new(name="UVMap")
    for li, l in enumerate(me.loops):
        co = me.vertices[l.vertex_index].co
        uv.data[li].uv = (co.x / W + .5, co.y / H + .5)
    return ob


def build_meat_tiles():
    o = O("acougue")
    c = col("Acougue pieces")
    wipe_collection(c.name)
    mi = save_data_image("meat_fields", meat_fields())
    fi = save_data_image("fat_fields", fat_fields())
    tile_plane("meat_tile", (MEAT_T, MEAT_T), meat_material(mi), o, c)
    tile_plane("fat_tile", FAT_T, fat_material(fi), o + Vector((.8, 0, 0)), c)


def render_tile(obname, size, res, out):
    ob = bpy.data.objects[obname]
    W, H = size
    tmp = os.path.join(TILE_SRC, "_" + out)
    shoot(ob.location, (W * 1.5, H * 1.5), (int(res[0] * 1.5), int(res[1] * 1.5)), tmp, False, [obname])
    a = img_load(tmp)
    x0, y0 = res[0] // 4, res[1] // 4
    a = a[y0:y0 + res[1], x0:x0 + res[0]].copy()
    a[..., 3] = 1
    return save_png(a, out)


def render_piece_acougue(kind):
    if kind == "meat":
        return render_tile("meat_tile", (MEAT_T, MEAT_T), (512, 512), "pz_meat_tile.png")
    return render_tile("fat_tile", FAT_T, (512, 128), "pz_fat_tile.png")


def endgrain_material():
    mat = mat_get("M_endgrain")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    s = .068
    row = nb.math("FLOOR", nb.math("DIVIDE", y, s))
    xo = nb.add(x, nb.mul(nb.math("MODULO", nb.add(row, 100.0), 2.0), s * .5))
    colm = nb.math("FLOOR", nb.math("DIVIDE", xo, s))
    cid = nb.node("ShaderNodeCombineXYZ", X=colm, Y=row, Z=0.0).outputs[0]
    wn = nb.node("ShaderNodeTexWhiteNoise", Vector=cid, _noise_dimensions="3D")
    rnd = wn.outputs["Value"]
    rc = nb.sep(wn.outputs["Color"])
    u = nb.math("SUBTRACT", nb.math("FRACT", nb.math("DIVIDE", xo, s)), .5)
    v = nb.math("SUBTRACT", nb.math("FRACT", nb.math("DIVIDE", y, s)), .5)
    px = nb.add(nb.mul(nb.math("SUBTRACT", rc[0], .5), 2.6), nb.mul(nb.math("SIGN", nb.math("SUBTRACT", rc[0], .5)), .6))
    py = nb.add(nb.mul(nb.math("SUBTRACT", rc[1], .5), 2.6), nb.mul(nb.math("SIGN", nb.math("SUBTRACT", rc[1], .5)), .6))
    dx, dy = nb.math("SUBTRACT", u, px), nb.math("SUBTRACT", v, py)
    d = nb.math("SQRT", nb.add(nb.mul(dx, dx), nb.mul(dy, dy)))
    wob = nb.noise(tc, 60, 3, .5)
    freq = nb.add(6.0, nb.mul(rc[2], 9.0))
    ring = nb.math("SINE", nb.mul(nb.mul(nb.add(d, nb.mul(wob, .06)), 2 * math.pi), freq))
    rings = nb.mapr(ring, .2, 1.0)
    fine = nb.noise(tc, 700, 3, .6)
    tone = nb.ramp(nb.add(nb.mul(rnd, .85), nb.mul(nb.noise(tc, 3, 3), .3), -.1),
                   [(0, srgb("EAC690")), (.3, srgb("DDAE72")), (.6, srgb("C8925A")), (.85, srgb("A36D3C")), (1, srgb("7E4E2A"))])
    base = nb.mix(nb.mul(rings, .45), tone, srgb("7A4826"))
    stain = nb.mapr(nb.noise(tc, 4, 5, .6, .2), .55, .75)
    base = nb.mix(nb.mul(stain, .25), base, srgb("6A3C1E"))
    base = nb.mix(nb.mul(fine, .12), base, srgb("6E4220"))
    seam = nb.mapr(nb.math("MAXIMUM", nb.math("ABSOLUTE", u), nb.math("ABSOLUTE", v)), .491, .5)
    base = nb.mix(nb.mul(seam, .6), base, srgb("5E3519"))
    # knife marks: thin light scratches in a few directions
    scr = None
    for ang, sc in ((.3, 1.0), (-.5, 1.3), (1.2, .8)):
        sv = nb.node("ShaderNodeMapping", Vector=tc, Scale=(5 * sc, 700, 1), Rotation=(0, 0, ang)).outputs[0]
        l = nb.mul(nb.mapr(nb.noise(sv, 1.0, 2, .5), .7, .76), nb.mapr(nb.noise(tc, 6 + sc, 2), .5, .66))
        scr = l if scr is None else nb.math("MAXIMUM", scr, l)
    base = nb.mix(nb.mul(scr, .45), base, srgb("F3D7A8"))
    h = nb.add(nb.mul(rings, .2), nb.mul(fine, .5), nb.mul(seam, -1.2), nb.mul(scr, -.4))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.62, nb.mul(fine, .1)), "Specular IOR Level": .35,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.22, Distance=.001).outputs[0]})
    return mat


def nb_const(v):
    return v


def twine_material():
    mat = mat_get("M_twine")
    nb = NB(mat)
    uv = nb.node("ShaderNodeTexCoord").outputs["UV"]
    u, v, _ = nb.sep(uv)
    tw = nb.math("FRACT", nb.add(nb.mul(u, 1 / .006), nb.mul(v, 2.0)))
    ply = nb.mapr(nb.math("ABSOLUTE", nb.math("SUBTRACT", tw, .5)), .5, .1)
    red = nb.mapr(nb.math("FRACT", nb.add(nb.mul(u, 1 / .012), v)), .5, .52)
    base = nb.mix(red, srgb("F4EEE2"), srgb("C8392F"))
    fuzz = nb.noise(nb.node("ShaderNodeTexCoord").outputs["Object"], 900, 3)
    nb.bsdf(**{"Base Color": nb.mix(nb.mul(nb.math("SUBTRACT", 1.0, ply), .25), base, srgb("8E7A66")), "Roughness": .85,
               "Sheen Weight": .5, "Normal": nb.node("ShaderNodeBump", Height=nb.add(ply, nb.mul(fuzz, .3)), Strength=.6, Distance=.0008).outputs[0]})
    return mat


def leaf_material(name="M_rosemary", c0="35603E", c1="56805A"):
    mat = mat_get(name)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    rnd = nb.node("ShaderNodeObjectInfo").outputs["Random"]
    n = nb.noise(tc, 200, 3)
    base = nb.ramp(nb.add(nb.mul(n, .6), nb.mul(rnd, .4)), [(0, srgb(c0)), (1, srgb(c1))])
    nb.bsdf(**{"Base Color": base, "Roughness": .45, "Coat Weight": .2, "Subsurface Weight": .2, "Subsurface Radius": (.4, 1, .3),
               "Subsurface Scale": .002})
    return mat


def rosemary_bm(L=.14, seed=0, bend=.02):
    rnd = random.Random(seed)
    bm = bmesh.new()
    pts = [(t * L, bend * math.sin(t * 2.4 + seed), .004) for t in [i / 10 for i in range(11)]]
    bm_join(bm, tube_bm(spline(pts, 3), lambda t: .0016 * (1 - .5 * t), 8))
    n = 46
    for i in range(n):
        t = .08 + .9 * i / n
        x, y = t * L, bend * math.sin(t * 2.4 + seed)
        for side in (-1, 1):
            ln = .016 * (1 - .45 * t) * rnd.uniform(.85, 1.1)
            nd = ellipsoid(ln / 2, .0017, .0011, 2)
            ang = side * rnd.uniform(35, 65)
            xform(nd, loc=(ln / 2 * .9, 0, 0), rot=(0, 0, 0))
            xform(nd, rot=(rnd.uniform(-15, 15), rnd.uniform(-12, 4), ang), loc=(x, y, .0055 + rnd.uniform(0, .003)))
            bm_join(bm, nd)
    return bm


def build_bench_acougue():
    o = O("acougue") + Vector((0, -2.0, 0))
    c = col("Acougue bench")
    wipe_collection(c.name)
    W, H = BENCH_SIZE
    top = mesh_object("AB_Top", quad_bm(W * 1.04, H * 1.04), endgrain_material(), c, subsurf=0)
    top.location = o
    # butcher paper, top-left, with rosemary on it
    pap = bmesh.new()
    nu, nv = 40, 30
    pw, ph = .4, .3
    vs = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            x, y = (i / nu - .5) * pw, (j / nv - .5) * ph
            z = .0015 + .003 * noise.fractal(Vector((x * 9, y * 9, 1.3)), .6, 2, 3) ** 2
            corner = max(0.0, (x / pw + .5) + (-(y / ph) + .5) - 1.55)
            z += corner * .06
            vs[i, j] = pap.verts.new((x, y, z))
    for i in range(nu):
        for j in range(nv):
            pap.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    paper = mesh_object("AB_Paper", pap, paper_material(), c, subsurf=1)
    paper.location = o + Vector((-.5, .27, 0))
    paper.rotation_euler.z = math.radians(-9)
    rm = leaf_material()
    for k, (rx, ry, rr, L) in enumerate(((-.52, .3, -20, .16), (-.46, .24, -5, .13), (-.58, .22, 25, .12))):
        r = mesh_object("AB_Rosemary%d" % k, rosemary_bm(L, k), rm, c, subsurf=1)
        r.location = o + Vector((rx, ry, .003))
        r.rotation_euler.z = math.radians(rr)
    # twine coil, top-right
    pts = []
    turns = 3.4
    for i in range(int(turns * 48) + 1):
        a = 2 * math.pi * i / 48
        rr = .052 + .006 * a / (2 * math.pi) + .002 * math.sin(a * 3)
        pts.append((rr * math.cos(a), rr * .92 * math.sin(a), .003 + .0012 * math.sin(a * .5) ** 2 + .0006 * (a / (2 * math.pi))))
    a_end = 2 * math.pi * turns
    for i in range(1, 12):
        t = i / 11
        pts.append((pts[-1][0] - .012 * t - .004, pts[-1][1] - .014, .003))
    tw = mesh_object("AB_Twine", tube_bm(pts, .0026, 10), twine_material(), c, subsurf=1)
    tw.location = o + Vector((.52, .27, 0))
    # coarse salt in a small wooden bowl, bottom-left, plus a few crystals
    prof = [(0, 0), (.04, 0), (.055, .008), (.062, .028), (.058, .031), (.05, .012), (.036, .007), (0, .007)]
    bowl = mesh_object("AB_Bowl", lathe_bm(spline(prof, 3), 48), wood_material("M_saltbowl", light="8E5A32", dark="5E3A1E", plank=10, seam=False, scale=5), c, subsurf=1)
    bowl.location = o + Vector((-.5, -.28, 0))
    rnd = random.Random(7)
    sb = bmesh.new()
    def crystal(x, y, z, s):
        cb = bmesh.new()
        bmesh.ops.create_cube(cb, size=1)
        bmesh.ops.bevel(cb, geom=cb.edges[:], offset=.12, segments=2, affect="EDGES")
        xform(cb, scale=(s * rnd.uniform(.8, 1.2), s * rnd.uniform(.8, 1.2), s * rnd.uniform(.6, 1.0)))
        xform(cb, loc=(x, y, z), rot=(rnd.uniform(0, 360), rnd.uniform(0, 360), rnd.uniform(0, 360)))
        bm_join(sb, cb)
    for i in range(260):
        a, r = rnd.uniform(0, 6.28), .05 * math.sqrt(rnd.random())
        crystal(-.5 + r * math.cos(a), -.28 + r * math.sin(a), .012 + .012 * (1 - (r / .05) ** 2) + rnd.uniform(0, .003), rnd.uniform(.0035, .006))
    for i in range(30):
        crystal(rnd.uniform(-.44, -.3), rnd.uniform(-.34, -.2), .002, rnd.uniform(.003, .005))
    for i in range(14):
        crystal(rnd.uniform(-.6, -.4), rnd.uniform(-.2, -.14), .002, rnd.uniform(.003, .0045))
    mesh_object("AB_Salt", sb, salt_material(), c, subsurf=0).location = o
    # peppercorns
    pb = bmesh.new()
    for i in range(18):
        p = ellipsoid(.0035, .0035, .0032, 2, seed=i, lump=.12, lump_f=9)
        xform(p, loc=(rnd.uniform(-.36, -.22), rnd.uniform(-.33, -.24), .003))
        bm_join(pb, p)
    mesh_object("AB_Pepper", pb, simple_material("M_pepper", "2B1D16", .55, var="4A3426", bump_scale=900), c, subsurf=1).location = o
    # cleaver, bottom-right, handle leaving the frame
    cl = knife(c, "AB_Cleaver", o + Vector((.55, -.27, 0)), 160, blade_len=.2, blade_w=.095, handle_len=.13, kind="cleaver",
               blade_mat=metal_material("M_cleaver", "8E989F", .3))
    bl = bpy.data.objects[cl[0]]
    hb = lathe_bm([(0, 0), (.0088, 0), (.009, .0003), (0, .0003)], 32)    # hanging hole faked with end-grain disc
    xform(hb, loc=(.17, .025, .0041))
    ho = mesh_object("AB_CleaverHole", hb, endgrain_material(), c, subsurf=0)
    ho.location, ho.rotation_euler = bl.location.copy(), bl.rotation_euler.copy()


def paper_material():
    mat = mat_get("M_butcher_paper")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 40, 6, .6)
    fib = nb.noise(nb.node("ShaderNodeMapping", Vector=tc, Scale=(1, 6, 1)).outputs[0], 400, 3, .6)
    base = nb.ramp(nb.add(nb.mul(n, .6), nb.mul(fib, .4)), [(0, srgb("F3DCCB")), (1, srgb("E8C8B2"))])
    nb.bsdf(**{"Base Color": base, "Roughness": .8, "Sheen Weight": .2,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(n, nb.mul(fib, .5)), Strength=.15, Distance=.001).outputs[0]})
    return mat


def salt_material():
    mat = mat_get("M_salt")
    nb = NB(mat)
    rnd = nb.node("ShaderNodeObjectInfo").outputs["Random"]
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 300, 3)
    nb.bsdf(**{"Base Color": nb.ramp(n, [(0, srgb("FFFFFF")), (1, srgb("E9EEF0"))]), "Roughness": .25, "Coat Weight": .4,
               "Subsurface Weight": .6, "Subsurface Radius": (1, 1, 1), "Subsurface Scale": .003})
    return mat


def mockup_acougue():
    bench = load("pz_bench_acougue.png")
    bench[..., 3] = 1
    meat = load("pz_meat_tile.png")
    fat = load("pz_fat_tile.png")
    slices = 26
    width, height = 1460, 170
    left = 800 - width / 2
    floor_y = 450 - (10 - height * .55)          # image y of the column bottoms
    rnd = random.Random(3)
    a1, p1, a2, tilt = .42, 1.3, .2, .25
    sw = width / slices
    mask = np.zeros((900, 1600), np.float32)
    layer = blank(1600, 900)
    for i in range(slices):
        x = i / (slices - 1)
        th = max(.35, 1 + a1 * math.sin(x * 3.4 + p1) + a2 * math.sin(x * 9 + p1 * 2) + tilt * (x - .5))
        h = int(height * th / 1.7 * 1.25)
        x0 = int(left + i * sw)
        x1 = int(left + (i + 1) * sw)
        fh = 14
        for xx in range(x0, x1):
            col_ = meat[:, xx % 512]
            # meat: tile rows from the bottom up
            rows = np.arange(h - fh)
            layer[int(floor_y) - (h - fh) + rows, xx, :] = col_[(511 - rows[::-1]) % 512]
            frows = np.arange(fh)
            layer[int(floor_y) - h + frows, xx, :] = fat[(frows * 128 // fh), xx % 512]
            mask[int(floor_y) - h:int(floor_y), xx] = 1
    layer[..., 3] = mask
    soft_shadow(bench, mask, 0, 0, r=10, dx=6, dy=10, strength=.5)
    over(bench, layer, 0, 0)
    # cut guides: two white knife lines like the game
    for cx in (left + width * .34, left + width * .67):
        g = blank(5, 290, (1, 1, 1), .85)
        over(bench, g, int(cx) - 2, int(floor_y) - 250)
    bench[..., 3] = 1
    return save_png(bench, "mockup_acougue.png")


def build_acougue():
    build_meat_tiles()
    build_bench_acougue()


def run_acougue():
    out = [render_piece_acougue("meat"), render_piece_acougue("fat"), render_bench("acougue")]
    out.append(mockup_acougue())
    return out



# ============================================================================================ PEIXARIA
FISH = {   # kind: (sprite px w, h)
    "peixe": (760, 320), "file": (520, 248), "salmao": (560, 248), "camarao": (360, 288)}
FISH_SLOT = {"peixe": 0.0, "file": .5, "salmao": .9, "camarao": 1.3}


def fish_body_bm(L=.3, H=.105, T=.045, n=90):
    """Whole fish lying on its side, head towards +X. Writes 'fs' (0 tail .. 1 snout) and 'fy' (-1 belly .. 1 back)."""
    bm = cube_sphere(n)
    ls = bm.verts.layers.float.new("fs")
    ly = bm.verts.layers.float.new("fy")
    for v in bm.verts:
        x, y, z = v.co
        s = (x + 1) / 2
        rc = math.hypot(y, z)
        uy, uz = (y / rc, z / rc) if rc > 1e-9 else (0.0, 1.0)
        # outline: deep body, thin tail peduncle, pointed snout; belly a little fuller than the back
        prof = (.16 + .84 * math.sin(math.pi * min(1.0, s ** 1.35)) ** .8) * (1 - s ** 9) ** .45
        hh = H / 2 * prof * (1.08 if uy < 0 else 1.0)
        tt = T / 2 * prof ** 1.1 * (1 - .25 * s ** 4)
        r = (abs(uy) ** 2.2 + abs(uz) ** 2.2) ** (-1 / 2.2)
        Y = uy * r * hh
        Z = uz * r * tt
        if Z < 0:
            Z *= .3
        # snout slightly below the centre line, back a bit humped
        Y += H * .04 * math.sin(math.pi * s) - H * .05 * max(0.0, s - .85) / .15
        v.co = Vector(((s - .5) * L, Y, Z + T / 2 * .3))
        v[ls] = s
        v[ly] = max(-1.0, min(1.0, uy * r))
    return bm


def fin_bm(pts, t=.0009, bevel=.0004):
    bm = outline_slab(pts, t, bevel=bevel, segs=2)
    return bm


def fish_skin_material():
    mat = mat_get("M_fish_skin")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    fs = nb.node("ShaderNodeAttribute", _attribute_name="fs").outputs["Fact"] if False else nb.node("ShaderNodeAttribute", _attribute_name="fs").outputs["Fac"]
    fy = nb.node("ShaderNodeAttribute", _attribute_name="fy").outputs["Fac"]
    n_m = nb.noise(tc, 40, 5, .6)
    n_f = nb.noise(tc, 300, 4, .6)
    t = nb.add(nb.mul(fy, .5), .5, nb.mul(nb.math("SUBTRACT", n_m, .5), .15))
    base = nb.ramp(t, [(0, srgb("F4F6F4")), (.35, srgb("E3EAEC")), (.55, srgb("B5C7D2")), (.68, srgb("7F9BB0")),
                       (.82, srgb("3F6683")), (1, srgb("2B4A63"))])
    # lateral line + a gold-ish iridescent band along the flank
    lat = nb.mapr(nb.math("ABSOLUTE", nb.math("SUBTRACT", fy, .38)), .05, .0)
    band = nb.mapr(nb.math("ABSOLUTE", nb.math("SUBTRACT", fy, .1)), .22, .0)
    base = nb.mix(nb.mul(band, .25), base, srgb("E8D9A8"))
    base = nb.mix(nb.mul(lat, .45), base, srgb("2C4458"))
    # scales: overlapping scallops
    ssz = .0055
    syy = nb.add(nb.math("DIVIDE", y, ssz * .8), nb.mul(n_m, .6))
    row = nb.math("FLOOR", syy)
    sxx = nb.add(nb.math("DIVIDE", x, ssz), nb.mul(nb.math("MODULO", nb.add(row, 100.0), 2.0), .5))
    fx = nb.math("SUBTRACT", nb.math("FRACT", sxx), .5)
    fy = nb.math("FRACT", syy)
    dd = nb.math("SQRT", nb.add(nb.mul(nb.mul(fx, 1.0), fx), nb.mul(nb.math("SUBTRACT", fy, .1), nb.math("SUBTRACT", fy, .1))))
    edge = nb.mul(nb.mapr(dd, .38, .5), nb.mapr(dd, .62, .5))
    fade_sc = nb.mul(nb.mapr(fs, .05, .2), nb.mapr(fs, .78, .7))
    sc = nb.mul(edge, fade_sc)
    base = nb.mix(nb.mul(sc, .16), base, srgb("1E3446"))
    cid = nb.node("ShaderNodeCombineXYZ", X=nb.math("FLOOR", sxx), Y=row, Z=0.0).outputs[0]
    spark = nb.mul(nb.mul(nb.mapr(nb.node("ShaderNodeTexWhiteNoise", Vector=cid, _noise_dimensions="3D").outputs["Value"], .85, .97), fade_sc),
                   nb.mapr(dd, .45, .2))
    base = nb.mix(nb.mul(spark, .12), base, srgb("F4FAFF"))
    # gill cover arc and head shading
    gx = nb.math("SUBTRACT", fs, .79)
    arc = nb.mapr(nb.math("ABSOLUTE", nb.math("SUBTRACT", nb.math("SQRT", nb.add(nb.mul(gx, gx), nb.mul(nb.mul(fy, .085), nb.mul(fy, .085)))), .085)), .008, .0)
    arc = nb.mul(arc, nb.mapr(fs, .73, .76))
    base = nb.mix(nb.mul(arc, .85), base, srgb("4A3440"))
    mouth = nb.mul(nb.mapr(nb.math("ABSOLUTE", nb.math("SUBTRACT", fy, -.12)), .05, .0), nb.mapr(fs, .965, .985))
    base = nb.mix(nb.mul(mouth, .8), base, srgb("3A2A30"))
    head = nb.mapr(fs, .8, .9)
    base = nb.mix(nb.mul(head, .2), base, srgb("C8D3D9"))
    h = nb.add(nb.mul(sc, -.5), nb.mul(n_f, .15), nb.mul(arc, -.8))
    nb.bsdf(**{"Base Color": base, "Metallic": nb.add(.25, nb.mul(spark, .4)), "Roughness": nb.add(.22, nb.mul(sc, .1)),
               "Coat Weight": .7, "Coat Roughness": .08, "Specular IOR Level": .6,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.35, Distance=.0006).outputs[0]})
    return mat


def fin_material():
    mat = mat_get("M_fish_fin")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    rays = nb.mapr(nb.math("SINE", nb.mul(nb.add(x, nb.mul(y, .3)), 2 * math.pi / .0022)), .6, 1.0)
    n = nb.noise(tc, 60, 4)
    base = nb.ramp(nb.add(nb.mul(n, .6), nb.mul(rays, .25)), [(0, srgb("C9D6DE")), (.6, srgb("9FB3C2")), (1, srgb("7B93A6"))])
    nb.bsdf(**{"Base Color": base, "Roughness": .28, "Coat Weight": .6, "Coat Roughness": .1, "Subsurface Weight": .5,
               "Subsurface Radius": (.6, .8, 1), "Subsurface Scale": .002, "Alpha": .82,
               "Normal": nb.node("ShaderNodeBump", Height=rays, Strength=.12, Distance=.0004).outputs[0]})
    return mat


def fin_material2(name, center, rays, length):
    """Translucent fin: dark rays fanning out from `center` (local coords), darker at the root, lighter tips."""
    mat = mat_get("M_fin_" + name)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    dx, dy = nb.math("SUBTRACT", x, center[0]), nb.math("SUBTRACT", y, center[1])
    ang = nb.math("ARCTAN2", dy, dx)
    d = nb.math("SQRT", nb.add(nb.mul(dx, dx), nb.mul(dy, dy)))
    n = nb.noise(tc, 90, 3)
    ray = nb.mapr(nb.math("ABSOLUTE", nb.math("SINE", nb.add(nb.mul(ang, rays * 3.0), nb.mul(n, .6)))), .8, 1.0)
    root = abs(center[1]) if abs(center[1]) > .01 else 0.0
    t = nb.mapr(nb.math("SUBTRACT", d, root), .0, length)
    base = nb.ramp(nb.add(nb.mul(t, .8), nb.mul(n, .2)), [(0, srgb("4F6A80")), (.45, srgb("7F98AB")), (1, srgb("C9D8E2"))])
    base = nb.mix(nb.mul(ray, nb.add(.25, nb.mul(t, .45))), base, srgb("324A5E"))
    alpha = nb.add(.95, nb.mul(t, -.4), nb.mul(ray, .3))
    nb.bsdf(**{"Base Color": base, "Roughness": .25, "Coat Weight": .7, "Coat Roughness": .08, "Subsurface Weight": .4,
               "Subsurface Radius": (.6, .8, 1), "Subsurface Scale": .002, "Alpha": nb.math("MINIMUM", alpha, 1.0),
               "Normal": nb.node("ShaderNodeBump", Height=ray, Strength=.25, Distance=.0004).outputs[0]})
    return mat


def eye_material():
    mat = mat_get("M_fish_eye")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    r = nb.math("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    pupil = nb.mapr(r, .0048, .0042)
    iris = nb.ramp(nb.mapr(r, .0045, .0095), [(0, srgb("D9B45A")), (.5, srgb("E9E1CF")), (1, srgb("8C9BA6"))])
    base = nb.mix(pupil, iris, srgb("0B0F14"))
    nb.bsdf(**{"Base Color": base, "Roughness": .05, "Coat Weight": 1.0, "Coat Roughness": .02, "Specular IOR Level": .8})
    return mat


def build_fish(c, at):
    L, H, T = .27, .092, .04
    body = mesh_object("fish_peixe", fish_body_bm(L, H, T), fish_skin_material(), c, subsurf=1)
    body.location = at
    # fins: each its own object (origin at the fin base) so the rays can fan out from the root
    x0 = -L / 2 + .014
    tail = [(0, -.01)]
    for k in range(1, 9):
        t = k / 8
        tail.append((-.052 * t, -.01 - .034 * t ** .8))
    tail += [(-.044, -.02), (-.036, -.004), (-.036, .004), (-.044, .02)]
    for k in range(8, 0, -1):
        t = k / 8
        tail.append((-.052 * t, .01 + .034 * t ** .8))
    tail.append((0, .01))
    dor = [(-.045, -.004)]
    for k in range(13):
        t = k / 12
        dor.append((-.045 + .1 * t, .016 * (1 - .55 * t) * (1 if k % 2 == 0 else .82)))
    dor.append((.06, -.004))
    an = [(-.025, .002), (-.02, -.013), (-.002, -.016), (.012, -.01), (.02, .002)]
    pv = [(-.012, .002), (-.008, -.014), (.004, -.015), (.012, .002)]
    pc = [(0, 0), (-.026, -.009), (-.034, -.003), (-.03, .005), (-.007, .007)]
    fins = []
    for name, pts, loc, rot, center, rays, ln, t in (
            ("tail", tail, (x0, H * .01, T * .14), 0, (.004, 0), 7.0, .055, .0009),
            ("dorsal", dor, (0, H / 2 * .86, T * .22), 0, (0, -.06), 20.0, .018, .0009),
            ("anal", an, (-.06, -H / 2 * .6, T * .2), 0, (0, .05), 18.0, .016, .0009),
            ("pelvic", pv, (.012, -H / 2 * .9, T * .2), 0, (0, .04), 18.0, .015, .0009),
            ("pect", pc, (.066, -.012, T * .8), -12, (.002, 0), 6.0, .034, .0008)):
        fbm = fin_bm(round_outline(pts, .003 if name != "dorsal" else .0015, 3), t=t)
        if name == "pect":
            xform(fbm, rot=(0, 4, 0))
        ob = mesh_object("fish_peixe_" + name, fbm, fin_material2(name, center, rays, ln), c, subsurf=1)
        ob.location = at + Vector(loc)
        ob.rotation_euler.z = math.radians(rot)
        fins.append(ob.name)
    # eye
    s_eye = .9
    ex = (s_eye - .5) * L
    ey = H * .07
    eb = ellipsoid(.0095, .0095, .004, 4)
    eo = mesh_object("fish_peixe_eye", eb, eye_material(), c, subsurf=1)
    eo.location = at + Vector((ex, ey, T * .6))
    ring = lathe_bm([(.0095, 0), (.0122, .0), (.0127, .0014), (.0107, .0026), (.0095, .0019)], 48)
    ro = mesh_object("fish_peixe_eyering", ring, simple_material("M_eyering", "6F8494", .3, var="8FA2AE", coat=.6), c, subsurf=1)
    ro.location = at + Vector((ex, ey, T * .6 - .0012))
    return [body.name, eo.name, ro.name] + fins


def fillet_bm(L, W, T, taper=1.0, seed=0, belly=.0):
    """Fillet: long teardrop outline (thick end at -X), domed; returns bmesh sitting on z=0."""
    bm = cube_sphere(70)
    for v in bm.verts:
        x, y, z = v.co
        s = (x + 1) / 2
        rc = math.hypot(y, z)
        uy, uz = (y / rc, z / rc) if rc > 1e-9 else (0.0, 1.0)
        w = (math.sin(math.pi * min(1.0, (s * .97 + .03) ** .8)) ** .7) * (1 - .55 * s ** 1.5 * taper)
        hh = W / 2 * w * (1 + belly * (1 if uy < 0 else 0))
        tt = T * w ** 1.3 * (1 - .5 * s * taper)
        r = (abs(uy) ** 2.6 + abs(uz) ** 2.6) ** (-1 / 2.6)
        Y = uy * r * hh
        Z = max(0.0, uz) * r * tt if uz > 0 else uz * r * tt * .08
        k = 1 + .025 * noise.noise(Vector((x * 3, y * 3, seed)))
        Y += W * .06 * math.sin(math.pi * s) * (1 if seed % 2 else -1)
        v.co = Vector(((s - .5) * L, Y * k, (Z + tt * .08) * k))
    return bm


def fillet_material(kind):
    mat = mat_get("M_fillet_" + kind)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    geo = nb.node("ShaderNodeNewGeometry")
    nz = nb.sep(geo.outputs["Normal"])[2]
    n_m = nb.noise(tc, 50, 5, .6)
    n_f = nb.noise(tc, 400, 4, .6)
    sal = kind == "salmao"
    # myomere (flake) lines: W-shaped arcs across the fillet, uneven spacing
    yy = nb.add(y, nb.mul(nb.math("SUBTRACT", n_m, .5), .008))
    ay = nb.math("ABSOLUTE", yy)
    warp = nb.math("SUBTRACT", nb.noise(nb.node("ShaderNodeMapping", Vector=tc, Scale=(1, .35, 1)).outputs[0], 9, 3, .5), .5)
    curv = nb.add(.45 if sal else .38, nb.mul(nb.math("SUBTRACT", nb.noise(tc, 6, 2), .5), .3))
    chev = nb.add(x, nb.mul(ay, curv), nb.mul(nb.mul(ay, ay), -5.0 if sal else -4.0), nb.mul(warp, .03))
    per = .0135 if sal else .016
    ph = nb.math("FRACT", nb.math("DIVIDE", chev, per))
    width = nb.mul(nb.add(.045 if sal else .035, nb.mul(nb.noise(tc, 22, 3), .05 if sal else .03)), nb.mapr(ay, .05, .02))
    line = nb.node("ShaderNodeMapRange", Value=nb.math("ABSOLUTE", nb.math("SUBTRACT", ph, .5)),
                   **{"From Min": nb.math("SUBTRACT", .5, width), "From Max": .5, "To Min": 0.0, "To Max": 1.0},
                   _interpolation_type="SMOOTHSTEP", _clamp=True).outputs[0]
    shade = nb.mapr(ph, .5, .9)                       # each flake slightly darker towards its next line
    lat = nb.mul(nb.mapr(nb.math("ABSOLUTE", nb.add(y, nb.add(-.004, nb.mul(warp, .006)))), .003, .0), nb.mapr(nb.noise(tc, 12, 2), .35, .6))
    skin = nb.mapr(nz, .45, .2)
    if sal:
        back = nb.mapr(y, -.04, .05)
        flesh = nb.ramp(nb.add(nb.mul(back, .7), nb.mul(n_m, .4), -.1), [(0, srgb("FFA06A")), (.45, srgb("F7834B")), (1, srgb("E2622F"))])
        flesh = nb.mix(nb.mul(shade, .12), flesh, srgb("D4552A"))
        base = nb.mix(nb.mul(line, .92), flesh, srgb("FFEBDD"))
        belly = nb.mapr(y, -.035, -.052)
        base = nb.mix(nb.mul(belly, .6), base, srgb("FFDCC6"))
        base = nb.mix(nb.mul(lat, .25), base, srgb("B9644A"))
        base = nb.mix(skin, base, srgb("9EA6AC"))
        kw = {"Subsurface Weight": .45, "Subsurface Radius": (1, .45, .25), "Roughness": .28, "Coat Weight": .65}
    else:
        flesh = nb.ramp(nb.add(nb.mul(n_m, .6), nb.mul(n_f, .3), -.05), [(0, srgb("F0F5FA")), (.5, srgb("E9EEF4")), (1, srgb("E2E4EA"))])
        flesh = nb.mix(nb.mul(shade, .2), flesh, srgb("D6D6DE"))
        base = nb.mix(nb.mul(line, .7), flesh, srgb("C9BCBC"))
        base = nb.mix(nb.mul(lat, .15), base, srgb("E6B9B2"))
        base = nb.mix(skin, base, srgb("8C9298"))
        kw = {"Subsurface Weight": .35, "Subsurface Radius": (.9, .9, 1), "Roughness": .3, "Coat Weight": .5}
    h = nb.add(nb.mul(line, -.6), nb.mul(shade, -.25), nb.mul(n_f, .25))
    kw.update({"Base Color": base, "Coat Roughness": .1, "Subsurface Scale": .006, "Specular IOR Level": .55,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.3, Distance=.0008).outputs[0]})
    nb.bsdf(**kw)
    return mat


def shrimp_bm(seed=0, R=.027, r0=.0128):
    """Shell-on (headless) shrimp curled in a C, seen from its side: overlapping shell plates.
    Writes 'dors' (+1 back / outer curve .. -1 belly / inner curve)."""
    pts = []
    N = 40
    for i in range(N + 1):
        t = i / N
        a = math.radians(-20 + 225 * t)
        rr = R * (1 - .32 * t)
        pts.append((rr * math.cos(a), rr * math.sin(a), 0))
    P = spline(pts, 3)
    def rad(t):
        plate = (t * 6.0) % 1.0
        seg = .9 + .14 * plate ** 1.5
        return r0 * (1 - .6 * t ** 1.3) * seg * (.82 + .18 * min(1.0, t * 8 + .3))
    bm = tube_bm(P, rad, 18)
    ld = bm.verts.layers.float.new("dors")
    for v in bm.verts:
        q = Vector((v.co.x, v.co.y, 0))
        best = min(P, key=lambda p: (Vector(p[:2] + (0,)) - q).length_squared)
        c = Vector((best[0], best[1], 0))
        outward = c.normalized() if c.length > 1e-6 else Vector((1, 0, 0))
        d = (Vector((v.co.x, v.co.y, v.co.z)) - Vector((best[0], best[1], 0)))
        v[ld] = max(-1.0, min(1.0, d.dot(outward) / max(d.length, 1e-6)))
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
        if v.co.z < r0 * .25:
            v.co.z *= .5
    return bm, P


def shrimp_material():
    mat = mat_get("M_shrimp")
    nb = NB(mat)
    uv = nb.node("ShaderNodeTexCoord").outputs["UV"]
    u, v, _ = nb.sep(uv)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    dors = nb.node("ShaderNodeAttribute", _attribute_name="dors").outputs["Fac"]
    n = nb.noise(tc, 120, 4)
    seg = nb.math("FRACT", nb.mul(u, 1 / .0098))
    edge = nb.mapr(seg, .9, .985)
    band = nb.mapr(seg, .55, .9)
    base = nb.ramp(nb.add(nb.mul(dors, .5), .5, nb.mul(n, .15)),
                   [(0, srgb("FFE0D4")), (.35, srgb("FFB79E")), (.6, srgb("F6865F")), (.85, srgb("E65A3A")), (1, srgb("C9452E"))])
    base = nb.mix(nb.mul(band, .22), base, srgb("FFF0E6"))
    base = nb.mix(nb.mul(edge, .5), base, srgb("B5402C"))
    nb.bsdf(**{"Base Color": base, "Roughness": .28, "Coat Weight": .75, "Coat Roughness": .08, "Subsurface Weight": .45,
               "Subsurface Radius": (1, .5, .4), "Subsurface Scale": .004,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(nb.mul(edge, -.8), nb.mul(band, .3), nb.mul(n, .2)), Strength=.4, Distance=.0008).outputs[0]})
    return mat


def shrimp_tail_material():
    mat = mat_get("M_shrimp_tail")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    rnd = nb.node("ShaderNodeObjectInfo").outputs["Random"]
    n = nb.noise(tc, 300, 3)
    base = nb.ramp(n, [(0, srgb("E2502F")), (1, srgb("F57C52"))])
    nb.bsdf(**{"Base Color": base, "Roughness": .25, "Coat Weight": .7, "Coat Roughness": .08, "Subsurface Weight": .5,
               "Subsurface Radius": (1, .4, .3), "Subsurface Scale": .003, "Alpha": .92})
    return mat


def build_shrimps(c, at):
    sb = bmesh.new()
    tb = bmesh.new()
    lb = bmesh.new()
    poses = [(-.028, -.014, 10, 0, 0), (.03, -.01, 175, 1, 0), (.0, .018, 95, 2, .014)]
    for x, y, rot, seed, z in poses:
        b, P = shrimp_bm(seed)
        xform(b, loc=(x, y, z), rot=(0, 0, rot))
        bm_join(sb, b)
        # tail fan: telson + two uropods each side, fanned out
        e = Vector(P[-1])
        d = (Vector(P[-1]) - Vector(P[-4])).normalized()
        a = math.degrees(math.atan2(d.y, d.x))
        f = bmesh.new()
        for k, (ang, ln, w) in enumerate(((0, .02, .0045), (-28, .019, .005), (28, .019, .005), (-50, .016, .0045), (50, .016, .0045))):
            blade = [(0, -w * .5), (ln * .5, -w), (ln, -w * .45), (ln * 1.05, 0), (ln, w * .45), (ln * .5, w), (0, w * .5)]
            bl = outline_slab(round_outline(blade, .0015, 2), .0014, bevel=.0005, segs=1)
            xform(bl, rot=(0, -6, ang), loc=(0, 0, .0006 * k))
            bm_join(f, bl)
        xform(f, loc=(e.x, e.y, .004), rot=(0, 0, a))
        xform(f, loc=(x, y, z), rot=(0, 0, rot))
        bm_join(tb, f)
        # little legs (pleopods) under the belly, along the inner curve
        for k in range(5):
            t = .12 + .13 * k
            i = int(t * (len(P) - 1))
            p = Vector(P[i])
            inward = -Vector((p.x, p.y, 0)).normalized()
            tang = (Vector(P[min(i + 1, len(P) - 1)]) - Vector(P[max(i - 1, 0)])).normalized()
            r_here = .0128 * (1 - .6 * t ** 1.3)
            for side in (-1, 1):
                root = p + inward * r_here * .7 + Vector((0, 0, .006 + side * .002))
                tip = root + inward * .009 - tang * .003 + Vector((0, 0, -.002))
                leg = tube_bm([root[:], ((root + tip) / 2 + inward * .001)[:], tip[:]], lambda q: .0011 * (1 - .6 * q), 6)
                xform(leg, loc=(x, y, z), rot=(0, 0, rot))
                bm_join(lb, leg)
    s = mesh_object("fish_camarao", sb, shrimp_material(), c, subsurf=1)
    s.location = at
    t = mesh_object("fish_camarao_tails", tb, shrimp_tail_material(), c, subsurf=1)
    t.location = at
    lg = mesh_object("fish_camarao_legs", lb, simple_material("M_shrimp_legs", "F7A58C", .35, var="FFC9B6", sss=.4), c, subsurf=1)
    lg.location = at
    return [s.name, t.name, lg.name]


def build_fish_pieces():
    o = O("peixaria")
    c = col("Peixaria pieces")
    wipe_collection(c.name)
    names = {}
    names["peixe"] = build_fish(c, o + Vector((FISH_SLOT["peixe"], 0, .0005)))
    f = mesh_object("fish_file", fillet_bm(.235, .1, .016, 1.0, 1), fillet_material("file"), c, subsurf=1)
    f.location = o + Vector((FISH_SLOT["peixe"] + .5, 0, .0005))
    names["file"] = [f.name]
    sm = mesh_object("fish_salmao", fillet_bm(.24, .1, .026, .35, 2, belly=.06), fillet_material("salmao"), c, subsurf=1)
    sm.location = o + Vector((FISH_SLOT["peixe"] + .9, 0, .0005))
    names["salmao"] = [sm.name]
    names["camarao"] = build_shrimps(c, o + Vector((FISH_SLOT["peixe"] + 1.3, 0, .0005)))
    catcher("peixaria", o + Vector((.7, 0, 0)), (2.4, .8))
    return names


FISH_PARTS = {"peixe": ["fish_peixe", "fish_peixe_eye", "fish_peixe_eyering"] + ["fish_peixe_" + n for n in ("tail", "dorsal", "anal", "pelvic", "pect")],
              "file": ["fish_file"], "salmao": ["fish_salmao"], "camarao": ["fish_camarao", "fish_camarao_tails", "fish_camarao_legs"]}
FISH_X = {"peixe": 0.0, "file": .5, "salmao": .9, "camarao": 1.3}


def render_piece_peixaria(kind):
    w, h = FISH[kind]
    at = O("peixaria") + Vector((FISH_X[kind], 0, 0))
    size = (w / MPX, h / MPX)
    return shoot(at, size, (w, h), os.path.join(OUT, "pz_fish_%s.png" % kind), True, FISH_PARTS[kind] + ["Catcher_peixaria"])


def ice_material():
    mat = mat_get("M_ice")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    rnd = nb.node("ShaderNodeObjectInfo").outputs["Random"]
    n = nb.noise(tc, 200, 4)
    frost = nb.mapr(nb.noise(tc, 90, 5, .6), .35, .7)
    base = nb.ramp(nb.add(nb.mul(n, .4), nb.mul(frost, .6)), [(0, srgb("D8F0FA")), (.5, srgb("EEF9FD")), (1, srgb("FFFFFF"))])
    glow = nb.ramp(nb.add(nb.mul(rnd, .6), nb.mul(n, .4)), [(0, srgb("BFE6F5")), (1, srgb("E8F7FD"))])
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.05, nb.mul(frost, .3)),
               "IOR": 1.31, "Coat Weight": .9, "Coat Roughness": .03, "Subsurface Weight": .3, "Subsurface Radius": (1, 1, 1),
               "Subsurface Scale": .004, "Specular IOR Level": .8, "Emission Color": glow, "Emission Strength": .2,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(n, frost), Strength=.3, Distance=.0008).outputs[0]})
    return mat


_ICE_TEMPLATES = []


def ice_templates(n=14, seed=77):
    """A few bevelled, jittered unit chunks (verts, faces) reused for every ice piece."""
    if _ICE_TEMPLATES:
        return _ICE_TEMPLATES
    rnd = random.Random(seed)
    for k in range(n):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts:
            v.co += Vector((rnd.uniform(-.2, .2), rnd.uniform(-.2, .2), rnd.uniform(-.2, .2)))
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=.14, segments=2, affect="EDGES", clamp_overlap=True)
        vs = np.array([v.co[:] for v in bm.verts], np.float32)
        fs = [[v.index for v in f.verts] for f in bm.faces]
        bm.free()
        _ICE_TEMPLATES.append((vs, fs))
    return _ICE_TEMPLATES


def ice_bm(area, count, seed, size=(.007, .016), heap=None, zbase=0.0, bm=None):
    """Crushed ice from instanced template chunks (fast). area = (x0, y0, x1, y1); heap(x, y) -> 0..1."""
    tpl = ice_templates()
    rnd = random.Random(seed)
    x0, y0, x1, y1 = area
    V, F = [], []
    off = 0
    placed = tries = 0
    while placed < count and tries < count * 10:
        tries += 1
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        hgt = heap(x, y) if heap else 1.0
        if hgt <= 0 or rnd.random() > hgt:
            continue
        s = rnd.uniform(*size)
        vs, fs = tpl[rnd.randrange(len(tpl))]
        S = np.diag([s * rnd.uniform(.8, 1.3), s * rnd.uniform(.8, 1.3), s * rnd.uniform(.5, .9)])
        R = np.array(Matrix.Rotation(rnd.uniform(0, 6.28), 3, "Z") @ Matrix.Rotation(rnd.uniform(0, 6.28), 3, "Y") @
                     Matrix.Rotation(rnd.uniform(0, 6.28), 3, "X"), np.float32)
        p = vs @ S.T @ R.T + np.array([x, y, zbase + hgt * .02 * rnd.random() + s * .3], np.float32)
        V.append(p)
        F.extend([[i + off for i in f] for f in fs])
        off += len(vs)
        placed += 1
    me = bpy.data.meshes.new("_ice")
    me.from_pydata(np.concatenate(V).tolist(), [], F)
    bm = bm or bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def lemon_material():
    mat = mat_get("M_lemon_cut")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    geo = nb.node("ShaderNodeNewGeometry")
    nz = nb.sep(geo.outputs["Normal"])[2]
    r = nb.math("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    ang = nb.math("ARCTAN2", y, x)
    n = nb.noise(tc, 150, 4)
    R = .04
    seg = nb.math("ABSOLUTE", nb.math("SUBTRACT", nb.math("FRACT", nb.mul(ang, 10 / (2 * math.pi))), .5))
    memb = nb.mul(nb.mapr(seg, .44, .5), nb.mapr(r, .004, .007))
    cells = nb.mapr(nb.node("ShaderNodeTexVoronoi", Vector=nb.node("ShaderNodeMapping", Vector=tc, Scale=(1, 1, 1)).outputs[0], Scale=500, _feature="DISTANCE_TO_EDGE").outputs["Distance"], .0, .12)
    pulp = nb.ramp(nb.add(nb.mul(n, .5), nb.mul(cells, .4)), [(0, srgb("F6D23A")), (1, srgb("FCEB8A"))])
    face = nb.mix(memb, pulp, srgb("FFF6D8"))
    pith = nb.mapr(r, R * .86, R * .9)
    face = nb.mix(pith, face, srgb("FFF7DE"))
    rind = nb.mapr(r, R * .95, R * .98)
    face = nb.mix(rind, face, srgb("F4C21A"))
    center = nb.mapr(r, .004, .002)
    face = nb.mix(center, face, srgb("FFF3CC"))
    peel = nb.ramp(n, [(0, srgb("F7C51E")), (1, srgb("E9AE12"))])
    top = nb.mapr(nz, .8, .95)
    base = nb.mix(top, peel, face)
    h = nb.add(nb.mul(memb, .6), nb.mul(cells, .3))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.45, nb.mul(top, -.25)), "Coat Weight": nb.mul(top, .7), "Coat Roughness": .1,
               "Subsurface Weight": .35, "Subsurface Radius": (1, .9, .3), "Subsurface Scale": .004,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.35, Distance=.0008).outputs[0]})
    return mat


def lemon_half_bm(R=.032, H=.026):
    prof = [(0, 0), (R * .55, 0)] + [(R * math.sin(a), H * (1 - math.cos(a))) for a in [math.pi / 2 * k / 12 for k in range(3, 13)]] + [(R * .97, H + .0006), (0, H - .0012)]
    return lathe_bm(prof, 64)


def parsley_bm(seed=0, L=.12, leaves=7):
    rnd = random.Random(seed)
    bm = bmesh.new()
    pts = [(t * L, .012 * math.sin(t * 3 + seed), .003) for t in [i / 8 for i in range(9)]]
    bm_join(bm, tube_bm(spline(pts, 3), .0016, 8))
    for k in range(leaves):
        t = .45 + .55 * k / max(1, leaves - 1)
        x, y = t * L, .012 * math.sin(t * 3 + seed)
        side = 1 if k % 2 else -1
        ang = side * rnd.uniform(25, 55) + (0 if k < leaves - 1 else -side * 40)
        lpts = []
        for i in range(48):
            a = 2 * math.pi * i / 48
            rr = .015 * (1 + .22 * math.cos(3 * a)) * (1 + .05 * math.cos(15 * a)) * rnd.uniform(.97, 1.03)
            lpts.append((rr * math.cos(a) * 1.1 + .013, rr * math.sin(a)))
        lb = outline_slab(lpts, .0012, bevel=.0005, segs=1)
        for v in lb.verts:
            v.co.z += .002 * math.sin(v.co.x * 120) + .0015 * (v.co.x / .03)
        xform(lb, rot=(0, -6, ang), loc=(x, y, .004 + rnd.uniform(0, .002)))
        bm_join(bm, lb)
    return bm


def steel_counter_material():
    mat = mat_get("M_counter_steel")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    sv = nb.node("ShaderNodeMapping", Vector=tc, Scale=(3, 500, 1)).outputs[0]
    br = nb.noise(sv, 1.0, 4, .55)
    n = nb.noise(tc, 5, 5, .6)
    smudge = nb.mapr(nb.noise(tc, 9, 6, .65, .3), .5, .75)
    base = nb.ramp(nb.add(nb.mul(br, .5), nb.mul(n, .5)), [(0, srgb("8D979E")), (1, srgb("AEB7BD"))])
    base = nb.mix(nb.mul(smudge, .1), base, srgb("838D95"))
    nb.bsdf(**{"Base Color": base, "Metallic": .85, "Roughness": nb.add(.32, nb.mul(br, .1), nb.mul(smudge, .12)),
               "Normal": nb.node("ShaderNodeBump", Height=br, Strength=.12, Distance=.0004).outputs[0]})
    return mat


def build_bench_peixaria():
    o = O("peixaria") + Vector((0, -2.0, 0))
    c = col("Peixaria bench")
    wipe_collection(c.name)
    W, H = BENCH_SIZE
    top = mesh_object("PB_Top", quad_bm(W * 1.04, H * 1.04), steel_counter_material(), c, subsurf=0)
    top.location = o
    im = ice_material()
    def heap_tl(x, y):
        d = math.hypot((x + .66) / .42, (y - .38) / .25)
        return max(0.0, 1 - d ** 3)
    def heap_br(x, y):
        d = math.hypot((x - .66) / .42, (y + .38) / .24)
        return max(0.0, 1 - d ** 3)
    ib = ice_bm((-.66, .12, -.22, .38), 1500, 1, size=(.009, .019), heap=heap_tl)
    ice_bm((.22, -.38, .66, -.12), 1500, 2, size=(.009, .019), heap=heap_br, bm=ib)
    mesh_object("PB_Ice", ib, im, c, subsurf=1).location = o
    lm = lemon_material()
    for k, (lx, ly, lz) in enumerate(((-.5, .25, .022), (-.4, .31, .016), (.5, -.25, .02))):
        lo = mesh_object("PB_Lemon%d" % k, lemon_half_bm(.04, .03), lm, c, subsurf=1)
        lo.location = o + Vector((lx, ly, lz))
        lo.rotation_euler = (math.radians(6 * (k - 1)), math.radians(4), 0)
    pm = leaf_material("M_parsley", "3E8F3A", "6DB352")
    for k, (px, py, pr) in enumerate(((.47, .26, 200), (.53, .3, 230), (.43, .31, 170), (.36, -.31, 20))):
        po = mesh_object("PB_Parsley%d" % k, parsley_bm(k), pm, c, subsurf=1)
        po.location = o + Vector((px, py, 0 if k < 3 else .012))
        po.rotation_euler.z = math.radians(pr)
    knife(c, "PB_Knife", o + Vector((-.43, -.3, 0)), 12, blade_len=.21, blade_w=.03, handle_len=.12, kind="chef",
          blade_mat=metal_material("M_steel_p", "8F9AA2", .25),
          handle_mat=simple_material("M_knife_poly", "1F8F85", .35, var="25A193", coat=.3))


def build_icebed():
    """Mockup only: the crushed ice bed of the stage (1540 x 690 px)."""
    o = O("peixaria") + Vector((0, -4.0, 0))
    c = col("Peixaria parts")
    wipe_collection(c.name)
    w, h = 1540 / MPX, 690 / MPX
    tray = rounded_slab(w, h, .012, 22 / MPX)
    mesh_object("PP_IceTray", tray, steel_counter_material(), c, subsurf=1).location = o
    ib = ice_bm((-w / 2 + .01, -h / 2 + .01, w / 2 - .01, h / 2 - .01), 8000, 5, size=(.008, .015), zbase=.008)
    mesh_object("PP_Ice", ib, ice_material(), c, subsurf=1).location = o
    # scale tray (260 x 150 px): steel body, white plate, dark readout window
    sw, sh = 260 / MPX, 150 / MPX
    sb = rounded_slab(sw, sh, .02, 18 / MPX)
    mesh_object("PP_Scale", sb, simple_material("M_scale_body", "D9DEE3", .35, var="CDD3D9", coat=.3), c, subsurf=1).location = o + Vector((1.0, 0, 0))
    pb = rounded_slab(sw - 24 / MPX, sh - 56 / MPX, .006, 16 / MPX)
    xform(pb, loc=(0, 10 / MPX, .02))
    mesh_object("PP_Plate", pb, simple_material("M_scale_plate", "F7FAFC", .25, var="EEF2F5", coat=.4), c, subsurf=1).location = o + Vector((1.0, 0, 0))
    rb = rounded_slab(sw - 40 / MPX, 34 / MPX, .003, 10 / MPX)
    xform(rb, loc=(0, -sh / 2 + 22 / MPX, .02))
    mesh_object("PP_Readout", rb, simple_material("M_readout", "2E3A4A", .2, coat=.8), c, subsurf=1).location = o + Vector((1.0, 0, 0))
    catcher("peixaria", o + Vector((.5, 0, -.0005)), (2.6, 1.2), "Catcher_pparts")


def render_parts_peixaria():
    o = O("peixaria") + Vector((0, -4.0, 0))
    a = shoot(o, (1600 / MPX, 760 / MPX), (1600, 760), os.path.join(OUT, "mockup_part_icebed.png"), True, ["PP_IceTray", "PP_Ice", "Catcher_pparts"])
    b = shoot(o + Vector((1.0, 0, 0)), (300 / MPX, 190 / MPX), (300, 190), os.path.join(OUT, "mockup_part_scale.png"), True,
              ["PP_Scale", "PP_Plate", "PP_Readout", "Catcher_pparts"])
    return [a, b]


def mockup_peixaria():
    bench = load("pz_bench_peixaria.png")
    bench[..., 3] = 1
    place(bench, load("mockup_part_icebed.png"), 800, 547)
    sc = load("mockup_part_scale.png")
    for t in range(3):
        place(bench, sc, 800 + (t - 1) * 290, 89)
    unit = 82
    looks = {"peixe": (1.9, .8), "file": (1.3, .62), "camarao": (.9, .72), "salmao": (1.4, .62)}
    pieces = ["peixe", "salmao", "camarao", "file", "peixe", "salmao"]
    for i, k in enumerate(pieces):
        row, colm = i // 3, i % 3
        cx = 800 + (colm - 1) * (1480 / 3)
        cy = 547 - (1 if row == 0 else -1) * 690 * .22
        w, h = looks[k]
        place(bench, load("pz_fish_%s.png" % k), cx, cy, int(w * unit * 1.9), int(h * unit * 1.9))
    # one piece already on the middle scale
    place(bench, load("pz_fish_file.png"), 800, 80, int(1.3 * unit), int(.62 * unit))
    bench[..., 3] = 1
    return save_png(bench, "mockup_peixaria.png")


def build_peixaria(part=None):
    if part in (None, "pieces"):
        build_fish_pieces()
    if part in (None, "bench"):
        build_bench_peixaria()
    if part in (None, "icebed"):
        build_icebed()


def run_peixaria():
    out = [render_piece_peixaria(k) for k in FISH]
    out.append(render_bench("peixaria"))
    out += render_parts_peixaria()
    out.append(mockup_peixaria())
    return out




# ============================================================================================ ACOUGUE v2: real cuts (side view)
MEAT_RES = (1400, 300)
MEAT_PXM = 2000.0
MEAT_TILT = 3.0
CUTS = ["contrafile", "picanha", "fraldinha"]


def cut_shape(cut):
    """(length, depth, thickness(s), fat(s) thickness) for s in 0..1 along the piece (left -> right)."""
    if cut == "contrafile":       # strip loin: thick, even, a fat cap all along the top
        L, D = .6, .13
        th = lambda s: .074 + .008 * math.sin(s * 5.1 + .4) * .5 + .006 * s
        fat = lambda s: .011 + .003 * math.sin(s * 7 + 1) - .005 * max(0.0, s - .8) / .2
    elif cut == "picanha":        # rump cap: thick in the middle, triangular, a thick fat cap
        L, D = .56, .14
        th = lambda s: .03 + .07 * math.sin(math.pi * min(1.0, max(0.0, s * .95 + .03))) ** 1.3
        fat = lambda s: .011 + .003 * math.sin(s * 9)
    else:                         # flank steak: long, thin, tapering, almost no fat
        L, D = .62, .12
        th = lambda s: .012 + .03 * (1 - s) ** .9 * (1 + .12 * math.sin(s * 11))
        fat = lambda s: 0.0
    return L, D, th, fat


def meat_cut_bm(cut, n=90):
    """Slab along X, cross-section a soft superellipse (flat bottom); writes 's' (along) and 'hz' (0 bottom..1 top)
    and 'ft' (fat thickness / local height) for the shader."""
    L, D, th, fat = cut_shape(cut)
    bm = cube_sphere(n)
    ls = bm.verts.layers.float.new("s")
    lh = bm.verts.layers.float.new("hz")
    lf = bm.verts.layers.float.new("ft")
    off = Vector((CUTS.index(cut) * 3.1, 1.7, .4))
    for v in bm.verts:
        x, y, z = v.co
        s = (x + 1) / 2
        rc = math.hypot(y, z)
        uy, uz = (y / rc, z / rc) if rc > 1e-9 else (0.0, 1.0)
        r = (abs(uy) ** 5 + abs(uz) ** 5) ** (-1 / 5)
        end = (1 - abs(2 * s - 1) ** 8) ** .35                    # rounded, slightly pinched ends
        H = th(s) * (.55 + .45 * end)
        dd = D / 2 * (.8 + .2 * end)
        Y = uy * r * dd
        zz = uz * r
        Z = H * max(0.0, (zz + .8) / 1.8)
        lump = 1 + .02 * noise.fractal(Vector((x * 3, y * 2, z * 2)) + off, .6, 2, 2)
        X = (s - .5) * L + .006 * noise.noise(Vector((y * 5, z * 5, 1)) + off) * (1 - end)
        v.co = Vector((X, Y * lump, Z * lump))
        v[ls] = s
        v[lh] = Z / max(H, 1e-6)
        v[lf] = fat(s) / max(H, 1e-6)
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
    return bm


def beef_material(cut):
    mat = mat_get("M_beef_" + cut)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    s = nb.node("ShaderNodeAttribute", _attribute_name="s").outputs["Fac"]
    hz = nb.node("ShaderNodeAttribute", _attribute_name="hz").outputs["Fac"]
    ft = nb.node("ShaderNodeAttribute", _attribute_name="ft").outputs["Fac"]
    geo = nb.node("ShaderNodeNewGeometry")
    # grain runs along the piece, gently waving
    wav = nb.noise(tc, 6, 3, .5)
    gz = nb.add(z, nb.mul(wav, .02), nb.mul(y, .15))
    gvec = nb.node("ShaderNodeCombineXYZ", X=nb.mul(x, 1.0), Y=nb.mul(gz, 1.0), Z=nb.mul(y, 1.0)).outputs[0]
    gstr = nb.node("ShaderNodeMapping", Vector=gvec, Scale=(1.0, 9.0, 9.0)).outputs[0]
    zones = nb.noise(tc, 15, 5, .6, .4)
    fib = nb.noise(nb.node("ShaderNodeMapping", Vector=gvec, Scale=(1.0, 90.0, 90.0)).outputs[0], 22, 3, .6)
    meat = nb.ramp(nb.add(nb.mul(zones, 1.2), nb.mul(fib, .45), -.35),
                   [(0, srgb("BC3833")), (.3, srgb("A6292D")), (.55, srgb("8C1F26")), (.8, srgb("74171F")), (1, srgb("561019"))])
    # intramuscular marbling: long thin veins running with the grain + small elongated flecks, in clusters
    vgr = nb.node("ShaderNodeMapping", Vector=gvec, Scale=(1.0, 22.0, 22.0)).outputs[0]
    vn = nb.noise(vgr, 6, 2, .45, .0)
    vein = nb.mapr(nb.math("ABSOLUTE", nb.math("SUBTRACT", vn, .5)), .012, .0)
    vein = nb.mul(vein, nb.mapr(nb.noise(nb.node("ShaderNodeMapping", Vector=gvec, Scale=(1.0, 3.0, 3.0)).outputs[0], 12, 2, .5), .42, .56))
    clus = nb.mapr(nb.noise(tc, 10, 3, .5, .2), .3, .55)
    vein = nb.mul(vein, clus)
    fl = nb.noise(nb.node("ShaderNodeMapping", Vector=gvec, Scale=(1.0, 4.5, 4.5)).outputs[0], 140, 2, .5)
    fleck = nb.mul(nb.mapr(fl, .64, .69), nb.mapr(nb.noise(tc, 16, 3), .32, .55))
    fl2 = nb.noise(nb.node("ShaderNodeMapping", Vector=gvec, Scale=(1.0, 3.0, 3.0)).outputs[0], 320, 2, .5)
    fleck = nb.math("MAXIMUM", fleck, nb.mul(nb.mapr(fl2, .7, .74), nb.mapr(nb.noise(tc, 9, 3), .42, .62)))
    seam = nb.mapr(nb.math("ABSOLUTE", nb.math("SUBTRACT", nb.noise(nb.node("ShaderNodeMapping", Vector=gvec, Scale=(1.0, 4.0, 4.0)).outputs[0], 2.5, 2, .4), .5)), .006, .0)
    marb = nb.math("MAXIMUM", nb.math("MAXIMUM", vein, nb.mul(fleck, .8)), nb.mul(seam, .45))
    fstreak = nb.mapr(fib, .55, .75)
    meat = nb.mix(nb.mul(fstreak, .3), meat, srgb("C9554B"))
    dstreak = nb.mapr(fib, .42, .25)
    meat = nb.mix(nb.mul(dstreak, .3), meat, srgb("5A1118"))
    if cut == "fraldinha":
        marb = nb.mul(marb, .6)
    fatc = nb.ramp(nb.noise(tc, 60, 3), [(0, srgb("FBF1DE")), (1, srgb("F0DCB8"))])
    halo = nb.mapr(marb, .0, .5)
    base = nb.mix(nb.mul(halo, .35), meat, srgb("D9706A"))
    base = nb.mix(nb.mapr(marb, .25, .7), base, fatc)
    # cut ends a little darker and drier
    ends = nb.math("MAXIMUM", nb.mapr(s, .06, .0), nb.mapr(s, .94, 1.0))
    base = nb.mix(nb.mul(ends, .45), base, srgb("5E1016"))
    # fat cap on top: creamy, smooth, wavy boundary
    edge = nb.math("SUBTRACT", 1.0, ft)
    edge = nb.add(edge, nb.mul(nb.math("SUBTRACT", nb.noise(tc, 30, 3), .5), .08))
    cap = nb.node("ShaderNodeMapRange", Value=hz, **{"From Min": edge, "From Max": nb.add(edge, .04), "To Min": 0.0, "To Max": 1.0},
                  _interpolation_type="SMOOTHSTEP", _clamp=True).outputs[0]
    cap = nb.mul(cap, nb.mapr(ft, .0, .02))
    fatcap = nb.ramp(nb.add(nb.mul(nb.noise(tc, 25, 5, .6), .7), nb.mul(hz, .3)), [(0, srgb("F2DDB4")), (.5, srgb("F6E6C6")), (1, srgb("FCF5E6"))])
    base = nb.mix(cap, base, fatcap)
    rim = nb.mul(cap, nb.mapr(cap, 1.0, .5))
    base = nb.mix(nb.mul(rim, .4), base, srgb("F2C9B2"))
    h = nb.add(nb.mul(fib, .6), nb.mul(marb, .4), nb.mul(cap, nb.noise(tc, 40, 3)))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.42, nb.mul(cap, -.08), nb.mul(fib, .12)),
               "Coat Weight": nb.add(.22, nb.mul(cap, -.05)), "Coat Roughness": .18, "Specular IOR Level": .5,
               "Subsurface Weight": nb.add(.12, nb.mul(cap, .4)), "Subsurface Radius": (1, .55, .35), "Subsurface Scale": .006,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.22, Distance=.0006).outputs[0]})
    return mat


def build_meat_cuts():
    o = O("acougue") + Vector((0, 1.0, 0))
    c = col("Acougue cuts")
    wipe_collection(c.name)
    for i, cut in enumerate(CUTS):
        ob = mesh_object("cut_" + cut, meat_cut_bm(cut), beef_material(cut), c, subsurf=1)
        ob.location = o + Vector((i * 1.0, 0, .0005))
    catcher("acougue", o + Vector((1.0, .1, 0)), (3.4, 1.0), "Catcher_cuts")


def meat_profile(path, bins=120):
    a = img_load(path)
    h, w = a.shape[:2]
    m = a[..., 3] > .5            # same rule as the game: alpha > 0.5 (shadows are capped at 0.45)
    cols = np.where(m.any(0))[0]
    l, r = int(cols.min()), int(cols.max())
    hts = np.zeros(w, np.float32)
    for xx in range(l, r + 1):
        ys = np.where(m[:, xx])[0]
        if len(ys):
            hts[xx] = (ys.max() - ys.min() + 1) / h
    prof = []
    for k in range(bins):
        a0 = l + (r + 1 - l) * k / bins
        a1 = l + (r + 1 - l) * (k + 1) / bins
        seg = hts[int(a0):max(int(a0) + 1, int(a1))]
        prof.append(round(float(seg.mean()), 4))
    rows = np.where(m.any(1))[0]
    return {"profile": prof, "x_range": [l, r], "y_range_from_bottom": [int(h - 1 - rows.max()), int(h - 1 - rows.min())],
            "size": [w, h]}


def render_piece_acougue2(cut):
    ob = bpy.data.objects["cut_" + cut]
    L, D, th, fat = cut_shape(cut)
    size = (MEAT_RES[0] / MEAT_PXM, MEAT_RES[1] / MEAT_PXM)
    center = ob.location + Vector((0, 0, .055))
    path = shoot(center, size, MEAT_RES, os.path.join(OUT, "pz_meat_%s.png" % cut), True, [ob.name, "Catcher_cuts"], "front", MEAT_TILT)
    manifest_update("pz_meat_%s" % cut, meat_profile(path))
    return path


def mockup_acougue2(cut="picanha"):
    bench = load("pz_bench_acougue.png")
    bench[..., 3] = 1
    sp = load("pz_meat_%s.png" % cut)
    place(bench, sp, 800, 430, 1500, None)
    for cx in (800 - 1460 * .17, 800 + 1460 * .16):
        g = blank(5, 300, (1, 1, 1), .85)
        over(bench, g, int(cx) - 2, 270)
        hd = blank(40, 56, srgb_f("3B2A1E"), 1.0)
        hd[..., 3] = rounded_mask(40, 56, 12)
        over(bench, hd, int(cx) - 20, 214)
    bench[..., 3] = 1
    return save_png(bench, "mockup_acougue.png")


def run_acougue2():
    out = [render_piece_acougue2(c) for c in CUTS]
    out.append(mockup_acougue2())
    return out



# ============================================================================================ PEIXARIA v2: shard ice, meltwater, retail scale
_SHARDS = []


def shard_templates(n=20, seed=91):
    """Irregular faceted ice chips: convex hulls of random points, flattened a bit, tiny bevel for edge glints."""
    if _SHARDS:
        return _SHARDS
    rnd = random.Random(seed)
    for k in range(n):
        bm = bmesh.new()
        sx, sy, sz = 1.0, rnd.uniform(.55, 1.0), rnd.uniform(.35, .7)
        for i in range(rnd.randint(8, 13)):
            d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized() * rnd.uniform(.65, 1.0)
            bm.verts.new((d.x * sx, d.y * sy, d.z * sz))
        res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
        kill = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="VERTS")
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=.035, segments=1, affect="EDGES", clamp_overlap=True)
        bm.verts.index_update()
        vs = np.array([v.co[:] for v in bm.verts], np.float32)
        fs = [[v.index for v in f.verts] for f in bm.faces]
        bm.free()
        _SHARDS.append((vs, fs))
    return _SHARDS


def shard_ice(area, count, seed, size=(.006, .014), heap=None, zbase=0.0, layers=1.0):
    tpl = shard_templates()
    rnd = random.Random(seed)
    x0, y0, x1, y1 = area
    V, F = [], []
    off = placed = tries = 0
    while placed < count and tries < count * 12:
        tries += 1
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        hgt = heap(x, y) if heap else 1.0
        if hgt <= 0 or rnd.random() > hgt:
            continue
        s_ = rnd.uniform(*size)
        vs, fs = tpl[rnd.randrange(len(tpl))]
        R = np.array(Matrix.Rotation(rnd.uniform(0, 6.28), 3, "Z") @ Matrix.Rotation(rnd.uniform(-.5, .5), 3, "Y") @
                     Matrix.Rotation(rnd.uniform(-.5, .5), 3, "X"), np.float32)
        p = (vs * s_) @ R.T + np.array([x, y, zbase + hgt * layers * .018 * rnd.random() + s_ * .25], np.float32)
        V.append(p)
        F.extend([[i + off for i in f] for f in fs])
        off += len(vs)
        placed += 1
    me = bpy.data.meshes.new("_ice")
    me.from_pydata(np.concatenate(V).tolist(), [], F)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def ice_material2():
    mat = mat_get("M_ice2")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 180, 4)
    frost = nb.mapr(nb.noise(tc, 70, 5, .6), .5, .72)
    ao = nb.node("ShaderNodeAmbientOcclusion", Distance=.01, _samples=8).outputs["AO"]
    occ = nb.mapr(ao, .95, .45)
    base = nb.ramp(nb.add(nb.mul(n, .4), nb.mul(frost, .6)), [(0, srgb("EAF7FC")), (1, srgb("FFFFFF"))])
    base = nb.mix(nb.mul(occ, .45), base, srgb("6FA9CF"))
    bubbles = nb.mapr(nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=900, _feature="F1").outputs["Distance"], .1, .03)
    base = nb.mix(nb.mul(bubbles, .4), base, srgb("FFFFFF"))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.02, nb.mul(frost, .3)), "IOR": 1.31,
               "Transmission Weight": nb.mul(nb.math("SUBTRACT", 1.0, frost), .5), "Specular IOR Level": 1.0,
               "Coat Weight": .6, "Coat Roughness": .02, "Subsurface Weight": .35, "Subsurface Radius": (.5, .75, 1),
               "Subsurface Scale": .008, "Emission Color": nb.mix(occ, srgb("E6F7FD"), srgb("8DC0DD")), "Emission Strength": .14})
    return mat


def water_material():
    mat = mat_get("M_meltwater")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 25, 4, .6)
    a = nb.mapr(n, .35, .55)
    nb.bsdf(**{"Base Color": srgb("9CCBE0"), "Roughness": .02, "Coat Weight": 1.0, "Coat Roughness": .01, "Specular IOR Level": .9,
               "Alpha": nb.mul(a, .55),
               "Normal": nb.node("ShaderNodeBump", Height=nb.noise(tc, 60, 3), Strength=.08, Distance=.001).outputs[0]})
    return mat


def puddle_bm(rx, ry, seed=0, n=72):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + .18 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, seed)))
        pts.append((rx * k * math.cos(a), ry * k * math.sin(a)))
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0)) for x, y in pts]
    bm.faces.new(vs)
    return bm


def build_bench_peixaria2():
    o = O("peixaria") + Vector((0, -2.0, 0))
    c = col("Peixaria bench")
    wipe_collection(c.name)
    W, H = BENCH_SIZE
    top = mesh_object("PB_Top", quad_bm(W * 1.04, H * 1.04), steel_counter_material(), c, subsurf=0)
    top.location = o
    def heap_tl(x, y):
        d = math.hypot((x + .66) / .44, (y - .38) / .27)
        return max(0.0, 1 - d ** 3)
    def heap_br(x, y):
        d = math.hypot((x - .66) / .44, (y + .38) / .26)
        return max(0.0, 1 - d ** 3)
    ib = shard_ice((-.66, .1, -.2, .38), 2600, 1, size=(.007, .016), heap=heap_tl, layers=1.4)
    bm_join(ib, shard_ice((.2, -.38, .66, -.1), 2600, 2, size=(.007, .016), heap=heap_br, layers=1.4))
    mesh_object("PB_Ice", ib, ice_material2(), c, subsurf=0, smooth_shade=False).location = o
    wm = water_material()
    for k, (x, y, rx, ry) in enumerate(((-.56, .3, .2, .13), (.56, -.3, .21, .13))):
        pu = mesh_object("PB_Water%d" % k, puddle_bm(rx, ry, k), wm, c, subsurf=0)
        pu.location = o + Vector((x, y, .0008))
    lm = lemon_material()
    for k, (lx, ly, lz) in enumerate(((-.5, .25, .024), (-.4, .31, .018), (.5, -.25, .022))):
        lo = mesh_object("PB_Lemon%d" % k, lemon_half_bm(.04, .03), lm, c, subsurf=1)
        lo.location = o + Vector((lx, ly, lz))
        lo.rotation_euler = (math.radians(6 * (k - 1)), math.radians(4), 0)
    pm = leaf_material("M_parsley", "3E8F3A", "6DB352")
    for k, (px, py, pr) in enumerate(((.47, .26, 200), (.53, .3, 230), (.43, .31, 170), (.36, -.31, 20))):
        po = mesh_object("PB_Parsley%d" % k, parsley_bm(k), pm, c, subsurf=1)
        po.location = o + Vector((px, py, 0 if k < 3 else .016))
        po.rotation_euler.z = math.radians(pr)
    knife(c, "PB_Knife", o + Vector((-.43, -.3, 0)), 12, blade_len=.21, blade_w=.03, handle_len=.12, kind="chef",
          blade_mat=metal_material("M_steel_p", "8F9AA2", .25),
          handle_mat=simple_material("M_knife_poly", "1F8F85", .35, var="25A193", coat=.3))


SCALE_PXM = 4000.0          # the scale sprite is rendered at 2x the game's 260 x 150 px


def build_scale(c, at):
    w, h = 260 / 2000, 150 / 2000
    names = []
    body_m = metal_material("M_scale_steel", "B9C3CA", .28)
    body = rounded_slab(w, h, .014, .012)
    ob = mesh_object("SC_Body", body, body_m, c, subsurf=1)
    ob.location = at
    names.append(ob.name)
    # recessed dark gap under the plate + the brushed weighing plate on top
    pw, ph = w - .012, h - .034
    gap = rounded_slab(pw + .002, ph + .002, .0155, .009)
    xform(gap, loc=(0, .006, 0))
    g = mesh_object("SC_Gap", gap, simple_material("M_scale_gap", "39424A", .5), c, subsurf=1)
    g.location = at
    plate = rounded_slab(pw, ph, .004, .008)
    xform(plate, loc=(0, .006, .016))
    pm = mat_get("M_scale_plate")
    nb = NB(pm)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    sv = nb.node("ShaderNodeMapping", Vector=tc, Scale=(2, 900, 1)).outputs[0]
    br = nb.noise(sv, 1.0, 4, .55)
    nb.bsdf(**{"Base Color": nb.ramp(br, [(0, srgb("CBD3D9")), (1, srgb("EEF2F5"))]), "Metallic": .9, "Roughness": nb.add(.18, nb.mul(br, .12)),
               "Normal": nb.node("ShaderNodeBump", Height=br, Strength=.12, Distance=.0004).outputs[0]})
    p = mesh_object("SC_Plate", plate, pm, c, subsurf=1)
    p.location = at
    # display: dark glass window in a bezel along the front edge, two small buttons (no digits)
    bz = rounded_slab(w - .018, .019, .0152, .005)
    xform(bz, loc=(0, -h / 2 + .0115, 0))
    b = mesh_object("SC_Bezel", bz, simple_material("M_scale_bezel", "5E6971", .35, var="6E7A82"), c, subsurf=1)
    b.location = at
    dw = rounded_slab(w - .05, .012, .0156, .003)
    xform(dw, loc=(-.008, -h / 2 + .0115, 0))
    dm = mat_get("M_scale_display")
    nb = NB(dm)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    refl = nb.mapr(nb.add(x, nb.mul(y, -2.0)), -.02, .03)
    nb.bsdf(**{"Base Color": nb.mix(nb.mul(refl, .25), srgb("142028"), srgb("2E4250")), "Roughness": .05, "Coat Weight": 1.0,
               "Coat Roughness": .02, "Specular IOR Level": .9})
    d = mesh_object("SC_Display", dw, dm, c, subsurf=1)
    d.location = at
    for k, hexc in enumerate(("1F8F85", "F08A2C")):
        bt = lathe_bm([(0, .0152), (.0032, .0152), (.0034, .0165), (.0026, .0178), (0, .018)], 24)
        xform(bt, loc=(w / 2 - .022 + k * .0095, -h / 2 + .0115, 0))
        bo = mesh_object("SC_Btn%d" % k, bt, simple_material("M_btn_" + hexc, hexc, .3, coat=.6), c, subsurf=1)
        bo.location = at
        names.append(bo.name)
    names += [g.name, p.name, b.name, d.name]
    return names


def build_icebed2():
    o = O("peixaria") + Vector((0, -4.0, 0))
    c = col("Peixaria parts")
    wipe_collection(c.name)
    w, h = 1540 / MPX, 690 / MPX
    tray = rounded_slab(w, h, .012, 22 / MPX)
    mesh_object("PP_IceTray", tray, steel_counter_material(), c, subsurf=1).location = o
    ib = shard_ice((-w / 2 + .012, -h / 2 + .012, w / 2 - .012, h / 2 - .012), 9000, 5, size=(.007, .014), zbase=.009)
    mesh_object("PP_Ice", ib, ice_material2(), c, subsurf=0, smooth_shade=False).location = o
    wb = quad_bm(w - .02, h - .02)
    wa = mesh_object("PP_Water", wb, water_material(), c, subsurf=0)
    wa.location = o + Vector((0, 0, .0125))
    build_scale(c, o + Vector((1.0, 0, 0)))
    catcher("peixaria", o + Vector((.5, 0, -.0005)), (2.6, 1.2), "Catcher_pparts")


SCALE_PARTS = ["SC_Body", "SC_Gap", "SC_Plate", "SC_Bezel", "SC_Display", "SC_Btn0", "SC_Btn1"]


def render_scale():
    o = O("peixaria") + Vector((1.0, -4.0, 0))
    p = shoot(o + Vector((0, 0, .01)), (560 / SCALE_PXM, 340 / SCALE_PXM), (560, 340), os.path.join(OUT, "pz_scale.png"), True,
              SCALE_PARTS + ["Catcher_pparts"])
    a = img_load(p)
    save_png(img_resize(a, 300, 182), "mockup_part_scale.png")
    return p


def render_icebed2():
    o = O("peixaria") + Vector((0, -4.0, 0))
    return shoot(o, (1600 / MPX, 760 / MPX), (1600, 760), os.path.join(OUT, "mockup_part_icebed.png"), True,
                 ["PP_IceTray", "PP_Ice", "PP_Water", "Catcher_pparts"])


def mockup_peixaria2():
    bench = load("pz_bench_peixaria.png")
    bench[..., 3] = 1
    place(bench, load("mockup_part_icebed.png"), 800, 547)
    sc = load("pz_scale.png")
    for t in range(3):
        place(bench, sc, 800 + (t - 1) * 290, 89, 280, None)
    unit = 82
    looks = {"peixe": (1.9, .8), "file": (1.3, .62), "camarao": (.9, .72), "salmao": (1.4, .62)}
    pieces = ["peixe", "salmao", "camarao", "file", "peixe", "salmao"]
    for i, k in enumerate(pieces):
        row, colm = i // 3, i % 3
        cx = 800 + (colm - 1) * (1480 / 3)
        cy = 547 - (1 if row == 0 else -1) * 690 * .22
        w, h = looks[k]
        place(bench, load("pz_fish_%s.png" % k), cx, cy, int(w * unit * 1.9), int(h * unit * 1.9))
    place(bench, load("pz_fish_file.png"), 800, 76, int(1.3 * unit * 1.2), int(.62 * unit * 1.2))
    bench[..., 3] = 1
    return save_png(bench, "mockup_peixaria.png")


# ============================================================================================ GLASS SPRITES (sucos, adega)
GLASS_TILT = 8.0


def glass_material(name="M_glass"):
    mat = mat_get(name)
    nb = NB(mat)
    nb.bsdf(**{"Base Color": (1, 1, 1, 1), "Roughness": .02, "Transmission Weight": 1.0, "IOR": 1.45, "Specular IOR Level": .6})
    return mat


def glass_shadow_material():
    mat = mat_get("M_glass_shadow")
    nb = NB(mat)
    tr = nb.node("ShaderNodeBsdfTransparent")
    df = nb.node("ShaderNodeBsdfDiffuse", Color=(.2, .25, .22, 1))
    mx = nb.node("ShaderNodeMixShader", Fac=.18)
    nb.nt.links.new(tr.outputs[0], mx.inputs[1])
    nb.nt.links.new(df.outputs[0], mx.inputs[2])
    o = nb.node("ShaderNodeOutputMaterial")
    nb.nt.links.new(mx.outputs[0], o.inputs["Surface"])
    return mat


def glass_mask_material(base_z=0.0, rim_z=1.0):
    """Emission = how 'dense' the glass looks: grazing walls, thick base and rim."""
    mat = mat_get("M_glass_mask")
    nb = NB(mat)
    lw = nb.node("ShaderNodeLayerWeight", Blend=.5)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    z = nb.sep(tc)[2]
    attr = nb.node("ShaderNodeAttribute", _attribute_name="dense").outputs["Fac"]
    e = nb.math("POWER", lw.outputs["Facing"], 2.2)
    e = nb.math("MAXIMUM", e, attr)
    em = nb.node("ShaderNodeEmission", Color=(1, 1, 1, 1), Strength=e)
    o = nb.node("ShaderNodeOutputMaterial")
    nb.nt.links.new(em.outputs[0], o.inputs["Surface"])
    return mat


def holdout_material():
    mat = mat_get("M_holdout")
    nb = NB(mat)
    h = nb.node("ShaderNodeHoldout")
    o = nb.node("ShaderNodeOutputMaterial")
    nb.nt.links.new(h.outputs[0], o.inputs["Surface"])
    return mat


def emitter_material(strength=6.0):
    mat = mat_get("M_softbox_%d" % int(strength * 10))
    nb = NB(mat)
    em = nb.node("ShaderNodeEmission", Color=(1, .97, .92, 1), Strength=strength)
    o = nb.node("ShaderNodeOutputMaterial")
    nb.nt.links.new(em.outputs[0], o.inputs["Surface"])
    return mat


def softboxes(c, prefix, at, dist=.6, height=.5):
    """Two tall strips (front-left strong, front-right weak) + a top card, only seen in reflections."""
    names = []
    for k, (ang, w, hgt, st, z) in enumerate(((-48, .1, height * 1.6, 9.0, .1), (62, .06, height * 1.6, 4.0, .1), (0, .5, .2, 3.0, .55))):
        bm = quad_bm(w, hgt)
        ob = mesh_object("%s_Soft%d" % (prefix, k), bm, emitter_material(st), c, subsurf=0)
        a = math.radians(ang)
        if k < 2:
            ob.location = at + Vector((math.sin(a) * dist, -math.cos(a) * dist, z + hgt * .15))
            ob.rotation_euler = (math.radians(90), 0, a)
        else:
            ob.location = at + Vector((0, -dist * .5, z + .3))
            ob.rotation_euler = (math.radians(55), 0, 0)
        ob.visible_camera = False
        ob.visible_shadow = False
        ob.visible_diffuse = False
        names.append(ob.name)
    return names


def set_dense(ob, fn):
    """Per-vertex 'dense' attribute (0..1) from fn(co) — thick base / rim / handle read denser."""
    me = ob.data
    a = me.attributes.get("dense") or me.attributes.new("dense", "FLOAT", "POINT")
    for i, v in enumerate(me.vertices):
        a.data[i].value = fn(v.co)


def render_glass(name, glass, opaque, softs, center, size_m, res, tint="AFDCD5", tilt=GLASS_TILT, catcher_name=None,
                 a0=.05, a1=.65, edge_col="5E8F86"):
    """Three passes -> one straight-alpha sprite where the inside of the glass stays see-through:
    A reflections (glass on black, Standard view), M density mask (emission), B opaque parts + contact shadow."""
    sc = bpy.context.scene
    tmp = os.path.join(OUT, "_src")
    os.makedirs(tmp, exist_ok=True)
    mats = {n: [s.material for s in bpy.data.objects[n].material_slots] for n in glass + opaque}
    def assign(names, m):
        for n in names:
            ob = bpy.data.objects[n]
            for s in ob.material_slots:
                s.material = m
    def restore():
        for n, ms in mats.items():
            for s, m in zip(bpy.data.objects[n].material_slots, ms):
                s.material = m
    vt, lk = sc.view_settings.view_transform, sc.view_settings.look
    try:
        # A: reflections
        sc.view_settings.view_transform, sc.view_settings.look = "Standard", "None"
        set_world("glass", .7)
        assign(opaque, holdout_material())
        pa = shoot(center, size_m, res, os.path.join(tmp, name + "_A.png"), False, glass + opaque + softs, "front", tilt)
        # M: density mask
        assign(glass, glass_mask_material())
        set_world("warm", 0.0)
        pm = shoot(center, size_m, res, os.path.join(tmp, name + "_M.png"), True, glass + opaque, "front", tilt, sun="")
        restore()
        # B: opaque parts + shadow (glass casts a light shadow only)
        sc.view_settings.view_transform, sc.view_settings.look = vt, lk
        set_world("warm")
        assign(glass, glass_shadow_material())
        for n in glass:
            bpy.data.objects[n].visible_camera = False
        vis = glass + opaque + ([catcher_name] if catcher_name else [])
        pb = shoot(center, size_m, res, os.path.join(tmp, name + "_B.png"), True, vis, "front", tilt)
    finally:
        restore()
        for n in glass:
            bpy.data.objects[n].visible_camera = True
        sc.view_settings.view_transform, sc.view_settings.look = vt, lk
        set_world("warm")
    A, M, B = img_load(pa), img_load(pm), img_load(pb)
    cov = M[..., 3]
    E = np.clip(M[..., 0], 0, 1)
    lum = A[..., :3].max(-1)
    tint_c = np.array(srgb_f(tint), np.float32)
    edge_c = np.array(srgb_f(edge_col), np.float32)
    base_a = cov * (a0 + a1 * E ** 2.2)
    base_c = tint_c[None, None, :] * (1 - E[..., None]) + edge_c[None, None, :] * E[..., None]
    ha = np.clip((lum - .09) * 1.8, 0, .95) * np.clip(cov * 4, 0, 1)
    hc = np.clip(A[..., :3] / np.maximum(lum, 1e-4)[..., None], 0, 1) * .25 + .75
    ga = ha + base_a * (1 - ha)
    gc = (hc * ha[..., None] + base_c * (base_a * (1 - ha))[..., None]) / np.maximum(ga, 1e-5)[..., None]
    glass_l = np.concatenate([gc, ga[..., None]], -1).astype(np.float32)
    out = B.copy()
    over(out, glass_l, 0, 0)
    return save_png(out, name + ".png"), glass_l


def glass_stats(name, rect):
    """Alpha inside the liquid rect; 'frac_over_025_no_hl' ignores the reflection streaks (pass A brighter than .25)."""
    a = load(name + ".png")
    A = img_load(os.path.join(OUT, "_src", name + "_A.png"))
    h = a.shape[0]
    l, b, r, t = rect
    sub = a[h - t:h - b, l:r, 3]
    hl = A[h - t:h - b, l:r, :3].max(-1) > .25
    return {"median_alpha": round(float(np.median(sub)), 3), "frac_over_025_no_hl": round(float((sub[~hl] > .25).mean()), 3),
            "highlight_frac": round(float(hl.mean()), 3)}


def project_px(p, res):
    """World point -> pixel (x from left, y from bottom) through the current camera."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    v = world_to_camera_view(sc, sc.camera, Vector(p))
    return v.x * res[0], v.y * res[1]


def inner_rect(center, size_m, res, r_in, z_bot, z_top, tilt=GLASS_TILT, shrink=5, axis=None):
    """Pixel rect (l, b, r, t from bottom-left) of the liquid column inside a round vessel of inner radius r_in."""
    sc = bpy.context.scene
    cam = bpy.data.objects["Cam"]
    t = math.radians(tilt)
    d = Vector((0, math.cos(t), -math.sin(t)))
    c = Vector(center)
    cam.location = c - d * 5.0
    cam.rotation_euler = (math.pi / 2 - t, 0, 0)
    cam.data.ortho_scale = max(size_m)
    sc.render.resolution_x, sc.render.resolution_y = res
    bpy.context.view_layer.update()
    x0 = axis.x if axis is not None else c.x
    l, _ = project_px((x0 - r_in, c.y, z_bot), res)
    r, _ = project_px((x0 + r_in, c.y, z_bot), res)
    _, b = project_px((x0, c.y - r_in, z_bot), res)       # front of the bottom ellipse
    _, tp = project_px((x0, c.y, z_top), res)             # liquid surface line (centre)
    return [int(math.ceil(l)) + shrink, int(math.ceil(b)) + shrink, int(r) - shrink, int(tp)]


def shell_profile(outer, wall=.0028, base=.012, rim=.0016, round_floor=0.0):
    """outer: [(r, z)] bottom->top (first r>0 at z=0). Returns a closed lathe profile with a thick base and a
    rounded rim: outer up, round over the rim, inner wall back down (offset inwards), inner floor."""
    prof = [(0.0, 0.0)] + list(outer)
    rT, zT = outer[-1]
    for k in range(1, 6):
        a = math.pi * k / 6
        prof.append((rT - rim + rim * math.cos(a), zT + rim * math.sin(a)))
    inner = []
    for i in range(len(outer) - 1, -1, -1):
        r, z = outer[i]
        if z < base:
            continue
        inner.append((max(.0005, r - wall), z))
    if round_floor:
        rin = inner[-1][0]
        zf = inner[-1][1]
        inner = [p for p in inner if p[1] > base + round_floor]
        for k in range(1, 7):
            a = math.pi / 2 * k / 6
            inner.append(((rin - round_floor) + round_floor * math.cos(a), base + round_floor - round_floor * math.sin(a)))
    else:
        inner.append((max(.0005, outer[0][0] - wall - .004), base))
    prof += inner
    prof.append((0.0, base))
    return prof


# ============================================================================================ SUCOS
JUG = dict(R=.042, H=.25, res=(240, 560))


def build_jug(c, at):
    R, H = JUG["R"], JUG["H"]
    outer = [(R - .006, 0), (R - .0015, .0012), (R, .006)] + [(R + .0008 * math.sin(math.pi * k / 10), .006 + (H - .006) * k / 10) for k in range(1, 11)]
    bm = lathe_bm(shell_profile(outer, wall=.0026, base=.013), 96)
    jug = mesh_object("JG_Glass", bm, glass_material(), c, subsurf=1)
    jug.location = at
    # handle: a C-shaped glass rod on the right
    pts = []
    for i in range(25):
        t = i / 24
        a = math.radians(-80 + 160 * t)
        pts.append((R - .002 + .026 * math.cos(a) * (1 - .1 * math.sin(math.pi * t)), 0, H * .52 + .072 * math.sin(a)))
    hb = tube_bm(spline(pts, 2), lambda t: .0062 * (1 - .25 * math.sin(math.pi * t)), 16)
    hd = mesh_object("JG_Handle", hb, glass_material(), c, subsurf=1)
    hd.location = at
    set_dense(jug, lambda co: max(min(1.0, max(0.0, (.016 - co.z) / .01)) * .75, min(1.0, max(0.0, (co.z - (H - .004)) / .004)) * .6))
    set_dense(hd, lambda co: .55)
    return [jug.name, hd.name]


def build_sucos_pieces():
    o = O("sucos")
    c = col("Sucos pieces")
    wipe_collection(c.name)
    g = build_jug(c, o)
    soft = softboxes(c, "JG", o)
    catcher("sucos", o + Vector((0, .1, 0)), (1.2, 1.2))
    return g, soft


def render_piece_sucos(kind="jug"):
    o = O("sucos")
    res = JUG["res"]
    size = (res[0] / MPX, res[1] / MPX)
    center = o + Vector((.008, 0, JUG["H"] * .5 + .006))
    soft = [n for n in ("JG_Soft0", "JG_Soft1", "JG_Soft2")]
    path, _ = render_glass("pz_jug_glass", ["JG_Glass", "JG_Handle"], [], soft, center, size, res, catcher_name="Catcher_sucos")
    rect = inner_rect(center, size, res, JUG["R"] - .0026, .017, JUG["H"] - .02, axis=o)
    m = manifest_update("pz_jug_glass", {"inner": rect, "size": list(res), "check": glass_stats("pz_jug_glass", rect)})
    return path


def fruit_skin_material(name, c0, c1, pore=900, rough=.4, coat=.3, pore_amt=.6):
    mat = mat_get(name)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 40, 5, .6)
    vor = nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=pore, _feature="F1").outputs["Distance"]
    pores = nb.mapr(vor, .3, .0)
    base = nb.ramp(nb.add(nb.mul(n, .7), nb.mul(pores, .2)), [(0, srgb(c0)), (1, srgb(c1))])
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(rough, nb.mul(pores, .1)), "Coat Weight": coat, "Coat Roughness": .2,
               "Subsurface Weight": .2, "Subsurface Radius": (1, .7, .3), "Subsurface Scale": .004,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(nb.mul(pores, -pore_amt), nb.mul(n, .2)), Strength=.3, Distance=.0006).outputs[0]})
    return mat


def citrus_cut_material(name, pulp0, pulp1, pith, peel, R, segs=10):
    mat = mat_get(name)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    geo = nb.node("ShaderNodeNewGeometry")
    nz = nb.sep(geo.outputs["Normal"])[2]
    r = nb.math("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    ang = nb.math("ARCTAN2", y, x)
    n = nb.noise(tc, 150, 4)
    seg = nb.math("ABSOLUTE", nb.math("SUBTRACT", nb.math("FRACT", nb.mul(ang, segs / (2 * math.pi))), .5))
    memb = nb.mul(nb.mapr(seg, .44, .5), nb.mapr(r, R * .12, R * .2))
    cells = nb.mapr(nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=450, _feature="DISTANCE_TO_EDGE").outputs["Distance"], .0, .12)
    pulp = nb.ramp(nb.add(nb.mul(n, .5), nb.mul(cells, .4)), [(0, srgb(pulp0)), (1, srgb(pulp1))])
    face = nb.mix(memb, pulp, srgb(pith))
    face = nb.mix(nb.mapr(r, R * .84, R * .88), face, srgb(pith))
    face = nb.mix(nb.mapr(r, R * .94, R * .97), face, srgb(peel))
    face = nb.mix(nb.mapr(r, R * .12, R * .06), face, srgb(pith))
    skin = nb.ramp(n, [(0, srgb(peel)), (1, srgb(peel))])
    top = nb.mapr(nz, .8, .95)
    base = nb.mix(top, skin, face)
    h = nb.add(nb.mul(memb, .6), nb.mul(cells, .3))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.45, nb.mul(top, -.25)), "Coat Weight": nb.mul(top, .7), "Coat Roughness": .1,
               "Subsurface Weight": .35, "Subsurface Radius": (1, .7, .3), "Subsurface Scale": .004,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.35, Distance=.0008).outputs[0]})
    return mat


def strawberry_bm(seed=0, s=1.0):
    bm = cube_sphere(30)
    for v in bm.verts:
        x, y, z = v.co
        t = (y + 1) / 2             # 0 tip .. 1 shoulder (lying on its side, tip towards -Y)
        w = (.35 + .65 * math.sin(math.pi * min(1.0, t * .62 + .2))) * s
        v.co = Vector((x * .016 * w, y * .021 * s, (z * .014 * w) + .013 * s))
    return bm


def strawberry_material():
    mat = mat_get("M_strawberry")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    vor = nb.node("ShaderNodeTexVoronoi", Vector=nb.node("ShaderNodeMapping", Vector=tc, Scale=(1, .8, 1)).outputs[0], Scale=210, Randomness=.5, _feature="F1")
    d = vor.outputs["Distance"]
    seed = nb.mapr(d, .14, .08)
    pit = nb.mapr(d, .26, .1)
    n = nb.noise(tc, 50, 4)
    base = nb.ramp(n, [(0, srgb("E2232E")), (1, srgb("C1121F"))])
    base = nb.mix(nb.mul(pit, .3), base, srgb("A50E1A"))
    base = nb.mix(seed, base, srgb("F2D46A"))
    nb.bsdf(**{"Base Color": base, "Roughness": .25, "Coat Weight": .6, "Coat Roughness": .1, "Subsurface Weight": .3,
               "Subsurface Radius": (1, .2, .2), "Subsurface Scale": .004,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(nb.mul(pit, -1.0), nb.mul(seed, .6)), Strength=.4, Distance=.0006).outputs[0]})
    return mat


def calyx_bm(seed=0):
    rnd = random.Random(seed)
    bm = bmesh.new()
    for k in range(6):
        a = 360 * k / 6 + rnd.uniform(-12, 12)
        pts = [(0, -.0018), (.009, -.0026), (.014, 0), (.009, .0026), (0, .0018)]
        lf = outline_slab(round_outline(pts, .0012, 2), .0009, bevel=.0003, segs=1)
        for v in lf.verts:
            v.co.z += .0018 * (v.co.x / .014) ** 2
        xform(lf, rot=(0, -15, a))
        bm_join(bm, lf)
    return bm


def pineapple_slice_material(R):
    mat = mat_get("M_pineapple")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    geo = nb.node("ShaderNodeNewGeometry")
    nz = nb.sep(geo.outputs["Normal"])[2]
    r = nb.math("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    ang = nb.math("ARCTAN2", y, x)
    n = nb.noise(tc, 120, 5)
    fib = nb.mapr(nb.math("SINE", nb.add(nb.mul(ang, 70), nb.mul(n, 4))), .3, 1.0)
    flesh = nb.ramp(nb.add(nb.mul(nb.mapr(r, R * .2, R * .9), .6), nb.mul(fib, .3)), [(0, srgb("FFF0A0")), (.5, srgb("FFDD55")), (1, srgb("F7C531"))])
    core = nb.mapr(r, R * .24, R * .2)
    flesh = nb.mix(core, flesh, srgb("FFF6CE"))
    eyes = nb.mul(nb.mul(nb.mapr(r, R * .8, R * .84), nb.mapr(r, R * .9, R * .87)), nb.mapr(nb.math("ABSOLUTE", nb.math("SINE", nb.mul(ang, 9))), .25, .0))
    flesh = nb.mix(nb.mul(eyes, .7), flesh, srgb("B88A2A"))
    rind = nb.mapr(r, R * .9, R * .93)
    skin = nb.ramp(nb.add(nb.mul(nb.math("ABSOLUTE", nb.math("SINE", nb.mul(ang, 14))), .6), nb.mul(n, .4)), [(0, srgb("6E5A1E")), (.5, srgb("8E7A2C")), (1, srgb("5E7A2A"))])
    face = nb.mix(rind, flesh, skin)
    side = nb.ramp(n, [(0, srgb("9C7A2A")), (1, srgb("C29A3A"))])
    base = nb.mix(nb.mapr(nz, .8, .95), side, face)
    nb.bsdf(**{"Base Color": base, "Roughness": .35, "Coat Weight": .5, "Coat Roughness": .1, "Subsurface Weight": .3,
               "Subsurface Radius": (1, .8, .3), "Subsurface Scale": .004,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(nb.mul(fib, .4), nb.mul(eyes, -.6)), Strength=.35, Distance=.0008).outputs[0]})
    return mat


def tile_counter_material(c0="F3E6CC", c1="E9D8B8", grout="CDB892", tile=.075):
    mat = mat_get("M_tiles_" + c0)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    fx = nb.math("FRACT", nb.math("DIVIDE", x, tile))
    fy = nb.math("FRACT", nb.math("DIVIDE", y, tile))
    ex = nb.math("MINIMUM", fx, nb.math("SUBTRACT", 1.0, fx))
    ey = nb.math("MINIMUM", fy, nb.math("SUBTRACT", 1.0, fy))
    e = nb.math("MINIMUM", ex, ey)
    g = nb.mapr(e, .022, .01)
    cid = nb.node("ShaderNodeCombineXYZ", X=nb.math("FLOOR", nb.math("DIVIDE", x, tile)), Y=nb.math("FLOOR", nb.math("DIVIDE", y, tile)), Z=0.0).outputs[0]
    rnd = nb.node("ShaderNodeTexWhiteNoise", Vector=cid, _noise_dimensions="3D").outputs["Value"]
    n = nb.noise(tc, 30, 5, .6)
    base = nb.ramp(nb.add(nb.mul(rnd, .6), nb.mul(n, .4)), [(0, srgb(c0)), (1, srgb(c1))])
    base = nb.mix(g, base, srgb(grout))
    bev = nb.mapr(e, .06, .02)
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.18, nb.mul(g, .6)), "Coat Weight": .5, "Coat Roughness": .08,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(nb.mul(bev, -.4), nb.mul(g, -1.0), nb.mul(n, .1)), Strength=.4, Distance=.002).outputs[0]})
    return mat


def orange_bm(R=.044, seed=0):
    return ellipsoid(R, R, R * .95, 4, seed=seed, lump=.015, lump_f=4)


def build_bench_sucos():
    o = O("sucos") + Vector((0, -2.0, 0))
    c = col("Sucos bench")
    wipe_collection(c.name)
    W, H = BENCH_SIZE
    top = mesh_object("SB_Top", quad_bm(W * 1.04, H * 1.04), tile_counter_material(), c, subsurf=0)
    top.location = o
    om = fruit_skin_material("M_orange", "F7931E", "E5770F", pore=700, rough=.35)
    for k, (x, y) in enumerate(((-.56, .29), (-.45, .33), (-.6, .17))):
        ob = mesh_object("SB_Orange%d" % k, orange_bm(seed=k), om, c, subsurf=1)
        ob.location = o + Vector((x, y, .042))
    hcm = citrus_cut_material("M_orange_cut", "FFA531", "FFC566", "FFE9C2", "F28A1A", .044, 11)
    oh = mesh_object("SB_OrangeHalf", lemon_half_bm(.044, .036), hcm, c, subsurf=1)
    oh.location = o + Vector((-.42, .23, 0))
    # limes, top-right
    lm = fruit_skin_material("M_lime", "5DAA2E", "3E8A1F", pore=800, rough=.3)
    for k, (x, y) in enumerate(((.56, .31), (.49, .34))):
        b = ellipsoid(.032, .037, .03, 4, seed=k + 5, lump=.02)
        ob = mesh_object("SB_Lime%d" % k, b, lm, c, subsurf=1)
        ob.location = o + Vector((x, y, .03))
        ob.rotation_euler.z = math.radians(30 * k + 20)
    lcm = citrus_cut_material("M_lime_cut", "A6D65A", "C8EA8A", "EEF7D8", "4F9A28", .033, 9)
    lh = mesh_object("SB_LimeHalf", lemon_half_bm(.033, .027), lcm, c, subsurf=1)
    lh.location = o + Vector((.47, .25, 0))
    # strawberries, bottom-left
    sm = strawberry_material()
    cm = leaf_material("M_calyx", "3E7A2E", "5E9A3A")
    for k, (x, y, r) in enumerate(((-.55, -.27, 20), (-.47, -.31, -40), (-.6, -.33, 80), (-.42, -.25, 150), (-.52, -.2, 110))):
        b = strawberry_bm(k, rnd_s := (1.45 - .06 * k))
        ob = mesh_object("SB_Straw%d" % k, b, sm, c, subsurf=1)
        ob.location = o + Vector((x, y, 0))
        ob.rotation_euler.z = math.radians(r)
        ca = mesh_object("SB_Calyx%d" % k, calyx_bm(k), cm, c, subsurf=1)
        a = math.radians(r)
        ca.location = o + Vector((x - math.sin(a) * -.021 * rnd_s, y + math.cos(a) * .021 * rnd_s, .013 * rnd_s))
        ca.rotation_euler = (math.radians(90), 0, a)
    # green grapes + pineapple slice, bottom-right
    grape_bunch(c, "SB_Grapes", o + Vector((.38, -.3, 0)), grape_material("M_grape_green", "9CC24A", "C9DD74", bloom=.5), n=24, seed=6, rot=110, r=.013,
                stem_mat=stem_material())
    R = .055
    pr = [(0, 0), (R * .98, 0), (R, .002), (R, .012), (R * .98, .014), (0, .014)]
    pm = mesh_object("SB_Pineapple", lathe_bm(pr, 64), pineapple_slice_material(R), c, subsurf=1)
    pm.location = o + Vector((.56, -.27, 0))
    lv = bmesh.new()
    for k in range(5):
        pts = [(0, -.004), (.05, -.003), (.075, 0), (.05, .003), (0, .004)]
        lf = outline_slab(pts, .0015, bevel=.0005, segs=1)
        xform(lf, rot=(0, -8, 140 + 14 * k), loc=(0, 0, .002 * k))
        bm_join(lv, lf)
    lo = mesh_object("SB_PineLeaf", lv, leaf_material("M_pine_leaf", "4C7F3A", "6C9E4C"), c, subsurf=1)
    lo.location = o + Vector((.62, -.17, .0))


def mockup_sucos():
    bench = load("pz_bench_bebidas.png")
    bench[..., 3] = 1
    with open(os.path.join(OUT, "manifest.json")) as f:
        man = json.load(f)
    l, b, r, t = man["pz_jug_glass"]["inner"]
    jug = load("pz_jug_glass.png")
    sw, sh = 240, 560
    scale = 120 / sw                           # the game draws the jug 120 px wide
    out_w, out_h = int(sw * scale), int(sh * scale)
    cols = ["F59A23", "E5484D", "8CCB3C", "7E4AA8", "F6D44A", "F2667E"]
    stacks = [[0, 1, 2, 0], [1, 2, 1], [2, 0, 1, 2], [3, 4], [4, 3, 4, 3], []]
    for j in range(6):
        cx = 800 + (j - 2.5) * 144
        cy = 440
        x0 = int(cx - out_w / 2)
        y0 = int(cy - out_h / 2)
        il, ir = x0 + l * scale, x0 + r * scale
        ib = y0 + out_h - b * scale
        it = y0 + out_h - t * scale
        unit = (ib - it) / 4
        for k, ci in enumerate(stacks[j]):
            y1 = ib - k * unit
            y2 = y1 - unit
            rgb = srgb_f(cols[ci])
            layer = blank(int(ir - il), int(y1 - y2) + 1, rgb, .92)
            layer[:3, :, :3] = np.minimum(1, np.array(rgb) * 1.25)
            over(bench, layer, int(il), int(y2))
        place(bench, jug, cx, cy, out_w, out_h)
    bench[..., 3] = 1
    return save_png(bench, "mockup_sucos.png")


def build_sucos():
    build_sucos_pieces()
    build_bench_sucos()


def run_sucos():
    out = [render_piece_sucos(), render_bench("sucos"), mockup_sucos()]
    return out



# ============================================================================================ SORVETES
FLAVORS = ["chocolate", "morango", "baunilha", "menta", "flocos", "limao"]
SCOOP_TILT = 24.0
SCOOP_R = .042


def scoop_bm(seed=0, R=SCOOP_R):
    """Scooped ball: smooth ridges left by the scoop across the top, a ruffled lip (drip skirt) at the base; sits on z=0."""
    rnd = random.Random(seed)
    bm = cube_sphere(64)
    off = Vector((seed * 3.7, seed * 1.3, 2.2))
    ang = rnd.uniform(-.6, .6)
    dirv = Vector((math.cos(ang), math.sin(ang) * .4, .9)).normalized()
    for v in bm.verts:
        p = v.co.copy()
        th = math.atan2(p.y, p.x)
        z = p.z
        r = 1 + .02 * noise.fractal(p * 2.0 + off, .5, 2.0, 2)
        band = math.sin(p.dot(dirv) * 9 + 1.2 * noise.noise(p * 1.3 + off)) * smooth(-.1, .5, z)
        r *= 1 + .028 * band
        q = p * r
        # lower cap: squashed into a flat base; around it the lip flares out with a wavy, drooping edge
        wav = .5 + .5 * math.sin(th * 8 + 2.0 * noise.noise(Vector((math.cos(th), math.sin(th), seed)) * 1.5))
        lip = smooth(-.25, -.62, z) * (1 - smooth(-.75, -.95, z))
        flare = 1 + lip * (.2 + .1 * wav)
        q.x *= flare
        q.y *= flare
        if z < -.5:
            q.z = -.5 + (z + .5) * .35
        q.z -= lip * (.05 + .05 * wav)
        v.co = q * R
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
    return bm


def icecream_material(flavor):
    mat = mat_get("M_ice_" + flavor)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n_m = nb.noise(tc, 40, 5, .6)
    n_f = nb.noise(tc, 350, 5, .65)
    look = {"chocolate": ("8A5232", "6A3A22", "4A2716"), "morango": ("F9B2C4", "F18FAA", "D9637F"),
            "baunilha": ("FFF1C8", "F7E1A8", "E8C985"), "menta": ("BFF0D9", "9FE3C4", "7FCFAE"),
            "flocos": ("FFFDF8", "F8F3EA", "EDE4D6"), "limao": ("EFF8B8", "DDEF94", "C6DD72")}[flavor]
    base = nb.ramp(nb.add(nb.mul(n_m, .7), nb.mul(n_f, .3), -.1), [(0, srgb(look[0])), (.6, srgb(look[1])), (1, srgb(look[2]))])
    bits = None
    if flavor == "morango":       # strawberry chunks + seeds
        vor = nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=70, Randomness=1.0, _feature="F1")
        sel = nb.mapr(nb.node("ShaderNodeTexWhiteNoise", Vector=vor.outputs["Position"]).outputs[0], .45, .5)
        bits = nb.mul(nb.mapr(vor.outputs["Distance"], .32, .2), sel)
        chunk = nb.ramp(n_f, [(0, srgb("D21E3C")), (1, srgb("E8445C"))])
        base = nb.mix(bits, base, chunk)
        swirl = nb.mapr(nb.noise(tc, 18, 4, .6, .8), .62, .7)
        base = nb.mix(nb.mul(swirl, .7), base, srgb("E35A7C"))
    elif flavor == "baunilha":    # vanilla specks
        sp = nb.mapr(nb.noise(tc, 700, 2, .5), .66, .72)
        base = nb.mix(nb.mul(sp, .9), base, srgb("3A281A"))
    elif flavor in ("menta", "flocos"):   # chocolate chips / flakes
        sv = tc if flavor == "menta" else nb.node("ShaderNodeMapping", Vector=tc, Scale=(1, 3.5, 1), Rotation=(.4, .2, .7)).outputs[0]
        vor = nb.node("ShaderNodeTexVoronoi", Vector=sv, Scale=70 if flavor == "menta" else 55, Randomness=1.0, _feature="F1")
        sel = nb.mapr(nb.node("ShaderNodeTexWhiteNoise", Vector=vor.outputs["Position"]).outputs[0], .3 if flavor == "menta" else .2, .36 if flavor == "menta" else .26)
        bits = nb.mul(nb.mapr(vor.outputs["Distance"], .26, .17), sel)
        base = nb.mix(bits, base, nb.ramp(n_f, [(0, srgb("2E1A10")), (1, srgb("4A2C1A"))]))
    elif flavor == "limao":       # zest specks
        sp = nb.mapr(nb.noise(tc, 700, 2, .5), .7, .76)
        base = nb.mix(nb.mul(sp, .7), base, srgb("7FB03A"))
    elif flavor == "chocolate":
        sp = nb.mapr(nb.noise(tc, 500, 3, .6), .68, .75)
        base = nb.mix(nb.mul(sp, .5), base, srgb("3E2012"))
    x, y, z = nb.sep(tc)
    curl = nb.math("SINE", nb.add(nb.mul(nb.add(nb.mul(x, .5), z), 2 * math.pi / .007), nb.mul(n_m, 6.0)))
    curl = nb.mul(nb.mapr(curl, -.2, 1.0), nb.mapr(z, .03, .06))
    grain = nb.noise(tc, 160, 6, .7)
    h = nb.add(nb.mul(n_f, .5), nb.mul(n_m, .2), nb.mul(curl, .5), nb.mul(grain, .5))
    if bits is not None:
        h = nb.add(h, nb.mul(bits, .5))
    nb.bsdf(**{"Base Color": base, "Roughness": .72 if flavor != "chocolate" else .6, "Coat Weight": .08, "Coat Roughness": .35,
               "Subsurface Weight": .35, "Subsurface Radius": (1, .85, .7), "Subsurface Scale": .006, "Sheen Weight": .15,
               "Normal": nb.node("ShaderNodeBump", Height=h, Strength=.5, Distance=.0012).outputs[0]})
    return mat


def cone_material():
    mat = mat_get("M_cone")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    ang = nb.math("ARCTAN2", y, x)
    k = 2 * math.pi / .014
    u = nb.add(nb.mul(ang, .03), nb.mul(z, .55))
    v = nb.math("SUBTRACT", nb.mul(ang, .03), nb.mul(z, .55))
    gu = nb.math("ABSOLUTE", nb.math("SINE", nb.mul(u, k / 1.6)))
    gv = nb.math("ABSOLUTE", nb.math("SINE", nb.mul(v, k / 1.6)))
    grid = nb.math("MINIMUM", gu, gv)
    groove = nb.mapr(grid, .22, .05)
    n = nb.noise(tc, 90, 5, .6)
    base = nb.ramp(nb.add(nb.mul(n, .6), nb.mul(groove, .5), -.1), [(0, srgb("EDBE78")), (.5, srgb("D9A05B")), (1, srgb("A8692C"))])
    nb.bsdf(**{"Base Color": base, "Roughness": .55, "Coat Weight": .15,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(nb.mul(groove, -1.0), nb.mul(n, .2)), Strength=.6, Distance=.0015).outputs[0]})
    return mat


def build_cone(c, at):
    R, H = .036, .105
    prof = [(0, 0)] + [(R * (k / 20) ** 1.02 * (1 + .03 * math.sin(k * .7)), H * k / 20) for k in range(1, 21)]
    # rolled rim at the top
    prof += [(R + .0025, H + .001), (R + .003, H + .005), (R + .0005, H + .008), (R - .0035, H + .006), (R - .004, H + .002)]
    prof += [(R * .9 * (k / 10), H * .98 * (k / 10) + .006) for k in range(9, 0, -1)] + [(0, .01)]
    bm = lathe_bm(prof, 96)
    ob = mesh_object("cone", bm, cone_material(), c, subsurf=1)
    ob.location = at
    return ob


def build_sorvetes_pieces():
    o = O("sorvetes")
    c = col("Sorvetes pieces")
    wipe_collection(c.name)
    for i, f in enumerate(FLAVORS):
        ob = mesh_object("scoop_" + f, scoop_bm(i + 1), icecream_material(f), c, subsurf=1)
        ob.location = o + Vector((i * .2, 0, 0))
    build_cone(c, o + Vector((1.4, 0, 0)))
    catcher("sorvetes", o + Vector((.7, .1, 0)), (2.4, 1.0))


def render_piece_sorvetes(kind):
    o = O("sorvetes")
    if kind == "cone":
        ob = bpy.data.objects["cone"]
        H = .118
        center = ob.location + Vector((0, 0, H * .52))
        return shoot(center, (240 / 2100, 320 / 2100), (240, 320), os.path.join(OUT, "pz_cone.png"), True, ["cone"], "front", 14)
    ob = bpy.data.objects["scoop_" + kind]
    center = ob.location + Vector((0, 0, SCOOP_R * .95))
    return shoot(center, (.112, .112), (300, 300), os.path.join(OUT, "pz_scoop_%s.png" % kind), True, [ob.name, "Catcher_sorvetes"], "front", SCOOP_TILT)


def terrazzo_material():
    mat = mat_get("M_terrazzo")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 6, 5, .6)
    base = nb.ramp(n, [(0, srgb("CDEBDD")), (1, srgb("BFE3D2"))])
    for sc, sel, hexc in ((90, .88, "F7B6C8"), (110, .9, "FFF4DE"), (70, .93, "F4C77A"), (130, .9, "8FD3BF")):
        vor = nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=sc, Randomness=1.0, _feature="F1")
        pick = nb.mapr(nb.node("ShaderNodeTexWhiteNoise", Vector=vor.outputs["Position"]).outputs[0], sel, sel + .02)
        chip = nb.mul(nb.mapr(vor.outputs["Distance"], .3, .22), pick)
        base = nb.mix(chip, base, srgb(hexc))
    nb.bsdf(**{"Base Color": base, "Roughness": .22, "Coat Weight": .6, "Coat Roughness": .06,
               "Normal": nb.node("ShaderNodeBump", Height=nb.noise(tc, 300, 3), Strength=.05, Distance=.001).outputs[0]})
    return mat


def build_bench_sorvetes():
    o = O("sorvetes") + Vector((0, -2.0, 0))
    c = col("Sorvetes bench")
    wipe_collection(c.name)
    W, H = BENCH_SIZE
    top = mesh_object("IB_Top", quad_bm(W * 1.04, H * 1.04), terrazzo_material(), c, subsurf=0)
    top.location = o
    # bowl of rainbow sprinkles, top-left, a few spilled
    prof = [(0, 0), (.04, 0), (.06, .01), (.07, .035), (.066, .037), (.056, .014), (.04, .008), (0, .008)]
    bowl = mesh_object("IB_Bowl", lathe_bm(spline(prof, 3), 64), simple_material("M_ibowl", "F49AB5", .25, coat=.7, var="F7A9C0"), c, subsurf=1)
    bowl.location = o + Vector((-.52, .26, 0))
    rnd = random.Random(9)
    cols = ["E5484D", "F6D44A", "54B6E8", "8CCB3C", "FFFFFF", "F28CA6", "9A6AD0"]
    sp = {h: bmesh.new() for h in cols}
    def sprinkle(x, y, z, h):
        t = tube_bm([(-.0035, 0, 0), (.0035, 0, 0)], .0011, 6)
        xform(t, loc=(x, y, z + .0011), rot=(rnd.uniform(-20, 20), rnd.uniform(-20, 20), rnd.uniform(0, 360)))
        bm_join(sp[h], t)
    for i in range(420):
        a, r = rnd.uniform(0, 6.28), .058 * math.sqrt(rnd.random())
        sprinkle(-.52 + r * math.cos(a), .26 + r * math.sin(a), .012 + .018 * (1 - (r / .058) ** 2) + rnd.uniform(0, .004), rnd.choice(cols))
    for i in range(40):
        sprinkle(rnd.uniform(-.44, -.3), rnd.uniform(.16, .3), 0, rnd.choice(cols))
    for h, b in sp.items():
        mesh_object("IB_Spr_" + h, b, simple_material("M_spr_" + h, h, .35, coat=.5), c, subsurf=0).location = o
    # wafer rolls, top-right
    wm = simple_material("M_wafer", "E7B26A", .55, var="D49A50", bump_scale=400)
    for k, (x, y, r) in enumerate(((.47, .28, 15), (.5, .31, 25), (.55, .25, 8))):
        t = tube_bm([(-.07, 0, .007), (.07, 0, .007)], .0072, 24)
        ob = mesh_object("IB_Wafer%d" % k, t, wm, c, subsurf=1)
        ob.location = o + Vector((x, y, 0))
        ob.rotation_euler.z = math.radians(r)
    # cherries, bottom-left
    chm = simple_material("M_cherry", "B3102A", .15, coat=1.0, var="D4203A", sss=.2)
    for k, (x, y) in enumerate(((-.5, -.28), (-.46, -.31), (-.55, -.33))):
        b = ellipsoid(.014, .014, .013, 4, seed=k, lump=.02)
        for v in b.verts:
            v.co.z += .013
            if v.co.z > .024:
                v.co.z -= .003 * (1 - min(1, math.hypot(v.co.x, v.co.y) / .006))
        ob = mesh_object("IB_Cherry%d" % k, b, chm, c, subsurf=1)
        ob.location = o + Vector((x, y, 0))
        st = tube_bm(spline([(0, 0, .025), (.008, .015, .03), (.02, .035, .022), (.03, .05, .008)], 4), .0011, 6)
        so = mesh_object("IB_CherryStem%d" % k, st, stem_material(), c, subsurf=1)
        so.location = ob.location
        so.rotation_euler.z = math.radians(-40 + 50 * k)
    # scoop tool, bottom-right
    sm = metal_material("M_scoop_tool", "B8C1C8", .2)
    bowl2 = lathe_bm([(0, 0), (.022, .002), (.03, .012), (.031, .016), (.028, .016), (.02, .008), (0, .006)], 48)
    so = mesh_object("IB_ToolBowl", bowl2, sm, c, subsurf=1)
    so.location = o + Vector((.42, -.26, 0))
    hp = round_outline([(0, -.008), (.17, -.011), (.17, .011), (0, .008)], .008, 6)
    hb = outline_slab(hp, .014, bevel=.005, segs=4)
    xform(hb, loc=(.032, 0, 0))
    ho = mesh_object("IB_ToolHandle", hb, simple_material("M_tool_handle", "F49AB5", .3, coat=.4, var="F7A9C0"), c, subsurf=1)
    ho.location = so.location
    ho.rotation_euler.z = math.radians(-15)


def mockup_sorvetes():
    bench = load("pz_bench_sorvetes.png")
    bench[..., 3] = 1
    scoop = 104
    cone_x, cone_y = 800 - 1600 * .14, 450 - (-450 + scoop * .75 + 12)
    # order slip on the right (plain paper, no text)
    slip = np.ones((860, 520, 4), np.float32)
    slip[..., :3] = srgb_f("FFFDF6")
    slip[..., 3] = rounded_mask(520, 860, 20)
    soft_shadow(bench, slip[..., 3], 1600 - 20 - 520, 20, r=10, dx=6, dy=10, strength=.35)
    over(bench, slip, 1600 - 20 - 520, 20)
    cone = load("pz_cone.png")
    place(bench, cone, cone_x, cone_y, int(scoop * .95 * 1.25), int(scoop * 1.3 * 1.25))
    stack = ["chocolate", "menta", "morango"]
    for i, f in enumerate(stack):
        y = cone_y - (scoop * .7 + i * scoop * .82)
        place(bench, load("pz_scoop_%s.png" % f), cone_x, y, int(scoop * 1.2), int(scoop * 1.2))
    left = ["baunilha", "flocos", "limao", "morango", "chocolate"]
    for k, f in enumerate(left):
        y = 450 - (450 - scoop * .62 - k * (900 - 40) / 5) + 30
        place(bench, load("pz_scoop_%s.png" % f), 90, y, int(scoop * 1.15), int(scoop * 1.15))
    bench[..., 3] = 1
    return save_png(bench, "mockup_sorvetes.png")


def build_sorvetes():
    build_sorvetes_pieces()
    build_bench_sorvetes()


def run_sorvetes():
    out = [render_piece_sorvetes(f) for f in FLAVORS] + [render_piece_sorvetes("cone"), render_bench("sorvetes"), mockup_sorvetes()]
    return out


# ============================================================================================ ADEGA
VESSELS = {   # name: (sprite px, outer profile builder)
    "big": (360, 560), "mid": (280, 440), "small": (220, 320)}


def vessel_outer(kind):
    """Outer profile [(r, z)] bottom->top (metres) and (inner radius, straight part top z) for the liquid rect."""
    if kind == "big":        # 5 L garrafao: cylinder, round shoulders, short neck with lip
        R, Hb = .078, .15
        pts = [(R - .01, 0), (R - .003, .002), (R, .01)]
        pts += [(R + .002 * math.sin(math.pi * k / 6), .01 + (Hb - .01) * k / 6) for k in range(1, 7)]
        for k in range(1, 11):
            a = math.pi / 2 * k / 10
            pts.append((.016 + (R - .016) * math.cos(a) ** 1.3, Hb + .075 * math.sin(a) ** .9))
        pts += [(.016, .24), (.0175, .25), (.0185, .256)]
        return pts, (R - .003, .012, Hb)
    if kind == "mid":        # carafe: straight body, sloping shoulder, neck flaring to a lip
        R, Hb = .052, .115
        pts = [(R - .008, 0), (R - .002, .002), (R, .009)]
        pts += [(R - .002 * k / 6, .009 + (Hb - .009) * k / 6) for k in range(1, 7)]
        for k in range(1, 9):
            t = k / 8
            pts.append((R - .002 - (R - .002 - .019) * smooth(0, 1, t), Hb + .05 * t))
        pts += [(.018, .18), (.02, .192), (.026, .2)]
        return pts, (R - .0045, .011, Hb)
    R, Hb = .041, .1         # small jug: slightly bellied, with a pouring lip and a handle
    pts = [(R - .006, 0), (R - .0015, .0015), (R, .008)]
    pts += [(R + .003 * math.sin(math.pi * k / 8 * .8), .008 + (Hb - .008) * k / 8) for k in range(1, 9)]
    pts += [(R - .001, .11), (R + .001, .118), (R + .003, .124)]
    return pts, (R - .003, .011, .1)


def rope_material():
    mat = mat_get("M_rope")
    nb = NB(mat)
    uv = nb.node("ShaderNodeTexCoord").outputs["UV"]
    u, v, _ = nb.sep(uv)
    tw = nb.math("FRACT", nb.add(nb.mul(u, 1 / .007), nb.mul(v, 3.0)))
    ply = nb.mapr(nb.math("ABSOLUTE", nb.math("SUBTRACT", tw, .5)), .5, .08)
    n = nb.noise(nb.node("ShaderNodeTexCoord").outputs["Object"], 300, 4)
    base = nb.ramp(nb.add(nb.mul(ply, .6), nb.mul(n, .4)), [(0, srgb("7A5530")), (.5, srgb("B48650")), (1, srgb("D9B07A"))])
    nb.bsdf(**{"Base Color": base, "Roughness": .85, "Sheen Weight": .4,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(ply, nb.mul(n, .3)), Strength=.8, Distance=.0012).outputs[0]})
    return mat


def build_vessel(c, kind, at):
    outer, (r_in, z_bot, z_top) = vessel_outer(kind)
    bm = lathe_bm(shell_profile(outer, wall=.003, base=z_bot), 96)
    ob = mesh_object("VS_%s" % kind, bm, glass_material("M_glass_green"), c, subsurf=1)
    ob.location = at
    zt = outer[-1][1]
    set_dense(ob, lambda co: max(min(1.0, max(0.0, (z_bot + .003 - co.z) / .008)) * .75,
                                 min(1.0, max(0.0, (co.z - (zt - .006)) / .006)) * .6))
    glass = [ob.name]
    opaque = []
    if kind == "big":       # rope collar: three turns around the neck + a short tied loop
        pts = []
        for i in range(3 * 40 + 1):
            a = 2 * math.pi * i / 40
            zz = .222 + .0062 * a / (2 * math.pi)
            rr = .0195 + .0004 * math.sin(a * 3)
            pts.append((rr * math.cos(a), rr * math.sin(a), zz))
        rb = tube_bm(pts, .0034, 12)
        for k in range(14):
            t = k / 13
            pass
        loop = []
        for i in range(25):
            t = i / 24
            a = math.pi * t
            loop.append((.021 + .028 * math.sin(a) * .6, -.004 - .0 * t, .23 - .045 * math.sin(a * .5) - .02 * t))
        bm_join(rb, tube_bm(spline(loop, 2), .0028, 10))
        ro = mesh_object("VS_big_rope", rb, rope_material(), c, subsurf=1)
        ro.location = at
        opaque.append(ro.name)
        # cork stopper
        ck = lathe_bm([(0, .248), (.0145, .248), (.016, .27), (.0158, .274), (0, .275)], 32)
        co = mesh_object("VS_big_cork", ck, cork_material(), c, subsurf=1)
        co.location = at
        opaque.append(co.name)
    if kind == "small":     # handle
        R = .041
        pts = []
        for i in range(25):
            t = i / 24
            a = math.radians(-75 + 150 * t)
            pts.append((R + .002 + .022 * math.cos(a), 0, .062 + .043 * math.sin(a)))
        hb = tube_bm(spline(pts, 2), lambda t: .0055 * (1 - .2 * math.sin(math.pi * t)), 14)
        hd = mesh_object("VS_small_handle", hb, glass_material("M_glass_green"), c, subsurf=1)
        hd.location = at
        set_dense(hd, lambda co: .5)
        glass.append(hd.name)
    return glass, opaque, (r_in, z_bot, z_top)


def cork_material():
    mat = mat_get("M_cork")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 300, 5, .7)
    pits = nb.mapr(nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=500, _feature="F1").outputs["Distance"], .12, .02)
    base = nb.ramp(nb.add(nb.mul(n, .7), nb.mul(pits, .4)), [(0, srgb("D9AC72")), (.6, srgb("BC8A50")), (1, srgb("7E5530"))])
    nb.bsdf(**{"Base Color": base, "Roughness": .8,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(n, nb.mul(pits, -1.0)), Strength=.6, Distance=.001).outputs[0]})
    return mat


VESSEL_X = {"big": 0.0, "mid": .35, "small": .65}


def build_adega_pieces():
    o = O("adega")
    c = col("Adega pieces")
    wipe_collection(c.name)
    for k in VESSELS:
        build_vessel(c, k, o + Vector((VESSEL_X[k], 0, 0)))
        softboxes(c, "VS_%s" % k, o + Vector((VESSEL_X[k], 0, 0)), dist=.7, height=.6)
    catcher("adega", o + Vector((.35, .1, 0)), (2.0, 1.2))


def render_piece_adega(kind):
    o = O("adega")
    at = o + Vector((VESSEL_X[kind], 0, 0))
    res = VESSELS[kind]
    pxm = {"big": 1720, "mid": 1950, "small": 1620}[kind]
    size = (res[0] / pxm, res[1] / pxm)
    outer, (r_in, z_bot, z_top) = vessel_outer(kind)
    ztop = max(z for r, z in outer) + (.03 if kind == "big" else .002)
    center = at + Vector((.013 if kind == "small" else 0, 0, ztop * .5 + (.008 if kind == "big" else .006)))
    glass = ["VS_%s" % kind] + (["VS_small_handle"] if kind == "small" else [])
    opaque = ["VS_big_rope", "VS_big_cork"] if kind == "big" else []
    soft = ["VS_%s_Soft%d" % (kind, i) for i in range(3)]
    name = "pz_vessel_%s" % kind
    path, _ = render_glass(name, glass, opaque, soft, center, size, res, tint="BFE3CC", catcher_name="Catcher_adega", edge_col="4E8064")
    rect = inner_rect(center, size, res, r_in, z_bot + .004, z_top, axis=at)
    manifest_update(name, {"inner": rect, "size": list(res), "check": glass_stats(name, rect)})
    return path


def barrel_top_material(R):
    mat = mat_get("M_barrel_top")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    r = nb.math("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    plank = .045
    idx = nb.math("FLOOR", nb.math("DIVIDE", x, plank))
    rnd = nb.node("ShaderNodeTexWhiteNoise", W=idx, _noise_dimensions="1D").outputs[0]
    fx = nb.math("FRACT", nb.math("DIVIDE", x, plank))
    seam = nb.mapr(nb.math("MINIMUM", fx, nb.math("SUBTRACT", 1.0, fx)), .03, .0)
    g = nb.noise(nb.node("ShaderNodeMapping", Vector=tc, Scale=(30, 2, 1)).outputs[0], 8, 4, .6)
    wood = nb.ramp(nb.add(nb.mul(rnd, .6), nb.mul(g, .5), -.1), [(0, srgb("9A6236")), (.5, srgb("7C4A26")), (1, srgb("5A3418"))])
    wood = nb.mix(nb.mul(seam, .9), wood, srgb("2E1A0C"))
    hoop = nb.mul(nb.mapr(r, R * .86, R * .88), nb.mapr(r, R * .99, R * .97))
    chime = nb.mul(nb.mapr(r, R * .8, R * .84), nb.mapr(r, R * .86, R * .84))
    iron = nb.ramp(nb.noise(tc, 80, 4), [(0, srgb("2B2A2A")), (1, srgb("4A4644"))])
    base = nb.mix(nb.mul(chime, .5), wood, srgb("3A2412"))
    base = nb.mix(hoop, base, iron)
    stain = nb.mapr(nb.noise(tc, 12, 4, .6), .6, .7)
    base = nb.mix(nb.mul(stain, .35), base, srgb("5A1A2A"))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.6, nb.mul(hoop, -.3)), "Metallic": nb.mul(hoop, .6),
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(nb.mul(seam, -1.0), nb.mul(g, .3), nb.mul(hoop, .5)), Strength=.4, Distance=.0015).outputs[0]})
    return mat


def bottle_material():
    mat = mat_get("M_bottle")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    lab = nb.mul(nb.mapr(x, -.07, -.065), nb.mapr(x, .02, .015))
    n = nb.noise(tc, 60, 3)
    glass = nb.ramp(n, [(0, srgb("1C3A28")), (1, srgb("244A33"))])
    label = nb.ramp(n, [(0, srgb("F3E6CC")), (1, srgb("E9D8B8"))])
    band = nb.mul(nb.mapr(nb.math("ABSOLUTE", nb.add(x, .0225)), .006, .004), lab)
    label = nb.mix(band, label, srgb("8E1B3A"))
    base = nb.mix(lab, glass, label)
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.08, nb.mul(lab, .6)), "Coat Weight": nb.math("SUBTRACT", 1.0, lab),
               "Coat Roughness": .03, "Specular IOR Level": .7})
    return mat


def build_bench_adega():
    o = O("adega") + Vector((0, -2.0, 0))
    c = col("Adega bench")
    wipe_collection(c.name)
    W, H = BENCH_SIZE
    top = mesh_object("WB_Top", quad_bm(W * 1.04, H * 1.04), wood_material("M_dark_table", light="6E4326", dark="3E2414", plank=.13, seam=True, scale=1.2), c, subsurf=0)
    top.location = o
    # barrel head, top-left corner (mostly outside the frame)
    R = .26
    prof = [(0, 0), (R, 0), (R + .004, .03), (R, .06), (R - .01, .062), (R - .012, .055), (0, .055)]
    bo = mesh_object("WB_Barrel", lathe_bm(prof, 128), barrel_top_material(R), c, subsurf=1)
    bo.location = o + Vector((-.68, .4, 0))
    # bottle lying down, top-right, neck pointing into the frame
    bp = [(0, 0), (.036, 0), (.038, .004), (.038, .2), (.034, .225), (.018, .26), (.014, .29), (.0145, .31), (.016, .312), (.016, .32), (0, .32)]
    bb = lathe_bm(spline(bp, 3), 64)
    xform(bb, rot=(0, -90, 0), loc=(0, 0, .038))
    bto = mesh_object("WB_Bottle", bb, bottle_material(), c, subsurf=1)
    bto.location = o + Vector((.75, .25, 0))
    bto.rotation_euler.z = math.radians(-15)
    # grapes on a vine leaf, bottom-left
    grape_bunch(c, "WB_Grapes", o + Vector((-.5, -.25, 0)), grape_material("M_grape_red", "4A1630", "8A2E4E"), n=34, seed=11, rot=-30,
                spread=(.06, .1), stem_mat=stem_material())
    # corks + corkscrew, bottom-right
    cm = cork_material()
    rnd = random.Random(2)
    for k, (x, y, r) in enumerate(((.42, -.3, 20), (.47, -.24, 75), (.36, -.25, -30), (.52, -.33, 130))):
        cb = lathe_bm([(0, 0), (.011, 0), (.012, .002), (.012, .042), (.011, .044), (0, .044)], 32)
        xform(cb, rot=(0, 90, 0), loc=(-.022, 0, .012))
        ob = mesh_object("WB_Cork%d" % k, cb, cm, c, subsurf=1)
        ob.location = o + Vector((x, y, 0))
        ob.rotation_euler.z = math.radians(r)
    st = metal_material("M_corkscrew", "B9C2C8", .2, False)
    pts = [(.0 + .0045 * math.cos(t * 2 * math.pi * 5), .07 * t, .006 + .0045 * math.sin(t * 2 * math.pi * 5)) for t in [i / 160 for i in range(161)]]
    sp = tube_bm(pts, .0013, 8)
    bm_join(sp, tube_bm([(-.045, -.006, .009), (.045, -.006, .009)], .0075, 16))
    so = mesh_object("WB_Corkscrew", sp, st, c, subsurf=1)
    so.location = o + Vector((.56, -.18, 0))
    so.rotation_euler.z = math.radians(-60)


def mockup_adega():
    bench = load("pz_bench_adega.png")
    bench[..., 3] = 1
    with open(os.path.join(OUT, "manifest.json")) as f:
        man = json.load(f)
    W, H = 1600, 900
    count = 3
    colW = min(170, (W - 120) / count - 30)
    fullH = H - 150
    caps = {"big": 8, "mid": 5, "small": 3}
    amount = {"big": 6, "mid": 2, "small": 3}
    for v, k in enumerate(("big", "mid", "small")):
        sw, sh = VESSELS[k]
        h = max(70, fullH * caps[k] / 8)
        w = h * sw / sh
        cx = 800 + (v - (count - 1) / 2) * (colW + 30) * 1.75 - W * .04
        cy = 450 - (-H / 2 + 50 + h / 2)
        sc = h / sh
        x0, y0 = cx - w / 2, cy - h / 2
        l, b, r, t = man["pz_vessel_%s" % k]["inner"]
        il, ir = x0 + l * sc, x0 + r * sc
        ib, it = y0 + h - b * sc, y0 + h - t * sc
        lvl = ib - (ib - it) * amount[k] / caps[k]
        wine = blank(int(ir - il), int(ib - lvl), srgb_f("8E1B3A"), .95)
        wine[:4, :, :3] = srgb_f("B8385A")
        over(bench, wine, int(il), int(lvl))
        place(bench, load("pz_vessel_%s.png" % k), cx, cy, int(w), int(h))
    bench[..., 3] = 1
    return save_png(bench, "mockup_adega.png")


def build_adega():
    build_adega_pieces()
    build_bench_adega()


def run_adega():
    out = [render_piece_adega(k) for k in VESSELS] + [render_bench("adega"), mockup_adega()]
    return out



# ============================================================================================ masks (inside of a glass) + SUCOS v2
def mask_material():
    mat = mat_get("M_inside_mask")
    nb = NB(mat)
    em = nb.node("ShaderNodeEmission", Color=(1, 1, 1, 1), Strength=1.0)
    o = nb.node("ShaderNodeOutputMaterial")
    nb.nt.links.new(em.outputs[0], o.inputs["Surface"])
    return mat


def inside_bm(outer, wall, base, seg=96, top_drop=0.0, round_floor=0.0):
    """Solid of the cavity of a lathe vessel: inner wall from the inner floor up to the rim."""
    prof = [(0.0, base)]
    if round_floor:
        rin = max(.0005, [r for r, z in outer if z >= base + round_floor][0] - wall)
        for k in range(6, 0, -1):
            a = math.pi / 2 * k / 6
            prof.append(((rin - round_floor) + round_floor * math.cos(a), base + round_floor - round_floor * math.sin(a)))
    for r, z in outer:
        if z < base + round_floor:
            continue
        prof.append((max(.0005, r - wall), z))
    zt = outer[-1][1] - top_drop
    prof = [p for p in prof if p[1] <= zt] + [(max(.0005, outer[-1][0] - wall), zt), (0.0, zt)]
    return lathe_bm(prof, seg)


def render_mask(name, mask_obj, center, size_m, res, tilt=GLASS_TILT):
    sc = bpy.context.scene
    vt, lk = sc.view_settings.view_transform, sc.view_settings.look
    try:
        sc.view_settings.view_transform, sc.view_settings.look = "Standard", "None"
        set_world("warm", 0.0)
        p = shoot(center, size_m, res, os.path.join(OUT, name + "_mask.png"), True, [mask_obj], "front", tilt, sun="")
    finally:
        sc.view_settings.view_transform, sc.view_settings.look = vt, lk
        set_world("warm")
    a = img_load(p)
    a[..., :3] = 1.0
    img_save(a, p)
    return p


JUICE = dict(R0=.034, R1=.041, H=.205, wall=.0042, base=.02, res=(240, 560), pxm=1850.0, cx=-.014)


def juice_outer():
    R0, R1, H = JUICE["R0"], JUICE["R1"], JUICE["H"]
    pts = [(R0 - .012, 0), (R0 - .006, .0008), (R0 - .0022, .003), (R0 - .0004, .0075), (R0, .012)]
    for k in range(1, 13):
        t = k / 12
        pts.append((R0 + (R1 - R0) * t ** 1.15, .012 + (H - .012) * t))
    return pts


def citrus_slice_material(name, pulp0, pulp1, pith, peel, R, segs=10):
    mat = mat_get(name)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    r = nb.math("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    ang = nb.math("ARCTAN2", y, x)
    n = nb.noise(tc, 150, 4)
    seg = nb.math("ABSOLUTE", nb.math("SUBTRACT", nb.math("FRACT", nb.mul(ang, segs / (2 * math.pi))), .5))
    memb = nb.mul(nb.mapr(seg, .44, .5), nb.mapr(r, R * .12, R * .2))
    cells = nb.mapr(nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=450, _feature="DISTANCE_TO_EDGE").outputs["Distance"], .0, .12)
    pulp = nb.ramp(nb.add(nb.mul(n, .5), nb.mul(cells, .4)), [(0, srgb(pulp0)), (1, srgb(pulp1))])
    face = nb.mix(memb, pulp, srgb(pith))
    face = nb.mix(nb.mapr(r, R * .82, R * .87), face, srgb(pith))
    face = nb.mix(nb.mapr(r, R * .92, R * .95), face, srgb(peel))
    face = nb.mix(nb.mapr(r, R * .12, R * .06), face, srgb(pith))
    nb.bsdf(**{"Base Color": face, "Roughness": .3, "Coat Weight": .6, "Coat Roughness": .1, "Subsurface Weight": .45,
               "Subsurface Radius": (1, .7, .3), "Subsurface Scale": .004,
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(nb.mul(memb, .6), nb.mul(cells, .3)), Strength=.3, Distance=.0008).outputs[0]})
    return mat


def straw_material():
    mat = mat_get("M_straw")
    nb = NB(mat)
    uv = nb.node("ShaderNodeTexCoord").outputs["UV"]
    u, v, _ = nb.sep(uv)
    st = nb.mapr(nb.math("SINE", nb.mul(nb.add(nb.mul(u, 1 / .012), nb.mul(v, 1.0)), 2 * math.pi)), -.1, .1)
    base = nb.mix(st, srgb("FFF7EA"), srgb("1F8F85"))
    nb.bsdf(**{"Base Color": base, "Roughness": .3, "Coat Weight": .5, "Coat Roughness": .1})
    return mat


def build_juice_glass(c, at):
    outer = juice_outer()
    H = JUICE["H"]
    bm = lathe_bm(shell_profile(outer, wall=JUICE["wall"], base=JUICE["base"], rim=.0022, round_floor=.009), 96)
    g = mesh_object("JG_Glass", bm, glass_material(), c, subsurf=1)
    g.location = at
    set_dense(g, lambda co: max(min(1.0, max(0.0, (JUICE["base"] + .004 - co.z) / .012)) * .85,
                                min(1.0, max(0.0, (co.z - (H - .005)) / .005)) * .6))
    # striped straw leaning out over the back-left of the rim
    a, b = Vector((-.016, .014, H - .022)), Vector((-.036, .006, H + .05))
    st = tube_bm([a[:], ((a + b) / 2)[:], b[:]], .0034, 16)
    so = mesh_object("JG_Straw", st, straw_material(), c, subsurf=1)
    so.location = at
    # orange wheel clipped on the right of the rim (outside the glass)
    R = .019
    sl = lathe_bm([(0, -.003), (R * .98, -.003), (R, -.0018), (R, .0018), (R * .98, .003), (0, .003)], 64)
    so2 = mesh_object("JG_Slice", sl, citrus_slice_material("M_juice_slice", "FFA531", "FFC566", "FFEBC8", "F28A1A", R, 10), c, subsurf=1)
    so2.location = at + Vector((JUICE["R1"] + .014, -.006, H + .006))
    so2.rotation_euler = (math.radians(90), math.radians(-8), 0)
    m = mesh_object("JG_Inside", inside_bm(outer, JUICE["wall"], JUICE["base"], round_floor=.009), mask_material(), c, subsurf=1)
    m.location = at
    return [g.name], [so.name, so2.name], m.name


def build_sucos_pieces2():
    o = O("sucos")
    c = col("Sucos pieces")
    wipe_collection(c.name)
    build_juice_glass(c, o)
    softboxes(c, "JG", o)
    catcher("sucos", o + Vector((0, .1, 0)), (1.2, 1.2))


def juice_frame():
    o = O("sucos")
    res = JUICE["res"]
    size = (res[0] / JUICE["pxm"], res[1] / JUICE["pxm"])
    center = o + Vector((-JUICE["cx"] + .002, 0, JUICE["H"] * .5 + .022))
    return o, res, size, center


def render_piece_sucos2(kind="glass"):
    o, res, size, center = juice_frame()
    if kind == "mask":
        p = render_mask("pz_jug_glass", "JG_Inside", center, size, res)
        return p
    path, _ = render_glass("pz_jug_glass", ["JG_Glass"], ["JG_Straw", "JG_Slice"], ["JG_Soft0", "JG_Soft1", "JG_Soft2"],
                           center, size, res, catcher_name="Catcher_sucos")
    rect = inner_rect(center, size, res, JUICE["R0"] + .002 - JUICE["wall"], JUICE["base"] + .004, JUICE["H"] - .012, axis=o)
    manifest_update("pz_jug_glass", {"inner": rect, "size": list(res), "mask": "pz_jug_glass_mask.png",
                                     "check": glass_stats("pz_jug_glass", rect)})
    return path


def build_bench_sucos2():
    o = O("sucos") + Vector((0, -2.0, 0))
    c = col("Sucos bench")
    wipe_collection(c.name)
    W, H = BENCH_SIZE
    top = mesh_object("SB_Top", quad_bm(W * 1.04, H * 1.04),
                      wood_material("M_juicebar", light="F0C98E", dark="C99055", plank=.1, seam=True, scale=1.2), c, subsurf=0)
    top.location = o
    linen(c, "SB_Napkin", o + Vector((-.5, .27, 0)), (.36, .26), rot=-10, seed=3)
    om = fruit_skin_material("M_orange", "F7931E", "E5770F", pore=700, rough=.35)
    for k, (x, y) in enumerate(((-.58, .3), (-.47, .34), (-.62, .17))):
        ob = mesh_object("SB_Orange%d" % k, orange_bm(seed=k), om, c, subsurf=1)
        ob.location = o + Vector((x, y, .044))
    hcm = citrus_cut_material("M_orange_cut", "FFA531", "FFC566", "FFE9C2", "F28A1A", .044, 11)
    for k, (x, y) in enumerate(((-.42, .24), (-.52, .16))):
        oh = mesh_object("SB_OrangeHalf%d" % k, lemon_half_bm(.044, .036), hcm, c, subsurf=1)
        oh.location = o + Vector((x, y, .004))
    lm = fruit_skin_material("M_lime", "5DAA2E", "3E8A1F", pore=800, rough=.3)
    for k, (x, y) in enumerate(((.57, .31), (.49, .35))):
        b = ellipsoid(.032, .037, .03, 4, seed=k + 5, lump=.02)
        ob = mesh_object("SB_Lime%d" % k, b, lm, c, subsurf=1)
        ob.location = o + Vector((x, y, .03))
        ob.rotation_euler.z = math.radians(30 * k + 20)
    lcm = citrus_cut_material("M_lime_cut", "A6D65A", "C8EA8A", "EEF7D8", "4F9A28", .033, 9)
    lh = mesh_object("SB_LimeHalf", lemon_half_bm(.033, .027), lcm, c, subsurf=1)
    lh.location = o + Vector((.45, .26, 0))
    mm = leaf_material("M_mint", "3E9A4A", "79C267")
    for k, (px, py, pr) in enumerate(((.6, .18, 200), (.4, .33, 150))):
        po = mesh_object("SB_Mint%d" % k, parsley_bm(k + 7, .1, 6), mm, c, subsurf=1)
        po.location = o + Vector((px, py, 0))
        po.rotation_euler.z = math.radians(pr)
    sm = strawberry_material()
    cm = leaf_material("M_calyx", "3E7A2E", "5E9A3A")
    for k, (x, y, r) in enumerate(((-.55, -.27, 20), (-.47, -.31, -40), (-.6, -.33, 80), (-.42, -.25, 150), (-.52, -.2, 110))):
        sc_ = 1.45 - .06 * k
        ob = mesh_object("SB_Straw%d" % k, strawberry_bm(k, sc_), sm, c, subsurf=1)
        ob.location = o + Vector((x, y, 0))
        ob.rotation_euler.z = math.radians(r)
        ca = mesh_object("SB_Calyx%d" % k, calyx_bm(k), cm, c, subsurf=1)
        a = math.radians(r)
        ca.location = o + Vector((x + math.sin(a) * .021 * sc_, y + math.cos(a) * .021 * sc_, .013 * sc_))
        ca.rotation_euler = (math.radians(90), 0, a)
    grape_bunch(c, "SB_Grapes", o + Vector((.36, -.3, 0)), grape_material("M_grape_green", "9CC24A", "C9DD74", bloom=.5), n=24, seed=6, rot=110, r=.013,
                stem_mat=stem_material())
    R = .06
    pr_ = [(0, 0), (R * .98, 0), (R, .002), (R, .012), (R * .98, .014), (0, .014)]
    pm = mesh_object("SB_Pineapple", lathe_bm(pr_, 64), pineapple_slice_material(R), c, subsurf=1)
    pm.location = o + Vector((.56, -.26, 0))
    lv = bmesh.new()
    for k in range(6):
        pts = [(0, -.004), (.05, -.003), (.08, 0), (.05, .003), (0, .004)]
        lf = outline_slab(pts, .0015, bevel=.0005, segs=1)
        xform(lf, rot=(0, -8, 130 + 12 * k), loc=(0, 0, .002 * k))
        bm_join(lv, lf)
    lo = mesh_object("SB_PineLeaf", lv, leaf_material("M_pine_leaf", "4C7F3A", "6C9E4C"), c, subsurf=1)
    lo.location = o + Vector((.64, -.15, .0))
    # a few clear ice cubes near the limes
    ib = bmesh.new()
    rnd = random.Random(4)
    for k in range(5):
        cb = bmesh.new()
        bmesh.ops.create_cube(cb, size=.022)
        bmesh.ops.bevel(cb, geom=cb.edges[:], offset=.003, segments=3, affect="EDGES")
        xform(cb, loc=(.3 + rnd.uniform(-.04, .04), .3 + rnd.uniform(-.04, .03), .011), rot=(0, 0, rnd.uniform(0, 90)))
        bm_join(ib, cb)
    mesh_object("SB_IceCubes", ib, ice_material2(), c, subsurf=0).location = o


def mockup_sucos2():
    bench = load("pz_bench_bebidas.png")
    bench[..., 3] = 1
    with open(os.path.join(OUT, "manifest.json")) as f:
        man = json.load(f)
    l, b, r, t = man["pz_jug_glass"]["inner"]
    jug = load("pz_jug_glass.png")
    mask = load("pz_jug_glass_mask.png")[..., 3]
    sw, sh = 240, 560
    sc = 150 / sw
    ow, oh = int(sw * sc), int(sh * sc)
    mask_s = img_resize(np.dstack([np.ones_like(mask)] * 3 + [mask]).astype(np.float32), ow, oh)[..., 3]
    cols = ["F59A23", "E5484D", "8CCB3C", "7E4AA8", "F6D44A", "F2667E"]
    stacks = [[0, 1, 2, 0], [1, 2, 1], [2, 0, 1, 2], [3, 4], [4, 3, 4, 3], []]
    ys_bottom = oh - b * sc
    ys_top = oh - t * sc
    unit = (ys_bottom - ys_top) / 4
    for j in range(6):
        cx = 800 + (j - 2.5) * 175
        cy = 430
        x0, y0 = int(cx - ow / 2), int(cy - oh / 2)
        layer = blank(ow, oh)
        for k, ci in enumerate(stacks[j]):
            y1 = ys_bottom - k * unit
            y2 = y1 - unit
            rgb = np.array(srgb_f(cols[ci]), np.float32)
            top = int(y2) if k < len(stacks[j]) - 1 else int(y2)
            layer[max(0, int(y2)):int(y1) if k else oh, :, :3] = rgb
            layer[max(0, int(y2)):int(y1) if k else oh, :, 3] = .93
            layer[max(0, int(y2)):max(0, int(y2)) + 3, :, :3] = np.minimum(1, rgb * 1.25)
        layer[..., 3] *= mask_s
        over(bench, layer, x0, y0)
        place(bench, jug, cx, cy, ow, oh)
    bench[..., 3] = 1
    return save_png(bench, "mockup_sucos.png")



# ============================================================================================ SORVETES v2: gelato tubs + display freezer
TUB = dict(W=.22, D=.17, H=.075, r=.018, res=(400, 320), pxm=1500.0, tilt=62.0)


def rrect_pts(w, d, r, n=10):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180), (w / 2 - r, -d / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def sweep_rrect(w, d, r, profile, n=10):
    """Rounded-rectangle 'lathe': each (offset, z) of `profile` becomes a ring offset outwards by `offset`.
    Closes the first and last ring with n-gons."""
    bm = bmesh.new()
    rings = []
    for off, z in profile:
        rings.append([bm.verts.new((x, y, z)) for x, y in rrect_pts(w + 2 * off, d + 2 * off, max(.002, r + off), n)])
    m = len(rings[0])
    for i in range(len(rings) - 1):
        for j in range(m):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % m], rings[i + 1][(j + 1) % m], rings[i + 1][j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def pan_material():
    mat = mat_get("M_gelato_pan")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    geo = nb.node("ShaderNodeNewGeometry")
    nz = nb.sep(geo.outputs["Normal"])[2]
    sv = nb.node("ShaderNodeMapping", Vector=tc, Scale=(4, 700, 1)).outputs[0]
    br = nb.noise(sv, 1.0, 3, .5)
    steel = nb.ramp(nb.add(nb.mul(br, .6), nb.mul(nb.noise(tc, 20, 3), .4)), [(0, srgb("7F8A92")), (1, srgb("B4BEC5"))])
    # frost: fine white crystals on the rim and the upper wall
    fr = nb.mul(nb.mapr(z, TUB["H"] - .002, TUB["H"] + .004), nb.mapr(nb.noise(tc, 60, 5, .6), .25, .45))
    sp = nb.mapr(nb.noise(tc, 1400, 2, .5), .6, .66)
    fr = nb.math("MAXIMUM", fr, nb.mul(sp, nb.mapr(z, TUB["H"] - .02, TUB["H"] - .004)))
    base = nb.mix(fr, steel, nb.ramp(nb.noise(tc, 500, 2), [(0, srgb("EAF4F9")), (1, srgb("FFFFFF"))]))
    nb.bsdf(**{"Base Color": base, "Metallic": nb.math("SUBTRACT", .95, nb.mul(fr, .95)), "Roughness": nb.add(.22, nb.mul(fr, .55), nb.mul(br, .1)),
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(br, nb.mul(fr, nb.noise(tc, 400, 3))), Strength=.25, Distance=.0005).outputs[0]})
    return mat


def gelato_surface_bm(seed, nx=90, ny=70):
    W, D, H, r = TUB["W"], TUB["D"], TUB["H"], TUB["r"]
    iw, idd = W - .012, D - .012
    rnd = random.Random(seed)
    off = Vector((seed * 5.1, seed * 1.7, .3))
    sc = (rnd.uniform(-.04, .04), rnd.uniform(-.03, .03), rnd.uniform(.035, .05), rnd.uniform(0, 6.28))   # scoop mark
    bm = bmesh.new()
    vs = {}
    rr = r - .006
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = (i / nx - .5) * iw
            y = (j / ny - .5) * idd
            # pull corner points onto the rounded inner outline
            qx, qy = abs(x) - (iw / 2 - rr), abs(y) - (idd / 2 - rr)
            if qx > 0 and qy > 0:
                k = rr / math.hypot(qx, qy)
                if k < 1:
                    x = math.copysign(iw / 2 - rr + qx * k, x)
                    y = math.copysign(idd / 2 - rr + qy * k, y)
            ex = min(iw / 2 - abs(x), idd / 2 - abs(y))
            edge = smooth(0, .02, ex)
            heap = math.cos(min(1.0, abs(x) / (iw / 2)) * math.pi / 2) ** .6 * math.cos(min(1.0, abs(y) / (idd / 2)) * math.pi / 2) ** .6
            p = Vector((x, y, 0))
            wave = .009 * math.sin(x * 60 + 3.0 * noise.noise(p * 16 + off)) * math.sin(y * 48 + 2.0 * noise.noise(p * 12 + off))
            swirl = .007 * noise.fractal(p * 22 + off, .6, 2.0, 3)
            ridge = .006 * (1 - abs(math.sin((x * .8 + y) * 90 + 4 * noise.noise(p * 10 + off)))) ** 3
            z = H * .92 + edge * (.038 * heap + wave + swirl + ridge) + (1 - edge) * .004
            # the scoop mark: a curled trough with a raised lip beside it
            dx, dy = x - sc[0], y - sc[1]
            d = abs(math.hypot(dx, dy) - sc[2] * .5)
            ang = math.atan2(dy, dx)
            arc = smooth(-.2, .6, math.cos(ang - sc[3]))
            z += arc * edge * (-.012 * math.exp(-(d / .009) ** 2) + .005 * math.exp(-((d - .013) / .005) ** 2))
            vs[i, j] = bm.verts.new((x, y, z))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    return bm


def build_tubs():
    o = O("sorvetes") + Vector((0, 1.0, 0))
    c = col("Sorvetes tubs")
    wipe_collection(c.name)
    W, D, H, r = TUB["W"], TUB["D"], TUB["H"], TUB["r"]
    prof = [(-.006, 0), (-.0035, .0012), (-.001, .006), (0, .02), (0, H), (.005, H + .001), (.0065, H + .0035), (.005, H + .0055),
            (.001, H + .0055), (-.0025, H + .004), (-.003, H - .002), (-.003, .008), (-.006, .004), (-.009, .004)]
    for i, f in enumerate(FLAVORS):
        at = o + Vector((i * .4, 0, .0005))
        pan = mesh_object("tub_pan_" + f, sweep_rrect(W, D, r, prof), pan_material(), c, subsurf=1)
        pan.location = at
        g = mesh_object("tub_gelato_" + f, gelato_surface_bm(i + 3), icecream_material(f), c, subsurf=1)
        g.location = at
    catcher("sorvetes", o + Vector((1.0, .05, 0)), (3.0, 1.0), "Catcher_tubs")


def render_tub(f):
    pan = bpy.data.objects["tub_pan_" + f]
    res = TUB["res"]
    size = (res[0] / TUB["pxm"], res[1] / TUB["pxm"])
    center = pan.location + Vector((0, 0, TUB["H"] * .55))
    return shoot(center, size, res, os.path.join(OUT, "pz_tub_%s.png" % f), True, [pan.name, "tub_gelato_" + f, "Catcher_tubs"], "front", TUB["tilt"])


FREEZER_PXM = 1600 / (BENCH_SIZE[0])
SLOT = dict(w=280, h=224, gap=26, x0=70, y0=196)         # pixels, top-left origin, 3 x 2


def slot_rects_px():
    out = []
    for row in range(2):
        for col_ in range(3):
            l = SLOT["x0"] + col_ * (SLOT["w"] + SLOT["gap"])
            t = SLOT["y0"] + row * (SLOT["h"] + SLOT["gap"])
            out.append((l, t, l + SLOT["w"], t + SLOT["h"]))
    return out


def px2m(x, y, o):
    """Bench pixel (top-left origin) -> world point on the bench plane."""
    W, H = BENCH_SIZE
    return o + Vector(((x / 1600 - .5) * W, (.5 - y / 900) * H, 0))


def freezer_well_material():
    mat = mat_get("M_freezer_well")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 30, 5, .6)
    fr = nb.mul(nb.mapr(nb.noise(tc, 220, 4, .6), .55, .7), nb.mapr(nb.noise(tc, 12, 3), .35, .65))
    base = nb.ramp(n, [(0, srgb("4A6073")), (1, srgb("647D90"))])
    base = nb.mix(nb.mul(fr, .55), base, srgb("DCEBF4"))
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.35, nb.mul(fr, .4)), "Metallic": nb.mul(nb.math("SUBTRACT", 1.0, fr), .5),
               "Normal": nb.node("ShaderNodeBump", Height=nb.add(n, fr), Strength=.2, Distance=.001).outputs[0]})
    return mat


def build_bench_sorvetes2():
    o = O("sorvetes") + Vector((0, -2.0, 0))
    c = col("Sorvetes bench")
    wipe_collection(c.name)
    W, H = BENCH_SIZE
    top = mesh_object("IB_Top", quad_bm(W * 1.04, H * 1.04), terrazzo_material(), c, subsurf=0)
    top.location = o
    s = 1 / FREEZER_PXM
    steel = metal_material("M_freezer_steel", "B3BDC4", .26)
    # freezer cabinet top: a steel deck around the well, dividers between the 6 slots
    fx0, fy0, fx1, fy1 = 28, 40, 990, 852
    cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    deck = rounded_slab((fx1 - fx0) * s, (fy1 - fy0) * s, .02, .02)
    d = mesh_object("IB_Deck", deck, steel, c, subsurf=0)
    d.location = px2m(cx, cy, o)
    # dark frosty well where the slots open
    rects = slot_rects_px()
    wl, wt = rects[0][0] - 14, rects[0][1] - 14
    wr, wb = rects[-1][2] + 14, rects[-1][3] + 14
    well = rounded_slab((wr - wl) * s, (wb - wt) * s, .0215, .012)
    w = mesh_object("IB_Well", well, freezer_well_material(), c, subsurf=0)
    w.location = px2m((wl + wr) / 2, (wt + wb) / 2, o)
    # slot frames: a raised steel lip around every opening (4 bars each), then the dividers between them
    bars = bmesh.new()
    lip = 10
    for (l, t, r_, b) in rects:
        for (bx, by, bw, bh) in ((l - lip, t - lip, r_ - l + 2 * lip, lip), (l - lip, b, r_ - l + 2 * lip, lip),
                                 (l - lip, t, lip, b - t), (r_, t, lip, b - t)):
            sl = rounded_slab(bw * s, bh * s, .006, .0025)
            xform(sl, loc=px2m(bx + bw / 2, by + bh / 2, Vector()) + Vector((0, 0, .0215)))
            bm_join(bars, sl)
    mesh_object("IB_SlotLips", bars, metal_material("M_freezer_lip", "C9D1D7", .2), c, subsurf=1).location = o
    # front: curved glass sneeze guard along the customer edge
    gl = rounded_slab((fx1 - fx0 - 30) * s, 46 * s, .03, .01)
    gm = mat_get("M_freezer_glass")
    nb = NB(gm)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    y_ = nb.sep(tc)[1]
    hl = nb.mapr(nb.math("ABSOLUTE", nb.add(y_, .004)), .006, .0)
    nb.bsdf(**{"Base Color": nb.mix(nb.mul(hl, .8), srgb("A9D8E6"), srgb("FFFFFF")), "Roughness": .03, "Transmission Weight": .5, "IOR": 1.45,
               "Coat Weight": 1.0, "Coat Roughness": .02, "Alpha": nb.add(.55, nb.mul(hl, .45))})
    g = mesh_object("IB_Glass", gl, gm, c, subsurf=0)
    g.location = px2m(cx, fy1 - 32, o) + Vector((0, 0, .02))
    # cone stand on the right: a round steel base with a ring holder (the game stands the cone in it)
    st = CONE_STAND
    base = lathe_bm([(0, 0), (.07, 0), (.075, .004), (.074, .012), (.068, .015), (0, .015)], 64)
    bo = mesh_object("IB_StandBase", base, steel, c, subsurf=1)
    bo.location = px2m(st[0], st[1], o)
    ring = lathe_bm([(.026, .015), (.034, .015), (.036, .03), (.034, .034), (.028, .034), (.026, .03)], 48)
    ro = mesh_object("IB_StandRing", ring, metal_material("M_stand_ring", "D7DEE3", .18, False), c, subsurf=1)
    ro.location = bo.location
    hole = lathe_bm([(0, .0151), (.0262, .0151), (.0262, .016), (0, .016)], 48)
    ho = mesh_object("IB_StandHole", hole, simple_material("M_stand_hole", "3A434B", .6), c, subsurf=0)
    ho.location = bo.location
    # props at the right corners: sprinkles bowl (top-right), cherries + wafers (bottom-right)
    prof = [(0, 0), (.04, 0), (.06, .01), (.07, .035), (.066, .037), (.056, .014), (.04, .008), (0, .008)]
    bowl = mesh_object("IB_Bowl", lathe_bm(spline(prof, 3), 64), simple_material("M_ibowl", "F49AB5", .25, coat=.7, var="F7A9C0"), c, subsurf=1)
    bowl.location = px2m(1500, 110, o)
    rnd = random.Random(9)
    cols = ["E5484D", "F6D44A", "54B6E8", "8CCB3C", "FFFFFF", "F28CA6", "9A6AD0"]
    sp = {h: bmesh.new() for h in cols}
    bc = bowl.location - o
    def sprinkle(x, y, z, h):
        t = tube_bm([(-.0035, 0, 0), (.0035, 0, 0)], .0011, 6)
        xform(t, loc=(x, y, z + .0011), rot=(rnd.uniform(-20, 20), rnd.uniform(-20, 20), rnd.uniform(0, 360)))
        bm_join(sp[h], t)
    for i in range(380):
        a, r = rnd.uniform(0, 6.28), .058 * math.sqrt(rnd.random())
        sprinkle(bc.x + r * math.cos(a), bc.y + r * math.sin(a), .012 + .018 * (1 - (r / .058) ** 2) + rnd.uniform(0, .004), rnd.choice(cols))
    for i in range(30):
        sprinkle(bc.x - rnd.uniform(.07, .16), bc.y - rnd.uniform(-.04, .08), 0, rnd.choice(cols))
    for h, b in sp.items():
        mesh_object("IB_Spr_" + h, b, simple_material("M_spr_" + h, h, .35, coat=.5), c, subsurf=0).location = o
    chm = simple_material("M_cherry", "B3102A", .15, coat=1.0, var="D4203A", sss=.2)
    for k, (x, y) in enumerate(((1480, 800), (1520, 770), (1445, 830))):
        b = ellipsoid(.014, .014, .013, 4, seed=k, lump=.02)
        for v in b.verts:
            v.co.z += .013
        ob = mesh_object("IB_Cherry%d" % k, b, chm, c, subsurf=1)
        ob.location = px2m(x, y, o)
        stm = tube_bm(spline([(0, 0, .025), (.008, .015, .03), (.02, .035, .022), (.03, .05, .008)], 4), .0011, 6)
        so = mesh_object("IB_CherryStem%d" % k, stm, stem_material(), c, subsurf=1)
        so.location = ob.location
        so.rotation_euler.z = math.radians(-40 + 50 * k)
    wm = simple_material("M_wafer", "E7B26A", .55, var="D49A50", bump_scale=400)
    for k, (x, y, rr_) in enumerate(((1180, 800, 15), (1200, 830, 25))):
        t = tube_bm([(-.07, 0, .007), (.07, 0, .007)], .0072, 24)
        ob = mesh_object("IB_Wafer%d" % k, t, wm, c, subsurf=1)
        ob.location = px2m(x, y, o)
        ob.rotation_euler.z = math.radians(rr_)
    rects_bl = [[l, 900 - b, r_, 900 - t] for (l, t, r_, b) in rects]
    manifest_update("pz_bench_sorvetes", {"slots": rects_bl, "slot_order": "row-major from the top-left, rects (left, bottom, right, top) px from bottom-left",
                                          "cone_stand": [CONE_STAND[0], 900 - CONE_STAND[1]], "size": [1600, 900]})


CONE_STAND = (1290, 560)


def mockup_sorvetes2():
    bench = load("pz_bench_sorvetes.png")
    bench[..., 3] = 1
    for (l, t, r_, b), f in zip(slot_rects_px(), FLAVORS):
        place(bench, load("pz_tub_%s.png" % f), (l + r_) / 2, (t + b) / 2 - 6, r_ - l + 30, None)
    scoop = 120
    cx, cy = CONE_STAND
    place(bench, load("pz_cone.png"), cx, cy - 60, int(scoop * 1.0), None)
    for i, f in enumerate(["chocolate", "menta", "morango"]):
        place(bench, load("pz_scoop_%s.png" % f), cx, cy - 150 - i * scoop * .72, int(scoop * 1.25), None)
    bench[..., 3] = 1
    return save_png(bench, "mockup_sorvetes.png")



# ============================================================================================ ADEGA masks + mockup v2
def adega_frame(kind):
    o = O("adega")
    at = o + Vector((VESSEL_X[kind], 0, 0))
    res = VESSELS[kind]
    pxm = {"big": 1720, "mid": 1950, "small": 1620}[kind]
    size = (res[0] / pxm, res[1] / pxm)
    outer, _ = vessel_outer(kind)
    ztop = max(z for r, z in outer) + (.03 if kind == "big" else .002)
    center = at + Vector((.013 if kind == "small" else 0, 0, ztop * .5 + (.008 if kind == "big" else .006)))
    return at, center, size, res


def build_adega_masks():
    c = col("Adega pieces")
    for k in VESSELS:
        at, center, size, res = adega_frame(k)
        outer, (r_in, z_bot, z_top) = vessel_outer(k)
        name = "VS_%s_Inside" % k
        ob = bpy.data.objects.get(name)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
        m = mesh_object(name, inside_bm(outer, .003, z_bot), mask_material(), c, subsurf=1)
        m.location = at


def render_adega_mask(kind):
    at, center, size, res = adega_frame(kind)
    p = render_mask("pz_vessel_%s" % kind, "VS_%s_Inside" % kind, center, size, res)
    m = {}
    pth = os.path.join(OUT, "manifest.json")
    with open(pth) as f:
        m = json.load(f)
    d = m.get("pz_vessel_%s" % kind, {})
    d["mask"] = "pz_vessel_%s_mask.png" % kind
    manifest_update("pz_vessel_%s" % kind, d)
    return p


def mockup_adega2():
    bench = load("pz_bench_adega.png")
    bench[..., 3] = 1
    with open(os.path.join(OUT, "manifest.json")) as f:
        man = json.load(f)
    W, H = 1600, 900
    colW = min(170, (W - 120) / 3 - 30)
    fullH = H - 150
    caps = {"big": 8, "mid": 5, "small": 3}
    amount = {"big": 6, "mid": 2, "small": 3}
    wine = np.array(srgb_f("5A0E1E"), np.float32)
    for v, k in enumerate(("big", "mid", "small")):
        sw, sh = VESSELS[k]
        h = max(70, fullH * caps[k] / 8)
        w = h * sw / sh
        cx = 800 + (v - 1) * (colW + 30) * 1.75 - W * .04
        cy = 450 - (-H / 2 + 50 + h / 2)
        sc = h / sh
        l, b, r, t = man["pz_vessel_%s" % k]["inner"]
        mk = load("pz_vessel_%s_mask.png" % k)
        mk = img_resize(mk, int(w), int(h))
        ib, it = h - b * sc, h - t * sc
        lvl = ib - (ib - it) * amount[k] / caps[k]
        layer = blank(int(w), int(h))
        layer[int(lvl):, :, :3] = wine
        layer[int(lvl):, :, 3] = .96
        layer[int(lvl):int(lvl) + 3, :, :3] = np.minimum(1, wine * 1.8)
        layer[..., 3] *= mk[..., 3]
        over(bench, layer, int(cx - w / 2), int(cy - h / 2))
        place(bench, load("pz_vessel_%s.png" % k), cx, cy, int(w), int(h))
    bench[..., 3] = 1
    return save_png(bench, "mockup_adega.png")


# ============================================================================================ registry / entry points
def build(sector):
    ensure_file()
    setup_scene()
    BUILD[sector]()


def render_piece(sector, kind):
    return RENDER_PIECE[sector](kind)


def render_bench(sector):
    vis = [ob.name for ob in bpy.data.collections["%s bench" % sector.capitalize()].objects]
    o = O(sector) + Vector((0, -2.0, 0))
    return shoot(o, BENCH_SIZE, (1600, 900), os.path.join(OUT, "pz_bench_%s.png" % BENCH_NAME.get(sector, sector)), False, vis)


BENCH_NAME = {"sucos": "bebidas"}


def build_queijaria():
    build_cheeses()
    build_bench_queijaria()
    build_rack_queijaria()


def run_queijaria():
    out = [render_piece_queijaria(k) for k in CHEESES]
    out.append(render_bench("queijaria"))
    out += render_parts_queijaria()
    out.append(mockup_queijaria())
    return out


BUILD = {"queijaria": build_queijaria, "acougue": build_acougue, "peixaria": build_peixaria, "sucos": build_sucos, "sorvetes": build_sorvetes, "adega": build_adega}
RENDER_PIECE = {"queijaria": render_piece_queijaria, "acougue": render_piece_acougue, "peixaria": render_piece_peixaria, "sucos": render_piece_sucos, "sorvetes": render_piece_sorvetes, "adega": render_piece_adega}
RUN = {"queijaria": run_queijaria, "acougue": run_acougue, "peixaria": run_peixaria, "sucos": run_sucos, "sorvetes": run_sorvetes, "adega": run_adega}


def run(sector):
    build(sector)
    out = RUN[sector]()
    save()
    return out


def run_all():
    out = []
    for s in SECTORS:
        if s in RUN:
            out += run(s)
    return out


# ============================================================================================ v2 registry (second pass)
def build_acougue_v2():
    build_meat_cuts()
    build_bench_acougue()


def build_peixaria_v2():
    build_fish_pieces()
    build_bench_peixaria2()
    build_icebed2()


def run_peixaria_v2():
    out = [render_piece_peixaria(k) for k in FISH]
    out += [render_bench("peixaria"), render_icebed2(), render_scale(), mockup_peixaria2()]
    return out


def build_sucos_v2():
    build_sucos_pieces2()
    build_bench_sucos2()


def run_sucos_v2():
    return [render_piece_sucos2("glass"), render_piece_sucos2("mask"), render_bench("sucos"), mockup_sucos2()]


def build_sorvetes_v2():
    build_sorvetes_pieces()
    build_tubs()
    build_bench_sorvetes2()


def run_sorvetes_v2():
    out = [render_piece_sorvetes(f) for f in FLAVORS + ["cone"]] + [render_tub(f) for f in FLAVORS]
    return out + [render_bench("sorvetes"), mockup_sorvetes2()]


def build_adega_v2():
    build_adega()
    build_adega_masks()


def run_adega_v2():
    out = [render_piece_adega(k) for k in VESSELS] + [render_adega_mask(k) for k in VESSELS]
    return out + [render_bench("adega"), mockup_adega2()]


BUILD.update({"acougue": build_acougue_v2, "peixaria": build_peixaria_v2, "sucos": build_sucos_v2,
              "sorvetes": build_sorvetes_v2, "adega": build_adega_v2})
RUN.update({"acougue": run_acougue2, "peixaria": run_peixaria_v2, "sucos": run_sucos_v2,
            "sorvetes": run_sorvetes_v2, "adega": run_adega_v2})
