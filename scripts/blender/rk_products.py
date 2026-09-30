"""Realistic Kit — products (bottles, cans, cartons, packs) with printed labels from IK_Labels. Blender space."""
import math, bmesh
from mathutils import Vector
from rk_core import *


def pet_bottle(acc, loc, h=.30, r=.036, liquid="C_4A1C10", label="soda_0", cap="C_D74A3C", grp="Body", seg=10):
    """Soda PET: petaloid foot, straight body with label, grip waist, domed shoulder, neck ring and ridged cap."""
    x, y, z = loc
    prof = [(0, 0), (r * .55, 0), (r * .8, h * .01), (r * .95, h * .04), (r, h * .09), (r, h * .2), (r * .93, h * .27),
            (r, h * .34), (r, h * .56), (r * .96, h * .62), (r * .78, h * .74), (r * .5, h * .84), (r * .36, h * .88), (r * .34, h * .92)]
    lathe(acc, prof, loc, liquid, seg, 1, grp=grp, cap_top=False)
    lathe(acc, [(r * 1.015, h * .36), (r * 1.015, h * .55)], loc, LAB, seg, 0, grp=grp, uv_cell=label, u_rep=2, v_range=(h * .36, h * .55), cap_top=False, cap_bottom=False)
    lathe(acc, [(r * .42, h * .905), (r * .42, h * .92)], loc, "C_" + WHITE, seg, 0, grp=grp)
    lathe(acc, [(r * .4, h * .92), (r * .41, h * .99), (r * .36, h * 1.0), (0, h * 1.0)], loc, cap, 10, 0, grp=grp)


def water_bottle(acc, loc, h=.29, r=.034, label="water_0", grp="Body", seg=10):
    prof = [(0, 0), (r * .8, 0), (r, h * .05)]
    for k in range(5):
        z0 = h * (.1 + k * .09)
        prof += [(r, z0), (r * .93, z0 + h * .03)]
    prof += [(r, h * .58), (r * .9, h * .7), (r * .55, h * .82), (r * .34, h * .88)]
    lathe(acc, prof, loc, "C_BFE3F0", seg, 0, grp=grp, cap_top=False)
    lathe(acc, [(r * 1.02, h * .6), (r * 1.02, h * .72)], loc, LAB, seg, 0, grp=grp, uv_cell=label, u_rep=2, v_range=(h * .6, h * .72), cap_top=False, cap_bottom=False)
    lathe(acc, [(r * .38, h * .88), (r * .39, h * .96), (r * .34, h * .97), (0, h * .97)], loc, "C_3E8FD6", 10, 0, grp=grp)


def can(acc, loc, r=.033, h=.122, label="can_0", grp="Body", seg=10):
    prof = [(0, .004), (r * .7, 0), (r * .92, .004), (r, h * .08), (r, h * .86), (r * .86, h * .97), (r * .87, h)]
    lathe(acc, prof[:4], loc, "C_" + CHROME, seg, 0, grp=grp, cap_top=False)
    lathe(acc, [(r, h * .08), (r, h * .86)], loc, LAB, seg, 0, grp=grp, uv_cell=label, u_rep=2, v_range=(h * .08, h * .86), cap_top=False, cap_bottom=False)
    lathe(acc, [(r, h * .86), (r * .86, h * .97), (r * .87, h), (r * .8, h * .985), (0, h * .985)], loc, "C_" + CHROME, seg, 0, grp=grp)


def longneck(acc, loc, h=.26, r=.03, glass="C_5A3312", label="beer_0", grp="Body", seg=10):
    prof = [(0, 0), (r * .9, 0), (r, h * .03), (r, h * .55), (r * .9, h * .64), (r * .5, h * .74), (r * .4, h * .8), (r * .38, h * .93), (r * .45, h * .95), (r * .44, h * .98)]
    lathe(acc, prof, loc, glass, seg, 1, grp=grp, cap_top=False)
    lathe(acc, [(r * 1.015, h * .15), (r * 1.015, h * .45)], loc, LAB, seg, 0, grp=grp, uv_cell=label, u_rep=2, v_range=(h * .15, h * .45), cap_top=False, cap_bottom=False)
    lathe(acc, [(r * .47, h * .96), (r * .47, h * 1.0), (0, h * 1.0)], loc, "C_" + GOLD, 10, 0, grp=grp)


