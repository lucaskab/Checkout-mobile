"""Realistic Kit — plants: branching trees with bark and clumpy leaf canopies, box hedges, flowers, potted plants."""
import math, random, bmesh
from mathutils import Vector, Matrix
from rk_core import *


def leaf_clump(acc, c, size, seed, key="T_IK_R_Leaves", grp="Body"):
    """Irregular foliage clump: a displaced icosphere (lobes + small bumps) wrapped in the leaf texture."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3 if max(size) > .3 else 2, radius=1)
    ph = [rnd.random() * 6.28 for _ in range(9)]
    for v in bm.verts:
        n = v.co.normalized()
        lobes = .16 * math.sin(n.x * 3.1 + ph[0]) * math.sin(n.y * 2.7 + ph[1]) * math.sin(n.z * 3.3 + ph[2])
        bumps = .07 * math.sin(n.x * 9 + ph[3]) * math.sin(n.y * 8 + ph[4]) * math.sin(n.z * 10 + ph[5])
        flat = 1 - .22 * max(0, -n.z)          # flatter underside
        r = (1 + lobes + bumps) * flat
        v.co = Vector((n.x * size[0] * r, n.y * size[1] * r, n.z * size[2] * r))
    uv_box(bm, 1.6)
    place(bm, c)
    acc.add(bm, key, grp)


def tree(acc, base, height=3.2, spread=1.3, seed=1, grp="Body", trunk_r=.09):
    """Trunk with root flare that forks into 3–4 limbs; each limb ends in a leaf clump, plus a crown clump."""
    rnd = random.Random(seed)
    x, y, z = base
    # root flare
    for k in range(5):
        a = k * 1.2566 + rnd.random() * .4
        tube(acc, [(x, y, z + .18), (x + math.cos(a) * .12, y + math.sin(a) * .12, z + .05), (x + math.cos(a) * .22, y + math.sin(a) * .22, z - .01)],
             lambda s: trunk_r * (1 - .7 * s), "T_IK_R_Bark", 7, 2, grp)
    fork = z + height * .45
    lean = (rnd.uniform(-.08, .08), rnd.uniform(-.08, .08))
    tube(acc, [(x, y, z - .02), (x + lean[0] * .5, y + lean[1] * .5, z + height * .25), (x + lean[0], y + lean[1], fork)],
         lambda s: trunk_r * (1.15 - .35 * s), "T_IK_R_Bark", 10, 3, grp)
    tips = []
    n = rnd.choice((3, 4))
    for k in range(n):
        a = k * 2 * math.pi / n + rnd.uniform(-.4, .4)
        r = spread * rnd.uniform(.45, .7)
        tip = (x + lean[0] + math.cos(a) * r, y + lean[1] + math.sin(a) * r, fork + height * rnd.uniform(.28, .4))
        mid = (x + lean[0] + math.cos(a) * r * .4, y + lean[1] + math.sin(a) * r * .4, fork + height * .18)
        tube(acc, [(x + lean[0], y + lean[1], fork - .05), mid, tip], lambda s: trunk_r * .75 * (1 - .65 * s), "T_IK_R_Bark", 8, 3, grp)
        # a twig
        tw = (tip[0] + math.cos(a + 1) * .25, tip[1] + math.sin(a + 1) * .25, tip[2] + .15)
        tube(acc, [mid, tw], lambda s: trunk_r * .35 * (1 - .7 * s), "T_IK_R_Bark", 6, 0, grp)
        tips += [tip, tw]
    for i, t in enumerate(tips):
        s = spread * rnd.uniform(.42, .55)
        leaf_clump(acc, (t[0], t[1], t[2] + s * .25), (s, s, s * .8), seed * 31 + i, grp=grp)
    top = (x + lean[0], y + lean[1], fork + height * .5)
    leaf_clump(acc, top, (spread * .7, spread * .7, spread * .55), seed * 17, grp=grp)


def hedge(acc, p0, p1, width=.5, height=.6, seed=0, planter=True, grp="Body"):
    """Clipped box hedge on a timber planter, following the segment p0 -> p1 (on the ground)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    ang = math.degrees(math.atan2(d.y, d.x))
    c = (p0 + p1) / 2
    ph = .0
    if planter:
        rbox(acc, (L, width, .38), (c.x, c.y, .19), "T_IK_R_PlanksDark", .03, 3, rot=(0, 0, ang), grp=grp, uv=1.2)
        rbox(acc, (L + .04, width + .04, .04), (c.x, c.y, .39), "C_" + NAVY, .015, 2, rot=(0, 0, ang), grp=grp)
        z0 = .38
    else:
        z0 = 0
    rnd = random.Random(seed)
    bm = rbox_bm((L - .06, width - .08, height), .14, 4)
    for v in bm.verts:
        v.co.x += .025 * math.sin(v.co.y * 11 + v.co.z * 7 + seed)
        v.co.y += .025 * math.sin(v.co.x * 9 + v.co.z * 13 + seed)
        v.co.z += .02 * math.sin(v.co.x * 7 + v.co.y * 5 + seed) * (v.co.z > 0)
    uv_box(bm, 1.2)
    place(bm, (c.x, c.y, z0 + height / 2), (0, 0, ang))
    acc.add(bm, "T_IK_R_Hedge", grp)
    # a few blossoms
    for k in range(int(L * 3)):
        t = rnd.random()
        q = p0 + d * t
        flower(acc, (q.x + rnd.uniform(-.1, .1), q.y + rnd.uniform(-.1, .1), z0 + height + .01), rnd.choice(("F4A6C1", "FFFFFF", "F2C23F")), .035, grp)


