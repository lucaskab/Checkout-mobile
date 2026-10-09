"""Rig kit for the market events (Oct 2026).

Turns the baked event props (Assets/Resources/EventProps2/*.fbx) into rigged props: the mesh is split into
rigid parts by connected islands, each part is parented to a bone of an armature, and Blender actions drive the
bones. The result is exported to Assets/Resources/EventRigs/<Rig>.fbx with its clips (Unity imports the folder as
Legacy animation, see Assets/Editor/CheckoutEventRigImport.cs). The parts keep the UVs of the baked atlas, so the
game reuses EventProps2/<Prop>_BaseColor.png (mesh names are "<Prop>__<part>").

Run inside Blender:  exec(open(r"...\\ArtSource\\event_rigs\\rig_kit.py").read())  then call the builders.
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix, Quaternion, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__) if "__file__" in globals() else r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\event_rigs", "..", "..", "..", ".."))
UNITY = os.path.join(ROOT, "unity", "CheckoutSimulator")
PROPS = os.path.join(UNITY, "Assets", "Resources", "EventProps2")
RIGS_OUT = os.path.join(UNITY, "Assets", "Resources", "EventRigs")
QA = os.path.join(UNITY, "Temp", "qa", "rigs")
FPS = 24


# ----------------------------------------------------------------------------------------------------- context
def _ctx():
    win = bpy.context.window_manager.windows[0]
    area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), win.screen.areas[0])
    return dict(window=win, area=area, screen=win.screen)


def reset():
    """Empties the scene (keeps the QA camera/lights) and drops orphan data."""
    for o in list(bpy.data.objects):
        if not o.name.startswith("QA_"):
            bpy.data.objects.remove(o, do_unlink=True)
    for a in list(bpy.data.actions):          # every action would be exported as a take
        bpy.data.actions.remove(a)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_set(1)


def import_prop(name):
    """Imports EventProps2/<name>.fbx; returns its mesh object (named <name>)."""
    before = set(bpy.data.objects)
    with bpy.context.temp_override(**_ctx()):
        bpy.ops.import_scene.fbx(filepath=os.path.join(PROPS, name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    mesh = next(o for o in new if o.type == 'MESH')
    mesh.name = name
    for o in new:
        if o is not mesh:
            bpy.data.objects.remove(o, do_unlink=True)
    return mesh


# ----------------------------------------------------------------------------------------------------- islands
class Island:
    def __init__(self, idx, verts):
        self.idx = idx
        self.verts = verts  # vertex indices
        self.lo = Vector((min(v[0] for v in verts.values()), min(v[1] for v in verts.values()), min(v[2] for v in verts.values())))
        self.hi = Vector((max(v[0] for v in verts.values()), max(v[1] for v in verts.values()), max(v[2] for v in verts.values())))
        self.center = (self.lo + self.hi) / 2
        self.size = self.hi - self.lo
        self.count = len(verts)

    def inside(self, lo, hi, pad=0.02):
        return all(lo[i] - pad <= self.lo[i] and self.hi[i] <= hi[i] + pad for i in range(3))

    def __repr__(self):
        return f"Island#{self.idx}(n={self.count} lo={tuple(round(v, 2) for v in self.lo)} hi={tuple(round(v, 2) for v in self.hi)})"


def islands(obj):
    """Connected vertex islands of a mesh, in the object's local space."""
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
    seen = set(); out = []
    for v in bm.verts:
        if v.index in seen:
            continue
        comp = {}; stack = [v]; seen.add(v.index)
        while stack:
            x = stack.pop(); comp[x.index] = x.co.copy()
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen:
                    seen.add(y.index); stack.append(y)
        out.append(Island(len(out), comp))
    bm.free()
    return out


def split(obj, assign):
    """Splits `obj` into one object per part. `assign(island)` returns the part name of each island.
    Every part object keeps the source transform, mesh data and material; it is named "<obj>__<part>"."""
    parts = {}
    for isl in islands(obj):
        parts.setdefault(assign(isl), set()).update(isl.verts)
    made = {}
    for part, keep in parts.items():
        me = obj.data.copy(); me.name = f"{obj.name}__{part}"
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context='VERTS')
        bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(me.name, me); o.matrix_world = obj.matrix_world.copy()
        bpy.context.scene.collection.objects.link(o)
        made[part] = o
    bpy.data.objects.remove(obj, do_unlink=True)
    return made


