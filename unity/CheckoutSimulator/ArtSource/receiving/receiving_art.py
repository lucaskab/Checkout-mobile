"""receiving_art.py -- Checkout - Supermercado Simulator (Oct 2026)
Props of the RECEIVING mini-game (the stockroom / "deposito" where a supplier delivery is checked in), modelled in 3D
and rendered with a PERSPECTIVE camera (same angle family as ArtSource/restock/restock_art.py: ~14-18 deg top-down).

Outputs (Assets/Resources/CheckoutDesktop/Receiving, PNG transparent unless noted; previews in ArtSource/receiving/render):
  receiving_backdrop.jpg                    1920 x 800 opaque back-room interior with the dock door on the left
  receiving_truck_back/front.png + .json    box truck backed into the dock; "cargo" floor quad + "ppm"
  receiving_rack_back/front.png + .json     pallet rack 2 bays x 3 levels; "slots" (18) + "sign" quad
  receiving_coldroom_back/front.png + .json walk-in cold room; "slots" (6) + "display" quad; strip curtain in front
  box_<variant>.png + box_<variant>_marks.json   512 x 512 box sprites (carton, crate, pack, frozen, tray); "label" rect
  receiving_clipboard.png + .json           600 x 800; "sheet" rect
  stamp_conferido.png                       512 x 512 red rubber stamp imprint
All quads/rects are normalised image coords with the origin at the BOTTOM-LEFT (world_to_camera_view convention,
same as fixture_<key>.json of the restock kit). "ppm" = pixels per metre of height at the FRONT edge of the quad.

    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\receiving\\receiving_art.py", encoding="utf-8").read())
    render_all()          # or build_rack(); render_rack() ...
"""
import bpy, bmesh, math, os, json, random
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\receiving"
OUT = os.path.join(HERE, "render")
GAME = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets\Resources\CheckoutDesktop\Receiving"
RES = (1600, 1000)
SCENE = "ReceivingArt"
rad = math.radians

# Market brand BLUE (HUD #2E8CAE; shadows #1F6F8F; accents #45B7D0), stored linear. The old teal names are kept as
# aliases so every painted-steel part of the kit follows the market blue (user request, Oct 2026).
BLUE = (0.027, 0.272, 0.450, 1); BLUE_D = (0.014, 0.150, 0.275, 1); BLUE_L = (0.059, 0.473, 0.637, 1)
TEAL, TEAL_D, TEAL_L = BLUE, BLUE_D, BLUE_L
CREAM = (0.96, 0.90, 0.74, 1); WHITE = (0.93, 0.93, 0.90, 1); ORANGE = (0.93, 0.45, 0.12, 1)
WOOD = (0.62, 0.38, 0.19, 1); WOOD_L = (0.80, 0.58, 0.33, 1); METAL = (0.62, 0.66, 0.66, 1); DARK = (0.10, 0.11, 0.12, 1)
FROST = (0.80, 0.90, 0.96, 1); YELLOW = (1.0, 0.70, 0.02, 1); CARD = (0.60, 0.40, 0.20, 1); CARD_D = (0.45, 0.28, 0.13, 1)
RED = (0.80, 0.12, 0.10, 1); GREEN = (0.22, 0.58, 0.25, 1); STEEL = (0.78, 0.80, 0.80, 1)

OFF = Vector((0, 0, 0))     # placement offset of the prop being built (used by the composed preview)

# ---------------------------------------------------------------- scene / materials
def scene():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = sc
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.resolution_percentage = 100; sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
    return sc

def clear():
    sc = scene()
    for o in list(sc.objects):
        bpy.data.objects.remove(o, do_unlink=True)

_M = {}
def mat(name, rgb, rough=.55, metal=0., emit=0., alpha=1., transmission=0., bump=.10, scale=60., emit_rgb=None, spec=None):
    """Principled material with a subtle painted-texture bump (noise) so flat faces don't read as CG plastic."""
    if name in _M and _M[name].name in bpy.data.materials: return _M[name]
    m = bpy.data.materials.get("RV_" + name) or bpy.data.materials.new("RV_" + name)
    m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgb; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit: b.inputs["Emission Color"].default_value = emit_rgb or rgb; b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"): m.surface_render_method = 'BLENDED'
    if transmission: b.inputs["Transmission Weight"].default_value = transmission
    if spec is not None and "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = spec
    if bump > 0:
        n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 4; n.inputs["Roughness"].default_value = .6
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = .01
        nt.links.new(n.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        # tiny colour variation: a second, coarser noise darkens the base colour a little
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = scale * .15; n2.inputs["Detail"].default_value = 2
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.inputs["Factor"].default_value = .12
        mx.inputs[6].default_value = rgb; mx.inputs[7].default_value = (rgb[0] * .75, rgb[1] * .75, rgb[2] * .75, 1)
        ramp = nt.nodes.new("ShaderNodeMath"); ramp.operation = 'MULTIPLY'; ramp.inputs[1].default_value = .18
        nt.links.new(n2.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], mx.inputs["Factor"])
        nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    _M[name] = m; return m

def _finish(o, name, m, layer):
    o.name = name
    if m is not None: o.data.materials.append(m)
    o["layer"] = layer
    for p in o.data.polygons: p.use_smooth = True
    return o

def box(name, size, loc, m, bevel=.01, layer="back", seg=3, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=Vector(loc) + OFF, rotation=rot); o = bpy.context.object
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        md = o.modifiers.new("b", 'BEVEL'); md.width = min(bevel, min(size) * .49); md.segments = seg; md.limit_method = 'ANGLE'
    return _finish(o, name, m, layer)

def cyl(name, r, h, loc, m, rot=(0, 0, 0), layer="back", verts=24, bevel=0.):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=Vector(loc) + OFF, rotation=rot, vertices=verts); o = bpy.context.object
    if bevel > 0:
        md = o.modifiers.new("b", 'BEVEL'); md.width = min(bevel, r * .5, h * .49); md.segments = 3; md.limit_method = 'ANGLE'
    return _finish(o, name, m, layer)

def sphere(name, r, loc, m, layer="back", scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=Vector(loc) + OFF, segments=24, ring_count=12); o = bpy.context.object
    o.scale = scale; bpy.ops.object.transform_apply(scale=True)
    return _finish(o, name, m, layer)

def text(name, body, size, loc, m, rot=(0, 0, 0), layer="back", align='CENTER', extrude=0.0, bold=False):
    """A text object lying in its local XY plane (rotate it onto the face it decorates)."""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.align_x = align; cu.align_y = 'CENTER'
    cu.extrude = extrude; cu.offset = .01 * size if bold else 0; cu.resolution_u = 6
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    o.location = Vector(loc) + OFF; o.rotation_euler = rot; o.data.materials.append(m); o["layer"] = layer
    return o

def grid_wire(name, w, d, loc, m, nx=12, ny=6, thick=.006, layer="back"):
    """Welded wire mesh decking: a subdivided plane turned into wire by the Wireframe modifier."""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=nx, y_subdivisions=ny, size=1, location=Vector(loc) + OFF); o = bpy.context.object
    o.scale = (w, d, 1); bpy.ops.object.transform_apply(scale=True)
    md = o.modifiers.new("w", 'WIREFRAME'); md.thickness = thick; md.use_replace = True; md.use_even_offset = False
    return _finish(o, name, m, layer)

def pivot_rot(o, pivot, angle_z):
    """Rotate an object around a vertical axis through `pivot` (world, before OFF)."""
    p = Vector(pivot) + OFF; R = Matrix.Rotation(angle_z, 4, 'Z')
    o.location = p + R @ (o.location - p)
    o.rotation_euler = (R @ o.rotation_euler.to_matrix().to_4x4()).to_euler()

def light_rig(target, size, warm=1.0, world=.35):
    sc = bpy.context.scene
    w = bpy.data.worlds.get("RV_World") or bpy.data.worlds.new("RV_World"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (.85, .88, .92, 1); w.node_tree.nodes["Background"].inputs[1].default_value = world
    def area(n, loc, energy, s, color=(1, .97, .92)):
        bpy.ops.object.light_add(type='AREA', location=loc); l = bpy.context.object; l.name = n
        l.data.energy = energy; l.data.size = s; l.data.color = color
        l.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); l["layer"] = "light"
    t = Vector(target) + OFF
    area("Key", (t[0] - size * 1.2, t[1] - size * 2.2, t[2] + size * 2.0), 120 * size * size * warm, size * 1.5)
    area("Fill", (t[0] + size * 1.6, t[1] - size * 1.6, t[2] + size * .6), 35 * size * size, size * 2, (.92, .95, 1))

