"""Distrito industrial (Lucas 08/11): the brand factory that grows from a mini factory to a big industry, and the meat
packing plant (frigorífico). Preview round 1 — studio stills for approval, nothing exported to Unity yet.

Run inside Blender after the kit (same namespace as rede_dc.py):
    REPO = "/Users/lucas-furini/repos/checkout"
    ns = {"__name__": "kit", "REPO": REPO}
    exec(open(REPO + "/scripts/blender/fixture_tiers.py").read(), ns)
    exec(open(REPO + "/scripts/blender/rede_assets.py").read(), ns)
    exec(open(REPO + "/scripts/blender/rede_dc.py").read(), ns)
    exec(open(REPO + "/scripts/blender/industry_v1.py").read(), ns)
    ns["shoot_factory"](); ns["shoot_frigo"]()

Space: metres, Z up, the FRONT faces -Y (the street / the camera). Each tier is a complete lot that contains the tier
before it (the factory grows on the same lot): factory lot 36 x 40 m, frigorífico lot 30 x 30 m.
Material contract as rede_assets.py: navy C_1D2B4F / C_2E4A7D and gold C_D3A53D follow "Cores do mercado"; white
plates with Brand_* empties carry the chain's logo / name (drawn by the game, never baked words).
"""
import bpy, bmesh, math, os
from rk_nature import leafy_tree, leafy_hedge
from mathutils import Vector

QA_IND = os.path.join(REPO, "unity", "CheckoutSimulator", "Temp", "qa", "industry")
FLAT_ROOF, ROOF_EDGE = "C_C3C8CB", "C_AEB4B8"
ASPHALT, LINE_W, KERB = "C_4A4D50", "C_EDE6D3", "C_BDB6A8"
PAVER = "C_CFC6B4"
GRASS = "C_6E9C48"
TANK_W, TANK_SHADE = "C_F2F2EE", "C_D9DCDA"
COLD_W, COLD_RIB = "C_F5F7F7", "C_E1E6E8"
RED_STRIPE = "C_C7372F"
STEAM = "C_F4F4F2"
BRICK, BRICK_L = "C_B5583D", "C_C9714F"


# --------------------------------------------------------------------------------------------- small pieces
def ground(acc, x0, x1, y0, y1, key, z=.0, t=.06):
    rbox(acc, (x1 - x0, y1 - y0, t), ((x0 + x1) / 2, (y0 + y1) / 2, z - t / 2 + .01), key, .01, 1)


def stripes(acc, x0, y0, y1, n, dx, w=.1):
    for k in range(n + 1):
        x = x0 + k * dx
        rbox(acc, (w, y1 - y0, .012), (x, (y0 + y1) / 2, .026), LINE_W, .004, 1)


def fence(acc, x0, y0, x1, y1, gaps=(), h=1.6):
    """A steel mesh fence along a straight line with navy posts (gaps: (t0, t1) fractions left open for gates)."""
    L = math.hypot(x1 - x0, y1 - y0)
    n = max(1, int(L / 2.5))
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        if any(a < (t0 + t1) / 2 < b for a, b in gaps):
            continue
        cx, cy = x0 + (x1 - x0) * (t0 + t1) / 2, y0 + (y1 - y0) * (t0 + t1) / 2
        rbox(acc, (L / n - .1, .03, h - .15), (cx, cy, h / 2 + .05), "C_9AA6AE", .01, 1, rot=(0, 0, yaw))
        rbox(acc, (L / n, .05, .05), (cx, cy, h), C(NAVY), .01, 1, rot=(0, 0, yaw))
    for k in range(n + 1):
        t = k / n
        if any(a < t < b for a, b in gaps):
            continue
        lathe(acc, [(0, 0), (.05, 0), (.05, h + .05), (0, h + .07)], (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0), C(NAVY), 8, 0)


def roll_door(acc, axis, line, out, u, w, h, frame=C(STEEL), door=DOOR, cold=False):
    """A sectional roller door in a wall (closed), with a steel frame, guards and a downlight."""
    a, b = u - w / 2, u + w / 2
    def B(ua, ub, va, vb, za, zb, key, r=.01, seg=1):
        wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
    B(a, b, -.1, .02, .05, h, door, .01)
    n = 7
    for k in range(1, n):
        z = .05 + k * (h - .05) / n
        B(a + .02, b - .02, .02, .05, z - .02, z + .02, DOOR_D, .006)
    if not cold:
        for k in range(4):
            uu = a + .35 + k * (w - .7) / 3
            B(uu - .2, uu + .2, .02, .04, h * .62, h * .62 + .2, WIN, .02)
    for uu in (a - .08, b + .08):
        B(uu - .08, uu + .08, 0, .14, 0, h + .1, frame, .02)
        for k in range(6):
            B(uu - .08, uu + .08, .14, .17, .12 + k * .2, .3 + k * .2, YELLOW if k % 2 == 0 else BLACK, .004)
    B(a - .16, b + .16, 0, .14, h, h + .16, frame, .02)
    if cold:   # insulated door: a thick rubber cushion round it
        B(a - .3, b + .3, .14, .5, h + .1, h + .55, RUBBER_D, .05, 2)
        for uu in (a - .23, b + .23):
            B(uu - .07, uu + .07, .14, .5, .1, h + .1, RUBBER_D, .03, 2)
    wall_lamp(acc, axis, line, out, u, h + .6)


def person_door(acc, axis, line, out, u, w=1.0, h=2.2, key=C(NAVY)):
    def B(ua, ub, va, vb, za, zb, k, r=.01, seg=1):
        wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, k, r, seg)
    B(u - w / 2 - .06, u + w / 2 + .06, -.04, .06, 0, h + .06, C(STEEL), .01)
    B(u - w / 2, u + w / 2, .02, .05, .02, h, key, .01)
    B(u + w / 2 - .2, u + w / 2 - .12, .05, .1, h * .45, h * .45 + .3, C(CHROME), .005)
    B(u - w / 2 - .3, u + w / 2 + .3, 0, .9, h + .3, h + .42, C(NAVY), .03, 2)
    B(u - w / 2 - .32, u + w / 2 + .32, .85, .92, h + .28, h + .44, C(GOLD), .01)


