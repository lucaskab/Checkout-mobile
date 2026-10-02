
# lot_build.py - the four lot models
import bpy, math, random, sys, importlib
sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
import era_kit as k, lot_kit as L
from mathutils import Vector, Matrix

def build_casa():
    c = L.clear("LOT Casa"); M = L.mats()
    bpy.context.scene.cursor.location = (0, 0, 0)
    m_wall = L.plaster("LOT_CasaWall", (.93, .80, .62, 1), under=(.60, .48, .40, 1), damage=.55, brick_under=True, zband=.45, band=(.45, .55, .62, 1))
    m_gable = L.plaster("LOT_CasaGable", (.93, .80, .62, 1), under=(.60, .48, .40, 1), damage=.35, brick_under=True)
    m_tile = L.rooftiles("LOT_CasaTiles")
    m_ridge = k.mat("LOT_CasaRidge", (.58, .32, .24, 1), rough=.85, var=.12, scale=10)
    W, D, H, T = 6.0, 5.0, 2.7, .25
    L.pad("CASA_pad", 7.0, 6.0, c)
    # walls (origin at ground so the painted band / damage gradient use world Z)
    L.gbox("CASA_wallF", (W, T, H), (0, -D / 2 + T / 2, H / 2), m_wall, c=c)
    L.gbox("CASA_wallB", (W, T, H), (0, D / 2 - T / 2, H / 2), m_wall, c=c)
    L.gbox("CASA_wallL", (T, D - 2 * T, H), (-W / 2 + T / 2, 0, H / 2), m_wall, c=c)
    L.gbox("CASA_wallR", (T, D - 2 * T, H), (W / 2 - T / 2, 0, H / 2), m_wall, c=c)
    L.gbox("CASA_inner", (W - .5, D - .5, H - .3), (0, 0, (H - .3) / 2), M["shadow"], bevel=0, c=c)
    # gables
    ZR = 4.3
    for x, nm in ((-W / 2 + T / 2, "L"), (W / 2 - T / 2, "R")):
        L.poly_prism("CASA_gable" + nm, [(-D / 2, H - .01), (D / 2, H - .01), (0, ZR)], T, (x, 0, 0), m_gable, axis='X', c=c)
    # roof with a hole on the front slope (right side) and a small one at the back
    roof, pitch, Ls = L.gable_roof("CASA_roof", 0, 0, 6.9, 5.9, 2.75, 4.35, .09, m_tile,
                                   holes_f=[(0.9, 0.95, 2.2, 2.05)], holes_b=[(-2.3, 1.3, -1.5, 1.95)], c=c, ridge_cap=m_ridge)
    # slipped tiles lying on the roof near the hole + a broken tile on the ground
    Mf = roof[0].matrix_world
    for i, (u, v, a) in enumerate(((0.55, 0.6, .3), (2.45, 0.7, -.4), (1.5, 2.25, .2))):
        o = k.box(f"CASA_tile{i}", (.3, .24, .03), (u, v, .07), m_ridge, rot=(0, 0, a), bevel=.004, seg=1, c=c)
        o.matrix_world = Mf @ o.matrix_world
    k.box("CASA_tileG", (.3, .24, .03), (2.1, -3.2, .03), m_ridge, rot=(0, 0, .5), bevel=.004, seg=1, c=c)
    k.box("CASA_tileG2", (.2, .24, .03), (2.35, -3.0, .03), m_ridge, rot=(.3, 0, 1.2), bevel=.004, seg=1, c=c)
    # chimney at the back slope
    L.gbox("CASA_chim", (.45, .45, 1.1), (1.9, 1.0, 3.9), m_gable, bevel=.012, c=c)
    L.gbox("CASA_chimTop", (.55, .55, .10), (1.9, 1.0, 4.45), M["concreteD"], bevel=.012, c=c)
    # door (front, left): dark opening, crooked metal door ajar, concrete step
    yF = -D / 2
    k.box("CASA_doorHole", (1.0, .10, 2.15), (-1.4, yF + .02, 1.075), M["dark"], bevel=0, c=c)
    door = k.box("CASA_door", (.92, .05, 2.05), (0, 0, 0), M["door"], bevel=.01, seg=2, c=c)
    door.data.transform(Matrix.Translation((.46, 0, 1.025)))   # hinge at the left edge
    door.location = (-1.9, yF - .03, 0.03); door.rotation_euler = (0, .06, math.radians(-42))
    k.box("CASA_doorFrame", (1.12, .06, .08), (-1.4, yF - .02, 2.2), M["frame"], bevel=.006, seg=1, c=c)
    k.box("CASA_step", (1.4, .5, .14), (-1.4, yF - .3, .07), M["concrete"], bevel=.02, seg=2, c=c)
    # boarded windows
    L.boarded_window("CASA_winF", 1.2, 1.1, (1.4, yF, 1.55), M["glass"], M["frame"], M["wood"], (0, -1, 0), c=c, seed=1)
    L.boarded_window("CASA_winL", 1.0, 1.0, (-W / 2, -.4, 1.6), M["glass"], M["frame"], M["wood"], (-1, 0, 0), c=c, seed=2)
    L.boarded_window("CASA_winR", 1.0, 1.0, (W / 2, .6, 1.6), M["glass"], M["frame"], M["wood"], (1, 0, 0), c=c, seed=3, n_planks=2)
    L.boarded_window("CASA_winB", 1.2, 1.0, (-.8, D / 2, 1.6), M["glass"], M["frame"], M["wood"], (0, 1, 0), c=c, seed=4)
    # gutter along the front eave, hanging loose at the right end; rusty downpipe at the left corner
    yE = -5.9 / 2 - .04
    k.tube("CASA_gutter", (-3.4, yE, 2.70), (1.6, yE - .05, 2.15), .055, M["gutter"], verts=8, c=c)
    k.tube("CASA_gutterBr", (-3.45, yE + .08, 2.71), (-3.45, yE - .02, 2.71), .02, M["rust"], verts=6, c=c)
    k.tube("CASA_down", (-3.1, yE + .1, 2.65), (-3.2, yE + .2, .25), .045, M["gutter"], verts=8, c=c)
    # props: tyres by the right wall, two crates at the left wall, a dead bush and weeds
    L.tire("CASA_tire0", (3.45, 1.9, .10), M["tire"], rot=(0, 0, .2), c=c)
    L.tire("CASA_tire1", (3.45, 1.9, .30), M["tire"], rot=(0, .08, .9), c=c)
    L.tire("CASA_tire2", (3.3, -1.9, .32), M["tire"], rot=(math.radians(80), 0, .3), c=c)
    k.crate("CASA_crate0", (-3.4, 1.2, 0), m=M["wood"], c=c, rot_z=.2)
    k.crate("CASA_crate1", (-3.4, 1.2, .26), m=M["wood"], c=c, rot_z=-.15)
    k.crate("CASA_crate2", (-3.35, .55, 0), m=M["wood"], c=c, rot_z=1.3)
    L.dead_bush("CASA_bush", (-2.8, -2.55, 0), M["twig"], r=.75, n=24, c=c, seed=4)
    L.dead_bush("CASA_bush2", (3.1, 2.75, 0), M["twig"], r=.35, c=c, seed=9)
    pts = [(-3.2, -2.2), (-2.2, -2.75), (-.3, -2.8), (.6, -2.65), (2.2, -2.75), (3.2, -2.5), (3.3, -1.0), (3.35, .5), (3.2, 2.7), (2.3, 2.8),
           (.4, 2.7), (-1.5, 2.8), (-3.2, 2.5), (-3.3, -.3), (-3.3, -1.3), (1.6, -2.4), (3.0, -2.0), (-1.1, -2.6)]
    L.scatter_tufts("CASA", pts, c, seed=11)
    for o in c.objects:
        if o.name.startswith(("CASA_tire", "CASA_tileG")): L.ground(o)
    for i, (x, y, a) in enumerate(((2.8, -2.6, .3), (2.95, -2.45, 1.0), (-2.5, 2.6, .8))):
        L.brick(f"CASA_brick{i}", (x, y, .035), M["brick"], rot=(0, 0, a), c=c)
    return c


