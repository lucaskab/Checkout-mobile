# headless runner: blender -b --factory-startup --python run_scenes.py -- preview v2_HoraDoRush ... | export Rush_CityBus ... | tris
import sys, os, traceback, time
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
sys.path.insert(0, ART); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(ART))), "scripts", "blender"))
import bpy
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
mode, names = argv[0], argv[1:]
t0 = time.time()
try:
    import events_kit as E, scenes as V
    if mode == "preview":
        for n in names:
            E.build(n)
            # tris of the props (excluding diorama + actors)
            dg = bpy.context.evaluated_depsgraph_get()
            path = E.preview(n, res=(1600, 1000), ortho={"v2_CafeComEquipe": 11, "v2_Viralizou": 12, "v2_FimDoMes": 14, "v2_TurnoPuxado": 8.5}.get(n, 13),
                             target={"v2_FimDoMes": (-2.6, 2.4, 1.3), "v2_TurnoPuxado": (.4, 2.6, 1.3), "v2_Viralizou": (1.6, 1.5, 1.1), "v2_CafeComEquipe": (0, 1.8, 1.0)}.get(n))
            print("PREVIEW", n, path, round(time.time() - t0, 1), flush=True)
    elif mode == "closeup":
        # closeup <Prop> [ortho] : the prop alone on a plain floor, ArtSource/Review/events_v2/cu_<Prop>.png
        n = names[0]; ortho = float(names[1]) if len(names) > 1 else 3.0
        c = E.clear("EV cu_" + n); V.mats(); objs = V.PROPS[n][0](c)
        import era_kit as k
        from mathutils import Matrix
        zmin = min((o.matrix_world @ __import__("mathutils").Vector(v)).z for o in objs for v in o.bound_box)
        if zmin < -.01:
            for o in objs: o.matrix_world = Matrix.Translation((0, 0, -zmin + .02)) @ o.matrix_world
        k.box("floor", (6, 6, .02), (0, 0, -.011), E.mats()["pavers"], bevel=0, c=c)
        from mathutils import Vector
        lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
        for o in objs:
            for v in o.bound_box:
                w = o.matrix_world @ Vector(v); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        path = E.preview("cu_" + n, res=(1200, 900), ortho=ortho, target=(lo + hi) / 2)
        print("CLOSEUP", n, path, flush=True)
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
