# works_power.py - event props v2, batch WORKS & POWER (Rua em obras, Queda de energia, Maquininha fora do ar).
# Same pipeline as vehicles.py: builders model at the origin, ground z=0, camera side -Y, vehicles drive along +X.
# Animated parts are their own props with the origin at the hinge (Obras_BackhoeArm, Energia_BucketBoom).
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
for pth in (ART, HERE):
    if pth not in sys.path: sys.path.insert(0, pth)
import events_kit as E
import era_kit as k
import works_kit as W
import vehicles as V
from vehicles import P, put, ROT
rad = math.radians

XM = {}
def mats():
    m = V.mats()
    if XM: return XM
    XM.update(m)
    XM["dirt"] = k.mat("EV_Dirt", (.44, .30, .17, 1), rough=.95, var=.28, scale=7, bump=.6)
    XM["mud"] = k.mat("EV_Mud", (.30, .20, .11, 1), rough=.9, var=.25, scale=6, bump=.5)
    XM["cut"] = k.mat("EV_CutAsphalt", (.19, .19, .20, 1), rough=.95, var=.22, scale=18, bump=.5)
    XM["puddle"] = k.mat("EV_Puddle", (.28, .34, .38, 1), rough=.06, var=.05, scale=4, metallic=.25)
    XM["gravel"] = k.mat("EV_Gravel", (.60, .58, .54, 1), rough=.95, var=.3, scale=24, bump=.7)
    XM["concP"] = k.mat("EV_ConcretePole", (.70, .69, .66, 1), rough=.9, var=.16, scale=5, bump=.35)
    XM["alum"] = k.mat("EV_Alum", (.80, .81, .83, 1), rough=.35, var=.05, scale=8, metallic=.45)
    XM["trafo"] = k.mat("EV_Trafo", (.42, .48, .45, 1), rough=.6, var=.1, scale=6, bump=.15)
    XM["ceramic"] = k.mat("EV_Ceramic", (.90, .88, .80, 1), rough=.3, var=.04, scale=6)
    XM["smoke"] = k.mat("EV_Smoke", (.58, .58, .61, 1), rough=1.0, var=.18, scale=3)
    XM["sparkW"] = k.emissive("EV_SparkWhite", (1.0, .97, .75, 1), 7.0)
    XM["sparkY"] = k.emissive("EV_SparkYellow", (1.0, .80, .20, 1), 5.0)
    XM["cableW"] = k.stripes("EV_CableWind", (.07, .07, .08, 1), (.15, .15, .17, 1), .014, axis='Y', rough=.7)
    XM["drum"] = k.wood("EV_DrumWood", (.78, .64, .42, 1), (.56, .42, .25, 1), scale=6, axis='Z')
    XM["pvc"] = k.mat("EV_PVC", (.93, .45, .12, 1), rough=.35, var=.05, scale=6)
    XM["greyD"] = k.mat("EV_GreyDark", (.36, .37, .39, 1), rough=.6, var=.06, scale=6)
    XM["ctoG"] = k.mat("EV_CtoGrey", (.52, .54, .56, 1), rough=.5, var=.05, scale=6)
    XM["sand"] = k.mat("EV_Sandbag", (.74, .64, .46, 1), rough=.95, var=.15, scale=10, bump=.3)
    return XM

def bar(p, name, a, b, w, h, m, bevel=.015, seg=1):
    """Box from a to b in the XZ plane: cross-section w (along Y) x h (normal to the bar)."""
    a, b = Vector(a), Vector(b); d = b - a; ln = math.hypot(d.x, d.z)
    return p.box(name, (ln, w, h), (a + b) / 2, m, rot=(0, -math.atan2(d.z, d.x), 0), bevel=bevel, seg=seg)

def ram(p, name, a, b, r, m_cyl, m_rod, verts=8):
    a, b = Vector(a), Vector(b)
    p.tube(name + "_c", a, a.lerp(b, .58), r, m_cyl, verts=verts)
    p.tube(name + "_r", a.lerp(b, .5), b, r * .55, m_rod, verts=verts)

def pin(p, name, loc, r=.06, w=.4, m=None):
    return p.cyl(name, r, w, loc, m or mats()["dark"], rot=(rad(90), 0, 0), verts=10)

def torus(p, name, R, r, loc, m, rot=(0, 0, 0), segs=20, rings=6):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=segs, minor_segments=rings, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; k.link(o, p.c); k.finish(o, m, 0); p.o.append(o); return o

def xform(objs, M):
    bpy.context.view_layer.update()
    for o in objs: o.matrix_world = M @ o.matrix_world
    return objs

def put_pivot(objs, piv, x=0, y=0, z=0, rot=0.0):
    """Place a pivoted prop (set_pivot(piv)) at x, y, z turning it `rot` about its own pivot."""
    piv = Vector(piv)
    return xform(objs, Matrix.Translation((x, y, z)) @ Matrix.Translation(piv) @ Matrix.Rotation(rot, 4, 'Z') @ Matrix.Translation(-piv))

def set_pivot(objs, piv=(0, 0, 0)):
    """Give every object the same origin `piv` (world) so the exporter's joined mesh pivots there."""
    piv = Vector(piv); bpy.context.view_layer.update()
    T = Matrix.Translation(piv)
    for o in objs:
        if o.type != 'MESH': continue
        o.data.transform(T.inverted() @ o.matrix_world)
        o.matrix_world = T
    return objs

# ================================================================== 1. RUA EM OBRAS
BH_HINGE = Vector((-2.45, 0, 1.40))   # rear arm hinge of the backhoe (world, body at the origin)

