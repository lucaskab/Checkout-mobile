
# works_kit2.py - construction-works PROPS (hand tools, carried items, site props, half-built stage pieces).
# Same family / pipeline as works_kit.py (metres, Blender Z up, front = +Y, one baked BaseColor atlas + one material per FBX,
# exported with checkout_project.export_unity which turns the roots 180 deg so the front faces Unity +Z).
# The small items are grouped into KIT FBX files: every item is ONE root object (no hierarchy) named exactly as the game
# expects (Tool_Hammer, Prop_Plank, ...), laid side by side along X; the game instantiates an item by name.
#   KIT Works_Tools  : origin = grip point, long axis +Z (Unity +Y), head at the top
#   KIT Works_Carry  : origin = centre of the item
#   KIT Works_Site   : origin = ground centre (DebrisPile / GreenWaste: bottom centre so they can be scaled to 0)
#   Works_TentFrame / Works_StallFrame / Works_Foundation / Works_SignFrame : own FBX, origin ground centre, front +Y
#
#   import sys; sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
#   import works_kit2 as W2; W2.build_all()        # sources under the "Works_v2" collection (one child collection per FBX)
#   W2.pipeline("Works_Tools")                      # export copy + bake atlas + FBX
#   W2.contact_kits(); W2.contact_big()             # ArtSource/Review/works_v2/contact_kits.png / contact_big.png
import bpy, bmesh, math, random, sys, os
sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
sys.path.insert(0, r"C:\Checkout-mobile\scripts\blender")
import era_kit as k, lot_kit as L, works_kit as W, checkout_project as cp
from mathutils import Vector, Matrix, Euler

ROOT_COL = "Works_v2"
EXPORT_COL = "Works_v2 Export"
OUT = W.OUT
REVIEW = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\works_v2"
rad, T, Rx, Rz = W.rad, W.T, W.Rx, W.Rz
PI2 = math.pi / 2

KITS = {
    "Works_Tools": ["Tool_Sledgehammer", "Tool_Hammer", "Tool_Saw", "Tool_Shovel", "Tool_BrushCutter", "Tool_Drill",
                    "Tool_Trowel", "Tool_PaintRoller", "Tool_Wrench", "Tool_Broom", "Tool_Crowbar"],
    "Works_Carry": ["Prop_Plank", "Prop_Brick", "Prop_CementBag", "Prop_Box", "Prop_Pole", "Prop_Tire", "Prop_Bucket",
                    "Prop_PipeBundle", "Prop_Sheet", "Prop_GrassBundle", "Prop_Rubble"],
    "Works_Site": ["Prop_Sawhorse", "Prop_PlankStack", "Prop_BrickPallet", "Prop_CementBags", "Prop_RebarBundle",
                   "Prop_SteelBeams", "Prop_Pallet", "Prop_Ladder", "Prop_Toolbox", "Prop_Cone", "Prop_Barrier",
                   "Prop_Generator", "Prop_WorkLight", "Prop_PortaToilet", "Prop_SitePlate", "Prop_TireStack", "Prop_Drum",
                   "Prop_GlassCrate", "Prop_PaintBuckets", "Prop_RoofTrusses", "Prop_Formwork", "Prop_DebrisPile",
                   "Prop_GreenWaste", "Prop_WheelbarrowFull", "Prop_TentPoles", "Prop_CanvasRoll", "Prop_ScaffoldTower"],
}
BIG = ["Works_TentFrame", "Works_StallFrame", "Works_Foundation", "Works_SignFrame"]
MODELS = list(KITS) + BIG
SIZE = {"Works_Tools": 1024, "Works_Carry": 1024, "Works_Site": 2048, "Works_TentFrame": 1024, "Works_StallFrame": 1024,
        "Works_Foundation": 1024, "Works_SignFrame": 1024}
SPACING = {"Works_Tools": 0.9, "Works_Carry": 3.0, "Works_Site": 4.5}

def short(name): return name[len("Works_"):]
def src_col(name): return "W2 " + short(name)
def exp_col(name): return name + " Export"
objs_of, bounds = W.objs_of, W.bounds

# ------------------------------------------------------------------ collections
def show(*names):
    keep = set(names) | {"Studio", ROOT_COL, EXPORT_COL}
    def hit(lc):
        return lc.name in keep or any(hit(ch) for ch in lc.children)
    def walk(lc, parent_named):
        want = hit(lc) or parent_named
        lc.exclude = not want
        named = (lc.name in keep and lc.name not in (ROOT_COL, EXPORT_COL)) or parent_named
        for ch in lc.children:
            walk(ch, named)
    for _ in range(2):
        for ch in bpy.context.view_layer.layer_collection.children:
            walk(ch, False)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection

def new_col(name):
    c = W._attach(name, k.col(ROOT_COL))
    for o in list(c.objects):
        bpy.data.objects.remove(o)
    show(name)
    bpy.context.view_layer.active_layer_collection = W.lc_find(bpy.context.view_layer.layer_collection, name)
    bpy.context.scene.cursor.location = (0, 0, 0)
    return c

# ------------------------------------------------------------------ materials (WK_* from works_kit + WK2_*)
M = {}
def reset_mats():
    M.clear()
    for m in list(bpy.data.materials):
        if m.name.startswith("WK2_"): bpy.data.materials.remove(m)

def mats():
    if M:
        return M
    M.update(W.mats())
    M["handle"] = k.mat("WK2_Handle", (.82, .62, .36, 1), rough=.8, var=.08, scale=6)
    M["pwood"] = k.wood("WK2_PaleWood", (.86, .70, .44, 1), (.62, .46, .26, 1), scale=10, axis='X', rough=.8, bump=.2)
    M["pwoodY"] = k.wood("WK2_PaleWoodY", (.86, .70, .44, 1), (.62, .46, .26, 1), scale=10, axis='Y', rough=.8, bump=.2)
    M["pwoodZ"] = k.wood("WK2_PaleWoodZ", (.86, .70, .44, 1), (.62, .46, .26, 1), scale=10, axis='Z', rough=.8, bump=.2)
    M["woodZ"] = k.wood("WK2_WoodZ", (.80, .60, .35, 1), (.52, .36, .22, 1), scale=8, axis='Z', rough=.8, bump=.2)
    M["paper"] = k.mat("WK2_Paper", (.82, .76, .62, 1), rough=.9, var=.08, scale=8)
    M["card"] = k.mat("WK2_Cardboard", (.76, .58, .36, 1), rough=.9, var=.06, scale=8)
    M["tape"] = k.mat("WK2_Tape", (.55, .38, .22, 1), rough=.6, var=.04)
    M["rust"] = L.rustmetal("WK2_Rust", (.42, .30, .22, 1), rustiness=.7)
    M["alu"] = k.mat("WK2_Alu", (.78, .80, .82, 1), rough=.4, var=.06, scale=8, metallic=.4)
    M["grass"] = k.mat("WK2_Grass", (.42, .62, .22, 1), rough=.9, var=.22, scale=5)
    M["grassD"] = k.mat("WK2_GrassDark", (.30, .48, .18, 1), rough=.9, var=.22, scale=5)
    M["branch"] = k.mat("WK2_Branch", (.42, .31, .19, 1), rough=.9, var=.12, scale=8)
    M["sand"] = k.mat("WK2_Sand", (.80, .70, .46, 1), rough=.95, var=.12, scale=8, bump=.3)
    M["toilet"] = k.mat("WK2_ToiletBlue", (.18, .50, .78, 1), rough=.6, var=.05, scale=5)
    M["toiletD"] = k.mat("WK2_ToiletBlueD", (.13, .40, .66, 1), rough=.6, var=.05, scale=5)
    M["canvas"] = k.stripes("WK2_Canvas", (.86, .22, .18, 1), (.95, .93, .88, 1), width=.28, axis='X')
    M["straw"] = k.mat("WK2_Straw", (.84, .70, .36, 1), rough=.9, var=.15, scale=20)
    M["pane"] = k.mat("WK2_Pane", (.62, .80, .86, 1), rough=.15, var=.04, scale=3)
    M["brickwall"] = L.brickwall("WK2_BrickWall")
    M["sheet"] = corrugated_clean("WK2_Sheet", base=(.62, .64, .65, 1), pitch=.076, axis='Y')
    M["cement"] = k.mat("WK2_CementBand", (.75, .20, .16, 1), rough=.7, var=.05)
    M["green"] = k.mat("WK2_Green", (.20, .55, .35, 1), rough=.55, var=.06, scale=5)
    M["lime"] = k.mat("WK2_Lime", (.62, .80, .26, 1), rough=.55, var=.06, scale=5)
    return M

