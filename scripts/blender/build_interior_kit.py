"""Interior Kit and city decorations for build mode, modelled in Blender.

Run inside the connected Blender (exec) or: blender -b --python scripts/blender/build_interior_kit.py [-- name ...]
Every model is exported as one FBX to Assets/Art/Interior/Models/<name>.fbx and a shop thumbnail is rendered to
Assets/Resources/CheckoutDesktop/Decor/<name>.png.

Design space is Unity's: metres, +Y up, the customer side is -Z. U() converts to Blender (the FBX export and
Unity's import turn Blender (x, y, z) into Unity (-x, z, -y)).
Material naming contract with CheckoutInteriorKitBuilder (Unity):
    C_RRGGBB   painted colour (MarketDay/Soft Painted, warm ink contour)
    T_<tex>    painted texture from Assets/Art/Interior/Textures/<tex>_albedo.png (metric UVs)
    S_RRGGBB   striped awning cloth tinted with that colour
    E_RRGGBB   glowing (emissive) part
    G_Glass    glass
Static parts are merged into one object "Body"; nodes named "Anim Bob", "Anim Sway", "Anim Blink", "Anim Spin"
or "Anim Scroll" stay separate so CheckoutInteriorLife can move them.
"""
import math
import os
import bpy
import bmesh
from mathutils import Vector, Matrix

UNITY = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets"
OUT = os.path.join(UNITY, "Art", "Interior", "Models")
THUMBS = os.path.join(UNITY, "Resources", "CheckoutDesktop", "Decor")
TEX = os.path.join(UNITY, "Art", "Interior", "Textures")
FONT = os.path.join(UNITY, "Resources", "CheckoutDesktop", "Fonts", "Fredoka_700Bold.ttf")

# Market palette.
NAVY, GOLD, GOLDL, CREAM, WHITE = "1D2B4F", "E0B040", "FFD97A", "F4EFE4", "FBF8F1"
TEAL, TEALD, RED, ORANGE, PINK = "1F9A8E", "17655D", "D74A3C", "EC862E", "EE8FAE"
WOOD, WOODL, WOODD, STEEL, DARK = "AB6537", "D69C53", "6B4128", "C9D2D6", "2F3A40"
GREEN, LEAF, LEAFD, BLUE, PURPLE = "5A9D33", "5DAE3E", "2F6F2C", "3E8FD6", "8E6CCF"

SECTORS = {
    "padaria": ("PADARIA", "D98E2B"), "queijaria": ("QUEIJARIA", "8E6CCF"), "acougue": ("AÇOUGUE", "D64541"),
    "peixaria": ("PEIXARIA", "2E86DE"), "bebidas": ("BEBIDAS", "27AE60"), "sorvetes": ("SORVETES", "E86A9E"),
    "adega": ("ADEGA", "8E2240"),
}


def U(x, y, z):
    return Vector((-x, -z, y))


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c)


# ------------------------------------------------------------------------------------------- materials (preview)
def material(key):
    m = bpy.data.materials.get(key)
    if m:
        return m
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = .7
    if key.startswith("C_") or key.startswith("S_"):
        bsdf.inputs["Base Color"].default_value = (*srgb(key[2:8]), 1)
        if key.startswith("S_"):
            img = load_tex("IK_Stripes")
            if img:
                tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
                mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
                mix.inputs["Factor"].default_value = 1
                mix.inputs["A"].default_value = (*srgb(key[2:8]), 1)
                nt.links.new(tex.outputs["Color"], mix.inputs["B"])
                nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    elif key.startswith("T_"):
        img = load_tex(key[2:])
        if img:
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    elif key.startswith("E_"):
        col = (*srgb(key[2:8]), 1)
        bsdf.inputs["Base Color"].default_value = col
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = 2.5
    elif key == "G_Glass":
        bsdf.inputs["Base Color"].default_value = (.8, .92, 1, 1)
        bsdf.inputs["Alpha"].default_value = .25
        bsdf.inputs["Roughness"].default_value = .05
        m.surface_render_method = "BLENDED"
    m.diffuse_color = tuple(bsdf.inputs["Base Color"].default_value)
    return m


def load_tex(name):
    path = os.path.join(TEX, name + "_albedo.png")
    if not os.path.exists(path):
        return None
    img = bpy.data.images.get(name + "_albedo.png") or bpy.data.images.load(path)
    return img


# ------------------------------------------------------------------------------------------- geometry
class Model:
    """Collects parts per output object; everything is one bmesh per object with material slots."""

    def __init__(self, name):
        self.name = name
        self.objects = {}   # object name -> (bmesh, [materials])
        self.anim_count = {}

    def target(self, obj):
        if obj not in self.objects:
            bm = bmesh.new()
            bm.loops.layers.uv.new("UVMap")
            self.objects[obj] = (bm, [])
        return self.objects[obj]

    def anim(self, kind):
        n = self.anim_count.get(kind, 0)
        self.anim_count[kind] = n + 1
        return kind if n == 0 else "%s.%03d" % (kind, n)

    def add(self, part, key, obj="Body", uv="metric"):
        """part: bmesh already in Blender space. Merged into `obj` with material `key`."""
        bm, mats = self.target(obj)
        if key not in mats:
            mats.append(key)
        index = mats.index(key)
        uvl = part.loops.layers.uv.get("UVMap") or part.loops.layers.uv.new("UVMap")
        if uv == "metric":
            uv_metric(part, uvl)
        elif uv == "fit":
            uv_fit(part, uvl)
        for f in part.faces:
            f.material_index = index
        mesh = bpy.data.meshes.new("tmp")
        part.to_mesh(mesh)
        part.free()
        bm.from_mesh(mesh)
        bpy.data.meshes.remove(mesh)


def uv_metric(bm, uvl):
    """UVs in metres, projected from each face's dominant axis (in Unity space: u across, v up)."""
    for f in bm.faces:
        n = f.normal
        a = (abs(n.x), abs(n.y), abs(n.z))
        for l in f.loops:
            co = l.vert.co  # Blender space: x=-ux, y=-uz, z=uy
            ux, uy, uz = -co.x, co.z, -co.y
            if a[2] >= a[0] and a[2] >= a[1]:      # Unity Y faces (tops)
                l[uvl].uv = (ux, uz)
            elif a[0] >= a[1]:                     # Unity X faces (sides)
                l[uvl].uv = (uz * (1 if n.x < 0 else -1), uy)
            else:                                  # Unity Z faces (front/back)
                l[uvl].uv = (ux * (1 if n.y > 0 else -1), uy)


def uv_fit(bm, uvl):
    """0..1 over the part's front (for printed cards and screens)."""
    xs = [-v.co.x for v in bm.verts]; ys = [v.co.z for v in bm.verts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = ((-l.vert.co.x - x0) / max(1e-6, x1 - x0), (l.vert.co.z - y0) / max(1e-6, y1 - y0))


def _place(bm, center, pitch=0, yaw=0, roll=0):
    # Unity rotation (pitch about X, then yaw about Y) expressed in Blender space.
    rot = Matrix.Rotation(math.radians(-yaw), 4, "Z") @ Matrix.Rotation(math.radians(pitch), 4, "X") @ Matrix.Rotation(math.radians(-roll), 4, "Y")
    bmesh.ops.transform(bm, matrix=Matrix.Translation(U(*center)) @ rot, verts=bm.verts)
    return bm


def box_bm(size, bevel=.02, seg=2):
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=Vector((sx, sz, sy)), verts=bm.verts)
    b = min(bevel, sx * .45, sy * .45, sz * .45)
    if b > .0005:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=b, segments=seg, affect="EDGES", profile=.5)
    return bm


def box(m, size, center, key, bevel=.02, seg=2, pitch=0, yaw=0, roll=0, obj="Body", uv="metric"):
    m.add(_place(box_bm(size, bevel, seg), center, pitch, yaw, roll), key, obj, uv)


def lathe_bm(profile, seg=24, cap=True):
    """profile: [(radius, height)] bottom to top, revolved around Unity Y."""
    bm = bmesh.new()
    rings = []
    for r, h in profile:
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, h)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(seg):
            a, b = rings[i][k], rings[i][(k + 1) % seg]
            c, d = rings[i + 1][(k + 1) % seg], rings[i + 1][k]
            try:
                bm.faces.new((a, b, c, d))
            except ValueError:
                pass
    if cap:
        if profile[-1][0] > .0005:
            bm.faces.new(rings[-1])
        if profile[0][0] > .0005:
            bm.faces.new(list(reversed(rings[0])))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.00005)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def lathe(m, profile, base, key, seg=24, pitch=0, yaw=0, roll=0, obj="Body", cap=True, smooth=True):
    bm = lathe_bm(profile, seg, cap)
    for f in bm.faces:
        f.smooth = smooth
    m.add(_place(bm, base, pitch, yaw, roll), key, obj)


def cyl(m, r, h, base, key, seg=20, bevel=0, pitch=0, yaw=0, roll=0, obj="Body"):
    b = min(bevel, r * .4, h * .4)
    if b > 0:
        prof = [(0, 0), (r - b, 0), (r - b * .3, b * .3), (r, b), (r, h - b), (r - b * .3, h - b * .3), (r - b, h), (0, h)]
    else:
        prof = [(r, 0), (r, h)]
    lathe(m, prof, base, key, seg, pitch, yaw, roll, obj)


def ball(m, center, size, key, seg=16, rings=10, obj="Body", pitch=0, yaw=0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=.5)
    sx, sy, sz = size
    bmesh.ops.scale(bm, vec=Vector((sx, sz, sy)), verts=bm.verts)
    for f in bm.faces:
        f.smooth = True
    m.add(_place(bm, center, pitch, yaw), key, obj)


def bar(m, a, b, r, key, seg=10, obj="Body"):
    a, b = U(*a), U(*b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length)
    for f in bm.faces:
        f.smooth = len(f.verts) == 4
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ rot, verts=bm.verts)
    m.add(bm, key, obj)


def torus(m, R, r, center, key, pitch=0, yaw=0, obj="Body", seg=24, minor=8, roll=0):
    bm = bmesh.new()
    for i in range(seg):
        for j in range(minor):
            pass
    verts = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ring = []
        for j in range(minor):
            b = 2 * math.pi * j / minor
            ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        verts.append(ring)
    for i in range(seg):
        for j in range(minor):
            a, b = verts[i][j], verts[(i + 1) % seg][j]
            c, d = verts[(i + 1) % seg][(j + 1) % minor], verts[i][(j + 1) % minor]
            f = bm.faces.new((a, b, c, d)); f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m.add(_place(bm, center, pitch, yaw, roll), key, obj)


def quad(m, w, h, center, key, yaw=0, pitch=0, obj="Body", thick=.004):
    """A thin printed card facing the customer (-Z), UVs 0..1."""
    m.add(_place(box_bm((w, h, thick), 0), center, pitch, yaw), key, obj, uv="fit")


def text(m, value, center, size, key, depth=.02, yaw=0, obj="Body", bevel=.004):
    """3D letters in the game font, facing the customer."""
    font = bpy.data.fonts.get("Fredoka_700Bold") or bpy.data.fonts.load(FONT)
    font.name = "Fredoka_700Bold"
    cu = bpy.data.curves.new("txt", type="FONT")
    cu.body = value; cu.font = font; cu.size = size; cu.align_x = "CENTER"; cu.align_y = "CENTER"
    cu.extrude = depth * .5; cu.bevel_depth = bevel; cu.bevel_resolution = 1; cu.resolution_u = 4
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    # Text lies in the XY plane facing +Z: stand it up facing Unity -Z (Blender +Y), reading left to right.
    basis = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=basis, verts=bm.verts)
    m.add(_place(bm, center, 0, yaw), key, obj, uv="none")


def prism_bm(points, thick):
    """A flat shape drawn in Unity XY (x, y) with `thick` depth along Unity Z, centred on z = 0."""
    bm = bmesh.new()
    front = [bm.verts.new(U(x, y, -thick / 2)) for x, y in points]
    back = [bm.verts.new(U(x, y, thick / 2)) for x, y in points]
    bm.faces.new(front); bm.faces.new(list(reversed(back)))
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def prism(m, points, thick, center, key, pitch=0, yaw=0, obj="Body", uv="metric"):
    bm = prism_bm(points, thick)
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.radians(-yaw), 4, "Z") @ Matrix.Rotation(math.radians(pitch), 4, "X"), verts=bm.verts)
    bmesh.ops.translate(bm, vec=U(*center), verts=bm.verts)
    m.add(bm, key, obj, uv)


def arc_points(r, a0, a1, n, cx=0, cy=0):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def scallops(m, width, center, key, r=.07, yaw=0, obj="Body", thick=.018):
    """Row of half-discs hanging under an awning edge (Unity x across, hanging down from center y)."""
    n = max(3, int(round(width / (r * 2))))
    step = width / n
    for i in range(n):
        x = -width / 2 + step * (i + .5)
        pts = arc_points(step * .5, 180, 360, 10)
        prism(m, pts, thick, (center[0] + x * math.cos(math.radians(yaw)), center[1], center[2] - x * math.sin(math.radians(yaw))), key, 0, yaw, obj)


def awning(m, width, depth, top, front_z, key, slope=20, yaw=0, obj="Body"):
    """Striped canopy sloping down towards the customer, with a scalloped valance."""
    zc = front_z + depth / 2 * math.cos(math.radians(slope))
    box(m, (width, .03, depth), (0, top, zc), key, .01, 1, pitch=-slope, yaw=yaw, obj=obj)
    lowy = top - depth / 2 * math.sin(math.radians(slope))
    box(m, (width + .02, .12, .02), (0, lowy - .05, front_z), key, .006, 1, yaw=yaw, obj=obj)
    scallops(m, width, (0, lowy - .11, front_z), key, .075, yaw, obj)


# ------------------------------------------------------------------------------------------- export
def clear_scene():
    sc = bpy.data.scenes.get("IK") or bpy.data.scenes.new("IK")
    bpy.context.window.scene = sc
    for o in list(sc.objects):
        bpy.data.objects.remove(o)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    return sc


def realize(m):
    sc = bpy.context.scene
    objs = []
    for name, (bm, mats) in m.objects.items():
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.00002)
        me = bpy.data.meshes.new(m.name + "_" + name)
        bm.to_mesh(me); bm.free()
        for key in mats:
            me.materials.append(material(key))
        ob = bpy.data.objects.new(name, me)
        sc.collection.objects.link(ob)
        if name != "Body" and me.vertices:
            # Animated parts pivot on their own base (sway, bob, spin in place).
            xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
            pivot = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs) if name.startswith("Anim Sway") else (min(zs) + max(zs)) / 2))
            me.transform(Matrix.Translation(-pivot))
            ob.location = pivot
        # Soft, rounded shading with flat faces kept flat.
        for p in me.polygons:
            if not p.use_smooth:
                p.use_smooth = True
        wn = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        wn.keep_sharp = True; wn.weight = 100
        objs.append(ob)
    return objs


def export(m):
    os.makedirs(OUT, exist_ok=True)
    clear_scene()
    objs = realize(m)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, m.name + ".fbx"), use_selection=True, object_types={"MESH"},
                             axis_forward="-Z", axis_up="Y", bake_anim=False, path_mode="STRIP",
                             use_mesh_modifiers=True, mesh_smooth_type="OFF", apply_scale_options="FBX_SCALE_ALL",
                             use_tspace=False)
    return objs


