"""Special sectors, round 3: detailed products and set dressing (exec'd into the fixture_tiers namespace).

    G = {"__name__": "ft", "REPO": R}
    exec(open(R + "/scripts/blender/fixture_tiers.py").read(), G)
    exec(open(R + "/scripts/blender/sector_detail.py").read(), G)

Products are real silhouettes (swept, lathed and extruded bmesh) painted from one atlas, FT_Sector_albedo.png
(scripts/blender/sector_atlas.py, 8x8 cells, no words or letters). Material "T_FT_Sector" -> Unity KitRemap
"IK_PT_Sector" with Assets/Art/Interior/Textures/FT_Sector_albedo.png. Structure keeps the navy / cream / gold /
wood kit materials, so the market paint still recolours the navy and gold.
"""
SD = "T_FT_Sector"
SD_CELLS = [
    ["loaf", "boule", "baguette", "croissant", "roll", "cake_choc", "cake_straw", "cake_cream"],
    ["steak", "tbone", "ribs", "chop", "sausage", "chicken", "ham", "salami"],
    ["rind_wax", "rind_natural", "cheese_cut", "blue_cut", "provolone", "brie", "parmesan", "ground"],
    ["fish_blue", "fish_red", "salmon", "shrimp", "lobster", "squid", "lemon_cut", "ice"],
    ["gelato_pistachio", "gelato_choc", "gelato_straw", "gelato_cream", "gelato_mint", "gelato_mango", "gelato_berry", "sprinkles"],
    ["waffle", "wl_grape", "wl_glass", "bottle_wall", "wl_leaf", "wl_star", "cork", "burlap"],
    ["orange_cut", "lime_cut", "kiwi_cut", "melon_cut", "strawberry", "pineapple", "apple", "melon_skin"],
    ["chalk_bread", "chalk_meat", "chalk_cheese", "chalk_fish", "chalk_ice", "chalk_wine", "chalk_juice", "leaf"],
]
SD_INDEX = {n: (c, r) for r, row in enumerate(SD_CELLS) for c, n in enumerate(row)}
for _n, _cr in SD_INDEX.items():           # lathe_bm(uv_cell=...) resolves cells through rk_core.LABELS
    rk_core.LABELS["sd:" + _n] = _cr
WARM = "E_FFC67A"                          # warm bulb glow
WOOD_PEEL = WOOD_L


def sd_material():
    m = bpy.data.materials.get(SD) or bpy.data.materials.new(SD)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    t = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.get("FT_Sector_albedo.png")
    if img:
        img.reload()
    else:
        img = bpy.data.images.load(os.path.join(ART, "textures", "FT_Sector_albedo.png"))
    t.image = img
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = .5
    w = material(WARM)
    w.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = 6.0


def cuv(name, u, v, inset=.015):
    c, r = SD_INDEX[name]
    u = inset + min(1, max(0, u)) * (1 - 2 * inset)
    v = inset + min(1, max(0, v)) * (1 - 2 * inset)
    return ((c + u) / 8, 1 - (r + 1 - v) / 8)


def _uvl(bm):
    return bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")


def planar(bm, cell, ax=(0, 1), lo=None, hi=None, rot=0.0):
    """Project every loop onto two axes, normalised to the bounds (or lo/hi), into one atlas cell."""
    uvl = _uvl(bm)
    if lo is None:
        lo = [min(v.co[a] for v in bm.verts) for a in ax]
        hi = [max(v.co[a] for v in bm.verts) for a in ax]
    ca, sa = math.cos(rot), math.sin(rot)
    for f in bm.faces:
        for l in f.loops:
            u = (l.vert.co[ax[0]] - lo[0]) / max(1e-6, hi[0] - lo[0]) - .5
            v = (l.vert.co[ax[1]] - lo[1]) / max(1e-6, hi[1] - lo[1]) - .5
            l[uvl].uv = cuv(cell, .5 + u * ca - v * sa, .5 + u * sa + v * ca)
    return bm


def tiled(bm, cell, size=.25, ax=None):
    """Per-face tiling of one cell (seams hide in noisy textures such as ice and burlap)."""
    uvl = _uvl(bm)
    for f in bm.faces:
        n = f.normal
        a = ax or [i for i in range(3) if i != max(range(3), key=lambda k: abs(n[k]))]
        cen = f.calc_center_median()
        base = [math.floor(cen[a[0]] / size) * size, math.floor(cen[a[1]] / size) * size]
        for l in f.loops:
            l[uvl].uv = cuv(cell, (l.vert.co[a[0]] - base[0]) / size, (l.vert.co[a[1]] - base[1]) / size)
    return bm


