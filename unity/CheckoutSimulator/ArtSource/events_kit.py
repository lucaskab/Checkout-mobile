# events_kit.py - props for the market events (round "eventos repaginados", Oct 2026).
# Same family as era_kit / works_kit (metres, Blender Z up, front = +Y, procedural materials baked to one atlas per FBX).
# Each event builds its props into its own collection "EV <Event>" on a small street diorama (road, curb, sidewalk,
# a slice of the market facade) so the preview shows WHERE the props stand in the game.
#
#   import sys; sys.path.insert(0, "<repo>/unity/CheckoutSimulator/ArtSource")
#   import events_kit as E; E.build("HoraDoRush"); E.preview("HoraDoRush")   # ArtSource/Review/events_v2/<name>.png
#   E.build_all(); E.preview_all()
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, "scripts", "blender"))
import era_kit as k
import checkout_project as cp
cp.ROOT = REPO; cp.UNITY = os.path.join(REPO, "unity", "CheckoutSimulator"); cp.ART_SOURCE = HERE
import lot_kit as L
import works_kit as W
W.REVIEW = os.path.join(HERE, "Review", "works_v1")
REVIEW = os.path.join(HERE, "Review", "events_v2")
rad = math.radians

# ------------------------------------------------------------------ palette (the market's current vivid colours)
C = dict(
    teal=(.06, .52, .48, 1), tealL=(.25, .74, .64, 1), navy=(.05, .10, .30, 1), cream=(.96, .90, .72, 1),
    white=(.95, .94, .90, 1), red=(.86, .20, .15, 1), orange=(.97, .52, .10, 1), yellow=(.98, .80, .16, 1),
    gold=(.91, .70, .27, 1), green=(.10, .55, .22, 1), lime=(.55, .80, .20, 1), blue=(.10, .40, .80, 1),
    sky=(.45, .75, .95, 1), pink=(.95, .45, .60, 1), purple=(.50, .28, .70, 1), dark=(.13, .14, .16, 1),
    grey=(.55, .57, .58, 1), steel=(.70, .72, .74, 1), brown=(.45, .28, .16, 1), skin=(.90, .67, .46, 1))
M = {}

def mats():
    if M: return M
    for n, c in C.items():
        M[n] = k.mat("EV_" + n, c, rough=.55, var=.07, scale=6)
    M["chrome"] = k.mat("EV_Chrome", (.80, .82, .84, 1), rough=.25, var=.04, scale=8, metallic=.8)
    M["rubber"] = k.mat("EV_Rubber", (.09, .09, .10, 1), rough=.85, var=.05, scale=12)
    M["glass"] = k.mat("EV_Glass", (.30, .52, .62, 1), rough=.12, var=.05, scale=3)
    M["glassL"] = k.mat("EV_GlassLight", (.62, .82, .88, 1), rough=.12, var=.05, scale=3)
    M["screen"] = k.emissive("EV_Screen", (.30, .75, 1.0, 1), 2.5)
    M["lamp"] = k.emissive("EV_Lamp", (1.0, .93, .75, 1), 4.0)
    M["tail"] = k.emissive("EV_Tail", (1.0, .12, .08, 1), 2.0)
    M["amber"] = k.emissive("EV_Amber", (1.0, .55, .05, 1), 3.0)
    M["ledR"] = k.emissive("EV_LedRed", (1.0, .18, .10, 1), 4.0)
    M["ledG"] = k.emissive("EV_LedGreen", (.25, 1.0, .35, 1), 4.0)
    M["asphalt"] = k.mat("EV_Asphalt", (.24, .25, .26, 1), rough=.95, var=.18, scale=14, bump=.25)
    M["concrete"] = k.mat("EV_Concrete", (.72, .70, .66, 1), rough=.95, var=.12, scale=9, bump=.2)
    M["pavers"] = k.pavers("ERA_Pavers")
    M["wood"] = k.wood("EV_Wood")
    M["canvasR"] = k.stripes("EV_CanvasRed", C["red"], C["white"], .22)
    M["canvasB"] = k.stripes("EV_CanvasBlue", C["blue"], C["white"], .22)
    M["canvasG"] = k.stripes("EV_CanvasGreen", C["green"], C["yellow"], .22)
    M["hazard"] = W.hazard("EV_Hazard")
    M["hazardR"] = W.hazard("EV_HazardRed", (.85, .15, .12, 1), (.93, .93, .90, 1), .09)
    M["ink"] = k.mat("EV_Ink", (.05, .05, .06, 1), rough=.9, var=0)
    M["paper"] = k.mat("EV_Paper", (.98, .97, .93, 1), rough=.9, var=.02)
    return M

