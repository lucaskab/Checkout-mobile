import bpy, os, json, sys
ROOT = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\decor_v4"
out = {}
for id_ in ("plant-small", "park-bench", "fountain"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, "fbx", id_ + ".fbx"))
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    info = []
    for o in objs:
        me = o.data
        info.append({"name": o.name, "loc": [round(c, 3) for c in o.location], "dims": [round(c, 3) for c in o.dimensions],
                     "mats": [m.name for m in me.materials], "tris": sum(len(p.vertices) - 2 for p in me.polygons),
                     "custom_normals": bool(me.has_custom_normals), "uv": [u.name for u in me.uv_layers]})
    out[id_] = info
print("CHK " + json.dumps(out), flush=True)
