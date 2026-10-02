"""
product_icons.py  --  Checkout - Supermercado Simulator
Procedural 3D product icons (products 046..061), rendered in Blender (Cycles).

Usage inside Blender (Checkout_Workspace.blend open):
    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\product_icons.py").read())
    build_all()                     # builds every icon in scene/collection "ProductIcons_v1"
    render_icons(["product-046"])   # renders 512x512 RGBA to ArtSource/Review/icons_v1/render/
    render_icons(ALL_IDS)

Everything lives in its own scene "ProductIcons_v1" (collection "ProductIcons_v1"),
the rest of the .blend is not touched.  Downscaling to 128x128 is done outside
Blender (PIL, premultiplied Lanczos) -- see bottom of file for the snippet.
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

SCENE_NAME = "ProductIcons_v1"
COLL_NAME = "ProductIcons_v1"
OUT_DIR = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\icons_v1\render"
RES = 512
SAMPLES = 96

ICONS = {
    "product-046": "banana",
    "product-047": "alface",
    "product-048": "batata",
    "product-049": "maca",
    "product-050": "ovos",
    "product-051": "arroz",
    "product-052": "feijao",
    "product-053": "acucar",
    "product-054": "oleo",
    "product-055": "cafe",
    "product-056": "pao_forma",
    "product-057": "frango",
    "product-058": "papel_higienico",
    "product-059": "sabao_po",
    "product-060": "cerveja",
    "product-061": "picole",
    "product-062": "uva",
}
ALL_IDS = list(ICONS.keys())

# --------------------------------------------------------------------------- scene

def get_scene():
    sc = bpy.data.scenes.get(SCENE_NAME)
    if sc is None:
        sc = bpy.data.scenes.new(SCENE_NAME)
    coll = bpy.data.collections.get(COLL_NAME)
    if coll is None:
        coll = bpy.data.collections.new(COLL_NAME)
    if coll.name not in sc.collection.children:
        sc.collection.children.link(coll)
    # render settings
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x = RES
    r.resolution_y = RES
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    r.filter_size = 1.5
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.device = "GPU"
    sc.cycles.max_bounces = 12
    sc.cycles.transparent_max_bounces = 12
    sc.cycles.transmission_bounces = 8
    sc.cycles.film_transparent_glass = True
    sc.cycles.film_transparent_roughness = 0.3
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        for d in prefs.devices:
            d.use = (d.type != "CPU")
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    # world: soft neutral ambient
    w = bpy.data.worlds.get("ProductIcons_World")
    if w is None:
        w = bpy.data.worlds.new("ProductIcons_World")
        w.use_nodes = True
        bg = w.node_tree.nodes["Background"]
        bg.inputs[0].default_value = (0.85, 0.88, 0.95, 1)
        bg.inputs[1].default_value = 0.25
    sc.world = w
    return sc, coll


def sub_coll(parent, name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if c.name not in parent.children:
        parent.children.link(c)
    return c


def clear_coll(c):
    for o in list(c.objects):
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if me is not None and hasattr(me, "users") and me.users == 0:
            try:
                if isinstance(me, bpy.types.Mesh):
                    bpy.data.meshes.remove(me)
            except Exception:
                pass
    for ch in list(c.children):
        clear_coll(ch)
        bpy.data.collections.remove(ch)


LIGHTS = (  # name, position (for a ~2 unit object at origin), energy W, disk size
    ("PI_Key", (-2.4, -3.0, 3.6), 330, 2.6),
    ("PI_Fill", (3.2, -2.6, 1.4), 90, 3.5),
    ("PI_Rim", (1.6, 3.2, 2.8), 140, 2.0),
    ("PI_Under", (0.0, -1.5, -2.5), 25, 3.0),
)
LIGHT_COLORS = {"PI_Key": (1.0, 0.95, 0.86), "PI_Fill": (0.85, 0.9, 1.0), "PI_Rim": (1, 1, 1), "PI_Under": (1, 1, 1)}


def setup_lights_camera(sc, coll):
    rig = sub_coll(coll, "PI_Rig")
    clear_coll(rig)
    def light(name, typ, loc, energy, color=(1, 1, 1), size=2.0):
        ld = bpy.data.lights.new(name, typ)
        ld.energy = energy
        ld.color = color
        if typ == "AREA":
            ld.size = size
            ld.shape = "DISK"
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        rig.objects.link(ob)
        # aim at origin
        d = -Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return ob
    for name, base, energy, size in LIGHTS:
        light(name, "AREA", base, energy, LIGHT_COLORS[name], size)
    cam_d = bpy.data.cameras.new("PI_Cam")
    cam_d.lens = 60
    cam_d.sensor_width = 36
    cam = bpy.data.objects.new("PI_Cam", cam_d)
    rig.objects.link(cam)
    sc.camera = cam
    return cam


def collection_bbox(coll):
    pts = []
    for ob in coll.all_objects:
        if ob.type != "MESH" or ob.hide_render:
            continue
        for c in ob.bound_box:
            pts.append(ob.matrix_world @ Vector(c))
    if not pts:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def frame_camera(sc, cam, coll, fill=0.80, view_dir=(0.95, -1.35, 0.78)):
    """Place camera at three-quarter view so the collection's bbox fills `fill` of the frame."""
    from bpy_extras.object_utils import world_to_camera_view
    sc.view_layers[0].update()
    mn, mx = collection_bbox(coll)
    centre = (mn + mx) * 0.5
    corners = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
    d = Vector(view_dir).normalized()
    dist = (mx - mn).length * 1.8 + 0.5
    cam.data.shift_x = 0
    cam.data.shift_y = 0
    for _ in range(6):
        cam.location = centre + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.view_layers[0].update()
        xs, ys = [], []
        for c in corners:
            p = world_to_camera_view(sc, cam, c)
            xs.append(p.x); ys.append(p.y)
        w = max(xs) - min(xs); h = max(ys) - min(ys)
        ext = max(w, h)
        cx = (max(xs) + min(xs)) * 0.5; cy = (max(ys) + min(ys)) * 0.5
        # centre via shift, then rescale distance
        cam.data.shift_x += (cx - 0.5)
        cam.data.shift_y += (cy - 0.5)
        dist *= ext / fill
    cam.location = centre + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    # bring the lights to the object's scale (they were authored for a ~1 unit object)
    s = max((mx - mn).length, 0.4) / 2.0   # lights were authored for a ~2 unit object
    for name, base, energy, size in LIGHTS:
        ob = bpy.data.objects.get(name)
        if ob:
            ob.location = centre + Vector(base) * s
            ob.rotation_euler = (centre - ob.location).to_track_quat("-Z", "Y").to_euler()
            ob.data.energy = energy * s * s
            ob.data.size = size * s
    sc.view_layers[0].update()


