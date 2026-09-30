"""Stock clerk (repositor) and cleaner (auxiliar de limpeza) built from the market's own Meshy workers.

Both start from the delivery worker (textures recoloured into Assets/Art/Staff/Models/Staff_*.png) and keep its
skeleton and hand-made Idle / Walking / Carry / Pickup / PutDown clips; restock, push, mop and reach-up are layered
on those clips by changing only the arms and torso, so the legs always move exactly like the other workers. The
rigid Meshy skin weights are blended across the joints so elbows and wrists bend without tearing.

Run inside the connected Blender (needs scripts/blender/build_interior_kit.py for the props):
    exec(open(r"C:/Checkout-mobile/scripts/blender/build_staff_characters.py").read())
Output: Assets/Art/Staff/Models/Staff_Clerk.fbx, Staff_Cleaner.fbx
"""
import math
import os

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

UNITY = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets"
WORKERS = os.path.join(UNITY, "Art", "Characters", "Meshy", "Workers")
OUT = os.path.join(UNITY, "Art", "Staff", "Models")
KIT = r"C:\Checkout-mobile\scripts\blender\build_interior_kit.py"

# Both use the delivery worker's body: it is the one Meshy worker whose arms and legs stay whole on big moves
# (carrying, pushing, reaching). The textures tell them apart: red shirt and navy overalls for the clerk, yellow
# shirt, cap and rubber gloves with green overalls for the cleaner (the courier outside wears orange and teal).
CHARACTERS = {
    "Staff_Clerk": {"base": "Worker_Delivery", "props": "boxes", "fit": False},
    "Staff_Cleaner": {"base": "Worker_Delivery", "props": "cleaning", "fit": False},
}
CARRY = ["CarryWalking", "CarryIdle", "Pickup", "PutDown"]
ARMS = ["UpperArm_L", "Forearm_L", "Hand_L", "UpperArm_R", "Forearm_R", "Hand_R"]

K = {"__name__": "staffkit"}
exec(open(KIT, encoding="utf-8").read(), K)


# ------------------------------------------------------------------------------------------- scene helpers
def fresh_scene():
    sc = bpy.data.scenes.get("STAFF2") or bpy.data.scenes.new("STAFF2")
    bpy.context.window.scene = sc
    for o in list(sc.objects):
        bpy.data.objects.remove(o)
    # Leftovers of earlier builds anywhere in the file would steal the names (Staff_Clerk_Rig.001...).
    for o in list(bpy.data.objects):
        if o.name.startswith(("Staff_", "Box_", "Mop", "Bulb", "Cutter")):
            bpy.data.objects.remove(o)
    for a in list(bpy.data.actions):
        if a.users == 0 or "|" in a.name or a.name.startswith("S2_"):
            bpy.data.actions.remove(a)
    for block in (bpy.data.meshes, bpy.data.armatures):
        for d in list(block):
            if d.users == 0:
                block.remove(d)
    sc.render.fps = 24
    return sc


def import_worker(name):
    before = set(bpy.data.objects)
    acts_before = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=os.path.join(WORKERS, name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == "ARMATURE")
    body = next(o for o in new if o.type == "MESH")
    acts = {}
    for a in bpy.data.actions:
        if a in acts_before:
            continue
        logical = a.name.split("|")[-1].split(".")[0]
        acts.setdefault(logical, a)
    return rig, body, acts, new


def fcurves(action):
    try:
        return list(action.fcurves)
    except Exception:
        return [fc for layer in action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]


def frames(action):
    a, b = action.frame_range
    return int(round(a)), int(round(b))


# ------------------------------------------------------------------------------------------- clips
def sample(rig, action, frame):
    rig.animation_data.action = action
    bpy.context.scene.frame_set(int(frame))
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in rig.pose.bones}


