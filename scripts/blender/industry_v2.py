"""Distrito industrial, preview round 2 (Lucas 08/11 feedback on round 1):
  * grass with the game's own grass texture (Assets/Art/TerrainTiles/Grass.png), one lawn per lot (no concrete strip
    splitting it); pavers, concrete pads and brick use the game's MarketStages textures;
  * frigorífico: a bigger lot (34 x 38 m) with a clear truck yard; the office tower moved off the truck bays; the three
    buildings look different from each other (T1 brick + navy barrel roof, T2 tall white cold store with a dock
    canopy and a screened plant deck, T3 grey-blue processing plant with a glass ribbon, round tanks and a steam stack);
  * factory: a much bigger lot (48 x 60 m) with lanes and lawns between the buildings, and its own architecture so it
    no longer reads like the frigorífico: red brick, sawtooth roofs with north lights, a barrel-roof warehouse, a
    tall brick chimney, silos, a classic brick office; the white high-bay tower only at the last tier.

Run after industry_v1.py in the same namespace (it reuses its helpers):
    exec(open(REPO + "/scripts/blender/industry_v2.py").read(), ns); ns["shoot_factory2"](); ns["shoot_frigo2"]()
"""
import bpy, bmesh, math, os
from mathutils import Vector

ASSETS = os.path.join(REPO, "unity", "CheckoutSimulator", "Assets")
QA_IND2 = os.path.join(REPO, "unity", "CheckoutSimulator", "Temp", "qa", "industry2")
X_GRASS, X_PAVER, X_CONC, X_BRICK, X_ASPH = "X_Grass", "X_Pavers", "X_Concrete", "X_Brick", "X_Asphalt"
CREAM_WALL = "C_EFE6D2"
STEEL_BLUE, STEEL_BLUE_L = "C_8FA7BA", "C_A9BDCC"
SHED_ROOF = "C_2E4A7D"     # navy family: the sawtooth slopes follow "Cores do mercado"
ARCH_ROOF = "C_9AA6AE"


def tex_mat(key, path, size, tint=(1, 1, 1), rough=.75):
    """A preview material with the game's texture, projected from the object's axes (box) every `size` metres."""
    m = bpy.data.materials.get(key)
    if m:
        return m
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / size, 1 / size, 1 / size)
    im = nt.nodes.new("ShaderNodeTexImage")
    im.image = bpy.data.images.load(path, check_existing=True)
    im.projection = "BOX"
    im.projection_blend = .25
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 1
    mix.inputs["Color2"].default_value = tint + (1,)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], im.inputs["Vector"])
    nt.links.new(im.outputs["Color"], mix.inputs["Color1"])
    nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
    return m


def textures():
    T = os.path.join(ASSETS, "Art", "MarketStages", "Textures")
    tex_mat(X_GRASS, os.path.join(ASSETS, "Art", "TerrainTiles", "Grass.png"), 5.0, rough=.9)
    tex_mat(X_PAVER, os.path.join(T, "MS_Pavers_albedo.png"), 3.0)
    tex_mat(X_CONC, os.path.join(T, "MS_Concrete_albedo.png"), 4.0)
    tex_mat(X_BRICK, os.path.join(T, "MS_Brick_albedo.png"), 1.6, rough=.85)
    tex_mat(X_ASPH, os.path.join(T, "MS_Concrete_albedo.png"), 6.0, tint=(.36, .37, .39), rough=.9)


# --------------------------------------------------------------------------------------------- walls and roofs
def brick_wall(acc, axis, line, out, u0, u1, h, holes=(), cornice=True, pil_every=0.0):
    """A red brick wall (the game's brick texture) on a concrete plinth, a navy cornice band with gold coping
    and, optionally, brick pilasters."""
    t = .32
    def B(ua, ub, va, vb, za, zb, key, r=.01, seg=1):
        wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
    hu = [(a, b) for a, b, _, _ in holes]
    for a, b in spans(u0, u1, hu):
        B(a, b, -t, 0, 0, h, X_BRICK, .01)
    for a, b, za, zb in holes:
        B(a, b, -t, 0, zb, h, X_BRICK, .01)
        if za > .02:
            B(a, b, -t, 0, 0, za, X_BRICK, .01)
        B(a - .12, b + .12, 0, .06, zb, zb + .22, CONCRETE, .01)       # lintel
    for a, b in spans(u0, u1, [(x - .05, y + .05) for x, y, z0, _ in holes if z0 < .5]):
        B(a, b, 0, .07, 0, .45, CONCRETE, .015, 2)
    if cornice:
        B(u0 - .03, u1 + .03, 0, .14, h - .55, h, C(NAVY), .03, 2)
        B(u0 - .06, u1 + .06, -t - .05, .2, h, h + .1, C(GOLD), .03, 2)
    if pil_every:
        n = max(1, round((u1 - u0) / pil_every))
        for k in range(n + 1):
            uu = u0 + k * (u1 - u0) / n
            if any(a - .3 < uu < b + .3 for a, b in hu):
                continue
            B(uu - .22, uu + .22, 0, .14, .45, h - .55, X_BRICK, .02)


def window_grid(acc, axis, line, out, u0, u1, rows, cols, z0, wh=1.5, gap=1.4, frame=C(NAVY)):
    """Rows of separate factory windows (white frames, small panes) — the brick buildings' look."""
    def B(ua, ub, va, vb, za, zb, key, r=.01, seg=1):
        wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
    w = (u1 - u0) / cols
    for r in range(rows):
        za = z0 + r * (wh + gap)
        for c in range(cols):
            a, b = u0 + c * w + w * .18, u0 + (c + 1) * w - w * .18
            B(a - .06, b + .06, -.02, .06, za - .06, za + wh + .06, frame, .01)
            B(a, b, .02, .07, za, za + wh, WIN, .01)
            for k in (1, 2):
                uu = a + k * (b - a) / 3
                B(uu - .025, uu + .025, .05, .1, za, za + wh, C(WHITE), .005)
            B(a, b, .05, .1, za + wh * .5 - .025, za + wh * .5 + .025, C(WHITE), .005)
            B(a - .1, b + .1, 0, .16, za - .14, za - .06, CONCRETE, .01)      # sill