# ----------------------------------------------------------------------------------------------------- armature
def armature(name, matrix_world, bones):
    """Creates an armature object at `matrix_world` with `bones` = [(name, head, tail, parent or None, roll)]
    given in that object's local space."""
    arm = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    bpy.context.scene.collection.objects.link(arm)
    arm.matrix_world = matrix_world.copy()
    arm.data.display_type = 'STICK'; arm.show_in_front = True
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.selected_objects:
        o.select_set(False)
    arm.select_set(True)
    with bpy.context.temp_override(**_ctx(), active_object=arm, object=arm):
        bpy.ops.object.mode_set(mode='EDIT')
        eb = arm.data.edit_bones
        for b in bones:
            bn, head, tail, parent = b[:4]
            roll = b[4] if len(b) > 4 else 0.0
            e = eb.new(bn); e.head = Vector(head); e.tail = Vector(tail); e.roll = roll
            if parent:
                e.parent = eb[parent]
            e.use_connect = False
        bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return arm


def attach(obj, arm, bone):
    """Parents a part to a bone, keeping where it is in the world (rigid, no deformation)."""
    mw = obj.matrix_world.copy()
    obj.parent = arm; obj.parent_type = 'BONE'; obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = mw


def skin(obj, arm, weights):
    """Deforming parts (flags, banners): armature modifier + vertex groups. `weights(co, index) -> {bone: w}`
    gets each vertex position in armature space (and its index). Weights should sum to 1 (give the rest to a
    static bone), Unity keeps at most 4 per vertex."""
    mw = obj.matrix_world.copy()
    inv = arm.matrix_world.inverted() @ obj.matrix_world
    for v in obj.data.vertices:
        for bn, w in weights(inv @ v.co, v.index).items():
            if w <= 0:
                continue
            g = obj.vertex_groups.get(bn) or obj.vertex_groups.new(name=bn)
            g.add([v.index], w, 'REPLACE')
    obj.parent = arm; obj.parent_type = 'OBJECT'
    bpy.context.view_layer.update(); obj.matrix_world = mw
    m = obj.modifiers.new("Armature", 'ARMATURE'); m.object = arm


def subdivide(obj, cuts=8, min_length=0.25):
    """Cloth made of a thin box only bends at its corners: cut its long edges into a grid (UVs follow)."""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    edges = [e for e in bm.edges if e.calc_length() >= min_length]
    if edges:
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
    bm.to_mesh(obj.data); bm.free()


