"""Rain umbrella v2 for the heavy-rain event (held by city pedestrians).

Run inside Blender (MCP / Text Editor) or headless:
    Blender -b --python scripts/blender/build_umbrella_v2.py

Builds the model from scratch in its own scene "UmbrellaV2", exports
    unity/CheckoutSimulator/ArtSource/rain/RainUmbrellaV2.fbx   (-Z forward, Y up, FBX_SCALE_ALL, mesh only)
and renders previews to unity/CheckoutSimulator/Temp/qa/umbrella_v2_*.png.
It does NOT touch Assets/ - the designer approves the previews first.

Design: origin at the GRIP (hand position, just above the crook). Shaft along +Z.
  canopy diameter 1.15 m, rim 0.85 m above the grip (at the rib tips), dome top 1.10 m, crook bottom -0.25 m.
Material slots: "Canopy" (near-white vertex colours, tint it per character in Unity), "Metal", "Handle".
"""
import math
import os

import bpy
import bmesh
from mathutils import Vector

ROOT = r"C:\Checkout-mobile"
UNITY = os.path.join(ROOT, "unity", "CheckoutSimulator")
EXPORT_DIR = os.path.join(UNITY, "ArtSource", "rain")
PREVIEWS = os.path.join(UNITY, "Temp", "qa")

# --- dimensions (metres, grip at the origin) -----------------------------------------------------------------
CANOPY_R = 0.575      # canopy radius at the rib tips (diameter 1.15)
RIM_Z = 0.85          # rib tips / rim height above the grip
TOP_Z = 1.10          # dome top (fabric) above the grip
SHAFT_R = 0.011
HANDLE_R = 0.019
CROOK_R = 0.075       # crook bend radius -> bottom of the crook at -0.25
PANELS = 8
ANG_PER_PANEL = 6     # angular subdivisions per panel (48 around)
RINGS = 5             # radial rings of the canopy sheet
SAG = 0.034           # fabric sag between ribs (dome centre line of each panel)
SCALLOP = 0.058       # rim bows inward between rib tips (fraction of radius)
LIP = 0.012           # visible fabric thickness at the rim

TINTS = {"red": "E04B3A", "navy": "2E4A7D", "yellow": "F2C230", "green": "4FA36B", "teal": "2FA3A3", "pink": "E97AA2"}