def corrugated_clean(name, base=(.62, .64, .65, 1), pitch=.076, axis='Y', rough=.6):
    """Galvanised sheet: rib shading only (no rust streaks), object-space bands along `axis`."""
    m, nt, bsdf, obj = L._start(name, rough)
    if nt is None:
        return m
    w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type = 'BANDS'; w.bands_direction = axis; w.wave_profile = 'SIN'
    w.inputs["Scale"].default_value = (2 * math.pi / 10.0) / pitch
    w.inputs["Distortion"].default_value = 0
    nt.links.new(obj, w.inputs["Vector"])
    shade = L.ramp(nt, w.outputs["Fac"], 0, 1, .70, 1.06)
    col = L.mul(nt, base, shade)
    col, g = L.grime(nt, col, .08, 30)
    L._finish(nt, bsdf, col, w.outputs["Fac"], .35)
    return m

# ------------------------------------------------------------------ geometry helpers
def tbox(name, size, loc, m, top=(1.0, 1.0), rot=(0, 0, 0), bevel=0.0, seg=1):
    """Box whose top face is scaled by `top` (fx, fy) -> tapered block / tray."""
    o = k.box(name, size, (0, 0, 0), m, bevel=bevel, seg=seg)
    h = size[2]
    for v in o.data.vertices:
        t = (v.co.z + h / 2) / h
        v.co.x *= 1 + (top[0] - 1) * t; v.co.y *= 1 + (top[1] - 1) * t
    o.location = loc; o.rotation_euler = rot
    return o

def xbeam(name, a, b, w, h, m, bevel=.005, seg=1):
    """Box from a to b lying in the XY plane (long axis along a->b), cross-section w (across) x h (Z)."""
    a, b = Vector(a), Vector(b); d = b - a
    ang = math.atan2(d.y, d.x)
    return k.box(name, (d.length, w, h), (a + b) / 2, m, rot=(0, 0, ang), bevel=bevel, seg=seg)

def ibeam(name, L_, x, y, z, m, w=.18, h=.18, t=.025):
    return [k.box(name + "_f1", (L_, w, t), (x, y, z + t / 2), m, bevel=0),
            k.box(name + "_f2", (L_, w, t), (x, y, z + h - t / 2), m, bevel=0),
            k.box(name + "_w", (L_, t, h - 2 * t), (x, y, z + h / 2), m, bevel=0)]

def bucket_objs(name, loc, M_, band=None, lid=True, r=.14, h=.32):
    x, y, z = loc
    p = [k.cyl(name + "_b", r * .86, h, (x, y, z + h / 2), M_["white"], verts=14, bevel=.01, seg=1, r2=r),
         k.cyl(name + "_band", r * .97, h * .3, (x, y, z + h * .55), band or M_["blue"], verts=14)]
    if lid:
        p.append(k.cyl(name + "_lid", r * 1.04, .025, (x, y, z + h + .01), M_["dsteel"], verts=14))
    p.append(k.tube(name + "_h1", (x - r, y, z + h - .02), (x - r * .8, y, z + h + .12), .006, M_["steel"], verts=5))
    p.append(k.tube(name + "_h2", (x - r * .8, y, z + h + .12), (x + r * .8, y, z + h + .12), .006, M_["steel"], verts=5))
    p.append(k.tube(name + "_h3", (x + r * .8, y, z + h + .12), (x + r, y, z + h - .02), .006, M_["steel"], verts=5))
    return p

def pallet_objs(name, m, loc=(0, 0, 0), simple=False):
    if not simple:
        return [L.pallet(name, loc, m, broken=False)]
    x, y, z = loc; p = []
    for yy in (-.5, 0, .5):
        p.append(k.box(name + "_run", (1.2, .10, .09), (x, y + yy, z + .045), m, bevel=0))
    for xx in (-.52, -.26, 0, .26, .52):
        p.append(k.box(name + "_top", (.10, 1.1, .02), (x + xx, y, z + .10), m, bevel=0))
    for yy in (-.42, 0, .42):
        p.append(k.box(name + "_bot", (1.2, .10, .02), (x, y + yy, z + .01), m, bevel=0))
    return p

def bag_objs(name, loc, M_, rot_z=0.0, seg=2):
    x, y, z = loc
    R = Matrix.Rotation(rot_z, 4, 'Z')
    p = [k.box(name + "_b", (.50, .32, .16), (0, 0, 0), M_["paper"], bevel=.045, seg=seg),
         k.box(name + "_band", (.09, .33, .165), (0, 0, 0), M_["cement"], bevel=.04, seg=seg),
         k.box(name + "_e1", (.03, .26, .08), (-.255, 0, 0), M_["paper"], bevel=.01, seg=1),
         k.box(name + "_e2", (.03, .26, .08), (.255, 0, 0), M_["paper"], bevel=.01, seg=1)]
    return W.place(p, T((x, y, z + .08)) @ R)

def truss_objs(name, z, M_, L_=3.0, h=.9, t=.05):
    m = M_["pwood"]
    p = [k.box(name + "_bc", (L_, .08, t), (0, -h / 2, z + t / 2), m, bevel=0),
         xbeam(name + "_tc1", (-L_ / 2, -h / 2, z + t / 2), (0, h / 2, z + t / 2), .08, t, m, bevel=0),
         xbeam(name + "_tc2", (0, h / 2, z + t / 2), (L_ / 2, -h / 2, z + t / 2), .08, t, m, bevel=0),
         k.box(name + "_kp", (.07, h, t), (0, 0, z + t / 2), m, bevel=0),
         xbeam(name + "_w1", (-L_ / 4, -h / 2, z + t / 2), (0, h / 2, z + t / 2), .06, t, m, bevel=0),
         xbeam(name + "_w2", (L_ / 4, -h / 2, z + t / 2), (0, h / 2, z + t / 2), .06, t, m, bevel=0)]
    return p

def tire_objs(name, loc, M_, R=.32, r=.11, rot=(0, 0, 0), rim=False):
    p = [L.tire(name + "_t", loc, M_["tire"], rot=rot, R=R, r=r)]
    if rim:
        p.append(k.cyl(name + "_rim", R - r + .03, r * 1.2, loc, M_["rim"], rot=(rot[0] + 0, rot[1], rot[2]), verts=10))
    return p

# ================================================================== ITEM BUILDERS (each returns primitives; origin = (0,0,0))
ITEMS = {}
def item(name):
    def deco(fn):
        ITEMS[name] = fn
        return fn
    return deco

# ---------------- KIT A: tools (grip at origin, long axis +Z, head on top)
@item("Tool_Sledgehammer")
def _(M_):
    return [k.cyl("h", .02, .95, (0, 0, .33), M_["handle"], verts=8),
            k.cyl("grip", .025, .18, (0, 0, 0), M_["black"], verts=8),
            k.box("hd", (.26, .09, .09), (0, 0, .85), M_["dsteel"], bevel=.012, seg=1)]

@item("Tool_Hammer")
def _(M_):
    return [k.cyl("h", .013, .31, (0, 0, .095), M_["handle"], verts=8),
            k.cyl("hd", .018, .10, (0, 0, .275), M_["dsteel"], rot=(0, PI2, 0), verts=8),
            k.box("claw", (.03, .018, .05), (0, -.025, .285), M_["dsteel"], bevel=.004, seg=1, rot=(rad(-30), 0, 0))]