def join(objs, name):
    """Joins part objects into one (same material atlas)."""
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    with bpy.context.temp_override(**_ctx(), active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name; objs[0].data.name = name
    return objs[0]


# ----------------------------------------------------------------------------------------------------- animation
def new_action(arm, name, frames=None):
    """A new action on the armature; `frames` = loop length (exported range 1..frames, key frames+1 = key 1)."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if frames:
        act.use_frame_range = True; act.frame_start = 1; act.frame_end = frames
        act.use_cyclic = True
    arm.animation_data_create(); arm.animation_data.action = act
    return act


def pose(arm, bone, frame, rot=None, loc=None, axis_space='ARMATURE'):
    """Keys a bone at `frame`. `rot` = (axis, degrees) about an axis given in armature space (default) or a
    quaternion/Euler in the bone's local space when axis_space='LOCAL'. `loc` = local translation."""
    pb = arm.pose.bones[bone]
    if rot is not None:
        if axis_space == 'ARMATURE':
            axis, deg = rot
            rest = pb.bone.matrix_local.to_quaternion()
            q = rest.inverted() @ Quaternion(Vector(axis).normalized(), math.radians(deg)) @ rest
        else:
            q = rot.to_quaternion() if isinstance(rot, Euler) else rot
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    if loc is not None:
        pb.location = Vector(loc)
        pb.keyframe_insert("location", frame=frame)


def compose(*rots):
    """Armature-space rotations combined (applied right to left): compose((z,30),(y,-10))."""
    q = Quaternion()
    for axis, deg in rots:
        q = Quaternion(Vector(axis).normalized(), math.radians(deg)) @ q
    return q


def pose_q(arm, bone, frame, q_arm, loc=None):
    """Keys a bone with an armature-space rotation quaternion (rotation about the bone head)."""
    pb = arm.pose.bones[bone]
    rest = pb.bone.matrix_local.to_quaternion()
    pb.rotation_quaternion = rest.inverted() @ q_arm @ rest
    pb.keyframe_insert("rotation_quaternion", frame=frame)
    if loc is not None:
        pb.location = Vector(loc); pb.keyframe_insert("location", frame=frame)


def smooth(act, interpolation='BEZIER', cyclic=True):
    """Eases every key; cyclic actions loop without a pop (first and last keys must match)."""
    for fc in _fcurves(act):
        for k in fc.keyframe_points:
            k.interpolation = interpolation
            k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'
        if cyclic:
            m = fc.modifiers.new('CYCLES') if not any(m.type == 'CYCLES' for m in fc.modifiers) else None
        fc.update()


def _fcurves(act):
    """Blender 5 layered actions keep their curves in channelbags."""
    if hasattr(act, "layers") and act.layers:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
        return out
    return list(act.fcurves)


def linear(act, data_path_part):
    for fc in _fcurves(act):
        if data_path_part in fc.data_path:
            for k in fc.keyframe_points:
                k.interpolation = 'LINEAR'


# ----------------------------------------------------------------------------------------------------- preview
def studio(focus_lo, focus_hi, direction=(0.35, -1.0, 0.5), lens=50, res=(720, 480), distance=2.0):
    sc = bpy.context.scene
    if "QA_Cam" not in bpy.data.objects:
        cam = bpy.data.objects.new("QA_Cam", bpy.data.cameras.new("QA_Cam")); sc.collection.objects.link(cam)
        sun = bpy.data.objects.new("QA_Sun", bpy.data.lights.new("QA_Sun", "SUN")); sc.collection.objects.link(sun)
        sun.data.energy = 3.2; sun.rotation_euler = (math.radians(48), 0, math.radians(32))
        fill = bpy.data.objects.new("QA_Fill", bpy.data.lights.new("QA_Fill", "SUN")); sc.collection.objects.link(fill)
        fill.data.energy = 1.0; fill.rotation_euler = (math.radians(60), 0, math.radians(210))
    if not sc.world or sc.world.name != "QA_World":
        w = bpy.data.worlds.get("QA_World") or bpy.data.worlds.new("QA_World"); sc.world = w; w.use_nodes = True
        bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.80, 0.84, 0.88, 1); bg.inputs[1].default_value = 0.8
    if "QA_Ground" not in bpy.data.objects:
        me = bpy.data.meshes.new("QA_Ground"); bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40); bm.to_mesh(me); bm.free()
        g = bpy.data.objects.new("QA_Ground", me); sc.collection.objects.link(g)
        m = bpy.data.materials.new("QA_GroundMat"); m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.56, 0.58, 1)
        me.materials.append(m)
    cam = bpy.data.objects["QA_Cam"]; sc.camera = cam
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    c = (Vector(focus_lo) + Vector(focus_hi)) / 2; size = (Vector(focus_hi) - Vector(focus_lo)).length
    d = Vector(direction).normalized()
    cam.data.lens = lens
    cam.location = c + d * size * distance
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()


def render_frames(name, frames):
    """Renders the given frames to Temp/qa/rigs/<name>_<frame>.png; returns the paths."""
    os.makedirs(QA, exist_ok=True)
    sc = bpy.context.scene; paths = []
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(QA, f"{name}_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
        paths.append(sc.render.filepath)
    return paths


# ----------------------------------------------------------------------------------------------------- export
def export_rig(rig_name, arm, parts, actions):
    """Writes Assets/Resources/EventRigs/<rig_name>.fbx: the armature, its parts and one take per action
    (named after the action). Same axes as the game's other props (FBX -Z forward, Y up)."""
    os.makedirs(RIGS_OUT, exist_ok=True)
    arm.name = rig_name
    for o in bpy.context.selected_objects:
        o.select_set(False)
    arm.select_set(True)
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = arm
    # Every action becomes a take: give each its own NLA track so "all actions" exports them by name.
    arm.animation_data_create(); arm.animation_data.action = None
    for a in actions:
        a.use_fake_user = True
    path = os.path.join(RIGS_OUT, rig_name + ".fbx")
    with bpy.context.temp_override(**_ctx()):
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH', 'EMPTY'},
                                 axis_forward='-Z', axis_up='Y', path_mode='STRIP', use_mesh_modifiers=False,
                                 mesh_smooth_type='FACE', apply_scale_options='FBX_SCALE_ALL', use_tspace=False,
                                 add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                                 use_armature_deform_only=False, armature_nodetype='NULL',
                                 bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                                 bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
                                 bake_anim_step=1.0, bake_anim_simplify_factor=0.0)
    tris = 0
    for p in parts:
        p.data.calc_loop_triangles(); tris += len(p.data.loop_triangles)
    return {"fbx": path, "tris": tris, "clips": [a.name for a in actions]}