def sawtooth_roof(acc, x0, x1, y0, y1, z, teeth, rise=2.0):
    """North-light sawtooth roof: navy slopes rising towards +Y, glazed vertical faces looking north, steel ribs."""
    d = (y1 - y0) / teeth
    for k in range(teeth):
        ya, yb = y0 + k * d, y0 + (k + 1) * d
        prof = [(ya, z), (yb, z), (yb, z + rise)]
        prism(acc, prof, x1 - x0 + .2, SHED_ROOF, ((x0 + x1) / 2, 0, 0), r=.02, seg=1)
        rbox(acc, (x1 - x0 - .2, .08, rise - .25), ((x0 + x1) / 2, yb - .02, z + rise / 2), WIN, .01, 1)
        n = max(2, int((x1 - x0) / 1.4))
        for j in range(n + 1):
            xx = x0 + .1 + j * (x1 - x0 - .2) / n
            rbox(acc, (.06, .12, rise - .2), (xx, yb + .01, z + rise / 2 - .05), C(STEEL), .01, 1)
        # ribs along the slope
        j = x0 + .6
        while j < x1 - .4:
            L = math.hypot(d, rise)
            ang = math.degrees(math.atan2(rise, d))
            rbox(acc, (.05, L, .06), (j, (ya + yb) / 2, z + rise / 2 + .05), "C_243B66", .01, 1, rot=(ang, 0, 0))
            j += 1.2
        rbox(acc, (x1 - x0 + .25, .25, .18), ((x0 + x1) / 2, yb, z + rise + .05), C(GOLD), .02, 1)


def arch_roof(acc, x0, x1, y0, y1, z, rise, key=ARCH_ROOF, n=18):
    """Barrel (arched) roof along Y with ribs and glazed lunettes in both gables."""
    w = x1 - x0
    pts = []
    for i in range(n + 1):
        a = math.pi * i / n
        pts.append(((x0 + x1) / 2 - math.cos(a) * w / 2, z + math.sin(a) * rise))
    bm = bmesh.new()
    front = [bm.verts.new((x, y0 - .15, zz)) for x, zz in pts]
    back = [bm.verts.new((x, y1 + .15, zz)) for x, zz in pts]
    for i in range(n):
        bm.faces.new((front[i], front[i + 1], back[i + 1], back[i]))
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv_box(bm)
    acc.add(bm, key, "Body")
    # ribs
    yy = y0 + .8
    while yy < y1 - .5:
        tube(acc, [(x, yy, zz + .04) for x, zz in pts], .05, C(STEEL), seg=5)
        yy += 1.6
    # gold edge arcs on the gables and lunette glazing
    for yg, s in ((y0 - .17, -1), (y1 + .17, 1)):
        tube(acc, [(x, yg, zz + .02) for x, zz in pts], .08, C(GOLD), seg=6)
        lp = [((x0 + x1) / 2 - math.cos(math.pi * i / 12) * w * .36, z + .15 + math.sin(math.pi * i / 12) * rise * .7) for i in range(13)]
        bm = bmesh.new()
        vs = [bm.verts.new((x, yg + s * .02, zz)) for x, zz in lp]
        bm.faces.new(vs if s > 0 else list(reversed(vs)))
        uv_box(bm)
        acc.add(bm, WIN, "Body")
        for i in range(1, 6):
            xx = x0 + w * .14 + i * w * .72 / 6
            hh = math.sqrt(max(0, 1 - ((xx - (x0 + x1) / 2) / (w * .36)) ** 2)) * rise * .7
            rbox(acc, (.05, .05, max(.05, hh)), (xx, yg + s * .04, z + .15 + hh / 2), C(WHITE), .005, 1)


def lawn(acc, x0, x1, y0, y1, trees_at=(), seed=0, kerb=True):
    """A lawn with the game's grass texture, a low kerb, and trees."""
    if kerb:
        rbox(acc, (x1 - x0 + .3, y1 - y0 + .3, .14), ((x0 + x1) / 2, (y0 + y1) / 2, .07), KERB, .03, 2)
    rbox(acc, (x1 - x0, y1 - y0, .06), ((x0 + x1) / 2, (y0 + y1) / 2, .13), X_GRASS, .01, 1)
    for k, (x, y) in enumerate(trees_at):
        leafy_tree(acc, (x, y, .15), 4.4 + (k % 3) * .6, 1.9, seed + k, density=.75)


def lane_marks(acc, x0, y0, x1, y1, w=.12, dash=1.5, gap=1.5):
    L = math.hypot(x1 - x0, y1 - y0)
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
    t = 0
    while t < L:
        a, b = t / L, min(1, (t + dash) / L)
        cx, cy = x0 + (x1 - x0) * (a + b) / 2, y0 + (y1 - y0) * (a + b) / 2
        rbox(acc, ((b - a) * L, w, .012), (cx, cy, .025), LINE_W, .004, 1, rot=(0, 0, yaw))
        t += dash + gap


