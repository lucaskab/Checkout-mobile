"""Rebuild the thief's game FBX from thief_game.blend in a temporary scene (the other sessions' scenes untouched):
all security_anim.THIEF_CLIPS + the arrest clips (Thief_Cuffed / Thief_CuffedWalk) + the cuffs.

    exec(open(".../security_rebuild.py").read()); rebuild_thief()          # exports Assets/Resources/CheckoutSecurity/Thief.fbx
    preview_pose(fn_name, t, out_png, **overrides)                         # QA stills in the temp scene
"""
import bpy, os, sys, types, math
from mathutils import Vector

UNITY = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator"
PETS = os.path.join(UNITY, "ArtSource/pets")
NPCS = os.path.join(UNITY, "ArtSource/NPCs")
OUTDIR = os.path.join(UNITY, "Assets/Resources/CheckoutSecurity")
QA = os.path.join(UNITY, "Temp/qa")
THIEF_ARM_REST = 36.5
CUFF_CLIPS = [("Thief_Cuffed", 48, "thief_cuffed"), ("Thief_CuffedWalk", 64, "thief_cuffed_walk")]


def _module(name, path):
    g = {"__name__": name, "__file__": path}
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), g)
    m = types.ModuleType(name); m.__dict__.update(g); sys.modules[name] = m
    return m


def modules():
    sec = _module("security_anim", os.path.join(PETS, "security_anim.py"))
    arr = _module("security_arrest", os.path.join(PETS, "security_arrest.py"))
    sec.build.__globals__["ARM_REST"] = THIEF_ARM_REST
    return sec, arr


def load_thief(sec, arr):
    sc, prev = arr.enter_tmp()
    rig, meshes = arr.append_character(os.path.join(NPCS, "thief_game.blend"), "Thief_Rig")
    sec.init_rest(rig)
    return sc, prev, rig, meshes


def rebuild_thief(export=True):
    sec, arr = modules()
    sc, prev, rig, meshes = load_thief(sec, arr)
    try:
        sec.build(rig, sec.THIEF_CLIPS)
        for name, frames, fn in CUFF_CLIPS:
            sec.make(rig, name, frames, getattr(arr, fn)(sec))
        body = next(o for o in meshes if o.name.startswith("Thief_Body"))
        meshes.append(arr.cuffs(rig, body))
        path = arr.export(rig, meshes, os.path.join(OUTDIR, "Thief.fbx")) if export else None
        print("actions", sorted(a.name for a in bpy.data.actions if a.name.startswith("Thief_")))
        print("exported", path, os.path.getsize(path) if path else "")
    finally:
        arr.leave_tmp(prev)


def _studio(sc, target_z=1.2):
    cam = bpy.data.objects.get("Thief_QA_Cam")
    if not cam:
        cam = bpy.data.objects.new("Thief_QA_Cam", bpy.data.cameras.new("Thief_QA_Cam")); sc.collection.objects.link(cam)
        sun = bpy.data.objects.new("Thief_QA_Sun", bpy.data.lights.new("Thief_QA_Sun", 'SUN')); sc.collection.objects.link(sun)
        sun.data.energy = 3.5; sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    sc.camera = cam
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x = 600; sc.render.resolution_y = 800; sc.render.film_transparent = False
    if not sc.world:
        sc.world = bpy.data.worlds.new("Thief_QA_World")
    sc.world.color = (0.55, 0.55, 0.57)
    return cam


def _shoot(sc, cam, view, path, target_z=1.2):
    d = 5.2
    pos = {"front": Vector((0, -d, target_z)), "side": Vector((d, 0, target_z)), "back": Vector((0, d, target_z)),
           "34": Vector((d * 0.7, -d * 0.7, target_z))}[view]
    cam.location = pos
    cam.rotation_euler = (Vector((0, 0, target_z)) - pos).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 50
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def preview(poses, prefix, views=("front", "side")):
    """poses: list of (label, pose-dict-function(t), t). Renders <prefix>_<i>_<view>.png in Temp/qa."""
    sec, arr = modules()
    sc, prev, rig, meshes = load_thief(sec, arr)
    out = []
    try:
        cam = _studio(sc)
        rig.animation_data_create(); rig.animation_data.action = None
        for b in rig.pose.bones:
            b.rotation_mode = 'QUATERNION'
        for i, (label, fn, t) in enumerate(poses):
            p = fn(sec, arr, t)
            sec.apply(rig, p); bpy.context.view_layer.update()
            for v in views:
                path = os.path.join(QA, "%s_%d_%s.png" % (prefix, i, v))
                _shoot(sc, cam, v, path); out.append(path)
    finally:
        for n in ("Thief_QA_Cam", "Thief_QA_Sun"):
            o = bpy.data.objects.get(n)
            if o:
                d = o.data; bpy.data.objects.remove(o, do_unlink=True)
                (bpy.data.cameras if n.endswith("Cam") else bpy.data.lights).remove(d)
        w = bpy.data.worlds.get("Thief_QA_World")
        if w:
            bpy.data.worlds.remove(w)
        arr.leave_tmp(prev)
    print("rendered", out)
    return out


def preview_clip(fn_name, frames, ts, prefix, views=("front", "side")):
    """Builds one security_anim clip on the thief, measures how far the body travels per clip (the planted foot slides
    back that much: the game's stride), and renders it at the given normalized times."""
    sec, arr = modules()
    sc, prev, rig, meshes = load_thief(sec, arr)
    out = []
    try:
        act = sec.make(rig, "Thief_QA_Clip", frames, getattr(sec, fn_name))
        travel = 0.0; last = None
        for f in range(frames + 1):
            sc.frame_set(f); bpy.context.view_layer.update()
            fl, fr = rig.pose.bones["Foot_L"].head, rig.pose.bones["Foot_R"].head
            low = "L" if fl.z <= fr.z else "R"; y = (fl if low == "L" else fr).y
            if last and last[0] == low:
                travel += max(0.0, y - last[1])          # the character faces -Y: the planted foot goes to +Y
            last = (low, y)
        print("travel per clip (character units)", round(travel, 3))
        cam = _studio(sc)
        for i, t in enumerate(ts):
            sc.frame_set(int(round(t * frames))); bpy.context.view_layer.update()
            for v in views:
                path = os.path.join(QA, "%s_%d_%s.png" % (prefix, i, v))
                _shoot(sc, cam, v, path); out.append(path)
    finally:
        for n in ("Thief_QA_Cam", "Thief_QA_Sun"):
            o = bpy.data.objects.get(n)
            if o:
                d = o.data; bpy.data.objects.remove(o, do_unlink=True)
                (bpy.data.cameras if n.endswith("Cam") else bpy.data.lights).remove(d)
        w = bpy.data.worlds.get("Thief_QA_World")
        if w:
            bpy.data.worlds.remove(w)
        a = bpy.data.actions.get("Thief_QA_Clip")
        if a:
            bpy.data.actions.remove(a)
        arr.leave_tmp(prev)
    return out
