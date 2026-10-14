"""receiving_art_v3.py -- Checkout - Supermercado Simulator (Oct 2026)
Third take on the RECEIVING mini-game art. v2 rendered every fixture alone, each with its own camera, and Unity laid
them side by side at one scale: the perspectives did not match, nothing cast a shadow and the room was far too big
around tiny racks ("parece fake"). v3 builds ONE stockroom in real metres -- the dock with the truck backed in on the
left, the four fixtures against the back wall -- and renders every layer from the SAME camera:

  receiving_backdrop.jpg (+ .json)        2048 x 1024 the empty room (dock open to the yard); json "dock" = opening
  receiving_truck_back.png (+ .json)      the truck's cargo box seen through the dock door (crop of the stage)
  receiving_<fixture>_back/front.png      rack (SECOS), drinks (BEBIDAS), produce (HORTIFRUTI | PAES), coldroom
                                          (CAMARA FRIA); crops of the stage with their contact shadows (the floor and
                                          the wall are shadow catchers), front = what stands in front of the boxes
  box_<kind>.png + box_<kind>_marks.json  carton, crate (hortifruti), bread, pack (engradado de bebidas), water (fardo),
                                          milk (engradado de leite), frozen (caixa termica), tray (ovos); 512 x 512
Every crop json carries "stage": [x0, y0, x1, y1], its rect in the backdrop (normalised, origin bottom-left), so Unity
places it exactly where it was rendered. Slots/sign/display/cargo/dockRect are normalised to the crop as in v2.
The clipboard and the stamp keep the v2 renders.

    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\receiving\\receiving_art_v3.py", encoding="utf-8").read())
    build_stage(); render_stage("backdrop"); render_stage("truck"); render_stage("rack"); ...; render_box("crate"); ...
"""
import bpy, bmesh, math, os, json, random
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

_HERE = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\receiving"
exec(compile(open(os.path.join(_HERE, "receiving_art_v2.py"), encoding="utf-8").read(), "receiving_art_v2.py", "exec"), globals())
OUT = os.path.join(_HERE, "render_v3")
SCENE = "ReceivingArtV3"
STAGE = (2048, 1024)
SAMPLES = 128

# ---------------------------------------------------------------- layout (metres; back wall face at y = 0, floor z = 0)
CEIL = 3.10
DOCK = dict(x0=-0.875, x1=0.875, h=2.30)          # the dock in the middle: shelves on both sides
FIXX = dict(rack=-3.89, drinks=-2.55, produce=1.30, coldroom=3.18)     # left edge of each fixture
CAM = dict(x=0.58, y=-8.25, z=1.50, lens=26.8, centre_z=1.52, plane_y=-0.8)
GROUPS = ("room", "yard", "truck", "rack", "drinks", "produce", "coldroom")
INFO = {}

def strip_text():
    """The game is translated: no words are baked into the art (Unity writes every label)."""
    for o in list(bpy.context.scene.objects):
        if o.type == 'FONT': bpy.data.objects.remove(o, do_unlink=True)

def chevron(nm, x, y, z, size, m, rot_z=0., thick=.004, plane="floor", layer="back"):
    """Painted arrow head pointing +y (floor) or +z (wall, plane='wall')."""
    L = size * .62; w = size * .16
    for s_ in (-1, 1):
        if plane == "floor": box(f"{nm}{s_}", (L, w, thick), (x + s_ * L * .33, y, z), m, bevel=0, rot=(0, 0, rot_z + s_ * rad(-40)), layer=layer)
        else: box(f"{nm}{s_}", (L, thick, w), (x + s_ * L * .33, y, z), m, bevel=0, rot=(0, rot_z + s_ * rad(40), 0), layer=layer)

def snowflake(nm, x, y, z, r, m, thick=.002, layer="back"):
    for k in range(3):
        a = rad(k * 60)
        box(f"{nm}_a{k}", (.012 * r / .05, thick, r * 2), (x, y, z), m, bevel=0, rot=(0, a, 0), layer=layer)
        for d in (-1, 1):
            cx, cz = x + math.sin(a) * r * .62 * d, z + math.cos(a) * r * .62 * d
            for s_ in (-1, 1):
                box(f"{nm}_b{k}{s_}{d}", (.008 * r / .05, thick, r * .40), (cx + math.sin(a + s_ * rad(40)) * r * .14 * d, y, cz + math.cos(a + s_ * rad(40)) * r * .14 * d), m, bevel=0, rot=(0, a + s_ * rad(40), 0), layer=layer)

def tag(group, fn, *a, **k):
    before = set(bpy.context.scene.objects)
    r = fn(*a, **k)
    for o in bpy.context.scene.objects:
        if o not in before: o["group"] = group
    return r

def set_off(x, y, z=0.):
    global OFF; OFF = Vector((x, y, z))

def stage_camera():
    sc = bpy.context.scene
    cam = bpy.data.objects.get("RV3_Cam")
    if not cam or cam.name not in sc.objects:
        cam = bpy.data.objects.new("RV3_Cam", bpy.data.cameras.new("RV3_Cam")); sc.collection.objects.link(cam)
    cam.data.lens = CAM["lens"]; cam.data.sensor_width = 36; cam.data.sensor_fit = 'HORIZONTAL'; cam.data.clip_end = 100
    cam.location = (CAM["x"], CAM["y"], CAM["z"]); cam.rotation_euler = (rad(90), 0, 0)
    width_at_plane = (CAM["plane_y"] - CAM["y"]) * 36 / CAM["lens"]
    cam.data.shift_y = (CAM["centre_z"] - CAM["z"]) / width_at_plane
    cam["layer"] = "cam"; sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = STAGE
    return cam

def P(p):
    """World point -> normalised stage coords (bottom-left origin)."""
    sc = bpy.context.scene; v = world_to_camera_view(sc, sc.camera, Vector(p)); return [v.x, v.y]

def local_quad(x0, x1, y0, y1, z):
    o = OFF
    pts = dict(fl=(x0, y0), fr=(x1, y0), bl=(x0, y1), br=(x1, y1))
    q = {k: P((a + o.x, b + o.y, z + o.z)) for k, (a, b) in pts.items()}
    q["ppm"] = ppm_at((x0 + o.x, y0 + o.y, z + o.z)); q["ppmBack"] = ppm_at((x0 + o.x, y1 + o.y, z + o.z))
    return q

def rect_of(objs):
    sc = bpy.context.scene; xs, ys = [], []
    for o in objs:
        if o.type not in ('MESH', 'FONT', 'CURVE'): continue
        for c in o.bound_box:
            v = world_to_camera_view(sc, sc.camera, o.matrix_world @ Vector(c)); xs.append(v.x); ys.append(v.y)
    return [min(xs), min(ys), max(xs), max(ys)]