def build_galpao():
    c = L.clear("LOT Galpao"); M = L.mats()
    bpy.context.scene.cursor.location = (0, 0, 0)
    base, rust = (.68, .70, .68, 1), (.52, .27, .12, 1)
    mX = L.corrugated("LOT_CorrX", base, rust, .40, axis='X')
    mY = L.corrugated("LOT_CorrY", base, rust, .40, axis='Y')
    mR = L.corrugated("LOT_CorrRoof", (.68, .70, .68, 1), rust, .28, axis='X')
    mZ = L.corrugated("LOT_CorrDoor", (.60, .63, .62, 1), rust, .35, axis='Z', pitch=.11)
    mS = k.mat("LOT_Steel", (.22, .24, .27, 1), rough=.6, var=.08, scale=10)
    W, D, H, T = 4.1, 6.6, 2.7, .05
    L.pad("GALP_pad", 4.5, 7.0, c)
    yF = -D / 2
    # corner / mid posts and top girts
    for x in (-W / 2, W / 2):
        for y in (-D / 2, 0, D / 2):
            L.gbox(f"GALP_post", (.12, .12, H + .05), (x, y, (H + .05) / 2), mS, bevel=.006, seg=1, c=c)
    for y in (-D / 2, D / 2):
        L.gbox("GALP_girt", (W + .12, .08, .08), (0, y, H + .04), mS, bevel=.006, seg=1, c=c)
    for x in (-W / 2, W / 2):
        L.gbox("GALP_girt", (.08, D, .08), (x, 0, H + .04), mS, bevel=.006, seg=1, c=c)
    # walls: front with roll-up door opening, back full, left full, right with a missing sheet
    dw, dh = 2.6, 2.3
    L.gbox("GALP_wallF", ((W - dw) / 2, T, H), (-W / 4 - dw / 4, yF, H / 2), mX, bevel=.004, seg=1, c=c)
    L.gbox("GALP_wallF", ((W - dw) / 2, T, H), (W / 4 + dw / 4, yF, H / 2), mX, bevel=.004, seg=1, c=c)
    L.gbox("GALP_wallF", (dw + .02, T, H - dh), (0, yF, dh + (H - dh) / 2), mX, bevel=.004, seg=1, c=c)
    L.gbox("GALP_wallB", (W, T, H), (0, D / 2, H / 2), mX, bevel=.004, seg=1, c=c)
    L.gbox("GALP_wallL", (T, D, H), (-W / 2, 0, H / 2), mY, bevel=.004, seg=1, c=c)
    g0, g1, gz = 0.7, 1.75, 1.95
    L.gbox("GALP_wallR", (T, g0 + D / 2, H), (W / 2, (-D / 2 + g0) / 2, H / 2), mY, bevel=.004, seg=1, c=c)
    L.gbox("GALP_wallR", (T, D / 2 - g1, H), (W / 2, (g1 + D / 2) / 2, H / 2), mY, bevel=.004, seg=1, c=c)
    L.gbox("GALP_wallR", (T, g1 - g0, H - gz), (W / 2, (g0 + g1) / 2, gz + (H - gz) / 2), mY, bevel=.004, seg=1, c=c)
    # bent loose sheet lying at the foot of the gap
    L.ground(k.box("GALP_sheet", (.04, 1.0, 1.3), (W / 2 + .27, 1.25, .65), mY, rot=(.06, math.radians(-20), .12), bevel=.004, seg=1, c=c))
    L.gbox("GALP_inner", (W - .3, D - .3, H - .2), (0, 0, (H - .2) / 2), M["shadow"], bevel=0, c=c)
    # gables (ridge along Y, so the triangles sit on the front / back walls)
    ZR = 3.38
    for y, nm in ((yF, "F"), (D / 2, "B")):
        L.poly_prism("GALP_gable" + nm, [(-W / 2, H - .02), (W / 2, H - .02), (0, ZR)], T, (0, y, 0), mX, axis='Y', c=c, bevel=.004)
    roof, pitch, Ls = L.gable_roof("GALP_roof", 0, 0, 7.0, 4.5, 2.74, 3.44, .05, mR, holes_b=[(1.1, 0.5, 2.1, 1.7)], ridge='Y', c=c,
                                   m_purlin=mS, ridge_cap=M["rust"])
    # roll-up door: dark opening, roll drum, half-open curtain with a bent bottom, guide rails
    k.box("GALP_doorHole", (dw, .12, dh), (0, yF + .03, dh / 2), M["dark"], bevel=0, c=c)
    k.cyl("GALP_roll", .17, dw + .2, (0, yF - .10, dh + .12), M["rust"], rot=(0, math.radians(90), 0), verts=14, bevel=.01, c=c)
    L.gbox("GALP_curtain", (dw - .04, .04, 1.05), (0, yF - .04, dh - .52), mZ, bevel=.004, seg=1, c=c)
    cb = k.box("GALP_curtainB", (dw - .04, .04, .5), (0, 0, 0), mZ, bevel=.004, seg=1, c=c)
    cb.data.transform(Matrix.Translation((0, 0, -.25))); cb.location = (0, yF - .06, dh - 1.05); cb.rotation_euler = (math.radians(-22), 0, 0)
    k.box("GALP_bar", (dw, .06, .07), (0, yF - .14, dh - 1.05 - .47), mS, bevel=.006, seg=1, c=c)
    for x in (-dw / 2 - .05, dw / 2 + .05):
        L.gbox("GALP_rail", (.08, .10, dh), (x, yF - .03, dh / 2), mS, bevel=.004, seg=1, c=c)
    # boarded window on the left wall, small vent on the back
    L.boarded_window("GALP_winL", .9, .7, (-W / 2, 1.3, 1.7), M["glass"], M["frame"], M["wood"], (-1, 0, 0), c=c, seed=5, n_planks=2)
    # props
    L.drum("GALP_drum", (1.55, -3.2, 0), M["drum"], rot=(0, 0, .4), c=c)
    L.ground(L.drum("GALP_drum2", (2.22, -2.3, .29), M["rust"], rot=(math.radians(90), 0, .15), c=c))
    L.ground(L.pallet("GALP_pallet", (2.33, 2.6, .5), M["wood"], rot=(0, math.radians(78), 0), c=c))
    L.tire("GALP_tire0", (-1.95, -3.05, .10), M["tire"], rot=(0, 0, .2), c=c)
    L.tire("GALP_tire1", (-1.95, -3.05, .30), M["tire"], rot=(0, .05, 1.1), c=c)
    L.tire("GALP_tire2", (-2.0, 2.6, .32), M["tire"], rot=(0, math.radians(82), .4), c=c)
    L.dead_bush("GALP_bush", (-1.9, 3.1, 0), M["twig"], r=.45, n=18, c=c, seed=7)
    pts = [(-1.2, -3.3), (0.0, -3.35), (1.0, -3.3), (2.15, -3.2), (2.2, -1.6), (2.2, -.2), (2.15, 1.9), (1.4, 3.3), (.2, 3.35), (-1.0, 3.3),
           (-2.15, 1.5), (-2.15, -.2), (-2.1, -1.8), (-2.15, .6), (2.1, 3.3), (-.6, -3.3)]
    L.scatter_tufts("GALP", pts, c, seed=21)
    for o in c.objects:
        if o.name.startswith(("GALP_tire", "GALP_brick")): L.ground(o)
    for i, (x, y, a) in enumerate(((-1.4, -3.15, .3), (-1.15, -3.0, 1.1))):
        L.brick(f"GALP_brick{i}", (x, y, .035), M["brick"], rot=(0, 0, a), c=c)
    return c


