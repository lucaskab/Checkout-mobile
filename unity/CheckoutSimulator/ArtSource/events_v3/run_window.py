# headless: blender -b --factory-startup --python run_window.py   -> Review/vehicles_v3/jam_window.png
# Builds the v3 Transito_Car, exports it to Temp/qa/v3props (NOT Assets), rigs it with events_interactive/window_sale.py
# (Window_Driver + driver bust + clips) and renders window up / window down + Driver_WaveOut / front 3-4.
import sys, os, time, importlib.util, math, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(ART)))
UNITY = os.path.join(REPO, "unity", "CheckoutSimulator")
for pth in (ART, os.path.join(ART, "events_v2"), os.path.join(REPO, "scripts", "blender")):
    sys.path.insert(0, pth)
import bpy
from mathutils import Vector, Matrix
REVIEW = os.path.join(ART, "Review", "vehicles_v3")
TMPP = os.path.join(UNITY, "Temp", "qa", "v3props")
os.makedirs(TMPP, exist_ok=True)
t0 = time.time()
try:
    import events_kit as E
    spec = importlib.util.spec_from_file_location("vehicles3", os.path.join(HERE, "vehicles.py"))
    V3 = importlib.util.module_from_spec(spec); sys.modules["vehicles3"] = V3; spec.loader.exec_module(V3)
    for n in ("Cube", "Light", "Camera"):
        if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    c = E.prop_collection("Transito_Car"); V3.mats(); V3.PROPS["Transito_Car"][0](c)
    print("EXPORT_TMP", E.export_prop("Transito_Car", size=1024, out=TMPP), round(time.time() - t0, 1), flush=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    WS = os.path.join(ART, "events_interactive", "window_sale.py")
    g = {"__name__": "window_sale"}
    exec(open(WS, encoding="utf-8").read(), g)
    g["rk"].PROPS = TMPP; g["rk"].import_prop.__globals__["PROPS"] = TMPP   # the script-module functions keep their own globals
    g["rk"].reset()
    bpy.context.scene.frame_set(1)
    car, parts, info = g["rig_car"]()
    acts = g["car_clips"](car)
    CA = {a.name: a for a in acts}
    studio, aim, label, render, contact_sheet, set_action, street, hide_label = (g[k] for k in ("studio", "aim", "label", "render", "contact_sheet", "set_action", "street", "hide_label"))
    bust = parts[-1]
    print("RIG bones", [b.name for b in car.data.bones], "parts", [p.name for p in parts], "car_tris", g["tris"](parts[:-1]), "driver_tris", g["tris"]([bust]), flush=True)
    studio(res=(900, 700), ground=False)
    st = street()
    shots = []
    for name, act, f in (("window up (rest)", "Car_WindowUp", 18), ("window down - Driver_WaveOut f12", "Driver_WaveOut", 12), ("window down - Driver_WaveOut f36", "Driver_WaveOut", 36)):
        if name.startswith("window down"):
            set_action(car, CA["Car_WindowDown"], 18)
            win = car.pose.bones["Window_Driver"].location.copy()
            set_action(car, CA[act], f); car.pose.bones["Window_Driver"].location = win
            bpy.context.view_layer.update()
        else:
            set_action(car, CA[act], f)
        aim((-0.2, -0.3, 0.75), (-0.55, -1.0, 0.55), 7.5, lens=55)
        label(name, 0.045)
        shots.append(render(os.path.join(REVIEW, f"_jam_{len(shots)}.png")))
    # whole car with the driver, from the road side
    aim((0.0, 0.0, 0.8), (-0.8, 0.9, 0.6), 8.5, lens=50)
    label("Rig_Car (v3) - window down, driver", 0.045)
    shots.append(render(os.path.join(REVIEW, f"_jam_{len(shots)}.png")))
    contact_sheet(shots, os.path.join(REVIEW, "jam_window.png"), cols=2)
    print("JAM", os.path.join(REVIEW, "jam_window.png"), round(time.time() - t0, 1), flush=True)
    print("DONE", flush=True)
except Exception:
    traceback.print_exc(); print("FAILED", flush=True)
