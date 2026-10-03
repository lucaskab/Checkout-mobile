import sys, os, bpy
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
sys.path.insert(0, ART); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(ART))), "scripts", "blender"))
import events_kit as E, scenes as V
n = "Viral_HeartPop"
c = E.prop_collection(n); V.mats(); V.PROPS[n][0](c)
src = [o for o in c.all_objects if o.type == 'MESH']
def count(dg):
    t = 0
    for o in src:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); me.calc_loop_triangles(); t += len(me.loop_triangles)
    return t
print("A before exclude", count(bpy.context.evaluated_depsgraph_get()), flush=True)
for lc in bpy.context.view_layer.layer_collection.children:
    lc.exclude = lc.name not in ("EP export tmp", "Studio")
print("B after exclude", count(bpy.context.evaluated_depsgraph_get()), flush=True)