def van(acc, x, y, yaw=0, key="C_F7F4EC", reefer=False):
    """A small delivery van (white, navy stripe) — scale ~4.6 x 1.9 m."""
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    def P(dx, dy, z):
        return (x + dx * ca - dy * sa, y + dx * sa + dy * ca, z)
    rbox(acc, (1.9, 3.3, 1.9), P(0, .55, 1.35), key, .18, 3, rot=(0, 0, yaw))
    rbox(acc, (1.9, 1.3, 1.25), P(0, -1.6, 1.0), key, .3, 3, rot=(0, 0, yaw))
    rbox(acc, (1.8, .6, .6), P(0, -1.95, 1.45), WIN, .15, 3, rot=(0, 0, yaw))
    rbox(acc, (1.95, 3.2, .25), P(0, .55, 1.05), C(NAVY), .04, 2, rot=(0, 0, yaw))
    if reefer:
        rbox(acc, (1.4, .5, .5), P(0, 2.0, 2.45), "C_D7DCDF", .06, 2, rot=(0, 0, yaw))
    for dx in (-.85, .85):
        for dy in (-1.5, 1.35):
            px, py, _ = P(dx, dy, 0)
            cyl_x(acc, .36, .24, (px, py, .36), RUBBER, 14) if abs(ca) > .5 else cyl_y(acc, .36, .24, (px, py, .36), RUBBER, 14)


# --------------------------------------------------------------------------------------------- the factory (round 2)
FW, FD = 48.0, 60.0          # x -24..24, y -30..30; the street on -Y
F_GATE = (8.0, 16.0)         # truck gate on the street (x)


def factory_lot2(acc, tier):
    x0, x1, y0, y1 = -FW / 2, FW / 2, -FD / 2, FD / 2
    rbox(acc, (FW, FD, .06), (0, 0, -.02), X_ASPH, .01, 1)
    rbox(acc, (FW + .3, .3, .18), (0, y0 - .15, .09), KERB, .03, 2)
    # the main lane from the gate to the back, dashed centre line
    lane_marks(acc, 12.0, y0 + 1, 12.0, y1 - 3)
    # pavers in front of the buildings
    rbox(acc, (16.0, 5.0, .05), (-14.0, -26.5, .02), X_PAVER, .01, 1)
    # lawns: the back of the lot waits as one lawn until the buildings come
    if tier == 1:
        lawn(acc, -23.0, 6.5, -12.0, 29.0, [(-18, 20), (-6, 25), (2, 10), (-12, 4)], 11)
        lawn(acc, 17.0, 23.0, -12.0, 29.0, [(20, 0), (20, 18)], 21)
    elif tier == 2:
        lawn(acc, -23.0, 6.5, 6.0, 29.0, [(-18, 20), (-6, 25), (2, 12)], 11)
        lawn(acc, 17.0, 23.0, 2.0, 29.0, [(20, 8), (20, 22)], 21)
    elif tier < 5:
        lawn(acc, 17.0, 23.0, 14.0, 29.0, [(20, 20)], 21)
    lawn(acc, -23.0, -5.5, -29.2, -27.4, [(-21, -28.3), (-9, -28.3)], 31)        # front verge with trees
    fence(acc, x0 + .3, y0 + .3, x1 - .3, y0 + .3, gaps=(((F_GATE[0] + 24) / 48, (F_GATE[1] + 24) / 48),))
    fence(acc, x0 + .3, y0 + .3, x0 + .3, y1 - .3)
    fence(acc, x1 - .3, y0 + .3, x1 - .3, y1 - .3)
    fence(acc, x0 + .3, y1 - .3, x1 - .3, y1 - .3)
    for gx in F_GATE:
        rbox(acc, (.6, .6, 2.4), (gx, y0 + .3, 1.2), X_BRICK, .03, 2)
        rbox(acc, (.7, .7, .12), (gx, y0 + .3, 2.46), C(GOLD), .02, 1)
        lathe(acc, [(0, 0), (.18, 0), (.18, .32), (0, .34)], (gx, y0 + .3, 2.52), HEAD_L, 12, 1)


def f2_workshop(acc, root):
    """T1 — Mini fábrica: a brick workshop with a two-tooth sawtooth roof, a roller door with an awning, factory
    windows, a delivery van and pallets of the brand's boxes."""
    x0, x1, y0, y1, h = -22.0, -8.0, -25.0, -14.0, 4.6
    door = (-18.6, -14.8, 0, 3.4)
    brick_wall(acc, "x", y0, -1, x0, x1, h, [door, (-12.4, -11.4, 0, 2.2)])
    brick_wall(acc, "x", y1, 1, x0, x1, h)
    brick_wall(acc, "y", x0, -1, y0, y1, h)
    brick_wall(acc, "y", x1, 1, y0, y1, h, [(-23.0, -21.0, 1.2, 2.8), (-19.5, -17.5, 1.2, 2.8)])
    roll_door(acc, "x", y0, -1, -16.7, 3.8, 3.4)
    person_door(acc, "x", y0, -1, -11.9)
    window_grid(acc, "x", y0, -1, -10.8, -8.3, 1, 1, 1.2)
    window_grid(acc, "y", x1, 1, -23.5, -15.5, 1, 2, 1.2)
    rbox(acc, (x1 - x0, y1 - y0, .25), ((x0 + x1) / 2, (y0 + y1) / 2, h - .1), FLAT_ROOF, .02, 1)
    sawtooth_roof(acc, x0 + .1, x1 - .1, y0 + .1, y1 - .1, h, 2, 1.7)
    rbox(acc, (4.6, 1.7, .2), (-16.7, y0 - .85, 3.95), C(NAVY), .05, 3)
    rbox(acc, (4.64, 1.74, .07), (-16.7, y0 - .85, 3.82), C(GOLD), .02, 1)
    lathe(acc, [(.26, h), (.24, h + 3.2)], (-9.4, -15.6, 0), C(STEEL), 16, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(.36, h + 3.2), (.36, h + 3.35), (.16, h + 3.6), (0, h + 3.62)], (-9.4, -15.6, 0), C(STEEL), 16, 0)
    board(root, "BoardMini", (-16.7, y0 - .3, 5.6), 5.0, .8)
    logo_disc(root, acc, "Mini", (-10.6, y0 - .2, 3.6), R=.5)
    van(acc, -5.0, -24.0, 180)
    pallet_stack(acc, -21.0, -26.4, 2)
    pallet_stack(acc, -13.4, -26.6, 1, "C_D9B07A")


