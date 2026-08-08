"""Import and render the supplied courtyard FBX for art-direction inspection."""

import os

import bpy
from mathutils import Vector


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_PATH = os.path.join(SCRIPT_DIR, "diamond_courtyard_market_source.fbx")
PREVIEW_PATH = os.path.join(SCRIPT_DIR, "diamond_courtyard_market_source_preview.png")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=SOURCE_PATH)

meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not meshes:
    raise RuntimeError("The supplied FBX did not contain visual meshes")

min_bound = Vector((float("inf"), float("inf"), float("inf")))
max_bound = Vector((float("-inf"), float("-inf"), float("-inf")))
for obj in meshes:
    for corner in obj.bound_box:
        point = obj.matrix_world @ Vector(corner)
        min_bound.x = min(min_bound.x, point.x)
        min_bound.y = min(min_bound.y, point.y)
        min_bound.z = min(min_bound.z, point.z)
        max_bound.x = max(max_bound.x, point.x)
        max_bound.y = max(max_bound.y, point.y)
        max_bound.z = max(max_bound.z, point.z)

center = (min_bound + max_bound) * 0.5
size = max(max_bound.x - min_bound.x, max_bound.y - min_bound.y, max_bound.z - min_bound.z)

bpy.ops.object.camera_add(location=center + Vector((size * 1.15, -size * 1.25, size * 1.05)))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = size * 1.55
camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = camera

bpy.ops.object.light_add(type="AREA", location=center + Vector((-size, -size, size * 1.7)))
key = bpy.context.object
key.data.energy = 1700.0
key.data.shape = "DISK"
key.data.size = size * 1.7
key.rotation_euler = (center - key.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="SUN", location=center + Vector((0.0, 0.0, size)))
bpy.context.object.data.energy = 1.2
bpy.context.object.rotation_euler = (0.45, -0.35, -0.45)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.color = (0.06, 0.08, 0.09)
scene.render.filepath = PREVIEW_PATH
bpy.ops.render.render(write_still=True)

print("SOURCE_FBX_INSPECTION_OK")
print("Mesh count:", len(meshes))
print("Bounds min:", tuple(round(value, 3) for value in min_bound))
print("Bounds max:", tuple(round(value, 3) for value in max_bound))
print("Materials:", ", ".join(sorted(material.name for material in bpy.data.materials)))
for obj in meshes:
    print("Object:", obj.name)
    print("Material slots:", ", ".join(slot.material.name if slot.material else "<empty>" for slot in obj.material_slots))
    for index in range(len(obj.material_slots)):
        print("Faces in slot {}:".format(index), sum(1 for polygon in obj.data.polygons if polygon.material_index == index))
bpy.ops.wm.quit_blender()
