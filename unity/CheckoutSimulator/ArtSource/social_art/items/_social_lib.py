"""_social_lib: shared pieces of the three "invite reward" decorations (social v1).

  * paints(): the shared palette (navy powder-coat / painted wood, thin gold, cream, warm wood, marble, foliage, flowers)
  * emblem(): the friendship emblem, two shopping bags leaning together under a small heart, on a cream medallion with a
    gold rim. It is all geometry (no text, no letters); it faces +Y (the customer side) and stands in the plane y = y0.
  * shrub() / flower_ring(): planter fillings.
  * person(): a chunky figure in the style of the game's own characters (big round head, round belly, short limbs), used
    for the statue of invite-reward-5.
Blender Z up, metres, front = +Y (dv4 contract).
"""
import math
import dv4
from dv4 import RNG
import _lib_E as E
import _lib_D as LD

NAVY = "1D2B4F"
GOLD = "D3A53D"


def paints():
    P = {}
    P["navy"] = E.paint_painted("Navy", NAVY, light="6F86BE", dark="0A1124", variation=.18, sheen=.14)
    P["navy_wood"] = dv4.paint_wood("NavyWood", base="22325A", dark="111A33", light="3A4E80", scale=4.0, dist=2.0, along="Z",
                                   edge="6F86BE", tint=.12)
    P["gold"] = dv4.paint_gold("Gold", base=GOLD, dark="8E6418", light="FFE59A")
    P["cream"] = E.paint_painted("Cream", "F4EBD8", light="FFFFFF", dark="C9B998", variation=.14, sheen=.1)
    P["wood"] = dv4.paint_wood("Wood", base="B9743F", dark="6B4128", light="E2A95C", scale=4.0, dist=2.2, along="X", tint=.25)
    P["kraft"] = E.paint_painted("Kraft", "C9A06A", light="E6C899", dark="8A6436", variation=.25, sheen=.08)
    P["soil"] = dv4.paint_soil("Soil")
    P["leaf"] = dv4.paint_leaf("Leaf", base="3E8E3B", dark="1E5A2A", light="86C654", veins=5)
    P["canopy"] = E.paint_canopy("Boxwood", base="3F8C36", dark="1B4A22", light="8CCB4E")
    P["stem"] = dv4.paint_flat("Stem", "4E8A34", "2E5A24", variation=.3)
    P["throat"] = dv4.paint_flat("Throat", "5A1F3A", "2A0C1A", variation=.2)
    P["centre"] = E.paint_petal("Centre", "F2C23F", "B57A18", "FFE58A")
    P["pink"] = E.paint_petal("PetalPink", "EE8FAE", "C2567E", "FFC6D8")
    P["white"] = E.paint_petal("PetalWhite", "FBF8F1", "C9BFAE", "FFFFFF")
    P["purple"] = E.paint_petal("PetalPurple", "8E6CCF", "5A3E96", "C7AEF0")
    P["coral"] = E.paint_petal("PetalCoral", "EC7A5C", "B04A30", "FFB49A")
    return P


# ------------------------------------------------------------------------------------------------- friendship emblem
def _bag_pts(w_top, w_bot, h, r=.0):
    return [(-w_bot / 2, 0.0), (w_bot / 2, 0.0), (w_top / 2, h), (-w_top / 2, h)]


def _xz(x, z, cx, cz, a):
    """Rotate (x, z) by a degrees in the emblem plane and move to (cx, cz)."""
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return (cx + x * c - z * s, cz + x * s + z * c)


