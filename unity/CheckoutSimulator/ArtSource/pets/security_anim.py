"""Clips for the thief and the guard on the customers' 14-bone skeleton (24 fps). Bones pivot at their heads and
all point up: Torso (root, pelvis at z 1.02) > Head; Torso > Thigh > Shin > Foot; Torso > UpperArm > Forearm > Hand.
Character faces -Y, its left is -X. Poses are written as rotations about world axes ("swing forward", "lean",
"abduct") and converted to each bone's local space through the chain, so they read like a pose description.

Thief: Thief_Sneak 32, Thief_LookAround 48, Thief_Stash 36, Thief_Run 16, Thief_Caught 20, Thief_HandsUp 24,
       Thief_GiveBack 36, Thief_WalkAshamed 32 (+ the customer's own Walking / Idle / GetFromShelf kept as Thief_*).
Guard: Guard_Idle 72, Guard_Run 16, Guard_Stop 24, Guard_Catch 30, Guard_Radio 48, Guard_ThumbsUp 24, Guard_Point 30
       (+ Guard_Walking / Guard_Idle0 from the customer).
"""
import bpy, math
from mathutils import Matrix, Vector, Quaternion

TAU = math.tau


def R(axis, deg):
    return Matrix.Rotation(math.radians(deg), 3, axis)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def hump(t, a, b):
    """0 outside [a,b], smooth 0->1->0 inside."""
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a))


# ------------------------------------------------------------------------------------------------ pose model
def P(**kw):
    """A pose: degrees. Missing keys = 0.
    torso: lift (m), fwd (m), lean (+ forward), side (+ toward its right), twist (+ turns to its left)
    head: nod (+ down), turn (+ to its left), tilt
    legs L/R: swing (+ forward), knee (+ bend), foot (+ toes down), spread (+ outward)
    arms L/R: fwd (+ forward), out (+ away from the body), twist, elbow (+ bend, forearm forward/up),
              elbow_in (+ forearm toward the body's middle), wrist (+ bend down),
              ftw (+ forearm/hand turn the palm toward the thigh; half on the forearm, all of it on the hand)"""
    d = dict(lift=0.0, fwd=0.0, lean=0.0, side=0.0, twist=0.0, nod=0.0, turn=0.0, tilt=0.0, ik=1.0,
             fyL=0.0, fzL=0.0, fyR=0.0, fzR=0.0)
    for s in "LR":
        for k in ("swing", "knee", "foot", "spread", "afwd", "aout", "atwist", "arot", "ftw", "elbow", "elbow_in", "wrist"):
            d[k + s] = 0.0
    d.update(kw)
    return d


def mix(a, b, t):
    out = {k: lerp(a.get(k, 0.0), b.get(k, 0.0), t) for k in set(a) | set(b)}
    out["ik"] = 1.0 if max(a.get("ik", 0), b.get("ik", 0)) > 0.5 else 0.0
    return out


def add(a, b):
    out = {k: a.get(k, 0.0) + b.get(k, 0.0) for k in set(a) | set(b)}
    out["ik"] = 1.0 if max(a.get("ik", 0), b.get("ik", 0)) > 0.5 else 0.0
    return out


REST = {}


def init_rest(rig):
    """Rest orientations, and the leg lengths of THIS rig (build_npcs fits the joints to each sculpt)."""
    global THIGH, SHIN, HIP_Z, ANKLE_Z
    REST.clear()
    for b in rig.data.bones:
        REST[b.name] = b.matrix_local.to_3x3()
    B = rig.data.bones
    HIP_Z = B["Thigh_L"].head_local.z
    THIGH = (B["Thigh_L"].head_local - B["Shin_L"].head_local).length
    SHIN = (B["Shin_L"].head_local - B["Foot_L"].head_local).length
    ANKLE_Z = B["Foot_L"].head_local.z


def _local(name, Rw, Rp):
    B = REST[name]
    return (B.inverted() @ Rp.inverted() @ Rw @ B).to_quaternion()


THIGH, SHIN, HIP_Z, ANKLE_Z = 0.47, 0.39, 0.98, 0.12
ARM_REST = 0.0       # the sculpt's arms hang this far out at rest (deg from vertical): poses give absolute angles


