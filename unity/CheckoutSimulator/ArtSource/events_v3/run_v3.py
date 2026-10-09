# headless runner for events_v3: blender -b --factory-startup --python run_v3.py -- shot Transito_Car ... | lineup | closeups | tris ...
# Review pictures go to ArtSource/Review/vehicles_v3/. Nothing is exported unless mode == export.
import sys, os, traceback, time, math, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(ART)))
for pth in (ART, os.path.join(ART, "events_v2"), os.path.join(REPO, "scripts", "blender")):
    sys.path.insert(0, pth)
import bpy
from mathutils import Vector, Matrix
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
mode, names = argv[0], argv[1:]
REVIEW = os.path.join(ART, "Review", "vehicles_v3")
MM = os.path.join(REPO, "unity", "CheckoutSimulator", "Assets", "Art", "Models", "MapModels")
os.makedirs(REVIEW, exist_ok=True)
t0 = time.time()
SHOT_FILE = {"Rush_CityBus": "bus", "Excursao_SchoolBus": "school_bus", "Ofertas_BoxTruck": "box_truck", "Maquininha_TelecomVan": "telecom_van",
             "Vigilancia_Car": "inspection_car", "Energia_BucketTruck": "bucket_truck", "Som_Van": "sound_van", "Obras_Backhoe": "backhoe",
             "Transito_Car": "car"}


def load_v3():
    import events_kit as E
    spec = importlib.util.spec_from_file_location("vehicles3", os.path.join(HERE, "vehicles.py"))
    V3 = importlib.util.module_from_spec(spec); sys.modules["vehicles3"] = V3; spec.loader.exec_module(V3)
    return E, V3


