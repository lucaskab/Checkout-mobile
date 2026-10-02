"""
fixture_art.py  --  Checkout - Supermercado Simulator
Front views of every kind of fixture for the shelf window of the game (CheckoutDesktopHUD.Shelf.cs).

Each fixture is rendered twice with the same orthographic camera (1200 x 800, 12 x 8 world units):
  <name>_back.png   everything behind the products (inside of the crates, back panels, shelves)
  <name>_front.png  what stands in front of the products (crate fronts, glass doors, shelf lips)
The UI draws back -> product icons -> front, so the products look like they sit inside the fixture.

Product places (normalised, origin bottom-left, same for every fixture; keep in sync with the C# side):
  top row    (slots 0-3): x centres .17 .39 .61 .83, y .50-.78, width .19
  bottom row (slots 4-6): x centres .28 .50 .72,     y .14-.42, width .19
  sign band:              y .84-.98
World: x = nx*12-6, z = ny*8-4.

Usage in Blender:
  exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\fixture_art.py").read())
  render_all()            # or render(["isopor"])
"""
import bpy, bmesh, math, os, random
from mathutils import Vector

SCENE = "FixtureArt"
OUT = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\fixtures"
RES_X, RES_Y = 1200, 800
SAMPLES = 48
TILT = math.radians(16)

TOP_X = [-3.96, -1.32, 1.32, 3.96]
BOT_X = [-2.64, 0.0, 2.64]
TOP_Z = (0.0, 2.24)
BOT_Z = (-2.88, -0.64)
SLOT_W = 2.28
SIGN_Z = (2.72, 3.84)


# ---------------------------------------------------------------- scene helpers
def scene():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y, r.resolution_percentage = RES_X, RES_Y, 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.device = "GPU"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = -0.45
    w = bpy.data.worlds.get("FixtureArt_World")
    if w is None:
        w = bpy.data.worlds.new("FixtureArt_World")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs[0].default_value = (0.93, 0.92, 0.9, 1)
        w.node_tree.nodes["Background"].inputs[1].default_value = 0.2
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.2
    sc.world = w
    return sc


def coll(name):
    sc = scene()
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if c.name not in [x.name for x in sc.collection.children]:
        sc.collection.children.link(c)
    return c


def clear(c):
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)


CUR = {"c": None}
MATS = {}


def mat(name, color, rough=0.5, metal=0.0, alpha=1.0, transmission=0.0, emission=0.0, coat=0.0):
    key = name
    m = bpy.data.materials.get("FA_" + key) or bpy.data.materials.new("FA_" + key)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Alpha"].default_value = alpha
    try:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["Coat Weight"].default_value = coat
        if emission:
            b.inputs["Emission Color"].default_value = (*color, 1)
            b.inputs["Emission Strength"].default_value = emission
    except KeyError:
        pass
    if alpha < 1:
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    return m


