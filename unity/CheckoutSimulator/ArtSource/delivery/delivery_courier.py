"""delivery_courier.py -- the GAME'S delivery worker (Worker_Delivery.fbx) as the motoboy (Oct 2026).
import_courier() brings in the shipped rig + 24k-tri textured body (Worker_Delivery.png), build_helmet() adds a clean
full-face helmet bone-parented to the Head bone, pose_ride() seats it on the bike (hands on the grips, feet on the pegs)
and pose_stand_bag() makes the standing hand-over pose holding the thermal bag.  Poses are solved analytically (2-bone IK)
and written as bone matrices, so the model stays a normal skinned mesh.  PREVIEW only (nothing is exported)."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Euler

WORKER_DIR = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets\Art\Characters\Meshy\Workers"
FBX = WORKER_DIR + r"\Worker_Delivery.fbx"; TEX = WORKER_DIR + r"\Worker_Delivery.png"
CS = 0.72          # game worker is 2.4 units tall -> 1.73 m rider
TEAL_H, ORANGE_H = "#12847E", "#EA7B1D"

def courier_material():
    m = bpy.data.materials.get("DK_courier")
    if m: return m
    m = bpy.data.materials.new("DK_courier"); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    t = nt.nodes.new("ShaderNodeTexImage"); img = bpy.data.images.get("Worker_Delivery.png") or bpy.data.images.load(TEX); img.colorspace_settings.name = 'sRGB'; t.image = img; t.interpolation = 'Cubic'
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .58
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = .35
    bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(t.outputs["Color"], bw.inputs["Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .25; bp.inputs["Distance"].default_value = .004
    nt.links.new(bw.outputs["Val"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def import_courier(tag, loc=(0, 0, 0), yaw=0., scale=CS, parent=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=FBX)
    new = set(bpy.data.objects) - before
    rig = next(o for o in new if o.type == 'ARMATURE'); body = next(o for o in new if o.type == 'MESH')
    for o in new:
        if o not in (rig, body): bpy.data.objects.remove(o, do_unlink=True)
    rig.name = tag + "_rig"; body.name = tag + "_body"
    if rig.animation_data: rig.animation_data_clear()      # the FBX ships baked clips that would override the pose every frame
    for a in [a for a in bpy.data.actions if a.users == 0]: bpy.data.actions.remove(a)
    body.data.materials.clear(); body.data.materials.append(courier_material())
    for p in body.data.polygons: p.use_smooth = True
    rig.rotation_mode = 'XYZ'; rig.rotation_euler = (0, 0, yaw); rig.scale = (scale,) * 3; rig.location = loc
    if parent is not None: rig.parent = parent
    for pb in rig.pose.bones: pb.rotation_mode = 'XYZ'
    bpy.context.view_layer.update(); return rig, body

def upd(): bpy.context.view_layer.update()
def rest3(rig, name): return rig.data.bones[name].matrix_local.to_3x3()
def rhead(rig, name): return rig.data.bones[name].head_local.copy()
def to_arm(rig, world): return rig.matrix_world.inverted() @ Vector(world)
def Rx(a): return Matrix.Rotation(math.radians(a), 3, 'X')
def Ry(a): return Matrix.Rotation(math.radians(a), 3, 'Y')
def Rz(a): return Matrix.Rotation(math.radians(a), 3, 'Z')

def set_bone(rig, name, head, R3):
    """R3 = rotation (armature space) applied on top of the bone's rest orientation; head = armature-space head position."""
    pb = rig.pose.bones[name]; pb.matrix = Matrix.Translation(head) @ (R3 @ rest3(rig, name)).to_4x4(); upd(); return pb

def rotdiff(a, b): return a.normalized().rotation_difference(b.normalized()).to_matrix()