def collection(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    return c

def clear(name):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    return collection(name)

def label(c, s, size, loc, m, rot=(rad(90), 0, 0), extrude=.006):
    return k.text("lbl", s, size, loc, m, rot=rot, extrude=extrude, c=c)

def wheel(c, loc, R=.38, w=.24, axis='X'):
    m = mats(); rot = (0, rad(90), 0) if axis == 'X' else (rad(90), 0, 0)
    t = k.cyl("tire", R, w, loc, m["rubber"], rot=rot, verts=24, bevel=.03, c=c)
    off = Vector((w / 2 + .002, 0, 0)) if axis == 'X' else Vector((0, w / 2 + .002, 0))
    for s in (-1, 1):
        k.cyl("rim", R * .58, .02, Vector(loc) + off * s, m["chrome"], rot=rot, verts=20, c=c)
        k.cyl("hub", R * .2, .03, Vector(loc) + off * s * 1.02, m["grey"], rot=rot, verts=12, c=c)
    return t

def person(c, loc, shirt, rot=0, h=1.7, pants=None, pose="stand"):
    """Simple low-poly stand-in (only for the previews: the game uses its own animated characters)."""
    m = mats(); x, y = loc; pants = pants or m["navy"]
    g = []
    for s in (-1, 1):
        g.append(k.cyl("leg", .07, h * .47, (x + s * .09, y, h * .235), pants, verts=10, c=c))
    g.append(k.box("torso", (.36, .22, h * .32), (x, y, h * .63), shirt, bevel=.06, seg=3, c=c))
    g.append(k.ball("head", .12, (x, y, h * .88), m["skin"], sub=2, c=c))
    g.append(k.ball("hair", .125, (x, y + .02, h * .915), m["brown"], sub=2, scale=(1, 1, .6), c=c))
    for s in (-1, 1):
        g.append(k.cyl("arm", .05, h * .32, (x + s * .23, y, h * .62), shirt, verts=8, c=c))
    for o in g:
        o.location = Matrix.Rotation(rot, 3, 'Z') @ (o.location - Vector((x, y, 0))) + Vector((x, y, 0)); o.rotation_euler.z += rot
    return g

CHAR_DIR = os.path.join(REPO, "unity", "CheckoutSimulator", "Assets", "Art", "Characters", "Meshy")
def _char_source(name):
    """The game's own customer model (Meshy, textured), imported once into the hidden "REF chars" collection."""
    rc = bpy.data.collections.get("REF chars") or bpy.data.collections.new("REF chars")
    rig = next((o for o in rc.objects if o.get("char") == name and o.type == 'ARMATURE'), None)
    if rig: return rig
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CHAR_DIR, name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for cc in list(o.users_collection): cc.objects.unlink(o)
        if o.name.endswith("_Prop"): bpy.data.objects.remove(o); continue
        rc.objects.link(o); o["char"] = name
    return next(o for o in rc.objects if o.get("char") == name and o.type == 'ARMATURE')

def actor(c, name, loc, rot=0.0, scale=.72):
    """Places one of the game's customers (Customer_06..09) - previews only; in the game the event spawns the live ones."""
    rig = _char_source(name)
    holder = bpy.data.objects.new("actor_" + name, None); c.objects.link(holder)
    holder.location = (loc[0], loc[1], loc[2] if len(loc) > 2 else .13); holder.rotation_euler = (0, 0, rot); holder.scale = (scale,) * 3
    r2 = rig.copy(); c.objects.link(r2); r2.parent = holder   # the rig's own action keys its root, so move the holder
    for ch in rig.children:
        b = ch.copy(); c.objects.link(b); b.parent = r2
        for md in b.modifiers:
            if md.type == 'ARMATURE': md.object = r2
    return r2

# ------------------------------------------------------------------ street diorama
def diorama(c, w=14, facade=True, road=True, depth=10):
    """Road at -Y (towards the camera), curb, sidewalk, then a slice of the market facade at the back."""
    m = mats()
    if road:
        k.box("road", (w, 4.2, .1), (0, -3.6, -.05), m["asphalt"], bevel=0, c=c)
        for i in range(int(w / 2.4) + 1):
            k.box("dash", (1.2, .12, .005), (-w / 2 + .9 + i * 2.4, -4.1, .002), m["white"], bevel=0, c=c)
        k.box("curb", (w, .22, .16), (0, -1.39, .03), m["concrete"], bevel=.02, c=c)
    k.box("sidewalk", (w, depth - 4.7 if road else depth, .13), (0, (-1.28 + depth - 4.7) / 2 if road else 0, .065), m["pavers"], bevel=0, c=c)
    if facade:
        y = depth - 4.6
        k.box("wall", (w, .3, 3.6), (0, y + .15, 1.8), m["cream"], bevel=.02, c=c)
        k.box("base", (w, .34, .45), (0, y + .15, .35), m["teal"], bevel=.02, c=c)
        k.box("cornice", (w, .5, .25), (0, y + .1, 3.55), m["teal"], bevel=.03, c=c)
        for x in (-4.2, 4.2):
            k.box("window", (2.6, .05, 1.7), (x, y - .01, 1.75), m["glass"], bevel=.01, c=c)
            k.box("sill", (2.8, .2, .08), (x, y - .07, .87), m["white"], c=c)
            k.box("awn", (2.9, .9, .06), (x, y - .4, 2.85), m["canvasG"], rot=(rad(-18), 0, 0), bevel=.01, c=c)
        k.box("doorframe", (2.0, .12, 2.5), (0, y - .02, 1.38), m["navy"], bevel=.02, c=c)
        k.box("door", (1.7, .06, 2.3), (0, y - .06, 1.28), m["glassL"], bevel=.01, c=c)
        k.box("signboard", (4.2, .15, .62), (0, y - .1, 3.05), m["red"], bevel=.03, c=c)
        label(c, "CHECKOUT", .42, (0, y - .19, 3.03), m["white"])
    return c

# ------------------------------------------------------------------ preview
ISO = (1.0, -1.25, 1.05)   # front-right, the game's look (front = -Y towards the camera here)

def preview(name, res=(1400, 900), ortho=None, target=None, direction=ISO):
    cname = "EV " + name
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = lc.name not in (cname, "Studio")
    objs = list(bpy.data.collections[cname].all_objects)
    lo = Vector((min(o.matrix_world.translation.x for o in objs), min(o.matrix_world.translation.y for o in objs), 0))
    hi = Vector((max(o.matrix_world.translation.x for o in objs), max(o.matrix_world.translation.y for o in objs), 3))
    t = Vector(target) if target else (lo + hi) / 2
    sc = bpy.context.scene
    cp.studio(); sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.engine = 'BLENDER_EEVEE'
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = .55
    bpy.data.objects["Studio Sun"].data.energy = 3.6
    sc.view_settings.exposure = -0.15
    cam = bpy.data.objects.get("Studio Cam")
    if not cam:
        cam = bpy.data.objects.new("Studio Cam", bpy.data.cameras.new("Studio Cam")); collection("Studio").objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho or 15; cam.data.clip_end = 500
    d = Vector(direction).normalized(); cam.location = t + d * 60
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    os.makedirs(REVIEW, exist_ok=True)
    sc.render.filepath = os.path.join(REVIEW, name + ".png")
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath

BUILDERS = {}
def event(fn):
    BUILDERS[fn.__name__] = fn
    return fn

def build(name):
    c = clear("EV " + name); mats(); BUILDERS[name](c); return c

def build_all():
    for n in BUILDERS: build(n)

def preview_all(**kw):
    return [preview(n, **kw) for n in BUILDERS]

# ================================================================== props
def city_bus(c, x=0, y=-3.2, length=10.8, body="white", stripe="teal", accent="yellow", sign="123 CENTRO"):
    """Low-floor city bus driving along +X, doors on the sidewalk side (+Y). ~6k tris after bevels."""
    m = mats(); W_, H = 2.5, 3.0; z0 = .32; fx, bx = x + length / 2, x - length / 2
    k.box("bus_body", (length, W_, H - z0), (x, y, z0 + (H - z0) / 2), m[body], bevel=.22, seg=4, c=c)
    k.box("bus_skirt", (length - .1, W_ + .02, .55), (x, y, z0 + .27), m[stripe], bevel=.12, seg=3, c=c)
    k.box("bus_stripe", (length - .3, W_ + .03, .14), (x - .1, y, .98), m[accent], bevel=.05, seg=2, c=c)
    # continuous tinted window band with body-colour pillars
    for s in (-1, 1):
        k.box("bus_glass", (length - 1.4, .04, 1.05), (x - .45, y + s * (W_ / 2 + .004), 2.18), m["glass"], bevel=.05, c=c)
        for i in range(8):
            px = bx + 1.0 + i * 1.32
            k.box("bus_pillar", (.12, .05, 1.07), (px, y + s * (W_ / 2 + .012), 2.18), m[body], bevel=.02, c=c)
        for ax in (fx - 2.3, bx + 2.6):   # wheel arches + wheels
            k.cyl("bus_arch", .6, .04, (ax, y + s * (W_ / 2 + .005), .5), m["dark"], rot=(rad(90), 0, 0), verts=24, c=c)
            wheel(c, (ax, y + s * (W_ / 2 - .14), .5), R=.5, w=.3, axis='Y')
    # doors on the sidewalk side: framed double leaves
    for dx in (fx - 1.25, x + .2):
        k.box("bus_doorframe", (1.36, .05, 2.42), (dx, y + W_ / 2 + .01, 1.55), m["dark"], bevel=.03, c=c)
        for lx in (-.31, .31):
            k.box("bus_door", (.56, .04, 2.2), (dx + lx, y + W_ / 2 + .03, 1.55), m["glassL"], bevel=.02, c=c)
        k.box("bus_doorlamp", (.3, .04, .08), (dx, y + W_ / 2 + .04, 2.8), m["amber"], bevel=.01, c=c)
    # front: big windscreen, LED destination sign, grille, lamps, wipers, mirrors
    k.box("bus_windshield", (.06, W_ - .2, 1.55), (fx + .005, y, 1.95), m["glass"], bevel=.06, c=c)
    k.box("bus_destination", (.07, W_ - .4, .34), (fx + .02, y, 2.85), m["dark"], bevel=.03, c=c)
    label(c, sign, .2, (fx + .06, y, 2.84), m["amber"], rot=(rad(90), 0, rad(90)))
    k.box("bus_grille", (.05, 1.3, .3), (fx + .01, y, .95), m["dark"], bevel=.03, c=c)
    k.box("bus_bumper", (.16, W_ + .02, .3), (fx + .06, y, .5), m["dark"], bevel=.06, c=c)
    k.box("bus_bumper_r", (.16, W_ + .02, .3), (bx - .06, y, .5), m["dark"], bevel=.06, c=c)
    k.box("bus_engine", (.05, 1.6, .7), (bx - .01, y, 1.05), m["dark"], bevel=.03, c=c)
    k.box("bus_rearglass", (.05, W_ - .4, .9), (bx - .005, y, 2.3), m["glass"], bevel=.05, c=c)
    for s in (-1, 1):
        k.box("bus_head", (.05, .38, .17), (fx + .02, y + s * .88, .95), m["lamp"], bevel=.04, c=c)
        k.box("bus_tail", (.05, .18, .55), (bx - .02, y + s * 1.05, 1.2), m["tail"], bevel=.04, c=c)
        k.box("bus_wiper", (.03, .7, .03), (fx + .05, y + s * .5, 1.25), m["dark"], rot=(rad(25 * s), 0, 0), c=c)
        k.box("bus_mirror_arm", (.45, .05, .05), (fx + .18, y + s * 1.2, 2.55), m["dark"], c=c)
        k.box("bus_mirror", (.07, .2, .42), (fx + .4, y + s * 1.3, 2.32), m["dark"], bevel=.04, c=c)
    k.box("bus_roof_ac", (2.6, 1.7, .3), (bx + 3.2, y, H + .12), m["white"], bevel=.1, seg=3, c=c)
    k.box("bus_roof_vent", (.9, .8, .1), (x + 1.8, y, H + .02), m["grey"], bevel=.04, c=c)
    label(c, "TRANSPORTE URBANO", .2, (x - .3, y - W_ / 2 - .02, 1.42), m[stripe], rot=(rad(90), 0, 0))
    return c

def bus_shelter(c, x=0, y=1.0, w=4.2):
    m = mats(); d = 1.5
    for sx in (-1, 1):
        for sy in (0, 1):
            k.cyl("post", .05, 2.5, (x + sx * (w / 2 - .1), y + sy * (d - .2), 1.38), m["steel"], verts=12, c=c)
    k.box("roof", (w + .3, d + .25, .14), (x, y + d / 2 - .1, 2.68), m["teal"], bevel=.05, seg=3, c=c)
    k.box("roof_edge", (w + .32, .06, .2), (x, y - .23, 2.62), m["yellow"], bevel=.02, c=c)
    label(c, "PONTO DE ÔNIBUS", .16, (x, y - .27, 2.62), m["navy"])
    k.box("back_glass", (w - .3, .03, 1.7), (x, y + d - .2, 1.2), m["glassL"], bevel=.01, c=c)
    k.box("ad_frame", (1.3, .14, 1.9), (x + w / 2 - .1, y + d / 2 - .1, 1.3), m["steel"], bevel=.03, c=c)
    k.box("ad_light", (.03, 1.0, 1.6), (x + w / 2 - .18, y + d / 2 - .1, 1.32), m["screen"], rot=(0, 0, 0), bevel=0, c=c)
    k.box("bench", (2.6, .42, .07), (x - .4, y + d - .5, .5), m["wood"], bevel=.02, c=c)
    for bx in (-1.5, .7):
        k.box("bench_leg", (.06, .38, .45), (x + bx, y + d - .5, .27), m["steel"], c=c)
    k.cyl("stop_pole", .045, 3.0, (x - w / 2 - .6, y - .2, 1.6), m["steel"], verts=10, c=c)
    k.cyl("stop_plate", .32, .04, (x - w / 2 - .6, y - .25, 2.85), m["blue"], rot=(rad(90), 0, 0), verts=28, c=c)
    label(c, "BUS", .2, (x - w / 2 - .6, y - .28, 2.85), m["white"])
    k.box("timetable", (.42, .03, .6), (x - w / 2 - .6, y - .25, 1.9), m["paper"], bevel=.01, c=c)
    return c

@event
def HoraDoRush(c):
    diorama(c)
    bus_shelter(c, x=-3.0, y=-1.0)
    city_bus(c, x=-1.0, y=-2.8)
    for i, (px, py, who, r) in enumerate([(-4.6, -.2, "Customer_06", 200), (-3.6, .1, "Customer_08", 170), (.0, -.9, "Customer_07", 20),
                                           (1.0, -.3, "Customer_09", 40), (2.3, .6, "Customer_06", 60), (3.4, 1.6, "Customer_07", 80)]):
        actor(c, who, (px, py), rad(r))

# ------------------------------------------------------------------ shared vehicles / street furniture
def vehicle(c, x, y, kind="van", paint="white", length=None, heading=0.0, stripe=None, roof=None):
    """kind: car | van | box (box truck) | pickup. Drives along +X. Doors / livery on both sides."""
    m = mats(); p = m[paint]; before = set(c.objects)
    L_ = length or {"car": 4.2, "van": 4.9, "box": 7.2, "pickup": 5.2}[kind]
    W_ = 2.0 if kind != "box" else 2.4
    objs = []
    def B(*a, **kw): o = k.box(*a, c=c, **kw); objs.append(o); return o
    def Cy(*a, **kw): o = k.cyl(*a, c=c, **kw); objs.append(o); return o
    fx, bx = L_ / 2, -L_ / 2
    if kind == "car":
        B("car_body", (L_, W_, .7), (0, 0, .62), p, bevel=.16, seg=4)
        B("car_cabin", (2.3, W_ - .2, .62), (-.2, 0, 1.2), p, bevel=.18, seg=4)
        for s in (-1, 1):
            B("car_side_glass", (2.05, .03, .44), (-.2, s * (W_ / 2 - .09), 1.22), m["glass"], bevel=.06)
            B("car_pillar", (.08, .04, .46), (-.2, s * (W_ / 2 - .085), 1.22), p)
        B("car_windshield", (.05, W_ - .35, .48), (.97, 0, 1.2), m["glass"], rot=(0, rad(-35), 0), bevel=.05)
        B("car_rear_glass", (.05, W_ - .35, .44), (-1.37, 0, 1.2), m["glass"], rot=(0, rad(35), 0), bevel=.05)
        axles = (fx - .85, bx + .8); R = .34
    elif kind in ("van", "pickup"):
        H = 2.0 if kind == "van" else 1.55
        if kind == "van":
            B("van_body", (L_, W_, H - .3), (0, 0, .3 + (H - .3) / 2), p, bevel=.2, seg=4)
        else:
            B("cab", (2.4, W_, 1.25), (fx - 1.2, 0, .95), p, bevel=.18, seg=4)
        if kind == "pickup":
            B("bed", (2.6, W_, .55), (bx + 1.3, 0, .72), p, bevel=.05)
            B("bed_in", (2.4, W_ - .2, .1), (bx + 1.3, 0, .9), m["dark"], bevel=0)
        B("van_windshield", (.06, W_ - .3, .75), (fx - .02 if kind == "van" else fx - .02, 0, 1.45 if kind == "van" else 1.25), m["glass"], rot=(0, rad(-12), 0), bevel=.05)
        for s in (-1, 1):
            B("van_door_glass", (.8, .03, .6), (fx - .75, s * (W_ / 2 + .003), 1.5 if kind == "van" else 1.25), m["glass"], bevel=.05)
            if kind == "van":
                B("van_side_glass", (1.9, .03, .5), (-.5, s * (W_ / 2 + .003), 1.55), m["glass"], bevel=.05)
                B("van_slide_line", (.03, .04, 1.35), (.35, s * (W_ / 2 + .004), 1.0), m["dark"])
        axles = (fx - .85, bx + .95); R = .36
    else:  # box truck
        B("cab", (2.0, W_, 1.9), (fx - 1.0, 0, 1.35), p, bevel=.2, seg=4)
        B("cab_glass", (.06, W_ - .3, .8), (fx + .01, 0, 1.8), m["glass"], rot=(0, rad(-8), 0), bevel=.05)
        for s in (-1, 1):
            B("cab_door_glass", (.75, .03, .6), (fx - .75, s * (W_ / 2 + .003), 1.85), m["glass"], bevel=.05)
        B("chassis", (L_, 1.1, .25), (0, 0, .55), m["dark"], bevel=.03)
        B("box", (L_ - 2.15, W_ + .1, 2.5), (bx + (L_ - 2.15) / 2, 0, 1.95), m["white"], bevel=.06, seg=2)
        for s in (-1, 1):
            B("box_trim", (L_ - 2.1, .05, .16), (bx + (L_ - 2.15) / 2, s * (W_ / 2 + .08), 3.1), m[stripe or "teal"], bevel=.01)
            B("box_skirt", (L_ - 2.1, .05, .18), (bx + (L_ - 2.15) / 2, s * (W_ / 2 + .08), .8), m[stripe or "teal"], bevel=.01)
        bl = L_ - 2.15; bcx = bx + bl / 2
        for i in range(int(bl / .55)):   # vertical ribs of the aluminium box
            for s in (-1, 1):
                B("box_rib", (.05, .03, 2.3), (bx + .3 + i * .55, s * (W_ / 2 + .07), 1.95), m["steel"], bevel=0)
        B("rear_door", (.04, W_ - .1, 2.3), (bx - .02, 0, 1.92), m["steel"], bevel=.02)
        for i in range(7):
            B("rear_door_line", (.05, W_ - .12, .02), (bx - .03, 0, .9 + i * .3), m["grey"], bevel=0)
        B("cab_visor", (.35, W_ - .1, .08), (fx + .1, 0, 2.3), m["dark"], bevel=.02)
        B("cab_deflector", (.9, W_ - .2, .5), (fx - 1.1, 0, 2.5), p, rot=(0, rad(-18), 0), bevel=.08, seg=2)
        for s in (-1, 1):
            B("cab_doorline", (.03, .03, 1.4), (fx - 1.55, s * (W_ / 2 + .005), 1.35), m["dark"])
            B("cab_step", (.45, .25, .06), (fx - 1.0, s * (W_ / 2 + .05), .55), m["steel"], bevel=.01)
            B("fuel_tank", (.9, .3, .4), (bx + 2.8, s * (W_ / 2 - .3), .62), m["chrome"], bevel=.1, seg=3)
        axles = (fx - 1.0, bx + 1.2); R = .46
    for s in (-1, 1):
        for ax in axles:
            Cy("arch", R + .1, .04, (ax, s * (W_ / 2 + .004), R + .02), m["dark"], rot=(rad(90), 0, 0), verts=20)
            objs.append(wheel(c, (ax, s * (W_ / 2 - .13), R + .02), R=R, w=.26, axis='Y'))
        B("headlight", (.05, .3, .14), (fx + .01, s * (W_ / 2 - .3), .78 if kind != "box" else .9), m["lamp"], bevel=.03)
        B("taillight", (.05, .16, .3), (bx - .01, s * (W_ / 2 - .14), .9 if kind != "box" else 1.0), m["tail"], bevel=.03)
        B("mirror", (.06, .14, .16), (fx - (1.0 if kind != "box" else .2), s * (W_ / 2 + .1), 1.4 if kind != "box" else 2.1), m["dark"], bevel=.02)
    B("bumper_f", (.14, W_ + .02, .2), (fx + .04, 0, .45), m["dark"], bevel=.05)
    B("bumper_r", (.14, W_ + .02, .2), (bx - .04, 0, .45), m["dark"], bevel=.05)
    B("grille", (.04, .9, .22), (fx + .02, 0, .7 if kind != "box" else .85), m["dark"], bevel=.02)
    if stripe and kind != "box":
        B("stripe", (L_ - .3, W_ + .02, .12), (0, 0, .82), m[stripe], bevel=.03)
    plate = B("plate", (.03, .5, .14), (bx - .1, 0, .62), m["paper"])
    Mw = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(heading, 4, 'Z')
    objs = [o for o in c.objects if o not in before]   # wheels add rims and hubs too
    for o in objs:
        o.matrix_world = Mw @ o.matrix_world
    return objs

def place(objs, x=0, y=0, rot=0.0):
    Mw = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(rot, 4, 'Z')
    for o in objs: o.matrix_world = Mw @ o.matrix_world
    return objs

def grab(c, fn, *a, **kw):
    """Run a prop builder and return the objects it added to c."""
    before = set(c.objects); fn(c, *a, **kw); return [o for o in c.objects if o not in before]

def cone(c, x, y, h=.7):
    m = mats()
    k.box("cone_base", (.42, .42, .05), (x, y, .155), m["dark"], bevel=.02, c=c)
    k.cyl("cone", .17, h, (x, y, .13 + h / 2), m["orange"], r2=.03, verts=16, c=c)
    k.cyl("cone_band", .12, .1, (x, y, .13 + h * .55), m["white"], r2=.095, verts=16, c=c)

def barrier(c, x, y, rot=0.0, w=1.6):
    m = mats(); objs = []
    for s in (-1, 1):
        objs.append(k.box("bar_leg", (.08, .5, .05), (s * w / 2, 0, .16), m["dark"], c=c))
        objs.append(k.box("bar_post", (.05, .05, 1.0), (s * w / 2, 0, .65), m["white"], c=c))
    for z in (.65, 1.0):
        objs.append(k.box("bar_board", (w, .04, .22), (0, 0, z), m["hazardR"], bevel=.01, c=c))
    objs.append(k.cyl("bar_lamp", .07, .1, (w / 2 - .05, 0, 1.2), m["amber"], rot=(rad(90), 0, 0), verts=12, c=c))
    return place(objs, x, y, rot)

def balloon(c, loc, col, r=.22, string=1.2):
    m = mats(); x, y, z = loc
    k.ball("balloon", r, (x, y, z), m[col], sub=3, scale=(1, 1, 1.18), c=c)
    k.cyl("knot", .03, .05, (x, y, z - r * 1.18), m[col], r2=.0, verts=8, c=c)
    k.cyl("string", .006, string, (x, y, z - r * 1.18 - string / 2), m["white"], verts=4, c=c)

def bunting(c, a, b, cols=("green", "yellow", "blue", "white"), sag=.35, n=12):
    m = mats(); a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, i / n) - Vector((0, 0, sag * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]
    for i in range(n):
        k.tube("rope", pts[i], pts[i + 1], .008, m["white"], verts=4, c=c)
        mid = (pts[i] + pts[i + 1]) / 2; d = (pts[i + 1] - pts[i])
        f = k.cyl("flag", .16, .01, mid - Vector((0, 0, .14)), m[cols[i % len(cols)]], verts=3, c=c)
        f.rotation_euler = (rad(90), 0, math.atan2(d.y, d.x)); f.scale = (1, 1.3, 1)

def pole(c, x, y, h=4.5, col="steel"):
    k.cyl("pole", .07, h, (x, y, .13 + h / 2), mats()[col], verts=12, c=c)

# ================================================================== events
@event
def QuintoDiaUtil(c):
    """ATM kiosk with a queue on the sidewalk next to the door."""
    diorama(c); m = mats(); x, y = 3.2, 3.9
    k.box("atm_plinth", (1.3, .9, .12), (x, y, .19), m["concrete"], bevel=.02, c=c)
    k.box("atm_body", (1.1, .75, 2.05), (x, y, 1.27), m["navy"], bevel=.06, seg=3, c=c)
    k.box("atm_face", (.95, .06, 1.25), (x, y - .38, 1.25), m["steel"], bevel=.03, c=c)
    k.box("atm_hood", (1.12, .45, .12), (x, y - .55, 1.95), m["navy"], rot=(rad(-12), 0, 0), bevel=.03, c=c)
    k.box("atm_screen", (.5, .03, .36), (x, y - .42, 1.55), m["screen"], rot=(rad(-10), 0, 0), bevel=.01, c=c)
    k.box("atm_shelf", (.8, .3, .05), (x, y - .55, 1.05), m["steel"], bevel=.01, c=c)
    for r in range(4):
        for col in range(3):
            k.box("key", (.06, .05, .045), (x - .12 + col * .075, y - .58, 1.09 + r * 0), m["dark" if r else "green"], rot=(0, 0, 0), bevel=.005, c=c).location.y -= r * .065
    k.box("card_slot", (.16, .03, .05), (x + .28, y - .42, 1.3), m["ledG"], bevel=.005, c=c)
    k.box("cash_slot", (.32, .03, .04), (x - .1, y - .42, 1.18), m["dark"], bevel=.005, c=c)
    k.box("atm_sign", (1.15, .12, .42), (x, y - .1, 2.5), m["yellow"], bevel=.04, c=c)
    label(c, "24 HORAS", .2, (x, y - .17, 2.5), m["navy"])
    for s in (-1, 1):
        k.box("privacy", (.04, .4, 1.3), (x + s * .5, y - .55, 1.3), m["steel"], bevel=.01, c=c)
    # queue line: stanchions with a red belt
    pts = [(x - .9, y - .9), (x - .9, y - 2.4), (x - .9, y - 3.9)]
    for i, (px, py) in enumerate(pts + [(x + .6, y - 2.4), (x + .6, y - 3.9)]):
        k.cyl("stanchion_base", .16, .03, (px, py, .145), m["chrome"], verts=16, c=c)
        k.cyl("stanchion", .025, .95, (px, py, .6), m["chrome"], verts=10, c=c)
        k.ball("stanchion_top", .04, (px, py, 1.08), m["chrome"], sub=2, c=c)
    for a, b in [((x - .9, y - .9), (x - .9, y - 2.4)), ((x - .9, y - 2.4), (x - .9, y - 3.9)), ((x + .6, y - 2.4), (x + .6, y - 3.9))]:
        k.box("belt", (.02, abs(b[1] - a[1]), .05), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 1.0), m["red"], bevel=0, c=c)
    for i, who in enumerate(["Customer_07", "Customer_06", "Customer_09", "Customer_08"]):
        actor(c, who, (x - .15, y - 1.0 - i * .85), rad(180))