def window_row(acc, axis, line, out, u0, u1, z0, z1, n):
    def B(ua, ub, va, vb, za, zb, k, r=.01, seg=1):
        wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, k, r, seg)
    B(u0 - .1, u1 + .1, -.02, .08, z0 - .1, z1 + .1, C(NAVY), .02, 2)
    B(u0, u1, .02, .1, z0, z1, WIN, .01)
    for k in range(n + 1):
        uu = u0 + k * (u1 - u0) / n
        B(uu - .04, uu + .04, .06, .13, z0, z1, C(STEEL), .006)
    for k in range(n):
        uu = u0 + (k + .3) * (u1 - u0) / n
        B(uu - .05, uu + .05, .1, .11, z0 + .15, z1 - .15, WIN_HI, .004)
    B(u0 - .15, u1 + .15, 0, .25, z0 - .18, z0 - .1, C(GOLD), .01)


def flat_roof(acc, x0, x1, y0, y1, z, skylights=0, ribs=True):
    rbox(acc, (x1 - x0 - .2, y1 - y0 - .2, .2), ((x0 + x1) / 2, (y0 + y1) / 2, z), FLAT_ROOF, .02, 1)
    if ribs:
        yy = y0 + .7
        while yy < y1 - .5:
            rbox(acc, (x1 - x0 - .5, .05, .06), ((x0 + x1) / 2, yy, z + .12), ROOF_EDGE, .01, 1)
            yy += .9
    for k in range(skylights):
        yy = y0 + (k + 1) * (y1 - y0) / (skylights + 1)
        L = (x1 - x0) * .7
        rbox(acc, (L, 1.2, .28), ((x0 + x1) / 2, yy, z + .22), C(STEEL), .04, 2)
        rbox(acc, (L - .2, 1.0, .1), ((x0 + x1) / 2, yy, z + .42), TRANSLUCENT, .05, 3)


def hall(acc, x0, x1, y0, y1, h, holes=None, band=True, skylights=2, pil=4.6):
    """A clad production hall (rede_dc's clad_wall on the four sides) with a ribbed flat roof.
    holes: {"S": [(u0, u1, z0, z1)], "N": ..., "E": ..., "W": ...} openings (u along x for S/N, along y for E/W)."""
    holes = holes or {}
    clad_wall(acc, "x", y0, -1, x0, x1, h, holes.get("S", ()), pil_every=pil, band=band)
    clad_wall(acc, "x", y1, 1, x0, x1, h, holes.get("N", ()), pil_every=pil, band=band)
    clad_wall(acc, "y", x0, -1, y0, y1, h, holes.get("W", ()), pil_every=pil, band=band)
    clad_wall(acc, "y", x1, 1, y0, y1, h, holes.get("E", ()), pil_every=pil, band=band)
    flat_roof(acc, x0, x1, y0, y1, h - .45, skylights)


def cold_wall(acc, axis, line, out, u0, u1, h, holes=()):
    """Insulated cold-store wall: white sandwich panels with vertical seams every 1.15 m, a navy base band, a red
    safety stripe, a navy top band with gold coping (holes as clad_wall's)."""
    t = .35
    def B(ua, ub, va, vb, za, zb, key, r=.01, seg=1):
        wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
    hu = [(a, b) for a, b, _, _ in holes]
    for a, b in spans(u0, u1, hu):
        B(a, b, -t, 0, 0, h, COLD_W, .01)
    for a, b, za, zb in holes:
        B(a, b, -t, 0, zb, h, COLD_W, .01)
    for a, b in spans(u0, u1, [(x - .05, y + .05) for x, y, z0, _ in holes if z0 < .9]):
        B(a, b, 0, .06, 0, .9, C(NAVY), .02, 2)
        B(a, b, 0, .07, .9, 1.02, RED_STRIPE, .01)
    n = max(1, int((u1 - u0) / 1.15))
    for k in range(1, n):
        uu = u0 + k * (u1 - u0) / n
        if any(a - .1 < uu < b + .1 for a, b in hu):
            continue
        B(uu - .02, uu + .02, 0, .03, 1.02, h - .9, COLD_RIB, .005)
    B(u0 - .02, u1 + .02, 0, .14, h - .9, h, C(NAVY), .03, 2)
    B(u0 - .06, u1 + .06, -t - .05, .2, h, h + .1, C(GOLD), .03, 2)


def cold_box(acc, x0, x1, y0, y1, h, holes=None):
    holes = holes or {}
    cold_wall(acc, "x", y0, -1, x0, x1, h, holes.get("S", ()))
    cold_wall(acc, "x", y1, 1, x0, x1, h, holes.get("N", ()))
    cold_wall(acc, "y", x0, -1, y0, y1, h, holes.get("W", ()))
    cold_wall(acc, "y", x1, 1, y0, y1, h, holes.get("E", ()))
    flat_roof(acc, x0, x1, y0, y1, h - .1, 0)


