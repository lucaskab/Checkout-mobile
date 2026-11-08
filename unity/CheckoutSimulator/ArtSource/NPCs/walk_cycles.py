"""Rebuilds the LEGS of every walking clip of the game's characters (Lucas 06/11: "the legs move in a strange way").

The characters share one 14-bone skeleton but each body has its own proportions, and the old walks were made for one
of them (or keyed as fixed angles): on some bodies the knee bent backwards, others walked crouched, shuffled, or the
feet slid. Here every walking clip (Walking, WalkingWithBasket, CarryWalking, PushWalking) gets new leg keys solved
for THAT character: its own hip/knee/ankle/heel/ball measured in the rest pose, a two-bone IK with the knee always to
the front, heel strike -> flat foot -> heel off -> toe off, a swing that clears the ground, the hips dipping at the
double support and swaying over the standing foot, and a stride proportional to the leg. The planted foot moves back
at a constant speed, so a game that plays the clip by the distance walked (CheckoutWalkCycle) has no sliding feet.
Arms, head, props and every other clip are kept exactly as they were; the left heel strikes when the right arm
swings forward (taken from the old clip), so arms and legs stay opposite.

Run (Unity project dir):  Blender -b --python ArtSource/NPCs/walk_cycles.py -- preview|export [name ...]
  preview: renders before/after sheets to ArtSource/NPCs/logs/walk_<name>.png (nothing is written to Assets)
  export:  writes the FBX back to the same path with the same object, mesh and take names (Unity keeps its GUIDs)
"""
import bpy, sys, math, json
from pathlib import Path
from mathutils import Vector, Matrix, Euler

ROOT = Path(__file__).resolve().parents[2]
LOGS = Path(__file__).resolve().parent / "logs"
FILES = {
    "Customer_01": "Assets/Art/Characters/Meshy/Customer_01.fbx",
    "Customer_02": "Assets/Art/Characters/Meshy/Customer_02.fbx",
    "Customer_03": "Assets/Art/Characters/Meshy/Customer_03.fbx",
    "Customer_04": "Assets/Art/Characters/Meshy/Customer_04.fbx",
    "Customer_05": "Assets/Art/Characters/Meshy/Customer_05.fbx",
    "Customer_06": "Assets/Art/Characters/Meshy/Customer_06.fbx",
    "Customer_07": "Assets/Art/Characters/Meshy/Customer_07.fbx",
    "Customer_08": "Assets/Art/Characters/Meshy/Customer_08.fbx",
    "Customer_09": "Assets/Art/Characters/Meshy/Customer_09.fbx",
    "Worker_Baker": "Assets/Art/Characters/Meshy/Workers/Worker_Baker.fbx",
    "Worker_Butcher": "Assets/Art/Characters/Meshy/Workers/Worker_Butcher.fbx",
    "Worker_Delivery": "Assets/Art/Characters/Meshy/Workers/Worker_Delivery.fbx",
    "Worker_Fishmonger": "Assets/Art/Characters/Meshy/Workers/Worker_Fishmonger.fbx",
    "Staff_Clerk": "Assets/Art/Staff/Models/Staff_Clerk.fbx",
    "Staff_Cleaner": "Assets/Art/Staff/Models/Staff_Cleaner.fbx",
    "CheckoutWoman": "Assets/Art/Models/MapModels/CheckoutWoman/CheckoutWomanAnimated.fbx",
    "GirlCustomer": "Assets/Art/Models/MapModels/GirlCustomer/GirlCustomerAnimated.fbx",
    "Worker_ConstructionM": "Assets/Resources/CheckoutCrew/Worker_ConstructionM.fbx",
    "Worker_ConstructionF": "Assets/Resources/CheckoutCrew/Worker_ConstructionF.fbx",
}
# stride factor per clip (carrying or pushing: a slightly shorter step)
WALKS = {"Walking": 1.0, "WalkingWithBasket": 1.0, "CarryWalking": .9, "PushWalking": .86}
FWD = Vector((0, -1, 0))      # the characters face -Y in Blender (+Z in Unity)
STANCE = .58                  # share of the cycle a foot is on the ground
CYCLE = 1.15                  # metres walked per cycle (two steps), in leg lengths
CLEAR = .11                   # swing clearance of the ankle, in leg lengths
SWAY = .014                   # hips over the standing foot (m)
REACH = .996                  # the leg never fully locks
HEEL_UP, TOE_DOWN = 14.0, 34.0  # foot pitch at heel strike / toe off (deg)
# Lucas 06/11 (legs open in a V, "como se estivessem assados"): the sculpts stand with the toes turned out 15-30 deg and
# some with the legs apart. In EVERY clip the feet are turned to point (almost) straight ahead, the knee turns with them,
# and a leg that spreads out more than SPLAY_MAX is brought in at the hip. Absolute targets: running it again is harmless.
TOE_OUT = 5.0                 # toes out per foot (deg), a natural stance
SPLAY_MAX = 3.5               # how far the sole may sit outside the hip, as an angle from the hip (deg)
LEG_BONES = ("Thigh", "Shin", "Foot")


def smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def hermite(p0, p1, m0, m1, t):
    t2, t3 = t * t, t * t * t
    return (2*t3 - 3*t2 + 1) * p0 + (t3 - 2*t2 + t) * m0 + (-2*t3 + 3*t2) * p1 + (t3 - t2) * m1


def rot_x(deg):
    return Matrix.Rotation(math.radians(deg), 3, 'X')


def rot_z(deg):
    return Matrix.Rotation(math.radians(deg), 3, 'Z')


def yaw_of(v):                # + = turned towards +X from straight ahead (-Y)
    return math.degrees(math.atan2(v.x, -v.y))


def frame_of(v, pole=FWD):
    u = v.normalized(); n = u.cross(pole).normalized(); return Matrix((u, n, u.cross(n))).transposed()


class Leg:
    def __init__(self, arm, side, meshes):
        b = arm.data.bones
        self.side = side
        self.hip0 = b["Thigh_" + side].head_local.copy()
        self.knee0 = b["Shin_" + side].head_local.copy()
        self.ank0 = b["Foot_" + side].head_local.copy()
        self.a = (self.knee0 - self.hip0).length
        self.b = (self.ank0 - self.knee0).length
        self.L = self.a + self.b
        self.rest = {n: b[n + "_" + side].matrix_local.to_3x3() for n in ("Thigh", "Shin", "Foot")}
        pts = []
        for m in meshes:
            g = m.vertex_groups.get("Foot_" + side)
            if not g: continue
            mw = arm.matrix_world.inverted() @ m.matrix_world
            for v in m.data.vertices:
                for e in v.groups:
                    if e.group == g.index and e.weight > .5: pts.append(mw @ v.co); break
        if len(pts) < 20: raise RuntimeError("no foot vertices " + side)
        self.ground = min(p.z for p in pts)
        low = [p for p in pts if p.z < self.ground + .05]
        # which way the toes point in the sculpt: from the heel to the toe through the sole (the middle of its back tenth to
        # the middle of its front tenth). Lucas 08/11 ("a perna direita dele tá torta ao andar", Customer_09): the old
        # guide, the toe tip seen from the ANKLE, read 10-20 deg too far out on every body because these shoes sit outboard
        # of the ankle, so the feet were turned in too far (pigeon-toed) and the knees with them.
        cx = sum(p.x for p in low) / len(low); cy = sum(p.y for p in low) / len(low)
        ys = sorted(p.y for p in low); k = max(3, len(low) // 10)
        def mid(pts): return Vector((sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts), 0))
        d = (mid([p for p in low if p.y <= ys[k]]) - mid([p for p in low if p.y >= ys[-k - 1]])).normalized()
        self.toe_dir = d                                   # forward along the sole, rest pose
        self.sole0 = Vector((cx, cy, self.ground))
        self.toe_yaw = max(-40.0, min(40.0, yaw_of(d)))   # (a lumpy boot can read wild: never turn more than that)
        out = 1 if self.ank0.x > 0 else -1                 # outwards for this side
        self.target_yaw = TOE_OUT * out
        # turn of the foot about the ankle in every pose (at most 25 deg: more twists the boot out of shape)
        self.fix = max(-25.0, min(25.0, self.target_yaw - self.toe_yaw))
        self.knee_yaw = .5 * self.toe_yaw                  # the sculpted knee faces half way to the toes
        ts = [(p - self.sole0).dot(d) for p in low]
        heel = self.sole0 + d * (min(ts) + .01); toe = self.sole0 + d * max(ts)
        R = rot_z(self.fix)
        self.heel0 = self.ank0 + R @ (heel - self.ank0); self.heel0.z = self.ground
        self.ball0 = self.ank0 + R @ ((toe + .3 * (heel - toe)) - self.ank0); self.ball0.z = self.ground
        self.pole = rot_z(self.target_yaw) @ FWD
        # legs set wider than SPLAY_MAX are brought in at the hip by a fixed angle (constant, so a planted foot stays put)
        splay = math.degrees(math.atan2(self.sole0.x - self.hip0.x, self.hip0.z - self.ground))
        self.adduct = math.radians(splay - max(-SPLAY_MAX, min(SPLAY_MAX, splay)))
        self.rest_pole = rot_z(self.knee_yaw) @ FWD

    # ankle position and foot pitch (deg, + = toe down) at phase p (0 = heel strike), in rest-relative armature space
    def target(self, p, stride, centre):
        ex = STANCE * stride
        def planted(u):          # where a ground point of the foot sits (forward offset) at stance progress u
            return Vector((0, -(ex * (.5 - u) + centre), 0))
        def stance(u):
            T = planted(u)
            if u < .15:
                th = -HEEL_UP * (1 - smooth(u / .15)); piv = self.heel0 + T
            elif u > .62:
                th = TOE_DOWN * smooth((u - .62) / .38); piv = self.ball0 + T
            else:
                return self.ank0 + T, 0.0
            rest_piv = self.heel0 if th < 0 else self.ball0
            return piv + rot_x(th) @ (self.ank0 - rest_piv), th
        if p < STANCE:
            return stance(p / STANCE)
        v = (p - STANCE) / (1 - STANCE)
        a0, th0 = stance(1.0); a1, th1 = stance(0.0)
        vel = -ex / STANCE * (1 - STANCE)            # planted-foot speed, per unit of swing
        y = hermite(a0.y, a1.y, -vel, -vel, v)       # (-Y is forward: the foot came back at +y speed)
        z = a0.z + (a1.z - a0.z) * smooth(v) + CLEAR * self.L * math.sin(math.pi * v) ** .9 * (1 - .25 * v)
        th = th0 + (th1 - th0) * smooth(v)
        return Vector((self.ank0.x, y, z)), th

    def solve(self, H, A):
        d = A - H; dist = min(max(d.length, abs(self.a - self.b) + 1e-4), self.L - 1e-4)
        u = d.normalized(); pole = (self.pole - self.pole.dot(u) * u).normalized()
        ca = max(-1, min(1, (self.a ** 2 + dist ** 2 - self.b ** 2) / (2 * self.a * dist)))
        K = H + self.a * (ca * u + math.sqrt(1 - ca * ca) * pole)
        A2 = H + u * dist
        Rt = frame_of(K - H, self.pole) @ frame_of(self.knee0 - self.hip0, self.rest_pole).transposed()
        Rs = frame_of(A2 - K, self.pole) @ frame_of(self.ank0 - self.knee0, self.rest_pole).transposed()
        return K, A2, Rt, Rs


