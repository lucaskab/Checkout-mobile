"""Create a lightweight 3D customer for the Unity supermarket simulation.

The character is built from clean low-poly meshes with named joint pivots. Unity
uses those pivots for the walk, shelf-pick, payment, and leaving animations at
runtime, which avoids sprite billboards while keeping the mobile asset compact.
"""

import os

import bpy
from mathutils import Vector


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(SCRIPT_DIR, "supermarket_customer.blend")
FBX_PATH = os.path.abspath(
    os.path.join(SCRIPT_DIR, "../../Assets/Resources/Models/Customers/customer_3d.fbx")
)
PREVIEW_PATH = os.path.join(SCRIPT_DIR, "supermarket_customer_preview.png")


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


def material(name, color, roughness=0.65):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return result


def finish_mesh(obj, name, material_value, collection, parent=None, local_location=None, bevel=0.04):
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("Soft_Edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.materials.append(material_value)
    move_to_collection(obj, collection)
    if parent is not None:
        obj.parent = parent
        obj.location = local_location or (0.0, 0.0, 0.0)
    return obj


def add_box(name, local_location, dimensions, material_value, collection, parent=None, bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(location=local_location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    return finish_mesh(obj, name, material_value, collection, parent, local_location, bevel)


def add_cylinder(name, local_location, radius, depth, material_value, collection, parent=None, bevel=0.04):
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=radius, depth=depth, location=local_location)
    return finish_mesh(bpy.context.object, name, material_value, collection, parent, local_location, bevel)


def add_sphere(name, local_location, scale, material_value, collection, parent=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=local_location)
    obj = bpy.context.object
    obj.scale = scale
    return finish_mesh(obj, name, material_value, collection, parent, local_location, 0.0)


def add_empty(name, local_location, parent, collection):
    obj = bpy.data.objects.new(name, None)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = local_location
    obj.empty_display_type = "SPHERE"
    obj.empty_display_size = 0.08
    return obj


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_character():
    models = make_collection("Customer")
    preview = make_collection("Preview")

    skin = material("MAT_CustomerSkin", (0.86, 0.43, 0.25), 0.60)
    hair = material("MAT_CustomerHair", (0.16, 0.055, 0.025), 0.72)
    shirt = material("MAT_CustomerShirt", (0.96, 0.45, 0.16), 0.65)
    pants = material("MAT_CustomerPants", (0.08, 0.22, 0.38), 0.72)
    shoes = material("MAT_CustomerShoes", (0.08, 0.10, 0.13), 0.78)
    basket_material = material("MAT_CustomerBasket", (0.05, 0.43, 0.35), 0.64)
    produce = material("MAT_CustomerProduce", (0.90, 0.20, 0.12), 0.56)

    root = bpy.data.objects.new("Customer3D", None)
    models.objects.link(root)
    root.location = (0.0, 0.0, 0.0)

    body = add_empty("Body", (0.0, 0.0, 1.30), root, models)
    add_box("Torso", (0.0, 0.0, 0.0), (0.72, 0.42, 0.92), shirt, models, body, 0.10)
    add_box("Apron", (0.0, -0.23, -0.02), (0.54, 0.05, 0.64), basket_material, models, body, 0.03)

    head = add_empty("Head", (0.0, 0.0, 2.03), root, models)
    add_sphere("Face", (0.0, 0.0, 0.0), (0.42, 0.38, 0.45), skin, models, head)
    add_sphere("Hair", (0.0, 0.04, 0.31), (0.44, 0.40, 0.25), hair, models, head)
    add_sphere("Nose", (0.0, -0.38, -0.03), (0.06, 0.05, 0.06), skin, models, head)
    for x in (-0.14, 0.14):
        add_sphere("Eye_L" if x < 0 else "Eye_R", (x, -0.36, 0.08), (0.055, 0.04, 0.07), shoes, models, head)

    arm_left = add_empty("Arm_L", (-0.48, 0.0, 1.62), root, models)
    arm_right = add_empty("Arm_R", (0.48, 0.0, 1.62), root, models)
    for name, arm in (("Left", arm_left), ("Right", arm_right)):
        add_cylinder("Arm_" + name, (0.0, 0.0, -0.31), 0.13, 0.62, shirt, models, arm, 0.05)
        add_sphere("Hand_" + name, (0.0, 0.0, -0.67), (0.15, 0.15, 0.15), skin, models, arm)

    leg_left = add_empty("Leg_L", (-0.20, 0.0, 0.90), root, models)
    leg_right = add_empty("Leg_R", (0.20, 0.0, 0.90), root, models)
    for name, leg in (("Left", leg_left), ("Right", leg_right)):
        add_box("Leg_" + name, (0.0, 0.0, -0.34), (0.25, 0.28, 0.68), pants, models, leg, 0.06)
        add_box("Shoe_" + name, (0.0, -0.10, -0.72), (0.30, 0.50, 0.18), shoes, models, leg, 0.06)

    basket = add_empty("Basket", (0.62, -0.08, 0.94), root, models)
    add_box("BasketBody", (0.0, 0.0, 0.0), (0.54, 0.34, 0.34), basket_material, models, basket, 0.07)
    add_box("BasketOpening", (0.0, 0.0, 0.19), (0.42, 0.24, 0.08), shoes, models, basket, 0.03)
    add_cylinder("BasketHandle", (0.0, 0.0, 0.42), 0.035, 0.52, basket_material, models, basket, 0.01)
    bpy.context.object.rotation_euler[0] = 1.5708
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    add_sphere("BasketTomato", (-0.12, -0.04, 0.25), (0.10, 0.10, 0.10), produce, models, basket)
    add_sphere("BasketApple", (0.12, -0.02, 0.25), (0.10, 0.10, 0.10), produce, models, basket)

    bpy.ops.object.camera_add(location=(5.2, -7.0, 4.4))
    camera = bpy.context.object
    camera.name = "Preview_Camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.1
    look_at(camera, (0.0, 0.0, 1.15))
    move_to_collection(camera, preview)
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(-3.0, -4.0, 6.0))
    key = bpy.context.object
    key.data.energy = 850.0
    key.data.shape = "DISK"
    key.data.size = 5.0
    look_at(key, (0.0, 0.0, 1.2))
    move_to_collection(key, preview)
    bpy.ops.object.light_add(type="AREA", location=(4.0, 1.0, 4.0))
    fill = bpy.context.object
    fill.data.energy = 360.0
    fill.data.size = 4.0
    look_at(fill, (0.0, 0.0, 1.2))
    move_to_collection(fill, preview)

    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.render.resolution_x = 640
    bpy.context.scene.render.resolution_y = 640
    bpy.context.scene.render.resolution_percentage = 100
    bpy.context.scene.world.color = (0.055, 0.075, 0.085)
    return root, preview


def export_customer(root, preview):
    bpy.ops.object.select_all(action="DESELECT")
    export_objects = [root] + list(root.children_recursive)
    for obj in export_objects:
        if obj.name in bpy.context.scene.objects:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(
        filepath=FBX_PATH,
        use_selection=True,
        object_types={"MESH", "EMPTY"},
        add_leaf_bones=False,
        bake_anim=False,
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z",
        axis_up="Y",
    )


def main():
    clean_scene()
    root, preview = create_character()
    bpy.context.scene.render.filepath = PREVIEW_PATH
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    export_customer(root, preview)
    if not os.path.exists(FBX_PATH) or os.path.getsize(FBX_PATH) == 0:
        raise RuntimeError("Customer FBX export failed")
    print("CUSTOMER_EXPORT_OK")
    print("FBX path:", FBX_PATH)
    if not bpy.app.background:
        bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    main()
