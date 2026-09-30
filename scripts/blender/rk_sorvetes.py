"""Sorveteria: gelato dipping cabinet with curved glass, soft-serve machine, milkshake mixer, toppings bar, cone and
cup dispensers, menu board; low side walls so the counter stays visible from the game camera."""
import math, random, bmesh
from mathutils import Vector
from rk_core import *

BACK, HW = 1.5, 1.6
WALL_H, SIDE_H = 2.55, 1.05
FLAVOURS = [("gelato_%d" % i) for i in range(8)]
GARNISH = ["F4A6C1", "8FB85A", "F7EFD8", "5A3521", "F7B733", "A8E6CF", "3E2215", "9C7BD8"]


def sweep_x(acc, prof_yz, x0, x1, key, nx=1, grp="Body", closed=False):
    """Extrudes a (y, z) polyline along X (bent sheets: curved glass, rounded counter fronts)."""
    bm = bmesh.new()
    rows = []
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx
        rows.append([bm.verts.new((x, y, z)) for y, z in prof_yz])
    n = len(prof_yz)
    for i in range(nx):
        for j in range(n - 1 + (1 if closed else 0)):
            j2 = (j + 1) % n
            bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j2], rows[i][j2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv_box(bm)
    acc.add(bm, key, grp)


def slab_x(acc, prof_yz, x0, x1, key, grp="Body"):
    """Closed (y, z) outline extruded along X with end caps (a counter body with a curved front)."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in prof_yz]
    b = [bm.verts.new((x1, y, z)) for y, z in prof_yz]
    n = len(prof_yz)
    bm.faces.new(a); bm.faces.new(list(reversed(b)))
    for j in range(n):
        bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.calc_face_angle(0) > .7], offset=.012, segments=2, affect="EDGES", clamp_overlap=True)
    uv_box(bm)
    acc.add(bm, key, grp)


def mound(acc, cx, cy, z, w, d, h, flavour, seed, grp):
    """Heaped gelato in a pan: soft mound with scooped ridges and a swirl, textured with the flavour."""
    rnd = random.Random(seed)
    nu, nv = 14, 10
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    ph = [rnd.random() * 6.28 for _ in range(4)]
    V = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            u, v = i / nu, j / nv
            edge = (1 - abs(2 * u - 1) ** 3) * (1 - abs(2 * v - 1) ** 3)
            wave = .18 * math.sin(u * 9 + v * 4 + ph[0]) * math.sin(v * 7 + ph[1]) + .12 * math.sin(u * 17 + ph[2])
            hz = h * max(0, edge) ** .55 * (1 + wave * edge)
            V[(i, j)] = bm.verts.new((cx + (u - .5) * w, cy + (v - .5) * d, z + hz))
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((V[(i, j)], V[(i + 1, j)], V[(i + 1, j + 1)], V[(i, j + 1)]))
            for l in f.loops:
                co = l.vert.co
                l[uvl].uv = cell_uv(flavour, (co.x - cx) / w + .5, (co.y - cy) / d + .5)
    acc.add(bm, LAB, grp)
    # A scooped curl on top.
    t = [(cx - w * .12 + math.cos(a) * w * .1 * (1 - a / 9), cy + math.sin(a) * d * .15 * (1 - a / 9), z + h * .9 + a * .004) for a in [k * .5 for k in range(16)]]
    bm = tube_bm(t, lambda s: .02 * (1 - .6 * s) + .004, 8, 0)
    uvl2 = bm.loops.layers.uv.get("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uvl2].uv = cell_uv(flavour, .3 + .4 * rnd.random(), .3 + .4 * rnd.random())
    acc.add(bm, LAB, grp)


def pan(acc, cx, cy, z, w, d, flavour, seed, grp, garnish):
    rbox(acc, (w, d, .09), (cx, cy, z - .045), "C_" + CHROME, .008, 2, grp=grp)
    rbox(acc, (w + .012, d + .012, .012), (cx, cy, z), "C_" + CHROME, .005, 1, grp=grp)
    mound(acc, cx, cy, z - .005, w - .03, d - .03, .085, flavour, seed, grp)
    rnd = random.Random(seed + 9)
    for k in range(4):   # garnish: fruit pieces / cookie chunks on top
        gx, gy = cx + (rnd.random() - .5) * w * .5, cy + (rnd.random() - .5) * d * .4
        blob(acc, (.018, .014, .01), (gx, gy, z + .075), "C_" + garnish, 2, .15, seed + k, grp=grp)
    # Spatula resting in the pan.
    rbox(acc, (.05, .008, .07), (cx + w * .28, cy + d * .15, z + .06), "C_" + STEEL, .004, 1, rot=(-25, 0, 0), grp=grp)
    tube(acc, [(cx + w * .28, cy + d * .18, z + .09), (cx + w * .28, cy + d * .38, z + .2)], .007, "C_" + DARK, 6, grp=grp)


def gelato_case(acc):
    x0, x1 = -1.36, 1.36
    yf, yb = -.88, -.06          # front (customer) / back (server) edges of the cabinet
    # Body with a rounded front, cream with a pink band, a steel kick and toe.
    body = [(yf + .06, .08), (yb, .08), (yb, .86), (yf + .1, .86), (yf + .02, .8), (yf, .6), (yf + .02, .2)]
    slab_x(acc, body, x0, x1, "C_" + WHITE)
    sweep_x(acc, [(yf - .005, .5), (yf - .003, .6), (yf + .015, .74)], x0 + .02, x1 - .02, "C_E86A9E", 1)
    rbox(acc, (x1 - x0 - .04, .6, .08), (0, (yf + yb) / 2 + .04, .04), "C_" + NAVY, .02, 2)
    for x in (x0 + .01, x1 - .01):   # rounded end cheeks
        pts = [(yf, .08), (yb, .08), (yb, 1.38), (yb - .12, 1.38), (yf + .05, .98), (yf, .86)]
        bm = bmesh.new()
        a = [bm.verts.new((x - .018, y, z)) for y, z in pts]
        b = [bm.verts.new((x + .018, y, z)) for y, z in pts]
        bm.faces.new(a); bm.faces.new(list(reversed(b)))
        for j in range(len(pts)):
            bm.faces.new((a[j], a[(j + 1) % len(pts)], b[(j + 1) % len(pts)], b[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=.012, segments=2, affect="EDGES", clamp_overlap=True)
        uv_box(bm); acc.add(bm, "C_E86A9E")
    # Display well and the steel rim.
    rbox(acc, (x1 - x0 - .06, (yb - yf) - .12, .02), (0, (yf + yb) / 2 + .02, .86), "C_" + STEEL, .005, 1)
    rbox(acc, (x1 - x0, .06, .03), (0, yb - .03, .88), "C_" + CHROME, .01, 2)
    sweep_x(acc, [(yf + .08, .87), (yf + .1, .885)], x0 + .02, x1 - .02, "C_" + GOLD, 1)
    # Curved front glass (bent sheet) and a flat serving shelf at the top.
    arc = [(yf + .04 + .42 * (1 - math.cos(a)), .88 + .5 * math.sin(a)) for a in [k * math.pi / 2 / 8 for k in range(9)]]
    sweep_x(acc, arc, x0 + .03, x1 - .03, "G_Glass", 1)
    rbox(acc, (x1 - x0 - .06, .26, .014), (0, yb - .16, 1.385), "G_Glass", .004, 1)
    rbox(acc, (x1 - x0 - .06, .03, .02), (0, yb - .02, 1.38), "C_" + CHROME, .008, 2)
    rbox(acc, (x1 - x0 - .12, .02, .02), (0, yb - .12, 1.36), "E_FFF4DC", .006, 1)
    # Pans: two rows of six flavours; each quarter of the case empties on its own.
    w, d = .4, .27
    for i in range(12):
        col, row = i % 6, i // 6
        cx = x0 + .24 + col * .448
        cy = yf + .3 + row * .3
        pan(acc, cx, cy, .96 + row * .03, w, d, FLAVOURS[i % 8], i * 7, "Anim Fill %d" % min(3, col * 4 // 6), GARNISH[i % 8])
        # flavour tag
        rbox(acc, (.09, .004, .05), (cx, cy - d / 2 - .01, 1.02 + row * .03), "C_" + WHITE, .005, 1, rot=(-20, 0, 0))
        rbox(acc, (.07, .003, .012), (cx, cy - d / 2 - .014, 1.025 + row * .03), "C_" + GARNISH[i % 8], .004, 1, rot=(-20, 0, 0))


def soft_serve(acc, x, y, z):
    """Twin-flavour soft-serve machine: rounded cabinet, hopper lids, freezing door with three star spouts and
    draw handles, drip tray, control panel and side vents."""
    rbox(acc, (.56, .52, .66), (x, y, z + .33), "C_" + STEEL, .06, 4)
    rbox(acc, (.58, .54, .16), (x, y + .01, z + .73), "C_" + WHITE, .06, 4)
    for s in (-1, 1):
        lathe(acc, [(0, 0), (.1, 0), (.105, .02), (.08, .035), (0, .04)], (x + s * .13, y + .03, z + .81), "C_" + ("F4A6C1" if s < 0 else "6B3E26"), 16, 2)
        for k in range(4):
            rbox(acc, (.006, .3, .025), (x + s * .285, y + .02, z + .2 + k * .06), "C_" + DARK, .003, 1)
    # Freezing door: rounded plate with three spouts and three draw handles.
    fr = rbox_bm((.46, .06, .22), .05, 4); uv_box(fr)
    place(fr, (x, y - .28, z + .52)); acc.add(fr, "C_" + CHROME)
    for k, sx in enumerate((-.14, 0, .14)):
        lathe(acc, [(.03, 0), (.028, .05), (.018, .07), (.02, .085)], (sx + x, y - .31, z + .38), "C_" + CHROME, 12, 0, rot=(180, 0, 0))
        for t in range(6):
            a = t * math.pi / 3
            rbox(acc, (.006, .006, .02), (x + sx + math.cos(a) * .014, y - .31 + math.sin(a) * .014, z + .3), "C_" + STEEL, .002, 1)
        tube(acc, [(x + sx, y - .3, z + .6), (x + sx, y - .38, z + .66), (x + sx, y - .44, z + .78)], .012, "C_" + CHROME, 8, 2)
        lathe(acc, [(0, 0), (.028, .01), (.03, .04), (.02, .06), (0, .065)], (x + sx, y - .44, z + .78), "C_" + ("D74A3C" if k != 1 else "3E8FD6"), 12, 2, rot=(-30, 0, 0))
    # Drip tray with a slotted grid.
    rbox(acc, (.46, .16, .05), (x, y - .33, z + .12), "C_" + STEEL, .02, 3)
    for k in range(8):
        rbox(acc, (.012, .13, .006), (x - .19 + k * .055, y - .33, z + .148), "C_" + DARK, .003, 1)
    # Control panel.
    rbox(acc, (.26, .02, .07), (x, y - .265, z + .66), "C_" + DARK, .01, 2)
    rbox(acc, (.09, .005, .04), (x - .06, y - .277, z + .66), "E_7ED957", .004, 1)
    for k in range(3):
        lathe(acc, [(0, 0), (.012, 0), (.012, .01), (0, .012)], (x + .04 + k * .035, y - .277, z + .66), "C_" + ("D74A3C" if k == 0 else WHITE), 8, 0, rot=(90, 0, 0))


def milkshake_mixer(acc, x, y, z):
    rbox(acc, (.18, .2, .04), (x, y, z + .02), "C_" + CHROME, .015, 3)
    tube(acc, [(x, y + .07, z + .02), (x, y + .07, z + .42)], .028, "C_E86A9E", 12)
    rbox(acc, (.12, .22, .1), (x, y - .01, z + .47), "C_E86A9E", .04, 3)
    tube(acc, [(x, y - .05, z + .42), (x, y - .05, z + .22)], .006, "C_" + STEEL, 6)
    lathe(acc, [(0, 0), (.035, 0), (.045, .16), (.047, .17)], (x, y - .05, z + .06), "C_" + CHROME, 14, 0, cap_top=False)
    lathe(acc, [(0, 0), (.04, 0), (.04, .1)], (x, y - .05, z + .07), "C_F4A6C1", 14, 0)


def cone(acc, x, y, z, scoops=(), tilt=0, grp="Body"):
    lathe(acc, [(.002, 0), (.028, .1), (.036, .13), (.04, .14), (.035, .145)], (x, y, z), "T_IK_Waffle", 12, 1, rot=(tilt, 0, 0), grp=grp, cap_top=False)
    for i, c in enumerate(scoops):
        scoop(acc, x, y, z + .14 + i * .062, .043, c, i, grp)


def scoop(acc, x, y, z, r, col, seed=0, grp="Body"):
    """Scooped ball: a sphere with a wavy, flared skirt at its base."""
    prof = []
    for k in range(13):
        a = -math.pi / 2 + math.pi * k / 12
        prof.append((max(0.0, r * math.cos(a)), r * (1 + math.sin(a)) * .95))
    prof[0] = (0, 0)
    bm = lathe_bm(prof, 20, 0)
    for v in bm.verts:
        if v.co.z < r * .45:
            ang = math.atan2(v.co.y, v.co.x)
            f = 1 + .12 * (1 - v.co.z / (r * .45)) * (1 + math.sin(ang * 7 + seed))
            v.co.x *= f; v.co.y *= f
    uv_box(bm, 3)
    place(bm, (x, y, z)); acc.add(bm, "C_" + col, grp)


def cone_holder(acc, x, y, z):
    rbox(acc, (.3, .12, .02), (x, y, z + .01), "C_" + CHROME, .008, 2)
    for k in range(3):
        cx = x - .1 + k * .1
        lathe(acc, [(.04, 0), (.042, .3), (.045, .31)], (cx, y, z + .02), "G_Glass", 14, 0, cap_top=False, cap_bottom=False)
        for s in range(7):
            cone(acc, cx, y, z + .03 + s * .038)
    rbox(acc, (.3, .006, .05), (x, y - .065, z + .08), "C_E86A9E", .006, 1)


def toppings(acc, x, y, z):
    cols = [("F4A6C1", "8FD3C0", "F2C23F"), ("5A3521",), ("D74A3C",), ("F7EFD8", "E86A9E"), ("3E2215",), ("8FB85A",)]
    rbox(acc, (.62, .2, .04), (x, y, z + .02), "C_" + CHROME, .01, 2)
    for k, cc in enumerate(cols):
        jx = x - .25 + k * .1
        lathe(acc, [(0, 0), (.038, 0), (.04, .1), (.036, .11), (.036, .12)], (jx, y, z + .04), "G_Glass", 12, 1, cap_top=False)
        rnd = random.Random(k)
        for t in range(10):
            blob(acc, (.008, .008, .006), (jx + (rnd.random() - .5) * .05, y + (rnd.random() - .5) * .05, z + .06 + rnd.random() * .05), "C_" + cc[t % len(cc)], 1, 0, t)
        lathe(acc, [(0, 0), (.041, 0), (.041, .012), (.03, .02), (0, .022)], (jx, y, z + .16), "C_" + CHROME, 12, 1)


def cup_dispenser(acc, x, y, z):
    for k, (r, col) in enumerate(((.045, "F4A6C1"), (.055, "8FD3C0"))):
        cx = x + k * .13
        lathe(acc, [(r + .005, 0), (r + .005, .36)], (cx, y, z), "G_Glass", 14, 0, cap_top=False, cap_bottom=False)
        for s in range(9):
            lathe(acc, [(r * .7, 0), (r, .06), (r * 1.02, .065)], (cx, y, z + .02 + s * .035), "C_" + col, 14, 0, cap_top=False)
    rbox(acc, (.3, .12, .02), (x + .065, y, z + .005), "C_" + CHROME, .008, 2)


def build(name="sector-sorvetes"):
    acc = Acc(name)
    # Back wall (pink tile, mint wainscot, cream trims) and LOW side walls.
    rbox(acc, (2 * HW, .1, WALL_H), (0, BACK, WALL_H / 2), "T_IK_TilePink", .015, 2, uv=2.2)
    rbox(acc, (2 * HW - .02, .03, .9), (0, BACK - .065, .45), "T_IK_TileMint", .01, 1, uv=2.2)
    rbox(acc, (2 * HW, .06, .05), (0, BACK - .08, .92), "C_" + GOLD, .02, 3)
    rbox(acc, (2 * HW, .06, .1), (0, BACK - .08, .05), "C_" + NAVY, .02, 2)
    for s in (-1, 1):
        prof = [(BACK, 0), (BACK, SIDE_H), (.75, SIDE_H), (.55, SIDE_H - .15), (.45, .5), (.4, 0)]
        bm = bmesh.new()
        a = [bm.verts.new((s * HW - .05, y, z)) for y, z in prof]
        b = [bm.verts.new((s * HW + .05, y, z)) for y, z in prof]
        bm.faces.new(a); bm.faces.new(list(reversed(b)))
        for j in range(len(prof)):
            bm.faces.new((a[j], a[(j + 1) % len(prof)], b[(j + 1) % len(prof)], b[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=.02, segments=3, affect="EDGES", clamp_overlap=True)
        uv_box(bm, 2.2); acc.add(bm, "T_IK_TilePink")
        rbox(acc, (.12, 1.1, .05), (s * HW, 1.0, SIDE_H + .02), "C_" + GOLD, .02, 3)
    # Sign board with a scalloped awning over the counter.
    rbox(acc, (2.3, .08, .5), (0, BACK - .1, 2.25), "C_" + NAVY, .05, 4)
    rbox(acc, (2.36, .09, .05), (0, BACK - .1, 2.0), "C_" + GOLD, .02, 3)
    text(acc, "SORVETES", .26, (0, BACK - .16, 2.25), "C_" + GOLDL, .04, bevel=.006)
    for k in range(12):
        x = -1.5 + k * .273
        col = "C_" + ("E86A9E" if k % 2 else WHITE)
        sweep_x(acc, [(BACK - .12, 2.02), (BACK - .3, 1.97), (BACK - .45, 1.9)], x - .1365, x + .1365, col, 1)
        # scalloped valance: a hanging half-disc per stripe
        bm, _ = panel_bm(.27, .02, .012, .001, 1)
        bm.free()
        pts = [(x + math.cos(a) * .1365, 1.9 - math.sin(a) * .07) for a in [math.pi * i / 10 for i in range(11)]]
        vb = bmesh.new()
        f_ = [vb.verts.new((px, BACK - .455, pz)) for px, pz in pts]
        b_ = [vb.verts.new((px, BACK - .44, pz)) for px, pz in pts]
        vb.faces.new(f_); vb.faces.new(list(reversed(b_)))
        for j in range(len(pts)):
            vb.faces.new((f_[j], f_[(j + 1) % len(pts)], b_[(j + 1) % len(pts)], b_[j]))
        bmesh.ops.recalc_face_normals(vb, faces=vb.faces)
        uv_box(vb); acc.add(vb, col)
    tube(acc, [(-1.62, BACK - .45, 1.905), (1.62, BACK - .45, 1.905)], .012, "C_" + GOLD, 8)
    # Menu board.
    label_panel(acc, .9, .45, (-.95, BACK - .07, 1.5), "menu", .02, .04)
    # Back counter with marble top and its equipment.
    rbox(acc, (2 * HW - .3, .45, .9), (0, BACK - .3, .45), "C_F6D6E1", .03, 3)
    rbox(acc, (2 * HW - .26, .5, .04), (0, BACK - .3, .92), "T_IK_Marble", .015, 2)
    for k in range(6):
        rbox(acc, (.4, .01, .6), (-1.08 + k * .43, BACK - .53, .45), "C_" + WHITE, .02, 2)
        lathe(acc, [(0, 0), (.012, 0), (.012, .02), (0, .02)], (-1.08 + k * .43, BACK - .54, .7), "C_" + GOLD, 8, 0, rot=(90, 0, 0))
    soft_serve(acc, .95, BACK - .28, .94)
    milkshake_mixer(acc, .45, BACK - .25, .94)
    toppings(acc, -.1, BACK - .3, .94)
    cone_holder(acc, -.72, BACK - .28, .94)
    cup_dispenser(acc, -1.25, BACK - .28, .94)
    # The dipping cabinet in front.
    gelato_case(acc)
    # Finished cones on a stand on the glass shelf.
    rbox(acc, (.62, .1, .07), (0, -.2, 1.43), "T_IK_WoodLight", .02, 3)
    for k, sc in enumerate((("F4A6C1", "F7EFD8"), ("6B3E26",), ("B5D98A", "F7B733"))):
        cone(acc, -.2 + k * .2, -.2, 1.37, sc)
    return acc
