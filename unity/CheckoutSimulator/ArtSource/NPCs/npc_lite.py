"""Light (mobile) versions of the new NPC sculpts (Tripo GLBs, 185k-2M triangles each), made in Blender.

Run (background, one sculpt per call so memory stays low):
    blender -b --factory-startup --python ArtSource/NPCs/npc_lite.py -- <name> [budget]
Input:  ArtSource/NPCs/incoming/<name>.glb  (the file as Lucas sent it, never modified)
Output: ArtSource/NPCs/lite/<name>.blend    (light mesh, feet on z=0, 2.4 units tall, faces -Y, texture packed)
        Temp/qa/npcs/<name>_compare.png     (original left, light version right, front and 3/4 view)
        ArtSource/NPCs/lite/<name>.json     (triangle counts, landmarks for the rig)

Same polish as scripts/blender/mobile_lod.py (Lucas, 11/10): UV island borders are protected during the collapse
and the original's normals are copied onto the light mesh, so the texture and the shading stay as in the original.
"""
import bpy, bmesh, sys, os, json, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
INCOMING = os.path.join(HERE, "incoming")
LITE = os.path.join(HERE, "lite")
PREVIEWS = os.path.join(PROJECT, "Temp", "qa", "npcs")
HEIGHT = 2.4          # the customer rigs' height (ArtSource/Customers/build_customers.py)
TEX = 2048


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def load(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(INCOMING, name + ".glb"))
    meshes = [o for o in set(bpy.data.objects) - before if o.type == 'MESH']
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.parent = None
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for e in [x for x in bpy.data.objects if x.type == 'EMPTY']:
        bpy.data.objects.remove(e, do_unlink=True)
    # Feet on the floor, centred, HEIGHT tall.
    lo = Vector([min(v.co[i] for v in o.data.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in o.data.vertices) for i in range(3)])
    s = HEIGHT / (hi.z - lo.z)
    c = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for v in o.data.vertices:
        v.co = (v.co - c) * s
    o.data.update()
    return o


def decimate(o, budget):
    before = tris(o)
    source = o.copy(); source.data = o.data.copy(); bpy.context.collection.objects.link(source)
    # Tripo exports split vertices along UV seams: weld first so the collapse sees one surface.
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=HEIGHT * 1e-5)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    for x in bpy.data.objects:
        if x is not None and x.name in bpy.context.view_layer.objects:
            x.select_set(False)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    borders = {v for e in o.data.edges if e.use_seam for v in e.vertices}
    keep = o.vertex_groups.new(name="keep")
    if borders:
        keep.add(list(borders), 1.0, 'REPLACE')
    m = o.modifiers.new("lite", 'DECIMATE'); m.decimate_type = 'COLLAPSE'
    m.ratio = min(1, budget / tris(o)); m.use_collapse_triangulate = True
    m.vertex_group = keep.name; m.vertex_group_factor = 100.0
    bpy.ops.object.modifier_apply(modifier=m.name)
    if tris(o) > budget * 1.25:      # too many islands to keep every border: finish the way down unprotected
        m = o.modifiers.new("lite2", 'DECIMATE'); m.decimate_type = 'COLLAPSE'
        m.ratio = budget / tris(o); m.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=m.name)
    o.vertex_groups.remove(o.vertex_groups["keep"])
    for e in o.data.edges:
        e.use_seam = False
    bpy.ops.object.shade_smooth()
    dt = o.modifiers.new("normals", 'DATA_TRANSFER'); dt.object = source
    dt.use_loop_data = True; dt.data_types_loops = {'CUSTOM_NORMAL'}; dt.loop_mapping = 'POLYINTERP_NEAREST'
    bpy.ops.object.modifier_apply(modifier=dt.name)
    return source, before, tris(o)


def base_color(o):
    for mat in o.data.materials:
        if mat and mat.use_nodes:
            for n in mat.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and any(l.to_socket.name == "Base Color" for l in n.outputs["Color"].links):
                    return mat, n.image
    # Some exports route the colour through a mix node: take the largest colour (non-data) texture.
    best = None
    for mat in o.data.materials:
        if mat and mat.use_nodes:
            for n in mat.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and n.image.colorspace_settings.name != 'Non-Color':
                    if best is None or n.image.size[0] > best[1].size[0]:
                        best = (mat, n.image)
    return best or (None, None)


def landmarks(o):
    """Heights and widths the rig needs, measured on the sculpt (normalized space, front is -Y)."""
    vs = [v.co for v in o.data.vertices]
    def band(z0, z1):
        xs = [v.x for v in vs if z0 <= v.z < z1]
        return (min(xs), max(xs)) if xs else (0, 0)
    rows = []
    for i in range(48):
        z0 = HEIGHT * i / 48; z1 = HEIGHT * (i + 1) / 48
        lo, hi = band(z0, z1)
        rows.append({"z": round((z0 + z1) / 2, 3), "xmin": round(lo, 3), "xmax": round(hi, 3), "w": round(hi - lo, 3)})
    return rows


def render(name, source, light, image):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 1600, 760
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("W"); world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.80, 0.85, 0.89, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    sc.world = world
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN')); sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30)); sc.collection.objects.link(sun)
    # Four figures: original front, light front, original 3/4, light 3/4.
    figs = [(source, -3.3, 0), (light, -1.1, 0), (source, 1.1, 40), (light, 3.3, 40)]
    shown = []
    for i, (obj, x, yaw) in enumerate(figs):
        f = obj if i < 2 else obj.copy()
        if i >= 2:
            sc.collection.objects.link(f)
        f.rotation_mode = 'XYZ'; f.location = (x, 0, 0); f.rotation_euler = (0, 0, math.radians(yaw)); shown.append(f)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 8.9
    cam.location = (0, -12, 1.25); cam.rotation_euler = (math.radians(90), 0, 0); sc.camera = cam
    os.makedirs(PREVIEWS, exist_ok=True)
    sc.render.filepath = os.path.join(PREVIEWS, name + "_compare.png")
    bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    name = argv[0]; budget = int(argv[1]) if len(argv) > 1 else 24000
    bpy.ops.wm.read_factory_settings(use_empty=True)
    o = load(name)
    mat, image = base_color(o)
    source, before, after = decimate(o, budget)
    o.name = o.data.name = name
    if image is not None and max(image.size) > TEX:
        image.scale(TEX, TEX)
    if image is not None:
        image.pack()
    # Only the base colour is used by the game's character shader: drop the normal / roughness maps.
    if mat is not None:
        for n in list(mat.node_tree.nodes):
            if n.type == 'TEX_IMAGE' and n.image is not image:
                mat.node_tree.nodes.remove(n)
    render(name, source, o, image)
    info = {"name": name, "source_tris": before, "tris": after, "verts": len(o.data.vertices),
            "texture": list(image.size) if image else None, "rows": landmarks(o)}
    o.rotation_mode = 'XYZ'; o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0)   # back from the preview spot
    for x in list(bpy.data.objects):
        if x is not o:
            bpy.data.objects.remove(x, do_unlink=True)
    for img in list(bpy.data.images):
        if img is not image:
            bpy.data.images.remove(img)
    os.makedirs(LITE, exist_ok=True)
    with open(os.path.join(LITE, name + ".json"), "w") as f:
        json.dump(info, f, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(LITE, name + ".blend"), compress=True)
    print("NPC_LITE_OK", json.dumps({k: info[k] for k in ("name", "source_tris", "tris", "verts", "texture")}))


main()
