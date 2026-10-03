# headless runner: blender -b --factory-startup --python run_vehicles.py -- preview v2_HoraDoRush ... | export Rush_CityBus ... | tris
import sys, os, traceback, time
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
sys.path.insert(0, ART); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(ART))), "scripts", "blender"))
import bpy
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
mode, names = argv[0], argv[1:]
t0 = time.time()
try:
    import events_kit as E, vehicles as V
    if mode == "preview":
        for n in names:
            E.build(n)
            # tris of the props (excluding diorama + actors)
            dg = bpy.context.evaluated_depsgraph_get()
            path = E.preview(n, res=(1600, 1000), ortho={"v2_HoraDoRush": 16.5, "v2_Engarrafamento": 17, "v2_ExcursaoDaEscola": 15, "v2_CaminhaoDeOfertas": 15, "v2_CarroDeSom": 14}.get(n, 13))
            print("PREVIEW", n, path, round(time.time() - t0, 1), flush=True)
    elif mode == "tris":
        for n in names:
            c = E.prop_collection(n); V.mats(); V.PROPS[n][0](c)
            dg = bpy.context.evaluated_depsgraph_get(); t = 0
            for o in c.all_objects:
                if o.type == 'MESH':
                    me = o.evaluated_get(dg).data; me.calc_loop_triangles(); t += len(me.loop_triangles)
            print("TRIS", n, t, flush=True)
            agg = {}
            for o in c.all_objects:
                if o.type == 'MESH':
                    me = o.evaluated_get(dg).data; me.calc_loop_triangles()
                    key = o.name.rstrip("0123456789.")
                    agg[key] = agg.get(key, 0) + len(me.loop_triangles)
            print("  ", sorted(agg.items(), key=lambda kv: -kv[1])[:14], flush=True)
    elif mode == "export":
        V.export(names or None)
    print("DONE", round(time.time() - t0, 1), flush=True)
except Exception:
    traceback.print_exc(); print("FAILED", flush=True)
