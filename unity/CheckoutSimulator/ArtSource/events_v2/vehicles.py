# vehicles.py - event vehicles v2 (Hora do rush, Caminhao de ofertas, Engarrafamento, Vigilancia sanitaria,
# Carro de som, Maquininha fora do ar, Excursao da escola).  Builders model at the origin, ground z=0,
# drive along +X, the camera side is -Y.  Each returns the objects it created (place them with put()).
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
if ART not in sys.path: sys.path.insert(0, ART)
import events_kit as E
import era_kit as k
import lot_kit as L
rad = math.radians
C = E.C

XM = {}
def mats():
    m = E.mats()
    if XM: return XM
    XM.update(m)
    XM["alu"] = k.stripes("EV_AluRib", (.88, .89, .91, 1), (.76, .77, .80, 1), .07, axis='X', rough=.4)
    XM["tyre"] = k.mat("EV_Tyre", (.10, .10, .11, 1), rough=.9, var=.06, scale=10, bump=.2)
    XM["tyreside"] = k.mat("EV_TyreSide", (.16, .16, .17, 1), rough=.85, var=.05, scale=10)
    XM["rim"] = k.mat("EV_Rim", (.78, .79, .80, 1), rough=.35, var=.05, scale=8, metallic=.6)
    XM["rimD"] = k.mat("EV_RimDark", (.30, .31, .33, 1), rough=.6, var=.05, scale=8)
    XM["glassD"] = k.mat("EV_GlassDark", (.18, .30, .40, 1), rough=.15, var=.05, scale=3)
    XM["purpleD"] = k.mat("EV_PurpleDark", (.33, .16, .50, 1), rough=.55, var=.07, scale=6)
    XM["yellowS"] = k.mat("EV_SchoolYellow", (.98, .72, .10, 1), rough=.5, var=.06, scale=6)
    XM["cardboard"] = k.mat("EV_Cardboard", (.72, .52, .30, 1), rough=.9, var=.10, scale=8)
    XM["tape"] = k.mat("EV_Tape", (.80, .62, .35, 1), rough=.5, var=.04, scale=8)
    XM["film"] = k.mat("EV_Film", (.80, .90, .95, 1), rough=.15, var=.08, scale=6, metallic=.1)
    XM["solar"] = k.stripes("EV_Solar", (.08, .12, .30, 1), (.14, .22, .48, 1), .08, axis='X', rough=.3)
    XM["greenD"] = k.mat("EV_GreenDark", (.05, .38, .18, 1), rough=.55, var=.06, scale=6)
    XM["ledOff"] = k.mat("EV_LedOff", (.10, .10, .11, 1), rough=.5, var=.03, scale=20, bump=.4)
    XM["rubberM"] = k.mat("EV_RubberMat", (.14, .14, .15, 1), rough=.95, var=.08, scale=20, bump=.4)
    return XM

ROT = {"-Y": (rad(90), 0, 0), "+Y": (rad(90), 0, rad(180)), "+X": (rad(90), 0, rad(90)), "-X": (rad(90), 0, rad(-90)), "UP": (0, 0, 0)}

class P:
    """Collects the objects of one prop."""
    def __init__(self, c): self.c = c; self.o = []
    def box(self, name, size, loc, m, bevel=.008, seg=1, **kw): o = k.box(name, size, loc, m, bevel=bevel, seg=seg, c=self.c, **kw); self.o.append(o); return o
    def cyl(self, name, r, h, loc, m, **kw): o = k.cyl(name, r, h, loc, m, c=self.c, **kw); self.o.append(o); return o
    def ball(self, name, r, loc, m, **kw): o = k.ball(name, r, loc, m, c=self.c, **kw); self.o.append(o); return o
    def tube(self, name, a, b, r, m, **kw): o = k.tube(name, a, b, r, m, c=self.c, **kw); self.o.append(o); return o
    def txt(self, s, size, loc, m, face="-Y", res=1, extrude=0.0, spacing=1.0):
        o = k.text("lbl", s, size, loc, m, rot=ROT[face], extrude=extrude, c=self.c, res=res, spacing=spacing); self.o.append(o); return o
    def cut(self, o, cutter):
        """Boolean-subtract `cutter` from `o` (applied at once; the cutter is deleted)."""
        md = o.modifiers.new("cut", 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_move_to_index(modifier=md.name, index=0)
        bpy.ops.object.modifier_apply(modifier=md.name)
        if cutter in self.o: self.o.remove(cutter)
        bpy.data.objects.remove(cutter, do_unlink=True)
        return o
    def arch(self, body, ax, y, R, z, w=.5):
        """Cut a wheel arch (cylinder along Y) into `body` at x=ax."""
        cutter = k.cyl("cutter", R, w, (ax, y, z), None, rot=(rad(90), 0, 0), verts=24, c=self.c)
        return self.cut(body, cutter)
    def prism(self, name, x0, x1, X0, X1, yb, z0, z1, m, yt=None, bevel=.08, seg=2):
        """Hexahedron: bottom x0..x1 (half-width yb) at z0, top X0..X1 (half-width yt) at z1; bevelled. Car cabins, hoods."""
        yt = yb if yt is None else yt
        bm = bmesh.new()
        vs = [bm.verts.new(v) for v in [(x0, -yb, z0), (x1, -yb, z0), (x1, yb, z0), (x0, yb, z0), (X0, -yt, z1), (X1, -yt, z1), (X1, yt, z1), (X0, yt, z1)]]
        for f in [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]:
            bm.faces.new([vs[i] for i in f])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); self.c.objects.link(o)
        k.finish(o, m, bevel, seg); self.o.append(o); return o
    def pane(self, name, a, b, width, m, out=1, t=.035, proud=.018, bevel=.012):
        """Glass pane lying on the slope from (xa, za) to (xb, zb) (in the XZ plane), standing `proud` off it."""
        (xa, za), (xb, zb) = a, b; dx, dz = xb - xa, zb - za; ln = math.hypot(dx, dz)
        n = Vector((dz, 0, -dx)).normalized() * out
        ctr = Vector(((xa + xb) / 2, 0, (za + zb) / 2)) + n * proud
        return self.box(name, (ln, width, t), ctr, m, rot=(0, -math.atan2(dz, dx), 0), bevel=bevel)
    def side_glass(self, name, x, w, zc, h, s, y_at, tilt, m, frame=True, proud=.012):
        """Side window strip on a (tumblehome-tilted) cabin side. y_at(z) gives the half width at height z."""
        yy = s * (y_at(zc) + proud)
        if frame: self.box(name + "_frame", (w + .08, .02, h + .06), (x, yy - s * .006, zc), mats()["ink"], rot=(s * tilt, 0, 0), bevel=.006)
        return self.box(name, (w, .025, h), (x, yy + s * .006, zc), m, rot=(s * tilt, 0, 0), bevel=.015)
    def wheel(self, loc, R=.34, w=.22, hub="rim", side=-1, nuts=5, verts=18):
        """Tyre (bevelled), sidewall rings, rim dish and hub both sides; lug nuts on the camera side. Axle along Y."""
        m = mats(); x, y, z = loc; rot = (rad(90), 0, 0)
        self.cyl("tyre", R, w, loc, m["tyre"], rot=rot, verts=verts, bevel=min(.05, R * .14), seg=1)
        for s in (-1, 1):
            yy = y + s * (w / 2 + .004)
            if s == side: self.cyl("sidewall", R * .80, .012, (x, yy, z), m["tyreside"], rot=rot, verts=verts)
            self.cyl("rim", R * .60, .03, (x, yy + s * .006, z), m[hub], rot=rot, verts=14)
            self.cyl("rimdish", R * .44, .025, (x, yy + s * .012, z), m["rimD"], rot=rot, verts=10)
            self.cyl("hub", R * .14, .05, (x, yy + s * .02, z), m["grey"], rot=rot, verts=6)
        if nuts:
            yy = y + side * (w / 2 + .03)
            for i in range(nuts):
                a = i * math.tau / nuts
                self.cyl("nut", R * .035, .02, (x + math.cos(a) * R * .27, yy, z + math.sin(a) * R * .27), m["dark"], rot=rot, verts=4)
    def mirror(self, loc, sx, arm=.3, h=.26, w=.16, m=None, up=0.0):
        """Door mirror: arm out along -/+Y from loc, housing at the end."""
        mm = mats(); x, y, z = loc; m = m or mm["dark"]
        self.box("mirror_arm", (.04, arm, .04), (x, y + sx * arm / 2, z + up), m, bevel=.005)
        self.box("mirror", (.06, w, h), (x, y + sx * (arm + w / 2 - .02), z), m, bevel=.015)
        self.box("mirror_glass", (.012, w - .04, h - .04), (x + .03, y + sx * (arm + w / 2 - .02), z), mm["glassL"], bevel=0)
    def handle(self, loc, face=-1):
        x, y, z = loc
        self.box("handle", (.16, .025, .04), (x, y + face * .012, z), mats()["chrome"], bevel=.006)
    def seam(self, x, y, z0, z1, face=-1, m=None):
        return self.box("seam", (.022, .012, z1 - z0), (x, y + face * .004, (z0 + z1) / 2), m or mats()["ink"], bevel=0)
    def plate(self, x, y, z, face="+X", s="ABC 1D23"):
        m = mats(); rot = ROT[face]
        if face in ("+X", "-X"):
            d = 1 if face == "+X" else -1
            self.box("plate", (.02, .40, .13), (x + d * .01, y, z), m["paper"], bevel=.004)
            self.txt(s, .065, (x + d * .022, y, z - .005), m["ink"], face=face, res=1, extrude=.003)
        else:
            d = -1 if face == "-Y" else 1
            self.box("plate", (.40, .02, .13), (x, y + d * .01, z), m["paper"], bevel=.004)
            self.txt(s, .065, (x, y + d * .022, z - .005), m["ink"], face=face, res=1, extrude=.003)
    def lamp(self, name, size, loc, m, lens=True, bezel=None):
        """Light with a dark bezel and a lens standing proud (boxes; `size` is (x, y, z))."""
        mm = mats(); x, y, z = loc; sx, sy, sz = size
        self.box(name + "_bezel", (sx * 1.15 + .02, sy * 1.15 + .02, sz * 1.15 + .02), loc, bezel or mm["ink"], bevel=.006)
        self.box(name, size, loc, m, bevel=min(sx, sy, sz) * .3, seg=2)