def sweep_bm(pts, rad, seg=10, cell=None, caps=True, v_of=None, up=(0, 0, 1)):
    """Loft along a polyline. rad(t) -> r or (rw, rh): rw along the side axis, rh along the 'up' axis.
    UV: u = t along the path (cell x), v = around (v_of(angle) or 0.5 + 0.5 sin(angle), 1 = up side)."""
    P = [Vector(p) for p in pts]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    U = Vector(up)
    rings = []
    L = [0.0]
    for i in range(1, len(P)):
        L.append(L[-1] + (P[i] - P[i - 1]).length)
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        side = t.cross(U)
        if side.length < 1e-4:
            side = t.cross(Vector((1, 0, 0)))
        side.normalize()
        upv = side.cross(t).normalized()
        r = rad(L[i] / L[-1])
        rw, rh = (r, r) if not isinstance(r, tuple) else r
        rings.append([bm.verts.new(p + side * math.cos(2 * math.pi * j / seg) * rw + upv * math.sin(2 * math.pi * j / seg) * rh) for j in range(seg + 1)])
    for i in range(len(rings) - 1):
        for j in range(seg):
            f = bm.faces.new((rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                a = 2 * math.pi * jj / seg
                v = v_of(a) if v_of else .5 + .5 * math.sin(a)
                l[uvl].uv = cuv(cell, L[ii] / L[-1], v) if cell else (L[ii] / L[-1], v)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    if caps:
        for ring in (rings[0], rings[-1]):
            vs = [v for v in ring[:seg] if v.is_valid]
            if len(vs) > 2:
                try:
                    f = bm.faces.new(vs)
                    for l in f.loops:
                        l[uvl].uv = cuv(cell, .02, .5) if cell else (0, 0)
                except ValueError:
                    pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def outline_bm(pts2d, t, z0=0.0):
    """Extruded flat outline (x, y) of thickness t, bottom at z0."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in pts2d]
    hi = [bm.verts.new((x, y, z0 + t)) for x, y in pts2d]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    n = len(pts2d)
    for i in range(n):
        bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def blob_outline(rx, ry, n=16, seed=0, wob=.12, pinch=None):
    rnd = random.Random(seed)
    ph = [rnd.random() * 6.28 for _ in range(3)]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + wob * (.6 * math.sin(2 * a + ph[0]) + .4 * math.sin(3 * a + ph[1]))
        if pinch:
            k *= 1 - pinch * max(0, math.cos(a - ph[2])) ** 6
        pts.append((rx * k * math.cos(a), ry * k * math.sin(a)))
    return pts


def arc_lathe_bm(profile, a0, a1, seg, side_cell, cut_cell=None, cap_cell=None):
    """Partial surface of revolution from angle a0 to a1 (radians), with flat cut faces and caps (cheese)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    R = max(r for r, z in profile)
    z0, z1 = profile[0][1], profile[-1][1]
    rings = [[bm.verts.new((r * math.cos(a0 + (a1 - a0) * j / seg), r * math.sin(a0 + (a1 - a0) * j / seg), z)) for j in range(seg + 1)] for r, z in profile]
    for i in range(len(profile) - 1):
        for j in range(seg):
            f = bm.faces.new((rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                l[uvl].uv = cuv(side_cell, (a1 - a0) * jj / seg / (2 * math.pi) * 2 % 1.0001, (profile[ii][1] - z0) / (z1 - z0))
    cb = bm.verts.new((0, 0, z0))
    ct = bm.verts.new((0, 0, z1))
    for j in range(seg):
        for ring, c, rev in ((rings[0], cb, True), (rings[-1], ct, False)):
            vs = [c, ring[j], ring[j + 1]]
            f = bm.faces.new(list(reversed(vs)) if rev else vs)
            for l in f.loops:
                l[uvl].uv = cuv(cap_cell or side_cell, .5 + .5 * l.vert.co.x / R, .5 + .5 * l.vert.co.y / R)
    if abs(a1 - a0) < 2 * math.pi - 1e-3:
        axis = [bm.verts.new((0, 0, z)) for r, z in profile]
        for j, rev in ((0, False), (seg, True)):
            for i in range(len(profile) - 1):
                vs = [axis[i], rings[i][j], rings[i + 1][j], axis[i + 1]]
                f = bm.faces.new(list(reversed(vs)) if rev else vs)
                for l in f.loops:
                    rr = (l.vert.co.x ** 2 + l.vert.co.y ** 2) ** .5
                    l[uvl].uv = cuv(cut_cell or side_cell, rr / R, (l.vert.co.z - z0) / (z1 - z0))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def grid_bm(w, h, cell):
    """Flat grid in the XZ plane (facing -Y) whose quads are `cell` metres, for per-face tiling."""
    nx, nz = max(1, round(w / cell)), max(1, round(h / cell))
    bm = bmesh.new()
    V = [[bm.verts.new((-w / 2 + w * i / nx, 0, -h / 2 + h * j / nz)) for j in range(nz + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(nz):
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    return bm


def put(acc, bm, key, loc=(0, 0, 0), rot=(0, 0, 0), grp="Body"):
    place(bm, loc, rot)
    acc.add(bm, key, grp)


def flat_bottom(bm, z_cut):
    for v in bm.verts:
        if v.co.z < z_cut:
            v.co.z = z_cut + (v.co.z - z_cut) * .12
    lo = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= lo
    return bm


# ================================================================================================ bakery products
def sd_loaf(acc, loc, L=.26, W=.13, H=.1, yaw=0, cell="loaf", seed=0, grp="Body"):
    bm = blob_bm((L / 2, W / 2, H / 1.6), 2, .03, seed)
    flat_bottom(bm, -H * .25)
    planar(bm, cell)
    put(acc, bm, SD, loc, (0, 0, yaw), grp)


def sd_boule(acc, loc, r=.1, seed=0, grp="Body"):
    sd_loaf(acc, loc, r * 2, r * 2, r * 1.1, seed * 37, "boule", seed, grp)


def sd_baguette(acc, loc, L=.56, r=.034, yaw=0, pitch=0, seed=0, grp="Body"):
    pts = [(-L / 2 + L * i / 6, 0, .012 * math.sin(math.pi * i / 6)) for i in range(7)]
    bm = sweep_bm(pts, lambda t: (r * (.35 + .65 * math.sin(math.pi * min(1, max(0, t * 1.04 - .02))) ** .35), r * .85 * (.35 + .65 * math.sin(math.pi * t) ** .35)), 6, "baguette")
    put(acc, bm, SD, loc, (0, pitch, yaw), grp)


def sd_croissant(acc, loc, s=1.0, yaw=0, grp="Body"):
    pts = []
    for i in range(8):
        a = math.radians(-75 + i * 150 / 7)
        pts.append((.065 * s * math.sin(a), -.038 * s * math.cos(a) + .02 * s, 0))
    rad = lambda t: (.03 * s * (.3 + .7 * math.sin(math.pi * t) ** .8) * (1 + .1 * math.cos(t * math.pi * 7)), .022 * s * (.3 + .7 * math.sin(math.pi * t)))
    bm = sweep_bm(pts, rad, 7, "croissant")
    flat_bottom(bm, min(v.co.z for v in bm.verts) + .006 * s)
    put(acc, bm, SD, loc, (0, 0, yaw), grp)


def sd_roll(acc, loc, r=.045, seed=0, grp="Body"):
    bm = blob_bm((r, r * .92, r * .75), 2, .05, seed)
    flat_bottom(bm, -r * .3)
    planar(bm, "roll", rot=seed * .7)
    put(acc, bm, SD, loc, (0, 0, 0), grp)


FROST = {"choc": "5A301E", "straw": "F4A6C1", "cream": "FAF4E4"}


def sd_cake(acc, loc, r=.1, h=.085, kind="straw", grp="Body"):
    x, y, z = loc
    lathe(acc, [(r, 0), (r, h)], loc, SD, 12, 0, grp=grp, uv_cell="sd:cake_" + kind, u_rep=1, v_range=(0, h), cap_top=False, cap_bottom=False)
    lathe(acc, [(r * 1.005, h), (r * .98, h + .008), (0, h + .01)], loc, C(FROST[kind]), 12, 0, grp=grp, cap_bottom=False)
    for k in range(6):
        a = k * math.pi / 3
        lathe(acc, [(0, 0), (.013, 0), (0, .02)], (x + r * .82 * math.cos(a), y + r * .82 * math.sin(a), z + h + .008), C(FROST[kind] if kind != "choc" else "FAF4E4"), 5, 0, grp=grp)
    if kind == "straw":
        for k in range(5):
            a = k * 2 * math.pi / 5
            lathe(acc, [(0, 0), (.014, .004), (.012, .016), (0, .024)], (x + r * .4 * math.cos(a), y + r * .4 * math.sin(a), z + h + .01), SD, 8, 0, grp=grp, uv_cell="sd:strawberry")
    elif kind == "choc":
        for k in range(7):
            a = k * 2 * math.pi / 7
            rbox(acc, (.03, .012, .004), (x + r * .45 * math.cos(a), y + r * .45 * math.sin(a), z + h + .016), C("3A1A10"), .002, 1, rot=(20, 0, math.degrees(a)), grp=grp)
        blob(acc, (.014, .014, .014), (x, y, z + h + .024), C("C0392B"), 1, 0, 1, grp=grp)
    else:
        for k in range(4):
            a = k * math.pi / 2 + .4
            blob(acc, (.01, .01, .01), (x + r * .35 * math.cos(a), y + r * .35 * math.sin(a), z + h + .02), C(GOLD), 1, 0, k, grp=grp)


def sd_cake_stand(acc, loc, kind="straw", r=.1, dome=True):
    x, y, z = loc
    lathe(acc, [(0, 0), (.07, 0), (.02, .03), (.018, .1), (r * 1.25, .11), (r * 1.25, .12), (0, .12)], loc, C(WHITE), 10, 0)
    sd_cake(acc, (x, y, z + .12), r, .08, kind)
    if dome:
        lathe(acc, [(r * 1.2, 0), (r * 1.2, .1), (r * 1.05, .16), (r * .5, .19), (0, .2)], (x, y, z + .122), GLASS, 12, 1, cap_bottom=False)
        lathe(acc, [(0, 0), (.016, 0), (.016, .02), (0, .03)], (x, y, z + .32), C(GOLD), 8, 0)


def sd_sack(acc, loc, s=1.0, yaw=0, open_top=False, seed=0):
    x, y, z = loc
    if open_top:
        prof = [(0, 0), (.15, 0), (.19, .1), (.2, .3), (.19, .42), (.2, .46), (.21, .47)]
    else:
        prof = [(0, 0), (.15, 0), (.19, .1), (.2, .28), (.15, .4), (.06, .47), (.05, .5), (.08, .55)]
    prof = [(r * s, h * s) for r, h in prof]
    bm = lathe_bm(prof, 10, 1, uv_cell="sd:burlap", u_rep=1, cap_top=open_top, cap_bottom=True)
    rnd = random.Random(seed)
    for v in bm.verts:
        v.co.x *= 1 + .06 * math.sin(v.co.z * 30 + seed) ; v.co.y *= .85
    put(acc, bm, SD, loc, (0, 0, yaw))
    if open_top:
        blob(acc, (.18 * s, .15 * s, .04 * s), (x, y, z + .46 * s), C("F6F1E6"), 2, .1, seed)
        X = Xf(acc, (x + .05 * s, y, z + .5 * s), (0, -35, yaw))
        lathe(X, [(0, 0), (.04, 0), (.045, .06), (0, .06)], (0, 0, 0), C(CHROME), 10, 0, rot=(90, 0, 0))
        tube(X, [(0, -.06, .03), (0, -.15, .03)], .008, WOOD_D, 6)
    else:
        lathe(acc, [(.054 * s, 0), (.058 * s, .012 * s), (.054 * s, .024 * s)], (x, y, z + .47 * s), ROPE, 10, 0, cap_top=False, cap_bottom=False)


def sd_peel(acc, loc, rot=(0, 0, 0), L=1.4):
    X = Xf(acc, loc, rot)
    bm = outline_bm([(-.16, 0), (.16, 0), (.18, .06), (.17, .26), (.1, .33), (.03, .36), (-.03, .36), (-.1, .33), (-.17, .26), (-.18, .06)], .012)
    uv_box(bm, 2); place(bm, (0, 0, 0), (90, 0, 0)); X.add(bm, WOOD_L)
    tube(X, [(0, -.006, .35), (0, -.006, L)], .016, WOOD_L, 8)


def sd_rolling_pin(acc, loc, yaw=0):
    X = Xf(acc, loc, (0, 0, yaw))
    lathe(X, [(0, -.16), (.03, -.16), (.032, 0), (.03, .16), (0, .16)], (0, 0, .032), WOOD_L, 12, 0, rot=(0, 90, 0))
    for s in (-1, 1):
        lathe(X, [(0, 0), (.012, 0), (.014, .07), (0, .08)], (s * .16, 0, .032), WOOD_D, 8, 0, rot=(0, s * 90, 0))


def sd_firewood(acc, loc, w=.6, rows=3, yaw=0):
    X = Xf(acc, loc, (0, 0, yaw))
    rnd = random.Random(3)
    for r_ in range(rows):
        n = int(w / .1) - r_
        for k in range(n):
            x = -w / 2 + .06 + k * .1 + r_ * .05
            rr = rnd.uniform(.038, .05)
            lathe(X, [(rr, -.17), (rr * 1.05, 0), (rr, .17)], (x, 0, .05 + r_ * .085), C("6B4A30"), 7, 0, rot=(90, 0, 0), cap_top=False, cap_bottom=False)
            for s in (-1, 1):
                lathe(X, [(0, 0), (rr * .99, 0)], (x, s * .17, .05 + r_ * .085), C("D9B07A"), 7, 0, rot=(90 * s, 0, 0), cap_top=False, cap_bottom=False)


def sd_bread_bag(acc, loc, yaw=0):
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.14, .09, .26), (0, 0, .13), C("C9A06A"), .01, 1)
    rbox(X, (.141, .091, .03), (0, 0, .2), C(NAVY), .004, 1)
    for k in range(2):
        sd_baguette(X, (-.02 + k * .04, 0, .3), .36, .025, 0, -80, k)


# ================================================================================================ butcher products
def sd_steak(acc, loc, s=1.0, yaw=0, cell="steak", seed=0, t=.022, grp="Body"):
    pts = blob_outline(.085 * s, .058 * s, 16, seed, .1)
    bm = outline_bm(pts, t * s)
    planar(bm, cell, rot=0)
    put(acc, bm, SD, loc, (0, 0, yaw), grp)


def sd_tbone(acc, loc, s=1.0, yaw=0, seed=0, grp="Body"):
    sd_steak(acc, loc, s * 1.15, yaw, "tbone", seed, .024, grp)


def sd_ribs(acc, loc, s=1.0, yaw=0, grp="Body"):
    X = Xf(acc, loc, (0, 0, yaw))
    pts = [(-.16 * s + .32 * s * i / 8, 0, .02 * s * math.sin(math.pi * i / 8)) for i in range(9)]
    bm = sweep_bm(pts, lambda t: (.075 * s, .028 * s * (.6 + .4 * math.sin(math.pi * t))), 10, "ribs")
    flat_bottom(bm, -.02 * s)
    X.add(bm, SD, grp)
    for k in range(6):
        lathe(X, [(0, 0), (.009 * s, 0), (.011 * s, .028 * s), (0, .03 * s)], (-.13 * s + k * .052 * s, -.072 * s, .02 * s), C("F1E6CF"), 6, 0, rot=(90, 0, 0), grp=grp)


def sd_sausages(acc, pts, links=6, r=.016, grp="Body"):
    bm = sweep_bm(pts, lambda t: r * (.45 + .55 * abs(math.sin(math.pi * t * links)) ** .3), 8, "sausage")
    acc.add(bm, SD, grp)


def sd_sausage_loop(acc, x, y, z, drop=.45, links=6, r=.016):
    pts = [(x - .03, y, z), (x - .05, y, z - drop * .6), (x - .02, y, z - drop), (x + .02, y, z - drop), (x + .05, y, z - drop * .6), (x + .03, y, z)]
    sd_sausages(acc, rk_core.spline(pts, 4), links, r)
    sd_s_hook(acc, x, y, z + .03)


def sd_s_hook(acc, x, y, z):
    tube(acc, [(x, y, z + .05), (x + .015, y, z + .07), (x + .02, y, z + .05), (x, y, z), (x - .015, y, z - .02), (x - .02, y, z - .035)], .0035, C(CHROME), 5, 2)


def sd_chicken(acc, loc, s=1.0, yaw=0, grp="Body", raw=False):
    X = Xf(acc, loc, (0, 0, yaw))
    key, cell = (C("F2C9A8"), None) if raw else (SD, "chicken")
    bm = blob_bm((.085 * s, .065 * s, .055 * s), 2, .05, 3)
    flat_bottom(bm, -.02 * s)
    if cell:
        planar(bm, cell)
    X.add(bm, key, grp)
    for sy in (-1, 1):
        pts = [(.02 * s, sy * .04 * s, .035 * s), (.09 * s, sy * .055 * s, .045 * s), (.13 * s, sy * .045 * s, .04 * s)]
        b2 = sweep_bm(rk_core.spline(pts, 3), lambda t: .028 * s * (1 - .65 * t), 8, cell)
        X.add(b2, key, grp)
        lathe(X, [(0, 0), (.008 * s, 0), (.009 * s, .012 * s), (0, .014 * s)], (.135 * s, sy * .045 * s, .04 * s), C("F1E6CF"), 6, 0, rot=(0, 90, 0), grp=grp)
        b3 = blob_bm((.035 * s, .015 * s, .018 * s), 1, .1, sy)
        if cell:
            planar(b3, cell)
        place(b3, (-.03 * s, sy * .062 * s, .04 * s), (0, 0, sy * 20)); X.add(b3, key, grp)


def sd_rotisserie(acc, loc, levels=2, w=.7):
    """Frango assado: a glass rotisserie cabinet, spits of golden chickens, warm glow."""
    x, y, z = loc
    X = Xf(acc, loc)
    rbox(X, (w, .5, .22), (0, 0, .11), C(STEEL), .02, 2)
    rbox(X, (w, .5, .08), (0, 0, .16 + .48 * levels + .1), C(NAVY), .02, 2)
    for s in (-1, 1):
        rbox(X, (.05, .5, .48 * levels), (s * (w / 2 - .025), 0, .22 + .24 * levels), C(STEEL), .01, 1)
    rbox(X, (w - .1, .01, .48 * levels), (0, -.245, .22 + .24 * levels), GLASS, .004, 1)
    rbox(X, (w - .1, .02, .48 * levels - .02), (0, .23, .22 + .24 * levels), WARM, .004, 1)
    for lv in range(levels):
        zz = .42 + lv * .48
        tube(X, [(-w / 2 + .05, 0, zz), (w / 2 - .05, 0, zz)], .006, C(CHROME), 6)
        for k in range(3):
            sd_chicken(X, (-w / 3 + k * w / 3, 0, zz - .05), .9, 90 * (k % 2))


def sd_ham(acc, x, y, z, s=1.0):
    """Hanging cured ham in a string net with a hook."""
    prof = [(0, -.42), (.06, -.4), (.11, -.32), (.12, -.2), (.09, -.08), (.04, 0), (.025, .05), (0, .07)]
    prof = [(r * s, h * s) for r, h in prof]
    lathe(acc, prof, (x, y, z - .1), SD, 12, 0, uv_cell="sd:ham", v_range=(-.42 * s, .07 * s))
    for k in range(6):
        a = k * math.pi / 3
        pts = [(x + r * 1.03 * math.cos(a), y + r * 1.03 * math.sin(a) * .9, z - .1 + h) for r, h in prof[1:-1]]
        tube(acc, pts, .0025, ROPE, 3)
    for h in (-.3, -.18, -.06):
        rr = max(r for r, hh in prof if abs(hh - h * s) < .07 * s) * 1.04
        lathe(acc, [(rr, -.003), (rr, .003)], (x, y, z - .1 + h * s), ROPE, 12, 0, cap_top=False, cap_bottom=False)
    sd_s_hook(acc, x, y, z - .05)


def sd_salami(acc, loc, L=.22, r=.03, yaw=0, cut=True, grp="Body"):
    X = Xf(acc, loc, (0, 0, yaw))
    tube(X, [(-L / 2, 0, r), (L / 2, 0, r)], lambda t: r * (.85 + .15 * math.sin(math.pi * t) ** .3), C("8E2F2A"), 10, 0, grp=grp)
    if cut:
        lathe(X, [(0, 0), (r * .98, 0)], (L / 2 + .001, 0, r), SD, 12, 0, rot=(0, 90, 0), grp=grp, uv_cell="sd:salami", cap_top=False, cap_bottom=False)
        b = arc_lathe_bm([(r * .95, 0), (r * .95, .004)], 0, 2 * math.pi, 12, "salami", None, "salami")
        for k in range(4):
            bb = b.copy()
            place(bb, (L / 2 + .03 + k * .028, 0, .004 + k * .002), (0, 25, 0)); X.add(bb, SD, grp)
        b.free()


def sd_ground(acc, loc, w=.2, d=.14, grp="Body"):
    bm = blob_bm((w / 2, d / 2, .035), 2, .25, 4)
    flat_bottom(bm, -.01)
    tiled(bm, "ground", .08)
    put(acc, bm, SD, loc, (0, 0, 0), grp)


def sd_parsley(acc, loc, n=3, seed=0):
    x, y, z = loc
    rnd = random.Random(seed)
    for k in range(n):
        blob(acc, (.016, .016, .01), (x + rnd.uniform(-.02, .02), y + rnd.uniform(-.02, .02), z + .008), C("4E9A3A" if k % 2 else "6DB84A"), 1, .4, k + seed)


def sd_grass_divider(acc, x0, x1, y, z, grp="Body"):
    """The green plastic 'grass' strip butchers put between trays."""
    n = max(2, int((x1 - x0) / .02))
    pts = []
    for i in range(n + 1):
        pts.append((x0 + (x1 - x0) * i / n, y, z + (.025 if i % 2 else .005)))
    bm = bmesh.new()
    top = [bm.verts.new(p) for p in pts]
    bot = [bm.verts.new((p[0], p[1], z - .005)) for p in pts]
    for i in range(n):
        bm.faces.new((bot[i], bot[i + 1], top[i + 1], top[i]))
    uv_box(bm)
    acc.add(bm, C("3FA34D"), grp)


def sd_tray(acc, loc, w=.24, d=.18, yaw=0, col=WHITE):
    X = Xf(acc, loc, (0, 0, yaw))
    open_box(X, w, d, .025, (0, 0, 0), C(col), .006, 0, 1)
    return X


# ================================================================================================ cheese products
def sd_wheel(acc, loc, r=.12, h=.09, rind="rind_wax", cut=0.0, yaw=0, cut_cell="cheese_cut", grp="Body"):
    """Cheese wheel with a bulged rind; cut > 0 removes a wedge of that many degrees (shows the paste)."""
    prof = [(r * .9, 0), (r * .98, h * .15), (r, h * .5), (r * .98, h * .85), (r * .9, h)]
    a0 = math.radians(cut)
    bm = arc_lathe_bm(prof, a0, 2 * math.pi, 12, rind, cut_cell, rind)
    put(acc, bm, SD, loc, (0, 0, yaw), grp)


def sd_wedge(acc, loc, r=.12, h=.08, deg=40, rind="rind_wax", yaw=0, cut_cell="cheese_cut", grp="Body"):
    prof = [(r * .95, 0), (r, h * .5), (r * .95, h)]
    bm = arc_lathe_bm(prof, 0, math.radians(deg), 4, rind, cut_cell, cut_cell)
    put(acc, bm, SD, loc, (0, 0, yaw), grp)


def sd_provolone(acc, x, y, z, s=1.0, hook=True):
    prof = [(0, -.36), (.04, -.35), (.07, -.3), (.08, -.2), (.075, -.12), (.05, -.04), (.03, 0), (0, .01)]
    prof = [(r * s, h * s) for r, h in prof]
    lathe(acc, prof, (x, y, z - .08), SD, 9, 0, uv_cell="sd:provolone", v_range=(-.36 * s, .01 * s))
    for k in range(3):
        a = k * 2 * math.pi / 3 + .4
        pts = [(x + r * 1.04 * math.cos(a), y + r * 1.04 * math.sin(a), z - .08 + h) for r, h in prof[1:-1]]
        tube(acc, pts, .003, ROPE, 3)
    for h in (-.28, -.16):
        rr = max(r for r, hh in prof if abs(hh - h * s) < .06 * s) * 1.05
        lathe(acc, [(rr, -.003), (rr, .003)], (x, y, z - .08 + h * s), ROPE, 9, 0, cap_top=False, cap_bottom=False)
    tube(acc, [(x, y, z - .07), (x, y, z)], .003, ROPE, 3)
    if hook:
        sd_s_hook(acc, x, y, z + .02)


def sd_brie(acc, loc, r=.1, yaw=0):
    sd_wheel(acc, loc, r, .035, "brie", 50, yaw, "blue_cut")


def sd_grapes(acc, loc, s=1.0, col="6A2B5C", seed=0, leaf=True):
    x, y, z = loc
    rnd = random.Random(seed)
    k = 0
    for row, n in enumerate((4, 3, 2, 1)):
        for j in range(n):
            a = j * 2 * math.pi / n + row * .5
            rr = .022 * s * (n - 1) / 3
            blob(acc, (.013 * s, .013 * s, .015 * s), (x + rr * math.cos(a), y + rr * math.sin(a) * .7, z - row * .02 * s), C(col), 1, 0, k)
            k += 1
    tube(acc, [(x, y, z + .01 * s), (x + .01, y, z + .04 * s)], .003, C("6B5A30"), 4)
    if leaf:
        sd_leaf(acc, (x + .03 * s, y, z + .03 * s), .06 * s, (60, 0, 30))


def sd_leaf(acc, loc, L=.08, rot=(0, 0, 0), grp="Body"):
    pts = [(0, 0), (L * .2, L * .3), (L * .26, L * .6), (L * .12, L * .9), (0, L), (-L * .12, L * .9), (-L * .26, L * .6), (-L * .2, L * .3)]
    bm = outline_bm(pts, .002)
    planar(bm, "leaf")
    for v in bm.verts:
        v.co.z += .1 * L * (v.co.x / L) ** 2 * 6
    put(acc, bm, SD, loc, rot, grp)


def sd_honey_jar(acc, loc, s=1.0, col="E8A23A"):
    x, y, z = loc
    lathe(acc, [(0, 0), (.035 * s, 0), (.038 * s, .02), (.038 * s, .08 * s), (.025 * s, .095 * s), (0, .095 * s)], loc, GLASS, 12, 0)
    lathe(acc, [(0, .002), (.034 * s, .002), (.035 * s, .075 * s), (0, .075 * s)], loc, C(col), 12, 0)
    lathe(acc, [(.03 * s, .095 * s), (.03 * s, .115 * s), (0, .118 * s)], loc, C(GOLD), 12, 0)
    lathe(acc, [(.0385 * s, .03), (.0385 * s, .06 * s)], loc, C(CREAM), 12, 0, cap_top=False, cap_bottom=False)


# ================================================================================================ fish products
FISH_TINT = {"fish_blue": "36526F", "fish_red": "B8433E"}


def sd_fish(acc, loc, L=.4, yaw=0, cell="fish_blue", grp="Body", seed=0, lying=True):
    """Whole fish lying on its side: lofted body (back dark -> silver belly, scales), forked tail, dorsal and
    pectoral fins, a glossy eye and a mouth line."""
    X = Xf(acc, loc, (0, 0, yaw))
    n = 9
    body = .82 * L
    pts = [(-L / 2 + body * i / n, 0, 0) for i in range(n + 1)]
    def rad(t):
        prof = math.sin(math.pi * min(1, (t * .92 + .04))) ** .7 * (1 - .55 * t ** 2)
        h = .14 * L * max(.12, prof)
        w = .055 * L * max(.12, prof)
        return (h, w)            # rw = height along the side axis (y), rh = thickness along up (z)
    bm = sweep_bm(pts, rad, 8, cell, True, v_of=lambda a: .5 + .5 * math.cos(a))
    for v in bm.verts:
        v.co.z += .055 * L
    X.add(bm, SD, grp)
    tint = C(FISH_TINT.get(cell, "8FA3AE"))
    tx = -L / 2 + body - .01 * L
    tail = [(tx, 0), (tx + .1 * L, .11 * L), (tx + .2 * L, .14 * L), (tx + .15 * L, .03 * L), (tx + .15 * L, -.03 * L), (tx + .2 * L, -.14 * L), (tx + .1 * L, -.11 * L)]
    tb = outline_bm(tail, .006 * L, .052 * L)
    uv_box(tb); X.add(tb, tint, grp)
    dors = [(-.12 * L, .12 * L), (.04 * L, .17 * L), (.18 * L, .1 * L), (.12 * L, .095 * L), (-.08 * L, .11 * L)]
    db = outline_bm(dors, .004 * L, .053 * L); uv_box(db); X.add(db, tint, grp)
    pec = [(-.24 * L, -.02 * L), (-.12 * L, -.075 * L), (-.15 * L, -.02 * L)]
    pb = outline_bm(pec, .003 * L, .11 * L); uv_box(pb); X.add(pb, tint, grp)
    ex, ey = -L / 2 + .09 * L, .025 * L
    lathe(X, [(0, 0), (.022 * L, 0), (0, .008 * L)], (ex, ey, .1 * L), C(WHITE), 8, 0, grp=grp)
    blob(X, (.013 * L, .013 * L, .008 * L), (ex, ey, .108 * L), C("15181C"), 1, 0, 0, grp=grp)
    rbox(X, (.05 * L, .004, .006), (-L / 2 + .035 * L, -.02 * L, .1 * L), C("3A1A1E"), .002, 1, rot=(0, 0, -20), grp=grp)


def sd_salmon_steak(acc, loc, s=1.0, yaw=0, seed=0):
    pts = blob_outline(.06 * s, .055 * s, 16, seed, .08, pinch=.35)
    bm = outline_bm(pts, .025 * s)
    planar(bm, "salmon")
    put(acc, bm, SD, loc, (0, 0, yaw))


def sd_shrimp(acc, loc, s=1.0, yaw=0, grp="Body"):
    X = Xf(acc, loc, (0, 0, yaw))
    pts = []
    for i in range(8):
        a = math.radians(-30 + i * 250 / 7)
        rr = .028 * s * (1 - .25 * i / 7)
        pts.append((rr * math.cos(a), rr * math.sin(a), .012 * s))
    bm = sweep_bm(pts, lambda t: .013 * s * (1 - .7 * t), 6, "shrimp")
    X.add(bm, SD, grp)
    e = Vector(pts[-1])
    fan = [(e.x, e.y), (e.x + .02 * s, e.y - .012 * s), (e.x + .025 * s, e.y + .004 * s), (e.x + .012 * s, e.y + .014 * s)]
    fb = outline_bm(fan, .002, .008 * s); uv_box(fb); X.add(fb, C("E8644A"), grp)
    st = Vector(pts[0])
    for k in (-1, 1):
        tube(X, [(st.x, st.y, .02 * s), (st.x + .02 * s, st.y - .03 * s, .02 * s), (st.x + .01 * s * k, st.y - .07 * s, .015 * s)], .0012, C("D8553A"), 3, 2)
    blob(X, (.004 * s, .004 * s, .004 * s), (st.x + .006 * s, st.y - .004 * s, .022 * s), C("15181C"), 1, 0, 0, grp=grp)


def sd_lobster(acc, loc, s=1.0, yaw=0, grp="Body"):
    X = Xf(acc, loc, (0, 0, yaw))
    body = [(-.12 * s + .3 * s * i / 10, 0, .03 * s) for i in range(11)]
    def rad(t):
        if t < .4:
            r = .042 * s * math.sin(math.pi * (.15 + t * 1.8)) ** .5
        else:
            r = .03 * s * (1 - (t - .4) * .9) * (1 + .1 * math.cos(t * math.pi * 14))
        return (r, r * .75)
    X.add(sweep_bm(body, rad, 10, "lobster"), SD, grp)
    fan = [(.17 * s, 0), (.21 * s, .035 * s), (.23 * s, .012 * s), (.235 * s, -.012 * s), (.21 * s, -.035 * s)]
    fb = outline_bm(fan, .004 * s, .025 * s); planar(fb, "lobster"); X.add(fb, SD, grp)
    for sy in (-1, 1):
        arm = [(-.1 * s, sy * .025 * s, .035 * s), (-.15 * s, sy * .05 * s, .04 * s), (-.2 * s, sy * .06 * s, .04 * s)]
        X.add(sweep_bm(arm, lambda t: .011 * s, 6, "lobster"), SD, grp)
        cb = blob_bm((.05 * s, .025 * s, .016 * s), 2, .05, sy); planar(cb, "lobster")
        place(cb, (-.25 * s, sy * .068 * s, .04 * s), (0, 0, sy * 12)); X.add(cb, SD, grp)
        for k in range(2):
            pb = blob_bm((.032 * s, .008 * s, .008 * s), 1, 0, k); planar(pb, "lobster")
            place(pb, (-.31 * s, sy * (.06 + k * .018) * s, .04 * s), (0, 0, sy * (20 - k * 30))); X.add(pb, SD, grp)
        tube(X, [(-.12 * s, sy * .012 * s, .045 * s), (-.25 * s, sy * .1 * s, .05 * s), (-.33 * s, sy * .2 * s, .03 * s)], .0018, C("A8301F"), 3, 2)
        for k in range(4):
            x0 = -.06 * s + k * .03 * s
            tube(X, [(x0, sy * .03 * s, .025 * s), (x0 - .01 * s, sy * .07 * s, .02 * s), (x0 - .02 * s, sy * .09 * s, .0)], .003 * s, C("A8301F"), 4)
        blob(X, (.005 * s, .005 * s, .005 * s), (-.115 * s, sy * .015 * s, .055 * s), C("15181C"), 1, 0, 0, grp=grp)


def sd_squid(acc, loc, s=1.0, yaw=0, grp="Body"):
    X = Xf(acc, loc, (0, 0, yaw))
    m = [(.0 + .2 * s * i / 8, 0, .02 * s) for i in range(9)]
    X.add(sweep_bm(m, lambda t: (.032 * s * (1 - .85 * t ** 1.5), .02 * s * (1 - .85 * t ** 1.5)), 10, "squid"), SD, grp)
    fin = [(.12 * s, 0), (.2 * s, .05 * s), (.21 * s, 0), (.2 * s, -.05 * s)]
    fb = outline_bm(fin, .003, .018 * s); planar(fb, "squid"); X.add(fb, SD, grp)
    for k in range(8):
        a = (k - 3.5) * .09
        pts = [(-.0, a * .2 * s, .02 * s), (-.035 * s, a * .4 * s, .015 * s), (-.07 * s, a * .55 * s + .006 * s * math.sin(k), .008 * s), (-.095 * s, a * .65 * s, .005 * s)]
        tube(X, rk_core.spline(pts, 2), lambda t: .007 * s * (1 - .6 * t), C("E8C8D0"), 5, 0, grp=grp)
    for sy in (-1, 1):
        blob(X, (.006 * s, .006 * s, .006 * s), (.01 * s, sy * .022 * s, .03 * s), C("15181C"), 1, 0, 0, grp=grp)


def sd_mussels(acc, loc, w=.26, d=.18, seed=0):
    """A heap of mussels: dark blue-black shells, a few open ones showing orange meat."""
    x, y, z = loc
    rnd = random.Random(seed)
    blob(acc, (w * .45, d * .42, .025), (x, y, z + .01), C("23262E"), 2, .2, seed)
    for k in range(9):
        px_, py = x + rnd.uniform(-w * .38, w * .38), y + rnd.uniform(-d * .35, d * .35)
        yaw = rnd.uniform(0, 360)
        bm = blob_bm((.03, .016, .012), 1, .05, k)
        place(bm, (px_, py, z + .035), (0, 0, yaw)); acc.add(bm, C("2A2F3A" if k % 3 else "3A4058"))
        if k % 3 == 0:
            blob(acc, (.02, .01, .006), (px_, py, z + .048), C("E8834A"), 1, .1, k)


def sd_lemon_half(acc, loc, r=.03, rot=(0, 0, 0), cell="lemon_cut", skin="F4D228", grp="Body"):
    X = Xf(acc, loc, rot)
    lathe(X, [(0, -r), (r * .75, -r * .7), (r, 0)], (0, 0, r * .95), C(skin), 8, 0, grp=grp, cap_top=False)
    b = arc_lathe_bm([(r, 0), (r, .001)], 0, 2 * math.pi, 8, cell, cell, cell)
    place(b, (0, 0, r * .95 - .0005)); X.add(b, SD, grp)


def sd_ice_bed(acc, w, d, loc, tilt=16, seed=0, h=.05):
    """Crushed-ice mound in a steel tray, tilted towards the customer."""
    x, y, z = loc
    X = Xf(acc, (x, y, z), (tilt, 0, 0))
    open_box(X, w, d, .1, (0, 0, 0), BRUSHED, .015, .006, 2)
    nx, ny = max(4, int(w / .09)), max(3, int(d / .09))
    bm = bmesh.new()
    rnd = random.Random(seed)
    V = [[None] * (ny + 1) for _ in range(nx + 1)]
    for i in range(nx + 1):
        for j in range(ny + 1):
            u, v = i / nx, j / ny
            edge = min(u, 1 - u, v, 1 - v)
            hz = .03 + h * min(1, edge * 6) + rnd.uniform(-.008, .008)
            V[i][j] = bm.verts.new((-w / 2 + .012 + u * (w - .024), -d / 2 + .012 + v * (d - .024), hz))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    tiled(bm, "ice", .22, (0, 1))
    X.add(bm, SD)
    return X, .03 + h


# ================================================================================================ gelato
GELATO_DECO = {"gelato_pistachio": ("nut", "8FB24A"), "gelato_choc": ("chunk", "3A1A10"), "gelato_straw": ("berry", None),
               "gelato_cream": ("cookie", "3A2418"), "gelato_mint": ("leaf", None), "gelato_mango": ("slice", "F2B33A"),
               "gelato_berry": ("blue", "3A2A6A")}


def sd_gelato_pan(acc, loc, w=.24, d=.17, flavor="gelato_choc", seed=0, paddle=False):
    x, y, z = loc
    X = Xf(acc, loc)
    open_box(X, w, d, .06, (0, -0, -.055), BRUSHED, .008, 0, 2)
    nx, ny = 6, 4
    bm = bmesh.new()
    V = [[None] * (ny + 1) for _ in range(nx + 1)]
    for i in range(nx + 1):
        for j in range(ny + 1):
            u, v = i / nx * 2 - 1, j / ny * 2 - 1
            r = math.hypot(u, v)
            a = math.atan2(v, u)
            hz = .045 * max(0, 1 - (abs(u) ** 4 + abs(v) ** 4) ** .5 * .8) + .01 * math.sin(r * 9 - a * 2 + seed) * (1 - r * .5)
            V[i][j] = bm.verts.new((u * (w / 2 - .006), v * (d / 2 - .006), hz))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    planar(bm, flavor)
    X.add(bm, SD)
    kind, col = GELATO_DECO.get(flavor, ("", None))
    rnd = random.Random(seed)
    for k in range(3):
        px_, py = rnd.uniform(-w * .3, w * .3), rnd.uniform(-d * .3, d * .3)
        top = .05
        if kind == "nut":
            blob(X, (.009, .007, .006), (px_, py, top), C(col), 1, .2, k)
        elif kind == "chunk":
            rbox(X, (.018, .014, .01), (px_, py, top), C(col), .003, 1, rot=(rnd.uniform(0, 40), 20, k * 40))
        elif kind == "berry":
            lathe(X, [(0, 0), (.012, .003), (.011, .014), (0, .02)], (px_, py, top - .004), SD, 8, 0, uv_cell="sd:strawberry", rot=(70, 0, k * 60))
        elif kind == "cookie":
            lathe(X, [(0, 0), (.016, 0), (.016, .006), (0, .006)], (px_, py, top), C(col), 10, 0, rot=(50, 0, k * 70))
        elif kind == "leaf":
            sd_leaf(X, (px_, py, top), .03, (20, 0, k * 90))
        elif kind == "slice":
            rbox(X, (.03, .014, .006), (px_, py, top), C(col), .003, 1, rot=(10, 0, k * 50))
        elif kind == "blue":
            blob(X, (.006, .006, .006), (px_, py, top), C(col), 1, 0, k)
    if paddle:
        Xp = Xf(X, (w * .28, 0, .04), (0, 30, 0))
        rbox(Xp, (.03, .01, .06), (0, 0, 0), C(CHROME), .003, 1)
        tube(Xp, [(0, 0, .03), (0, 0, .2)], .005, C(CHROME), 6)


def sd_scoop(acc, loc, r=.032, flavor="gelato_straw", seed=0):
    x, y, z = loc
    bm = blob_bm((r, r, r * .9), 2, .1, seed)
    for v in bm.verts:
        if v.co.z < -r * .4:
            v.co.z = -r * .4 + (v.co.z + r * .4) * .2
            v.co.x *= 1.08 + .06 * math.sin(math.atan2(v.co.y, v.co.x) * 9)
            v.co.y *= 1.08 + .06 * math.sin(math.atan2(v.co.y, v.co.x) * 9)
    planar(bm, flavor)
    put(acc, bm, SD, (x, y, z + r * .4))


def sd_cone(acc, loc, flavors=(), h=.12, r=.028):
    x, y, z = loc
    lathe(acc, [(0, 0), (r * .2, .005), (r, h), (r * 1.08, h + .006), (r * .9, h + .008)], loc, SD, 10, 0, uv_cell="sd:waffle", v_range=(0, h), cap_top=True)
    for k, f in enumerate(flavors):
        sd_scoop(acc, (x, y, z + h + k * r * 1.2), r * 1.15, f, k)


def sd_sundae(acc, loc, flavors=("gelato_straw", "gelato_cream")):
    x, y, z = loc
    lathe(acc, [(0, 0), (.04, 0), (.04, .008), (.008, .02), (.008, .06), (.03, .07), (.055, .1), (.06, .12)], loc, GLASS, 12, 2, cap_top=False)
    for k, f in enumerate(flavors):
        sd_scoop(acc, (x + (k - .5) * .03, y, z + .095), .03, f, k)
    lathe(acc, [(0, 0), (.01, 0), (.012, .015), (0, .03)], (x + .01, y, z + .17), C("F6F1E6"), 8, 0)
    blob(acc, (.008, .008, .008), (x + .01, y, z + .2), C("C0392B"), 1, 0, 0)
    rbox(acc, (.012, .05, .006), (x - .03, y, z + .17), SD, .002, 1, rot=(0, 60, 0))


def sd_topping_jar(acc, loc, cell="sprinkles", col=None):
    x, y, z = loc
    lathe(acc, [(0, 0), (.04, 0), (.042, .1), (.035, .11), (0, .11)], loc, GLASS, 12, 0)
    if col:
        lathe(acc, [(0, .003), (.038, .003), (.039, .075), (0, .08)], loc, C(col), 12, 0)
    else:
        lathe(acc, [(0, .003), (.038, .003), (.039, .075), (0, .08)], loc, SD, 12, 0, uv_cell="sd:" + cell)
    lathe(acc, [(.037, .108), (.038, .125), (0, .127)], loc, C(CHROME), 12, 0)


def sd_neon_cone(acc, x, y, z, s=1.0):
    """Wall pictogram in warm 'neon': a cone with two scoops, no words."""
    pts = [(x - .1 * s, y, z), (x, y, z - .28 * s), (x + .1 * s, y, z)]
    tube(acc, pts + [pts[0]], .008, WARM, 6)
    for k, (dx, dz) in enumerate(((-.05, .06), (.05, .06), (0, .14))):
        a = [(x + dx * s + .07 * s * math.cos(t * math.pi / 8), y, z + dz * s + .065 * s * math.sin(t * math.pi / 8)) for t in range(17)]
        tube(acc, a, .008, "E_F4A6C1" if k != 1 else "E_B9E8D2", 6)


# ================================================================================================ wine
def sd_wine_bottle(acc, loc, label="wl_grape", glass="2A3B22", foil="7A1E2E", kind="bordeaux", rot=(0, 0, 0), grp="Body"):
    X = Xf(acc, loc, rot)
    if kind == "burgundy":
        prof = [(0, 0), (.036, 0), (.038, .02), (.038, .16), (.03, .22), (.016, .26), (.014, .31), (.016, .315), (0, .32)]
    elif kind == "sparkling":
        prof = [(0, 0), (.04, 0), (.042, .02), (.042, .16), (.03, .23), (.018, .27), (.016, .31), (.02, .315), (0, .32)]
    else:
        prof = [(0, 0), (.035, 0), (.037, .02), (.037, .2), (.032, .22), (.016, .245), (.014, .31), (.016, .315), (0, .32)]
    lathe(X, prof[1:], (0, 0, 0), C(glass), 8, 0, grp=grp, cap_bottom=False)
    r = prof[3][0]
    lathe(X, [(r * 1.015, .05), (r * 1.015, .15)], (0, 0, 0), SD, 8, 0, grp=grp, uv_cell="sd:" + label, cap_top=False, cap_bottom=False)
    lathe(X, [(.0165, .255 if kind != "sparkling" else .24), (.0175, .3), (0, .322)], (0, 0, 0), C(foil), 8, 0, grp=grp)


def sd_wine_glass(acc, loc, wine="6A1A2A", fill=True):
    lathe(acc, [(0, 0), (.035, 0), (.035, .004), (.004, .01), (.004, .09), (.028, .105), (.04, .15), (.034, .2)], loc, GLASS, 12, 2, cap_top=False)
    if fill and wine:
        lathe(acc, [(0, .1), (.026, .108), (.036, .135), (0, .135)], loc, C(wine), 12, 0)


def sd_decanter(acc, loc):
    lathe(acc, [(0, 0), (.09, 0), (.1, .03), (.07, .08), (.025, .14), (.02, .26), (.026, .27), (0, .27)], loc, GLASS, 16, 2, cap_top=False)
    lathe(acc, [(0, .004), (.088, .004), (.095, .03), (.06, .07), (0, .07)], loc, C("5A1222"), 16, 0)


def sd_cork(acc, loc, rot=(0, 0, 0)):
    lathe(acc, [(0, 0), (.011, 0), (.011, .042), (0, .042)], loc, SD, 8, 0, uv_cell="sd:cork", rot=rot)


def sd_wine_crate(acc, loc, yaw=0, n=6, lying=True):
    X = Xf(acc, loc, (0, 0, yaw))
    open_box(X, .52, .34, .2, (0, 0, 0), WOOD_L, .014, .006, 2)
    rbox(X, (.14, .006, .07), (0, -.173, .11), C(NAVY), .003, 1)
    rbox(X, (.1, .004, .04), (0, -.177, .11), C(CREAM), .003, 1)
    cols = ["2A3B22", "4A1C24", "2A3B22", "3A2A1A", "4A1C24", "2A3B22"]
    for k in range(n):
        if lying:
            sd_wine_bottle(X, (-.21 + (k % 3) * .14, -.12 + (k // 3) * .02, .055 + (k // 3) * .075), ["wl_grape", "wl_leaf", "wl_star"][k % 3], cols[k], ["7A1E2E", GOLD, "1D2B4F"][k % 3], "bordeaux", (-90, 0, 0))
        else:
            sd_wine_bottle(X, (-.17 + (k % 3) * .17, -.08 + (k // 3) * .16, .01), ["wl_grape", "wl_leaf", "wl_star"][k % 3], cols[k], ["7A1E2E", GOLD, "1D2B4F"][k % 3])


def sd_ice_bucket(acc, loc):
    x, y, z = loc
    lathe(acc, [(0, 0), (.08, 0), (.1, .2), (.105, .21), (0, .2)], loc, C(CHROME), 16, 0)
    blob(acc, (.09, .09, .02), (x, y, z + .2), C("E8F4FA"), 2, .3, 1)
    sd_wine_bottle(acc, (x, y + .02, z + .06), "wl_star", "2A3B22", GOLD, "sparkling", (15, 0, 0))
    for s in (-1, 1):
        lathe(acc, [(0, 0), (.012, 0), (.012, .015), (0, .015)], (x + s * .105, y, z + .17), C(GOLD), 8, 0, rot=(0, s * 90, 0))


def sd_vine(acc, x0, x1, y, z, seed=0):
    """A grapevine garland: a twisting brown stem with leaves and a few bunches."""
    rnd = random.Random(seed)
    n = max(3, int((x1 - x0) / .12))
    pts = [(x0 + (x1 - x0) * i / n, y, z + .04 * math.sin(i * 1.7)) for i in range(n + 1)]
    tube(acc, pts, .008, C("6B4A30"), 5, 2)
    for i in range(n + 1):
        p = pts[i]
        sd_leaf(acc, (p[0], p[1] - .01, p[2] - .01), .09, (rnd.uniform(60, 110), 0, rnd.uniform(-40, 40)))
        if i % 5 == 2:
            sd_grapes(acc, (p[0] + .03, p[1] - .03, p[2] - .03), 1.1, "5A1F4E", i, False)


# ================================================================================================ fruit
def sd_orange(acc, loc, r=.038, leaf=False, col="F28C28", seed=0, grp="Body"):
    x, y, z = loc
    bm = blob_bm((r, r, r * .94), 2, .02, seed)
    put(acc, bm, C(col), (x, y, z + r * .94), (0, 0, 0), grp)
    if leaf or seed % 3 == 0:
        rbox(acc, (.008, .008, .004), (x, y, z + r * 1.88), C("6B5A30"), 0, 1, grp=grp)
    if leaf:
        sd_leaf(acc, (x + .004, y, z + r * 1.85), r * 1.3, (70, 0, seed * 40), grp)


def sd_citrus_half(acc, loc, r=.035, kind="orange", rot=(0, 0, 0), grp="Body"):
    skin, cell = {"orange": ("F28C28", "orange_cut"), "lemon": ("F4D228", "lemon_cut"), "lime": ("4E9A3A", "lime_cut"),
                  "kiwi": ("8A6A3E", "kiwi_cut")}[kind]
    sd_lemon_half(acc, loc, r, rot, cell, skin, grp)


def sd_apple(acc, loc, r=.036, seed=0, leaf=True, grp="Body"):
    x, y, z = loc
    prof = [(0, .01), (r * .55, 0), (r * .95, r * .35), (r, r * .9), (r * .8, r * 1.5), (r * .35, r * 1.62), (0, r * 1.5)]
    lathe(acc, prof, loc, SD, 8, 1, grp=grp, uv_cell="sd:apple", v_range=(0, r * 1.6))
    tube(acc, [(x, y, z + r * 1.5), (x + .004, y, z + r * 1.95)], .0025, C("6B4A30"), 4, grp=grp)
    if leaf:
        sd_leaf(acc, (x + .004, y, z + r * 1.85), r * 1.1, (60, 0, 30 + seed * 50), grp)


def sd_pineapple(acc, loc, s=1.0, grp="Body"):
    x, y, z = loc
    prof = [(0, 0), (.05 * s, .005), (.065 * s, .06 * s), (.066 * s, .12 * s), (.055 * s, .17 * s), (.03 * s, .19 * s), (0, .195 * s)]
    lathe(acc, prof, loc, SD, 12, 2, grp=grp, uv_cell="sd:pineapple", u_rep=1, v_range=(0, .19 * s))
    for k in range(11):
        a = k * 2 * math.pi / 11
        tilt = 15 + (k % 3) * 18
        L = (.13 - (k % 3) * .02) * s
        pts = [(x, y, z + .185 * s), (x + L * .5 * math.sin(math.radians(tilt)) * math.cos(a), y + L * .5 * math.sin(math.radians(tilt)) * math.sin(a), z + .185 * s + L * .5),
               (x + L * math.sin(math.radians(tilt * 1.6)) * math.cos(a), y + L * math.sin(math.radians(tilt * 1.6)) * math.sin(a), z + .185 * s + L * .85)]
        tube(acc, pts, lambda t: .009 * s * (1 - t), C("3F7F3A" if k % 2 else "5A9A48"), 4, 1, grp=grp)


def sd_watermelon(acc, loc, s=1.0, rot=(0, 0, 0), grp="Body"):
    prof = [(0, 0), (.08 * s, .01 * s), (.12 * s, .07 * s), (.13 * s, .16 * s), (.12 * s, .25 * s), (.08 * s, .31 * s), (0, .32 * s)]
    X = Xf(acc, loc, rot)
    lathe(X, prof, (0, 0, 0), SD, 14, 2, grp=grp, uv_cell="sd:melon_skin", u_rep=1, v_range=(0, .32 * s))


def sd_melon_wedge(acc, loc, s=1.0, yaw=0, grp="Body"):
    """Watermelon slice standing on its rind: a half-disc extruded, cut faces painted."""
    R, t = .14 * s, .035 * s
    pts = [(R * math.cos(math.pi * i / 10), R * math.sin(math.pi * i / 10)) for i in range(11)]
    bm = outline_bm(pts, t)
    uvl = _uvl(bm)
    for f in bm.faces:
        for l in f.loops:
            co = l.vert.co
            rr = (co.x ** 2 + co.y ** 2) ** .5
            if abs(f.normal.z) > .5:
                l[uvl].uv = cuv("melon_cut", .5 + co.x / (2 * R), 1 - min(1, rr / R) * .95)
            elif f.normal.y < -.5:
                l[uvl].uv = cuv("melon_cut", .2 + .6 * (co.x / (2 * R) + .5), .9)
            else:
                l[uvl].uv = cuv("melon_skin", .5, .5)
    place(bm, (0, t / 2, R), (-90, 0, 0))     # rind down, flat cut edge up
    put(acc, bm, SD, loc, (0, 0, yaw), grp)


def sd_banana_bunch(acc, loc, s=1.0, yaw=0, grp="Body"):
    X = Xf(acc, loc, (0, 0, yaw))
    for k in range(5):
        off = (k - 2) * .024 * s
        pts = [(0, off * .4, .02 * s), (.06 * s, off, .035 * s), (.13 * s, off * 1.3, .03 * s), (.18 * s, off * 1.4, .055 * s)]
        X.add(sweep_bm(rk_core.spline(pts, 3), lambda t: .017 * s * (.35 + .65 * math.sin(math.pi * min(1, t * 1.1)) ** .5), 6, None), C("F2CF3A"), grp)
        blob(X, (.005 * s, .005 * s, .005 * s), (.18 * s, off * 1.4, .055 * s), C("4A3420"), 1, 0, 0, grp=grp)
    lathe(X, [(0, 0), (.012 * s, 0), (.01 * s, .03 * s), (0, .03 * s)], (-.01 * s, 0, .02 * s), C("8FA03A"), 6, 0, rot=(0, -70, 0), grp=grp)


def sd_strawberry(acc, loc, s=1.0, rot=(0, 0, 0), grp="Body"):
    X = Xf(acc, loc, rot)
    lathe(X, [(0, 0), (.008 * s, .004 * s), (.017 * s, .02 * s), (.018 * s, .03 * s), (.012 * s, .036 * s), (0, .036 * s)], (0, 0, 0), SD, 7, 0, grp=grp, uv_cell="sd:strawberry")
    for k in range(3):
        a = k * 2 * math.pi / 3
        rbox(X, (.012 * s, .005 * s, .002), (.008 * s * math.cos(a), .008 * s * math.sin(a), .037 * s), C("3F8A3A"), .001, 1, rot=(0, -15, math.degrees(a)), grp=grp)


def sd_kiwi(acc, loc, s=1.0, grp="Body"):
    blob(acc, (.03 * s, .025 * s, .025 * s), (loc[0], loc[1], loc[2] + .025 * s), C("8A6A3E"), 2, .03, 1, grp=grp)


def sd_fruit_mound(acc, w, d, loc, kind, seed=0, tilt=0, mound=.05, grp="Body"):
    """A crate's worth of one fruit: a low mound in its colour topped with whole, detailed fruits (and a few
    halves showing the cut face)."""
    rnd = random.Random(seed)
    X = Xf(acc, loc, (tilt, 0, 0))
    base = {"orange": "A8561A", "lemon": "A89224", "lime": "2E6A2A", "apple": "7A1E18", "kiwi": "4E3A22", "strawberry": "7A1420"}.get(kind, "8A6A3A")
    blob(X, (w * .46, d * .42, mound * .6), (0, 0, 0), C(base), 2, .05, seed, grp=grp)
    sz = {"orange": .04, "lemon": .034, "lime": .03, "apple": .038, "kiwi": .03, "strawberry": .022}[kind]
    cs = max(sz, .034)                      # small fruit (strawberries) are spaced like limes to keep the count sane
    nx, ny = max(1, int(w / (cs * 2.15))), max(1, int(d / (cs * 2.3)))
    for i in range(nx):
        for j in range(ny):
            px_ = -w / 2 + (i + .5) * w / nx + rnd.uniform(-.004, .004)
            py = -d / 2 + (j + .5) * d / ny + rnd.uniform(-.004, .004)
            h = mound * (1 - (2 * px_ / w) ** 2 * .5 - (2 * py / d) ** 2 * .5) - sz * .4
            k = (i * 7 + j * 3 + seed) % 9
            if kind in ("orange", "lemon", "lime"):
                if k == 0:
                    sd_citrus_half(X, (px_, py, h + sz * .2), sz * .95, kind, (20, 0, k * 40), grp)
                else:
                    sd_orange(X, (px_, py, h), sz, k == 4, {"orange": "F28C28", "lemon": "F2D23A", "lime": "5FA83C"}[kind], k, grp)
            elif kind == "apple":
                sd_apple(X, (px_, py, h), sz, k, k == 4, grp)
            elif kind == "kiwi":
                if k == 0:
                    sd_citrus_half(X, (px_, py, h + sz * .2), sz * .9, "kiwi", (25, 0, 0), grp)
                else:
                    sd_kiwi(X, (px_, py, h), sz / .03, grp)
            elif kind == "strawberry":
                sd_strawberry(X, (px_, py, h + .01), 1.0, (rnd.uniform(60, 100), 0, rnd.uniform(0, 360)), grp)
    return X


def sd_pitcher(acc, loc, liquid="F28C28", h=.24, slices="orange"):
    x, y, z = loc
    lathe(acc, [(0, 0), (.06, 0), (.065, .02), (.062, h * .8), (.055, h), (.06, h + .01)], loc, GLASS, 14, 2, cap_top=False)
    lathe(acc, [(0, .004), (.058, .004), (.06, .02), (.058, h * .68), (0, h * .68)], loc, C(liquid), 14, 0)
    tube(acc, [(x + .06, y, z + h * .85), (x + .1, y, z + h * .8), (x + .1, y, z + h * .3), (x + .062, y, z + h * .2)], .008, GLASS, 6, 2)
    lathe(acc, [(.055, h * .97), (.07, h + .02), (.062, h + .012)], (x - .01, y, z), GLASS, 8, 0, cap_top=False, cap_bottom=False)
    if slices:
        for k in range(2):
            sd_citrus_half(acc, (x - .02 + k * .03, y + .01, z + h * .68 - .02), .025, slices, (75, 0, 30 + k * 90))
        for k in range(3):
            rbox(acc, (.022, .022, .02), (x + .015 - k * .02, y - .02 + k * .015, z + h * .66), GLASS, .004, 1, rot=(10 * k, 20, 15 * k))


def sd_cup(acc, loc, liquid="F28C28", straw="E8505B", garnish="orange", h=.13):
    x, y, z = loc
    lathe(acc, [(0, 0), (.03, 0), (.04, h), (.041, h + .003)], loc, GLASS, 12, 0, cap_top=False)
    lathe(acc, [(0, .004), (.029, .004), (.037, h * .82), (0, h * .82)], loc, C(liquid), 12, 0)
    tube(acc, [(x + .01, y, z + .02), (x + .018, y, z + h + .03), (x + .04, y, z + h + .06)], .0045, C(straw), 6, 1)
    if garnish:
        sd_citrus_half(acc, (x - .038, y, z + h - .028), .022, garnish, (0, -80, 0))


def sd_juicer(acc, loc):
    x, y, z = loc
    lathe(acc, [(0, 0), (.09, 0), (.09, .1), (.07, .12), (0, .12)], loc, C(CHROME), 14, 0)
    lathe(acc, [(0, .12), (.06, .12), (.065, .15), (.03, .19), (0, .2)], loc, C(CHROME), 14, 0)
    tube(acc, [(x + .09, y, z + .08), (x + .14, y, z + .06)], .008, C(CHROME), 6)
    tube(acc, [(x - .02, y + .07, z + .12), (x - .02, y + .07, z + .3), (x + .08, y + .02, z + .33)], .01, C(INK), 6, 2)


# ================================================================================================ set dressing
def sd_chalkboard(acc, loc, cell, w=.55, h=.75, yaw=0, mode="wall"):
    """Slate menu with pictograms (no words). mode: wall | aframe | hang."""
    X = Xf(acc, loc, (0, 0, yaw))
    def board(Xb):
        b = rbox_bm((w, .016, h), 0, 1)
        planar(b, cell, (0, 2))
        Xb.add(b, SD)
        for s in (-1, 1):
            rbox(Xb, (w + .06, .028, .03), (0, 0, s * (h / 2 + .015)), WOOD_D, .006, 1)
            rbox(Xb, (.03, .028, h), (s * (w / 2 + .015), 0, 0), WOOD_D, .006, 1)
    if mode == "aframe":
        for s in (-1, 1):
            Xb = Xf(X, (0, s * .1, h / 2 + .04), (s * -12, 0, 180 if s > 0 else 0))
            board(Xb)
        rbox(X, (w * .9, .2, .012), (0, 0, h * .35), WOOD_D, .004, 1)
    elif mode == "hang":
        Xb = Xf(X, (0, 0, 0))
        board(Xb)
        for s in (-1, 1):
            tube(X, [(s * w * .4, 0, h / 2 + .02), (s * w * .2, 0, h / 2 + .25)], .003, C(INK), 4)
    else:
        Xb = Xf(X, (0, 0, 0))
        board(Xb)


def sd_price_tag(acc, loc, rot=(0, 0, 0), pick=True):
    X = Xf(acc, loc, rot)
    rbox(X, (.06, .006, .04), (0, 0, .02), C(CREAM), 0, 1)
    rbox(X, (.06, .0064, .01), (0, 0, .036), C(NAVY), 0, 1)
    if pick:
        tube(X, [(0, 0, 0), (0, 0, -.06)], .0018, C(CHROME), 3, caps=False)


def sd_knife(acc, loc, rot=(0, 0, 0), L=.2, kind="chef"):
    X = Xf(acc, loc, rot)
    if kind == "cleaver":
        pts = [(0, 0), (.13, 0), (.14, .08), (.0, .08)]
    else:
        pts = [(0, 0), (L * .62, -.004), (L * .7, .006), (L * .62, .028), (0, .03)]
    bm = outline_bm(pts, .002)
    uv_box(bm); place(bm, (0, 0, 0), (90, 0, 0)); X.add(bm, C(CHROME))
    rbox(X, (.1, .016, .022), (-.05, 0, .015 if kind != "cleaver" else .04), C(INK) if kind != "cleaver" else WOOD_D, .007, 2)
    for k in range(2):
        lathe(X, [(0, 0), (.003, 0), (.003, .017), (0, .017)], (-.03 - k * .04, -.0085, .015 if kind != "cleaver" else .04), C(CHROME), 6, 0, rot=(90, 0, 0))


def sd_knife_strip(acc, x, y, z, n=5, w=.6):
    rbox(acc, (w, .025, .05), (x, y, z), C(INK), .008, 2)
    for k in range(n):
        kx = x - w / 2 + .07 + k * (w - .14) / max(1, n - 1)
        sd_knife(acc, (kx, y - .016, z + .02), (0, 90, 0), .18 + .04 * (k % 2), "cleaver" if k == n - 1 else "chef")


def sd_scale(acc, loc, yaw=0):
    """Counter scale: white body, steel platform, a cool-lit display on a short post (no digits)."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.32, .3, .08), (0, 0, .04), C(WHITE), .025, 3)
    rbox(X, (.3, .27, .012), (0, 0, .086), C(CHROME), .008, 2)
    tube(X, [(0, .12, .08), (0, .12, .28)], .015, C(WHITE), 8)
    rbox(X, (.18, .05, .1), (0, .12, .32), C(NAVY), .02, 2, rot=(-15, 0, 0))
    rbox(X, (.13, .006, .05), (0, .093, .325), "E_B9F0D0", .004, 1, rot=(-15, 0, 0))


def sd_slicer(acc, loc, yaw=0):
    """Deli slicer: steel base, round chrome blade with a guard, a carriage tray and a knob."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.5, .36, .1), (0, 0, .05), C(STEEL), .03, 3)
    Xb = Xf(X, (-.02, .03, .27), (75, 0, 0))
    lathe(Xb, [(0, 0), (.15, 0), (.152, .006), (0, .008)], (0, 0, 0), C(CHROME), 22, 0)
    lathe(Xb, [(.12, .008), (.155, .012), (.155, .03), (0, .04)], (0, 0, 0), C(WHITE), 22, 0, cap_bottom=False)
    lathe(Xb, [(0, .04), (.03, .04), (.025, .07), (0, .075)], (0, 0, 0), C(NAVY), 10, 0)
    rbox(X, (.24, .2, .02), (.1, -.06, .14), C(CHROME), .01, 2, rot=(0, -15, 0))
    rbox(X, (.03, .2, .1), (.22, -.06, .19), C(CHROME), .01, 2, rot=(0, -15, 0))
    lathe(X, [(0, 0), (.025, 0), (.025, .04), (0, .05)], (.24, -.17, .12), C(NAVY), 10, 0, rot=(90, 0, 0))


def sd_paper_roll(acc, loc, yaw=0, w=.5, col="C9A06A"):
    X = Xf(acc, loc, (0, 0, yaw))
    for s in (-1, 1):
        rbox(X, (.02, .18, .2), (s * w / 2, 0, .1), C(STEEL), .006, 1)
    rbox(X, (w + .02, .18, .02), (0, 0, .01), C(STEEL), .006, 1)
    lathe(X, [(0, -w / 2 + .02), (.07, -w / 2 + .02), (.07, w / 2 - .02), (0, w / 2 - .02)], (0, 0, .11), C(col), 18, 0, rot=(0, 90, 0))
    rbox(X, (w - .02, .004, .06), (0, -.075, .06), C(col), .002, 1, rot=(-30, 0, 0))
    rbox(X, (w, .02, .01), (0, -.09, .04), C(CHROME), .003, 1)


def sd_apron(acc, loc, col=NAVY, trim=CREAM, yaw=0, L=.62):
    """Bib apron hanging from a hook: shaped panel, neck strap, pocket, ties."""
    X = Xf(acc, loc, (0, 0, yaw))
    pts = [(-.1, 0), (.1, 0), (.11, -.12), (.2, -.2), (.22, -L), (-.22, -L), (-.2, -.2), (-.11, -.12)]
    bm = outline_bm(pts, .006)
    for v in bm.verts:
        v.co.z += .02 * math.sin(v.co.x * 12) + .01
    uv_box(bm); place(bm, (0, 0, 0), (90, 0, 0)); X.add(bm, C(col))
    rbox(X, (.2, .004, .1), (0, -.016, -L * .55), C(trim), .006, 1)
    rbox(X, (.004, .0045, .1), (0, -.0185, -L * .55), C(col), .002, 1)
    tube(X, [(-.09, -.005, -.01), (0, -.005, .1), (.09, -.005, -.01)], .006, C(trim), 5, 2)
    for s in (-1, 1):
        tube(X, [(s * .2, -.01, -.22), (s * .23, -.03, -.35), (s * .22, -.04, -.45)], .005, C(trim), 4, 2)
    sd_s_hook(acc, loc[0], loc[1] + .01, loc[2] + .07)


def sd_peg_rail(acc, x, y, z, w=.8, n=4):
    rbox(acc, (w, .03, .08), (x, y, z), WOOD_D, .01, 2)
    for k in range(n):
        tube(acc, [(x - w / 2 + .1 + k * (w - .2) / max(1, n - 1), y - .015, z), (x - w / 2 + .1 + k * (w - .2) / max(1, n - 1), y - .07, z + .02)], .008, C(GOLD), 6)


def sd_wall_shelf(acc, x, y, z, w=.9, items="jars", seed=0):
    """Wall shelf on gold brackets, filled with jars / bottles / tins in a calm palette."""
    rbox(acc, (w, .2, .03), (x, y - .1, z), WOOD, .008, 2)
    for s in (-1, 1):
        bm = outline_bm([(0, 0), (.16, 0), (0, -.14)], .02)
        uv_box(bm); place(bm, (x + s * (w / 2 - .08) - .01, y, z - .015), (90, 0, -90)); acc.add(bm, C(GOLD))
    rnd = random.Random(seed)
    n = int((w - .1) / .09)
    for k in range(n):
        px_ = x - w / 2 + .08 + k * (w - .16) / max(1, n - 1)
        kind = items if items != "mix" else ["jars", "bottles", "tins"][k % 3]
        if kind == "jars":
            col = rnd.choice(["C0392B", "E8A23A", "6A2B5C", "8FB24A", "F2C23F"])
            lathe(acc, [(.032, 0), (.034, .09), (.026, .1), (0, .1)], (px_, y - .1, z + .015), GLASS, 8, 0, cap_bottom=False)
            lathe(acc, [(.03, .002), (.031, .08), (0, .08)], (px_, y - .1, z + .015), C(col), 8, 0, cap_bottom=False)
            lathe(acc, [(.027, .1), (.028, .118), (0, .12)], (px_, y - .1, z + .015), C(rnd.choice([GOLD, "C0392B", CREAM])), 8, 0)
            lathe(acc, [(.0345, .035), (.0345, .06)], (px_, y - .1, z + .015), C(CREAM), 8, 0, cap_top=False, cap_bottom=False)
        elif kind == "bottles":
            col = rnd.choice(["5A7A2A", "8A9A3A", "2A3B22"])
            lathe(acc, [(0, 0), (.028, 0), (.03, .16), (.012, .2), (.01, .25), (0, .25)], (px_, y - .1, z + .015), C(col), 10, 0)
            lathe(acc, [(.031, .05), (.031, .11)], (px_, y - .1, z + .015), C(CREAM), 10, 0, cap_top=False, cap_bottom=False)
            lathe(acc, [(.011, .24), (.012, .27), (0, .27)], (px_, y - .1, z + .015), C(GOLD), 8, 0)
        else:
            col = rnd.choice(["C0392B", NAVY, "3F7F3A", GOLD])
            lathe(acc, [(0, 0), (.035, 0), (.035, .11), (0, .11)], (px_, y - .1, z + .015), C(col), 12, 0)
            lathe(acc, [(.0355, .03), (.0355, .08)], (px_, y - .1, z + .015), C(CREAM), 12, 0, cap_top=False, cap_bottom=False)
            lathe(acc, [(.036, .105), (.036, .112)], (px_, y - .1, z + .015), C(CHROME), 12, 0, cap_top=False, cap_bottom=False)


def sd_plant(acc, loc, s=1.0, kind="herb", seed=0):
    x, y, z = loc
    lathe(acc, [(0, 0), (.07 * s, 0), (.09 * s, .14 * s), (.1 * s, .15 * s), (.1 * s, .17 * s), (0, .16 * s)], loc, "T_IK_Terracotta", 14, 0)
    rnd = random.Random(seed)
    if kind == "herb":
        for k in range(14):
            a = k * 2.4
            sd_leaf(acc, (x + .02 * s * math.cos(a), y + .02 * s * math.sin(a), z + .15 * s), rnd.uniform(.08, .13) * s, (rnd.uniform(15, 55), 0, math.degrees(a) - 90))
    else:   # small olive tree
        tube(acc, [(x, y, z + .15 * s), (x + .02 * s, y, z + .45 * s), (x, y, z + .7 * s)], .015 * s, C("6B4A30"), 6, 2)
        for k in range(7):
            a = k * 2 * math.pi / 7
            blob(acc, (.12 * s, .12 * s, .09 * s), (x + .1 * s * math.cos(a), y + .1 * s * math.sin(a), z + (.72 + .08 * (k % 2)) * s), C("6E8B3D" if k % 2 else "8FA05A"), 1, .35, k + seed)


def sd_bulb_pendant(acc, x, y, ztop, zlamp, shade=True):
    """Warm pendant: cord, navy enamel shade with a gold rim and a visible glowing bulb."""
    tube(acc, [(x, y, ztop), (x, y, zlamp + .02)], .004, C(INK), 4)
    if shade:
        lathe(acc, [(0, .02), (.02, .02), (.03, -.02), (.11, -.1), (.115, -.11), (0, -.07)], (x, y, zlamp), C(NAVY), 14, 0)
        lathe(acc, [(.112, -.108), (.118, -.114)], (x, y, zlamp), C(GOLD), 14, 0, cap_top=False, cap_bottom=False)
        blob(acc, (.035, .035, .04), (x, y, zlamp - .09), WARM, 2, 0, 0)
    else:
        lathe(acc, [(0, .02), (.016, .02), (.016, -.02), (0, -.02)], (x, y, zlamp), C(GOLD), 8, 0)
        lathe(acc, [(0, -.02), (.012, -.022), (.04, -.07), (.042, -.1), (.03, -.13), (0, -.14)], (x, y, zlamp), WARM, 12, 2)


def sd_wall_lamp(acc, x, y, z):
    tube(acc, [(x, y, z), (x, y - .15, z + .05)], .008, C(GOLD), 6)
    lathe(acc, [(0, 0), (.02, 0), (.07, -.08), (0, -.06)], (x, y - .15, z + .07), C(NAVY), 12, 0)
    blob(acc, (.03, .03, .03), (x, y - .15, z), WARM, 1, 0, 0)


def sd_stool(acc, loc, h=.66):
    x, y, z = loc
    lathe(acc, [(0, h), (.17, h), (.18, h + .03), (.16, h + .07), (0, h + .07)], loc, C(NAVY), 16, 1)
    lathe(acc, [(.181, h + .025), (.183, h + .04)], loc, C(GOLD), 16, 0, cap_top=False, cap_bottom=False)
    for k in range(4):
        a = k * math.pi / 2 + .78
        tube(acc, [(x + .1 * math.cos(a), y + .1 * math.sin(a), h), (x + .16 * math.cos(a), y + .16 * math.sin(a), 0)], .014, WOOD_D, 6)
    lathe(acc, [(.12, h * .35), (.125, h * .35 + .02)], loc, C(GOLD), 16, 0, cap_top=False, cap_bottom=False)


def sd_buoy(acc, loc, rot=(0, 0, 0)):
    X = Xf(acc, loc, rot)
    lathe(X, [(0, 0), (.06, .01), (.075, .06), (.06, .11), (0, .12)], (0, 0, 0), C(CREAM), 14, 1)
    lathe(X, [(.073, .045), (.076, .075)], (0, 0, 0), C(NAVY), 14, 0, cap_top=False, cap_bottom=False)
    tube(X, [(0, 0, .12), (0, 0, .17)], .006, ROPE, 4)


def sd_rope_coil(acc, loc, r=.12, turns=4):
    x, y, z = loc
    pts = [(x + (r - k * .006) * math.cos(t), y + (r - k * .006) * math.sin(t), z + .012 + k * .018) for k in range(turns) for t in [i * math.pi / 8 for i in range(16)]]
    tube(acc, pts, .011, ROPE, 6)


def sd_cutting_board(acc, loc, yaw=0, w=.4, d=.26, items=()):
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (w, d, .025), (0, 0, .0125), "T_IK_ButcherBlock", .008, 2, uv=3)
    return X


def sd_napkins(acc, loc):
    x, y, z = loc
    rbox(acc, (.12, .1, .1), (x, y, z + .05), C(CHROME), .015, 2)
    rbox(acc, (.1, .005, .04), (x, y - .05, z + .1), C(WHITE), .003, 1)


def sd_spoon_cup(acc, loc, n=6):
    x, y, z = loc
    lathe(acc, [(0, 0), (.035, 0), (.038, .1), (0, .1)], loc, C(NAVY), 12, 0)
    for k in range(n):
        a = k * 2 * math.pi / n
        tube(acc, [(x + .01 * math.cos(a), y + .01 * math.sin(a), z + .05), (x + .025 * math.cos(a), y + .025 * math.sin(a), z + .16)], .003, C(["E8505B", "F2C23F", "5FB548", "3E8FD6"][k % 4]), 4)


# ================================================================================================ product test sheet
TEST_Y = 300.0


def sd_test_sheet(render_it=True):
    """All products on a board at y = TEST_Y, for checking silhouettes and textures."""
    sd_material()
    c = coll("SD test", coll("Fixture tiers"))
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    acc = Acc("SD_test")
    rbox(acc, (3.4, 2.2, .02), (0, 0, -.01), C("E9E3D6"), 0, 1)
    row = [lambda X: sd_loaf(X, (0, 0, 0)), lambda X: sd_boule(X, (0, 0, 0)), lambda X: sd_baguette(X, (0, 0, .03), .4),
           lambda X: sd_croissant(X, (0, 0, 0)), lambda X: sd_roll(X, (0, 0, 0)), lambda X: sd_cake_stand(X, (0, 0, 0), "straw"),
           lambda X: sd_cake(X, (0, 0, 0), .1, .085, "choc"), lambda X: sd_sack(X, (0, 0, 0), .6, 0, True)]
    row2 = [lambda X: sd_steak(X, (0, 0, 0)), lambda X: sd_tbone(X, (0, 0, 0)), lambda X: sd_ribs(X, (0, 0, 0), .8),
            lambda X: sd_chicken(X, (0, 0, 0)), lambda X: sd_salami(X, (0, 0, 0), .16), lambda X: sd_ground(X, (0, 0, 0)),
            lambda X: sd_sausages(X, [(-.12, 0, .02), (0, .05, .02), (.12, 0, .02)], 5), lambda X: sd_ham(X, 0, 0, .55)]
    row3 = [lambda X: sd_wheel(X, (0, 0, 0), .12, .09, "rind_wax", 45), lambda X: sd_wedge(X, (0, 0, 0)), lambda X: sd_provolone(X, 0, 0, .45),
            lambda X: sd_brie(X, (0, 0, 0)), lambda X: sd_wheel(X, (0, 0, 0), .13, .1, "parmesan", 30, 0, "parmesan"),
            lambda X: sd_grapes(X, (0, 0, .12)), lambda X: sd_honey_jar(X, (0, 0, 0)), lambda X: sd_wheel(X, (0, 0, 0), .1, .07, "rind_natural", 60, 0, "blue_cut")]
    row4 = [lambda X: sd_fish(X, (0, 0, 0), .36), lambda X: sd_fish(X, (0, 0, 0), .3, 0, "fish_red"), lambda X: sd_shrimp(X, (0, 0, 0), 1.6),
            lambda X: sd_lobster(X, (0, 0, 0), .9), lambda X: sd_squid(X, (0, 0, 0)), lambda X: sd_lemon_half(X, (0, 0, 0)),
            lambda X: sd_salmon_steak(X, (0, 0, 0)), lambda X: sd_ice_bed(X, .3, .2, (0, 0, 0), 0)]
    row5 = [lambda X: sd_gelato_pan(X, (0, 0, .06), .24, .17, "gelato_pistachio", 1, True), lambda X: sd_gelato_pan(X, (0, 0, .06), .24, .17, "gelato_straw", 2),
            lambda X: sd_cone(X, (0, 0, 0), ("gelato_choc", "gelato_mint")), lambda X: sd_sundae(X, (0, 0, 0)),
            lambda X: sd_topping_jar(X, (0, 0, 0)), lambda X: sd_neon_cone(X, 0, 0, .35, .8), lambda X: sd_wine_bottle(X, (0, 0, 0)),
            lambda X: sd_wine_crate(X, (0, 0, 0), 0, 6)]
    row6 = [lambda X: sd_fruit_mound(X, .3, .2, (0, 0, 0), "orange", 1), lambda X: sd_apple(X, (0, 0, 0)), lambda X: sd_pineapple(X, (0, 0, 0)),
            lambda X: sd_melon_wedge(X, (0, 0, 0)), lambda X: sd_banana_bunch(X, (0, 0, 0)), lambda X: sd_pitcher(X, (0, 0, 0)),
            lambda X: sd_cup(X, (0, 0, 0)), lambda X: sd_watermelon(X, (0, 0, 0), .8, (0, 90, 0))]
    row7 = [lambda X: sd_chalkboard(X, (0, 0, 0), "chalk_meat", .4, .55, 0, "aframe"), lambda X: sd_scale(X, (0, 0, 0)),
            lambda X: sd_slicer(X, (0, 0, 0)), lambda X: sd_paper_roll(X, (0, 0, 0), 0, .3), lambda X: sd_apron(X, (0, 0, .7)),
            lambda X: sd_knife_strip(X, 0, 0, .3, 4, .35), lambda X: sd_plant(X, (0, 0, 0), 1, "herb"), lambda X: sd_bulb_pendant(X, 0, 0, .9, .6)]
    for r_, row_ in enumerate((row, row2, row3, row4, row5, row6, row7)):
        for i, fn in enumerate(row_):
            fn(Xf(acc, (-1.4 + i * .4, .9 - r_ * .3, 0)))
    for o in acc.realize(c):
        o.location.y += TEST_Y
    bpy.context.view_layer.update()
    if render_it:
        isolate(TEST_Y, 2)
        camera((0, TEST_Y - .05, 0), (0, -.55, 1), 3.2, 50)
        return render("sd_test_sheet", (2000, 1400))


# ================================================================================================ sector furniture (detailed)
def sd_bread_wall(acc, x, y, w, h, z0=.9, rows=3, seed=0):
    """Paneleira: dark-wood frame, slanted lipped shelves with real loaves, boules, rolls, croissants and a top
    row of upright baguettes; small blank price tags along the lips."""
    rbox(acc, (w, .3, h), (x, y + .05, z0 + h / 2), WOOD_D, .02, 2)
    rbox(acc, (w + .04, .34, .05), (x, y + .05, z0 + h + .02), WOOD_D, .015, 2)
    rbox(acc, (w + .05, .01, .012), (x, y - .121, z0 + h + .02), C(GOLD), .003, 1)
    for r_ in range(rows):
        z = z0 + .08 + r_ * h / rows
        X = Xf(acc, (x, y - .08, z), (14, 0, 0))
        rbox(X, (w - .08, .26, .02), (0, 0, 0), WOOD, .006, 1)
        rbox(X, (w - .08, .02, .06), (0, -.13, .03), WOOD, .006, 1)
        n = max(1, int((w - .1) / .24))
        for i in range(n):
            px_ = -w / 2 + .14 + i * (w - .28) / max(1, n - 1) if n > 1 else 0
            if r_ == rows - 1:
                for k in range(2):
                    sd_baguette(X, (px_ - .03 + k * .06, .05, .22), .44, .028, 90 + k * 8, -78, seed + i + k)
            elif r_ % 2:
                if i % 2:
                    sd_boule(X, (px_, -.01, .012), .075, i + seed)
                else:
                    sd_loaf(X, (px_, -.01, .012), .22, .11, .085, 90, "loaf", i + seed)
            else:
                if i % 2:
                    for k in range(2):
                        sd_croissant(X, (px_ - .03 + k * .07, -.03 + k * .06, .012), .9, 20 * k + 70)
                else:
                    for k in range(3):
                        sd_roll(X, (px_ - .05 + k * .05, -.04 + (k % 2) * .06, .012), .036, i + k + seed)
            if i % 2 == 0:
                sd_price_tag(X, (px_, -.142, .07), (0, 0, 0), False)


def sd_bakery_case(acc, W, y, H=.9):
    """Curved glass pastry case: navy body with light-wood slats, cakes on stands, croissants, pastries on trays."""
    rbox(acc, (W, .7, H - .05), (0, y, (H - .05) / 2), C(NAVY), .03, 3)
    n = int(W / .06)
    for k in range(n):
        rbox(acc, (.034, .016, H - .3), (-W / 2 + .05 + k * (W - .1) / (n - 1), y - .356, H / 2), WOOD_L, 0, 1)
    rbox(acc, (W - .1, .01, .01), (0, y - .362, H - .12), C(GOLD), .003, 1)
    rbox(acc, (W + .02, .74, .04), (0, y, H), MARBLE, .01, 2)
    bm = bmesh.new()
    prof = [(0, 0), (.06, .12), (.1, .26), (.11, .4), (.09, .46)]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        bm.faces.new([bm.verts.new((-W / 2 + .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -b[0], b[1])), bm.verts.new((-W / 2 + .03, -b[0], b[1]))])
    uv_box(bm); place(bm, (0, y - .25, H + .02)); acc.add(bm, GLASS)
    rbox(acc, (W - .06, .45, .012), (0, y + .02, H + .47), GLASS, .004, 1)
    rbox(acc, (W - .1, .02, .012), (0, y + .2, H + .45), LED, .004, 1)
    for s in (-1, 1):
        rbox(acc, (.03, .6, .46), (s * (W / 2 - .02), y, H + .23), C(NAVY), .01, 1)
    rbox(acc, (W - .1, .5, .012), (0, y + .02, H + .24), GLASS, .003, 1)
    x = -W / 2 + .16
    k = 0
    while x < W / 2 - .14:
        kind = ["straw", "choc", "cream"][k % 3]
        sd_cake_stand(acc, (x, y - .02, H + .02), kind, .07, False)
        X = sd_tray(acc, (x + .11, y - .05, H + .25), .18, .3, 0, WHITE)
        for j in range(2):
            sd_croissant(X, (0, -.08 + j * .14, .006), .8, 80 + 20 * j)
        x += .32
        k += 1


def sd_bread_counter(acc, W, y, D=.7, x0=0.0, baskets=3, seed=0):
    """Wooden bread counter: planked front with a gold line, tilted wicker baskets of rolls, boules and baguettes,
    a paper-bag stack and a scale."""
    X0 = Xf(acc, (x0, 0, 0))
    wood_counter(X0, W, y, D, PLANKS, WOOD_L)
    for i in range(baskets):
        bx = -W / 2 + (i + .5) * W / baskets
        B = basket(X0, min(.5, W / baskets - .06), .34, .1, (bx, y - .05, .9), 10)
        kind = (i + seed) % 3
        for k in range(4):
            if kind == 0:
                sd_roll(B, (-.15 + k * .1, 0, .02), .04, k + i)
            elif kind == 1:
                sd_boule(B, (-.14 + k * .095, 0, .015), .045, k + i)
            else:
                sd_baguette(B, (0, -.12 + k * .08, .04), min(.44, W / baskets - .1), .026, 0, 0, k)
        sd_price_tag(X0, (bx, y - D / 2 - .01, .9), (0, 0, 0), False)


def sd_oven_tools(acc, x, y):
    sd_peel(acc, (x, y, .05), (-8, 0, 0), 1.5)
    sd_peel(acc, (x + .22, y + .02, .05), (-6, 0, 10), 1.35)


# ------------------------------------------------------------------------------------------------ PADARIA
def sd_dome_oven(acc, x, y, r, z0=0):
    """Wood-fired dome oven with brick courses that follow the dome (no bull's-eye), a stone hearth, a glowing
    arched mouth with a gold rim, embers, an iron door leaning beside it, and a chimney."""
    rbox(acc, (r * 2.3, r * 2.0, .75), (x, y, z0 + .375), BRICK, .03, 2, uv=2)
    rbox(acc, (r * 2.4, r * 2.1, .05), (x, y, z0 + .77), STONE, .015, 2, uv=2)
    prof = [(r, 0), (r * 1.02, r * .25), (r * .93, r * .55), (r * .72, r * .8), (r * .42, r * .95), (r * .12, r * 1.0), (0, r * 1.01)]
    dome = lathe_bm(prof, 20, 1, cap_top=True, cap_bottom=False)
    uvl = dome.loops.layers.uv.get("UVMap")
    for f in dome.faces:
        for l in f.loops:
            co = l.vert.co
            ang = math.atan2(co.y, co.x)
            arc = math.atan2(co.z, max(1e-4, (co.x ** 2 + co.y ** 2) ** .5))
            l[uvl].uv = (ang * r * 2.4, arc * r * 2.4)
    place(dome, (x, y, z0 + .79)); acc.add(dome, BRICK)
    mw, mh = r * .9, r * .55
    plate(acc, mw + .1, mh + .1, (x, y - r * .92, z0 + .79 + mh / 2), STONE, .1, mh * .5)
    plate(acc, mw, mh, (x, y - r * .97, z0 + .79 + mh / 2), "E_FF8A2A", .02, mh * .48)
    for k in range(3):
        lathe(acc, [(.035, -.12), (.04, 0), (.035, .12)], (x - .12 + k * .12, y - r * .8, z0 + .82), C("3A2418"), 6, 0, rot=(0, 90, 10 * k), cap_top=False, cap_bottom=False)
        blob(acc, (.05, .04, .02), (x - .12 + k * .12, y - r * .8, z0 + .8), "E_FF7A20", 1, .2, k)
    fr = frame_bm(mw + .04, mh + .04, .02, mh * .48, .025)
    place(fr, (x, y - r * .99, z0 + .79 + mh / 2)); acc.add(fr, C(GOLD))
    rbox(acc, (.18, .18, .6), (x + r * .3, y + r * .3, z0 + .79 + r + .2), BRICK, .03, 2, uv=2)
    rbox(acc, (.22, .22, .05), (x + r * .3, y + r * .3, z0 + .79 + r + .52), C(INK), .015, 2)
    plate(acc, mw * .9, mh * .9, (x + r * .95, y - r * .85, z0 + .79 + mh / 2), C(INK), .02, mh * .45, (0, -8, 25))
    lathe(acc, [(0, 0), (.02, 0), (.02, .02), (0, .03)], (x + r * .95, y - r * .9, z0 + .79 + mh * .55), C(GOLD), 8, 0, rot=(90, 0, 25))


def padaria_v3(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, BRICK, "T_IK_WoodLight" if tier > 1 else None, .9, uv=1.6)
    if tier == 1:
        sd_dome_oven(acc, -W / 2 + .7, yb - .55, .48)
        sd_firewood(acc, (-W / 2 + .7, yb - .55, .02), .5, 2, 0)
        sd_bread_wall(acc, .55, yb - .2, 1.1, 1.0, .25, 3, 1)
        sd_bread_counter(acc, W - .3, -D / 2 + .45, .7, 0, 3, 0)
        sd_sack(acc, (W / 2 - .22, yb - .62, 0), .85, 20)
        sd_sack(acc, (W / 2 - .3, yb - .98, 0), .8, -10, True, 2)
        sd_oven_tools(acc, -W / 2 + .2, yb - .95)
        sd_chalkboard(acc, (-.3, -D / 2 - .1, 0), "chalk_bread", .36, .5, 0, "aframe")
        sd_bread_bag(acc, (W / 2 - .45, -D / 2 + .55, .9), 20)
        sd_scale(acc, (-W / 2 + .4, -D / 2 + .5, .9), 0)
        name_board(acc, 0, yb - .08, H - .2)
        for x in (-.6, .6):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .3, 1.85, False)
    elif tier == 2:
        sd_dome_oven(acc, 0, yb - .7, .62)
        sd_firewood(acc, (0, yb - .7, .02), .7, 3, 0)
        sd_bread_wall(acc, -W / 2 + .62, yb - .2, 1.0, 1.4, .9, 3, 2)
        sd_bread_wall(acc, W / 2 - .62, yb - .2, 1.0, 1.4, .9, 3, 5)
        sd_bread_counter(acc, W * .55, -D / 2 + .45, .7, -W * .2, 3, 1)
        Xc = Xf(acc, (W * .3, 0, 0))
        sd_bakery_case(Xc, W * .36, -D / 2 + .45)
        for k in range(3):
            sd_sack(acc, (-W / 2 + .25 + (k % 2) * .34, -D / 2 + 1.15 + k * .05, 0), .85, 30 * k, k == 2, k)
        sd_oven_tools(acc, .75, yb - .55)
        sd_wall_shelf(acc, 0, yb - .06, 1.75, .9, "jars", 3)
        sd_chalkboard(acc, (W / 2 - .1, -D / 2 + 1.1, 1.35), "chalk_bread", .45, .6, -90, "wall")
        sd_plant(acc, (-W / 2 + .2, -D / 2 + .2, 0), 1.0, "olive", 1)
        sd_scale(acc, (-W * .2 - .55, -D / 2 + .5, .9), 0)
        name_board(acc, 0, yb - .08, H - .15, 1.3)
        for x in (-1.0, 0, 1.0):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .3, 1.95)
    else:
        sd_dome_oven(acc, 0, yb - .8, .72)
        arch = frame_bm(2.0, 2.4, .2, .6, .18)
        place(arch, (0, yb - .14, 1.2)); acc.add(arch, BRICK)
        sd_firewood(acc, (0, yb - .8, .02), .8, 3, 0)
        sd_bread_wall(acc, -W / 2 + .75, yb - .2, 1.3, 1.6, .9, 3, 3)
        sd_bread_wall(acc, W / 2 - .75, yb - .2, 1.3, 1.6, .9, 3, 7)
        Xc = Xf(acc, (-.55, 0, 0))
        sd_bakery_case(Xc, 2.0, -D / 2 + .5)
        sd_bread_counter(acc, 1.1, -D / 2 + .5, .7, 1.25, 2, 2)
        for side in (-1, 1):                          # bakers' racks of trays
            rx = side * (W / 2 - .45)
            for z in (.3, .75, 1.2):
                Xt = sd_tray(acc, (rx, -D / 2 + 1.3, z), .5, .4, 0, STEEL)
                for k in range(3):
                    if z < .7:
                        sd_roll(Xt, (-.15 + k * .15, 0, .006), .04, k)
                    else:
                        sd_croissant(Xt, (-.15 + k * .15, 0, .006), .85, 90)
            for sx in (-1, 1):
                for sy in (1.12, 1.48):
                    tube(acc, [(rx + sx * .26, -D / 2 + sy, .05), (rx + sx * .26, -D / 2 + sy, 1.35)], .012, C(CHROME), 6)
                    lathe(acc, [(0, 0), (.025, 0), (.025, .03), (0, .03)], (rx + sx * .26, -D / 2 + sy, .02), C(INK), 8, 0, rot=(90, 0, 0))
        for k, (x, z) in enumerate(((-.35, 0), (0, 0), (.35, 0), (-.17, .4), (.17, .4))):
            sd_sack(acc, (x - W / 2 + 1.05, -D / 2 + 1.0 + (k % 2) * .05, z), .8, 15 * k, k == 4, k)
        sd_oven_tools(acc, .9, yb - .6)
        sd_wall_shelf(acc, -.0, yb - .3, 2.0, .9, "jars", 4)
        sd_chalkboard(acc, (-1.2, -D / 2 - .12, 0), "chalk_bread", .42, .58, 0, "aframe")
        sd_chalkboard(acc, (1.25, yb - .1, 1.95), "chalk_bread", .55, .42, 0, "wall")
        sd_plant(acc, (W / 2 - .2, -D / 2 + .2, 0), 1.1, "olive", 2)
        sd_scale(acc, (1.0, -D / 2 + .55, .9), 0)
        name_board(acc, 0, yb - .1, H - .1, 1.6, .4)
        for x in (-1.4, -.45, .45, 1.4):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .4, 2.0)


# ------------------------------------------------------------------------------------------------ AÇOUGUE
def sd_meat_case(acc, W, y, H=.9, D=.75, seed=0, chicken=True):
    """Serve-over meat case: navy/steel body, straight glass, white trays of steaks, T-bones, ribs, chops, ground
    beef, sausages and chicken, green grass dividers, parsley and blank price picks."""
    rbox(acc, (W, D, H - .05), (0, y, (H - .05) / 2), C(NAVY), .03, 3)
    rbox(acc, (W - .1, .01, .3), (0, y - D / 2 - .004, .45), BRUSHED, .01, 1)
    rbox(acc, (W - .12, .01, .01), (0, y - D / 2 - .01, .63), C(GOLD), .003, 1)
    rbox(acc, (W + .02, D + .02, .04), (0, y, H), BRUSHED, .01, 2)
    rbox(acc, (W - .06, .012, .42), (0, y - D / 2 + .08, H + .21), GLASS, .004, 1, rot=(-18, 0, 0))
    rbox(acc, (W - .06, .4, .012), (0, y + .05, H + .42), GLASS, .004, 1)
    for s in (-1, 1):
        rbox(acc, (.03, D - .1, .44), (s * (W / 2 - .02), y, H + .22), BRUSHED, .01, 1)
    rbox(acc, (W - .1, .02, .012), (0, y + .22, H + .4), "E_FFF0E8", .004, 1)
    X = Xf(acc, (0, y, H + .02), (12, 0, 0))
    rbox(X, (W - .1, .52, .02), (0, 0, 0), C(WHITE), .005, 1)
    x = -W / 2 + .16
    k = seed
    kinds = ["steak", "tbone", "ribs", "ground", "chop", "sausage", "chicken" if chicken else "steak"]
    while x < W / 2 - .16:
        kind = kinds[k % len(kinds)]
        T = sd_tray(X, (x, 0, .012), .22, .44, 0, WHITE)
        if kind in ("steak", "tbone", "chop"):
            for j in range(3):
                (sd_tbone if kind == "tbone" else sd_steak)(T, (0, -.14 + j * .14, .006 + j * .002), .78, -8 + j * 8, *(() if kind == "tbone" else ("chop" if kind == "chop" else "steak",)), j + k)
        elif kind == "ribs":
            sd_ribs(T, (0, -.07, .006), .6, 90)
            sd_ribs(T, (0, .1, .006), .6, 90)
        elif kind == "ground":
            sd_ground(T, (0, 0, .006), .18, .38)
        elif kind == "sausage":
            for j in range(3):
                sd_sausages(T, rk_core.spline([(-.09, -.13 + j * .12, .02), (-.03, -.11 + j * .12, .022), (.03, -.12 + j * .12, .022), (.09, -.1 + j * .12, .02)], 2), 4, .016)
        else:
            for j in range(2):
                sd_chicken(T, (0, -.1 + j * .2, .006), .65, 90, "Body", True)
        sd_parsley(T, (.07, .17, .01), 2, k)
        sd_price_tag(T, (0, -.2, .06), (0, 0, 0))
        sd_grass_divider(X, x + .115, x + .125, 0, .02)
        tube(X, [(x + .12, -.24, .025), (x + .12, .24, .025)], .008, C("3FA34D"), 4)
        x += .24
        k += 1


def sd_butcher_block(acc, x, y, w=.7, d=.55):
    rbox(acc, (w, d, .25), (x, y, .72), "T_IK_ButcherBlock", .03, 2, uv=3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rbox(acc, (.07, .07, .62), (x + sx * (w / 2 - .06), y + sy * (d / 2 - .06), .31), WOOD_D, .015, 2)
    rbox(acc, (w - .1, d - .1, .03), (x, y, .2), WOOD_D, .01, 1)
    sd_knife(acc, (x + .12, y - .05, .855), (0, 0, 20), .22, "cleaver")
    sd_steak(acc, (x - .12, y, .85), 1.2, 30, "steak", 3)
    sd_tbone(acc, (x - .05, y + .12, .85), 1.0, 70, 4)
    sd_parsley(acc, (x + .2, y + .15, .85), 2, 1)


def acougue_v3(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, TILE_W, C(NAVY) if tier > 1 else None, 1.0, uv=1.5)
    n = {1: 4, 2: 7, 3: 10}[tier]
    rw = W - .6
    tube(acc, [(-rw / 2, yb - .3, H - .35), (rw / 2, yb - .3, H - .35)], .018, C(CHROME), 8)
    for sx in (-1, 1):
        tube(acc, [(sx * rw / 2, yb - .3, H - .35), (sx * rw / 2, yb - .08, H - .35)], .012, C(CHROME), 6)
    for i in range(n):
        x = -rw / 2 + .15 + i * (rw - .3) / max(1, n - 1)
        if i % 3 == 1:
            sd_sausage_loop(acc, x, yb - .3, H - .39, .5, 7, .016)
        else:
            sd_ham(acc, x, yb - .3, H - .37, 1.0 if tier < 3 else 1.12)
    if tier == 1:
        sd_butcher_block(acc, -W / 2 + .55, yb - .75)
        sd_meat_case(acc, W - .5, -D / 2 + .42, .9, .7, 0, False)
        sd_scale(acc, (W / 2 - .4, yb - .4, .9), 180)
        rbox(acc, (.4, .35, .9), (W / 2 - .4, yb - .4, .45), C(NAVY), .03, 2)
        sd_knife_strip(acc, .45, yb - .075, 1.45, 4, .5)
        sd_apron(acc, (-W / 2 + .3, yb - .08, 1.6), CREAM, NAVY)
        sd_chalkboard(acc, (W / 2 - .2, -D / 2 - .1, 0), "chalk_meat", .34, .48, 0, "aframe")
        name_board(acc, 0, yb - .08, H - .15, 1.0)
        for x in (-.6, .6):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .3, 1.95)
    elif tier == 2:
        sd_butcher_block(acc, -W / 2 + .6, yb - .8)
        sd_butcher_block(acc, .1, yb - .8)
        sd_meat_case(acc, W - .4, -D / 2 + .42, .9, .75, 1)
        sd_slicer(acc, (W / 2 - .45, yb - .5, .9), 180)
        rbox(acc, (.6, .5, .9), (W / 2 - .45, yb - .5, .45), C(STEEL), .03, 2)
        sd_knife_strip(acc, W / 2 - .7, yb - .075, 1.5, 5, .7)
        sd_paper_roll(acc, (-.8, yb - .12, 1.25), 0, .5)
        sd_peg_rail(acc, -W / 2 + .45, yb - .075, 1.75, .6, 2)
        sd_apron(acc, (-W / 2 + .3, yb - .12, 1.68), NAVY, CREAM)
        sd_apron(acc, (-W / 2 + .6, yb - .12, 1.68), CREAM, NAVY)
        sd_chalkboard(acc, (.95, yb - .075, 1.65), "chalk_meat", .5, .4, 0, "wall")
        sd_scale(acc, (-W / 2 + .5, -D / 2 + .45, .92), 0)
        name_board(acc, 0, yb - .08, H - .15, 1.2)
        for x in (-1.0, 0, 1.0):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .3, 1.95)
    else:
        cx = W / 2 - .55
        rbox(acc, (.9, .7, 2.2), (cx, yb - .42, 1.1), C(NAVY), .04, 3)
        rbox(acc, (.74, .02, 1.8), (cx, yb - .78, 1.15), GLASS, .01, 1)
        rbox(acc, (.7, .02, 1.75), (cx, yb - .1, 1.15), "E_FFE0D0", .01, 1)
        for k in range(2):
            lathe(acc, [(0, 0), (.08, -.1), (.13, -.45), (.12, -.9), (.07, -1.2), (0, -1.25)], (cx - .15 + k * .3, yb - .5, 1.95), SD, 14, 1, uv_cell="sd:ribs", v_range=(-1.25, 0))
            sd_s_hook(acc, cx - .15 + k * .3, yb - .5, 1.97)
        for z in (.35, .6):
            rbox(acc, (.68, .45, .015), (cx, yb - .45, z), C(CHROME), .004, 1)
            for j in range(3):
                sd_tbone(acc, (cx - .2 + j * .2, yb - .45, z + .01), .9, 90, j)
        rbox(acc, (.9, .01, .012), (cx, yb - .78, 2.1), C(GOLD), .003, 1)
        sd_butcher_block(acc, -W / 2 + .7, yb - .85, .9, .6)
        Xc = Xf(acc, (-.35, 0, 0))
        sd_meat_case(Xc, W - 1.1, -D / 2 + .45, .9, .75, 2)
        sd_rotisserie(acc, (W / 2 - .5, -D / 2 + .5, .0), 2, .7)
        tile_arch = frame_bm(2.2, 2.3, .14, .7, .12)
        place(tile_arch, (-.45, yb - .1, 1.15)); acc.add(tile_arch, C(NAVY))
        sd_knife_strip(acc, -.45, yb - .08, 1.55, 6, .9)
        sd_slicer(acc, (.5, yb - .5, .9), 180)
        rbox(acc, (.6, .5, .9), (.5, yb - .5, .45), C(STEEL), .03, 2)
        sd_paper_roll(acc, (-1.5, yb - .12, 1.35), 0, .5)
        sd_peg_rail(acc, -1.4, yb - .075, 1.85, .7, 3)
        for k in range(2):
            sd_apron(acc, (-1.6 + k * .3, yb - .12, 1.78), [NAVY, CREAM][k], [CREAM, NAVY][k])
        sd_chalkboard(acc, (-1.6, -D / 2 - .12, 0), "chalk_meat", .42, .58, 0, "aframe")
        sd_plant(acc, (-W / 2 + .2, -D / 2 + 1.4, 0), 1.0, "herb", 3)
        name_board(acc, -.45, yb - .2, H - .1, 1.4, .36)
        for x in (-1.5, -.45, .6, 1.5):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .4, 2.0)


# ------------------------------------------------------------------------------------------------ QUEIJARIA
def sd_wheel_rack(acc, x, y, w, h, levels=4, d=.42, seed=0):
    """Dark-wood cheese rack with slatted shelves of wheels (some cut), wedges and blank tags."""
    for sx in (-1, 1):
        rbox(acc, (.06, d, h), (x + sx * (w / 2 - .03), y, h / 2), WOOD_D, .015, 2)
    rbox(acc, (w, .03, h), (x, y + d / 2 - .015, h / 2), WOOD_D, .01, 1)
    rbox(acc, (w + .04, d + .04, .05), (x, y, h + .02), WOOD_D, .015, 2)
    rinds = ["rind_wax", "rind_natural", "parmesan", "rind_wax", "brie"]
    rnd = random.Random(seed)
    for i in range(levels):
        z = .15 + i * (h - .2) / levels
        for k in range(4):
            rbox(acc, (w - .1, .08, .02), (x, y - d / 2 + .06 + k * .1, z), WOOD, .006, 1)
        n = max(1, int((w - .14) / .27))
        for j in range(n):
            rr = .11 if (i + j) % 3 else .125
            rind = rinds[(i * 2 + j + seed) % len(rinds)]
            hh = .035 if rind == "brie" else .085 + .02 * ((i + j) % 2)
            cut = 40 if (i + j + seed) % 4 == 0 else 0
            sd_wheel(acc, (x - w / 2 + .17 + j * .27, y, z + .012), rr, hh, rind, cut, rnd.uniform(0, 360) if not cut else -90 - 20, "parmesan" if rind == "parmesan" else "blue_cut" if rind == "brie" else "cheese_cut")
        sd_price_tag(acc, (x, y - d / 2 - .005, z - .025), (0, 0, 0), False)


def sd_cheese_board(acc, loc, yaw=0):
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.42, .26, .025), (0, 0, .0125), WOOD, .008, 2)
    sd_wedge(X, (-.1, .02, .025), .12, .07, 40, "rind_wax", -100)
    sd_wedge(X, (.0, -.05, .025), .1, .06, 50, "rind_natural", 160, "blue_cut")
    sd_grapes(X, (.12, .04, .09), .9, "6A2B5C", 2, False)
    sd_knife(X, (.05, .09, .03), (0, 0, -10), .14)


def queijaria_v3(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, PLASTER, WOOD_D, .9, uv=1.5)
    if tier == 1:
        sd_wheel_rack(acc, -W / 2 + .7, yb - .3, 1.2, 1.9, 4, .42, 0)
        wood_counter(acc, W - .4, -D / 2 + .45, .7, WOOD_D, WOOD)
        sd_wheel(acc, (-.65, -D / 2 + .45, .9), .13, .1, "rind_wax", 45, -110)
        sd_wheel(acc, (-.3, -D / 2 + .42, .9), .12, .09, "rind_natural", 0)
        sd_cheese_board(acc, (.15, -D / 2 + .45, .9), 0)
        cloche(acc, .62, -D / 2 + .45, .9)
        beam_y = yb - .7
        for sx in (-1, 1):
            rbox(acc, (.08, .08, 2.1), (W / 2 - .2 + (sx - 1) * .45, beam_y, 1.05), WOOD_D, .02, 2)
        rbox(acc, (1.0, .08, .08), (W / 2 - .65, beam_y, 2.1), WOOD_D, .02, 2)
        for k in range(4):
            sd_provolone(acc, W / 2 - 1.0 + k * .22, beam_y, 2.04, 1.0 - .1 * (k % 2))
        sd_honey_jar(acc, (.95, -D / 2 + .55, .9))
        sd_chalkboard(acc, (W / 2 - .3, -D / 2 - .1, 0), "chalk_cheese", .34, .48, 0, "aframe")
        name_board(acc, .35, yb - .08, H - .15, .9)
        for x in (-.6, .6):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .3, 1.85, False)
    elif tier == 2:
        arch = frame_bm(W - .4, H - .1, .14, .8, .16)
        place(arch, (0, yb - .1, (H - .1) / 2)); acc.add(arch, STONE)
        sd_wheel_rack(acc, -.7, yb - .35, 1.3, 2.1, 5, .42, 1)
        sd_wheel_rack(acc, .7, yb - .35, 1.3, 2.1, 5, .42, 2)
        rbox(acc, (W - .5, .7, .85), (0, -D / 2 + .45, .425), WOOD_D, .03, 2)
        for k in range(3):
            fr = frame_bm((W - .7) / 3 - .1, .5, .02, .04, .05); place(fr, (-(W - .7) / 3 + k * (W - .7) / 3, -D / 2 + .095, .42)); acc.add(fr, WOOD)
        rbox(acc, (W - .48, .74, .04), (0, -D / 2 + .45, .87), MARBLE, .01, 2)
        rbox(acc, (W - .6, .5, .3), (0, -D / 2 + .5, 1.04), GLASS, .01, 1)
        x = -W / 2 + .5
        k = 0
        while x < W / 2 - .4:
            if k % 3 == 0:
                sd_wheel(acc, (x, -D / 2 + .5, .89), .1, .07, "rind_wax", 40, -110)
            elif k % 3 == 1:
                sd_wedge(acc, (x - .05, -D / 2 + .48, .89), .12, .07, 45, "rind_natural", -110, "blue_cut")
            else:
                sd_brie(acc, (x, -D / 2 + .5, .89), .08, -100)
            sd_price_tag(acc, (x, -D / 2 + .3, .95), (0, 0, 0))
            x += .25
            k += 1
        beam_y = -D / 2 + 1.0
        rbox(acc, (W - .3, .08, .08), (0, beam_y, 2.2), WOOD_D, .02, 2)
        for sx in (-1, 1):
            rbox(acc, (.08, .08, 2.2), (sx * (W / 2 - .15), beam_y, 1.1), WOOD_D, .02, 2)
        for k in range(7):
            sd_provolone(acc, -W / 2 + .5 + k * (W - 1) / 6, beam_y, 2.15, 1.0 - .12 * (k % 2))
        sd_slicer(acc, (W / 2 - .35, -D / 2 + 1.45, .0), 0)
        sd_chalkboard(acc, (-W / 2 + .1, -D / 2 + 1.3, 1.3), "chalk_cheese", .45, .6, 90, "wall")
        sd_wine_crate(acc, (-W / 2 + .4, -D / 2 + 1.5, 0), 20, 6, False)
        name_board(acc, 0, yb - .2, H - .1, 1.2)
        for x in (-1.0, 0, 1.0):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .3, 1.95)
    else:
        arch = frame_bm(W - .2, H + .1, .16, 1.4, .2)
        place(arch, (0, yb - .12, (H + .1) / 2)); acc.add(arch, STONE)
        rbox(acc, (W, .14, .9), (0, yb - .02, .45), STONE, .02, 2, uv=1.5)
        for k, x in enumerate((-1.3, 0, 1.3)):
            sd_wheel_rack(acc, x, yb - .3, 1.2, 2.4, 6, .42, k + 3)
        wood_counter(acc, W - .8, -D / 2 + .5, .75, WOOD_D, WOOD)
        rbox(acc, (W - .76, .79, .03), (0, -D / 2 + .5, .915), MARBLE, .008, 2)
        for k, x in enumerate((-1.15, -.4, .35)):
            sd_cheese_board(acc, (x, -D / 2 + .5, .93), 8 * (k % 2))
        sd_slicer(acc, (1.15, -D / 2 + .55, .93), 0)
        for lvl, n in enumerate((3, 2, 1)):
            for j in range(n):
                sd_wheel(acc, (W / 2 - .5 + (j - (n - 1) / 2) * .27, -D / 2 + 1.3, lvl * .1), .13, .1, ["rind_wax", "parmesan", "rind_natural"][(lvl + j) % 3], 0, j * 40)
        for k in range(9):
            sd_provolone(acc, -W / 2 + .5 + k * (W - 1) / 8, -D / 2 + 1.1, 2.58, 1.0 - .12 * (k % 2))
        rbox(acc, (W - .4, .08, .08), (0, -D / 2 + 1.1, 2.64), WOOD_D, .02, 2)
        sd_wine_crate(acc, (-W / 2 + .45, -D / 2 + 1.4, 0), 10, 6, False)
        sd_wine_crate(acc, (-W / 2 + .45, -D / 2 + 1.4, .21), -5, 6, True)
        sd_chalkboard(acc, (-1.4, -D / 2 - .12, 0), "chalk_cheese", .42, .58, 0, "aframe")
        sd_plant(acc, (W / 2 - .2, -D / 2 + .2, 0), 1.0, "olive", 4)
        for k in range(3):
            sd_honey_jar(acc, (.85 + k * .09, -D / 2 + .7, .93))
        name_board(acc, 0, yb - .25, H - .2, 1.4, .36)
        for x in (-1.4, -.45, .45, 1.4):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .4, 2.1)