def f2_hall(acc, root):
    """T2 — Fábrica: the production hall in brick with a four-tooth sawtooth roof, two loading docks on the lane,
    two flour silos with a conveyor into the hall, a covered walkway to the workshop."""
    x0, x1, y0, y1, h = -4.0, 8.0, -24.0, -4.0, 7.0
    docks = [(-21.0, -17.8, .1, 3.8), (-15.0, -11.8, .1, 3.8)]
    brick_wall(acc, "y", x1, 1, y0, y1, h, docks + [(-8.5, -7.5, 0, 2.2)], pil_every=4.0)
    brick_wall(acc, "y", x0, -1, y0, y1, h, pil_every=4.0)
    brick_wall(acc, "x", y0, -1, x0, x1, h, [(-1.5, 5.5, 1.4, 4.2)])
    brick_wall(acc, "x", y1, 1, x0, x1, h)
    for a, b, _, _ in docks:
        roll_door(acc, "y", x1, 1, (a + b) / 2, 3.2, 3.7)
    person_door(acc, "y", x1, 1, -8.0)
    window_grid(acc, "x", y0, -1, -1.5, 5.5, 1, 3, 1.5, wh=2.6)
    window_grid(acc, "y", x0, -1, -23.0, -5.0, 1, 5, 1.6, wh=2.2)
    rbox(acc, (x1 - x0, y1 - y0, .25), ((x0 + x1) / 2, (y0 + y1) / 2, h - .1), FLAT_ROOF, .02, 1)
    sawtooth_roof(acc, x0 + .1, x1 - .1, y0 + .1, y1 - .1, h, 4, 2.2)
    board(root, "BoardHall", (2.0, y0 - .3, 5.9), 7.0, 1.1)
    logo_disc(root, acc, "Hall", (6.9, y0 - .2, 5.9), R=.6)
    for sy in (-1.0, 3.8):
        silo(acc, 3.5, sy, 1.7, 8.5)
    conveyor_bridge(acc, (3.5, -1.8), (3.5, -4.2), 9.6, 1.0)
    pipe_run(acc, [(3.5, 2.2, 12.2), (3.5, -1.0, 12.2)], .12)
    # covered walkway workshop -> hall
    rbox(acc, (4.2, 2.2, .18), (-6.0, -19.0, 3.2), C(NAVY), .03, 2)
    for xx in (-7.8, -4.2):
        for yy in (-19.9, -18.1):
            lathe(acc, [(0, 0), (.07, 0), (.07, 3.1), (0, 3.12)], (xx, yy, 0), C(STEEL), 8, 0)
    lawn(acc, -6.8, -4.6, -12.0, -5.0, [(-5.7, -8.5)], 41)


def f2_industry(acc, root):
    """T3 — Indústria: a barrel-roof warehouse at the back, the tall brick chimney, a three-storey brick office on
    the street with a corner entrance, and a conveyor gallery from the hall."""
    x0, x1, y0, y1, h = -22.0, 4.0, 4.0, 22.0, 7.5
    holes = [(5.0, 8.4, .1, 4.0), (10.0, 13.4, .1, 4.0)]
    for axis, line, out, u0, u1, hl in (("y", x1, 1, y0, y1, holes), ("y", x0, -1, y0, y1, ()), ("x", y0, -1, x0, x1, ()), ("x", y1, 1, x0, x1, ())):
        def B(ua, ub, va, vb, za, zb, key, r=.01, seg=1, axis=axis, line=line, out=out):
            wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
        for a, b in spans(u0, u1, [(p, q) for p, q, _, _ in hl]):
            B(a, b, -.3, 0, 0, h, CREAM_WALL, .01)
        for a, b, za, zb in hl:
            B(a, b, -.3, 0, zb, h, CREAM_WALL, .01)
        for a, b in spans(u0, u1, [(p - .05, q + .05) for p, q, _, _ in hl]):
            B(a, b, 0, .08, 0, 1.1, X_BRICK, .015)
        B(u0 - .03, u1 + .03, 0, .12, h - .35, h, C(NAVY), .03, 2)
    for a, b, _, _ in holes:
        roll_door(acc, "y", x1, 1, (a + b) / 2, 3.2, 3.9)
    window_grid(acc, "x", y0, -1, x0 + 1, x1 - 1, 1, 7, 3.6, wh=1.6, gap=0)
    arch_roof(acc, x0, x1, y0, y1, h, 4.2)
    chimney(acc, -19.0, 26.0, .9, 24)
    conveyor_bridge(acc, (2.0, -4.0), (2.0, 4.0), 7.6, 1.3)
    # brick office on the street (front-right of the workshop): three storeys, corner entrance with a canopy
    ox0, ox1, oy0, oy1, oh = -6.0, 4.0, -29.0, -25.5, 10.0
    brick_wall(acc, "x", oy0, -1, ox0, ox1, oh, [(-1.6, .6, 0, 2.6)])
    brick_wall(acc, "x", oy1, 1, ox0, ox1, oh)
    brick_wall(acc, "y", ox0, -1, oy0, oy1, oh)
    brick_wall(acc, "y", ox1, 1, oy0, oy1, oh)
    rbox(acc, (ox1 - ox0, oy1 - oy0, .25), ((ox0 + ox1) / 2, (oy0 + oy1) / 2, oh - .1), FLAT_ROOF, .02, 1)
    window_grid(acc, "x", oy0, -1, ox0 + .3, -2.0, 3, 2, 1.0, wh=1.8, gap=1.5)
    window_grid(acc, "x", oy0, -1, 1.0, ox1 - .3, 3, 2, 1.0, wh=1.8, gap=1.5)
    window_grid(acc, "x", oy0, -1, -1.6, .6, 2, 1, 4.3, wh=1.8, gap=1.5)
    rframe(acc, 2.2, 2.6, .1, .1, (-.5, oy0 - .02, 1.3), C(STEEL), .02)
    rpanel(acc, 2.0, 2.45, .03, (-.5, oy0 - .05, 1.25), C("8FB2C4"), .02)
    rbox(acc, (3.4, 1.6, .25), (-.5, oy0 - .8, 3.0), C(NAVY), .05, 3)
    rbox(acc, (3.44, 1.64, .07), (-.5, oy0 - .8, 2.86), C(GOLD), .02, 1)
    logo_disc(root, acc, "Office", (-.5, oy0 - .2, 9.0), R=.75)
    trees(acc, [(-22.0, -28.6), (6.5, -28.6)], 5)


