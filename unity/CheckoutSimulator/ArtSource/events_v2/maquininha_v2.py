# maquininha_v2.py - "Maquininha fora do ar" redone at the checkout (Lucas 06/11: "se o evento é da maquininha de
# cartão não tá funcionando, o caixa é lá que tem que ficar com alguma animação"). No text baked in: icons only.
#  Maquininha_Handheld   the card machine the cashier lifts up looking for signal: navy body, receipt printer head with
#                        a paper strip, RED error screen with a crossed-out signal icon, keypad, card slot.
#                        Origin at the grip (where the hand holds it), screen facing -Y.
#  Maquininha_NoCardBubble  speech bubble over the counter: a credit card with a red "no" ring across it.
#  Maquininha_CashBills  a little fan of green banknotes (in the customer's hand / on the counter).
#  Maquininha_CounterSign  small acrylic standee on the counter: banknote icon with a green tick + card with a red cross.
import bpy, math, os, sys, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
for p_ in (ART, HERE): 
    if p_ not in sys.path: sys.path.insert(0, p_)
import events_kit as E
import era_kit as k
from vehicles import P, put
from scenes import mats as smats, uvball, poly, torus
rad = math.radians

def mats():
    m = smats()
    if "posRed" not in m:
        m["posRed"] = k.emissive("EV_PosRed", (.95, .03, .02, 1), 1.1)
        m["posBezel"] = k.mat("EV_PosBezel", (.06, .07, .09, 1), rough=.35, var=.03, scale=8)
        m["posBody"] = k.mat("EV_PosBody", (.07, .13, .33, 1), rough=.45, var=.06, scale=10)
        m["posGrey"] = k.mat("EV_PosGrey", (.78, .80, .82, 1), rough=.5, var=.04, scale=8)
        m["keyCream"] = k.mat("EV_KeyCream", (.96, .92, .80, 1), rough=.5, var=.03, scale=10)
        m["cashG"] = k.mat("EV_CashGreen", (.30, .62, .36, 1), rough=.8, var=.12, scale=30)
        m["cashD"] = k.mat("EV_CashDark", (.20, .48, .28, 1), rough=.8, var=.10, scale=30)
        m["cardB"] = k.mat("EV_CardBlue", (.12, .42, .85, 1), rough=.4, var=.05, scale=8)
        m["acrylic2"] = k.mat("EV_AcrylicClear", (.80, .90, .95, 1), rough=.1, var=.02, scale=4)
        m["bubbleW"] = k.mat("EV_BubbleWhite", (.99, .98, .95, 1), rough=.7, var=.02, scale=6)
    return m

def handheld(c):
    p = P(c); m = mats()
    # body: 8 x 17 x 3.4 cm, grip at the origin (lower third), the face towards -Y
    W, L, T = .082, .172, .034
    zc = .045                                           # body centre above the grip point
    p.box("pos_body", (W, T, L), (0, 0, zc), m["posBody"], bevel=.012, seg=3)
    p.box("pos_back_bump", (W * .8, .012, L * .45), (0, T / 2 + .004, zc - .02), m["posBody"], bevel=.006, seg=2)
    # printer head on top with the paper slot and a receipt strip curling out
    p.box("pos_printer", (W * .96, T * 1.25, .045), (0, .004, zc + L / 2 + .012), m["posGrey"], bevel=.012, seg=3)
    p.box("pos_slot", (W * .78, .006, .005), (0, -.012, zc + L / 2 + .036), m["ink"], bevel=.001)
    p.box("pos_paper", (W * .7, .002, .05), (0, -.016, zc + L / 2 + .06), m["paper"], rot=(rad(-12), 0, 0), bevel=0)
    # screen: dark bezel + RED glowing panel with a crossed-out signal icon (3 arcs + dot + slash)
    sz = zc + .036
    p.box("pos_bezel", (W * .86, .004, .062), (0, -T / 2 - .001, sz), m["posBezel"], bevel=.004, seg=2)
    p.box("pos_screen", (W * .74, .003, .05), (0, -T / 2 - .003, sz), m["posRed"], bevel=.002)
    ic = Vector((0, -T / 2 - .0055, sz - .006))
    for i, r in enumerate((.008, .014, .02)):
        pts = [(ic.x + r * math.cos(t), ic.y, ic.z + r * math.sin(t)) for t in [rad(a) for a in range(45, 136, 15)]]
        for a, b in zip(pts, pts[1:]): p.tube("sig", a, b, .0024, m["white"])
    p.ball("sig_dot", .0028, (ic.x, ic.y, ic.z), m["white"])
    p.tube("sig_slash", (ic.x - .017, ic.y - .0005, ic.z - .006), (ic.x + .017, ic.y - .0005, ic.z + .024), .0032, m["white"])
    # keypad 3x4 cream keys + red/yellow/green row
    kz0 = zc - .012
    for row in range(4):
        for col in range(3):
            p.box("key", (.017, .005, .011), (-.022 + col * .022, -T / 2 - .002, kz0 - row * .015), m["keyCream"], bevel=.002)
    for col, mm in enumerate(("red", "yellow", "green")):
        p.box("key_fn", (.017, .005, .011), (-.022 + col * .022, -T / 2 - .002, kz0 - 4 * .015), m[mm], bevel=.002)
    # card slot at the bottom edge, a card half inserted
    p.box("pos_slot_b", (W * .7, .01, .004), (0, -.002, zc - L / 2 - .001), m["ink"], bevel=.001)
    p.box("pos_card", (.054, .0015, .04), (0, -.002, zc - L / 2 - .016), m["cardB"], bevel=.002)
    p.box("pos_chip", (.01, .0018, .008), (-.012, -.0035, zc - L / 2 - .026), m["gold"], bevel=.001)
    return p.o