def flower(acc, c, col, r=.04, grp="Body"):
    """Five rounded petals around a yellow centre."""
    x, y, z = c
    for k in range(5):
        a = k * 2 * math.pi / 5
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1)
        for v in bm.verts:
            v.co = Vector((v.co.x * r * .55, v.co.y * r * .35, v.co.z * r * .15))
        uv_box(bm)
        place(bm, (x + math.cos(a) * r * .55, y + math.sin(a) * r * .55, z), (0, 0, math.degrees(a) + 90))
        acc.add(bm, "C_" + col, grp)
    blob(acc, (r * .25, r * .25, r * .15), (x, y, z + r * .08), "C_F2B03D", 1, 0, 0, grp=grp)


def flower_bed(acc, c, size, seed=0, grp="Body"):
    """Timber bed with soil, leafy mounds and flowers."""
    x, y, _ = c
    w, d = size
    rbox(acc, (w, d, .42), (x, y, .21), "T_IK_R_PlanksDark", .03, 3, grp=grp, uv=1.2)
    rbox(acc, (w + .04, d + .04, .04), (x, y, .42), "C_" + NAVY, .015, 2, grp=grp)
    rbox(acc, (w - .08, d - .08, .03), (x, y, .41), "C_5B4030", .01, 1, grp=grp)
    rnd = random.Random(seed)
    for k in range(int(w * d * 12)):
        px, py = x + rnd.uniform(-w / 2 + .1, w / 2 - .1), y + rnd.uniform(-d / 2 + .1, d / 2 - .1)
        h = .12 + rnd.random() * .08
        tube(acc, [(px, py, .43), (px + rnd.uniform(-.02, .02), py, .43 + h)], .005, "C_3F7A2E", 4, 0, grp)
        for j in range(5):
            b = j * 1.256 + rnd.random()
            add_leaf(acc, (px, py, .44 + j * .02), (math.cos(b), math.sin(b), .35), size=.9, key="C_" + LEAF_GREENS[rnd.randrange(5)], grp=grp, roll=rnd.uniform(-.4, .4), rnd=rnd)
        flower(acc, (px, py, .44 + h), rnd.choice(("E15533", "F2B03D", "E86A9E", "FFFFFF", "8E6CCF")), .045, grp)


