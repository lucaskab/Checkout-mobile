"""Textured 3D-rendered art for the simulator mini-games (register and store mishaps), in the look of the
app's game-art icons: saturated glossy materials with real surface detail (wood grain, granite, tiles,
ribbed rubber, brushed metal, paper), soft studio light, transparent PNGs.

Run:  blender -b --factory-startup --python scripts/blender/build_ui_sprites.py [-- name ...]
Output: unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Game/<name>.png
        plus <name>.json with the normalized rects (x0, y0, x1, y1; origin bottom-left) of marked parts
        (screens, slots, sockets) so the UI can place live content over them.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Game'
FONT_PATH = ROOT / 'unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Fonts/Fredoka_700Bold.ttf'
R = math.radians


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c)


# ---------------------------------------------------------------- materials

_mats = {}


def _principled(m):
    return m.node_tree.nodes['Principled BSDF']


def mat(hex_color, rough=.32, metal=0.0, coat=.35, emit=0.0, alpha=1.0, trans=0.0):
    key = ('flat', hex_color, rough, metal, coat, emit, alpha, trans)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new('M_' + hex_color)
    m.use_nodes = True
    b = _principled(m)
    col = (*srgb(hex_color), 1)
    b.inputs['Base Color'].default_value = col
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = .12
    if emit:
        b.inputs['Emission Color'].default_value = col
        b.inputs['Emission Strength'].default_value = emit
    if trans:
        b.inputs['Transmission Weight'].default_value = trans
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    _mats[key] = m
    return m


def tex(kind, c1, c2, rough=.4, scale=1.0, bump=.25, metal=0.0, coat=.2, c3=None, stretch=(1, 1, 1)):
    """Procedural surface: wood, granite, tiles, ribs, brushed, paper, noise, checker, fabric."""
    key = ('tex', kind, c1, c2, c3, rough, scale, bump, metal, coat, stretch)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f'T_{kind}_{c1}')
    m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; L = nt.links
    b = _principled(m)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = .15
    coord = n.new('ShaderNodeTexCoord')
    mapping = n.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = [scale * s for s in stretch]
    L.new(coord.outputs['Object'], mapping.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    e = ramp.color_ramp.elements
    e[0].color = (*srgb(c1), 1); e[1].color = (*srgb(c2), 1)
    height = None
    if kind == 'wood':
        # Fine long grain: stretched noise bands plus a faint wave, low contrast.
        mapping.inputs['Scale'].default_value = (scale * 1.0, scale * .08, scale * 1.0) if stretch == (1, 1, 1) else [scale * s for s in stretch]
        w = n.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'X'
        w.inputs['Scale'].default_value = 7; w.inputs['Distortion'].default_value = 2.5; w.inputs['Detail'].default_value = 2
        w.inputs['Detail Scale'].default_value = 1.2
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 14; nz.inputs['Detail'].default_value = 10
        mix = n.new('ShaderNodeMath'); mix.operation = 'MULTIPLY_ADD'
        L.new(mapping.outputs['Vector'], w.inputs['Vector']); L.new(mapping.outputs['Vector'], nz.inputs['Vector'])
        L.new(nz.outputs['Fac'], mix.inputs[0]); mix.inputs[1].default_value = .6; L.new(w.outputs['Fac'], mix.inputs[2])
        clamp = n.new('ShaderNodeMath'); clamp.operation = 'MULTIPLY'; clamp.inputs[1].default_value = .62
        L.new(mix.outputs[0], clamp.inputs[0])
        L.new(clamp.outputs[0], ramp.inputs['Fac']); height = clamp.outputs[0]
        e[0].position = .2; e[1].position = .85
    elif kind == 'granite':
        v = n.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = 28
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 6
        L.new(mapping.outputs['Vector'], v.inputs['Vector']); L.new(mapping.outputs['Vector'], nz.inputs['Vector'])
        mix = n.new('ShaderNodeMix'); mix.data_type = 'FLOAT'; mix.inputs['Factor'].default_value = .55
        L.new(nz.outputs['Fac'], mix.inputs['A']); L.new(v.outputs['Distance'], mix.inputs['B'])
        L.new(mix.outputs['Result'], ramp.inputs['Fac']); height = v.outputs['Distance']
        e[0].position = .3; e[1].position = .75
        if c3:
            s = e.new(.9); s.color = (*srgb(c3), 1)
    elif kind == 'tiles':
        br = n.new('ShaderNodeTexBrick')
        br.inputs['Color1'].default_value = (*srgb(c1), 1); br.inputs['Color2'].default_value = (*srgb(c3 or c1), 1)
        br.inputs['Mortar'].default_value = (*srgb(c2), 1); br.inputs['Scale'].default_value = 1
        br.inputs['Mortar Size'].default_value = .03; br.inputs['Mortar Smooth'].default_value = .3
        br.inputs['Brick Width'].default_value = 1; br.inputs['Row Height'].default_value = 1
        br.offset = 0; br.squash = 1
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 18; nz.inputs['Detail'].default_value = 5
        L.new(mapping.outputs['Vector'], br.inputs['Vector']); L.new(mapping.outputs['Vector'], nz.inputs['Vector'])
        mul = n.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = .12
        L.new(br.outputs['Color'], mul.inputs['A']); L.new(nz.outputs['Color'], mul.inputs['B'])
        L.new(mul.outputs['Result'], b.inputs['Base Color'])
        inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
        L.new(br.outputs['Fac'], inv.inputs[1]); height = inv.outputs[0]
        ramp = None
    elif kind == 'ribs':
        w = n.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'X'; w.wave_profile = 'SIN'
        w.inputs['Scale'].default_value = 1; w.inputs['Distortion'].default_value = 0
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60
        L.new(mapping.outputs['Vector'], w.inputs['Vector']); L.new(mapping.outputs['Vector'], nz.inputs['Vector'])
        mix = n.new('ShaderNodeMath'); mix.operation = 'MULTIPLY_ADD'; L.new(nz.outputs['Fac'], mix.inputs[0]); mix.inputs[1].default_value = .15; L.new(w.outputs['Fac'], mix.inputs[2])
        L.new(mix.outputs[0], ramp.inputs['Fac']); height = w.outputs['Fac']
    elif kind == 'brushed':
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; nz.inputs['Detail'].default_value = 12
        mapping.inputs['Scale'].default_value = (scale * 1, scale * 90, scale * 1)
        L.new(mapping.outputs['Vector'], nz.inputs['Vector']); L.new(nz.outputs['Fac'], ramp.inputs['Fac']); height = nz.outputs['Fac']
        e[0].position = .35; e[1].position = .65
    elif kind in ('paper', 'noise', 'fabric', 'plastic'):
        nz = n.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = {'paper': 60, 'noise': 8, 'fabric': 120, 'plastic': 30}[kind]
        nz.inputs['Detail'].default_value = 8
        L.new(mapping.outputs['Vector'], nz.inputs['Vector']); L.new(nz.outputs['Fac'], ramp.inputs['Fac']); height = nz.outputs['Fac']
        e[0].position = .38; e[1].position = .68
    elif kind == 'checker':
        ck = n.new('ShaderNodeTexChecker'); ck.inputs['Scale'].default_value = 1
        ck.inputs['Color1'].default_value = (*srgb(c1), 1); ck.inputs['Color2'].default_value = (*srgb(c2), 1)
        L.new(mapping.outputs['Vector'], ck.inputs['Vector']); L.new(ck.outputs['Color'], b.inputs['Base Color'])
        ramp = None
    elif kind == 'gradient':
        g = n.new('ShaderNodeTexGradient'); g.gradient_type = 'LINEAR'
        L.new(mapping.outputs['Vector'], g.inputs['Vector']); L.new(g.outputs['Fac'], ramp.inputs['Fac'])
    if ramp is not None:
        L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    if height is not None and bump > 0:
        bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = .02
        L.new(height, bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    _mats[key] = m
    return m


# ---------------------------------------------------------------- geometry helpers

def finish(o, m, bev=.02, seg=4, smooth=True, subsurf=0):
    if bev > 0:
        mod = o.modifiers.new('Bevel', 'BEVEL'); mod.width = bev; mod.segments = seg; mod.limit_method = 'ANGLE'
    if subsurf:
        mod = o.modifiers.new('Sub', 'SUBSURF'); mod.levels = subsurf; mod.render_levels = subsurf
    o.data.materials.append(m)
    if smooth and hasattr(o.data, 'polygons'):
        for p in o.data.polygons:
            p.use_smooth = True
        try:
            mod = o.modifiers.new('Smooth', 'SMOOTH_BY_ANGLE')
        except Exception:
            pass
    return o


def box(size, loc, m, bev=.03, rot=(0, 0, 0), seg=4):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=[R(a) for a in rot])
    o = bpy.context.object
    o.scale = [s / 2 for s in size]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, m, min(bev, min(size) * .45), seg)


def cyl(r, depth, loc, m, rot=(0, 0, 0), v=48, bev=.01, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=[R(a) for a in rot], vertices=v)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=depth, location=loc, rotation=[R(a) for a in rot], vertices=v)
    return finish(bpy.context.object, m, bev, 3)


def sphere(r, loc, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=48, ring_count=24)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, m, 0)


def torus(Rr, r, loc, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=Rr, minor_radius=r, location=loc, rotation=[R(a) for a in rot], major_segments=64, minor_segments=16)
    return finish(bpy.context.object, m, 0)


def bar(a, b, r, m):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2, vertices=24)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return finish(o, m, 0)


def plane(size, loc, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(location=loc, rotation=[R(a) for a in rot])
    o = bpy.context.object
    o.scale = (size[0] / 2, size[1] / 2, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, m, 0, smooth=False)


_font = None


def text(body, loc, size, m, rot=(90, 0, 0), extrude=.012, bevel=.004, align='CENTER'):
    global _font
    if _font is None:
        try:
            _font = bpy.data.fonts.load(str(FONT_PATH))
        except Exception:
            _font = False
    bpy.ops.object.text_add(location=loc, rotation=[R(a) for a in rot])
    o = bpy.context.object
    o.data.body = body
    if _font:
        o.data.font = _font
    o.data.size = size; o.data.extrude = extrude; o.data.bevel_depth = bevel
    o.data.align_x = align; o.data.align_y = 'CENTER'
    o.data.materials.append(m)
    return o


MARKS = {}


def mark(label, o):
    MARKS[label] = o
    return o


def reset():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for item in list(block):
            block.remove(item)
    _mats.clear(); MARKS.clear()


def use_gpu(sc):
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for kind in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                devices = [d for d in prefs.devices if d.type == kind]
                if devices:
                    for d in prefs.devices:
                        d.use = d.type == kind
                    sc.cycles.device = 'GPU'
                    return kind
            except Exception:
                continue
    except Exception:
        pass
    sc.cycles.device = 'CPU'
    return 'CPU'


DEVICE = None


def studio(elev=22, yaw=-24, size=None, width=512, height=512, target=None, light=1.0, samples=64):
    """Orthographic camera fitted to the objects, soft key/fill/rim light, transparent film."""
    global DEVICE
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    objs = [o for o in sc.objects if o.type in ('MESH', 'FONT')]
    lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    center = Vector(target) if target else (lo + hi) / 2
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'
    e, y = R(elev), R(yaw)
    direction = Vector((math.sin(y) * math.cos(e), -math.cos(y) * math.cos(e), math.sin(e)))
    cam.location = center + direction * 40
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    extent = (hi - lo).length
    cam.data.ortho_scale = size or extent * 1.0
    cam.data.clip_end = 200
    sc.render.resolution_x, sc.render.resolution_y = width, height
    k = max(1.0, extent / 3.2)
    for name, energy, loc, sz in (('Key', 1000, (-4, -6, 8), 6), ('Fill', 320, (6, -5, 3), 8), ('Rim', 520, (2, 7, 6), 4), ('Top', 220, (0, 0, 10), 10)):
        lamp = bpy.data.lights.new(name, 'AREA'); lamp.energy = energy * k * k * light; lamp.size = sz * k
        lo_ = bpy.data.objects.new(name, lamp); sc.collection.objects.link(lo_)
        lo_.location = center + Vector(loc) * k
        lo_.rotation_euler = (center - lo_.location).to_track_quat('-Z', 'Y').to_euler()
    world = sc.world or bpy.data.worlds.new('World'); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes['Background']; bg.inputs[0].default_value = (1, .97, .92, 1); bg.inputs[1].default_value = .6
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    if DEVICE is None:
        DEVICE = use_gpu(sc)
        print('UI_SPRITE_DEVICE', DEVICE, flush=True)
    elif DEVICE != 'CPU':
        sc.cycles.device = 'GPU'
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'


def backdrop_studio(width, height, size, target, elev=90, yaw=0, light=1.0):
    studio(elev=elev, yaw=yaw, size=size, width=width, height=height, target=target, light=light, samples=96)
    bpy.context.scene.render.film_transparent = False


def projected_rects():
    sc = bpy.context.scene; cam = sc.camera
    out = {}
    for label, o in MARKS.items():
        xs, ys = [], []
        for c in o.bound_box:
            p = world_to_camera_view(sc, cam, o.matrix_world @ Vector(c))
            xs.append(p.x); ys.append(p.y)
        out[label] = [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]
    return out


# ---------------------------------------------------------------- palette

TEAL, TEAL_D, CREAM, WOOD, WOOD_D, RED, YELLOW, GREEN, INK = '188F86', '11655E', 'FFF1D8', 'D69C53', '9A6232', 'E15533', 'F2B03D', '5DA637', '2F3A40'


# ---------------------------------------------------------------- register: backdrop and fixtures

def reg_backdrop():
    # The checkout counter seen from the cashier: warm wooden planks, steel edge, teal front, tiled wall behind.
    tones = [('D9A15C', 'A8703C'), ('D29856', '9C6636'), ('DEA863', 'B07A44')]
    for i in range(-9, 10):
        c1, c2 = tones[i % 3]
        box((1.04, 8.4, .3), (i * 1.06, -.2, 0), tex('wood', c1, c2, rough=.35, scale=.55 + (i % 4) * .05, bump=.35, coat=.45), .03)
    box((21, .4, .3), (0, -4.55, .05), tex('brushed', 'D5DCDE', '9AA6AA', rough=.28, metal=.9, scale=.5), .08)
    box((21, .4, 3.0), (0, -4.9, -1.5), tex('plastic', TEAL, TEAL_D, rough=.35, scale=1.5, bump=.05), .06)
    for i in range(-10, 11):
        box((.1, .05, 2.6), (i * 1.0, -5.12, -1.5), mat(TEAL_D, .4), .01)
    box((21, .3, 4), (0, 4.1, 2.0), tex('tiles', 'F4F1EA', 'C8C2B6', c3='DDEFEA', scale=1.4, bump=.25, rough=.2, coat=.6), .02, rot=(0, 0, 0))
    box((21, .5, .35), (0, 3.95, .15), tex('wood', WOOD, WOOD_D, scale=1.2, bump=.2, stretch=(.1, 1, 1)), .06)
    backdrop_studio(1600, 900, 16, (0, -.3, 0), elev=68)


def belt():
    rubber = tex('ribs', '2B3033', '3D4448', rough=.8, scale=4, bump=.6, coat=.05)
    box((8.0, 1.4, .25), (0, 0, .2), rubber, .05)
    frame = tex('brushed', 'C5CDD0', '8E9A9E', rough=.28, metal=.9, scale=.4)
    for yy in (-.82, .82):
        box((8.3, .24, .45), (0, yy, .22), frame, .07)
    for x in (-4.05, 4.05):
        cyl(.26, 1.64, (x, 0, .2), frame, rot=(90, 0, 0))
    box((8.6, 2.0, .2), (0, 0, -.05), mat(TEAL, .35), .06)
    mark('surface', plane((8.0, 1.4), (0, 0, .33), rubber))
    studio(elev=90, yaw=0, width=1024, height=256, size=8.9)


def belt_tile():
    # Seamless ribbed rubber (period divides the tile) for the running belt surface.
    m = tex('ribs', '262B2E', '41494D', rough=.75, scale=4, bump=.7, coat=.05)
    plane((4, 1), (0, 0, 0), m)
    backdrop_studio(512, 128, 4, (0, 0, 0))


def scanner_bed():
    body = tex('plastic', '2E3437', '3A4145', rough=.4, scale=1, bump=.05)
    box((2.2, 1.8, .4), (0, 0, .2), body, .18)
    box((1.8, 1.4, .08), (0, 0, .42), tex('brushed', 'B8C2C5', '8E9A9E', metal=.9, rough=.3, scale=.5), .03)
    mark('glass', box((1.5, 1.1, .06), (0, 0, .47), mat('4A1B18', .04, coat=1, trans=.1), .02))
    for i in range(-5, 6):
        box((.02, 1.0, .01), (i * .12, 0, .505), mat('7E2A22', .1, emit=.8), 0)
    studio(elev=90, yaw=0, width=512, height=420, size=2.4)


def pos_terminal():
    body = tex('plastic', '394245', '48524F', rough=.35, scale=1, bump=.04)
    box((.6, .5, .1), (0, 0, .05), body, .04)
    bar((0, .05, .1), (0, .15, .9), .07, tex('brushed', 'B8C2C5', '8E9A9E', metal=.9, rough=.3, scale=.5))
    box((2.4, .22, 1.5), (0, .1, 1.35), body, .12)
    box((2.2, .05, 1.3), (0, -.02, 1.35), mat('20292C', .2), .04)
    mark('screen', box((2.0, .04, 1.08), (0, -.05, 1.39), mat('BFE3B3', .25, emit=.6, coat=.8), .03))
    text('CAIXA 01', (0, -.05, 2.04), .14, mat('E9F5E5', .3, emit=.8), extrude=.005, bevel=0)
    box((2.3, .3, .14), (0, .05, 2.13), mat(TEAL, .35), .06)
    studio(elev=6, yaw=0, width=640, height=512)


def card_machine():
    body = tex('plastic', '30383B', '404A4D', rough=.32, scale=1, bump=.05)
    box((1.2, .32, 2.1), (0, 0, 1.05), body, .2)
    box((1.26, .38, .45), (0, .02, 2.05), mat(TEAL, .3), .16)
    mark('slot', box((.9, .12, .05), (0, 0, 2.29), mat('0C0F10', .8), .02))
    box((.95, .06, .62), (0, -.17, 1.55), mat('161C1E', .15, coat=1), .05)
    mark('screen', box((.85, .04, .52), (0, -.2, 1.55), mat('A6DCCF', .3, emit=.45, coat=.8), .03))
    labels = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'X', '0', 'OK']
    colors = ['DDE3E4'] * 9 + [RED, 'DDE3E4', GREEN]
    for i, (lab, c) in enumerate(zip(labels, colors)):
        x, z = (i % 3 - 1) * .32, 1.02 - (i // 3) * .2
        box((.26, .08, .15), (x, -.19, z), mat(c, .35, coat=.6), .05)
        text(lab, (x, -.24, z), .09 if len(lab) < 2 else .07, mat('2F3A40' if c == 'DDE3E4' else 'FFFFFF', .4), extrude=.003, bevel=0)
    mark('led', sphere(.05, (.46, -.18, 1.93), mat('3A4448', .2)))
    studio(elev=8, yaw=0, width=384, height=640)


def credit_card(color, color2, name):
    def build():
        box((1.7, .05, 1.08), (0, 0, .54), tex('gradient', color, color2, rough=.22, scale=.6, bump=0, coat=1), .08)
        chip = tex('brushed', 'F3C95C', 'C8962E', metal=1, rough=.25, scale=.3)
        box((.3, .03, .24), (-.52, -.03, .68), chip, .04)
        for zz in (.64, .72):
            box((.3, .01, .01), (-.52, -.047, zz), mat('A87A24', .3, .8), 0)
        text('4821  0093  7710  2256', (-.05, -.035, .38), .1, mat('FFFFFF', .3, coat=.4), extrude=.006, bevel=.002)
        text('CLIENTE', (-.55, -.035, .18), .07, mat('FFFFFF', .3), extrude=.004, bevel=0, align='LEFT')
        cyl(.13, .02, (.62, -.035, .2), mat('F2B03D', .3, .3), rot=(90, 0, 0))
        cyl(.13, .02, (.48, -.04, .2), mat('E15533', .3), rot=(90, 0, 0))
        for i in range(3):
            torus(.07 + i * .05, .012, (.62, -.035, .78), mat('FFFFFF', .3), rot=(90, 0, 0))
        studio(elev=6, yaw=0, width=512, height=336)
    build.__name__ = name
    return build


def cash_tray():
    # Open register drawer seen from above: worn steel tray with five note slots and coin cups.
    steel = tex('brushed', 'B7C0C3', '8A9598', metal=.85, rough=.35, scale=.4)
    box((4.2, 2.6, .5), (0, 0, .25), tex('plastic', '2F383B', '3C464A', rough=.45, scale=1, bump=.05), .1)
    box((4.0, 2.4, .1), (0, 0, .46), steel, .03)
    for i in range(5):
        x = -1.6 + i * .8
        mark(f'bin{i}', box((.7, 1.3, .12), (x, .45, .5), mat('1C2224', .6), .04))
        box((.05, 1.3, .25), (x + .38, .45, .6), steel, .01)
        bar((x, -.1, .7), (x, 1.0, .7), .03, steel)
    for i in range(5):
        x = -1.6 + i * .8
        mark(f'cup{i}', cyl(.3, .12, (x, -.75, .5), mat('1C2224', .6), bev=.03))
    box((4.2, .35, .6), (0, -1.45, .3), mat(TEAL, .35), .08)
    box((1.2, .15, .15), (0, -1.65, .42), tex('brushed', 'F0D4A0', 'C9A36A', metal=.8, rough=.3, scale=.3), .05)
    studio(elev=90, yaw=0, width=768, height=512, size=4.4)


def cash_drawer_closed():
    box((4.2, 1.2, .9), (0, 0, .45), tex('plastic', '2F383B', '3C464A', rough=.45, scale=1, bump=.05), .12)
    box((4.0, .1, .6), (0, -.6, .45), mat(TEAL, .35), .08)
    box((1.2, .15, .15), (0, -.68, .52), tex('brushed', 'F0D4A0', 'C9A36A', metal=.8, rough=.3, scale=.3), .05)
    cyl(.07, .1, (1.6, -.66, .7), mat('E9B345', .25, .8), rot=(90, 0, 0))
    studio(elev=22, yaw=0, width=768, height=256)


NOTE_COLORS = {100: ('4F8FCB', 'A9CFF0'), 50: ('D98E3A', 'F6CD8C'), 20: ('D8B23C', 'F6E391'), 10: ('C9605A', 'F2AFA6'),
               5: ('8A73BF', 'CEC0EE'), 2: ('4FA79A', 'A9DCD3')}


def banknote(value):
    def build():
        c1, c2 = NOTE_COLORS[value]
        paper = tex('paper', c2, c1, rough=.6, scale=1, bump=.12, coat=0)
        box((2.4, .03, 1.15), (0, 0, .58), paper, .03)
        box((2.2, .01, .95), (0, -.02, .58), tex('ribs', c2, c1, rough=.6, scale=10, bump=.03, coat=0), .01)  # fine engraved lines
        box((1.0, .012, .95), (-.55, -.025, .58), tex('paper', c2, c2, rough=.6, scale=1, bump=.08, coat=0), .01)
        cyl(.36, .01, (.55, -.03, .58), tex('paper', 'FFFFFF', c2, rough=.5, scale=1, bump=.1, coat=0), rot=(90, 0, 0))
        torus(.36, .03, (.55, -.035, .58), mat(c1, .5), rot=(90, 0, 0))
        cyl(.2, .03, (.55, -.04, .58), mat(c1, .45, coat=.3), rot=(90, 0, 0), v=5)
        text(str(value), (-.55, -.04, .58), .52, mat('FFFFFF', .4), extrude=.008, bevel=.004)
        text(str(value), (.95, -.035, .95), .16, mat(c1, .4), extrude=.004, bevel=0)
        text('REAIS', (-.55, -.035, .22), .12, mat(c1, .5), extrude=.003, bevel=0)
        studio(elev=6, yaw=0, width=480, height=240)
    build.__name__ = f'note_{value}'
    return build


def coin(value, gold):
    def build():
        a, b = ('F3C95C', 'C8962E') if gold else ('D5DCDE', '9AA6AA')
        metal = tex('noise', a, b, metal=1, rough=.22, scale=1, bump=.05)
        cyl(.6, .12, (0, 0, .06), metal, v=64, bev=.03)
        torus(.54, .045, (0, 0, .13), mat(b, .25, 1))
        text(str(value), (0, 0, .15), .62, mat(b, .3, 1), rot=(0, 0, 0), extrude=.03, bevel=.01)
        studio(elev=90, yaw=0, width=256, height=256, size=1.3)
    build.__name__ = f'coin_{value}'
    return build


def shopping_bag():
    paper = tex('paper', 'D39A61', 'B77B45', rough=.8, scale=1, bump=.2, coat=0)
    box((1.3, .8, 1.5), (0, 0, .75), paper, .02)
    box((1.32, .82, .14), (0, 0, 1.46), tex('paper', 'B77B45', '9E6636', rough=.8, scale=1, bump=.2, coat=0), .02)
    torus(.3, .04, (0, -.4, 1.62), mat('8B5A3C', .6), rot=(90, 0, 0))
    torus(.3, .04, (0, .4, 1.62), mat('8B5A3C', .6), rot=(90, 0, 0))
    cyl(.28, .02, (0, -.41, .82), mat(GREEN, .45), rot=(90, 0, 0))
    text('$', (0, -.43, .82), .34, mat('FFFFFF', .4), extrude=.01)
    mark('mouth', box((1.2, .7, .02), (0, 0, 1.5), mat('6B4A2E', .9), 0))
    studio(elev=24, yaw=-20)


def receipt_printer():
    body = tex('plastic', 'E7E1D4', 'D5CEBF', rough=.35, scale=1, bump=.04)
    box((1.4, 1.2, .8), (0, 0, .4), body, .2)
    box((1.3, .8, .12), (0, .15, .82), mat('C9C1B0', .4), .06)
    mark('slot', box((1.0, .08, .06), (0, -.28, .86), mat('2B3134', .6), .02))
    cyl(.06, .05, (.48, -.6, .62), mat(GREEN, .2, emit=3), rot=(90, 0, 0))
    studio(elev=30, yaw=0)


def keypad_panel():
    # Big number pad the player keys the total on (buttons overlaid in UI on the marked spots).
    body = tex('plastic', '3A4346', '454F53', rough=.35, scale=1, bump=.04)
    box((3.0, .3, 3.6), (0, 0, 1.8), body, .25)
    box((2.7, .05, .7), (0, -.16, 3.05), mat('161C1E', .15, coat=1), .06)
    mark('screen', box((2.55, .04, .56), (0, -.19, 3.05), mat('BFE3B3', .25, emit=.5, coat=.8), .04))
    labels = ['7', '8', '9', '4', '5', '6', '1', '2', '3', 'C', '0', 'OK']
    for i, lab in enumerate(labels):
        x, z = (i % 3 - 1) * .86, 2.25 - (i // 3) * .6
        c = RED if lab == 'C' else GREEN if lab == 'OK' else 'EEF1F1'
        box((.8, .1, .56), (x, -.16, z), mat('2B3336', .6), .08)  # key wells; caps are live UI sprites
        k = mark('key_' + lab, box((.74, .16, .5), (x, -.2, z), mat(c, .35), .1))
        k.hide_render = True
    studio(elev=4, yaw=0, width=560, height=640)


def key_cap(color, name, dark):
    def build():
        box((.74, .16, .5), (0, 0, 0), mat(color, .35, coat=.7), .1)
        box((.62, .02, .36), (0, -.085, .02), mat(dark, .4), .05)
        studio(elev=4, yaw=0, width=256, height=180, size=.8)
    build.__name__ = name
    return build


# ---------------------------------------------------------------- mishaps

def floor_backdrop():
    for i in range(-12, 13):
        for j in range(-8, 6):
            c = ('F3EDE0', 'E7DFCE') if (i + j) % 2 == 0 else ('BFE3DC', 'A8D6CD')
            box((.98, .98, .1), (i * 1.0, j * 1.0, 0), tex('noise', c[0], c[1], rough=.18, scale=1, bump=.05, coat=.8), .03)
    plane((26, 16), (0, -1, -.06), mat('A89B86', .7))
    box((24, 1.8, .6), (0, 6.2, .3), tex('wood', WOOD, WOOD_D, scale=1.2, bump=.2, stretch=(.1, 1, 1)), .08)
    colors = ['E15533', 'F2B03D', '2E8CAE', '5DA637', '8B5C9E', 'D9716A', '45B7D0']
    for i in range(-12, 13):
        c = colors[i % len(colors)]
        box((.8, .8, 1.1), (i * 1.0, 6.4, 1.15), tex('plastic', c, c, rough=.35, scale=1, bump=.03), .08)
        box((.6, .02, .3), (i * 1.0, 5.99, 1.2), mat('FFFFFF', .4), .02)
    box((24, .25, .7), (0, 5.3, .35), mat(TEAL, .35), .06)
    backdrop_studio(1600, 900, 17, (0, .6, 0), elev=58, light=.9)


def wall_backdrop():
    plane((22, 7), (0, 0, 2.5), tex('tiles', 'F4F1EA', 'C8C2B6', c3='E8F3F0', scale=1.1, bump=.25, rough=.2, coat=.6), rot=(90, 0, 0))
    plane((22, 3.2), (0, -.05, -2.6), tex('plastic', TEAL, TEAL_D, rough=.35, scale=2, bump=.04), rot=(90, 0, 0))
    for i in range(-11, 12):
        box((.08, .06, 3.0), (i * 1.0, -.1, -2.6), mat(TEAL_D, .4), .01)
    box((22, .35, .3), (0, -.15, -1.0), tex('wood', WOOD, WOOD_D, scale=1.2, bump=.2, stretch=(.1, 1, 1)), .06)
    box((22, .3, .5), (0, -.15, -4.15), tex('wood', WOOD_D, '7A4A26', scale=1.2, bump=.2, stretch=(.1, 1, 1)), .06)
    plane((22, 5), (0, -2.6, -4.4), tex('noise', 'E7DFCE', 'D3C9B4', rough=.2, scale=1, bump=.05, coat=.8))
    backdrop_studio(1600, 900, 18, (0, 0, 0), elev=4, light=.9)


def ceiling_backdrop():
    panels = tex('tiles', 'EDEAE3', '9AA0A2', c3='E6E3DA', scale=.5, bump=.3, rough=.6, coat=.1)
    plane((22, 14), (0, 0, 0), panels)
    for x in (-6, 6):
        box((3.8, 1.2, .1), (x, 2.5, .05), tex('brushed', 'D5DCDE', 'A9B3B6', metal=.7, rough=.35, scale=.4), .04)
        for i in range(8):
            box((3.4, .05, .04), (x, 2.05 + i * .13, .12), mat('6F7A7E', .5), 0)
    backdrop_studio(1600, 900, 18, (0, 0, 0), elev=90, light=.8)


def mop():
    bar((0, 0, .45), (0, 0, 3.6), .07, tex('wood', WOOD, WOOD_D, scale=6, bump=.1, stretch=(1, 1, .1)))
    box((1.1, .32, .24), (0, 0, .5), mat('E9A52E', .4, coat=.6), .07)
    cyl(.09, .1, (0, 0, 3.62), mat(RED, .4))
    strand = tex('fabric', 'F7F0E2', 'D8CDB9', rough=.95, scale=1, bump=.4, coat=0)
    for i in range(17):
        x = -.56 + i * .07
        for j, yy in enumerate((-.1, 0, .1)):
            bar((x, yy, .42), (x * 1.25 + math.sin(i * 1.7 + j) * .12, yy * 3 + math.cos(i + j) * .06, -.45 - (i * 7 + j * 3) % 5 * .04), .05, strand)
    studio(elev=12, yaw=-10)


def bucket():
    cyl(.8, 1.1, (0, 0, .55), mat('F4BA42', .35, coat=.6), r2=.62, bev=.03)
    cyl(.72, .05, (0, 0, 1.02), mat('6FC0DE', .03, coat=1, trans=.3))
    for i in range(6):
        sphere(.07 + (i % 3) * .03, (math.cos(i) * .4, math.sin(i * 1.3) * .3, 1.06), mat('FFFFFF', .1, coat=1, trans=.5))
    torus(.78, .04, (0, 0, 1.1), tex('brushed', 'C5CDD0', '8E9A9E', metal=.9, rough=.3, scale=.4), rot=(0, 90, 0))
    studio(elev=24, yaw=-20)


def puddle():
    water = mat('6CB7E0', .02, coat=1, trans=.25)
    for x, y, r in ((0, 0, 1.3), (1.0, .5, .75), (-1.1, -.4, .7), (.7, -.75, .55), (-.5, .85, .5), (1.7, -.1, .35)):
        o = cyl(r, .06, (x, y, .03), water, v=64, bev=.03)
        o.scale = (1, .8, 1)
    for x, y, r in ((2.1, .5, .12), (-1.9, .5, .1), (.2, -1.25, .09), (-1.4, -1.0, .07)):
        sphere(r, (x, y, .04), water, (1, 1, .45))
    studio(elev=62, yaw=0, width=768, height=512)


def dirt_stain():
    m = mat('B7925E', .8, coat=0, alpha=1)
    for x, y, r in ((0, 0, .9), (.6, .3, .5), (-.6, -.3, .45), (.3, -.5, .35)):
        o = cyl(r, .01, (x, y, 0), m, v=40, bev=0)
    studio(elev=62, yaw=0, width=384, height=256)


def wet_sign():
    yellow = mat('F4BA42', .35, coat=.6)
    for s in (-1, 1):
        box((1.0, .08, 1.9), (0, s * .32, 1.0), yellow, .06, rot=(s * 12, 0, 0))
    bar((-.45, 0, 1.9), (.45, 0, 1.9), .05, mat('2F3A40', .4))
    text('!', (0, -.48, 1.3), .7, mat('2F3A40', .4), rot=(78, 0, 0), extrude=.02)
    text('PISO\nMOLHADO', (0, -.43, .55), .16, mat('2F3A40', .4), rot=(78, 0, 0), extrude=.01, bevel=0)
    studio(elev=12, yaw=-24)


def soap_bubble():
    for x, y, r in ((0, 0, .5), (.55, .25, .3), (-.45, .3, .25), (.2, -.45, .2)):
        sphere(r, (x, 0, y), mat('E6F7FF', .02, coat=1, trans=.6))
    studio(elev=0, yaw=0, width=128, height=128)


def sparkle():
    m = mat('FFF3B0', .2, emit=4)
    for a in (0, 90):
        box((.18, .18, 1.6), (0, 0, 0), m, .08, rot=(0, a, 0))
    for a in (45, 135):
        box((.1, .1, .9), (0, 0, 0), m, .04, rot=(0, a, 0))
    studio(elev=0, yaw=0, width=128, height=128)


def freezer_unit():
    white = tex('plastic', 'F4F7F8', 'E1E7E9', rough=.28, scale=1, bump=.03)
    box((4.2, 1.4, 5.4), (0, 0, 2.7), white, .2)
    for x in (-1.02, 1.02):
        box((1.9, .1, 3.3), (x, -.72, 3.45), mat('DCE8EC', .2, coat=.4), .08)
        box((1.6, .06, 3.0), (x, -.76, 3.45), mat('A9D8E8', .03, coat=1, trans=.35), .04)
        for r_ in range(4):
            for c_ in range(3):
                col = ['E15533', 'F2B03D', '2E8CAE', '5DA637', 'FFFFFF'][(r_ * 3 + c_ + (x > 0)) % 5]
                box((.36, .3, .5), (x - .45 + c_ * .45, -.5, 2.2 + r_ * .8), mat(col, .4), .05)
        bar((x + (.75 if x < 0 else -.75), -.85, 2.6), (x + (.75 if x < 0 else -.75), -.85, 4.3), .05, tex('brushed', 'D5DCDE', 'A9B3B6', metal=.9, rough=.3, scale=.4))
    box((4.0, .1, .5), (0, -.72, 5.25), mat(TEAL, .35), .06)
    text('FREEZER', (0, -.78, 5.25), .26, mat('FFFFFF', .3), extrude=.01)
    mark('led', sphere(.12, (1.7, -.78, 5.25), mat('3A4448', .2)))
    # Open service bay at the bottom (fan and bolts are placed by the UI over it).
    mark('bay', box((3.6, .1, 1.35), (0, -.68, .95), mat('1E2426', .7), .06))
    for i in range(12):
        box((3.3, .02, .03), (0, -.735, .4 + i * .1), mat('2E3639', .6), 0)
    studio(elev=4, yaw=0, width=640, height=820)


def service_cover():
    steel = tex('brushed', 'C9D1D3', '9AA6AA', metal=.85, rough=.32, scale=.35)
    box((3.6, .1, 1.35), (0, 0, 0), steel, .06)
    for i in range(7):
        box((2.6, .03, .06), (0, -.06, -.45 + i * .15), mat('6F7A7E', .5), .01)
    for x, z in ((-1.6, .5), (1.6, .5), (-1.6, -.5), (1.6, -.5)):
        cyl(.06, .04, (x, -.07, z), mat('8E9A9E', .3, .9), rot=(90, 0, 0))
    studio(elev=4, yaw=0, width=640, height=256, size=3.7)


def fan():
    hub = mat('2B3134', .4)
    cyl(.22, .15, (0, 0, 0), hub, rot=(90, 0, 0))
    cyl(.08, .05, (0, -.1, 0), mat(RED, .3), rot=(90, 0, 0))
    torus(1.0, .05, (0, 0, 0), tex('brushed', 'C5CDD0', '8E9A9E', metal=.9, rough=.3, scale=.4), rot=(90, 0, 0))
    for i in range(5):
        a = i * 72
        o = box((.3, .04, .85), (math.cos(R(a)) * .55, 0, math.sin(R(a)) * .55), mat('45B7D0', .3, coat=.7), .1, rot=(0, -a + 90, 22))
    studio(elev=0, yaw=0, width=320, height=320, size=2.2)


def bolt():
    metal = tex('brushed', 'D3DCDA', 'A2AEAC', metal=1, rough=.25, scale=.3)
    cyl(.5, .3, (0, 0, .15), metal, v=6, bev=.04)
    cyl(.34, .08, (0, 0, .32), metal, v=48, bev=.02)
    box((.6, .1, .1), (0, 0, .36), mat('3A4448', .5), .02)
    studio(elev=90, yaw=0, width=160, height=160, size=1.1)


def spare_part():
    # New fan motor in its box: copper coils, steel shell.
    copper = tex('brushed', 'E89A55', 'B8662B', metal=1, rough=.3, scale=.3)
    cyl(.55, 1.0, (0, 0, .7), tex('brushed', 'C5CDD0', '8E9A9E', metal=.9, rough=.3, scale=.4), rot=(0, 90, 0))
    for i in range(6):
        torus(.5, .05, (-.4 + i * .16, 0, .7), copper, rot=(0, 90, 0))
    cyl(.12, .5, (.7, 0, .7), mat('8E9A9E', .3, .9), rot=(0, 90, 0))
    box((2.0, 1.4, .25), (0, 0, .12), tex('paper', 'D3A56B', 'B8864E', rough=.8, scale=1, bump=.15, coat=0), .03)
    studio(elev=28, yaw=-24)


def bulb(state):
    def build():
        if state == 'on':
            glass = mat('FFE27A', .05, emit=9)
        elif state == 'dead':
            glass = mat('8E8A80', .1, coat=1, trans=.2)
        else:
            glass = mat('E6EAE6', .04, coat=1, trans=.45)
        sphere(.8, (0, 0, 1.45), glass, (1, 1, 1.12))
        if state != 'on':
            bar((-.2, 0, 1.0), (-.12, 0, 1.55), .02, mat('6F6A60', .5))
            bar((.2, 0, 1.0), (.12, 0, 1.55), .02, mat('6F6A60', .5))
            bar((-.12, 0, 1.55), (.12, 0, 1.55), .015, mat('3A342E' if state == 'dead' else 'B08850', .5))
        if state == 'dead':
            sphere(.35, (.2, -.55, 1.8), mat('3A342E', .6), (1.2, .2, 1))
        metal = tex('brushed', 'C9D1D3', '9AA6AA', metal=.95, rough=.3, scale=.3)
        cyl(.42, .62, (0, 0, .6), metal, bev=.02)
        for z in (.42, .58, .74):
            torus(.43, .035, (0, 0, z), metal)
        cyl(.15, .12, (0, 0, .25), mat('3A342E', .5))
        studio(elev=6, yaw=0, width=256, height=320)
    build.__name__ = 'bulb_' + state
    return build


def pendant_lamp():
    bar((0, 0, 2.5), (0, 0, 4.2), .05, mat('2F3A40', .4))
    cyl(1.3, 1.0, (0, 0, 1.9), tex('plastic', TEAL, TEAL_D, rough=.3, scale=1, bump=.04), r2=.35, bev=.03)
    cyl(1.22, .04, (0, 0, 1.4), mat('F4F1EA', .5), bev=0)
    mark('socket', cyl(.3, .4, (0, 0, 1.25), tex('brushed', 'C9D1D3', '9AA6AA', metal=.9, rough=.3, scale=.3)))
    studio(elev=8, yaw=0, width=420, height=640)


def bulb_box():
    card = tex('paper', 'F4E0B8', 'D9C08E', rough=.8, scale=1, bump=.15, coat=0)
    box((1.4, 1.0, 1.2), (0, 0, .6), card, .03)
    box((1.42, 1.02, .25), (0, 0, 1.0), mat(YELLOW, .5, coat=0), .02)
    text('LED', (0, -.52, .55), .3, mat(TEAL, .5), extrude=.01)
    studio(elev=22, yaw=-24)


def shelf_unit():
    wood = tex('wood', WOOD, WOOD_D, scale=1.0, bump=.2, stretch=(.1, 1, 1))
    box((6.0, .3, 4.4), (0, .8, 2.2), tex('plastic', 'E8E1D2', 'D8CFBD', rough=.5, scale=1, bump=.05), .1)
    box((6.2, 1.8, .3), (0, 0, 1.3), wood, .08)
    box((6.2, 1.8, .3), (0, 0, 3.6), wood, .08)
    for x in (-3.05, 3.05):
        box((.3, 2.0, 4.6), (x, .1, 2.3), mat(TEAL, .35), .08)
    rail = tex('brushed', 'D5DCDE', 'A9B3B6', metal=.9, rough=.3, scale=.4)
    box((6.0, .2, .5), (0, -.95, 1.2), rail, .05)
    mark('holder', box((1.6, .05, .42), (0, -1.06, 1.2), mat('F7F4EC', .4), .03))
    mark('spot', box((2.4, .4, 2.0), (0, 0, 2.45), mat('000000', 1, alpha=0), 0))
    studio(elev=6, yaw=0, width=900, height=700, size=6.8)
    MARKS['spot'].hide_render = True


def price_tag(color, name):
    def build():
        box((1.6, .06, .8), (0, 0, .4), tex('plastic', color, color, rough=.3, scale=1, bump=.03, coat=.6), .08)
        box((1.5, .01, .7), (0, -.035, .4), mat('FFFFFF', .4, alpha=1), .05).scale = (1, 1, 1)
        box((1.5, .02, .18), (0, -.04, .66), mat(color, .35), .02)
        text('R$', (-.52, -.05, .32), .18, mat('2F3A40', .4), extrude=.004, bevel=0)
        mark('value', box((.95, .01, .42), (.18, -.045, .33), mat('FFFFFF', .4), 0))
        studio(elev=4, yaw=0, width=400, height=210, size=1.72)
    build.__name__ = name
    return build


def hand_pointer():
    # Cartoon glove with the index finger up (the UI rotates it), for the "do this" ghost hint.
    glove = tex('plastic', 'FFFFFF', 'EEF1F1', rough=.35, scale=1, bump=.03)
    box((.9, .5, .9), (0, 0, 0), glove, .24)
    cyl(.15, 1.0, (-.25, 0, .85), glove, bev=.07)
    sphere(.16, (-.25, 0, 1.35), glove)
    for x in (.02, .24):
        sphere(.19, (x, -.12, .45), glove, (1, 1.1, 1))
    cyl(.14, .55, (.52, 0, .05), glove, rot=(0, 50, 0), bev=.06)
    box((1.0, .56, .3), (0, 0, -.55), mat(TEAL, .35), .1)
    studio(elev=0, yaw=0, width=256, height=256)


def change_dish():
    cyl(1.2, .18, (0, 0, .09), tex('plastic', TEAL, TEAL_D, rough=.3, scale=1, bump=.04), bev=.08, v=64)
    cyl(1.0, .05, (0, 0, .17), tex('ribs', '0F4F49', '1B6D65', rough=.7, scale=6, bump=.4, coat=0), bev=.02, v=64)
    studio(elev=62, yaw=0, width=420, height=300)


def emote(kind):
    def build():
        if kind == 'heart':
            m = mat('F0567A', .2, coat=1)
            sphere(.5, (-.33, 0, .2), m); sphere(.5, (.33, 0, .2), m)
            box((.72, .72, .72), (0, 0, -.25), m, .25, rot=(0, 45, 0))
        elif kind == 'angry':
            text('!', (0, 0, 0), 1.6, mat('E13B2E', .25, coat=1), extrude=.15, bevel=.04)
        elif kind == 'sweat':
            m = mat('7CC7EA', .05, coat=1, trans=.3)
            sphere(.45, (0, 0, 0), m)
            cyl(.44, .7, (0, 0, .38), m, r2=0.0, bev=0)
        elif kind == 'question':
            text('?', (0, 0, 0), 1.4, mat(TEAL, .3, coat=.8), extrude=.12, bevel=.03)
        studio(elev=6, yaw=-10, width=192, height=192)
    build.__name__ = 'emote_' + kind
    return build


# ---------------------------------------------------------------- cooler short circuit (wiring puzzle)

def chest_freezer():
    # Ice cream chest freezer: white body, glass sliding lids over colourful tubs, service grille on the side.
    white = tex('plastic', 'F6F8F9', 'E3E9EB', rough=.26, scale=1, bump=.03)
    box((4.4, 2.0, 1.8), (0, 0, .9), white, .18)
    box((4.5, 2.1, .3), (0, 0, .15), mat(TEAL, .35), .1)
    box((3.0, .06, .8), (.3, -1.02, .95), mat('F48FB1', .35, coat=.6), .08)
    text('SORVETES', (.3, -1.06, .98), .3, mat('FFFFFF', .3), extrude=.01)
    steel = tex('brushed', 'D5DCDE', 'A9B3B6', metal=.9, rough=.3, scale=.4)
    box((4.3, 1.9, .12), (0, 0, 1.86), steel, .05)
    colors = ['F8BBD0', 'FFF59D', 'A5D6A7', '8D6E63', 'FFFFFF', 'CE93D8', 'FFCC80', '90CAF9']
    for i in range(4):
        for j in range(2):
            c = colors[(i * 2 + j) % len(colors)]
            cyl(.38, .5, (-1.5 + i * 1.0, -.42 + j * .84, 1.62), mat(c, .5), bev=.03)
            sphere(.33, (-1.5 + i * 1.0, -.42 + j * .84, 1.9), mat(c, .6), (1, 1, .45))
    glass = mat('CFEFF7', .02, coat=1, alpha=.28)
    box((2.1, 1.8, .06), (-1.05, 0, 2.02), glass, .03)
    box((2.1, 1.8, .06), (1.05, 0, 2.08), glass, .03)
    bar((-1.05, -.9, 2.1), (-1.05, .9, 2.1), .03, steel)
    mark('panel', box((.08, 1.2, .9), (-2.22, .2, .75), mat('3A4448', .5), .05))
    for i in range(6):
        box((.03, 1.0, .06), (-2.27, .2, .45 + i * .12), mat('222A2D', .6), .01)
    lid = mark('lid', box((4.2, 1.8, .02), (0, 0, 2.12), mat('000000', 1, alpha=0), 0))
    lid.hide_render = True
    studio(elev=28, yaw=-28, width=720, height=560)


def drinks_cooler():
    # Upright drinks fridge: glass door with bottles and cans, lit header, service grille at the bottom.
    white = tex('plastic', 'F6F8F9', 'E3E9EB', rough=.26, scale=1, bump=.03)
    box((2.4, 1.6, 5.0), (0, 0, 2.5), white, .15)
    box((2.3, .2, .6), (0, -.78, 4.6), mat(TEAL, .3, emit=.3), .08)
    text('GELADO', (0, -.9, 4.6), .32, mat('FFFFFF', .3, emit=1.5), extrude=.01)
    box((2.1, .08, 3.5), (0, -.78, 2.45), mat('DCE8EC', .2, coat=.4), .08)
    box((1.9, .05, 3.3), (0, -.83, 2.45), mat('BFEFFF', .02, coat=1, alpha=.22), .04)
    box((2.0, .1, 3.4), (0, .45, 2.45), mat('EAF6FA', .5, emit=.4), .02)
    door = mark('door', box((1.9, .01, 3.3), (0, -.86, 2.45), mat('000000', 1, alpha=0), 0))
    door.hide_render = True
    steel = tex('brushed', 'D5DCDE', 'A9B3B6', metal=.9, rough=.3, scale=.4)
    drink = ['E53935', '43A047', 'FB8C00', '1E88E5', '8E24AA', 'FDD835']
    for r in range(4):
        z = 1.05 + r * .8
        box((1.9, .9, .04), (0, -.2, z - .05), steel, .01)
        for c in range(5):
            x = -.76 + c * .38
            col = drink[(r * 2 + c) % len(drink)]
            if (r + c) % 3 == 0:
                cyl(.13, .36, (x, -.35, z + .18), tex('brushed', col, col, metal=.8, rough=.3, scale=.3), bev=.02)
            else:
                cyl(.12, .42, (x, -.35, z + .21), mat(col, .15, coat=1, trans=.25), bev=.02)
                cyl(.12, .14, (x, -.35, z + .48), mat(col, .15, coat=1, trans=.25), r2=.05, bev=0)
                cyl(.055, .05, (x, -.35, z + .57), mat('F5F5F5', .4))
    bar((.9, -.9, 1.8), (.9, -.9, 3.2), .05, steel)
    mark('panel', box((2.1, .08, .55), (0, -.8, .35), mat('2A3134', .5), .05))
    for i in range(4):
        box((1.9, .03, .05), (0, -.85, .18 + i * .11), mat('1A2023', .6), .01)
    studio(elev=6, yaw=-14, width=460, height=820)


def electric_panel():
    # Open electrical box (front view): galvanized back plate, slotted cable duct on top, DIN rail
    # for the terminal block at the bottom and a slot for the breaker. Wires/terminals are live UI.
    steel = tex('brushed', 'C9D1D3', '9AA6AA', metal=.85, rough=.32, scale=.35)
    box((4.2, .6, 4.8), (0, .3, 0), mat('596468', .45), .12)
    box((3.8, .1, 4.4), (0, -.02, 0), tex('noise', 'B9C2C4', '98A3A6', metal=.7, rough=.45, scale=1, bump=.15), .04)
    mark('duct', box((3.4, .35, .5), (0, -.2, 1.75), mat('8E969A', .5), .04))
    for i in range(14):
        box((.06, .36, .36), (-1.56 + i * .24, -.21, 1.72), mat('6E777B', .55), .01)
    mark('terminals', box((3.4, .25, .22), (0, -.15, -1.55), steel, .03))
    sw = mark('switch', box((1.0, .3, 1.0), (1.1, -.15, .9), mat('000000', 1, alpha=0), 0))
    sw.hide_render = True
    box((1.3, .2, .12), (1.1, -.12, .9), steel, .02)
    box((.7, .02, .45), (-1.35, -.09, 1.05), mat('F2B03D', .4), .04)
    text('!', (-1.35, -.11, 1.05), .32, mat('2F3A40', .4), extrude=.005, bevel=0)
    for x, z in ((-1.8, 2.05), (1.8, 2.05), (-1.8, -2.05), (1.8, -2.05)):
        cyl(.08, .05, (x, -.1, z), mat('8E9A9E', .3, .9), rot=(90, 0, 0))
    studio(elev=0, yaw=0, width=640, height=720, size=4.9)


def cable_tile():
    m = tex('plastic', 'FFFFFF', 'F1F1F1', rough=.3, scale=6, bump=.05, coat=.8)
    cyl(.25, 4.0, (0, 0, 0), m, rot=(0, 90, 0), bev=0)
    studio(elev=0, yaw=0, width=256, height=32, size=4.0)


def plug_part(part):
    def build():
        if part == 'sleeve':
            m = tex('plastic', 'FFFFFF', 'EEEEEE', rough=.3, scale=4, bump=.05, coat=.8)
            cyl(.3, .6, (0, 0, .55), m, r2=.24, bev=.04)
            for z in (.35, .5, .65):
                torus(.29, .03, (0, 0, z), m)
            cyl(.2, .25, (0, 0, .95), m, bev=.03)
        else:
            metal = tex('brushed', 'F3C95C', 'C8962E', metal=1, rough=.25, scale=.3)
            cyl(.22, .2, (0, 0, .15), tex('brushed', 'D5DCDE', 'A9B3B6', metal=1, rough=.25, scale=.3), bev=.02)
            cyl(.1, .75, (0, 0, -.35), metal, bev=.02)
        studio(elev=0, yaw=0, width=128, height=256, size=2.0, target=(0, 0, .05))
    build.__name__ = 'plug_' + part
    return build


def terminal():
    body = tex('plastic', '8C969A', '7A8488', rough=.4, scale=2, bump=.05)
    box((1.0, .9, 1.3), (0, 0, 0), body, .08)
    box((.5, .5, .2), (0, 0, .62), mat('1C2224', .7), .04)
    cyl(.24, .1, (0, -.46, .05), tex('brushed', 'F3C95C', 'C8962E', metal=1, rough=.25, scale=.3), rot=(90, 0, 0), bev=.02)
    box((.34, .03, .06), (0, -.52, .05), mat('6B4A1E', .5), .01)
    studio(elev=18, yaw=0, width=160, height=200, size=1.7, target=(0, 0, 0))


def breaker(on):
    def build():
        box((.9, .7, 1.4), (0, 0, 0), tex('plastic', 'F4F4F2', 'E2E2DE', rough=.35, scale=2, bump=.03), .08)
        box((.5, .1, .7), (0, -.36, 0), mat('2F3A40', .5), .05)
        z = .15 if on else -.15
        box((.36, .5, .3), (0, -.55, z), mat('5DA637' if on else 'E15533', .35, coat=.6), .08, rot=(-25 if on else 25, 0, 0))
        cyl(.08, .05, (.3, -.37, .55), mat('5DA637' if on else 'E15533', .2, emit=3), rot=(90, 0, 0))
        text('ON' if on else 'OFF', (0, -.37, -.55), .16, mat('2F3A40', .4), extrude=.003, bevel=0)
        studio(elev=6, yaw=0, width=160, height=240, size=1.6, target=(0, 0, 0))
    build.__name__ = 'breaker_' + ('on' if on else 'off')
    return build


def diagram_card():
    box((2.4, .03, 3.0), (0, 0, 0), tex('paper', 'FFFDF6', 'EFE8D8', rough=.7, scale=1, bump=.1, coat=0), .02)
    for x in (-.85, .85):
        box((.7, .02, .25), (x, -.03, 1.45), mat('F7E9A8', .4, trans=.3), .01, rot=(0, x * 12, 0))
    box((2.0, .01, .05), (0, -.02, 1.05), mat('9AA6AA', .5), 0)
    text('ESQUEMA', (0, -.03, 1.25), .22, mat('2F3A40', .4), extrude=.004, bevel=0)
    rows = mark('rows', box((2.0, .01, 2.1), (0, -.02, -.1), mat('000000', 1, alpha=0), 0))
    rows.hide_render = True
    studio(elev=0, yaw=0, width=400, height=500, size=3.2, target=(0, 0, 0))


def wire_kit():
    card = tex('paper', 'D3A56B', 'B8864E', rough=.8, scale=1, bump=.15, coat=0)
    box((2.0, 1.4, .8), (0, 0, .4), card, .03)
    for i, c in enumerate(['E53935', '1E88E5', 'FDD835', '43A047']):
        torus(.32, .12, (-.62 + i * .42, 0, .95), mat(c, .3, coat=.8), rot=(90, 0, 0))
    text('FIOS', (0, -.71, .4), .3, mat('2F3A40', .5), extrude=.01)
    studio(elev=26, yaw=-22)


def soot():
    m = mat('2B2522', .9, coat=0)
    for x, y, r in ((0, 0, .6), (.45, .2, .35), (-.4, -.25, .3), (.2, -.4, .25), (-.3, .35, .22)):
        sphere(r, (x, y, 0), m, (1, 1, .08))
    studio(elev=90, yaw=0, width=256, height=256)


COOLER_SPRITES = {
    'chest_freezer': chest_freezer, 'drinks_cooler': drinks_cooler, 'electric_panel': electric_panel,
    'cable_tile': cable_tile, 'plug_sleeve': plug_part('sleeve'), 'plug_pin': plug_part('pin'), 'terminal': terminal,
    'breaker_on': breaker(True), 'breaker_off': breaker(False), 'diagram_card': diagram_card, 'wire_kit': wire_kit, 'soot': soot,
}


# ---------------------------------------------------------------- receiving (truck unloading, stockroom)

def dock_backdrop():
    # Loading dock seen from inside: concrete floor with a yellow/black safety edge, roller door.
    plane((24, 16), (0, 0, 0), tex('noise', 'B9B4AA', '9D978B', rough=.7, scale=1.5, bump=.2, coat=0))
    for i in range(-12, 13):
        box((.5, .3, .05), (i * 1.0, -1.2, .02), mat('F2B03D' if i % 2 == 0 else '2F3A40', .5), .01, rot=(0, 0, 35))
    for x in (-8, 8):
        box((.16, 16, .02), (x, 0, .01), mat('F2B03D', .5), 0)
    wall = tex('tiles', 'D9D4C8', 'A9A396', c3='CFC9BB', scale=.7, bump=.2, rough=.6, coat=.1)
    box((24, .4, 7), (0, 6.2, 3.5), wall, .02)
    shutter = tex('ribs', 'AEB6B8', '8E9699', rough=.4, metal=.6, scale=3, bump=.5, stretch=(.1, 1, 1))
    box((8, .2, 5.4), (0, 5.9, 2.7), shutter, .03)
    box((8.6, .3, .5), (0, 5.85, 5.6), mat(TEAL, .35), .05)
    for x in (-4.3, 4.3):
        box((.3, .3, 5.8), (x, 5.85, 2.9), mat('F2B03D', .45), .05)
    backdrop_studio(1600, 900, 18, (0, 1.5, 1.2), elev=38, light=.9)


def truck_back():
    # Rear of a delivery truck with both doors open and an empty cargo bay (boxes are live UI).
    body = tex('plastic', 'F4F6F7', 'E1E6E8', rough=.3, scale=1, bump=.03)
    box((4.2, 1.0, 4.4), (0, .5, 2.6), body, .12)
    box((3.6, 1.2, 3.6), (0, .55, 2.55), tex('wood', 'C99A62', 'A8784A', scale=1.4, bump=.2, stretch=(.1, 1, 1)), .02)
    mark('cargo', box((3.4, .1, 3.3), (0, -.1, 2.55), mat('000000', 1, alpha=0), 0))
    MARKS['cargo'].hide_render = True
    for s in (-1, 1):
        box((.1, 2.0, 4.2), (s * 2.9, -.9, 2.6), body, .05, rot=(0, 0, s * 20))
        bar((s * 2.1, -.05, 1.0), (s * 2.1, -.05, 4.2), .04, tex('brushed', 'C9D1D3', '9AA6AA', metal=.9, rough=.3, scale=.4))
    box((4.4, .4, .5), (0, -.1, .45), mat('2F3A40', .5), .08)
    for x in (-1.8, 1.8):
        box((.5, .1, .25), (x, -.32, .5), mat('E53935', .2, emit=2), .05)
    box((4.3, .9, .5), (0, .5, 4.95), mat(TEAL, .35), .1)
    text('ENTREGAS', (0, -.02, 4.95), .32, mat('FFFFFF', .3), extrude=.01)
    studio(elev=6, yaw=0, width=640, height=640)


def cardboard_box():
    card = tex('paper', 'D6A469', 'B98449', rough=.75, scale=1, bump=.25, coat=0)
    box((1.4, 1.1, 1.0), (0, 0, .5), card, .04)
    box((.25, 1.12, .02), (0, 0, 1.0), mat('C9A46A', .3, trans=.2), 0)
    box((.25, .02, 1.0), (0, -.56, .5), mat('C9A46A', .3, trans=.2), 0)
    mark('label', box((.9, .02, .55), (-.1, -.565, .5), mat('FFFDF6', .6), .02))
    studio(elev=22, yaw=-18, width=256, height=240)


def rack_bay():
    # Stockroom rack: steel uprights, orange beams, three wooden decks (boxes are live UI).
    steel = tex('brushed', 'B7C0C3', '8A9598', metal=.85, rough=.35, scale=.4)
    for x in (-1.6, 1.6):
        for y in (-.5, .5):
            box((.12, .12, 4.6), (x, y, 2.3), steel, .02)
    for i, z in enumerate((.35, 1.85, 3.35)):
        for y in (-.55, .55):
            box((3.3, .1, .18), (0, y, z), mat('F28C28', .4), .03)
        box((3.2, 1.1, .08), (0, 0, z + .1), tex('wood', 'D2A46A', 'A87A45', scale=1.5, bump=.2, stretch=(.1, 1, 1)), .02)
        m = mark(f'level{i}', box((3.1, .1, 1.2), (0, -.2, z + .75), mat('000000', 1, alpha=0), 0))
        m.hide_render = True
    studio(elev=6, yaw=0, width=420, height=600, size=4.9)


def zone_sign():
    box((2.4, .08, .7), (0, 0, 0), tex('plastic', 'FFFFFF', 'F1F1F1', rough=.3, scale=2, bump=.03, coat=.8), .12)
    for x in (-.9, .9):
        bar((x, 0, .35), (x * .6, 0, 1.0), .02, tex('brushed', 'C9D1D3', '9AA6AA', metal=.9, rough=.3, scale=.4))
    mark('text', box((2.2, .01, .6), (0, -.05, 0), mat('000000', 1, alpha=0), 0)).hide_render = True
    studio(elev=0, yaw=0, width=400, height=180, size=2.6, target=(0, 0, .25))


def hand_cart():
    steel = tex('brushed', 'C9D1D3', '9AA6AA', metal=.9, rough=.3, scale=.4)
    bar((-.5, 0, .3), (-.5, 0, 3.0), .06, mat(TEAL, .35))
    bar((.5, 0, .3), (.5, 0, 3.0), .06, mat(TEAL, .35))
    bar((-.5, 0, 3.0), (.5, 0, 3.0), .06, mat('2F3A40', .4))
    box((1.3, .8, .08), (0, -.4, .2), steel, .02)
    for x in (-.6, .6):
        cyl(.25, .15, (x, .2, .25), mat('2F3A40', .6), rot=(0, 90, 0))
    studio(elev=10, yaw=-20)


RECEIVING_SPRITES = {
    'dock_backdrop': dock_backdrop, 'truck_back': truck_back, 'cardboard_box': cardboard_box,
    'rack_bay': rack_bay, 'zone_sign': zone_sign, 'hand_cart': hand_cart,
}


def panel_board():
    # Wooden plank board for headers/badges (9-sliced in UI).
    box((4, .3, 2), (0, 0, 1), tex('wood', 'E0A965', 'B37440', scale=1.2, bump=.25, stretch=(.1, 1, 1)), .14)
    box((3.7, .05, 1.7), (0, -.16, 1), tex('wood', 'EFC285', 'C98C52', scale=1.2, bump=.2, stretch=(.1, 1, 1)), .1)
    studio(elev=0, yaw=0, width=512, height=256, size=4.1)


SPRITES = {
    'reg_backdrop': reg_backdrop, 'belt': belt, 'belt_tile': belt_tile, 'scanner_bed': scanner_bed,
    'pos_terminal': pos_terminal, 'card_machine': card_machine,
    'card_blue': credit_card('2E8CAE', '1B5F80', 'card_blue'),
    'card_purple': credit_card('8B5C9E', '5A3470', 'card_purple'),
    'card_red': credit_card('E07A5F', 'B04A35', 'card_red'),
    'cash_tray': cash_tray, 'cash_drawer': cash_drawer_closed,
    'note_100': banknote(100), 'note_50': banknote(50), 'note_20': banknote(20), 'note_10': banknote(10), 'note_5': banknote(5),
    'note_2': banknote(2), 'coin_1': coin(1, True),
    'shopping_bag': shopping_bag, 'receipt_printer': receipt_printer, 'keypad_panel': keypad_panel,
    'key_light': key_cap('EEF1F1', 'key_light', 'E1E6E6'), 'key_red': key_cap(RED, 'key_red', 'C9442A'), 'key_green': key_cap(GREEN, 'key_green', '4E9030'),
    'floor_backdrop': floor_backdrop, 'wall_backdrop': wall_backdrop, 'ceiling_backdrop': ceiling_backdrop,
    'mop': mop, 'bucket': bucket, 'puddle': puddle, 'wet_sign': wet_sign,
    'soap_bubble': soap_bubble, 'sparkle': sparkle,
    'freezer_unit': freezer_unit, 'service_cover': service_cover, 'fan': fan, 'bolt': bolt, 'spare_part': spare_part,
    'bulb_off': bulb('off'), 'bulb_on': bulb('on'), 'bulb_dead': bulb('dead'), 'pendant_lamp': pendant_lamp, 'bulb_box': bulb_box,
    'shelf_unit': shelf_unit, 'tag_yellow': price_tag('F2B03D', 'tag_yellow'), 'tag_red': price_tag('E15533', 'tag_red'),
    'panel_board': panel_board, 'hand_pointer': hand_pointer, 'change_dish': change_dish,
    'emote_heart': emote('heart'), 'emote_angry': emote('angry'), 'emote_sweat': emote('sweat'), 'emote_question': emote('question'),
}


SPRITES.update(COOLER_SPRITES)
SPRITES.update(RECEIVING_SPRITES)


def main(args):
    names = [a for a in args if a in SPRITES] or list(SPRITES)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names:
        reset()
        SPRITES[name]()
        sc = bpy.context.scene
        sc.render.filepath = str(OUT / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        if MARKS:
            (OUT / (name + '_marks.json')).write_text(json.dumps(projected_rects()))
        print('UI_SPRITE', name, flush=True)
    print('UI_SPRITES_DONE', len(names), flush=True)


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
