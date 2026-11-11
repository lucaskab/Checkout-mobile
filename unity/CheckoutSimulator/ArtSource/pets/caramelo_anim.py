"""Caramelo, stage 4 - clips (24 fps). A pose is a small dict of readable parameters (body offsets, spine/neck/head
angles, paw targets, tail, ears, jaw, lids); clips are functions of time that build poses, keyed every frame on the
controls + deform bones. Legs are driven by the paw IK targets (planted paws never slide); the FBX export samples
the evaluated pose, so the game gets plain bone curves.

Clips (frames): Dog_Idle 72, Dog_Walk 24, Dog_Trot 16, Dog_SitDown 20, Dog_SitIdle 72, Dog_StandUp 20,
Dog_LieDown 30, Dog_Sleep 96, Dog_WakeUp 30, Dog_Happy 36, Dog_Bark 24, Dog_Sniff 48, Dog_Stretch 48.
Forward is -Y. Angles in degrees: pitch > 0 = nose/tip up, yaw > 0 = turns to the dog's left (+X), roll > 0 = left
side down.
"""
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler

FPS = 24
TAU = math.tau


def rad(d):
    return math.radians(d)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------------------------------------ pose model
def base_pose():
    p = dict(
        body=Vector((0, 0, 0)),           # hips + everything above, armature-space offset
        hips=(0.0, 0.0, 0.0),             # pitch, yaw, roll of the pelvis
        spine=(0.0, 0.0, 0.0), chest=(0.0, 0.0, 0.0),
        chest_off=Vector((0, 0, 0)),      # extra lift of the chest (sit / bow) applied as a spine bend
        neck=(0.0, 0.0, 0.0), head=(0.0, 0.0, 0.0),
        jaw=0.0, tongue=0.0, lids=0.0,
        ears=dict(L=(0.0, 0.0), R=(0.0, 0.0)),          # (back, droop) degrees
        tail=[(0.0, 0.0)] * 5,                          # (pitch, yaw) per segment
        paws={},                                        # 'FL' -> (pos, pitch)  armature space
        hocks={},                                       # 'HL' -> hock position override
        wrists={},                                      # 'FL' -> wrist position override
    )
    for k in ("FL", "FR", "HL", "HR"):
        p["paws"][k] = (REST_PAW[k].copy(), 0.0)
    return p


def mix(a, b, t):
    """Blend two poses (t: 0 -> a, 1 -> b)."""
    out = {}
    for k, va in a.items():
        vb = b[k]
        if isinstance(va, Vector):
            out[k] = va.lerp(vb, t)
        elif isinstance(va, tuple):
            out[k] = tuple(lerp(x, y, t) for x, y in zip(va, vb))
        elif isinstance(va, float):
            out[k] = lerp(va, vb, t)
        elif isinstance(va, list):
            out[k] = [tuple(lerp(x, y, t) for x, y in zip(sa, sb)) for sa, sb in zip(va, vb)]
        elif isinstance(va, dict):
            d = {}
            for kk in set(va) | set(vb):
                xa, xb = va.get(kk), vb.get(kk)
                if xa is None or xb is None:
                    d[kk] = xa if xb is None else xb
                elif isinstance(xa, tuple) and isinstance(xa[0], Vector):
                    d[kk] = (xa[0].lerp(xb[0], t), lerp(xa[1], xb[1], t))
                elif isinstance(xa, Vector):
                    d[kk] = xa.lerp(xb, t)
                else:
                    d[kk] = tuple(lerp(x, y, t) for x, y in zip(xa, xb))
            out[k] = d
        else:
            out[k] = va
    return out


REST_PAW, REST = {}, {}


def init_rest(rig):
    bones = rig.data.bones
    for sd, k in (("L", "FL"), ("R", "FR")):
        REST_PAW[k] = bones["FPaw_" + sd].tail_local.copy() * 0 + _ground(bones["FPaw_" + sd])
    for sd, k in (("L", "HL"), ("R", "HR")):
        REST_PAW[k] = _ground(bones["HPaw_" + sd])
    for b in bones:
        REST[b.name] = (b.matrix_local.to_3x3(), b.head_local.copy(), b.tail_local.copy())