def build_entulho():
    c = L.clear("LOT Entulho"); M = L.mats()
    bpy.context.scene.cursor.location = (0, 0, 0)
    rnd = random.Random(3)
    m_rub = k.mat("LOT_Rubble", (.52, .48, .42, 1), rough=.95, var=.22, scale=5, bump=.5)
    L.pad("ENT_pad", 3.0, 2.5, c, t=.04)
    mound = k.ball("ENT_mound", 1.0, (.15, .1, -.05), m_rub, sub=2, scale=(1.25, .95, .40), c=c)
    L.clip_below(mound, -.01)
    for p in mound.data.polygons: p.use_smooth = False
    # concrete chunks and bricks over the mound
    for i in range(13):
        a = rnd.uniform(0, 6.3); r = rnd.uniform(.15, 1.05)
        x, y = .15 + r * math.cos(a) * 1.1, .1 + r * math.sin(a) * .85
        h = max(0.0, .36 * (1 - (r / 1.15) ** 2))
        L.chunk(f"ENT_chunk{i}", (x, y, h + .08), M["concrete"] if i % 3 else M["concreteD"], s=rnd.uniform(.16, .30), c=c, seed=i)
    for i in range(18):
        a = rnd.uniform(0, 6.3); r = rnd.uniform(.2, 1.3)
        x, y = .15 + r * math.cos(a) * 1.1, .1 + r * math.sin(a) * .9
        h = max(0.0, .36 * (1 - (r / 1.15) ** 2))
        L.brick(f"ENT_brick{i}", (x, y, h + .035), M["brick"], rot=(rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), rnd.uniform(0, 6)), c=c)
    # bent rebar
    for j, pts in enumerate((((-.4, .3, .25), (-.1, .5, .85), (.35, .45, 1.0)), ((.6, -.2, .3), (.8, .1, .75), (.7, .5, .95)))):
        for a, b in zip(pts[:-1], pts[1:]):
            k.tube(f"ENT_rebar{j}", a, b, .014, M["rebar"], verts=5, c=c)
        k.ball(f"ENT_rebarJ{j}", .016, pts[1], M["rebar"], sub=1, c=c)
    # old sofa, one cushion missing, slumped on the mound edge
    mf = M["fabric"]
    parts = [k.box("ENT_sofaBase", (1.5, .75, .40), (0, 0, .20), mf, bevel=.03, seg=2),
             k.box("ENT_sofaBack", (1.5, .22, .50), (0, .27, .62), mf, bevel=.03, seg=2),
             k.box("ENT_sofaArm", (.18, .75, .58), (-.66, 0, .29), mf, bevel=.03, seg=2),
             k.box("ENT_sofaArm", (.18, .75, .58), (.66, 0, .29), mf, bevel=.03, seg=2),
             k.box("ENT_sofaCush", (.62, .55, .14), (-.24, -.06, .47), mf, bevel=.03, seg=2),
             k.box("ENT_sofaFoam", (.60, .52, .05), (.30, -.06, .42), M["foam"], bevel=.01, seg=1)]
    sofa = k.join(parts, "ENT_sofa", origin=(0, 0, 0))
    sofa.location = (-.65, -.35, .06); sofa.rotation_euler = (math.radians(6), math.radians(-9), math.radians(28))
    k.link(sofa, c); L.ground(sofa, .0)
    L.tire("ENT_tire0", (.95, -.75, .10), M["tire"], rot=(0, 0, .3), c=c)
    L.tire("ENT_tire1", (.55, .55, .50), M["tire"], rot=(math.radians(70), 0, 1.2), c=c)
    k.cyl("ENT_bucket", .13, .30, (1.15, .65, .13), M["drum"], rot=(math.radians(100), 0, .7), verts=12, bevel=.01, r2=.11, c=c)
    L.dead_bush("ENT_bush", (-1.1, .75, 0), M["twig"], r=.4, n=16, c=c, seed=12)
    pts = [(-1.3, -1.0), (-.6, -1.1), (.3, -1.1), (1.3, -.3), (1.35, .9), (.6, 1.1), (-.4, 1.1), (-1.35, .1), (1.2, -1.05), (-1.3, 1.1), (0.0, .95)]
    L.scatter_tufts("ENT", pts, c, seed=31, dry_every=2)
    for o in c.objects:
        if o.name.startswith(("ENT_tire", "ENT_bucket")): L.ground(o)
    return c