# ---------------------------------------------------------------- lights (shared by every stage render)
def stage_lights():
    sc = bpy.context.scene
    w = bpy.data.worlds.get("RV3_World") or bpy.data.worlds.new("RV3_World"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (.82, .86, .92, 1); w.node_tree.nodes["Background"].inputs[1].default_value = .12
    def area(n, loc, rot, energy, size, size_y=None, color=(1, .97, .93)):
        bpy.ops.object.light_add(type='AREA', location=loc); l = bpy.context.object; l.name = n
        l.data.energy = energy; l.data.color = color
        if size_y: l.data.shape = 'RECTANGLE'; l.data.size = size; l.data.size_y = size_y
        else: l.data.size = size
        l.rotation_euler = rot; l["layer"] = "light"; l["group"] = "light"
    # LED battens on the ceiling (pointing down), a big soft fill from the camera side, a warm bounce from the floor
    for k, x in enumerate((-3.1, -0.9, 1.9, 4.2)):
        area(f"Ceil{k}", (x, -1.35, CEIL - .08), (0, 0, 0), 170, 1.6, .25, (1, .97, .92))
    area("Fill", (0.4, -6.5, 2.6), (rad(80), 0, 0), 150, 5.0, 2.0, (.95, .97, 1))
    area("KeyL", (-2.5, -4.5, 2.9), (rad(62), 0, rad(-28)), 200, 1.6, None, (1, .93, .84))

# ---------------------------------------------------------------- room
def build_room():
    set_off(0, 0)
    epoxy = mat("r3_epoxy", (0.36, 0.40, 0.39, 1), rough=.28, bump=.05, scale=5, spec=.55)
    up = block_mat("r3_block_up", (0.93, 0.88, 0.76, 1)); lo = block_mat("r3_block_lo", (0.045, 0.30, 0.48, 1), mortar=(0.03, 0.18, 0.30, 1))
    side_up = block_mat("r3_side_up", (0.90, 0.85, 0.72, 1)); side_lo = block_mat("r3_side_lo", (0.04, 0.27, 0.44, 1), mortar=(0.03, 0.18, 0.30, 1))
    yellow = mat("r3_yellow", YELLOW, rough=.5, bump=.1, scale=30); black = mat("r3_black", (0.04, 0.04, 0.04, 1), rough=.6, bump=.1, scale=30)
    steel = mat("r3_steel", (0.62, 0.64, 0.65, 1), rough=.4, metal=.7); skirt = mat("r3_skirt", (0.12, 0.13, 0.14, 1), rough=.6)
    band_m = mat("r3_band", ORANGE, rough=.6, bump=0); ceil_m = mat("r3_ceil", (0.78, 0.78, 0.76, 1), rough=.9, bump=.1)
    joist = mat("r3_joist", (0.30, 0.32, 0.34, 1), rough=.6, metal=.3); led = mat("r3_led", (1, 1, .97, 1), emit=9, bump=0)
    rubber = mat("r3_rubber", (0.05, 0.05, 0.05, 1), rough=.85, bump=.2)
    x0, x1, dh = DOCK["x0"], DOCK["x1"], DOCK["h"]
    XL, XR = -4.40, 5.52; band = 1.20
    # floor, saw-cut joints, yellow aisle line, the receiving box painted in front of the dock
    box("r3_floor", (XR - XL + 1, 10, .05), ((XL + XR) / 2, -4.6, -.025), epoxy, bevel=0)
    for x in (-3.0, 0.0, 3.0): box(f"r3_joint{x:.0f}", (.01, 9.6, .004), (x, -4.6, .001), mat("r3_jointm", (0.24, 0.27, 0.27, 1), rough=.6, bump=0), bevel=0)
    box("r3_joint_y", (XR - XL, .01, .004), ((XL + XR) / 2, -2.8, .001), mat("r3_jointm", (0.24, 0.27, 0.27, 1), rough=.6, bump=0), bevel=0)
    for nm, xa, xb in (("L", XL + .2, x0 - .35), ("R", x1 + .35, XR - .2)): box("r3_aisle" + nm, (xb - xa, .09, .004), ((xa + xb) / 2, -1.30, .002), yellow, bevel=0)
    bx0, bx1, by0, by1 = x0 - .05, x1 + .05, -2.3, -.5
    for nm, sz, lc in (("f", (bx1 - bx0, .09, .004), ((bx0 + bx1) / 2, by0, .002)), ("l", (.09, by1 - by0, .004), (bx0, (by0 + by1) / 2, .002)), ("r", (.09, by1 - by0, .004), (bx1, (by0 + by1) / 2, .002))):
        box("r3_lane_" + nm, sz, lc, yellow, bevel=0)
    for k in range(9):   # hatched strip at the dock edge
        box(f"r3_hatch{k}", ((x1 - x0) / 9, .26, .004), (x0 + (k + .5) * (x1 - x0) / 9, -.48, .002), yellow if k % 2 == 0 else black, bevel=0)
    for k, yy in enumerate((-1.95, -1.50, -1.05)): chevron(f"r3_chev{k}", (x0 + x1) / 2, yy, .004, .70, yellow)
    # back wall (blue block band, cream above, orange rule, skirting) with the dock opening
    def wall(nm, xa, xb, za, zb, m, y=.15, d=.30):
        if xb - xa > .01 and zb - za > .01: box(nm, (xb - xa, d, zb - za), ((xa + xb) / 2, y, (za + zb) / 2), m, bevel=0)
    wall("r3_wL_lo", XL, x0, 0, band, lo); wall("r3_wL_up", XL, x0, band, CEIL, up)
    # the cold room is built into the wall: a hole as big as its front
    cx0, cx1, ch = FIXX["coldroom"] + .02, FIXX["coldroom"] + C3["W"] - .02, C3["H"] - .02
    wall("r3_wR_lo", x1, cx0, 0, band, lo); wall("r3_wR_up", x1, cx0, band, CEIL, up)
    wall("r3_wC_up", cx0, cx1, ch, CEIL, up)
    wall("r3_wE_lo", cx1, XR, 0, band, lo); wall("r3_wE_up", cx1, XR, band, CEIL, up)
    wall("r3_wT", x0, x1, dh, CEIL, up)
    for nm, xa, xb in (("L", XL, x0 - .12), ("R", x1 + .12, cx0), ("E", cx1, XR)):
        box("r3_skirt" + nm, (xb - xa, .02, .10), ((xa + xb) / 2, -.01, .05), skirt, bevel=0)
        box("r3_rule" + nm, (xb - xa, .015, .045), ((xa + xb) / 2, -.006, band + .02), band_m, bevel=0)
    # side walls (the room's corners frame the shot) and the ceiling with joists and LED battens
    for nm, x, m1, m2 in (("L", XL - .15, side_lo, side_up), ("R", XR + .15, side_lo, side_up)):
        box("r3_side_lo" + nm, (.3, 9.5, band), (x, -4.6, band / 2), m1, bevel=0); box("r3_side_up" + nm, (.3, 9.5, CEIL - band), (x, -4.6, band + (CEIL - band) / 2), m2, bevel=0)
        box("r3_side_rule" + nm, (.32, 9.5, .045), (x, -4.6, band + .02), band_m, bevel=0)
    box("r3_ceiling", (XR - XL + 1, 10, .1), ((XL + XR) / 2, -4.6, CEIL + .05), ceil_m, bevel=0)
    for k in range(5): box(f"r3_joist{k}", (XR - XL + 1, .10, .20), ((XL + XR) / 2, -.35 - k * 1.25, CEIL - .10), joist, bevel=.01)
    for k, x in enumerate((-3.1, -0.9, 1.9, 4.2)):
        box(f"r3_batten{k}", (1.62, .14, .05), (x, -1.35, CEIL - .03), mat("r3_batten_case", (0.86, 0.87, 0.87, 1), rough=.4, metal=.3), bevel=.01)
        box(f"r3_batten_led{k}", (1.54, .09, .01), (x, -1.35, CEIL - .058), led, bevel=0)
    cyl("r3_conduit", .018, XR - XL, ((XL + XR) / 2, -.05, CEIL - .22), steel, rot=(0, rad(90), 0), verts=12)
    # dock: steel angle frame painted with safety stripes, rubber bumpers, the rolled-up door (drum + guides), leveler
    for nm, x in (("L", x0 - .06), ("R", x1 + .06)):
        box("r3_jamb" + nm, (.12, .34, dh + .1), (x, .13, (dh + .1) / 2), steel, bevel=.012)
        bx = x + (-.22 if nm == "L" else .22)
        cyl("r3_bollard" + nm, .065, .95, (bx, -.42, .475), yellow, verts=24, bevel=.03)
        for z in (.55, .75): cyl(f"r3_bollard_band{nm}{z}", .066, .06, (bx, -.42, z), black, verts=24)
        box("r3_guide" + nm, (.07, .10, dh), (x + (.09 if nm == "L" else -.09), -.07, dh / 2), steel, bevel=.008)
        box("r3_bumper" + nm, (.24, .12, .34), (x + (.10 if nm == "L" else -.10), -.10, .22), rubber, bevel=.03, seg=4)
    box("r3_lintel", (x1 - x0 + .24, .34, .14), ((x0 + x1) / 2, .13, dh + .07), steel, bevel=.012)
    box("r3_drum", (x1 - x0 + .24, .32, .28), ((x0 + x1) / 2, -.14, dh + .26), mat("r3_drum_m", (0.50, 0.52, 0.53, 1), rough=.35, metal=.7), bevel=.04, seg=4)
    for k in range(6): box(f"r3_drum_rib{k}", (.025, .33, .29), (x0 + .05 + k * (x1 - x0 - .1) / 5, -.14, dh + .26), mat("r3_drum_rib", (0.55, 0.57, 0.57, 1), rough=.4, metal=.6), bevel=.008)
    box("r3_door_bar", (x1 - x0 + .1, .05, .06), ((x0 + x1) / 2, -.06, dh + .06), mat("r3_door_bar", (0.25, 0.27, 0.28, 1), rough=.4, metal=.6), bevel=.01)
    box("r3_leveler", (x1 - x0 - .12, .70, .03), ((x0 + x1) / 2, -.12, .006), mat("r3_lev", (0.46, 0.48, 0.48, 1), rough=.45, metal=.6, bump=.35, scale=55), bevel=.008)
    # outside: the dock seal around the door, yard ground lower than the dock, a wall and the late-afternoon sky
    for nm, sz, lc in (("T", (x1 - x0 + .6, .30, .28), ((x0 + x1) / 2, .45, dh + .02)), ("L", (.26, .30, dh + .3), (x0 - .02, .45, (dh + .3) / 2 - .1)), ("R", (.26, .30, dh + .3), (x1 + .02, .45, (dh + .3) / 2 - .1))):
        box("r3_seal" + nm, sz, lc, rubber, bevel=.06, seg=4)
    # the tops of the seal pads: yellow guide stripes, a lamp arm by the door
    box("r3_lamp_arm", (.04, .5, .04), (x1 + .35, -.25, 2.25), steel, bevel=.01)
    cyl("r3_lamp_head", .09, .12, (x1 + .35, -.50, 2.2), mat("r3_lamp_head", (0.15, 0.16, 0.17, 1), rough=.5), rot=(rad(-60), 0, 0), verts=20)
    # wall: the ESTOQUE board, a clock, the fire extinguisher between the dock and the rack, an outlet strip
    cx, cz = -1.12, 2.62
    cyl("r3_clock", .17, .045, (cx, -.02, cz), mat("r3_clock_m", (0.10, 0.11, 0.12, 1), rough=.4), rot=(rad(90), 0, 0), verts=40, bevel=.01)
    cyl("r3_clock_face", .15, .01, (cx, -.046, cz), mat("r3_face", (0.98, 0.98, 0.96, 1), rough=.6, bump=0), rot=(rad(90), 0, 0), verts=40)
    for k in range(12):
        a = rad(k * 30); box(f"r3_tick{k}", (.01, .004, .025), (cx + math.sin(a) * .13, -.053, cz + math.cos(a) * .13), mat("r3_ink", DARK, rough=.8, bump=0), bevel=0, rot=(0, -a, 0))
    box("r3_clock_h", (.014, .004, .08), (cx + .02, -.056, cz + .035), mat("r3_ink", DARK, rough=.8, bump=0), bevel=0, rot=(0, rad(-35), 0))
    box("r3_clock_m", (.01, .004, .12), (cx - .04, -.058, cz + .04), mat("r3_ink", DARK, rough=.8, bump=0), bevel=0, rot=(0, rad(48), 0))
    ex = 1.12
    rounded("r3_ext_sign", .20, .26, (ex, -.02, 1.95), mat("r3_red_sign", (0.85, 0.10, 0.08, 1), rough=.5, bump=0), r=.02, thick=.01, rot=(rad(90), 0, 0))
    box("r3_ext_bracket", (.09, .04, .26), (ex, -.02, 1.35), mat("r3_bracket", DARK, rough=.5), bevel=.008)
    cyl("r3_ext_body", .075, .46, (ex, -.11, 1.18), mat("r3_red", (0.82, 0.08, 0.06, 1), rough=.3, bump=.04), verts=24, bevel=.03)
    cyl("r3_ext_neck", .025, .07, (ex, -.11, 1.44), steel, verts=12); box("r3_ext_lever", (.025, .10, .02), (ex, -.14, 1.49), steel, bevel=.006)
    cyl("r3_ext_hose", .01, .28, (ex + .07, -.17, 1.26), mat("r3_hose", DARK, rough=.7), rot=(rad(10), rad(8), 0), verts=10)
    box("r3_ext_label", (.09, .005, .12), (ex, -.187, 1.16), mat("r3_label", WHITE, rough=.6, bump=0), bevel=.004)
    box("r3_outlet", (.16, .04, .10), (ex, -.02, .45), mat("r3_outlet", (0.92, 0.92, 0.9, 1), rough=.4), bevel=.01)

def build_yard():
    set_off(0, 0)
    x0, x1 = DOCK["x0"], DOCK["x1"]; c = (x0 + x1) / 2
    box("r3_yard_ground", (12, 14, .05), (c, 7.5, -1.22), mat("r3_asphalt", (0.25, 0.25, 0.26, 1), rough=.9, bump=.3, scale=30), bevel=0)
    for k in range(3): box(f"r3_yard_line{k}", (.12, 6, .01), (c - 2.5 + k * 2.5, 6, -1.19), mat("r3_yline", (0.9, 0.9, 0.85, 1), rough=.8), bevel=0)
    box("r3_yard_wall", (14, .2, 2.4), (c, 11, 0), mat("r3_ywall", (0.70, 0.58, 0.44, 1), rough=.9, bump=.2), bevel=0)
    box("r3_sky", (30, .1, 16), (c, 16, 6), mat("r3_skym", (1.0, 0.86, 0.66, 1), emit=2.6, bump=0), bevel=0)

# ---------------------------------------------------------------- truck backed into the dock (only its cargo box shows)
TRUCK3 = dict(W=1.62, L=3.4, H=1.98, y0=.62)
def _corrugated():
    """Ribbed aluminium lining of a box truck."""
    m = mat("t3_alu", (0.80, 0.82, 0.83, 1), rough=.35, metal=.75, bump=0)
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]; tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'; wv.wave_profile = 'SIN'; wv.inputs["Scale"].default_value = 9
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .6; bp.inputs["Distance"].default_value = .01
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def build_truck():
    W, L, H, y0 = TRUCK3["W"], TRUCK3["L"], TRUCK3["H"], TRUCK3["y0"]
    set_off((DOCK["x0"] + DOCK["x1"]) / 2, y0, 0)
    body = mat("t3_body", BLUE, rough=.4, bump=.06); ply = _corrugated()
    track = mat("t3_track", (0.66, 0.69, 0.70, 1), rough=.3, metal=.8, bump=0); hole = mat("t3_hole", (0.05, 0.05, 0.05, 1), rough=.9, bump=0)
    floor_m = mat("t3_floor", (0.55, 0.57, 0.58, 1), rough=.35, metal=.7, bump=.5, scale=90); roof = mat("t3_roof", (0.92, 0.94, 0.95, 1), rough=.5, emit=.6, bump=0)
    steel = mat("t3_steel", (0.70, 0.72, 0.72, 1), rough=.3, metal=.8); amber = mat("t3_amber", (1.0, 0.6, 0.1, 1), rough=.2, emit=1.2)
    t = .05
    box("t3_floor", (W, L, .10), (0, L / 2, -.05), floor_m, bevel=.01)
    box("t3_sill", (W, .10, .04), (0, .05, .0), steel, bevel=.01)
    for sx in (-1, 1):
        box(f"t3_wall{sx}", (t, L, H), (sx * (W / 2 + t / 2), L / 2, H / 2), body, bevel=.01)
        box(f"t3_ply{sx}", (.012, L - .05, H - .05), (sx * (W / 2 - .006), L / 2, H / 2), ply, bevel=0)
        for z in (.55, 1.25):
            box(f"t3_track{sx}{z:.1f}", (.012, L - .1, .08), (sx * (W / 2 - .016), L / 2, z), track, bevel=.004)
            for k in range(22): box(f"t3_th{sx}{z:.1f}{k}", (.004, .05, .025), (sx * (W / 2 - .024), .15 + k * (L - .3) / 21, z), hole, bevel=0)
    box("t3_front", (W, .05, H), (0, L - .025, H / 2), ply, bevel=0)
    box("t3_roof", (W + .1, L, .05), (0, L / 2, H + .025), roof, bevel=.01)
    for k in range(5): box(f"t3_bow{k}", (W, .05, .05), (0, .3 + k * (L - .5) / 4, H - .02), track, bevel=.008)
    # rear frame: corner posts, header with marker lamps, the door hinges folded open outside
    for sx in (-1, 1):
        box(f"t3_post{sx}", (.12, .12, H + .12), (sx * (W / 2 + .03), .03, (H + .12) / 2 - .06), body, bevel=.02)
        for z in (.35, 1.05, 1.75): box(f"t3_hinge{sx}{z:.1f}", (.05, .07, .12), (sx * (W / 2 + .1), -.02, z), steel, bevel=.01)
    box("t3_header", (W + .3, .14, .16), (0, .03, H + .06), body, bevel=.02)
    for k in range(3): box(f"t3_marker{k}", (.09, .03, .05), (-W / 2 + .25 + k * (W - .5) / 2, -.045, H + .06), amber, bevel=.012, seg=4)
    bpy.ops.object.light_add(type='AREA', location=Vector((0, L * .45, H - .1)) + OFF); l = bpy.context.object; l.name = "t3_light"
    l.data.energy = 70; l.data.size = 1.2; l.data.color = (1, .95, .86); l["layer"] = "light"
    # cargo floor quad: the boxes stand on it (2 columns x 3 rows, back rows first)
    INFO["truck_cargo"] = local_quad(-W / 2 + .14, W / 2 - .14, .14, L - .25, .0)