def leg_ik(p, s):
    """Swing/knee so the ankle reaches (footY s, footZ s) [m, world, footZ = height above its rest] with the hips
    lowered by p['lift']. Knee bends forward."""
    hip = Vector((0, -p["fwd"], HIP_Z + p["lift"]))
    foot = Vector((0, p.get("fy" + s, 0.0), ANKLE_Z + p.get("fz" + s, 0.0)))
    d = foot - hip
    L = min(d.length, THIGH + SHIN - 1e-4)
    a = math.acos(max(-1, min(1, (THIGH ** 2 + L ** 2 - SHIN ** 2) / (2 * THIGH * L))))
    k = math.pi - math.acos(max(-1, min(1, (THIGH ** 2 + SHIN ** 2 - L ** 2) / (2 * THIGH * SHIN))))
    base = math.atan2(-d.y, -d.z)                      # 0 = straight down, + = toward -Y (forward)
    p["swing" + s] = math.degrees(base + a)
    p["knee" + s] = math.degrees(k)


def apply(rig, p):
    pb = rig.pose.bones
    if p.get("ik", 0) > 0.5:
        for s_ in "LR":
            leg_ik(p, s_)
    side = {"L": -1, "R": 1}
    # torso (root): world delta
    Rt = R('Z', p["twist"]) @ R('X', p["lean"]) @ R('Y', -p["side"])
    B = REST["Torso"]
    pb["Torso"].rotation_quaternion = (B.inverted() @ Rt @ B).to_quaternion()
    pb["Torso"].location = B.inverted() @ Vector((0, -p["fwd"], p["lift"]))
    Rh = Rt @ R('Z', -p["turn"]) @ R('X', p["nod"]) @ R('Y', p["tilt"])
    pb["Head"].rotation_quaternion = _local("Head", Rh, Rt)
    for s in "LR":
        sg = side[s]
        # legs keep their own world angles (the torso lean does not swing them)
        Rthigh = R('Y', sg * -p["spread" + s]) @ R('X', -p["swing" + s])
        pb["Thigh_" + s].rotation_quaternion = _local("Thigh_" + s, Rthigh, Rt)
        Rshin = Rthigh @ R('X', p["knee" + s])
        pb["Shin_" + s].rotation_quaternion = _local("Shin_" + s, Rshin, Rthigh)
        Rfoot = R('X', p["foot" + s])                      # the foot keeps its own world pitch (flat / tiptoe)
        pb["Foot_" + s].rotation_quaternion = _local("Foot_" + s, Rfoot, Rshin)
        # arms follow the torso
        # the sculpt's arm hangs ARM_REST out at rest: first bring it down along the body (C), then pose it, so
        # elbow and wrist bends happen in the arm's own plane
        C = R('Y', sg * ARM_REST)
        Rua0 = Rt @ R('Z', sg * -p["atwist" + s]) @ R('Y', sg * -p["aout" + s]) @ R('X', -p["afwd" + s]) @ R('Z', sg * -p.get("arot" + s, 0.0))
        Rua = Rua0 @ C
        pb["UpperArm_" + s].rotation_quaternion = _local("UpperArm_" + s, Rua, Rt)
        Rel = Rua0 @ R('Y', sg * p["elbow_in" + s]) @ R('X', -p["elbow" + s])
        ftw = p.get("ftw" + s, 0.0)
        Rfa0 = Rel @ R('Z', sg * -0.5 * ftw)                # forearm: half the pronation (no candy-wrap at the elbow)
        Rfa = Rfa0 @ C
        pb["Forearm_" + s].rotation_quaternion = _local("Forearm_" + s, Rfa, Rua)
        Rha = Rel @ R('Z', sg * -ftw) @ R('X', p["wrist" + s]) @ C
        pb["Hand_" + s].rotation_quaternion = _local("Hand_" + s, Rha, Rfa)


def key(rig, f):
    for b in rig.pose.bones:
        if b.name == "Prop":
            continue
        b.keyframe_insert("rotation_quaternion", frame=f, group=b.name)
        if b.name == "Torso":
            b.keyframe_insert("location", frame=f, group=b.name)


def make(rig, name, frames, fn):
    a = bpy.data.actions.get(name)
    if a:
        bpy.data.actions.remove(a)
    a = bpy.data.actions.new(name); a.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = a
    for b in rig.pose.bones:
        b.rotation_mode = 'QUATERNION'; b.location = (0, 0, 0); b.rotation_quaternion = (1, 0, 0, 0)
    for f in range(frames + 1):
        p = fn(f / frames)
        apply(rig, p)
        if p.get("ground", 0) > 0.5:                     # the lower ankle on the floor (the customers' walk does this)
            bpy.context.view_layer.update()
            low = min(rig.pose.bones["Foot_L"].head.z, rig.pose.bones["Foot_R"].head.z)
            p["lift"] = p["lift"] + ANKLE_Z - low
            apply(rig, p)
        key(rig, f)
    a.frame_range = (0, frames)
    return a