def card_icon(p, m, loc, s=1.0):
    x, y, z = loc
    p.box("card", (.30 * s, .03 * s, .19 * s), (x, y, z), m["cardB"], bevel=.03 * s, seg=2)
    p.box("card_stripe", (.30 * s, .034 * s, .035 * s), (x, y, z + .045 * s), m["navy"], bevel=.004)
    p.box("card_chip", (.055 * s, .036 * s, .045 * s), (x - .08 * s, y, z - .02 * s), m["gold"], bevel=.008 * s)
    p.box("card_num", (.14 * s, .036 * s, .014 * s), (x + .04 * s, y, z - .055 * s), m["white"], bevel=.004 * s)

def no_ring(p, m, loc, R, r):
    x, y, z = loc
    p.o.append(torus(p.c, "no_ring", R, r, (x, y, z), m["red"], maj=40, mn=10))
    p.box("no_bar", (2 * R, 2 * r, 2 * r), (x, y, z), m["red"], rot=(0, rad(45), 0), bevel=r * .9, seg=3)

def no_card_bubble(c):
    """Speech bubble, origin at its centre, reads from -Y: a card crossed out by a red 'no' ring."""
    p = P(c); m = mats()
    p.box("bubble", (.62, .07, .46), (0, 0, 0), m["bubbleW"], bevel=.16, seg=4)
    p.box("bubble_rim", (.64, .05, .48), (0, .015, 0), m["navy"], bevel=.17, seg=4)
    # tail pointing down-left
    p.o.append(poly(c, "tail", [(-.14, -.17), (.04, -.17), (-.2, -.38)], .06, m["bubbleW"], bevel=.012))
    card_icon(p, m, (0, -.05, .0), .95)
    no_ring(p, m, (0, -.075, 0), .17, .018)
    return p.o

def cash_bills(c):
    """Three banknotes fanned out (origin at the pinch point), ~15 x 7 cm each."""
    p = P(c); m = mats()
    for i, a in enumerate((-18, 0, 18)):
        rot = (0, rad(a), 0)
        cx = math.sin(rad(a)) * .05; cz = .035 + math.cos(rad(a)) * .02
        p.box("bill", (.075, .002, .15), (cx, -.001 * i, cz + .035), m["cashG"], rot=rot, bevel=.002)
        p.box("bill_band", (.077, .0025, .03), (cx + math.sin(rad(a)) * .02, -.001 * i - .0005, cz + .055), m["cashD"], rot=rot, bevel=.001)
        p.cyl("bill_seal", .014, .003, (cx + math.sin(rad(a)) * .045, -.001 * i - .002, cz + .08), m["cashD"], rot=(rad(90), 0, 0), verts=12)
    return p.o

