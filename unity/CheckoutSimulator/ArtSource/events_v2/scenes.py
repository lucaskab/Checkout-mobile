# scenes.py - "people" event props v2 (Cafe com a equipe, Viralizou!, Fim do mes, Turno puxado).
# Builders model at the origin, ground z=0, the readable side facing -Y (icons: origin at their centre).
# Each returns the objects it created (place them with put()).  Export: PROPS / export().
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
if ART not in sys.path: sys.path.insert(0, ART)
if HERE not in sys.path: sys.path.insert(0, HERE)
import events_kit as E
import era_kit as k
import lot_kit as L
from vehicles import P, put, ROT
rad = math.radians
C = E.C

SM = {}
def checker(name, a, b, size=.08, rough=.85):
    """Gingham / checkered cloth (object space, XY)."""
    m, nt = k._new(name)
    if nt is None: return m
    n, Lk = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = rough
    tc = n.new("ShaderNodeTexCoord")
    ch = n.new("ShaderNodeTexChecker"); ch.inputs["Scale"].default_value = 1.0 / size
    ch.inputs["Color1"].default_value = a; ch.inputs["Color2"].default_value = b
    Lk.new(tc.outputs["Object"], ch.inputs["Vector"])
    noise = n.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 70; noise.inputs["Detail"].default_value = 5
    Lk.new(tc.outputs["Object"], noise.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = .35; mr.inputs["From Max"].default_value = .65
    mr.inputs["To Min"].default_value = .88; mr.inputs["To Max"].default_value = 1.08
    Lk.new(noise.outputs[0], mr.inputs[0])
    mul = n.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1
    Lk.new(ch.outputs["Color"], mul.inputs[6]); Lk.new(mr.outputs[0], mul.inputs[7])
    Lk.new(mul.outputs[2], bsdf.inputs["Base Color"])
    b_ = n.new("ShaderNodeBump"); b_.inputs["Strength"].default_value = .12
    Lk.new(noise.outputs[0], b_.inputs["Height"]); Lk.new(b_.outputs["Normal"], bsdf.inputs["Normal"])
    return m

def mats():
    m = E.mats()
    if SM: return SM
    SM.update(m)
    SM["gingham"] = checker("EV_Gingham", C["red"], (.97, .95, .90, 1), .07)
    SM["chalkboard"] = k.mat("EV_Chalkboard", (.11, .15, .13, 1), rough=.95, var=.18, scale=18, bump=.35)
    SM["chalk"] = k.mat("EV_Chalk", (.94, .94, .90, 1), rough=.95, var=.30, scale=40)
    SM["chalkY"] = k.mat("EV_ChalkYellow", (.98, .84, .30, 1), rough=.95, var=.30, scale=40)
    SM["chalkP"] = k.mat("EV_ChalkPink", (.98, .55, .65, 1), rough=.95, var=.30, scale=40)
    SM["steelD"] = k.mat("EV_SteelDoor", (.52, .56, .60, 1), rough=.55, var=.08, scale=5, metallic=.3, bump=.15)
    SM["steelL"] = k.mat("EV_SteelLight", (.80, .82, .84, 1), rough=.35, var=.05, scale=6, metallic=.5)
    SM["corr"] = k.stripes("EV_CorrAwn", (.07, .50, .46, 1), (.20, .66, .58, 1), .03, axis='X', rough=.5)
    SM["pinkD"] = k.mat("EV_PinkDeep", (.93, .30, .52, 1), rough=.6, var=.06, scale=6)
    SM["pinkL"] = k.mat("EV_PinkLight", (.99, .72, .80, 1), rough=.6, var=.05, scale=6)
    SM["neonPink"] = k.emissive("EV_NeonPink", (1.0, .20, .50, 1), 1.4)
    SM["neonW"] = k.emissive("EV_NeonWhite", (1.0, .92, .95, 1), 2.0)
    SM["diffuser"] = k.emissive("EV_Diffuser", (1.0, .98, .95, 1), 1.3)
    SM["acrylic"] = k.mat("EV_Acrylic", (.16, .10, .16, 1), rough=.25, var=.04, scale=6)
    SM["leather"] = k.mat("EV_Leather", (.40, .20, .09, 1), rough=.7, var=.12, scale=14, bump=.3)
    SM["leatherL"] = k.mat("EV_LeatherIn", (.88, .74, .52, 1), rough=.75, var=.10, scale=14)
    SM["moth"] = k.mat("EV_Moth", (.56, .46, .32, 1), rough=.9, var=.12, scale=20)
    SM["cardboard"] = k.mat("EV_CupSleeve", (.70, .50, .30, 1), rough=.9, var=.10, scale=10)
    SM["cupW"] = k.mat("EV_CupWhite", (.96, .95, .92, 1), rough=.6, var=.04, scale=10)
    SM["coffee"] = k.mat("EV_Coffee", (.22, .12, .06, 1), rough=.25, var=.05, scale=10)
    SM["energy"] = k.mat("EV_EnergyCan", (.10, .11, .13, 1), rough=.35, var=.05, scale=10, metallic=.4)
    SM["cloudW"] = k.mat("EV_Cloud", (.97, .97, .99, 1), rough=.8, var=.04, scale=6)
    SM["clockFace"] = k.mat("EV_ClockFace", (.97, .96, .92, 1), rough=.7, var=.03, scale=6)
    SM["vinyl"] = k.mat("EV_Vinyl", (.97, .95, .90, 1), rough=.5, var=.03, scale=8)
    SM["plasticT"] = k.mat("EV_PlasticTeal", (.08, .55, .50, 1), rough=.45, var=.05, scale=6)
    SM["rope"] = k.mat("EV_Rope", (.86, .80, .64, 1), rough=.9, var=.12, scale=40)
    SM["bannerR"] = k.mat("EV_BannerRed", (.88, .18, .14, 1), rough=.75, var=.06, scale=4, bump=.1)
    SM["tagY"] = k.mat("EV_TagYellow", (.99, .82, .14, 1), rough=.8, var=.04, scale=8)
    return SM

# ---------------------------------------------------------------- small helpers
def poly(c, name, pts, depth, m, bevel=.01, seg=2, loc=(0, 0, 0), rot=(0, 0, 0), smooth=False):
    """Extruded flat shape from 2D points (x, z) lying in the XZ plane (thickness along Y, centred)."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, 0, z)) for x, z in pts]
    bm.faces.new(vs); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); c.objects.link(o)
    sol = o.modifiers.new("Solid", 'SOLIDIFY'); sol.thickness = depth; sol.offset = 0; sol.use_even_offset = True
    k.finish(o, m, bevel, seg, smooth=smooth)
    o.location = loc; o.rotation_euler = rot
    return o

def heart_pts(size, n=36):
    out = []
    for i in range(n):
        t = i * math.tau / n
        x = 16 * math.sin(t) ** 3
        z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        out.append((x / 32 * size, (z + 2.5) / 32 * size))
    return out

def star_pts(r, n=12, inner=.78):
    return [((r if i % 2 == 0 else r * inner) * math.cos(i * math.pi / n + math.pi / 2),
             (r if i % 2 == 0 else r * inner) * math.sin(i * math.pi / n + math.pi / 2)) for i in range(2 * n)]

def uvball(c, name, r, loc, m, scale=(1, 1, 1), seg=12, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=r, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    k.link(o, c); k.finish(o, m, 0)
    return o

def torus(c, name, R, r, loc, m, rot=(rad(90), 0, 0), maj=24, mn=6):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot, major_segments=maj, minor_segments=mn)
    o = bpy.context.active_object; o.name = name; k.link(o, c); k.finish(o, m, 0)
    return o

def tri_legs(p, top, R, z_feet=0.0, r=.012, m=None, feet=True, a0=90):
    """Three tripod legs from a hub at `top` to feet on a circle of radius R."""
    m = m or mats()["dark"]
    for i in range(3):
        a = rad(a0 + 120 * i); f = (math.cos(a) * R, math.sin(a) * R, z_feet)
        p.tube("leg", f, top, r, m, verts=6)
        if feet: p.cyl("foot", r * 2.2, .02, (f[0], f[1], .01), mats()["rubber"], verts=8)

# ================================================================== 1. CAFE COM A EQUIPE
def break_table(c):
    """Folding table 1.8 x .8 m with X steel legs, red/white gingham cloth, thermos, pao de queijo, cups, sugar bowl."""
    p = P(c); m = mats(); W_, D, H = 1.8, .8, .74
    p.box("table_top", (W_, D, .04), (0, 0, H - .02), m["vinyl"], bevel=.01)
    p.box("table_rail", (W_ + .02, D + .02, .025), (0, 0, H - .035), m["steelL"], bevel=.006)
    for sx in (-1, 1):
        x = sx * (W_ / 2 - .22)
        for a, b in (((x, -D / 2 + .05, .01), (x, D / 2 - .05, H - .05)), ((x, D / 2 - .05, .01), (x, -D / 2 + .05, H - .05))):
            p.tube("leg", a, b, .014, m["steelL"], verts=8)
        p.box("leg_foot", (.05, D - .1, .03), (x, 0, .015), m["rubber"], bevel=.008)
        p.cyl("leg_pivot", .025, .06, (x, 0, H / 2 - .02), m["dark"], rot=(0, rad(90), 0), verts=10)
    p.box("leg_brace", (W_ - .5, .025, .025), (0, 0, H - .07), m["steelL"], bevel=.004)
    cl = k.cloth("tablecloth", W_ + .06, D + .06, H + .005, .26, m["gingham"], c=c)
    cl.modifiers["Sub"].levels = cl.modifiers["Sub"].render_levels = 0
    cl.modifiers["Folds"].strength = .025
    cl.modifiers.remove(cl.modifiers["Thick"]); p.o.append(cl)
    zt = H + .006
    # garrafa termica (red pump thermos)
    tx, ty = -.55, .12
    p.cyl("thermos_base", .085, .03, (tx, ty, zt + .015), m["dark"], verts=18)
    p.cyl("thermos", .085, .24, (tx, ty, zt + .15), m["red"], verts=18)
    p.cyl("thermos_band", .087, .025, (tx, ty, zt + .19), m["white"], verts=18)
    p.cyl("thermos_top", .07, .05, (tx, ty, zt + .295), m["dark"], verts=18)
    p.cyl("thermos_pump", .035, .05, (tx, ty, zt + .34), m["red"], verts=12)
    p.cyl("thermos_spout", .012, .09, (tx, ty - .10, zt + .28), m["dark"], rot=(rad(90), 0, 0), verts=8)
    p.cyl("thermos_spout_tip", .012, .04, (tx, ty - .145, zt + .265), m["dark"], verts=8)
    p.tube("thermos_handle", (tx + .08, ty, zt + .27), (tx + .13, ty, zt + .27), .012, m["dark"], verts=8)
    p.tube("thermos_handle", (tx + .13, ty, zt + .27), (tx + .13, ty, zt + .10), .012, m["dark"], verts=8)
    p.tube("thermos_handle", (tx + .13, ty, zt + .10), (tx + .08, ty, zt + .10), .012, m["dark"], verts=8)
    # plate of pao de queijo
    px, py = .25, -.08
    p.cyl("plate", .20, .012, (px, py, zt + .006), m["cupW"], verts=24)
    p.cyl("plate_rim", .20, .016, (px, py, zt + .018), m["cupW"], verts=24, r2=.17)
    p.cyl("napkin", .17, .004, (px, py, zt + .028), m["paper"], verts=8)
    for i in range(8):
        a = i * 2.4 + .4; r = .06 + .09 * (i % 3) / 2
        p.ball("pao_de_queijo", .045, (px + math.cos(a) * r, py + math.sin(a) * r, zt + .07), m["gold"], sub=1, scale=(1, .95, .85))
    # cups with coffee (white ceramic, little handles)
    for (cx, cy, ca) in ((-.15, -.25, 20), (.62, .22, 200), (-.25, .28, 120), (.70, -.22, -40)):
        p.cyl("cup", .042, .085, (cx, cy, zt + .043), m["cupW"], r2=.036, verts=12)
        p.cyl("coffee", .038, .006, (cx, cy, zt + .082), m["coffee"], verts=12)
        hx, hy = cx + math.cos(rad(ca)) * .05, cy + math.sin(rad(ca)) * .05
        t = torus(c, "cup_handle", .018, .006, (hx, hy, zt + .05), m["cupW"], rot=(rad(90), 0, rad(ca)), maj=8, mn=4); p.o.append(t)
    # sugar bowl + spoon, napkin stack
    sx_, sy_ = .55, -.02
    p.cyl("sugar_bowl", .055, .07, (sx_, sy_, zt + .035), m["cupW"], verts=14)
    p.cyl("sugar_lid", .06, .015, (sx_, sy_, zt + .077), m["cupW"], verts=14)
    p.ball("sugar_knob", .013, (sx_, sy_, zt + .092), m["cupW"], sub=1)
    p.box("spoon", (.11, .022, .005), (sx_ + .11, sy_ + .07, zt + .003), m["chrome"], rot=(0, 0, rad(25)), bevel=.002)
    p.box("napkins", (.14, .14, .03), (-.2, .0, zt + .015), m["paper"], rot=(0, 0, rad(12)), bevel=.004)
    return p.o

def folding_chair(c):
    """Steel-tube folding chair, teal plastic seat and back, facing -Y."""
    p = P(c); m = mats(); r = .011
    # front frame: feet at the front, rises into the backrest
    for s in (-1, 1):
        p.tube("frame_f", (s * .21, -.21, .01), (s * .21, .14, .86), r, m["steelL"], verts=8)
        p.tube("frame_r", (s * .19, .22, .01), (s * .19, -.17, .47), r, m["steelL"], verts=8)
        p.cyl("pivot", .018, .012, (s * .21 + s * .012, -.02, .43), m["dark"], rot=(0, rad(90), 0), verts=8)
        for yy, zz in ((-.21, .01), (.22, .01)):
            p.cyl("cap", .016, .025, (s * .2, yy, .012), m["rubber"], verts=8)
    p.tube("frame_top", (-.21, .14, .86), (.21, .14, .86), r, m["steelL"], verts=8)
    p.tube("frame_bar", (-.21, -.21, .01), (.21, -.21, .01), r, m["steelL"], verts=8)
    p.tube("frame_bar", (-.19, .22, .01), (.19, .22, .01), r, m["steelL"], verts=8)
    p.tube("frame_bar", (-.19, -.17, .47), (.19, -.17, .47), r, m["steelL"], verts=8)
    p.box("seat", (.42, .40, .035), (0, -.01, .455), m["plasticT"], rot=(rad(-3), 0, 0), bevel=.012, seg=2)
    p.box("back", (.42, .03, .20), (0, .135, .75), m["plasticT"], rot=(rad(8), 0, 0), bevel=.012, seg=2)
    return p.o

def back_door(c):
    """Steel staff door with frame, push bar, kick plate, vent, SO FUNCIONARIOS plate, lamp and a corrugated awning.
    Back face at y=+.06 (stand against the wall); the door faces -Y."""
    p = P(c); m = mats(); W_, H = 1.0, 2.15
    p.box("door_frame", (W_ + .18, .12, H + .1), (0, 0, (H + .1) / 2), m["dark"], bevel=.012)
    p.box("door_frame_in", (W_ + .04, .13, H + .02), (0, 0, (H + .02) / 2), m["steelD"], bevel=.006)
    p.box("door", (W_, .05, H), (0, -.05, H / 2), m["steelD"], bevel=.012, seg=2)
    for zc, hh in ((1.55, .7), (.62, .62)):
        p.box("panel_seam", (W_ - .22, .006, hh), (0, -.078, zc), m["ink"], bevel=0)
        p.box("panel", (W_ - .24, .012, hh - .02), (0, -.081, zc), m["steelD"], bevel=.006)
    p.box("kick_plate", (W_ - .1, .008, .28), (0, -.08, .17), m["steelL"], bevel=.003)
    for i in range(5):
        p.box("vent", (.36, .01, .012), (0, -.082, .40 + i * .035), m["ink"], bevel=0)
    p.box("push_bar", (W_ - .2, .05, .055), (0, -.11, 1.02), m["steelL"], bevel=.012, seg=2)
    for s in (-1, 1):
        p.box("push_bar_mount", (.06, .05, .09), (s * (W_ / 2 - .14), -.095, 1.02), m["dark"], bevel=.008)
        p.box("hinge", (.025, .07, .14), (-W_ / 2 - .005, -.05, .5 + s * .6 + .6), m["steelL"], bevel=.004)
    p.box("hinge", (.025, .07, .14), (-W_ / 2 - .005, -.05, 1.1), m["steelL"], bevel=.004)
    p.cyl("lock", .022, .02, (W_ / 2 - .12, -.085, 1.02), m["chrome"], rot=(rad(90), 0, 0), verts=10)
    p.cyl("peephole", .015, .01, (0, -.08, 1.38), m["chrome"], rot=(rad(90), 0, 0), verts=8)
    p.box("plate", (.74, .02, .2), (0, -.085, 1.60), m["red"], bevel=.006)
    p.box("plate_border", (.70, .006, .16), (0, -.097, 1.60), m["white"], bevel=0)
    p.box("plate_inner", (.68, .004, .14), (0, -.1, 1.60), m["red"], bevel=0)
    p.txt("SÓ FUNCIONÁRIOS", .082, (0, -.102, 1.60), m["white"], face="-Y", res=2)
    for s in (-1, 1):
        p.cyl("plate_screw", .008, .01, (s * .34, -.097, 1.60), m["chrome"], rot=(rad(90), 0, 0), verts=6)
    # step + mat
    p.box("step", (W_ + .4, .5, .04), (0, -.25, .02), m["concrete"], bevel=.01)
    p.box("doormat", (.7, .42, .015), (0, -.3, .048), m["rubber"], bevel=.004)
    # lamp over the door
    p.box("lamp_box", (.18, .12, .1), (0, -.06, H + .2), m["dark"], bevel=.012)
    p.box("lamp_lens", (.14, .04, .07), (0, -.125, H + .2), m["lamp"], bevel=.01)
    # awning: corrugated sheet on two tube brackets
    aw_d, aw_z = .7, H + .32
    for s in (-1, 1):
        x = s * (W_ / 2 + .12)
        p.tube("awn_bracket", (x, -.02, aw_z - .55), (x, -aw_d + .08, aw_z - .15), .014, m["dark"], verts=6)
        p.tube("awn_bracket", (x, -.02, aw_z - .04), (x, -aw_d + .08, aw_z - .15), .014, m["dark"], verts=6)
        p.box("awn_plate", (.05, .05, .6), (x, -.0, aw_z - .32), m["dark"], bevel=.006)
    aw = [p.box("awning", (W_ + .3, aw_d, .025), (0, -aw_d / 2, aw_z), m["corr"], bevel=.006),
          p.box("awning_lip", (W_ + .32, .03, .08), (0, -aw_d + .015, aw_z - .03), m["teal"], bevel=.006),
          p.box("awning_rail", (W_ + .32, .03, .04), (0, -.01, aw_z + .03), m["teal"], bevel=.006)]
    for o in aw:   # slope down towards the street, hinged at the wall edge
        o.matrix_world = Matrix.Translation((0, 0, aw_z)) @ Matrix.Rotation(rad(12), 4, 'X') @ Matrix.Translation((0, 0, -aw_z)) @ o.matrix_world
    return p.o

def coffee_board(c):
    """Wooden easel chalkboard: PAUSA PRO CAFÉ with a chalk cup icon; faces -Y, leans back a little."""
    p = P(c); m = mats(); tilt = rad(-8)
    bw, bh = .70, .95; z0 = .55
    hold = []
    hold.append(p.box("board_frame", (bw, .035, bh), (0, 0, z0 + bh / 2), m["wood"], bevel=.008))
    hold.append(p.box("board", (bw - .09, .012, bh - .09), (0, -.015, z0 + bh / 2), m["chalkboard"], bevel=0))
    hold.append(p.box("chalk_tray", (bw - .1, .07, .025), (0, -.045, z0 + .02), m["wood"], bevel=.005))
    hold.append(p.cyl("chalk", .007, .07, (-.12, -.055, z0 + .04), m["chalk"], rot=(0, rad(90), 0), verts=6))
    hold.append(p.txt("PAUSA", .17, (0, -.024, z0 + bh - .22), m["chalkY"], face="-Y", res=3))
    hold.append(p.txt("PRO CAFÉ", .12, (0, -.024, z0 + bh - .42), m["chalk"], face="-Y", res=3))
    cx, cz = -.03, z0 + .25
    hold.append(p.cyl("cup_icon", .075, .13, (cx, -.028, cz), m["chalk"], r2=.06, rot=(rad(90), 0, 0) if False else (0, 0, 0), verts=12))
    hold.append(p.box("cup_coffee", (.12, .006, .012), (cx, -.034, cz + .06), m["chalkboard"], bevel=0))
    t = torus(c, "cup_icon_handle", .035, .009, (cx + .09, -.028, cz), m["chalk"], rot=(rad(90), 0, 0), maj=10, mn=4); hold.append(t); p.o.append(t)
    for i, dx in enumerate((-.04, 0, .04)):
        hold.append(p.tube("steam", (cx + dx, -.028, cz + .1), (cx + dx + .015, -.028, cz + .17), .006, m["chalk"], verts=4))
        hold.append(p.tube("steam", (cx + dx + .015, -.028, cz + .17), (cx + dx, -.028, cz + .23), .006, m["chalk"], verts=4))
    for s in (-1, 1):
        hold.append(p.box("easel_leg", (.04, .035, 1.55), (s * .30, .0, .775), m["wood"], bevel=.006))
    hold.append(p.box("easel_bar", (.72, .035, .04), (0, 0, z0 - .03), m["wood"], bevel=.006))
    hold.append(p.box("easel_top", (.14, .035, .05), (0, 0, 1.53), m["wood"], bevel=.006))
    for o in hold:
        o.matrix_world = Matrix.Translation((0, 0, 0)) @ Matrix.Rotation(tilt, 4, 'X') @ o.matrix_world
    p.box("easel_leg_r", (.04, .035, 1.45), (0, .42, .72), m["wood"], rot=(rad(16), 0, 0), bevel=.006)
    p.box("easel_hinge", (.16, .14, .035), (0, .17, 1.41), m["dark"], bevel=.006)
    return p.o

@E.event
def v2_CafeComEquipe(c):
    E.diorama(c, road=False, depth=8)
    put(back_door(c), x=-2.2, y=3.34, z=.13)
    put(coffee_board(c), x=-1.2, y=3.0, z=.13, rot=rad(10))
    put(break_table(c), x=.9, y=1.3, z=.13, rot=rad(-6))
    put(folding_chair(c), x=-.5, y=1.3, z=.13, rot=rad(-90))
    put(folding_chair(c), x=2.3, y=1.4, z=.13, rot=rad(95))
    put(folding_chair(c), x=1.0, y=2.2, z=.13, rot=rad(180))
    k.crate("crate", (2.6, 2.9, .13), m=mats()["wood"], c=c, rot_z=rad(15))
    k.crate("crate", (2.6, 2.9, .40), m=mats()["wood"], c=c, rot_z=rad(-5))
    for (px, py, who, r) in ((-.55, .55, "Customer_07", 60), (2.35, .6, "Customer_09", 120), (1.0, 2.75, "Customer_06", 185)):
        E.actor(c, who, (px, py), rad(r))

# ================================================================== 2. VIRALIZOU!
def ring_light_tripod(c):
    """Tripod + 10" ring light + phone holder with a phone; the phone screen faces -Y (the influencer stands at -Y)."""
    p = P(c); m = mats(); hz = 1.05
    tri_legs(p, (0, 0, hz), .42, r=.013)
    for i in range(3):
        a = rad(90 + 120 * i)
        p.tube("brace", (0, 0, hz - .26), (math.cos(a) * .16, math.sin(a) * .16, hz - .40), .007, m["dark"], verts=5)
    p.cyl("hub", .035, .09, (0, 0, hz), m["dark"], verts=10, bevel=.006)
    p.cyl("column", .016, .70, (0, 0, hz + .35), m["steelL"], verts=8)
    p.cyl("column_lock", .028, .04, (0, 0, hz + .10), m["dark"], verts=10)
    p.cyl("column_lock", .028, .04, (0, 0, hz + .66), m["dark"], verts=10)
    rz = hz + .98; R = .26
    p.cyl("ring_mount", .03, .14, (0, 0, rz - R - .05), m["dark"], verts=10)
    p.box("ring_knob", (.06, .025, .025), (.045, 0, rz - R - .04), m["dark"], bevel=.006)
    t = torus(c, "ring_housing", R, .045, (0, 0, rz), m["dark"], maj=28, mn=8); p.o.append(t)
    t = torus(c, "ring_led", R, .034, (0, -.018, rz), m["lamp"], maj=28, mn=6); p.o.append(t)
    p.box("ring_bridge", (.04, .03, .20), (0, .03, rz - R + .02), m["dark"], bevel=.005)
    # phone holder clamp in the middle of the ring
    p.cyl("holder_arm", .012, .22, (0, .03, rz - .11), m["dark"], verts=8)
    p.cyl("ball_head", .022, .022, (0, .03, rz), m["dark"], verts=10)
    p.box("clamp", (.095, .022, .06), (0, .005, rz), m["dark"], bevel=.006)
    for s in (-1, 1):
        p.box("clamp_jaw", (.012, .03, .17), (s * .048, .003, rz), m["dark"], bevel=.004)
    p.box("phone", (.08, .012, .165), (0, -.004, rz), m["dark"], bevel=.006, seg=2)
    p.box("phone_screen", (.072, .004, .152), (0, -.011, rz), m["screen"], bevel=0)
    p.box("phone_camera", (.02, .004, .03), (-.025, .0045, rz + .06), m["ink"], bevel=.002)
    # cable to the ground + remote
    p.tube("cable", (0, .05, rz - R), (0, .05, hz + .1), .005, m["dark"], verts=4)
    p.tube("cable", (0, .05, hz + .1), (.25, .25, .01), .005, m["dark"], verts=4)
    return p.o

def backdrop(c):
    """Pink backdrop on two stands (base feet + sandbags), neon heart on a dark acrylic plate, #VIRALIZOU.  Faces -Y."""
    p = P(c); m = mats(); W_, H = 2.1, 2.2; sx = W_ / 2 + .12
    for s in (-1, 1):
        p.cyl("stand", .022, H + .1, (s * sx, 0, (H + .1) / 2), m["steelL"], verts=8)
        p.cyl("stand_lock", .034, .05, (s * sx, 0, 1.1), m["dark"], verts=10)
        p.cyl("stand_lock", .034, .05, (s * sx, 0, H + .02), m["dark"], verts=10)
        p.box("foot_t", (.06, .9, .05), (s * sx, 0, .025), m["dark"], bevel=.01)
        p.box("foot_x", (.55, .06, .05), (s * (sx - .22), 0, .025), m["dark"], bevel=.01)
        p.box("sandbag", (.22, .34, .14), (s * sx, .18, .10), m["navy"], rot=(0, 0, rad(10 * s)), bevel=.04, seg=2)
    p.cyl("crossbar", .018, W_ + .3, (0, 0, H + .12), m["steelL"], rot=(0, rad(90), 0), verts=8)
    for s in (-1, 1):
        for i in range(2):
            p.box("clip", (.05, .07, .035), (s * (W_ / 2 - .25 - i * .3), 0, H + .11), m["dark"], bevel=.006)
    p.box("drape", (W_, .025, H), (0, 0, H / 2 + .05), m["pinkD"], bevel=.01, seg=2)
    p.box("drape_hem", (W_ + .02, .03, .09), (0, 0, .1), m["pinkL"], bevel=.006)
    # soft stripe pattern + stars on the drape
    for i in range(4):
        p.box("drape_stripe", (W_ - .3, .006, .02), (0, -.016, 1.95 - i * .06), m["pinkL"], bevel=0)
    for (x, z, r) in ((-.8, 1.3, .07), (.85, 1.85, .06), (-.7, .55, .05), (.8, .5, .07)):
        p.o.append(poly(c, "star", star_pts(r, 5, .45), .012, m["pinkL"], bevel=0, loc=(x, -.02, z)))
    # neon heart: dark acrylic plate, glowing tube outline, inner white tube
    p.o.append(poly(c, "neon_plate", heart_pts(.80), .03, m["acrylic"], bevel=0, loc=(0, -.03, 1.45)))
    hp = heart_pts(.70, 24)
    for i in range(24):
        a, b = Vector((hp[i][0], 0, hp[i][1])), Vector((hp[(i + 1) % 24][0], 0, hp[(i + 1) % 24][1]))
        p.tube("neon", a + Vector((0, -.06, 1.45)), b + Vector((0, -.06, 1.45)), .022, m["neonPink"], verts=5)
    hp = heart_pts(.42, 20)
    for i in range(20):
        a, b = Vector((hp[i][0], 0, hp[i][1])), Vector((hp[(i + 1) % 20][0], 0, hp[(i + 1) % 20][1]))
        p.tube("neon_in", a + Vector((0, -.06, 1.47)), b + Vector((0, -.06, 1.47)), .014, m["neonW"], verts=5)
    p.box("neon_box", (.16, .06, .08), (.9, .0, .3), m["dark"], bevel=.008)
    p.tube("neon_cable", (.9, -.03, .34), (.3, -.045, 1.2), .006, m["dark"], verts=4)
    # hashtag plate
    p.box("tag_plate", (1.5, .02, .34), (0, -.028, .72), m["white"], bevel=.008)
    p.txt("#VIRALIZOU", .22, (0, -.041, .71), m["pinkD"], face="-Y", res=3)
    p.box("live_badge", (.4, .02, .16), (-.78, -.028, 1.95), m["red"], bevel=.01)
    p.txt("AO VIVO", .09, (-.75, -.041, 1.95), m["white"], face="-Y", res=2)
    p.cyl("live_dot", .025, .01, (-.93, -.04, 1.95), m["white"], rot=(rad(90), 0, 0), verts=10)
    return p.o

def softbox(c):
    """Softbox on a light stand, tilted 25 degrees down, opening towards -Y."""
    p = P(c); m = mats(); hz = .9
    tri_legs(p, (0, 0, hz), .45, r=.014)
    p.cyl("hub", .04, .1, (0, 0, hz), m["dark"], verts=10, bevel=.006)
    p.cyl("column", .018, .95, (0, 0, hz + .47), m["steelL"], verts=8)
    p.cyl("column_lock", .03, .04, (0, 0, hz + .15), m["dark"], verts=10)
    p.cyl("column2", .014, .5, (0, 0, hz + 1.18), m["steelL"], verts=8)
    p.cyl("column_lock", .03, .04, (0, 0, hz + .95), m["dark"], verts=10)
    zt = hz + 1.42
    p.box("tilt_bracket", (.08, .07, .09), (0, 0, zt), m["dark"], bevel=.01)
    p.cyl("tilt_knob", .03, .03, (.055, 0, zt), m["dark"], rot=(0, rad(90), 0), verts=10)
    tilt = rad(25)
    body = p.prism("softbox_body", -.11, .11, -.30, .30, .11, .0, .45, m["dark"], yt=.30, bevel=.02, seg=2)
    rot = Matrix.Rotation(rad(90), 4, 'X') @ Matrix.Rotation(0, 4, 'Z')
    tiltM = Matrix.Rotation(-tilt, 4, 'X')
    diff = p.box("diffuser", (.56, .56, .02), (0, 0, .46), m["diffuser"], bevel=0)
    rim = p.box("softbox_rim", (.62, .62, .03), (0, 0, .45), m["steelL"], bevel=.006)
    cut = p.box("softbox_rim_in", (.56, .56, .035), (0, 0, .45), None, bevel=0); p.cut(rim, cut)
    speed = p.cyl("speedring", .085, .10, (0, 0, -.04), m["dark"], verts=12)
    head = p.box("flash_head", (.14, .12, .16), (0, .0, -.16), m["dark"], bevel=.015, seg=2)
    for o in (body, diff, rim, speed, head):
        o.matrix_world = Matrix.Translation((0, -.04, zt)) @ tiltM @ rot @ o.matrix_world
    p.tube("cable", (0, .08, zt - .1), (.1, .3, .01), .005, m["dark"], verts=4)
    p.box("sandbag", (.34, .22, .14), (.25, .3, .08), m["navy"], rot=(0, 0, rad(-30)), bevel=.04, seg=3)
    return p.o

def heart_pop(c):
    """Stylised 'like' heart, origin at its centre, front -Y."""
    p = P(c); m = mats()
    p.o.append(poly(c, "heart", heart_pts(.44), .14, m["red"], bevel=.03, seg=3, loc=(0, 0, -.02)))
    p.o.append(poly(c, "heart_rim", heart_pts(.50), .05, m["white"], bevel=.012, seg=2, loc=(0, 0, -.02)))
    p.o.append(uvball(c, "shine", .045, (-.1, -.085, .1), m["white"], scale=(1.3, .4, .8), seg=10, rings=6))
    return p.o

@E.event
def v2_Viralizou(c):
    E.diorama(c)
    put(backdrop(c), x=2.6, y=3.1, z=.13)
    put(ring_light_tripod(c), x=1.9, y=.4, z=.13, rot=rad(180))
    put(softbox(c), x=.4, y=2.5, z=.13, rot=rad(45))
    E.actor(c, "Customer_06", (1.9, 2.3), rad(0))      # the influencer at the backdrop
    for (px, py, who, r) in ((-.2, -.2, "Customer_08", 50), (-1.2, .9, "Customer_07", 70), (.9, -.9, "Customer_09", 30)):
        E.actor(c, who, (px, py), rad(r))
    for i, (hx, hy, hz, s) in enumerate(((1.2, 1.5, 2.7, .8), (2.5, 1.6, 3.1, .6), (3.2, 2.4, 2.6, .45), (.8, 1.9, 3.3, .5))):
        objs = heart_pop(c)
        for o in objs: o.matrix_world = Matrix.Translation((hx, hy, hz)) @ Matrix.Rotation(rad(-20 + i * 15), 4, 'Z') @ Matrix.Scale(s, 4) @ o.matrix_world

# ================================================================== 3. FIM DO MES
def sale_banner(c):
    """4 m vinyl banner LIQUIDA TUDO / ATÉ -50% with grommets and tie ropes; hangs 2.1-3.3 m above z=0, face -Y.
    Place its origin at the foot of the facade (banner centre 2.7 m up)."""
    p = P(c); m = mats(); W_, H, zc = 4.0, 1.15, 2.95
    p.box("banner", (W_, .025, H), (0, 0, zc), m["bannerR"], bevel=.006)
    p.box("banner_border", (W_ - .12, .008, H - .12), (0, -.015, zc), m["yellow"], bevel=0)
    p.box("banner_inner", (W_ - .2, .008, H - .2), (0, -.018, zc), m["bannerR"], bevel=0)
    p.txt("LIQUIDA TUDO", .40, (0, -.028, zc + .20), m["yellow"], face="-Y", res=3)
    p.txt("ATÉ -50%", .33, (0, -.028, zc - .25), m["white"], face="-Y", res=3)
    for s in (-1, 1):
        p.o.append(poly(c, "burst", star_pts(.30, 10, .7), .012, m["yellow"], bevel=0, loc=(s * (W_ / 2 - .40), -.028, zc)))
        p.txt("SÓ", .10, (s * (W_ / 2 - .40), -.04, zc + .07), m["red"], face="-Y", res=2)
        p.txt("HOJE", .10, (s * (W_ / 2 - .40), -.04, zc - .07), m["red"], face="-Y", res=2)
        for z in (zc - H / 2 + .08, zc + H / 2 - .08):
            p.cyl("grommet", .025, .035, (s * (W_ / 2 - .08), 0, z), m["chrome"], rot=(rad(90), 0, 0), verts=10)
            p.tube("rope", (s * (W_ / 2 - .08), 0, z), (s * (W_ / 2 + .25), 0, z + (.2 if z > zc else -.2)), .008, m["rope"], verts=5)
    return p.o

def aframe(c):
    """A-frame sidewalk chalkboard: wooden frames, -50% in chalk, chalk prices, chain between the legs.  Front -Y."""
    p = P(c); m = mats(); w, h, spread = .62, .92, rad(16)
    for s in (-1, 1):
        objs = []
        objs.append(p.box("frame", (w, .035, h), (0, 0, h / 2), m["wood"], bevel=.008))
        objs.append(p.box("board", (w - .1, .012, h - .14), (0, -s * .014, h / 2 - .01), m["chalkboard"], bevel=0))
        objs.append(p.box("header", (w - .1, .012, .09), (0, -s * .014, h - .08), m["red"], bevel=0))
        face = "-Y" if s > 0 else "+Y"
        objs.append(p.txt("OFERTAS", .06, (0, -s * .022, h - .085), m["white"], face=face, res=2))
        objs.append(p.txt("-50%", .26, (0, -s * .022, h / 2 + .06), m["chalkY"], face=face, res=3))
        objs.append(p.txt("ARROZ 9,90", .075, (0, -s * .022, h / 2 - .2), m["chalk"], face=face, res=2))
        objs.append(p.txt("FEIJÃO 5,99", .075, (0, -s * .022, h / 2 - .32), m["chalk"], face=face, res=2))
        for o in objs:
            o.matrix_world = Matrix.Translation((0, 0, h + .02)) @ Matrix.Rotation(-s * spread, 4, 'X') @ Matrix.Translation((0, 0, -h - .02)) @ Matrix.Translation((0, -s * .02, 0)) @ o.matrix_world
    p.cyl("hinge", .02, w + .02, (0, 0, h + .02), m["dark"], rot=(0, rad(90), 0), verts=8)
    for s in (-1, 1):
        p.box("hinge_strap", (.06, .04, .12), (s * (w / 2 - .06), 0, h - .04), m["dark"], bevel=.005)
    yl = (h - .35) * math.tan(spread) + .02
    for i in range(9):
        t = i / 8; y = -yl + 2 * yl * t; z = .35 - .05 * 4 * t * (1 - t)
        p.box("chain", (.012, .035, .012), (0, y, z), m["chrome"], rot=(0, 0, 0), bevel=.002)
    return p.o

def price_tags(c):
    """3 m string of hanging yellow OFERTA tags and red -50% bursts, with end hooks. Hangs 2.0-2.5 m above z=0."""
    p = P(c); m = mats(); n = 14; a, b = Vector((-1.5, 0, 2.25)), Vector((1.5, 0, 2.25))
    pts = [a.lerp(b, i / n) - Vector((0, 0, .32 * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]
    for i in range(n):
        p.tube("string", pts[i], pts[i + 1], .006, m["rope"], verts=4)
    for s in (-1, 1):
        p.tube("hook", (s * 1.5, 0, 2.25), (s * 1.5, 0, 2.37), .008, m["chrome"], verts=5)
        p.tube("hook", (s * 1.5, 0, 2.37), (s * 1.5, .06, 2.41), .008, m["chrome"], verts=5)
    for i in range(1, n, 2):
        q = pts[i]; x, z = q.x, q.z
        if (i // 2) % 2 == 0:
            p.tube("tag_string", (x, 0, z), (x, 0, z - .08), .004, m["rope"], verts=4)
            p.o.append(poly(c, "tag", [(-.12, 0), (.12, 0), (.12, -.26), (0, -.34), (-.12, -.26)], .012, m["tagY"], bevel=.004, loc=(x, 0, z - .08)))
            p.cyl("tag_eyelet", .014, .018, (x, 0, z - .11), m["chrome"], rot=(rad(90), 0, 0), verts=8)
            p.txt("OFERTA", .055, (x, -.012, z - .25), m["red"], face="-Y", res=2)
        else:
            p.tube("tag_string", (x, 0, z), (x, 0, z - .06), .004, m["rope"], verts=4)
            p.o.append(poly(c, "burst", star_pts(.17, 10, .72), .012, m["red"], bevel=0, loc=(x, 0, z - .22)))
            p.txt("-50%", .085, (x, -.012, z - .22), m["white"], face="-Y", res=2)
    return p.o

def empty_wallet(c):
    """Open empty leather wallet with a moth flying out, origin at the centre, front -Y."""
    p = P(c); m = mats(); w, h = .42, .30
    for s, ang in ((-1, 62), (1, -22)):
        objs = []
        objs.append(p.box("flap", (w, .035, h), (0, 0, h / 2), m["leather"], bevel=.012, seg=2))
        objs.append(p.box("lining", (w - .05, .01, h - .05), (0, -s * .02, h / 2), m["leatherL"], bevel=.004))
        objs.append(p.box("stitch", (w - .03, .003, .004), (0, -s * .022, h - .03), m["ink"], bevel=0))
        objs.append(p.box("stitch", (w - .03, .003, .004), (0, -s * .022, .03), m["ink"], bevel=0))
        for j in range(3):
            objs.append(p.box("card_slot", (w * .45, .006, .07), (-s * w * .22, -s * .026, .05 + j * .055), m["leather"], bevel=.004))
            objs.append(p.box("slot_edge", (w * .45, .003, .006), (-s * w * .22, -s * .03, .085 + j * .055), m["ink"], bevel=0))
        objs.append(p.box("bill_pocket", (w * .42, .006, h - .1), (s * w * .24, -s * .024, h / 2 + .02), m["leatherL"], bevel=.004))
        for o in objs:
            o.matrix_world = Matrix.Translation((0, 0, -.1)) @ Matrix.Rotation(rad(ang), 4, 'X') @ o.matrix_world
    p.box("spine", (w, .05, .06), (0, 0, -.1), m["leather"], bevel=.015, seg=2)
    # moth flying out (wings in the XY plane, slightly raised in a V)
    mx, my, mz = .05, -.03, .36
    p.ball("moth_body", .02, (mx, my, mz), m["moth"], sub=1, scale=(.7, 1.9, .7))
    p.ball("moth_head", .017, (mx, my - .05, mz + .008), m["dark"], sub=1)
    wing = [(x * .75, z * .75) for x, z in [(0, .035), (.05, .075), (.13, .085), (.18, .045), (.15, -.01), (.10, -.035), (.12, -.09), (.08, -.13), (.02, -.10), (0, -.05)]]
    for sx in (-1, 1):
        for name, pts, lift in (("moth_wing", wing, 16),):
            w_ = poly(c, name, [(sx * x, z) for x, z in pts][::sx], .006, m["moth"], bevel=.006, seg=1)
            w_.rotation_euler = (rad(90), sx * rad(lift), 0); w_.location = (mx + sx * .01, my, mz)
            p.o.append(w_)
        p.o.append(poly(c, "moth_spot", star_pts(.016, 6, .6), .004, m["dark"], bevel=0, loc=(mx + sx * .075, my - .03, mz + .03), rot=(rad(90), sx * rad(18), 0)))
        p.tube("antenna", (mx + sx * .008, my - .06, mz + .015), (mx + sx * .045, my - .10, mz + .055), .003, m["dark"], verts=3)
    # a single sad coin at the bottom
    p.cyl("coin", .03, .005, (-.1, .0, -.12), m["gold"], verts=12)
    return p.o

@E.event
def v2_FimDoMes(c):
    E.diorama(c); m = mats()
    for o in list(c.objects):   # the neighbour shop replaces the left window of the market facade
        if o.name.split(".")[0] in ("window", "sill", "awn") and o.location.x < -1: bpy.data.objects.remove(o, do_unlink=True)
    k.box("neighbour", (5.2, .3, 3.6), (-4.6, 5.0, 1.8), m["sky"], bevel=.02, c=c)
    k.box("neighbour_base", (5.2, .34, .45), (-4.6, 5.0, .35), m["navy"], bevel=.02, c=c)
    k.box("neighbour_door", (1.4, .06, 2.2), (-4.6, 4.82, 1.23), m["glass"], bevel=.01, c=c)
    k.box("neighbour_window", (1.6, .06, 1.4), (-2.7, 4.82, 1.9), m["glass"], bevel=.01, c=c)
    put(sale_banner(c), x=-4.6, y=4.80, z=.13)
    put(price_tags(c), x=-4.6, y=4.55, z=.13)
    put(aframe(c), x=-3.0, y=2.4, z=.13, rot=rad(12))
    put(aframe(c), x=-6.2, y=2.9, z=.13, rot=rad(-10))
    for (px, py, who, r) in ((-3.6, 1.5, "Customer_08", 160), (-5.0, 1.7, "Customer_06", 195), (1.6, 1.8, "Customer_07", 150), (-1.2, 2.6, "Customer_09", 120)):
        E.actor(c, who, (px, py), rad(r))
    for (hx, hy, hz, s, who) in ((1.6, 1.8, 2.45, .9, 0), (-1.2, 2.6, 2.45, .8, 0)):
        objs = empty_wallet(c)
        for o in objs: o.matrix_world = Matrix.Translation((hx, hy, hz)) @ Matrix.Scale(s, 4) @ o.matrix_world

# ================================================================== 4. TURNO PUXADO
def sleepy_bubble(c):
    """'zZ' thought bubble, origin at the centre, reads from -Y."""
    p = P(c); m = mats()
    for (x, z, r) in ((0, 0, .26), (-.2, .05, .2), (.2, .04, .2), (-.1, .17, .17), (.1, .17, .17), (-.1, -.14, .16), (.1, -.14, .16), (.26, -.1, .12), (-.27, -.08, .13)):
        p.o.append(uvball(c, "cloud", r, (x, 0, z), m["cloudW"], scale=(1, .55, 1), seg=9, rings=6))
    p.o.append(uvball(c, "trail", .07, (-.3, 0, -.34), m["cloudW"], scale=(1, .6, 1), seg=8, rings=6))
    p.o.append(uvball(c, "trail", .04, (-.42, 0, -.46), m["cloudW"], scale=(1, .6, 1), seg=8, rings=6))
    p.txt("z", .22, (-.17, -.13, -.09), m["navy"], face="-Y", res=3, extrude=.015)
    p.txt("Z", .30, (.07, -.14, .02), m["navy"], face="-Y", res=3, extrude=.015)
    return p.o

def coffee_cups(c):
    """Cluster of empty disposable coffee cups (one knocked over), an energy-drink can, a crumpled napkin, stains."""
    p = P(c); m = mats()
    def cup(x, y, z=0.0, rot=(0, 0, 0), lid=True, tilt=False):
        objs = []
        objs.append(p.cyl("cup", .042, .12, (0, 0, .06), m["cupW"], r2=.03, verts=12))
        objs.append(p.cyl("sleeve", .041, .045, (0, 0, .062), m["cardboard"], r2=.035, verts=12))
        objs.append(p.cyl("cup_rim", .044, .008, (0, 0, .118), m["cupW"], verts=12))
        if lid:
            objs.append(p.cyl("lid", .046, .014, (0, 0, .127), m["dark"], verts=12))
            objs.append(p.cyl("lid_sip", .022, .006, (0, -.015, .137), m["dark"], verts=8))
        else:
            objs.append(p.cyl("dregs", .029, .004, (0, 0, .012), m["coffee"], verts=12))
        for o in objs:
            o.matrix_world = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot[0], 4, 'X') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[2], 4, 'Z') @ o.matrix_world
    cup(-.12, -.02, rot=(0, 0, rad(10)))
    cup(.02, .09, rot=(0, 0, rad(-30)), lid=False)
    cup(-.03, -.13, rot=(0, 0, rad(60)))
    cup(.22, -.06, z=.044, rot=(0, rad(90), rad(-20)), lid=False)   # knocked over
    p.cyl("stain", .05, .002, (.17, -.12, .001), m["coffee"], verts=10)
    p.cyl("stain", .035, .002, (-.2, .1, .001), m["coffee"], verts=10)
    # energy drink can
    cx, cy = .16, .12
    p.cyl("can", .028, .155, (cx, cy, .078), m["energy"], verts=14, bevel=.004)
    p.cyl("can_top", .026, .006, (cx, cy, .157), m["steelL"], verts=14)
    p.cyl("can_bottom", .026, .006, (cx, cy, .003), m["steelL"], verts=14)
    p.box("can_tab", (.012, .022, .002), (cx, cy - .006, .162), m["steelL"], bevel=0)
    p.cyl("can_hole", .009, .002, (cx, cy + .012, .160), m["dark"], verts=8)
    p.cyl("can_label", .0285, .06, (cx, cy, .085), m["lime"], verts=14)
    p.box("can_bolt", (.012, .006, .03), (cx, cy - .03, .09), m["yellow"], rot=(0, rad(20), 0), bevel=.001)
    # crumpled napkin + sugar sachets
    p.ball("napkin", .035, (-.22, -.12, .03), m["paper"], sub=1, scale=(1.2, 1, .8))
    p.box("sachet", (.05, .03, .004), (.05, -.2, .002), m["white"], rot=(0, 0, rad(30)), bevel=.002)
    p.box("sachet", (.05, .03, .004), (-.14, .16, .002), m["white"], rot=(0, 0, rad(-50)), bevel=.002)
    return p.o

def yawn_clock(c):
    """Wall clock showing 23:55, origin at the centre, face -Y."""
    p = P(c); m = mats(); R = .22
    p.cyl("rim", R, .05, (0, 0, 0), m["navy"], rot=(rad(90), 0, 0), verts=32, bevel=.012, seg=2)
    p.cyl("face", R - .025, .012, (0, -.022, 0), m["clockFace"], rot=(rad(90), 0, 0), verts=32)
    for i in range(12):
        a = rad(90 - i * 30); big = i % 3 == 0
        p.box("tick", (.018 if big else .01, .006, .035 if big else .02), (math.cos(a) * (R - .055), -.031, math.sin(a) * (R - .055)), m["navy"] if big else m["dark"], rot=(0, -a + rad(90), 0), bevel=0)
    p.box("hour_hand", (.016, .006, .11), (math.cos(rad(60 + 2)) * .045, -.034, math.sin(rad(62)) * .045 + .0), m["dark"], rot=(0, rad(-28), 0), bevel=.002)
    p.box("min_hand", (.012, .006, .17), (math.cos(rad(120)) * .07, -.038, math.sin(rad(120)) * .07), m["dark"], rot=(0, rad(30), 0), bevel=.002)
    p.box("sec_hand", (.005, .004, .17), (math.cos(rad(-30)) * .06, -.042, math.sin(rad(-30)) * .06), m["red"], rot=(0, rad(-120), 0), bevel=0)
    p.cyl("pin", .012, .012, (0, -.042, 0), m["red"], rot=(rad(90), 0, 0), verts=10)
    p.box("brand_plate", (.09, .004, .024), (0, -.03, -.09), m["navy"], bevel=0)
    p.txt("HORA", .03, (0, -.034, -.09), m["white"], face="-Y", res=1, extrude=.002)
    p.cyl("hanger", .012, .02, (0, .02, R + .01), m["dark"], rot=(rad(90), 0, 0), verts=8)
    return p.o

@E.event
def v2_TurnoPuxado(c):
    E.diorama(c); m = mats()
    k.checkout_counter("counter", (0, 1.2, .13), rot_z=rad(180), c=c, with_stool=False)
    for (x, y, s, r) in ((-.5, .95, 1.0, 20), (.55, 1.0, .9, -40)):
        objs = coffee_cups(c)
        for o in objs: o.matrix_world = Matrix.Translation((x, y, 1.13)) @ Matrix.Rotation(rad(r), 4, 'Z') @ Matrix.Scale(s, 4) @ o.matrix_world
    E.actor(c, "Customer_07", (0, 2.0), rad(180))       # the exhausted cashier
    E.actor(c, "Customer_09", (-1.4, 2.4), rad(200))
    for (x, y, z, s) in ((.55, 2.0, 2.35, .9), (-.9, 2.4, 2.3, .75)):
        objs = sleepy_bubble(c)
        for o in objs: o.matrix_world = Matrix.Translation((x, y, z)) @ Matrix.Scale(s, 4) @ o.matrix_world
    objs = yawn_clock(c)
    for o in objs: o.matrix_world = Matrix.Translation((1.2, 5.38, 2.3)) @ Matrix.Scale(2.0, 4) @ o.matrix_world

PROPS = {"Cafe_BreakTable": (break_table, 1024), "Cafe_FoldingChair": (folding_chair, 512), "Cafe_BackDoor": (back_door, 1024), "Cafe_CoffeeBoard": (coffee_board, 512),
         "Viral_RingLightTripod": (ring_light_tripod, 1024), "Viral_Backdrop": (backdrop, 1024), "Viral_Softbox": (softbox, 1024), "Viral_HeartPop": (heart_pop, 512),
         "FimMes_SaleBanner": (sale_banner, 1024), "FimMes_AFrame": (aframe, 1024), "FimMes_PriceTags": (price_tags, 1024), "FimMes_EmptyWallet": (empty_wallet, 512),
         "Turno_SleepyBubble": (sleepy_bubble, 512), "Turno_CoffeeCups": (coffee_cups, 512), "Turno_YawnClock": (yawn_clock, 512)}

def export(names=None):
    out = {}
    for n in (names or PROPS):
        fn, size = PROPS[n]
        c = E.prop_collection(n); mats(); fn(c)
        out[n] = E.export_prop(n, size=size)
        print("EXPORTED", n, out[n], flush=True)
    return out
