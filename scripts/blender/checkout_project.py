"""Checkout Simulator <-> Blender bridge (used through the Blender MCP or Blender's Text Editor / Python console).

    import sys; sys.path.insert(0, r"C:\\Checkout-mobile\\scripts\\blender"); import checkout_project as cp
    cp.reference("BeverageShelf")          # import a project model (textured) to match its style
    cp.studio(); cp.preview(objs, "name")  # soft studio render to unity/CheckoutSimulator/Temp/qa/<name>.png
    cp.export_unity(objs, "sector-bebidas")  # FBX to Assets/Art/Interior/Models with the kit axis convention

Style of the project (see the models in Assets/Art/Models/MapModels): chunky, soft rounded edges (bevel + subdivision,
never raw boxes), teal / cream / orange / wood palette (ArtSource/palette.json), painted textures and printed labels
on products, readable silhouettes from the top-down game camera. Front of a prop faces Blender -Y while modelling;
export_unity() turns it to face the customers (Unity -Z).
"""
import json
import math
import os

import bpy
from mathutils import Vector

ROOT = r"C:\Checkout-mobile"
UNITY = os.path.join(ROOT, "unity", "CheckoutSimulator")
ASSETS = os.path.join(UNITY, "Assets")
ART_SOURCE = os.path.join(UNITY, "ArtSource")
MAP_MODELS = os.path.join(ASSETS, "Art", "Models", "MapModels")
INTERIOR_MODELS = os.path.join(ASSETS, "Art", "Interior", "Models")
INTERIOR_TEXTURES = os.path.join(ASSETS, "Art", "Interior", "Textures")
PREVIEWS = os.path.join(UNITY, "Temp", "qa")
WORKSPACE = os.path.join(ART_SOURCE, "Checkout_Workspace.blend")


def palette():
    with open(os.path.join(ART_SOURCE, "palette.json"), encoding="utf-8") as f:
        return {k: tuple(v) for k, v in json.load(f).items()}


def collection(name, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if col.name not in parent.children:
        parent.children.link(col)
    return col


def _texture_material(name, folder):
    mat = bpy.data.materials.get("REF_" + name)
    if mat:
        return mat
    files = [f for f in os.listdir(folder) if ("BaseColor" in f or "Albedo" in f) and not f.endswith(".meta")]
    mat = bpy.data.materials.new("REF_" + name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = .7
    if files:
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(os.path.join(folder, files[0]), check_existing=True)
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def reference(name, location=(0, 0, 0), col="REF Project models"):
    """Imports Assets/Art/Models/MapModels/<name>/<name>.fbx with its painted texture."""
    folder = os.path.join(MAP_MODELS, name)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(folder, name + ".fbx"))
    objs = [o for o in bpy.data.objects if o not in before]
    target = collection(col)
    mat = _texture_material(name, folder)
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        target.objects.link(o)
        if o.type == "MESH":
            o.data.materials.clear()
            o.data.materials.append(mat)
        if o.parent is None:
            o.location = Vector(location)
    return objs


def studio(size=900, background=(.86, .86, .88)):
    """Soft daylight like the game (EEVEE, warm sun, light grey backdrop)."""
    sc = bpy.context.scene
    world = bpy.data.worlds.get("Checkout Studio") or bpy.data.worlds.new("Checkout Studio")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*background, 1)
    bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.get("Studio Sun")
    if not sun:
        sun = bpy.data.objects.new("Studio Sun", bpy.data.lights.new("Studio Sun", "SUN"))
        collection("Studio").objects.link(sun)
    sun.data.energy = 3.2
    sun.data.color = (1, .96, .9)
    sun.data.angle = math.radians(8)
    sun.rotation_euler = (math.radians(42), math.radians(12), math.radians(28))
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    return sc


def preview(objs, name, direction=(1, -1.25, .85), persp=False, lens=50, size=None, pad=1.0):
    """Frames `objs` (or every mesh) and renders to Temp/qa/<name>.png; returns the path."""
    sc = bpy.context.scene
    if size:
        sc.render.resolution_x = sc.render.resolution_y = size
    objs = [o for o in (objs or sc.objects) if o.type == "MESH" and o.visible_get()]
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    center = (lo + hi) / 2
    radius = (hi - lo).length / 2 * pad
    cam = bpy.data.objects.get("Studio Cam")
    if not cam:
        cam = bpy.data.objects.new("Studio Cam", bpy.data.cameras.new("Studio Cam"))
        collection("Studio").objects.link(cam)
    d = Vector(direction).normalized()
    if persp:
        cam.data.type = "PERSP"; cam.data.lens = lens
        cam.location = center + d * radius * (lens / 16)
    else:
        cam.data.type = "ORTHO"; cam.data.ortho_scale = radius * 2.1
        cam.location = center + d * radius * 6
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = radius * 40
    sc.camera = cam
    os.makedirs(PREVIEWS, exist_ok=True)
    path = os.path.join(PREVIEWS, name + ".png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def export_unity(objs, name, folder=INTERIOR_MODELS, turn=True):
    """Exports `objs` as <folder>/<name>.fbx for Unity (kit convention: FBX axis -Z forward, Y up, no baked
    axis conversion). With `turn`, a prop modelled facing Blender -Y is turned to face the customers."""
    os.makedirs(folder, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if turn:
        for o in objs:
            if o.parent is None:
                o.rotation_euler.z += math.pi
                o.location.x, o.location.y = -o.location.x, -o.location.y
    try:
        path = os.path.join(folder, name + ".fbx")
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH", "EMPTY"},
                                 axis_forward="-Z", axis_up="Y", bake_anim=False, path_mode="STRIP",
                                 use_mesh_modifiers=True, mesh_smooth_type="FACE", apply_scale_options="FBX_SCALE_ALL",
                                 use_tspace=False)
    finally:
        if turn:
            for o in objs:
                if o.parent is None:
                    o.rotation_euler.z -= math.pi
                    o.location.x, o.location.y = -o.location.x, -o.location.y
    return path


def open_workspace():
    """Opens (or creates) ArtSource/Checkout_Workspace.blend, the Blender home of the project."""
    if os.path.exists(WORKSPACE):
        bpy.ops.wm.open_mainfile(filepath=WORKSPACE)
    else:
        bpy.ops.wm.save_as_mainfile(filepath=WORKSPACE)
    return WORKSPACE
