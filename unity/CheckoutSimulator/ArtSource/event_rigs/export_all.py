"""Export runner for the event rigs + interactive events (Oct 2026).

    blender -b --factory-startup --python export_all.py -- rigs [window] [inspector] [moves] [qa]

rigs      : event_rigs builders (vehicles, bucket truck, backhoe) -> Assets/Resources/EventRigs/Rig_*.fbx
window    : events_interactive/window_sale.py -> Rig_JamCar.fbx, Rig_Cooler.fbx (+ JamCar_Driver / JamCar_Interior /
            Vendor_Cooler atlases in EventProps2) and the props Vendor_Bottle, Vendor_Can, Vendor_Coins, Horn_Icon
inspector : events_interactive/inspector.py -> Inspector.fbx (+ Inspector / Inspector_Coat atlases) and the props
            Inspect_Clipboard, Inspect_Pen, Inspect_Stamp, Inspect_Seal, Inspect_WarningNotice, Inspect_FineNotice, Inspect_Marker
moves     : EventMoves.fbx = characters.py clips + Vendor_* + Inspect_* on the Customer_01_Rig skeleton
qa        : re-imports every written FBX into a fresh scene, checks names / bones / clips / tris and renders
            Temp/qa/export_check.png

Every line starting with "STAT " is a JSON record for the report. Nothing here touches a .blend file.
"""
import sys, os, json, math, time, traceback, shutil, importlib
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
EI = os.path.join(ART, "events_interactive")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(ART)))
UNITY = os.path.join(REPO, "unity", "CheckoutSimulator")
PROPS2 = os.path.join(UNITY, "Assets", "Resources", "EventProps2")
RIGS_OUT = os.path.join(UNITY, "Assets", "Resources", "EventRigs")
CHARS = os.path.join(UNITY, "Assets", "Art", "Characters", "Meshy")
QA = os.path.join(UNITY, "Temp", "qa")
for p in (ART, EI, os.path.join(ART, "events_v2"), os.path.join(REPO, "scripts", "blender")):
    if p not in sys.path:
        sys.path.insert(0, p)
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["qa"]
T0 = time.time()
WRITTEN = []


def stat(**kw):
    kw["t"] = round(time.time() - T0, 1)
    print("STAT " + json.dumps(kw, default=str), flush=True)


def load_kits():
    import ei_kit as E
    return E, E.rk, E.ch


def exec_script(E, path, name):
    """events_interactive scripts reload ei_kit on import; keep the one instance so rk / ch are shared."""
    real = importlib.reload
    importlib.reload = lambda m: m
    try:
        g = {"__name__": name, "__file__": path}
        exec(open(path, encoding="utf-8").read(), g)
    finally:
        importlib.reload = real
    return g


def sel(objs, active=None):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def ctx(rk, **kw):
    d = rk._ctx(); d.update(kw); return d


def apply_mods(rk, o):
    """Applies every modifier but the armature (export_rig writes meshes without modifiers)."""
    for m in list(o.modifiers):
        if m.type == 'ARMATURE':
            continue
        sel([o])
        with bpy.context.temp_override(**ctx(rk, active_object=o, object=o, selected_objects=[o], selected_editable_objects=[o])):
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except RuntimeError as e:
                print("WARN modifier_apply", o.name, m.name, e, flush=True); o.modifiers.remove(m)


def reset_pose(arm):
    arm.animation_data_create(); arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.scene.frame_set(1); bpy.context.view_layer.update()


def tris_of(objs):
    t = 0
    for o in objs:
        if o.type == 'MESH':
            o.data.calc_loop_triangles(); t += len(o.data.loop_triangles)
    return t


