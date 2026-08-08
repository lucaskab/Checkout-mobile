"""Lightweight import check for the customer model sent to Unity."""

import os

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FBX_PATH = os.path.abspath(
    os.path.join(SCRIPT_DIR, "../../Assets/Resources/Models/Customers/customer_3d.fbx")
)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX_PATH)

required = {"Customer3D", "Arm_L", "Arm_R", "Leg_L", "Leg_R", "Basket", "Torso", "Face"}
available = set(bpy.data.objects.keys())
missing = sorted(required.difference(available))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if missing:
    raise RuntimeError("Customer FBX is missing: " + ", ".join(missing))
if len(meshes) < 12:
    raise RuntimeError("Customer FBX has too few visual meshes")

print("CUSTOMER_FBX_VALIDATION_OK")
print("Imported mesh count:", len(meshes))
bpy.ops.wm.quit_blender()