def f2_complex(acc, root):
    """T4 — Complexo industrial: tank farm with a pipe bridge over the lane, the water tower with the logo, a fleet
    truck yard on the right with two trucks, a gatehouse."""
    rbox(acc, (9.0, 9.0, .3), (19.5, 8.0, .15), X_CONC, .02, 1)
    for k, (tx, ty) in enumerate(((17.3, 5.8), (21.7, 5.8), (17.3, 10.2), (21.7, 10.2))):
        tank(acc, tx, ty, 1.7, 7.5 + (k % 2) * 1.5)
    # pipe bridge over the lane from the tanks to the warehouse
    for px in (9.5, 14.5):
        for s in (-1, 1):
            tube(acc, [(px, 8.0 + s * .5, 0), (px, 8.0 + s * .5, 6.0)], .09, C(NAVY), seg=8)
    for k, key in enumerate((C(STEEL), C(GOLD), C(STEEL))):
        tube(acc, [(4.2, 7.6 + k * .4, 6.2), (16.0, 7.6 + k * .4, 6.2)], .11, key, seg=10)
    wt, _ = water_tower(f"{root.name}_WaterTower", (0, 0, 0))
    wt.parent = root
    wt.location = Vector((-15.0, 10.0, 11.7))
    # truck yard: bays painted on the asphalt along the right fence, two fleet trucks
    for k in range(4):
        rbox(acc, (5.0, .12, .012), (20.5, -24.0 + k * 4.0, .026), LINE_W, .004, 1)
    for k, (yy, reefer) in enumerate(((-22.0, False), (-18.0, True))):
        r, _ = truck(f"{root.name}_Truck{k}", (0, 0, 0), reefer=reefer)
        r.parent = root
        r.location = Vector((20.5, yy, 0))
        r.rotation_euler = (0, 0, math.radians(-90))
        r.scale = (.75, .75, .75)
    # gatehouse at the truck gate
    rbox(acc, (2.4, 2.0, 2.6), (17.6, -27.6, 1.3), C(WHITE), .05, 2)
    rbox(acc, (2.44, 2.04, .5), (17.6, -27.6, 2.45), C(NAVY), .04, 2)
    rbox(acc, (2.0, .06, 1.0), (17.6, -28.62, 1.6), WIN, .02, 1)
    rbox(acc, (6.0, .12, .12), (12.0, -29.0, 1.05), YELLOW, .03, 1)


def f2_mega(acc, root):
    """T5 — Megaindústria: the automated high-bay warehouse with the giant logo on the back right, solar on the
    sawtooth hall's neighbour (the warehouse's arch stays), a second chimney, the flag square at the entrance."""
    x0, x1, y0, y1, h = 6.5, 23.0, 15.0, 29.0, 18.0
    hall(acc, x0, x1, y0, y1, h, {"S": [(13.0, 16.4, .1, 4.0)]}, skylights=0, pil=3.3)
    roll_door(acc, "x", y0, -1, 14.7, 3.4, 4.0)
    logo_disc(root, acc, "HighBay", ((x0 + x1) / 2, y0 - .2, 14.0), R=2.4)
    board(root, "BoardHighBay", ((x0 + x1) / 2, y0 - .32, 9.8), 12.0, 1.8)
    conveyor_bridge(acc, (4.0, 17.0), (6.5, 17.0), 9.0, 2.0)
    chimney(acc, -14.0, 26.5, .8, 21)
    # solar carports over the staff car park (front left)
    for k in range(3):
        cx = -21.0 + k * 5.0
        for s in (-1, 1):
            lathe(acc, [(0, 0), (.08, 0), (.08, 3.0), (0, 3.02)], (cx + s * 1.8, -9.0, 0), C(NAVY), 8, 0)
        rbox(acc, (4.6, 5.4, .12), (cx, -10.5, 3.2), C(STEEL), .02, 1, rot=(-8, 0, 0))
        for j in range(2):
            for i in range(4):
                rbox(acc, (1.0, 2.4, .05), (cx - 1.65 + i * 1.1, -11.8 + j * 2.6, 3.32 + j * .36), SOLAR, .01, 1, rot=(-8, 0, 0))
        for i, col in enumerate(("C_D74A3C", "C_2F6FA8")):
            px = cx - 1.1 + i * 2.2
            rbox(acc, (1.7, 3.6, .7), (px, -10.5, .55), col, .25, 3)
            rbox(acc, (1.5, 1.9, .55), (px, -10.2, 1.15), WIN, .22, 3)
    # flags in a little square by the gate
    rbox(acc, (6.0, 3.0, .08), (3.5, -27.8, .05), X_PAVER, .01, 1)
    for k in range(3):
        fx = 1.6 + k * 1.9
        lathe(acc, [(0, 0), (.06, 0), (.04, 8.5), (0, 8.55)], (fx, -27.8, 0), C(STEEL), 10, 0)
        rbox(acc, (1.4, .02, .9), (fx + .73, -27.8, 7.9), (C(NAVY), PLATE, C(GOLD))[k], .01, 1)


