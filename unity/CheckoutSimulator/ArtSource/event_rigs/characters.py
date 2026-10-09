"""Event moves for the game's own characters (every customer and worker shares the Customer_01_Rig skeleton:
Torso, Head, Thigh/Shin/Foot, UpperArm/Forearm/Hand, Prop). The clips are keyed on that skeleton and exported
without a mesh to Assets/Resources/EventRigs/EventMoves.fbx; in the game CheckoutEventMoves samples a clip on
that skeleton and copies the bones onto any character (arms-only clips keep the character's own walk on the legs).

Axes (armature space): the characters face -Y, +Z is up. The rig's L/R names are mirrored, so sides are taken
from the bone position (s = +1 for the arm at +X).
"""
import math
from mathutils import Vector, Quaternion, Matrix

CHAR = "Customer_06"
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
CLIPS = {}
STEP = 2           # a pose is solved every 2 frames (IK keeps feet and hands where they belong)


def clip(name, frames, arms_only=False):
    def deco(fn):
        CLIPS[name] = (frames, fn, arms_only)
        return fn
    return deco


def ss(a, b, x):
    """smoothstep"""
    t = max(0.0, min(1.0, (x - a) / (b - a))) if b != a else 0.0
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return a + (b - a) * t


def V(x, y, z):
    return Vector((x, y, z))


class Rig:
    """Rest-pose measurements of the skeleton (character space: faces -Y, +Z up)."""
    def __init__(self, arm):
        self.arm = arm
        B = arm.data.bones
        self.side = lambda n: 1 if B[n].head_local.x > 0 else -1
        self.ua = {self.side(b.name): b.name for b in B if b.name.startswith("UpperArm")}
        self.fa = {s: n.replace("UpperArm", "Forearm") for s, n in self.ua.items()}
        self.hd = {s: n.replace("UpperArm", "Hand") for s, n in self.ua.items()}
        self.th = {s: n.replace("UpperArm", "Thigh") for s, n in self.ua.items()}
        self.sh = {s: n.replace("UpperArm", "Shin") for s, n in self.ua.items()}
        self.ft = {s: n.replace("UpperArm", "Foot") for s, n in self.ua.items()}
        h = lambda n: B[n].head_local.copy()
        self.pivot = h("Torso")
        self.shoulder = {s: h(self.ua[s]) for s in (1, -1)}
        self.elbow = {s: h(self.fa[s]) for s in (1, -1)}
        self.wrist = {s: h(self.hd[s]) for s in (1, -1)}
        self.hip = {s: h(self.th[s]) for s in (1, -1)}
        self.knee = {s: h(self.sh[s]) for s in (1, -1)}
        self.ankle = {s: h(self.ft[s]) for s in (1, -1)}
        self.l_ua = (self.elbow[1] - self.shoulder[1]).length
        self.l_fa = (self.wrist[1] - self.elbow[1]).length
        self.l_th = (self.knee[1] - self.hip[1]).length
        self.l_sh = (self.ankle[1] - self.knee[1]).length


def two_bone(a, target, l1, l2, pole):
    """Joint position of a two-bone limb from `a` reaching `target`, bending towards `pole` (directions)."""
    d = target - a; dist = max(1e-4, min(d.length, l1 + l2 - 1e-4)); u = d.normalized()
    x = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist); hgt = math.sqrt(max(0.0, l1 * l1 - x * x))
    v = pole - u * pole.dot(u)
    v = v.normalized() if v.length > 1e-5 else Vector((0, 0, -1))
    joint = a + u * x + v * hgt
    return joint, a + u * dist


