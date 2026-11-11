"""Review renders for the pets / security assets: a soft light-grey studio (like the inspector turnarounds) and
contact sheets saved to unity/CheckoutSimulator/Temp/qa/pets/.

    exec(open(".../pets/pet_review.py").read())
    sheet(["Caramelo"], "caramelo_turn", views=[...])
"""
import bpy, math, os
from mathutils import Vector

QA = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/Temp/qa/pets"
os.makedirs(QA, exist_ok=True)


def studio():
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    try:
        sc.eevee.taa_render_samples = 48
        sc.eevee.use_shadows = True
    except Exception:
        pass
    w = sc.world or bpy.data.worlds.new("World"); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.80, 0.83, 0.88, 1); bg.inputs["Strength"].default_value = 0.9
    for n in ("QA_Key", "QA_Fill", "QA_Rim", "QA_Floor"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    def light(name, kind, energy, loc, rot, size=1.0, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, kind); d.energy = energy; d.color = color
        if kind == 'AREA':
            d.size = size
        if kind == 'SUN':
            d.angle = math.radians(8)
        o = bpy.data.objects.new(name, d); sc.collection.objects.link(o)
        o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
        return o
    light("QA_Key", 'SUN', 3.2, (2, -3, 4), (48, 0, 28), color=(1.0, 0.96, 0.90))
    light("QA_Fill", 'AREA', 260, (-2.5, -1.5, 1.5), (70, 0, -60), size=3, color=(0.85, 0.90, 1.0))
    light("QA_Rim", 'AREA', 220, (0.5, 3, 2.2), (-60, 0, 180), size=2)
    me = bpy.data.meshes.new("QA_Floor")
    me.from_pydata([(-15, -15, 0), (15, -15, 0), (15, 15, 0), (-15, 15, 0)], [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new("QA_Floor", me); sc.collection.objects.link(fl)
    m = bpy.data.materials.get("QA_FloorMat") or bpy.data.materials.new("QA_FloorMat"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.86, 0.88, 0.92, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    fl.data.materials.clear(); fl.data.materials.append(m)


def _bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        ev = o.evaluated_get(dg)
        if o.type == 'MESH':
            me = ev.to_mesh()
            pts += [ev.matrix_world @ v.co for v in me.vertices]
            ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def shot(objs, path, direction, res=(900, 900), lens=60, margin=1.15, focus=None, dist_scale=1.0):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("QA_Cam")
    if not cam:
        cam = bpy.data.objects.new("QA_Cam", bpy.data.cameras.new("QA_Cam")); sc.collection.objects.link(cam)
    cam.data.lens = lens
    sc.camera = cam
    lo, hi = _bounds(objs)
    c = (lo + hi) / 2 if focus is None else Vector(focus)
    r = (hi - lo).length / 2 * margin
    d = Vector(direction).normalized()
    fov = 2 * math.atan(18 / lens)
    dist = r / math.sin(fov / 2) * dist_scale
    cam.location = c + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.render.filepath = path
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    return path


def sheet(names, tag, views=None, res=(900, 900), **kw):
    objs = [bpy.data.objects[n] for n in names]
    views = views or [(0.35, -1, 0.22), (1, 0, 0.12), (0.7, 0.7, 0.3), (-0.5, -0.8, 0.6)]
    out = []
    for i, v in enumerate(views):
        out.append(shot(objs, os.path.join(QA, f"{tag}_{i}.png"), v, res=res, **kw))
    return out


CHARS = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/Assets/Art/Characters/Meshy"


def scale_buddy(name="Customer_07", x=0.75, y=0.05, scale=0.72):
    """One of the game's customers next to the asset, at the game's scale (2.4 m model x 0.72), for size."""
    obj = bpy.data.objects.get("QA_Buddy")
    if obj:
        return obj
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CHARS, name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    root = next(o for o in new if o.parent is None)
    root.name = "QA_Buddy"
    root.location = (x, y, 0); root.scale = [s * scale for s in root.scale]
    root.rotation_euler = (root.rotation_euler[0], 0, math.radians(-30))
    png = os.path.join(CHARS, name + ".png")
    for o in new:
        if o.type == 'MESH' and os.path.exists(png):
            m = bpy.data.materials.new("QA_BuddyMat"); m.use_nodes = True
            t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(png, check_existing=True)
            m.node_tree.links.new(t.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
            o.data.materials.clear(); o.data.materials.append(m)
        if o.type == 'ARMATURE' and o.animation_data:
            o.animation_data.action = None
    return root