def backhoe(c):
    """Retroescavadeira: 5.9 x 2.3 x 2.95 m body + front loader, rear kingpost + stabilisers. Drives along +X."""
    p = P(c); m = mats(); Y, D, I, S, Ch, G = m["yellow"], m["dark"], m["ink"], m["steel"], m["chrome"], m["glass"]
    Rf, Rr, yf, yr = .50, .74, .88, .95
    # frame / chassis
    p.box("frame", (4.3, .9, .40), (-.05, 0, .82), I, bevel=.02)
    p.box("frame_low", (3.2, 1.15, .14), (.2, 0, .60), D, bevel=.01)
    p.box("axle_f", (.18, 1.9, .14), (1.65, 0, Rf + .02), D, bevel=.01)
    p.box("axle_r", (.3, 2.0, .3), (-1.25, 0, Rr + .02), D, bevel=.03)
    # engine hood (front)
    p.box("hood_base", (2.15, 1.32, .55), (1.45, 0, 1.20), Y, bevel=.06, seg=2)
    p.prism("hood", .40, 2.52, .40, 2.35, .64, 1.46, 1.90, Y, yt=.50, bevel=.05)
    p.box("hood_lid_line", (1.6, 1.0, .01), (1.3, 0, 1.905), I, bevel=0)
    for s in (-1, 1):
        for i in range(5):
            p.box("louver", (.18, .012, .32), (.75 + i * .33, s * .666, 1.18), I, bevel=0)
        p.lamp("headlamp", (.05, .2, .18), (2.54, s * .42, 1.45), m["lamp"])
        p.box("hood_stripe", (.9, .012, .07), (1.85, s * .67, 1.0), I, bevel=0)
    p.box("grille", (.05, .95, .5), (2.55, 0, 1.12), I, bevel=.02)
    for i in range(4):
        p.box("grille_bar", (.025, .85, .035), (2.58, 0, .94 + i * .12), m["grey"], bevel=0)
    p.box("bumper_f_pad", (.2, 1.3, .22), (2.5, 0, .72), D, bevel=.04, seg=2)
    p.cyl("exhaust", .045, .95, (.62, .50, 2.3), D, verts=8)
    p.cyl("exhaust_cap", .07, .09, (.62, .50, 2.78), D, verts=8)
    p.cyl("air_filter", .12, .42, (.95, -.48, 2.05), D, rot=(0, rad(90), 0), verts=10)
    p.box("filter_bracket", (.08, .18, .22), (1.1, -.48, 1.93), I, bevel=0)
    # cab: x -1.05..0.3, y +-.66, floor 1.32, roof 2.95; ROPS pillars black, glass all round
    cx, cw, z0, z1 = -.38, .66, 1.32, 2.95; cl = 1.35
    p.box("cab_floor", (cl, cw * 2, .12), (cx, 0, z0), D, bevel=.01)
    p.box("cab_skirt_f", (.06, cw * 2, .5), (cx + cl / 2 - .03, 0, z0 + .3), Y, bevel=.01)
    p.box("cab_skirt_b", (.06, cw * 2, .55), (cx - cl / 2 + .03, 0, z0 + .32), Y, bevel=.01)
    for s in (-1, 1):
        p.box("cab_skirt_s", (cl, .06, .5), (cx, s * (cw - .03), z0 + .3), Y, bevel=.01)
        for xx in (cx - cl / 2 + .035, cx + cl / 2 - .035):
            p.box("pillar", (.07, .07, z1 - z0), (xx, s * (cw - .035), (z0 + z1) / 2), I, bevel=.006)
        p.box("cab_side_glass", (cl - .14, .03, 1.0), (cx, s * (cw + .005), 2.33), G, bevel=.012)
        p.seam(cx + .05, s * (cw + .018), z0 + .55, z1 - .15, face=s)
        p.handle((cx - .3, s * (cw + .03), 2.0), face=s)
        p.mirror((cx + .45, s * (cw + .02), 2.4), s, arm=.22, h=.3, w=.16)
        p.box("cab_step", (.42, .22, .04), (cx + .1, s * 1.05, .95), S, bevel=.008)
        p.box("cab_step2", (.42, .22, .04), (cx + .1, s * 1.0, 1.3), S, bevel=.008)
        p.box("step_hanger", (.04, .04, .4), (cx + .3, s * 1.1, 1.12), I, bevel=0)
        p.box("roof_lamp", (.16, .1, .12), (cx + .5, s * .4, z1 + .1), m["lamp"], bevel=.01)
        p.box("roof_lamp_bz", (.18, .12, .14), (cx + .49, s * .4, z1 + .1), I, bevel=.006)
    p.box("cab_glass_f", (.03, cw * 2 - .14, 1.0), (cx + cl / 2 + .005, 0, 2.33), G, bevel=.012)
    p.box("cab_glass_b", (.03, cw * 2 - .14, 1.0), (cx - cl / 2 - .005, 0, 2.33), G, bevel=.012)
    p.box("cab_roof", (cl + .16, cw * 2 + .16, .11), (cx, 0, z1 + .02), Y, bevel=.035, seg=2)
    p.box("cab_roof_trim", (cl + .18, cw * 2 + .18, .04), (cx, 0, z1 - .035), I, bevel=.006)
    p.box("seat", (.5, .5, .5), (cx - .15, 0, 1.68), D, bevel=.05, seg=2)
    p.box("seat_back", (.12, .5, .55), (cx - .38, 0, 2.08), D, bevel=.04, seg=2)
    p.box("dash", (.25, 1.1, .28), (cx + .45, 0, 1.55), I, bevel=.02)
    p.cyl("wheel_col", .02, .35, (cx + .25, 0, 1.78), I, rot=(0, rad(-50), 0), verts=6)
    p.cyl("steer", .15, .025, (cx + .12, 0, 1.9), I, rot=(0, rad(-50), 0), verts=12)
    p.box("wiper", (.02, .45, .02), (cx + cl / 2 + .03, .15, 2.6), I, rot=(rad(-30), 0, 0), bevel=0)
    p.cyl("beacon_base", .09, .03, (cx - .4, 0, z1 + .09), D, verts=10)
    p.cyl("beacon", .07, .13, (cx - .4, 0, z1 + .17), m["amber"], verts=10, bevel=.012)
    # rear: kingpost mount + stabilisers
    p.box("rear_frame", (.55, 1.2, .65), (-2.15, 0, 1.08), Y, bevel=.04, seg=2)
    p.box("rear_hazard", (.03, 1.1, .2), (-2.43, 0, .9), m["hazard"], bevel=0)
    p.box("kingpost", (.32, .4, .85), (-2.42, 0, 1.25), D, bevel=.03)
    p.box("kingpost_top", (.4, .5, .12), (-2.42, 0, 1.7), D, bevel=.015)
    p.box("hyd_tank", (.6, .55, .55), (-1.75, -.0, 1.65), Y, bevel=.04, seg=2)
    p.box("tank_cap", (.1, .1, .06), (-1.6, .1, 1.95), I, bevel=.01)
    for s in (-1, 1):
        p.tube("stab", (-2.15, s * .55, 1.05), (-2.15, s * 1.42, .22), .085, Y, verts=8)
        p.tube("stab_ram", (-2.15, s * .45, 1.35), (-2.15, s * 1.1, .55), .04, Ch, verts=8)
        p.tube("stab_ram_c", (-2.15, s * .45, 1.35), (-2.15, s * .8, .92), .055, D, verts=8)
        p.box("stab_pad", (.42, .36, .08), (-2.15, s * 1.45, .06), D, bevel=.012)
        p.box("stab_pad_h", (.44, .06, .09), (-2.15, s * 1.6, .06), m["hazard"], bevel=0)
        # rear fenders + taillights
        p.box("fender", (1.75, .52, .07), (-1.25, s * yr, 2 * Rr + .12), Y, bevel=.012)
        p.box("fender_skirt", (1.75, .04, .28), (-1.25, s * (yr + .24), 2 * Rr - .02), Y, bevel=.01)
        p.box("fender_brace", (.06, .4, .4), (-.4, s * (yr - .05), 1.3), I, bevel=0)
        p.box("taillamp", (.05, .14, .14), (-2.44, s * .45, 1.42), m["tail"], bevel=.01)
        p.box("plate_bracket", (.03, .3, .1), (-2.44, 0, 1.15), I, bevel=0)
    p.plate(-2.47, 0, 1.15, "-X", "OBR 4A12")
    # front loader arms (pivot beside the cab) -> knee -> bucket
    A0, K0, B0 = Vector((-.15, 0, 1.78)), Vector((1.95, 0, 1.12)), Vector((3.05, 0, .62))
    for s in (-1, 1):
        off = Vector((0, s * .82, 0))
        bar(p, "larm1", A0 + off, K0 + off, .13, .22, Y, bevel=.02)
        bar(p, "larm2", K0 + off, B0 + off, .13, .19, Y, bevel=.02)
        p.box("larm_knee", (.3, .15, .3), K0 + off, Y, bevel=.03, seg=2)
        pin(p, "larm_pin", A0 + off, r=.06, w=.2)
        ram(p, "lift_ram", Vector((.35, s * .95, .98)), Vector((1.5, s * .95, 1.1)), .05, D, Ch)
        ram(p, "tilt_ram", Vector((.75, s * .82, 1.72)), Vector((2.7, s * .82, 1.02)), .045, D, Ch)
        p.box("arm_mount", (.5, .12, .5), (-.15, s * .76, 1.6), Y, bevel=.03)
    p.cyl("larm_x", .08, 1.72, K0, Y, rot=(rad(90), 0, 0), verts=10)
    p.cyl("larm_x2", .06, 1.72, A0 + Vector((.5, 0, -.1)), D, rot=(rad(90), 0, 0), verts=8)
    # front bucket (opening +X), 2.3 wide
    bw, bd, bh = 2.3, .85, .78
    p.box("fb_back", (.07, bw, bh), (3.05, 0, .5), Y, rot=(0, rad(-22), 0), bevel=.01)
    p.box("fb_bottom", (bd, bw, .07), (3.42, 0, .1), Y, bevel=.01)
    p.box("fb_top", (.45, bw, .06), (3.3, 0, .88), Y, rot=(0, rad(-30), 0), bevel=.01)
    for s in (-1, 1):
        p.prism("fb_side", 3.1, 3.85, 2.95, 3.3, .035, .08, .9, Y, bevel=.01, seg=1).location.y = s * (bw / 2 - .035)
        p.box("fb_stripe", (.6, .03, .12), (3.2, s * (bw / 2 + .02), .78), m["hazard"], rot=(0, rad(-30), 0), bevel=0)
    p.box("fb_lip", (.12, bw + .02, .07), (3.86, 0, .1), D, bevel=.008)
    for i in range(5):
        p.box("fb_tooth", (.2, .14, .06), (3.95, -bw / 2 + bw * (i + .5) / 5, .1), D, bevel=0)
    p.box("fb_brace", (.5, bw - .4, .08), (3.2, 0, .55), D, rot=(0, rad(-22), 0), bevel=.01)
    # wheels
    for s in (-1, 1):
        p.wheel((1.65, s * yf, Rf + .02), R=Rf, w=.30, side=s, hub="rimD", verts=16)
        p.wheel((-1.25, s * yr, Rr + .02), R=Rr, w=.48, side=s, hub="rimD", verts=20, nuts=5)
        for i in range(8):   # tread lugs on the big rear tyres
            a = i * math.tau / 8
            p.box("lug", (.13, .5, .05), (-1.25 + math.cos(a) * Rr, s * yr, Rr + .02 + math.sin(a) * Rr), m["tyre"], rot=(0, -a, 0), bevel=0)
    p.box("counterweight", (.3, 1.2, .35), (2.62, 0, .75), D, bevel=.03)
    p.box("toolbox", (.6, .3, .35), (.55, -1.0, .85), D, bevel=.02)
    return set_pivot(p.o)

