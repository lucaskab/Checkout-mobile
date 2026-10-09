"""Shared helpers for the interactive events (ArtSource/events_interactive, Oct 2026).

Loads the event-rig pipeline (event_rigs/rig_kit.py + characters.py, which are plain scripts) as modules, keeps the
market palette (events_kit.C), builds skinned clothing from the game's own characters, and renders the review
contact sheets. Everything is in metres, Blender Z up; characters face -Y (character space, scale 1 = 2.4 m tall,
the game scales them to 0.72).

    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\events_interactive\\inspector.py").read())
"""
import bpy, bmesh, math, os, sys, types
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

HERE = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\events_interactive"
ART = os.path.dirname(HERE)
RIGS = os.path.join(ART, "event_rigs")
UNITY = os.path.join(os.path.dirname(os.path.dirname(ART)), "CheckoutSimulator")
CHARS = os.path.join(UNITY, "Assets", "Art", "Characters", "Meshy")
STAFF = os.path.join(UNITY, "Assets", "Art", "Staff", "Models")
REVIEW = os.path.join(ART, "Review", "events_interactive")
TMP = os.path.join(UNITY, "Temp", "qa", "interactive")
for p in (ART, RIGS, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(ART))), "scripts", "blender")):
    if p not in sys.path:
        sys.path.insert(0, p)
import era_kit as k

rad = math.radians
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def _script_module(name, path, base=None):
    """event_rigs/*.py are written to be exec'd one after the other; load them as modules sharing one namespace."""
    g = dict(base or {}); g["__file__"] = path; g["__name__"] = name
    exec(open(path, encoding="utf-8").read(), g)
    mod = types.ModuleType(name); mod.__dict__.update(g); sys.modules[name] = mod
    return mod


rk = _script_module("rig_kit", os.path.join(RIGS, "rig_kit.py"))
ch = _script_module("characters", os.path.join(RIGS, "characters.py"), base=rk.__dict__)

# ------------------------------------------------------------------------------------------------ palette
C = dict(
    teal=(.06, .52, .48, 1), tealL=(.25, .74, .64, 1), navy=(.05, .10, .30, 1), cream=(.96, .90, .72, 1),
    white=(.95, .94, .90, 1), red=(.86, .20, .15, 1), orange=(.97, .52, .10, 1), yellow=(.98, .80, .16, 1),
    gold=(.91, .70, .27, 1), green=(.10, .55, .22, 1), lime=(.55, .80, .20, 1), blue=(.10, .40, .80, 1),
    sky=(.45, .75, .95, 1), pink=(.95, .45, .60, 1), purple=(.50, .28, .70, 1), dark=(.13, .14, .16, 1),
    grey=(.55, .57, .58, 1), steel=(.70, .72, .74, 1), brown=(.45, .28, .16, 1), skin=(.90, .67, .46, 1),
    coat=(.97, .96, .93, 1), paper=(.98, .97, .93, 1), ink=(.05, .05, .06, 1))
M = {}


def mats():
    if M:
        return M
    for n, c in C.items():
        M[n] = k.mat("EI_" + n, c, rough=.6, var=.06, scale=8)
    M["coat"] = k.mat("EI_coat", C["coat"], rough=.75, var=.05, scale=14, bump=.15)      # cotton twill
    M["paper"] = k.mat("EI_paper", C["paper"], rough=.9, var=.02, scale=20)
    M["ink"] = k.mat("EI_ink", C["ink"], rough=.85, var=0)
    M["chrome"] = k.mat("EI_chrome", (.80, .82, .84, 1), rough=.25, var=.04, scale=8, metallic=.8)
    M["rubber"] = k.mat("EI_rubber", (.12, .12, .13, 1), rough=.9, var=.05, scale=12)
    M["wood"] = k.wood("EI_wood")
    M["glass"] = k.glass("EI_glass", tint=(.75, .90, .98, 1), alpha=.35)
    M["ice"] = k.mat("EI_ice", (.86, .95, .99, 1), rough=.25, var=.12, scale=40, bump=.5)
    M["foam"] = k.mat("EI_foam", (.93, .94, .92, 1), rough=.95, var=.10, scale=60, bump=.6)   # styrofoam grain
    M["water"] = k.glass("EI_water", tint=(.70, .88, .98, 1), alpha=.45)
    M["lamp"] = k.emissive("EI_lamp", (1.0, .93, .75, 1), 3.0)
    return M


