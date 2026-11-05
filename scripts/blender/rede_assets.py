"""Rede de supermercados — the chain's own assets (brand + distribution centre), round 1 (preview only).

Run inside Blender (Blender MCP):
    REPO = "/Users/lucas-furini/repos/checkout"
    ns = {"__name__": "kit", "REPO": REPO}
    exec(open(REPO + "/scripts/blender/fixture_tiers.py").read(), ns)      # the Realistic Kit + palette
    exec(open(REPO + "/scripts/blender/rede_assets.py").read(), ns)
    ns["build_all"]()

Modelling space is rk_core's: metres, Z up, the FRONT faces -Y (a truck drives towards -Y).
Material contract (CheckoutMarketPaint / KitRemap):
  * C_1D2B4F / C_2E4A7D navy  -> repainted with the market's main colour ("Cores do mercado")
  * C_D3A53D gold trims        -> repainted with the accent colour
  * everything else (white panels, steel, rubber, glass, E_ lights) keeps its colour.
No written words: the chain's name and logo are drawn by the game on the blank white plates; the plates carry
empties named Brand_* (+X of the empty = the plate's right, +Z = up, -Y = the side you read from).
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

QA_REDE = os.path.join(REPO, "unity", "CheckoutSimulator", "Temp", "qa", "rede")
RUBBER, RUBBER_D, TREAD = "C_2B2F36", "C_1E2126", "C_33383F"
PLASTIC, BUMPER = "C_3A4048", "C_4A525C"
ALU = "C_B8C2C8"
PLATE = "C_FBF8F1"          # blank brand plates (never repainted)
CAB_WHITE = "C_F7F4EC"
REEFER_WHITE = "C_EEF1F2"
RED_L, AMBER_L, HEAD_L, COOL_L = "E_FF4B3E", "E_FFB347", "E_FFF6DC", "E_CFEFFF"
SEAT, DASH = "C_3B4250", "C_2A2F38"
WIN, WIN_HI = "C_7FA3B8", "C_D4E8F1"     # stylised tinted glass (opaque, like the game's vehicles) + highlight


# --------------------------------------------------------------------------------------------- helpers
def prism_bm(profile, width, r=.04, seg=3):
    """A side profile [(y, z), ...] extruded across X (centred), edges rounded by r."""
    bm = bmesh.new()
    left = [bm.verts.new((-width / 2, y, z)) for y, z in profile]
    right = [bm.verts.new((width / 2, y, z)) for y, z in profile]
    bm.faces.new(left)
    bm.faces.new(list(reversed(right)))
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((left[i], left[j], right[j], right[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if r > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r, segments=seg, profile=.5, affect="EDGES", clamp_overlap=True)
    uv_box(bm)
    return bm


def prism(acc, profile, width, key, loc=(0, 0, 0), r=.04, seg=3, rot=(0, 0, 0), grp="Body"):
    bm = prism_bm(profile, width, r, seg)
    place(bm, loc, rot)
    acc.add(bm, key, grp)


def rpanel(acc, w, h, t, loc, key, r=.04, rot=(0, 0, 0), grp="Body", seg=5):
    bm, _ = panel_bm(w, h, t, r, seg)
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = ((l.vert.co.x + w / 2) / w, (l.vert.co.z + h / 2) / h)
    place(bm, loc, rot)
    acc.add(bm, key, grp)


def rframe(acc, w, h, t, border, loc, key, r=.04, rot=(0, 0, 0), grp="Body"):
    bm = frame_bm(w, h, t, r, border)
    place(bm, loc, rot)
    acc.add(bm, key, grp)


def anchor(name, loc, rot=(0, 0, 0), size=.3, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = size
    e.location = Vector(loc)
    e.rotation_euler = tuple(math.radians(a) for a in rot)
    bpy.context.scene.collection.objects.link(e)
    if parent:
        e.parent = parent
    return e


def cyl_x(acc, r, length, loc, key, seg=20, grp="Body"):
    """Closed cylinder along X."""
    lathe(acc, [(0, -length / 2), (r, -length / 2), (r, length / 2), (0, length / 2)], loc, key, seg, 0, rot=(0, 90, 0), grp=grp)


def cyl_y(acc, r, length, loc, key, seg=20, grp="Body", round_ends=0.0):
    e = round_ends
    prof = [(0, -length / 2), (r - e, -length / 2), (r, -length / 2 + e), (r, length / 2 - e), (r - e, length / 2), (0, length / 2)]
    lathe(acc, prof, loc, key, seg, 2 if e else 0, rot=(90, 0, 0), grp=grp)


# --------------------------------------------------------------------------------------------- wheels
def wheel(acc, loc, side, dual=False):
    """Chunky tyre with tread blocks, a steel rim with hub, lug nuts and (dual) a second tyre inboard."""
    x, y, z = loc
    R, W = .48, .30
    tires = [x] if not dual else [x, x - side * .31]
    for tx in tires:
        prof = [(.27, -W / 2), (.40, -W / 2), (.455, -W / 2 + .03), (R - .01, -W / 2 + .07), (R, 0), (R - .01, W / 2 - .07), (.455, W / 2 - .03), (.40, W / 2), (.27, W / 2)]
        lathe(acc, prof, (tx, y, z), RUBBER, 28, 2, rot=(0, 90, 0))
        # tread blocks around the crown (alternating offset, like a real truck tyre)
        for k in range(22):
            a = 2 * math.pi * k / 22
            off = .055 if k % 2 else -.055
            cy, cz = y + math.cos(a) * (R + .004), z + math.sin(a) * (R + .004)
            rbox(acc, (.11, .075, .03), (tx + off, cy, cz), TREAD, .01, 1, rot=(math.degrees(a) - 90, 0, 0))
    # rim on the outer face
    ox = x + side * (W / 2 - .02)
    rim = [(0, 0), (.08, 0), (.10, .015), (.20, .02), (.26, .045), (.285, .03), (.29, 0), (.285, -.04)]
    lathe(acc, rim, (ox, y, z), C(STEEL), 28, 2, rot=(0, side * 90, 0))
    # hub cap + lug nuts
    lathe(acc, [(0, .045), (.075, .045), (.085, .02), (.085, 0)], (ox, y, z), C(CHROME), 20, 1, rot=(0, side * 90, 0))
    for k in range(8):
        a = 2 * math.pi * k / 8
        lathe(acc, [(0, .045), (.016, .045), (.016, 0)], (ox + side * .005, y + math.cos(a) * .12, z + math.sin(a) * .12), C(CHROME), 6, 0, rot=(0, side * 90, 0))
    # vent holes in the rim, dark
    for k in range(6):
        a = 2 * math.pi * k / 6 + .26
        rbox(acc, (.012, .07, .045), (ox + side * .022, y + math.cos(a) * .19, z + math.sin(a) * .19), DASH, .015, 2, rot=(math.degrees(a), 0, 0))


def arch(acc, x, y, z, side, r=.58, key=RUBBER_D):
    """Black wheel-arch lip on the body side (semi-circle) + a dark inner liner disc behind the tyre."""
    pts = [(x, y + math.cos(a) * r, z + math.sin(a) * r) for a in [math.pi * i / 16 for i in range(17)]]
    tube(acc, pts, .045, key, seg=8)
    lathe(acc, [(0, 0), (r - .02, 0), (r - .02, .02), (0, .02)], (x - side * .16, y, z), DASH, 24, 0, rot=(0, 90, 0))


# --------------------------------------------------------------------------------------------- the cab
CAB_FRONT, CAB_BACK, CAB_W = -3.05, -1.42, 2.26
CAB_PROFILE = [(-1.42, .72), (-3.00, .72), (-3.08, 1.05), (-3.06, 1.58), (-2.74, 2.40), (-2.58, 2.53), (-1.52, 2.57), (-1.42, 2.48)]


def cab(acc, root, reefer=False):
    W = CAB_W
    # body: white upper, navy lower skirt with a gold pinstripe (the stripe is the accent colour)
    prism(acc, CAB_PROFILE, W, CAB_WHITE, r=.07, seg=4)
    skirt = [(-1.405, .70), (-3.02, .70), (-3.10, 1.05), (-3.095, 1.16), (-1.405, 1.16)]
    prism(acc, skirt, W + .03, C(NAVY), r=.05, seg=3)
    for s in (-1, 1):
        rbox(acc, (.012, 1.58, .035), (s * (W / 2 + .018), -2.22, 1.205), C(GOLD), .006, 1)
    rbox(acc, (W - .2, .012, .035), (0, -3.112, 1.205), C(GOLD), .006, 1)
    # windscreen (sloped glass) with black rubber frame, wipers and a sun visor
    ang = math.degrees(math.atan2(.32, .82))
    mid = Vector((0, (-3.06 - 2.74) / 2, (1.58 + 2.40) / 2))
    nrm = Vector((0, -.82, .32)).normalized()
    rframe(acc, 1.98, .86, .03, .06, tuple(mid + nrm * .012), RUBBER_D, .09, rot=(-ang, 0, 0))
    rpanel(acc, 1.88, .76, .012, tuple(mid + nrm * .016), WIN, .07, rot=(-ang, 0, 0))
    for dx, ww in ((-.35, .16), (-.08, .07)):
        rpanel(acc, ww, .70, .006, tuple(mid + nrm * .024 + Vector((dx, 0, 0))), WIN_HI, .02, rot=(-ang, 0, -24))
    for s in (-1, 1):
        base = mid + nrm * .03 + Vector((s * .42, 0, 0)) - Vector((0, -.32, -.82)).normalized() * -.36
        tube(acc, [tuple(base), tuple(base + Vector((-s * .55, .06, .16)))], .011, DASH, seg=6)
    rbox(acc, (1.9, .22, .05), (0, -2.66, 2.52), C(NAVY), .02, 2, rot=(12, 0, 0))
    # grille, headlights, indicators, bumper, plate
    rpanel(acc, 1.12, .40, .04, (0, -3.095, 1.36), DASH, .06)
    for k in range(5):
        rbox(acc, (1.0, .02, .025), (0, -3.12, 1.21 + k * .075), C(CHROME), .008, 1)
    rframe(acc, 1.16, .44, .03, .035, (0, -3.10, 1.36), C(CHROME), .07)
    for s in (-1, 1):
        rpanel(acc, .34, .22, .035, (s * .80, -3.09, 1.38), DASH, .07)
        rpanel(acc, .28, .16, .02, (s * .80, -3.11, 1.385), HEAD_L, .06)
        lathe(acc, [(0, 0), (.05, 0), (.05, .02), (0, .03)], (s * .80, -3.12, 1.385), C(CHROME), 14, 1, rot=(90, 0, 0))
        rpanel(acc, .14, .07, .02, (s * .80, -3.10, 1.215), AMBER_L, .03)
        rpanel(acc, .08, .05, .02, (s * 1.115, -2.98, 1.05), AMBER_L, .02, rot=(0, 0, s * 70))
    rbox(acc, (W + .08, .26, .26), (0, -3.15, .86), BUMPER, .07, 3)
    rbox(acc, (W - .3, .04, .05), (0, -3.285, .93), PLASTIC, .02, 2)
    for s in (-1, 1):
        rpanel(acc, .14, .07, .02, (s * .86, -3.285, .80), C("E8EEF2"), .03)           # fog lights
    rpanel(acc, .48, .14, .015, (0, -3.288, .83), PLATE, .02)                           # blank plate
    rframe(acc, .52, .18, .012, .02, (0, -3.29, .83), C(CHROME), .03)
    # doors: seams, windows, handles, mirrors, steps
    for s in (-1, 1):
        x = s * (W / 2 + .004)
        for yy in (-2.62, -1.62):
            rbox(acc, (.012, .014, 1.45), (x, yy, 1.47), DASH, .004, 1)
        rbox(acc, (.012, 1.0, .014), (x, -2.12, 2.20), DASH, .004, 1)
        rbox(acc, (.012, 1.0, .014), (x, -2.12, .76), DASH, .004, 1)
        rframe(acc, .92, .58, .03, .05, (x + s * .006, -2.10, 1.86), RUBBER_D, .07, rot=(0, 0, 90))
        rpanel(acc, .84, .50, .012, (x + s * .012, -2.10, 1.86), WIN, .06, rot=(0, 0, 90))
        rpanel(acc, .10, .46, .006, (x + s * .02, -2.22, 1.86), WIN_HI, .02, rot=(0, -s * 22, 90))
        rbox(acc, (.03, .17, .04), (x + s * .02, -1.78, 1.58), C(CHROME), .015, 2)
        rbox(acc, (.012, .09, .09), (x + s * .008, -1.66, 1.10), C(CHROME), .02, 2)  # door keyhole cap
        # mirror: two arms from the A pillar + a tall head with glass facing back
        mx = s * (W / 2 + .30)
        tube(acc, [(s * (W / 2), -2.70, 2.15), (mx, -2.62, 2.12)], .02, DASH, seg=8)
        tube(acc, [(s * (W / 2), -2.80, 1.62), (mx, -2.62, 1.70)], .02, DASH, seg=8)
        rbox(acc, (.12, .10, .52), (mx, -2.62, 1.90), C(NAVY), .04, 3)
        rpanel(acc, .09, .44, .01, (mx, -2.565, 1.90), C("CFE3EE"), .03)
        # entry steps (two treads) and a grab handle
        for k, zz in enumerate((.50, .26)):
            rbox(acc, (.26, .52, .04), (s * (W / 2 - .02 + k * .02), -2.12, zz), ALU, .015, 2)
            for t in range(4):
                rbox(acc, (.2, .02, .012), (s * (W / 2 - .02 + k * .02), -2.30 + t * .12, zz + .025), C(CHROME), .004, 1)
        tube(acc, [(s * (W / 2 + .03), -1.50, 1.30), (s * (W / 2 + .06), -1.50, 1.62), (s * (W / 2 + .06), -1.50, 2.05), (s * (W / 2 + .03), -1.50, 2.30)], .018, C(CHROME), seg=8, smooth_n=3)
        arch(acc, s * (W / 2 + .03), -2.42, .48, s)
    # roof: air deflector up to the box (navy, follows the paint), clearance lights, horn
    if not reefer:
        defl = [(-1.50, 2.55), (-2.45, 2.55), (-2.20, 2.78), (-1.60, 3.06), (-1.42, 3.06), (-1.42, 2.55)]
        prism(acc, defl, W - .12, C(NAVY), r=.05, seg=3)
        rbox(acc, (W - .1, .03, .03), (0, -1.98, 2.86), C(GOLD), .01, 1, rot=(-38, 0, 0))
    else:
        prism(acc, [(-1.50, 2.55), (-2.30, 2.55), (-2.05, 2.68), (-1.50, 2.70)], W - .3, C(NAVY), r=.04, seg=3)
    for k in (-.5, 0, .5):
        rpanel(acc, .14, .06, .03, (k, -2.47, 2.60), AMBER_L, .025)
    for s in (-1, 1):
        lathe(acc, [(0, 0), (.035, 0), (.05, .22), (0, .22)], (s * .35, -1.80, 2.72 if reefer else 3.07), C(CHROME), 12, 1, rot=(90, 0, 0))
    # small door logo plates (the game prints the logo)
    for s in (-1, 1):
        rpanel(acc, .30, .30, .01, (s * (W / 2 + .012), -2.12, 1.52), PLATE, .15, rot=(0, 0, 90))
        anchor(f"Brand_Logo_Door{'R' if s > 0 else 'L'}", (s * (W / 2 + .02), -2.12, 1.52), (0, 0, s * 90), .2, root)


# --------------------------------------------------------------------------------------------- chassis
def chassis(acc, reefer=False):
    for s in (-1, 1):
        rbox(acc, (.14, 6.0, .22), (s * .45, -.05, .64), DASH, .03, 2)
    for yy in (-1.0, .2, 1.3, 2.6):
        rbox(acc, (1.05, .10, .12), (0, yy, .64), DASH, .02, 2)
    # axles + differential
    cyl_x(acc, .07, 1.9, (0, -2.42, .48), DASH, 12)
    cyl_x(acc, .09, 1.9, (0, 1.75, .48), DASH, 12)
    lathe(acc, [(0, -.14), (.17, -.12), (.2, 0), (.17, .12), (0, .14)], (0, 1.75, .48), DASH, 16, 2, rot=(90, 0, 0))
    cyl_y(acc, .045, 3.9, (0, -.3, .52), PLASTIC, 10)                                   # drive shaft
    # fuel tank with straps (right), battery box + air tank (left), exhaust
    cyl_y(acc, .21, .95, (.82, -.75, .62), C(CHROME), 22, round_ends=.05)
    for yy in (-1.05, -.45):
        lathe(acc, [(.215, -.03), (.215, .03)], (.82, yy, .62), DASH, 22, 0, rot=(90, 0, 0), cap_top=False, cap_bottom=False)
    lathe(acc, [(0, 0), (.07, 0), (.07, .03), (0, .03)], (.82, -.75, .835), DASH, 12, 0)  # cap
    rbox(acc, (.36, .60, .38), (-.82, -.85, .62), DASH, .04, 3)
    rbox(acc, (.37, .62, .04), (-.82, -.85, .83), ALU, .015, 2)
    cyl_y(acc, .12, .70, (-.78, .05, .60), C(STEEL), 16, round_ends=.06)
    tube(acc, [(-.55, -1.3, .55), (-.75, -1.0, .45), (-.95, .4, .45), (-1.05, .62, .45)], .05, C(STEEL), seg=10, smooth_n=3)
    lathe(acc, [(.055, 0), (.065, 0), (.065, .15), (.055, .15)], (-1.05, .7, .45), C(CHROME), 12, 0, rot=(90, 0, 0), cap_top=False, cap_bottom=False)
    # side under-run guards between the axles
    for s in (-1, 1):
        for zz in (.42, .62):
            rbox(acc, (.05, 2.0, .07), (s * 1.12, .05, zz), ALU, .02, 2)
        for yy in (-.85, .05, .95):
            rbox(acc, (.06, .06, .34), (s * 1.10, yy, .62), DASH, .015, 1)
    # rear wheels' fenders + mud flaps
    for s in (-1, 1):
        rbox(acc, (.72, 1.25, .045), (s * .98, 1.75, 1.0), RUBBER_D, .02, 2)
        rpanel(acc, .62, .45, .02, (s * .98, 2.42, .55), RUBBER, .04)
        rbox(acc, (.5, .01, .04), (s * .98, 2.405, .72), C(CHROME), .005, 1)


# --------------------------------------------------------------------------------------------- the box
BOX_Y0, BOX_Y1, BOX_Z0, BOX_Z1, BOX_W = -1.32, 3.02, 1.06, 3.10, 2.38


def box(acc, root, reefer=False):
    L = BOX_Y1 - BOX_Y0
    cy, cz, H = (BOX_Y0 + BOX_Y1) / 2, (BOX_Z0 + BOX_Z1) / 2, BOX_Z1 - BOX_Z0
    wall = REEFER_WHITE if reefer else C(NAVY)
    rbox(acc, (BOX_W + .04, L + .04, .12), (0, cy, BOX_Z0 - .03), DASH, .025, 2)     # floor sill
    rbox(acc, (BOX_W, L, H), (0, cy, cz), wall, .07 if reefer else .05, 3)
    # aluminium corner posts and rails
    for sx in (-1, 1):
        for yy in (BOX_Y0 + .03, BOX_Y1 - .03):
            rbox(acc, (.07, .07, H + .02), (sx * (BOX_W / 2 - .02), yy, cz), ALU, .025, 2)
        for zz in (BOX_Z0 + .03, BOX_Z1 - .03):
            rbox(acc, (.06, L, .07), (sx * (BOX_W / 2 - .01), cy, zz), ALU, .02, 2)
    for yy in (BOX_Y0 + .03, BOX_Y1 - .03):
        rbox(acc, (BOX_W, .06, .07), (0, yy, BOX_Z1 - .03), ALU, .02, 2)
    # roof ribs
    for k in range(6):
        rbox(acc, (BOX_W - .1, .035, .02), (0, BOX_Y0 + .4 + k * (L - .8) / 5, BOX_Z1 + .005), ALU, .008, 1)
    if reefer:
        # insulated panels: navy bottom band (paint), gold line, smooth white sides with rivet seams
        for sx in (-1, 1):
            rbox(acc, (.03, L - .1, .42), (sx * (BOX_W / 2 + .004), cy, BOX_Z0 + .27), C(NAVY), .015, 2)
            rbox(acc, (.03, L - .1, .04), (sx * (BOX_W / 2 + .006), cy, BOX_Z0 + .52), C(GOLD), .01, 1)
            for k in range(1, 7):
                rbox(acc, (.014, .02, H - .55), (sx * (BOX_W / 2 + .002), BOX_Y0 + k * L / 7, cz + .2), C("D7DDE0"), .005, 1)
    else:
        for sx in (-1, 1):
            for k in range(1, 9):
                rbox(acc, (.016, .03, H - .16), (sx * (BOX_W / 2 + .002), BOX_Y0 + k * L / 9, cz), C(BLUE), .006, 1)
            rbox(acc, (.03, L - .1, .11), (sx * (BOX_W / 2 + .006), cy, BOX_Z0 + .30), C(GOLD), .015, 2)
            rbox(acc, (.03, L - .1, .035), (sx * (BOX_W / 2 + .006), cy, BOX_Z1 - .20), C(GOLD), .01, 1)
    # brand plates on both sides (white, gold frame) — the game draws logo + name there
    pw, ph = 3.05, 1.18
    for s in (-1, 1):
        x = s * (BOX_W / 2 + .012)
        rpanel(acc, pw, ph, .016, (x, cy + .05, cz + .12), PLATE, .12, rot=(0, 0, 90))
        rframe(acc, pw + .1, ph + .1, .02, .05, (x + s * .004, cy + .05, cz + .12), C(GOLD), .16, rot=(0, 0, 90))
        side = "R" if s > 0 else "L"
        # read from outside: the plate's "right" runs towards the cab on the right side, towards the back on the left
        # logo at the reader's left end of the plate, the name to its right (the reader's right is +Y on the right
        # side of the truck and -Y on the left side)
        anchor(f"Brand_Logo_{side}", (x + s * .01, cy + .05 + s * (-pw / 2 + .62), cz + .12), (0, 0, s * 90), .35, root)
        anchor(f"Brand_Name_{side}", (x + s * .01, cy + .05 + s * .42, cz + .12), (0, 0, s * 90), .35, root)
        # side marker lights along the bottom rail
        for k in range(4):
            rpanel(acc, .07, .04, .02, (s * (BOX_W / 2 + .03), BOX_Y0 + .5 + k * (L - 1) / 3, BOX_Z0 + .06), AMBER_L, .015, rot=(0, 0, 90))
    # rear: frame, doors, lights, bumper
    ry = BOX_Y1 + .01
    rframe(acc, BOX_W - .02, H - .02, .05, .09, (0, ry, cz), ALU, .06)
    if reefer:
        for s in (-1, 1):
            rpanel(acc, BOX_W / 2 - .12, H - .2, .04, (s * (BOX_W / 4 - .02), ry + .02, cz), REEFER_WHITE, .04)
            for xx in (s * .28, s * .85):
                tube(acc, [(xx, ry + .07, BOX_Z0 + .1), (xx, ry + .07, BOX_Z1 - .1)], .022, C(CHROME), seg=8)
                rbox(acc, (.07, .06, .1), (xx, ry + .07, cz - .1), C(STEEL), .02, 2)
                rbox(acc, (.05, .2, .04), (xx + s * .07, ry + .1, cz - .1), C(STEEL), .015, 2)
            for zz in (BOX_Z0 + .35, cz, BOX_Z1 - .35):
                rbox(acc, (.12, .06, .07), (s * (BOX_W / 2 - .08), ry + .05, zz), C(STEEL), .02, 2)
            rbox(acc, (BOX_W / 2 - .14, .03, .3), (s * (BOX_W / 4 - .02), ry + .045, BOX_Z0 + .28), C(NAVY), .02, 2)
        rbox(acc, (.03, .04, H - .2), (0, ry + .045, cz), RUBBER_D, .01, 1)
    else:
        n = 10
        for k in range(n):
            zz = BOX_Z0 + .12 + (H - .24) * (k + .5) / n
            rbox(acc, (BOX_W - .2, .03, (H - .24) / n - .025), (0, ry + .02, zz), C("DCE3E8"), .012, 2)
        rbox(acc, (BOX_W - .2, .05, .08), (0, ry + .04, BOX_Z0 + .16), C(STEEL), .02, 2)
        rbox(acc, (.24, .06, .06), (0, ry + .07, BOX_Z0 + .22), C(CHROME), .02, 2)
        rbox(acc, (BOX_W - .2, .04, .05), (0, ry + .035, BOX_Z0 + .32), C(GOLD), .015, 1)
    rpanel(acc, .55, .55, .01, (0, ry + .075, BOX_Z1 - .5), PLATE, .27)            # round-ish rear logo plate
    anchor("Brand_Logo_Back", (0, ry + .085, BOX_Z1 - .5), (0, 0, 180), .3, root)
    for s in (-1, 1):
        rpanel(acc, .22, .30, .04, (s * (BOX_W / 2 - .2), ry + .03, BOX_Z0 - .22), DASH, .04)
        rpanel(acc, .16, .10, .02, (s * (BOX_W / 2 - .2), ry + .055, BOX_Z0 - .15), RED_L, .03)
        rpanel(acc, .16, .07, .02, (s * (BOX_W / 2 - .2), ry + .055, BOX_Z0 - .26), AMBER_L, .025)
        rpanel(acc, .16, .05, .02, (s * (BOX_W / 2 - .2), ry + .055, BOX_Z0 - .335), C("F2F4F5"), .02)
        rpanel(acc, .06, .03, .015, (s * (BOX_W / 2 - .05), ry + .02, BOX_Z1 - .06), RED_L, .012)
    rbox(acc, (BOX_W - .1, .12, .14), (0, ry + .05, .52), C(STEEL), .03, 2)          # under-ride bar
    for s in (-1, 1):
        rbox(acc, (.08, .08, .5), (s * .7, ry - .05, .78), DASH, .02, 1)
        rbox(acc, (.18, .06, .02), (s * .7, ry + .1, .62), RED_L, .01, 1)            # reflectors
    rbox(acc, (.6, .3, .03), (0, ry + .02, .74), ALU, .015, 2)                       # step
    if reefer:
        reefer_unit(acc)


def reefer_unit(acc):
    """Refrigeration unit on the front wall of the box, above the cab roof (like a real reefer truck)."""
    y0, y1, z0, z1 = BOX_Y0 - .52, BOX_Y0 + .02, 2.64, 3.06
    cy, cz, d, h = (y0 + y1) / 2, (z0 + z1) / 2, y1 - y0, z1 - z0
    rbox(acc, (1.90, d, h), (0, cy, cz), C(NAVY), .08, 3)
    rbox(acc, (1.91, d - .06, .03), (0, cy, z0 + .05), C(GOLD), .01, 1)
    # front grille with two fans, status lights and a service hatch line
    fy = y0 - .005
    rpanel(acc, 1.66, .32, .02, (0, fy, cz + .01), PLASTIC, .05)
    for k in range(5):
        rbox(acc, (1.56, .015, .022), (0, fy - .012, z0 + .1 + k * .055), DASH, .006, 1)
    for s in (-1, 1):
        fx = s * .45
        lathe(acc, [(0, 0), (.15, 0), (.15, .015), (0, .015)], (fx, fy - .02, cz + .01), C("23272E"), 22, 0, rot=(90, 0, 0))
        lathe(acc, [(.152, 0), (.165, .03)], (fx, fy - .02, cz + .01), C(CHROME), 22, 0, rot=(90, 0, 0), cap_top=False, cap_bottom=False)
        for j in range(5):
            a = j * 2 * math.pi / 5
            rbox(acc, (.12, .01, .04), (fx + .055 * math.cos(a), fy - .035, cz + .01 + .055 * math.sin(a)), C(STEEL), .008, 1, rot=(0, math.degrees(a), 0))
        lathe(acc, [(0, 0), (.03, 0), (.03, .02), (0, .02)], (fx, fy - .045, cz + .01), C(CHROME), 10, 0, rot=(90, 0, 0))
    rpanel(acc, .045, .045, .02, (-.06, fy - .02, z1 - .08), COOL_L, .02)
    rpanel(acc, .045, .045, .02, (.02, fy - .02, z1 - .08), C("7FE08A"), .02)
    # vents on the top and the drain hoses down the box front corners
    for k in range(4):
        rbox(acc, (.30, .05, .02), (-.6 + k * .4, cy, z1 + .005), DASH, .01, 1)
    for s in (-1, 1):
        tube(acc, [(s * .82, y1, z0 + .02), (s * 1.1, BOX_Y0 - .02, 2.3), (s * 1.12, BOX_Y0 - .02, 1.3)], .022, C(STEEL), seg=8, smooth_n=2)


# --------------------------------------------------------------------------------------------- truck
def truck(name, loc=(0, 0, 0), reefer=False):
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    cab(acc, root, reefer)
    chassis(acc, reefer)
    box(acc, root, reefer)
    for s in (-1, 1):
        wheel(acc, (s * 1.02, -2.42, .48), s)
        wheel(acc, (s * 1.04, 1.75, .48), s, dual=True)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root, objs


# --------------------------------------------------------------------------------------------- preview
def preview_setup():
    rk_core.PREVIEW = QA_REDE
    setup_materials()
    for key, s in ((HEAD_L, 2.0), (RED_L, 2.5), (AMBER_L, 2.5), (COOL_L, 2.0)):
        material(key).node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = s
    for key, rough in ((CAB_WHITE, .35), (C(NAVY), .38), (REEFER_WHITE, .35), (PLATE, .4), (C(BLUE), .38), (RUBBER, .85), (TREAD, .9)):
        material(key).node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = rough
    for key in (ALU, C(STEEL)):
        b = material(key).node_tree.nodes.get("Principled BSDF")
        b.inputs["Metallic"].default_value = .75
        b.inputs["Roughness"].default_value = .3


def build_trucks():
    rk_core.clear("Rede Trucks")
    rk_core.studio((1600, 1000))
    preview_setup()
    a = truck("FleetTruck_Dry", (-1.8, 0, 0))
    b = truck("FleetTruck_Reefer", (1.8, 0, 0), reefer=True)
    return a, b


# --------------------------------------------------------------------------------------------- brand signs
STONE = "C_E6DCC6"
BULB = "E_FFE6B8"


def bulbs_ring(acc, cx, cy, cz, r, n, axis="y", rot_extra=0.0, key=BULB, size=.035):
    """Ring of round marquee bulbs (each a little lathe dome) facing -Y (axis y) or +Z."""
    for k in range(n):
        a = 2 * math.pi * k / n + rot_extra
        if axis == "y":
            p = (cx + math.cos(a) * r, cy, cz + math.sin(a) * r)
            lathe(acc, [(0, 0), (size, 0), (size * .9, size * .7), (0, size * 1.1)], p, key, 8, 0, rot=(90, 0, 0))
        else:
            p = (cx + math.cos(a) * r, cy + math.sin(a) * r, cz)
            lathe(acc, [(0, 0), (size, 0), (size * .9, size * .7), (0, size * 1.1)], p, key, 8, 0)


def disc_sign(acc, root, name, loc, R=.8, depth=.22, both=True, prefix="Brand_Logo"):
    """Round logo medallion: navy drum, gold rim with marquee bulbs, white face (the game draws the logo)."""
    x, y, z = loc
    drum = [(0, -depth / 2), (R, -depth / 2), (R + .02, -depth / 2 + .03), (R + .02, depth / 2 - .03), (R, depth / 2), (0, depth / 2)]
    lathe(acc, drum, (x, y, z), C(NAVY), 48, 0, rot=(90, 0, 0))
    faces = (-1, 1) if both else (-1,)
    for f in faces:
        fy = y + f * depth / 2
        rim = [(R - .14, 0), (R + .05, 0), (R + .07, .03), (R + .05, .07), (R - .12, .07), (R - .14, .04)]
        lathe(acc, rim, (x, fy, z), C(GOLD), 48, 1, rot=(-f * 90, 0, 0), cap_top=False, cap_bottom=False)
        lathe(acc, [(0, 0), (R - .16, 0), (R - .16, .012), (0, .012)], (x, fy, z), PLATE, 48, 0, rot=(-f * 90, 0, 0))
        n = 20
        for k in range(n):
            a = 2 * math.pi * k / n
            p = (x + math.cos(a) * (R - .045), fy + f * .075, z + math.sin(a) * (R - .045))
            lathe(acc, [(0, 0), (.032, 0), (.028, .02), (0, .034)], p, BULB, 8, 0, rot=(-f * 90, 0, 0))
        side = "Front" if f < 0 else "Back"
        anchor(f"{prefix}_{side}", (x, fy + f * .016, z), (0, 0, 0 if f < 0 else 180), .35, root)


def totem(name="RedeTotem", loc=(0, 0, 0)):
    """The chain's pylon by the car park: stone plinth with planters, navy column, name plate with lit edges,
    a big round logo medallion at the top crowned with a gold cap."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    # plinth: stone steps + two planters with shrubs
    rbox(acc, (2.3, 1.3, .22), (0, 0, .11), STONE, .04, 3)
    rbox(acc, (2.0, 1.05, .2), (0, 0, .32), C("D9CDB3"), .04, 3)
    for s in (-1, 1):
        rbox(acc, (.52, .9, .42), (s * .78, 0, .62), STONE, .05, 3)
        rbox(acc, (.44, .82, .04), (s * .78, 0, .83), C("6B4A2E"), .02, 2)
        for k in range(5):
            blob(acc, (.13, .13, .11), (s * .78 + (k % 2 - .5) * .14, -.3 + k * .15, .93), C("4E9A3E" if k % 2 else "5FB04A"), sub=2, noise=.25, seed=k + (s > 0) * 7)
    # column
    H0, H1 = .42, 5.0
    rbox(acc, (1.0, .55, H1 - H0), (0, 0, (H0 + H1) / 2), C(NAVY), .08, 3)
    for s in (-1, 1):
        rbox(acc, (.06, .57, H1 - H0 - .1), (s * .47, 0, (H0 + H1) / 2), C(GOLD), .02, 2)          # gold edges
        for k in range(14):
            lathe(acc, [(0, 0), (.025, 0), (.02, .02), (0, .03)], (s * .47, -.29, H0 + .3 + k * .3), BULB, 8, 0, rot=(90, 0, 0))
            lathe(acc, [(0, 0), (.025, 0), (.02, .02), (0, .03)], (s * .47, .29, H0 + .3 + k * .3), BULB, 8, 0, rot=(-90, 0, 0))
    # name plate (white, both faces) on the column + its frame
    for f in (-1, 1):
        rpanel(acc, .78, 2.4, .02, (0, f * .285, 2.55), PLATE, .1)
        rframe(acc, .86, 2.48, .025, .045, (0, f * .29, 2.55), C(GOLD), .12)
        anchor(f"Brand_Name_{'Front' if f < 0 else 'Back'}", (0, f * .3, 2.55), (0, 90 if f < 0 else -90, 0 if f < 0 else 180), .3, root)
    # little opening-hours plate under it (icon only: a clock drawn as a ring + hands)
    for f in (-1, 1):
        rpanel(acc, .6, .42, .02, (0, f * .285, 1.0), C(BLUE), .06)
        lathe(acc, [(.12, 0), (.15, 0), (.15, .01), (.12, .01)], (-.12, f * .3, 1.0), C(GOLD), 20, 0, rot=(-f * 90, 0, 0))
        rbox(acc, (.012, .01, .09), (-.12, f * .305, 1.035), C(GOLD), .004, 1)
        rbox(acc, (.07, .01, .012), (-.09, f * .305, 1.0), C(GOLD), .004, 1)
        for k in range(3):
            rbox(acc, (.16, .01, .025), (.13, f * .305, 1.07 - k * .07), PLATE, .008, 1)
    # head: a collar, the medallion, gold cap with a finial
    rbox(acc, (1.25, .7, .18), (0, 0, H1 + .05), C(GOLD), .05, 3)
    disc_sign(acc, root, name, (0, 0, H1 + 1.05), R=.95, depth=.36)
    lathe(acc, [(0, 0), (.22, 0), (.26, .06), (.12, .2), (.06, .32), (0, .36)], (0, 0, H1 + 2.02), C(GOLD), 24, 2)
    lathe(acc, [(0, 0), (.06, 0), (.07, .08), (0, .2)], (0, 0, H1 + 2.36), BULB, 12, 1)
    for s in (-1, 1):
        rbox(acc, (.12, .5, .22), (s * .45, 0, H1 + .22), C(NAVY), .04, 2)
    # ground spot lights aimed at the column
    for s in (-1, 1):
        lathe(acc, [(0, 0), (.08, 0), (.09, .08), (.07, .12), (0, .12)], (s * .5, -.55, .44), DASH, 12, 1, rot=(-30, 0, 0))
        lathe(acc, [(0, 0), (.06, 0), (0, .01)], (s * .5, -.6, .54), BULB, 10, 0, rot=(-30, 0, 0))
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root, objs


