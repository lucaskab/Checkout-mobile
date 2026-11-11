"""Thief, from Lucas's Tripo model (texture fixed + beanie, thief_hoodie_fixed.blend) to the game.

  1. Character space like the other customers: feet on z = 0, 2.4 units tall, faces -Y (npc_lite's convention).
  2. Mobile mesh: npc_lite.decimate (welds Tripo's split seams, protects UV island borders, copies the original's
     normals) to ~24k triangles; the beanie to ~3k; albedo 2048 for the body, 1024 for the beanie.
  3. Rig: the customers' 14-bone skeleton (Customer_02), joints fitted to this body and skin weights by anatomy
     (build_npcs: measure / fit_rig / skin_weights / free_walk / adduct_customer). The beanie rides on the head.
  4. Clips: the customer's own (renamed Thief_Walking, Thief_Idle, Thief_GetFromShelf...) + the thief's
     (security_anim.THIEF_CLIPS: sneak, look around, stash, run, caught, hands up, give back, walk ashamed).
  5. Export: Assets/Resources/CheckoutSecurity/Thief.fbx + Textures/Thief_Body.png, Thief_Beanie.png.
"""
import bpy, os, sys, shutil, types, math
from mathutils import Vector, Matrix

UNITY = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator"
NPCS = os.path.join(UNITY, "ArtSource/NPCs")
OUTDIR = os.path.join(UNITY, "Assets/Resources/CheckoutSecurity")
TEXOUT = os.path.join(OUTDIR, "Textures")


def module(name, path):
    """Load a script as a module without running its command-line main() (npc_lite calls main() at the end)."""
    src = open(path, encoding="utf-8").read()
    if src.rstrip().endswith("\nmain()"):
        src = src.rstrip()[:-len("main()")]
    os.environ["NPC_NO_MAIN"] = "1"
    g = {"__name__": name, "__file__": path}
    exec(compile(src, path, "exec"), g)
    m = types.ModuleType(name); m.__dict__.update(g); sys.modules[name] = m
    return m


def to_character_space(body, extra):
    lo = Vector([min(v.co[i] for v in body.data.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in body.data.vertices) for i in range(3)])
    s = 2.4 / (hi.z - lo.z)
    c = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for o in [body] + extra:
        o.data.transform(Matrix.Translation(-c))
        o.data.transform(Matrix.Scale(s, 4))
        o.data.update()
    return s


def shrink_texture(src_path, dst_path, size):
    img = bpy.data.images.load(src_path, check_existing=False)
    img.scale(size, size)
    img.filepath_raw = dst_path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return dst_path


def game_material(o, name, tex_path):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    g = m.node_tree; g.nodes.clear()
    out = g.nodes.new("ShaderNodeOutputMaterial"); b = g.nodes.new("ShaderNodeBsdfPrincipled")
    t = g.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex_path, check_existing=True); t.image.reload()
    g.links.new(t.outputs["Color"], b.inputs["Base Color"]); g.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    b.inputs["Roughness"].default_value = 0.75; b.inputs["Specular IOR Level"].default_value = 0.3
    o.data.materials.clear(); o.data.materials.append(m)


def light_prop(o, budget):
    d = o.modifiers.new("budget", 'DECIMATE'); d.ratio = min(1.0, budget / max(1, sum(len(p.vertices) - 2 for p in o.data.polygons)))
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True); bpy.ops.object.modifier_apply(modifier="budget")
    for p in o.data.polygons:
        p.use_smooth = True


def rigid_to(o, rig, bone):
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    vg = o.vertex_groups.new(name=bone); vg.add(range(len(o.data.vertices)), 1.0, 'REPLACE')
    m = o.modifiers.new("Skeleton", 'ARMATURE'); m.object = rig
    o.parent = rig


def build(budget=24000):
    os.makedirs(TEXOUT, exist_ok=True)
    lite = module("npc_lite", os.path.join(NPCS, "npc_lite.py"))
    npcs = module("build_npcs", os.path.join(NPCS, "build_npcs.py"))
    sec = module("security_anim", os.path.join(UNITY, "ArtSource/pets/security_anim.py"))
    body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("tripo_node"))
    bean = bpy.data.objects["Thief_Beanie"]; band = bpy.data.objects["Thief_Bandana"]
    for o in list(bpy.data.objects):                      # previews, cameras, old rigs
        if o not in (body, bean, band) and not o.name.startswith("QA_"):
            bpy.data.objects.remove(o, do_unlink=True)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    to_character_space(body, [bean, band])
    body.name = "Thief"
    source, before, after = lite.decimate(body, budget)
    bpy.data.objects.remove(source, do_unlink=True)
    print("body tris", before, "->", after)
    light_prop(bean, 3000); light_prop(band, 4000)
    print("beanie tris", lite.tris(bean), "bandana tris", lite.tris(band))
    body_png = shrink_texture(os.path.join(NPCS, "incoming/Thief_Hoodie_albedo.png"), os.path.join(TEXOUT, "Thief_Body.png"), 2048)
    bean_png = shrink_texture(os.path.join(NPCS, "incoming/Thief_Beanie.png"), os.path.join(TEXOUT, "Thief_Beanie.png"), 1024)
    band_png = shrink_texture(os.path.join(NPCS, "incoming/Thief_Bandana.png"), os.path.join(TEXOUT, "Thief_Bandana.png"), 1024)
    game_material(body, "Thief_Body_Mat", body_png)
    game_material(bean, "Thief_Beanie_Mat", bean_png)
    game_material(band, "Thief_Bandana_Mat", band_png)
    # rig: the customers' skeleton fitted to this body
    L = npcs.measure(body)
    rig, others = npcs.import_rig("Customer_02")
    for o in others:
        bpy.data.objects.remove(o, do_unlink=True)
    side = npcs.fit_rig(rig, L)
    missed = npcs.skin_weights(body, L, side)
    npcs.bind(body, rig, "Thief")
    body.name = "Thief_Body"
    npcs.free_walk(rig, "Customer_02")
    r = npcs.Rig(rig)
    wide = math.degrees(math.atan2(abs(r.wrist[1].x - r.shoulder[1].x), r.shoulder[1].z - r.wrist[1].z))
    npcs.adduct_customer(rig, max(0.0, min(16.0, wide - 12.0)))
    # the thief's own clips, after the customers' adduction, with absolute arm angles (the sculpt is in an A pose)
    sec.build.__globals__["ARM_REST"] = wide          # (the functions read their own globals dict)
    sec.build(rig, sec.THIEF_CLIPS)
    rig.name = "Thief_Rig"; rig.data.name = "Thief_Rig"
    head = next(b.name for b in rig.data.bones if b.name.startswith("Head"))
    rigid_to(bean, rig, head); rigid_to(band, rig, head)
    for a in bpy.data.actions:
        if "|" in a.name:
            a.name = "Thief_" + a.name.split("|")[-1]
    print("rig", rig.name, "missed arm verts", missed, "wide", round(wide, 1), "actions", sorted(a.name for a in bpy.data.actions))
    return rig, body, bean, band


def export(rig, objs):
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    for x in bpy.context.selected_objects:
        x.select_set(False)
    rig.select_set(True)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    path = os.path.join(OUTDIR, "Thief.fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
                             use_armature_deform_only=True, bake_anim=True, bake_anim_use_all_actions=True,
                             bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y',
                             path_mode='STRIP')
    print("exported", path)
    return path