# ------------------------------------------------------------------------------------------------ gaits
def gait(t, stride=0.50, height=0.10, duty=0.6, toe=0.0, arm=18.0, elbow=12.0, bob=0.02, lift=0.0, twist=0.0, sway=0.0):
    """Walk/run cycle with planted feet: the ankle targets slide back under the body during the stance and arc
    forward in the swing; the legs are solved by IK. Left foot strikes at t = 0."""
    p = P(lift=lift)
    for s, ph in (("L", 0.0), ("R", 0.5)):
        q = (t + ph) % 1.0
        if q < duty:
            u = q / duty
            p["fy" + s] = -stride / 2 + stride * u
            p["fz" + s] = 0.0
            p["foot" + s] = toe + (6 * (1 - u / 0.15) if u < 0.15 else 0) - (14 * (u - 0.8) / 0.2 if u > 0.8 else 0)
        else:
            u = (q - duty) / (1 - duty)
            e = ease(u)
            p["fy" + s] = stride / 2 - stride * e
            p["fz" + s] = height * math.sin(math.pi * u)
            p["foot" + s] = toe - 18 * math.sin(math.pi * u)
        c = math.cos(TAU * q)
        p["afwd" + s] = -arm * c
        p["elbow" + s] = elbow + 0.5 * elbow * (1 - c)
        p["aout" + s] = 6
    p["lift"] = lift - bob * 0.5 + bob * abs(math.cos(TAU * t))
    # a person, not a robot: the pelvis turns with the legs and shifts over the standing foot, the head keeps
    # looking ahead (counter-turn), a small nod with each step
    if twist or sway:
        p["twist"] = twist * math.sin(TAU * t + math.pi / 2)
        p["side"] = sway * math.sin(TAU * t)
        p["turn"] = -p["twist"] * 0.7
        p["nod"] = 1.5 * math.cos(TAU * t * 2)
    return p


# ------------------------------------------------------------------------------------------------ thief
def casual_walk(ph, swing=19.0, knee=40.0, arm=21.0, ftw=90.0):
    """The customers' walk (build_npcs.free_walk: the thighs swing, the knee folds as the leg comes forward, the arms
    swing against the legs, the lower foot stays on the floor) written in this pose model, plus what a person's
    body does on top: the shoulders turn against the hips, the weight shifts over the standing foot, a small nod."""
    sn, cs = math.sin(ph), math.cos(ph)
    p = P(ik=0.0, ground=1.0)
    p["swingL"] = swing * sn; p["swingR"] = -swing * sn
    p["kneeL"] = 6 + knee * max(0.0, cs); p["kneeR"] = 6 + knee * max(0.0, -cs)
    p["footL"] = -10 * sn; p["footR"] = 10 * sn               # toes up as the foot lands in front, heel up behind
    p["afwdL"] = -arm * sn; p["afwdR"] = arm * sn
    for s_ in "LR":
        p["elbow" + s_] = 12 + 0.45 * max(0.0, p["afwd" + s_]); p["aout" + s_] = 6; p["ftw" + s_] = ftw; p["wrist" + s_] = 4
    p["twist"] = 5 * sn
    p["side"] = 1.6 * cs
    p["turn"] = -0.8 * p["twist"]
    p["nod"] = 1.2 * math.cos(2 * ph)
    return p


def thief_sneak(t):
    """Walking in like any shopper (the customers' own walk), with a wary touch: leaning a little forward, head a bit
    down, scanning left and right. Two steps cycles per clip (Lucas 08/11: "parece um robô andando")."""
    p = casual_walk(2 * TAU * t)
    p["lean"] = 6
    p["nod"] += 4
    p["turn"] += 20 * math.sin(TAU * t)
    return p


def thief_sneak_old(t):
    """Walking in like any shopper, a touch wary: relaxed arms swinging, the pelvis and shoulders turning with the
    steps, the head scanning slowly left and right (Lucas 08/11: not stiff, not with the hands up)."""
    p = gait(t, stride=0.58, height=0.10, duty=0.6, toe=3, arm=21, elbow=18, bob=0.02, lift=-0.02, twist=6, sway=2.2)
    p.update(lean=5)
    for s in "LR":
        p["aout" + s] = 7; p["wrist" + s] = 6; p["ftw" + s] = 65      # palms toward the thighs, like a person
    p["turn"] = p["turn"] + 22 * math.sin(TAU * t * 0.5)
    return p


