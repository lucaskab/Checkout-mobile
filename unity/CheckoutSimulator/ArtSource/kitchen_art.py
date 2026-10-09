"""
kitchen_art.py  --  Checkout - Supermercado Simulator
Art for the hand-made production games (CheckoutDesktopHUD.Kitchen.cs): the work bench of each sector and the
things the player handles on it (dough, molds, cuts of meat, fish…), each in every state the game shows.

Same look as the other mini-game art (Game/*.png): soft studio light, painted materials, seen from the front and
above. Built from the helpers of lane_art.py (materials with noise/planks/bricks/tiles, bevelled boxes...).

Usage in Blender:
  exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\kitchen_art.py", encoding="utf-8").read())
  render_sector("padaria")     # props -> ArtSource/Review/kitchen/<name>.png, bench -> kt_bench_<sector>.png
"""
import bpy, bmesh, math, os, random
from mathutils import Vector

exec(open(r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\lane_art.py", encoding="utf-8").read())

KSCENE = "KitchenArt"
KOUT = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\kitchen"
TILT = math.radians(58)          # camera angle from straight down (props and benches share it)

PAL.update({
    "dough": (0.95, 0.86, 0.68), "dough_d": (0.9, 0.78, 0.58), "crust": (0.78, 0.45, 0.16), "crust_d": (0.55, 0.28, 0.08),
    "flour": (0.98, 0.97, 0.94), "ceramic": (0.96, 0.94, 0.9), "stripe": (0.25, 0.5, 0.72), "steel_k": (0.78, 0.8, 0.82),
    "choco": (0.32, 0.17, 0.09), "batter": (0.48, 0.28, 0.14), "cherry": (0.8, 0.08, 0.12), "glass_k": (0.75, 0.88, 0.95),
    "tile_w": (0.95, 0.95, 0.92), "wood_t": (0.72, 0.5, 0.3),
})


def kscene():
    sc = bpy.data.scenes.get(KSCENE) or bpy.data.scenes.new(KSCENE)
    bpy.context.window.scene = sc
    r = sc.render
    r.engine = "CYCLES"
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    try:
        sc.cycles.device = "GPU"
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = 0.0
    w = bpy.data.worlds.get("KitchenArt_World") or bpy.data.worlds.new("KitchenArt_World")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 0.97, 0.92, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.32
    sc.world = w
    if "KitchenArt_Cam" not in bpy.data.objects:
        cam = bpy.data.objects.new("KitchenArt_Cam", bpy.data.cameras.new("KitchenArt_Cam"))
        sc.collection.objects.link(cam)
        sun = bpy.data.objects.new("KitchenArt_Sun", bpy.data.lights.new("KitchenArt_Sun", "SUN"))
        sc.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(35), math.radians(18), math.radians(-25))
        fill = bpy.data.objects.new("KitchenArt_Fill", bpy.data.lights.new("KitchenArt_Fill", "AREA"))
        sc.collection.objects.link(fill)
        fill.location = (0, -6, 6)
        fill.rotation_euler = (math.radians(45), 0, 0)
    bpy.data.lights["KitchenArt_Sun"].energy = 2.6
    bpy.data.lights["KitchenArt_Sun"].angle = math.radians(12)
    bpy.data.lights["KitchenArt_Fill"].energy = 60
    bpy.data.lights["KitchenArt_Fill"].size = 6
    sc.camera = bpy.data.objects["KitchenArt_Cam"]
    return sc


def kcoll(name):
    sc = kscene()
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for other in bpy.data.collections:
        if other.name.startswith("KitchenArt_"):
            other.hide_render = other is not c
            other.hide_viewport = other is not c
    CUR["c"] = c
    return c


def aim(size, target=(0, 0, 0), res=(512, 512)):
    """Orthographic camera from the front and above, framing `size` world units."""
    sc = kscene()
    cam = bpy.data.objects["KitchenArt_Cam"]
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size
    d = 20
    t = Vector(target)
    cam.location = t + Vector((0, -math.sin(TILT) * d, math.cos(TILT) * d))
    cam.rotation_euler = (TILT, 0, 0)
    cam.data.clip_end = 100
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = True


# ---------------------------------------------------------------- organic shapes
def meta(elements, m, res=0.04, name="meta"):
    """A soft shape from metaball spheres/ellipsoids [(loc, radius, (sx, sy, sz))], turned into a mesh."""
    mb = bpy.data.metaballs.new(name)
    mb.resolution = res
    mb.render_resolution = res
    o = bpy.data.objects.new(name, mb)
    CUR["c"].objects.link(o)
    for loc, r, s in elements:
        e = mb.elements.new()
        e.type = "ELLIPSOID"
        e.co = loc
        e.radius = r
        e.size_x, e.size_y, e.size_z = s
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o, do_unlink=True)
    out = bpy.data.objects.new(name, me)
    _link(out, m)
    return out