# ---------------------------------------------------------------- fixtures
def zone_sign(nm, x, z, w=.92, h=.24, y=-.02, mount="posts", layer="back"):
    """Blue-framed cream plate (Unity writes the zone name on the cream). mount: posts below it, or flat on a panel."""
    if mount == "posts":
        for px in (-w * .35, w * .35): box(f"{nm}_post{px:+.2f}", (.03, .03, .26), (x + px, y + .02, z - .16), mat("z3_post", BLUE_D, rough=.5), bevel=.006, layer=layer)
    elif mount == "chains":   # hung from the ceiling on two chains (z = centre of the plate, world ceiling at CEIL)
        top = CEIL - OFF.z; ln = top - (z + h / 2)
        for px in (-w * .38, w * .38):
            for k in range(int(ln / .035)):
                cyl(f"{nm}_ch{px:+.2f}_{k}", .006, .03, (x + px, y, z + h / 2 + .02 + k * .035), mat("z3_chain", (0.55, 0.57, 0.58, 1), rough=.35, metal=.9, bump=0), rot=(0, 0, rad(90 * (k % 2))), verts=6, layer=layer)
            cyl(f"{nm}_hook{px:+.2f}", .02, .02, (x + px, y, top - .01), mat("z3_chain", (0.55, 0.57, 0.58, 1), rough=.35, metal=.9, bump=0), verts=12, layer=layer)
    rounded(f"{nm}_bd", w, h, (x, y, z), mat("z3_bd", BLUE, rough=.45, bump=.04), r=.035, thick=.03, rot=(rad(90), 0, 0), layer=layer)
    return rounded(f"{nm}_in", w - .07, h - .07, (x, y - .02, z), mat("z3_in", CREAM, rough=.5, emit=.3, bump=0), r=.025, thick=.008, rot=(rad(90), 0, 0), layer=layer)

def fixture_slots(key):
    return [dict(level=s["level"], bay=s["bay"], index=s["index"], **local_quad(s["x0"], s["x1"], s["y0"], s["y1"], s["z"])) for s in SLOTS.get(key, [])]

# --- SECOS: one bay, four box levels + overstock on top
R3 = dict(BW=1.06, D=.64, H=2.42, post=.08, levels=(.10, .62, 1.14, 1.66), top=2.20)
def chalk_apple(nm, x, y, z, r, m):
    rounded(nm + "_o", r * 1.7, r * 1.55, (x, y, z - r * .05), m, r=r * .7, frame=.005, rot=(rad(90), 0, 0))
    box(nm + "_st", (.006, .003, r * .5), (x + r * .05, y, z + r * .78), m, bevel=0, rot=(0, rad(15), 0))
    rounded(nm + "_lf", r * .6, r * .28, (x + r * .38, y, z + r * .82), m, r=r * .13, frame=.005, rot=(rad(90), rad(-25), 0))
def chalk_carrot(nm, x, y, z, r, m):
    for s_ in (-1, 1): box(f"{nm}_s{s_}", (.006, .003, r * 1.9), (x + s_ * r * .22, y, z - r * .1), m, bevel=0, rot=(0, rad(s_ * 12), 0))
    for k in range(3): box(f"{nm}_l{k}", (.005, .003, r * .55), (x + (k - 1) * r * .16, y, z + r * .95), m, bevel=0, rot=(0, rad((k - 1) * 25), 0))
    for k in range(3): box(f"{nm}_r{k}", (r * .3, .003, .005), (x - r * .02, y, z - r * (.4 - k * .35)), m, bevel=0)
def chalk_bread(nm, x, y, z, r, m):
    rounded(nm + "_o", r * 2.4, r * .95, (x, y, z), m, r=r * .45, frame=.005, rot=(rad(90), 0, 0))
    for k in range(3): box(f"{nm}_c{k}", (.006, .003, r * .55), (x + (k - 1) * r * .62, y, z + r * .05), m, bevel=0, rot=(0, rad(35), 0))

def build_rack3(key="rack"):
    BW, D, H, post = R3["BW"], R3["D"], R3["H"], R3["post"]; W = BW + 2 * post
    set_off(FIXX[key] + W / 2, -D - .05); SLOTS.pop(key, None)
    rack_frame(key, BW, D, H, R3["levels"] + (R3["top"],), post=post, deck="wood", bays=1)
    sw = (BW - .06) / 2
    for lv, z in enumerate(R3["levels"]):
        for k in range(2):
            x0 = -(BW - .06) / 2 + k * sw
            slot(key, lv, 0, k, x0 + .02, x0 + sw - .02, .06, D - .06, z + .025)
    z = R3["top"] + .025
    flour = mat("dc_flour", (0.96, 0.94, 0.88, 1), rough=.85, bump=.3, scale=50); sugar = mat("dc_sugar", (0.95, 0.62, 0.20, 1), rough=.7, bump=.25, scale=50)
    sack("dc_sack0", (-.26, D * .5, z), flour, w=.40, d=.30, h=.20, rot_z=rad(5)); sack("dc_sack1", (.12, D * .5, z), sugar, w=.36, d=.30, h=.18, rot_z=rad(-4))
    carton_deco("dc_ct0", (.36, D * .5, z), w=.30, d=.30, h=.22, rot_z=rad(4))
    sg = zone_sign(key + "_sign", 0, 2.70, y=-.10, mount="chains")
    INFO[key] = dict(sign=sg, widthM=W, slots=fixture_slots(key))

# --- BEBIDAS: half pallet on the floor + three wire decks
D3 = dict(BW=1.06, D=.70, H=2.42, post=.08, levels=(.70, 1.26, 1.82))
def build_drinks3(key="drinks"):
    BW, D, H, post = D3["BW"], D3["D"], D3["H"], D3["post"]; W = BW + 2 * post
    set_off(FIXX[key] + W / 2, -D - .05); SLOTS.pop(key, None)
    rack_frame(key, BW, D, H, D3["levels"], post=post, deck="wire", bays=1)
    pallet(f"{key}_pal", (0, D / 2, 0), w=BW - .06, d=D - .08)
    sw = (BW - .10) / 2
    for k in range(2):
        x0 = -(BW - .10) / 2 + k * sw
        slot(key, 0, 0, k, x0 + .02, x0 + sw - .02, .08, D - .08, .15)
    sw = (BW - .06) / 2
    for lv, z in enumerate(D3["levels"]):
        for k in range(2):
            x0 = -(BW - .06) / 2 + k * sw
            slot(key, lv + 1, 0, k, x0 + .02, x0 + sw - .02, .06, D - .06, z + .02)
    sg = zone_sign(key + "_sign", 0, 2.70, y=-.10, mount="chains")
    INFO[key] = dict(sign=sg, widthM=W, slots=fixture_slots(key))