def srgb(hex6):
    c = [int(hex6[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((v / 12.92) if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c)


# --- scene -----------------------------------------------------------------------------------------------------
def scene():
    sc = bpy.data.scenes.get("UmbrellaV2")
    if sc:
        for o in list(sc.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        sc = bpy.data.scenes.new("UmbrellaV2")
    for w in bpy.context.window_manager.windows:
        w.scene = sc
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1200, 800
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    world = bpy.data.worlds.get("UmbrellaStudio") or bpy.data.worlds.new("UmbrellaStudio")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (.80, .82, .86, 1)
    bg.inputs[1].default_value = 0.55
    sc.world = world
    return sc


def link(obj, sc):
    sc.collection.objects.link(obj)
    return obj


def material(name, rgb, rough=.55, metallic=0.0, use_vcol=False, tint=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if use_vcol:
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Col"
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(vc.outputs["Color"], mix.inputs[6])
        mix.inputs[7].default_value = (*(tint or (1, 1, 1)), 1)
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        mat.diffuse_color = (*(tint or (.92, .92, .92)), 1)
    else:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
        mat.diffuse_color = (*rgb, 1)
    return mat


def smooth(obj, angle=40):
    me = obj.data
    for p in me.polygons:
        p.use_smooth = True
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.mark_sharp(clear=True)
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.select_mode(type="EDGE")
    bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(angle))
    bpy.ops.mesh.mark_sharp()
    bpy.ops.object.mode_set(mode="OBJECT")


def mesh_object(name, bm, mat, sc):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    me.materials.append(mat)
    return link(obj, sc)


# --- geometry helpers -------------------------------------------------------------------------------------------
def dome_z(u):
    """Height of the fabric centre line at normalised radius u (0 centre .. 1 rim)."""
    return RIM_Z + (TOP_Z - RIM_Z) * (1 - u ** 2.1)


def tube(bm, points, radius, sides=8, caps=True, radii=None):
    """Sweeps a circle along a polyline with parallel-transport frames. Returns the rings of verts."""
    pts = [Vector(p) for p in points]
    rings = []
    normal = None
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0]).normalized()
        elif i == len(pts) - 1:
            t = (pts[-1] - pts[-2]).normalized()
        else:
            t = ((pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()).normalized()
        if normal is None:
            ref = Vector((0, 1, 0)) if abs(t.y) < .9 else Vector((1, 0, 0))
            normal = ref.cross(t).normalized()
        else:
            normal = (normal - t * normal.dot(t)).normalized()
        binormal = t.cross(normal)
        r = radii[i] if radii else radius
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            ring.append(bm.verts.new(p + normal * (r * math.cos(a)) + binormal * (r * math.sin(a))))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    return rings


def uv_sphere(bm, center, radius, segments=6, rings=3):
    c = Vector(center)
    top = bm.verts.new(c + Vector((0, 0, radius)))
    bot = bm.verts.new(c - Vector((0, 0, radius)))
    loops = []
    for j in range(1, rings):
        phi = math.pi * j / rings
        loop = []
        for i in range(segments):
            th = 2 * math.pi * i / segments
            loop.append(bm.verts.new(c + Vector((radius * math.sin(phi) * math.cos(th),
                                                 radius * math.sin(phi) * math.sin(th), radius * math.cos(phi)))))
        loops.append(loop)
    for i in range(segments):
        bm.faces.new((top, loops[0][i], loops[0][(i + 1) % segments]))
        bm.faces.new((bot, loops[-1][(i + 1) % segments], loops[-1][i]))
    for a, b in zip(loops, loops[1:]):
        for i in range(segments):
            bm.faces.new((a[i], b[i], b[(i + 1) % segments], a[(i + 1) % segments]))


def cylinder(bm, z0, z1, radius, sides=8, r_top=None):
    p = [(0, 0, z0), (0, 0, z1)]
    tube(bm, p, radius, sides, caps=True, radii=[radius, r_top if r_top is not None else radius])


# --- parts ---------------------------------------------------------------------------------------------------------
def rim_point(i, u):
    """Fabric point at angular index i and normalised radius u (sag between ribs, scalloped rim)."""
    na = PANELS * ANG_PER_PANEL
    ang = 2 * math.pi * i / na
    # t: -1 at one rib, 0 at the panel centre, +1 at the next rib
    t = ((i % ANG_PER_PANEL) / ANG_PER_PANEL) * 2 - 1
    bulge = 1 - t * t
    r = CANOPY_R * u * (1 - SCALLOP * bulge * u ** 3)
    z = dome_z(u) - SAG * bulge * u ** 1.5
    return Vector((r * math.cos(ang), r * math.sin(ang), z))


def build_canopy(sc, mat):
    na = PANELS * ANG_PER_PANEL
    bm = bmesh.new()
    # top sheet
    centre = bm.verts.new((0, 0, TOP_Z))
    rings = []
    for j in range(1, RINGS + 1):
        u = (j / RINGS) ** 0.88
        rings.append([bm.verts.new(rim_point(i, u)) for i in range(na)])
    for i in range(na):
        bm.faces.new((centre, rings[0][i], rings[0][(i + 1) % na]))
    for a, b in zip(rings, rings[1:]):
        for i in range(na):
            bm.faces.new((a[i], b[i], b[(i + 1) % na], a[(i + 1) % na]))
    # rim lip (fabric thickness) and a low-poly underside (never seen from the game camera)
    lip = []
    for i in range(na):
        p = rim_point(i, 1.0)
        lip.append(bm.verts.new((p.x * 0.995, p.y * 0.995, p.z - LIP)))
    for i in range(na):
        j = (i + 1) % na
        bm.faces.new((rings[-1][i], lip[i], lip[j], rings[-1][j]))
    under_mid = []
    for i in range(na):
        p = rim_point(i, 0.55)
        under_mid.append(bm.verts.new((p.x, p.y, p.z - LIP)))
    for i in range(na):
        j = (i + 1) % na
        bm.faces.new((lip[i], under_mid[i], under_mid[j], lip[j]))
    under_centre = bm.verts.new((0, 0, TOP_Z - LIP - 0.004))
    for i in range(na):
        bm.faces.new((under_mid[i], under_centre, under_mid[(i + 1) % na]))
    bm.normal_update()
    obj = mesh_object("Canopy", bm, mat, sc)
    paint_canopy(obj)
    smooth(obj, 50)
    return obj


def paint_canopy(obj):
    """Near-white vertex colours (tint target), darker along the rib seams, the rim and underneath."""
    me = obj.data
    col = me.color_attributes.get("Col") or me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    na = PANELS * ANG_PER_PANEL
    for poly in me.polygons:
        down = poly.normal.z < -0.2
        lip = abs(poly.normal.z) < 0.45
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            r = math.hypot(v.x, v.y)
            u = min(r / CANOPY_R, 1.0)
            ang = math.atan2(v.y, v.x) % (2 * math.pi)
            panel_pos = (ang / (2 * math.pi / PANELS)) % 1.0        # 0..1 across one panel
            seam = abs(panel_pos - .5) * 2                            # 0 centre .. 1 at the rib
            shade = 0.93
            shade -= 0.16 * max(0.0, (seam - .6) / .4) ** 1.4 * (0.3 + 0.7 * u)    # dark seam at the ribs
            shade -= 0.05 * u ** 3                                                 # slightly darker rim
            shade += 0.04 * (1 - u) ** 2                                           # soft highlight on top
            if lip:
                shade *= 0.86
            if down:
                shade *= 0.70
            shade = max(0.0, min(1.0, shade))
            col.data[li].color = (shade, shade, shade, 1.0)


def build_ribs(sc, mat):
    bm = bmesh.new()
    for k in range(PANELS):
        ang = 2 * math.pi * k / PANELS
        d = Vector((math.cos(ang), math.sin(ang), 0))
        pts = []
        for s in range(5):
            u = 0.06 + (1 - 0.06) * (s / 4)
            r = CANOPY_R * u * (1.0 if s < 4 else 0.985)
            pts.append(d * r + Vector((0, 0, dome_z(u) - 0.014)))
        tube(bm, pts, 0.006, sides=3, caps=False)
        # rounded rib-tip bead
        uv_sphere(bm, d * (CANOPY_R * 0.997) + Vector((0, 0, RIM_Z - 0.005)), 0.017, segments=6, rings=3)
    # hub under the dome where the ribs meet
    cylinder(bm, TOP_Z - 0.07, TOP_Z - 0.02, 0.028, sides=8, r_top=0.02)
    # top ferrule + finial knob
    cylinder(bm, TOP_Z - 0.03, TOP_Z + 0.055, 0.013, sides=8, r_top=0.009)
    uv_sphere(bm, (0, 0, TOP_Z + 0.07), 0.022, segments=8, rings=4)
    # shaft (grip .. hub) and runner
    cylinder(bm, 0.0, TOP_Z - 0.05, SHAFT_R, sides=8)
    tube(bm, [(0, 0, 0.60), (0, 0, 0.615), (0, 0, 0.675), (0, 0, 0.69)], 0.018, sides=8, caps=True,
         radii=[0.012, 0.019, 0.019, 0.012])
    bm.normal_update()
    obj = mesh_object("Frame", bm, mat, sc)
    smooth(obj, 75)
    return obj


def build_handle(sc, mat):
    bm = bmesh.new()
    cz = -0.25 + CROOK_R           # crook centre height
    pts = [(0, 0, 0.055), (0, 0, -0.06), (0, 0, cz)]
    n = 7
    for i in range(1, n + 1):
        a = math.pi + math.pi * i / n          # from the shaft (left) under to the right
        pts.append((CROOK_R + CROOK_R * math.cos(a), 0, cz + CROOK_R * math.sin(a)))
    pts.append((2 * CROOK_R, 0, cz + 0.045))
    radii = [HANDLE_R * 0.78, HANDLE_R, HANDLE_R] + [HANDLE_R] * n + [HANDLE_R * 0.9]
    tube(bm, pts, HANDLE_R, sides=8, caps=True, radii=radii)
    bm.normal_update()
    obj = mesh_object("Handle", bm, mat, sc)
    smooth(obj, 75)
    return obj


def build(sc):
    mats = {
        "Canopy": material("Canopy", (.92, .92, .92), rough=.62, use_vcol=True),
        "Metal": material("Metal", (.72, .74, .78), rough=.35, metallic=.6),
        "Handle": material("Handle", (.16, .10, .07), rough=.5),
    }
    canopy = build_canopy(sc, mats["Canopy"])
    frame = build_ribs(sc, mats["Metal"])
    handle = build_handle(sc, mats["Handle"])
    # one object, three material slots, origin at the grip
    bpy.ops.object.select_all(action="DESELECT")
    for o in (canopy, frame, handle):
        o.select_set(True)
    bpy.context.view_layer.objects.active = canopy
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = "RainUmbrellaV2"
    obj.data.name = "RainUmbrellaV2"
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)
    obj.scale = (1, 1, 1)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# --- export & previews ---------------------------------------------------------------------------------------------
def export(obj):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, "RainUmbrellaV2.fbx")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, axis_forward="-Z", axis_up="Y",
                             apply_scale_options="FBX_SCALE_ALL", bake_anim=False, path_mode="STRIP",
                             use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=False, colors_type="SRGB")
    return path