def straighten(arm, action, legs, report):
    """Every frame of `action`: feet pointing ahead (TOE_OUT), knees with them, legs no wider than SPLAY_MAX."""
    sc = bpy.context.scene; pb = arm.pose.bones
    f0, f1 = [int(round(x)) for x in action.frame_range]
    arm.animation_data.action = action
    if action.slots: arm.animation_data.action_slot = action.slots[0]
    for s in legs:
        for n in LEG_BONES: pb[n + "_" + s].rotation_mode = 'QUATERNION'
    turned, spread = [], []
    # already straight (an earlier run, or a walk made above): only the width is checked
    yaws = {s: [] for s in legs}; splays = {s: [] for s in legs}
    for f in range(f0, f1 + 1, max(1, (f1 - f0) // 8)):
        sc.frame_set(f); bpy.context.view_layer.update()
        for s, leg in legs.items():
            D = pb["Foot_" + s].matrix.to_3x3().normalized() @ leg.rest["Foot"].inverted()
            yaws[s].append(yaw_of(D @ leg.toe_dir))
            sole = pb["Foot_" + s].head + D @ (leg.sole0 - leg.ank0); H = pb["Thigh_" + s].head
            splays[s].append(math.degrees(math.atan2(sole.x - H.x, max(.05, H.z - sole.z))))
    turn = {s: abs(sum(v) / len(v) - leg.target_yaw) > abs(leg.fix) * .5 for s, (leg, v) in ((s, (legs[s], yaws[s])) for s in legs)}
    # the legs come in by a fixed angle for the whole clip, unless they already have (an earlier run)
    narrow = {s: abs(legs[s].adduct) > 1e-4 and abs(sum(v) / len(v)) > SPLAY_MAX + .5 * abs(math.degrees(legs[s].adduct)) for s, v in splays.items()}
    for f in range(f0, f1 + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        feet = {}
        for s, leg in legs.items():
            th, ft = pb["Thigh_" + s], pb["Foot_" + s]
            F0 = ft.matrix.to_3x3().normalized(); D = F0 @ leg.rest["Foot"].inverted()
            toe = D @ leg.toe_dir; toe.z = 0
            H = th.head.copy(); A = ft.head.copy()
            sole = A + D @ (leg.sole0 - leg.ank0)
            splay = math.degrees(math.atan2(sole.x - H.x, max(.05, H.z - sole.z)))
            lim = max(-SPLAY_MAX, min(SPLAY_MAX, splay))
            b = leg.adduct if narrow[s] else 0.0
            R2 = Matrix.Rotation(b, 3, 'Y')
            A2 = H + R2 @ (A - H); u = (A2 - H).normalized()
            T0 = th.matrix.to_3x3().normalized()
            # the knee turns with half of the foot's correction, about the hip-ankle line (the foot stays where it is)
            a = math.radians(.5 * leg.fix) if turn[s] else 0.0
            R1 = Matrix.Rotation(a, 3, u)
            th.matrix = pose_matrix(R1 @ R2 @ T0, H)
            feet[s] = (F0, leg.fix if turn[s] else 0.0)
            spread.append(abs(splay - lim)); turned.append(abs(math.degrees(a)))
        bpy.context.view_layer.update()
        for s, leg in legs.items():
            F0, fix = feet[s]; ft = pb["Foot_" + s]
            ft.matrix = pose_matrix(rot_z(fix) @ F0, ft.head.copy())
        bpy.context.view_layer.update()
        for s in legs:
            for n in ("Thigh", "Foot"):
                b = pb[n + "_" + s]
                b.keyframe_insert(data_path="rotation_quaternion", frame=f); b.keyframe_insert(data_path="location", frame=f)
    report.append({"clip": action.name.split("|")[-1], "turned": [s for s in legs if turn[s]], "kneeTwistMax": round(max(turned or [0]), 1), "spreadFixMax": round(max(spread or [0]), 1)})


def pose_matrix(rot3, head):
    m = rot3.to_4x4(); m.translation = head; return m


def ordered(pb):
    out = []; todo = [b for b in pb if b.parent is None]
    while todo:
        b = todo.pop(0); out.append(b); todo += list(b.children)
    return out


def rebuild(arm, action, factor, meshes, legs, report):
    sc = bpy.context.scene; pb = arm.pose.bones
    f0, f1 = [int(round(x)) for x in action.frame_range]; n = f1 - f0
    arm.animation_data.action = action
    if action.slots: arm.animation_data.action_slot = action.slots[0]
    bones = ordered(pb)
    for b in bones: b.rotation_mode = 'QUATERNION'
    # original channels and the moment the right hand is furthest forward (= left heel strike)
    orig, handR, handL, ankL = [], [], [], []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        orig.append({b.name: (b.location.copy(), b.rotation_quaternion.copy(), b.scale.copy()) for b in bones})
        handR.append(-pb["Hand_R"].head.y); handL.append(-pb["Hand_L"].head.y); ankL.append(-pb["Foot_L"].head.y)
    swing = max(handR) - min(handR)
    key = handR if swing > .04 else ankL
    hs = key.index(max(key))
    stride = CYCLE * sum(l.L for l in legs.values()) / 2 * factor / 2              # one step (half a cycle)
    ex_cycle = stride * 2
    phase = lambda f, side: ((f - f0 - hs) / n + (0 if side == "L" else .5)) % 1.0
    torso = pb["Torso"]; t0 = arm.data.bones["Torso"].head_local.copy()
    centre = .02

    def set_channels(i):
        for b in bones:
            b.location, b.rotation_quaternion, b.scale = orig[i][b.name]

    def place_torso(offset):
        rot = torso.matrix.to_3x3()
        torso.matrix = pose_matrix(rot, t0 + offset)

    # pass 1: how high may the hips be at each frame
    raw = []
    for i, f in enumerate(range(f0, f1 + 1)):
        sc.frame_set(f); set_channels(i); bpy.context.view_layer.update()
        place_torso(Vector()); bpy.context.view_layer.update()
        dz = 1e9
        for s, leg in legs.items():
            p = phase(f, s); A, _ = leg.target(p, ex_cycle, centre)
            H = pb["Thigh_" + s].head
            reach = REACH * leg.L if p < STANCE else .999 * leg.L
            h2 = (A.x - H.x) ** 2 + (A.y - H.y) ** 2
            dz = min(dz, A.z + math.sqrt(max(reach * reach - h2, 1e-6)) - H.z)
        raw.append(min(dz, 0.0))
    mean = sum(raw) / len(raw)
    hip = [min(r, mean + .75 * (r - mean)) for r in raw]
    hip = [min(raw[i], (hip[i - 1] + 2 * hip[i] + hip[(i + 1) % len(hip)]) / 4) for i in range(len(hip))]
    hip[-1] = hip[0]

    new = bpy.data.actions.new(action.name + "_new")
    arm.animation_data.action = new
    knees = []
    for i, f in enumerate(range(f0, f1 + 1)):
        sc.frame_set(f); set_channels(i); bpy.context.view_layer.update()
        pL = phase(f, "L")
        sway = -SWAY * math.cos(2 * math.pi * (pL - STANCE / 2))
        place_torso(Vector((sway, 0, hip[i]))); bpy.context.view_layer.update()
        sol = {}
        for s, leg in legs.items():
            A, th = leg.target(phase(f, s), ex_cycle, centre)
            H = pb["Thigh_" + s].head.copy()
            K, A2, Rt, Rs = leg.solve(H, A)
            sol[s] = (K, A2, Rt, Rs, th)
            pb["Thigh_" + s].matrix = pose_matrix(Rt @ leg.rest["Thigh"], H)
            knees.append(math.degrees((K - H).angle(A2 - K)))
        bpy.context.view_layer.update()
        for s, leg in legs.items():
            K, A2, Rt, Rs, th = sol[s]
            pb["Shin_" + s].matrix = pose_matrix(Rs @ leg.rest["Shin"], pb["Shin_" + s].head.copy())
        bpy.context.view_layer.update()
        for s, leg in legs.items():
            th = sol[s][4]
            pb["Foot_" + s].matrix = pose_matrix(rot_x(th) @ rot_z(leg.fix) @ leg.rest["Foot"], pb["Foot_" + s].head.copy())
        bpy.context.view_layer.update()
        for b in bones:
            for path in ("location", "rotation_quaternion", "scale"):
                b.keyframe_insert(data_path=path, frame=f)
    # loop seam: the last frame equals the first
    name = action.name
    action.name = name + "_old"; new.name = name
    bpy.data.actions.remove(action)
    for fc in getattr(new, "fcurves", []):
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    # what the game will measure (CheckoutWalkCycle): the speed of a foot while it is flat on the ground, per cycle
    S = 64; track = {"L": [], "R": []}
    for i in range(S):
        t = f0 + n * i / S; sc.frame_set(int(t), subframe=t - int(t))
        for s in "LR": track[s].append(pb["Foot_" + s].head.copy())
    speeds = []
    for s in "LR":
        lo = min(p.z for p in track[s]); hi = max(p.z for p in track[s]); flat = lo + max(.003, (hi - lo) * .03)
        for i in range(S):
            p, q = track[s][i], track[s][(i + 1) % S]
            if p.z <= flat and q.z <= flat: speeds.append(abs(q.y - p.y) * S)
    speeds.sort(); pushed = speeds[len(speeds) // 2] if speeds else 0
    report.append({"measured": round(pushed, 3), "clip": name.split("|")[-1], "frames": [f0, f1], "stepModel": round(stride, 3),
                   "cycleModel": round(ex_cycle, 3), "kneeMax": round(max(knees)), "kneeMin": round(min(knees)),
                   "hipDrop": round(-min(hip), 3), "armSwing": round(swing, 3), "heelStrikeFrame": f0 + hs})
    return new


SOURCE = None    # "--from <dir>": read <dir>/<name>.fbx (e.g. untouched copies) instead of the game's file


def load(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    src = Path(SOURCE) / f"{name}.fbx" if SOURCE else ROOT / FILES[name]
    bpy.ops.import_scene.fbx(filepath=str(src), use_anim=True)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    return arm, meshes


def walk_actions(arm):
    out = []
    for a in bpy.data.actions:
        clip = a.name.split("|")[-1]
        if clip in WALKS and a.name.startswith(arm.name + "|"): out.append((a, WALKS[clip]))
    return out


def sheet(arm, clips, path, legs=False):
    import numpy as np
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'OBJECT'
    W, H = (170, 150) if legs else (150, 210); sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    cd = bpy.data.cameras.new("cam"); cd.type = 'ORTHO'; cd.ortho_scale = 1.45 if legs else 2.9
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    me = bpy.data.meshes.new("floor"); me.from_pydata([(-9, -9, 0), (9, -9, 0), (9, 9, 0), (-9, 9, 0)], [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new("floor", me); sc.collection.objects.link(fl); fl.color = (.35, .4, .45, 1)
    for o in bpy.data.objects:
        if o.type == 'MESH' and o is not fl: o.color = (.85, .72, .55, 1)
    rows = []
    tmp = str(LOGS / "_tile.png")
    for act in clips:
        arm.animation_data.action = act
        if act.slots: arm.animation_data.action_slot = act.slots[0]
        f0, f1 = act.frame_range; n = f1 - f0; tiles = []
        for view, cnt in ((("side", 10),) if legs else (("side", 8), ("front", 3))):
            for i in range(cnt):
                f = f0 + n * i / cnt; sc.frame_set(int(f), subframe=f - int(f))
                if view == "side": cam.location = (6, 0, .62 if legs else 1.2); cam.rotation_euler = Euler((math.pi / 2, 0, math.pi / 2))
                else: cam.location = (0, -6, 1.2); cam.rotation_euler = Euler((math.pi / 2, 0, 0))
                sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
                img = bpy.data.images.load(tmp, check_existing=False)
                tiles.append(np.array(img.pixels[:]).reshape(H, W, 4)); bpy.data.images.remove(img)
        rows.append(np.concatenate(tiles, axis=1))
    s = np.concatenate(rows[::-1], axis=0); h, w = s.shape[:2]
    im = bpy.data.images.new("sheet", w, h); im.pixels = s.ravel(); im.filepath_raw = str(path); im.file_format = 'PNG'; im.save()


def process(name, mode):
    arm, meshes = load(name)
    names = {o.name: (o.type, o.data.name if o.data else None) for o in bpy.data.objects}
    legs = {s: Leg(arm, s, meshes) for s in "LR"}
    walks = walk_actions(arm)
    report = []
    before = []
    if mode == "preview":
        for a, _ in walks:
            c = a.copy(); c.name = a.name + "_before"; before.append(c)
    for a, factor in walks:
        rebuild(arm, a, factor, meshes, legs, report)
    fixed = []
    for a in [a for a in bpy.data.actions if a.name.startswith(arm.name + "|") and not a.name.endswith("_before")]:
        straighten(arm, a, legs, fixed)
    arm.animation_data.action = None
    info = {"name": name, "legLength": round(legs["L"].L, 3), "clips": report, "straightened": fixed,
            "toeYawRest": {s: round(l.toe_yaw, 1) for s, l in legs.items()}}
    if mode == "preview":
        after = [bpy.data.actions[a.name[:-7]] for a in before]
        pairs = [x for ab in zip(before, after) for x in ab]
        sheet(arm, pairs, LOGS / f"walk_{name}.png")
        sheet(arm, pairs, LOGS / f"walk_{name}_legs.png", legs=True)
        for a in bpy.data.actions: a.use_fake_user = True
        bpy.ops.wm.save_as_mainfile(filepath=str(LOGS / f"walk_{name}.blend"))
    else:
        # take = <object>|<action>: keep the original take names Unity's clip settings point to
        prefix = arm.name + "|"
        takes = {}
        for a in list(bpy.data.actions):
            if not a.name.startswith(prefix): continue
            take = a.name[len(prefix):]
            takes[a] = take
        heads = {t.split("|")[0] for t in takes.values()}
        if len(heads) != 1: raise RuntimeError(f"mixed take prefixes {heads}")
        head = heads.pop()
        arm.name = head
        for a, take in takes.items(): a.name = take.split("|", 1)[1]
        for o, (t, d) in names.items():
            if o not in bpy.data.objects: raise RuntimeError("renamed object " + o)
        bpy.ops.object.select_all(action='DESELECT')
        for o in bpy.data.objects:
            if o.type in ('ARMATURE', 'MESH'): o.select_set(True)
        bpy.context.view_layer.objects.active = arm
        target = ROOT / FILES[name] if mode == "export" else LOGS / "trial" / Path(FILES[name]).name
        target.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.fbx(filepath=str(target), use_selection=True, object_types={'ARMATURE', 'MESH'},
                                 add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True,
                                 bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0, axis_forward='-Z',
                                 axis_up='Y', path_mode='STRIP')
        info["objects"] = sorted(names); info["takes"] = sorted(head + "|" + a.name for a in takes)
        info["check"] = verify(name, target)
    print("WALK_CYCLE", json.dumps(info), flush=True)
    return info


def verify(name, exported):
    """Re-imports the original and the new FBX: same objects, meshes, bones and takes; non-walking clips unchanged."""
    def grab(path):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
        arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        out = {"objects": sorted((o.name, o.type, len(o.data.vertices) if o.type == 'MESH' else len(o.data.bones)) for o in bpy.data.objects),
               "takes": {}, "fps": bpy.context.scene.render.fps}
        pb = arm.pose.bones
        for a in bpy.data.actions:
            arm.animation_data.action = a
            if a.slots: arm.animation_data.action_slot = a.slots[0]
            f0, f1 = a.frame_range; poses = []
            for f in (f0, (f0 + f1) / 2, f1):
                bpy.context.scene.frame_set(int(f), subframe=f - int(f))
                poses.append([tuple(round(x, 3) for x in b.head) + tuple(round(x, 3) for x in b.tail) for b in pb
                              if not any(b.name.startswith(n + "_") for n in LEG_BONES) and b.name != "Torso"])
            out["takes"][a.name.split("|", 1)[1]] = (round(f0, 2), round(f1, 2), poses)
        return out
    old = grab(ROOT / FILES[name]); new = grab(exported)
    problems = []
    if old["objects"] != new["objects"]: problems.append(f"objects {old['objects']} -> {new['objects']}")
    if old["fps"] != new["fps"]: problems.append(f"fps {old['fps']} -> {new['fps']}")
    if sorted(old["takes"]) != sorted(new["takes"]): problems.append(f"takes {sorted(old['takes'])} -> {sorted(new['takes'])}")
    changed = []
    for take, (f0, f1, poses) in old["takes"].items():
        if take not in new["takes"]: continue
        n0, n1, nposes = new["takes"][take]
        if (f0, f1) != (n0, n1): problems.append(f"range {take} {f0}-{f1} -> {n0}-{n1}")
        if poses != nposes and take.split("|")[-1] not in WALKS:
            # arms, head, props: within half a centimetre (the legs and the hips may move)
            worst = max(abs(x - y) for p, q in zip(poses, nposes) for bp, bq in zip(p, q) for x, y in zip(bp, bq))
            if worst > .006: changed.append(take.split("|")[-1])
    walk = sorted(c for c in changed if c in WALKS); other = sorted(c for c in changed if c not in WALKS)
    if other: problems.append(f"non-walking clips changed {other}")
    return {"ok": not problems, "problems": problems, "walksChanged": walk}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    global SOURCE
    if "--from" in argv:
        i = argv.index("--from"); SOURCE = argv[i + 1]; del argv[i:i + 2]
    mode = argv[0] if argv else "preview"
    names = argv[1:] or list(FILES)
    LOGS.mkdir(exist_ok=True)
    out = []
    for n in names:
        try: out.append(process(n, mode))
        except Exception as e:
            import traceback; traceback.print_exc(); out.append({"name": n, "error": str(e)})
    (LOGS / f"walk_cycles_{mode}.json").write_text(json.dumps(out, indent=1) + "\n")
    print("WALK_CYCLES_DONE", flush=True)


if __name__ == "__main__":
    main()
