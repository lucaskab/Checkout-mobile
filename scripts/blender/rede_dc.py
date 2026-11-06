"""Rede de supermercados, round 2 (Lucas 05/11): the distribution centre building (the hypermarket's "Armazém central"
was simple and small) and the market's ceiling decorations (the bunting and pendant lamps read as stray marks from the
game's camera: "minha irmã não entendeu o que era").

Run after rede_assets.py in the same namespace (its helpers: rbox, rpanel, rframe, lathe, tube, prism, anchor, Acc,
disc_sign, name_board, water_tower, blob...):
    exec(open(REPO + "/scripts/blender/rede_dc.py").read(), ns); ns["build_dc_v2"]()

Space: metres, Z up. The DC stands on the Warehouse Large footprint (18.4 x 18 m, centre = origin): its docks face +X
(east, the truck yard) at the yard's three bays (y -1.45 / +1.55 / +4.55) plus a fourth for show, its front faces -Y
(south, towards the market and the camera). Material contract as rede_assets.py (C_1D2B4F navy and C_D3A53D gold are
repainted with the market's colours; no written words: Brand_* empties on blank plates).
"""
import bpy, bmesh, math
from mathutils import Vector

W2, D2 = 9.2, 9.0                    # half width (x) and half depth (y)
H_BAY, H_OFFICE = 11.0, 7.4          # high bay and office block heights (top of the parapet)
OFF_X1, OFF_Y1 = -2.2, -3.0          # the office block: x -9.2..-2.2, y -9..-3 (south-west corner)
DOCKS = (-4.45, -1.45, 1.55, 4.55)   # dock door centres on the east wall (the last three are the yard's bays)
DOCK_W, DOCK_Z0, DOCK_Z1 = 3.0, 1.1, 4.3

CLAD, RIB, PLINTH = "C_EEF0EE", "C_DCE0DF", "C_A8A399"
DOOR, DOOR_D = "C_D9DFE3", "C_9AA4AC"
ROOF, ROOF_RIB = "C_B9BFC3", "C_A9AFB4"
TRANSLUCENT = "C_CFE4EA"
SOLAR, SOLAR_F = "C_24324F", "C_C0C8CE"
YELLOW, BLACK = "C_F2C230", "C_2B2F36"
CONCRETE = "C_C9C3B6"
SHRUB, SHRUB2, SOIL = "C_4E9A3E", "C_5FB04A", "C_6B4A2E"


# --------------------------------------------------------------------------------------------- wall helpers
def wbox(acc, axis, line, u0, u1, v0, v1, z0, z1, key, r=.02, seg=1):
    """A box in a wall's frame: u along the wall, v outwards from the wall line, z up.
    axis "x": the wall runs along x at y = line, outwards = sign of v (callers pass v already signed by side)."""
    if u1 < u0: u0, u1 = u1, u0
    if v1 < v0: v0, v1 = v1, v0
    if axis == "x":
        size, loc = (u1 - u0, v1 - v0, z1 - z0), ((u0 + u1) / 2, line + (v0 + v1) / 2, (z0 + z1) / 2)
    else:
        size, loc = (v1 - v0, u1 - u0, z1 - z0), (line + (v0 + v1) / 2, (u0 + u1) / 2, (z0 + z1) / 2)
    if min(size) <= .0005: return
    rbox(acc, size, loc, key, min(r, min(size) * .45), seg)


def spans(u0, u1, holes):
    """The pieces of [u0, u1] left between the holes (sorted (a, b) pairs)."""
    out, at = [], u0
    for a, b in sorted(holes):
        if a > at: out.append((at, a))
        at = max(at, b)
    if at < u1: out.append((at, u1))
    return out