# ----------------------------------------------------------------------------------------------------- traffic side
def mirror_vehicle(obj, thin=0.025, gap=1.0):
    """The event vehicles were modelled with their doors on the left (+Y, local) and the lettering on the right.
    Brazil drives on the right: the bus stops with its doors at the curb, so the vehicle is mirrored across its
    centre line (local Y). Lettering would then read backwards: every lettering line (thin pieces lying on one face,
    grouped when closer than `gap`) is mirrored back across its own centre, so it reads right on the other side.
    Returns how many lettering groups were turned back."""
    me = obj.data
    bm = bmesh.new(); bm.from_mesh(me)
    for v in bm.verts:
        v.co.y = -v.co.y
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free(); me.update()
    isl = islands(obj)
    lo = Vector((min(i.lo.x for i in isl), min(i.lo.y for i in isl), min(i.lo.z for i in isl)))
    hi = Vector((max(i.hi.x for i in isl), max(i.hi.y for i in isl), max(i.hi.z for i in isl)))
    groups = []
    for axis, flip in ((1, 0), (0, 1)):          # side faces (thin in Y) flip in X; front/back faces flip in Y
        cand = [i for i in isl if i.size[axis] < thin and max(i.size[a] for a in range(3) if a != axis) < 1.2]
        parent = list(range(len(cand)))
        def root(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        others = [a for a in range(3) if a != axis]
        for a in range(len(cand)):
            for b in range(a + 1, len(cand)):
                A, B = cand[a], cand[b]
                if abs(A.center[axis] - B.center[axis]) > 0.02:
                    continue
                # same line of lettering: the letters overlap in height and follow each other closely
                if min(A.hi.z, B.hi.z) - max(A.lo.z, B.lo.z) > 0.3 * min(A.size.z, B.size.z) \
                        and max(A.lo[flip], B.lo[flip]) - min(A.hi[flip], B.hi[flip]) < gap:
                    parent[root(a)] = root(b)
        sets = {}
        for a in range(len(cand)):
            sets.setdefault(root(a), []).append(cand[a])
        # accents and dots sit apart from their letter: they join the line they hang over
        lines = [m for m in sets.values() if len(m) >= 2]
        for key, members in list(sets.items()):
            if len(members) != 1:
                continue
            s = members[0]
            for line in lines:
                if abs(line[0].center[axis] - s.center[axis]) <= 0.02 \
                        and min(m.lo[flip] for m in line) <= s.center[flip] <= max(m.hi[flip] for m in line) \
                        and min(m.lo.z for m in line) - 0.15 <= s.center.z <= max(m.hi.z for m in line) + 0.15:
                    line.append(s); del sets[key]; break
        for members in sets.values():
            if len(members) < 3:
                continue                           # lone thin plates (glass, lamps) are symmetric enough
            verts = set().union(*[m.verts.keys() for m in members])
            c = (min(m.lo[flip] for m in members) + max(m.hi[flip] for m in members)) / 2
            groups.append((flip, c, verts))
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    for flip, c, verts in groups:
        for vi in verts:
            v = bm.verts[vi]; co = v.co.copy(); co[flip] = 2 * c - co[flip]; v.co = co
        faces = {f for vi in verts for f in bm.verts[vi].link_faces}
        bmesh.ops.reverse_faces(bm, faces=list(faces))
    bm.to_mesh(me); bm.free(); me.update()
    return len(groups)