def wall_medallion(name="RedeMedallion", loc=(0, 0, 0)):
    """Logo medallion for the market's back wall and the DC facade (one face, wall brackets behind)."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    disc_sign(acc, root, name, (0, 0, 0), R=.85, depth=.24, both=False)
    for s in (-1, 1):
        rbox(acc, (.1, .4, .1), (s * .45, .3, .3), C(STEEL), .02, 2)
        rbox(acc, (.1, .4, .1), (s * .45, .3, -.3), C(STEEL), .02, 2)
    rbox(acc, (1.2, .05, .9), (0, .5, 0), C(STEEL), .02, 2)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root, objs


def name_board(name="RedeNameBoard", loc=(0, 0, 0), L=8.0, H=1.25):
    """Long lit name board for the back wall / DC: navy face (the game writes the name in gold), gold frame,
    marquee bulbs top and bottom, end caps."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    rbox(acc, (L, .22, H), (0, .05, 0), C(NAVY), .06, 3)
    rframe(acc, L + .1, H + .1, .05, .08, (0, -.08, 0), C(GOLD), .1)
    rpanel(acc, L - .1, H - .12, .015, (0, -.07, 0), C(BLUE), .05)
    n = int(L / .32)
    for zz in (H / 2 + .02, -H / 2 - .02):
        for k in range(n):
            lathe(acc, [(0, 0), (.03, 0), (.026, .02), (0, .032)], (-L / 2 + .2 + k * (L - .4) / (n - 1), -.1, zz), BULB, 8, 0, rot=(90, 0, 0))
    for s in (-1, 1):
        rbox(acc, (.18, .34, H + .2), (s * (L / 2 + .09), .02, 0), C(GOLD), .06, 3)
    anchor("Brand_Name_Front", (0, -.08, 0), (0, 0, 0), .4, root)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root, objs