class Pose:
    """A full-body pose: torso/head angles, arms by hand target (IK) or by directions, legs planted (IK) or
    by directions. Points and directions are in character space (rest pose, faces -Y); the torso carries them."""
    def __init__(self, rig):
        self.r = rig; self.lean = self.turn = self.tilt = 0.0; self.lift = 0.0
        self.hnod = self.hturn = self.htilt = 0.0
        self.arms = {}; self.legs = {}

    def torso(self, lean=0.0, turn=0.0, tilt=0.0, lift=0.0):
        self.lean, self.turn, self.tilt, self.lift = lean, turn, tilt, lift; return self

    def head(self, nod=0.0, turn=0.0, tilt=0.0):
        self.hnod, self.hturn, self.htilt = nod, turn, tilt; return self

    def hand_at(self, s, x, y, z, pole=None, bend=0.0):
        """Wrist of arm `s` at (s*x, y, z): x is outward from the body centre line."""
        self.arms[s] = ("ik", V(s * x, y, z), pole or V(s * 0.5, 0.45, -1.0), bend); return self

    def arm_dirs(self, s, ua, fa, bend=0.0):
        """Upper arm / forearm directions as (out, forward, up)."""
        self.arms[s] = ("dir", V(s * ua[0], -ua[1], ua[2]), V(s * fa[0], -fa[1], fa[2]), bend); return self

    def relaxed(self, s, swing=0.0):
        return self.arm_dirs(s, (0.10, 0.05 + swing, -1), (0.04, 0.16 + swing, -1))

    def planted(self, s, dx=0.0, dy=0.0):
        self.legs[s] = ("ik", dx, dy); return self

    def leg_dirs(self, s, thigh, shin):
        self.legs[s] = ("dir", V(s * thigh[0], -thigh[1], thigh[2]), V(s * shin[0], -shin[1], shin[2])); return self


def _rot(lean, turn, tilt):
    return (Quaternion(Z, math.radians(turn)) @ Quaternion(Y, math.radians(tilt)) @ Quaternion(X, math.radians(lean)))


def solve(p):
    """Absolute rotation of every bone (armature space, about its head) for pose p."""
    r = p.r; A = {}
    T = _rot(p.lean, p.turn, p.tilt); A["Torso"] = T
    piv = r.pivot + V(0, 0, p.lift)
    carry = lambda pt: piv + T @ (pt - r.pivot)            # rest point carried by the torso
    A["Head"] = T @ _rot(p.hnod, p.hturn, p.htilt)
    swing = lambda parent, rest_dir, want: (parent @ rest_dir).rotation_difference(want) @ parent
    for s in (1, -1):
        sh = carry(r.shoulder[s])
        kind = p.arms.get(s, ("dir", None, None, 0.0))
        if kind[0] == "ik":
            target = carry(kind[1]); pole = T @ kind[2]
            elbow, wrist = two_bone(sh, target, r.l_ua, r.l_fa, pole)
            ua_dir, fa_dir = elbow - sh, wrist - elbow
        elif kind[1] is None:
            ua_dir, fa_dir = T @ (r.elbow[s] - r.shoulder[s]), T @ (r.wrist[s] - r.elbow[s])
        else:
            ua_dir, fa_dir = T @ kind[1], T @ kind[2]
        bend = kind[3]
        A[r.ua[s]] = swing(T, r.elbow[s] - r.shoulder[s], ua_dir)
        A[r.fa[s]] = swing(A[r.ua[s]], r.wrist[s] - r.elbow[s], fa_dir)
        A[r.hd[s]] = Quaternion((A[r.fa[s]] @ X), math.radians(-bend)) @ A[r.fa[s]] if bend else A[r.fa[s]]
        # legs
        hip = carry(r.hip[s])
        leg = p.legs.get(s, ("ik", 0.0, 0.0))
        if leg[0] == "ik":
            ankle = r.ankle[s] + V(s * leg[1], -leg[2], 0)
            if (ankle - hip).length < r.l_th + r.l_sh + 0.02:   # straight legs at rest still count as standing
                knee, ank = two_bone(hip, ankle, r.l_th, r.l_sh, T @ V(0, -1, 0.15))
                th_dir, sh_dir = knee - hip, ank - knee
            else:                                   # feet leave the ground: legs hang straight, a bit tucked
                th_dir, sh_dir = T @ V(0, -0.12, -1), T @ V(0, 0.18, -1)
        else:
            th_dir, sh_dir = T @ leg[1], T @ leg[2]
        A[r.th[s]] = swing(T, r.knee[s] - r.hip[s], th_dir)
        A[r.sh[s]] = swing(A[r.th[s]], r.ankle[s] - r.knee[s], sh_dir)
        A[r.ft[s]] = Quaternion()                     # soles stay flat
    return A


PARENT = {"Torso": None, "Head": "Torso"}


