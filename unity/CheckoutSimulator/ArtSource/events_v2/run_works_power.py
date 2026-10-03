# headless runner: blender -b --factory-startup --python run_works_power.py -- preview v2_RuaEmObras ... | export Obras_Backhoe ... | tris Obras_Backhoe ...
import sys, os, traceback, time
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
sys.path.insert(0, ART); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(ART))), "scripts", "blender"))
import bpy
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
mode, names = argv[0], argv[1:]
t0 = time.time()
try:
    import events_kit as E, works_power as WP
    if mode == "preview":
        for n in names:
            E.build(n)
            # actor offsets: evaluated mesh bbox centre vs holder (the rigs' actions move their root)
            dg = bpy.context.evaluated_depsgraph_get()
            for h in [o for o in bpy.data.collections["EV " + n].objects if o.name.startswith("actor_")]:
                pts = []
                for r in h.children:
                    for mo in r.children:
                        if mo.type == 'MESH':
                            me = mo.evaluated_get(dg); pts += [me.matrix_world @ v.co for v in me.data.vertices]
                if pts:
                    cx = sum(p.x for p in pts) / len(pts); cy = sum(p.y for p in pts) / len(pts); mz = min(p.z for p in pts)
                    print("ACTOR", h.name, "holder", tuple(round(v, 2) for v in h.location), "mesh centre", round(cx, 2), round(cy, 2), "minz", round(mz, 2), flush=True)
            path = E.preview(n, res=(1600, 1000), ortho={"v2_RuaEmObras": 16, "v2_QuedaDeEnergia": 18, "v2_Maquininha": 15.5}.get(n, 14),
                             target={"v2_QuedaDeEnergia": (0.8, .6, 2.6), "v2_Maquininha": (0, 1.2, 2.2), "v2_RuaEmObras": (-1.3, .3, 1.0)}.get(n))
            print("PREVIEW", n, path, round(time.time() - t0, 1), flush=True)
    elif mode == "tris":
        for n in (names or WP.PROPS):
            c = E.prop_collection(n); WP.mats(); WP.PROPS[n][0](c)
            dg = bpy.context.evaluated_depsgraph_get(); t = 0; agg = {}
            for o in c.all_objects:
                if o.type == 'MESH':
                    me = o.evaluated_get(dg).data; me.calc_loop_triangles(); t += len(me.loop_triangles)
                    key = o.name.rstrip("0123456789."); agg[key] = agg.get(key, 0) + len(me.loop_triangles)
            print("TRIS", n, t, sorted(agg.items(), key=lambda kv: -kv[1])[:10], flush=True)
    elif mode == "export":
        WP.export(names or None)
    print("DONE", round(time.time() - t0, 1), flush=True)
except Exception:
    traceback.print_exc(); print("FAILED", flush=True)
