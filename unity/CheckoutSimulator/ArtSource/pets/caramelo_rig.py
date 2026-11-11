"""Caramelo, stage 3 - rig: a quadruped skeleton (Unity Legacy-friendly: plain deform bones, no constraints at
runtime) fitted to the sculpt's key points, skinned per part, plus a non-deform control layer (paw IK targets, poles)
used only while animating; the clips are baked to the deform bones before export.

Deform bones (24 fps clips drive these):
  Root > Hips > Spine > Chest > Neck > Head > Jaw > Tongue ; Head > Ear_L/EarTip_L, Ear_R/EarTip_R, Lid_L, Lid_R
  Chest > Scapula_L > UpperArm_L > Forearm_L > FPaw_L            (and _R)
  Hips > Thigh_L > Shin_L > Meta_L > HPaw_L                       (and _R)
  Hips > Tail1 .. Tail5
Controls: IK_F_L (wrist target), IK_FP_L (front paw flat), Pole_F_L, IK_H_L (hock target), IK_HP_L (hind paw),
          Pole_H_L ... children of Root.
"""
import bpy, math
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

RIG = "Caramelo_Rig"


def _side(v, s):
    return Vector((v.x * s, v.y, v.z))


def bone_layout():
    """name -> (head, tail, parent, deform)"""
    B = {}
    B["Root"] = (Vector((0, 0, 0)), Vector((0, 0.12, 0)), None, True)
    B["Hips"] = (Vector((0, 0.20, 0.43)), Vector((0, 0.07, 0.425)), "Root", True)
    B["Spine"] = (Vector((0, 0.07, 0.425)), Vector((0, -0.07, 0.43)), "Hips", True)
    B["Chest"] = (Vector((0, -0.07, 0.43)), Vector((0, -0.23, 0.45)), "Spine", True)
    B["Neck"] = (Vector((0, -0.25, 0.475)), Vector((0, -0.36, 0.605)), "Chest", True)
    B["Head"] = (Vector((0, -0.36, 0.605)), Vector((0, -0.40, 0.74)), "Neck", True)
    jt = P["jaw"]
    B["Jaw"] = (jt, Vector((0, P["nose"].y + 0.04, jt.z - 0.02)), "Head", True)
    B["Tongue"] = (Vector((0, P["nose"].y + 0.11, jt.z - 0.006)), Vector((0, P["nose"].y + 0.035, jt.z - 0.008)), "Jaw", True)
    for s, sd in ((1, "L"), (-1, "R")):
        e = EAR_BASE[sd]
        up = EAR_UP[sd]
        B["Ear_" + sd] = (e, e + up * 0.06, "Head", True)
        B["EarTip_" + sd] = (e + up * 0.06, e + up * 0.115, "Ear_" + sd, True)
        ec = EYE_C[sd]
        B["Lid_" + sd] = (ec, ec + Vector((s * 0.022, 0, 0)), "Head", True)       # rolls about its own length (X)
        sh, el, wr, fp = (_side(P[k], s) for k in ("shoulder", "elbow", "wrist", "fpaw"))
        B["Scapula_" + sd] = (_side(Vector((0.055, -0.13, 0.48)), s), sh, "Chest", True)
        B["UpperArm_" + sd] = (sh, el, "Scapula_" + sd, True)
        B["Forearm_" + sd] = (el, wr, "UpperArm_" + sd, True)
        B["FPaw_" + sd] = (wr, fp + Vector((0, -0.045, 0.0)), "Forearm_" + sd, True)
        hp, kn, hk, hpw = (_side(P[k], s) for k in ("hip", "knee", "hock", "hpaw"))
        ank = hpw + Vector((0, 0.012, 0.018))
        B["Thigh_" + sd] = (hp, kn, "Hips", True)
        B["Shin_" + sd] = (kn, hk, "Thigh_" + sd, True)
        B["Meta_" + sd] = (hk, ank, "Shin_" + sd, True)
        B["HPaw_" + sd] = (ank, hpw + Vector((0, -0.05, -0.004)), "Meta_" + sd, True)
        # controls
        B["IK_F_" + sd] = (wr, wr + Vector((0, 0, 0.05)), "Root", False)
        B["IK_FP_" + sd] = (wr, fp + Vector((0, -0.045, 0.0)), "Root", False)
        B["Pole_F_" + sd] = (el + Vector((0, 0.35, 0)), el + Vector((0, 0.35, 0.05)), "Root", False)
        B["IK_H_" + sd] = (hk, hk + Vector((0, 0, 0.05)), "Root", False)
        B["IK_HP_" + sd] = (ank, hpw + Vector((0, -0.05, -0.004)), "Root", False)
        B["Pole_H_" + sd] = (kn + Vector((0, -0.35, 0)), kn + Vector((0, -0.35, 0.05)), "Root", False)
    tp = catmull(TAIL, 1)
    prev = "Hips"
    for i in range(5):
        a = tp[i]; b = tp[i + 1]
        B[f"Tail{i + 1}"] = (a, b, prev, True); prev = f"Tail{i + 1}"
    return B