def bake_atlas(rk, parts, name, size=1024):
    """Like events_kit.export_prop, for parts that must stay separate objects (rig parts): smart-UVs them together,
    bakes the diffuse colour of their procedural materials into EventProps2/<name>_BaseColor.png and gives every
    part the single material <name>_Mat with that image."""
    for o in parts:
        apply_mods(rk, o)
    sel(parts)
    with bpy.context.temp_override(**ctx(rk, active_object=parts[0], object=parts[0], selected_objects=parts, selected_editable_objects=parts)):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002, scale_to_bounds=False)
        bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
        bpy.ops.object.mode_set(mode='OBJECT')
    img_name = name + "_BaseColor"
    for im in list(bpy.data.images):
        if im.name.startswith(img_name):
            bpy.data.images.remove(im)
    img = bpy.data.images.new(img_name, size, size)
    added = []
    mats = {m for o in parts for m in o.data.materials if m}
    for m in mats:
        if not m.use_nodes:
            m.use_nodes = True
        nd = m.node_tree.nodes.new("ShaderNodeTexImage"); nd.image = img; m.node_tree.nodes.active = nd; added.append((m, nd))
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 1
    b = sc.render.bake; b.use_pass_direct = False; b.use_pass_indirect = False; b.use_pass_color = True; b.margin = 4; b.use_clear = True
    sel(parts)
    with bpy.context.temp_override(**ctx(rk, active_object=parts[0], object=parts[0], selected_objects=parts, selected_editable_objects=parts)):
        bpy.ops.object.bake(type='DIFFUSE')
    for m, nd in added:
        m.node_tree.nodes.remove(nd)
    os.makedirs(PROPS2, exist_ok=True)
    img.filepath_raw = os.path.join(PROPS2, img_name + ".png"); img.file_format = 'PNG'; img.save()
    WRITTEN.append(img.filepath_raw)
    am = bpy.data.materials.get(name + "_Mat") or bpy.data.materials.new(name + "_Mat"); am.use_nodes = True
    for nd in list(am.node_tree.nodes):
        if nd.bl_idname == "ShaderNodeTexImage":
            am.node_tree.nodes.remove(nd)
    tex = am.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = img
    am.node_tree.links.new(tex.outputs["Color"], am.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    for o in parts:
        o.data.materials.clear(); o.data.materials.append(am)
        for p in o.data.polygons:
            p.material_index = 0
    sc.render.engine = 'BLENDER_EEVEE'
    return img.filepath_raw


def copy_texture(src_png, name):
    """A character's painted albedo as an EventProps2 atlas (the game textures rig parts by their name prefix)."""
    dst = os.path.join(PROPS2, name + "_BaseColor.png")
    shutil.copyfile(src_png, dst); WRITTEN.append(dst)
    return dst


def export_props(EK, objs, size=512):
    """objs = {PropName: object}; each is exported with events_kit.export_prop (own atlas, front turned to Unity +Z).
    Returns {PropName: (stats, atlas-UV mesh copy)} - the copy keeps the baked UVs for rig-held versions."""
    out = {}
    for name, o in objs.items():
        c = EK.prop_collection(name)
        if o.name == name:
            o.name = "built_" + name             # export_prop names its joined copy after the prop: keep that name free
        src = bpy.data.objects.new("src_" + name, o.data.copy()); src.matrix_world = Matrix.Identity(4)
        c.objects.link(src)
        st = EK.export_prop(name, size=size)
        j = bpy.data.objects[name]
        held = j.data.copy(); held.name = name + "__held"
        out[name] = (st, held)
        WRITTEN.extend([st["fbx"], st["atlas"]])
        stat(kind="prop", name=name, tris=st["tris"], dims=st["dims"], atlas=os.path.basename(st["atlas"]), fbx=st["fbx"])
        bpy.data.collections.remove(bpy.data.collections["EP " + name])
    # export_prop excludes the other view-layer collections; nothing else lives in collections here
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = False
    return out


def bone_space(arm, bone):
    """Matrix of a bone's tail frame in world space in the current pose (the space of bone-parented children)."""
    pb = arm.pose.bones[bone]
    return arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))


def rig_summary(arm, parts, acts):
    return {"bones": [b.name for b in arm.data.bones], "parts": [(o.name, len(o.data.vertices)) for o in parts],
            "clips": {a.name: [int(a.frame_start), int(a.frame_end)] for a in acts}, "tris": tris_of(parts)}


# ============================================================================================ rigs (B)
def do_rigs(E, rk, ch):
    veh = E._script_module("ev_vehicles", os.path.join(ART, "event_rigs", "vehicles.py"), base=rk.__dict__)
    bt = E._script_module("ev_bucket", os.path.join(ART, "event_rigs", "bucket_truck.py"), base=rk.__dict__)
    bh = E._script_module("ev_backhoe", os.path.join(ART, "event_rigs", "backhoe.py"), base=rk.__dict__)
    builders = dict(veh.BUILDERS)
    builders["Rig_BucketTruck"] = bt.build
    builders["Rig_Backhoe"] = bh.build
    for name, fn in builders.items():
        try:
            arm, parts, acts = fn()
            reset_pose(arm)                      # the builders leave the pose at their last frame: export from the rest pose
            summ = rig_summary(arm, parts, acts)
            res = rk.export_rig(name, arm, parts, acts)
            WRITTEN.append(res["fbx"])
            stat(kind="rig", name=name, fbx=res["fbx"], **summ)
        except Exception:
            traceback.print_exc(); stat(kind="rig", name=name, error=traceback.format_exc()[-800:])