def camera(target, pitch_deg, dist, lens=40, yaw_deg=0):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("RV_Cam")
    if not cam:
        cam = bpy.data.objects.new("RV_Cam", bpy.data.cameras.new("RV_Cam")); sc.collection.objects.link(cam)
    cam.data.lens = lens; cam.data.sensor_width = 36; cam.data.clip_end = 200
    p = rad(pitch_deg); y = rad(yaw_deg); t = Vector(target) + OFF
    off = Vector((math.sin(y) * math.cos(p) * dist, -math.cos(y) * math.cos(p) * dist, math.sin(p) * dist))
    cam.location = t + off
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam["layer"] = "cam"
    sc.camera = cam; return cam

def fit_camera(margin=1.07, layers=None):
    """Frame every mesh so nothing is cut, keeping the pitch; then pull back by `margin`."""
    sc = bpy.context.scene; cam = sc.camera; dg = bpy.context.evaluated_depsgraph_get()
    coords = []
    for o in sc.objects:
        if o.type not in ('MESH', 'FONT') or o.get("layer") in ("light", "cam"): continue
        if layers and o.get("layer", "back") not in layers: continue
        coords += [c for corner in o.bound_box for c in (o.matrix_world @ Vector(corner))]
    loc, _ = cam.camera_fit_coords(dg, coords)
    pts = [Vector(coords[i:i + 3]) for i in range(0, len(coords), 3)]
    center = sum(pts, Vector()) / len(pts)
    fwd = cam.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    d = (center - Vector(loc)).dot(fwd)
    cam.location = Vector(loc) - fwd * d * (margin - 1)

def _show(layer_names):
    for o in bpy.context.scene.objects:
        lay = o.get("layer", "back")
        if lay in ("light", "cam"): o.hide_render = False; continue
        o.hide_render = lay not in layer_names

def render_layers(name, layers, res=RES, transparent=True, out=None, also_game=True):
    """Renders each (suffix, [layers]) to OUT/<name>_<suffix>.png and copies to GAME."""
    os.makedirs(OUT, exist_ok=True); os.makedirs(GAME, exist_ok=True)
    sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = res; sc.render.film_transparent = transparent
    paths = []
    for suffix, show in layers:
        _show(show); fn = f"{name}_{suffix}.png" if suffix else f"{name}.png"
        p = os.path.join(OUT, fn); sc.render.filepath = p; bpy.ops.render.render(write_still=True); paths.append(p)
        if also_game:
            import shutil; shutil.copyfile(p, os.path.join(GAME, fn))
    _show(["back", "front"]); sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.film_transparent = True
    return paths

# ---------------------------------------------------------------- projection helpers
def proj(p):
    sc = bpy.context.scene; v = world_to_camera_view(sc, sc.camera, Vector(p)); return [round(v.x, 4), round(v.y, 4)]

def ppm_at(p):
    sc = bpy.context.scene; a = world_to_camera_view(sc, sc.camera, Vector(p)); b = world_to_camera_view(sc, sc.camera, Vector(p) + Vector((0, 0, 1)))
    return round((b.y - a.y) * sc.render.resolution_y, 2)

def quad(x0, x1, y0, y1, z):
    """Floor quad of a place in world coords (OFF applied): front-left, front-right, back-left, back-right."""
    o = OFF
    return dict(fl=proj((x0 + o.x, y0 + o.y, z + o.z)), fr=proj((x1 + o.x, y0 + o.y, z + o.z)), bl=proj((x0 + o.x, y1 + o.y, z + o.z)), br=proj((x1 + o.x, y1 + o.y, z + o.z)),
                ppm=ppm_at((x0 + o.x, y0 + o.y, z + o.z)), ppmBack=ppm_at((x0 + o.x, y1 + o.y, z + o.z)))

def obj_rect(o):
    cs = [world_to_camera_view(bpy.context.scene, bpy.context.scene.camera, o.matrix_world @ Vector(c)) for c in o.bound_box]
    return [round(min(c.x for c in cs), 4), round(min(c.y for c in cs), 4), round(max(c.x for c in cs), 4), round(max(c.y for c in cs), 4)]

def write_json(name, data, also_game=True):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f: json.dump(data, f, indent=1)
    if also_game:
        with open(os.path.join(GAME, name), "w") as f: json.dump(data, f, indent=1)

SLOTS = {}   # key -> list of dict(level, bay, index, x0, x1, y0, y1, z) in local coords (+OFF applied at projection time)
def slot(key, level, bay, index, x0, x1, y0, y1, z):
    SLOTS.setdefault(key, []).append(dict(level=level, bay=bay, index=index, x0=x0, x1=x1, y0=y0, y1=y1, z=z))
def slots_json(key):
    out = []
    for s in SLOTS.get(key, []):
        d = dict(level=s["level"], bay=s["bay"], index=s["index"]); d.update(quad(s["x0"], s["x1"], s["y0"], s["y1"], s["z"])); out.append(d)
    return out

# ---------------------------------------------------------------- 1. backdrop
# Wall front face at y = 0, the room extends toward the camera (y < 0). Dock door opening on the left third.
BD_W, BD_H = 13.0, 5.0
DOCK = dict(x0=-5.0, x1=-2.0, h=2.75)     # opening of the loading dock door

