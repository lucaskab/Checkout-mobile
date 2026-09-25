"""Build simple stylized props (self-checkout kiosk, rain umbrella, road works) as FBX for the Unity map.

Run: Blender -b --python scripts/blender/build_props.py -- SelfCheckout
Colors are assigned in Unity by material name (Teal, Cream, Orange, Yellow, Dark, Metal, Screen, Lamp, Red,
White, Asphalt, Dirt, Sand, Stone).
"""
import sys
import math
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'unity/CheckoutSimulator/Assets/Art/Models/MapModels'
PREVIEW = {'Teal': (.10, .42, .38), 'Cream': (.90, .78, .55), 'Orange': (.85, .30, .06), 'Dark': (.03, .035, .04),
           'Metal': (.55, .58, .60), 'Screen': (.35, .80, .90), 'Lamp': (.20, .85, .30), 'Red': (.95, .10, .08),
           'White': (.9, .9, .88), 'Asphalt': (.07, .07, .075), 'Dirt': (.33, .20, .10), 'Sand': (.75, .58, .32),
           'Yellow': (.95, .70, .05), 'Stone': (.45, .44, .42)}


def material(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*PREVIEW[name], 1)
    mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*PREVIEW[name], 1)
    return mat


def box(name, size, location, mat, bevel=.02, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=[math.radians(a) for a in rotation])
    obj = bpy.context.object
    obj.name = name
    obj.scale = [s / 2 for s in size]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        mod = obj.modifiers.new('Bevel', 'BEVEL')
        mod.width = min(bevel, min(size) * .45)
        mod.segments = 3
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.materials.append(material(mat))
    return obj


def cylinder(name, radius, depth, location, mat, rotation=(0, 0, 0), vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=location, vertices=vertices,
                                        rotation=[math.radians(a) for a in rotation])
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material(mat))
    bpy.ops.object.shade_smooth()
    return obj


def self_checkout():
    # Front (customer side) faces -Y. Height ~1.8 m to the status lamp.
    box('Cabinet', (.62, .50, .80), (0, 0, .42), 'Teal', .05)
    box('Kick', (.64, .52, .10), (0, 0, .07), 'Orange', .03)
    box('Top', (.72, .58, .06), (0, 0, .85), 'Cream', .025)
    box('ScannerGlass', (.30, .26, .02), (-.10, -.06, .885), 'Dark', .006)
    box('ScanLine', (.26, .015, .005), (-.10, -.06, .897), 'Red', 0)
    box('Door', (.44, .02, .46), (0, -.255, .45), 'Cream', .015)
    box('Handle', (.14, .03, .03), (0, -.27, .60), 'Metal', .01)
    # Bagging shelf on the right, with a bag on it.
    box('BagShelf', (.44, .46, .04), (.60, 0, .78), 'Metal', .012)
    cylinder('BagPost', .025, .74, (.60, .15, .40), 'Metal')
    box('BagFoot', (.30, .30, .03), (.60, .05, .02), 'Metal', .01)
    box('Bag', (.24, .16, .26), (.60, 0, .93), 'White', .03)
    box('BagFrame', (.36, .02, .02), (.60, -.20, 1.10), 'Metal', .008)
    for x in (.43, .77):
        cylinder('BagBar', .012, .32, (x, -.20, .95), 'Metal', vertices=8)
    # Screen on a neck, tilted towards the customer.
    cylinder('Neck', .035, .32, (0, .17, 1.03), 'Metal')
    box('ScreenBody', (.48, .06, .34), (0, .14, 1.30), 'Teal', .025, rotation=(-18, 0, 0))
    box('ScreenFace', (.40, .01, .27), (0, .104, 1.31), 'Screen', 0, rotation=(-18, 0, 0))
    box('Badge', (.22, .03, .07), (0, .17, 1.52), 'Orange', .015)
    # Card terminal.
    box('Terminal', (.10, .07, .03), (.20, -.14, .91), 'Dark', .01, rotation=(-20, 0, 0))
    box('TerminalKeys', (.07, .045, .005), (.20, -.146, .928), 'Metal', 0, rotation=(-20, 0, 0))
    # Status lamp pole.
    cylinder('LampPole', .018, .95, (-.27, .20, 1.33), 'Metal', vertices=8)
    cylinder('LampBase', .045, .04, (-.27, .20, 1.80), 'Dark')
    cylinder('Lamp', .05, .09, (-.27, .20, 1.86), 'Lamp')