# --------------------------------------------------------------------------- materials

def mat(name, color, rough=0.35, metallic=0.0, spec=0.5, transmission=0.0, alpha=1.0,
        ior=1.45, sss=0.0, coat=0.0, noise=0.0, noise_scale=8.0, emission=0.0, sheen=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    col = (*color[:3], 1.0)
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["IOR"].default_value = ior
    bsdf.inputs["Alpha"].default_value = alpha
    try:
        bsdf.inputs["Specular IOR Level"].default_value = spec
        bsdf.inputs["Transmission Weight"].default_value = transmission
        bsdf.inputs["Subsurface Weight"].default_value = sss
        bsdf.inputs["Subsurface Radius"].default_value = (0.1, 0.05, 0.03)
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Sheen Weight"].default_value = sheen
        if emission:
            bsdf.inputs["Emission Color"].default_value = col
            bsdf.inputs["Emission Strength"].default_value = emission
    except KeyError:
        pass
    if noise > 0:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise_scale
        tex.inputs["Detail"].default_value = 3
        ramp = nt.nodes.new("ShaderNodeMixRGB")
        ramp.blend_type = "MULTIPLY"
        ramp.inputs["Fac"].default_value = noise
        ramp.inputs["Color1"].default_value = col
        nt.links.new(tex.outputs["Color"], ramp.inputs["Color2"])
        # map noise to 0.7..1.3 brightness
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.3
        mr.inputs["From Max"].default_value = 0.7
        mr.inputs["To Min"].default_value = 0.75
        mr.inputs["To Max"].default_value = 1.2
        nt.links.new(tex.outputs["Fac"], mr.inputs["Value"])
        mix2 = nt.nodes.new("ShaderNodeMixRGB")
        mix2.blend_type = "MULTIPLY"
        mix2.inputs["Fac"].default_value = noise
        mix2.inputs["Color1"].default_value = col
        nt.links.new(mr.outputs[0], mix2.inputs["Color2"])
        nt.links.new(mix2.outputs[0], bsdf.inputs["Base Color"])
    if transmission > 0:
        # Cycles glass casts a black shadow without caustics -> let shadow rays pass through
        lp = nt.nodes.new("ShaderNodeLightPath")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs[0])
        nt.links.new(bsdf.outputs[0], mix.inputs[1])
        nt.links.new(tr.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs[0])
    return m


def glass(name, color=(1, 1, 1), rough=0.05, ior=1.45):
    return mat(name, color, rough=rough, transmission=1.0, ior=ior, spec=0.5)


def film(name, color=(0.9, 0.93, 1.0), alpha=0.12, rough=0.2):
    """Thin plastic wrap: glossy highlights, see-through without refraction."""
    return mat(name, color, rough=rough, alpha=alpha, spec=0.25)


# --------------------------------------------------------------------------- mesh helpers

CURRENT = {"coll": None}


def add_obj(name, me, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), material=None, smooth=True, bevel=None,
            subsurf=0):
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    ob.scale = scale
    CURRENT["coll"].objects.link(ob)
    if material is not None:
        me.materials.append(material)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if bevel:
        b = ob.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = 4
        b.limit_method = "ANGLE"
        b.angle_limit = math.radians(40)
        b.harden_normals = True
    if subsurf:
        s = ob.modifiers.new("Subd", "SUBSURF")
        s.levels = subsurf
        s.render_levels = subsurf
    return ob


def bm_to_mesh(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def box(name, size=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0), material=None, bevel=0.04, segments=4, subsurf=0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    me = bm_to_mesh(bm, name)
    ob = add_obj(name, me, loc, rot, material=material, smooth=True, subsurf=subsurf)
    if bevel:
        b = ob.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = segments
        b.harden_normals = True
        b.limit_method = "ANGLE"
    return ob


def sphere(name, radius=0.5, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), material=None, segs=32, rings=16,
           subsurf=0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    me = bm_to_mesh(bm, name)
    return add_obj(name, me, loc, rot, scale, material=material, subsurf=subsurf)


def icosphere(name, radius=0.5, loc=(0, 0, 0), scale=(1, 1, 1), material=None, subdiv=3):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    me = bm_to_mesh(bm, name)
    return add_obj(name, me, loc, scale=scale, material=material)


def cylinder(name, radius=0.5, depth=1.0, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), material=None, segs=32,
             bevel=0.0, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=radius, radius2=radius if r2 is None else r2,
                          depth=depth)
    me = bm_to_mesh(bm, name)
    ob = add_obj(name, me, loc, rot, scale, material=material, bevel=bevel)
    return ob


def lathe(name, profile, loc=(0, 0, 0), material=None, segs=48, smooth=True, scale=(1, 1, 1)):
    """profile: list of (radius, z) from bottom to top. radius 0 at ends closes the shape."""
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=math.pi * 2, steps=segs,
                   use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bm_to_mesh(bm, name)
    return add_obj(name, me, loc, scale=scale, material=material, smooth=smooth)