def clad_wall(acc, axis, line, out, u0, u1, z1, holes=(), pil_every=4.6, band=True, z0=0.0):
    """A clad warehouse wall: concrete plinth, light ribbed metal panels (a rib every 0.45 m), a gold stripe, a band
    of translucent panels under a navy cornice with gold coping, navy pilasters. holes: [(u0, u1, z0, z1)] openings
    (the panels stop around them). out: +1/-1, the side the wall faces."""
    t = .3
    def B(ua, ub, va, vb, za, zb, key, r=.02, seg=1):
        wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
    # the core, cut around the holes: columns between them, then above / below each one
    hu = [(h[0], h[1]) for h in holes]
    for a, b in spans(u0, u1, hu):
        B(a, b, -t, 0, z0, z1, CLAD, .01)
    for a, b, za, zb in holes:
        B(a, b, -t, 0, zb, z1, CLAD, .01)
        if za > z0 + .01: B(a, b, -t, 0, z0, za, CONCRETE, .01)
    # plinth and ribs (split by the holes that reach them)
    for a, b in spans(u0, u1, [(h[0], h[1]) for h in holes if h[2] < .7]):
        B(a, b, 0, .06, z0, z0 + .7, PLINTH, .015, 2)
    top_band = z1 - 1.1
    z = z0 + .95
    while z < top_band - (1.2 if band else .1):
        cut = [(h[0] - .05, h[1] + .05) for h in holes if h[2] - .04 < z < h[3] + .08]
        for a, b in spans(u0, u1, cut):
            B(a, b, 0, .035, z, z + .05, RIB, .01)
        z += .45
    # gold stripe at 3 m (not over the docks)
    for a, b in spans(u0, u1, [(h[0] - .1, h[1] + .1) for h in holes if h[2] < 3.1 < h[3] + .1]):
        B(a, b, 0, .05, 2.95, 3.07, C(GOLD), .015, 2)
    # translucent band and the cornice
    if band:
        for a, b in spans(u0 + .3, u1 - .3, [(h[0], h[1]) for h in holes if h[3] > top_band - 1.2]):
            B(a, b, 0, .03, top_band - 1.05, top_band - .15, TRANSLUCENT, .01)
            n = max(1, int((b - a) / 1.15))
            for k in range(n + 1):
                uu = a + k * (b - a) / n
                B(uu - .03, uu + .03, 0, .05, top_band - 1.1, top_band - .1, C(STEEL), .01)
    B(u0 - .02, u1 + .02, 0, .14, top_band, z1, C(NAVY), .03, 2)
    B(u0 - .06, u1 + .06, -t - .05, .2, z1, z1 + .1, C(GOLD), .03, 2)
    # pilasters
    n = max(1, round((u1 - u0) / pil_every))
    for k in range(n + 1):
        uu = u0 + k * (u1 - u0) / n
        if any(h[0] - .3 < uu < h[1] + .3 for h in holes): continue
        B(uu - .2, uu + .2, 0, .16, z0 + .7, top_band, C(NAVY), .03, 2)
        B(uu - .24, uu + .24, 0, .2, z0, z0 + .7, PLINTH, .03, 2)


def wall_lamp(acc, axis, line, out, u, z, key=None):
    """A wall pack light: navy housing, warm lens facing down/out."""
    wbox(acc, axis, line, u - .18, u + .18, 0, out * .22, z - .14, z + .14, C(NAVY), .04, 2)
    wbox(acc, axis, line, u - .14, u + .14, out * .05, out * .24, z - .16, z - .1, key or HEAD_L, .02, 1)


def downpipe(acc, x, y, z1):
    tube(acc, [(x, y, z1), (x, y, .35), (x, y, .12)], .07, C(STEEL), seg=10)
    lathe(acc, [(.07, 0), (.12, .1), (.12, .25), (.07, .25)], (x, y, z1 - .3), C(STEEL), 10, 0, cap_top=False, cap_bottom=False)


# --------------------------------------------------------------------------------------------- docks
def dock(acc, root, yc, active=True):
    """One loading dock on the east wall: steel-framed opening, sectional door with a window row, black foam
    shelter with yellow guides, rubber bumpers, leveller lip, swing-arm dock light, traffic light, guide posts."""
    x = W2
    a, b = yc - DOCK_W / 2, yc + DOCK_W / 2
    # reveal frame
    for yy in (a - .08, b + .08):
        rbox(acc, (.18, .16, DOCK_Z1 - DOCK_Z0 + .16), (x + .02, yy, (DOCK_Z0 + DOCK_Z1) / 2), C(STEEL), .02, 1)
    rbox(acc, (.18, DOCK_W + .32, .16), (x + .02, yc, DOCK_Z1 + .08), C(STEEL), .02, 1)
    # the door (closed on the decorative bay, half up on the others: a dark inside shows under it)
    open_to = DOCK_Z0 if not active else DOCK_Z0 + .0
    rbox(acc, (.06, DOCK_W, DOCK_Z1 - open_to), (x - .12, yc, (open_to + DOCK_Z1) / 2), DOOR, .01, 1)
    n = 6
    for k in range(1, n):
        z = open_to + k * (DOCK_Z1 - open_to) / n
        rbox(acc, (.03, DOCK_W - .04, .035), (x - .08, yc, z), DOOR_D, .008, 1)
    zw = open_to + 3.5 * (DOCK_Z1 - open_to) / n
    for k in range(5):
        rpanel(acc, .42, .2, .02, (x - .075, a + .35 + k * (DOCK_W - .7) / 4, zw), WIN, .04, rot=(0, 0, 90))
    rbox(acc, (.05, .3, .05), (x - .07, yc, open_to + .25), C(STEEL), .01, 1)       # handle
    # shelter: side pads, head curtain, yellow guide stripes
    for s, yy in ((-1, a - .32), (1, b + .32)):
        rbox(acc, (.55, .36, DOCK_Z1 - DOCK_Z0 + .5), (x + .3, yy, (DOCK_Z0 + DOCK_Z1 + .5) / 2), RUBBER_D, .06, 3)
        rbox(acc, (.02, .1, DOCK_Z1 - DOCK_Z0), (x + .585, yy - s * .06, (DOCK_Z0 + DOCK_Z1) / 2 + .1), C(YELLOW), .005, 1)
    rbox(acc, (.62, DOCK_W + 1.0, .65), (x + .32, yc, DOCK_Z1 + .45), RUBBER_D, .06, 3)
    for k in range(7):
        rbox(acc, (.03, .02, .5), (x + .64, a + .1 + k * (DOCK_W - .2) / 6, DOCK_Z1 + .38), RUBBER, .005, 1)
    # dock face below the door: bumpers, leveller lip, hazard edge
    for yy in (yc - 1.15, yc + 1.15):
        rbox(acc, (.2, .32, .5), (x + .1, yy, .78), RUBBER, .04, 3)
        rbox(acc, (.06, .26, .06), (x + .19, yy, .9), C(STEEL), .01, 1)
    rbox(acc, (.32, 2.2, .04), (x + .12, yc, DOCK_Z0 - .02), C(STEEL), .01, 1)
    for k in range(10):
        rbox(acc, (.03, .22, .12), (x + .02, a + .3 + k * .26, DOCK_Z0 - .1), C(YELLOW if k % 2 == 0 else BLACK), .004, 1)
    # dock light on a swing arm, traffic light
    ly = b + .75
    rbox(acc, (.08, .2, .3), (x + .04, ly, 3.4), C(NAVY), .02, 1)
    tube(acc, [(x + .08, ly, 3.4), (x + .5, ly - .25, 3.45), (x + .78, ly - .55, 3.42)], .025, C(STEEL), seg=6)
    lathe(acc, [(0, 0), (.11, 0), (.13, .1), (.06, .2), (0, .2)], (x + .82, ly - .58, 3.42), C(NAVY), 12, 1, rot=(0, 120, -40))
    lathe(acc, [(0, 0), (.1, 0), (0, .01)], (x + .9, ly - .62, 3.37), HEAD_L, 10, 0, rot=(0, 120, -40))
    tl = a - .78
    rbox(acc, (.1, .22, .5), (x + .05, tl, 2.3), BLACK, .03, 2)
    lathe(acc, [(0, 0), (.06, 0), (.06, .02), (0, .02)], (x + .1, tl, 2.42), RED_L, 12, 0, rot=(0, 90, 0))
    lathe(acc, [(0, 0), (.06, 0), (.06, .02), (0, .02)], (x + .1, tl, 2.18), "E_5BE35B", 12, 0, rot=(0, 90, 0))
    # guide posts on the apron
    for yy in (a - .55, b + .55):
        lathe(acc, [(0, 0), (.09, 0), (.09, 1.05), (.07, 1.12), (0, 1.14)], (x + 1.0, yy, 0), C(YELLOW), 12, 1)
        lathe(acc, [(.092, .7), (.092, .85)], (x + 1.0, yy, 0), C(BLACK), 12, 0, cap_top=False, cap_bottom=False)