def silo(acc, x, y, r, h, legs=True):
    """A steel grain / flour silo on a navy skirt: ribbed shell, gold band, cone roof with a vent and a cage ladder."""
    z0 = 1.6 if legs else 0
    if legs:
        for k in range(6):
            a = k * math.pi / 3
            tube(acc, [(x + math.cos(a) * r * .9, y + math.sin(a) * r * .9, 0), (x + math.cos(a) * r * .95, y + math.sin(a) * r * .95, z0 + .2)], .09, C(NAVY), seg=8)
        lathe(acc, [(0, z0 - 1.2), (r * .3, z0 - 1.2), (r, z0), (0, z0)], (x, y, 0), C(STEEL), 32, 0)   # hopper
    lathe(acc, [(r, z0), (r, z0 + h)], (x, y, 0), ALU, 40, 0, cap_top=False, cap_bottom=False)
    for k in range(1, int(h / .9)):
        zz = z0 + k * .9
        lathe(acc, [(r + .005, zz - .03), (r + .03, zz - .02), (r + .03, zz + .02), (r + .005, zz + .03)], (x, y, 0), C(STEEL), 40, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(r + .01, z0 + h * .62), (r + .04, z0 + h * .62), (r + .04, z0 + h * .62 + .45), (r + .01, z0 + h * .62 + .45)], (x, y, 0), C(NAVY), 40, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(r + .01, z0 + h * .62 + .5), (r + .045, z0 + h * .62 + .5), (r + .045, z0 + h * .62 + .6), (r + .01, z0 + h * .62 + .6)], (x, y, 0), C(GOLD), 40, 0, cap_top=False, cap_bottom=False)
    top = z0 + h
    lathe(acc, [(r + .06, top), (r * .25, top + r * .55), (r * .2, top + r * .6), (0, top + r * .6)], (x, y, 0), ALU, 40, 0)
    lathe(acc, [(0, top + r * .6), (.25, top + r * .6), (.25, top + r * .6 + .35), (.35, top + r * .6 + .45), (0, top + r * .6 + .5)], (x, y, 0), C(STEEL), 16, 0)
    # ladder with a cage on the -Y side
    ly = y - r - .12
    for s in (-.2, .2):
        tube(acc, [(x + s, ly, z0), (x + s, ly, top + .3)], .02, C(STEEL), seg=5)
    k = 0
    while z0 + k * .3 < top:
        rbox(acc, (.4, .03, .03), (x, ly, z0 + k * .3), C(STEEL), .005, 1)
        k += 1
    k = 0
    while z0 + 2.2 + k * .8 < top:
        tube(acc, [(x - .25, ly, z0 + 2.2 + k * .8), (x - .3, ly - .4, z0 + 2.2 + k * .8), (x + .3, ly - .4, z0 + 2.2 + k * .8), (x + .25, ly, z0 + 2.2 + k * .8)], .015, C(STEEL), seg=4)
        k += 1


def chimney(acc, x, y, r, h, steam=True):
    """Brick chimney stack on a concrete base with navy / gold bands and a steel cap (and a little steam puff)."""
    rbox(acc, (r * 2.8, r * 2.8, 1.2), (x, y, .6), CONCRETE, .05, 2)
    lathe(acc, [(r, 1.2), (r * .78, h)], (x, y, 0), BRICK, 24, 0, cap_top=False, cap_bottom=False)
    for k in range(1, int(h / 1.4)):
        zz = 1.2 + k * 1.4
        rr = r - (r * .22) * (zz - 1.2) / (h - 1.2)
        lathe(acc, [(rr + .005, zz - .04), (rr + .02, zz - .03), (rr + .02, zz + .03), (rr + .005, zz + .04)], (x, y, 0), BRICK_L, 24, 0, cap_top=False, cap_bottom=False)
    for zz, key in ((h * .7, C(NAVY)), (h * .7 + .55, C(GOLD)), (h - .6, C(NAVY))):
        rr = r - (r * .22) * (zz - 1.2) / (h - 1.2)
        lathe(acc, [(rr + .01, zz), (rr + .05, zz), (rr + .05, zz + .45), (rr + .01, zz + .45)], (x, y, 0), key, 24, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(r * .78 + .08, h), (r * .78 + .12, h + .1), (r * .6, h + .25), (r * .55, h + .1)], (x, y, 0), C(STEEL), 24, 0)
    lathe(acc, [(0, h + .02), (r * .55, h + .02), (r * .55, h + .05), (0, h + .05)], (x, y, 0), BLACK, 24, 0)
    if steam:
        for k, (dx, dz, s) in enumerate(((.0, .9, .55), (.35, 1.9, .75), (.9, 3.0, .95))):
            blob(acc, (r * s * 1.6, r * s * 1.6, r * s * 1.2), (x + dx, y + dx * .4, h + dz), STEAM, sub=2, noise=.25, seed=k + int(x * 7))


def tank(acc, x, y, r, h, key=TANK_W):
    """A vertical process tank on a ring base with a catwalk crown, a side ladder and a gold band."""
    lathe(acc, [(0, 0), (r + .25, 0), (r + .25, .35), (0, .35)], (x, y, 0), CONCRETE, 32, 0)
    lathe(acc, [(r, .35), (r, h)], (x, y, 0), key, 32, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(r + .01, h * .55), (r + .04, h * .55), (r + .04, h * .55 + .3), (r + .01, h * .55 + .3)], (x, y, 0), C(NAVY), 32, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(r + .01, h * .55 + .34), (r + .04, h * .55 + .34), (r + .04, h * .55 + .42), (r + .01, h * .55 + .42)], (x, y, 0), C(GOLD), 32, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(r, h), (r * .7, h + r * .25), (0, h + r * .3)], (x, y, 0), TANK_SHADE, 32, 0)
    for k in range(16):
        a = 2 * math.pi * k / 16
        tube(acc, [(x + math.cos(a) * (r + .05), y + math.sin(a) * (r + .05), h - .05), (x + math.cos(a) * (r + .05), y + math.sin(a) * (r + .05), h + .45)], .012, C(STEEL), seg=4)
    lathe(acc, [(r + .03, h + .43), (r + .07, h + .43), (r + .07, h + .47), (r + .03, h + .47)], (x, y, 0), C(STEEL), 32, 0, cap_top=False, cap_bottom=False)
    for s in (-.18, .18):
        tube(acc, [(x + s, y - r - .1, .35), (x + s, y - r - .1, h + .4)], .02, C(STEEL), seg=5)
    for k in range(int(h / .3)):
        rbox(acc, (.36, .03, .03), (x, y - r - .1, .5 + k * .3), C(STEEL), .005, 1)


