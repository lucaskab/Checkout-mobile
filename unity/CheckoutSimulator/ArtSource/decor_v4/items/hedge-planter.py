"""hedge-planter: slatted wooden planter box (corner posts, iron bands, feet) with a neatly clipped boxwood hedge, soil ring and
a few stray leaves. Footprint half .80 x .30, height <= 1.1 (Blender: X across, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_I as L

CONFIG = {"floor": "C9C3B8", "seed": 22}


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.22, light=.36)
    wood_x = dv4.paint_wood("WoodX", base="B06A37", dark="5A3418", light="E0A65A", scale=4.0, dist=2.5, along="X", edge="E6BE86", tint=.3)
    wood_y = dv4.paint_wood("WoodY", base="B06A37", dark="5A3418", light="E0A65A", scale=4.0, dist=2.5, along="Y", edge="E6BE86", tint=.3)
    post_p = dv4.paint_wood("Post", base="8E5330", dark="4A2A12", light="BF8146", scale=5.0, along="Z", edge="D9A66A", tint=.1)
    iron = dv4.paint_iron("Iron", base="2A313A", mid="4A5560", edge="A9B4BC", rust_amt=.35)
    soil = dv4.paint_soil("Soil")
    hedge = L.paint_foliage("Hedge", dark="163D19", base="378A2B", light="82C847", cell=55.0, top=.38, clumps=16.0)
    leaf_p = dv4.paint_leaf("Leaf", base="3E9238", dark="22602A", light="86C851", vein="C2E59A", veins=4)

    W, Dp, H = 1.56, .56, .46        # box outer size, height
    # corner posts (slightly taller than the slats, chamfered tops)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.cube("Post%d%d" % (sx, sy), (.075, .075, H + .03), loc=(sx * (W / 2 - .0375), sy * (Dp / 2 - .0375), (H + .03) / 2 + .012),
                     paint=post_p, bevel=.01, segs=2)
            dv4.cube("Foot%d%d" % (sx, sy), (.06, .06, .024), loc=(sx * (W / 2 - .0375), sy * (Dp / 2 - .0375), .012), paint=iron, bevel=.005)
    # slats: three per side with a 1 cm gap, long sides grain along X, short sides along Y
    sl_h = (H - .05) / 3 - .01
    for i in range(3):
        z = .05 + i * (sl_h + .01) + sl_h / 2
        for sy in (-1, 1):
            dv4.cube("SlatY%d_%d" % (i, sy), (W - .15, .03, sl_h), loc=(0, sy * (Dp / 2 - .015), z), paint=wood_x, bevel=.006, segs=2)
        for sx in (-1, 1):
            dv4.cube("SlatX%d_%d" % (i, sx), (.03, Dp - .15, sl_h), loc=(sx * (W / 2 - .015), 0, z), paint=wood_y, bevel=.006, segs=2)
    # top rim trim (a lighter frame of planks lying flat) and iron straps around the posts
    dv4.cube("RimY1", (W + .02, .07, .028), loc=(0, Dp / 2 - .02, H + .04), paint=wood_x, bevel=.007, segs=2)
    dv4.cube("RimY2", (W + .02, .07, .028), loc=(0, -Dp / 2 + .02, H + .04), paint=wood_x, bevel=.007, segs=2)
    dv4.cube("RimX1", (.07, Dp + .02, .028), loc=(W / 2 - .02, 0, H + .04), paint=wood_y, bevel=.007, segs=2)
    dv4.cube("RimX2", (.07, Dp + .02, .028), loc=(-W / 2 + .02, 0, H + .04), paint=wood_y, bevel=.007, segs=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for z in (.10, .36):
                dv4.cube("StrapX%d%d%s" % (sx, sy, z), (.09, .012, .035), loc=(sx * (W / 2 - .0375), sy * (Dp / 2 - .003), z), paint=iron, bevel=0)
                dv4.cube("StrapY%d%d%s" % (sx, sy, z), (.012, .09, .035), loc=(sx * (W / 2 - .003), sy * (Dp / 2 - .0375), z), paint=iron, bevel=0)
                dv4.sphere("Rivet%d%d%s" % (sx, sy, z), .007, loc=(sx * (W / 2 + .004), sy * (Dp / 2 - .0375), z), scale=(.5, 1, 1), seg=6, rings=3, paint=iron)
    # soil, slightly bumpy, just under the rim
    s = dv4.patch("Soil", W - .1, Dp - .1, 14, 6, loc=(0, 0, H - .02), paint=soil)
    dv4.mod_displace(s, strength=.02, size=.08, mid=.5)
    # ---- the clipped hedge (sways from the soil)
    sw = "Anim Sway"; dv4.pivot(sw, (0, 0, H - .02))
    hz = .56
    hs = (W - .2, Dp - .14, hz)
    hc = (0, 0, H - .03 + hz / 2)
    bm = L.rounded_box_bm(hs, r=.13, segs=4, cuts=1)
    samples = L.surface_samples(bm, 46, min_dist=.09, top_bias=.3)
    h = dv4.from_bm("Hedge", bm, hedge, sw, hc, smooth=True)
    dv4.mod_displace(h, strength=.045, size=.11, mid=.5)
    # stray leaves sprouting from the clipped surface (placed on the box surface, pushed out past the displacement)
    for i, (p, nrm) in enumerate(samples):
        if nrm.z < -.2:
            continue
        q = (hc[0] + p.x + nrm.x * .008, hc[1] + p.y + nrm.y * .008, hc[2] + p.z + nrm.z * .008)
        yaw = math.degrees(math.atan2(nrm.y, nrm.x))
        pitch = math.degrees(math.asin(max(-1, min(1, nrm.z))))
        LL = RNG.uniform(.06, .09)
        dv4.leaf("Stray%d" % i, LL, LL * .62, loc=q, rot=(pitch - 30 + RNG.uniform(-10, 20), RNG.uniform(-30, 30), yaw - 90 + RNG.uniform(-30, 30)),
                 paint=leaf_p, out=sw, shape="spade", bend=.3, cup=.3, thickness=.003, nl=3, nw=2)
    return {"name": "HedgePlanter", "tex": 1024, "budget": 6000, "floor": "C9C3B8"}