# --------------------------------------------------------------------------------------------- the office block
def office(acc, root):
    """Two-storey glass office in the south-west corner: curtain walls on the south and west, a navy spandrel band
    between the floors, entrance doors under a cantilever canopy with a logo plate, planters, bollards, bike rack."""
    x0, x1, y0, y1, H = -W2, OFF_X1, -D2, OFF_Y1, H_OFFICE
    F1 = 3.7
    # floor slabs and back walls (the glass sits on a frame)
    rbox(acc, (x1 - x0, y1 - y0, .25), ((x0 + x1) / 2, (y0 + y1) / 2, F1), CLAD, .02, 1)
    rbox(acc, (x1 - x0 - .4, y1 - y0 - .4, H - .5), ((x0 + x1) / 2 + .2, (y0 + y1) / 2 + .2, (H - .5) / 2), C("5E6E7A"), .02, 1)
    rbox(acc, (x1 - x0, y1 - y0, .3), ((x0 + x1) / 2, (y0 + y1) / 2, H - .65), CLAD, .02, 1)
    def curtain(axis, line, out, u0, u1, door=None):
        def B(ua, ub, va, vb, za, zb, key, r=.015, seg=1):
            wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
        B(u0, u1, -.12, -.06, .25, H - .8, WIN, .01)                              # glass
        B(u0, u1, -.02, .1, 0, .3, PLINTH, .015, 2)
        B(u0, u1, -.04, .12, F1 - .15, F1 + .55, C(NAVY), .02, 2)                # spandrel
        B(u0, u1, -.04, .13, F1 + .2, F1 + .28, C(GOLD), .01, 1)
        B(u0 - .05, u1 + .05, -.1, .18, H - .8, H, C(NAVY), .03, 2)              # parapet band
        B(u0 - .1, u1 + .1, -.2, .22, H, H + .1, C(GOLD), .02, 2)
        n = max(1, round((u1 - u0) / 1.17))
        for k in range(n + 1):
            uu = u0 + k * (u1 - u0) / n
            if door and door[0] - .05 < uu < door[1] + .05:
                B(uu - .04, uu + .04, -.06, .06, F1 + .55, H - .8, C(STEEL), .008)
                continue
            B(uu - .045, uu + .045, -.06, .07, .3, H - .8, C(STEEL), .008)
        for zz in (1.15, 2.6, F1 + 1.6, F1 + 2.6):
            if door and zz < F1:
                for a, b in spans(u0, u1, [door]): B(a, b, -.06, .06, zz - .03, zz + .03, C(STEEL), .008)
            else:
                B(u0, u1, -.06, .06, zz - .03, zz + .03, C(STEEL), .008)
        # reflections: a few lighter diagonal glints
        for k in range(3):
            uu = u0 + (k + .5) * (u1 - u0) / 3
            B(uu - .08, uu + .08, -.055, -.05, F1 + .9, H - 1.2, WIN_HI, .005)
            B(uu + .12, uu + .17, -.055, -.05, F1 + 1.2, H - 1.5, WIN_HI, .005)
    door = (-6.4, -4.6)
    curtain("x", y0, -1, x0 + .1, x1, door)
    curtain("y", x0, -1, y0 + .1, y1)
    # corner column
    rbox(acc, (.34, .34, H), (x0, y0, H / 2), C(NAVY), .05, 2)
    # entrance: sliding glass doors with a steel frame, mat, canopy
    dx = (door[0] + door[1]) / 2
    rframe(acc, door[1] - door[0], 2.6, .12, .1, (dx, y0 - .02, 1.3), C(STEEL), .02)
    for s in (-1, 1):
        rpanel(acc, (door[1] - door[0]) / 2 - .12, 2.4, .03, (dx + s * .45, y0 - .06, 1.25), C("8FB2C4"), .02)
        rbox(acc, (.04, .04, .5), (dx + s * .1, y0 - .1, 1.15), C(CHROME), .01, 1)
    rbox(acc, (door[1] - door[0] + .2, 1.0, .04), (dx, y0 - .55, .02), C("4A4F57"), .01, 1)
    cy = y0 - 1.0
    rbox(acc, (4.4, 2.0, .32), (dx, cy, 3.25), C(NAVY), .06, 3)
    rbox(acc, (4.44, 2.04, .1), (dx, cy, 3.06), C(GOLD), .03, 2)
    rbox(acc, (4.2, 1.8, .03), (dx, cy, 3.02), C("F4F1E8"), .01, 1)
    for k in range(3):
        lathe(acc, [(0, 0), (.09, 0), (0, .01)], (dx - 1.2 + k * 1.2, cy - .3, 3.0), HEAD_L, 12, 0, rot=(180, 0, 0))
    for s in (-1, 1):
        tube(acc, [(dx + s * 2.0, cy - .9, 3.1), (dx + s * 2.0, y0 - .15, 5.2)], .03, C(STEEL), seg=6)   # tie rods
    rpanel(acc, 1.3, .26, .012, (dx, cy - 1.025, 3.25), PLATE, .05)
    anchor("Brand_Name_Entrance", (dx, cy - 1.033, 3.25), (0, 0, 0), .2, root)
    # planters with shrubs, bollards, bike rack
    for px in (dx - 2.9, dx + 2.9):
        rbox(acc, (1.1, .7, .6), (px, y0 - .7, .3), C(NAVY), .06, 3)
        rbox(acc, (1.14, .74, .06), (px, y0 - .7, .62), C(GOLD), .02, 2)
        rbox(acc, (1.0, .6, .04), (px, y0 - .7, .6), SOIL, .02, 1)
        for k in range(5):
            blob(acc, (.22, .2, .2), (px - .36 + k * .18, y0 - .7 + (k % 2 - .5) * .14, .78), SHRUB if k % 2 else SHRUB2, sub=2, noise=.25, seed=k + int(px * 3))
    for k in range(4):
        bx = x1 + .6 + k * 1.1
        lathe(acc, [(0, 0), (.1, 0), (.1, .8), (.08, .9), (0, .92)], (bx, y0 - .9, 0), C(NAVY), 14, 1)
        lathe(acc, [(.102, .62), (.102, .7)], (bx, y0 - .9, 0), C(GOLD), 14, 0, cap_top=False, cap_bottom=False)
    for k in range(4):
        tube(acc, [(x0 + 1.0 + k * .5, y0 - 1.6, 0), (x0 + 1.0 + k * .5, y0 - 1.6, .75), (x0 + 1.0 + k * .5, y0 - 2.2, .75), (x0 + 1.0 + k * .5, y0 - 2.2, 0)], .03, C(STEEL), seg=6, smooth_n=2)
    # roof: HVAC box, skylight dome, railing
    rbox(acc, (1.8, 1.2, .9), (x0 + 2.2, y1 - 1.4, H - .5 + .45), C("C9D0D4"), .05, 3)
    for k in range(2):
        lathe(acc, [(.32, 0), (.36, 0), (.36, .06), (.32, .06)], (x0 + 1.75 + k * .9, y1 - 1.4, H + .4), C(DASH), 20, 0, cap_top=False, cap_bottom=False)
        lathe(acc, [(0, 0), (.32, 0), (.32, .01), (0, .01)], (x0 + 1.75 + k * .9, y1 - 1.4, H + .38), C("4A525C"), 20, 0)
    rbox(acc, (1.6, 1.6, .25), (x0 + 4.6, y0 + 2.6, H - .5 + .12), C(STEEL), .04, 2)
    lathe(acc, [(0, 0), (.7, 0), (.6, .25), (.3, .4), (0, .44)], (x0 + 4.6, y0 + 2.6, H - .25), TRANSLUCENT, 20, 2)