def hz_tank(acc, x, y, r, L, key=TANK_W):
    """A horizontal tank on two saddles (along x)."""
    for s in (-1, 1):
        rbox(acc, (.35, r * 1.8, r * .9), (x + s * L * .32, y, r * .45), CONCRETE, .03, 2)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=r, radius2=r, depth=L)
    for v in bm.verts:
        v.co = Vector((v.co.z, v.co.x, v.co.y))
    uv_box(bm)
    place(bm, (x, y, r + .2))
    acc.add(bm, key, "Body")
    for s in (-1, 1):
        lathe(acc, [(0, 0), (r, 0), (r * .6, r * .35), (0, r * .4)], (x + s * L / 2, y, r + .2), key, 28, 0, rot=(0, s * 90, 0))
    for s in (-.25, .25):
        lathe(acc, [(r + .005, -.04), (r + .03, -.03), (r + .03, .03), (r + .005, .04)], (x + s * L, y, r + .2), C(NAVY), 28, 0, rot=(0, 90, 0), cap_top=False, cap_bottom=False)


def condenser(acc, x, y, z, w=2.2, d=1.2, fans=2, yaw=0):
    """A rooftop condensing unit: grey casing, louvres, round fans on top."""
    rbox(acc, (w, d, .9), (x, y, z + .45), "C_D7DCDF", .05, 3, rot=(0, 0, yaw))
    rbox(acc, (w + .04, d + .04, .06), (x, y, z + .03), DASH, .02, 1, rot=(0, 0, yaw))
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for k in range(fans):
        off = (k - (fans - 1) / 2) * (w / fans)
        fx, fy = x + off * ca, y + off * sa
        lathe(acc, [(.34, 0), (.38, 0), (.38, .08), (.34, .08)], (fx, fy, z + .9), DASH, 22, 0, cap_top=False, cap_bottom=False)
        lathe(acc, [(0, 0), (.34, 0), (.34, .01), (0, .01)], (fx, fy, z + .9), "C_4A525C", 22, 0)
        for j in range(3):
            rbox(acc, (.62, .03, .02), (fx, fy, z + .93), C(STEEL), .005, 1, rot=(0, 0, yaw + j * 60))


def cooling_tower(acc, x, y, w=2.6, h=3.2):
    rbox(acc, (w, w, h), (x, y, h / 2), "C_D7DCDF", .06, 3)
    for k in range(int(h / .25)):
        rbox(acc, (w + .02, .02, .05), (x, y - w / 2 - .01, .3 + k * .25), C(STEEL), .005, 1)
    lathe(acc, [(w * .38, h), (w * .42, h + .5), (w * .44, h + .9), (w * .4, h + .9)], (x, y, 0), C(NAVY), 28, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(0, h + .5), (w * .4, h + .5), (w * .4, h + .52), (0, h + .52)], (x, y, 0), "C_4A525C", 28, 0)
    blob(acc, (w * .45, w * .45, w * .3), (x, y, h + 1.6), STEAM, sub=2, noise=.25, seed=int(x * 5 + y))


def pipe_run(acc, pts, r=.09, key=C(STEEL)):
    tube(acc, pts, r, key, seg=10)


def conveyor_bridge(acc, p0, p1, z, w=1.4):
    """An enclosed conveyor gallery between two buildings at height z, on a steel trestle."""
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rbox(acc, (L, w, 1.2), (cx, cy, z), CLAD, .03, 2, rot=(0, 0, yaw))
    rbox(acc, (L + .05, w + .06, .12), (cx, cy, z + .62), C(NAVY), .02, 1, rot=(0, 0, yaw))
    rbox(acc, (L * .9, w + .02, .3), (cx, cy, z + .15), WIN, .01, 1, rot=(0, 0, yaw))
    n = max(1, int(L / 6))
    for k in range(1, n + 1):
        t = k / (n + 1)
        px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        for s in (-1, 1):
            ox, oy = -math.sin(math.radians(yaw)) * s * w * .4, math.cos(math.radians(yaw)) * s * w * .4
            tube(acc, [(px + ox, py + oy, 0), (px + ox, py + oy, z - .6)], .08, C(NAVY), seg=8)


def pallet_stack(acc, x, y, n=3, key="C_C9A06A"):
    for k in range(n):
        rbox(acc, (1.1, 1.1, .14), (x, y, .07 + k * .9), "C_B88A55", .01, 1)
        rbox(acc, (1.0, 1.0, .72), (x, y, .14 + .36 + k * .9), key, .02, 2)
        rbox(acc, (1.02, .12, .74), (x, y - .45, .14 + .36 + k * .9), PLATE, .01, 1)   # band with the logo plate


def trees(acc, pts, seed=0):
    for k, (x, y) in enumerate(pts):
        leafy_tree(acc, (x, y, 0), 4.2 + (k % 3) * .5, 1.8, seed + k, density=.7)


def logo_disc(root, acc, name, loc, R=1.0, yaw=0):
    disc_sign(acc, root, name, loc, R=R, depth=.25, both=False, prefix="Brand_Logo_" + name)


def board(root, name, loc, L, H, yaw=0):
    nb, _ = name_board(f"{root.name}_{name}", (0, 0, 0), L=L, H=H)
    nb.parent = root
    nb.location = Vector(loc)
    nb.rotation_euler = (0, 0, math.radians(yaw))
    return nb


def new_root(name, loc):
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    return root


def finish(root, acc):
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{root.name}_{o.name}"
    return objs


# --------------------------------------------------------------------------------------------- the factory
LOT_W, LOT_D = 36.0, 40.0      # x -18..18, y -20..20; the street (and the camera) on -Y