FACTORY2 = [
    ("T1", "Mini fábrica", [f2_workshop]),
    ("T2", "Fábrica", [f2_workshop, f2_hall]),
    ("T3", "Indústria", [f2_workshop, f2_hall, f2_industry]),
    ("T4", "Complexo industrial", [f2_workshop, f2_hall, f2_industry, f2_complex]),
    ("T5", "Megaindústria", [f2_workshop, f2_hall, f2_industry, f2_complex, f2_mega]),
]


def factory2(tier, loc=(0, 0, 0)):
    tid, label, parts = FACTORY2[tier - 1]
    root = new_root(f"Factory2{tid}", loc)
    acc = Acc(root.name)
    factory_lot2(acc, tier)
    for p in parts:
        p(acc, root)
    finish(root, acc)
    return root


# --------------------------------------------------------------------------------------------- the frigorífico (round 2)
GW, GD = 34.0, 38.0          # x -17..17, y -19..19; street on -Y; truck gate x 3..13; truck yard x 1..16, y -18..-5


def frigo_lot2(acc, tier):
    x0, x1, y0, y1 = -GW / 2, GW / 2, -GD / 2, GD / 2
    rbox(acc, (GW, GD, .06), (0, 0, -.02), X_ASPH, .01, 1)
    rbox(acc, (GW + .3, .3, .18), (0, y0 - .15, .09), KERB, .03, 2)
    rbox(acc, (12.0, 5.5, .05), (-10.5, -16.0, .02), X_PAVER, .01, 1)       # van parking in front of the store
    if tier == 1:
        lawn(acc, -16.0, 16.0, 0.5, 18.0, [(-12, 6), (-4, 14), (6, 4), (13, 13)], 51)
    elif tier == 2:
        lawn(acc, -16.0, -1.5, 0.5, 18.0, [(-12, 6), (-5, 14)], 51)
    fence(acc, x0 + .3, y0 + .3, x1 - .3, y0 + .3, gaps=((20 / 34, 30 / 34),))
    fence(acc, x0 + .3, y0 + .3, x0 + .3, y1 - .3)
    fence(acc, x1 - .3, y0 + .3, x1 - .3, y1 - .3)
    fence(acc, x0 + .3, y1 - .3, x1 - .3, y1 - .3)
    if tier >= 2:
        for k in range(4):
            rbox(acc, (.12, 5.5, .012), (2.4 + k * 3.8, -7.0, .026), LINE_W, .004, 1)
        lane_marks(acc, 8.0, -18.0, 8.0, -11.0)


def g_t1(acc, root):
    """T1 — Entreposto de carnes: a small cold store with a brick base, white insulated upper walls and a navy
    barrel roof; a reefer door with a cushion, a shop door with an awning, condensers on a side platform,
    a small reefer van."""
    x0, x1, y0, y1, h = -16.0, -5.0, -12.0, -2.0, 4.4
    door = (-14.4, -11.4, .1, 3.3)
    for axis, line, out, u0, u1, hl in (("x", y0, -1, x0, x1, [door, (-8.4, -7.2, 0, 2.2)]), ("x", y1, 1, x0, x1, ()),
                                        ("y", x0, -1, y0, y1, ()), ("y", x1, 1, y0, y1, ())):
        def B(ua, ub, va, vb, za, zb, key, r=.01, seg=1, axis=axis, line=line, out=out):
            wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
        for a, b in spans(u0, u1, [(p, q) for p, q, _, _ in hl]):
            B(a, b, -.32, 0, 0, 1.4, X_BRICK, .01)
            B(a, b, -.32, 0, 1.4, h, COLD_W, .01)
            B(a, b, 0, .08, 1.38, 1.5, RED_STRIPE, .01)
        for a, b, za, zb in hl:
            B(a, b, -.32, 0, zb, h, COLD_W, .01)
        n = int((u1 - u0) / 1.1)
        for k in range(1, n):
            uu = u0 + k * (u1 - u0) / n
            if not any(p - .1 < uu < q + .1 for p, q, _, _ in hl):
                B(uu - .02, uu + .02, 0, .03, 1.5, h - .1, COLD_RIB, .005)
    arch_roof(acc, x0, x1, y0, y1, h, 1.8, C(NAVY), 14)
    roll_door(acc, "x", y0, -1, -12.9, 2.8, 3.2, cold=True)
    rframe(acc, 1.2, 2.2, .1, .08, (-7.8, y0 - .02, 1.1), C(STEEL), .02)
    rpanel(acc, 1.04, 2.06, .03, (-7.8, y0 - .05, 1.05), C("8FB2C4"), .02)
    rbox(acc, (2.2, 1.2, .14), (-7.8, y0 - .6, 2.7), RED_STRIPE, .04, 2)
    for k in range(5):
        rbox(acc, (.44, 1.22, .16), (-8.68 + k * .44, y0 - .6, 2.62), (C(WHITE) if k % 2 else RED_STRIPE), .02, 1)
    # condensers on a steel platform on the west side
    rbox(acc, (1.6, 6.0, .15), (x0 - .9, -7.0, 2.2), C(STEEL), .02, 1)
    for yy in (-9.3, -4.7):
        for s in (-1, 1):
            lathe(acc, [(0, 0), (.05, 0), (.05, 2.15), (0, 2.16)], (x0 - .2 - (s + 1) * .6, yy, 0), C(STEEL), 6, 0)
        condenser(acc, x0 - .9, yy, 2.28, 1.4, 1.4, 1, yaw=90)
    board(root, "BoardT1", (-10.5, y0 - .3, 4.7), 4.6, .75)
    van(acc, -9.0, -16.0, 0, reefer=True)


