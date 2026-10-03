# street.py - street furniture v2 (Quinto dia util, Feira de rua, Onda de calor, Sorteio na porta, Dia de jogo).
# Builders model at the origin, ground z=0, the readable side facing -Y (camera). Each returns its objects
# (place them with put()). Headless runner: run_street.py (preview | tris | export).
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
if ART not in sys.path: sys.path.insert(0, ART)
import events_kit as E
import era_kit as k
rad = math.radians
C = E.C

XM = {}
def mats():
    m = E.mats()
    if XM: return XM
    XM.update(m)
    XM["galv"] = k.mat("EV_Galv", (.62, .66, .70, 1), rough=.45, var=.08, scale=10, metallic=.5)
    XM["navyD"] = k.mat("EV_NavyDark", (.04, .08, .22, 1), rough=.5, var=.05, scale=6)
    XM["plastic"] = k.mat("EV_PlasticWhite", (.93, .93, .90, 1), rough=.35, var=.03, scale=8)
    XM["chalk"] = k.mat("EV_Chalk", (.12, .14, .13, 1), rough=.95, var=.08, scale=20, bump=.3)
    XM["brass"] = k.mat("EV_Brass", (.85, .68, .30, 1), rough=.3, var=.05, scale=8, metallic=.7)
    XM["ice"] = k.mat("EV_IceBlue", (.70, .88, .96, 1), rough=.3, var=.04, scale=8)
    XM["coolerB"] = k.mat("EV_CoolerBlue", (.12, .36, .72, 1), rough=.4, var=.05, scale=8)
    XM["pitch"] = k.emissive("EV_Pitch", (.18, .70, .26, 1), 1.5)
    XM["pitchD"] = k.emissive("EV_PitchDark", (.14, .60, .22, 1), 1.5)
    XM["ledOff"] = k.mat("EV_LedOff", (.10, .10, .11, 1), rough=.5, var=.03, scale=20, bump=.4)
    XM["ledO"] = k.emissive("EV_LedOrange", (1.0, .45, .08, 1), 2.2)
    XM["ledHot"] = k.emissive("EV_LedHot", (1.0, .12, .04, 1), 2.0)
    XM["gingham"] = k.stripes("EV_Gingham", (.90, .25, .22, 1), (.97, .95, .90, 1), .07, axis='X', rough=.9)
    XM["canvasY"] = k.mat("EV_CanvasCream", (.95, .88, .66, 1), rough=.9, var=.08, scale=8, bump=.15)
    XM["woodD"] = k.wood("EV_WoodDark", (.52, .34, .18, 1), (.38, .23, .11, 1), scale=8)
    XM["concreteD"] = k.mat("EV_ConcreteDark", (.55, .54, .52, 1), rough=.95, var=.12, scale=9, bump=.25)
    XM["foil"] = k.mat("EV_Foil", (.80, .82, .85, 1), rough=.25, var=.06, scale=12, metallic=.6)
    XM["cup"] = k.mat("EV_CupGreen", (.15, .60, .30, 1), rough=.4, var=.04, scale=8)
    XM["cupY"] = k.mat("EV_CupYellow", (.98, .82, .20, 1), rough=.4, var=.04, scale=8)
    XM["waterB"] = k.mat("EV_WaterBlue", (.25, .55, .85, 1), rough=.2, var=.05, scale=8)
    XM["cardboard"] = k.mat("EV_Cardboard", (.72, .52, .30, 1), rough=.9, var=.10, scale=8)
    return XM

ROT = {"-Y": (rad(90), 0, 0), "+Y": (rad(90), 0, rad(180)), "+X": (rad(90), 0, rad(90)), "-X": (rad(90), 0, rad(-90)), "UP": (0, 0, 0)}

class P:
    """Collects the objects of one prop (thin wrappers over era_kit; small parts default to a 1-segment bevel)."""
    def __init__(self, c): self.c = c; self.o = []
    def box(self, name, size, loc, m, bevel=.008, seg=1, rot=(0, 0, 0)):
        o = k.box(name, size, loc, m, rot=rot, bevel=bevel, seg=seg, c=self.c); self.o.append(o); return o
    def cyl(self, name, r, h, loc, m, rot=(0, 0, 0), verts=16, bevel=0., seg=1, r2=None):
        o = k.cyl(name, r, h, loc, m, rot=rot, verts=verts, bevel=bevel, seg=seg, c=self.c, r2=r2); self.o.append(o); return o
    def ball(self, name, r, loc, m, sub=1, scale=(1, 1, 1), rot=(0, 0, 0)):
        o = k.ball(name, r, loc, m, sub=sub, scale=scale, rot=rot, c=self.c); self.o.append(o); return o
    def tube(self, name, a, b, r, m, verts=6):
        o = k.tube(name, a, b, r, m, verts=verts, c=self.c); self.o.append(o); return o
    def txt(self, s, size, loc, m, face="-Y", res=1, extrude=.003, spacing=1.0, rot=None, align='CENTER'):
        o = k.text("lbl", s, size, loc, m, rot=rot or ROT[face], extrude=extrude, c=self.c, res=res, spacing=spacing, align=align)
        self.o.append(o); return o
    def mesh(self, name, verts, faces, mlist, loc=(0, 0, 0), solid=0., smooth=False, bevel=0., midx=None, offset=-1):
        """bmesh polygon soup; `mlist` material slots, `midx` per-face material index; optional solidify."""
        bm = bmesh.new(); vs = [bm.verts.new(v) for v in verts]
        for i, f in enumerate(faces):
            try:
                face = bm.faces.new([vs[j] for j in f])
                if midx: face.material_index = midx[i]
            except ValueError:
                pass
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); self.c.objects.link(o); o.location = loc
        for mm in mlist: me.materials.append(mm)
        if solid:
            s = o.modifiers.new("solid", 'SOLIDIFY'); s.thickness = solid; s.offset = offset
        if bevel:
            b = o.modifiers.new("Bevel", 'BEVEL'); b.width = bevel; b.segments = 1; b.limit_method = 'ANGLE'; b.angle_limit = rad(40); b.harden_normals = True
        if smooth:
            for p_ in me.polygons: p_.use_smooth = True
        self.o.append(o); return o

def put(objs, x=0, y=0, z=0, rot=0.0, scale=None):
    Mw = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, 'Z')
    if scale: Mw = Mw @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1))
    for o in objs: o.matrix_world = Mw @ o.matrix_world
    return objs