def backhoe_arm(c):
    """Rear digging arm: boom, dipper, bucket + rams. Origin = hinge BH_HINGE (rotate about local Y to dig)."""
    p = P(c); m = mats(); Y, D, I, Ch = m["yellow"], m["dark"], m["ink"], m["chrome"]
    H = BH_HINGE; Mv = H + Vector((-.75, 0, .95)); K = H + Vector((-1.7, 0, 1.65)); A = K + Vector((-1.2, 0, -2.35))
    pin(p, "hinge_pin", H, r=.075, w=.55)
    p.box("swing_bracket", (.36, .5, .5), H + Vector((-.15, 0, -.05)), Y, bevel=.03, seg=2)
    bar(p, "boom1", H + Vector((.1, 0, -.1)), Mv, .24, .36, Y, bevel=.025, seg=2)
    bar(p, "boom2", Mv, K, .24, .3, Y, bevel=.025, seg=2)
    p.box("boom_elbow", (.34, .26, .36), Mv, Y, bevel=.04, seg=2)
    p.box("boom_knee", (.3, .3, .34), K, Y, bevel=.04, seg=2)
    pin(p, "knee_pin", K, r=.06, w=.36)
    ram(p, "boom_ram", H + Vector((-.05, 0, -.42)), Mv + Vector((-.25, 0, -.05)), .055, D, Ch)
    ram(p, "dipper_ram", Mv + Vector((.05, 0, .25)), K + Vector((-.3, 0, -.45)), .05, D, Ch)
    bar(p, "dipper", K + Vector((.2, 0, .2)), A, .18, .26, Y, bevel=.02, seg=2)
    p.box("dipper_end", (.26, .22, .3), K + Vector((.15, 0, .2)), Y, bevel=.03)
    p.box("dipper_stripe", (.2, .26, .2), K.lerp(A, .5), m["hazard"], rot=(0, -math.atan2((A - K).z, (A - K).x), 0), bevel=0)
    ram(p, "bucket_ram", K + Vector((.3, 0, .05)), A + Vector((.25, 0, .5)), .045, D, Ch)
    p.box("bucket_link", (.4, .05, .05), A + Vector((.15, 0, .35)), D, rot=(0, rad(40), 0), bevel=0)
    pin(p, "bucket_pin", A, r=.05, w=.3)
    # bucket: pivot at A, back wall hangs below, opening towards +X (curls to the machine)
    bw, bd, bh = .72, .6, .55; t = .05
    bk = []
    def bb(name, size, loc, mm, **kw): bk.append(p.box(name, size, loc, mm, **kw))
    bb("bk_back", (t, bw, bh), (-.0, 0, -bh / 2), D, bevel=.01)
    bb("bk_bottom", (bd, bw, t), (bd / 2, 0, -bh + t / 2), D, bevel=.01)
    for s in (-1, 1):
        bb("bk_side", (bd, t, bh), (bd / 2, s * (bw / 2 - t / 2), -bh / 2), D, bevel=.01)
    bb("bk_lip", (.06, bw + .02, .08), (bd + .01, 0, -bh + .04), I, bevel=.006)
    for i in range(4):
        bb("bk_tooth", (.16, .09, .055), (bd + .1, -bw / 2 + bw * (i + .5) / 4, -bh + t / 2), I, bevel=.005)
    bb("bk_ear", (.3, .3, .2), (-.02, 0, -.0), Y, bevel=.02)
    xform(bk, Matrix.Translation(A) @ Matrix.Rotation(rad(30), 4, 'Y'))
    return set_pivot(p.o, H)

def pit(c):
    """Asphalt cut 3.4 x 1.8 m: ragged edge, mud floor, dirt heaps, PVC pipe, rubble, puddle, shovel. Ground z=0."""
    p = P(c); m = mats(); rnd = random.Random(7)
    Lx, Ly = 3.4, 1.8
    p.box("cut_n", (Lx, .28, .05), (0, Ly / 2 - .14, .025), m["cut"], bevel=.015)
    p.box("cut_s", (Lx, .28, .05), (0, -Ly / 2 + .14, .025), m["cut"], bevel=.015)
    p.box("cut_e", (.28, Ly, .05), (Lx / 2 - .14, 0, .025), m["cut"], bevel=.015)
    p.box("cut_w", (.28, Ly, .05), (-Lx / 2 + .14, 0, .025), m["cut"], bevel=.015)
    for i in range(6):   # broken asphalt slabs along the cut
        p.box("slab", (rnd.uniform(.25, .45), rnd.uniform(.18, .3), .05), (rnd.uniform(-1.4, 1.4), rnd.choice((-1, 1)) * (Ly / 2 + .12), .03), m["cut"], rot=(0, 0, rnd.uniform(-.4, .4)), bevel=.01)
    p.box("floor", (Lx - .5, Ly - .5, .03), (0, 0, .015), m["mud"], bevel=0)
    p.box("gravel", (1.2, .9, .035), (.9, -.2, .02), m["gravel"], bevel=0)
    # dirt heaps (long one behind the cut, small ones at the ends)
    for (x, y, r, sc) in ((-.2, 1.25, .75, (1.9, .7, .45)), (1.3, 1.2, .55, (1.3, .8, .5)), (-1.95, -.3, .5, (.7, 1.2, .55)), (1.6, -1.15, .4, (1.1, .7, .5))):
        p.ball("heap", r, (x, y, .02), m["dirt"], sub=2, scale=sc)
    for i in range(18):
        r = rnd.uniform(.05, .12)
        x, y = rnd.uniform(-1.5, 1.5), rnd.choice((rnd.uniform(.9, 1.5), rnd.uniform(-.7, .7)))
        p.box("rubble", (r * 2, r * 1.5, r), (x, y, .05 + (0.12 if abs(y) > .85 else 0)), m["concrete"] if i % 3 else m["cut"], rot=(rnd.uniform(0, .5), rnd.uniform(0, .5), rnd.uniform(0, 3)), bevel=r * .3)
    # orange PVC pipe lying in the trench + a coupling and an elbow
    p.cyl("pipe", .13, 2.6, (-.2, .15, .16), m["pvc"], rot=(0, rad(90), 0), verts=14, bevel=.01)
    p.cyl("pipe_coupling", .15, .3, (.4, .15, .16), m["pvc"], rot=(0, rad(90), 0), verts=14, bevel=.012)
    p.cyl("pipe_elbow", .13, .45, (1.1, .15, .3), m["pvc"], rot=(0, 0, 0), verts=14, bevel=.01)
    p.ball("pipe_elbow_j", .135, (1.1, .15, .16), m["pvc"], sub=2)
    p.cyl("pipe_cap", .14, .06, (-1.52, .15, .16), m["dark"], rot=(0, rad(90), 0), verts=14)
    # puddle + shovel stuck in the heap
    p.cyl("puddle", .42, .012, (-.9, -.35, .036), m["puddle"], verts=16).scale = (1.5, .9, 1)
    p.tube("shovel_handle", (-.55, 1.35, .95), (-.3, 1.15, 1.9), .018, m["wood"], verts=6)
    p.box("shovel_grip", (.12, .04, .04), (-.3, 1.15, 1.92), m["dark"], bevel=.005)
    p.box("shovel_blade", (.26, .04, .32), (-.62, 1.4, .68), m["steel"], rot=(rad(-20), 0, rad(15)), bevel=.008)
    return set_pivot(p.o)