# ============================================================================================ window sale (C)
def do_window(E, rk, ch):
    import events_kit as EK
    WS = exec_script(E, os.path.join(EI, "window_sale.py"), "window_sale")
    rk.reset(); bpy.context.scene.frame_set(1)
    car, car_parts, info = WS["rig_car"]()
    car_acts = WS["car_clips"](car)
    reset_pose(car)
    bust = car_parts[-1]
    extra = [o for o in car_parts if "__Body_" in o.name]          # interior, seat, sill
    plain = [o for o in car_parts if o is not bust and o not in extra]
    # the game textures a part "<Prop>__<part>" with EventProps2/<Prop>_BaseColor: the car parts keep Transito_Car,
    # the driver bust gets a copy of its character's albedo, the cabin bits a small baked atlas
    bust.name = "JamCar_Driver__Bust"
    copy_texture(os.path.join(CHARS, WS["DRIVER"] + ".png"), "JamCar_Driver")
    for o in extra:
        o.name = "JamCar_Interior__" + o.name.split("__Body_")[1]
    bake_atlas(rk, extra, "JamCar_Interior", size=256)
    summ = rig_summary(car, car_parts, car_acts)
    summ["driver_tris"] = tris_of([bust]); summ["car_tris"] = tris_of(plain + extra)
    summ["window_pane_lo_z"] = round(info["W"](info["glass"].lo).z, 3)
    res = rk.export_rig("Rig_JamCar", car, car_parts, car_acts)
    WRITTEN.append(res["fbx"])
    stat(kind="rig", name="Rig_JamCar", fbx=res["fbx"], **summ)
    # cooler
    cool, cool_parts, cool_acts = WS["cooler"]()
    reset_pose(cool)
    cool_parts[0].name = "Vendor_Cooler__Body"; cool_parts[1].name = "Vendor_Cooler__Lid"
    bake_atlas(rk, cool_parts, "Vendor_Cooler", size=1024)
    summ = rig_summary(cool, cool_parts, cool_acts)
    res = rk.export_rig("Rig_Cooler", cool, cool_parts, cool_acts)
    WRITTEN.append(res["fbx"])
    # where the vendor's Torso bone carries it (window_sale.build): local matrix in the Torso bone space of a 0.72-scaled actor
    M = Matrix.Translation((0.46, -0.02, 0.86)) @ Matrix.Rotation(math.radians(-90), 4, 'Z') @ Matrix.Scale(1 / WS["ACTOR"], 4)
    summ["torso_local_matrix_blender"] = [[round(v, 4) for v in row] for row in M]
    stat(kind="rig", name="Rig_Cooler", fbx=res["fbx"], **summ)
    # small props
    props = {"Vendor_Bottle": WS["bottle"](), "Vendor_Can": WS["can"](), "Vendor_Coins": WS["coins"](), "Horn_Icon": WS["horn_icon"]()}
    for o in props.values():
        for p in o.data.polygons:
            p.use_smooth = True
    export_props(EK, props, size=512)