@event
def FeiraDeRua(c):
    """Street market: striped stalls on the closed side street, cones at the ends."""
    diorama(c); m = mats()
    def stall(x, y, canvas, goods):
        w, d = 3.0, 1.6
        for sx in (-1, 1):
            for sy in (-1, 1):
                k.cyl("stall_pole", .035, 2.4, (x + sx * w / 2, y + sy * d / 2, 1.2), m["steel"], verts=8, c=c)
        roof = k.box("stall_roof", (w + .3, d + .4, .05), (x, y, 2.45), m[canvas], rot=(rad(8), 0, 0), bevel=.01, c=c)
        k.box("stall_valance", (w + .3, .04, .3), (x, y - d / 2 - .2, 2.25), m[canvas], bevel=.01, c=c)
        k.box("stall_table", (w, d - .2, .06), (x, y, .85), m["wood"], bevel=.01, c=c)
        k.box("stall_cloth", (w + .05, .04, .5), (x, y - (d - .2) / 2, .62), m["white"], bevel=.005, c=c)
        for i in range(4):
            cx = x - w / 2 + .4 + i * .73
            k.crate("crate", (cx, y - .2, .88), w=.6, d=.42, h=.22, m=m["wood"], c=c)
            fill = goods[i % len(goods)]
            k.produce_fill("fruit", (cx, y - .2, .88), .52, .34, .2, m[fill], kind='ball', r=.05, c=c, seed=i)
        k.box("price_board", (.5, .03, .32), (x + w / 2 - .4, y - d / 2 - .02, 1.6), m["dark"], bevel=.01, c=c)
        label(c, "R$ 5", .12, (x + w / 2 - .4, y - d / 2 - .04, 1.6), m["white"])
        k.cyl("scale_post", .015, .3, (x - w / 2 + .3, y - d / 2 + .1, 2.1), m["steel"], verts=6, c=c)
        k.cyl("scale_pan", .14, .03, (x - w / 2 + .3, y - d / 2 + .1, 1.92), m["chrome"], verts=16, c=c)
    stall(-3.4, -3.5, "canvasR", ["red", "orange", "lime"])
    stall(.4, -3.5, "canvasB", ["yellow", "green", "red"])
    stall(4.2, -3.5, "canvasG", ["orange", "lime", "purple"])
    for cx in (-6.4, 6.6):
        for cy in (-2.4, -3.6, -4.8): cone(c, cx, cy)
    k.box("banner", (3.0, .04, .5), (.4, -1.8, 3.0), m["yellow"], bevel=.01, c=c)
    label(c, "FEIRA LIVRE", .3, (.4, -1.83, 3.0), m["red"])
    for bx in (-1.1, 1.9):
        pole(c, bx, -1.8, 3.1, "wood")
    for i, (px, py, who, r) in enumerate([(-3.0, -1.9, "Customer_06", 0), (.9, -2.0, "Customer_08", 10), (3.6, -1.9, "Customer_07", -10), (-1.4, -.6, "Customer_09", 200)]):
        actor(c, who, (px, py, .13), rad(r))

