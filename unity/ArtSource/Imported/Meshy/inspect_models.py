"""Report the bounds and geometry budget of the four supplied Meshy assets."""

import os

import bpy
from mathutils import Vector


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCES = {
    "checkout": os.path.join(SCRIPT_DIR, "checkout_counter", "Meshy_AI_Checkout_Counter_0807105305_image-to-3d-texture.fbx"),
    "entrance": os.path.join(SCRIPT_DIR, "entrance_door", "Meshy_AI_Store_Entrance_Door_0807105256_image-to-3d-texture.fbx"),
    "cashier": os.path.join(SCRIPT_DIR, "cashier", "Meshy_AI_Cashier_Character_0807105249_image-to-3d-texture.fbx"),
    "bakery_display": os.path.join(SCRIPT_DIR, "bakery_display", "Meshy_AI_Bakery_Display_Case_0807105230_image-to-3d-texture.fbx"),
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


for label, path in SOURCES.items():
    clear_scene()
    bpy.ops.import_scene.fbx(filepath=path)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    triangles = 0
    for obj in meshes:
        triangles += sum(len(polygon.vertices) - 2 for polygon in obj.data.polygons)
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            minimum.x = min(minimum.x, point.x)
            minimum.y = min(minimum.y, point.y)
            minimum.z = min(minimum.z, point.z)
            maximum.x = max(maximum.x, point.x)
            maximum.y = max(maximum.y, point.y)
            maximum.z = max(maximum.z, point.z)
    print("MODEL", label)
    print("Meshes:", len(meshes), "Triangles:", triangles)
    print("Bounds:", tuple(round(value, 3) for value in minimum), tuple(round(value, 3) for value in maximum))
    print("Materials:", ", ".join(sorted(material.name for material in bpy.data.materials)))

bpy.ops.wm.quit_blender()