# ------------------------------------------------------------------------------------------------ PEIXARIA
def sd_fish_bed(acc, w, d, loc, tilt=16, seed=0, rows=2, mix=("fish_blue", "fish_red")):
    """Ice bed with whole fish laid head to the customer, shrimp heaps, salmon steaks, squid, lemon halves and
    parsley; blank price picks."""
    X, top = sd_ice_bed(acc, w, d, loc, tilt, seed)
    rnd = random.Random(seed)
    n = max(2, int(w / .42))
    for i in range(n):
        fx = -w / 2 + .18 + i * (w - .36) / max(1, n - 1)
        kind = (i + seed) % 5
        for r_ in range(rows if d > .45 else 1):
            fy = -d / 4 + r_ * d / 2 if d > .45 else 0
            if kind in (0, 2):
                for q in range(2):
                    sd_fish(X, (fx - .07 + q * .14, fy + .02 * q, top - .02 + q * .006), .4, 80 + q * 20 + rnd.uniform(-6, 6), mix[(i + r_ + q) % len(mix)], "Body", i + q)
            elif kind == 1:
                for k in range(3):
                    sd_shrimp(X, (fx - .06 + k * .06, fy + .02 * (k % 2), top - .005), 1.6, k * 70)
            elif kind == 3:
                for k in range(3):
                    sd_salmon_steak(X, (fx - .06 + k * .07, fy, top - .01), 1.0, 90 + k * 20, k)
            else:
                sd_mussels(X, (fx, fy, top - .02), .26, .18, i)
        sd_lemon_half(X, (fx + .12, -d / 2 + .08, top - .01), .026, (30, 0, 0))
        sd_parsley(X, (fx - .1, -d / 2 + .09, top - .01), 2, i)
        sd_price_tag(X, (fx, -d / 2 + .05, top + .04), (0, 0, 0))
    return X