def put(objs, x=0, y=0, z=0, rot=0.0):
    Mw = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, 'Z')
    for o in objs: o.matrix_world = Mw @ o.matrix_world
    return objs

# ================================================================== 1. HORA DO RUSH
def city_bus(c, body="white", stripe="teal", accent="yellow", sign="123 CENTRO", num="123"):
    """Brazilian low-floor city bus: 11 x 2.5 x 3.05 m, doors on +Y (sidewalk), livery on -Y (camera)."""
    p = P(c); m = mats(); Lb, Wb, H, z0 = 11.0, 2.5, 3.05, .34
    fx, bx = Lb / 2, -Lb / 2; hw = Wb / 2
    axles = (fx - 2.5, bx + 2.8); R = .5
    body_o = p.box("bus_body", (Lb, Wb, H - z0), (0, 0, z0 + (H - z0) / 2), m[body], bevel=.20, seg=3)
    skirt = p.box("bus_skirt", (Lb - .08, Wb + .02, .62), (0, 0, z0 + .31), m[stripe], bevel=.06, seg=1)
    for s in (-1, 1):
        for ax in axles:
            for o in (body_o, skirt):
                p.arch(o, ax, s * hw, R + .12, R + .02, w=.7)
    for s in (-1, 1):
        for ax in axles:
            p.cyl("archliner", R + .1, .12, (ax, s * (hw - .42), R + .02), m["ink"], rot=(rad(90), 0, 0), verts=16)
            p.wheel((ax, s * (hw - .20), R + .02), R=R, w=.32, side=s)
        p.box("underbody", (Lb - 1.2, .1, .22), (0, s * (hw - .18), .22), m["ink"], bevel=.01)
    p.box("chassis", (Lb - .6, Wb - .9, .34), (0, 0, .2), m["ink"], bevel=.02)
    # livery, camera side (-Y): wide stripe swoosh, thin accent line, route number, operator text
    y = -hw - .012
    p.box("stripe_main", (Lb - .9, .02, .32), (-.2, y, 1.42), m[stripe], bevel=.006)
    p.box("stripe_swoosh", (3.2, .02, .32), (fx - 2.3, y, 1.58), m[stripe], rot=(0, 0, 0), bevel=.006).rotation_euler.y = rad(-6)
    p.box("stripe_thin", (Lb - .6, .02, .07), (-.1, y, 1.12), m[accent], bevel=.004)
    p.txt("TRANSPORTE URBANO", .21, (-1.0, y - .012, 1.42), m["white"], face="-Y", spacing=1.05)
    p.txt(num, .34, (fx - 1.3, y - .014, .66), m["white"], face="-Y")
    p.txt("LINHA 123 - CENTRO", .11, (bx + 1.9, y - .014, .66), m["white"], face="-Y")
    # window band both sides: dark frame + panes
    for s in (-1, 1):
        yy = s * (hw + .006)
        p.box("win_frame", (Lb - 1.3, .025, 1.22), (-.35, yy, 2.2), m["ink"], bevel=.01)
        n = 7; w0 = (Lb - 1.3) / n
        for i in range(n):
            px = -.35 - (Lb - 1.3) / 2 + w0 * (i + .5)
            if s == 1 and (abs(px - (fx - 1.3)) < .9 or abs(px - .1) < .9): continue   # door openings on +Y
            p.box("win_glass", (w0 - .12, .03, 1.08), (px, yy + s * .012, 2.2), m["glass"], bevel=.02)
            p.box("win_slider", (w0 - .12, .012, .02), (px, yy + s * .03, 2.42), m["ink"], bevel=0)
            p.box("win_slider_v", (.02, .012, .62), (px + w0 * .22, yy + s * .03, 2.73), m["ink"], bevel=0)
    # doors on +Y: double leaves with frames, tread lights
    for dx in (fx - 1.3, .1):
        p.box("door_frame", (1.5, .04, 2.5), (dx, hw + .014, 1.6), m["ink"], bevel=.015)
        for lx in (-.36, .36):
            p.box("door_leaf", (.62, .03, 2.3), (dx + lx, hw + .035, 1.6), m[body], bevel=.01)
            p.box("door_glass", (.5, .02, 1.3), (dx + lx, hw + .052, 2.05), m["glass"], bevel=.015)
            p.box("door_glass_low", (.5, .02, .55), (dx + lx, hw + .052, .95), m["glassD"], bevel=.015)
        p.box("door_lamp", (.4, .04, .08), (dx, hw + .04, 2.92), m["amber"], bevel=.01)
    # front (+X): destination LED, windscreen, lamps, grille, bumper, wipers, mirrors
    p.box("dest_box", (.08, Wb - .5, .40), (fx + .02, 0, 2.72), m["ink"], bevel=.02)
    p.box("dest_led", (.04, Wb - .7, .28), (fx + .06, 0, 2.72), m["ledOff"], bevel=.005)
    p.txt(sign, .19, (fx + .085, 0, 2.70), m["amber"], face="+X", res=2, extrude=.004)
    p.box("windshield", (.06, Wb - .3, 1.25), (fx + .01, 0, 1.78), m["glass"], bevel=.04)
    p.box("ws_bar", (.07, Wb - .3, .05), (fx + .02, 0, 2.42), m["ink"], bevel=0)
    for s in (-1, 1):
        p.box("wiper", (.03, .75, .03), (fx + .05, s * .55, 1.3), m["ink"], rot=(rad(-30 * s), 0, 0), bevel=0)
        p.box("wiper_blade", (.02, .55, .02), (fx + .055, s * .55 + s * .15, 1.3 + .3), m["ink"], rot=(rad(-30 * s), 0, 0), bevel=0)
        p.lamp("headlamp", (.05, .46, .26), (fx + .02, s * .80, .98), m["lamp"])
        p.cyl("foglamp", .07, .04, (fx + .02, s * 1.0, .62), m["lamp"], rot=(0, rad(90), 0), verts=12)
        p.box("indicator", (.04, .14, .08), (fx + .025, s * .52, .98), m["amber"], bevel=.01)
        p.box("mirror_post", (.05, .05, .9), (fx + .22, s * (hw + .12), 1.95), m["ink"], bevel=0)
        p.box("mirror_arm", (.42, .05, .05), (fx + .02, s * (hw + .12), 2.38), m["ink"], bevel=0)
        p.box("mirror_h", (.08, .22, .48), (fx + .24, s * (hw + .28), 2.0), m["ink"], bevel=.03)
        p.box("mirror_g", (.012, .18, .42), (fx + .285, s * (hw + .28), 2.0), m["glassL"], bevel=0)
    p.box("grille", (.05, 1.1, .22), (fx + .015, 0, .78), m["ink"], bevel=.02)
    for i in range(3):
        p.box("grille_bar", (.02, 1.0, .03), (fx + .045, 0, .70 + i * .07), m["grey"], bevel=0)
    p.box("bumper_f", (.18, Wb + .02, .32), (fx + .04, 0, .44), m["ink"], bevel=.06, seg=3)
    p.box("bumper_f_lip", (.12, Wb - .4, .1), (fx + .12, 0, .32), m[stripe], bevel=.02)
    p.plate(fx + .13, 0, .50, "+X", "BUS 2A26")
    p.txt("CHECKOUT", .08, (fx + .05, 0, 2.95 - .02), m[stripe], face="+X", res=1)
    # rear (-X): engine louvres, window, tail lights, bumper, plate
    p.box("engine_hatch", (.03, 1.7, .9), (bx - .005, 0, 1.0), m[body], bevel=.01)
    for i in range(5):
        p.box("louvre", (.03, 1.5, .05), (bx - .02, 0, .65 + i * .16), m["ink"], bevel=0)
    p.box("rear_glass", (.05, Wb - .5, .85), (bx - .005, 0, 2.35), m["glass"], bevel=.04)
    p.box("rear_sign", (.06, 1.0, .28), (bx - .01, 0, 2.86), m["ink"], bevel=.01)
    p.txt(num, .17, (bx - .045, 0, 2.85), m["amber"], face="-X", res=1)
    for s in (-1, 1):
        for i, col in enumerate(("tail", "amber", "white")):
            p.box("taillamp", (.05, .16, .16), (bx - .015, s * 1.02, 1.52 - i * .19), m[col], bevel=.02)
        p.box("tail_bezel", (.03, .2, .62), (bx - .005, s * 1.02, 1.33), m["ink"], bevel=.01)
    p.box("bumper_r", (.18, Wb + .02, .32), (bx - .04, 0, .44), m["ink"], bevel=.06, seg=3)
    p.plate(bx - .13, 0, .50, "-X", "BUS 2A26")
    # roof: AC unit, hatches, antenna
    p.box("roof_ac", (2.4, 1.6, .28), (bx + 3.0, 0, H + .1), m[body], bevel=.08, seg=3)
    for i in range(4):
        p.box("ac_vent", (.35, 1.3, .03), (bx + 2.2 + i * .5, 0, H + .25), m["grey"], bevel=.005)
    for hx in (fx - 2.6, .9):
        p.box("roof_hatch", (.8, .8, .07), (hx, 0, H + .02), m["grey"], bevel=.02)
        p.box("roof_hatch_lid", (.7, .7, .03), (hx, 0, H + .07), m[body], bevel=.01)
    p.cyl("antenna", .012, .4, (fx - .6, -.6, H + .18), m["ink"], verts=6)
    p.box("roof_strip", (Lb - 1.6, .06, .03), (0, 0, H + .005), m["grey"], bevel=0)
    return p.o