def thief_look(t):
    """At the shelf: weight shifting, hands low, quick looks around (left, centre, right, over the shoulder)."""
    p = P(lean=6, lift=-0.025, side=3 * math.sin(TAU * t))
    for s in "LR":
        p["afwd" + s] = 8; p["aout" + s] = 8; p["elbow" + s] = 24 + 3 * math.sin(TAU * t * 2); p["wrist" + s] = 4
        p["ftw" + s] = 60
    p["spreadL"] = p["spreadR"] = 4
    keys = [(0.0, 0), (0.12, 0), (0.2, 40), (0.38, 40), (0.46, -5), (0.55, -5), (0.62, -45), (0.82, -45), (0.92, 0), (1.0, 0)]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if a <= t <= b:
            p["turn"] = lerp(va, vb, ease((t - a) / (b - a)))
    p["twist"] = p["turn"] * 0.25
    p["nod"] = -2
    return p


def thief_stash(t):
    base = P(lean=8, lift=-0.04, kneeL=10, kneeR=10)
    reach = P(lean=14, lift=-0.04, kneeL=12, kneeR=12, afwdR=82, aoutR=6, elbowR=8, wristR=-10, turn=0, nod=6)
    grab = add(reach, P(elbowR=30, wristR=30))
    stash = P(lean=10, lift=-0.06, kneeL=14, kneeR=14, afwdR=18, aoutR=-14, elbowR=78, elbow_inR=48, wristR=20,
              twist=-12, nod=12, turn=-10)
    look = add(stash, P(turn=-40, nod=-2))
    if t < 0.28:
        p = mix(base, reach, ease(t / 0.28))
    elif t < 0.40:
        p = mix(reach, grab, ease((t - 0.28) / 0.12))
    elif t < 0.70:
        p = mix(grab, stash, ease((t - 0.40) / 0.30))
    else:
        p = mix(stash, look, ease((t - 0.70) / 0.30))
    for s in ("L",):
        p["afwdL"] = p.get("afwdL", 0) + 10; p["elbowL"] = p.get("elbowL", 0) + 20; p["aoutL"] = 8
    return p


def thief_run(t):
    p = gait(t, stride=0.95, height=0.26, duty=0.42, arm=44, elbow=80, bob=0.06, lift=-0.06, twist=9, sway=2.5)
    p.update(lean=14 + 2 * math.sin(TAU * t * 2))
    p["nod"] = -6 + p["nod"]
    for s in "LR":
        p["elbow" + s] = 86
        p["elbow_in" + s] = 14
        p["ftw" + s] = 50
    return p


HANDS_UP = P(lift=0.0, lean=-6, nod=-8, afwdL=40, aoutL=118, elbowL=40, afwdR=40, aoutR=118, elbowR=40,
             wristL=-20, wristR=-20, spreadL=5, spreadR=5)


def thief_caught(t):
    """Startled: a jump back with the hands half up in front of the chest, then the hands go up."""
    start = P(lean=14, lift=-0.04)
    flinch = P(lean=-8, lift=0.03, nod=-10, kneeL=8, kneeR=8, afwdL=40, aoutL=28, elbowL=70, afwdR=40, aoutR=28, elbowR=70,
               wristL=-20, wristR=-20, fyL=0.06, fyR=0.06)
    if t < 0.3:
        p = mix(start, flinch, ease(t / 0.3))
    elif t < 0.55:
        p = flinch
    else:
        p = mix(flinch, HANDS_UP, ease((t - 0.55) / 0.45))
    return p


def thief_hands_up(t):
    p = add(HANDS_UP, P(lift=0.006 * math.sin(TAU * t * 4), turn=18 * math.sin(TAU * t), nod=-8 + 3 * math.sin(TAU * t * 2)))
    for s in "LR":
        p["elbow" + s] += 4 * math.sin(TAU * t * 8 + (0 if s == "L" else 1.3))      # nervous shake
    return p


def thief_give_back(t):
    offer = P(lean=6, nod=18, afwdR=62, aoutR=4, elbowR=18, wristR=-18, afwdL=4, elbowL=10, kneeL=6, kneeR=6)
    shame = P(lean=10, nod=34, afwdR=6, elbowR=14, afwdL=6, elbowL=14, side=2, kneeL=6, kneeR=6, turn=-6)
    if t < 0.4:
        p = mix(HANDS_UP, offer, ease(t / 0.4))
    elif t < 0.65:
        p = offer
    else:
        p = mix(offer, shame, ease((t - 0.65) / 0.35))
    return p


def thief_walk_ashamed(t):
    p = casual_walk(2 * TAU * t, swing=15, knee=38, arm=10)
    p["lean"] = 9; p["nod"] += 30
    for s in "LR":
        p["afwd" + s] += 4; p["aout" + s] = 4
    return p