@item("Tool_Saw")
def _(M_):
    bl = k.box("bl", (.13, .004, .48), (0, 0, 0), M_["steel"], bevel=0)
    for v in bl.data.vertices:
        if v.co.z > 0: v.co.x *= .55
    bl.location = (.055, 0, .33)
    return [k.box("hdl", (.04, .045, .16), (0, 0, 0), M_["handle"], bevel=.012, seg=2),
            k.box("horn", (.07, .045, .035), (-.03, 0, .085), M_["handle"], bevel=.01, seg=1), bl,
            k.box("teeth", (.008, .007, .46), (.12, 0, .31), M_["dsteel"], bevel=0, rot=(0, rad(-5), 0))]

@item("Tool_Shovel")
def _(M_):
    bl = k.box("bl", (.25, .02, .30), (0, 0, 0), M_["steel"], bevel=.006, seg=1)
    for v in bl.data.vertices:
        if v.co.z > 0: v.co.x *= .55
    bl.location = (0, 0, .77)
    return [k.cyl("h", .017, .88, (0, 0, .13), M_["handle"], verts=8),
            k.cyl("collar", .026, .12, (0, 0, .60), M_["dsteel"], verts=8), bl,
            k.box("dh", (.13, .03, .035), (0, 0, -.36), M_["black"], bevel=.01, seg=1),
            k.box("d1", (.025, .03, .08), (-.055, 0, -.31), M_["black"], bevel=0),
            k.box("d2", (.025, .03, .08), (.055, 0, -.31), M_["black"], bevel=0)]

@item("Tool_BrushCutter")
def _(M_):
    return [k.cyl("shaft", .016, 1.35, (0, 0, 0), M_["alu"], verts=8),
            k.cyl("motor", .085, .17, (0, 0, .76), M_["orange"], verts=12, bevel=.015, seg=1),
            k.cyl("start", .05, .04, (0, 0, .865), M_["black"], verts=10),
            k.box("tank", (.11, .09, .09), (0, -.085, .70), M_["black"], bevel=.015, seg=1),
            k.cyl("guard", .15, .035, (0, 0, -.70), M_["orange"], verts=12),
            k.cyl("spool", .05, .05, (0, 0, -.745), M_["black"], verts=10),
            k.tube("bar", (-.27, .05, .24), (.27, .05, .24), .012, M_["dsteel"], verts=6),
            k.tube("bar2", (0, .0, .22), (0, .05, .24), .012, M_["dsteel"], verts=6),
            k.cyl("g1", .018, .11, (-.22, .05, .24), M_["black"], rot=(0, PI2, 0), verts=6),
            k.cyl("g2", .018, .11, (.22, .05, .24), M_["black"], rot=(0, PI2, 0), verts=6)]

@item("Tool_Drill")
def _(M_):
    return [k.box("grip", (.042, .055, .13), (0, -.005, 0), M_["black"], bevel=.012, seg=2),
            k.cyl("body", .038, .18, (0, .02, .165), M_["yellow"], verts=10, bevel=.01, seg=1),
            k.box("bodyB", (.07, .09, .07), (0, -.01, .12), M_["yellow"], bevel=.015, seg=1),
            k.cyl("chuck", .024, .05, (0, .02, .28), M_["dsteel"], verts=10),
            k.cyl("bit", .006, .10, (0, .02, .35), M_["steel"], verts=6),
            k.box("batt", (.065, .085, .045), (0, -.01, -.085), M_["black"], bevel=.01, seg=1),
            k.box("trig", (.02, .02, .03), (0, .03, .04), M_["dsteel"], bevel=0)]

@item("Tool_Trowel")
def _(M_):
    bl = k.box("bl", (.12, .005, .18), (0, 0, 0), M_["steel"], bevel=0)
    for v in bl.data.vertices:
        if v.co.z > 0: v.co.x *= .12
    bl.location = (0, .04, .19)
    return [k.cyl("h", .014, .13, (0, 0, 0), M_["handle"], verts=8, bevel=.005, seg=1),
            k.tube("neck", (0, 0, .06), (0, .04, .11), .007, M_["dsteel"], verts=6), bl]

@item("Tool_PaintRoller")
def _(M_):
    return [k.cyl("pole", .012, .42, (0, 0, .11), M_["alu"], verts=8),
            k.cyl("grip", .017, .13, (0, 0, 0), M_["black"], verts=8),
            k.tube("fr", (0, 0, .30), (.11, 0, .45), .006, M_["steel"], verts=6),
            k.cyl("roller", .033, .24, (0, 0, .47), M_["blue"], rot=(0, PI2, 0), verts=10, bevel=.006, seg=1)]

@item("Tool_Wrench")
def _(M_):
    return [k.box("hdl", (.034, .012, .25), (0, 0, .075), M_["steel"], bevel=.004, seg=1),
            k.box("jaw", (.08, .014, .035), (0, 0, .215), M_["steel"], bevel=.004, seg=1),
            k.box("p1", (.022, .014, .05), (-.03, 0, .255), M_["steel"], bevel=.003, seg=1),
            k.box("p2", (.022, .014, .05), (.03, 0, .255), M_["steel"], bevel=.003, seg=1),
            k.cyl("ring", .032, .012, (0, 0, -.07), M_["steel"], rot=(PI2, 0, 0), verts=10)]

@item("Tool_Broom")
def _(M_):
    br = k.box("br", (.30, .05, .14), (0, 0, 0), M_["straw"], bevel=0)
    for v in br.data.vertices:
        if v.co.z > 0: v.co.x *= 1.12; v.co.y *= 1.3
    br.location = (0, 0, .925)
    return [k.cyl("h", .013, 1.1, (0, 0, .25), M_["handle"], verts=8),
            k.box("blk", (.30, .06, .05), (0, 0, .835), M_["wood"], bevel=.006, seg=1), br]

@item("Tool_Crowbar")
def _(M_):
    return [k.cyl("bar", .013, .82, (0, 0, .27), M_["dsteel"], verts=8),
            k.tube("hk1", (0, 0, .66), (0, .06, .74), .013, M_["dsteel"], verts=8),
            k.tube("hk2", (0, .06, .74), (0, .12, .72), .013, M_["dsteel"], verts=8),
            k.box("tip", (.03, .04, .012), (0, .13, .71), M_["dsteel"], bevel=0),
            k.box("chisel", (.03, .012, .07), (0, 0, -.16), M_["dsteel"], bevel=0)]

# ---------------- KIT B: carried items (origin at the centre)
@item("Prop_Plank")
def _(M_):
    return [k.box("pl", (2.4, .20, .05), (0, 0, 0), M_["pwood"], bevel=.006, seg=1)]

@item("Prop_Brick")
def _(M_):
    return [L.brick("b1", (0, -.062, 0), M_["brickR"]), L.brick("b2", (0, .062, 0), M_["brickR"], rot=(0, 0, .04))]

@item("Prop_CementBag")
def _(M_):
    return bag_objs("bag", (0, 0, -.08), M_)

@item("Prop_Box")
def _(M_):
    return [k.box("bx", (.5, .5, .5), (0, 0, 0), M_["card"], bevel=.012, seg=1),
            k.box("tape", (.07, .506, .506), (0, 0, 0), M_["tape"], bevel=0),
            k.box("flap", (.49, .003, .18), (0, .252, .15), M_["tape"], bevel=0)]

@item("Prop_Pole")
def _(M_):
    return [k.cyl("pole", .03, 2.5, (0, 0, 0), M_["alu"], rot=(0, PI2, 0), verts=8),
            k.cyl("c1", .036, .06, (-1.22, 0, 0), M_["black"], rot=(0, PI2, 0), verts=8),
            k.cyl("c2", .036, .06, (1.22, 0, 0), M_["black"], rot=(0, PI2, 0), verts=8)]

@item("Prop_Tire")
def _(M_):
    return tire_objs("t", (0, 0, 0), M_, R=.30, r=.10, rot=(PI2, 0, 0), rim=True)