# --- HORTIFRUTI | PAES: a stepped pine stand (3 tiers x 2) and a stainless bakery trolley (3 trays)
PR3 = dict(SW=1.06, TW=.60, gap=.08, D=1.12, H=1.80)
def build_produce3(key="produce"):
    SW_, TW, gap, D, H = PR3["SW"], PR3["TW"], PR3["gap"], PR3["D"], PR3["H"]; W = SW_ + gap + TW
    set_off(FIXX[key] + W / 2, -D - .05); SLOTS.pop(key, None)
    xl = -W / 2 + SW_ / 2; xr = W / 2 - TW / 2
    pine = wood_mat("pr_pine", (0.86, 0.64, 0.36, 1), (0.64, 0.44, 0.22, 1), grain=(1.0, 18.0, 18.0)); pine_d = wood_mat("pr_pine_d", (0.55, 0.36, 0.18, 1), (0.40, 0.25, 0.12, 1), grain=(18.0, 18.0, 1.0))
    chalk = mat("pr_chalk", (0.12, 0.14, 0.13, 1), rough=.9, bump=.2, scale=30); chalk_ink = mat("pr_chalk_ink", (0.95, 0.95, 0.92, 1), rough=.9, bump=0)
    tiers = ((.30, .04, .36), (.68, .40, .36), (1.06, .76, .32)); tilt = 0.     # level shelves: the crates stand straight
    for sx in (-1, 1):
        for k, (z, y, d) in enumerate(tiers):
            zt = z + d * math.sin(tilt)
            box(f"pr_sidep{sx}{k}", (.04, d + .04, zt + .02), (xl + sx * (SW_ / 2 - .02), y + d / 2, (zt + .02) / 2), pine_d, bevel=.006, layer="front" if k == 0 else "back")
        box(f"pr_sideb{sx}", (.04, .16, H), (xl + sx * (SW_ / 2 - .02), D - .08, H / 2), pine_d, bevel=.006)
    box("pr_top", (SW_, .05, .05), (xl, D - .03, H - .02), pine_d, bevel=.006)
    box("pr_backp", (SW_ - .08, .03, H - .4), (xl, D - .015, .4 + (H - .4) / 2), pine, bevel=.004)
    for k, (z, y, d) in enumerate(tiers):
        zc = z + d * math.sin(tilt) / 2; yc = y + d * math.cos(tilt) / 2
        for j in range(4): box(f"pr_tier{k}_{j}", (SW_ - .08, d / 4 - .008, .022), (xl, yc + (j - 1.5) * d / 4 * math.cos(tilt), zc + (j - 1.5) * d / 4 * math.sin(tilt)), pine, bevel=.004, rot=(tilt, 0, 0))
        # a low front lip; only the bottom tier's is drawn over the boxes (an upper lip is behind the crates below it)
        box(f"pr_lip{k}", (SW_ - .06, .025, .045), (xl, y - .01, z + .012), pine_d, bevel=.005, layer="front" if k == 0 else "back")
        zb = 0 if k == 0 else tiers[k - 1][0] + tiers[k - 1][2] * math.sin(tilt)      # the riser stands on the back of the tier below
        box(f"pr_under{k}", (SW_ - .08, .025, z - zb), (xl, y + .01, (z + zb) / 2), pine_d, bevel=.004, layer="front" if k == 0 else "back")
        sw = (SW_ - .12) / 2
        for i in range(2):
            x0 = xl - (SW_ - .12) / 2 + i * sw
            slot(key, k, 0, i, x0 + .02, x0 + sw - .02, y + .03, y + d * math.cos(tilt) * .85, z + d * math.sin(tilt) * .3 + .022)
    rounded("pr_board", .62, .20, (xl, D - .05, H + .14), chalk, r=.02, thick=.02, rot=(rad(90), 0, 0))
    rounded("pr_board_fr", .62, .20, (xl, D - .06, H + .14), pine_d, r=.02, thick=.02, rot=(rad(90), 0, 0), frame=.025)
    chalk_apple("pr_apple", xl - .09, D - .068, H + .14, .055, chalk_ink); chalk_carrot("pr_carrot", xl + .10, D - .068, H + .14, .06, chalk_ink)
    for px in (-.24, .24): box(f"pr_board_post{px:+.2f}", (.025, .025, .12), (xl + px, D - .05, H + .03), pine_d, bevel=.004)
    # bakery trolley: stainless uprights on casters, tray rails, three trays with slots and a top tray of bread
    inox = mat("pr_inox", (0.80, 0.82, 0.82, 1), rough=.22, metal=.9, bump=0); inox_d = mat("pr_inox_d", (0.60, 0.62, 0.62, 1), rough=.3, metal=.85, bump=0)
    alu = mat("dc_alu", (0.72, 0.74, 0.74, 1), rough=.3, metal=.8, bump=.06)
    tw, td, th = TW - .04, .66, 1.66; ty = D / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(f"pr_tpost{sx}{sy}", .018, th, (xr + sx * tw / 2, ty + sy * td / 2, th / 2 + .08), inox, verts=14, layer="front" if sy < 0 else "back")
            cyl(f"pr_caster{sx}{sy}", .04, .03, (xr + sx * tw / 2, ty + sy * td / 2, .04), mat("pr_caster", (0.12, 0.12, 0.13, 1), rough=.5), rot=(0, rad(90), 0), verts=16, layer="front" if sy < 0 else "back")
        box(f"pr_tside{sx}", (.025, td, .025), (xr + sx * tw / 2, ty, th + .08), inox, bevel=.006)
    for sy in (-1, 1): box(f"pr_ttop{sy}", (tw, .025, .025), (xr, ty + sy * td / 2, th + .08), inox, bevel=.006, layer="front" if sy < 0 else "back")
    box("pr_tbase", (tw + .02, td, .03), (xr, ty, .10), inox_d, bevel=.008)
    for k in range(11):
        zz = .22 + k * .13
        for sx in (-1, 1): box(f"pr_rail{sx}{k}", (.02, td - .05, .01), (xr + sx * (tw / 2 - .016), ty, zz), inox_d, bevel=.003)
    for k, zz in enumerate((.25, .77, 1.29)):
        box(f"pr_tray{k}", (tw - .05, td - .06, .010), (xr, ty, zz), alu, bevel=.003)
        for sy in (-1, 1): box(f"pr_tray{k}_ry{sy}", (tw - .05, .010, .025), (xr, ty + sy * (td / 2 - .035), zz + .01), alu, bevel=.003, layer="front" if sy < 0 else "back")
        slot(key, k, 1, 0, xr - tw / 2 + .05, xr + tw / 2 - .05, ty - td / 2 + .06, ty + td / 2 - .08, zz + .01)
    zz = 1.62; box("pr_tray3", (tw - .05, td - .06, .010), (xr, ty, zz), alu, bevel=.003)
    rnd = random.Random(8)
    for k in range(8):
        i, j = k % 2, k // 2
        french_roll(f"pr_roll{k}", (xr - .12 + i * .24 + rnd.uniform(-.02, .02), ty - .22 + j * .145, zz + .01), rnd.uniform(-12, 12), seed=k)
    rounded("pr_board2", .40, .17, (xr, D - .05, H + .12), chalk, r=.02, thick=.02, rot=(rad(90), 0, 0))
    rounded("pr_board2_fr", .40, .17, (xr, D - .06, H + .12), pine_d, r=.02, thick=.02, rot=(rad(90), 0, 0), frame=.025)
    chalk_bread("pr_breadic", xr, D - .068, H + .12, .07, chalk_ink)
    sg = zone_sign(key + "_sign", 0, 2.70, w=1.25, y=-.10, mount="chains")
    INFO[key] = dict(sign=sg, widthM=W, slots=fixture_slots(key))

