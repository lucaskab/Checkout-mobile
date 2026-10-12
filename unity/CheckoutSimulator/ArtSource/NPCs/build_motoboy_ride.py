"""The new motoboy sculpt seated on the delivery bike (Lucas 12/10: replace the rider of the bike).

Run: blender -b --factory-startup --python ArtSource/NPCs/build_motoboy_ride.py -- [preview|export]

The bike model Assets/Resources/CheckoutDelivery/delivery_bike_riding.fbx stays as it is: this builds only the
rider, in the bike's own frame (the bike faces -Y, wheels on z=0), as a static posed mesh:
  * the motoboy sculpt rigged by build_npcs.py (same skeleton and weights as the crew),
  * scaled like the old rider (2.4 units -> 0.72 = a 1.73 m rider),
  * seated with IK: hips on the seat, wrists on the grips, ankles on the pegs, leaning in;
and exports Assets/Resources/CheckoutDelivery/delivery_rider.fbx (texture embedded). CheckoutCourier hides the
old rider meshes of the bike (fx_riding_DK_courier, fx_riding_DK_helm_*) and puts this one on the seat.
The grips, seat and pegs are measured on the bike model itself, so the hands land on the real handlebar.
"""
import bpy, os, sys, json, math
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["NPC_NO_MAIN"] = "1"
NPC = {"__file__": os.path.join(HERE, "build_npcs.py"), "__name__": "build_npcs"}
exec(open(NPC["__file__"]).read(), NPC)
PROJECT = NPC["PROJECT"]
BIKE = os.path.join(PROJECT, "Assets", "Resources", "CheckoutDelivery", "delivery_bike_riding.fbx")
OUT = os.path.join(PROJECT, "Assets", "Resources", "CheckoutDelivery", "delivery_rider.fbx")
PREVIEWS = NPC["PREVIEWS"]
CS = .72
OLD_RIDER = ("fx_riding_DK_courier", "fx_riding_DK_helm")
V = NPC["V"]