def put(arm, frame, p, last):
    """Keys pose p at frame. Rotations are stored relative to the parent; quaternion signs kept continuous."""
    A = solve(p)
    for pb in arm.pose.bones:
        n = pb.name
        if n not in A:
            continue
        par = pb.parent.name if pb.parent else None
        rel = (A[par].inverted() @ A[n]) if par in A else A[n]
        rest = pb.bone.matrix_local.to_quaternion()
        q = rest.inverted() @ rel @ rest
        if n in last and last[n].dot(q) < 0:
            q.negate()
        last[n] = q.copy()
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        if n == "Torso":
            pb.location = (0, p.lift, 0)
            pb.keyframe_insert("location", frame=frame)


# ------------------------------------------------------------------------------------------------- the clips
# Each clip is a function of the frame (1..N) returning a Pose; N+1 must equal frame 1 for loops.
TAU = 2 * math.pi


@clip("Rest", 2)
def rest(r, f):
    return Pose(r)


@clip("Cheer", 48)
def cheer(r, f):
    u = ((f - 1) % 24) / 24.0
    big = (f - 1) < 24
    peak = 0.22 if big else 0.14
    if u < 0.3:
        lift = -0.10 * ss(0.0, 0.3, u)
    elif u < 0.8:
        lift = -0.10 + (peak + 0.10) * math.sin(math.pi * (u - 0.3) / 0.5)
    else:
        lift = -0.10 * (1 - ss(0.8, 1.0, u))
    up = ss(-0.06, 0.12, lift)                   # arms rise with the jump
    p = Pose(r).torso(lean=6 * (1 - up) - 3 * up, lift=lift).head(nod=-6 - 10 * up)
    for s in (1, -1):
        p.planted(s, dx=0.03)
        # fists at the shoulders when crouched, punched up high in the air
        p.hand_at(s, mix(0.30, 0.30, up), mix(-0.36, -0.12, up), mix(1.72, 2.75, up), pole=V(s * mix(0.5, 1.0, up), 0.2, mix(-1.0, -0.35, up)))
    return p


@clip("Clap", 24)
def clap(r, f):
    u = ((f - 1) % 12) / 12.0
    close = 1 - ss(0.0, 0.25, u) if u < 0.25 else ss(0.55, 1.0, u)   # hands meet at u=0, open at 0.25..0.55
    p = Pose(r).head(nod=4).torso(lean=3)
    for s in (1, -1):
        p.hand_at(s, mix(0.03, 0.24, 1 - close), -0.42, mix(1.58, 1.62, 1 - close), pole=V(s * 1.0, 0.3, -0.6))
        p.planted(s)
    return p


@clip("Wave", 48)
def wave(r, f):
    w = math.sin(TAU * (f - 1) / 24)
    p = Pose(r).head(tilt=-5, turn=6).torso(tilt=-2)
    p.arm_dirs(1, (0.85, 0.15, 0.45), (0.10 + 0.40 * w, 0.12, 1.0), bend=-10)
    p.relaxed(-1)
    for s in (1, -1): p.planted(s)
    return p


@clip("FilmPhone", 96)
def film(r, f):
    t = TAU * (f - 1) / 96
    p = Pose(r).torso(turn=3 * math.sin(t), tilt=2 * math.sin(t)).head(nod=-4, tilt=3 * math.sin(t))
    # phone held at arm's length in front of the face, filming herself and the shop
    p.hand_at(1, 0.30 + 0.02 * math.sin(t), -0.60, 1.98 + 0.02 * math.sin(2 * t), pole=V(1.0, 0.2, -0.8), bend=-15)
    g = 0.5 + 0.5 * math.sin(2 * t)               # the free hand talks
    p.hand_at(-1, mix(0.30, 0.42, g), mix(-0.32, -0.46, g), mix(1.38, 1.66, g), pole=V(-1.0, 0.4, -1.0), bend=-20)
    for s in (1, -1): p.planted(s)
    return p


@clip("Clipboard", 96)
def clipboard(r, f):
    look = ss(48, 58, f) * (1 - ss(78, 88, f))
    jitter = 0.025 * math.sin(TAU * (f - 1) / 8) * (1 - look)
    p = Pose(r).head(nod=24 - 24 * look, turn=22 * look)
    p.hand_at(-1, 0.06, -0.40, 1.44, pole=V(-1.0, 0.2, -0.6))                  # holds the board flat
    p.hand_at(1, 0.02 + jitter, -0.44, 1.49, pole=V(1.0, 0.3, -0.7))            # writes on it
    for s in (1, -1): p.planted(s)
    return p


