"""Lighter (mobile) versions of the game's heavy models, made in Blender.

The Tripo models came at 150-185k triangles each. Each heavy mesh is decimated (collapse, keeping the model's own
UVs and texture) to a per-model budget; meshes already under budget are left untouched. Object and mesh names are
kept so Unity maps the new file onto the same sub-assets (the scene keeps its references).

Usage inside Blender (Blender MCP):
    exec(open(r"C:/Checkout-mobile/scripts/blender/mobile_lod.py").read())
    run(["Art/Models/MapModels/Gym/Gym.fbx", ...])          # -> staging + previews, originals untouched
    install(["Art/Models/MapModels/Gym/Gym.fbx", ...])      # backs up the originals, copies the light files in
    restore(["Art/Models/MapModels/Gym/Gym.fbx", ...])      # puts the originals back
"""
import bpy, os, re, shutil, json, math, mathutils

PROJECT = r"C:/Checkout-mobile/unity/CheckoutSimulator"
ASSETS = PROJECT + "/Assets"
STAGING = PROJECT + "/ArtSource/mobile_lod"
ORIGINALS = PROJECT + "/_Unused/originals"
PREVIEWS = PROJECT + "/Temp/qa/mobile_lod"

DEFAULT_BUDGET = 30000
# Small props seen many times over (crates, boxes, planters, traffic lights): a lower budget.
BUDGETS = {
    "VegetableCrate": 12000, "CardboardBox": 12000, "FlowerPlanter": 12000, "TrafficLight": 14000,
    # One big single mesh (the whole café): a higher budget.
    "plaza-cafe": 60000,
}


def _budget(rel):
    stem = os.path.splitext(os.path.basename(rel))[0]
    return BUDGETS.get(stem, DEFAULT_BUDGET)