def bus_shelter(c, w=4.0, d=1.5):
    """Glass bus shelter facing -Y, with a bench, a lit ad panel on the right, the stop sign on the left."""
    p = P(c); m = mats()
    for sx in (-1, 1):
        for yy in (-d / 2 + .1, d / 2 - .05):
            p.box("post", (.09, .09, 2.5), (sx * (w / 2 - .08), yy, 1.25), m["steel"], bevel=.012, seg=2)
            p.box("post_foot", (.2, .2, .03), (sx * (w / 2 - .08), yy, .015), m["dark"], bevel=.006)
    p.box("roof", (w + .36, d + .3, .12), (0, 0, 2.62), m["teal"], bevel=.05, seg=3)
    p.box("roof_cap", (w + .40, d + .34, .04), (0, 0, 2.70), m["tealL"], bevel=.015)
    p.box("roof_gutter", (w + .38, .06, .22), (0, -d / 2 - .14, 2.54), m[ "yellow"], bevel=.015)
    p.txt("PONTO DE ÔNIBUS", .14, (0, -d / 2 - .175, 2.54), m["navy"], face="-Y", res=2)
    p.box("glass_back", (w - .4, .025, 1.95), (0, d / 2 - .05, 1.22), m["glassL"], bevel=.006)
    p.box("glass_back_band", (w - .4, .03, .12), (0, d / 2 - .05, 1.0), m["teal"], bevel=.004)
    p.box("glass_left", (.025, d - .2, 1.95), (-w / 2 + .08, 0, 1.22), m["glassL"], bevel=.006)
    for sx in (-1, 1):
        p.box("glass_rail_top", (w - .3, .05, .05), (0, d / 2 - .05, 2.22), m["steel"], bevel=.006)
    # lit advertising panel (right side)
    ax = w / 2 - .08
    p.box("ad_frame", (.14, 1.2, 1.9), (ax, 0, 1.25), m["steel"], bevel=.02)
    p.box("ad_light", (.03, 1.04, 1.7), (ax - .075, 0, 1.28), m["screen"], bevel=0)
    p.box("ad_light_o", (.03, 1.04, 1.7), (ax + .075, 0, 1.28), m["screen"], bevel=0)
    p.txt("CHECKOUT", .13, (ax - .095, 0, 1.75), m["navy"], face="+X" if False else "-X", res=1)
    p.txt("OFERTAS", .17, (ax - .095, 0, 1.35), m["red"], face="-X", res=1)
    p.txt("TODO DIA", .11, (ax - .095, 0, 1.0), m["navy"], face="-X", res=1)
    # bench with slats
    bx, by = -.5, d / 2 - .45
    for i in range(4):
        p.box("bench_slat", (2.4, .085, .035), (bx, by - .17 + i * .11, .47), m["wood"], bevel=.006)
    for lx in (-1.0, 1.0):
        p.box("bench_leg", (.05, .36, .44), (bx + lx, by, .22), m["dark"], bevel=.006)
        p.box("bench_leg_f", (.05, .4, .03), (bx + lx, by, .015), m["dark"], bevel=.004)
    p.box("bench_rail", (2.4, .04, .04), (bx, by + .18, .50), m["dark"], bevel=.004)
    # waste bin
    p.cyl("bin", .16, .62, (w / 2 - .7, -.35, .31), m["green"], verts=14, bevel=.01)
    p.cyl("bin_ring", .17, .04, (w / 2 - .7, -.35, .6), m["dark"], verts=14)
    # stop pole, sign, timetable
    sx_ = -w / 2 - .55
    p.cyl("stop_pole", .04, 3.0, (sx_, -d / 2 + .1, 1.5), m["steel"], verts=10)
    p.cyl("stop_foot", .1, .05, (sx_, -d / 2 + .1, .025), m["dark"], verts=12)
    p.cyl("stop_plate", .34, .035, (sx_, -d / 2 + .05, 2.72), m["blue"], rot=(rad(90), 0, 0), verts=28)
    p.cyl("stop_ring", .36, .02, (sx_, -d / 2 + .06, 2.72), m["white"], rot=(rad(90), 0, 0), verts=28)
    p.txt("ÔNIBUS", .11, (sx_, -d / 2 + .03, 2.80), m["white"], face="-Y", res=1)
    p.txt("123", .14, (sx_, -d / 2 + .03, 2.62), m["yellow"], face="-Y", res=1)
    p.box("timetable", (.46, .04, .62), (sx_, -d / 2 + .06, 1.95), m["steel"], bevel=.008)
    p.box("timetable_paper", (.40, .01, .56), (sx_, -d / 2 + .035, 1.95), m["paper"], bevel=0)
    for i in range(5):
        p.box("tt_line", (.3, .006, .018), (sx_, -d / 2 + .028, 2.14 - i * .09), m["navy"] if i else m["red"], bevel=0)
    return p.o

@E.event
def v2_HoraDoRush(c):
    E.diorama(c)
    put(bus_shelter(c), x=-4.4, y=-.3, z=.13)
    put(city_bus(c), x=.6, y=-2.75)
    for (px, py, who, r) in [(-4.4, -.3, "Customer_06", 200), (-3.4, .1, "Customer_08", 170), (.2, -.9, "Customer_07", 20),
                             (1.2, -.3, "Customer_09", 40), (2.4, .6, "Customer_06", 60), (3.5, 1.6, "Customer_07", 80), (-1.6, -.4, "Customer_09", 150)]:
        E.actor(c, who, (px, py), rad(r))

# ================================================================== 2. CAMINHAO DE OFERTAS
def box_truck(c, paint="orange", stripe="red"):
    """Cab-over supplier truck 7.6 x 2.4 x 3.5 m: aluminium ribbed box, roll-up rear door, banner on -Y."""
    p = P(c); m = mats(); Lt, Wt = 7.6, 2.4; hw = Wt / 2; fx, bx = Lt / 2, -Lt / 2
    cabL = 2.1; cx = fx - cabL / 2; R = .46
    # chassis + cab
    p.box("chassis", (Lt - .4, 1.0, .22), (-.1, 0, .62), m["ink"], bevel=.02)
    p.box("chassis_rail_l", (Lt - 1.0, .08, .18), (-.3, -.5, .62), m["dark"], bevel=.01)
    cab = p.box("cab", (cabL, Wt, 1.75), (cx, 0, 1.48), m[paint], bevel=.14, seg=3)
    p.arch(cab, fx - 1.0, -hw, R + .1, R + .02, w=.6); p.arch(cab, fx - 1.0, hw, R + .1, R + .02, w=.6)
    p.box("cab_roof", (cabL - .2, Wt - .2, .12), (cx, 0, 2.38), m[paint], bevel=.04)
    p.prism("deflector", cx - .9, cx + .45, cx - .9, cx - .72, hw - .25, 2.44, 2.98, m[paint], yt=hw - .32, bevel=.04, seg=2)
    p.box("windshield", (.06, Wt - .36, .82), (fx + .005, 0, 1.78), m["glass"], rot=(0, rad(-6), 0), bevel=.03)
    p.box("visor", (.3, Wt - .1, .07), (fx + .06, 0, 2.28), m["dark"], bevel=.015)
    for s in (-1, 1):
        p.box("cab_sideglass", (.72, .03, .62), (cx - .25, s * (hw + .003), 1.82), m["glass"], bevel=.03)
        p.seam(cx + .22, s * hw, .75, 2.2, face=s); p.seam(cx - .66, s * hw, .75, 2.2, face=s)
        p.handle((cx - .1, s * hw, 1.4), face=s)
        p.box("step", (.5, .3, .05), (cx, s * (hw - .05), .55), m["steel"], bevel=.01)
        p.box("step2", (.5, .3, .05), (cx, s * (hw - .05), .9), m["steel"], bevel=.01)
        p.box("step_bracket", (.05, .25, .5), (cx + .2, s * (hw - .08), .72), m["dark"], bevel=0)
        p.mirror((fx - .35, s * hw, 1.95), s, arm=.25, h=.44, w=.2)
        p.lamp("headlamp", (.05, .36, .18), (fx + .02, s * .74, .95), m["lamp"])
        p.box("indicator", (.04, .12, .08), (fx + .025, s * .46, .95), m["amber"], bevel=.01)
        p.wheel((fx - 1.0, s * (hw - .16), R + .02), R=R, w=.28, side=s)
        p.box("sun_strip", (.3, .3, .03), (cx + .35, s * (hw - .35), 2.455), m["dark"], bevel=.004)
    p.box("grille", (.05, 1.3, .35), (fx + .015, 0, 1.22), m["ink"], bevel=.02)
    for i in range(4):
        p.box("grille_bar", (.02, 1.2, .035), (fx + .045, 0, 1.08 + i * .09), m["grey"], bevel=0)
    p.box("bumper_f", (.2, Wt + .04, .3), (fx + .04, 0, .5), m["dark"], bevel=.05, seg=3)
    p.plate(fx + .14, 0, .5, "+X", "OFE 2B25")
    p.cyl("beacon", .07, .1, (cx - .5, -.6, 2.46), m["amber"], verts=10)
    # fuel tank, exhaust, battery box
    p.cyl("fuel_tank", .3, 1.0, (bx + 2.6, -(hw - .3), .62), m["chrome"], rot=(0, rad(90), 0), verts=16, bevel=.03)
    for dx in (-.35, .35):
        p.box("tank_strap", (.05, .64, .64), (bx + 2.6 + dx, -(hw - .3), .62), m["dark"], bevel=.01)
    p.box("battery_box", (.7, .35, .4), (bx + 3.6, -(hw - .25), .62), m["dark"], bevel=.03)
    p.cyl("exhaust", .05, 1.0, (bx + 1.4, -(hw - .2), .4), m["grey"], rot=(0, rad(90), 0), verts=8)
    # cargo box: aluminium ribbed sides, white roof, corner posts, rubbing rails
    bl = Lt - cabL - .25; bcx = bx + bl / 2
    p.box("cargo", (bl, Wt + .08, 2.5), (bcx, 0, 2.05), m["alu"], bevel=.02, seg=1)
    p.box("cargo_roof", (bl + .04, Wt + .12, .06), (bcx, 0, 3.31), m["white"], bevel=.015)
    p.box("cargo_floor", (bl + .04, Wt + .12, .08), (bcx, 0, .82), m["dark"], bevel=.015)
    for s in (-1, 1):
        for xx in (bx + .05, bx + bl - .05):
            p.box("cargo_post", (.1, .06, 2.5), (xx, s * (hw + .06), 2.05), m["steel"], bevel=.008)
        p.box("rub_rail", (bl - .2, .04, .1), (bcx, s * (hw + .07), 1.05), m[stripe], bevel=.005)
        p.box("top_rail", (bl - .2, .04, .12), (bcx, s * (hw + .07), 3.18), m[stripe], bevel=.005)
        p.box("marker", (.12, .03, .05), (bx + .3, s * (hw + .08), 3.1), m["amber"], bevel=.006)
    # banner on the camera side
    p.box("banner", (bl - .6, .03, 1.1), (bcx, -(hw + .08), 2.0), m["yellow"], bevel=.01)
    p.box("banner_border", (bl - .5, .02, 1.2), (bcx, -(hw + .07), 2.0), m["red"], bevel=.01)
    p.txt("OFERTA", .48, (bcx - .55, -(hw + .105), 2.22), m["red"], face="-Y", res=2)
    p.txt("-25%", .50, (bcx + 1.5, -(hw + .105), 2.22), m["navy"], face="-Y", res=2)
    p.txt("DIRETO DO FORNECEDOR", .16, (bcx, -(hw + .105), 1.68), m["navy"], face="-Y", res=2)
    # roll-up rear door
    p.box("roll_door", (.04, Wt - .3, 2.25), (bx - .02, 0, 1.98), m["steel"], bevel=.01)
    for i in range(8):
        p.box("roll_slat", (.02, Wt - .34, .015), (bx - .045, 0, .98 + i * .27), m["dark"], bevel=0)
    p.box("roll_bar", (.05, Wt - .2, .08), (bx - .04, 0, 1.1), m["dark"], bevel=.01)
    p.box("roll_latch", (.06, .14, .22), (bx - .05, .3, 1.0), m["dark"], bevel=.01)
    p.box("roll_drum", (.3, Wt - .2, .3), (bx + .1, 0, 3.0), m["dark"], bevel=.08, seg=3)
    for s in (-1, 1):
        p.box("rear_lamp", (.05, .12, .4), (bx - .03, s * (hw - .25), .78), m["tail"], bevel=.015)
        p.box("rear_lamp_bezel", (.03, .16, .46), (bx - .015, s * (hw - .25), .78), m["ink"], bevel=.006)
        p.box("mudguard", (.95, .32, .06), (bx + 1.5, s * (hw - .2), R * 2 + .1), m["ink"], bevel=.01)
        p.box("mudflap", (.06, .3, .4), (bx + 1.5 - .5, s * (hw - .2), .3), m["rubber"], bevel=.005)
        p.wheel((bx + 1.5, s * (hw - .16), R + .02), R=R, w=.28, side=s)
        p.wheel((bx + 1.5, s * (hw - .46), R + .02), R=R, w=.28, side=s, nuts=0)
    p.box("underride", (.08, Wt - .4, .14), (bx - .02, 0, .48), m["hazard"], bevel=.01)
    p.plate(bx - .07, 0, .5 + .1, "-X", "OFE 2B25")
    return p.o