def g_t2(acc, root):
    """T2 — Frigorífico: a tall white cold store on the right (three reefer docks under a long navy canopy on the
    truck yard, a raised dock platform), a screened plant deck on the roof, a brick compressor house behind with
    two cooling towers on its side, a reefer truck at the middle dock."""
    x0, x1, y0, y1, h = 1.0, 16.0, -2.0, 12.0, 9.5
    xs = (4.0, 8.0, 12.0)
    cold_box(acc, x0, x1, y0, y1, h, {"S": [(x - 1.5, x + 1.5, .1, 3.6) for x in xs]})
    for x in xs:
        roll_door(acc, "x", y0, -1, x, 3.0, 3.5, cold=True)
    rbox(acc, (x1 - x0, 1.4, .9), ((x0 + x1) / 2, y0 - .7, .45), X_CONC, .03, 2)
    rbox(acc, (x1 - x0 + .6, 3.2, .3), ((x0 + x1) / 2, y0 - 1.6, 5.0), C(NAVY), .05, 3)
    rbox(acc, (x1 - x0 + .64, 3.24, .08), ((x0 + x1) / 2, y0 - 1.6, 4.82), C(GOLD), .02, 1)
    for xx in (x0 + .5, (x0 + x1) / 2, x1 - .5):
        tube(acc, [(xx, y0 - 3.1, 5.1), (xx, y0 + .05, 7.0)], .04, C(STEEL), seg=6)
    # screened plant deck on the roof: louvred screen round four condensers
    sx0, sx1, sy0, sy1 = 3.0, 14.0, 2.0, 10.0
    for k in range(int((sx1 - sx0) / .3)):
        xx = sx0 + k * .3
        rbox(acc, (.08, .04, 1.4), (xx, sy0, h + .8), STEEL_BLUE, .01, 1)
        rbox(acc, (.08, .04, 1.4), (xx, sy1, h + .8), STEEL_BLUE, .01, 1)
    for k in range(int((sy1 - sy0) / .3)):
        yy = sy0 + k * .3
        rbox(acc, (.04, .08, 1.4), (sx0, yy, h + .8), STEEL_BLUE, .01, 1)
        rbox(acc, (.04, .08, 1.4), (sx1, yy, h + .8), STEEL_BLUE, .01, 1)
    for k in range(4):
        condenser(acc, 5.6 + (k % 2) * 5.6, 4.0 + (k // 2) * 4.0, h - .05, 3.0, 1.5, 3)
    # compressor house (brick) and cooling towers on the visible east side
    brick_wall(acc, "x", 13.2, -1, 2.0, 11.0, 4.4, [(5.6, 7.4, 0, 2.3)])
    brick_wall(acc, "x", 17.6, 1, 2.0, 11.0, 4.4)
    brick_wall(acc, "y", 2.0, -1, 13.2, 17.6, 4.4)
    brick_wall(acc, "y", 11.0, 1, 13.2, 17.6, 4.4)
    rbox(acc, (9.0, 4.4, .25), (6.5, 15.4, 4.3), FLAT_ROOF, .02, 1)
    person_door(acc, "x", 13.2, -1, 6.5)
    cooling_tower(acc, 14.0, 15.2, 2.4, 3.4)
    pipe_run(acc, [(11.0, 15.2, 3.0), (12.8, 15.2, 3.0)], .16)
    board(root, "BoardT2", (8.5, y0 - .32, 7.7), 10.0, 1.4)
    r, _ = truck(f"{root.name}_Reefer", (0, 0, 0), reefer=True)
    r.parent = root
    r.location = Vector((8.0, y0 - 1.4 - .8 - 2.4 * .75, 0))
    r.scale = (.75, .75, .75)


def g_t3(acc, root):
    """T3 — Frigorífico industrial: a grey-blue processing plant on the lawn (a two-level volume with a glass
    ribbon and a stepped front), round ammonia tanks, a steam stack, a glass office tower at the front-left corner
    of the lot (away from the truck yard), a covered bridge to the cold store, a second reefer truck."""
    x0, x1, y0, y1, h = -16.0, -2.0, 1.5, 17.0, 8.0
    holes = {"E": [(9.0, 12.0, .1, 3.6)]}
    for axis, line, out, u0, u1, hl in (("x", y0, -1, x0, x1, ()), ("x", y1, 1, x0, x1, ()),
                                        ("y", x0, -1, y0, y1, ()), ("y", x1, 1, y0, y1, holes["E"])):
        def B(ua, ub, va, vb, za, zb, key, r=.01, seg=1, axis=axis, line=line, out=out):
            wbox(acc, axis, line, ua, ub, out * va, out * vb, za, zb, key, r, seg)
        for a, b in spans(u0, u1, [(p, q) for p, q, _, _ in hl]):
            B(a, b, -.32, 0, 0, h, STEEL_BLUE, .01)
        for a, b, za, zb in hl:
            B(a, b, -.32, 0, zb, h, STEEL_BLUE, .01)
        z = .9
        while z < h - .8:
            for a, b in spans(u0, u1, [(p - .05, q + .05) for p, q, za, zb in hl if za - .05 < z < zb + .05]):
                B(a, b, 0, .03, z, z + .05, STEEL_BLUE_L, .005)
            z += .5
        for a, b in spans(u0, u1, [(p - .05, q + .05) for p, q, _, _ in hl]):
            B(a, b, 0, .07, 0, .8, C(NAVY), .02, 2)
        B(u0 - .03, u1 + .03, 0, .14, h - .7, h, C(WHITE), .03, 2)
        B(u0 - .06, u1 + .06, -.37, .2, h, h + .1, C(GOLD), .03, 2)
    roll_door(acc, "y", x1, 1, 10.5, 3.0, 3.5, cold=True)
    window_row(acc, "x", y0, -1, x0 + 1.0, x1 - 1.0, 4.2, 5.8, 10)
    window_row(acc, "y", x1, 1, 2.5, 8.0, 4.2, 5.8, 4)
    flat_roof(acc, x0, x1, y0, y1, h - .45, 2)
    # a lower stepped front volume (staff entrance and canteen)
    rbox(acc, (8.0, 3.0, 3.6), (-10.0, y0 - 1.5, 1.8), C(WHITE), .05, 2)
    rbox(acc, (8.1, 3.1, .3), (-10.0, y0 - 1.5, 3.6), C(NAVY), .04, 2)
    rbox(acc, (7.0, .06, 1.6), (-10.0, y0 - 3.02, 2.0), WIN, .02, 1)
    conveyor_bridge(acc, (-2.0, 6.0), (1.0, 6.0), 6.0, 1.6)
    for k in range(3):
        condenser(acc, -13.0 + k * 4.4, 13.0, h - .05, 3.0, 1.5, 3)
    # ammonia tanks behind the plant
    for tx in (-11.0, -6.0):
        hz_tank(acc, tx, 18.15, .7, 3.6)
    chimney(acc, -.4, 16.6, .45, 13)
    # glass office tower at the front-left corner (the trucks keep the right side of the lot)
    ox, oy = -1.5, -15.4
    rbox(acc, (5.0, 4.4, 10.0), (ox, oy, 5.0), "C_5E6E7A", .03, 1)
    for zb in (.5, 3.7, 6.9):
        window_row(acc, "x", oy - 2.2, -1, ox - 2.2, ox + 2.2, zb, zb + 2.5, 4)
        window_row(acc, "y", ox - 2.5, -1, oy - 1.9, oy + 1.9, zb, zb + 2.5, 3)
    rbox(acc, (5.3, 4.7, .5), (ox, oy, 10.25), C(NAVY), .05, 2)
    rbox(acc, (5.4, 4.8, .1), (ox, oy, 10.55), C(GOLD), .02, 1)
    logo_disc(root, acc, "T3", (ox, oy - 2.42, 11.7), R=.85)
    r, _ = truck(f"{root.name}_Reefer2", (0, 0, 0), reefer=True)
    r.parent = root
    r.location = Vector((12.0, -2.0 - 1.4 - .8 - 2.4 * .75, 0))
    r.scale = (.75, .75, .75)


FRIGO2 = [
    ("T1", "Entreposto de carnes", [g_t1]),
    ("T2", "Frigorífico", [g_t1, g_t2]),
    ("T3", "Frigorífico industrial", [g_t1, g_t2, g_t3]),
]


def frigo2(tier, loc=(0, 0, 0)):
    tid, label, parts = FRIGO2[tier - 1]
    root = new_root(f"Frigo2{tid}", loc)
    acc = Acc(root.name)
    frigo_lot2(acc, tier)
    for p in parts:
        p(acc, root)
    finish(root, acc)
    return root


# --------------------------------------------------------------------------------------------- previews
def setup2(scene):
    setup(scene)
    rk_core.PREVIEW = QA_IND2
    textures()
    fl = bpy.data.objects.get("RK_Floor")
    if fl:
        fl.scale = (20, 20, 1)
    w = bpy.context.scene.world
    if w and w.node_tree:
        w.node_tree.nodes["Background"].inputs[0].default_value = (.62, .62, .6, 1)


def shoot_factory2():
    out, info = [], []
    for t in range(1, 6):
        setup2("Industry Factory 2")
        root = factory2(t)
        info.append(f"factory2 T{t}: {tri_count(root)} tris")
        out.append(rk_core.shoot(f"factory2_T{t}", (0, 0, 3), GAMECAM, 112, 36, (1800, 1100)))
    setup2("Industry Factory 2")
    factory2(1)
    out.append(rk_core.shoot("factory2_T1_close", (-14, -21, 3), (-.45, -.85, .55), 26, 36, (1800, 1100)))
    setup2("Industry Factory 2")
    factory2(5)
    out.append(rk_core.shoot("factory2_T5_front", (0, -6, 6), (-.2, -1, .5), 78, 36, (1800, 1100)))
    return out, info


def shoot_frigo2():
    out, info = [], []
    for t in range(1, 4):
        setup2("Industry Frigo 2")
        root = frigo2(t)
        info.append(f"frigo2 T{t}: {tri_count(root)} tris")
        out.append(rk_core.shoot(f"frigo2_T{t}", (0, 0, 2.5), GAMECAM, 76, 36, (1800, 1100)))
    setup2("Industry Frigo 2")
    frigo2(3)
    out.append(rk_core.shoot("frigo2_T3_front", (0, -4, 3), (-.25, -1, .45), 52, 36, (1800, 1100)))
    return out, info
