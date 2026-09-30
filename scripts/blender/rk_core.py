"""Realistic Kit — core. Soft, rounded, real-shaped props in the style of the game's supplied models
(chunky bevels, teal / cream / orange palette, drawn product labels from IK_Labels_albedo.png).

Modelling space: Blender, metres, Z up, the FRONT (customer side) faces -Y, the back is +Y. export() turns the
model 180° about Z so that, after Unity's FBX import, Unity (x, y, z) = Blender (x, z, y): the back ends up at
Unity +Z and customers stand on Unity -Z, like every other kit piece.
Material naming contract with CheckoutInteriorKitBuilder.KitRemap (Unity):
    C_RRGGBB painted colour · E_RRGGBB glow · G_Glass glass · T_IK_<tex> painted texture (mesh UVs)
Parts are accumulated per output object ("Body", "Anim Fill 0".."Anim Fill 3") so hundreds of products stay cheap.
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

UNITY = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets"
OUT = os.path.join(UNITY, "Art", "Interior", "Models")
TEX = os.path.join(UNITY, "Art", "Interior", "Textures")
PREVIEW = r"C:\Checkout-mobile\unity\CheckoutSimulator\Temp\qa\real"
FONT = os.path.join(UNITY, "Resources", "CheckoutDesktop", "Fonts", "Fredoka_700Bold.ttf")

LABELS = {'soda_0': (0, 0), 'soda_1': (1, 0), 'soda_2': (2, 0), 'soda_3': (3, 0), 'soda_4': (4, 0), 'soda_5': (5, 0), 'soda_6': (6, 0), 'soda_7': (7, 0),
          'water_0': (0, 1), 'water_1': (1, 1), 'juice_0': (2, 1), 'juice_1': (3, 1), 'juice_2': (4, 1), 'juice_3': (5, 1), 'milk': (6, 1), 'yogurt': (7, 1),
          'can_0': (0, 2), 'can_1': (1, 2), 'can_2': (2, 2), 'can_3': (3, 2), 'can_4': (4, 2), 'can_5': (5, 2), 'can_6': (6, 2), 'can_7': (7, 2),
          'beer_0': (0, 3), 'beer_1': (1, 3), 'beer_2': (2, 3), 'beer_3': (3, 3), 'wine_0': (4, 3), 'wine_1': (5, 3), 'wine_2': (6, 3), 'wine_3': (7, 3),
          'gelato_0': (0, 4), 'gelato_1': (1, 4), 'gelato_2': (2, 4), 'gelato_3': (3, 4), 'gelato_4': (4, 4), 'gelato_5': (5, 4), 'gelato_6': (6, 4), 'gelato_7': (7, 4),
          'pack_0': (0, 5), 'pack_1': (1, 5), 'pack_2': (2, 5), 'pack_3': (3, 5), 'pack_4': (4, 5), 'pack_5': (5, 5), 'pack_6': (6, 5), 'pack_7': (7, 5),
          'pack_8': (0, 6), 'pack_9': (1, 6), 'pack_10': (2, 6), 'pack_11': (3, 6), 'pack_12': (4, 6), 'pack_13': (5, 6), 'pack_14': (6, 6), 'pack_15': (7, 6),
          'wood': (0, 7), 'leaf': (1, 7), 'waffle': (2, 7), 'menu': (3, 7), 'coffee_menu': (4, 7), 'fabric': (5, 7), 'bark': (6, 7), 'brand': (7, 7)}
LAB = "T_IK_Labels"

# Palette of the supplied models.
TEAL, TEALD, TEALL = "1F8F85", "146B63", "5FC2B5"
CREAM, CREAMD, ORANGE, ORANGED = "F6ECD4", "E3D2AE", "F08A2C", "C9651B"
WHITE, STEEL, CHROME, DARK, INK = "FBF8F1", "C9D2D6", "DCE3E8", "2F3A40", "1D2B4F"
NAVY, GOLD, GOLDL, RED, PINK, MINT = "1D2B4F", "E0B040", "FFD97A", "D74A3C", "F4A6C1", "B9E8D2"
WOOD, WOODL, WOODD = "B97A45", "D6A266", "6B4128"
METALLIC = {"C_" + STEEL, "C_" + CHROME, "C_B8C2C8", "C_E0B040"}


def cell_uv(name, u, v, inset=.01):
    """(u, v) in 0..1 inside the label cell -> atlas UV (row 0 is the top of the image)."""
    c, r = LABELS[name]
    u = inset + u * (1 - 2 * inset)
    v = inset + v * (1 - 2 * inset)
    return ((c + u) / 8, 1 - (r + 1 - v) / 8)


# --------------------------------------------------------------------------------------------- materials (preview)
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c)


def material(key):
    m = bpy.data.materials.get(key)
    if m:
        return m
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = .5
    if key.startswith("C_"):
        b.inputs["Base Color"].default_value = srgb(key[2:8]) + (1,)
        if key in METALLIC:
            b.inputs["Metallic"].default_value = .7
            b.inputs["Roughness"].default_value = .28
    elif key.startswith("E_"):
        b.inputs["Base Color"].default_value = srgb(key[2:8]) + (1,)
        b.inputs["Emission Color"].default_value = srgb(key[2:8]) + (1,)
        b.inputs["Emission Strength"].default_value = 2.5
    elif key == "G_Glass":
        b.inputs["Base Color"].default_value = (.85, .95, 1, 1)
        b.inputs["Roughness"].default_value = .04
        b.inputs["Alpha"].default_value = .07
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            m.blend_method = "BLEND"
    elif key.startswith("T_"):
        path = os.path.join(TEX, key[2:] + "_albedo.png")
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(path, check_existing=True)
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = .6
    return m


# --------------------------------------------------------------------------------------------- accumulator
class Acc:
    """Collects bmesh parts per output object, each with its material slots."""

    def __init__(self, name):
        self.name = name
        self.parts = {}

    def add(self, bm, key, grp="Body", smooth=True):
        if grp not in self.parts:
            b = bmesh.new()
            b.loops.layers.uv.new("UVMap")
            self.parts[grp] = (b, [])
        target, mats = self.parts[grp]
        if key not in mats:
            mats.append(key)
        idx = mats.index(key)
        if not bm.loops.layers.uv.get("UVMap"):
            bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            f.material_index = idx
            f.smooth = smooth
        me = bpy.data.meshes.new("_tmp")
        bm.to_mesh(me)
        bm.free()
        target.from_mesh(me)
        bpy.data.meshes.remove(me)

    def realize(self, collection=None):
        sc = bpy.context.scene
        col = collection or sc.collection
        objs = []
        for grp, (bm, mats) in self.parts.items():
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.00001)
            me = bpy.data.meshes.new(self.name + "_" + grp)
            bm.to_mesh(me)
            for k in mats:
                me.materials.append(material(k))
            ob = bpy.data.objects.new(grp, me)
            col.objects.link(ob)
            wn = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
            wn.keep_sharp = True
            wn.weight = 100
            objs.append(ob)
        return objs


def place(bm, loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    if scale:
        bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    rx, ry, rz = (math.radians(a) for a in rot)
    R = Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rx, 4, "X")
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(loc)) @ R, verts=bm.verts)
    return bm


class Xf:
    """Local frame proxy: parts added through it are moved by (loc, rot) first. Nestable."""

    def __init__(self, acc, loc=(0, 0, 0), rot=(0, 0, 0), grp=None):
        self.acc, self.grp = acc, grp
        rx, ry, rz = (math.radians(a) for a in rot)
        self.M = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rx, 4, "X")

    def add(self, bm, key, grp="Body", smooth=True):
        bmesh.ops.transform(bm, matrix=self.M, verts=bm.verts)
        self.acc.add(bm, key, self.grp or grp, smooth)


def uv_box(bm, scale=1.0):
    """Metric box projection (for tiling textures)."""
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            co = l.vert.co
            if ax == 0:
                l[uvl].uv = (co.y * scale, co.z * scale)
            elif ax == 1:
                l[uvl].uv = (co.x * scale, co.z * scale)
            else:
                l[uvl].uv = (co.x * scale, co.y * scale)


# --------------------------------------------------------------------------------------------- primitives
def rbox_bm(size, r=.02, seg=3):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    r = min(r, min(size) * .49)
    if r > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r, segments=seg, profile=.5, affect="EDGES", clamp_overlap=True)
    return bm


def rbox(acc, size, loc, key, r=.02, seg=3, rot=(0, 0, 0), grp="Body", uv=1.0):
    bm = rbox_bm(size, r, seg)
    uv_box(bm, uv)
    place(bm, loc, rot)
    acc.add(bm, key, grp)


def spline(pts, n=4):
    """Catmull-Rom through pts (2D or 3D tuples), n samples per segment; keeps the end points."""
    if len(pts) < 3:
        return list(pts)
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (Vector(P[j]) for j in (i - 1, i, i + 1, i + 2))
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            v = .5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append(tuple(v))
    out.append(tuple(pts[-1]))
    return out


def lathe_bm(profile, seg=24, smooth_n=0, uv_cell=None, u_rep=1.0, v_range=None, cap_top=True, cap_bottom=True):
    """Surface of revolution around Z. profile: [(r, z)] bottom to top. With uv_cell the label cell is wrapped
    u_rep times around, v over v_range (z0, z1) (defaults to the profile's height)."""
    prof = spline(profile, smooth_n) if smooth_n else list(profile)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for r, z in prof:
        if r < 1e-6:
            v = bm.verts.new((0, 0, z))
            rings.append([v] * (seg + 1))
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / seg), r * math.sin(2 * math.pi * j / seg), z)) for j in range(seg + 1)])
    z0 = v_range[0] if v_range else prof[0][1]
    z1 = v_range[1] if v_range else prof[-1][1]

    def uv(jj, z):
        u = jj / seg * u_rep
        v = (z - z0) / max(1e-6, z1 - z0)
        if uv_cell:
            return cell_uv(uv_cell, u - math.floor(u) if u_rep > 1 and u > 1 else u, min(1, max(0, v)))
        return (u, z)

    for i in range(len(prof) - 1):
        for j in range(seg):
            quad = [(rings[i][j], j), (rings[i][j + 1], j + 1), (rings[i + 1][j + 1], j + 1), (rings[i + 1][j], j)]
            seen, vs = set(), []
            for v, jj in quad:
                if v not in seen:
                    seen.add(v)
                    vs.append((v, jj))
            if len(vs) < 3:
                continue
            try:
                f = bm.faces.new([v for v, _ in vs])
            except ValueError:
                continue
            ju = {v: jj for v, jj in vs}
            for l in f.loops:
                jj = ju[l.vert]
                if prof[i][0] < 1e-6 and l.vert is rings[i][0] or prof[i + 1][0] < 1e-6 and l.vert is rings[i + 1][0]:
                    jj = j + .5
                l[uvl].uv = uv(jj, l.vert.co.z)
    for idx, flip in ((0, True), (len(prof) - 1, False)):
        if prof[idx][0] > 1e-6 and ((cap_bottom and flip) or (cap_top and not flip)):
            ring = rings[idx][:seg]
            f = bm.faces.new(list(reversed(ring)) if flip else ring)
            for l in f.loops:
                l[uvl].uv = cell_uv(uv_cell, .5, .02) if uv_cell else (l.vert.co.x, l.vert.co.y)
    return bm


