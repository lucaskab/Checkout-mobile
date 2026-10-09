"""Vehicles that drive in the event scenes get real wheels and a sprung body, buses get working doors.

Rig_<Vehicle>: Root -> Body (pivot between the axles: the game pitches it when braking/accelerating)
                    -> Wheel_<F|R|R2>_<L|R> (one bone per wheel, rolled by the game from the distance driven)
                    -> Door_<n> (bus door leaves, clips "DoorsOpen" / "DoorsClose", 0.75 s each)
Wheels are found on the mesh: each tyre plus the rim/hub pieces inside its circle. Vehicles drive along +X in
Blender (the game turns them like the other props).

Right-hand traffic: the vehicles that stop at the market's curb (buses, the supplier truck, the operator's van, the
inspection car, the jam's cars don't matter) are mirrored across their centre line (rig_kit.mirror_vehicle) so the
doors open onto the curb when they drive on the right; their lettering is turned back so it still reads.
"""
import math
from mathutils import Vector, Matrix

# door leaves: (name, x range, hinge x, swing sign) in the prop's own space, leaves on the +Y side
DOORS = {
    "Rush_CityBus": [("Door_1L", (3.50, 4.18), 3.53, 1), ("Door_1R", (4.22, 4.90), 4.87, -1),
                     ("Door_2L", (-0.60, 0.08), -0.57, 1), ("Door_2R", (0.12, 0.80), 0.77, -1)],
    "Excursao_SchoolBus": [("Door_1L", (1.70, 2.18), 1.72, 1), ("Door_1R", (2.18, 2.66), 2.64, -1)],
}
DOOR_Y = {"Rush_CityBus": 1.25, "Excursao_SchoolBus": 1.18}
DOOR_ANGLE = -84   # leaves fold into the bus, like the city's buses


def find_wheels(isl):
    tyres = [i for i in isl if i.lo.z < 0.08 and abs(i.size.x - i.size.z) < 0.08 and i.size.x > 0.45 and i.size.y > 0.15]
    wheels = {}
    xs = sorted({round(t.center.x, 1) for t in tyres}, reverse=True)
    for t in tyres:
        axle = xs.index(round(t.center.x, 1))
        key = ("F" if axle == 0 else "R" if axle == 1 else f"R{axle}") + ("_L" if t.center.y > 0 else "_R")
        wheels.setdefault(key, []).append(t)
    return wheels


def part_of_factory(isl_all, wheels, prop, mirrored=False):
    doors = DOORS.get(prop, []); dy = DOOR_Y.get(prop, 99)
    def part_of(i):
        for key, tyres in wheels.items():
            for t in tyres:
                r = t.size.x / 2 + 0.01
                if i is t or (abs(i.center.x - t.center.x) < r and abs(i.center.z - t.center.z) < r
                              and max(i.size.x, i.size.z) <= t.size.x + 0.02 and abs(i.center.y - t.center.y) < 0.25):
                    return "Wheel_" + key
        for name, (x0, x1), hinge, sign in doors:
            on_side = i.hi.y <= -dy if mirrored else i.lo.y >= dy
            if on_side and i.lo.x >= x0 - 0.01 and i.hi.x <= x1 + 0.01 and i.size.z > 0.2 and i.lo.z > 0.3 and i.size.y < 0.1:   # thin: a leaf, not the mirror
                return name
        return "Body"
    return part_of


def rig_vehicle(prop, rig_name, mirrored=False):
    reset()
    o = import_prop(prop); S = o.matrix_world.copy(); W = lambda p: S @ Vector(p)
    lettering = mirror_vehicle(o) if mirrored else 0
    isl = islands(o)
    wheels = find_wheels(isl)
    parts = split(o, part_of_factory(isl, wheels, prop, mirrored))
    centers = {k: sum((t.center for t in v), Vector()) / len(v) for k, v in wheels.items()}
    axle_z = sum(c.z for c in centers.values()) / len(centers)
    mid = Vector(((max(c.x for c in centers.values()) + min(c.x for c in centers.values())) / 2, 0, axle_z))
    bones = [("Root", W((0, 0, 0)), W((0, 0, 0.5)), None), ("Body", W(mid), W(mid + Vector((0, 0, 0.6))), "Root")]
    for k, c in centers.items():
        out = Vector((0, 0.3 if c.y > 0 else -0.3, 0))
        bones.append(("Wheel_" + k, W(c), W(c + out), "Root"))
    side = -1 if mirrored else 1
    for name, (x0, x1), hinge, sign in DOORS.get(prop, []):
        p = Vector((hinge, side * (DOOR_Y[prop] + 0.04), 0.4))
        bones.append((name, W(p), W(p + Vector((0, 0, 1.6))), "Body"))
    arm = armature(rig_name, Matrix.Identity(4), bones)
    for name, o2 in parts.items():
        o2.name = f"{prop}__{name}"; attach(o2, arm, name)
    acts = []
    if prop in DOORS:
        up = S.to_quaternion() @ Vector((0, 0, 1))
        for clip, a, b in (("DoorsOpen", 0, 1), ("DoorsClose", 1, 0)):
            act = new_action(arm, clip)
            for f, u in ((1, a), (18, b)):
                for name, _, _, sign in DOORS[prop]:
                    pose(arm, name, f, rot=(up, side * sign * DOOR_ANGLE * u))
            smooth(act, cyclic=False)
            act.frame_start, act.frame_end = 1, 18
            acts.append(act)
    else:
        # parked engine idle: the body trembles a little (the game uses it while the car waits in the jam)
        act = new_action(arm, "Idle", frames=24)
        for f in range(1, 26):
            pose(arm, "Body", f, loc=(0, 0.006 * math.sin(2 * math.pi * f / 6), 0))
        linear(act, "location"); acts.append(act)
    return arm, list(parts.values()), acts


BUILDERS = {
    "Rig_CityBus": lambda: rig_vehicle("Rush_CityBus", "Rig_CityBus", mirrored=True),
    "Rig_SchoolBus": lambda: rig_vehicle("Excursao_SchoolBus", "Rig_SchoolBus", mirrored=True),
    "Rig_BoxTruck": lambda: rig_vehicle("Ofertas_BoxTruck", "Rig_BoxTruck", mirrored=True),
    "Rig_TelecomVan": lambda: rig_vehicle("Maquininha_TelecomVan", "Rig_TelecomVan", mirrored=True),
    "Rig_InspectionCar": lambda: rig_vehicle("Vigilancia_Car", "Rig_InspectionCar", mirrored=True),
    # the sound car drives the far (eastbound) lane: its lettering already faces the street
    "Rig_SoundVan": lambda: rig_vehicle("Som_Van", "Rig_SoundVan"),
    **{f"Rig_Car{c}": (lambda c=c: rig_vehicle("Transito_Car" + c, "Rig_Car" + c))
       for c in ("", "Blue", "Yellow", "White", "Teal", "Green")},
}