# ------------------------------------------------------------------------------------------------ characters
def ctx():
    return rk._ctx()


def load_character(fbx, png, rig_name, body_name):
    """Imports one of the game's characters; drops its props and clips, paints its texture. -> (armature, body)"""
    before = set(bpy.data.objects); acts = set(bpy.data.actions)
    with bpy.context.temp_override(**ctx()):
        bpy.ops.import_scene.fbx(filepath=fbx)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE' and o.data.bones)
    body = next(o for o in new if o.type == 'MESH' and o.name.endswith("_Body"))
    for o in new:
        if o is not arm and o is not body:
            bpy.data.objects.remove(o, do_unlink=True)
    for a in list(bpy.data.actions):
        if a not in acts:
            bpy.data.actions.remove(a)
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    arm.name = rig_name; arm.data.name = rig_name; body.name = body_name; body.data.name = body_name
    if png:
        paint(body, png, body_name + "_Mat")
    return arm, body


def paint(obj, png, mat_name):
    """One textured material (the character's painted albedo) on the mesh."""
    m = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type in ('TEX_IMAGE', 'NORMAL_MAP'):
            nt.nodes.remove(n)
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(png, check_existing=True)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = .7; bsdf.inputs["Specular IOR Level"].default_value = .3
    obj.data.materials.clear(); obj.data.materials.append(m)
    return m


class Body:
    """Rest-pose vertex cloud of a character body, by bone group (numpy), to fit clothes around it."""
    def __init__(self, body):
        me = body.data; n = len(me.vertices)
        co = np.empty(n * 3); me.vertices.foreach_get("co", co); self.co = co.reshape(n, 3)
        self.grp = np.full(n, -1)
        names = [g.name for g in body.vertex_groups]
        for v in me.vertices:
            if v.groups:
                self.grp[v.index] = max(v.groups, key=lambda g: g.weight).group
        self.names = names
        self.idx = {g: i for i, g in enumerate(names)}

    def pts(self, groups):
        sel = np.isin(self.grp, [self.idx[g] for g in groups if g in self.idx])
        return self.co[sel]

    def ring(self, pts, z, band, n, centre=None, pad=0.03, start=0.0, span=2 * math.pi, fallback=0.12):
        """Silhouette ring at height z: for n angles from `start` over `span`, the farthest point of `pts`
        (within +-band in z, +-half a step in angle) from `centre`, pushed out by pad. -> list of Vectors"""
        s = pts[np.abs(pts[:, 2] - z) < band]
        if centre is None:
            centre = Vector((0, float(s[:, 1].mean()) if len(s) else 0.0, z))
        cx, cy = centre.x, centre.y
        out = []
        if len(s):
            ang = np.arctan2(s[:, 1] - cy, s[:, 0] - cx); dist = np.hypot(s[:, 0] - cx, s[:, 1] - cy)
        step = span / max(1, (n - 1 if span < 2 * math.pi - 1e-6 else n))
        for i in range(n):
            a = start + i * step
            if len(s):
                d = np.abs((ang - a + math.pi) % (2 * math.pi) - math.pi)
                m = d < max(step * 0.75, rad(9))
                r = float(dist[m].max()) if m.any() else fallback
            else:
                r = fallback
            r += pad
            out.append(Vector((cx + math.cos(a) * r, cy + math.sin(a) * r, z)))
        return out


def mesh_from_rings(name, rings, close=False, cap_top=False, cap_bottom=False):
    """Quad strips between consecutive rings (same vertex count). `close` joins the last vertex to the first."""
    bm = bmesh.new(); vs = []
    for ring in rings:
        vs.append([bm.verts.new(p) for p in ring])
    n = len(rings[0])
    for a, b in zip(vs, vs[1:]):
        for i in range(n - 1 + (1 if close else 0)):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap_bottom:
        bm.faces.new(list(reversed(vs[0])))
    if cap_top:
        bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    return o


def skin_weights(obj, arm, weights_of):
    """Armature-deform `obj` with vertex groups from weights_of(co) -> {bone: w} (co in armature space)."""
    rk.skin(obj, arm, lambda co, i: weights_of(co))
    return obj


