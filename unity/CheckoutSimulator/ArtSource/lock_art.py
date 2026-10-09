"""
lock_art.py  --  Checkout - Supermercado Simulator
The padlock badge that floats over a lot that is not the player's yet (CheckoutLotSites.cs): a glossy padlock
in front of a round badge with a cream rim, like the locked areas of the big tycoon games.

  lot_lock       for sale now (green badge, gold padlock)
  lot_lock_grey  not next to the player's land yet (slate badge, steel padlock)
  lot_lock_open  bought, waiting to be cleared (orange badge, the padlock open)

Usage in Blender:
  exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\lock_art.py", encoding="utf-8").read())
  render_locks()
Output: ArtSource/Review/lock/<name>.png (512 x 512, transparent);
copied to Resources/CheckoutDesktop/Game/<name>.png
"""
import bpy, bmesh, math, os
from mathutils import Vector

exec(open(r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\lane_art.py", encoding="utf-8").read())

LOCK_OUT = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\lock"

VARIANTS = {
    "lot_lock": {"face": (0.33, 0.68, 0.22), "face_d": (0.2, 0.48, 0.14), "metal": (1.0, 0.76, 0.22), "open": False},
    "lot_lock_grey": {"face": (0.36, 0.43, 0.58), "face_d": (0.24, 0.29, 0.42), "metal": (0.78, 0.8, 0.84), "open": False},
    "lot_lock_open": {"face": (0.96, 0.55, 0.17), "face_d": (0.78, 0.38, 0.1), "metal": (1.0, 0.76, 0.22), "open": True},
}


def gloss(key, color, metal=0.0, rough=0.3, coat=0.0):
    """Smooth glossy paint or polished metal (no noise: the badge reads as a clean icon)."""
    name = "LK_" + key
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    try:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    except Exception:
        pass
    return m


def radial(key, inner, outer):
    """Badge face: lighter in the middle, darker at the rim (a soft dome)."""
    name = "LK_" + key
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = 0.35
    try:
        b.inputs["Coat Weight"].default_value = 0.6
        b.inputs["Coat Roughness"].default_value = 0.05
    except Exception:
        pass
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    # distance from the centre in the badge plane (x, z)
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MULTIPLY"
    nt.links.new(sep.outputs["X"], mx.inputs[0]); nt.links.new(sep.outputs["X"], mx.inputs[1])
    mz = nt.nodes.new("ShaderNodeMath"); mz.operation = "MULTIPLY"
    nt.links.new(sep.outputs["Z"], mz.inputs[0]); nt.links.new(sep.outputs["Z"], mz.inputs[1])
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    nt.links.new(mx.outputs[0], add.inputs[0]); nt.links.new(mz.outputs[0], add.inputs[1])
    sq = nt.nodes.new("ShaderNodeMath"); sq.operation = "SQRT"
    nt.links.new(add.outputs[0], sq.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.2
    ramp.color_ramp.elements[0].color = (*[min(1, c * 1.18) for c in inner], 1)
    ramp.color_ramp.elements[1].position = 0.92
    ramp.color_ramp.elements[1].color = (*outer, 1)
    nt.links.new(sq.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m


def half_ring(r, t, loc, m, name="shackle"):
    """Upper half of a torus standing in the x-z plane: the U of the shackle."""
    o = torus(r, t, loc, m, rot=(math.radians(90), 0, 0), name=name)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    # the torus was rotated, so its local y is world z: keep the upper half
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.002], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    return o


def lock_badge(v):
    c = CUR["c"]
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    rot = (math.radians(90), 0, 0)  # cylinders facing the camera (-y)
    # Badge: cream rim, coloured domed face, a thin dark ring between them.
    cyl(1.0, 0.22, (0, 0.06, 0), gloss("rim", (0.99, 0.95, 0.86), rough=0.25, coat=0.5), seg=96, bevel=0.07, rot=rot, name="rim")
    cyl(0.885, 0.06, (0, -0.06, 0), gloss("ring", (0.18, 0.16, 0.2), rough=0.4), seg=96, bevel=0.0, rot=rot, name="ring")
    face = cyl(0.86, 0.1, (0, -0.075, 0), radial("face_" + v["key"], v["face"], v["face_d"]), seg=96, bevel=0.04, rot=rot, name="face")
    # Padlock: rounded metal body with a keyhole, steel shackle.
    metal = gloss("metal_" + v["key"], v["metal"], metal=0.55, rough=0.24, coat=0.7)
    steel = gloss("steel", (0.86, 0.87, 0.9), metal=1.0, rough=0.18)
    dark = gloss("keyhole", (0.09, 0.08, 0.1), rough=0.5)
    body = box((0.84, 0.34, 0.66), (0, -0.32, -0.18), metal, bevel=0.12)
    body.modifiers["Bevel"].segments = 6
    # a darker band and rivets at the top edge of the body
    box((0.86, 0.36, 0.07), (0, -0.32, 0.1), gloss("band_" + v["key"], [c * 0.78 for c in v["metal"]], metal=0.95, rough=0.3), bevel=0.03)
    for x in (-0.3, 0.3):
        sphere(0.035, (x, -0.495, 0.1), steel)
    # keyhole: a round hole and a tapered slot
    cyl(0.085, 0.04, (0, -0.49, -0.12), dark, seg=32, bevel=0.0, rot=rot, name="key_round")
    box((0.07, 0.04, 0.2), (0, -0.49, -0.24), dark, bevel=0.0)
    # shackle: a U whose legs go into the body; open = lifted and turned
    lift = 0.22 if v["open"] else 0.0
    sh = half_ring(0.27, 0.075, (0, -0.32, 0.36 + lift), steel)
    left = cyl(0.075, 0.26, (-0.27, -0.32, 0.24 + lift), steel, seg=24, bevel=0.0, name="leg")
    # the right leg stays in the body: longer when the shackle is lifted
    right = cyl(0.075, 0.26 + lift, (0.27, -0.32, 0.24 + lift / 2), steel, seg=24, bevel=0.0, name="leg")
    if v["open"]:
        # the shackle turns around its right leg, the free leg swinging towards the viewer
        a = math.radians(40)
        for o in (sh, left, right):
            dx = o.location.x - 0.27
            o.location.x = 0.27 + dx * math.cos(a)
            o.location.y = -0.32 + dx * math.sin(a)
            o.rotation_euler.z += a
    return face


def lock_camera():
    cam = bpy.data.objects["LaneArt_Cam"]
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2.32
    tilt = math.radians(84)  # almost straight on, a little from above
    cam.location = (0, -10 * math.sin(tilt), 10 * math.cos(tilt))
    cam.rotation_euler = (tilt, 0, 0)


def render_locks(names=None):
    os.makedirs(LOCK_OUT, exist_ok=True)
    sc = scene()
    sc.render.resolution_x, sc.render.resolution_y = 512, 512
    sc.cycles.samples = 96
    sun = bpy.data.objects["LaneArt_Sun"]
    sun.rotation_euler = (math.radians(35), math.radians(-28), math.radians(-20))
    bpy.data.lights["LaneArt_Sun"].energy = 3.2
    c = coll("LockArt")
    CUR["c"] = c
    for other in bpy.data.collections:
        if other.name.startswith("LaneArt_") or other.name.startswith("KitArt") or other.name == "LockArt":
            other.hide_render = other is not c
            other.hide_viewport = other is not c
    lock_camera()
    for n in names or list(VARIANTS):
        v = dict(VARIANTS[n], key=n)
        lock_badge(v)
        # scene() (called by the helpers) puts the lane size back: square frame right before rendering
        sc.render.resolution_x, sc.render.resolution_y = 512, 512
        sc.render.filepath = os.path.join(LOCK_OUT, n + ".png")
        bpy.ops.render.render(write_still=True)
    sc.render.resolution_x, sc.render.resolution_y = RES
