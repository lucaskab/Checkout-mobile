"""
lane_art.py  --  Checkout - Supermercado Simulator
Art for the delivery lanes of the Entregas window (CheckoutDesktopHUD.Lanes.cs): where each truck comes
from (the supplier for the product's category), the supermarket it drives to and the trucks seen from the side.

Every place is a small diorama on a round patch of grass, seen from the front and a little from above, in the
palette of the supplied map models (terracotta roofs, teal trims, cream walls). The trucks are the game's own
models (DeliveryTruck / FishDeliveryTruck / IceCreamTruck) seen from the side, cab to the right.

Usage in Blender:
  exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\lane_art.py").read())
  render_all()                 # or render(["fazenda"]) / render_trucks()
Output: ArtSource/Review/lane/<name>.png (512 x 420, transparent); copy to Resources/CheckoutDesktop/Game/lane_<name>.png
"""
import bpy, bmesh, math, os, random
from mathutils import Vector

SCENE = "LaneArt"
MODELS = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\MapModels"
OUT = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\lane"
RES = (512, 420)

PAL = {
    "roof": (0.86, 0.42, 0.24), "roof_dark": (0.62, 0.27, 0.15), "teal": (0.16, 0.52, 0.5), "teal_dark": (0.09, 0.34, 0.34),
    "cream": (0.95, 0.89, 0.76), "wall_y": (0.98, 0.8, 0.45), "wood": (0.55, 0.34, 0.18), "wood_l": (0.74, 0.52, 0.3),
    "glass": (0.36, 0.62, 0.72), "dark": (0.16, 0.13, 0.11), "white": (0.94, 0.94, 0.92), "red": (0.82, 0.22, 0.17),
    "brick": (0.72, 0.33, 0.22), "grass": (0.42, 0.68, 0.27), "grass_d": (0.3, 0.55, 0.2), "soil": (0.5, 0.33, 0.2),
    "steel": (0.72, 0.75, 0.78), "water": (0.22, 0.58, 0.78), "leaf": (0.33, 0.62, 0.2), "grape": (0.45, 0.2, 0.45),
    "wheat": (0.93, 0.75, 0.32), "sky_blue": (0.55, 0.78, 0.9), "path": (0.86, 0.76, 0.58),
}


# ---------------------------------------------------------------- scene
def scene():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = sc
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y, r.resolution_percentage = RES[0], RES[1], 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    try:
        sc.cycles.device = "GPU"
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.05
    w = bpy.data.worlds.get("LaneArt_World") or bpy.data.worlds.new("LaneArt_World")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1.0, 0.96, 0.9, 1)
    bg.inputs[1].default_value = 0.42
    sc.world = w
    if "LaneArt_Cam" not in bpy.data.objects:
        cd = bpy.data.cameras.new("LaneArt_Cam")
        cam = bpy.data.objects.new("LaneArt_Cam", cd)
        sc.collection.objects.link(cam)
        sun = bpy.data.lights.new("LaneArt_Sun", "SUN")
        sun.energy = 3.8
        sun.angle = math.radians(8)
        so = bpy.data.objects.new("LaneArt_Sun", sun)
        sc.collection.objects.link(so)
        so.rotation_euler = (math.radians(48), math.radians(12), math.radians(-38))
    bpy.data.lights["LaneArt_Sun"].energy = 3.8
    sc.camera = bpy.data.objects["LaneArt_Cam"]
    return sc


def coll(name):
    sc = scene()
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
    return c


CUR = {"c": None}
MATS = {}


