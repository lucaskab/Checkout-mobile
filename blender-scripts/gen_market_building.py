"""
Checkout Game — Market Building Generator
Run inside Blender: Scripting tab > Open > Run Script
Exports: market_building.fbx to the same folder as this script
"""

import bpy
import bmesh
import math
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)


def new_material(name, r, g, b, roughness=0.65, specular=0.1):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = specular
    return mat


def add_mat(obj, mat):
    obj.data.materials.append(mat)


def make_box(name, location, dimensions, mat=None, collection=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = dimensions
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        obj.data.materials.clear()
        add_mat(obj, mat)
    if collection:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def make_cylinder(name, location, radius, depth, mat=None, verts=12, collection=None):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=int(verts), radius=radius, depth=depth, location=location)
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.clear()
        add_mat(obj, mat)
    if collection:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def make_wedge(name, location, w, h, d, mat=None, collection=None):
    """Triangular prism used for gabled roof panels."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    # 6 verts: two triangular faces
    x, y, z = w / 2, d / 2, h
    verts = [
        bm.verts.new((-x, -y, 0)),
        bm.verts.new(( x, -y, 0)),
        bm.verts.new(( x,  y, 0)),
        bm.verts.new((-x,  y, 0)),
        bm.verts.new(( 0, -y, z)),
        bm.verts.new(( 0,  y, z)),
    ]
    bm.faces.new([verts[0], verts[1], verts[2], verts[3]])  # bottom
    bm.faces.new([verts[0], verts[1], verts[4]])            # front tri
    bm.faces.new([verts[3], verts[2], verts[5]])            # back tri
    bm.faces.new([verts[0], verts[4], verts[5], verts[3]])  # left slope
    bm.faces.new([verts[1], verts[2], verts[5], verts[4]])  # right slope
    bm.to_mesh(mesh)
    bm.free()
    obj.location = location
    if mat:
        obj.data.materials.clear()
        add_mat(obj, mat)
    if collection:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def bevel_edges(obj, amount=0.04, segments=2):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bevel(offset=amount, segments=segments)
    bpy.ops.object.mode_set(mode='OBJECT')


def join_objects(objects, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    bpy.context.active_object.name = name
    return bpy.context.active_object


# ── Materials ──────────────────────────────────────────────────────────────────
M_WALL    = new_material("M_Wall",    0.96, 0.95, 0.92, roughness=0.72)
M_TEAL    = new_material("M_Teal",    0.08, 0.52, 0.62, roughness=0.58)
M_ORANGE  = new_material("M_Orange",  1.00, 0.52, 0.12, roughness=0.60)
M_CREAM   = new_material("M_Cream",   1.00, 0.97, 0.90, roughness=0.70)
M_ROOF    = new_material("M_Roof",    0.22, 0.52, 0.78, roughness=0.55)
M_GLASS   = new_material("M_Glass",   0.52, 0.88, 0.92, roughness=0.08, specular=0.9)
M_DARK    = new_material("M_Dark",    0.08, 0.10, 0.14, roughness=0.80)
M_YELLOW  = new_material("M_Yellow",  1.00, 0.85, 0.20, roughness=0.65)
M_WOOD    = new_material("M_Wood",    0.55, 0.32, 0.14, roughness=0.85)
M_LEAF    = new_material("M_Leaf",    0.22, 0.68, 0.18, roughness=0.90)
M_GRASS   = new_material("M_Grass",   0.36, 0.72, 0.22, roughness=0.95)
M_ASPHALT = new_material("M_Asphalt", 0.30, 0.30, 0.32, roughness=0.92)

clear_scene()
col = bpy.data.collections.new("MarketBuilding")
bpy.context.scene.collection.children.link(col)

parts = []

# ── Ground base (plaza) ────────────────────────────────────────────────────────
parts.append(make_box("Plaza",       (0, 0, -0.1),    (11, 9, 0.2),   M_CREAM,   col))
parts.append(make_box("PlazaEdge",   (0, 0, 0.0),     (11.3, 9.3, 0.12), M_ORANGE, col))

# ── Main body ─────────────────────────────────────────────────────────────────
parts.append(make_box("WallBody",    (0, 0, 1.5),     (10.0, 8.0, 3.0),  M_WALL,   col))
# Upper teal band
parts.append(make_box("TealBand",    (0, 0, 2.85),    (10.1, 8.1, 0.6),  M_TEAL,   col))
# Orange base stripe
parts.append(make_box("BaseStripe",  (0, 0, 0.14),    (10.1, 8.1, 0.22), M_ORANGE, col))
# Cream coping at top of teal band
parts.append(make_box("Coping",      (0, 0, 3.22),    (10.3, 8.3, 0.16), M_CREAM,  col))

# ── Gabled roof ───────────────────────────────────────────────────────────────
# Two sloped panels meeting at ridge
roof_pitch = 1.4
parts.append(make_wedge("Roof",      (0, 0, 3.30),    10.4, roof_pitch, 8.2, M_ROOF, col))
# Ridge cap
parts.append(make_box("RidgeCap",    (0, 0, 3.30 + roof_pitch - 0.06), (0.32, 8.3, 0.18), M_TEAL, col))

# ── Front facade details ───────────────────────────────────────────────────────
# Large entrance opening recess
parts.append(make_box("EntranceRecess", (0, -4.08, 1.1), (3.5, 0.3, 2.2), M_TEAL, col))
# Entrance header beam
parts.append(make_box("EntranceBeam",   (0, -4.0, 2.38), (4.0, 0.35, 0.42), M_TEAL, col))
parts.append(make_box("EntranceSign",   (0, -3.82, 2.38), (2.8, 0.06, 0.28), M_YELLOW, col))
# Entrance posts
for sx in (-1.62, 1.62):
    parts.append(make_box(f"EntrancePost_{sx}", (sx, -4.02, 1.1), (0.38, 0.38, 2.2), M_WALL, col))

# ── Windows (front) ───────────────────────────────────────────────────────────
for wx in (-3.2, 3.2):
    parts.append(make_box(f"WinFrame_{wx}",  (wx, -4.05, 1.3), (1.9, 0.16, 1.5),  M_CREAM,  col))
    parts.append(make_box(f"WinGlass_{wx}",  (wx, -3.98, 1.3), (1.6, 0.08, 1.2),  M_GLASS,  col))
    parts.append(make_box(f"WinBarV_{wx}",   (wx, -3.96, 1.3), (0.08, 0.06, 1.22), M_CREAM, col))
    parts.append(make_box(f"WinBarH_{wx}",   (wx, -3.96, 1.3), (1.62, 0.06, 0.08), M_CREAM, col))
    # Awning over window
    parts.append(make_box(f"Awning_{wx}",    (wx, -4.24, 1.98), (2.1, 0.7, 0.18), M_ORANGE, col))
    parts.append(make_box(f"AwningFront_{wx}", (wx, -4.55, 1.9), (2.1, 0.06, 0.34), M_CREAM, col))

# ── Side windows ──────────────────────────────────────────────────────────────
for side_y in (-2.5, 1.5):
    for side_x, face_x in ((-5.06, 1), (5.06, -1)):
        parts.append(make_box(f"SideWinFrame_{side_x}_{side_y}", (side_x, side_y, 1.4),
                              (0.16, 1.5, 1.2), M_CREAM, col))
        parts.append(make_box(f"SideWinGlass_{side_x}_{side_y}", (side_x, side_y, 1.4),
                              (0.08, 1.25, 0.95), M_GLASS, col))

# ── Chimney (back right) ──────────────────────────────────────────────────────
parts.append(make_cylinder("Chimney",    (3.5, 3.2, 4.6), 0.2, 1.2, mat=M_TEAL,   collection=col))
parts.append(make_box("ChimneyCap",     (3.5, 3.2, 5.28), (0.52, 0.52, 0.14), M_ORANGE, col))

# ── Planters (front corners) ──────────────────────────────────────────────────
for px in (-4.5, 4.5):
    parts.append(make_cylinder(f"PlanterPot_{px}", (px, -4.0, 0.18), 0.32, 0.3, mat=M_ORANGE, collection=col))
    parts.append(make_cylinder(f"PlanterRim_{px}", (px, -4.0, 0.36), 0.36, 0.08, mat=M_CREAM, collection=col))
    parts.append(make_cylinder(f"PlanterSoil_{px}", (px, -4.0, 0.39), 0.28, 0.06, mat=M_WOOD, collection=col))
    for i, (ox, oz) in enumerate(((0,0),(0.18,0.12),(-0.14,0.1),(0.08,-0.14))):
        s = 0.42 - i * 0.05
        parts.append(make_cylinder(f"Bush_{px}_{i}", (px+ox, -4.0+oz, 0.55 + i*0.06), s, s*1.2, mat=M_LEAF, collection=col))

# ── Small decorative flag poles on roof ───────────────────────────────────────
for fx in (-4.5, 0, 4.5):
    parts.append(make_cylinder(f"FlagPole_{fx}", (fx, -4.0, 3.6 + abs(fx)*0.05), 0.04, 0.8, mat=M_TEAL, collection=col))
    parts.append(make_box(f"Flag_{fx}",          (fx + 0.22, -4.0, 4.08 + abs(fx)*0.05), (0.4, 0.05, 0.24), M_ORANGE, col))


# ── Export ────────────────────────────────────────────────────────────────────
out_path = os.path.join(OUTPUT_DIR, "market_building.fbx")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(
    filepath=out_path,
    use_selection=True,
    global_scale=1.0,
    apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',
    axis_forward='-Z',
    axis_up='Y',
    mesh_smooth_type='FACE',
    use_mesh_modifiers=True,
)
print(f"[OK] Exported to: {out_path}")