# --------------------------------------------------------------------------------------------- the roof
def roof(acc, root):
    """High bay roof: deck with standing seams, three skylight strips, HVAC units with fans, vents, a roof hatch,
    a solar array on the north-west wing and a cable tray."""
    deck = H_BAY - .5
    # deck: L-shape (A: the east part over the docks, B: the north-west wing behind the office)
    for (ax0, ax1, ay0, ay1) in ((OFF_X1, W2, -D2, D2), (-W2, OFF_X1, OFF_Y1, D2)):
        rbox(acc, (ax1 - ax0 - .3, ay1 - ay0 - .3, .2), ((ax0 + ax1) / 2, (ay0 + ay1) / 2, deck), ROOF, .02, 1)
        yy = ay0 + .6
        while yy < ay1 - .4:
            rbox(acc, (ax1 - ax0 - .5, .05, .07), ((ax0 + ax1) / 2, yy, deck + .13), ROOF_RIB, .01, 1)
            yy += .9
    # skylights on A
    for yy in (-5.2, -.2, 4.8):
        rbox(acc, (8.6, 1.3, .3), (3.6, yy, deck + .25), C(STEEL), .04, 2)
        rbox(acc, (8.4, 1.1, .12), (3.6, yy, deck + .45), TRANSLUCENT, .05, 3)
        for k in range(8):
            rbox(acc, (.05, 1.12, .14), (-.5 + k * 1.17, yy, deck + .46), C(STEEL), .01, 1)
    # HVAC units
    for (hx, hy) in ((-.9, -7.3), (-.9, 2.3), (7.2, -7.4)):
        rbox(acc, (2.2, 1.4, 1.0), (hx, hy, deck + .6), C("C9D0D4"), .06, 3)
        rbox(acc, (2.24, 1.44, .08), (hx, hy, deck + .14), C(DASH), .02, 1)
        for s in (-1, 1):
            lathe(acc, [(.38, 0), (.43, 0), (.43, .08), (.38, .08)], (hx + s * .52, hy, deck + 1.1), C(DASH), 22, 0, cap_top=False, cap_bottom=False)
            lathe(acc, [(0, 0), (.38, 0), (.38, .01), (0, .01)], (hx + s * .52, hy, deck + 1.1), C("4A525C"), 22, 0)
            for k in range(5):
                rbox(acc, (.7, .03, .02), (hx + s * .52, hy - .3 + k * .15, deck + 1.13), C(STEEL), .005, 1)
        for k in range(6):
            rbox(acc, (.02, .02, .7), (hx - 1.11, hy - .5 + k * .2, deck + .55), C(STEEL), .005, 1)   # side louvres
        tube(acc, [(hx, hy + .7, deck + .4), (hx, hy + 1.6, deck + .4), (hx, hy + 1.6, deck + .2)], .2, C(STEEL), seg=12)
    # vents and the hatch
    for (vx, vy) in ((1.5, 7.5), (3.0, 7.5), (8.3, 2.0), (8.3, -2.8)):
        lathe(acc, [(0, 0), (.18, 0), (.18, .55), (.32, .6), (.3, .7), (0, .72)], (vx, vy, deck + .1), C(STEEL), 16, 1)
    rbox(acc, (1.1, 1.1, .45), (6.0, -2.6, deck + .3), C("C9D0D4"), .05, 2)
    rbox(acc, (1.15, 1.15, .06), (6.0, -2.6, deck + .55), C(NAVY), .02, 1)
    # solar array on the north-west wing
    for row in range(4):
        y = .6 + row * 1.9
        for col in range(3):
            x = -8.0 + col * 1.85
            rbox(acc, (1.7, 1.1, .05), (x, y, deck + .55), SOLAR, .02, 1, rot=(18, 0, 0))
            rbox(acc, (1.74, 1.14, .03), (x, y, deck + .53), SOLAR_F, .02, 1, rot=(18, 0, 0))
            for k in range(1, 4):
                rbox(acc, (.015, 1.1, .055), (x - .85 + k * .425, y, deck + .552), SOLAR_F, .004, 1, rot=(18, 0, 0))
            for s in (-1, 1):
                rbox(acc, (.05, .05, .5), (x + s * .7, y + .35, deck + .3), C(STEEL), .01, 1)
                rbox(acc, (.05, .05, .25), (x + s * .7, y - .35, deck + .18), C(STEEL), .01, 1)
    # cable tray along the solar rows
    rbox(acc, (.25, 7.6, .1), (-3.1, 4.4, deck + .2), C(STEEL), .02, 1)


