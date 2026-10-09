"""Venda pela janela (interactive event 12 - Engarrafamento): jam car with a driver, cooler, vendor clips.

Rig_Car (from EventProps2/Transito_Car.fbx - the v3 rounded car built by events_v3/vehicles.py, same bones as event_rigs/vehicles.py: Root, Body, Wheel_F/R_L/R) gets
  - Window_Driver (child of Body): the driver's door glass, slides down into the door (Car_WindowDown / Car_WindowUp, 18 f);
  - a driver bust (head, chest, both arms) cut from one of the game's customers (Customer_09), skinned to
    Driver_Root, Driver_Head, Driver_Arm_L, Driver_Forearm_L, Driver_Hand_L (the arm on the door side);
  - clips Driver_Honk 12, Driver_WaveOut 48 (loop), Driver_TakeBottle 48, Driver_Pay 36, Car_HonkBounce 12.
  The car drives along world -X here (the FBX comes back turned, like in event_rigs); the driver sits on the
  -Y side (right-hand traffic: the kerb side when the jam's lane is next to the market's sidewalk).
Rig_Cooler: styrofoam cooler with a shoulder strap, ice, water bottles and soda cans; bones Root -> Lid
  (hinge at the back edge), clips Cooler_Open / Cooler_Close (18 f). Parented by the game to the vendor's Torso.
Props: Vendor_Bottle (water PET, 29 cm), Vendor_Can (soda, 12 cm), Vendor_Coins, Horn_Icon (balloon pictogram).
Vendor clips (on the character skeleton, IK feet; keyed here on the Staff_Clerk for the preview; the cooler hangs
on the +X hip (bone side "R"), that hand opens the lid / takes the bottle / hands it over, the other holds the strap):
  Vendor_WalkCarry 32 (loop, stride 0.70 -> 0.76 m/s in the game), Vendor_OpenCooler 36, Vendor_TakeBottle 36,
  Vendor_HandOver 36, Vendor_ReceiveCoin 36.

    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\events_interactive\\window_sale.py").read())
    S = build(); review(S); save()
"""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

HERE = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\events_interactive"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import importlib, ei_kit
importlib.reload(ei_kit)
from ei_kit import *                       # noqa
E = ei_kit
veh = E._script_module("ev_vehicles", os.path.join(RIGS, "vehicles.py"), base=rk.__dict__)
V = ch.V
ss, mix, TAU = ch.ss, ch.mix, ch.TAU
ACTOR = 0.72                                # the game's scale for the 2.4 m character models
DRIVER_SCALE = 0.68                         # seated a little lower in the car
DRIVER = "Customer_09"


# ============================================================================================ car + driver
def driver_bust(name="Driver_Bust"):
    """Head, chest and arms of a customer, decimated (~4k tris), vertex groups renamed to the driver bones.
    Returns (mesh object in character space, armature of the source to delete)."""
    arm, body = load_character(os.path.join(CHARS, DRIVER + ".fbx"), os.path.join(CHARS, DRIVER + ".png"), "tmp_driver_rig", name)
    names = [g.name for g in body.vertex_groups]
    keep_groups = {"Head", "Torso", "UpperArm_R", "Forearm_R", "Hand_R", "UpperArm_L", "Forearm_L", "Hand_L"}
    bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
    dl = bm.verts.layers.deform.verify()
    kill = []
    for v in bm.verts:
        d = v[dl]
        g = max(d.items(), key=lambda kv: kv[1])[0] if len(d) else -1
        gname = names[g] if g >= 0 else ""
        if gname not in keep_groups or (gname == "Torso" and v.co.z < 1.22) or (gname in ("UpperArm_L", "Forearm_L", "Hand_L") and v.co.z < 1.30):
            kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(body.data); bm.free()
    # bone mapping: the +X arm (bone names *_R) is the character's physical left arm -> the door side
    remap = {"Head": "Driver_Head", "Torso": "Driver_Root", "UpperArm_R": "Driver_Arm_L", "Forearm_R": "Driver_Forearm_L",
             "Hand_R": "Driver_Hand_L", "UpperArm_L": "Driver_Root", "Forearm_L": "Driver_Root", "Hand_L": "Driver_Root"}
    for g in list(body.vertex_groups):
        if g.name not in remap:
            body.vertex_groups.remove(g)
    for g in list(body.vertex_groups):
        g.name = "tmp_" + remap[g.name]
    merged = {}
    for g in list(body.vertex_groups):
        target = g.name[4:]
        if target in merged:
            tgt = merged[target]
            for v in body.data.vertices:
                for vg in v.groups:
                    if vg.group == g.index and vg.weight > 0:
                        tgt.add([v.index], vg.weight, 'ADD')
            body.vertex_groups.remove(g)
        else:
            merged[target] = g
    for target, g in merged.items():
        g.name = target
    body.parent = None; body.modifiers.clear()
    dec = body.modifiers.new("Decimate", 'DECIMATE'); dec.ratio = 0.34
    dec.vertex_group = "Driver_Hand_L"; dec.invert_vertex_group = True; dec.vertex_group_factor = 1.0   # the hand keeps its detail
    bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active = body
    with bpy.context.temp_override(**ctx(), active_object=body, object=body, selected_objects=[body]):
        bpy.ops.object.modifier_apply(modifier="Decimate")
    bpy.data.objects.remove(arm, do_unlink=True)
    return body