def road_barrier(c, w=1.6):
    """Cavalete: white A-frame, two red/white boards, OBRAS plate, amber blinker with a solar cell. Faces -Y."""
    p = P(c); m = mats(); Wt, I = m["white"], m["ink"]
    for s in (-1, 1):
        x = s * (w / 2 - .06)
        for sy in (-1, 1):
            p.tube("leg", (x, sy * .02, 1.12), (x, sy * .36, .03), .024, Wt, verts=8)
        p.box("foot", (.07, .78, .05), (x, 0, .03), m["dark"], bevel=.01)
        p.box("leg_cap", (.07, .1, .05), (x, 0, 1.13), Wt, bevel=.01)
        p.box("leg_brace", (.05, .55, .03), (x, 0, .45), Wt, bevel=.005)
    for z in (.58, .95):
        p.box("board_bk", (w + .02, .025, .25), (0, .012, z), I, bevel=.006)
        p.box("board", (w, .05, .22), (0, 0, z), m["hazardR"], bevel=.01)
    p.box("obras_plate", (.56, .012, .15), (0, -.03, .95), Wt, bevel=.004)
    p.txt("OBRAS", .1, (0, -.04, .945), I, face="-Y")
    p.box("blink_base", (.18, .14, .09), (w / 2 - .06, 0, 1.2), m["dark"], bevel=.012)
    p.cyl("blink_lamp", .075, .13, (w / 2 - .06, 0, 1.3), m["amber"], verts=12, bevel=.015)
    p.cyl("blink_cap", .08, .02, (w / 2 - .06, 0, 1.37), m["dark"], verts=12)
    p.box("solar", (.16, .12, .012), (w / 2 - .06, .0, 1.39), m["solar"], rot=(rad(15), 0, 0), bevel=.003)
    return set_pivot(p.o)

def detour_sign(c):
    """DESVIO -> orange sign on a tubular stand weighted with sandbags. Faces -Y."""
    p = P(c); m = mats(); I, S = m["ink"], m["steel"]
    p.box("base_bar", (1.0, .08, .06), (0, .0, .03), m["dark"], bevel=.01)
    p.box("base_bar2", (.08, .8, .06), (0, 0, .03), m["dark"], bevel=.01)
    for s in (-1, 1):
        p.tube("post", (s * .36, 0, .06), (s * .36, 0, 1.95), .025, S, verts=8)
        p.tube("brace", (s * .36, 0, 1.0), (s * .36, .38, .06), .018, S, verts=6)
        p.ball("sandbag", .17, (s * .3, .22, .09), m["sand"], sub=2, scale=(1.3, 1, .55))
    p.tube("crossbar", (-.4, 0, 1.95), (.4, 0, 1.95), .025, S, verts=8)
    p.tube("crossbar2", (-.4, 0, 1.15), (.4, 0, 1.15), .025, S, verts=8)
    p.box("sign_bk", (.98, .015, .66), (0, -.02, 1.55), I, bevel=.006)
    p.box("sign", (.92, .03, .6), (0, -.035, 1.55), m["orange"], bevel=.012)
    p.txt("DESVIO", .2, (-.1, -.055, 1.6), I, face="-Y", res=2)
    p.box("arrow_shaft", (.3, .012, .07), (-.06, -.055, 1.36), I, bevel=0)
    p.cyl("arrow_head", .12, .012, (.2, -.055, 1.36), I, rot=(rad(90), 0, 0), verts=3)
    p.txt("OBRAS NA PISTA", .07, (.0, -.055, 1.82), I, face="-Y")
    for s in (-1, 1):
        for z in (1.3, 1.8):
            p.cyl("bolt", .018, .02, (s * .36, -.052, z), S, rot=(rad(90), 0, 0), verts=6)
    return set_pivot(p.o)

def light_tower(c):
    """Mobile light tower: small trailer with a generator box, telescopic mast, 4 floodlights (lamps face -Y)."""
    p = P(c); m = mats(); Y, D, I, S = m["yellow"], m["dark"], m["ink"], m["steel"]
    p.box("trailer", (2.0, 1.15, .1), (0, 0, .45), D, bevel=.012)
    p.box("gen", (1.5, 1.05, .95), (.15, 0, 1.0), Y, bevel=.045, seg=2)
    p.box("gen_lid", (1.54, 1.09, .06), (.15, 0, 1.5), D, bevel=.012)
    for s in (-1, 1):
        p.seam(.15, s * .525, .6, 1.4, face=s)
        for i in range(4):
            p.box("vent", (.35, .012, .035), (-.3, s * .53, .7 + i * .11), I, bevel=0)
        p.box("gen_stripe", (1.5, .012, .1), (.15, s * .53, .58), m["hazard"], bevel=0)
        p.wheel((.1, s * .64, .3), R=.28, w=.16, side=s, hub="rimD", verts=14, nuts=4)
        p.box("mudguard", (.75, .2, .04), (.1, s * .64, .62), D, bevel=.008)
        p.box("jack", (.06, .06, .5), (.95, s * .5, .25), S, bevel=0)
        p.box("jack_pad", (.16, .16, .03), (.95, s * .5, .015), D, bevel=.005)
    p.box("panel", (.012, .35, .3), (.9, .0, 1.1), I, bevel=.004)
    p.box("panel_led", (.012, .04, .04), (.905, -.1, 1.2), m["ledG"], bevel=0)
    p.box("panel_led2", (.012, .04, .04), (.905, .0, 1.2), m["ledR"], bevel=0)
    p.cyl("gen_exhaust", .03, .25, (-.35, .3, 1.6), D, verts=6)
    p.tube("drawbar", (-1.0, 0, .45), (-1.75, 0, .42), .04, D, verts=8)
    p.box("hitch", (.14, .12, .1), (-1.78, 0, .44), D, bevel=.012)
    p.cyl("jockey_post", .025, .4, (-1.5, .12, .25), S, verts=6)
    p.cyl("jockey_wheel", .09, .05, (-1.5, .12, .09), m["tyre"], rot=(0, rad(90), 0), verts=10)
    p.box("mast_base", (.3, .3, .2), (-.45, 0, 1.6), D, bevel=.02)
    for i, (r, z0, z1) in enumerate(((.07, 1.6, 2.9), (.055, 2.8, 4.0), (.042, 3.9, 4.95))):
        p.cyl("mast%d" % i, r, z1 - z0, (-.45, 0, (z0 + z1) / 2), S, verts=8)
        p.cyl("mast_collar%d" % i, r + .02, .06, (-.45, 0, z1 - .03), D, verts=8)
    p.tube("mast_cable", (-.52, .05, 1.6), (-.52, .05, 4.9), .01, I, verts=4)
    p.box("crossbar", (1.5, .06, .06), (-.45, 0, 4.98), D, bevel=.008)
    for x in (-.6, -.2, .2, .6):
        p.box("flood_bz", (.32, .22, .28), (-.45 + x, -.1, 4.86), I, rot=(rad(35), 0, 0), bevel=.012)
        p.box("flood", (.28, .05, .24), (-.45 + x, -.21, 4.84), m["lamp"], rot=(rad(35), 0, 0), bevel=.01)
        p.box("flood_arm", (.04, .06, .12), (-.45 + x, -.02, 4.95), S, bevel=0)
    return set_pivot(p.o)

def cone0(c, x, y, h=.7):
    """The game's cone (E.cone) sits on the sidewalk height; this one stands on the road (z=0)."""
    return put(E.grab(c, E.cone, x, y, h), z=-.13)

@E.event
def v2_RuaEmObras(c):
    E.diorama(c); m = mats(); px, py = -2.7, -3.4
    put(pit(c), px, py)
    put(backhoe(c), px + 4.3, py - .05); put(backhoe_arm(c), px + 4.3, py - .05)
    for (bx_, by_, r) in ((px - 2.3, py, 90), (px + 1.3, py + 1.55, 0), (px - .9, py + 1.55, 0), (px - .9, py - 1.45, 0), (px + 1.3, py - 1.45, 0)):
        put(road_barrier(c), bx_, by_, rot=rad(r))
    for i, cx_ in enumerate((-6.6, -6.0, -5.4)):
        cone0(c, cx_, -1.8 - i * .55, h=.7)
    put(detour_sign(c), -6.6, -.5, z=.13, rot=rad(8))
    put(light_tower(c), 1.0, -.25, z=.13, rot=rad(4))
    E.actor(c, "Customer_07", (px - 1.2, py + .3, 0), rad(35)); E.actor(c, "Customer_09", (px + 1.0, py - 2.2, 0), rad(170))
    E.actor(c, "Customer_06", (-4.4, 1.4), rad(160))