def sd_lobster_tank(acc, x, y, w=1.1, d=.55):
    rbox(acc, (w, d, .7), (x, y, .35), C(NAVY), .03, 2)
    rbox(acc, (w + .02, .01, .01), (x, y - d / 2 - .006, .6), C(GOLD), .003, 1)
    rbox(acc, (w, d, .6), (x, y, 1.0), GLASS, .02, 1)
    rbox(acc, (w - .06, .02, .5), (x, y + d / 2 - .04, .97), C("6FB0D0"), .005, 1)
    rbox(acc, (w - .1, .015, .02), (x, y + d / 2 - .06, 1.2), "E_CFEFFF", .004, 1)
    rbox(acc, (w - .08, d - .08, .04), (x, y, .73), C("C9B98A"), .01, 1)
    for k in range(3):
        sd_lobster(acc, (x - .3 + k * .3, y + (-.08 if k % 2 else .06), .75), .75, 40 + k * 70)
    for k in range(5):
        blob(acc, (.03, .025, .02), (x - .4 + k * .2, y + .15, .76), C(["8E9A9A", "6E7A7A", "A8B0A8"][k % 3]), 1, .3, k)
    rbox(acc, (w + .02, d + .02, .05), (x, y, 1.32), C(NAVY), .02, 2)
    tube(acc, [(x + w / 2 - .1, y + .15, 1.3), (x + w / 2 - .1, y + .15, .85)], .01, C(CHROME), 6)
    for k in range(6):
        blob(acc, (.008, .008, .008), (x + w / 2 - .1, y + .15, .9 + k * .065), GLASS, 1, 0, k)