def _ground(b):
    """Point under the paw's middle (on the floor) for a paw bone."""
    m = (b.head_local + b.tail_local) / 2
    return Vector((m.x, m.y, 0.0))


def rot_world(pitch=0.0, yaw=0.0, roll=0.0):
    # pitch about armature X (positive = tip up for a bone pointing -Y), yaw about Z, roll about Y
    return (Matrix.Rotation(rad(yaw), 3, 'Z') @ Matrix.Rotation(rad(-pitch), 3, 'X')
            @ Matrix.Rotation(rad(roll), 3, 'Y'))


def set_rot(pb, R):
    B = REST[pb.name][0]
    q = (B.inverted() @ R @ B).to_quaternion()
    pb.rotation_quaternion = q


def set_loc(pb, d):
    B = REST[pb.name][0]
    pb.location = B.inverted() @ d


def set_ctrl(pb, pos, R=None):
    """Control bone (child of Root, Root left at rest) to an armature-space position and rotation."""
    B, head, tail = REST[pb.name]
    pb.location = B.inverted() @ (pos - head)
    if R is not None:
        pb.rotation_quaternion = (B.inverted() @ R @ B).to_quaternion()
    else:
        pb.rotation_quaternion = (1, 0, 0, 0)


def apply_pose(rig, p):
    pbs = rig.pose.bones
    set_loc(pbs["Hips"], p["body"])
    set_rot(pbs["Hips"], rot_world(*p["hips"]))
    set_rot(pbs["Spine"], rot_world(*p["spine"]))
    set_rot(pbs["Chest"], rot_world(*p["chest"]))
    set_rot(pbs["Neck"], rot_world(*p["neck"]))
    set_rot(pbs["Head"], rot_world(*p["head"]))
    set_rot(pbs["Jaw"], rot_world(pitch=-p["jaw"]))
    t = p["tongue"]
    pbs["Tongue"].scale = (1, 1 + 0.6 * t, 1)
    set_rot(pbs["Tongue"], rot_world(pitch=-14 * t))
    for sd, s in (("L", 1), ("R", -1)):
        # lid: roll forward-down over the eye about the lid bone's own length (X)
        set_rot(pbs["Lid_" + sd], rot_world(pitch=-104 * p["lids"]))
        back, droop = p["ears"][sd]
        set_rot(pbs["Ear_" + sd], rot_world(pitch=back, roll=s * droop * 0.6, yaw=s * droop * 0.4))
        set_rot(pbs["EarTip_" + sd], rot_world(pitch=-droop * 0.8))
    for i, (pt, yw) in enumerate(p["tail"]):
        set_rot(pbs[f"Tail{i + 1}"], rot_world(pitch=-pt, yaw=yw))   # pt > 0: raise / curl over
    for k, sd in (("FL", "L"), ("FR", "R")):
        pos, pitch = p["paws"][k]
        R = rot_world(pitch=pitch)
        rest_wr = REST["FPaw_" + sd][1]
        wr = p["wrists"].get(k)
        if wr is None:
            # wrist sits above the paw like at rest, the paw bone rotated about the paw's heel
            off = rest_wr - REST_PAW[k]
            wr = pos + R @ off
        set_ctrl(pbs["IK_F_" + sd], wr)
        set_ctrl(pbs["IK_FP_" + sd], wr, R)
    for k, sd in (("HL", "L"), ("HR", "R")):
        pos, pitch = p["paws"][k]
        R = rot_world(pitch=pitch)
        ank_rest = REST["HPaw_" + sd][1]
        ank = pos + R @ (ank_rest - REST_PAW[k])
        hk = p["hocks"].get(k)
        if hk is None:
            hk = ank + (REST["Meta_" + sd][1] - ank_rest)
        set_ctrl(pbs["IK_H_" + sd], hk)
        set_ctrl(pbs["IK_HP_" + sd], ank, R)


KEYED = None