def lot(acc, tier):
    """The factory's lot: pavers / asphalt grow with the tier, kerbs, a fence with a gate on the street side."""
    x0, x1, y0, y1 = -LOT_W / 2, LOT_W / 2, -LOT_D / 2, LOT_D / 2
    ground(acc, x0, x1, y0, y1, PAVER if tier < 3 else ASPHALT, .0)
    rbox(acc, (LOT_W + .3, .3, .18), (0, y0 - .15, .09), KERB, .03, 2)
    if tier < 3:
        # the back of the lot is still grass: the factory grows into it
        ground(acc, x0 + 1, x1 - 1, -2, y1 - 1, GRASS, .03, .05)
        trees(acc, [(-12.0, 14.0), (2.0, 16.0), (12.5, 12.0)], 7)
    elif tier < 5:
        ground(acc, 5.5, x1 - 1, 8.5, y1 - 1, GRASS, .03, .05)
    gate = ((.38, .52),)
    fence(acc, x0 + .3, y0 + .3, x1 - .3, y0 + .3, gaps=gate)
    fence(acc, x0 + .3, y0 + .3, x0 + .3, y1 - .3)
    fence(acc, x1 - .3, y0 + .3, x1 - .3, y1 - .3)
    fence(acc, x0 + .3, y1 - .3, x1 - .3, y1 - .3)
    # gate pillars with lamps
    for gx in (x0 + LOT_W * .38, x0 + LOT_W * .52):
        rbox(acc, (.5, .5, 2.2), (gx, y0 + .3, 1.1), C(NAVY), .05, 2)
        rbox(acc, (.56, .56, .1), (gx, y0 + .3, 2.25), C(GOLD), .02, 1)
        lathe(acc, [(0, 0), (.16, 0), (.16, .3), (0, .32)], (gx, y0 + .3, 2.3), HEAD_L, 12, 1)


def mini_factory(acc, root):
    """Tier 1 — Mini fábrica: a small brick workshop with one roller door, a side office door, a little extractor
    stack, two pallets of the brand's boxes outside and a logo medallion."""
    x0, x1, y0, y1, h = -16.0, -6.0, -17.0, -9.5, 5.4
    def W(axis, line, out, u0, u1, holes=()):
        def B(ua, ub, va, vb, za, zb, key, r=.01, seg=1):
            wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
        for a, b in spans(u0, u1, [(p, q) for p, q, _, _ in holes]):
            B(a, b, -.3, 0, 0, h, BRICK, .01)
        for a, b, za, zb in holes:
            B(a, b, -.3, 0, zb, h, BRICK, .01)
        # brick courses
        z = .3
        while z < h - .6:
            for a, b in spans(u0, u1, [(p - .05, q + .05) for p, q, za, zb in holes if za - .05 < z < zb + .05]):
                B(a, b, 0, .02, z, z + .03, BRICK_L, .004)
            z += .32
        B(u0, u1, 0, .08, 0, .4, CONCRETE, .015, 2)
        B(u0 - .03, u1 + .03, 0, .16, h - .6, h, C(NAVY), .03, 2)
        B(u0 - .06, u1 + .06, -.35, .2, h, h + .1, C(GOLD), .03, 2)
    W("x", y0, -1, x0, x1, [(-13.6, -10.0, 0, 3.4), (-8.4, -7.4, 0, 2.2)])
    W("x", y1, 1, x0, x1)
    W("y", x0, -1, y0, y1, [(-14.6, -12.4, 1.4, 2.6)])
    W("y", x1, 1, y0, y1, [(-14.4, -12.0, 1.4, 2.6)])
    flat_roof(acc, x0, x1, y0, y1, h - .45, 1)
    roll_door(acc, "x", y0, -1, -11.8, 3.6, 3.4)
    person_door(acc, "x", y0, -1, -7.9, 1.0)
    window_row(acc, "y", x0, -1, -14.6, -12.4, 1.4, 2.6, 2)
    window_row(acc, "y", x1, 1, -14.4, -12.0, 1.4, 2.6, 2)
    # extractor stack + a fan box on the roof
    lathe(acc, [(.32, h - .3), (.3, h + 2.6)], (-8.6, -11.4, 0), C(STEEL), 18, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(.42, h + 2.6), (.42, h + 2.75), (.2, h + 3.0), (0, h + 3.02)], (-8.6, -11.4, 0), C(STEEL), 18, 0)
    condenser(acc, -13.5, -11.0, h - .3, 1.8, 1.0, 1)
    # an awning over the roller door
    rbox(acc, (4.4, 1.6, .2), (-11.8, y0 - .8, 3.95), C(NAVY), .05, 3)
    rbox(acc, (4.44, 1.64, .07), (-11.8, y0 - .8, 3.82), C(GOLD), .02, 1)
    pallet_stack(acc, -15.0, -18.4, 2)
    pallet_stack(acc, -6.8, -18.6, 1, "C_D9B07A")
    logo_disc(root, acc, "Mini", (-9.4, y0 - .14, 4.55), R=.55)
    board(root, "BoardMini", (-13.0, y0 - .3, 4.55), 4.0, .7)


def factory_hall(acc, root):
    """Tier 2 — Fábrica: the main production hall beside the workshop: two loading docks on the street side, a
    window ribbon, two flour silos feeding the hall by a conveyor."""
    x0, x1, y0, y1, h = -4.0, 12.0, -17.0, -3.0, 8.5
    hall(acc, x0, x1, y0, y1, h, {"S": [(-1.6, 1.6, .1, 3.8), (3.4, 6.6, .1, 3.8), (9.0, 10.0, 0, 2.3)]}, skylights=3)
    for u in (0.0, 5.0):
        roll_door(acc, "x", y0, -1, u, 3.2, 3.7)
    person_door(acc, "x", y0, -1, 9.5)
    window_row(acc, "y", x1, 1, -16.0, -12.0, 4.2, 5.6, 3)
    for sy in (-8.0, -3.2):
        silo(acc, 15.0, sy, 1.55, 8.0)
    conveyor_bridge(acc, (13.4, -8.0), (12.2, -8.0), 9.0, 1.0)
    pipe_run(acc, [(15.0, -6.6, 11.2), (15.0, -5.6, 11.2), (12.3, -5.6, 9.4)], .12)
    logo_disc(root, acc, "Hall", (8.2, y0 - .2, 6.6), R=1.1)
    board(root, "BoardHall", (2.6, y0 - .32, 6.6), 9.0, 1.3)
    condenser(acc, 1.0, -6.0, h - .3, 2.4, 1.3, 2)
    condenser(acc, 7.0, -6.0, h - .3, 2.4, 1.3, 2)
    pallet_stack(acc, -2.8, -18.6, 2)