@item("Prop_Bucket")
def _(M_):
    return bucket_objs("bk", (0, 0, -.16), M_)

@item("Prop_PipeBundle")
def _(M_):
    p = []
    for i, (y, z) in enumerate([(-.065, -.03), (0, -.03), (.065, -.03), (-.032, .025), (.032, .025)]):
        p.append(k.cyl(f"p{i}", .03, 2.0, (0, y, z), M_["steel"], rot=(0, PI2, 0), verts=8))
    for x in (-.6, .6):
        p.append(k.box("strap", (.04, .21, .13), (x, 0, 0), M_["black"], bevel=.01, seg=1))
    return p

@item("Prop_Sheet")
def _(M_):
    return [k.box("sh", (2.0, 1.0, .02), (0, 0, 0), M_["sheet"], bevel=0)]

@item("Prop_GrassBundle")
def _(M_):
    rnd = random.Random(7); p = []
    for i in range(5):
        x = -.24 + i * .12; m = M_["grass"] if i % 2 else M_["grassD"]
        p.append(k.ball(f"g{i}", .17, (x, rnd.uniform(-.06, .06), rnd.uniform(-.03, .03)), m, sub=2,
                        scale=(1.3, 1.0, .8), rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), 0)))
    for i in range(5):
        a = rnd.uniform(0, 6.28); e = rnd.uniform(-.3, .5)
        p.append(k.tube(f"br{i}", (rnd.uniform(-.2, .2), 0, 0),
                        (rnd.uniform(-.2, .2) + .45 * math.cos(a), .45 * math.sin(a) * .6, .35 * e), .012, M_["branch"], verts=4))
    return p

@item("Prop_Rubble")
def _(M_):
    return [L.chunk("ch", (0, 0, 0), M_["concrete"], s=.26, seed=3),
            k.tube("rb1", (-.1, .05, .05), (-.35, .12, .25), .012, M_["rust"], verts=5),
            k.tube("rb2", (.12, -.05, .08), (.32, -.1, .28), .012, M_["rust"], verts=5)]

# ---------------- KIT C: site props (origin ground centre)
def sawhorse(name, x, M_):
    m = M_["pwoodY"]; p = [k.box(name + "_top", (.09, .9, .09), (x, 0, .76), m, bevel=.006, seg=1)]
    for sy in (-1, 1):
        for sx in (-1, 1):
            p.append(k.box(name + "_leg", (.05, .05, .78), (x + sx * .13, sy * .36, .38), m, bevel=0, rot=(0, sx * rad(-18), 0)))
        p.append(k.box(name + "_br", (.34, .05, .04), (x, sy * .36, .35), m, bevel=0))
    return p

@item("Prop_Sawhorse")
def _(M_):
    return sawhorse("s1", -.8, M_) + sawhorse("s2", .8, M_) + \
           [k.box("plank", (2.4, .2, .05), (0, .05, .835), M_["pwood"], bevel=.006, seg=1, rot=(0, 0, rad(2)))]

@item("Prop_PlankStack")
def _(M_):
    rnd = random.Random(2); p = []
    for lvl in range(3):
        z = .025 + lvl * .13
        for i, y in enumerate((-.33, -.11, .11, .33)):
            p.append(k.box(f"pl{lvl}{i}", (2.4, .2, .05), (rnd.uniform(-.06, .06), y, z), M_["pwood"], bevel=.005, seg=1))
        if lvl < 2:
            for x in (-.9, .9):
                p.append(k.box("sp", (.08, .9, .08), (x, 0, z + .065), M_["wood"], bevel=0))
    return p

@item("Prop_BrickPallet")
def _(M_):
    return pallet_objs("pal", M_["wood"]) + \
           [k.box("bricks", (1.05, .92, .75), (0, 0, .11 + .375), M_["brickwall"], bevel=.01, seg=1),
            k.box("strap1", (.03, .94, .77), (-.35, 0, .11 + .375), M_["black"], bevel=0),
            k.box("strap2", (.03, .94, .77), (.35, 0, .11 + .375), M_["black"], bevel=0)]

@item("Prop_CementBags")
def _(M_):
    p = pallet_objs("pal", M_["wood"], simple=True)
    for i, y in enumerate((-.33, 0, .33)):
        p += bag_objs(f"b0{i}", (0, y, .11), M_, rot_z=0, seg=1)
    for i, x in enumerate((-.33, .0, .33)):
        p += bag_objs(f"b1{i}", (x, 0, .27), M_, rot_z=PI2, seg=1)
    p += bag_objs("b20", (0, -.2, .43), M_, rot_z=0.1, seg=1)
    return p

@item("Prop_RebarBundle")
def _(M_):
    p = []
    for x in (-1.0, 1.0):
        p.append(k.box("blk", (.14, .36, .09), (x, 0, .045), M_["wood"], bevel=0))
    for i, (y, z) in enumerate([(-.09, .115), (-.03, .115), (.03, .115), (.09, .115), (-.06, .165), (0, .165), (.06, .165)]):
        p.append(k.cyl(f"r{i}", .015, 3.0, (0, y, z), M_["rust"], rot=(0, PI2, 0), verts=6))
    for x in (-.7, .7):
        p.append(k.box("tie", (.03, .25, .13), (x, 0, .14), M_["dsteel"], bevel=0))
    return p

@item("Prop_SteelBeams")
def _(M_):
    p = []
    for x in (-1.0, 1.0):
        p.append(k.box("blk", (.14, .8, .09), (x, 0, .045), M_["wood"], bevel=0))
    p += ibeam("b1", 3.0, 0, -.2, .09, M_["dsteel"]) + ibeam("b2", 3.0, 0, .2, .09, M_["dsteel"])
    p += ibeam("b3", 3.0, .1, 0, .27, M_["dsteel"])
    return p

@item("Prop_Pallet")
def _(M_):
    return pallet_objs("pal", M_["wood"])

@item("Prop_Ladder")
def _(M_):
    p = []; H = 1.8
    for sy in (-1, 1):
        for sx in (-1, 1):
            p.append(k.tube("rail", (sx * .23, sy * .36, 0), (sx * .22, sy * .04, H), .022, M_["alu"], verts=6))
        for i in range(5):
            t = (i + .5) / 5.5; z = t * H; y = sy * (.36 + (.04 - .36) * t)
            p.append(k.tube("rung", (-.23, y, z), (.23, y, z), .016, M_["alu"], verts=6))
    p.append(k.box("top", (.52, .20, .05), (0, 0, H + .02), M_["alu"], bevel=.006, seg=1))
    return p

@item("Prop_Toolbox")
def _(M_):
    return [k.box("bx", (.52, .24, .22), (0, 0, .11), M_["red"], bevel=.015, seg=2),
            k.box("lid", (.53, .25, .012), (0, 0, .16), M_["dsteel"], bevel=0),
            k.box("hdl", (.17, .03, .03), (0, 0, .265), M_["black"], bevel=.006, seg=1),
            k.box("hp1", (.02, .025, .05), (-.08, 0, .24), M_["dsteel"], bevel=0),
            k.box("hp2", (.02, .025, .05), (.08, 0, .24), M_["dsteel"], bevel=0),
            k.box("latch", (.05, .012, .05), (0, .125, .15), M_["dsteel"], bevel=0)]

@item("Prop_Cone")
def _(M_):
    return [k.box("base", (.38, .38, .04), (0, 0, .02), M_["orange"], bevel=.006, seg=1),
            k.cyl("cone", .13, .62, (0, 0, .34), M_["orange"], verts=12, r2=.035),
            k.cyl("band", .092, .09, (0, 0, .42), M_["white"], verts=12, r2=.078)]

