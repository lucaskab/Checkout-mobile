"""Rede de supermercados: the approved models (Lucas 06/11 "Aprovado") exported for the game.

Run after rede_assets.py and rede_dc.py in the same namespace:
    exec(open(REPO + "/scripts/blender/rede_export.py").read(), ns); ns["export_rede"]()

Writes Assets/Resources/Rede/<Name>.fbx + <Name>_brand.json for each model. FBX like eras_v2 / export_unity(turn):
-Z forward, Y up, turned 180 deg about Z, so a point at Blender (x, y, z) of the model lands at Unity model (x, z, y).
Materials keep their contract names (C_RRGGBB painted colour, E_RRGGBB lit colour): CheckoutRedeModels builds them
at runtime with the painted shader, and the market paint repaints the navy / gold ones like the rest of the market.
The brand plates are listed in the JSON instead of relying on FBX empties: Unity-model position, the plate's normal
(the side you read from), its right and up, and the size the logo or the name takes there (as brand_preview).
"""
import bpy, json, math, os
from mathutils import Vector, Matrix

REDE_OUT = os.path.join(REPO, "unity", "CheckoutSimulator", "Assets", "Resources", "Rede")


def _u(v):
    """Blender model space -> Unity model space (x, z, y)."""
    return [round(v.x, 4), round(v.z, 4), round(v.y, 4)]


def _plate(e, rname):
    """brand_preview's sizes: (kind, size, text size, upper, colour)."""
    if e.name.startswith("Brand_Logo"):
        if "Door" in e.name:
            size = LOGO_SIZE["Door"]
        elif "Back" in e.name and "Truck" in rname:
            size = LOGO_SIZE["Back"]
        elif "Bag" in rname:
            size = LOGO_SIZE["Bag"]
        elif "Truck" in rname:
            size = .95
        elif "Totem" in rname:
            size = 1.45
        elif "Medallion" in rname:
            size = 1.25
        elif "WaterTower" in rname:
            size = .8
        elif "Gatehouse" in rname:
            size = .26
        elif "Fuel" in rname:
            size = .28
        else:
            size = .5
        return "logo", size, 0, False, ""
    big = "Board" in rname
    return "name", 0, (.62 if big else .36 if "Truck" in rname else .26), ("Truck" in rname or "Board" in rname), ("F0C75A" if big else NAVY)


def export_model(root, name, folder=REDE_OUT):
    os.makedirs(folder, exist_ok=True)
    inv = root.matrix_world.inverted()
    meshes = [o for o in root.children_recursive if o.type == "MESH"]
    dg = bpy.context.evaluated_depsgraph_get()
    R = Matrix.Rotation(math.pi, 4, "Z")
    temps, tris = [], 0
    for o in meshes:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(R @ inv @ o.matrix_world)
        t = bpy.data.objects.new(o.name.replace(root.name + "_", "", 1)[:60], me)
        bpy.context.scene.collection.objects.link(t)
        me.calc_loop_triangles(); tris += len(me.loop_triangles)
        temps.append(t)
    plates = []
    for e in root.children_recursive:
        if e.type != "EMPTY" or not e.name.startswith("Brand_"):
            continue
        holder = e.parent
        rname = holder.name if holder else root.name
        m = inv @ e.matrix_world
        rot = m.to_3x3().normalized()
        kind, size, text, upper, col = _plate(e, rname + " " + root.name)
        plates.append({"name": e.name, "holder": rname, "kind": kind, "size": size, "text": text, "upper": upper, "color": col,
                       "pos": _u(m.translation), "normal": _u(-(rot @ Vector((0, 1, 0)))), "right": _u(rot @ Vector((1, 0, 0))),
                       "up": _u(rot @ Vector((0, 0, 1)))})
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for t in temps:
        for v in t.data.vertices:
            lo = Vector(map(min, lo, v.co)); hi = Vector(map(max, hi, v.co))
    path = os.path.join(folder, name + ".fbx")
    try:
        bpy.ops.object.select_all(action="DESELECT")
        for t in temps:
            t.select_set(True)
        bpy.context.view_layer.objects.active = temps[0]
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, axis_forward="-Z", axis_up="Y",
                                 bake_anim=False, path_mode="STRIP", use_mesh_modifiers=True, mesh_smooth_type="OFF",
                                 apply_scale_options="FBX_SCALE_ALL", use_tspace=False)
    finally:
        for t in temps:
            me = t.data
            bpy.data.objects.remove(t, do_unlink=True)
            bpy.data.meshes.remove(me)
    # bounds in Unity model space (the turn negated x and y: undo it for the report)
    size = [round(hi.x - lo.x, 3), round(hi.z - lo.z, 3), round(hi.y - lo.y, 3)]
    info = {"model": name, "tris": tris, "size": size, "plates": plates}
    with open(os.path.join(folder, name + "_brand.json"), "w") as f:
        json.dump(info, f, indent=1)
    return {"file": name + ".fbx", "tris": tris, "size": size, "plates": len(plates)}


def export_rede():
    rk_core.clear("Rede Export")
    preview_setup()
    out = []
    dc = dc_building("RedeDC", (0, 0, 0))
    out.append(export_model(dc, "RedeDC"))
    for reefer in (False, True):
        r, _ = truck("FleetTruck_" + ("Reefer" if reefer else "Dry"), (0, 0, 0), reefer=reefer)
        out.append(export_model(r, r.name))
    for fn, nm in ((totem, "RedeTotem"), (gatehouse, "RedeGatehouse"), (water_tower, "RedeWaterTower"),
                   (fuel_island, "RedeFuelIsland"), (shopping_bag, "RedeBag"), (wall_medallion, "RedeMedallion")):
        r, _ = fn(nm, (0, 0, 0))
        out.append(export_model(r, nm))
    return out
