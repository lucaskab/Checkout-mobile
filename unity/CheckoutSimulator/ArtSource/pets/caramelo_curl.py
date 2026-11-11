"""Caramelo curled up to sleep (Lucas 09/11/2026: "enroladinho, pra ele caber nas caminhas"). Adds to caramelo_anim:
Dog_CurlDown 40 (stand -> turn -> curl), Dog_CurlSleep 96 (loop, breathing), Dog_CurlUp 30 (wake).

The donut: lying low on the right hip, the back as the outer arc, the spine bent to the dog's left so the nose
reaches the left hind paw, legs tucked inside, the tail wrapped round the outside up to the nose.
Leg targets are found from the posed body (shoulders / hip joints), so they follow the bend.

    exec(caramelo_anim.py); exec(caramelo_curl.py); init_rest(rig); build_curl(rig)
"""
import bpy, math
from mathutils import Vector

CURL = dict(
    body=(-0.155, -0.311, -0.29),       # centres the donut on the root (measured on the evaluated mesh)
    hips=(-2.0, 48.0, -8.0), spine=(0.0, 46.0, 0.0), chest=(-4.0, 46.0, -4.0),
    neck=(-64.0, 54.0, 0.0), head=(14.0, 44.0, 18.0),
    tail=[(-74.0, -58.0), (-24.0, -50.0), (-12.0, -46.0), (-6.0, -42.0), (0.0, -36.0)],
    front_reach=0.13, hind_reach=0.15,
)


def _bone_head(rig, name):
    return rig.pose.bones[name].head.copy()


def _bone_dir(rig, name):
    b = rig.pose.bones[name]
    d = b.tail - b.head; d.z = 0
    return d.normalized() if d.length > 1e-6 else Vector((0, -1, 0))


def pose_curl(rig, c=None):
    """Builds the curl pose against the rig (needs the rig to read where the shoulders / hips land)."""
    c = dict(CURL, **(c or {}))
    p = base_pose()
    p["body"] = Vector(c["body"])
    for k in ("hips", "spine", "chest", "neck", "head"):
        p[k] = tuple(c[k])
    p["tail"] = [tuple(x) for x in c["tail"]]
    p["lids"] = 1.0
    p["ears"] = dict(L=(30.0, 22.0), R=(30.0, 22.0))
    # where the body went: legs tucked against it
    apply_pose(rig, p); bpy.context.view_layer.update()
    fwd_c = _bone_dir(rig, "Chest")
    left_c = Vector((-fwd_c.y, fwd_c.x, 0))         # dog's left of the chest (fwd -Y -> left +X)
    for k, sd in (("FL", "L"), ("FR", "R")):
        sh = _bone_head(rig, "UpperArm_" + sd); sh.z = 0
        side = 1 if sd == "L" else -1
        paw = sh + fwd_c * c["front_reach"] + left_c * (0.03 * side + 0.05)
        p["paws"][k] = (Vector((paw.x, paw.y, 0.0)), -20.0)
        p["wrists"][k] = Vector((paw.x, paw.y, 0.0)) - fwd_c * 0.05 + Vector((0, 0, 0.035))
    fwd_h = _bone_dir(rig, "Spine")
    left_h = Vector((-fwd_h.y, fwd_h.x, 0))
    for k, sd in (("HL", "L"), ("HR", "R")):
        hp = _bone_head(rig, "Thigh_" + sd); hp.z = 0
        side = 1 if sd == "L" else -1
        # the inner (left) hind paw by the nose, the outer one tucked well under the belly
        paw = hp + fwd_h * (c["hind_reach"] if sd == "L" else c["hind_reach"] * 0.7) + left_h * (0.10 if sd == "L" else 0.12)
        p["paws"][k] = (Vector((paw.x, paw.y, 0.0)), 0.0)
        p["hocks"][k] = hp - fwd_h * 0.06 + left_h * 0.04 * side + Vector((0, 0, 0.03))
    return p


def pose_curl_breath(rig, b, twitch=0.0):
    p = pose_curl(rig)
    p["body"] = p["body"] + Vector((0, 0, 0.004 * b))
    p["chest"] = (p["chest"][0] + 1.6 * b, p["chest"][1], p["chest"][2])
    p["ears"] = dict(L=(30 - 18 * twitch, 22.0), R=(30.0, 22.0))
    return p


def build_curl(rig):
    curl = pose_curl(rig)
    lie = pose_lie()

    def down(t, f):
        a = base_pose()
        if t < 0.35:                                 # a little turn in place: head goes left first
            p = base_pose()
            k = ease(t / 0.35)
            p["neck"] = (0, 30 * k, 0); p["head"] = (0, 20 * k, 0); p["hips"] = (0, -8 * k, 0)
            return p
        k = ease((t - 0.35) / 0.65)
        mid = mix(lie, curl, 0.35)
        if k < 0.5:
            src = base_pose(); src["neck"] = (0, 30, 0); src["head"] = (0, 20, 0); src["hips"] = (0, -8, 0)
            p = mix(src, mid, ease(k / 0.5))
        else:
            p = mix(mid, curl, ease((k - 0.5) / 0.5))
        p["lids"] = max(0.0, (k - 0.7) / 0.3)
        return p

    def sleep(t, f):
        b = math.sin(math.tau * t * 3)
        tw = math.exp(-((t - 0.55) / 0.025) ** 2)
        p = pose_curl_breath(rig, b, tw)
        tip = math.exp(-((t - 0.8) / 0.04) ** 2)
        tl = list(p["tail"]); tl[4] = (tl[4][0], tl[4][1] - 14 * tip); p["tail"] = tl
        return p

    def up(t, f):
        p = down(1 - t, f)
        p["lids"] = max(0.0, 1 - t * 4)
        return p

    acts = [make_action(rig, "Dog_CurlDown", 40, down), make_action(rig, "Dog_CurlSleep", 96, sleep, True),
            make_action(rig, "Dog_CurlUp", 30, up)]
    print("curl clips", [a.name for a in acts])
    return acts