def skin_transfer(obj, arm, body):
    """Armature-deform `obj` with the body's own skin weights (nearest surface): tight clothing then bends
    exactly like the character underneath, whatever the Meshy weighting does at the joints."""
    mw = obj.matrix_world.copy()
    md = obj.modifiers.new("Transfer", 'DATA_TRANSFER'); md.object = body
    md.use_vert_data = True; md.data_types_verts = {'VGROUP_WEIGHTS'}; md.vert_mapping = 'POLYINTERP_NEAREST'
    md.layers_vgroup_select_src = 'ALL'; md.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    with bpy.context.temp_override(**ctx(), active_object=obj, object=obj, selected_objects=[obj]):
        bpy.ops.object.datalayout_transfer(modifier=md.name)
        bpy.ops.object.modifier_move_to_index(modifier=md.name, index=0)
        bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    obj.parent = arm; obj.parent_type = 'OBJECT'
    bpy.context.view_layer.update(); obj.matrix_world = mw
    m = obj.modifiers.new("Armature", 'ARMATURE'); m.object = arm
    return obj


def skin_const(obj, arm, bone):
    return skin_weights(obj, arm, lambda co: {bone: 1.0})


def blend(z, z0, z1):
    """0 at z0 -> 1 at z1 (smoothstep)."""
    t = max(0.0, min(1.0, (z - z0) / (z1 - z0))) if z1 != z0 else 0.0
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------------------------------------ props
def finish(o, m, bevel=.004, seg=2):
    return k.finish(o, m, bevel, seg)


def pictogram_check(c, loc, size, m, thick=.012, depth=.006, plane='XZ', name="check"):
    """A tick mark: short stroke down to the vertex, long stroke up to the right. plane 'XZ' = standing, face -Y
    (depth along Y); plane 'XY' = lying flat, face +Z (depth along Z). Centre at loc, `size` tall."""
    s = size
    short = ((-.225 * s, -.125 * s), .43 * s, 54)      # (offset, length, descent angle)
    long_ = ((.175 * s, .10 * s), .97 * s, -55)
    out = []
    for i, ((dx, dy), ln, ang) in enumerate((short, long_)):
        if plane == 'XZ':
            o = k.box(f"{name}_{i}", (ln, depth, thick), (loc[0] + dx, loc[1], loc[2] + dy), m, rot=(0, rad(ang), 0), bevel=thick * .3, c=c)
        else:
            o = k.box(f"{name}_{i}", (ln, thick, depth), (loc[0] + dx, loc[1] + dy, loc[2]), m, rot=(0, 0, rad(-ang)), bevel=thick * .3, c=c)
        out.append(o)
    return out


def pictogram_cross(c, loc, size, m, thick=.014, depth=.006, name="cross"):
    out = []
    for i, a in enumerate((45, -45)):
        out.append(k.box(f"{name}_{i}", (size, depth, thick), loc, m, rot=(0, rad(a), 0), bevel=thick * .3, c=c))
    return out


def pictogram_bang(c, loc, size, m, thick=.028, depth=.006, name="bang"):
    """An exclamation mark: tapered bar + dot."""
    bar = k.box(name + "_bar", (thick, depth, size * .62), (loc[0], loc[1], loc[2] + size * .16), m, bevel=thick * .3, c=c)
    dot = k.cyl(name + "_dot", thick * .6, depth, (loc[0], loc[1], loc[2] - size * .36), m, rot=(rad(90), 0, 0), verts=12, c=c)
    return [bar, dot]


