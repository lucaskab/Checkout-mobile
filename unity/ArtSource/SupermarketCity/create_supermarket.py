"""Build and export a stylized, game-ready supermarket environment.

Run from Blender 5.2 or newer:
    Blender --background --python create_supermarket.py

The scene keeps the playable shell separate from preview-only objects.  The
FBX contains meshes only: visual meshes, simplified collision meshes, and LOD
proxies.  The preview camera and lights remain in the .blend only.
"""

import math
import os

import bpy
from mathutils import Vector


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(SCRIPT_DIR, "supermarket_city.blend")
FBX_PATH = os.path.abspath(
    os.path.join(SCRIPT_DIR, "../../Assets/Resources/Models/SupermarketCity/supermarket_city.fbx")
)
PREVIEW_PATH = os.path.join(SCRIPT_DIR, "supermarket_city_preview.png")
TEXTURE_DIR = os.path.abspath(
    os.path.join(SCRIPT_DIR, "../../Assets/Art/Textures/SupermarketCity")
)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def create_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def set_material(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)


def make_material(
    name,
    color,
    roughness=0.65,
    metallic=0.0,
    alpha=1.0,
    texture_filename=None,
    texture_scale=(1.0, 1.0, 1.0),
    tint_texture=False,
):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Alpha"].default_value = alpha
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.1 if alpha < 1.0 else 0.0
    try:
        material.surface_render_method = "DITHERED"
    except AttributeError:
        pass

    if texture_filename:
        texture_path = os.path.join(TEXTURE_DIR, texture_filename)
        if not os.path.exists(texture_path):
            raise RuntimeError("Texture file is missing: " + texture_path)
        image = bpy.data.images.load(texture_path, check_existing=True)
        image.colorspace_settings.name = "sRGB"

        coordinates = nodes.new("ShaderNodeTexCoord")
        coordinates.name = "TextureCoordinates"
        mapping = nodes.new("ShaderNodeMapping")
        mapping.name = "TextureMapping"
        mapping.inputs["Scale"].default_value = texture_scale
        texture = nodes.new("ShaderNodeTexImage")
        texture.name = "AlbedoTexture"
        texture.image = image
        texture.interpolation = "Linear"
        texture.extension = "REPEAT"
        texture.projection = "BOX"
        texture.projection_blend = 0.18
        links.new(coordinates.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], texture.inputs["Vector"])

        if tint_texture:
            tint = nodes.new("ShaderNodeMixRGB")
            tint.name = "TextureTint"
            tint.blend_type = "MULTIPLY"
            tint.inputs["Fac"].default_value = 1.0
            tint.inputs["Color2"].default_value = (*color, 1.0)
            links.new(texture.outputs["Color"], tint.inputs["Color1"])
            links.new(tint.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
        material["albedo_texture"] = texture_filename
    return material


def apply_scale_and_rotation(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def add_bevel(obj, width=0.08, segments=2):
    smallest_dimension = min(abs(value) for value in obj.dimensions)
    width = min(width, smallest_dimension * 0.22)
    if width <= 0.001:
        return
    modifier = obj.modifiers.new("Soft_Edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def add_box(name, location, dimensions, material, collection, bevel=0.0, role="visual"):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    apply_scale_and_rotation(obj)
    if bevel:
        add_bevel(obj, bevel)
    set_material(obj, material)
    obj["game_role"] = role
    move_to_collection(obj, collection)
    return obj


def add_cylinder(
    name,
    location,
    radius,
    depth,
    material,
    collection,
    vertices=12,
    bevel=0.0,
    role="visual",
):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    apply_scale_and_rotation(obj)
    if bevel:
        add_bevel(obj, bevel)
    set_material(obj, material)
    obj["game_role"] = role
    move_to_collection(obj, collection)
    return obj


def add_ico_sphere(name, location, scale, material, collection, role="visual"):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    apply_scale_and_rotation(obj)
    set_material(obj, material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj["game_role"] = role
    move_to_collection(obj, collection)
    return obj


def add_arch(name, center, outer_radius, thickness, depth, material, collection, segments=12):
    """Create a light, extruded semi-circular arch in the X/Z plane."""
    cx, cy, cz = center
    inner_radius = outer_radius - thickness
    front_y = cy - depth * 0.5
    back_y = cy + depth * 0.5
    vertices = []
    faces = []

    for index in range(segments + 1):
        angle = math.pi - math.pi * index / segments
        outer_x = cx + math.cos(angle) * outer_radius
        outer_z = cz + math.sin(angle) * outer_radius
        inner_x = cx + math.cos(angle) * inner_radius
        inner_z = cz + math.sin(angle) * inner_radius
        vertices.extend(
            [
                (outer_x, front_y, outer_z),
                (inner_x, front_y, inner_z),
                (outer_x, back_y, outer_z),
                (inner_x, back_y, inner_z),
            ]
        )

    for index in range(segments):
        base = index * 4
        next_base = (index + 1) * 4
        faces.extend(
            [
                (base, next_base, next_base + 1, base + 1),
                (base + 2, base + 3, next_base + 3, next_base + 2),
                (base, base + 2, next_base + 2, next_base),
                (base + 1, next_base + 1, next_base + 3, base + 3),
            ]
        )

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.validate(clean_customdata=True)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    set_material(obj, material)
    add_bevel(obj, 0.035, 2)
    obj["game_role"] = "visual"
    return obj


def add_window_group(name, center_x, front_y, width, glass, cream, supermarket, center_z=1.25, glass_height=1.05):
    glass_panel = add_box(
        name,
        (center_x, front_y, center_z),
        (width, 0.10, glass_height),
        glass,
        supermarket,
        0.025,
    )
    frame_height = glass_height + 0.24
    top_z = center_z + glass_height * 0.5 + 0.12
    bottom_z = center_z - glass_height * 0.5 - 0.12
    add_box(name + "_Top", (center_x, front_y - 0.035, top_z), (width + 0.22, 0.18, 0.16), cream, supermarket, 0.04)
    add_box(name + "_Bottom", (center_x, front_y - 0.035, bottom_z), (width + 0.22, 0.18, 0.16), cream, supermarket, 0.04)
    for index in range(3):
        divider_x = center_x - width * 0.5 + (index + 1) * width / 3
        add_box(name + "_Mullion_{:02d}".format(index + 1), (divider_x, front_y - 0.045, center_z), (0.12, 0.17, frame_height), cream, supermarket, 0.025)
    for side, x in (("Left", center_x - width * 0.5), ("Right", center_x + width * 0.5)):
        add_box(name + "_Frame_" + side, (x, front_y - 0.045, center_z), (0.18, 0.17, frame_height), cream, supermarket, 0.04)
    return glass_panel


def add_planter(name, location, scale, cream, leaves, flowers, props, vegetation):
    add_box(name + "_Body", location, scale, cream, props, 0.12)
    bush_count = 3 if scale[0] > scale[1] else 1
    for index in range(bush_count):
        offset = 0.0 if bush_count == 1 else -scale[0] * 0.28 + index * scale[0] * 0.28
        add_ico_sphere(
            name + "_Bush_{:02d}".format(index + 1),
            (location[0] + offset, location[1], location[2] + scale[2] * 0.55),
            (scale[0] * 0.22, scale[1] * 0.38, scale[2] * 0.62),
            leaves,
            vegetation,
        )
        if index % 2 == 0:
            add_ico_sphere(
                name + "_Flower_{:02d}".format(index + 1),
                (location[0] + offset + 0.12, location[1] - scale[1] * 0.2, location[2] + scale[2] * 0.9),
                (0.08, 0.08, 0.08),
                flowers,
                vegetation,
            )


def add_tree(name, location, scale, wood, leaves, leaves_light, vegetation):
    add_cylinder(name + "_Trunk", (location[0], location[1], location[2] + scale * 0.85), scale * 0.16, scale * 1.7, wood, vegetation, vertices=10, bevel=0.03)
    add_ico_sphere(name + "_Crown", (location[0], location[1], location[2] + scale * 2.05), (scale, scale, scale * 1.05), leaves, vegetation)
    add_ico_sphere(name + "_CrownAccent", (location[0] + scale * 0.35, location[1] - scale * 0.2, location[2] + scale * 2.30), (scale * 0.58, scale * 0.55, scale * 0.6), leaves_light, vegetation)


def add_collision(name, location, dimensions, collisions):
    collision = add_box(name, location, dimensions, COLLISION, collisions, role="collision")
    collision.display_type = "WIRE"
    collision.hide_render = True
    return collision


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_scene():
    global COLLISION

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1536
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 65
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.use_nodes = True
    world_background = scene.world.node_tree.nodes.get("Background")
    world_background.inputs["Color"].default_value = (0.18, 0.21, 0.23, 1.0)
    world_background.inputs["Strength"].default_value = 0.42

    supermarket = create_collection("Supermarket")
    environment = create_collection("Environment")
    vegetation = create_collection("Vegetation")
    props = create_collection("Props")
    background = create_collection("BackgroundBuildings")
    collisions = create_collection("Collisions")
    lods = create_collection("LODs")
    preview = create_collection("Preview")

    turquoise = make_material("MAT_Turquoise", (0.055, 0.49, 0.47), 0.52, texture_filename="tex_wall_turquoise_v1.png", texture_scale=(2.4, 2.4, 2.4))
    turquoise_light = make_material("MAT_Turquoise_Light", (0.14, 0.66, 0.63), 0.48, texture_filename="tex_wall_turquoise_v1.png", texture_scale=(3.1, 3.1, 3.1))
    coral = make_material("MAT_Coral", (0.94, 0.30, 0.20), 0.48, texture_filename="tex_wall_coral_v1.png", texture_scale=(3.0, 3.0, 3.0))
    cream = make_material("MAT_Cream", (0.96, 0.82, 0.58), 0.58, texture_filename="tex_stucco_detail_v1.png", texture_scale=(3.0, 3.0, 3.0), tint_texture=True)
    floor = make_material("MAT_Floor", (0.91, 0.70, 0.43), 0.72, texture_filename="tex_tile_cream_v1.png", texture_scale=(3.2, 3.2, 3.2))
    concrete = make_material("MAT_Concrete", (0.66, 0.61, 0.52), 0.78, texture_filename="tex_tile_cream_v1.png", texture_scale=(2.5, 2.5, 2.5))
    asphalt = make_material("MAT_Asphalt", (0.10, 0.13, 0.16), 0.88, texture_filename="tex_asphalt_stylized_v1.png", texture_scale=(4.0, 4.0, 4.0))
    grass = make_material("MAT_Grass", (0.20, 0.53, 0.19), 0.92, texture_filename="tex_grass_stylized_v1.png", texture_scale=(3.5, 3.5, 3.5))
    grass_dark = make_material("MAT_Grass_Dark", (0.35, 0.65, 0.35), 0.92, texture_filename="tex_grass_stylized_v1.png", texture_scale=(2.2, 2.2, 2.2), tint_texture=True)
    wood = make_material("MAT_Wood", (0.40, 0.20, 0.08), 0.76, texture_filename="tex_wood_stylized_v1.png", texture_scale=(2.5, 2.5, 2.5))
    leaves = make_material("MAT_Leaves", (0.19, 0.58, 0.16), 0.76, texture_filename="tex_foliage_stylized_v1.png", texture_scale=(1.25, 1.25, 1.25))
    leaves_light = make_material("MAT_Leaves_Light", (0.70, 0.88, 0.55), 0.72, texture_filename="tex_foliage_stylized_v1.png", texture_scale=(1.5, 1.5, 1.5), tint_texture=True)
    flowers = make_material("MAT_Flowers", (0.96, 0.26, 0.30), 0.46)
    glass = make_material("MAT_Glass", (0.22, 0.78, 0.78), 0.22, 0.04, 0.52)
    dark_metal = make_material("MAT_DarkMetal", (0.08, 0.12, 0.14), 0.38, 0.4)
    warm_light = make_material("MAT_WarmLight", (1.0, 0.67, 0.22), 0.25, 0.0)
    neutral = make_material("MAT_Neutral", (0.43, 0.45, 0.48), 0.72, texture_filename="tex_stucco_detail_v1.png", texture_scale=(2.0, 2.0, 2.0))
    house_blue = make_material("MAT_HouseBlue", (0.24, 0.46, 0.58), 0.74, texture_filename="tex_stucco_detail_v1.png", texture_scale=(2.5, 2.5, 2.5), tint_texture=True)
    house_peach = make_material("MAT_HousePeach", (0.82, 0.47, 0.31), 0.74, texture_filename="tex_stucco_detail_v1.png", texture_scale=(2.5, 2.5, 2.5), tint_texture=True)
    roof_tile = make_material("MAT_RoofTile", (0.45, 0.14, 0.09), 0.68, texture_filename="tex_tile_cream_v1.png", texture_scale=(3.2, 3.2, 3.2), tint_texture=True)
    COLLISION = make_material("MAT_Collision", (0.8, 0.08, 0.08), 0.6)

    # Environment foundation, sidewalks, road, and simple parking context.
    add_box("ENV_Ground", (0, 0, -0.18), (35, 35, 0.36), grass, environment, 0.12)
    add_box("ENV_Road", (0, -13.55, 0.03), (35, 6.45, 0.14), asphalt, environment, 0.04)
    add_box("ENV_Sidewalk_Front", (0, -9.08, 0.11), (28.7, 2.3, 0.20), concrete, environment, 0.08)
    add_box("ENV_Sidewalk_Left", (-12.55, 2.1, 0.11), (2.25, 18.8, 0.20), concrete, environment, 0.08)
    add_box("ENV_Sidewalk_Right", (12.55, 2.1, 0.11), (2.25, 18.8, 0.20), concrete, environment, 0.08)
    add_box("ENV_Sidewalk_Back", (0, 12.05, 0.11), (28.7, 2.25, 0.20), concrete, environment, 0.08)
    add_box("ENV_Curb_Front", (0, -10.22, 0.28), (30.2, 0.22, 0.28), cream, environment, 0.04)
    for x in (-8.5, -2.8, 2.8, 8.5):
        add_box("ENV_ParkingLine_{:02d}".format(int(x + 10)), (x, -13.35, 0.13), (0.16, 3.1, 0.035), cream, environment)
    for index, x in enumerate((-2.4, -1.6, -0.8, 0.0, 0.8, 1.6, 2.4)):
        add_box("ENV_Crosswalk_{:02d}".format(index + 1), (x, -10.85, 0.13), (0.42, 1.35, 0.035), cream, environment)

    # Interior floor is a separate, low-profile shell component.
    add_box("SM_Building_Floor", (0, 2.0, 0.14), (22.0, 17.0, 0.22), floor, supermarket, 0.10)
    for x in (-10.9, 10.9):
        add_box("SM_Interior_Skirting_" + ("Left" if x < 0 else "Right"), (x, 2.0, 0.54), (0.16, 16.3, 0.30), cream, supermarket, 0.025)
    add_box("SM_Interior_Skirting_Back", (0, 10.2, 0.54), (21.5, 0.16, 0.30), cream, supermarket, 0.025)

    # The main shell is intentionally a low-wall cutaway, so isometric gameplay never hides the store interior.
    wall_height = 1.30
    wall_center_z = 0.84
    top_band_z = 1.48
    top_trim_z = 1.76
    add_box("SM_Building_Walls_Back", (0, 10.35, wall_center_z), (22.0, 0.42, wall_height), turquoise, supermarket, 0.14)
    add_box("SM_Building_Walls_Left", (-10.8, 2.0, wall_center_z), (0.42, 17.1, wall_height), turquoise, supermarket, 0.14)
    add_box("SM_Building_Walls_Right", (10.8, 2.0, wall_center_z), (0.42, 17.1, wall_height), turquoise, supermarket, 0.14)
    add_box("SM_WallBand_Back", (0, 10.26, top_band_z), (22.16, 0.52, 0.28), coral, supermarket, 0.06)
    add_box("SM_WallBand_Left", (-10.88, 2.0, top_band_z), (0.54, 17.25, 0.28), coral, supermarket, 0.06)
    add_box("SM_WallBand_Right", (10.88, 2.0, top_band_z), (0.54, 17.25, 0.28), coral, supermarket, 0.06)
    add_box("SM_Trim_Back", (0, 10.24, top_trim_z), (22.35, 0.62, 0.24), cream, supermarket, 0.12)
    add_box("SM_Trim_Left", (-10.96, 2.0, top_trim_z), (0.62, 17.45, 0.24), cream, supermarket, 0.12)
    add_box("SM_Trim_Right", (10.96, 2.0, top_trim_z), (0.62, 17.45, 0.24), cream, supermarket, 0.12)

    # Rounded exterior corner accents support the cozy silhouette in the reference.
    for index, (x, y) in enumerate(((-10.72, -6.22), (10.72, -6.22), (-10.72, 10.22), (10.72, 10.22))):
        add_cylinder("SM_Corner_{:02d}_Base".format(index + 1), (x, y, wall_center_z), 0.72, wall_height, turquoise, supermarket, bevel=0.08)
        add_cylinder("SM_Corner_{:02d}_Band".format(index + 1), (x, y, top_band_z), 0.77, 0.30, coral, supermarket, bevel=0.05)
        add_cylinder("SM_Corner_{:02d}_Cap".format(index + 1), (x, y, top_trim_z), 0.83, 0.24, cream, supermarket, bevel=0.08)

    # Front facade. Separate doors make future automatic-door animation straightforward.
    front_y = -6.48
    add_box("SM_Front_Wall_Left_Base", (-6.6, front_y, 0.56), (8.0, 0.42, 0.72), turquoise, supermarket, 0.09)
    add_box("SM_Front_Wall_Right_Base", (6.6, front_y, 0.56), (8.0, 0.42, 0.72), turquoise, supermarket, 0.09)
    add_window_group("SM_Window_Left", -6.45, front_y - 0.05, 7.25, glass, cream, supermarket, center_z=1.25, glass_height=1.05)
    add_window_group("SM_Window_Right", 6.45, front_y - 0.05, 7.25, glass, cream, supermarket, center_z=1.25, glass_height=1.05)
    add_box("SM_FrontBand_Left", (-6.6, front_y - 0.02, top_band_z), (8.15, 0.54, 0.28), coral, supermarket, 0.06)
    add_box("SM_FrontBand_Right", (6.6, front_y - 0.02, top_band_z), (8.15, 0.54, 0.28), coral, supermarket, 0.06)
    add_box("SM_FrontTrim_Left", (-6.6, front_y - 0.02, top_trim_z), (8.35, 0.62, 0.24), cream, supermarket, 0.10)
    add_box("SM_FrontTrim_Right", (6.6, front_y - 0.02, top_trim_z), (8.35, 0.62, 0.24), cream, supermarket, 0.10)
    add_box("SM_Entrance_Threshold", (0, -6.88, 0.20), (4.65, 1.25, 0.15), cream, supermarket, 0.08)
    add_box("SM_Entrance_Door_Left", (-0.92, -6.62, 1.42), (1.72, 0.12, 2.38), glass, supermarket, 0.03)
    add_box("SM_Entrance_Door_Right", (0.92, -6.62, 1.42), (1.72, 0.12, 2.38), glass, supermarket, 0.03)
    for door in (bpy.data.objects["SM_Entrance_Door_Left"], bpy.data.objects["SM_Entrance_Door_Right"]):
        door["animation_type"] = "SLIDE_X"
        door["pivot"] = "center_for_sliding_door"
    add_box("SM_Entrance_Frame_Left", (-2.02, -6.70, 1.55), (0.24, 0.30, 2.95), cream, supermarket, 0.06)
    add_box("SM_Entrance_Frame_Right", (2.02, -6.70, 1.55), (0.24, 0.30, 2.95), cream, supermarket, 0.06)
    add_box("SM_Entrance_Frame_Center", (0, -6.70, 1.42), (0.16, 0.30, 2.42), cream, supermarket, 0.025)
    add_box("SM_Entrance_Header_Coral", (0, -6.70, 2.88), (4.75, 0.36, 0.42), coral, supermarket, 0.08)
    add_arch("SM_Entrance_Arch", (0, -6.70, 1.50), 2.12, 0.24, 0.34, cream, supermarket)

    # Door handles and decorative wall sconces.
    for index, x in enumerate((-0.18, 0.18)):
        add_cylinder("PROP_Door_Handle_{:02d}".format(index + 1), (x, -6.77, 1.63), 0.045, 0.50, dark_metal, props, vertices=8)
        bpy.context.object.rotation_euler[0] = math.radians(90)
        apply_scale_and_rotation(bpy.context.object)
    for index, x in enumerate((-2.85, 2.85)):
        add_cylinder("PROP_Entrance_Lamp_{:02d}".format(index + 1), (x, -6.74, 2.0), 0.23, 0.12, warm_light, props, vertices=12, bevel=0.03)
        bpy.context.object.rotation_euler[0] = math.radians(90)
        apply_scale_and_rotation(bpy.context.object)
        add_box("PROP_Entrance_Lamp_Back_{:02d}".format(index + 1), (x, -6.68, 2.0), (0.44, 0.08, 0.44), dark_metal, props, 0.04)

    # A complete checkout counter is part of the shell, so customers have a readable place to pay.
    add_box("PROP_Checkout_Base", (6.0, -2.80, 0.68), (3.15, 1.42, 1.30), turquoise, props, 0.10)
    add_box("PROP_Checkout_Front", (6.0, -3.53, 0.72), (2.82, 0.10, 0.82), coral, props, 0.03)
    add_box("PROP_Checkout_Countertop", (6.0, -2.80, 1.42), (3.34, 1.58, 0.18), cream, props, 0.08)
    add_box("PROP_Checkout_Conveyor", (6.55, -2.92, 1.54), (1.36, 0.72, 0.05), dark_metal, props, 0.03)
    add_box("PROP_Checkout_Monitor", (5.38, -2.65, 2.00), (0.62, 0.18, 0.58), dark_metal, props, 0.04)
    add_cylinder("PROP_Checkout_MonitorStand", (5.38, -2.65, 1.68), 0.07, 0.34, dark_metal, props, vertices=8)
    add_box("PROP_Checkout_Bag", (6.92, -2.48, 1.70), (0.42, 0.38, 0.48), coral, props, 0.05)

    # A separate roof object is exported but intentionally omitted from the preview render.
    roof = add_box("Roof", (0, 2.0, 3.80), (22.35, 17.45, 0.14), cream, supermarket, 0.12)
    roof.hide_render = True
    roof["engine_toggleable"] = True
    roof["purpose"] = "Optional roof. Hide or remove in the game to expose the interior."

    # Planters, trees and simple foliage around the facade and side paths.
    add_planter("PROP_FrontPlanter_Left", (-8.65, -7.55, 0.55), (2.85, 0.76, 0.62), cream, leaves, flowers, props, vegetation)
    add_planter("PROP_FrontPlanter_Right", (8.65, -7.55, 0.55), (2.85, 0.76, 0.62), cream, leaves, flowers, props, vegetation)
    add_planter("PROP_EntryPlanter_Left", (-3.55, -7.35, 0.46), (0.95, 0.85, 0.52), cream, leaves, flowers, props, vegetation)
    add_planter("PROP_EntryPlanter_Right", (3.55, -7.35, 0.46), (0.95, 0.85, 0.52), cream, leaves, flowers, props, vegetation)
    add_tree("VEG_Tree_01", (-14.25, -2.7, 0.0), 1.25, wood, leaves, leaves_light, vegetation)
    add_tree("VEG_Tree_02", (14.25, -1.2, 0.0), 1.15, wood, leaves, leaves_light, vegetation)
    add_tree("VEG_Tree_03", (-10.8, 13.7, 0.0), 1.0, wood, leaves, leaves_light, vegetation)
    add_tree("VEG_Tree_04", (13.8, 9.8, 0.0), 1.05, wood, leaves, leaves_light, vegetation)

    # Simple city props give the storefront a believable urban context.
    add_cylinder("PROP_TrashBin", (8.2, -9.1, 0.58), 0.30, 1.0, dark_metal, props, vertices=12, bevel=0.04)
    add_cylinder("PROP_TrashBin_Lid", (8.2, -9.1, 1.10), 0.33, 0.12, dark_metal, props, vertices=12, bevel=0.03)
    add_cylinder("PROP_StreetLamp_Pole", (-8.4, -9.25, 2.05), 0.09, 3.9, dark_metal, props, vertices=10)
    add_box("PROP_StreetLamp_Head", (-8.4, -9.25, 4.05), (0.50, 0.50, 0.32), warm_light, props, 0.08)
    for index, x in enumerate((4.0, 4.55, 5.1)):
        add_cylinder("PROP_BikeRack_{:02d}".format(index + 1), (x, -8.7, 0.43), 0.06, 0.85, dark_metal, props, vertices=8)
        bpy.context.object.rotation_euler[0] = math.radians(90)
        apply_scale_and_rotation(bpy.context.object)

    # Hand-authored production props follow the rounded, storybook treatment of the reference sheet.
    def add_bakery_roof_segment(name, x, y, z, width, depth, tilt):
        segment = add_box(name, (x, y, z), (width, depth, 0.22), cream, props, 0.08)
        segment.rotation_euler[1] = math.radians(tilt)
        apply_scale_and_rotation(segment)
        return segment

    def add_storybook_bakery(name, location):
        x, y, base_z = location
        front_y = y - 1.70
        add_box(name + "_Foundation", (x, y, base_z + 0.16), (4.42, 3.62, 0.32), concrete, props, 0.12)
        add_box(name + "_Walls", (x, y, base_z + 1.22), (4.12, 3.24, 1.92), wood, props, 0.12)
        add_box(name + "_BaseTrim", (x, y, base_z + 0.46), (4.26, 3.36, 0.24), neutral, props, 0.06)
        add_box(name + "_TopTrim", (x, y, base_z + 2.15), (4.34, 3.44, 0.24), turquoise, props, 0.10)
        for side, px in (("Left", x - 1.83), ("Right", x + 1.83)):
            add_box(name + "_Pillar_" + side, (px, front_y, base_z + 1.18), (0.34, 0.38, 1.90), turquoise, props, 0.09)
            add_box(name + "_PillarCap_" + side, (px, front_y - 0.02, base_z + 2.10), (0.44, 0.46, 0.22), coral, props, 0.06)

        # Curved segmented roof: the silhouette is intentionally more important than geometric realism.
        roof_positions = ((-1.52, 38, 2.65), (-1.10, 28, 3.02), (-0.62, 16, 3.27), (0.0, 0, 3.38), (0.62, -16, 3.27), (1.10, -28, 3.02), (1.52, -38, 2.65))
        for index, (offset, tilt, height) in enumerate(roof_positions):
            add_bakery_roof_segment(name + "_Roof_{:02d}".format(index + 1), x + offset, y + 0.08, base_z + height, 0.72, 3.46, tilt)
        add_box(name + "_RoofEdge", (x, front_y - 0.02, base_z + 2.82), (4.48, 0.26, 0.22), cream, props, 0.06)
        add_arch(name + "_BreadArch", (x, front_y - 0.16, base_z + 2.20), 1.22, 0.22, 0.28, turquoise, props, segments=16)
        add_box(name + "_BreadSign", (x, front_y - 0.19, base_z + 2.43), (1.58, 0.12, 0.76), cream, props, 0.10)
        loaf = add_ico_sphere(name + "_BreadSign_Loaf", (x, front_y - 0.28, base_z + 2.45), (0.55, 0.12, 0.25), coral, props)
        for index, offset in enumerate((-0.22, 0.0, 0.22)):
            score = add_box(name + "_BreadScore_{:02d}".format(index + 1), (x + offset, front_y - 0.41, base_z + 2.51), (0.07, 0.04, 0.24), cream, props, 0.01)
            score.rotation_euler[1] = math.radians(-32)
            apply_scale_and_rotation(score)

        # Door, window and a loaded bread display give the prop a readable production identity.
        add_arch(name + "_DoorArch", (x - 0.92, front_y - 0.08, base_z + 0.52), 0.58, 0.13, 0.18, cream, props, segments=12)
        add_box(name + "_Door", (x - 0.92, front_y - 0.12, base_z + 0.91), (0.85, 0.12, 1.32), turquoise, props, 0.10)
        add_cylinder(name + "_DoorKnob", (x - 0.63, front_y - 0.22, base_z + 0.92), 0.06, 0.08, warm_light, props, vertices=8)
        add_box(name + "_DisplayFrame", (x + 0.93, front_y - 0.10, base_z + 1.03), (1.52, 0.18, 1.30), cream, props, 0.08)
        add_box(name + "_DisplayShadow", (x + 0.93, front_y - 0.21, base_z + 1.03), (1.28, 0.05, 1.05), dark_metal, props, 0.02)
        for row in range(2):
            shelf_z = base_z + 0.73 + row * 0.44
            add_box(name + "_BreadShelf_{:02d}".format(row + 1), (x + 0.93, front_y - 0.28, shelf_z), (1.24, 0.25, 0.07), cream, props, 0.02)
            for column in range(3):
                add_ico_sphere(name + "_Loaf_{:02d}_{:02d}".format(row + 1, column + 1), (x + 0.52 + column * 0.40, front_y - 0.39, shelf_z + 0.13), (0.17, 0.12, 0.11), coral, props)

        # The striped canopy is made from individual rounded pieces instead of a flat textured plane.
        for index in range(7):
            stripe_material = coral if index % 2 == 0 else cream
            add_box(name + "_Awning_{:02d}".format(index + 1), (x - 1.42 + index * 0.47, front_y - 0.48, base_z + 1.72), (0.48, 0.90, 0.16), stripe_material, props, 0.10)
        add_planter(name + "_Planter", (x + 1.74, front_y - 0.56, base_z + 0.30), (0.68, 0.46, 0.46), cream, leaves, flowers, props, vegetation)
        add_cylinder(name + "_Barrel", (x - 2.10, front_y - 0.25, base_z + 0.52), 0.28, 0.72, wood, props, vertices=12, bevel=0.05)
        for band_z in (base_z + 0.32, base_z + 0.69):
            add_cylinder(name + "_BarrelBand_{:.2f}".format(band_z), (x - 2.10, front_y - 0.25, band_z), 0.30, 0.06, dark_metal, props, vertices=12)

    def add_crop_patch(name, location, crop_type):
        x, y, base_z = location
        add_box(name + "_Soil", (x, y, base_z + 0.16), (3.10, 2.35, 0.28), wood, props, 0.16)
        for side, px, py, sx, sy in (("Top", x, y + 1.10, 3.20, 0.20), ("Bottom", x, y - 1.10, 3.20, 0.20), ("Left", x - 1.50, y, 0.20, 2.40), ("Right", x + 1.50, y, 0.20, 2.40)):
            add_box(name + "_Stone_" + side, (px, py, base_z + 0.30), (sx, sy, 0.36), concrete, props, 0.10)
        for index, (ox, oy) in enumerate(((-0.82, -0.48), (0.0, -0.48), (0.82, -0.48), (-0.42, 0.42), (0.42, 0.42))):
            if crop_type == "tomato":
                add_cylinder(name + "_Stake_{:02d}".format(index + 1), (x + ox, y + oy, base_z + 0.72), 0.035, 0.92, wood, props, vertices=6)
                add_ico_sphere(name + "_Leaves_{:02d}".format(index + 1), (x + ox, y + oy, base_z + 0.90), (0.34, 0.30, 0.40), leaves, vegetation)
                add_ico_sphere(name + "_Tomato_{:02d}".format(index + 1), (x + ox + 0.12, y + oy - 0.08, base_z + 0.68), (0.13, 0.13, 0.13), coral, props)
            elif crop_type == "carrot":
                add_ico_sphere(name + "_Carrot_{:02d}".format(index + 1), (x + ox, y + oy, base_z + 0.49), (0.13, 0.13, 0.23), coral, props)
                add_ico_sphere(name + "_Greens_{:02d}".format(index + 1), (x + ox, y + oy, base_z + 0.72), (0.24, 0.18, 0.32), leaves_light, vegetation)
            else:
                add_ico_sphere(name + "_Cabbage_{:02d}".format(index + 1), (x + ox, y + oy, base_z + 0.52), (0.42, 0.36, 0.28), leaves, vegetation)
                add_ico_sphere(name + "_CabbageCore_{:02d}".format(index + 1), (x + ox, y + oy - 0.03, base_z + 0.62), (0.25, 0.22, 0.18), leaves_light, vegetation)

    def add_storybook_fence(name, location, length, rotation=0):
        x, y, base_z = location
        root = add_box(name + "_RailLower", (x, y, base_z + 0.54), (length, 0.14, 0.14), wood, props, 0.05)
        root.rotation_euler[2] = math.radians(rotation)
        apply_scale_and_rotation(root)
        upper = add_box(name + "_RailUpper", (x, y, base_z + 0.94), (length, 0.14, 0.14), wood, props, 0.05)
        upper.rotation_euler[2] = math.radians(rotation)
        apply_scale_and_rotation(upper)
        half = length * 0.5
        for side, offset in (("Left", -half), ("Right", half)):
            post = add_box(name + "_Post_" + side, (x + offset, y, base_z + 0.74), (0.24, 0.24, 1.48), wood, props, 0.06)
            post.rotation_euler[2] = math.radians(rotation)
            apply_scale_and_rotation(post)
            cap = add_box(name + "_Cap_" + side, (x + offset, y, base_z + 1.52), (0.32, 0.32, 0.22), coral, props, 0.07)
            cap.rotation_euler[2] = math.radians(rotation)
            apply_scale_and_rotation(cap)

    add_storybook_bakery("PROP_StorybookBakery", (15.15, 3.10, 0.0))
    add_crop_patch("PROP_CabbagePatch", (-14.0, 4.55, 0.0), "cabbage")
    add_crop_patch("PROP_TomatoPatch", (-14.0, 7.25, 0.0), "tomato")
    add_crop_patch("PROP_CarrotPatch", (-14.0, 9.95, 0.0), "carrot")
    add_storybook_fence("PROP_GardenFence_Front", (-14.0, 3.16, 0.0), 3.72)
    add_storybook_fence("PROP_GardenFence_Left", (-15.78, 6.95, 0.0), 7.10, 90)

    # Neighboring homes are deliberately complete stylized silhouettes rather than anonymous cubes.
    def add_pitched_roof_part(name, location, dimensions, tilt):
        roof_part = add_box(name, location, dimensions, roof_tile, background, 0.08)
        roof_part.rotation_euler[1] = math.radians(tilt)
        apply_scale_and_rotation(roof_part)
        return roof_part

    def add_background_house(name, location, dimensions, body_material):
        x, y, base_z = location
        width, depth, height = dimensions
        wall_height = height * 0.68
        facade_y = y - depth * 0.5 - 0.04
        add_box(name + "_Walls", (x, y, base_z + wall_height * 0.5), (width, depth, wall_height), body_material, background, 0.16)
        add_box(name + "_Foundation", (x, y, base_z + 0.12), (width + 0.18, depth + 0.18, 0.24), concrete, background, 0.08)
        add_pitched_roof_part(name + "_RoofLeft", (x - width * 0.23, y, base_z + wall_height + 0.48), (width * 0.62, depth + 0.32, 0.34), -27)
        add_pitched_roof_part(name + "_RoofRight", (x + width * 0.23, y, base_z + wall_height + 0.48), (width * 0.62, depth + 0.32, 0.34), 27)
        add_box(name + "_RoofRidge", (x, y, base_z + wall_height + 0.90), (0.24, depth + 0.32, 0.22), cream, background, 0.05)
        add_box(name + "_Door", (x, facade_y, base_z + 0.85), (1.12, 0.12, 1.55), wood, background, 0.05)
        add_cylinder(name + "_DoorKnob", (x + 0.34, facade_y - 0.08, base_z + 0.92), 0.05, 0.08, warm_light, background, vertices=8)
        for index, offset in enumerate((-width * 0.27, width * 0.27)):
            add_box(name + "_WindowFrame_{:02d}".format(index + 1), (x + offset, facade_y - 0.02, base_z + 1.72), (1.34, 0.14, 1.20), cream, background, 0.05)
            add_box(name + "_WindowGlass_{:02d}".format(index + 1), (x + offset, facade_y - 0.10, base_z + 1.72), (1.13, 0.04, 0.99), glass, background, 0.02)
            add_box(name + "_WindowMullion_{:02d}".format(index + 1), (x + offset, facade_y - 0.13, base_z + 1.72), (0.08, 0.05, 1.04), cream, background, 0.01)
        add_box(name + "_Porch", (x, facade_y - 0.46, base_z + 0.10), (2.25, 0.78, 0.18), concrete, background, 0.06)
        add_box(name + "_Chimney", (x + width * 0.30, y + depth * 0.16, base_z + wall_height + 1.00), (0.45, 0.52, 1.30), coral, background, 0.04)

    add_background_house("BG_House_01", (-13.4, 14.1, 0.14), (7.1, 4.8, 5.3), house_blue)
    add_background_house("BG_House_02", (12.7, 14.2, 0.14), (7.5, 4.7, 4.9), house_peach)
    add_box("BG_GardenWall_Left", (-16.0, 3.1, 0.86), (0.42, 10.6, 1.72), neutral, background, 0.08)

    # Efficient collision proxy meshes; they are visible only as wireframes in Blender.
    add_collision("UCX_SM_Wall_Back", (0, 10.35, wall_center_z), (22.0, 0.42, 1.8), collisions)
    add_collision("UCX_SM_Wall_Left", (-10.8, 2.0, wall_center_z), (0.42, 17.1, 1.8), collisions)
    add_collision("UCX_SM_Wall_Right", (10.8, 2.0, wall_center_z), (0.42, 17.1, 1.8), collisions)
    add_collision("UCX_SM_Wall_Front_Left", (-6.6, front_y, 1.0), (8.0, 0.42, 1.75), collisions)
    add_collision("UCX_SM_Wall_Front_Right", (6.6, front_y, 1.0), (8.0, 0.42, 1.75), collisions)
    add_collision("UCX_SM_Floor", (0, 2.0, 0.14), (22.0, 17.0, 0.22), collisions)

    # LOD proxy meshes are intentionally hidden in the preview and exported as named alternatives.
    # The names avoid Unity's automatic _LOD naming convention because the full LOD0 is modular.
    lod1 = add_box("SM_Supermarket_Proxy_Near", (0, 2.0, 0.92), (22.0, 17.0, 1.84), turquoise, lods, 0.10, role="lod1")
    lod2 = add_box("SM_Supermarket_Proxy_Far", (0, 2.0, 0.70), (21.5, 16.5, 1.40), turquoise, lods, 0.04, role="lod2")
    lod1.hide_render = True
    lod2.hide_render = True

    # Preview-only camera and warm, soft lighting. These objects are excluded from the FBX.
    bpy.ops.object.camera_add(location=(25.0, -28.0, 27.0))
    camera = bpy.context.object
    camera.name = "Preview_Camera_Isometric"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 37.0
    look_at(camera, (0.0, 1.0, 1.6))
    move_to_collection(camera, preview)
    scene.camera = camera

    bpy.ops.object.light_add(type="SUN", location=(6.0, -8.0, 22.0))
    sun = bpy.context.object
    sun.name = "Preview_Sun"
    sun.data.energy = 2.8
    sun.data.angle = math.radians(20.0)
    sun.rotation_euler = (math.radians(28.0), math.radians(-18.0), math.radians(28.0))
    move_to_collection(sun, preview)
    bpy.ops.object.light_add(type="AREA", location=(-7.0, -10.0, 15.0))
    fill = bpy.context.object
    fill.name = "Preview_FillLight"
    fill.data.energy = 1350.0
    fill.data.shape = "DISK"
    fill.data.size = 10.0
    look_at(fill, (0.0, 1.0, 0.0))
    move_to_collection(fill, preview)
    bpy.ops.object.light_add(type="AREA", location=(11.0, 9.0, 13.0))
    rim = bpy.context.object
    rim.name = "Preview_RimLight"
    rim.data.energy = 1000.0
    rim.data.shape = "DISK"
    rim.data.size = 12.0
    look_at(rim, (0.0, 2.0, 1.7))
    move_to_collection(rim, preview)

    # Keep the preview composition open: roof, LODs and collisions must not obscure the interior.
    for obj in collisions.objects:
        obj.hide_render = True
    for obj in lods.objects:
        obj.hide_render = True

    # Add a little visual variation to grass without procedural materials.
    for index, (x, y, sx, sy) in enumerate(((-14.0, 7.0, 2.0, 4.0), (14.0, 6.7, 2.2, 4.5), (-14.0, -5.2, 2.0, 2.0), (14.0, -4.8, 2.0, 2.4))):
        patch = add_box("ENV_GrassPatch_{:02d}".format(index + 1), (x, y, 0.025), (sx, sy, 0.04), grass_dark, environment, 0.06)
        patch.hide_render = False


def export_game_asset():
    export_objects = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        if any(collection.name == "Preview" for collection in obj.users_collection):
            continue
        export_objects.append(obj)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = export_objects[0]

    bpy.ops.export_scene.fbx(
        filepath=FBX_PATH,
        use_selection=True,
        object_types={"MESH"},
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="AUTO",
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z",
        axis_up="Y",
    )
    return export_objects


def validate_scene(export_objects):
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
    missing = sorted(required.difference(bpy.data.objects.keys()))
    if missing:
        raise RuntimeError("Missing required game objects: " + ", ".join(missing))
    if not os.path.exists(BLEND_PATH):
        raise RuntimeError("Blend file was not saved")
    if not os.path.exists(FBX_PATH) or os.path.getsize(FBX_PATH) == 0:
        raise RuntimeError("FBX file was not exported")
    print("VALIDATION_OK")
    print("Export mesh count:", len(export_objects))
    print("FBX path:", FBX_PATH)
    print("Blend path:", BLEND_PATH)
    print("Preview path:", PREVIEW_PATH)


def main():
    clean_scene()
    create_scene()
    bpy.context.scene.render.filepath = PREVIEW_PATH
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    export_objects = export_game_asset()
    validate_scene(export_objects)
    if not bpy.app.background:
        bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    main()
