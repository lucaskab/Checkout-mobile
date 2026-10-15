"""restock_art.py -- Checkout - Supermercado Simulator (Oct 2026)
Fixtures of the REPOR mini-game (CheckoutRestockGame.cs), modelled in 3D and rendered with a PERSPECTIVE camera so the
2D mini-game reads as 3D: you see the shelf tops, the side walls going back, the glass in front.

Per fixture <key> (1600 x 1000, transparent):
  fixture_<key>_back.png    body, interior, shelves (behind the products)
  fixture_<key>_front.png   what stands in front of the products (shelf lips with the price rail, crate fronts, frame)
  fixture_<key>_door<N>.png each glass door / lid alone (fridges and freezers); lanes name the door they sit behind
  fixture_<key>.json        per lane: the product floor quad (fl, fr, bl, br) in normalised image coords (origin
                            bottom-left), pixels-per-metre at the front and back edge, and the product height (m)
The game draws back -> product icons (back rows first, smaller and a bit darker) -> front -> door.

    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\restock\\restock_art.py").read())
    build("fridge"); render("fridge")      # or render_all()
"""
import bpy, bmesh, math, os, json, sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\restock"
OUT = os.path.join(HERE, "render")
GAME = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets\Resources\CheckoutDesktop\Game"
RES = (1600, 1000)
SCENE = "RestockArt"
rad = math.radians

# palette (linear-ish sRGB values as used by the other kits)
TEAL = (0.05, 0.42, 0.40, 1); TEAL_D = (0.02, 0.22, 0.21, 1); TEAL_L = (0.30, 0.66, 0.62, 1)
CREAM = (0.96, 0.90, 0.74, 1); WHITE = (0.93, 0.93, 0.90, 1); ORANGE = (0.93, 0.45, 0.12, 1)
WOOD = (0.62, 0.38, 0.19, 1); WOOD_L = (0.80, 0.58, 0.33, 1); METAL = (0.62, 0.66, 0.66, 1); DARK = (0.10, 0.11, 0.12, 1)
FROST = (0.80, 0.90, 0.96, 1); INTERIOR = (0.95, 0.95, 0.92, 1); PINK = (0.93, 0.52, 0.64, 1)

# ---------------------------------------------------------------- scene / materials
def scene():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = sc
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 64; sc.cycles.use_denoising = True
    try:   # render on the GPU (OptiX on the RTX): a CPU render of the backdrop takes minutes instead of seconds
        prefs = bpy.context.preferences.addons['cycles'].preferences
        types = [t[0] for t in prefs.get_device_types(bpy.context)]
        prefs.compute_device_type = 'OPTIX' if 'OPTIX' in types else ('CUDA' if 'CUDA' in types else 'NONE')
        prefs.get_devices()
        for d in prefs.devices: d.use = d.type != 'CPU'
        sc.cycles.device = 'GPU' if prefs.compute_device_type != 'NONE' else 'CPU'
    except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.film_transparent = True
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    return sc

def clear():
    sc = scene()
    for o in list(sc.collection.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)

_M = {}
def mat(name, rgb, rough=.55, metal=0., emit=0., alpha=1., transmission=0.):
    key = name
    if key in _M and _M[key].name in bpy.data.materials: return _M[key]
    m = bpy.data.materials.get("RA_" + name) or bpy.data.materials.new("RA_" + name)
    m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgb; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit: b.inputs["Emission Color"].default_value = rgb; b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"): m.surface_render_method = 'BLENDED'
    if transmission: b.inputs["Transmission Weight"].default_value = transmission
    _M[key] = m; return m

# ---------------------------------------------------------------- procedural materials (shared with backdrop_art.py)
def _new(name):
    key = "bd4_" + name
    if key in _M and _M[key].name in bpy.data.materials: return _M[key], None
    m = bpy.data.materials.get("RA_" + key) or bpy.data.materials.new("RA_" + key); m.use_nodes = True
    _M[key] = m; return m, m.node_tree

