import sys, os, importlib.util, json
ROOT = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\decor_v4"
sys.path.insert(0, ROOT)
import bpy, dv4
id_ = sys.argv[sys.argv.index("--") + 1]
spec = importlib.util.spec_from_file_location("it", os.path.join(ROOT, "items", id_ + ".py")); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
dv4.reset(); mod.build()
parts = [o for o in dv4.PARTS if not o.get("dv4_skip")]
dv4._select(parts); bpy.ops.object.convert(target="MESH")
counts = {}
for o in parts:
    if o.type == "MESH":
        key = "".join(c for c in o.name if not c.isdigit() and c not in ".-")
        counts[key] = counts.get(key, 0) + dv4.tri_count([o])
print("DBG " + json.dumps(counts), flush=True)
