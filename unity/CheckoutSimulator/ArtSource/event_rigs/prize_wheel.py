"""Sorteio na porta: the prize wheel is pulled, spins about three turns, slows down with the flapper ticking
over the pegs, and stops on a prize; a pause, then the next customer pulls it again.

Rig_PrizeWheel = Sorteio_WheelStand (static) + Sorteio_WheelDisc on the "Disc" bone at the hub + the stand's
rubber flapper on the "Flapper" bone. Clip "Spin" (10 s loop). Disc and flapper angles are computed per frame,
so the flapper is pushed aside by every peg that really passes under it.
"""
import math
from mathutils import Vector, Matrix

HUB = Vector((0, -0.18, 1.75))          # stand space (the disc sits in front of the stand)
FLAP_PIN = Vector((0, -0.25, 2.70))
PEGS = 16
TURNS = 3
FRAMES = 240
PULL, STOP = 20, 170                       # spin from the pull to the stop, then rest
REST = 22.5                                # the pointer stops in the middle of a slice (8 slices)


def part_of(isl):
    if isl.inside(Vector((-0.08, -0.26, 2.42)), Vector((0.08, -0.24, 2.70)), pad=0.01):
        return "Flapper"
    return "Stand"


def build():
    reset()
    stand = import_prop("Sorteio_WheelStand")
    disc = import_prop("Sorteio_WheelDisc")
    S = stand.matrix_world.copy(); W = lambda p: S @ p
    parts = split(stand, part_of)
    # the disc is modelled around its hub: put it on the stand like the game does
    disc.matrix_world = S @ Matrix.Translation(HUB) @ (S.inverted() @ disc.matrix_world)
    disc.name = "Sorteio_WheelDisc__Disc"
    arm = armature("Rig_PrizeWheel", Matrix.Identity(4), [
        ("Root", (0, 0, 0), (0, 0, 0.5), None),
        ("Disc", W(HUB), W(HUB + Vector((0, -0.3, 0))), "Root"),
        ("Flapper", W(FLAP_PIN), W(FLAP_PIN + Vector((0, 0, -0.28))), "Root"),
    ])
    attach(parts["Stand"], arm, "Root"); parts["Stand"].name = "Sorteio_WheelStand__Stand"
    attach(parts["Flapper"], arm, "Flapper"); parts["Flapper"].name = "Sorteio_WheelStand__Flapper"
    attach(disc, arm, "Disc")

    act = new_action(arm, "Spin", frames=FRAMES)
    axis = (S.to_quaternion() @ Vector((0, 1, 0)))           # hub axis in world
    total = TURNS * 360.0
    step = 360.0 / PEGS
    prev = 0.0
    disc_bone = arm.pose.bones["Disc"]; disc_bone.rotation_mode = 'XYZ'
    for f in range(1, FRAMES + 2):
        t = f - 1
        if t <= PULL:                       # the pull: a short wind-back before the throw
            u = t / PULL; ang = -8 * math.sin(math.pi * u)
        elif t <= STOP:
            u = (t - PULL) / (STOP - PULL); ang = total * (1 - (1 - u) ** 3)
        else:
            ang = total
        speed = abs(ang - prev); prev = ang
        # Euler about the bone's own axis (along the hub): several turns stay continuous, no quaternion flips
        disc_bone.rotation_euler = (0, math.radians(ang + REST), 0)
        disc_bone.keyframe_insert("rotation_euler", frame=f)
        # flapper: each peg lifts it up to 28 degrees and lets it snap back; at speed it just flutters
        phase = ((ang + step / 2) % step) / step
        lift = phase / 0.75 if phase < 0.75 else (1 - phase) / 0.25
        flap = -28 * lift * min(1.0, speed / 1.5) if PULL < t <= STOP + 2 else 0
        pose(arm, "Flapper", f, rot=(axis, flap))
    linear(act, "rotation")
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, FRAMES
    return arm, [parts["Stand"], parts["Flapper"], disc], [act]