# ================================================================== 2. QUEDA DE ENERGIA
def concrete_pole(p, h=7.5, number="4821"):
    """Tapered double-T concrete pole from z=0 to h, foot painted black, number plate on -Y."""
    m = mats()
    p.prism("pole", -.14, .14, -.10, .10, .18, 0, h, m["concP"], yt=.13, bevel=.02, seg=1)
    for s in (-1, 1):   # the double-T recesses on the +-X faces
        p.prism("pole_web", s * .145 - .02, s * .145 + .02, s * .105 - .02, s * .105 + .02, .09, .5, h - .4, m["greyD"], yt=.065, bevel=0, seg=1)
    p.box("pole_foot", (.32, .4, .9), (0, 0, .45), m["ink"], bevel=.01)
    p.box("pole_plate", (.12, .012, .16), (0, -.19, 2.2), m["white"], bevel=.003)
    p.txt(number, .05, (0, -.2, 2.2), m["ink"], face="-Y")
    p.txt("PERIGO", .045, (0, -.2, 2.28), m["red"], face="-Y")

def utility_pole(c):
    """7.5 m concrete pole with crossarm + 3 insulators, 25 kVA transformer can with fins and bushings, fuse cutouts, LV rack."""
    p = P(c); m = mats(); I, W_, Cer = m["ink"], m["wood"], m["ceramic"]
    concrete_pole(p, 7.5, "4821")
    p.box("crossarm", (2.0, .1, .12), (0, .0, 7.05), W_, bevel=.012)
    p.box("crossarm_bracket", (.3, .16, .14), (0, 0, 7.05), m["greyD"], bevel=.01)
    for s in (-1, 1):
        p.tube("arm_brace", (s * .8, .0, 6.99), (s * .05, .0, 6.4), .014, m["greyD"], verts=6)
        p.cyl("insulator", .045, .16, (s * .85, 0, 7.19), Cer, verts=10, bevel=.01)
        p.cyl("insulator_skirt", .07, .05, (s * .85, 0, 7.15), Cer, verts=10)
        p.cyl("insulator_skirt2", .06, .04, (s * .85, 0, 7.22), Cer, verts=10)
        p.tube("hv_cable", (s * 2.4, 0, 7.18), (s * .85, 0, 7.28), .012, I, verts=4)
    p.cyl("insulator_c", .045, .18, (0, 0, 7.35), Cer, verts=10, bevel=.01)
    p.cyl("insulator_c_skirt", .07, .05, (0, 0, 7.3), Cer, verts=10)
    p.tube("hv_cable_c", (-2.4, .0, 7.33), (2.4, .0, 7.33), .012, I, verts=4)
    # transformer can on the -Y side
    ty, tz = -.62, 5.75
    p.cyl("trafo", .36, 1.05, (0, ty, tz), m["trafo"], verts=20, bevel=.02)
    p.cyl("trafo_lid", .38, .06, (0, ty, tz + .55), m["greyD"], verts=20, bevel=.01)
    p.cyl("trafo_base", .3, .08, (0, ty, tz - .55), m["greyD"], verts=12)
    for i in range(7):
        a = rad(-120 + i * 40)
        p.box("fin", (.03, .14, .8), (math.sin(a) * .40, ty - math.cos(a) * .40, tz - .02), m["trafo"], rot=(0, 0, -a), bevel=.004)
    for s in (-1, 1):
        p.cyl("bushing", .035, .3, (s * .17, ty, tz + .7), Cer, verts=8, bevel=.01)
        p.cyl("bushing_skirt", .06, .04, (s * .17, ty, tz + .65), Cer, verts=8)
        p.box("trafo_bracket", (.5, .36, .07), (0, -.3, tz + .35 * s), m["greyD"], bevel=.01)
        p.tube("bushing_lead", (s * .17, ty, tz + .85), (s * .85, 0, 7.12), .01, I, verts=4)
    p.cyl("lv_bushing", .03, .2, (0, ty - .25, tz + .65), Cer, verts=8)
    p.box("nameplate", (.18, .012, .12), (0, ty - .37, tz + .1), m["white"], bevel=.003)
    p.txt("25 kVA", .035, (0, ty - .38, tz + .1), I, face="-Y")
    # fuse cutouts (chaves fusíveis) on a bracket above the can
    p.box("fuse_bracket", (1.1, .08, .08), (0, -.35, 6.55), m["greyD"], bevel=.01)
    for i, x in enumerate((-.4, 0, .4)):
        p.cyl("cutout_ins", .04, .22, (x, -.38, 6.68), Cer, verts=8, bevel=.01, rot=(rad(25), 0, 0))
        p.cyl("fuse_tube", .022, .36, (x, -.5, 6.62), m["greyD"], verts=6, rot=(rad(25), 0, 0))
        p.tube("fuse_lead", (x, -.52, 6.8), (x * 2.125, 0, 7.3 if x else 7.42), .008, I, verts=4)
    p.cyl("arrester", .035, .3, (.6, -.3, 6.3), m["greyD"], verts=8, bevel=.01)
    # low-voltage rack with spool insulators + 4 cable stubs
    p.box("lv_rack", (.08, .5, .5), (0, -.25, 4.95), m["greyD"], bevel=.008)
    for i in range(4):
        z = 4.76 + i * .13
        p.cyl("spool", .035, .07, (0, -.3, z), Cer, verts=8, rot=(0, rad(90), 0))
        p.tube("lv_cable", (-2.4, -.32, z - .06), (2.4, -.32, z - .06), .011, I, verts=4)
    p.tube("ground_wire", (.0, -.19, .9), (.0, -.19, 5.2), .008, m["greyD"], verts=4)
    p.tube("drop_wire", (0, -.35, 4.95), (.9, 1.6, 4.0), .009, I, verts=4)
    return set_pivot(p.o)

def spark(c):
    """Stylised arc burst, origin at the centre (the game scales/flickers it)."""
    p = P(c); m = mats(); rnd = random.Random(11)
    p.ball("spark_core", .08, (0, 0, 0), m["sparkW"], sub=2)
    p.ball("spark_glow", .14, (0, 0, 0), m["sparkY"], sub=2, scale=(1.1, .7, 1.1))
    for i in range(11):
        a = i * math.tau / 11 + rnd.uniform(-.15, .15); L_ = rnd.uniform(.35, .75)
        d = Vector((math.cos(a), rnd.uniform(-.25, .25), math.sin(a)))
        p.cyl("spike", .04 if i % 2 else .028, L_, d * (L_ / 2 + .05), m["sparkY"] if i % 2 else m["sparkW"], r2=0.0, verts=4).rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    for i in range(7):
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-.4, .4), rnd.uniform(-1, 1))).normalized() * rnd.uniform(.45, .8)
        p.ball("spark_dot", rnd.uniform(.02, .04), d, m["sparkW"], sub=1)
    p.cyl("zig1", .022, .5, (-.35, 0, .3), m["sparkW"], verts=4, rot=(0, rad(55), 0))
    p.cyl("zig2", .02, .35, (-.55, 0, .62), m["sparkY"], verts=4, rot=(0, rad(-40), 0))
    return set_pivot(p.o)

def smoke(c):
    """Soft puff, origin at the centre."""
    p = P(c); m = mats()
    for (x, y, z, r) in ((0, 0, 0, .34), (.28, .05, .18, .26), (-.26, -.04, .2, .24), (.05, .1, .36, .22), (-.1, -.12, -.18, .2), (.3, -.08, -.1, .17)):
        p.ball("puff", r, (x, y, z), m["smoke"], sub=2)
    return set_pivot(p.o)

BT_TURRET = Vector((-2.35, 0, 1.52))   # boom pivot of the bucket truck (top of the turret ring)