def tube(name, points, radii, nsides=12, material=None, loc=(0, 0, 0), rot=(0, 0, 0), profile=None, subsurf=1):
    """Sweep a (possibly polygonal) cross-section along a polyline. profile: list of (u,v) unit offsets."""
    if profile is None:
        profile = [(math.cos(2 * math.pi * i / nsides), math.sin(2 * math.pi * i / nsides)) for i in range(nsides)]
    bm = bmesh.new()
    rings = []
    n = len(points)
    for i, p in enumerate(points):
        p = Vector(p)
        if i == 0:
            t = (Vector(points[1]) - p)
        elif i == n - 1:
            t = (p - Vector(points[i - 1]))
        else:
            t = (Vector(points[i + 1]) - Vector(points[i - 1]))
        t.normalize()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        nx = t.cross(up).normalized()
        ny = nx.cross(t).normalized()
        r = radii[i]
        ring = [bm.verts.new(p + (nx * u + ny * v) * r) for u, v in profile]
        rings.append(ring)
    for i in range(n - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(len(profile)):
            bm.faces.new((a[j], a[(j + 1) % len(profile)], b[(j + 1) % len(profile)], b[j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bm_to_mesh(bm, name)
    return add_obj(name, me, loc, rot, material=material, subsurf=subsurf)


def displace(ob, strength=0.05, scale=1.5, noise_basis="BLENDER_ORIGINAL"):
    tex = bpy.data.textures.new(ob.name + "_tex", "CLOUDS")
    tex.noise_scale = scale
    tex.noise_depth = 2
    d = ob.modifiers.new("Displace", "DISPLACE")
    d.texture = tex
    d.strength = strength
    d.mid_level = 0.5
    return d


def label(name, size, loc, rot, material, thick=0.012, bevel=0.01):
    """A thin rounded plate used as an abstract label on packaging."""
    ob = box(name, (size[0], thick, size[1]), loc, rot, material=material, bevel=bevel, segments=3)
    return ob


def rnd(seed):
    return random.Random(seed)


# --------------------------------------------------------------------------- products

def build_banana():
    m_skin = mat("PI_Banana", (0.98, 0.80, 0.14), rough=0.4, noise=0.2, noise_scale=6)
    m_tip = mat("PI_BananaTip", (0.25, 0.14, 0.05), rough=0.6)
    m_stem = mat("PI_BananaStem", (0.55, 0.45, 0.18), rough=0.6)
    # pentagon profile (bananas are ridged)
    prof = [(math.cos(2 * math.pi * i / 5 + 0.3), math.sin(2 * math.pi * i / 5 + 0.3)) for i in range(5)]
    N = 16
    for k, (yoff, zoff, ang) in enumerate(((0.0, 0.0, 0.0), (0.36, -0.06, 0.18), (-0.36, -0.06, -0.18))):
        pts, rad = [], []
        for i in range(N + 1):
            t = i / N
            a = math.radians(-35 + 165 * t)          # arc from stem to tip
            x = 1.15 * math.sin(a)
            z = 0.75 * math.cos(a)
            pts.append(Vector((x, 0.0, z)))
            r = 0.21 * math.sin(math.pi * (0.1 + 0.9 * t)) ** 0.55 + 0.03
            if t < 0.08:
                r = 0.07
            rad.append(r)
        ob = tube(f"Banana_{k}", pts, rad, profile=prof, material=m_skin, subsurf=2)
        ob.location = (0.0, yoff, zoff)
        ob.rotation_euler = (0, 0, ang)
        tip = sphere(f"BananaTip_{k}", 0.05, material=m_tip)
        tip.parent = ob
        tip.location = pts[-1]
    # stem cluster at the top-left
    cylinder("BananaStem", 0.09, 0.3, loc=(-0.72, 0, 0.72), rot=(0, math.radians(-40), 0), material=m_stem, segs=10,
             bevel=0.02)


def build_alface():
    m_in = mat("PI_LettuceIn", (0.80, 0.92, 0.40), rough=0.45, sss=0.2, noise=0.2, noise_scale=5)
    m_out = mat("PI_LettuceOut", (0.28, 0.62, 0.16), rough=0.5, sss=0.15, noise=0.35, noise_scale=4)
    core = icosphere("LettuceCore", 0.55, loc=(0, 0, 0.05), scale=(1, 1, 0.9), material=m_in, subdiv=4)
    displace(core, 0.12, 0.6)
    r = rnd(7)
    for i in range(9):
        a = 2 * math.pi * i / 9 + r.uniform(-0.2, 0.2)
        rad = 0.52
        leaf = icosphere(f"LettuceLeaf_{i}", 0.42, loc=(math.cos(a) * rad, math.sin(a) * rad, r.uniform(-0.15, 0.1)),
                         scale=(1.15, 0.85, 0.42 + r.uniform(0, 0.15)), material=m_out, subdiv=4)
        leaf.rotation_euler = (r.uniform(-0.6, 0.0), r.uniform(-0.2, 0.2), a)
        displace(leaf, 0.14, 0.45)
    for i in range(5):
        a = 2 * math.pi * i / 5 + 0.4
        leaf = icosphere(f"LettuceLeafTop_{i}", 0.36, loc=(math.cos(a) * 0.32, math.sin(a) * 0.32, 0.38),
                         scale=(1.0, 0.8, 0.6), material=m_out, subdiv=4)
        leaf.rotation_euler = (-0.5, 0, a)
        displace(leaf, 0.12, 0.4)


def build_batata():
    m = mat("PI_Potato", (0.70, 0.48, 0.24), rough=0.8, noise=0.45, noise_scale=10)
    r = rnd(3)
    specs = [((0.0, 0.0, 0.0), (1.0, 0.72, 0.62), (0.2, 0.1, 0.5)),
             ((-0.65, 0.55, 0.05), (0.85, 0.62, 0.55), (0.1, -0.2, 2.1)),
             ((0.55, 0.65, 0.42), (0.75, 0.6, 0.52), (0.3, 0.2, 1.0))]
    for i, (loc, sc, rot) in enumerate(specs):
        ob = icosphere(f"Potato_{i}", 0.62, loc=loc, scale=sc, material=m, subdiv=4)
        ob.rotation_euler = rot
        displace(ob, 0.10, 0.9)


def build_maca():
    m = mat("PI_Apple", (0.86, 0.10, 0.08), rough=0.22, coat=0.4, noise=0.12, noise_scale=3)
    m_stem = mat("PI_AppleStem", (0.35, 0.22, 0.10), rough=0.6)
    m_leaf = mat("PI_AppleLeaf", (0.30, 0.65, 0.18), rough=0.45, sss=0.2)
    # apple body: sphere with top/bottom dimples
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=0.62)
    for v in bm.verts:
        z = v.co.z / 0.62
        rxy = math.hypot(v.co.x, v.co.y) / 0.62
        # dimple top & bottom
        dz = -0.16 * math.exp(-(rxy / 0.35) ** 2) if z > 0 else 0.10 * math.exp(-(rxy / 0.3) ** 2)
        # slightly wider shoulders
        w = 1.0 + 0.08 * math.exp(-((z - 0.35) / 0.4) ** 2)
        v.co.x *= w; v.co.y *= w
        v.co.z = v.co.z * 0.95 + dz
    me = bm_to_mesh(bm, "Apple")
    add_obj("Apple", me, material=m)
    cylinder("AppleStem", 0.035, 0.32, loc=(0.02, 0, 0.58), rot=(0.1, 0.2, 0), material=m_stem, segs=10, r2=0.028,
             bevel=0.01)
    # leaf: flattened scaled sphere, bent
    leaf = sphere("AppleLeaf", 0.5, loc=(0.24, 0.02, 0.66), rot=(0.1, -0.35, 0.3), scale=(0.44, 0.17, 0.045),
                  material=m_leaf, segs=24, rings=12)
    bend = leaf.modifiers.new("Bend", "SIMPLE_DEFORM")
    bend.deform_method = "BEND"
    bend.angle = math.radians(40)
    bend.deform_axis = "Y"


def build_ovos():
    m_paper = mat("PI_EggCarton", (0.78, 0.72, 0.60), rough=0.9, noise=0.2, noise_scale=12)
    m_egg = mat("PI_Egg", (0.92, 0.72, 0.50), rough=0.35, sss=0.3)
    base = box("EggBase", (1.5, 1.0, 0.42), loc=(0, 0, 0.21), material=m_paper, bevel=0.06, segments=5)
    # cup rims: a thin raised grid
    for i in range(2):
        box(f"EggDivX_{i}", (1.5, 0.05, 0.1), loc=(0, -0.5 + (i + 0.5) * 1.0 - 0.0, 0.45), material=m_paper,
            bevel=0.02)
    for j in range(2):
        box(f"EggDivY_{j}", (0.05, 1.0, 0.1), loc=(-0.75 + (j + 1) * 0.5, 0, 0.45), material=m_paper, bevel=0.02)
    # lid (open, hinged at back)
    lid = box("EggLid", (1.5, 1.0, 0.4), loc=(0, 0, 0.2), material=m_paper, bevel=0.07, segments=5)
    # pivot at the lid's back-bottom edge (hinge), then swing it open backwards
    lid.data.transform(Matrix.Translation((0, -0.5, 0.2)))
    lid.location = (0, 0.5, 0.42)
    lid.rotation_euler = (math.radians(-105), 0, 0)
    for i in range(3):
        for j in range(2):
            sphere(f"Egg_{i}{j}", 0.21, loc=(-0.5 + i * 0.5, -0.25 + j * 0.5, 0.42), scale=(1, 1, 1.28), material=m_egg,
                   segs=32, rings=20)


def build_arroz():
    m_bag = mat("PI_RiceBag", (0.96, 0.96, 0.95), rough=0.30, coat=0.2)
    m_blue = mat("PI_RiceBlue", (0.08, 0.35, 0.80), rough=0.35)
    m_white = mat("PI_RiceWhite", (0.98, 0.98, 0.98), rough=0.35)
    bag = box("RiceBag", (1.1, 0.45, 1.5), loc=(0, 0, 0.75), material=m_bag, bevel=0.16, segments=8, subsurf=0)
    # pillowy bulge
    bag.scale = (1, 1, 1)
    bend = bag.modifiers.new("Taper", "SIMPLE_DEFORM")
    bend.deform_method = "TAPER"
    bend.factor = -0.08
    bend.deform_axis = "Z"
    # seams top & bottom
    box("RiceSeamTop", (1.0, 0.03, 0.12), loc=(0, 0, 1.54), material=m_bag, bevel=0.012, segments=2)
    box("RiceSeamBot", (1.0, 0.03, 0.10), loc=(0, 0, -0.03), material=m_bag, bevel=0.012, segments=2)
    # label: blue band + white oval
    label("RiceBand", (0.95, 0.52), (0, -0.235, 0.78), (0, 0, 0), m_blue)
    label("RiceOval", (0.6, 0.30), (0, -0.25, 0.78), (0, 0, 0), m_white, bevel=0.14)
    label("RiceStripe", (0.95, 0.07), (0, -0.235, 0.32), (0, 0, 0), m_blue)


def build_feijao():
    m_bag = film("PI_BeanBag", alpha=0.05)
    m_bean = mat("PI_Bean", (0.07, 0.045, 0.05), rough=0.4)
    m_red = mat("PI_BeanRed", (0.80, 0.08, 0.10), rough=0.35)
    m_white = mat("PI_BeanWhite", (0.98, 0.95, 0.90), rough=0.35)
    box("BeanBag", (1.0, 0.5, 1.45), loc=(0, 0, 0.725), material=m_bag, bevel=0.12, segments=6)
    # bean filling: an inner dark block + many small beans on the outside surface of the block
    box("BeanFill", (0.9, 0.4, 1.3), loc=(0, 0, 0.66), material=mat("PI_BeanFill", (0.06, 0.04, 0.045), rough=0.7), bevel=0.1, segments=4)
    r = rnd(11)
    bm = bmesh.new()
    for i in range(260):
        face = r.randrange(4)
        x = r.uniform(-0.42, 0.42); z = r.uniform(0.05, 1.27)
        if face == 0:
            loc = Vector((x, -0.185, z))
        elif face == 1:
            loc = Vector((x, 0.185, z))
        elif face == 2:
            loc = Vector((-0.435, r.uniform(-0.16, 0.16), z))
        else:
            loc = Vector((0.435, r.uniform(-0.16, 0.16), z))
        ret = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.055)
        vs = ret["verts"]
        rot = Matrix.Rotation(r.uniform(0, 3.14), 4, "Z") @ Matrix.Rotation(r.uniform(0, 3.14), 4, "X")
        bmesh.ops.scale(bm, vec=(1.0, 0.65, 0.5), verts=vs)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ rot, verts=vs)
    me = bm_to_mesh(bm, "Beans")
    add_obj("Beans", me, material=m_bean)
    label("BeanLabel", (0.78, 0.5), (0, -0.265, 0.95), (0, 0, 0), m_red, thick=0.015, bevel=0.03)
    label("BeanLabelOval", (0.5, 0.22), (0, -0.28, 0.95), (0, 0, 0), m_white, thick=0.012, bevel=0.1)
    box("BeanSeamTop", (0.92, 0.04, 0.1), loc=(0, 0, 1.48), material=m_bag, bevel=0.012, segments=2)


def build_acucar():
    m_paper = mat("PI_SugarPaper", (0.98, 0.97, 0.96), rough=0.85)
    m_pink = mat("PI_SugarPink", (0.96, 0.45, 0.62), rough=0.8)
    m_pink2 = mat("PI_SugarPinkDark", (0.85, 0.20, 0.45), rough=0.8)
    box("SugarBlock", (1.0, 0.62, 1.4), loc=(0, 0, 0.7), material=m_paper, bevel=0.035, segments=3)
    # top fold flaps
    box("SugarFlapTop", (1.0, 0.64, 0.12), loc=(0, 0, 1.44), material=m_paper, bevel=0.02, segments=2)
    box("SugarFlapTop2", (0.5, 0.66, 0.06), loc=(0, 0, 1.51), material=m_paper, bevel=0.015, segments=2)
    # pink bands bottom and top, around the block
    for name, z, h in (("SugarBandBot", 0.26, 0.48), ("SugarBandTop", 1.18, 0.26)):
        box(name, (1.012, 0.632, h), loc=(0, 0, z), material=m_pink, bevel=0.03, segments=3)
    label("SugarOval", (0.62, 0.34), (0, -0.325, 0.78), (0, 0, 0), m_pink2, bevel=0.15)
    label("SugarOvalIn", (0.5, 0.22), (0, -0.333, 0.78), (0, 0, 0), m_paper, bevel=0.1)


def build_oleo():
    m_pet = glass("PI_OilPET", (0.97, 0.98, 0.95), rough=0.03, ior=1.4)
    m_oil = mat("PI_Oil", (1.0, 0.72, 0.06), rough=0.15, sss=0.3, coat=0.5)
    m_cap = mat("PI_OilCap", (0.85, 0.12, 0.10), rough=0.35)
    m_lbl = mat("PI_OilLabel", (0.95, 0.75, 0.12), rough=0.4)
    m_lbl2 = mat("PI_OilLabelGreen", (0.25, 0.60, 0.20), rough=0.4)
    prof = [(0, 0), (0.28, 0), (0.36, 0.03), (0.4, 0.12), (0.40, 0.55), (0.37, 0.65), (0.37, 1.3), (0.40, 1.42),
            (0.40, 1.55), (0.3, 1.78), (0.17, 1.95), (0.17, 2.05), (0, 2.05)]
    lathe("OilBottle", prof, material=m_pet)
    prof_oil = [(0, 0.04), (0.26, 0.04), (0.33, 0.07), (0.37, 0.14), (0.37, 0.55), (0.34, 0.65), (0.34, 1.3),
                (0.37, 1.42), (0.37, 1.5), (0.3, 1.66), (0, 1.66)]
    lathe("Oil", prof_oil, material=m_oil)
    capp = [(0, 2.02), (0.19, 2.02), (0.2, 2.1), (0.2, 2.22), (0.17, 2.26), (0, 2.26)]
    lathe("OilCap", capp, material=m_cap, segs=24)
    # label wrap: a short cylinder ring around the mid section
    prof_l = [(0.372, 0.75), (0.382, 0.75), (0.382, 1.22), (0.372, 1.22)]
    lathe("OilLabel", prof_l, material=m_lbl, segs=48)
    label("OilLabelGreen", (0.36, 0.22), (0, -0.39, 1.0), (0, 0, 0), m_lbl2, thick=0.01, bevel=0.1)


def build_cafe():
    m_pack = mat("PI_CoffeePack", (0.42, 0.06, 0.06), rough=0.25, coat=0.5)
    m_dark = mat("PI_CoffeeBrown", (0.22, 0.10, 0.05), rough=0.3)
    m_gold = mat("PI_CoffeeGold", (0.95, 0.72, 0.25), rough=0.35, metallic=0.3)
    box("CoffeeBrick", (0.9, 0.55, 1.35), loc=(0, 0, 0.675), material=m_pack, bevel=0.06, segments=4)
    box("CoffeeFlapTop", (0.95, 0.12, 0.05), loc=(0, 0, 1.37), material=m_pack, bevel=0.015, segments=2)
    box("CoffeeFlapBot", (0.95, 0.12, 0.05), loc=(0, 0, -0.01), material=m_pack, bevel=0.015, segments=2)
    label("CoffeeBand", (0.85, 0.55), (0, -0.285, 0.9), (0, 0, 0), m_dark, bevel=0.04)
    label("CoffeeOval", (0.55, 0.30), (0, -0.30, 0.9), (0, 0, 0), m_gold, bevel=0.14)
    label("CoffeeStripe", (0.85, 0.05), (0, -0.285, 0.38), (0, 0, 0), m_gold)


def build_pao_forma():
    m_crust = mat("PI_LoafCrust", (0.80, 0.42, 0.14), rough=0.5, noise=0.3, noise_scale=6)
    m_bag = film("PI_LoafBag", alpha=0.08)
    m_lbl = mat("PI_LoafLabel", (0.90, 0.25, 0.20), rough=0.4)
    m_lbl2 = mat("PI_LoafLabelY", (0.98, 0.85, 0.35), rough=0.4)
    # loaf: box with domed top
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(1.7, 0.85, 0.85), verts=bm.verts)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=5, use_grid_fill=True)
    for v in bm.verts:
        if v.co.z > 0.3:
            v.co.z += 0.22 * (1 - (v.co.y / 0.425) ** 2) + 0.03 * (1 - (v.co.x / 0.85) ** 2)
    me = bm_to_mesh(bm, "Loaf")
    loaf = add_obj("Loaf", me, loc=(0, 0, 0.5), material=m_crust, bevel=0.08)
    s = loaf.modifiers.new("Subd", "SUBSURF"); s.levels = 2; s.render_levels = 2
    # slice grooves: thin dark planes
    m_slice = mat("PI_LoafSlice", (0.95, 0.85, 0.65), rough=0.8)
    for i in range(7):
        box(f"LoafSlice_{i}", (0.012, 0.8, 0.95), loc=(-0.72 + i * 0.24, 0, 0.5), material=m_slice, bevel=0.0)
    # bag: larger rounded box, transparent
    box("LoafBag", (2.0, 1.0, 1.25), loc=(0, 0, 0.6), material=m_bag, bevel=0.22, segments=8)
    # twisted end
    cylinder("LoafBagEnd", 0.12, 0.3, loc=(1.1, 0, 0.55), rot=(0, math.radians(90), 0), material=m_bag, segs=12,
             bevel=0.03)
    cylinder("LoafTie", 0.08, 0.06, loc=(1.12, 0, 0.55), rot=(0, math.radians(90), 0), material=m_lbl, segs=12)
    label("LoafLabel", (0.7, 0.45), (-0.2, -0.515, 0.75), (0, 0, 0), m_lbl, bevel=0.06)
    label("LoafLabelOval", (0.45, 0.22), (-0.2, -0.53, 0.75), (0, 0, 0), m_lbl2, bevel=0.1)