def peixaria_v3(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, TILE_W, TILE_B, 1.1, uv=1.5)
    if tier == 1:
        rbox(acc, (W - .4, .75, .75), (0, -D / 2 + .5, .375), BRUSHED, .03, 2)
        rbox(acc, (W - .5, .01, .3), (0, -D / 2 + .124, .38), TILE_B, .01, 1)
        sd_fish_bed(acc, W - .5, .65, (0, -D / 2 + .5, .76), 16, 1)
        for k in range(2):
            Xc = crate(acc, .5, .34, .14, (W / 2 - .4, yb - .5, k * .15))
            _, top = sd_ice_bed(Xc, .46, .3, (0, 0, .0), 0, k, .02)
            for j in range(3):
                sd_fish(Xc, (-.12 + j * .12, 0, top - .02), .26, 90, ["fish_blue", "fish_red"][j % 2], "Body", j)
        Xc = crate(acc, .5, .34, .14, (-W / 2 + .45, yb - .5, 0))
        for j in range(6):
            sd_shrimp(Xc, (-.16 + (j % 3) * .15, -.06 + (j // 3) * .1, .03), 1.6, j * 60)
        hanging_scale(acc, 0, yb - .5, 2.1)
        fishing_net(acc, -W / 2 + .3, -.3, yb - .07, 1.25, 2.1)
        sd_buoy(acc, (-.6, yb - .12, 1.55), (90, 0, 0))
        sd_rope_coil(acc, (W / 2 - .35, yb - .5, .3), .1, 3)
        sd_chalkboard(acc, (-W / 2 + .3, -D / 2 - .1, 0), "chalk_fish", .34, .48, 0, "aframe")
        name_board(acc, .6, yb - .08, H - .2, .9)
        for x in (-.6, .6):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .3, 1.95)
    elif tier == 2:
        rbox(acc, (W - .3, .8, .78), (0, -D / 2 + .5, .39), BRUSHED, .03, 2)
        rbox(acc, (W - .4, .01, .3), (0, -D / 2 + .09, .4), TILE_B, .01, 1)
        sd_fish_bed(acc, W - .4, .72, (0, -D / 2 + .5, .79), 18, 2)
        rbox(acc, (1.0, .55, .9), (W / 2 - .7, yb - .4, .45), BRUSHED, .03, 2)
        lathe(acc, [(0, 0), (.22, 0), (.22, -.14), (0, -.15)], (W / 2 - .7, yb - .4, .9), C(CHROME), 16, 0)
        tube(acc, [(W / 2 - .5, yb - .2, .9), (W / 2 - .5, yb - .2, 1.25), (W / 2 - .65, yb - .3, 1.25)], .012, C(CHROME), 8)
        sd_cutting_board(acc, (W / 2 - .95, yb - .4, .9), 0, .35, .3)
        sd_fish(acc, (W / 2 - .95, yb - .4, .925), .3, 0, "fish_blue")
        sd_knife(acc, (W / 2 - .85, yb - .5, .93), (0, 0, 10), .2)
        for k in range(3):
            Xc = crate(acc, .5, .34, .14, (-W / 2 + .45, yb - .5, k * .15))
            if k == 2:
                _, top = sd_ice_bed(Xc, .46, .3, (0, 0, 0), 0, k, .02)
                for j in range(3):
                    sd_fish(Xc, (-.12 + j * .12, 0, top - .02), .26, 90, "fish_red", "Body", j)
        hanging_scale(acc, -.2, yb - .6, 2.3)
        fishing_net(acc, -W / 2 + .3, .3, yb - .07, 1.35, 2.4)
        for k in range(2):
            sd_buoy(acc, (-.9 + k * .5, yb - .12, 1.7 - k * .2), (90, 0, 0))
        sd_knife_strip(acc, W / 2 - .7, yb - .075, 1.55, 4, .5)
        sd_apron(acc, (.35, yb - .1, 1.75), NAVY, CREAM)
        sd_chalkboard(acc, (W / 2 - .1, -D / 2 + 1.2, 1.35), "chalk_fish", .45, .6, -90, "wall")
        name_board(acc, .2, yb - .1, H - .15, 1.1)
        for x in (-1.0, 0, 1.0):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .3, 1.95)
    else:
        rbox(acc, (W - .4, 1.1, .7), (0, -D / 2 + .7, .35), BRUSHED, .04, 2)
        rbox(acc, (W - .5, .01, .3), (0, -D / 2 + .149, .36), TILE_B, .01, 1)
        sd_fish_bed(acc, W - .5, .55, (0, -D / 2 + .5, .72), 14, 3)
        Xt = sd_fish_bed(acc, W - .5, .5, (0, -D / 2 + .98, .88), 20, 4, 1, ("fish_red", "fish_blue"))
        sd_lobster(Xt, (0, .05, .08), .8, 90)
        sd_lobster_tank(acc, -W / 2 + .75, yb - .4)
        for k in range(2):
            for j in range(2):
                Xc = crate(acc, .5, .34, .14, (W / 2 - .45, yb - .45 - j * .4, k * .15))
                if k == 1:
                    _, top = sd_ice_bed(Xc, .46, .3, (0, 0, 0), 0, j, .02)
                    for q in range(3):
                        sd_fish(Xc, (-.12 + q * .12, 0, top - .02), .26, 90, ["fish_blue", "fish_red"][(q + j) % 2], "Body", q)
        hanging_scale(acc, .5, -D / 2 + .5, 2.55)
        fishing_net(acc, -.1, W / 2 - .3, yb - .07, 1.4, 2.6)
        for k in range(3):
            sd_buoy(acc, (.2 + k * .45, yb - .12, 2.0 - (k % 2) * .25), (90, 0, 0))
        sd_rope_coil(acc, (W / 2 - .45, yb - .85, 0), .14, 4)
        sd_knife_strip(acc, .6, yb - .075, 1.25, 5, .6)
        sd_chalkboard(acc, (1.6, -D / 2 - .12, 0), "chalk_fish", .42, .58, 0, "aframe")
        sd_scale(acc, (-1.5, -D / 2 + .45, .7), 0)
        name_board(acc, -.6, yb - .2, H - .15, 1.3, .36)
        for x in (-1.4, -.45, .45, 1.4):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .4, 2.05)


