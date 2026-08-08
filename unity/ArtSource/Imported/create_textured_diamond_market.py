"""Prepare the supplied Meshy courtyard as the game-ready Unity market shell."""

import math
import os

import bpy
from mathutils import Vector


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_PATH = os.path.join(SCRIPT_DIR, "diamond_courtyard_market_source.fbx")
BLEND_PATH = os.path.join(SCRIPT_DIR, "diamond_courtyard_market_textured.blend")
PREVIEW_PATH = os.path.join(SCRIPT_DIR, "diamond_courtyard_market_textured_preview.png")
TEXTURE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../Assets/Art/Textures/SupermarketCity"))
FBX_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "../../Assets/Resources/Models/DiamondMarket/diamond_market.fbx"))


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def make_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def make_material(name, color, texture_filename, roughness=0.62, metallic=0.0, alpha=1.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        try:
            material.surface_render_method = "DITHERED"
        except AttributeError:
            pass

    texture_path = os.path.join(TEXTURE_DIR, texture_filename)
    if not os.path.exists(texture_path):
        raise RuntimeError("Missing texture: " + texture_path)
    image = bpy.data.images.load(texture_path, check_existing=True)
    image.colorspace_settings.name = "sRGB"
    coordinates = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (2.8, 2.8, 2.8)
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.projection = "BOX"
    texture.projection_blend = 0.16
    texture.extension = "REPEAT"
    links.new(coordinates.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
    links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    material["albedo_texture"] = texture_filename
    return material


def make_glass():
    material = bpy.data.materials.new("MAT_DiamondMarket_Glass")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.10, 0.58, 0.62, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.18
    bsdf.inputs["Metallic"].default_value = 0.05
    bsdf.inputs["Alpha"].default_value = 0.70
    try:
        material.surface_render_method = "DITHERED"
    except AttributeError:
        pass
    return material


def apply_scale(obj, scale):
    obj.scale = (scale, scale, scale)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def polygon_center(mesh, polygon):
    center = Vector((0.0, 0.0, 0.0))
    for index in polygon.vertices:
        center += mesh.vertices[index].co
    return center / len(polygon.vertices)


def assign_market_materials(obj, materials):
    mesh = obj.data
    mesh.materials.clear()
    for material in materials:
        mesh.materials.append(material)

    floor, concrete, turquoise, coral, cream, glass, foliage = range(7)
    for polygon in mesh.polygons:
        center = polygon_center(mesh, polygon)
        normal = polygon.normal
        edge_distance = max(abs(center.x), abs(center.y))
        near_corner = abs(center.x) > 0.78 and abs(center.y) > 0.62

        if normal.z > 0.58:
            if center.z < -0.070:
                polygon.material_index = floor if edge_distance < 0.78 else concrete
            elif near_corner and center.z > -0.005:
                polygon.material_index = foliage
            elif center.z > 0.042:
                polygon.material_index = cream
            else:
                polygon.material_index = floor
            continue

        if center.z < -0.080:
            polygon.material_index = concrete
        elif center.y < -0.72 and abs(center.x) < 0.36 and -0.075 < center.z < 0.035:
            polygon.material_index = glass
        elif near_corner and center.z > -0.035:
            polygon.material_index = foliage
        elif edge_distance > 0.74:
            if center.z > 0.055:
                polygon.material_index = cream
            elif center.z > -0.010:
                polygon.material_index = coral
            else:
                polygon.material_index = turquoise
        elif center.z > 0.060:
            polygon.material_index = cream
        else:
            polygon.material_index = turquoise


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    clean_scene()
    os.makedirs(os.path.dirname(FBX_PATH), exist_ok=True)
    playable = make_collection("DiamondMarket")
    preview = make_collection("Preview")
    bpy.ops.import_scene.fbx(filepath=SOURCE_PATH)
    imported = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(imported) != 1:
        raise RuntimeError("Expected one market mesh, found {}".format(len(imported)))

    market = imported[0]
    market.name = "SM_DiamondCourtyardMarket"
    move_to_collection(market, playable)
    market.location = (0.0, 2.0, 0.0)

    materials = [
        make_material("MAT_DiamondMarket_Floor", (0.91, 0.70, 0.43), "tex_tile_cream_v1.png", 0.72),
        make_material("MAT_DiamondMarket_Concrete", (0.66, 0.61, 0.52), "tex_tile_cream_v1.png", 0.78),
        make_material("MAT_DiamondMarket_Turquoise", (0.055, 0.49, 0.47), "tex_wall_turquoise_v1.png", 0.52),
        make_material("MAT_DiamondMarket_Coral", (0.94, 0.30, 0.20), "tex_wall_coral_v1.png", 0.48),
        make_material("MAT_DiamondMarket_Cream", (0.96, 0.82, 0.58), "tex_stucco_detail_v1.png", 0.58),
        make_glass(),
        make_material("MAT_DiamondMarket_Foliage", (0.19, 0.58, 0.16), "tex_foliage_stylized_v1.png", 0.76),
    ]
    assign_market_materials(market, materials)
    apply_scale(market, 11.55)

    # The source is a high-density Meshy export. Keep the detailed silhouette while
    # bringing the static focal building into a realistic mobile triangle budget.
    decimator = market.modifiers.new("Mobile_Optimization", "DECIMATE")
    decimator.ratio = 0.18
    bpy.context.view_layer.objects.active = market
    bpy.ops.object.modifier_apply(modifier=decimator.name)

    # Preview-only presentation, excluded from the FBX.
    bpy.ops.object.camera_add(location=(25.0, -28.0, 27.0))
    camera = bpy.context.object
    camera.name = "Preview_Camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 35.0
    look_at(camera, (0.0, 2.0, 1.2))
    move_to_collection(camera, preview)
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="SUN", location=(6.0, -8.0, 22.0))
    sun = bpy.context.object
    sun.data.energy = 2.0
    sun.data.angle = math.radians(20.0)
    sun.rotation_euler = (math.radians(28.0), math.radians(-18.0), math.radians(28.0))
    move_to_collection(sun, preview)
    bpy.ops.object.light_add(type="AREA", location=(-7.0, -10.0, 15.0))
    fill = bpy.context.object
    fill.data.energy = 1100.0
    fill.data.size = 10.0
    look_at(fill, (0.0, 2.0, 0.0))
    move_to_collection(fill, preview)

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1536
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 65
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.18, 0.21, 0.23)
    scene.render.filepath = PREVIEW_PATH
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    bpy.ops.object.select_all(action="DESELECT")
    market.select_set(True)
    bpy.context.view_layer.objects.active = market
    bpy.ops.export_scene.fbx(
        filepath=FBX_PATH,
        use_selection=True,
        object_types={"MESH"},
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="COPY",
        embed_textures=False,
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z",
        axis_up="Y",
    )
    if not os.path.exists(FBX_PATH) or os.path.getsize(FBX_PATH) == 0:
        raise RuntimeError("Diamond market FBX export failed")
    print("DIAMOND_MARKET_EXPORT_OK")
    print("FBX path:", FBX_PATH)
    print("Faces:", len(market.data.polygons))
    print("Material face counts:", ", ".join(str(sum(1 for face in market.data.polygons if face.material_index == index)) for index in range(len(materials))))
    if not bpy.app.background:
        bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    main()
