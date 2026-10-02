
# works_kit.py - the construction-works machines (Works_*): animated hierarchies for Unity.
# Same family as lot_kit / lot_kit2 (metres, origin at ground centre, one baked BaseColor atlas per model,
# exported with checkout_project.export_unity) but every model keeps a HIERARCHY of separate objects
# (object origin = hinge) named exactly as the game expects: Body (root) > Cab > Boom > Arm > Bucket, Wheel_i, ...
# Front of a vehicle faces +Y while modelling; export_unity() turns it 180 deg so it faces Unity +Z.
# Pitch parts rotate about their local X, yaw parts about local Z (Blender) = local Y (Unity).
#
#   import sys; sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
#   import works_kit as W; W.build_all()          # sources under the "Works_v1" collection (one child collection per model)
#   W.pipeline("Works_MiniExcavator")              # export copy (hierarchy kept) + bake atlas + FBX + verify
#   W.contact_sheet()                              # ArtSource/Review/works_v1/contact.png
import bpy, bmesh, math, random, sys, os
sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
sys.path.insert(0, r"C:\Checkout-mobile\scripts\blender")
import era_kit as k, lot_kit as L, checkout_project as cp
from mathutils import Vector, Matrix, Euler

ROOT_COL = "Works_v1"
EXPORT_COL = "Works_v1 Export"
OUT = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets\Resources\CheckoutWorks"
REVIEW = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\works_v1"
MODELS = ["Works_MiniExcavator", "Works_Excavator", "Works_SkidLoader", "Works_DumpTruck", "Works_TowTruck",
          "Works_CraneTruck", "Works_WreckingCrane", "Works_Pickup", "Works_Forklift", "Works_CherryPicker",
          "Works_CementMixer", "Works_Dumpster", "Works_Container"]
SIZE = {"Works_MiniExcavator": 1024, "Works_SkidLoader": 1024, "Works_Forklift": 1024, "Works_CementMixer": 1024,
        "Works_Dumpster": 1024, "Works_Pickup": 2048}   # default 2048

def rad(d): return math.radians(d)
def short(name): return name[len("Works_"):]          # Works_DumpTruck -> DumpTruck
def src_col(name): return "W " + short(name)            # source collection name
def exp_col(name): return name + " Export"

# ------------------------------------------------------------------ collections / view layer
def lc_find(lc, name):
    if lc.name == name:
        return lc
    for ch in lc.children:
        r = lc_find(ch, name)
        if r:
            return r
    return None

def _attach(name, root):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in root.children:
        for p in bpy.data.collections:
            if c.name in p.children: p.children.unlink(c)
        if c.name in bpy.context.scene.collection.children: bpy.context.scene.collection.children.unlink(c)
        root.children.link(c)
    return c

def show(*names):
    """Include only the named collections (any depth) + Studio in the view layer."""
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
    """Empty child collection of Works_v1, shown and made active (bpy.ops primitives land in it)."""
    c = _attach(name, k.col(ROOT_COL))
    for o in list(c.objects):
        bpy.data.objects.remove(o)
    show(name)
    bpy.context.view_layer.active_layer_collection = lc_find(bpy.context.view_layer.layer_collection, name)
    bpy.context.scene.cursor.location = (0, 0, 0)
    return c

def objs_of(cname):
    return [o for o in bpy.data.collections[cname].objects if o.type == 'MESH']

def bounds(objs):
    lo = Vector((1e9,) * 3); hi = -lo
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != 'MESH': continue
        me = o.evaluated_get(dg).data
        for v in me.vertices:
            w = o.matrix_world @ v.co; lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi

def stats(name):
    objs = objs_of(src_col(name))
    lo, hi = bounds(objs)
    dg = bpy.context.evaluated_depsgraph_get()
    return {"dims": [round(v, 2) for v in (hi - lo)], "lo": [round(v, 2) for v in lo], "hi": [round(v, 2) for v in hi],
            "tris": sum(len(o.evaluated_get(dg).data.loop_triangles) for o in objs),
            "parts": [(o.name.split(".", 1)[1], o.parent.name.split(".", 1)[1] if o.parent else None,
                       [round(v, 3) for v in o.location]) for o in objs]}

# ------------------------------------------------------------------ materials (all names WK_*)
def hazard(name, a=(.96, .72, .10, 1), b=(.12, .12, .13, 1), width=.10):
    """Diagonal hazard stripes (object space x+y+z)."""
    m, nt = k._new(name)
    if nt is None:
        return m
    bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = .6
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    s = L.fmath(nt, 'ADD', L.fmath(nt, 'ADD', sep.outputs[0], sep.outputs[1]), sep.outputs[2])
    f = L.fmath(nt, 'FRACT', L.fmath(nt, 'DIVIDE', s, width * 2))
    gt = L.fmath(nt, 'GREATER_THAN', f, .5)
    col = L.mix(nt, a, b, gt)
    nt.links.new(col, bsdf.inputs["Base Color"])
    return m

M = {}
def reset_mats(prefix="WK_"):
    M.clear()
    for m in list(bpy.data.materials):
        if m.name.startswith(prefix): bpy.data.materials.remove(m)

def mats():
    if M:
        return M
    M["yellow"] = k.mat("WK_Yellow", (.97, .72, .10, 1), rough=.55, var=.08, scale=5)
    M["orange"] = k.mat("WK_Orange", (.95, .42, .08, 1), rough=.55, var=.08, scale=5)
    M["red"] = k.mat("WK_Red", (.80, .13, .11, 1), rough=.55, var=.08, scale=5)
    M["blue"] = k.mat("WK_Blue", (.13, .33, .68, 1), rough=.55, var=.08, scale=5)
    M["white"] = k.mat("WK_White", (.91, .91, .88, 1), rough=.55, var=.05, scale=5)
    M["black"] = k.mat("WK_Black", (.13, .13, .14, 1), rough=.7, var=.05, scale=8)
    M["steel"] = k.mat("WK_Steel", (.55, .57, .59, 1), rough=.5, var=.08, scale=8, metallic=.3)
    M["dsteel"] = k.mat("WK_DarkSteel", (.27, .28, .30, 1), rough=.6, var=.08, scale=8)
    M["tire"] = k.mat("WK_Tire", (.11, .11, .12, 1), rough=.8, var=.05, scale=10)
    M["rim"] = k.mat("WK_Rim", (.62, .63, .64, 1), rough=.45, var=.06, scale=8, metallic=.3)
    M["glass"] = k.mat("WK_Glass", (.26, .44, .55, 1), rough=.2, var=.06, scale=3)
    M["beacon"] = k.mat("WK_Beacon", (1.0, .45, .05, 1), rough=.3, var=.03)
    M["light"] = k.mat("WK_Light", (.96, .94, .82, 1), rough=.3, var=.03)
    M["tail"] = k.mat("WK_TailLight", (.85, .12, .10, 1), rough=.3, var=.03)
    M["hazard"] = hazard("WK_Hazard")
    M["hazardR"] = hazard("WK_HazardRed", (.85, .15, .12, 1), (.93, .93, .90, 1), .09)
    M["chrome"] = k.mat("WK_Chrome", (.74, .76, .78, 1), rough=.3, var=.05, scale=8, metallic=.7)
    M["wood"] = k.wood("WK_Wood", (.80, .60, .35, 1), (.52, .36, .22, 1), scale=8, axis='Y', rough=.8, bump=.2)
    M["rubble"] = k.mat("WK_Rubble", (.58, .55, .50, 1), rough=.95, var=.20, scale=8, bump=.4)
    M["dirt"] = k.mat("WK_Dirt", (.50, .40, .28, 1), rough=.95, var=.18, scale=6, bump=.4)
    M["brickR"] = k.mat("WK_BrickR", (.68, .36, .26, 1), rough=.9, var=.12, scale=20)
    M["concrete"] = k.mat("WK_Concrete", (.66, .64, .60, 1), rough=.95, var=.14, scale=10, bump=.3)
    M["contY"] = L.corrugated("WK_ContainerY", base=(.28, .46, .33, 1), rustiness=.45, pitch=.15, axis='Y', rough=.7)
    M["contX"] = L.corrugated("WK_ContainerX", base=(.28, .46, .33, 1), rustiness=.45, pitch=.15, axis='X', rough=.7)
    M["contFlat"] = L.rustmetal("WK_ContainerFlat", (.28, .46, .33, 1), rustiness=.55)
    M["seat"] = k.mat("WK_Seat", (.20, .20, .22, 1), rough=.8, var=.05)
    return M

# ------------------------------------------------------------------ geometry helpers
def place(objs, Mw):
    for o in objs:
        o.matrix_world = Mw @ o.matrix_world
    return objs

def Rx(deg): return Matrix.Rotation(rad(deg), 4, 'X')
def Rz(deg): return Matrix.Rotation(rad(deg), 4, 'Z')
def T(v): return Matrix.Translation(Vector(v))

def beam(name, a, b, w, h, m, bevel=.01, seg=1):
    """Box from a to b (same x), cross-section w (X) x h; long axis along the a->b direction (in the YZ plane)."""
    a, b = Vector(a), Vector(b); d = b - a
    ang = math.atan2(d.z, d.y)
    return k.box(name, (w, d.length, h), (a + b) / 2, m, rot=(ang, 0, 0), bevel=bevel, seg=seg)