# --- CAMARA FRIA: walk-in cooler; open door swung out on the right, PVC strip curtain, 4 wire shelves x 2 inside
C3 = dict(W=1.90, D=1.55, H=2.42, ow=1.04, oh=2.04, levels=(.10, .56, 1.02, 1.48))
def build_coldroom3(key="coldroom"):
    W, D, H, ow, oh = C3["W"], C3["D"], C3["H"], C3["ow"], C3["oh"]; t = .10
    set_off(FIXX[key] + W / 2, -.12); SLOTS.pop(key, None)     # built into the wall: only the front stands out
    ox = -W / 2 + .16 + ow / 2; xl_, xr_ = ox - ow / 2, ox + ow / 2
    panel = mat("cr_panel", (0.95, 0.96, 0.95, 1), rough=.35, bump=.04, scale=20); trim = mat("cr_trim", (0.82, 0.84, 0.85, 1), rough=.2, metal=.95, bump=0)
    inner = mat("cr_inner", (0.62, 0.74, 0.82, 1), rough=.5, bump=.05); shelf = mat("cr_shelf", (0.82, 0.84, 0.84, 1), rough=.25, metal=.9, bump=0)
    seam = mat("cr_seam", (0.78, 0.80, 0.80, 1), rough=.5, bump=0); kick = mat("cr_kick", (0.62, 0.64, 0.65, 1), rough=.3, metal=.9, bump=.05, scale=80)
    box("cr_side_L", (t, D, H), (-W / 2 + t / 2, D / 2, H / 2), panel, bevel=.025, seg=4)
    box("cr_side_R", (t, D, H), (W / 2 - t / 2, D / 2, H / 2), panel, bevel=.025, seg=4)
    box("cr_roof", (W, D, t), (0, D / 2, H - t / 2), panel, bevel=.025, seg=4)
    box("cr_back", (W - 2 * t, .05, H - t), (0, D - .025, (H - t) / 2), inner, bevel=.01)
    box("cr_inL", (.02, D - .1, H - t), (-W / 2 + t + .01, D / 2, (H - t) / 2), inner, bevel=0)
    box("cr_ceil", (W - 2 * t, D - .1, .02), (0, D / 2, H - t - .01), inner, bevel=0)
    box("cr_floor", (W, D, .05), (0, D / 2, .025), mat("cr_floorm", (0.55, 0.58, 0.60, 1), rough=.35, metal=.4, bump=.4, scale=60), bevel=.01)
    box("cr_lamp", (.9, .07, .02), (ox, D * .45, H - t - .025), mat("cr_lampm", (.85, .96, 1, 1), emit=5, bump=0), bevel=0)
    bpy.ops.object.light_add(type='AREA', location=Vector((ox, D * .45, H - t - .12)) + OFF); l = bpy.context.object; l.name = "cr_light"
    l.data.energy = 45; l.data.size = 1.0; l.data.color = (.62, .84, 1.0); l["layer"] = "light"
    # front wall around the opening (front layer), seams, trims, kick plate
    box("cr_front_L", (xl_ + W / 2, t, H), ((-W / 2 + xl_) / 2, t / 2, H / 2), panel, bevel=.025, seg=4, layer="front")
    box("cr_front_R", (W / 2 - xr_, t, H), ((xr_ + W / 2) / 2, t / 2, H / 2), panel, bevel=.025, seg=4, layer="front")
    box("cr_front_T", (ow + .02, t, H - oh), (ox, t / 2, oh + (H - oh) / 2), panel, bevel=.025, seg=4, layer="front")
    for xx in (xr_ + .40,): box(f"cr_seam{xx:.1f}", (.006, .004, H - .05), (xx, -.003, H / 2), seam, bevel=0, layer="front")
    for nm, sz, lc in (("L", (.06, .06, oh + .05), (xl_ - .03, -.02, oh / 2)), ("R", (.06, .06, oh + .05), (xr_ + .03, -.02, oh / 2)), ("T", (ow + .12, .06, .06), (ox, -.02, oh + .03))):
        box("cr_trim_" + nm, sz, lc, trim, bevel=.012, layer="front")
    box("cr_kick", (W, .02, .26), (0, -.012, .13), kick, bevel=.006, layer="front")
    box("cr_sill", (ow, .10, .02), (ox, .02, .055), trim, bevel=.005, layer="front")
    # PVC strip curtain hanging from a rail across the opening (front layer, see-through)
    pvc = mat("cr_pvc", (0.75, 0.88, 0.95, 1), rough=.08, alpha=.08, bump=0, spec=.6)
    box("cr_strip_rail", (ow + .06, .04, .05), (ox, -.045, oh - .02), trim, bevel=.008, layer="front")
    ns = 6
    for k in range(ns):
        sx = ox - ow / 2 + (k + .5) * ow / ns
        box(f"cr_strip{k}", (ow / ns + .03, .004, oh - .10), (sx, -.05 - (k % 2) * .006, (oh - .10) / 2 + .05), pvc, bevel=.002, layer="front")
        box(f"cr_strip_edge{k}", (.004, .006, oh - .10), (sx + ow / ns / 2 + .012, -.052, (oh - .10) / 2 + .05), mat("cr_pvc_edge", (0.70, 0.85, 0.92, 1), rough=.1, alpha=.35, bump=0), bevel=0, layer="front")
    # the door: insulated leaf swung open ~95 degrees on its right hinges (front layer); the camera sees its outer face
    dw, dh_, dt = ow + .06, oh + .04, .09
    hx, hy = xr_ + .05, -.02
    door = box("cr_door", (dw, dt, dh_), (hx + dw / 2, hy, dh_ / 2 + .02), panel, bevel=.025, seg=4, layer="front")
    inn = box("cr_door_in", (dw - .16, .01, dh_ - .24), (hx + dw / 2, hy - dt / 2 - .006, dh_ / 2 + .04), mat("cr_door_inm", (0.88, 0.91, 0.93, 1), rough=.45, bump=.04), bevel=.008, layer="front")
    kp = box("cr_door_kick", (dw - .02, .008, .24), (hx + dw / 2, hy - dt / 2 - .005, .16), kick, bevel=.004, layer="front")
    pull = box("cr_pull", (.04, .05, .50), (hx + dw - .10, hy - dt / 2 - .035, dh_ / 2 + .02), trim, bevel=.012, seg=4, layer="front")
    for o in (door, inn, kp, pull): pivot_rot(o, (hx, hy, 0), rad(-95))
    for z in (.3, dh_ - .3):
        cyl(f"cr_hinge{z:.1f}", .022, .14, (hx, hy - .02, z), trim, verts=16, layer="front")
    # thermometer over the opening, the zone sign on the panel
    box("cr_disp_box", (.24, .04, .13), (-W / 2 + .2, -.03, oh + .18), mat("cr_disp_case", (0.85, 0.86, 0.86, 1), rough=.3, metal=.5, bump=0), bevel=.01, layer="front")
    dsp = box("cr_display", (.18, .01, .08), (-W / 2 + .2, -.052, oh + .18), mat("cr_disp", (0.03, 0.04, 0.05, 1), rough=.3, bump=0), bevel=.004, layer="front")
    led = mat("cr_led", (0.35, 0.90, 1.0, 1), emit=6, bump=0)
    for k, (dx, w_, h_) in enumerate(((-.05, .03, .008), (-.005, .034, .05), (.04, .034, .05))):
        box(f"cr_seg{k}", (w_, .004, h_), (-W / 2 + .2 + dx, -.058, oh + .18), led, bevel=0, layer="front")
    sg = zone_sign(key + "_sign", ox + .18, oh + .19, w=.80, h=.22, y=-.03, mount="flat", layer="front")
    # inside: chrome wire shelving, 4 levels x 2 places; frost; the cold blue light
    iw = ow - .02; sd = .72; yc = .52      # shelves close behind the opening: the jambs hide little of them
    for lv, z in enumerate(C3["levels"]):
        grid_wire(f"cr_deck{lv}", iw, sd, (ox, yc, z), shelf, nx=20, ny=7, thick=.006)
        for yy in (yc - sd / 2, yc + sd / 2): box(f"cr_shelf_edge{lv}{yy:.1f}", (iw, .025, .03), (ox, yy, z - .01), shelf, bevel=.006)
        sw = (iw - .16) / 2          # inset and nudged right: seen from the left, the left jamb hides the left edge
        for k in range(2):
            x0 = ox - iw / 2 + .12 + k * sw
            slot(key, lv, 0, k, x0 + .02, x0 + sw - .02, yc - sd / 2 + .04, yc + sd / 2 - .04, z + .01)
    for sxx in (-1, 1):
        for yy in (yc - sd / 2 + .015, yc + sd / 2 - .015):
            cyl(f"cr_leg{sxx}{yy:.1f}", .014, 1.95, (ox + sxx * (iw / 2 - .015), yy, .975), shelf, verts=12)
    frost = mat("cr_frost", (0.92, 0.97, 1.0, 1), rough=.9, bump=.4, scale=90); rnd = random.Random(7)
    for k in range(12): sphere(f"cr_frost{k}", rnd.uniform(.04, .09), (rnd.uniform(-W / 2 + t + .08, W / 2 - t - .08), D - .05, H - t - rnd.uniform(.02, .2)), frost, scale=(1.4, .3, .7))
    INFO[key] = dict(sign=sg, display=dsp, widthM=W, slots=fixture_slots(key))

# ---------------------------------------------------------------- produce and bread models (shared by boxes + decor)
def _uvsphere(name, r, loc, segs=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=Vector(loc) + OFF, segments=segs, ring_count=rings); return bpy.context.object

def _deform(o, f):
    me = o.data
    for v in me.vertices: v.co = f(v.co.copy())
    me.update()