def build_frango():
    m_tray = mat("PI_Tray", (0.97, 0.78, 0.28), rough=0.5)
    m_skin = mat("PI_ChickenSkin", (0.82, 0.48, 0.32), rough=0.4, sss=0.05, noise=0.2, noise_scale=8)
    m_film = film("PI_Film", alpha=0.05)
    m_lbl = mat("PI_TrayLabel", (0.95, 0.85, 0.30), rough=0.4)
    tray = box("Tray", (1.8, 1.3, 0.22), loc=(0, 0, 0.11), material=m_tray, bevel=0.08, segments=5)
    box("TrayRim", (1.9, 1.4, 0.05), loc=(0, 0, 0.21), material=m_tray, bevel=0.02, segments=3)
    # chicken body
    body = icosphere("ChickenBody", 0.5, loc=(0.0, 0.05, 0.52), scale=(1.25, 0.95, 0.72), material=m_skin, subdiv=4)
    displace(body, 0.03, 0.8)
    # drumsticks (two legs tucked)
    for k, sgn in enumerate((-1, 1)):
        pts = [Vector((0.25, sgn * 0.25, 0.45)), Vector((0.55, sgn * 0.33, 0.48)), Vector((0.8, sgn * 0.30, 0.44))]
        tube(f"Leg_{k}", pts, [0.17, 0.14, 0.09], nsides=12, material=m_skin, subsurf=2)
        sphere(f"LegKnob_{k}", 0.09, loc=(0.82, sgn * 0.30, 0.44), material=m_skin)
    # wings
    for k, sgn in enumerate((-1, 1)):
        sphere(f"Wing_{k}", 0.2, loc=(-0.3, sgn * 0.42, 0.5), scale=(1.3, 0.7, 0.6), material=m_skin)
    # film: cover box
    box("Film", (1.95, 1.45, 0.75), loc=(0, 0, 0.42), material=m_film, bevel=0.3, segments=8)
    label("TrayLabel", (0.5, 0.3), (-0.5, -0.4, 0.82), (math.radians(90), 0, 0), m_lbl, bevel=0.04)