def pallet_stack(c):
    """Euro pallet with 2x2x2 cartons held by three bands of stretch film."""
    p = P(c); m = mats(); w, d = 1.2, 1.0
    for i in range(3):
        p.box("stringer", (w, .1, .09), (0, -d / 2 + .05 + i * (d / 2 - .05), .07), m["wood"], bevel=.006)
    for i in range(3):
        p.box("bottom_board", (w, .1, .022), (0, -d / 2 + .05 + i * (d / 2 - .05), .011), m["wood"], bevel=.004)
    for i in range(3):
        p.box("block", (.14, .1, .07), (-w / 2 + .07 + i * (w / 2 - .07), 0, .09), m["wood"], bevel=.004)
    for i in range(5):
        p.box("top_board", (.14, d, .022), (-w / 2 + .07 + i * (w / 2 - .07) / 2, 0, .133), m["wood"], bevel=.004)
    z = .144; cw, cd, ch = .56, .46, .40
    for lvl in range(2):
        for i in range(2):
            for j in range(2):
                col = m["cardboard"] if (i + j + lvl) % 2 else m["gold"]
                cx, cy = -cw / 2 - .02 + i * (cw + .04), -cd / 2 - .02 + j * (cd + .04)
                p.box("carton", (cw, cd, ch), (cx, cy, z + ch / 2 + lvl * (ch + .01)), col, bevel=.012)
                p.box("carton_tape", (.05, cd + .004, ch + .004), (cx, cy, z + ch / 2 + lvl * (ch + .01)), m["tape"], bevel=0)
                if j == 0: p.txt("FRÁGIL", .06, (cx, cy - cd / 2 - .004, z + ch * .4 + lvl * (ch + .01)), m["red"], face="-Y")
    for i, zz in enumerate((.28, .62)):
        p.box("film", (cw * 2 + .06 + .02, cd * 2 + .06 + .02, .07), (0, 0, z + zz), m["film"], bevel=.02, seg=1)
    p.box("film_top", (cw * 2 + .05, cd * 2 + .05, .02), (0, 0, z + 2 * ch + .02), m["film"], bevel=.004)
    return p.o

def pallet_jack(c):
    """Hand pallet jack, forks pointing +X, tiller folded up."""
    p = P(c); m = mats()
    for s in (-1, 1):
        p.box("fork", (1.15, .16, .055), (.55, s * .27, .1), m["red"], bevel=.01)
        p.box("fork_tip", (.14, .14, .05), (1.1, s * .27, .095), m["red"], bevel=.02)
        p.cyl("fork_wheel", .04, .07, (1.02, s * .27, .04), m["rubber"], rot=(rad(90), 0, 0), verts=12)
    p.box("fork_bridge", (.3, .68, .1), (.05, 0, .13), m["red"], bevel=.015)
    p.box("pump_body", (.26, .4, .34), (-.1, 0, .32), m["red"], bevel=.03, seg=2)
    p.cyl("pump_cyl", .07, .5, (-.1, 0, .5), m["dark"], verts=12)
    for s in (-1, 1):
        p.cyl("steer_wheel", .09, .06, (-.08, s * .17, .09), m["rubber"], rot=(rad(90), 0, 0), verts=14)
        p.cyl("steer_hub", .04, .07, (-.08, s * .17, .09), m["grey"], rot=(rad(90), 0, 0), verts=8)
    p.box("tiller", (.05, .06, .85), (-.22, 0, 1.05), m["dark"], rot=(0, rad(12), 0), bevel=.006)
    p.cyl("tiller_pivot", .05, .14, (-.14, 0, .68), m["dark"], rot=(rad(90), 0, 0), verts=10)
    p.box("grip", (.06, .42, .06), (-.3, 0, 1.46), m["rubber"], bevel=.02)
    p.box("grip_lever", (.03, .2, .04), (-.27, 0, 1.4), m["chrome"], bevel=.006)
    return p.o

@E.event
def v2_CaminhaoDeOfertas(c):
    E.diorama(c)
    put(box_truck(c), x=.2, y=-2.95)
    put(pallet_stack(c), x=5.0, y=.2, z=.13, rot=rad(8))
    put(pallet_stack(c), x=5.3, y=1.8, z=.13, rot=rad(-6))
    put(pallet_jack(c), x=3.3, y=1.0, z=.13, rot=rad(-20))
    E.actor(c, "Customer_09", (4.1, -.4), rad(-40)); E.actor(c, "Customer_06", (2.4, 2.2), rad(150)); E.actor(c, "Customer_07", (-1.5, 1.4), rad(60))

# ================================================================== 3. ENGARRAFAMENTO
def hatchback(c, paint="red"):
    """Compact hatchback 3.95 x 1.72 x 1.48 m: bevelled lower body, tapered cabin with sloped windscreen / hatch."""
    p = P(c); m = mats(); Lc, Wc = 3.95, 1.72; hw = Wc / 2; fx, bx = Lc / 2, -Lc / 2; R = .30
    body = p.box("body", (Lc, Wc, .60), (0, 0, .33 + .30), m[paint], bevel=.11, seg=3)
    p.box("sill", (Lc - .7, Wc - .08, .14), (0, 0, .33), m["ink"], bevel=.03, seg=1)
    # bonnet wedge + cabin prism (tumblehome: narrower at the roof)
    p.prism("bonnet", fx - 1.25, fx - .05, fx - 1.25, fx - .35, hw - .06, .90, 1.0, m[paint], yt=hw - .1, bevel=.05)
    z0, z1 = .92, 1.48; yb, yt = hw - .05, hw - .16
    p.prism("cabin", -1.55, 1.05, -1.2, -.05, yb, z0, z1, m[paint], yt=yt, bevel=.09, seg=3)
    y_at = lambda z: yb + (yt - yb) * (z - z0) / (z1 - z0); tilt = math.atan2(yb - yt, z1 - z0)
    p.pane("windshield", (1.0, z0 + .02), (-.1, z1 - .02), 2 * yt - .1, m["glass"])
    p.pane("rear_glass", (-1.2, z1 - .02), (-1.5, z0 + .02), 2 * yt - .1, m["glass"])
    for s in (-1, 1):
        for ax in (fx - .72, bx + .72):
            p.arch(body, ax, s * hw, R + .09, R + .02, w=.5)
            p.cyl("archliner", R + .08, .1, (ax, s * (hw - .42), R + .02), m["ink"], rot=(rad(90), 0, 0), verts=16)
            p.wheel((ax, s * (hw - .14), R + .02), R=R, w=.2, side=s, verts=18)
        zc = (z0 + z1) / 2 + .02
        p.side_glass("win_front", .3, .78, zc, .40, s, y_at, tilt, m["glass"])
        p.side_glass("win_rear", -.52, .62, zc, .40, s, y_at, tilt, m["glass"])
        p.side_glass("win_q", -1.08, .3, zc - .02, .32, s, y_at, tilt, m["glass"])
        p.seam(-.12, s * hw, .36, .92, face=s); p.seam(-.9, s * hw, .36, .92, face=s); p.seam(fx - 1.2, s * hw, .36, .92, face=s)
        p.handle((.05, s * hw, .80), face=s); p.handle((-.75, s * hw, .80), face=s)
        p.mirror((.72, s * (y_at(1.05) - .02), 1.06), s, arm=.1, h=.14, w=.16, m=m[paint])
        p.lamp("headlamp", (.05, .36, .18), (fx + .01, s * .55, .74), m["lamp"])
        p.box("foglamp", (.04, .12, .07), (fx + .07, s * .55, .40), m["lamp"], bevel=.01)
        p.lamp("taillamp", (.05, .22, .26), (bx - .01, s * .62, .86), m["tail"])
        p.box("wiper", (.02, .5, .025), (.9, s * .3, .98), m["ink"], rot=(0, rad(-30), rad(-25 * s)), bevel=0)
    p.box("grille", (.04, .8, .14), (fx + .01, 0, .74), m["ink"], bevel=.015)
    p.box("grille_low", (.04, 1.0, .18), (fx + .02, 0, .44), m["ink"], bevel=.015)
    p.box("bumper_f", (.16, Wc + .02, .26), (fx + .02, 0, .48), m[paint], bevel=.07, seg=2)
    p.box("bumper_f_lip", (.1, Wc - .3, .08), (fx + .06, 0, .33), m["ink"], bevel=.02)
    p.box("bumper_r", (.16, Wc + .02, .26), (bx - .02, 0, .48), m[paint], bevel=.07, seg=2)
    p.box("bumper_r_lip", (.1, Wc - .3, .08), (bx - .06, 0, .33), m["ink"], bevel=.02)
    p.box("hatch_line", (.02, Wc - .5, .015), (bx + .02, 0, .74), m["ink"], bevel=0)
    p.plate(fx + .1, 0, .60, "+X", "CAR 1A23"); p.plate(bx - .1, 0, .68, "-X", "CAR 1A23")
    for s in (-1, 1): p.box("roof_rail", (1.0, .05, .03), (-.6, s * (yt - .1), z1 + .01), m["ink"], bevel=.006)
    p.cyl("antenna", .008, .18, (-1.0, 0, z1 + .08), m["ink"], verts=6)
    p.box("exhaust", (.2, .05, .05), (bx + .05, -.5, .26), m["chrome"], bevel=.01)
    return p.o