def bake(rig, name, length, pose_at):
    """New clip `name` of `length` frames; pose_at(frame) -> {bone: (loc, quat)}."""
    action = bpy.data.actions.new("S2_" + name)
    action.use_fake_user = True
    poses = [pose_at(f) for f in range(length + 1)]
    rig.animation_data.action = action
    for f, pose in enumerate(poses):
        for bone, (loc, quat) in pose.items():
            pb = rig.pose.bones[bone]
            pb.location = loc
            pb.rotation_quaternion = quat
            pb.keyframe_insert("location", frame=f + 1)
            pb.keyframe_insert("rotation_quaternion", frame=f + 1)
    return action


def delta(q, x=0, y=0, z=0):
    return q @ Euler((math.radians(x), math.radians(y), math.radians(z)), "XYZ").to_quaternion()


def absolute(x=0, y=0, z=0):
    return Euler((math.radians(x), math.radians(y), math.radians(z)), "XYZ").to_quaternion()


def retarget(rig, source, name, hip_scale):
    """Copies a clip made on another market rig (same bones), scaling the hip bob to this body."""
    f0, f1 = frames(source)
    def pose_at(f):
        pose = sample(rig, source, f0 + f)
        loc, quat = pose["Torso"]
        pose["Torso"] = (loc * hip_scale, quat)
        return pose
    return bake(rig, name, f1 - f0, pose_at)


def layered(rig, base, name, length, arms):
    """Legs and head from `base` (looped), arms and torso from arms(t, pose) with t in 0..1."""
    f0, f1 = frames(base)
    span = f1 - f0
    def pose_at(f):
        t = f / length
        pose = sample(rig, base, f0 + (t * span if length else 0))
        arms(t, pose)
        return pose
    return bake(rig, name, length, pose_at)


def set_rot(pose, bone, q):
    pose[bone] = (pose[bone][0], q)


def push_arms(t, pose):
    # Both hands forward at waist height on the cart handle; a slight forward lean with the legs kept upright.
    lean = 5
    set_rot(pose, "Torso", delta(pose["Torso"][1], lean))
    for side in ("L", "R"):
        set_rot(pose, "Thigh_" + side, delta(pose["Thigh_" + side][1], -lean))
        set_rot(pose, "UpperArm_" + side, absolute(-30, 0, 20 if side == "L" else -20))
        set_rot(pose, "Forearm_" + side, absolute(-18))
        set_rot(pose, "Hand_" + side, absolute(8))


def mop_arms(t, pose):
    # Both hands on the stick in front of the belly (one high, one low), swept left and right by turning the torso.
    s = math.sin(t * math.tau)
    set_rot(pose, "Torso", delta(pose["Torso"][1], 8, 14 * s))
    set_rot(pose, "Head", delta(pose["Head"][1], -4, -7 * s))
    for side in ("L", "R"):
        set_rot(pose, "Thigh_" + side, delta(pose["Thigh_" + side][1], -8, -14 * s))
    # Angles found by searching the wrist positions on this rig: low fist by the belly, high fist at the chest.
    set_rot(pose, "UpperArm_R", absolute(-20 - 4 * s, 0, -40))
    set_rot(pose, "Forearm_R", absolute(-10, 0, 20))
    set_rot(pose, "UpperArm_L", absolute(-30 + 4 * s, 0, 50))
    set_rot(pose, "Forearm_L", absolute(-10, 0, 20))


def restock_arms(t, pose):
    # Placing items on the shelf: one hand then the other reaches forward to shelf height, the torso turning a little.
    r = max(0.0, math.sin(t * math.tau)); l = max(0.0, -math.sin(t * math.tau))
    s = math.sin(t * math.tau)
    set_rot(pose, "Torso", delta(pose["Torso"][1], 4, 7 * s))
    for side in ("L", "R"):
        set_rot(pose, "Thigh_" + side, delta(pose["Thigh_" + side][1], -4, -7 * s))
    for side, k in (("R", r), ("L", l)):
        set_rot(pose, "UpperArm_" + side, absolute(-12 - 68 * k, 0, (-4 if side == "R" else 4)))
        set_rot(pose, "Forearm_" + side, absolute(-18 - 22 * k))
        set_rot(pose, "Hand_" + side, absolute(-10 * k))