def ram(name, a, b, r, m_cyl, m_rod, verts=8):
    """Hydraulic cylinder from a (barrel end) to b (rod end)."""
    a, b = Vector(a), Vector(b)
    return [k.tube(name + "_c", a, a.lerp(b, .58), r, m_cyl, verts=verts),
            k.tube(name + "_r", a.lerp(b, .5), b, r * .55, m_rod, verts=verts)]

def autosmooth(o, angle=50.0):
    """Smooth faces + sharp edges above `angle` (Blender 4.1+ auto-smooth representation)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    for f in bm.faces: f.smooth = True
    for e in bm.edges:
        e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(0.0) < rad(angle)
    bm.to_mesh(o.data); bm.free()
    return o

def ram_along(name, a, b, t0, t1, off, r, m_cyl, m_rod):
    """Ram parallel to segment a->b (fractions t0..t1), offset `off` along the segment's normal in the YZ plane
    (positive = rotated +90 deg about X: for a segment going up-forward that is back-up)."""
    a, b = Vector(a), Vector(b); d = (b - a).normalized(); n = Vector((0, -d.z, d.y))
    return ram(name, a + d * ((b - a).length * t0) + n * off, a + d * ((b - a).length * t1) + n * off, r, m_cyl, m_rod)

def part(name, objs, pivot, parent=None, c=None, rot=(0, 0, 0), flat=False):
    """Join `objs` (world-space primitives) into ONE object whose origin is `pivot`, parented to `parent`
    (local axes aligned with the parent, unless `rot`). Modifiers are applied by k.join."""
    bpy.context.view_layer.update()
    o = k.join(objs, name, origin=pivot)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    R = Euler(rot).to_matrix().to_4x4()
    if any(rot):
        o.data.transform(R.inverted())
    o.rotation_euler = rot
    if parent is not None:
        o.parent = parent
        o.matrix_parent_inverse.identity()
    bpy.context.view_layer.update()
    o.matrix_world = T(pivot) @ R
    autosmooth(o, 20.0 if flat else 50.0)
    k.link(o, c)
    return o

def wheel(name, loc, R=.5, w=.3, parent=None, c=None, verts=16, m_t=None, m_r=None):
    """Wheel spinning about its local X (axle), origin at the hub."""
    M_ = mats(); m_t = m_t or M_["tire"]; m_r = m_r or M_["rim"]
    rot = (0, math.pi / 2, 0)
    objs = [k.cyl(name + "_t", R, w, loc, m_t, rot=rot, verts=verts, bevel=min(.05, R * .14), seg=2),
            k.cyl(name + "_r", R * .62, w * 1.04, loc, m_r, rot=rot, verts=10),
            k.cyl(name + "_h", R * .24, w * 1.12, loc, M_["dsteel"], rot=rot, verts=8)]
    return part(name, objs, loc, parent, c)

def tracks(p, name, L_, W, H, x, M_, m_frame=None):
    """Crawler undercarriage: two rounded track loops at +-x, sprocket discs, centre frame."""
    for sx in (-1, 1):
        p.append(k.box(name + "_tr", (W, L_, H), (sx * x, 0, H / 2), M_["tire"], bevel=H * .42, seg=3))
        p.append(k.box(name + "_sh", (W * 1.06, L_ * .55, H * .5), (sx * x, 0, H * .5), M_["dsteel"], bevel=.01))
        for sy in (-1, 1):
            p.append(k.cyl(name + "_sp", H * .34, W * 1.1, (sx * x, sy * (L_ / 2 - H * .44), H * .5), M_["dsteel"], rot=(0, math.pi / 2, 0), verts=10))
    p.append(k.box(name + "_frame", (2 * x - W + .02, L_ * .78, H * .55), (0, 0, H * .58), m_frame or M_["dsteel"], bevel=.03, seg=1))

def bucket(name, w, d, h, M_, m, teeth=3):
    """Scoop at the origin: pivot = top-back edge, opening faces +Y, hangs down to -h. Returns objs."""
    t = .06
    objs = [k.box(name + "_back", (w, t, h), (0, t / 2, -h / 2), m, bevel=.01),
            k.box(name + "_bot", (w, d, t), (0, d / 2, -h + t / 2), m, bevel=.01),
            k.box(name + "_sL", (t, d, h), (-w / 2 + t / 2, d / 2, -h / 2), m, bevel=.01),
            k.box(name + "_sR", (t, d, h), (w / 2 - t / 2, d / 2, -h / 2), m, bevel=.01),
            k.box(name + "_lip", (w, .05, .08), (0, d - .02, -h + .04), M_["dsteel"], bevel=.005)]
    for i in range(teeth):
        x = -w / 2 + w * (i + .5) / teeth
        objs.append(k.box(name + "_th", (w / teeth * .32, .16, t * 1.3), (x, d + .06, -h + t / 2), M_["dsteel"], bevel=.005))
    return objs

def beacon(p, name, loc, M_, r=.07, h=.12):
    p.append(k.cyl(name + "_bb", r * 1.2, .03, (loc[0], loc[1], loc[2] + .015), M_["dsteel"], verts=10))
    p.append(k.cyl(name + "_bl", r, h, (loc[0], loc[1], loc[2] + .03 + h / 2), M_["beacon"], verts=10, bevel=.01))

def mirror(p, name, loc, sx, M_, h=.45):
    p.append(k.box(name + "_ma", (.035, .035, h), (loc[0] + sx * .04, loc[1], loc[2]), M_["dsteel"], bevel=0))
    p.append(k.box(name + "_mb", (.10, .18, .28), (loc[0] + sx * .12, loc[1], loc[2] + h * .18), M_["black"], bevel=.01))

def ladder(p, name, x, y, z0, z1, M_, w=.4, step=.3, along='Y'):
    """Ladder on a side face at x (rails along Z), rungs along `along`."""
    for s in (-1, 1):
        if along == 'Y':
            p.append(k.box(name + "_rail", (.04, .04, z1 - z0), (x, y + s * w / 2, (z0 + z1) / 2), M_["dsteel"], bevel=0))
        else:
            p.append(k.box(name + "_rail", (.04, .04, z1 - z0), (x + s * w / 2, y, (z0 + z1) / 2), M_["dsteel"], bevel=0))
    z = z0 + step / 2
    while z < z1 - .05:
        size = (.04, w, .03) if along == 'Y' else (w, .04, .03)
        p.append(k.box(name + "_rung", size, (x, y, z), M_["steel"], bevel=0))
        z += step

def handrail(p, name, pts, z, h, M_, r=.02):
    """Pipe handrail along the polyline pts (x, y) at height z..z+h with a post at each point."""
    for i, (x, y) in enumerate(pts):
        p.append(k.cyl(name + "_post", r, h, (x, y, z + h / 2), M_["steel"], verts=6))
        if i:
            x0, y0 = pts[i - 1]
            p.append(k.tube(name + "_rail", (x0, y0, z + h), (x, y, z + h), r, M_["steel"], verts=6))

def frame(p, name, y0, y1, M_, w=1.0, z=.6):
    for sx in (-1, 1):
        p.append(k.box(name + "_rail", (.12, y1 - y0, .22), (sx * w / 2, (y0 + y1) / 2, z), M_["dsteel"], bevel=.01))
    for yy in (y0 + .4, (y0 + y1) / 2, y1 - .4):
        p.append(k.box(name + "_x", (w, .10, .16), (0, yy, z), M_["dsteel"], bevel=0))

def truck_cab(p, name, y0, y1, w, z0, z1, m_paint, M_, bar=False, stripe=None):
    """Cab-over cab from y0 (back) to y1 (front), floor z0 to roof z1, front faces +Y."""
    L_ = y1 - y0; h = z1 - z0; yc = (y0 + y1) / 2; zc = (z0 + z1) / 2
    p.append(k.box(name + "_cab", (w, L_, h), (0, yc, zc), m_paint, bevel=.10, seg=2))
    p.append(k.box(name + "_ws", (w - .3, .06, h * .42), (0, y1 - .0, z0 + h * .68), M_["glass"], bevel=.01))
    for sx in (-1, 1):
        p.append(k.box(name + "_sw", (.06, L_ * .42, h * .36), (sx * w / 2, y0 + L_ * .60, z0 + h * .66), M_["glass"], bevel=.01))
        mirror(p, name + "_m", (sx * (w / 2 + .10), y1 - .15, z0 + h * .55), sx, M_)
        p.append(k.box(name + "_hl", (.32, .06, .16), (sx * (w / 2 - .32), y1 + .01, z0 + h * .20), M_["light"], bevel=.01))
    p.append(k.box(name + "_grille", (w * .5, .05, h * .16), (0, y1 + .01, z0 + h * .22), M_["black"], bevel=.01))
    p.append(k.box(name + "_bumper", (w + .06, .18, .24), (0, y1 - .05, z0 - .05), M_["dsteel"], bevel=.03))
    p.append(k.box(name + "_ucab", (w - .5, L_ - .2, .55), (0, yc, z0 - .25), M_["dsteel"], bevel=.02))
    if stripe:
        p.append(k.box(name + "_stripe", (w + .02, L_ * .9, .18), (0, yc - .05, z0 + h * .40), stripe, bevel=.005))
    if bar:
        p.append(k.box(name + "_bar", (w * .5, .18, .13), (0, yc, z1 + .07), M_["beacon"], bevel=.02))
        p.append(k.box(name + "_barB", (w * .55, .22, .04), (0, yc, z1 + .01), M_["dsteel"], bevel=0))
    else:
        beacon(p, name, (-w / 2 + .3, yc, z1), M_)

def hook_objs(name, loc, M_, s=1.0):
    """Lifting hook (block + bent hook), hanging from loc (= pivot at the top)."""
    x, y, z = loc
    return [k.box(name + "_blk", (.22 * s, .14 * s, .26 * s), (x, y, z - .13 * s), M_["yellow"], bevel=.02),
            k.cyl(name + "_pin", .05 * s, .25 * s, (x, y, z - .30 * s), M_["dsteel"], verts=8),
            k.box(name + "_h1", (.06 * s, .06 * s, .22 * s), (x, y, z - .48 * s), M_["chrome"], bevel=.01),
            k.box(name + "_h2", (.06 * s, .20 * s, .06 * s), (x, y + .08 * s, z - .60 * s), M_["chrome"], bevel=.01),
            k.box(name + "_h3", (.06 * s, .06 * s, .16 * s), (x, y + .16 * s, z - .52 * s), M_["chrome"], bevel=.01)]

def lattice(name, L_, w0, w1, m, m2, seg=1.0, r=.045):
    """Lattice boom along +Y from the origin, square section tapering w0 -> w1. Returns objs."""
    objs = []
    n = max(2, int(round(L_ / seg)))
    def corner(i, sx, sz):
        t = i / n; w = w0 + (w1 - w0) * t
        return Vector((sx * w / 2, t * L_, sz * w / 2))
    for sx in (-1, 1):
        for sz in (-1, 1):
            objs.append(k.tube(name + "_ch", corner(0, sx, sz), corner(n, sx, sz), r, m, verts=6))
    for i in range(n):
        flip = 1 if i % 2 == 0 else -1
        # top / bottom faces: diagonal between the two x-corners; sides: diagonal between the two z-corners
        for sz in (-1, 1):
            objs.append(k.tube(name + "_br", corner(i, -flip, sz), corner(i + 1, flip, sz), r * .6, m2, verts=4))
        for sx in (-1, 1):
            objs.append(k.tube(name + "_br", corner(i, sx, -flip), corner(i + 1, sx, flip), r * .6, m2, verts=4))
        if i % 2 == 0:
            for sz in (-1, 1):
                objs.append(k.tube(name + "_st", corner(i, -1, sz), corner(i, 1, sz), r * .6, m2, verts=4))
    return objs

def cabin_house(p, name, loc, size, m, M_, front=True, left=True, right=True, back=False, beac=True):
    """Operator cab (box with windows) centred at loc (x, y, z-centre)."""
    w, d, h = size; x, y, z = loc
    p.append(k.box(name + "_cab", size, loc, m, bevel=.06, seg=2))
    if front: p.append(k.box(name + "_wF", (w - .16, .05, h * .62), (x, y + d / 2, z + h * .12), M_["glass"], bevel=.01))
    if back: p.append(k.box(name + "_wB", (w - .16, .05, h * .45), (x, y - d / 2, z + h * .15), M_["glass"], bevel=.01))
    if left: p.append(k.box(name + "_wL", (.05, d - .20, h * .58), (x - w / 2, y, z + h * .12), M_["glass"], bevel=.01))
    if right: p.append(k.box(name + "_wR", (.05, d * .5, h * .5), (x + w / 2, y + d * .1, z + h * .15), M_["glass"], bevel=.01))
    if beac: beacon(p, name, (x, y - d * .2, z + h / 2), M_)
    mirror(p, name + "_m", (x - w / 2 - .06, y + d / 2 - .1, z + h * .2), -1, M_, h=.35)

# ================================================================== builders
def build_excavator(name="Works_MiniExcavator", s=1.0, big=False):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    Y, D, G, H, B = M_["yellow"], M_["dsteel"], M_["glass"], M_["hazard"], M_["black"]
    p = []
    tracks(p, N + "tr", 1.9 * s, .32 * s, .42 * s, .62 * s, M_)
    p.append(k.cyl(N + "tt", .55 * s, .12 * s, (0, 0, .50 * s), D, verts=20, bevel=.01))
    if big:
        for sx in (-1, 1):   # track-frame steps + ladder
            p.append(k.box(N + "stp", (.5, .6, .06), (sx * .74 * s, .3 * s, .62 * s), D, bevel=0))
        ladder(p, N + "lad", -.80 * s - .02, .1 * s, .25 * s, .78 * s, M_, w=.4, step=.25)
    else:
        p.append(k.box(N + "blade", (1.55, .08, .40), (0, 1.08, .24), Y, bevel=.02, seg=2))
        p.append(k.box(N + "bladeTop", (1.55, .14, .06), (0, 1.03, .45), Y, bevel=.01))
        p.append(k.box(N + "bladeEdge", (1.57, .03, .07), (0, 1.11, .05), D, bevel=0))
        for sx in (-1, 1):
            p.append(k.box(N + "bArm", (.07, .5, .08), (sx * .45, .82, .30), D, bevel=.005))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    # ---- Cab (yaw about the turntable centre)
    zt = .55 * s
    p = [k.box(N + "deck", (1.35 * s, 2.0 * s, .16 * s), (0, -.15 * s, .64 * s), Y, bevel=.03 * s, seg=2),
         k.box(N + "cw", (1.35 * s, .75 * s, .62 * s), (0, -.78 * s, 1.02 * s), B if big else Y, bevel=.10 * s, seg=2),
         k.box(N + "cwStripe", (1.2 * s, .04, .14 * s), (0, -1.16 * s, .88 * s), H, bevel=0),
         k.box(N + "eng", (.55 * s, .9 * s, .55 * s), (.38 * s, -.15 * s, 1.0 * s), Y, bevel=.05 * s, seg=2),
         k.cyl(N + "exh", .035 * s, .28 * s, (.5 * s, -.45 * s, 1.40 * s), D, verts=8),
         k.box(N + "bfoot", (.30 * s, .32 * s, .34 * s), (.30 * s, .42 * s, .92 * s), D, bevel=.02)]
    cabin_house(p, N + "cab", (-.30 * s, .25 * s, 1.35 * s), (.78 * s, 1.0 * s, 1.25 * s), Y, M_, back=True)
    if big:
        p.append(k.box(N + "cwTop", (1.35 * s, .75 * s, .10 * s), (0, -.78 * s, 1.36 * s), Y, bevel=.02, seg=1))
        handrail(p, N + "hr", [(.62 * s, -1.1 * s), (.62 * s, -.5 * s), (.62 * s, .25 * s)], 1.28 * s, .45, M_)
        handrail(p, N + "hr2", [(-.62 * s, -1.1 * s), (-.62 * s, -.35 * s)], 1.28 * s, .45, M_)
        p.append(k.box(N + "vent", (.35 * s, .5 * s, .04), (.42 * s, -.2 * s, 1.28 * s), B, bevel=0))
    cab = part(N + "Cab", p, (0, 0, zt), body, c)
    # ---- Boom (pitch at the foot), Arm, Bucket
    F = Vector((.30, .45, 1.00)) * s; K = Vector((.30, 1.05, 2.00)) * s; Tp = Vector((.30, 1.65, 1.90)) * s
    A = Tp + Vector((0, .55, -1.15)) * s
    p = [beam(N + "b1", F - (K - F).normalized() * .08 * s, K, .22 * s, .30 * s, Y, bevel=.02 * s, seg=2),
         beam(N + "b2", K, Tp, .22 * s, .26 * s, Y, bevel=.02 * s, seg=2),
         k.box(N + "knee", (.24 * s, .36 * s, .36 * s), K, Y, bevel=.03 * s, seg=2),
         k.cyl(N + "pinF", .06 * s, .40 * s, F, D, rot=(0, math.pi / 2, 0), verts=8)]
    p += ram_along(N + "ram1", F, K, .05, .62, -.21 * s, .05 * s, D, M_["chrome"])
    p += ram_along(N + "ram2", K, Tp, .02, .90, .19 * s, .045 * s, D, M_["chrome"])
    if big:
        p.append(k.box(N + "bStripe", (.23 * s, .04, .2 * s), K + Vector((0, .19 * s, -.05 * s)), H, bevel=0))
    boom = part(N + "Boom", p, F, cab, c)
    p = [beam(N + "arm", Tp + (Tp - A).normalized() * .12 * s, A, .18 * s, .24 * s, Y, bevel=.02 * s, seg=2),
         k.cyl(N + "pinT", .05 * s, .30 * s, Tp, D, rot=(0, math.pi / 2, 0), verts=8)]
    p += ram_along(N + "ram3", Tp, A, .08, .72, .17 * s, .04 * s, D, M_["chrome"])
    arm = part(N + "Arm", p, Tp, boom, c)
    bk = bucket(N + "bk", .62 * s, .50 * s, .46 * s, M_, Y, teeth=3 if not big else 4)
    place(bk, T(A) @ Rx(-35) @ Rz(180))
    part(N + "Bucket", bk, A, arm, c)
    return stats(name)

def build_skid_loader(name="Works_SkidLoader"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    Wt, D, G, H, B = M_["white"], M_["dsteel"], M_["glass"], M_["hazard"], M_["black"]
    p = [k.box(N + "chassis", (1.25, 1.75, .40), (0, -.05, .38), D, bevel=.03),
         k.box(N + "body", (1.40, 1.95, .70), (0, -.15, .85), Wt, bevel=.06, seg=2),
         k.box(N + "engDoor", (1.0, .05, .5), (0, -1.13, .85), H, bevel=0),
         k.box(N + "roof", (1.0, 1.05, .08), (0, .15, 2.02), Wt, bevel=.02),
         k.cyl(N + "exh", .035, .25, (.45, -.9, 1.3), D, verts=8)]
    # cab cage: four posts + glass panels + seat
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(k.box(N + "post", (.07, .07, .85), (sx * .47, .15 + sy * .5, 1.6), B, bevel=0))
        p.append(k.box(N + "wS", (.03, .9, .7), (sx * .47, .15, 1.6), G, bevel=0))
        p.append(k.box(N + "tower", (.22, .40, 1.2), (sx * .70, -.92, 1.35), Wt, bevel=.03, seg=2))
    p.append(k.box(N + "wF", (.85, .03, .7), (0, .66, 1.6), G, bevel=0))
    p.append(k.box(N + "seat", (.45, .45, .5), (0, -.1, 1.4), M_["seat"], bevel=.03))
    beacon(p, N, (-.3, .0, 2.06), M_)
    mirror(p, N + "_m", (-.56, .55, 1.75), -1, M_, h=.3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(k.cyl(N + "wh", .33, .26, (sx * .76, sy * .6, .33), M_["tire"], rot=(0, math.pi / 2, 0), verts=14, bevel=.04, seg=2))
            p.append(k.cyl(N + "rim", .19, .28, (sx * .76, sy * .6, .33), M_["rim"], rot=(0, math.pi / 2, 0), verts=10))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    P = Vector((0, -.95, 1.88))
    p = [k.cyl(N + "pin", .06, 1.7, P, D, rot=(0, math.pi / 2, 0), verts=8)]
    for sx in (-1, 1):
        a = Vector((sx * .80, -.95, 1.88)); b = Vector((sx * .80, 1.45, .62))
        p.append(beam(N + "armL", a, b, .14, .20, Wt, bevel=.015, seg=2))
        p += ram(N + "ram", (sx * .80, -.55, 1.0), (sx * .80, .55, 1.0), .04, D, M_["chrome"])
    p.append(k.box(N + "cross", (1.70, .14, .16), (0, 1.40, .66), Wt, bevel=.015))
    arms = part(N + "Arms", p, P, body, c)
    Pb = Vector((0, 1.52, .60))
    bk = bucket(N + "bk", 1.75, .70, .55, M_, Wt, teeth=5)
    place(bk, T(Pb) @ Rx(12))
    part(N + "Bucket", bk, Pb, arms, c)
    return stats(name)

def build_dump_truck(name="Works_DumpTruck"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    O, D, S, H = M_["orange"], M_["dsteel"], M_["steel"], M_["hazard"]
    p = []
    frame(p, N + "fr", -3.55, 3.3, M_, w=1.0, z=.62)
    truck_cab(p, N + "cab", 1.55, 3.55, 2.3, 1.05, 2.75, O, M_)
    p.append(k.cyl(N + "tank", .30, 1.1, (-1.05, .5, .72), S, rot=(math.pi / 2, 0, 0), verts=12, bevel=.02))
    p.append(k.box(N + "box", (.5, .8, .5), (1.05, .6, .75), D, bevel=.02))
    p.append(k.cyl(N + "exh", .07, 1.5, (1.18, 1.45, 1.75), D, verts=8))
    for sx in (-1, 1):
        p.append(k.box(N + "mud", (.62, 1.9, .08), (sx * 1.02, -1.25, 1.08), D, bevel=.01))
    p.append(k.box(N + "rearStripe", (2.2, .05, .22), (0, -3.58, .62), H, bevel=0))
    for sx in (-1, 1):
        p.append(k.box(N + "tl", (.22, .05, .12), (sx * .9, -3.59, .80), M_["tail"], bevel=0))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    ws = [(-1.0, 2.3, .34), (1.0, 2.3, .34), (-1.0, -.55, .5), (1.0, -.55, .5), (-1.0, -1.95, .5), (1.0, -1.95, .5)]
    for i, (x, y, w) in enumerate(ws):
        wheel(N + f"Wheel_{i}", (x, y, .5), .5, w, body, c)
    y0, y1, zb = -3.45, 1.25, 1.12
    p = [k.box(N + "floor", (2.3, y1 - y0, .12), (0, (y0 + y1) / 2, zb + .06), S, bevel=.02),
         k.box(N + "front", (2.3, .08, 1.35), (0, y1 - .04, zb + .68), S, bevel=.02, seg=2),
         k.box(N + "guard", (2.3, 1.0, .08), (0, y1 + .45, zb + 1.38), S, bevel=.02),
         k.box(N + "tail", (2.3, .08, 1.0), (0, y0 + .04, zb + .55), S, bevel=.02, seg=2),
         k.box(N + "tailStripe", (2.0, .04, .18), (0, y0 - .01, zb + .35), H, bevel=0),
         k.box(N + "load", (2.1, 4.3, .5), (0, (y0 + y1) / 2 + .1, zb + .95), M_["dirt"], bevel=.14, seg=2)]
    for sx in (-1, 1):
        p.append(k.box(N + "side", (.08, y1 - y0, 1.1), (sx * 1.11, (y0 + y1) / 2, zb + .60), S, bevel=.02, seg=2))
        for yy in (-2.5, -1.3, -.1, 1.0):
            p.append(k.box(N + "rib", (.06, .12, 1.1), (sx * 1.18, yy, zb + .60), O, bevel=.005))
        p.append(k.box(N + "toprail", (.12, y1 - y0, .08), (sx * 1.13, (y0 + y1) / 2, zb + 1.16), O, bevel=.01))
    p += ram(N + "ram", (0, .55, .75), (0, -.5, zb), .11, D, M_["chrome"])
    part(N + "Bed", p, (0, -3.35, zb), body, c)
    return stats(name)

def build_tow_truck(name="Works_TowTruck"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    R, D, S, H = M_["red"], M_["dsteel"], M_["steel"], M_["hazard"]
    p = []
    frame(p, N + "fr", -3.2, 3.1, M_, w=1.0, z=.58)
    truck_cab(p, N + "cab", 1.35, 3.25, 2.15, .95, 2.45, R, M_, bar=True)
    p.append(k.cyl(N + "tank", .26, .9, (-1.0, .4, .65), S, rot=(math.pi / 2, 0, 0), verts=12, bevel=.02))
    p.append(k.box(N + "box", (.5, .7, .45), (1.0, .5, .68), D, bevel=.02))
    p.append(k.box(N + "rearStripe", (2.1, .05, .2), (0, -3.22, .55), H, bevel=0))
    for sx in (-1, 1):
        p.append(k.box(N + "mud", (.55, 1.3, .07), (sx * 1.0, -1.4, 1.0), D, bevel=.01))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    ws = [(-1.0, 2.1, .32), (1.0, 2.1, .32), (-1.0, -1.4, .48), (1.0, -1.4, .48)]
    for i, (x, y, w) in enumerate(ws):
        wheel(N + f"Wheel_{i}", (x, y, .45), .45, w, body, c)
    y0, y1, zb = -3.3, 1.15, 1.02
    p = [k.box(N + "deck", (2.2, y1 - y0, .12), (0, (y0 + y1) / 2, zb + .06), S, bevel=.02),
         k.box(N + "head", (2.2, .10, .55), (0, y1 - .05, zb + .38), R, bevel=.02, seg=2),
         k.cyl(N + "winch", .13, .8, (0, y1 - .32, zb + .33), D, rot=(0, math.pi / 2, 0), verts=12, bevel=.01),
         k.box(N + "winchF", (1.0, .3, .08), (0, y1 - .32, zb + .12), D, bevel=.01),
         k.box(N + "rampStripe", (2.2, .25, .06), (0, y0 + .12, zb + .09), H, bevel=0),
         k.box(N + "deckStripe", (.25, y1 - y0 - .6, .02), (0, (y0 + y1) / 2 - .1, zb + .125), H, bevel=0)]
    for sx in (-1, 1):
        p.append(k.box(N + "rail", (.08, y1 - y0, .10), (sx * 1.06, (y0 + y1) / 2, zb + .14), R, bevel=.01))
        for yy in (-2.6, -1.4, -.2, 1.0):
            p.append(k.cyl(N + "post", .025, .4, (sx * 1.06, yy, zb + .3), M_["steel"], verts=6))
    part(N + "Bed", p, (0, -3.15, zb), body, c)
    part(N + "Hook", hook_objs(N + "hk", (0, -2.9, zb + .62), M_, .9), (0, -2.9, zb + .62), None, c)
    return stats(name)

def build_crane_truck(name="Works_CraneTruck"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    Bl, Y, D, S, H = M_["blue"], M_["yellow"], M_["dsteel"], M_["steel"], M_["hazard"]
    p = []
    frame(p, N + "fr", -4.0, 3.8, M_, w=1.0, z=.62)
    truck_cab(p, N + "cab", 2.05, 4.0, 2.3, 1.05, 2.75, Bl, M_)
    p.append(k.cyl(N + "tank", .30, 1.1, (-1.05, 1.1, .72), S, rot=(math.pi / 2, 0, 0), verts=12, bevel=.02))
    p.append(k.cyl(N + "exh", .07, 1.5, (1.18, 1.95, 1.75), D, verts=8))
    p.append(k.box(N + "deck", (2.4, 5.0, .14), (0, -1.45, 1.10), S, bevel=.02, seg=2))
    p.append(k.box(N + "deckW", (2.4, 5.0, .04), (0, -1.45, 1.19), M_["wood"], bevel=0))
    for sx in (-1, 1):
        p.append(k.box(N + "mud", (.62, 2.9, .08), (sx * 1.02, -1.55, 1.0), D, bevel=.01))
        p.append(k.box(N + "stake", (.08, .08, .5), (sx * 1.15, -3.85, 1.45), S, bevel=0))
        p.append(k.box(N + "stake", (.08, .08, .5), (sx * 1.15, .6, 1.45), S, bevel=0))
        # outriggers (hazard legs with pads) beside the crane base
        p.append(k.box(N + "outr", (.3, .28, .28), (sx * 1.5, 1.45, .85), H, bevel=.01))
        p.append(k.box(N + "outrLeg", (.14, .14, .5), (sx * 1.5, 1.45, .5), D, bevel=0))
        p.append(k.box(N + "outrPad", (.4, .4, .08), (sx * 1.5, 1.45, .05), D, bevel=.01))
    p.append(k.box(N + "outrBeam", (3.2, .28, .28), (0, 1.45, .85), H, bevel=.01))
    p.append(k.box(N + "rearStripe", (2.2, .05, .22), (0, -4.02, .62), H, bevel=0))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    ws = [(-1.0, 2.9, .34), (1.0, 2.9, .34), (-1.0, -.9, .5), (1.0, -.9, .5), (-1.0, -2.25, .5), (1.0, -2.25, .5)]
    for i, (x, y, w) in enumerate(ws):
        wheel(N + f"Wheel_{i}", (x, y, .5), .5, w, body, c)
    Pb = Vector((0, 1.45, 1.17)); Pa = Vector((0, 1.45, 2.25))
    p = [k.cyl(N + "base", .50, .22, Pb + Vector((0, 0, .11)), D, verts=16, bevel=.02),
         k.box(N + "col", (.60, .60, .80), Pb + Vector((0, 0, .62)), Y, bevel=.04, seg=2),
         k.box(N + "colStripe", (.62, .62, .12), Pb + Vector((0, 0, .35)), H, bevel=0),
         k.box(N + "knuckle", (.44, .5, .5), Pa + Vector((0, 0, .02)), Y, bevel=.04, seg=2)]
    base = part(N + "CraneBase", p, Pb, body, c)
    ang = 15.0; Lb = 3.9
    tip = Pa + Vector((0, -Lb * math.cos(rad(ang)), Lb * math.sin(rad(ang))))
    p = [beam(N + "a1", Pa, Pa.lerp(tip, .55), .34, .38, Y, bevel=.025, seg=2),
         beam(N + "a2", Pa.lerp(tip, .45), tip, .26, .30, Y, bevel=.02, seg=2),
         k.cyl(N + "pin", .07, .5, Pa, D, rot=(0, math.pi / 2, 0), verts=8)]
    p += ram(N + "ram", Pb + Vector((0, -.6, .45)), Pa.lerp(tip, .4) + Vector((0, 0, -.25)), .07, D, M_["chrome"])
    stripe = beam(N + "tipStripe", Pa.lerp(tip, .85), Pa.lerp(tip, .97), .27, .31, H, bevel=0)
    p.append(stripe)
    arm = part(N + "CraneArm", p, Pa, base, c)
    p = [k.box(N + "sheave", (.22, .36, .30), tip + Vector((0, -.05, -.02)), D, bevel=.02),
         k.cyl(N + "pulley", .12, .26, tip + Vector((0, -.12, -.1)), M_["steel"], rot=(0, math.pi / 2, 0), verts=10)]
    part(N + "CraneTip", p, tip, arm, c)
    hp = (0, tip.y, 1.95)
    part(N + "Hook", hook_objs(N + "hk", hp, M_, 1.0), hp, None, c)
    return stats(name)

def build_wrecking_crane(name="Works_WreckingCrane"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    Y, D, S, H, B, G = M_["yellow"], M_["dsteel"], M_["steel"], M_["hazard"], M_["black"], M_["glass"]
    p = []
    tracks(p, N + "tr", 6.0, .9, 1.0, 1.55, M_)
    p.append(k.cyl(N + "tt", 1.6, .2, (0, 0, 1.08), D, verts=24, bevel=.02))
    for sx in (-1, 1):
        p.append(k.box(N + "stp", (.6, 1.2, .08), (sx * 1.0, .8, 1.04), D, bevel=0))
    ladder(p, N + "lad", -2.02, .5, .3, 1.1, M_, w=.5, step=.3)
    body = part(N + "Body", p, (0, 0, 0), None, c)
    zt = 1.18
    p = [k.box(N + "deck", (3.4, 4.9, .25), (0, -.8, 1.30), Y, bevel=.04, seg=2),
         k.box(N + "house", (3.3, 3.2, 1.7), (0, -.9, 2.25), Y, bevel=.10, seg=2),
         k.box(N + "cw", (3.3, 1.2, 1.4), (0, -3.05, 2.1), B, bevel=.10, seg=2),
         k.box(N + "cwStripe", (3.0, .05, .28), (0, -3.66, 1.9), H, bevel=0),
         k.box(N + "vent", (1.0, 1.4, .05), (.8, -1.3, 3.12), B, bevel=0),
         k.cyl(N + "exh", .09, .9, (1.2, -2.2, 3.45), D, verts=8),
         k.box(N + "bfoot", (1.1, .8, .55), (0, .95, 1.65), D, bevel=.03),
         k.box(N + "drum", (1.2, .9, .9), (.0, -2.1, 3.5), D, bevel=.05, seg=2)]
    # A-frame gantry
    for sx in (-1, 1):
        p.append(k.tube(N + "gant", (sx * 1.1, -2.6, 3.1), (sx * .5, -1.6, 5.2), .07, S, verts=6))
        p.append(k.tube(N + "gant2", (sx * 1.1, -.6, 3.1), (sx * .5, -1.6, 5.2), .07, S, verts=6))
    p.append(k.tube(N + "gantX", (-.5, -1.6, 5.2), (.5, -1.6, 5.2), .08, S, verts=6))
    handrail(p, N + "hr", [(1.6, -3.5), (1.6, -1.0), (1.6, .5), (-.5, .5)], 3.12, .5, M_)
    cabin_house(p, N + "cab", (-1.1, 1.1, 2.15), (1.1, 1.6, 1.5), Y, M_, back=False)
    ladder(p, N + "lad2", 1.67, -2.0, 1.45, 3.1, M_, w=.5, step=.3)
    cab = part(N + "Cab", p, (0, 0, zt), body, c)
    F = Vector((0, .95, 1.95)); ang = 62.0; Lb = 14.0
    tip = F + Vector((0, Lb * math.cos(rad(ang)), Lb * math.sin(rad(ang))))
    lat = lattice(N + "lat", Lb, .95, .55, Y, S, seg=1.0, r=.05)
    lat.append(k.box(N + "foot", (1.0, .5, .6), (0, .2, 0), D, bevel=.03))
    lat.append(k.cyl(N + "pin", .09, 1.2, (0, 0, 0), D, rot=(0, math.pi / 2, 0), verts=8))
    place(lat, T(F) @ Rx(ang))
    boom = part(N + "Boom", lat, F, cab, c)
    p = [k.box(N + "sheave", (.5, .5, .4), tip + Vector((0, .05, .0)), D, bevel=.03),
         k.cyl(N + "pulley", .22, .3, tip + Vector((0, .25, -.05)), S, rot=(0, math.pi / 2, 0), verts=12)]
    part(N + "BoomTip", p, tip, boom, c)
    bp = (0, tip.y, 1.3)
    p = [k.ball(N + "ball", .62, bp, D, sub=2), k.cyl(N + "lug", .10, .3, (bp[0], bp[1], bp[2] + .65), D, verts=8),
         k.cyl(N + "band", .64, .18, bp, B, verts=18)]
    part(N + "Ball", p, bp, None, c)
    return stats(name)

def build_pickup(name="Works_Pickup"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    Wt, D, G, B = M_["white"], M_["dsteel"], M_["glass"], M_["black"]
    p = [k.box(N + "chassis", (1.6, 4.4, .25), (0, 0, .50), D, bevel=.02),
         k.box(N + "hood", (1.80, 1.45, .55), (0, 1.75, .86), Wt, bevel=.08, seg=2),
         k.box(N + "cab", (1.78, 1.55, .80), (0, .40, 1.50), Wt, bevel=.09, seg=2),
         k.box(N + "ws", (1.5, .06, .62), (0, 1.12, 1.52), G, bevel=.01, rot=(rad(-28), 0, 0)),
         k.box(N + "rw", (1.4, .05, .5), (0, -.36, 1.52), G, bevel=.01),
         k.box(N + "bedFloor", (1.80, 2.2, .08), (0, -1.40, .90), Wt, bevel=.01),
         k.box(N + "bedFront", (1.80, .06, .55), (0, -.35, 1.18), Wt, bevel=.01),
         k.box(N + "tailgate", (1.80, .06, .55), (0, -2.47, 1.18), Wt, bevel=.01),
         k.box(N + "bumpF", (1.85, .18, .20), (0, 2.45, .55), M_["chrome"], bevel=.03),
         k.box(N + "bumpB", (1.85, .16, .20), (0, -2.46, .55), M_["chrome"], bevel=.03),
         k.box(N + "grille", (1.1, .05, .25), (0, 2.48, .80), B, bevel=.01),
         k.box(N + "toolbox", (1.6, .45, .40), (0, -.62, 1.14), M_["orange"], bevel=.02, seg=2),
         k.box(N + "plank", (.16, 2.3, .04), (-.45, -1.5, .98), M_["wood"], bevel=.004, rot=(rad(3), 0, rad(2))),
         k.box(N + "plank2", (.16, 2.0, .04), (-.25, -1.6, 1.02), M_["wood"], bevel=.004, rot=(0, rad(-6), rad(-3))),
         k.box(N + "plank3", (.16, 2.4, .04), (.1, -1.45, 1.00), M_["wood"], bevel=.004, rot=(rad(-4), 0, rad(4))),
         k.box(N + "bag", (.5, .7, .3), (.5, -1.7, 1.08), M_["concrete"], bevel=.06, seg=2, rot=(0, 0, .3))]
    for sx in (-1, 1):
        p.append(k.box(N + "sw", (.05, 1.3, .5), (sx * .89, .40, 1.55), G, bevel=.01))
        p.append(k.box(N + "bedSide", (.06, 2.2, .55), (sx * .87, -1.40, 1.18), Wt, bevel=.01))
        p.append(k.box(N + "hl", (.3, .05, .18), (sx * .6, 2.48, .85), M_["light"], bevel=.01))
        p.append(k.box(N + "tl", (.14, .05, .3), (sx * .8, -2.49, 1.05), M_["tail"], bevel=.01))
        mirror(p, N + "_m", (sx * .95, 1.05, 1.45), sx, M_, h=.2)
        for yy in (1.55, -1.5):
            p.append(k.box(N + "arch", (.3, 1.0, .5), (sx * .80, yy, .62), B, bevel=.04, seg=2))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    for i, (x, y) in enumerate([(-.80, 1.55), (.80, 1.55), (-.80, -1.5), (.80, -1.5)]):
        wheel(N + f"Wheel_{i}", (x, y, .37), .37, .24, body, c, verts=14)
    return stats(name)

def build_forklift(name="Works_Forklift"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    O, D, B, S = M_["orange"], M_["dsteel"], M_["black"], M_["steel"]
    p = [k.box(N + "chassis", (1.10, 1.70, .50), (0, -.30, .50), O, bevel=.05, seg=2),
         k.box(N + "cw", (1.10, .55, .75), (0, -1.0, .72), O, bevel=.08, seg=2),
         k.box(N + "cwStripe", (.9, .04, .16), (0, -1.28, .55), M_["hazard"], bevel=0),
         k.box(N + "floor", (1.0, .9, .06), (0, .0, .78), B, bevel=0),
         k.box(N + "seatB", (.45, .40, .12), (0, -.55, .95), M_["seat"], bevel=.02),
         k.box(N + "seatK", (.45, .10, .45), (0, -.75, 1.2), M_["seat"], bevel=.02),
         k.box(N + "dash", (.9, .25, .4), (0, .35, 1.0), O, bevel=.03),
         k.cyl(N + "col", .025, .4, (0, .2, 1.3), D, rot=(rad(30), 0, 0), verts=6),
         k.cyl(N + "sw", .15, .03, (0, .1, 1.47), B, rot=(rad(30), 0, 0), verts=12),
         k.box(N + "roof", (1.05, 1.25, .05), (0, -.15, 2.05), D, bevel=.01)]
    for sx in (-1, 1):
        for yy in (.4, -.7):
            p.append(k.box(N + "post", (.06, .06, 1.3), (sx * .48, yy, 1.4), D, bevel=0))
    for yy in (-.5, -.2, .1):
        p.append(k.box(N + "roofbar", (1.0, .04, .03), (0, yy, 2.03), D, bevel=0))
    beacon(p, N, (-.35, -.6, 2.08), M_, r=.06)
    for sx in (-1, 1):
        p.append(k.cyl(N + "wh", .28, .22, (sx * .52, .45, .28), M_["tire"], rot=(0, math.pi / 2, 0), verts=14, bevel=.03, seg=2))
        p.append(k.cyl(N + "rim", .16, .24, (sx * .52, .45, .28), M_["rim"], rot=(0, math.pi / 2, 0), verts=10))
        p.append(k.cyl(N + "wh2", .22, .18, (sx * .46, -.85, .22), M_["tire"], rot=(0, math.pi / 2, 0), verts=14, bevel=.03, seg=2))
        p.append(k.cyl(N + "rim2", .12, .20, (sx * .46, -.85, .22), M_["rim"], rot=(0, math.pi / 2, 0), verts=10))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    Pm = Vector((0, .80, .15))
    p = [k.cyl(N + "mpin", .04, 1.0, Pm, D, rot=(0, math.pi / 2, 0), verts=8)]
    for sx in (-1, 1):
        p.append(k.box(N + "upr", (.09, .12, 1.95), (sx * .42, .82, 1.12), D, bevel=.008))
        p.append(k.box(N + "upr2", (.07, .08, 1.5), (sx * .30, .86, 1.2), S, bevel=.006))
    for zz in (.45, 1.25, 2.07):
        p.append(k.box(N + "cross", (.92, .10, .08), (0, .80, zz), D, bevel=.006))
    p += ram(N + "lift", (0, .78, .3), (0, .78, 1.9), .045, D, M_["chrome"])
    mast = part(N + "Mast", p, Pm, body, c)
    Pf = Vector((0, .92, .25))
    p = [k.box(N + "carr", (.95, .06, .50), (0, .93, .52), D, bevel=.006)]
    for sx in (-1, 1):
        p.append(k.box(N + "fv", (.10, .05, .55), (sx * .30, .98, .50), D, bevel=.004))
        p.append(k.box(N + "fh", (.10, .90, .04), (sx * .30, 1.43, .25), D, bevel=.004))
    part(N + "Forks", p, Pf, mast, c)
    return stats(name)

def build_cherry_picker(name="Works_CherryPicker"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    Wt, O, D, S, H = M_["white"], M_["orange"], M_["dsteel"], M_["steel"], M_["hazard"]
    p = []
    frame(p, N + "fr", -3.4, 3.3, M_, w=1.0, z=.58)
    truck_cab(p, N + "cab", 1.55, 3.5, 2.15, .95, 2.45, Wt, M_, bar=True, stripe=O)
    p.append(k.box(N + "lockers", (2.2, 3.6, .55), (0, -1.3, 1.02), Wt, bevel=.04, seg=2))
    p.append(k.box(N + "lockStripe", (2.22, 3.4, .14), (0, -1.3, 1.02), O, bevel=.005))
    p.append(k.box(N + "deck", (2.2, 3.7, .06), (0, -1.3, 1.32), D, bevel=.01))
    for sx in (-1, 1):
        for yy in (-2.9, .2):
            p.append(k.box(N + "outr", (.3, .26, .26), (sx * 1.25, yy, .82), H, bevel=.01))
            p.append(k.box(N + "outrLeg", (.12, .12, .55), (sx * 1.25, yy, .4), D, bevel=0))
            p.append(k.box(N + "outrPad", (.38, .38, .08), (sx * 1.25, yy, .06), D, bevel=.01))
        p.append(k.box(N + "mud", (.55, 1.4, .07), (sx * .98, -1.55, .98), D, bevel=.01))
    for yy in (-2.9, .2):
        p.append(k.box(N + "outrBeam", (2.6, .26, .26), (0, yy, .82), H, bevel=.01))
    p.append(k.box(N + "rearStripe", (2.1, .05, .2), (0, -3.42, .55), H, bevel=0))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    ws = [(-.97, 2.5, .32), (.97, 2.5, .32), (-.97, -1.55, .46), (.97, -1.55, .46)]
    for i, (x, y, w) in enumerate(ws):
        wheel(N + f"Wheel_{i}", (x, y, .45), .45, w, body, c)
    Pt = Vector((0, -1.3, 1.35)); P1 = Vector((0, -1.3, 2.05))
    p = [k.cyl(N + "ring", .55, .18, Pt + Vector((0, 0, .09)), D, verts=18, bevel=.02),
         k.box(N + "ped", (.7, .9, .55), Pt + Vector((0, 0, .42)), O, bevel=.04, seg=2),
         k.box(N + "pedStripe", (.72, .92, .10), Pt + Vector((0, 0, .32)), H, bevel=0)]
    tur = part(N + "Turret", p, Pt, body, c)
    a1, L1 = 28.0, 3.0
    K = P1 + Vector((0, L1 * math.cos(rad(a1)), L1 * math.sin(rad(a1))))
    p = [beam(N + "a1", P1 - (K - P1).normalized() * .15, K, .34, .36, O, bevel=.025, seg=2),
         k.cyl(N + "pin1", .07, .5, P1, D, rot=(0, math.pi / 2, 0), verts=8),
         beam(N + "a1s", P1.lerp(K, .8), P1.lerp(K, .92), .35, .37, H, bevel=0)]
    p += ram(N + "ram1", Pt + Vector((0, .5, .5)), P1.lerp(K, .5) + Vector((0, .1, -.22)), .07, D, M_["chrome"])
    arm1 = part(N + "Arm1", p, P1, tur, c)
    a2, L2 = 5.0, 1.7
    Tp = K + Vector((0, L2 * math.cos(rad(a2)), L2 * math.sin(rad(a2))))
    p = [beam(N + "a2", K - (Tp - K).normalized() * .2, Tp, .26, .28, O, bevel=.02, seg=2),
         k.box(N + "knee", (.40, .45, .45), K, O, bevel=.04, seg=2),
         k.cyl(N + "pin2", .06, .44, K, D, rot=(0, math.pi / 2, 0), verts=8)]
    p += ram(N + "ram2", P1.lerp(K, .55) + Vector((0, 0, .25)), K.lerp(Tp, .35) + Vector((0, 0, .18)), .05, D, M_["chrome"])
    arm2 = part(N + "Arm2", p, K, arm1, c)
    bw, bd, bh = 1.05, .85, .95
    bc = Tp + Vector((0, .15 + bd / 2, -.55))
    p = [k.box(N + "bfloor", (bw, bd, .06), (bc.x, bc.y, bc.z - bh / 2 + .03), D, bevel=.01),
         k.box(N + "bmount", (.3, .25, .5), Tp + Vector((0, .05, -.3)), D, bevel=.02),
         k.cyl(N + "pin3", .05, .36, Tp, D, rot=(0, math.pi / 2, 0), verts=8)]
    for sx in (-1, 1):
        p.append(k.box(N + "bw", (.06, bd, bh), (bc.x + sx * (bw / 2 - .03), bc.y, bc.z), Wt, bevel=.01))
    for sy in (-1, 1):
        p.append(k.box(N + "bw2", (bw, .06, bh), (bc.x, bc.y + sy * (bd / 2 - .03), bc.z), Wt, bevel=.01))
    p.append(k.box(N + "brail", (bw + .06, bd + .06, .06), (bc.x, bc.y, bc.z + bh / 2 - .03), O, bevel=.01))
    p.append(k.box(N + "bstripe", (bw + .02, .04, .18), (bc.x, bc.y + bd / 2, bc.z - .1), H, bevel=0))
    part(N + "Basket", p, Tp, arm2, c)
    return stats(name)

def build_cement_mixer(name="Works_CementMixer"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    O, D, S, B = M_["orange"], M_["dsteel"], M_["steel"], M_["black"]
    p = [k.box(N + "base", (.95, .10, .07), (0, -.30, .22), D, bevel=.005),
         k.cyl(N + "axle", .025, 1.1, (0, -.30, .20), D, rot=(0, math.pi / 2, 0), verts=6),
         k.box(N + "motor", (.34, .30, .30), (-.28, -.05, .42), B, bevel=.02, seg=2),
         k.box(N + "motorT", (.30, .20, .06), (-.28, -.05, .60), O, bevel=.01),
         k.box(N + "handle", (.05, .55, .04), (.0, -.78, .34), D, bevel=.005, rot=(rad(-25), 0, 0)),
         k.box(N + "grip", (.40, .05, .05), (.0, -1.02, .45), B, bevel=.01),
         k.cyl(N + "wheelC", .10, .22, (0, .05, .78), D, rot=(rad(50), 0, 0), verts=12),
         k.box(N + "crossT", (.9, .06, .06), (0, .05, .78), D, bevel=.005)]
    for sx in (-1, 1):
        p.append(k.tube(N + "leg", (sx * .42, -.30, .20), (sx * .42, .05, .78), .025, D, verts=6))
        p.append(k.tube(N + "leg2", (sx * .36, .40, .02), (sx * .42, .05, .78), .025, D, verts=6))
        p.append(k.box(N + "foot", (.12, .12, .04), (sx * .36, .40, .02), D, bevel=.005))
        p.append(k.cyl(N + "wh", .20, .08, (sx * .52, -.30, .20), M_["tire"], rot=(0, math.pi / 2, 0), verts=14, bevel=.02, seg=2))
        p.append(k.cyl(N + "rim", .11, .09, (sx * .52, -.30, .20), M_["rim"], rot=(0, math.pi / 2, 0), verts=10))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    Pd = Vector((0, .05, .78)); tilt = 50.0
    rotY = (-math.pi / 2, 0, 0)   # cylinder depth along +Y
    p = [k.cyl(N + "drum", .36, .50, (0, .05, 0), O, rot=rotY, verts=18, bevel=.02, seg=2),
         k.cyl(N + "cone", .36, .22, (0, .41, 0), O, rot=rotY, verts=18, r2=.24),
         k.cyl(N + "back", .18, .20, (0, -.30, 0), O, rot=rotY, verts=18, r2=.36),
         k.cyl(N + "rim", .26, .05, (0, .54, 0), D, rot=rotY, verts=18),
         k.cyl(N + "mouth", .22, .02, (0, .55, 0), B, rot=rotY, verts=18),
         k.cyl(N + "band", .375, .07, (0, .05, 0), D, rot=rotY, verts=18),
         k.cyl(N + "gear", .40, .06, (0, -.17, 0), D, rot=rotY, verts=24)]
    place(p, T(Pd) @ Rx(tilt))
    part(N + "Drum", p, Pd, body, c, rot=(rad(tilt), 0, 0))
    return stats(name)

def build_dumpster(name="Works_Dumpster"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    Y, D, H = M_["yellow"], M_["dsteel"], M_["hazard"]
    zf, zt = .15, 1.30
    p = [k.box(N + "floor", (1.80, 3.0, .08), (0, 0, zf + .04), Y, bevel=.01),
         beam(N + "endF", (0, 1.50, zf), (0, 1.80, zt), 1.90, .06, Y, bevel=.01),
         beam(N + "endB", (0, -1.50, zf), (0, -1.80, zt), 1.90, .06, Y, bevel=.01),
         beam(N + "hzF", (0, 1.58, .45), (0, 1.66, .78), 1.4, .04, H, bevel=0),
         beam(N + "hzB", (0, -1.58, .45), (0, -1.66, .78), 1.4, .04, H, bevel=0),
         k.box(N + "railF", (1.98, .09, .09), (0, 1.80, zt + .02), D, bevel=.01),
         k.box(N + "railB", (1.98, .09, .09), (0, -1.80, zt + .02), D, bevel=.01)]
    for sx in (-1, 1):
        o = L.poly_prism(N + "side", [(-1.5, zf), (1.5, zf), (1.8, zt), (-1.8, zt)], .06, (sx * .92, 0, 0), Y, axis='X')
        p.append(o)
        p.append(k.box(N + "railS", (.09, 3.62, .09), (sx * .95, 0, zt + .02), D, bevel=.01))
        p.append(k.box(N + "skid", (.12, 3.0, .15), (sx * .78, 0, .075), D, bevel=.01))
        for yy in (-.9, .9):
            p.append(k.box(N + "lug", (.10, .25, .24), (sx * 1.0, yy, zt - .12), D, bevel=.01))
            p.append(k.box(N + "rib", (.05, .10, 1.0), (sx * .97, yy * .4, .70), D, bevel=.005))
    body = part(N + "Body", p, (0, 0, 0), None, c)
    rnd = random.Random(7)
    Pf = (0, 0, zf + .08)
    p = [k.ball(N + "mound", 1.0, (0, 0, zf + .10), M_["rubble"], sub=2, scale=(.82, 1.45, .62))]
    for i in range(14):
        x, y = rnd.uniform(-.65, .65), rnd.uniform(-1.3, 1.3)
        z = zf + .1 + .58 * max(0.0, 1 - (x / .8) ** 2 - (y / 1.45) ** 2) ** .5 * .9
        m = [M_["concrete"], M_["brickR"], M_["rubble"]][i % 3]
        if i % 4 == 3:
            p.append(k.box(N + "chunk", (.22, .11, .07), (x, y, max(z, zf + .15)), M_["brickR"], rot=(rnd.uniform(0, .6), rnd.uniform(0, .6), rnd.uniform(0, 6)), bevel=.006))
        else:
            p.append(L.chunk(N + "chunk", (x, y, max(z, zf + .15)), m, s=rnd.uniform(.16, .28), seed=i))
    p.append(k.box(N + "plank", (.14, 1.7, .04), (.3, -.2, zf + .62), M_["wood"], bevel=.004, rot=(rad(14), 0, rad(15))))
    p.append(k.cyl(N + "pipe", .05, 1.1, (-.3, .5, zf + .55), D, rot=(rad(80), 0, rad(20)), verts=8))
    for o in p:
        if o.name.startswith(N + "mound"):
            for pg in o.data.polygons: pg.use_smooth = False
    part(N + "Fill", p, Pf, body, c)
    return stats(name)

def build_container(name="Works_Container"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    CY, CX, CF, D = M_["contY"], M_["contX"], M_["contFlat"], M_["dsteel"]
    W, Ln, Hh = 2.44, 6.06, 2.60
    p = [k.box(N + "roof", (W - .1, Ln - .1, .05), (0, 0, Hh - .04), CF, bevel=0),
         k.box(N + "floor", (W - .1, Ln - .1, .14), (0, 0, .10), D, bevel=.01),
         k.box(N + "endF", (W - .2, .06, Hh - .3), (0, Ln / 2 - .05, Hh / 2), CX, bevel=0)]
    for sx in (-1, 1):
        p.append(k.box(N + "side", (.06, Ln - .2, Hh - .3), (sx * (W / 2 - .05), 0, Hh / 2), CY, bevel=0))
        for sy in (-1, 1):
            p.append(k.box(N + "post", (.16, .16, Hh), (sx * (W / 2 - .08), sy * (Ln / 2 - .08), Hh / 2), D, bevel=.01))
            for zz in (.09, Hh - .09):
                p.append(k.box(N + "cast", (.20, .20, .18), (sx * (W / 2 - .10), sy * (Ln / 2 - .10), zz), D, bevel=.01))
        p.append(k.box(N + "rail", (.10, Ln, .12), (sx * (W / 2 - .05), 0, Hh - .06), D, bevel=.01))
        p.append(k.box(N + "railB", (.10, Ln, .16), (sx * (W / 2 - .05), 0, .08), D, bevel=.01))
        # doors (rear, -Y) with lock bars and hinges
        p.append(k.box(N + "door", (W / 2 - .2, .06, Hh - .3), (sx * (W / 4 - .02), -Ln / 2 + .02, Hh / 2), CX, bevel=0))
        for xx in (.28, .80):
            p.append(k.cyl(N + "bar", .028, Hh - .6, (sx * xx, -Ln / 2 - .03, Hh / 2), D, verts=6))
            p.append(k.box(N + "handle", (.06, .05, .22), (sx * xx + .06, -Ln / 2 - .03, Hh * .45), D, bevel=.005))
            for zz in (.5, Hh - .5):
                p.append(k.box(N + "keeper", (.08, .07, .10), (sx * xx, -Ln / 2 - .02, zz), D, bevel=.005))
        for zz in (.4, Hh / 2, Hh - .4):
            p.append(k.box(N + "hinge", (.06, .08, .14), (sx * (W / 2 - .18), -Ln / 2 - .03, zz), D, bevel=.005))
    for sy in (-1, 1):
        p.append(k.box(N + "railE", (W, .10, .12), (0, sy * (Ln / 2 - .05), Hh - .06), D, bevel=.01))
        p.append(k.box(N + "railEB", (W, .10, .16), (0, sy * (Ln / 2 - .05), .08), D, bevel=.01))
    part(N + "Body", p, (0, 0, 0), None, c)
    return stats(name)

BUILDERS = {"Works_MiniExcavator": lambda: build_excavator("Works_MiniExcavator", 1.0, False),
            "Works_Excavator": lambda: build_excavator("Works_Excavator", 1.9, True),
            "Works_SkidLoader": build_skid_loader, "Works_DumpTruck": build_dump_truck, "Works_TowTruck": build_tow_truck,
            "Works_CraneTruck": build_crane_truck, "Works_WreckingCrane": build_wrecking_crane, "Works_Pickup": build_pickup,
            "Works_Forklift": build_forklift, "Works_CherryPicker": build_cherry_picker, "Works_CementMixer": build_cement_mixer,
            "Works_Dumpster": build_dumpster, "Works_Container": build_container}

def build(name):
    return BUILDERS[name]()

def build_all():
    return {n: build(n) for n in MODELS}

# ================================================================== pipeline (export copy with hierarchy -> bake -> fbx)
def make_export(name):
    cname = src_col(name)
    d = _attach(exp_col(name), k.col(EXPORT_COL))
    for o in list(d.objects): bpy.data.objects.remove(o)
    show(cname, d.name)
    src = objs_of(cname); mp = {}
    for o in src:
        n = o.copy(); n.data = o.data.copy(); n.name = "X_" + o.name; d.objects.link(n); mp[o] = n
    for o in src:
        n = mp[o]
        n.parent = mp[o.parent] if o.parent in mp else None
        n.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        n.matrix_basis = o.matrix_basis.copy()
    bpy.context.view_layer.update()
    out = list(mp.values())
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
    """Diffuse colour of all export copies -> one atlas (OUT/<name>_BaseColor.png), one material <name>_Mat."""
    size = size or SIZE.get(name, 2048)
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
    """FBX with the final part names (X_Model.Cab -> Cab); the root is turned 180 deg by export_unity (front -> Unity +Z)."""
    show(exp_col(name))
    objs = objs_of(exp_col(name))
    renames, parked = [], []
    for o in objs:
        final = o.name.split(".", 1)[1]
        other = bpy.data.objects.get(final)
        if other is not None and other is not o:
            other.name = other.name + "~"; parked.append(other)
        renames.append((o, o.name)); o.name = final
    lo, hi = bounds(objs)
    try:
        path = cp.export_unity(objs, name, folder=OUT)
    finally:
        for o, old in renames: o.name = old
        for other in parked: other.name = other.name[:-1]
    tris = sum(len(o.data.loop_triangles) for o in objs)
    return {"fbx": path, "kb": os.path.getsize(path) // 1024, "dims": [round(x, 2) for x in (hi - lo)],
            "lo": [round(x, 2) for x in lo], "hi": [round(x, 2) for x in hi], "tris": tris, "objs": len(objs)}

def verify(name):
    """Re-import the FBX into a scratch collection, list names / parents / origins, then delete the import."""
    before = set(bpy.data.objects); mb = set(bpy.data.materials); ib = set(bpy.data.images); meb = set(bpy.data.meshes)
    c = _attach("Works_Scratch", k.col(EXPORT_COL)); show("Works_Scratch")
    bpy.context.view_layer.active_layer_collection = lc_find(bpy.context.view_layer.layer_collection, "Works_Scratch")
    bpy.ops.import_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    info = []
    for o in new:
        info.append({"name": o.name, "parent": o.parent.name if o.parent else None,
                     "world": [round(v, 3) for v in o.matrix_world.translation],
                     "rot": [round(math.degrees(a), 1) for a in o.matrix_world.to_euler()],
                     "tris": len(o.data.loop_triangles) if o.type == 'MESH' else 0,
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

def pipeline(name, batches=2):
    batches = max(1, min(batches, len(make_export(name))))
    for p in range(batches):
        bake(name, None, batches, p)
    return export(name)

# ================================================================== previews
ISO = (1.0, 1.25, 1.1)   # front-right (front = +Y), ~35 deg down

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

def preview(name, baked=True, direction=ISO):
    cname = exp_col(name) if baked else src_col(name)
    show(cname)
    objs = objs_of(cname)
    lo, hi = bounds(objs); ctr = (lo + hi) / 2; size = (hi - lo).length
    g = k.box("WK_Ground", (80, 80, .02), (0, 0, -.015), k.pavers("ERA_Pavers"), bevel=0)
    p = shot((ctr.x, ctr.y, (hi.z - lo.z) * .35), direction, size * 1.5, lens=38, name=short(name))
    bpy.data.objects.remove(g)
    return p

SHEET = ["Works_MiniExcavator", "Works_SkidLoader", "Works_Forklift", "Works_CementMixer", "Works_Dumpster",
         "Works_Pickup", "Works_TowTruck", "Works_DumpTruck", "Works_CherryPicker", "Works_Container",
         "Works_Excavator", "Works_CraneTruck", "Works_WreckingCrane"]   # front row first (camera at +X+Y)

def contact_sheet(name="contact", baked=True, direction=ISO, res=(4400, 2500), cols=5, dx=11.0, dy=12.5):
    """All 13 at the same scale in a grid laid out along the camera's screen axes, labelled, ortho from the front-right."""
    order = [exp_col(n) if baked else src_col(n) for n in SHEET]
    show(*order)
    d = Vector(direction); right = Vector((-d.y, d.x, 0)).normalized(); back = Vector((-d.x, -d.y, 0)).normalized()
    moved = []; labels = []
    m_txt = k.mat("WK_Label", (.08, .08, .09, 1), rough=.9, var=0)
    rz = math.atan2(right.y, right.x)
    for i, (n, cname) in enumerate(zip(SHEET, order)):
        col, row = i % cols, i // cols
        pos = right * (col * dx) + back * (row * dy)
        for o in objs_of(cname):
            if o.parent is None:
                o.location.x += pos.x; o.location.y += pos.y; moved.append((o, pos.x, pos.y))
        lp = pos - back * 5.0
        t = k.text("WK_lbl", short(n), 1.0, (lp.x, lp.y, .01), m_txt, rot=(0, 0, rz), extrude=.01, res=2)
        labels.append(t)
    n_rows = (len(SHEET) + cols - 1) // cols
    ctr = right * ((cols - 1) * dx / 2) + back * ((n_rows - 1) * dy / 2)
    g = k.box("WK_Ground", (260, 260, .02), (ctr.x, ctr.y, -.015), k.pavers("ERA_Pavers"), bevel=0)
    p = shot((ctr.x, ctr.y, 3.0), direction, 300, lens=40, name=name, res=res, ortho=cols * dx + 1)
    bpy.data.objects.remove(g)
    for t in labels: bpy.data.objects.remove(t)
    for o, ox, oy in moved:
        o.location.x -= ox; o.location.y -= oy
    return p
