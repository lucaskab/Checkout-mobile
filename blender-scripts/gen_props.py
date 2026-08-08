"""
Checkout Game — Props Generator (shelf, truck, checkout counter, tree)
Run inside Blender: Scripting tab > Open > Run Script
Exports one FBX per prop to the same folder.
"""

import bpy
import bmesh
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for m in bpy.data.materials:
        bpy.data.materials.remove(m)


def mat(name, r, g, b, roughness=0.65):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b_ = m.node_tree.nodes["Principled BSDF"]
    b_.inputs["Base Color"].default_value = (r, g, b, 1)
    b_.inputs["Roughness"].default_value = roughness
    return m


def box(name, loc, dims, mat_=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = dims
    bpy.ops.object.transform_apply(scale=True)
    if mat_:
        o.data.materials.clear()
        o.data.materials.append(mat_)
    return o


def cyl(name, loc, r, d, verts=10, mat_=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=loc)
    o = bpy.context.active_object
    o.name = name
    if rot != (0, 0, 0):
        import math
        o.rotation_euler = tuple(math.radians(a) for a in rot)
        bpy.ops.object.transform_apply(rotation=True)
    if mat_:
        o.data.materials.clear()
        o.data.materials.append(mat_)
    return o


def sphere(name, loc, r, mat_=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=10, ring_count=8)
    o = bpy.context.active_object
    o.name = name
    if mat_:
        o.data.materials.clear()
        o.data.materials.append(mat_)
    return o


def export_fbx(filename):
    out_path = os.path.join(OUTPUT_DIR, filename)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(
        filepath=out_path, use_selection=True,
        global_scale=1.0, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        axis_forward='-Z', axis_up='Y',
        mesh_smooth_type='FACE', use_mesh_modifiers=True,
    )
    print(f"[OK] {out_path}")


# ═══════════════════════════════════════════════════════════════════════════════
#  SHELF
# ═══════════════════════════════════════════════════════════════════════════════
clear_scene()

WALL   = mat("M_Wall",   0.96, 0.95, 0.92, 0.72)
TEAL   = mat("M_Teal",   0.08, 0.52, 0.62, 0.58)
ORANGE = mat("M_Orange", 1.00, 0.52, 0.12, 0.60)
CREAM  = mat("M_Cream",  1.00, 0.97, 0.90, 0.70)
DARK   = mat("M_Dark",   0.10, 0.10, 0.12, 0.85)
WOOD   = mat("M_Wood",   0.55, 0.32, 0.14, 0.85)

# Back panel
box("ShelfBack",    (0, 0.14, 0.95), (2.6, 0.14, 1.9),  TEAL)
# Base
box("ShelfBase",    (0, 0, 0.16),    (2.8, 0.82, 0.28), ORANGE)
# Three shelving boards
for i, h in enumerate((0.44, 0.85, 1.28)):
    box(f"Board_{i}", (0, -0.1, h), (2.64, 0.78, 0.1), CREAM)
# Top cap
box("TopCap",       (0, 0, 1.86),   (2.8, 0.86, 0.12), CREAM)
# Side posts
for sx in (-1.22, 1.22):
    box(f"Post_{sx}", (sx, -0.2, 0.95), (0.14, 0.56, 1.9), WALL)
# Price tag rail
box("PriceRail",    (0, -0.42, 0.43), (2.6, 0.06, 0.08), ORANGE)
box("PriceRail2",   (0, -0.42, 0.84), (2.6, 0.06, 0.08), ORANGE)
# Label board on back
box("LabelBoard",   (0, 0.22, 1.78), (2.2, 0.06, 0.26), ORANGE)

export_fbx("shelf.fbx")


# ═══════════════════════════════════════════════════════════════════════════════
#  CHECKOUT COUNTER
# ═══════════════════════════════════════════════════════════════════════════════
clear_scene()

WALL   = mat("M_Wall",   0.96, 0.95, 0.92, 0.72)
TEAL   = mat("M_Teal",   0.08, 0.52, 0.62, 0.58)
ORANGE = mat("M_Orange", 1.00, 0.52, 0.12, 0.60)
CREAM  = mat("M_Cream",  1.00, 0.97, 0.90, 0.70)
DARK   = mat("M_Dark",   0.10, 0.10, 0.12, 0.85)
BLUE   = mat("M_ScreenBlue", 0.28, 0.72, 1.00, 0.08)

# Counter body
box("CounterBody",  (0, 0, 0.72), (3.0, 1.4, 1.44), WALL)
box("CounterBand",  (0, 0, 1.26), (3.06, 1.46, 0.36), TEAL)
box("CounterBase",  (0, 0, 0.08), (3.1, 1.5, 0.16), ORANGE)
# Countertop
box("Countertop",   (0, 0, 1.5),  (3.18, 1.56, 0.14), CREAM)
# Conveyor belt
box("Belt",         (0, 0.32, 1.6),  (2.6, 0.5, 0.08), DARK)
cyl("BeltRollerL",  (-1.22, 0.32, 1.6), 0.11, 0.52, 10, TEAL, rot=(90,0,0))
cyl("BeltRollerR",  ( 1.22, 0.32, 1.6), 0.11, 0.52, 10, TEAL, rot=(90,0,0))
# Register monitor
box("MonPole",      (0, -0.52, 1.8),  (0.1, 0.1, 0.6), TEAL)
box("MonBase",      (0, -0.52, 1.6),  (0.44, 0.28, 0.12), TEAL)
box("MonScreen",    (0, -0.56, 1.92), (0.68, 0.1, 0.5), DARK)
box("MonGlow",      (0, -0.54, 1.92), (0.56, 0.06, 0.38), BLUE)
# Scanner bar
box("Scanner",      (0.8, -0.1, 1.56), (0.32, 0.44, 0.06), DARK)

export_fbx("checkout_counter.fbx")


# ═══════════════════════════════════════════════════════════════════════════════
#  DELIVERY TRUCK
# ═══════════════════════════════════════════════════════════════════════════════
clear_scene()

ORANGE = mat("M_Orange", 1.00, 0.52, 0.12, 0.60)
TEAL   = mat("M_Teal",   0.08, 0.52, 0.62, 0.58)
CREAM  = mat("M_Cream",  1.00, 0.97, 0.90, 0.70)
DARK   = mat("M_Dark",   0.12, 0.12, 0.14, 0.85)
GLASS  = mat("M_Glass",  0.52, 0.88, 0.92, 0.08)
GREY   = mat("M_Grey",   0.60, 0.62, 0.64, 0.70)
ROOF   = mat("M_Roof",   0.22, 0.52, 0.78, 0.55)
YELLOW = mat("M_Yellow", 1.00, 0.85, 0.20, 0.65)

# Cargo box
box("Cargo",        (0, 0, 0.85),   (3.5, 1.8, 1.7),  ORANGE)
box("CargoBand",    (0, 0, 1.5),    (3.56, 1.86, 0.3), TEAL)
box("CargoStripe",  (0, 0, 0.18),   (3.56, 1.86, 0.2), CREAM)
box("CargoRoof",    (0, 0, 1.74),   (3.6, 1.88, 0.12), TEAL)
# Cab
box("Cab",          (2.12, 0, 0.78),(0.8, 1.75, 1.56), TEAL)
box("CabRoof",      (2.12, 0, 1.58),(0.86, 1.8, 0.2),  ROOF)
box("CabBumper",    (2.54, 0, 0.24),(0.16, 1.78, 0.28), GREY)
box("Window",       (2.54, 0, 0.92),(0.1, 1.15, 0.72), GLASS)
# Headlights
for wy in (-0.72, 0.72):
    box(f"Headlight_{wy}", (2.56, wy, 0.76), (0.1, 0.32, 0.24), YELLOW)
# Wheels (4)
for wx, wy in ((-0.8, -1.02), (-0.8, 1.02), (1.1, -1.02), (1.1, 1.02)):
    cyl(f"Wheel_{wx}_{wy}", (wx, wy, 0.28), 0.28, 0.22, 12, DARK, rot=(90,0,0))
    cyl(f"Hub_{wx}_{wy}",   (wx, wy, 0.28), 0.16, 0.06, 8,  GREY, rot=(90,0,0))
# Logo on side
box("Logo",         (-0.2, -0.92, 1.0), (1.8, 0.06, 0.7), YELLOW)

export_fbx("truck.fbx")


# ═══════════════════════════════════════════════════════════════════════════════
#  TREE
# ═══════════════════════════════════════════════════════════════════════════════
clear_scene()

ORANGE = mat("M_Orange", 1.00, 0.52, 0.12, 0.60)
CREAM  = mat("M_Cream",  1.00, 0.97, 0.90, 0.70)
WOOD   = mat("M_Wood",   0.55, 0.32, 0.14, 0.85)
LEAF   = mat("M_Leaf",   0.22, 0.68, 0.18, 0.90)
LEAFLT = mat("M_LeafLt", 0.40, 0.80, 0.24, 0.90)
DARKSOIL = mat("M_Soil", 0.22, 0.18, 0.12, 0.95)

cyl("Pot",      (0, 0, 0.18), 0.5,  0.30, 12, ORANGE)
cyl("PotRim",   (0, 0, 0.36), 0.56, 0.08, 12, CREAM)
cyl("Soil",     (0, 0, 0.40), 0.44, 0.06, 12, DARKSOIL)
cyl("Trunk",    (0, 0, 0.9),  0.16, 1.0,  8,  WOOD)
sphere("Crown",      (0,    0,    1.92), 0.72, LEAF)
sphere("CrownHigh",  (0,    0,    2.52), 0.52, LEAFLT)
sphere("CrownL",     (-0.4, 0.1,  1.8),  0.46, LEAF)
sphere("CrownR",     ( 0.4,-0.1,  1.8),  0.44, LEAF)
sphere("CrownFront", ( 0.2, -0.3, 2.1),  0.38, LEAFLT)

export_fbx("tree.fbx")

print("[DONE] All props exported.")