# --------------------------------------------------------------------------------------------- DC gatehouse
def gatehouse(name="RedeGatehouse", loc=(0, 0, 0)):
    """Guard booth + barrier at the distribution centre's truck gate. The barrier arm is its own object
    (pivot at the hinge, opens about +Y) so the game can lift it for each truck."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    # island kerb with yellow/black nose
    rbox(acc, (1.9, 3.4, .16), (0, 0, .08), STONE, .04, 3)
    for k in range(6):
        rbox(acc, (.32, .05, .17), (-.8 + k * .32, -1.71, .085), C("F2C230" if k % 2 == 0 else "2B2F36"), .01, 1)
    # booth: cream walls, big windows on 3 sides, navy roof slab with gold edge and a logo plate
    bx, by, bz = 1.5, 1.7, 2.3
    rbox(acc, (bx, by, .7), (0, .3, .16 + .35), CAB_WHITE, .05, 3)
    for c in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        rbox(acc, (.1, .1, bz - .7), (c[0] * (bx / 2 - .05), .3 + c[1] * (by / 2 - .05), .86 + (bz - .7) / 2), CAB_WHITE, .03, 2)
    for s in (-1, 1):
        rpanel(acc, by - .2, bz - .82, .02, (s * (bx / 2 - .03), .3, .86 + (bz - .7) / 2), WIN, .03, rot=(0, 0, 90))
        rpanel(acc, .14, bz - .9, .01, (s * (bx / 2 - .01), .1, .86 + (bz - .7) / 2), WIN_HI, .02, rot=(0, 0, 90))
    rpanel(acc, bx - .2, bz - .82, .02, (0, .3 - by / 2 + .03, .86 + (bz - .7) / 2), WIN, .03)
    rpanel(acc, .12, bz - .9, .01, (-.3, .3 - by / 2 + .01, .86 + (bz - .7) / 2), WIN_HI, .02, rot=(0, 18, 0))
    rbox(acc, (bx, .08, bz - .7), (0, .3 + by / 2 - .04, .86 + (bz - .7) / 2), CAB_WHITE, .03, 2)
    rbox(acc, (bx + .1, by + .1, .06), (0, .3, .88), C(STEEL), .02, 2)                         # window sill
    rbox(acc, (bx + .7, by + .7, .22), (0, .3, .16 + bz + .11), C(NAVY), .06, 3)
    rbox(acc, (bx + .72, by + .72, .05), (0, .3, .16 + bz), C(GOLD), .02, 2)
    rpanel(acc, .9, .3, .01, (0, .3 - (by + .7) / 2 - .006, .16 + bz + .11), PLATE, .06)
    anchor("Brand_Logo_Front", (0, .3 - (by + .7) / 2 - .015, .16 + bz + .11), (0, 0, 0), .2, root)
    # inside: desk, monitor glow, a chair
    rbox(acc, (bx - .2, .45, .08), (0, -.25, 1.0), C("B97A45"), .02, 2)
    rbox(acc, (.4, .05, .28), (.2, -.2, 1.22), DASH, .02, 2)
    rpanel(acc, .34, .22, .005, (.2, -.228, 1.23), COOL_L, .01)
    rbox(acc, (.4, .4, .08), (-.2, .3, .6), SEAT, .04, 2)
    # roof beacon + floodlight
    lathe(acc, [(0, 0), (.1, 0), (.1, .05), (.08, .2), (0, .22)], (.45, .9, .16 + bz + .22), AMBER_L, 14, 1)
    tube(acc, [(-.6, .9, .16 + bz + .22), (-.6, .9, .16 + bz + .55), (-.6, .7, .16 + bz + .65)], .025, DASH, seg=8, smooth_n=2)
    rbox(acc, (.25, .14, .12), (-.6, .62, .16 + bz + .62), DASH, .03, 2, rot=(25, 0, 0))
    # barrier post with motor housing (navy) and a rest post at the far end
    px, py = 1.3, -1.2
    rbox(acc, (.34, .34, 1.05), (px, py, .16 + .52), C(NAVY), .06, 3)
    rbox(acc, (.36, .36, .04), (px, py, .16 + .8), C(GOLD), .01, 1)
    lathe(acc, [(0, 0), (.06, 0), (.06, .04), (0, .05)], (px, py - .18, .16 + .9), RED_L, 10, 0, rot=(90, 0, 0))
    rest_x = px + 4.2
    rbox(acc, (.1, .1, .85), (rest_x, py, .43), C(STEEL), .03, 2)
    tube(acc, [(rest_x - .12, py, .85), (rest_x - .12, py, .95), (rest_x + .12, py, .95), (rest_x + .12, py, .85)], .02, C(STEEL), seg=6)
    for k in range(3):
        rbox(acc, (.1, .102, .08), (rest_x, py, .25 + k * .22), C("F2C230"), .02, 1)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    # the arm (own object, pivot at the hinge)
    arm = Acc(name + "_Arm")
    L = 4.1
    rbox(arm, (L, .07, .1), (L / 2, 0, 0), C("FBF8F1"), .03, 2)
    for k in range(int(L / .5)):
        rbox(arm, (.25, .074, .104), (.3 + k * .5, 0, 0), RED_L.replace("E_", "C_"), .02, 1)
    for k in range(4):
        rbox(arm, (.12, .075, .03), (.6 + k * 1.0, 0, -.07), C("F2C230"), .01, 1)
    lathe(arm, [(0, -.12), (.12, -.12), (.12, .12), (0, .12)], (0, 0, 0), DASH, 16, 0, rot=(90, 0, 0))
    arms = arm.realize()
    for o in arms:
        o.name = f"{name}_Arm"
        o.parent = root
        o.location = (px, py, .16 + .92)
    return root, objs + arms


# --------------------------------------------------------------------------------------------- shopping bag
def shopping_bag(name="RedeBag", loc=(0, 0, 0)):
    """Paper carrier bag the customers leave with: navy paper, gold twisted handles, white logo plate both
    sides, gusset folds and the bread/greens peeking out. Low poly (many customers carry one)."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    W, D, H = .34, .17, .38
    rbox(acc, (W, D, H), (0, 0, H / 2), C(NAVY), .012, 1)
    rbox(acc, (W + .004, D + .004, .035), (0, 0, H - .02), C(GOLD), .006, 1)              # folded top cuff
    for s in (-1, 1):
        rbox(acc, (.006, .03, H - .06), (s * (W / 2 + .001), 0, H / 2 - .02), C(BLUE), .002, 1)   # gusset fold
        rpanel(acc, .2, .2, .004, (0, s * (D / 2 + .002), .19), PLATE, .1, rot=(0, 0, 0 if s < 0 else 180), seg=6)
        anchor(f"Brand_Logo_{'Front' if s < 0 else 'Back'}", (0, s * (D / 2 + .005), .19), (0, 0, 0 if s < 0 else 180), .08, root)
        pts = [(-.07, s * .05, H - .01), (-.06, s * .05, H + .1), (0, s * .05, H + .14), (.06, s * .05, H + .1), (.07, s * .05, H - .01)]
        tube(acc, pts, .008, C(GOLD), seg=6, smooth_n=3)
    # groceries peeking out: a baguette, leafy greens, a bottle cap
    tube(acc, [(-.1, -.02, H - .1), (-.06, .0, H + .1)], .03, C("D6A266"), seg=8, smooth_n=0)
    for k in range(3):
        blob(acc, (.05, .04, .05), (.07 + k * .025, .02 - k * .02, H + .01 + k * .01), C("5FB04A" if k != 1 else "7CC462"), sub=1, noise=.3, seed=k)
    lathe(acc, [(0, 0), (.022, 0), (.022, .03), (0, .03)], (.0, -.04, H), C("D74A3C"), 10, 0)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root, objs