# ============================================================================================ inspector (D)
def do_inspector(E, rk, ch):
    import events_kit as EK
    INS = exec_script(E, os.path.join(EI, "inspector.py"), "inspector")
    arm, body, clothes, P, acts, stats = INS["build"]()
    reset_pose(arm)
    # props first (their atlas UV copies ride in the hands of the rig)
    names = {"clipboard": "Inspect_Clipboard", "pen": "Inspect_Pen", "stamp": "Inspect_Stamp", "seal": "Inspect_Seal",
             "warning": "Inspect_WarningNotice", "fine": "Inspect_FineNotice", "marker": "Inspect_Marker"}
    held_local = {}
    for key in ("clipboard", "pen", "stamp", "seal"):
        o = P[key]
        held_local[key] = (o.parent_bone, bone_space(arm, o.parent_bone).inverted() @ o.matrix_world)
    exported = export_props(EK, {names[k]: P[k] for k in names}, size=512)
    held = []
    for key, (bone, local) in held_local.items():
        name = names[key]
        h = bpy.data.objects.new(name + "__Held", exported[name][1]); bpy.context.scene.collection.objects.link(h)
        h.parent = arm; h.parent_type = 'BONE'; h.parent_bone = bone
        h.matrix_parent_inverse = Matrix.Identity(4); h.matrix_basis = local
        bpy.context.view_layer.update()
        err = (h.matrix_world.translation - P[key].matrix_world.translation).length
        stat(kind="held", name=h.name, bone=bone, placement_error_m=round(err, 5),
             local_pos=[round(v, 4) for v in local.translation], local_rot_deg=[round(math.degrees(a), 2) for a in local.to_euler()])
        held.append(h)
    for key in names:
        bpy.data.objects.remove(P[key], do_unlink=True)
    # clothes: one skinned mesh, one baked atlas
    for o in clothes:
        apply_mods(rk, o)
    sel(clothes)
    with bpy.context.temp_override(**ctx(rk, active_object=clothes[0], object=clothes[0], selected_objects=clothes, selected_editable_objects=clothes)):
        bpy.ops.object.join()
    coat = clothes[0]; coat.name = "Inspector_Coat__Clothes"; coat.data.name = coat.name
    assert any(m.type == 'ARMATURE' for m in coat.modifiers), "clothes lost the armature modifier"
    bake_atlas(rk, [coat], "Inspector_Coat", size=1024)
    body.name = "Inspector__Body"; body.data.name = body.name
    copy_texture(os.path.join(CHARS, INS["BASE"] + ".png"), "Inspector")
    reset_pose(arm)
    parts = [body, coat] + held
    summ = rig_summary(arm, parts, acts)
    summ["body_tris"] = tris_of([body]); summ["clothes_tris"] = tris_of([coat]); summ["held_tris"] = tris_of(held)
    res = rk.export_rig("Inspector", arm, parts, acts)
    WRITTEN.append(res["fbx"])
    stat(kind="rig", name="Inspector", fbx=res["fbx"], **summ)


# ============================================================================================ event moves (E)
def do_moves(E, rk, ch):
    WS = exec_script(E, os.path.join(EI, "window_sale.py"), "window_sale")
    INS = exec_script(E, os.path.join(EI, "inspector.py"), "inspector")
    # window_sale's foot-height solver (legs may carry dz / toe): characters.put looks `solve` up in its own globals
    ch.put.__globals__["solve"] = WS["solve_z"]
    clips = dict(ch.CLIPS); clips.update(WS["VCLIPS"]); clips.update(INS["CLIPS"])
    arm, meshes = ch.load_skeleton()
    acts = E.bake_clips(arm, clips)
    arm.name = "Customer_01_Rig"
    reset_pose(arm)
    res = ch.export_moves(arm, acts)
    WRITTEN.append(res["fbx"])
    stat(kind="moves", name="EventMoves", fbx=res["fbx"], bones=[b.name for b in arm.data.bones],
         clips={a.name: [int(a.frame_start), int(a.frame_end)] for a in acts}, arms_only=[n for n, v in clips.items() if v[2]])


# ============================================================================================ QA
def fbx_check(path):
    """Imports one FBX into the current (fresh) scene; returns a record of what came in."""
    before_o = set(bpy.data.objects); before_a = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before_o]
    acts = [a for a in bpy.data.actions if a not in before_a]
    arms = [o for o in new if o.type == 'ARMATURE']
    meshes = [o for o in new if o.type == 'MESH']
    rec = {"file": os.path.basename(path), "objects": [o.name for o in new], "armatures": [a.name for a in arms],
           "bones": [b.name for b in arms[0].data.bones] if arms else [],
           "meshes": [(o.name, len(o.data.loop_triangles) if o.data.calc_loop_triangles() is None else 0,
                       "skinned" if any(m.type == 'ARMATURE' for m in o.modifiers) else ("bone:" + o.parent_bone if o.parent_type == 'BONE' else "-"),
                       bool(o.data.uv_layers)) for o in meshes],
           "clips": {a.name: [int(a.frame_range[0]), int(a.frame_range[1])] for a in acts},
           "tris": sum(len(o.data.loop_triangles) for o in meshes)}
    lo = Vector((1e9,) * 3); hi = -lo
    dg = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        ev = o.evaluated_get(dg)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    rec["bounds_lo"] = [round(v, 2) for v in lo]; rec["bounds_hi"] = [round(v, 2) for v in hi]
    rec["dims"] = [round(v, 2) for v in (hi - lo)]
    rec["scale"] = [round(v, 3) for v in (arms[0].scale if arms else meshes[0].scale)]
    return new, acts, rec