def lump(parts, m, voxel=0.03, name="lump"):
    """A soft hand-made shape: spheres [(loc, radius, (sx, sy, sz))] fused into one surface (voxel remesh)."""
    objs = []
    for loc, r, sc in parts:
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=r)
        bmesh.ops.scale(bm, vec=Vector(sc), verts=bm.verts)
        bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        CUR["c"].objects.link(o)
        objs.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    rm = o.modifiers.new("Fuse", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    bpy.ops.object.modifier_apply(modifier=rm.name)
    sm = o.modifiers.new("Soft", "SMOOTH")
    sm.iterations = 6
    o.data.materials.append(m if not isinstance(m, str) else mat(m))
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def bumpy(o, strength=0.03, size=0.15, seed=1):
    """Hand-made lumps on a surface (dough, meat, curd)."""
    tex = bpy.data.textures.new("bump%d" % seed, "CLOUDS")
    tex.noise_scale = size
    d = o.modifiers.new("Lumps", "DISPLACE")
    d.texture = tex
    d.strength = strength
    d.texture_coords = "OBJECT"
    sm = o.modifiers.new("Smooth", "SUBSURF")
    sm.levels = 1
    sm.render_levels = 1
    return o


def dough_mat(key, color, flour=0.0, gloss=0.55):
    """Dough/bread: base colour with a dusting of flour on top (by facing up)."""
    name = "LA_" + key
    if name in MATS:
        return MATS[name]
    m = mat(key, color, rough=gloss, noise=0.1)
    if flour > 0:
        nt = m.node_tree
        b = [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"][0]
        src = b.inputs["Base Color"].links[0].from_socket
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], sep.inputs[0])
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 18
        mix_f = nt.nodes.new("ShaderNodeMath")
        mix_f.operation = "MULTIPLY"
        nt.links.new(sep.outputs["Z"], mix_f.inputs[0])
        nt.links.new(noise.outputs["Fac"], mix_f.inputs[1])
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value = 0.45 - flour * 0.2
        ramp.inputs["From Max"].default_value = 0.7
        nt.links.new(mix_f.outputs[0], ramp.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMixRGB")
        nt.links.new(ramp.outputs["Result"], mix.inputs["Fac"])
        nt.links.new(src, mix.inputs["Color1"])
        mix.inputs["Color2"].default_value = (*PAL["flour"], 1)
        nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
    return m


def crust_mat(key, light, dark):
    """Baked crust: darker where the surface faces the oven top, paler in the creases."""
    name = "LA_" + key
    if name in MATS:
        return MATS[name]
    m = mat(key, light, rough=0.45, noise=0.15)
    nt = m.node_tree
    b = [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"][0]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    nt.links.new(sep.outputs["Z"], add.inputs[0])
    add.inputs[1].default_value = 0.7
    nt.links.new(noise.outputs["Fac"], add.inputs[2])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*light, 1)
    ramp.color_ramp.elements[1].color = (*dark, 1)
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[1].position = 1.05
    nt.links.new(add.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


def bowl(r=1.0, h=0.55, m_out="ceramic", inner=None):
    """A ceramic mixing bowl with a blue band; `inner` fills it (dough, batter…)."""
    me = bpy.data.meshes.new("bowl")
    bm = bmesh.new()
    prof = [(0.45 * r, 0), (0.62 * r, 0.04 * h), (0.86 * r, 0.35 * h), (0.98 * r, 0.75 * h), (1.0 * r, h)]
    seg = 48
    rings = []
    for (rr, z) in prof:
        rings.append([bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)) for a in [i / seg * math.tau for i in range(seg)]])
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
    bm.faces.new(rings[0][::-1])
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("bowl", me)
    _link(o, m_out)
    s = o.modifiers.new("Wall", "SOLIDIFY")
    s.thickness = 0.06 * r
    sub = o.modifiers.new("Smooth", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 2
    torus(0.93 * r, 0.03 * r, (0, 0, 0.62 * h), "stripe")
    if inner:
        inner()
    return o


# ---------------------------------------------------------------- padaria
def dough_ball(state="rough"):
    if state == "rough":
        # Just mixed: a shaggy lump with dry flour on it.
        parts = [((0, 0, 0.22), 0.55, (1.1, 1.0, 0.6)), ((0.42, 0.12, 0.2), 0.3, (1, 1, 0.8)), ((-0.4, -0.18, 0.2), 0.3, (1, 1, 0.8)),
                 ((0.1, 0.42, 0.22), 0.26, (1, 1, 0.9)), ((-0.15, -0.45, 0.18), 0.22, (1, 1, 0.9)), ((0.25, -0.3, 0.32), 0.2, (1, 1, 1))]
        o = lump(parts, dough_mat("dough_rough", PAL["dough_d"], flour=0.9, gloss=0.8), voxel=0.025)
        bumpy(o, 0.06, 0.1, 3)
        rnd = random.Random(5)
        for i in range(14):
            a = rnd.uniform(0, math.tau)
            r = rnd.uniform(0.6, 0.9)
            sphere(rnd.uniform(0.03, 0.06), (math.cos(a) * r, math.sin(a) * r, 0.02), dough_mat("flourbits", PAL["flour"]), scale=(1, 1, 0.4))
        return o
    big = 0.62 if state == "smooth" else 0.78
    o = lump([((0, 0, big * 0.5), big, (1.05, 1.0, 0.62 if state == "smooth" else 0.72))],
             dough_mat("dough_" + state, PAL["dough"], flour=0.25, gloss=0.4), voxel=0.03)
    bumpy(o, 0.01, 0.35, 4)
    if state == "risen":
        rnd = random.Random(9)
        for i in range(9):
            a = rnd.uniform(0, math.tau)
            r = rnd.uniform(0.1, 0.5)
            sphere(0.035, (math.cos(a) * r, math.sin(a) * r * 0.9, big * 0.5 + big * 0.7 * 0.62 * math.sqrt(max(0, 1 - (r / big) ** 2)) + 0.02),
                   mat("bubble", (0.97, 0.9, 0.74), rough=0.25), scale=(1, 1, 0.4))
    return o


def baguette(state="raw", x=0.0, y=0.0, length=2.6):
    if state == "baked":
        m = crust_mat("crust", PAL["crust"], PAL["crust_d"])
    else:
        m = dough_mat("dough_bag", PAL["dough"], flour=0.6, gloss=0.6)
    o = lump([((x, y, 0.2), 0.5, (length / 1.0, 0.62, 0.42))], m, voxel=0.03, name="baguette")
    bumpy(o, 0.012 if state != "baked" else 0.025, 0.25, 7)
    if state in ("scored", "baked"):
        for k in range(4):
            cx = x + (k - 1.5) * length * 0.2
            if state == "scored":
                box((0.44, 0.035, 0.05), (cx, y, 0.385), mat("slit3", (0.22, 0.15, 0.09), rough=0.95), bevel=0.012, rot=(0, 0, math.radians(25)))
            else:
                # The "pestana": the cut opens and its lip bakes paler and crisp.
                lip = lump([((0, 0, 0.37), 0.2, (1.35, 0.3, 0.2))], crust_mat("ear3", (0.7, 0.42, 0.16), (0.5, 0.26, 0.08)), voxel=0.012, name="lip")
                lip.rotation_euler = (0, 0, math.radians(25))
                lip.location = (cx, y, 0)
                box((0.34, 0.05, 0.03), (cx + 0.02, y - 0.07, 0.38), mat("crumb2", (0.93, 0.78, 0.52), rough=0.9), bevel=0.012, rot=(0, 0, math.radians(25)))
    return o


def croissant(state="raw", x=0.0, y=0.0, s=1.0):
    m = crust_mat("crust_c", (0.93, 0.66, 0.3), (0.66, 0.36, 0.1)) if state == "baked" else dough_mat("dough_cr", (0.97, 0.89, 0.72), flour=0.15, gloss=0.4)
    parts = []
    n = 7
    for i in range(n):
        t = i / (n - 1)
        a = math.radians(205 - 230 * t)
        r = (0.12 + 0.24 * math.sin(t * math.pi)) * s
        parts.append(((x + math.cos(a) * 0.6 * s, y + math.sin(a) * 0.38 * s - 0.12 * s, r * 0.8), r, (0.75, 1.1, 0.85)))
    o = lump(parts, m, voxel=0.02, name="croissant")
    bumpy(o, 0.008, 0.3, 11)
    return o


def cake(state="baked"):
    if state == "batter":
        bowl(1.0, 0.55, inner=lambda: cyl(0.9, 0.05, (0, 0, 0.42), mat("batter", PAL["batter"], rough=0.25, noise=0.05), seg=48, bevel=0))
        return
    cyl(1.05, 0.06, (0, 0, 0.03), mat("plate", (0.95, 0.95, 0.95), rough=0.2), seg=64, bevel=0.02)
    body = cyl(0.85, 0.55, (0, 0, 0.33), crust_mat("cake", (0.45, 0.25, 0.12), (0.3, 0.15, 0.07)), seg=64, bevel=0.06)
    if state == "done":
        cyl(0.88, 0.1, (0, 0, 0.64), mat("ganache", PAL["choco"], rough=0.15, noise=0.05), seg=64, bevel=0.05)
        for i in range(10):
            a = i / 10 * math.tau
            meta([((math.cos(a) * 0.72, math.sin(a) * 0.72, 0.72), 0.1, (1, 1, 1.2))], mat("cream", (0.98, 0.95, 0.88), rough=0.35), res=0.02, name="cream")
            if i % 2 == 0:
                sphere(0.06, (math.cos(a) * 0.72, math.sin(a) * 0.72, 0.84), mat("cherry", PAL["cherry"], rough=0.15))
        rnd = random.Random(2)
        for i in range(40):
            a = rnd.uniform(0, math.tau)
            rr = rnd.uniform(0, 0.55)
            box((0.06, 0.015, 0.015), (math.cos(a) * rr, math.sin(a) * rr, 0.7), mat("spr%d" % (i % 4), [(0.95, 0.8, 0.2), (0.9, 0.35, 0.5), (0.3, 0.7, 0.9), (0.98, 0.98, 0.95)][i % 4]), bevel=0, rot=(0, 0, rnd.uniform(0, 3)))


def oven():
    box((3.2, 1.4, 2.0), (0, 0, 1.0), mat("oven", (0.72, 0.74, 0.76), rough=0.3, metal=0.7, noise=0.03), bevel=0.06)
    box((3.25, 1.45, 0.2), (0, 0, 2.05), mat("oven_top", (0.25, 0.25, 0.27), rough=0.4), bevel=0.04)
    # The glass door with the glow of the baking chamber.
    box((2.4, 0.06, 1.1), (0, -0.72, 0.95), "dark", bevel=0.05)
    box((2.2, 0.07, 0.92), (0, -0.74, 0.95), mat("ovenglow3", (0.95, 0.32, 0.06), rough=0.2, emit=0.55, noise=0.05), bevel=0.03)
    box((2.0, 0.1, 0.06), (0, -0.85, 1.6), mat("handle", (0.85, 0.85, 0.86), rough=0.2, metal=0.9, noise=0), bevel=0.02)
    for x in (-0.9, 0.9):
        box((0.06, 0.12, 0.08), (x, -0.8, 1.6), "dark", bevel=0.01)
    # Dials and the temperature display.
    for x in (-1.1, -0.75):
        cyl(0.11, 0.08, (x, -0.74, 1.82), "dark", seg=24, rot=(math.radians(90), 0, 0))
        box((0.02, 0.03, 0.08), (x, -0.79, 1.86), "white", bevel=0)
    box((0.6, 0.05, 0.2), (0.8, -0.73, 1.82), mat("display", (0.1, 0.12, 0.1), rough=0.3), bevel=0.02)
    text("220°", (0.8, -0.77, 1.82), 0.14, mat("digits", (1.0, 0.45, 0.1), emit=3, noise=0))
    for x in (-1.4, 1.4):
        cyl(0.07, 0.12, (x, -0.4, -0.04), "dark", seg=16)


def jug():
    glass = mat("glassk", PAL["glass_k"], rough=0.05, noise=0.02)
    for n in glass.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED" and "Transmission Weight" in n.inputs:
            n.inputs["Transmission Weight"].default_value = 0.9
    cyl(0.42, 1.0, (0, 0, 0.5), glass, seg=40, r2=0.36, bevel=0.03)
    cyl(0.38, 0.75, (0, 0, 0.4), mat("water", (0.55, 0.78, 0.95), rough=0.05, noise=0.02), seg=40, r2=0.33, bevel=0)
    for i in range(4):
        box((0.18, 0.18, 0.18), (0.12 * math.cos(i * 1.7), 0.1 * math.sin(i * 1.7), 0.72 + 0.03 * i), mat("ice", (0.88, 0.95, 1.0), rough=0.1), bevel=0.04, rot=(0.3 * i, 0.2, 0.4 * i))
    torus(0.22, 0.05, (0.48, 0, 0.6), glass, rot=(math.radians(90), 0, 0))


def jar(label_color, label="", lid=(0.85, 0.2, 0.15), fill=(0.95, 0.93, 0.88)):
    cyl(0.4, 0.8, (0, 0, 0.4), mat("jar_glass", PAL["glass_k"], rough=0.05, noise=0.02), seg=40, bevel=0.04)
    cyl(0.36, 0.6, (0, 0, 0.32), mat("jar_fill%d" % int(fill[0] * 100), fill, rough=0.8), seg=40, bevel=0)
    cyl(0.42, 0.16, (0, 0, 0.86), mat("lid%d" % int(lid[0] * 100), lid, rough=0.3), seg=40, bevel=0.04)
    cyl(0.405, 0.32, (0, 0, 0.42), mat("lab%d" % int(label_color[1] * 100), label_color, rough=0.6), seg=40, bevel=0)
    if label:
        t = text(label, (0, -0.41, 0.42), 0.14, "white", rot=(math.radians(90), 0, 0))


def yeast_pack():
    box((0.9, 0.12, 1.1), (0, 0, 0.55), mat("yeast", (0.95, 0.75, 0.15), rough=0.4), bevel=0.06)
    box((0.92, 0.13, 0.12), (0, 0, 1.05), mat("yeast_top", (0.85, 0.2, 0.15), rough=0.4), bevel=0.03)
    text("FERMENTO", (0, -0.08, 0.6), 0.12, mat("ink", (0.45, 0.18, 0.08), noise=0), rot=(math.radians(90), 0, 0))
    meta([((0, -0.1, 0.35), 0.18, (1.4, 0.6, 1))], mat("bread_logo", (0.85, 0.55, 0.25)), res=0.02)


def tray(w=3.0, d=1.6):
    box((w, d, 0.08), (0, 0, 0.04), mat("tray", (0.35, 0.33, 0.32), rough=0.35, metal=0.6, noise=0.04), bevel=0.04)
    box((w - 0.15, d - 0.15, 0.02), (0, 0, 0.085), mat("paper", (0.95, 0.92, 0.85), rough=0.9), bevel=0.01)


def bench_padaria():
    """Bakery bench: a wooden table top that fills the view, white tiles and a shelf of flour behind it (1600 x 900, opaque)."""
    box((18, 13, 0.4), (0, -2.0, -0.2), mat("bench_wood", (0.78, 0.55, 0.33), rough=0.55, pattern="planks", scale=0.55, noise=0.14, wavy=0.15), bevel=0.02)
    box((18, 0.3, 8), (0, 4.6, 3.8), mat("tiles_wall", PAL["tile_w"], rough=0.3, pattern="bricks", scale=1.2, noise=0.03, axis="xz"), bevel=0)
    box((18, 0.7, 0.14), (0, 4.15, 2.0), mat("shelf_w", (0.6, 0.4, 0.22), pattern="planks", scale=3), bevel=0.03)
    for i, x in enumerate((-7.2, -6.2, -5.2, 5.2, 6.2, 7.2)):
        jarc = [(0.95, 0.94, 0.9), (0.9, 0.75, 0.4), (0.6, 0.35, 0.2)][i % 3]
        cyl(0.38, 0.85, (x, 4.15, 2.5), mat("sjar", PAL["glass_k"], rough=0.05, noise=0.02), seg=24, bevel=0.03)
        cyl(0.33, 0.6, (x, 4.15, 2.4), mat("sjar%d" % i, jarc, rough=0.8), seg=24, bevel=0)
        cyl(0.4, 0.13, (x, 4.15, 2.98), mat("slid", (0.7, 0.45, 0.25)), seg=24)
    for x in (-2.4, 0, 2.4):
        lump([((x, 4.15, 2.75), 0.62, (1, 0.7, 1.25))], mat("sack", (0.92, 0.86, 0.72), rough=0.95), voxel=0.04, name="sack")
        text("TRIGO", (x, 3.68, 2.7), 0.26, mat("flourlogo", (0.75, 0.3, 0.2)), rot=(math.radians(90), 0, 0))
    # Rolling pin and a few dustings of flour on the table.
    cyl(0.18, 2.6, (-6.4, -3.2, 0.18), mat("pin", (0.82, 0.62, 0.4), pattern="planks", scale=8), seg=24, rot=(0, math.radians(90), math.radians(18)))
    rnd = random.Random(8)
    for c in range(3):
        cx, cy = rnd.uniform(-6, 6), rnd.uniform(-4, 2)
        for i in range(14):
            sphere(rnd.uniform(0.05, 0.12), (cx + rnd.gauss(0, 0.35), cy + rnd.gauss(0, 0.25), 0.0), mat("dust", PAL["flour"], rough=1), scale=(1, 1, 0.12))


def dough_sheet():
    """Dough rolled out into a sheet (croissants, laminated dough)."""
    o = box((2.6, 1.7, 0.16), (0, 0, 0.08), dough_mat("dough_sheet", PAL["dough"], flour=0.5, gloss=0.5), bevel=0.07)
    o.modifiers["Bevel"].segments = 5
    bumpy(o, 0.01, 0.4, 13)
    rnd = random.Random(3)
    for i in range(18):
        sphere(rnd.uniform(0.03, 0.07), (rnd.uniform(-1.1, 1.1), rnd.uniform(-0.7, 0.7), 0.17), dough_mat("flourbits", PAL["flour"]), scale=(1, 1, 0.3))
    return o


def blade():
    """The baker's lame: a wooden handle with a curved razor."""
    cyl(0.07, 0.9, (-0.35, 0, 0.07), mat("lame_wood", (0.62, 0.4, 0.22), pattern="planks", scale=20), seg=20, rot=(0, math.radians(90), 0))
    box((0.5, 0.12, 0.012), (0.32, 0, 0.07), mat("razor", (0.85, 0.87, 0.9), rough=0.15, metal=1.0, noise=0.02), bevel=0.005)
    box((0.12, 0.05, 0.03), (0.08, 0, 0.07), "dark", bevel=0.01)


def whisk():
    cyl(0.07, 0.8, (-0.55, 0, 0.1), mat("whisk_h", (0.85, 0.3, 0.2), rough=0.3), seg=20, rot=(0, math.radians(90), 0))
    wire = mat("wire", (0.85, 0.86, 0.88), rough=0.2, metal=1.0, noise=0.01)
    for k in range(5):
        a = k / 5 * math.pi
        bpy.ops.mesh.primitive_torus_add(major_radius=0.32, minor_radius=0.012, location=(0.1, 0, 0.1), rotation=(a, math.radians(90), 0), major_segments=40, minor_segments=6)
        o = bpy.context.active_object
        for c in o.users_collection:
            c.objects.unlink(o)
        o.scale = (1.0, 1.0, 1.6)
        _link(o, wire)


# ---------------------------------------------------------------- queijaria
STEEL = None


def steel():
    return mat("steel_k2", (0.8, 0.82, 0.85), rough=0.25, metal=0.85, noise=0.03)


def pot(fill="milk"):
    """The cheese vat: a steel pot with handles, full of milk, set curd or curd in whey."""
    # Open-topped vat: a tube with a bottom, given a wall thickness.
    me = bpy.data.meshes.new("vat")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=64, radius1=1.0, radius2=1.0, depth=1.0)
    bottom = [v for v in bm.verts if v.co.z < 0]
    bm.faces.new(sorted(bottom, key=lambda v: math.atan2(v.co.y, v.co.x)))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("vat", me)
    o.location = (0, 0, 0.5)
    _link(o, steel())
    sol = o.modifiers.new("Wall", "SOLIDIFY")
    sol.thickness = 0.05
    torus(1.0, 0.05, (0, 0, 1.0), steel())
    for x in (-1.08, 1.08):
        box((0.22, 0.12, 0.08), (x, 0, 0.82), steel(), bevel=0.03)
    if fill == "milk":
        cyl(0.95, 0.02, (0, 0, 0.92), mat("milk", (0.98, 0.97, 0.93), rough=0.15, noise=0.02), seg=64, bevel=0)
    elif fill == "gel":
        cyl(0.95, 0.03, (0, 0, 0.92), mat("curdgel", (0.96, 0.93, 0.8), rough=0.05, noise=0.06), seg=64, bevel=0)
        box((0.9, 0.025, 0.02), (0.05, 0.1, 0.94), mat("whey_line", (0.85, 0.86, 0.62), rough=0.1), bevel=0.005, rot=(0, 0, 0.3))
    elif fill == "curd":
        # Curd cut in cubes floating in the whey: a tiled top (pale cubes, greenish whey in the cuts).
        cyl(0.95, 0.02, (0, 0, 0.9), mat("whey", (0.88, 0.9, 0.66), rough=0.08, noise=0.04), seg=64, bevel=0)
        cyl(0.86, 0.05, (0, 0, 0.92), mat("curd_tiles2", (0.98, 0.95, 0.84), rough=0.5, noise=0.06, pattern="tiles", scale=1.5), seg=64, bevel=0.01)