@event
def OndaDeCalor(c):
    """Street thermometer at 38 degrees, ice-cream cart with a parasol, sun umbrellas."""
    diorama(c); m = mats(); x, y = -3.5, -.4
    k.cyl("thermo_pole", .08, 3.4, (x, y, 1.83), m["steel"], verts=12, c=c)
    k.box("thermo_case", (1.5, .25, .9), (x, y, 3.6), m["dark"], bevel=.06, seg=3, c=c)
    k.box("thermo_face", (1.32, .03, .7), (x, y - .13, 3.6), m["ink"], bevel=.01, c=c)
    label(c, "38°C", .42, (x, y - .16, 3.6), m["ledR"], extrude=.01)
    k.box("thermo_brand", (1.5, .26, .14), (x, y, 3.08), m["teal"], bevel=.02, c=c)
    label(c, "14:35", .1, (x, y - .14, 3.08), m["white"])
    # ice-cream cart
    cx, cy = .6, .4
    k.box("cart_box", (1.3, .7, .75), (cx, cy, .85), m["white"], bevel=.06, seg=3, c=c)
    k.box("cart_band", (1.32, .72, .16), (cx, cy, .62), m["pink"], bevel=.03, c=c)
    k.box("cart_lid", (1.32, .72, .06), (cx, cy, 1.25), m["sky"], bevel=.02, c=c)
    label(c, "SORVETE", .14, (cx, cy - .37, .92), m["pink"])
    for s in (-1, 1):
        wheel(c, (cx + .45, cy + s * .4, .4), R=.25, w=.08, axis='Y')
    k.cyl("cart_handle", .02, .9, (cx - .8, cy, 1.05), m["chrome"], rot=(rad(90), 0, 0), verts=8, c=c)
    k.umbrella("parasol", (cx, cy, 1.28), h=1.6, R=.95, m_a=m["yellow"], m_b=m["pink"], m_pole=m["white"], c=c)
    for i, col in enumerate(["pink", "yellow", "lime"]):   # popsicles on the lid
        k.box("pop", (.08, .03, .16), (cx - .3 + i * .15, cy - .2, 1.38), m[col], bevel=.02, c=c)
    k.umbrella("sun_umbrella", (3.6, 2.2, .13), h=2.3, R=1.2, m_a=m["orange"], m_b=m["white"], m_pole=m["steel"], c=c)
    k.box("bench", (1.8, .5, .08), (3.6, 2.2, .55), m["wood"], bevel=.02, c=c)
    for i, (px, py, who, r) in enumerate([(1.6, -.4, "Customer_09", 120), (-.4, -.2, "Customer_06", 240), (3.1, 1.6, "Customer_08", 200)]):
        actor(c, who, (px, py), rad(r))