# ------------------------------------------------------------------------------------------------ SORVETERIA
FLAVORS = ["gelato_pistachio", "gelato_choc", "gelato_straw", "gelato_cream", "gelato_mint", "gelato_mango", "gelato_berry"]


def sd_gelato_case(acc, W, y, H=.95, rows=2, seed=0):
    """Curved-glass gelato case: navy body, light-wood slats, gold line, steel pans of swirled gelato with
    toppings and paddles, a lit sneeze guard."""
    rbox(acc, (W, .8, H - .05), (0, y, (H - .05) / 2), C(NAVY), .04, 3)
    n = int(W / .07)
    for k in range(n):
        rbox(acc, (.034, .016, H - .4), (-W / 2 + .1 + k * (W - .2) / (n - 1), y - .406, H / 2), WOOD_L, 0, 1)
    rbox(acc, (W - .1, .01, .01), (0, y - .41, H - .15), C(GOLD), .003, 1)
    rbox(acc, (W + .02, .82, .04), (0, y, H), MARBLE, .01, 2)
    cols = int((W - .2) / .27)
    k = seed
    for r_ in range(rows):
        for c in range(cols):
            x = -W / 2 + .2 + c * (W - .4) / max(1, cols - 1)
            sd_gelato_pan(acc, (x, y - .12 + r_ * .25, H + .06), .25, .2, FLAVORS[k % len(FLAVORS)], k, (c + r_) % 3 == 0)
            k += 1
    bm = bmesh.new()
    prof = [(0, 0), (.07, .1), (.12, .22), (.14, .34), (.12, .42)]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        bm.faces.new([bm.verts.new((-W / 2 + .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -a[0], a[1])), bm.verts.new((W / 2 - .03, -b[0], b[1])), bm.verts.new((-W / 2 + .03, -b[0], b[1]))])
    uv_box(bm); place(bm, (0, y - .25, H + .02)); acc.add(bm, GLASS)
    rbox(acc, (W - .04, .45, .012), (0, y + .02, H + .44), GLASS, .004, 1)
    rbox(acc, (W - .1, .02, .012), (0, y + .22, H + .42), LED, .004, 1)
    for s in (-1, 1):
        rbox(acc, (.03, .7, .46), (s * (W / 2 - .015), y, H + .23), C(NAVY), .01, 1)