def ik2(rig, upper, lower, end, target, pole, min_ext=1e-3):
    """Analytic 2-bone IK in armature space: joints = bone heads (upper head, lower head, end head)."""
    pa, pb_, pc = rhead(rig, upper), rhead(rig, lower), rhead(rig, end)
    la, lb = (pb_ - pa).length, (pc - pb_).length
    A = rig.pose.bones[upper].head.copy(); T = Vector(target); d = T - A; dist = d.length
    reach = la + lb - min_ext
    clamped = dist > reach
    if clamped: T = A + d.normalized() * reach; dist = reach; d = T - A
    n = d.normalized(); x = (la * la - lb * lb + dist * dist) / (2 * dist); h = math.sqrt(max(la * la - x * x, 0))
    pv = Vector(pole); pv = (pv - n * pv.dot(n)).normalized()
    K = A + n * x + pv * h
    set_bone(rig, upper, A, rotdiff(pb_ - pa, K - A)); set_bone(rig, lower, K, rotdiff(pc - pb_, T - K))
    return K, T, clamped

def end_bone(rig, lower, end, T, extra=None):
    """Hand/foot: inherits the lower bone's rotation, plus `extra` (armature-space rotation about the wrist/ankle)."""
    pbl = rig.pose.bones[lower]; delta = pbl.matrix.to_3x3() @ rest3(rig, lower).inverted()
    R = (extra if extra is not None else Matrix.Identity(3)) @ delta
    return set_bone(rig, end, T, R)

def reset_pose(rig):
    for pb in rig.pose.bones: pb.location = (0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    upd()

# ------------------------------------------------------------------ helmet
def build_helmet(rig, tag="courier"):
    reset_pose(rig)
    """Clean full-face helmet (teal shell, dark bubble visor, chin guard, orange stripe) bone-parented to Head.  Built at REST."""
    m = M(); s = rig.scale[0]
    teal = mat("helm_teal", srgb(TEAL_H), "paint", rough=.18, coat=1., wear=.12, scale=40, prefix="DK_")
    org = mat("helm_org", srgb(ORANGE_H), "paint", rough=.25, coat=.8, wear=.1, scale=40, prefix="DK_")
    vis = mat("helm_visor", (0.012, 0.02, 0.03, 1), "plastic", rough=.22, metal=0., coat=.5, bump=0, rand=0, prefix="DK_")
    rim = mat("helm_rim", (0.012, 0.016, 0.02, 1), "rubber", rough=.7, bump=.1, spec=.2, rand=0, prefix="DK_")
    glossy = mat("helm_shine", (0.9, 0.95, 1.0, 1), "plastic", rough=.05, coat=1., emit=.0, bump=0, rand=0, prefix="DK_")
    liner = mat("helm_pad", (0.10, 0.11, 0.12, 1), "fabric", rough=.9, bump=.4, scale=60, prefix="DK_")
    W = lambda p: rig.matrix_world @ Vector(p)
    H = Vector((0, .08, 2.20)); parts = []
    MW = rig.matrix_world
    def sph(nm, c, r, sc, mm, seg=64, ss=2):
        o = sphere(nm, r * s, W(c), mm, scale=sc, seg=seg, ss=ss, rot=tuple(MW.to_euler())); parts.append(o); return o
    def patch(nm, c, rad, az, el, grow, mm, thick=.004, seg=(96, 48)):
        """Window of an ellipsoid shell (radii rad, centre c in armature rest space), az = +-deg from the front (-Y), el = (lo, hi) deg."""
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0)
        dele = []
        for f in bm.faces:
            d = f.calc_center_median(); l = d.length; d = d / l
            azf = math.degrees(math.atan2(d.x, -d.y)); elf = math.degrees(math.asin(max(-1, min(1, d.z))))
            if not (abs(azf) <= az and el[0] <= elf <= el[1]): dele.append(f)
        bmesh.ops.delete(bm, geom=dele, context='FACES')
        for v in bm.verts:
            u = v.co.copy()
            v.co = MW @ (Vector(c) + Vector((u.x * rad[0], u.y * rad[1], u.z * rad[2])) * grow)
        me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(nm, me); bpy.context.scene.collection.objects.link(o); me.materials.append(mm)
        for q in me.polygons: q.use_smooth = True
        sd = o.modifiers.new("solid", 'SOLIDIFY'); sd.thickness = thick * s; sd.offset = 1.0
        ss_ = o.modifiers.new("ss", 'SUBSURF'); ss_.levels = 0; ss_.render_levels = 1
        parts.append(o); return o
    RAD = (.26, .31, .335); HS = Vector((0, .08, 2.125))       # deep shell: the lower front is the chin guard
    sph(tag + "_helm_shell", HS, 1.0, RAD, teal, 56, 2)
    sph(tag + "_helm_neck_pad", Vector((0, .07, 1.86)), .20, (.80, .90, .22), liner, 32, 1)
    sph(tag + "_helm_stripe", HS, 1.0, (.025, RAD[1] + .004, RAD[2] + .004), org, 56, 2)
    patch(tag + "_helm_visor_rim", HS, RAD, 69, (-9, 33), 1.008, rim, .008)
    patch(tag + "_helm_visor", HS, RAD, 66, (-6, 30), 1.024, vis, .008)
    for sd in (-1, 1):
        sph(tag + f"_helm_pivot_cap{sd}", HS + Vector((sd * .243, -.06, .06)), .03, (.18, 1, 1), org, 24, 1)
    sph(tag + "_helm_chin_vent", HS + Vector((0, -.285, -.19)), .05, (1.0, .22, .34), rim, 24, 1)
    # re-collect every object just created (sphere() returns the object; parts list kept for the loose ones above)
    helm = [o for o in bpy.context.scene.objects if o.name.startswith(tag + "_helm")]
    rig_pb = rig.pose.bones["Head"]; inv = (rig.matrix_world @ rig_pb.matrix @ Matrix.Translation((0, rig_pb.bone.length, 0))).inverted()   # Blender parents to the bone TAIL
    for o in helm:
        o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = "Head"; o.matrix_parent_inverse = inv
    return helm