def counter_sign(c):
    """Acrylic standee 16 x 22 cm on a navy foot: banknote + green tick on top, card + red cross below."""
    p = P(c); m = mats()
    p.box("foot", (.17, .07, .02), (0, 0, .01), m["navy"], bevel=.006, seg=2)
    p.box("panel", (.16, .008, .22), (0, 0, .13), m["white"], bevel=.01, seg=2)
    p.box("panel_rim", (.165, .006, .225), (0, .004, .13), m["navy"], bevel=.011, seg=2)
    # top: banknote + tick
    p.box("note", (.085, .004, .045), (-.02, -.006, .19), m["cashG"], bevel=.003)
    p.cyl("note_seal", .011, .003, (-.02, -.009, .19), m["cashD"], rot=(rad(90), 0, 0), verts=12)
    p.tube("tick_a", (.03, -.009, .19), (.042, -.009, .178), .0045, m["green"])
    p.tube("tick_b", (.042, -.009, .178), (.065, -.009, .205), .0045, m["green"])
    # bottom: card + red cross
    p.box("card_s", (.075, .004, .048), (-.02, -.006, .095), m["cardB"], bevel=.006)
    p.box("chip_s", (.014, .005, .011), (-.04, -.008, .092), m["gold"], bevel=.002)
    p.tube("x_a", (.032, -.009, .08), (.064, -.009, .11), .0045, m["red"])
    p.tube("x_b", (.032, -.009, .11), (.064, -.009, .08), .0045, m["red"])
    return p.o

HAND = [0, 0, 1.4]
PROPS = {"Maquininha_Handheld": (handheld, 512), "Maquininha_NoCardBubble": (no_card_bubble, 512),
         "Maquininha_CashBills": (cash_bills, 512), "Maquininha_CounterSign": (counter_sign, 512)}

def export(names=None):
    out = {}
    for n in (names or PROPS):
        fn, size = PROPS[n]
        c = E.prop_collection(n); mats(); fn(c)
        out[n] = E.export_prop(n, size=size)
        print("EXPORTED", n, out[n], flush=True)
    return out

def review(path, bare=False):
    """The checkout counter of the game (checkout_T3) with the new props where the game will put them."""
    import checkout_project as cp
    c = E.clear("EV MaquininhaV2"); m = mats()
    k.box("floor", (5, 4, .05), (0, 0, -.025), m["concrete"], bevel=0, c=c)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(E.REPO, "unity", "CheckoutSimulator", "Assets", "Art", "Interior", "Models", "Tiers", "checkout_T3.fbx"))
    tex = os.path.join(E.REPO, "unity", "CheckoutSimulator", "Assets", "Art", "Interior", "Textures")
    for o in set(bpy.data.objects) - before:
        for cc in list(o.users_collection): cc.objects.unlink(o)
        c.objects.link(o)
        if o.type == 'MESH':
            for mt in o.data.materials:
                for n in (mt.node_tree.nodes if mt and mt.node_tree else []):
                    if n.type == 'TEX_IMAGE' and n.image:
                        f = os.path.join(tex, os.path.basename(n.image.filepath))
                        if os.path.exists(f): n.image.filepath = f; n.image.reload()
    if bare:
        for i in range(-3, 4):          # 0.5 m grid marks on the floor: red = x axis, blue = y axis
            k.box("gx", (.02, 4, .004), (i * .5, 0, .003), m["red" if i == 0 else "grey"], bevel=0, c=c)
            k.box("gy", (5, .02, .004), (0, i * .5, .003), m["blue" if i == 0 else "grey"], bevel=0, c=c)
        return c
    # The counter (checkout_T3): the cashier works on the -Y side (stool, screen), the customers come along +Y
    # (impulse rack, card terminal at about (-.1, .75)). Counter top found by a ray.
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = bpy.context.scene.ray_cast(dg, Vector((.4, .45, 3)), Vector((0, 0, -1)))
    top = loc.z if hit else 1.0
    cashier = E.actor(c, "Customer_07", (-.55, -.42, 0), rad(180))
    customer = E.actor(c, "Customer_08", (.05, 1.35, 0), 0)
    hand = raise_arm(cashier); HAND[:] = hand
    hh = handheld(c)                          # held up, the red screen towards the customer (+Y)
    for o in hh: o.matrix_world = Matrix.Translation(hand) @ Matrix.Rotation(rad(180), 4, 'Z') @ Matrix.Rotation(rad(12), 4, 'X') @ o.matrix_world
    bb = no_card_bubble(c)
    for o in bb: o.matrix_world = Matrix.Translation((.45, .25, 2.35)) @ Matrix.Rotation(rad(180), 4, 'Z') @ o.matrix_world
    cs = counter_sign(c)
    for o in cs: o.matrix_world = Matrix.Translation((-.55, .72, top)) @ Matrix.Rotation(rad(180), 4, 'Z') @ o.matrix_world
    ch = raise_arm(customer, face=(0, -1, 0), upper=(.75, -.35, .1), fore=(1, .15, -.1))   # holding the cash out
    cb = cash_bills(c)
    for o in cb: o.matrix_world = Matrix.Translation(ch + Vector((0, -.02, -.03))) @ Matrix.Rotation(rad(180), 4, 'Z') @ Matrix.Rotation(rad(-60), 4, 'X') @ o.matrix_world
    # the counter's own terminal blinks red in the game: a red light over it here
    lt = bpy.data.lights.new("TermRed", 'POINT'); lt.color = (1, .15, .1); lt.energy = 25; lt.shadow_soft_size = .05
    lo = bpy.data.objects.new("TermRed", lt); lo.location = (-.1, .72, top + .12); c.objects.link(lo)
    return c

