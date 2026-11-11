"""QA renders of the pet beds (pet-bed-*) for approval - reads the decor_v4 outputs (fbx/, tex/), writes PNGs, touches nothing else.
    blender -b --factory-startup --python qa_pet_beds.py -- <out_dir> [<id> ...]
Per bed: <id>_close.png (3/4 beauty shot), <id>_game.png (isometric-ish camera from above at ~45 deg, like the game),
<id>_colourways.png (navy / teal / orange / rose side by side). With all five ids: all_beds_scale.png (side by side, with a
0.8 m ring and a cartoon curled-up dog of Caramelo's size as a scale reference - render only, not part of any item)."""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import dv4

ALL = ["pet-bed-round", "pet-bed-basket", "pet-bed-house", "pet-bed-sofa", "pet-bed-royal"]
NAMES = {"pet-bed-round": "PetBedRound", "pet-bed-basket": "PetBedBasket", "pet-bed-house": "PetBedHouse",
         "pet-bed-sofa": "PetBedSofa", "pet-bed-royal": "PetBedRoyal"}
STYLES = ["navy", "teal", "orange", "rose"]


def tex_path(name, st):
    return os.path.join(dv4.D["tex"], "IK_D4_%s_albedo%s.png" % (name, "" if st == "navy" else "_" + st))


def tex_mat(name, st):
    key = "QA_%s_%s" % (name, st)
    m = bpy.data.materials.get(key)
    if m:
        return m
    m = bpy.data.materials.new(key); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = .62
    try:
        bsdf.inputs["Specular IOR Level"].default_value = .25
    except Exception:
        pass
    p = tex_path(name, st)
    if os.path.exists(p):
        ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p, check_existing=True)
        nt.links.new(ti.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        print("[qa] missing", p); bsdf.inputs["Base Color"].default_value = (1, 0, 1, 1)
    return m


def load(id_, st="navy", offset=(0, 0, 0), rot_z=0.0):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(dv4.D["fbx"], id_ + ".fbx"))
    objs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    for o in objs:
        for i, m in enumerate(o.data.materials):
            nm = m.name.split(".")[0] if m else ""
            o.data.materials[i] = tex_mat(NAMES[id_], st) if nm.startswith("T_IK_D4") else dv4.preview_material(nm)
    bpy.context.view_layer.update()
    M = Matrix.Translation(Vector(offset)) @ Matrix.Rotation(math.radians(rot_z), 4, "Z")
    for o in objs:
        if o.parent is None:
            o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    return objs


def clear():
    for o in list(bpy.data.objects):
        if not o.name.startswith("DV4_"):
            bpy.data.objects.remove(o)


def floor(size=60.0):
    me = bpy.data.meshes.new("QA_Floor"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    bm.to_mesh(me); bm.free()
    fl = bpy.data.objects.new("DV4_Floor", me); bpy.context.scene.collection.objects.link(fl)
    m = bpy.data.materials.new("QA_FloorMat"); m.use_nodes = True; nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = .85
    tc = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1.0; br.offset = 0.0
    br.inputs["Brick Width"].default_value = .5; br.inputs["Row Height"].default_value = .5; br.inputs["Mortar Size"].default_value = .006
    br.inputs["Color1"].default_value = dv4.rgba("F3E8D0"); br.inputs["Color2"].default_value = dv4.rgba("ECDFC2")
    br.inputs["Mortar"].default_value = dv4.rgba("D2BC96")
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"]); nt.links.new(br.outputs["Color"], bsdf.inputs["Base Color"])
    me.materials.append(m)
    return fl


def setup():
    dv4.reset()
    cam = dv4._light_rig(False)
    sc = bpy.context.scene
    sc.render.film_transparent = False; sc.render.image_settings.color_mode = "RGB"; sc.render.resolution_percentage = 100
    sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = dv4.rgba("EFEDE8")
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .7
    floor()
    return cam


def frame(cam, objs, az, el, w, h, path, ortho=False, lens=50.0, pad=1.12, aim_z=0.0):
    sc = bpy.context.scene
    lo, hi = dv4.bounds(objs); c = (lo + hi) / 2; c.z = c.z * .8 + aim_z
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    # fit: project the bounding box corners on the camera plane
    fwd = -d; right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd)
    corners = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    ex = max(abs((p - c).dot(right)) for p in corners); ey = max(abs((p - c).dot(up)) for p in corners)
    asp = w / h
    half = max(ex, ey * asp) * pad
    sc.render.resolution_x, sc.render.resolution_y = w, h
    if ortho:
        cam.data.type = "ORTHO"; cam.data.ortho_scale = half * 2; dist = 20.0
    else:
        cam.data.type = "PERSP"; cam.data.lens = lens; cam.data.sensor_fit = "HORIZONTAL"; cam.data.sensor_width = 36
        dist = half / math.tan(math.atan(18 / lens)) + max(ex, ey) * .6
    cam.data.clip_end = 300
    dv4._aim(cam, c, d, dist)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[qa] wrote", path, flush=True)