def bbox(objs, keep=lambda v: True):
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    pts = [p for p in pts if keep(p)]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def main():
    mode = (sys.argv[sys.argv.index("--") + 1:] or ["preview"])[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = NPC["FPS"]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=BIKE)
    bike = [o for o in set(bpy.data.objects) - before if o.type == 'MESH']
    old = [o for o in bike if o.name.startswith(OLD_RIDER)]
    grip = next(o for o in bike if o.name.endswith("DB_grip"))
    seat = next(o for o in bike if o.name.endswith("DB_seat"))
    # Landmarks on the bike: grip centres per side, the seat top, the old rider's feet (on the pegs).
    grips = {s: (lambda b: (b[0] + b[1]) / 2)(bbox([grip], lambda p, s=s: p.x * s > .05)) for s in (1, -1)}
    seat_lo, seat_hi = bbox([seat])
    courier = next(o for o in old if o.name.endswith("DK_courier"))
    feet = {s: bbox([courier], lambda p, s=s: p.z < .46 and p.x * s > 0) for s in (1, -1)}
    for o in old:
        o.hide_render = True; o.hide_set(True)

    L_ = NPC
    mesh = L_["load_lite"]("motoboy"); L = L_["measure"](mesh)
    rig, others = L_["import_rig"]("Worker_Delivery")
    for o in others:
        bpy.data.objects.remove(o, do_unlink=True)
    side = L_["fit_rig"](rig, L)
    L_["skin_weights"](mesh, L, side)
    body = L_["bind"](mesh, rig, "Motoboy")
    r = L_["Rig"](rig); r.set_hang(L["half_hip"])
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'

    # Hips on the seat: the torso pivot (the hip joints' height) sits a little above the seat top, toward its front.
    seat_y = seat_lo.y + .30 * (seat_hi.y - seat_lo.y)
    hip_world = Vector((0, seat_y, seat_hi.z + .085))
    rig.scale = (CS, CS, CS)
    rig.location = hip_world - r.pivot * CS
    bpy.context.view_layer.update()
    A = lambda w: (Vector(w) - rig.location) / CS          # bike frame -> armature space (no rotation)

    p = L_["Pose"](r).torso(lean=30).head(nod=-16)
    for s in (1, -1):
        g = grips[s] + V(0, .03, .025)                      # the wrist sits just behind and above the grip
        p.hand(s, A(g), pole=V(s * 1, .45, -.55), world=True, bend=-12)
        lo, hi = feet[s]
        ankle = V((lo.x + hi.x) / 2, lo.y + .62 * (hi.y - lo.y), lo.z + .085)
        p.feet_abs = getattr(p, "feet_abs", {})
        p.feet_abs[s] = A(ankle)
    # Solve with absolute feet (the crew poses use offsets from the rest ankle).
    solve0 = L_["solve"]

    def solve_abs(pose):
        Aq = solve0(pose)
        T = L_["_rot"](pose.lean, pose.turn, pose.tilt); piv = r.pivot + V(0, 0, pose.lift)
        carry = lambda pt: piv + T @ (pt - r.pivot)
        swing = lambda parent, rest_dir, want: (parent @ rest_dir).rotation_difference(want) @ parent
        for s in (1, -1):
            hip = carry(r.hip[s])
            knee, ank = L_["two_bone"](hip, pose.feet_abs[s], r.l_th, r.l_sh, T @ V(s * .35, -1, .2))
            Aq[r.th[s]] = swing(T, r.knee[s] - r.hip[s], knee - hip)
            Aq[r.sh[s]] = swing(Aq[r.th[s]], r.ankle[s] - r.knee[s], ank - knee)
            from mathutils import Quaternion
            Aq[r.ft[s]] = Quaternion(V(1, 0, 0), math.radians(-8))
        return Aq
    L_["solve"] = solve_abs
    rig.animation_data_create(); act = bpy.data.actions.new("Ride"); rig.animation_data.action = act
    L_["put"](rig, 1, p, {})
    bpy.context.scene.frame_set(1); bpy.context.view_layer.update()

    # Bake the pose into a static mesh in the bike frame.
    dg = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(body.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    rider = bpy.data.objects.new("delivery_rider", baked); bpy.context.collection.objects.link(rider)
    for m in baked.materials:
        if m:
            m.name = "MotoboyRider"          # not "paint"/"body": CheckoutCourier.TintPaint must leave it alone
    rider.matrix_world = body.matrix_world.copy()
    bpy.context.view_layer.update()
    rider.data.transform(rider.matrix_world); rider.matrix_world = Matrix()
    body.hide_render = True; body.hide_set(True)
    info = {"grips": {s: list(map(lambda x: round(x, 3), grips[s])) for s in grips}, "seat_top": round(seat_hi.z, 3),
            "rider_tris": sum(len(f.vertices) - 2 for f in baked.polygons)}
    hands = {s: rig.matrix_world @ rig.pose.bones[r.hd[s]].head for s in (1, -1)}
    info["wrist_to_grip_cm"] = {s: round((hands[s] - grips[s]).length * 100, 1) for s in (1, -1)}

    # Preview: bike + new rider, three views.
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 760, 760
    world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.80, .85, .89, 1)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN')); sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30)); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.5; sc.camera = cam
    shots = []
    for i, yaw in enumerate((-90, -35, 30, 180)):
        a = math.radians(yaw)
        cam.location = (math.sin(a) * 8, -math.cos(a) * 8, 1.05); cam.rotation_euler = (math.radians(90), 0, a)
        path = os.path.join(PREVIEWS, f"motoboy_ride_{i}.png"); sc.render.filepath = path
        bpy.ops.render.render(write_still=True); shots.append((str(yaw), path))
    NPC["contact_sheet"](shots, os.path.join(PREVIEWS, "motoboy_ride_sheet.png"))
    if mode == "export":
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        rider.hide_set(False); rider.select_set(True); bpy.context.view_layer.objects.active = rider
        bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={'MESH'}, axis_forward='-Z', axis_up='Y',
                                 apply_scale_options='FBX_SCALE_NONE', bake_space_transform=True, path_mode='STRIP',
                                 mesh_smooth_type='OFF', use_mesh_modifiers=True)
        # The texture goes next to it: the game paints the rider with its own toon material (delivery_rider.mat).
        img = next((n.image for m in baked.materials if m and m.node_tree for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
        if img is not None:
            img.filepath_raw = os.path.join(os.path.dirname(OUT), "delivery_rider.png"); img.file_format = 'PNG'; img.save()
        info["fbx"] = OUT
    print("MOTOBOY_RIDE_OK", json.dumps(info))


main()