def lathe(acc, profile, loc, key, seg=24, smooth_n=3, rot=(0, 0, 0), grp="Body", **kw):
    bm = lathe_bm(profile, seg, smooth_n, **kw)
    place(bm, loc, rot)
    acc.add(bm, key, grp)


def tube_bm(points, r, seg=10, smooth_n=0, caps=True):
    pts = [Vector(p) for p in (spline(points, smooth_n) if smooth_n else points)]
    bm = bmesh.new()
    rings = []
    prev_n = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if prev_n is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < .9 else Vector((1, 0, 0))
            n = t.cross(ref).normalized()
        else:
            n = (prev_n - t * prev_n.dot(t)).normalized()
        prev_n = n
        b = t.cross(n)
        rr = r(i / (len(pts) - 1)) if callable(r) else r
        rings.append([bm.verts.new(p + (n * math.cos(2 * math.pi * j / seg) + b * math.sin(2 * math.pi * j / seg)) * rr) for j in range(seg)])
    for i in range(len(rings) - 1):
        for j in range(seg):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % seg], rings[i + 1][(j + 1) % seg], rings[i + 1][j]))
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv_box(bm)
    return bm


def tube(acc, points, r, key, seg=10, smooth_n=0, grp="Body", caps=True):
    acc.add(tube_bm(points, r, seg, smooth_n, caps), key, grp)