def industry_wing(acc, root):
    """Tier 3 — Indústria: a second, taller hall at the back joined by conveyor galleries, a two-storey glass office
    on the street corner, the first chimney and trees along the street."""
    x0, x1, y0, y1, h = -17.0, 2.0, -1.0, 12.0, 10.5
    hall(acc, x0, x1, y0, y1, h, {"E": [(0.5, 3.5, .1, 3.9), (4.5, 7.5, .1, 3.9)]}, skylights=3)
    for u in (2.0, 6.0):
        roll_door(acc, "y", x1, 1, u, 3.0, 3.8)
    conveyor_bridge(acc, (-1.0, -3.0), (-1.0, -1.0), 7.5)
    conveyor_bridge(acc, (-11.0, -9.5), (-11.0, -1.0), 4.2, 1.1)
    chimney(acc, -15.0, 14.5, .75, 19)
    condenser(acc, -4.0, 9.0, h - .3, 2.6, 1.3, 2)
    # glass office on the front-right corner of the lot
    ox0, ox1, oy0, oy1 = 12.8, 17.4, -19.2, -12.6
    rbox(acc, (ox1 - ox0, oy1 - oy0, 7.2), ((ox0 + ox1) / 2, (oy0 + oy1) / 2, 3.6), "C_5E6E7A", .03, 1)
    for (axis, line, out, u0, u1) in (("x", oy0, -1, ox0, ox1), ("y", ox0, -1, oy0, oy1)):
        for zb in (.4, 3.9):
            window_row(acc, axis, line, out, u0 + .25, u1 - .25, zb, zb + 2.8, 4)
        wbox(acc, axis, line, u0 - .05, u1 + .05, out * -.02, out * .15, 3.3, 3.8, C(NAVY), .02, 2)
    rbox(acc, (ox1 - ox0 + .3, oy1 - oy0 + .3, .5), ((ox0 + ox1) / 2, (oy0 + oy1) / 2, 7.25), C(NAVY), .05, 2)
    rbox(acc, (ox1 - ox0 + .4, oy1 - oy0 + .4, .1), ((ox0 + ox1) / 2, (oy0 + oy1) / 2, 7.55), C(GOLD), .02, 1)
    logo_disc(root, acc, "Office", ((ox0 + ox1) / 2, oy0 - .2, 8.6), R=.8)
    trees(acc, [(-17.0, -19.0), (-5.0, -19.1), (11.2, -19.1)], 3)


def industrial_complex(acc, root):
    """Tier 4 — Complexo industrial: a tank farm, the water tower with the logo on the back hall, a pipe rack, two
    fleet trucks at the back hall's docks."""
    rbox(acc, (7.6, 7.6, .3), (13.5, 2.5, .15), CONCRETE, .02, 1)
    for k, (tx, ty) in enumerate(((11.8, .6), (15.2, .6), (11.8, 4.4), (15.2, 4.4))):
        tank(acc, tx, ty, 1.4, 7.0 + (k % 2) * 1.2)
    pipe_run(acc, [(2.2, 1.0, 7.6), (9.0, 1.0, 7.6), (9.0, .6, 7.6), (10.4, .6, 7.6)], .1)
    pipe_run(acc, [(2.2, 8.0, 8.6), (9.5, 8.0, 8.6), (9.5, 4.4, 8.6), (10.4, 4.4, 8.6)], .1, C(NAVY))
    # pipe rack between the front hall and the tanks
    for k in range(4):
        px = 5.0 + k * 2.2
        for s in (-1, 1):
            tube(acc, [(px, -1.6 + s * .45, 0), (px, -1.6 + s * .45, 5.4)], .08, C(NAVY), seg=8)
        rbox(acc, (.12, 1.1, .12), (px, -1.6, 5.4), C(NAVY), .02, 1)
    for k, key in enumerate((C(STEEL), C(GOLD), C(STEEL))):
        tube(acc, [(4.5, -1.9 + k * .3, 5.6), (11.6, -1.9 + k * .3, 5.6)], .1, key, seg=10)
    wt, _ = water_tower(f"{root.name}_WaterTower", (0, 0, 0))
    wt.parent = root
    wt.location = Vector((-14.0, 9.0, 10.0))
    for k, yy in enumerate((2.0, 6.0)):
        r, _ = truck(f"{root.name}_Truck{k}", (0, 0, 0), reefer=(k == 1))
        r.parent = root
        r.location = Vector((2.0 + .8 + 2.4 * .75, yy, 0))
        r.rotation_euler = (0, 0, math.radians(90))
        r.scale = (.75, .75, .75)


