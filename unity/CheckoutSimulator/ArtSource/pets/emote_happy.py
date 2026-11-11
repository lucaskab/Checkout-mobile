"""The "happy" emote (Lucas 08/11: the dog shows a happy face, not hearts): a glossy yellow face with smiling eyes and an
open smile, lit like the other emotes (Resources/CheckoutDesktop/Game/emote_heart/sweat/angry, 192 px RGBA).

    blender -b --factory-startup --python emote_happy.py -- <out.png>
"""
import bpy, bmesh, math, sys
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/emote_happy.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def mat(name, rgb, rough=.22, coat=.6, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = .08
    return m


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)


yellow = mat("Face", lin("FFC93C"), .25, .7)
dark = mat("Ink", lin("5A2E12"), .35, .3)
tongue = mat("Tongue", lin("F06A6A"), .3, .4)
mouth_in = mat("Mouth", lin("7A2A1E"), .5, .1)
blush = mat("Blush", lin("FF8A7A"), .5, .0)

# the face: a slightly squashed glossy ball
bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=1.0)
face = bpy.context.active_object; face.scale = (1.0, .9, .96); face.data.materials.append(yellow)
bpy.ops.object.shade_smooth()


def on_face(x, z, push=0.0):
    """Point on the face surface (front = -Y) for the given x/z."""
    y2 = max(0.0, 1 - x * x - z * z)
    return Vector((x, -math.sqrt(y2) * .9 - push, z * .96))


def arc(name, cx, cz, r, a0, a1, thick, m, n=24):
    """A tube following an arc drawn on the face (smiling eyes / smile line)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = thick; cu.bevel_resolution = 6
    sp = cu.splines.new('POLY'); sp.points.add(n - 1)
    for i in range(n):
        a = math.radians(a0 + (a1 - a0) * i / (n - 1))
        p = on_face(cx + r * math.cos(a), cz + r * math.sin(a), push=.01)
        sp.points[i].co = (*p, 1)
    sp.use_endpoint_u = True
    o = bpy.data.objects.new(name, cu); sc.collection.objects.link(o); o.data.materials.append(m)
    cu.use_fill_caps = True
    return o


# smiling eyes: upside-down arcs (^ ^)
arc("EyeL", -.33, .22, .16, 20, 160, .055, dark)
arc("EyeR", .33, .22, .16, 20, 160, .055, dark)

# open smile: a half-moon mouth sunk into the face, with a tongue
bm = bmesh.new()
pts = []
for i in range(33):
    a = math.pi + math.pi * i / 32                      # lower half circle
    pts.append((.44 * math.cos(a), .40 * math.sin(a) - .08))
verts = [bm.verts.new(on_face(x, z, push=-.02)) for x, z in pts]
bm.faces.new(verts)
me = bpy.data.meshes.new("Mouth"); bm.to_mesh(me); bm.free()
mouth = bpy.data.objects.new("Mouth", me); sc.collection.objects.link(mouth); me.materials.append(mouth_in)
so = mouth.modifiers.new("t", 'SOLIDIFY'); so.thickness = .03
# lip line around the mouth
cu = bpy.data.curves.new("LipTop", 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = .035; cu.bevel_resolution = 6
sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
for i, (x, z) in enumerate(pts):
    sp.points[i].co = (*on_face(x, z, push=.012), 1)
sp.use_cyclic_u = True
lip = bpy.data.objects.new("LipTop", cu); sc.collection.objects.link(lip); lip.data.materials.append(dark)
# tongue
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=.2, location=on_face(0, -.36, push=-.06))
tg = bpy.context.active_object; tg.scale = (1.2, .5, .7); tg.data.materials.append(tongue); bpy.ops.object.shade_smooth()

# rosy cheeks
for x in (-.58, .58):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=.14, location=on_face(x, -.08, push=-.02))
    c = bpy.context.active_object; c.scale = (1.2, .25, .8); c.data.materials.append(blush); bpy.ops.object.shade_smooth()

# camera, lights (soft key from top-left, rim, a little fill), transparent film
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.85
cam.location = (0, -6, .05); cam.rotation_euler = (math.radians(90), 0, 0)
for name, loc, energy, size in (("Key", (-3, -4, 4), 900, 3), ("Rim", (3, 2, 3), 500, 2), ("Fill", (2, -5, -1), 160, 4)):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA')); sc.collection.objects.link(L)
    L.data.energy = energy; L.data.size = size; L.location = loc
    L.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.8, .8, .82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = .6
sc.render.engine = 'CYCLES'; sc.cycles.samples = 96; sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = 384
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("EMOTE_OK", OUT)