def blob_bm(size, sub=3, noise=0.0, seed=0, squash=1.0):
    """Soft organic lump (icosphere scaled, optionally displaced)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1)
    import random
    rnd = random.Random(seed)
    phase = [rnd.random() * 6.28 for _ in range(6)]
    for v in bm.verts:
        d = 1 + noise * (math.sin(v.co.x * 3 + phase[0]) * math.sin(v.co.y * 3 + phase[1]) * math.sin(v.co.z * 3 + phase[2]) + .5 * math.sin(v.co.x * 7 + phase[3]) * math.sin(v.co.z * 6 + phase[4]))
        v.co = Vector((v.co.x * size[0] * d, v.co.y * size[1] * d, v.co.z * size[2] * d * squash))
    uv_box(bm, 2)
    return bm


def blob(acc, size, loc, key, sub=3, noise=0, seed=0, rot=(0, 0, 0), grp="Body"):
    bm = blob_bm(size, sub, noise, seed)
    place(bm, loc, rot)
    acc.add(bm, key, grp)


def panel_bm(w, h, t, r, seg=6):
    """Rounded-rectangle slab in the XZ plane (faces -Y/+Y), thickness t along Y."""
    pts = []
    for cx, cz, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    bm = bmesh.new()
    front = [bm.verts.new((x, -t / 2, z)) for x, z in pts]
    back = [bm.verts.new((x, t / 2, z)) for x, z in pts]
    bm.faces.new(list(reversed(front)))
    bm.faces.new(back)
    n = len(pts)
    for i in range(n):
        bm.faces.new((front[i], front[(i + 1) % n], back[(i + 1) % n], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, pts


def frame_bm(w, h, t, r, border, seg=6):
    """Rounded rectangular ring (a door frame): outer w x h, border width, thickness t along Y."""
    bm = bmesh.new()
    def loop(W, H, R):
        pts = []
        for cx, cz, a0 in ((W / 2 - R, H / 2 - R, 0), (-W / 2 + R, H / 2 - R, 90), (-W / 2 + R, -H / 2 + R, 180), (W / 2 - R, -H / 2 + R, 270)):
            for i in range(seg + 1):
                a = math.radians(a0 + 90 * i / seg)
                pts.append((cx + R * math.cos(a), cz + R * math.sin(a)))
        return pts
    o = loop(w, h, r)
    i_ = loop(w - 2 * border, h - 2 * border, max(.004, r - border * .6))
    n = len(o)
    of = [bm.verts.new((x, -t / 2, z)) for x, z in o]
    ob = [bm.verts.new((x, t / 2, z)) for x, z in o]
    inf = [bm.verts.new((x, -t / 2, z)) for x, z in i_]
    inb = [bm.verts.new((x, t / 2, z)) for x, z in i_]
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((of[k], of[k2], inf[k2], inf[k]))
        bm.faces.new((ob[k2], ob[k], inb[k], inb[k2]))
        bm.faces.new((of[k2], of[k], ob[k], ob[k2]))
        bm.faces.new((inf[k], inf[k2], inb[k2], inb[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # soften the edges a little
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.calc_face_angle(0) > .8], offset=min(t, border) * .25, segments=2, affect="EDGES", clamp_overlap=True)
    uv_box(bm)
    return bm


def label_panel(acc, w, h, loc, cell, t=.006, r=.02, rot=(0, 0, 0), grp="Body", back_key=None):
    """Flat rounded sign showing a label cell on its -Y face."""
    bm, pts = panel_bm(w, h, t, r)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            x, z = l.vert.co.x, l.vert.co.z
            l[uvl].uv = cell_uv(cell, (x + w / 2) / w, (z + h / 2) / h)
    place(bm, loc, rot)
    acc.add(bm, LAB, grp, smooth=False)


def text_bm(value, size, depth=.01, bevel=.002, align="CENTER"):
    font = bpy.data.fonts.get("Fredoka_700Bold") or bpy.data.fonts.load(FONT)
    font.name = "Fredoka_700Bold"
    cu = bpy.data.curves.new("txt", type="FONT")
    cu.body = value; cu.font = font; cu.size = size; cu.align_x = align; cu.align_y = "CENTER"
    cu.extrude = depth / 2; cu.bevel_depth = bevel; cu.bevel_resolution = 1 if bevel else 0; cu.resolution_u = 2
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2), verts=bm.verts, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    # Text lies in XY facing +Z: stand it up to face -Y.
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    uv_box(bm)
    return bm


def text(acc, value, size, loc, key, depth=.01, rot=(0, 0, 0), grp="Body", bevel=.002):
    bm = text_bm(value, size, depth, bevel)
    place(bm, loc, rot)
    acc.add(bm, key, grp, smooth=False)


# --------------------------------------------------------------------------------------------- scene / preview / export
def clear(scene_name=None):
    """Switches to (or creates) the preview scene `scene_name` and empties it; other scenes are left alone."""
    if scene_name:
        sc = bpy.data.scenes.get(scene_name) or bpy.data.scenes.new(scene_name)
        bpy.context.window.scene = sc
    sc = bpy.context.scene
    for o in list(sc.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for x in list(coll):
            if x.users == 0:
                coll.remove(x)


def studio(size=(1400, 1000), floor=True, bg=(.62, .6, .58)):
    sc = bpy.context.scene
    w = bpy.data.worlds.get("RK") or bpy.data.worlds.new("RK")
    sc.world = w
    w.use_nodes = True
    n = w.node_tree.nodes["Background"]
    n.inputs[0].default_value = bg + (1,)
    n.inputs[1].default_value = .75
    for name, energy, rot in (("RK_Key", 3.2, (50, 8, 35)), ("RK_Fill", 1.0, (60, -10, -120))):
        l = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
        sc.collection.objects.link(l)
        l.data.energy = energy
        l.data.angle = math.radians(8)
        l.rotation_euler = tuple(math.radians(a) for a in rot)
    if floor:
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=30)
        me = bpy.data.meshes.new("RK_Floor")
        bm.to_mesh(me)
        fl = bpy.data.objects.new("RK_Floor", me)
        sc.collection.objects.link(fl)
        m = bpy.data.materials.get("RK_Floor") or bpy.data.materials.new("RK_Floor")
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.82, .78, .72, 1)
        m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
        me.materials.append(m)
    sc.render.engine = "BLENDER_EEVEE"
    try:
        sc.eevee.use_shadows = True
        sc.eevee.use_raytracing = True
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    try:
        sc.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = -.2


def shoot(name, target, direction, dist, lens=40, size=None):
    sc = bpy.context.scene
    if size:
        sc.render.resolution_x, sc.render.resolution_y = size
    cam = bpy.data.objects.get("RK_Cam") or bpy.data.objects.new("RK_Cam", bpy.data.cameras.new("RK_Cam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    d = Vector(direction).normalized()
    cam.data.type = "PERSP"
    cam.data.lens = lens
    cam.data.clip_end = 300
    cam.location = Vector(target) + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    os.makedirs(PREVIEW, exist_ok=True)
    sc.render.filepath = os.path.join(PREVIEW, name + ".png")
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


def export(name, objs):
    """Turn to Unity's facing and write Assets/Art/Interior/Models/<name>.fbx."""
    os.makedirs(OUT, exist_ok=True)
    R = Matrix.Rotation(math.pi, 4, "Z")
    for o in objs:
        o.data.transform(R)
        o.data.update()
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), use_selection=True, object_types={"MESH"},
                             axis_forward="-Z", axis_up="Y", bake_anim=False, path_mode="STRIP",
                             use_mesh_modifiers=True, mesh_smooth_type="OFF", apply_scale_options="FBX_SCALE_ALL",
                             use_tspace=False)
    for o in objs:
        o.data.transform(R.inverted())
        o.data.update()
