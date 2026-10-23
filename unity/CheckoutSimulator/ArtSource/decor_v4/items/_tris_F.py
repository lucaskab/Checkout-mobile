"""Per-part triangle profiler for group F items (headless):
blender -b --factory-startup --python items/_tris_F.py -- <id>"""
import sys, os, importlib.util, collections
import bpy
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "items"))
import dv4

id_ = sys.argv[sys.argv.index("--") + 1]
spec = importlib.util.spec_from_file_location("item_x", os.path.join(ROOT, "items", id_ + ".py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
dv4.reset(); dv4.RNG.seed(getattr(mod, "CONFIG", {}).get("seed", 4))
mod.build()
dg = bpy.context.evaluated_depsgraph_get()
counts = collections.Counter(); groups = collections.Counter()
import re
for o in dv4.PARTS:
    if o.get("dv4_skip"):
        continue
    try:
        me = o.evaluated_get(dg).to_mesh()
        t = sum(len(p.vertices) - 2 for p in me.polygons)
    except Exception:
        t = 0
    key = re.sub(r"[-\d.]+$", "", o.name)
    counts[key] += t; groups[key] += 1
total = sum(counts.values())
print("TRIS_TOTAL", total)
for k, v in counts.most_common(40):
    print("TRIS %6d  %3d  %s" % (v, groups[k], k))