def bottle(label, color, cap=(0.2, 0.2, 0.22), body=(0.92, 0.92, 0.9), small=False):
    k = 0.75 if small else 1.0
    cyl(0.3 * k, 0.8 * k, (0, 0, 0.4 * k), mat("btl%d" % int(body[0] * 100 + body[2] * 10), body, rough=0.25, noise=0.03), seg=32, bevel=0.06)
    cyl(0.14 * k, 0.2 * k, (0, 0, 0.88 * k), mat("btln", body, rough=0.25), seg=24, bevel=0.02)
    cyl(0.16 * k, 0.14 * k, (0, 0, 1.02 * k), mat("cap%d" % int(cap[0] * 100 + cap[1] * 10), cap, rough=0.35), seg=24, bevel=0.03)
    cyl(0.305 * k, 0.36 * k, (0, 0, 0.42 * k), mat("lbl%d" % int(color[0] * 100 + color[1] * 10 + color[2]), color, rough=0.5), seg=32, bevel=0)
    text(label, (0, -0.31 * k, 0.42 * k), 0.1 * k, "white", rot=(math.radians(90), 0, 0))


def ladle():
    cyl(0.04, 1.4, (-0.3, 0, 0.25), steel(), seg=12, rot=(0, math.radians(75), 0))
    o = sphere(0.32, (0.45, 0, 0.18), steel(), scale=(1, 1, 0.55))


def lira():
    """The curd harp: a steel frame strung with wires."""
    box((0.08, 0.08, 1.5), (-0.6, 0, 0.75), steel(), bevel=0.02)
    box((0.08, 0.08, 1.5), (0.6, 0, 0.75), steel(), bevel=0.02)
    box((1.28, 0.08, 0.08), (0, 0, 1.5), steel(), bevel=0.02)
    box((1.28, 0.08, 0.08), (0, 0, 0.0), steel(), bevel=0.02)
    for i in range(1, 8):
        cyl(0.008, 1.45, (-0.6 + i * 0.15, 0, 0.75), steel(), seg=6, bevel=0)
    cyl(0.05, 0.9, (0, 0, 1.95), mat("lira_h", (0.25, 0.25, 0.27), rough=0.4), seg=16, bevel=0.02)


def molds(full=False, cheese=False):
    """A draining tray with four round cheese molds (empty, full of curd or with the turned-out cheeses)."""
    box((2.6, 1.4, 0.08), (0, 0, 0.04), steel(), bevel=0.03)
    for i, (x, y) in enumerate(((-0.62, 0.32), (0.62, 0.32), (-0.62, -0.32), (0.62, -0.32))):
        if cheese:
            cyl(0.3, 0.32, (x, y, 0.24), mat("minas", (0.98, 0.96, 0.9), rough=0.45, noise=0.05), seg=40, bevel=0.06)
            continue
        cyl(0.32, 0.42, (x, y, 0.29), mat("mold", (0.95, 0.95, 0.95), rough=0.35, noise=0.02), seg=40, bevel=0.02)
        for k in range(10):
            a = k / 10 * math.tau
            for z in (0.18, 0.3, 0.42):
                cyl(0.025, 0.02, (x + math.cos(a) * 0.32, y + math.sin(a) * 0.32, z), "dark", seg=8, bevel=0, rot=(math.radians(90), 0, a + math.radians(90)))
        if full:
            o = lump([((x, y, 0.48), 0.3, (1, 1, 0.35))], mat("curdtop", (0.98, 0.95, 0.84), rough=0.5), voxel=0.02)
            bumpy(o, 0.02, 0.06, 5)


def curd_scoop():
    o = lump([((0, 0, 0.2), 0.32, (1, 1, 0.7)), ((0.15, 0.1, 0.32), 0.18, (1, 1, 1)), ((-0.12, -0.08, 0.3), 0.16, (1, 1, 1))], mat("curd", (0.98, 0.95, 0.84), rough=0.5), voxel=0.02)
    bumpy(o, 0.03, 0.06, 6)


def wheel(kind="fresh"):
    if kind == "brie":
        o = cyl(0.9, 0.36, (0, 0, 0.18), mat("brie_rind", (0.97, 0.96, 0.9), rough=0.95, noise=0.12), seg=64, bevel=0.08)
        bumpy(o, 0.015, 0.05, 8)
    else:
        cyl(0.85, 0.5, (0, 0, 0.25), mat("minas", (0.98, 0.96, 0.9), rough=0.45, noise=0.05), seg=64, bevel=0.08)
        for k in range(24):
            a = k / 24 * math.tau
            box((0.03, 0.02, 0.4), (math.cos(a) * 0.86, math.sin(a) * 0.86, 0.25), mat("mold_mark", (0.93, 0.9, 0.82)), bevel=0, rot=(0, 0, a))


def cheese_wedge():
    me = bpy.data.meshes.new("wedge")
    bm = bmesh.new()
    pts = [(0, 0), (0.9, -0.3), (0.9, 0.3)]
    vs = [bm.verts.new((x, y, 0)) for x, y in pts] + [bm.verts.new((x, y, 0.36)) for x, y in pts]
    bm.faces.new(vs[0:3][::-1])
    bm.faces.new(vs[3:6])
    for i in range(3):
        j = (i + 1) % 3
        bm.faces.new((vs[i], vs[j], vs[j + 3], vs[i + 3]))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("wedge", me)
    o.location = (-0.45, 0, 0)
    _link(o, mat("brie_in", (0.98, 0.9, 0.62), rough=0.3, noise=0.04), bevel=0.03)
    box((0.04, 0.62, 0.38), (0.47, 0, 0.18), mat("brie_rind", (0.97, 0.96, 0.9), rough=0.95, noise=0.12), bevel=0.02)