def texture_like_unity(objs):
    """CheckoutEventAssets.Rig: a part "<Prop>__<part>" (or the file's prop) is painted with EventProps2/<Prop>_BaseColor."""
    for o in objs:
        if o.type != 'MESH':
            continue
        name = o.name; cut = name.find("__"); prop = name[:cut] if cut > 0 else name
        if "." in prop: prop = prop.split(".")[0]
        png = os.path.join(PROPS2, prop + "_BaseColor.png")
        m = bpy.data.materials.new("QA_" + prop); m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = .7
        if os.path.exists(png):
            tex = m.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(png, check_existing=True)
            m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            bsdf.inputs["Base Color"].default_value = (1, 0, 1, 1)      # magenta = missing atlas
            print("QA missing atlas", prop, "for", o.name, flush=True)
        o.data.materials.clear(); o.data.materials.append(m)
        for p in o.data.polygons:
            p.material_index = 0


def do_qa(E, rk, ch, files):
    import numpy as np
    os.makedirs(QA, exist_ok=True)
    shots = []; records = []
    poses = {"Rig_JamCar": ("Car_WindowDown", 18), "Rig_Cooler": ("Cooler_Open", 18), "Inspector": ("Inspect_Write", 20),
             "Rig_Backhoe": ("Dig", 88), "Rig_BucketTruck": ("Work", 54), "Rig_CityBus": ("DoorsOpen", 18), "Rig_SchoolBus": ("DoorsOpen", 18),
             "EventMoves": ("Vendor_WalkCarry", 9)}
    for path in files:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = E.studio(res=(520, 400))
        try:
            new, acts, rec = fbx_check(path)
        except Exception:
            rec = {"file": os.path.basename(path), "error": traceback.format_exc()[-600:]}
            records.append(rec); stat(kind="qa", **rec); continue
        texture_like_unity(new)
        name = os.path.splitext(os.path.basename(path))[0]
        arms = [o for o in new if o.type == 'ARMATURE']
        shown = name
        if arms and name in poses:
            clip, f = poses[name]
            act = next((a for a in acts if a.name.endswith(clip)), None)
            if act:
                arms[0].animation_data_create(); arms[0].animation_data.action = act
                sc.frame_set(f); shown = f"{name}  {clip} f{f}"
        if name == "EventMoves":
            arms[0].data.display_type = 'OCTAHEDRAL'
            rec["skeleton_only"] = True
        meshes = [o for o in new if o.type == 'MESH']
        direction = (0.9, -1.0, 0.6) if "Car" in name or "Bus" in name or "Van" in name or "Truck" in name or "Backhoe" in name else (0.6, -1.0, 0.45)
        if meshes:
            E.frame_objects(meshes, direction=direction, lens=50, pad=1.2)
        else:
            E.aim((0, 0, 1.2), (0.6, -1.0, 0.45), 6.0, lens=50)
        E.label(f"{shown}  {rec['tris']} tris  {rec['dims'][0]}x{rec['dims'][1]}x{rec['dims'][2]} m", 0.05)
        shots.append(E.render(os.path.join(QA, "export", f"qa_{name}.png")))
        records.append(rec); stat(kind="qa", **rec)
    out = E.contact_sheet(shots, os.path.join(QA, "export_check.png"), cols=5)
    stat(kind="qa_sheet", path=out, n=len(shots))


# ============================================================================================ main
try:
    E, rk, ch = load_kits()
    for n in ("Cube", "Light", "Camera"):
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    for mode in argv:
        if mode == "rigs":
            do_rigs(E, rk, ch)
        elif mode == "window":
            do_window(E, rk, ch)
        elif mode == "inspector":
            do_inspector(E, rk, ch)
        elif mode == "moves":
            do_moves(E, rk, ch)
        elif mode == "qa":
            names = ["Rig_Car", "Rig_CarBlue", "Rig_CarYellow", "Rig_CarWhite", "Rig_CarTeal", "Rig_CarGreen", "Rig_CityBus", "Rig_SchoolBus",
                     "Rig_BoxTruck", "Rig_TelecomVan", "Rig_InspectionCar", "Rig_SoundVan", "Rig_BucketTruck", "Rig_Backhoe",
                     "Rig_JamCar", "Rig_Cooler", "Inspector", "EventMoves"]
            files = [os.path.join(RIGS_OUT, n + ".fbx") for n in names]
            files += [os.path.join(PROPS2, n + ".fbx") for n in ("Vendor_Bottle", "Vendor_Can", "Vendor_Coins", "Horn_Icon", "Inspect_Clipboard",
                                                                  "Inspect_Pen", "Inspect_Stamp", "Inspect_Seal", "Inspect_WarningNotice", "Inspect_FineNotice", "Inspect_Marker")]
            do_qa(E, rk, ch, [f for f in files if os.path.exists(f)])
    stat(kind="done", written=WRITTEN)
    print("DONE", flush=True)
except Exception:
    traceback.print_exc(); print("FAILED", flush=True)