def box(name, x, y, z, w, d, h, m, bevel=0.04, rot=(0, 0, 0)):
    """Box centred at (x, y, z) with size w (x) x d (y) x h (z)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = (x, y, z)
    o.scale = (w, d, h)
    o.rotation_euler = rot
    me.materials.append(m)
    CUR["c"].objects.link(o)
    if bevel:
        bv = o.modifiers.new("b", "BEVEL")
        bv.width = bevel
        bv.segments = 3
        bv.affect = "EDGES"
        bpy.context.view_layer.update()
    # apply scale so the bevel is even
    return o


def cyl(name, x, y, z, r, h, m, axis="z", segs=24, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = (x, y, z)
    if axis == "x":
        o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "y":
        o.rotation_euler = (math.pi / 2, 0, 0)
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    CUR["c"].objects.link(o)
    return o


def sphere(name, x, y, z, r, m, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = (x, y, z)
    o.scale = scale
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    CUR["c"].objects.link(o)
    return o


def fix_scales(c):
    """Apply object scale so bevels are uniform."""
    for o in c.objects:
        if o.type != "MESH" or tuple(o.scale) == (1, 1, 1):
            continue
        me = o.data
        sx, sy, sz = o.scale
        for v in me.vertices:
            v.co.x *= sx
            v.co.y *= sy
            v.co.z *= sz
        o.scale = (1, 1, 1)


def camera_and_lights(sc, root):
    cam = bpy.data.objects.get("FA_Cam")
    if cam is None:
        cd = bpy.data.cameras.new("FA_Cam")
        cam = bpy.data.objects.new("FA_Cam", cd)
    if cam.name not in [o.name for o in root.objects]:
        root.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 12
    # A slight look from above shows the tops of crates and coolers (products sit at depth 0, where the
    # screen height is z * cos(TILT): under 1% off the slot rectangles).
    cam.location = (0, -30 * math.cos(TILT), 30 * math.sin(TILT))
    cam.rotation_euler = (math.pi / 2 - TILT, 0, 0)
    cam.data.clip_end = 100
    sc.camera = cam
    for name, loc, energy, size in (("FA_Key", (-7, -12, 11), 4200, 5), ("FA_Fill", (9, -10, 3), 600, 10), ("FA_Top", (0, 1, 13), 800, 10)):
        l = bpy.data.objects.get(name)
        if l is None:
            ld = bpy.data.lights.new(name, "AREA")
            l = bpy.data.objects.new(name, ld)
        if l.name not in [o.name for o in root.objects]:
            root.objects.link(l)
        l.data.energy = energy
        l.data.size = size
        l.location = loc
        l.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


# ---------------------------------------------------------------- colours
WOOD = (0.52, 0.30, 0.13)
WOOD_D = (0.32, 0.17, 0.08)
WOOD_L = (0.70, 0.45, 0.22)
CREAM = (0.97, 0.94, 0.88)
WHITE = (0.95, 0.95, 0.95)
STEEL = (0.75, 0.77, 0.80)
DARK = (0.16, 0.18, 0.22)
ICE = (0.80, 0.92, 1.0)


def slot_rows():
    """(x, z0, z1) of every product place."""
    return [(x, TOP_Z[0], TOP_Z[1]) for x in TOP_X] + [(x, BOT_Z[0], BOT_Z[1]) for x in BOT_X]


# ---------------------------------------------------------------- fixtures
def crate(name, x, z0, back, front, color, color_d, slats=True):
    """A wooden crate in a product place: back + sides in BACK, front planks in FRONT."""
    w = SLOT_W
    CUR["c"] = back
    box(name + "_in", x, 0.6, z0 + 0.55, w - 0.1, 0.1, 1.1, mat("crate_in", color_d, 0.8))
    box(name + "_bottom", x, 0.0, z0 + 0.04, w, 1.2, 0.08, mat("crate_in", color_d, 0.8))
    for s in (-1, 1):
        box(name + "_side%d" % s, x + s * (w / 2 - 0.05), 0.0, z0 + 0.5, 0.1, 1.2, 1.0, mat("crate", color, 0.7))
    CUR["c"] = front
    for i, (zz, hh) in enumerate(((z0 + 0.18, 0.3), (z0 + 0.55, 0.3))):
        box(name + "_f%d" % i, x, -0.62, zz, w + 0.04, 0.08, hh, mat("crate", color, 0.7), bevel=0.03)
    for s in (-1, 1):
        box(name + "_post%d" % s, x + s * (w / 2 - 0.05), -0.66, z0 + 0.38, 0.12, 0.1, 0.78, mat("crate_d", color_d, 0.7), bevel=0.02)


def build_caixotes(back, front):
    # Folding table on the sidewalk with two tiers of crates.
    CUR["c"] = back
    box("table", 0, 0.3, BOT_Z[0] - 0.25, 9.6, 2.4, 0.18, mat("table", WOOD_L, 0.6))
    for s in (-1, 1):
        box("leg%d" % s, s * 4.4, 0.3, BOT_Z[0] - 0.9, 0.14, 0.14, 1.2, mat("steel", STEEL, 0.4, 0.6))
    box("tier", 0, 1.2, -0.25, 10.2, 1.0, 0.5, mat("table_d", WOOD, 0.7))
    for s in (-1, 1):
        box("tierleg%d" % s, s * 4.9, 1.2, -1.6, 0.18, 0.18, 2.6, mat("table_d", WOOD, 0.7))
    for i, x in enumerate(TOP_X):
        crate("top%d" % i, x, TOP_Z[0], back, front, WOOD, WOOD_D)
    for i, x in enumerate(BOT_X):
        crate("bot%d" % i, x, BOT_Z[0], back, front, WOOD_L, WOOD)
    # Chalk board for the sign.
    CUR["c"] = back
    box("board", 0, 1.4, 3.25, 5.0, 0.12, 1.0, mat("chalk", (0.15, 0.2, 0.17), 0.9))
    box("boardframe", 0, 1.45, 3.25, 5.3, 0.1, 1.25, mat("table", WOOD_L, 0.6))
    for s in (-1, 1):
        box("stake%d" % s, s * 2.2, 1.5, 1.8, 0.12, 0.12, 2.4, mat("table", WOOD_L, 0.6))


def build_banca(back, front):
    green = (0.25, 0.48, 0.24)
    green_d = (0.16, 0.32, 0.15)
    CUR["c"] = back
    box("frame", 0, 1.0, -0.6, 11.4, 0.4, 7.2, mat("banca_back", (0.86, 0.80, 0.66), 0.8))
    for s in (-1, 1):
        box("post%d" % s, s * 5.6, 0.0, -0.4, 0.3, 0.3, 7.6, mat("green", green, 0.6))
    box("tier", 0, 0.4, -0.3, 11.0, 1.2, 0.3, mat("green", green, 0.6))
    box("base", 0, 0.0, BOT_Z[0] - 0.35, 11.0, 1.6, 0.4, mat("green", green, 0.6))
    for i, x in enumerate(TOP_X):
        crate("top%d" % i, x, TOP_Z[0], back, front, WOOD_L, WOOD)
    for i, x in enumerate(BOT_X):
        crate("bot%d" % i, x, BOT_Z[0], back, front, WOOD_L, WOOD)
    # Striped awning over the sign band.
    CUR["c"] = front
    for i in range(12):
        col = green if i % 2 == 0 else CREAM
        box("awn%d" % i, -5.5 + i * 1.0, -0.8, 3.75, 1.0, 0.2, 0.5, mat("awn%d" % (i % 2), col, 0.7), bevel=0.02)
        sphere("awnb%d" % i, -5.5 + i * 1.0, -0.8, 3.48, 0.5, mat("awn%d" % (i % 2), col, 0.7), scale=(1, 0.3, 0.35))
    CUR["c"] = back
    box("sign", 0, 0.6, 3.0, 5.2, 0.15, 0.9, mat("signboard", CREAM, 0.7))
    box("signframe", 0, 0.65, 3.0, 5.5, 0.1, 1.15, mat("green_d", green_d, 0.6))


def styro(name, x, z0, back, front):
    w = SLOT_W
    white = mat("styro", (0.96, 0.96, 0.94), 0.95)
    CUR["c"] = back
    box(name + "_in", x, 0.55, z0 + 0.6, w - 0.12, 0.1, 1.2, mat("styro_in", (0.88, 0.92, 0.95), 0.9))
    box(name + "_bottom", x, 0.0, z0 + 0.06, w, 1.2, 0.12, white)
    for s in (-1, 1):
        box(name + "_side%d" % s, x + s * (w / 2 - 0.07), 0.0, z0 + 0.55, 0.14, 1.2, 1.1, white)
    # Ice between the bottles.
    random.seed(hash(name) & 0xFFFF)
    for k in range(9):
        box(name + "_ice%d" % k, x + random.uniform(-0.85, 0.85), random.uniform(-0.3, 0.4), z0 + 0.55 + random.uniform(-0.1, 0.15),
            0.28, 0.28, 0.24, mat("ice", ICE, 0.05, transmission=0.6, coat=0.6), bevel=0.06, rot=(random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1)))
    CUR["c"] = front
    box(name + "_front", x, -0.62, z0 + 0.36, w + 0.04, 0.14, 0.72, white, bevel=0.06)
    for k in range(5):
        box(name + "_fice%d" % k, x - 0.9 + k * 0.45, -0.7, z0 + 0.76, 0.3, 0.26, 0.24, mat("ice", ICE, 0.05, transmission=0.6, coat=0.6), bevel=0.06, rot=(0.3 * k, 0.5, 0.2 * k))


def build_isopor(back, front):
    CUR["c"] = back
    box("bench", 0, 0.3, BOT_Z[0] - 0.25, 9.0, 2.0, 0.18, mat("table", WOOD_L, 0.6))
    box("tier", 0, 1.2, -0.3, 10.2, 1.0, 0.4, mat("table_d", WOOD, 0.7))
    for s in (-1, 1):
        box("tierleg%d" % s, s * 4.9, 1.2, -1.6, 0.18, 0.18, 2.6, mat("table_d", WOOD, 0.7))
    for i, x in enumerate(TOP_X):
        styro("top%d" % i, x, TOP_Z[0], back, front)
    for i, x in enumerate(BOT_X):
        styro("bot%d" % i, x, BOT_Z[0], back, front)
    CUR["c"] = back
    box("sign", 0, 1.4, 3.25, 4.6, 0.12, 0.9, mat("signcard", (0.98, 0.98, 0.98), 0.8))
    box("signframe", 0, 1.45, 3.25, 4.9, 0.1, 1.15, mat("bluecard", (0.18, 0.55, 0.68), 0.6))


def cabinet(back, front, body, inner, shelf_m, lip_m, glass=False, frost=False, light=(0.9, 0.97, 1.0), doors=2):
    """Upright cabinet (fridge, freezer, display): body, lit inside, two shelves, lips or glass doors."""
    CUR["c"] = back
    box("body", 0, 0.9, -0.35, 11.4, 1.2, 7.3, body, bevel=0.15)
    box("inner", 0, 0.25, -0.5, 10.6, 0.1, 6.1, inner, bevel=0)
    box("light", 0, 0.2, 2.45, 10.4, 0.4, 0.12, mat("light", light, 0.3, emission=3.0), bevel=0.02)
    for z in (TOP_Z[0], BOT_Z[0]):
        box("shelf%.1f" % z, 0, -0.1, z - 0.04, 10.6, 1.2, 0.08, shelf_m, bevel=0.01)
    if frost:
        # Frost on the back wall: a pale band at the bottom of each shelf space.
        for z in (TOP_Z[0], BOT_Z[0]):
            box("frostband%.1f" % z, 0, 0.18, z + 0.35, 10.4, 0.04, 0.7, mat("frost", (0.92, 0.97, 1.0), 0.7, alpha=0.6), bevel=0)
    CUR["c"] = front
    for z in (TOP_Z[0], BOT_Z[0]):
        box("lip%.1f" % z, 0, -0.7, z + 0.1, 10.6, 0.08, 0.22, lip_m, bevel=0.02)
    box("grille", 0, -0.6, -3.55, 11.4, 0.2, 0.7, mat("grille", DARK, 0.5, 0.4), bevel=0.05)
    for k in range(10):
        box("gr%d" % k, -4.5 + k, -0.72, -3.55, 0.12, 0.05, 0.5, mat("grille_l", (0.35, 0.37, 0.42), 0.5, 0.5), bevel=0)
    if glass:
        w = 10.6 / doors
        for d in range(doors):
            cx = -5.3 + w * (d + 0.5)
            g = mat("glass", (0.9, 0.96, 1.0), 0.02, alpha=0.07)
            box("glass%d" % d, cx, -0.9, -0.55, w - 0.2, 0.03, 5.9, g, bevel=0)
            fm = body
            box("frameL%d" % d, cx - w / 2 + 0.07, -0.95, -0.55, 0.14, 0.1, 6.0, fm, bevel=0.02)
            box("frameR%d" % d, cx + w / 2 - 0.07, -0.95, -0.55, 0.14, 0.1, 6.0, fm, bevel=0.02)
            box("frameT%d" % d, cx, -0.95, 2.4, w, 0.1, 0.14, fm, bevel=0.02)
            box("frameB%d" % d, cx, -0.95, -3.5, w, 0.1, 0.14, fm, bevel=0.02)
            box("handle%d" % d, cx + (w / 2 - 0.35) * (1 if d % 2 == 0 else -1), -1.05, -0.4, 0.1, 0.1, 1.8, mat("chrome", STEEL, 0.15, 1.0), bevel=0.03)
            # Glints on the glass.
            box("glint%d" % d, cx - 0.6, -0.92, 0.6, 0.18, 0.01, 3.2, mat("glint", (1, 1, 1), 0.1, alpha=0.35), bevel=0, rot=(0, 0.35, 0))
            if frost:
                # Frosty glass: misted corners at the bottom and top of each door.
                box("dfrostb%d" % d, cx, -0.93, -3.15, w - 0.3, 0.01, 0.55, mat("frostg", (0.95, 0.98, 1.0), 0.5, alpha=0.45), bevel=0)
                box("dfrostt%d" % d, cx, -0.93, 2.15, w - 0.3, 0.01, 0.35, mat("frostg", (0.95, 0.98, 1.0), 0.5, alpha=0.35), bevel=0)


def build_geladeira(back, front):
    cabinet(back, front, mat("fridge", (0.07, 0.30, 0.42), 0.35, coat=0.4), mat("fridge_in", (0.93, 0.96, 0.98), 0.6),
            mat("wire", STEEL, 0.3, 0.8), mat("chrome", STEEL, 0.15, 1.0), glass=True)
    CUR["c"] = back
    box("signbox", 0, 0.7, 3.3, 11.4, 0.6, 1.1, mat("fridge", (0.07, 0.30, 0.42), 0.35, coat=0.4), bevel=0.1)
    box("signface", 0, 0.38, 3.3, 7.0, 0.05, 0.8, mat("signlight", (0.85, 0.97, 1.0), 0.4, emission=0.6), bevel=0.02)


def build_expositor(back, front):
    cabinet(back, front, mat("display", (0.92, 0.94, 0.96), 0.4, coat=0.3), mat("display_in", (0.78, 0.88, 0.95), 0.6),
            mat("steelshelf", STEEL, 0.3, 0.7), mat("chrome", STEEL, 0.15, 1.0), glass=False)
    CUR["c"] = back
    box("canopy", 0, 0.2, 3.3, 11.6, 1.8, 1.0, mat("display_c", (0.12, 0.42, 0.55), 0.35, coat=0.3), bevel=0.12)
    box("signface", 0, -0.72, 3.3, 7.0, 0.05, 0.7, mat("signlight", (0.85, 0.97, 1.0), 0.4, emission=0.6), bevel=0.02)
    CUR["c"] = front
    box("curtain", 0, -0.8, 2.6, 10.8, 0.04, 0.18, mat("curtain", (0.8, 0.9, 1.0), 0.2, alpha=0.4), bevel=0)


def build_freezer(back, front):
    cabinet(back, front, mat("freezer", (0.17, 0.33, 0.58), 0.35, coat=0.4), mat("freezer_in", (0.86, 0.93, 1.0), 0.5),
            mat("wire", STEEL, 0.3, 0.8), mat("chrome", STEEL, 0.15, 1.0), glass=True, frost=True, light=(0.8, 0.9, 1.0), doors=4)
    CUR["c"] = back
    box("signbox", 0, 0.7, 3.3, 11.4, 0.6, 1.1, mat("freezer", (0.17, 0.33, 0.58), 0.35, coat=0.4), bevel=0.1)
    box("signface", 0, 0.38, 3.3, 7.0, 0.05, 0.8, mat("signlight", (0.85, 0.97, 1.0), 0.4, emission=0.6), bevel=0.02)


def icebin(name, x, z0, back, front, pink):
    w = SLOT_W
    CUR["c"] = back
    box(name + "_in", x, 0.55, z0 + 0.6, w - 0.12, 0.1, 1.2, mat("bin_in", (0.86, 0.94, 1.0), 0.5))
    box(name + "_bottom", x, 0.0, z0 + 0.06, w, 1.2, 0.12, mat("bin_white", (0.96, 0.96, 0.97), 0.4, coat=0.3))
    for s_ in (-1, 1):
        box(name + "_side%d" % s_, x + s_ * (w / 2 - 0.06), 0.0, z0 + 0.55, 0.12, 1.2, 1.1, mat("bin_white", (0.96, 0.96, 0.97), 0.4, coat=0.3))
    box(name + "_frost", x, 0.4, z0 + 1.05, w - 0.2, 0.05, 0.25, mat("frost", (0.92, 0.97, 1.0), 0.7, alpha=0.6), bevel=0)
    CUR["c"] = front
    box(name + "_front", x, -0.62, z0 + 0.36, w + 0.04, 0.14, 0.72, mat("bin_white", (0.96, 0.96, 0.97), 0.4, coat=0.3), bevel=0.06)
    box(name + "_band", x, -0.7, z0 + 0.36, w + 0.06, 0.05, 0.18, mat("chest_pink", pink, 0.4, coat=0.3), bevel=0.02)
    box(name + "_rim", x, -0.62, z0 + 0.75, w + 0.06, 0.18, 0.08, mat("chrome", STEEL, 0.15, 1.0), bevel=0.02)


def build_chest(back, front):
    pink = (0.85, 0.36, 0.55)
    CUR["c"] = back
    box("body", 0, 0.9, -0.6, 11.4, 1.0, 6.6, mat("chest_back", (0.98, 0.9, 0.93), 0.6), bevel=0.12)
    box("tier", 0, 0.6, -0.3, 10.8, 1.4, 0.4, mat("chest_pinkd", (0.7, 0.25, 0.42), 0.4, coat=0.3), bevel=0.05)
    box("base", 0, 0.2, BOT_Z[0] - 0.35, 10.8, 1.8, 0.5, mat("chest_pinkd", (0.7, 0.25, 0.42), 0.4, coat=0.3), bevel=0.05)
    for i, x in enumerate(TOP_X):
        icebin("top%d" % i, x, TOP_Z[0], back, front, pink)
    for i, x in enumerate(BOT_X):
        icebin("bot%d" % i, x, BOT_Z[0], back, front, pink)
    CUR["c"] = back
    box("signbox", 0, 0.7, 3.3, 11.4, 0.6, 1.1, mat("chest_pink", pink, 0.4, coat=0.3), bevel=0.1)
    box("signface", 0, 0.38, 3.3, 7.0, 0.05, 0.8, mat("signcream", CREAM, 0.6), bevel=0.02)


def build_gondola(back, front):
    CUR["c"] = back
    peg = mat("pegboard", (0.86, 0.87, 0.88), 0.7)
    box("back", 0, 0.9, -0.4, 11.2, 0.15, 7.0, peg, bevel=0.03)
    random.seed(3)
    for i in range(22):
        for j in range(13):
            cyl("hole%d_%d" % (i, j), -5.2 + i * 0.5, 0.8, -3.6 + j * 0.55, 0.04, 0.02, mat("hole", (0.55, 0.56, 0.58), 0.9), axis="y", segs=8)
    for s in (-1, 1):
        box("upright%d" % s, s * 5.6, 0.3, -0.4, 0.25, 1.4, 7.4, mat("upright", (0.32, 0.34, 0.38), 0.5, 0.6), bevel=0.04)
    for z in (TOP_Z[0], BOT_Z[0]):
        box("shelf%.1f" % z, 0, 0.1, z - 0.05, 11.0, 1.6, 0.1, mat("shelfm", (0.80, 0.81, 0.83), 0.4, 0.6), bevel=0.02)
    box("base", 0, 0.1, -3.6, 11.0, 1.8, 0.6, mat("upright", (0.32, 0.34, 0.38), 0.5, 0.6), bevel=0.04)
    box("header", 0, 0.7, 3.3, 11.4, 0.3, 1.1, mat("header", (0.95, 0.95, 0.95), 0.6), bevel=0.06)
    CUR["c"] = front
    for z in (TOP_Z[0], BOT_Z[0]):
        box("rail%.1f" % z, 0, -0.75, z + 0.05, 11.0, 0.06, 0.24, mat("rail", (0.97, 0.97, 0.97), 0.4), bevel=0.02)
        box("railedge%.1f" % z, 0, -0.78, z + 0.18, 11.0, 0.05, 0.04, mat("railedge", (0.85, 0.2, 0.15), 0.4), bevel=0)


def build_cesto(back, front):
    wicker = (0.74, 0.55, 0.32)
    wicker_d = (0.55, 0.38, 0.2)
    CUR["c"] = back
    box("table", 0, 0.3, BOT_Z[0] - 0.25, 9.6, 2.4, 0.18, mat("table", WOOD_L, 0.6))
    box("cloth", 0, 0.0, BOT_Z[0] - 0.1, 9.8, 2.6, 0.08, mat("cloth", (0.86, 0.22, 0.18), 0.8))
    box("tier", 0, 1.2, -0.25, 10.2, 1.0, 0.5, mat("table_d", WOOD, 0.7))
    for s in (-1, 1):
        box("tierleg%d" % s, s * 4.9, 1.2, -1.6, 0.18, 0.18, 2.6, mat("table_d", WOOD, 0.7))
    for name, xs, z0 in (("top", TOP_X, TOP_Z[0]), ("bot", BOT_X, BOT_Z[0])):
        for i, x in enumerate(xs):
            CUR["c"] = back
            box("%s%d_in" % (name, i), x, 0.5, z0 + 0.45, SLOT_W - 0.2, 0.1, 0.8, mat("wicker_d", wicker_d, 0.9), bevel=0.1)
            box("%s%d_cloth" % (name, i), x, 0.3, z0 + 0.62, SLOT_W - 0.3, 0.05, 0.5, mat("napkin", (0.97, 0.93, 0.85), 0.9), bevel=0.05)
            CUR["c"] = front
            for k in range(4):
                box("%s%d_w%d" % (name, i, k), x, -0.6, z0 + 0.1 + k * 0.17, SLOT_W - 0.1 + (0.05 if k % 2 else 0), 0.12, 0.13,
                    mat("wicker%d" % (k % 2), wicker if k % 2 == 0 else wicker_d, 0.9), bevel=0.05)
            cyl("%s%d_handle" % (name, i), x, -0.3, z0 + 0.62, 0.03, SLOT_W - 0.4, mat("wicker_d", wicker_d, 0.9), axis="x", segs=8)
    CUR["c"] = back
    box("board", 0, 1.4, 3.25, 5.0, 0.12, 1.0, mat("chalk", (0.15, 0.2, 0.17), 0.9))
    box("boardframe", 0, 1.45, 3.25, 5.3, 0.1, 1.25, mat("table", WOOD_L, 0.6))


def build_padaria(back, front):
    CUR["c"] = back
    box("cabinet", 0, 0.9, -0.4, 11.2, 1.2, 7.2, mat("bak", WOOD, 0.6), bevel=0.12)
    box("inner", 0, 0.25, -0.5, 10.4, 0.1, 6.0, mat("bak_in", (0.95, 0.86, 0.68), 0.7), bevel=0)
    for z in (TOP_Z[0], BOT_Z[0]):
        box("shelf%.1f" % z, 0, -0.1, z - 0.05, 10.6, 1.4, 0.1, mat("bak_l", WOOD_L, 0.6), bevel=0.02)
    box("light", 0, 0.2, 2.45, 10.2, 0.4, 0.12, mat("warm", (1.0, 0.85, 0.55), 0.3, emission=3.0), bevel=0.02)
    box("signboard", 0, 0.7, 3.3, 11.4, 0.5, 1.1, mat("bak_d", WOOD_D, 0.6), bevel=0.1)
    box("signface", 0, 0.42, 3.3, 7.0, 0.05, 0.8, mat("signcream", CREAM, 0.6), bevel=0.02)
    CUR["c"] = front
    for z in (TOP_Z[0], BOT_Z[0]):
        box("lip%.1f" % z, 0, -0.75, z + 0.12, 10.6, 0.1, 0.26, mat("bak_l", WOOD_L, 0.6), bevel=0.03)
    box("plinth", 0, -0.65, -3.55, 11.2, 0.3, 0.75, mat("bak_d", WOOD_D, 0.6), bevel=0.05)
    g = mat("glass", (0.9, 0.96, 1.0), 0.02, alpha=0.07)
    box("guard", 0, -1.0, 0.0, 10.8, 0.03, 4.0, g, bevel=0, rot=(-0.08, 0, 0))
    box("glint", -2.5, -1.03, 0.4, 0.2, 0.01, 3.0, mat("glint", (1, 1, 1), 0.1, alpha=0.3), bevel=0, rot=(0, 0.35, 0))


def build_balcao(back, front):
    CUR["c"] = back
    box("wall", 0, 1.2, -0.3, 11.6, 0.2, 7.4, mat("tile", (0.93, 0.92, 0.88), 0.8), bevel=0)
    box("body", 0, 0.2, -2.6, 11.4, 1.6, 2.4, mat("counter", (0.55, 0.36, 0.58), 0.45, coat=0.3), bevel=0.12)
    box("inner", 0, 0.3, -0.3, 10.8, 0.1, 5.4, mat("counter_in", (0.96, 0.95, 0.93), 0.6), bevel=0)
    for z in (TOP_Z[0], BOT_Z[0]):
        box("tray%.1f" % z, 0, -0.1, z - 0.05, 10.6, 1.4, 0.1, mat("chromeshelf", STEEL, 0.25, 0.9), bevel=0.02)
    box("light", 0, 0.2, 2.45, 10.4, 0.4, 0.12, mat("light", (0.95, 0.97, 1.0), 0.3, emission=3.0), bevel=0.02)
    box("signboard", 0, 0.9, 3.3, 11.4, 0.5, 1.1, mat("counter", (0.55, 0.36, 0.58), 0.45, coat=0.3), bevel=0.1)
    box("signface", 0, 0.62, 3.3, 7.0, 0.05, 0.8, mat("signcream", CREAM, 0.6), bevel=0.02)
    CUR["c"] = front
    g = mat("glass", (0.85, 0.93, 1.0), 0.02, alpha=0.14)
    box("glass", 0, -1.0, 0.1, 10.8, 0.03, 5.0, g, bevel=0)
    for s in (-1, 1):
        box("gpost%d" % s, s * 5.45, -1.0, 0.1, 0.12, 0.12, 5.1, mat("chrome", STEEL, 0.15, 1.0), bevel=0.03)
    box("gtop", 0, -1.0, 2.62, 11.0, 0.12, 0.12, mat("chrome", STEEL, 0.15, 1.0), bevel=0.03)
    box("glint", -2.5, -1.03, 0.4, 0.2, 0.01, 3.4, mat("glint", (1, 1, 1), 0.1, alpha=0.3), bevel=0, rot=(0, 0.35, 0))
    box("front", 0, -0.75, -3.4, 11.4, 0.2, 1.0, mat("counter_f", (0.45, 0.28, 0.48), 0.45, coat=0.3), bevel=0.08)


BUILDERS = {
    "caixotes": build_caixotes,
    "banca": build_banca,
    "isopor": build_isopor,
    "geladeira": build_geladeira,
    "expositor": build_expositor,
    "cesto": build_cesto,
    "padaria": build_padaria,
    "gondola": build_gondola,
    "freezer": build_freezer,
    "chest": build_chest,
    "balcao": build_balcao,
}


def build(name):
    sc = scene()
    root = coll("FA_Root")
    back = coll("FA_%s_back" % name)
    front = coll("FA_%s_front" % name)
    clear(back)
    clear(front)
    BUILDERS[name](back, front)
    fix_scales(back)
    fix_scales(front)
    camera_and_lights(sc, root)
    return back, front


def render(names=None, out=OUT):
    os.makedirs(out, exist_ok=True)
    sc = scene()
    done = []
    for name in names or list(BUILDERS):
        back, front = build(name)
        for layer in ("back", "front"):
            for c in sc.collection.children:
                if c.name.startswith("FA_") and c.name != "FA_Root":
                    c.hide_render = c.name != "FA_%s_%s" % (name, layer)
            sc.render.filepath = os.path.join(out, "%s_%s.png" % (name, layer))
            bpy.ops.render.render(write_still=True, scene=sc.name)
            done.append(sc.render.filepath)
    return done


def render_all():
    return render(None)
