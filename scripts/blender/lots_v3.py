"""lots_v3.py - third generation of the locked-lot ruins (Lucas 25/10: the old ones were far below the city's quality).

Built one at a time for approval. So far: Lot_Casa (abandoned one-storey house of lot A1).

Run from the Blender MCP / Text editor:

    import sys, importlib; sys.path.insert(0, r"C:\\Checkout-mobile\\scripts\\blender")
    import lots_v3 as V; importlib.reload(V)
    V.build_casa()                 # rebuilds collection "V3 Casa" (several short steps: see build_casa)
    V.stage(); V.render_iso("casa_v3_iso")
    V.make_export(); V.bake(); V.export()   # -> Temp/qa/lots_v3/export/Lot_Casa.fbx + Lot_Casa_BaseColor.png

Conventions (same as ArtSource/lot_kit.py + lot_pipe.py, read by CheckoutLotSites.Ruin()/Paint()):
  * modelled in metres, front (avenue side, Unity -Z) facing Blender -Y, ground at z=0, origin at the lot centre;
  * export_unity(turn=True): FBX -Z forward / Y up, objects turned 180 deg -> Blender (x, y) == Unity (x, z);
  * one material per FBX (<name>_Mat); the colour is baked into <name>_BaseColor.png (2048, smart-UV atlas) which
    Paint() puts on a Standard material, so everything (AO / painted shading included) lives in that texture;
  * the invisible "CASA_pad" (hidden by Ruin() because its name ends with _pad) is 10.0 x 11.6 m: Ruin() fits the
    model's bounds into the lot (11.5 x 13.25 minus 1.4) => scale ~1.01, and depth > width keeps it un-rotated;
  * no letters or words anywhere (the game is multilingual).
Game camera (MarketSimulation.UpdateCamera): orthographic, offset (28, 33, -38) from the focus in Unity
= direction (28, -38, 33) in Blender: ~35 deg down, looking from the front-right (south-east).
"""
import bpy, bmesh, math, os, random, sys, importlib
from mathutils import Vector, Matrix, Euler

ROOT = r"C:\Checkout-mobile"
UNITY = os.path.join(ROOT, "unity", "CheckoutSimulator")
ART = os.path.join(UNITY, "ArtSource")
QA = os.path.join(UNITY, "Temp", "qa", "lots_v3")
EXPORT = os.path.join(QA, "export")
for p in (os.path.join(ROOT, "scripts", "blender"), ART):
    if p not in sys.path:
        sys.path.insert(0, p)
import checkout_project as cp

GAME_DIR = Vector((28, -38, 33)).normalized()
LOT_W, LOT_D = 11.5, 13.25


def col(name, parent=None):
    return cp.collection(name, parent)


def show_only(*names):
    """Exclude every top-level collection except `names` (+ Stage)."""
    for ch in bpy.context.view_layer.layer_collection.children:
        ch.exclude = ch.name not in names + ("Stage", "Studio")


# ------------------------------------------------------------------ stage (ground + light + camera)
def _img_mat(name, path, tile, rough=.95, tint=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True)
    nt.links.new(mp.outputs[0], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    return m


def stage(lot_center=(0, -.25), extra=()):
    """Ground like the game: the lot's bare earth (Game/lot_dirt.png, 7 m tile) on light pavers, soft sun."""
    c = col("Stage")
    for o in list(c.objects):
        if o.type == 'MESH':
            bpy.data.objects.remove(o)
    cp.studio()
    sc = bpy.context.scene
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (.80, .84, .86, 1)
    sun = bpy.data.objects["Studio Sun"]
    sun.data.energy = 3.6
    sun.rotation_euler = (math.radians(48), math.radians(0), math.radians(35))
    dirt = _img_mat("STAGE_Dirt", os.path.join(UNITY, "Assets", "Resources", "CheckoutDesktop", "Game", "lot_dirt.png"), 7.0)
    import era_kit as k
    pav = k.pavers("ERA_Pavers")
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -.03))
    g = bpy.context.active_object; g.name = "STAGE_Pavers"; g.scale = (90, 90, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    g.data.materials.append(pav); k.link(g, c)
    for cx, cy in [lot_center] + list(extra):
        # the game's lot ground: Game/lot_dirt.png, 7 m tile in world metres, drawn ~2 cm under the ruin's ground
        bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, -.018))
        d = bpy.context.active_object; d.name = "STAGE_Lot"; d.scale = (LOT_W, LOT_D, 1)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        d.data.materials.append(dirt); k.link(d, c)
    sc.render.engine = "BLENDER_EEVEE"
    try:
        sc.eevee.use_shadows = True
        sc.eevee.use_raytracing = True
        sc.eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = -.1
    return c


def camera(target, ortho, direction=GAME_DIR, res=(1600, 1000), persp_lens=None):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("Studio Cam")
    if not cam:
        cam = bpy.data.objects.new("Studio Cam", bpy.data.cameras.new("Studio Cam")); col("Stage").objects.link(cam)
    d = Vector(direction).normalized(); t = Vector(target)
    if persp_lens:
        cam.data.type = 'PERSP'; cam.data.lens = persp_lens; cam.location = t + d * ortho
    else:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho; cam.location = t + d * 80
    cam.data.clip_end = 400
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    return cam


def render(name):
    os.makedirs(QA, exist_ok=True)
    sc = bpy.context.scene
    sc.render.filepath = os.path.join(QA, name + ".png")
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