def build_signs():
    rk_core.clear("Rede Signs")
    rk_core.studio((1600, 1000))
    preview_setup()
    t = totem("RedeTotem", (-4.5, 0, 0))
    m = wall_medallion("RedeMedallion", (-1.2, 0, 2.0))
    nb = name_board("RedeNameBoard", (3.6, 0, 2.0), L=5.0)
    g = gatehouse("RedeGatehouse", (-1.5, 6, 0))
    b = shopping_bag("RedeBag", (1.2, -1.5, 0))
    return t, m, nb, g, b


# --------------------------------------------------------------------------------------------- DC landmarks
def water_tower(name="RedeWaterTower", loc=(0, 0, 0)):
    """Roof-top water tank on a steel lattice with the chain's logo on four plates around the tank — the
    landmark of the distribution centre, seen from far away. Sits on the warehouse roof (base plates at z=0)."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    leg_r, H = .95, 2.6
    legs = [(math.cos(a) * leg_r, math.sin(a) * leg_r) for a in [math.pi / 4 + k * math.pi / 2 for k in range(4)]]
    for x, y in legs:
        rbox(acc, (.34, .34, .06), (x, y, .03), C(STEEL), .02, 2)
        tube(acc, [(x, y, .06), (x * .82, y * .82, H)], .065, C(NAVY), seg=10)
    for k in range(4):
        (x0, y0), (x1, y1) = legs[k], legs[(k + 1) % 4]
        for z0, z1 in ((.25, 1.25), (1.25, 2.25)):
            f0, f1 = 1 - .18 * z0 / H, 1 - .18 * z1 / H
            tube(acc, [(x0 * f0, y0 * f0, z0), (x1 * f1, y1 * f1, z1)], .025, C(STEEL), seg=6)
            tube(acc, [(x1 * f0, y1 * f0, z0), (x0 * f1, y0 * f1, z1)], .025, C(STEEL), seg=6)
        for zz in (.25, 1.25, 2.25):
            f = 1 - .18 * zz / H
            tube(acc, [(x0 * f, y0 * f, zz), (x1 * f, y1 * f, zz)], .035, C(NAVY), seg=8)
    # ladder up one leg + cage
    for s in (-1, 1):
        tube(acc, [(1.05 + s * .17, -.0, .06), (1.0 + s * .17, 0, H + .1)], .018, C(STEEL), seg=6)
    for k in range(12):
        z = .3 + k * .2
        tube(acc, [(1.05 - .17 - .002 * k, 0, z), (1.05 + .17 - .002 * k, 0, z)], .012, C(STEEL), seg=5)
    # tank: navy body with a gold belt, domed roof, catwalk with railing, four logo plates
    R, T0, T1 = 1.25, H, H + 1.55
    prof = [(0, T0 - .25), (R * .55, T0 - .22), (R * .92, T0 - .08), (R, T0 + .08), (R, T1), (R * .96, T1 + .12), (R * .6, T1 + .42), (R * .15, T1 + .58), (0, T1 + .6)]
    lathe(acc, prof, (0, 0, 0), C(NAVY), 40, 2)
    lathe(acc, [(R + .01, T0 + .32), (R + .03, T0 + .34), (R + .03, T0 + .44), (R + .01, T0 + .46)], (0, 0, 0), C(GOLD), 40, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(R + .01, T1 - .1), (R + .025, T1 - .09), (R + .025, T1 - .03), (R + .01, T1 - .02)], (0, 0, 0), C(GOLD), 40, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(0, T1 + .6), (.12, T1 + .6), (.1, T1 + .78), (0, T1 + .8)], (0, 0, 0), C(STEEL), 12, 1)
    lathe(acc, [(0, T1 + .8), (.06, T1 + .8), (.05, T1 + .9), (0, T1 + .92)], (0, 0, 0), RED_L, 10, 1)       # aircraft light
    lathe(acc, [(R - .05, T0 - .02), (R + .32, T0 - .02), (R + .32, T0 + .03), (R - .05, T0 + .03)], (0, 0, 0), ALU, 40, 0)
    for k in range(32):
        a = 2 * math.pi * k / 32
        tube(acc, [(math.cos(a) * (R + .3), math.sin(a) * (R + .3), T0 + .03), (math.cos(a) * (R + .3), math.sin(a) * (R + .3), T0 + .45)], .012, C(STEEL), seg=5)
    lathe(acc, [(R + .29, T0 + .44), (R + .31, T0 + .44), (R + .31, T0 + .47), (R + .29, T0 + .47)], (0, 0, 0), C(STEEL), 40, 0)
    lathe(acc, [(R + .29, T0 + .24), (R + .31, T0 + .24), (R + .31, T0 + .26), (R + .29, T0 + .26)], (0, 0, 0), C(STEEL), 40, 0, cap_top=False, cap_bottom=False)
    zc = (T0 + .55 + T1) / 2
    for k, (side, yaw) in enumerate((("S", 0), ("E", 90), ("N", 180), ("W", -90))):
        a = math.radians(yaw - 90)
        px, py = math.cos(a) * (R + .015), math.sin(a) * (R + .015)
        # a curved-looking plate: flat round plate + gold ring, tangent to the tank
        lathe(acc, [(0, 0), (.5, 0), (.5, .02), (0, .02)], (px, py, zc), PLATE, 32, 0, rot=(90, 0, yaw))
        lathe(acc, [(.48, 0), (.56, 0), (.56, .035), (.48, .035)], (px, py, zc), C(GOLD), 32, 0, rot=(90, 0, yaw), cap_top=False, cap_bottom=False)
        anchor(f"Brand_Logo_{side}", (px * 1.02 + math.cos(a) * .02, py * 1.02 + math.sin(a) * .02, zc), (0, 0, yaw), .25, root)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root, objs


def fuel_island(name="RedeFuelIsland", loc=(0, 0, 0)):
    """The fleet's diesel island in the yard: kerbed island, two pumps with hose and nozzle, a navy canopy on
    two columns with a gold fascia and a logo plate, bollards and a wash brush arch beside it."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    rbox(acc, (1.4, 4.2, .18), (0, 0, .09), STONE, .05, 3)
    for k in range(7):
        rbox(acc, (.2, .05, .185), (-.6 + k * .2, -2.11, .09), C("F2C230" if k % 2 == 0 else "2B2F36"), .01, 1)
        rbox(acc, (.2, .05, .185), (-.6 + k * .2, 2.11, .09), C("F2C230" if k % 2 == 0 else "2B2F36"), .01, 1)
    for yy in (-.85, .85):
        rbox(acc, (.62, .42, 1.55), (0, yy, .18 + .78), CAB_WHITE, .06, 3)
        rbox(acc, (.64, .44, .32), (0, yy, .18 + 1.38), C(NAVY), .06, 3)
        rbox(acc, (.65, .45, .03), (0, yy, .18 + 1.21), C(GOLD), .01, 1)
        for s in (-1, 1):
            rpanel(acc, .34, .22, .012, (s * .315, yy, .18 + 1.05), DASH, .03, rot=(0, 0, 90))
            rpanel(acc, .26, .09, .006, (s * .322, yy, .18 + 1.1), COOL_L, .02, rot=(0, 0, 90))
            for b in range(3):
                rbox(acc, (.012, .05, .05), (s * .322, yy - .08 + b * .08, .18 + .96), C(CHROME), .01, 1)
            # holster + nozzle and the hose looping down
            rbox(acc, (.05, .1, .14), (s * .33, yy + .12, .18 + .75), DASH, .02, 2)
            tube(acc, [(s * .34, yy + .12, .18 + .82), (s * .36, yy + .16, .18 + .88), (s * .36, yy + .2, .18 + .78)], .022, C("2B2F36"), seg=8, smooth_n=2)
            tube(acc, [(s * .34, yy - .1, .18 + .7), (s * .55, yy - .05, .3), (s * .5, yy + .12, .2), (s * .34, yy + .12, .18 + .7)], .024, RUBBER, seg=8, smooth_n=3)
    for yy in (-1.85, 1.85):
        tube(acc, [(0, yy, .18), (0, yy, 3.6)], .14, C(NAVY), seg=16)
        lathe(acc, [(.15, .18), (.2, .18), (.2, .5), (.15, .55)], (0, yy, 0), C(GOLD), 16, 0, cap_top=False, cap_bottom=False)
        for s in (-1, 1):
            lathe(acc, [(0, 0), (.09, 0), (.09, .7), (.07, .78), (0, .8)], (s * .45, yy * 1.09, .18), C("F2C230"), 12, 1)
            lathe(acc, [(.092, .5), (.092, .6)], (s * .45, yy * 1.09, .18), C("2B2F36"), 12, 0, cap_top=False, cap_bottom=False)
    rbox(acc, (3.4, 5.0, .42), (0, 0, 3.8), C(NAVY), .08, 3)
    rbox(acc, (3.44, 5.04, .1), (0, 0, 3.62), C(GOLD), .03, 2)
    rbox(acc, (3.2, 4.8, .03), (0, 0, 3.58), C("F4F1E8"), .01, 1)
    for k in range(4):
        rpanel(acc, .7, .25, .02, (-.7 + (k % 2) * 1.4, -1.2 + (k // 2) * 2.4, 3.565), HEAD_L, .05, rot=(90, 0, 0))
    for s in (-1, 1):
        rpanel(acc, 1.0, .32, .012, (0, s * 2.522, 3.8), PLATE, .06, rot=(0, 0, 0 if s < 0 else 180))
        anchor(f"Brand_Logo_{'Front' if s < 0 else 'Back'}", (0, s * 2.53, 3.8), (0, 0, 0 if s < 0 else 180), .2, root)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root, objs


def build_dc():
    rk_core.clear("Rede DC")
    rk_core.studio((1600, 1000))
    preview_setup()
    w = water_tower("RedeWaterTower", (-3, 0, 0))
    f = fuel_island("RedeFuelIsland", (2.5, 0, 0))
    g = gatehouse("RedeGatehouse", (7, 0, 0))
    return w, f, g


# --------------------------------------------------------------------------------------------- preview of the brand
LOGO_SIZE = {"Door": .26, "Back": .44, "Bag": .16}


def _logo_material(path):
    m = bpy.data.materials.get("PREVIEW_Logo") or bpy.data.materials.new("PREVIEW_Logo")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    t = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=True)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = .45
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        m.blend_method = "HASHED"
    return m


def _text_material(hexcol, name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = srgb(hexcol) + (1,)
    return m


def brand_preview(logo_png, name="Bom Preço"):
    """Preview only (never exported): puts a logo picture and the chain's name on every Brand_* empty, the way the
    game will draw them, so Lucas sees the finished look."""
    for o in [o for o in bpy.data.objects if o.name.startswith("PREVIEW_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    lm = _logo_material(logo_png)
    font = bpy.data.fonts.get("Fredoka_700Bold") or bpy.data.fonts.load(rk_core.FONT)
    navy_t = _text_material(NAVY, "PREVIEW_TextNavy")
    gold_t = _text_material("F0C75A", "PREVIEW_TextGold")
    made = 0
    for e in [o for o in bpy.context.scene.objects if o.type == "EMPTY" and o.name.startswith("Brand_")]:
        root = e.parent
        rname = root.name if root else ""
        if e.name.startswith("Brand_Logo"):
            if "Door" in e.name:
                size = LOGO_SIZE["Door"]
            elif "Back" in e.name and "Truck" in rname:
                size = LOGO_SIZE["Back"]
            elif "Bag" in rname:
                size = LOGO_SIZE["Bag"]
            elif "Truck" in rname:
                size = .95
            elif "Totem" in rname:
                size = 1.45
            elif "Medallion" in rname:
                size = 1.25
            elif "WaterTower" in rname:
                size = .8
            elif "Gatehouse" in rname:
                size = .26
            elif "Fuel" in rname:
                size = .28
            else:
                size = .5
            bpy.ops.mesh.primitive_plane_add(size=size)
            p = bpy.context.active_object
            p.name = "PREVIEW_" + e.name
            p.data.materials.append(lm)
            # plane lies in XY facing +Z: stand it up facing -Y
            p.data.transform(Matrix.Rotation(math.radians(90), 4, "X"))
            p.matrix_world = e.matrix_world @ Matrix.Translation((0, -.004, 0))
            made += 1
        else:
            cu = bpy.data.curves.new("PREVIEW_txt", "FONT")
            cu.body = name.upper() if "Truck" in rname or "Board" in rname else name
            cu.font = font
            cu.align_x = "CENTER"
            cu.align_y = "CENTER"
            cu.extrude = .004
            big = "Board" in rname
            cu.size = .62 if big else .36 if "Truck" in rname else .26
            ob = bpy.data.objects.new("PREVIEW_" + e.name, cu)
            bpy.context.scene.collection.objects.link(ob)
            ob.data.materials.append(gold_t if big else navy_t)
            ob.matrix_world = e.matrix_world @ Matrix.Translation((0, -.006, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")
            made += 1
    return made


def build_showcase(logo_png, name="Bom Preço"):
    """Every asset of round 1 in one scene with a sample brand on it (preview images for Lucas)."""
    rk_core.clear("Rede Showcase")
    rk_core.studio((1800, 1100), bg=(.86, .84, .8))
    preview_setup()
    fl = bpy.data.objects.get("RK_Floor")
    if fl:
        fl.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.55, .55, .56, 1)
    truck("FleetTruck_Dry", (-3.2, 0, 0))
    truck("FleetTruck_Reefer", (0.3, 0, 0), reefer=True)
    totem("RedeTotem", (4.4, -1.5, 0))
    gatehouse("RedeGatehouse", (8.2, 1.2, 0))
    fuel_island("RedeFuelIsland", (-8.0, 1.0, 0))
    # a navy wall with the name board and the medallion, the water tower on its roof
    acc = Acc("Mock_Wall")
    rbox(acc, (16, .4, 4.4), (0, 9.0, 2.2), C(NAVY), .05, 2)
    rbox(acc, (16.1, .45, .12), (0, 9.0, 4.45), C(GOLD), .03, 2)
    rbox(acc, (16, 8, .3), (0, 13, 4.5), C("B8BEC4"), .05, 2)
    for o in acc.realize():
        o.name = "Mock_Wall"
    name_board("RedeNameBoard", (1.4, 8.68, 2.6), L=7.0)
    wall_medallion("RedeMedallion", (-4.2, 8.55, 2.6))
    water_tower("RedeWaterTower", (4.5, 12.5, 4.65))
    shopping_bag("RedeBag", (2.6, -2.6, 0))
    m = mannequin((2.2, -2.7, 0)) if "mannequin" in globals() else None
    brand_preview(logo_png, name)
    return m


def shoot_showcase(prefix="rede_r1"):
    shots = []
    shots.append(rk_core.shoot(prefix + "_overview", (0, 3.5, 1.5), (-.55, -1, .75), 26, 32, (1800, 1100)))
    shots.append(rk_core.shoot(prefix + "_trucks", (-1.4, 0, 1.4), (-.9, -1, .45), 11.5, 36, (1800, 1100)))
    shots.append(rk_core.shoot(prefix + "_trucks_back", (-1.4, 0, 1.4), (.85, 1, .4), 11.5, 36, (1800, 1100)))
    shots.append(rk_core.shoot(prefix + "_totem_bag", (3.6, -2.0, 2.6), (-.25, -1, .25), 9.5, 36, (1400, 1100)))
    shots.append(rk_core.shoot(prefix + "_dc", (3.0, 6.0, 2.5), (.55, -1, .5), 16, 34, (1800, 1100)))
    shots.append(rk_core.shoot(prefix + "_gamecam", (0, 3, 1), (-.62, -.62, .95), 34, 30, (1800, 1100)))
    return shots