def reach_arms(t, pose):
    # Both arms up over the head (changing a bulb), a small turn of the wrist.
    s = math.sin(t * math.tau)
    set_rot(pose, "UpperArm_R", absolute(-168, 0, -6))
    set_rot(pose, "Forearm_R", absolute(-8 - 6 * s))
    set_rot(pose, "Hand_R", absolute(0, 25 * s))
    set_rot(pose, "UpperArm_L", absolute(-160, 0, 10))
    set_rot(pose, "Forearm_L", absolute(-14 + 6 * s))
    set_rot(pose, "Head", delta(pose["Head"][1], 16))


# ------------------------------------------------------------------------------------------- props
def realize_model(name, build):
    m = K["Model"](name)
    build(m)
    objs = K["realize"](m)
    for o in objs:
        o.name = name if len(objs) == 1 else name + "_" + o.name
    if len(objs) > 1:
        for o in objs[1:]:
            o.parent = objs[0]
    return objs[0]


def part_centre(body, group):
    """Centre of the evaluated (posed) mesh part skinned mostly to `group`."""
    gi = body.vertex_groups[group].index
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    pts = [ev.matrix_world @ me.vertices[v.index].co for v in body.data.vertices
           if any(g.group == gi and g.weight > .6 for g in v.groups)]
    ev.to_mesh_clear()
    return sum(pts, Vector()) / max(1, len(pts))


def attach(obj, rig, bone, world_matrix):
    obj.matrix_world = world_matrix
    bpy.context.view_layer.update()
    keep = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    bpy.context.view_layer.update()
    pb = rig.pose.bones[bone]
    bone_world = rig.matrix_world @ pb.matrix @ Matrix.Translation((0, rig.data.bones[bone].length, 0))
    obj.matrix_parent_inverse = bone_world.inverted()
    obj.matrix_world = keep