EAR_BASE, EAR_UP, EYE_C = {}, {}, {}


def measure_parts(parts):
    """Ear base/up and eye centres from the placed parts (before the join)."""
    for sd in ("L", "R"):
        ear = parts["ear" + sd]
        vs = [ear.matrix_world @ v.co for v in ear.data.vertices]
        zmin = min(v.z for v in vs)
        base = [v for v in vs if v.z < zmin + 0.012]
        b = sum(base, Vector()) / len(base)
        top = max(vs, key=lambda v: (v - b).length)
        EAR_BASE[sd] = b
        EAR_UP[sd] = (top - b).normalized()
        eye = parts["eye" + sd]
        EYE_C[sd] = sum((eye.matrix_world @ v.co for v in eye.data.vertices), Vector()) / len(eye.data.vertices)


def build_armature():
    B = bone_layout()
    old = bpy.data.objects.get(RIG)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    arm = bpy.data.armatures.new(RIG)
    o = bpy.data.objects.new(RIG, arm); bpy.context.scene.collection.objects.link(o)
    ctx_obj(o)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    for name, (h, t, par, dfm) in B.items():
        b = eb.new(name); b.head = h; b.tail = t; b.use_deform = dfm
        b.roll = 0
    for name, (h, t, par, dfm) in B.items():
        if par:
            eb[name].parent = eb[par]
            eb[name].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    arm.display_type = 'STICK'
    o.show_in_front = True
    for pb in o.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return o


def add_ik(rig, pole_f=-90.0, pole_h=90.0):
    pbs = rig.pose.bones
    for sd in ("L", "R"):
        c = pbs["Forearm_" + sd].constraints.new('IK')
        c.target = rig; c.subtarget = "IK_F_" + sd; c.chain_count = 2
        c.pole_target = rig; c.pole_subtarget = "Pole_F_" + sd; c.pole_angle = math.radians(pole_f)
        c2 = pbs["FPaw_" + sd].constraints.new('COPY_ROTATION'); c2.target = rig; c2.subtarget = "IK_FP_" + sd
        c = pbs["Shin_" + sd].constraints.new('IK')
        c.target = rig; c.subtarget = "IK_H_" + sd; c.chain_count = 2
        c.pole_target = rig; c.pole_subtarget = "Pole_H_" + sd; c.pole_angle = math.radians(pole_h)
        c3 = pbs["Meta_" + sd].constraints.new('DAMPED_TRACK'); c3.target = rig; c3.subtarget = "IK_HP_" + sd
        c4 = pbs["HPaw_" + sd].constraints.new('COPY_ROTATION'); c4.target = rig; c4.subtarget = "IK_HP_" + sd