def message_board(c):
    """Portable LED message trailer (board faces -Y): LENTIDAO +15 MIN, solar panel, drawbar towards +X."""
    p = P(c); m = mats()
    p.box("trailer", (1.5, 1.1, .32), (0, 0, .52), m["orange"], bevel=.04, seg=2)
    for s in (-1, 1):
        p.box("trailer_hz", (1.52, .03, .18), (0, s * .56, .50), m["hazard"], bevel=.005)
        p.wheel((0, s * .68, .3), R=.3, w=.16, side=s, verts=16)
        p.box("mudguard", (.75, .2, .05), (0, s * .68, .64), m["dark"], bevel=.01)
        p.box("outrigger", (.08, .08, .5), (-.6, s * .62, .27), m["dark"], bevel=.005)
        p.box("outrigger_foot", (.18, .18, .03), (-.6, s * .62, .015), m["dark"], bevel=.004)
        p.cyl("beacon", .07, .1, (s * .95, 0, 3.72), m["amber"], verts=10)
    p.box("battery_lid", (.9, .7, .04), (-.1, 0, .70), m["dark"], bevel=.01)
    p.box("axle", (.08, 1.3, .08), (0, 0, .3), m["dark"], bevel=.005)
    p.box("drawbar", (1.3, .1, .08), (1.1, 0, .40), m["dark"], bevel=.01)
    p.box("coupler", (.2, .14, .12), (1.75, 0, .42), m["dark"], bevel=.02)
    p.cyl("jack", .03, .4, (1.35, .12, .2), m["steel"], verts=8)
    p.cyl("jack_foot", .07, .03, (1.35, .12, .015), m["dark"], verts=10)
    p.box("mast", (.14, .14, 1.9), (0, 0, 1.6), m["dark"], bevel=.01)
    p.box("mast2", (.1, .1, 1.3), (0, 0, 2.6), m["grey"], bevel=.008)
    p.box("board", (2.1, .22, 1.25), (0, 0, 3.0), m["dark"], bevel=.03, seg=2)
    p.box("board_face", (1.95, .02, 1.1), (0, -.115, 3.0), m["ledOff"], bevel=0)
    p.txt("LENTIDÃO", .32, (0, -.13, 3.2), m["amber"], face="-Y")
    p.txt("+15 MIN", .26, (0, -.13, 2.8), m["amber"], face="-Y")
    p.box("board_hood", (2.2, .3, .06), (0, -.04, 3.65), m["dark"], bevel=.01)
    p.box("solar_frame", (1.3, .9, .05), (0, .05, 3.9), m["steel"], rot=(rad(28), 0, 0), bevel=.01)
    p.box("solar_cells", (1.2, .8, .02), (0, .05 - .015, 3.92), m["solar"], rot=(rad(28), 0, 0), bevel=0)
    return p.o

@E.event
def v2_Engarrafamento(c):
    E.diorama(c, w=18); cols = ["red", "blue", "white", "yellow", "teal", "lime", "purple"]
    for i, vx in enumerate((-6.6, -2.3, 2.0, 6.3)):
        put(hatchback(c, cols[i]), x=vx, y=-2.75)
    for i, vx in enumerate((-4.4, .2, 4.8)):
        put(hatchback(c, cols[i + 4]), x=vx, y=-4.8, rot=math.pi)
    put(message_board(c), x=5.6, y=-.3, z=.13, rot=rad(-15))
    E.actor(c, "Customer_08", (-1.0, .9), rad(160))

# ================================================================== 4. VIGILANCIA SANITARIA
def sedan_vigilancia(c):
    """White compact sedan 4.45 x 1.75 x 1.46 m, green stripe, VIGILANCIA SANITARIA, roof sign, door emblem."""
    p = P(c); m = mats(); Lc, Wc = 4.45, 1.75; hw = Wc / 2; fx, bx = Lc / 2, -Lc / 2; R = .30; Wt = m["white"]
    body = p.box("body", (Lc, Wc, .58), (0, 0, .33 + .29), Wt, bevel=.11, seg=3)
    p.box("sill", (Lc - .8, Wc - .08, .14), (0, 0, .33), m["ink"], bevel=.03, seg=1)
    p.prism("bonnet", fx - 1.4, fx - .05, fx - 1.4, fx - .4, hw - .06, .88, .98, Wt, yt=hw - .1, bevel=.05)
    p.prism("boot", bx + .05, bx + 1.1, bx + .3, bx + 1.1, hw - .06, .88, 1.02, Wt, yt=hw - .1, bevel=.05)
    z0, z1 = .90, 1.46; yb, yt = hw - .05, hw - .17
    p.prism("cabin", -1.25, 1.1, -.95, -.1, yb, z0, z1, Wt, yt=yt, bevel=.09, seg=3)
    y_at = lambda z: yb + (yt - yb) * (z - z0) / (z1 - z0); tilt = math.atan2(yb - yt, z1 - z0)
    p.pane("windshield", (1.05, z0 + .02), (-.15, z1 - .02), 2 * yt - .1, m["glass"])
    p.pane("rear_glass", (-.95, z1 - .02), (-1.22, z0 + .02), 2 * yt - .1, m["glass"])
    for s in (-1, 1):
        for ax in (fx - .78, bx + .80):
            p.arch(body, ax, s * hw, R + .09, R + .02, w=.5)
            p.cyl("archliner", R + .08, .1, (ax, s * (hw - .42), R + .02), m["ink"], rot=(rad(90), 0, 0), verts=16)
            p.wheel((ax, s * (hw - .14), R + .02), R=R, w=.2, side=s, verts=18)
        zc = (z0 + z1) / 2 + .02
        p.side_glass("win_front", .35, .80, zc, .40, s, y_at, tilt, m["glass"])
        p.side_glass("win_rear", -.52, .70, zc, .40, s, y_at, tilt, m["glass"])
        p.seam(-.1, s * hw, .36, .9, face=s); p.seam(-1.0, s * hw, .36, .9, face=s); p.seam(fx - 1.3, s * hw, .36, .9, face=s)
        p.handle((.15, s * hw, .80), face=s); p.handle((-.75, s * hw, .80), face=s)
        p.mirror((.78, s * (y_at(1.05) - .02), 1.05), s, arm=.1, h=.14, w=.16, m=Wt)
        p.lamp("headlamp", (.05, .38, .17), (fx + .01, s * .56, .72), m["lamp"])
        p.lamp("taillamp", (.05, .32, .16), (bx - .01, s * .58, .84), m["tail"])
        p.box("wiper", (.02, .5, .025), (.95, s * .3, .97), m["ink"], rot=(0, rad(-28), rad(-25 * s)), bevel=0)
        face = "-Y" if s < 0 else "+Y"
        p.box("stripe", (Lc - 1.0, .02, .16), (-.05, s * (hw + .006), .58), m["green"], bevel=.004)
        p.box("stripe_thin", (Lc - 1.0, .02, .04), (-.05, s * (hw + .006), .70), m["greenD"], bevel=.003)
        p.txt("VIGILÂNCIA SANITÁRIA", .115, (.15, s * (hw + .018), .83), m["greenD"], face=face)
        p.cyl("emblem", .14, .02, (-1.0, s * (hw + .012), .95), m["green"], rot=(rad(90), 0, 0), verts=18)
        p.cyl("emblem_in", .10, .02, (-1.0, s * (hw + .02), .95), Wt, rot=(rad(90), 0, 0), verts=18)
        p.box("emblem_cross_v", (.035, .02, .12), (-1.0, s * (hw + .028), .95), m["green"], bevel=0)
        p.box("emblem_cross_h", (.12, .02, .035), (-1.0, s * (hw + .028), .95), m["green"], bevel=0)
    p.box("grille", (.04, .9, .14), (fx + .01, 0, .72), m["ink"], bevel=.015)
    p.box("grille_bar", (.03, .9, .025), (fx + .03, 0, .72), m["chrome"], bevel=0)
    p.box("grille_low", (.04, 1.0, .16), (fx + .02, 0, .42), m["ink"], bevel=.015)
    p.box("bumper_f", (.16, Wc + .02, .26), (fx + .02, 0, .48), Wt, bevel=.07, seg=2)
    p.box("bumper_r", (.16, Wc + .02, .26), (bx - .02, 0, .48), Wt, bevel=.07, seg=2)
    p.box("boot_line", (.02, Wc - .5, .015), (bx + .08, 0, 1.03), m["ink"], bevel=0)
    p.plate(fx + .1, 0, .60, "+X", "VIG 1S23"); p.plate(bx - .1, 0, .62, "-X", "VIG 1S23")
    p.box("roof_sign_base", (1.0, .34, .04), (-.5, 0, z1 + .01), m["dark"], bevel=.008)
    p.box("roof_sign", (.95, .3, .24), (-.5, 0, z1 + .14), m["green"], bevel=.03, seg=2)
    p.txt("VIGILÂNCIA", .085, (-.5, -.165, z1 + .14), Wt, face="-Y")
    p.txt("VIGILÂNCIA", .085, (-.5, .165, z1 + .14), Wt, face="+Y")
    p.cyl("roof_beacon", .06, .08, (-.5, 0, z1 + .30), m["amber"], verts=10)
    p.cyl("antenna", .008, .3, (-1.1, .4, z1 + .05), m["ink"], verts=6)
    p.box("exhaust", (.2, .05, .05), (bx + .05, -.5, .26), m["chrome"], bevel=.01)
    return p.o