def mega_industry(acc, root):
    """Tier 5 — Megaindústria: an automated high-bay warehouse with a giant logo, solar roofs, a second chimney,
    a glass skybridge, flag poles and a hedge along the street."""
    x0, x1, y0, y1, h = 6.0, 17.5, 9.0, 19.5, 17.0
    hall(acc, x0, x1, y0, y1, h, {"W": [(12.5, 15.5, .1, 4.0)]}, skylights=0, pil=3.2)
    roll_door(acc, "y", x0, -1, 14.0, 3.0, 3.9)
    logo_disc(root, acc, "HighBay", ((x0 + x1) / 2, y0 - .2, 13.0), R=2.1)
    board(root, "BoardHighBay", ((x0 + x1) / 2, y0 - .32, 9.0), 10.0, 1.6)
    chimney(acc, -11.0, 14.8, .7, 17)
    conveyor_bridge(acc, (2.0, 9.5), (6.0, 11.0), 8.0, 2.0)
    for (sx0, sx1, sy0, sy1, z) in ((-3.0, 10.5, -15.5, -10.5, 8.6), (-10.5, 0.5, 0.5, 6.5, 10.6)):
        y = sy0
        while y < sy1:
            x = sx0
            while x + 1.7 < sx1:
                rbox(acc, (1.7, 1.1, .05), (x + .85, y, z), SOLAR, .02, 1, rot=(18, 0, 0))
                rbox(acc, (1.74, 1.14, .03), (x + .85, y, z - .02), SOLAR_F, .02, 1, rot=(18, 0, 0))
                x += 1.85
            y += 1.8
    for k in range(3):
        fx = 2.0 + k * 1.4
        lathe(acc, [(0, 0), (.06, 0), (.04, 8.0), (0, 8.05)], (fx, -19.0, 0), C(STEEL), 10, 0)
        rbox(acc, (1.3, .02, .85), (fx + .68, -19.0, 7.45), (C(NAVY), PLATE, C(GOLD))[k], .01, 1)
    leafy_hedge(acc, (-15.5, -18.8), (-6.8, -18.8), .6, .6, seed=4)


FACTORY_TIERS = [
    ("T1", "Mini fábrica", [mini_factory]),
    ("T2", "Fábrica", [mini_factory, factory_hall]),
    ("T3", "Indústria", [mini_factory, factory_hall, industry_wing]),
    ("T4", "Complexo industrial", [mini_factory, factory_hall, industry_wing, industrial_complex]),
    ("T5", "Megaindústria", [mini_factory, factory_hall, industry_wing, industrial_complex, mega_industry]),
]


def factory(tier, loc=(0, 0, 0)):
    tid, label, parts = FACTORY_TIERS[tier - 1]
    root = new_root(f"Factory{tid}", loc)
    acc = Acc(root.name)
    lot(acc, tier)
    for p in parts:
        p(acc, root)
    finish(root, acc)
    return root


# --------------------------------------------------------------------------------------------- the frigorífico
FL_W, FL_D = 30.0, 30.0        # x -15..15, y -15..15


def frigo_lot(acc, tier):
    x0, x1, y0, y1 = -FL_W / 2, FL_W / 2, -FL_D / 2, FL_D / 2
    ground(acc, x0, x1, y0, y1, ASPHALT, .0)
    rbox(acc, (FL_W + .3, .3, .18), (0, y0 - .15, .09), KERB, .03, 2)
    if tier < 2:
        ground(acc, 0.5, x1 - 1, -2.5, y1 - 1, GRASS, .03, .05)
    if tier < 3:
        ground(acc, x0 + 1, -1.5, 1.5, y1 - 1, GRASS, .03, .05)
    fence(acc, x0 + .3, y0 + .3, x1 - .3, y0 + .3, gaps=((.5, .8),))
    fence(acc, x0 + .3, y0 + .3, x0 + .3, y1 - .3)
    fence(acc, x1 - .3, y0 + .3, x1 - .3, y1 - .3)
    fence(acc, x0 + .3, y1 - .3, x1 - .3, y1 - .3)
    if tier >= 2:
        stripes(acc, 1.8, -9.0, -3.2, 3, 3.8)


def frigo_t1(acc, root):
    """Tier 1 — Entreposto de carnes: a small insulated cold store with one reefer door on the yard, rooftop
    condensers, an office door and a window on the street."""
    x0, x1, y0, y1, h = -14.0, -4.0, -9.0, 0.0, 5.6
    cold_box(acc, x0, x1, y0, y1, h, {"E": [(-6.0, -3.0, .1, 3.6)], "S": [(-6.6, -5.6, 0, 2.2)]})
    roll_door(acc, "y", x1, 1, -4.5, 3.0, 3.5, cold=True)
    person_door(acc, "x", y0, -1, -6.1)
    window_row(acc, "x", y0, -1, -12.8, -9.2, 1.3, 2.4, 3)
    for k in range(2):
        condenser(acc, -11.5 + k * 4.2, -3.5, h - .05, 2.4, 1.3, 2)
    pipe_run(acc, [(-11.5, -2.4, h + .3), (-11.5, -.6, h + .3), (-4.4, -.6, h + .3), (-4.4, -.6, 4.4), (-3.7, -.6, 4.4)], .08)
    board(root, "BoardT1", (-11.0, y0 - .3, 4.5), 5.0, .85)
    logo_disc(root, acc, "T1", (-7.6, y0 - .2, 4.4), R=.55)