def _shade(name, base, base2=None, rough=.4, spec=.5, bump=.05, bump_scale=200, sss=0.0, wave=None):
    """Organic skin: base colour mottled toward base2 (noise), optional wave streaks, fine bump."""
    key = "org_" + name
    if key in _M and _M[key].name in bpy.data.materials: return _M[key]
    m = bpy.data.materials.new("RV3_" + key); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = spec
    if sss and "Subsurface Weight" in b.inputs: b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (.4, .1, .05)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 18; n.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    rmp = nt.nodes.new("ShaderNodeValToRGB"); rmp.color_ramp.elements[0].color = base; rmp.color_ramp.elements[1].color = base2 or base
    rmp.color_ramp.elements[0].position = .42; rmp.color_ramp.elements[1].position = .68
    src = n.outputs["Fac"]
    if wave:
        wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'; wv.inputs["Scale"].default_value = wave; wv.inputs["Distortion"].default_value = 6
        nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = 'MULTIPLY'; nt.links.new(n.outputs["Fac"], mx.inputs[0]); nt.links.new(wv.outputs["Fac"], mx.inputs[1])
        ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'ADD'; nt.links.new(mx.outputs[0], ad.inputs[0]); ad.inputs[1].default_value = .1
        src = ad.outputs[0]
    nt.links.new(src, rmp.inputs["Fac"]); nt.links.new(rmp.outputs["Color"], b.inputs["Base Color"])
    if bump:
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = bump_scale; n2.inputs["Detail"].default_value = 3
        nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = .002
        nt.links.new(n2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    _M[key] = m; return m

def _leaf_mat(): return _shade("leaf", (0.10, 0.36, 0.06, 1), (0.22, 0.50, 0.10, 1), rough=.5, spec=.3, bump=.1)
def _stem_mat(): return _shade("stem", (0.30, 0.20, 0.08, 1), (0.42, 0.30, 0.12, 1), rough=.7, spec=.2, bump=.1)

def tomato(nm, loc, r=.038, rot=0., seed=0, layer="back"):
    o = _uvsphere(nm, r, loc)
    def f(c):
        rr = math.hypot(c.x, c.y); phi = math.atan2(c.y, c.x) + rot
        k = 1 + .045 * math.cos(5 * phi) * (rr / r)
        c.x *= k; c.y *= k; c.z *= .80
        c.z -= .18 * r * math.exp(-(rr / r) ** 2 * 7) * (1 if c.z > 0 else 0)
        return c
    _deform(o, f); _finish(o, nm, _shade("tomato", (0.72, 0.05, 0.02, 1), (0.86, 0.16, 0.04, 1), rough=.22, spec=.7, bump=.03, sss=.08), layer)
    top = Vector(loc) + Vector((0, 0, r * .66))
    for k in range(5):
        a = rot + k * 2 * math.pi / 5
        lf = sphere(f"{nm}_sepal{k}", r * .30, (top.x + math.cos(a) * r * .22, top.y + math.sin(a) * r * .22, top.z), _leaf_mat(), layer=layer, scale=(1.6, .38, .18), rot=(0, rad(-10), a))
    cyl(f"{nm}_stem", r * .07, r * .28, (top.x, top.y, top.z + r * .12), _leaf_mat(), verts=8, layer=layer)

def orange_fruit(nm, loc, r=.040, seed=0, layer="back"):
    o = _uvsphere(nm, r, loc)
    _deform(o, lambda c: Vector((c.x, c.y, c.z * .94)))
    _finish(o, nm, _shade("orange", (0.95, 0.36, 0.02, 1), (1.0, 0.50, 0.06, 1), rough=.45, spec=.5, bump=.35, bump_scale=900), layer)
    cyl(f"{nm}_navel", r * .10, r * .02, (loc[0], loc[1], loc[2] + r * .93), _stem_mat(), verts=10, layer=layer)

def apple(nm, loc, r=.039, rot=0., layer="back"):
    o = _uvsphere(nm, r, loc)
    def f(c):
        rr = math.hypot(c.x, c.y) / r
        c.z *= .90
        if c.z > 0: c.z -= .26 * r * math.exp(-rr * rr * 6)
        else: c.z += .14 * r * math.exp(-rr * rr * 6); c.x *= 1 - .08 * (-c.z / r); c.y *= 1 - .08 * (-c.z / r)
        return c
    _deform(o, f); _finish(o, nm, _shade("apple", (0.62, 0.04, 0.05, 1), (0.92, 0.55, 0.12, 1), rough=.30, spec=.6, bump=.02, wave=14), layer)
    cyl(f"{nm}_stem", r * .045, r * .40, (loc[0] + r * .03, loc[1], loc[2] + r * .78), _stem_mat(), rot=(0, rad(12), rot), verts=8, layer=layer)

def banana_hand(nm, loc, n=4, rot=0., layer="back"):
    """A hand of bananas: curved tapered fingers (curve + bevel), dark tips, joined at a crown."""
    yel = _shade("banana", (0.95, 0.75, 0.10, 1), (0.85, 0.70, 0.12, 1), rough=.45, spec=.4, bump=.05)
    R = Matrix.Rotation(rot, 4, 'Z'); L = Vector(loc) + OFF
    for k in range(n):
        cu = bpy.data.curves.new(f"{nm}_c{k}", 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = .017; cu.bevel_resolution = 3; cu.use_fill_caps = True
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(2)
        off = (k - (n - 1) / 2) * .036
        pts = [(-.09, off * .7, .0), (0, off, .035), (.09, off * 1.15, .01)]
        for i, p in enumerate(pts):
            bp = sp.bezier_points[i]; bp.co = Vector(p); bp.handle_left_type = bp.handle_right_type = 'AUTO'; bp.radius = (.55, 1.0, .5)[i]
        o = bpy.data.objects.new(f"{nm}_f{k}", cu); bpy.context.scene.collection.objects.link(o)
        o.matrix_world = Matrix.Translation(L) @ R; o.data.materials.append(yel); o["layer"] = layer
        for i, s in ((0, -1), (2, 1)):
            p = (R @ Vector(pts[i])) + L - OFF
            sphere(f"{nm}_tip{k}{i}", .008, (p.x, p.y, p.z), _stem_mat(), layer=layer, scale=(1.4, 1, 1))
    p = (R @ Vector((-.10, 0, 0))) + L - OFF
    box(f"{nm}_crown", (.03, .10, .025), (p.x, p.y, p.z), _shade("banana_crown", (0.45, 0.42, 0.12, 1), (0.30, 0.25, 0.08, 1), rough=.7), bevel=.008, layer=layer, rot=(0, 0, rot))

def _bread_mat():
    key = "org_bread_vc"
    if key in _M and _M[key].name in bpy.data.materials: return _M[key]
    m = bpy.data.materials.new("RV3_" + key); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = .62
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = .3
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "Col"
    tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 60; n.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs["Factor"].default_value = .35
    nt.links.new(at.outputs["Color"], mx.inputs[6]); nt.links.new(n.outputs["Color"], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 320; n2.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .25; bp.inputs["Distance"].default_value = .002
    nt.links.new(n2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    _M[key] = m; return m

def french_roll(nm, loc, rot_deg=0., seed=0, layer="back", L=.13, Wd=.075, Hh=.058):
    """Pao frances: an oval roll with tapered ends, a flat-ish base, the long split ('pestana') along the top where the
    crumb shows (light) and one lip rises; crust golden, darker on top (vertex colours)."""
    rnd = random.Random(seed)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=Vector(loc) + OFF, segments=40, ring_count=20); o = bpy.context.object
    me = o.data; hl, hw = L / 2, Wd / 2; off = rnd.uniform(-.15, .15) * hw
    cols = []
    for v in me.vertices:
        x, y, z = v.co.x, v.co.y, v.co.z
        taper = 1 - .30 * x * x
        X = x * hl; Y = y * hw * taper; Z = (z * Hh * .78 if z > 0 else z * Hh * .22) * (1 - .25 * x * x)
        g = math.exp(-((Y - off) / (hw * .24)) ** 2) * max(0, 1 - (x * 1.15) ** 2) * (1 if z > .2 else 0)
        Z -= g * Hh * .26
        if z > .2 and Y < off: Z += Hh * .11 * max(0, 1 - (x * 1.1) ** 2) * math.exp(-((Y - off + hw * .25) / (hw * .3)) ** 2)
        v.co = Vector((X, Y, Z + Hh * .22))
        top = max(0, z) ** 1.5
        crust = (0.80 - .22 * top, 0.52 - .20 * top, 0.20 - .10 * top)
        crumb = (0.97, 0.90, 0.70)
        cols.append(tuple(crust[i] * (1 - g) + crumb[i] * g for i in range(3)) + (1,))
    ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
    for i, c in enumerate(cols): ca.data[i].color = c
    me.update(); o.rotation_euler = (0, 0, rad(rot_deg))
    return _finish(o, nm, _bread_mat(), layer)

def egg(nm, loc, r=.022, m=None, layer="back"):
    o = _uvsphere(nm, r, loc, 24, 12)
    _deform(o, lambda c: Vector((c.x * (1 - .12 * c.z / r), c.y * (1 - .12 * c.z / r), c.z * 1.30)))
    return _finish(o, nm, m, layer)

def lathe(nm, prof, loc, m, segs=24, layer="back"):
    """Solid of revolution from (radius, z) pairs (bottom to top)."""
    me = bpy.data.meshes.new(nm); bm = bmesh.new(); rings = []
    for (r, z) in prof:
        r = max(r, .0006)
        ring = [bm.verts.new((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z)) for k in range(segs)]; rings.append(ring)
    for a, b_ in zip(rings, rings[1:]):
        for k in range(segs): bm.faces.new((a[k], a[(k + 1) % segs], b_[(k + 1) % segs], b_[k]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nm, me); bpy.context.scene.collection.objects.link(o); o.location = Vector(loc) + OFF
    return _finish(o, nm, m, layer)

# ---------------------------------------------------------------- the stage: build once, render each layer
def build_stage():
    clear(); sc = scene(); sc.cycles.samples = SAMPLES
    stage_camera(); stage_lights()
    sc.view_settings.exposure = -.35
    tag("room", build_room); tag("yard", build_yard); tag("truck", build_truck)
    tag("rack", build_rack3); tag("drinks", build_drinks3); tag("produce", build_produce3); tag("coldroom", build_coldroom3)
    set_off(0, 0); strip_text()
    return {g: sum(1 for o in sc.objects if o.get("group") == g) for g in GROUPS}

def _vis(group, layer):
    for o in bpy.context.scene.objects:
        if o.type == 'CAMERA': continue
        g = o.get("group", "room"); lay = o.get("layer", "back")
        o.is_shadow_catcher = False; o.visible_camera = True; o.hide_render = False
        if o.type == 'LIGHT':
            # lights inside the truck / cold room only light their own render (and the backdrop never sees them)
            o.hide_render = g not in ("light", group); continue
        if group == "backdrop": o.hide_render = g not in ("room", "yard"); continue
        # back layers catch the shadows of the whole fixture on the floor and the wall; front layers carry none
        # (the wall seen through the invisible back parts would catch them as a dark ghost)
        if g == "room":
            if layer == "front": o.hide_render = True
            else: o.is_shadow_catcher = True
        elif g == group: o.visible_camera = lay == layer
        else: o.hide_render = True

def _crop(group, mx=.010, my=(.025, .012)):
    objs = [o for o in bpy.context.scene.objects if o.get("group") == group]
    r = rect_of(objs)
    return [max(0, r[0] - mx), max(0, r[1] - my[0]), min(1, r[2] + mx), min(1, r[3] + my[1])], r

def _render(path, crop=None, transparent=True):
    sc = bpy.context.scene; sc.render.film_transparent = transparent
    sc.render.resolution_x, sc.render.resolution_y = STAGE; sc.render.resolution_percentage = 100
    if crop:
        sc.render.use_border = True; sc.render.use_crop_to_border = True
        sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = crop
    else: sc.render.use_border = False
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); sc.render.use_border = False

def _cn(p, c): return [round((p[0] - c[0]) / (c[2] - c[0]), 4), round((p[1] - c[1]) / (c[3] - c[1]), 4)]
def _crect(r, c): a = _cn((r[0], r[1]), c); b = _cn((r[2], r[3]), c); return a + b
def _px(c): return [round((c[2] - c[0]) * STAGE[0]), round((c[3] - c[1]) * STAGE[1])]

def render_stage(what, samples=None):
    os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene; sc.cycles.samples = samples or SAMPLES
    stage_camera()
    if what == "backdrop":
        _vis("backdrop", None); p = os.path.join(OUT, "receiving_backdrop.png"); _render(p, None, transparent=False)
        img = bpy.data.images.load(p, check_existing=False)
        sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.image_settings.quality = 92
        img.save_render(os.path.join(OUT, "receiving_backdrop.jpg"), scene=sc)
        sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'; bpy.data.images.remove(img)
        a = P((DOCK["x0"], 0, 0)); b = P((DOCK["x1"], 0, DOCK["h"]))
        write_json("receiving_backdrop.json", dict(size=list(STAGE), dock=[round(a[0], 4), round(a[1], 4), round(b[0], 4), round(b[1], 4)], floorY=round(P((0, -1.3, 0))[1], 4)))
        return "ok"
    if what == "truck":
        x0, x1, dh = DOCK["x0"], DOCK["x1"], DOCK["h"]
        a = P((x0, 0, 0)); b = P((x1, 0, dh)); crop = [a[0] - .004, a[1] - .004, b[0] + .004, b[1] + .004]
        _vis("truck", "back"); _render(os.path.join(OUT, "receiving_truck_back.png"), crop)
        q = INFO["truck_cargo"]
        write_json("receiving_truck.json", dict(key="truck", size=_px(crop), stage=[round(v, 4) for v in crop],
                   cargo={k: _cn(q[k], crop) for k in ("fl", "fr", "bl", "br")}, ppm=q["ppm"], ppmBack=q["ppmBack"], boxHeight=.42,
                   dockRect=_cn(a, crop) + _cn(b, crop), cargoColumns=2, cargoRows=3))
        return "ok"
    crop, body = _crop(what)
    for layer in ("back", "front"):
        _vis(what, layer); _render(os.path.join(OUT, f"receiving_{what}_{layer}.png"), crop)
    inf = INFO[what]
    data = dict(key=what, size=_px(crop), stage=[round(v, 4) for v in crop], body=_crect(body, crop), bodyWidthM=round(inf["widthM"], 3),
                boxHeight=.42, slots=[dict(level=s["level"], bay=s["bay"], index=s["index"], fl=_cn(s["fl"], crop), fr=_cn(s["fr"], crop),
                                           bl=_cn(s["bl"], crop), br=_cn(s["br"], crop), ppm=s["ppm"], ppmBack=s["ppmBack"]) for s in inf["slots"]])
    data["sign"] = _crect(rect_of([inf["sign"]]), crop)
    if inf.get("display") is not None: data["display"] = _crect(rect_of([inf["display"]]), crop)
    write_json(f"receiving_{what}.json", data)
    return "ok"

# ---------------------------------------------------------------- boxes (512 x 512, contact shadow, eye-level view)
BOX3_VIEW = dict(pitch=14, yaw=0, lens=50)     # square to the camera, like the shelves
BOX3_PITCH = dict(bread=24, crate=20, tray=22, milk=18, pack=16)

def _crate_plastic(nm, W, D, H, m, slots_m, handle=True, ribs=True):
    """Stackable plastic crate: thick rim, ribbed walls with window slots, hand holes on the short sides."""
    t = .012
    box(nm + "_base", (W, D, .02), (0, 0, .01), m, bevel=.005)
    for sy in (-1, 1): box(f"{nm}_wy{sy}", (W, t, H), (0, sy * (D / 2 - t / 2), H / 2), m, bevel=.004)
    for sx in (-1, 1): box(f"{nm}_wx{sx}", (t, D, H), (sx * (W / 2 - t / 2), 0, H / 2), m, bevel=.004)
    box(nm + "_rimF", (W + .008, .02, .025), (0, -D / 2 + .006, H - .012), m, bevel=.006)
    box(nm + "_rimB", (W + .008, .02, .025), (0, D / 2 - .006, H - .012), m, bevel=.006)
    for sx in (-1, 1): box(f"{nm}_rimS{sx}", (.02, D + .008, .025), (sx * (W / 2 - .006), 0, H - .012), m, bevel=.006)
    n = max(3, int(W / .08))
    for k in range(n):
        x = -W / 2 + W * (k + .5) / n
        rounded(f"{nm}_win{k}", W / n * .55, H * .40, (x, -D / 2 - .001, H * .42), slots_m, r=.006, thick=.002, rot=(rad(90), 0, 0))
        if ribs: box(f"{nm}_rib{k}", (.008, .008, H * .9), (x + W / n / 2, -D / 2 - .003, H * .47), m, bevel=.002)
    if handle:
        for sx in (-1, 1): rounded(f"{nm}_hand{sx}", D * .40, .035, (sx * (W / 2 + .001), 0, H - .06), slots_m, r=.015, thick=.002, rot=(rad(90), 0, rad(90)))

def _label(nm, w, h, loc, rot=(rad(90), 0, 0)):
    return rounded(nm, w, h, loc, mat("bx3_label", (0.97, 0.97, 0.95, 1), rough=.6, bump=0), r=.006, thick=.002, rot=rot)

def build_box3_carton():
    """Plain corrugated carton (secos): flaps, brown tape, 'this side up' arrows and a fragile-glass pictogram."""
    W, D, H = .44, .34, .32
    card = mat("bx_card", CARD, rough=.8, bump=.22, scale=120); card_d = mat("bx_card_d", CARD_D, rough=.85, bump=.2, scale=120)
    tape = mat("bx_tape", (0.66, 0.46, 0.24, 1), rough=.25, bump=.04); ink = mat("bx_ink", (0.14, 0.11, 0.10, 1), rough=.8, bump=0)
    blue = mat("bx3_print", BLUE, rough=.75, bump=0)
    box("bx_body", (W, D, H - .02), (0, 0, (H - .02) / 2), card, bevel=.01, seg=4)
    for sx in (-1, 1): box(f"bx_flap{sx}", (W / 2 - .003, D, .02), (sx * W / 4, 0, H - .01 + (.003 if sx > 0 else 0)), card, bevel=.006)
    box("bx_flap_seam", (.005, D - .01, .016), (0, 0, H - .01), card_d, bevel=0)
    box("bx_tape_top", (.06, D + .004, .005), (0, 0, H + .002), tape, bevel=.002)
    box("bx_tape_front", (.06, .005, .10), (0, -D / 2 - .002, H - .05), tape, bevel=.002)
    box("bx3_band", (W + .002, D + .002, .03), (0, 0, .04), blue, bevel=.002)
    for k, x in enumerate((-W * .38, -W * .28)):
        box(f"bx_arr_s{k}", (.008, .002, .06), (x, -D / 2 - .002, H * .55), ink, bevel=0)
        chevron(f"bx_arr_h{k}", x, -D / 2 - .002, H * .55 + .035, .04, ink, plane="wall", thick=.002)
    lab = _label("bx_label", .17, .11, (W * .12, -D / 2 - .004, H * .52))
    return dict(label=lab, size=(W, D, H))

def build_box3_crate():
    W, D, H = .48, .33, .26; t = .017
    PINE, PINE2 = (0.88, 0.66, 0.38, 1), (0.66, 0.44, 0.20, 1)
    pine_x = wood_mat("bx_pine_x", PINE, PINE2); pine_y = wood_mat("bx_pine_y", PINE, PINE2, grain=(22.0, 1.0, 22.0))
    post_m = wood_mat("bx_post", (0.52, 0.32, 0.14, 1), (0.36, 0.20, 0.08, 1), grain=(18.0, 18.0, 1.0)); nail = mat("bx_nail", (0.45, 0.46, 0.46, 1), rough=.35, metal=.9, bump=0)
    ink = mat("bx_stencil", (0.12, 0.34, 0.16, 1), rough=.9, bump=0); paper = mat("bx3_paper", (0.30, 0.55, 0.30, 1), rough=.9, bump=.2, scale=150)
    pw = .03; px, py = W / 2 - t - pw / 2, D / 2 - t - pw / 2
    for sx in (-1, 1):
        for sy in (-1, 1): box(f"bx_cr_post{sx}{sy}", (pw, pw, H - .01), (sx * px, sy * py, (H - .01) / 2), post_m, bevel=.004)
    box("bx_cr_floor", (W - 2 * t, D - 2 * t, .012), (0, 0, .03), pine_x, bevel=.002)
    zs = (.04, .125, .215); bh = .058
    for k, z in enumerate(zs):
        for sy in (-1, 1):
            box(f"bx_cr_bdY{sy}{k}", (W, t, bh), (0, sy * (D / 2 - t / 2), z), pine_x, bevel=.003)
            for sx in (-1, 1): cyl(f"bx_cr_nail{sy}{k}{sx}", .004, .004, (sx * px, sy * (D / 2 + .001), z), nail, rot=(rad(90), 0, 0), verts=10)
        for sx in (-1, 1): box(f"bx_cr_bdX{sx}{k}", (t, D - 2 * t - .004, bh), (sx * (W / 2 - t / 2), 0, z), pine_y, bevel=.003)
    # green tissue liner peeking over the rim
    # a heap of tomatoes, a cluster of oranges and apples, a hand of bananas on top
    rnd = random.Random(21); zf = .19
    for i in range(4):
        for j in range(3):
            x = -W / 2 + .07 + i * .108 + rnd.uniform(-.008, .008); y = -D / 2 + .07 + j * .095 + rnd.uniform(-.008, .008)
            kind = "tomato" if i < 2 else ("orange" if j != 1 else "apple")
            if kind == "tomato": tomato(f"bx3_tom{i}{j}", (x, y, zf + .02), r=.043, rot=rnd.uniform(0, 6))
            elif kind == "orange": orange_fruit(f"bx3_or{i}{j}", (x, y, zf + .025), r=.046)
            else: apple(f"bx3_ap{i}{j}", (x, y, zf + .025), r=.044, rot=rnd.uniform(0, 6))
    for k, (x, y) in enumerate(((-.17, -.04), (-.10, .05), (-.05, -.06), (-.18, .07))): tomato(f"bx3_tomt{k}", (x, y, zf + .075), r=.042, rot=k * 1.3)
    for k, (x, y) in enumerate(((.05, .07), (.12, -.07))): orange_fruit(f"bx3_ort{k}", (x, y, zf + .07), r=.045)
    banana_hand("bx3_ban", (.13, .0, zf + .075), n=4, rot=rad(-20))

    lab = _label("bx_cr_tag", .14, .052, (W * .24, -D / 2 - .004, zs[1]))
    return dict(label=lab, size=(W, D, H + .08))

def build_box3_bread():
    """Bakery delivery crate (low, green plastic, parchment liner) heaped with paes franceses."""
    W, D, H = .48, .34, .075
    crate = mat("bx3_bread_crate", (0.10, 0.50, 0.30, 1), rough=.45, bump=.04, spec=.4); dark = mat("bx3_slot", (0.02, 0.10, 0.05, 1), rough=.9, bump=0)
    _crate_plastic("bx3_bc", W, D, H, crate, dark, handle=False)
    paper = mat("bx3_bpaper", (0.95, 0.93, 0.86, 1), rough=.9, bump=.2, scale=90)
    box("bx3_bpaper", (W - .03, D - .03, .006), (0, 0, .024), paper, bevel=.002)
    for sx in (-1, 1): box(f"bx3_bpaper_up{sx}", (.006, D - .06, .05), (sx * (W / 2 - .03), 0, .055), paper, bevel=.002, rot=(0, rad(sx * 20), 0))
    rnd = random.Random(3); k = 0
    for i in range(3):
        for j in range(4):
            french_roll(f"bx3_roll{k}", (-W / 2 + .085 + i * .155 + rnd.uniform(-.008, .008), -D / 2 + .05 + j * .078, .022), rnd.uniform(-8, 8), seed=k); k += 1
    for i in range(2):
        for j in range(3):
            french_roll(f"bx3_roll{k}", (-W / 2 + .16 + i * .155 + rnd.uniform(-.01, .01), -D / 2 + .09 + j * .078, .060), rnd.uniform(-14, 14), seed=k); k += 1
    french_roll(f"bx3_roll{k}", (-.01, .0, .098), 25, seed=k)
    lab = _label("bx3_bread_lbl", .14, .042, (W * .24, -D / 2 - .004, H * .5))
    return dict(label=lab, size=(W, D, .16))

def build_box3_pack():
    """Engradado de refrigerante: red plastic crate, 12 glass bottles with crown caps."""
    W, D, H = .40, .30, .17
    crate = mat("bx3_red", (0.78, 0.06, 0.05, 1), rough=.4, bump=.04, spec=.45); dark = mat("bx3_slot2", (0.12, 0.02, 0.02, 1), rough=.9, bump=0)
    _crate_plastic("bx3_pk", W, D, H, crate, dark)
    glass = mat("bx3_glass", (0.30, 0.13, 0.04, 1), rough=.05, transmission=.85, bump=0, spec=.8); capm = mat("bx3_cap", (0.85, 0.80, 0.70, 1), rough=.25, metal=.9, bump=0)
    lbl = mat("bx3_blabel", (0.95, 0.85, 0.20, 1), rough=.5, bump=0)
    prof = [(.0, 0), (.028, .002), (.031, .01), (.031, .17), (.027, .20), (.015, .245), (.0125, .28), (.0135, .29), (.0, .292)]
    for i in range(4):
        for j in range(3):
            x = -W / 2 + .058 + i * .095; y = -D / 2 + .055 + j * .095
            lathe(f"bx3_bt{i}{j}", prof, (x, y, .015), glass, segs=20)
            cyl(f"bx3_btc{i}{j}", .015, .012, (x, y, .015 + .296), capm, verts=14, bevel=.003)
            cyl(f"bx3_btl{i}{j}", .0315, .06, (x, y, .015 + .11), lbl, verts=20)
    lab = _label("bx3_pk_lbl", .16, .055, (0, -D / 2 - .004, H * .55))
    return dict(label=lab, size=(W, D, .33))

def build_box3_water():
    """Fardo de agua: 6 x 1,5 L PET bottles, blue caps and labels, wrapped in film with a carry strip."""
    W, D = .27, .18; r = .044; hb = .31
    pet = mat("bx3_pet", (0.82, 0.92, 1.0, 1), rough=.05, transmission=.92, bump=0, spec=.6)
    capm = mat("bx3_wcap", (0.05, 0.35, 0.85, 1), rough=.35, bump=0); lblm = mat("bx3_wlabel", (0.10, 0.45, 0.88, 1), rough=.45, bump=0)
    film = mat("bx3_film", (0.92, 0.96, 1.0, 1), rough=.12, alpha=.16, bump=.06, scale=40, spec=.5)
    prof = [(0, 0), (r * .85, .0), (r, .02), (r, .08), (r * .93, .095), (r, .11), (r, .19), (r * .93, .205), (r, .22), (r, .245), (r * .55, .29), (.014, .30), (.014, .31), (0, .31)]
    xs = (-.092, 0, .092); ys = (-.046, .046)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            lathe(f"bx3_w{i}{j}", prof, (x, y, 0), pet, segs=24)
            cyl(f"bx3_wc{i}{j}", .016, .02, (x, y, .318), capm, verts=16, bevel=.004)
            cyl(f"bx3_wl{i}{j}", r + .001, .07, (x, y, .15), lblm, verts=24)
    box("bx3_film", (W + .02, D + .015, hb - .02), (0, 0, (hb - .02) / 2 + .005), film, bevel=.035, seg=5)
    lab = _label("bx3_w_lbl", .13, .05, (0, -D / 2 - .012, .15))
    return dict(label=lab, size=(W + .02, D + .02, .34))

def build_box3_milk():
    """Engradado de leite: blue crate with twelve 1 L cartons (white, blue band, screw cap)."""
    W, D, H = .40, .30, .15
    crate = mat("bx3_blue", (0.06, 0.32, 0.78, 1), rough=.4, bump=.04, spec=.45); dark = mat("bx3_slot3", (0.02, 0.05, 0.14, 1), rough=.9, bump=0)
    _crate_plastic("bx3_mk", W, D, H, crate, dark)
    white = mat("bx3_carton", (0.97, 0.97, 0.96, 1), rough=.35, bump=0, spec=.4); band = mat("bx3_milkband", (0.10, 0.45, 0.85, 1), rough=.4, bump=0)
    capm = mat("bx3_mcap", (0.05, 0.30, 0.75, 1), rough=.4, bump=0); grass = mat("bx3_grass", (0.30, 0.65, 0.20, 1), rough=.5, bump=0)
    cw, cd, ch = .066, .066, .19
    for i in range(4):
        for j in range(3):
            x = -W / 2 + .052 + i * .098; y = -D / 2 + .053 + j * .097
            box(f"bx3_ct{i}{j}", (cw, cd, ch), (x, y, .02 + ch / 2), white, bevel=.004)
            box(f"bx3_ctb{i}{j}", (cw + .002, cd + .002, .05), (x, y, .02 + ch * .40), band, bevel=.002)
            box(f"bx3_ctg{i}{j}", (cw + .003, cd + .003, .012), (x, y, .02 + ch * .22), grass, bevel=.001)
            box(f"bx3_ctt{i}{j}", (cw * .98, .012, .02), (x, y + cd * .25, .02 + ch + .006), white, bevel=.003)
            cyl(f"bx3_ctc{i}{j}", .011, .014, (x + .012, y - .012, .02 + ch + .007), capm, verts=14, bevel=.003)
    lab = _label("bx3_mk_lbl", .16, .055, (0, -D / 2 - .004, H * .52))
    return dict(label=lab, size=(W, D, .24))

def build_box3_frozen():
    """Caixa termica (isopor): beaded styrofoam body and lid, blue tape, a 'CONGELADO' print and frost."""
    W, D, H = .44, .32, .28
    foam = mat("bx3_foam", (0.96, 0.96, 0.95, 1), rough=.75, bump=.45, scale=420); blue = mat("bx3_tape", (0.08, 0.36, 0.82, 1), rough=.3, bump=.02)
    ink = mat("bx3_fink", (0.08, 0.30, 0.70, 1), rough=.8, bump=0); frost = mat("bx_frost", (0.93, 0.97, 1.0, 1), rough=.9, bump=.4, scale=200)
    box("bx3_fz_body", (W, D, H - .05), (0, 0, (H - .05) / 2), foam, bevel=.015, seg=4)
    box("bx3_fz_lid", (W + .016, D + .016, .06), (0, 0, H - .02), foam, bevel=.018, seg=4)
    box("bx3_fz_lidstep", (W - .03, D - .03, .02), (0, 0, H + .015), foam, bevel=.008)
    for sx in (-1, 1): box(f"bx3_fz_tape{sx}", (.05, D + .025, H + .03), (sx * W * .30, 0, (H + .03) / 2), blue, bevel=.004)
    snowflake("bx3_fz_flake", 0, -D / 2 - .003, H * .28, .045, ink)
    rnd = random.Random(5)
    lab = _label("bx3_fz_lbl", .16, .065, (0, -D / 2 - .003, H * .64))
    return dict(label=lab, size=(W + .02, D + .02, H + .03))

def build_box3_tray():
    """Ovos: an open low carton holding two stacked pulp trays of 30 brown/white eggs."""
    W, D, H = .36, .36, .12
    card = mat("bx_card", CARD, rough=.8, bump=.22, scale=120); pulp = mat("bx3_pulp", (0.70, 0.66, 0.58, 1), rough=.95, bump=.4, scale=260)
    brown = _shade("egg_brown", (0.78, 0.52, 0.32, 1), (0.84, 0.60, 0.40, 1), rough=.55, spec=.3, bump=.08, bump_scale=600)
    white = _shade("egg_white", (0.95, 0.92, 0.86, 1), (0.97, 0.95, 0.90, 1), rough=.55, spec=.3, bump=.08, bump_scale=600)
    box("bx3_eg_floor", (W, D, .015), (0, 0, .0075), card, bevel=.004)
    for sy in (-1, 1): box(f"bx3_eg_wy{sy}", (W, .012, H), (0, sy * (D / 2 - .006), H / 2), card, bevel=.004)
    for sx in (-1, 1): box(f"bx3_eg_wx{sx}", (.012, D, H), (sx * (W / 2 - .006), 0, H / 2), card, bevel=.004)
    for k, z in enumerate((.035, .10)):
        box(f"bx3_tray{k}", (W - .03, D - .03, .02), (0, 0, z), pulp, bevel=.008)
        for i in range(6):
            for j in range(5):
                x = -W / 2 + .042 + i * .055; y = -D / 2 + .045 + j * .068
                if k == 1: egg(f"bx3_egg{i}{j}", (x, y, z + .035), r=.021, m=brown if (i * 3 + j * 5) % 4 else white)
                else: cyl(f"bx3_cup{i}{j}", .022, .02, (x, y, z + .015), pulp, verts=12)
    box("bx3_eg_print", (W * .7, .002, .03), (0, -D / 2 - .002, H * .78), mat("bx3_eg_ink", ORANGE, rough=.8, bump=0), bevel=0)
    lab = _label("bx3_eg_lbl", .15, .045, (0, -D / 2 - .004, H * .40))
    return dict(label=lab, size=(W, D, H + .08))

BOXES3 = {"carton": build_box3_carton, "crate": build_box3_crate, "bread": build_box3_bread, "pack": build_box3_pack,
          "water": build_box3_water, "milk": build_box3_milk, "frozen": build_box3_frozen, "tray": build_box3_tray}

def render_box(name, samples=None, res=BOX_RES):
    clear(); sc = scene(); sc.cycles.samples = samples or SAMPLES; set_off(0, 0); sc.view_settings.exposure = .15
    v = BOXES3[name](); strip_text(); W, D, H = v["size"]
    ground = box("bx3_ground", (6, 6, .01), (0, 0, -.005), mat("bx3_ground", (0.5, 0.5, 0.5, 1), rough=.9, bump=0), bevel=0); ground["nofit"] = True; ground.is_shadow_catcher = True
    camera((0, 0, H * .45), BOX3_PITCH.get(name, BOX3_VIEW["pitch"]), 2.2, BOX3_VIEW["lens"], yaw_deg=BOX3_VIEW["yaw"])
    sc.render.resolution_x, sc.render.resolution_y = res; fit_camera(1.12)
    light_rig((0, 0, H / 2), max(W, H) * 1.3, warm=.42, world=.32)
    for o in sc.objects:
        if o.type == 'LIGHT' and o.name.startswith("Key"): o.location = Vector((-.6, -1.6, 2.2)); o.rotation_euler = (Vector((0, 0, 0)) - o.location).to_track_quat('-Z', 'Y').to_euler()
    pv = proj((0, 0, 0))
    marks = dict(label=obj_rect(v["label"]), pivot=[round(pv[0], 4), round(pv[1], 4)], ppm=ppm_at((0, 0, 0)), width=W, depth=D, height=H)
    sc.render.film_transparent = True; sc.render.use_border = False
    p = os.path.join(OUT, f"box_{name}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    write_json(f"box_{name}_marks.json", marks)
    return p

# ---------------------------------------------------------------- clipboard and stamp, without printed words
def render_clipboard3():
    clear(); sc = scene(); sc.cycles.samples = SAMPLES; sc.view_settings.exposure = 0; set_off(0, 0)
    v = build_clipboard(); strip_text()
    camera((0, -.004, 0), 84, 1.0, 50); sc.render.resolution_x, sc.render.resolution_y = CLIP_RES; fit_camera(1.05)
    light_rig((0, 0, 0), .45, warm=.45, world=.3)
    data = dict(size=list(CLIP_RES), sheet=obj_rect(v["sheet"]))
    L = v["lines"]
    data["lines"] = [dict(x0=proj((L["x0"], L["yTop"] - k * L["step"], .011))[0], x1=proj((L["x1"], L["yTop"] - k * L["step"], .011))[0],
                          y=proj((0, L["yTop"] - k * L["step"] - L["step"] * .45, .011))[1]) for k in range(L["n"])]
    sc.render.film_transparent = True; sc.render.use_border = False
    p = os.path.join(OUT, "receiving_clipboard.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    write_json("receiving_clipboard.json", data)
    return p

def render_stamp3():
    clear(); sc = scene(); sc.cycles.samples = SAMPLES; sc.view_settings.exposure = 0; set_off(0, 0)
    build_stamp(); strip_text()
    ink = _M.get("st_ink")
    for o in list(sc.objects):
        if o.name.startswith("st_ck"): bpy.data.objects.remove(o, do_unlink=True)
    box("st_ck1", (.024, .085, .002), (-.055, -.02, 0), ink, bevel=.006, rot=(0, 0, rad(42)))
    box("st_ck2", (.024, .17, .002), (.03, .015, 0), ink, bevel=.006, rot=(0, 0, rad(-34)))
    camera((0, 0, 0), 89.9, 1.2, 50); sc.render.resolution_x, sc.render.resolution_y = BOX_RES; fit_camera(1.08)
    light_rig((0, 0, 0), .5, warm=.4, world=.4)
    sc.render.film_transparent = True; sc.render.use_border = False
    p = os.path.join(OUT, "stamp_conferido.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    return p
