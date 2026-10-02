"""care_spots.py -- little mess sprites of the shelf care game (wilted leaf, frost, crumbs, smudge).
Rendered 256x256 RGBA to ArtSource/Review/care/<name>.png."""
import bpy, bmesh, math, os, random

OUT = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\care"
SC = "CareSpots"


def scene():
    sc = bpy.data.scenes.get(SC) or bpy.data.scenes.new(SC)
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x = r.resolution_y = 256
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.device = "GPU"
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.get("Care_World") or bpy.data.worlds.new("Care_World")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.22
    sc.world = w
    c = bpy.data.collections.get("CS_Root") or bpy.data.collections.new("CS_Root")
    if c.name not in [x.name for x in sc.collection.children]:
        sc.collection.children.link(c)
    cam = bpy.data.objects.get("CS_Cam")
    if cam is None:
        cam = bpy.data.objects.new("CS_Cam", bpy.data.cameras.new("CS_Cam"))
        c.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.55
    cam.location = (0, -6, 4)
    cam.rotation_euler = (math.radians(56), 0, 0)
    sc.camera = cam
    l = bpy.data.objects.get("CS_Key")
    if l is None:
        l = bpy.data.objects.new("CS_Key", bpy.data.lights.new("CS_Key", "AREA"))
        c.objects.link(l)
    l.data.energy = 420
    l.data.size = 3
    l.location = (-2, -3, 5)
    l.rotation_euler = (math.radians(40), math.radians(-20), 0)
    return sc


def mat(name, color, rough=0.5, alpha=1.0, transmission=0.0, coat=0.0):
    m = bpy.data.materials.get("CS_" + name) or bpy.data.materials.new("CS_" + name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Alpha"].default_value = alpha
    try:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["Coat Weight"].default_value = coat
    except KeyError:
        pass
    return m


def coll(name):
    sc = scene()
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in [x.name for x in sc.collection.children]:
        sc.collection.children.link(c)
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return c


def obj(c, name, me, loc, rot=(0, 0, 0), scale=(1, 1, 1), m=None):
    o = bpy.data.objects.new(name, me)
    o.location, o.rotation_euler, o.scale = loc, rot, scale
    if m:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    c.objects.link(o)
    return o


def sphere_mesh(name, r=0.5, seg=24, ring=12):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def ico_mesh(name, r=0.5, sub=1):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def wilted(c):
    random.seed(4)
    for i, (x, y, rz, col) in enumerate(((-0.2, 0, 0.4, (0.36, 0.30, 0.07)), (0.25, 0.1, -0.6, (0.27, 0.27, 0.06)), (0.0, -0.25, 1.4, (0.42, 0.24, 0.06)))):
        o = obj(c, "leaf%d" % i, sphere_mesh("leaf%d" % i), (x, y, 0.05), (0, 0.15, rz), (0.55, 0.22, 0.05), mat("leaf%d" % i, col, 0.7))
        bend = o.modifiers.new("b", "SIMPLE_DEFORM")
        bend.deform_method = "BEND"
        bend.angle = math.radians(70)
        bend.deform_axis = "Y"
        tw = o.modifiers.new("t", "SIMPLE_DEFORM")
        tw.deform_method = "TWIST"
        tw.angle = math.radians(40)
    obj(c, "spot", sphere_mesh("spot"), (0.05, 0.05, -0.05), (0, 0, 0), (0.7, 0.6, 0.02), mat("damp", (0.25, 0.2, 0.1), 0.3, alpha=0.5))


def frost(c):
    random.seed(9)
    ice = mat("ice", (0.88, 0.95, 1.0), 0.15, transmission=0.4, coat=0.6)
    snow = mat("snow", (0.96, 0.98, 1.0), 0.7)
    obj(c, "base", sphere_mesh("base"), (0, 0, 0), (0, 0, 0), (0.8, 0.65, 0.12), snow)
    for i in range(9):
        a = random.uniform(0, math.tau)
        rr = random.uniform(0.1, 0.55)
        obj(c, "shard%d" % i, ico_mesh("shard%d" % i, 0.18), (math.cos(a) * rr, math.sin(a) * rr * 0.8, 0.12),
            (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3)), (random.uniform(0.6, 1.2), 0.5, random.uniform(0.8, 1.6)), ice)


def crumbs(c):
    random.seed(12)
    for i in range(14):
        a = random.uniform(0, math.tau)
        rr = random.uniform(0.0, 0.6)
        col = random.choice(((0.78, 0.55, 0.28), (0.66, 0.42, 0.2), (0.88, 0.7, 0.42)))
        s = random.uniform(0.06, 0.16)
        obj(c, "crumb%d" % i, ico_mesh("crumb%d" % i, 1, 1), (math.cos(a) * rr, math.sin(a) * rr * 0.8, s * 0.5),
            (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3)), (s, s * 0.8, s * 0.6), mat("crumb%d" % (i % 3), col, 0.8))


def smudge(c):
    m = mat("smudge", (0.55, 0.6, 0.65), 0.4, alpha=0.45)
    for i in range(5):
        r = 0.18 + i * 0.12
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=False, segments=32, radius=r)
        me = bpy.data.meshes.new("ring%d" % i)
        bm.to_mesh(me)
        bm.free()
        o = obj(c, "ring%d" % i, me, (0, 0, 0), (0, 0, 0.3 * i), (1, 0.8, 1), m)
        sk = o.modifiers.new("s", "SKIN")
        for v in o.data.skin_vertices[0].data:
            v.radius = (0.035, 0.035)


BUILD = {"wilted": wilted, "frost": frost, "crumbs": crumbs}


def render_all():
    os.makedirs(OUT, exist_ok=True)
    sc = scene()
    out = []
    for name, fn in BUILD.items():
        c = coll("CS_" + name)
        fn(c)
        for x in sc.collection.children:
            if x.name.startswith("CS_") and x.name != "CS_Root":
                x.hide_render = x.name != "CS_" + name
        sc.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True, scene=sc.name)
        out.append(sc.render.filepath)
    return out