def _sip(p, f, n):
    drink = ss(n * 0.25, n * 0.37, f) * (1 - ss(n * 0.55, n * 0.67, f))
    p.hand_at(1, mix(0.14, 0.05, drink), mix(-0.34, -0.33, drink), mix(1.45, 1.86, drink),
              pole=V(1.0, 0.3, -1.0), bend=-10 - 20 * drink)
    p.head(nod=mix(4, -10, drink))
    return p


@clip("Sip", 96)
def sip(r, f):
    p = Pose(r)
    p.hand_at(-1, 0.33, 0.02, 1.12, pole=V(-1.0, 0.8, 0.0))     # other hand on the hip
    for s in (1, -1): p.planted(s)
    return _sip(p, f, 96)


@clip("SitSip", 96)
def sit_sip(r, f):
    p = Pose(r).torso(lift=-0.50, lean=-3)
    for s in (1, -1): p.planted(s, dx=0.03, dy=0.50)
    p.hand_at(-1, 0.20, -0.42, 1.10, pole=V(-1.0, 0.4, -1.0))  # hand resting on the knee/table
    return _sip(p, f, 96)


@clip("Tired", 120)
def tired(r, f):
    nod = 22 + 10 * ss(14, 30, f) - 20 * ss(30, 36, f) + 14 * ss(40, 62, f) * (1 - ss(70, 80, f))
    yawn = ss(80, 88, f) * (1 - ss(104, 113, f))
    p = Pose(r).torso(lean=10 - 6 * yawn, tilt=2).head(nod=mix(nod, -16, yawn))
    p.relaxed(-1)
    if yawn > 0:
        p.hand_at(1, mix(0.30, 0.05, yawn), mix(-0.10, -0.33, yawn), mix(1.15, 1.86, yawn), pole=V(1.0, 0.3, -1.0))
    else:
        p.relaxed(1)
    for s in (1, -1): p.planted(s)
    return p


@clip("WorkOverhead", 72)
def overhead(r, f):
    t = TAU * (f - 1) / 36
    p = Pose(r).head(nod=-28).torso(lean=-4)
    for s, ph in ((1, 0.0), (-1, math.pi)):
        p.hand_at(s, 0.16 + 0.03 * math.sin(t + ph), -0.42 + 0.03 * math.cos(t + ph), 2.62 + 0.05 * math.sin(t + ph),
                  pole=V(s * 1.0, 0.1, -0.3), bend=-25)
        p.planted(s)
    return p


@clip("TypeATM", 48)
def atm(r, f):
    tap = 0.02 * max(0.0, math.sin(TAU * (f - 1) / 8))
    p = Pose(r).head(nod=16).torso(lean=4)
    p.hand_at(1, 0.10, -0.55, 1.62 - tap, pole=V(1.0, 0.3, -1.0), bend=-15)
    p.relaxed(-1)
    for s in (1, -1): p.planted(s)
    return p


@clip("LookPhone", 96)
def look_phone(r, f):
    up = ss(46, 52, f) * (1 - ss(66, 74, f))
    tap = 4 * max(0.0, math.sin(TAU * (f - 1) / 12))
    p = Pose(r).head(nod=26 - 18 * up, turn=8 * up)
    p.hand_at(1, 0.05, -0.40, 1.52, pole=V(1.0, 0.3, -1.0), bend=-25 - tap)
    p.hand_at(-1, 0.07, -0.39, 1.49, pole=V(-1.0, 0.3, -1.0), bend=-25)
    for s in (1, -1): p.planted(s)
    return p


@clip("Fan", 48)
def fan(r, f):
    w = math.sin(TAU * (f - 1) / 12)
    p = Pose(r).head(nod=-6, tilt=4).torso(lean=-3)
    p.hand_at(1, 0.20 + 0.10 * w, -0.40, 1.98, pole=V(1.0, 0.1, -1.0), bend=-10)   # fans the face
    p.hand_at(-1, 0.33, 0.02, 1.12, pole=V(-1.0, 0.8, 0.0))                       # hand on the hip
    for s in (1, -1): p.planted(s)
    return p