def star(c, loc, r, m, depth=.006, name="star", points=5):
    bm = bmesh.new()
    pts = []
    for i in range(points * 2):
        a = math.pi / 2 + i * math.pi / points
        rr = r if i % 2 == 0 else r * .45
        pts.append(bm.verts.new((math.cos(a) * rr, 0, math.sin(a) * rr)))
    f = bm.faces.new(pts)
    bmesh.ops.triangulate(bm, faces=[f])
    r_ = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    bmesh.ops.translate(bm, verts=[g for g in r_["geom"] if isinstance(g, bmesh.types.BMVert)], vec=(0, -depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = loc; k.link(o, c); me.materials.append(m)
    return o


def shield(c, loc, w, h, m, depth=.006, name="shield"):
    """Heraldic shield outline lying in XZ (face -Y)."""
    bm = bmesh.new(); pts = []
    prof = [(-.5, .5), (.5, .5), (.5, .1), (.42, -.2), (.22, -.42), (0, -.5), (-.22, -.42), (-.42, -.2), (-.5, .1)]
    for u, v in prof:
        pts.append(bm.verts.new((u * w, 0, v * h)))
    f = bm.faces.new(pts); bmesh.ops.triangulate(bm, faces=[f])
    r_ = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    bmesh.ops.translate(bm, verts=[g for g in r_["geom"] if isinstance(g, bmesh.types.BMVert)], vec=(0, -depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = loc; k.link(o, c); me.materials.append(m)
    return o


def lathe(name, profile, loc, m, seg=16, c=None):
    """Solid of revolution around Z from (r, z) profile points (r=0 at both ends closes it)."""
    bm = bmesh.new(); rings = []
    for r, z in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, z))] * seg)
        else:
            rings.append([bm.verts.new((math.cos(i * 2 * math.pi / seg) * r, math.sin(i * 2 * math.pi / seg) * r, z)) for i in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            vs = []
            for v in (a[i], a[j], b[j], b[i]):
                if v not in vs:
                    vs.append(v)
            if len(vs) >= 3:
                bm.faces.new(vs)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = loc; k.link(o, c)
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    return o


def join(objs, name, origin=(0, 0, 0)):
    """Applies modifiers, joins, bakes the rotation (local = world), sets the origin; keeps each part's material."""
    o = k.join(objs, name, origin=None)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.context.scene.cursor.location = origin
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return o


def tris(objs):
    dg = bpy.context.evaluated_depsgraph_get(); t = 0
    for o in objs:
        if o.type == 'MESH':
            me = o.evaluated_get(dg).data; me.calc_loop_triangles(); t += len(me.loop_triangles)
    return t


# ------------------------------------------------------------------------------------------------ attach
def attach_to_bone(obj, arm, bone, world):
    """Parents `obj` rigidly to `bone` so that it sits at `world` (a Matrix) in the CURRENT pose; in any other
    pose it follows the bone."""
    obj.matrix_world = world
    bpy.context.view_layer.update()
    obj.parent = arm; obj.parent_type = 'BONE'; obj.parent_bone = bone
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone]
    bone_world = arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))
    obj.matrix_parent_inverse = bone_world.inverted()
    obj.matrix_world = world


def bone_world(arm, bone):
    pb = arm.pose.bones[bone]
    return arm.matrix_world @ pb.matrix


# ------------------------------------------------------------------------------------------------ review renders
def studio(res=(900, 900), bg=(0.80, 0.84, 0.88), ground=True):
    """The event-rig review look: soft sun + fill, grey floor, light sky (same as rig_kit.studio)."""
    sc = bpy.context.scene
    if "QA_Cam" not in bpy.data.objects:
        cam = bpy.data.objects.new("QA_Cam", bpy.data.cameras.new("QA_Cam")); sc.collection.objects.link(cam)
        sun = bpy.data.objects.new("QA_Sun", bpy.data.lights.new("QA_Sun", "SUN")); sc.collection.objects.link(sun)
        sun.data.energy = 3.2; sun.data.angle = rad(6); sun.rotation_euler = (rad(48), 0, rad(32))
        fill = bpy.data.objects.new("QA_Fill", bpy.data.lights.new("QA_Fill", "SUN")); sc.collection.objects.link(fill)
        fill.data.energy = 1.0; fill.rotation_euler = (rad(60), 0, rad(210))
    w = bpy.data.worlds.get("QA_World") or bpy.data.worlds.new("QA_World"); sc.world = w; w.use_nodes = True
    bgn = w.node_tree.nodes["Background"]; bgn.inputs[0].default_value = (*bg, 1); bgn.inputs[1].default_value = 0.8
    if ground and "QA_Ground" not in bpy.data.objects:
        me = bpy.data.meshes.new("QA_Ground"); bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40); bm.to_mesh(me); bm.free()
        g = bpy.data.objects.new("QA_Ground", me); sc.collection.objects.link(g)
        m = bpy.data.materials.new("QA_GroundMat"); m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.56, 0.58, 1)
        me.materials.append(m)
    sc.camera = bpy.data.objects["QA_Cam"]
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    sc.render.fps = 24
    return sc


def aim(target, direction, distance, lens=50, ortho=None):
    cam = bpy.data.objects["QA_Cam"]; d = Vector(direction).normalized()
    cam.location = Vector(target) + d * distance
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.type = 'ORTHO' if ortho else 'PERSP'
    if ortho:
        cam.data.ortho_scale = ortho
    cam.data.clip_end = 200
    return cam


