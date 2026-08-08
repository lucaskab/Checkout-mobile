"""Optimize and export the supplied Meshy props with their original PBR textures."""

import os

import bpy


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../Assets/Resources/Models/Meshy"))
SPECS = (
    {
        "name": "checkout",
        "folder": "checkout_counter",
        "source": "Meshy_AI_Checkout_Counter_0807105305_image-to-3d-texture.fbx",
        "texture": "Meshy_AI_Checkout_Counter_0807105305_image-to-3d-texture.png",
        "roughness": "Meshy_AI_Checkout_Counter_0807105305_image-to-3d-texture_roughness.png",
        "metallic": "Meshy_AI_Checkout_Counter_0807105305_image-to-3d-texture_metallic.png",
        "normal": "Meshy_AI_Checkout_Counter_0807105305_image-to-3d-texture_normal.png",
        "emission": "Meshy_AI_Checkout_Counter_0807105305_image-to-3d-texture_emission.png",
        "scale": 1.35,
        "ratio": 0.11,
    },
    {
        "name": "entrance",
        "folder": "entrance_door",
        "source": "Meshy_AI_Store_Entrance_Door_0807105256_image-to-3d-texture.fbx",
        "texture": "Meshy_AI_Store_Entrance_Door_0807105256_image-to-3d-texture.png",
        "roughness": "Meshy_AI_Store_Entrance_Door_0807105256_image-to-3d-texture_roughness.png",
        "metallic": "Meshy_AI_Store_Entrance_Door_0807105256_image-to-3d-texture_metallic.png",
        "normal": "Meshy_AI_Store_Entrance_Door_0807105256_image-to-3d-texture_normal.png",
        "emission": "Meshy_AI_Store_Entrance_Door_0807105256_image-to-3d-texture_emission.png",
        "scale": 1.78,
        "ratio": 0.14,
    },
    {
        "name": "cashier",
        "folder": "cashier",
        "source": "Meshy_AI_Cashier_Character_0807105249_image-to-3d-texture.fbx",
        "texture": "Meshy_AI_Cashier_Character_0807105249_image-to-3d-texture.png",
        "roughness": "Meshy_AI_Cashier_Character_0807105249_image-to-3d-texture_roughness.png",
        "metallic": "Meshy_AI_Cashier_Character_0807105249_image-to-3d-texture_metallic.png",
        "normal": "Meshy_AI_Cashier_Character_0807105249_image-to-3d-texture_normal.png",
        "emission": "Meshy_AI_Cashier_Character_0807105249_image-to-3d-texture_emission.png",
        "scale": 0.94,
        "ratio": 0.12,
    },
    {
        "name": "bakery_display",
        "folder": "bakery_display",
        "source": "Meshy_AI_Bakery_Display_Case_0807105230_image-to-3d-texture.fbx",
        "texture": "Meshy_AI_Bakery_Display_Case_0807105230_image-to-3d-texture.png",
        "roughness": "Meshy_AI_Bakery_Display_Case_0807105230_image-to-3d-texture_roughness.png",
        "metallic": "Meshy_AI_Bakery_Display_Case_0807105230_image-to-3d-texture_metallic.png",
        "normal": "Meshy_AI_Bakery_Display_Case_0807105230_image-to-3d-texture_normal.png",
        "emission": "Meshy_AI_Bakery_Display_Case_0807105230_image-to-3d-texture_emission.png",
        "scale": 1.42,
        "ratio": 0.085,
    },
)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)


def load_image(path, non_color=False):
    image = bpy.data.images.load(path, check_existing=True)
    image.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return image


def create_pbr_material(spec):
    source_dir = os.path.join(SCRIPT_DIR, spec["folder"])
    material = bpy.data.materials.new("MAT_Meshy_" + spec["name"])
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.56

    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = load_image(os.path.join(source_dir, spec["texture"]))
    links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])

    roughness = nodes.new("ShaderNodeTexImage")
    roughness.image = load_image(os.path.join(source_dir, spec["roughness"]), non_color=True)
    links.new(roughness.outputs["Color"], bsdf.inputs["Roughness"])

    metallic = nodes.new("ShaderNodeTexImage")
    metallic.image = load_image(os.path.join(source_dir, spec["metallic"]), non_color=True)
    links.new(metallic.outputs["Color"], bsdf.inputs["Metallic"])

    normal_texture = nodes.new("ShaderNodeTexImage")
    normal_texture.image = load_image(os.path.join(source_dir, spec["normal"]), non_color=True)
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = 0.62
    links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

    emission = nodes.new("ShaderNodeTexImage")
    emission.image = load_image(os.path.join(source_dir, spec["emission"]))
    if "Emission Color" in bsdf.inputs:
        links.new(emission.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 0.15

    material["albedo_texture"] = spec["texture"]
    return material


def apply_transform(obj, scale):
    obj.scale = (scale, scale, scale)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def process(spec):
    clear_scene()
    source_dir = os.path.join(SCRIPT_DIR, spec["folder"])
    source_path = os.path.join(source_dir, spec["source"])
    target_dir = os.path.join(ASSET_ROOT, spec["name"])
    target_path = os.path.join(target_dir, spec["name"] + ".fbx")
    os.makedirs(target_dir, exist_ok=True)

    bpy.ops.import_scene.fbx(filepath=source_path)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError("{} should contain one mesh, found {}".format(spec["name"], len(meshes)))
    model = meshes[0]
    model.name = "SM_Meshy_" + spec["name"].title().replace("_", "")
    material = create_pbr_material(spec)
    model.data.materials.clear()
    model.data.materials.append(material)
    for face in model.data.polygons:
        face.material_index = 0
    apply_transform(model, spec["scale"])

    optimizer = model.modifiers.new("Mobile_Optimization", "DECIMATE")
    optimizer.ratio = spec["ratio"]
    bpy.context.view_layer.objects.active = model
    bpy.ops.object.modifier_apply(modifier=optimizer.name)

    bpy.ops.object.select_all(action="DESELECT")
    model.select_set(True)
    bpy.context.view_layer.objects.active = model
    bpy.ops.export_scene.fbx(
        filepath=target_path,
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
    print("MESHY_MODEL_EXPORT_OK", spec["name"], "faces", len(model.data.polygons), "path", target_path)


for model_spec in SPECS:
    process(model_spec)

bpy.ops.wm.quit_blender()