@clip("PullWheel", 240)
def pull_wheel(r, f):
    # the wheel stands on her right: reach the rim (f 1-8), pull it down (8-18), let go, then present it
    reach = ss(1, 8, f) * (1 - ss(8, 18, f))
    pull = ss(8, 18, f) * (1 - ss(18, 30, f))
    show = ss(36, 50, f) * (1 - ss(205, 225, f))
    p = Pose(r).head(turn=-22 + 30 * ss(170, 185, f) * (1 - ss(205, 220, f)), nod=-10 * reach)
    # presenting = arm stretched out towards the wheel, palm up
    x = 0.18 + 0.26 * reach + 0.24 * pull + 0.49 * show
    y = -0.30 - 0.30 * reach - 0.35 * pull - 0.20 * show
    z = 1.05 + 1.55 * reach + 0.30 * pull + 0.58 * show
    p.hand_at(1, x, y, z, pole=V(1.0, 0.5, -1.0), bend=-15 * show)
    p.relaxed(-1)
    p.torso(lean=6 * pull)
    for s in (1, -1): p.planted(s)
    return p


@clip("HoldHandle", 24, arms_only=True)
def hold_handle(r, f):
    b = 0.015 * math.sin(TAU * (f - 1) / 24)
    p = Pose(r)
    for s in (1, -1):
        p.hand_at(s, 0.17, -0.56 - b, 1.30 + b, pole=V(s * 0.6, 0.5, -1.0), bend=-20)
    return p


@clip("CarryBox", 24, arms_only=True)
def carry_box(r, f):
    b = 0.012 * math.sin(TAU * (f - 1) / 24)
    p = Pose(r)
    for s in (1, -1):
        p.hand_at(s, 0.22, -0.42, 1.36 + b, pole=V(s * 1.0, 0.4, -1.0), bend=-35)
    return p


# ------------------------------------------------------------------------------------------------- build
def load_skeleton():
    reset()
    before = set(bpy.data.objects)
    with bpy.context.temp_override(**_ctx()):
        bpy.ops.import_scene.fbx(filepath=os.path.join(UNITY, "Assets", "Art", "Characters", "Meshy", CHAR + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE' and o.data.bones)
    for o in new:
        if o.type == 'ARMATURE' and o is not arm:
            bpy.data.objects.remove(o, do_unlink=True)
    for a in list(bpy.data.actions):          # the character's own clips stay in its own FBX
        bpy.data.actions.remove(a)
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return arm, [o for o in new if o.type == 'MESH' and o.name in bpy.data.objects]


def build():
    arm, meshes = load_skeleton()
    acts = []
    rig = Rig(arm)
    for name, (frames, fn, arms_only) in CLIPS.items():
        act = new_action(arm, name, frames=frames if frames > 2 else None)
        last = {}
        keys = list(range(1, frames + 2, STEP))
        if keys[-1] != frames + 1:
            keys.append(frames + 1)
        for f in keys:
            put(arm, f, fn(rig, ((f - 1) % frames) + 1 if frames > 2 else f), last)
        linear(act, "rotation"); linear(act, "location")
        if frames > 2:
            act.frame_start, act.frame_end = 1, frames
        acts.append(act)
    arm.name = "Customer_01_Rig"
    return arm, meshes, acts


def export_moves(arm, acts):
    """Skeleton + clips only (no mesh) -> EventRigs/EventMoves.fbx."""
    for o in bpy.context.selected_objects:
        o.select_set(False)
    arm.select_set(True); bpy.context.view_layer.objects.active = arm
    arm.animation_data.action = None
    path = os.path.join(RIGS_OUT, "EventMoves.fbx")
    with bpy.context.temp_override(**_ctx()):
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'ARMATURE'},
                                 axis_forward='-Z', axis_up='Y', add_leaf_bones=False, primary_bone_axis='Y',
                                 secondary_bone_axis='X', armature_nodetype='NULL', apply_scale_options='FBX_SCALE_ALL',
                                 bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                                 bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
                                 bake_anim_step=1.0, bake_anim_simplify_factor=0.0)
    return {"fbx": path, "clips": [a.name for a in acts]}