def build_papel_higienico():
    m_roll = mat("PI_TPRoll", (0.98, 0.98, 0.97), rough=0.85, sss=0.1)
    m_core = mat("PI_TPCore", (0.65, 0.50, 0.32), rough=0.8)
    m_wrap = film("PI_TPWrap", alpha=0.12)
    m_lbl = mat("PI_TPLabel", (0.20, 0.55, 0.90), rough=0.4)
    m_lbl2 = mat("PI_TPLabelW", (0.98, 0.98, 0.98), rough=0.4)
    prof = [(0.17, 0), (0.5, 0), (0.5, 1.0), (0.17, 1.0), (0.17, 0.0)]
    prof_core = [(0.0, 0.02), (0.17, 0.02), (0.17, 0.98), (0.0, 0.98)]
    for i, (x, y) in enumerate(((-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5))):
        lathe(f"Roll_{i}", prof, loc=(x, y, 0.0), material=m_roll, segs=48)
        # cardboard core as an inner surface
        bm = bmesh.new()
        prof_in = [(0.165, 0.0), (0.165, 1.0)]
        verts = [bm.verts.new((r, 0, z)) for r, z in prof_in]
        edges = [bm.edges.new((verts[0], verts[1]))]
        bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=math.pi * 2, steps=32,
                       use_merge=True)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            f.normal_flip()
        me = bm_to_mesh(bm, f"RollCore_{i}")
        add_obj(f"RollCore_{i}", me, loc=(x, y, 0), material=m_core)
        # hole bottom filler (dark)
        cylinder(f"RollHole_{i}", 0.16, 0.02, loc=(x, y, 0.5), material=mat("PI_TPDark", (0.25, 0.2, 0.15), rough=1),
                 segs=24)
    box("TPWrap", (2.1, 2.1, 1.12), loc=(0, 0, 0.5), material=m_wrap, bevel=0.14, segments=6)
    label("TPLabel", (0.9, 0.5), (0, -1.065, 0.5), (0, 0, 0), m_lbl, bevel=0.05)
    label("TPLabelOval", (0.6, 0.26), (0, -1.08, 0.5), (0, 0, 0), m_lbl2, bevel=0.12)