# ------------------------------------------------------------------ shared helpers
def parasol(p, loc, h=2.2, R=1.0, ma=None, mb=None, mpole=None, panels=8, drop=.32, tilt=0.0, base=True, pole_r=.022):
    """Low-poly scalloped parasol (alternating panels, ribs, finial, pole, concrete base). ~350 tris."""
    m = mats(); ma = ma or m["orange"]; mb = mb or m["white"]; mpole = mpole or m["steel"]
    x, y, z = loc; n2 = panels * 2
    verts = [(0, 0, h + .02)]; inner = []; outer = []
    for i in range(n2):
        a = math.tau * i / n2; rib = i % 2 == 0
        ro = R if rib else R * .90; zo = h - drop if rib else h - drop * .82
        outer.append(len(verts)); verts.append((ro * math.cos(a), ro * math.sin(a), zo))
        inner.append(len(verts)); verts.append((R * .48 * math.cos(a), R * .48 * math.sin(a), h - drop * .28))
    faces = []; midx = []
    for i in range(n2):
        j = (i + 1) % n2
        faces.append((0, inner[i], inner[j])); midx.append((i // 2) % 2)
        faces.append((inner[i], outer[i], outer[j], inner[j])); midx.append((i // 2) % 2)
    can = p.mesh("parasol_canopy", verts, faces, [ma, mb], loc=(x, y, z), solid=.012, smooth=True, midx=midx)
    for i in range(panels):
        a = math.tau * i / panels
        p.tube("rib", (x, y, z + h), (x + R * .97 * math.cos(a), y + R * .97 * math.sin(a), z + h - drop), .007, mpole, verts=5)
    p.ball("finial", .035, (x, y, z + h + .05), m["gold"], sub=2)
    p.cyl("pole", pole_r, h, (x, y, z + h / 2), mpole, verts=10)
    p.cyl("hub", .035, .08, (x, y, z + h - .5), mpole, verts=8)
    if base:
        p.cyl("base", .19, .07, (x, y, z + .035), m["concreteD"], verts=18, bevel=.012, seg=2)
        p.cyl("base_ring", .07, .1, (x, y, z + .1), m["dark"], verts=10)
    if tilt:
        for o in p.o:
            if o.name.startswith(("parasol_canopy", "rib", "finial", "hub")):
                o.matrix_world = Matrix.Translation((x, y, z + h - .5)) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Translation((-x, -y, -(z + h - .5))) @ o.matrix_world
    return can

def valance(p, top_pts, drop, tab, m, n=None):
    """Scalloped canvas valance hanging from the polyline `top_pts` (list of (x,y,z)); band + triangular tabs."""
    verts = []; faces = []
    for a, b in zip(top_pts[:-1], top_pts[1:]):
        a, b = Vector(a), Vector(b); ln = (b - a).length; nn = n or max(2, int(ln / tab))
        T = []; M = []
        for i in range(nn + 1):
            q = a.lerp(b, i / nn); T.append(len(verts)); verts.append((q.x, q.y, q.z))
            M.append(len(verts)); verts.append((q.x, q.y, q.z - drop * .55))
        for i in range(nn):
            faces.append((T[i], T[i + 1], M[i + 1], M[i]))
            q = a.lerp(b, (i + .5) / nn); tip = len(verts); verts.append((q.x, q.y, q.z - drop))
            faces.append((M[i], M[i + 1], tip))
    return p.mesh("valance", verts, faces, [m], solid=.012, smooth=False, offset=0)

def spoked_wheel(p, loc, R=.3, w=.045, spokes=10, m_tyre=None, m_rim=None):
    m = mats(); x, y, z = loc; rot = (rad(90), 0, 0)
    p.cyl("tyre", R, w, loc, m_tyre or m["rubber"], rot=rot, verts=20, bevel=.014, seg=1)
    p.cyl("rim", R - .035, w * .7, loc, m_rim or m["chrome"], rot=rot, verts=20)
    p.cyl("rim_in", R - .06, w * .5, loc, m["dark"], rot=rot, verts=16)
    for i in range(spokes):
        a = math.tau * i / spokes
        p.tube("spoke", (x, y, z), (x + math.cos(a) * (R - .05), y, z + math.sin(a) * (R - .05)), .004, m["chrome"], verts=4)
    p.cyl("hub", .03, w + .03, loc, m["chrome"], rot=rot, verts=10)

def flag_br(p, loc, w=1.0, h=.7, face="-Y", t=.015):
    """Brazilian flag as a flat panel: green field, yellow rhombus, blue globe, white band."""
    m = mats(); x, y, z = loc
    p.box("flag", (w, t, h), loc, m["green"], bevel=.004)
    d = p.cyl("flag_rhombus", h * .44, t + .004, (x, y, z), m["yellow"], rot=(rad(90), 0, 0), verts=4); d.scale = (w / h * .72, 1.0, 1)
    p.cyl("flag_globe", h * .25, t + .008, (x, y, z), m["blue"], rot=(rad(90), 0, 0), verts=18)
    p.box("flag_band", (h * .46, t + .012, h * .05), (x, y, z + h * .03), m["white"], rot=(0, rad(-12), 0), bevel=0)

def cheap_crate(p, loc, w=.52, d=.36, h=.22, m=None):
    """Wooden feira crate, ~130 tris: corner posts, 2 slats per long side, end slats, bottom boards."""
    m = m or mats()["wood"]; x, y, z = loc; t = .016; post = .03
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box("crate_post", (post, post, h), (x + sx * (w / 2 - post / 2), y + sy * (d / 2 - post / 2), z + h / 2), m, bevel=0)
    for i in range(2):
        zz = z + h * (.28 + i * .45)
        for sy in (-1, 1):
            p.box("crate_slat", (w, t, h * .32), (x, y + sy * (d / 2 - t / 2), zz), m, bevel=0)
    for sx in (-1, 1):
        p.box("crate_end", (t, d - 2 * post, h * .5), (x + sx * (w / 2 - post - t / 2), y, z + h * .3), m, bevel=0)
        p.box("crate_endbar", (t, d - 2 * post, h * .18), (x + sx * (w / 2 - post - t / 2), y, z + h * .85), m, bevel=0)
    p.box("crate_bottom", (w - 2 * post, d - 2 * post, t), (x, y, z + t / 2), m, bevel=0)

def gift_box(p, loc, size, mb, mr, bow=True, rot=0.0):
    m = mats(); x, y, z = loc; w, d, h = size
    objs = [p.box("gift", (w, d, h), (x, y, z + h / 2), mb, bevel=.012, seg=2),
            p.box("gift_lid", (w + .03, d + .03, h * .22), (x, y, z + h - h * .11), mb, bevel=.01),
            p.box("ribbon_x", (w + .036, d * .14, h + .008), (x, y, z + h / 2), mr, bevel=0),
            p.box("ribbon_y", (w * .14, d + .036, h + .008), (x, y, z + h / 2), mr, bevel=0)]
    if bow:
        for a in (0, 90, 180, 270):
            objs.append(p.ball("bow", .05, (x + math.cos(rad(a)) * .045, y + math.sin(rad(a)) * .045, z + h + .035), mr, sub=1, scale=(1.3, .7, .7), rot=(0, 0, rad(a))))
        objs.append(p.ball("bow_knot", .025, (x, y, z + h + .03), mr, sub=1))
    for o in objs:
        o.matrix_world = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(rot, 4, 'Z') @ Matrix.Translation((-x, -y, 0)) @ o.matrix_world
    return objs

# ================================================================== 1. QUINTO DIA UTIL
def atm_kiosk(c):
    """Free-standing 24h ATM kiosk: 1.15 x 0.85 x 2.45 m, canopy with the 24 HORAS fascia, privacy side panels."""
    p = P(c); m = mats(); W_, D, H = 1.15, .85, 2.0
    yf = -D / 2
    p.box("plinth", (1.55, 1.15, .08), (0, -.05, .04), m["concrete"], bevel=.012, seg=2)
    p.box("plinth_edge", (1.57, .05, .085), (0, -.6, .042), m["yellow"], bevel=0)
    p.box("mat", (.9, .55, .012), (0, yf - .4, .086), m["rubber"], bevel=.004)
    body = p.box("body", (W_, D, H), (0, 0, .08 + H / 2), m["navy"], bevel=.035, seg=2)
    p.box("body_band", (W_ + .02, D + .02, .12), (0, 0, .25), m["teal"], bevel=.01)
    # lower safe door + vent + lock
    p.box("safe_door", (.92, .03, .72), (0, yf - .01, .62), m["steel"], bevel=.012)
    p.box("safe_lock", (.06, .02, .06), (.36, yf - .03, .62), m["dark"], bevel=.004)
    p.cyl("safe_key", .012, .02, (.36, yf - .035, .62), m["chrome"], rot=(rad(90), 0, 0), verts=8)
    for i in range(5):
        p.box("vent", (.3, .012, .012), (-.2, yf - .03, .40 + i * .04), m["dark"], bevel=0)
    # console: keypad shelf (sloped), screen panel (sloped)
    shelf = p.box("shelf", (.92, .34, .07), (0, yf - .09, 1.04), m["steel"], rot=(rad(-16), 0, 0), bevel=.012, seg=2)
    p.box("screen_panel", (.92, .06, .62), (0, yf - .02, 1.52), m["steel"], rot=(rad(-6), 0, 0), bevel=.012, seg=2)
    p.box("screen_bezel", (.64, .02, .44), (-.06, yf - .055, 1.56), m["ink"], rot=(rad(-6), 0, 0), bevel=.006)
    p.box("screen", (.58, .012, .38), (-.06, yf - .065, 1.56), m["screen"], rot=(rad(-6), 0, 0), bevel=0)
    p.txt("BEM-VINDO", .06, (-.06, yf - .073, 1.60), m["navy"], res=1, extrude=0)
    for i in range(4):   # side function keys
        for sx in (-.42, .30):
            p.box("fkey", (.06, .02, .04), (sx, yf - .06, 1.70 - i * .09), m["grey"], bevel=0)
    # keypad on the shelf: 4x3 + function column (keys sit on the sloped shelf)
    def on_shelf(x, u, dz=.0):
        base = Vector((x, yf - .09, 1.04)); R = Matrix.Rotation(rad(-16), 3, 'X')
        return base + R @ Vector((0, u, .035 + dz))
    for r in range(4):
        for col in range(3):
            loc = on_shelf(-.18 + col * .07, .10 - r * .06)
            p.box("key", (.055, .045, .022), loc, m["dark"] if (r, col) != (3, 1) else m["grey"], rot=(rad(-16), 0, 0), bevel=0)
    for i, kc in enumerate(("red", "yellow", "green", "white")):
        p.box("fkey2", (.07, .045, .022), on_shelf(.14, .10 - i * .06), m[kc], rot=(rad(-16), 0, 0), bevel=0)
    p.box("speaker", (.11, .02, .11), (.38, yf - .055, 1.76), m["dark"], bevel=0)
    for j in range(4):
        p.box("spk_slot", (.08, .008, .008), (.38, yf - .068, 1.72 + j * .028), m["grey"], bevel=0)
    # slots
    p.box("card_slot", (.12, .025, .04), (.36, yf - .105, 1.30), m["ink"], bevel=.004)
    p.box("card_led", (.12, .012, .01), (.36, yf - .115, 1.33), m["ledG"], bevel=0)
    p.box("cash_slot", (.42, .03, .07), (-.1, yf - .105, 1.30), m["ink"], bevel=.006)
    p.box("cash_lip", (.44, .035, .012), (-.1, yf - .11, 1.265), m["chrome"], bevel=0)
    p.box("receipt", (.16, .025, .03), (-.1, yf - .105, 1.37), m["ink"], bevel=.004)
    # header band with ATM label
    p.box("header", (W_ + .02, .06, .3), (0, yf - .02, 1.93), m["teal"], bevel=.012)
    p.txt("CAIXA ELETRÔNICO", .075, (0, yf - .056, 1.93), m["white"], res=1, extrude=0)
    # privacy side panels (steel frame + frosted glass)
    for sx in (-1, 1):
        px = sx * (W_ / 2 + .03)
        p.box("priv_frame", (.045, .62, 1.25), (px, yf - .22, 1.42), m["steel"], bevel=.01)
        p.box("priv_glass", (.02, .52, 1.1), (px, yf - .24, 1.44), m["glassL"], bevel=.004)
        p.box("priv_brace", (.045, .06, .5), (px, .08, 1.42), m["steel"], bevel=0)
    # canopy: roof, fascia, downlight, camera dome, sign on top
    p.box("canopy", (W_ + .5, D + .55, .13), (0, -.3, .08 + H + .07), m["navy"], bevel=.03, seg=2)
    p.box("canopy_cap", (W_ + .54, D + .59, .04), (0, -.3, .08 + H + .15), m["tealL"], bevel=.012)
    p.box("fascia", (W_ + .52, .07, .38), (0, -.3 - (D + .55) / 2 - .02, .08 + H + .09), m["yellow"], bevel=.012)
    p.txt("24 HORAS", .19, (0, -.3 - (D + .55) / 2 - .06, .08 + H + .09), m["navy"], res=2, extrude=.004)
    p.txt("ATM", .16, (-((W_ + .5) / 2 + .01), -.3, .08 + H + .07), m["white"], face="-X", res=1, extrude=0)
    p.box("downlight", (.9, .14, .025), (0, yf - .3, .08 + H), m["lamp"], bevel=0)
    p.ball("cam_dome", .065, (-.42, yf - .45, .08 + H), m["glass"], sub=2)
    p.cyl("cam_ring", .075, .02, (-.42, yf - .45, .08 + H + .005), m["dark"], verts=12)
    p.box("topsign", (.9, .18, .36), (0, .1, .08 + H + .35), m["red"], bevel=.03, seg=2)
    p.txt("SAQUE 24H", .13, (0, .0, .08 + H + .35), m["white"], res=1, extrude=0)
    p.box("topsign_light", (.6, .04, .03), (0, .0, .08 + H + .54), m["lamp"], bevel=0)
    return p.o

def queue_stanchions(c, lane=1.5, length=3.0, n=3):
    """Chrome posts with red retractable belts in a U (open towards +Y, the ATM side). 1.8 x 3.0 m."""
    p = P(c); m = mats()
    pts = []
    for sx in (-1, 1):
        col = [(sx * lane / 2, -length / 2 + i * length / (n - 1)) for i in range(n)]
        pts.append(col if sx < 0 else col[::-1])
    chain = pts[0][::-1] + pts[1][::-1]   # left column from +Y to -Y, then across the bottom, then right column up
    for (x, y) in chain:
        p.cyl("base", .17, .035, (x, y, .018), m["chrome"], verts=16, r2=.15)
        p.cyl("post", .028, .95, (x, y, .51), m["chrome"], verts=8)
        p.cyl("collar", .036, .04, (x, y, .06), m["chrome"], verts=8)
        p.cyl("head", .05, .11, (x, y, 1.02), m["chrome"], verts=10)
        p.cyl("top", .05, .035, (x, y, 1.09), m["chrome"], verts=10, r2=.028)
        p.box("belt_clip", (.03, .03, .05), (x, y, 1.0), m["dark"], bevel=0)
    for a, b in zip(chain[:-1], chain[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]; ln = math.hypot(dx, dy); ang = math.atan2(dy, dx)
        p.box("belt", (ln - .1, .014, .05), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, .985), m["red"], rot=(0, rad(1.5), ang), bevel=0)
    return p.o

@E.event
def v2_QuintoDiaUtil(c):
    E.diorama(c)
    put(atm_kiosk(c), x=2.5, y=4.9, z=.13)
    put(queue_stanchions(c), x=2.5, y=2.85, z=.13)
    for i, (who, dy, r) in enumerate([("Customer_07", 3.95, 180), ("Customer_06", 2.95, 180), ("Customer_09", 2.0, 180), ("Customer_08", .9, 170)]):
        E.actor(c, who, (2.45 + (.1 if i % 2 else -.1), dy), rad(r))
    E.actor(c, "Customer_06", (-2.6, 2.2), rad(60))
    E.actor(c, "Customer_09", (5.4, 1.4), rad(-40))

# ================================================================== 2. FEIRA DE RUA
def feira_stall(c, canvas="canvasR", goods=("orange", "red", "lime", "purple"), kinds=("ball", "tomato", "lime", "ball"), price=("R$ 5", "R$ 3")):
    """Feira stall 3.2 x 2.0 x 2.45 m: tubular frame, sloped striped canvas with scalloped valance, cloth table,
    4 crates of produce, 2 chalk price boards, hanging scale. Front (customers) at -Y."""
    p = P(c); m = mats(); w, d = 3.0, 2.0; zf, zb = 2.1, 2.42
    mc = m[canvas]
    for sx in (-1, 1):
        for sy, zz in ((-1, zf), (1, zb)):
            p.cyl("pole", .022, zz, (sx * w / 2, sy * d / 2, zz / 2), m["galv"], verts=8)
            p.cyl("foot", .045, .02, (sx * w / 2, sy * d / 2, .01), m["dark"], verts=8)
        p.tube("rail_side", (sx * w / 2, -d / 2, zf), (sx * w / 2, d / 2, zb), .018, m["galv"], verts=6)
        p.tube("brace", (sx * w / 2, -d / 2, 1.5), (sx * w / 2, d / 2, 1.5), .014, m["galv"], verts=5)
    p.tube("rail_f", (-w / 2, -d / 2, zf), (w / 2, -d / 2, zf), .018, m["galv"], verts=6)
    p.tube("rail_b", (-w / 2, d / 2, zb), (w / 2, d / 2, zb), .018, m["galv"], verts=6)
    p.tube("hang_bar", (-w / 2, -d / 2 + .02, 1.78), (w / 2, -d / 2 + .02, 1.78), .012, m["galv"], verts=5)
    slope = math.atan2(zb - zf, d)
    p.box("canvas", (w + .34, d + .36, .03), (0, 0, (zf + zb) / 2 + .03), mc, rot=(slope, 0, 0), bevel=.006)
    p.box("canvas_ridge", (w + .36, .06, .05), (0, d / 2 + .16, zb + .07), mc, bevel=.01)
    valance(p, [(-w / 2 - .17, -d / 2 - .18, zf + .035), (w / 2 + .17, -d / 2 - .18, zf + .035)], .3, .3, mc)
    valance(p, [(-w / 2 - .17, d / 2 + .18, zb + .035), (-w / 2 - .17, -d / 2 - .18, zf + .035)], .26, .3, mc)
    valance(p, [(w / 2 + .17, -d / 2 - .18, zf + .035), (w / 2 + .17, d / 2 + .18, zb + .035)], .26, .3, mc)
    # table: wooden top on two trestles, gingham cloth over the front, drape
    ty = -.35; td = 1.2
    p.box("table_top", (w, td, .045), (0, ty, .82), m["wood"], bevel=.006)
    for tx in (-1.1, 1.1):
        for sy in (-1, 1):
            p.box("trestle_leg", (.05, .06, .78), (tx, ty + sy * .38, .40), m["woodD"], rot=(rad(-18 * sy), 0, 0), bevel=0)
        p.box("trestle_bar", (.05, .7, .05), (tx, ty, .42), m["woodD"], bevel=0)
    p.box("cloth_top", (w + .04, .95, .012), (0, ty - .12, .848), m["gingham"], bevel=.004)
    p.box("cloth_drape", (w + .04, .012, .42), (0, ty - td / 2 - .004, .64), m["gingham"], bevel=.004)
    p.box("cloth_hem", (w + .06, .02, .03), (0, ty - td / 2 - .006, .43), m["red"], bevel=0)
    # crates with produce (front row) + 2 stacked spare crates behind
    for i in range(4):
        cx = -w / 2 + .45 + i * .70; cy = ty - .2
        cheap_crate(p, (cx, cy, .87))
        o = k.produce_fill("fruit", (cx, cy, .865 + .22), .50, .34, .2, m[goods[i % len(goods)]], kind=kinds[i % len(kinds)], r=.062, c=c, seed=i + 1, sub=1)
        p.o.append(o)
    cheap_crate(p, (1.0, ty + .36, .845))
    cheap_crate(p, (-1.0, ty + .36, .845), m=m["woodD"])
    o = k.produce_fill("fruit", (-1.0, ty + .36, .845 + .22), .50, .34, .2, m["yellow"], kind='ball', r=.06, c=c, seed=9, sub=1); p.o.append(o)
    # paper bags + a plastic bag roll on the table
    for i in range(3):
        p.box("paperbag", (.12, .07, .25), (.05 + i * .13, ty + .4, .97), m["cardboard"] if "cardboard" in m else m["brown"], bevel=.006)
    p.cyl("bagroll", .05, .22, (-.45, ty + .42, .9), m["white"], rot=(0, rad(90), 0), verts=10)
    # chalk price boards hanging from the hang bar
    for bx, s1, s2 in ((.95, price[0], "KG"), (-.35, price[1], "DZ")):
        for sx in (-1, 1):
            p.tube("string", (bx + sx * .17, -d / 2 + .02, 1.78), (bx + sx * .17, -d / 2 - .02, 1.52), .004, m["white"], verts=4)
        p.box("board_frame", (.44, .025, .34), (bx, -d / 2 - .02, 1.35), m["woodD"], bevel=.006)
        p.box("board", (.38, .014, .28), (bx, -d / 2 - .035, 1.35), m["chalk"], bevel=0)
        p.txt(s1, .12, (bx, -d / 2 - .045, 1.39), m["white"], res=1, extrude=0)
        p.txt(s2, .055, (bx, -d / 2 - .045, 1.28), m["yellow"], res=1, extrude=0)
    # hanging scale (left): hook, dial body, pan on chains
    sx_ = -1.25; sy_ = -d / 2 - .04
    p.tube("scale_hook", (sx_, sy_ + .06, 1.78), (sx_, sy_, 1.66), .006, m["dark"], verts=5)
    p.cyl("scale_body", .12, .07, (sx_, sy_, 1.52), m["white"], rot=(rad(90), 0, 0), verts=16, bevel=.008)
    p.cyl("scale_dial", .095, .012, (sx_, sy_ - .04, 1.52), m["paper"], rot=(rad(90), 0, 0), verts=16)
    p.box("scale_needle", (.012, .006, .08), (sx_, sy_ - .05, 1.55), m["red"], rot=(0, rad(-35), 0), bevel=0)
    p.cyl("scale_pin", .012, .01, (sx_, sy_ - .05, 1.52), m["dark"], rot=(rad(90), 0, 0), verts=6)
    p.box("scale_cap", (.08, .07, .05), (sx_, sy_, 1.65), m["dark"], bevel=.006)
    for a in (90, 210, 330):
        p.tube("chain", (sx_, sy_, 1.44), (sx_ + math.cos(rad(a)) * .13, sy_ + math.sin(rad(a)) * .13, 1.12), .003, m["dark"], verts=4)
    p.cyl("scale_pan", .15, .025, (sx_, sy_, 1.10), m["chrome"], verts=16, bevel=.006, r2=.13)
    for i in range(3):
        p.ball("pan_fruit", .05, (sx_ + (i - 1) * .07, sy_ + (i % 2) * .05, 1.16), m["orange"], sub=1)
    return p.o

def feira_banner(c):
    """FEIRA LIVRE banner (3.2 x 0.6 m yellow canvas) tied between two wooden posts on concrete feet. 4.0 x 0.5 x 3.3 m."""
    p = P(c); m = mats(); px = 1.85
    for sx in (-1, 1):
        p.box("post", (.08, .08, 3.2), (sx * px, 0, 1.6), m["woodD"], bevel=.008)
        p.box("post_cap", (.1, .1, .03), (sx * px, 0, 3.21), m["dark"], bevel=.004)
        p.cyl("foot", .22, .14, (sx * px, 0, .07), m["concreteD"], verts=14, r2=.19)
        p.box("foot_band", (.44, .44, .03), (sx * px, 0, .015), m["dark"], bevel=0)
    bw, bh, bz = 3.2, .62, 2.7
    p.box("banner", (bw, .02, bh), (0, 0, bz), m["yellow"], bevel=.006)
    p.box("banner_edge", (bw + .02, .024, .05), (0, 0, bz + bh / 2 - .025), m["red"], bevel=0)
    p.box("banner_edge2", (bw + .02, .024, .05), (0, 0, bz - bh / 2 + .025), m["red"], bevel=0)
    p.txt("FEIRA LIVRE", .33, (0, -.015, bz + .07), m["red"], res=2, extrude=.004)
    p.txt("FRUTAS  VERDURAS  LEGUMES", .09, (0, -.015, bz - .2), m["navy"], res=1, extrude=0)
    for sx in (-1, 1):
        for zz in (bz + bh / 2 - .06, bz - bh / 2 + .06):
            p.cyl("grommet", .022, .03, (sx * (bw / 2 - .07), 0, zz), m["chrome"], rot=(rad(90), 0, 0), verts=8)
            p.tube("tie", (sx * (bw / 2 - .07), 0, zz), (sx * px, 0, zz + .02), .006, m["white"], verts=4)
    # small pennant string on top between the posts
    cols = ("green", "yellow", "red", "white")
    for i in range(12):
        t = (i + .5) / 12; x = -px + 2 * px * t; z = 3.15 - .18 * 4 * t * (1 - t)
        p.mesh("pennant", [(x - .08, 0, z), (x + .08, 0, z), (x, 0, z - .2)], [(0, 1, 2)], [m[cols[i % 4]]], solid=.01)
    for i in range(12):
        t0, t1 = i / 12, (i + 1) / 12
        p.tube("rope", (-px + 2 * px * t0, 0, 3.15 - .18 * 4 * t0 * (1 - t0)), (-px + 2 * px * t1, 0, 3.15 - .18 * 4 * t1 * (1 - t1)), .005, m["white"], verts=4)
    return p.o

def street_cone(p, loc, h=.7):
    m = mats(); x, y, z = loc
    p.box("cone_base", (.4, .4, .04), (x, y, z + .02), m["dark"], bevel=.01)
    p.cyl("cone", .16, h, (x, y, z + .04 + h / 2), m["orange"], r2=.035, verts=14)
    p.cyl("cone_band", .115, .1, (x, y, z + .04 + h * .55), m["white"], r2=.09, verts=14)

@E.event
def v2_FeiraDeRua(c):
    E.diorama(c)
    put(feira_stall(c, "canvasR", ("orange", "red", "lime", "purple"), ("ball", "tomato", "lime", "ball")), x=-4.1, y=-3.55)
    put(feira_stall(c, "canvasB", ("yellow", "green", "red", "orange"), ("ball", "ball", "tomato", "ball"), ("R$ 4", "R$ 6")), x=0, y=-3.55)
    put(feira_stall(c, "canvasG", ("lime", "orange", "purple", "red"), ("lime", "ball", "ball", "tomato"), ("R$ 2", "R$ 8")), x=4.1, y=-3.55)
    put(feira_banner(c), x=.2, y=-.55, z=.13)
    p = P(c)
    for cx in (-6.5, 6.5):
        for cy in (-2.2, -3.6, -5.0): street_cone(p, (cx, cy, 0))
    for (px, py, who, r) in [(-4.6, -5.0, "Customer_06", 180), (-.5, -5.1, "Customer_08", 170), (4.6, -5.0, "Customer_07", 190),
                             (-3.2, -2.1, "Customer_09", 0), (.6, -2.0, "Customer_07", 10), (4.0, -2.1, "Customer_06", -10), (-4.2, 2.4, "Customer_08", 220)]:
        E.actor(c, who, (px, py, .0 if py < -1.4 else .13), rad(r))

# ================================================================== 3. ONDA DE CALOR
def street_thermometer(c):
    """Street clock-thermometer: steel pole with a bolted flange, double-sided LED case reading 38°C / 14:35. 1.5 x 0.3 x 4.2 m."""
    p = P(c); m = mats()
    p.cyl("flange", .2, .03, (0, 0, .015), m["dark"], verts=16, bevel=.006)
    for a in range(4):
        p.cyl("bolt", .018, .02, (math.cos(rad(45 + a * 90)) * .15, math.sin(rad(45 + a * 90)) * .15, .04), m["chrome"], verts=6)
    p.cyl("pole", .07, 3.3, (0, 0, 1.65), m["steel"], verts=14)
    p.cyl("pole_collar", .085, .12, (0, 0, .35), m["dark"], verts=14)
    p.cyl("pole_collar2", .085, .08, (0, 0, 3.3), m["dark"], verts=14)
    cz = 3.72; cw, cd, ch = 1.5, .28, .92
    p.box("case", (cw, cd, ch), (0, 0, cz), m["dark"], bevel=.05, seg=2)
    p.box("case_trim", (cw + .03, cd + .03, .06), (0, 0, cz + ch / 2 - .03), m["teal"], bevel=.012)
    p.box("case_trim2", (cw + .03, cd + .03, .06), (0, 0, cz - ch / 2 + .03), m["teal"], bevel=.012)
    p.box("case_cap", (cw * .5, cd * .6, .06), (0, 0, cz + ch / 2 + .04), m["grey"], bevel=.012)
    for s, face in ((-1, "-Y"), (1, "+Y")):
        yy = s * (cd / 2 + .006)
        p.box("led_panel", (cw - .14, .012, ch - .14), (0, yy, cz), m["ledOff"], bevel=0)
        p.txt("38°C", .42, (0, yy + s * .012, cz + .1), m["ledHot"], face=face, res=2 if s < 0 else 1, extrude=.005 if s < 0 else 0)
        p.txt("14:35", .17, (0, yy + s * .012, cz - .26), m["ledO"], face=face, res=1, extrude=0)
        # thermometer glyph on the right
        gx = .52 * (1 if s < 0 else -1)
        p.box("glyph_tube", (.04, .01, .5), (gx, yy + s * .012, cz + .02), m["white"], bevel=0)
        p.box("glyph_mercury", (.022, .014, .34), (gx, yy + s * .016, cz - .04), m["ledR"], bevel=0)
        p.cyl("glyph_bulb", .05, .014, (gx, yy + s * .016, cz - .26), m["ledR"], rot=(rad(90), 0, 0), verts=12)
    p.box("brand_band", (cw + .03, cd + .03, .14), (0, 0, cz - ch / 2 - .1), m["teal"], bevel=.012)
    p.txt("TEMPERATURA", .07, (0, -(cd + .03) / 2 - .006, cz - ch / 2 - .1), m["white"], res=1, extrude=0)
    p.cyl("sun_disc", .09, .02, (0, 0, cz + ch / 2 + .16), m["yellow"], rot=(rad(90), 0, 0), verts=12)
    for a in range(8):
        p.box("sun_ray", (.07, .015, .02), (math.cos(rad(a * 45)) * .14, 0, cz + ch / 2 + .16 + math.sin(rad(a * 45)) * .14), m["yellow"], rot=(0, rad(-a * 45), 0), bevel=0)
    return p.o

def icecream_cart(c):
    """Brazilian picolé cart: insulated box on two spoked wheels, push handle at +Y... no: handle at -X, parasol. 1.9 x 1.2 x 2.4 m."""
    p = P(c); m = mats(); bw, bd, bh = 1.15, .62, .72; z0 = .34
    p.box("box", (bw, bd, bh), (0, 0, z0 + bh / 2), m["plastic"], bevel=.045, seg=2)
    p.box("box_band", (bw + .02, bd + .02, .2), (0, 0, z0 + .32), m["pink"], bevel=.01)
    p.box("box_band2", (bw + .02, bd + .02, .05), (0, 0, z0 + .12), m["sky"], bevel=.006)
    p.box("lid", (bw + .05, bd + .05, .06), (0, 0, z0 + bh + .03), m["sky"], bevel=.015, seg=2)
    p.box("lid_split", (.012, bd + .06, .064), (0, 0, z0 + bh + .03), m["dark"], bevel=0)
    for sx in (-1, 1):
        p.box("lid_handle", (.14, .03, .025), (sx * .3, -bd / 2 - .04, z0 + bh + .07), m["chrome"], bevel=.006)
        p.box("hinge", (.1, .03, .02), (sx * .35, bd / 2 + .02, z0 + bh + .03), m["chrome"], bevel=0)
    p.txt("SORVETE", .13, (.05, -bd / 2 - .016, z0 + .33), m["white"], res=2, extrude=.004)
    p.txt("PICOLÉ  R$ 3", .055, (.05, -bd / 2 - .016, z0 + .16), m["navy"], res=1, extrude=0)
    for i, (col, dz) in enumerate((("yellow", 0), ("red", .03), ("lime", -.02))):   # popsicle decals on the front
        px = -.42 + i * .13
        p.box("pop", (.07, .012, .14), (px, -bd / 2 - .012, z0 + .55 + dz), m[col], bevel=.015, seg=1)
        p.box("pop_stick", (.02, .012, .07), (px, -bd / 2 - .01, z0 + .45 + dz), m["cream"], bevel=0)
    for i, col in enumerate(("pink", "yellow", "lime", "sky")):   # popsicles on the lid
        p.box("pop_lid", (.07, .028, .14), (-.3 + i * .14, .12, z0 + bh + .12), m[col], rot=(0, rad(10 * (i - 1.5)), 0), bevel=.015, seg=1)
        p.box("pop_lid_stick", (.02, .02, .06), (-.3 + i * .14, .12, z0 + bh + .03), m["cream"], rot=(0, rad(10 * (i - 1.5)), 0), bevel=0)
    # chassis: axle, 2 spoked wheels at the +X end, foldable leg at -X, push handle at -X
    p.cyl("axle", .015, bd + .2, (.3, 0, .3), m["dark"], rot=(rad(90), 0, 0), verts=6)
    for sy in (-1, 1):
        spoked_wheel(p, (.3, sy * (bd / 2 + .06), .3), R=.3, w=.04)
        p.box("mudguard", (.42, .06, .02), (.3, sy * (bd / 2 + .06), .62), m["pink"], bevel=.006)
    p.box("leg", (.05, .05, .32), (-.45, 0, .18), m["dark"], bevel=0)
    p.box("leg_foot", (.14, .14, .02), (-.45, 0, .01), m["rubber"], bevel=.004)
    for sy in (-1, 1):
        p.tube("handle_arm", (-bw / 2 + .05, sy * .22, z0 + .5), (-bw / 2 - .4, sy * .22, z0 + .62), .016, m["chrome"], verts=8)
    p.cyl("handle_bar", .018, .5, (-bw / 2 - .4, 0, z0 + .62), m["chrome"], rot=(rad(90), 0, 0), verts=8)
    for sy in (-1, 1):
        p.cyl("grip", .024, .12, (-bw / 2 - .4, sy * .18, z0 + .62), m["rubber"], rot=(rad(90), 0, 0), verts=8)
    p.ball("bell", .035, (-bw / 2 - .3, -.22, z0 + .66), m["brass"], sub=2)
    p.box("bag", (.18, .1, .22), (-bw / 2 - .25, .3, z0 + .42), m["cream"], bevel=.015)
    parasol(p, (.1, .08, z0 + bh), h=1.35, R=.95, ma=m["yellow"], mb=m["pink"], mpole=m["white"], drop=.26, base=False, pole_r=.016)
    p.cyl("parasol_clamp", .035, .16, (.1, .08, z0 + bh + .02), m["dark"], verts=8)
    return p.o

def sun_umbrella_bench(c):
    """Park bench (slatted wood, cast-iron frame) under a big striped sun umbrella. 2.4 x 2.4 x 2.5 m."""
    p = P(c); m = mats(); bw = 1.8
    for lx in (-.75, .75):
        p.box("leg_f", (.05, .06, .44), (lx, -.2, .22), m["dark"], bevel=.006)
        p.box("leg_b", (.05, .06, .44), (lx, .2, .22), m["dark"], bevel=.006)
        p.box("leg_foot", (.06, .52, .03), (lx, 0, .015), m["dark"], bevel=.004)
        p.box("seat_rail", (.05, .48, .04), (lx, 0, .45), m["dark"], bevel=.004)
        p.box("back_post", (.05, .05, .5), (lx, .24, .70), m["dark"], rot=(rad(-10), 0, 0), bevel=.004)
        p.box("armrest", (.05, .5, .035), (lx, .0, .70), m["dark"], bevel=.006)
        p.box("arm_post", (.04, .04, .22), (lx, -.2, .58), m["dark"], bevel=0)
    for i in range(4):
        p.box("seat_slat", (bw, .09, .035), (0, -.18 + i * .12, .48), m["wood"], bevel=.006)
    for i in range(3):
        p.box("back_slat", (bw, .035, .09), (0, .27 + i * .022, .62 + i * .12), m["wood"], rot=(rad(-10), 0, 0), bevel=.006)
    parasol(p, (0, .55, 0), h=2.35, R=1.2, ma=m["orange"], mb=m["white"], mpole=m["steel"], drop=.36)
    return p.o

@E.event
def v2_OndaDeCalor(c):
    E.diorama(c)
    put(street_thermometer(c), x=-4.0, y=-.45, z=.13)
    put(icecream_cart(c), x=.9, y=.9, z=.13, rot=rad(-15))
    put(sun_umbrella_bench(c), x=4.3, y=2.2, z=.13)
    for (px, py, who, r) in [(2.0, .2, "Customer_09", 130), (-.4, .1, "Customer_06", 230), (3.9, 1.9, "Customer_08", 0),
                             (-2.4, 2.8, "Customer_07", 40), (-5.6, 2.4, "Customer_08", -60)]:
        E.actor(c, who, (px, py), rad(r))

# ================================================================== 4. SORTEIO NA PORTA
HUB = (0, -.18, 1.75)   # where Sorteio_WheelDisc sits on Sorteio_WheelStand (prop-local, Blender axes)
def wheel_stand(c):
    """Wooden A-stand with the GIRE E GANHE sign and the pointer; the wheel disc is a separate prop at HUB. 1.3 x 0.9 x 2.9 m."""
    p = P(c); m = mats(); hx, hy, hz = HUB
    p.box("foot", (1.3, .9, .07), (0, 0, .035), m["woodD"], bevel=.012, seg=2)
    p.box("foot_trim", (1.32, .92, .025), (0, 0, .012), m["dark"], bevel=0)
    for sx in (-1, 1):
        p.box("upright", (.09, .36, 2.75), (sx * .55, .1, 1.395), m["wood"], bevel=.01)
        p.box("upright_cap", (.11, .4, .04), (sx * .55, .1, 2.79), m["red"], bevel=.006)
        p.box("brace", (.05, .5, .05), (sx * .55, -.1, .55), m["woodD"], rot=(rad(30), 0, 0), bevel=0)
        p.cyl("knob", .035, .03, (sx * .55, -.085, 1.3), m["gold"], rot=(rad(90), 0, 0), verts=10)
    p.box("crossbar", (1.2, .1, .18), (0, .05, hz), m["wood"], bevel=.01)
    p.box("crossbar_lo", (1.2, .1, .1), (0, .05, .9), m["wood"], bevel=.01)
    p.cyl("axle_boss", .09, .06, (hx, hy + .14, hz), m["dark"], rot=(rad(90), 0, 0), verts=14)
    p.cyl("axle", .03, .34, (hx, hy + .04, hz), m["chrome"], rot=(rad(90), 0, 0), verts=10)
    # sign on top with bulb border
    sz_ = 2.97
    p.box("sign", (1.5, .08, .42), (0, .05, sz_), m["red"], bevel=.025, seg=2)
    p.box("sign_edge", (1.54, .06, .46), (0, .07, sz_), m["yellow"], bevel=.012)
    p.txt("GIRE E GANHE", .19, (0, .005, sz_), m["yellow"], res=2, extrude=.005)
    for i in range(9):
        for zz in (sz_ - .22, sz_ + .22):
            p.ball("bulb", .028, (-.6 + i * .15, 0, zz), m["lamp"], sub=1)
    # pointer (flapper) hanging from the sign into the peg ring
    p.box("pointer_bracket", (.08, .08, .1), (hx, hy - .02, sz_ - .26), m["dark"], bevel=.004)
    p.mesh("pointer", [(-.075, 0, 0), (.075, 0, 0), (0, 0, -.28)], [(0, 1, 2)], [m["red"]], loc=(hx, hy - .06, sz_ - .27), solid=.025)
    p.cyl("pointer_pin", .016, .05, (hx, hy - .06, sz_ - .27), m["chrome"], rot=(rad(90), 0, 0), verts=6)
    # prize shelf at the bottom front with tickets
    p.box("shelf", (1.0, .3, .04), (0, -.35, .6), m["wood"], bevel=.008)
    p.box("shelf_lip", (1.0, .03, .06), (0, -.5, .63), m["woodD"], bevel=0)
    p.box("tickets", (.3, .2, .06), (-.25, -.35, .65), m["paper"], bevel=.004)
    p.box("tickets_band", (.32, .05, .064), (-.25, -.35, .65), m["red"], bevel=0)
    p.box("urn", (.3, .25, .3), (.25, -.35, .77), m["glassL"], bevel=.012)
    p.box("urn_lid", (.32, .27, .03), (.25, -.35, .93), m["teal"], bevel=.006)
    return p.o

def wheel_disc(c):
    """8-colour prize wheel, origin at the hub, plane XZ, face -Y. Spins around its Y axis (Unity: local Z). 1.72 x 0.14 x 1.72 m."""
    p = P(c); m = mats(); R = .8
    cols = ["red", "yellow", "blue", "green", "orange", "purple", "pink", "teal"]
    verts = [(0, 0, 0)]; faces = []; midx = []; ring = []
    for i in range(8 * 6):
        a = math.tau * i / 48; ring.append(len(verts)); verts.append((math.cos(a) * R, 0, math.sin(a) * R))
    for i in range(48):
        faces.append((0, ring[i], ring[(i + 1) % 48])); midx.append(i // 6)
    p.mesh("wheel_face", verts, faces, [m[cn] for cn in cols], solid=.06, midx=midx, offset=0)
    bpy.ops.mesh.primitive_torus_add(major_radius=R + .02, minor_radius=.04, major_segments=32, minor_segments=6, location=(0, 0, 0), rotation=(rad(90), 0, 0))
    rim = bpy.context.active_object; rim.name = "wheel_rim"; k.link(rim, c); k.finish(rim, m["gold"], bevel=0); p.o.append(rim)
    for i in range(16):
        a = math.tau * i / 16 + math.tau / 32
        p.cyl("peg", .028, .09, (math.cos(a) * (R - .06), -.05, math.sin(a) * (R - .06)), m["white"], rot=(rad(90), 0, 0), verts=6)
    p.cyl("hub", .13, .05, (0, -.045, 0), m["white"], rot=(rad(90), 0, 0), verts=16)
    p.cyl("hub_ring", .15, .025, (0, -.04, 0), m["gold"], rot=(rad(90), 0, 0), verts=16)
    p.ball("hub_cap", .06, (0, -.08, 0), m["red"], sub=2)
    for i in range(8):   # divider lines + prize labels, radial
        a = math.tau * i / 8
        p.box("divider", (R - .1, .01, .012), (math.cos(a) * R / 2, -.034, math.sin(a) * R / 2), m["white"], rot=(0, -a, 0), bevel=0)
    labels = ["R$ 10", "10%", "BRINDE", "VALE", "R$ 5", "20%", "GRÁTIS", "5%"]
    for i, s in enumerate(labels):
        a = math.tau * (i + .5) / 8
        o = p.txt(s, .11, (math.cos(a) * .5, -.036, math.sin(a) * .5), m["white"], res=1, extrude=0, rot=(rad(90), -a, 0))
    return p.o

def balloon_arch(c, width=2.9, height=3.2):
    """Arch of 4-balloon clusters framing the market door, with two weighted bases. 3.3 x 0.7 x 3.2 m."""
    p = P(c); m = mats(); rnd = random.Random(4)
    cols = ["red", "yellow", "white", "teal", "blue"]
    n = 12; r = .19; hw = width / 2 - .25; htop = height - .45 - r
    for i in range(n):
        a = math.pi * (1 - i / (n - 1))
        cx, cz = hw * math.cos(a), .45 + htop * math.sin(a)
        nv = Vector((htop * math.cos(a), 0, hw * math.sin(a))).normalized()   # outward normal of the ellipse
        for j in range(3):
            b = math.tau * j / 3 + i * .7 - rad(90)
            off = nv * (math.cos(b) * r * 1.05) + Vector((0, math.sin(b) * r * 1.1, 0))
            col = cols[(i + j) % len(cols)]
            p.ball("balloon", r * rnd.uniform(.92, 1.05), (cx + off.x, off.y, cz + off.z), m[col], sub=2, scale=(1, 1, 1.15),
                   rot=(rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), rnd.uniform(0, 6)))
    for sx in (-1, 1):
        p.box("weight", (.42, .42, .3), (sx * hw, 0, .15), m["white"], bevel=.02, seg=2)
        p.box("weight_ribbon", (.44, .08, .31), (sx * hw, 0, .15), m["red"], bevel=0)
        p.box("weight_ribbon2", (.08, .44, .31), (sx * hw, 0, .15), m["red"], bevel=0)
    return p.o

def gift_boxes(c):
    """Pile of wrapped gifts (5 boxes, ribbons, bows). 1.1 x 0.9 x 0.9 m."""
    p = P(c); m = mats()
    gift_box(p, (-.25, .05, 0), (.5, .42, .36), m["red"], m["gold"], rot=rad(5))
    gift_box(p, (.3, -.1, 0), (.42, .36, .3), m["blue"], m["yellow"], rot=rad(-12))
    gift_box(p, (.15, .32, 0), (.34, .3, .26), m["yellow"], m["red"], rot=rad(20))
    gift_box(p, (-.1, .05, .37), (.34, .28, .24), m["teal"], m["white"], rot=rad(-8))
    gift_box(p, (.28, .1, .31), (.22, .22, .2), m["pink"], m["white"], rot=rad(30))
    return p.o

@E.event
def v2_SorteioNaPorta(c):
    E.diorama(c)
    put(balloon_arch(c), x=0, y=4.7, z=.13)
    sx, sy = 2.6, 3.7
    put(wheel_stand(c), x=sx, y=sy, z=.13)
    put(wheel_disc(c), x=sx + HUB[0], y=sy + HUB[1], z=.13 + HUB[2])
    put(gift_boxes(c), x=3.9, y=3.4, z=.13, rot=rad(15))
    put(gift_boxes(c), x=-2.5, y=4.2, z=.13, rot=rad(-70))
    E.actor(c, "Customer_07", (2.5, 2.35), rad(170)); E.actor(c, "Customer_08", (1.5, 2.2), rad(150))
    E.actor(c, "Customer_09", (-.6, 3.2), rad(200)); E.actor(c, "Customer_06", (3.9, 2.2), rad(140))

# ================================================================== 5. DIA DE JOGO DO BRASIL
def truss_column(p, x, y, h, s=.3, m=None, faces=("-Y", "+X", "-X")):
    """Square aluminium truss column (4 chords + zigzag bracing on the visible faces)."""
    m = m or mats()["steel"]
    cs = [(x - s / 2, y - s / 2), (x + s / 2, y - s / 2), (x + s / 2, y + s / 2), (x - s / 2, y + s / 2)]
    for cx, cy in cs:
        p.cyl("chord", .024, h, (cx, cy, h / 2), m, verts=6)
    pairs = {"-Y": (cs[0], cs[1]), "+Y": (cs[3], cs[2]), "+X": (cs[1], cs[2]), "-X": (cs[0], cs[3])}
    nseg = max(2, int(h / .45))
    for f in faces:
        a, b = pairs[f]
        for i in range(nseg):
            z0, z1 = h * i / nseg, h * (i + 1) / nseg
            (ax, ay), (bx, by) = (a, b) if i % 2 == 0 else (b, a)
            p.tube("brace", (ax, ay, z0), (bx, by, z1), .012, m, verts=4)
    for zz in (0.02, h - .02):
        p.box("truss_plate", (s + .08, s + .08, .025), (x, y, zz), mats()["dark"], bevel=.004)

def truss_beam(p, x0, x1, y, z, s=.3, m=None):
    m = m or mats()["steel"]
    for dy in (-s / 2, s / 2):
        for dz in (-s / 2, s / 2):
            p.tube("chord", (x0, y + dy, z + dz), (x1, y + dy, z + dz), .024, m, verts=6)
    nseg = max(2, int((x1 - x0) / .45))
    for i in range(nseg):
        xa, xb = x0 + (x1 - x0) * i / nseg, x0 + (x1 - x0) * (i + 1) / nseg
        za, zb = (z - s / 2, z + s / 2) if i % 2 == 0 else (z + s / 2, z - s / 2)
        p.tube("brace", (xa, y - s / 2, za), (xb, y - s / 2, zb), .012, m, verts=4)
        ya, yb = (y - s / 2, y + s / 2) if i % 2 == 0 else (y + s / 2, y - s / 2)
        p.tube("brace", (xa, ya, z - s / 2), (xb, yb, z - s / 2), .012, m, verts=4)

def big_screen(c):
    """LED screen (3.6 x 2.1 m) on an aluminium truss goal-post, two speakers, ballast blocks. 4.9 x 1.0 x 4.6 m."""
    p = P(c); m = mats()
    XM["alu"] = XM.get("alu") or k.mat("EV_Alu", (.80, .82, .84, 1), rough=.35, var=.05, scale=8, metallic=.6)
    cx = 2.1; H = 4.2; s = .3
    for sx in (-1, 1):
        truss_column(p, sx * cx, 0, H, s, m=XM["alu"], faces=("-Y", "+X" if sx > 0 else "-X"))
        p.box("ballast", (.7, .7, .3), (sx * cx, 0, .15), m["concreteD"], bevel=.02, seg=1)
        p.box("ballast_stripe", (.72, .72, .06), (sx * cx, 0, .27), m["hazard"], bevel=0)
    truss_beam(p, -cx - s / 2, cx + s / 2, 0, H + s / 2 + .02, s, m=XM["alu"])
    sz = 2.75; sw, sh = 3.6, 2.1
    p.box("screen_frame", (sw, .22, sh), (0, -.05, sz), m["dark"], bevel=.03, seg=2)
    p.box("screen_frame_trim", (sw + .04, .1, sh + .04), (0, .02, sz), m["grey"], bevel=.012)
    for sx in (-1, 1):   # mounting arms to the truss
        for dz in (-.6, .6):
            p.box("mount", (.3, .08, .08), (sx * (sw / 2 + .12), 0, sz + dz), m["dark"], bevel=0)
    # the pitch
    y = -.165
    p.box("screen", (sw - .18, .02, sh - .18), (0, y, sz), m["pitch"], bevel=0)
    pw, ph = sw - .4, sh - .62; pz = sz - .14
    for i in range(6):
        if i % 2: p.box("mow", (pw / 6, .012, ph), (-pw / 2 + pw / 12 + i * pw / 6, y - .008, pz), m["pitchD"], bevel=0)
    lw = .025
    p.box("line_t", (pw, .014, lw), (0, y - .012, pz + ph / 2), m["white"], bevel=0)
    p.box("line_b", (pw, .014, lw), (0, y - .012, pz - ph / 2), m["white"], bevel=0)
    p.box("line_l", (lw, .014, ph), (-pw / 2, y - .012, pz), m["white"], bevel=0)
    p.box("line_r", (lw, .014, ph), (pw / 2, y - .012, pz), m["white"], bevel=0)
    p.box("line_m", (lw, .014, ph), (0, y - .012, pz), m["white"], bevel=0)
    bpy.ops.mesh.primitive_torus_add(major_radius=.2, minor_radius=.012, major_segments=20, minor_segments=4, location=(0, y - .012, pz), rotation=(rad(90), 0, 0))
    t = bpy.context.active_object; t.name = "circle"; k.link(t, c); k.finish(t, m["white"], bevel=0); p.o.append(t)
    for sx in (-1, 1):
        p.box("box_l", (lw, .014, .6), (sx * (pw / 2 - .4), y - .012, pz), m["white"], bevel=0)
        p.box("box_t", (.4, .014, lw), (sx * (pw / 2 - .2), y - .012, pz + .3), m["white"], bevel=0)
        p.box("box_b", (.4, .014, lw), (sx * (pw / 2 - .2), y - .012, pz - .3), m["white"], bevel=0)
        p.box("goal", (.04, .03, .25), (sx * (pw / 2 + .02), y - .012, pz), m["white"], bevel=0)
    rnd = random.Random(7)
    for i in range(10):
        px, pzz = rnd.uniform(-pw / 2 + .2, pw / 2 - .2), rnd.uniform(-ph / 2 + .12, ph / 2 - .12)
        col = m["yellow"] if i < 5 else m["white"]
        p.box("player", (.045, .02, .09), (px, y - .02, pz + pzz), col, bevel=0)
        p.box("player_shorts", (.045, .022, .03), (px, y - .02, pz + pzz - .045), m["blue"] if i < 5 else m["dark"], bevel=0)
    p.ball("ball", .018, (.35, y - .022, pz + .1), m["white"], sub=1)
    # score bar
    p.box("scorebar", (1.5, .025, .26), (0, y - .012, sz + sh / 2 - .25), m["navy"], bevel=.006)
    p.txt("BRA  1 x 0", .16, (0, y - .03, sz + sh / 2 - .25), m["yellow"], res=1, extrude=0)
    p.box("live", (.4, .025, .12), (-sw / 2 + .45, y - .012, sz + sh / 2 - .22), m["red"], bevel=.006)
    p.txt("AO VIVO", .07, (-sw / 2 + .45, y - .03, sz + sh / 2 - .22), m["white"], res=1, extrude=0)
    p.box("clock", (.5, .025, .12), (sw / 2 - .5, y - .012, sz + sh / 2 - .22), m["dark"], bevel=.006)
    p.txt("2T  78'", .07, (sw / 2 - .5, y - .03, sz + sh / 2 - .22), m["ledG"], res=1, extrude=0)
    # speakers hanging from the beam
    for sx in (-1, 1):
        x = sx * (cx + .0); z = H - .55
        p.tube("spk_chain", (x, 0, H), (x, 0, z + .32), .008, m["dark"], verts=4)
        p.box("speaker", (.42, .4, .62), (x, -.02, z), m["dark"], bevel=.025, seg=2)
        p.box("spk_grille", (.36, .015, .54), (x, -.225, z), m["grey"], bevel=.006)
        p.cyl("woofer", .13, .02, (x, -.235, z - .1), m["ink"], rot=(rad(90), 0, 0), verts=14)
        p.cyl("tweeter", .05, .02, (x, -.235, z + .18), m["ink"], rot=(rad(90), 0, 0), verts=10)
    # cables + banner on the truss
    p.box("banner", (2.0, .03, .3), (0, -.17, H + .5), m["green"], bevel=.006)
    p.txt("VAI BRASIL!", .16, (0, -.19, H + .5), m["yellow"], res=2, extrude=.004)
    return p.o

def bunting(c, length=12.0, n=32, sag=.45, cols=("green", "yellow", "green", "yellow", "blue", "white")):
    """Pennant bunting, origin at the left anchor, runs along +X with a slight sag; the game scales X to the span."""
    p = P(c); m = mats()
    pts = [Vector((length * i / n, 0, -sag * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]
    for i in range(n):
        p.tube("rope", pts[i], pts[i + 1], .007, m["white"], verts=4)
        a, b = pts[i], pts[i + 1]; mid = (a + b) / 2; d = b - a; ang = math.atan2(d.z, d.x)
        w, h = .26, .36
        base_l = mid - d.normalized() * w / 2; base_r = mid + d.normalized() * w / 2
        tip = mid + Vector((0, 0, -h))
        p.mesh("pennant", [tuple(base_l - Vector((0, 0, .01))), tuple(base_r - Vector((0, 0, .01))), tuple(tip)], [(0, 1, 2)], [m[cols[i % len(cols)]]], solid=.008)
    return p.o

def flag_pole(c):
    """4 m steel flagpole with flange, cleat, finial and a 1.0 x 0.7 m Brazilian flag. 1.2 x 0.4 x 4.2 m."""
    p = P(c); m = mats()
    p.cyl("flange", .17, .03, (0, 0, .015), m["dark"], verts=14, bevel=.006)
    for a in range(4):
        p.cyl("bolt", .015, .02, (math.cos(rad(45 + a * 90)) * .12, math.sin(rad(45 + a * 90)) * .12, .04), m["chrome"], verts=6)
    p.cyl("pole", .035, 4.0, (0, 0, 2.0), m["steel"], verts=12, r2=.025)
    p.cyl("pole_band", .045, .06, (0, 0, .5), m["green"], verts=12)
    p.cyl("pole_band2", .045, .06, (0, 0, .62), m["yellow"], verts=12)
    p.box("cleat", (.04, .12, .03), (0, -.04, 1.3), m["chrome"], bevel=.004)
    p.ball("finial", .06, (0, 0, 4.06), m["gold"], sub=2)
    p.tube("halyard", (0, -.035, 1.3), (0, -.035, 3.95), .005, m["white"], verts=4)
    objs_before = len(p.o)
    flag_br(p, (.55, -.02, 3.55), w=1.0, h=.7)
    for o in p.o[objs_before:]:   # angle the flag a little, as if blowing
        o.matrix_world = Matrix.Translation((.04, -.02, 0)) @ Matrix.Rotation(rad(22), 4, 'Z') @ Matrix.Translation((-.04, .02, 0)) @ o.matrix_world
    for zz in (3.2, 3.9):
        p.cyl("flag_ring", .045, .02, (0, 0, zz), m["chrome"], verts=10)
    return p.o

def fan_table(c):
    """Folding table with a green cloth, cooler on the ground, cups, snack bowl, vuvuzela and a mini flag. 2.2 x 1.3 x 1.0 m."""
    p = P(c); m = mats(); tw, td, th = 1.8, .75, .74
    p.box("top", (tw, td, .045), (0, 0, th - .022), m["plastic"], bevel=.012, seg=2)
    p.box("top_lip", (tw + .02, td + .02, .03), (0, 0, th - .06), m["grey"], bevel=.006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.tube("leg", (sx * (tw / 2 - .15), sy * (td / 2 - .1), th - .06), (sx * (tw / 2 - .4), -sy * (td / 2 - .1), .02), .018, m["steel"], verts=6)
        p.tube("leg_bar", (sx * (tw / 2 - .4), -(td / 2 - .1), .03), (sx * (tw / 2 - .4), (td / 2 - .1), .03), .016, m["steel"], verts=6)
    p.box("cloth", (tw - .4, td + .04, .012), (0, 0, th + .006), m["green"], bevel=.004)
    p.box("cloth_drape", (tw - .4, .012, .28), (0, -td / 2 - .02, th - .14), m["green"], bevel=.004)
    p.box("cloth_hem", (tw - .38, .016, .04), (0, -td / 2 - .022, th - .27), m["yellow"], bevel=0)
    p.txt("BRASIL", .11, (0, -td / 2 - .03, th - .14), m["yellow"], res=1, extrude=0)
    # cups
    for i, (cx, cy) in enumerate([(-.6, .1), (-.5, -.15), (-.38, .12), (-.65, -.2), (-.25, -.1)]):
        p.cyl("cup", .035, .11, (cx, cy, th + .055), m["cup"] if i % 2 else m["cupY"], verts=10, r2=.028)
    # snack bowl
    p.cyl("bowl", .17, .08, (.1, .08, th + .04), m["white"], verts=16, r2=.12, bevel=.008)
    for i in range(7):
        a = i * .9; p.ball("snack", .03, (.1 + math.cos(a) * .08 * (i % 3), .08 + math.sin(a) * .08 * (i % 3), th + .085), m["gold"], sub=1, scale=(1, 1, .6))
    # vuvuzela
    p.cyl("vuvuzela", .06, .55, (.6, -.1, th + .06), m["yellow"], rot=(0, rad(90), rad(15)), verts=12, r2=.018)
    p.cyl("vuvu_mouth", .02, .08, (.6 - .3 * math.cos(rad(15)), -.1 - .3 * math.sin(rad(15)), th + .06), m["green"], rot=(0, rad(90), rad(15)), verts=8)
    p.cyl("vuvu_band", .045, .04, (.6 + .12 * math.cos(rad(15)), -.1 + .12 * math.sin(rad(15)), th + .06), m["green"], rot=(0, rad(90), rad(15)), verts=12)
    # mini flag on a stick
    p.cyl("mini_stick", .006, .4, (.75, .22, th + .2), m["white"], verts=5)
    flag_br(p, (.85, .22, th + .33), w=.22, h=.15, t=.008)
    # cooler on the ground at the left
    cxp, cyp = -1.35, .05
    p.box("cooler", (.6, .4, .42), (cxp, cyp, .21), m["coolerB"], bevel=.025, seg=2)
    p.box("cooler_lid", (.62, .42, .07), (cxp, cyp, .455), m["plastic"], bevel=.015, seg=2)
    p.box("cooler_handle", (.2, .04, .03), (cxp, cyp - .22, .47), m["plastic"], bevel=.006)
    p.box("cooler_band", (.61, .41, .05), (cxp, cyp, .1), m["plastic"], bevel=.006)
    p.cyl("cooler_drain", .02, .02, (cxp + .31, cyp, .08), m["white"], rot=(0, rad(90), 0), verts=8)
    p.txt("GELO", .06, (cxp, cyp - .205, .25), m["plastic"], res=1, extrude=0)
    for i in range(3):   # bottles standing in the open ice on the lid? no - beside the cooler
        p.cyl("bottle", .035, .22, (cxp - .45 + .09 * i, cyp - .1, .11), m["ice"], verts=10)
        p.cyl("bottle_cap", .018, .02, (cxp - .45 + .09 * i, cyp - .1, .23), m["blue"], verts=8)
    # folding chair beside the table
    chx, chy = 1.3, -.1
    for sx in (-1, 1):
        p.tube("chair_leg", (chx + sx * .2, chy - .2, .02), (chx + sx * .2, chy + .2, .45), .012, m["steel"], verts=5)
        p.tube("chair_leg2", (chx + sx * .2, chy + .2, .02), (chx + sx * .2, chy - .2, .45), .012, m["steel"], verts=5)
        p.tube("chair_back", (chx + sx * .2, chy + .18, .45), (chx + sx * .2, chy + .22, .85), .012, m["steel"], verts=5)
    p.box("chair_seat", (.44, .4, .025), (chx, chy, .46), m["green"], bevel=.006)
    p.box("chair_backrest", (.44, .025, .18), (chx, chy + .21, .76), m["yellow"], bevel=.006)
    return p.o

def span_bunting(c, a, b, sag=.45):
    """Preview helper: a bunting line stretched between two world points (what the game does by scaling X)."""
    a, b = Vector(a), Vector(b); d = b - a; ln = math.hypot(d.x, d.y)
    objs = bunting(c, length=12.0, sag=sag)
    return put(objs, x=a.x, y=a.y, z=a.z, rot=math.atan2(d.y, d.x), scale=(ln / 12.0, 1, 1))

@E.event
def v2_DiaDeJogo(c):
    E.diorama(c, w=15)
    put(big_screen(c), x=-3.6, y=3.4, z=.13)
    put(fan_table(c), x=2.6, y=1.5, z=.13, rot=rad(-10))
    put(flag_pole(c), x=5.4, y=-.6, z=.13, rot=rad(150))
    put(flag_pole(c), x=-6.4, y=-.6, z=.13, rot=rad(10))
    for px in (-6.6, 6.6):
        E.pole(c, px, -.9, 4.6); E.pole(c, px, -5.8, 4.6)
    span_bunting(c, (-6.6, -.9, 4.65), (6.6, -5.8, 4.65), sag=.6)
    span_bunting(c, (-6.6, -5.8, 4.65), (6.6, -.9, 4.65), sag=.6)
    span_bunting(c, (-6.6, -.9, 4.5), (6.6, -.9, 4.5), sag=.45)
    for (px, py, who, r) in [(-4.6, 1.3, "Customer_07", 180), (-3.5, 1.0, "Customer_09", 175), (-2.4, 1.4, "Customer_06", 185),
                             (-1.2, 1.8, "Customer_08", 160), (2.0, .4, "Customer_09", 120), (4.0, 2.2, "Customer_07", 220)]:
        E.actor(c, who, (px, py), rad(r))

# ================================================================== export table
PROPS = {"Pagamento_ATM": (atm_kiosk, 1024), "Pagamento_QueueStanchions": (queue_stanchions, 512),
         "Feira_StallRed": (lambda c: feira_stall(c, "canvasR", ("orange", "red", "lime", "purple"), ("ball", "tomato", "lime", "ball")), 1024),
         "Feira_StallBlue": (lambda c: feira_stall(c, "canvasB", ("yellow", "green", "red", "orange"), ("ball", "ball", "tomato", "ball"), ("R$ 4", "R$ 6")), 1024),
         "Feira_StallGreen": (lambda c: feira_stall(c, "canvasG", ("lime", "orange", "purple", "red"), ("lime", "ball", "ball", "tomato"), ("R$ 2", "R$ 8")), 1024),
         "Feira_Banner": (feira_banner, 1024),
         "Calor_StreetThermometer": (street_thermometer, 1024), "Calor_IceCreamCart": (icecream_cart, 1024), "Calor_SunUmbrellaBench": (sun_umbrella_bench, 1024),
         "Sorteio_WheelStand": (wheel_stand, 1024), "Sorteio_WheelDisc": (wheel_disc, 1024), "Sorteio_BalloonArch": (balloon_arch, 1024), "Sorteio_GiftBoxes": (gift_boxes, 512),
         "Jogo_BigScreen": (big_screen, 1024), "Jogo_Bunting": (bunting, 512), "Jogo_FlagPole": (flag_pole, 512), "Jogo_FanTable": (fan_table, 1024)}

def export(names=None):
    out = {}
    for n in (names or PROPS):
        fn, size = PROPS[n]
        c = E.prop_collection(n); mats(); fn(c)
        out[n] = E.export_prop(n, size=size)
        print("EXPORTED", n, out[n], flush=True)
    return out