def cut_window(obj, x0, x1, z0, z1, y0, y1):
    """Opens a rectangular hole (x0..x1, z0..z1) through every wall of `obj` lying between y0 and y1 (world):
    bisects the nearby faces along the four edges, then deletes the faces inside the rectangle."""
    M = obj.matrix_world; Mi = M.inverted()
    bm = bmesh.new(); bm.from_mesh(obj.data)
    def near():
        out = []
        for f in bm.faces:
            c = M @ f.calc_center_median()
            if y0 < c.y < y1 and x0 - .3 < c.x < x1 + .3 and z0 - .3 < c.z < z1 + .3:
                out.append(f)
        return out
    for co, no in (((x0, 0, 0), (1, 0, 0)), ((x1, 0, 0), (1, 0, 0)), ((0, 0, z0), (0, 0, 1)), ((0, 0, z1), (0, 0, 1))):
        fs = near()
        geom = list({g for f in fs for g in f.verts} | {g for f in fs for g in f.edges} | set(fs))
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Mi @ Vector(co), plane_no=(Mi.to_3x3() @ Vector(no)).normalized(), dist=1e-5)
    kill = []
    for f in bm.faces:
        c = M @ f.calc_center_median()
        if y0 < c.y < y1 and x0 + 1e-4 < c.x < x1 - 1e-4 and z0 + 1e-4 < c.z < z1 - 1e-4:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    return len(kill)


def glass_window_far_side(o, isl, glass):
    """The asset's passenger-side front window is a solid plate textured in the dark frame grey: seen from the
    driver's side it reads as a dark block standing on the windscreen. Maps it to the glass texel, like the
    driver's pane and the other windows."""
    far = [i for i in isl if i.size.y < 0.15 and i.center.y > 0.6 and abs(i.center.x - glass.center.x) < 0.12
           and abs(i.lo.z - glass.lo.z) < 0.08 and abs(i.hi.z - glass.hi.z) < 0.08 and i.idx != glass.idx]
    if not far:
        return 0
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active
    gv = set(glass.verts); uv = Vector((0.0, 0.0)); n = 0
    for f in bm.faces:
        if all(v.index in gv for v in f.verts):
            for l in f.loops:
                uv += l[uvl].uv; n += 1
    uv /= max(1, n); done = 0
    for i in far:
        fv = set(i.verts)
        for f in bm.faces:
            if all(v.index in fv for v in f.verts):
                for l in f.loops:
                    l[uvl].uv = uv
                done += 1
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return done


def rig_car(prop="Transito_Car", rig_name="Rig_Car"):
    o = rk.import_prop(prop); S = o.matrix_world.copy(); W = lambda p: S @ Vector(p)
    isl = rk.islands(o)
    wheels = veh.find_wheels(isl)
    glass = [i for i in isl if i.size.y < 0.15 and i.center.y > 0.6 and -0.2 < i.center.x < 0.8 and i.lo.z > 0.95
             and 0.5 < i.size.x < 0.85 and i.size.z > 0.3]
    glass = min(glass, key=lambda i: i.size.x)        # the front door pane (its rubber seal is the wider island)
    # (v3 car: the far-side pane is real glass set in its seal - the old dark-plate fix is not needed)
    base = veh.part_of_factory(isl, wheels, prop)
    def part_of(i):
        return "Window_Driver" if i.idx == glass.idx else base(i)
    parts = rk.split(o, part_of)
    centers = {kk: sum((t.center for t in v), Vector()) / len(v) for kk, v in wheels.items()}
    axle_z = sum(c.z for c in centers.values()) / len(centers)
    mid = Vector(((max(c.x for c in centers.values()) + min(c.x for c in centers.values())) / 2, 0, axle_z))
    bones = [("Root", W((0, 0, 0)), W((0, 0, 0.5)), None), ("Body", W(mid), W(mid + Vector((0, 0, 0.6))), "Root")]
    for kk, c in centers.items():
        bones.append(("Wheel_" + kk, W(c), W(c + Vector((0, 0.3 if c.y > 0 else -0.3, 0))), "Root"))
    gb = W((glass.center.x, glass.center.y, glass.lo.z))
    bones.append(("Window_Driver", gb, gb + Vector((0, 0, 0.3)), "Body"))
    # driver: character space -> car space (seat on the -Y side, facing -X)
    Mc = Matrix.Translation((W((glass.center.x, 0, 0)).x + 0.30, -0.34, -0.23)) @ Matrix.Rotation(rad(-90), 4, 'Z') @ Matrix.Scale(DRIVER_SCALE, 4)
    C = lambda p: Mc @ Vector(p)
    hip, head = C((0, 0, 1.035)), C((0, 0, 1.87))
    sh, el, wr = C((0.30, 0, 1.80)), C((0.35, 0, 1.36)), C((0.37, -0.025, 1.04))
    bones += [("Driver_Root", hip, hip + Vector((0, 0, 0.45)), "Body"), ("Driver_Head", head, head + Vector((0, 0, 0.3)), "Driver_Root"),
              ("Driver_Arm_L", sh, el, "Driver_Root"), ("Driver_Forearm_L", el, wr, "Driver_Arm_L"),
              ("Driver_Hand_L", wr, wr + (wr - el).normalized() * 0.12, "Driver_Forearm_L")]
    arm = rk.armature(rig_name, Matrix.Identity(4), bones)
    # the driver's window is a real opening: cut it through the door frame panel and the cabin wall
    body_part = parts["Body"]
    glo, ghi = W(glass.lo), W(glass.hi)
    x0, x1 = sorted((glo.x, ghi.x)); yc = (glo.y + ghi.y) / 2
    cut_window(body_part, x0 + .025, x1 - .025, glo.z + .02, ghi.z - .02, yc - .14, yc + .12)
    m = mats()
    # dark cabin interior on the passenger half (its face at y -0.08 is the backdrop behind the driver), kept inside
    # the v3 greenhouse: behind the windscreen base (x0 - 0.35 here, the car's front is -X) and under the roof (1.56)
    interior = k.box("interior", (1.05, 0.60, 0.54), ((x0 + x1) / 2 + 0.45, 0.22, 1.06), m["dark"], bevel=0)
    seat = k.box("seat_back", (0.14, 0.46, 0.76), (x1 + 0.20, -0.32, 1.00), m["dark"], bevel=.03, seg=2)
    # door sill under the opening: hides the door cavity (and the lowered pane) from the high camera
    sill = k.box("door_sill", (x1 - x0 + 0.16, 0.24, 0.02), ((x0 + x1) / 2, yc + 0.10, glo.z - 0.012), m["dark"], bevel=0)
    for o2 in (interior, seat, sill):
        k.bake(o2); o2.name = f"{prop}__Body_{o2.name}"
        rk.attach(o2, arm, "Body")
    for name, o2 in parts.items():
        o2.name = f"{prop}__{name}"; rk.attach(o2, arm, name)
    extra = [interior, seat, sill]
    bust = driver_bust()
    bust.matrix_world = Mc
    bust.parent = arm; bust.parent_type = 'OBJECT'; bpy.context.view_layer.update(); bust.matrix_world = Mc
    md = bust.modifiers.new("Armature", 'ARMATURE'); md.object = arm
    bust.name = f"{prop}__Driver"
    return arm, list(parts.values()) + extra + [bust], {"glass": glass, "W": W, "C": C, "Mc": Mc}