@E.event
def v2_VigilanciaSanitaria(c):
    E.diorama(c); m = mats()
    put(sedan_vigilancia(c), x=-1.4, y=-2.75)
    E.actor(c, "Customer_08", (1.4, 3.6), rad(10)); E.actor(c, "Customer_06", (.2, 2.6), rad(60))
    k.box("clipboard", (.25, .02, .32), (1.25, 3.3, 1.1), m["wood"], rot=(rad(-30), 0, 0), bevel=.005, c=c)
    k.box("clip_paper", (.22, .01, .26), (1.25, 3.28, 1.1), m["paper"], rot=(rad(-30), 0, 0), c=c)
    k.box("inspection_case", (.45, .15, .32), (1.9, 3.5, .3), m["dark"], bevel=.02, c=c)

# ================================================================== 5. CARRO DE SOM
def sound_van(c):
    """Retro one-box van 4.3 x 1.8 x 2.0 m (Kombi-like, no brand): purple lower / cream upper, V nose,
    split windscreen, 4 horn speakers on a roof rack, banners on both sides."""
    p = P(c); m = mats(); Lv, Wv, H = 4.3, 1.8, 1.95; hw = Wv / 2; fx, bx = Lv / 2, -Lv / 2; R = .32
    body = p.box("body_low", (Lv, Wv, .78), (0, 0, .36 + .39), m["purple"], bevel=.14, seg=3)
    up = p.box("body_up", (Lv, Wv, .86), (0, 0, 1.13 + .43), m["cream"], bevel=.16, seg=3)
    p.box("roof", (Lv - .3, Wv - .25, .08), (0, 0, H + .02), m["cream"], bevel=.03, seg=2)
    p.box("beltline", (Lv + .02, Wv + .02, .04), (0, 0, 1.13), m["chrome"], bevel=.01)
    for s in (-1, 1):
        for ax in (fx - .8, bx + .85):
            p.arch(body, ax, s * hw, R + .1, R + .02, w=.5)
            p.cyl("archliner", R + .08, .1, (ax, s * (hw - .42), R + .02), m["ink"], rot=(rad(90), 0, 0), verts=16)
            p.wheel((ax, s * (hw - .15), R + .02), R=R, w=.2, side=s, hub="white", verts=22)
    # V nose: two angled cream panels over the purple front, big round headlamps
    for s in (-1, 1):
        p.box("nose_v", (.03, .95, .22), (fx + .012, s * .36, .98), m["cream"], rot=(rad(-32 * s), 0, 0), bevel=.006)
        p.cyl("headlamp_ring", .17, .05, (fx + .02, s * .6, 1.08), m["chrome"], rot=(0, rad(90), 0), verts=18)
        p.cyl("headlamp", .13, .05, (fx + .04, s * .6, 1.08), m["lamp"], rot=(0, rad(90), 0), verts=18)
        p.box("indicator", (.04, .14, .08), (fx + .03, s * .6, .78), m["amber"], bevel=.01)
        p.box("ws_half", (.05, .72, .55), (fx + .01, s * .4, 1.52), m["glass"], bevel=.03)
        p.box("ws_post", (.06, .06, .58), (fx + .015, 0, 1.52), m["cream"], bevel=.005)
        p.box("wiper", (.02, .4, .025), (fx + .04, s * .45, 1.3), m["ink"], rot=(rad(-35 * s), 0, 0), bevel=0)
        p.mirror((fx - .55, s * hw, 1.45), s, arm=.2, h=.2, w=.16, m=m["chrome"])
        # side windows: door window, 2 body windows, cream pillars in between
        yy = s * (hw + .004)
        for wx, ww in ((fx - .75, .7), (fx - 1.7, .95), (bx + 1.0, .95)):
            p.box("win_frame", (ww + .06, .02, .6), (wx, yy, 1.55), m["ink"], bevel=.006)
            p.box("win", (ww, .025, .54), (wx, yy + s * .008, 1.55), m["glass"], bevel=.02)
        p.seam(fx - 1.15, s * hw, .4, 1.9, face=s)
        p.seam(fx - 1.22, s * hw, .4, 1.9, face=s) if False else None
        p.handle((fx - .95, s * hw, 1.05), face=s); p.handle((fx - 1.35, s * hw, 1.05), face=s)
        p.seam(bx + 1.5, s * hw, .4, 1.9, face=s)
        p.box("slide_rail", (1.0, .02, .03), (bx + 1.0, s * (hw + .006), 1.9), m["chrome"], bevel=0)
        p.box("taillamp", (.04, .12, .22), (bx - .01, s * .6, .95), m["tail"], bevel=.015)
        p.box("tail_bezel", (.03, .16, .26), (bx - .005, s * .6, .95), m["chrome"], bevel=.006)
        # banners
        p.box("banner", (2.8, .03, .55), (-.1, s * (hw + .03), 1.0), m["yellow"], bevel=.008)
        p.box("banner_border", (2.86, .02, .61), (-.1, s * (hw + .025), 1.0), m["red"], bevel=.008)
        face = "-Y" if s < 0 else "+Y"
        p.txt("SUPER LEVA MAIS", .2, (-.1, s * (hw + .052), 1.1), m["purple"], face=face, res=2)
        p.txt("TUDO EM OFERTA!", .14, (-.1, s * (hw + .052), .86), m["red"], face=face, res=2)
    p.box("bumper_f", (.14, Wv + .06, .14), (fx + .04, 0, .46), m["chrome"], bevel=.04, seg=2)
    p.box("bumper_r", (.14, Wv + .06, .14), (bx - .04, 0, .46), m["chrome"], bevel=.04, seg=2)
    p.cyl("emblem", .11, .03, (fx + .03, 0, 1.22), m["chrome"], rot=(0, rad(90), 0), verts=16)
    p.box("nose_panel", (.02, Wv - .3, .3), (fx + .005, 0, 1.0), m["cream"], bevel=.004)
    p.plate(fx + .1, 0, .62, "+X", "SOM 4D44"); p.plate(bx - .07, 0, .62, "-X", "SOM 4D44")
    # rear engine lid with louvres, rear window
    p.box("rear_glass", (.04, 1.1, .5), (bx - .005, 0, 1.55), m["glass"], bevel=.03)
    p.box("engine_lid", (.03, 1.2, .5), (bx - .005, 0, .9), m["purple"], bevel=.01)
    for i in range(4):
        p.box("louvre", (.03, 1.0, .03), (bx - .025, 0, .75 + i * .1), m["purpleD"], bevel=0)
    # roof rack with 4 horn speakers
    for s in (-1, 1):
        p.box("rack_rail", (2.2, .05, .05), (0, s * .62, H + .14), m["steel"], bevel=.006)
        for xx in (-1.0, 1.0):
            p.box("rack_leg", (.05, .05, .14), (xx, s * .62, H + .07), m["steel"], bevel=0)
    for xx in (-.9, .9):
        p.box("rack_x", (.05, 1.3, .05), (xx, 0, H + .14), m["steel"], bevel=.006)
    p.box("amp_box", (.6, .5, .3), (0, 0, H + .32), m["dark"], bevel=.03)
    for (hx, hy, ry, rz) in ((-.75, -.3, 90, 0), (.75, -.3, -90, 0), (-.35, .35, 90, -90), (.35, .35, -90, -90)):
        # two horns along the van, two facing the kerb (-Y)
        R_ = Matrix.Rotation(rad(rz), 4, 'Z') @ Matrix.Rotation(rad(ry), 4, 'Y')
        ax = (R_ @ Vector((0, 0, 1))).normalized()
        base = Vector((hx, hy, H + .42))
        h = p.cyl("horn", .07, .45, base + ax * .12, m["white"], r2=.26, verts=14); h.matrix_world = Matrix.Translation(base + ax * .12) @ R_
        d_ = p.cyl("horn_driver", .10, .16, base - ax * .2, m["dark"], verts=10); d_.matrix_world = Matrix.Translation(base - ax * .2) @ R_
        p.box("horn_bracket", (.07, .07, .24), (hx, hy, H + .28), m["steel"], bevel=0)
    return p.o

@E.event
def v2_CarroDeSom(c):
    E.diorama(c)
    put(sound_van(c), x=1.0, y=-4.6)
    for (bx_, col) in ((-1.25, "yellow"), (-1.0, "purple")):
        E.balloon(c, (bx_, -4.0, 3.0), col)
    E.actor(c, "Customer_07", (-2.4, .6), rad(200)); E.actor(c, "Customer_09", (2.6, 1.0), rad(160))

