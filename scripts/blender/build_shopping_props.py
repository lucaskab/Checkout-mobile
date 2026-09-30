"""Shopping cart and hand basket carried by the customers (market colours: chrome wire, navy plastic, gold caps).

Run:  blender -b --factory-startup --python scripts/blender/build_shopping_props.py [-- preview]
Output: unity/CheckoutSimulator/Assets/Resources/CheckoutProps/ShoppingCart.fbx, ShoppingBasket.fbx
        (materials named C_RRGGBB: Unity paints them with the MarketDay/Soft Painted shader)
        with `preview`: PNG renders in scripts/blender/preview_props/.
Empties exported with the meshes tell Unity where the hands go: GripL / GripR on the cart handle, Grip on the
basket handle, Front at the cart nose. "Item_N" meshes are the groceries, shown as the customer shops.
Cart: +Y is forward, origin on the floor under the middle of the handle. Basket: origin at the handle grip.
"""
import math
import random
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'unity/CheckoutSimulator/Assets/Resources/CheckoutProps'
PREVIEW = ROOT / 'scripts/blender/preview_props'
R = math.radians


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c)


_mats = {}


def mat(hex_color, rough=.35, metal=0.0):
    name = 'C_' + hex_color
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(hex_color), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    _mats[name] = m
    return m


CHROME, NAVY, NAVY_D, GOLD, RUBBER, RED, RED_D = 'D9DEE3', '22345E', '16233F', 'E8B04A', '24262B', 'E15533', 'B53A22'
PARTS = []


def reset():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.curves):
        for item in list(block):
            block.remove(item)
    _mats.clear(); PARTS.clear()


def keep(o, m):
    o.data.materials.append(m)
    for p in o.data.polygons:
        p.use_smooth = True
    PARTS.append(o)
    return o


def tube(a, b, r, m, v=8):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2, vertices=v)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return keep(o, m)


def curve_tube(points, r, m):
    """A smooth bent tube (handles), converted to mesh with the rest."""
    cu = bpy.data.curves.new('Tube', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3
    sp = cu.splines.new('NURBS'); sp.points.add(len(points) - 1); sp.use_endpoint_u = True; sp.order_u = 4
    for p_, v in zip(sp.points, points):
        p_.co = (v[0], v[1], v[2], 1)
    o = bpy.data.objects.new('Tube', cu); bpy.context.scene.collection.objects.link(o)
    cu.materials.append(m)
    PARTS.append(o)
    return o


def box(size, loc, m, bev=.01, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=[R(x) for x in rot])
    o = bpy.context.object
    o.scale = [s / 2 for s in size]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bev:
        mod = o.modifiers.new('Bevel', 'BEVEL'); mod.width = min(bev, min(size) * .45); mod.segments = 2
    return keep(o, m)


def cyl(r, depth, loc, m, rot=(0, 0, 0), v=24, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=[R(x) for x in rot], vertices=v)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=depth, location=loc, rotation=[R(x) for x in rot], vertices=v)
    return keep(bpy.context.object, m)


def sphere(r, loc, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=8)
    o = bpy.context.object
    o.scale = scale
    return keep(o, m)


def empty(name, loc):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


def lerp(a, b, t):
    return Vector(a).lerp(Vector(b), t)


def grid(p00, p10, p01, p11, cols, rows, r, m):
    """Wire mesh between four corners (bilinear): `cols` bars one way, `rows` the other."""
    def at(u, v):
        return lerp(lerp(p00, p10, u), lerp(p01, p11, u), v)
    for i in range(1, cols):
        u = i / cols
        tube(at(u, 0), at(u, 1), r, m, 6)
    for j in range(1, rows):
        v = j / rows
        tube(at(0, v), at(1, v), r, m, 6)