@item("Prop_Barrier")
def _(M_):
    return [k.box("base", (1.2, .48, .22), (0, 0, .11), M_["red"], bevel=.02, seg=1),
            tbox("body", (1.2, .36, .62), (0, 0, .53), M_["hazardR"], top=(1.0, .55), bevel=.02, seg=1),
            k.box("top", (1.22, .2, .08), (0, 0, .86), M_["red"], bevel=.015, seg=1),
            k.box("f1", (.25, .56, .06), (-.42, 0, .03), M_["black"], bevel=0),
            k.box("f2", (.25, .56, .06), (.42, 0, .03), M_["black"], bevel=0)]

@item("Prop_Generator")
def _(M_):
    p = [k.box("body", (.85, .50, .52), (0, 0, .46), M_["yellow"], bevel=.03, seg=2),
         k.box("eng", (.40, .34, .16), (-.1, 0, .78), M_["black"], bevel=.015, seg=1),
         k.cyl("exh", .035, .20, (.3, 0, .80), M_["dsteel"], verts=8),
         k.box("panel", (.32, .02, .24), (.15, .255, .45), M_["black"], bevel=0),
         k.box("skid", (.9, .55, .06), (0, 0, .20), M_["dsteel"], bevel=0),
         k.box("vent", (.02, .36, .3), (.43, 0, .45), M_["black"], bevel=0),
         k.tube("hdl", (-.44, -.2, .20), (-.75, -.2, .55), .015, M_["dsteel"], verts=6),
         k.tube("hdl2", (-.44, .2, .20), (-.75, .2, .55), .015, M_["dsteel"], verts=6),
         k.tube("hdl3", (-.75, -.2, .55), (-.75, .2, .55), .015, M_["black"], verts=6)]
    for sx in (-1, 1):
        p.append(k.box(f"leg{sx}", (.08, .5, .18), (sx * .38, 0, .09), M_["dsteel"], bevel=0))
    for sy in (-1, 1):
        p.append(k.cyl("wh", .12, .06, (.42, sy * .3, .12), M_["tire"], rot=(PI2, 0, 0), verts=12))
    return p

@item("Prop_WorkLight")
def _(M_):
    p = []
    for i in range(3):
        a = rad(90 + 120 * i)
        p.append(k.tube(f"leg{i}", (.55 * math.cos(a), .55 * math.sin(a), 0), (0, 0, 1.3), .018, M_["dsteel"], verts=6))
    p.append(k.cyl("mast", .022, 1.3, (0, 0, 1.85), M_["dsteel"], verts=8))
    p.append(k.cyl("hub", .05, .12, (0, 0, 1.3), M_["black"], verts=8))
    p.append(k.box("bar", (.55, .05, .05), (0, 0, 2.5), M_["dsteel"], bevel=0))
    for sx in (-1, 1):
        p.append(k.box("lamp", (.24, .16, .22), (sx * .18, .10, 2.56), M_["yellow"], bevel=.015, seg=1, rot=(rad(-25), 0, 0)))
        p.append(k.box("face", (.20, .015, .18), (sx * .18, .185, 2.595), M_["light"], bevel=0, rot=(rad(-25), 0, 0)))
    return p

@item("Prop_PortaToilet")
def _(M_):
    return [k.box("skid", (1.2, 1.25, .08), (0, 0, .04), M_["dsteel"], bevel=0),
            k.box("body", (1.1, 1.15, 2.3), (0, 0, 1.23), M_["toilet"], bevel=.03, seg=1),
            k.box("roof", (1.16, 1.21, .10), (0, 0, 2.42), M_["white"], bevel=.02, seg=1),
            k.box("door", (.74, .03, 2.0), (0, .575, 1.15), M_["toiletD"], bevel=0),
            k.box("vent", (.5, .02, .14), (0, .595, 2.0), M_["white"], bevel=0),
            k.box("hdl", (.05, .03, .14), (.28, .60, 1.05), M_["white"], bevel=0),
            k.cyl("pipe", .04, .3, (-.4, -.45, 2.55), M_["white"], verts=8)]

@item("Prop_SitePlate")
def _(M_):
    return [k.cyl("p1", .045, 2.5, (-1.15, 0, 1.25), M_["dsteel"], verts=8),
            k.cyl("p2", .045, 2.5, (1.15, 0, 1.25), M_["dsteel"], verts=8),
            k.box("frame", (2.7, .05, 1.4), (0, 0, 1.75), M_["blue"], bevel=.01, seg=1),
            k.box("panel", (2.56, .06, 1.26), (0, .01, 1.75), M_["white"], bevel=.006, seg=1),
            k.box("rail", (2.3, .04, .04), (0, 0, 1.0), M_["dsteel"], bevel=0)]

@item("Prop_TireStack")
def _(M_):
    p = []
    for i in range(4):
        p += tire_objs(f"t{i}", (0, 0, .11 + i * .22), M_, R=.32, r=.11, rot=(0, 0, i * .4))
    return p

@item("Prop_Drum")
def _(M_):
    return [L.drum("dr", (0, 0, 0), M_["blue"]), k.cyl("lid", .27, .03, (0, 0, .885), M_["dsteel"], verts=18)]

@item("Prop_GlassCrate")
def _(M_):
    p = [k.box("base", (2.0, 1.0, .10), (0, 0, .05), M_["wood"], bevel=.006, seg=1)]
    for sy in (-1, 1):
        r = (sy * rad(18), 0, 0)
        for x in (-.85, .85):
            p.append(k.box("post", (.08, .08, 1.5), (x, sy * .22, .80), M_["wood"], bevel=0, rot=r))
        p.append(k.box("top", (1.9, .08, .08), (0, sy * .06, 1.53), M_["wood"], bevel=0))
        for i in range(3):
            p.append(k.box(f"pane{sy}{i}", (1.6, .02, 1.1), (0, sy * (.28 + i * .04), .63), M_["pane"], bevel=0, rot=r))
    p.append(k.box("stop", (2.0, .06, .12), (0, -.49, .16), M_["wood"], bevel=0))
    p.append(k.box("stop2", (2.0, .06, .12), (0, .49, .16), M_["wood"], bevel=0))
    return p

@item("Prop_PaintBuckets")
def _(M_):
    return bucket_objs("b1", (-.2, -.15, 0), M_, band=M_["blue"]) + bucket_objs("b2", (.18, .1, 0), M_, band=M_["red"]) + \
           bucket_objs("b3", (-.2, -.15, .345), M_, band=M_["yellow"]) + bucket_objs("b4", (-.1, .3, 0), M_, band=M_["green"], lid=False)

@item("Prop_RoofTrusses")
def _(M_):
    p = []
    for i in range(4):
        p += truss_objs(f"tr{i}", i * .055, M_)
    return p

@item("Prop_Formwork")
def _(M_):
    p = []
    def panel(name, y, ang, m):
        R = T((0, y, 0)) @ Matrix.Rotation(ang, 4, 'X') @ T((0, 0, 1.0))
        q = [k.box(name + "_ply", (1.2, .03, 2.0), (0, 0, 0), m, bevel=0)]
        for z in (-.8, 0, .8):
            q.append(k.box(name + "_bat", (1.2, .06, .08), (0, .045, z), M_["wood"], bevel=0))
        for x in (-.5, .5):
            q.append(k.box(name + "_st", (.08, .06, 2.0), (x, .045, 0), M_["wood"], bevel=0))
        return W.place(q, R)
    p += panel("f1", -.70, rad(-20), M_["pwood"])
    p += panel("f2", .70, rad(20), M_["pwood"])
    p += panel("f3", .93, rad(24), M_["pwood"])
    p.append(k.box("spacer", (1.1, .6, .08), (0, 0, .04), M_["wood"], bevel=0))
    return p

