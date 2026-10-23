"""Runs decor_v4 items headless:  blender -b --factory-startup --python dv4_run.py -- <id> [<id> ...]
Each id loads ArtSource/decor_v4/items/<id>.py (must define build()). Log lines: [dv4] ..., DV4DONE {json}, DV4FAIL id."""
import sys, os, importlib.util, traceback
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import dv4

def main():
    ids = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not ids:
        print("usage: blender -b --factory-startup --python dv4_run.py -- <id> [<id> ...]"); return
    for id_ in ids:
        path = os.path.join(ROOT, "items", id_ + ".py")
        try:
            spec = importlib.util.spec_from_file_location("item_" + id_.replace("-", "_"), path)
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            dv4.run_item(id_, mod)
        except Exception:
            traceback.print_exc()
            print("DV4FAIL " + id_, flush=True)
    print("DV4ALLDONE", flush=True)

main()
