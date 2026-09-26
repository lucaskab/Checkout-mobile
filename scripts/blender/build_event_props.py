"""Blender-authored props for the 18 market events (everything except rain and street works).

Run from Unity (Checkout > Eventos > 1. Gerar props no Blender) or directly:
    blender -b --python scripts/blender/build_event_props.py [-- PropName ...]

Every prop is exported as one FBX to Assets/Resources/EventProps/<Name>.fbx.
Material naming contract with CheckoutEventAssets.Model():
    C_RRGGBB  -> shared "MarketDay/Soft Painted" colour with the warm ink contour
    T_<file>  -> the same shader using Resources/EventProps/Textures/<file>.png
Origin sits on the ground, +Z up, the readable front faces -Y (towards the camera).
"""
import sys
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'unity/CheckoutSimulator/Assets/Resources/EventProps'
PREVIEWS = ROOT / 'unity/CheckoutSimulator/ArtSource/EventProps/Previews'

# Project palette (ArtSource/palette.json) plus a few event accents.
P = dict(cream='F4DFA4', white='FFF1D1', paper='FFF8E6', wood='AB6537', woodLight='D69C53', woodDark='643F2B',
         teal='188F86', tealLight='54C1AB', tealDark='17655D', blue='45B7D0', red='D74A3C', salmon='F18962',
         pink='F6AC94', rose='E67C98', orange='EC862E', yellow='F4BA42', gold='E9B345', goldLight='FFD97A',
         green='5A9D33', grass='83B749', leaf='468237', purple='A96985', violet='8E5BB5', black='384444',
         dark='2F3A40', metal='A3B9AD', steel='C9D6D2', glass='B4EBE2', bread='DB953D', breadLight='F4C16C',
         skin='E7AC71', road='73776C', coffee='6B4430', magenta='D5487E', sky='8FD3F0', lime='B5D84A', brick='BB5D35')


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c)


def mat(key):
    """key is a palette name, a raw hex, or 'T_<texture>'."""
    if key.startswith('T_'):
        name, col = key, (1, 1, 1)
    else:
        hx = P.get(key, key).upper()
        name, col = 'C_' + hx, srgb(hx)
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*col, 1)
        if not m.node_tree:
            m.use_nodes = True
        bsdf = m.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (*col, 1)
        bsdf.inputs['Roughness'].default_value = .8
        if key.startswith('T_'):
            tex = m.node_tree.nodes.new('ShaderNodeTexImage')
            path = ROOT / 'unity/CheckoutSimulator/ArtSource/EventProps/SignTextures' / (key[2:] + '.png')
            if path.exists():
                tex.image = bpy.data.images.load(str(path))
                m.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    return m


def _finish(obj, key, smooth=False):
    obj.data.materials.append(mat(key))
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def _rad(r):
    return [math.radians(a) for a in r]


def bevel(obj, width, segments=3):
    if width <= 0:
        return obj
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new('Bevel', 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def box(size, loc, key, bev=.03, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=_rad(rot))
    o = bpy.context.object
    o.scale = [s / 2 for s in size]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(o, min(bev, min(size) * .45))
    return _finish(o, key)


def cyl(r, depth, loc, key, rot=(0, 0, 0), v=20, bev=0, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=_rad(rot), vertices=v)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=depth, location=loc, rotation=_rad(rot), vertices=v)
    o = bpy.context.object
    bevel(o, bev, 2)
    return _finish(o, key, smooth=v > 10)


def ball(r, loc, key, scale=(1, 1, 1), seg=18, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=rings)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, key, smooth=True)


def torus(R, r, loc, key, rot=(0, 0, 0), maj=28, mino=10):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=_rad(rot),
                                     major_segments=maj, minor_segments=mino)
    return _finish(bpy.context.object, key, smooth=True)