def thumbnail(name, objs, size=256):
    os.makedirs(THUMBS, exist_ok=True)
    sc = bpy.context.scene
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    center = (lo + hi) / 2
    radius = max((hi - lo).length * .5, .3)
    cam = bpy.data.objects.get("IK_Cam")
    if not cam:
        cam = bpy.data.objects.new("IK_Cam", bpy.data.cameras.new("IK_Cam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = radius * 2.1
    # Three-quarter view from the customer side (Blender +Y) and a little from the left.
    d = Vector((.55, 1, .75)).normalized()
    cam.location = center + d * (radius * 6)
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = radius * 20
    sc.camera = cam
    sun = bpy.data.objects.get("IK_Sun")
    if not sun:
        sun = bpy.data.objects.new("IK_Sun", bpy.data.lights.new("IK_Sun", "SUN"))
    if sun.name not in sc.collection.objects:
        sc.collection.objects.link(sun)
    sun.data.energy = 2.4; sun.rotation_euler = (math.radians(40), math.radians(10), math.radians(150))
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    if not sc.world:
        sc.world = bpy.data.worlds.new("IK_World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (1, .97, .9, 1); bg.inputs["Strength"].default_value = .55
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = -.15
    sc.render.filepath = os.path.join(THUMBS, name + ".png")
    bpy.ops.render.render(write_still=True)


BUILDERS = {}


def model(name):
    def wrap(fn):
        BUILDERS[name] = fn
        return fn
    return wrap


def build(names=None, thumbs=True):
    done = []
    for name in names or list(BUILDERS):
        m = Model(name)
        BUILDERS[name](m)
        objs = export(m)
        if thumbs:
            thumbnail(name, objs)
        done.append(name)
    return done


# =========================================================================================== shared details
def rounded_panel(m, w, h, center, key, thick=.05, r=.06, yaw=0, obj="Body"):
    """Sign board with rounded corners (Unity XY), thickness along Z."""
    r = min(r, w * .45, h * .45)
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        pts += arc_points(r, a0, a0 + 90, 5, cx, cy)
    prism(m, pts, thick, center, key, 0, yaw, obj)


def sign(m, label, center, w, h=.3, letter=.15, board=NAVY, frame=GOLD, ink=GOLDL, yaw=0):
    x, y, z = center
    rounded_panel(m, w + .05, h + .05, (x, y, z + .008), "C_" + frame, .04, .07, yaw)
    rounded_panel(m, w, h, (x, y, z - .012), "C_" + board, .04, .06, yaw)
    tz = z - .04
    text(m, label, (x, y - letter * .04, tz), letter, "C_" + ink, .025, yaw)


def price_tags(m, xs, y, z, colors=(GOLD, "F2C23F", RED)):
    for i, x in enumerate(xs):
        box(m, (.07, .045, .006), (x, y, z), "C_" + colors[i % len(colors)], .004, 1)


def wobbler(m, x, y, z, col=RED):
    """Round 'OFERTA' tag sticking out of a shelf edge."""
    bar(m, (x, y, z), (x, y, z - .06), .004, "C_" + STEEL, 6)
    cyl(m, .045, .008, (x, y + .0, z - .08), "C_" + col, 16, 0, pitch=90)


# =========================================================================================== shelves
def gondola(m, title):
    box(m, (1.9, .12, .6), (0, .06, 0), "C_" + NAVY, .03)
    box(m, (1.92, .025, .03), (0, .125, -.3), "C_" + GOLD, .01)
    box(m, (1.82, 1.66, .04), (0, 1.0, .27), "T_IK_Pegboard", .01)
    box(m, (1.86, .06, .06), (0, 1.84, .27), "C_" + NAVY, .02)
    for x in (-.925, .925):
        box(m, (.06, 1.78, .6), (x, 1.0, 0), "C_" + CREAM, .025)
        box(m, (.075, .05, .64), (x, 1.9, 0), "C_" + GOLD, .02)
        box(m, (.075, .1, .64), (x, .05, 0), "C_" + NAVY, .02)
        cyl(m, .02, .012, (x, 1.93, -.28), "C_" + GOLD, 12)
    for y in (.16, .52, .88, 1.24, 1.6):
        box(m, (1.8, .028, .52), (0, y, -.02), "C_" + CREAM, .012)
        box(m, (1.8, .05, .014), (0, y - .006, -.285), "T_IK_PriceRail", .004, 1)
    for x in (-.55, .6):
        pass
    wobbler(m, -.5, .88, -.3)
    wobbler(m, .62, 1.24, -.3, "F2C23F")
    for x in (-.55, .55):
        bar(m, (x, 1.86, .24), (x, 2.0, .24), .012, "C_" + GOLD, 8)
    sign(m, title, (0, 2.1, .22), 1.5, .3, .13)


@model("shelf-grocery")
def shelf_grocery(m): gondola(m, "MERCEARIA")


@model("shelf-snacks")
def shelf_snacks(m): gondola(m, "DOCES & SNACKS")


@model("shelf-cleaning")
def shelf_cleaning(m): gondola(m, "LIMPEZA")


@model("shelf-cooler")
def shelf_cooler(m):
    box(m, (1.9, .18, .8), (0, .09, .02), "C_" + NAVY, .04)
    box(m, (1.8, .08, .02), (0, .09, -.39), "C_" + DARK, .01)
    for x in range(-8, 9):
        box(m, (.05, .012, .01), (x * .1, .09, -.4), "C_" + STEEL, .003, 1)
    box(m, (1.84, 1.86, .04), (0, 1.1, .4), "C_" + WHITE, .01)
    for x in (-.93, .93):
        box(m, (.05, 1.96, .82), (x, 1.07, .02), "C_" + NAVY, .025)
    box(m, (1.92, .1, .84), (0, 2.08, .02), "C_" + NAVY, .035)
    box(m, (1.92, .03, .03), (0, 2.02, -.4), "C_" + GOLD, .01)
    for y in (.2, .6, 1.0, 1.4):
        box(m, (1.82, .02, .7), (0, y, .02), "C_" + STEEL, .006, 1)
        box(m, (1.82, .04, .012), (0, y + .01, -.33), "T_IK_PriceRail", .003, 1)
    box(m, (1.8, .025, .06), (0, 1.98, -.12), "E_FFF4DC", .008, 1)
    for i, x in enumerate((-.62, 0, .62)):
        box(m, (.6, .05, .04), (x, 1.96, -.37), "C_" + STEEL, .015)
        box(m, (.6, .05, .04), (x, .2, -.37), "C_" + STEEL, .015)
        box(m, (.045, 1.8, .04), (x - .28, 1.08, -.37), "C_" + STEEL, .015)
        box(m, (.045, 1.8, .04), (x + .28, 1.08, -.37), "C_" + STEEL, .015)
        box(m, (.52, 1.72, .012), (x, 1.08, -.385), "G_Glass", .002, 1)
        hx = x + (.2 if i < 2 else -.2)
        bar(m, (hx, .85, -.42), (hx, 1.35, -.42), .016, "C_" + STEEL, 10)
        for yy in (.85, 1.35):
            bar(m, (hx, yy, -.39), (hx, yy, -.42), .01, "C_" + STEEL, 6)
    rounded_panel(m, 1.7, .24, (0, 2.3, -.3), "E_2FB7A8", .08, .1)
    text(m, "BEBIDAS GELADAS", (0, 2.29, -.35), .12, "C_" + WHITE, .02)
    for x in (-.7, .7):
        bar(m, (x, 2.12, -.3), (x, 2.18, -.3), .015, "C_" + GOLD, 8)


@model("shelf-dairy")
def shelf_dairy(m):
    box(m, (1.9, .5, .9), (0, .25, -.05), "C_" + NAVY, .05)
    box(m, (1.92, .04, .04), (0, .5, -.5), "C_" + GOLD, .012)
    box(m, (1.82, .025, .02), (0, .08, -.5), "C_" + STEEL, .006)
    box(m, (1.84, .04, .86), (0, .52, -.05), "C_" + WHITE, .01)
    box(m, (1.9, 1.45, .08), (0, 1.22, .38), "C_" + WHITE, .02)
    # Side panels curving from the deep base up to the canopy.
    side = [(-.5, 0), (.42, 0), (.42, 1.97), (.1, 1.97), (-.05, 1.8), (-.15, 1.2), (-.3, .95), (-.5, .55)]
    for x in (-.93, .93):
        prism(m, [(z, y) for z, y in side], .04, (x, 0, 0), "C_" + NAVY, 0, -90)
    box(m, (1.92, .1, .72), (0, 1.99, .06), "C_" + NAVY, .04)
    box(m, (1.8, .02, .06), (0, 1.93, -.12), "E_FFF4DC", .006, 1)
    for y, d in ((.9, .5), (1.2, .44), (1.5, .38)):
        box(m, (1.84, .025, d), (0, y, .34 - d / 2), "C_" + STEEL, .006)
        box(m, (1.84, .045, .012), (0, y - .005, .34 - d - .006), "T_IK_PriceRail", .003, 1)
    box(m, (1.84, .22, .02), (0, .63, -.49), "G_Glass", .003, 1, pitch=-8)
    rounded_panel(m, 1.7, .2, (0, 2.12, -.26), "E_5DA0D8", .06, .09)
    text(m, "LATICÍNIOS & FRIOS", (0, 2.11, -.3), .1, "C_" + WHITE, .02)


@model("shelf-produce")
def shelf_produce(m):
    box(m, (1.9, .4, 1.1), (0, .2, -.05), "T_IK_WoodLight", .03)
    box(m, (1.94, .05, 1.14), (0, .025, -.05), "C_" + NAVY, .015)
    box(m, (1.94, .03, .03), (0, .4, -.6), "C_" + GOLD, .01)
    tiers = ((.42, -.38), (.66, -.05), (.9, .28))
    for t, (y, z) in enumerate(tiers):
        if t > 0:
            box(m, (1.86, y - .4, .32), (0, (y + .4) / 2, z), "T_IK_WoodLight", .012)
        for x in (-.62, 0, .62):
            # Crate: slatted box tilted towards the customer.
            for part, size, off in (("b", (.58, .03, .32), (0, .02, 0)), ("f", (.58, .12, .025), (0, .07, -.155)),
                                    ("k", (.58, .12, .025), (0, .07, .155)), ("l", (.025, .12, .32), (-.28, .07, 0)),
                                    ("r", (.025, .12, .32), (.28, .07, 0))):
                c = (x + off[0], y + off[1] * math.cos(math.radians(10)) + off[2] * math.sin(math.radians(10)), z + off[2] * math.cos(math.radians(10)) - off[1] * math.sin(math.radians(10)))
                box(m, size, c, "T_IK_Crate", .006, 1, pitch=-10)
            box(m, (.12, .07, .006), (x, y + .09, z - .175), "C_" + CREAM, .005, 1, pitch=-10)
    box(m, (1.9, 1.3, .06), (0, 1.05, .47), "T_IK_WoodLight", .02)
    for x in (-.93, .93):
        box(m, (.07, 1.9, .07), (x, .95, .47), "T_IK_WoodLight", .02)
    awning(m, 1.98, .42, 1.66, .15, "S_3FA34D", 18)
    sign(m, "HORTIFRUTI", (0, 1.95, .42), 1.3, .28, .13, board="2F6F2C")


@model("shelf-freezer")
def shelf_freezer(m):
    box(m, (1.9, .72, .95), (0, .42, 0), "C_" + WHITE, .08, 3)
    box(m, (1.86, .1, .9), (0, .05, 0), "C_" + DARK, .02)
    box(m, (1.92, .07, .04), (0, .5, -.48), "C_" + NAVY, .02)
    box(m, (1.92, .07, .04), (0, .5, .48), "C_" + NAVY, .02)
    box(m, (1.92, .04, .97), (0, .78, 0), "C_" + STEEL, .015)
    box(m, (1.8, .02, .85), (0, .5, 0), "C_E3F1F8", .005, 1)
    box(m, (.92, .014, .9), (-.46, .81, 0), "G_Glass", .003, 1)
    box(m, (.92, .014, .9), (.46, .83, 0), "G_Glass", .003, 1)
    box(m, (.04, .035, .92), (0, .84, 0), "C_" + STEEL, .012)
    for x in (-.93, .93):
        box(m, (.04, .035, .92), (x, .82, 0), "C_" + STEEL, .012)
    bar(m, (0, .85, .44), (0, 1.5, .44), .02, "C_" + STEEL, 10)
    sign(m, "CONGELADOS", (0, 1.62, .43), 1.15, .28, .12, board="2E86DE", ink=WHITE)


@model("shelf-bakery")
def shelf_bakery(m):
    box(m, (1.92, .16, .8), (0, .08, 0), "C_" + NAVY, .04)
    for x in (-.92, .92):
        box(m, (.07, 1.62, .78), (x, .9, 0), "T_IK_WoodLight", .025)
    box(m, (1.8, 1.6, .03), (0, .9, .37), "T_IK_WoodLight", .006)
    prism(m, arc_points(.95, 0, 180, 18), .08, (0, 1.68, .3), "T_IK_WoodLight")
    prism(m, arc_points(.8, 0, 180, 18), .085, (0, 1.68, .3), "C_" + CREAM)
    for y in (.3, .72, 1.14):
        box(m, (1.8, .03, .66), (0, y, 0), "T_IK_WoodLight", .01, pitch=-14)
        lipy = y + .04 - .33 * math.sin(math.radians(14))
        box(m, (1.8, .07, .02), (0, lipy, -.33 * math.cos(math.radians(14))), "T_IK_WoodLight", .006, pitch=-14)
    text(m, "PÃES", (0, 2.02, .27), .16, "C_" + GOLDL, .03)
    box(m, (.9, .26, .04), (0, 2.02, .31), "C_B8672A", .04)


# =========================================================================================== sector counters
def sector(m, sid):
    title, hexc = SECTORS[sid]
    staffed = sid in ("padaria", "queijaria", "acougue", "peixaria")
    accent = "C_" + hexc
    wall = {"peixaria": "T_IK_Tile", "acougue": "T_IK_Tile", "adega": "T_IK_WoodLight"}.get(sid, "C_" + CREAM)
    box(m, (2.8, 2.44, .1), (0, 1.22, 1.44), wall, .02)
    box(m, (2.8, .22, .07), (0, .11, 1.37), accent, .02)
    box(m, (2.82, .04, .04), (0, .23, 1.36), "C_" + GOLD, .012)
    for x in (-1.35, 1.35):
        box(m, (.12, 2.56, .32), (x, 1.28, 1.3), accent, .035)
        box(m, (.14, .06, .34), (x, 2.58, 1.3), "C_" + GOLD, .02)
        box(m, (.14, .1, .34), (x, .05, 1.3), "C_" + NAVY, .02)
    awning(m, 2.86, .62, 2.24, .86, "S_" + hexc, 20)
    rounded_panel(m, 2.3, .52, (0, 2.66, 1.39), "C_" + GOLD, .06, .1)
    rounded_panel(m, 2.22, .44, (0, 2.66, 1.36), "C_" + NAVY, .06, .08)
    text(m, title, (0, 2.64, 1.31), .24, "C_" + GOLDL, .04)
    if staffed or sid == "sorvetes":
        front = {"padaria": "T_IK_WoodLight", "sorvetes": "C_F6D6E1"}.get(sid, "T_IK_Tile")
        box(m, (2.7, .96, .8), (0, .52, -.2), front, .04)
        box(m, (2.66, .1, .76), (0, .05, -.2), "C_" + NAVY, .02)
        box(m, (2.72, .1, .03), (0, .84, -.605), accent, .015)
        box(m, (2.72, .03, .03), (0, .9, -.61), "C_" + GOLD, .01)
        box(m, (2.78, .05, .88), (0, 1.02, -.2), "T_IK_Marble", .02)
        box(m, (2.5, .03, .5), (0, 1.06, -.28), "C_E8F4FA" if sid == "peixaria" else "C_" + WHITE, .01, 1)
        # Curved glass sneeze guard: bent pane built from narrow strips.
        pts = arc_points(.44, 180, 270, 8, 0, 0)
        for i in range(len(pts) - 1):
            (z0, y0), (z1, y1) = pts[i], pts[i + 1]
            zc, yc = (z0 + z1) / 2, (y0 + y1) / 2
            ang = math.degrees(math.atan2(y1 - y0, z1 - z0))
            box(m, (2.5, .012, math.hypot(z1 - z0, y1 - y0) + .004), (0, 1.5 + yc, -.1 + zc), "G_Glass", .002, 1, pitch=-ang)
        box(m, (2.5, .012, .3), (0, 1.5, -.02), "G_Glass", .002, 1)
        for x in (-1.26, 1.26):
            box(m, (.03, .5, .5), (x, 1.3, -.32), "C_" + STEEL, .01)
        box(m, (2.4, .02, .04), (0, 1.49, -.08), "E_FFF4DC", .006, 1)
        box(m, (2.6, .9, .36), (0, .45, 1.2), "T_IK_Steel", .02)
        box(m, (2.64, .04, .4), (0, .92, 1.2), "T_IK_Marble", .01)
    else:
        for l in range(3):
            box(m, (2.6, .035, .34), (0, .55 + l * .5, 1.25), "T_IK_WoodLight" if sid == "adega" else "T_IK_Steel", .01)
            for x in (-1.25, 1.25):
                box(m, (.04, .04, .34), (x, .5 + l * .5, 1.25), "C_" + NAVY, .01)
        box(m, (2.5, .74, .8), (0, .39, -.15), "T_IK_WoodLight" if sid == "adega" else "C_" + NAVY, .04)
        box(m, (2.56, .04, .86), (0, .78, -.15), "C_5B2A1E" if sid == "adega" else "T_IK_Marble", .015)
        box(m, (2.5, .08, .02), (0, .6, -.56), accent, .01)
    if sid == "padaria":
        lathe(m, [(0, 0), (.42, 0), (.44, .1), (.42, .35), (.34, .55), (.2, .66), (0, .7)], (.85, .95, 1.18), "C_B5563A", 20)
        prism(m, arc_points(.17, 0, 180, 10) + [(-.17, -.05), (.17, -.05)], .03, (.85, 1.12, .8), "E_FF8A2A")
        box(m, (.1, .3, .1), (.85, 1.75, 1.2), "C_7A3A28", .02)
        for i in range(3):
            lathe(m, [(0, 0), (.13, 0), (.16, .08), (.17, .1)], (-.95 + i * .36, .94, 1.2), "C_" + WOODL, 14)
    elif sid == "queijaria":
        box(m, (2.6, .03, .26), (0, 1.58, 1.3), "T_IK_WoodLight", .008)
        for i in range(5):
            cyl(m, .15, .12, (-1 + i * .5, 1.595, 1.3), "C_F2C94A", 18, .03)
            cyl(m, .1, .09, (-.75 + i * .5, 1.715, 1.32), "C_E6B63A", 16, .025)
    elif sid == "acougue":
        bar(m, (-1.2, 1.9, 1.25), (1.2, 1.9, 1.25), .015, "C_" + STEEL, 8)
        for i in range(5):
            x = -.9 + i * .45
            bar(m, (x, 1.9, 1.25), (x, 1.78, 1.25), .006, "C_" + STEEL, 6)
            lathe(m, [(0, 0), (.05, .02), (.085, .12), (.08, .24), (.04, .3), (0, .31)], (x, 1.45, 1.25), "C_B8423A", 14)
    elif sid == "peixaria":
        rounded_panel(m, 1.1, .5, (0, 1.62, 1.37), "C_2E86DE", .03, .08)
        body = [(math.cos(math.radians(a)) * .3, math.sin(math.radians(a)) * .1) for a in range(0, 360, 20)]
        prism(m, body, .03, (-.05, 1.62, 1.34), "C_BFD4E0")
        prism(m, [(.28, 0), (.42, .12), (.42, -.12)], .03, (-.05, 1.62, 1.34), "C_BFD4E0")
        ball(m, (-.27, 1.64, 1.32), (.04, .04, .02), "C_" + DARK)
    elif sid == "sorvetes":
        lathe(m, [(0, 0), (.16, .55), (.18, .58)], (1.05, 1.1, 1.3), "C_D9A45A", 16)
        ball(m, (1.05, 1.78, 1.3), (.38, .34, .38), "C_F4A6C1")
        ball(m, (1.05, 2.0, 1.3), (.3, .28, .3), "C_B8E6D2")
        ball(m, (1.05, 2.16, 1.3), (.08, .08, .08), "C_" + RED)
    elif sid == "adega":
        for i in range(7):
            x = -1.2 + i * .4
            bar(m, (x, .3, 1.36), (x + .4, 2.1, 1.36), .012, "T_IK_WoodLight", 6)
            bar(m, (x + .4, .3, 1.36), (x, 2.1, 1.36), .012, "T_IK_WoodLight", 6)
        # Barrel lying along +X on the tasting island.
        lathe(m, [(0, 0), (.22, 0), (.27, .3), (.22, .6), (0, .6)], (.5, 1.05, -.3), "C_8A5A34", 18, roll=90)
        for s in (.06, .3, .54):
            torus(m, .235 + (.035 if s == .3 else 0), .012, (.5 + s, 1.05, -.3), "C_" + DARK, roll=90)
        cyl(m, .03, .1, (.44, 1.05, -.3), "C_" + GOLD, 10, roll=90)
    else:  # bebidas
        lathe(m, [(0, 0), (.2, 0), (.26, .36), (.27, .38)], (1.0, .8, -.2), "C_" + STEEL, 18, cap=False)
        ball(m, (1.0, 1.12, -.2), (.46, .12, .46), "C_E8F4FA")


for _sid in SECTORS:
    model("sector-" + _sid)(lambda m, s=_sid: sector(m, s))


# =========================================================================================== checkout and kiosk
@model("checkout")
def checkout(m):
    box(m, (2.4, .84, .9), (0, .42, 0), "C_" + NAVY, .05)
    box(m, (2.12, .6, .02), (-.1, .46, -.455), "T_IK_WoodLight", .01)
    box(m, (2.42, .035, .03), (0, .8, -.46), "C_" + GOLD, .01)
    box(m, (2.42, .08, .92), (0, .05, 0), "C_" + DARK, .02)
    box(m, (2.46, .045, .96), (0, .86, 0), "T_IK_Marble", .018)
    box(m, (1.3, .03, .44), (-.38, .885, -.08), "T_IK_Belt", .01, 1)
    for x in (-1.03, .27):
        cyl(m, .025, .44, (x, .885, -.3), "C_" + STEEL, 12, pitch=90)
    for z in (-.32, .16):
        box(m, (1.34, .045, .03), (-.38, .9, z), "C_" + STEEL, .012)
    box(m, (.035, .06, .4), (-.7, .93, -.08), "C_" + RED, .012)
    box(m, (.32, .025, .32), (.42, .89, -.05), "C_" + DARK, .01)
    box(m, (.2, .006, .2), (.42, .905, -.05), "E_FF4A3A", .002, 1)
    # Bag carousel.
    cyl(m, .02, .35, (.95, .88, .02), "C_" + STEEL, 10)
    for a in range(0, 360, 90):
        bar(m, (.95, 1.2, .02), (.95 + .18 * math.cos(math.radians(a)), 1.2, .02 + .18 * math.sin(math.radians(a))), .008, "C_" + STEEL, 6)
    box(m, (.26, .3, .16), (.95, 1.02, -.12), "C_" + WHITE, .04)
    # Register.
    cyl(m, .03, .26, (.6, .88, .3), "C_" + STEEL, 12)
    box(m, (.4, .26, .05), (.6, 1.22, .3), "C_" + DARK, .025, pitch=12, yaw=180)
    box(m, (.34, .2, .01), (.6, 1.22, .33), "E_7BD3F7", .004, 1, pitch=12, yaw=180)
    box(m, (.42, .12, .36), (.6, .74, .28), "C_" + DARK, .02)
    box(m, (.1, .17, .06), (.62, .96, -.34), "C_" + DARK, .02, pitch=-20)
    box(m, (.07, .08, .006), (.62, .97, -.375), "E_5DA637", .002, 1, pitch=-20)
    # Lane lamp with the lane number.
    cyl(m, .025, 1.0, (-1.15, .86, .35), "C_" + STEEL, 10)
    cyl(m, .16, .06, (-1.15, 1.84, .35), "C_" + NAVY, 20, .02)
    cyl(m, .14, .12, (-1.15, 1.9, .35), "E_FFD97A", 20, .03)
    text(m, "1", (-1.15, 1.96, .2), .14, "C_" + NAVY, .03)
    # Impulse rack.
    box(m, (.32, 1.1, .3), (-1.1, .55, -.62), "C_" + NAVY, .03)
    for l in range(3):
        box(m, (.3, .02, .26), (-1.1, .34 + l * .3, -.64), "C_" + CREAM, .006)
    box(m, (.34, .12, .03), (-1.1, 1.15, -.62), "C_" + GOLD, .02)


@model("kiosk")
def kiosk(m):
    box(m, (.62, .84, .5), (-.12, .42, .05), "C_" + NAVY, .06)
    box(m, (.64, .08, .52), (-.12, .04, .05), "C_" + DARK, .02)
    box(m, (.64, .04, .02), (-.12, .7, -.205), "C_" + GOLD, .01)
    box(m, (.66, .05, .54), (-.14, .86, -.04), "T_IK_Steel", .02)
    box(m, (.24, .006, .24), (-.14, .89, -.08), "E_FF4A3A", .002, 1)
    cyl(m, .03, .35, (-.12, .88, .18), "C_" + STEEL, 12)
    box(m, (.48, .36, .06), (-.12, 1.32, .15), "C_" + DARK, .03, pitch=15)
    box(m, (.42, .3, .01), (-.12, 1.32, .118), "E_7BD3F7", .004, 1, pitch=15)
    box(m, (.1, .12, .06), (.12, .96, -.16), "C_" + DARK, .02, pitch=15)
    cyl(m, .02, .66, (.78, 0, 0), "C_" + STEEL, 10)
    box(m, (.46, .03, .46), (.78, .68, 0), "T_IK_Steel", .012)
    box(m, (.34, .3, .22), (.78, .84, 0), "C_" + WHITE, .05)
    cyl(m, .02, 1.1, (-.4, .86, .22), "C_" + STEEL, 10)
    cyl(m, .1, .16, (-.4, 1.94, .22), "E_7ED957", 18, .03)
    rounded_panel(m, .5, .12, (-.12, 1.58, .16), "C_" + TEAL, .03, .05)
    text(m, "AUTO", (-.12, 1.575, .13), .07, "C_" + WHITE, .015)


# =========================================================================================== decorations: inside
def leaves(m, center, count, spread, size, obj, seed=1, cols=(LEAF, LEAFD)):
    for i in range(count):
        a = i * 2.39996 + seed
        r = spread * math.sqrt((i + .5) / count)
        y = center[1] + (i % 3) * size * .25
        ball(m, (center[0] + math.cos(a) * r, y, center[2] + math.sin(a) * r), (size, size * .8, size), "C_" + cols[i % len(cols)], 10, 7, obj)


@model("basket-stack")
def basket_stack(m):
    for i in range(6):
        y = .05 + i * .09
        box(m, (.46, .13, .34), (0, y + .07, 0), "C_D8423A", .025)
        box(m, (.48, .018, .36), (0, y + .14, 0), "C_A92E28", .008)
    for x in (-.14, .14):
        bar(m, (x, .72, 0), (x, .8, 0), .012, "C_" + DARK, 6)
    bar(m, (-.14, .8, 0), (.14, .8, 0), .014, "C_" + DARK, 8)
    cyl(m, .015, .5, (.2, .1, .17), "C_" + STEEL, 8)
    rounded_panel(m, .34, .14, (.2, .98, .17), "C_" + NAVY, .02, .04)
    text(m, "CESTAS", (.2, .975, .155), .06, "C_" + GOLDL, .012)


@model("plant-small")
def plant_small(m):
    lathe(m, [(0, 0), (.15, 0), (.21, .36), (.25, .38), (.25, .44), (.21, .44), (.2, .4), (0, .4)], (0, 0, 0), "C_C4673D", 20)
    ball(m, (0, .42, 0), (.4, .06, .4), "C_4A3526")
    leaves(m, (0, .55, 0), 9, .12, .24, m.anim("Anim Sway"))


@model("balloons")
def balloons(m):
    lathe(m, [(0, 0), (.15, 0), (.15, .07), (.07, .12), (0, .13)], (0, 0, 0), "C_" + GOLD, 18)
    cols = ("E15533", "F2B03D", "2E8CAE", "5DA637", "E86A9E", "8E6CCF", "FFFFFF")
    for i in range(7):
        a = i * 2.2
        top = (math.cos(a) * .22, 1.45 + (i % 3) * .22, math.sin(a) * .22)
        bar(m, (0, .13, 0), (top[0], top[1] - .2, top[2]), .004, "C_" + WHITE, 4)
        o = m.anim("Anim Bob")
        ball(m, top, (.32, .38, .32), "C_" + cols[i], 16, 10, o)
        lathe(m, [(0, 0), (.03, .02), (0, .05)], (top[0], top[1] - .23, top[2]), "C_" + cols[i], 8, obj=o)


@model("floor-lamp")
def floor_lamp(m):
    lathe(m, [(0, 0), (.2, 0), (.21, .02), (.18, .05), (.04, .07), (0, .07)], (0, 0, 0), "C_" + GOLD, 24)
    cyl(m, .018, 1.4, (0, .06, 0), "C_" + GOLD, 10)
    lathe(m, [(.27, 0), (.25, .02), (.16, .33), (.14, .34)], (0, 1.4, 0), "C_F7EBD2", 24, cap=False)
    lathe(m, [(0, 0), (.2, 0)], (0, 1.42, 0), "E_FFE9B0", 18)
    ball(m, (0, 1.5, 0), (.09, .11, .09), "E_FFF2CC")


@model("bench")
def bench(m):
    for x in (-.64, .64):
        prism(m, [(-.24, 0), (.24, 0), (.2, .44), (.22, .62), (.18, .66), (.14, .46), (-.2, .46)], .06, (x, 0, 0), "C_" + NAVY, 0, -90)
        box(m, (.07, .04, .46), (x, .64, -.01), "C_" + GOLD, .015)
    for i in range(3):
        box(m, (1.52, .045, .13), (0, .46, -.15 + i * .15), "T_IK_WoodLight", .015)
    for i in range(2):
        box(m, (1.52, .12, .035), (0, .66 + i * .17, .2 + i * .02), "T_IK_WoodLight", .015, pitch=-8)


def cart(m, x, z, obj="Body"):
    for side in (-1, 1):
        box(m, (.03, .03, .72), (x + side * .26, .88, z), "C_" + STEEL, .01)
        for i in range(5):
            zz = z - .32 + i * .16
            bar(m, (x + side * .25, .52, zz), (x + side * .26, .88, zz), .008, "C_" + STEEL, 5)
    box(m, (.54, .04, .74), (x, .5, z), "C_" + STEEL, .012)
    box(m, (.56, .03, .03), (x, .88, z + .36), "C_" + STEEL, .01)
    for i in range(5):
        xx = x - .22 + i * .11
        bar(m, (xx, .52, z + .36), (xx, .88, z + .36), .008, "C_" + STEEL, 5)
    bar(m, (x - .27, 1.0, z - .44), (x + .27, 1.0, z - .44), .02, "C_" + RED, 10)
    for side in (-1, 1):
        bar(m, (x + side * .24, .88, z - .36), (x + side * .25, 1.0, z - .44), .01, "C_" + STEEL, 6)
        bar(m, (x + side * .2, .06, z - .3), (x + side * .22, .5, z - .3), .012, "C_" + STEEL, 6)
        bar(m, (x + side * .2, .06, z + .3), (x + side * .22, .5, z + .3), .012, "C_" + STEEL, 6)
        for zz in (-.3, .3):
            cyl(m, .045, .03, (x + side * .2 - .015, .045, z + zz), "C_" + DARK, 12, pitch=0, roll=90)


@model("cart-corral")
def cart_corral(m):
    for x in (-.37, .37):
        bar(m, (x, .5, -.95), (x, .5, .95), .02, "C_" + STEEL, 10)
        for z in (-.95, .95):
            bar(m, (x, 0, z), (x, .5, z), .02, "C_" + STEEL, 10)
    bar(m, (-.37, .5, .95), (.37, .5, .95), .02, "C_" + STEEL, 10)
    cyl(m, .02, 1.1, (0, 0, .97), "C_" + STEEL, 10)
    rounded_panel(m, .7, .22, (0, 1.2, .97), "C_" + NAVY, .03, .06)
    text(m, "CARRINHOS", (0, 1.195, .95), .07, "C_" + GOLDL, .014)
    for i in range(4):
        cart(m, 0, -.6 + i * .28)


@model("plant-palm")
def plant_palm(m):
    lathe(m, [(0, 0), (.24, 0), (.34, .5), (.37, .52), (.37, .58), (.32, .58), (0, .56)], (0, 0, 0), "C_" + GOLD, 24)
    lathe(m, [(.345, 0), (.36, .03)], (0, .2, 0), "C_" + NAVY, 24, cap=False)
    sway = m.anim("Anim Sway")
    for i in range(5):
        cyl(m, .075 - i * .008, .28, (math.sin(i) * .02, .56 + i * .26, 0), "C_8A6A45", 10, .02, obj=sway)
    for i in range(9):
        a = i * 40
        rad = math.radians(a)
        for k in range(3):
            d = .15 + k * .22
            y = 1.9 - (d * d) * .45
            ball(m, (math.sin(rad) * d, y, math.cos(rad) * d), (.14, .04, .3), "C_" + (LEAF if i % 2 else LEAFD), 8, 5, sway, pitch=-20 - k * 12, yaw=a)


@model("promo-stand")
def promo_stand(m):
    for x in (-.45, 0, .45):
        box(m, (.12, .1, .85), (x, .05, 0), "T_IK_Crate", .01)
    box(m, (1.1, .04, .85), (0, .12, 0), "T_IK_Crate", .01)
    cols = ("D74A3C", "3E8FD6", "F2C23F", "5DAE3E")
    for l in range(3):
        n = 3 - l
        for i in range(n):
            for j in range(3 - l):
                x = -(n - 1) * .16 + i * .32
                z = -(3 - l - 1) * .14 + j * .28
                box(m, (.3, .28, .26), (x, .28 + l * .29, z), "C_" + cols[(i + j + l) % 4], .03)
                box(m, (.2, .1, .005), (x, .3 + l * .29, z - .13), "C_" + WHITE, .004, 1)
    cyl(m, .015, 1.5, (.46, .14, .32), "C_" + STEEL, 8)
    quad(m, .62, .32, (.46, 1.6, .3), "T_IK_PromoCard")
    box(m, (.66, .36, .02), (.46, 1.6, .32), "C_" + GOLD, .015)


@model("water-cooler")
def water_cooler(m):
    box(m, (.36, 1.0, .36), (0, .5, 0), "C_" + WHITE, .05)
    box(m, (.3, .38, .01), (0, .4, -.18), "C_" + STEEL, .005)
    box(m, (.2, .02, .09), (0, .62, -.2), "C_" + DARK, .008)
    box(m, (.05, .07, .05), (-.06, .8, -.2), "C_" + RED, .015)
    box(m, (.05, .07, .05), (.06, .8, -.2), "C_" + BLUE, .015)
    lathe(m, [(.05, 0), (.05, .06), (.16, .12), (.16, .42), (.12, .47), (0, .48)], (0, 1.0, 0), "G_Glass", 20)
    lathe(m, [(.045, 0), (.045, .06), (.15, .12), (.15, .32), (0, .32)], (0, 1.0, 0), "C_7FC4F0", 18)


@model("gumball")
def gumball(m):
    lathe(m, [(0, 0), (.2, 0), (.2, .04), (.06, .1), (.05, .72), (.15, .76), (.16, .96), (0, .98)], (0, 0, 0), "C_D8423A", 22)
    box(m, (.12, .12, .03), (0, .88, -.16), "C_" + STEEL, .02)
    cyl(m, .03, .03, (0, .88, -.18), "C_" + GOLD, 12, pitch=90)
    cols = ("E15533", "F2B03D", "2E8CAE", "5DA637", "E86A9E", "FFFFFF")
    for i in range(26):
        a = i * 2.4
        r = .12 * math.sqrt((i % 9 + .5) / 9)
        ball(m, (math.cos(a) * r, 1.02 + (i // 9) * .06, math.sin(a) * r), (.055, .055, .055), "C_" + cols[i % 6], 8, 6)
    ball(m, (0, 1.14, 0), (.36, .36, .36), "G_Glass", 20, 14)
    lathe(m, [(.1, 0), (.08, .05), (0, .08)], (0, 1.3, 0), "C_D8423A", 16)


@model("flower-stand")
def flower_stand(m):
    box(m, (1.3, .1, .7), (0, .44, 0), "T_IK_WoodLight", .02)
    box(m, (1.32, .14, .04), (0, .52, -.35), "T_IK_WoodLight", .01)
    for x in (-.55, .55):
        for z in (-.28, .28):
            box(m, (.05, .4, .05), (x, .2, z), "C_" + NAVY, .015)
    cyl(m, .2, .05, (-.7, .2, 0), "C_" + DARK, 18, .015, roll=90)
    cols = ("E15533", "F2B03D", "E86A9E", "FFFFFF", "8E6CCF", "F28C38")
    for i in range(6):
        at = (-.42 + (i % 3) * .42, .49, -.14 + (i // 3) * .28)
        lathe(m, [(0, 0), (.1, 0), (.13, .24), (.14, .26), (.12, .26), (0, .24)], at, "T_IK_Steel", 16)
        sway = m.anim("Anim Sway")
        for k in range(7):
            a = k * 2.4 + i
            h = (math.cos(a) * .07, .44 + (k % 3) * .04, math.sin(a) * .07)
            bar(m, (at[0], .7, at[2]), (at[0] + h[0], at[1] + h[1] - .02, at[2] + h[2]), .006, "C_" + LEAFD, 4, sway)
            ball(m, (at[0] + h[0], at[1] + h[1], at[2] + h[2]), (.09, .06, .09), "C_" + cols[i], 8, 5, sway)
    for x in (-.62, .62):
        box(m, (.04, 1.1, .04), (x, 1.0, .3), "C_" + NAVY, .012)
    awning(m, 1.42, .55, 1.56, -.1, "S_E86A9E", 14)


@model("watermelon-pile")
def watermelon_pile(m):
    box(m, (1.36, .48, 1.06), (0, .24, 0), "T_IK_Crate", .03)
    box(m, (1.42, .05, 1.12), (0, .5, 0), "T_IK_WoodLight", .015)
    k = 0
    for l in range(3):
        for i in range(3 - l):
            for j in range(2 if l < 2 else 1):
                x = -.4 + i * .4 + l * .2
                z = (-.2 + j * .4) if l < 2 else 0
                ball(m, (x, .64 + l * .22, z * (1 - l * .3)), (.38, .3, .3), "S_3E8E3A", 16, 10, yaw=90 + (k * 23) % 40)
                k += 1
    lathe(m, [(0, 0), (.17, 0), (.18, .03), (0, .035)], (.42, .96, -.34), "C_E0453A", 16)
    lathe(m, [(.18, 0), (.19, .03)], (.42, .96, -.34), "C_" + GREEN, 16, cap=False)
    for a in range(0, 360, 60):
        ball(m, (.42 + math.cos(math.radians(a)) * .09, .995, -.34 + math.sin(math.radians(a)) * .09), (.015, .01, .02), "C_" + DARK, 6, 4)
    rounded_panel(m, .3, .2, (-.42, .9, -.52), "C_F2C23F", .02, .05)
    text(m, "R$3", (-.42, .895, -.535), .08, "C_" + RED, .012)


@model("claw-machine")
def claw_machine(m):
    pink = "C_E86A9E"
    box(m, (.82, .9, .82), (0, .45, 0), pink, .06)
    box(m, (.84, .08, .84), (0, .04, 0), "C_" + NAVY, .02)
    box(m, (.72, .12, .18), (0, .95, -.37), "C_" + NAVY, .03, pitch=-15)
    cyl(m, .015, .1, (-.15, .98, -.4), "C_" + DARK, 8)
    ball(m, (-.15, 1.09, -.4), (.07, .07, .07), "C_" + RED)
    cyl(m, .045, .03, (.15, 1.0, -.4), "C_F2B03D", 14, .01)
    box(m, (.14, .1, .02), (.28, .6, -.415), "C_" + DARK, .01)
    for x in (-.39, .39):
        for z in (-.39, .39):
            box(m, (.05, 1.0, .05), (x, 1.4, z), "C_" + GOLD, .015)
    for yaw in (0, 90, 180, 270):
        rz = math.radians(yaw)
        box(m, (.76, .96, .01), (-.39 * math.sin(rz), 1.4, -.39 * math.cos(rz)), "G_Glass", .002, 1, yaw=yaw)
    box(m, (.88, .12, .88), (0, 1.95, 0), pink, .04)
    rounded_panel(m, .82, .3, (0, 2.16, -.3), "C_" + NAVY, .06, .08)
    text(m, "PEGUE!", (0, 2.15, -.34), .13, "C_" + GOLDL, .025)
    cols = ("F2B03D", "2E8CAE", "5DA637", "FFFFFF", "8E6CCF")
    for i in range(16):
        a = i * 2.4
        r = .28 * math.sqrt((i + .5) / 16)
        ball(m, (math.cos(a) * r, .98 + (i % 3) * .05, math.sin(a) * r), (.14, .14, .14), "C_" + cols[i % 5], 10, 7)
    spin = m.anim("Anim Spin")
    bar(m, (.1, 1.9, .05), (.1, 1.72, .05), .006, "C_" + DARK, 4, spin)
    for k in range(3):
        a = math.radians(k * 120)
        bar(m, (.1, 1.72, .05), (.1 + math.cos(a) * .06, 1.62, .05 + math.sin(a) * .06), .008, "C_" + STEEL, 5, spin)
    for i in range(8):
        blink = m.anim("Anim Blink")
        ball(m, (-.36 + i * .103, 1.95, -.45), (.05, .05, .05), "E_" + ("FFE066" if i % 2 == 0 else "FF6FA8"), 8, 6, blink)


@model("atm")
def atm(m):
    box(m, (.7, 1.6, .6), (0, .8, .04), "T_IK_Steel", .05)
    box(m, (.62, .9, .05), (0, 1.0, -.27), "C_" + TEAL, .03)
    box(m, (.38, .28, .02), (0, 1.26, -.3), "E_7BD3F7", .01, 1, pitch=-10)
    box(m, (.22, .03, .15), (-.1, .92, -.33), "C_" + DARK, .01, pitch=-20)
    for i in range(3):
        for j in range(3):
            box(m, (.04, .01, .03), (-.17 + i * .06, .94, -.37 + j * .04), "C_" + STEEL, .004, 1, pitch=-20)
    box(m, (.1, .04, .03), (.18, 1.0, -.31), "E_5DA637", .008)
    box(m, (.3, .04, .03), (0, .72, -.3), "C_" + DARK, .01)
    rounded_panel(m, .72, .24, (0, 1.76, -.1), "C_" + NAVY, .1, .08)
    text(m, "24H", (0, 1.755, -.16), .12, "C_" + GOLDL, .02)


@model("digital-totem")
def digital_totem(m):
    rounded_panel(m, .62, .1, (0, .05, 0), "C_" + GOLD, .34, .04)
    rounded_panel(m, .62, 1.86, (0, 1.0, 0), "C_" + NAVY, .12, .12)
    box(m, (.64, .06, .14), (0, 1.97, 0), "C_" + GOLD, .02)
    quad(m, .52, 1.56, (0, 1.05, -.064), "T_IK_Screen", obj=m.anim("Anim Scroll"))


# =========================================================================================== decorations: outside
@model("park-bench")
def park_bench(m):
    for x in (-.7, .7):
        prism(m, [(-.3, 0), (-.22, 0), (-.18, .4), (.2, .4), (.24, 0), (.32, 0), (.28, .44), (.3, .9), (.24, .92), (.2, .5), (-.26, .48)], .07, (x, 0, 0), "C_" + DARK, 0, -90)
        cyl(m, .03, .02, (x, .66, -.28), "C_" + GOLD, 10, pitch=90)
    for i in range(4):
        box(m, (1.62, .045, .11), (0, .47, -.2 + i * .12), "T_IK_WoodLight", .015)
    for i in range(3):
        box(m, (1.62, .1, .035), (0, .6 + i * .13, .25 + i * .02), "T_IK_WoodLight", .015, pitch=-10)


@model("tree-planter")
def tree_planter(m):
    lathe(m, [(0, 0), (.62, 0), (.66, .05), (.66, .42), (.7, .45), (.7, .5), (.6, .5), (0, .46)], (0, 0, 0), "C_" + CREAM, 28)
    lathe(m, [(.66, 0), (.67, .06)], (0, .3, 0), "C_" + NAVY, 28, cap=False)
    ball(m, (0, .47, 0), (1.2, .08, 1.2), "C_5C4030", 20, 8)
    for a in range(0, 360, 60):
        ball(m, (math.cos(math.radians(a)) * .45, .52, math.sin(math.radians(a)) * .45), (.12, .1, .12), "C_" + ("F2B03D" if a % 120 else "E86A9E"), 8, 6)
    sway = m.anim("Anim Sway")
    lathe(m, [(.1, 0), (.08, .9), (.06, 1.5)], (0, .45, 0), "C_7A5236", 10, obj=sway)
    for i, (x, y, z, s) in enumerate(((0, 2.25, 0, 1.1), (.35, 2.0, .15, .8), (-.35, 2.05, -.1, .85), (.1, 2.6, -.1, .75), (-.15, 1.95, .3, .7), (.2, 2.1, -.35, .7))):
        ball(m, (x, y, z), (s, s * .85, s), "C_" + (LEAF if i % 2 == 0 else "4E9A3A"), 14, 9, sway)


@model("flower-bed")
def flower_bed(m):
    box(m, (2.0, .45, .8), (0, .225, 0), "T_IK_WoodLight", .04)
    box(m, (2.06, .05, .86), (0, .45, 0), "C_" + NAVY, .02)
    box(m, (1.9, .04, .7), (0, .43, 0), "C_5C4030", .01, 1)
    cols = ("E15533", "F2B03D", "E86A9E", "FFFFFF", "8E6CCF", "F28C38")
    sway = m.anim("Anim Sway")
    for i in range(34):
        x = -.85 + (i % 12) * .155 + (.07 if (i // 12) % 2 else 0)
        z = -.22 + (i // 12) * .22
        if x > .9:
            continue
        bar(m, (x, .44, z), (x, .62 + (i % 3) * .04, z), .008, "C_" + LEAFD, 4, sway)
        ball(m, (x, .64 + (i % 3) * .04, z), (.09, .06, .09), "C_" + cols[i % 6], 8, 5, sway)
        ball(m, (x + .03, .52, z - .02), (.08, .03, .05), "C_" + LEAF, 6, 4, sway)


@model("street-lamp")
def street_lamp(m):
    lathe(m, [(0, 0), (.2, 0), (.2, .08), (.12, .14), (.08, .4), (0, .4)], (0, 0, 0), "C_" + DARK, 18)
    cyl(m, .05, 2.6, (0, .38, 0), "C_" + DARK, 14)
    torus(m, .07, .02, (0, 1.0, 0), "C_" + GOLD)
    torus(m, .06, .015, (0, 2.8, 0), "C_" + GOLD)
    lathe(m, [(.06, 0), (.16, .12), (.16, .42), (.2, .46), (.02, .62), (0, .62)], (0, 2.95, 0), "C_" + DARK, 16)
    lathe(m, [(.07, 0), (.14, .12), (.14, .4), (0, .4)], (0, 3.0, 0), "E_FFE6A8", 16)
    ball(m, (0, 3.6, 0), (.07, .1, .07), "C_" + GOLD)
    for side in (-1, 1):
        box(m, (.05, .5, .3), (side * .16, 1.6, 0), "C_" + ("D74A3C" if side < 0 else TEAL), .02)


@model("fountain")
def fountain(m):
    lathe(m, [(0, 0), (1.05, 0), (1.1, .05), (1.1, .42), (1.0, .45), (.95, .2), (0, .2)], (0, 0, 0), "C_" + CREAM, 36)
    lathe(m, [(1.1, 0), (1.12, .05)], (0, .38, 0), "C_" + GOLD, 36, cap=False)
    lathe(m, [(0, 0), (.95, 0)], (0, .34, 0), "C_6CC4E8", 36)
    lathe(m, [(0, 0), (.2, 0), (.12, .2), (.1, .7), (.14, .75), (0, .75)], (0, .2, 0), "C_" + CREAM, 20)
    lathe(m, [(0, 0), (.08, 0), (.5, .1), (.52, .16), (.46, .16), (0, .06)], (0, .92, 0), "C_" + CREAM, 28)
    lathe(m, [(0, 0), (.44, 0)], (0, 1.06, 0), "C_6CC4E8", 24)
    lathe(m, [(0, 0), (.06, 0), (.04, .25), (.1, .3), (0, .34)], (0, 1.02, 0), "C_" + CREAM, 14)
    spin = m.anim("Anim Spin")
    for a in range(0, 360, 45):
        r = math.radians(a)
        bar(m, (0, 1.34, 0), (math.cos(r) * .35, 1.2, math.sin(r) * .35), .02, "C_A9E0F5", 5, spin)
    for a in range(0, 360, 60):
        r = math.radians(a)
        ball(m, (math.cos(r) * .6, .4, math.sin(r) * .6), (.12, .04, .12), "C_E0F4FC", 8, 5, spin)


@model("bike-rack")
def bike_rack(m):
    box(m, (1.8, .04, .5), (0, .02, 0), "C_9A9A94", .01)
    for i in range(5):
        x = -.72 + i * .36
        pts = [(x - .12, 0)] + [(x + math.cos(math.radians(a)) * .12, .55 + math.sin(math.radians(a)) * .12) for a in range(180, -1, -30)] + [(x + .12, 0)]
        for k in range(len(pts) - 1):
            bar(m, (pts[k][0], pts[k][1], 0), (pts[k + 1][0], pts[k + 1][1], 0), .02, "C_" + TEAL, 8)
    rounded_panel(m, .5, .16, (.8, .9, .2), "C_" + NAVY, .02, .05)
    cyl(m, .015, .85, (.8, 0, .2), "C_" + STEEL, 8)
    text(m, "BIKE", (.8, .895, .185), .07, "C_" + WHITE, .012)


def cart_body(m, col, title, awn):
    box(m, (1.1, .7, .7), (0, .75, 0), "C_" + col, .06)
    box(m, (1.14, .06, .74), (0, .4, 0), "C_" + GOLD, .02)
    box(m, (1.16, .05, .76), (0, 1.12, 0), "C_" + WHITE, .02)
    for x in (-.62, .62):
        pass
    cyl(m, .28, .06, (-.3, .28, -.36), "C_" + DARK, 18, .02, pitch=90)
    cyl(m, .28, .06, (-.3, .28, .3), "C_" + DARK, 18, .02, pitch=90)
    cyl(m, .1, .07, (-.3, .28, -.37), "C_" + GOLD, 12, 0, pitch=90)
    cyl(m, .1, .07, (-.3, .28, .31), "C_" + GOLD, 12, 0, pitch=90)
    bar(m, (.55, .85, -.2), (.75, .95, -.2), .02, "C_" + STEEL, 8)
    bar(m, (.55, .85, .2), (.75, .95, .2), .02, "C_" + STEEL, 8)
    bar(m, (.75, .95, -.22), (.75, .95, .22), .025, "C_" + DARK, 8)
    bar(m, (.5, .4, 0), (.5, 0, 0), .025, "C_" + STEEL, 8)
    for x in (-.5, .5):
        bar(m, (x, 1.14, 0), (x, 1.85, 0), .02, "C_" + STEEL, 8)
    lathe(m, [(0, .0), (.85, -.02), (.9, -.08), (0, .22)], (0, 1.95, 0), "S_" + awn, 12, pitch=0)
    ball(m, (0, 2.2, 0), (.08, .08, .08), "C_" + GOLD)
    rounded_panel(m, .8, .2, (0, .8, -.37), "C_" + WHITE, .02, .06)
    text(m, title, (0, .795, -.39), .09, "C_" + col, .014)


@model("popcorn-cart")
def popcorn_cart(m):
    cart_body(m, "D74A3C", "PIPOCA", "D74A3C")
    box(m, (.6, .5, .5), (.05, 1.4, 0), "G_Glass", .02)
    for i in range(24):
        a = i * 2.4
        ball(m, (.05 + math.cos(a) * .2 * ((i % 5) / 5), 1.2 + (i // 8) * .06, math.sin(a) * .18), (.06, .05, .06), "C_FFF1C4", 6, 4)


@model("ice-cream-cart")
def ice_cream_cart(m):
    cart_body(m, "E86A9E", "SORVETE", "2E8CAE")
    for i, c in enumerate(("F4A6C1", "B8E6D2", "FFF1C4", "8A5A34")):
        lathe(m, [(0, 0), (.06, 0), (.06, .02), (0, .02)], (-.3 + i * .2, 1.14, -.1), "C_" + STEEL, 12)
        ball(m, (-.3 + i * .2, 1.2, -.1), (.12, .1, .12), "C_" + c, 10, 7)


@model("parasol-table")
def parasol_table(m):
    lathe(m, [(0, 0), (.3, 0), (.3, .04), (.05, .08), (.04, .7), (.4, .72), (.42, .76), (0, .77)], (0, 0, 0), "C_" + WHITE, 24)
    cyl(m, .025, 1.6, (0, .75, 0), "C_" + STEEL, 10)
    lathe(m, [(0, 0), (1.0, -.05), (1.02, -.12), (0, .3)], (0, 2.2, 0), "S_" + ORANGE, 16)
    ball(m, (0, 2.52, 0), (.07, .07, .07), "C_" + GOLD)
    for a in (0, 180):
        r = math.radians(a)
        cx, cz = math.sin(r) * .75, math.cos(r) * .75
        box(m, (.42, .05, .42), (cx, .46, cz), "C_" + TEAL, .03)
        box(m, (.42, .42, .05), (cx, .7, cz + (.2 if a == 0 else -.2)), "C_" + TEAL, .03)
        for dx in (-.18, .18):
            for dz in (-.18, .18):
                bar(m, (cx + dx, 0, cz + dz), (cx + dx, .45, cz + dz), .015, "C_" + DARK, 6)


@model("kiddie-ride")
def kiddie_ride(m):
    box(m, (.9, .12, 1.2), (0, .06, 0), "C_" + NAVY, .05)
    box(m, (.94, .03, 1.24), (0, .12, 0), "C_" + GOLD, .01)
    for i in range(6):
        torus(m, .12, .02, (0, .18 + i * .045, 0), "C_" + STEEL)
    bob = m.anim("Anim Bob")
    # Little red car on a spring.
    box(m, (.62, .32, .95), (0, .6, 0), "C_" + RED, .12, 3, obj=bob)
    box(m, (.5, .22, .4), (0, .86, .1), "C_" + RED, .08, 3, obj=bob)
    box(m, (.46, .18, .02), (0, .86, -.12), "G_Glass", .01, obj=bob)
    box(m, (.52, .08, .3), (0, .78, .1), "C_" + CREAM, .03, obj=bob)
    for x in (-.32, .32):
        for z in (-.32, .32):
            cyl(m, .12, .08, (x + (.04 if x > 0 else -.04), .45, z), "C_" + DARK, 16, .02, roll=90, obj=bob)
    ball(m, (-.2, .66, -.47), (.1, .1, .04), "E_FFE9A8", obj=bob)
    ball(m, (.2, .66, -.47), (.1, .1, .04), "E_FFE9A8", obj=bob)
    box(m, (.24, .1, .03), (.3, .18, -.6), "C_" + DARK, .01)


@model("billboard")
def billboard(m):
    for x in (-.7, .7):
        box(m, (.1, 1.6, .1), (x, .8, .1), "C_" + DARK, .03)
        box(m, (.26, .06, .26), (x, .03, .1), "C_" + DARK, .02)
    rounded_panel(m, 1.8, .96, (0, 1.9, .1), "C_" + NAVY, .1, .1)
    rounded_panel(m, 1.86, 1.02, (0, 1.9, .14), "C_" + GOLD, .06, .12)
    quad(m, 1.62, .8, (0, 1.9, .04), "T_IK_PromoCard")
    for x in (-.6, 0, .6):
        bar(m, (x, 2.46, -.04), (x, 2.5, -.2), .012, "C_" + DARK, 6)
        lathe(m, [(0, 0), (.08, .06), (.02, .08)], (x, 2.52, -.22), "C_" + DARK, 10, pitch=180)


@model("recycle-bins")
def recycle_bins(m):
    for i, c in enumerate(("2E86DE", "F2C23F", "5DA637", "D74A3C")):
        x = -.57 + i * .38
        box(m, (.34, .8, .4), (x, .42, 0), "C_" + c, .05)
        box(m, (.36, .06, .42), (x, .84, 0), "C_" + c, .03)
        box(m, (.2, .02, .06), (x, .88, -.08), "C_" + DARK, .01)
        box(m, (.18, .12, .01), (x, .55, -.2), "C_" + WHITE, .01, 1)
    box(m, (1.56, .06, .46), (0, .03, 0), "C_" + DARK, .015)


# =========================================================================================== detailed staffed counters
# Padaria, queijaria, açougue and peixaria are big, rounded departments with their own trade equipment and a
# modelled stock on display, replacing the shared sector() look. Contract with CheckoutInteriorKitBuilder
# (Unity, SectorCounter): footprint FOOTPRINT, attendant at STAFF, customers at z -1.6, stock in the objects
# "Anim Fill 0..3" (left to right), which Unity turns into the fill groups shown as stock rises.

def dbox(m, size, center, key, bevel=.02, seg=1, pitch=0, yaw=0, roll=0, obj="Body", uv="metric"):
    """box() with single-segment chamfers: same silhouette, a fraction of the triangles (many small parts here)."""
    box(m, size, center, key, bevel, seg, pitch, yaw, roll, obj, uv)


def text_lite(m, value, center, size, key, depth=.006, yaw=0, obj="Body"):
    """Flat low-poly lettering for chalkboards and plaques."""
    font = bpy.data.fonts.get("Fredoka_700Bold") or bpy.data.fonts.load(FONT)
    font.name = "Fredoka_700Bold"
    cu = bpy.data.curves.new("txt", type="FONT")
    cu.body = value; cu.font = font; cu.size = size; cu.align_x = "CENTER"; cu.align_y = "CENTER"
    cu.extrude = depth * .5; cu.bevel_depth = 0; cu.resolution_u = 2
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2), verts=bm.verts, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    basis = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=basis, verts=bm.verts)
    m.add(_place(bm, center, 0, yaw), key, obj, uv="none")


def text_mid(m, value, center, size, key, depth=.03, obj="Body"):
    """Bevelled 3D lettering for the department boards, lighter than text() (fewer curve steps)."""
    font = bpy.data.fonts.get("Fredoka_700Bold") or bpy.data.fonts.load(FONT)
    font.name = "Fredoka_700Bold"
    cu = bpy.data.curves.new("txt", type="FONT")
    cu.body = value; cu.font = font; cu.size = size; cu.align_x = "CENTER"; cu.align_y = "CENTER"
    cu.extrude = depth * .5; cu.bevel_depth = .005; cu.bevel_resolution = 0; cu.resolution_u = 2
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    basis = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=basis, verts=bm.verts)
    m.add(_place(bm, center, 0, 0), key, obj, uv="none")


class Local:
    """Proxy for Model: parts built with the usual helpers in local Unity coordinates are placed (pitch about X,
    then yaw about Y, then moved to `center`) before being merged. Nestable."""

    def __init__(self, m, center, yaw=0, pitch=0, roll=0, obj=None):
        self.m, self.obj = m, obj
        self.mat = (Matrix.Translation(U(*center)) @ Matrix.Rotation(math.radians(-yaw), 4, "Z")
                    @ Matrix.Rotation(math.radians(pitch), 4, "X") @ Matrix.Rotation(math.radians(-roll), 4, "Y"))

    def add(self, part, key, obj="Body", uv="metric"):
        bmesh.ops.transform(part, matrix=self.mat, verts=part.verts)
        self.m.add(part, key, self.obj or obj, uv)

    def anim(self, kind):
        return self.m.anim(kind)


def lathe_s(m, profile, base, key, scale=(1, 1, 1), seg=16, pitch=0, yaw=0, roll=0, obj="Body", cap=True):
    """Lathe (around Unity Y) scaled in Unity axes before being rotated/placed."""
    bm = lathe_bm(profile, seg, cap)
    for f in bm.faces:
        f.smooth = True
    sx, sy, sz = scale
    bmesh.ops.scale(bm, vec=Vector((sx, sz, sy)), verts=bm.verts)
    m.add(_place(bm, base, pitch, yaw, roll), key, obj)


def torus_arc(m, R, r, center, key, a0=0, a1=360, pitch=0, yaw=0, roll=0, obj="Body", seg=12, minor=8):
    """Part of a torus lying in the Unity XZ plane (angles from +X towards -Z)."""
    bm = bmesh.new()
    closed = abs(a1 - a0) >= 360
    n = seg if closed else seg + 1
    rings = []
    for i in range(n):
        a = math.radians(a0 + (a1 - a0) * i / seg)
        rings.append([bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
                      for b in (2 * math.pi * j / minor for j in range(minor))])
    for i in range(seg if closed else seg):
        A, B = rings[i], rings[(i + 1) % n]
        for j in range(minor):
            f = bm.faces.new((A[j], B[j], B[(j + 1) % minor], A[(j + 1) % minor])); f.smooth = True
    if not closed:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m.add(_place(bm, center, pitch, yaw, roll), key, obj)


def prism_t(m, points, thick, center, key, pitch=0, yaw=0, obj="Body"):
    """prism() for concave outlines: ear-clipped so the FBX carries clean triangles."""
    bm = prism_bm(points, thick)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.radians(-yaw), 4, "Z") @ Matrix.Rotation(math.radians(pitch), 4, "X"), verts=bm.verts)
    bmesh.ops.translate(bm, vec=U(*center), verts=bm.verts)
    m.add(bm, key, obj)


def ring_points(r_out, r_in, a0, a1, n):
    """Flat arch/ring outline (Unity XY) from a0 to a1 degrees."""
    return arc_points(r_out, a0, a1, n) + list(reversed(arc_points(r_in, a0, a1, n)))


def bread_loaf(m, center, size, yaw=0, obj="Body", scores=3):
    """Rustic loaf: crusty ellipsoid with flour-dusted slashes on top."""
    sx, sy, sz = size
    ball(m, center, size, "T_IK_Crust", 12, 7, obj, yaw=yaw)
    k = Local(m, center, yaw, obj=obj)
    for i in range(scores):
        x = (i - (scores - 1) / 2) * sx / (scores + .6)
        ball(k, (x, sy * .46, 0), (.022, .012, sz * .5), "C_F4E6C8", 6, 3, yaw=25)


def baguette(m, a, b, r=.03, obj="Body"):
    bar(m, a, b, r, "T_IK_Crust", 8, obj)
    ax, ay, az = a; bx, by, bz = b
    for t in (.25, .5, .75):
        ball(m, (ax + (bx - ax) * t, ay + (by - ay) * t + r * .6, az + (bz - az) * t), (r * 1.1, r * .5, r * 1.3), "C_F4E6C8", 5, 3, obj)


def croissant(m, center, s=1.0, yaw=0, obj="Body"):
    k = Local(m, center, yaw, obj=obj)
    torus_arc(k, .045 * s, .022 * s, (0, .02 * s, 0), "T_IK_Crust", 20, 160, seg=5, minor=5)
    for a in (40, 90, 140):
        r = math.radians(a)
        ball(k, (math.cos(r) * .045 * s, .024 * s, -math.sin(r) * .045 * s), (.05 * s, .045 * s, .03 * s), "T_IK_Crust", 6, 4, yaw=-a)


def basket(m, center, r=.12, h=.1, obj="Body"):
    x, y, z = center
    lathe(m, [(0, 0), (r * .82, 0), (r, h)], center, "T_IK_Wicker", 18, obj=obj, cap=False)
    torus(m, r, .012, (x, y + h, z), "C_8A5A34", obj=obj, seg=20, minor=6)


def knife(m, center, yaw=0, pitch=0, length=.26, blade="C_DCE1E6", handle="C_2F3A40", cleaver=False, obj="Body"):
    """Knife lying along local +X (blade) with the handle at -X; built in local coords."""
    k = Local(m, center, yaw, pitch, obj=obj)
    bl = length * .62
    if cleaver:
        dbox(k, (bl, .005, .1), (bl / 2, 0, .01), blade, .003, 1)
        cyl(k, .008, .006, (bl * .8, -.003, .03), "C_" + DARK, 10)
    else:
        prism(k, [(0, .022), (bl * .8, .02), (bl, 0), (bl * .7, -.012), (0, -.012)], .004, (0, 0, 0), blade, pitch=90)
    dbox(k, (length - bl, .022, .03), (-(length - bl) / 2, 0, .005), handle, .008)
    for x in (-.03, -.07):
        cyl(k, .005, .024, (x, -.012, .005), "C_" + GOLD, 6)


def fish(m, center, L, yaw=0, lying=True, body="T_IK_FishScale", fin="C_6F8FA6", obj="Body"):
    """Whole fish along local +X (head at 0), upright in XY; lying=True lays it on its side (flat on ice)."""
    k = Local(m, center, yaw, 90 if lying else 0, obj=obj)
    H = .26 * L
    prof = [(0, 0), (.3 * H, .03 * L), (.47 * H, .16 * L), (.5 * H, .38 * L), (.38 * H, .64 * L), (.16 * H, .84 * L), (.08 * H, .9 * L)]
    lathe_s(k, prof, (0, 0, 0), body, (1, 1, .42), 14, roll=90)
    tail = [(.86 * L, 0), (1.08 * L, .2 * L), (1.02 * L, 0), (1.08 * L, -.2 * L)]
    prism(k, tail, .012, (0, 0, 0), fin)
    prism(k, [(.28 * L, .12 * L), (.4 * L, .21 * L), (.62 * L, .17 * L), (.68 * L, .1 * L)], .01, (0, 0, 0), fin)
    prism(k, [(.5 * L, -.11 * L), (.58 * L, -.16 * L), (.66 * L, -.1 * L)], .008, (0, 0, 0), fin)
    for s in (-1, 1):
        ball(k, (.09 * L, .03 * L, s * .045 * L), (.05 * L, .05 * L, .02 * L), "C_FBFAF6", 10, 6)
        ball(k, (.09 * L, .03 * L, s * .052 * L), (.028 * L, .028 * L, .012 * L), "C_1A1A1A", 8, 5)
        torus_arc(k, .09 * L, .006, (.1 * L, 0, s * .04 * L), fin, -70, 70, pitch=90, seg=6, minor=5)


def digital_scale(m, center, screen="E_7ED957"):
    x, y, z = center
    dbox(m, (.3, .06, .26), (x, y + .03, z), "C_" + WHITE, .02)
    dbox(m, (.27, .012, .22), (x, y + .066, z), "T_IK_Steel", .006, 1)
    dbox(m, (.2, .13, .04), (x, y + .13, z + .15), "C_" + WHITE, .012)
    dbox(m, (.15, .05, .006), (x, y + .15, z + .128), "C_" + DARK, .002, 1)
    dbox(m, (.12, .03, .004), (x, y + .15, z + .124), screen, .001, 1)


def chalkboard(m, center, w, h, lines, size=.055, frame="C_" + WOODD, yaw=0):
    x, y, z = center
    dbox(m, (w + .05, h + .05, .03), (x, y, z + .01), frame, .012, yaw=yaw)
    dbox(m, (w, h, .012), (x, y, z - .006), "T_IK_Chalk", .003, 1, yaw=yaw)
    n = len(lines)
    for i, (txt, col) in enumerate(lines):
        ly = y + (n - 1) / 2 * size * 1.5 - i * size * 1.5
        text_lite(m, txt, (x, ly, z - .015), size, "C_" + col, .004, yaw)


def hook(m, x, y, z):
    bar(m, (x, y, z), (x, y - .07, z), .005, "C_" + STEEL, 5)
    torus_arc(m, .018, .005, (x + .018, y - .07, z), "C_" + STEEL, 180, 360, pitch=90, seg=6, minor=5)


# ------------------------------------------------------------------------------------------- icons
def icon_bread(k):
    ball(k, (0, 0, 0), (.22, .12, .1), "T_IK_Crust", 16, 8, pitch=90)
    for x in (-.05, 0, .05):
        dbox(k, (.012, .07, .01), (x, 0, -.05), "C_F4E6C8", .004, 1, roll=20)


def icon_cheese(k):
    prism(k, [(-.12, -.07), (.12, -.07), (.12, .03), (-.12, .09)], .05, (0, 0, 0), "T_IK_Cheese")
    for x, y in ((-.05, -.02), (.05, 0), (.07, -.045), (-.01, .03)):
        cyl(k, .014, .01, (x, y, -.03), "C_C99A2E", 10, pitch=-90)


def icon_steak(k):
    body = [(math.cos(math.radians(a)) * .13 * (1 + .12 * math.sin(math.radians(a * 2))), math.sin(math.radians(a)) * .09) for a in range(0, 360, 20)]
    prism(k, [(x * 1.12, y * 1.15) for x, y in body], .03, (0, 0, .01), "C_F6E6DA")
    prism(k, body, .045, (0, 0, 0), "T_IK_Meat")
    cyl(k, .025, .05, (.03, .01, -.03), "C_" + WHITE, 12, pitch=-90)


def icon_fish(k):
    fish(k, (-.13, 0, -.02), .26, 0, False, "C_2E86DE", "C_1F6FB8")


def cheese_wheel(m, center, r, h, cut=False, obj="Body"):
    x, y, z = center
    if not cut:
        cyl(m, r, h, center, "T_IK_Rind", 22, min(.03, h * .3), obj=obj)
        cyl(m, r * .9, .004, (x, y + h - .001, z), "C_E3A948", 22, obj=obj)
        return
    # Wheel with a wedge taken out: rind outline plus a paler cut face.
    pts = [(0, 0)] + arc_points(r, 35, 360, 20)
    prism_t(m, [(px, pz) for px, pz in pts], h, (x, y + h / 2, z), "T_IK_Rind", pitch=90, obj=obj)
    for a in (35, 360):
        ra = math.radians(a)
        dbox(m, (r, h * .92, .004), (x + math.cos(ra) * r / 2, y + h / 2, z + math.sin(ra) * r / 2), "T_IK_Cheese", 0, 1, yaw=-a, obj=obj)


def slicer(m, cx, cz, y0=.94):
    """Deli slicer: red enamel body, chrome blade and guard, carriage with a cheese block, flywheel."""
    red = "C_C8352D"
    dbox(m, (.46, .08, .36), (cx, y0 + .04, cz), red, .03)
    for x in (-.18, .18):
        for z in (-.13, .13):
            cyl(m, .02, .02, (cx + x, y0 - .01, cz + z), "C_" + DARK, 8)
    dbox(m, (.14, .24, .14), (cx - .1, y0 + .2, cz + .08), red, .04)
    dbox(m, (.18, .12, .22), (cx - .1, y0 + .36, cz + .02), red, .05, 3)
    cyl(m, .165, .012, (cx - .02, y0 + .3, cz - .02), "C_DCE1E6", 32, roll=90)
    cyl(m, .05, .03, (cx + .0, y0 + .3, cz - .02), "C_" + STEEL, 16, .01, roll=90)
    torus_arc(m, .175, .015, (cx - .005, y0 + .3, cz - .02), red, 20, 200, roll=90, seg=14, minor=6)
    dbox(m, (.02, .12, .2), (cx + .02, y0 + .12, cz - .06), "C_" + STEEL, .006)
    # Carriage sliding in front of the blade, with a block of cheese.
    dbox(m, (.18, .02, .22), (cx + .12, y0 + .16, cz - .05), "T_IK_Steel", .006, roll=-10)
    dbox(m, (.02, .14, .22), (cx + .03, y0 + .22, cz - .05), "T_IK_Steel", .006)
    dbox(m, (.12, .1, .18), (cx + .1, y0 + .22, cz - .05), "T_IK_Cheese", .01)
    bar(m, (cx + .2, y0 + .2, cz - .05), (cx + .27, y0 + .34, cz - .05), .01, "C_" + STEEL, 6)
    ball(m, (cx + .27, y0 + .35, cz - .05), (.035, .035, .035), "C_" + DARK)
    # Flywheel (manual slicer icon) and thickness knob.
    torus(m, .1, .014, (cx - .25, y0 + .22, cz + .06), red, roll=90, seg=20, minor=6)
    for a in range(0, 360, 60):
        r = math.radians(a)
        bar(m, (cx - .25, y0 + .22, cz + .06), (cx - .25, y0 + .22 + math.sin(r) * .1, cz + .06 + math.cos(r) * .1), .007, red, 5)
    cyl(m, .02, .03, (cx - .28, y0 + .22, cz + .06), "C_" + STEEL, 10, roll=90)
    bar(m, (cx - .28, y0 + .3, cz + .12), (cx - .33, y0 + .3, cz + .12), .01, "C_" + DARK, 6)
    cyl(m, .035, .04, (cx - .05, y0 + .1, cz - .2), "C_" + DARK, 14, .01, pitch=-90)


def band_saw(m, cx, cz):
    dbox(m, (.5, .88, .4), (cx, .47, cz), "T_IK_Steel", .02)
    dbox(m, (.46, .04, .36), (cx, .04, cz), "C_" + DARK, .01)
    dbox(m, (.008, .6, .006), (cx, .52, cz - .201), "C_" + DARK, .002, 1)
    for x in (-.12, .12):
        bar(m, (cx + x, .62, cz - .215), (cx + x, .78, cz - .215), .008, "C_" + STEEL, 6)
    dbox(m, (.2, .12, .04), (cx, .3, cz - .21), "C_" + DARK, .01)
    for i in range(5):
        dbox(m, (.16, .008, .006), (cx, .26 + i * .02, cz - .232), "C_" + STEEL, .002, 1)
    dbox(m, (.62, .035, .5), (cx, .925, cz - .06), "T_IK_Steel", .008)
    dbox(m, (.5, .98, .16), (cx, 1.44, cz + .12), "C_" + WHITE, .04)
    dbox(m, (.505, .06, .165), (cx, 1.22, cz + .12), "C_D64541", .01)
    for y in (1.2, 1.72):
        cyl(m, .19, .02, (cx, y, cz + .04), "C_" + WHITE, 28, .008, pitch=-90)
        cyl(m, .05, .015, (cx, y, cz + .02), "C_" + STEEL, 14, pitch=-90)
    dbox(m, (.14, .1, .22), (cx + .02, 1.64, cz - .05), "C_" + WHITE, .03)
    dbox(m, (.03, .12, .03), (cx + .02, 1.54, cz - .12), "C_" + STEEL, .008)
    dbox(m, (.006, .6, .022), (cx + .02, 1.245, cz - .12), "C_E8EDF0", .002, 1)
    dbox(m, (.1, .14, .06), (cx - .22, 1.1, cz - .02), "C_" + DARK, .015)
    cyl(m, .022, .02, (cx - .22, 1.12, cz - .05), "C_" + RED, 10, pitch=-90)
    cyl(m, .015, .02, (cx - .22, 1.07, cz - .05), "C_27AE60", 10, pitch=-90)
    dbox(m, (.14, .012, .1), (cx - .12, .945, cz - .12), "T_IK_Steel", .004)
    dbox(m, (.02, .08, .1), (cx - .05, .98, cz - .12), "T_IK_Steel", .004)
    dbox(m, (.2, .1, .13), (cx - .15, .993, cz - .2), "T_IK_Meat", .03)
    for i in range(4):
        cyl(m, .012, .13, (cx - .23 + i * .05, .995, cz - .265), "C_F6E6DA", 8, pitch=-90)


def meat_grinder(m, cx, cz, y0=.94):
    dbox(m, (.26, .28, .32), (cx, y0 + .14, cz + .02), "T_IK_Steel", .04)
    cyl(m, .1, .18, (cx, y0 + .2, cz + .1), "C_" + STEEL, 16, .02, pitch=90)
    for i in range(4):
        torus(m, .101, .006, (cx, y0 + .2, cz + .13 + i * .03), "C_" + DARK, pitch=90, seg=16, minor=5)
    cyl(m, .06, .18, (cx, y0 + .34, cz + .04), "C_DCE1E6", 16, .01, pitch=-90)
    torus(m, .062, .012, (cx, y0 + .34, cz - .13), "C_" + STEEL, pitch=90, seg=16, minor=6)
    cyl(m, .058, .01, (cx, y0 + .34, cz - .145), "C_9A9A94", 16, pitch=-90)
    for a in range(0, 360, 60):
        r = math.radians(a)
        cyl(m, .008, .004, (cx + math.cos(r) * .03, y0 + .34 + math.sin(r) * .03, cz - .152), "C_" + DARK, 6, pitch=-90)
    for i, dx in enumerate((-.025, 0, .025, -.012, .012)):
        dy = (i // 3) * .02
        bar(m, (cx + dx, y0 + .33 + dy, cz - .152), (cx + dx * 1.4, y0 + .22, cz - .2), .009, "T_IK_Meat", 6)
        bar(m, (cx + dx * 1.4, y0 + .22, cz - .2), (cx + dx * 2, y0 + .07, cz - .18), .009, "T_IK_Meat", 6)
    dbox(m, (.24, .04, .16), (cx, y0 + .02, cz - .16), "T_IK_Steel", .01)
    ball(m, (cx, y0 + .06, cz - .16), (.18, .06, .12), "T_IK_Meat", 12, 7)
    cyl(m, .045, .14, (cx, y0 + .34, cz + .04), "C_DCE1E6", 14)
    dbox(m, (.34, .025, .28), (cx, y0 + .49, cz + .04), "T_IK_Steel", .008)
    for x in (-.17, .17):
        dbox(m, (.01, .04, .28), (cx + x, y0 + .51, cz + .04), "T_IK_Steel", .004)
    for i, (dx, dz) in enumerate(((-.08, -.02), (.06, .06), (.1, -.06), (-.04, .09))):
        dbox(m, (.08, .05, .07), (cx + dx, y0 + .525, cz + .04 + dz), "T_IK_Meat", .015, yaw=i * 30)
    cyl(m, .03, .16, (cx + .12, y0 + .5, cz + .12), "C_" + WHITE, 10, .01)
    dbox(m, (.04, .06, .04), (cx + .14, y0 + .14, cz - .08), "C_" + RED, .01)


def steak(m, center, yaw=0, bone=True):
    k = Local(m, center, yaw)
    dbox(k, (.17, .028, .11), (0, 0, 0), "C_F6E6DA", .013)
    dbox(k, (.155, .03, .095), (-.005, .002, .004), "T_IK_Meat", .012)
    if bone:
        dbox(k, (.012, .032, .08), (.03, .003, .005), "C_" + WHITE, .004, yaw=10)


def lifebuoy(m, center, R=.15, r=.045):
    for i in range(8):
        torus_arc(m, R, r, center, "C_" + (RED if i % 2 == 0 else WHITE), i * 45, i * 45 + 45, pitch=90, seg=4, minor=8)
    for a in (22, 112, 202, 292):
        torus_arc(m, R + r, .008, center, "T_IK_Rope", a - 12, a + 12, pitch=90, seg=3, minor=4)


def fish_net(m, x0, x1, y0, y1, z, cell=.09):
    """Rope net pinned to the wall, sagging a little in the middle, with cork floats."""
    def sag(x, y):
        t = (x - x0) / (x1 - x0)
        return z - .03 * math.sin(t * math.pi) * (1 - (y - y0) / (y1 - y0))
    nx = int((x1 - x0) / cell)
    ny = int((y1 - y0) / cell)
    for i in range(nx + 1):
        for j in range(ny):
            ya, yb = y0 + j * cell, y0 + (j + 1) * cell
            for xa, xb in ((x0 + i * cell, x0 + (i + 1) * cell), (x0 + (i + 1) * cell, x0 + i * cell)):
                if max(xa, xb) <= x1 + 1e-6:
                    bar(m, (xa, ya, sag(xa, ya)), (xb, yb, sag(xb, yb)), .004, "T_IK_Rope", 4)
    for i in range(nx + 1):
        x = x0 + i * cell
        if i % 2 == 0:
            ball(m, (x, y1 + .01, z), (.05, .035, .05), "C_EC862E" if i % 4 else "C_D69C53", 10, 6)
    bar(m, (x0, y1, z), (x1, y1, z), .008, "T_IK_Rope", 6)


def aquarium(m, x0, x1, y0, z0, z1, h=.46):
    w, d, xc, zc = x1 - x0, z1 - z0, (x0 + x1) / 2, (z0 + z1) / 2
    dbox(m, (w + .02, .04, d + .02), (xc, y0 + .02, zc), "C_" + DARK, .01)
    dbox(m, (w - .02, .05, d - .02), (xc, y0 + .065, zc), "C_D9C9A0", .01, 1)
    for i in range(14):
        ball(m, (x0 + .05 + (i * .137) % (w - .1), y0 + .09, z0 + .05 + (i * .071) % (d - .1)), (.04, .025, .035), "C_" + ("9A9A94" if i % 3 else "C4673D"), 6, 4)
    dbox(m, (w - .03, h - .06, .01), (xc, y0 + h / 2 + .02, z1 - .02), "C_1F6FB8", .003, 1)
    dbox(m, (w - .02, h - .08, d - .02), (xc, y0 + h / 2 + .01, zc), "G_Glass", .004, 1)
    dbox(m, (w, h, d), (xc, y0 + h / 2 + .02, zc), "G_Glass", .006, 1)
    for x in (x0, x1):
        for z in (z0, z1):
            dbox(m, (.02, h, .02), (x, y0 + h / 2 + .02, z), "C_" + DARK, .005)
    dbox(m, (w + .03, .05, d + .03), (xc, y0 + h + .045, zc), "C_" + DARK, .012)
    dbox(m, (w - .1, .012, .03), (xc, y0 + h + .018, zc - .05), "E_A9E0F5", .003, 1)
    sway = m.anim("Anim Sway")
    for i, sx in enumerate((x0 + .08, x0 + .14, x1 - .1)):
        for k in range(4):
            bar(m, (sx + math.sin(k) * .015, y0 + .09 + k * .07, z1 - .07), (sx + math.sin(k + 1) * .015, y0 + .16 + k * .07, z1 - .07), .012, "C_" + (LEAF if k % 2 else LEAFD), 5, sway)
    bob = m.anim("Anim Bob")
    fish(m, (xc - .12, y0 + .27, zc - .02), .2, 10, False, "C_D74A3C", "C_F28C38", bob)
    bob2 = m.anim("Anim Bob")
    fish(m, (xc + .18, y0 + .17, zc + .04), .16, 190, False, "C_F2C23F", "C_EC862E", bob2)
    # Crab on the gravel.
    cx, cy, cz = x1 - .16, y0 + .12, zc - .02
    ball(m, (cx, cy, cz), (.1, .04, .08), "C_D74A3C", 12, 6)
    for s in (-1, 1):
        for i in range(3):
            bar(m, (cx + s * .04, cy, cz - .02 + i * .025), (cx + s * .08, cy - .02, cz - .03 + i * .03), .005, "C_D74A3C", 4)
        ball(m, (cx + s * .035, cy + .01, cz - .05), (.035, .025, .03), "C_D74A3C", 8, 5)
        ball(m, (cx + s * .015, cy + .03, cz - .035), (.012, .012, .012), "C_1A1A1A", 6, 4)
    for i in range(6):
        ball(m, (x0 + .1 + (i % 2) * .01, y0 + .15 + i * .05, z0 + .08), (.015, .015, .015), "C_E0F4FC", 6, 4)
    cyl(m, .015, h - .04, (x0 + .1, y0 + .06, z0 + .08), "C_2F3A40", 8)


def hanging_scale(m, x, z, y_top=2.02, wall=1.39):
    bar(m, (x, y_top, wall), (x, y_top, z), .012, "C_" + DARK, 6)
    dbox(m, (.06, .08, .03), (x, y_top - .03, wall - .02), "C_" + DARK, .01)
    bar(m, (x, y_top, z), (x, y_top - .07, z), .006, "C_" + STEEL, 5)
    cyl(m, .11, .05, (x, y_top - .19, z - .025), "C_" + RED, 26, .015, pitch=-90)
    cyl(m, .095, .01, (x, y_top - .19, z - .05), "C_" + WHITE, 26, pitch=-90)
    for a in range(-120, 121, 30):
        r = math.radians(a)
        dbox(m, (.004, .016, .004), (x + math.sin(r) * .075, y_top - .19 + math.cos(r) * .075, z - .058), "C_" + DARK, 0, 1, roll=a)
    dbox(m, (.005, .075, .004), (x + .015, y_top - .17, z - .062), "C_" + DARK, 0, 1, roll=-20)
    ball(m, (x, y_top - .19, z - .062), (.018, .018, .01), "C_" + DARK)
    bar(m, (x, y_top - .3, z), (x, y_top - .38, z), .006, "C_" + STEEL, 5)
    for a in (90, 210, 330):
        r = math.radians(a)
        bar(m, (x, y_top - .38, z), (x + math.cos(r) * .13, y_top - .62, z + math.sin(r) * .13), .003, "C_" + STEEL, 4)
    lathe(m, [(0, 0), (.1, 0), (.14, .035), (.145, .04)], (x, y_top - .66, z), "T_IK_Steel", 22, cap=False)




# ------------------------------------------------------------------------------------------- big rounded sectors
# Plan of every detailed sector (Unity space, customers on -Z):
#   curved back wall  z = WALL_Z - WALL_SAG * (x / 1.8)^2   (x ±1.8, bows away from the customer)
#   round columns at its ends, a crown cornice with a cove light and an arched name board (no awning)
#   curved serving case on the ellipse (0, CASE_CZ) rx CASE_RX rz CASE_RZ, angles CASE_A0..CASE_A1
#   staff area in between (attendant at STAFF), trade equipment on the floor corners and the curved bench
#   stock on display: 4 Blender-modelled groups "Anim Fill 0..3" (left to right) that Unity shows as stock rises.
WALL_Z, WALL_SAG, WALL_HALF, WALL_H = 1.9, .45, 1.8, 2.3
CASE_CZ, CASE_RX, CASE_RZ, CASE_A0, CASE_A1 = .15, 1.42, .92, 192, 348
BED_Y = 1.03
STAFF = (0, 0, .45)
FOOTPRINT = ((-1.98, -1.3), (1.98, 2.06))


def wall_z(x):
    return WALL_Z - WALL_SAG * (x / WALL_HALF) ** 2


def wall_at(x, d=0):
    """Point on the back wall face at x, `d` metres out towards the customer, and the yaw facing out."""
    f = -2 * WALL_SAG * x / WALL_HALF ** 2
    n = math.hypot(f, 1)
    return (x + d * f / n, wall_z(x) - d / n, math.degrees(math.atan2(-f, 1)))


def wall_path(x0, x1, n=24):
    return [(x0 + (x1 - x0) * i / n, wall_z(x0 + (x1 - x0) * i / n)) for i in range(n + 1)]


def case_at(a, d=0):
    """Point on the counter centre line at ellipse angle a (deg), `d` towards the customer, and the yaw along it."""
    r = math.radians(a)
    px, pz = CASE_RX * math.cos(r), CASE_CZ + CASE_RZ * math.sin(r)
    tx, tz = -CASE_RX * math.sin(r), CASE_RZ * math.cos(r)
    L = math.hypot(tx, tz); tx, tz = tx / L, tz / L
    return (px + tz * d, pz - tx * d, math.degrees(math.atan2(-tz, tx)))


def case_path(a0=CASE_A0, a1=CASE_A1, n=28):
    out = []
    for i in range(n + 1):
        x, z, _ = case_at(a0 + (a1 - a0) * i / n)
        out.append((x, z))
    return out


def sweep(m, path, profile, key, obj="Body", caps=True):
    """Extrude a closed cross-section along a path on the floor plan.
    path: [(x, z)] in Unity space; profile: [(d, y)] with d measured sideways, positive to the right of the
    direction of travel (= towards the customer for paths drawn left to right across the front)."""
    bm = bmesh.new()
    n = len(path)
    rings = []
    for i, (x, z) in enumerate(path):
        a = path[max(0, i - 1)]; b = path[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, tz) or 1; tx, tz = tx / L, tz / L
        nx, nz = tz, -tx
        rings.append([bm.verts.new(U(x + nx * d, y, z + nz * d)) for d, y in profile])
    k = len(profile)
    for i in range(n - 1):
        for j in range(k):
            try:
                bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % k], rings[i][(j + 1) % k]))
            except ValueError:
                pass
    if caps:
        for ring in (rings[0], rings[-1]):
            try:
                f = bm.faces.new(ring)
                if len(ring) > 4:
                    bmesh.ops.triangulate(bm, faces=[f], quad_method="BEAUTY", ngon_method="EAR_CLIP")
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m.add(bm, key, obj)


def rect(d0, d1, y0, y1):
    return [(d0, y0), (d1, y0), (d1, y1), (d0, y1)]


def circle_prof(dc, yc, r, n=8):
    return [(dc + r * math.cos(2 * math.pi * i / n), yc + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def sub_path(path, t0, t1):
    """Part of a polyline between fractions t0..t1 of its points (inclusive, resampled)."""
    n = len(path) - 1
    out = []
    steps = max(2, int(round((t1 - t0) * n)) + 1)
    for i in range(steps + 1):
        t = (t0 + (t1 - t0) * i / steps) * n
        k = min(int(t), n - 1); f = t - k
        out.append((path[k][0] + (path[k + 1][0] - path[k][0]) * f, path[k][1] + (path[k + 1][1] - path[k][1]) * f))
    return out


def end_cap(m, path, at_end, profile, key, thick=.04):
    """A flat side panel with `profile` across the start or end of a swept piece."""
    if at_end:
        a, b = path[-2], path[-1]
    else:
        a, b = path[1], path[0]
    tx, tz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(tx, tz); tx, tz = tx / L, tz / L
    p0 = (b[0] - tx * thick * .2, b[1] - tz * thick * .2)
    p1 = (b[0] + tx * thick * .8, b[1] + tz * thick * .8)
    if not at_end:
        p0, p1 = p1, p0
        profile = [(-d, y) for d, y in profile]
    sweep(m, [p0, p1], profile, key)


# ------------------------------------------------------------------------------------------- shell: wall, columns, board
def sector_shell(m, sid, wall, wains, floor, trim=GOLD, icon=None, board=NAVY):
    title, hexc = SECTORS[sid]
    acc = "C_" + hexc
    wp = wall_path(-WALL_HALF, WALL_HALF, 32)
    # Wall body (thick, textured) with wainscot, chair rail, skirting and a crown cornice with a cove light.
    sweep(m, wp, rect(-.14, 0, 0, WALL_H), wall)
    sweep(m, wp, rect(0, .025, .12, 1.0), wains)
    sweep(m, wp, [(0, .98), (.045, .99), (.055, 1.02), (.045, 1.05), (0, 1.06)], "C_" + trim)
    sweep(m, wp, rect(0, .04, 0, .12), "C_" + NAVY)
    sweep(m, wp, [(-.16, WALL_H - .02), (.06, WALL_H - .02), (.1, WALL_H + .04), (.1, WALL_H + .1), (.14, WALL_H + .14), (.14, WALL_H + .2), (-.16, WALL_H + .2)], "C_" + NAVY)
    sweep(m, wp, rect(.1, .15, WALL_H + .1, WALL_H + .13), "C_" + trim)
    sweep(m, wp, rect(-.16, .16, WALL_H + .2, WALL_H + .23), "C_" + trim)
    sweep(m, sub_path(wp, .03, .97), rect(.03, .07, WALL_H - .05, WALL_H - .03), "E_FFF4DC")
    # Upper wall framed into three soft arched panels by slim pilasters.
    for x in (-1.2, -.4, .4, 1.2):
        px, pz, yaw = wall_at(x, .02)
        dbox(m, (.08, WALL_H - 1.1, .04), (px, 1.06 + (WALL_H - 1.1) / 2, pz), acc, .015, yaw=yaw)
        dbox(m, (.1, .05, .05), (px, 1.1, pz), "C_" + trim, .012, yaw=yaw)
        dbox(m, (.1, .05, .05), (px, WALL_H - .06, pz), "C_" + trim, .012, yaw=yaw)
    # Round end columns with gold bands and a glowing globe.
    for s in (-1, 1):
        cx, cz = s * (WALL_HALF + .02), wall_z(WALL_HALF) - .04
        cyl(m, .2, .14, (cx, 0, cz), "C_" + NAVY, 24, .03)
        cyl(m, .16, WALL_H + .06, (cx, .14, cz), acc, 24, .02)
        for y in (.5, 1.02, 1.6, 2.1):
            torus(m, .162, .014, (cx, y, cz), "C_" + trim, seg=24, minor=6)
        cyl(m, .21, .08, (cx, WALL_H + .2, cz), "C_" + trim, 24, .03)
        cyl(m, .09, .08, (cx, WALL_H + .28, cz), "C_" + NAVY, 16, .02)
        ball(m, (cx, WALL_H + .46, cz), (.24, .24, .24), "E_FFF4DC", 16, 10)
        torus(m, .09, .012, (cx, WALL_H + .36, cz), "C_" + trim, seg=16, minor=5)
    # Arched name board over the centre of the cornice.
    bw, bh = 2.3, .5
    arch = [(-bw / 2, 0), (bw / 2, 0), (bw / 2, bh * .55)] + [(math.cos(math.radians(a)) * bw / 2, bh * .55 + math.sin(math.radians(a)) * bh * .45) for a in range(10, 171, 10)] + [(-bw / 2, bh * .55)]
    zb = wall_z(0)
    prism(m, [(x * 1.035, y * 1.08 - .02) for x, y in arch], .06, (0, WALL_H + .18, zb - .02), "C_" + trim)
    prism(m, arch, .06, (0, WALL_H + .18, zb - .05), "C_" + board)
    text_mid(m, title, (0, WALL_H + .4, zb - .1), .25, "C_" + GOLDL, .04)
    for s in (-1, 1):
        cyl(m, .15, .05, (s * 1.02, WALL_H + .42, zb - .04), "C_" + trim, 24, .015, pitch=-90)
        cyl(m, .125, .03, (s * 1.02, WALL_H + .42, zb - .09), "C_" + CREAM, 24, .01, pitch=-90)
        if icon:
            icon(Local(m, (s * 1.02, WALL_H + .42, zb - .13), 0))
    # Floor of the service area.
    inner = [(x, z) for x, z in (case_at(CASE_A0 + (CASE_A1 - CASE_A0) * i / 24, -.34)[:2] for i in range(25))]
    back = [(x, wall_z(x) + .01) for x, _ in reversed(wall_path(-WALL_HALF + .1, WALL_HALF - .1, 16))]
    prism_t(m, inner + back, .016, (0, .008, 0), floor, pitch=90)
    # Pendant lamps on arms out of the cornice.
    for x in (-.85, 0, .85):
        px, pz, yaw = wall_at(x, 0)
        bar(m, (px, WALL_H + .06, pz), (px, WALL_H + .06, .62), .018, "C_" + DARK, 8)
        bar(m, (px, WALL_H + .06, .62), (px, 2.08, .62), .006, "C_" + DARK, 5)
        lathe(m, [(0, 0), (.16, 0), (.15, .04), (.1, .12), (.04, .16), (.02, .2), (0, .2)], (px, 1.9, .62), acc, 20)
        lathe(m, [(0, 0), (.13, 0)], (px, 1.895, .62), "E_FFF4DC", 16)
        torus(m, .158, .01, (px, 1.905, .62), "C_" + trim, seg=20, minor=5)


def serving_case(m, sid, front, bed, frame=GOLD, bumper=STEEL):
    """Curved refrigerated counter following the ellipse, with curved glass and end caps."""
    title, hexc = SECTORS[sid]
    acc = "C_" + hexc
    p = case_path()
    sweep(m, p, rect(-.3, .36, 0, .1), "C_" + NAVY)
    sweep(m, p, rect(-.34, .4, .1, .93), front)
    sweep(m, p, rect(.4, .432, .8, .88), acc)
    sweep(m, p, rect(.4, .426, .9, .925), "C_" + frame)
    sweep(m, p, rect(.36, .372, .02, .09), "C_" + DARK)
    # Raised front panels between gold frames.
    for i in range(5):
        t0, t1 = .025 + i * .19, .025 + i * .19 + .17
        sp = sub_path(p, t0, t1)
        sweep(m, sp, rect(.4, .415, .2, .72), "C_" + frame)
        sweep(m, sub_path(p, t0 + .006, t1 - .006), rect(.4, .425, .215, .705), front)
    # Chrome bumper rail on stand-offs.
    sweep(m, sub_path(p, .02, .98), circle_prof(.5, .72, .016), "C_" + bumper, caps=True)
    for t in (.06, .3, .5, .7, .94):
        x, z, yaw = case_at(CASE_A0 + (CASE_A1 - CASE_A0) * t, .45)
        dbox(m, (.03, .03, .1), (x, .72, z), "C_" + bumper, .008, yaw=yaw)
    # Marble top with a rounded nose, display bed, price rail.
    sweep(m, p, [(-.37, .93), (.45, .93), (.475, .945), (.48, .965), (.47, .99), (.45, 1.0), (-.37, 1.0)], "T_IK_Marble")
    sweep(m, p, rect(-.14, .37, 1.0, BED_Y), bed)
    sweep(m, p, rect(.37, .395, .995, 1.07), "T_IK_PriceRail")
    # Curved glass front, flat top, rear sliding doors, LED and steel frame.
    glass = [(-.02 + .41 * math.cos(math.radians(a)), 1.065 + .41 * math.sin(math.radians(a))) for a in range(0, 91, 10)]
    glass_in = [(-.02 + .398 * math.cos(math.radians(a)), 1.065 + .398 * math.sin(math.radians(a))) for a in range(90, -1, -10)]
    sweep(m, sub_path(p, .004, .996), glass + glass_in, "G_Glass")
    sweep(m, sub_path(p, .004, .996), rect(-.24, -.02, 1.463, 1.474), "G_Glass")
    sweep(m, p, rect(-.035, -.005, 1.47, 1.492), "C_" + STEEL)
    sweep(m, p, rect(-.255, -.225, 1.47, 1.488), "C_" + STEEL)
    sweep(m, sub_path(p, .01, .99), rect(-.16, -.06, 1.452, 1.462), "E_FFF4DC")
    sweep(m, sub_path(p, .004, .996), rect(-.235, -.225, 1.03, 1.46), "G_Glass")
    sweep(m, p, rect(-.25, -.21, 1.0, 1.035), "C_" + STEEL)
    cap = [(-.38, .96), (.48, .96), (.43, 1.065)] + [(-.02 + .43 * math.cos(math.radians(a)), 1.065 + .43 * math.sin(math.radians(a))) for a in range(15, 91, 15)] + [(-.26, 1.495), (-.26, .96)]
    end_cap(m, p, False, cap, acc, .05)
    end_cap(m, p, True, cap, acc, .05)
    for t in (.12, .88):
        x, z, yaw = case_at(CASE_A0 + (CASE_A1 - CASE_A0) * t, -.23)
        bar(m, (x, 1.2, z - .015), (x, 1.34, z - .015), .008, "C_" + STEEL, 6)


def curved_bench(m, x0, x1, body="T_IK_Steel", top="T_IK_Steel", depth=.42, h=.9):
    wp = wall_path(x0, x1, 16)
    sweep(m, wp, rect(.03, depth - .02, .08, h), body)
    sweep(m, wp, rect(.05, depth - .05, 0, .08), "C_" + NAVY)
    sweep(m, wp, [(0, h), (depth + .02, h), (depth + .03, h + .02), (depth + .02, h + .04), (0, h + .04)], top)
    n = max(1, int(round((x1 - x0) / .45)))
    for i in range(1, n):
        x, z, yaw = wall_at(x0 + (x1 - x0) * i / n, depth - .015)
        dbox(m, (.01, h - .16, .01), (x, .5, z), "C_" + DARK, .002, yaw=yaw)
    for i in range(n):
        x, z, yaw = wall_at(x0 + (x1 - x0) * (i + .5) / n + (.12 if i % 2 else -.12), depth - .005)
        dbox(m, (.1, .018, .02), (x, .8, z), "C_" + STEEL, .006, yaw=yaw)


def curved_shelf(m, x0, x1, y, key, depth=.26, bracket="C_" + DARK):
    wp = wall_path(x0, x1, 14)
    sweep(m, wp, rect(0, depth, y - .035, y), key)
    sweep(m, wp, rect(depth - .02, depth, y - .035, y + .02), key)
    for x in (x0 + .08, (x0 + x1) / 2, x1 - .08):
        px, pz, yaw = wall_at(x, 0)
        prism(m, [(0, 0), (-.03, 0), (-.03, -.16), (-.2, -.02), (-.2, 0)], .025, (px, y - .035, pz), bracket, 0, yaw + 90)


def side_closures(m, key, trim=GOLD):
    """Low curved partition on the left, swing gate on the right, between counter ends and columns."""
    lx, lz, _ = case_at(CASE_A0, -.3)
    cx, cz = -(WALL_HALF + .02), wall_z(WALL_HALF) - .04
    pts = [(lx + (cx - lx) * t + math.sin(t * math.pi) * -.12, lz + (cz - lz) * t) for t in (i / 8 for i in range(9))]
    pts = list(reversed(pts))
    sweep(m, pts, rect(-.04, .04, 0, .98), key)
    sweep(m, pts, rect(-.05, .05, .98, 1.02), "C_" + trim)
    sweep(m, pts, rect(-.045, .045, 0, .1), "C_" + NAVY)
    rx, rz, _ = case_at(CASE_A1, -.3)
    gx, gz = WALL_HALF + .02, wall_z(WALL_HALF) - .04
    cyl(m, .035, 1.05, (rx + .02, 0, rz + .05), "C_" + NAVY, 12, .01)
    ball(m, (rx + .02, 1.07, rz + .05), (.06, .06, .06), "C_" + trim)
    # Half-open swing gate.
    L = math.hypot(gx - rx, gz - rz) - .25
    ang = math.degrees(math.atan2(-(gz - rz), gx - rx)) + 35
    k = Local(m, (rx + .02, 0, rz + .05), ang)
    dbox(k, (L, .06, .04), (L / 2 + .04, .95, 0), "C_" + trim, .015)
    dbox(k, (L, .06, .04), (L / 2 + .04, .25, 0), "C_" + trim, .015)
    dbox(k, (L - .06, .64, .03), (L / 2 + .04, .6, 0), key, .01)
    for t in (.3, .7):
        bar(k, (t * L, .25, .02), (t * L, .95, .02), .008, "C_" + trim, 6)


def price_card(m, center, yaw, col=RED, obj="Body"):
    k = Local(m, center, yaw, obj=obj)
    bar(k, (0, 0, 0), (0, .07, 0), .003, "C_" + STEEL, 5)
    dbox(k, (.075, .048, .005), (0, .095, 0), "C_" + WHITE, .004, pitch=-15)
    dbox(k, (.075, .013, .006), (0, .112, -.004), "C_" + col, .003, pitch=-15)


def parsley(m, center, obj="Body"):
    x, y, z = center
    for i in range(3):
        a = i * 2.1
        ball(m, (x + math.cos(a) * .018, y + .01, z + math.sin(a) * .018), (.035, .02, .03), "C_" + ("5DAE3E" if i % 2 else "2F6F2C"), 5, 3, obj)


def fill_slots(i, rows=(.24, .02), per_row=3):
    """Placements (x, z, yaw) on the display bed for fill group i: rows at depth d, spread along the arc."""
    span = (CASE_A1 - CASE_A0 - 8) / 4
    a0 = CASE_A0 + 4 + i * span
    out = []
    for r, d in enumerate(rows):
        for k in range(per_row):
            a = a0 + span * (k + .5) / per_row
            out.append(case_at(a, d))
    return out


# ------------------------------------------------------------------------------------------- display products
def tray(k, w, dp, key="T_IK_Steel", h=.018):
    dbox(k, (w, h, dp), (0, h / 2, 0), key, .006)
    dbox(k, (w - .02, .004, dp - .02), (0, h, 0), key, .002)


def roll_bun(k, pos, s=1.0, obj="Body"):
    x, y, z = pos
    ball(k, (x, y + .025 * s, z), (.09 * s, .055 * s, .06 * s), "T_IK_Crust", 8, 5, obj)
    dbox(k, (.07 * s, .008, .012 * s), (x, y + .052 * s, z), "C_F4E6C8", .004, obj=obj)


def donut(k, pos, glaze="F4A6C1", obj="Body"):
    x, y, z = pos
    torus(k, .035, .02, (x, y + .02, z), "T_IK_Crust", obj=obj, seg=9, minor=5)
    torus_arc(k, .035, .021, (x, y + .026, z), "C_" + glaze, 0, 360, obj=obj, seg=9, minor=3)
    for j in range(3):
        a = j * 1.7
        dbox(k, (.012, .006, .004), (x + math.cos(a) * .035, y + .045, z + math.sin(a) * .035), "C_" + ("FBF8F1" if j % 2 else "5DA0D8"), 0, 1, yaw=j * 40, obj=obj)


def cake(k, pos, r=.1, h=.08, col="F4A6C1", cut=True, obj="Body"):
    x, y, z = pos
    if cut:
        pts = [(0, 0)] + arc_points(r, 50, 360, 16)
        prism_t(k, pts, h, (x, y + h / 2, z), "C_" + col, pitch=90, obj=obj)
        prism_t(k, pts, .012, (x, y + h + .006, z), "C_FBF8F1", pitch=90, obj=obj)
    else:
        cyl(k, r, h, (x, y, z), "C_" + col, 16, .01, obj=obj)
        cyl(k, r * 1.02, .015, (x, y + h, z), "C_FBF8F1", 16, .005, obj=obj)
    for a in range(60 if cut else 0, 360, 45):
        ball(k, (x + math.cos(math.radians(a)) * r * .75, y + h + .025, z - math.sin(math.radians(a)) * r * .75), (.022, .022, .022), "C_D74A3C", 6, 4, obj)


def fill_padaria(m, i, obj):
    for j, (x, z, yaw) in enumerate(fill_slots(i, per_row=2)):
        k = Local(m, (x, BED_Y, z), yaw, obj=obj)
        tray(k, .34, .2, "T_IK_WoodLight" if j % 2 else "T_IK_Steel")
        kind = (i * 2 + j) % 5
        if kind == 0:
            for a in range(6):
                roll_bun(k, (-.11 + (a % 3) * .11, .018, -.05 + (a // 3) * .1), 1.0, obj)
        elif kind == 1:
            for a in range(5):
                croissant(k, (-.12 + a * .06, .018, (-.04 if a % 2 else .04)), .95, 90 + a * 7, obj)
        elif kind == 2:
            for a in range(6):
                donut(k, (-.11 + (a % 3) * .11, .018, -.05 + (a // 3) * .1), ("F4A6C1", "8A5A34", "FBF8F1")[a % 3], obj)
        elif kind == 3:
            cake(k, (-.06, .018, 0), .085, .075, ("F4A6C1", "8A5A34", "F2C94A")[i % 3], True, obj)
            for a in range(3):
                ball(k, (.09 + (a % 2) * .04, .035 + (a // 2) * .03, -.05 + a * .04), (.04, .035, .04), "C_F2C94A", 8, 5, obj)
        else:
            for a in range(3):
                baguette(k, (-.15, .04, -.06 + a * .06), (.15, .04, -.06 + a * .06), .022, obj)
        if j == 0:
            price_card(k, (.0, .018, -.12), 0, (RED, GOLD, "27AE60")[i % 3], obj)


def fill_acougue(m, i, obj):
    for j, (x, z, yaw) in enumerate(fill_slots(i, per_row=2)):
        k = Local(m, (x, BED_Y, z), yaw, obj=obj)
        tray(k, .34, .2, "C_FBFAF6")
        kind = (i * 2 + j) % 5
        if kind == 0:  # picanha steaks with a fat cap
            for a in range(3):
                kk = Local(k, (-.1 + a * .1, .03, 0), 12 * (a - 1))
                dbox(kk, (.09, .03, .16), (0, 0, 0), "T_IK_Meat", .012, obj=obj)
                dbox(kk, (.092, .032, .03), (0, .001, .07), "C_F6E6DA", .01, obj=obj)
        elif kind == 1:  # ribs
            dbox(k, (.28, .03, .14), (0, .035, 0), "T_IK_Meat", .012, obj=obj)
            for a in range(7):
                bar(k, (-.13 + a * .043, .052, -.07), (-.13 + a * .043, .052, .075), .008, "C_F6E6DA", 5, obj)
        elif kind == 2:  # sausage coils
            for c in (-.08, .08):
                for r in (.025, .05):
                    torus(k, r, .014, (c, .035, 0), "C_A8543A", obj=obj, seg=12, minor=5)
        elif kind == 3:  # ground beef mound
            ball(k, (0, .03, 0), (.26, .06, .15), "T_IK_Meat", 12, 6, obj)
            for a in range(6):
                ball(k, (-.1 + a * .04, .06, (-.02 if a % 2 else .02)), (.03, .02, .03), "T_IK_Meat", 6, 4, obj)
        else:  # chicken drumsticks
            for a in range(4):
                kk = Local(k, (-.11 + a * .075, .035, 0), 90 + (a % 2) * 180)
                lathe_s(kk, [(0, 0), (.028, .02), (.03, .06), (.018, .1), (.008, .13), (0, .14)], (0, 0, -.06), "C_E8B89A", (1, 1, .8), 8, pitch=90, obj=obj)
                ball(kk, (0, 0, .085), (.02, .02, .02), "C_FBF8F1", 6, 4, obj)
        parsley(k, (.14, .018, .07), obj)
        if j == 0:
            price_card(k, (0, .018, -.12), 0, (RED, GOLD)[i % 2], obj)


def fill_queijaria(m, i, obj):
    for j, (x, z, yaw) in enumerate(fill_slots(i, per_row=2)):
        k = Local(m, (x, BED_Y, z), yaw, obj=obj)
        dbox(k, (.34, .025, .2), (0, .0125, 0), "T_IK_WoodLight", .008)
        kind = (i * 2 + j) % 5
        y0 = .025
        if kind == 0:  # cut wheel and wedges
            cheese_wheel(k, (-.06, y0, 0), .085, .07, True, obj)
            for a in range(2):
                prism(k, [(0, 0), (.09, .035), (.09, -.035)], .06, (.06 + a * .05, y0 + .03, -.04 + a * .08), "T_IK_Cheese", pitch=90, yaw=20 + a * 60, obj=obj)
        elif kind == 1:  # blocks: prato and mussarela
            dbox(k, (.14, .07, .09), (-.07, y0 + .035, 0), "C_F2C94A", .012, obj=obj)
            dbox(k, (.14, .065, .09), (.08, y0 + .0325, 0), "C_FBF6E6", .012, obj=obj)
            for a in range(3):
                dbox(k, (.004, .066, .09), (-.12 + a * .035, y0 + .034, 0), "C_E6B63A", 0, 1, obj=obj)
        elif kind == 2:  # buffalo mozzarella balls and burrata
            for a in range(5):
                ball(k, (-.12 + a * .06, y0 + .03, (-.03 if a % 2 else .03)), (.055, .05, .055), "C_FBFAF6", 10, 6, obj)
            ball(k, (.02, y0 + .075, 0), (.03, .02, .03), "C_2F6F2C", 6, 4, obj)
        elif kind == 3:  # salami and sliced ham log
            for a in range(2):
                bar(k, (-.14, y0 + .03, -.04 + a * .07), (.02, y0 + .03, -.04 + a * .07), .028, "C_8E2240", 10, obj)
                cyl(k, .026, .005, (.021, y0 + .03, -.04 + a * .07), "C_D74A3C", 10, roll=90, obj=obj)
            for a in range(4):
                cyl(k, .04, .004, (.08 + a * .012, y0 + .04, .0), "C_F4A6C1", 12, roll=90, obj=obj)
        else:  # brie and blue cheese
            cyl(k, .07, .035, (-.07, y0, 0), "C_FBF8F1", 16, .008, obj=obj)
            prism(k, [(0, 0), (.1, .04), (.1, -.04)], .05, (.05, y0 + .025, 0), "C_E3E6D8", pitch=90, obj=obj)
            for a in range(5):
                ball(k, (.1 + (a % 2) * .02, y0 + .052, -.02 + a * .01), (.012, .006, .01), "C_4E6A8A", 5, 3, obj)
        if j == 0:
            price_card(k, (0, .025, -.12), 0, (PURPLE, GOLD)[i % 2], obj)


def fill_peixaria(m, i, obj):
    for j, (x, z, yaw) in enumerate(fill_slots(i, per_row=2)):
        k = Local(m, (x, BED_Y, z), yaw, obj=obj)
        for a in range(6):
            ball(k, (-.13 + a * .052, .012, (a % 2) * .04 - .02), (.08, .03, .12), "C_F4FAFD", 6, 4, obj)
        kind = (i * 2 + j) % 5
        if kind == 0:  # whole fish
            cols = (("T_IK_FishScale", "C_6F8FA6"), ("C_D74A3C", "C_F28C38"), ("C_8FA3AE", "C_5A7488"))
            for a in range(2):
                b, f = cols[(i + a) % 3]
                fish(k, (-.15, .035, -.045 + a * .09), .3, 0, True, b, f, obj)
        elif kind == 1:  # salmon fillets and steaks
            for a in range(3):
                kk = Local(k, (-.1 + a * .1, .03, 0), 10 * (a - 1))
                dbox(kk, (.08, .028, .16), (0, 0, 0), "C_F28C6A", .012, obj=obj)
                for s in range(4):
                    dbox(kk, (.082, .03, .004), (0, .001, -.06 + s * .04), "C_FBD3C0", 0, 1, obj=obj)
        elif kind == 2:  # shrimp pile
            for a in range(11):
                torus_arc(k, .022, .01, (-.12 + (a % 6) * .045, .03 + (a // 6) * .015, -.03 + (a // 6) * .05), "C_F28C6A", 20, 250, yaw=a * 47, seg=5, minor=5, obj=obj)
        elif kind == 3:  # squid and mussels
            for a in range(2):
                lathe_s(k, [(0, 0), (.022, .02), (.024, .1), (.015, .14), (0, .15)], (-.12, .03, -.04 + a * .08), "C_F6E6DA", (1, 1, .6), 8, roll=90, obj=obj)
            for a in range(6):
                ball(k, (.05 + (a % 3) * .04, .03, -.04 + (a // 3) * .07), (.05, .022, .03), "C_2F3A40", 8, 4, obj, yaw=a * 35)
        else:  # crab and lobster
            ball(k, (-.07, .04, 0), (.11, .045, .09), "C_D74A3C", 10, 6, obj)
            for s in (-1, 1):
                for a in range(3):
                    bar(k, (-.07 + s * .04, .035, -.02 + a * .02), (-.07 + s * .08, .02, -.03 + a * .03), .005, "C_D74A3C", 4, obj)
            lathe_s(k, [(0, 0), (.03, .02), (.035, .08), (.025, .15), (.012, .18), (0, .19)], (.03, .04, 0), "C_C8352D", (1, 1, .7), 8, roll=90, obj=obj)
            for s in (-1, 1):
                ball(k, (.02, .04, s * .045), (.05, .02, .03), "C_C8352D", 6, 4, obj)
        if j == 0:
            price_card(k, (0, .01, -.12), 0, (BLUE, RED)[i % 2], obj)


def fills(m, fn):
    for i in range(4):
        fn(m, i, "Anim Fill %d" % i)


# ------------------------------------------------------------------------------------------- padaria
def deck_oven(k):
    """Three-deck stainless bakery oven with glowing windows, control panel and a steam hood (local, facing -Z)."""
    dbox(k, (.86, .1, .6), (0, .05, 0), "C_" + DARK, .02)
    for x in (-.38, .38):
        for z in (-.24, .24):
            cyl(k, .025, .1, (x, 0, z), "C_" + DARK, 8)
    dbox(k, (.86, 1.34, .6), (0, .77, 0), "T_IK_Steel", .03)
    for l in range(3):
        y = .38 + l * .4
        dbox(k, (.64, .3, .03), (-.06, y + .14, -.305), "C_" + DARK, .02)
        dbox(k, (.54, .18, .01), (-.06, y + .15, -.32), "E_FF8A2A", .005)
        for b in range(3):
            ball(k, (-.22 + b * .16, y + .1, -.3), (.12, .06, .06), "T_IK_Crust", 8, 5)
        bar(k, (-.3, y + .31, -.34), (.18, y + .31, -.34), .012, "C_" + STEEL, 8)
        for x in (-.3, .18):
            bar(k, (x, y + .31, -.32), (x, y + .31, -.34), .008, "C_" + STEEL, 5)
    dbox(k, (.16, 1.14, .02), (.33, .9, -.305), "C_" + NAVY, .01)
    for l in range(3):
        y = .52 + l * .4
        cyl(k, .025, .02, (.33, y, -.31), "C_" + WHITE, 12, pitch=-90)
        dbox(k, (.004, .02, .004), (.33, y + .01, -.33), "C_" + RED, 0, 1)
        dbox(k, (.08, .03, .004), (.33, y - .07, -.316), "E_FF4A3A", .002, 1)
    dbox(k, (.96, .12, .72), (0, 1.5, -.04), "T_IK_Steel", .03)
    dbox(k, (.9, .05, .6), (0, 1.43, -.08), "C_" + DARK, .01)
    cyl(k, .07, .5, (.25, 1.56, .12), "T_IK_Steel", 12)
    text_lite(k, "FORNO", (-.06, 1.5, -.405), .06, "C_" + GOLDL, .008)


def spiral_mixer(k, spin_obj):
    """Floor-standing spiral dough mixer (local, facing -Z) with its hook spinning."""
    dbox(k, (.5, .5, .62), (0, .25, .05), "C_" + CREAM, .05)
    dbox(k, (.52, .06, .64), (0, .03, .05), "C_" + NAVY, .02)
    dbox(k, (.3, .55, .22), (0, .75, .26), "C_" + CREAM, .06)
    dbox(k, (.34, .18, .5), (0, 1.1, .12), "C_" + CREAM, .08)
    dbox(k, (.345, .03, .505), (0, 1.02, .12), "C_D98E2B", .01)
    lathe(k, [(0, 0), (.14, 0), (.2, .04), (.22, .28), (.23, .3)], (0, .5, -.1), "T_IK_Steel", 22, cap=False)
    torus(k, .225, .012, (0, .8, -.1), "C_" + STEEL, seg=22, minor=5)
    ball(k, (0, .62, -.1), (.36, .16, .36), "C_F4E6C8", 14, 8)
    ball(k, (.05, .7, -.13), (.16, .08, .14), "C_F7EDD8", 10, 6)
    pts = [(math.cos(t * .9) * .06, 1.0 - t * .045, -.1 + math.sin(t * .9) * .06) for t in range(8)]
    bar(k, (0, 1.02, -.1), (0, .98, -.1), .02, "C_" + STEEL, 8, spin_obj)
    for a, b in zip(pts, pts[1:]):
        bar(k, a, b, .014, "C_" + STEEL, 6, spin_obj)
    dbox(k, (.16, .12, .04), (.12, 1.05, -.14), "C_" + NAVY, .01)
    cyl(k, .018, .015, (.08, 1.06, -.165), "C_27AE60", 10, pitch=-90)
    cyl(k, .018, .015, (.16, 1.06, -.165), "C_" + RED, 10, pitch=-90)


def bread_slicer(k):
    """Bench bread slicer: frame with blade bars, feed tray and bag holder (local, facing -Z)."""
    dbox(k, (.42, .1, .34), (0, .05, 0), "C_" + WHITE, .02)
    dbox(k, (.42, .42, .1), (0, .31, .1), "C_" + WHITE, .03)
    for i in range(11):
        dbox(k, (.004, .3, .012), (-.15 + i * .03, .26, .03), "C_DCE1E6", 0, 1)
    dbox(k, (.36, .015, .16), (0, .12, -.07), "T_IK_Steel", .005, pitch=-8)
    bread_loaf(k, (0, .16, -.07), (.28, .1, .12), 0, scores=2)
    dbox(k, (.1, .05, .03), (.15, .44, .05), "C_D98E2B", .01)
    bar(k, (-.26, .12, -.12), (-.26, .12, .12), .01, "C_" + STEEL, 6)


def proof_rack(k):
    """Mobile rack of trays with dough balls (local)."""
    for x in (-.24, .24):
        for z in (-.2, .2):
            bar(k, (x, .06, z), (x, 1.5, z), .012, "C_" + STEEL, 6)
            ball(k, (x, .03, z), (.05, .05, .05), "C_" + DARK, 8, 5)
    for l in range(6):
        y = .25 + l * .22
        dbox(k, (.5, .015, .42), (0, y, 0), "T_IK_Steel", .004, 1)
        for a in range(6):
            ball(k, (-.16 + (a % 3) * .16, y + .03, -.1 + (a // 3) * .2), (.1, .05, .1), "C_F4E6C8" if l % 2 else "T_IK_Crust", 8, 5)


def padaria(m):
    sector_shell(m, "padaria", "T_IK_Brick", "T_IK_WoodLight", "T_IK_WoodLight", icon=icon_bread)
    serving_case(m, "padaria", "T_IK_WoodLight", "T_IK_WoodLight", bumper=GOLD)
    side_closures(m, "T_IK_WoodLight")
    curved_bench(m, -.95, .95, "T_IK_WoodLight", "T_IK_ButcherBlock")
    # Deck oven on the right corner, spiral mixer on the left, proofing rack beside the gate.
    x, z, yaw = wall_at(1.28, .36)
    deck_oven(Local(m, (x, 0, z), yaw - 14))
    x, z, yaw = wall_at(-1.3, .4)
    spiral_mixer(Local(m, (x, 0, z), yaw + 16), m.anim("Anim Spin"))
    # Bench: bread slicer, floured board with loaves, croissant tray, rolling pin.
    x, z, yaw = wall_at(-.62, .22)
    bread_slicer(Local(m, (x, .94, z), yaw))
    k = Local(m, wall_at(0, .22)[:1] + (.94,) + wall_at(0, .22)[1:2], 0)
    dbox(k, (.5, .025, .28), (0, .0125, 0), "T_IK_WoodLight", .008)
    for i in range(10):
        ball(k, (-.2 + (i * .047) % .4, .027, -.1 + (i * .061) % .2), (.05, .004, .04), "C_F7F2E6", 6, 3)
    bread_loaf(k, (-.08, .07, 0), (.26, .11, .15), -8)
    bread_loaf(k, (.13, .065, .03), (.2, .1, .13), 14)
    cyl(k, .03, .32, (-.18, .06, -.12), "T_IK_WoodLight", 12, roll=90)
    x, z, yaw = wall_at(.62, .22)
    k = Local(m, (x, .94, z), yaw)
    dbox(k, (.36, .015, .26), (0, .0075, 0), "T_IK_Steel", .005)
    for i in range(6):
        croissant(k, (-.11 + (i % 3) * .11, .015, -.06 + (i // 3) * .12), 1.0, 90)
    # Curved wall shelves with baskets of bread, baguettes standing in a tall basket.
    for y in (1.34, 1.72):
        curved_shelf(m, -1.0, 1.0, y, "T_IK_WoodLight", .26, "C_" + WOODD)
    for j, xx in enumerate((-.75, -.35, .05, .45, .8)):
        x, z, yaw = wall_at(xx, .13)
        if j % 2 == 0:
            basket(m, (x, 1.34, z), .1, .08)
            for b in range(3):
                ball(m, (x - .03 + b * .03, 1.4 + (b % 2) * .02, z + (b - 1) * .03), (.08, .05, .06), "T_IK_Crust", 8, 5)
        else:
            bread_loaf(m, (x, 1.39, z), (.24, .1, .13), yaw)
    for j, xx in enumerate((-.8, -.45, -.1, .25, .6)):
        x, z, yaw = wall_at(xx, .13)
        k = Local(m, (x, 1.72, z), yaw)
        for c in range(3):
            croissant(k, (-.06 + c * .06, 0, 0), 1.0, 90) if j % 2 else roll_bun(k, (-.06 + c * .06, 0, 0), 1.0)
    x, z, yaw = wall_at(.95, .16)
    basket(m, (x, .94, z), .09, .22)
    for b in range(5):
        a = b * 1.3
        baguette(m, (x + math.cos(a) * .03, 1.0, z + math.sin(a) * .03), (x + math.cos(a) * .09, 1.55, z + math.sin(a) * .06), .022)
    # Flour sacks, chalkboard easel, cake dome on the service top.
    for s, (fx, fz) in enumerate(((-.95, .9), (-.72, 1.0))):
        ball(m, (fx, .22, fz), (.3, .44, .24), "C_F4EFE4", 12, 8)
        torus(m, .07, .012, (fx, .4, fz), "T_IK_Rope", seg=12, minor=5)
        ball(m, (fx, .46, fz), (.12, .08, .1), "C_F4EFE4", 8, 6)
        text_lite(m, "FARINHA", (fx, .24, fz - .122), .04, "C_" + RED, .006)
    x, z, yaw = wall_at(-.55, .02)
    chalkboard(m, (x, 1.98, z - .01), .5, .26, [("PÃO QUENTINHO", "FFD97A"), ("7H · 11H · 16H", "FBF8F1")], .05)
    x, z, yaw = case_at(CASE_A1 - 22, -.29)
    k = Local(m, (x, 1.0, z), yaw)
    lathe(k, [(0, 0), (.05, 0), (.03, .02), (.025, .08), (.14, .09), (.14, .1), (0, .1)], (0, 0, 0), "C_" + WHITE, 20)
    cake(k, (0, .1, 0), .11, .09, "F4A6C1", False)
    lathe(k, [(.135, 0), (.135, .16), (.12, .22), (.07, .26), (0, .27)], (0, .1, 0), "G_Glass", 20, cap=False)
    fills(m, fill_padaria)


# ------------------------------------------------------------------------------------------- queijaria
def electric_slicer(k):
    dbox(k, (.5, .08, .4), (0, .04, 0), "C_" + WHITE, .03)
    dbox(k, (.16, .3, .16), (-.12, .22, .1), "C_" + WHITE, .05)
    cyl(k, .15, .012, (-.02, .3, -.02), "C_DCE1E6", 28, roll=90)
    torus_arc(k, .16, .014, (-.015, .3, -.02), "C_" + STEEL, 10, 210, roll=90, seg=12, minor=6)
    dbox(k, (.2, .02, .26), (.12, .16, -.04), "T_IK_Steel", .006, roll=-10)
    dbox(k, (.1, .14, .22), (.12, .24, -.04), "C_F4A6C1", .02)
    bar(k, (.22, .2, -.04), (.28, .32, -.04), .01, "C_" + STEEL, 6)
    ball(k, (.28, .33, -.04), (.035, .035, .035), "C_" + DARK)
    dbox(k, (.1, .06, .03), (-.18, .1, -.2), "C_" + NAVY, .01)
    cyl(k, .015, .01, (-.2, .1, -.22), "C_27AE60", 8, pitch=-90)


def parmesan_stand(k):
    """Round wooden stand with a split giant parmesan wheel and almond knives (local)."""
    lathe(k, [(0, 0), (.28, 0), (.3, .04), (.1, .08), (.08, .6), (.3, .62), (.32, .66), (0, .66)], (0, 0, 0), "T_IK_WoodDark", 24)
    for half, (a0, a1) in ((1, (-85, 85)), (-1, (95, 265))):
        pts = [(0, 0)] + arc_points(.25, a0, a1, 12)
        prism_t(k, pts, .18, (half * .025, .75, 0), "T_IK_Rind", pitch=90)
        prism_t(k, [(x * .92, y * .92) for x, y in pts], .005, (half * .025, .843, 0), "C_F2D98E", pitch=90)
    for i, a in enumerate((-20, 25)):
        kk = Local(k, (.0, .86, -.05 + i * .1), a)
        prism(kk, [(0, 0), (.06, -.03), (.12, 0), (.06, .02)], .006, (0, 0, 0), "C_DCE1E6", pitch=90)
        bar(kk, (0, 0, 0), (-.1, .03, 0), .012, "T_IK_WoodDark", 6)
    text_lite(k, "PARMESÃO 24 MESES", (0, .64, -.33), .032, "C_" + GOLDL, .004)


def wine_rack(k, w=.5, h=1.0):
    dbox(k, (w, h, .3), (0, h / 2, 0), "T_IK_WoodDark", .015)
    rows, cols = 5, 4
    for r in range(rows):
        for c in range(cols):
            x = -w / 2 + .08 + c * (w - .16) / (cols - 1)
            y = .12 + r * (h - .2) / (rows - 1)
            cyl(k, .038, .02, (x, y, -.16), "C_" + ("4A2A2E" if (r + c) % 3 else "2F4A2A"), 10, pitch=-90)
            cyl(k, .014, .02, (x, y, -.175), "C_" + GOLD if (r * c) % 2 else "C_" + RED, 8, pitch=-90)


def hanging_salami(m, x, z, top, n=3):
    for i in range(n):
        L = .28 + .06 * (i % 2)
        xx = x + i * .09
        bar(m, (xx, top, z), (xx, top - .06, z), .004, "T_IK_Rope", 4)
        lathe(m, [(0, 0), (.022, .02), (.032, .06), (.032, L - .06), (.02, L - .02), (0, L)], (xx, top - .06 - L, z), "C_8E2240", 10)
        for t in (.3, .6):
            torus(m, .033, .004, (xx, top - .06 - L + L * t, z), "T_IK_Rope", seg=10, minor=4)


def queijaria(m):
    sector_shell(m, "queijaria", "T_IK_Plaster", "T_IK_WoodDark", "T_IK_WoodDark", icon=icon_cheese)
    serving_case(m, "queijaria", "T_IK_WoodDark", "T_IK_WoodLight")
    side_closures(m, "T_IK_WoodDark")
    curved_bench(m, -.95, .95, "T_IK_WoodDark", "T_IK_ButcherBlock")
    # Aging shelves loaded with wheels along the whole curved wall.
    for y in (1.3, 1.64, 1.98):
        curved_shelf(m, -1.05, 1.05, y, "T_IK_WoodDark", .27, "C_3E2618")
    for r, y in enumerate((1.3, 1.64, 1.98)):
        for j in range(7):
            xx = -.92 + j * .3 + (r % 2) * .08
            if xx > .95:
                continue
            x, z, _ = wall_at(xx, .13)
            rr, h = .1 + ((j + r) % 3) * .015, .07 + ((j * 7 + r) % 3) * .015
            cheese_wheel(m, (x, y, z), rr, h, cut=(j == 3 and r == 1))
            if (j + r) % 4 == 0 and r < 2:
                cheese_wheel(m, (x, y + h, z), rr * .85, h * .9)
    # Deli slicer (classic flywheel), electric slicer, parmesan stand, wine rack, hanging provolone and salami.
    x, z, yaw = wall_at(-.55, .22)
    slicer(Local(m, (x, 0, z), yaw), 0, 0)
    x, z, yaw = wall_at(.5, .22)
    electric_slicer(Local(m, (x, .94, z), yaw))
    x, z, yaw = wall_at(.02, .2)
    k = Local(m, (x, .94, z), yaw)
    cyl(k, .12, .015, (0, 0, 0), "C_" + WHITE, 20, .005)
    for i in range(7):
        dbox(k, (.1, .004, .07), (-.06 + i * .02, .018 + i * .003, 0), "C_F4A6C1" if i % 2 else "T_IK_Cheese", .002, 1, yaw=i * 12, roll=-8)
    x, z, yaw = wall_at(-1.3, .42)
    parmesan_stand(Local(m, (x, 0, z), yaw + 18))
    x, z, yaw = wall_at(1.3, .2)
    wine_rack(Local(m, (x, 0, z), yaw - 16), .56, 1.1)
    x, z, yaw = wall_at(1.3, .2)
    k = Local(m, (x, 1.1, z), yaw - 16)
    for i in range(3):
        lathe(k, [(0, 0), (.035, 0), (.035, .2), (.014, .26), (.014, .32), (.017, .33), (0, .33)], (-.15 + i * .15, 0, 0), "C_4A2A2E" if i != 1 else "C_2F4A2A", 12)
        cyl(k, .036, .07, (-.15 + i * .15, .08, 0), "C_" + CREAM, 12)
    for xx, top in ((-.95, 2.28), (.72, 2.28)):
        x, z, yaw = wall_at(xx, .35)
        bar(m, (x - .2, top, z), (x + .3, top, z), .012, "T_IK_WoodDark", 8)
    x, z, _ = wall_at(.72, .35)
    for i, (L, c) in enumerate(((.36, "C_E6B63A"), (.46, "T_IK_Rind"), (.32, "C_F2C94A"), (.42, "T_IK_Rind"))):
        xx = x - .15 + i * .13
        bar(m, (xx, 2.28, z), (xx, 2.2, z), .005, "T_IK_Rope", 5)
        lathe(m, [(0, 0), (.055, .02), (.075, L * .25), (.07, L * .55), (.04, L * .82), (.018, L * .95), (0, L)], (xx, 2.2 - L, z), c, 14)
        for t in (.35, .62):
            torus(m, .07 if t < .5 else .055, .007, (xx, 2.2 - L + L * t, z), "T_IK_Rope", seg=12, minor=4)
    x, z, _ = wall_at(-.95, .35)
    hanging_salami(m, x - .12, z, 2.28, 4)
    # Honey jars, grapes, cheese knives and wire cutter on the service top.
    x, z, yaw = case_at(CASE_A0 + 22, -.29)
    k = Local(m, (x, 1.0, z), yaw)
    dbox(k, (.3, .03, .2), (0, .015, 0), "T_IK_Marble", .008)
    prism(k, [(0, 0), (.16, 0), (.16, .06), (0, .1)], .09, (-.06, .03, 0), "T_IK_Cheese", pitch=90)
    cyl(k, .015, .04, (-.13, .03, .08), "C_" + STEEL, 10)
    bar(k, (-.13, .07, .08), (.1, .19, -.02), .008, "C_" + STEEL, 6)
    bar(k, (.1, .19, -.02), (.16, .19, -.05), .014, "T_IK_WoodDark", 8)
    x, z, yaw = case_at(CASE_A1 - 22, -.29)
    k = Local(m, (x, 1.0, z), yaw)
    for i in range(3):
        lathe(k, [(0, 0), (.04, 0), (.045, .07), (.036, .09), (.032, .1), (0, .1)], (-.08 + i * .08, 0, 0), "C_E0A030", 12)
        cyl(k, .036, .02, (-.08 + i * .08, .1, 0), "C_" + ("D74A3C" if i % 2 else "E0B040"), 12, .005)
    fills(m, fill_queijaria)


# ------------------------------------------------------------------------------------------- açougue
def cold_room_door(m, xx):
    """Walk-in cold-room door set in the curved wall: steel leaf, strip curtain window, big latch."""
    x, z, yaw = wall_at(xx, .02)
    k = Local(m, (x, 0, z), yaw)
    dbox(k, (.86, 2.06, .06), (0, 1.03, 0), "C_" + NAVY, .02)
    dbox(k, (.74, 1.96, .05), (0, 1.0, -.03), "T_IK_Steel", .015)
    for y in (.3, .7, 1.1, 1.5):
        dbox(k, (.7, .01, .01), (0, y, -.058), "C_" + STEEL, .003, 1)
    dbox(k, (.3, .36, .01), (0, 1.55, -.058), "C_" + DARK, .005)
    dbox(k, (.26, .32, .01), (0, 1.55, -.062), "G_Glass", .003)
    dbox(k, (.06, .3, .06), (.3, 1.0, -.08), "C_" + STEEL, .015)
    bar(k, (.3, 1.1, -.12), (.18, 1.1, -.12), .018, "C_" + STEEL, 8)
    dbox(k, (.3, .12, .01), (0, 1.9, -.06), "C_" + WHITE, .01)
    text_lite(k, "CÂMARA FRIA", (0, 1.9, -.07), .04, "C_2E86DE", .004)
    dbox(k, (.1, .1, .01), (-.24, 1.3, -.06), "C_" + DARK, .005)
    dbox(k, (.07, .03, .004), (-.24, 1.31, -.066), "E_7BD3F7", .002, 1)


def butcher_block(k):
    """Round end-grain chopping block on three legs, with cleaver and a joint of beef."""
    for a in (90, 210, 330):
        r = math.radians(a)
        bar(k, (math.cos(r) * .2, 0, math.sin(r) * .2), (math.cos(r) * .16, .55, math.sin(r) * .16), .03, "T_IK_WoodDark", 8)
    cyl(k, .3, .34, (0, .55, 0), "T_IK_WoodLight", 24, .03)
    cyl(k, .29, .01, (0, .89, 0), "T_IK_ButcherBlock", 24)
    torus(k, .302, .012, (0, .6, 0), "C_" + DARK, seg=24, minor=5)
    torus(k, .302, .012, (0, .84, 0), "C_" + DARK, seg=24, minor=5)
    ball(k, (-.05, .95, .02), (.28, .12, .2), "T_IK_Meat", 12, 7)
    ball(k, (-.05, .96, .1), (.24, .08, .06), "C_F6E6DA", 8, 5)
    knife(k, (.12, .905, -.1), -30, cleaver=True, length=.32)


def tenderizer(k):
    """Bench steak tenderizer: white body, twin roller slot and a feed chute."""
    dbox(k, (.3, .36, .3), (0, .18, 0), "C_" + WHITE, .04)
    dbox(k, (.16, .12, .16), (0, .42, -.02), "T_IK_Steel", .02)
    dbox(k, (.12, .02, .12), (0, .49, -.02), "C_" + DARK, .005)
    dbox(k, (.18, .04, .06), (0, .08, -.17), "T_IK_Steel", .01)
    cyl(k, .02, .012, (.1, .28, -.155), "C_" + RED, 10, pitch=-90)
    steak(k, (0, .1, -.24), 0, False)


def acougue(m):
    sector_shell(m, "acougue", "T_IK_TileSquare", "T_IK_Checker", "T_IK_Checker", icon=icon_steak, trim=GOLD)
    serving_case(m, "acougue", "T_IK_TileSquare", "C_F4EFE4", frame="D64541")
    side_closures(m, "T_IK_Checker")
    cold_room_door(m, -.05)
    curved_bench(m, -1.0, -.55, "T_IK_Steel", "T_IK_Steel")
    curved_bench(m, .45, 1.0, "T_IK_Steel", "T_IK_Steel")
    # Band saw on the left corner, grinder and tenderizer on the right bench, round butcher block.
    x, z, yaw = wall_at(-1.32, .4)
    band_saw(Local(m, (x, 0, z), yaw + 18), 0, 0)
    x, z, yaw = wall_at(.62, .2)
    meat_grinder(Local(m, (x, 0, z), yaw), 0, 0)
    x, z, yaw = wall_at(.9, .2)
    tenderizer(Local(m, (x, .94, z), yaw - 6))
    butcher_block(Local(m, (1.2, 0, .95), -30))
    x, z, yaw = wall_at(-.78, .22)
    k = Local(m, (x, .94, z), yaw)
    dbox(k, (.4, .06, .28), (0, .03, 0), "T_IK_ButcherBlock", .012)
    steak(k, (-.08, .075, .02), 15)
    steak(k, (.08, .075, -.03), -25, False)
    knife(k, (.05, .065, .1), 170, length=.28)
    # Magnetic knife strip and hook rails with hams, sausage links, ribs.
    for xs, xe in ((-1.0, -.55), (.4, .8)):
        x0, z0, _ = wall_at(xs, .03); x1, z1, _ = wall_at(xe, .03)
        bar(m, (x0, 2.06, z0), (x1, 2.06, z1), .014, "C_" + STEEL, 8)
    for j, xx in enumerate((-.92, -.7)):
        x, z, _ = wall_at(xx, .1)
        bar(m, (x, 2.06, z - .07), (x, 1.98, z - .07), .005, "C_" + STEEL, 5)
        s = 1 - .15 * j
        lathe_s(m, [(0, 0), (.07, .02), (.11, .12), (.1, .24), (.06, .33), (.03, .38), (0, .4)], (x, 1.97 - .42 * s, z - .07), "T_IK_Meat", (s, s, s * .8), 16)
        cyl(m, .02, .08, (x, 1.97 - .03, z - .07), "C_" + WHITE, 10)
    x, z, _ = wall_at(.5, .1)
    px, py = x, 1.98
    for i in range(7):
        ny = py - .08
        nx = x + (.04 if i % 2 == 0 else -.04)
        ball(m, ((px + nx) / 2, (py + ny) / 2, z - .07), (.045, .1, .045), "C_A8543A", 8, 5)
        px, py = nx, ny
    x, z, yaw = wall_at(.68, .1)
    k = Local(m, (x, 1.74, z - .05), yaw)
    dbox(k, (.24, .36, .04), (0, 0, 0), "T_IK_Meat", .015)
    for i in range(6):
        bar(k, (-.12, -.14 + i * .055, -.022), (.12, -.14 + i * .055, -.022), .009, "C_F6E6DA", 6)
    x, z, yaw = wall_at(-.78, .015)
    k = Local(m, (x, 1.36, z), yaw)
    dbox(k, (.44, .05, .025), (0, 0, 0), "C_" + DARK, .01)
    for i in range(5):
        prism(k, [(-.018, 0), (.018, 0), (.012, -.2 + i * .012), (-.004, -.22 + i * .012)], .004, (-.16 + i * .08, -.03, -.015), "C_DCE1E6")
        dbox(k, (.026, .1, .024), (-.16 + i * .08, .04, -.015), "C_" + DARK if i % 2 else "T_IK_WoodDark", .008)
    x, z, yaw = wall_at(.95, .02)
    chalkboard(m, (x, 1.86, z - .01), .34, .4, [("PICANHA", "FBF8F1"), ("ALCATRA", "FFD97A"), ("FRALDINHA", "F4A6C1")], .048)
    # Scale and paper roll on the service top.
    x, z, yaw = case_at(CASE_A0 + 22, -.29)
    digital_scale(Local(m, (x, 1.0, z), yaw), (0, 0, 0))
    x, z, yaw = case_at(CASE_A1 - 22, -.29)
    k = Local(m, (x, 1.0, z), yaw)
    dbox(k, (.3, .02, .12), (0, .01, 0), "C_" + STEEL, .006)
    cyl(k, .055, .24, (-.12, .075, 0), "C_" + WHITE, 14, roll=90)
    for s in (-.13, .13):
        dbox(k, (.01, .08, .06), (s, .05, 0), "C_" + STEEL, .003)
    fills(m, fill_acougue)


# ------------------------------------------------------------------------------------------- peixaria
def flake_ice_machine(k):
    """Floor ice maker with a bin of flake ice and a scoop (local, facing -Z)."""
    dbox(k, (.62, .72, .56), (0, .36, 0), "T_IK_Steel", .03)
    dbox(k, (.5, .2, .04), (0, .52, -.28), "C_" + DARK, .02)
    dbox(k, (.46, .16, .01), (0, .52, -.3), "G_Glass", .005)
    for i in range(9):
        ball(k, (-.18 + i * .045, .48, -.27), (.06, .05, .05), "C_F4FAFD", 6, 4)
    bar(k, (-.2, .66, -.31), (.2, .66, -.31), .012, "C_" + STEEL, 6)
    dbox(k, (.62, .46, .5), (0, .95, .03), "C_" + WHITE, .04)
    for i in range(6):
        dbox(k, (.4, .012, .01), (0, .85 + i * .03, -.225), "C_" + DARK, .003, 1)
    dbox(k, (.14, .06, .01), (.18, 1.1, -.225), "C_" + DARK, .005)
    dbox(k, (.1, .025, .004), (.18, 1.1, -.23), "E_7BD3F7", .002, 1)
    text_lite(k, "GELO", (-.1, 1.1, -.228), .05, "C_2E86DE", .006)
    for x in (-.26, .26):
        for z in (-.22, .22):
            cyl(k, .025, .04, (x, -.0, z), "C_" + DARK, 8)


def fish_crate(k, cols):
    """Wooden crate of fish on ice."""
    for part, size, off in ((("b"), (.5, .03, .34), (0, .015, 0)), ("f", (.5, .12, .02), (0, .07, -.16)), ("k", (.5, .12, .02), (0, .07, .16)),
                            ("l", (.02, .12, .34), (-.24, .07, 0)), ("r", (.02, .12, .34), (.24, .07, 0))):
        dbox(k, size, off, "T_IK_WoodLight", .004)
    for i in range(8):
        ball(k, (-.2 + (i % 4) * .13, .05, -.08 + (i // 4) * .16), (.14, .04, .14), "C_F4FAFD", 6, 4)
    for i, c in enumerate(cols):
        fish(k, (-.2, .09, -.1 + i * .1), .38, 0, True, c[0], c[1])


def peixaria(m):
    sector_shell(m, "peixaria", "T_IK_TileSquare", "T_IK_TileBlue", "T_IK_TileSquare", icon=icon_fish)
    serving_case(m, "peixaria", "T_IK_TileBlue", "C_E8F4FA", frame=WHITE)
    side_closures(m, "T_IK_TileBlue")
    curved_bench(m, -.98, -.05, "T_IK_Steel", "T_IK_Steel")
    curved_bench(m, .05, .98, "T_IK_Steel", "T_IK_Steel")
    # Fish-cleaning sink and board on the left bench.
    x, z, yaw = wall_at(-.78, .22)
    k = Local(m, (x, .94, z), yaw)
    dbox(k, (.4, .012, .28), (0, .005, 0), "C_8FA3AE", .004, 1)
    for dz in (-.14, .14):
        dbox(k, (.42, .025, .02), (0, .012, dz), "C_" + STEEL, .006)
    for dx in (-.2, .2):
        dbox(k, (.02, .025, .3), (dx, .012, 0), "C_" + STEEL, .006)
    cyl(k, .02, .008, (0, .006, 0), "C_" + DARK, 10)
    bar(k, (0, 0, .17), (0, .34, .17), .014, "C_" + STEEL, 8)
    torus_arc(k, .07, .013, (0, .34, .1), "C_" + STEEL, 0, 180, roll=90, seg=8, minor=6)
    bar(k, (0, .34, .03), (0, .26, .03), .012, "C_" + STEEL, 8)
    for dx in (-.07, .07):
        cyl(k, .02, .03, (dx, 0, .17), "C_" + STEEL, 10)
        bar(k, (dx, .05, .17), (dx * 1.5, .05, .17), .008, "C_" + (BLUE if dx > 0 else RED), 6)
    x, z, yaw = wall_at(-.3, .22)
    k = Local(m, (x, .94, z), yaw)
    dbox(k, (.6, .05, .32), (0, .025, 0), "T_IK_ButcherBlock", .012)
    fish(k, (-.24, .075, -.02), .46, -6, True)
    knife(k, (.12, .06, .11), 170, length=.28, handle="C_2E86DE")
    for a in range(2):
        dbox(k, (.14, .02, .07), (.16 - a * .08, .06, -.06 - a * .03), "C_F28C6A", .008, yaw=12 - a * 18)
    # Seafood tank on the right bench, flake-ice machine and fish crates on the floor.
    x, z, yaw = wall_at(.5, .02)
    aquarium(Local(m, (x, 0, z), yaw), -.45, .45, .94, -.38, -.04)
    text_lite(m, "FRUTOS DO MAR", (x, 1.5, z - .02), .045, "C_" + WHITE, .006)
    x, z, yaw = wall_at(1.3, .38)
    flake_ice_machine(Local(m, (x, 0, z), yaw - 16))
    x, z, yaw = wall_at(-1.3, .4)
    k = Local(m, (x, 0, z), yaw + 16)
    fish_crate(k, (("T_IK_FishScale", "C_6F8FA6"), ("C_D74A3C", "C_F28C38"), ("C_8FA3AE", "C_5A7488")))
    fish_crate(Local(k, (.03, .14, .02), 8), (("C_F2C23F", "C_EC862E"), ("T_IK_FishScale", "C_6F8FA6")))
    # Hanging scale, fishing net with floats, lifebuoy, crossed oars.
    x, z, _ = wall_at(0, 0)
    hanging_scale(m, 0, z - .45, 2.2, z)
    x0, z0, _ = wall_at(-1.0, .03)
    x1, z1, _ = wall_at(-.2, .03)
    fish_net(m, -.98, -.18, 1.45, 2.15, (z0 + z1) / 2 + .01)
    x, z, _ = wall_at(-.55, .06)
    lifebuoy(m, (x, 1.8, z))
    x, z, yaw = wall_at(.55, .03)
    k = Local(m, (x, 1.85, z), yaw)
    for s in (-1, 1):
        kk = Local(k, (0, 0, 0), 0, 0, s * 35)
        bar(kk, (0, -.4, 0), (0, .35, 0), .014, "T_IK_WoodLight", 8)
        dbox(kk, (.1, .22, .015), (0, -.46, 0), "T_IK_WoodLight", .01)
    x, z, yaw = case_at(CASE_A0 + 22, -.29)
    k = Local(m, (x, 1.0, z), yaw)
    dbox(k, (.3, .03, .2), (0, .015, 0), "T_IK_Steel", .008)
    for i in range(7):
        torus_arc(k, .025, .011, (-.1 + (i % 4) * .065, .045, -.04 + (i // 4) * .07), "C_F28C6A", 20, 250, yaw=i * 50, seg=6, minor=6)
    x, z, yaw = case_at(CASE_A1 - 22, -.29)
    digital_scale(Local(m, (x, 1.0, z), yaw), (0, 0, 0), "E_7BD3F7")
    fills(m, fill_peixaria)


BUILDERS["sector-padaria"] = padaria
BUILDERS["sector-queijaria"] = queijaria
BUILDERS["sector-acougue"] = acougue
BUILDERS["sector-peixaria"] = peixaria


# =========================================================================================== detailed side sectors
# Ice-cream parlour, drinks corner and wine cellar: open wall-backed departments (no attendant) that stand against
# the side walls. Local space as the big counters (customers on -Z), footprint x ±1.6, z -0.9..1.5, height 2.95.
# Each carries its stock as "Anim Fill 0..3" (left to right) which Unity empties as the department sells out.
SIDE_W, SIDE_BACK, SIDE_H = 3.2, 1.46, 2.55


def side_shell(m, sid, wall, wains, floor, trim=GOLD, board=NAVY, subtitle=None):
    title, hexc = SECTORS[sid]
    acc = "C_" + hexc
    hw = SIDE_W / 2
    # Floor inlay, back wall with wainscot, chair rail and skirting, short returns at both ends.
    dbox(m, (SIDE_W - .06, .018, 2.3), (0, .009, .3), floor, .004)
    dbox(m, (SIDE_W, .02, .05), (0, .011, -.86), "C_" + trim, .006)
    dbox(m, (SIDE_W, SIDE_H, .12), (0, SIDE_H / 2, SIDE_BACK), wall, .02)
    dbox(m, (SIDE_W - .02, .95, .03), (0, .12 + .95 / 2, SIDE_BACK - .075), wains, .008)
    dbox(m, (SIDE_W, .05, .06), (0, 1.09, SIDE_BACK - .08), "C_" + trim, .012)
    dbox(m, (SIDE_W, .12, .04), (0, .06, SIDE_BACK - .08), "C_" + NAVY, .01)
    for s in (-1, 1):
        x = s * (hw - .07)
        dbox(m, (.14, SIDE_H, 1.0), (x, SIDE_H / 2, SIDE_BACK - .45), wall, .02)
        dbox(m, (.16, .12, 1.02), (x, .06, SIDE_BACK - .45), "C_" + NAVY, .01)
        dbox(m, (.17, .06, 1.04), (x, SIDE_H + .03, SIDE_BACK - .45), "C_" + trim, .012)
        dbox(m, (.06, SIDE_H - .2, .06), (x - s * .02, SIDE_H / 2, SIDE_BACK - .97), acc, .015)
    # Cornice with a cove light, name board with trim and a subtitle plate.
    dbox(m, (SIDE_W + .1, .18, .34), (0, SIDE_H + .09, SIDE_BACK - .1), "C_" + board, .02)
    dbox(m, (SIDE_W + .12, .04, .36), (0, SIDE_H + .2, SIDE_BACK - .1), "C_" + trim, .01)
    dbox(m, (SIDE_W - .3, .02, .06), (0, SIDE_H - .02, SIDE_BACK - .28), "E_FFF4DC", .004)
    rounded_panel(m, 1.96, .42, (0, SIDE_H + .5, SIDE_BACK - .14), "C_" + trim, .05, .08)
    rounded_panel(m, 1.88, .35, (0, SIDE_H + .5, SIDE_BACK - .17), "C_" + board, .05, .07)
    text_mid(m, title, (0, SIDE_H + .5, SIDE_BACK - .21), .21, "C_" + GOLDL, .035)
    if subtitle:
        dbox(m, (1.1, .13, .03), (0, SIDE_H - .14, SIDE_BACK - .3), acc, .01)
        text_lite(m, subtitle, (0, SIDE_H - .14, SIDE_BACK - .32), .07, "C_" + WHITE, .004)
    # Pendant lamps on arms.
    for x in (-.9, .9):
        bar(m, (x, SIDE_H + .05, SIDE_BACK - .2), (x, SIDE_H + .05, .45), .016, "C_" + DARK, 8)
        bar(m, (x, SIDE_H + .05, .45), (x, 2.2, .45), .006, "C_" + DARK, 5)
        lathe(m, [(0, 0), (.15, 0), (.14, .04), (.09, .11), (.03, .15), (0, .16)], (x, 2.04, .45), acc, 16)
        lathe(m, [(0, 0), (.12, 0)], (x, 2.035, .45), "E_FFF4DC", 12)


def bottle(k, base, h=.3, r=.035, body="C_27AE60", cap="C_" + GOLD, label=None, pitch=0, obj="Body", seg=8):
    prof = [(0, 0), (r, 0), (r, h * .6), (r * .5, h * .76), (r * .38, h * .8), (r * .38, h), (0, h)]
    lathe(k, prof, base, body, seg, pitch=pitch, obj=obj)
    x, y, z = base
    if pitch == 0:
        cyl(k, r * .42, h * .1, (x, y + h * .92, z), cap, 6, 0, obj=obj)
        if label:
            cyl(k, r * 1.02, h * .22, (x, y + h * .2, z), label, seg, 0, obj=obj)
    else:
        cyl(k, r * .42, h * .1, (x, y, z - h * .92), cap, 6, 0, pitch=-90, obj=obj)


def can(k, base, r=.033, h=.12, body="C_D74A3C", obj="Body"):
    cyl(k, r, h, base, body, 8, .005, obj=obj)
    cyl(k, r * .85, .006, (base[0], base[1] + h, base[2]), "C_" + STEEL, 8, 0, obj=obj)


# ------------------------------------------------------------------------------------------- sorvetes
GELATO = ["F4A6C1", "8FD3C0", "F2E3C6", "6B3E26", "F2C23F", "B8E6D2", "E86A9E", "C9A2E8", "F7F2E6", "D74A3C", "A7D66B", "F29C6B"]


def gelato_case(m):
    x0, x1, zc = -1.32, 1.32, -.42
    w = x1 - x0
    dbox(m, (w, .8, .76), (0, .4, zc), "T_IK_Terrazzo", .025)
    dbox(m, (w + .02, .1, .78), (0, .05, zc), "C_" + NAVY, .012)
    dbox(m, (w + .02, .05, .03), (0, .78, zc - .38), "C_E86A9E", .008)
    for x in (x0 + .01, x1 - .01):
        dbox(m, (.05, 1.28, .8), (x, .64, zc), "T_IK_Steel", .012)
    dbox(m, (w, .04, .7), (0, .82, zc), "T_IK_Steel", .008)
    # Curved front glass and the flat top the customers look over.
    pts = arc_points(.5, 180, 270, 7, 0, 0)
    for i in range(len(pts) - 1):
        (z0, y0), (z1, y1) = pts[i], pts[i + 1]
        ang = math.degrees(math.atan2(y1 - y0, z1 - z0))
        dbox(m, (w - .06, .012, math.hypot(z1 - z0, y1 - y0) + .004), (0, .82 + .5 + (y0 + y1) / 2, zc + .12 + (z0 + z1) / 2), "G_Glass", .002, pitch=-ang)
    dbox(m, (w - .06, .012, .34), (0, 1.32, zc + .28), "G_Glass", .002)
    dbox(m, (w, .03, .05), (0, 1.33, zc + .45), "T_IK_Steel", .006)
    dbox(m, (w - .1, .012, .03), (0, 1.3, zc + .1), "E_FFF4DC", .003)
    # Twelve tubs of gelato in two rows, heaped and swirled, with a flavour flag each.
    for i in range(12):
        col, row = i % 6, i // 6
        x = x0 + .24 + col * .43
        z = zc - .16 + row * .3
        y = .84 + row * .04
        g = "Anim Fill %d" % min(3, col * 4 // 6)
        dbox(m, (.38, .1, .26), (x, y + .05, z), "T_IK_Steel", .01, obj=g)
        c = GELATO[i]
        ball(m, (x, y + .12, z), (.34, .12, .22), "C_" + c, 10, 5, obj=g)
        ball(m, (x - .06, y + .17, z + .02), (.16, .08, .12), "C_" + c, 8, 4, obj=g)
        for d in range(3):
            ball(m, (x - .1 + d * .1, y + .16, z - .05 + (d % 2) * .06), (.03, .02, .03), "C_" + GELATO[(i + 5 + d) % 12], 5, 3, obj=g)
        bar(m, (x + .12, y + .12, z + .08), (x + .12, y + .28, z + .08), .004, "C_" + WHITE, 4, g)
        dbox(m, (.08, .05, .006), (x + .16, y + .26, z + .08), "C_" + GELATO[(i + 3) % 12], .002, obj=g)


def cone(k, pos, s=1.0, scoops=(), tilt=0):
    x, y, z = pos
    lathe(k, [(0, 0), (.002, 0), (.05 * s, .17 * s), (.056 * s, .19 * s), (0, .19 * s)], (x, y, z), "T_IK_Waffle", 10, pitch=tilt)
    for i, c in enumerate(scoops):
        ball(k, (x, y + (.2 + i * .07) * s, z), (.11 * s, .1 * s, .11 * s), "C_" + c, 10, 6)


def soft_serve(k):
    dbox(k, (.5, .62, .44), (0, .31, 0), "T_IK_Steel", .03)
    dbox(k, (.46, .16, .4), (0, .7, 0), "C_" + WHITE, .03)
    for x, c in ((-.13, "F4A6C1"), (.13, "6B3E26")):
        dbox(k, (.14, .06, .01), (x, .72, -.205), "C_" + c, .005)
        cyl(k, .025, .06, (x, .28, -.18), "C_" + STEEL, 8, .006)
        bar(k, (x, .38, -.2), (x, .5, -.3), .012, "C_" + DARK, 6)
        ball(k, (x, .5, -.3), (.04, .04, .04), "C_" + RED, 8, 5)
    dbox(k, (.4, .02, .2), (0, .1, -.17), "T_IK_Steel", .006)
    dbox(k, (.14, .08, .006), (0, .55, -.221), "E_7ED957", .003)


def sorvetes(m):
    side_shell(m, "sorvetes", "T_IK_TilePink", "T_IK_TileMint", "T_IK_Terrazzo", subtitle="GELATO ARTESANAL")
    gelato_case(m)
    # Back counter: soft-serve machine, milkshake mixers, cups, topping jars and cone stacks.
    dbox(m, (2.9, .9, .52), (0, .45, 1.12), "C_F6D6E1", .03)
    dbox(m, (2.94, .04, .56), (0, .92, 1.12), "T_IK_Marble", .01)
    dbox(m, (2.9, .08, .02), (0, .8, .855), "C_E86A9E", .006)
    soft_serve(Local(m, (1.0, .94, 1.12), 0))
    for i, x in enumerate((.35, .55)):
        dbox(m, (.16, .26, .18), (x, 1.07, 1.2), "C_" + ("F4A6C1" if i else "8FD3C0"), .03)
        lathe(m, [(0, 0), (.05, 0), (.06, .18), (.065, .2)], (x, 1.02, 1.08), "T_IK_Steel", 10, cap=False)
        bar(m, (x, 1.3, 1.08), (x, 1.16, 1.08), .006, "C_" + STEEL, 5)
    for j in range(3):
        for c in range(3 - j):
            lathe(m, [(0, 0), (.04, 0), (.05, .12), (.052, .125)], (-.05 + c * .11 + j * .055, .94 + j * .125, 1.08), "C_" + WHITE, 10, cap=False)
    for i in range(5):
        x = -1.2 + i * .19
        lathe(m, [(0, 0), (.07, 0), (.075, .16), (.05, .18), (.05, .2), (0, .2)], (x, .94, 1.15), "G_Glass", 10)
        ball(m, (x, 1.0, 1.15), (.12, .1, .12), "C_" + GELATO[(i * 5) % 12], 8, 5)
        cyl(m, .052, .03, (x, 1.14, 1.15), "C_" + ("E86A9E" if i % 2 else "8FD3C0"), 10, .005)
    for i in range(2):
        for c in range(6):
            lathe(m, [(0, 0), (.002, 0), (.05, .17), (.056, .19), (0, .19)], (-.35 + i * .12, .94 + .19 + c * .035, 1.2), "T_IK_Waffle", 10, pitch=180)
    # Wall: menu chalkboard, a big decorative cone, shelves of candy jars.
    chalkboard(m, (-.72, 1.74, SIDE_BACK - .08), 1.1, .72, [("GELATO", "FFD97A"), ("1 BOLA  8,00", "FBF8F1"), ("2 BOLAS 14,00", "FBF8F1"), ("CASCÃO  5,00", "FBF8F1"), ("MILK-SHAKE", "F4A6C1")], .07)
    k = Local(m, (.95, 1.36, SIDE_BACK - .14), 0)
    lathe(k, [(0, 0), (.004, 0), (.15, .52), (.17, .56), (0, .56)], (0, 0, 0), "T_IK_Waffle", 14)
    for i, c in enumerate(("F4A6C1", "8FD3C0", "F2E3C6")):
        ball(k, ((i - 1) * .1 * (i != 1), .62 + i * .16, 0), (.32 - i * .04, .26, .3), "C_" + c, 14, 8)
    ball(k, (0, 1.08, 0), (.08, .08, .08), "C_" + RED, 10, 6)
    bar(k, (0, 1.1, 0), (.04, 1.2, 0), .006, "C_2F6F2C", 4)
    for y in (1.5, 1.86):
        dbox(m, (.9, .03, .2), (.05, y, SIDE_BACK - .18), "C_" + WHITE, .006)
    for i in range(8):
        x = -.3 + (i % 4) * .22; y = 1.515 + (i // 4) * .36
        lathe(m, [(0, 0), (.06, 0), (.065, .14), (.045, .17), (0, .17)], (x, y, SIDE_BACK - .18), "G_Glass", 10)
        ball(m, (x, y + .05, SIDE_BACK - .18), (.1, .08, .1), "C_" + GELATO[(i * 7) % 12], 6, 4)
    # A popsicle chest freezer at the left return with a frosty sliding lid.
    k = Local(m, (-1.22, 0, .2), 90)
    dbox(k, (.9, .78, .52), (0, .39, 0), "C_" + WHITE, .04)
    dbox(k, (.86, .02, .48), (0, .79, 0), "G_Glass", .005)
    dbox(k, (.9, .06, .02), (0, .74, -.26), "C_8FD3C0", .006)
    for i in range(10):
        dbox(k, (.1, .025, .05), (-.36 + (i % 5) * .18, .7, -.1 + (i // 5) * .2), "C_" + GELATO[i], .006)
    text_lite(k, "PICOLÉ", (0, .5, -.265), .07, "C_E86A9E", .004)


# ------------------------------------------------------------------------------------------- bebidas
def fridge(m, cx, contents, fill):
    w, h, d = .96, 2.12, .68
    z = SIDE_BACK - .08 - d / 2
    # Hollow cabinet: plinth, roof, two sides and a lit back panel, so the stock shows through the glass door.
    dbox(m, (w, .12, d), (cx, .06, z), "C_" + DARK, .02)
    dbox(m, (w, .3, d), (cx, h - .15, z), "C_" + DARK, .02)
    for s in (-1, 1):
        dbox(m, (.05, h, d), (cx + s * (w / 2 - .025), h / 2, z), "C_" + DARK, .012)
    dbox(m, (w, h, .03), (cx, h / 2, z + d / 2 - .015), "C_" + DARK, .006)
    dbox(m, (w - .1, h - .44, .02), (cx, .12 + (h - .44) / 2, z + d / 2 - .04), "E_EAF6FF", .004)
    for s in (-1, 1):
        dbox(m, (.015, h - .5, .015), (cx + s * (w / 2 - .06), .14 + (h - .5) / 2, z - d / 2 + .05), "E_FFFFFF", .003)
    dbox(m, (w - .02, .24, .04), (cx, h - .14, z - d / 2 - .01), "C_27AE60", .01)
    text_lite(m, "GELADO", (cx, h - .14, z - d / 2 - .035), .085, "C_" + WHITE, .004)
    dbox(m, (w - .1, .012, .02), (cx, h - .28, z - d / 2 + .02), "E_FFFFFF", .003)
    for i, y in enumerate((.18, .52, .86, 1.2, 1.54)):
        dbox(m, (w - .1, .02, d - .08), (cx, y, z + .02), "C_C9D2D6", .004)
        dbox(m, (w - .1, .04, .01), (cx, y + .02, z - d / 2 + .06), "C_" + contents[i % len(contents)][2], .003)
        kind, col, _ = contents[i % len(contents)]
        for c in range(6):
            x = cx - w / 2 + .12 + c * (w - .24) / 5
            for r in range(2):
                zz = z - .16 + r * .2
                if kind == "can":
                    can(m, (x, y + .01, zz), .033, .12, "C_" + col, fill)
                else:
                    bottle(m, (x, y + .01, zz), .27, .032, "C_" + col, "C_" + WHITE, None, 0, fill)
    dbox(m, (w - .02, h - .12, .03), (cx, .08 + (h - .12) / 2, z - d / 2 - .02), "G_Glass", .006)
    dbox(m, (w, .04, .05), (cx, .06, z - d / 2 - .02), "C_" + STEEL, .01)
    bar(m, (cx + w / 2 - .09, .7, z - d / 2 - .07), (cx + w / 2 - .09, 1.5, z - d / 2 - .07), .015, "C_" + STEEL, 6)
    for y in (.7, 1.5):
        bar(m, (cx + w / 2 - .09, y, z - d / 2 - .07), (cx + w / 2 - .09, y, z - d / 2 - .03), .01, "C_" + STEEL, 5)


def beer_crate(k, pos, obj, col="D74A3C", tops="8A5A20"):
    x, y, z = pos
    dbox(k, (.4, .26, .3), (x, y + .13, z), "C_" + col, .02, obj=obj)
    dbox(k, (.3, .1, .004), (x, y + .13, z - .152), "C_" + WHITE, .004, obj=obj)
    for c in range(4):
        for r in range(3):
            cyl(k, .018, .06, (x - .15 + c * .1, y + .26, z - .1 + r * .1), "C_" + tops, 6, 0, obj=obj)
            cyl(k, .012, .012, (x - .15 + c * .1, y + .32, z - .1 + r * .1), "C_" + GOLD, 6, 0, obj=obj)


def bebidas(m):
    side_shell(m, "bebidas", "T_IK_Plaster", "T_IK_TileMint", "T_IK_TileSquare", subtitle="SEMPRE GELADAS")
    sets = [
        [("can", "D74A3C", "D74A3C"), ("bottle", "EC862E", "EC862E"), ("can", "27AE60", "27AE60"), ("bottle", "3E8FD6", "3E8FD6"), ("can", "2F3A40", "2F3A40")],
        [("bottle", "8A5A20", "E0B040"), ("can", "E0B040", "E0B040"), ("bottle", "2F6F2C", "2F6F2C"), ("can", "C9D2D6", "D74A3C"), ("bottle", "8A5A20", "E0B040")],
        [("bottle", "BFE3F0", "3E8FD6"), ("bottle", "F2A23F", "F2A23F"), ("bottle", "BFE3F0", "3E8FD6"), ("can", "8E6CCF", "8E6CCF"), ("bottle", "C2E07A", "5A9D33")],
    ]
    for i, cx in enumerate((-1.0, 0, 1.0)):
        fridge(m, cx, sets[i], "Anim Fill %d" % i)
    # Floor display: a stack of beer crates, a galvanised ice tub with bottles, wrapped packs of water.
    k = m
    f = "Anim Fill 3"
    for j, (x, y, z) in enumerate(((-1.05, 0, -.45), (-.63, 0, -.45), (-.84, .26, -.45), (-1.05, 0, -.13))):
        beer_crate(k, (x, y, z), f, "D74A3C" if j % 2 == 0 else "27AE60")
    lathe(m, [(0, 0), (.24, 0), (.3, .42), (.32, .45), (.3, .46)], (.62, 0, -.35), "T_IK_Steel", 18, cap=False)
    torus(m, .31, .012, (.62, .3, -.35), "C_" + STEEL, seg=18, minor=4)
    for i in range(14):
        a = i * 2.4
        ball(m, (.62 + math.cos(a) * .17 * (i % 3) / 2, .42, -.35 + math.sin(a) * .17 * (i % 3) / 2), (.1, .06, .1), "C_E8F6FB", 6, 4, obj=f)
    for i in range(7):
        a = i * .9
        bottle(m, (.62 + math.cos(a) * .15, .3, -.35 + math.sin(a) * .15), .28, .03, "C_" + ("8A5A20" if i % 2 else "27AE60"), "C_" + GOLD, None, 0, f)
    for i in range(3):
        for j in range(2 - i // 2):
            x = -.1 + j * .34 + (i // 2) * .17
            dbox(m, (.32, .24, .22), (x, .12 + (i // 2) * .24, -.5 - (i % 2) * .0), "G_Glass", .03, obj=f)
            for b in range(3):
                bottle(m, (x - .1 + b * .1, (i // 2) * .24 + .01, -.5), .22, .03, "C_BFE3F0", "C_3E8FD6", None, 0, f)
            dbox(m, (.3, .06, .005), (x, .12 + (i // 2) * .24, -.612), "C_3E8FD6", .003, obj=f)
    # Kegs on the right return, a price board.
    for j, (x, z) in enumerate(((1.3, .3), (1.3, .72))):
        lathe(m, [(0, 0), (.16, 0), (.18, .04), (.18, .5), (.16, .54), (0, .54)], (x, 0, z), "T_IK_Steel", 14)
        for y in (.12, .42):
            torus(m, .182, .012, (x, y, z), "C_" + DARK, seg=14, minor=4)
        cyl(m, .03, .05, (x, .54, z), "C_" + DARK, 8, 0)
    # Price board on a post by the kegs, facing the aisle.
    dbox(m, (.05, 1.12, .05), (1.3, .56, -.1), "C_" + WOODD, .01)
    dbox(m, (.3, .04, .3), (1.3, .02, -.1), "C_" + WOODD, .01)
    chalkboard(m, (1.3, 1.26, -.13), .46, .34, [("GELADA", "FFD97A"), ("2 POR 9,90", "FBF8F1")], .05)


# ------------------------------------------------------------------------------------------- adega
def lattice(m, cx, y0, w, h, z, s, key, rod=.012):
    x0 = cx - w / 2
    # Diagonal slats both ways, clipped to the rack.
    for direction in (1, -1):
        for kk in range(-int(h / s) - 2, int(w / s) + int(h / s) + 3):
            u = kk * s
            pts = []
            for t in (0.0, h):
                xx = u + (t if direction > 0 else -t)
                pts.append((xx, t))
            (xa, ya), (xb, yb) = pts
            # clip to 0..w in x
            def clip(xa, ya, xb, yb):
                if xa > xb: xa, ya, xb, yb = xb, yb, xa, ya
                if xb < 0 or xa > w: return None
                if xa < 0:
                    ya = ya + (yb - ya) * (0 - xa) / (xb - xa); xa = 0
                if xb > w:
                    yb = ya + (yb - ya) * (w - xa) / (xb - xa); xb = w
                return xa, ya, xb, yb
            c = clip(xa, ya, xb, yb)
            if not c or math.hypot(c[2] - c[0], c[3] - c[1]) < .05: continue
            bar(m, (x0 + c[0], y0 + c[1], z), (x0 + c[2], y0 + c[3], z), rod, key, 5)


def lattice_cells(cx, y0, w, h, s):
    x0 = cx - w / 2
    out = []
    for i in range(-20, 20):
        for j in range(-20, 20):
            u, v = (i + .5) * s, (j + .5) * s
            x, y = (u + v) / 2, (u - v) / 2
            if .07 < x < w - .07 and .07 < y < h - .07:
                out.append((x0 + x, y0 + y))
    return out


def barrel(k, pos, r=.3, L=.7, lying=True, obj="Body"):
    prof = [(0, 0), (r * .88, 0), (r, L * .5), (r * .88, L), (0, L)]
    x, y, z = pos
    if lying:
        lathe(k, prof, (x, y, z + L / 2), "T_IK_Staves", 16, pitch=-90, obj=obj)
        for f in (.08, .92):
            rr = r * (.88 + .12 * math.sin(math.pi * f))
            torus(k, rr + .005, .012, (x, y, z + L / 2 - f * L), "C_" + DARK, pitch=90, seg=16, minor=4, obj=obj)
        cyl(k, r * .8, .01, (x, y, z - L / 2 - .004), "T_IK_WoodDark", 16, 0, pitch=-90, obj=obj)
        cyl(k, .025, .05, (x, y - r * .4, z - L / 2 - .03), "C_" + GOLD, 8, 0, pitch=-90, obj=obj)
    else:
        lathe(k, prof, (x, y, z), "T_IK_Staves", 16, obj=obj)
        for f in (.1, .9):
            rr = r * (.88 + .12 * math.sin(math.pi * f))
            torus(k, rr + .005, .012, (x, y + f * L, z), "C_" + DARK, seg=16, minor=4, obj=obj)


def wine_glass(k, pos, wine=True):
    x, y, z = pos
    lathe(k, [(0, 0), (.035, 0), (.035, .004), (.004, .01), (.004, .09), (.03, .11), (.04, .15), (.035, .19), (0, .19)], (x, y, z), "G_Glass", 10)
    if wine:
        lathe(k, [(0, 0), (.028, .005), (.036, .035), (0, .035)], (x, y + .1, z), "C_7A1E2E", 10)


def adega(m):
    side_shell(m, "adega", "T_IK_Stone", "T_IK_WoodDark", "T_IK_Terracotta", board="5B1A28", subtitle="VINHOS · ESPUMANTES")
    # Two tall diamond racks full of bottles either side of an arched barrel alcove.
    for i, cx in enumerate((-.98, .98)):
        w, h, y0, z = 1.0, 2.1, .2, SIDE_BACK - .24
        dbox(m, (w + .08, h + .08, .3), (cx, y0 + h / 2, z + .02), "T_IK_WoodDark", .015)
        dbox(m, (w, h, .02), (cx, y0 + h / 2, z + .14), "C_2A1810", .004)
        lattice(m, cx, y0, w, h, z - .12, .34, "T_IK_WoodLight", .014)
        f = "Anim Fill %d" % i
        for n, (bx, by) in enumerate(lattice_cells(cx, y0, w, h, .34)):
            for dx in (-.035, .035):
                col = ("3A1520", "4A2A2E", "2F4A2A", "E8D9A0")[(n + (dx > 0)) % 4]
                bottle(m, (bx + dx, by - .02, z + .1), .3, .032, "C_" + col, "C_" + (GOLD if n % 3 else RED), None, -90, f)
    # Alcove: stone arch framing three barrels, a shelf of standing bottles over them.
    arch = [(-.5, 0), (.5, 0), (.5, 1.2)] + [(math.cos(math.radians(a)) * .5, 1.2 + math.sin(math.radians(a)) * .5) for a in range(10, 171, 10)] + [(-.5, 1.2)]
    prism(m, [(x * 1.12, y * 1.04) for x, y in arch], .06, (0, .14, SIDE_BACK - .1), "C_B9A58A")
    prism(m, arch, .02, (0, .14, SIDE_BACK - .13), "C_2A1810")
    for (x, y) in ((-.24, .28), (.24, .28), (0, .8)):
        barrel(m, (x, .14 + y, SIDE_BACK - .5), .26, .62, True)
    dbox(m, (.9, .04, .22), (0, 1.66, SIDE_BACK - .24), "T_IK_WoodDark", .01)
    for j in range(6):
        bottle(m, (-.36 + j * .144, 1.68, SIDE_BACK - .24), .3, .034, "C_" + ("3A1520" if j % 2 else "2F4A2A"), "C_" + GOLD, "C_F4EFE4", 0, "Anim Fill 2")
    # Tasting barrel with glasses, a decanter and a cheese board; wine crates in straw; champagne on ice.
    barrel(m, (-.6, 0, -.4), .3, .86, False)
    cyl(m, .42, .04, (-.6, .86, -.4), "T_IK_WoodDark", 20, .01)
    for j, (x, z) in enumerate(((-.78, -.5), (-.64, -.6), (-.44, -.52))):
        wine_glass(m, (x, .9, z), j != 1)
    lathe(m, [(0, 0), (.09, 0), (.11, .05), (.08, .12), (.03, .16), (.025, .28), (.035, .3), (0, .3)], (-.6, .9, -.28), "G_Glass", 12)
    lathe(m, [(0, 0), (.1, 0), (.1, .09), (0, .09)], (-.6, .905, -.28), "C_5B1A28", 12)
    bottle(m, (-.36, .9, -.3), .3, .034, "C_3A1520", "C_" + RED, "C_F4EFE4", 0, "Anim Fill 2")
    dbox(m, (.3, .025, .18), (-.84, .91, -.3), "T_IK_ButcherBlock", .006)
    for j in range(3):
        cheese_wheel(m, (-.9 + j * .06, .925, -.3), .03, .04)
    f = "Anim Fill 3"
    for j, (x, z, yaw) in enumerate(((.55, -.45, 8), (1.0, -.4, -6))):
        k = Local(m, (x, 0, z), yaw)
        dbox(k, (.42, .24, .32), (0, .12, 0), "T_IK_WoodLight", .012)
        text_lite(k, "VINHO", (0, .13, -.165), .05, "C_5B1A28", .004)
        dbox(k, (.38, .03, .28), (0, .22, 0), "T_IK_Wicker", .006)
        for b in range(4):
            bottle(k, (-.14 + b * .09, .27, .1), .3, .032, "C_" + ("3A1520" if b % 2 else "4A2A2E"), "C_" + GOLD, None, -90, f)
    k = Local(m, (1.3, 0, .35), 0)
    bar(k, (0, 0, 0), (0, .62, 0), .015, "C_" + GOLD, 6)
    for a in range(3):
        bar(k, (0, .02, 0), (math.cos(a * 2.1) * .16, 0, math.sin(a * 2.1) * .16), .012, "C_" + GOLD, 5)
    lathe(k, [(0, 0), (.12, 0), (.14, .22), (.15, .24)], (0, .62, 0), "T_IK_Steel", 14, cap=False)
    for i in range(10):
        ball(k, (math.cos(i) * .08, .82, math.sin(i) * .08), (.06, .04, .06), "C_E8F6FB", 5, 3)
    bottle(k, (.02, .7, 0), .34, .04, "C_2F4A2A", "C_" + GOLD, "C_F4EFE4", 0, f)
    # Cork board with tasting notes and hanging grapes painted on a plaque.
    dbox(m, (.46, .34, .03), (1.28, 1.52, .0), "T_IK_Cork", .01, yaw=-90)
    for j in range(3):
        dbox(m, (.1, .08, .004), (1.262, 1.48 + (j % 2) * .09, -.1 + j * .1), "C_" + ("F4EFE4" if j % 2 else "FFD97A"), .002, yaw=-90)


BUILDERS["sector-sorvetes"] = sorvetes
BUILDERS["sector-bebidas"] = bebidas
BUILDERS["sector-adega"] = adega


# =========================================================================================== plaza café
# The hypermarket's café and social corner ("área de convivência"): a coffee kiosk, a pergola terrace, a
# lounge and a small garden on the yard strip between the shop's back-east corner and the truck yard.
# Local space: x ±3 (+x towards the street), z ±6.5 (+z towards the truck yard), y up; the terrace looks
# south (-z) towards the shop. Placed by CheckoutMarketStagesBuilder.PlazaCafe.
CAFE_W, CAFE_L = 6.0, 13.0
COFFEE = "5A3521"


def bistro_chair(k, pos, yaw, col=TEAL):
    """Café chair; its seat faces local -z. yaw = atan2(dx, dz) of the chair seen from the table."""
    c = Local(k, pos, yaw)
    for dx in (-.16, .16):
        for dz in (-.16, .16):
            bar(c, (dx * 1.1, 0, dz * 1.1), (dx, .44, dz), .013, "C_" + DARK, 6)
    dbox(c, (.42, .045, .42), (0, .46, 0), "C_" + col, .02)
    for dx in (-.16, .16):
        bar(c, (dx, .46, .18), (dx, .88, .23), .013, "C_" + DARK, 6)
    dbox(c, (.4, .22, .03), (0, .76, .215), "C_" + col, .015, pitch=-10)
    bar(c, (-.17, .6, .2), (.17, .6, .2), .01, "C_" + DARK, 5)


def bistro_table(k, pos, top="T_IK_Marble", chairs=2, col=TEAL, cups=True, seed=0):
    x, y, z = pos
    lathe(k, [(0, 0), (.24, 0), (.24, .03), (.05, .07), (.035, .7), (0, .7)], (x, y, z), "C_" + DARK, 16)
    cyl(k, .36, .035, (x, y + .7, z), top, 20, .008)
    lathe(k, [(.36, 0), (.37, .035)], (x, y + .7, z), "C_" + GOLD, 20, cap=False)
    for i in range(chairs):
        a = math.radians(seed * 37 + i * 360 / chairs)
        dx, dz = math.sin(a) * .66, math.cos(a) * .66
        bistro_chair(k, (x + dx, y, z + dz), math.degrees(math.atan2(dx, dz)), col)
    if cups:
        for i in range(min(chairs, 3)):
            a = math.radians(seed * 37 + i * 360 / chairs)
            cx, cz = x + math.sin(a) * .2, z + math.cos(a) * .2
            cyl(k, .06, .008, (cx, y + .735, cz), "C_" + WHITE, 12)
            lathe(k, [(0, 0), (.03, 0), (.04, .07), (.035, .075)], (cx, y + .743, cz), "C_" + WHITE, 10, cap=False)
            cyl(k, .033, .004, (cx, y + .8, cz), "C_" + COFFEE, 10)
        cyl(k, .05, .12, (x, y + .735, z), "G_Glass", 10)
        leaves(k, (x, y + .87, z), 4, .03, .05, "Body", seed + 3, ("F2B03D", "E86A9E"))


def espresso_machine(k):
    dbox(k, (.62, .38, .42), (0, .19, 0), "T_IK_Steel", .04)
    dbox(k, (.64, .06, .44), (0, .41, 0), "C_" + RED, .02)
    for x in (-.16, .16):
        cyl(k, .045, .06, (x, .12, -.2), "C_" + DARK, 10)
        bar(k, (x, .12, -.23), (x, .12, -.32), .012, "C_" + DARK, 6)
        lathe(k, [(0, 0), (.025, 0), (.032, .06), (.03, .065)], (x, .02, -.18), "C_" + WHITE, 10)
    for i in range(3):
        lathe(k, [(0, 0), (.028, 0), (.036, .06), (.034, .065)], (-.18 + i * .18, .44, .02), "C_" + WHITE, 10)
    cyl(k, .018, .16, (.26, .3, -.2), "C_" + STEEL, 8)
    for x in (-.08, .08):
        cyl(k, .035, .012, (x, .3, -.215), "C_" + WHITE, 10, pitch=90)


def coffee_grinder(k):
    dbox(k, (.18, .3, .22), (0, .15, 0), "C_" + DARK, .03)
    lathe(k, [(0, 0), (.07, 0), (.1, .16), (.09, .18), (0, .18)], (0, .3, 0), "G_Glass", 12)
    ball(k, (0, .36, 0), (.14, .08, .14), "C_" + COFFEE, 10, 6)


def pastry_case(k, w=.9):
    dbox(k, (w, .06, .5), (0, .03, 0), "T_IK_WoodDark", .015)
    dbox(k, (w - .04, .34, .46), (0, .23, 0), "G_Glass", .02)
    dbox(k, (w, .02, .5), (0, .41, 0), "T_IK_WoodDark", .01)
    for r, y in enumerate((.08, .24)):
        dbox(k, (w - .08, .01, .4), (0, y, 0), "C_" + STEEL, .003)
        for i in range(4):
            x = -w / 2 + .14 + i * (w - .28) / 3
            if (i + r) % 2:
                croissant(k, (x, y + .03, 0), .9, 20 * i)
            else:
                cake(k, (x, y + .012, 0), .07, .06, ("F4A6C1", "F2E3C6", "6B3E26", "F2C23F")[(i + r * 2) % 4], True)


def pergola_lights(m, a, b, sag, n):
    """String of bulbs hanging between two points."""
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - math.sin(math.pi * t) * sag, a[2] + (b[2] - a[2]) * t))
    for i in range(n):
        bar(m, pts[i], pts[i + 1], .006, "C_" + DARK, 4)
        if 0 < i:
            x, y, z = pts[i]
            ball(m, (x, y - .05, z), (.06, .08, .06), "E_FFE6A8", 8, 5)


def cafe_kiosk(m, z0):
    """Coffee kiosk from z0 (its serving front) to the north end of the plot."""
    w, d, h = 5.0, 2.9, 2.7
    zc = z0 + d / 2
    # Plinth, walls (wood cladding below, painted plaster above), flat roof with a gold-trimmed fascia.
    dbox(m, (w + .1, .16, d + .1), (0, .08, zc), "T_IK_Stone", .02)
    dbox(m, (w, 1.0, d), (0, .66, zc), "T_IK_WoodDark", .02)
    for side in (-1, 1):
        dbox(m, (.2, h - 1.16, d), (side * (w / 2 - .1), 1.16 + (h - 1.16) / 2, zc), "C_" + CREAM, .02)
    dbox(m, (w, h - 1.16, .2), (0, 1.16 + (h - 1.16) / 2, z0 + d - .1), "C_" + CREAM, .02)
    dbox(m, (w - .4, .38, .2), (0, h - .19, z0 + .1), "C_" + CREAM, .02)
    dbox(m, (w + .3, .2, d + .3), (0, h + .1, zc), "C_" + NAVY, .03)
    for y in (h + .2, h):
        for s in (-1, 1):
            dbox(m, (w + .34, .05, .05), (0, y, zc + s * (d / 2 + .15)), "C_" + GOLD, .01)
            dbox(m, (.05, .05, d + .34), (s * (w / 2 + .15), y, zc), "C_" + GOLD, .01)
    dbox(m, (w + .1, .03, d + .1), (0, h + .205, zc), "C_" + DARK, .01)
    # Serving window with a timber ledge, an inside counter with the espresso bar, cups and cakes.
    dbox(m, (w - .3, .06, .38), (0, 1.13, z0 - .08), "T_IK_WoodLight", .02)
    dbox(m, (w - .4, .9, .5), (0, .7, z0 + .55), "T_IK_WoodLight", .02)
    dbox(m, (w - .4, .04, .56), (0, 1.17, z0 + .55), "T_IK_Marble", .01)
    espresso_machine(Local(m, (-.9, 1.19, z0 + .62), 0))
    coffee_grinder(Local(m, (-.25, 1.19, z0 + .7), 0))
    pastry_case(Local(m, (.8, 1.19, z0 + .55), 0))
    for i in range(4):
        lathe(m, [(0, 0), (.035, 0), (.045, .11), (.047, .12)], (-1.95 + i * .1, 1.19, z0 + .7), "C_" + ("F2E3C6" if i % 2 else WHITE), 10, cap=False)
    # Back wall shelves with jars of beans and a menu board over the window.
    for y in (1.5, 1.85):
        dbox(m, (3.4, .04, .24), (0, y, z0 + d - .32), "T_IK_WoodLight", .01)
        for i in range(9):
            x = -1.5 + i * .37
            lathe(m, [(0, 0), (.06, 0), (.065, .16), (.045, .19), (0, .19)], (x, y + .02, z0 + d - .32), "G_Glass", 10)
            ball(m, (x, y + .08, z0 + d - .32), (.1, .1, .1), "C_" + (COFFEE if i % 3 else "8A5A20"), 6, 4)
    chalkboard(m, (0, 2.36, z0 - .02), 2.2, .5, [("CAFÉ 5,00   CAPUCCINO 8,00", "FBF8F1"), ("PÃO DE QUEIJO 4,00   BOLO 7,00", "FFD97A")], .075)
    # Striped awning over the window and a hanging row of lamps under it.
    awning(Local(m, (0, 0, 0)), w + .2, 1.1, 2.12, z0 - 1.0, "S_" + RED, 18)
    for x in (-1.6, -.55, .55, 1.6):
        bar(m, (x, 2.1, z0 - .25), (x, 1.85, z0 - .25), .005, "C_" + DARK, 4)
        lathe(m, [(0, 0), (.1, 0), (.08, .06), (.03, .1), (0, .1)], (x, 1.74, z0 - .25), "C_" + GOLD, 12)
        lathe(m, [(0, 0), (.08, 0)], (x, 1.735, z0 - .25), "E_FFE6A8", 10)
    # Roof sign and a giant coffee cup with steam.
    rounded_panel(m, 3.0, .62, (-.6, h + .62, z0 + .3), "C_" + GOLD, .07, .12)
    rounded_panel(m, 2.9, .52, (-.6, h + .62, z0 + .26), "C_" + NAVY, .07, .1)
    text_mid(m, "CAFÉ DO MERCADO", (-.6, h + .62, z0 + .2), .26, "C_" + GOLDL, .04)
    for x in (-1.9, .7):
        bar(m, (x, h + .2, z0 + .36), (x, h + .35, z0 + .36), .03, "C_" + DARK, 6)
    k = Local(m, (1.6, h + .2, z0 + 1.3), 0)
    cyl(k, .6, .05, (0, 0, 0), "C_" + WHITE, 24, .01)
    lathe(k, [(0, 0), (.32, 0), (.42, .5), (.44, .56), (.4, .56)], (0, .05, 0), "C_" + WHITE, 24, cap=False)
    cyl(k, .41, .02, (0, .55, 0), "C_" + COFFEE, 24)
    torus(k, .16, .045, (.44, .3, 0), "C_" + WHITE, pitch=90, seg=16, minor=6)
    lathe(k, [(.425, 0), (.43, .12)], (0, .22, 0), "C_" + RED, 24, cap=False)
    for i, (x, zz) in enumerate(((-.1, 0), (.08, .05), (0, -.08))):
        for j in range(4):
            ball(k, (x + math.sin(j * 1.3 + i) * .06, .7 + j * .18 + i * .05, zz), (.14 - j * .02, .12 - j * .015, .14 - j * .02), "C_F7F7F2", 8, 5)
    # Side door (staff) on the east wall with a lamp, a vent pipe and some sacks of beans.
    dbox(m, (.04, 2.0, .9), (w / 2 + .01, 1.0 + .16, z0 + 1.8), "C_" + TEAL, .02)
    ball(m, (w / 2 + .05, 1.05, z0 + 1.45), (.05, .05, .05), "C_" + GOLD)
    lathe(m, [(0, 0), (.1, 0), (.07, .12), (0, .14)], (w / 2 + .12, 2.3, z0 + 1.8), "C_" + DARK, 12, pitch=0)
    lathe(m, [(0, 0), (.07, 0)], (w / 2 + .12, 2.295, z0 + 1.8), "E_FFE6A8", 10)
    for i in range(3):
        ball(m, (w / 2 + .3, .28 + (i // 2) * .3, z0 + .5 + (i % 2) * .45), (.4, .34, .3), "T_IK_Wicker", 10, 6)


def lounge(m, pos, yaw):
    k = Local(m, pos, yaw)
    dbox(k, (2.6, .012, 1.9), (0, .006, 0), "T_IK_Stripes", .003)
    # Sofa with its back to the hedge (seat facing -z), two armchairs and a low coffee table.
    dbox(k, (1.9, .38, .72), (0, .24, .6), "T_IK_WoodLight", .04)
    dbox(k, (1.8, .14, .62), (0, .48, .56), "C_" + TEAL, .06)
    dbox(k, (1.9, .5, .16), (0, .62, .92), "T_IK_WoodLight", .04)
    dbox(k, (1.76, .4, .14), (0, .74, .82), "C_" + TEAL, .06, pitch=-8)
    for x in (-.5, .5):
        dbox(k, (.4, .3, .12), (x, .8, .76), "C_" + ("F2C23F" if x < 0 else "E86A9E"), .06, pitch=-12)
    for x in (-.98, .98):
        dbox(k, (.12, .56, .74), (x, .3, .6), "T_IK_WoodLight", .03)
    for x, yaw2 in ((-1.05, 120), (1.05, -120)):
        a = Local(k, (x, 0, -.35), yaw2)
        dbox(a, (.72, .34, .7), (0, .2, 0), "T_IK_Wicker", .05)
        dbox(a, (.62, .12, .6), (0, .42, -.02), "C_" + CREAM, .05)
        dbox(a, (.72, .42, .14), (0, .55, .3), "T_IK_Wicker", .05)
        for s in (-1, 1):
            dbox(a, (.1, .2, .66), (s * .32, .5, 0), "T_IK_Wicker", .04)
    dbox(k, (.9, .06, .5), (0, .36, -.25), "T_IK_WoodDark", .02)
    for x in (-.38, .38):
        for z in (-.45, -.05):
            bar(k, (x, 0, z), (x, .34, z), .02, "C_" + DARK, 6)
    for i in range(2):
        lathe(k, [(0, 0), (.035, 0), (.045, .1), (.047, .11)], (-.15 + i * .3, .39, -.25), "C_" + WHITE, 10, cap=False)
    lathe(k, [(0, 0), (.1, 0), (.12, .12), (.09, .2), (0, .2)], (.12, .39, -.3), "T_IK_Terracotta", 12)
    leaves(k, (.12, .6, -.3), 6, .08, .09, "Body", 4)
    floor_lamp(Local(k, (1.25, 0, .75), 0))


def plaza_cafe(m):
    hw, hl = CAFE_W / 2, CAFE_L / 2
    # Ground: a paved plot with a stone kerb, a timber terrace deck under the pergola.
    dbox(m, (CAFE_W, .06, CAFE_L), (0, .03, 0), "T_IK_Paver", .01)
    for s in (-1, 1):
        dbox(m, (.12, .1, CAFE_L), (s * (hw - .06), .05, 0), "T_IK_Stone", .015)
    dbox(m, (CAFE_W, .1, .12), (0, .05, -hl + .06), "T_IK_Stone", .015)
    deck_z0, deck_z1 = -1.4, 3.35
    dz = deck_z1 - deck_z0
    dbox(m, (CAFE_W - .5, .14, dz), (0, .13, (deck_z0 + deck_z1) / 2), "T_IK_WoodLight", .015)
    dbox(m, (CAFE_W - .46, .06, .1), (0, .12, deck_z0), "T_IK_WoodDark", .01)
    dbox(m, (1.6, .08, .32), (0, .08, deck_z0 - .2), "T_IK_WoodDark", .01)
    # Pergola: six posts, two long beams, cross slats, vines and strings of lights.
    posts = [(x, z) for x in (-hw + .45, hw - .45) for z in (deck_z0 + .2, (deck_z0 + deck_z1) / 2, deck_z1 - .1)]
    for x, z in posts:
        dbox(m, (.16, 2.7, .16), (x, .2 + 1.35, z), "T_IK_WoodDark", .02)
        dbox(m, (.26, .12, .26), (x, .26, z), "T_IK_Stone", .02)
    for x in (-hw + .45, hw - .45):
        dbox(m, (.14, .24, dz + .5), (x, 2.95, (deck_z0 + deck_z1) / 2), "T_IK_WoodDark", .02)
    n = 13
    for i in range(n):
        z = deck_z0 - .1 + i * (dz + .2) / (n - 1)
        dbox(m, (CAFE_W - .4, .1, .07), (0, 3.1, z), "T_IK_WoodLight", .012)
    for x in (-hw + .45, hw - .45):
        for j in range(15):
            z = deck_z0 - .1 + j * (dz + .2) / 14
            ball(m, (x + math.sin(j * 2.1) * .14, 3.12 + (j % 2) * .08, z), (.3, .22, .34), "C_" + (LEAF if j % 3 else LEAFD), 8, 5)
            if j % 3 == 1:
                ball(m, (x + math.sin(j * 2.1) * .14, 2.9, z), (.14, .3, .14), "C_" + LEAFD, 6, 4)
        for z in (deck_z0 + .2, deck_z1 - .1):
            for j in range(5):
                ball(m, (x + math.sin(j) * .08, .6 + j * .45, z - .1), (.18, .2, .14), "C_" + (LEAF if j % 2 else LEAFD), 8, 5)
    for x in (-1.5, 0, 1.5):
        pergola_lights(m, (x, 3.02, deck_z0), (x, 3.02, deck_z1), .28, 8)
    # Terrace furniture: three bistro tables and a long communal table with benches.
    for i, (x, z, c) in enumerate(((-1.55, -.45, TEAL), (1.55, -.45, "E86A9E"), (-1.55, 1.25, "F2B03D"))):
        bistro_table(m, (x, .2, z), chairs=3 if i != 1 else 2, col=c, seed=i)
    k = Local(m, (1.4, .2, 1.85), 90)
    dbox(k, (2.2, .06, .7), (0, .74, 0), "T_IK_WoodLight", .015)
    for x in (-.9, .9):
        dbox(k, (.08, .7, .6), (x, .37, 0), "T_IK_WoodDark", .01)
    for zz in (-.62, .62):
        dbox(k, (2.1, .06, .3), (0, .44, zz), "T_IK_WoodLight", .012)
        for x in (-.85, .85):
            dbox(k, (.06, .42, .24), (x, .21, zz), "T_IK_WoodDark", .01)
    for i in range(5):
        x = -.8 + i * .4
        lathe(k, [(0, 0), (.035, 0), (.045, .1), (.047, .11)], (x, .77, -.18 + (i % 2) * .36), "C_" + WHITE, 10, cap=False)
    for x in (-.5, .5):
        lathe(k, [(0, 0), (.08, 0), (.1, .12), (0, .12)], (x, .77, 0), "T_IK_Terracotta", 10)
        leaves(k, (x, .92, 0), 5, .06, .08, "Body", int(x * 10) + 20, ("F2B03D", LEAF))
    # The kiosk closes the north end, facing the terrace.
    cafe_kiosk(m, hl - 2.95)
    # Lounge corner south of the terrace, by the western hedge; a tree with a ring bench to the east.
    lounge(m, (-1.4, 0, -3.0), 0)
    tree_planter(Local(m, (1.75, 0, -3.1), 0, obj="Body"))
    for a in range(0, 360, 40):
        r = math.radians(a)
        dbox(m, (.36, .05, .2), (1.75 + math.cos(r) * .95, .45, -3.1 + math.sin(r) * .95), "T_IK_WoodLight", .01, yaw=-a + 90)
        bar(m, (1.75 + math.cos(r) * .95, 0, -3.1 + math.sin(r) * .95), (1.75 + math.cos(r) * .95, .43, -3.1 + math.sin(r) * .95), .02, "C_" + DARK, 6)
    # Hedges along the edges (the west side faces the staff walkway, the east side the street), with a gap
    # onto the sidewalk; flower beds and a welcome arch at the south entrance.
    for x, z0, z1 in ((-hw + .3, -4.3, deck_z1 + .1), (hw - .3, -1.9, deck_z1 + .1)):
        L = z1 - z0
        dbox(m, (.5, .4, L), (x, .2, (z0 + z1) / 2), "T_IK_WoodLight", .03)
        dbox(m, (.54, .05, L + .04), (x, .41, (z0 + z1) / 2), "C_" + NAVY, .015)
        for j in range(int(L / .32)):
            ball(m, (x + math.sin(j * 1.7) * .05, .58, z0 + .16 + j * .32), (.46, .38, .4), "C_" + (LEAF if j % 3 else LEAFD), 8, 5)
            if j % 4 == 1:
                ball(m, (x - .1, .74, z0 + .16 + j * .32), (.08, .07, .08), "C_" + ("E86A9E" if j % 8 == 1 else "F2B03D"), 6, 4)
    for s in (-1, 1):
        flower_bed(Local(m, (s * 1.98, 0, -hl + .62), 0, obj="Body"))
    for s in (-1, 1):
        bar(m, (s * .9, 0, -hl + .55), (s * .9, 2.35, -hl + .55), .045, "C_" + NAVY, 10)
        ball(m, (s * .9, 2.4, -hl + .55), (.12, .12, .12), "C_" + GOLD)
        for j in range(6):
            ball(m, (s * (.9 + math.sin(j) * .06), .4 + j * .36, -hl + .45), (.2, .22, .16), "C_" + (LEAF if j % 2 else LEAFD), 8, 5)
    pts = [(math.cos(math.radians(a)) * .9, 2.3 + math.sin(math.radians(a)) * .35) for a in range(0, 181, 15)]
    for i in range(len(pts) - 1):
        bar(m, (pts[i][0], pts[i][1], -hl + .55), (pts[i + 1][0], pts[i + 1][1], -hl + .55), .04, "C_" + NAVY, 8)
    rounded_panel(m, 1.9, .36, (0, 2.34, -hl + .5), "C_" + GOLD, .05, .08)
    rounded_panel(m, 1.82, .3, (0, 2.34, -hl + .47), "C_" + NAVY, .05, .07)
    text_mid(m, "CONVIVÊNCIA", (0, 2.34, -hl + .43), .15, "C_" + GOLDL, .03)
    # Street side: bike rack in the hedge gap's lee, recycling bins, an A-frame sign; lamp posts.
    bike_rack(Local(m, (1.85, 0, -4.72), 0, obj="Body"))
    recycle_bins(Local(m, (-1.85, 0, -4.72), 0, obj="Body"))
    k = Local(m, (hw - .9, 0, -2.4), -60)
    for s in (-1, 1):
        dbox(k, (.62, .9, .04), (0, .45, s * .14), "T_IK_WoodDark", .01, pitch=s * 10)
        dbox(k, (.52, .72, .01), (0, .47, s * .165), "T_IK_Chalk", .003, pitch=s * 10)
    text_lite(k, "CAFÉ", (0, .66, -.18), .09, "C_FFD97A", .004)
    text_lite(k, "FRESQUINHO", (0, .5, -.18), .06, "C_FBF8F1", .004)
    for x, z in ((-hw + .3, -1.75), (hw - .3, deck_z1 + .4)):
        street_lamp(Local(m, (x, 0, z), 0, obj="Body"))


BUILDERS["plaza-cafe"] = plaza_cafe