def build_backdrop(full=True):
    """Painted concrete floor with safety stripes, teal plank wainscot, cream upper wall, roll-up dock door (open),
    pendant lamps, extinguisher and the DEPOSITO sign. full=False skips the floor dressing (preview uses full)."""
    concrete = mat("bd_floor", (0.38, 0.37, 0.36, 1), rough=.75, bump=.3, scale=12)
    concrete_d = mat("bd_floor_d", (0.36, 0.36, 0.35, 1), rough=.75, bump=.3, scale=12)
    plank = mat("bd_plank", BLUE, rough=.6, bump=.15); plank_d = mat("bd_plank_d", (0.020, 0.215, 0.365, 1), rough=.6, bump=.15)
    cream = mat("bd_cream", (0.96, 0.87, 0.68, 1), rough=.9, bump=.2, scale=20); rail = mat("bd_rail", (0.50, 0.30, 0.14, 1), rough=.5)
    yellow = mat("bd_yellow", YELLOW, rough=.6, bump=.2, scale=30); black = mat("bd_black", (0.06, 0.06, 0.06, 1), rough=.6, bump=.2, scale=30)
    rubber = mat("bd_rubber", (0.05, 0.05, 0.05, 1), rough=.8); door_m = mat("bd_door", (0.70, 0.72, 0.72, 1), rough=.4, metal=.4)
    sky = mat("bd_sky", (1.0, 0.78, 0.45, 1), emit=2.0, bump=0); ground = mat("bd_ground", (0.55, 0.50, 0.42, 1), rough=.8, bump=.2)
    W, H = BD_W, BD_H; x0, x1, dh = DOCK["x0"], DOCK["x1"], DOCK["h"]
    # floor slabs with faint joints
    s = 2.0
    for i in range(-4, 4):
        for j in range(0, 5):
            box(f"slab{i}_{j}", (s - .01, s - .01, .04), ((i + .5) * s, -(j + .5) * s, -.02), concrete if (i * 3 + j) % 4 else concrete_d, bevel=.008)
    box("subfloor", (W + 2, 10, .02), (0, -5, -.045), concrete_d, bevel=0)
    # safety stripes along the dock edge and the painted staging box
    n = 16
    for k in range(n):
        box(f"stripe{k}", ((x1 - x0 + .4) / n, .32, .006), (x0 - .2 + (k + .5) * (x1 - x0 + .4) / n, -.18, .003), yellow if k % 2 == 0 else black, bevel=0, rot=(0, 0, rad(0)))
    sx0, sx1, sy0, sy1 = x0 - .1, x1 + .9, -2.9, -.5
    for nm, sz, lc in (("stg_f", (sx1 - sx0, .08, .005), ((sx0 + sx1) / 2, sy0, .0025)), ("stg_b", (sx1 - sx0, .08, .005), ((sx0 + sx1) / 2, sy1, .0025)),
                       ("stg_l", (.08, sy1 - sy0, .005), (sx0, (sy0 + sy1) / 2, .0025)), ("stg_r", (.08, sy1 - sy0, .005), (sx1, (sy0 + sy1) / 2, .0025))):
        box(nm, sz, lc, yellow, bevel=0)
    # walls: cream upper, teal planks lower (wainscot up to 1.1 m), chair rail; the dock opening is cut by building pieces
    def wall_piece(nm, xa, xb, za, zb):
        if xb - xa < .01 or zb - za < .01: return
        box(nm, (xb - xa, .25, zb - za), ((xa + xb) / 2, .125, (za + zb) / 2), cream, bevel=.01)
    wall_piece("wall_L", -W / 2, x0, 0, H); wall_piece("wall_R", x1, W / 2, 0, H); wall_piece("wall_T", x0, x1, dh, H)
    pw = .16
    for seg, (xa, xb) in enumerate(((-W / 2, x0 - .06), (x1 + .06, W / 2))):
        k = 0; x = xa
        while x + pw <= xb + .001:
            box(f"plank{seg}_{k}", (pw - .012, .04, .40), (x + pw / 2, -.02, .20), plank if k % 2 else plank_d, bevel=.005)
            box(f"plank{seg}_{k}b", (pw - .012, .04, .62), (x + pw / 2, -.02, .72), plank if k % 2 else plank_d, bevel=.005)
            x += pw; k += 1
        box(f"rail{seg}", (xb - xa, .06, .06), ((xa + xb) / 2, -.03, 1.06), rail, bevel=.012)
        box(f"base{seg}", (xb - xa, .05, .10), ((xa + xb) / 2, -.03, .05), mat("bd_base", (0.30, 0.18, 0.08, 1), rough=.5), bevel=.008)
    # dock opening: frame, rolled-up door drum with ribs, rubber bumpers, outside daylight
    frame = mat("bd_frame", (0.85, 0.84, 0.80, 1), rough=.5, metal=.2)
    box("jamb_L", (.14, .32, dh + .1), (x0 - .07, .14, (dh + .1) / 2), frame, bevel=.02); box("jamb_R", (.14, .32, dh + .1), (x1 + .07, .14, (dh + .1) / 2), frame, bevel=.02)
    box("lintel", (x1 - x0 + .28, .32, .16), ((x0 + x1) / 2, .14, dh + .08), frame, bevel=.02)
    drum = cyl("drum", .20, x1 - x0 + .2, ((x0 + x1) / 2, .12, dh + .34), door_m, rot=(0, rad(90), 0), verts=32)
    for k in range(5):
        cyl(f"drum_rib{k}", .205, .03, (x0 + .25 + k * (x1 - x0 - .5) / 4, .12, dh + .34), mat("bd_door_d", (0.55, 0.57, 0.57, 1), rough=.4, metal=.4), rot=(0, rad(90), 0), verts=32)
    for k in range(5):  # slats of the door still hanging below the drum (the curtain is rolled up, only its edge shows)
        box(f"slat{k}", (x1 - x0 + .1, .03, .07), ((x0 + x1) / 2, .02, dh + .15 - k * .0 + .04 - k * .08 * 0), door_m, bevel=.01) if k == 0 else None
    for side, xs in ((0, x0 + .25), (1, x1 - .25)):
        box(f"bumper{side}", (.32, .14, .45), (xs, .05, .26), rubber, bevel=.03, seg=4)
        for z in (.12, .40):
            cyl(f"bolt{side}_{z:.1f}", .025, .02, (xs, -.025, z), mat("bd_bolt", STEEL, rough=.3, metal=.8), rot=(rad(90), 0, 0), verts=12)
    box("sky", (x1 - x0 + 3, .02, dh + 6), ((x0 + x1) / 2, 6.0, dh / 2), sky, bevel=0)
    box("ground_out", (x1 - x0 + 2, 6, .05), ((x0 + x1) / 2, 3.0, -.03), ground, bevel=0)
    box("leveler", (x1 - x0 - .3, .9, .03), ((x0 + x1) / 2, .55, .0), mat("bd_leveler", (0.45, 0.47, 0.47, 1), rough=.4, metal=.5, bump=.3, scale=40), bevel=.01)
    box("yard_wall", (x1 - x0 + 2, .2, 1.0), ((x0 + x1) / 2, 5.5, .5), mat("bd_yard", (0.62, 0.50, 0.36, 1), rough=.9, bump=.2), bevel=0)
    # pendant lamps: a cone shade with a warm bulb hanging on a rod
    shade = mat("bd_shade", BLUE, rough=.4, metal=.3); bulb = mat("bd_bulb", (1, .92, .75, 1), emit=25, bump=0)
    for k, x in enumerate((-1.3, 3.3)):
        cyl(f"lamp_rod{k}", .012, H - 3.1, (x, -1.0, (H + 3.1) / 2), mat("bd_rod", DARK, rough=.5), verts=10)
        bpy.ops.mesh.primitive_cone_add(radius1=.28, radius2=.06, depth=.26, location=Vector((x, -1.0, 2.97)) + OFF, vertices=32); o = bpy.context.object
        _finish(o, f"lamp_shade{k}", shade, "back")
        md = o.modifiers.new("b", 'BEVEL'); md.width = .01; md.segments = 3; md.limit_method = 'ANGLE'
        sphere(f"lamp_bulb{k}", .07, (x, -1.0, 2.84), bulb)
        bpy.ops.object.light_add(type='POINT', location=Vector((x, -1.0, 2.80)) + OFF); l = bpy.context.object; l.name = f"lamp_light{k}"
        l.data.energy = 450; l.data.color = (1, .85, .65); l.data.shadow_soft_size = .15; l["layer"] = "light"
    # fire extinguisher on the right wall + DEPOSITO sign painted above the wainscot
    ex = 5.3
    box("ext_bracket", (.10, .04, .30), (ex, -.02, 1.55), mat("bd_bracket", DARK, rough=.5), bevel=.008)
    cyl("ext_body", .085, .50, (ex, -.13, 1.38), mat("bd_red", (0.85, 0.10, 0.08, 1), rough=.35, bump=.05), verts=24, bevel=.03)
    cyl("ext_neck", .03, .08, (ex, -.13, 1.66), mat("bd_steel", STEEL, rough=.3, metal=.8), verts=12)
    box("ext_lever", (.03, .12, .025), (ex, -.16, 1.72), mat("bd_steel", STEEL, rough=.3, metal=.8), bevel=.008)
    cyl("ext_hose", .012, .30, (ex + .08, -.19, 1.45), mat("bd_hose", DARK, rough=.7), rot=(rad(12), rad(8), 0), verts=10)
    box("ext_label", (.11, .005, .14), (ex, -.215, 1.36), mat("bd_label", WHITE, rough=.6, bump=0), bevel=.004)
    text("ext_txt", "A B C", .045, (ex, -.219, 1.36), mat("bd_ink", DARK, rough=.8, bump=0), rot=(rad(90), 0, 0))
    text("sign_txt", "DEPÓSITO", .34, (1.2, -.01, 3.45), mat("bd_sign_ink", BLUE_D, rough=.8, bump=0), rot=(rad(90), 0, 0), extrude=.003, bold=True)
    box("sign_under", (2.0, .012, .035), (1.2, -.01, 3.22), mat("bd_sign_or", ORANGE, rough=.7, bump=0), bevel=.01)
    return dict(target=(0.3, -1.5, 1.35), pitch=14, dist=8.0, lens=32, size=2.6)