# --------------------------------------------------------------------------------------------- the building
def dc_building(name="RedeDC", loc=(0, 0, 0)):
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    personnel = (-7.8, -6.8, 0, 2.3)
    east_holes = [(yc - DOCK_W / 2 - .45, yc + DOCK_W / 2 + .45, DOCK_Z0 - .05, DOCK_Z1 + .9) for yc in DOCKS] + [personnel]
    # walls: east (docks), north, west wing, south of A, the step above the office (south face of B, east face of
    # the office's top)
    clad_wall(acc, "y", W2, 1, -D2, D2, H_BAY, east_holes)
    clad_wall(acc, "x", D2, 1, -W2, W2, H_BAY)
    clad_wall(acc, "y", -W2, -1, OFF_Y1, D2, H_BAY, [(3.0, 4.0, 4.4, 6.6)])
    exit_door = (5.6, 6.8, 0, 2.4)
    clad_wall(acc, "x", -D2, -1, OFF_X1, W2, H_BAY, [exit_door])
    clad_wall(acc, "x", OFF_Y1, -1, -W2, OFF_X1, H_BAY, z0=H_OFFICE - .2, band=False)
    clad_wall(acc, "y", OFF_X1, -1, -D2, OFF_Y1, H_BAY, z0=H_OFFICE - .2, band=False)
    for yc in DOCKS:
        dock(acc, root, yc, active=yc != DOCKS[0])
    # dock canopy over the four bays
    cy0, cy1 = DOCKS[0] - 2.1, DOCKS[-1] + 2.1
    rbox(acc, (2.8, cy1 - cy0, .38), (W2 + 1.4, (cy0 + cy1) / 2, 5.6), C(NAVY), .06, 3)
    rbox(acc, (.12, cy1 - cy0 + .04, .14), (W2 + 2.82, (cy0 + cy1) / 2, 5.5), C(GOLD), .03, 2)
    rbox(acc, (2.7, cy1 - cy0 - .1, .03), (W2 + 1.4, (cy0 + cy1) / 2, 5.4), C("F4F1E8"), .01, 1)
    for yc in DOCKS:
        lathe(acc, [(0, 0), (.14, 0), (0, .01)], (W2 + 1.6, yc, 5.39), HEAD_L, 12, 0, rot=(180, 0, 0))
    for yy in (cy0 + .4, (cy0 + cy1) / 2, cy1 - .4):
        tube(acc, [(W2 + 2.6, yy, 5.75), (W2 + .05, yy, 7.6)], .045, C(STEEL), seg=8)
    # personnel door on the east wall (south end): door, small canopy, lamp, steps
    pd = (personnel[0] + personnel[1]) / 2
    rframe(acc, 1.1, 2.3, .1, .08, (W2 + .02, pd, 1.15), C(STEEL), .02, rot=(0, 0, 90))
    rpanel(acc, .94, 2.18, .04, (W2 - .02, pd, 1.1), C(NAVY), .02, rot=(0, 0, 90))
    rbox(acc, (.03, .05, .3), (W2 + .03, pd + .32, 1.05), C(CHROME), .01, 1)
    rbox(acc, (1.0, 1.6, .12), (W2 + .5, pd, 2.65), C(NAVY), .03, 2)
    rbox(acc, (1.02, 1.62, .04), (W2 + .5, pd, 2.58), C(GOLD), .01, 1)
    # emergency exit (south wall): door + green running-man-free plate (just a lit green panel)
    ex = (exit_door[0] + exit_door[1]) / 2
    rframe(acc, 1.3, 2.4, .1, .08, (ex, -D2 - .02, 1.2), C(STEEL), .02)
    rpanel(acc, 1.14, 2.26, .04, (ex, -D2 + .02, 1.13), C("C7372F"), .02)
    rbox(acc, (.8, .05, .04), (ex, -D2 - .06, 1.05), C(CHROME), .01, 1)
    rpanel(acc, .5, .2, .03, (ex, -D2 - .03, 2.65), "E_5BE35B", .03)
    # west fire stair from the mezzanine door down to the ground
    wx = -W2 - .05
    for k in range(16):
        z = .28 * (k + 1)
        y = -1.35 + k * .28
        rbox(acc, (1.0, .3, .05), (wx - .6, y, z), C(STEEL), .01, 1)
    for s in (-.1, -1.1):                                                       # stringers
        tube(acc, [(wx + s, -1.6, 0), (wx + s, 2.9, 4.45)], .04, C(NAVY), seg=6)
    rbox(acc, (1.1, 1.3, .08), (wx - .6, 3.5, 4.45), C(STEEL), .01, 1)
    for s in (-.1, -1.1):
        tube(acc, [(wx + s, 4.15, 5.45), (wx + s, 4.15, 4.45)], .025, C(NAVY), seg=6)
        tube(acc, [(wx + s, 4.15, 5.45), (wx + s, 2.85, 5.45), (wx + s, -1.35, 1.25), (wx + s, -1.35, .3)], .025, C(NAVY), seg=6)
    tube(acc, [(wx - 1.1, 2.85, 4.45), (wx - 1.1, 2.85, 0)], .05, C(NAVY), seg=8)
    rframe(acc, 1.0, 2.2, .1, .08, (-W2 - .02, 3.5, 5.55), C(STEEL), .02, rot=(0, 0, 90))
    rpanel(acc, .86, 2.08, .04, (-W2 + .01, 3.5, 5.5), C("C7372F"), .02, rot=(0, 0, 90))
    # downpipes and wall lamps
    for (px, py) in ((W2 + .1, -D2 + .25), (W2 + .1, D2 - .25), (-W2 - .1, D2 - .25), (-W2 - .1, OFF_Y1 + .3), (OFF_X1 + .3, -D2 - .1)):
        downpipe(acc, px, py, H_BAY - 1.0)
    for u in (0.4, 3.4, 8.4):
        wall_lamp(acc, "x", -D2, -1, u, 6.2)
    for u in (-6.9, 7.6):
        wall_lamp(acc, "y", W2, 1, u, 6.6)
    for u in (-3.0, 3.5, 7.0):
        wall_lamp(acc, "x", D2, 1, u, 6.2)
    # security cameras at two corners
    for (cx, cy, yaw) in ((W2 + .1, -D2 - .1, -45), (-W2 - .1, D2 + .1, 135)):
        rbox(acc, (.25, .1, .1), (cx, cy, 7.4), C("E8ECEE"), .03, 2, rot=(0, 0, yaw))
        rbox(acc, (.06, .06, .2), (cx, cy, 7.55), C(STEEL), .01, 1)
    office(acc, root)
    roof(acc, root)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    # brand: big name board over the office (south face of the north-west wing), the logo medallion on the high bay's
    # south wall, a name board over the dock canopy, the water tower on the roof
    nb, _ = name_board(f"{name}_NameSouth", (0, 0, 0), L=6.2, H=1.5)
    nb.parent = root; nb.location = Vector(((-W2 + OFF_X1) / 2, OFF_Y1 - .2, 9.15))
    md, _ = wall_medallion(f"{name}_Medallion", (0, 0, 0))
    md.parent = root; md.location = Vector((1.4, -D2 - .55, 7.6)); md.scale = (1.55, 1.55, 1.55)
    ne, _ = name_board(f"{name}_NameEast", (0, 0, 0), L=7.4, H=1.4)
    ne.parent = root; ne.location = Vector((W2 + .2, (DOCKS[0] + DOCKS[-1]) / 2, 8.4)); ne.rotation_euler = (0, 0, math.radians(90))
    wt, _ = water_tower(f"{name}_WaterTower", (0, 0, 0))
    wt.parent = root; wt.location = Vector((6.4, 6.6, H_BAY - .4))
    return root


