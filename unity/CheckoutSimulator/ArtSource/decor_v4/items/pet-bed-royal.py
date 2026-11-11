"""pet-bed-royal: "Cama real" - premium canopy bed for Caramelo. Carved gold-painted frame (moulded base on bun feet, an arched
headboard with scrolls, a tufted velvet panel and a raised crown pictogram with jewels), four thin turned gold posts with finials
carrying a domed canopy with a scalloped valance, two drapes gathered with gold tie-backs, a tufted velvet mattress with gold
tassels at the front corners, and a little crown-shaped golden pillow with pearls.
Fabric parts (mattress, headboard panel, canopy, valance, drapes) follow the colourway (navy default + teal / orange / rose
bakes); gold, jewels and the crown pillow never change.
Footprint half .50 x .38, height ~1.06 (Blender Z up, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import MATH, MIX, RAMP, SMOOTH, NOISE
import _lib_pet as P
import _lib_A as A
import _lib_F as F
import _lib_H as H

CONFIG = {"floor": "F4EFE4", "seed": 35}
FW, FD = .92, .72                 # frame outline
MW, MD, MZ, MH = .86, .66, .185, .11  # mattress
PX, PY = .435, .335               # posts
ZC = .985                         # canopy rail height
HB_Y = -.36                       # headboard centre plane (y)
CM_Z = .49                        # crown pictogram (bottom) on the headboard panel
VAL = .04                         # valance / canopy overhang beyond the posts


def hb_top(x, base=.585, rise=.16, half=.44):
    return base + rise * max(0.0, 1 - (x / half) ** 2) ** .6


def panel(name, half, z0, top, y, t, nx, paint, rows=2):
    rr = []
    for j in range(rows + 1):
        u = j / rows
        row = []
        for i in range(nx + 1):
            x = -half + 2 * half * i / nx
            row.append((x, y, z0 + (top(x) - z0) * u))
        rr.append(row)
    ob = P.loft(name, rr, paint, closed=False, smooth=False)
    dv4.mod_solidify(ob, t, offset=0.0)
    return ob


def outline_pts(pts2d, close=True):
    """2D polygon -> [(x, y, nx, ny)] with bisector normals (CCW polygon, outward)."""
    n = len(pts2d); out = []
    for i in range(n):
        p0, p1, p2 = pts2d[i - 1], pts2d[i], pts2d[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1]); e2 = (p2[0] - p1[0], p2[1] - p1[1])
        n1 = (e1[1], -e1[0]); n2 = (e2[1], -e2[0])
        l1 = math.hypot(*n1) or 1; l2 = math.hypot(*n2) or 1
        nx, ny = n1[0] / l1 + n2[0] / l2, n1[1] / l1 + n2[1] / l2
        l = math.hypot(nx, ny) or 1
        out.append((p1[0], p1[1], nx / l, ny / l))
    return out


def crown2d(w, h, band, n_edge=2):
    """Crown silhouette (CCW), origin at the middle of the band; three rounded spikes."""
    hw = w / 2
    key = [(-hw, 0), (hw, 0), (hw, band), (hw + .01, h * .88), (hw * .5, band + (h - band) * .2), (0, h),
           (-hw * .5, band + (h - band) * .2), (-hw - .01, h * .88), (-hw, band)]
    pts = []
    for i in range(len(key)):
        a, b = key[i], key[(i + 1) % len(key)]
        for k in range(n_edge):
            t = k / n_edge
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - band * .5))
    return pts, key


def relief(name, pts2d, depth, center, paint):
    """Raised plaque from a 2D outline (local XY, star-shaped around `center`): straight sides, a chamfered top, front = +Z."""
    cx, cy = center
    rings = [[(x, y, 0.0) for x, y in pts2d], [(x, y, depth * .55) for x, y in pts2d],
             [(cx + (x - cx) * .9, cy + (y - cy) * .9, depth) for x, y in pts2d], [(cx, cy, depth)]]
    return P.loft(name, rings, paint, smooth=False)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.34)
    gold = P.paint_gilt("Gold")
    gold_c = P.paint_gilt("GoldCarved", base="DDAA3A", dark="A8781F")
    ruby = H.paint_gloss("Ruby", "C8303A", dark="6E1018", light="FFB0B0", hl=.6, var=.1)
    emerald = H.paint_gloss("Emerald", "1F9A8E", dark="0B4F48", light="B9F2EA", hl=.6, var=.1)
    pearl = H.paint_gloss("Pearl", "F6F1E6", dark="CFC6B4", light="FFFFFF", hl=.6, var=.05)
    plush_gold = H.paint_plush("CrownPillow", base="E5B33C", dark="A8781F", light="FFE08A", thread="8A5A12", nap=.15)

    def mattress(st, pal):
        return A.paint_tufted("Mattress_" + st, base=pal["base"], dark=pal["dark"], light=pal["light"], px=.19, py=.26,
                              origin=(0.0, 0.0), dimple_r=.026, crease=.012)

    def hb_panel(st, pal):
        return A.paint_tufted("Headboard_" + st, base=pal["alt"], dark=pal["dark"], light=pal["light"], px=.12, py=.15,
                              origin=(0.0, HB_Y, .40), axis="XZ", dimple_r=.02, crease=.009)

    def drape(st, pal):
        def deco(c, col):
            nt = c.nt
            band = P.MUL(nt, SMOOTH(nt, c.z, ZC - .035, ZC - .025), SMOOTH(nt, c.z, ZC - .005, ZC - .015))
            return MIX(nt, P.MUL(nt, band, .85), col, "E0B040")
        return P.paint_cloth("Canopy_" + st, pal, "base", kind="velvet", decorate=deco, sheen=.3)

    mat_p = P.fabric(mattress)
    hb_p = P.fabric(hb_panel)
    can_p = P.fabric(drape)

    # ---- moulded gold base on bun feet
    ol = P.rrect_pts(FW, FD, .07, 3, 4, 3)
    prof = [(-.02, .062), (.012, .078), (.014, .092), (.002, .102), (0.0, .165), (.013, .18), (.0, .2), (-.032, .2)]
    P.loft("Frame", [P.ring_at(ol, o, z) for o, z in prof], gold_c)
    foot = [(0, 0), (.022, 0), (.036, .014), (.04, .034), (.034, .052), (.024, .066), (0, .07)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.lathe("Foot", foot, seg=6, loc=(sx * .38, sy * .28, 0), paint=gold)
    # ---- posts with finials and the canopy rail
    post = [(0, 0), (.028, 0), (.03, .012), (.028, .2), (.034, .214), (.026, .232), (.016, .26), (.015, .6), (.022, .615),
            (.015, .63), (.014, ZC - .02), (.02, ZC - .008), (0, ZC)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.lathe("Post", post, seg=6, loc=(sx * PX, sy * PY, 0), paint=gold)
            dv4.sphere("Finial", .021, loc=(sx * PX, sy * PY, ZC + .03), seg=8, rings=4, paint=gold)
            dv4.cylinder("FinialNeck", .012, .02, loc=(sx * PX, sy * PY, ZC - .002), seg=6, paint=gold)
    P.piping("Rail", [(PX, PY, ZC), (-PX, PY, ZC), (-PX, -PY, ZC), (PX, -PY, ZC)], r=.011, paint=gold)
    # ---- canopy: domed top + scalloped valance
    nx, ny = 6, 4
    rows = []
    for j in range(ny + 1):
        v = -1 + 2 * j / ny
        row = []
        for i in range(nx + 1):
            u = -1 + 2 * i / nx
            dome = .07 * (1 - u * u) * (1 - v * v) + .012 * math.cos(u * math.pi * 4) * (1 - v * v)
            row.append((u * (PX + VAL), v * (PY + VAL), ZC + .006 + dome))
        rows.append(row)
    top = P.loft("CanopyTop", rows, can_p, closed=False)
    dv4.mod_solidify(top, .008, offset=0.0)
    F.scallop_strip_rect("Valance", -PX - VAL, PX + VAL, -PY - VAL, PY + VAL, ZC + .012, .09, can_p, n_w=6, n_d=5, thickness=.006,
                         segs_per=4)
    # ---- drapes at the back posts, gathered by gold tie-backs
    for sx in (-1, 1):
        cols, nrow = 6, 8
        zt, ztie, zb = ZC - .005, .48, .015
        rr = []
        for j in range(nrow + 1):
            u = j / nrow
            z = zt + (zb - zt) * u
            if z > ztie:
                k = (zt - z) / (zt - ztie); w = .27 + (.05 - .27) * (k * k * (3 - 2 * k)); xp = .457 + .008 * k
            else:
                k = (ztie - z) / (ztie - zb); w = .05 + (.14 - .05) * k ** .8; xp = .465 + .045 * k ** .7
            amp = .006 + .022 * (.27 - w) / .22 if z > ztie else .012 + .01 * k
            row = []
            for i in range(cols + 1):
                t = i / cols
                y = -PY - .015 + t * w
                x = sx * (xp + amp * math.sin(t * math.pi * 3.0 + .4))
                row.append((x, y, z))
            rr.append(row)
        ob = P.loft("Drape", rr, can_p, closed=False)
        dv4.mod_solidify(ob, .006, offset=0.0)
        dv4.torus("TieBack", .036, .007, loc=(sx * .462, -PY + .012, ztie), seg=14, minor=5, paint=gold, scale=(.75, 1, 1))
        dv4.sphere("TieKnot", .013, loc=(sx * .49, -PY + .02, ztie - .01), seg=8, rings=5, paint=gold)
    # ---- headboard: arched gold board, tufted velvet panel, bead moulding, scrolls, crown pictogram
    panel("Headboard", .44, .05, hb_top, HB_Y, .04, 14, gold_c)
    yf = HB_Y + .02
    inner_top = lambda x: hb_top(x, .52, .135, .36)
    panel("HeadPanel", .36, .25, inner_top, yf + .004, .012, 12, hb_p)
    bead = [(-.36, yf + .01, .25), (.36, yf + .01, .25)]
    for i in range(1, 12):
        x = .36 - .72 * i / 12
        bead.append((x, yf + .01, inner_top(x)))
    P.piping("Bead", bead, r=.009, paint=gold)
    for sx in (-1, 1):
        dv4.tube("Scroll", dv4.spiral((sx * .395, yf + .006, .5), .004, .045, 1.4, n=11, a0=math.pi * 1.5, plane="XZ", ccw=sx < 0),
                 radius=.008, res=6, paint=gold, resolution=1)
    pts, key = crown2d(.17, .12, .04, 2)
    i0 = P.mark()
    relief("CrownMark", [(x, y + .02) for x, y in pts], .016, (0.0, .006), gold)
    P.place(i0, (0, yf + .004, CM_Z), (90, 0, 180))
    for (x, y), m in zip(((-.045, .0), (0, .0), (.045, .0)), (emerald, ruby, emerald)):
        dv4.sphere("Jewel", .011, loc=(x, yf + .021, CM_Z + .02 + y), scale=(1, .6, 1), seg=8, rings=5, paint=m)
    for x, y in ((key[3][0], key[3][1]), (0, key[5][1]), (key[7][0], key[7][1])):
        dv4.sphere("CrownBall", .011, loc=(-x, yf + .012, CM_Z + y + .008), seg=8, rings=5, paint=gold)
    # ---- tufted velvet mattress, tassels at the front corners
    ol = P.rrect_pts(MW, MD, .07, 2, 4, 3)
    P.cushion("Mattress", ol, MH, z0=MZ, e=.035, bulge=.008, puff=.02, paint=mat_p, bottom=False)
    for sx in (-1, 1):
        x = sx * (MW / 2 - .03)
        dv4.tube("TasselCord", [(x, MD / 2 - .01, MZ + MH * .62), (x, MD / 2 + .068, MZ + MH * .5)], radius=.004, res=6, paint=gold,
                 kind="POLY", resolution=1)
        tl = [(0, 0), (.014, 0), (.022, .012), (.024, .03), (.016, .05), (.01, .056), (.013, .062), (.01, .072), (0, .074)]
        dv4.lathe("Tassel", tl, seg=8, loc=(x, MD / 2 + .072, MZ + MH * .5 - .074), paint=gold)
    # ---- crown pillow leaning on the headboard
    i0 = P.mark()
    cp, ck = crown2d(.25, .17, .075, 2)
    P.cushion("CrownPillow", outline_pts(cp), .055, e=.016, bulge=.004, puff=.012, inner=(.7, .35), paint=plush_gold)
    for x, y in (ck[3], ck[5], ck[7]):
        dv4.sphere("Pearl", .012, loc=(x * .97, y - .075 * .5 - .004, .03), seg=8, rings=5, paint=pearl)
    for x, m in ((-.06, emerald), (0.0, ruby), (.06, emerald)):
        dv4.sphere("PillowJewel", .012, loc=(x, 0.0, .066), scale=(1, 1, .55), seg=8, rings=5, paint=m)
    P.place(i0, (.0, -.30, MZ + MH + .075 * .5 + .004), (74, 0, 180))
    return {"name": "PetBedRoyal", "tex": 1024, "budget": 6000, "floor": "F4EFE4", "styles": P.STYLES}