# ================================================================== 6. MAQUININHA FORA DO AR
def telecom_van(c):
    """White panel van 5.2 x 2.0 x 2.3 m, orange stripe, roof rack with a ladder, amber beacon."""
    p = P(c); m = mats(); Lv, Wv, H = 5.2, 2.0, 2.3; hw = Wv / 2; fx, bx = Lv / 2, -Lv / 2; R = .34; Wt = m["white"]
    cabF = fx - 1.15   # where the cargo body ends and the sloped cab front begins
    body = p.box("body", (cabF - bx, Wv, H - .4), (bx + (cabF - bx) / 2, 0, .4 + (H - .4) / 2), Wt, bevel=.15, seg=3)
    nose = p.box("nose", (fx - cabF + .2, Wv - .04, .8), (fx - (fx - cabF + .2) / 2, 0, .8), Wt, bevel=.12, seg=3)
    p.prism("bonnet", cabF - .2, fx - .05, cabF - .2, fx - .5, hw - .05, 1.18, 1.32, Wt, yt=hw - .1, bevel=.05)
    p.prism("cab_front", cabF - .2, fx - .5, cabF - .2, cabF - .05, hw - .02, 1.3, H - .02, Wt, yt=hw - .1, bevel=.06, seg=2)
    p.pane("windshield", (fx - .5, 1.34), (cabF - .05, H - .06), Wv - .5, m["glass"])
    for s in (-1, 1):
        for ax in (fx - 1.0, bx + 1.0):
            p.arch(nose if ax > 0 else body, ax, s * hw, R + .1, R + .02, w=.5)
            if ax > 0: p.arch(body, ax, s * hw, R + .1, R + .02, w=.5)
            p.cyl("archliner", R + .08, .1, (ax, s * (hw - .42), R + .02), m["ink"], rot=(rad(90), 0, 0), verts=16)
            p.wheel((ax, s * (hw - .14), R + .02), R=R, w=.22, side=s, hub="rimD", verts=18)
        yy = s * (hw + .004)
        p.box("door_win_frame", (1.0, .02, .66), (cabF - .5, yy, 1.66), m["ink"], bevel=.006)
        p.box("door_win", (.9, .025, .58), (cabF - .5, yy + s * .008, 1.66), m["glass"], bevel=.02)
        p.seam(cabF - 1.02, s * hw, .45, 2.0, face=s); p.seam(cabF + .02, s * hw, .45, 1.3, face=s)
        p.handle((cabF - .85, s * hw, 1.1), face=s)
        if s < 0:
            p.seam(bx + 1.6, s * hw, .45, 2.0, face=s); p.handle((bx + 1.75, s * hw, 1.1), face=s)
            p.box("slide_rail", (1.6, .02, .035), (bx + 1.2, s * (hw + .006), 1.95), m["ink"], bevel=0)
        p.box("stripe", (Lv - .5, .02, .22), (-.2, s * (hw + .006), 1.1), m["orange"], bevel=.004)
        p.box("stripe2", (Lv - .5, .02, .05), (-.2, s * (hw + .006), .95), m["navy"], bevel=.003)
        p.txt("TELECOM - ASSISTÊNCIA TÉCNICA", .11, (-.7, s * (hw + .018), 1.42), m["navy"], face="-Y" if s < 0 else "+Y")
        p.mirror((cabF - .95, s * (hw - .02), 1.5), s, arm=.12, h=.26, w=.18, m=m["dark"])
        p.lamp("headlamp", (.05, .40, .24), (fx + .01, s * .6, .82), m["lamp"])
        p.box("indicator", (.04, .14, .08), (fx + .025, s * .62, .6), m["amber"], bevel=.01)
        p.lamp("taillamp", (.04, .16, .5), (bx - .01, s * (hw - .16), 1.1), m["tail"])
        p.box("wiper", (.02, .55, .025), (fx - .55, s * .32, 1.42), m["ink"], rot=(0, rad(-40), rad(-25 * s)), bevel=0)
        p.box("rack_rail", (3.0, .05, .06), (-.6, s * .72, H + .06), m["dark"], bevel=.006)
        for xx in (-1.9, -.6, .7):
            p.box("rack_leg", (.06, .05, .1), (xx, s * .72, H + .0), m["dark"], bevel=0)
        p.box("rear_handle", (.025, .04, .18), (bx - .012, s * .12, 1.15), m["chrome"], bevel=.005)
        p.box("rear_win", (.025, .7, .5), (bx - .012, s * .42, 1.7), m["glass"], bevel=.02)
    for xx in (-1.9, -.6, .7):
        p.box("rack_x", (.05, 1.5, .05), (xx, 0, H + .07), m["dark"], bevel=.004)
    p.box("rear_door_line", (.012, .022, 1.6), (bx - .004, 0, 1.3), m["ink"], bevel=0)
    p.box("grille", (.04, 1.1, .16), (fx + .01, 0, .8), m["ink"], bevel=.015)
    p.box("grille_bar", (.03, 1.1, .03), (fx + .03, 0, .8), m["chrome"], bevel=0)
    p.box("grille_low", (.04, 1.2, .18), (fx + .02, 0, .5), m["ink"], bevel=.015)
    p.box("bumper_f", (.18, Wv + .02, .3), (fx + .02, 0, .55), m["dark"], bevel=.07, seg=2)
    p.box("bumper_r", (.14, Wv + .02, .26), (bx - .02, 0, .5), m["dark"], bevel=.06, seg=2)
    p.box("step_r", (.3, 1.2, .04), (bx - .1, 0, .34), m["steel"], bevel=.01)
    p.plate(fx + .11, 0, .62, "+X", "TEL 3C33"); p.plate(bx - .09, 0, .70, "-X", "TEL 3C33")
    lz = H + .16
    for s in (-1, 1):
        p.box("ladder_rail", (3.4, .04, .07), (-.5, s * .2, lz), m["steel"], bevel=.005)
    for i in range(10):
        p.box("ladder_rung", (.035, .4, .03), (-2.05 + i * .35, 0, lz), m["steel"], bevel=0)
    p.box("ladder_strap", (.04, .5, .1), (.2, 0, lz + .01), m["orange"], bevel=.005)
    p.cyl("beacon_base", .09, .03, (cabF - .4, 0, H + .02), m["dark"], verts=10)
    p.cyl("beacon", .07, .12, (cabF - .4, 0, H + .09), m["amber"], verts=10, bevel=.01)
    p.cyl("antenna", .008, .35, (cabF - .7, -.6, H + .17), m["ink"], verts=6)
    return p.o

@E.event
def v2_MaquininhaVan(c):
    E.diorama(c); m = mats(); x, y = -3.8, -.9
    k.cyl("utility_pole", .14, 7.0, (x, y, 3.6), m["concrete"], r2=.1, verts=12, c=c)
    k.box("crossarm", (1.6, .1, .1), (x, y, 6.6), m["wood"], c=c)
    k.box("cto_box", (.45, .25, .6), (x, y - .2, 4.4), m["dark"], bevel=.03, c=c)
    k.box("cto_led", (.05, .02, .05), (x + .12, y - .33, 4.55), m["ledR"], c=c)
    for i in range(3):
        k.tube("cable", (x - 6, y + .2 * i, 6.3 - i * .2), (x + 6, y + .2 * i, 6.2 - i * .2), .015, m["ink"], verts=4, c=c)
    lx, ly = x + .55, y - .5
    for s in (-1, 1):
        k.tube("ladder_rail", (lx + s * .22, ly - .5, .13), (lx + s * .22, ly + .1, 4.3), .03, m["steel"], verts=6, c=c)
    for i in range(12):
        t = i / 11; zz = .3 + t * 3.9; yy = ly - .5 + t * .6
        k.box("rung", (.44, .03, .03), (lx, yy, zz), m["steel"], c=c)
    k.cyl("cable_reel", .35, .3, (x + 1.8, -.2, .48), m["wood"], rot=(rad(90), 0, 0), verts=20, c=c)
    k.cyl("cable_core", .2, .32, (x + 1.8, -.2, .48), m["ink"], rot=(rad(90), 0, 0), verts=16, c=c)
    put(telecom_van(c), x=-.2, y=-2.95)
    E.actor(c, "Customer_07", (lx, ly + .2, 2.4), rad(180)); E.actor(c, "Customer_09", (1.6, 3.4), rad(20))
    k.box("door_sign", (.6, .02, .4), (.6, 5.3, 1.5), m["yellow"], bevel=.01, c=c)
    E.label(c, "SÓ DINHEIRO", .08, (.6, 5.28, 1.55), m["red"])
    k.box("door_sign_x", (.3, .02, .06), (.6, 5.28, 1.4), m["red"], rot=(0, rad(45), 0), c=c)

