"""Things the wind moves: Dia de jogo bunting and flag, the FEIRA LIVRE banner, the neighbour's LIQUIDA TUDO
banner and the parasol of the heat wave bench. Each loops "Wind" (4 s).

- Rig_Bunting: the string swings as a whole between its two ends, every flag flutters on its own hinge with the
  wind wave running along the line (one skinned mesh, one bone per flag; the game still stretches it in X).
- Rig_FeiraBanner / Rig_SaleBanner: the cloth (cut into a grid) billows between its ties with a ripple running
  across; posts and ropes stay put.
- Rig_FlagPole: the flag waves on a chain of four bones.
- Rig_SunUmbrella: the parasol canopy rocks in the gusts on the pole top.
"""
import math
from mathutils import Vector, Matrix

FRAMES = 96
TAU = 2 * math.pi


def _wave(t, period, phase=0.0):
    return math.sin(TAU * t / period - phase)


def bunting():
    reset()
    o = import_prop("Jogo_Bunting"); S = o.matrix_world.copy(); W = lambda p: S @ Vector(p)
    flags = sorted([i for i in islands(o) if i.size.z > 0.12], key=lambda i: i.center.x)
    owner = {vi: k for k, i in enumerate(flags) for vi in i.verts}
    bones = [("Root", W((0, 0, 0)), W((0, 0, 0.4)), None), ("Sway", W((0, 0, 0)), W((12, 0, 0)), "Root")]
    for k, i in enumerate(flags):
        top = Vector((i.center.x, 0, i.hi.z))
        bones.append((f"Flag{k:02d}", W(top), W(top - Vector((0, 0, 0.3))), "Sway"))
    arm = armature("Rig_Bunting", Matrix.Identity(4), bones)
    o.name = "Jogo_Bunting__Line"
    skin(o, arm, lambda co, vi: {f"Flag{owner[vi]:02d}": 1.0} if vi in owner else {"Sway": 1.0})
    act = new_action(arm, "Wind", frames=FRAMES)
    X = (1, 0, 0)
    for f in range(1, FRAMES + 2):
        t = f - 1
        pose(arm, "Sway", f, rot=(X, 7 * _wave(t, FRAMES)))
        for k in range(len(flags)):
            pose(arm, f"Flag{k:02d}", f, rot=(X, 16 * _wave(t, FRAMES / 2, k * 0.45) + 4))
    linear(act, "rotation")
    return arm, [o], [act]


