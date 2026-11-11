"""Security guard (segurança), v2 (Lucas 08/11): the game's own Customer_09 (the bearded man) re-dressed as a guard.

v1 grew new shirt shells out of the body and they tore at the hems; v2 keeps the customer's own clean geometry and
repaints its texture instead (the open yellow shirt becomes a navy uniform shirt with a gold badge, a silver name
bar and shoulder patches, the white tee a black tee, the jeans black trousers, the loafers black shoes; the original
painting's folds and seams are kept as shading). On top: a navy cap with a stiff visor and a gold emblem, and a
black duty belt (radio, flashlight, buckle) that hugs the waist. No written words anywhere (pictograms only).

    exec(security_chars.py); exec(security_build.py); exec(guard_v2.py); rig = build_guard_v2()
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector as V
from mathutils.bvhtree import BVHTree

UNITY_ = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator"
GTEX = os.path.join(UNITY_, "Assets/Resources/CheckoutSecurity/Textures")
G = dict(navy=(0.11, 0.16, 0.34), navy_dark=(0.07, 0.10, 0.22), tee=(0.09, 0.09, 0.10), pants=(0.13, 0.13, 0.15),
         shoes=(0.07, 0.07, 0.075), gold=(0.92, 0.72, 0.28), gold_dark=(0.62, 0.44, 0.14), silver=(0.80, 0.82, 0.84),
         patch=(0.20, 0.38, 0.70))


def _srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def bake_positions(body, size=2048):
    """Object-space position of every texel (float image), so the repaint can use where a texel is on the body."""
    m = bpy.data.materials.new("Guard_PosBake"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord"); nt.links.new(tc.outputs["Object"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    img = bpy.data.images.new("Guard_Pos", size, size, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img; nt.nodes.active = tn
    keep = list(body.data.materials); body.data.materials.clear(); body.data.materials.append(m)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 1; sc.render.bake.margin = 4
    sc.render.bake.use_clear = True
    img.generated_color = (0, 0, 0, 0)
    for x in bpy.context.selected_objects:
        x.select_set(False)
    body.select_set(True); bpy.context.view_layer.objects.active = body
    bpy.ops.object.bake(type='EMIT')
    body.data.materials.clear()
    for mm in keep:
        body.data.materials.append(mm)
    a = np.empty(size * size * 4, np.float32); img.pixels.foreach_get(a)
    return a.reshape(size, size, 4)


def rgb_to_hsv(c):
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    mx = c.max(-1); mn = c.min(-1); d = mx - mn + 1e-6
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) / 6.0
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-6), 0)
    return h % 1.0, s, mx


def star_mask(dx, dz, r_out, r_in):
    a = np.arctan2(dz, dx) - math.pi / 2
    r = np.hypot(dx, dz)
    k = (a % (2 * math.pi / 5)) / (2 * math.pi / 5)
    edge = r_in + (r_out - r_in) * np.abs(1 - 2 * k)
    return r < edge


def repaint(body, size=2048):
    src = next(n.image for n in body.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE')
    if tuple(src.size) != (size, size):
        src = src.copy(); src.scale(size, size)
    o = np.empty(size * size * 4, np.float32); src.pixels.foreach_get(o); o = o.reshape(size, size, 4)
    rgb = o[..., :3].copy()                                     # image pixels are display (sRGB) values
    P = bake_positions(body, size)
    x, y, z, valid = P[..., 0], P[..., 1], P[..., 2], P[..., 3] > 0.5
    h, s, v = rgb_to_hsv(rgb)
    out = rgb.copy()

    def tint(mask, col, ref=None, gamma=0.85):
        if not mask.any():
            return
        vv = v[mask]; r_ = ref if ref is not None else float(np.median(vv))
        shade = np.clip((vv / max(r_, 1e-3)) ** gamma, 0.45, 1.35)[:, None]
        out[mask] = np.clip(np.asarray(col)[None, :] * shade, 0, 1)
    yellow = valid & (s > 0.26) & (v > 0.18) & (z > 0.95) & ((z < 1.90) | ((z < 2.0) & (y > 0.02)))
    shirt = yellow & (h > 0.088) & (h < 0.18)
    shirt |= valid & (z >= 1.88) & (z < 1.99) & (h > 0.100) & (h < 0.17) & (s > 0.42) & (np.abs(x) > 0.05)   # collar tips
    # the shirt's shadowed folds drift towards orange: accepted on the torso only (arms and neck: that hue is skin)
    shirt |= yellow & (h > 0.068) & (h <= 0.088) & (np.abs(x) < 0.34) & (z < 1.84)
    tee = valid & (s < 0.26) & (v > 0.42) & (z > 0.98) & (z < 1.88) & (np.abs(x) < 0.26) & ~shirt
    pants = valid & (h > 0.50) & (h < 0.72) & (s > 0.18) & (z < 1.25)
    shoes = valid & (z < 0.24) & ~pants
    tint(shirt, G["navy"]); tint(tee, G["tee"]); tint(pants, G["pants"]); tint(shoes, G["shoes"], gamma=1.0)
    # shoulder tops: a darker yoke
    yoke = shirt & (z > 1.80) & (np.abs(x) > 0.12)
    out[yoke] *= 0.78
    front = valid & (y < -0.04)
    # gold badge: a shield with a star on the left chest (the side of the pocket, +X)
    bx, bz = 0.165, 1.665
    dx, dz = x - bx, z - bz
    half = np.where(dz > 0, 0.036, 0.036 * np.clip(1 + dz / 0.050, 0, 1))
    shield = front & (np.abs(dx) < half) & (dz < 0.030) & (dz > -0.050)
    inner = front & (np.abs(dx) < half - 0.006) & (dz < 0.024) & (dz > -0.043)
    out[shield] = G["gold_dark"]; out[inner] = G["gold"]
    out[front & star_mask(dx, dz + 0.008, 0.019, 0.008) & inner] = G["gold_dark"]
    # silver name bar (blank) on the right chest
    nb = front & (np.abs(x + 0.165) < 0.040) & (np.abs(z - 1.655) < 0.011)
    out[nb] = G["silver"]; out[front & (np.abs(x + 0.165) < 0.040) & (np.abs(z - 1.655) < 0.011) & (np.abs(z - 1.655) > 0.008)] = (0.55, 0.56, 0.58)
    # shoulder patches on the outer upper arms: round, blue with a gold ring and star
    for sx in (-1, 1):
        side = valid & (sx * x > 0.36) & shirt
        dy_, dz_ = y - 0.0, z - 1.615
        rr = np.hypot(dy_, dz_)
        out[side & (rr < 0.048)] = G["gold"]
        out[side & (rr < 0.040)] = G["patch"]
        out[side & star_mask(-dy_ * sx, dz_, 0.024, 0.010) & (rr < 0.040)] = G["gold"]
    res = np.concatenate([out, np.ones_like(out[..., :1])], -1)
    img = bpy.data.images.get("Guard_Body") or bpy.data.images.new("Guard_Body", size, size, alpha=False)
    img.pixels.foreach_set(res.ravel().astype(np.float32))
    os.makedirs(GTEX, exist_ok=True)
    path = os.path.join(GTEX, "Guard_Body.png"); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    m = bpy.data.materials.get("Guard_Body_Mat") or bpy.data.materials.new("Guard_Body_Mat"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    ou = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True); t.image.reload()
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"]); nt.links.new(b.outputs["BSDF"], ou.inputs["Surface"])
    b.inputs["Roughness"].default_value = 0.72
    body.data.materials.clear(); body.data.materials.append(m)
    print("repaint: shirt", int(shirt.sum()), "tee", int(tee.sum()), "pants", int(pants.sum()), "shoes", int(shoes.sum()))
    return path


def inside_ring(body, z, lift, n=48, cx=0.0, cy=0.0, rmax=0.40):
    """Waist ring from the inside out (the first surface met going outwards: the hanging hands never count)."""
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    pts = []
    for k in range(n):
        a = math.tau * k / n
        d = V((math.cos(a), math.sin(a), 0))
        hit = bvh.ray_cast(V((cx, cy, z)), d, rmax)
        if hit[0] is not None:
            pts.append(hit[0] + d * lift)
    return pts


def cap_v2(info, body):
    lo, hi = info.head_box()
    c = (lo + hi) / 2; rx, ry, rz = (hi - lo) / 2
    nose_z, nose_y = eye_line(info)
    z_band = nose_z + 0.19
    centre = V((c[0], c[1] + 0.01, z_band))
    dome = fit_cap(info, "Guard_CapDome", centre, (rx * 0.98, ry * 1.0, (hi[2] - z_band) * 1.05),
                   lambda p: p.z < z_band - 0.005, offset=0.024, smooth=8)
    s = dome.modifiers.new("t", 'SOLIDIFY'); s.thickness = 0.012; s.offset = 1
    ctx_obj(dome); bpy.ops.object.modifier_apply(modifier="t")
    # visor: only in front, following the dome's lower edge, stiff, slightly curved down at the sides
    edge = [v.co.copy() for v in dome.data.vertices if v.co.z < z_band + 0.012]
    ccx, ccy = c[0], c[1] + 0.01
    bm = bmesh.new(); cols, rows = 28, 6; grid = []
    for i in range(cols + 1):
        a = math.radians(205 + 130 * i / cols)       # 205..335 deg: the front arc (-Y is 270)
        d = V((math.cos(a), math.sin(a), 0))
        # radius of the dome's edge in that direction
        best = max((p for p in edge if V((p.x - ccx, p.y - ccy, 0)).normalized().dot(d) > 0.985),
                   key=lambda p: V((p.x - ccx, p.y - ccy, 0)).length, default=None)
        r0 = V((best.x - ccx, best.y - ccy, 0)).length - 0.006 if best else rx
        f = math.sin(math.pi * i / cols)                 # 0 at the ends, 1 in the middle
        col = []
        for j in range(rows + 1):
            t = j / rows
            L = 0.175 * (f ** 0.7) * t
            zz = z_band + 0.002 - 0.030 * t * t * (0.6 + 0.4 * f) - 0.010 * (1 - f) * t
            col.append(bm.verts.new((ccx + d.x * (r0 + L), ccy + d.y * (r0 + L), zz)))
        grid.append(col)
    for i in range(cols):
        for j in range(rows):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    me = bpy.data.meshes.new("Guard_Visor"); bm.to_mesh(me); bm.free()
    vis = link(bpy.data.objects.new("Guard_Visor", me))
    s = vis.modifiers.new("t", 'SOLIDIFY'); s.thickness = 0.011; s.offset = 0
    sb = vis.modifiers.new("s", 'SUBSURF'); sb.levels = 1
    ctx_obj(vis); bpy.ops.object.modifier_apply(modifier="t"); bpy.ops.object.modifier_apply(modifier="s")
    for p in vis.data.polygons:
        p.use_smooth = True
    for p in dome.data.polygons:
        p.use_smooth = True
    capm = simple_mat("Guard_Cap_Mat", G["navy"], 0.7)
    dome.data.materials.append(capm); vis.data.materials.append(simple_mat("Guard_Visor_Mat", G["navy_dark"], 0.55))
    emb = shield("Guard_CapEmblem", 0.07)
    hit = BVHTree.FromObject(dome, bpy.context.evaluated_depsgraph_get()).ray_cast(
        V((c[0], -1.5, z_band + (hi[2] - z_band) * 0.40)), V((0, 1, 0)))
    emb.location = hit[0] + V((0, -0.004, 0)); emb.rotation_euler = (math.radians(90 - 20), 0, 0)
    ctx_obj(emb); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for m in emb.data.materials:
        m.name = "Guard_Gold_Mat"
    return join([dome, vis, emb], "Guard_Cap")


def belt_v2(body, z=1.035):
    pts = inside_ring(body, z, 0.010, n=56)
    belt = ring_mesh("Guard_Belt", pts, 0.070, 0.020)
    for p in belt.data.polygons:
        p.use_smooth = False
    belt.data.materials.append(simple_mat("Guard_Belt_Mat", (0.06, 0.06, 0.065), 0.5))
    front = min(pts, key=lambda p: p.y)
    buckle = rounded_box("Guard_Buckle", (0.060, 0.014, 0.045), bevel=0.008)
    buckle.location = V((0, front.y - 0.024, z)); buckle.data.materials.append(simple_mat("Guard_Metal_Mat", G["silver"], 0.3, 0.9))
    right = max(pts, key=lambda p: p.x); left = min(pts, key=lambda p: p.x)
    radio = rounded_box("Guard_Radio", (0.030, 0.050, 0.090), bevel=0.012)
    radio.location = right + V((0.038, -0.01, -0.02))
    ant = tube("Guard_Antenna", [radio.location + V((0, 0.015, 0.06)), radio.location + V((0, 0.015, 0.16))], 0.008, sides=8)
    led = rounded_box("Guard_Led", (0.006, 0.012, 0.008), bevel=0.002); led.location = radio.location + V((0.016, -0.012, 0.035))
    for o in (radio, ant):
        o.data.materials.append(simple_mat("Guard_Radio_Mat", (0.12, 0.13, 0.14), 0.5))
    led.data.materials.append(simple_mat("Guard_Led_Mat", (0.25, 0.95, 0.40), 0.3, 0, emit=2.0))
    pouch = rounded_box("Guard_Pouch", (0.030, 0.060, 0.070), bevel=0.012); pouch.location = left + V((-0.034, 0.0, -0.01))
    pouch.data.materials.append(simple_mat("Guard_Belt_Mat", (0.06, 0.06, 0.065), 0.5))
    flash = tube("Guard_Flashlight", [left + V((-0.030, 0.06, 0.03)), left + V((-0.030, 0.06, -0.11))], 0.018, sides=14)
    flash.data.materials.append(simple_mat("Guard_Radio_Mat", (0.12, 0.13, 0.14), 0.5))
    fh = tube("Guard_FlashHead", [left + V((-0.030, 0.06, -0.11)), left + V((-0.030, 0.06, -0.145))], 0.025, sides=16)
    fh.data.materials.append(simple_mat("Guard_Metal_Mat", G["silver"], 0.25, 0.9))
    parts = [belt, buckle, radio, ant, led, pouch, flash, fh]
    for o in parts:
        ctx_obj(o); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return join(parts, "Guard_DutyBelt")


def customer_clips(base):
    """The customer's own clips (Walking, Idle...) re-imported (load_character drops them), named Guard_*."""
    before = set(bpy.data.objects); acts = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CHARS, base + ".fbx"))
    for o in [o for o in bpy.data.objects if o not in before]:
        bpy.data.objects.remove(o, do_unlink=True)
    new = [a for a in bpy.data.actions if a not in acts]
    for a in new:
        a.name = "Guard_" + a.name.split("|")[-1]; a.use_fake_user = True
    return new


def build_guard_v2():
    rig, body = load_character("Customer_09", "Guard")
    info = BodyInfo(body)
    repaint(body)
    cap = cap_v2(info, body); weights_rigid(cap, rig, "Head")
    belt = belt_v2(body); weights_rigid(belt, rig, "Torso")
    if not body.modifiers.get("Armature") and not any(m.type == 'ARMATURE' for m in body.modifiers):
        m = body.modifiers.new("Armature", 'ARMATURE'); m.object = rig
    clips = customer_clips("Customer_09")
    print("guard v2", [o.name for o in rig.children], "clips", [a.name for a in clips])
    return rig