# ================================================================== 7. EXCURSAO DA ESCOLA
def school_bus(c):
    """Classic yellow school bus 9.0 x 2.4 x 3.0 m with a sloped hood, black stripes, ESCOLAR, stop arm on -Y,
    door on +Y (sidewalk)."""
    p = P(c); m = mats(); Lb, Wb, H, z0 = 9.0, 2.4, 3.0, .55; hw = Wb / 2; fx, bx = Lb / 2, -Lb / 2; R = .48
    Y = m["yellowS"]; hoodL = 1.7; bodyL = Lb - hoodL; bcx = bx + bodyL / 2; bf = bx + bodyL
    body = p.box("body", (bodyL, Wb, H - z0), (bcx, 0, z0 + (H - z0) / 2), Y, bevel=.15, seg=3)
    p.prism("hood", bf - .1, fx, bf - .1, fx - .12, hw - .25, z0 + .05, 1.62, Y, yt=hw - .35, bevel=.09, seg=3)
    p.prism("cowl", bf - .15, bf + .35, bf - .15, bf - .05, hw - .02, 1.55, 1.85, Y, yt=hw - .1, bevel=.03)
    p.box("chassis", (Lb - .8, Wb - .9, .4), (-.2, 0, .45), m["ink"], bevel=.02)
    p.box("front_frame", (hoodL, 1.1, .5), (fx - hoodL / 2, 0, .5), m["ink"], bevel=.02)
    for s in (-1, 1):
        for ax in (fx - 1.95, bx + 2.3):
            if ax < 0:
                p.arch(body, ax, s * hw, R + .12, R + .02, w=.6)
                p.cyl("archliner", R + .1, .12, (ax, s * (hw - .42), R + .02), m["ink"], rot=(rad(90), 0, 0), verts=16)
            p.wheel((ax, s * (hw - .2), R + .02), R=R, w=.3, side=s)
        p.wheel((bx + 2.3, s * (hw - .5), R + .02), R=R, w=.3, side=s, nuts=0)
        p.box("fender", (1.35, .42, .14), (fx - 1.95, s * (hw - .2), R * 2 + .18), Y, bevel=.06, seg=2)
        p.box("fender_side", (1.0, .06, .26), (fx - 1.95, s * (hw - .02), R * 2 + .06), Y, bevel=.02)
        p.box("step", (.5, .3, .05), (bf + .3, s * (hw - .5), .62), m["steel"], bevel=.01) if s > 0 else None
    for s in (-1, 1):
        yy = s * (hw + .006)
        p.box("win_band", (bodyL - .8, .025, 1.0), (bcx - .1, yy, 2.15), m["ink"], bevel=.01)
        n = 8; w0 = (bodyL - .8) / n
        for i in range(n):
            px = bcx - .1 - (bodyL - .8) / 2 + w0 * (i + .5)
            if s == 1 and i == n - 1: continue
            p.box("win", (w0 - .12, .03, .86), (px, yy + s * .012, 2.15), m["glass"], bevel=.02)
            p.box("win_split", (w0 - .12, .012, .02), (px, yy + s * .03, 2.25), m["ink"], bevel=0)
        p.box("stripe_black", (bodyL - .3, .02, .14), (bcx, yy, 1.52), m["ink"], bevel=.004)
        p.box("stripe_black2", (bodyL - .3, .02, .14), (bcx, yy, .98), m["ink"], bevel=.004)
        p.txt("ESCOLAR", .36, (bcx - .4, yy + s * .012, 1.26), m["ink"], face="-Y" if s < 0 else "+Y")
        p.txt("ESCOLA MUNICIPAL", .10, (bcx + 1.8, yy + s * .012, 1.78), m["ink"], face="-Y" if s < 0 else "+Y")
        p.box("marker_f", (.12, .03, .06), (bf - .3, yy + s * .01, 2.78), m["amber"], bevel=.006)
        p.box("marker_r", (.12, .03, .06), (bx + .3, yy + s * .01, 2.78), m["tail"], bevel=.006)
    dx = bf - .62
    p.box("door_frame", (1.0, .04, 2.2), (dx, hw + .014, 1.75), m["ink"], bevel=.012)
    for lx in (-.24, .24):
        p.box("door_leaf", (.44, .03, 2.05), (dx + lx, hw + .035, 1.75), Y, bevel=.01)
        p.box("door_glass", (.34, .02, .8), (dx + lx, hw + .052, 2.15), m["glass"], bevel=.012)
        p.box("door_glass2", (.34, .02, .5), (dx + lx, hw + .052, 1.35), m["glass"], bevel=.012)
    p.pane("windshield", (bf + .04, 1.86), (bf - .02, 2.75), Wb - .4, m["glass"], proud=.03)
    p.box("ws_post", (.07, .06, .95), (bf + .02, 0, 2.3), m["ink"], bevel=0)
    p.box("roof_sign", (.1, 1.3, .3), (bf + .01, 0, 2.86), m["ink"], bevel=.02)
    p.txt("ESCOLAR", .17, (bf + .065, 0, 2.85), m["amber"], face="+X")
    p.box("grille", (.05, 1.1, .5), (fx + .005, 0, 1.0), m["ink"], bevel=.02)
    for i in range(6):
        p.box("grille_bar", (.03, 1.0, .03), (fx + .035, 0, .8 + i * .08), m["chrome"], bevel=0)
    p.box("bumper_f", (.2, Wb - .1, .3), (fx + .04, 0, .5), m["ink"], bevel=.06, seg=2)
    p.box("bumper_r", (.2, Wb + .02, .3), (bx - .06, 0, .5), m["ink"], bevel=.06, seg=2)
    for s in (-1, 1):
        p.cyl("headlamp_ring", .15, .05, (fx + .01, s * .62, 1.12), m["chrome"], rot=(0, rad(90), 0), verts=16)
        p.cyl("headlamp", .11, .05, (fx + .03, s * .62, 1.12), m["lamp"], rot=(0, rad(90), 0), verts=16)
        p.box("indicator", (.04, .18, .1), (fx + .02, s * .62, .82), m["amber"], bevel=.01)
        p.box("mirror_arm", (.35, .05, .05), (bf + .15, s * (hw + .17), 2.35), m["ink"], bevel=0)
        p.box("mirror_post", (.05, .05, .9), (bf + .3, s * (hw + .17), 1.95), m["ink"], bevel=0)
        p.box("mirror_h", (.07, .2, .42), (bf + .3, s * (hw + .3), 2.0), m["ink"], bevel=.03)
        p.box("mirror_g", (.012, .16, .36), (bf + .34, s * (hw + .3), 2.0), m["glassL"], bevel=0)
        p.box("wiper", (.03, .6, .03), (bf + .075, s * .5, 2.1), m["ink"], rot=(rad(-30 * s), 0, 0), bevel=0)
        p.cyl("roof_flash", .08, .1, (bf - .3, s * .8, H + .08), m["tail"] if s < 0 else m["amber"], verts=12)
        p.cyl("roof_flash_r", .08, .1, (bx + .4, s * .8, H + .08), m["tail"], verts=12)
        p.box("taillamp", (.05, .16, .16), (bx - .02, s * .9, 1.3), m["tail"], bevel=.02)
        p.box("taillamp2", (.05, .16, .16), (bx - .02, s * .9, 1.1), m["amber"], bevel=.02)
    p.plate(fx + .15, 0, .78, "+X", "ESC 5E55"); p.plate(bx - .17, 0, .78, "-X", "ESC 5E55")
    p.box("rear_door", (.04, 1.1, 1.8), (bx - .005, 0, 1.75), Y, bevel=.01)
    p.box("rear_glass", (.04, .9, .7), (bx - .015, 0, 2.2), m["glass"], bevel=.03)
    p.txt("SAÍDA DE EMERGÊNCIA", .07, (bx - .03, 0, 1.6), m["ink"], face="-X")
    p.box("roof_hatch", (.7, .7, .06), (bcx + .5, 0, H + .02), Y, bevel=.02)
    p.box("roof_hatch2", (.7, .7, .06), (bcx - 2.0, 0, H + .02), Y, bevel=.02)
    p.cyl("exhaust", .05, .9, (bx + .8, -(hw - .25), .32), m["grey"], rot=(0, rad(90), 0), verts=8)
    sx_ = bf - 1.0; sy = -(hw + .01)
    p.box("arm_hinge", (.1, .06, .5), (sx_, sy, 1.95), m["ink"], bevel=.008)
    p.box("arm_bar", (.05, .55, .05), (sx_, sy - .3, 1.95), m["ink"], bevel=.005)
    p.cyl("stop_sign", .28, .03, (sx_, sy - .6, 1.95), m["red"], rot=(rad(90), 0, 0), verts=8)
    p.cyl("stop_sign_rim", .3, .02, (sx_, sy - .59, 1.95), m["white"], rot=(rad(90), 0, 0), verts=8)
    p.txt("PARE", .13, (sx_, sy - .62, 1.95), m["white"], face="-Y")
    for s in (-1, 1):
        p.cyl("stop_led", .035, .02, (sx_, sy - .625, 1.95 + s * .19), m["ledR"], rot=(rad(90), 0, 0), verts=8)
    return p.o

def kid(c, who, loc, rot=0.0, scale=.55):
    """One of the game's customers scaled down (no child mesh exists in Assets/Art/Characters/Meshy; the
    CustomerChild texture does not fit the adult UVs) - previews only."""
    return E.actor(c, who, loc, rot, scale)

@E.event
def v2_ExcursaoDaEscola(c):
    E.diorama(c)
    put(school_bus(c), x=-.6, y=-2.75)
    kids = ["Customer_06", "Customer_07", "Customer_08", "Customer_09"]
    spots = [(1.2, .1, 110), (2.0, 1.0, 80), (2.9, .3, 60), (3.7, 1.3, 100), (4.6, .5, 40), (5.3, 1.7, 70), (2.6, 2.3, 120), (4.2, 2.8, 90)]
    for i, (px, py, r) in enumerate(spots):
        kid(c, kids[i % 4], (px, py), rad(r))
    E.actor(c, "Customer_08", (1.4, 3.2), rad(-30))   # teacher counting heads
    E.actor(c, "Customer_06", (6.2, 3.4), rad(200))

PROPS = {"Rush_CityBus": (city_bus, 2048), "Rush_BusShelter": (bus_shelter, 1024),
         "Ofertas_BoxTruck": (box_truck, 2048), "Ofertas_PalletStack": (pallet_stack, 1024), "Ofertas_PalletJack": (pallet_jack, 512),
         "Transito_Car": (hatchback, 2048), "Transito_MessageBoard": (message_board, 1024),
         "Vigilancia_Car": (sedan_vigilancia, 2048), "Som_Van": (sound_van, 2048),
         "Maquininha_TelecomVan": (telecom_van, 2048), "Excursao_SchoolBus": (school_bus, 2048)}
# colour variants of the traffic-jam hatchback (the game picks one per car)
for _paint in ("blue", "yellow", "white", "teal", "green"):
    PROPS["Transito_Car" + _paint.capitalize()] = ((lambda paint: (lambda c: hatchback(c, paint=paint)))(_paint), 1024)

def export(names=None):
    out = {}
    for n in (names or PROPS):
        fn, size = PROPS[n]
        c = E.prop_collection(n); mats(); fn(c)
        out[n] = E.export_prop(n, size=size)
        print("EXPORTED", n, out[n], flush=True)
    return out
