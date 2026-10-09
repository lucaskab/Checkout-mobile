"""Rua em obras: the backhoe digs the trench in front of the market and dumps the earth on the side.

Rig_Backhoe = Obras_Backhoe (body, static) + Obras_BackhoeArm split into its real parts:
  Root -> Swing (kingpost, turns the whole arm left/right)
        -> Boom (main arm, pitches at the kingpost pin)
          -> Stick (dipper, pitches at the boom tip)
            -> Bucket (curls at the stick tip)
  and three hydraulic rams (barrel + rod bones that always aim at each other, so the rams stretch and shrink
  with the arm instead of bending). Clip "Dig" (8 s loop).
"""
import math
from mathutils import Vector, Matrix

ARM_PIVOT = Vector((0, 0, 0))           # in Obras_BackhoeArm space
ELBOW = Vector((-1.70, 0, 1.65))
BUCKET_PIN = Vector((-2.90, 0, -0.70))
BUCKET_TIP = Vector((-2.56, 0, -1.56))
# hydraulic rams: barrel bone parent, rod bone parent (anchors are measured on the meshes)
RAMS = {
    "BoomRam": ("Swing", "Boom"),
    "StickRam": ("Boom", "Stick"),
    # The bucket ram drives a dogbone linkage; its rod end rides on the stick and slides out as the bucket curls.
    "BucketRam": ("Stick", "Stick"),
}
BUCKET_RAM_TRAVEL = 0.004  # metres of rod per degree of bucket curl
DIRT_AT = Vector((-2.74, 0, -1.02))  # inside the bucket (arm space)


def dirt_mesh():
    """A lumpy load of earth that fills the bucket (plain colour in the game: mesh name ends in __Dirt)."""
    import bmesh, random
    rnd = random.Random(7)
    me = bpy.data.meshes.new("Obras_BackhoeArm__Dirt"); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in bm.verts:
        n = v.co.normalized()
        v.co = Vector((n.x * 0.30, n.y * 0.26, n.z * 0.20)) * (1 + rnd.uniform(-0.18, 0.18))
        if v.co.z < -0.05:
            v.co.z = -0.05 + (v.co.z + 0.05) * 0.3
    bm.to_mesh(me); bm.free()
    m = bpy.data.materials.get("Dirt") or bpy.data.materials.new("Dirt"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.36, 0.24, 0.14, 1)
    me.materials.append(m)
    for poly in me.polygons:
        poly.use_smooth = True
    return me
RAM_OVERLAP = 0.12   # how deep the rod always stays inside the barrel


def ram_anchors(barrel, rod):
    """Barrel and rod lie on one axis: the anchors are the outer ends (barrel end away from the rod, rod end
    away from the barrel), measured on the vertices in arm space."""
    pb = [v.co.copy() for v in barrel.data.vertices]; pr = [v.co.copy() for v in rod.data.vertices]
    cb = sum(pb, Vector()) / len(pb); cr = sum(pr, Vector()) / len(pr)
    axis = (cr - cb).normalized()
    a = min(pb, key=lambda p: (p - cb).dot(axis)); b = max(pr, key=lambda p: (p - cb).dot(axis))
    a = cb + axis * (a - cb).dot(axis); b = cb + axis * (b - cb).dot(axis)
    lb = max((p - cb).dot(axis) for p in pb) - (a - cb).dot(axis)
    lr = (b - cb).dot(axis) - min((p - cb).dot(axis) for p in pr)
    return a, b, lb, lr


def part_of(isl):
    lo, hi, c = isl.lo, isl.hi, isl.center
    def box(a, b):
        return isl.inside(Vector(a), Vector(b), pad=0.03)
    # rams (octagonal tubes, 16 verts)
    if isl.count == 16:
        if box((-0.65, -0.06, -0.45), (-0.01, 0.06, 0.38)): return "BoomRamBarrel"
        if box((-1.02, -0.03, 0.22), (-0.50, 0.03, 0.92)): return "BoomRamRod"
        if box((-1.45, -0.05, 1.15), (-0.70, 0.05, 1.25)): return "StickRamBarrel"
        if box((-2.00, -0.03, 1.17), (-1.35, 0.03, 1.23)): return "StickRamRod"
        if box((-2.16, -0.05, 0.57), (-1.36, 0.05, 1.72)): return "BucketRamBarrel"
        if box((-2.67, -0.02, -0.21), (-2.00, 0.02, 0.76)): return "BucketRamRod"
    if hi.x <= 0.1 and lo.x >= -0.4 and hi.z <= 0.25:
        return "Swing"                     # kingpost block and its pin
    if box((-2.95, -0.15, -0.75), (-2.85, 0.15, -0.65)):
        return "Stick"                     # bucket pin rides on the stick
    if box((-2.92, -0.03, -0.5), (-2.58, 0.03, -0.2)):
        return "Stick"                     # dogbone link of the bucket ram
    if hi.z <= -0.45 or box((-3.09, -0.15, -0.84), (-2.75, 0.15, -0.54)):
        return "Bucket"                    # shell, side plates, teeth and the link
    if lo.x <= -1.39 and (lo.z < 0.6 or c.x < -1.95) or box((-1.68, -0.11, 1.7), (-1.42, 0.11, 2.0)) or box((-2.43, -0.13, 0.34), (-2.17, 0.13, 0.61)):
        return "Stick"
    return "Boom"