def car_clips(arm):
    acts = []
    down = -0.46                                 # the pane is 0.40 tall: fully inside the door
    for name, a, b in (("Car_WindowDown", 0, 1), ("Car_WindowUp", 1, 0)):
        act = rk.new_action(arm, name)
        for f, u in ((1, a), (18, b)):
            rk.pose(arm, "Window_Driver", f, loc=(0, down * u, 0))
        rk.smooth(act, cyclic=False); act.frame_start, act.frame_end = 1, 18; acts.append(act)
    act = rk.new_action(arm, "Car_HonkBounce")
    for f, dz in ((1, 0), (4, 0.035), (8, -0.012), (12, 0)):
        rk.pose(arm, "Body", f, loc=(0, dz, 0))
    rk.smooth(act, cyclic=False); act.frame_start, act.frame_end = 1, 12; acts.append(act)
    # driver: armature-space axes. X = along the car (front -X), Y = across (window at -Y), Z up.
    def driver_pose(f, arm_out, fore_up, wave=0.0, head_turn=0.0, nod=0.0, push=0.0, palm=0.0, fore_fwd=0.0):
        """arm_out: upper arm from hanging (0) to horizontal out of the window (1); fore_up: forearm lift out of
        the window (deg); push / fore_fwd: arm and forearm towards the steering wheel (inside)."""
        q_arm = rk.compose((X, -92 * arm_out), (Y, 50 * push))
        rk.pose_q(arm, "Driver_Arm_L", f, q_arm)
        q_fore = rk.compose((X, -fore_up), (Y, wave + fore_fwd))
        rk.pose_q(arm, "Driver_Forearm_L", f, q_fore)
        rk.pose_q(arm, "Driver_Hand_L", f, rk.compose((X, -palm)))
        rk.pose_q(arm, "Driver_Head", f, rk.compose((Z, head_turn), (Y, -nod)))
    act = rk.new_action(arm, "Driver_Honk")
    for f, p, n in ((1, 0, 0), (4, 1, 6), (8, 0.2, 0), (12, 0, 0)):
        driver_pose(f, 0, 0, push=0.5 + 0.4 * p, fore_fwd=70 + 12 * p, nod=n)
    rk.smooth(act, cyclic=False); act.frame_start, act.frame_end = 1, 12; acts.append(act)
    act = rk.new_action(arm, "Driver_WaveOut", frames=48)
    for f in range(1, 50, 2):
        w = 26 * math.sin(TAU * (f - 1) / 24)
        driver_pose(f, 0.95, 95, wave=w, head_turn=48, nod=4, push=0.0, fore_fwd=0.0)
    rk.linear(act, "rotation"); act.frame_start, act.frame_end = 1, 48; acts.append(act)
    act = rk.new_action(arm, "Driver_TakeBottle")
    for f in range(1, 50, 2):
        out = ss(1, 12, f) * (1 - ss(32, 46, f)); grab = ss(20, 28, f)
        driver_pose(f, out, (2 + 70 * grab) * out, head_turn=50 * out, nod=8 * out, palm=30 * out * (1 - grab), push=0.5 * (1 - out), fore_fwd=70 * (1 - out))
    rk.linear(act, "rotation"); act.frame_start, act.frame_end = 1, 48; acts.append(act)
    act = rk.new_action(arm, "Driver_Pay")
    for f in range(1, 38, 2):
        out = ss(1, 10, f) * (1 - ss(24, 34, f))
        driver_pose(f, out, 14 * out, head_turn=45 * out, nod=4 * out, palm=35 * out, push=0.5 * (1 - out), fore_fwd=70 * (1 - out))
    rk.linear(act, "rotation"); act.frame_start, act.frame_end = 1, 36; acts.append(act)
    return acts