def build_armazem():
    c = L.clear("LOT Armazem"); M = L.mats()
    bpy.context.scene.cursor.location = (0, 0, 0)
    m_wall = L.plaster("LOT_ArmWall", (.84, .80, .70, 1), under=(.60, .50, .42, 1), damage=.45, brick_under=True, zband=1.3, band='brick', crack_scale=2.6, crack_amount=.3)
    m_gable = L.plaster("LOT_ArmGable", (.84, .80, .70, 1), under=(.60, .50, .42, 1), damage=.35, brick_under=True, crack_scale=2.6, crack_amount=.3)
    m_sign = L.plaster("LOT_ArmSign", (.95, .94, .89, 1), under=(.84, .80, .70, 1), damage=.35, cracks=False)
    m_signB = k.mat("LOT_ArmSignBorder", (.34, .40, .52, 1), rough=.85, var=.10, scale=10)
    mR = L.corrugated("LOT_CorrRoofB", (.66, .68, .66, 1), (.52, .27, .12, 1), .30, axis='X')
    mDoor = L.corrugated("LOT_CorrDoorB", (.36, .48, .50, 1), (.52, .27, .12, 1), .45, axis='X')
    mS = k.mat("LOT_Steel", (.22, .24, .27, 1), rough=.6, var=.08, scale=10)
    W, D, H, T = 15.0, 9.0, 4.6, .3
    L.pad("ARM_pad", 16.0, 11.6, c, t=.05)   # the building sits 0.8 m back so the dock stays inside the pad
    yF = -D / 2
    L.gbox("ARM_wallF", (W, T, H), (0, yF + T / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("ARM_wallB", (W, T, H), (0, D / 2 - T / 2, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("ARM_wallL", (T, D - 2 * T, H), (-W / 2 + T / 2, 0, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("ARM_wallR", (T, D - 2 * T, H), (W / 2 - T / 2, 0, H / 2), m_wall, bevel=.015, c=c)
    L.gbox("ARM_inner", (W - .6, D - .6, H - .4), (0, 0, (H - .4) / 2), M["shadow"], bevel=0, c=c)
    # pilasters + lintel beam on the front and back
    for y, s in ((yF, -1), (D / 2, 1)):
        for x in (-7.4, -1.0, 2.0, 7.4):
            L.gbox("ARM_pil", (.4, .14, H + .15), (x, y + s * .07, (H + .15) / 2), M["concreteD"], bevel=.012, c=c)
        L.gbox("ARM_beam", (W, .10, .22), (0, y + s * .05, 3.2), M["concreteD"], bevel=.012, c=c)
    for x, s in ((-W / 2, -1), (W / 2, 1)):
        L.gbox("ARM_pil", (.14, .4, H + .15), (x + s * .07, 0, (H + .15) / 2), M["concreteD"], bevel=.012, c=c)
    # gables (ridge along X)
    ZR = 5.9
    for x, nm in ((-W / 2 + T / 2, "L"), (W / 2 - T / 2, "R")):
        L.poly_prism("ARM_gable" + nm, [(-D / 2, H - .02), (D / 2, H - .02), (0, ZR)], T, (x, 0, 0), m_gable, axis='X', c=c)
    roof, pitch, Ls = L.gable_roof("ARM_roof", 0, 0, 16.0, 10.0, 4.68, 5.98, .06, mR,
                                   holes_f=[(2.6, 1.0, 4.4, 2.7), (-6.0, 2.9, -4.6, 4.1)], holes_b=[(-1.2, 0.5, 0.6, 2.3)],
                                   c=c, m_purlin=mS, ridge_cap=M["rust"])
    # big sliding door (left half of the front), off its rail
    dx, dw, dh = -3.6, 4.2, 3.9
    k.box("ARM_doorHole", (dw, .14, dh), (dx, yF + .02, dh / 2), M["dark"], bevel=0, c=c)
    k.box("ARM_rail", (6.4, .10, .12), (dx + .5, yF - .18, dh + .35), mS, bevel=.008, seg=1, c=c)
    for x in (dx - 2.4, dx - .6, dx + 1.2, dx + 3.0):
        k.box("ARM_railBr", (.12, .22, .10), (x, yF - .09, dh + .35), mS, bevel=.006, seg=1, c=c)
    door = k.box("ARM_door", (dw + .2, .08, dh), (0, 0, 0), mDoor, bevel=.012, seg=2, c=c)
    door.location = (dx + 1.25, yF - .32, dh / 2 + .22); door.rotation_euler = (0, math.radians(-6), 0)
    for z in (-dh / 2 + .15, 0, dh / 2 - .15):
        b = k.box("ARM_doorBar", (dw + .2, .05, .10), (0, -.06, z), mS, bevel=.004, seg=1, c=c)
        b.parent = door
    for x in (-dw / 2, dw / 2):
        b = k.box("ARM_doorBar", (.10, .05, dh), (x, -.06, 0), mS, bevel=.004, seg=1, c=c)
        b.parent = door
    for x in (-1.6, .2):
        r = k.cyl("ARM_roller", .10, .06, (x, -.02, dh / 2 + .10), mS, rot=(math.radians(90), 0, 0), verts=10, c=c)
        r.parent = door
    # blank faded sign area above the big door
    # blank faded sign area on the right gable (the camera-facing end)
    sxw, szc = W / 2 + .02, 4.95
    k.box("ARM_sign", (.04, 4.4, .9), (sxw, 0, szc), m_sign, bevel=.01, seg=1, c=c)
    for sy, sz, sw, sh in ((0, .45, 4.4, .10), (0, -.45, 4.4, .10), (-2.2, 0, .10, .9), (2.2, 0, .10, .9)):
        k.box("ARM_signB", (.03, sw + .07, sh + .07), (sxw + .025, sy, szc + sz), m_signB, bevel=0, c=c)
    # loading dock on the right: platform with a broken corner, small door above it, chunk + rebar
    px = 4.6
    k.box("ARM_dockHole", (2.2, .14, 2.4), (px, yF + .02, .95 + 1.2), M["dark"], bevel=0, c=c)
    k.box("ARM_dock", (3.4, 1.4, .95), (px, yF - .7, .475), M["concrete"], bevel=.03, seg=2, c=c)
    k.box("ARM_dock2", (2.0, 1.0, .95), (px - .7, yF - 1.9, .475), M["concrete"], bevel=.03, seg=2, c=c)
    k.box("ARM_dockEdge", (3.4, .10, .10), (px, yF - 1.42, .93), mS, bevel=.006, seg=1, c=c)
    L.chunk("ARM_dockChunk", (px + 1.3, yF - 2.3, .22), M["concrete"], s=.42, c=c, seed=5)
    L.chunk("ARM_dockChunk2", (px + .6, yF - 2.55, .12), M["concreteD"], s=.25, c=c, seed=6)
    k.tube("ARM_dockBar", (px + .35, yF - 2.4, .55), (px + 1.1, yF - 2.75, .35), .014, M["rebar"], verts=5, c=c)
    k.tube("ARM_dockBar2", (px + .4, yF - 2.4, .60), (px + .9, yF - 2.5, .98), .014, M["rebar"], verts=5, c=c)
    L.poly_prism("ARM_ramp", [(0, 0), (-2.2, 0), (0, .95)], 1.4, (px - 1.7, yF - .7, 0), M["concrete"], axis='Y', c=c, bevel=.02)
    # clerestory windows: front right half, back full row, with missing panes
    missing = [(), ((1, 1),), ((0, 0), (2, 1)), ((2, 0),), ((1, 0), (1, 1)), ((0, 1),)]
    for i, x in enumerate((.6, 2.9, 5.2, 7.0 - .6)):
        if x > 6.0: continue
        L.pane_window(f"ARM_winF{i}", 1.5, .85, (x, yF, 3.95), M["glass"], M["frame"], (0, -1, 0), c=c, missing=missing[i % 6])
    for i, x in enumerate((-6.0, -3.6, -1.2, 1.2, 3.6, 6.0)):
        L.pane_window(f"ARM_winB{i}", 1.5, .85, (x, D / 2, 3.95), M["glass"], M["frame"], (0, 1, 0), c=c, missing=missing[(i + 2) % 6])
    for i, y in enumerate((-2.5, 0.0, 2.5)):
        L.pane_window(f"ARM_winL{i}", 1.5, .85, (-W / 2, y, 3.95), M["glass"], M["frame"], (-1, 0, 0), c=c, missing=missing[(i + 4) % 6])
        L.pane_window(f"ARM_winR{i}", 1.5, .85, (W / 2, y, 3.95), M["glass"], M["frame"], (1, 0, 0), c=c, missing=missing[(i + 1) % 6])
    # props: weeds, bricks, tyres, a drum
    pts = [(-7.6, -4.7), (-6.2, -4.85), (-4.9, -4.7), (-1.6, -4.8), (-.3, -4.75), (1.6, -4.85), (3.0, -4.7), (7.2, -4.8), (7.75, -3.2), (7.8, -1.0),
           (7.75, 1.4), (7.8, 3.6), (7.4, 4.8), (5.0, 4.85), (2.4, 4.8), (-.5, 4.85), (-3.3, 4.8), (-6.4, 4.85), (-7.8, 3.6), (-7.8, 1.0),
           (-7.75, -1.5), (-7.8, -3.4), (-6.8, -4.6), (6.6, -4.5), (-2.9, -4.9), (4.3, 4.7)]
    L.scatter_tufts("ARM", pts, c, seed=41, size=1.5)
    for o in c.objects:
        if o.name.startswith(("ARM_tire", "ARM_dockChunk")): L.ground(o)
    for o in c.objects:
        if o.parent is None and o.name != "ARM_pad": o.location.y += .8
    for i in range(7):
        rnd = random.Random(50 + i)
        L.brick(f"ARM_brick{i}", (-7.3 + rnd.uniform(-.4, .5), -4.1 + rnd.uniform(-.4, .5), .035 + (0.07 if i > 4 else 0)), M["brick"], rot=(0, 0, rnd.uniform(0, 3)), c=c)
    L.tire("ARM_tire0", (7.5, -3.9, .10), M["tire"], rot=(0, 0, .5), c=c)
    L.tire("ARM_tire1", (7.5, -3.9, .30), M["tire"], rot=(0, .06, 1.3), c=c)
    L.drum("ARM_drum", (-7.5, 2.4, 0), M["drum"], rot=(0, 0, .6), c=c)
    L.dead_bush("ARM_bush", (-3.0, -4.7, 0), M["twig"], r=.6, n=20, c=c, seed=15)
    L.dead_bush("ARM_bush2", (7.4, 2.4, 0), M["twig"], r=.5, n=18, c=c, seed=16)
    return c