def join(name):
    meshes = {}
    for o in PARTS:
        meshes.setdefault(o.data.materials[0].name if o.data.materials else 'none', []).append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in PARTS:
        o.select_set(True)
    bpy.context.view_layer.objects.active = PARTS[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    PARTS.clear()
    return o


GROCERY = ['E15533', 'F2B03D', '2E8CAE', '5DA637', '8B5C9E', 'F07F3C', 'F4E3B5', '45B7D0']


def groceries(spots, seed):
    """One mesh per item (Item_0..N) so Unity can show them one by one."""
    rnd = random.Random(seed)
    for n, (x, y, z) in enumerate(spots):
        c = GROCERY[n % len(GROCERY)]
        kind = rnd.random()
        if kind < .35:
            cyl(.045, .2, (x, y, z + .1), mat(c, .3), v=16)
            cyl(.022, .04, (x, y, z + .22), mat('F4F1EA', .3), v=12)
        elif kind < .7:
            box((.14, .06, .18), (x, y, z + .09), mat(c, .4), .008, rot=(0, 0, rnd.uniform(-25, 25)))
            box((.1, .002, .07), (x, y - .031, z + .1), mat('FFFFFF', .4), 0, rot=(0, 0, 0))
        else:
            sphere(.06, (x, y, z + .06), mat(c, .35), (1, 1, .9))
            sphere(.055, (x + .07, y + .02, z + .06), mat(GROCERY[(n + 3) % len(GROCERY)], .35), (1, 1, .9))
        join(f'Item_{n}')


# ---------------------------------------------------------------- cart
def cart():
    chrome, navy, gold, rubber = mat(CHROME, .22, .9), mat(NAVY, .35), mat(GOLD, .3, .6), mat(RUBBER, .7)
    # Wire basket: a tapered box, narrower and lower at the back where it nests.
    bl, br_ = (-.25, .12, .46), (.25, .12, .46)       # rear bottom
    fl, fr = (-.22, .9, .5), (.22, .9, .5)            # front bottom
    tl, tr = (-.29, .02, .98), (.29, .02, .98)        # rear top
    ftl, ftr = (-.27, 1.0, .98), (.27, 1.0, .98)      # front top
    rim = .012
    for a, b in ((tl, tr), (ftl, ftr), (tl, ftl), (tr, ftr), (bl, br_), (fl, fr), (bl, fl), (br_, fr), (bl, tl), (br_, tr), (fl, ftl), (fr, ftr)):
        tube(a, b, rim, chrome, 10)
    grid(bl, br_, tl, tr, 11, 6, .005, chrome)                 # rear gate
    grid(fl, fr, ftl, ftr, 10, 6, .005, chrome)                # nose
    grid(bl, fl, tl, ftl, 18, 6, .005, chrome)                 # left side
    grid(br_, fr, tr, ftr, 18, 6, .005, chrome)                # right side
    grid(bl, br_, fl, fr, 10, 16, .005, chrome)                # floor
    # Child seat flap folded against the rear gate: navy plastic with a gold badge.
    box((.46, .03, .22), (0, .06, .82), navy, .01, rot=(-12, 0, 0))
    cyl(.045, .012, (0, .04, .83), gold, rot=(90 - 12, 0, 0), v=20)
    # Handle: navy grip bar between two chrome posts, gold end caps.
    for sx in (-1, 1):
        tube((sx * .27, .02, .96), (sx * .27, -.07, 1.06), .014, chrome, 10)
        cyl(.028, .02, (sx * .29, -.07, 1.06), gold, rot=(0, 90, 0), v=16)
    cyl(.024, .56, (0, -.07, 1.06), navy, rot=(0, 90, 0), v=16)
    for sx in (-.18, -.06, .06, .18):
        cyl(.027, .018, (sx, -.07, 1.06), mat(NAVY_D, .4), rot=(0, 90, 0), v=16)
    # Chassis: two tubes under the basket, a lower tray and the post down to the rear casters.
    for sx in (-1, 1):
        tube((sx * .24, .06, .14), (sx * .2, .92, .14), .014, chrome, 10)
        tube((sx * .24, .06, .14), (sx * .26, .1, .46), .012, chrome, 10)
        tube((sx * .2, .92, .14), (sx * .21, .9, .5), .012, chrome, 10)
    grid((-.22, .12, .2), (.22, .12, .2), (-.19, .86, .2), (.19, .86, .2), 8, 10, .004, chrome)
    for a, b in (((-.22, .12, .2), (.22, .12, .2)), ((-.19, .86, .2), (.19, .86, .2)), ((-.22, .12, .2), (-.19, .86, .2)), ((.22, .12, .2), (.19, .86, .2))):
        tube(a, b, .008, chrome, 8)
    # Navy corner bumpers.
    for x, y in ((-.24, .06), (.24, .06), (-.2, .92), (.2, .92)):
        box((.06, .06, .05), (x, y, .14), navy, .012)
    # Swivel casters: fork, grey hub, black tyre.
    for x, y in ((-.24, .06), (.24, .06), (-.2, .92), (.2, .92)):
        cyl(.012, .05, (x, y, .1), chrome, v=10)
        for sy in (-1, 1):
            box((.006, .05, .06), (x + sy * .02, y - .015, .06), chrome, .002)
        cyl(.05, .03, (x, y - .02, .05), rubber, rot=(0, 90, 0), v=20)
        cyl(.022, .034, (x, y - .02, .05), mat('9AA6AA', .3, .8), rot=(0, 90, 0), v=14)
    body = join('Cart')
    groceries([(-.12, .3, .47), (.1, .35, .47), (-.1, .6, .5), (.1, .62, .5), (0, .45, .6), (-.12, .8, .5), (.12, .8, .5), (0, .75, .62)], 7)
    empty('GripL', (-.2, -.07, 1.06)); empty('GripR', (.2, -.07, 1.06)); empty('Front', (0, 1.0, .5))
    return body


# ---------------------------------------------------------------- hand basket
def basket():
    red, red_d, navy, gold = mat(RED, .35), mat(RED_D, .4), mat(NAVY, .35), mat(GOLD, .3, .6)
    # Origin at the grip (handles raised), the basket hanging below it.
    top, bottom = -.28, -.52
    tw, td, bw, bd = .23, .16, .19, .12
    # Floor and a thick top rim.
    box((bw * 2, bd * 2, .02), (0, 0, bottom + .01), red_d, .01)
    for (a, b) in (((-tw, -td), (tw, -td)), ((tw, -td), (tw, td)), ((tw, td), (-tw, td)), ((-tw, td), (-tw, -td))):
        tube((a[0], a[1], top), (b[0], b[1], top), .014, red, 10)
    # Sides: vertical ribs with a middle band, like the moulded crates in shops.
    def side(p0, p1, q0, q1, n):
        for i in range(n + 1):
            t = i / n
            a = lerp(p0, p1, t); b = lerp(q0, q1, t)
            box((.016, .016, (a - b).length), (a + b) / 2, red, .004, rot=(0, 0, 0)) if False else tube(b, a, .009, red, 6)
        tube(lerp(q0, p0, .45), lerp(q1, p1, .45), .008, red, 6)
        tube(lerp(q0, p0, .12), lerp(q1, p1, .12), .008, red, 6)
    side((-tw, -td, top), (tw, -td, top), (-bw, -bd, bottom), (bw, -bd, bottom), 14)
    side((-tw, td, top), (tw, td, top), (-bw, bd, bottom), (bw, bd, bottom), 14)
    side((-tw, -td, top), (-tw, td, top), (-bw, -bd, bottom), (-bw, bd, bottom), 9)
    side((tw, -td, top), (tw, td, top), (bw, -bd, bottom), (bw, bd, bottom), 9)
    # A white label plate with the market's gold M.
    box((.12, .004, .05), (0, -td - .006, top - .06), mat('FFF7EA', .4), .006)
    box((.03, .002, .03), (0, -td - .01, top - .06), gold, .004)
    # Two navy handles raised and meeting at the grip.
    for sy in (-1, 1):
        pts = []
        for k in range(13):
            a = k / 12 * math.pi
            pts.append(Vector((math.cos(a) * -tw * .92, sy * td * .55 * math.sin(a) ** 3, top + math.sin(a) * .27)))
        curve_tube(pts, .012, navy)
        for sx in (-1, 1):
            cyl(.018, .01, (sx * tw * .92, sy * td * .02, top), gold, rot=(90, 0, 0), v=12)
    cyl(.02, .12, (0, 0, top + .27), navy, rot=(0, 90, 0), v=14)
    body = join('Basket')
    groceries([(-.1, -.05, bottom + .02), (.08, .03, bottom + .02), (-.02, .06, bottom + .02), (.12, -.06, bottom + .02)], 3)
    empty('Grip', (0, 0, top + .27))
    return body


def preview(name, view_yaw):
    sc = bpy.context.scene
    objs = [o for o in sc.objects if o.type == 'MESH']
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    center = (lo + hi) / 2
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = (hi - lo).length * 1.05
    e, y = R(24), R(view_yaw)
    cam.location = center + Vector((math.sin(y) * math.cos(e), -math.cos(y) * math.cos(e), math.sin(e))) * 10
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for n, en, loc in (('Key', 600, (-3, -4, 5)), ('Fill', 250, (4, -3, 2)), ('Rim', 350, (1, 5, 4))):
        l = bpy.data.lights.new(n, 'AREA'); l.energy = en; l.size = 4
        lo_ = bpy.data.objects.new(n, l); sc.collection.objects.link(lo_); lo_.location = center + Vector(loc)
        lo_.rotation_euler = (center - lo_.location).to_track_quat('-Z', 'Y').to_euler()
    world = sc.world or bpy.data.worlds.new('W'); sc.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.96, .93, .87, 1)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = 640
    sc.view_settings.view_transform = 'AgX'
    PREVIEW.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(PREVIEW / f'{name}_{view_yaw}.png')
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


def export(name):
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT / (name + '.fbx')), use_selection=True, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                             object_types={'MESH', 'EMPTY'}, bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False)


def main(args):
    for name, build in (('ShoppingCart', cart), ('ShoppingBasket', basket)):
        reset()
        build()
        if 'preview' in args:
            for yaw in (-35, 150):
                preview(name, yaw)
        export(name)
        print('SHOPPING_PROP', name, flush=True)


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
