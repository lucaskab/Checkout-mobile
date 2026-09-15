import bpy
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/Assets/Art/Models/MarketWorld.fbx")

for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    xs = [corner.x for corner in corners]
    ys = [corner.y for corner in corners]
    zs = [corner.z for corner in corners]
    print(f"MESH_BOUNDS {obj.name} width={max(xs)-min(xs):.3f} height={max(zs)-min(zs):.3f} depth={max(ys)-min(ys):.3f}")
