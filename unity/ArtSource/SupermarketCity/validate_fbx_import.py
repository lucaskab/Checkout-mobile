"""Re-import the generated FBX and verify its game-facing contents."""

import os

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FBX_PATH = os.path.abspath(
    os.path.join(SCRIPT_DIR, "../../Assets/Resources/Models/SupermarketCity/supermarket_city.fbx")
)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX_PATH)

names = {obj.name for obj in bpy.context.scene.objects}
required = {
    "SM_Building_Walls_Back",
    "SM_Building_Floor",
    "SM_Entrance_Door_Left",
    "SM_Entrance_Door_Right",
    "Roof",
    "ENV_Ground",
    "ENV_Sidewalk_Front",
    "ENV_Road",
    "UCX_SM_Wall_Back",
    "SM_Supermarket_Proxy_Near",
    "SM_Supermarket_Proxy_Far",
}
missing = sorted(required.difference(names))
if missing:
    raise RuntimeError("FBX is missing required objects: " + ", ".join(missing))

non_meshes = [obj.name for obj in bpy.context.scene.objects if obj.type != "MESH"]
if non_meshes:
    raise RuntimeError("FBX contains non-mesh preview objects: " + ", ".join(non_meshes))

mesh_count = sum(1 for obj in bpy.context.scene.objects if obj.type == "MESH")
collision_count = sum(1 for obj in bpy.context.scene.objects if obj.name.startswith("UCX_"))
required_materials = {
    "MAT_Turquoise",
    "MAT_Asphalt",
    "MAT_Grass",
    "MAT_Leaves",
    "MAT_Concrete",
}
missing_materials = sorted(required_materials.difference(bpy.data.materials.keys()))
if missing_materials:
    raise RuntimeError("FBX is missing textured materials: " + ", ".join(missing_materials))

required_textures = {
    "tex_asphalt_stylized_v1.png",
    "tex_foliage_stylized_v1.png",
    "tex_grass_stylized_v1.png",
    "tex_stucco_detail_v1.png",
    "tex_tile_cream_v1.png",
    "tex_wall_coral_v1.png",
    "tex_wall_turquoise_v1.png",
    "tex_wood_stylized_v1.png",
}
imported_textures = {os.path.basename(image.filepath) for image in bpy.data.images}
missing_textures = sorted(required_textures.difference(imported_textures))
if missing_textures:
    raise RuntimeError("FBX is missing texture references: " + ", ".join(missing_textures))

print("FBX_IMPORT_VALIDATION_OK")
print("Imported mesh count:", mesh_count)
print("Imported collision count:", collision_count)
print("Imported texture references:", len(imported_textures))
bpy.ops.wm.quit_blender()