def frame_objects(objs, direction=(1.0, -1.25, 0.85), lens=50, pad=1.15, ortho=False):
    """Camera that frames the given objects (evaluated bounds) from `direction`."""
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9,) * 3); hi = -lo
    for o in objs:
        if o.type != 'MESH':
            continue
        ev = o.evaluated_get(dg)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    c = (lo + hi) / 2; size = (hi - lo).length
    sc = bpy.context.scene; asp = sc.render.resolution_x / sc.render.resolution_y
    if ortho:
        return aim(c, direction, size * 4, lens, ortho=size * pad / min(1.0, asp)), (lo, hi)
    fov = 2 * math.atan(36 / 2 / lens) * min(1.0, asp)
    dist = (size / 2 * pad) / math.tan(fov / 2)
    return aim(c, direction, dist, lens), (lo, hi)


def label(text, size=0.06):
    """A caption parented to the camera, bottom-left of the frame (review images only)."""
    cam = bpy.data.objects["QA_Cam"]
    o = bpy.data.objects.get("QA_Label")
    if o is None:
        cu = bpy.data.curves.new("QA_Label", 'FONT'); o = bpy.data.objects.new("QA_Label", cu)
        bpy.context.scene.collection.objects.link(o)
        m = bpy.data.materials.new("QA_LabelMat"); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (.08, .09, .12, 1)
        b.inputs["Emission Color"].default_value = (.08, .09, .12, 1); b.inputs["Emission Strength"].default_value = 1.0
        cu.materials.append(m)
    o.data.body = text; o.data.align_x = 'LEFT'
    o.parent = cam; o.matrix_parent_inverse = Matrix.Identity(4)
    sc = bpy.context.scene; asp = sc.render.resolution_x / sc.render.resolution_y
    dist = 2.0
    if cam.data.type == 'ORTHO':
        w = cam.data.ortho_scale; h = w / asp if asp >= 1 else w; w = h * asp
        hw, hh = w / 2, h / 2
    else:
        hw = dist * 18 / cam.data.lens; hh = hw / asp if asp >= 1 else hw; hw = hh * asp
    o.data.size = size * 2 * hh            # `size` = fraction of the frame height
    o.location = (-hw + 0.03 * 2 * hw, -hh + 0.03 * 2 * hh, -dist); o.scale = (1, 1, 1)
    o.rotation_euler = (0, 0, 0)
    o.hide_render = False
    return o


def hide_label():
    o = bpy.data.objects.get("QA_Label")
    if o:
        o.hide_render = True


def render(path):
    sc = bpy.context.scene
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def contact_sheet(paths, out, cols, gap=12, bg=(0.80, 0.84, 0.88, 1.0)):
    """Tiles rendered PNGs into one image (numpy), row-major."""
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p, check_existing=False)
        w, h = im.size; px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
        imgs.append(px); bpy.data.images.remove(im)
    h = max(px.shape[0] for px in imgs); w = max(px.shape[1] for px in imgs)
    rows = (len(imgs) + cols - 1) // cols
    W = cols * w + (cols + 1) * gap; H = rows * h + (rows + 1) * gap
    sheet = np.empty((H, W, 4), dtype=np.float32); sheet[:] = bg
    for i, px in enumerate(imgs):
        r, c = divmod(i, cols)
        ph, pw = px.shape[:2]
        y = gap + r * (h + gap) + (h - ph) // 2; x = gap + c * (w + gap) + (w - pw) // 2
        sheet[y:y + ph, x:x + pw] = px
    img = bpy.data.images.new("sheet", W, H, alpha=True)
    img.pixels = sheet[::-1].ravel().tolist()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.filepath_raw = out; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return out


# ------------------------------------------------------------------------------------------------ clips
def bake_clips(arm, clips, step=2, rig_cls=None):
    """Keys the clips dict {name: (frames, fn(rig, f) -> Pose, arms_only)} on `arm` (characters.py machinery)."""
    rig = (rig_cls or ch.Rig)(arm)
    acts = []
    for name, (frames, fn, arms_only) in clips.items():
        act = rk.new_action(arm, name, frames=frames if frames > 2 else None)
        last = {}
        keys = list(range(1, frames + 2, step))
        if keys[-1] != frames + 1:
            keys.append(frames + 1)
        for f in keys:
            ch.put(arm, f, fn(rig, ((f - 1) % frames) + 1 if frames > 2 else f), last)
        rk.linear(act, "rotation"); rk.linear(act, "location")
        if frames > 2:
            act.frame_start, act.frame_end = 1, frames
        acts.append(act)
    return acts


def set_action(arm, act, frame=1):
    arm.animation_data_create(); arm.animation_data.action = act
    bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()


def save_as(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=False)
    return path