def build():
    reset()
    body = import_prop("Obras_Backhoe")
    arm_mesh = import_prop("Obras_BackhoeArm")
    A = arm_mesh.matrix_world.copy()
    W = lambda p: A @ p                      # arm space -> world
    parts = split(arm_mesh, part_of)
    rams = {r: ram_anchors(parts[r + "Barrel"], parts[r + "Rod"]) for r in RAMS}
    bones = [
        ("Root", (0, 0, 0), (0, 0, 0.6), None),
        ("Swing", W(ARM_PIVOT), W(ARM_PIVOT) + Vector((0, 0, 0.5)), "Root"),
        ("Boom", W(ARM_PIVOT), W(ELBOW), "Swing"),
        ("Stick", W(ELBOW), W(BUCKET_PIN), "Boom"),
        ("Bucket", W(BUCKET_PIN), W(BUCKET_TIP), "Stick"),
    ]
    bones.append(("Dirt", W(DIRT_AT), W(DIRT_AT) + Vector((0, 0, 0.3)), "Bucket"))
    for ram, (pa, pb) in RAMS.items():
        a, b = rams[ram][:2]
        bones.append((ram + "Barrel", W(a), W(b), pa))
        bones.append((ram + "Rod", W(b), W(a), pb))
    arm = armature("Rig_Backhoe", Matrix.Identity(4), bones)
    for ram in RAMS:
        for me, other in (("Barrel", "Rod"), ("Rod", "Barrel")):
            c = arm.pose.bones[ram + me].constraints.new('DAMPED_TRACK')
            c.target = arm; c.subtarget = ram + other; c.head_tail = 0.0
    attach(body, arm, "Root")
    body.name = "Obras_Backhoe__Body"
    for name, o in parts.items():
        attach(o, arm, name)                 # part names are bone names
    dirt = bpy.data.objects.new("Obras_BackhoeArm__Dirt", dirt_mesh())
    bpy.context.scene.collection.objects.link(dirt)
    dirt.matrix_world = A @ Matrix.Translation(DIRT_AT) @ Matrix.Rotation(math.radians(35), 4, 'Y')
    attach(dirt, arm, "Dirt"); parts["Dirt"] = dirt

    # Dig: reach out, bite, drag the stick in, curl, lift, swing to the pile, dump, come back (8 s).
    act = new_action(arm, "Dig", frames=192)
    Y, Z = (0, 1, 0), (0, 0, 1)
    keys = [
        (1,   0, -8,  -5, -15),
        (30,  0,  6, -25, -35),
        (66,  0, 10,  10,   5),
        (88,  0,  6,  18,  45),
        (112, 0, -22, 15,  50),
        (136, 40, -20,  5,  50),
        (152, 40, -14, -20, -30),
        (170, 40, -16, -10, -10),
        (193, 0, -8,  -5, -15),
    ]
    for f, swing, boom, stick, bucket in keys:
        pose(arm, "Swing", f, rot=(Z, swing))
        pose(arm, "Boom", f, rot=(Y, boom))
        pose(arm, "Stick", f, rot=(Y, stick))
        pose(arm, "Bucket", f, rot=(Y, bucket))
    # the bucket comes up full after the bite and empties over the pile
    for f, size in ((1, 0.01), (70, 0.01), (88, 1), (138, 1), (152, 0.01), (193, 0.01)):
        pb = arm.pose.bones["Dirt"]; pb.scale = (size, size, size); pb.keyframe_insert("scale", frame=f)
    smooth(act)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 192
    # The rod slides in the barrel: each frame it is as long as the gap between the barrel and its anchor, plus
    # a hidden part inside the barrel (keyed per frame, so Unity gets the exact length).
    bucket = arm.pose.bones["Bucket"]; rest = bucket.bone.matrix_local.to_quaternion()
    for f in range(1, 194):
        sc.frame_set(f)
        q = rest @ bucket.rotation_quaternion @ rest.inverted()
        curl = math.degrees(2 * math.atan2(q.y, q.w))
        rod = arm.pose.bones["BucketRamRod"]
        rod.location = (0, -BUCKET_RAM_TRAVEL * curl, 0); rod.keyframe_insert("location", frame=f)
        bpy.context.view_layer.update()
        for ram in RAMS:
            a, b, lb, lr = rams[ram]
            pa = arm.pose.bones[ram + "Barrel"]; pr = arm.pose.bones[ram + "Rod"]
            L = ((arm.matrix_world @ pa.head) - (arm.matrix_world @ pr.head)).length
            s = max(0.3, (L - lb + RAM_OVERLAP) / lr)
            pr.scale = (1, s, 1); pr.keyframe_insert("scale", frame=f)
    linear(act, "scale"); linear(act, "location")
    return arm, [body] + list(parts.values()), [act]


def preview(arm, frames=(1, 30, 66, 88, 112, 136, 152, 170)):
    studio((-2.8, -2.5, 0), (6.5, 2.5, 4.5), direction=(0.25, -1.0, 0.42), lens=40, distance=1.25)
    return render_frames("backhoe_dig", frames)