# ------------------------------------------------------------------ poses
def end_abs(rig, name, T, R3):
    """Place an end bone (hand/foot) with an absolute armature-space rotation relative to its rest orientation."""
    return set_bone(rig, name, T, R3)

def side_sign(rig, root, sd):
    """+1 / -1: which side of the bike (local y) a bone side lies on."""
    return 1 if (root.matrix_world.inverted() @ (rig.matrix_world @ rig.pose.bones["UpperArm_" + sd].head)).y > 0 else -1

def pose_ride(rig, root, hip=(-0.30, 0, 0.98), lean=36., grips=None, pegs=None, wrist_off=(-.035, 0, .03), ankle_off=(-.10, 0, .15), hand_rot=(0, 0, 0), foot_pitch=-6., head_pitch=10.):
    """Seated pose (bike-local frame: x forward, y left, z up; root = bike root empty). grips / pegs: {+1: p, -1: p} keyed by y sign."""
    grips = grips or {1: (0.31, .32, .985), -1: (0.31, -.32, .985)}; pegs = pegs or {1: (-0.08, .165, .345), -1: (-0.08, -.165, .345)}
    reset_pose(rig); Rm = root.matrix_world; A = lambda p: to_arm(rig, Rm @ Vector(p))
    set_bone(rig, "Torso", A(hip), Rx(lean))
    set_bone(rig, "Head", rig.pose.bones["Head"].head.copy(), Rx(head_pitch))
    info = {}
    for sd in ("L", "R"):
        sy = side_sign(rig, root, sd); sx = 1 if sd == "R" else -1
        g = Vector(grips[sy]) + Vector(wrist_off)
        K, T, cl = ik2(rig, "UpperArm_" + sd, "Forearm_" + sd, "Hand_" + sd, A(g), Vector((sx * .7, .25, -.6)))
        end_bone(rig, "Forearm_" + sd, "Hand_" + sd, T, Rx(hand_rot[0]) @ Ry(hand_rot[1]) @ Rz(hand_rot[2]))
        pg = Vector(pegs[sy]) + Vector(ankle_off)
        K2, T2, cl2 = ik2(rig, "Thigh_" + sd, "Shin_" + sd, "Foot_" + sd, A(pg), Vector((sx * .35, -1, .5)))
        end_abs(rig, "Foot_" + sd, T2, Rx(foot_pitch))
        info[sd] = dict(side=sy, arm_clamped=cl, leg_clamped=cl2)
    return info