def raise_arm(rig, face=(0, 1, 0), upper=(.8, .25, .2), fore=(.45, .9, 0)):
    """Freezes the rig's current (idle) pose, then lifts its right arm up in front, as if holding the machine up
    looking for signal. Returns the world position of the hand."""
    sc = bpy.context.scene; sc.frame_set(1); bpy.context.view_layer.update()
    saved = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
    if rig.animation_data: rig.animation_data.action = None
    for pb in rig.pose.bones:                      # parents before children
        pb.matrix = saved[pb.name]; bpy.context.view_layer.update()
    inv = rig.matrix_world.inverted().to_3x3()
    fw = Vector(face); fwd = (inv @ fw).normalized()          # where the character faces in the world
    side = (inv @ Vector((-fw.y, fw.x, 0))).normalized()     # outwards, on the side of this arm
    up = (inv @ Vector((0, 0, 1))).normalized()
    # (this rig's bones are not chained head-to-tail: a limb's direction is from its head to the next bone's head)
    def aim(name, child, d):
        pb, ch = rig.pose.bones[name], rig.pose.bones[child]
        h = pb.head.copy(); v = ch.head - h
        q = v.rotation_difference(d.normalized())
        pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
        bpy.context.view_layer.update()
    aim("UpperArm_R", "Forearm_R", fwd * upper[0] + up * upper[1] + side * upper[2])
    aim("Forearm_R", "Hand_R", fwd * fore[0] + up * fore[1] + side * fore[2])
    fa, hd = rig.pose.bones["Forearm_R"].head, rig.pose.bones["Hand_R"].head
    return rig.matrix_world @ (hd + (hd - fa).normalized() * .09)

if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    if args and args[0] == "layout":
        c = review(None, bare=True); sc = bpy.context.scene
        out = os.path.join(ART, "..", "Temp", "qa", "maquininha_v2"); os.makedirs(out, exist_ok=True)
        import shutil
        for tag, d in (("top", (0, -.001, 1)), ("front", (0, -1, .35)), ("back", (0, 1, .35))):
            E.preview("MaquininhaV2", res=(1200, 900), ortho=3.4, target=(0, .37, .8), direction=d)
            shutil.copy(sc.render.filepath, os.path.join(out, "layout_" + tag + ".png"))
        print("LAYOUT_DONE", flush=True)
    elif args and args[0] == "export":
        print(json.dumps(export(), default=str))
    else:
        import checkout_project as cp
        c = review(None)
        sc = bpy.context.scene
        out = os.path.join(ART, "..", "Temp", "qa", "maquininha_v2")
        os.makedirs(out, exist_ok=True)
        # overall + close-ups of the props
        E.preview("MaquininhaV2", res=(1500, 1000), ortho=3.6, target=(0, .4, 1.1), direction=(.55, 1, .8))
        import shutil; shutil.copy(sc.render.filepath, os.path.join(out, "review_counter.png"))
        E.preview("MaquininhaV2", res=(1200, 900), ortho=.9, target=tuple(HAND), direction=(.3, 1, .25))
        shutil.copy(sc.render.filepath, os.path.join(out, "review_handheld.png"))
        E.preview("MaquininhaV2", res=(1200, 900), ortho=1.1, target=(.45, .25, 2.35), direction=(.3, 1, .25))
        shutil.copy(sc.render.filepath, os.path.join(out, "review_bubble.png"))
        E.preview("MaquininhaV2", res=(1200, 900), ortho=1.2, target=(-.3, .95, 1.0), direction=(.5, 1, .6))
        shutil.copy(sc.render.filepath, os.path.join(out, "review_sign_cash.png"))
        print("REVIEW_DONE", out, flush=True)