# --------------------------------------------------------------------------------------------- ceiling decorations
PENNANT_COLOURS = (C(NAVY), C(GOLD), "C_F4EBD8")
CORD = "C_6B4A2E"


def pennant_bm(w, h, curl=.03, t=.006):
    """A fabric pennant hanging from its top edge: a triangle with a soft belly (it bulges a little as cloth does),
    a thickness and rounded edges."""
    bm = bmesh.new()
    rows = 4
    front, back = [], []
    for side, store in ((-1, front), (1, back)):
        for i in range(rows + 1):
            f = i / rows
            z = -h * f
            half = w / 2 * (1 - f)
            row = []
            for j in range(3):
                u = (-1 + j) * half
                bulge = curl * math.sin(math.pi * (1 - f) * .9) * (1 - abs(u) / max(half, 1e-4) * .6) if half > 1e-4 else 0
                row.append(bm.verts.new((u, side * t / 2 + bulge, z)))
            store.append(row)
    for store, flip in ((front, False), (back, True)):
        for i in range(rows):
            a, b = store[i], store[i + 1]
            for j in range(2):
                q = [a[j], a[j + 1], b[j + 1], b[j]]
                if flip: q.reverse()
                try: bm.faces.new(q)
                except ValueError: pass
    # rims (outer edges) joining the two sides
    for i in range(rows):
        for j in (0, 2):
            q = [front[i][j], front[i + 1][j], back[i + 1][j], back[i][j]]
            if j == 2: q.reverse()
            try: bm.faces.new(q)
            except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv_box(bm)
    return bm