# ============================================================================================ cooler
def cooler():
    """Styrofoam cooler 50 x 34 x 36 cm with a teal shoulder strap; ice, 4 water bottles, 4 soda cans inside.
    Rig_Cooler: Root (bottom centre) -> Lid (hinge along the back top edge, +Y side). Clips Cooler_Open/Close."""
    m = mats(); Wd, D, H, T = .50, .34, .34, .03
    box = [k.box("cooler_shell", (Wd, D, H), (0, 0, H / 2), m["foam"], bevel=.025, seg=3)]
    box.append(k.box("cooler_band", (Wd + .006, D + .006, .05), (0, 0, H - .08), m["teal"], bevel=.01, seg=2))
    box.append(k.box("cooler_foot", (Wd - .06, D - .06, .02), (0, 0, .01), m["grey"], bevel=.005, seg=1))
    for sx in (-1, 1):
        box.append(k.box("strap_anchor", (.03, .05, .06), (sx * (Wd / 2 + .012), 0, H - .12), m["navy"], bevel=.008, seg=2))
    # strap: over the shoulder (the box hangs at the hip, the strap rises to +Z and curves inward)
    pts = [Vector((-.26, 0, H - .12)), Vector((-.27, -.04, .45)), Vector((-.17, -.10, .64)), Vector((0, -.12, .72)),
           Vector((.17, -.10, .64)), Vector((.27, -.04, .45)), Vector((.26, 0, H - .12))]
    for a, b in zip(pts, pts[1:]):
        s = k.tube("strap", a, b, .010, m["teal"], verts=8); s.scale = (1.8, 1, 1); box.append(s)
    box.append(k.box("strap_pad", (.24, .05, .022), (0, -.12, .72), m["navy"], bevel=.008, seg=2))
    # cavity + contents (the shell is solid; the contents sit in a dark inset so the rim reads)
    box.append(k.box("inset", (Wd - 2 * T, D - 2 * T, .02), (0, 0, H - .01), m["ice"], bevel=0))
    rng = np.random.default_rng(3)
    for i in range(14):
        x, y = rng.uniform(-(Wd / 2 - T - .03), Wd / 2 - T - .03), rng.uniform(-(D / 2 - T - .03), D / 2 - T - .03)
        c = k.box("ice_cube", (.038, .038, .032), (x, y, H - .005 + rng.uniform(0, .02)), m["ice"], rot=tuple(rng.uniform(0, 1, 3)), bevel=.009, seg=1)
        box.append(c)
    contents = box
    for i, x in enumerate((-.17, -.06)):
        for j, y in enumerate((-.08, .07)):
            contents.append(bottle(f"cooler_bottle_{i}{j}", (x, y, H - .12), rot=(rad(rng.uniform(-8, 8)), rad(rng.uniform(-8, 8)), rng.uniform(0, 6)), seg=10))
    for i, x in enumerate((.08, .18)):
        for j, y in enumerate((-.09, .06)):
            contents.append(can(f"cooler_can_{i}{j}", (x, y + (.04 if i else 0), H - .06), rot=(rad(rng.uniform(-6, 6)), rad(rng.uniform(-6, 6)), rng.uniform(0, 6))))
    body = join(contents, "Cooler__Body", origin=(0, 0, 0))
    lid = [k.box("lid", (Wd + .01, D + .01, .055), (0, 0, H + .0275), m["foam"], bevel=.022, seg=3),
           k.box("lid_band", (Wd + .016, D + .016, .018), (0, 0, H + .012), m["teal"], bevel=.004, seg=1),
           k.box("lid_handle", (.14, .05, .02), (0, -D / 2 + .02, H + .06), m["navy"], bevel=.006, seg=2),
           k.box("lid_plug", (Wd - 2 * T - .01, D - 2 * T - .01, .02), (0, 0, H - .01), m["foam"], bevel=.004, seg=1)]
    lid = join(lid, "Cooler__Lid", origin=(0, D / 2, H))
    hinge = Vector((0, D / 2, H))
    arm = rk.armature("Rig_Cooler", Matrix.Identity(4), [("Root", (0, 0, 0), (0, 0, 0.2), None), ("Lid", hinge, hinge + Vector((0, 0, 0.2)), "Root")])
    rk.attach(body, arm, "Root"); rk.attach(lid, arm, "Lid")
    acts = []
    for name, a, b in (("Cooler_Open", 0, 1), ("Cooler_Close", 1, 0)):
        act = rk.new_action(arm, name)
        for f, u in ((1, a), (18, b)):
            rk.pose(arm, "Lid", f, rot=(X, -105 * u))
        rk.smooth(act, cyclic=False); act.frame_start, act.frame_end = 1, 18; acts.append(act)
    return arm, [body, lid], acts