def board(full=False):
    box((2.4, 1.4, 0.12), (0, 0, 0.06), mat("board", (0.7, 0.48, 0.28), rough=0.6, pattern="planks", scale=4, wavy=0.3), bevel=0.05)
    if full:
        for x, y, r in ((-0.6, 0.25, 0.3), (0.65, 0.3, 0.0)):
            o = cyl(0.36, 0.22, (x, y, 0.23), mat("minas", (0.98, 0.96, 0.9), rough=0.45), seg=48, bevel=0.05)
        for k in range(3):
            o = cheese_wedge_at((-0.2 + k * 0.4, -0.35, 0.12), k * 0.5)
        for g in range(7):
            sphere(0.07, (0.85 + (g % 3) * 0.1, -0.35 + (g // 3) * 0.1, 0.18), mat("grape", PAL["grape"], rough=0.2))


def cheese_wedge_at(loc, rot):
    box((0.4, 0.28, 0.2), (loc[0], loc[1], loc[2] + 0.1), mat("brie_in", (0.98, 0.9, 0.62), rough=0.3, noise=0.04), bevel=0.03, rot=(0, 0, rot))


def bench_queijaria():
    """Cheese room: a stainless steel table and white tiles with a shelf of maturing cheeses."""
    box((18, 13, 0.4), (0, -2.0, -0.2), mat("bench_steel2", (0.8, 0.82, 0.84), rough=0.32, metal=0.55, noise=0.05), bevel=0.02)
    box((18, 0.3, 8), (0, 4.6, 3.8), mat("tiles_wall2", (0.93, 0.95, 0.95), rough=0.3, pattern="bricks", scale=1.4, noise=0.03, axis="xz"), bevel=0)
    for z in (1.4, 2.9):
        box((18, 0.7, 0.12), (0, 4.15, z), mat("shelf_q", (0.6, 0.42, 0.24), pattern="planks", scale=3), bevel=0.03)
        for x in [-7.2 + i * 1.3 for i in range(12)]:
            if abs(x) < 1.6 and z > 2:
                continue
            c = (0.97, 0.9, 0.55) if (int(x * 10) + int(z)) % 2 else (0.98, 0.96, 0.88)
            cyl(0.48, 0.38, (x, 4.15, z + 0.25), mat("shelfcheese%d" % int(c[2] * 10), c, rough=0.6), seg=32, bevel=0.07)


# ---------------------------------------------------------------- açougue
def beef():
    return mat("beef", (0.72, 0.16, 0.14), rough=0.35, noise=0.14)


def fat():
    return mat("fat", (0.97, 0.92, 0.8), rough=0.45, noise=0.06)


def meat_piece(trimmed=False, aged=False):
    """A boneless beef piece: red muscle, a fat cap and silver skin (gone when trimmed); aged = dark crust."""
    m = mat("aged", (0.36, 0.13, 0.1), rough=0.8, noise=0.2) if aged else beef()
    o = lump([((0, 0, 0.32), 0.7, (1.45, 0.95, 0.5)), ((0.5, 0.15, 0.3), 0.45, (1, 1, 0.8)), ((-0.55, -0.1, 0.3), 0.45, (1, 1, 0.8))], m, voxel=0.03, name="meat")
    bumpy(o, 0.04 if not aged else 0.07, 0.15, 12)
    if not trimmed:
        f = lump([((-0.1, 0.35, 0.5), 0.5, (1.6, 0.5, 0.35)), ((0.6, 0.3, 0.45), 0.3, (1, 0.6, 0.4))], fat(), voxel=0.025, name="fatcap")
        bumpy(f, 0.03, 0.1, 13)
        for i, (x, y, r) in enumerate(((-0.6, -0.2, 0.4), (0.3, -0.25, -0.3), (0.0, 0.05, 0.1))):
            box((0.55, 0.05, 0.03), (x, y, 0.62), mat("silver", (0.9, 0.9, 0.92), rough=0.25, noise=0.04), bevel=0.012, rot=(0, 0, r))
    else:
        for i, (x, y, r) in enumerate(((-0.5, -0.1, 0.3), (0.2, 0.15, -0.4), (0.5, -0.2, 0.2), (-0.1, -0.3, 0.6))):
            box((0.4, 0.025, 0.02), (x, y, 0.64), mat("marble", (0.95, 0.85, 0.82), rough=0.4), bevel=0.008, rot=(0, 0, r))


def grinder(full=False):
    s_ = steel()
    box((0.7, 0.9, 0.9), (0, 0, 0.45), s_, bevel=0.12)
    cyl(0.32, 1.1, (0.55, 0, 0.75), s_, seg=40, rot=(0, math.radians(90), 0))
    cyl(0.36, 0.06, (1.12, 0, 0.75), mat("plate_holes", (0.55, 0.57, 0.6), rough=0.3, metal=0.8), seg=40, rot=(0, math.radians(90), 0))
    cyl(0.42, 0.45, (0.45, 0, 1.4), s_, seg=40, r2=0.2)
    cyl(0.05, 0.6, (-0.2, 0, 0.95), s_, seg=12, rot=(0, math.radians(90), 0))
    box((0.08, 0.08, 0.55), (-0.5, 0, 1.15), s_, bevel=0.02)
    cyl(0.08, 0.28, (-0.5, -0.1, 1.42), mat("crank_knob", (0.85, 0.2, 0.15), rough=0.3), seg=16, rot=(math.radians(90), 0, 0))
    if full:
        for i in range(9):
            cyl(0.035, 0.35 + (i % 3) * 0.08, (1.3 + (i % 3) * 0.04, -0.2 + (i // 3) * 0.2 + (i % 3) * 0.03, 0.62 - 0.05 * (i % 3)), mat("mince", (0.78, 0.25, 0.22), rough=0.5, noise=0.2), seg=8, rot=(0, math.radians(100), 0))
        o = lump([((1.45, 0, 0.2), 0.32, (1.2, 1.2, 0.6))], mat("mince", (0.78, 0.25, 0.22), rough=0.5, noise=0.2), voxel=0.02)
        bumpy(o, 0.05, 0.03, 14)
        cyl(0.5, 0.06, (1.45, 0, 0.03), mat("plate_w", (0.96, 0.96, 0.96), rough=0.2), seg=40)


def patty(pressed=False, x=0.0, y=0.0):
    m = mat("mince", (0.78, 0.25, 0.22), rough=0.5, noise=0.2)
    if pressed:
        o = cyl(0.5, 0.14, (x, y, 0.07), m, seg=40, bevel=0.06)
    else:
        o = lump([((x, y, 0.3), 0.32, (1, 1, 0.9))], m, voxel=0.02)
    bumpy(o, 0.03, 0.025, 15)
    return o


def scale_with(ball=True):
    box((1.6, 1.3, 0.3), (0, 0, 0.15), mat("scale_body", (0.92, 0.92, 0.9), rough=0.3), bevel=0.08)
    box((1.4, 1.1, 0.05), (0, 0.05, 0.33), steel(), bevel=0.02)
    box((0.7, 0.06, 0.2), (0, -0.66, 0.16), mat("lcd", (0.55, 0.7, 0.5), rough=0.2, emit=0.4), bevel=0.02)
    text("150 g", (0, -0.7, 0.16), 0.12, "dark")
    if ball:
        o = lump([((0, 0.05, 0.6), 0.3, (1, 1, 0.9))], mat("mince", (0.78, 0.25, 0.22), rough=0.5, noise=0.2), voxel=0.02)
        bumpy(o, 0.03, 0.025, 16)


def foam_tray(content=None):
    box((2.4, 1.5, 0.16), (0, 0, 0.08), mat("foam", (0.96, 0.96, 0.95), rough=0.8), bevel=0.06)
    if content == "patties":
        for i, (x, y) in enumerate(((-0.55, 0.3), (0.55, 0.3), (-0.55, -0.3), (0.55, -0.3))):
            o = cyl(0.42, 0.12, (x, y, 0.25), mat("mince", (0.78, 0.25, 0.22), rough=0.5, noise=0.2), seg=40, bevel=0.05)
    if content == "steaks":
        for i in range(3):
            o = lump([((-0.7 + i * 0.7, 0, 0.24), 0.36, (0.9, 1.3, 0.25))], beef(), voxel=0.02)
            box((0.06, 0.5, 0.04), (-0.85 + i * 0.7, 0, 0.29), fat(), bevel=0.02)
    if content:
        box((0.7, 0.4, 0.02), (0.7, -0.45, 0.38), mat("label", (0.98, 0.98, 0.95), rough=0.6), bevel=0.01)
        box((0.55, 0.06, 0.021), (0.7, -0.4, 0.39), "red", bevel=0)


def aging_cabinet():
    box((2.0, 1.2, 3.0), (0, 0, 1.5), mat("cab", (0.2, 0.21, 0.23), rough=0.35, metal=0.4), bevel=0.06)
    box((1.7, 0.05, 2.6), (0, -0.6, 1.5), mat("cab_glow", (0.95, 0.55, 0.55), rough=0.15, emit=0.35, noise=0.02), bevel=0.03)
    for z in (0.9, 1.7, 2.4):
        box((1.6, 0.9, 0.04), (0, 0, z), steel(), bevel=0.01)
    box((0.5, 0.05, 0.16), (0.55, -0.64, 2.88), mat("lcd2", (0.15, 0.15, 0.15)), bevel=0.02)
    text("2°C", (0.55, -0.68, 2.88), 0.1, mat("digits_b", (0.4, 0.8, 1.0), emit=2, noise=0))


def steaks():
    for i in range(3):
        o = lump([((-0.65 + i * 0.65, 0.05 * i, 0.12), 0.38, (0.85, 1.25, 0.3))], beef(), voxel=0.02)
        bumpy(o, 0.015, 0.1, 17 + i)
        box((0.07, 0.55, 0.05), (-0.82 + i * 0.65, 0.05 * i, 0.18), fat(), bevel=0.025)
        for k in range(3):
            box((0.22, 0.02, 0.01), (-0.6 + i * 0.65, -0.15 + k * 0.15, 0.24), mat("marble", (0.95, 0.85, 0.82), rough=0.4), bevel=0.005, rot=(0, 0, 0.4 * k))


def picanha(pieces=False):
    if pieces:
        o = lump([((0, 0, 0.25), 0.3, (1, 1, 0.8))], beef(), voxel=0.02)
        f = lump([((0, 0.2, 0.32), 0.22, (1.2, 0.5, 0.6))], fat(), voxel=0.02)
        return
    o = lump([((0, 0, 0.25), 0.6, (1.8, 0.9, 0.45))], beef(), voxel=0.03)
    bumpy(o, 0.03, 0.15, 19)
    f = lump([((0, 0.25, 0.42), 0.55, (1.95, 0.55, 0.22))], fat(), voxel=0.03)


def skewer(full=False):
    cyl(0.03, 2.6, (0, 0, 0.3), steel(), seg=10, rot=(0, math.radians(90), 0))
    box((0.4, 0.14, 0.14), (-1.4, 0, 0.3), mat("skewer_h", (0.55, 0.35, 0.2), pattern="planks", scale=12), bevel=0.04)
    if full:
        for i in range(5):
            x = -0.8 + i * 0.42
            lump([((x, 0, 0.3), 0.2, (1, 1, 0.9))], beef(), voxel=0.02)
            lump([((x, 0.12, 0.38), 0.14, (1, 0.5, 0.6))], fat(), voxel=0.02)


def bbq_box(full=False):
    box((2.4, 1.6, 0.5), (0, 0, 0.25), mat("kraft", (0.78, 0.6, 0.38), rough=0.8, noise=0.1), bevel=0.04)
    box((2.2, 1.4, 0.05), (0, 0, 0.47), mat("kraft_in", (0.7, 0.52, 0.32), rough=0.85), bevel=0.01)
    text("CHURRASCO", (0, -0.81, 0.27), 0.16, "red")
    if full:
        for i in range(2):
            cyl(0.03, 1.8, (-0.1, -0.3 + i * 0.3, 0.6), steel(), seg=8, rot=(0, math.radians(90), 0))
            for k in range(4):
                lump([((-0.7 + k * 0.4, -0.3 + i * 0.3, 0.62), 0.15, (1, 1, 0.9))], beef(), voxel=0.02)
        for k in range(3):
            cyl(0.13, 0.5, (0.85, -0.45 + k * 0.32, 0.75), mat("can", (0.85, 0.65, 0.15), rough=0.25, metal=0.6), seg=24, bevel=0.03)


def cleaver():
    box((0.8, 0.04, 0.38), (0.25, 0, 0.3), mat("blade_k", (0.8, 0.82, 0.85), rough=0.15, metal=1.0, noise=0.02), bevel=0.01)
    box((0.6, 0.12, 0.12), (-0.45, 0, 0.3), mat("handle_k", (0.15, 0.13, 0.12), rough=0.4), bevel=0.04)


def bench_acougue():
    """Butcher's: an end-grain chopping block and red and white tiles with knives on a magnet bar."""
    box((18, 13, 0.4), (0, -2.0, -0.2), mat("block", (0.66, 0.42, 0.25), rough=0.6, pattern="bricks", scale=1.6, noise=0.1), bevel=0.02)
    box((18, 0.3, 8), (0, 4.6, 3.8), mat("tiles_red", (0.95, 0.94, 0.92), rough=0.3, pattern="bricks", scale=1.2, noise=0.03, axis="xz"), bevel=0)
    box((18, 0.32, 0.5), (0, 4.5, 1.2), mat("tile_band", (0.75, 0.15, 0.13), rough=0.3), bevel=0)
    box((7, 0.2, 0.25), (0, 4.35, 2.6), "dark", bevel=0.04)
    for i in range(6):
        x = -2.6 + i * 1.05
        box((0.35, 0.05, 1.0), (x, 4.2, 2.1), mat("blade_k", (0.8, 0.82, 0.85), rough=0.15, metal=1.0, noise=0.02), bevel=0.01)
        box((0.12, 0.12, 0.5), (x, 4.2, 2.85), mat("handle_k", (0.15, 0.13, 0.12), rough=0.4), bevel=0.03)


# ---------------------------------------------------------------- peixaria
def fish_mat(state):
    if state == "whole":
        return mat("fish_scales2", (0.55, 0.63, 0.72), rough=0.35, metal=0.25, pattern="tiles", scale=22, noise=0.18)
    return mat("fish_skin", (0.7, 0.76, 0.82), rough=0.15, metal=0.35, noise=0.06)


def fish(state="whole"):
    """A whole fish lying on its side on the board (its flank up): body, tail, fins, eye; scaled / opened versions."""
    m = fish_mat(state)
    parts = [((x, 0, 0.22), 0.5 * (1 - abs(x + 0.1) * 0.42), (1.0, 0.8, 0.45)) for x in (-1.1, -0.7, -0.3, 0.1, 0.5, 0.85)]
    lump(parts, m, voxel=0.03, name="fish")
    fin_m = mat("fin", (0.5, 0.58, 0.68), rough=0.3)
    for pts in ([(1.0, 0, 0), (1.65, 0.5, 0), (1.65, -0.5, 0)], [(-0.4, 0.3, 0), (0.4, 0.62, 0), (0.55, 0.28, 0)], [(0.0, -0.3, 0), (0.45, -0.55, 0), (0.55, -0.25, 0)]):
        me = bpy.data.meshes.new("fin")
        me.from_pydata(pts, [], [(0, 1, 2)])
        o = bpy.data.objects.new("fin", me)
        o.location = (0, 0, 0.2)
        _link(o, fin_m)
        o.modifiers.new("Solid", "SOLIDIFY").thickness = 0.03
    sphere(0.1, (-1.12, 0.06, 0.42), mat("eye_w", (0.95, 0.95, 0.92), rough=0.1), scale=(1, 1, 0.5))
    sphere(0.055, (-1.13, 0.06, 0.46), mat("eye_b", (0.05, 0.05, 0.06), rough=0.05), scale=(1, 1, 0.5))
    box((0.05, 0.55, 0.04), (-0.78, 0, 0.44), mat("gill", (0.45, 0.5, 0.58), rough=0.3), bevel=0.02, rot=(0, 0, 0.15))
    if state == "open":
        box((1.3, 0.1, 0.05), (-0.3, -0.3, 0.42), mat("belly", (0.85, 0.4, 0.4), rough=0.4), bevel=0.025)


def fillets(bones=False, ice=False):
    if ice:
        box((2.6, 1.6, 0.14), (0, 0, 0.07), steel(), bevel=0.04)
        rnd = random.Random(30)
        for i in range(70):
            box((0.16, 0.16, 0.12), (rnd.uniform(-1.15, 1.15), rnd.uniform(-0.65, 0.65), 0.18), mat("ice_c", (0.9, 0.96, 1.0), rough=0.05, noise=0.02), bevel=0.04, rot=(rnd.random(), rnd.random(), rnd.random()))
    n = 2 if not ice else 4
    for i in range(n):
        y = (i - (n - 1) / 2) * (0.62 if not ice else 0.36)
        z = 0.08 if not ice else 0.3
        o = lump([((x, y, z), 0.3 * (1 - abs(x) * 0.35), (1.0, 0.85 if not ice else 0.6, 0.3)) for x in [k * 0.1 - 0.85 for k in range(18)]],
                 mat("fillet", (0.97, 0.75, 0.62), rough=0.3, noise=0.08), voxel=0.025, name="fillet")
        for k in range(6):
            box((0.02, 0.18, 0.012), (-0.7 + k * 0.28, y, z + 0.1), mat("flake_l", (1.0, 0.88, 0.8), rough=0.35), bevel=0.005, rot=(0, 0, 0.5))
        if bones and i == 0:
            for k in range(7):
                cyl(0.012, 0.12, (-0.55 + k * 0.17, y + 0.08, z + 0.11), mat("bone", (0.98, 0.98, 0.95), rough=0.3), seg=6, bevel=0, rot=(0, math.radians(90), 0.3))


def ice_tray():
    box((2.6, 1.6, 0.14), (0, 0, 0.07), steel(), bevel=0.04)
    rnd = random.Random(30)
    for i in range(70):
        box((0.16, 0.16, 0.12), (rnd.uniform(-1.15, 1.15), rnd.uniform(-0.65, 0.65), 0.18), mat("ice_c", (0.9, 0.96, 1.0), rough=0.05, noise=0.02), bevel=0.04, rot=(rnd.random(), rnd.random(), rnd.random()))


def shrimp():
    """A cooked shrimp: a curl of shell segments, the tail fan and the stripe on its back."""
    m = mat("shrimp", (0.98, 0.52, 0.36), rough=0.3, noise=0.08)
    parts = []
    for k in range(9):
        a = math.radians(-30 + k * 27)
        r = 0.16 * (1 - k * 0.06)
        parts.append(((math.cos(a) * 0.32, math.sin(a) * 0.32, 0.15), r, (1, 1, 0.75)))
    o = lump(parts, m, voxel=0.015, name="shrimp")
    for s_ in (1, -1):
        sphere(0.12, (0.42 + 0.05 * s_, -0.32, 0.12), m, scale=(0.6, 1.2, 0.3))


def scaler():
    cyl(0.06, 0.7, (-0.45, 0, 0.1), mat("scaler_h", (0.2, 0.45, 0.75), rough=0.3), seg=16, rot=(0, math.radians(90), 0))
    box((0.4, 0.3, 0.06), (0.1, 0, 0.1), steel(), bevel=0.02)
    for k in range(6):
        box((0.02, 0.28, 0.06), (-0.05 + k * 0.06, 0, 0.14), steel(), bevel=0)


def tweezers():
    for s_ in (1, -1):
        box((1.0, 0.06, 0.03), (0, s_ * 0.06, 0.08), steel(), bevel=0.01, rot=(0, 0, s_ * 0.06))


def fish_knife():
    box((1.0, 0.03, 0.18), (0.25, 0, 0.12), mat("blade_k", (0.8, 0.82, 0.85), rough=0.15, metal=1.0, noise=0.02), bevel=0.01)
    box((0.5, 0.1, 0.12), (-0.5, 0, 0.12), mat("handle_w", (0.95, 0.95, 0.95), rough=0.4), bevel=0.04)


def rice_tub(seasoned=False):
    cyl(1.0, 0.4, (0, 0, 0.2), mat("hangiri", (0.75, 0.55, 0.32), rough=0.5, pattern="planks", scale=18), seg=64, bevel=0.04)
    for z in (0.1, 0.3):
        torus(1.0, 0.025, (0, 0, z), mat("copper", (0.75, 0.45, 0.25), rough=0.3, metal=0.8))
    o = lump([((0, 0, 0.3), 0.92, (1, 1, 0.15))], mat("rice" + ("_s" if seasoned else ""), (0.98, 0.97, 0.93) if not seasoned else (0.98, 0.96, 0.88), rough=0.6, noise=0.1), voxel=0.03)
    bumpy(o, 0.03, 0.02, 31)


def salmon(sliced=False):
    m = mat("salmon", (0.98, 0.5, 0.32), rough=0.25, noise=0.06)
    if not sliced:
        box((1.8, 0.8, 0.4), (0, 0, 0.2), m, bevel=0.08)
        for k in range(8):
            box((0.02, 0.82, 0.41), (-0.8 + k * 0.23, 0, 0.2), mat("salmon_line", (1.0, 0.85, 0.75)), bevel=0)
        return
    for i in range(6):
        box((0.42, 0.75, 0.1), (-1.0 + i * 0.4, 0, 0.1 + i * 0.01), m, bevel=0.04, rot=(0, -0.25, 0))
        box((0.43, 0.02, 0.11), (-1.0 + i * 0.4, -0.2, 0.1 + i * 0.01), mat("salmon_line", (1.0, 0.85, 0.75)), bevel=0, rot=(0, -0.25, 0))


def makisu(rolled=False):
    if not rolled:
        for k in range(22):
            cyl(0.04, 1.8, (-1.0 + k * 0.095, 0, 0.04), mat("bamboo", (0.82, 0.72, 0.45), rough=0.5), seg=8, rot=(math.radians(90), 0, 0))
        box((1.7, 1.5, 0.03), (0, 0, 0.1), mat("nori", (0.12, 0.2, 0.12), rough=0.6, noise=0.1), bevel=0.01)
        o = lump([((0, -0.1, 0.17), 0.8, (1.0, 0.8, 0.08))], mat("rice_s", (0.98, 0.96, 0.88), rough=0.6, noise=0.1), voxel=0.03)
        bumpy(o, 0.02, 0.02, 32)
        box((1.4, 0.18, 0.12), (0, -0.2, 0.26), mat("salmon", (0.98, 0.5, 0.32), rough=0.25, noise=0.06), bevel=0.04)
        return
    cyl(0.32, 2.0, (0, 0, 0.32), mat("nori", (0.12, 0.2, 0.12), rough=0.6, noise=0.1), seg=40, bevel=0.03, rot=(0, math.radians(90), 0))


def sushi_plate(boat=False, full=True):
    if boat:
        hull = lump([((x, 0, 0.3), 0.5, (1.0, 1.0, 0.6)) for x in (-1.0, -0.4, 0.2, 0.8)], mat("boat", (0.62, 0.38, 0.2), rough=0.5, pattern="planks", scale=10), voxel=0.04)
        box((2.6, 0.75, 0.1), (0, 0, 0.55), mat("boat_top", (0.72, 0.48, 0.26), pattern="planks", scale=12), bevel=0.03)
        box((0.1, 0.1, 0.9), (1.25, 0, 0.9), mat("boat", (0.62, 0.38, 0.2)), bevel=0.02)
    else:
        box((2.4, 1.0, 0.12), (0, 0, 0.06), mat("plate_black", (0.1, 0.1, 0.11), rough=0.15), bevel=0.05)
    if not full:
        return
    z = 0.65 if boat else 0.12
    for i in range(6 if boat else 5):
        x = -1.0 + i * (0.38 if boat else 0.48)
        cyl(0.17, 0.2, (x, -0.15 if boat else 0, z + 0.1), mat("rice_s", (0.98, 0.96, 0.88), rough=0.6), seg=24, bevel=0.03)
        box((0.32, 0.36, 0.05), (x, -0.15 if boat else 0, z + 0.22), mat("salmon", (0.98, 0.5, 0.32), rough=0.25), bevel=0.02)
    if boat:
        for i in range(4):
            torus(0.13, 0.05, (-0.8 + i * 0.5, 0.2, z + 0.12), mat("shrimp", (0.98, 0.55, 0.4), rough=0.3), rot=(0, 0, 0.5))


def sushi_piece():
    cyl(0.3, 0.35, (0, 0, 0.18), mat("rice_s", (0.98, 0.96, 0.88), rough=0.6), seg=24, bevel=0.05)
    box((0.62, 0.66, 0.08), (0, 0, 0.4), mat("salmon", (0.98, 0.5, 0.32), rough=0.25, noise=0.06), bevel=0.03)


def bench_peixaria():
    """Fish counter: a steel table with a bed of crushed ice and blue tiles behind it."""
    box((18, 13, 0.4), (0, -2.0, -0.2), mat("bench_steel2", (0.8, 0.82, 0.84), rough=0.32, metal=0.55, noise=0.05), bevel=0.02)
    box((18, 0.3, 8), (0, 4.6, 3.8), mat("tiles_blue", (0.6, 0.78, 0.9), rough=0.3, pattern="bricks", scale=1.2, noise=0.04, axis="xz"), bevel=0)
    rnd = random.Random(40)
    for i in range(160):
        box((0.3, 0.3, 0.2), (rnd.uniform(-8.5, 8.5), rnd.uniform(2.6, 4.3), 0.1), mat("ice_c", (0.9, 0.96, 1.0), rough=0.05, noise=0.02), bevel=0.06, rot=(rnd.random(), rnd.random(), rnd.random()))
    for x in (-6, -3, 3, 6):
        fish_at = lump([((x + dx, 3.5, 0.35), 0.35 * (1 - abs(dx) * 0.4), (1, 0.5, 0.7)) for dx in (-0.6, -0.2, 0.2, 0.6)], fish_mat("whole"), voxel=0.04)


# ---------------------------------------------------------------- bebidas, sorvetes, adega
def glassm():
    """Clear glass for the UI art: a pale, partly see-through surface (no refraction of the empty background)."""
    name = "LA_glass_ui"
    if name in MATS:
        return MATS[name]
    g = mat("glass_ui", (0.9, 0.96, 1.0), rough=0.06, noise=0.01)
    for n in g.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Alpha"].default_value = 0.32
    g.blend_method = "BLEND" if hasattr(g, "blend_method") else g.blend_method
    return g


def drink_glass(fill=None, ice=True, straw=True):
    """A tall glass, empty or with a drink (colour), ice cubes and a straw."""
    me = bpy.data.meshes.new("glass")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=0.36, radius2=0.42, depth=1.3)
    bottom = [v for v in bm.verts if v.co.z < 0]
    bm.faces.new(sorted(bottom, key=lambda v: math.atan2(v.co.y, v.co.x)))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("glass", me)
    o.location = (0, 0, 0.65)
    _link(o, glassm())
    o.modifiers.new("Wall", "SOLIDIFY").thickness = 0.03
    if fill:
        cyl(0.36, 1.0, (0, 0, 0.52), mat("drink%d" % int(fill[0] * 100 + fill[1] * 10 + fill[2]), fill, rough=0.1, noise=0.05), seg=48, r2=0.4, bevel=0)
        if ice:
            for k in range(3):
                box((0.2, 0.2, 0.2), (-0.12 + k * 0.12, 0.05 * (k % 2), 1.0 + 0.03 * k), mat("ice_c", (0.9, 0.96, 1.0), rough=0.05, noise=0.02), bevel=0.05, rot=(0.4 * k, 0.3, 0.6 * k))
        if straw:
            cyl(0.03, 1.4, (0.15, 0.05, 1.1), mat("straw", (0.95, 0.3, 0.35), rough=0.3), seg=12, rot=(0.25, 0.2, 0))


def blender_jar(fill=None, smooth=False):
    """The bar blender: a base with buttons and a glass jar, empty or with fruit or blended juice."""
    box((0.9, 0.8, 0.5), (0, 0, 0.25), mat("blender_base", (0.88, 0.3, 0.25), rough=0.3), bevel=0.1)
    for k in range(3):
        cyl(0.07, 0.05, (-0.2 + k * 0.2, -0.41, 0.25), mat("btn", (0.95, 0.95, 0.95), rough=0.3), seg=16, rot=(math.radians(90), 0, 0))
    me = bpy.data.meshes.new("jar")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=40, radius1=0.32, radius2=0.45, depth=1.2)
    bottom = [v for v in bm.verts if v.co.z < 0]
    bm.faces.new(sorted(bottom, key=lambda v: math.atan2(v.co.y, v.co.x)))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("jar", me)
    o.location = (0, 0, 1.12)
    _link(o, glassm())
    o.modifiers.new("Wall", "SOLIDIFY").thickness = 0.03
    cyl(0.47, 0.1, (0, 0, 1.75), mat("lid", (0.15, 0.15, 0.16), rough=0.4), seg=40, bevel=0.03)
    if fill:
        m = mat("blend%d" % int(fill[0] * 100 + fill[1] * 10 + fill[2]), fill, rough=0.15 if smooth else 0.5, noise=0.04 if smooth else 0.2)
        if smooth:
            cyl(0.31, 0.8, (0, 0, 0.95), m, seg=40, r2=0.4, bevel=0)
        else:
            rnd = random.Random(50)
            for k in range(14):
                sphere(rnd.uniform(0.09, 0.14), (rnd.uniform(-0.18, 0.18), rnd.uniform(-0.18, 0.18), 0.65 + k * 0.045), m)


def fruit_bowl(washed=False):
    bowl(1.0, 0.55)
    if True:
        cyl(0.88, 0.04, (0, 0, 0.4), mat("water_b", (0.6, 0.82, 0.95), rough=0.05, noise=0.02), seg=48, bevel=0)
    for k, (x, y) in enumerate(((-0.35, 0.1), (0.3, 0.2), (0.0, -0.25))):
        sphere(0.28, (x, y, 0.5), mat("apple", (0.85, 0.12, 0.12), rough=0.25, noise=0.08))
        cyl(0.02, 0.12, (x, y, 0.8), "wood", seg=8)
    for k in range(2):
        o = lump([((0.3 * math.cos(a), 0.3 * math.sin(a) - 0.1 + k * 0.25, 0.62), 0.11, (1, 1, 1)) for a in [math.radians(200 + i * 18) for i in range(8)]],
                 mat("banana", (0.98, 0.84, 0.25), rough=0.4, noise=0.08), voxel=0.02)
    if washed:
        for k in range(12):
            sphere(0.03, (random.Random(k).uniform(-0.6, 0.6), random.Random(k + 9).uniform(-0.5, 0.5), 0.85), mat("drop", (0.8, 0.92, 1.0), rough=0.02))


def apple_board(sliced=False):
    box((1.8, 1.2, 0.1), (0, 0, 0.05), mat("cboard", (0.85, 0.7, 0.5), rough=0.6, pattern="planks", scale=5, wavy=0.2), bevel=0.04)
    if not sliced:
        sphere(0.4, (0, 0, 0.45), mat("apple", (0.85, 0.12, 0.12), rough=0.25, noise=0.08))
        cyl(0.025, 0.15, (0, 0, 0.88), "wood", seg=8)
        sphere(0.1, (0.1, 0.05, 0.86), mat("leaf", PAL["leaf"]), scale=(1.4, 0.6, 0.2))
        return
    for k in range(4):
        a = k * math.pi / 2
        o = sphere(0.3, (math.cos(a) * 0.35, math.sin(a) * 0.25, 0.25), mat("apple_in", (0.98, 0.93, 0.75), rough=0.4), scale=(1, 0.6, 0.6))
        sphere(0.3, (math.cos(a) * 0.38, math.sin(a) * 0.27, 0.25), mat("apple", (0.85, 0.12, 0.12), rough=0.25, noise=0.08), scale=(1.01, 0.55, 0.62))


def kettle():
    o = lump([((0, 0, 0.5), 0.6, (1, 1, 0.85))], steel(), voxel=0.03)
    cyl(0.25, 0.1, (0, 0, 1.0), mat("knob_k", (0.15, 0.15, 0.15)), seg=24, bevel=0.03)
    cyl(0.07, 0.6, (0.62, 0, 0.6), steel(), seg=16, rot=(0, math.radians(55), 0))
    torus(0.32, 0.05, (-0.35, 0, 0.75), mat("knob_k", (0.15, 0.15, 0.15)), rot=(math.radians(90), 0, 0))


def tea_jar():
    jar((0.35, 0.55, 0.3), "CHÁ", lid=(0.8, 0.6, 0.3), fill=(0.35, 0.45, 0.2))


def ice_bucket():
    cyl(0.6, 0.6, (0, 0, 0.3), steel(), seg=40, r2=0.7, bevel=0.03)
    rnd = random.Random(60)
    for k in range(16):
        box((0.2, 0.2, 0.18), (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 0.62 + rnd.uniform(0, 0.12)), mat("ice_c", (0.9, 0.96, 1.0), rough=0.05, noise=0.02), bevel=0.05, rot=(rnd.random(), rnd.random(), rnd.random()))


def ice_cube():
    box((0.5, 0.5, 0.45), (0, 0, 0.25), mat("ice_c", (0.9, 0.96, 1.0), rough=0.05, noise=0.02), bevel=0.1, rot=(0.2, 0.15, 0.3))


def churner(full=False):
    """Ice cream machine: a steel body with a frozen bowl and a paddle."""
    box((1.6, 1.2, 0.9), (0, 0, 0.45), mat("churn_body", (0.92, 0.92, 0.9), rough=0.3), bevel=0.12)
    box((0.6, 0.05, 0.2), (-0.35, -0.61, 0.5), mat("lcd3", (0.2, 0.6, 0.9), rough=0.2, emit=0.6), bevel=0.02)
    cyl(0.62, 0.5, (0.1, 0.1, 1.05), steel(), seg=48, bevel=0.03)
    cyl(0.55, 0.05, (0.1, 0.1, 1.3), mat("cream_soft" if full else "base_liq", (0.98, 0.95, 0.85) if full else (0.98, 0.93, 0.78), rough=0.4 if full else 0.1, noise=0.08), seg=48, bevel=0)
    if full:
        for k in range(6):
            sphere(0.16, (0.1 + math.cos(k) * 0.3, 0.1 + math.sin(k) * 0.3, 1.36), mat("cream_soft", (0.98, 0.95, 0.85), rough=0.4), scale=(1, 1, 0.5))
    box((0.08, 0.5, 0.06), (0.1, 0.1, 1.4), "dark", bevel=0.02)


def scoop_ball(color=(0.98, 0.94, 0.8)):
    o = lump([((0, 0, 0.3), 0.32, (1, 1, 0.9)), ((0.15, 0.1, 0.22), 0.18, (1, 1, 0.6)), ((-0.15, -0.08, 0.2), 0.18, (1, 1, 0.6))],
             mat("icecream%d" % int(color[0] * 100 + color[2] * 10), color, rough=0.5, noise=0.06), voxel=0.015)
    bumpy(o, 0.015, 0.05, 61)


def ice_pot(full=False, family=False):
    r = 0.75 if family else 0.55
    cyl(r, 0.6, (0, 0, 0.3), mat("pot_paper", (0.98, 0.97, 0.95), rough=0.5), seg=48, r2=r * 1.15, bevel=0.03)
    cyl(r * 1.16, 0.12, (0, 0, 0.62), mat("pot_band", (0.9, 0.35, 0.5), rough=0.4), seg=48, bevel=0.02)
    if full:
        for k in range(3 if family else 1):
            a = k * 2.1
            lump([((math.cos(a) * r * 0.45 * (1 if family else 0), math.sin(a) * r * 0.45 * (1 if family else 0), 0.7), r * 0.6, (1, 1, 0.6))],
                 mat("icecream98", (0.98, 0.94, 0.8), rough=0.5, noise=0.06), voxel=0.02)


def sundae(full=False):
    glass = glassm()
    cyl(0.2, 0.08, (0, 0, 0.04), glass, seg=32)
    cyl(0.06, 0.4, (0, 0, 0.28), glass, seg=16)
    me = bpy.data.meshes.new("cup")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=40, radius1=0.25, radius2=0.62, depth=0.5)
    bottom = [v for v in bm.verts if v.co.z < 0]
    bm.faces.new(sorted(bottom, key=lambda v: math.atan2(v.co.y, v.co.x)))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("cup", me)
    o.location = (0, 0, 0.73)
    _link(o, glass)
    o.modifiers.new("Wall", "SOLIDIFY").thickness = 0.03
    if full:
        for x in (-0.18, 0.18):
            lump([((x, 0, 0.98), 0.28, (1, 1, 0.85))], mat("icecream98", (0.98, 0.94, 0.8), rough=0.5, noise=0.06), voxel=0.02)
        for k in range(8):
            a = k * 0.8
            cyl(0.03, 0.25, (math.cos(a) * 0.25, math.sin(a) * 0.15, 1.12 - k * 0.02), mat("choc_sauce", PAL["choco"], rough=0.1), seg=8, rot=(1.2, 0, a))
        sphere(0.08, (0, 0, 1.3), mat("cherry", PAL["cherry"], rough=0.15))


def grape_tub(crushed=False):
    cyl(1.0, 0.7, (0, 0, 0.35), mat("tub_wood", (0.6, 0.4, 0.22), rough=0.6, pattern="planks", scale=14), seg=48, r2=1.1, bevel=0.03)
    for z in (0.15, 0.55):
        torus(1.02 + z * 0.12, 0.03, (0, 0, z), mat("hoop", (0.3, 0.28, 0.27), metal=0.5, noise=0))
    if crushed:
        cyl(1.0, 0.05, (0, 0, 0.66), mat("must", (0.42, 0.08, 0.2), rough=0.15, noise=0.1), seg=48, bevel=0)
        rnd = random.Random(70)
        for k in range(30):
            sphere(0.06, (rnd.uniform(-0.7, 0.7), rnd.uniform(-0.7, 0.7), 0.69), mat("skin", (0.3, 0.1, 0.25), rough=0.3), scale=(1, 1, 0.4))
        return
    rnd = random.Random(71)
    for k in range(70):
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(0, 0.85)
        sphere(0.11, (math.cos(a) * r, math.sin(a) * r, 0.72 + rnd.uniform(0, 0.15)), mat("grape", PAL["grape"], rough=0.2, noise=0.1))


def wine_press(full=False):
    box((1.4, 1.4, 0.15), (0, 0, 0.08), mat("press_base", (0.45, 0.3, 0.18), pattern="planks", scale=8), bevel=0.04)
    cyl(0.55, 1.0, (0, 0, 0.65), mat("press_cage", (0.6, 0.4, 0.22), rough=0.6, pattern="planks", scale=20), seg=24, bevel=0.02)
    cyl(0.06, 1.0, (0, 0, 1.6), mat("screw", (0.3, 0.3, 0.3), metal=0.7, rough=0.3), seg=12)
    box((1.2, 0.08, 0.08), (0, 0, 1.75), mat("screw", (0.3, 0.3, 0.3), metal=0.7, rough=0.3), bevel=0.02)
    box((0.3, 0.2, 0.1), (0, -0.75, 0.15), mat("spout", (0.45, 0.3, 0.18)), bevel=0.03)
    if full:
        cyl(0.3, 0.25, (0, -1.0, 0.13), mat("pan", (0.75, 0.75, 0.76), metal=0.6, rough=0.3), seg=32, bevel=0.02)
        cyl(0.27, 0.03, (0, -1.0, 0.25), mat("must", (0.42, 0.08, 0.2), rough=0.15), seg=32, bevel=0)


def wine_barrel():
    barrel(0, 0, 0.0, 3.2, lying=True)


def wine_bottle(state="empty"):
    g = mat("bottle_g", (0.15, 0.3, 0.15), rough=0.1, noise=0.03)
    if state == "empty":
        for n in g.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED" and "Transmission Weight" in n.inputs:
                n.inputs["Transmission Weight"].default_value = 0.6
    cyl(0.3, 1.1, (0, 0, 0.55), g, seg=40, bevel=0.06)
    cyl(0.3, 0.3, (0, 0, 1.25), g, seg=40, r2=0.11, bevel=0)
    cyl(0.11, 0.5, (0, 0, 1.6), g, seg=24, bevel=0.02)
    if state != "empty":
        cyl(0.31, 0.5, (0, 0, 0.55), mat("wine_label", (0.95, 0.9, 0.78), rough=0.6), seg=40, bevel=0)
        text("VINHO", (0, -0.32, 0.6), 0.11, mat("wine", (0.5, 0.12, 0.2)), rot=(math.radians(90), 0, 0))
    if state == "corked":
        cyl(0.12, 0.25, (0, 0, 1.9), mat("cap_w", (0.55, 0.12, 0.2), rough=0.3), seg=24, bevel=0.03)


def pitcher(full=False):
    glass = glassm()
    me = bpy.data.meshes.new("pitcher")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=0.5, radius2=0.45, depth=1.3)
    bottom = [v for v in bm.verts if v.co.z < 0]
    bm.faces.new(sorted(bottom, key=lambda v: math.atan2(v.co.y, v.co.x)))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("pitcher", me)
    o.location = (0, 0, 0.65)
    _link(o, glass)
    o.modifiers.new("Wall", "SOLIDIFY").thickness = 0.03
    torus(0.3, 0.05, (0.55, 0, 0.7), glass, rot=(math.radians(90), 0, 0))
    if full:
        cyl(0.48, 1.0, (0, 0, 0.52), mat("sangria", (0.6, 0.12, 0.18), rough=0.1, noise=0.05), seg=48, bevel=0)
        for k in range(5):
            sphere(0.13, (math.cos(k * 1.3) * 0.25, math.sin(k * 1.3) * 0.25, 1.0 + 0.02 * k), mat("apple_in", (0.98, 0.93, 0.75), rough=0.4), scale=(1, 0.6, 0.5))


def gift_box(full=False):
    box((2.4, 1.6, 0.4), (0, 0, 0.2), mat("gift", (0.45, 0.12, 0.2), rough=0.5), bevel=0.05)
    box((2.2, 1.4, 0.05), (0, 0, 0.38), mat("straw_fill", (0.9, 0.78, 0.45), rough=0.9, noise=0.2), bevel=0.01)
    if full:
        o = wine_bottle_lying()
        cyl(0.4, 0.2, (0.5, 0.2, 0.5), mat("minas", (0.98, 0.96, 0.9), rough=0.45), seg=40, bevel=0.05)
        for k in range(4):
            sphere(0.12, (0.4 + k * 0.18, -0.35, 0.48), mat("truffle", (0.35, 0.18, 0.1), rough=0.4))
        box((0.1, 1.62, 0.42), (-0.2, 0, 0.21), mat("ribbon", (0.95, 0.8, 0.3), rough=0.3, metal=0.4), bevel=0.01)


def wine_bottle_lying():
    g = mat("bottle_g", (0.15, 0.3, 0.15), rough=0.1, noise=0.03)
    cyl(0.22, 1.0, (-0.55, 0, 0.6), g, seg=32, bevel=0.05, rot=(0, math.radians(90), 0))
    cyl(0.08, 0.4, (0.1, 0, 0.6), g, seg=16, rot=(0, math.radians(90), 0))
    cyl(0.225, 0.4, (-0.55, 0, 0.6), mat("wine_label", (0.95, 0.9, 0.78), rough=0.6), seg=32, bevel=0, rot=(0, math.radians(90), 0))


def bench_bar(tile, name):
    """Drinks / ice cream / wine: a counter top and coloured tiles."""
    box((18, 13, 0.4), (0, -2.0, -0.2), mat("bench_" + name, (0.92, 0.9, 0.86), rough=0.3, noise=0.05), bevel=0.02)
    box((18, 0.3, 8), (0, 4.6, 3.8), mat("tiles_" + name, tile, rough=0.3, pattern="bricks", scale=1.2, noise=0.04, axis="xz"), bevel=0)
    box((18, 0.7, 0.12), (0, 4.15, 2.0), mat("shelf_w", (0.6, 0.4, 0.22), pattern="planks", scale=3), bevel=0.03)


def bench_adega():
    box((18, 13, 0.4), (0, -2.0, -0.2), mat("bench_adega", (0.5, 0.32, 0.2), rough=0.5, pattern="planks", scale=0.55, noise=0.12, wavy=0.2), bevel=0.02)
    box((18, 0.3, 8), (0, 4.6, 3.8), mat("brick_adega", (0.62, 0.3, 0.22), rough=0.6, pattern="bricks", scale=1.6, noise=0.1, axis="xz"), bevel=0)
    for x in (-6.5, -4.0, 4.0, 6.5):
        barrel(x, 3.8, 0.0, 3.0, lying=True)


# ---------------------------------------------------------------- render lists
PROPS = {
    "padaria": {
        "kt_bowl": (lambda: bowl(1.0, 0.55), 2.4),
        "kt_dough_rough": (lambda: dough_ball("rough"), 2.0),
        "kt_dough_smooth": (lambda: dough_ball("smooth"), 2.0),
        "kt_dough_risen": (lambda: dough_ball("risen"), 2.0),
        "kt_baguette_raw": (lambda: baguette("raw"), 3.0),
        "kt_baguette_scored": (lambda: baguette("scored"), 3.0),
        "kt_baguette_baked": (lambda: baguette("baked"), 3.0),
        "kt_croissant_raw": (lambda: croissant("raw"), 1.7),
        "kt_croissant_baked": (lambda: croissant("baked"), 1.7),
        "kt_cake_batter": (lambda: cake("batter"), 2.4),
        "kt_cake_baked": (lambda: cake("baked"), 2.4),
        "kt_cake_done": (lambda: cake("done"), 2.4),
        "kt_oven": (oven, 4.0),
        "kt_tray": (lambda: tray(), 3.4),
        "kt_water": (jug, 1.6),
        "kt_yeast": (yeast_pack, 1.5),
        "kt_salt": (lambda: jar((0.25, 0.5, 0.72), "SAL"), 1.3),
        "kt_dough_sheet": (dough_sheet, 3.0),
        "kt_blade": (blade, 1.4),
        "kt_whisk": (whisk, 1.6),
    },
}
PROPS["queijaria"] = {
    "kt_pot_milk": (lambda: pot("milk"), 2.6),
    "kt_pot_gel": (lambda: pot("gel"), 2.6),
    "kt_pot_curd": (lambda: pot("curd"), 2.6),
    "kt_culture": (lambda: bottle("FERMENTO", (0.3, 0.6, 0.35), cap=(0.95, 0.95, 0.95)), 1.4),
    "kt_calcium": (lambda: bottle("CLORETO", (0.25, 0.45, 0.75)), 1.4),
    "kt_rennet": (lambda: bottle("COALHO", (0.75, 0.25, 0.2), small=True), 1.2),
    "kt_penicillium": (lambda: bottle("MOFO", (0.55, 0.55, 0.6), cap=(0.95, 0.95, 0.95), small=True), 1.2),
    "kt_ladle": (ladle, 1.9),
    "kt_lira": (lira, 2.4),
    "kt_molds": (lambda: molds(), 3.0),
    "kt_molds_full": (lambda: molds(full=True), 3.0),
    "kt_cheese_minas": (lambda: molds(cheese=True), 3.0),
    "kt_curd_scoop": (curd_scoop, 1.0),
    "kt_cheese_fresh": (lambda: wheel("fresh"), 2.1),
    "kt_cheese_brie": (lambda: wheel("brie"), 2.1),
    "kt_cheese_wedge": (cheese_wedge, 1.2),
    "kt_board": (lambda: board(), 2.8),
    "kt_cheese_board": (lambda: board(True), 2.8),
}
PROPS["acougue"] = {
    "kt_meat_raw": (lambda: meat_piece(), 2.4),
    "kt_meat_clean": (lambda: meat_piece(trimmed=True), 2.4),
    "kt_meat_aged": (lambda: meat_piece(trimmed=True, aged=True), 2.4),
    "kt_grinder": (lambda: grinder(), 3.4),
    "kt_grinder_full": (lambda: grinder(True), 3.4),
    "kt_patty_ball": (lambda: patty(False), 0.9),
    "kt_patty": (lambda: patty(True), 1.2),
    "kt_scale": (lambda: scale_with(True), 2.0),
    "kt_tray_foam": (lambda: foam_tray(), 2.6),
    "kt_tray_patties": (lambda: foam_tray("patties"), 2.6),
    "kt_tray_steaks": (lambda: foam_tray("steaks"), 2.6),
    "kt_aging_cabinet": (aging_cabinet, 3.6),
    "kt_steaks": (steaks, 2.4),
    "kt_steak": (lambda: lump([((0, 0, 0.12), 0.38, (0.85, 1.25, 0.3))], beef(), voxel=0.02), 1.2),
    "kt_picanha": (lambda: picanha(), 2.6),
    "kt_picanha_piece": (lambda: picanha(True), 0.9),
    "kt_skewer": (lambda: skewer(), 3.0),
    "kt_skewer_full": (lambda: skewer(True), 3.0),
    "kt_bbq_box": (lambda: bbq_box(), 2.8),
    "kt_bbq_box_full": (lambda: bbq_box(True), 2.8),
    "kt_cleaver": (cleaver, 1.4),
}
PROPS["peixaria"] = {
    "kt_fish_whole": (lambda: fish("whole"), 3.4),
    "kt_fish_scaled": (lambda: fish("scaled"), 3.4),
    "kt_fish_open": (lambda: fish("open"), 3.4),
    "kt_fillets": (lambda: fillets(), 2.4),
    "kt_fillet_bones": (lambda: fillets(bones=True), 2.4),
    "kt_ice_tray": (lambda: fillets(ice=True) if False else ice_tray(), 2.8),
    "kt_ice_tray_full": (lambda: fillets(ice=True), 2.8),
    "kt_fillet": (lambda: lump([((x, 0, 0.08), 0.3 * (1 - abs(x) * 0.35), (1.0, 0.6, 0.3)) for x in [k * 0.1 - 0.85 for k in range(18)]], mat("fillet", (0.97, 0.75, 0.62), rough=0.3, noise=0.08), voxel=0.025), 2.0),
    "kt_scaler": (scaler, 1.3),
    "kt_tweezers": (tweezers, 1.2),
    "kt_fish_knife": (fish_knife, 1.6),
    "kt_rice_tub": (lambda: rice_tub(False), 2.4),
    "kt_rice_seasoned": (lambda: rice_tub(True), 2.4),
    "kt_vinegar": (lambda: bottle("VINAGRE", (0.85, 0.2, 0.2), cap=(0.15, 0.15, 0.15)), 1.4),
    "kt_salmon_block": (lambda: salmon(False), 2.2),
    "kt_salmon_slices": (lambda: salmon(True), 2.8),
    "kt_makisu": (lambda: makisu(False), 2.4),
    "kt_sushi_roll": (lambda: makisu(True), 2.4),
    "kt_sushi_plate": (lambda: sushi_plate(False, False), 2.8),
    "kt_sushi_plate_full": (lambda: sushi_plate(False, True), 2.8),
    "kt_sushi_boat": (lambda: sushi_plate(True, False), 3.2),
    "kt_sushi_boat_full": (lambda: sushi_plate(True, True), 3.2),
    "kt_sushi_piece": (sushi_piece, 0.9),
    "kt_shrimp": (shrimp, 1.1),
}
PROPS["bebidas"] = {
    "kt_fruit_bowl": (lambda: fruit_bowl(False), 2.4),
    "kt_fruit_washed": (lambda: fruit_bowl(True), 2.4),
    "kt_apple": (lambda: apple_board(False), 2.0),
    "kt_apple_sliced": (lambda: apple_board(True), 2.0),
    "kt_blender": (lambda: blender_jar(), 2.8),
    "kt_blender_fruit": (lambda: blender_jar((0.95, 0.8, 0.45)), 2.8),
    "kt_blender_juice": (lambda: blender_jar((0.98, 0.75, 0.35), True), 2.8),
    "kt_blender_smoothie": (lambda: blender_jar((0.98, 0.9, 0.75), True), 2.8),
    "kt_glass": (lambda: drink_glass(None), 2.3),
    "kt_glass_juice": (lambda: drink_glass((0.98, 0.72, 0.3)), 2.3),
    "kt_glass_tea": (lambda: drink_glass((0.7, 0.38, 0.12)), 2.3),
    "kt_glass_smoothie": (lambda: drink_glass((0.98, 0.9, 0.75), ice=False), 2.3),
    "kt_kettle": (kettle, 1.9),
    "kt_tea": (tea_jar, 1.3),
    "kt_ice_bucket": (ice_bucket, 1.8),
    "kt_ice_cube": (ice_cube, 0.8),
}
PROPS["sorvetes"] = {
    "kt_churner": (lambda: churner(False), 2.2),
    "kt_churner_full": (lambda: churner(True), 2.2),
    "kt_scoop": (lambda: scoop_ball(), 1.0),
    "kt_scoop_choc": (lambda: scoop_ball((0.42, 0.22, 0.12)), 1.0),
    "kt_ice_pot": (lambda: ice_pot(), 1.6),
    "kt_ice_pot_full": (lambda: ice_pot(True), 1.6),
    "kt_family_pot": (lambda: ice_pot(False, True), 2.0),
    "kt_family_pot_full": (lambda: ice_pot(True, True), 2.0),
    "kt_sundae": (lambda: sundae(False), 2.0),
    "kt_sundae_full": (lambda: sundae(True), 2.0),
}
PROPS["adega"] = {
    "kt_grape_tub": (lambda: grape_tub(False), 2.6),
    "kt_grape_crushed": (lambda: grape_tub(True), 2.6),
    "kt_press": (lambda: wine_press(False), 2.6),
    "kt_press_full": (lambda: wine_press(True), 2.6),
    "kt_barrel": (wine_barrel, 2.6),
    "kt_bottle_empty": (lambda: wine_bottle("empty"), 2.4),
    "kt_bottle_full": (lambda: wine_bottle("full"), 2.4),
    "kt_bottle_corked": (lambda: wine_bottle("corked"), 2.4),
    "kt_pitcher": (lambda: pitcher(False), 2.2),
    "kt_pitcher_full": (lambda: pitcher(True), 2.2),
    "kt_gift_box": (lambda: gift_box(False), 2.8),
    "kt_gift_box_full": (lambda: gift_box(True), 2.8),
}
BENCHES = {"padaria": bench_padaria, "queijaria": bench_queijaria, "acougue": bench_acougue, "peixaria": bench_peixaria,
           "bebidas": lambda: bench_bar((0.98, 0.78, 0.45), "bebidas"), "sorvetes": lambda: bench_bar((0.98, 0.78, 0.86), "sorvetes"), "adega": bench_adega}


def render_sector(sector, only=None):
    os.makedirs(KOUT, exist_ok=True)
    sc = kscene()
    for name, (build, size) in PROPS[sector].items():
        if only and name not in only:
            continue
        kcoll("KitchenArt_" + name)
        build()
        bpy.context.view_layer.update()
        # Aim at the middle of what was built (tall things like glasses and blenders stay in frame).
        pts = [o.matrix_world @ Vector(c) for o in CUR["c"].objects if o.type == "MESH" for c in o.bound_box]
        if pts:
            lo = Vector([min(p[i] for p in pts) for i in range(3)])
            hi = Vector([max(p[i] for p in pts) for i in range(3)])
            aim(size, ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, (lo.z + hi.z) / 2))
        else:
            aim(size, (0, 0, 0.2))
        sc.render.filepath = os.path.join(KOUT, name + ".png")
        bpy.ops.render.render(write_still=True)
    if not only or "bench" in only:
        kcoll("KitchenArt_bench_" + sector)
        BENCHES[sector]()
        aim(16.0, (0, 1.2, 0.0), res=(1600, 900))
        sc.render.film_transparent = False
        sc.render.filepath = os.path.join(KOUT, "kt_bench_" + sector + ".png")
        bpy.ops.render.render(write_still=True)
        sc.render.film_transparent = True
