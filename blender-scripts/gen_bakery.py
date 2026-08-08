"""
Checkout Game — Bakery Building Generator
Run inside Blender: Scripting tab > Open > Run Script
Exports: bakery.fbx
"""

import bpy
import bmesh
import math
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def new_material(name, r, g, b, roughness=0.65, specular=0.1):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = specular
    return mat


def make_box(name, loc, dims, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = dims
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


def make_cylinder(name, loc, radius, depth, verts=12, mat=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


def make_sphere(name, loc, radius, mat=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc, segments=10, ring_count=8)
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


def make_wedge_roof(name, loc, w, h, d, mat=None):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    x, y, z = w / 2, d / 2, h
    v = [
        bm.verts.new((-x, -y, 0)), bm.verts.new((x, -y, 0)),
        bm.verts.new(( x,  y, 0)), bm.verts.new((-x,  y, 0)),
        bm.verts.new(( 0, -y, z)), bm.verts.new(( 0,  y, z)),
    ]
    bm.faces.new([v[0], v[1], v[2], v[3]])
    bm.faces.new([v[0], v[1], v[4]])
    bm.faces.new([v[3], v[2], v[5]])
    bm.faces.new([v[0], v[4], v[5], v[3]])
    bm.faces.new([v[1], v[2], v[5], v[4]])
    bm.to_mesh(mesh)
    bm.free()
    obj.location = loc
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


clear_scene()

M_WALL   = new_material("M_Wall",   0.96, 0.95, 0.92, 0.72)
M_TEAL   = new_material("M_Teal",   0.08, 0.52, 0.62, 0.58)
M_ORANGE = new_material("M_Orange", 1.00, 0.52, 0.12, 0.60)
M_CREAM  = new_material("M_Cream",  1.00, 0.97, 0.90, 0.70)
M_ROOF   = new_material("M_Roof",   0.22, 0.52, 0.78, 0.55)
M_GLASS  = new_material("M_Glass",  0.52, 0.88, 0.92, 0.08, 0.9)
M_WOOD   = new_material("M_Wood",   0.55, 0.32, 0.14, 0.85)
M_LEAF   = new_material("M_Leaf",   0.22, 0.68, 0.18, 0.90)
M_YELLOW = new_material("M_Yellow", 1.00, 0.85, 0.20, 0.65)

# ── Ground base ───────────────────────────────────────────────────────────────
make_box("Base",      (0, 0, -0.05), (5.5, 4.5, 0.14), M_CREAM)
make_box("BaseStripe",(0, 0,  0.08), (5.6, 4.6, 0.14), M_ORANGE)

# ── Main walls ────────────────────────────────────────────────────────────────
make_box("Walls",     (0, 0, 1.2),   (4.8, 3.6, 2.4),  M_WALL)
make_box("TealBand",  (0, 0, 2.16),  (4.9, 3.7, 0.52), M_TEAL)
make_box("Coping",    (0, 0, 2.50),  (5.0, 3.8, 0.14), M_CREAM)

# ── Roof ──────────────────────────────────────────────────────────────────────
make_wedge_roof("Roof", (0, 0, 2.56), 5.1, 1.1, 3.75, M_ROOF)
make_box("RidgeCap",    (0, 0, 3.60), (0.28, 3.8, 0.16), M_TEAL)

# ── Front window ──────────────────────────────────────────────────────────────
make_box("WinFrame",  (0, -1.82, 1.18), (2.2, 0.14, 1.1), M_CREAM)
make_box("WinGlass",  (0, -1.78, 1.18), (1.9, 0.07, 0.85), M_GLASS)
make_box("WinBarV",   (0, -1.76, 1.18), (0.07, 0.05, 0.87), M_CREAM)
make_box("WinBarH",   (0, -1.76, 1.18), (1.92, 0.05, 0.07), M_CREAM)

# ── Striped awning ────────────────────────────────────────────────────────────
make_box("Awning",     (0, -2.1, 2.0),  (4.9, 0.75, 0.2), M_ORANGE)
make_box("AwningFront",(0, -2.44, 1.9), (4.9, 0.06, 0.38), M_CREAM)
# Stripes
for sx in (-1.5, -0.5, 0.5, 1.5):
    make_box(f"Stripe_{sx}", (sx, -2.1, 2.0), (0.3, 0.77, 0.22), M_CREAM)

# ── Door ──────────────────────────────────────────────────────────────────────
make_box("DoorFrame",  (0, -1.82, 0.52), (1.2, 0.14, 1.04), M_TEAL)
make_box("Door",       (0, -1.78, 0.52), (0.9, 0.07, 0.96), M_CREAM)
make_box("DoorKnob",   (0.38, -1.74, 0.52), (0.1, 0.06, 0.1), M_ORANGE)

# ── Chimney ───────────────────────────────────────────────────────────────────
make_cylinder("Chimney",    (1.6, 1.2, 4.1),  0.22, 1.0,  10, M_TEAL)
make_box("ChimneyCap",      (1.6, 1.2, 4.66), (0.58, 0.58, 0.12), M_ORANGE)

# ── Planters ──────────────────────────────────────────────────────────────────
for px in (-2.0, 2.0):
    make_cylinder(f"Pot_{px}",  (px, -1.82, 0.18), 0.3,  0.28, 10, M_ORANGE)
    make_cylinder(f"Rim_{px}",  (px, -1.82, 0.34), 0.34, 0.07, 10, M_CREAM)
    make_cylinder(f"Soil_{px}", (px, -1.82, 0.37), 0.26, 0.05, 10, M_WOOD)
    make_sphere(f"Bush_{px}_0", (px, -1.82, 0.62), 0.35, M_LEAF)
    make_sphere(f"Bush_{px}_1", (px + 0.18, -1.72, 0.72), 0.22, M_LEAF)
    make_sphere(f"Bush_{px}_2", (px - 0.14, -1.90, 0.68), 0.20, M_LEAF)

# ── Sign board above awning ───────────────────────────────────────────────────
make_box("SignBoard",   (0, -2.46, 2.36), (3.2, 0.12, 0.42), M_YELLOW)
make_box("SignBoardBorder", (0, -2.44, 2.36), (3.4, 0.08, 0.56), M_TEAL)

# ── Export ────────────────────────────────────────────────────────────────────
out_path = os.path.join(OUTPUT_DIR, "bakery.fbx")
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