def pose_stand_bag(rig, hands_world, lean=4., head_pitch=4., elbow_pole=(.8, .4, -.5), hand_rot=(0, 0, 0)):
    """Standing, both hands at the given WORLD points (dict {'L': p, 'R': p}); legs straight, slight forward lean."""
    reset_pose(rig); upd()
    set_bone(rig, "Torso", rig.pose.bones["Torso"].head.copy(), Rx(lean))
    set_bone(rig, "Head", rig.pose.bones["Head"].head.copy(), Rx(head_pitch))
    info = {}
    for sd in ("L", "R"):
        sx = 1 if sd == "R" else -1
        K, T, cl = ik2(rig, "UpperArm_" + sd, "Forearm_" + sd, "Hand_" + sd, to_arm(rig, hands_world[sd]), Vector((sx * elbow_pole[0], elbow_pole[1], elbow_pole[2])))
        end_bone(rig, "Forearm_" + sd, "Hand_" + sd, T, Rx(hand_rot[0]) @ Ry(hand_rot[1] * sx) @ Rz(hand_rot[2] * sx)); info[sd] = cl
    return info

# ------------------------------------------------------------------ thermal delivery bag (hand-over prop) + standing courier
def courier_bag(name, loc=(0, 0, 0), yaw=0., size=(.42, .30, .30), parent=None):
    """Quilted blue nylon thermal bag with orange band, zipper lid, carry handle and the printed market decal (same art as the bau)."""
    global ROOT
    m = M(); W, D, H = size
    ny = mat("bag_nylon", BLUE, "nylon", rough=.68, bump=.7, scale=22, wear=.1, dirt=.08, prefix="DK_")
    nyd = mat("bag_nylon_d", BLUE_D, "nylon", rough=.7, bump=.6, scale=22, prefix="DK_")
    bpy.ops.object.empty_add(location=loc, rotation=(0, 0, yaw)); e = bpy.context.object; e.name = name
    if parent is not None: e.parent = parent
    saved = ROOT; ROOT = e
    box(name + "_body", (W, D, H), (0, 0, H / 2), ny, bev=.03, seg=5, ss=1)
    box(name + "_lid", (W + .012, D + .012, .07), (0, 0, H + .028), nyd, bev=.026, seg=5, ss=1)
    box(name + "_zip", (W + .016, D + .016, .012), (0, 0, H - .004), m["zipper"], bev=.004)
    for sx in (-1, 1): box(name + f"_zip_end{sx}", (.02, D + .02, .018), (sx * (W / 2 - .002), 0, H), m["black"], bev=.006)
    cyl(name + "_zip_pull", .012, .03, (W / 2 - .09, -D / 2 - .012, H + .004), m["zipper"], axis='Y', verts=14)
    curve_tube(name + "_zip_tag", [(W / 2 - .09, -D / 2 - .022, H + .004), (W / 2 - .07, -D / 2 - .05, H - .02), (W / 2 - .065, -D / 2 - .06, H - .06)], .004, m["orange"])
    for k, (dx, dy, face) in enumerate(((0, -D / 2 - .004, 'y'), (0, D / 2 + .004, 'y'))):   # orange band + reflective strip front/back
        box(name + f"_band{k}", (W + .004, .008, .05), (0, dy, H * .30), m["orange"], bev=.003)
        box(name + f"_refl{k}", (W + .006, .009, .012), (0, dy * 1.001, H * .30 + .034), m["stripe"], bev=.002)
    for sx in (-1, 1):
        box(name + f"_sband{sx}", (.008, D + .004, .05), (sx * (W / 2 + .004), 0, H * .30), m["orange"], bev=.003)
        rbox(name + f"_pocket{sx}", (.016, .12, .14), (sx * (W / 2 + .008), .02, H * .50), nyd, seg=4, ss=1)
        box(name + f"_pzip{sx}", (.006, .11, .01), (sx * (W / 2 + .018), .02, H * .50 + .06), m["zipper"], bev=.002)
    # handle: webbing loop over the lid + padded grip + base tabs
    curve_tube(name + "_handle", [(-.10, -.02, H + .05), (-.09, -.03, H + .10), (0, -.03, H + .125), (.09, -.03, H + .10), (.10, -.02, H + .05)], .011, m["orange"], res=14)
    rbox(name + "_handle_pad", (.11, .03, .026), (0, -.03, H + .127), nyd, seg=4, ss=1)
    for sx in (-1, 1): box(name + f"_handle_tab{sx}", (.04, .05, .008), (sx * .10, -.02, H + .06), nyd, bev=.003)
    # printed decals + stitching
    vin = decal_mat("bau_logo_fab", D_img("bau_logo"), rough=.62, spec=.3)
    decal_plane(name + "_decal_f", .24, .24 * 700 / 900, (0, -D / 2 - .0065, H * .72), (rad(90), 0, 0), vin, e)
    decal_plane(name + "_decal_b", .24, .24 * 700 / 900, (0, D / 2 + .0065, H * .72), (rad(90), 0, rad(180)), vin, e)
    stitches(name + "_st_f", [(-W / 2 + .03, -D / 2 - .003, H - .035), (W / 2 - .03, -D / 2 - .003, H - .035)], m["thread_w"], step=.014, r=.0009, length=.006)
    stitches(name + "_st_f2", [(-W / 2 + .03, -D / 2 - .003, .035), (W / 2 - .03, -D / 2 - .003, .035)], m["thread_w"], step=.014, r=.0009, length=.006)
    stitches(name + "_st_l", [(-W / 2 - .003, -D / 2 + .03, H - .035), (-W / 2 - .003, D / 2 - .03, H - .035)], m["thread_w"], step=.014, r=.0009, length=.006)
    rbox(name + "_foot0", (.07, .05, .012), (-W / 2 + .06, -D / 2 + .05, .004), m["black"], seg=3, ss=1); rbox(name + "_foot1", (.07, .05, .012), (W / 2 - .06, -D / 2 + .05, .004), m["black"], seg=3, ss=1)
    ROOT = saved
    return e