# ------------------------------------------------------------------ the current (old) Casa, as the game shows it
def old_casa():
    """Imports Resources/CheckoutLots/Lot_Casa.fbx under 'OLD Casa' placed like CheckoutLotSites.Ruin() does:
    its bounds (7.1 x 6.1, wider than deep) are turned 90 deg to fit the deeper lot, scaled by the 1.15 cap,
    the _pad hidden."""
    c = col("OLD Casa")
    if c.objects:
        return c
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(UNITY, "Assets", "Resources", "CheckoutLots", "Lot_Casa.fbx"))
    objs = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new("OLD_root", None); c.objects.link(root)
    for o in objs:
        for cc in list(o.users_collection): cc.objects.unlink(o)
        c.objects.link(o); o.parent = root
    img = bpy.data.images.load(os.path.join(UNITY, "Assets", "Resources", "CheckoutLots", "Lot_Casa_BaseColor.png"), check_existing=True)
    for o in objs:
        if o.type == 'MESH':
            for m in o.data.materials:
                if m and m.use_nodes and not any(n.bl_idname == "ShaderNodeTexImage" for n in m.node_tree.nodes):
                    t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = img
                    m.node_tree.links.new(t.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        if o.name.endswith("_pad"):
            o.hide_render = True; o.hide_set(True)
    # imported FBX = modelling frame turned 180; the game then turns it 90 (Unity yaw +90 = Blender -90) and scales 1.15
    root.rotation_euler = (0, 0, math.radians(180 - 90))
    root.scale = (1.15,) * 3
    return c


def reference(name, location, rot_z=0.0, fit=None, cname="REF City"):
    """A MapModels building at the size the city places it (CheckoutCityModelsBuilder: fitted into `fit` = (w, h, d))."""
    c = col(cname)
    before = set(bpy.data.objects)
    objs = cp.reference(name, (0, 0, 0), col=cname)
    root = bpy.data.objects.new("REF_" + name, None); c.objects.link(root)
    for o in objs:
        if o.parent is None: o.parent = root
    bpy.context.view_layer.update()
    lo = Vector((1e9,) * 3); hi = -lo
    for o in objs:
        if o.type != 'MESH': continue
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    size = hi - lo
    s = 1.0
    if fit:
        s = min(fit[0] / size.x, fit[1] / size.z, fit[2] / size.y)
    root.scale = (s,) * 3
    root.location = (location[0] - (lo.x + hi.x) / 2 * s, location[1] - (lo.y + hi.y) / 2 * s, -lo.z * s)
    if rot_z:
        piv = bpy.data.objects.new("REFP_" + name, None); c.objects.link(piv); piv.location = (location[0], location[1], 0)
        root.parent = piv; root.location = (root.location.x - location[0], root.location.y - location[1], root.location.z)
        piv.rotation_euler = (0, 0, rot_z)
    dg = bpy.context.evaluated_depsgraph_get()
    tris = sum(len(o.evaluated_get(dg).data.loop_triangles) for o in objs if o.type == 'MESH')
    return {"name": name, "size": [round(x * s, 2) for x in size], "scale": round(s, 3), "tris": tris}


# ================================================================== colours (sRGB hex -> linear)
def C(h, a=1.0):
    h = h.lstrip("#")
    def lin(v):
        v = int(v, 16) / 255
        return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
    return (lin(h[0:2]), lin(h[2:4]), lin(h[4:6]), a)


# ================================================================== node helper
class NT:
    """Tiny node-tree builder for the procedural (bakeable, Cycles + EEVEE) materials."""
    def __init__(s, name, rough=.85):
        s.m = bpy.data.materials.get(name) or bpy.data.materials.new(name); s.m.use_nodes = True
        s.nt = s.m.node_tree; s.n = s.nt.nodes; s.L = s.nt.links
        s.n.clear()   # rebuilt in place so objects keep their material
        out = s.n.new("ShaderNodeOutputMaterial"); s.bsdf = s.n.new("ShaderNodeBsdfPrincipled")
        s.L.new(s.bsdf.outputs[0], out.inputs["Surface"])
        s.bsdf.inputs["Roughness"].default_value = rough
        s._geo = s._tc = None

    def plug(s, sock, v):
        if isinstance(v, bpy.types.NodeSocket): s.L.new(v, sock)
        else: sock.default_value = v

    @property
    def geo(s):
        if s._geo is None: s._geo = s.n.new("ShaderNodeNewGeometry")
        return s._geo

    @property
    def obj(s):
        if s._tc is None: s._tc = s.n.new("ShaderNodeTexCoord")
        return s._tc.outputs["Object"]

    @property
    def pos(s): return s.geo.outputs["Position"]

    @property
    def island(s): return s.geo.outputs["Random Per Island"]

    def noise(s, vec, scale, detail=4., rough=.5, dist=0.):
        n = s.n.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = dist
        s.L.new(vec, n.inputs["Vector"]); return n.outputs["Fac"]

    def scale(s, vec, sx, sy, sz, off=(0, 0, 0)):
        mp = s.n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (sx, sy, sz)
        mp.inputs["Location"].default_value = off
        s.L.new(vec, mp.inputs["Vector"]); return mp.outputs[0]

    def vor(s, vec, scale, feature='DISTANCE_TO_EDGE', out="Distance"):
        v = s.n.new("ShaderNodeTexVoronoi"); v.feature = feature; v.inputs["Scale"].default_value = scale
        s.L.new(vec, v.inputs["Vector"]); return v.outputs[out]

    def ramp(s, f, lo, hi, a=0., b=1.):
        r = s.n.new("ShaderNodeMapRange"); r.clamp = True
        r.inputs["From Min"].default_value = lo; r.inputs["From Max"].default_value = hi
        r.inputs["To Min"].default_value = a; r.inputs["To Max"].default_value = b
        s.plug(r.inputs["Value"], f); return r.outputs[0]

    def mix(s, a, b, f, blend='MIX'):
        m = s.n.new("ShaderNodeMix"); m.data_type = 'RGBA'; m.blend_type = blend
        s.plug(m.inputs[6], a); s.plug(m.inputs[7], b); s.plug(m.inputs[0], f); return m.outputs[2]

    def mul(s, col, f): return s.mix(col, f, 1.0, 'MULTIPLY')

    def math(s, op, a, b=None):
        n = s.n.new("ShaderNodeMath"); n.operation = op
        s.plug(n.inputs[0], a)
        if b is not None: s.plug(n.inputs[1], b)
        return n.outputs[0]

    def comp(s, vec, axis):
        x = s.n.new("ShaderNodeSeparateXYZ"); s.L.new(vec, x.inputs[0]); return x.outputs[axis]

    def tint(s, col, amount=.12):
        """Per-island (per plank / tile / brick) value + hue jitter."""
        f = s.ramp(s.island, 0, 1, 1 - amount, 1 + amount)
        return s.mul(col, f)

    def ao(s, col, strength=.55, dist=.6):
        a = s.n.new("ShaderNodeAmbientOcclusion"); a.inputs["Distance"].default_value = dist; a.samples = 24
        f = s.ramp(a.outputs["AO"], 0, 1, 1 - strength, 1.0)
        return s.mul(col, f)

    def done(s, col, bump=None, strength=.25, ao=.42, ao_dist=.6):
        if ao: col = s.ao(col, ao, ao_dist)
        s.L.new(col, s.bsdf.inputs["Base Color"])
        if bump is not None and strength:
            b = s.n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = strength
            s.L.new(bump, b.inputs["Height"]); s.L.new(b.outputs["Normal"], s.bsdf.inputs["Normal"])
        return s.m


def brick_tex(t, vec, scale=1.0, c1=C("D2683F"), c2=C("BC5636"), mortar=C("EBDDC2"), bw=.25, rh=.085, msize=.012, smooth=.4):
    """Brick courses along world X+Y (so it wraps both wall directions), rows in Z."""
    br = t.n.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = scale; br.inputs["Mortar Size"].default_value = msize
    br.inputs["Mortar Smooth"].default_value = smooth; br.inputs["Bias"].default_value = 0
    br.inputs["Color1"].default_value = c1; br.inputs["Color2"].default_value = c2; br.inputs["Mortar"].default_value = mortar
    br.inputs["Brick Width"].default_value = bw; br.inputs["Row Height"].default_value = rh
    u = t.math('ADD', t.comp(vec, "X"), t.comp(vec, "Y"))
    cm = t.n.new("ShaderNodeCombineXYZ"); t.L.new(u, cm.inputs["X"]); t.L.new(t.comp(vec, "Z"), cm.inputs["Y"])
    t.L.new(cm.outputs[0], br.inputs["Vector"])
    return br.outputs["Color"], br.outputs["Fac"]


# ================================================================== materials
def m_plaster(name, paint, band=None, band_top=.85, chips=.5, seed=0.):
    """Clean painted plaster like the city houses: flat paint with a very soft tone shift, a crisp painted band
    (barrado) at the foot, and a few deliberate chipped patches with sharp edges and a pale plaster rim showing
    neat bricks. World-space so neighbouring walls line up. (v4: no smears / rain streaks.)"""
    t = NT(name, .9)
    p = t.pos; z = t.comp(p, "Z")
    po = t.scale(p, 1, 1, 1, (seed, seed * .7, 0))
    col = t.mul(paint, t.ramp(t.noise(po, .3, 2, .4), .3, .7, .965, 1.035))
    if band is not None:
        bz = t.ramp(z, band_top - .004, band_top + .004)
        bcol = t.mul(band, t.ramp(t.noise(po, .4, 2, .4), .3, .7, .95, 1.04))
        col = t.mix(bcol, col, bz)
        # darker painted edge line on top of the band
        col = t.mix(col, (band[0] * .62, band[1] * .62, band[2] * .62, 1), t.math('MULTIPLY', t.ramp(z, band_top - .035, band_top - .028), t.ramp(z, band_top + .001, band_top - .006)))
    # chipped patches: smooth blobs with a slightly ragged but crisp outline
    f = t.math('ADD', t.noise(t.scale(po, 1, 1, 1.35), .62, 1.5, .4), t.math('MULTIPLY', t.noise(po, 7, 2, .5), .045))
    f = t.math('ADD', f, t.ramp(z, 0, 1.4, .05, 0))
    thr = .72 - chips * .06
    hole = t.ramp(f, thr, thr + .004)
    rim = t.math('SUBTRACT', t.ramp(f, thr - .028, thr - .024), hole)
    bcol, bfac = brick_tex(t, p, smooth=.05)
    bcol = t.mul(bcol, t.ramp(f, thr, thr + .05, .82, 1.0))          # soft shadow under the broken edge
    col = t.mix(col, C("FBF1DC"), rim)
    col = t.mix(col, bcol, hole)
    col = t.mul(col, t.ramp(z, 0, .35, .9, 1.0))                     # a touch darker at the foot
    return t.done(col, t.math('MULTIPLY', hole, -1.0), .2)


def m_stone(name, base=C("F5E9CB"), dark=C("DECBA4")):
    t = NT(name, .85)
    p = t.pos
    col = t.mix(base, dark, t.ramp(t.noise(p, 3.5, 4, .55), .4, .7))
    col = t.tint(col, .07)
    col = t.mix(col, C("B7A27E"), t.ramp(t.noise(p, 1.4, 2), .66, .74, 0, .25))   # a few soft weathered spots
    return t.done(col, t.noise(p, 9, 3), .2)


def m_tiles(name, a=C("EA673B"), b=C("D9572F"), light=C("F49157"), moss=C("8EA84E")):
    t = NT(name, .8)
    p = t.pos
    isl = t.island
    col = t.mix(a, b, t.ramp(isl, .2, .8))
    col = t.mix(col, light, t.ramp(isl, .82, .95))
    col = t.mul(col, t.ramp(t.noise(p, 2.2, 2), .3, .7, .93, 1.05))
    mz = t.math('ADD', t.noise(p, 1.6, 4, .6), t.math('MULTIPLY', isl, .12))
    col = t.mix(col, moss, t.ramp(mz, .72, .78, 0, .6))
    col = t.mix(col, C("7A4430"), t.ramp(t.noise(p, 2.4, 4), .72, .86, 0, .2))
    return t.done(col, t.noise(p, 12, 3), .15, ao=.45, ao_dist=.35)


def m_paint_wood(name, paint, wood=C("B98A5A"), peel=.5, rough=.75):
    """Painted boards (door, shutters, gate) with paint flaking off to bare wood."""
    t = NT(name, rough)
    p = t.pos
    col = t.mul(paint, t.ramp(t.noise(p, 1.2, 3), .3, .7, .88, 1.08))
    pf = t.noise(t.scale(p, 3, 3, .6), 3.2, 5, .65)
    hole = t.ramp(pf, .66 - peel * .1, .69 - peel * .1)
    col = t.mix(col, wood, hole)
    col = t.mix(col, C("FFFFFF"), t.ramp(t.noise(p, 7, 2), .7, .8, 0, .12))
    return t.done(col, hole, .2)


def m_wood(name, light=C("C9A777"), dark=C("8E6B45"), grey=C("9C9384"), rough=.85):
    """Weathered boards; each plank (mesh island) its own tone, grain along the longest axis (via noise stretch)."""
    t = NT(name, rough)
    p = t.pos
    col = t.mix(light, dark, t.ramp(t.island, 0, 1))
    col = t.mix(col, grey, t.ramp(t.noise(p, 1.6, 3), .45, .7, 0, .5))
    g = t.noise(t.scale(p, 18, 18, 18), 1.0, 6, .7, 3)
    col = t.mul(col, t.ramp(g, .3, .7, .82, 1.1))
    return t.done(col, g, .15)


def m_flat(name, col, var=.08, scale=6., rough=.8, island=0., ao=.5):
    t = NT(name, rough)
    c = t.mul(col, t.ramp(t.noise(t.pos, scale, 3), .3, .7, 1 - var, 1 + var))
    if island: c = t.tint(c, island)
    return t.done(c, ao=ao)


def m_rust(name, paint, rust=C("98532F"), amount=.45, rough=.6):
    t = NT(name, rough)
    p = t.pos
    col = t.mul(paint, t.ramp(t.noise(p, 2, 3), .3, .7, .85, 1.08))
    r = t.ramp(t.noise(t.scale(p, 2, 2, .5), 2.4, 5, .6), .62 - amount * .1, .68 - amount * .1)
    col = t.mix(col, t.mix(rust, C("6A3A22"), t.ramp(t.noise(p, 12, 2), .4, .6)), r)
    return t.done(col, r, .2)


def m_green(name, dark, light, z0=0., z1=1., var=.15):
    """Foliage / grass: dark at the base, sunny tips, painted dapples."""
    t = NT(name, .8)
    p = t.pos
    col = t.mix(dark, light, t.ramp(t.comp(p, "Z"), z0, z1))
    col = t.mul(col, t.ramp(t.noise(p, 3.5, 3), .3, .7, 1 - var, 1 + var))
    col = t.tint(col, .08)
    return t.done(col, t.noise(p, 10, 2), .2, ao=.45, ao_dist=.4)


def m_tarp(name, col=C("3F8ED3")):
    t = NT(name, .6)
    p = t.pos
    c = t.mul(col, t.ramp(t.noise(p, 1.5, 3), .3, .7, .85, 1.1))
    c = t.mix(c, C("8FB6D9"), t.ramp(t.noise(p, 4, 4), .66, .75, 0, .6))   # sun-bleached
    return t.done(c, t.noise(p, 5, 2), .3)


def m_lawn(name, a=C("6DB33F"), b=C("8FCB4C"), edge=C("4E9A35")):
    t = NT(name, .85)
    p = t.pos
    col = t.mix(a, b, t.ramp(t.noise(p, .9, 2, .4), .35, .65))
    col = t.mix(col, C("A9D95C"), t.ramp(t.noise(p, 3.0, 2, .5), .62, .7, 0, .5))      # sunny dapples
    col = t.mix(col, edge, t.ramp(t.comp(t.geo.outputs["Normal"], "Z"), .8, .3))          # darker rounded rim
    return t.done(col, ao=.35)


def m_bark(name, light=C("C87638"), dark=C("8E4B24")):
    """The city trees' warm orange-brown trunk with soft vertical grooves."""
    t = NT(name, .8)
    p = t.pos
    g = t.noise(t.scale(p, 9, 9, 1.2), 1.4, 3, .5)
    col = t.mix(light, dark, t.ramp(g, .4, .7))
    col = t.mix(col, C("DB8F4E"), t.ramp(t.comp(t.geo.outputs["Normal"], "Z"), .3, .9, 0, .4))
    return t.done(col, g, .3)


M = {}


def mats():
    M.clear()
    M["wall"] = m_plaster("V3_CasaWall", C("F7D893"), band=C("3FAA9B"), band_top=.9, chips=.5)
    M["gable"] = m_plaster("V3_CasaGable", C("F7D893"), chips=.3, seed=3.)
    M["lowwall"] = m_plaster("V3_LowWall", C("F6ECD6"), band=C("3FAA9B"), band_top=.3, chips=.55, seed=7.)
    M["chimney"] = m_plaster("V3_Chimney", C("F6ECD6"), chips=.8, seed=11.)
    M["stone"] = m_stone("V3_Stone")
    M["plinth"] = m_stone("V3_Plinth", C("D6C39F"), C("B8A27C"))
    M["tiles"] = m_tiles("V3_Tiles", moss=C("8E8F4C"))
    M["ridge"] = m_tiles("V3_Ridge", C("C9573A"), C("B44C33"), C("D86A45"))
    M["fascia"] = m_paint_wood("V3_Fascia", C("8C4A2A"), C("A98560"), .35)
    M["frame"] = m_paint_wood("V3_Frame", C("A24D27"), C("C4A27A"), .4)
    M["teal"] = m_paint_wood("V3_TealWood", C("23A08D"), C("C29A68"), .5)
    M["wood"] = m_wood("V3_Planks")
    M["deck"] = m_wood("V3_Deck", C("7A5236"), C("5A3B27"), C("6E6252"))
    M["glass"] = m_flat("V3_Glass", C("9FCDE0"), .1, 2, .2, ao=.3)
    M["dark"] = m_flat("V3_Dark", C("3B2F2A"), .05, 3, .9, ao=0)
    M["floor"] = m_flat("V3_RedFloor", C("B4523F"), .12, 3, .7, ao=.6)
    M["concrete"] = m_flat("V3_Concrete", C("C9C0AE"), .1, 4, .9, island=.08)
    M["brick"] = m_flat("V3_Brick", C("C4623E"), .08, 8, .85, island=.12)
    M["tire"] = m_flat("V3_Tire", C("3C3B40"), .06, 8, .7, ao=.4)
    M["gate"] = m_rust("V3_Gate", C("2C8577"), amount=.55)
    M["rust"] = m_rust("V3_RustMetal", C("8E9A96"), amount=.7)
    M["barrow"] = m_rust("V3_Barrow", C("E39A2C"), amount=.45)
    M["bucket"] = m_rust("V3_Bucket", C("E9E3D5"), C("4FA397"), .5)
    M["tarp"] = m_tarp("V3_Tarp")
    M["rope"] = m_flat("V3_Rope", C("E2C891"), .1, 20, .9, ao=.2)
    M["grass"] = m_green("V3_Grass", C("4F8A2C"), C("B9D65A"), 0, .55)
    M["grassdry"] = m_green("V3_GrassDry", C("8C8A3A"), C("E3CF73"), 0, .6)
    M["leaf"] = m_green("V3_Leaf", C("3E7A2F"), C("8CC04A"), .2, 2.4)
    M["ivy"] = m_green("V3_Ivy", C("2F6B2E"), C("6FA843"), 0, 4.5)
    M["treeleaf"] = m_green("V3_TreeLeaf", C("3D7A2E"), C("93C452"), 2.0, 4.6)
    M["bark"] = m_bark("V3_Bark")
    M["fruit"] = m_flat("V3_Orange", C("F59A26"), .08, 10, .5, ao=.2)
    M["flower"] = m_flat("V3_Flower", C("E8443A"), .1, 10, .6, ao=.2)
    M["stepstone"] = m_stone("V3_StepStone", C("D3CBB8"), C("B3A991"))
    M["dirt"] = m_flat("V3_DirtMound", C("9E7652"), .15, 3, .95)
    M["picket"] = m_paint_wood("V3_Picket", C("F1E9D6"), C("A98560"), .6)
    M["lawn"] = m_lawn("V3_Lawn")
    M["tank"] = m_rust("V3_Tank", C("3C86C9"), C("8FB6D9"), .3)
    M["pad"] = m_flat("V3_Pad", C("A88661"), .1, 2, .95, ao=0)
    return M


# ================================================================== geometry
def _M(loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    m = Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4()
    if scale is not None:
        m = m @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1))
    return m