def thief_walk_ashamed_old(t):
    p = gait(t, stride=0.40, height=0.07, duty=0.62, arm=9, elbow=12, bob=0.014, lift=-0.02, twist=4, sway=1.6)
    p.update(lean=8, nod=30)
    for s in "LR":
        p["afwd" + s] = p["afwd" + s] + 4; p["aout" + s] = 4; p["ftw" + s] = 65
    return p


# ------------------------------------------------------------------------------------------------ guard
def guard_idle(t):
    sway = math.sin(TAU * t)
    p = P(side=2.5 * sway, lift=0.004 * math.sin(TAU * t * 2), lean=-2)
    p["spreadL"] = p["spreadR"] = 6
    p["fyL"] = -0.03; p["fyR"] = 0.03; p["lift"] -= 0.012 + 0.008 * abs(sway)
    for s in "LR":                                      # hands clasped behind the back
        p["afwd" + s] = -22; p["aout" + s] = 10; p["elbow" + s] = 62; p["elbow_in" + s] = 70
    keys = [(0.0, 0), (0.25, 0), (0.35, 30), (0.55, 30), (0.65, -25), (0.85, -25), (0.95, 0), (1.0, 0)]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if a <= t <= b:
            p["turn"] = lerp(va, vb, ease((t - a) / (b - a)))
    p["nod"] = -3
    return p


def guard_run(t):
    p = gait(t, stride=0.95, height=0.24, duty=0.42, arm=44, elbow=82, bob=0.06, lift=-0.05)
    p.update(lean=12, nod=-4)
    for s in "LR":
        p["elbow" + s] = 86; p["elbow_in" + s] = 10
    return p


def guard_stop(t):
    stop = P(lean=-4, afwdR=88, aoutR=6, elbowR=72, wristR=-62, afwdL=6, aoutL=8, elbowL=20, nod=-6, fyR=-0.10, lift=-0.015,
             spreadL=6)
    k = ease(t / 0.4)
    p = mix(P(), stop, k)
    p["elbowR"] += 3 * math.sin(TAU * t * 2) * k
    return p


def guard_catch(t):
    grab = P(lean=10, fwd=0.04, afwdR=72, aoutR=-4, elbowR=24, wristR=24, afwdL=10, aoutL=10, elbowL=60, elbow_inL=40,
             fyR=-0.22, fyL=0.05, lift=-0.04, nod=6)
    hold = add(grab, P(elbowR=8, lean=-2))
    if t < 0.45:
        return mix(P(), grab, ease(t / 0.45))
    return mix(grab, hold, ease((t - 0.45) / 0.55))


def guard_radio(t):
    p = P(afwdL=36, aoutL=26, elbowL=128, elbow_inL=36, wristL=-10, tilt=-8, nod=2, spreadL=5, spreadR=5)
    talk = math.sin(TAU * t * 6) * hump(t, 0.1, 0.9)
    p["nod"] += 3 * talk
    p["turn"] = 10 * math.sin(TAU * t)
    p["afwdR"] = 4; p["elbowR"] = 12
    return p


def guard_thumbs(t):
    up = P(afwdR=48, aoutR=10, elbowR=96, wristR=-20, nod=-10, tilt=8, lean=-3)
    nod = 8 * hump(t, 0.4, 0.6)
    p = mix(P(), up, ease(t / 0.35))
    p["nod"] += nod
    return p


def guard_point(t):
    pt = P(afwdR=82, aoutR=40, elbowR=4, wristR=-6, turn=-28, twist=-10, afwdL=6, elbowL=10, nod=-4)
    return mix(P(), pt, ease(t / 0.35))


THIEF_CLIPS = [("Thief_Sneak", 64, thief_sneak), ("Thief_LookAround", 48, thief_look), ("Thief_Stash", 36, thief_stash),
               ("Thief_Run", 16, thief_run), ("Thief_Caught", 20, thief_caught), ("Thief_HandsUp", 24, thief_hands_up),
               ("Thief_GiveBack", 36, thief_give_back), ("Thief_WalkAshamed", 64, thief_walk_ashamed)]
GUARD_CLIPS = [("Guard_Idle", 72, guard_idle), ("Guard_Run", 16, guard_run), ("Guard_Stop", 24, guard_stop),
               ("Guard_Catch", 30, guard_catch), ("Guard_Radio", 48, guard_radio), ("Guard_ThumbsUp", 24, guard_thumbs),
               ("Guard_Point", 30, guard_point)]


def build(rig, clips):
    init_rest(rig)
    out = [make(rig, n, f, fn) for n, f, fn in clips]
    print("clips", [a.name for a in out])
    return out
