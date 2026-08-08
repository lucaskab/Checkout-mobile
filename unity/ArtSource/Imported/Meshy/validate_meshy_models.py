"""Verify optimized geometry and PBR texture references for game imports."""

import os

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../Assets/Resources/Models/Meshy"))
EXPECTED = {
    "checkout": 50000,
    "entrance": 35000,
    "cashier": 50000,
    "bakery_display": 65000,
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


for name, maximum_faces in EXPECTED.items():
    clear_scene()
    path = os.path.join(ASSET_ROOT, name, name + ".fbx")
    bpy.ops.import_scene.fbx(filepath=path)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError("{} has {} meshes instead of one".format(name, len(meshes)))
    faces = len(meshes[0].data.polygons)
    if faces > maximum_faces:
        raise RuntimeError("{} exceeds its mobile geometry budget".format(name))
    images = [image for image in bpy.data.images if image.filepath]
    if len(images) < 4:
        raise RuntimeError("{} is missing PBR texture references".format(name))
    print("MESHY_MODEL_VALIDATION_OK", name, "faces", faces, "textures", len(images))

bpy.ops.wm.quit_blender()