class G:
    """Accumulates many parts into one mesh object (one material, one bevel modifier, smooth + hardened normals).
    `frame` (Matrix) is applied to every part, so a whole window can be built in wall-local coordinates."""
    def __init__(s, name, mat, c, bevel=0., seg=2, frame=None, smooth=True, angle=40):
        s.name, s.mat, s.c, s.bevel, s.seg, s.smooth, s.angle = name, mat, c, bevel, seg, smooth, angle
        s.bm = bmesh.new(); s.frame = frame or Matrix.Identity(4)

    def _put(s, verts, M):
        bmesh.ops.transform(s.bm, matrix=s.frame @ M, verts=verts)

    def box(s, size, loc, rot=(0, 0, 0), M=None, open_bottom=False):
        r = bmesh.ops.create_cube(s.bm, size=1.0)
        if open_bottom:   # the face lying on the ground / on the roof deck is never seen: drop it (and its bevels)
            vs = set(r["verts"])
            for f in [f for f in s.bm.faces if all(v in vs for v in f.verts) and all(v.co.z < 0 for v in f.verts)]:
                s.bm.faces.remove(f)
        s._put(r["verts"], (M or Matrix.Identity(4)) @ _M(loc, rot, size)); return s

    def cyl(s, r, h, loc, rot=(0, 0, 0), verts=12, r2=None, M=None, caps=True):
        res = bmesh.ops.create_cone(s.bm, cap_ends=caps, cap_tris=False, segments=verts, radius1=r,
                                    radius2=r if r2 is None else r2, depth=h)
        s._put(res["verts"], (M or Matrix.Identity(4)) @ _M(loc, rot)); return s

    def ball(s, r, loc, scale=(1, 1, 1), rot=(0, 0, 0), sub=2, M=None):
        res = bmesh.ops.create_icosphere(s.bm, subdivisions=sub, radius=r)
        s._put(res["verts"], (M or Matrix.Identity(4)) @ _M(loc, rot, scale)); return s

    def tube(s, a, b, r, verts=8, r2=None):
        a, b = Vector(a), Vector(b); d = b - a
        q = d.to_track_quat('Z', 'Y')
        M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
        return s.cyl(r, d.length, (0, 0, 0), verts=verts, r2=r2, M=M)

    def torus(s, R, r, loc, rot=(0, 0, 0), seg=16, rseg=8, M=None):
        vs = []; rings = []
        for i in range(seg):
            a = 2 * math.pi * i / seg; ring = []
            for j in range(rseg):
                b = 2 * math.pi * j / rseg
                ring.append(s.bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
            rings.append(ring); vs += ring
        for i in range(seg):
            for j in range(rseg):
                a, b = rings[i], rings[(i + 1) % seg]
                s.bm.faces.new((a[j], b[j], b[(j + 1) % rseg], a[(j + 1) % rseg]))
        s._put(vs, (M or Matrix.Identity(4)) @ _M(loc, rot)); return s

    def prism(s, pts, thick, M=None):
        """Polygon `pts` in local (x, z), extruded `thick` along local Y (centred)."""
        top = [s.bm.verts.new((u, -thick / 2, z)) for (u, z) in pts]
        f = s.bm.faces.new(top)
        r = bmesh.ops.extrude_face_region(s.bm, geom=[f])
        nv = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
        bmesh.ops.translate(s.bm, verts=nv, vec=(0, thick, 0))
        s._put(top + nv, M or Matrix.Identity(4)); return s

    def blades(s, loc, n=7, h=.5, w=.06, seed=0, spread=.10, lean=(.25, .7)):
        """A chunky grass clump: n tapered 3-sided blades leaning out from the centre."""
        rnd = random.Random(seed)
        for i in range(n):
            a = 2 * math.pi * i / n + rnd.uniform(-.4, .4)
            tilt = rnd.uniform(*lean); hh = h * rnd.uniform(.6, 1.1)
            d = Vector((math.cos(a), math.sin(a), 0))
            base = Vector(loc) + d * rnd.uniform(0, spread)
            M = Matrix.Translation(base) @ Matrix.Rotation(rnd.uniform(0, 6.3), 4, 'Z')
            M = Matrix.Translation(base) @ (Matrix.Rotation(tilt, 4, Vector((-d.y, d.x, 0))) @ Matrix.Rotation(rnd.uniform(0, 6.3), 4, 'Z'))
            s.cyl(w * rnd.uniform(.8, 1.2), hh, (0, 0, hh / 2), verts=3, r2=0, M=M, caps=False)
        return s

    clip = None

    def done(s):
        if s.clip is not None:
            bmesh.ops.bisect_plane(s.bm, geom=s.bm.verts[:] + s.bm.edges[:] + s.bm.faces[:], plane_co=(0, 0, s.clip),
                                   plane_no=(0, 0, 1), clear_inner=True)
        bmesh.ops.recalc_face_normals(s.bm, faces=s.bm.faces[:])
        me = bpy.data.meshes.new(s.name); s.bm.to_mesh(me); s.bm.free()
        o = bpy.data.objects.new(s.name, me); s.c.objects.link(o)
        me.materials.append(s.mat)
        for p in me.polygons: p.use_smooth = s.smooth
        if s.bevel:
            b = o.modifiers.new("Bevel", 'BEVEL'); b.width = s.bevel; b.segments = s.seg
            b.limit_method = 'ANGLE'; b.angle_limit = math.radians(s.angle); b.harden_normals = True
            b.miter_outer = 'MITER_ARC'
        return o


def wall_frame(face, u0=0.0):
    """Matrix from wall-local (x along the wall, -y = outward, z up) to world, for the house faces."""
    if face == "F": return Matrix.Translation((u0, HY0, 0))
    if face == "B": return Matrix.Translation((-u0, HY1, 0)) @ Matrix.Rotation(math.pi, 4, 'Z')
    if face == "E": return Matrix.Translation((HX1, u0, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'Z')
    if face == "W": return Matrix.Translation((HX0, -u0, 0)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z')


def cut_rects(rects, hole):
    hx0, hy0, hx1, hy1 = hole; out = []
    for (x0, y0, x1, y1) in rects:
        if hx1 <= x0 or hx0 >= x1 or hy1 <= y0 or hy0 >= y1:
            out.append((x0, y0, x1, y1)); continue
        if hy0 > y0: out.append((x0, y0, x1, hy0))
        if hy1 < y1: out.append((x0, hy1, x1, y1))
        iy0, iy1 = max(y0, hy0), min(y1, hy1)
        if hx0 > x0: out.append((x0, iy0, hx0, iy1))
        if hx1 < x1: out.append((hx1, iy0, x1, iy1))
    return out


# ================================================================== the house
HX0, HX1, HY0, HY1 = -3.6, 3.6, -1.6, 3.6     # outer wall faces
WT, WH = .30, 3.0                              # wall thickness / height
RIDGE_Y = (HY0 + HY1) / 2
PITCH = math.radians(35)
EAVE_OUT, GABLE_OUT = .55, .38
ROOF_Z0 = WH + .12                            # roof underside height at the wall face

# openings per face: (kind, centre u, width, sill z, height)
OPENINGS = {
    "F": [("door", -2.3, 1.05, 0.0, 2.25), ("win", -.55, 1.15, 1.0, 1.25), ("win", 2.05, 1.3, .95, 1.35)],
    "E": [("win", -.15, 1.15, 1.0, 1.25)],          # u along +Y
    "B": [("win", -1.4, 1.1, 1.05, 1.2), ("door", 1.8, .95, 0.0, 2.15)],
    "W": [("win", -1.0, 1.1, 1.05, 1.2)],
}


def face_len(face):
    return (HX1 - HX0) if face in "FB" else (HY1 - HY0)


def face_mid(face):
    """u of the face centre in that face's wall_frame (frames start at x=0 / y=0)."""
    return {"F": 0.0, "B": 0.0, "E": RIDGE_Y, "W": -RIDGE_Y}[face]


def build_walls(c):
    g = G("CASA_walls", M["wall"], c, bevel=.05, seg=2)
    for face in "FBEW":
        Lf = face_len(face); um = face_mid(face)
        # front/back walls run the full length; side walls fit between them
        ext = 0 if face in "FB" else -WT
        rects = [(um - Lf / 2 - ext, 0, um + Lf / 2 + ext, WH)]
        if face in "EW":
            rects = [(um - Lf / 2 + WT, 0, um + Lf / 2 - WT, WH)]
        for (kind, u, w, sill, h) in OPENINGS[face]:
            rects = cut_rects(rects, (u - w / 2, sill, u + w / 2, sill + h))
        F = wall_frame(face)
        for (x0, z0, x1, z1) in rects:
            g.box((x1 - x0, WT, z1 - z0), ((x0 + x1) / 2, WT / 2, (z0 + z1) / 2), M=F, open_bottom=z0 < .01)
    o = g.done()
    # dark inside (seen through the broken panes / the door)
    d = G("CASA_inside", M["dark"], c)
    d.box((HX1 - HX0 - 2 * WT - .02, HY1 - HY0 - 2 * WT - .02, .05), (0, RIDGE_Y, .02))
    d.box((HX1 - HX0 - 2 * WT - .02, .04, WH), (0, HY1 - WT - .03, WH / 2))
    d.box((HX1 - HX0 - 2 * WT - .02, HY1 - HY0 - 2 * WT, .04), (0, RIDGE_Y, WH - .05))
    d.done()
    # gables (east / west), slightly inside the roof
    gg = G("CASA_gables", M["gable"], c, bevel=.04, seg=2)
    half = (HY1 - HY0) / 2; top = ROOF_Z0 + half * math.tan(PITCH) - .08
    pts = [(-half, WH - .02), (half, WH - .02), (half, ROOF_Z0 - .05), (0, top), (-half, ROOF_Z0 - .05)]
    for x in (HX0 + WT / 2, HX1 - WT / 2):
        gg.prism(pts, WT, M=Matrix.Translation((x, RIDGE_Y, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'))
    gg.done()
    return o


def build_trims(c):
    """Chunky stone quoins at the corners, plinth, cornice, window / door surrounds (like the city houses)."""
    q = G("CASA_quoins", M["stone"], c, bevel=.045, seg=2)
    corners = [(HX0, HY0, -1, -1), (HX1, HY0, 1, -1), (HX1, HY1, 1, 1), (HX0, HY1, -1, 1)]
    z = .40; i = 0
    while z < WH - .3:
        h = .52
        for (cx, cy, sx, sy) in corners:
            lx, ly = (.62, .38) if i % 2 == 0 else (.38, .62)
            q.box((lx, ly, h - .05), (cx - sx * (lx / 2 - .05), cy - sy * (ly / 2 - .05), z + h / 2))
        z += h; i += 1
    q.done()
    p = G("CASA_plinth", M["plinth"], c, bevel=.04, seg=1)
    ph = .40
    for face in "FBEW":
        Lf = face_len(face) + .12; um = face_mid(face); F = wall_frame(face)
        segs = [(um - Lf / 2, um + Lf / 2)]
        for (kind, u, w, sill, h) in OPENINGS[face]:
            if kind == "door":
                segs = [(a, b) for (a, b) in segs for (a, b) in ((a, min(b, u - w / 2 - .12)), (max(a, u + w / 2 + .12), b)) if b - a > .05]
        for (a, b) in segs:
            # irregular stone blocks
            x = a; k = 0
            while x < b - .05:
                bw = min(b - x, (1.1, .85, 1.25, .95)[k % 4]); hh = ph if k % 3 else ph - .06
                p.box((bw - .04, .10, hh), (x + bw / 2, -.03, hh / 2), M=F, open_bottom=True)
                x += bw; k += 1
    p.done()
    cr = G("CASA_cornice", M["stone"], c, bevel=.035, seg=2)
    for face in "FB":
        F = wall_frame(face)
        cr.box((HX1 - HX0 + .22, .14, .18), (0, -.05, WH - .05), M=F)
        cr.box((HX1 - HX0 + .14, .08, .07), (0, -.02, WH - .19), M=F)
    for face in "EW":
        F = wall_frame(face)
        cr.box((HY1 - HY0 + .22, .14, .16), (face_mid(face), -.05, WH - .04), M=F)
    cr.done()


def window(c, name, face, u, w, sill, h, style, seed=0):
    """Chunky stone surround + brown wooden frame + panes; style: 'boarded', 'shutters', 'broken'."""
    rnd = random.Random(seed)
    F = wall_frame(face)
    zc = sill + h / 2
    s = G(name + "_surround", M["stone"], c, bevel=.035, seg=2, frame=F)
    s.box((w + .34, .16, .14), (u, -.03, sill + h + .07))               # lintel
    s.box((.20, .12, .24), (u, -.07, sill + h + .10))                     # keystone
    s.box((w + .36, .22, .12), (u, -.07, sill - .05))                     # sill
    for sx in (-1, 1):
        s.box((.17, .12, h + .02), (u + sx * (w / 2 + .085), -.02, zc))
    s.done()
    fr = G(name + "_frame", M["frame"], c, bevel=.014, seg=1, frame=F)
    ft = .07
    fr.box((w, .10, ft), (u, .06, sill + h - ft / 2)); fr.box((w, .10, ft), (u, .06, sill + ft / 2))
    for sx in (-1, 1): fr.box((ft, .10, h), (u + sx * (w / 2 - ft / 2), .06, zc))
    fr.box((.05, .07, h - 2 * ft), (u, .06, zc)); fr.box((w - 2 * ft, .07, .05), (u, .06, sill + h * .58))
    fr.done()
    gl = G(name + "_glass", M["glass"], c, frame=F)
    missing = {1, 2} if style == "broken" else set()
    pw, i = (w - 2 * ft) / 2, 0
    for sx in (-1, 1):
        for (z0, z1) in ((sill + ft, sill + h * .58), (sill + h * .58, sill + h - ft)):
            if i not in missing:
                gl.box((pw - .04, .02, z1 - z0 - .03), (u + sx * pw / 2, .08, (z0 + z1) / 2))
            elif style == "broken":   # jagged shard left in the corner
                gl.prism([(0, 0), (pw * .6, 0), (0, (z1 - z0) * .7)], .02,
                         M=Matrix.Translation((u + sx * pw / 2 - pw / 2 + .03, .08, z0 + .02)))
            i += 1
    gl.done()
    if style in ("boarded", "broken"):
        pl = G(name + "_planks", M["wood"], c, bevel=.012, seg=1, frame=F)
        n = 3 if style == "boarded" else 2
        zs = [sill + h * (k + .5) / n for k in range(n)]
        if style == "broken": zs = [sill + h * .78, sill + h * .3]
        for k, zz in enumerate(zs):
            ang = rnd.uniform(-.18, .18) if k % 2 == 0 else rnd.uniform(-.08, .08)
            pl.box((w + .42, .045, .17), (u + rnd.uniform(-.06, .06), -.14, zz), rot=(0, ang, 0))
        if style == "boarded":   # one diagonal brace
            pl.box((math.hypot(w, h) * .95, .04, .15), (u, -.18, zc), rot=(0, math.atan2(h, w) * (1 if seed % 2 else -1), 0))
        pl.done()
        nails = G(name + "_nails", M["rust"], c, frame=F)
        for k, zz in enumerate(zs):
            for sx in (-1, 1):
                nails.cyl(.022, .02, (u + sx * (w / 2 + .1), -.17, zz), rot=(math.pi / 2, 0, 0), verts=6)
        nails.done()
    if style in ("shutters", "broken"):
        sh = G(name + "_shutters", M["teal"], c, bevel=.012, seg=1, frame=F)
        sw = w / 2 + .04
        # left shutter open flat against the wall, right one hanging from its lower hinge
        lM = Matrix.Translation((u - w / 2 - .17 - sw / 2, -.1, zc))
        # right one swung out and hanging from its lower hinge
        rM = (Matrix.Translation((u + w / 2 + .17, -.08, sill + .05)) @ Matrix.Rotation(-1.05, 4, 'Z')
              @ Matrix.Rotation(-.13, 4, 'Y') @ Matrix.Translation((sw / 2, 0, h / 2)))
        for k, SM in enumerate((lM, rM)):
            if style == "broken" and k == 1:
                continue
            sh.box((sw, .06, h + .05), (0, 0, 0), M=SM)
            for j in range(5):   # louvres
                sh.box((sw - .12, .05, .09), (0, -.04, -h / 2 + .2 + j * (h - .35) / 4), rot=(.35, 0, 0), M=SM)
            sh.box((sw - .1, .07, .07), (0, -.02, h / 2 - .02), M=SM); sh.box((sw - .1, .07, .07), (0, -.02, -h / 2 + .02), M=SM)
        sh.done()


def door(c, name, face, u, w, h, ajar=0.45, back=False):
    F = wall_frame(face)
    s = G(name + "_surround", M["stone"], c, bevel=.04, seg=2, frame=F)
    for sx in (-1, 1): s.box((.2, .14, h + .1), (u + sx * (w / 2 + .1), -.03, (h + .1) / 2))
    s.box((w + .5, .18, .18), (u, -.04, h + .12)); s.box((.24, .2, .3), (u, -.06, h + .14))
    s.done()
    d = G(name + "_door", M["teal"], c, bevel=.014, seg=2, frame=F)
    hinge = Matrix.Translation((u - w / 2 + .02, .05, 0)) @ Matrix.Rotation(ajar, 4, 'Z')
    dw = w - .04
    d.box((dw, .06, h - .02), (dw / 2, 0, h / 2), M=hinge)
    for zz in (h * .3, h * .72):
        d.box((dw - .26, .05, h * .3), (dw / 2, -.04, zz), M=hinge)
    d.box((dw - .1, .07, .08), (dw / 2, -.02, h * .52), M=hinge)
    d.done()
    k = G(name + "_knob", M["rust"], c, frame=F)
    k.ball(.045, (dw - .12, -.09, h * .5), sub=1, M=hinge)
    k.done()


def build_openings(c):
    styles = {("F", 1): "boarded", ("F", 2): "shutters", ("E", 0): "broken", ("B", 0): "boarded", ("W", 0): "boarded"}
    for face, ops in OPENINGS.items():
        for i, (kind, u, w, sill, h) in enumerate(ops):
            nm = f"CASA_{face}{i}"
            if kind == "win":
                window(c, nm, face, u, w, sill, h, styles.get((face, i), "boarded"), seed=i + ord(face))
            else:
                door(c, nm, face, u, w, h, ajar=.5 if face == "F" else .0)


# ------------------------------------------------------------------ roof
ROOF_W = (HX1 - HX0) + 2 * GABLE_OUT
DECK_T = .14
ROW = .54                       # tile course
TILE_W = .92
HOLE = (.35, 1.75, 1.55, 2.75)  # missing tiles on the front slope (local x0, y0, x1, y1)
TARP = (1.95, .25, 3.75, 2.95)  # tarp patch on the front slope
CHIMNEY = (-2.05, .15, .64)     # world x, y, size


def slope_frames():
    ye = HY0 - EAVE_OUT; ze = ROOF_Z0 - EAVE_OUT * math.tan(PITCH)
    Ls = (RIDGE_Y - ye) / math.cos(PITCH)
    Mf = Matrix.Translation((0, ye, ze)) @ Matrix.Rotation(PITCH, 4, 'X')
    Mb = Matrix.Translation((0, HY1 + EAVE_OUT, ze)) @ Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Rotation(PITCH, 4, 'X')
    return Mf, Mb, Ls, ze


def _in(x, y, r, pad=0.):
    return r[0] - pad < x < r[2] + pad and r[1] - pad < y < r[3] + pad


def build_roof(c):
    Mf, Mb, Ls, ze = slope_frames()
    rnd = random.Random(7)
    # deck (dark boards, seen at the eaves and through the hole), cut around the hole on the front slope
    dk = G("CASA_roofDeck", M["deck"], c, bevel=.03, seg=2)
    for Mx, holes in ((Mf, [HOLE]), (Mb, [])):
        rects = [(-ROOF_W / 2, 0, ROOF_W / 2, Ls + .02)]
        for h in holes: rects = cut_rects(rects, h)
        for (x0, y0, x1, y1) in rects:
            dk.box((x1 - x0, y1 - y0, DECK_T), ((x0 + x1) / 2, (y0 + y1) / 2, DECK_T / 2), M=Mx)
    dk.done()
    # battens + a rafter across the hole, darkness below it
    bt = G("CASA_battens", M["wood"], c, bevel=.01, seg=1)
    x0, y0, x1, y1 = HOLE
    for k in range(3):
        y = y0 + .2 + k * ROW
        if y < y1: bt.box((x1 - x0 + .3, .07, .06), ((x0 + x1) / 2, y, DECK_T * .5), rot=(0, 0, rnd.uniform(-.03, .03)), M=Mf)
    bt.box((.11, y1 - y0 + .4, .16), (x0 + (x1 - x0) * .62, (y0 + y1) / 2, -.04), M=Mf)
    bt.box((.11, y1 - y0 + .4, .16), (x0 + .08, (y0 + y1) / 2, -.04), M=Mf)
    bt.done()
    hd = G("CASA_holeDark", M["dark"], c)
    hd.box((x1 - x0 + .1, y1 - y0 + .1, .02), ((x0 + x1) / 2, (y0 + y1) / 2, -.35), M=Mf)
    hd.done()
    # tiles: puffy overlapping courses, staggered, each a little crooked; gaps at the hole / tarp / chimney
    cx, cy, cs = CHIMNEY
    nrows = int(Ls / ROW) + 1
    tl_f = G("CASA_tilesF", M["tiles"], c, bevel=.068, seg=2)
    tl_b = G("CASA_tilesB", M["tiles"], c, bevel=.068, seg=1)
    th = ROW + .17; tt = .15; dl = math.atan2(tt * .9, th)
    for Mx, g, front in ((Mf, tl_f, True), (Mb, tl_b, False)):
        for r in range(nrows):
            y = r * ROW - .04
            if y > Ls - .25: break
            off = (TILE_W / 2) if r % 2 else 0
            x = -ROOF_W / 2 - off
            while x < ROOF_W / 2 - .02:
                xa, xb = max(x, -ROOF_W / 2), min(x + TILE_W, ROOF_W / 2)
                w = xb - xa; xm = (xa + xb) / 2; x += TILE_W
                if w < .2: continue
                yc = y + th / 2
                if front:
                    if _in(xm, yc, HOLE, -.05): continue
                    if _in(xm, yc, TARP, -.25): continue
                    wpos = Mx @ Vector((xm, yc, 0))
                    if abs(wpos.x - cx) < cs / 2 + .12 and abs(wpos.y - cy) < cs / 2 + .1: continue
                elif rnd.random() < .04:
                    continue
                g.box((w - .012, th, tt), (xm + rnd.uniform(-.02, .02), yc, DECK_T + tt / 2 + .035 + rnd.uniform(-.008, .012)),
                      rot=(-dl + rnd.uniform(-.03, .03), rnd.uniform(-.035, .035), rnd.uniform(-.04, .04)), M=Mx, open_bottom=True)
    # a few tiles slipped down next to the hole
    for (u, v, a) in ((.2, 1.25, .5), (1.75, 1.3, -.35), (1.0, 1.05, .15)):
        tl_f.box((TILE_W - .05, th, tt), (u, v, DECK_T + tt + .12), rot=(-.05, .1, a), M=Mf)
    tl_f.done(); tl_b.done()
    # ridge caps (rounded, overlapping)
    rz = ze + Ls * math.sin(PITCH) + DECK_T / math.cos(PITCH) + .06
    rc = G("CASA_ridge", M["ridge"], c, bevel=.02, seg=1)
    n = 11; L = ROOF_W / n
    for i in range(n):
        x = -ROOF_W / 2 + L * (i + .5)
        rc.cyl(.22, L + .1, (x, RIDGE_Y, rz + .02), rot=(rnd.uniform(-.03, .03), math.pi / 2, 0), verts=8, r2=.19)
    rc.box((ROOF_W + .05, .3, .12), (0, RIDGE_Y, rz - .1))
    rc.done()
    # barge boards on the gables + eave fascias
    fb = G("CASA_fascia", M["fascia"], c, bevel=.025, seg=2)
    for Mx in (Mf, Mb):
        for sx in (-1, 1):
            fb.box((.12, Ls + .12, .3), (sx * (ROOF_W / 2 + .03), Ls / 2, .02), M=Mx)
        fb.box((ROOF_W + .14, .11, .26), (0, -.03, .02), M=Mx)
    fb.done()
    return Mf, Ls


def build_tarp(c):
    """Blue tarp tied over the bad patch, weighed down with bricks and an old tyre (no print on it)."""
    Mf, Mb, Ls, ze = slope_frames()
    x0, y0, x1, y1 = TARP
    nx, ny = 14, 12
    bm = bmesh.new(); rnd = random.Random(3)
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x = x0 + (x1 - x0) * u + rnd.uniform(-.02, .02); y = y0 + (y1 - y0) * v
            edge = min(u, 1 - u, v, 1 - v)
            z = DECK_T + .11 + .05 * math.sin(u * 9.0 + v * 3) * math.sin(v * 7.0) + .03 * rnd.random()
            if edge < .08: z -= .06 * (1 - edge / .08)          # edges tucked down onto the tiles
            row.append(bm.verts.new(Mf @ Vector((x, y, z))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    me = bpy.data.meshes.new("CASA_tarp"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("CASA_tarp", me); c.objects.link(o); me.materials.append(M["tarp"])
    for p in me.polygons: p.use_smooth = True
    so = o.modifiers.new("Solid", 'SOLIDIFY'); so.thickness = .025
    # weights on top
    br = G("CASA_tarpBricks", M["brick"], c, bevel=.012, seg=1)
    for (u, v, a) in ((x0 + .15, y0 + .25, .3), (x1 - .2, y0 + .3, -.2), (x0 + .25, y1 - .25, .1), (x1 - .25, y1 - .3, .6), ((x0 + x1) / 2, y1 - .2, -.4)):
        br.box((.24, .12, .08), (u, v, DECK_T + .2), rot=(0, 0, a), M=Mf)
    br.done()
    ty = G("CASA_tarpTyre", M["tire"], c)
    ty.torus(.3, .1, ((x0 + x1) / 2 + .1, (y0 + y1) / 2 - .1, DECK_T + .25), M=Mf)
    ty.done()
    # rope ties down the eave
    rp = G("CASA_tarpRope", M["rope"], c)
    for xx in (x0 + .1, x1 - .1):
        a = Mf @ Vector((xx, y0 + .05, DECK_T + .12)); b = Mf @ Vector((xx + .05, -.02, -.05))
        rp.tube(a, b, .018, verts=5)
    rp.done()
    return o


def build_chimney(c):
    cx, cy, cs = CHIMNEY
    ch = G("CASA_chimney", M["chimney"], c, bevel=.05, seg=2)
    ch.box((cs, cs, 2.6), (cx, cy, 3.0 + 1.3))
    ch.done()
    cp_ = G("CASA_chimneyCap", M["stone"], c, bevel=.04, seg=2)
    cp_.box((cs + .16, cs + .16, .14), (cx, cy, 5.37))
    cp_.box((cs + .08, cs + .08, .08), (cx, cy, 5.06))
    cp_.done()
    pots = G("CASA_chimneyPots", M["ridge"], c, bevel=.015, seg=1)
    pots.cyl(.13, .34, (cx - .13, cy, 5.6), verts=10, r2=.11)
    pots.cyl(.13, .22, (cx + .14, cy + .06, 5.53), rot=(0, .25, 0), verts=10, r2=.12)   # cracked, leaning
    pots.done()
    br = G("CASA_chimneyBricks", M["brick"], c, bevel=.01, seg=1)
    rnd = random.Random(5)
    for k in range(7):   # bricks poking out where the plaster fell
        z = 4.55 + (k % 4) * .1; side = k % 2
        if side: br.box((.22, .05, .07), (cx + rnd.uniform(-.15, .15), cy - cs / 2 - .01, z + (k // 4) * .3))
        else: br.box((.05, .22, .07), (cx + cs / 2 + .01, cy + rnd.uniform(-.15, .15), z + .05 + (k // 4) * .3))
    br.done()


def build_gutter(c):
    Mf, Mb, Ls, ze = slope_frames()
    ye = HY0 - EAVE_OUT - .1
    gt = G("CASA_gutter", M["rust"], c)
    gt.tube((-ROOF_W / 2 + .1, ye, ze - .12), (2.9, ye, ze - .17), .07, verts=8)
    gt.tube((2.9, ye, ze - .17), (3.75, ye - .15, ze - 1.0), .07, verts=8)     # came loose, hanging
    for x in (-3.3, -1.6, .2, 1.8):
        gt.box((.04, .16, .04), (x, ye + .07, ze - .1))
    # downpipe at the front-right corner, its foot broken off and lying in the grass
    gt.tube((3.45, ye + .02, ze - .15), (3.75, HY0 - .12, ze - .5), .055, verts=8)
    gt.tube((3.75, HY0 - .12, ze - .5), (3.75, HY0 - .12, .85), .055, verts=8)
    gt.tube((3.95, HY0 - .9, .06), (4.35, HY0 - 1.6, .06), .055, verts=8)
    gt.done()


# ------------------------------------------------------------------ porch (varanda)
PORCH = (-3.6, .38, -3.15)    # x0, x1, front y


def build_porch(c):
    x0, x1, yf = PORCH
    fl = G("CASA_porchFloor", M["floor"], c, bevel=.03, seg=2)
    fl.box((x1 - x0, HY0 - yf, .2), ((x0 + x1) / 2, (HY0 + yf) / 2, .1))
    fl.done()
    st = G("CASA_porchStep", M["concrete"], c, bevel=.03, seg=2)
    st.box((1.5, .4, .11), (-2.3, yf - .2, .055), rot=(0, 0, .03))
    st.box((.7, .35, .1), (-1.35, yf - .14, .05), rot=(.06, .02, -.25))     # cracked-off piece
    st.done()
    # posts: left and middle standing, right one knocked askew; the roof sags towards it
    pz = 2.42
    po = G("CASA_porchPosts", M["frame"], c, bevel=.025, seg=2)
    for i, x in enumerate((x0 + .2, -1.45, x1 - .2)):
        if i < 2:
            po.box((.17, .17, pz - .2), (x, yf + .2, .2 + (pz - .2) / 2))
            po.box((.28, .28, .12), (x, yf + .2, .26)); po.box((.28, .28, .1), (x, yf + .2, pz - .05))
        else:
            Mp = Matrix.Translation((x + .12, yf + .2, .2)) @ Matrix.Rotation(-.1, 4, 'Y')   # kicked out at the foot
            po.box((.17, .17, pz - .32), (0, 0, (pz - .32) / 2), M=Mp)
            po.box((.28, .28, .1), (0, 0, pz - .3), M=Mp)
    po.done()
    # sagging roof: one frame for beam + deck + tiles, pivoting down at the right end
    piv = Vector((x0, 0, 0))
    sag = Matrix.Translation(piv) @ Matrix.Rotation(.045, 4, 'Y') @ Matrix.Translation(-piv)
    bm_ = G("CASA_porchBeam", M["frame"], c, bevel=.025, seg=2)
    bm_.box((x1 - x0 + .2, .2, .2), ((x0 + x1) / 2, yf + .2, pz + .1), M=sag)
    for x in (x0 + .5, (x0 + x1) / 2, x1 - .5):
        bm_.box((.12, HY0 - yf + .1, .14), (x, (HY0 + yf) / 2, pz + .25), M=sag)
    bm_.done()
    rise = 2.88 - (pz + .3); run = HY0 - (yf - .35)
    p = math.atan2(rise, run)
    Mr = sag @ Matrix.Translation((0, yf - .35, pz + .3 - .35 * math.tan(p))) @ Matrix.Rotation(p, 4, 'X')
    Lr = run / math.cos(p)
    dk = G("CASA_porchDeck", M["deck"], c, bevel=.025, seg=2)
    dk.box((x1 - x0 + .3, Lr, .1), ((x0 + x1) / 2, Lr / 2, .05), M=Mr)
    dk.done()
    tl = G("CASA_porchTiles", M["tiles"], c, bevel=.045, seg=1)
    rnd = random.Random(11)
    th = ROW + .14; tt = .1; dl = math.atan2(tt * .9, th)
    W = x1 - x0 + .3; tw = .8
    for r in range(int(Lr / ROW) + 1):
        y = r * ROW - .04
        if y > Lr - .2: break
        x = -W / 2 - (tw / 2 if r % 2 else 0)
        while x < W / 2 - .02:
            xa, xb = max(x, -W / 2), min(x + tw, W / 2); w = xb - xa; xm = (xa + xb) / 2 + (x0 + x1) / 2; x += tw
            if w < .18: continue
            if r == 1 and abs(xm - (-.9)) < .3: continue            # one missing
            tl.box((w - .012, th, tt), (xm, y + th / 2, .1 + tt / 2 + .03), rot=(-dl + rnd.uniform(-.03, .03), rnd.uniform(-.04, .04), rnd.uniform(-.05, .05)), M=Mr, open_bottom=True)
    tl.done()
    fb = G("CASA_porchFascia", M["fascia"], c, bevel=.02, seg=2)
    fb.box((x1 - x0 + .36, .09, .2), ((x0 + x1) / 2, -.02, .03), M=Mr)
    fb.done()
    # an old chair, a clay pot whose geranium still flowers
    ch = G("CASA_chair", M["wood"], c, bevel=.012, seg=1)
    Mc = Matrix.Translation((-3.15, -2.25, .2)) @ Matrix.Rotation(.5, 4, 'Z')
    ch.box((.46, .44, .05), (0, 0, .45), M=Mc)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ch.box((.05, .05, .45 if sy < 0 else .95), (sx * .19, sy * .18, (.45 if sy < 0 else .95) / 2), M=Mc)
    for z in (.65, .82): ch.box((.42, .04, .08), (0, .18, z), M=Mc)
    ch.done()
    pot = G("CASA_pot", M["ridge"], c, bevel=.015, seg=1)
    pot.cyl(.2, .32, (-.95, -2.15, .2 + .16), verts=12, r2=.25)
    pot.cyl(.27, .06, (-.95, -2.15, .2 + .32), verts=12)
    pot.done()
    pl = G("CASA_potPlant", M["leaf"], c)
    for (dx, dy, dz, r) in ((0, 0, .58, .2), (.12, .06, .52, .14), (-.1, .08, .55, .15), (.02, -.12, .54, .13)):
        pl.ball(r, (-.95 + dx, -2.15 + dy, .2 + dz), scale=(1, 1, .8), sub=2)
    pl.done()
    fw = G("CASA_potFlowers", M["flower"], c)
    for (dx, dy, dz) in ((.08, -.1, .76), (-.12, .02, .74), (.05, .12, .78), (-.02, -.02, .82)):
        fw.ball(.075, (-.95 + dx, -2.15 + dy, .2 + dz), sub=2)
    fw.done()


# ------------------------------------------------------------------ lot boundary: low front wall + gate, picket fences
PAD_W, PAD_D = 10.0, 11.6
FY = -5.47           # centre line of the front wall
GATE = (-2.79, -1.81)


def build_front_wall(c):
    wl = G("CASA_lowWall", M["lowwall"], c, bevel=.04, seg=2)
    cap = G("CASA_lowWallCap", M["stone"], c, bevel=.03, seg=1)
    t, h = .26, .82
    pillars = [-4.72, GATE[0] - .21, GATE[1] + .21, 4.72]
    runs = [(-4.72, GATE[0] - .21), (GATE[1] + .21, 1.05), (2.75, 4.72)]
    for (a, b) in runs:
        wl.box((b - a, t, h), ((a + b) / 2, FY, h / 2), open_bottom=True); cap.box((b - a + .04, t + .1, .09), ((a + b) / 2, FY, h + .04))
    # broken stretch: stepped, jagged remains
    steps = [(1.05, 1.45, .66), (1.45, 1.8, .42), (1.8, 2.15, .22), (2.15, 2.45, .35), (2.45, 2.75, .6)]
    for (a, b, hh) in steps:
        wl.box((b - a, t, hh), ((a + b) / 2, FY, hh / 2), open_bottom=True)
    for x in pillars:
        hp = 1.12
        wl.box((.42, .42, hp), (x, FY, hp / 2), open_bottom=True)
        cap.box((.52, .52, .1), (x, FY, hp + .05)); cap.box((.4, .4, .07), (x, FY, hp + .12))
    wl.done(); cap.done()
    fin = G("CASA_finials", M["stone"], c)
    fin.ball(.15, (GATE[0] - .21, FY, 1.34), sub=2)
    fin.ball(.15, (GATE[1] + .48, FY + .45, .15), sub=2)       # the other one fell off into the grass
    fin.done()
    # rubble of the broken stretch
    rb = G("CASA_wallRubble", M["brick"], c, smooth=False)
    rnd = random.Random(21)
    for k in range(16):
        x = rnd.uniform(1.2, 2.6); y = FY + rnd.uniform(.25, .9); z = .04 + (k // 6) * .07
        rb.box((.24, .12, .08), (x, y, z), rot=(rnd.uniform(-.2, .2), rnd.uniform(-.2, .2), rnd.uniform(0, 3.1)))
    rb.done()
    ch = G("CASA_wallChunks", M["lowwall"], c, bevel=.03, seg=1)
    for (x, y, s) in ((1.6, FY + .55, .3), (2.2, FY + .75, .24), (1.3, FY + 1.0, .2)):
        ch.box((s, s * .8, s * .6), (x, y, s * .3), rot=(.1, .2, rnd.uniform(0, 3)))
    ch.done()
    # iron gate: one leaf, rusty, sagging open on its lower hinge
    gw = GATE[1] - GATE[0] - .04
    Mg = Matrix.Translation((GATE[0] + .02, FY, .08)) @ Matrix.Rotation(1.15, 4, 'Z') @ Matrix.Rotation(.05, 4, 'Y')
    gt = G("CASA_gate", M["gate"], c)
    for z in (.05, .55, .98):
        gt.box((gw, .05, .05), (gw / 2, 0, z), M=Mg)
    for sx in (0, 1): gt.box((.06, .06, 1.0), (.03 + sx * (gw - .06), 0, .5), M=Mg)
    for k in range(1, 8):
        x = gw * k / 8
        gt.cyl(.016, .98, (x, 0, .5), verts=6, M=Mg)
        gt.cyl(.035, .1, (x, 0, 1.03), verts=6, r2=0, M=Mg)
    gt.torus(.1, .018, (gw / 2, 0, .77), rot=(math.pi / 2, 0, 0), seg=12, rseg=5, M=Mg)
    gt.done()


def picket_fence(c, name, a, b, posts_every=1.9, seed=0, states=None):
    """Picket fence from a to b (2D points). states: list per bay of 'ok' | 'gappy' | 'lean' | 'fallen'."""
    rnd = random.Random(seed)
    a, b = Vector((*a, 0)), Vector((*b, 0)); d = b - a; L = d.length; dirv = d.normalized()
    ang = math.atan2(dirv.y, dirv.x)
    nb = max(1, round(L / posts_every)); bay = L / nb
    pk = G(name + "_pickets", M["picket"], c, bevel=.0, smooth=False)
    rl = G(name + "_rails", M["picket"], c, smooth=False)
    po = G(name + "_posts", M["picket"], c, bevel=.02, seg=1)
    outline = [(-.055, 0), (.055, 0), (.055, .86), (0, .97), (-.055, .86)]
    inward = Vector((-dirv.y, dirv.x, 0))
    for i in range(nb + 1):
        p = a + dirv * bay * i
        if states and states[min(i, nb - 1) % len(states)] == 'fallen' and i not in (0, nb):
            continue
        po.box((.12, .12, 1.1), (0, 0, .55), M=Matrix.Translation(p) @ Matrix.Rotation(ang + rnd.uniform(-.05, .05), 4, 'Z') @ Matrix.Rotation(rnd.uniform(-.04, .04), 4, 'X'))
    for i in range(nb):
        st = states[i % len(states)] if states else 'ok'
        base = Matrix.Translation(a + dirv * bay * i) @ Matrix.Rotation(ang, 4, 'Z')
        if st == 'lean': base = base @ Matrix.Rotation(-.35, 4, 'X')
        if st == 'fallen': base = Matrix.Translation(inward * .05) @ base @ Matrix.Rotation(-1.5, 4, 'X') @ Matrix.Translation((0, 0, .06))
        for z in (.25, .72):
            if st == 'gappy' and z > .5:
                rl.box((bay * .45, .05, .08), (bay * .25, .05, z), rot=(0, .25, 0), M=base)
            else:
                rl.box((bay - .1, .05, .08), (bay / 2, .05, z), M=base)
        n = int(bay / .2)
        for k in range(n):
            x = (k + .5) * bay / n
            if st == 'gappy' and rnd.random() < .45: continue
            if rnd.random() < .08: continue
            tilt = rnd.uniform(-.06, .06) + (rnd.uniform(-.35, .35) if rnd.random() < .12 else 0)
            pk.prism(outline, .04, M=base @ Matrix.Translation((x, 0, .04 + rnd.uniform(-.03, .03))) @ Matrix.Rotation(tilt, 4, 'Y'))
    pk.done(); po.done(); rl.done()


def build_fences(c):
    picket_fence(c, "CASA_fenceE", (4.82, -5.2), (4.82, 5.62), seed=3, states=['ok', 'gappy', 'ok', 'fallen', 'lean', 'ok'])
    picket_fence(c, "CASA_fenceW", (-4.82, 5.62), (-4.82, -5.2), seed=4, states=['ok', 'lean', 'gappy', 'ok', 'ok', 'gappy'])
    picket_fence(c, "CASA_fenceN", (4.82, 5.62), (-4.82, 5.62), seed=5, states=['ok', 'gappy', 'ok', 'lean', 'ok'])


# ------------------------------------------------------------------ yard: path, plants, debris
def build_path(c):
    st = G("CASA_path", M["stepstone"], c, bevel=.03, seg=1)
    rnd = random.Random(31)
    for k, y in enumerate((-5.05, -4.5, -3.95)):
        st.cyl(rnd.uniform(.3, .36), .07, (-2.3 + rnd.uniform(-.12, .12), y, .035), verts=9, rot=(0, 0, rnd.uniform(0, 1)))
        if k == 1: st.cyl(.2, .06, (-1.85, y + .1, .03), verts=7)
    st.done()


def tufts(g, pts, seed, size=1.0):
    rnd = random.Random(seed)
    for i, (x, y) in enumerate(pts):
        g.blades((x, y, 0), n=rnd.randint(6, 9), h=rnd.uniform(.38, .62) * size, w=.07 * size, seed=seed * 100 + i)


def build_plants(c):
    rnd = random.Random(41)
    # grass clumps: along the walls and fences, around the debris, between the stones
    green = []; dry = []
    edge = [(-4.5, -5.15), (-3.9, -5.2), (-3.4, -5.05), (-1.3, -5.15), (-.6, -5.2), (.1, -5.1), (.8, -5.0), (2.9, -5.1), (3.5, -5.2), (4.4, -5.05),
            (4.55, -3.6), (4.6, -1.6), (4.5, -.5), (4.6, 1.1), (4.55, 3.0), (4.5, 4.9), (-4.55, -3.8), (-4.6, -2.0), (-4.5, .3), (-4.6, 2.2),
            (-4.5, 4.6), (-2.0, 5.3), (0.5, 5.35), (2.6, 5.3)]
    house = [(-3.75, -1.0), (-3.7, .9), (-3.8, 2.8), (3.8, -1.3), (3.75, .8), (3.85, 3.3), (-1.2, -1.8), (.7, -1.75), (1.4, -1.8), (2.9, -1.8),
             (.5, -3.3), (-3.65, -3.3), (-2.9, -3.45), (-1.7, -3.45), (1.0, 3.8), (-1.5, 3.8)]
    yard = [(-1.7, -4.2), (-2.85, -4.4), (-1.6, -4.9), (-3.0, -4.9), (.1, -4.3), (.9, -3.9), (2.4, -3.9), (3.2, -3.4), (2.0, -4.3), (3.4, -4.6),
            (-.5, -3.7), (-3.9, -4.0), (3.0, -2.7), (3.9, -3.1), (1.6, -2.6)]
    for i, p in enumerate(edge + house + yard):
        (dry if i % 4 == 0 else green).append((p[0] + rnd.uniform(-.1, .1), p[1] + rnd.uniform(-.1, .1)))
    g = G("CASA_grass", M["grass"], c, smooth=False); tufts(g, green, 1); g.done()
    g = G("CASA_grassDry", M["grassdry"], c, smooth=False); tufts(g, dry, 2, 1.15); g.done()
    # tall weeds in the broken wall gap and by the tyres
    g = G("CASA_weeds", M["grass"], c, smooth=False)
    for i, (x, y) in enumerate(((1.6, -5.25), (2.3, -5.3), (4.4, -2.0), (-4.3, -1.6))):
        g.blades((x, y, 0), n=9, h=.9, w=.08, seed=500 + i, lean=(.15, .5))
    g.done()
    # lawn patches: crisp painted shapes with a soft rounded edge (like the city's park lawns), tufts on top
    t = G("CASA_lawn", M["lawn"], c, bevel=.025, seg=1)
    for k, (x, y, sx, sy) in enumerate(((-3.6, -4.4, 1.0, .75), (3.5, -4.2, .95, .8), (.6, -4.55, 1.2, .55), (-.9, -4.7, .6, .4), (3.95, -1.0, .55, 1.3),
                                        (-4.05, -.6, .5, 1.1), (2.4, -2.75, .75, .45), (-4.05, 3.6, .6, 1.3), (3.3, 4.75, 1.1, .6), (-1.0, 4.8, 1.5, .5))):
        rr = random.Random(100 + k); n = 22; ph = [rr.uniform(0, 6.3) for _ in range(3)]
        pts = []
        for q in range(n):
            a = 2 * math.pi * q / n
            rad = 1 + .13 * math.sin(3 * a + ph[0]) + .07 * math.sin(5 * a + ph[1]) + .04 * math.sin(7 * a + ph[2])
            pts.append((x + sx * rad * math.cos(a), y + sy * rad * math.sin(a)))
        top = [t.bm.verts.new((px, py, .045)) for (px, py) in pts]
        bot = [t.bm.verts.new((px, py, 0)) for (px, py) in pts]
        t.bm.faces.new(top)
        for q in range(n):
            t.bm.faces.new((bot[q], bot[(q + 1) % n], top[(q + 1) % n], top[q]))
    t.done()
    # bushes: leaf clusters of the city tree's own crown (same painted texture), small and low on the ground
    for k, (x, y, r, rz) in enumerate(((-4.15, -4.55, .62, .4), (4.1, -4.5, .66, 2.1), (-4.2, -1.1, .5, 3.3), (2.95, -1.95, .38, 1.2),
                                        (-4.1, 2.6, .55, 4.4), (-3.8, 4.75, .62, .9), (.3, 4.9, .52, 5.1))):
        city_tree(f"CASA_bush{k}", c, (x, y, 0), 1, rot_z=rz, tris=650, crown_only=True, width=r * 2.1)


def build_ivy(c):
    """Ivy climbing the east wall corner up onto the gable (the side the game camera sees)."""
    rnd = random.Random(51)
    v = G("CASA_ivyVines", M["bark"], c)
    lv = G("CASA_ivy", M["ivy"], c)
    x = HX1 + .03
    paths = [[(2.6, 0), (2.7, .9), (2.4, 1.8), (2.6, 2.7), (2.2, 3.4), (1.9, 4.0)],
             [(3.2, 0), (3.3, 1.0), (3.05, 2.1), (3.3, 2.9)],
             [(2.6, .9), (2.0, 1.4), (1.6, 2.2)]]
    for path in paths:
        for (y0, z0), (y1, z1) in zip(path, path[1:]):
            v.tube((x + .02, y0, z0), (x + .02, y1, z1), .03, verts=5)
            n = int(math.hypot(y1 - y0, z1 - z0) / .13)
            for k in range(n):
                f = k / max(1, n); yy = y0 + (y1 - y0) * f + rnd.uniform(-.25, .25); zz = z0 + (z1 - z0) * f + rnd.uniform(-.15, .15)
                if zz < .1: continue
                r = rnd.uniform(.12, .19)
                lv.ball(r, (x + r * .3, yy, zz), scale=(.4, 1, .75), rot=(rnd.uniform(-.6, .6), 0, 0), sub=1)
    v.done(); lv.done()


# ------------------------------------------------------------------ the city's own tree (MapModels/StylizedTree)
CITY_TREE = os.path.join(UNITY, "Assets", "Art", "Models", "MapModels", "StylizedTree")
TREE_BAND = .25          # top band of the atlas: [0, TREE_BAND] x [1 - TREE_BAND, 1] holds the city tree's own texture


def m_citytree():
    """The city tree's painted texture read through its own UVs ('TreeUV'); baking copies it into the Casa atlas."""
    m = bpy.data.materials.get("V3_CityTree") or bpy.data.materials.new("V3_CityTree")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"]); b.inputs["Roughness"].default_value = .8
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "TreeUV"
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(CITY_TREE, "StylizedTree_BaseColor.png"), check_existing=True)
    nt.links.new(uvn.outputs[0], t.inputs["Vector"]); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    return m


def city_tree_source():
    """StylizedTree.fbx as one mesh (kept with a fake user), upright, base centred at the origin, 1 m tall."""
    me = bpy.data.meshes.get("CITYTREE_src")
    if me: return me
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CITY_TREE, "StylizedTree.fbx"))
    objs = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in objs if o.type == 'MESH']
    bpy.context.view_layer.update()
    bm = bmesh.new()
    for o in meshes:
        t = o.data.copy(); t.transform(o.matrix_world); bm.from_mesh(t); bpy.data.meshes.remove(t)
    lo = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts), min(v.co.z for v in bm.verts)))
    hi = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts), max(v.co.z for v in bm.verts)))
    h = hi.z - lo.z
    bmesh.ops.transform(bm, matrix=Matrix.Scale(1 / h, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)), verts=bm.verts)
    me = bpy.data.meshes.new("CITYTREE_src"); bm.to_mesh(me); bm.free()
    if me.uv_layers: me.uv_layers[0].name = "TreeUV"
    me.use_fake_user = True
    for o in objs: bpy.data.objects.remove(o)
    return me


def city_tree(name, c, loc, height, rot_z=0., tris=7000, crown_only=False, width=None):
    """A copy of the city tree, decimated (collapse) to about `tris` triangles, `height` tall at `loc`.
    crown_only: just its leaf clusters, sunk into the ground a little (used as bushes)."""
    src = city_tree_source()
    bm = bmesh.new(); bm.from_mesh(src)
    if crown_only:   # drop the trunk: keep the upper crown, then sit it on the ground
        cut = .45
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, cut), plane_no=(0, 0, 1), clear_inner=True)
        top = max(v.co.z for v in bm.verts)
        bmesh.ops.transform(bm, matrix=Matrix.Scale(1 / (top - cut), 4) @ Matrix.Translation((0, 0, -cut - .06 * (top - cut))), verts=bm.verts)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); c.objects.link(o)
    o.location = loc; o.rotation_euler = (0, 0, rot_z); o.scale = (height,) * 3
    if width:   # size by footprint instead of height (bushes)
        xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
        o.scale = (width / max(max(xs) - min(xs), max(ys) - min(ys)),) * 3
    me.materials.clear(); me.materials.append(m_citytree())
    n0 = sum(len(p.vertices) - 2 for p in me.polygons)
    d = o.modifiers.new("Decimate", 'DECIMATE'); d.decimate_type = 'COLLAPSE'; d.ratio = min(1.0, tris / max(1, n0))
    d.use_collapse_triangulate = True
    _apply(o)
    for p in o.data.polygons: p.use_smooth = True
    # atlas UVs: the tree's own layout squeezed into the TREE_BAND square (baking then copies its texture there)
    me = o.data
    tuv = me.uv_layers["TreeUV"]
    if "UVMap" not in me.uv_layers: me.uv_layers.new(name="UVMap")
    au = me.uv_layers["UVMap"]
    ins = .004
    for a, b in zip(au.data, tuv.data):
        a.uv = (ins + b.uv[0] * (TREE_BAND - 2 * ins), 1 - TREE_BAND + ins + b.uv[1] * (TREE_BAND - 2 * ins))
    me.uv_layers.active = au
    # keep it inside the lot (the pad: |x| <= 5, |y| <= 5.8)
    bpy.context.view_layer.update()
    ws = [o.matrix_world @ v.co for v in me.vertices]
    o.location.x += min(0, 4.97 - max(w.x for w in ws)) + max(0, -4.97 - min(w.x for w in ws))
    o.location.y += min(0, 5.77 - max(w.y for w in ws)) + max(0, -5.77 - min(w.y for w in ws))
    bpy.context.view_layer.update()
    return o


def build_tree(c):
    """The city's street tree (MapModels/StylizedTree, as the street trees use it) in the back-right corner,
    decimated for the lot, plus a couple of oranges (it is an old fruit tree nobody picks)."""
    o = city_tree("CASA_tree", c, (3.62, 4.62, 0), 1, rot_z=math.radians(10), tris=7500, width=2.95)
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    # two oranges on the crown's sunny side (towards the game camera), and two fallen ones
    cand = sorted((w for w in ws if w.z > 1.7), key=lambda w: -(w.x * .55 - w.y * .75 + w.z * .4))
    fr = G("CASA_oranges", M["fruit"], c)
    for w in (cand[0], cand[min(len(cand) - 1, 40)]):
        fr.ball(.1, w + Vector((.03, -.05, -.02)), sub=2)
    for (x, y) in ((3.0, 4.0), (4.3, 3.85)):
        fr.ball(.1, (x, y, .1), sub=2)
    fr.done()
    return o


def build_props(c):
    rnd = random.Random(71)
    # tyres: a stack of three + one leaning on the stack
    ty = G("CASA_tyres", M["tire"], c)
    for k in range(3):
        ty.torus(.34, .12, (4.15 + rnd.uniform(-.05, .05), -2.55 + rnd.uniform(-.05, .05), .12 + k * .23), rot=(rnd.uniform(-.06, .06), rnd.uniform(-.06, .06), 0), seg=14, rseg=7)
    ty.torus(.34, .12, (3.65, -2.95, .45), rot=(math.radians(72), 0, .5), seg=14, rseg=7)
    ty.torus(.32, .11, (-1.0, -4.95, .3), rot=(math.radians(75), 0, -.3), seg=14, rseg=7)          # half sunk in the weeds by the wall
    ty.done()
    # rusty wheelbarrow left in the yard, full of earth with weeds growing in it
    Mw = Matrix.Translation((1.3, -3.7, 0)) @ Matrix.Rotation(-.75, 4, 'Z')
    wb = G("CASA_barrow", M["barrow"], c, bevel=.03, seg=2)
    wb.prism([(-.38, .28), (.22, .28), (.62, .7), (-.6, .7)], .62, M=Mw)
    wb.done()
    wf = G("CASA_barrowFrame", M["rust"], c)
    for sy in (-1, 1):
        wf.tube(Mw @ Vector((-1.25, sy * .27, .58)), Mw @ Vector((.55, sy * .14, .2)), .026, verts=6)
        wf.tube(Mw @ Vector((-.32, sy * .24, .33)), Mw @ Vector((-.42, sy * .26, 0)), .022, verts=5)
    wf.tube(Mw @ Vector((.55, -.14, .17)), Mw @ Vector((.55, .14, .17)), .02, verts=5)
    wf.done()
    ww = G("CASA_barrowWheel", M["tire"], c)
    ww.torus(.15, .055, (0, 0, 0), M=Mw @ Matrix.Translation((.55, 0, .2)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), seg=14, rseg=6)
    ww.done()
    dm = G("CASA_barrowEarth", M["dirt"], c)
    dm.ball(.5, (0, 0, 0), scale=(1.1, .58, .2), sub=2, M=Mw @ Matrix.Translation((0, 0, .66)))
    dm.done()
    gw = G("CASA_barrowWeeds", M["grass"], c, smooth=False)
    gw.blades(Mw @ Vector((-.1, 0, .7)), n=7, h=.45, w=.06, seed=901)
    gw.blades(Mw @ Vector((.3, .1, .7)), n=5, h=.3, w=.05, seed=902)
    gw.done()
    # pile of bricks (neat-ish stack + loose ones)
    br = G("CASA_bricks", M["brick"], c, smooth=False)
    for lay in range(4):
        for k in range(3 if lay < 3 else 2):
            if lay % 2 == 0: br.box((.24, .115, .075), (2.95 + k * .25, -4.35, .04 + lay * .08), rot=(0, 0, rnd.uniform(-.06, .06)))
            else: br.box((.115, .24, .075), (2.9 + k * .27, -4.35, .04 + lay * .08), rot=(0, 0, rnd.uniform(-.06, .06)))
    for k in range(5):
        br.box((.24, .115, .075), (2.8 + rnd.uniform(-.3, .6), -3.95 + rnd.uniform(-.25, .2), .04), rot=(0, rnd.uniform(-.3, .3), rnd.uniform(0, 3)))
    br.done()
    # crates by the porch
    cr = G("CASA_crates", M["wood"], c, bevel=.008, seg=1)
    for (x, y, z, a) in ((-4.25, -2.75, 0, .25), (-4.2, -2.72, .3, -.2), (-4.2, -2.12, 0, 1.35)):
        Mc = Matrix.Translation((x, y, z)) @ Matrix.Rotation(a, 4, 'Z')
        for zz in (.06, .2):
            for sy in (-1, 1): cr.box((.56, .025, .1), (0, sy * .19, zz), M=Mc)
            for sx in (-1, 1): cr.box((.025, .36, .1), (sx * .27, 0, zz), M=Mc)
        for sx in (-1, 1):
            for sy in (-1, 1): cr.box((.04, .04, .29), (sx * .26, sy * .18, .145), M=Mc)
        cr.box((.5, .34, .02), (0, 0, .015), M=Mc)
    # spare roof tiles stacked under the right window
    st = G("CASA_tileStack", M["tiles"], c, bevel=.03, seg=1)
    for i in range(6):
        st.box((.6, .5, .07), (3.1 + rnd.uniform(-.03, .03), -2.2, .04 + i * .075), rot=(0, 0, .3 + rnd.uniform(-.08, .08)))
    st.box((.6, .5, .07), (2.65, -2.55, .15), rot=(.05, -.4, -.2))
    st.box((.3, .5, .07), (2.45, -2.85, .04), rot=(0, 0, .8))          # broken half
    st.done()
    # planks leaning on the east wall + the fallen shutter in the grass
    pl = G("CASA_planks", M["wood"], c, bevel=.012, seg=1)
    for k in range(4):
        pl.box((.05, .2, 2.2), (HX1 + .35 + k * .05, 1.15 + k * .23, 1.02), rot=(0, -.32 + k * .02, 0))
    for k in range(3):
        pl.box((1.6, .18, .05), (-.3 + k * .05, -4.1 + k * .2, .03 + k * .05), rot=(0, 0, .2 + k * .1))
    pl.done()
    sh = G("CASA_fallenShutter", M["teal"], c, bevel=.012, seg=1)
    Ms = Matrix.Translation((4.2, .35, .05)) @ Matrix.Rotation(.4, 4, 'Z') @ Matrix.Rotation(.06, 4, 'X')
    sh.box((.62, 1.25, .06), (0, 0, 0), M=Ms)
    for j in range(5): sh.box((.5, .07, .05), (0, -.5 + j * .25, .04), rot=(.35, 0, 0), M=Ms)
    sh.done()
    # paint buckets (one tipped over, a dried teal drip)
    bk = G("CASA_buckets", M["bucket"], c, bevel=.01, seg=1)
    bk.cyl(.16, .34, (.75, -3.4, .17), verts=14, r2=.18)
    bk.cyl(.15, .32, (.35, -3.55, .15), rot=(math.pi / 2 - .1, 0, 1.0), verts=14, r2=.17)
    bk.done()
    dr = G("CASA_paintSpill", M["teal"], c)
    dr.cyl(.32, .015, (.05, -3.85, .008), verts=12)
    dr.done()
    # back yard: an old blue water tank lying in the grass, some boards
    wt = G("CASA_waterTank", M["tank"], c, bevel=.03, seg=2)
    wt.cyl(.5, .95, (1.55, 4.9, .52), rot=(0, math.pi / 2 - .05, .2), verts=16, r2=.6)
    wt.done()


def build_pad(c):
    """Invisible in the game (Ruin() hides *_pad): only sets the model's bounds/scale and orientation in the lot."""
    p = G("CASA_pad", M["pad"], c)
    # 20 cm thick below the ground: Ruin() sets the model's lowest point 2 cm above the holder (world y .04) while the
    # lot's dirt plane is drawn at y .222, so without this the bottom ~18 cm of the ruin sat under the dirt.
    p.box((PAD_W, PAD_D, .2), (0, 0, -.1))
    o = p.done(); o.hide_render = True
    return o


# ------------------------------------------------------------------ assembly
CASA = "V3 Casa"


def build_casa(part="all"):
    """part: 'all' or one of 'house', 'roof', 'yard' (each fits well inside an MCP call)."""
    c = col(CASA)
    if part in ("all", "house"):
        for o in list(c.objects): bpy.data.objects.remove(o)
        for m in list(bpy.data.meshes):
            if m.users == 0: bpy.data.meshes.remove(m)
    mats()
    if part in ("all", "house"):
        build_pad(c); build_walls(c); build_trims(c); build_openings(c)
    if part in ("all", "roof"):
        build_roof(c); build_tarp(c); build_chimney(c); build_gutter(c); build_porch(c)
    if part in ("all", "yard"):
        build_front_wall(c); build_fences(c); build_path(c); build_plants(c); build_ivy(c); build_tree(c); build_props(c)
    return stats(c)


def stats(c=None):
    c = c or bpy.data.collections[CASA]
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    tris = 0; lo = Vector((1e9,) * 3); hi = -lo; heavy = []
    for o in c.objects:
        if o.type != 'MESH': continue
        me = o.evaluated_get(dg).data
        n = sum(len(p.vertices) - 2 for p in me.polygons); tris += n; heavy.append((n, o.name))
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    heavy.sort(reverse=True)
    return {"objects": len(c.objects), "tris": tris, "lo": [round(x, 2) for x in lo], "hi": [round(x, 2) for x in hi], "heavy": heavy[:12]}


def render_views(prefix="casa_v4", views=("iso",), cname=CASA):
    show_only(cname)
    out = []
    for v in views:
        if v == "iso": camera((0, -.1, 2.2), 17.2, GAME_DIR)
        elif v == "front": camera((0, -.3, 1.9), 13.5, Vector((.18, -1, .42)))
        elif v == "back": camera((0, .3, 1.9), 13.5, Vector((-.35, 1, .5)))
        elif v == "close": camera((.5, -2.2, 2.2), 8.5, GAME_DIR)
        out.append(render(f"{prefix}_{v}"))
    return out


# ================================================================== export: joined copies -> one UV atlas -> baked colour -> FBX
EXPORT_GROUPS = [
    ("CASA_pad", ("CASA_pad",)),
    ("CASA_house", ("CASA_walls", "CASA_gables", "CASA_inside", "CASA_quoins", "CASA_plinth", "CASA_cornice", "CASA_F", "CASA_E",
                    "CASA_B", "CASA_W", "CASA_chimney", "CASA_gutter", "CASA_ivy", "CASA_planks")),
    ("CASA_roof", ("CASA_roofDeck", "CASA_battens", "CASA_holeDark", "CASA_tiles", "CASA_ridge", "CASA_fascia", "CASA_tarp")),
    ("CASA_porch", ("CASA_porch", "CASA_chair", "CASA_pot")),
    ("CASA_boundary", ("CASA_lowWall", "CASA_finials", "CASA_wallRubble", "CASA_wallChunks", "CASA_gate", "CASA_fence")),
    ("CASA_garden", ("CASA_tree", "CASA_bush", "CASA_path", "CASA_lawn", "CASA_grass", "CASA_weeds", "CASA_turf", "CASA_bushes", "CASA_tree", "CASA_oranges")),
    ("CASA_junk", ("CASA_tyres", "CASA_barrow", "CASA_bricks", "CASA_crates", "CASA_tileStack", "CASA_fallenShutter", "CASA_buckets",
                   "CASA_paintSpill", "CASA_waterTank", "CASA_dirtSpill")),
]
NAME = "Lot_Casa"


def _group_of(name):
    best = None
    for g, prefixes in EXPORT_GROUPS:
        for p in prefixes:
            if name.startswith(p) and (best is None or len(p) > best[1]):
                best = (g, len(p))
    return best[0] if best else "CASA_junk"


def _apply(o):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    o.modifiers.clear(); old = o.data; o.data = me
    if old.users == 0: bpy.data.meshes.remove(old)


# Small parts in (nearly) flat colours share one "swatch" square each in a reserved row of the atlas instead of
# hundreds of tiny islands (each island costs its own margins): this frees most of the atlas for the walls.
SWATCH = ["V3_Picket", "V3_Glass", "V3_Dark", "V3_Tire", "V3_Rope", "V3_Orange", "V3_Flower", "V3_Gate", "V3_RustMetal",
          "V3_Brick", "V3_FoliageCore", "V3_Grass", "V3_GrassDry", "V3_Ivy", "V3_Leaf", "V3_Fruit", "V3_Concrete",
          "V3_StepStone", "V3_DirtMound", "V3_Bucket", "V3_Tank", "V3_Barrow", "V3_Ridge"]
SWATCH_CELL = .05                      # swatch squares in the band right of the city-tree square
RESERVED = TREE_BAND + .004


def _mat0(o):
    m = o.data.materials[0] if o.data.materials else None
    return m.name.split(".")[0] if m else ""


def swatch_uvs(o, slot):
    """Every face of `o` mapped onto the same square (its material's swatch): u across the face, v up the face
    (so a dark-foot / light-tip gradient survives), each face normalised to its own bounds."""
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    cols = int((1 - TREE_BAND - .006) / SWATCH_CELL); w = SWATCH_CELL; ins = .16
    x0 = TREE_BAND + .006 + (slot % cols) * w; y0 = 1 - (slot // cols + 1) * w
    for p in me.polygons:
        nrm = p.normal
        if abs(nrm.z) > .7: ax, ay = Vector((1, 0, 0)), Vector((0, 1, 0))
        else:
            ax = Vector((0, 0, 1)).cross(nrm).normalized(); ay = Vector((0, 0, 1))
        pts = [(me.vertices[me.loops[li].vertex_index].co.dot(ax), me.vertices[me.loops[li].vertex_index].co.dot(ay)) for li in p.loop_indices]
        xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
        dx = max(xs) - min(xs) or 1; dy = max(ys) - min(ys) or 1
        for li, (a, b) in zip(p.loop_indices, pts):
            su = (a - min(xs)) / dx; sv = (b - min(ys)) / dy
            uv[li].uv = (x0 + (ins + su * (1 - 2 * ins)) * w, y0 + (ins + sv * (1 - 2 * ins)) * w)


def make_export(src=CASA, name=NAME):
    """Copies of every part with modifiers applied, cut flat at the ground. Painted parts get one smart-UV atlas
    (texel weights per material), leaves and flat-colour bits get reserved template slots, then everything is
    joined into a few named meshes."""
    d = col(name + " Export")
    for o in list(d.objects): bpy.data.objects.remove(o)
    show_only(src, name + " Export")
    packed, reserved = {}, {}
    for o in bpy.data.collections[src].objects:
        if o.type != 'MESH': continue
        n = o.copy(); n.data = o.data.copy(); n.name = "tmp_" + o.name; d.objects.link(n)
        n.hide_render = False
        _apply(n)
        n.data.transform(n.matrix_world); n.matrix_world = Matrix.Identity(4)
        if not o.name.endswith("_pad"):
            bm = bmesh.new(); bm.from_mesh(n.data)
            if min((v.co.z for v in bm.verts), default=0) < -.004:
                bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, -.004), plane_no=(0, 0, 1), clear_inner=True)
            bm.to_mesh(n.data); bm.free()
        g = _group_of(o.name); m0 = _mat0(n)
        (reserved if (m0 == "V3_CityTree" or m0 in SWATCH) else packed).setdefault(g, []).append(n)

    def join(objs, nm):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = nm; j.data.name = nm
        return j
    pk = [join(objs, "X_" + g) for g, objs in packed.items()]
    bpy.ops.object.select_all(action='DESELECT')
    for o in pk: o.select_set(True)
    bpy.context.view_layer.objects.active = pk[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in pk: texel_weights(o)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(margin=0.0035, rotate=True, scale=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in pk:
        for l in o.data.uv_layers.active.data: l.uv = (l.uv[0], l.uv[1] * (1 - RESERVED))
    # reserved parts: leaves into their shade slots, the rest into their material's swatch
    out = {o.name[2:]: o for o in pk}
    for g, objs in reserved.items():
        for o in objs:
            if _mat0(o) == "V3_CityTree":
                o.data.uv_layers.active = o.data.uv_layers["UVMap"]       # already in the tree band
            else:
                swatch_uvs(o, SWATCH.index(_mat0(o)))
        objs = ([out[g]] if g in out else []) + objs
        out[g] = join(objs, "X_" + g)
        if "UVMap" in out[g].data.uv_layers: out[g].data.uv_layers.active = out[g].data.uv_layers["UVMap"]
    out = list(out.values())
    for o in out:
        for nm in ("leaf_u", "leaf_v"):
            if o.data.attributes.get(nm): o.data.attributes.remove(o.data.attributes[nm])
        if o.name.endswith("_pad"): o.hide_render = True    # hidden in the game too
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in out)
    return {"objects": [o.name for o in out], "tris": tris}


# texture space per material: the painted walls / roof get more pixels, flat colours and hidden faces almost none
TEXEL = {"V3_Pad": .02, "V3_Dark": .12, "V3_Deck": .5, "V3_Glass": .45, "V3_Tire": .5, "V3_Grass": .5, "V3_GrassDry": .5,
         "V3_Leaf": .6, "V3_Ivy": .5, "V3_TreeLeaf": .6, "V3_Foliage": .01, "V3_FoliageCore": .15, "V3_Lawn": .45, "V3_Picket": .6, "V3_Orange": .6, "V3_Flower": 1.2, "V3_Rope": .6, "V3_RustMetal": .9,
         "V3_CasaWall": 2.2, "V3_CasaGable": 1.8, "V3_LowWall": 2.6, "V3_Tiles": .8, "V3_Tarp": 1.1, "V3_Chimney": 1.3,
         "V3_TealWood": 1.15, "V3_Stone": 1.0}


def texel_weights(o):
    """Scales each UV island (smart-project keeps islands per face group) by its material's TEXEL weight."""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    names = [m.name.split(".")[0] if m else "" for m in me.materials]
    seen = set()
    for f in bm.faces:
        if f.index in seen: continue
        # flood the UV island of f (faces sharing UV-connected edges)
        isl = []; stack = [f]; seen.add(f.index)
        while stack:
            g = stack.pop(); isl.append(g)
            for l in g.loops:
                e = l.edge
                for lf in e.link_faces:
                    if lf.index in seen: continue
                    # same island when the shared edge has the same UVs on both sides
                    a = [x for x in g.loops if x.edge == e][0]; b = [x for x in lf.loops if x.edge == e]
                    if not b: continue
                    b = b[0]
                    if (a[uv].uv - b.link_loop_next[uv].uv).length < 1e-5 and (a.link_loop_next[uv].uv - b[uv].uv).length < 1e-5:
                        seen.add(lf.index); stack.append(lf)
        mname = names[f.material_index] if f.material_index < len(names) else ""
        k = TEXEL.get(mname, 1.0)
        cen3 = sum((g.calc_center_median() for g in isl), Vector()) / len(isl)
        nrm = sum((g.normal for g in isl), Vector())
        inside = (HX0 + WT - .03 < cen3.x < HX1 - WT + .03) and (HY0 + WT - .03 < cen3.y < HY1 - WT + .03)
        if mname in ("V3_CasaWall", "V3_CasaGable", "V3_Plinth", "V3_Stone") and inside:
            k = .08                                   # inner faces of the walls: never seen
        elif mname in ("V3_Tiles", "V3_Ridge") and nrm.y > .25 * nrm.length:
            k *= .55                                  # back slope: away from the game camera
        elif mname == "V3_LowWall" and (nrm.y > .5 * nrm.length or nrm.z > .5 * nrm.length):
            k = .5                                    # inner side / top under the cap of the front wall
        if abs(k - 1) < 1e-3: continue
        ls = [l for g in isl for l in g.loops]
        cen = sum((l[uv].uv for l in ls), Vector((0, 0))) / len(ls)
        for l in ls: l[uv].uv = cen + (l[uv].uv - cen) * k
    bm.to_mesh(me); bm.free()


def bake(name=NAME, size=2048, part=None, parts=1, samples=32):
    """Bakes the diffuse colour (painted AO included) of the export copies into <EXPORT>/<name>_BaseColor.png.
    Call with part=0..parts-1 to keep each MCP call short (the image is cleared on part 0, saved on the last)."""
    sc = bpy.context.scene
    allobjs = sorted(bpy.data.collections[name + " Export"].objects, key=lambda o: o.name)
    bakeable = [o for o in allobjs if not o.hide_render]     # the hidden _pad keeps an unbaked corner of the atlas
    objs = bakeable if part is None else bakeable[part::parts]
    img_name = name + "_BaseColor"
    first = part in (None, 0)
    if first:
        for im in list(bpy.data.images):
            if im.name.startswith(img_name): bpy.data.images.remove(im)
        img = bpy.data.images.new(img_name, size, size, alpha=True)
        img.generated_color = (0, 0, 0, 0)
    else:
        img = bpy.data.images[img_name]
    added = []
    for m in {m for o in objs for m in o.data.materials if m}:
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; m.node_tree.nodes.active = n; added.append((m, n))
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples
    try:
        sc.cycles.device = 'GPU'
    except Exception:
        pass
    b = sc.render.bake
    b.use_pass_direct = False; b.use_pass_indirect = False; b.use_pass_color = True; b.use_clear = first
    b.margin = 16; b.margin_type = 'EXTEND'
    b.target = 'IMAGE_TEXTURES'
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type='DIFFUSE')
    for m, n in added: m.node_tree.nodes.remove(n)
    sc.render.engine = 'BLENDER_EEVEE'
    if part is not None and part < parts - 1:
        return None
    # pixels no island covers: the atlas' mean colour (mipmaps of thin islands never fetch black on the phone)
    import numpy as np
    px = np.empty(size * size * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(-1, 4)
    empty = px[:, 3] < .5
    if (~empty).any():
        px[empty, :3] = px[~empty, :3].mean(axis=0)
    px[:, 3] = 1.0
    img.pixels.foreach_set(px.ravel()); img.update()
    os.makedirs(EXPORT, exist_ok=True)
    img.filepath_raw = os.path.join(EXPORT, img_name + ".png"); img.file_format = 'PNG'; img.save()
    am = bpy.data.materials.get(name + "_Mat") or bpy.data.materials.new(name + "_Mat")
    am.use_nodes = True; nt = am.node_tree
    for n in list(nt.nodes):
        if n.bl_idname == "ShaderNodeTexImage": nt.nodes.remove(n)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    bs = nt.nodes["Principled BSDF"]
    nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"]); bs.inputs["Roughness"].default_value = .85
    for o in allobjs:
        o.data.materials.clear(); o.data.materials.append(am)
    return img.filepath_raw


def export(name=NAME):
    """FBX like the current Resources/CheckoutLots ones (export_unity: turned 180, -Z fwd, Y up, scale 1)."""
    objs = list(bpy.data.collections[name + " Export"].objects)
    show_only(name + " Export")
    for o in objs:   # the city tree's own UVs were only needed to bake its texture into the atlas
        if "TreeUV" in o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers["TreeUV"])
    clash = {}
    for o in objs:
        final = o.name[2:]
        other = bpy.data.objects.get(final)
        if other and other not in objs:
            other.name = final + "~src"; clash[final] = other
        o.name = final
    try:
        path = cp.export_unity(objs, name, folder=EXPORT)
    finally:
        for o in objs: o.name = "X_" + o.name
        for final, other in clash.items(): other.name = final
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co; lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return {"fbx": path, "kb": os.path.getsize(path) // 1024, "dims": [round(x, 2) for x in (hi - lo)],
            "tris": sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs), "objects": len(objs)}


def vs_city(name="casa_v4_vs_city"):
    """The new Casa between two of the city's own houses (MapModels, sized as CheckoutCityModelsBuilder places them)."""
    c = bpy.data.collections.get("REF City")
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o)
    info = [reference("StylizedHouse", (-11.0, 0.8), fit=(8, 7.8, 8)), reference("CuteHouse", (11.5, 0.8), fit=(8, 7, 9)),
            reference("StylizedTree", (7.6, -5.2), fit=(3.65, 4.6, 3.8)), reference("StylizedTree", (-7.4, -5.6), rot_z=.8, fit=(3.83, 4.6, 3.8))]
    stage()
    show_only(NAME + " Export", "REF City")
    camera((0, -.8, 2.0), 35.0, GAME_DIR, res=(1800, 1000))
    render(name)
    return info