def emblem(name, x0, y0, z0, s, P, field="cream", rim="gold", bag_a="navy", bag_b="kraft", heart="gold", depth=1.0, disc=True):
    """Friendship emblem centred at (x0, y0, z0), radius s, facing +Y. depth scales the relief."""
    t = .05 * s * depth
    if disc:
        dv4.cylinder(name + "Disc", s, t, loc=(x0, y0, z0), rot=(-90, 0, 0), seg=32, paint=P[field], bevel=t * .4)
        dv4.torus(name + "Rim", s, .075 * s, loc=(x0, y0 + t, z0), rot=(90, 0, 0), seg=28, minor=5, paint=P[rim])
    yf = y0 + t + .02 * s * depth
    # two bags leaning into each other, overlapping a little in the middle
    for k, (side, key) in enumerate(((-1, bag_a), (1, bag_b))):
        a = -13 * side
        cx, cz = x0 + side * .23 * s, z0 - .48 * s
        w_top, w_bot, h = .36 * s, .44 * s, .58 * s
        pts = [_xz(x, z, 0, 0, a) for x, z in _bag_pts(w_top, w_bot, h)]
        bag = E.flat_shape("%sBag%d" % (name, k), pts, depth=.07 * s * depth, loc=(cx, yf + k * .012 * s, cz), rot=(90, 0, 0),
                           paint=P[key])
        dv4.mod_bevel(bag, .012 * s, 1)
        # fold line at the top of the bag (a thin strip)
        fx0, fz0 = _xz(-w_top / 2 + .02 * s, h - .07 * s, cx, cz, a)
        fx1, fz1 = _xz(w_top / 2 - .02 * s, h - .07 * s, cx, cz, a)
        dv4.tube("%sFold%d" % (name, k), [(fx0, yf + .04 * s * depth + k * .012 * s, fz0), (fx1, yf + .04 * s * depth + k * .012 * s, fz1)],
                 radius=.012 * s, res=6, paint=P["cream" if key != "cream" else "kraft"], kind="POLY", resolution=1)
        # rope handle: an arch above the bag mouth
        hp = []
        for i in range(7):
            u = i / 6
            hx = -w_top * .3 + w_top * .6 * u
            hz = h + math.sin(math.pi * u) * .2 * s
            hp.append(_xz(hx, hz, cx, cz, a))
        dv4.tube("%sHandle%d" % (name, k), [(px, yf + k * .012 * s, pz) for px, pz in hp], radius=.022 * s, res=5, paint=P[key],
                 resolution=3)
    # the heart they share
    hpts = E.heart_pts(.17 * s, 24)
    E.flat_shape(name + "Heart", [(x, y) for x, y in hpts], depth=.09 * s * depth, loc=(x0, yf + .03 * s, z0 + .42 * s), rot=(90, 0, 0),
                 paint=P[heart])


# ------------------------------------------------------------------------------------------------- planting
def shrub(name, loc, r, P, squash=.9, subdiv=3):
    ob = dv4.icosphere(name, r, loc=loc, scale=(1, 1, squash), subdiv=subdiv, paint=P["canopy"])
    dv4.mod_displace(ob, strength=r * .16, size=r * .45, mid=.5)
    return ob


def flower_ring(name, cx, cy, z, rx, ry, n, P, cols=("pink", "white", "coral"), size=.055, seed=0):
    for i in range(n):
        a = 2 * math.pi * i / n + RNG.uniform(-.15, .15)
        x, y = cx + math.cos(a) * rx, cy + math.sin(a) * ry
        h = RNG.uniform(.04, .09)
        top = (x + math.cos(a) * .02, y + math.sin(a) * .02, z + h)
        E.stem("%sS%d" % (name, i), (x, y, z - .01), top, P["stem"], radius=.005)
        col = cols[(i + seed) % len(cols)]
        tilt = (math.degrees(math.sin(a)) * -.5, math.degrees(math.cos(a)) * .5, 0)
        if col == "white":
            E.daisy("%sF%d" % (name, i), size, top, P["white"], P["centre"], rot=(tilt[0] * 40, tilt[1] * 40, RNG.uniform(0, 360)))
        else:
            E.petunia("%sF%d" % (name, i), size, top, P[col], P["throat"], rot=(tilt[0] * 40, tilt[1] * 40, RNG.uniform(0, 360)))
        dv4.leaf("%sL%d" % (name, i), RNG.uniform(.07, .1), .05, loc=(x, y, z), rot=(55, 0, math.degrees(a) - 90), paint=P["leaf"],
                 shape="spade", bend=.3, cup=.15, thickness=.003, nl=3, nw=2)


