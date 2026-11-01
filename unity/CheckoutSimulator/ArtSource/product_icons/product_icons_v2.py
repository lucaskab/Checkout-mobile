"""
product_icons_v2.py  --  Checkout - Supermercado Simulator
The 50 exclusive "evolution reward" products (product-122 .. product-171), rendered in Blender (Cycles) in the
style of product_icons.py (046..062): soft 3D, rounded bevels, glossy highlights, soft shadow, 3/4 top view.
Labels are blank or pictogram only (no text: the game is multilingual).

Usage (Blender, any file open; everything lives in its own scene "ProductIcons_v2"):
    NS = {}; exec(open(ART + "/product_icons/product_icons_v2.py").read(), NS)
    NS["render"](["product-122", ...])      # 1024 px RGBA into product_icons/render/
Then, outside Blender: python3 product_icons_v2_post.py  (crop, re-centre, 512 px, contact sheet).
"""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
ART = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/ArtSource"
OUT = os.path.join(ART, "product_icons", "render")

# the v1 toolkit (scene, lights, camera framing, materials, mesh helpers)
_V1 = {}
exec(open(os.path.join(ART, "product_icons.py")).read(), _V1)
_V1["SCENE_NAME"] = "ProductIcons_v2"
_V1["COLL_NAME"] = "ProductIcons_v2"
_V1["RES"] = 768
_V1["SAMPLES"] = 32
for _k in ("mat", "glass", "film", "box", "sphere", "icosphere", "cylinder", "lathe", "tube", "displace", "label",
           "rnd", "add_obj", "bm_to_mesh", "get_scene", "sub_coll", "clear_coll", "setup_lights_camera",
           "frame_camera", "CURRENT"):
    globals()[_k] = _V1[_k]


# ------------------------------------------------------------------------------------------------ colour / materials
def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)


def M(name, hexc, **kw):
    return mat("P2_" + name, lin(hexc), **kw)


def G(name, hexc="FFFFFF", rough=.04, ior=1.45):
    return glass("P2_" + name, lin(hexc), rough=rough, ior=ior)