# ============================================================================================ small props
def bottle(name="Vendor_Bottle", loc=(0, 0, 0), rot=(0, 0, 0), seg=14):
    """Water PET 29 cm: clear body, blue label band with a wave pictogram, blue cap."""
    m = mats(); h, r = .29, .034
    prof = [(0, 0), (r * .8, 0), (r, .012), (r, .17), (r * .92, .20), (r * .55, .235), (r * .40, .245), (r * .40, .265), (0, .265)]
    body = lathe(name + "_body", prof, (0, 0, 0), m["water"], seg=seg)
    liquid = lathe(name + "_water", [(0, .004), (r * .78, .004), (r * .9, .02), (r * .9, .16), (r * .5, .19), (0, .19)], (0, 0, 0), m["sky"], seg=seg - 2)
    band = k.cyl(name + "_label", r + .003, .07, (0, 0, .10), m["blue"], verts=seg)
    wave = k.cyl(name + "_wave", r + .006, .012, (0, 0, .10), m["white"], verts=seg)
    wave.scale = (1, 1, 1); wave.rotation_euler = (rad(12), 0, 0)
    cap = k.cyl(name + "_cap", r * .46, .028, (0, 0, h - .016), m["blue"], verts=12, bevel=.003, seg=1)
    ring = k.cyl(name + "_ring", r * .5, .006, (0, 0, h - .036), m["blue"], verts=12)
    o = join([body, liquid, band, wave, cap, ring], name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = rot
    return o


def can(name="Vendor_Can", loc=(0, 0, 0), rot=(0, 0, 0)):
    """Soda can 12 cm: red body with a cream swoosh band and a silver top with a tab."""
    m = mats(); r, h = .033, .122
    body = lathe(name + "_body", [(0, 0), (r * .8, 0), (r, .008), (r, .105), (r * .88, .116), (r * .86, .122), (0, .122)], (0, 0, 0), m["red"], seg=14)
    band = k.cyl(name + "_band", r + .002, .022, (0, 0, .062), m["cream"], verts=14)
    band.rotation_euler = (rad(18), 0, 0)
    top = k.cyl(name + "_top", r * .80, .004, (0, 0, h + .001), m["chrome"], verts=14)
    tab = k.box(name + "_tab", (.012, .018, .003), (0, .004, h + .005), m["chrome"], bevel=.001, seg=1)
    o = join([body, band, top, tab], name, origin=(0, 0, 0))
    o.location = loc; o.rotation_euler = rot
    return o


def coins(name="Vendor_Coins"):
    m = mats(); parts = []
    for i, (x, y, z, rz) in enumerate(((0, 0, 0, 0), (.004, .003, .004, .3), (-.003, .004, .008, .7))):
        parts.append(k.cyl(f"coin_{i}", .016, .004, (x, y, z + .002), m["gold"], rot=(0, 0, rz), verts=16, bevel=.001, seg=1))
        parts.append(k.cyl(f"coin_rim_{i}", .012, .005, (x, y, z + .002), m["yellow"], verts=16))
    return join(parts, name, origin=(0, 0, 0))


def arc(name, R, r, a0, a1, m, segs=10, verts=8):
    """Tube bent along an arc in the XZ plane (centre at the origin), from angle a0 to a1 (degrees)."""
    bm = bmesh.new(); rings = []
    for i in range(segs + 1):
        a = rad(mix(a0, a1, i / segs)); c = Vector((math.cos(a) * R, 0, math.sin(a) * R)); t = Vector((-math.sin(a), 0, math.cos(a)))
        n1 = Vector((0, 1, 0)); n2 = t.cross(n1)
        rings.append([bm.verts.new(c + (n1 * math.cos(j * TAU / verts) + n2 * math.sin(j * TAU / verts)) * r) for j in range(verts)])
    for ra, rb in zip(rings, rings[1:]):
        for j in range(verts):
            bm.faces.new((ra[j], ra[(j + 1) % verts], rb[(j + 1) % verts], rb[j]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    return o


def horn_icon(name="Horn_Icon"):
    """Balloon pictogram: an orange horn (bell pointing +X) with three yellow sound arcs. Faces -Y, ~40 cm."""
    m = mats()
    bell = lathe("horn_bell", [(0, 0), (.025, 0), (.03, .05), (.045, .10), (.075, .15), (.10, .175), (.10, .18), (.06, .18), (.045, .16), (.03, .10), (.02, .05), (0, .05)], (0, 0, 0), m["orange"], seg=16)
    bell.rotation_euler = (0, rad(90), 0); bell.location = (-.07, 0, .14)
    mouth = k.cyl("horn_mouth", .018, .05, (-.11, 0, .14), m["navy"], rot=(0, rad(90), 0), verts=10, bevel=.003, seg=1)
    parts = [bell, mouth]
    for i, R in enumerate((.17, .23, .29)):
        a = arc(f"horn_wave_{i}", R, .013, -32, 32, m["yellow"], segs=8)
        a.location = (.0, 0, .14); parts.append(a)
    return join(parts, name, origin=(0, 0, 0))


# ============================================================================================ vendor clips
VCLIPS = {}


def vclip(name, frames):
    def deco(fn):
        VCLIPS[name] = (frames, fn, False)
        return fn
    return deco


_solve_orig = ch.solve


def solve_z(p):
    """characters.solve with a foot height: legs may be ("ik", dx, dy, dz)."""
    r = p.r; A = _solve_orig(p)
    T = ch._rot(p.lean, p.turn, p.tilt)
    piv = r.pivot + V(0, 0, p.lift)
    carry = lambda pt: piv + T @ (pt - r.pivot)
    swing = lambda parent, rest_dir, want: (parent @ rest_dir).rotation_difference(want) @ parent
    for s in (1, -1):
        leg = p.legs.get(s)
        if not leg or leg[0] != "ik" or len(leg) < 4:
            continue
        hip = carry(r.hip[s])
        ankle = r.ankle[s] + V(s * leg[1], -leg[2], leg[3])
        knee, ank = ch.two_bone(hip, ankle, r.l_th, r.l_sh, T @ V(0, -1, 0.15))
        A[r.th[s]] = swing(T, r.knee[s] - r.hip[s], knee - hip)
        A[r.sh[s]] = swing(A[r.th[s]], r.ankle[s] - r.knee[s], ank - knee)
        toe = leg[4] if len(leg) > 4 else 0.0
        A[r.ft[s]] = Quaternion(X, math.radians(toe))
    return A


ch.solve = solve_z


def step(s, t, stride=0.70, lift=0.13):
    """In-place walk: foot s at cycle phase t in 0..1 (s=+1 leads by half a cycle). -> (dy, dz, toe)"""
    u = (t + (0.5 if s > 0 else 0.0)) % 1.0
    if u < 0.5:                                   # stance: planted, moving back at constant speed
        dy = mix(stride / 2, -stride / 2, u / 0.5); return dy, 0.0, 0.0
    v = (u - 0.5) / 0.5                            # swing: forward with an arc
    return mix(-stride / 2, stride / 2, v), lift * math.sin(math.pi * v), 18 * math.sin(math.pi * v)


def box_hand(p, lift=0.0):
    """The +X hand steadies the cooler lid at the hip; the strap sits on the -X shoulder."""
    return p.hand_at(1, 0.42, -0.16, 1.28 + lift, pole=V(1.0, 0.5, -0.9), bend=-12)


@vclip("Vendor_WalkCarry", 32)
def walk_carry(r, f):
    t = (f - 1) / 32.0
    bob = 0.025 * abs(math.sin(TAU * t))
    p = ch.Pose(r).torso(lean=5, lift=-bob - 0.005, tilt=3 * math.sin(TAU * t)).head(nod=-2, tilt=-2 * math.sin(TAU * t))
    for s in (1, -1):
        dy, dz, toe = step(s, t)
        p.legs[s] = ("ik", 0.0, dy, dz, toe)
    box_hand(p, lift=0.6 * bob)
    sw = 0.08 * math.sin(TAU * t)
    p.hand_at(-1, 0.30, 0.04 + sw, 1.12, pole=V(-0.8, 0.5, -1.0), bend=-6)
    return p


def strap_hand(p):
    """The -X hand holds the strap at the chest (the cooler hangs on the +X hip)."""
    return p.hand_at(-1, 0.10, -0.26, 1.62, pole=V(-1.0, 0.3, -0.8), bend=-10)


@vclip("Vendor_OpenCooler", 36)
def open_cooler(r, f):
    """The hip-side hand lifts the lid by its free (inner) edge; the lid swings open over the outer hinge."""
    reach = ss(1, 8, f) * (1 - ss(30, 36, f))
    up = ss(8, 18, f) * (1 - ss(26, 34, f))
    p = ch.Pose(r).head(nod=24 * reach, turn=-18 * reach).torso(lean=4 * reach, turn=-8 * reach)
    p.hand_at(1, mix(0.42, 0.26 + 0.10 * up, reach), mix(-0.16, -0.14, reach), mix(1.28, 1.36 + 0.30 * up, reach), pole=V(1.0, 0.4, -0.8), bend=-10)
    strap_hand(p)
    for s in (1, -1): p.planted(s)
    return p


@vclip("Vendor_TakeBottle", 36)
def take_bottle(r, f):
    """Dips into the open cooler and comes up with a bottle (hip-side hand)."""
    down = ss(1, 10, f) * (1 - ss(16, 26, f))
    out = ss(16, 26, f) * (1 - ss(30, 36, f))
    p = ch.Pose(r).head(nod=26 * down + 6 * out, turn=-18 * down).torso(lean=8 * down, turn=-10 * down)
    p.hand_at(1, mix(0.42, 0.44, down) - 0.06 * out, mix(-0.16, -0.08, down) - 0.22 * out, mix(1.36, 1.14, down) + 0.22 * out, pole=V(1.0, 0.4, -0.8), bend=-15 + 10 * down)
    strap_hand(p)
    for s in (1, -1): p.planted(s)
    return p


@vclip("Vendor_HandOver", 36)
def hand_over(r, f):
    """Reaches the bottle out and down to the car window (hip-side hand)."""
    out = ss(1, 12, f) * (1 - ss(24, 36, f))
    p = ch.Pose(r).head(nod=14 * out).torso(lean=12 * out)
    p.hand_at(1, mix(0.42, 0.14, out), mix(-0.16, -0.80, out), mix(1.30, 1.42, out), pole=V(1.0, 0.4, -0.7), bend=-15 * out)
    strap_hand(p)
    for s in (1, -1): p.planted(s, dy=0.10 * out if s > 0 else 0.0)
    return p


@vclip("Vendor_ReceiveCoin", 36)
def receive_coin(r, f):
    """Open palm at the window, then the coins go into the chest pocket."""
    out = ss(1, 10, f) * (1 - ss(18, 26, f))
    pocket = ss(22, 30, f) * (1 - ss(32, 36, f))
    p = ch.Pose(r).head(nod=10 * out - 6 * pocket).torso(lean=8 * out)
    p.hand_at(1, mix(0.42, 0.16, out) - 0.14 * pocket, mix(-0.16, -0.74, out) - 0.20 * pocket, mix(1.30, 1.42, out) + 0.30 * pocket, pole=V(1.0, 0.4, -0.7), bend=22 * out)
    strap_hand(p)
    for s in (1, -1): p.planted(s)
    return p


# ============================================================================================ build
def build():
    rk.reset()
    bpy.context.scene.frame_set(1)
    car, car_parts, info = rig_car()
    car_acts = car_clips(car)
    cool, cool_parts, cool_acts = cooler()
    props = {"bottle": bottle(), "can": can(), "coins": coins(), "horn": horn_icon()}
    for o in props.values():
        for p in o.data.polygons:
            p.use_smooth = True
    # vendor: the game's stock clerk, with the Vendor_* clips (IK on its own skeleton, retargeted by bind pose in the game)
    varm, vbody = load_character(os.path.join(STAFF, "Staff_Clerk.fbx"), None, "Vendor_Rig", "Vendor_Body")
    vacts = bake_clips(varm, VCLIPS)
    # cooler on the vendor's hip (+X side), strap over the -X shoulder; the bottle in the free hand for the hand-over
    cool.parent = varm; cool.parent_type = 'BONE'; cool.parent_bone = "Torso"
    bpy.context.view_layer.update()
    cool.matrix_world = Matrix.Translation((0.46, -0.02, 0.86)) @ Matrix.Rotation(rad(-90), 4, 'Z') @ Matrix.Scale(1 / ACTOR, 4)
    stats = {"car_tris": tris(car_parts[:-1]), "driver_tris": tris([car_parts[-1]]), "cooler_tris": tris(cool_parts),
             "props": {n: tris([o]) for n, o in props.items()}, "vendor_tris": tris([vbody]),
             "car_bones": [b.name for b in car.data.bones], "cooler_bones": [b.name for b in cool.data.bones],
             "clips": {a.name: (int(a.frame_start), int(a.frame_end)) for a in car_acts + cool_acts + vacts}}
    return dict(car=car, car_parts=car_parts, car_acts=car_acts, cool=cool, cool_parts=cool_parts, cool_acts=cool_acts,
                props=props, varm=varm, vbody=vbody, vacts=vacts, info=info, stats=stats)


# ============================================================================================ review
def street(w=9.0):
    """Road at +Y of the car (the jam lane), kerb and sidewalk at -Y (the driver's side)."""
    m = mats(); c = []
    c.append(k.box("st_road", (w, 4.0, .1), (0, 0.8, -.05), k.mat("EI_asphalt", (.24, .25, .26, 1), rough=.95, var=.18, scale=14, bump=.25), bevel=0))
    c.append(k.box("st_curb", (w, .22, .16), (0, -1.31, .03), k.mat("EI_concrete", (.72, .70, .66, 1), rough=.95, var=.12, scale=9, bump=.2), bevel=.02))
    c.append(k.box("st_sidewalk", (w, 3.0, .13), (0, -2.9, .065), k.pavers("EI_Pavers"), bevel=0))
    for i in range(int(w / 2.4) + 1):
        c.append(k.box("st_dash", (1.2, .12, .005), (-w / 2 + .9 + i * 2.4, 2.4, .002), m["white"], bevel=0))
    return c


def lid(cool, u):
    """Lid opening 0..1 set directly on the Lid bone (the preview mixes it with the vendor clips)."""
    cool.animation_data_create(); cool.animation_data.action = None
    pb = cool.pose.bones["Lid"]; rest = pb.bone.matrix_local.to_quaternion()
    pb.rotation_quaternion = rest.inverted() @ Quaternion(X, rad(-105 * u)) @ rest
    bpy.context.view_layer.update()


def review(S, res=(900, 700)):
    os.makedirs(TMP, exist_ok=True); os.makedirs(REVIEW, exist_ok=True)
    car, cool, varm, vbody, props = S["car"], S["cool"], S["varm"], S["vbody"], S["props"]
    CA = {a.name: a for a in S["car_acts"]}; KA = {a.name: a for a in S["cool_acts"]}; VA = {a.name: a for a in S["vacts"]}
    sc = studio(res=res, ground=False)
    st = street()
    hide = lambda objs, h: [setattr(o, "hide_render", h) for o in objs]
    hide([varm, vbody, cool] + S["cool_parts"] + list(props.values()), True)
    # 1. car: window up (rest) / window down + wave
    shots = []
    for name, act, f in (("window up (rest)", "Car_WindowUp", 18), ("window down - Driver_WaveOut f12", "Driver_WaveOut", 12)):
        if name.startswith("window down"):
            set_action(car, CA["Car_WindowDown"], 18)      # glass down, then the wave on top (the game layers them)
            win = car.pose.bones["Window_Driver"].location.copy()
            set_action(car, CA[act], f); car.pose.bones["Window_Driver"].location = win
            bpy.context.view_layer.update()
        else:
            set_action(car, CA[act], f)
        aim((-0.2, -0.3, 0.75), (-0.55, -1.0, 0.55), 7.5, lens=55)
        label(name, 0.045)
        shots.append(render(os.path.join(TMP, f"win_car_{len(shots)}.png")))
    contact_sheet(shots, os.path.join(REVIEW, "window_car.png"), cols=2)
    # 2. vendor with the open cooler + hand-over at the window
    car.animation_data.action = None
    for pb in car.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
    hide([varm, vbody, cool] + S["cool_parts"], False)
    shots = []
    # 2a. carrying the open cooler, alone
    hide(st, True); hide([car] + S["car_parts"], True)
    studio(res=(1200, 900))
    varm.matrix_world = Matrix.Identity(4)
    set_action(varm, VA["Vendor_WalkCarry"], 9); lid(cool, 1.0)
    aim((0.15, -0.1, 1.2), (0.9, -1.0, 0.35), 5.4, lens=55); label("Vendor_WalkCarry f9 + Cooler_Open", 0.035)
    shots.append(render(os.path.join(TMP, f"win_vendor_{len(shots)}.png")))
    aim((0.3, -0.1, 1.2), (-1.0, -0.6, 0.5), 3.6, lens=60); label("cooler contents (Rig_Cooler, lid open)", 0.035)
    shots.append(render(os.path.join(TMP, f"win_vendor_{len(shots)}.png")))
    # 2b. at the car window: vendor on the sidewalk (scaled like the game's actors), bottle in hand
    hide(st, False); hide([car] + S["car_parts"], False)
    studio(res=(1200, 900))
    gx = S["info"]["W"]((S["info"]["glass"].center.x, 0, 0)).x
    varm.matrix_world = Matrix.Translation((gx + 0.22, -1.62, 0.13)) @ Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Scale(ACTOR, 4)
    set_action(varm, VA["Vendor_HandOver"], 16)
    set_action(car, CA["Car_WindowDown"], 18); win = car.pose.bones["Window_Driver"].location.copy()
    set_action(car, CA["Driver_TakeBottle"], 16); car.pose.bones["Window_Driver"].location = win
    bpy.context.view_layer.update()
    # slide the vendor so that his palm meets the driver's hand (the game places him the same way)
    dh = bone_world(car, "Driver_Hand_L"); dpalm = dh.translation + dh.to_3x3() @ Vector((0, 0.09, 0))
    hand = bone_world(varm, "Hand_R"); vpalm = hand.translation + (hand.to_3x3() @ Vector((0, -0.10, 0)))
    d = dpalm - vpalm; d.z = 0
    varm.matrix_world = Matrix.Translation(d) @ varm.matrix_world
    bpy.context.view_layer.update()
    hand = bone_world(varm, "Hand_R"); vpalm = hand.translation + (hand.to_3x3() @ Vector((0, -0.10, 0)))
    b = props["bottle"]; b.hide_render = False
    mid = (vpalm + dpalm) / 2
    b.matrix_world = Matrix.Translation(mid + Vector((0, 0, -0.12))) @ Matrix.Rotation(rad(-25), 4, 'X')
    S["meet"] = {"driver_palm": [round(v, 3) for v in dpalm], "vendor_palm": [round(v, 3) for v in vpalm]}
    aim((gx + 0.15, -1.05, 0.8), (-0.85, -1.0, 0.6), 7.0, lens=50); label("Vendor_HandOver f16 / Driver_TakeBottle f16 / Car_WindowDown", 0.035)
    shots.append(render(os.path.join(TMP, f"win_vendor_{len(shots)}.png")))
    contact_sheet(shots, os.path.join(REVIEW, "window_vendor.png"), cols=3)
    b.hide_render = True
    # 3. the other clips
    shots = []
    studio(res=(600, 720))
    hide(st, True); hide([car] + S["car_parts"], True)
    varm.matrix_world = Matrix.Identity(4)
    for name, f in (("Vendor_OpenCooler", 24), ("Vendor_TakeBottle", 24), ("Vendor_ReceiveCoin", 18)):
        set_action(varm, VA[name], f)
        lid(cool, 1.0 if name != "Vendor_OpenCooler" else 0.4)
        aim((0.1, -0.2, 1.35), (0.8, -1.0, 0.45), 5.2, lens=55); label(f"{name} f{f}", 0.04)
        shots.append(render(os.path.join(TMP, f"win_pose_{len(shots)}.png")))
    hide([varm, vbody, cool] + S["cool_parts"], True); hide([car] + S["car_parts"], False)
    varm.animation_data.action = None
    for name, f in (("Driver_Honk", 4), ("Driver_WaveOut", 30), ("Driver_Pay", 18), ("Car_HonkBounce", 4)):
        set_action(car, CA["Car_WindowDown"], 18 if name != "Driver_Honk" else 1); win = car.pose.bones["Window_Driver"].location.copy()
        set_action(car, CA[name], f); car.pose.bones["Window_Driver"].location = win; bpy.context.view_layer.update()
        aim((-0.3, -0.5, 0.9), (-0.7, -1.0, 0.5), 5.0, lens=55); label(f"{name} f{f}", 0.04)
        shots.append(render(os.path.join(TMP, f"win_pose_{len(shots)}.png")))
    # props tile
    hide([car] + S["car_parts"], True)
    for i, (n, loc, rot) in enumerate((("bottle", (-0.12, 0, 0), (0, 0, 0)), ("can", (0.0, 0.02, 0), (0, 0, 0)), ("coins", (0.10, -0.03, 0), (0, 0, 0)), ("horn", (0.28, 0.05, 0.02), (0, 0, 0)))):
        o = props[n]; o.hide_render = False; o.matrix_world = Matrix.Translation(loc) @ Euler(rot).to_matrix().to_4x4()
    studio(res=(600, 720), ground=True); bpy.data.objects["QA_Ground"].hide_render = False
    frame_objects(list(props.values()), direction=(0.35, -1.0, 0.55), lens=55, pad=1.25)
    label("Vendor_Bottle / Vendor_Can / Vendor_Coins / Horn_Icon", 0.035)
    shots.append(render(os.path.join(TMP, f"win_pose_{len(shots)}.png")))
    out = contact_sheet(shots, os.path.join(REVIEW, "window_poses.png"), cols=4)
    hide([varm, vbody, cool, car] + S["cool_parts"] + S["car_parts"] + st, False)
    car.animation_data.action = None; varm.animation_data.action = None; cool.animation_data.action = None
    hide_label()
    return out


def save():
    return save_as(os.path.join(HERE, "window_sale.blend"))