def render_backdrop():
    clear(); sc = scene(); v = build_backdrop()
    camera(v["target"], v["pitch"], v["dist"], v["lens"]); light_rig(v["target"], v["size"], warm=.38, world=.22)
    sc.render.resolution_x, sc.render.resolution_y = 1920, 800; sc.render.film_transparent = False
    _show(["back", "front"]); p = os.path.join(OUT, "receiving_backdrop.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    sc.render.film_transparent = True; sc.render.resolution_x, sc.render.resolution_y = RES
    img = bpy.data.images.load(p, check_existing=False); img.file_format = 'JPEG'
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.image_settings.quality = 92
    img.save_render(os.path.join(GAME, "receiving_backdrop.jpg"), scene=sc)
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'; bpy.data.images.remove(img)
    return p

# ---------------------------------------------------------------- 2. truck
# Local coords: the rear opening of the cargo box is in the plane y = 0, the box extends to y = +L (outside), the cargo
# floor is at z = 0 (dock height). Rendered from inside the stockroom looking into the open truck.
TRUCK = dict(W=2.45, L=4.2, H=2.35)
def build_truck():
    W, L, H = TRUCK["W"], TRUCK["L"], TRUCK["H"]; t = .06
    body = mat("tk_body", TEAL, rough=.4, bump=.08); body_d = mat("tk_body_d", TEAL_D, rough=.45)
    cream = mat("tk_cream", CREAM, rough=.5); inner = mat("tk_inner", (0.84, 0.86, 0.82, 1), rough=.6, bump=.15)
    rib = mat("tk_rib", (0.72, 0.75, 0.74, 1), rough=.35, metal=.6); plank = mat("tk_plank", WOOD, rough=.65, bump=.2, scale=80); plank_l = mat("tk_plank_l", WOOD_L, rough=.65, bump=.2, scale=80)
    steel = mat("tk_steel", (0.70, 0.72, 0.72, 1), rough=.3, metal=.8); rubber = mat("tk_rubber", (0.06, 0.06, 0.06, 1), rough=.85, bump=.2)
    orange = mat("tk_refl", (1.0, 0.45, 0.05, 1), rough=.2, emit=.6); red = mat("tk_tail", (0.9, 0.08, 0.05, 1), rough=.2, emit=.5); amber = mat("tk_amber", (1.0, 0.6, 0.1, 1), rough=.2, emit=1.0)
    # cargo box: floor, side walls, roof, front wall (deep inside), inner ribs and wooden plank floor
    box("tk_floor", (W, L, .14), (0, L / 2, -.07), body_d, bevel=.02)
    nplk = 9; pw = (W - 2 * t - .04) / nplk
    for k in range(nplk):
        box(f"tk_plk{k}", (pw - .012, L - .2, .03), (-W / 2 + t + .02 + (k + .5) * pw, L / 2 + .05, .015), plank if k % 3 else plank_l, bevel=.006)
    box("tk_sill", (W - 2 * t, .08, .05), (0, .04, .015), steel, bevel=.012)
    for sx in (-1, 1):
        box(f"tk_wall{sx}", (t, L, H), (sx * (W / 2 - t / 2), L / 2, H / 2), body, bevel=.02)
        box(f"tk_stripe{sx}", (.012, L - .4, .18), (sx * (W / 2 + .003), L / 2 + .1, 1.05), cream, bevel=.004)
        for k in range(6):
            box(f"tk_rib{sx}_{k}", (.03, .05, H - .3), (sx * (W / 2 - t - .015), .45 + k * (L - .8) / 5, H / 2 - .05), rib, bevel=.008)
    box("tk_roof", (W, L, t), (0, L / 2, H - t / 2), body, bevel=.02)
    box("tk_roof_in", (W - 2 * t, L - .1, .01), (0, L / 2, H - t - .005), inner, bevel=0)
    box("tk_front", (W - 2 * t, .05, H - t), (0, L - .05, H / 2 - .02), inner, bevel=.01)
    for sx in (-1, 1):
        box(f"tk_wall_in{sx}", (.012, L - .1, H - .2), (sx * (W / 2 - t - .006), L / 2, H / 2 - .05), inner, bevel=0)
    # rear frame: the box edge around the opening (teal), top marker lights, the rear corner posts with hinges
    box("tk_frame_T", (W + .02, .10, .14), (0, .05, H - .07), body, bevel=.025)
    for sx in (-1, 1):
        box(f"tk_post{sx}", (.10, .10, H + .1), (sx * (W / 2 - .04), .05, H / 2 - .05), body, bevel=.025)
        for z in (.45, 1.25, 2.05):
            box(f"tk_hinge{sx}_{z:.1f}", (.05, .06, .14), (sx * (W / 2 + .02), -.02, z), steel, bevel=.012)
    for k in range(5):
        x = -W / 2 + .3 + k * (W - .6) / 4
        box(f"tk_marker{k}", (.10, .03, .05), (x, -.012, H - .05), amber if k in (0, 4) else orange, bevel=.012, seg=4)
    # dock seal: black foam pads hugging the box (the wall is at y = 0)
    for nm, sz, lc in (("tk_seal_T", (W + .7, .30, .28), (0, .16, H + .12)), ("tk_seal_L", (.28, .30, H + .4), (-W / 2 - .22, .16, H / 2 + .05)), ("tk_seal_R", (.28, .30, H + .4), (W / 2 + .22, .16, H / 2 + .05))):
        box(nm, sz, lc, rubber, bevel=.05, seg=4)
        box(nm + "_strp", (sz[0] + .004, .02, .08) if sz[0] > 1 else (.08, .02, sz[2] + .004), (lc[0], lc[1] - sz[1] / 2 - .005, lc[2]), mat("tk_seal_strp", YELLOW, rough=.6), bevel=.006)
    # the swing doors, open ~105 deg toward the viewer (front layer, they can overlap boxes near the sides)
    dw = W / 2 - .025; dh = H - .18
    for sx in (-1, 1):
        hx = sx * (W / 2 - .01); xc = sx * (dw / 2 + .01)
        parts = [box(f"tk_door{sx}", (dw - .02, .05, dh), (xc, -.03, dh / 2 + .02), body, bevel=.02, layer="front"),
                 box(f"tk_door_strp{sx}", (dw - .14, .012, .18), (xc, .002, 1.05), cream, bevel=.004, layer="front"),
                 box(f"tk_door_panel{sx}", (dw - .16, .012, dh * .32), (xc, .002, dh * .72), body_d, bevel=.01, layer="front"),
                 box(f"tk_refl{sx}", (.16, .012, .06), (xc, .002, .30), orange, bevel=.01, layer="front"),
                 box(f"tk_bar{sx}", (.03, .04, dh - .3), (xc + sx * .35, .017, dh / 2), steel, bevel=.008, layer="front"),
                 box(f"tk_hdl{sx}", (.04, .05, .22), (xc + sx * .35, .03, 1.0), steel, bevel=.01, layer="front")]
        for o in parts: pivot_rot(o, (hx, -.0, 0), rad(-100 if sx < 0 else 100))
    # bumper, tail lights, plate (front layer: under the floor edge, in front of the boxes' feet)
    box("tk_bumper", (W + .1, .12, .14), (0, -.03, -.25), steel, bevel=.03, seg=4)
    o = box("tk_bumper_f", (W + .1, .12, .14), (0, -.03, -.25), steel, bevel=.03, seg=4, layer="front"); o.hide_render = True
    for sx in (-1, 1):
        box(f"tk_tail{sx}", (.28, .05, .10), (sx * (W / 2 - .28), -.085, -.25), red, bevel=.02, seg=4, layer="front")
        box(f"tk_tail_a{sx}", (.10, .05, .10), (sx * (W / 2 - .50), -.085, -.25), amber, bevel=.02, seg=4, layer="front")
    box("tk_plate", (.36, .02, .12), (0, -.10, -.25), mat("tk_plate", (0.92, 0.92, 0.88, 1), rough=.5, bump=0), bevel=.006, layer="front")
    text("tk_plate_txt", "CKT 2026", .06, (0, -.112, -.25), mat("tk_ink", DARK, rough=.8, bump=0), rot=(rad(90), 0, 0), layer="front")
    return dict(target=(0, L * .3, H * .5), pitch=16, dist=6.8, lens=40, size=H)

def cargo_quad():
    W, L = TRUCK["W"], TRUCK["L"]
    return quad(-W / 2 + .14, W / 2 - .14, .14, L - .25, .03)

def render_truck():
    clear(); sc = scene(); v = build_truck()
    camera(v["target"], v["pitch"], v["dist"], v["lens"]); fit_camera(1.04); light_rig(v["target"], v["size"], warm=.7, world=.3)
    paths = render_layers("receiving_truck", [("back", ["back"]), ("front", ["front"])])
    q = cargo_quad()
    write_json("receiving_truck.json", dict(key="truck", size=list(RES), cargo=dict(fl=q["fl"], fr=q["fr"], bl=q["bl"], br=q["br"]), ppm=q["ppm"], ppmBack=q["ppmBack"], boxHeight=.5))
    return paths

# ---------------------------------------------------------------- 3. pallet rack
RACK = dict(BW=1.35, D=1.0, H=2.2, levels=(.16, .80, 1.44), post=.09)
def build_rack(key="rack"):
    BW, D, H, post = RACK["BW"], RACK["D"], RACK["H"], RACK["post"]; SLOTS.pop(key, None)
    up = mat("rk_upright", TEAL, rough=.45, bump=.08); up_d = mat("rk_upright_d", TEAL_D, rough=.5)
    beam = mat("rk_beam", (1.0, 0.40, 0.04, 1), rough=.45, bump=.08); mesh_m = mat("rk_mesh", (0.72, 0.74, 0.72, 1), rough=.35, metal=.7, bump=0)
    plate = mat("rk_plate", (0.55, 0.58, 0.58, 1), rough=.4, metal=.6); bolt = mat("rk_bolt", (0.80, 0.82, 0.82, 1), rough=.3, metal=.9, bump=0)
    hole = mat("rk_hole", (0.01, 0.06, 0.06, 1), rough=.9, bump=0); label = mat("rk_label", WHITE, rough=.5, bump=0)
    xs = [-BW - post, 0, BW + post]   # upright frames (centre x)
    for i, x in enumerate(xs):
        for j, y in enumerate((post / 2, D - post / 2)):
            lay = "front" if j == 0 else "back"
            box(f"rk_post{i}{j}", (post, post, H), (x, y, H / 2), up, bevel=.012, layer=lay)
            box(f"rk_base{i}{j}", (post + .08, post + .06, .014), (x, y, .007), plate, bevel=.004, layer=lay)
            for sx in (-1, 1):
                cyl(f"rk_bolt{i}{j}{sx}", .014, .012, (x + sx * (post / 2 + .03), y, .018), bolt, verts=10, bevel=.003, layer=lay)
            if j == 0:
                for k in range(int((H - .2) / .11)):
                    box(f"rk_hole{i}_{k}", (.022, .006, .036), (x, -.001, .14 + k * .11), hole, bevel=0, layer=lay)
        for k, z in enumerate((.6, 1.4, 2.2)):   # frame bracing between the front and the back post
            box(f"rk_brace{i}_{k}", (post * .5, D - post, post * .5), (x, D / 2, z), up_d, bevel=.008)
    for lv, z in enumerate(RACK["levels"]):
        for b in range(2):
            xc = (xs[b] + xs[b + 1]) / 2; w = BW - .01
            box(f"rk_beamF{lv}{b}", (w, .05, .10), (xc, .025, z - .05), beam, bevel=.012, layer="front")
            box(f"rk_labelF{lv}{b}", (w - .2, .008, .036), (xc, -.004, z - .055), label, bevel=.003, layer="front")
            box(f"rk_beamB{lv}{b}", (w, .05, .10), (xc, D - .025, z - .05), beam, bevel=.012)
            grid_wire(f"rk_deck{lv}{b}", w - .02, D - .10, (xc, D / 2, z + .004), mesh_m, nx=14, ny=8, thick=.007)
            for sup in (-1, 0, 1):
                box(f"rk_sup{lv}{b}{sup}", (.03, D - .1, .025), (xc + sup * w * .32, D / 2, z - .01), beam, bevel=.006)
            sw = (w - .06) / 3
            for k in range(3):
                x0 = xc - w / 2 + .03 + k * sw
                slot(key, lv, b, k, x0 + .02, x0 + sw - .02, .06, D - .06, z + .01)
    # the zone sign: a cream board on two short posts above the rack
    for x in (-BW * .5, BW * .5):
        box(f"rk_signpost{x:.1f}", (.04, .04, .30), (x, D / 2, H + .15), up_d, bevel=.008)
    box("rk_sign_bd", (1.9, .035, .42), (0, D / 2, H + .40), up, bevel=.02)
    sg = box("rk_sign", (1.78, .012, .32), (0, D / 2 - .022, H + .40), mat("rk_sign", CREAM, rough=.5, emit=.4, bump=0), bevel=.006)
    return dict(target=(0, D * .35, H * .5), pitch=15, dist=6.0, lens=40, size=H, sign=sg)

def render_rack():
    clear(); sc = scene(); v = build_rack()
    camera(v["target"], v["pitch"], v["dist"], v["lens"]); fit_camera(1.04); light_rig(v["target"], v["size"], warm=.55, world=.28)
    paths = render_layers("receiving_rack", [("back", ["back"]), ("front", ["front"])])
    write_json("receiving_rack.json", dict(key="rack", size=list(RES), slots=slots_json("rack"), sign=obj_rect(v["sign"]), boxHeight=.42))
    return paths

# ---------------------------------------------------------------- 4. cold room
COLD = dict(W=2.4, D=1.6, H=2.4, ow=1.7, oh=2.0, levels=(.40, 1.22))
def build_coldroom(key="coldroom"):
    W, D, H, ow, oh = COLD["W"], COLD["D"], COLD["H"], COLD["ow"], COLD["oh"]; SLOTS.pop(key, None); t = .10
    panel = mat("cr_panel", (0.95, 0.96, 0.95, 1), rough=.45, bump=.06); trim = mat("cr_trim", (0.80, 0.82, 0.83, 1), rough=.25, metal=.9, bump=0)
    inner = mat("cr_inner", (0.80, 0.90, 0.95, 1), rough=.55, bump=.08); shelf = mat("cr_shelf", (0.76, 0.78, 0.78, 1), rough=.3, metal=.8, bump=0)
    frost = mat("cr_frost", (0.92, 0.97, 1.0, 1), rough=.9, bump=.4, scale=90); strip = mat("cr_strip", (0.62, 0.84, 0.98, 1), rough=.3, alpha=.22, bump=.0, spec=.15)
    disp = mat("cr_disp", (0.03, 0.04, 0.05, 1), rough=.3, bump=0); led = mat("cr_led", (0.15, 1.0, 0.35, 1), emit=6, bump=0)
    # insulated panels: side walls, roof, back wall, floor; the front wall has the opening
    box("cr_side_L", (t, D, H), (-W / 2 + t / 2, D / 2, H / 2), panel, bevel=.03, seg=4)
    box("cr_side_R", (t, D, H), (W / 2 - t / 2, D / 2, H / 2), panel, bevel=.03, seg=4)
    box("cr_roof", (W, D, t), (0, D / 2, H - t / 2), panel, bevel=.03, seg=4)
    box("cr_back", (W - 2 * t, .06, H - t), (0, D - .03, (H - t) / 2), inner, bevel=.01)
    box("cr_inL", (.02, D - .1, H - t), (-W / 2 + t + .01, D / 2, (H - t) / 2), inner, bevel=0)
    box("cr_inR", (.02, D - .1, H - t), (W / 2 - t - .01, D / 2, (H - t) / 2), inner, bevel=0)
    box("cr_ceil", (W - 2 * t, D - .1, .02), (0, D / 2, H - t - .01), inner, bevel=0)
    box("cr_floor", (W, D, .06), (0, D / 2, .03), mat("cr_floor", (0.55, 0.58, 0.60, 1), rough=.5, metal=.3, bump=.3, scale=50), bevel=.01)
    box("cr_led_in", (W - 2 * t - .3, .05, .02), (0, .3, H - t - .025), mat("cr_lamp", (.85, .95, 1, 1), emit=10, bump=0), bevel=0)
    # front wall pieces around the opening, stainless trim around it, frost on the edges
    sx = (W - ow) / 2
    box("cr_front_L", (sx, t, H), (-W / 2 + sx / 2, t / 2 - .02, H / 2), panel, bevel=.03, seg=4, layer="front")
    box("cr_front_R", (sx, t, H), (W / 2 - sx / 2, t / 2 - .02, H / 2), panel, bevel=.03, seg=4, layer="front")
    box("cr_front_T", (ow + .02, t, H - oh), (0, t / 2 - .02, oh + (H - oh) / 2), panel, bevel=.03, seg=4, layer="front")
    for nm, sz, lc in (("cr_trim_L", (.05, .05, oh + .05), (-ow / 2 - .025, -.045, oh / 2)), ("cr_trim_R", (.05, .05, oh + .05), (ow / 2 + .025, -.045, oh / 2)), ("cr_trim_T", (ow + .1, .05, .06), (0, -.045, oh + .03))):
        box(nm, sz, lc, trim, bevel=.012, layer="front")
    box("cr_kick", (W, .04, .12), (0, -.04, .06), trim, bevel=.01, layer="front")
    rnd = random.Random(7)
    for k in range(16):   # frost crystals creeping in at the edges of the opening
        side = -1 if k % 2 else 1; z = rnd.uniform(.1, oh - .1); r = rnd.uniform(.03, .06)
        sphere(f"cr_frost{k}", r, (side * (ow / 2 + .02) - side * r * .3, -.02, z), frost, layer="front", scale=(1, .35, 1.6))
    for k in range(6):
        x = -ow / 2 + .15 + k * (ow - .3) / 5; r = rnd.uniform(.04, .08)
        sphere(f"cr_frostT{k}", r, (x, -.02, oh - .01), frost, layer="front", scale=(1.3, .5, 1))
    # PVC strip curtain: overlapping translucent strips hanging from a rail (front layer)
    box("cr_rail", (ow + .06, .06, .05), (0, -.10, oh + .01), trim, bevel=.01, layer="front")
    n = 9; sw = (ow + .04) / n * 1.18
    for k in range(n):
        x = -ow / 2 - .02 + (k + .5) * (ow + .04) / n
        box(f"cr_strip{k}", (sw, .006, oh - .08), (x, -.10 - (.012 if k % 2 else 0), (oh - .08) / 2 + .03), strip, bevel=.003, layer="front")
    # digital thermometer on the right front panel
    box("cr_disp_box", (.26, .04, .16), (W / 2 - sx / 2, -.03, oh - .25), mat("cr_disp_case", (0.85, 0.86, 0.86, 1), rough=.3, metal=.5, bump=0), bevel=.012, layer="front")
    dsp = box("cr_display", (.20, .01, .09), (W / 2 - sx / 2, -.052, oh - .24), disp, bevel=.004, layer="front")
    text("cr_disp_txt", "-2°C", .065, (W / 2 - sx / 2, -.059, oh - .24), led, rot=(rad(90), 0, 0), layer="front")
    # inside: two levels of stainless wire shelving with 3 places each
    iw = W - 2 * t - .14; sd = D - .40
    for lv, z in enumerate(COLD["levels"]):
        grid_wire(f"cr_deck{lv}", iw, sd, (0, D / 2 + .08, z), shelf, nx=18, ny=8, thick=.007)
        for yy in (D / 2 + .08 - sd / 2, D / 2 + .08 + sd / 2):
            box(f"cr_shelf_edge{lv}{yy:.1f}", (iw, .03, .035), (0, yy, z - .012), shelf, bevel=.008)
        for sxx in (-1, 1):
            for yy in (D / 2 + .08 - sd / 2 + .02, D / 2 + .08 + sd / 2 - .02):
                cyl(f"cr_leg{lv}{sxx}{yy:.1f}", .016, z, (sxx * (iw / 2 - .02), yy, z / 2), shelf, verts=12)
        slw = (iw - .08) / 3
        for k in range(3):
            x0 = -iw / 2 + .04 + k * slw
            slot(key, lv, 0, k, x0 + .02, x0 + slw - .02, D / 2 + .08 - sd / 2 + .05, D / 2 + .08 + sd / 2 - .05, z + .01)
    return dict(target=(0, D * .3, H * .5), pitch=15, dist=6.0, lens=40, size=H, display=dsp)

def render_coldroom():
    clear(); sc = scene(); v = build_coldroom()
    camera(v["target"], v["pitch"], v["dist"], v["lens"]); fit_camera(1.04); light_rig(v["target"], v["size"], warm=.55, world=.28)
    paths = render_layers("receiving_coldroom", [("back", ["back"]), ("front", ["front"])])
    write_json("receiving_coldroom.json", dict(key="coldroom", size=list(RES), slots=slots_json("coldroom"), display=obj_rect(v["display"]), boxHeight=.42))
    return paths

# ---------------------------------------------------------------- 5. box sprites (512 x 512, each rendered alone)
# Every box stands on z = 0, centred on x = y = 0, the front face toward -y. Builders return dict(label=<object whose
# projected bounds are the "label" mark>, size=(W, D, H)).
BOX_RES = (512, 512); BOX_VIEW = dict(pitch=18, yaw=28, lens=45)

def arrow(nm, x, y, z, m, h=.07, layer="back"):
    """A printed 'this way up' arrow on a face at y (the face looks toward -y)."""
    box(nm + "_s", (.009, .002, h), (x, y, z), m, bevel=0, layer=layer)
    box(nm + "_l", (.009, .002, h * .5), (x - h * .16, y, z + h * .34), m, bevel=0, layer=layer, rot=(0, rad(45), 0))
    box(nm + "_r", (.009, .002, h * .5), (x + h * .16, y, z + h * .34), m, bevel=0, layer=layer, rot=(0, rad(-45), 0))

def build_box_carton():
    W, D, H = .50, .40, .40
    card = mat("bx_card", CARD, rough=.8, bump=.22, scale=120); card_d = mat("bx_card_d", CARD_D, rough=.85, bump=.2, scale=120)
    tape = mat("bx_tape", (0.66, 0.46, 0.24, 1), rough=.25, bump=.04, alpha=.9); ink = mat("bx_ink", (0.12, 0.10, 0.10, 1), rough=.8, bump=0)
    white = mat("bx_label", (0.96, 0.96, 0.94, 1), rough=.6, bump=0)
    box("bx_body", (W, D, H - .03), (0, 0, (H - .03) / 2), card, bevel=.012, seg=4)
    for sx in (-1, 1):   # top flaps meeting in the middle, slightly uneven
        box(f"bx_flap{sx}", (W / 2 - .004, D, .03), (sx * W / 4, 0, H - .015 + (.004 if sx > 0 else 0)), card, bevel=.008)
        box(f"bx_flap_edge{sx}", (.006, D - .01, .022), (sx * .004, 0, H - .015), card_d, bevel=0)
    box("bx_tape_top", (.07, D + .004, .006), (0, 0, H + .002), tape, bevel=.002)
    box("bx_tape_front", (.07, .006, .12), (0, -D / 2 - .002, H - .06), tape, bevel=.002)
    box("bx_tape_back", (.07, .006, .12), (0, D / 2 + .002, H - .06), tape, bevel=.002)
    lab = box("bx_label", (.20, .006, .14), (W * .14, -D / 2 - .003, H * .50), white, bevel=.003)
    text("bx_fragil", "FRÁGIL", .038, (-W * .30, -D / 2 - .004, H * .62), ink, rot=(rad(90), 0, 0), bold=True)
    arrow("bx_arr0", -W * .34, -D / 2 - .002, H * .36, ink); arrow("bx_arr1", -W * .24, -D / 2 - .002, H * .36, ink)
    text("bx_side", "CHECKOUT", .030, (W / 2 + .004, .02, H * .55), ink, rot=(rad(90), 0, rad(90)))
    box("bx_dent", (.10, .006, .05), (-W * .30, D / 2 - .002, H * .25), card_d, bevel=.004)   # a scuffed patch on the back face
    return dict(label=lab, size=(W, D, H))

def wood_mat(name, rgb, rgb2, rough=.62, grain=(1.0, 22.0, 22.0), bump=.14):
    """Pine board material: a noise stretched along the board (object X by default) blends two tones into a wood grain."""
    m = mat(name, rgb, rough=rough, bump=bump, scale=70)
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = grain
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 2.2; n.inputs["Detail"].default_value = 6; n.inputs["Roughness"].default_value = .55
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    rmp = nt.nodes.new("ShaderNodeValToRGB"); rmp.color_ramp.elements[0].position = .38; rmp.color_ramp.elements[1].position = .62
    rmp.color_ramp.elements[0].color = rgb; rmp.color_ramp.elements[1].color = rgb2
    nt.links.new(n.outputs["Fac"], rmp.inputs["Fac"]); nt.links.new(rmp.outputs["Color"], b.inputs["Base Color"])
    return m

def build_box_crate():
    """Caixote de feira: light pine slats with gaps nailed onto darker corner posts, tomatoes/limes/oranges inside."""
    W, D, H = .52, .36, .30; t = .018
    PINE, PINE2 = (0.88, 0.63, 0.33, 1), (0.60, 0.38, 0.16, 1)
    pine_x = wood_mat("bx_pine_x", PINE, PINE2); pine_y = wood_mat("bx_pine_y", PINE, PINE2, grain=(22.0, 1.0, 22.0))
    post_m = wood_mat("bx_post", (0.40, 0.22, 0.09, 1), (0.27, 0.14, 0.05, 1), grain=(18.0, 18.0, 1.0))
    floor_m = wood_mat("bx_pine_f", (0.72, 0.52, 0.28, 1), (0.56, 0.37, 0.17, 1), grain=(1.0, 20.0, 20.0))
    nail = mat("bx_nail", (0.45, 0.46, 0.46, 1), rough=.35, metal=.9, bump=0)
    tomato = mat("bx_tomato", (0.85, 0.09, 0.05, 1), rough=.3, bump=.05); lime = mat("bx_lime", (0.36, 0.66, 0.10, 1), rough=.4, bump=.1)
    orange = mat("bx_orange", (1.0, 0.38, 0.03, 1), rough=.45, bump=.15, scale=200)
    tag = mat("bx_tag", (0.98, 0.97, 0.93, 1), rough=.7, bump=0); ink = mat("bx_stencil", (0.12, 0.34, 0.16, 1), rough=.9, bump=0)
    pw = .035; px, py = W / 2 - t - pw / 2, D / 2 - t - pw / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"bx_cr_post{sx}{sy}", (pw, pw, H - .01), (sx * px, sy * py, (H - .01) / 2), post_m, bevel=.004)
    for k in range(5):   # floor slats resting on the lowest boards
        box(f"bx_cr_floor{k}", (W - 2 * t - .01, (D - 2 * t - .02) / 5 - .012, .016), (0, -(D - 2 * t - .02) / 2 + ((D - 2 * t - .02) / 5) * (k + .5), .035), floor_m, bevel=.003)
    zs = (.045, .135, .235); bh = .062
    for k, z in enumerate(zs):
        for sy in (-1, 1):   # long boards (grain along x) nailed over the posts; the top one is split by a hand hole
            y = sy * (D / 2 - t / 2)
            if k == 2:
                for sx in (-1, 1): box(f"bx_cr_bdY{sy}{k}{sx}", ((W - .11) / 2, t, bh), (sx * (W / 4 + .0275), y, z), pine_x, bevel=.003)
            else:
                box(f"bx_cr_bdY{sy}{k}", (W, t, bh), (0, y, z), pine_x, bevel=.003)
            for sx in (-1, 1):
                for dz in (-.016, .016):
                    cyl(f"bx_cr_nail{sy}{k}{sx}{dz:+.3f}", .0045, .004, (sx * px, y - sy * t / 2 - sy * .001, z + dz), nail, rot=(rad(90), 0, 0), verts=10)
        for sx in (-1, 1):   # short boards (grain along y) between the long boards
            box(f"bx_cr_bdX{sx}{k}", (t, D - 2 * t - .004, bh), (sx * (W / 2 - t / 2), 0, z), pine_y, bevel=.003)
            for sy in (-1, 1):
                cyl(f"bx_cr_nailX{sx}{k}{sy}", .0045, .004, (sx * (W / 2 + .001), sy * py, z), nail, rot=(0, rad(90), 0), verts=10)
    rnd = random.Random(11)
    for k in range(14):
        x = (-W / 2 + .07) + (W - .14) * (k % 4 + .5) / 4 + rnd.uniform(-.02, .02); y = (-D / 2 + .07) + (D - .14) * ((k // 4) % 3 + .5) / 3 + rnd.uniform(-.02, .02)
        z = .20 + (0.04 if k >= 12 else 0); rr = rnd.uniform(.045, .06)
        sphere(f"bx_fruit{k}", rr, (x, y, z + rr * .4), (tomato, lime, orange)[k % 3], scale=(1, 1, .9))
    for k in range(3):
        sphere(f"bx_fruit_top{k}", .05, (-.12 + k * .12, rnd.uniform(-.04, .04), .29), (orange, lime, tomato)[k], scale=(1, 1, .9))
    text("bx_stencil", "HORTIFRUTI", .030, (-W * .10, -D / 2 - .001, zs[1]), ink, rot=(rad(90), 0, 0), bold=True)
    lab = box("bx_cr_tag", (.15, .004, .056), (W * .21, -D / 2 - .003, zs[2]), tag, bevel=.002)
    for sx in (-1, 1): box(f"bx_cr_staple{sx}", (.012, .003, .004), (W * .21 + sx * .062, -D / 2 - .006, zs[2] + .022), nail, bevel=0)
    return dict(label=lab, size=(W, D, H))

def build_box_pack():
    W, D, H = .50, .34, .34
    amber = mat("bx_amber", (0.28, 0.11, 0.02, 1), rough=.08, bump=0); cap = mat("bx_cap", (0.93, 0.93, 0.90, 1), rough=.4, bump=0)
    wrap = mat("bx_wrap", (0.80, 0.90, 1.0, 1), rough=.3, alpha=.14, bump=0, spec=.12); sleeve = mat("bx_sleeve", CARD, rough=.8, bump=.2, scale=120)
    white = mat("bx_label", (0.96, 0.96, 0.94, 1), rough=.6, bump=0); hole = mat("bx_hole", (0.2, 0.22, 0.24, 1), rough=.6, bump=0, alpha=.7)
    for i in range(3):
        for j in range(2):
            x = -W / 2 + .085 + i * .165; y = -D / 2 + .085 + j * .17
            cyl(f"bx_bt{i}{j}", .07, .24, (x, y, .12), amber, verts=20, bevel=.02)
            cyl(f"bx_bt_neck{i}{j}", .035, .06, (x, y, .27), amber, verts=16)
            cyl(f"bx_bt_cap{i}{j}", .038, .025, (x, y, .305), cap, verts=16, bevel=.004)
            box(f"bx_bt_lbl{i}{j}", (.10, .006, .09), (x, y - .07, .13), white, bevel=.003)
    box("bx_sleeve", (W + .01, D + .01, .13), (0, 0, .065), sleeve, bevel=.01)
    lab = box("bx_pk_label", (.30, .006, .09), (0, -D / 2 - .008, .065), white, bevel=.003)
    box("bx_wrap", (W + .02, D + .02, H), (0, 0, H / 2), wrap, bevel=.03, seg=4)
    box("bx_handle", (.12, .03, .006), (0, 0, H + .003), hole, bevel=.003)
    return dict(label=lab, size=(W, D, H))

def build_box_frozen():
    W, D, H = .46, .36, .34
    wax = mat("bx_wax", (0.95, 0.96, 0.95, 1), rough=.35, bump=.06); blue = mat("bx_blue", (0.08, 0.32, 0.78, 1), rough=.4, bump=.06)
    snow = mat("bx_snow", (1, 1, 1, 1), rough=.6, bump=0); frost = mat("bx_frost", (0.93, 0.97, 1.0, 1), rough=.9, bump=.4, scale=200)
    white = mat("bx_label", (0.96, 0.96, 0.94, 1), rough=.6, bump=0)
    box("bx_fz_body", (W, D, H), (0, 0, H / 2), wax, bevel=.012, seg=4)
    box("bx_fz_band", (W + .004, D + .004, .11), (0, 0, .11), blue, bevel=.004)
    def flake(nm, x, y, z, r, rot_face):
        for k in range(3):
            box(f"{nm}_{k}", (.008, .002, r * 2), (x, y - k * .0012, z), snow, bevel=0, rot=(0, rad(k * 60), 0))
    for k, x in enumerate((-.15, -.05, .05, .15)):
        flake(f"bx_fk{k}", x, -D / 2 - .003, .11, .03, 'front')
    for k, y in enumerate((-.10, 0, .10)):
        for j in range(3):
            box(f"bx_fks{k}_{j}", (.002, .008, .06), (W / 2 + .003 + j * .0012, y, .11), snow, bevel=0, rot=(rad(j * 60), 0, 0))
    lab = box("bx_fz_label", (.26, .006, .10), (0, -D / 2 - .003, .25), white, bevel=.003)
    rnd = random.Random(5)
    for k in range(10):
        x = rnd.uniform(-W / 2, W / 2); y = -D / 2 if k % 2 else rnd.uniform(-D / 2, D / 2); x = x if k % 2 else (W / 2 if k % 4 == 0 else -W / 2)
        sphere(f"bx_fz_frost{k}", rnd.uniform(.012, .022), (x, y, H - .004), frost, scale=(1.3, 1.3, .35))
    return dict(label=lab, size=(W, D, H))

def build_box_tray():
    W, D, H = .50, .38, .13
    card = mat("bx_card", CARD, rough=.8, bump=.22, scale=120); lid = mat("bx_lid", (0.80, 0.92, 1.0, 1), rough=.3, alpha=.12, bump=0, spec=.12)
    egg = mat("bx_egg", (0.95, 0.86, 0.68, 1), rough=.5, bump=.05); white = mat("bx_label", (0.96, 0.96, 0.94, 1), rough=.6, bump=0)
    box("bx_tr_floor", (W, D, .02), (0, 0, .01), card, bevel=.004)
    for sy in (-1, 1): box(f"bx_tr_wY{sy}", (W, .02, .11), (0, sy * (D / 2 - .01), .065), card, bevel=.006)
    for sx in (-1, 1): box(f"bx_tr_wX{sx}", (.02, D - .04, .11), (sx * (W / 2 - .01), 0, .065), card, bevel=.006)
    for i in range(4):
        for j in range(3):
            sphere(f"bx_egg{i}{j}", .048, (-W / 2 + .07 + i * .12, -D / 2 + .065 + j * .125, .085), egg, scale=(1, 1, 1.25))
    box("bx_tr_lid", (W + .01, D + .01, .08), (0, 0, .15), lid, bevel=.02, seg=4)
    box("bx_tr_rim", (W + .02, D + .02, .015), (0, 0, .118), mat("bx_rim", CREAM, rough=.5, bump=0), bevel=.005)
    lab = box("bx_tr_label", (.22, .006, .07), (0, -D / 2 - .003, .065), white, bevel=.003)
    return dict(label=lab, size=(W, D, H + .07))

BOXES = {"carton": build_box_carton, "crate": build_box_crate, "pack": build_box_pack, "frozen": build_box_frozen, "tray": build_box_tray}

def render_box(name):
    clear(); sc = scene(); v = BOXES[name]()
    W, D, H = v["size"]
    camera((0, 0, H * .45), BOX_VIEW["pitch"], 2.2, BOX_VIEW["lens"], yaw_deg=BOX_VIEW["yaw"])
    sc.render.resolution_x, sc.render.resolution_y = BOX_RES; fit_camera(1.10); light_rig((0, 0, H / 2), max(W, H) * 1.3, warm=.38, world=.25)
    marks = dict(label=obj_rect(v["label"]))   # projected while the frame is square
    paths = render_layers("box_" + name, [("", ["back", "front"])], res=BOX_RES)
    write_json(f"box_{name}_marks.json", marks)
    return paths

def render_boxes():
    for k in BOXES: render_box(k)

# ---------------------------------------------------------------- 6. clipboard (600 x 800) and 7. stamp (512 x 512)
def build_clipboard():
    W, H = .23, .32
    wood = mat("cb_wood", (0.70, 0.46, 0.22, 1), rough=.6, bump=.25, scale=40); clip = mat("cb_clip", (0.82, 0.84, 0.86, 1), rough=.2, metal=.95, bump=0)
    paper = mat("cb_paper", (0.98, 0.98, 0.96, 1), rough=.8, bump=.05, scale=200, emit=.25); teal = mat("cb_teal", TEAL, rough=.6, bump=0); line = mat("cb_line", (0.70, 0.72, 0.76, 1), rough=.8, bump=0)
    box("cb_board", (W, H, .008), (0, 0, .004), wood, bevel=.01, seg=4)
    sheet = box("cb_sheet", (W - .03, H - .05, .002), (0, -.012, .009), paper, bevel=.001)
    box("cb_header", (W - .03, .03, .0015), (0, -.012 + (H - .05) / 2 - .015, .0107), teal, bevel=.001)
    text("cb_title", "NOTA DE ENTREGA", .013, (0, -.012 + (H - .05) / 2 - .015, .0116), mat("cb_title", CREAM, rough=.8, bump=0), bold=True)
    for k in range(9):
        box(f"cb_line{k}", (W - .06, .0012, .0012), (0, -.012 + (H - .05) / 2 - .05 - k * .026, .0106), line, bevel=0)
    box("cb_clip_base", (.09, .025, .012), (0, H / 2 - .018, .014), clip, bevel=.004)
    box("cb_clip_jaw", (.07, .02, .006), (0, H / 2 - .035, .012), clip, bevel=.003)
    cyl("cb_clip_hinge", .008, .09, (0, H / 2 - .01, .022), clip, rot=(0, rad(90), 0), verts=16)
    box("cb_clip_lever", (.05, .018, .004), (0, H / 2 - .03, .030), clip, bevel=.002, rot=(rad(-25), 0, 0))
    cyl("cb_hole", .006, .01, (0, H / 2 - .008, .004), mat("cb_hole", DARK, rough=.9, bump=0), verts=12)
    return dict(sheet=sheet, lines=dict(x0=-(W - .06) / 2, x1=(W - .06) / 2, yTop=-.012 + (H - .05) / 2 - .05, step=.026, n=9), size=(W, H))

def render_clipboard():
    clear(); sc = scene(); v = build_clipboard(); W, H = v["size"]
    camera((0, -.01, 0), 82, 1.0, 50); sc.render.resolution_x, sc.render.resolution_y = 600, 800; fit_camera(1.06)
    light_rig((0, 0, 0), .45, warm=.45, world=.3)
    data = dict(size=[600, 800], sheet=obj_rect(v["sheet"]))
    L = v["lines"]; data["lines"] = [dict(x0=proj((L["x0"], L["yTop"] - k * L["step"], .011))[0], x1=proj((L["x1"], L["yTop"] - k * L["step"], .011))[0], y=proj((0, L["yTop"] - k * L["step"], .011))[1]) for k in range(L["n"])]
    paths = render_layers("receiving_clipboard", [("", ["back", "front"])], res=(600, 800))
    write_json("receiving_clipboard.json", data)
    return paths

def build_stamp():
    """Red rubber-stamp imprint: CONFERIDO in a rounded frame with a check mark, noise eats into the ink."""
    ink = mat("st_ink", (0.72, 0.05, 0.04, 1), rough=.9, bump=0, emit=.5)
    nt = ink.node_tree; b = nt.nodes["Principled BSDF"]
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 90; n.inputs["Detail"].default_value = 6; n.inputs["Roughness"].default_value = .7
    rmp = nt.nodes.new("ShaderNodeValToRGB"); rmp.color_ramp.elements[0].position = .36; rmp.color_ramp.elements[1].position = .52
    nt.links.new(n.outputs["Fac"], rmp.inputs["Fac"]); nt.links.new(rmp.outputs["Color"], b.inputs["Alpha"])
    if hasattr(ink, "surface_render_method"): ink.surface_render_method = 'BLENDED'
    W, H, t = .40, .20, .012
    for nm, sz, lc in (("st_fT", (W, t, .002), (0, H / 2, 0)), ("st_fB", (W, t, .002), (0, -H / 2, 0)), ("st_fL", (t, H + t, .002), (-W / 2, 0, 0)), ("st_fR", (t, H + t, .002), (W / 2, 0, 0))):
        box(nm, sz, lc, ink, bevel=.004)
    box("st_fT2", (W - .03, .004, .002), (0, H / 2 - .02, 0), ink, bevel=0); box("st_fB2", (W - .03, .004, .002), (0, -H / 2 + .02, 0), ink, bevel=0)
    text("st_txt", "CONFERIDO", .056, (.035, .0, .001), ink, bold=True, extrude=0)
    box("st_ck1", (.012, .04, .002), (-.163, -.018, 0), ink, bevel=.003, rot=(0, 0, rad(40)))
    box("st_ck2", (.012, .085, .002), (-.128, .0, 0), ink, bevel=.003, rot=(0, 0, rad(-32)))
    return dict(size=(W, H))

def render_stamp():
    clear(); sc = scene(); build_stamp()
    camera((0, 0, 0), 89.9, 1.2, 50); sc.render.resolution_x, sc.render.resolution_y = BOX_RES; fit_camera(1.08)
    light_rig((0, 0, 0), .5, warm=.4, world=.4)
    return render_layers("stamp_conferido", [("", ["back", "front"])], res=BOX_RES)

# ---------------------------------------------------------------- composed preview + render_all
def place(build_fn, off, scale=1.0, rot=None, **kw):
    """Builds a prop at `off` (optionally scaled / rotated about that point) inside the current scene."""
    global OFF
    sc = bpy.context.scene; before = {o.name for o in sc.objects}
    OFF = Vector(off); v = build_fn(**kw); OFF = Vector((0, 0, 0))
    R = rot or Matrix.Identity(4)
    for o in sc.objects:
        if o.name in before or o.get("layer") in ("light", "cam"): continue
        o.location = Vector(off) + R @ ((o.location - Vector(off)) * scale)
        o.rotation_euler = (R @ o.rotation_euler.to_matrix().to_4x4()).to_euler(); o.scale = Vector(o.scale) * scale
    return v

def pallet(nm, off):
    w = mat("pv_pallet", (0.78, 0.60, 0.36, 1), rough=.7, bump=.2, scale=80)
    for k in range(5): box(f"{nm}_top{k}", (.19, 1.0, .02), (off[0] - .48 + k * .24, off[1], off[2] + .13), w, bevel=.004)
    for k in range(3): box(f"{nm}_str{k}", (1.2, .10, .09), (off[0], off[1] - .45 + k * .45, off[2] + .075), w, bevel=.006)
    for k in range(3): box(f"{nm}_bot{k}", (1.2, .10, .02), (off[0], off[1] - .45 + k * .45, off[2] + .01), w, bevel=.004)

def build_preview():
    clear(); sc = scene(); SLOTS.clear()
    place(build_backdrop, (0, 0, 0))
    place(build_truck, (-3.5, .12, 0))
    place(build_rack, (-0.3, -1.05, 0)); sl1 = list(SLOTS["rack"]); place(build_rack, (2.75, -1.05, 0)); sl2 = list(SLOTS["rack"]); place(build_coldroom, (5.5, -1.62, 0))
    ink = mat("pv_sign_ink", TEAL_D, rough=.8, bump=0)
    text("pv_sign1", "SECOS", .17, (-0.3, -1.05 + RACK["D"] / 2 - .03, RACK["H"] + .40), ink, rot=(rad(90), 0, 0), bold=True)
    text("pv_sign2", "BEBIDAS", .17, (2.75, -1.05 + RACK["D"] / 2 - .03, RACK["H"] + .40), ink, rot=(rad(90), 0, 0), bold=True)
    # boxes on the cargo floor (truck local -> world: + (-3.5, .12, 0))
    for nm, x, y in (("carton", -.72, .55), ("crate", 0, .5), ("pack", .72, .55), ("frozen", -.7, 1.15), ("tray", .05, 1.1), ("carton", .72, 1.2), ("crate", -.3, 1.8), ("pack", .5, 1.85)):
        place(BOXES[nm], (-3.5 + x, .12 + y, .03))
    # boxes already on the racks and in the cold room (scaled to the slot width)
    def on_slot(key_slots, idx, nm, off, scale=.8):
        s_ = key_slots[idx]; place(BOXES[nm], (off[0] + (s_["x0"] + s_["x1"]) / 2, off[1] + (s_["y0"] + s_["y1"]) / 2 - .05, off[2] + s_["z"]), scale)
    for idx, nm in ((0, "carton"), (1, "carton"), (4, "crate"), (7, "carton"), (9, "tray"), (12, "carton"), (14, "frozen")): on_slot(sl1, idx, nm, (-0.3, -1.05, 0))
    for idx, nm in ((0, "pack"), (2, "pack"), (3, "carton"), (6, "pack"), (10, "pack"), (13, "crate")): on_slot(sl2, idx, nm, (2.75, -1.05, 0))
    for idx, nm in ((0, "frozen"), (2, "frozen"), (4, "frozen")): on_slot(SLOTS["coldroom"], idx, nm, (5.5, -1.62, 0), .9)
    # clipboard hanging on the wall beside the dock, a stack of pallets in the staging area
    place(build_clipboard, (-2.55, -2.86, .15), 1.0, Matrix.Rotation(rad(70), 4, 'X'))
    pallet("pv_pal0", (-3.3, -2.3, 0)); pallet("pv_pal1", (-3.3, -2.3, .15))
    place(BOXES["carton"], (-3.3, -2.3, .31)); place(BOXES["frozen"], (-2.9, -3.3, 0), .9)
    return dict(target=(0.5, -1.2, 1.5), pitch=12, dist=7.3, lens=26, size=2.6)

def render_preview():
    v = build_preview(); sc = bpy.context.scene
    camera(v["target"], v["pitch"], v["dist"], v["lens"]); light_rig(v["target"], v["size"], warm=.30, world=.20)
    sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.film_transparent = False
    _show(["back", "front"]); p = os.path.join(OUT, "preview_scene.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    sc.render.film_transparent = True
    return p

def render_all():
    render_backdrop(); render_truck(); render_rack(); render_coldroom(); render_boxes(); render_clipboard(); render_stamp(); render_preview()