@event
def SorteioNaPorta(c):
    """Prize wheel and a balloon arch at the entrance."""
    diorama(c); m = mats(); x, y = 2.2, 3.6
    for s in (-1, 1):
        k.box("wheel_leg", (.08, .7, 1.9), (x + s * .45, y, 1.05), m["wood"], rot=(rad(0), 0, 0), bevel=.01, c=c)
    k.box("wheel_foot", (1.1, .8, .08), (x, y, .17), m["wood"], bevel=.01, c=c)
    cols = ["red", "yellow", "blue", "green", "orange", "purple", "pink", "teal"]
    cz = 1.75
    for i in range(8):
        a0 = i * math.tau / 8
        bm = bmesh.new(); r = .78
        v0 = bm.verts.new((0, 0, 0)); seg = [bm.verts.new((math.cos(a0 + t * math.tau / 8 / 6) * r, 0, math.sin(a0 + t * math.tau / 8 / 6) * r)) for t in range(7)]
        for t in range(6): bm.faces.new((v0, seg[t], seg[t + 1]))
        me = bpy.data.meshes.new("slice"); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new("wheel_slice", me); c.objects.link(o); o.location = (x, y - .12, cz)
        sol = o.modifiers.new("t", 'SOLIDIFY'); sol.thickness = .06
        o.data.materials.append(m[cols[i]])
    bpy.ops.mesh.primitive_torus_add(major_radius=.8, minor_radius=.05, major_segments=40, minor_segments=8, location=(x, y - .12, cz), rotation=(rad(90), 0, 0))
    rim = bpy.context.active_object; rim.name = "wheel_rim"; k.link(rim, c); k.finish(rim, m["gold"], bevel=0)
    k.cyl("wheel_hub", .12, .12, (x, y - .2, cz), m["white"], rot=(rad(90), 0, 0), verts=16, c=c)
    for i in range(16):
        a = i * math.tau / 16
        k.ball("peg", .03, (x + math.cos(a) * .8, y - .2, cz + math.sin(a) * .8), m["white"], sub=1, c=c)
    k.cyl("pointer", .1, .25, (x, y - .2, cz + .95), m["red"], r2=0, rot=(rad(180), 0, 0), verts=3, c=c)
    k.box("prize_sign", (1.2, .05, .32), (x, y - .05, 2.85), m["red"], bevel=.02, c=c)
    label(c, "GIRE E GANHE", .14, (x, y - .09, 2.85), m["yellow"])
    # balloon arch over the door
    for i in range(23):
        t = i / 22; a = math.pi * t
        px = -1.4 * math.cos(a); pz = .2 + 2.85 * math.sin(a)
        k.ball("arch_balloon", .2, (px, 5.1, pz + .2), m[["red", "yellow", "white", "blue"][i % 4]], sub=2, scale=(1, .9, 1.1), c=c)
    for i, (gx, gc) in enumerate([(1.0, "red"), (1.35, "blue"), (3.3, "yellow")]):
        k.box("gift", (.35, .35, .3), (gx, y - .3 + (i % 2) * .2, .28), m[gc], bevel=.02, c=c)
        k.box("ribbon", (.37, .06, .31), (gx, y - .3 + (i % 2) * .2, .28), m["gold"], bevel=0, c=c)
    actor(c, "Customer_07", (2.2, 2.4), rad(10)); actor(c, "Customer_08", (1.2, 2.1), rad(-20))

