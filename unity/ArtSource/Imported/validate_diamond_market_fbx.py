"""Verify the optimized textured diamond market export used by Unity."""

import os

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FBX_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "../../Assets/Resources/Models/DiamondMarket/diamond_market.fbx"))

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX_PATH)

meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if len(meshes) != 1:
    raise RuntimeError("Expected one optimized market mesh, found {}".format(len(meshes)))
if len(meshes[0].data.polygons) > 110000:
    raise RuntimeError("Diamond market is over the mobile geometry budget")

required_materials = {
    "MAT_DiamondMarket_Floor",
    "MAT_DiamondMarket_Turquoise",
    "MAT_DiamondMarket_Coral",
    "MAT_DiamondMarket_Cream",
    "MAT_DiamondMarket_Glass",
}
missing = sorted(required_materials.difference(bpy.data.materials.keys()))
if missing:
    raise RuntimeError("Diamond market is missing materials: " + ", ".join(missing))

required_textures = {
    "tex_tile_cream_v1.png",
    "tex_wall_turquoise_v1.png",
    "tex_wall_coral_v1.png",
    "tex_stucco_detail_v1.png",
    "tex_foliage_stylized_v1.png",
}
imported = {os.path.basename(image.filepath) for image in bpy.data.images}
missing_textures = sorted(required_textures.difference(imported))
if missing_textures:
    raise RuntimeError("Diamond market is missing textures: " + ", ".join(missing_textures))

print("DIAMOND_MARKET_FBX_VALIDATION_OK")
print("Faces:", len(meshes[0].data.polygons))
print("Texture references:", len(imported))
bpy.ops.wm.quit_blender()