def potted_plant(acc, c, size=1.0, seed=0, grp="Body"):
    x, y, z = c
    lathe(acc, [(0, 0), (.14 * size, 0), (.17 * size, .28 * size), (.19 * size, .3 * size), (.18 * size, .31 * size)], c, "T_IK_Terracotta", 20, 1, cap_top=False, grp=grp)
    lathe(acc, [(0, 0), (.17 * size, 0)], (x, y, z + .27 * size), "C_5B4030", 16, 0, grp=grp)
    rnd = random.Random(seed)
    for k in range(7):
        a = k * 0.9 + rnd.random()
        tip = (x + math.cos(a) * .22 * size, y + math.sin(a) * .22 * size, z + (.55 + rnd.random() * .25) * size)
        tube(acc, [(x, y, z + .28 * size), (x + math.cos(a) * .08 * size, y + math.sin(a) * .08 * size, z + .45 * size), tip], .008 * size, "C_3F7A2E", 5, 2, grp)
        leaf_clump(acc, tip, (.09 * size, .09 * size, .06 * size), seed * 11 + k, grp=grp)


# ============================================================================================ real leaves
LEAF_GREENS = ("3F8A33", "4E9A3A", "5DAE3E", "6FBF4A", "2F6B2A")


def leaf_bm(length=.09, width=.05, fold=.12, curl=.15, segs=4):
    """A single leaf: broad ovate blade with a rounded tip, gently folded along the midrib and drooping towards
    the tip. Built along +X from the stalk, upper side +Z; two-sided."""
    bm = bmesh.new()
    mid, left, right = [], [], []
    for i in range(segs + 1):
        t = i / segs
        x = t * length
        # widest a bit below the middle, rounded tip (not a spike)
        w = width * .5 * (math.sin(math.pi * min(t, .999)) ** .55) * (1 - .18 * t)
        if i == segs:
            w = 0
        z = -curl * length * t * t
        mid.append(bm.verts.new((x, 0, z)))
        if 0 < i < segs:
            left.append(bm.verts.new((x, w, z + fold * w)))
            right.append(bm.verts.new((x, -w, z + fold * w)))
    faces = [(mid[0], mid[1], left[0]), (mid[0], right[0], mid[1])]
    for i in range(segs - 2):
        faces.append((mid[i + 1], mid[i + 2], left[i + 1], left[i]))
        faces.append((mid[i + 1], right[i], right[i + 1], mid[i + 2]))
    faces.append((mid[segs - 1], mid[segs], left[segs - 2])); faces.append((mid[segs - 1], right[segs - 2], mid[segs]))
    fs = [bm.faces.new(f) for f in faces]
    ret = bmesh.ops.duplicate(bm, geom=fs)
    dup = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=dup)
    for v in [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]:
        v.co.z -= .0015
    uv_box(bm, 4)
    return bm


def add_leaf(acc, pos, direction, up=(0, 0, 1), size=1.0, key="C_4E9A3A", grp="Body", roll=0.0, rnd=None):
    """Places a leaf whose stalk sits at `pos`, pointing along `direction`."""
    d = Vector(direction).normalized()
    u = Vector(up)
    side = d.cross(u)
    if side.length < 1e-4:
        side = d.cross(Vector((1, 0, 0)))
    side.normalize()
    nrm = side.cross(d).normalized()
    if roll:
        R = Matrix.Rotation(roll, 3, d)
        side = R @ side; nrm = R @ nrm
    M = Matrix(((d.x, side.x, nrm.x, pos[0]), (d.y, side.y, nrm.y, pos[1]), (d.z, side.z, nrm.z, pos[2]), (0, 0, 0, 1)))
    bm = leaf_bm(.09 * size, .056 * size, .12, .15 if rnd is None else rnd.uniform(.05, .25))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    acc.add(bm, key, grp)