def dog(loc):
    """Cartoon Caramelo curled up (about .75 x .55 m), caramel with cream chest and muzzle - scale reference only."""
    def mat(n, h):
        m = bpy.data.materials.new(n); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = dv4.rgba(h); b.inputs["Roughness"].default_value = .7
        return m
    car, cre, drk = mat("QA_Dog", "D3924A"), mat("QA_DogCream", "F2DDB8"), mat("QA_DogDark", "2A1C14")
    objs = []
    def sph(p, s, m, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(loc[0] + p[0], loc[1] + p[1], loc[2] + p[2]), segments=24, ring_count=14)
        o = bpy.context.active_object; o.scale = s; o.rotation_euler = rot; o.data.materials.append(m)
        bpy.ops.object.shade_smooth(); objs.append(o)
        return o
    sph((0, -.04, .12), (.34, .25, .13), car)                                   # curled body
    sph((-.17, .08, .1), (.14, .15, .09), car)                                  # hind leg
    sph((.05, .19, .06), (.2, .065, .05), cre, (0, 0, .2))                      # front paws
    sph((.16, .18, .17), (.11, .1, .095), car)                                  # head resting on the paws
    sph((.16, .27, .15), (.055, .05, .042), cre)                                # muzzle
    sph((.16, .315, .165), (.017, .014, .013), drk)                             # nose
    for s in (-1, 1):
        sph((.16 + s * .045, .25, .205), (.013, .01, .015), drk)                 # eyes (closed, sleepy)
        sph((.16 + s * .085, .15, .22), (.035, .022, .06), car, (0, s * .7, 0))  # floppy ears
    sph((-.24, .2, .07), (.05, .14, .04), car, (0, 0, -.5))                     # tail around the body
    return objs


def ring08(loc):
    bpy.ops.mesh.primitive_torus_add(major_radius=.4, minor_radius=.006, location=loc, major_segments=64, minor_segments=6)
    o = bpy.context.active_object
    m = bpy.data.materials.new("QA_Ring"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = dv4.rgba("D74A3C"); b.inputs["Emission Color"].default_value = dv4.rgba("D74A3C")
    b.inputs["Emission Strength"].default_value = .4
    o.data.materials.append(m)
    return [o]


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out = args[0]; ids = args[1:] or ALL
    os.makedirs(out, exist_ok=True)
    for id_ in ids:
        cam = setup()
        objs = load(id_)
        frame(cam, objs, 32, 24, 1200, 900, os.path.join(out, id_ + "_close.png"), lens=55, pad=1.06)
        frame(cam, objs, 35, 45, 1000, 800, os.path.join(out, id_ + "_game.png"), ortho=True, pad=1.9)
        if os.environ.get("QA_FRONT"):
            frame(cam, objs, 0, 8, 1000, 900, os.path.join(out, id_ + "_front.png"), ortho=True, pad=1.05)
        cam = setup()
        allo = []
        step = 1.25
        for i, st in enumerate(STYLES):
            allo += load(id_, st, offset=((1.5 - i) * step, 0, 0))      # +X is on the left: navy, teal, orange, rose read left to right
        frame(cam, allo, 12, 36, 2000, 640, os.path.join(out, id_ + "_colourways.png"), ortho=True, pad=1.04)
    if ids == ALL:
        cam = setup()
        allo = []
        xs = [2.3, 1.2, -.05, -1.35, -2.7]           # +X is on the left from this camera: round ... royal read left to right
        for x, id_ in zip(xs, ALL):
            allo += load(id_, "navy", offset=(x, 0, 0))
        allo += dog((3.45, -.02, 0)) + ring08((3.45, -.02, .004))
        frame(cam, allo, 12, 36, 2200, 760, os.path.join(out, "all_beds_scale.png"), ortho=True, pad=1.03)


main()