def frigo_t2(acc, root):
    """Tier 2 — Frigorífico: a big cold hall with three reefer docks on the yard, rooftop condensers, a compressor
    house with two cooling towers at the back and a reefer truck at a dock."""
    x0, x1, y0, y1, h = 1.0, 14.2, -2.0, 10.0, 8.0
    xs = (3.8, 7.6, 11.4)
    cold_box(acc, x0, x1, y0, y1, h, {"S": [(x - 1.5, x + 1.5, .1, 3.6) for x in xs]})
    for x in xs:
        roll_door(acc, "x", y0, -1, x, 3.0, 3.5, cold=True)
    rbox(acc, (x1 - x0 - .4, 1.4, .9), ((x0 + x1) / 2, y0 - .7, .45), CONCRETE, .03, 2)   # dock platform
    for k in range(4):
        condenser(acc, 4.0 + (k % 2) * 6.2, 1.5 + (k // 2) * 5.0, h - .05, 3.0, 1.5, 3)
    hall(acc, 3.0, 10.5, 10.6, 14.4, 4.6, {"W": [(11.6, 13.4, 0, 2.3)]}, skylights=0, band=False)
    person_door(acc, "y", 3.0, -1, 12.5)
    cooling_tower(acc, 12.6, 11.6, 2.2, 3.0)
    cooling_tower(acc, 12.6, 13.9, 1.8, 2.6)
    pipe_run(acc, [(10.5, 12.0, 3.6), (11.5, 12.0, 3.6), (11.5, 11.6, 3.4)], .14)
    pipe_run(acc, [(6.5, 10.6, 4.2), (6.5, 10.0, 4.2), (6.5, 9.6, 8.4)], .12, C(NAVY))
    board(root, "BoardT2", (7.6, y0 - .32, 6.6), 9.0, 1.3)
    r, _ = truck(f"{root.name}_Reefer", (0, 0, 0), reefer=True)
    r.parent = root
    r.location = Vector((7.6, y0 - 1.4 - .8 - 2.4 * .75, 0))
    r.scale = (.75, .75, .75)


def frigo_t3(acc, root):
    """Tier 3 — Frigorífico industrial: a processing hall on the grass (window ribbon, conveyor from the cold store),
    a tank farm behind it, a steam chimney, an office tower on the street corner and a second reefer truck."""
    x0, x1, y0, y1, h = -14.0, -2.0, 2.0, 11.5, 9.0
    cold_box(acc, x0, x1, y0, y1, h)
    window_row(acc, "x", y0, -1, -12.8, -6.0, 5.2, 6.4, 6)
    window_row(acc, "y", x1, 1, 3.0, 10.5, 5.2, 6.4, 6)
    conveyor_bridge(acc, (-9.0, 0.0), (-9.0, 2.0), 4.6, 1.6)
    for k in range(2):
        condenser(acc, -11.0 + k * 5.0, 7.5, h - .05, 3.0, 1.5, 3)
    rbox(acc, (11.0, 2.6, .3), (-8.5, 13.3, .15), CONCRETE, .02, 1)
    for tx in (-11.0, -6.0):
        hz_tank(acc, tx, 13.3, .85, 4.0)
    pipe_run(acc, [(-11.0, 13.3, 2.2), (-11.0, 11.6, 2.2), (-11.0, 11.6, 6.0)], .1, C(NAVY))
    chimney(acc, -.8, 12.8, .5, 12)
    ox, oy = 11.7, -12.4
    rbox(acc, (5.0, 4.0, 9.5), (ox, oy, 4.75), "C_5E6E7A", .03, 1)
    for zb in (.5, 3.6, 6.7):
        window_row(acc, "x", oy - 2.0, -1, ox - 2.2, ox + 2.2, zb, zb + 2.4, 4)
        window_row(acc, "y", ox - 2.5, -1, oy - 1.7, oy + 1.7, zb, zb + 2.4, 3)
    rbox(acc, (5.3, 4.3, .5), (ox, oy, 9.75), C(NAVY), .05, 2)
    rbox(acc, (5.4, 4.4, .1), (ox, oy, 10.05), C(GOLD), .02, 1)
    logo_disc(root, acc, "T3", (ox, oy - 2.22, 11.2), R=.85)
    r, _ = truck(f"{root.name}_Reefer2", (0, 0, 0), reefer=True)
    r.parent = root
    r.location = Vector((11.4, -2.0 - 1.4 - .8 - 2.4 * .75, 0))
    r.scale = (.75, .75, .75)


FRIGO_TIERS = [
    ("T1", "Entreposto de carnes", [frigo_t1]),
    ("T2", "Frigorífico", [frigo_t1, frigo_t2]),
    ("T3", "Frigorífico industrial", [frigo_t1, frigo_t2, frigo_t3]),
]


def frigo(tier, loc=(0, 0, 0)):
    tid, label, parts = FRIGO_TIERS[tier - 1]
    root = new_root(f"Frigo{tid}", loc)
    acc = Acc(root.name)
    frigo_lot(acc, tier)
    for p in parts:
        p(acc, root)
    finish(root, acc)
    return root


# --------------------------------------------------------------------------------------------- previews
def setup(scene):
    rk_core.clear(scene)
    rk_core.studio((1800, 1100), bg=(.86, .84, .8))
    preview_setup()
    rk_core.PREVIEW = QA_IND
    fl = bpy.data.objects.get("RK_Floor")
    if fl:
        fl.scale = (8, 8, 1)
        fl.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.62, .62, .6, 1)


def tri_count(root):
    n = 0
    for o in root.children_recursive:
        if o.type == "MESH":
            n += sum(len(p.vertices) - 2 for p in o.data.polygons)
    return n


GAMECAM = (-.5, -.8, .85)      # roughly the game's view direction (from the front-left, high)


def shoot_factory():
    out, info = [], []
    for t in range(1, 6):
        setup("Industry Factory")
        root = factory(t)
        info.append(f"factory T{t}: {tri_count(root)} tris")
        out.append(rk_core.shoot(f"factory_T{t}", (0, 0, 3), GAMECAM, 80, 36, (1800, 1100)))
    setup("Industry Factory")
    root = factory(5)
    out.append(rk_core.shoot("factory_T5_front", (2, -4, 5), (-.15, -1, .42), 52, 36, (1800, 1100)))
    out.append(rk_core.shoot("factory_T5_back", (2, 4, 5), (.7, .8, .6), 58, 36, (1800, 1100)))
    return out, info


def shoot_frigo():
    out, info = [], []
    for t in range(1, 4):
        setup("Industry Frigo")
        root = frigo(t)
        info.append(f"frigo T{t}: {tri_count(root)} tris")
        out.append(rk_core.shoot(f"frigo_T{t}", (0, 0, 2.5), GAMECAM, 66, 36, (1800, 1100)))
    setup("Industry Frigo")
    frigo(3)
    out.append(rk_core.shoot("frigo_T3_front", (0, -3, 3), (-.25, -1, .45), 42, 36, (1800, 1100)))
    return out, info