def leaf_cluster(acc, center, radius, count, seed, size=1.0, grp="Body", greens=LEAF_GREENS, squash=.8):
    """A cluster of individual leaves on a roughly spherical volume, stalks inside, blades facing outwards."""
    rnd = random.Random(seed)
    cx, cy, cz = center
    for i in range(count):
        # Fibonacci sphere + jitter
        k = i + .5
        phi = math.acos(1 - 2 * k / count)
        th = math.pi * (1 + 5 ** .5) * k
        n = Vector((math.cos(th) * math.sin(phi), math.sin(th) * math.sin(phi), math.cos(phi)))
        n = (n + Vector((rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), rnd.uniform(-.2, .3)))).normalized()
        r = radius * rnd.uniform(.72, 1.0)
        base = Vector((cx + n.x * r * .8, cy + n.y * r * .8, cz + n.z * r * .8 * squash))
        d = (n + Vector((0, 0, .35)) + Vector((rnd.uniform(-.4, .4), rnd.uniform(-.4, .4), 0))).normalized()
        add_leaf(acc, base, d, size=size * rnd.uniform(.8, 1.2), key="C_" + greens[rnd.randrange(len(greens))], grp=grp, roll=rnd.uniform(-.6, .6), rnd=rnd)


def leafy_tree(acc, base, height=3.3, spread=1.3, seed=1, grp="Body", trunk_r=.09, density=1.0):
    """A real tree: root flare, trunk, limbs that fork into branches and twigs, and leaves growing along every
    twig (alternate pairs, tilted up, drooping at the tips) - no filler ball inside the crown."""
    rnd = random.Random(seed)
    x, y, z = base
    for k in range(5):
        a = k * 1.2566 + rnd.random() * .4
        tube(acc, [(x, y, z + .2), (x + math.cos(a) * .13, y + math.sin(a) * .13, z + .05), (x + math.cos(a) * .24, y + math.sin(a) * .24, z - .01)],
             lambda s: trunk_r * (1 - .7 * s), "T_IK_R_Bark", 7, 2, grp)
    fork = Vector((x + rnd.uniform(-.06, .06), y + rnd.uniform(-.06, .06), z + height * .4))
    tube(acc, [(x, y, z - .02), ((x + fork.x) / 2, (y + fork.y) / 2, z + height * .2), tuple(fork)], lambda s: trunk_r * (1.15 - .4 * s), "T_IK_R_Bark", 10, 3, grp)
    greens = LEAF_GREENS

    def leaves_on(p0, p1, r_scale):
        d = (p1 - p0)
        L = d.length
        dn = d.normalized()
        side = dn.cross(Vector((0, 0, 1)))
        if side.length < 1e-3:
            side = Vector((1, 0, 0))
        side.normalize()
        n_leaf = max(4, int(L / .032 * density))
        for i in range(n_leaf):
            t = .15 + .85 * i / n_leaf
            p = p0 + d * t
            s = 1 if i % 2 else -1
            ang = rnd.uniform(.7, 1.1)
            dirv = (dn * math.cos(ang) + side * s * math.sin(ang)) + Vector((0, 0, rnd.uniform(.05, .35)))
            add_leaf(acc, tuple(p), dirv, size=rnd.uniform(1.35, 1.75), key="C_" + greens[rnd.randrange(len(greens))], grp=grp, roll=rnd.uniform(-.35, .35), rnd=rnd)
            if i % 3 == 1:   # a second leaf at every few nodes, pointing the other way and higher
                d2 = dn * math.cos(ang) - side * s * math.sin(ang) + Vector((0, 0, rnd.uniform(.3, .6)))
                add_leaf(acc, tuple(p), d2, size=rnd.uniform(1.2, 1.5), key="C_" + greens[rnd.randrange(len(greens))], grp=grp, roll=rnd.uniform(-.35, .35), rnd=rnd)
        # a small rosette at the tip
        for j in range(4):
            b = j * 1.57 + rnd.uniform(-.3, .3)
            dirv = dn * .6 + side * math.cos(b) + dn.cross(side) * math.sin(b) * .6 + Vector((0, 0, .25))
            add_leaf(acc, tuple(p1), dirv, size=rnd.uniform(1.2, 1.5), key="C_" + greens[rnd.randrange(len(greens))], grp=grp, roll=rnd.uniform(-.3, .3), rnd=rnd)

    def grow(p0, direction, length, radius, level):
        dn = direction.normalized()
        bend = Vector((rnd.uniform(-.15, .15), rnd.uniform(-.15, .15), rnd.uniform(-.05, .1)))
        mid = p0 + dn * length * .5 + bend * length * .3
        p1 = p0 + (dn + bend * .4).normalized() * length
        tube(acc, [tuple(p0), tuple(mid), tuple(p1)], lambda s: radius * (1 - .45 * s), "T_IK_R_Bark", max(5, 9 - 2 * level), 2, grp)
        if level >= 3:
            leaves_on(p0 + (p1 - p0) * .25, p1, 1)
            return
        n_kids = 3 if level < 2 else rnd.choice((2, 3))
        for k in range(n_kids):
            a = k * 2 * math.pi / n_kids + rnd.uniform(-.5, .5)
            side = dn.cross(Vector((0, 0, 1)))
            if side.length < 1e-3:
                side = Vector((1, 0, 0))
            side.normalize()
            up = side.cross(dn).normalized()
            spread_ang = .55 if level == 0 else .75
            child = (dn * math.cos(spread_ang) + (side * math.cos(a) + up * math.sin(a)) * math.sin(spread_ang))
            child.z = max(child.z, .05 if level < 2 else -.25)
            grow(p1, child, length * rnd.uniform(.62, .75), radius * .62, level + 1)
        # small side twig with leaves halfway along the branch (fills the crown from inside)
        for q_t in ((.55,) if level < 2 else (.4, .75)):
            q = p0 + (p1 - p0) * q_t
            if level < 1:
                continue
            tw = q + (Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, .6))).normalized()) * length * .38
            tube(acc, [tuple(q), tuple(tw)], radius * .35, "T_IK_R_Bark", 5, 0, grp)
            leaves_on(q, tw, 1)

    n = rnd.choice((4, 5))
    for k in range(n):
        a = k * 2 * math.pi / n + rnd.uniform(-.3, .3)
        d = Vector((math.cos(a) * .75, math.sin(a) * .75, 1.0))
        grow(fork, d, height * .3, trunk_r * .72, 0)
    grow(fork, Vector((rnd.uniform(-.1, .1), rnd.uniform(-.1, .1), 1)), height * .28, trunk_r * .6, 1)