@item("Prop_DebrisPile")
def _(M_):
    rnd = random.Random(11); p = []
    for i in range(10):
        a = rnd.uniform(0, 6.28); r = rnd.uniform(0, .8)
        x, y = 1.3 * r * math.cos(a), 1.0 * r * math.sin(a)
        s = rnd.uniform(.30, .48); z = s * .8 + (1 - r) * .35
        p.append(L.chunk(f"ch{i}", (x, y, z), M_["concrete"] if i % 3 else M_["rubble"], s=s, seed=i))
    for i in range(5):
        p.append(L.brick(f"bk{i}", (rnd.uniform(-1.15, 1.15), rnd.uniform(-.9, .9), .05), M_["brickR"], rot=(0, rnd.uniform(-.2, .2), rnd.uniform(0, 3))))
    p.append(k.box("plank", (1.3, .15, .04), (.3, -.4, .55), M_["wood"], bevel=0, rot=(rad(8), rad(-28), rad(30))))
    p.append(k.tube("rb1", (-.3, .2, .3), (-.9, .5, .85), .014, M_["rust"], verts=5))
    p.append(k.tube("rb2", (.2, -.1, .5), (.5, .3, 1.0), .014, M_["rust"], verts=5))
    return p

@item("Prop_GreenWaste")
def _(M_):
    rnd = random.Random(5); p = []
    for i in range(9):
        a = rnd.uniform(0, 6.28); r = rnd.uniform(0, .75)
        x, y = .85 * r * math.cos(a), .62 * r * math.sin(a)
        s = rnd.uniform(.34, .48); z = s * .75 + (1 - r) * .25 - .08
        p.append(k.ball(f"g{i}", s, (x, y, z), M_["grass"] if i % 2 else M_["grassD"], sub=1, scale=(1.2, 1.0, .75),
                        rot=(0, 0, rnd.uniform(0, 3))))
    for i in range(6):
        a = rnd.uniform(0, 6.28); e = rnd.uniform(.1, .6)
        p.append(k.tube(f"br{i}", (0.2 * math.cos(a), .2 * math.sin(a), .4), (1.05 * math.cos(a), .85 * math.sin(a), .4 + .7 * e), .02, M_["branch"], verts=4))
    return p

@item("Prop_WheelbarrowFull")
def _(M_):
    tray = tbox("tray", (.62, .95, .36), (0, .05, .46), M_["orange"], top=(1.0, 1.0), bevel=.03, seg=1)
    for v in tray.data.vertices:
        if v.co.z < 0: v.co.x *= .72; v.co.y *= .78
    return [tray, k.ball("sand", .3, (0, .05, .64), M_["sand"], sub=1, scale=(.95, 1.45, .55)),
            k.cyl("wh", .19, .07, (0, .62, .19), M_["tire"], rot=(0, PI2, 0), verts=14, bevel=.02, seg=1),
            k.cyl("rim", .10, .08, (0, .62, .19), M_["rim"], rot=(0, PI2, 0), verts=8),
            k.tube("h1", (-.25, .5, .27), (-.3, -.75, .62), .018, M_["dsteel"], verts=6),
            k.tube("h2", (.25, .5, .27), (.3, -.75, .62), .018, M_["dsteel"], verts=6),
            k.cyl("g1", .024, .16, (-.305, -.78, .63), M_["black"], rot=(PI2, 0, 0), verts=6),
            k.cyl("g2", .024, .16, (.305, -.78, .63), M_["black"], rot=(PI2, 0, 0), verts=6),
            k.box("l1", (.04, .04, .3), (-.25, -.25, .15), M_["dsteel"], bevel=0),
            k.box("l2", (.04, .04, .3), (.25, -.25, .15), M_["dsteel"], bevel=0),
            k.box("foot", (.6, .05, .04), (0, -.25, .02), M_["dsteel"], bevel=0),
            k.tube("fork", (0, .62, .19), (0, .3, .32), .02, M_["dsteel"], verts=6)]

@item("Prop_TentPoles")
def _(M_):
    p = []
    for i, (y, z) in enumerate([(-.05, .022), (0, .022), (.05, .022), (-.025, .062), (.025, .062), (0, .102)]):
        p.append(k.cyl(f"p{i}", .022, 2.5, (0, y, z), M_["alu"], rot=(0, PI2, 0), verts=8))
    for x in (-.8, .8):
        p.append(k.box("strap", (.05, .17, .14), (x, 0, .065), M_["black"], bevel=.01, seg=1))
    return p

@item("Prop_CanvasRoll")
def _(M_):
    return [k.cyl("roll", .21, 2.4, (0, 0, .21), M_["canvas"], rot=(0, PI2, 0), verts=14, bevel=.02, seg=1),
            k.box("s1", (.05, .45, .45), (-.7, 0, .21), M_["black"], bevel=.01, seg=1),
            k.box("s2", (.05, .45, .45), (.7, 0, .21), M_["black"], bevel=.01, seg=1)]

@item("Prop_ScaffoldTower")
def _(M_):
    A = M_["alu"]; p = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(k.cyl("leg", .026, 3.8, (sx * 1.0, sy * .7, .2 + 1.9), A, verts=8))
            p.append(k.cyl("wheel", .10, .07, (sx * 1.0, sy * .7, .10), M_["black"], rot=(0, PI2, 0), verts=10))
        for i in range(1, 11):
            z = .2 + i * .38
            p.append(k.tube("rung", (sx * 1.0, -.7, z), (sx * 1.0, .7, z), .016, A, verts=6))
    for sy in (-1, 1):
        for i in range(3):
            z0, z1 = .3 + i * 1.0, 1.3 + i * 1.0
            p.append(k.tube("brace", (-1.0 * (1 if i % 2 == 0 else -1), sy * .7, z0), (1.0 * (1 if i % 2 == 0 else -1), sy * .7, z1), .016, A, verts=6))
        for z in (3.5, 4.0):
            p.append(k.tube("rail", (-1.0, sy * .7, z), (1.0, sy * .7, z), .018, A, verts=6))
        p.append(k.box("toe", (2.0, .03, .15), (0, sy * .69, 3.11), M_["pwood"], bevel=0))
    for sx in (-1, 1):
        for z in (3.5, 4.0):
            p.append(k.tube("railx", (sx * 1.0, -.7, z), (sx * 1.0, .7, z), .018, A, verts=6))
    p.append(k.box("deck", (2.0, 1.4, .06), (0, 0, 3.03), M_["pwood"], bevel=.005, seg=1))
    p.append(k.box("hatch", (.6, .5, .07), (.55, .3, 3.035), M_["wood"], bevel=0))
    return p

# ================================================================== kit / big builders
def build_kit(name):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    out = []
    for i, item_name in enumerate(KITS[name]):
        p = ITEMS[item_name](M_)
        o = W.part(N + item_name, p, (0, 0, 0), None, c)
        o.location.x = i * SPACING[name]
        out.append(o)
    return stats(name)

