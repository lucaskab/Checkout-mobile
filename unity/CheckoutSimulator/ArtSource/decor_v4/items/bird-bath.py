"""bird-bath: carved stone bird bath on a fluted baluster pedestal (octagonal plinth, scalloped bowl rim), still water, moss,
pebbles and grass at the foot, two little birds on "Anim Bob". Footprint half .35 x .35, height <= 1.1 (front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_I as L

CONFIG = {"floor": "C9C3B8", "seed": 23}


def build():
    dv4.FINISH.update(ao=.68, ao_dist=.3, light=.38)
    stone = dv4.paint_stone("Stone", base="DACBAC", dark="A08A62", light="F1E7D2", moss_amt=.9, moss_z=.3)
    stone_hi = dv4.paint_stone("StoneHi", base="E2D4B6", dark="AE9870", light="F5EDDB", moss_amt=.25)
    shaft_p = dv4.paint_stone("Shaft", base="E0D2B4", dark="B29C74", light="F3EAD8", moss_amt=.15, moss_z=.3, k_ao=.4, ao_dist=.08)
    def gravel_r(c):
        nt = c.nt
        d = dv4.VORO(nt, c.pos, 55.0, "F1", "Distance")
        col = dv4.RAMP(nt, d, [(.15, "EDE4D2"), (.45, "D2C7B2"), (.7, "B9AD98")])
        return dv4.MIX(nt, dv4.MATH(nt, "MULTIPLY", dv4.NOISE(nt, c.pos, 6.0, 2.0), .3), col, "A89C86")
    gravel = dv4.paint("Gravel", gravel_r, k_ao=.5, k_light=.3)
    water = dv4.paint_water("Water", deep="2E96BC", shallow="7AD3E6", scale=16.0, caustic=.5)
    peb = dv4.paint_pebbles("Pebbles", cols=("E9E0D1", "CFC4B3", "B5AA9A", "F2ECE1", "A9B6A0"))
    grass = L.paint_grass("Grass")
    blue = L.paint_bird("Bluebird", body="2E8FD1", belly="F7E6C4", wing="1F5FA0")
    robin = L.paint_bird("Robin", body="8A5A3C", belly="EC862E", wing="5E3B24")
    beak = dv4.paint_flat("Beak", "F2B544", dark="B8771A", variation=.3, edge="FFE08A")
    eye = dv4.paint_flat("Eye", "14161C", variation=0.0, edge="4A5060")

    # ---- pedestal: octagonal plinth, round base torus, fluted baluster shaft, collar, then the bowl
    dv4.lathe("Plinth", [(0, 0), (.30, 0), (.30, .055), (.27, .075), (.0, .075)], seg=8, rot=(0, 0, 22.5), paint=stone)
    dv4.lathe("Base", [(0, .075), (.21, .075), (.215, .10), (.19, .125), (.15, .14), (0, .14)], seg=28, paint=stone_hi)
    dv4.torus("BaseRing", .185, .022, loc=(0, 0, .128), seg=28, minor=7, paint=stone_hi)
    dv4.lathe("Shaft", [(0, .13), (.15, .13), (.135, .2), (.115, .3), (.11, .4), (.12, .5), (.14, .6), (.15, .645), (0, .645)], seg=30, paint=shaft_p,
              scallop=(12, .035))
    dv4.lathe("Collar", [(.0, .64), (.155, .64), (.165, .665), (.15, .70), (.11, .72), (.0, .72)], seg=28, paint=stone_hi)
    dv4.torus("CollarRing", .145, .014, loc=(0, 0, .70), seg=28, minor=6, paint=stone_hi)
    # ---- the bowl: wide shallow basin, carved scalloped lip, water at z .86
    bowl = [(0, .72), (.15, .72), (.23, .76), (.29, .80), (.32, .84), (.335, .885), (.32, .915), (.29, .92), (.265, .90), (.25, .865),
            (.19, .835), (.1, .825), (0, .82)]
    dv4.lathe("Bowl", bowl, seg=40, paint=stone_hi, scallop=(10, .035))
    dv4.lathe("Water", [(0, .862), (.14, .862), (.26, .862)], seg=36, paint=water)
    # ---- foot of the pedestal: a soil patch with pebbles, grass and a little moss
    s = dv4.lathe("Gravel", [(0, 0), (.33, 0), (.345, .012), (.33, .022), (0, .022)], seg=32, paint=gravel)
    for i in range(9):
        a = i * 40 + RNG.uniform(-12, 12); r = RNG.uniform(.26, .31)
        sz = RNG.uniform(.018, .03)
        dv4.sphere("Pebble%d" % i, sz, loc=(math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, sz * .35),
                   scale=(RNG.uniform(.9, 1.4), RNG.uniform(.8, 1.1), .55), seg=7, rings=4, paint=peb, rot=(0, 0, RNG.uniform(0, 360)))
    for i in range(5):
        a = i * 72 + 20 + RNG.uniform(-15, 15); r = .29
        L.grass_tuft("Grass%d_" % i, (math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, .02), grass, n=5, L=.1, spread=28)
    # ---- the birds (bob): one perched on the rim at the front-right, one standing in the water on the left
    b0 = "Anim Bob"; p0 = (.20, .16, .965); dv4.pivot(b0, p0)
    L.bird("Blue", p0, yaw=128, paint_body=blue, paint_beak=beak, paint_eye=eye, out=b0, size=1.45, pitch=0)
    b1 = "Anim Bob.001"; p1 = (-.11, -.05, .905); dv4.pivot(b1, p1)
    L.bird("Robin", p1, yaw=-20, paint_body=robin, paint_beak=beak, paint_eye=eye, out=b1, size=1.3, pitch=12)
    # ripples around the standing bird
    dv4.torus("Ripple", .095, .006, loc=(-.11, -.05, .864), seg=22, minor=4, paint=water)
    dv4.torus("Ripple2", .15, .005, loc=(-.11, -.05, .863), seg=26, minor=4, paint=water)
    return {"name": "BirdBath", "tex": 1024, "budget": 6000, "floor": "C9C3B8"}
