"""Runs the social v1 art inside an already open Blender (the MCP add-on session) without touching the open file:
everything is built in its own scenes ("SocialArt" for the decorations, "SocialIcons" for the UI icons), and the user's
scene is put back after each call. Never calls read_factory_settings and never deletes data outside those scenes
(only orphan datablocks this pipeline created).

    NS = {}; exec(open(ART + "/social_art/social_run.py").read(), NS)
    NS["run_decor"]("invite-reward-1")         # decor_v4 pipeline: realize, bake atlas, FBX, thumb, previews
    NS["run_icons"](["friends", "gift"])       # build_ui_sprites pipeline: 512 px transparent PNGs

Outputs: ArtSource/social_art/{fbx,tex,thumbs,previews,icons}/ and report.json.
"""
import os, sys, re, types, time, json, importlib.util, traceback
import bpy

ART = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/ArtSource"
REPO = "/Users/lucas-furini/repos/checkout"
SA = os.path.join(ART, "social_art")
ITEMS = os.path.join(SA, "items")
DV4_ITEMS = os.path.join(ART, "decor_v4", "items")
LOG = os.path.join(SA, "run.log")
os.makedirs(SA, exist_ok=True)


def log(*a):
    with open(LOG, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a) + "\n")


def _scene(name):
    sc = bpy.data.scenes.get(name) or bpy.data.scenes.new(name)
    win = bpy.context.window
    prev = win.scene
    win.scene = sc
    return sc, prev


def _purge_orphans(prefixes):
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.textures, bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for b in list(coll):
            if b.users == 0:
                coll.remove(b)
    for b in list(bpy.data.materials):
        if b.users == 0 and b.name.startswith(prefixes):
            bpy.data.materials.remove(b)
    for b in list(bpy.data.images):
        if b.users == 0 and b.name.startswith(("IK_D4_", "Social")):
            bpy.data.images.remove(b)


# ================================================================================================ decorations (decor_v4)
def load_dv4():
    src = open(os.path.join(ART, "decor_v4", "dv4.py")).read()
    src = re.sub(r'^ROOT = .*$', 'ROOT = %r' % SA, src, count=1, flags=re.M)
    src = re.sub(r'^ASSETS = .*$', 'ASSETS = %r' % os.path.join(REPO, "unity", "CheckoutSimulator", "Assets"), src, count=1, flags=re.M)
    mod = types.ModuleType("dv4")
    mod.__file__ = os.path.join(SA, "dv4_patched.py")
    exec(compile(src, "dv4.py", "exec"), mod.__dict__)
    sys.modules["dv4"] = mod
    for k in [k for k in sys.modules if k.startswith(("_lib_", "_social_lib", "item_"))]:
        del sys.modules[k]
    for p in (DV4_ITEMS, ITEMS):
        if p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)

    def safe_reset():
        sc = bpy.data.scenes.get("SocialArt") or bpy.data.scenes.new("SocialArt")
        bpy.context.window.scene = sc
        for o in list(sc.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        _purge_orphans(("P_", "OV_", "T_IK_D4_", "C_", "E_", "G_", "DV4_", "old_"))
        mod.PARTS.clear(); mod.PIVOTS.clear()
        sc.unit_settings.system = "METRIC"; sc.unit_settings.scale_length = 1
        return sc

    def cpu():
        bpy.context.scene.cycles.device = "CPU"
        return False

    orig_bake = mod.bake

    def bake(outs, name, size, samples=64):
        return orig_bake(outs, name, size, min(samples, 32))

    mod.reset = safe_reset
    mod.gpu = cpu
    mod.bake = bake
    mod.render_old = lambda id_, floor: None
    return mod


def run_decor(id_):
    """One decoration per call (keeps each MCP call short)."""
    win = bpy.context.window
    prev = win.scene
    open(LOG, "a").close()
    log("decor start", id_)
    try:
        dv4 = load_dv4()
        spec = importlib.util.spec_from_file_location("item_" + id_.replace("-", "_"), os.path.join(ITEMS, id_ + ".py"))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        entry = dv4.run_item(id_, m)
        log("decor done", id_, entry["tris"], entry["secs"])
        return entry
    except Exception:
        log("decor FAIL", id_, traceback.format_exc())
        raise
    finally:
        try:
            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
        win.scene = prev


def save_blend(path=os.path.join(SA, "social_art.blend")):
    scenes = {s for s in (bpy.data.scenes.get("SocialArt"), bpy.data.scenes.get("SocialIcons")) if s}
    bpy.data.libraries.write(path, scenes, fake_user=True, compress=True)
    return path


# ================================================================================================ UI icons (build_ui_sprites)
def run_icons(names, size=512):
    win = bpy.context.window
    prev = win.scene
    log("icons start", names)
    try:
        sc, _ = _scene("SocialIcons")
        NS = {"__file__": os.path.join(REPO, "scripts", "blender", "build_ui_sprites.py"), "__name__": "social_sprites"}
        exec(open(os.path.join(REPO, "scripts", "blender", "build_ui_sprites.py")).read(), NS)
        exec(open(os.path.join(SA, "social_icons.py")).read(), NS)
        out = os.path.join(SA, "icons")
        os.makedirs(out, exist_ok=True)

        def safe_reset():
            s = bpy.context.scene
            for o in list(s.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            _purge_orphans(("M_", "T_"))
            NS["_mats"].clear(); NS["MARKS"].clear()
        NS["reset"] = safe_reset
        NS["DEVICE"] = "CPU"
        done = []
        for n in names:
            safe_reset()
            NS["SOCIAL_ICONS"][n]()
            s = bpy.context.scene
            s.cycles.device = "CPU"
            s.render.resolution_x = s.render.resolution_y = size
            s.render.filepath = os.path.join(out, n + ".png")
            bpy.ops.render.render(write_still=True, scene=s.name)
            done.append(s.render.filepath)
            log("icon", n)
        return done
    except Exception:
        log("icons FAIL", traceback.format_exc())
        raise
    finally:
        win.scene = prev
