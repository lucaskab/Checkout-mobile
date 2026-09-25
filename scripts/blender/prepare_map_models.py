"""Convert supplied static GLBs to textured FBX assets for the Unity map."""
import sys
import shutil
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'unity/CheckoutSimulator/Assets/Art/Models/MapModels'
SOURCES = ROOT / 'unity/CheckoutSimulator/ArtSource/MapModels'
MODELS = {'DeliveryTruck': 'delivery truck', 'DisplayShelf': 'display shelf',
          'FishDeliveryTruck': 'fish delivery truck', 'IceCreamTruck': 'ice cream truck',
          'WineRack': 'wine rack', 'Warehouse': 'warehouse',
          'CheckoutCounter': 'checkout counter', 'MarketStructure': 'stylized architectural 3d model (1).glb',
          'ButcherDisplay': 'butcher shop display', 'CheeseDisplay': 'cheese display',
          'SeafoodCounter': 'seafood market counter', 'Cow': 'cow',
          'FlowerPlanter': 'flower planter', 'StylizedTree': 'stylized tree',
          'FruitMarketStand': 'fruit market stand', 'VegetableCrate': 'vegetable crate',
          'CardboardBox': 'cardboard box', 'CuteHouse': 'cute house',
          'CartoonCar': 'cartoon car', 'StylizedBuilding': 'stylized building',
          'StylizedCar': 'stylized car', 'StylizedHouse': 'stylized house', 'ToyVan': 'toy van', 'BeverageShelf':'beverage shelf', 'GroceryShelf':'grocery shelf', 'GroceryDisplay':'grocery display', 'CheckoutWoman':'cartoon character checkout', 'GirlCustomer':'stylized girl customer', 'ConstructionPlatform':'construction platform', 'PickupBed':'pickup bed', 'PlaygroundForge':'playground forge', 'Sandbox':'sandbox', 'BakeryConstruction':'bakery construction', 'CheeseryConstruction':'cheesery construction', 'ButcheryConstruction':'butchery construction', 'FishConstruction':'fish construction'}
SOURCES.mkdir(parents=True, exist_ok=True)
MODELS.update({'Hospital': 'hospital building', 'Pharmacy': 'pharmacy', 'Gym': 'gym building'})
MODELS.update({'AmusementPark': 'amusement park', 'TrafficLight': 'traffic light'})
MODELS.update({'Refrigerator': 'refrigerator', 'IceCreamFreezer': 'ice cream freezer'})
selected = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(MODELS)
for name in selected:
    source = MODELS[name]
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    path = SOURCES / (name + '.glb')
    shutil.copy2(Path.home() / 'Downloads' / (source if source.endswith('.glb') else source + ' 3d model.glb'), path)
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    folder = ASSETS / name
    folder.mkdir(parents=True, exist_ok=True)
    for obj in meshes:
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes:
                continue
            mat.name = name + 'Material'
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    image = node.image
                    suffix = 'BaseColor' if image.colorspace_settings.name == 'sRGB' else str(image.name).split('_')[-1]
                    image.filepath_raw = str(folder / (name + '_' + suffix + '.png'))
                    image.file_format = 'PNG'
                    image.save()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes: obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.export_scene.fbx(filepath=str(folder / (name + '.fbx')), use_selection=True,
        object_types={'MESH'}, axis_forward='-Z', axis_up='Y', bake_anim=False,
        path_mode='STRIP', use_mesh_modifiers=True)
    # Isolated model preview, showing the front and side.
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low + high) * .5
    bpy.ops.object.camera_add(location=center + Vector((1.5, -2, 1.2)))
    camera = bpy.context.object
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 1.65
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type='AREA', location=(1, -2, 3))
    bpy.context.object.data.energy = 250
    bpy.context.object.data.shape = 'DISK'
    bpy.context.object.data.size = 4
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.world.color = (.4, .4, .4)
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.filepath = '/tmp/checkout-' + name + '.png'
    bpy.ops.render.render(write_still=True)
    print('MAP_MODEL', name, 'bounds', list(low), list(high), flush=True)