# ------------------------------------------------------------------------------------------------- statue figures
def _limb(name, pts, r, paint, taper=(1.0, .85)):
    return dv4.tube(name, pts, radius=r, res=10, paint=paint, resolution=4, taper=[(0, taper[0]), (1, taper[1])])


def mitten(name, loc, r, paint, rot=(0, 0, 0), open_=True):
    """Chunky cartoon hand: a flattened palm, a thumb, and (open) four fat finger bumps."""
    x, y, z = loc
    dv4.sphere(name + "Palm", r, loc=loc, scale=(1, .55, 1.1), seg=14, rings=10, paint=paint, rot=rot)
    a = math.radians(rot[1])
    dv4.sphere(name + "Thumb", r * .42, loc=(x - r * .95 * math.cos(a), y + r * .1, z - r * .1), scale=(1, .8, 1.3), seg=10, rings=6,
               paint=paint, rot=(0, 30, 0))
    if open_:
        for i in range(4):
            fx = (-.45 + i * .3) * r
            dv4.sphere("%sF%d" % (name, i), r * .26, loc=(x + fx, y, z + r * 1.05 + (.06 - abs(fx) * .3) * r), scale=(1, .8, 1.5),
                       seg=8, rings=6, paint=paint)


def person(name, x0, y0, z0, k, paint, wave="right", cap=True, apron=True, mustache=True, bag=None, hold=None):
    """Chunky figure standing at (x0, y0, z0), height ~1.05 * k. wave: which arm is raised ('right' / 'left' / None).
    hold: (x, y, z) world point the lowered hand reaches for (holding hands). bag: paint of a little shopping bag held in
    the lowered hand (if hold is None)."""
    def P_(x, y, z):
        return (x0 + x * k, y0 + y * k, z0 + z * k)
    # shoes and legs
    for s in (-1, 1):
        dv4.sphere(name + "Shoe%d" % s, .085 * k, loc=P_(s * .095, .035, .045), scale=(.75, 1.15, .5), seg=14, rings=8, paint=paint)
        dv4.cylinder(name + "Leg%d" % s, .068 * k, .26 * k, loc=P_(s * .095, 0, .06), seg=14, paint=paint, bevel=.02 * k)
    # body: round belly (lathe) and the apron over it
    body = [(0, .29), (.15, .29), (.205, .34), (.235, .43), (.24, .52), (.225, .61), (.19, .68), (.13, .73), (.06, .755), (0, .76)]
    b = dv4.lathe(name + "Body", [(r * k, z0 + z * k) for r, z in body], seg=28, loc=(x0, y0, 0), paint=paint)
    if apron:
        # apron: a bib and a skirt hugging the belly on the front (a partial lathe a hair larger)
        ap = []
        for i in range(12):
            u = i / 11
            ap.append((.245 + .02 * math.sin(math.pi * u), .31 + u * .37))
        bm = _arc_lathe([(r * k, z0 + z * k) for r, z in ap], -62, 62, 14)
        dv4.from_bm(name + "Apron", bm, paint, loc=(x0, y0, 0), rot=(0, 0, 90))
        dv4.torus(name + "Belt", .238 * k, .016 * k, loc=P_(0, 0, .5), seg=28, minor=6, paint=paint)
        dv4.cube(name + "Pocket", (.12 * k, .03 * k, .08 * k), loc=P_(0, .245, .42), paint=paint, bevel=.012 * k)
    # neck + head
    dv4.cylinder(name + "Neck", .07 * k, .06 * k, loc=P_(0, 0, .74), seg=14, paint=paint)
    hz = .93
    dv4.sphere(name + "Head", .2 * k, loc=P_(0, .005, hz), scale=(1, .96, 1.02), seg=22, rings=14, paint=paint)
    dv4.sphere(name + "Nose", .038 * k, loc=P_(0, .195, hz - .02), scale=(1.05, 1, .9), seg=10, rings=7, paint=paint)
    for s in (-1, 1):
        dv4.sphere(name + "Ear%d" % s, .05 * k, loc=P_(s * .195, 0, hz - .01), scale=(.5, .8, 1), seg=10, rings=6, paint=paint)
        dv4.sphere(name + "Eye%d" % s, .024 * k, loc=P_(s * .07, .182, hz + .04), scale=(1, .5, 1.2), seg=8, rings=6, paint=paint)
        dv4.sphere(name + "Cheek%d" % s, .05 * k, loc=P_(s * .11, .15, hz - .05), scale=(1, .6, .8), seg=10, rings=6, paint=paint)
    # smile: a shallow arc
    sm = [P_(math.sin(math.radians(a)) * .07, .186 - (1 - math.cos(math.radians(a))) * .05, hz - .085 + (1 - math.cos(math.radians(a))) * .09)
          for a in range(-60, 61, 20)]
    dv4.tube(name + "Smile", sm, radius=.011 * k, res=6, paint=paint, resolution=2)
    if mustache:
        for s in (-1, 1):
            dv4.sphere(name + "Must%d" % s, .05 * k, loc=P_(s * .045, .19, hz - .055), scale=(1.3, .55, .6), rot=(0, s * 18, 0), seg=10,
                       rings=6, paint=paint)
    if cap:
        capp = [(0, 0), (.19, 0), (.2, .03), (.19, .09), (.15, .13), (0, .14)]
        dv4.lathe(name + "Cap", [(r * k, z) for r, z in [(rr, z0 + (hz + .1 + zz) * k) for rr, zz in capp]], seg=24, loc=(x0, y0, 0),
                  paint=paint)
        dv4.cylinder(name + "Brim", .12 * k, .02 * k, loc=P_(0, .17, hz + .095), rot=(-8, 0, 0), seg=18, paint=paint, scale=(1, .7, 1))
    else:
        # hair tuft
        for i in range(3):
            dv4.sphere(name + "Hair%d" % i, .07 * k, loc=P_((-.06 + i * .06), -.02, hz + .17), scale=(1, 1, .7), seg=10, rings=6,
                       paint=paint)
    # arms
    for s in (-1, 1):
        sh = P_(s * .2, 0, .64)
        raised = (wave == "right" and s == 1) or (wave == "left" and s == -1)
        if raised:
            el = P_(s * .34, .02, .76)
            hd = P_(s * .38, .05, .96)
            _limb(name + "Arm%d" % s, [sh, el, hd], .055 * k, paint)
            mitten(name + "Hand%d" % s, P_(s * .385, .06, 1.02), .06 * k, paint, rot=(0, s * -12, 0), open_=True)
        else:
            if hold is not None:
                hd = hold
                el = ((sh[0] + hd[0]) / 2 + s * .03 * k, (sh[1] + hd[1]) / 2 + .02 * k, (sh[2] + hd[2]) / 2 - .02 * k)
            else:
                el = P_(s * .27, .02, .5)
                hd = P_(s * .29, .05, .37)
            _limb(name + "Arm%d" % s, [sh, el, hd], .055 * k, paint)
            dv4.sphere(name + "Fist%d" % s, .062 * k, loc=hd, scale=(1, .9, 1), seg=12, rings=8, paint=paint)
            if bag is not None and hold is None:
                bx, by, bz = hd
                dv4.cube(name + "Bag", (.16 * k, .08 * k, .17 * k), loc=(bx + s * .01 * k, by, bz - .14 * k), paint=bag, bevel=.012 * k)
                dv4.tube(name + "BagHandle", [(bx - .045 * k, by, bz - .06 * k), (bx, by, bz + .01 * k), (bx + .045 * k, by, bz - .06 * k)],
                         radius=.01 * k, res=6, paint=bag, resolution=3)


def _arc_lathe(profile, a0, a1, n):
    """Partial lathe (degrees a0..a1 around Z, 0 = +X) of a [(r, z)] profile, open."""
    import bmesh
    bm = bmesh.new()
    rings = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        rings.append([bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)) for r, z in profile])
    for i in range(n):
        for j in range(len(profile) - 1):
            f = bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][j + 1], rings[i][j + 1]))
            f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.012)
    return bm
