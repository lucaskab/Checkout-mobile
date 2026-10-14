"""receiving_art_v2.py -- Checkout - Supermercado Simulator (Oct 2026)
Second take on the RECEIVING mini-game art (stockroom where a supplier delivery is checked in). Everything is modelled
in 3D and rendered with Cycles from one camera family (pitch 15 deg, 40 mm) so the fixtures line up in one room.

Outputs go to ArtSource/receiving/render_v2 (NEVER into Assets; copy by hand after approval):
  receiving_backdrop.jpg (+ .json)            1920 x 960 stockroom interior; json "dock" = opening rect for the truck
  receiving_truck_back/front.png + .json      small delivery truck seen from inside; "cargo" quad + "ppm" + "dockRect"
  receiving_rack_back/front.png + .json       SECOS   steel rack, 2 bays x 3 levels, slots on levels 0-1 (8)
  receiving_drinks_back/front.png + .json     BEBIDAS pallet-base rack, slots on the pallets and level 1 (8)
  receiving_produce_back/front.png + .json    HORTIFRUTI | PAES tiered crate display (bay 0) + bakery trolley (bay 1), 7 slots
  receiving_coldroom_back/front.png + .json   CAMARA FRIA walk-in cooler, door open, 2 wire shelves x 4 slots (8)
  receiving_clipboard.png + .json             600 x 800 delivery note; "sheet" rect + 6 "lines"
  stamp_conferido.png                         512 x 512 rubber stamp imprint
  box_<variant>.png + box_<variant>_marks.json   (unchanged design, re-rendered for consistency)
JSON contract is the one CheckoutReceivingGame.cs reads (JFixture / JTruck / JClip): normalised image coords, origin at
the BOTTOM-LEFT, quads fl/fr/bl/br, "ppm" pixels per metre at the front edge of a quad. New optional keys: fixture
"body" (normalised rect of the rendered body, for sizing), truck "dockRect"/"screenWidth", backdrop json "dock".

    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\receiving\\receiving_art_v2.py", encoding="utf-8").read())
    render_all()
"""
import bpy, bmesh, math, os, json, random
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\receiving"
OUT = os.path.join(HERE, "render_v2")
RES = (1400, 1200)          # fixtures (near-square bodies)
SCENE = "ReceivingArtV2"
rad = math.radians

# Market brand BLUE for painted steel (kept from v1, user request Oct 2026); orange beams; cream, wood, stainless.
BLUE = (0.027, 0.272, 0.450, 1); BLUE_D = (0.014, 0.150, 0.275, 1); BLUE_L = (0.059, 0.473, 0.637, 1)
TEAL, TEAL_D, TEAL_L = BLUE, BLUE_D, BLUE_L
CREAM = (0.96, 0.90, 0.74, 1); WHITE = (0.93, 0.93, 0.90, 1); ORANGE = (1.0, 0.42, 0.05, 1)
WOOD = (0.62, 0.38, 0.19, 1); WOOD_L = (0.80, 0.58, 0.33, 1); METAL = (0.62, 0.66, 0.66, 1); DARK = (0.10, 0.11, 0.12, 1)
FROST = (0.80, 0.90, 0.96, 1); YELLOW = (1.0, 0.70, 0.02, 1); CARD = (0.60, 0.40, 0.20, 1); CARD_D = (0.45, 0.28, 0.13, 1)
RED = (0.80, 0.12, 0.10, 1); GREEN = (0.22, 0.58, 0.25, 1); STEEL = (0.78, 0.80, 0.80, 1)

OFF = Vector((0, 0, 0))

# ---------------------------------------------------------------- scene / materials
def scene():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = sc
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 96; sc.cycles.use_denoising = True
    try:
        p = bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type = 'OPTIX'; p.get_devices()
        for d in p.devices: d.use = d.type != 'CPU'
        sc.cycles.device = 'GPU'
    except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.resolution_percentage = 100; sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
    return sc

def clear():
    sc = scene()
    for o in list(sc.objects): bpy.data.objects.remove(o, do_unlink=True)
    _M.clear()

_M = {}
def mat(name, rgb, rough=.55, metal=0., emit=0., alpha=1., transmission=0., bump=.10, scale=60., emit_rgb=None, spec=None):
    if name in _M and _M[name].name in bpy.data.materials: return _M[name]
    m = bpy.data.materials.get("RV2_" + name)
    if m: bpy.data.materials.remove(m)
    m = bpy.data.materials.new("RV2_" + name)
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
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = scale * .15; n2.inputs["Detail"].default_value = 2
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.inputs["Factor"].default_value = .12
        mx.inputs[6].default_value = rgb; mx.inputs[7].default_value = (rgb[0] * .75, rgb[1] * .75, rgb[2] * .75, 1)
        ramp = nt.nodes.new("ShaderNodeMath"); ramp.operation = 'MULTIPLY'; ramp.inputs[1].default_value = .18
        nt.links.new(n2.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], mx.inputs["Factor"])
        nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    _M[name] = m; return m

def wood_mat(name, rgb, rgb2, rough=.62, grain=(1.0, 22.0, 22.0), bump=.14):
    m = mat(name, rgb, rough=rough, bump=bump, scale=70)
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = grain
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 2.2; n.inputs["Detail"].default_value = 6; n.inputs["Roughness"].default_value = .55
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    rmp = nt.nodes.new("ShaderNodeValToRGB"); rmp.color_ramp.elements[0].position = .38; rmp.color_ramp.elements[1].position = .62
    rmp.color_ramp.elements[0].color = rgb; rmp.color_ramp.elements[1].color = rgb2
    nt.links.new(n.outputs["Fac"], rmp.inputs["Fac"]); nt.links.new(rmp.outputs["Color"], b.inputs["Base Color"])
    return m