def build_tent_frame(name="Works_TentFrame"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    A, D = M_["alu"], M_["dsteel"]; p = []
    X, Y, H, R = 1.7, 1.1, 2.2, 2.85
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(k.cyl("pole", .032, H, (sx * X, sy * Y, H / 2), A, verts=8))
            p.append(k.box("foot", (.22, .22, .03), (sx * X, sy * Y, .015), D, bevel=.004, seg=1))
            p.append(k.tube("rafter", (sx * X, sy * Y, H), (sx * X, 0, R), .026, A, verts=6))
        p.append(k.tube("eaveY", (sx * X, -Y, H), (sx * X, Y, H), .026, A, verts=6))
        p.append(k.tube("king", (sx * X, 0, H), (sx * X, 0, R), .026, A, verts=6))
    for sy in (-1, 1):
        p.append(k.tube("eaveX", (-X, sy * Y, H), (X, sy * Y, H), .026, A, verts=6))
        p.append(k.tube("rafterM", (0, sy * Y, H), (0, 0, R), .026, A, verts=6))
    p.append(k.tube("ridge", (-X, 0, R), (X, 0, R), .03, A, verts=6))
    p.append(k.tube("eaveM", (-X, 0, H), (X, 0, H), .022, A, verts=6))
    # folding table leaning on the front-left pole (top edge against the pole, feet on the ground)
    R_ = T((-1.55, .55, .36)) @ Matrix.Rotation(rad(-20), 4, 'Y')
    q = [k.box("tabletop", (.05, 1.2, .72), (0, 0, 0), M_["white"], bevel=.01, seg=1),
         k.box("tabEdge", (.03, 1.24, .76), (0, 0, 0), M_["dsteel"], bevel=.006, seg=1),
         k.box("tabLeg1", (.03, .9, .03), (.04, 0, -.22), D, bevel=0),
         k.box("tabLeg2", (.03, .9, .03), (.04, 0, .22), D, bevel=0)]
    p += W.place(q, R_)
    W.part(N + "Body", p, (0, 0, 0), None, c)
    return stats(name)

def build_stall_frame(name="Works_StallFrame"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    P, Wd, PX = M_["pwoodZ"], M_["wood"], M_["pwood"]; p = []
    HX, YB, YF, HB, HF = 2.2, -1.4, 1.4, 2.3, 2.6
    for x in (-HX, 0, HX):
        p.append(k.box("postB", (.10, .10, HB), (x, YB, HB / 2), P, bevel=.006, seg=1))
        p.append(k.box("postF", (.10, .10, HF), (x, YF, HF / 2), P, bevel=.006, seg=1))
    p.append(k.box("plateF", (4.6, .10, .12), (0, YF, HF + .06), PX, bevel=.006, seg=1))
    p.append(k.box("plateB", (4.6, .10, .12), (0, YB, HB + .06), PX, bevel=.006, seg=1))
    # rafters: 3 of 5 in place, one lying on the ground
    for x in (-HX, 0, HX):
        p.append(W.beam("rafter", (x, YF + .1, HF + .12), (x, YB - .15, HB + .12), .08, .14, M_["wood"], bevel=.005, seg=1))
    p.append(k.box("rafterDown", (.08, 3.2, .14), (-1.3, .1, .07), M_["wood"], bevel=.005, seg=1, rot=(0, 0, rad(8))))
    p.append(k.box("purlin", (4.4, .08, .08), (0, -.3, HB + .12 + 1.1 / 2.8 * .3 + .11), PX, bevel=0))
    for i, y in enumerate((-1.3, -1.05, -.8, -.55)):   # a few roof boards on the back half
        zz = HB + .12 + (y - YB) / (YF - YB) * (HF - HB) + .09
        p.append(k.box(f"rb{i}", (4.5, .22, .025), (0, y, zz), PX, bevel=0, rot=(rad(6.1), 0, 0)))
    # counter at the front
    for y in (YF - .05, .75):
        p.append(k.box("crail", (4.5, .08, .08), (0, y, .86), PX, bevel=0))
    for x in (-HX, 0, HX):
        p.append(k.box("cx", (.08, .7, .08), (x, 1.05, .86), M_["wood"], bevel=0))
        p.append(k.box("cpost", (.08, .08, .86), (x, .75, .43), P, bevel=0))
    for i, y in enumerate((.80, 1.0, 1.2)):           # counter top: 3 of 4 planks
        p.append(k.box(f"ct{i}", (4.5, .18, .04), (0, y, .92), PX, bevel=.004, seg=1))
    p.append(k.box("ctLoose", (2.2, .18, .04), (1.0, 1.42, 1.1), PX, bevel=.004, seg=1, rot=(rad(-55), 0, rad(4))))
    for z in (.2, .45):                                # front skirt: 2 of 3 boards
        p.append(k.box("skirt", (4.5, .03, .18), (0, YF + .06, z), PX, bevel=0))
    p.append(k.box("skirtS", (1.5, .03, .18), (-1.5, YF + .06, .7), PX, bevel=0))
    for sx in (-1, 1):
        p.append(k.box("brace", (.06, 2.6, .10), (sx * HX, 0, 1.8), M_["wood"], bevel=0, rot=(rad(35), 0, 0)))
    p.append(k.box("sideRail", (.08, 2.8, .08), (-HX, 0, 1.3), PX, bevel=0))
    W.part(N + "Body", p, (0, 0, 0), None, c)
    return stats(name)

def build_foundation(name="Works_Foundation"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    C, Ru = M_["concrete"], M_["rust"]; p = []
    p.append(k.box("slab", (8, 6, .25), (0, 0, .125), C, bevel=.02, seg=1))
    for x in (-3, -1, 1, 3):
        for y in (-2, 0, 2):
            p.append(k.box("pad", (.7, .7, .33), (x, y, .165), M_["rubble"], bevel=.015, seg=1))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    p.append(k.cyl("stub", .02, .45, (x + sx * .2, y + sy * .2, .33 + .22), Ru, verts=5))
    for x in range(-7, 8, 2):
        for y in (-2.75, 2.75):
            p.append(k.cyl("edge", .02, .55, (x / 2, y, .25 + .27), Ru, verts=5))
    for y in (-1.5, -.5, .5, 1.5):
        for x in (-3.75, 3.75):
            p.append(k.cyl("edge", .02, .55, (x, y, .25 + .27), Ru, verts=5))
    for sx in (-1, 1):   # a couple of horizontal ties along the long edges
        p.append(k.cyl("tie", .015, 7.2, (0, sx * 2.75, .25 + .45), Ru, rot=(0, PI2, 0), verts=5))
    W.part(N + "Body", p, (0, 0, 0), None, c)
    return stats(name)

def build_sign_frame(name="Works_SignFrame"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    D, S = M_["dsteel"], M_["steel"]; p = []
    for z in (.3, 2.35):
        p.append(k.box("rail", (8.0, .08, .08), (0, 0, z), D, bevel=.004, seg=1))
    for i in range(9):
        x = -4.0 + i
        p.append(k.box("vert", (.08, .08, 2.4), (x, 0, 1.2), D, bevel=.004, seg=1))
    for x in (-3.5, -1.5, 1.5, 3.5):
        p.append(k.box("rpost", (.07, .07, 1.5), (x, -.35, .75), D, bevel=0))
        p.append(k.tube("diag", (x, -.35, 1.5), (x, -.02, 2.33), .03, S, verts=6))
        p.append(k.box("foot", (.3, .5, .05), (x, -.17, .025), D, bevel=0))
        p.append(k.box("base", (.07, .35, .07), (x, -.17, .3), D, bevel=0))
    p.append(k.box("panelL", (4.0, .04, 2.0), (-2.0, .06, 1.35), M_["white"], bevel=.006, seg=1))
    p.append(k.box("panelLead", (3.9, .04, 2.0), (2.05, .5, .906), M_["white"], bevel=.006, seg=1, rot=(rad(25), 0, 0)))
    for x in (.6, 3.4):
        p.append(k.box("clip", (.1, .06, .3), (x, .06, 2.2), S, bevel=0))
    W.part(N + "Body", p, (0, 0, 0), None, c)
    return stats(name)

BUILDERS = {"Works_TentFrame": build_tent_frame, "Works_StallFrame": build_stall_frame,
            "Works_Foundation": build_foundation, "Works_SignFrame": build_sign_frame}

def build(name):
    return build_kit(name) if name in KITS else BUILDERS[name]()

def build_all():
    return {n: build(n) for n in MODELS}

def stats(name):
    """Per root object: bbox dims (world, with the row offset removed), origin-relative lo/hi, tris."""
    objs = objs_of(src_col(name)); dg = bpy.context.evaluated_depsgraph_get(); out = {}
    for o in objs:
        lo, hi = bounds([o]); off = o.matrix_world.translation
        out[o.name.split(".", 1)[1]] = {"dims": [round(v, 2) for v in (hi - lo)], "lo": [round(v, 2) for v in (lo - off)],
                                        "hi": [round(v, 2) for v in (hi - off)], "tris": len(o.evaluated_get(dg).data.loop_triangles)}
    return out

# ================================================================== pipeline (copy -> bake one atlas -> fbx)
def make_export(name):
    cname = src_col(name)
    d = W._attach(exp_col(name), k.col(EXPORT_COL))
    for o in list(d.objects): bpy.data.objects.remove(o)
    show(cname, d.name)
    src = objs_of(cname); out = []
    for o in src:
        n = o.copy(); n.data = o.data.copy(); n.name = "X_" + o.name; d.objects.link(n)
        n.matrix_world = o.matrix_world.copy(); out.append(n)
    bpy.context.view_layer.update()
    for n in out: k.bake(n)
    bpy.ops.object.select_all(action='DESELECT')
    for o in out: o.select_set(True)
    bpy.context.view_layer.objects.active = out[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.001, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    return out

def bake(name, size=None, batches=1, batch_i=None):
    size = size or SIZE.get(name, 1024)
    sc = bpy.context.scene
    show(exp_col(name))
    allobjs = objs_of(exp_col(name))
    objs = allobjs if batch_i is None else allobjs[batch_i::batches]
    img_name = name + "_BaseColor"
    first = batch_i in (None, 0)
    if first:
        for im in list(bpy.data.images):
            if im.name.startswith(img_name): bpy.data.images.remove(im)
        img = bpy.data.images.new(img_name, size, size)
    else:
        img = bpy.data.images[img_name]
    mats_ = {m for o in objs for m in o.data.materials if m}; added = []
    for m in mats_:
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; m.node_tree.nodes.active = n; added.append((m, n))
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 1
    b = sc.render.bake
    b.use_pass_direct = False; b.use_pass_indirect = False; b.use_pass_color = True; b.margin = 4; b.use_clear = first
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type='DIFFUSE')
    for m, n in added: m.node_tree.nodes.remove(n)
    if batch_i is not None and batch_i < batches - 1:
        sc.render.engine = 'BLENDER_EEVEE'
        return None
    os.makedirs(OUT, exist_ok=True)
    img.filepath_raw = os.path.join(OUT, img_name + ".png"); img.file_format = 'PNG'; img.save()
    am = bpy.data.materials.get(name + "_Mat") or bpy.data.materials.new(name + "_Mat")
    am.use_nodes = True; nt = am.node_tree
    for n in list(nt.nodes):
        if n.bl_idname == "ShaderNodeTexImage": nt.nodes.remove(n)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
    for o in allobjs:
        o.data.materials.clear(); o.data.materials.append(am)
        for p in o.data.polygons: p.material_index = 0
    sc.render.engine = 'BLENDER_EEVEE'
    return img.filepath_raw

def export(name):
    """FBX with the final root names (X_Tools.Tool_Hammer -> Tool_Hammer); roots turned 180 deg by export_unity."""
    show(exp_col(name))
    objs = objs_of(exp_col(name))
    renames, parked = [], []
    for o in objs:
        final = o.name.split(".", 1)[1]
        other = bpy.data.objects.get(final)
        if other is not None and other is not o:
            other.name = other.name + "~"; parked.append(other)
        renames.append((o, o.name)); o.name = final
    try:
        path = cp.export_unity(objs, name, folder=OUT)
    finally:
        for o, old in renames: o.name = old
        for other in parked: other.name = other.name[:-1]
    tris = sum(len(o.data.loop_triangles) for o in objs)
    return {"fbx": path, "kb": os.path.getsize(path) // 1024, "tris": tris, "objs": len(objs)}

def pipeline(name, batches=1):
    batches = max(1, min(batches, len(make_export(name))))
    for p in range(batches):
        bake(name, None, batches, p)
    return export(name)

def verify(name):
    before = set(bpy.data.objects); mb = set(bpy.data.materials); ib = set(bpy.data.images); meb = set(bpy.data.meshes)
    c = W._attach("Works_Scratch", k.col(EXPORT_COL)); show("Works_Scratch")
    bpy.context.view_layer.active_layer_collection = W.lc_find(bpy.context.view_layer.layer_collection, "Works_Scratch")
    bpy.ops.import_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    info = []
    for o in new:
        lo, hi = bounds([o])
        info.append({"name": o.name, "parent": o.parent.name if o.parent else None,
                     "world": [round(v, 2) for v in o.matrix_world.translation],
                     "dims": [round(v, 2) for v in (hi - lo)], "tris": len(o.data.loop_triangles) if o.type == 'MESH' else 0,
                     "mats": [m.name for m in o.data.materials] if o.type == 'MESH' else []})
    for o in new: bpy.data.objects.remove(o)
    for m in list(bpy.data.materials):
        if m not in mb: bpy.data.materials.remove(m)
    for im in list(bpy.data.images):
        if im not in ib: bpy.data.images.remove(im)
    for me in list(bpy.data.meshes):
        if me not in meb and me.users == 0: bpy.data.meshes.remove(me)
    bpy.data.collections.remove(c)
    return info

# ================================================================== previews
ISO = W.ISO

def shot(target, direction, dist, lens=40, name="x", res=(1100, 720), ortho=None):
    sc = bpy.context.scene
    cp.studio(); sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.exposure = -0.2
    cam = bpy.data.objects["Studio Cam"]; cam.data.lens = lens
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho; cam.data.clip_end = 2000
    else:
        cam.data.type = 'PERSP'
    d = Vector(direction).normalized(); t = Vector(target)
    cam.location = t + d * dist; cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    os.makedirs(REVIEW, exist_ok=True)
    path = os.path.join(REVIEW, name + ".png"); sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path

def _sheet(entries, name, direction, res, cols, dx, dy, label_size, ortho_pad=1.0):
    """entries: list of (label, object). Objects are moved on a grid (lifted so their lowest point is on the ground)."""
    d = Vector(direction); right = Vector((-d.y, d.x, 0)).normalized(); back = Vector((-d.x, -d.y, 0)).normalized()
    moved = []; labels = []
    hidden = [o for o in bpy.context.scene.collection.objects if not o.hide_render]
    for o in hidden: o.hide_render = True
    m_txt = k.mat("WK_Label", (.08, .08, .09, 1), rough=.9, var=0)
    rz = math.atan2(right.y, right.x)
    for i, (lbl, o) in enumerate(entries):
        col, row = i % cols, i // cols
        pos = right * (col * dx) + back * (row * dy)
        lo, hi = bounds([o]); old = o.location.copy()
        o.location = (pos.x + (o.location.x - (lo.x + hi.x) / 2), pos.y + (o.location.y - (lo.y + hi.y) / 2), o.location.z - lo.z)
        moved.append((o, old))
        lp = pos - back * (dy * .42)
        labels.append(k.text("WK_lbl", lbl, label_size, (lp.x, lp.y, .01), m_txt, rot=(0, 0, rz), extrude=.01, res=2))
    n_rows = (len(entries) + cols - 1) // cols
    ctr = right * ((cols - 1) * dx / 2) + back * ((n_rows - 1) * dy / 2)
    g = k.box("WK_Ground", (400, 400, .02), (ctr.x, ctr.y, -.015), k.pavers("ERA_Pavers"), bevel=0)
    p = shot((ctr.x, ctr.y, 1.0), direction, 300, lens=40, name=name, res=res, ortho=(cols * dx + 1) * ortho_pad)
    bpy.data.objects.remove(g)
    for t in labels: bpy.data.objects.remove(t)
    for o, old in moved:
        o.location = old
    for o in hidden: o.hide_render = False
    return p

def contact_kits(name="contact_kits", baked=True, direction=ISO, res=(5600, 4000), cols=10, dx=3.8, dy=7.0, kits=None, label=.34):
    kits = kits or list(KITS)
    cols_ = [exp_col(n) if baked else src_col(n) for n in kits]
    show(*cols_)
    entries = []
    for kit, cname in zip(kits, cols_):
        for o in objs_of(cname):
            entries.append((o.name.split(".", 1)[1], o))
    return _sheet(entries, name, direction, res, cols, dx, dy, label)

def contact_big(name="contact_big", baked=True, direction=ISO, res=(4400, 2600), cols=2, dx=12.0, dy=11.0):
    cols_ = [exp_col(n) if baked else src_col(n) for n in BIG]
    show(*cols_)
    entries = [(short(n), objs_of(c)[0]) for n, c in zip(BIG, cols_)]
    return _sheet(entries, name, direction, res, cols, dx, dy, .8)