def lights(sc):
    key = bpy.data.objects.new("Key", bpy.data.lights.new("Key", "SUN"))
    key.data.energy = 1.7
    key.data.color = (1, .97, .92)
    key.data.angle = math.radians(12)
    key.rotation_euler = (math.radians(38), math.radians(10), math.radians(35))
    link(key, sc)
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "SUN"))
    fill.data.energy = 0.45
    fill.data.color = (.85, .9, 1)
    fill.data.angle = math.radians(40)
    fill.rotation_euler = (math.radians(55), math.radians(-20), math.radians(-120))
    link(fill, sc)
    return key, fill


def camera(sc, target, pitch=50, yaw=35, ortho_scale=2.0, shift_y=0.0):
    cam = bpy.data.objects.get("UmbrellaCam")
    if not cam or cam.name not in sc.objects:
        cam = bpy.data.objects.new("UmbrellaCam", bpy.data.cameras.new("UmbrellaCam"))
        link(cam, sc)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho_scale
    cam.data.shift_y = shift_y
    p, y = math.radians(pitch), math.radians(yaw)
    d = Vector((math.cos(p) * math.sin(y), -math.cos(p) * math.cos(y), math.sin(p)))
    cam.location = Vector(target) + d * 12
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = 100
    sc.camera = cam
    return cam