def sd_cone_stand(acc, x, y, z=0, h=1.1):
    """Wooden cone stand: three trays of waffle cones, the top one with scoops as a display."""
    lathe(acc, [(0, 0), (.18, 0), (.18, .04), (.04, .06), (.03, h), (0, h)], (x, y, z), WOOD, 12, 1)
    for k, zz in enumerate((h * .5, h * .75, h)):
        lathe(acc, [(0, 0), (.16 - k * .03, 0), (.16 - k * .03, .03), (0, .03)], (x, y, z + zz), WOOD_L, 14, 0)
        n = 6 - k
        for j in range(n):
            a = j * 2 * math.pi / n
            r = .11 - k * .025
            fl = (FLAVORS[(j + k) % 7], FLAVORS[(j + k + 3) % 7]) if k == 2 else (FLAVORS[(j + k) % 7],) if k == 1 else ()
            sd_cone(acc, (x + r * math.cos(a), y + r * math.sin(a), z + zz + .03), fl, .1, .024)


def sd_awning(acc, W, y, z, depth=.6, n=None):
    """Gelateria awning: navy and white stripes on a slightly bowed slope, scalloped valance, chrome arms."""
    n = n or max(6, int(W / .22))
    sw = W / n
    for k in range(n):
        x = -W / 2 + (k + .5) * sw
        col = C(NAVY) if k % 2 else C(WHITE)
        bm = bmesh.new()
        prof = [(0, 0), (depth * .35, -.06), (depth * .7, -.15), (depth, -.28)]
        vs = [[bm.verts.new((x + sx * sw / 2, y - py, z + pz)) for (py, pz) in prof] for sx in (-1, 1)]
        for i in range(len(prof) - 1):
            bm.faces.new((vs[0][i], vs[1][i], vs[1][i + 1], vs[0][i + 1]))
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.012)
        uv_box(bm); acc.add(bm, col)
        sc = [(x - sw / 2 + sw * i / 6, .0) for i in range(7)] + [(x + sw / 2 - sw * i / 6, -.06 - .03 * math.sin(math.pi * i / 6)) for i in range(7)]
        vb = outline_bm([(p[0], p[1]) for p in sc], .01)
        place(vb, (0, y - depth + .005, z - .28), (90, 0, 0)); acc.add(vb, col)
    rbox(acc, (W + .04, .04, .04), (0, y - .02, z + .02), C(GOLD), .01, 1)
    for sx in (-1, 1):
        tube(acc, [(sx * (W / 2 - .02), y, z - .5), (sx * (W / 2 - .02), y - depth * .9, z - .26)], .01, C(CHROME), 6)


def sd_parlour_table(acc, tx, ty):
    lathe(acc, [(0, 0), (.22, 0), (.22, .03), (.03, .05), (.03, .72), (.32, .72), (.32, .76), (0, .76)], (tx, ty, 0), C(NAVY), 16, 1)
    lathe(acc, [(.32, .76), (.325, .76), (.325, .77), (.32, .77)], (tx, ty, 0), C(GOLD), 16, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(0, .76), (.3, .76), (.3, .765), (0, .765)], (tx, ty, 0), MARBLE, 16, 0)
    sd_sundae(acc, (tx - .08, ty, .765))
    sd_napkins(acc, (tx + .1, ty + .05, .765))
    for s in (-1, 1):
        cx = tx + s * .45
        lathe(acc, [(0, 0), (.18, 0), (.18, .03), (0, .04)], (cx, ty, .45), C(CREAM), 14, 0)
        for k in range(4):
            a = k * math.pi / 2 + .78
            tube(acc, [(cx + .14 * math.cos(a), ty + .14 * math.sin(a), .45), (cx + .17 * math.cos(a), ty + .17 * math.sin(a), 0)], .008, C(NAVY), 4)
        tube(acc, [(cx + s * .16, ty - .12, .48), (cx + s * .2, ty - .06, .75), (cx + s * .21, ty, .85), (cx + s * .2, ty + .06, .75), (cx + s * .16, ty + .12, .48)], .01, C(NAVY), 5, 2)
        for j in range(3):
            tube(acc, [(cx + s * .175, ty - .1 + j * .1, .5), (cx + s * .2, ty - .08 + j * .08, .78)], .005, C(NAVY), 4)


def sorvetes_v3(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, "T_IK_V2_PaintCream", C(NAVY), .9, uv=1.5)
    if tier == 1:
        sd_gelato_case(acc, 1.6, -D / 2 + .5, .95, 2, 0)
        sd_cone_stand(acc, W / 2 - .3, -D / 2 + .45)
        sd_awning(acc, W - .2, yb - .06, 2.15, .55)
        rbox(acc, (1.2, .25, .03), (-W / 2 + .7, yb - .2, 1.28), WOOD, .01, 1)
        for k in range(5):
            sd_topping_jar(acc, (-W / 2 + .3 + k * .2, yb - .22, 1.295), "sprinkles", [None, "7A4A2E", None, "C0392B", "F2C23F"][k])
        sd_neon_cone(acc, .7, yb - .07, 1.75, .9)
        sd_spoon_cup(acc, (.55, -D / 2 + .35, .99))
        sd_chalkboard(acc, (-W / 2 + .25, -D / 2 - .1, 0), "chalk_ice", .34, .48, 0, "aframe")
        name_board(acc, .5, yb - .08, 1.6, .9)
    elif tier == 2:
        sd_gelato_case(acc, W - .8, -D / 2 + .5, .95, 2, 3)
        sd_cone_stand(acc, W / 2 - .3, -D / 2 + .5)
        sd_awning(acc, W - .1, yb - .06, 2.35, .6)
        rbox(acc, (W - .2, .5, .9), (0, yb - .3, .45), C(NAVY), .03, 2)
        rbox(acc, (W - .18, .54, .04), (0, yb - .3, .92), MARBLE, .01, 1)
        rbox(acc, (.5, .45, .6), (W / 2 - .5, yb - .32, 1.24), C(CREAM), .06, 3)
        for k in range(2):
            tube(acc, [(W / 2 - .6 + k * .2, yb - .55, 1.3), (W / 2 - .6 + k * .2, yb - .6, 1.18)], .025, C(CHROME), 8)
            lathe(acc, [(0, 0), (.03, 0), (.025, .04), (0, .06)], (W / 2 - .6 + k * .2, yb - .6, 1.0), SD, 10, 0, uv_cell="sd:" + FLAVORS[k * 3])
        for k in range(7):
            sd_topping_jar(acc, (-W / 2 + .35 + k * .17, yb - .3, .94), "sprinkles", [None, "7A4A2E", "C0392B", None, "F2C23F", "8FB24A", None][k])
        sd_wall_shelf(acc, -.5, yb - .06, 1.6, 1.2, "jars", 5)
        sd_neon_cone(acc, .9, yb - .07, 1.85, 1.0)
        sd_spoon_cup(acc, (-.2, -D / 2 + .35, .99))
        sd_napkins(acc, (.1, -D / 2 + .35, .99))
        sd_chalkboard(acc, (-W / 2 + .1, -D / 2 + 1.2, 1.4), "chalk_ice", .45, .6, 90, "wall")
        sd_plant(acc, (-W / 2 + .25, -D / 2 + .2, 0), 1.0, "herb", 6)
        name_board(acc, -.3, yb - .08, 1.75, 1.1)
        for x in (-.9, .2):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .3, 1.95)
    else:
        sd_gelato_case(acc, W - 1.3, -D / 2 + .5, .95, 2, 5)
        sd_cone_stand(acc, W / 2 - .45, -D / 2 + .5, 0, 1.25)
        sd_awning(acc, W - .1, yb - .06, 2.65, .7)
        rbox(acc, (W - .2, .5, .9), (0, yb - .3, .45), C(NAVY), .03, 2)
        rbox(acc, (W - .18, .54, .04), (0, yb - .3, .92), MARBLE, .01, 1)
        for k in range(2):
            mx = W / 2 - .5 - k * .6
            rbox(acc, (.5, .45, .6), (mx, yb - .32, 1.24), C(CREAM), .06, 3)
            tube(acc, [(mx, yb - .55, 1.3), (mx, yb - .6, 1.18)], .025, C(CHROME), 8)
            lathe(acc, [(0, 0), (.03, 0), (.025, .04), (0, .06)], (mx, yb - .6, 1.0), SD, 10, 0, uv_cell="sd:" + FLAVORS[k * 2 + 1])
        for k in range(3):
            nx = -W / 2 + .6 + k * .55
            fr = frame_bm(.42, .6, .06, .2, .04); place(fr, (nx, yb - .07, 1.6)); acc.add(fr, C(GOLD))
            plate(acc, .36, .54, (nx, yb - .055, 1.6), LED, .01, .17)
            sd_sundae(acc, (nx, yb - .15, 1.38), (FLAVORS[k], FLAVORS[k + 3]))
            rbox(acc, (.4, .14, .02), (nx, yb - .13, 1.37), WOOD, .005, 1)
        for k in range(6):
            sd_topping_jar(acc, (-.3 + k * .15, yb - .3, .94), "sprinkles", [None, "7A4A2E", "C0392B", None, "F2C23F", "8FB24A"][k])
        sd_neon_cone(acc, .08, yb - .07, 1.95, .9)
        sd_parlour_table(acc, -W / 2 + .55, -D / 2 + 1.35)
        sd_spoon_cup(acc, (.2, -D / 2 + .35, .99))
        sd_napkins(acc, (.5, -D / 2 + .35, .99))
        sd_chalkboard(acc, (W / 2 - .3, -D / 2 - .12, 0), "chalk_ice", .42, .58, 0, "aframe")
        sd_plant(acc, (-W / 2 + .2, -D / 2 + .2, 0), 1.1, "olive", 7)
        name_board(acc, .3, yb - .08, 2.05, 1.3, .36)
        for x in (-1.3, -.3, .7):
            sd_bulb_pendant(acc, x, yb - 1.0, H + .4, 2.1)


# ------------------------------------------------------------------------------------------------ ADEGA
def sd_wine_niches(acc, x, y, w, h, z0=0, lit=False, cols=None, seed=0):
    """Wine wall bay: dark-wood frame and shelves, bottle ends (foil and glass) in every niche, a few bottles
    shown label-out on a slanted display shelf at eye level."""
    rbox(acc, (w, .4, h), (x, y, z0 + h / 2), WOOD_D, .02, 2)
    if lit:
        for s_ in (-1, 1):
            rbox(acc, (.012, .02, h - .1), (x + s_ * (w / 2 - .05), y - .36, z0 + h / 2), WARM, 0, 1)
    n = cols or max(2, int(w / .3))
    cw = (w - .08) / n
    for i in range(n + 1):
        rbox(acc, (.025, .32, h - .08), (x - w / 2 + .04 + i * cw, y - .2, z0 + h / 2), WOOD, .006, 1)
    rows = int((h - .1) / .16)
    foils = ["7A1E2E", GOLD, "1D2B4F", "2A2A2A"]
    disp = rows // 2
    wall = grid_bm(w - .1, h - .1, .29)
    tiled(wall, "bottle_wall", .29, (0, 2))
    place(wall, (x, y - .3, z0 + h / 2)); acc.add(wall, SD)
    for r_ in range(rows):
        z = z0 + .1 + r_ * (h - .14) / rows
        rbox(acc, (w - .08, .32, .02), (x, y - .2, z - .04), WOOD, 0, 1)
        if r_ == disp:
            rbox(acc, (w - .08, .1, .05), (x, y - .33, z - .03), WOOD_D, .01, 1)
            for i in range(n):
                bx = x - w / 2 + .04 + (i + .5) * cw
                sd_wine_bottle(acc, (bx, y - .3, z - .01), ["wl_grape", "wl_leaf", "wl_star", "wl_glass"][(i + seed) % 4], ["2A3B22", "4A1C24", "3A2A1A"][i % 3], foils[i % 4], "burgundy" if i % 2 else "bordeaux", (-12, 0, 0))
        elif (r_ + seed) % 4 == 0 and r_ > 1:
            for i in range(0, n, 2):
                bx = x - w / 2 + .04 + (i + .5) * cw
                sd_wine_bottle(acc, (bx, y - .38, z + .04), ["wl_grape", "wl_leaf", "wl_star"][(i + r_) % 3], ["2A3B22", "4A1C24"][i % 2], foils[(i + r_) % 4], "bordeaux", (-90, 0, 0))