def bucket_truck(c):
    """Power-company truck 7.4 x 2.3 m: white cab-over cab, orange stripes, aerial-device body with tool lockers,
    outriggers and the turret pedestal. Boom is a separate prop (Energia_BucketBoom) pivoting at BT_TURRET."""
    p = P(c); m = mats(); Lt, Wt = 7.4, 2.3; hw = Wt / 2; fx, bx = Lt / 2, -Lt / 2
    Wh, O, D, I, S, Ch = m["white"], m["orange"], m["dark"], m["ink"], m["steel"], m["chrome"]
    cabL = 2.1; cx = fx - cabL / 2; R = .46
    p.box("chassis", (Lt - .4, 1.0, .22), (-.1, 0, .62), I, bevel=.02)
    for s in (-1, 1):
        p.box("chassis_rail", (Lt - .8, .08, .2), (-.2, s * .5, .62), D, bevel=.01)
    cab = p.box("cab", (cabL, Wt, 1.75), (cx, 0, 1.48), Wh, bevel=.14, seg=2)
    p.arch(cab, fx - 1.0, -hw, R + .1, R + .02, w=.6); p.arch(cab, fx - 1.0, hw, R + .1, R + .02, w=.6)
    p.box("cab_roof", (cabL - .2, Wt - .2, .12), (cx, 0, 2.38), Wh, bevel=.04)
    p.box("windshield", (.06, Wt - .36, .82), (fx + .005, 0, 1.78), m["glass"], rot=(0, rad(-6), 0), bevel=.03)
    p.box("visor", (.3, Wt - .1, .07), (fx + .06, 0, 2.28), D, bevel=.015)
    for s in (-1, 1):
        p.box("cab_sideglass", (.72, .03, .62), (cx - .25, s * (hw + .003), 1.82), m["glass"], bevel=.03)
        p.seam(cx + .22, s * hw, .75, 2.2, face=s); p.seam(cx - .66, s * hw, .75, 2.2, face=s)
        p.handle((cx - .1, s * hw, 1.4), face=s)
        p.box("step", (.5, .3, .05), (cx, s * (hw - .05), .55), S, bevel=.01)
        p.box("step2", (.5, .3, .05), (cx, s * (hw - .05), .9), S, bevel=.01)
        p.mirror((fx - .35, s * hw, 1.95), s, arm=.25, h=.44, w=.2)
        p.lamp("headlamp", (.05, .36, .18), (fx + .02, s * .74, .95), m["lamp"])
        p.box("indicator", (.04, .12, .08), (fx + .025, s * .46, .95), m["amber"], bevel=.01)
        p.wheel((fx - 1.0, s * (hw - .16), R + .02), R=R, w=.28, side=s)
        p.box("cab_stripe", (cabL - .3, .012, .2), (cx, s * (hw + .006), 1.1), O, bevel=.004)
        p.box("cab_stripe2", (cabL - .3, .012, .05), (cx, s * (hw + .006), .96), m["navy"], bevel=.003)
        if s < 0: p.txt("ENERGIA", .12, (cx - .05, s * (hw + .02), 1.42), m["navy"], face="-Y")
    p.box("grille", (.05, 1.3, .35), (fx + .015, 0, 1.22), I, bevel=.02)
    for i in range(3):
        p.box("grille_bar", (.02, 1.2, .035), (fx + .045, 0, 1.1 + i * .12), m["grey"], bevel=0)
    p.box("bumper_f", (.2, Wt + .04, .3), (fx + .04, 0, .5), D, bevel=.05, seg=3)
    p.box("lightbar_base", (.3, 1.1, .05), (cx, 0, 2.46), D, bevel=.006)
    p.box("lightbar", (.26, 1.0, .11), (cx, 0, 2.53), m["amber"], bevel=.03, seg=2)
    p.cyl("fuel_tank", .3, 1.0, (bx + 2.6, -(hw - .3), .62), Ch, rot=(0, rad(90), 0), verts=16, bevel=.03)
    for dx in (-.35, .35):
        p.box("tank_strap", (.05, .64, .64), (bx + 2.6 + dx, -(hw - .3), .62), D, bevel=.01)
    p.cyl("exhaust", .05, 1.0, (bx + 1.4, (hw - .2), .4), m["grey"], rot=(0, rad(90), 0), verts=8)
    # aerial-device body: lockers + deck + pedestal
    bl = Lt - cabL - .3; bcx = bx + bl / 2
    p.box("deck", (bl, Wt + .06, .08), (bcx, 0, 1.3), D, bevel=.012)
    p.box("deck_tread", (bl - .2, Wt - .1, .012), (bcx, 0, 1.345), m["rubberM"], bevel=0)
    p.box("lockers", (bl - .1, Wt + .02, .5), (bcx, 0, 1.02), Wh, bevel=.03, seg=2)
    for s in (-1, 1):
        p.box("locker_stripe", (bl - .2, .012, .16), (bcx, s * (hw + .018), 1.0), O, bevel=.004)
        for i in range(4):
            xx = bx + .5 + i * (bl - .6) / 3.2
            p.seam(xx, s * (hw + .012), .8, 1.24, face=s, m=I)
            if i % 2: p.handle((xx - .5, s * (hw + .02), 1.15), face=s)
        p.box("tall_locker", (.9, .4, 1.2), (bx + bl - .5, s * (hw - .2), 1.95), Wh, bevel=.03, seg=2)
        p.seam(bx + bl - .5, s * (hw + .002), 1.4, 2.5, face=s, m=I)
        p.box("tl_stripe", (.9, .012, .16), (bx + bl - .5, s * (hw + .006), 1.9), O, bevel=.004)
        for xx in (bx + .45, bx + bl - 1.3):
            p.box("outrigger", (.26, .5, .24), (xx, s * (hw - .05), 1.12), m["hazard"], bevel=.012)
            p.box("outr_leg", (.12, .12, .62), (xx, s * (hw + .05), .5), D, bevel=0)
            p.box("outr_pad", (.4, .4, .07), (xx, s * (hw + .05), .04), D, bevel=.012)
            p.tube("outr_ram", (xx, s * (hw + .05), 1.1), (xx, s * (hw + .05), .6), .035, Ch, verts=8)
        p.box("rear_lamp", (.05, .12, .4), (bx - .03, s * (hw - .25), .78), m["tail"], bevel=.015)
        p.box("rear_lamp_bezel", (.03, .16, .46), (bx - .015, s * (hw - .25), .78), I, bevel=.006)
        p.box("mudguard", (.95, .32, .06), (bx + 1.5, s * (hw - .2), R * 2 + .1), I, bevel=.01)
        p.wheel((bx + 1.5, s * (hw - .16), R + .02), R=R, w=.28, side=s)
        p.box("cone_rack", (.25, .25, .5), (bx + .3, s * (hw - .35), 1.6), O, bevel=.02)
    p.txt("ENERGIA", .2, (bcx - .3, -(hw + .028), 1.05), m["navy"], face="-Y")
    p.box("underride", (.08, Wt - .4, .14), (bx - .02, 0, .48), m["hazard"], bevel=.01)
    p.box("rear_bumper", (.14, Wt, .2), (bx - .04, 0, .62), D, bevel=.03)
    p.plate(bx - .11, 0, .62, "-X", "ENE 7E12")
    p.box("rear_hazard", (.03, 1.4, .2), (bx - .05, 0, 1.0), m["hazardR"], bevel=0)
    # turret pedestal (fixed part)
    T = BT_TURRET
    p.cyl("pedestal", .48, .3, (T.x, T.y, 1.34 + .15), m["greyD"], verts=18, bevel=.02)
    p.box("ped_stripe", (.98, .98, .1), (T.x, T.y, 1.4), m["hazard"], bevel=.0)
    p.box("ladder_rail", (.04, .04, 1.0), (bx + bl - .05, -(hw - .5), 1.8), S, bevel=0)
    p.box("ladder_rail", (.04, .04, 1.0), (bx + bl - .05, -(hw - .9), 1.8), S, bevel=0)
    for i in range(4):
        p.box("ladder_rung", (.03, .4, .03), (bx + bl - .05, -(hw - .7), 1.45 + i * .25), S, bevel=0)
    p.cyl("beacon_r", .07, .12, (bx + .3, 0, 1.4 + .06), m["amber"], verts=10, bevel=.012)
    return set_pivot(p.o)