def mat(key, color=None, rough=0.6, metal=0.0, noise=0.08, emit=0.0, pattern=None, scale=8.0, axis="xy", wavy=0.6):
    """Painted material: soft noise variation and a little bump; pattern adds planks, bricks or roof tiles."""
    name = "LA_" + key
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    col = color if color is not None else PAL.get(key, (0.8, 0.8, 0.8))
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*col, 1)
        b.inputs["Emission Strength"].default_value = emit
    coord = nt.nodes.new("ShaderNodeTexCoord")
    vec = coord.outputs["Object"]
    if axis == "xz":
        # Patterns on walls (x across, z up) instead of floors.
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
        nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])
        vec = mp.outputs["Vector"]
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 9.0
    tex.inputs["Detail"].default_value = 4.0
    nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    dark = tuple(max(0, c * (1 - max(noise, 0.02) * 1.6)) for c in col)
    light = tuple(min(1, c * (1 + max(noise, 0.02))) for c in col)
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[1].position = 0.75
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    base = ramp.outputs["Color"]
    height = tex.outputs["Fac"]
    if pattern in ("bricks", "tiles"):
        br = nt.nodes.new("ShaderNodeTexBrick")
        nt.links.new(vec, br.inputs["Vector"])
        br.inputs["Scale"].default_value = scale
        br.inputs["Mortar Size"].default_value = 0.025 if pattern == "bricks" else 0.04
        br.inputs["Brick Width"].default_value = 0.5 if pattern == "bricks" else 0.3
        br.inputs["Row Height"].default_value = 0.25 if pattern == "bricks" else 0.2
        mortar = tuple(c * (0.55 if pattern == "tiles" else 1.25) for c in col)
        nt.links.new(ramp.outputs["Color"], br.inputs["Color1"])
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.inputs["Fac"].default_value = 0.5
        nt.links.new(ramp.outputs["Color"], mix.inputs["Color1"])
        mix.inputs["Color2"].default_value = (*[c * 0.85 for c in col], 1)
        nt.links.new(mix.outputs["Color"], br.inputs["Color2"])
        br.inputs["Mortar"].default_value = (*[min(1, c) for c in mortar], 1)
        base = br.outputs["Color"]
        height = br.outputs["Fac"]
    elif pattern == "planks":
        wv = nt.nodes.new("ShaderNodeTexWave")
        nt.links.new(vec, wv.inputs["Vector"])
        wv.wave_profile = "SAW"
        wv.inputs["Scale"].default_value = scale
        wv.inputs["Distortion"].default_value = wavy
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].position = 0.06
        cr.color_ramp.elements[0].color = (0.62, 0.62, 0.62, 1)
        cr.color_ramp.elements[1].position = 0.1
        cr.color_ramp.elements[1].color = (1, 1, 1, 1)
        nt.links.new(wv.outputs["Fac"], cr.inputs["Fac"])
        mix.inputs["Fac"].default_value = 1.0
        nt.links.new(ramp.outputs["Color"], mix.inputs["Color1"])
        nt.links.new(cr.outputs["Color"], mix.inputs["Color2"])
        base = mix.outputs["Color"]
        height = cr.outputs["Color"]
    nt.links.new(base, b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25 if pattern else 0.08
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    MATS[name] = m
    return m


def roofmat(key):
    return mat("tiles_" + key, PAL[key], rough=0.7, noise=0.1, pattern="tiles", scale=7)


def _link(o, m, bevel=0.0, seg=3):
    CUR["c"].objects.link(o)
    if m is not None:
        o.data.materials.append(m if not isinstance(m, str) else mat(m))
    if bevel:
        bv = o.modifiers.new("Bevel", "BEVEL")
        bv.width = bevel
        bv.segments = seg
        bv.limit_method = "ANGLE"
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def box(size, loc, m, bevel=0.03, rot=(0, 0, 0), name="box"):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = loc
    o.rotation_euler = rot
    _link(o, m, bevel)
    if bevel:
        o.data.polygons.foreach_set("use_smooth", [False] * len(o.data.polygons))
        o.modifiers["Bevel"].harden_normals = False
    return o


def cyl(r, h, loc, m, seg=32, r2=None, bevel=0.02, rot=(0, 0, 0), name="cyl"):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = loc
    o.rotation_euler = rot
    _link(o, m, bevel)
    return o


def sphere(r, loc, m, scale=(1, 1, 1), name="sph"):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=r)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = loc
    o.scale = scale
    _link(o, m)
    return o


def torus(r, t, loc, m, rot=(0, 0, 0), name="tor"):
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=t, location=loc, rotation=rot, major_segments=32, minor_segments=12)
    o = bpy.context.active_object
    for c in o.users_collection:
        c.objects.unlink(o)
    _link(o, m)
    return o