def build_sabao_po():
    m_box = mat("PI_SoapBox", (0.08, 0.40, 0.85), rough=0.35, coat=0.3)
    m_or = mat("PI_SoapOrange", (0.98, 0.50, 0.08), rough=0.4)
    m_wh = mat("PI_SoapWhite", (0.98, 0.98, 0.98), rough=0.4)
    m_yl = mat("PI_SoapYellow", (1.0, 0.85, 0.2), rough=0.4)
    box("SoapBox", (1.15, 0.45, 1.45), loc=(0, 0, 0.725), material=m_box, bevel=0.03, segments=3)
    label("SoapSwoosh", (1.0, 0.42), (0, -0.23, 0.95), (0, 0, math.radians(-8)), m_or, bevel=0.2)
    label("SoapOval", (0.62, 0.3), (0, -0.245, 0.98), (0, 0, 0), m_wh, bevel=0.14)
    label("SoapDot", (0.22, 0.22), (0.38, -0.245, 0.35), (0, 0, 0), m_yl, bevel=0.11)
    label("SoapBar", (0.6, 0.1), (-0.2, -0.235, 0.35), (0, 0, 0), m_wh, bevel=0.04)
    # side panel accent
    label("SoapSide", (0.35, 1.3), (-0.585, 0.0, 0.73), (0, 0, math.radians(90)), m_or, bevel=0.03)