def key_all(rig, frame):
    for pb in rig.pose.bones:
        if pb.name == "Root":
            continue
        pb.keyframe_insert("location", frame=frame, group=pb.name)
        pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
        if pb.name == "Tongue":
            pb.keyframe_insert("scale", frame=frame, group=pb.name)


def make_action(rig, name, frames, fn, cyclic=False):
    """fn(t in [0,1], frame) -> pose; keyed on every frame 0..frames (the last == the first for cycles)."""
    act = bpy.data.actions.get(name)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    for f in range(frames + 1):
        t = f / frames
        apply_pose(rig, fn(t % 1.0 if (cyclic and f == frames) else t, f))
        key_all(rig, f)
    act.frame_range = (0, frames)
    try:
        act.use_frame_range = True
    except Exception:
        pass
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    return act


def _fcurves(act):
    try:
        return list(act.fcurves)
    except Exception:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out += list(cb.fcurves)
        return out


# ------------------------------------------------------------------------------------------------ building blocks
def wag(t, cycles, amp, base=(0.0, 0.0), curl=0.0):
    """Tail: base pitch per segment + a travelling sideways wave."""
    out = []
    for i in range(5):
        ph = TAU * (t * cycles) - i * 0.55
        out.append((base[0] + curl * i, base[1] + amp * math.sin(ph) * (0.6 + 0.2 * i)))
    return out


def gait(p, t, kind):
    """Paw targets for a walk (lateral 4-beat) or trot (diagonal pairs); in place, the game moves the dog."""
    if kind == "walk":
        L, H, duty = 0.42, 0.06, 0.62          # ground covered per cycle (the game scrubs the clip by distance)
        phase = dict(HL=0.0, FL=0.25, HR=0.5, FR=0.75)
    else:
        L, H, duty = 0.55, 0.08, 0.48
        phase = dict(FL=0.0, HR=0.0, FR=0.5, HL=0.5)
    for k, ph in phase.items():
        q = (t + ph) % 1.0
        rest = REST_PAW[k]
        front = k[0] == "F"
        if q < duty:                                    # stance: the paw slides back under the body
            s = q / duty
            y = -L / 2 + L * s
            z = 0.0
            pitch = lerp(0, 18 if front else 10, s) if s > 0.75 else 0.0
        else:                                           # swing: lift, fold and reach forward
            s = (q - duty) / (1 - duty)
            e = ease(s)
            y = L / 2 - L * e
            z = math.sin(math.pi * s) * H
            pitch = (-55 if front else -30) * math.sin(math.pi * s)
        p["paws"][k] = (Vector((rest.x, rest.y + y, z)), pitch)
        if front and q >= duty:
            # the wrist flexes up and back in the swing
            s = (q - duty) / (1 - duty)
            pos, pitch = p["paws"][k]
            wr_rest = REST["FPaw_" + ("L" if k == "FL" else "R")][1] - REST_PAW[k]
            p["wrists"][k] = pos + Vector((0, 0.025, 0.02)) * math.sin(math.pi * s) + wr_rest
    return p


# ------------------------------------------------------------------------------------------------ poses
def pose_sit():
    p = base_pose()
    p["body"] = Vector((0, 0.01, -0.235))
    p["hips"] = (28.0, 0.0, 0.0)            # front of the pelvis up: the rump sits on the floor
    p["spine"] = (8.0, 0.0, 0.0)
    p["chest"] = (6.0, 0.0, 0.0)
    p["neck"] = (-18.0, 0.0, 0.0)
    p["head"] = (-20.0, 0.0, 0.0)
    for k in ("HL", "HR"):
        r = REST_PAW[k]
        p["paws"][k] = (Vector((r.x * 1.12, r.y - 0.075, 0.0)), 0.0)
        p["hocks"][k] = Vector((r.x * 1.12, r.y + 0.035, 0.035))
    p["tail"] = [(-30.0, 8.0), (-10.0, 14.0), (-4.0, 14.0), (0.0, 10.0), (0.0, 6.0)]
    return p