def box_kinds():
    box, ball, cyl, lathe, text = K["box"], K["ball"], K["cyl"], K["lathe"], K["text_lite"]
    W, H, D = .5, .3, .36

    def cardboard(m):
        box(m, (W, H, D), (0, 0, 0), "T_IK_Cardboard", .012)
        box(m, (W + .004, .012, .07), (0, H / 2, 0), "C_C9A26A", .002)
        box(m, (.16, .09, .004), (-.1, 0, -D / 2 - .002), "C_FBF8F1", .002)
        box(m, (.12, .012, .004), (-.1, .02, -D / 2 - .004), "C_D74A3C", .001)

    def crate(m, key, top):
        box(m, (W, .03, D), (0, -H / 2 + .015, 0), key, .006)
        for sx in (-1, 1):
            box(m, (.025, H, D), (sx * (W / 2 - .012), 0, 0), key, .005)
        for sz in (-1, 1):
            for yy in (-.08, .06):
                box(m, (W, .07, .02), (0, yy, sz * (D / 2 - .01)), key, .004)
        top(m)

    def produce(m):
        def top(m):
            for i in range(6):
                x = -.15 + (i % 3) * .15; z = -.08 + (i // 3) * .16
                ball(m, (x, .06, z), (.14, .12, .14), "C_5DAE3E" if i % 2 else "C_2F6F2C", 10, 6)
            for i, (x, z) in enumerate(((-.1, 0), (.08, .08), (.16, -.1))):
                ball(m, (x, .12, z), (.08, .075, .08), "C_D74A3C", 10, 6)
        crate(m, "T_IK_WoodLight", top)

    def meat(m):
        box(m, (W, H, D), (0, 0, 0), "T_IK_Styrofoam", .02)
        box(m, (W + .01, .03, D + .01), (0, H / 2, 0), "C_F4EFE4", .01)
        box(m, (.2, .1, .004), (0, 0, -D / 2 - .003), "C_D64541", .002)
        text(m, "CARNES", (0, 0, -D / 2 - .006), .045, "C_FBF8F1", .002)

    def fish(m):
        box(m, (W, H, D), (0, 0, 0), "T_IK_Styrofoam", .02)
        box(m, (W + .01, .03, D + .01), (0, H / 2, 0), "C_2E86DE", .01)
        for i in range(5):
            ball(m, (-.18 + i * .09, H / 2 + .03, -.1 + (i % 2) * .12), (.07, .04, .07), "C_E8F6FB", 6, 4)
        box(m, (.2, .1, .004), (0, 0, -D / 2 - .003), "C_2E86DE", .002)
        text(m, "PEIXE", (0, 0, -D / 2 - .006), .045, "C_FBF8F1", .002)

    def bakery(m):
        lathe(m, [(0, 0), (.2, 0), (.24, .16), (.25, .18)], (0, -H / 2, 0), "T_IK_Wicker", 16, cap=False)
        for i, (x, z, r) in enumerate(((-.08, -.04, 0), (.08, .05, 30), (0, .0, 90))):
            ball(m, (x, -.02, z), (.24, .1, .12), "T_IK_Crust", 12, 6, yaw=r)

    def drinks(m):
        def top(m):
            for i in range(6):
                x = -.16 + (i % 3) * .16; z = -.08 + (i // 3) * .16
                lathe(m, [(0, 0), (.035, 0), (.035, .16), (.015, .22), (.015, .26), (0, .26)], (x, -H / 2 + .03, z), "C_27AE60" if i % 3 else "C_8E2240", 10)
        crate(m, "C_D74A3C", top)

    def frozen(m):
        box(m, (W, H, D), (0, 0, 0), "C_FBF8F1", .03)
        box(m, (W + .01, .04, D + .01), (0, H / 2, 0), "C_3E8FD6", .015)
        box(m, (.22, .1, .004), (0, 0, -D / 2 - .003), "C_3E8FD6", .002)
        text(m, "CONGELADOS", (0, 0, -D / 2 - .006), .03, "C_FBF8F1", .002)

    def dairy(m):
        def top(m):
            for i, (x, z) in enumerate(((-.12, -.06), (.12, .06), (0, .02))):
                cyl(m, .09, .07, (x, .05, z), "T_IK_Cheese", 16, .01)
        crate(m, "C_F2C23F", top)

    return {"caixa": cardboard, "hortifruti": produce, "carne": meat, "peixe": fish, "padaria": bakery,
            "bebidas": drinks, "congelados": frozen, "frios": dairy}


def blender_to_unity(p):
    return (-p.x, p.z, -p.y)


def mop_prop(m, low, high):
    """Mop through both fists (Blender world points), from above the top hand down to the floor."""
    d = (low - high).normalized()
    if d.z > -.55:  # keep the stick steep enough to reach the floor just in front of the feet
        d = Vector((d.x, d.y, 0)).normalized() * .6 + Vector((0, 0, -.8))
        d.normalize()
    top = high - d * .3
    k = (low.z - .06) / max(.05, -d.z)
    foot = low + d * k
    K["bar"](m, blender_to_unity(top), blender_to_unity(foot), .016, "C_2E86DE", 8)
    head = Vector((foot.x, foot.y, .04))
    K["box"](m, (.36, .05, .1), blender_to_unity(head), "C_F2C23F", .015)
    for i in range(10):
        x = -.16 + i * .0355
        a = head + Vector((-x, 0, 0))
        K["bar"](m, blender_to_unity(a), blender_to_unity(a + Vector((-x * .3, -.08 + .03 * (i % 3), -.035))), .012, "C_E8E2D0", 5)


def bulb_prop(m):
    K["ball"](m, (0, .05, 0), (.07, .09, .07), "E_FFF4DC", 10, 8)
    K["cyl"](m, .02, .04, (0, -.02, 0), "C_C9D2D6", 10, 0)


# ------------------------------------------------------------------------------------------- build
def paint(body, name):
    mat = bpy.data.materials.get(name + "_Body") or bpy.data.materials.new(name + "_Body")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    path = os.path.join(OUT, name + ".png")
    img = bpy.data.images.get(name + ".png")
    if img:
        img.filepath = path; img.reload()
    else:
        img = bpy.data.images.load(path)
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    body.data.materials.clear()
    body.data.materials.append(mat)


def boundary(body, a, b, band=.035):
    """Joint between two rigidly skinned parts: centre of the vertices of `a` and `b` that nearly touch."""
    idx = {g.name: g.index for g in body.vertex_groups}
    W = body.matrix_world
    pa = [W @ v.co for v in body.data.vertices if v.groups and v.groups[0].group == idx[a]]
    pb = [W @ v.co for v in body.data.vertices if v.groups and v.groups[0].group == idx[b]]
    # Grid lookup of b, then the a vertices within `band` of any b vertex (and vice versa).
    from collections import defaultdict
    def grid(ps):
        g = defaultdict(list)
        for p in ps: g[(int(p.x // band), int(p.y // band), int(p.z // band))].append(p)
        return g
    ga = grid(pa); gb = grid(pb)
    def near(p, g):
        k = (int(p.x // band), int(p.y // band), int(p.z // band))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in g.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                        if (p - q).length < band: return True
        return False
    seam = [p for p in pa if near(p, gb)] + [p for p in pb if near(p, ga)]
    if len(seam) < 6:
        return None
    return sum(seam, Vector()) / len(seam)


def fix_arm_weights(rig, body):
    """The auto-skin put some glove and cuff vertices (resting beside the hips) on the torso or thighs, so they stay
    behind when the arms lift. Anything out past the hips belongs to the arm: hand below the wrist, forearm below
    the elbow."""
    idx = {g.name: g.index for g in body.vertex_groups}
    arm_groups = {idx[n] for n in ARMS if n in idx}
    W = body.matrix_world; R = rig.matrix_world
    moved = 0
    for side, sign in (("L", -1), ("R", 1)):
        wrist = R @ rig.data.bones["Hand_" + side].head_local
        elbow = R @ rig.data.bones["Forearm_" + side].head_local
        limit = abs(wrist.x) - .13
        for v in body.data.vertices:
            p = W @ v.co
            if p.x * sign < limit or p.z > elbow.z + .05 or p.z < wrist.z - .45:
                continue
            if any(g.group in arm_groups and g.weight > .5 for g in v.groups):
                continue
            target = "Hand_" + side if p.z < wrist.z + .02 else "Forearm_" + side
            for g in list(v.groups):
                body.vertex_groups[g.group].remove([v.index])
            body.vertex_groups[target].add([v.index], 1.0, "REPLACE")
            moved += 1
    return moved


def smooth_weights(body, repeat=12):
    """Meshy workers come skinned rigidly (each vertex on one bone), which tears the mesh at elbows, wrists and
    knees on big moves. Blend the weights across every seam and renormalise so joints bend smoothly."""
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
    bpy.ops.object.vertex_group_smooth(group_select_mode="ALL", factor=.5, repeat=repeat, expand=.3)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def fit_joints(rig, body):
    """Meshy workers are skinned rigidly per bone, and their arm joints sit well below the real shoulder, elbow
    and wrist, which only shows on big arm moves (carrying, pushing, reaching). Move each arm joint to the seam
    between its two mesh parts so limbs turn where they bend."""
    chains = [("Torso", "UpperArm_L"), ("UpperArm_L", "Forearm_L"), ("Forearm_L", "Hand_L"),
              ("Torso", "UpperArm_R"), ("UpperArm_R", "Forearm_R"), ("Forearm_R", "Hand_R")]
    joints = {}
    for a, b in chains:
        p = boundary(body, a, b)
        if p is not None:
            joints[b] = rig.matrix_world.inverted() @ p
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bone, head in joints.items():
        eb = rig.data.edit_bones[bone]
        length = (eb.tail - eb.head).length
        eb.head = head
        eb.tail = head + Vector((0, 0, length))
        eb.roll = 0
    bpy.ops.object.mode_set(mode="OBJECT")
    return {k: [round(c, 3) for c in v] for k, v in joints.items()}


def build_character(name):
    spec = CHARACTERS[name]
    fresh_scene()
    rig, body, acts, _ = import_worker(spec["base"])
    drig, dbody, dacts, dnew = import_worker("Worker_Delivery")
    rig.name = name + "_Rig"; body.name = name + "_Body"; rig.data.name = name + "_RigData"
    paint(body, name)
    if spec.get("fit", True):
        fit_joints(rig, body)
    fix_arm_weights(rig, body)
    smooth_weights(body, spec.get("smooth", 12))
    hip = rig.data.bones["Torso"].head_local.z / drig.data.bones["Torso"].head_local.z
    rig.animation_data_create()
    clips = {}
    f0, f1 = frames(acts["Idle"])
    clips["Idle"] = bake(rig, "Idle", f1 - f0, lambda f: sample(rig, acts["Idle"], f0 + f))
    w0, w1 = frames(acts["Walking"])
    clips["Walking"] = bake(rig, "Walking", w1 - w0, lambda f: sample(rig, acts["Walking"], w0 + f))
    if "GetFromShelf" in acts:
        g0, g1 = frames(acts["GetFromShelf"])
        clips["Restock"] = bake(rig, "Restock", g1 - g0, lambda f: sample(rig, acts["GetFromShelf"], g0 + f))
    else:
        clips["Restock"] = layered(rig, acts["Idle"], "Restock", 48, restock_arms)
    for clip in CARRY:
        clips[clip] = retarget(rig, dacts[clip], clip, hip)
    clips["PushWalking"] = layered(rig, acts["Walking"], "PushWalking", w1 - w0, push_arms)
    clips["PushIdle"] = layered(rig, acts["Idle"], "PushIdle", 60, push_arms)
    clips["Mop"] = layered(rig, acts["Idle"], "Mop", 44, mop_arms)
    clips["ReachUp"] = layered(rig, acts["Idle"], "ReachUp", 48, reach_arms)
    for o in dnew:
        bpy.data.objects.remove(o)

    props = []
    if spec["props"] == "boxes":
        # Boxes held between the hands of the carry pose, on the torso so they ride with the body.
        rig.animation_data.action = clips["CarryIdle"]; bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
        palms = [part_centre(body, "Hand_L"), part_centre(body, "Hand_R")]
        mid = (palms[0] + palms[1]) / 2 + Vector((0, -.04, .1))
        for kind, fn in box_kinds().items():
            obj = realize_model("Box_" + kind, fn)
            # Labels (kit -Z side) face forward, away from the chest.
            attach(obj, rig, "Torso", Matrix.Translation(mid) @ Matrix.Rotation(math.pi, 4, "Z"))
            props.append(obj)
    else:
        rig.animation_data.action = clips["Mop"]; bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
        low, high = part_centre(body, "Hand_R"), part_centre(body, "Hand_L")
        if low.z > high.z:
            low, high = high, low
        mop = realize_model("Mop", lambda m: mop_prop(m, low, high))
        attach(mop, rig, "Hand_R", Matrix.Identity(4))
        props.append(mop)
        rig.animation_data.action = clips["ReachUp"]; bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
        hand = rig.matrix_world @ rig.pose.bones["Hand_R"].tail
        bulb = realize_model("Bulb", bulb_prop)
        attach(bulb, rig, "Hand_R", Matrix.Translation(hand + Vector((0, 0, .06))))
        props.append(bulb)
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
    # Only this character's clips go into the file.
    for a in list(bpy.data.actions):
        if not a.name.startswith("S2_"):
            bpy.data.actions.remove(a)
    for a in bpy.data.actions:
        a.name = a.name[3:]
    return rig, body, props, clips


def export(name, rig, body, props):
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in [rig, body] + props + [c for p in props for c in p.children]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), use_selection=True, object_types={"ARMATURE", "MESH"},
                             add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                             bake_anim_simplify_factor=0, axis_forward="-Z", axis_up="Y", path_mode="STRIP", use_mesh_modifiers=True,
                             mesh_smooth_type="OFF", use_armature_deform_only=True)


def build(names=("Staff_Clerk", "Staff_Cleaner"), do_export=True):
    out = {}
    for name in names:
        rig, body, props, clips = build_character(name)
        if do_export:
            export(name, rig, body, props)
        out[name] = {"clips": sorted(a.name for a in bpy.data.actions), "props": [p.name for p in props], "verts": len(body.data.vertices)}
    return out


if __name__ == "__main__":
    print(build())