def garland(name="MarketBunting", L=4.0, sag=.32, loc=(0, 0, 0), n=8):
    """One span of the market's party bunting (the game repeats it along each line): a cord that sags between two
    ceiling hooks, n fabric pennants in the market's two colours and cream, each folded over the cord with a hem,
    and a warm string-light bulb between the pennants. Origin = the left hook; the span runs along +X."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    def cz(x):
        f = (x / L) * 2 - 1
        return -sag * (1 - f * f)
    pts = [(L * k / 24, 0, cz(L * k / 24)) for k in range(25)]
    tube(acc, pts, .012, CORD, seg=6, smooth_n=1)
    for hx in (0, L):
        lathe(acc, [(.045, -.012), (.06, 0), (.045, .012), (.03, 0)], (hx, 0, .04), C(STEEL), 12, 1, rot=(90, 0, 0), cap_top=False, cap_bottom=False)
        lathe(acc, [(0, 0), (.07, 0), (.07, .03), (0, .03)], (hx, 0, .09), C(STEEL), 12, 0)
        tube(acc, [(hx, 0, .09), (hx, 0, .02)], .012, C(STEEL), seg=6)
    step = L / n
    for k in range(n):
        x = step * (k + .5)
        z = cz(x)
        slope = math.degrees(math.atan2(cz(x + .05) - cz(x - .05), .1))
        bm = pennant_bm(.36, .46)
        place(bm, (x, 0, z - .015), (0, -slope, 0))
        acc.add(bm, PENNANT_COLOURS[k % 3], "Body")
        rbox(acc, (.37, .03, .04), (x, 0, z), PENNANT_COLOURS[k % 3], .012, 2, rot=(0, -slope, 0))   # hem over the cord
        # a bulb between this pennant and the next
        bx = step * (k + 1)
        if k < n - 1:
            bz = cz(bx)
            rbox(acc, (.03, .03, .05), (bx, 0, bz - .035), C(DASH), .008, 1)
            lathe(acc, [(0, 0), (.035, .01), (.045, .05), (.03, .09), (0, .1)], (bx, 0, bz - .16), BULB, 10, 2)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root


def pendant(name="MarketPendant", drop=1.1, loc=(0, 0, 0)):
    """A supermarket pendant lamp: ceiling rose, steel cable with a grip, a big dome shade (navy outside with a gold
    rim, white inside) and a glowing diffuser. Origin = the ceiling point."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    lathe(acc, [(0, 0), (.13, 0), (.13, -.03), (.09, -.07), (0, -.07)], (0, 0, 0), C(NAVY), 20, 1)
    tube(acc, [(0, 0, -.07), (0, 0, -drop)], .01, C(DASH), seg=6)
    lathe(acc, [(0, 0), (.025, 0), (.025, .1), (0, .1)], (0, 0, -drop - .02), C(GOLD), 10, 0)
    top = -drop - .02
    outer = [(0, top), (.07, top), (.12, top - .04), (.26, top - .2), (.4, top - .42), (.47, top - .56), (.48, top - .6)]
    lathe(acc, outer, (0, 0, 0), C(NAVY), 32, 2, cap_top=False, cap_bottom=False)
    inner = [(.46, top - .6), (.45, top - .56), (.38, top - .43), (.25, top - .22), (.11, top - .06), (0, top - .03)]
    lathe(acc, inner, (0, 0, 0), "C_F7F4EC", 32, 2, cap_top=False, cap_bottom=False)
    lathe(acc, [(.455, top - .6), (.49, top - .6), (.5, top - .62), (.49, top - .65), (.455, top - .65)], (0, 0, 0), C(GOLD), 32, 1, cap_top=False, cap_bottom=False)
    lathe(acc, [(0, top - .5), (.38, top - .5), (.38, top - .52), (0, top - .53)], (0, 0, 0), HEAD_L, 28, 0)
    lathe(acc, [(0, top - .2), (.09, top - .24), (.11, top - .34), (.07, top - .44), (0, top - .46)], (0, 0, 0), BULB, 14, 2)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root