def _tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def _clean_scene(name):
    sc = bpy.data.scenes.get(name)
    if sc:
        for o in list(sc.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.scenes.remove(sc)
    sc = bpy.data.scenes.new(name)
    bpy.context.window.scene = sc
    return sc


def _purge():
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
        for d in list(blk):
            if d.users == 0:
                blk.remove(d)


def _true_names(objs, outside=None):
    """Blender adds .001-style suffixes when a name is already taken (by another scene's object). The exported file
    must carry the original node and mesh names, or Unity would see new sub-assets and the scene would lose them."""
    for o in objs:
        for block, item in ((bpy.data.objects, o), (bpy.data.meshes, o.data if o.type == 'MESH' else None)):
            if item is None:
                continue
            base = re.sub(r"\.\d{3}$", "", item.name)
            if base == item.name:
                continue
            other = block.get(base)
            if other is None or other == item:
                continue                      # no clash: the suffix is part of the model's own name
            if outside is not None and base not in outside:
                continue                      # the clash is inside the model itself (Head_Mesh / Head_Mesh.010): keep
            other.name = base + "_held"
            item.name = base


def _decimate(sc, budget):
    report = []
    for o in list(sc.objects):
        if o.type != 'MESH':
            continue
        before = _tris(o)
        if before <= budget * 1.3:
            report.append((o.name, before, before))
            continue
        # Polish (Lucas, 11/10: "riscos" on walls and cars): the first pass let the decimator cut across UV island
        # borders (texture streaks) and re-shaded the faces (lighting lines). Now
        #  - the UV island borders are protected (a weighted vertex group the collapse avoids), and
        #  - the original's normals are copied onto the light mesh, so it lights exactly like the full model.
        source = o.copy()
        source.data = o.data.copy()
        sc.collection.objects.link(source)
        for other in sc.objects:
            other.select_set(False)
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        borders = {v for e in o.data.edges if e.use_seam for v in e.vertices}
        keep = o.vertex_groups.new(name="MobileLOD_keep")
        if borders:
            keep.add(list(borders), 1.0, 'REPLACE')
        m = o.modifiers.new("MobileLOD", 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = budget / before
        m.use_collapse_triangulate = True
        m.vertex_group = keep.name
        m.vertex_group_factor = 100.0
        bpy.ops.object.modifier_apply(modifier=m.name)
        if _tris(o) > budget * 1.5:
            # Models cut into very many UV islands (our own Blender builds) can't come down with every border kept:
            # start again from the full mesh without the protection (their colours are flat, borders matter less).
            o.data = source.data.copy()
            m = o.modifiers.new("MobileLOD", 'DECIMATE')
            m.decimate_type = 'COLLAPSE'
            m.ratio = budget / before
            m.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.ops.object.shade_smooth()
        dt = o.modifiers.new("MobileLOD_normals", 'DATA_TRANSFER')
        dt.object = source
        dt.use_loop_data = True
        dt.data_types_loops = {'CUSTOM_NORMAL'}
        dt.loop_mapping = 'POLYINTERP_NEAREST'
        bpy.ops.object.modifier_apply(modifier=dt.name)
        left = o.vertex_groups.get("MobileLOD_keep")
        if left is not None:
            o.vertex_groups.remove(left)
        for e in o.data.edges:
            e.use_seam = False
        bpy.data.objects.remove(source, do_unlink=True)
        report.append((o.name, before, _tris(o)))
    return report


# Files made in Blender by our own builders were exported with FBX_SCALE_ALL (the Tripo ones with none): keep each
# file's own convention or Unity sees it 100x smaller.
SCALE_ALL = {"MarketWorld", "plaza-cafe", "sector-padaria", "sector-peixaria", "WarehouseLarge"}


def _export(sc, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for o in sc.objects:
        o.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=False, use_active_collection=False,
        object_types={'MESH', 'EMPTY'}, apply_unit_scale=True, global_scale=1.0,
        apply_scale_options='FBX_SCALE_ALL' if os.path.splitext(os.path.basename(path))[0] in SCALE_ALL else 'FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y', bake_space_transform=False,
        use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=False, add_leaf_bones=False,
        path_mode='AUTO', embed_textures=False, bake_anim=False,
    )


def _render_pair(rel, before_path, after_path, out_png):
    """Original left, light version right, same camera: for the approval sheet."""
    sc = _clean_scene("MOBILE_LOD_PREVIEW")
    objs = {}
    for side, path in (("before", before_path), ("after", after_path)):
        before = set(sc.objects)
        bpy.ops.import_scene.fbx(filepath=path)
        objs[side] = [o for o in sc.objects if o not in before]
    # The game's own texture (Unity assigns it; the FBX copies outside Assets don't find theirs).
    stem = os.path.splitext(os.path.basename(rel))[0]
    tex_path = os.path.join(ASSETS, os.path.dirname(rel), stem + "_BaseColor.png")
    if os.path.exists(tex_path):
        mat = bpy.data.materials.get("MOBILE_LOD_TEX_" + stem) or bpy.data.materials.new("MOBILE_LOD_TEX_" + stem)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        bsdf.inputs['Roughness'].default_value = 0.85
        tex = nt.nodes.get("TEX") or nt.nodes.new('ShaderNodeTexImage')
        tex.name = "TEX"
        tex.image = bpy.data.images.load(tex_path, check_existing=True)
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        for side in objs.values():
            for o in side:
                if o.type == 'MESH':
                    o.data.materials.clear()
                    o.data.materials.append(mat)
    def bounds(objs):
        pts = [o.matrix_world @ mathutils.Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
        lo = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        return lo, hi
    lo, hi = bounds(objs["before"])
    size = max((hi - lo).x, (hi - lo).y, (hi - lo).z)
    gap = size * 1.25
    for side, dx in (("before", -gap / 2), ("after", gap / 2)):
        l, h = bounds(objs[side])
        shift = mathutils.Vector((dx - (l.x + h.x) / 2, -(l.y + h.y) / 2, -l.z))
        for o in objs[side]:
            if o.parent is None:
                o.location += shift
    world = bpy.data.worlds.get("MOBILE_LOD") or bpy.data.worlds.new("MOBILE_LOD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.84, 0.88, 1)
    sc.world = world
    sun = bpy.data.objects.new("SUN", bpy.data.lights.new("SUN", 'SUN'))
    sc.collection.objects.link(sun)
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = gap * 2.2
    target = mathutils.Vector((0, 0, size * 0.4))
    cam.location = target + mathutils.Vector((1, -1.4, 1.2)) * size * 3
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = size * 40
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 1000, 560
    sc.render.image_settings.file_format = 'PNG'
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True)
    for o in list(sc.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def run(files, previews=True):
    done = {}
    for rel in files:
        # Always from the full original (kept in _Unused/originals once a light version is installed).
        src = os.path.join(ORIGINALS, rel) if os.path.exists(os.path.join(ORIGINALS, rel)) else os.path.join(ASSETS, rel)
        dst = os.path.join(STAGING, rel)
        sc = _clean_scene("MOBILE_LOD")
        outside = set(bpy.data.objects.keys()) | set(bpy.data.meshes.keys())
        bpy.ops.import_scene.fbx(filepath=src)
        _true_names(list(sc.objects), outside)
        rep = _decimate(sc, _budget(rel))
        _export(sc, dst)
        entry = {"meshes": rep, "before": sum(r[1] for r in rep), "after": sum(r[2] for r in rep)}
        if previews:
            png = os.path.join(PREVIEWS, os.path.splitext(os.path.basename(rel))[0] + ".png")
            _render_pair(rel, src, dst, png)
            entry["preview"] = png
        done[rel] = entry
        _purge()
    with open(os.path.join(STAGING, "report.json"), "a", encoding="utf-8") as f:
        f.write(json.dumps(done) + "\n")
    return done


def install(files):
    for rel in files:
        src, light, keep = os.path.join(ASSETS, rel), os.path.join(STAGING, rel), os.path.join(ORIGINALS, rel)
        if not os.path.exists(light):
            raise FileNotFoundError(light)
        if not os.path.exists(keep):
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.copy2(src, keep)
        shutil.copyfile(light, src)
    return {"installed": len(files)}


def restore(files):
    n = 0
    for rel in files:
        keep = os.path.join(ORIGINALS, rel)
        if os.path.exists(keep):
            shutil.copyfile(keep, os.path.join(ASSETS, rel))
            n += 1
    return {"restored": n}
