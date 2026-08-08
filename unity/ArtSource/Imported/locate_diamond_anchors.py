"""Find material clusters in the courtyard mesh to place Unity gameplay props."""

import collections
import os

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FBX_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "../../Assets/Resources/Models/DiamondMarket/diamond_market.fbx"))

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX_PATH)
mesh_object = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
slots = {index: slot.material.name if slot.material else "" for index, slot in enumerate(mesh_object.material_slots)}
glass_indices = {index for index, name in slots.items() if "Glass" in name}
clusters = collections.Counter()
cluster_points = collections.defaultdict(list)

for polygon in mesh_object.data.polygons:
    if polygon.material_index not in glass_indices:
        continue
    center = mesh_object.matrix_world @ (sum((mesh_object.data.vertices[index].co for index in polygon.vertices), Vector()) / len(polygon.vertices))
    key = (round(center.x * 2.0) / 2.0, round(center.y * 2.0) / 2.0)
    clusters[key] += 1
    cluster_points[key].append(center)

bpy.ops.object.camera_add(location=(24.0, -26.0, 28.0))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = 35.0
camera.rotation_euler = (Vector((0.0, 0.0, 0.8)) - camera.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = camera

print("DIAMOND_GLASS_CLUSTERS")
for point, count in clusters.most_common(12):
    print(point, count)
print("DIAMOND_GLASS_SCREEN_BOTTOM")
ranked = []
for key, points in cluster_points.items():
    average = sum(points, Vector()) / len(points)
    screen = world_to_camera_view(bpy.context.scene, camera, average)
    ranked.append((abs(screen.x - 0.5) + screen.y * 0.7, key, tuple(round(value, 2) for value in average), tuple(round(value, 2) for value in screen)))
for _, key, average, screen in sorted(ranked)[:12]:
    print(key, average, screen)
print("DIAMOND_GLASS_SCREEN_CENTER")
screen_center = []
for key, points in cluster_points.items():
    average = sum(points, Vector()) / len(points)
    screen_center.append((abs(average.x * 26.0 + average.y * 24.0), tuple(round(value, 2) for value in average), len(points)))
for _, average, count in sorted(screen_center)[:12]:
    print(average, count)
bpy.ops.wm.quit_blender()