# --------------------------------------------------------------------------------------------- previews
def build_dc_v2():
    rk_core.clear("Rede DC v2")
    rk_core.studio((1800, 1100), bg=(.86, .84, .8))
    preview_setup()
    fl = bpy.data.objects.get("RK_Floor")
    if fl:
        fl.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.5, .5, .52, 1)
    dc = dc_building("RedeDC", (0, 0, 0))
    # two fleet trucks at the bays and the yard pieces, for scale
    for yc, reefer in ((DOCKS[1], False), (DOCKS[3], True)):
        r, _ = truck("FleetTruck_" + ("Reefer" if reefer else "Dry"), (0, 0, 0), reefer=reefer)
        r.location = Vector((W2 + 3.6, yc, 0)); r.rotation_euler = (0, 0, math.radians(-90))
    fuel_island("RedeFuelIsland", (W2 + 9.5, -3.5, 0))
    gatehouse("RedeGatehouse", (W2 + 10.0, 6.5, 0))
    return dc


def build_ceiling_preview():
    """The decorations over a mock market floor, seen like the game sees them, plus a close-up."""
    rk_core.clear("Ceiling deco")
    rk_core.studio((1800, 1100), bg=(.86, .84, .8))
    preview_setup()
    acc = Acc("Mock_Floor")
    rbox(acc, (16, 11, .1), (0, 0, .05), C("EFE3CC"), .02, 1)
    for i in range(16):
        rbox(acc, (.02, 11, .005), (-8 + i, 0, .1), C("DCCDB0"), .002, 1)
    for j in range(11):
        rbox(acc, (16, .02, .005), (0, -5.5 + j, .1), C("DCCDB0"), .002, 1)
    for s in (-1, 1):
        rbox(acc, (16, .35, 3.6), (0, s * 5.6, 1.8), C(NAVY), .03, 2)
    rbox(acc, (.35, 11, 3.6), (-8.1, 0, 1.8), C(NAVY), .03, 2)
    rbox(acc, (.35, 11, 3.6), (8.1, 0, 1.8), C(NAVY), .03, 2)
    for k in range(4):
        for j in range(2):
            rbox(acc, (3.2, .8, 1.6), (-5 + k * 3.4, -2.2 + j * 3.8, .9), C("F6F2EA"), .05, 2)
            rbox(acc, (3.24, .84, .08), (-5 + k * 3.4, -2.2 + j * 3.8, 1.72), C(GOLD), .02, 1)
    for o in acc.realize():
        o.name = "Mock_Floor_" + o.name
    for row, y in enumerate((-3.9, -.4, 3.2)):
        for k in range(4):
            garland("MarketBunting", L=4.0, loc=(-8 + k * 4.0, y, 3.55))
    for x in (-5.1, -1.7, 1.7, 5.1):
        for y in (-2.2, 1.6):
            pendant("MarketPendant", 1.05, (x, y + .0, 3.6))
    garland("MarketBunting_Close", L=4.0, loc=(-30, 0, 3.55))
    pendant("MarketPendant_Close", 1.05, (-23.5, .4, 3.6))