@event
def CaminhaoDeOfertas(c):
    """Supplier box truck at the curb with an OFERTA banner, pallets being unloaded."""
    diorama(c); m = mats()
    vehicle(c, .5, -2.95, "box", "orange", stripe="red")
    k.box("offer_banner", (3.8, .03, 1.2), (-.7, -4.29, 2.0), m["yellow"], bevel=.01, c=c)
    label(c, "OFERTA", .5, (-.7, -4.32, 2.2), m["red"])
    label(c, "-25% DIRETO DO FORNECEDOR", .16, (-.7, -4.32, 1.65), m["navy"])
    for i, (px, py) in enumerate(((-4.6, -.2), (-4.6, 1.2))):
        k.box("pallet", (1.2, 1.0, .14), (px, py, .2), m["wood"], bevel=.01, c=c)
        for j in range(4):
            k.box("carton", (.55, .45, .38), (px - .29 + (j % 2) * .58, py - .23 + (j // 2) * .47, .47), m["brown"] if (i + j) % 2 else m["gold"], bevel=.02, c=c)
        k.box("carton_top", (.55, .45, .38), (px, py, .86), m["gold"], bevel=.02, c=c)
    k.box("jack_fork", (1.1, .6, .06), (-3.0, .3, .18), m["red"], bevel=.01, c=c)
    k.box("jack_body", (.3, .5, .4), (-2.4, .3, .4), m["red"], bevel=.03, c=c)
    k.cyl("jack_handle", .025, 1.2, (-2.1, .3, .9), m["dark"], rot=(0, rad(-25), 0), verts=8, c=c)
    actor(c, "Customer_09", (-3.4, -.8), rad(-30)); actor(c, "Customer_06", (-2.2, 1.0), rad(200))

@event
def DiaDeJogo(c):
    """Brazil match day: green-yellow bunting across the street, big screen on a truss, flags."""
    diorama(c); m = mats()
    for px in (-6.2, 6.2):
        pole(c, px, -1.0, 4.6); pole(c, px, -6.0, 4.6)
    for k_ in range(3):
        bunting(c, (-6.2, -1.0 - k_ * 2.5, 4.4), (6.2, -1.0 - k_ * 2.5 - 2.5 * 0, 4.4), cols=("green", "yellow", "blue", "white"), sag=.5, n=16) if False else None
    bunting(c, (-6.2, -1.0, 4.5), (6.2, -6.0, 4.5), sag=.6, n=18)
    bunting(c, (-6.2, -6.0, 4.5), (6.2, -1.0, 4.5), sag=.6, n=18, cols=("yellow", "green"))
    bunting(c, (-6.2, -1.0, 4.4), (6.2, -1.0, 4.4), sag=.4, n=18, cols=("green", "yellow", "blue"))
    # big screen on a truss on the sidewalk
    x, y = -3.4, 2.8
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box("truss_leg", (.12, .12, 3.6), (x + sx * 1.6, y + sy * .25, 1.93), m["steel"], bevel=.01, c=c)
    for z in (.6, 1.6, 2.6):
        k.box("truss_x", (3.3, .06, .06), (x, y - .25, z), m["steel"], c=c)
    k.box("screen_frame", (3.6, .2, 2.1), (x, y - .3, 3.0), m["dark"], bevel=.04, c=c)
    k.box("screen_field", (3.3, .03, 1.85), (x, y - .41, 3.0), k.emissive("EV_Field", (.15, .75, .25, 1), 1.6), bevel=0, c=c)
    for zz in (2.2, 3.0, 3.8):
        pass
    k.box("field_mid", (.03, .02, 1.8), (x, y - .43, 3.0), m["lamp"], c=c)
    bpy.ops.mesh.primitive_torus_add(major_radius=.3, minor_radius=.015, location=(x, y - .43, 3.0), rotation=(rad(90), 0, 0))
    t = bpy.context.active_object; k.link(t, c); k.finish(t, m["lamp"], bevel=0)
    k.box("score", (1.2, .03, .25), (x, y - .44, 3.75), m["dark"], c=c)
    label(c, "BRA 1 x 0", .16, (x, y - .46, 3.75), m["yellow"])
    for i, fx in enumerate((-.4, 1.6, 3.6)):
        k.cyl("flag_pole", .025, 2.4, (fx, -.9, 1.33), m["white"], verts=8, c=c)
        k.box("flag", (.9, .02, .6), (fx + .47, -.9, 2.2), m["green"], bevel=.005, c=c)
        d = k.cyl("flag_diamond", .34, .03, (fx + .47, -.92, 2.2), m["yellow"], rot=(rad(90), 0, 0), verts=4, c=c); d.scale = (1.15, .75, 1)
        k.cyl("flag_globe", .14, .04, (fx + .47, -.94, 2.2), m["blue"], rot=(rad(90), 0, 0), verts=20, c=c)
    for i, (px, py, who, r) in enumerate([(-4.2, 1.2, "Customer_07", 180), (-3.2, 1.0, "Customer_09", 170), (-2.2, 1.3, "Customer_06", 190), (1.8, .2, "Customer_08", 140)]):
        actor(c, who, (px, py), rad(r))

@event
def CafeComEquipe(c):
    """Staff coffee break by the back door: folding table, thermos, cups, pao de queijo, chairs."""
    diorama(c, road=False, depth=8); m = mats(); x, y = .8, 1.0
    k.box("back_door", (1.1, .08, 2.2), (-2.4, 3.2, 1.23), m["steel"], bevel=.02, c=c)
    label(c, "SÓ FUNCIONÁRIOS", .12, (-2.4, 3.14, 1.9), m["red"])
    k.box("table_top", (1.6, .9, .05), (x, y, .9), m["white"], bevel=.01, c=c)
    k.box("tablecloth", (1.65, .95, .02), (x, y, .93), k.stripes("EV_Checker", C["red"], C["white"], .12), bevel=0, c=c)
    for sx in (-1, 1):
        k.box("table_leg", (.04, .8, .8), (x + sx * .7, y, .5), m["steel"], rot=(0, 0, 0), c=c)
    k.cyl("thermos", .1, .42, (x - .5, y + .15, 1.15), m["red"], verts=16, bevel=.01, c=c)
    k.cyl("thermos_cap", .07, .1, (x - .5, y + .15, 1.41), m["dark"], verts=16, c=c)
    k.cyl("plate", .22, .02, (x + .3, y, .95), m["white"], verts=24, c=c)
    for i in range(9):
        a = i * 2.4; r = .05 + .11 * (i % 3) / 2
        k.ball("pao_de_queijo", .05, (x + .3 + math.cos(a) * r, y + math.sin(a) * r, .99), m["gold"], sub=2, scale=(1, 1, .8), c=c)
    for i, (cx, cy) in enumerate(((x - .1, y - .25), (x + .6, y + .25), (x - .2, y + .3), (x + .65, y - .3))):
        k.cyl("cup", .045, .1, (cx, cy, .99), m["white"], r2=.04, verts=12, c=c)
        k.cyl("coffee", .04, .005, (cx, cy, 1.04), m["brown"], verts=12, c=c)
    for (px, py, r) in ((x - 1.1, y, 90), (x + 1.1, y, -90), (x, y + .9, 180)):
        k.box("chair_seat", (.45, .45, .05), (px, py, .5), m["teal"], bevel=.01, c=c)
        k.box("chair_back", (.45, .05, .45), (px - .2 * math.sin(rad(r)), py + .2 * math.cos(rad(r)) * 0 + (.2 if r == 180 else 0), .75), m["teal"], rot=(0, 0, rad(r)), bevel=.01, c=c)
    k.box("crates_stack", (.6, .4, .9), (2.9, 2.6, .58), m["wood"], bevel=.02, c=c)
    k.box("coffee_sign", (.7, .04, .5), (.8, 3.15, 1.8), m["dark"], bevel=.01, c=c)
    label(c, "CAFÉ ☕", .12, (.8, 3.12, 1.8), m["white"])
    for (px, py, who, r) in ((x - 1.1, y - .5, "Customer_07", 0), (x + 1.2, y - .5, "Customer_09", 30), (x + .1, y - 1.0, "Customer_06", -10)):
        actor(c, who, (px, py), rad(r))

@event
def Viralizou(c):
    """Influencer filming in front of the market: ring light, phone on a tripod, neon heart, selfie crowd."""
    diorama(c); m = mats(); x, y = 2.6, 2.6
    for i in range(3):
        a = rad(120 * i)
        k.tube("tripod_leg", (x + math.cos(a) * .35, y - 1.6 + math.sin(a) * .35, .13), (x, y - 1.6, 1.3), .015, m["dark"], c=c)
    k.cyl("tripod_mast", .02, .45, (x, y - 1.6, 1.52), m["dark"], verts=8, c=c)
    bpy.ops.mesh.primitive_torus_add(major_radius=.32, minor_radius=.035, location=(x, y - 1.6, 1.85), rotation=(rad(90), 0, 0))
    rl = bpy.context.active_object; k.link(rl, c); k.finish(rl, m["lamp"], bevel=0)
    k.box("phone", (.09, .015, .17), (x, y - 1.6, 1.85), m["dark"], bevel=.01, c=c)
    k.box("phone_screen", (.08, .005, .15), (x, y - 1.61, 1.85), m["screen"], c=c)
    k.box("backdrop", (1.8, .05, 2.0), (x, y + .9, 1.13), m["pink"], bevel=.02, c=c)
    hp = [(math.sin(t) ** 3 * .3, 0, (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 16 * .3) for t in [i * math.tau / 40 for i in range(40)]]
    for i in range(40):
        a, b = Vector(hp[i]), Vector(hp[(i + 1) % 40])
        k.tube("neon", a + Vector((x, y + .85, 1.55)), b + Vector((x, y + .85, 1.55)), .02, m["ledR"], verts=6, c=c)
    label(c, "#VIRALIZOU", .14, (x, y + .85, .85), m["white"])
    k.box("light_stand", (.05, .05, 2.0), (x + 1.3, y - .2, 1.13), m["dark"], c=c)
    k.box("softbox", (.5, .3, .5), (x + 1.3, y - .25, 2.1), m["white"], rot=(rad(-20), 0, rad(-30)), bevel=.03, c=c)
    actor(c, "Customer_06", (x, y + .2), rad(0))
    for i, (px, py, who, r) in enumerate([(x - 1.6, y - 1.0, "Customer_08", 60), (x - 2.4, y - .4, "Customer_07", 80), (x + 1.8, y - 1.5, "Customer_09", -40)]):
        actor(c, who, (px, py), rad(r))
    for i in range(5):
        k.box("heart_icon", (.18, .04, .16), (x - .6 + i * .3, y - .5, 2.5 + (i % 2) * .4), m["red"], rot=(0, rad(45), 0), bevel=.06, seg=3, c=c)

@event
def RuaEmObras(c):
    """Street works: dug pit with rubble, barriers and cones, mini backhoe, DESVIO sign, work light."""
    diorama(c); m = mats(); x, y = .2, -3.4
    k.box("pit_edge", (3.6, 2.0, .04), (x, y, .005), k.mat("EV_Cut", (.30, .30, .31, 1), rough=.9, var=.2, scale=20), bevel=.02, c=c)
    k.box("pit", (3.2, 1.6, .05), (x, y, .02), k.mat("EV_Dirt", (.42, .30, .18, 1), rough=.95, var=.25, scale=8, bump=.5), bevel=0, c=c)
    rnd = random.Random(3)
    for i in range(14):
        k.ball("rubble", rnd.uniform(.08, .18), (x + rnd.uniform(-1.4, 1.4), y + rnd.uniform(-.7, .7), .06), m["concrete"], sub=1, scale=(1, 1, .6), c=c)
    k.box("pipe", (3.0, .3, .3), (x, y + .3, .1), m["orange"], bevel=.14, seg=4, c=c)
    for (bx_, by_, r) in ((x - 2.2, y, 90), (x + 2.2, y, 90), (x, y - 1.3, 0), (x, y + 1.3, 0)):
        barrier(c, bx_, by_, rad(r), w=1.8 if r == 0 else 1.4)
    for cx_ in (-4.5, -3.8, -3.1):
        cone(c, cx_, -2.4 - (cx_ + 4.5) * .8)
    # mini backhoe
    bx2, by2 = 3.9, -4.0
    k.box("bh_body", (2.0, 1.3, .7), (bx2, by2, .85), m["yellow"], bevel=.08, seg=3, c=c)
    k.box("bh_cab", (1.0, 1.1, 1.0), (bx2 - .2, by2, 1.7), m["yellow"], bevel=.06, seg=2, c=c)
    for s in (-1, 1):
        k.box("bh_glass", (.85, .03, .75), (bx2 - .2, by2 + s * .56, 1.72), m["glass"], bevel=.02, c=c)
    k.box("bh_roof", (1.15, 1.25, .08), (bx2 - .2, by2, 2.25), m["dark"], bevel=.02, c=c)
    for s in (-1, 1):
        wheel(c, (bx2 + .7, by2 + s * .7, .45), R=.42, w=.3, axis='Y')
        wheel(c, (bx2 - .7, by2 + s * .7, .55), R=.52, w=.36, axis='Y')
    k.box("bh_loader", (.3, 1.6, .5), (bx2 + 1.35, by2, .45), m["yellow"], bevel=.03, c=c)
    k.box("bh_boom", (1.6, .2, .22), (bx2 - 1.5, by2, 1.6), m["yellow"], rot=(0, rad(-35), 0), bevel=.04, c=c)
    k.box("bh_arm", (1.2, .18, .18), (bx2 - 2.4, by2, 1.4), m["yellow"], rot=(0, rad(60), 0), bevel=.04, c=c)
    k.box("bh_bucket", (.4, .5, .35), (bx2 - 2.7, by2, .7), m["dark"], bevel=.04, c=c)
    k.cyl("bh_beacon", .08, .12, (bx2 - .2, by2, 2.36), m["amber"], verts=12, c=c)
    # DESVIO sign and a work light
    k.box("desvio_post", (.06, .06, 1.6), (-5.4, -1.4, .9), m["dark"], c=c)
    k.box("desvio", (1.1, .04, .55), (-5.4, -1.43, 1.6), m["orange"], bevel=.02, c=c)
    label(c, "DESVIO →", .17, (-5.4, -1.46, 1.6), m["ink"])
    k.box("light_tower", (.1, .1, 2.6), (2.4, -1.3, 1.4), m["steel"], c=c)
    for s in (-1, 1):
        k.box("work_lamp", (.35, .12, .28), (2.4 + s * .22, -1.38, 2.7), m["lamp"], bevel=.02, c=c)
    actor(c, "Customer_07", (x - .8, y + .2), rad(30)); actor(c, "Customer_09", (x + 1.0, y - .2), rad(-60))

@event
def Engarrafamento(c):
    """Traffic jam: stopped cars nose to tail and a portable LENTIDAO message board."""
    diorama(c, w=18); m = mats()
    cols = ["red", "blue", "white", "yellow", "teal"]
    for i, (vx, kind) in enumerate(((-6.5, "car"), (-2.0, "van"), (2.6, "car"), (7.0, "car"))):
        vehicle(c, vx, -2.75, kind, cols[i])
    for i, vx in enumerate((-4.5, .5, 5.0)):
        vehicle(c, vx, -4.75, "car", cols[(i + 2) % 5], heading=math.pi)
    tx, ty = 5.6, -.4
    k.box("vms_trailer", (1.4, 1.0, .35), (tx, ty, .55), m["orange"], bevel=.04, c=c)
    for s in (-1, 1): wheel(c, (tx, ty + s * .55, .35), R=.25, w=.14, axis='Y')
    k.box("vms_mast", (.12, .12, 1.8), (tx, ty, 1.6), m["dark"], c=c)
    k.box("vms_board", (2.0, .2, 1.1), (tx, ty, 2.9), m["ink"], bevel=.04, c=c)
    label(c, "LENTIDÃO", .3, (tx, ty - .11, 3.05), m["amber"])
    label(c, "+15 MIN", .22, (tx, ty - .11, 2.65), m["amber"])
    k.box("vms_solar", (1.0, .7, .04), (tx, ty, 3.6), m["navy"], rot=(rad(-30), 0, 0), bevel=.01, c=c)
    for i in range(3):
        k.box("horn_icon", (.3, .04, .2), (-6.0 + i * 4.6, -2.75, 2.4), m["yellow"], bevel=.08, seg=3, c=c)

@event
def FimDoMes(c):
    """End of the month: the neighbour shop's sale banner and A-frames, shoppers comparing prices."""
    diorama(c); m = mats()
    k.box("neighbour", (5.0, .3, 3.6), (-4.6, 5.0, 1.8), m["sky"], bevel=.02, c=c)
    k.box("neighbour_banner", (4.0, .06, 1.0), (-4.6, 4.8, 2.2), m["red"], bevel=.01, c=c)
    label(c, "LIQUIDA TUDO", .32, (-4.6, 4.75, 2.35), m["yellow"])
    label(c, "ATÉ -50%", .24, (-4.6, 4.75, 1.95), m["white"])
    for (ax, ay) in ((-3.2, 2.6), (-5.8, 2.2)):
        for s in (-1, 1):
            k.box("aframe", (.7, .04, 1.0), (ax, ay + s * .18, .65), m["yellow"], rot=(rad(12 * s), 0, 0), bevel=.01, c=c)
        label(c, "-50%", .2, (ax, ay - .23, .7), m["red"], rot=(rad(78), 0, 0))
    for i, (px, py, who, r) in enumerate([(-3.6, 1.6, "Customer_08", 170), (-4.4, 1.2, "Customer_06", 200), (1.0, 2.4, "Customer_07", 120)]):
        actor(c, who, (px, py), rad(r))
    k.box("price_tag", (.25, .02, .15), (1.0, 2.0, 1.6), m["paper"], bevel=.005, c=c)

@event
def MaquininhaForaDoAr(c):
    """Card machines down: telecom technician up a ladder at the utility pole, SO DINHEIRO sign on the door."""
    diorama(c); m = mats(); x, y = -3.8, -.9
    k.cyl("utility_pole", .14, 7.0, (x, y, 3.6), m["concrete"], r2=.1, verts=12, c=c)
    k.box("crossarm", (1.6, .1, .1), (x, y, 6.6), m["wood"], c=c)
    k.box("cto_box", (.45, .25, .6), (x, y - .2, 4.4), m["dark"], bevel=.03, c=c)
    k.box("cto_led", (.05, .02, .05), (x + .12, y - .33, 4.55), m["ledR"], c=c)
    for i in range(3):
        k.tube("cable", (x - 6, y + .2 * i, 6.3 - i * .2), (x + 6, y + .2 * i, 6.2 - i * .2), .015, m["ink"], verts=4, c=c)
    lx, ly = x + .55, y - .5
    for s in (-1, 1):
        k.tube("ladder_rail", (lx + s * .22, ly - .5, .13), (lx + s * .22 - .0, ly + .1, 4.3), .03, m["steel"], verts=6, c=c)
    for i in range(12):
        t = i / 11; zz = .3 + t * 3.9; yy = ly - .5 + t * .6
        k.box("rung", (.44, .03, .03), (lx, yy, zz), m["steel"], c=c)
    k.cyl("cable_reel", .35, .3, (x + 1.8, y - .2, .48), m["wood"], rot=(rad(90), 0, 0), verts=20, c=c)
    k.cyl("cable_core", .2, .32, (x + 1.8, y - .2, .48), m["ink"], rot=(rad(90), 0, 0), verts=16, c=c)
    vehicle(c, x + 1.5, -2.95, "van", "white", stripe="orange")
    actor(c, "Customer_07", (lx, ly + .2, 2.4), rad(180))
    k.box("door_sign", (.6, .02, .4), (.6, 5.3, 1.5), m["yellow"], bevel=.01, c=c)
    label(c, "SÓ DINHEIRO", .08, (.6, 5.28, 1.55), m["red"])
    k.box("door_sign_x", (.3, .02, .06), (.6, 5.28, 1.4), m["red"], rot=(0, rad(45), 0), c=c)

@event
def AltaDoDiesel(c):
    """Diesel price spike: the corner fuel station's price totem with a red up arrow, supplier truck idling."""
    diorama(c); m = mats(); x, y = -4.2, .3
    k.box("totem", (1.3, .4, 4.2), (x, y, 2.23), m["white"], bevel=.06, seg=3, c=c)
    k.box("totem_top", (1.4, .45, .9), (x, y, 3.9), m["blue"], bevel=.06, seg=3, c=c)
    label(c, "POSTO", .26, (x, y - .24, 3.95), m["yellow"])
    for i, (fuel, price, col) in enumerate((("DIESEL", "7,89", "ledR"), ("GASOL.", "6,49", "amber"), ("ETANOL", "4,79", "amber"))):
        zz = 3.0 - i * .65
        k.box("price_row", (1.15, .03, .5), (x, y - .21, zz), m["ink"], bevel=.01, c=c)
        label(c, fuel, .11, (x - .3, y - .23, zz), m["white"])
        label(c, price, .2, (x + .25, y - .23, zz), m[col])
    k.cyl("arrow_up", .2, .3, (x + .85, y - .2, 3.0), m["red"], verts=3, rot=(0, 0, 0), c=c).rotation_euler = (rad(90), 0, rad(-90))
    k.box("arrow_tail", (.12, .04, .3), (x + .85, y - .2, 2.75), m["red"], c=c)
    vehicle(c, 1.8, -2.95, "box", "teal", stripe="yellow")
    k.box("fuel_island", (2.0, 1.0, .2), (-.2, 2.8, .23), m["concrete"], bevel=.02, c=c)
    for px in (-.7, .3):
        k.box("pump", (.5, .4, 1.4), (px, 2.8, 1.0), m["blue"], bevel=.04, c=c)
        k.box("pump_screen", (.3, .02, .2), (px, 2.59, 1.35), m["screen"], c=c)
    k.box("canopy", (4.0, 2.6, .3), (-.2, 2.8, 3.9), m["white"], bevel=.04, c=c)
    k.box("canopy_band", (4.02, 2.62, .12), (-.2, 2.8, 3.8), m["blue"], bevel=.01, c=c)
    for px in (-1.8, 1.4):
        k.box("canopy_post", (.2, .2, 3.6), (px, 2.8, 2.0), m["white"], bevel=.02, c=c)

@event
def QuedaDeEnergia(c):
    """Power cut: sparking transformer on the pole, utility bucket truck, street lamps off."""
    diorama(c); m = mats(); x, y = -2.6, -.9
    k.cyl("utility_pole", .14, 7.5, (x, y, 3.85), m["concrete"], r2=.1, verts=12, c=c)
    k.box("crossarm", (1.8, .1, .1), (x, y, 7.0), m["wood"], c=c)
    for s in (-1, 0, 1):
        k.cyl("insulator", .05, .15, (x + s * .7, y, 7.13), m["white"], verts=8, c=c)
    k.cyl("transformer", .38, .9, (x, y - .45, 5.6), m["grey"], verts=20, bevel=.02, c=c)
    for i in range(4):
        k.box("fin", (.04, .1, .7), (x - .2 + i * .13, y - .82, 5.55), m["grey"], c=c)
    for i in range(6):
        a = i * math.tau / 6
        k.cyl("spark", .06, .5, (x + math.cos(a) * .25, y - .8, 6.2 + math.sin(a) * .25), m["amber"], r2=0, verts=4, rot=(0, rad(90) - a, 0), c=c)
    k.ball("spark_core", .12, (x, y - .8, 6.2), m["lamp"], sub=2, c=c)
    k.ball("smoke", .35, (x + .2, y - .6, 6.9), k.mat("EV_Smoke", (.35, .35, .37, 1), rough=1, var=.2), sub=2, scale=(1.2, 1, .8), c=c)
    vehicle(c, x + 4.4, -2.95, "box", "white", stripe="orange")
    tb = (x + 3.2, -2.95)
    k.box("boom1", (3.0, .25, .25), (tb[0] - 1.2, tb[1] + .3, 4.1), m["orange"], rot=(0, rad(-38), 0), bevel=.03, c=c)
    k.box("basket", (.9, .8, .8), (x + .6, -2.6, 5.6), m["orange"], bevel=.04, c=c)
    actor(c, "Customer_09", (x + .6, -2.6, 5.4), rad(150))
    k.box("dark_lamp", (.4, .2, .1), (3.5, -.9, 4.4), m["dark"], c=c)
    pole(c, 3.5, -.9, 4.3)
    actor(c, "Customer_06", (1.0, .8), rad(200))

@event
def VigilanciaSanitaria(c):
    """Health inspection: white inspection car at the curb, inspector with a clipboard at the door."""
    diorama(c); m = mats()
    vehicle(c, -1.5, -2.75, "car", "white", stripe="green")
    label(c, "VIGILÂNCIA SANITÁRIA", .16, (-1.5, -3.77, .95), m["green"])
    k.box("roof_sign", (.9, .3, .25), (-1.7, -2.75, 1.65), m["green"], bevel=.03, c=c)
    actor(c, "Customer_08", (1.4, 3.6), rad(10))
    k.box("clipboard", (.25, .02, .32), (1.25, 3.3, 1.1), m["wood"], rot=(rad(-30), 0, 0), bevel=.005, c=c)
    k.box("clip_paper", (.22, .01, .26), (1.25, 3.28, 1.1), m["paper"], rot=(rad(-30), 0, 0), c=c)
    k.box("vest", (.38, .25, .45), (1.4, 3.6, 1.25), k.mat("EV_Vest", (.85, .95, .15, 1), rough=.6), bevel=.05, c=c) if False else None
    k.box("inspection_case", (.45, .15, .32), (1.9, 3.5, .3), m["dark"], bevel=.02, c=c)
    k.cyl("thermometer_probe", .015, .3, (1.0, 3.3, 1.2), m["chrome"], verts=6, c=c)

@event
def CarroDeSom(c):
    """Rival's sound car: old van with roof speakers and a SUPER LEVA MAIS banner cruising past."""
    diorama(c); m = mats(); x, y = -.5, -4.75
    vehicle(c, x, y, "van", "purple", stripe="yellow", heading=math.pi)
    k.box("roof_rack", (2.4, 1.6, .08), (x, y, 2.05), m["steel"], c=c)
    for s in (-1, 1):
        for d in (-1, 1):
            k.cyl("horn", .32, .55, (x + d * .65, y + s * .4, 2.35), m["white"], r2=.08, verts=16, rot=(0, rad(90 * d), 0), c=c)
    k.box("van_banner", (3.2, .03, .55), (x, y + 1.02, 1.0), m["yellow"], bevel=.01, c=c)
    k.box("van_banner2", (3.2, .03, .55), (x, y - 1.02, 1.0), m["yellow"], bevel=.01, c=c)
    label(c, "SUPER LEVA MAIS", .2, (x, y - 1.05, 1.05), m["purple"])
    label(c, "TUDO EM OFERTA!", .13, (x, y - 1.05, .85), m["red"])
    for i in range(3):
        k.box("sound_wave", (.05, .5 + i * .25, .05), (x - 1.6 - i * .3, y, 2.4), m["purple"], bevel=.02, c=c)
    for i, (bx_, col) in enumerate(((x + 1.4, "yellow"), (x + 1.7, "purple"))):
        balloon(c, (bx_, y + .2, 2.9), col)

@event
def TurnoPuxado(c):
    """Tired shift: no street prop - inside, staff move slower; preview shows the yawning 'zZ' bubble and empty coffee cups at the counter."""
    diorama(c); m = mats()
    k.box("counter", (2.2, .7, 1.0), (0, 1.0, .63), m["teal"], bevel=.04, c=c)
    k.box("counter_top", (2.3, .8, .06), (0, 1.0, 1.15), m["wood"], bevel=.01, c=c)
    for i in range(4):
        k.cyl("empty_cup", .045, .1, (-.7 + i * .2, .85, 1.23), m["white"], r2=.04, verts=12, c=c)
    actor(c, "Customer_07", (0, 1.8), rad(180))
    for i, (zz, s) in enumerate(((2.3, .22), (2.65, .3))):
        label(c, "z" if i == 0 else "Z", s, (.5 + i * .25, 1.8, zz), m["white"])

# ================================================================== export (one FBX + one baked atlas per prop)
PROP_OUT = os.path.join(REPO, "unity", "CheckoutSimulator", "Assets", "Resources", "EventProps2")

def prop_collection(prop):
    """Source collection for one exportable prop: modelled at the origin, ground at z=0, readable front facing -Y."""
    return clear("EP " + prop)

def export_prop(prop, size=1024, out=PROP_OUT):
    """Joins a copy of "EP <prop>" (modifiers applied), smart-UVs it, bakes the diffuse colour of the procedural
    materials into <prop>_BaseColor.png and writes <prop>.fbx (front turned to Unity +Z). Returns stats."""
    src = [o for o in bpy.data.collections["EP " + prop].all_objects if o.type in ('MESH', 'CURVE', 'FONT')]
    tmp = collection("EP export tmp")
    for o in list(tmp.objects): bpy.data.objects.remove(o, do_unlink=True)
    # NB: copy the EVALUATED meshes (bevel/solidify/displace applied) *before* excluding the source collection -
    # an excluded collection is not evaluated and new_from_object would silently return the un-modified mesh.
    copies = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in src:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        n = bpy.data.objects.new("X_" + o.name, me); n.matrix_world = o.matrix_world.copy(); tmp.objects.link(n); copies.append(n)
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = lc.name not in ("EP export tmp", "Studio")
    bpy.ops.object.select_all(action='DESELECT')
    for n in copies: n.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    origins = {tuple(round(v, 4) for v in n.matrix_world.translation) for n in copies}
    bpy.ops.object.join(); j = bpy.context.active_object; j.name = prop
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if len(origins) > 1:
        # parts with different origins: the prop's pivot is the modelling origin (ground centre / hub / hinge)
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    img_name = prop + "_BaseColor"
    for im in list(bpy.data.images):
        if im.name.startswith(img_name): bpy.data.images.remove(im)
    img = bpy.data.images.new(img_name, size, size)
    added = []
    for m in {m for m in j.data.materials if m}:
        nd = m.node_tree.nodes.new("ShaderNodeTexImage"); nd.image = img; m.node_tree.nodes.active = nd; added.append((m, nd))
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 1
    b = sc.render.bake; b.use_pass_direct = False; b.use_pass_indirect = False; b.use_pass_color = True; b.margin = 4; b.use_clear = True
    bpy.ops.object.bake(type='DIFFUSE')
    for m, nd in added: m.node_tree.nodes.remove(nd)
    os.makedirs(out, exist_ok=True)
    img.filepath_raw = os.path.join(out, img_name + ".png"); img.file_format = 'PNG'; img.save()
    am = bpy.data.materials.get(prop + "_Mat") or bpy.data.materials.new(prop + "_Mat"); am.use_nodes = True
    for nd in list(am.node_tree.nodes):
        if nd.bl_idname == "ShaderNodeTexImage": am.node_tree.nodes.remove(nd)
    tex = am.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = img
    am.node_tree.links.new(tex.outputs["Color"], am.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    j.data.materials.clear(); j.data.materials.append(am)
    for p in j.data.polygons: p.material_index = 0
    sc.render.engine = 'BLENDER_EEVEE'
    path = cp.export_unity([j], prop, folder=out, turn=True)
    j.data.calc_loop_triangles()
    return {"fbx": path, "tris": len(j.data.loop_triangles), "dims": [round(v, 2) for v in j.dimensions], "atlas": img.filepath_raw}