def wine_bottle(acc, loc, h=.31, r=.037, glass="C_2A3B22", label="wine_0", foil="C_7A1E2E", grp="Body", seg=10, rot=(0, 0, 0)):
    """Bordeaux bottle: punt, straight body, rounded shoulders, long neck, foil capsule."""
    prof = [(0, h * .03), (r * .5, h * .01), (r * .95, 0), (r, h * .03), (r, h * .62), (r * .88, h * .7), (r * .5, h * .76), (r * .33, h * .8), (r * .31, h * .98), (r * .34, h * 1.0)]
    bm = lathe_bm(prof, seg, 1, cap_top=False)
    place(bm, loc, rot); acc.add(bm, glass, grp)
    bm = lathe_bm([(r * 1.012, h * .18), (r * 1.012, h * .5)], seg, 0, uv_cell=label, u_rep=2, v_range=(h * .18, h * .5), cap_top=False, cap_bottom=False)
    place(bm, loc, rot); acc.add(bm, LAB, grp)
    bm = lathe_bm([(r * .335, h * .84), (r * .345, h * 1.0), (r * .3, h * 1.005), (0, h * 1.005)], 10, 0)
    place(bm, loc, rot); acc.add(bm, foil, grp)


def carton(acc, loc, w=.07, d=.07, h=.2, label="juice_0", grp="Body"):
    """Gable-top carton: box with the label on its sides and a folded roof with a seal fin."""
    bm = rbox_bm((w, d, h * .82), .004, 1)
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        for l in f.loops:
            co = l.vert.co
            if abs(n.z) > .5:
                l[uvl].uv = cell_uv(label, .5, .95)
            elif abs(n.y) > .5:
                l[uvl].uv = cell_uv(label, (co.x + w / 2) / w, (co.z + h * .41) / (h * .82))
            else:
                l[uvl].uv = cell_uv(label, (co.y + d / 2) / d, (co.z + h * .41) / (h * .82))
    place(bm, (loc[0], loc[1], loc[2] + h * .41)); acc.add(bm, LAB, grp, smooth=False)
    bm = bmesh.new()
    zt, zr = h * .82, h * .97
    vs = [bm.verts.new(p) for p in ((-w / 2, -d / 2, zt), (w / 2, -d / 2, zt), (w / 2, 0, zr), (-w / 2, 0, zr), (-w / 2, d / 2, zt), (w / 2, d / 2, zt))]
    bm.faces.new((vs[0], vs[1], vs[2], vs[3])); bm.faces.new((vs[3], vs[2], vs[5], vs[4]))
    bm.faces.new((vs[0], vs[3], vs[4])); bm.faces.new((vs[1], vs[5], vs[2]))
    uv_box(bm)
    place(bm, loc); acc.add(bm, "C_" + WHITE, grp, smooth=False)
    rbox(acc, (w, .006, h * .06), (loc[0], loc[1], loc[2] + zr + h * .02), "C_" + WHITE, .002, 1, grp=grp)
    lathe(acc, [(.009, 0), (.01, .012), (0, .013)], (loc[0] + w * .22, loc[1] - d * .22, loc[2] + zt + h * .05), "C_" + ORANGE, 8, 0, rot=(-20, 0, 0), grp=grp)


def box_pack(acc, loc, w, d, h, label, grp="Body", r=.004, yaw=0):
    """Cardboard/plastic package with its artwork on the front (-Y) and back, colour-matched sides."""
    bm = rbox_bm((w, d, h), r, 1)
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        for l in f.loops:
            co = l.vert.co
            if abs(n.y) > .5:
                l[uvl].uv = cell_uv(label, (co.x + w / 2) / w, (co.z + h / 2) / h)
            elif abs(n.x) > .5:
                l[uvl].uv = cell_uv(label, .1 + .1 * (co.y + d / 2) / d, (co.z + h / 2) / h)
            else:
                l[uvl].uv = cell_uv(label, .5, .92)
    place(bm, (loc[0], loc[1], loc[2] + h / 2), (0, 0, yaw)); acc.add(bm, LAB, grp, smooth=False)


def chip_bag(acc, loc, w=.16, h=.22, d=.06, label="pack_6", grp="Body"):
    """Pillow bag: puffed in the middle, crimped flat seams top and bottom."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    nu, nv = 8, 8
    grid = {}
    for side, s in ((0, -1), (1, 1)):
        for i in range(nu + 1):
            for j in range(nv + 1):
                u, v = i / nu, j / nv
                puff = math.sin(math.pi * v) ** .7 * (1 - (2 * u - 1) ** 4) ** .5
                grid[(side, i, j)] = bm.verts.new(((u - .5) * w * (1 - .06 * math.sin(math.pi * v)), s * d / 2 * puff + s * .002, v * h))
    faces = []
    for side in (0, 1):
        for i in range(nu):
            for j in range(nv):
                q = [grid[(side, i, j)], grid[(side, i + 1, j)], grid[(side, i + 1, j + 1)], grid[(side, i, j + 1)]]
                if side == 1:
                    q.reverse()
                f = bm.faces.new(q)
                for l in f.loops:
                    co = l.vert.co
                    l[uvl].uv = cell_uv(label, co.x / w + .5, co.z / h)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.0005)
    place(bm, loc); acc.add(bm, LAB, grp)