def build_cerveja():
    m_glass = mat("PI_BeerGlass", (0.62, 0.34, 0.08), rough=0.03, transmission=1.0, ior=1.5)
    m_beer = mat("PI_Beer", (0.55, 0.28, 0.05), rough=0.2, coat=0.3)
    m_cap = mat("PI_BeerCap", (0.90, 0.70, 0.25), rough=0.3, metallic=0.8)
    m_lbl = mat("PI_BeerLabel", (0.98, 0.96, 0.90), rough=0.5)
    m_lbl2 = mat("PI_BeerLabelGold", (0.90, 0.68, 0.22), rough=0.4, metallic=0.2)
    m_drop = glass("PI_Drop", (1, 1, 1), rough=0.0, ior=1.33)
    prof = [(0, 0), (0.25, 0), (0.33, 0.04), (0.36, 0.15), (0.36, 1.35), (0.33, 1.5), (0.22, 1.72), (0.15, 1.9),
            (0.14, 2.3), (0.15, 2.36), (0, 2.36)]
    lathe("BeerBottle", prof, material=m_glass)
    prof_in = [(0, 0.05), (0.31, 0.05), (0.33, 0.15), (0.33, 1.35), (0.30, 1.5), (0.19, 1.72), (0.12, 1.9),
               (0.11, 2.0), (0, 2.0)]
    lathe("Beer", prof_in, material=m_beer)
    capp = [(0, 2.33), (0.16, 2.33), (0.175, 2.36), (0.175, 2.45), (0.165, 2.47), (0, 2.47)]
    lathe("BeerCap", capp, material=m_cap, segs=24)
    prof_l = [(0.362, 0.42), (0.372, 0.42), (0.372, 1.12), (0.362, 1.12)]
    lathe("BeerLabel", prof_l, material=m_lbl, segs=48)
    label("BeerLabelOval", (0.34, 0.3), (0, -0.38, 0.77), (0, 0, 0), m_lbl2, thick=0.01, bevel=0.14)
    prof_n = [(0.152, 1.95), (0.162, 1.95), (0.162, 2.15), (0.152, 2.15)]
    lathe("BeerNeckLabel", prof_n, material=m_lbl2, segs=32)
    # droplets
    r = rnd(5)
    for i in range(26):
        a = r.uniform(math.radians(170), math.radians(370))
        z = r.uniform(0.1, 1.45)
        rad = 0.362 if 0.42 < z < 1.12 else 0.36
        if z > 1.35:
            rad = 0.36 - (z - 1.35) * 0.2
        d = r.uniform(0.02, 0.045)
        sphere(f"Drop_{i}", d, loc=(math.cos(a) * rad, math.sin(a) * rad, z), scale=(0.55, 1.0, 1.0),
               material=m_drop, segs=12, rings=8)
        ob = bpy.data.objects[f"Drop_{i}"]
        ob.rotation_euler = (0, 0, a)


def build_picole():
    m_ice = mat("PI_Popsicle", (0.95, 0.22, 0.36), rough=0.3, sss=0.25, coat=0.3)
    m_inner = mat("PI_PopsicleIn", (1.0, 0.80, 0.84), rough=0.5, sss=0.3)
    m_stick = mat("PI_Stick", (0.88, 0.72, 0.45), rough=0.7, noise=0.3, noise_scale=20)
    body = box("Popsicle", (0.8, 0.42, 1.6), loc=(0, 0, 1.0), material=m_ice, bevel=0.2, segments=8)
    # bite: boolean sphere at top-right corner
    bite = sphere("Bite", 0.36, loc=(0.4, -0.05, 1.78), scale=(1, 1, 1), material=m_inner, segs=24, rings=16)
    displace(bite, 0.05, 0.3)
    bite.display_type = "WIRE"
    bite.hide_render = True
    bo = body.modifiers.new("Bite", "BOOLEAN")
    bo.operation = "DIFFERENCE"
    bo.object = bite
    bo.solver = "EXACT"
    # inner lighter cream filling revealed by bite: second shell
    inner = box("PopsicleIn", (0.66, 0.30, 1.5), loc=(0, 0, 1.0), material=m_inner, bevel=0.15, segments=6)
    bo2 = inner.modifiers.new("Bite", "BOOLEAN")
    bo2.operation = "DIFFERENCE"
    bo2.object = bite
    bo2.solver = "EXACT"
    # drip
    sphere("Drip", 0.07, loc=(-0.3, -0.215, 0.35), scale=(0.9, 0.5, 1.6), material=m_ice)
    # stick
    cylinder("Stick", 0.1, 0.95, loc=(0, 0, -0.1), scale=(1, 0.42, 1), material=m_stick, segs=16, bevel=0.03)


