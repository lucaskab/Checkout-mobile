
# lot_pipe.py - previews, bake and export for the lot models
import bpy, math, os, sys, time
sys.path.insert(0, r"C:\Checkout-mobile\scripts\blender"); import checkout_project as cp
sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource"); import era_kit as k
from mathutils import Vector
OUT = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets\Resources\CheckoutLots"
QA = r"C:\Checkout-mobile\unity\CheckoutSimulator\Temp\qa"
LOTS = {"LOT Casa": "Lot_Casa", "LOT Galpao": "Lot_Galpao", "LOT Entulho": "Lot_Entulho", "LOT Armazem": "Lot_Armazem"}

def vl(): return bpy.context.view_layer

def show(*names):
    for ch in vl().layer_collection.children:
        ch.exclude = ch.name not in names + ("Studio",)

def hide_all():
    for ch in vl().layer_collection.children:
        ch.exclude = ch.name.endswith(" Export") or ch.name.startswith("LOT") or ch.name.startswith("ERA") or ch.name.startswith("REF")

def bounds(objs):
    lo = Vector((1e9,) * 3); hi = -lo
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != 'MESH': continue
        me = o.evaluated_get(dg).data
        for v in me.vertices:
            w = o.matrix_world @ v.co; lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi

def shot(target, direction, dist, lens=40, name="x", res=(1100, 720)):
    sc = bpy.context.scene
    cp.studio(); sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.exposure = -0.2
    cam = bpy.data.objects["Studio Cam"]; cam.data.type = 'PERSP'; cam.data.lens = lens
    d = Vector(direction).normalized(); t = Vector(target)
    cam.location = t + d * dist; cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    path = os.path.join(QA, name + ".png"); sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path

def preview(cname, name, direction=(1.0, -1.3, .75), ground=True):
    show(cname)
    objs = list(bpy.data.collections[cname].objects)
    lo, hi = bounds(objs); ctr = (lo + hi) / 2; size = (hi - lo).length
    g = None
    if ground:
        g = k.box("LOT_Ground", (80, 80, .02), (0, 0, -.015), k.pavers("ERA_Pavers"), bevel=0)
    p = shot((ctr.x, ctr.y, (hi.z - lo.z) * .38), direction, size * 1.55, lens=38, name=name)
    if g: bpy.data.objects.remove(g)
    return p

def preview_all(name="lots_ruinas", baked=True):
    """All four side by side at the same scale (baked export copies by default)."""
    order = ["LOT Armazem", "LOT Casa", "LOT Galpao", "LOT Entulho"]
    if baked:
        order = [LOTS[n] + " Export" for n in order]
    show(*order)
    offs = {}
    x = 0.0
    for cname in order:
        objs = list(bpy.data.collections[cname].objects)
        lo, hi = bounds(objs)
        dx = x - lo.x
        for o in objs:
            if o.parent is None: o.location.x += dx
        offs[cname] = dx
        x += (hi.x - lo.x) + 2.0
    g = k.box("LOT_Ground", (120, 120, .02), (0, 0, -.015), k.pavers("ERA_Pavers"), bevel=0)
    p = shot((x / 2 - 1, 0, 1.2), (0.3, -1.0, .66), 50, lens=40, name=name, res=(1800, 760))
    bpy.data.objects.remove(g)
    for cname, dx in offs.items():
        for o in bpy.data.collections[cname].objects:
            if o.parent is None: o.location.x -= dx
    return p

def make_export(cname, name):
    """Joined-free copies in '<name> Export' (modifiers applied), one smart-UV layout packed across all copies."""
    d = k.col(name + " Export")
    for o in list(d.objects): bpy.data.objects.remove(o)
    show(cname, name + " Export")
    out = []
    for o in bpy.data.collections[cname].objects:
        if o.type != 'MESH': continue
        n = o.copy(); n.data = o.data.copy(); n.name = "X_" + o.name; d.objects.link(n)
        n.parent = None; n.matrix_world = o.matrix_world.copy(); k.bake(n); out.append(n)
    bpy.ops.object.select_all(action='DESELECT')
    for o in out: o.select_set(True)
    vl().objects.active = out[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.001, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    return out

def bake(name, size=2048, batches=1, part=None):
    """Bake the diffuse colour of all export copies into one atlas. With batches>1 call once per `part`
    (0..batches-1) so each call stays short; the image is cleared only on part 0."""
    sc = bpy.context.scene
    allobjs = [o for o in bpy.data.collections[name + " Export"].objects]
    objs = allobjs if part is None else allobjs[part::batches]
    img_name = name + "_BaseColor"
    first = part in (None, 0)
    if first:
        for im in list(bpy.data.images):
            if im.name.startswith(img_name): bpy.data.images.remove(im)
        img = bpy.data.images.new(img_name, size, size)
    else:
        img = bpy.data.images[img_name]
    mats = {m for o in objs for m in o.data.materials if m}; added = []
    for m in mats:
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; m.node_tree.nodes.active = n; added.append((m, n))
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 1
    b = sc.render.bake
    b.use_pass_direct = False; b.use_pass_indirect = False; b.use_pass_color = True; b.margin = 4; b.use_clear = first
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    vl().objects.active = objs[0]
    bpy.ops.object.bake(type='DIFFUSE')
    for m, n in added: m.node_tree.nodes.remove(n)
    if part is not None and part < batches - 1:
        sc.render.engine = 'BLENDER_EEVEE'
        return None
    objs = allobjs
    os.makedirs(OUT, exist_ok=True)
    img.filepath_raw = os.path.join(OUT, img_name + ".png"); img.file_format = 'PNG'; img.save()
    am = bpy.data.materials.get(name + "_Mat") or bpy.data.materials.new(name + "_Mat")
    am.use_nodes = True; nt = am.node_tree
    for n in list(nt.nodes):
        if n.bl_idname == "ShaderNodeTexImage": nt.nodes.remove(n)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(am)
        for p in o.data.polygons: p.material_index = 0
    sc.render.engine = 'BLENDER_EEVEE'
    return img.filepath_raw

def export(cname, name):
    show(name + " Export")
    objs = [o for o in bpy.data.collections[name + " Export"].objects]
    originals = {o.name: o for o in bpy.data.collections[cname].objects}
    for o in originals.values(): o.name = o.name + "~"
    for o in objs: o.name = o.name[2:]
    lo, hi = bounds(objs)
    try:
        path = cp.export_unity(objs, name, folder=OUT)
    finally:
        for o in objs: o.name = "X_" + o.name
        for o in originals.values(): o.name = o.name[:-1]
    tris = sum(len(o.data.loop_triangles) for o in objs)
    return {"fbx": path, "kb": os.path.getsize(path) // 1024, "lo": [round(x, 2) for x in lo], "hi": [round(x, 2) for x in hi],
            "dims": [round(x, 2) for x in (hi - lo)], "tris": tris, "objs": len(objs)}