def bucket_boom(c):
    """Turret + lower boom (70 deg) + upper boom (10 deg) + insulated bucket. Origin at the turret (BT_TURRET):
    rotate about local Z to slew, about local Y to raise. Modelled pointing to -X (over the truck's rear)."""
    p = P(c); m = mats(); O, D, I, Wh, Ch = m["orange"], m["dark"], m["ink"], m["white"], m["chrome"]
    T = BT_TURRET
    p.cyl("turret_ring", .42, .12, T + Vector((0, 0, .06)), D, verts=18, bevel=.015)
    p.box("turret", (.7, .8, .55), T + Vector((0, 0, .4)), O, bevel=.04, seg=2)
    p.box("turret_stripe", (.72, .82, .1), T + Vector((0, 0, .25)), m["hazard"], bevel=0)
    P1 = T + Vector((.15, 0, .7)); a1, L1 = 70.0, 3.2
    K = P1 + Vector((-L1 * math.cos(rad(a1)), 0, L1 * math.sin(rad(a1))))
    a2, L2 = 10.0, 2.5
    Tp = K + Vector((-L2 * math.cos(rad(a2)), 0, L2 * math.sin(rad(a2))))
    bar(p, "boom1", P1 + (P1 - K).normalized() * .2, K, .34, .36, O, bevel=.03, seg=2)
    bar(p, "boom1_stripe", P1.lerp(K, .75), P1.lerp(K, .88), .35, .37, m["hazard"], bevel=0)
    pin(p, "pin1", P1, r=.08, w=.5)
    ram(p, "ram1", T + Vector((-.3, 0, .45)), P1.lerp(K, .45) + Vector((-.22, 0, .0)), .07, D, Ch)
    p.box("knee", (.42, .46, .46), K, O, bevel=.04, seg=2)
    pin(p, "pin2", K, r=.07, w=.5)
    bar(p, "boom2", K, Tp, .26, .28, Wh, bevel=.025, seg=2)   # insulated (fibreglass) upper section
    bar(p, "boom2_band", K.lerp(Tp, .1), K.lerp(Tp, .2), .27, .29, O, bevel=0)
    bar(p, "boom2_band2", K.lerp(Tp, .8), K.lerp(Tp, .9), .27, .29, O, bevel=0)
    ram(p, "ram2", P1.lerp(K, .6) + Vector((.18, 0, .1)), K.lerp(Tp, .3) + Vector((0, 0, .2)), .05, D, Ch)
    p.tube("hose", P1 + Vector((0, .2, 0)), K + Vector((0, .25, .1)), .018, I, verts=5)
    # bucket (cesto): fibreglass, hangs from Tp
    bw, bd, bh = 1.0, .8, 1.0
    bc = Tp + Vector((-(.15 + bd / 2), 0, -.5))
    pin(p, "pin3", Tp, r=.05, w=.36)
    p.box("bmount", (.3, .25, .55), Tp + Vector((-.05, 0, -.3)), D, bevel=.02)
    p.box("bfloor", (bd, bw, .06), (bc.x, bc.y, bc.z - bh / 2 + .03), D, bevel=.01)
    for s in (-1, 1):
        p.box("bwall_y", (bd, .06, bh), (bc.x, bc.y + s * (bw / 2 - .03), bc.z), Wh, bevel=.012)
        p.box("bwall_x", (.06, bw, bh), (bc.x + s * (bd / 2 - .03), bc.y, bc.z), Wh, bevel=.012)
    p.box("brail", (bd + .06, bw + .06, .06), (bc.x, bc.y, bc.z + bh / 2 - .03), O, bevel=.012)
    p.box("bstripe", (bd + .02, .012, .18), (bc.x, bc.y - bw / 2 - .006, bc.z - .1), m["hazard"], bevel=0)
    p.box("bstripe2", (.012, bw + .02, .18), (bc.x - bd / 2 - .006, bc.y, bc.z - .1), m["hazard"], bevel=0)
    p.box("btool", (.25, .14, .3), (bc.x + .2, bc.y + bw / 2 - .12, bc.z + .2), D, bevel=.01)
    p.cyl("bcontrol", .03, .25, (bc.x - .1, bc.y - .3, bc.z + bh / 2 + .1), I, verts=6)
    return set_pivot(p.o, T)

@E.event
def v2_QuedaDeEnergia(c):
    E.diorama(c); m = mats(); x, y = -2.6, -.9
    put(utility_pole(c), x, y, z=.13)
    put(spark(c), x - .12, y - .78, z=6.65); put(smoke(c), x + .3, y - .45, z=7.45)
    tx, ty = 2.7, -3.0
    put(bucket_truck(c), tx, ty)
    bucket_at = Vector((x - 1.45, y - 1.05)); T2 = Vector((tx + BT_TURRET.x, ty + BT_TURRET.y)); d = bucket_at - T2
    rot = math.atan2(d.y, d.x) - math.pi
    put_pivot(bucket_boom(c), BT_TURRET, tx, ty, rot=rot)
    reach = 3.95; bz = BT_TURRET.z + .7 + 3.2 * math.sin(rad(70)) + 2.5 * math.sin(rad(10)) - .97
    bpos = T2 + Vector((math.cos(rot + math.pi), math.sin(rot + math.pi))) * reach
    E.actor(c, "Customer_09", (bpos.x, bpos.y, bz), rot + math.pi + rad(90))
    E.actor(c, "Customer_06", (.6, .9), rad(205)); E.actor(c, "Customer_07", (-1.4, 2.3), rad(120))
    k.box("dark_lamp", (.45, .22, .1), (4.6, -.9, 4.4), m["dark"], c=c)
    E.pole(c, 4.6, -.9, 4.3)
    for cx_ in (-.6, 0.8):
        cone0(c, cx_, -1.75, h=.7)

# ================================================================== 3. MAQUININHA FORA DO AR
def telecom_pole(c):
    """7 m concrete pole with telecom brackets, CTO fibre box with a red LED, slack-cable loops, cable stubs."""
    p = P(c); m = mats(); I = m["ink"]
    concrete_pole(p, 7.0, "3317")
    # telecom cable brackets + 3 cable stubs (5.4-5.7 m), slack loops hanging on the -Y side
    for i, z in enumerate((5.35, 5.55, 5.75)):
        p.box("tbracket", (.12, .3, .05), (0, -.1, z), m["greyD"], bevel=.006)
        p.cyl("tclamp", .03, .08, (0, -.26, z + .03), I, verts=6, rot=(0, rad(90), 0))
        p.tube("tcable", (-2.4, -.27, z - .02 + i * .0), (2.4, -.27, z - .02), .012 if i else .018, I, verts=4)
    torus(p, "slack_loop", .32, .013, (.0, -.34, 4.95), I, rot=(0, rad(90), 0), segs=20, rings=5)
    torus(p, "slack_loop2", .3, .013, (.03, -.36, 4.9), I, rot=(0, rad(90), rad(8)), segs=20, rings=5)
    p.box("loop_hanger", (.08, .18, .06), (0, -.26, 5.28), m["greyD"], bevel=.005)
    # CTO (caixa de terminação óptica) on the -Y side at 4.4 m, with a red status LED
    p.box("cto_mount", (.3, .12, .5), (0, -.22, 4.35), m["greyD"], bevel=.008)
    p.box("cto", (.36, .22, .5), (0, -.36, 4.35), m["ctoG"], bevel=.03, seg=2)
    p.box("cto_lid", (.34, .02, .46), (0, -.48, 4.35), m["greyD"], bevel=.008)
    p.box("cto_label", (.2, .008, .07), (0, -.492, 4.42), m["white"], bevel=.002)
    p.txt("CTO", .045, (0, -.498, 4.42), I, face="-Y")
    p.box("cto_led_bz", (.06, .01, .06), (.11, -.492, 4.52), I, bevel=.004)
    p.box("cto_led", (.035, .012, .035), (.11, -.497, 4.52), m["ledR"], bevel=.004)
    for s in (-1, 1):
        p.cyl("cto_port", .018, .06, (s * .1, -.36, 4.07), I, verts=6)
        p.tube("drop", (s * .1, -.36, 4.05), (s * 1.9, -1.8, 3.2 + s * .3), .007, I, verts=4)
    p.tube("cto_feed", (0, -.3, 4.62), (0, -.3, 5.3), .012, I, verts=4)
    p.box("splice_box", (.16, .1, .12), (-.0, .18, 4.0), m["dark"], bevel=.01)
    p.box("stripe_band", (.3, .38, .1), (0, 0, 2.6), m["hazard"], bevel=.004)
    return set_pivot(p.o)