def plane(w, h, loc, key, rot=(90, 0, 0)):
    """Vertical sign face (UV 0-1) facing -Y by default."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=_rad(rot))
    o = bpy.context.object
    o.scale = (w, h, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, key)


def bar(a, b, r, key, v=10):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2, vertices=v)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return _finish(o, key, smooth=True)


def extrude_shape(points, depth, loc, key, rot=(90, 0, 0), bev=.02):
    """Extruded flat outline (x, y points) — used for icons such as hearts, stars, bolts."""
    mesh = bpy.data.meshes.new('shape')
    bm = bmesh.new()
    verts = [bm.verts.new((x, y, -depth / 2)) for x, y in points]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    for v in ext['geom']:
        if isinstance(v, bmesh.types.BMVert):
            v.co.z += depth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new('shape', mesh)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = _rad(rot)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bevel(o, bev, 2)
    return _finish(o, key)


def heart_pts(s=1, n=40):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * s / 17, y * s / 17))
    return pts


def star_pts(R=1, r=.45, n=5):
    return [((R if i % 2 == 0 else r) * math.sin(i * math.pi / n), (R if i % 2 == 0 else r) * math.cos(i * math.pi / n))
            for i in range(2 * n)]


def ring_pts(R, n=32):
    return [(R * math.cos(2 * math.pi * i / n), R * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ----------------------------------------------------------------------------------------------- shared pieces

def shopping_cart(x=0, y=0, full=False, rot=0):
    """~1 m tall cart, handle at -Y... built around (x, y)."""
    g = []
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def p(px, py, pz):
        return (x + px * c - py * s, y + px * s + py * c, pz)
    # Basket: floor + wire walls (as slim framed panels with bars)
    g.append(box((.56, .82, .05), p(0, 0, .52), 'steel', .015, rot=(0, 0, rot)))
    for side in (-1, 1):
        g.append(box((.03, .86, .03), p(side * .31, 0, .95), 'steel', .01, rot=(0, 0, rot)))
        for i in range(6):
            yy = -.4 + i * .16
            g.append(bar(p(side * .28, yy, .54), p(side * .31, yy, .95), .012, 'steel'))
    for end in (-1, 1):
        g.append(box((.64, .03, .03), p(0, end * .43, .95), 'steel', .01, rot=(0, 0, rot)))
        for i in range(5):
            xx = -.24 + i * .12
            g.append(bar(p(xx, end * .41, .54), p(xx, end * .43, .95), .012, 'steel'))
    # Handle with the market's teal grip
    g.append(bar(p(-.3, .45, .95), p(-.3, .62, 1.12), .018, 'steel'))
    g.append(bar(p(.3, .45, .95), p(.3, .62, 1.12), .018, 'steel'))
    g.append(bar(p(-.34, .62, 1.12), p(.34, .62, 1.12), .035, 'teal', 12))
    # Chassis + wheels
    for side in (-1, 1):
        g.append(bar(p(side * .22, -.38, .12), p(side * .26, .42, .5), .018, 'steel'))
        g.append(bar(p(side * .22, -.38, .12), p(side * .22, -.38, .5), .018, 'steel'))
    g.append(box((.48, .7, .03), p(0, 0, .16), 'steel', .01, rot=(0, 0, rot)))
    for wx in (-.2, .2):
        for wy in (-.34, .36):
            g.append(cyl(.06, .04, p(wx, wy, .06), 'dark', rot=(0, 90, rot), v=14))
    if full:
        items = [((-.14, -.22, .66), (.2, .16, .26), 'orange'), ((.1, -.2, .7), (.18, .18, .34), 'red'),
                 ((-.12, .08, .68), (.22, .2, .3), 'yellow'), ((.12, .1, .64), (.2, .22, .22), 'teal'),
                 ((0, .3, .66), (.34, .14, .26), 'cream')]
        for (px, py, pz), size, col in items:
            g.append(box(size, p(px, py, pz), col, .03, rot=(0, 0, rot)))
        g.append(ball(.1, p(.13, -.18, .9), 'green'))
        g.append(cyl(.05, .3, p(-.05, .28, .88), 'breadLight', rot=(0, 80, rot), v=12))
        g.append(ball(.08, p(-.14, .02, .9), 'red'))
    return g


def coin(loc, r=.32, rot=(90, 0, 0)):
    cyl(r, r * .22, loc, 'gold', rot=rot, v=28, bev=.02)
    x, y, z = loc
    for side in (-1, 1):
        plane(r * 1.38, r * 1.38, (x, y + side * (r * .115), z), 'T_coin_face', rot=(90, 0, 0 if side < 0 else 180))


def a_frame_sign(tex, h=1.1, w=.7, face_key=None, frame='teal'):
    ang = 12
    for side in (-1, 1):
        box((w + .08, .05, h), (0, side * .12, h / 2), frame, .02, rot=(side * ang, 0, 0))
    plane(w - .06, h - .16, (0, -.155, h / 2 + .01), tex, rot=(90 - ang, 0, 0))
    for side in (-1, 1):
        bar((side * w * .4, -.2, .03), (side * w * .4, .2, .03), .012, 'dark')


def barrel(loc, key='red', h=.9, r=.3):
    x, y, z = loc
    cyl(r, h, (x, y, z + h / 2), key, v=20, bev=.02)
    for dz in (.12, h - .12):
        torus(r + .005, .02, (x, y, z + dz), 'dark')
    cyl(r * .9, .02, (x, y, z + h + .005), 'dark', v=20)


def potted_flowers(x, y, key='rose', pot='brick', s=1.0):
    cyl(.28 * s, .42 * s, (x, y, .21 * s), pot, v=16, r2=.22 * s)
    torus(.28 * s, .035 * s, (x, y, .42 * s), pot, maj=20, mino=8)
    cyl(.25 * s, .04 * s, (x, y, .4 * s), 'woodDark', v=16)
    for i in range(7):
        a = i * 2 * math.pi / 7
        rr = .15 * s if i else 0
        px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
        bar((px, py, .4 * s), (px * 1.0 + math.cos(a) * .05 * s, py + math.sin(a) * .05 * s, (.72 + (i % 3) * .08) * s), .015 * s, 'leaf', 6)
        ball(.09 * s, (px + math.cos(a) * .05 * s, py + math.sin(a) * .05 * s, (.76 + (i % 3) * .08) * s),
             [key, 'yellow', 'white'][i % 3], seg=10, rings=6)
    for i in range(4):
        a = i * math.pi / 2 + .4
        ball(.1 * s, (x + math.cos(a) * .17 * s, y + math.sin(a) * .17 * s, .5 * s), 'leaf', (1, 1, .5), 8, 6)


def bunting(a, b, sag=.3, n=10, colors=('red', 'yellow', 'teal', 'white', 'orange')):
    a, b = Vector(a), Vector(b)
    prev = a
    for i in range(1, n * 2 + 1):
        t = i / (n * 2)
        pnt = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))
        bar(prev, pnt, .008, 'dark', 6)
        prev = pnt
    d = (b - a)
    yaw = math.degrees(math.atan2(d.y, d.x))
    for i in range(n):
        t = (i + .5) / n
        pnt = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))
        extrude_shape([(-.11, 0), (.11, 0), (0, -.24)], .015, pnt, colors[i % len(colors)], rot=(90, 0, yaw), bev=.004)


def balloon(loc, key, r=.3, string=1.4):
    x, y, z = loc
    ball(r, (x, y, z), key, (1, 1, 1.18), 20, 14)
    cyl(r * .16, r * .2, (x, y, z - r * 1.2), key, v=10, r2=r * .05)
    bar((x, y, z - r * 1.28), (x + .05, y, z - r * 1.28 - string), .007, 'white', 6)


def person_free_stool(x, y):
    cyl(.18, .04, (x, y, .5), 'woodLight', v=16)
    for a in range(3):
        ang = a * 2 * math.pi / 3
        bar((x + math.cos(ang) * .12, y + math.sin(ang) * .12, .48), (x + math.cos(ang) * .2, y + math.sin(ang) * .2, 0), .015, 'dark')


# ----------------------------------------------------------------------------------------------- event props

def cart_empty():
    shopping_cart()


def cart_full():
    shopping_cart(full=True)


def queue_stanchions():
    """Retractable-belt stanchions forming a short queue lane, 3 m long."""
    posts = [(-1.5, -.45), (0, -.45), (1.5, -.45), (-1.5, .45), (0, .45), (1.5, .45)]
    for x, y in posts:
        cyl(.17, .05, (x, y, .025), 'dark', v=20, bev=.01)
        cyl(.035, .95, (x, y, .5), 'steel', v=12)
        cyl(.055, .06, (x, y, .97), 'dark', v=16)
    for y in (-.45, .45):
        for x in (-1.5, 0):
            box((1.5, .015, .07), (x + .75, y, .88), 'red', .005)


def coin_stack():
    for i, (x, y, n) in enumerate(((0, 0, 6), (.36, .12, 4), (-.3, .2, 3))):
        for k in range(n):
            cyl(.16, .05, (x, y, .03 + k * .052), 'gold' if k % 2 == 0 else 'goldLight', v=24, bev=.008)


def gold_coin():
    coin((0, 0, 0), .34)


def money_bag():
    ball(.42, (0, 0, .42), 'woodLight', (1, 1, .92), 20, 14)
    cyl(.14, .16, (0, 0, .86), 'woodLight', v=16, r2=.2)
    torus(.15, .04, (0, 0, .82), 'wood')
    plane(.36, .36, (0, -.415, .42), 'T_coin_badge', rot=(90, 0, 0))


def ring_light():
    """Creator's tripod with ring light and phone, ~2 m tall."""
    for a in range(3):
        ang = math.radians(90 + a * 120)
        bar((0, 0, 1.0), (math.cos(ang) * .45, math.sin(ang) * .45, 0), .02, 'dark')
        ball(.03, (math.cos(ang) * .45, math.sin(ang) * .45, .02), 'dark', seg=8, rings=6)
    cyl(.035, .1, (0, 0, 1.0), 'dark', v=12)
    bar((0, 0, 1.0), (0, 0, 1.75), .022, 'steel')
    torus(.34, .06, (0, 0, 2.05), 'white', rot=(90, 0, 0), maj=40, mino=12)
    torus(.34, .03, (0, .045, 2.05), 'steel', rot=(90, 0, 0), maj=40, mino=8)
    bar((0, 0, 1.72), (0, 0, 2.05), .018, 'steel')
    box((.19, .025, .36), (0, -.07, 2.05), 'dark', .02)
    plane(.16, .32, (0, -.084, 2.05), 'T_phone_live', rot=(90, 0, 0))


def creator_backdrop():
    """Pastel photo backdrop with LIVE banner and floor mat — the creator's corner."""
    box((2.6, 1.8, .04), (0, 0, .02), 'pink', .01)
    for x in (-1.2, 1.2):
        bar((x, .78, 0), (x, .78, 2.4), .03, 'woodLight')
    box((2.5, .05, 1.9), (0, .8, 1.35), 'rose', .02)
    plane(2.1, 1.3, (0, .77, 1.45), 'T_creator_banner', rot=(90, 0, 0))
    for i in range(9):
        balloon((-1.1 + i * .27, .72, 2.35 + math.sin(i) * .08), ['pink', 'white', 'rose', 'gold'][i % 4], .14, .05)
    potted_flowers(-1.05, .45, 'rose', 'white', .8)
    potted_flowers(1.05, .45, 'yellow', 'white', .8)


def heart():
    extrude_shape(heart_pts(.42), .16, (0, 0, 0), 'rose', rot=(90, 0, 0), bev=.04)
    extrude_shape([(x * .5 - .13, y * .5 + .1) for x, y in heart_pts(.42)], .02, (0, -.09, 0), 'pink', rot=(90, 0, 0), bev=.005)