def studio(res=(1400, 900)):
    sc = bpy.context.scene
    for n in ("QA_Cam", "QA_Sun", "QA_Fill", "QA_Ground", "Cube", "Light", "Camera"):
        if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    cam = bpy.data.objects.new("QA_Cam", bpy.data.cameras.new("QA_Cam")); sc.collection.objects.link(cam); sc.camera = cam
    sun = bpy.data.objects.new("QA_Sun", bpy.data.lights.new("QA_Sun", 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = 3.0; sun.rotation_euler = (math.radians(48), 0, math.radians(32))
    fill = bpy.data.objects.new("QA_Fill", bpy.data.lights.new("QA_Fill", 'SUN')); sc.collection.objects.link(fill)
    fill.data.energy = 1.1; fill.rotation_euler = (math.radians(60), 0, math.radians(210))
    w = bpy.data.worlds.get("QA_World") or bpy.data.worlds.new("QA_World"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.80, 0.84, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    import bmesh
    me = bpy.data.meshes.new("QA_Ground"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60); bm.to_mesh(me); bm.free()
    g = bpy.data.objects.new("QA_Ground", me); sc.collection.objects.link(g)
    gm = bpy.data.materials.get("QA_GroundMat") or bpy.data.materials.new("QA_GroundMat"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.50, 0.51, 0.53, 1); gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    me.materials.append(gm)
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    return cam


def bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != 'MESH': continue
        oe = o.evaluated_get(dg)
        for c in oe.bound_box:
            w = oe.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def aim(cam, lo, hi, direction=(0.62, -1.0, 0.72), lens=50, pad=1.25, target=None):
    c = target or (lo + hi) / 2; size = (hi - lo).length
    d = Vector(direction).normalized(); cam.data.lens = lens
    cam.location = c + d * size * pad
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()


def render(path):
    bpy.context.scene.render.filepath = path; bpy.ops.render.render(write_still=True); return path


def tris_of(objs):
    dg = bpy.context.evaluated_depsgraph_get(); t = 0
    for o in objs:
        if o.type == 'MESH':
            me = o.evaluated_get(dg).data; me.calc_loop_triangles(); t += len(me.loop_triangles)
    return t


def build(E, V3, n):
    c = E.prop_collection(n); V3.mats(); objs = V3.PROPS[n][0](c)
    return c, [o for o in c.all_objects]


def ref_car(name, x, y, length):
    """One of the game's own traffic cars (MapModels), scaled to `length` m, standing at (x, y) on the ground, nose +X."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(MM, name, name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    img = bpy.data.images.load(os.path.join(MM, name, name + "_BaseColor.png"))
    mat = bpy.data.materials.new("REF_" + name); mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = img
    mat.node_tree.links.new(tex.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    for o in new:
        if o.type == 'MESH': o.data.materials.clear(); o.data.materials.append(mat)
    roots = [o for o in new if o.parent is None]
    lo, hi = bounds(new); size = hi - lo
    # the model's length runs along its Y: turn it to +X
    s = length / size.y
    for r in roots:
        r.matrix_world = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'Z') @ Matrix.Scale(s, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) @ r.matrix_world
    return new


def sheet(paths, out, cols=2):
    """Tiles rendered PNGs (same size) into one image with the compositor-free way: numpy via bpy images."""
    import numpy as np
    ims = [bpy.data.images.load(p) for p in paths]
    w, h = ims[0].size; rows = (len(ims) + cols - 1) // cols
    canvas = np.zeros((rows * h, cols * w, 4), dtype=np.float32); canvas[:, :, 3] = 1
    for i, im in enumerate(ims):
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        r, cidx = i // cols, i % cols
        canvas[(rows - 1 - r) * h:(rows - r) * h, cidx * w:(cidx + 1) * w] = px
    outim = bpy.data.images.new("sheet", cols * w, rows * h); outim.pixels = canvas.ravel().tolist()
    outim.filepath_raw = out; outim.file_format = 'PNG'; outim.save()
    return out


try:
    E, V3 = load_v3()
    if mode == "shot":
        for n in names:
            c, objs = build(E, V3, n)
            cam = studio()
            lo, hi = bounds(objs)
            aim(cam, lo, hi, pad=1.45)
            path = render(os.path.join(REVIEW, SHOT_FILE.get(n, n) + ".png"))
            print("SHOT", n, path, "tris", tris_of(objs), "dims", [round(v, 2) for v in (hi - lo)], round(time.time() - t0, 1), flush=True)
            bpy.data.collections["EP " + n].hide_render = True
            for o in objs: o.hide_render = True
    elif mode == "closeups":
        n = names[0] if names else "Transito_Car"
        c, objs = build(E, V3, n)
        cam = studio(res=(1000, 800))
        lo, hi = bounds(objs)
        shots = []
        for i, (d, pad, target) in enumerate(((( .75, -1.0, 0.55), 1.1, None), ((0.0, -1.0, 0.25), 1.1, None), ((-0.75, -1.0, 0.5), 1.1, None),
                                               ((0.6, -1.0, 0.35), 0.42, Vector((lo.x + 0.7, lo.y + 0.3, 0.33))))):
            aim(cam, lo, hi, direction=d, pad=pad, target=target)
            shots.append(render(os.path.join(REVIEW, f"_cu_{i}.png")))
        # contact sheet 2x2
        sheet(shots, os.path.join(REVIEW, "car_closeups.png"), cols=2)
        print("CLOSEUPS tris", tris_of(objs), flush=True)
    elif mode == "lineup":
        cam = studio(res=(4200, 780))
        bpy.data.objects["QA_Ground"].scale = (4, 4, 1)
        order = ["Transito_Car", "Vigilancia_Car", "Som_Van", "Maquininha_TelecomVan", "Ofertas_BoxTruck", "Rush_CityBus",
                 "Excursao_SchoolBus", "Energia_BucketTruck", "Obras_Backhoe"]
        allobjs = []; x = 0.0
        # the game's own traffic cars first, same row, so the family resemblance is an honest side-by-side
        allobjs += ref_car("StylizedCar", x + 1.8, 0, 3.6); x += 4.9
        allobjs += ref_car("CartoonCar", x + 1.8, 0, 3.6); x += 4.9
        for n in order:
            c, objs = build(E, V3, n)
            lo, hi = bounds(objs)
            V3.put(objs, x=x - lo.x, y=0)
            x += (hi.x - lo.x) + 1.2; allobjs += objs
        lo, hi = bounds(allobjs)
        # orthographic 3/4 view: every vehicle at the same scale, nothing cut off
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 4200, 780
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = (hi.x - lo.x) * 1.04
        ctr = Vector(((lo.x + hi.x) / 2, 0.0, 1.3)); dvec = Vector((0.22, -1.0, 0.62)).normalized()
        cam.location = ctr + dvec * 90.0; cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
        print("LINEUP", render(os.path.join(REVIEW, "lineup.png")), round(time.time() - t0, 1), flush=True)
    elif mode == "tris":
        for n in names:
            c, objs = build(E, V3, n)
            lo, hi = bounds(objs); print("TRIS", n, tris_of(objs), [round(v, 2) for v in (hi - lo)], flush=True)
            agg = {}
            dg = bpy.context.evaluated_depsgraph_get()
            for o in objs:
                if o.type == 'MESH':
                    me = o.evaluated_get(dg).data; me.calc_loop_triangles()
                    key = o.name.rstrip("0123456789."); agg[key] = agg.get(key, 0) + len(me.loop_triangles)
            print("  ", sorted(agg.items(), key=lambda kv: -kv[1])[:16], flush=True)
    elif mode == "export":
        V3.export(names or None)
    print("DONE", round(time.time() - t0, 1), flush=True)
except Exception:
    traceback.print_exc(); print("FAILED", flush=True)

