"""The arrest (Lucas 08/11: "em vez de o policial sair com o ladrão algemado, o policial fica parado e o ladrão sai de
cabeça baixa"): the guard cuffs the thief and walks him out of the market.

  Thief_Cuffed      standing, hands cuffed behind the back, head down (loop)
  Thief_CuffedWalk  walking slowly with the hands cuffed behind the back, head down (loop)
  Thief_Cuffs       steel handcuffs on the wrists (rigid on the right hand; the game shows it only once he is cuffed)
  Guard_Escort      walking behind him, the right hand on his shoulder (loop)

Works in a temporary scene of whatever file Blender has open (the other sessions' scenes are not touched):
    exec(security_anim.py) in module sec; exec(this); build_arrest_thief(sec) / build_arrest_guard(sec)
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

UNITY = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator"
NPCS = os.path.join(UNITY, "ArtSource/NPCs")
OUTDIR = os.path.join(UNITY, "Assets/Resources/CheckoutSecurity")
TMP_SCENE = "Security_Arrest_Tmp"


# ------------------------------------------------------------------------------------------------ temp scene
def enter_tmp():
    sc = bpy.data.scenes.get(TMP_SCENE) or bpy.data.scenes.new(TMP_SCENE)
    prev = bpy.context.window.scene
    bpy.context.window.scene = sc
    return sc, prev


def leave_tmp(prev):
    """Back to the scene the user was on; every Thief_* / Guard_* datablock this script brought in is removed."""
    sc = bpy.data.scenes.get(TMP_SCENE)
    bpy.context.window.scene = prev
    if sc:
        for o in list(sc.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.scenes.remove(sc)
    pre = ("Thief_", "Guard_", "Torus")
    for coll in (bpy.data.objects, bpy.data.actions, bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
        for d in list(coll):
            if d.name.startswith(pre) and (coll is not bpy.data.objects or not d.users_scene):
                if coll is bpy.data.meshes or coll is bpy.data.armatures or coll is bpy.data.materials or coll is bpy.data.images:
                    if d.users - (1 if d.use_fake_user else 0) > 0:
                        continue
                d.use_fake_user = False
                coll.remove(d)


def append_character(blend, rig_name):
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
        dst.actions = [n for n in src.actions if n.startswith(rig_name.split("_")[0] + "_")]
    sc = bpy.context.scene
    rig = None; meshes = []
    for o in dst.objects:
        if o is None:
            continue
        if o.type == 'ARMATURE' and o.name.startswith(rig_name):
            rig = o
    for o in dst.objects:
        if o is None:
            continue
        if o is rig or (o.type == 'MESH' and o.parent is rig):
            sc.collection.objects.link(o)
            if o is not rig:
                meshes.append(o)
        else:
            bpy.data.objects.remove(o, do_unlink=True)
    for a in dst.actions:
        if a:
            a.use_fake_user = True
    return rig, meshes


# ------------------------------------------------------------------------------------------------ poses
ROT = 90.0


def cuffed_arms(P, p):
    """Hands behind the back, wrists together at the small of the back."""
    for s in "LR":
        p["afwd" + s] = -36; p["aout" + s] = 6; p["arot" + s] = ROT
        p["elbow" + s] = 50; p["elbow_in" + s] = 0; p["wrist" + s] = 8
    return p


def thief_cuffed(sec):
    P = sec.P

    def fn(t):
        p = P(lean=8, nod=24, lift=-0.01 + 0.006 * math.sin(math.tau * t))
        p["turn"] = 6 * math.sin(math.tau * t)
        return cuffed_arms(P, p)
    return fn


def thief_cuffed_walk(sec):
    def fn(t):
        # the customers' walk (security_anim.casual_walk), two cycles per clip, shorter steps, head down
        p = sec.casual_walk(2 * math.tau * t, swing=15, knee=36, arm=0)
        p.update(lean=9); p["nod"] += 26
        p["turn"] += 4 * math.sin(math.tau * t)
        return cuffed_arms(sec.P, p)
    return fn


def guard_escort(sec):
    def fn(t):
        p = sec.gait(t, stride=0.46, height=0.08, duty=0.62, arm=14, elbow=14, bob=0.016)
        p.update(lean=4, nod=6)
        # right hand forward on the thief's shoulder (no swing), left arm swings
        p["afwdR"] = 58; p["aoutR"] = 6; p["elbowR"] = 28; p["elbow_inR"] = 10; p["wristR"] = -14
        return p
    return fn


# ------------------------------------------------------------------------------------------------ cuffs
def cuffs(rig, body):
    """Steel cuffs: two rings round the wrists (measured in the cuffed pose) and a short chain."""
    sc = bpy.context.scene
    rig.animation_data.action = bpy.data.actions["Thief_Cuffed"]
    try:
        rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    except Exception:
        pass
    sc.frame_set(0); bpy.context.view_layer.update()
    pb = rig.pose.bones
    wl = rig.matrix_world @ pb["Hand_L"].head; wr = rig.matrix_world @ pb["Hand_R"].head
    fl = (rig.matrix_world @ pb["Forearm_L"].head); fr = (rig.matrix_world @ pb["Forearm_R"].head)
    parts = []
    for w, f in ((wl, fl), (wr, fr)):
        axis = (w - f).normalized()
        c = w - axis * 0.035
        bpy.ops.mesh.primitive_torus_add(major_radius=0.055, minor_radius=0.011, major_segments=24, minor_segments=8, location=c)
        ring = bpy.context.active_object
        ring.rotation_mode = 'QUATERNION'; ring.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(axis)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        parts.append(ring)
    a = wl - (wl - fl).normalized() * 0.035; b = wr - (wr - fr).normalized() * 0.035
    n = 4
    for i in range(n):
        p = a.lerp(b, (i + 0.5) / n)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.016, minor_radius=0.005, major_segments=12, minor_segments=6, location=p)
        link = bpy.context.active_object
        link.rotation_mode = 'QUATERNION'; link.rotation_quaternion = Vector((0, 0, 1)).rotation_difference((b - a).normalized().cross(Vector((0, 0, 1))) if i % 2 else Vector((0, 0, 1)))
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        parts.append(link)
    for x in bpy.context.selected_objects:
        x.select_set(False)
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    o = bpy.context.active_object; o.name = "Thief_Cuffs"
    for poly in o.data.polygons:
        poly.use_smooth = True
    m = bpy.data.materials.get("Thief_Cuffs_Mat") or bpy.data.materials.new("Thief_Cuffs_Mat")
    m.use_nodes = True; m.diffuse_color = (0.75, 0.77, 0.80, 1)
    b_ = m.node_tree.nodes.get("Principled BSDF")
    if b_:
        b_.inputs["Base Color"].default_value = (0.75, 0.77, 0.80, 1); b_.inputs["Metallic"].default_value = 0.9
        b_.inputs["Roughness"].default_value = 0.3
    o.data.materials.append(m)
    # rigid on the right hand: move the mesh into the rest pose frame of that bone
    M_pose = rig.matrix_world @ pb["Hand_R"].matrix
    M_rest = rig.matrix_world @ rig.data.bones["Hand_R"].matrix_local
    o.data.transform(M_rest @ M_pose.inverted())
    o.data.update()
    vg = o.vertex_groups.new(name="Hand_R"); vg.add(range(len(o.data.vertices)), 1.0, 'REPLACE')
    mod = o.modifiers.new("Skeleton", 'ARMATURE'); mod.object = rig
    o.parent = rig
    rig.animation_data.action = None
    return o


# ------------------------------------------------------------------------------------------------ build + export
def export(rig, meshes, path):
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    for x in bpy.context.selected_objects:
        x.select_set(False)
    rig.select_set(True)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
                             use_armature_deform_only=True, bake_anim=True, bake_anim_use_all_actions=True,
                             bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y',
                             path_mode='STRIP')
    return path


def arm_rest(rig):
    B = rig.data.bones
    for s in ("R", "L"):
        sh = rig.matrix_world @ B["UpperArm_" + s].head_local; wr = rig.matrix_world @ B["Hand_" + s].head_local
        return math.degrees(math.atan2(abs(wr.x - sh.x), sh.z - wr.z))