def umbrella():
    # Origin is the grip; the canopy rim sits .93 above it so a hand at chin height clears the (large) head.
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=.66, radius2=0, depth=.27, location=(0, 0, 1.065),
                                    end_fill_type='NOTHING')
    canopy = bpy.context.object
    canopy.name = 'Canopy'
    panels = ['Orange', 'Cream', 'Teal', 'Yellow']
    for name in panels:
        canopy.data.materials.append(material(name))
    mod = canopy.modifiers.new('Solidify', 'SOLIDIFY')
    mod.thickness = .012
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for poly in canopy.data.polygons:
        angle = math.atan2(poly.center.y, poly.center.x) % (2 * math.pi)
        poly.material_index = int(angle / (math.pi / 4)) % len(panels)
    bpy.ops.object.shade_flat()
    for i in range(8):
        angle = i * math.pi / 4
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.024, segments=8, ring_count=6,
                                             location=(.66 * math.cos(angle), .66 * math.sin(angle), .93))
        bpy.context.object.data.materials.append(material('Dark'))
    cylinder('Finial', .022, .07, (0, 0, 1.23), 'Dark', vertices=8)
    cylinder('Shaft', .013, 1.22, (0, 0, .59), 'Metal', vertices=8)
    cylinder('Grip', .022, .15, (0, 0, .04), 'Dark', vertices=10)
    # J hook under the grip.
    bpy.ops.mesh.primitive_torus_add(major_radius=.055, minor_radius=.017, major_segments=16, minor_segments=6,
                                     location=(.055, 0, -.035), rotation=(math.radians(90), 0, 0))
    hook = bpy.context.object
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for vertex in hook.data.vertices:
        vertex.select = vertex.co.z > .004
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='VERT')
    bpy.ops.object.mode_set(mode='OBJECT')
    hook.data.materials.append(material('Dark'))


def cone(location):
    x, y = location
    box('ConeFoot', (.30, .30, .035), (x, y, .018), 'Dark', .01)
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=.12, radius2=.025, depth=.5, location=(x, y, .28))
    bpy.context.object.data.materials.append(material('Orange'))
    bpy.ops.object.shade_smooth()
    cylinder('ConeBand', .082, .07, (x, y, .30), 'White', vertices=12)


def barricade(x):
    # A-frame across the lane, facing the traffic along X.
    for y in (-.55, .55):
        for lean in (-1, 1):
            box('BarricadeLeg', (.05, .05, .95), (x + lean * .12, y, .46), 'Dark', .01, rotation=(0, lean * 14, 0))
    for z in (.78, .48):
        for i in range(6):
            box('BarricadeBoard', (.06, .2, .18), (x, -.5 + i * .2, z), 'Red' if i % 2 == 0 else 'White', .01)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.07, segments=10, ring_count=6, location=(x, .55, .98))
    bpy.context.object.data.materials.append(material('Yellow'))
    box('LampClip', (.06, .06, .08), (x, .55, .9), 'Dark', .01)