def gable(w, d, h, loc, m, over=0.08, thick=0.06, name="roof"):
    """A pitched roof along x: width w (x), depth d (y), ridge height h above loc (eaves at loc z)."""
    x0, x1 = -w / 2 - over, w / 2 + over
    y0, y1 = -d / 2 - over, d / 2 + over
    verts = [(x0, y0, 0), (x0, y1, 0), (x0, 0, h), (x1, y0, 0), (x1, y1, 0), (x1, 0, h)]
    faces = [(0, 1, 2), (3, 5, 4), (0, 2, 5, 3), (1, 4, 5, 2), (0, 3, 4, 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    o.location = loc
    _link(o, m)
    s = o.modifiers.new("Solid", "SOLIDIFY")
    s.thickness = thick
    bv = o.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.02
    bv.segments = 2
    return o


def gable_wall(w, d, h, loc, m, name="gablewall"):
    """The triangle that closes a pitched roof (front and back)."""
    verts = []
    faces = []
    for i, y in enumerate((-d / 2, d / 2)):
        verts += [(-w / 2, y, 0), (w / 2, y, 0), (0, y, h)]
    faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    o.location = loc
    o.rotation_euler = (0, 0, math.radians(90))
    _link(o, m)
    return o


def text(body, loc, size, m, extrude=0.012, rot=(math.radians(90), 0, 0), name="txt"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    for f in ("C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(f):
            cu.font = bpy.data.fonts.load(f, check_existing=True)
            break
    o = bpy.data.objects.new(name, cu)
    o.location = loc
    o.rotation_euler = rot
    CUR["c"].objects.link(o)
    o.data.materials.append(m if not isinstance(m, str) else mat(m))
    return o


def glb(name, loc, height=None, width=None, rot=0.0):
    """One of the supplied map models, scaled to a height (or width) and set on the ground at loc."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, name + ".glb"))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        CUR["c"].objects.link(o)
    o = [x for x in new if x.type == "MESH"][0]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector([min(p[i] for p in pts) for i in range(3)])
    mx = Vector([max(p[i] for p in pts) for i in range(3)])
    size = mx - mn
    s = height / size.z if height else width / max(size.x, size.y)
    o.scale = (o.scale[0] * s, o.scale[1] * s, o.scale[2] * s)
    o.rotation_euler = (o.rotation_euler[0], o.rotation_euler[1], o.rotation_euler[2] + rot)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector([min(p[i] for p in pts) for i in range(3)])
    mx = Vector([max(p[i] for p in pts) for i in range(3)])
    o.location += Vector(loc) - Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    return o


# ---------------------------------------------------------------- shared pieces
def ground(r=1.85, path=True):
    g = cyl(r, 0.16, (0, 0, -0.08), "grass", seg=64, bevel=0.06, name="ground")
    cyl(r + 0.04, 0.14, (0, 0, -0.17), mat("soil_edge", (0.52, 0.33, 0.19)), seg=64, bevel=0.04, name="ground_edge")
    rnd = random.Random(4)
    flowers = [(0.95, 0.85, 0.3), (0.95, 0.45, 0.55), (1.0, 1.0, 0.95), (0.6, 0.5, 0.9)]
    for i in range(26):
        a = rnd.uniform(0, math.tau)
        rr = rnd.uniform(1.25, r - 0.12)
        x, y = math.cos(a) * rr, math.sin(a) * rr
        k = rnd.random()
        if k < 0.35:
            sphere(rnd.uniform(0.08, 0.13), (x, y, 0.04), mat("bush", PAL["grass_d"]), scale=(1, 1, 0.75))
        elif k < 0.7:
            f = flowers[i % len(flowers)]
            cyl(0.008, 0.08, (x, y, 0.04), "grass_d", seg=6, bevel=0)
            sphere(0.03, (x, y, 0.09), mat("flower%d" % (i % len(flowers)), f, rough=0.5))
        elif k < 0.85:
            sphere(rnd.uniform(0.04, 0.07), (x, y, 0.01), mat("stone", (0.68, 0.66, 0.62)), scale=(1.3, 1, 0.6))
        else:
            for t in range(3):
                cyl(0.018, 0.09, (x + t * 0.025, y, 0.04), "grass_d", seg=6, r2=0.0, bevel=0, rot=(0, (t - 1) * 0.3, 0))
    return g


def window(x, y, z, w=0.26, h=0.3, frame="cream", face_y=True):
    box((w + 0.06, 0.04, h + 0.06), (x, y - 0.01, z), frame, bevel=0.012)
    box((w, 0.05, h), (x, y - 0.02, z), mat("glass", PAL["glass"], rough=0.15, noise=0.02), bevel=0.008)
    box((0.025, 0.06, h), (x, y - 0.03, z), frame, bevel=0.0)
    box((w, 0.06, 0.025), (x, y - 0.03, z), frame, bevel=0.0)


def door(x, y, z0, w=0.34, h=0.52, m="teal"):
    box((w + 0.06, 0.05, h + 0.04), (x, y - 0.005, z0 + h / 2), "cream", bevel=0.012)
    box((w, 0.06, h), (x, y - 0.02, z0 + h / 2), m, bevel=0.015)
    sphere(0.025, (x + w * 0.32, y - 0.06, z0 + h * 0.48), mat("knob", (0.9, 0.75, 0.3), rough=0.3, metal=0.6, noise=0))


def tree(x, y, s=1.0):
    cyl(0.06 * s, 0.45 * s, (x, y, 0.22 * s), "wood", seg=12, name="trunk")
    for dx, dy, dz, r in ((0, 0, 0.62, 0.32), (0.16, 0.05, 0.5, 0.22), (-0.15, -0.04, 0.52, 0.24), (0.02, -0.1, 0.8, 0.22)):
        sphere(r * s, (x + dx * s, y + dy * s, dz * s), mat("leaf", PAL["leaf"]), scale=(1, 1, 0.9))


def fence(x0, x1, y, h=0.22):
    n = max(2, int(abs(x1 - x0) / 0.22) + 1)
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        box((0.04, 0.04, h), (x, y, h / 2), "white", bevel=0.008)
    for z in (h * 0.4, h * 0.8):
        box((abs(x1 - x0) + 0.04, 0.025, 0.035), ((x0 + x1) / 2, y, z), "white", bevel=0.005)


def crate(x, y, z=0.0, s=0.22, fill=None):
    box((s * 1.4, s, s * 0.7), (x, y, z + s * 0.35), "wood_l", bevel=0.01)
    if fill:
        for i in range(5):
            sphere(s * 0.18, (x - s * 0.5 + i * s * 0.25, y + (i % 2) * 0.03, z + s * 0.72), mat("fill_" + str(fill), fill, rough=0.4), scale=(1, 1, 0.9))


def barrel(x, y, z=0.0, s=1.0, lying=False):
    rot = (math.radians(90), 0, 0) if lying else (0, 0, 0)
    zc = z + (0.13 * s if lying else 0.17 * s)
    cyl(0.13 * s, 0.34 * s, (x, y, zc), "wood", seg=24, r2=0.13 * s, rot=rot, name="barrel")
    for k in (-0.11, 0.11):
        off = Vector((0, k * s, 0)) if lying else Vector((0, 0, k * s))
        cyl(0.135 * s, 0.03 * s, Vector((x, y, zc)) + off, mat("hoop", (0.3, 0.28, 0.27), metal=0.5, noise=0), seg=24, rot=rot, name="hoop")


def smoke(x, y, z, n=3):
    for i in range(n):
        sphere(0.09 + i * 0.04, (x + i * 0.08, y, z + i * 0.17), mat("smoke", (0.97, 0.97, 0.96), rough=0.9, noise=0.02))


# ---------------------------------------------------------------- the places
def fazenda():
    ground()
    # Red barn with white trims.
    box((1.3, 0.95, 0.75), (-0.25, 0.35, 0.375), mat("barn", (0.78, 0.2, 0.16), pattern="planks", scale=14), bevel=0.02)
    gable_wall(0.95, 1.3, 0.42, (-0.25, 0.35, 0.75), mat("barn", (0.78, 0.2, 0.16), pattern="planks", scale=14))
    gable(1.3, 0.95, 0.45, (-0.25, 0.35, 0.74), roofmat("roof_dark"))
    door(-0.25, -0.13, 0.0, w=0.46, h=0.56, m=mat("barn_door", (0.62, 0.15, 0.12)))
    for s in (1, -1):
        box((0.6, 0.03, 0.04), (-0.25, -0.17, 0.28), "white", bevel=0.005, rot=(0, s * math.radians(50), 0))
    window(-0.25, -0.12, 0.98, w=0.2, h=0.18, frame="white")
    # Silo.
    cyl(0.2, 1.05, (0.65, 0.55, 0.52), "steel", seg=32, bevel=0.0)
    sphere(0.2, (0.65, 0.55, 1.05), "teal", scale=(1, 1, 0.6))
    # Crop rows and crates in front.
    for i in range(3):
        box((0.95, 0.16, 0.06), (0.95 - 0.05 * i, -0.45 - 0.3 * i, 0.03), "soil", bevel=0.02)
        for j in range(5):
            sphere(0.075, (0.58 + j * 0.19 - 0.05 * i, -0.45 - 0.3 * i, 0.1), mat("crop", (0.36, 0.7, 0.22)), scale=(1, 1, 0.8))
    crate(-1.05, -0.55, fill=(0.85, 0.2, 0.15))
    crate(-0.75, -0.75, fill=(0.95, 0.55, 0.15))
    tree(-1.35, 0.6, 0.95)


def laticinio():
    ground()
    box((1.45, 0.9, 0.72), (-0.15, 0.35, 0.36), "cream", bevel=0.02)
    box((1.47, 0.92, 0.1), (-0.15, 0.35, 0.05), "teal", bevel=0.01)
    gable(1.45, 0.9, 0.4, (-0.15, 0.35, 0.71), roofmat("teal"))
    gable_wall(0.9, 1.45, 0.38, (-0.15, 0.35, 0.72), "cream")
    door(-0.15, -0.1, 0.0)
    window(-0.62, -0.1, 0.44)
    window(0.32, -0.1, 0.44)
    # A milk sign: a white bottle on a blue plate.
    box((0.5, 0.05, 0.22), (-0.15, -0.12, 0.88), mat("sign_blue", (0.2, 0.45, 0.75)), bevel=0.02)
    text("LEITE", (-0.15, -0.16, 0.88), 0.13, "white")
    # Milk tank.
    cyl(0.24, 1.15, (0.92, 0.5, 0.58), "white", seg=32, bevel=0.0)
    for z in (0.3, 0.75):
        cyl(0.245, 0.06, (0.92, 0.5, z), mat("band", (0.2, 0.45, 0.75)), seg=32)
    sphere(0.24, (0.92, 0.5, 1.15), "white", scale=(1, 1, 0.5))
    # The cow by the fence.
    glb("Cow", (0.75, -0.75, 0.0), height=0.6, rot=math.radians(-30))
    fence(-1.4, -0.4, -0.95)
    tree(-1.35, 0.75, 0.9)


def frigorifico():
    ground()
    box((1.7, 1.0, 0.85), (0, 0.35, 0.425), "white", bevel=0.03)
    box((1.72, 1.02, 0.12), (0, 0.35, 0.79), "red", bevel=0.02)
    box((1.6, 0.9, 0.04), (0, 0.35, 0.86), mat("roofcap", (0.8, 0.8, 0.78)), bevel=0.01)
    box((1.72, 1.02, 0.08), (0, 0.35, 0.04), mat("plinth", (0.6, 0.62, 0.66)), bevel=0.01)
    # Insulated loading door with a ribbed panel and dock bumper.
    box((0.62, 0.06, 0.6), (-0.35, -0.16, 0.3), mat("coldoor", (0.75, 0.82, 0.88)), bevel=0.015)
    for i in range(5):
        box((0.6, 0.07, 0.015), (-0.35, -0.17, 0.08 + i * 0.11), mat("coldrib", (0.62, 0.7, 0.78)), bevel=0.0)
    box((0.7, 0.12, 0.08), (-0.35, -0.2, 0.62), "dark", bevel=0.01)
    door(0.45, -0.15, 0.0, w=0.3, h=0.48, m="steel")
    window(0.45, -0.15, 0.66, w=0.3, h=0.16)
    # Sign and cooling units on the roof.
    box((0.95, 0.06, 0.24), (0, -0.18, 1.0), "red", bevel=0.02)
    text("CARNES", (0, -0.22, 1.0), 0.15, "white")
    for x in (-0.45, 0.45):
        box((0.42, 0.34, 0.2), (x, 0.5, 0.95), "steel", bevel=0.02)
        cyl(0.12, 0.03, (x, 0.5, 1.06), "dark", seg=24)
        cyl(0.04, 0.035, (x, 0.5, 1.07), "steel", seg=12)
    # Ice-blue snowflake badge.
    sphere(0.11, (0.85, -0.15, 0.62), mat("frost", (0.55, 0.85, 0.98), rough=0.2), scale=(1, 0.3, 1))
    tree(-1.35, 0.75, 0.85)
    tree(1.35, 0.6, 0.75)


def porto():
    g = ground(path=False)
    # Water on the front half, wooden pier, the fishing boat.
    cyl(1.55, 0.06, (0.35, -0.55, 0.03), mat("water", PAL["water"], rough=0.08, noise=0.05), seg=48, bevel=0.03)
    for i in range(8):
        box((0.16, 0.95, 0.04), (-0.55 + i * 0.17, -0.55, 0.12), "wood_l", bevel=0.008)
    for x in (-0.55, 0.64):
        for y in (-0.95, -0.2):
            cyl(0.04, 0.3, (x, y, 0.05), "wood", seg=10)
    # Boat: tapered hull, white cabin, mast.
    hull = box((0.95, 0.38, 0.22), (0.95, -0.95, 0.13), mat("hull", (0.2, 0.45, 0.75)), bevel=0.08)
    box((0.97, 0.4, 0.05), (0.95, -0.95, 0.24), "white", bevel=0.02)
    box((0.32, 0.28, 0.24), (0.82, -0.95, 0.38), "white", bevel=0.03)
    window(0.82, -1.09, 0.4, w=0.16, h=0.1, frame="white")
    cyl(0.02, 0.6, (1.05, -0.95, 0.55), "wood", seg=8)
    # Fish shed with a teal roof and the fish sign.
    box((1.25, 0.8, 0.62), (-0.25, 0.55, 0.31), "wall_y", bevel=0.02)
    gable(1.25, 0.8, 0.36, (-0.25, 0.55, 0.61), roofmat("teal"))
    gable_wall(0.8, 1.25, 0.34, (-0.25, 0.55, 0.62), "wall_y")
    door(-0.45, 0.14, 0.0, w=0.32, h=0.46)
    window(0.1, 0.14, 0.38, w=0.24, h=0.22)
    box((0.62, 0.05, 0.2), (-0.25, 0.12, 0.76), "teal_dark", bevel=0.02)
    text("PEIXES", (-0.25, 0.08, 0.76), 0.12, "white")
    torus(0.1, 0.03, (0.45, 0.12, 0.45), "red", rot=(math.radians(90), 0, 0))
    crate(-1.0, 0.0, fill=(0.6, 0.75, 0.85))
    tree(-1.3, 0.85, 0.8)


def fabrica():
    ground()
    box((1.75, 1.0, 0.75), (-0.05, 0.35, 0.375), mat("brickwall", PAL["brick"], pattern="bricks", scale=9), bevel=0.02)
    # Saw-tooth roof: three slanted panes with glass.
    for i in range(3):
        x = -0.65 + i * 0.6
        box((0.6, 1.0, 0.05), (x, 0.35, 0.86), "teal", bevel=0.01, rot=(0, math.radians(-24), 0))
        box((0.04, 0.96, 0.24), (x + 0.28, 0.35, 0.86), mat("glass", PAL["glass"], rough=0.15, noise=0.02), bevel=0.005)
    box((1.77, 1.02, 0.1), (-0.05, 0.35, 0.72), "cream", bevel=0.01)
    door(-0.35, -0.16, 0.0, w=0.5, h=0.5, m="teal")
    for x in (0.3, 0.62):
        window(x, -0.16, 0.42, w=0.22, h=0.26)
    box((0.9, 0.06, 0.2), (-0.05, -0.18, 0.97), "teal_dark", bevel=0.02)
    text("FÁBRICA", (-0.05, -0.22, 0.97), 0.13, "white")
    for x, h in ((0.55, 1.65), (0.82, 1.4)):
        cyl(0.09, h, (x, 0.65, h / 2), "brick", seg=20, r2=0.075)
        cyl(0.1, 0.06, (x, 0.65, h), "dark", seg=20)
    smoke(0.58, 0.65, 1.78, 3)
    for i in range(3):
        box((0.22, 0.22, 0.2), (-1.1 + (i % 2) * 0.25, -0.65 + (i // 2) * 0.1, 0.1 + (i // 2) * 0.2), mat("carton", (0.8, 0.62, 0.4)), bevel=0.01)
    tree(1.3, -0.4, 0.75)


def engarrafadora():
    ground()
    box((1.3, 0.95, 0.7), (-0.4, 0.35, 0.35), "cream", bevel=0.02)
    box((1.32, 0.97, 0.12), (-0.4, 0.35, 0.68), "red", bevel=0.02)
    door(-0.6, -0.13, 0.0, w=0.4, h=0.48, m="red")
    window(-0.1, -0.13, 0.4, w=0.3, h=0.24)
    # Three steel tanks with pipes.
    for i, x in enumerate((0.55, 0.95)):
        cyl(0.21, 1.0, (x, 0.45, 0.55), mat("tank", (0.78, 0.8, 0.83), rough=0.25, metal=0.7, noise=0.03), seg=32, bevel=0.0)
        sphere(0.21, (x, 0.45, 1.05), mat("tank", (0.78, 0.8, 0.83), rough=0.25, metal=0.7, noise=0.03), scale=(1, 1, 0.45))
        for lx in (-0.15, 0.15):
            cyl(0.025, 0.12, (x + lx, 0.45, 0.03), "dark", seg=8)
    cyl(0.03, 0.75, (0.25, 0.45, 0.85), "steel", seg=10, rot=(0, math.radians(90), 0))
    # Giant bottle on the roof.
    bottle = mat("bottle", (0.25, 0.65, 0.35), rough=0.15, noise=0.03)
    cyl(0.13, 0.4, (-0.4, 0.35, 0.95), bottle, seg=24)
    cyl(0.13, 0.12, (-0.4, 0.35, 1.21), bottle, seg=24, r2=0.05)
    cyl(0.05, 0.12, (-0.4, 0.35, 1.32), bottle, seg=16)
    cyl(0.06, 0.04, (-0.4, 0.35, 1.4), "red", seg=16)
    cyl(0.135, 0.14, (-0.4, 0.35, 0.95), "white", seg=24)
    # Pallet of crates of bottles.
    for i in range(2):
        box((0.3, 0.24, 0.16), (-1.15, -0.55 + i * 0.26, 0.08), "red", bevel=0.01)
        for j in range(3):
            cyl(0.03, 0.12, (-1.25 + j * 0.1, -0.55 + i * 0.26, 0.22), bottle, seg=10)
    tree(1.35, -0.3, 0.7)


def vinicola():
    ground()
    box((1.15, 0.8, 0.62), (-0.45, 0.5, 0.31), "wall_y", bevel=0.02)
    gable(1.15, 0.8, 0.38, (-0.45, 0.5, 0.61), roofmat("roof"))
    gable_wall(0.8, 1.15, 0.36, (-0.45, 0.5, 0.62), "wall_y")
    door(-0.45, 0.09, 0.0, w=0.3, h=0.46, m="wood")
    window(-0.85, 0.09, 0.38, w=0.18, h=0.22)
    window(-0.05, 0.09, 0.38, w=0.18, h=0.22)
    box((0.62, 0.05, 0.18), (-0.45, 0.07, 0.72), mat("wine", (0.5, 0.12, 0.2)), bevel=0.02)
    text("VINHOS", (-0.45, 0.03, 0.72), 0.11, "white")
    # Vine rows with grape clusters.
    for r in range(3):
        y = -0.15 - r * 0.38
        box((1.1, 0.03, 0.03), (0.75, y, 0.42), "wood", bevel=0.0)
        for x in (0.22, 1.28):
            box((0.04, 0.04, 0.45), (x, y, 0.22), "wood", bevel=0.005)
        for j in range(5):
            sphere(0.11, (0.3 + j * 0.22, y, 0.38), mat("vine", PAL["leaf"]), scale=(1.1, 0.8, 0.9))
            sphere(0.045, (0.34 + j * 0.22, y - 0.08, 0.27), mat("grape", PAL["grape"], rough=0.3), scale=(1, 1, 1.4))
    barrel(-1.05, -0.4)
    barrel(-0.75, -0.6, lying=True)
    tree(-1.3, 0.85, 0.8)


def moinho():
    ground()
    # Tapered tower, conical roof, door and windows.
    cyl(0.5, 1.2, (0, 0.35, 0.6), "cream", seg=40, r2=0.36, bevel=0.0)
    cyl(0.52, 0.08, (0, 0.35, 0.04), "brick", seg=40)
    cyl(0.44, 0.5, (0, 0.35, 1.42), roofmat("roof"), seg=40, r2=0.02, bevel=0.0)
    box((0.26, 0.05, 0.42), (0, -0.13, 0.22), "wood", bevel=0.015)
    window(0, -0.07, 0.78, w=0.14, h=0.18, frame="white")
    # Four sails on a hub, a little turned.
    hub = Vector((0, -0.1, 1.15))
    sphere(0.07, hub, "dark")
    for k in range(4):
        a = math.radians(20 + 90 * k)
        d = Vector((math.cos(a), 0, math.sin(a)))
        c = hub + d * 0.55 + Vector((0, -0.03, 0))
        box((0.9, 0.025, 0.05), tuple(hub + d * 0.45 + Vector((0, -0.02, 0))), "wood", bevel=0.005, rot=(0, -a, 0))
        sail = box((0.62, 0.02, 0.22), tuple(c + Vector((0, 0, 0)) + Vector((-math.sin(a), 0, math.cos(a))) * 0.1), mat("sail", (0.96, 0.92, 0.84)), bevel=0.005, rot=(0, -a, 0))
    # Wheat field and flour sacks.
    for i in range(9):
        x = 0.65 + (i % 3) * 0.24
        y = -0.35 - (i // 3) * 0.26
        cyl(0.07, 0.34, (x, y, 0.17), mat("wheat", PAL["wheat"], rough=0.8), seg=10, r2=0.03)
    for i in range(3):
        x, y = -0.85 + i * 0.24, -0.5 - (i % 2) * 0.14
        box((0.2, 0.15, 0.26), (x, y, 0.13), mat("sack", (0.92, 0.86, 0.72), rough=0.9), bevel=0.06)
        cyl(0.035, 0.05, (x, y, 0.28), mat("sack", (0.92, 0.86, 0.72)), seg=10)
        box((0.1, 0.01, 0.07), (x, y - 0.08, 0.14), mat("flourlogo", (0.75, 0.3, 0.2)), bevel=0.0)
    tree(-1.3, 0.75, 0.85)


def distribuidora():
    ground()
    glb("Warehouse", (0, 0.3, 0.0), width=1.8)
    for i in range(3):
        box((0.3, 0.3, 0.06), (-1.0 + i * 0.36, -0.75, 0.03), "wood_l", bevel=0.005)
        for j in range(2):
            box((0.24, 0.24, 0.2), (-1.0 + i * 0.36, -0.75, 0.16 + j * 0.21), mat("carton", (0.8, 0.62, 0.4)), bevel=0.01)
    tree(1.35, -0.45, 0.75)


def mercado():
    ground()
    # Our supermarket: cream walls, teal band, striped awning, big windows and the sign.
    box((1.9, 1.0, 0.85), (0, 0.35, 0.425), "cream", bevel=0.02)
    box((1.94, 1.04, 0.16), (0, 0.35, 0.88), "teal", bevel=0.02)
    box((1.92, 1.02, 0.08), (0, 0.35, 0.04), "teal_dark", bevel=0.01)
    box((1.1, 0.07, 0.28), (0, -0.19, 1.07), "red", bevel=0.03)
    text("MERCADO", (0, -0.24, 1.07), 0.17, "white")
    # Awning stripes.
    for i in range(10):
        box((0.19, 0.36, 0.03), (-0.855 + i * 0.19, -0.3, 0.68), "red" if i % 2 == 0 else "white", bevel=0.005, rot=(math.radians(-22), 0, 0))
    # Glass front and the sliding door.
    for x in (-0.6, 0.6):
        box((0.62, 0.05, 0.42), (x, -0.16, 0.3), mat("glass", PAL["glass"], rough=0.15, noise=0.02), bevel=0.01)
        box((0.66, 0.06, 0.04), (x, -0.17, 0.52), "white", bevel=0.005)
    box((0.48, 0.06, 0.56), (0, -0.16, 0.28), mat("glass", PAL["glass"], rough=0.15, noise=0.02), bevel=0.01)
    box((0.02, 0.07, 0.56), (0, -0.17, 0.28), "white", bevel=0.0)
    # Carts and a tree.
    for x in (0.95, 1.12):
        box((0.16, 0.24, 0.12), (x, -0.62, 0.16), "steel", bevel=0.01)
        box((0.16, 0.03, 0.14), (x, -0.76, 0.25), "red", bevel=0.005)
    tree(-1.3, -0.4, 0.8)


PLACES = {
    "fazenda": fazenda, "laticinio": laticinio, "frigorifico": frigorifico, "porto": porto, "fabrica": fabrica,
    "engarrafadora": engarrafadora, "vinicola": vinicola, "moinho": moinho, "distribuidora": distribuidora,
    "mercado": mercado,
}


def camera_place():
    cam = bpy.data.objects["LaneArt_Cam"]
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 4.3
    tilt = math.radians(62)
    yaw = math.radians(16)
    dist = 12
    target = Vector((0, 0.05, 0.55))
    off = Vector((math.sin(yaw) * math.sin(tilt), -math.cos(yaw) * math.sin(tilt), math.cos(tilt))) * dist
    cam.location = target + off
    cam.rotation_euler = (tilt, 0, yaw)


def render(names=None):
    os.makedirs(OUT, exist_ok=True)
    sc = scene()
    camera_place()
    sc.render.resolution_x, sc.render.resolution_y = RES
    for n in names or list(PLACES):
        c = coll("LaneArt_" + n)
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        CUR["c"] = c
        for other in bpy.data.collections:
            if other.name.startswith("LaneArt_"):
                other.hide_render = other is not c
                other.hide_viewport = other is not c
        PLACES[n]()
        sc.render.filepath = os.path.join(OUT, n + ".png")
        bpy.ops.render.render(write_still=True)


def render_trucks():
    """The three truck models from the side, cab to the right (800 x 480)."""
    sc = scene()
    c = coll("LaneArt_trucks")
    CUR["c"] = c
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for other in bpy.data.collections:
        if other.name.startswith("LaneArt_"):
            other.hide_render = other is not c
    cam = bpy.data.objects["LaneArt_Cam"]
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.25
    cam.location = (10, 0, 0.32 + 10 * math.tan(math.radians(8)))
    cam.rotation_euler = (math.radians(82), 0, math.radians(90))
    sc.render.resolution_x, sc.render.resolution_y = 800, 480
    for model, out in (("DeliveryTruck", "truck"), ("FishDeliveryTruck", "truck_fish"), ("IceCreamTruck", "truck_ice")):
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        glb(model, (0, 0, 0), height=0.64)
        sc.render.filepath = os.path.join(OUT, out + ".png")
        bpy.ops.render.render(write_still=True)
    sc.render.resolution_x, sc.render.resolution_y = RES


def render_all():
    render()
    render_trucks()