def render(sc, name):
    os.makedirs(PREVIEWS, exist_ok=True)
    path = os.path.join(PREVIEWS, name + ".png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def tinted_copy(obj, key, hex6, location):
    me = obj.data.copy()
    me.name = "Umbrella_" + key
    me.materials[0] = material("Canopy_" + key, (1, 1, 1), rough=.62, use_vcol=True, tint=srgb(hex6))
    o = bpy.data.objects.new("Umbrella_" + key, me)
    o.location = location
    return o


def person(sc):
    """2.5 m capsule stand-in with a big head (centre 1.85, r .33); returns its objects."""
    objs = []
    mat = material("Person", (.62, .66, .70), rough=.7)
    bpy.ops.mesh.primitive_cylinder_add(radius=.30, depth=1.30, location=(0, 0, .80), vertices=24)
    body = bpy.context.object
    objs.append(body)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.30, location=(0, 0, .18), segments=24, ring_count=12)
    objs.append(bpy.context.object)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.30, location=(0, 0, 1.45), segments=24, ring_count=12)
    objs.append(bpy.context.object)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.33, location=(0, 0, 1.85), segments=32, ring_count=16)
    objs.append(bpy.context.object)
    for o in objs:
        o.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
    return objs


def previews(sc, obj):
    out = []
    lights(sc)
    # (a) game angle, 3/4 from above
    camera(sc, (0, 0, .55), pitch=50, yaw=35, ortho_scale=1.75)
    out.append(render(sc, "umbrella_v2_game_angle"))
    # (b) side view
    camera(sc, (0.04, 0, .47), pitch=3, yaw=0, ortho_scale=2.4)
    out.append(render(sc, "umbrella_v2_side"))
    # (c) six tints side by side at the game angle
    copies = []
    for i, (k, h) in enumerate(TINTS.items()):
        c = tinted_copy(obj, k, h, ((i - 2.5) * 1.35, 0, 0))
        link(c, sc)
        copies.append(c)
    obj.hide_render = True
    camera(sc, (0, 0, .55), pitch=50, yaw=0, ortho_scale=8.6)
    sc.render.resolution_x, sc.render.resolution_y = 2400, 800
    out.append(render(sc, "umbrella_v2_colors"))
    sc.render.resolution_x, sc.render.resolution_y = 1200, 800
    for c in copies:
        bpy.data.objects.remove(c, do_unlink=True)
    obj.hide_render = False
    # (d) held by a 2.5 m stand-in
    people = person(sc)
    held = bpy.data.objects.new("UmbrellaHeld", obj.data)
    link(held, sc)
    grip = Vector((0.15, -0.35, 1.75))
    tilt = math.radians(12)
    # tilt the shaft towards the head so the canopy sits over it
    to_head = Vector((0 - grip.x, 0 - grip.y, 0)).normalized()
    axis = Vector((0, 0, 1)).cross(to_head)
    held.location = grip
    held.rotation_mode = "AXIS_ANGLE"
    held.rotation_axis_angle = (tilt, *axis)
    obj.hide_render = True
    camera(sc, (0, 0, 1.55), pitch=50, yaw=35, ortho_scale=4.2)
    out.append(render(sc, "umbrella_v2_held_game"))
    camera(sc, (0, 0, 1.55), pitch=2, yaw=90, ortho_scale=4.8)
    out.append(render(sc, "umbrella_v2_held_side"))
    for o in people + [held]:
        bpy.data.objects.remove(o, do_unlink=True)
    obj.hide_render = False
    return out


def main(do_export=True, do_previews=True):
    sc = scene()
    obj = build(sc)
    info = {"triangles": tri_count(obj), "vertices": len(obj.data.vertices),
            "slots": [m.name for m in obj.data.materials],
            "rim_z": RIM_Z, "top_z": TOP_Z, "canopy_r": CANOPY_R,
            "bbox_z": [min(v.co.z for v in obj.data.vertices), max(v.co.z for v in obj.data.vertices)],
            "bbox_r": max(math.hypot(v.co.x, v.co.y) for v in obj.data.vertices)}
    if do_export:
        info["fbx"] = export(obj)
    if do_previews:
        info["previews"] = previews(sc, obj)
    return info


if __name__ == "__main__":
    print(main())