def wood_mat(name, light=(0.80, 0.56, 0.30), dark=(0.52, 0.31, 0.14), scale=1.0, rough=.5, axis="x"):
    """Procedural wood: long wave bands along `axis` with noise distortion and a fine pore bump."""
    m, nt = _new("wood_" + name)
    if nt is None: return m
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 14, 14) if axis == "x" else ((14, 1, 14) if axis == "y" else (14, 14, 1))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'DIAGONAL'
    wv.inputs["Scale"].default_value = 1.2 * scale; wv.inputs["Distortion"].default_value = 6; wv.inputs["Detail"].default_value = 3; wv.inputs["Detail Scale"].default_value = 1.5
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (*dark, 1); ramp.color_ramp.elements[1].color = (*light, 1)
    ramp.color_ramp.elements[0].position = .25; ramp.color_ramp.elements[1].position = .75
    nt.links.new(wv.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = .06
    nt.links.new(wv.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def stripes_mat(name, a, b_, period=.12, axis="x", rough=.8):
    """Cloth stripes along `axis` in WORLD space (so the skirt and its scallops share one pattern), e.g. the cream / teal
    skirt of the crates stand."""
    m, nt = _new("stripes_" + name)
    if nt is None: return m
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord"); geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
    prev = sep.outputs[{"x": "X", "y": "Y", "z": "Z"}[axis]]
    for op, val in (('DIVIDE', period), ('FLOOR', None), ('MODULO', 2), ('ABSOLUTE', None)):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = op
        if val is not None: n.inputs[1].default_value = val
        nt.links.new(prev, n.inputs[0]); prev = n.outputs[0]
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.inputs[6].default_value = a; mix.inputs[7].default_value = b_
    nt.links.new(prev, mix.inputs[0]); nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 120; nz.inputs["Detail"].default_value = 2
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = .05
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def box(name, size, loc, m, bevel=.01, layer="back", seg=3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        md = o.modifiers.new("b", 'BEVEL'); md.width = bevel; md.segments = seg; md.limit_method = 'ANGLE'
    o.data.materials.append(m); o["layer"] = layer
    for p in o.data.polygons: p.use_smooth = True
    return o

def cyl(name, r, h, loc, m, rot=(0, 0, 0), layer="back", verts=20, flat_caps=False, smooth=True):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, rotation=rot, vertices=verts); o = bpy.context.object
    o.name = name; o.data.materials.append(m); o["layer"] = layer
    for p in o.data.polygons: p.use_smooth = smooth and not (flat_caps and abs(p.normal.z) > .9)   # flat caps: no dark smoothing rim on short discs (normals are read before any rotation is applied, so use smooth=False for turned discs)
    return o

def light_rig(target, size):
    sc = bpy.context.scene
    w = bpy.data.worlds.get("RA_World") or bpy.data.worlds.new("RA_World"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (.85, .88, .92, 1); w.node_tree.nodes["Background"].inputs[1].default_value = .35
    def area(n, loc, energy, s, color=(1, .97, .92)):
        bpy.ops.object.light_add(type='AREA', location=loc); l = bpy.context.object; l.name = n
        l.data.energy = energy; l.data.size = s; l.data.color = color
        l.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); l["layer"] = "light"
    area("Key", (target[0] - size * 1.2, target[1] - size * 2.2, target[2] + size * 2.0), 120 * size * size, size * 1.5)
    area("Fill", (target[0] + size * 1.6, target[1] - size * 1.6, target[2] + size * .6), 35 * size * size, size * 2, (.92, .95, 1))

def camera(target, pitch_deg, dist, lens=40):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("RA_Cam")
    if not cam:
        cam = bpy.data.objects.new("RA_Cam", bpy.data.cameras.new("RA_Cam")); sc.collection.objects.link(cam)
    cam.data.lens = lens; cam.data.sensor_width = 36
    p = rad(pitch_deg); t = Vector(target)
    cam.location = t + Vector((0, -math.cos(p) * dist, math.sin(p) * dist))
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam["layer"] = "cam"
    sc.camera = cam; return cam

# ---------------------------------------------------------------- lanes
LANES = {}   # key -> list of dict(floor=[fl, fr, bl, br] world, h=product height m)
def lane(key, x0, x1, y0, y1, z, h, door=-1):
    LANES.setdefault(key, []).append(dict(floor=[(x0, y0, z), (x1, y0, z), (x0, y1, z), (x1, y1, z)], h=h, door=door))

# ---------------------------------------------------------------- fixtures
def shelf_rows(key, W, D, z_levels, splits, x_margin, y_front, depth, clearance, lip_mat, plate_mat, rail_mat, back_mat=None, doors=0):
    """Shelves: a plate per level (back layer), a lip with a price rail in front (front layer); lanes on the plates."""
    i = 0
    for z, n in zip(z_levels, splits):
        box(f"plate{i}", (W - 2 * x_margin, depth, .025), (0, y_front + depth / 2, z - .0125), plate_mat, bevel=.004)
        box(f"lip{i}", (W - 2 * x_margin + .01, .02, .065), (0, y_front - .005, z + .012), lip_mat, bevel=.006, layer="front")
        box(f"rail{i}", (W - 2 * x_margin + .012, .006, .028), (0, y_front - .016, z + .012), rail_mat, bevel=.002, layer="front")
        w = (W - 2 * x_margin - .03 * (n - 1)) / n
        for k in range(n):
            a = -W / 2 + x_margin + k * (w + .03)
            cx = a + w / 2
            lane(key, a + .02, a + w - .02, y_front + .03, y_front + depth - .04, z, clearance, (0 if cx < 0 else 1) if doors == 2 else (0 if doors == 1 else -1))
        i += 1

def build_fridge(key="fridge", frost=False):
    """Two-door drinks fridge (frost=True: the frozen-food freezer). Each door is its own layer, hinged on the outside."""
    clear(); LANES.pop(key, None)
    W, D, H = 1.46, 0.64, 2.0
    body = mat("fr_body" + ("_f" if frost else ""), TEAL if not frost else (0.16, 0.40, 0.64, 1), rough=.35)
    inner = mat("fr_inner" + ("_f" if frost else ""), INTERIOR if not frost else FROST, rough=.6)
    wire = mat("wire", METAL, rough=.3, metal=.8); lip = mat("lip_white", WHITE, rough=.4); rail = mat("rail_orange", ORANGE, rough=.5)
    led = mat("led", (1, .97, .9, 1), emit=8.0); sign = mat("sign_cream", CREAM, rough=.5, emit=.6)
    t = .06
    box("side_L", (t, D, H), (-W / 2 + t / 2, D / 2, H / 2), body, bevel=.02)
    box("side_R", (t, D, H), (W / 2 - t / 2, D / 2, H / 2), body, bevel=.02)
    box("mullion", (.05, .05, H - .46), (0, .03, .16 + (H - .46) / 2), body, bevel=.01, layer="front")
    box("top", (W, D, .30), (0, D / 2, H - .15), body, bevel=.025)
    box("base", (W, D, .16), (0, D / 2, .08), body, bevel=.02)
    box("back", (W - 2 * t, .04, H - .46), (0, D - .02, .16 + (H - .46) / 2), inner, bevel=.005)
    box("inner_L", (.01, D - .06, H - .46), (-W / 2 + t + .005, D / 2, .16 + (H - .46) / 2), inner, bevel=0)
    box("inner_R", (.01, D - .06, H - .46), (W / 2 - t - .005, D / 2, .16 + (H - .46) / 2), inner, bevel=0)
    box("inner_floor", (W - 2 * t, D - .04, .01), (0, D / 2, .165), inner, bevel=0)
    for x in (-W / 4, W / 4):
        box("led", (W / 2 - t - .08, .03, .015), (x, .06, H - .315), led, bevel=0)
    box("sign", (W * .74, .02, .17), (0, -.012, H - .15), sign, bevel=.01)
    if frost:
        snow = mat("snow", (1, 1, 1, 1), rough=.9)
        for k, x in enumerate((-.55, -.35, .35, .55)):
            cyl(f"flake{k}", .025, .01, (x, -.015, H - .15), snow, rot=(rad(90), 0, 0), verts=6)
    zs = [1.40, 1.04, .68, .25]
    shelf_rows(key, W, D, zs, [2, 2, 2, 1], t + .005, .07, D - .14, .26, lip, wire, rail, doors=2)
    # the doors: frame + glass + handle, hinged on the outside edges
    fr = mat("door_frame" + ("_f" if frost else ""), DARK if not frost else (0.15, 0.25, 0.35, 1), rough=.3, metal=.5)
    glass = mat("glass" + ("_f" if frost else ""), (.75, .90, .95, 1) if not frost else (.85, .95, 1, 1), rough=.05, alpha=.20)
    chrome = mat("chrome", (.85, .86, .88, 1), rough=.15, metal=1)
    dz0, dz1 = .16, H - .30; zc = (dz0 + dz1) / 2; hz = dz1 - dz0
    for d, (x0, x1) in enumerate(((-W / 2 + .01, -.015), (.015, W / 2 - .01))):
        lay = f"door{d}"; wd = x1 - x0; xc = (x0 + x1) / 2
        box("door_glass", (wd - .02, .012, hz), (xc, -.02, zc), glass, bevel=0, layer=lay)
        box("door_fL", (.045, .03, hz), (x0 + .022, -.02, zc), fr, bevel=.008, layer=lay)
        box("door_fR", (.045, .03, hz), (x1 - .022, -.02, zc), fr, bevel=.008, layer=lay)
        box("door_fT", (wd, .03, .05), (xc, -.02, dz1 - .025), fr, bevel=.008, layer=lay)
        box("door_fB", (wd, .03, .07), (xc, -.02, dz0 + .035), fr, bevel=.008, layer=lay)
        hx = x1 - .08 if d == 0 else x0 + .08
        box("handle", (.025, .05, .55), (hx, -.06, zc + .1), chrome, bevel=.01, layer=lay)
        # hinge on the outer edge: the door swings out toward the viewer around it
        hinge(lay, (x0 if d == 0 else x1, -.02, zc), -1 if d == 0 else 1)
    return dict(target=(0, D * .25, H * .50), pitch=14, dist=3.55, lens=40, size=H, doors=[dict(layer="door0", hinge="left", kind="swing"), dict(layer="door1", hinge="right", kind="swing")])

def build_gondola(key="gondola", back_rgb=TEAL, post_rgb=CREAM, holes=True, header_rgb=None):
    clear(); LANES.pop(key, None)
    W, D, H = 1.50, 0.50, 1.75
    post = mat("post_" + key, post_rgb, rough=.5); back = mat("peg_" + key, back_rgb, rough=.6)
    plate = mat("plate_metal", (.86, .87, .85, 1), rough=.35, metal=.3); lip = mat("lip_white", WHITE, rough=.4); rail = mat("rail_orange", ORANGE, rough=.5)
    box("post_L", (.06, D, H), (-W / 2 + .03, D / 2, H / 2), post, bevel=.015)
    box("post_R", (.06, D, H), (W / 2 - .03, D / 2, H / 2), post, bevel=.015)
    box("back", (W - .1, .05, H - .2), (0, D - .025, .1 + (H - .2) / 2), back, bevel=.006)
    # pegboard holes
    hole = mat("hole", (0.02, 0.10, 0.10, 1), rough=.9)
    for r in range(9 if holes else 0):
        for c in range(14):
            cyl(f"h{r}_{c}", .008, .004, (-W / 2 + .13 + c * (W - .26) / 13, D - .052, .25 + r * .16), hole, rot=(rad(90), 0, 0), verts=8)
    box("kick", (W - .1, .06, .16), (0, .04, .08), mat("kick_" + key, back_rgb, rough=.5), bevel=.01, layer="front")
    box("header", (W, .06, .22), (0, D * .5, H + .08), mat("header_" + key, header_rgb or back_rgb, rough=.4), bevel=.02)
    box("header_face", (W * .86, .01, .15), (0, D * .5 - .035, H + .08), mat("sign_cream", CREAM, rough=.5, emit=.6), bevel=.005)
    zs = [1.32, .98, .64, .25]
    shelf_rows(key, W, D, zs, [2, 2, 2, 1], .06, .03, D - .10, .26, lip, plate, rail)
    return dict(target=(0, D * .3, H * .53), pitch=13, dist=3.25, lens=38, size=H)

def build_chest(key="chest"):
    """Ice-cream chest freezer seen from the front and above: rounded white body, pink trim, a cream sign on
    the front, wire baskets inside and two framed sliding glass lids that together cover the whole top."""
    clear(); LANES.pop(key, None)
    W, D, H = 1.70, 0.80, 0.85
    body = mat("chest_body", WHITE, rough=.3); rim = mat("chest_rim", PINK, rough=.35); inner = mat("chest_in", FROST, rough=.7)
    wire = mat("wire", METAL, rough=.3, metal=.8); alu = mat("lid_frame", (.82, .84, .86, 1), rough=.2, metal=.9)
    t = .08
    box("front", (W, t, H), (0, t / 2, H / 2), body, bevel=.05, layer="front", seg=5)
    box("back", (W, t, H), (0, D - t / 2, H / 2), body, bevel=.05, seg=5)
    box("side_L", (t, D - 2 * t + .01, H), (-W / 2 + t / 2, D / 2, H / 2), body, bevel=.04, seg=5)
    box("side_R", (t, D - 2 * t + .01, H), (W / 2 - t / 2, D / 2, H / 2), body, bevel=.04, seg=5)
    box("floor", (W - 2 * t, D - 2 * t, .02), (0, D / 2, .62), inner, bevel=0)
    box("wall_in_back", (W - 2 * t, .01, H - .62), (0, D - t - .005, .62 + (H - .62) / 2), inner, bevel=0)
    # rim: a soft pink band around the top edge
    box("rim_front", (W + .01, .05, .035), (0, .02, H - .01), rim, bevel=.015, layer="front")
    box("rim_back", (W + .01, .05, .035), (0, D - .02, H - .01), rim, bevel=.015)
    box("rim_L", (.05, D, .035), (-W / 2 + .02, D / 2, H - .01), rim, bevel=.015)
    box("rim_R", (.05, D, .035), (W / 2 - .02, D / 2, H - .01), rim, bevel=.015)
    box("stripe", (W + .004, .004, .05), (0, -.002, H * .30), rim, bevel=.004, layer="front")
    box("sign", (W * .42, .012, .16), (0, -.008, H * .58), mat("sign_cream", CREAM, rough=.5, emit=.4), bevel=.02, layer="front")
    box("kick", (W - .14, .06, .07), (0, .06, .035), mat("kick", DARK, rough=.5), bevel=.01, layer="front")
    for x in (-W / 2 + .12, W / 2 - .12):
        cyl(f"foot{x:.1f}", .03, .03, (x, .12, .015), mat("kick", DARK, rough=.5), layer="front")
    # baskets: 3 at the back, 4 at the front (slot order: back row first)
    def basket(x0, x1, y0, y1, nm):
        z0, z1 = .63, H - .03
        for s, l in ((( x1 - x0, .008, z1 - z0), ((x0 + x1) / 2, y0, (z0 + z1) / 2)), ((x1 - x0, .008, z1 - z0), ((x0 + x1) / 2, y1, (z0 + z1) / 2)),
                     ((.008, y1 - y0, z1 - z0), (x0, (y0 + y1) / 2, (z0 + z1) / 2)), ((.008, y1 - y0, z1 - z0), (x1, (y0 + y1) / 2, (z0 + z1) / 2))):
            o = box(nm, s, l, wire, bevel=0)
            md = o.modifiers.new("w", 'WIREFRAME'); md.thickness = .006; md.use_replace = True
        lane(key, x0 + .02, x1 - .02, y0 + .02, y1 - .02, .64, .16, 0 if (x0 + x1) / 2 < 0 else 1)
    ix0, ix1 = -W / 2 + t + .02, W / 2 - t - .02; ym = D / 2
    for k in range(3):
        a = ix0 + k * (ix1 - ix0) / 3; basket(a, a + (ix1 - ix0) / 3 - .02, ym + .01, D - t - .02, f"bk{k}")
    for k in range(4):
        a = ix0 + k * (ix1 - ix0) / 4; basket(a, a + (ix1 - ix0) / 4 - .02, t + .02, ym - .01, f"bf{k}")
    # two sliding glass lids, each a framed pane covering half the top (with a small overlap in the middle)
    glass = mat("glass_f", (.85, .95, 1, 1), rough=.05, alpha=.22)
    for i, (x0, x1) in enumerate(((-W / 2 + .015, .03), (-.03, W / 2 - .015))):
        z = H + .02 + (.018 if i == 0 else 0); xc = (x0 + x1) / 2; w = x1 - x0; d = D - .03
        lay = f"door{i}"
        box(f"lid{i}", (w - .03, d - .03, .008), (xc, D / 2, z), glass, bevel=0, layer=lay)
        box(f"lidfF{i}", (w, .03, .022), (xc, D / 2 - d / 2 + .015, z), alu, bevel=.006, layer=lay)
        box(f"lidfB{i}", (w, .03, .022), (xc, D / 2 + d / 2 - .015, z), alu, bevel=.006, layer=lay)
        box(f"lidfL{i}", (.03, d, .022), (x0 + .015, D / 2, z), alu, bevel=.006, layer=lay)
        box(f"lidfR{i}", (.03, d, .022), (x1 - .015, D / 2, z), alu, bevel=.006, layer=lay)
        hx = x1 - .09 if i == 0 else x0 + .09
        box(f"lidh{i}", (.05, .22, .03), (hx, D * .3, z + .018), alu, bevel=.01, layer=lay)
    return dict(target=(0, D * .5, H * .7), pitch=60, dist=2.75, lens=40, size=W, doors=[dict(layer="door0", kind="slide", dir=1, slide=(.80, 0, 0)), dict(layer="door1", kind="slide", dir=-1, slide=(-.80, 0, 0))])


def build_dairy_open(key="dairy_open"):
    """Open multideck (laticínios): no doors, a cold air curtain at the top, white body, light blue inside."""
    clear(); LANES.pop(key, None)
    W, D, H = 1.46, 0.70, 1.95
    body = mat("dairy_body", WHITE, rough=.35); inner = mat("dairy_in", (0.78, 0.90, 0.97, 1), rough=.6)
    wire = mat("wire", METAL, rough=.3, metal=.8); lip = mat("lip_blue", (0.20, 0.47, 0.75, 1), rough=.4); rail = mat("rail_white", WHITE, rough=.5)
    t = .07
    box("side_L", (t, D, H), (-W / 2 + t / 2, D / 2, H / 2), body, bevel=.03)
    box("side_R", (t, D, H), (W / 2 - t / 2, D / 2, H / 2), body, bevel=.03)
    box("top", (W, D, .26), (0, D / 2, H - .13), body, bevel=.03)
    box("canopy", (W - .02, .18, .06), (0, .05, H - .27), body, bevel=.02, layer="front")
    box("led", (W - 2 * t - .05, .02, .012), (0, .10, H - .305), mat("led", (1, .97, .9, 1), emit=8.0), bevel=0)
    box("base", (W, D, .30), (0, D / 2, .15), body, bevel=.03)
    box("bumper", (W, .05, .10), (0, -.01, .26), lip, bevel=.02, layer="front")
    box("back", (W - 2 * t, .04, H - .56), (0, D - .02, .30 + (H - .56) / 2), inner, bevel=.005)
    box("inner_L", (.01, D - .06, H - .56), (-W / 2 + t + .005, D / 2, .30 + (H - .56) / 2), inner, bevel=0)
    box("inner_R", (.01, D - .06, H - .56), (W / 2 - t - .005, D / 2, .30 + (H - .56) / 2), inner, bevel=0)
    box("sign", (W * .74, .02, .16), (0, -.012, H - .13), mat("sign_cream", CREAM, rough=.5, emit=.6), bevel=.01)
    zs = [1.38, 1.04, .70, .32]
    shelf_rows(key, W, D, zs, [2, 2, 2, 1], t + .005, .06, D - .16, .25, lip, wire, rail)
    return dict(target=(0, D * .3, H * .5), pitch=14, dist=3.5, lens=40, size=H)

def grid_cells(W, D, back_n=3, front_n=4, margin=.06, gap=.04, y_split=None):
    """(x0, x1, y0, y1, row) of the cells: the back row first (slots 1..back_n), then the front row."""
    y_split = y_split if y_split is not None else D / 2
    cells = []
    for row, (n, y0, y1) in enumerate(((back_n, y_split + gap / 2, D - margin), (front_n, margin, y_split - gap / 2))):
        w = (W - 2 * margin - gap * (n - 1)) / n
        for k in range(n):
            x0 = -W / 2 + margin + k * (w + gap); cells.append((x0, x0 + w, y0, y1, row))
    return cells

def crate_cell(nm, x0, x1, y0, y1, z, h, wood_m, slat_m):
    """An open wooden crate: floor + back/sides in the back layer, the front slats in the front layer."""
    w, d = x1 - x0, y1 - y0; xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    box(nm + "_floor", (w, d, .02), (xc, yc, z + .01), wood_m, bevel=.004)
    box(nm + "_back", (w, .025, h), (xc, y1, z + h / 2), wood_m, bevel=.006)
    box(nm + "_l", (.025, d, h), (x0, yc, z + h / 2), wood_m, bevel=.006)
    box(nm + "_r", (.025, d, h), (x1, yc, z + h / 2), wood_m, bevel=.006)
    for i in range(2):
        box(nm + f"_f{i}", (w + .01, .028, h * .32), (xc, y0, z + h * (.2 + .45 * i)), slat_m, bevel=.008, layer="front")

def slat_crate(nm, x0, x1, y0, y1, z, h, wood_m, post_m, slats=2, layer_front="front"):
    """A real wooden produce crate: four corner posts, a slatted floor, `slats` horizontal slats per side with a gap
    between them (the dark interior shows through), and the front slats on the front layer."""
    w, d = x1 - x0, y1 - y0; xc, yc = (x0 + x1) / 2, (y0 + y1) / 2; p = .022; sh = (h - .02) / slats
    box(nm + "_floor", (w, d, .018), (xc, yc, z + .009), wood_m, bevel=.003)
    for px in (x0, x1):
        for py in (y0, y1):
            box(f"{nm}_p{px:.2f}{py:.2f}", (p, p, h), (px, py, z + h / 2), post_m, bevel=.004, layer=layer_front if py == y0 else "back")
    for k in range(slats):
        zc = z + .01 + sh * (k + .5); t = sh * .70
        box(f"{nm}_sb{k}", (w, .016, t), (xc, y1 + .004, zc), wood_m, bevel=.004)
        box(f"{nm}_sl{k}", (.016, d, t), (x0 - .004, yc, zc), wood_m, bevel=.004)
        box(f"{nm}_sr{k}", (.016, d, t), (x1 + .004, yc, zc), wood_m, bevel=.004)
        box(f"{nm}_sf{k}", (w + .01, .016, t), (xc, y0 - .004, zc), wood_m, bevel=.004, layer=layer_front)

def build_crates(key="crates"):
    """Hortifruti stand (v4): seven slatted wooden crates (3 on a raised step at the back, 4 in front) on a plank
    table with turned legs, a cream / teal striped cloth skirt with a scalloped hem, same lane grid as before."""
    clear(); LANES.pop(key, None)
    W, D = 1.70, 1.00
    plank = wood_mat("cr_plank", (0.84, 0.62, 0.36), (0.66, 0.45, 0.22), scale=1.4, axis="y")
    crate_w = wood_mat("cr_crate", (0.86, 0.68, 0.42), (0.68, 0.50, 0.26), scale=3, axis="x", rough=.7)
    post = wood_mat("cr_post", (0.62, 0.42, 0.20), (0.44, 0.27, 0.11), scale=3, axis="z", rough=.7)
    legs = wood_mat("cr_legs", (0.52, 0.32, 0.14), (0.36, 0.20, 0.08), scale=2, axis="z")
    skirt = stripes_mat("cr_skirt", CREAM, (0.10, 0.48, 0.45, 1), period=.11, axis="x")
    zt = .72
    box("table", (W + .12, D + .10, .04), (0, D / 2, zt - .02), plank, bevel=.012, seg=4)
    box("table_edge", (W + .14, .03, .07), (0, -.055, zt - .035), legs, bevel=.01, layer="front")
    for sx in (-1, 1):
        box(f"table_edge_s{sx}", (.03, D + .12, .07), (sx * (W / 2 + .055), D / 2, zt - .035), legs, bevel=.01)
    # turned legs: a stack of a cone, a bead and a shaft; the two front ones go to the front layer
    for sx in (-1, 1):
        for y, lay in ((.06, "back"), (D - .06, "back")):
            x = sx * (W / 2 - .02)
            cyl(f"leg{sx}{lay}_top", .045, .12, (x, y, zt - .11), legs, verts=20, layer=lay)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=.052, location=(x, y, zt - .20), segments=24, ring_count=12); o = bpy.context.object
            o.name = f"leg{sx}{lay}_bead"; o.data.materials.append(legs); o["layer"] = lay
            for p in o.data.polygons: p.use_smooth = True
            bpy.ops.mesh.primitive_cone_add(radius1=.03, radius2=.04, depth=zt - .26, location=(x, y, (zt - .26) / 2), vertices=20); o = bpy.context.object
            o.name = f"leg{sx}{lay}_shaft"; o.data.materials.append(legs); o["layer"] = lay
            for p in o.data.polygons: p.use_smooth = abs(p.normal.z) < .9
    box("stretcher", (W - .1, .035, .035), (0, .06, .22), legs, bevel=.008)
    # striped skirt hanging from the front edge, scalloped hem; a short return on each side
    box("skirt", (W + .10, .012, .40), (0, -.062, zt - .27), skirt, bevel=.004, layer="front")
    n = 14
    for k in range(n):
        x = -(W + .10) / 2 + (k + .5) * (W + .10) / n
        cyl(f"scallop{k}", (W + .10) / n / 2, .010, (x, -.073, zt - .47), skirt, rot=(rad(90), 0, 0), verts=24, layer="front", smooth=False)   # just in front of the skirt (coplanar faces render black)
    for sx in (-1, 1):
        box(f"skirt_s{sx}", (.012, .30, .40), (sx * (W / 2 + .062), .15, zt - .27), skirt, bevel=.004)
    # raised step at the back: plank top, slatted front
    box("step", (W, D / 2, .03), (0, D * .75, zt + .145), plank, bevel=.006)
    for k in range(3):
        box(f"step_slat{k}", (W, .02, .04), (0, D / 2 + .005, zt + .02 + k * .045), crate_w, bevel=.004)
    for sx in (-1, 1):
        box(f"step_side{sx}", (.02, D / 2, .14), (sx * (W / 2 - .01), D * .75, zt + .07), crate_w, bevel=.004)
    for i, (x0, x1, y0, y1, row) in enumerate(grid_cells(W, D, margin=.04, gap=.05)):
        z = .91 if row == 0 else .75; h = .17
        slat_crate(f"cr{i}", x0, x1, y0, y1, z, h, crate_w, post)
        lane(key, x0 + .03, x1 - .03, y0 + .04, y1 - .03, z + .02, .14)
    return dict(target=(0, D * .45, .9), pitch=34, dist=3.0, lens=40, size=W)

def build_stand(key="stand"):
    """Market stand: tilted wooden bins in two rows under a striped awning."""
    clear(); LANES.pop(key, None)
    W, D = 1.80, 1.00
    wood = mat("stand_wood", WOOD, rough=.6); bin_m = mat("bin_wood", (0.70, 0.47, 0.26, 1), rough=.65); slat = mat("bin_slat", (0.58, 0.37, 0.19, 1), rough=.65)
    box("frame", (W + .1, D, .08), (0, D / 2, .70), wood, bevel=.02)
    box("front_skirt", (W + .1, .03, .55), (0, -.01, .45), mat("skirt", (0.18, 0.50, 0.32, 1), rough=.7), bevel=.01, layer="front")
    box("step", (W, D / 2, .18), (0, D * .75, .83), wood, bevel=.015)
    for side in (-1, 1):
        box(f"pole{side}", (.05, .05, 1.2), (side * (W / 2 + .02), D - .05, 1.3), wood, bevel=.01)
    for k in range(9):
        c = (0.18, 0.50, 0.32, 1) if k % 2 == 0 else CREAM
        box(f"awn{k}", (W / 9 + .005, .9, .02), (-W / 2 + (k + .5) * W / 9, D * .55, 1.95), mat(f"awn{k%2}", c, rough=.7), bevel=.005).rotation_euler = (rad(-16), 0, 0)
    for i, (x0, x1, y0, y1, row) in enumerate(grid_cells(W, D, margin=.04, gap=.05)):
        z = .93 if row == 0 else .75
        crate_cell(f"bin{i}", x0, x1, y0, y1, z, .15, bin_m, slat)
        lane(key, x0 + .03, x1 - .03, y0 + .04, y1 - .03, z + .02, .14)
    return dict(target=(0, D * .45, 1.05), pitch=30, dist=3.2, lens=40, size=W)

def gingham(name, a=(0.98, 0.94, 0.84, 1), b=(0.80, 0.22, 0.18, 1), checks=48):
    """Checked cloth: red/cream stripes along X multiplied by stripes along Y+Z (so the pattern also shows on
    the hanging flaps) -> cream, pink, pink, red squares, like a real gingham."""
    key = "gingham_" + name
    if key in _M and _M[key].name in bpy.data.materials: return _M[key]
    m = bpy.data.materials.get("RA_" + key) or bpy.data.materials.new("RA_" + key); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = .9
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    yz = nt.nodes.new("ShaderNodeMath"); yz.operation = 'ADD'; nt.links.new(sep.outputs["Y"], yz.inputs[0]); nt.links.new(sep.outputs["Z"], yz.inputs[1])
    def stripe(sock):
        prev = sock
        for op, val in (('MULTIPLY', checks), ('FLOOR', None), ('MODULO', 2), ('ABSOLUTE', None)):
            n = nt.nodes.new("ShaderNodeMath"); n.operation = op
            if val is not None: n.inputs[1].default_value = val
            nt.links.new(prev, n.inputs[0]); prev = n.outputs[0]
        return prev
    add = nt.nodes.new("ShaderNodeMath"); add.operation = 'ADD'; nt.links.new(stripe(sep.outputs["X"]), add.inputs[0]); nt.links.new(stripe(yz.outputs[0]), add.inputs[1])
    half = nt.nodes.new("ShaderNodeMath"); half.operation = 'MULTIPLY'; half.inputs[1].default_value = .5; nt.links.new(add.outputs[0], half.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.inputs[6].default_value = a; mix.inputs[7].default_value = b
    nt.links.new(half.outputs[0], mix.inputs[0]); nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    _M[key] = m; return m

def wicker_basket(nm, x0, x1, y0, y1, z, h, wick, wick_m, wick_d, cloth=None, rows=3, back_rows=5):
    """A woven basket: stacked rounded rods (alternating tones, weaving in and out) around a floor, vertical
    stakes and a thick rolled rim. The front is low (rows) and the back high (back_rows) so the bread shows,
    the sides step up halfway. Optional gingham cloth lining, folded over the front rim.
    Front wall, front rim and front flap go to the front layer."""
    w, d = x1 - x0, y1 - y0; xc, yc = (x0 + x1) / 2, (y0 + y1) / 2; t = .028
    box(nm + "_floor", (w, d, .02), (xc, yc, z + .01), wick_d, bevel=.006)
    rh = h / rows; hb = rh * back_rows; ym = yc + .02   # the sides step up at ym
    for r in range(back_rows):
        zc = z + .01 + rh * (r + .5); m = wick if r % 2 else wick_m; bw = rh * .48; o = .004 if r % 2 else 0
        box(f"{nm}_b{r}", (w + t + 2 * o, t, rh), (xc, y1 + o, zc), m, bevel=bw, seg=4)
        if r < rows:
            box(f"{nm}_l{r}", (t, d + 2 * o, rh), (x0 - o, yc, zc), m, bevel=bw, seg=4)
            box(f"{nm}_r{r}", (t, d + 2 * o, rh), (x1 + o, yc, zc), m, bevel=bw, seg=4)
            box(f"{nm}_f{r}", (w + t + 2 * o, t, rh), (xc, y0 - o, zc), m, bevel=bw, seg=4, layer="front")
        else:
            box(f"{nm}_l{r}", (t, y1 - ym + 2 * o, rh), (x0 - o, (ym + y1) / 2, zc), m, bevel=bw, seg=4)
            box(f"{nm}_r{r}", (t, y1 - ym + 2 * o, rh), (x1 + o, (ym + y1) / 2, zc), m, bevel=bw, seg=4)
    n = max(3, int(w / .075)); nd = max(2, int(d / .075))
    for k in range(n):   # stakes end just under the rim, flat caps (no dark dots peeking out)
        x = x0 + (k + .5) * w / n
        cyl(f"{nm}_sb{k}", .0075, hb, (x, y1 + t * .5, z + .01 + hb / 2), wick_d, verts=8, flat_caps=True)
        cyl(f"{nm}_sf{k}", .0075, h, (x, y0 - t * .5, z + .01 + h / 2), wick_d, verts=8, layer="front", flat_caps=True)
    for k in range(nd):
        y = y0 + (k + .5) * d / nd; sh = hb if y > ym else h
        cyl(f"{nm}_sl{k}", .0075, sh, (x0 - t * .5, y, z + .01 + sh / 2), wick_d, verts=8, flat_caps=True)
        cyl(f"{nm}_sr{k}", .0075, sh, (x1 + t * .5, y, z + .01 + sh / 2), wick_d, verts=8, flat_caps=True)
    # rolled rim: low in front, high at the back, two steps on each side; cylinders close the bevelled corners
    zr = z + .01 + h + .012; zb = z + .01 + hb + .012; rt = .04
    box(nm + "_rb", (w + rt, rt, .028), (xc, y1, zb), wick_d, bevel=.013, seg=4)
    box(nm + "_rf", (w + rt, rt, .028), (xc, y0, zr), wick_d, bevel=.013, seg=4, layer="front")
    for sx, x in ((-1, x0), (1, x1)):
        box(f"{nm}_rs{sx}a", (rt, ym - y0 + rt, .028), (x, (y0 + ym) / 2, zr), wick_d, bevel=.013, seg=4)
        box(f"{nm}_rs{sx}b", (rt, y1 - ym + rt, .028), (x, (ym + y1) / 2, zb), wick_d, bevel=.013, seg=4)
        box(f"{nm}_rs{sx}c", (rt, rt, zb - zr + .028), (x, ym, (zr + zb) / 2), wick_d, bevel=.013, seg=4)
        cyl(f"{nm}_rc{sx}b", rt / 2, .030, (x, y1, zb), wick_d, verts=12, flat_caps=True)   # a hair taller than the rim boxes
        cyl(f"{nm}_rc{sx}m", rt / 2, .030, (x, ym, zb), wick_d, verts=12, flat_caps=True)
        cyl(f"{nm}_rc{sx}f", rt / 2, .030, (x, y0, zr), wick_d, verts=12, layer="front", flat_caps=True)
    if cloth:
        box(nm + "_cl", (w - .03, d - .03, .016), (xc, yc, z + .028), cloth, bevel=.007, seg=4)
        fw = w * .84
        box(nm + "_cf", (fw, rt + .02, .014), (xc, y0, zr + .018), cloth, bevel=.006, seg=3, layer="front")
        o = box(nm + "_cfh", (fw, .014, .075), (0, 0, -.0375), cloth, bevel=.006, seg=3, layer="front")
        o.location = (xc, y0 - rt / 2 - .006, zr + .018); o.rotation_euler = (rad(-14), 0, 0)

def build_basket(key="basket"):
    """Bakery bread display: woven wicker baskets lined with a red gingham cloth on a two-tier wooden stand
    whose base is a cream-painted plank cabinet with dark corner posts (same 3 + 4 lane grid as before)."""
    clear(); LANES.pop(key, None)
    W, D = 1.70, 1.00
    top = mat("bk_top", (0.74, 0.48, 0.24, 1), rough=.55); wood = mat("bk_wood", WOOD, rough=.6); dark = mat("bk_dark", (0.33, 0.18, 0.08, 1), rough=.6)
    plank = mat("bk_plank", CREAM, rough=.7); plank_d = mat("bk_plank_d", (0.87, 0.79, 0.61, 1), rough=.7)
    wick = mat("wicker", (0.84, 0.62, 0.33, 1), rough=.75); wick_m = mat("wicker_m", (0.74, 0.52, 0.26, 1), rough=.75); wick_d = mat("wicker_d", (0.56, 0.36, 0.16, 1), rough=.75)
    cloth = gingham("red")
    zt = .72; zb = zt - .07   # table top / top of the cabinet
    box("table", (W + .1, D + .1, .035), (0, D / 2, zt - .0175), top, bevel=.015, seg=4)
    box("apron_f", (W + .1, .035, .05), (0, -.035, zt - .055), wood, bevel=.01, layer="front")
    box("apron_trim", (W + .1, .012, .016), (0, -.056, zt - .045), dark, bevel=.004, layer="front")
    for sx in (-1, 1):
        box(f"apron_s{sx}", (.035, D + .1, .05), (sx * (W / 2 + .035), D / 2, zt - .055), wood, bevel=.01)
    # cabinet: corner posts, cream vertical planks in front and on the sides, a dark plinth
    for sx in (-1, 1):
        for y in (.0, D):
            box(f"post{sx}{y:.0f}", (.07, .07, zb), (sx * (W / 2 - .005), y, zb / 2), dark, bevel=.012, seg=4)
    box("cab_side_L", (.03, D - .08, zb - .08), (-W / 2 + .01, D / 2, zb / 2 + .02), plank, bevel=.006)
    box("cab_side_R", (.03, D - .08, zb - .08), (W / 2 - .01, D / 2, zb / 2 + .02), plank, bevel=.006)
    box("cab_back", (W - .08, .03, zb - .08), (0, D - .01, zb / 2 + .02), plank, bevel=.006)
    n = 15; pw = (W - .09) / n
    for k in range(n):
        box(f"plank{k}", (pw - .008, .03, zb - .14), (-W / 2 + .045 + (k + .5) * pw, -.005, zb / 2 + .05), plank if k % 2 else plank_d, bevel=.005)
    box("plinth", (W - .02, D - .02, .09), (0, D / 2, .045), dark, bevel=.01)
    box("plinth_f", (W + .02, .03, .07), (0, -.005, .035), dark, bevel=.008)
    box("step", (W, D / 2, .14), (0, D * .75, zt + .07), top, bevel=.015)
    box("step_face", (W, .025, .12), (0, D / 2 + .005, zt + .07), wood, bevel=.008)
    for i, (x0, x1, y0, y1, row) in enumerate(grid_cells(W, D, margin=.05, gap=.06)):
        z = .89 if row == 0 else .75; h = .07
        wicker_basket(f"bk{i}", x0, x1, y0, y1, z, h, wick, wick_m, wick_d, cloth)
        lane(key, x0 + .03, x1 - .03, y0 + .04, y1 - .03, z + .036, .13)
    return dict(target=(0, D * .45, .9), pitch=34, dist=3.0, lens=40, size=W)

def build_cooler(key="cooler"):
    """Styrofoam box with ice, seen from above; the white lid (door0) comes off to the side."""
    clear(); LANES.pop(key, None)
    W, D, H = 1.30, 0.80, .55
    foam = mat("foam", (0.97, 0.97, 0.95, 1), rough=.9); ice = mat("ice", (0.72, 0.88, 0.97, 1), rough=.25)
    t = .08
    box("front", (W, t, H), (0, t / 2, H / 2), foam, bevel=.03, layer="front")
    box("back", (W, t, H), (0, D - t / 2, H / 2), foam, bevel=.03)
    box("side_L", (t, D - 2 * t + .01, H), (-W / 2 + t / 2, D / 2, H / 2), foam, bevel=.03)
    box("side_R", (t, D - 2 * t + .01, H), (W / 2 - t / 2, D / 2, H / 2), foam, bevel=.03)
    box("ice_bed", (W - 2 * t, D - 2 * t, .03), (0, D / 2, .30), ice, bevel=.01)
    import random; rnd = random.Random(3)
    for k in range(26):
        sz = rnd.uniform(.045, .07)
        box(f"cube{k}", (sz, sz, sz * .8), (rnd.uniform(-W / 2 + t + .06, W / 2 - t - .06), rnd.uniform(t + .06, D - t - .06), .32 + sz * .3), ice, bevel=.015)
    for i, (x0, x1, y0, y1, row) in enumerate(grid_cells(W - 2 * t, D - 2 * t, margin=.03, gap=.03)):
        lane(key, x0 + .01, x1 - .01, y0 + t + .01, y1 + t - .01, .32, .17, 0)
    lid = mat("foam_lid", (0.99, 0.99, 0.97, 1), rough=.9)
    box("lid", (W + .02, D + .02, .06), (0, D / 2, H + .03), lid, bevel=.03, layer="door0")
    box("lid_grip", (.30, .06, .03), (0, D / 2, H + .075), mat("grip", (0.25, 0.55, 0.80, 1), rough=.5), bevel=.012, layer="door0")
    return dict(target=(0, D * .5, H * .6), pitch=55, dist=2.4, lens=40, size=W, doors=[dict(layer="door0", kind="slide", dir=1, slide=(1.30, 0, -.02))])

def build_display(key="display"):
    """Small refrigerated display (banca/contêiner): two tiers behind a glass front."""
    clear(); LANES.pop(key, None)
    W, D = 1.60, 0.90
    body = mat("disp_body", WHITE, rough=.35); inner = mat("disp_in", (0.80, 0.91, 0.97, 1), rough=.6)
    accent = mat("disp_accent", TEAL, rough=.4)
    box("base", (W, D, .70), (0, D / 2, .35), body, bevel=.03)
    box("base_stripe", (W + .004, .004, .08), (0, -.002, .55), accent, bevel=.004, layer="front")
    box("tier", (W - .1, D / 2, .16), (0, D * .75, .78), inner, bevel=.01)
    box("floor", (W - .1, D - .1, .02), (0, D / 2, .71), inner, bevel=0)
    box("back", (W, .05, .45), (0, D - .025, .92), body, bevel=.02)
    box("side_L", (.05, D, .45), (-W / 2 + .025, D / 2, .92), body, bevel=.02)
    box("side_R", (.05, D, .45), (W / 2 - .025, D / 2, .92), body, bevel=.02)
    glass = mat("disp_glass", (.80, .93, .97, 1), rough=.05, alpha=.18)
    g = box("glass_front", (W - .06, .01, .40), (0, .03, .95), glass, bevel=0, layer="front"); g.rotation_euler = (rad(-18), 0, 0)
    box("glass_top", (W - .06, .30, .01), (0, .30, 1.15), glass, bevel=0, layer="front")
    for i, (x0, x1, y0, y1, row) in enumerate(grid_cells(W - .1, D - .1, margin=.03, gap=.04)):
        z = .86 if row == 0 else .72
        lane(key, x0 + .01, x1 - .01, y0 + .06, y1 + .03, z, .13)
    return dict(target=(0, D * .45, .95), pitch=30, dist=2.9, lens=40, size=W)

def build_counter(key="counter"):
    """Service counter of the sectors: steel trays under a curved glass, wooden base."""
    clear(); LANES.pop(key, None)
    W, D = 1.90, 0.95
    wood = mat("ct_wood", WOOD, rough=.6); steel = mat("tray", (0.78, 0.80, 0.80, 1), rough=.25, metal=.8); inner = mat("ct_in", WHITE, rough=.5)
    box("base", (W, D, .78), (0, D / 2, .39), wood, bevel=.03)
    box("base_front", (W + .01, .03, .70), (0, -.01, .40), mat("ct_front", WOOD_L, rough=.55), bevel=.02, layer="front")
    box("deck", (W - .06, D - .06, .03), (0, D / 2, .80), inner, bevel=.01)
    box("tier", (W - .1, D / 2, .12), (0, D * .75, .86), inner, bevel=.01)
    glass = mat("ct_glass", (.82, .93, .97, 1), rough=.05, alpha=.16)
    g = box("glass_front", (W - .06, .01, .45), (0, .05, 1.02), glass, bevel=0, layer="front"); g.rotation_euler = (rad(-25), 0, 0)
    box("glass_top", (W - .06, .35, .01), (0, .40, 1.24), glass, bevel=0, layer="front")
    for i, (x0, x1, y0, y1, row) in enumerate(grid_cells(W - .1, D - .1, margin=.03, gap=.04)):
        z = .93 if row == 0 else .82
        box(f"tray{i}", (x1 - x0, y1 - y0 + .02, .02), ((x0 + x1) / 2, (y0 + y1) / 2 + .05, z), steel, bevel=.008)
        lane(key, x0 + .02, x1 - .02, y0 + .07, y1 + .03, z + .01, .13)
    return dict(target=(0, D * .45, 1.0), pitch=30, dist=3.3, lens=40, size=W)

BUILDERS = {"fridge": build_fridge, "freezer_upright": lambda: build_fridge("freezer_upright", True),
            "gondola": build_gondola, "chest": build_chest, "dairy_open": build_dairy_open,
            "shelf_small": lambda: build_gondola("shelf_small", WOOD_L, WOOD, False, ORANGE),
            "bakery_shelf": lambda: build_gondola("bakery_shelf", CREAM, WOOD_L, False, WOOD),
            "crates": build_crates, "stand": build_stand, "basket": build_basket, "cooler": build_cooler,
            "display": build_display, "counter": build_counter}
VIEWS = {}

HINGES = []   # (empty, sign) of the swing doors of the fixture being built
SWING_OPEN = 72  # degrees of a fully open swing door
def hinge(layer, at, sign):
    """Parents every object of `layer` to an empty on the hinge axis; rotating the empty swings the door."""
    sc = bpy.context.scene
    e = bpy.data.objects.new("hinge_" + layer, None); sc.collection.objects.link(e); e.location = at; e["layer"] = "cam"
    bpy.context.view_layer.update()
    for o in list(sc.collection.all_objects):
        if o.get("layer") == layer and o is not e:
            o.parent = e; o.matrix_parent_inverse = e.matrix_world.inverted()
    HINGES.append((e, sign))
def swing(angle):
    for e, sign in HINGES: e.rotation_euler = (0, 0, rad(angle) * sign)
    bpy.context.view_layer.update()

SLIDE_FRAMES = 4   # frames of a sliding lid (25%, 50%, 75%, 100% open)
def slide_doors(v, t, only=None):
    """Moves every sliding lid to fraction t of its open offset (box() bakes the location into the mesh, so
    the object location is the offset itself)."""
    for d in v.get("doors", []):
        if d.get("kind") != "slide" or (only and d["layer"] != only): continue
        off = Vector(d.get("slide", (0, 0, 0))) * t
        for o in bpy.context.scene.collection.all_objects:
            if o.get("layer") == d["layer"]: o.location = off
    bpy.context.view_layer.update()

def build(key):
    HINGES.clear()
    sc = scene(); v = BUILDERS[key](); VIEWS[key] = v
    camera(v["target"], v["pitch"], v["dist"], v["lens"])
    swing(SWING_OPEN if HINGES else 0); slide_doors(v, 1); fit_camera(v.get("margin", 1.07)); swing(0); slide_doors(v, 0)   # frame the open doors too
    light_rig(v["target"], v["size"])
    return v

def fit_camera(margin=1.07):
    """Frame every mesh (doors included) so nothing is cut, keeping the pitch; then pull back by `margin`."""
    sc = bpy.context.scene; cam = sc.camera; dg = bpy.context.evaluated_depsgraph_get()
    coords = []
    for o in sc.collection.all_objects:
        if o.type != 'MESH' or o.get("layer") in ("light", "cam"): continue
        coords += [c for corner in o.bound_box for c in (o.matrix_world @ Vector(corner))]
    loc, _ = cam.camera_fit_coords(dg, coords)
    pts = [Vector(coords[i:i + 3]) for i in range(0, len(coords), 3)]
    center = sum(pts, Vector()) / len(pts)
    fwd = cam.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    d = (center - Vector(loc)).dot(fwd)
    cam.location = Vector(loc) - fwd * d * (margin - 1)

# ---------------------------------------------------------------- render
def _show(layer_names):
    for o in bpy.context.scene.collection.all_objects:
        lay = o.get("layer", "back")
        if lay in ("light", "cam"): o.hide_render = False; continue
        o.hide_render = lay not in layer_names

def render(key):
    os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene; cam = sc.camera
    layers = [("back", ["back"]), ("front", ["front"])]
    doors = sorted({o.get("layer") for o in sc.collection.all_objects if str(o.get("layer", "")).startswith("door")})
    layers += [(d, [d]) for d in doors]
    paths = {}
    for name, show in layers:
        _show(show); p = os.path.join(OUT, f"fixture_{key}_{name}.png"); sc.render.filepath = p
        bpy.ops.render.render(write_still=True); paths[name] = p
    # swing doors: two more frames per door (half open, open) for the opening animation
    if HINGES:
        for k, ang in ((1, SWING_OPEN * .5), (2, SWING_OPEN)):
            swing(ang)
            for d in doors:
                _show([d]); p = os.path.join(OUT, f"fixture_{key}_{d}_{k}.png"); sc.render.filepath = p
                bpy.ops.render.render(write_still=True); paths[f"{d}_{k}"] = p
        swing(0)
    # sliding lids: frames along the rail, rendered in 3D so the lid keeps the perspective of the top
    v = VIEWS.get(key, {})
    for d in v.get("doors", []):
        if d.get("kind") != "slide" or "slide" not in d: continue
        for k in range(1, SLIDE_FRAMES + 1):
            slide_doors(v, k / SLIDE_FRAMES, d["layer"])
            _show([d["layer"]]); p = os.path.join(OUT, f"fixture_{key}_{d['layer']}_{k}.png"); sc.render.filepath = p
            bpy.ops.render.render(write_still=True); paths[f"{d['layer']}_{k}"] = p
        slide_doors(v, 0, d["layer"])
    _show(["back", "front"] + doors)
    # lanes -> image space
    data = dict(key=key, size=list(RES), lanes=[], doors=VIEWS.get(key, {}).get("doors", []))
    for ln in LANES.get(key, []):
        pts = [world_to_camera_view(sc, cam, Vector(p)) for p in ln["floor"]]
        def ppm(a):
            b = Vector(a) + Vector((0, 0, 1)); pa = world_to_camera_view(sc, cam, Vector(a)); pb = world_to_camera_view(sc, cam, b)
            return (pb.y - pa.y) * RES[1]
        data["lanes"].append(dict(fl=[pts[0].x, pts[0].y], fr=[pts[1].x, pts[1].y], bl=[pts[2].x, pts[2].y], br=[pts[3].x, pts[3].y],
                                  ppmFront=ppm(ln["floor"][0]), ppmBack=ppm(ln["floor"][2]), height=ln["h"], door=ln.get("door", -1)))
    for o in sc.collection.all_objects:
        if o.name in ("sign", "header_face"):
            cs = [world_to_camera_view(sc, cam, o.matrix_world @ Vector(c)) for c in o.bound_box]
            data["sign"] = [min(c.x for c in cs), min(c.y for c in cs), max(c.x for c in cs), max(c.y for c in cs)]
    with open(os.path.join(OUT, f"fixture_{key}.json"), "w") as f: json.dump(data, f, indent=1)
    return paths

def render_all(keys=None):
    for k in keys or BUILDERS:
        build(k); render(k)