def leafy_hedge(acc, p0, p1, width=.5, height=.55, seed=0, grp="Body"):
    """Clipped hedge in a timber planter: a dark core covered with individual leaves on every face."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    ang = math.atan2(d.y, d.x)
    c = (p0 + p1) / 2
    rbox(acc, (L, width, .38), (c.x, c.y, .19), "T_IK_R_PlanksDark", .03, 3, rot=(0, 0, math.degrees(ang)), grp=grp, uv=1.2)
    rbox(acc, (L + .04, width + .04, .04), (c.x, c.y, .39), "C_" + NAVY, .015, 2, rot=(0, 0, math.degrees(ang)), grp=grp)
    rbox(acc, (L - .1, width - .12, height - .06), (c.x, c.y, .38 + (height - .06) / 2), "T_IK_R_Hedge", .1, 3, rot=(0, 0, math.degrees(ang)), grp=grp, uv=1.5)
    rnd = random.Random(seed)
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    z0 = .38
    def world(a, b, h):
        return (c.x + ux * a + vx * b, c.y + uy * a + vy * b, z0 + h)
    step = .1
    # top
    na, nb = int((L - .08) / step), int((width - .06) / step)
    for i in range(na):
        for j in range(nb + 1):
            a = -L / 2 + .06 + i * step + rnd.uniform(-.02, .02)
            b = -width / 2 + .04 + j * step * .9 + rnd.uniform(-.02, .02)
            dirv = (ux * rnd.uniform(-1, 1) + vx * rnd.uniform(-1, 1), uy * rnd.uniform(-1, 1) + vy * rnd.uniform(-1, 1), 1.4)
            add_leaf(acc, world(a, b, height - .05), dirv, size=1.3, key="C_" + LEAF_GREENS[rnd.randrange(5)], grp=grp, roll=rnd.uniform(-1, 1), rnd=rnd)
    # long sides
    nh = int(height / step)
    for s in (-1, 1):
        for i in range(na):
            for k in range(nh):
                a = -L / 2 + .06 + i * step + rnd.uniform(-.02, .02)
                h = .03 + k * step + rnd.uniform(-.02, .02)
                dirv = (vx * s * 1.2 + ux * rnd.uniform(-.6, .6), vy * s * 1.2 + uy * rnd.uniform(-.6, .6), rnd.uniform(-.2, .7))
                add_leaf(acc, world(a, s * (width / 2 - .07), h), dirv, size=1.3, key="C_" + LEAF_GREENS[rnd.randrange(5)], grp=grp, roll=rnd.uniform(-1, 1), rnd=rnd)
    # ends
    for s in (-1, 1):
        for j in range(nb + 1):
            for k in range(nh):
                b = -width / 2 + .04 + j * step * .9
                h = .03 + k * step
                dirv = (ux * s * 1.2 + vx * rnd.uniform(-.6, .6), uy * s * 1.2 + vy * rnd.uniform(-.6, .6), rnd.uniform(-.2, .7))
                add_leaf(acc, world(s * (L / 2 - .07), b, h), dirv, size=1.3, key="C_" + LEAF_GREENS[rnd.randrange(5)], grp=grp, roll=rnd.uniform(-1, 1), rnd=rnd)
    for k in range(int(L * 3)):
        a = rnd.uniform(-L / 2 + .1, L / 2 - .1)
        flower(acc, world(a, rnd.uniform(-width / 2 + .08, width / 2 - .08), height + .02), rnd.choice(("F4A6C1", "FFFFFF", "F2C23F")), .035, grp)


def leafy_vine(acc, pts, seed=0, grp="Body", every=.09, size=1.0):
    """A climbing stem (smooth tube) with pairs of leaves along it."""
    tube(acc, pts, .012, "C_4E7A2E", 5, 2, grp)
    rnd = random.Random(seed)
    P = [Vector(p) for p in spline(pts, 4)]
    acc_len = 0
    for i in range(1, len(P)):
        seg = P[i] - P[i - 1]
        acc_len += seg.length
        if acc_len < every:
            continue
        acc_len = 0
        t = seg.normalized()
        side = t.cross(Vector((0, 0, 1)))
        if side.length < 1e-3:
            side = Vector((1, 0, 0))
        side.normalize()
        for s in (-1, 1):
            dirv = (side * s + t * .3 + Vector((0, 0, .2))).normalized()
            add_leaf(acc, tuple(P[i]), dirv, size=size * rnd.uniform(.8, 1.2), key="C_" + LEAF_GREENS[rnd.randrange(5)], grp=grp, roll=rnd.uniform(-.5, .5), rnd=rnd)


def leafy_plant(acc, c, size=1.0, seed=0, grp="Body", pot="T_IK_Terracotta"):
    """Potted plant: stems fanning out, each ending in a small crown of leaves."""
    x, y, z = c
    lathe(acc, [(0, 0), (.14 * size, 0), (.17 * size, .28 * size), (.19 * size, .3 * size), (.18 * size, .31 * size)], c, pot, 20, 1, cap_top=False, grp=grp)
    lathe(acc, [(0, 0), (.17 * size, 0)], (x, y, z + .27 * size), "C_5B4030", 16, 0, grp=grp)
    rnd = random.Random(seed)
    for k in range(9):
        a = k * 0.7 + rnd.random()
        r = rnd.uniform(.08, .22) * size
        tip = (x + math.cos(a) * r, y + math.sin(a) * r, z + (.45 + rnd.random() * .3) * size)
        tube(acc, [(x, y, z + .28 * size), (x + math.cos(a) * r * .4, y + math.sin(a) * r * .4, z + .4 * size), tip], .006 * size, "C_3F7A2E", 5, 2, grp)
        for j in range(4):
            b = a + j * 1.57 + rnd.uniform(-.3, .3)
            add_leaf(acc, tip, (math.cos(b), math.sin(b), .5), size=size * 1.3, key="C_" + LEAF_GREENS[rnd.randrange(5)], grp=grp, roll=rnd.uniform(-.4, .4), rnd=rnd)