def MIX(name, hex1, hex2, kind="voronoi", scale=8.0, lo=.45, hi=.55, rough=.4, coat=.0, sss=.0, w_dist=.0, band=False):
    """Two-colour procedural material: kind voronoi (cells/marbling), noise (veins/speckle), wave (wood grain)."""
    m = bpy.data.materials.get("P2_" + name) or bpy.data.materials.new("P2_" + name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Roughness"].default_value = rough
    try:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (.1, .05, .03)
    except KeyError:
        pass
    co = nt.nodes.new("ShaderNodeTexCoord")
    if kind == "voronoi":
        t = nt.nodes.new("ShaderNodeTexVoronoi")
        t.feature = "DISTANCE_TO_EDGE" if w_dist else "F1"
        src = t.outputs["Distance"]
    elif kind == "wave":
        t = nt.nodes.new("ShaderNodeTexWave")
        t.inputs["Distortion"].default_value = 4
        t.inputs["Detail"].default_value = 3
        src = t.outputs["Fac"]
    else:
        t = nt.nodes.new("ShaderNodeTexNoise")
        t.inputs["Detail"].default_value = 6
        t.inputs["Roughness"].default_value = .6
        src = t.outputs["Fac"]
    t.inputs["Scale"].default_value = scale
    nt.links.new(co.outputs["Object"], t.inputs["Vector"])
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position = lo
    r.color_ramp.elements[1].position = hi
    r.color_ramp.elements[0].color = (*lin(hex1), 1)
    r.color_ramp.elements[1].color = (*lin(hex2), 1)
    if band:                                   # thin veins of hex2 around the mid value, hex1 elsewhere
        r.color_ramp.elements[0].color = (*lin(hex1), 1)
        r.color_ramp.elements[1].color = (*lin(hex1), 1)
        r.color_ramp.elements[0].position = lo
        r.color_ramp.elements[1].position = hi
        e = r.color_ramp.elements.new((lo + hi) / 2)
        e.color = (*lin(hex2), 1)
    nt.links.new(src, r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    return m


# ------------------------------------------------------------------------------------------------ shape helpers
def blob(name, r, loc, scale=(1, 1, 1), m=None, disp=0.0, dscale=.6, rot=(0, 0, 0), segs=32, rings=20, sub=0):
    ob = sphere(name, r, loc, rot, scale, material=m, segs=segs, rings=rings, subsurf=sub)
    if disp:
        displace(ob, disp, dscale)
    return ob


def rb(name, size, loc, m, bevel=.05, rot=(0, 0, 0), seg=4):
    return box(name, size, loc, rot, material=m, bevel=bevel, segments=seg)


def disk(name, r, loc, m, t=.01, rot=(math.pi / 2, 0, 0), segs=32, bevel=.004):
    """Flat round sticker / pictogram, facing -Y by default."""
    return cylinder(name, r, t, loc, rot, material=m, segs=segs, bevel=bevel)


def leaf(name, loc, size=.3, rot=(0, 0, 0), m=None, bend=30):
    ob = sphere(name, .5, loc, rot, (size, size * .42, size * .09), material=m, segs=20, rings=10)
    b = ob.modifiers.new("Bend", "SIMPLE_DEFORM")
    b.deform_method = "BEND"; b.angle = math.radians(bend); b.deform_axis = "Y"
    return ob


def board(name, w, d, loc=(0, 0, 0), t=.1, hexc="B98552", round_=False):
    m = MIX("Wood_" + hexc, hexc, "8A5A32", "wave", 3.0, .3, .9, rough=.55)
    if round_:
        return cylinder(name, w / 2, t, (loc[0], loc[1], loc[2] + t / 2), material=m, segs=48, bevel=.03)
    return rb(name, (w, d, t), (loc[0], loc[1], loc[2] + t / 2), m, .03)


def plate(name, r, loc=(0, 0, 0), hexc="FBF8F1", rim=None):
    m = M("Plate_" + hexc, hexc, rough=.15, coat=.6)
    lathe(name, [(0, 0), (r * .7, 0), (r * .72, .03), (r, .08), (r * 1.0, .1), (r * .96, .1), (r * .7, .05), (0, .05)], loc, m, 48)
    if rim:
        lathe(name + "Rim", [(r * .97, .095), (r * 1.005, .1), (r * 1.005, .107), (r * .97, .104)], loc, M("Rim_" + rim, rim, rough=.25, metallic=.9), 48)


def bottle_prof(h, r, neck=.32, shoulder=.62, neck_r=.33):
    return [(0, 0), (r * .85, 0), (r, h * .03), (r, h * shoulder), (r * .9, h * (shoulder + .07)), (r * .5, h * (shoulder + .14)),
            (r * neck_r, h * (shoulder + .18)), (r * neck_r, h * .98), (r * (neck_r + .04), h), (0, h)]


def shrink(prof, d):
    return [(max(0, rr - d), z + (d if z == 0 else 0)) for rr, z in prof]


def lathe_band(name, r, z0, z1, m, loc=(0, 0, 0), segs=48):
    return lathe(name, [(r, z0), (r, z1)], loc, m, segs)


def sticker(name, size, loc, m, rot=(0, 0, 0), bevel=.08):
    return label(name, size, loc, rot, m, thick=.012, bevel=bevel)


def cone_pict(name, loc, s, m, rot=(math.pi / 2, 0, 0)):
    return cylinder(name, s, s * .2, loc, rot, material=m, segs=3, bevel=.0)


def straw(name, p0, p1, hexc="E8505B", r=.035):
    m = MIX("Straw_" + hexc, "FBF8F1", hexc, "wave", 6.0, .45, .55, rough=.3)
    return tube(name, [p0, p1], [r, r], 12, m, subsurf=0)


def ice(name, loc, s=.16, seed=0):
    rr = rnd(seed)
    ob = rb(name, (s, s, s), loc, G("Ice", "EAF6FB", .08, 1.31), .03, (rr.uniform(0, .6), rr.uniform(0, .6), rr.uniform(0, 1)))
    return ob


ICONS, BUILDERS, VIEW, FILL = {}, {}, {}, {}


def product(pid, key, view=None, fill=None):
    def deco(fn):
        ICONS["product-%03d" % pid] = key
        BUILDERS[key] = fn
        if view:
            VIEW[key] = view
        if fill:
            FILL[key] = fill
        return fn
    return deco


# ------------------------------------------------------------------------------------------------ build / render
def _device(sc, gpu=False):
    """CPU by default (the Metal path crashed Blender on the first try); gpu=True tries Metal."""
    sc.cycles.device = "CPU"
    if gpu:
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = "GPU"
        except Exception:
            sc.cycles.device = "CPU"


def build(pid):
    sc, coll = get_scene()
    key = ICONS[pid]
    c = sub_coll(coll, "P2_%s_%s" % (pid, key))
    clear_coll(c)
    CURRENT["coll"] = c
    BUILDERS[key]()
    return c


def render(ids, out_dir=OUT, samples=32, gpu=False):
    os.makedirs(out_dir, exist_ok=True)
    sc, coll = get_scene()
    _device(sc, gpu)
    sc.cycles.samples = samples
    cam = bpy.data.objects.get("PI_Cam")
    rig = bpy.data.collections.get("PI_Rig")
    if cam is None or rig is None or rig.name not in coll.children:
        cam = setup_lights_camera(sc, coll)
    sc.camera = cam
    done = []
    for pid in ids:
        key = ICONS[pid]
        c = build(pid)
        for ch in coll.children:
            ch.hide_render = not (ch.name == c.name or ch.name == "PI_Rig")
        frame_camera(sc, cam, c, fill=FILL.get(key, .8), view_dir=VIEW.get(key, (.95, -1.35, .78)))
        sc.render.filepath = os.path.join(out_dir, pid + ".png")
        bpy.ops.render.render(write_still=True, scene=sc.name)
        done.append(sc.render.filepath)
    return done


def save_blend(path=os.path.join(ART, "product_icons", "product_icons_v2.blend")):
    """Writes only the icon scene (and what it uses) to its own .blend."""
    sc = bpy.data.scenes.get("ProductIcons_v2")
    bpy.data.libraries.write(path, {sc}, fake_user=True, compress=True)
    return path


exec(open(os.path.join(ART, "product_icons", "product_icons_v2_items.py")).read(), globals())