def block_mat(name, rgb, mortar=(0.70, 0.68, 0.62, 1), size=(.39, .19), rough=.85):
    """Painted concrete-block wall: brick texture in object space (blocks 39 x 19 cm), slight bump in the joints."""
    m = mat(name, rgb, rough=rough, bump=.12, scale=40)
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); cb = nt.nodes.new("ShaderNodeCombineXYZ")
    mu = nt.nodes.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 1 / size[0]
    mv = nt.nodes.new("ShaderNodeMath"); mv.operation = 'MULTIPLY'; mv.inputs[1].default_value = 1 / size[1]
    nt.links.new(tc.outputs["Object"], sp.inputs[0]); nt.links.new(sp.outputs["X"], mu.inputs[0]); nt.links.new(sp.outputs["Z"], mv.inputs[0])
    nt.links.new(mu.outputs[0], cb.inputs["X"]); nt.links.new(mv.outputs[0], cb.inputs["Y"]); cb.inputs["Z"].default_value = 0
    br = nt.nodes.new("ShaderNodeTexBrick"); br.inputs["Color1"].default_value = rgb; br.inputs["Color2"].default_value = (rgb[0] * .93, rgb[1] * .93, rgb[2] * .92, 1)
    br.inputs["Mortar"].default_value = mortar; br.inputs["Scale"].default_value = 1; br.inputs["Mortar Size"].default_value = .025; br.inputs["Bias"].default_value = 0
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0; br.offset = .5
    nt.links.new(cb.outputs["Vector"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .35; bp.inputs["Distance"].default_value = .02
    nt.links.new(br.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

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

def sphere(name, r, loc, m, layer="back", scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=Vector(loc) + OFF, segments=24, ring_count=12, rotation=rot); o = bpy.context.object
    o.scale = scale; bpy.ops.object.transform_apply(scale=True)
    return _finish(o, name, m, layer)

def rounded(name, w, h, loc, m, r=.02, thick=.004, layer="back", rot=(0, 0, 0), frame=0.):
    """Flat rounded-rectangle plate (XY plane); frame > 0 keeps only a border of that width."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=Vector(loc) + OFF, rotation=rot); o = bpy.context.object
    o.scale = (w, h, 1); bpy.ops.object.transform_apply(scale=True)
    bv = o.modifiers.new("b", 'BEVEL'); bv.affect = 'VERTICES'; bv.width = r; bv.segments = 8
    if frame > 0:
        wf = o.modifiers.new("w", 'WIREFRAME'); wf.thickness = frame; wf.use_replace = True; wf.use_even_offset = True; wf.use_boundary = True
    else:
        sd = o.modifiers.new("s", 'SOLIDIFY'); sd.thickness = thick; sd.offset = 0
    return _finish(o, name, m, layer)

def text(name, body, size, loc, m, rot=(0, 0, 0), layer="back", align='CENTER', extrude=0.0, bold=False):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.align_x = align; cu.align_y = 'CENTER'
    cu.extrude = extrude; cu.offset = .01 * size if bold else 0; cu.resolution_u = 6
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    o.location = Vector(loc) + OFF; o.rotation_euler = rot; o.data.materials.append(m); o["layer"] = layer
    return o

def grid_wire(name, w, d, loc, m, nx=12, ny=6, thick=.006, layer="back"):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=nx, y_subdivisions=ny, size=1, location=Vector(loc) + OFF); o = bpy.context.object
    o.scale = (w, d, 1); bpy.ops.object.transform_apply(scale=True)
    md = o.modifiers.new("w", 'WIREFRAME'); md.thickness = thick; md.use_replace = True; md.use_even_offset = False
    return _finish(o, name, m, layer)

def pivot_rot(o, pivot, angle_z):
    p = Vector(pivot) + OFF; R = Matrix.Rotation(angle_z, 4, 'Z')
    o.location = p + R @ (o.location - p)
    o.rotation_euler = (R @ o.rotation_euler.to_matrix().to_4x4()).to_euler()

def light_rig(target, size, warm=1.0, world=.35, key_color=(1, .97, .92)):
    sc = bpy.context.scene
    w = bpy.data.worlds.get("RV2_World") or bpy.data.worlds.new("RV2_World"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (.85, .88, .92, 1); w.node_tree.nodes["Background"].inputs[1].default_value = world
    def area(n, loc, energy, s, color=(1, .97, .92)):
        bpy.ops.object.light_add(type='AREA', location=loc); l = bpy.context.object; l.name = n
        l.data.energy = energy; l.data.size = s; l.data.color = color
        l.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); l["layer"] = "light"
    t = Vector(target) + OFF
    area("Key", (t[0] - size * 1.2, t[1] - size * 2.2, t[2] + size * 2.0), 120 * size * size * warm, size * 1.5, key_color)
    area("Fill", (t[0] + size * 1.6, t[1] - size * 1.6, t[2] + size * .6), 35 * size * size, size * 2, (.92, .95, 1))

def camera(target, pitch_deg, dist, lens=40, yaw_deg=0):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("RV2_Cam")
    if not cam or cam.name not in sc.objects:
        cam = bpy.data.objects.new("RV2_Cam", bpy.data.cameras.new("RV2_Cam")); sc.collection.objects.link(cam)
    cam.data.lens = lens; cam.data.sensor_width = 36; cam.data.clip_end = 200
    p = rad(pitch_deg); y = rad(yaw_deg); t = Vector(target) + OFF
    off = Vector((math.sin(y) * math.cos(p) * dist, -math.cos(y) * math.cos(p) * dist, math.sin(p) * dist))
    cam.location = t + off
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam["layer"] = "cam"
    sc.camera = cam; return cam

def fit_camera(margin=1.05, layers=None):
    sc = bpy.context.scene; cam = sc.camera; dg = bpy.context.evaluated_depsgraph_get()
    coords = []
    for o in sc.objects:
        if o.type not in ('MESH', 'FONT') or o.get("layer") in ("light", "cam") or o.get("nofit"): continue
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

def render_layers(name, layers, res=RES, transparent=True):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = res; sc.render.film_transparent = transparent
    paths = []
    for suffix, show in layers:
        _show(show); fn = f"{name}_{suffix}.png" if suffix else f"{name}.png"
        p = os.path.join(OUT, fn); sc.render.filepath = p; bpy.ops.render.render(write_still=True); paths.append(p)
    _show(["back", "front"]); sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.film_transparent = True
    return paths

# ---------------------------------------------------------------- projection helpers
def proj(p):
    sc = bpy.context.scene; v = world_to_camera_view(sc, sc.camera, Vector(p)); return [round(v.x, 4), round(v.y, 4)]

def ppm_at(p):
    sc = bpy.context.scene; a = world_to_camera_view(sc, sc.camera, Vector(p)); b = world_to_camera_view(sc, sc.camera, Vector(p) + Vector((0, 0, 1)))
    return round((b.y - a.y) * sc.render.resolution_y, 2)

def quad(x0, x1, y0, y1, z):
    o = OFF
    return dict(fl=proj((x0 + o.x, y0 + o.y, z + o.z)), fr=proj((x1 + o.x, y0 + o.y, z + o.z)), bl=proj((x0 + o.x, y1 + o.y, z + o.z)), br=proj((x1 + o.x, y1 + o.y, z + o.z)),
                ppm=ppm_at((x0 + o.x, y0 + o.y, z + o.z)), ppmBack=ppm_at((x0 + o.x, y1 + o.y, z + o.z)))

def obj_rect(o):
    cs = [world_to_camera_view(bpy.context.scene, bpy.context.scene.camera, o.matrix_world @ Vector(c)) for c in o.bound_box]
    return [round(min(c.x for c in cs), 4), round(min(c.y for c in cs), 4), round(max(c.x for c in cs), 4), round(max(c.y for c in cs), 4)]

def body_rect(layers=("back", "front")):
    """Normalised bounds of everything rendered (what Unity should treat as the body of the image)."""
    sc = bpy.context.scene; xs, ys = [], []
    for o in sc.objects:
        if o.type not in ('MESH', 'FONT') or o.get("layer") not in layers or o.get("nofit"): continue
        for c in o.bound_box:
            v = world_to_camera_view(sc, sc.camera, o.matrix_world @ Vector(c)); xs.append(v.x); ys.append(v.y)
    return [round(max(0, min(xs)), 4), round(max(0, min(ys)), 4), round(min(1, max(xs)), 4), round(min(1, max(ys)), 4)]

def write_json(name, data):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f: json.dump(data, f, indent=1)

SLOTS = {}
def slot(key, level, bay, index, x0, x1, y0, y1, z):
    SLOTS.setdefault(key, []).append(dict(level=level, bay=bay, index=index, x0=x0, x1=x1, y0=y0, y1=y1, z=z))
def slots_json(key):
    out = []
    for s in SLOTS.get(key, []):
        d = dict(level=s["level"], bay=s["bay"], index=s["index"]); d.update(quad(s["x0"], s["x1"], s["y0"], s["y1"], s["z"])); out.append(d)
    return out

# ---------------------------------------------------------------- shared props
def pallet(nm, off, w=1.2, d=1.0, layer="back", m=None):
    """Wooden euro pallet: 5 top boards, 3 stringers on 3 bottom boards (top of the deck at off.z + .145)."""
    m = m or wood_mat(nm + "_w", (0.82, 0.64, 0.38, 1), (0.62, 0.44, 0.22, 1), grain=(1.0, 18.0, 18.0))
    for k in range(5): box(f"{nm}_top{k}", (w * .16, d, .022), (off[0] - w * .4 + k * w * .2, off[1], off[2] + .134), m, bevel=.004, layer=layer)
    for k in range(3): box(f"{nm}_str{k}", (w, .10, .09), (off[0], off[1] - d * .45 + k * d * .45, off[2] + .078), m, bevel=.006, layer=layer)
    for k in range(3): box(f"{nm}_bot{k}", (w, .10, .022), (off[0], off[1] - d * .45 + k * d * .45, off[2] + .011), m, bevel=.004, layer=layer)

def sack(nm, loc, m, w=.42, d=.28, h=.30, layer="back", rot_z=0.):
    """A soft stuffed sack (flour / rice / sugar): a squashed rounded box with pinched ends."""
    o = box(nm, (w, d, h), (loc[0], loc[1], loc[2] + h / 2), m, bevel=min(h, d) * .42, seg=6, layer=layer, rot=(0, 0, rot_z))
    for sx in (-1, 1):
        box(nm + f"_ear{sx}", (.06, d * .55, .04), (loc[0] + sx * (w / 2 + .01), loc[1], loc[2] + h * .35), m, bevel=.012, layer=layer, rot=(0, 0, rot_z))
    return o

def carton_deco(nm, loc, w=.42, d=.34, h=.32, layer="back", rot_z=0., label=True):
    card = mat("dc_card", CARD, rough=.8, bump=.22, scale=120); tape = mat("dc_tape", (0.66, 0.46, 0.24, 1), rough=.25, bump=.04)
    box(nm, (w, d, h), (loc[0], loc[1], loc[2] + h / 2), card, bevel=.012, seg=4, layer=layer, rot=(0, 0, rot_z))
    box(nm + "_tape", (.06, d + .004, .004), (loc[0], loc[1], loc[2] + h + .002), tape, bevel=.001, layer=layer, rot=(0, 0, rot_z))
    if label: box(nm + "_lbl", (w * .4, .004, h * .3), (loc[0] + w * .15, loc[1] - d / 2 - .002, loc[2] + h * .5), mat("dc_label", WHITE, rough=.6, bump=0), bevel=.002, layer=layer, rot=(0, 0, rot_z))

def water_pack(nm, loc, layer="back", n=(3, 2), r=.045, h=.30, cap=(0.10, 0.45, 0.85, 1)):
    """Shrink-wrapped pack of water bottles (fardo)."""
    pet = mat("dc_pet", (0.85, 0.93, 1.0, 1), rough=.08, alpha=.35, bump=0, spec=.3); capm = mat("dc_cap", cap, rough=.35, bump=0)
    lab = mat("dc_wlabel", (0.20, 0.55, 0.90, 1), rough=.5, bump=0); wrap = mat("dc_wrap", (0.80, 0.90, 1.0, 1), rough=.25, alpha=.16, bump=0, spec=.15)
    W, D = n[0] * r * 2.1, n[1] * r * 2.1
    for i in range(n[0]):
        for j in range(n[1]):
            x = loc[0] - W / 2 + r * 1.05 + i * r * 2.1; y = loc[1] - D / 2 + r * 1.05 + j * r * 2.1
            cyl(f"{nm}_b{i}{j}", r, h * .78, (x, y, loc[2] + h * .39), pet, verts=18, bevel=.012, layer=layer)
            cyl(f"{nm}_n{i}{j}", r * .5, h * .12, (x, y, loc[2] + h * .84), pet, verts=12, layer=layer)
            cyl(f"{nm}_c{i}{j}", r * .55, h * .07, (x, y, loc[2] + h * .935), capm, verts=12, bevel=.003, layer=layer)
            box(f"{nm}_l{i}{j}", (r * 1.4, .004, h * .22), (x, y - r - .002, loc[2] + h * .38), lab, bevel=.002, layer=layer)
    box(f"{nm}_wrap", (W + .01, D + .01, h * .92), (loc[0], loc[1], loc[2] + h * .46), wrap, bevel=.02, seg=4, layer=layer)

def bottle_crate(nm, loc, m, w=.40, d=.30, h=.28, layer="back"):
    """Plastic drinks crate (hollow box with slots on the sides) with brown bottles inside."""
    box(nm + "_base", (w, d, .03), (loc[0], loc[1], loc[2] + .015), m, bevel=.006, layer=layer)
    for sy in (-1, 1): box(f"{nm}_wy{sy}", (w, .02, h), (loc[0], loc[1] + sy * (d / 2 - .01), loc[2] + h / 2), m, bevel=.006, layer=layer)
    for sx in (-1, 1): box(f"{nm}_wx{sx}", (.02, d, h), (loc[0] + sx * (w / 2 - .01), loc[1], loc[2] + h / 2), m, bevel=.006, layer=layer)
    for k in range(4): box(f"{nm}_sl{k}", (w * .17, .024, h * .45), (loc[0] - w * .35 + k * w * .233, loc[1] - d / 2, loc[2] + h * .45), mat("dc_slot", (0.02, 0.02, 0.02, 1), rough=.9, bump=0), bevel=.004, layer=layer)
    amber = mat("dc_amber", (0.28, 0.11, 0.02, 1), rough=.08, bump=0); capm = mat("dc_gcap", (0.93, 0.80, 0.30, 1), rough=.35, bump=0)
    for i in range(4):
        for j in range(3):
            x = loc[0] - w / 2 + .05 + i * (w - .1) / 3; y = loc[1] - d / 2 + .05 + j * (d - .1) / 2
            cyl(f"{nm}_bt{i}{j}", .03, h * .9, (x, y, loc[2] + h * .5), amber, verts=14, bevel=.01, layer=layer)
            cyl(f"{nm}_bn{i}{j}", .014, .06, (x, y, loc[2] + h * .98), amber, verts=10, layer=layer)
            cyl(f"{nm}_bc{i}{j}", .016, .012, (x, y, loc[2] + h * 1.02), capm, verts=10, layer=layer)

def fruit_crate(nm, loc, fruit, w=.50, d=.34, h=.26, layer="back", rot_z=0., seed=3):
    """Pine market crate filled with round fruit (fruit = material)."""
    pine = wood_mat("dc_pine", (0.88, 0.63, 0.33, 1), (0.60, 0.38, 0.16, 1)); post = wood_mat("dc_post", (0.40, 0.22, 0.09, 1), (0.27, 0.14, 0.05, 1), grain=(18., 18., 1.))
    R = Matrix.Rotation(rot_z, 4, 'Z'); L = Vector(loc)
    def at(x, y, z): v = L + R @ Vector((x, y, z)); return (v.x, v.y, v.z)
    for sx in (-1, 1):
        for sy in (-1, 1): box(f"{nm}_p{sx}{sy}", (.03, .03, h), at(sx * (w / 2 - .02), sy * (d / 2 - .02), h / 2), post, bevel=.004, layer=layer, rot=(0, 0, rot_z))
    for k, z in enumerate((.04, .12, .21)):
        for sy in (-1, 1): box(f"{nm}_by{sy}{k}", (w, .016, .055), at(0, sy * (d / 2 - .008), z), pine, bevel=.003, layer=layer, rot=(0, 0, rot_z))
        for sx in (-1, 1): box(f"{nm}_bx{sx}{k}", (.016, d - .03, .055), at(sx * (w / 2 - .008), 0, z), pine, bevel=.003, layer=layer, rot=(0, 0, rot_z))
    box(f"{nm}_floor", (w - .03, d - .03, .014), at(0, 0, .02), pine, bevel=.002, layer=layer, rot=(0, 0, rot_z))
    rnd = random.Random(seed)
    for k in range(12):
        x = -w / 2 + .07 + (w - .14) * (k % 4 + .5) / 4 + rnd.uniform(-.015, .015); y = -d / 2 + .06 + (d - .12) * ((k // 4) % 3 + .5) / 3 + rnd.uniform(-.015, .015)
        rr = rnd.uniform(.04, .055); sphere(f"{nm}_f{k}", rr, at(x, y, h * .72 + rr * .3), fruit, layer=layer, scale=(1, 1, .9))
    for k in range(3): sphere(f"{nm}_ft{k}", .045, at(-.12 + k * .12, rnd.uniform(-.03, .03), h * .95), fruit, layer=layer, scale=(1, 1, .9))

def bread_tray(nm, loc, w=.60, d=.40, layer="back", loaves=6, seed=2, kind="french"):
    """Aluminium baking tray with french rolls / loaves."""
    alu = mat("dc_alu", (0.72, 0.74, 0.74, 1), rough=.3, metal=.8, bump=.06); crust = mat("dc_crust", (0.86, 0.58, 0.24, 1), rough=.55, bump=.25, scale=150)
    box(f"{nm}_tray", (w, d, .012), (loc[0], loc[1], loc[2] + .006), alu, bevel=.004, layer=layer)
    for sy in (-1, 1): box(f"{nm}_ry{sy}", (w, .012, .03), (loc[0], loc[1] + sy * (d / 2 - .006), loc[2] + .015), alu, bevel=.003, layer=layer)
    for sx in (-1, 1): box(f"{nm}_rx{sx}", (.012, d, .03), (loc[0] + sx * (w / 2 - .006), loc[1], loc[2] + .015), alu, bevel=.003, layer=layer)
    rnd = random.Random(seed)
    cols = 4 if loaves > 4 else loaves; rows = max(1, loaves // cols)
    for k in range(loaves):
        i, j = k % cols, k // cols
        x = loc[0] - w / 2 + w * (i + .5) / cols; y = loc[1] - d / 2 + d * (j + .5) / rows
        if kind == "french":
            sphere(f"{nm}_l{k}", .055, (x, y, loc[2] + .055), crust, layer=layer, scale=(2.0, 1, .85), rot=(0, 0, rad(rnd.uniform(-10, 10))))
            box(f"{nm}_cut{k}", (.14, .012, .01), (x, y, loc[2] + .100), mat("dc_crumb", (0.98, 0.90, 0.70, 1), rough=.8, bump=.3, scale=200), bevel=.003, layer=layer, rot=(0, 0, rad(rnd.uniform(-10, 10))))
        else:
            sphere(f"{nm}_l{k}", .07, (x, y, loc[2] + .06), crust, layer=layer, scale=(1.3, .9, .8))

# ---------------------------------------------------------------- 1. backdrop (1920 x 960)
BD = dict(W=14.0, H=3.6, depth=7.0)
DOCK = dict(x0=-5.45, x1=-3.35, h=2.3)

def build_backdrop():
    W, H = BD["W"], BD["H"]; x0, x1, dh = DOCK["x0"], DOCK["x1"], DOCK["h"]
    epoxy = mat("bd_epoxy", (0.40, 0.44, 0.42, 1), rough=.22, bump=.05, scale=6, spec=.6)
    blocks_up = block_mat("bd_block_up", (0.94, 0.88, 0.74, 1)); blocks_lo = block_mat("bd_block_lo", (0.045, 0.30, 0.48, 1), mortar=(0.03, 0.18, 0.30, 1))
    blocks_side = block_mat("bd_block_side", (0.90, 0.84, 0.70, 1)); blocks_side_lo = block_mat("bd_block_side_lo", (0.04, 0.27, 0.44, 1), mortar=(0.03, 0.18, 0.30, 1))
    yellow = mat("bd_yellow", YELLOW, rough=.5, bump=.1, scale=30); black = mat("bd_black", (0.05, 0.05, 0.05, 1), rough=.6, bump=.1, scale=30)
    rubber = mat("bd_rubber", (0.05, 0.05, 0.05, 1), rough=.85); door_m = mat("bd_door", (0.68, 0.70, 0.70, 1), rough=.4, metal=.5)
    frame = mat("bd_frame", (0.55, 0.58, 0.58, 1), rough=.45, metal=.4); steel = mat("bd_steel", STEEL, rough=.3, metal=.85, bump=0)
    conc = mat("bd_conc", (0.52, 0.52, 0.50, 1), rough=.85, bump=.3, scale=20); ceil_m = mat("bd_ceil", (0.80, 0.80, 0.78, 1), rough=.9, bump=.1)
    joist = mat("bd_joist", (0.30, 0.32, 0.34, 1), rough=.6, metal=.3)
    sky = mat("bd_sky", (1.0, 0.85, 0.60, 1), emit=3.0, bump=0); ground = mat("bd_ground", (0.50, 0.47, 0.42, 1), rough=.85, bump=.2)
    # floor: one epoxy slab with a glossy finish; saw-cut joints every 3 m
    box("floor", (W + 4, 12, .05), (0, -4, -.025), epoxy, bevel=0)
    for x in (-3.0, 0.0, 3.0): box(f"joint{x:.0f}", (.012, 12, .006), (x, -4, .001), mat("bd_joint", (0.30, 0.33, 0.32, 1), rough=.6, bump=0), bevel=0)
    # yellow safety lines: hatched strip along the dock edge, a lane box in front of the dock, the stockroom aisle line
    n = 12
    for k in range(n):
        box(f"stripe{k}", ((x1 - x0 + .5) / n, .30, .005), (x0 - .25 + (k + .5) * (x1 - x0 + .5) / n, -.17, .0025), yellow if k % 2 == 0 else black, bevel=0)
    sx0, sx1, sy0, sy1 = x0 + .3, x1 + 1.3, -3.3, -.4
    for nm, sz, lc in (("lane_f", (sx1 - sx0, .10, .005), ((sx0 + sx1) / 2, sy0, .0025)), ("lane_l", (.10, sy1 - sy0, .005), (sx0, (sy0 + sy1) / 2, .0025)), ("lane_r", (.10, sy1 - sy0, .005), (sx1, (sy0 + sy1) / 2, .0025))):
        box(nm, sz, lc, yellow, bevel=0)
    box("aisle", (W - 4, .10, .005), (1.8, -3.6, .0025), yellow, bevel=0)
    text("floor_txt", "RECEBIMENTO", .22, (-3.2, -2.95, .004), yellow, rot=(0, 0, 0), bold=True)
    # walls: painted block, blue band 1.2 m high, cream above, dark skirting; the dock opening cut by pieces
    def wall(nm, xa, xb, za, zb, m, y=.15, d=.30):
        if xb - xa < .01 or zb - za < .01: return
        box(nm, (xb - xa, d, zb - za), ((xa + xb) / 2, y, (za + zb) / 2), m, bevel=0)
    band = 1.25
    wall("wall_L_lo", -W / 2, x0 - .08, 0, band, blocks_lo); wall("wall_L_up", -W / 2, x0 - .08, band, H, blocks_up)
    wall("wall_R_lo", x1 + .08, W / 2, 0, band, blocks_lo); wall("wall_R_up", x1 + .08, W / 2, band, H, blocks_up)
    wall("wall_T", x0 - .08, x1 + .08, dh + .05, H, blocks_up)
    box("skirt_L", (x0 - .08 + W / 2, .02, .12), ((-W / 2 + x0 - .08) / 2, -.01, .06), mat("bd_skirt", (0.12, 0.13, 0.14, 1), rough=.6), bevel=0)
    box("skirt_R", (W / 2 - x1 - .08, .02, .12), ((x1 + .08 + W / 2) / 2, -.01, .06), mat("bd_skirt", (0.12, 0.13, 0.14, 1), rough=.6), bevel=0)
    box("band_line_L", (x0 - .08 + W / 2, .015, .05), ((-W / 2 + x0 - .08) / 2, -.005, band + .025), mat("bd_band", ORANGE, rough=.6, bump=0), bevel=0)
    box("band_line_R", (W / 2 - x1 - .08, .015, .05), ((x1 + .08 + W / 2) / 2, -.005, band + .025), mat("bd_band", ORANGE, rough=.6, bump=0), bevel=0)
    # side walls (right one is in view) and the ceiling with joists
    box("wall_side_R_lo", (.30, 9, band), (W / 2 + .15, -4.5, band / 2), blocks_side_lo, bevel=0); box("wall_side_R_up", (.30, 9, H - band), (W / 2 + .15, -4.5, band + (H - band) / 2), blocks_side, bevel=0)
    box("wall_side_L_lo", (.30, 9, band), (-W / 2 - .15, -4.5, band / 2), blocks_side_lo, bevel=0); box("wall_side_L_up", (.30, 9, H - band), (-W / 2 - .15, -4.5, band + (H - band) / 2), blocks_side, bevel=0)
    box("ceiling", (W + 1, 10, .10), (0, -4.5, H + .05), ceil_m, bevel=0)
    for k in range(4): box(f"joist{k}", (W + 1, .12, .22), (0, -.4 - k * 1.1, H - .11), joist, bevel=.01)
    # conduit + fluorescent fixtures on the ceiling, pendant lamps in front of the wall
    for k, x in enumerate((-1.6, 3.4)):
        box(f"fluo{k}", (1.3, .18, .07), (x, -1.9, H - .035), mat("bd_fluo_case", (0.85, 0.86, 0.86, 1), rough=.4, metal=.3), bevel=.01)
        box(f"fluo_tube{k}", (1.2, .10, .02), (x, -1.9, H - .075), mat("bd_fluo", (1, 1, .95, 1), emit=12, bump=0), bevel=0)
    shade = mat("bd_shade", BLUE, rough=.4, metal=.3); bulb = mat("bd_bulb", (1, .92, .75, 1), emit=25, bump=0)
    for k, x in enumerate((-2.7, 3.9)):
        cyl(f"lamp_rod{k}", .012, .55, (x, -1.0, H - .28), mat("bd_rod", DARK, rough=.5), verts=10)
        bpy.ops.mesh.primitive_cone_add(radius1=.30, radius2=.06, depth=.26, location=Vector((x, -1.0, H - .62)) + OFF, vertices=32); o = bpy.context.object
        _finish(o, f"lamp_shade{k}", shade, "back"); md = o.modifiers.new("b", 'BEVEL'); md.width = .01; md.segments = 3; md.limit_method = 'ANGLE'
        sphere(f"lamp_bulb{k}", .07, (x, -1.0, H - .75), bulb)
        bpy.ops.object.light_add(type='POINT', location=Vector((x, -1.0, H - .80)) + OFF); l = bpy.context.object; l.name = f"lamp_light{k}"
        l.data.energy = 380; l.data.color = (1, .85, .65); l.data.shadow_soft_size = .15; l["layer"] = "light"
    # dock opening: steel frame, guides, roll-up door curtain rolled on a drum, rubber bumpers, the yard outside
    box("jamb_L", (.16, .34, dh + .15), (x0 - .08, .15, (dh + .15) / 2), frame, bevel=.02); box("jamb_R", (.16, .34, dh + .15), (x1 + .08, .15, (dh + .15) / 2), frame, bevel=.02)
    box("lintel", (x1 - x0 + .32, .34, .18), ((x0 + x1) / 2, .15, dh + .14), frame, bevel=.02)
    box("drum_hood", (x1 - x0 + .5, .50, .50), ((x0 + x1) / 2, .20, dh + .50), door_m, bevel=.04, seg=4)
    for k in range(7): box(f"hood_rib{k}", (.04, .52, .52), (x0 + .1 + k * (x1 - x0 - .2) / 6, .20, dh + .50), mat("bd_door_d", (0.52, 0.54, 0.54, 1), rough=.4, metal=.5), bevel=.01)
    for k in range(3): box(f"slat{k}", (x1 - x0 + .14, .03, .075), ((x0 + x1) / 2, -.02, dh + .20 - k * .08), door_m, bevel=.008)
    for side, xs in ((0, x0 + .22), (1, x1 - .22)):
        box(f"bumper{side}", (.30, .14, .45), (xs, .05, .26), rubber, bevel=.03, seg=4)
    box("sky", (x1 - x0 + 3, .02, dh + 6), ((x0 + x1) / 2, 6.0, dh / 2), sky, bevel=0)
    box("ground_out", (x1 - x0 + 2, 6, .05), ((x0 + x1) / 2, 3.0, -.03), ground, bevel=0)
    box("leveler", (x1 - x0 - .3, .9, .03), ((x0 + x1) / 2, .55, .0), mat("bd_leveler", (0.45, 0.47, 0.47, 1), rough=.4, metal=.5, bump=.3, scale=40), bevel=.01)
    box("yard_wall", (x1 - x0 + 2, .2, 1.0), ((x0 + x1) / 2, 5.5, .5), mat("bd_yard", (0.62, 0.50, 0.36, 1), rough=.9, bump=.2), bevel=0)
    # ESTOQUE sign: a cream board with blue letters and an orange rule, centred over the fixtures' wall
    rounded("sign_bd", 2.6, .62, (0.3, -.02, 2.95), mat("bd_sign_bd", BLUE, rough=.5, bump=.04), r=.05, thick=.03, rot=(rad(90), 0, 0))
    rounded("sign_in", 2.46, .50, (0.3, -.04, 2.95), mat("bd_sign_in", CREAM, rough=.6, emit=.25, bump=0), r=.04, thick=.01, rot=(rad(90), 0, 0))
    text("sign_txt", "ESTOQUE", .33, (0.3, -.05, 2.96), mat("bd_sign_ink", BLUE_D, rough=.8, bump=0), rot=(rad(90), 0, 0), extrude=.003, bold=True)
    # wall details on the right: fuse box, clock, extinguisher, a first-aid box, a notice board
    ex = 4.2
    box("fuse", (.42, .12, .58), (5.0, -.06, 1.75), mat("bd_fuse", (0.78, 0.80, 0.80, 1), rough=.35, metal=.3), bevel=.012, seg=4)
    box("fuse_door", (.34, .012, .46), (5.0, -.125, 1.77), mat("bd_fuse_d", (0.70, 0.72, 0.72, 1), rough=.35, metal=.3), bevel=.008)
    box("fuse_lever", (.05, .04, .12), (5.0 + .10, -.15, 1.70), mat("bd_red", (0.85, 0.10, 0.08, 1), rough=.35), bevel=.01)
    rounded("fuse_warn", .09, .09, (4.92, -.132, 1.88), mat("bd_warn", YELLOW, rough=.6, bump=0), r=.01, thick=.004, rot=(rad(90), 0, 0))
    cyl("clock_body", .26, .05, (2.6, -.025, 2.55), mat("bd_clock", (0.10, 0.11, 0.12, 1), rough=.4), rot=(rad(90), 0, 0), verts=40, bevel=.01)
    cyl("clock_face", .23, .01, (2.6, -.052, 2.55), mat("bd_face", (0.98, 0.98, 0.96, 1), rough=.6, bump=0), rot=(rad(90), 0, 0), verts=40)
    for k in range(12):
        a = rad(k * 30); box(f"clock_tick{k}", (.015, .005, .035), (2.6 + math.sin(a) * .20, -.06, 2.55 + math.cos(a) * .20), mat("bd_ink", DARK, rough=.8, bump=0), bevel=0, rot=(0, -a, 0))
    box("clock_h", (.02, .005, .12), (2.6 + .03, -.062, 2.55 + .05), mat("bd_ink", DARK, rough=.8, bump=0), bevel=0, rot=(0, rad(-30), 0))
    box("clock_m", (.015, .005, .18), (2.6 - .06, -.064, 2.55 + .06), mat("bd_ink", DARK, rough=.8, bump=0), bevel=0, rot=(0, rad(45), 0))
    box("ext_bracket", (.10, .04, .30), (ex, -.02, 1.55), mat("bd_bracket", DARK, rough=.5), bevel=.008)
    cyl("ext_body", .085, .50, (ex, -.13, 1.38), mat("bd_red", (0.85, 0.10, 0.08, 1), rough=.35, bump=.05), verts=24, bevel=.03)
    cyl("ext_neck", .03, .08, (ex, -.13, 1.66), steel, verts=12); box("ext_lever", (.03, .12, .025), (ex, -.16, 1.72), steel, bevel=.008)
    cyl("ext_hose", .012, .30, (ex + .08, -.19, 1.45), mat("bd_hose", DARK, rough=.7), rot=(rad(12), rad(8), 0), verts=10)
    box("ext_label", (.11, .005, .14), (ex, -.215, 1.36), mat("bd_label", WHITE, rough=.6, bump=0), bevel=.004)
    rounded("ext_sign", .22, .22, (ex, -.02, 2.05), mat("bd_red_sign", (0.85, 0.10, 0.08, 1), rough=.5, bump=0), r=.02, thick=.01, rot=(rad(90), 0, 0))
    rounded("aid", .32, .32, (3.4, -.03, 1.95), mat("bd_aid", (0.95, 0.95, 0.93, 1), rough=.4, bump=0), r=.03, thick=.06, rot=(rad(90), 0, 0))
    box("aid_c1", (.16, .005, .05), (3.4, -.065, 1.95), mat("bd_green", (0.10, 0.60, 0.30, 1), rough=.5, bump=0), bevel=0); box("aid_c2", (.05, .005, .16), (3.4, -.065, 1.95), mat("bd_green", (0.10, 0.60, 0.30, 1), rough=.5, bump=0), bevel=0)
    rounded("board", 1.1, .8, (-6.3, -.02, 2.1), mat("bd_cork", (0.78, 0.60, 0.38, 1), rough=.9, bump=.3, scale=80), r=.02, thick=.03, rot=(rad(90), 0, 0))
    rounded("board_fr", 1.1, .8, (-6.3, -.03, 2.1), mat("bd_board_fr", WOOD, rough=.6, bump=.1), r=.02, thick=.02, rot=(rad(90), 0, 0), frame=.04)
    rnd = random.Random(4)
    for k in range(5):
        box(f"note{k}", (.22, .004, .28), (-6.3 - .4 + (k % 3) * .4 + rnd.uniform(-.03, .03), -.04, 2.25 - (k // 3) * .33), mat(f"bd_note{k}", [(0.98, 0.98, 0.95, 1), (1.0, 0.93, 0.45, 1), (0.85, 0.95, 1.0, 1)][k % 3], rough=.8, bump=0), bevel=0, rot=(0, rad(rnd.uniform(-5, 5)), 0))
    # pallet jack parked at the right front, a stack of empty pallets against the right wall, a broom
    pj = mat("bd_pj", (0.95, 0.45, 0.05, 1), rough=.4, bump=.06); pj_d = mat("bd_pj_d", (0.12, 0.12, 0.13, 1), rough=.5, metal=.3)
    jx, jy = 5.3, -3.1
    for sx in (-1, 1): box(f"pj_fork{sx}", (.16, 1.15, .07), (jx + sx * .25, jy, .07), pj, bevel=.012, rot=(0, 0, rad(-20)))
    box("pj_head", (.68, .22, .50), (jx + .22, jy + .62, .30), pj, bevel=.02, rot=(0, 0, rad(-20)))
    cyl("pj_handle", .022, 1.1, (jx + .40, jy + .95, .75), pj_d, rot=(rad(-30), rad(-10), 0), verts=12)
    box("pj_grip", (.36, .05, .05), (jx + .60, jy + 1.22, 1.22), pj_d, bevel=.015, rot=(0, 0, rad(-20)))
    for k in range(4): pallet(f"pal{k}", (5.9, -1.0, k * .15))
    for k in range(2): carton_deco(f"bd_ct{k}", (5.8 - k * .05, -1.05 + k * .05, .6 + k * .32), rot_z=rad(k * 12 - 6))
    cyl("broom", .014, 1.3, (-6.6, -.4, .65), wood_mat("bd_broom", (0.85, 0.65, 0.35, 1), (0.65, 0.45, 0.2, 1)), rot=(rad(-6), 0, 0), verts=10)
    box("broom_head", (.30, .06, .10), (-6.6, -.36, .07), mat("bd_broom_h", (0.70, 0.20, 0.15, 1), rough=.6), bevel=.01)
    return dict(target=(0.4, -1.6, 1.25), pitch=7, dist=8.2, lens=28, size=2.6)

def render_backdrop():
    clear(); sc = scene(); v = build_backdrop()
    camera(v["target"], v["pitch"], v["dist"], v["lens"]); light_rig(v["target"], v["size"], warm=.42, world=.30)
    sc.render.resolution_x, sc.render.resolution_y = 1920, 960; sc.render.film_transparent = False
    x0, x1, dh = DOCK["x0"], DOCK["x1"], DOCK["h"]
    a = proj((x0, 0, 0)); b = proj((x1, 0, dh))
    dock = [a[0], a[1], b[0], b[1]]
    _show(["back", "front"]); p = os.path.join(OUT, "receiving_backdrop.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(p, check_existing=False)
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.image_settings.quality = 93
    img.save_render(os.path.join(OUT, "receiving_backdrop.jpg"), scene=sc)
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'; bpy.data.images.remove(img); os.remove(p)
    sc.render.film_transparent = True; sc.render.resolution_x, sc.render.resolution_y = RES
    write_json("receiving_backdrop.json", dict(size=[1920, 960], dock=dock, floorY=proj((0, -3.0, 0))[1]))
    return dict(dock=dock)

# ---------------------------------------------------------------- 2. small delivery truck (seen from inside, doors folded back)
TRUCK = dict(W=1.95, L=3.2, H=2.0)
TRUCK_RES = (1100, 1200)
def build_truck():
    W, L, H = TRUCK["W"], TRUCK["L"], TRUCK["H"]; t = .06
    body = mat("tk_body", TEAL, rough=.4, bump=.08); body_d = mat("tk_body_d", TEAL_D, rough=.45)
    cream = mat("tk_cream", CREAM, rough=.5); inner = mat("tk_inner", (0.84, 0.86, 0.82, 1), rough=.6, bump=.15)
    rib = mat("tk_rib", (0.72, 0.75, 0.74, 1), rough=.35, metal=.6); plank = mat("tk_plank", WOOD, rough=.65, bump=.2, scale=80); plank_l = mat("tk_plank_l", WOOD_L, rough=.65, bump=.2, scale=80)
    steel = mat("tk_steel", (0.70, 0.72, 0.72, 1), rough=.3, metal=.8); rubber = mat("tk_rubber", (0.06, 0.06, 0.06, 1), rough=.85, bump=.2)
    orange = mat("tk_refl", (1.0, 0.45, 0.05, 1), rough=.2, emit=.6); red = mat("tk_tail", (0.9, 0.08, 0.05, 1), rough=.2, emit=.5); amber = mat("tk_amber", (1.0, 0.6, 0.1, 1), rough=.2, emit=1.0)
    box("tk_floor", (W, L, .14), (0, L / 2, -.07), body_d, bevel=.02)
    nplk = 7; pw = (W - 2 * t - .04) / nplk
    for k in range(nplk): box(f"tk_plk{k}", (pw - .012, L - .2, .03), (-W / 2 + t + .02 + (k + .5) * pw, L / 2 + .05, .015), plank if k % 3 else plank_l, bevel=.006)
    box("tk_sill", (W - 2 * t, .08, .05), (0, .04, .015), steel, bevel=.012)
    for sx in (-1, 1):
        box(f"tk_wall{sx}", (t, L, H), (sx * (W / 2 - t / 2), L / 2, H / 2), body, bevel=.02)
        for k in range(5): box(f"tk_rib{sx}_{k}", (.03, .05, H - .3), (sx * (W / 2 - t - .015), .45 + k * (L - .8) / 4, H / 2 - .05), rib, bevel=.008)
        box(f"tk_wall_in{sx}", (.012, L - .1, H - .2), (sx * (W / 2 - t - .006), L / 2, H / 2 - .05), inner, bevel=0)
    box("tk_roof", (W, L, t), (0, L / 2, H - t / 2), body, bevel=.02)
    box("tk_roof_in", (W - 2 * t, L - .1, .01), (0, L / 2, H - t - .005), inner, bevel=0)
    box("tk_front", (W - 2 * t, .05, H - t), (0, L - .05, H / 2 - .02), inner, bevel=.01)
    box("tk_lamp", (.5, .10, .03), (0, L * .45, H - t - .02), mat("tk_lamp", (1, .97, .9, 1), emit=6, bump=0), bevel=.005)
    bpy.ops.object.light_add(type='AREA', location=Vector((0, L * .45, H - .12)) + OFF); l = bpy.context.object; l.name = "tk_light"; l.data.energy = 60; l.data.size = .8; l.data.color = (1, .95, .85); l.rotation_euler = (0, 0, 0); l["layer"] = "light"
    box("tk_frame_T", (W + .02, .10, .14), (0, .05, H - .07), body, bevel=.025)
    for sx in (-1, 1):
        box(f"tk_post{sx}", (.10, .10, H + .1), (sx * (W / 2 - .04), .05, H / 2 - .05), body, bevel=.025)
        for z in (.45, 1.25, 1.85): box(f"tk_hinge{sx}_{z:.1f}", (.05, .06, .14), (sx * (W / 2 + .02), -.02, z), steel, bevel=.012)
    for k in range(3): box(f"tk_marker{k}", (.10, .03, .05), (-W / 2 + .3 + k * (W - .6) / 2, -.012, H - .05), amber if k in (0, 2) else orange, bevel=.012, seg=4)
    # dock seal: black foam pads hugging the box
    for nm, sz, lc in (("tk_seal_T", (W + .44, .30, .30), (0, .16, H + .17)), ("tk_seal_L", (.22, .30, H + .5), (-W / 2 - .11, .16, H / 2 + .10)), ("tk_seal_R", (.22, .30, H + .5), (W / 2 + .11, .16, H / 2 + .10))):
        box(nm, sz, lc, rubber, bevel=.06, seg=4)
        box(nm + "_strp", (sz[0] + .004, .02, .08) if sz[0] > 1 else (.08, .02, sz[2] + .004), (lc[0], lc[1] - sz[1] / 2 - .005, lc[2]), mat("tk_seal_strp", YELLOW, rough=.6), bevel=.006)
    # dock leveler lip bridging the gap between the cargo floor and the room (front layer, under the boxes' feet)
    box("tk_step", (W - .3, .34, .035), (0, -.14, -.012), mat("tk_step", (0.45, 0.47, 0.47, 1), rough=.5, metal=.5, bump=.3, scale=60), bevel=.008, layer="front")
    return dict(target=(0, L * .3, H * .48), pitch=15, dist=6.8, lens=40, size=H)

def cargo_quad():
    W, L = TRUCK["W"], TRUCK["L"]
    return quad(-W / 2 + .14, W / 2 - .14, .16, L - .3, .03)

def render_truck():
    clear(); sc = scene(); v = build_truck()
    camera(v["target"], v["pitch"], v["dist"], v["lens"]); sc.render.resolution_x, sc.render.resolution_y = TRUCK_RES; fit_camera(1.03); light_rig(v["target"], v["size"], warm=.6, world=.3)
    paths = render_layers("receiving_truck", [("back", ["back"]), ("front", ["front"])], res=TRUCK_RES)
    q = cargo_quad(); W, H = TRUCK["W"], TRUCK["H"]
    a = proj((-(DOCK["x1"] - DOCK["x0"]) / 2, 0, 0)); b = proj(((DOCK["x1"] - DOCK["x0"]) / 2, 0, DOCK["h"]))   # the dock opening, in truck space
    write_json("receiving_truck.json", dict(key="truck", size=list(TRUCK_RES), cargo=dict(fl=q["fl"], fr=q["fr"], bl=q["bl"], br=q["br"]), ppm=q["ppm"], ppmBack=q["ppmBack"], boxHeight=.5,
                                            dockRect=[a[0], a[1], b[0], b[1]], screenWidth=.22, cargoColumns=2, cargoRows=3))
    return paths

# ---------------------------------------------------------------- 3. fixtures (one camera family)
FIX_VIEW = dict(pitch=15, lens=40)
def fixture_cam(target, size, warm=.55, world=.28, key_color=(1, .97, .92)):
    sc = bpy.context.scene
    camera(target, FIX_VIEW["pitch"], 6.5, FIX_VIEW["lens"]); sc.render.resolution_x, sc.render.resolution_y = RES; fit_camera(1.03)
    light_rig(target, size, warm=warm, world=world, key_color=key_color)

def sign_board(nm, x, y, z, w=1.9, h=.44, posts=((-.6, .6),)):
    """Cream zone board in a blue frame on two short posts (Unity writes the zone names on the cream area)."""
    up_d = mat("sg_post", TEAL_D, rough=.5)
    for px in posts[0]: box(f"{nm}_post{px:.1f}", (.04, .04, .32), (x + px, y, z - .16), up_d, bevel=.008)
    rounded(f"{nm}_bd", w, h, (x, y, z + .06), mat("sg_bd", TEAL, rough=.45, bump=.04), r=.05, thick=.035, rot=(rad(90), 0, 0))
    sg = rounded(f"{nm}_in", w - .12, h - .12, (x, y - .025, z + .06), mat("sg_in", CREAM, rough=.5, emit=.35, bump=0), r=.04, thick=.01, rot=(rad(90), 0, 0))
    return sg

def rack_frame(key, BW, D, H, levels, post=.09, deck="wood", bays=2, front_label=True):
    """Boltless steel rack: blue uprights (front posts in the front layer), orange box beams, wood or wire decks.
    Returns the beam x centres per bay."""
    up = mat("rk_upright", TEAL, rough=.45, bump=.08); up_d = mat("rk_upright_d", TEAL_D, rough=.5)
    beam = mat("rk_beam", ORANGE, rough=.45, bump=.08); plate = mat("rk_plate", (0.55, 0.58, 0.58, 1), rough=.4, metal=.6)
    bolt = mat("rk_bolt", (0.80, 0.82, 0.82, 1), rough=.3, metal=.9, bump=0); hole = mat("rk_hole", (0.01, 0.06, 0.06, 1), rough=.9, bump=0)
    label = mat("rk_label", WHITE, rough=.5, bump=0); mesh_m = mat("rk_mesh", (0.72, 0.74, 0.72, 1), rough=.35, metal=.7, bump=0)
    deckw = wood_mat("rk_deck", (0.84, 0.64, 0.38, 1), (0.64, 0.45, 0.22, 1), grain=(1.0, 20.0, 20.0))
    xs = [(-bays / 2 + i) * (BW + post) for i in range(bays + 1)]
    for i, x in enumerate(xs):
        for j, y in enumerate((post / 2, D - post / 2)):
            lay = "front" if j == 0 else "back"
            box(f"{key}_post{i}{j}", (post, post, H), (x, y, H / 2), up, bevel=.012, layer=lay)
            box(f"{key}_base{i}{j}", (post + .10, post + .08, .016), (x, y, .008), plate, bevel=.004, layer=lay)
            for sx in (-1, 1): cyl(f"{key}_bolt{i}{j}{sx}", .014, .012, (x + sx * (post / 2 + .035), y, .02), bolt, verts=10, bevel=.003, layer=lay)
            if j == 0:
                for k in range(int((H - .2) / .11)): box(f"{key}_hole{i}_{k}", (.022, .006, .036), (x, -.001, .14 + k * .11), hole, bevel=0, layer=lay)
        for k, z in enumerate((.5, 1.3, H - .05)): box(f"{key}_brace{i}_{k}", (post * .5, D - post, post * .5), (x, D / 2, z), up_d, bevel=.008)
        box(f"{key}_bracex{i}", (post * .4, D - post, post * .4), (x, D / 2, .9), up_d, bevel=.006, rot=(rad(-45), 0, 0))
    centres = []
    for b in range(bays):
        xc = (xs[b] + xs[b + 1]) / 2; w = BW - .01; centres.append(xc)
        for lv, z in enumerate(levels):
            box(f"{key}_beamF{lv}{b}", (w, .05, .10), (xc, .025, z - .05), beam, bevel=.012, layer="front")
            if front_label: box(f"{key}_labelF{lv}{b}", (w * .35, .008, .036), (xc - w * .25, -.004, z - .055), label, bevel=.003, layer="front")
            box(f"{key}_beamB{lv}{b}", (w, .05, .10), (xc, D - .025, z - .05), beam, bevel=.012)
            if deck == "wood":
                nb = 6; bw_ = (D - .10) / nb
                for k in range(nb): box(f"{key}_deck{lv}{b}_{k}", (w - .02, bw_ - .012, .022), (xc, .05 + (k + .5) * bw_, z + .011), deckw, bevel=.004)
            else:
                grid_wire(f"{key}_deck{lv}{b}", w - .02, D - .10, (xc, D / 2, z + .004), mesh_m, nx=14, ny=8, thick=.007)
                for sup in (-1, 0, 1): box(f"{key}_sup{lv}{b}{sup}", (.03, D - .1, .025), (xc + sup * w * .32, D / 2, z - .01), beam, bevel=.006)
    return xs, centres

# --- 3a. SECOS: steel rack 2 bays x 3 levels, wood decks, slots on levels 0-1, dry goods decor on level 2
RACK = dict(BW=1.15, D=0.95, H=2.25, levels=(.16, .86, 1.56))
def build_rack(key="rack"):
    BW, D, H = RACK["BW"], RACK["D"], RACK["H"]; SLOTS.pop(key, None)
    xs, cs = rack_frame(key, BW, D, H, RACK["levels"])
    for lv, z in enumerate(RACK["levels"][:2]):
        for b, xc in enumerate(cs):
            sw = (BW - .08) / 2
            for k in range(2):
                x0 = xc - (BW - .08) / 2 + k * sw
                slot(key, lv, b, k, x0 + .03, x0 + sw - .03, .08, D - .08, z + .025)
    # decor on the top level: flour sacks, a rice-bag stack, two cartons, a tin stack
    z = RACK["levels"][2] + .025
    flour = mat("dc_flour", (0.96, 0.94, 0.88, 1), rough=.85, bump=.3, scale=50); rice = mat("dc_rice", (0.98, 0.98, 0.98, 1), rough=.6, bump=.2, scale=50)
    sugar = mat("dc_sugar", (0.95, 0.62, 0.20, 1), rough=.7, bump=.25, scale=50)
    sack("dc_sack0", (cs[0] - .32, D * .5, z), flour, rot_z=rad(6)); sack("dc_sack1", (cs[0] + .20, D * .48, z), sugar, w=.40, rot_z=rad(-4)); sack("dc_sack2", (cs[0] - .06, D * .5, z + .29), flour, w=.40, h=.26, rot_z=rad(2))
    box("dc_rice_lbl", (.16, .004, .10), (cs[0] + .20, D * .48 - .145, z + .15), mat("dc_rice_lbl", (0.10, 0.45, 0.25, 1), rough=.7, bump=0), bevel=.003)
    carton_deco("dc_ct0", (cs[1] - .34, D * .5, z), w=.44, h=.36); carton_deco("dc_ct1", (cs[1] + .22, D * .52, z), w=.40, d=.36, h=.30, rot_z=rad(5))
    carton_deco("dc_ct2", (cs[1] + .22, D * .52, z + .30), w=.36, d=.32, h=.22, rot_z=rad(-3))
    tin = mat("dc_tin", (0.80, 0.82, 0.80, 1), rough=.3, metal=.8, bump=0); tin_l = mat("dc_tin_l", (0.85, 0.20, 0.12, 1), rough=.5, bump=0)
    for k in range(3):
        cyl(f"dc_tin{k}", .075, .16, (cs[0] + .54, D * .4 + k * .17 - .17, z + .08), tin, verts=24, bevel=.004)
        cyl(f"dc_tin_l{k}", .076, .10, (cs[0] + .54, D * .4 + k * .17 - .17, z + .08), tin_l, verts=24)
    # floor decor: a pallet with a bag stack beside the left upright (back layer, outside the bays)
    sg = sign_board(key + "_sign", 0, D / 2, H + .30, w=2.0)
    return dict(target=(0, D * .35, H * .52), size=H, sign=sg, widthM=2 * BW + 3 * .09 + .10)

def render_fixture(key, build, boxH=.42, extra=None):
    clear(); sc = scene(); v = build()
    fixture_cam(v["target"], v["size"], **(v.get("light") or {}))
    paths = render_layers("receiving_" + key, [("back", ["back"]), ("front", ["front"])])
    data = dict(key=key, size=list(RES), slots=slots_json(key), boxHeight=boxH, body=body_rect(), bodyWidthM=round(v.get("widthM", 0), 3))
    if v.get("sign") is not None: data["sign"] = obj_rect(v["sign"])
    if v.get("display") is not None: data["display"] = obj_rect(v["display"])
    if extra: data.update(extra(v))
    write_json(f"receiving_{key}.json", data)
    return paths

def render_rack(): return render_fixture("rack", build_rack)

# --- 3b. BEBIDAS: heavy rack with a pallet base level, wire deck above; water packs + bottle crates as decor on top
DRINKS = dict(BW=1.15, D=1.0, H=2.25, levels=(.95, 1.70))
def build_drinks(key="drinks"):
    BW, D, H = DRINKS["BW"], DRINKS["D"], DRINKS["H"]; SLOTS.pop(key, None)
    xs, cs = rack_frame(key, BW, D, H, DRINKS["levels"], deck="wire")
    # ground level: a wooden pallet in each bay, 2 slots on each pallet
    for b, xc in enumerate(cs):
        pallet(f"{key}_pal{b}", (xc, D / 2, 0), w=BW - .12, d=D - .12)
        sw = (BW - .16) / 2
        for k in range(2):
            x0 = xc - (BW - .16) / 2 + k * sw
            slot(key, 0, b, k, x0 + .03, x0 + sw - .03, .10, D - .10, .15)
    # level 1 (wire deck): 2 slots per bay
    z = DRINKS["levels"][0]
    for b, xc in enumerate(cs):
        sw = (BW - .08) / 2
        for k in range(2):
            x0 = xc - (BW - .08) / 2 + k * sw
            slot(key, 1, b, k, x0 + .03, x0 + sw - .03, .08, D - .08, z + .02)
    # top level decor: water packs and bottle crates (brand colours: orange and blue)
    z = DRINKS["levels"][1] + .02
    water_pack("dc_wp0", (cs[0] - .30, D * .5, z)); water_pack("dc_wp1", (cs[0] + .28, D * .5, z), cap=(1.0, 0.35, 0.05, 1))
    water_pack("dc_wp2", (cs[0] - .02, D * .5, z + .30), n=(2, 2), cap=(0.10, 0.45, 0.85, 1))
    crate_o = mat("dc_crate_o", (1.0, 0.45, 0.05, 1), rough=.45, bump=.05); crate_b = mat("dc_crate_b", (0.06, 0.30, 0.65, 1), rough=.45, bump=.05)
    bottle_crate("dc_bc0", (cs[1] - .32, D * .5, z), crate_o); bottle_crate("dc_bc1", (cs[1] + .14, D * .5, z), crate_b); bottle_crate("dc_bc2", (cs[1] - .10, D * .5, z + .30), crate_b)
    sg = sign_board(key + "_sign", 0, D / 2, H + .30, w=2.0)
    return dict(target=(0, D * .35, H * .52), size=H, sign=sg, widthM=2 * BW + 3 * .09 + .10)

def render_drinks(): return render_fixture("drinks", build_drinks, boxH=.40)

# --- 3c. HORTIFRUTI | PAES: tiered wooden crate display (bay 0) and a stainless bakery trolley with trays (bay 1)
PRODUCE = dict(BW=1.30, D=1.0, H=2.0)
def build_produce(key="produce"):
    BW, D, H = PRODUCE["BW"], PRODUCE["D"], PRODUCE["H"]; SLOTS.pop(key, None)
    pine = wood_mat("pr_pine", (0.86, 0.64, 0.36, 1), (0.64, 0.44, 0.22, 1), grain=(1.0, 18.0, 18.0)); pine_d = wood_mat("pr_pine_d", (0.55, 0.36, 0.18, 1), (0.40, 0.25, 0.12, 1), grain=(18.0, 18.0, 1.0))
    chalk = mat("pr_chalk", (0.12, 0.14, 0.13, 1), rough=.9, bump=.2, scale=30); chalk_ink = mat("pr_chalk_ink", (0.95, 0.95, 0.92, 1), rough=.9, bump=0)
    xl = -BW / 2 - .05; xr = BW / 2 + .05        # bay centres
    # bay 0: tiered produce stand: solid pine side panels with a staircase profile, three stepped shelves with
    # front lips; the top shelf holds fruit crates, the lower two have the slots
    tiers = ((.28, .10, .80), (.74, .42, .50), (1.20, .70, .30))     # (z at the front edge, y front, depth)
    tilt = rad(6)
    for sx in (-1, 1):
        for k, (z, y, d) in enumerate(tiers):
            zt = z + d * math.sin(tilt)
            box(f"pr_sidep{sx}{k}", (.04, d + .04, zt + .02), (xl + sx * (BW / 2 - .02), y + d / 2, (zt + .02) / 2), pine_d, bevel=.006, layer="front" if k == 0 else "back")
        box(f"pr_sideb{sx}", (.04, .22, H - .1), (xl + sx * (BW / 2 - .02), D - .11, (H - .1) / 2), pine_d, bevel=.006)
    box("pr_top", (BW, .05, .05), (xl, D - .03, H - .1), pine_d, bevel=.006)
    box("pr_backp", (BW - .08, .03, 1.0), (xl, D - .015, H - .62), pine, bevel=.004)
    for k, (z, y, d) in enumerate(tiers):
        zc = z + d * math.sin(tilt) / 2; yc = y + d * math.cos(tilt) / 2
        for j in range(4): box(f"pr_tier{k}_{j}", (BW - .08, d / 4 - .008, .024), (xl, yc + (j - 1.5) * d / 4 * math.cos(tilt), zc + (j - 1.5) * d / 4 * math.sin(tilt)), pine, bevel=.004, rot=(tilt, 0, 0))
        box(f"pr_lip{k}", (BW - .06, .025, .09), (xl, y - .01, z + .03), pine_d, bevel=.005, layer="front")
        box(f"pr_under{k}", (BW - .08, .025, z - .02 if k == 0 else .12), (xl, y + .01, (z - .02) / 2 if k == 0 else z - .07), pine_d, bevel=.004, layer="front" if k == 0 else "back")
        if k < 2:
            sw = (BW - .16) / 2
            for i in range(2):
                x0 = xl - (BW - .16) / 2 + i * sw
                slot(key, k, 0, i, x0 + .02, x0 + sw - .02, y + .03, y + d * math.cos(tilt) * .62, z + d * math.sin(tilt) * .3 + .024)
    # top shelf decor: fruit crates; a chalkboard over the stand
    z, y, d = tiers[2]
    tomato = mat("dc_tomato", (0.85, 0.09, 0.05, 1), rough=.3, bump=.05); lime = mat("dc_lime", (0.36, 0.66, 0.10, 1), rough=.4, bump=.1); orng = mat("dc_orange", (1.0, 0.38, 0.03, 1), rough=.45, bump=.15, scale=200)
    fruit_crate("dc_fc0", (xl - .34, y + .17, z + .03), tomato, w=.46, d=.30, rot_z=rad(3), seed=1)
    fruit_crate("dc_fc1", (xl + .22, y + .17, z + .03), orng, w=.46, d=.30, rot_z=rad(-3), seed=2)
    fruit_crate("dc_fc2", (xl - .08, y + .17, z + .03 + .27), lime, w=.44, d=.28, rot_z=rad(2), seed=5)
    chalk = chalk; rounded("pr_board", .95, .30, (xl, D - .06, H + .02), chalk, r=.02, thick=.02, rot=(rad(90), 0, 0))
    rounded("pr_board_fr", .95, .30, (xl, D - .07, H + .02), pine_d, r=.02, thick=.02, rot=(rad(90), 0, 0), frame=.03)
    text("pr_board_txt", "FRUTAS & LEGUMES", .085, (xl, D - .075, H + .02), chalk_ink, rot=(rad(90), 0, 0), bold=True)
    # bay 1: bakery trolley: stainless frame on casters with tray rails; 3 trays with slots, the top tray holds bread
    inox = mat("pr_inox", (0.80, 0.82, 0.82, 1), rough=.25, metal=.9, bump=0); inox_d = mat("pr_inox_d", (0.60, 0.62, 0.62, 1), rough=.35, metal=.8, bump=0)
    tw, td, th = BW - .06, .75, 1.85; ty = D / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(f"pr_tpost{sx}{sy}", .024, th, (xr + sx * tw / 2, ty + sy * td / 2, th / 2 + .08), inox, verts=14, layer="front" if sy < 0 else "back")
            cyl(f"pr_caster{sx}{sy}", .045, .03, (xr + sx * tw / 2, ty + sy * td / 2, .045), mat("pr_caster", (0.12, 0.12, 0.13, 1), rough=.5), rot=(0, rad(90), 0), verts=16, layer="front" if sy < 0 else "back")
        for sy in (-1, 1): box(f"pr_tbar{sx}{sy}", (.03, td, .03), (xr + sx * tw / 2, ty, th + .08), inox, bevel=.006)
    for sy in (-1, 1): box(f"pr_ttop{sy}", (tw, .03, .03), (xr, ty + sy * td / 2, th + .08), inox, bevel=.006, layer="front" if sy < 0 else "back")
    box("pr_tbase", (tw + .02, td, .04), (xr, ty, .10), inox_d, bevel=.008)
    nr = 10
    for k in range(nr):
        zz = .22 + k * .16
        for sx in (-1, 1): box(f"pr_rail{sx}{k}", (.025, td - .06, .012), (xr + sx * (tw / 2 - .02), ty, zz), inox_d, bevel=.003)
    tray_z = (.38, .86, 1.34)
    for k, zz in enumerate(tray_z):
        alu = mat("dc_alu", (0.72, 0.74, 0.74, 1), rough=.3, metal=.8, bump=.06)
        box(f"pr_tray{k}", (tw - .06, td - .10, .012), (xr, ty, zz), alu, bevel=.004)
        for sy in (-1, 1): box(f"pr_tray{k}_ry{sy}", (tw - .06, .012, .03), (xr, ty + sy * (td / 2 - .056), zz + .01), alu, bevel=.003, layer="front" if sy < 0 else "back")
        if k < 2:
            sw = (tw - .14) / 2
            for i in range(2): slot(key, k, 1, i, xr - (tw - .14) / 2 + i * sw + .02, xr - (tw - .14) / 2 + (i + 1) * sw - .02, ty - td / 2 + .10, ty + td / 2 - .10, zz + .012)
    bread_tray("dc_bt0", (xr, ty, tray_z[2] + .006), w=tw - .06, d=td - .10, loaves=8, seed=2)
    rounded("pr_board2", .72, .30, (xr, D - .06, H + .02), chalk, r=.02, thick=.02, rot=(rad(90), 0, 0))
    rounded("pr_board2_fr", .72, .30, (xr, D - .07, H + .02), pine_d, r=.02, thick=.02, rot=(rad(90), 0, 0), frame=.03)
    text("pr_board2_txt", "PÃES", .11, (xr, D - .075, H + .02), chalk_ink, rot=(rad(90), 0, 0), bold=True)
    # a flour sack and a pine crate on the floor between the bays
    sg = sign_board(key + "_sign", 0, D / 2, H + .52, w=2.2)
    return dict(target=(0, D * .35, H * .55), size=H + .2, sign=sg, widthM=2 * BW + .10)

def render_produce(): return render_fixture("produce", build_produce, boxH=.36)

# --- 3d. CAMARA FRIA: walk-in cooler, insulated panels, a sliding stainless door slid open, wire shelving in cold light
COLD = dict(W=3.0, D=1.8, H=2.5, ow=1.58, oh=2.12, ox=-.56, levels=(.42, 1.22))
def build_coldroom(key="coldroom"):
    W, D, H, ow, oh, ox = COLD["W"], COLD["D"], COLD["H"], COLD["ow"], COLD["oh"], COLD["ox"]; SLOTS.pop(key, None); t = .12
    panel = mat("cr_panel", (0.95, 0.96, 0.95, 1), rough=.4, bump=.05, scale=20); trim = mat("cr_trim", (0.82, 0.84, 0.85, 1), rough=.22, metal=.95, bump=0)
    inner = mat("cr_inner", (0.78, 0.88, 0.95, 1), rough=.5, bump=.06); shelf = mat("cr_shelf", (0.80, 0.82, 0.82, 1), rough=.3, metal=.85, bump=0)
    disp = mat("cr_disp", (0.03, 0.04, 0.05, 1), rough=.3, bump=0); led = mat("cr_led", (0.35, 0.90, 1.0, 1), emit=6, bump=0)
    kick = mat("cr_kick", (0.62, 0.64, 0.65, 1), rough=.3, metal=.9, bump=.05, scale=80); seam = mat("cr_seam", (0.80, 0.82, 0.82, 1), rough=.5, bump=0)
    # panels, roof, floor; the inside is light blue
    box("cr_side_L", (t, D, H), (-W / 2 + t / 2, D / 2, H / 2), panel, bevel=.03, seg=4)
    box("cr_side_R", (t, D, H), (W / 2 - t / 2, D / 2, H / 2), panel, bevel=.03, seg=4)
    box("cr_roof", (W, D, t), (0, D / 2, H - t / 2), panel, bevel=.03, seg=4)
    box("cr_back", (W - 2 * t, .06, H - t), (0, D - .03, (H - t) / 2), inner, bevel=.01)
    box("cr_inL", (.02, D - .1, H - t), (-W / 2 + t + .01, D / 2, (H - t) / 2), inner, bevel=0); box("cr_inR", (.02, D - .1, H - t), (W / 2 - t - .01, D / 2, (H - t) / 2), inner, bevel=0)
    box("cr_ceil", (W - 2 * t, D - .1, .02), (0, D / 2, H - t - .01), inner, bevel=0)
    box("cr_floor", (W, D, .06), (0, D / 2, .03), mat("cr_floor", (0.50, 0.54, 0.58, 1), rough=.35, metal=.4, bump=.3, scale=50), bevel=.01)
    box("cr_lamp", (ow + .3, .08, .02), (ox, D * .35, H - t - .025), mat("cr_lampm", (.80, .95, 1, 1), emit=14, bump=0), bevel=0)
    bpy.ops.object.light_add(type='AREA', location=Vector((ox, D * .4, H - t - .1)) + OFF); l = bpy.context.object; l.name = "cr_light"; l.data.energy = 120; l.data.size = 1.6; l.data.color = (.55, .80, 1.0); l.rotation_euler = (0, 0, 0); l["layer"] = "light"
    # front wall around the opening (front layer): left strip, right part, top strip; seams between panels
    xl_, xr_ = ox - ow / 2, ox + ow / 2
    box("cr_front_L", (xl_ + W / 2, t, H), ((-W / 2 + xl_) / 2, t / 2 - .02, H / 2), panel, bevel=.03, seg=4, layer="front")
    box("cr_front_R", (W / 2 - xr_, t, H), ((xr_ + W / 2) / 2, t / 2 - .02, H / 2), panel, bevel=.03, seg=4, layer="front")
    box("cr_front_T", (ow + .02, t, H - oh), (ox, t / 2 - .02, oh + (H - oh) / 2), panel, bevel=.03, seg=4, layer="front")
    for xx in (xr_ + .55, xr_ + 1.1):
        if xx < W / 2 - .1: box(f"cr_seam{xx:.1f}", (.006, .004, H - .05), (xx, -.082, H / 2), seam, bevel=0, layer="front")
    for nm, sz, lc in (("cr_trim_L", (.06, .07, oh + .06), (xl_ - .03, -.055, oh / 2)), ("cr_trim_R", (.06, .07, oh + .06), (xr_ + .03, -.055, oh / 2)), ("cr_trim_T", (ow + .12, .07, .06), (ox, -.055, oh + .03))):
        box(nm, sz, lc, trim, bevel=.012, layer="front")
    box("cr_kick", (W, .03, .30), (0, -.095, .15), kick, bevel=.008, layer="front")
    box("cr_sill", (ow, .12, .02), (ox, -.02, .07), trim, bevel=.005, layer="front")
    # sliding door on a top rail, slid open to the right (front layer): white insulated leaf with stainless edges,
    # a vertical pull bar on its leading edge, the "CÂMARA FRIA" plate and a snowflake badge
    dw, dh_, dt = ow + .08, oh + .10, .09
    dx = xr_ + .06 + dw / 2 - .30         # leaf overlaps the opening's right trim by a few cm
    dy = -.16 - dt / 2
    box("cr_rail", (W - .3, .10, .08), (0, -.16, H - .18), trim, bevel=.012, layer="front")
    for k in range(4): box(f"cr_rail_bk{k}", (.06, .06, .10), (-W / 2 + .35 + k * (W - .7) / 3, -.11, H - .18), trim, bevel=.008, layer="front")
    for sxx in (-1, 1):
        box(f"cr_roller{sxx}", (.10, .06, .16), (dx + sxx * (dw / 2 - .15), dy, dh_ + .08), trim, bevel=.01, layer="front")
        cyl(f"cr_wheel{sxx}", .05, .04, (dx + sxx * (dw / 2 - .15), dy, H - .18), mat("cr_wheel", (0.15, 0.15, 0.16, 1), rough=.5), rot=(rad(90), 0, 0), verts=20, layer="front")
    box("cr_door", (dw, dt, dh_), (dx, dy, dh_ / 2 + .02), panel, bevel=.03, seg=4, layer="front")
    box("cr_door_edge", (dw + .01, .02, dh_ + .01), (dx, dy - dt / 2 - .005, dh_ / 2 + .02), trim, bevel=.006, layer="front")
    box("cr_door_in", (dw - .22, .01, dh_ - .36), (dx, dy - dt / 2 - .014, dh_ / 2 + .08), mat("cr_door_in", (0.90, 0.93, 0.95, 1), rough=.5, bump=.05), bevel=.01, layer="front")
    box("cr_door_kick", (dw, .012, .30), (dx, dy - dt / 2 - .012, .17), kick, bevel=.006, layer="front")
    box("cr_pull", (.05, .06, .60), (dx - dw / 2 + .14, dy - dt / 2 - .05, dh_ / 2 + .05), trim, bevel=.015, seg=4, layer="front")
    for zz in (dh_ / 2 - .22, dh_ / 2 + .32): box(f"cr_pull_a{zz:.1f}", (.04, .04, .05), (dx - dw / 2 + .14, dy - dt / 2 - .025, zz), trim, bevel=.008, layer="front")
    rounded("cr_door_lbl", .70, .18, (dx + .08, dy - dt / 2 - .02, dh_ * .74), mat("cr_lbl", BLUE, rough=.5, bump=0), r=.03, thick=.01, rot=(rad(90), 0, 0), layer="front")
    text("cr_door_txt", "CÂMARA FRIA", .085, (dx + .08, dy - dt / 2 - .03, dh_ * .74), mat("cr_lbl_ink", CREAM, rough=.8, bump=0), rot=(rad(90), 0, 0), layer="front", bold=True)
    rounded("cr_snow", .26, .26, (dx + .08, dy - dt / 2 - .02, dh_ * .50), mat("cr_snow_bd", BLUE_L, rough=.5, bump=0), r=.04, thick=.01, rot=(rad(90), 0, 0), layer="front")
    for k in range(3): box(f"cr_snow_f{k}", (.016, .004, .17), (dx + .08, dy - dt / 2 - .03, dh_ * .50), mat("cr_snow_ink", (0.95, 0.98, 1, 1), rough=.8, bump=0), bevel=0, rot=(0, rad(k * 60), 0), layer="front")
    text("cr_temp_txt", "MANTER A -2°C", .05, (dx + .08, dy - dt / 2 - .03, dh_ * .34), mat("cr_lbl_ink2", (0.25, 0.30, 0.35, 1), rough=.8, bump=0), rot=(rad(90), 0, 0), layer="front")
    # digital thermometer on the left strip
    tx = (-W / 2 + xl_) / 2
    box("cr_disp_box", (.26, .05, .18), (tx, -.085, oh - .25), mat("cr_disp_case", (0.85, 0.86, 0.86, 1), rough=.3, metal=.5, bump=0), bevel=.012, layer="front")
    dsp = box("cr_display", (.20, .01, .10), (tx, -.112, oh - .24), disp, bevel=.004, layer="front")
    text("cr_disp_txt", "-2°C", .065, (tx, -.119, oh - .24), led, rot=(rad(90), 0, 0), layer="front")
    # inside: chrome wire shelving behind the opening, 2 levels x 4 places; frost on the back wall; a milk-crate stack
    iw = ow + .20; sd = D - .50; yc = D / 2 + .12
    for lv, z in enumerate(COLD["levels"]):
        grid_wire(f"cr_deck{lv}", iw, sd, (ox, yc, z), shelf, nx=22, ny=8, thick=.007)
        for yy in (yc - sd / 2, yc + sd / 2): box(f"cr_shelf_edge{lv}{yy:.1f}", (iw, .03, .035), (ox, yy, z - .012), shelf, bevel=.008)
        slw = (iw - .08) / 3
        for k in range(3):
            x0 = ox - iw / 2 + .04 + k * slw
            slot(key, lv, 0, k, x0 + .02, x0 + slw - .02, yc - sd / 2 + .05, yc + sd / 2 - .05, z + .01)
    for sxx in (-1, 1):
        for yy in (yc - sd / 2 + .02, yc + sd / 2 - .02):
            cyl(f"cr_leg{sxx}{yy:.1f}", .016, COLD["levels"][1] + .3, (ox + sxx * (iw / 2 - .02), yy, (COLD["levels"][1] + .3) / 2), shelf, verts=12)
    crate_m = mat("dc_milk", (0.10, 0.45, 0.85, 1), rough=.45, bump=.05)
    for k in range(2): bottle_crate(f"cr_mc{k}", (W / 2 - t - .45, D - .40, .06 + k * .28), crate_m, w=.36, d=.30)
    frost = mat("cr_frost", (0.92, 0.97, 1.0, 1), rough=.9, bump=.4, scale=90)
    rnd = random.Random(7)
    for k in range(10): sphere(f"cr_frost{k}", rnd.uniform(.05, .12), (rnd.uniform(-W / 2 + t + .1, W / 2 - t - .1), D - .05, H - t - rnd.uniform(.02, .25)), frost, scale=(1.4, .3, .8))
    sg = sign_board(key + "_sign", 0, D / 2, H + .30, w=2.0)
    return dict(target=(0, D * .3, H * .5), size=H, sign=sg, display=dsp, light=dict(key_color=(.95, .97, 1.0)), widthM=max(W, dx + dw / 2 + W / 2))

def render_coldroom(): return render_fixture("coldroom", build_coldroom, boxH=.42)

# ---------------------------------------------------------------- 4. box sprites (unchanged designs from v1)
BOX_RES = (512, 512); BOX_VIEW = dict(pitch=18, yaw=28, lens=45)
def arrow(nm, x, y, z, m, h=.07, layer="back"):
    box(nm + "_s", (.009, .002, h), (x, y, z), m, bevel=0, layer=layer)
    box(nm + "_l", (.009, .002, h * .5), (x - h * .16, y, z + h * .34), m, bevel=0, layer=layer, rot=(0, rad(45), 0))
    box(nm + "_r", (.009, .002, h * .5), (x + h * .16, y, z + h * .34), m, bevel=0, layer=layer, rot=(0, rad(-45), 0))

def build_box_carton():
    W, D, H = .50, .40, .40
    card = mat("bx_card", CARD, rough=.8, bump=.22, scale=120); card_d = mat("bx_card_d", CARD_D, rough=.85, bump=.2, scale=120)
    tape = mat("bx_tape", (0.66, 0.46, 0.24, 1), rough=.25, bump=.04, alpha=.9); ink = mat("bx_ink", (0.12, 0.10, 0.10, 1), rough=.8, bump=0)
    white = mat("bx_label", (0.96, 0.96, 0.94, 1), rough=.6, bump=0)
    box("bx_body", (W, D, H - .03), (0, 0, (H - .03) / 2), card, bevel=.012, seg=4)
    for sx in (-1, 1):
        box(f"bx_flap{sx}", (W / 2 - .004, D, .03), (sx * W / 4, 0, H - .015 + (.004 if sx > 0 else 0)), card, bevel=.008)
        box(f"bx_flap_edge{sx}", (.006, D - .01, .022), (sx * .004, 0, H - .015), card_d, bevel=0)
    box("bx_tape_top", (.07, D + .004, .006), (0, 0, H + .002), tape, bevel=.002)
    box("bx_tape_front", (.07, .006, .12), (0, -D / 2 - .002, H - .06), tape, bevel=.002)
    box("bx_tape_back", (.07, .006, .12), (0, D / 2 + .002, H - .06), tape, bevel=.002)
    lab = box("bx_label", (.20, .006, .14), (W * .14, -D / 2 - .003, H * .50), white, bevel=.003)
    text("bx_fragil", "FRÁGIL", .038, (-W * .30, -D / 2 - .004, H * .62), ink, rot=(rad(90), 0, 0), bold=True)
    arrow("bx_arr0", -W * .34, -D / 2 - .002, H * .36, ink); arrow("bx_arr1", -W * .24, -D / 2 - .002, H * .36, ink)
    text("bx_side", "CHECKOUT", .030, (W / 2 + .004, .02, H * .55), ink, rot=(rad(90), 0, rad(90)))
    box("bx_dent", (.10, .006, .05), (-W * .30, D / 2 - .002, H * .25), card_d, bevel=.004)
    return dict(label=lab, size=(W, D, H))

def build_box_crate():
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
        for sy in (-1, 1): box(f"bx_cr_post{sx}{sy}", (pw, pw, H - .01), (sx * px, sy * py, (H - .01) / 2), post_m, bevel=.004)
    for k in range(5): box(f"bx_cr_floor{k}", (W - 2 * t - .01, (D - 2 * t - .02) / 5 - .012, .016), (0, -(D - 2 * t - .02) / 2 + ((D - 2 * t - .02) / 5) * (k + .5), .035), floor_m, bevel=.003)
    zs = (.045, .135, .235); bh = .062
    for k, z in enumerate(zs):
        for sy in (-1, 1):
            y = sy * (D / 2 - t / 2)
            if k == 2:
                for sx in (-1, 1): box(f"bx_cr_bdY{sy}{k}{sx}", ((W - .11) / 2, t, bh), (sx * (W / 4 + .0275), y, z), pine_x, bevel=.003)
            else: box(f"bx_cr_bdY{sy}{k}", (W, t, bh), (0, y, z), pine_x, bevel=.003)
            for sx in (-1, 1):
                for dz in (-.016, .016): cyl(f"bx_cr_nail{sy}{k}{sx}{dz:+.3f}", .0045, .004, (sx * px, y - sy * t / 2 - sy * .001, z + dz), nail, rot=(rad(90), 0, 0), verts=10)
        for sx in (-1, 1):
            box(f"bx_cr_bdX{sx}{k}", (t, D - 2 * t - .004, bh), (sx * (W / 2 - t / 2), 0, z), pine_y, bevel=.003)
            for sy in (-1, 1): cyl(f"bx_cr_nailX{sx}{k}{sy}", .0045, .004, (sx * (W / 2 + .001), sy * py, z), nail, rot=(0, rad(90), 0), verts=10)
    rnd = random.Random(11)
    for k in range(14):
        x = (-W / 2 + .07) + (W - .14) * (k % 4 + .5) / 4 + rnd.uniform(-.02, .02); y = (-D / 2 + .07) + (D - .14) * ((k // 4) % 3 + .5) / 3 + rnd.uniform(-.02, .02)
        z = .20 + (0.04 if k >= 12 else 0); rr = rnd.uniform(.045, .06)
        sphere(f"bx_fruit{k}", rr, (x, y, z + rr * .4), (tomato, lime, orange)[k % 3], scale=(1, 1, .9))
    for k in range(3): sphere(f"bx_fruit_top{k}", .05, (-.12 + k * .12, rnd.uniform(-.04, .04), .29), (orange, lime, tomato)[k], scale=(1, 1, .9))
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
    def flake(nm, x, y, z, r):
        for k in range(3): box(f"{nm}_{k}", (.008, .002, r * 2), (x, y - k * .0012, z), snow, bevel=0, rot=(0, rad(k * 60), 0))
    for k, x in enumerate((-.15, -.05, .05, .15)): flake(f"bx_fk{k}", x, -D / 2 - .003, .11, .03)
    for k, y in enumerate((-.10, 0, .10)):
        for j in range(3): box(f"bx_fks{k}_{j}", (.002, .008, .06), (W / 2 + .003 + j * .0012, y, .11), snow, bevel=0, rot=(rad(j * 60), 0, 0))
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
        for j in range(3): sphere(f"bx_egg{i}{j}", .048, (-W / 2 + .07 + i * .12, -D / 2 + .065 + j * .125, .085), egg, scale=(1, 1, 1.25))
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
    marks = dict(label=obj_rect(v["label"]))
    paths = render_layers("box_" + name, [("", ["back", "front"])], res=BOX_RES)
    write_json(f"box_{name}_marks.json", marks)
    return paths

def render_boxes():
    for k in BOXES: render_box(k)

# ---------------------------------------------------------------- 5. clipboard (600 x 800) and 6. stamp (512 x 512)
CLIP_RES = (600, 800)
def build_clipboard():
    """Blue hardboard clipboard with a chrome clip and a printed delivery note. Unity writes the title (white, on the
    header band) and the 6 product lines; everything else is printed here."""
    W, H = .23, .32
    board = mat("cb_board", BLUE, rough=.5, bump=.12, scale=60); board_d = mat("cb_board_d", BLUE_D, rough=.5, bump=0)
    clip = mat("cb_clip", (0.84, 0.86, 0.88, 1), rough=.18, metal=.95, bump=0)
    paper = mat("cb_paper", (0.99, 0.99, 0.97, 1), rough=.75, bump=.03, scale=200, emit=.3); band = mat("cb_band", BLUE, rough=.6, bump=0)
    line = mat("cb_line", (0.78, 0.80, 0.84, 1), rough=.8, bump=0); ink = mat("cb_ink", (0.25, 0.27, 0.32, 1), rough=.9, bump=0)
    ink_l = mat("cb_ink_l", (0.55, 0.58, 0.62, 1), rough=.9, bump=0); orange = mat("cb_orange", ORANGE, rough=.6, bump=0)
    rounded("cb_board", W, H, (0, 0, .004), board, r=.012, thick=.008)
    rounded("cb_board_rim", W, H, (0, 0, .0085), board_d, r=.012, thick=.001, frame=.006)
    sw, sh = W - .028, H - .048
    sy = -.010
    sheet = box("cb_sheet", (sw, sh, .0016), (0, sy, .0092), paper, bevel=.0008)
    box("cb_sheet2", (sw, sh, .0008), (.0015, sy - .0015, .0083), mat("cb_paper2", (0.93, 0.93, 0.90, 1), rough=.8, bump=0), bevel=0)
    top = sy + sh / 2
    # header band (Unity's title goes here), supplier logo row, column header, 6 ruled lines with a check box, footer
    box("cb_header", (sw, .026, .0012), (0, top - .013, .0102), band, bevel=.0005)
    cyl("cb_logo", .009, .0012, (-sw / 2 + .016, top - .041, .0102), orange, verts=24)
    text("cb_logo_txt", "CK", .009, (-sw / 2 + .016, top - .041, .011), mat("cb_logo_ink", CREAM, rough=.8, bump=0), bold=True)
    text("cb_supplier", "Distribuidora Checkout Ltda.", .0075, (-sw / 2 + .030, top - .038, .011), ink, align='LEFT', bold=True)
    text("cb_supplier2", "Pedido Nº 0421  ·  Entrega: hoje", .0062, (-sw / 2 + .030, top - .0475, .011), ink_l, align='LEFT')
    box("cb_rule0", (sw - .016, .0008, .0008), (0, top - .055, .0102), line, bevel=0)
    text("cb_col_prod", "PRODUTO", .0068, (-sw / 2 + .012, top - .062, .011), ink, align='LEFT', bold=True)
    text("cb_col_qtd", "QTD", .0068, (sw / 2 - .036, top - .062, .011), ink, align='CENTER', bold=True)
    text("cb_col_chk", "OK", .0062, (sw / 2 - .014, top - .062, .011), ink, align='CENTER', bold=True)
    box("cb_rule1", (sw - .016, .0012, .0008), (0, top - .068, .0102), ink_l, bevel=0)
    n, step, y0 = 6, .024, top - .081
    for k in range(n):
        y = y0 - k * step
        box(f"cb_line{k}", (sw - .016, .0008, .0008), (0, y - step / 2 + .002, .0102), line, bevel=0)
        rounded(f"cb_chk{k}", .010, .010, (sw / 2 - .014, y, .0103), ink_l, r=.002, thick=.0006, frame=.0012)
    yf = y0 - n * step - .006
    box("cb_rule2", (sw - .016, .0012, .0008), (0, yf, .0102), ink_l, bevel=0)
    text("cb_foot", "Conferido por: ____________", .0062, (-sw / 2 + .012, yf - .012, .011), ink_l, align='LEFT')
    text("cb_foot2", "Assinatura do estoque", .0055, (sw / 2 - .012, yf - .012, .011), ink_l, align='RIGHT')
    # the clip
    box("cb_clip_base", (.095, .026, .012), (0, H / 2 - .018, .014), clip, bevel=.004, seg=4)
    box("cb_clip_jaw", (.075, .020, .006), (0, H / 2 - .036, .012), clip, bevel=.003, seg=4)
    cyl("cb_clip_hinge", .008, .095, (0, H / 2 - .010, .022), clip, rot=(0, rad(90), 0), verts=20)
    box("cb_clip_lever", (.055, .018, .004), (0, H / 2 - .030, .030), clip, bevel=.002, rot=(rad(-25), 0, 0))
    cyl("cb_hole", .006, .012, (0, H / 2 - .008, .004), mat("cb_hole", DARK, rough=.9, bump=0), verts=12)
    return dict(sheet=sheet, lines=dict(x0=-sw / 2 + .010, x1=sw / 2 - .006, yTop=y0, step=step, n=n), size=(W, H))

def render_clipboard():
    clear(); sc = scene(); v = build_clipboard(); W, H = v["size"]
    camera((0, -.004, 0), 84, 1.0, 50); sc.render.resolution_x, sc.render.resolution_y = CLIP_RES; fit_camera(1.05)
    light_rig((0, 0, 0), .45, warm=.45, world=.3)
    data = dict(size=list(CLIP_RES), sheet=obj_rect(v["sheet"]))
    L = v["lines"]
    data["lines"] = [dict(x0=proj((L["x0"], L["yTop"] - k * L["step"], .011))[0], x1=proj((L["x1"], L["yTop"] - k * L["step"], .011))[0],
                          y=proj((0, L["yTop"] - k * L["step"] - L["step"] * .45, .011))[1]) for k in range(L["n"])]
    paths = render_layers("receiving_clipboard", [("", ["back", "front"])], res=CLIP_RES)
    write_json("receiving_clipboard.json", data)
    return paths

def build_stamp():
    ink = mat("st_ink", (0.80, 0.08, 0.06, 1), rough=.9, bump=0, emit=.5)
    nt = ink.node_tree; b = nt.nodes["Principled BSDF"]
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 70; n.inputs["Detail"].default_value = 6; n.inputs["Roughness"].default_value = .7
    rmp = nt.nodes.new("ShaderNodeValToRGB"); rmp.color_ramp.elements[0].position = .34; rmp.color_ramp.elements[1].position = .50
    nt.links.new(n.outputs["Fac"], rmp.inputs["Fac"]); nt.links.new(rmp.outputs["Color"], b.inputs["Alpha"])
    if hasattr(ink, "surface_render_method"): ink.surface_render_method = 'BLENDED'
    W, H = .42, .22
    rounded("st_frame", W, H, (0, 0, 0), ink, r=.03, thick=.002, frame=.014)
    rounded("st_frame2", W - .04, H - .04, (0, 0, 0), ink, r=.02, thick=.002, frame=.004)
    text("st_txt", "CONFERIDO", .050, (.045, .018, .001), ink, bold=True)
    text("st_sub", "ESTOQUE  ·  OK", .022, (.045, -.038, .001), ink, bold=True)
    box("st_ck1", (.012, .045, .002), (-.168, -.012, 0), ink, bevel=.003, rot=(0, 0, rad(40)))
    box("st_ck2", (.012, .095, .002), (-.133, .010, 0), ink, bevel=.003, rot=(0, 0, rad(-32)))
    return dict(size=(W, H))

def render_stamp():
    clear(); sc = scene(); build_stamp()
    camera((0, 0, 0), 89.9, 1.2, 50); sc.render.resolution_x, sc.render.resolution_y = BOX_RES; fit_camera(1.08)
    light_rig((0, 0, 0), .5, warm=.4, world=.4)
    return render_layers("stamp_conferido", [("", ["back", "front"])], res=BOX_RES)

# ---------------------------------------------------------------- render_all
def render_fixtures():
    render_rack(); render_drinks(); render_produce(); render_coldroom()

def render_all():
    render_backdrop(); render_truck(); render_fixtures(); render_boxes(); render_clipboard(); render_stamp()
