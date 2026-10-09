"""Queda de energia: the utility truck's insulated boom holds the lineman up at the blown transformer.

Rig_BucketTruck = Energia_BucketTruck (static) + Energia_BucketBoom split into
  Root -> Turret (turntable) -> LowerBoom (pin on the turret) -> UpperBoom (knuckle) -> Basket (kept level)
  with two hydraulic rams. Clip "Work" (6 s loop): the operator nudges the basket closer to the transformer,
  holds while the lineman works, eases back. The basket bone is where the game seats the lineman.
"""
import math
from mathutils import Vector, Matrix

HINGE = Vector((0.15, 0, 0.70))
KNUCKLE = Vector((-0.95, 0, 3.71))
BASKET_PIN = Vector((-3.40, 0, 4.14))
BASKET_FLOOR = Vector((-3.95, 0, 3.17))
RAMS = {"LowerRam": ("Turret", "LowerBoom"), "UpperRam": ("LowerBoom", "UpperBoom")}
RAM_OVERLAP = 0.10
SWING, LOWER, UPPER = 70, 0, 26   # basket floor ~3.6 m up, 3.7 m out over the sidewalk, 3.7 m behind the turret


def part_of(isl):
    def box(a, b):
        return isl.inside(Vector(a), Vector(b), pad=0.03)
    if isl.count == 16:
        if box((-0.52, -0.07, 0.44), (-0.23, 0.07, 1.39)): return "LowerRamBarrel"
        if box((-0.60, -0.04, 1.25), (-0.39, 0.04, 2.06)): return "LowerRamRod"
        if box((-1.15, -0.05, 2.57), (-0.29, 0.05, 3.47)): return "UpperRamBarrel"
        if box((-1.70, -0.03, 3.30), (-0.98, 0.03, 4.06)): return "UpperRamRod"
    if isl.hi.z <= 0.8 and isl.lo.x >= -0.42:
        return "Turret"
    if isl.lo.x <= -3.5 or box((-3.61, -0.12, 3.57), (-3.31, 0.12, 4.12)):
        return "Basket"
    if box((-3.43, -0.13, 3.57), (-0.92, 0.13, 4.27)) or box((-3.19, -0.14, 3.91), (-2.89, 0.14, 4.24)) \
            or box((-1.46, -0.14, 3.61), (-1.17, 0.14, 3.94)) or box((-3.45, -0.18, 4.09), (-3.36, 0.18, 4.19)):
        return "UpperBoom"
    return "LowerBoom"


def ram_anchors(barrel, rod):
    pb = [v.co.copy() for v in barrel.data.vertices]; pr = [v.co.copy() for v in rod.data.vertices]
    cb = sum(pb, Vector()) / len(pb); cr = sum(pr, Vector()) / len(pr)
    axis = (cr - cb).normalized()
    proj = lambda p: (p - cb).dot(axis)
    a = cb + axis * min(map(proj, pb)); b = cb + axis * max(map(proj, pr))
    lb = max(map(proj, pb)) - min(map(proj, pb)); lr = max(map(proj, pr)) - min(map(proj, pr))
    return a, b, lb, lr


def build():
    reset()
    truck = import_prop("Energia_BucketTruck")
    mirror_vehicle(truck)                    # right-hand traffic: the curb is on the truck's right (see vehicles.py)
    boom = import_prop("Energia_BucketBoom")
    A = boom.matrix_world.copy(); W = lambda p: A @ p
    parts = split(boom, part_of)
    rams = {r: ram_anchors(parts[r + "Barrel"], parts[r + "Rod"]) for r in RAMS}
    up = Vector((0, 0, 0.5))
    bones = [
        ("Root", (0, 0, 0), (0, 0, 0.6), None),
        ("Turret", W(Vector()), W(Vector()) + up, "Root"),
        ("LowerBoom", W(HINGE), W(KNUCKLE), "Turret"),
        ("UpperBoom", W(KNUCKLE), W(BASKET_PIN), "LowerBoom"),
        ("Basket", W(BASKET_PIN), W(BASKET_FLOOR), "UpperBoom"),
        ("Seat", W(BASKET_FLOOR), W(BASKET_FLOOR) + up, "Basket"),   # where the game stands the lineman
    ]
    for ram, (pa, pb) in RAMS.items():
        a, b = rams[ram][:2]
        bones += [(ram + "Barrel", W(a), W(b), pa), (ram + "Rod", W(b), W(a), pb)]
    arm = armature("Rig_BucketTruck", Matrix.Identity(4), bones)
    for ram in RAMS:
        for me, other in (("Barrel", "Rod"), ("Rod", "Barrel")):
            c = arm.pose.bones[ram + me].constraints.new('DAMPED_TRACK'); c.target = arm; c.subtarget = ram + other
    truck.name = "Energia_BucketTruck__Body"; attach(truck, arm, "Root")
    for name, o in parts.items():
        attach(o, arm, name)

    act = new_action(arm, "Work", frames=144)
    Y, Z = (0, 1, 0), (0, 0, 1)
    # (frame, turret, lower boom, upper boom) — the basket always cancels both booms to stay level. The turret is
    # swung SWING degrees over the curb (+Z turns the boom to the truck's right, the mirrored curb side), where the
    # transformer hangs on the pole; the operator nudges it closer, holds, and eases back.
    # LOWER/UPPER hold the basket floor ~3.6 m up over the sidewalk: the lineman's hands reach the transformer.
    keys = [(1, SWING, LOWER, UPPER), (30, SWING + 3, LOWER - 3, UPPER + 4), (54, SWING + 4, LOWER - 4, UPPER + 6),
            (96, SWING + 4, LOWER - 4, UPPER + 6), (120, SWING + 1, LOWER + 1, UPPER - 2), (145, SWING, LOWER, UPPER)]
    for f, turret, lower, upper in keys:
        pose(arm, "Turret", f, rot=(Z, turret))
        pose(arm, "LowerBoom", f, rot=(Y, lower))
        pose(arm, "UpperBoom", f, rot=(Y, upper))
        pose(arm, "Basket", f, rot=(Y, -(lower + upper)))
    smooth(act)
    sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, 144
    for f in range(1, 146):
        sc.frame_set(f)
        for ram in RAMS:
            a, b, lb, lr = rams[ram]
            pa = arm.pose.bones[ram + "Barrel"]; pr = arm.pose.bones[ram + "Rod"]
            L = ((arm.matrix_world @ pa.head) - (arm.matrix_world @ pr.head)).length
            pr.scale = (1, max(0.3, (L - lb + RAM_OVERLAP) / lr), 1); pr.keyframe_insert("scale", frame=f)
    linear(act, "scale")
    return arm, [truck] + list(parts.values()), [act]
