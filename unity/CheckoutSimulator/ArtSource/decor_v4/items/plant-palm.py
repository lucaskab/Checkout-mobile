"""plant-palm: tall areca palm - a clump of ringed canes rising from a hammered brass planter (navy enamel band, gold rope
rings, ring handles), each cane crowned by arching fronds made of real leaflets; the whole plant sways ("Anim Sway").
Footprint half .45 x .45, height <= 2.4."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_B as lib

lib.install_fixes()

CONFIG = {"floor": "F4EFE4", "seed": 13}
SOIL_Z = .52


def leaflet_w(t):
    return (t / .22) ** .5 if t < .22 else max(0.0, (1 - t) / .78) ** .62


def frond(k, p0, az, e0, Lf, rachis_p, leaf_p, out, pairs=9):
    """Arching frond: parabolic rachis from p0 at azimuth az (deg) and elevation e0 (deg); overlapping leaflets in pairs,
    held in a V (rolled up on both sides) and drooping toward their tips, so the frond reads as one feather."""
    a, e = math.radians(az), math.radians(e0)
    dx, dy, dz = math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)
    g = (Lf * dz + .18) / (Lf * Lf)            # tip ends about 18 cm below the start
    def pos(s):
        return (p0[0] + dx * Lf * s, p0[1] + dy * Lf * s, p0[2] + dz * Lf * s - g * (Lf * s) ** 2)
    def pitch(s):
        vz = dz * Lf - 2 * g * Lf * Lf * s
        vh = math.cos(e) * Lf
        return math.degrees(math.atan2(vz, vh))
    pts = [pos(s) for s in (0, .2, .4, .6, .8, 1.0)]
    dv4.tube("Rachis%d" % k, pts, radius=.012, res=4, paint=rachis_p, out=out, resolution=3, taper=[(0, 1.0), (.5, .8), (1, .4)])
    for i in range(pairs):
        s = .16 + .84 * i / (pairs - 1)
        p = pos(s); pt = pitch(s)
        L = .34 * (1 - .45 * s) * RNG.uniform(.92, 1.08)
        W = .085 * (1 - .35 * s)
        spread = 50 - 18 * s
        for side in (-1, 1):
            yaw = az + side * spread + RNG.uniform(-5, 5)
            lib.blade("Leaflet%d_%d_%d" % (k, i, side), L, W, leaflet_w, loc=p,
                      rot=(pt - 14 + RNG.uniform(-6, 6), side * 48 + RNG.uniform(-8, 8), yaw - 90), paint=leaf_p, out=out,
                      bend=.5, cup=.45, twist=side * .25, thickness=.003, nl=3, nw=2)
    p = pos(1.0)
    lib.blade("LeafletT%d" % k, .2, .05, leaflet_w, loc=p, rot=(pitch(1.0) - 12, 0, az - 90), paint=leaf_p, out=out,
              bend=.5, cup=.4, thickness=.003, nl=3, nw=2)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.36)
    brass = lib.paint_hammered_gold("Brass", base="E0A830", dark="9A6A1A", light="FFEAA0", dimple=26.0)
    gold = dv4.paint_gold("Gold")
    navy = dv4.paint_flat("Navy", "1D2B4F", dark="0D1530", variation=.2, scale=6.0, edge="5A6E9C", edge_k=.6, edge_r=.004)
    soil = dv4.paint_soil("Soil")
    peb = dv4.paint_pebbles("Pebbles", cols=("E9DFCB", "CFC3AE", "B8AB97", "F2EADA"))
    cane = lib.paint_cane("Cane", period=.1)
    rachis = lib.paint_cane("Rachis", base="7E9A3C", dark="4E6A22", light="B6CC6A", ring="7E9A3C", period=1.0)
    leaf = dv4.paint_leaf("Leaf", base="3C8F3A", dark="1E5A28", light="8CC956", vein="CBE69A", veins=3)

    # ---- planter: hammered brass urn with a stepped foot, navy enamel band framed by gold rope rings, two ring handles
    prof = [(0, 0), (.20, 0), (.235, .012), (.235, .04), (.215, .055), (.225, .075), (.25, .14), (.285, .30), (.31, .44), (.325, .50),
            (.345, .525), (.352, .555), (.34, .585), (.315, .59), (.30, .57), (.295, .53), (.29, SOIL_Z - .02), (0, SOIL_Z - .02)]
    dv4.lathe("Urn", prof, seg=32, paint=brass)
    dv4.lathe("Band", [(.283, .27), (.292, .28), (.300, .345), (.292, .355)], seg=32, paint=navy, cap=False)
    dv4.torus("Rope1", .287, .011, loc=(0, 0, .268), seg=32, minor=5, paint=gold)
    dv4.torus("Rope2", .300, .011, loc=(0, 0, .36), seg=32, minor=5, paint=gold)
    dv4.torus("FootRing", .232, .009, loc=(0, 0, .052), seg=32, minor=5, paint=gold)
    for sx in (-1, 1):
        dv4.sphere("Boss%d" % sx, .03, loc=(sx * .30, 0, .42), scale=(.7, 1, 1), seg=12, rings=8, paint=gold)
        dv4.torus("Handle%d" % sx, .045, .009, loc=(sx * .325, 0, .395), rot=(0, 90, 0), seg=16, minor=5, paint=gold)
    # soil, pebbles
    sl = dv4.patch("Soil", .60, .60, 12, 12, loc=(0, 0, SOIL_Z), paint=soil, disk=True)
    dv4.mod_displace(sl, strength=.025, size=.08, mid=.4)
    for i in range(7):
        a = i * .9 + RNG.random() * .5; r = RNG.uniform(.13, .25); s = RNG.uniform(.018, .03)
        dv4.sphere("Pebble%d" % i, s, loc=(math.cos(a) * r, math.sin(a) * r, SOIL_Z + s * .3), scale=(RNG.uniform(.9, 1.3), 1, .5),
                   seg=8, rings=5, paint=peb, rot=(0, 0, RNG.uniform(0, 360)))
    # ---- the palm (sways from the soil): three ringed canes in a tight clump, each crowned by 3-4 arching fronds
    sway = "Anim Sway"; dv4.pivot(sway, (0, 0, SOIL_Z))
    canes = [(20, 1.42, 4), (140, 1.68, 3), (260, 1.92, 4)]
    k = 0
    for az, h, n_fr in canes:
        a = math.radians(az)
        x0, y0 = math.cos(a) * .045, math.sin(a) * .045
        lean = .07 + (h - 1.0) * .05
        top = (math.cos(a) * lean, math.sin(a) * lean, h)
        dv4.tube("Cane%d" % az, [(x0, y0, SOIL_Z - .03), (x0 * 1.6, y0 * 1.6, SOIL_Z + (h - SOIL_Z) * .5), top], radius=.025, res=7,
                 paint=cane, out=sway, resolution=4, taper=[(0, 1.0), (1, .72)])
        dv4.sphere("Crown%d" % az, .028, loc=top, seg=8, rings=5, paint=rachis, out=sway)
        for j in range(n_fr):
            faz = az + 180 + (j - (n_fr - 1) / 2) * (360 / n_fr) * .8 + RNG.uniform(-12, 12)
            e0 = RNG.uniform(58, 70)
            Lf = RNG.uniform(.66, .76)
            frond(k, top, faz, e0, Lf, rachis, leaf, sway, pairs=9)
            k += 1
    return {"name": "PlantPalm", "tex": 1024, "budget": 15000, "floor": "F4EFE4"}
