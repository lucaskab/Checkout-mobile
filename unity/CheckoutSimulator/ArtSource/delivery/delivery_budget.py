"""delivery_budget.py -- triangle accounting + budget fitting for the delivery previews (Oct 2026)."""
import bpy, math

def _eval_tris(o, dg):
    try:
        ev = o.evaluated_get(dg); me = ev.to_mesh(); t = sum(len(p.vertices) - 2 for p in me.polygons); ev.to_mesh_clear(); return t
    except Exception: return 0

def _lvl(o):
    for md in o.modifiers:
        if md.type == 'SUBSURF': return md, md.render_levels - md.levels
    return None, 0

def tri_total(objs):
    """Triangle count of `objs` at RENDER subdivision (viewport evaluates subsurf at 0; scale by 4^levels)."""
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in objs:
        if o.type not in ('MESH', 'CURVE', 'FONT'): continue
        md, L = _lvl(o); n += _eval_tris(o, dg) * 4 ** L
    return n

def fit_budget(objs, budget, min_level=1, report=None):
    """Lower the render subdivision of the heaviest objects first until the set fits `budget` triangles."""
    dg = bpy.context.evaluated_depsgraph_get(); items = []
    for o in objs:
        if o.type not in ('MESH', 'CURVE', 'FONT'): continue
        md, L = _lvl(o); items.append([o, md, _eval_tris(o, dg), L])
    total = sum(b * 4 ** L for o, md, b, L in items)
    while total > budget:
        cand = [it for it in items if it[1] is not None and it[3] > min_level]
        if not cand: break
        it = max(cand, key=lambda i: i[2] * 4 ** i[3]); before = it[2] * 4 ** it[3]
        it[3] -= 1; it[1].render_levels = it[1].levels + it[3]; total -= before - it[2] * 4 ** it[3]
    while total > budget and min_level > 0:     # phase 2: dense parts (already smooth at base level) may drop their subdivision completely
        cand = [it for it in items if it[1] is not None and it[3] > 0 and it[2] >= 400]
        if not cand: break
        it = max(cand, key=lambda i: i[2] * 4 ** i[3]); before = it[2] * 4 ** it[3]
        it[3] -= 1; it[1].render_levels = it[1].levels + it[3]; total -= before - it[2] * 4 ** it[3]
    while total > budget and min_level > 0:     # phase 3: anything left subdivided, heaviest first
        cand = [it for it in items if it[1] is not None and it[3] > 0]
        if not cand: break
        it = max(cand, key=lambda i: i[2] * 4 ** i[3]); before = it[2] * 4 ** it[3]
        it[3] -= 1; it[1].render_levels = it[1].levels + it[3]; total -= before - it[2] * 4 ** it[3]
    if report is not None: report.update(dict(total=total, budget=budget, min_level=min_level))
    return total

def descendants(root):
    out = []; stack = [root]
    while stack:
        o = stack.pop()
        for c in o.children: out.append(c); stack.append(c)
    return out

def asset_objects(root, kind):
    """kind: 'bike' (everything under root except bau_/logo_ and the rider), 'bau', 'rider' (courier body + helmet)."""
    objs = descendants(root); res = []
    for o in objs:
        n = o.name
        is_bau = n.startswith(("bau_", "logo_"))
        is_rider = "_rider" in n or o.type == 'ARMATURE'
        if kind == 'bau' and is_bau: res.append(o)
        elif kind == 'rider' and is_rider: res.append(o)
        elif kind == 'bike' and not is_bau and not is_rider: res.append(o)
    return res
