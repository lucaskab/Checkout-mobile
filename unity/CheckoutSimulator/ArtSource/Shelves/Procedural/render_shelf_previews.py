import math
import os

import bpy
from mathutils import Vector


ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, "models")
PREVIEWS = os.path.join(ROOT, "previews")


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def render(name):
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, f"{name}.glb"))

    camera_data = bpy.data.cameras.new("ReviewCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 3.55
    camera = bpy.data.objects.new("ReviewCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (4.3, 5.1, 3.2)
    point_at(camera, (0, 0, 1.15))
    bpy.context.scene.camera = camera

    key_data = bpy.data.lights.new("Key", type="AREA")
    key_data.energy = 850
    key_data.shape = "DISK"
    key_data.size = 4
    key = bpy.data.objects.new("Key", key_data)
    bpy.context.collection.objects.link(key)
    key.location = (-3.5, 4, 5)
    point_at(key, (0, 0, 1.15))

    fill_data = bpy.data.lights.new("Fill", type="AREA")
    fill_data.energy = 450
    fill_data.size = 3
    fill = bpy.data.objects.new("Fill", fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (3, 2, 2.5)
    point_at(fill, (0, 0, 1.15))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.render.filepath = os.path.join(PREVIEWS, f"{name}.png")
    scene.world.color = (0.06, 0.06, 0.06)
    bpy.ops.render.render(write_still=True)


os.makedirs(PREVIEWS, exist_ok=True)
for variant in ("ShelfFull", "ShelfPartial", "ShelfEmpty"):
    render(variant)