def pose_lie():
    p = base_pose()
    p["body"] = Vector((0, 0.0, -0.285))
    p["hips"] = (-4.0, 0.0, -10.0)
    p["spine"] = (2.0, 0.0, 0.0)
    p["chest"] = (4.0, 0.0, 0.0)
    p["neck"] = (-4.0, 0.0, 0.0)
    p["head"] = (0.0, 0.0, 0.0)
    for k, sd in (("FL", "L"), ("FR", "R")):
        r = REST_PAW[k]
        p["paws"][k] = (Vector((r.x * 0.95, r.y - 0.16, 0.0)), 0.0)
        p["wrists"][k] = Vector((r.x * 0.95, r.y - 0.10, 0.03))
    for k, s in (("HL", 1), ("HR", -1)):
        r = REST_PAW[k]
        p["paws"][k] = (Vector((r.x * 1.6, r.y - 0.12, 0.0)), 0.0)
        p["hocks"][k] = Vector((r.x * 1.55, r.y + 0.02, 0.03))
    p["tail"] = [(-62.0, 34.0), (-22.0, 24.0), (-14.0, 22.0), (-10.0, 18.0), (-6.0, 12.0)]
    p["ears"] = dict(L=(15.0, 10.0), R=(15.0, 10.0))
    return p


def pose_sleep():
    p = pose_lie()
    p["neck"] = (-46.0, 8.0, 0.0)
    p["head"] = (28.0, 6.0, 10.0)         # chin resting on the paws
    p["lids"] = 1.0
    p["ears"] = dict(L=(25.0, 18.0), R=(25.0, 18.0))
    p["tail"] = [(-66.0, 48.0), (-22.0, 32.0), (-16.0, 30.0), (-12.0, 26.0), (-8.0, 18.0)]
    return p


def pose_bow():
    p = base_pose()
    p["body"] = Vector((0, 0.02, -0.03))
    p["hips"] = (-18.0, 0.0, 0.0)          # front goes down, rump stays up
    p["spine"] = (-6.0, 0.0, 0.0)
    p["chest"] = (-6.0, 0.0, 0.0)
    p["neck"] = (18.0, 0.0, 0.0)
    p["head"] = (16.0, 0.0, 0.0)
    for k, sd in (("FL", "L"), ("FR", "R")):
        r = REST_PAW[k]
        p["paws"][k] = (Vector((r.x, r.y - 0.15, 0.0)), 0.0)
        p["wrists"][k] = Vector((r.x, r.y - 0.08, 0.025))
    return p


# ------------------------------------------------------------------------------------------------ clips
def blink(t, at, dur=0.05):
    d = abs(t - at)
    return max(0.0, 1 - d / dur)


def clip_idle(t, f):
    p = base_pose()
    b = math.sin(TAU * t * 3)                      # breathing (3 per clip)
    p["body"] = Vector((0, 0, 0.003 * b))
    p["chest"] = (1.2 * b, 0, 0)
    look = math.sin(TAU * t)                       # slow look left/right
    p["neck"] = (2 + 2 * math.sin(TAU * t * 2), 10 * look, 0)
    p["head"] = (0, 6 * look, 5 * math.sin(TAU * t + 1.2))
    p["tail"] = wag(t, 4, 16, base=(6, 0), curl=4)
    flick = math.exp(-((t - 0.62) / 0.03) ** 2)
    p["ears"] = dict(L=(18 * flick, 0.0), R=(0.0, 0.0))
    p["lids"] = max(blink(t, 0.30), blink(t, 0.86))
    p["jaw"] = 4 + 3 * (0.5 + 0.5 * math.sin(TAU * t * 6))       # a soft pant
    p["tongue"] = 0.35
    return p


def clip_walk(t, f):
    p = gait(base_pose(), t, "walk")
    p["body"] = Vector((0, 0, 0.007 * math.sin(TAU * t * 2)))
    p["hips"] = (0, 3 * math.sin(TAU * t), 3 * math.sin(TAU * t + 1.0))
    p["chest"] = (0, -3 * math.sin(TAU * t), -2 * math.sin(TAU * t + 1.0))
    p["neck"] = (-4 + 2.5 * math.sin(TAU * t * 2 + 1.2), 0, 0)
    p["head"] = (2 - 2.5 * math.sin(TAU * t * 2 + 1.2), 0, 0)
    p["tail"] = wag(t, 1, 14, base=(10, 0), curl=4)
    p["ears"] = dict(L=(4 * math.sin(TAU * t * 2), 0.0), R=(4 * math.sin(TAU * t * 2 + 0.5), 0.0))
    p["jaw"] = 3.0; p["tongue"] = 0.2
    return p