def build_uva():
    m = mat("PI_Grape", (0.16, 0.03, 0.22), rough=0.32, coat=0.25, noise=0.10, noise_scale=4, sheen=0.35)
    m_stem = mat("PI_GrapeStem", (0.38, 0.30, 0.14), rough=0.65)
    m_leaf = mat("PI_GrapeLeaf", (0.18, 0.45, 0.10), rough=0.45, sss=0.2)
    r = rnd(62)
    # bunch: rows of berries, widest at the top, narrowing to a point
    rows = [(0.62, 7), (0.50, 6), (0.38, 6), (0.18, 5), (-0.02, 4), (-0.22, 3), (-0.42, 2), (-0.60, 1)]
    br = 0.17
    for ri, (z, n) in enumerate(rows):
        ring = 0.07 * n
        for k in range(n):
            a = 2 * math.pi * k / n + ri * 0.5
            x = math.cos(a) * ring + r.uniform(-0.03, 0.03)
            y = math.sin(a) * ring * 0.8 + r.uniform(-0.03, 0.03)
            sphere("Grape%d_%d" % (ri, k), br * r.uniform(0.92, 1.06), loc=(x, y, z), scale=(1, 1, 1.12), material=m,
                   segs=20, rings=12)
    cylinder("GrapeStem", 0.04, 0.4, loc=(0.0, 0.0, 0.88), rot=(0.0, 0.3, 0), material=m_stem, segs=10, r2=0.03,
             bevel=0.01)
    leaf = sphere("GrapeLeaf", 0.5, loc=(0.28, 0.05, 0.92), rot=(0.2, -0.5, 0.4), scale=(0.5, 0.36, 0.04),
                  material=m_leaf, segs=24, rings=12)
    bend = leaf.modifiers.new("Bend", "SIMPLE_DEFORM")
    bend.deform_method = "BEND"
    bend.angle = math.radians(35)
    bend.deform_axis = "Y"


BUILDERS = {
    "banana": build_banana, "alface": build_alface, "batata": build_batata, "maca": build_maca, "ovos": build_ovos,
    "arroz": build_arroz, "feijao": build_feijao, "acucar": build_acucar, "oleo": build_oleo, "cafe": build_cafe,
    "pao_forma": build_pao_forma, "frango": build_frango, "papel_higienico": build_papel_higienico,
    "sabao_po": build_sabao_po, "cerveja": build_cerveja, "picole": build_picole, "uva": build_uva,
}

VIEW_DIRS = {  # per-product tweak of the three-quarter camera direction (x, y, z)
    "banana": (0.25, -1.4, 0.6),
    "alface": (0.9, -1.3, 1.0),
    "batata": (0.8, -1.3, 1.1),
    "ovos": (0.7, -1.3, 1.05),
    "pao_forma": (0.8, -1.35, 0.85),
    "frango": (0.6, -1.3, 1.15),
    "papel_higienico": (0.9, -1.3, 0.9),
    "picole": (0.6, -1.4, 0.55),
    "cerveja": (0.9, -1.4, 0.55),
    "oleo": (0.9, -1.4, 0.55),
}
FILL = {"cerveja": 0.86, "oleo": 0.86, "picole": 0.84, "banana": 0.82}


def build(pid):
    sc, coll = get_scene()
    key = ICONS[pid]
    c = sub_coll(coll, f"PI_{pid}_{key}")
    clear_coll(c)
    CURRENT["coll"] = c
    BUILDERS[key]()
    return c


def build_all():
    for pid in ALL_IDS:
        build(pid)


def render_icons(ids, out_dir=OUT_DIR):
    import os
    os.makedirs(out_dir, exist_ok=True)
    sc, coll = get_scene()
    cam = bpy.data.objects.get("PI_Cam")
    if cam is None or cam.name not in [o.name for o in coll.all_objects]:
        cam = setup_lights_camera(sc, coll)
    sc.camera = cam
    done = []
    for pid in ids:
        key = ICONS[pid]
        name = f"PI_{pid}_{key}"
        c = bpy.data.collections.get(name)
        if c is None:
            c = build(pid)
        # show only this product (and rig)
        for ch in coll.children:
            ch.hide_render = not (ch.name == name or ch.name == "PI_Rig")
            ch.hide_viewport = False
        for vl in sc.view_layers:
            def walk(lc):
                for child in lc.children:
                    child.exclude = False
                    walk(child)
            walk(vl.layer_collection)
        frame_camera(sc, cam, c, fill=FILL.get(key, 0.80), view_dir=VIEW_DIRS.get(key, (0.95, -1.35, 0.78)))
        sc.render.filepath = os.path.join(out_dir, pid + ".png")
        bpy.ops.render.render(write_still=True, scene=sc.name)
        done.append(sc.render.filepath)
    return done


# --------------------------------------------------------------------------- downscale (run OUTSIDE blender)
DOWNSCALE_SNIPPET = r'''
from PIL import Image
import numpy as np
def downscale(src, dst, size=128):
    im = Image.open(src).convert("RGBA")
    a = np.asarray(im).astype(np.float32) / 255.0
    rgb = a[..., :3] * a[..., 3:4]            # premultiply
    pm = np.concatenate([rgb, a[..., 3:4]], axis=-1)
    small = Image.fromarray((pm * 255).round().astype(np.uint8), "RGBA").resize((size, size), Image.LANCZOS)
    s = np.asarray(small).astype(np.float32) / 255.0
    al = np.clip(s[..., 3:4], 1e-4, 1.0)
    out = np.concatenate([np.clip(s[..., :3] / al, 0, 1), s[..., 3:4]], axis=-1)
    out[..., 3][s[..., 3] < 0.004] = 0
    Image.fromarray((out * 255).round().astype(np.uint8), "RGBA").save(dst, optimize=True)
'''