def add_standing_courier(tag, loc=(0, 0, 0), yaw=0., with_bag=True, parent=None, helmet=False, bag_offset=(0, -.30, .95)):
    """Standing courier facing local -Y rotated by `yaw` (world), holding the thermal bag in both hands at bag_offset (courier-local frame)."""
    rig, body = import_courier(tag, loc=loc, yaw=yaw, parent=parent)
    if helmet: build_helmet(rig, tag)
    Mrig = rig.matrix_world
    # courier-local (x right, y forward = -Y of the rig frame) -> world
    def Wp(p): return Mrig @ Vector((p[0] / rig.scale[0], p[1] / rig.scale[0], p[2] / rig.scale[0]))
    c = Vector(bag_offset)
    bag = None
    if with_bag:
        bag_loc = Mrig @ Vector((c.x / rig.scale[0], c.y / rig.scale[0], 0)); bag_loc.z = loc[2] + c.z - .15
        bag = courier_bag(tag + "_bag", loc=bag_loc, yaw=yaw, parent=None)   # decal side faces away from the courier (viewer / counter)
    hands = {"R": Wp((c.x + .245, c.y, c.z - .02)), "L": Wp((c.x - .245, c.y, c.z - .02))}
    info = pose_stand_bag(rig, hands, lean=5., head_pitch=0., elbow_pole=(.9, .5, -.4), hand_rot=(0, 0, 0))
    return rig, body, bag, info