def clip_trot(t, f):
    p = gait(base_pose(), t, "trot")
    p["body"] = Vector((0, 0, 0.012 * math.sin(TAU * t * 2 - 0.6)))
    p["hips"] = (0, 2 * math.sin(TAU * t), 4 * math.sin(TAU * t))
    p["chest"] = (0, -2 * math.sin(TAU * t), -3 * math.sin(TAU * t))
    p["neck"] = (-8 + 3 * math.sin(TAU * t * 2), 0, 0)
    p["head"] = (4 - 3 * math.sin(TAU * t * 2), 0, 0)
    p["tail"] = wag(t, 2, 20, base=(14, 0), curl=3)
    p["ears"] = dict(L=(10 + 6 * math.sin(TAU * t * 2), 0.0), R=(10 + 6 * math.sin(TAU * t * 2 + 0.4), 0.0))
    p["jaw"] = 9.0; p["tongue"] = 0.8
    return p


def clip_sit_down(t, f):
    return mix(base_pose(), pose_sit(), ease(t))


def clip_stand_up(t, f):
    return mix(pose_sit(), base_pose(), ease(t))


def clip_sit_idle(t, f):
    p = pose_sit()
    b = math.sin(TAU * t * 3)
    p["chest"] = (6 + 1.2 * b, 0, 0)
    look = math.sin(TAU * t)
    p["neck"] = (-18, 12 * look, 0)
    p["head"] = (-20 + 4 * math.sin(TAU * t * 2), 6 * look, 8 * math.sin(TAU * t + 0.8))
    tw = wag(t, 3, 10)
    p["tail"] = [(a[0], a[1] + w[1]) for a, w in zip(p["tail"], tw)]
    p["lids"] = blink(t, 0.45)
    p["jaw"] = 5 + 3 * (0.5 + 0.5 * math.sin(TAU * t * 6)); p["tongue"] = 0.5
    return p


def clip_lie_down(t, f):
    a, b, c = base_pose(), pose_sit(), pose_lie()
    # stand -> (through a half-sit) -> lie: the rump goes first, then the front walks forward
    if t < 0.45:
        return mix(a, mix(b, c, 0.3), ease(t / 0.45))
    return mix(mix(b, c, 0.3), c, ease((t - 0.45) / 0.55))


def clip_wake_up(t, f):
    p = clip_lie_down(1 - t, f)
    p["lids"] = max(0.0, 1 - t * 4)
    return p


def clip_sleep(t, f):
    p = pose_sleep()
    b = math.sin(TAU * t * 3)                      # slow, deep breaths
    p["body"] = p["body"] + Vector((0, 0, 0.005 * b))
    p["chest"] = (4 + 2.0 * b, 0, 0)
    twitch = math.exp(-((t - 0.55) / 0.025) ** 2)
    p["ears"] = dict(L=(25 - 20 * twitch, 18.0), R=(25.0, 18.0))
    tip = math.exp(-((t - 0.8) / 0.04) ** 2)
    tl = list(p["tail"]); tl[4] = (tl[4][0], tl[4][1] + 20 * tip); tl[3] = (tl[3][0], tl[3][1] + 10 * tip)
    p["tail"] = tl
    return p


