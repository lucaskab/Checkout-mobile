"""Render the Unity placements in Blender using the same FBX transforms."""

import os

import bpy
from mathutils import Vector


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UNITY_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../Assets/Resources/Models"))
PREVIEW_PATH = os.path.join(SCRIPT_DIR, "unity_layout_preview.png")
MODELS = (
    ("DiamondMarket/diamond_market.fbx", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
    ("Meshy/entrance/entrance.fbx", (4.0, -6.7, 1.25), (0.0, 0.0, 0.0)),
    ("Meshy/checkout/checkout.fbx", (5.85, 2.8, 1.1), (0.0, 0.0, 0.0)),
    ("Meshy/cashier/cashier.fbx", (5.35, 1.55, 0.9), (0.0, 0.0, 3.14159)),
    ("Meshy/bakery_display/bakery_display.fbx", (1.8, -4.05, 0.9), (0.0, 0.0, 0.0)),
)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

for relative_path, location, rotation in MODELS:
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(UNITY_ROOT, relative_path))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before and obj.type == "MESH"]
    for obj in imported:
        obj.location = location
        obj.rotation_euler = rotation

bpy.ops.object.camera_add(location=(24.0, -26.0, 28.0))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = 35.0
look_at(camera, (0.0, 0.0, 0.8))
bpy.context.scene.camera = camera

bpy.ops.object.light_add(type="SUN", location=(6.0, -8.0, 22.0))
sun = bpy.context.object
sun.data.energy = 2.0
sun.rotation_euler = (0.48, -0.32, 0.48)
bpy.ops.object.light_add(type="AREA", location=(-8.0, -10.0, 18.0))
fill = bpy.context.object
fill.data.energy = 1300.0
fill.data.size = 12.0
look_at(fill, (0.0, 0.0, 1.0))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1536
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 65
scene.render.image_settings.file_format = "PNG"
scene.world.color = (0.15, 0.19, 0.21)
scene.render.filepath = PREVIEW_PATH
bpy.ops.render.render(write_still=True)
print("UNITY_LAYOUT_PREVIEW_OK", PREVIEW_PATH)
bpy.ops.wm.quit_blender()
