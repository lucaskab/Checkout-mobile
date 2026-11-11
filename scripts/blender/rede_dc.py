"""Rede de supermercados, round 2 (Lucas 05/11): the distribution centre building (the hypermarket's "Armazém central"
was simple and small). (The remade ceiling bunting and pendant lamps were tried in the shop and dropped: Lucas did not
want ceiling decorations at all.)

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
DOCKS = (-1.45, 1.55, 4.55)          # dock door centres on the east wall: the yard's three bays (1, 2, 3)
DOCK_W, DOCK_Z0, DOCK_Z1 = 2.6, .12, 3.7   # ground-level roller doors (the loaders walk through them)
APRON_X, APRON_TOP = 1.45, .03       # asphalt apron from the dock wall out to the yard's asphalt (x 2.7 .. 4.2 world)
BAY_LINES = (-2.95, .05, 3.05, 6.05) # the yard's bay lines (between the docks): one guide post each

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
# v2 (Lucas 06/11: "tem alguns pilares que não tá fazendo muito sentido, as portas também não estão muito alinhadas com
# o chão e com as vagas 1, 2 e 3 ... 4 portas para 3 vagas"): three docks only, one on each of the yard's bays; the doors
# come down to the ground (the loaders walk in and out of them), the wall between them stays wall (the old foam
# shelters of neighbouring docks met and read as double pillars), one guide post on each bay line, an asphalt apron
# from the wall to the yard's own asphalt. Each roller door is its own mesh (DockDoor<i>) so the game rolls it up.
def dock(acc, root, i, yc):
    """One loading dock on the east wall: steel frame, sectional roller door (own mesh) with a window row, a dark
    inside behind it, a rubber hood over it, yellow / black guards on the jambs, a traffic light, a threshold strip."""
    x = W2
    a, b = yc - DOCK_W / 2, yc + DOCK_W / 2
    # the dark loading bay behind the door (seen when it rolls up)
    rbox(acc, (2.2, DOCK_W + .1, DOCK_Z1 - DOCK_Z0 + .3), (x - 1.4, yc, (DOCK_Z0 + DOCK_Z1) / 2 + .1), C("3A3F47"), .01, 1)
    rbox(acc, (2.2, DOCK_W + .1, .04), (x - 1.4, yc, DOCK_Z0 + .01), C("8C8A84"), .01, 1)
    for k in range(3):   # pallets of boxes waiting inside
        px, pz = x - 1.6 - (k % 2) * .5, DOCK_Z0 + .05
        py = a + .55 + k * (DOCK_W - 1.1) / 2
        rbox(acc, (.9, .9, .12), (px, py, pz + .06), C("B88A55"), .01, 1)
        rbox(acc, (.8, .8, .7 - .15 * (k % 2)), (px, py, pz + .12 + (.7 - .15 * (k % 2)) / 2), C("C9A06A"), .02, 2)
    # steel frame round the opening, yellow / black guards on the jambs
    for yy in (a - .07, b + .07):
        rbox(acc, (.16, .14, DOCK_Z1 - DOCK_Z0 + .1), (x + .03, yy, (DOCK_Z0 + DOCK_Z1) / 2 + .05), C(STEEL), .02, 1)
        for k in range(6):
            rbox(acc, (.03, .15, .16), (x + .12, yy, DOCK_Z0 + .12 + k * .2), (YELLOW if k % 2 == 0 else BLACK), .005, 1)
    rbox(acc, (.16, DOCK_W + .28, .14), (x + .03, yc, DOCK_Z1 + .07), C(STEEL), .02, 1)
    # the roller door (closed; the game rolls it up): panels, a window row, a handle
    g = f"DockDoor{i}"
    rbox(acc, (.06, DOCK_W, DOCK_Z1 - DOCK_Z0), (x - .12, yc, (DOCK_Z0 + DOCK_Z1) / 2), DOOR, .01, 1, grp=g)
    n = 7
    for k in range(1, n):
        z = DOCK_Z0 + k * (DOCK_Z1 - DOCK_Z0) / n
        rbox(acc, (.03, DOCK_W - .04, .035), (x - .08, yc, z), DOOR_D, .008, 1, grp=g)
    zw = DOCK_Z0 + 4.5 * (DOCK_Z1 - DOCK_Z0) / n
    for k in range(4):
        rpanel(acc, .42, .2, .02, (x - .075, a + .4 + k * (DOCK_W - .8) / 3, zw), WIN, .04, rot=(0, 0, 90), grp=g)
    rbox(acc, (.05, .3, .05), (x - .07, yc, DOCK_Z0 + .9), C(STEEL), .01, 1, grp=g)
    rbox(acc, (.06, DOCK_W, .08), (x - .1, yc, DOCK_Z0 + .04), RUBBER, .01, 1, grp=g)   # bottom seal
    # rubber hood over the door
    rbox(acc, (.45, DOCK_W + .3, .5), (x + .24, yc, DOCK_Z1 + .38), RUBBER_D, .06, 3)
    for k in range(6):
        rbox(acc, (.03, .02, .38), (x + .47, a + .15 + k * (DOCK_W - .3) / 5, DOCK_Z1 + .3), RUBBER, .005, 1)
    # traffic light on the wall beside the door, a downlight over it
    tl = a - .42
    rbox(acc, (.1, .22, .5), (x + .05, tl, 2.0), BLACK, .03, 2)
    lathe(acc, [(0, 0), (.06, 0), (.06, .02), (0, .02)], (x + .1, tl, 2.12), RED_L, 12, 0, rot=(0, 90, 0))
    lathe(acc, [(0, 0), (.06, 0), (.06, .02), (0, .02)], (x + .1, tl, 1.88), "E_5BE35B", 12, 0, rot=(0, 90, 0))
    # threshold strip on the apron in front of the door
    for k in range(9):
        rbox(acc, (.3, .28, .012), (x + .25, a + .15 + k * (DOCK_W - .3) / 8, APRON_TOP + .006), (YELLOW if k % 2 == 0 else BLACK), .004, 1)


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
        lathe(acc, [(.32, 0), (.36, 0), (.36, .06), (.32, .06)], (x0 + 1.75 + k * .9, y1 - 1.4, H + .4), DASH, 20, 0, cap_top=False, cap_bottom=False)
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
        rbox(acc, (2.24, 1.44, .08), (hx, hy, deck + .14), DASH, .02, 1)
        for s in (-1, 1):
            lathe(acc, [(.38, 0), (.43, 0), (.43, .08), (.38, .08)], (hx + s * .52, hy, deck + 1.1), DASH, 22, 0, cap_top=False, cap_bottom=False)
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
    east_holes = [(yc - DOCK_W / 2 - .02, yc + DOCK_W / 2 + .02, DOCK_Z0 - .05, DOCK_Z1 + .05) for yc in DOCKS] + [personnel]
    # walls: east (docks), north, west wing, south of A, the step above the office (south face of B, east face of
    # the office's top)
    clad_wall(acc, "y", W2, 1, -D2, D2, H_BAY, east_holes)
    clad_wall(acc, "x", D2, 1, -W2, W2, H_BAY)
    clad_wall(acc, "y", -W2, -1, OFF_Y1, D2, H_BAY, [(3.0, 4.0, 4.4, 6.6)])
    exit_door = (5.6, 6.8, 0, 2.4)
    clad_wall(acc, "x", -D2, -1, OFF_X1, W2, H_BAY, [exit_door])
    clad_wall(acc, "x", OFF_Y1, -1, -W2, OFF_X1, H_BAY, z0=H_OFFICE - .2, band=False)
    clad_wall(acc, "y", OFF_X1, -1, -D2, OFF_Y1, H_BAY, z0=H_OFFICE - .2, band=False)
    for i, yc in enumerate(DOCKS):
        dock(acc, root, i, yc)
    # the asphalt apron in front of the docks (down to the yard's asphalt) and a guide post on each bay line
    ay0, ay1 = BAY_LINES[0] - .4, BAY_LINES[-1] + .4
    rbox(acc, (APRON_X, ay1 - ay0, .06), (W2 + APRON_X / 2, (ay0 + ay1) / 2, APRON_TOP - .03), C("484B4E"), .01, 1)
    for yy in BAY_LINES:
        lathe(acc, [(0, 0), (.09, 0), (.09, 1.05), (.07, 1.12), (0, 1.14)], (W2 + .75, yy, APRON_TOP), YELLOW, 12, 1)
        lathe(acc, [(.092, .7), (.092, .85)], (W2 + .75, yy, APRON_TOP), BLACK, 12, 0, cap_top=False, cap_bottom=False)
    # dock canopy over the three bays
    cy0, cy1 = BAY_LINES[0] - .3, BAY_LINES[-1] + .3
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
    # a ribbon of mezzanine windows on the south wall (offices and the staff room over the floor)
    rx0, rx1, rz0, rz1 = 3.0, 8.4, 4.3, 5.5
    rbox(acc, (rx1 - rx0 + .2, .2, rz1 - rz0 + .2), ((rx0 + rx1) / 2, -D2 - .08, (rz0 + rz1) / 2), C(NAVY), .03, 2)
    rbox(acc, (rx1 - rx0, .2, rz1 - rz0), ((rx0 + rx1) / 2, -D2 - .12, (rz0 + rz1) / 2), WIN, .01, 1)
    for k in range(7):
        xx = rx0 + k * (rx1 - rx0) / 6
        rbox(acc, (.06, .1, rz1 - rz0), (xx, -D2 - .23, (rz0 + rz1) / 2), C(STEEL), .01, 1)
    rbox(acc, (rx1 - rx0, .1, .05), ((rx0 + rx1) / 2, -D2 - .23, rz0 + .55), C(STEEL), .01, 1)
    rbox(acc, (rx1 - rx0 + .3, .35, .06), ((rx0 + rx1) / 2, -D2 - .2, rz0 - .12), C(GOLD), .02, 1)   # sill
    for k in range(3):
        xx = rx0 + (k + .5) * (rx1 - rx0) / 3
        rbox(acc, (.12, .02, .8), (xx, -D2 - .23, rz0 + .65), WIN_HI, .005, 1, rot=(0, 25, 0))
    # emergency exit (south wall): door + a lit green plate over it
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
    nb, _ = name_board(f"{name}_NameBoardSouth", (0, 0, 0), L=6.2, H=1.5)
    nb.parent = root; nb.location = Vector(((-W2 + OFF_X1) / 2, OFF_Y1 - .2, 9.15))
    md, _ = wall_medallion(f"{name}_Medallion", (0, 0, 0))
    md.parent = root; md.location = Vector((1.4, -D2 - .55, 7.6)); md.scale = (1.55, 1.55, 1.55)
    ne, _ = name_board(f"{name}_NameBoardEast", (0, 0, 0), L=7.4, H=1.4)
    ne.parent = root; ne.location = Vector((W2 + .2, (DOCKS[0] + DOCKS[-1]) / 2, 8.4)); ne.rotation_euler = (0, 0, math.radians(90))
    wt, _ = water_tower(f"{name}_WaterTower", (0, 0, 0))
    wt.parent = root; wt.location = Vector((6.4, 6.6, H_BAY - .4))
    return root


# --------------------------------------------------------------------------------------------- previews
def docks_preview():
    """Studio stills of the dock side (v2 docks): the three docks on the bays, two trucks backed onto them."""
    dc = build_dc_v2()
    # the yard's bay lines and numbers' places, painted on the studio floor for reference
    acc = Acc("BayRef")
    for yy in BAY_LINES:
        rbox(acc, (6.0, .12, .01), (W2 + APRON_X + 3.0, yy, .006), "C_EDE6D3", .005, 1)
    rbox(acc, (8.0, BAY_LINES[-1] - BAY_LINES[0] + 2, .01), (W2 + APRON_X + 4.0, (BAY_LINES[0] + BAY_LINES[-1]) / 2, .002), "C_43474A", .005, 1)
    acc.realize()
    out = []
    for nm, d, ds, lens, tgt in (("dc_docks_v2", (1.0, -.55, .5), 22, 38, (W2 + 1.0, 1.5, 2.2)),
                                 ("dc_docks_v2_front", (1.0, 0.0, .28), 17, 40, (W2, 1.5, 2.0)),
                                 ("dc_docks_v2_iso", (.8, -.9, .8), 34, 36, (W2 - 1.0, 0.5, 3.0))):
        out.append(rk_core.shoot(nm, Vector(tgt), d, ds, lens, (1600, 1000)))
    return out


def build_dc_v2():
    rk_core.clear("Rede DC v2")
    rk_core.studio((1800, 1100), bg=(.86, .84, .8))
    preview_setup()
    fl = bpy.data.objects.get("RK_Floor")
    if fl:
        fl.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.5, .5, .52, 1)
    dc = dc_building("RedeDC", (0, 0, 0))
    # two fleet trucks at the bays and the yard pieces, for scale
    for yc, reefer in ((DOCKS[0], False), (DOCKS[2], True)):
        r, _ = truck("FleetTruck_" + ("Reefer" if reefer else "Dry"), (0, 0, 0), reefer=reefer)
        # backed onto the bay at the game's fleet scale, its tail 0.8 m off the wall
        r.location = Vector((W2 + .8 + 2.4, yc, 0)); r.rotation_euler = (0, 0, math.radians(90)); r.scale = (.75, .75, .75)
    fuel_island("RedeFuelIsland", (W2 + 13.0, -4.5, 0))
    gatehouse("RedeGatehouse", (W2 + 10.0, 6.5, 0))
    return dc
