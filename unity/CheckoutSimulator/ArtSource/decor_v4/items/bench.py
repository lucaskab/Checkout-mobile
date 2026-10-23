"""bench: indoor waiting bench - navy velvet seat and back cushions with diamond tufting (real puffs, dimples and brass
buttons), warm turned-wood frame with armrests, brass foot caps and a row of brass tacks on the front rail.
Footprint half .80 x .30, height <= 1.2 (Blender: X across, front = +Y)."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_A as lib

CONFIG = {"floor": "F4EFE4", "seed": 9}
TILT = 5.0      # back lean (degrees)


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.22, light=.34)
    wood = dv4.paint_wood("Wood", base="A5602F", dark="5A3217", light="D49A5A", scale=4.0, dist=2.5, along="X", edge="E2B47E", tint=.2)
    wood_z = dv4.paint_wood("WoodZ", base="A5602F", dark="5A3217", light="D49A5A", scale=5.0, dist=2.5, along="Z", edge="E2B47E", tint=.2)
    brass = lib.paint_brass("Brass", base="C48E36", dark="6A4712", light="F5D277")
    sin, cos = math.sin(math.radians(TILT)), math.cos(math.radians(TILT))
    back_origin = (0.0, -.21, .69)
    seat_p = lib.paint_tufted("Seat", base="22365F", dark="111C3A", light="40588F", px=.17, py=.3333, origin=(0, 0), dimple_r=.032)
    back_p = lib.paint_tufted("Back", base="22365F", dark="111C3A", light="40588F", px=.17, py=.28, origin=back_origin, axis="XZ", tilt=TILT, dimple_r=.03)

    # ---- frame: turned legs with brass caps, seat rails, back posts, top rail, armrests
    leg = [(0, 0), (.03, 0), (.032, .018), (.024, .04), (.022, .11), (.036, .14), (.04, .18), (.034, .22), (.024, .26), (.024, .31),
           (.032, .34), (.032, .40), (0, .40)]
    for x in (-.70, .70):
        for y in (-.22, .22):
            dv4.lathe("Leg", leg, seg=14, loc=(x, y, .012), paint=wood_z)
            dv4.lathe("Cap", [(0, 0), (.034, 0), (.034, .014), (.03, .02), (0, .02)], seg=12, loc=(x, y, 0), paint=brass)
    dv4.cube("RailF", (1.50, .05, .075), loc=(0, .245, .395), paint=wood, bevel=.008, segs=2)
    dv4.cube("RailB", (1.50, .05, .075), loc=(0, -.245, .395), paint=wood, bevel=.008, segs=2)
    for x in (-.725, .725):
        dv4.cube("RailS", (.05, .54, .075), loc=(x, 0, .395), paint=wood, bevel=.008, segs=2)
        # back post leaning back with the cushion
        dv4.cube("Post", (.055, .05, .60), loc=(x, -.21 - sin * .30, .40 + cos * .30), rot=(TILT, 0, 0), paint=wood_z, bevel=.008, segs=2)
        dv4.sphere("PostBall", .031, loc=(x, -.21 - sin * .62, .40 + cos * .62), seg=12, rings=8, paint=wood_z)
        # armrest on a short turned post
        dv4.cube("Arm", (.065, .52, .035), loc=(x * 1.015, -.03, .665), paint=wood, bevel=.01, segs=2)
        dv4.lathe("ArmPost", [(0, 0), (.022, 0), (.03, .03), (.022, .08), (.02, .16), (.03, .2), (.024, .24), (0, .24)], seg=12,
                  loc=(x * 1.015, .18, .43), paint=wood_z)
    dv4.cube("TopRail", (1.56, .055, .085), loc=(0, -.21 - sin * .58, .40 + cos * .58), rot=(TILT, 0, 0), paint=wood, bevel=.012, segs=2)
    # brass tacks along the front rail
    for i in range(13):
        x = -.66 + i * .11
        dv4.sphere("Tack", .011, loc=(x, .272, .395), scale=(1, .5, 1), seg=8, rings=4, paint=brass)

    # ---- cushions (the seat sits on the rails, the back leans on the posts)
    lib.tufted_cushion("SeatCushion", 1.46, .50, .11, px=.17, rows=3, amp=.022, nx=30, ny=10, paint=seat_p, loc=(0, 0, .43),
                       bevel=.035, segs=3, button_r=.012, button_paint=brass, dimple=.014)
    lib.tufted_cushion("BackCushion", 1.42, .42, .085, px=.17, rows=3, amp=.02, nx=30, ny=8, paint=back_p, loc=back_origin,
                       rot=(-90 + TILT, 0, 0), bevel=.03, segs=3, button_r=.012, button_paint=brass, dimple=.013)
    return {"name": "Bench", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