def road_works():
    # Origin at the road surface, X along the street, +Y towards the curb. Footprint ~5.4 x 1.4 m.
    for y in (-.62, .62):
        box('CutEdge', (4.3, .08, .03), (0, y, .015), 'Asphalt', .005)
    for x in (-2.11, 2.11):
        box('CutEdge', (.08, 1.32, .03), (x, 0, .015), 'Asphalt', .005)
    box('FreshPatch', (1.3, 1.16, .025), (-1.4, 0, .013), 'Asphalt', .005)
    box('Trench', (2.6, .9, .03), (.65, .05, .016), 'Dirt', .01)
    box('TrenchHole', (1.9, .42, .01), (.75, .05, .034), 'Dark', .004)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=14, ring_count=8, location=(1.75, .42, 0))
    mound = bpy.context.object
    mound.scale = (.55, .32, .28)
    mound.data.materials.append(material('Dirt'))
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=.38, radius2=.05, depth=.34, location=(-1.45, .3, .17))
    bpy.context.object.data.materials.append(material('Sand'))
    bpy.ops.object.shade_smooth()
    # Concrete pipe waiting to go into the trench.
    cylinder('Pipe', .2, .9, (-.35, .32, .2), 'Stone', rotation=(0, 90, 0), vertices=16)
    cylinder('PipeHole', .13, .92, (-.35, .32, .2), 'Dark', rotation=(0, 90, 0), vertices=16)
    # Wheelbarrow with a shovel stuck in the sand.
    box('BarrowTray', (.62, .42, .2), (-.8, -.25, .4), 'Teal', .03, rotation=(0, -6, 0))
    box('BarrowSand', (.5, .32, .04), (-.8, -.25, .5), 'Sand', .01, rotation=(0, -6, 0))
    cylinder('BarrowWheel', .13, .07, (-1.15, -.25, .13), 'Dark', rotation=(90, 0, 0))
    for y in (-.42, -.08):
        box('BarrowHandle', (.75, .035, .035), (-.5, y, .38), 'Metal', .008, rotation=(0, -12, 0))
        box('BarrowLeg', (.035, .035, .3), (-.62, y, .16), 'Metal', .008)
    box('ShovelHandle', (.035, .035, .9), (-1.4, .3, .6), 'Sand', .01, rotation=(18, 0, 10))
    box('ShovelBlade', (.2, .03, .24), (-1.33, .15, .2), 'Metal', .008, rotation=(18, 0, 10))
    for x in (-1.8, -.6, .6, 1.8):
        cone((x, -.72))
    barricade(-2.5)
    barricade(2.5)
    # Work ahead sign for the westbound traffic coming from +X.
    cylinder('SignPost', .02, 1.0, (2.95, .5, .5), 'Metal', vertices=8)
    cylinder('SignBorder', .34, .025, (2.95, .5, 1.12), 'Red', rotation=(90, 0, 90), vertices=3)
    cylinder('SignFace', .26, .03, (2.95, .5, 1.1), 'White', rotation=(90, 0, 90), vertices=3)
    box('SignWorker', (.035, .07, .14), (2.93, .5, 1.1), 'Dark', .01)
    box('SignFoot', (.4, .4, .05), (2.95, .5, .025), 'Dark', .01)


BUILDERS = {'SelfCheckout': self_checkout, 'Umbrella': umbrella, 'RoadWorks': road_works}


def export(name):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    BUILDERS[name]()
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    bpy.context.object.name = name
    folder = ASSETS / name
    folder.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(folder / (name + '.fbx')), use_selection=True, object_types={'MESH'},
                             axis_forward='-Z', axis_up='Y', bake_anim=False, path_mode='STRIP',
                             use_mesh_modifiers=True)
    preview(name)


def preview(name):
    bpy.ops.object.camera_add(location=(2.2, -2.8, 2.2))
    camera = bpy.context.object
    target = bpy.context.scene.objects[name].location.copy()
    target.z += min(.8, bpy.context.scene.objects[name].dimensions.z / 2)
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(2.6, max(bpy.context.scene.objects[name].dimensions) * 1.1)
    scene = bpy.context.scene
    scene.camera = camera
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 5), rotation=(math.radians(40), math.radians(20), 0))
    bpy.context.object.data.energy = 4
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items} else 'BLENDER_EEVEE'
    scene.world.color = (.5, .5, .5)
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.filepath = '/tmp/prop-' + name + '.png'
    bpy.ops.render.render(write_still=True)


for prop in (sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else list(BUILDERS)):
    export(prop)
    print('PROP_BUILT', prop, flush=True)