def clip_happy(t, f):
    p = base_pose()
    w = math.sin(TAU * t * 6)                      # fast wag (6 per 1.5 s)
    p["hips"] = (0, 9 * w, 3 * w)                  # the whole rump wiggles with the tail
    p["chest"] = (4, -5 * w, -2 * w)
    p["body"] = Vector((0, 0, 0.006 * abs(w)))
    p["neck"] = (14, 0, 0)
    p["head"] = (10 + 3 * math.sin(TAU * t * 2), 4 * math.sin(TAU * t), 14 + 4 * math.sin(TAU * t * 2))
    p["tail"] = wag(t, 6, 34, base=(18, 0), curl=3)
    p["ears"] = dict(L=(38.0, 12.0), R=(38.0, 12.0))     # ears flattened back, happy
    p["lids"] = 0.62
    p["jaw"] = 14 + 3 * math.sin(TAU * t * 6)
    p["tongue"] = 1.0
    # front paws do a little happy tap
    for k, ph in (("FL", 0.0), ("FR", 0.5)):
        r = REST_PAW[k]
        q = (t * 3 + ph) % 1.0
        z = 0.025 * max(0.0, math.sin(TAU * q)) ** 2
        p["paws"][k] = (Vector((r.x, r.y, z)), -20 * (z / 0.025))
    return p


def clip_bark(t, f):
    p = base_pose()
    pulses = [0.18, 0.55]
    bark = sum(math.exp(-((t - c) / 0.06) ** 2) for c in pulses)
    p["body"] = Vector((0, -0.02 * bark, 0.01 * bark))
    p["chest"] = (6 * bark, 0, 0)
    p["neck"] = (10 + 8 * bark, 0, 0)
    p["head"] = (4 + 12 * bark, 0, 0)
    p["jaw"] = 30 * bark
    p["tongue"] = 0.2
    p["ears"] = dict(L=(-10 * bark, 0.0), R=(-10 * bark, 0.0))   # ears pricked forward
    p["tail"] = wag(t, 2, 10, base=(24, 0), curl=2)
    for k in ("FL", "FR"):
        r = REST_PAW[k]
        p["paws"][k] = (Vector((r.x * 1.08, r.y - 0.03, 0.0)), 0.0)
    return p


def clip_sniff(t, f):
    p = base_pose()
    p["neck"] = (-38, 6 * math.sin(TAU * t), 0)
    p["head"] = (-18, 10 * math.sin(TAU * t + 0.6), 0)
    p["chest"] = (-4, 0, 0)
    sn = math.sin(TAU * t * 16) * (0.5 + 0.5 * math.sin(TAU * t * 2))
    p["head"] = (p["head"][0] + 3 * sn, p["head"][1], p["head"][2])
    p["tail"] = wag(t, 2, 12, base=(4, 0), curl=4)
    p["ears"] = dict(L=(-6.0, 6.0), R=(-6.0, 6.0))
    return p


def clip_stretch(t, f):
    a, b = base_pose(), pose_bow()
    k = ease(t / 0.3) if t < 0.3 else (1.0 if t < 0.7 else ease((1 - t) / 0.3))
    p = mix(a, b, k)
    p["tail"] = wag(t, 3, 22 * k + 6, base=(20 * k + 6, 0), curl=3)
    p["jaw"] = 26 * math.exp(-((t - 0.5) / 0.12) ** 2)        # a big yawn in the middle
    p["lids"] = 0.8 * math.exp(-((t - 0.5) / 0.12) ** 2)
    return p


CLIPS = [
    ("Dog_Idle", 72, clip_idle, True), ("Dog_Walk", 24, clip_walk, True), ("Dog_Trot", 16, clip_trot, True),
    ("Dog_SitDown", 20, clip_sit_down, False), ("Dog_SitIdle", 72, clip_sit_idle, True),
    ("Dog_StandUp", 20, clip_stand_up, False), ("Dog_LieDown", 30, clip_lie_down, False),
    ("Dog_Sleep", 96, clip_sleep, True), ("Dog_WakeUp", 30, clip_wake_up, False),
    ("Dog_Happy", 36, clip_happy, True), ("Dog_Bark", 24, clip_bark, False), ("Dog_Sniff", 48, clip_sniff, True),
    ("Dog_Stretch", 48, clip_stretch, False),
]


def build_clips(rig, only=None):
    init_rest(rig)
    acts = []
    for name, n, fn, cyc in CLIPS:
        if only and name not in only:
            continue
        acts.append(make_action(rig, name, n, fn, cyc))
    print("clips", [a.name for a in acts])
    return acts