def tune_poles(rig):
    """Pick the pole angles that keep the rest pose (elbow/knee where the sculpt has them)."""
    bpy.context.view_layer.update()
    best = {}
    for kind, bone, ref in (("F", "Forearm_L", "elbow"), ("H", "Shin_L", "knee")):
        c = rig.pose.bones[bone].constraints[0]
        scores = []
        for a in range(-180, 181, 5):
            c.pole_angle = math.radians(a)
            bpy.context.view_layer.update()
            head = rig.pose.bones[bone].head
            scores.append(((head - P[ref]).length, a))
        err, a = min(scores)
        best[kind] = a
        for sd in ("L", "R"):
            rig.pose.bones[bone.replace("_L", "_" + sd)].constraints[0].pole_angle = math.radians(a * (1 if sd == "L" else 1))
        print("pole", kind, a, "err", round(err, 4))
    bpy.context.view_layer.update()
    return best


# ------------------------------------------------------------------------------------------------ skinning
PART_BONE = dict(jaw="Jaw", tongue="Tongue", nose="Head", eyeL="Head", eyeR="Head", lidL="Lid_L", lidR="Lid_R")
NOT_BODY = ("Jaw", "Tongue", "Lid_L", "Lid_R", "Ear_L", "Ear_R", "EarTip_L", "EarTip_R")


def skin_parts(parts, rig):
    body = parts["body"]
    ctx_obj(body); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    # the body never follows the jaw/tongue/lids/ears
    for g in list(body.vertex_groups):
        if g.name in NOT_BODY or g.name.startswith(("IK_", "Pole_")):
            body.vertex_groups.remove(g)
    fill_unweighted(body)
    _normalize(body)
    for key, bone in PART_BONE.items():
        o = parts[key]
        vg = o.vertex_groups.new(name=bone); vg.add(range(len(o.data.vertices)), 1.0, 'REPLACE')
        _armature(o, rig)
    for sd in ("L", "R"):
        o = parts["ear" + sd]
        g1 = o.vertex_groups.new(name="Ear_" + sd); g2 = o.vertex_groups.new(name="EarTip_" + sd)
        b = EAR_BASE[sd]; up = EAR_UP[sd]
        for v in o.data.vertices:
            h = (o.matrix_world @ v.co - b).dot(up) / 0.115
            t = min(1, max(0, (h - 0.40) / 0.30))
            g1.add([v.index], 1 - t, 'REPLACE'); g2.add([v.index], t, 'REPLACE')
        # the very base stays glued to the head
        g0 = o.vertex_groups.new(name="Head")
        for v in o.data.vertices:
            h = (o.matrix_world @ v.co - b).dot(up) / 0.115
            if h < 0.12:
                w = 1 - h / 0.12
                g0.add([v.index], w, 'REPLACE'); g1.add([v.index], (1 - w), 'REPLACE')
        _armature(o, rig)


def fill_unweighted(o):
    """Bone-heat can leave a few vertices without weights (they would stay behind as spikes): give each one the
    weights of the nearest weighted vertex."""
    from mathutils.kdtree import KDTree
    me = o.data
    good = [v for v in me.vertices if sum(g.weight for g in v.groups) > 0.05]
    bad = [v for v in me.vertices if sum(g.weight for g in v.groups) <= 0.05]
    if not bad:
        return 0
    kd = KDTree(len(good))
    for i, v in enumerate(good):
        kd.insert(v.co, i)
    kd.balance()
    vgs = o.vertex_groups
    for v in bad:
        co, i, d = kd.find(v.co)
        for g in good[i].groups:
            vgs[g.group].add([v.index], g.weight, 'REPLACE')
    print("filled unweighted", len(bad))
    return len(bad)


def _armature(o, rig):
    m = o.modifiers.get("Armature") or o.modifiers.new("Armature", 'ARMATURE')
    m.object = rig
    o.parent = rig


def _normalize(o):
    ctx_obj(o)
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def build_rig(parts):
    measure_parts(parts)
    rig = build_armature()
    skin_parts(parts, rig)
    add_ik(rig)
    tune_poles(rig)
    return rig