def _billow(prop, rig_name, is_cloth, cuts=10):
    """Cloth islands (is_cloth(island)) are joined, cut into a grid and skinned to Billow + two ripple bones."""
    reset()
    o = import_prop(prop); S = o.matrix_world.copy()
    parts = split(o, lambda i: "Cloth" if is_cloth(i) else "Frame")
    cloth = parts["Cloth"]; subdivide(cloth, cuts=cuts)
    pts = [S @ v.co for v in cloth.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    at = lambda u: Vector((lo.x + (hi.x - lo.x) * u, c.y, c.z))
    bones = [("Root", (c.x, c.y, 0), (c.x, c.y, 0.4), None)]
    for name, u in (("Billow", 0.5), ("RippleL", 0.25), ("RippleR", 0.75)):
        bones.append((name, at(u), at(u) + Vector((0, 0.3, 0)), "Root"))
    arm = armature(rig_name, Matrix.Identity(4), bones)

    def weights(co, vi):
        u = (co.x - lo.x) / max(1e-6, hi.x - lo.x); v = (co.z - lo.z) / max(1e-6, hi.z - lo.z)
        shape = 0.35 + 0.65 * math.sin(math.pi * min(1, max(0, v)))
        b = 0.6 * math.sin(math.pi * min(1, max(0, u))) * shape
        l = 0.4 * max(0.0, math.sin(TAU * u)) * shape
        r = 0.4 * max(0.0, -math.sin(TAU * u)) * shape
        return {"Billow": b, "RippleL": l, "RippleR": r, "Root": max(0.0, 1 - b - l - r)}
    skin(cloth, arm, weights)
    if "Frame" in parts:
        attach(parts["Frame"], arm, "Root")
    cloth.name = f"{prop}__Cloth"
    if "Frame" in parts:
        parts["Frame"].name = f"{prop}__Frame"
    act = new_action(arm, "Wind", frames=FRAMES)
    for f in range(1, FRAMES + 2):
        t = f - 1
        pose(arm, "Billow", f, loc=(0, 0.06 + 0.2 * _wave(t, FRAMES), 0))
        pose(arm, "RippleL", f, loc=(0, 0.16 * _wave(t, FRAMES / 2), 0))
        pose(arm, "RippleR", f, loc=(0, 0.16 * _wave(t, FRAMES / 2, math.pi / 2), 0))
    linear(act, "location")
    return arm, [cloth] + ([parts["Frame"]] if "Frame" in parts else []), [act]


def feira_banner():
    return _billow("Feira_Banner", "Rig_FeiraBanner",
                   lambda i: i.lo.x > -1.75 and i.hi.x < 1.75 and i.lo.z > 2.3)


def sale_banner():
    return _billow("FimMes_SaleBanner", "Rig_SaleBanner",
                   lambda i: i.lo.x > -2.02 and i.hi.x < 2.02)


def flagpole():
    reset()
    o = import_prop("Jogo_FlagPole"); S = o.matrix_world.copy(); W = lambda p: S @ Vector(p)
    parts = split(o, lambda i: "Flag" if i.lo.x > 0.03 and i.lo.z > 3.1 else "Pole")
    flag = parts["Flag"]; subdivide(flag, cuts=8, min_length=0.2)
    root = Vector((0.05, -0.02, 3.55)); tip = Vector((0.98, 0.36, 3.55))
    n = 4; seg = [(root.lerp(tip, k / n), root.lerp(tip, (k + 1) / n)) for k in range(n)]
    bones = [("Root", W((0, 0, 0)), W((0, 0, 0.5)), None)]
    for k, (a, b) in enumerate(seg):
        bones.append((f"Flag{k}", W(a), W(b), "Root" if k == 0 else f"Flag{k - 1}"))
    arm = armature("Rig_FlagPole", Matrix.Identity(4), bones)
    A, B = W(root), W(tip); L = (B - A).length; d = (B - A).normalized()

    def weights(co, vi):
        x = max(0.0, min(0.9999, (co - A).dot(d) / L)) * n
        k = int(x); f = x - k
        if k + 1 >= n:
            return {f"Flag{k}": 1.0}
        return {f"Flag{k}": 1 - f, f"Flag{k + 1}": f}
    skin(flag, arm, weights)
    attach(parts["Pole"], arm, "Root")
    flag.name = "Jogo_FlagPole__Flag"; parts["Pole"].name = "Jogo_FlagPole__Pole"
    act = new_action(arm, "Wind", frames=FRAMES)
    Z = (0, 0, 1)
    for f in range(1, FRAMES + 2):
        t = f - 1
        for k in range(n):
            pose(arm, f"Flag{k}", f, rot=(Z, (6 + 4 * k) * _wave(t, FRAMES / 3, k * 0.9)))
    linear(act, "rotation")
    return arm, [flag, parts["Pole"]], [act]


def sun_umbrella():
    reset()
    o = import_prop("Calor_SunUmbrellaBench"); S = o.matrix_world.copy(); W = lambda p: S @ Vector(p)
    parts = split(o, lambda i: "Canopy" if i.lo.z >= 1.95 else "Bench")
    top = Vector((0, 0.55, 1.98))
    arm = armature("Rig_SunUmbrella", Matrix.Identity(4), [
        ("Root", W((0, 0.55, 0)), W((0, 0.55, 0.5)), None),
        ("Canopy", W(top), W(top + Vector((0, 0, 0.4))), "Root"),
    ])
    attach(parts["Bench"], arm, "Root"); attach(parts["Canopy"], arm, "Canopy")
    parts["Bench"].name = "Calor_SunUmbrellaBench__Bench"; parts["Canopy"].name = "Calor_SunUmbrellaBench__Canopy"
    act = new_action(arm, "Wind", frames=FRAMES)
    for f in range(1, FRAMES + 2):
        t = f - 1
        q = compose(((1, 0, 0), 2.5 * _wave(t, FRAMES)), ((0, 1, 0), 1.5 * _wave(t, FRAMES / 2, 1.0)))
        pose_q(arm, "Canopy", f, q)
    linear(act, "rotation")
    return arm, list(parts.values()), [act]


BUILDERS = {"Rig_Bunting": bunting, "Rig_FeiraBanner": feira_banner, "Rig_SaleBanner": sale_banner,
            "Rig_FlagPole": flagpole, "Rig_SunUmbrella": sun_umbrella}
