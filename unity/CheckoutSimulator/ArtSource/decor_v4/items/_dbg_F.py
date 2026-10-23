"""Debug render of an exported fbx without its G_Glass faces (group F): blender -b --factory-startup --python items/_dbg_F.py -- <id>"""
import sys, os, collections
import bpy, bmesh
from mathutils import Vector
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import dv4
id_ = sys.argv[sys.argv.index("--") + 1]
dv4.reset()
bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, "fbx", id_ + ".fbx"))
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in objs:
    print("DBG obj", o.name, [m.name if m else None for m in o.data.materials], len(o.data.polygons))
    cnt = collections.Counter(p.material_index for p in o.data.polygons)
    print("DBG faces per slot", dict(cnt))
    for i, m in enumerate(o.data.materials):
        if m is None:
            continue
        key = m.name.split(".")[0]
        pts = [o.matrix_world @ o.data.vertices[v].co for p in o.data.polygons if p.material_index == i for v in p.vertices]
        if pts:
            lo = Vector(map(min, *pts)); hi = Vector(map(max, *pts))
            print("DBG slot", i, key, "bbox", [round(c, 3) for c in lo], [round(c, 3) for c in hi])
        if key == "G_Glass":
            bm = bmesh.new(); bm.from_mesh(o.data)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == i], context="FACES")
            bm.to_mesh(o.data); bm.free()
            print("DBG deleted glass faces")
        else:
            if key.startswith("T_"):
                bpy.data.materials.remove(m) if False else None
                nm = bpy.data.materials.new(key + "_dbg"); nm.use_nodes = True
                bsdf = nm.node_tree.nodes.get("Principled BSDF")
                p = os.path.join(dv4.D["tex"], key[2:] + "_albedo.png")
                if os.path.exists(p):
                    img = bpy.data.images.load(p); ti = nm.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = img
                    nm.node_tree.links.new(ti.outputs["Color"], bsdf.inputs["Base Color"])
                o.data.materials[i] = nm
            else:
                o.data.materials[i] = dv4.preview_material(key)
dv4.previews(objs, os.path.join(dv4.D["previews"], "F_dbg_" + id_), "C9C3B8", views=(("close", 36, 22, 1.55, 45), ("front", 10, 30, 1.3, 50)))
print("DBGDONE")