def fair_stall(canvas='T_awning_red'):
    """Street-fair tent: wooden counter with produce crates and a striped canvas roof (3.2 x 1.8)."""
    w, d = 3.0, 1.6
    for x in (-w / 2, w / 2):
        for y in (-d / 2, d / 2):
            bar((x, y, 0), (x, y, 2.35), .045, 'woodLight', 8)
    # Pitched canvas roof built from two textured planes (UV 0-1 carries the stripes)
    for side in (-1, 1):
        plane(w + .25, d / 2 + .25, (0, side * d / 4, 2.55), canvas, rot=(-side * 18, 0, 0))
    # Scalloped valance on the front
    for i in range(12):
        cyl(.13, .02, (-w / 2 + .13 + i * (w / 12), -d / 2 - .1, 2.28), ['red', 'white'][i % 2] if 'red' in canvas else ['teal', 'white'][i % 2], rot=(90, 0, 0), v=16)
    box((w - .1, .06, .22), (0, -d / 2 - .08, 2.4), 'white', .02)
    plane(w - .4, .18, (0, -d / 2 - .115, 2.4), 'T_fair_sign', rot=(90, 0, 0))
    # Counter
    box((w - .1, .9, .8), (0, -.25, .4), 'wood', .03)
    box((w, 1.0, .06), (0, -.25, .83), 'woodLight', .02)
    for i in range(5):
        box((.08, .02, .6), (-w / 2 + .35 + i * .6, -.71, .42), 'woodDark', .01)
    # Tilted produce crates
    produce = [('red', .09), ('orange', .1), ('green', .1), ('yellow', .08), ('lime', .09)]
    for i, (col, r) in enumerate(produce):
        cx = -1.15 + i * .58
        box((.5, .42, .14), (cx, -.35, .93), 'woodLight', .015, rot=(-14, 0, 0))
        for k in range(6):
            ball(r, (cx - .15 + (k % 3) * .15, -.45 + (k // 3) * .17, 1.03 + (k // 3) * .05), col, seg=10, rings=8)
    # Hanging price boards + bananas
    for i, x in enumerate((-.9, .9)):
        bar((x, -d / 2 + .05, 2.25), (x, -d / 2 + .05, 1.9), .006, 'dark', 6)
        box((.34, .03, .22), (x, -d / 2 + .05, 1.8), 'woodDark', .01)
        plane(.3, .18, (x, -d / 2 + .03, 1.8), 'T_price_tag', rot=(90, 0, 0))
    for k in range(4):
        cyl(.04, .3, (0 + k * .05, -d / 2 + .1, 1.95 - k * .01), 'yellow', rot=(0, 60 + k * 8, 0), v=8)
    # Crates on the floor
    box((.55, .4, .35), (-1.2, .55, .18), 'woodLight', .02)
    box((.55, .4, .35), (1.2, .55, .18), 'woodLight', .02)
    for k in range(6):
        ball(.1, (-1.35 + (k % 3) * .15, .5 + (k // 3) * .12, .4), 'red', seg=10, rings=8)
        ball(.1, (1.05 + (k % 3) * .15, .5 + (k // 3) * .12, .4), 'orange', seg=10, rings=8)


def fair_stall_teal():
    fair_stall('T_awning_teal')


def fair_bunting():
    for x in (-3.5, 3.5):
        bar((x, 0, 0), (x, 0, 3.2), .05, 'woodLight', 8)
        ball(.09, (x, 0, 3.24), 'red', seg=10, rings=8)
    bunting((-3.5, 0, 3.1), (3.5, 0, 3.1), .55, 14)


def wholesale_pallet():
    """Shrink-wrapped pallet of boxes with a WHOLESALE price board."""
    for y in (-.5, 0, .5):
        box((1.3, .12, .12), (0, y, .06), 'woodLight', .01)
    for x in (-.55, 0, .55):
        box((.14, 1.2, .04), (x, 0, .14), 'woodLight', .008)
    box((1.3, 1.2, .03), (0, 0, .17), 'woodLight', .008)
    cols = ['cream', 'woodLight', 'cream', 'woodLight']
    for layer in range(3):
        for i in range(4):
            x, y = -.3 + (i % 2) * .6, -.28 + (i // 2) * .56
            box((.58, .54, .38), (x, y, .38 + layer * .39), cols[(i + layer) % 4], .02)
            plane(.3, .2, (x, y - .275, .4 + layer * .39), 'T_box_label', rot=(90, 0, 0))
    # Shrink film: slightly larger translucent-looking pale box on the sides
    for x in (-.61, .61):
        box((.01, 1.14, 1.2), (x, 0, .77), 'glass', .004)
    # Sticker with -30%
    plane(.5, .5, (.3, -.6, .95), 'T_badge_discount', rot=(90, 0, 0))


def pallet():
    """Plain wooden pallet (1.3 x 1.1) for stacking the market's cardboard boxes."""
    for y in (-.46, 0, .46):
        box((1.3, .14, .1), (0, y, .05), 'woodLight', .015)
    for x in (-.56, 0, .56):
        box((.14, 1.1, .05), (x, 0, .125), 'wood', .01)
    for i in range(6):
        box((.19, 1.1, .03), (-.55 + i * .22, 0, .165), 'woodLight', .008)


def wholesale_board():
    for x in (-.55, .55):
        box((.1, .1, 2.0), (x, .1, 1.0), 'woodDark', .02)
    box((1.5, .08, 1.05), (0, 0, 1.55), 'white', .03)
    plane(1.36, .92, (0, -.045, 1.55), 'T_sign_wholesale', rot=(90, 0, 0))
    box((1.7, .12, .12), (0, 0, 2.1), 'teal', .03)


def pallet_jack():
    box((.55, 1.2, .07), (0, -.1, .08), 'yellow', .02)
    for x in (-.18, .18):
        box((.16, 1.2, .06), (x, -.1, .08), 'yellow', .02)
    box((.6, .25, .35), (0, .6, .22), 'yellow', .03)
    bar((0, .7, .35), (0, .95, 1.15), .03, 'dark')
    box((.36, .05, .06), (0, .98, 1.2), 'dark', .02)
    for x in (-.18, .18):
        cyl(.06, .05, (x, -.62, .06), 'dark', rot=(0, 90, 0), v=12)
    cyl(.1, .1, (0, .62, .1), 'dark', rot=(0, 90, 0), v=16)


def delivery_van():
    """Rounded delivery van in the market colours, ~2.1 x 4.2 m (front at -Y)."""
    box((1.9, 3.1, 1.75), (0, .45, 1.28), 'white', .18)
    box((1.9, 1.2, 1.1), (0, -1.55, .95), 'white', .2)
    box((1.8, .9, .7), (0, -1.45, 1.75), 'white', .25, rot=(-20, 0, 0))
    box((1.94, 4.25, .38), (0, -.1, .52), 'teal', .12)
    plane(1.6, .6, (0, -1.9, 1.55), 'glass', rot=(70, 0, 0))
    for x in (-.96, .96):
        plane(.62, .5, (x, -1.25, 1.55), 'glass', rot=(90, 0, 90))
        plane(2.6, 1.1, (x * 1.005, .55, 1.35), 'T_van_logo', rot=(90, 0, 90 if x > 0 else -90))
    box((1.7, .12, .25), (0, -2.2, .7), 'dark', .05)
    for x in (-.65, .65):
        box((.34, .06, .18), (x, -2.14, 1.0), 'goldLight', .04)
        box((.26, .06, .14), (x, 2.02, 1.2), 'red', .03)
    plane(1.5, 1.5, (0, 2.005, 1.3), 'T_van_back', rot=(90, 0, 180))
    for y in (-1.3, 1.3):
        for x in (-.92, .92):
            cyl(.38, .3, (x, y, .38), 'dark', rot=(0, 90, 0), v=24, bev=.04)
            cyl(.2, .32, (x, y, .38), 'steel', rot=(0, 90, 0), v=16)
    box((.3, .1, .2), (.98, -1.1, 1.75), 'white', .03)


def lane_arrow():
    extrude_shape([(-.25, -.9), (.25, -.9), (.25, .1), (.6, .1), (0, .9), (-.6, .1), (-.25, .1)], .02,
                  (0, 0, .015), 'lime', rot=(0, 0, 0), bev=.006)


def green_light():
    cyl(.07, 3.0, (0, 0, 1.5), 'dark', v=12)
    box((.42, .38, 1.1), (0, 0, 3.2), 'dark', .06)
    for i, col in enumerate(('C_5A4040', 'C_5A5540', 'lime')):
        cyl(.13, .06, (0, -.2, 3.55 - i * .34), col.replace('C_', '') if col.startswith('C_') else col, rot=(90, 0, 0), v=20)
        cyl(.17, .03, (0, -.22, 3.62 - i * .34), 'dark', rot=(90, 0, 0), v=20, r2=.17)


def star_badge():
    extrude_shape(star_pts(.55, .25), .16, (0, 0, 0), 'gold', rot=(90, 0, 0), bev=.035)
    extrude_shape(star_pts(.36, .16), .03, (0, -.09, 0), 'goldLight', rot=(90, 0, 0), bev=.008)


def energy_bolt():
    pts = [(.12, .6), (-.32, -.05), (-.02, -.05), (-.14, -.6), (.32, .08), (.02, .08)]
    extrude_shape(pts, .14, (0, 0, 0), 'yellow', rot=(90, 0, 0), bev=.03)


def bread_rack():
    """Rolling bakery rack full of fresh trays."""
    for x in (-.45, .45):
        for y in (-.3, .3):
            bar((x, y, .08), (x, y, 1.75), .02, 'steel', 8)
            cyl(.05, .04, (x, y, .05), 'dark', rot=(0, 90, 0), v=12)
    for i in range(5):
        z = .35 + i * .32
        box((.95, .66, .03), (0, 0, z), 'metal', .01)
        for k in range(4):
            cyl(.07, .3, (-.33 + k * .22, -.05, z + .07), 'bread' if (i + k) % 2 else 'breadLight', rot=(90, 0, 0), v=12)
        ball(.08, (-.3 + (i % 3) * .2, .2, z + .08), 'breadLight', (1.4, 1, .7), 10, 8)
    box((.2, .02, .25), (0, -.33, 1.72), 'white', .01)


def team_banner():
    for x in (-1.2, 1.2):
        bar((x, 0, 0), (x, 0, 2.6), .04, 'woodDark', 8)
    box((2.5, .05, .8), (0, 0, 2.15), 'teal', .03)
    plane(2.3, .66, (0, -.03, 2.15), 'T_banner_team', rot=(90, 0, 0))


def training_board():
    """Easel whiteboard + flip chart used for the express training."""
    for x in (-.7, .7):
        bar((x, -.1, 0), (x * .9, 0, 2.1), .03, 'woodDark', 8)
    bar((0, .6, 0), (0, 0, 2.0), .03, 'woodDark', 8)
    box((1.7, .06, 1.15), (0, -.05, 1.45), 'steel', .03)
    plane(1.58, 1.03, (0, -.085, 1.45), 'T_training_board', rot=(90, 0, 0))
    box((1.6, .12, .04), (0, -.1, .86), 'dark', .01)
    for i, col in enumerate(('red', 'teal', 'dark')):
        cyl(.012, .12, (-.3 + i * .1, -.12, .9), col, rot=(0, 90, 0), v=8)


def training_chairs():
    for i, x in enumerate((-1.1, 0, 1.1)):
        box((.46, .44, .05), (x, 0, .46), ['teal', 'orange', 'teal'][i], .02)
        box((.46, .05, .45), (x, .21, .72), ['teal', 'orange', 'teal'][i], .02)
        for dx in (-.19, .19):
            for dy in (-.18, .18):
                bar((x + dx, dy, 0), (x + dx, dy, .44), .015, 'dark', 6)
        box((.3, .22, .02), (x + .05, -.05, .5), 'paper', .005)


def graduation_cap():
    box((.7, .7, .05), (0, 0, .2), 'dark', .01, rot=(0, 0, 45))
    cyl(.22, .2, (0, 0, .08), 'dark', v=20)
    ball(.035, (0, 0, .23), 'gold', seg=8, rings=6)
    bar((0, 0, .23), (.3, -.1, .2), .012, 'gold', 6)
    bar((.3, -.1, .2), (.32, -.1, -.02), .012, 'gold', 6)
    cyl(.04, .1, (.32, -.1, -.06), 'gold', v=8, r2=.01)


def gift_box():
    """Big lucky-checkout gift with a bow and a half-open lid."""
    box((.8, .8, .6), (0, 0, .3), 'teal', .03)
    box((.14, .82, .62), (0, 0, .3), 'gold', .01)
    box((.82, .14, .62), (0, 0, .3), 'gold', .01)
    box((.88, .88, .16), (-.05, .12, .72), 'teal', .03, rot=(24, 0, -8))
    box((.16, .9, .18), (-.05, .12, .72), 'gold', .01, rot=(24, 0, -8))
    for side in (-1, 1):
        torus(.13, .045, (side * .14 - .05, .3, 1.02), 'gold', rot=(90, 20 * side, 0))
    ball(.07, (-.05, .3, 1.0), 'goldLight', seg=12, rings=8)
    for i in range(6):
        a = i * math.pi / 3
        ball(.07, (math.cos(a) * .25, math.sin(a) * .25 - .05, .74 + (i % 2) * .08), 'goldLight', seg=10, rings=8)


def confetti_cannon():
    cyl(.18, .7, (0, 0, .5), 'magenta', rot=(30, 0, 0), v=20, r2=.28)
    torus(.28, .04, (0, -.175, .80), 'gold', rot=(30, 0, 0))
    for i in range(6):
        a = i * math.pi / 3
        ball(.05, (math.cos(a) * .18, -.25 + math.sin(a) * .05, .95 + math.sin(a) * .15), ['yellow', 'teal', 'rose'][i % 3], seg=8, rings=6)
    box((.3, .3, .18), (0, .18, .09), 'dark', .03)


def lucky_sign():
    for x in (-.35, .35):
        bar((x, 0, 0), (x, 0, 1.6), .025, 'gold', 8)
    box((1.0, .05, .6), (0, 0, 1.55), 'gold', .04)
    plane(.9, .5, (0, -.03, 1.55), 'T_sign_lucky', rot=(90, 0, 0))


def flower_arch():
    """Garden arch over the entrance, ~3.4 m wide."""
    n = 26
    for side in (-1, 1):
        for i in range(n):
            a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
            p0 = (1.6 * math.cos(a0), side * .15, 1.6 + 1.2 * math.sin(a0))
            p1 = (1.6 * math.cos(a1), side * .15, 1.6 + 1.2 * math.sin(a1))
            bar(p0, p1, .035, 'white', 8)
        for x in (-1.6, 1.6):
            bar((x, side * .15, 0), (x, side * .15, 1.6), .04, 'white', 8)
    for i in range(34):
        a = math.pi * i / 33
        x, z = 1.6 * math.cos(a), 1.6 + 1.2 * math.sin(a)
        ball(.13, (x, -.05, z), 'leaf', seg=8, rings=6)
        ball(.09, (x + .05, -.18, z + .04), ['rose', 'yellow', 'white', 'salmon'][i % 4], seg=10, rings=6)
    for x in (-1.6, 1.6):
        for k in range(9):
            z = .15 + k * .17
            ball(.12, (x, -.08, z), 'leaf', seg=8, rings=6)
            if k % 2:
                ball(.08, (x + .06, -.2, z), ['rose', 'yellow', 'white'][k % 3], seg=10, rings=6)
        box((.55, .55, .45), (x, 0, .22), 'brick', .04)
    plane(1.6, .42, (0, -.2, 2.95), 'T_sign_welcome', rot=(90, 0, 0))
    box((1.7, .06, .5), (0, -.16, 2.95), 'white', .03)


def flower_pot():
    potted_flowers(0, 0, 'rose', 'brick', 1.1)


def balloon_bunch():
    cols = ['yellow', 'teal', 'rose', 'white', 'orange']
    for i in range(5):
        a = i * 2 * math.pi / 5
        balloon((math.cos(a) * .28, math.sin(a) * .28, 2.1 + (i % 2) * .25), cols[i], .26, 1.5)
    balloon((0, 0, 2.55), 'gold', .28, 1.9)
    box((.2, .2, .12), (0, 0, .06), 'dark', .03)


def sun_badge():
    cyl(.45, .14, (0, 0, 0), 'yellow', rot=(90, 0, 0), v=32, bev=.04)
    for i in range(12):
        a = i * math.pi / 6
        extrude_shape([(-.09, 0), (.09, 0), (0, .28)], .08, (math.sin(a) * .5, 0, math.cos(a) * .5), 'orange',
                      rot=(90, math.degrees(a), 0), bev=.015)
    plane(.6, .6, (0, -.08, 0), 'T_sun_face', rot=(90, 0, 0))


def rival_tent():
    """Competitor pop-up tent in magenta with a PROMO banner, 3 x 3 m."""
    s = 1.5
    for x in (-s, s):
        for y in (-s, s):
            bar((x, y, 0), (x, y, 2.2), .04, 'steel', 8)
            cyl(.12, .04, (x, y, .02), 'dark', v=12)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=s * 1.45, radius2=.08, depth=.9, location=(0, 0, 2.62),
                                    rotation=(0, 0, math.radians(45)))
    _finish(bpy.context.object, 'magenta')
    for side in range(4):
        ang = side * 90
        for i in range(8):
            x = -s + .19 + i * .375
            c, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            px, py = x * c - (-s - .02) * sn, x * sn + (-s - .02) * c
            cyl(.19, .02, (px, py, 2.15), ['magenta', 'white'][i % 2], rot=(90, 0, ang), v=14)
    box((3.1, .06, .35), (0, -s - .04, 2.3), 'white', .02)
    plane(2.9, .3, (0, -s - .075, 2.3), 'T_rival_valance', rot=(90, 0, 0))
    box((2.4, .9, .95), (0, -.5, .48), 'white', .04)
    plane(2.2, .75, (0, -.955, .5), 'T_rival_counter', rot=(90, 0, 0))
    for i in range(6):
        box((.3, .3, .3), (-.9 + i * .36, -.5, 1.1), ['magenta', 'violet', 'yellow'][i % 3], .03)


def rival_board():
    for x in (-.8, .8):
        box((.1, .1, 2.6), (x, .12, 1.3), 'dark', .02)
    box((2.0, .1, 1.3), (0, 0, 2.05), 'magenta', .05)
    plane(1.84, 1.14, (0, -.055, 2.05), 'T_sign_rival', rot=(90, 0, 0))
    for i in range(6):
        ball(.06, (-.9 + i * .36, -.06, 2.74), 'yellow', seg=8, rings=6)


def tube_man():
    """Inflatable tube man for the rival stand (sways in Unity)."""
    cyl(.35, .4, (0, 0, .2), 'dark', v=20, bev=.03)
    pts = [(0, 0, .4), (.05, 0, 1.2), (-.05, 0, 2.0), (.08, 0, 2.8), (0, 0, 3.3)]
    for a, b in zip(pts, pts[1:]):
        bar(a, b, .22, 'magenta', 16)
    ball(.28, (0, 0, 3.45), 'magenta', seg=16, rings=10)
    ball(.08, (-.1, -.24, 3.52), 'white', seg=10, rings=8)
    ball(.08, (.1, -.24, 3.52), 'white', seg=10, rings=8)
    ball(.04, (-.1, -.31, 3.52), 'dark', seg=8, rings=6)
    ball(.04, (.1, -.31, 3.52), 'dark', seg=8, rings=6)
    box((.22, .04, .06), (0, -.27, 3.33), 'dark', .02)
    for side in (-1, 1):
        bar((side * .15, 0, 2.6), (side * .8, 0, 3.1), .11, 'yellow', 12)
        bar((side * .8, 0, 3.1), (side * 1.0, 0, 3.6), .09, 'yellow', 12)
    for i in range(6):
        cyl(.25, .1, (0, 0, 3.72 + i * .04), ['yellow', 'magenta'][i % 2], v=8, r2=.05)


def price_tag():
    pts = [(-.35, .25), (.2, .25), (.42, 0), (.2, -.25), (-.35, -.25)]
    extrude_shape(pts, .06, (0, 0, 0), 'yellow', rot=(90, 0, 0), bev=.02)
    plane(.46, .38, (-.05, -.04, 0), 'T_tag_cheap', rot=(90, 0, 0))
    cyl(.05, .07, (.24, 0, 0), 'dark', rot=(90, 0, 0), v=12)


def coupon_stand():
    for x in (-.4, .4):
        bar((x, 0, 0), (x, 0, 1.6), .025, 'steel', 8)
    box((1.0, .06, 1.1), (0, 0, 1.15), 'white', .04)
    plane(.92, 1.0, (0, -.035, 1.15), 'T_coupon_board', rot=(90, 0, 0))
    for i in range(3):
        box((.26, .1, .05), (-.3 + i * .3, -.08, .6), 'paper', .01)
    box((.95, .14, .03), (0, -.07, .57), 'teal', .01)


def calculator():
    box((.4, .08, .56), (0, 0, 0), 'dark', .05)
    plane(.32, .14, (0, -.045, .17), 'T_calc_screen', rot=(90, 0, 0))
    for r in range(4):
        for c in range(3):
            box((.08, .03, .07), (-.1 + c * .1, -.05, .04 - r * .085), 'orange' if (r == 3 and c == 2) else 'paper', .01)


def shopping_list():
    box((.44, .02, .6), (0, 0, 0), 'paper', .01)
    plane(.4, .56, (0, -.012, 0), 'T_shopping_list', rot=(90, 0, 0))
    box((.2, .03, .06), (0, 0, .3), 'red', .01)


def broken_terminal():
    """Checkout POS with an error screen, cable mess and repair toolbox."""
    box((.45, .4, .15), (0, 0, .08), 'dark', .03)
    bar((0, 0, .15), (0, 0, .45), .04, 'steel', 10)
    box((.6, .08, .45), (0, 0, .7), 'dark', .04, rot=(-10, 0, 0))
    plane(.52, .37, (0, -.048, .7), 'T_pos_error', rot=(80, 0, 0))
    box((.28, .2, .06), (.35, -.2, .06), 'dark', .02)
    plane(.22, .14, (.35, -.2, .095), 'T_card_error', rot=(0, 0, 0))
    for i in range(5):
        a = (.1 * i, -.3 - .05 * i, .01)
        b = (.15 * i - .3, -.4 + .1 * (i % 2), .01)
        bar(a, b, .012, ['red', 'dark', 'yellow'][i % 3], 6)


def warning_badge():
    s = .55
    extrude_shape([(0, s), (s * .95, -s * .6), (-s * .95, -s * .6)], .12, (0, 0, 0), 'red', rot=(90, 0, 0), bev=.06)
    extrude_shape([(0, s * .72), (s * .7, -s * .45), (-s * .7, -s * .45)], .02, (0, -.07, 0), 'yellow', rot=(90, 0, 0), bev=.01)
    box((.07, .02, .28), (0, -.09, .02), 'dark', .02)
    ball(.045, (0, -.09, -.2), 'dark', seg=8, rings=6)


def out_of_order_sign():
    a_frame_sign('T_sign_outoforder', 1.0, .65, frame='yellow')


def toolbox():
    box((.7, .34, .32), (0, 0, .17), 'red', .03)
    box((.72, .36, .08), (0, 0, .36), 'red', .03)
    bar((-.2, 0, .45), (.2, 0, .45), .025, 'dark', 8)
    for x in (-.25, .25):
        bar((x, 0, .4), (x * .8, 0, .45), .02, 'dark', 6)
    box((.08, .02, .08), (0, -.18, .3), 'steel', .01)
    # Tools lying on the lid
    box((.5, .05, .05), (.1, -.05, .43), 'steel', .01, rot=(0, 0, 20))
    cyl(.07, .04, (.35, .04, .43), 'steel', v=12)
    box((.22, .06, .04), (-.2, .08, .42), 'yellow', .01, rot=(0, 0, -30))


def fuel_pump():
    """Gas pump whose display shows the price shooting up."""
    box((1.0, .7, .14), (0, 0, .07), 'metal', .03)
    box((.8, .5, 1.5), (0, 0, .87), 'red', .06)
    box((.84, .54, .4), (0, 0, 1.8), 'white', .06)
    plane(.64, .28, (0, -.275, 1.8), 'T_fuel_display', rot=(90, 0, 0))
    plane(.5, .5, (0, -.255, 1.0), 'T_fuel_logo', rot=(90, 0, 0))
    box((.2, .1, .3), (.42, -.05, 1.15), 'dark', .03)
    bar((.42, -.1, 1.02), (.55, -.25, .5), .025, 'dark', 8)
    bar((.55, -.25, .5), (.47, -.2, .25), .025, 'dark', 8)
    box((.1, .05, .25), (.42, -.12, 1.2), 'yellow', .02)
    cyl(.18, .08, (0, 0, 2.05), 'yellow', v=16)


def up_arrow():
    extrude_shape([(-.2, -.6), (.2, -.6), (.2, .05), (.45, .05), (0, .6), (-.45, .05), (-.2, .05)], .14,
                  (0, 0, 0), 'red', rot=(90, 0, 0), bev=.03)


def oil_barrels():
    barrel((0, 0, 0), 'red')
    barrel((.62, .1, 0), 'yellow')
    barrel((.3, .6, 0), 'teal')
    box((.3, .2, .15), (-.4, -.4, .08), 'dark', .02)


def jerry_can():
    box((.36, .16, .46), (0, 0, .23), 'red', .04)
    bar((-.08, 0, .5), (.08, 0, .5), .025, 'red', 8)
    cyl(.04, .1, (.13, 0, .52), 'dark', rot=(0, 30, 0), v=10)


def traffic_car(body='salmon'):
    """Compact city car, 1.8 x 3.6 m, front at -Y."""
    box((1.7, 3.5, .55), (0, 0, .62), body, .18)
    box((1.5, 1.9, .72), (0, .2, 1.22), body, .22)
    plane(1.3, .55, (0, -.77, 1.24), 'glass', rot=(62, 0, 0))
    plane(1.3, .5, (0, 1.17, 1.24), 'glass', rot=(-65, 0, 180))
    for x in (-.755, .755):
        plane(1.4, .45, (x, .2, 1.26), 'glass', rot=(90, 0, 90 if x > 0 else -90))
    box((1.74, .16, .2), (0, -1.76, .5), 'dark', .06)
    box((1.74, .16, .2), (0, 1.76, .5), 'dark', .06)
    for x in (-.6, .6):
        box((.3, .06, .16), (x, -1.74, .78), 'goldLight', .04)
        box((.26, .06, .12), (x, 1.74, .8), 'red', .03)
    for y in (-1.15, 1.15):
        for x in (-.82, .82):
            cyl(.33, .26, (x, y, .33), 'dark', rot=(0, 90, 0), v=22, bev=.04)
            cyl(.17, .28, (x, y, .33), 'steel', rot=(0, 90, 0), v=14)
    box((.9, .8, .06), (0, .25, 1.6), 'white' if body != 'white' else 'teal', .03)


def traffic_car_blue():
    traffic_car('blue')


def traffic_car_yellow():
    traffic_car('yellow')


def traffic_car_teal():
    traffic_car('tealLight')


def slow_sign():
    cyl(.035, 2.0, (0, 0, 1.0), 'steel', v=10)
    box((.9, .06, .9), (0, 0, 2.2), 'yellow', .04, rot=(0, 45, 0))
    plane(.64, .64, (0, -.035, 2.2), 'T_sign_traffic', rot=(90, 0, 0))
    box((.35, .35, .06), (0, 0, .03), 'dark', .02)


def angry_cloud():
    for x, z, r in ((-.3, 0, .32), (.05, .12, .4), (.4, -.02, .3), (0, -.12, .3)):
        ball(r, (x, 0, z), 'metal', (1, .7, 1), 14, 10)
    for x in (-.14, .2):
        ball(.06, (x, -.3, .02), 'dark', seg=10, rings=8)
        box((.18, .04, .05), (x, -.31, .13), 'dark', .01, rot=(0, 25 if x < 0 else -25, 0))
    box((.2, .04, .04), (.03, -.31, -.1), 'dark', .01, rot=(0, 8, 0))
    energy_bolt_small = [(.06, .3), (-.16, -.03), (-.01, -.03), (-.07, -.3), (.16, .04), (.01, .04)]
    extrude_shape(energy_bolt_small, .08, (.05, -.2, -.35), 'yellow', rot=(90, 0, 0), bev=.015)


def step_ladder():
    for x in (-.28, .28):
        bar((x, -.3, 0), (x * .8, 0, 1.9), .03, 'yellow', 8)
        bar((x, .45, 0), (x * .8, .02, 1.85), .025, 'steel', 8)
    for i in range(5):
        z = .3 + i * .33
        t = z / 1.9
        box((.52 * (1 - t * .2), .12, .035), (0, -.3 + t * .3, z), 'yellow', .01)
    box((.46, .3, .05), (0, 0, 1.92), 'yellow', .02)


def repair_station():
    """Maintenance zone: floor mat, barrier with maintenance sign, spare parts."""
    box((2.6, 1.8, .03), (0, 0, .015), 'yellow', .005)
    for i in range(10):
        box((.18, 1.82, .032), (-1.2 + i * .27, 0, .018), 'dark', .002, rot=(0, 0, 30))
    for x in (-1.2, 1.2):
        cyl(.14, .05, (x, -.9, .025), 'dark', v=16)
        cyl(.035, .9, (x, -.9, .45), 'steel', v=10)
    box((2.3, .05, .22), (0, -.9, .75), 'white', .02)
    plane(2.2, .18, (0, -.93, .75), 'T_tape_maintenance', rot=(90, 0, 0))
    box((.5, .4, .35), (.8, .5, .18), 'metal', .03)
    cyl(.18, .35, (-.8, .5, .18), 'steel', v=16)
    box((.6, .45, .08), (-.1, .5, .04), 'woodLight', .02)
    for k in range(3):
        cyl(.08, .06, (-.25 + k * .15, .5, .11), 'dark', v=14)


def maintenance_sign():
    a_frame_sign('T_sign_maintenance', 1.1, .7, frame='orange')


def gear():
    pts = []
    n = 10
    for i in range(n * 4):
        a = 2 * math.pi * i / (n * 4)
        r = .5 if (i % 4) in (1, 2) else .38
        pts.append((r * math.cos(a), r * math.sin(a)))
    extrude_shape(pts, .14, (0, 0, 0), 'steel', rot=(90, 0, 0), bev=.02)
    cyl(.14, .16, (0, 0, 0), 'dark', rot=(90, 0, 0), v=20)


def break_corner():
    """Staff break corner: bench, side table with coffee machine and cups, potted plant."""
    box((2.8, 1.6, .03), (0, 0, .015), 'woodLight', .005)
    box((1.7, .5, .08), (-.4, .25, .48), 'wood', .02)
    box((1.7, .08, .45), (-.4, .47, .78), 'wood', .02)
    for x in (-1.15, .35):
        box((.08, .45, .45), (x, .25, .23), 'dark', .02)
    box((.7, .55, .72), (1.0, .3, .36), 'teal', .03)
    box((.72, .57, .04), (1.0, .3, .74), 'woodLight', .01)
    box((.32, .3, .45), (1.1, .38, .98), 'dark', .04)
    box((.26, .04, .12), (1.1, .22, 1.08), 'orange', .01)
    cyl(.05, .09, (1.1, .28, .81), 'white', v=12)
    for k in range(3):
        cyl(.045, .1, (.78 + k * .1, .12, .8), ['white', 'orange', 'teal'][k], v=12)
    potted_flowers(-1.25, .55, 'yellow', 'teal', .8)
    box((.5, .4, .06), (-.4, -.35, .03), 'woodDark', .01)


def coffee_cup_big():
    cyl(.22, .34, (0, 0, .17), 'white', v=24, r2=.26)
    cyl(.23, .02, (0, 0, .34), 'coffee', v=24)
    torus(.1, .035, (.27, 0, .19), 'white', rot=(90, 0, 0), maj=16, mino=8)
    cyl(.28, .03, (0, 0, .015), 'white', v=24)


def zzz():
    def z_shape(s):
        return [(-s, s), (s, s), (s, s * .6), (-s * .35, -s * .6), (s, -s * .6), (s, -s), (-s, -s), (-s, -s * .6),
                (s * .35, s * .6), (-s, s * .6)]
    extrude_shape(z_shape(.18), .06, (-.25, 0, -.15), 'sky', rot=(90, 0, 0), bev=.015)
    extrude_shape(z_shape(.13), .05, (.05, 0, .12), 'sky', rot=(90, 0, 0), bev=.012)
    extrude_shape(z_shape(.09), .04, (.27, 0, .34), 'sky', rot=(90, 0, 0), bev=.01)


def inspection_kit():
    """Inspector's folding table with documents, thermometer and a sealed case."""
    box((1.2, .6, .05), (0, 0, .75), 'white', .02)
    for x in (-.52, .52):
        for y in (-.24, .24):
            bar((x, y, 0), (x, y, .74), .018, 'steel', 6)
    box((.5, .34, .3), (-.3, .05, .93), 'dark', .04)
    box((.18, .05, .04), (-.3, .05, 1.1), 'steel', .01)
    for k in range(3):
        box((.3, .4, .012), (.25 + k * .02, -.02, .79 + k * .013), 'paper', .003, rot=(0, 0, k * 6))
    plane(.28, .38, (.29, -.02, .832), 'T_inspection_form', rot=(0, 0, 12))
    cyl(.02, .3, (.5, .18, .9), 'white', rot=(0, 70, 0), v=8)


def clipboard_icon():
    box((.6, .06, .8), (0, 0, 0), 'woodLight', .04)
    box((.26, .08, .1), (0, 0, .4), 'steel', .02)
    plane(.5, .66, (0, -.035, -.03), 'T_checklist', rot=(90, 0, 0))


def magnifier():
    torus(.28, .06, (0, 0, .15), 'dark', rot=(90, 0, 0), maj=32, mino=10)
    cyl(.26, .02, (0, 0, .15), 'glass', rot=(90, 0, 0), v=28)
    bar((.2, 0, -.05), (.48, 0, -.4), .06, 'dark', 12)


def id_badge():
    box((.5, .04, .66), (0, 0, 0), 'white', .04)
    plane(.44, .6, (0, -.025, 0), 'T_inspector_badge', rot=(90, 0, 0))
    box((.14, .05, .06), (0, 0, .34), 'dark', .01)


# ---------------------------------------------------------------- market entrance (not an event prop)
def profile_x(points, x0, x1, key):
    """Prism from a (y, z) profile extruded between x0 and x1 (for sloped cheeks and caps)."""
    mesh = bpy.data.meshes.new('profile'); obj = bpy.data.objects.new('profile', mesh)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in points]
    b = [bm.verts.new((x1, y, z)) for y, z in points]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh); bm.free()
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    bevel(obj, .02, 2)
    return _finish(obj, key)


def market_portal():
    """Storefront portal: teal pillars with cream capitals, cream header with a painted MERCADO board,
    a striped awning, wall lanterns and a steel threshold. Origin: floor level, centre of the opening,
    on the portal's street face; the building is towards +Y."""
    for s in (-1, 1):
        x = s * 1.64
        box((.64, .84, .32), (x, .38, .16), 'tealDark', .04)
        box((.52, .72, 1.98), (x, .38, 1.31), 'teal', .05)
        box((.6, .8, .14), (x, .38, 2.23), 'cream', .03)
        for k in range(3):  # recessed fluting on the street face
            box((.06, .04, 1.5), (x + (k - 1) * .14, .005, 1.28), 'tealDark', .015)
        box((.16, .12, .06), (x, -.07, 1.62), 'dark', .02)
        cyl(.07, .26, (x, -.18, 1.66), 'tealDark', v=12)
        ball(.075, (x, -.18, 1.68), 'goldLight', scale=(1, 1, 1.3))
        cyl(.1, .05, (x, -.18, 1.81), 'tealDark', v=12)
    box((3.96, .9, .46), (0, .38, 2.53), 'cream', .05)
    box((4.0, .94, .09), (0, .38, 2.34), 'teal', .03)
    box((4.0, .94, .05), (0, .38, 2.74), 'orange', .02)
    # Sign board on top of the header.
    box((2.86, .18, .74), (0, .12, 3.12), 'tealDark', .06)
    plane(2.66, .62, (0, .015, 3.12), 'T_sign_market')
    for s in (-1, 1):
        ball(.08, (s * 1.43, .12, 3.5), 'orange')
    # Striped awning, tilted towards the street, with a scalloped valance.
    plane(3.36, 1.0, (0, -.5, 2.35), 'T_awning_teal', rot=(22, 0, 0))
    plane(3.36, 1.0, (0, -.5, 2.335), 'cream', rot=(202, 0, 0))
    plane(3.36, .2, (0, -.965, 2.08), 'T_awning_teal', rot=(90, 0, 0))
    for k in range(12):
        x = -1.54 + k * .28
        cyl(.14, .03, (x, -.952, 1.98), 'teal' if k % 2 == 0 else 'white', rot=(90, 0, 0), v=14)
    for s in (-1, 1):
        bar((s * 1.66, -.02, 2.5), (s * 1.66, -.93, 2.18), .025, 'dark')
    # Threshold and welcome mat on the shop floor.
    box((2.84, .76, .14), (0, .38, -.065), 'steel', .02)
    box((2.84, .08, .03), (0, .02, .005), 'dark', .01)
    box((2.3, 1.0, .03), (0, 1.3, .0), 'tealDark', .012)
    plane(2.2, .92, (0, 1.3, .017), 'T_mat_welcome', rot=(0, 0, 0))


STEP_L, STEP_RISE = 1.5, .59


def market_steps():
    """Three generous steps from the sidewalk to the shop floor with yellow nosings, teal cheek walls and
    steel handrails. Origin: top of the steps at the portal face; the flight runs towards -Y and is stretched
    in Unity to the projected entrance depth."""
    L, R, n, w = STEP_L, STEP_RISE, 3, 2.84
    for i in range(n):
        y0 = -L + i * L / n
        top = -R + (i + 1) * R / n
        depth = -y0
        box((w, depth, top + R + .06), (0, y0 / 2, (top - R - .06) / 2), 'D9D1BD', .015)
        box((w, .07, .012), (0, y0 + .04, top + .004), 'yellow', .004)
        for k in range(1, 7):  # paving joints
            box((.018, depth - .02, .006), (-w / 2 + k * w / 7, y0 / 2, top + .002), 'B8AF9A', 0)
    for s in (-1, 1):
        x0, x1 = s * w / 2, s * (w / 2 + .24)
        lo, hi = min(x0, x1), max(x0, x1)
        profile_x([(0, .16), (0, -R - .06), (-L, -R - .06), (-L, -R + .16)], lo, hi, 'teal')
        profile_x([(0, .22), (0, .16), (-L, -R + .16), (-L, -R + .22)], lo - .02, hi + .02, 'cream')
        xr = s * (w / 2 + .12)
        posts = [(-L + .12, -R + .19), (-L / 2, -R / 2 + .19), (-.1, .19)]
        for y, z in posts:
            bar((xr, y, z), (xr, y, z + .82), .03, 'dark')
        bar((xr, -L + .12, -R + 1.0), (xr, -.1, 1.0), .035, 'steel')
        bar((xr, -.1, 1.0), (xr, .25, 1.0), .035, 'steel')
        ball(.05, (xr, -L + .12, -R + 1.0), 'steel')


BUILDERS = {
    'CartEmpty': cart_empty, 'CartFull': cart_full, 'QueueStanchions': queue_stanchions,
    'CoinStack': coin_stack, 'GoldCoin': gold_coin, 'MoneyBag': money_bag,
    'RingLight': ring_light, 'CreatorBackdrop': creator_backdrop, 'Heart': heart,
    'FairStallRed': fair_stall, 'FairStallTeal': fair_stall_teal, 'FairBunting': fair_bunting,
    'WholesalePallet': wholesale_pallet, 'Pallet': pallet, 'WholesaleBoard': wholesale_board, 'PalletJack': pallet_jack,
    'DeliveryVan': delivery_van, 'LaneArrow': lane_arrow, 'GreenLight': green_light,
    'StarBadge': star_badge, 'EnergyBolt': energy_bolt, 'BreadRack': bread_rack, 'TeamBanner': team_banner,
    'TrainingBoard': training_board, 'TrainingChairs': training_chairs, 'GraduationCap': graduation_cap,
    'GiftBox': gift_box, 'ConfettiCannon': confetti_cannon, 'LuckySign': lucky_sign,
    'FlowerArch': flower_arch, 'FlowerPot': flower_pot, 'BalloonBunch': balloon_bunch, 'SunBadge': sun_badge,
    'RivalTent': rival_tent, 'RivalBoard': rival_board, 'TubeMan': tube_man,
    'PriceTag': price_tag, 'CouponStand': coupon_stand, 'Calculator': calculator, 'ShoppingList': shopping_list,
    'BrokenTerminal': broken_terminal, 'WarningBadge': warning_badge, 'OutOfOrderSign': out_of_order_sign,
    'Toolbox': toolbox,
    'FuelPump': fuel_pump, 'UpArrow': up_arrow, 'OilBarrels': oil_barrels, 'JerryCan': jerry_can,
    'TrafficCarRed': traffic_car, 'TrafficCarBlue': traffic_car_blue, 'TrafficCarYellow': traffic_car_yellow,
    'TrafficCarTeal': traffic_car_teal, 'SlowSign': slow_sign, 'AngryCloud': angry_cloud,
    'StepLadder': step_ladder, 'RepairStation': repair_station, 'MaintenanceSign': maintenance_sign, 'Gear': gear,
    'BreakCorner': break_corner, 'CoffeeCup': coffee_cup_big, 'Zzz': zzz,
    'MarketPortal': market_portal, 'MarketSteps': market_steps,
    'InspectionKit': inspection_kit, 'ClipboardIcon': clipboard_icon, 'Magnifier': magnifier, 'IdBadge': id_badge,
}


# Game models the user already supplied (Tripo GLBs in ArtSource/MapModels), re-exported at real-world size
# (metres, longest side) with a light decimation so several can appear in one event on mobile.
GAME_MODELS = {'GameCardboardBox': ('CardboardBox', .62), 'GameVegetableCrate': ('VegetableCrate', .7),
               'GameFruitStand': ('FruitMarketStand', 2.2), 'GameCartoonCar': ('CartoonCar', 3.5),
               'GameStylizedCar': ('StylizedCar', 3.6), 'GameToyVan': ('ToyVan', 4.0),
               'GameDeliveryTruck': ('DeliveryTruck', 4.6), 'GameFlowerPlanter': ('FlowerPlanter', 1.5),
               'GameTrafficLight': ('TrafficLight', 3.4), 'GameWorker': ('ConstructionWorker', 1.8)}
SOURCES = ROOT / 'unity/CheckoutSimulator/ArtSource/MapModels'
TEX = ASSETS / 'Tex'
# Sign-heavy props get a sharper atlas so the painted lettering stays readable.
HIRES = {'WholesaleBoard', 'RivalBoard', 'RivalTent', 'CreatorBackdrop', 'TrainingBoard', 'LuckySign', 'CouponStand',
         'FairStallRed', 'FairStallTeal', 'DeliveryVan', 'FuelPump', 'TeamBanner', 'FlowerArch', 'WholesalePallet', 'MarketPortal'}


def reset():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.images):
        for item in list(block):
            block.remove(item)


def painted_material(m, source_uv):
    """Emission network baked into the atlas: palette colour (or sign texture) with soft painterly variation,
    ambient occlusion in crevices and a warm highlight on convex edges — the look of the supplied Tripo models."""
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    out = [n for n in nodes if n.type == 'OUTPUT_MATERIAL'][0]
    tex = next((n for n in nodes if n.type == 'TEX_IMAGE' and n.image), None)
    if tex:
        base = tex.outputs['Color']
        if source_uv:
            uv = nodes.new('ShaderNodeUVMap'); uv.uv_map = source_uv
            links.new(uv.outputs['UV'], tex.inputs['Vector'])
    else:
        rgb = nodes.new('ShaderNodeRGB')
        rgb.outputs[0].default_value = bsdf.inputs['Base Color'].default_value[:]
        base = rgb.outputs[0]
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 7
    noise.inputs['Detail'].default_value = 6
    var = nodes.new('ShaderNodeMapRange')
    var.inputs['To Min'].default_value, var.inputs['To Max'].default_value = .9, 1.08
    links.new(noise.outputs['Fac'], var.inputs['Value'])
    mul1 = nodes.new('ShaderNodeMix'); mul1.data_type = 'RGBA'; mul1.blend_type = 'MULTIPLY'
    mul1.inputs['Factor'].default_value = .25 if tex else 1
    links.new(base, mul1.inputs[6]); links.new(var.outputs[0], mul1.inputs[7])
    ao = nodes.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = .3; ao.samples = 16
    aor = nodes.new('ShaderNodeMapRange')
    aor.inputs['To Min'].default_value, aor.inputs['To Max'].default_value = .5, 1
    links.new(ao.outputs['AO'], aor.inputs['Value'])
    mul2 = nodes.new('ShaderNodeMix'); mul2.data_type = 'RGBA'; mul2.blend_type = 'MULTIPLY'
    mul2.inputs['Factor'].default_value = .55 if tex else 1
    links.new(mul1.outputs[2], mul2.inputs[6]); links.new(aor.outputs[0], mul2.inputs[7])
    geo = nodes.new('ShaderNodeNewGeometry')
    edge = nodes.new('ShaderNodeMapRange')
    edge.inputs['From Min'].default_value, edge.inputs['From Max'].default_value = .52, .64
    edge.inputs['To Min'].default_value, edge.inputs['To Max'].default_value = 0, .3 if not tex else .1
    links.new(geo.outputs['Pointiness'], edge.inputs['Value'])
    scr = nodes.new('ShaderNodeMix'); scr.data_type = 'RGBA'; scr.blend_type = 'SCREEN'
    links.new(edge.outputs[0], scr.inputs['Factor']); links.new(mul2.outputs[2], scr.inputs[6])
    scr.inputs[7].default_value = (1, .95, .85, 1)
    emit = nodes.new('ShaderNodeEmission')
    links.new(scr.outputs[2], emit.inputs['Color']); links.new(emit.outputs[0], out.inputs['Surface'])
    return nodes


def bake_atlas(obj, name, size):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.device = 'CPU'
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    mesh = obj.data
    source_uv = mesh.uv_layers[0].name if mesh.uv_layers else None
    # Sign textures keep sampling their authored UVs; the atlas gets its own unwrap.
    atlas_uv = mesh.uv_layers.new(name='Atlas')
    mesh.uv_layers.active = atlas_uv
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=.006)
    bpy.ops.object.mode_set(mode='OBJECT')
    image = bpy.data.images.new('Atlas_' + name, size, size)
    image.colorspace_settings.name = 'sRGB'
    for slot in obj.material_slots:
        nodes = painted_material(slot.material, source_uv)
        target = nodes.new('ShaderNodeTexImage'); target.image = image; nodes.active = target
    bpy.ops.object.bake(type='EMIT', margin=6)
    if source_uv and source_uv in mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[source_uv])
    mesh.uv_layers['Atlas'].active_render = True
    TEX.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(TEX / (name + '.png')); image.file_format = 'PNG'; image.save()
    atlas_material(obj, name, image)


def atlas_material(obj, name, image):
    """Single G_<Name> material (Unity: Standard shader + Resources/EventProps/Tex/<Name>.png)."""
    m = bpy.data.materials.new('G_' + name)
    m.use_nodes = True
    tex = m.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = image
    m.node_tree.links.new(tex.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    obj.data.materials.clear(); obj.data.materials.append(m)


def game_model(name):
    source, size = GAME_MODELS[name]
    bpy.ops.import_scene.gltf(filepath=str(SOURCES / (source + '.glb')))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    obj = bpy.context.object
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    lo = Vector([min((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)])
    hi = Vector([max((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)])
    k = size / max(hi - lo)
    obj.scale = (k, k, k); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = (-(lo.x + hi.x) / 2 * k, -(lo.y + hi.y) / 2 * k, -lo.z * k)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    if len(obj.data.polygons) > 24000:
        mod = obj.modifiers.new('Decimate', 'DECIMATE'); mod.ratio = 24000 / len(obj.data.polygons)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    image = next(n.image for n in obj.material_slots[0].material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image
                 and n.image.colorspace_settings.name == 'sRGB')
    image.scale(1024, 1024)
    TEX.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(TEX / (name + '.png')); image.file_format = 'PNG'; image.save()
    atlas_material(obj, name, image)
    return obj


def export(name):
    reset()
    if name in GAME_MODELS:
        obj = game_model(name)
    else:
        BUILDERS[name]()
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        bpy.ops.object.select_all(action='DESELECT')
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        obj = bpy.context.object
        # Pivot at the authoring origin (ground, centre) so Unity placement matches the builder coordinates.
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        try:
            bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
        except Exception:
            pass
        bake_atlas(obj, name, 2048 if name in HIRES else 1024)
    obj.name = name
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    ASSETS.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(ASSETS / (name + '.fbx')), use_selection=True, object_types={'MESH'},
                             axis_forward='-Z', axis_up='Y', bake_anim=False, path_mode='STRIP',
                             use_mesh_modifiers=True, mesh_smooth_type='FACE')
    return obj


def preview(name, obj):
    """EEVEE preview from the game camera's direction (+X, -Y, above)."""
    scene = bpy.context.scene
    for o in list(scene.objects):
        if o.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(o)
    lo = Vector([min((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)])
    hi = Vector([max((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)])
    center, size = (lo + hi) / 2, (hi - lo).length
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scene.collection.objects.link(cam); scene.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = size * 1.05
    cam.location = center + Vector((.47, -.64, .6)).normalized() * (size * 3 + 5)
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = size * 10 + 50
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); sun.data.energy = 3
    sun.rotation_euler = (math.radians(50), 0, math.radians(30)); scene.collection.objects.link(sun)
    scene.world = scene.world or bpy.data.worlds.new('World')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (.6, .6, .6, 1); bg.inputs[1].default_value = .8
    scene.view_settings.view_transform = 'Standard'
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = 420
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(PREVIEWS / (name + '.png'))
    bpy.ops.render.render(write_still=True)


ALL = list(BUILDERS) + list(GAME_MODELS)


def main(args):
    wanted = [a for a in args if a in ALL] or ALL
    for prop in wanted:
        try:
            obj = export(prop)
            print('EVENT_PROP_BUILT', prop, flush=True)
            if '--no-preview' not in args:
                preview(prop, obj)
        except Exception as ex:  # keep going so one broken prop never blocks the batch
            import traceback
            traceback.print_exc()
            print('EVENT_PROP_FAILED', prop, repr(ex), flush=True)
    print('EVENT_PROPS_DONE', len(wanted), flush=True)


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