def sd_tasting_set(acc, x, y, z, n=4, seed=0):
    for k in range(n):
        sd_wine_glass(acc, (x - (n - 1) * .1 + k * .2, y - .05, z), ["6A1A2A", "E8D9A0", "6A1A2A", None][k % 4], k % 4 != 3)
    sd_wine_bottle(acc, (x - .05, y + .1, z), "wl_grape", "2A3B22", "7A1E2E", "bordeaux")
    sd_wine_bottle(acc, (x + .12, y + .12, z), "wl_star", "4A1C24", GOLD, "burgundy")
    for k in range(3):
        sd_cork(acc, (x + .25 + k * .02, y + .02, z + .011), (90, 0, k * 40))


def adega_v3(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, BRICK if tier == 3 else "T_IK_WoodDark", WOOD_D, .9, uv=1.5)
    if tier == 1:
        sd_wine_niches(acc, -.3, yb - .26, 1.6, 2.0, 0, False, 5, 0)
        barrel(acc, (W / 2 - .45, -D / 2 + .55, 0), .32, .85)
        lathe(acc, [(0, 0), (.36, 0), (.36, .04), (0, .04)], (W / 2 - .45, -D / 2 + .55, .86), WOOD_D, 16, 0)
        sd_tasting_set(acc, W / 2 - .45, -D / 2 + .55, .9, 2)
        sd_wine_crate(acc, (-W / 2 + .5, -D / 2 + .55, 0), 0, 6, False)
        sd_grapes(acc, (W / 2 - .3, -D / 2 + .45, .98), 1.0, "5A1F4E", 1)
        sd_vine(acc, -1.05, .45, yb - .07, 2.12, 0)
        sd_chalkboard(acc, (.75, yb - .075, 1.45), "chalk_wine", .45, .6, 0, "wall")
        name_board(acc, -.3, yb - .3, 2.2, .9)
        sd_bulb_pendant(acc, W / 2 - .45, yb - 1.0, H + .3, 1.75, False)
    elif tier == 2:
        for k, x in enumerate((-1.05, 0, 1.05)):
            sd_wine_niches(acc, x, yb - .26, .95, 2.2, 0, False, 3, k)
        ty = -D / 2 + .55
        for x in (-.75, .75):
            barrel(acc, (x, ty, 0), .3, .85)
        rbox(acc, (2.2, .55, .06), (0, ty, .88), WOOD_D, .02, 2)
        rbox(acc, (2.2, .01, .012), (0, ty - .28, .88), C(GOLD), .003, 1)
        sd_tasting_set(acc, -.3, ty, .91, 4)
        sd_ice_bucket(acc, (.55, ty, .91))
        sd_grapes(acc, (.85, ty - .05, .98), 1.0, "5A1F4E", 2)
        for k in range(2):
            barrel(acc, (W / 2 - .45, -D / 2 + 1.25, .08 + k * .5), .25, .7, True, 90)
        rbox(acc, (.6, .7, .1), (W / 2 - .45, -D / 2 + 1.25, .05), WOOD_D, .02, 2)
        tube(acc, [(W / 2 - .45, -D / 2 + .9, .33), (W / 2 - .45, -D / 2 + .84, .33), (W / 2 - .45, -D / 2 + .84, .28)], .012, C(GOLD), 6)
        sd_wine_crate(acc, (-W / 2 + .4, -D / 2 + 1.35, 0), 15, 6, True)
        sd_vine(acc, -1.5, 1.5, yb - .3, 2.32, 1)
        sd_chalkboard(acc, (-W / 2 + .2, -D / 2 - .1, 0), "chalk_wine", .36, .5, 0, "aframe")
        name_board(acc, 0, yb - .35, 2.45, 1.1)
        for x in (-.7, .7):
            sd_bulb_pendant(acc, x, ty, H + .3, 1.8, False)
    else:
        arch = frame_bm(W - .3, H + .1, .3, 1.3, .25)
        place(arch, (0, yb - .2, (H + .1) / 2)); acc.add(arch, BRICK)
        for k, x in enumerate((-1.15, 0, 1.15)):
            sd_wine_niches(acc, x, yb - .26, 1.05, 2.3, 0, True, 3, k + 2)
        ty = -D / 2 + .5
        rbox(acc, (W - 1.3, .6, .9), (-.45, ty, .45), WOOD_D, .03, 2)
        n = 18
        for k in range(n):
            rbox(acc, (.034, .016, .6), (-.45 - (W - 1.4) / 2 + k * (W - 1.4) / (n - 1), ty - .306, .45), WOOD, 0, 1)
        rbox(acc, (W - 1.26, .66, .05), (-.45, ty, .92), MARBLE, .01, 2)
        sd_tasting_set(acc, -1.0, ty, .945, 4, 1)
        sd_decanter(acc, (-.2, ty + .1, .945))
        sd_ice_bucket(acc, (.3, ty, .945))
        Xb = sd_cheese_board(acc, (.75, ty, .945), 0)
        for k in range(3):
            sx = -1.3 + k * .85
            sd_stool(acc, (sx, ty - .55, 0), .62)
        for lvl, n in enumerate((3, 2)):
            for j in range(n):
                barrel(acc, (W / 2 - .55, -D / 2 + .6 + (j - (n - 1) / 2) * .55, .02 + lvl * .48), .26, .7, True, 90)
        rbox(acc, (1.6, .35, .05), (-.45, ty, 2.05), WOOD_D, .02, 2)
        for k in range(8):
            lathe(acc, [(0, 0), (.035, 0), (.04, -.05), (.004, -.09), (.004, -.17), (.03, -.2)], (-1.15 + k * .2, ty, 2.02), GLASS, 10, 0)
        for s in (-1, 1):
            tube(acc, [(-.45 + s * .75, ty, 2.07), (-.45 + s * .75, ty, H + .3)], .006, C(INK), 4)
        sd_wine_crate(acc, (W / 2 - .55, -D / 2 + 1.55, 0), 0, 6, False)
        sd_wine_crate(acc, (W / 2 - .55, -D / 2 + 1.55, .21), 8, 6, True)
        sd_vine(acc, -1.75, 1.75, yb - .32, 2.62, 2)
        sd_chalkboard(acc, (-W / 2 + .3, -D / 2 - .12, 0), "chalk_wine", .42, .58, 0, "aframe")
        sd_plant(acc, (-W / 2 + .2, -D / 2 + 1.5, 0), 1.1, "olive", 8)
        for x in (-1.9, 1.9):
            sd_wall_lamp(acc, x, yb - .32, 1.9)
        name_board(acc, 0, yb - .45, H - .05, 1.4, .36)


# ------------------------------------------------------------------------------------------------ SUCOS
JUICE = {"orange": "F28C28", "red": "D8354A", "green": "7DB84A", "yellow": "F2C23F"}


def sd_dispenser(acc, x, y, z, col, fruit="orange", r=.13, h=.38):
    """Juice dispenser: steel base and tap, glass tank with juice, floating slices, navy lid."""
    rbox(acc, (r * 2.6, r * 2.3, .1), (x, y, z + .05), BRUSHED, .02, 2)
    lathe(acc, [(0, 0), (r, 0), (r * 1.05, h), (0, h)], (x, y, z + .1), GLASS, 10, 0, cap_top=False)
    lathe(acc, [(0, .01), (r * .95, .01), (r, h * .78), (0, h * .78)], (x, y, z + .1), C(col), 10, 0)
    for k in range(2):
        sd_citrus_half(acc, (x - .05 + k * .05, y + .02 * (k % 2), z + .1 + h * .78 - .02), .03, fruit, (80, 0, 40 + k * 60))
    lathe(acc, [(0, 0), (r * 1.08, 0), (r * 1.08, .04), (r * .4, .06), (0, .07)], (x, y, z + .1 + h), C(NAVY), 10, 0)
    lathe(acc, [(r * 1.085, .01), (r * 1.09, .025)], (x, y, z + .1 + h), C(GOLD), 10, 0, cap_top=False, cap_bottom=False)
    rbox(acc, (.04, .05, .06), (x, y - r - .02, z + .17), C(CHROME), .01, 1)
    tube(acc, [(x, y - r - .04, z + .2), (x, y - r - .04, z + .26)], .008, C(CHROME), 6)


def sd_fruit_front(acc, W, y, z0=.15, rows=2, kinds=("orange", "lemon", "apple", "lime", "kiwi", "strawberry")):
    n = max(2, int(W / .5))
    for r_ in range(rows):
        for i in range(n):
            x = -W / 2 + (i + .5) * W / n
            X = Xf(acc, (x, y - .05 - (rows - 1 - r_) * .16, z0 + r_ * .3), (22, 0, 0))
            open_box(X, W / n - .04, .3, .1, (0, 0, 0), WOOD, .014, .006, 2)
            sd_fruit_mound(X, W / n - .08, .26, (0, 0, .02), kinds[(i + r_ * 2) % len(kinds)], i + r_ * 5, 0, .045)
            if i % 2 == 0:
                sd_price_tag(X, (0, -.16, .08), (0, 0, 0), False)


def sd_juice_bar_top(acc, x0, x1, y, z, seed=0):
    """Counter top: cutting board with halved fruit and a knife, a juicer, cups with straws and a pitcher."""
    cx = (x0 + x1) / 2
    B = sd_cutting_board(acc, (x0 + .3, y, z), 0, .38, .25)
    sd_citrus_half(B, (-.08, 0, .025), .035, "orange", (0, 0, 0))
    sd_citrus_half(B, (.0, .04, .025), .03, "lime", (0, 0, 0))
    sd_melon_wedge(B, (.1, -.02, .025), .6, 90)
    sd_knife(B, (-.05, -.08, .03), (0, 0, 5), .18)
    sd_juicer(acc, (x0 + .75, y + .05, z))
    for k in range(3):
        sd_cup(acc, (x1 - .55 + k * .12, y - .08, z), [JUICE["orange"], JUICE["red"], JUICE["green"]][k], ["E8505B", NAVY, GOLD][k], ["orange", "lemon", "lime"][k])
    sd_pitcher(acc, (x1 - .15, y + .05, z), JUICE["orange"])


def sucos_v3(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    back_wall(acc, W, yb, H, PLANKS if tier == 1 else "T_IK_V2_PaintCream", C(NAVY) if tier > 1 else None, .9, uv=1.4)
    if tier == 1:
        cw = W - .3
        cy = -D / 2 + .55
        rbox(acc, (cw, .65, .9), (0, cy, .45), WOOD, .02, 2)
        rbox(acc, (cw + .04, .69, .04), (0, cy, .92), WOOD_L, .01, 2)
        sd_fruit_front(acc, cw - .1, cy - .33, .45, 1)
        for k in range(2):
            sd_dispenser(acc, -.5 + k * .45, cy + .1, .94, [JUICE["orange"], JUICE["red"]][k], ["orange", "lemon"][k])
        blender_(acc, .45, cy + .12, .94)
        for k in range(3):
            sd_cup(acc, (.2 + k * .1, cy - .17, .94), [JUICE["orange"], JUICE["yellow"], JUICE["green"]][k], ["E8505B", NAVY, GOLD][k], None)
        rbox(acc, (W - .4, .3, .03), (0, yb - .2, 1.4), WOOD, .01, 1)
        for k, kind in enumerate(("orange", "lemon", "apple")):
            Bk = basket(acc, .4, .26, .1, (-.7 + k * .7, yb - .2, 1.42), 0)
            sd_fruit_mound(Bk, .36, .22, (0, 0, .02), kind, k, 0, .04)
        sd_pineapple(acc, (W / 2 - .3, yb - .25, 1.43), .9)
        sd_banana_bunch(acc, (-W / 2 + .3, yb - .25, 1.43), 1.0, 30)
        sd_chalkboard(acc, (-W / 2 + .25, -D / 2 - .1, 0), "chalk_juice", .34, .48, 0, "aframe")
        name_board(acc, 0, yb - .08, 1.9, .9)
        sd_bulb_pendant(acc, 0, cy, H + .3, 1.85, False)
    elif tier == 2:
        cw = W - .3
        cy = -D / 2 + .55
        rbox(acc, (cw, .7, .95), (0, cy, .475), C(NAVY), .03, 2)
        sd_fruit_front(acc, cw - .1, cy - .36, .5, 1)
        rbox(acc, (cw + .04, .74, .04), (0, cy, .97), WOOD_L, .01, 2)
        for k in range(3):
            sd_dispenser(acc, -1.0 + k * .45, cy + .12, .99, [JUICE["orange"], JUICE["red"], JUICE["green"]][k], ["orange", "lemon", "lime"][k])
        for k in range(2):
            blender_(acc, .6 + k * .3, cy + .12, .99, ["F2C23F", "7DB84A"][k])
        for k in range(4):
            sd_cup(acc, (.35 + k * .11, cy - .2, .99), list(JUICE.values())[k], ["E8505B", NAVY, GOLD, "5FB548"][k], ["orange", "lemon", "lime", None][k])
        for z in (1.45,):
            rbox(acc, (W - .4, .35, .03), (0, yb - .22, z), WOOD, .01, 1)
            for k in range(3):
                Bk = crate(acc, .55, .3, .12, (-.9 + k * .9, yb - .22, z + .015), 0)
                sd_fruit_mound(Bk, .5, .26, (0, 0, .02), ["orange", "lemon", "apple", "lime", "kiwi"][(k + int(z * 2)) % 5], k, 0, .04)
        for k in range(3):
            tube(acc, [(-.8 + k * .8, -D / 2 + 1.25, H + .2), (-.8 + k * .8, -D / 2 + 1.25, 2.1)], .004, ROPE, 4)
            if k == 1:
                sd_pineapple(acc, (-.8 + k * .8, -D / 2 + 1.25, 1.85), .9)
            else:
                sd_banana_bunch(acc, (-.8 + k * .8 - .08, -D / 2 + 1.25, 1.95), 1.0, 90)
        sd_chalkboard(acc, (W / 2 - .1, -D / 2 + 1.2, 1.35), "chalk_juice", .45, .6, -90, "wall")
        sd_plant(acc, (-W / 2 + .2, -D / 2 + .2, 0), 1.0, "herb", 9)
        sd_watermelon(acc, (W / 2 - .3, -D / 2 + 1.4, 0), .9, (0, 90, 30))
        name_board(acc, 0, yb - .08, H - .2, 1.1)
        for x in (-.9, .9):
            sd_bulb_pendant(acc, x, cy, H + .3, 1.95)
    else:
        cy = -D / 2 + .7
        rbox(acc, (W - .6, .9, 1.0), (0, cy, .5), C(NAVY), .04, 3)
        n = int((W - .7) / .07)
        for k in range(n):
            rbox(acc, (.034, .016, .6), (-(W - .7) / 2 + k * (W - .7) / (n - 1), cy - .456, .5), WOOD_L, 0, 1)
        rbox(acc, (W - .56, .94, .05), (0, cy, 1.02), MARBLE, .01, 2)
        rbox(acc, (W - .7, .01, .012), (0, cy - .462, .82), C(GOLD), .003, 1)
        for k in range(4):
            sd_dispenser(acc, -1.05 + k * .5, cy + .25, 1.045, list(JUICE.values())[k], ["orange", "lemon", "lime", "orange"][k])
        blender_(acc, 1.15, cy + .25, 1.045)
        sd_juice_bar_top(acc, -1.6, 1.6, cy - .17, 1.045)
        for k in range(4):
            sd_stool(acc, (-1.2 + k * .8, cy - .75, 0), .7)
        for r_ in range(2):
            rbox(acc, (W - 1.0, .4, .03), (0, yb - .26 - r_ * .05, .95 + r_ * .4), WOOD, .008, 2)
            for sx in (-1, 1):
                bk = outline_bm([(0, 0), (.3, 0), (0, -.22)], .02)
                uv_box(bk); place(bk, (sx * (W / 2 - .6), yb - .06, .935 + r_ * .4), (90, 0, -90)); acc.add(bk, C(GOLD))
            X = Xf(acc, (0, yb - .3 - r_ * .05, 1.0 + r_ * .4), (22, 0, 0))
            for i in range(3):
                x = -W / 2 + .9 + i * (W - 1.8) / 2
                open_box(X, .62, .3, .1, (x, 0, 0), WOOD, .014, .006, 2)
                sd_fruit_mound(Xf(X, (x, 0, 0)), .58, .26, (0, 0, .02), ["orange", "lemon", "apple", "lime", "kiwi", "strawberry"][(i + r_) % 6], i + r_ * 7, 0, .04)
        rbox(acc, (W - .6, .3, .03), (0, yb - .21, 1.92), WOOD, .008, 2)
        sd_pineapple(acc, (-W / 2 + .5, yb - .22, 1.935), 1.0)
        sd_pineapple(acc, (W / 2 - .5, yb - .22, 1.935), 1.0)
        sd_banana_bunch(acc, (-.4, yb - .22, 1.935), 1.1, 0)
        sd_banana_bunch(acc, (.3, yb - .22, 1.935), 1.0, 180)
        for k in range(3):
            sd_pitcher(acc, ([-1.05, -.05, 1.0][k], yb - .22, 1.935), list(JUICE.values())[k], .2, None)
        sd_watermelon(acc, (W / 2 - .35, -D / 2 + 1.55, 0), 1.0, (0, 90, 20))
        sd_watermelon(acc, (W / 2 - .7, -D / 2 + 1.6, 0), .9, (0, 90, -40))
        fw, fd = W - .5, .9
        for sy in (-1, 1):
            rbox(acc, (fw, .07, .07), (0, cy + sy * fd / 2, H), C(NAVY), .02, 2)
        for sx in (-1, 1):
            rbox(acc, (.07, fd, .07), (sx * fw / 2, cy, H), C(NAVY), .02, 2)
            tube(acc, [(sx * fw / 2, cy, H), (sx * fw / 2, cy, H + .5)], .008, C(INK), 4)
        for x in (-1.1, 0, 1.1):
            sd_bulb_pendant(acc, x, cy, H, 2.25)
        sd_chalkboard(acc, (-W / 2 + .3, -D / 2 - .12, 0), "chalk_juice", .42, .58, 0, "aframe")
        sd_plant(acc, (-W / 2 + .2, -D / 2 + 1.5, 0), 1.1, "olive", 10)
        name_board(acc, 0, yb - .08, H - .2, 1.3, .36)


for _sid, _fn in (("padaria", padaria_v3), ("acougue", acougue_v3), ("queijaria", queijaria_v3), ("peixaria", peixaria_v3),
                  ("sorvetes", sorvetes_v3), ("adega", adega_v3), ("sucos", sucos_v3)):
    BUILDERS["sector-" + _sid] = make_sector_v2(_sid, _fn)


def sector_topdown(sid, tier=3):
    """Game-camera check: the T3 from above at the game's pitch (steep, slightly from the front), orthographic."""
    o = bpy.data.objects["sector-%s-t%d" % (sid, tier)]
    by = BASE_Y["sector-" + sid]
    isolate(by, 3.4)
    w, d, h = SECTOR_SIZES[tier - 1]
    camera((o.location.x, o.location.y + .2, .6), (0, -.62, 1), 30, 40, ortho=w * 1.4)
    return render("sector-%s_T%d_topdown" % (sid, tier), (1400, 1100))


def sd_rebuild_sector(sid, top=True):
    sd_material()
    kind = "sector-" + sid
    tris = rebuild(kind)
    out = sheet(kind)
    if top:
        out.append(sector_topdown(sid, 3))
    return tris, out