CTO_LED = Vector((.11, -.497, 4.52))   # the CTO status LED, in telecom-pole space

def cto_led(c):
    """The red status LED alone (origin at its centre) so the game can blink it over the pole's baked (lit) LED."""
    p = P(c); m = mats()
    p.box("led", (.04, .016, .04), (0, 0, 0), m["ledR"], bevel=.005)
    return set_pivot(p.o)

def ext_ladder(c, lean=16.0):
    """Aluminium extension ladder (2 x 3.4 m sections, 1 m overlap), leaning `lean` deg towards +Y. Origin at the foot."""
    p = P(c); m = mats(); Al = m["alum"]; objs = []
    def section(z0, L_, y, w, lock=False):
        for s in (-1, 1):
            p.box("rail", (.045, .085, L_), (s * w / 2, y, z0 + L_ / 2), Al, bevel=.006)
        n = int(L_ / .3)
        for i in range(n):
            p.cyl("rung", .016, w - .045, (0, y, z0 + .18 + i * .3), Al, rot=(0, rad(90), 0), verts=8)
    section(0, 3.4, 0, .46)
    section(1.1, 3.4, .1, .36)
    for z in (1.15, 3.35):   # rung locks / guide brackets between the sections
        for s in (-1, 1):
            p.box("bracket", (.04, .2, .08), (s * .215, .05, z), m["dark"], bevel=.006)
    for s in (-1, 1):
        p.box("foot", (.06, .12, .06), (s * .23, 0, .03), m["rubber"], bevel=.012)
        p.box("top_cap", (.06, .14, .05), (s * .18, .1, 4.5), m["rubber"], bevel=.01)
    p.tube("rope", (-.14, .14, 1.2), (-.14, .14, 4.4), .007, m["cream"], verts=4)
    p.cyl("pulley", .035, .03, (-.14, .14, 4.45), m["dark"], verts=8, rot=(0, rad(90), 0))
    p.box("label", (.012, .14, .07), (-.25, 0, 1.0), m["orange"], bevel=.002)
    xform(p.o, Matrix.Rotation(rad(-lean), 4, 'X'))
    return set_pivot(p.o)

def cable_reel(c):
    """Wooden cable drum 0.9 m: planked flanges, through-bolts, black cable wound on the core, loose end. Axle along Y."""
    p = P(c); m = mats(); R_, W_ = .45, .5
    for s in (-1, 1):
        y = s * (W_ / 2 - .025)
        p.cyl("flange", R_, .05, (0, y, R_), m["drum"], rot=(rad(90), 0, 0), verts=24)
        for i in range(8):
            a = i * math.pi / 8
            p.box("plank", (.16, .02, .76), (0, y + s * .03, R_), m["drum"], rot=(0, a, 0), bevel=.004)
        for i in range(4):
            a = i * math.tau / 4 + rad(45)
            p.cyl("bolt", .025, .03, (math.cos(a) * .3, y + s * .05, R_ + math.sin(a) * .3), m["steel"], rot=(rad(90), 0, 0), verts=6)
    p.cyl("core", .22, W_ - .1, (0, 0, R_), m["drum"], rot=(rad(90), 0, 0), verts=16)
    p.cyl("cable", .36, W_ - .14, (0, 0, R_), m["cableW"], rot=(rad(90), 0, 0), verts=24)
    p.cyl("axle", .03, W_ + .2, (0, 0, R_), m["steel"], rot=(rad(90), 0, 0), verts=8)
    p.tube("cable_end", (.3, -.1, R_ + .22), (.9, -.25, .02), .014, m["ink"], verts=5)
    p.tube("cable_end2", (.9, -.25, .02), (1.4, -.1, .02), .014, m["ink"], verts=5)
    p.txt("FIBRA ÓPTICA", .055, (0, -(W_ / 2 + .006), R_ + .02), m["ink"], face="-Y")
    p.txt("FRÁGIL", .045, (0, -(W_ / 2 + .006), R_ - .06), m["red"], face="-Y")
    for s in (-1, 1):
        p.box("chock", (.2, .12, .08), (s * .3, 0, .04), m["wood"], rot=(0, s * rad(-25), 0), bevel=.008)
    return set_pivot(p.o)

def cash_only_sign(c):
    """Door sign SÓ DINHEIRO with a crossed-out card. Hangs from the origin (hook) on two strings; faces -Y."""
    p = P(c); m = mats(); I = m["ink"]
    zc = -.42
    p.box("sign_bk", (.64, .012, .46), (0, .01, zc), m["red"], bevel=.006)
    p.box("sign", (.6, .025, .42), (0, 0, zc), m["yellow"], bevel=.01)
    p.txt("SÓ DINHEIRO", .082, (0, -.016, zc + .13), m["red"], face="-Y", res=2)
    p.txt("MAQUININHA FORA DO AR", .034, (0, -.016, zc + .05), I, face="-Y")
    p.box("card", (.17, .012, .11), (0, -.016, zc - .09), m["navy"], bevel=.012)
    p.box("card_stripe", (.17, .006, .024), (0, -.024, zc - .06), I, bevel=0)
    p.box("card_chip", (.03, .006, .022), (-.05, -.024, zc - .115), m["gold"], bevel=.003)
    for a in (45, -45):
        p.box("cross", (.24, .008, .03), (0, -.03, zc - .09), m["red"], rot=(0, rad(a), 0), bevel=0)
    for s in (-1, 1):
        p.tube("string", (s * .26, 0, zc + .21), (0, 0, -.01), .004, I, verts=4)
        p.cyl("eyelet", .012, .01, (s * .26, 0, zc + .19), m["chrome"], verts=8, rot=(rad(90), 0, 0))
    p.cyl("hook", .018, .02, (0, 0, -.0), m["chrome"], verts=8)
    return set_pivot(p.o)

@E.event
def v2_Maquininha(c):
    E.diorama(c); m = mats(); x, y = -3.8, -.9
    put(telecom_pole(c), x, y, z=.13)
    lean = 16.0; lx, ly = x + 1.32, y + .05   # ladder stands at +X of the pole and leans back (-X) against it
    put(ext_ladder(c, lean), lx, ly, z=.13, rot=rad(90))
    E.actor(c, "Customer_07", (lx - 3.05 * math.sin(rad(lean)) - .18, ly, .13 + 3.05 * math.cos(rad(lean))), rad(-90))
    put(cable_reel(c), x + 1.3, y + 1.3, z=.13, rot=rad(-12))
    put(V.telecom_van(c), 3.0, -2.95)
    E.actor(c, "Customer_09", (1.6, 3.4), rad(20)); E.actor(c, "Customer_06", (-1.2, 2.2), rad(230))
    put(cash_only_sign(c), .3, 5.28, z=1.95)

PROPS = {"Obras_Backhoe": (backhoe, 2048), "Obras_BackhoeArm": (backhoe_arm, 1024), "Obras_Pit": (pit, 1024),
         "Obras_Barrier": (road_barrier, 512), "Obras_DetourSign": (detour_sign, 512), "Obras_LightTower": (light_tower, 1024),
         "Energia_UtilityPole": (utility_pole, 1024), "Energia_Spark": (spark, 256), "Energia_Smoke": (smoke, 256),
         "Energia_BucketTruck": (bucket_truck, 2048), "Energia_BucketBoom": (bucket_boom, 1024),
         "Maquininha_TelecomPole": (telecom_pole, 1024), "Maquininha_CtoLed": (cto_led, 64), "Maquininha_Ladder": (ext_ladder, 512),
         "Maquininha_CableReel": (cable_reel, 512), "Maquininha_CashOnlySign": (cash_only_sign, 512)}

def export(names=None):
    out = {}
    for n in (names or PROPS):
        fn, size = PROPS[n]
        c = E.prop_collection(n); mats(); fn(c)
        out[n] = E.export_prop(n, size=size)
        print("EXPORTED", n, out[n], flush=True)
    return out
