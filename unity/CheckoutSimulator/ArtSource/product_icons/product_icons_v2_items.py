"""The 50 product builders for product_icons_v2.py (exec'd into its namespace). Units: the product is ~2 units big,
its front faces -Y (the camera looks from -Y, +X, above)."""


# ================================================================================================ PRODUCE
def strawberry(name, loc, s=1.0, rot=(0, 0, 0), seed=0):
    m = M("Strawberry", "E0262E", rough=.22, coat=.5, sss=.15)
    ms = M("StrawSeed", "F6D35B", rough=.4)
    ml = M("StrawLeaf", "3E9B2F", rough=.45, sss=.2)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=.5)
    for v in bm.verts:
        z = v.co.z / .5
        k = .18 + .82 * ((z + 1) / 2) ** .55         # tapers to a rounded tip at the bottom
        k *= 1.0 - .12 * max(0, z) ** 3               # rounded shoulders
        v.co.x *= k; v.co.y *= k
        v.co.z *= 1.1
    me = bm_to_mesh(bm, name)
    ob = add_obj(name, me, loc, rot, (s, s, s), material=m)
    rr = rnd(seed)
    for i in range(70):
        a = rr.uniform(0, 2 * math.pi); z = rr.uniform(-.9, .8)
        k = (.18 + .82 * ((z + 1) / 2) ** .55) * (1.0 - .12 * max(0, z) ** 3)
        rad = math.sqrt(max(0, 1 - z * z)) * .5 * k
        p = Vector((math.cos(a) * rad * 1.01, math.sin(a) * rad * 1.01, z * .5 * 1.1))
        p = ob.matrix_basis @ p if False else p
        sp = sphere("%sSeed%d" % (name, i), .018 * s, (loc[0] + p.x * s, loc[1] + p.y * s, loc[2] + p.z * s), (0, 0, a),
                    (1, .6, 1.4), material=ms, segs=8, rings=6)
        sp.parent = None
    for k in range(6):
        a = 2 * math.pi * k / 6
        leaf("%sCalyx%d" % (name, k), (loc[0] + math.cos(a) * .14 * s, loc[1] + math.sin(a) * .14 * s, loc[2] + .52 * s), .34 * s,
             (0, .45, a), ml, -35)
    cylinder(name + "Stem", .03 * s, .22 * s, (loc[0], loc[1], loc[2] + .66 * s), (0, .25, 0), material=M("StrawStem", "4C8A2A"), segs=8)
    return ob


@product(122, "morango", view=(.9, -1.3, .9))
def b_morango():
    strawberry("Straw1", (0, 0, .6), 1.0, seed=1)
    strawberry("Straw2", (.62, .35, .45), .8, seed=2)
    strawberry("Straw3", (-.55, .32, .42), .75, seed=3)


@product(123, "abacate", view=(.8, -1.3, 1.0))
def b_abacate():
    skin = MIX("AvoSkin", "2F4A1C", "4E6B2A", "noise", 18, .4, .6, rough=.55)
    flesh = M("AvoFlesh", "D9E58A", rough=.35, sss=.2)
    flesh2 = M("AvoFleshRim", "8DBE45", rough=.35)
    seed_ = M("AvoSeed", "7A4A26", rough=.3, coat=.4)
    def avo_shape(name, loc, rot, half=False, scale=1.0):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=28, radius=.5)
        for v in bm.verts:
            z = v.co.z / .5
            k = 1.0 - .38 * max(0, z) ** 1.3
            v.co.x *= k; v.co.y *= k; v.co.z *= 1.35
        if half:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, -1, 0), clear_inner=True)
        me = bm_to_mesh(bm, name)
        return add_obj(name, me, loc, rot, (scale,) * 3, material=skin)
    avo_shape("AvoWhole", (.5, .4, .62), (0, -.25, -.3), False, 1.0)
    # half: lying on its back, cut face up (the camera looks down on it)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=28, radius=.5)
    for v in bm.verts:
        z = v.co.z / .5
        k = 1.0 - .38 * max(0, z) ** 1.3
        v.co.x *= k; v.co.y *= k; v.co.z *= 1.35
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, 1, 0), clear_inner=True)
    me = bm_to_mesh(bm, "AvoHalf")
    add_obj("AvoHalf", me, (-.35, -.2, .5), (-math.pi / 2, 0, .5), material=skin)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=28, radius=.47)
    for v in bm.verts:
        z = v.co.z / .47
        k = 1.0 - .38 * max(0, z) ** 1.3
        v.co.x *= k; v.co.y = v.co.y * k * .03; v.co.z *= 1.35
    me = bm_to_mesh(bm, "AvoCut")
    add_obj("AvoCut", me, (-.35, -.2, .505), (-math.pi / 2, 0, .5), material=flesh)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=28, radius=.5)
    for v in bm.verts:
        z = v.co.z / .5
        k = 1.0 - .38 * max(0, z) ** 1.3
        v.co.x *= k * 1.0; v.co.y = v.co.y * k * .02; v.co.z *= 1.35
    me = bm_to_mesh(bm, "AvoRim")
    add_obj("AvoRim", me, (-.35, -.2, .5), (-math.pi / 2, 0, .5), material=flesh2)
    blob("AvoSeed", .19, (-.35 + .072, -.2 - .13, .56), (1, 1, .7), seed_)


@product(124, "cogumelos", view=(.85, -1.3, 1.05))
def b_cogumelos():
    tray = M("MushTray", "D8C8A8", rough=.7)
    lathe("MushPunnet", [(0, 0), (.95, 0), (1.05, .35), (.98, .35), (.9, .05), (0, .05)], (0, 0, 0), tray, 4)
    bpy.data.objects["MushPunnet"].rotation_euler = (0, 0, math.pi / 4)
    bpy.data.objects["MushPunnet"].scale = (1.0, .75, 1)
    cap = MIX("MushCap", "8A5A36", "B88A5E", "noise", 6, .35, .65, rough=.6)
    stem = M("MushStem", "F2E8D6", rough=.6)
    gill = M("MushGill", "C9B49A", rough=.7)
    rr = rnd(24)
    spots = [(-.45, -.15), (.0, -.2), (.45, -.12), (-.25, .25), (.25, .25), (.0, .05), (-.6, .2), (.6, .2)]
    for i, (x, y) in enumerate(spots):
        s = rr.uniform(.85, 1.15)
        z = .35 + rr.uniform(0, .12)
        cylinder("MushStem%d" % i, .09 * s, .3, (x, y, z), material=stem, segs=16, bevel=.02)
        lathe("MushCap%d" % i, [(0, .12), (.26, .1), (.28, .05), (.22, 0), (.08, .02), (0, .0)], (x, y, z + .1), cap, 32)
        o = bpy.data.objects["MushCap%d" % i]
        o.scale = (s, s, s * 1.2)
        o.rotation_euler = (rr.uniform(-.3, .3), rr.uniform(-.3, .3), 0)
        lathe("MushGill%d" % i, [(0, .0), (.22, .0), (.08, .02), (0, .02)], (x, y, z + .1), gill, 24)
        bpy.data.objects["MushGill%d" % i].scale = (s, s, s)
        bpy.data.objects["MushGill%d" % i].rotation_euler = o.rotation_euler


@product(125, "frutas_exoticas", view=(.85, -1.3, 1.0))
def b_exoticas():
    pink = M("PitayaSkin", "E83E8C", rough=.35, coat=.4)
    tip = M("PitayaTip", "7CC24A", rough=.4)
    flesh = MIX("PitayaFlesh", "1B1B1B", "FBF8F1", "voronoi", 30, .12, .16, rough=.3)
    # whole pitaya (left back) and a half (front)
    for nm, loc, half in (("PitayaW", (-.45, .35, .65), False), ("PitayaH", (.15, -.25, .4), True)):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=36, v_segments=24, radius=.5)
        for v in bm.verts:
            v.co.z *= 1.25
        if half:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_outer=True)
        me = bm_to_mesh(bm, nm)
        add_obj(nm, me, loc, (0, 0, 0) if not half else (0, 0, 0), material=pink)
        if not half:
            for k in range(14):
                a = k * 2.3994
                z = -.45 + (k / 14) * .95
                rad = math.sqrt(max(0, 1 - (z / .62) ** 2)) * .5
                sc = leaf("%sScale%d" % (nm, k), (loc[0] + math.cos(a) * rad, loc[1] + math.sin(a) * rad, loc[2] + z), .3,
                          (0, -1.1, a), pink, -40)
                cylinder("%sTip%d" % (nm, k), .025, .08, (loc[0] + math.cos(a) * (rad + .1), loc[1] + math.sin(a) * (rad + .1), loc[2] + z + .1),
                         (0, .9, a), material=tip, segs=8)
    disk("PitayaCut", .49, (.15, -.25, .4), M("PitayaWhite", "FBF8F1", rough=.3, sss=.3), .01, (0, 0, 0), 48)
    rs = rnd(77)
    for i in range(60):
        a = rs.uniform(0, 6.28); d = math.sqrt(rs.uniform(0, 1)) * .42
        blob("PitayaSeed%d" % i, .018, (.15 + math.cos(a) * d, -.25 + math.sin(a) * d, .41), (1, 1, .5), M("Seed", "151515", rough=.3), segs=8, rings=6)
    # lychees: bumpy red + one peeled
    lyc = MIX("Lychee", "C2283A", "8E1A2A", "voronoi", 14, .0, .25, rough=.5)
    pearl = M("LycheeFlesh", "F4F0E6", rough=.15, coat=.6, sss=.4)
    for i, (x, y) in enumerate(((.75, .3), (.9, -.2), (.55, -.6))):
        if i == 2:
            blob("LycheeP", .2, (x, y, .2), (1, 1, 1.1), pearl)
        else:
            blob("Lychee%d" % i, .22, (x, y, .22), (1, 1, 1.05), lyc, .02, .15)


# ================================================================================================ DRINKS
@product(126, "agua_coco", view=(.9, -1.35, .7))
def b_agua_coco():
    husk = MIX("CocoHusk", "5FA83A", "7FC24E", "noise", 4, .35, .65, rough=.45, coat=.2)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=.75)
    for v in bm.verts:
        z = v.co.z / .75
        k = 1 - .25 * max(0, z) ** 2
        v.co.x *= k; v.co.y *= k
        v.co.z *= 1.1
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, .62), plane_no=(0, 0, 1), clear_outer=True)
    me = bm_to_mesh(bm, "Coconut")
    add_obj("Coconut", me, (0, 0, .78), material=husk)
    disk("CocoTop", .36, (0, 0, 1.4), M("CocoWhite", "F4EFE0", rough=.5), .02, (0, 0, 0), 32)
    disk("CocoHole", .09, (0, 0, 1.411), M("CocoWater", "E8EEE0", rough=.05, coat=1), .01, (0, 0, 0), 24)
    straw("CocoStraw", (0, 0, 1.2), (.32, -.1, 2.3), "E8505B")
    leaf("CocoLeaf", (.55, .2, .3), .7, (0, -.2, .5), M("CocoLeafG", "3E8F2A", rough=.45), 20)


@product(127, "kombucha", view=(.9, -1.4, .6), fill=.86)
def b_kombucha():
    gl = G("KombuchaGlass", "F2FBF6", .02)
    liq = M("Kombucha", "E9A34A", rough=.08, transmission=.6, sss=.2, coat=.5)
    prof = [(0, 0), (.33, 0), (.36, .04), (.36, 1.2), (.3, 1.4), (.16, 1.62), (.14, 1.9), (.16, 1.95), (0, 1.95)]
    lathe("KombBottle", prof, (0, 0, 0), gl)
    lathe("KombLiquid", [(0, .04), (.33, .04), (.33, 1.18), (.27, 1.38), (.13, 1.6), (0, 1.6)], (0, 0, 0), liq)
    lathe("KombCap", [(0, 1.92), (.17, 1.92), (.18, 2.08), (.15, 2.12), (0, 2.12)], (0, 0, 0), M("KombCapC", "2F6B4F", rough=.35), 32)
    lathe_band("KombLabel", .365, .38, 1.0, M("KombLabelC", "F4EBD8", rough=.5))
    disk("KombPict", .13, (0, -.375, .72), M("KombPictG", "4E9B5A", rough=.4), .012)
    leaf("KombPictLeaf", (.04, -.39, .76), .18, (math.pi / 2, .6, 0), M("KombPictL", "F4EBD8", rough=.4), 0)


@product(128, "cerveja_artesanal", view=(.9, -1.4, .6), fill=.86)
def b_cerveja_art():
    gl = M("CraftGlass", "6E3A0E", rough=.03, transmission=1.0, ior=1.5)
    beer = M("CraftBeer", "7A3D0C", rough=.15, coat=.3)
    prof = [(0, 0), (.36, 0), (.42, .05), (.42, 1.15), (.36, 1.35), (.2, 1.55), (.16, 1.85), (.18, 1.9), (0, 1.9)]
    lathe("CraftBottle", prof, (0, 0, 0), gl)
    lathe("CraftBeerIn", [(0, .05), (.38, .05), (.38, 1.13), (.32, 1.32), (.16, 1.5), (0, 1.5)], (0, 0, 0), beer)
    lathe("CraftCap", [(0, 1.87), (.19, 1.87), (.2, 1.97), (.18, 1.99), (0, 1.99)], (0, 0, 0), M("CraftCapG", "C9962E", rough=.3, metallic=.85), 24)
    lathe("CraftWax", [(.165, 1.62), (.2, 1.62), (.21, 1.95), (.17, 1.99)], (0, 0, 0), M("CraftWaxR", "8E1F2A", rough=.25, coat=.6), 24)
    lathe_band("CraftLabel", .425, .35, 1.0, M("CraftLabelC", "F4EBD8", rough=.5))
    lathe_band("CraftLabelGold", .428, .35, .4, M("CraftGoldBand", "C9962E", rough=.3, metallic=.8))
    lathe_band("CraftLabelGold2", .428, .95, 1.0, M("CraftGoldBand", "C9962E", rough=.3, metallic=.8))
    # hop pictogram: green cone of small scales
    hop = M("Hop", "7DB84A", rough=.45)
    for k in range(5):
        z = .78 - k * .07
        blob("Hop%d" % k, .06 - k * .008, (0, -.44, z), (1.2, .5, .8), hop)


@product(129, "espumante_rose", view=(.9, -1.4, .62), fill=.86)
def b_espumante_rose():
    gl = G("RoseGlass", "FFE9EE", .02)
    wine = M("RoseWine", "F29BB0", rough=.08, transmission=.5, coat=.6)
    prof = [(0, .03), (.3, .01), (.4, 0), (.42, .04), (.42, 1.05), (.36, 1.3), (.2, 1.55), (.15, 1.68), (.15, 2.1), (.17, 2.15), (0, 2.15)]
    lathe("RoseBottle", prof, (0, 0, 0), gl)
    lathe("RoseIn", [(0, .06), (.39, .05), (.39, 1.03), (.33, 1.27), (.17, 1.5), (0, 1.5)], (0, 0, 0), wine)
    gold = M("RoseFoil", "D4AF37", rough=.25, metallic=.9)
    lathe("RoseFoilTop", [(.148, 1.62), (.162, 1.62), (.172, 2.17), (.12, 2.2), (0, 2.2)], (0, 0, 0), gold, 32)
    lathe_band("RoseLabel", .425, .35, .85, M("RoseLabelC", "FBF4EA", rough=.45))
    disk("RoseSeal", .1, (0, -.44, .6), gold, .02)
    disk("RoseSealIn", .065, (0, -.452, .6), M("RoseSealPink", "E86A8A", rough=.3), .01)
    # flute with rosé
    fl = G("Flute", "FFFFFF", .02)
    x, y = .75, -.15
    lathe("FluteGlass", [(0, 0), (.22, 0), (.22, .02), (.03, .04), (.025, .5), (.1, .62), (.13, 1.05), (.14, 1.25), (.13, 1.25), (.09, .64), (0, .58)], (x, y, 0), fl)
    lathe("FluteWine", [(0, .62), (.09, .64), (.12, 1.0), (0, 1.0)], (x, y, 0), wine)
    for k in range(7):
        blob("FluteBub%d" % k, .012, (x + (k % 3 - 1) * .03, y, .7 + k * .04), (1, 1, 1), M("Bubble", "FFFFFF", rough=.0, coat=1))


# ================================================================================================ BAKERY
def roll_bun(name, loc, r=.22, hexc="D99A4E", scale=(1.15, 1, .75), glossy=.4, seed=0):
    m = M("Bun_" + hexc, hexc, rough=.38, coat=glossy, noise=.18, noise_scale=6)
    return blob(name, r, loc, scale, m, .02, .4)


@product(130, "bisnaguinha", view=(.9, -1.3, .85))
def b_bisnaguinha():
    for row in range(2):
        for k in range(4):
            roll_bun("Bisn%d_%d" % (row, k), (-.6 + k * .4, -.18 + row * .38, .3 + row * .02), .24, "E0A85A", (1.0, 1.25, .85), .5)
    bag = M("BisnBag", "FFFFFF", rough=.15, alpha=.18)
    rb("BisnBagBox", (1.75, 1.05, .7), (0, .0, .35), bag, .25)
    tube("BisnTwist", [(.88, 0, .36), (1.0, 0, .36), (1.12, 0, .36)], [.12, .04, .1], 10, bag, subsurf=1)
    cylinder("BisnClip", .06, .1, (.99, 0, .36), (0, math.pi / 2, 0), material=M("BisnClipY", "F2C23F", rough=.35), segs=16)
    sticker("BisnLabel", (.5, .3), (-.1, -.53, .38), M("BisnLabelC", "F6E7C8", rough=.45), bevel=.12)
    disk("BisnPict", .08, (-.1, -.542, .38), M("BisnPictO", "E0A85A"), .01)


@product(131, "pao_integral", view=(.85, -1.35, .9))
def b_pao_integral():
    crust = MIX("WholeCrust", "6E3F1F", "8C5530", "noise", 12, .35, .65, rough=.6)
    crumb = MIX("WholeCrumb", "C9A06A", "8A5A32", "voronoi", 60, .0, .12, rough=.7)
    loaf = rb("WholeLoaf", (1.6, .95, .7), (.15, .08, .35), crust, .18)
    blob("WholeDome", .5, (.15, .08, .7), (1.55, .9, .35), crust)
    seeds = M("Oat", "E8D6A8", rough=.6)
    rr = rnd(31)
    for i in range(40):
        blob("Oat%d" % i, .03, (.15 + rr.uniform(-.7, .7), .08 + rr.uniform(-.35, .35), .86 + rr.uniform(-.02, .03)), (1.6, .8, .5), seeds,
             rot=(0, 0, rr.uniform(0, 3)), segs=8, rings=6)
    for k in range(2):
        x = -.8 - k * .17
        rb("WholeSlice%d" % k, (.14, .9, .95), (x, -.08 - k * .06, .48), crumb, .12, rot=(0, -.12 - k * .1, 0))
        rb("WholeSliceRim%d" % k, (.13, .95, 1.0), (x + .005, -.08 - k * .06, .48), crust, .14, rot=(0, -.12 - k * .1, 0))


@product(132, "pao_fermentacao", view=(.8, -1.3, 1.05))
def b_sourdough():
    crust = MIX("SourCrust", "7A4220", "A9672F", "noise", 5, .3, .7, rough=.55)
    flour = M("Flour", "F2EADB", rough=.85)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=28, radius=.8)
    for v in bm.verts:
        v.co.z = max(v.co.z, -.15) * .7
    me = bm_to_mesh(bm, "Sour")
    ob = add_obj("Sour", me, (0, 0, .15), material=crust)
    displace(ob, .03, .5)
    # scoring: four curved "ears" (lighter, floury inside)
    ear = M("SourEar", "D9A15C", rough=.5)
    for k in range(4):
        a = k * math.pi / 2 + .3
        pts = [(math.cos(a + t * .9) * (.2 + t * .38), math.sin(a + t * .9) * (.2 + t * .38), .66 - t * t * .18) for t in [i / 6 for i in range(7)]]
        tube("SourScore%d" % k, [(p[0], p[1], p[2] + .02) for p in pts], [.045] * 7, 8, ear, subsurf=1)
        tube("SourLip%d" % k, [(p[0] * 1.04, p[1] * 1.04, p[2] + .05) for p in pts], [.025] * 7, 8, crust, subsurf=1)
    rr = rnd(9)
    for i in range(30):
        a = rr.uniform(0, 6.28); d = rr.uniform(0, .55)
        blob("SourFlour%d" % i, .05, (math.cos(a) * d, math.sin(a) * d, .7 - d * d * .25), (1.4, 1.4, .2), flour, segs=8, rings=6)
    board("SourBoard", 2.1, 1.5, (0, 0, -.1), .1, round_=True)


@product(133, "brioche", view=(.85, -1.35, .9))
def b_brioche():
    gl = M("Brioche", "C9761E", rough=.22, coat=.8, noise=.15, noise_scale=5)
    base = rb("BriocheBase", (1.7, .9, .55), (0, 0, .3), gl, .2)
    for k in range(4):
        blob("BriocheLobe%d" % k, .42, (-.6 + k * .4, 0, .62), (1.0, 1.1, .85), gl)
    butter = M("Butter", "F7DC7A", rough=.3, coat=.4, sss=.2)
    rb("BriocheButter", (.45, .3, .16), (.75, -.75, .08), butter, .05)
    rb("BriochePaper", (.7, .5, .02), (.75, -.75, .0), M("ButterPaper", "FBF4E2", rough=.6), .01)


# ================================================================================================ DAIRY
@product(134, "requeijao", view=(.85, -1.3, 1.05))
def b_requeijao():
    gl = G("ReqGlass", "FFFFFF", .03)
    cream = M("ReqCream", "FBF8F1", rough=.25, sss=.3, coat=.3)
    lathe("ReqCup", [(0, 0), (.62, 0), (.68, .05), (.7, .95), (.66, .97), (.62, .95), (.58, .06), (0, .06)], (0, 0, 0), gl)
    lathe("ReqIn", [(0, .06), (.58, .06), (.64, .82), (.5, .86), (.2, .9), (0, .88)], (0, 0, 0), cream)
    tube("ReqSwirl", [(math.cos(t) * (.4 - t * .05), math.sin(t) * (.4 - t * .05), .86 + t * .015) for t in [i * .6 for i in range(12)]],
         [.06] * 12, 10, cream, subsurf=1)
    lathe_band("ReqLabel", .706, .2, .72, M("ReqLabelBlue", "2E6FBF", rough=.4))
    disk("ReqPict", .17, (0, -.71, .46), M("ReqPictW", "F4EBD8", rough=.4), .012)
    lid = M("ReqLid", "C9D2D6", rough=.25, metallic=.85)
    cylinder("ReqLid", .72, .1, (.95, .35, .05), (0, 0, 0), material=lid, segs=48, bevel=.03)
    disk("ReqLidTop", .5, (.95, .35, .101), M("ReqLidBlue", "2E6FBF", rough=.35), .005, (0, 0, 0), 48)


@product(135, "iogurte_grego", view=(.85, -1.3, 1.0))
def b_iogurte_grego():
    pot = M("GreekPot", "FBF8F1", rough=.3, coat=.3)
    yog = M("GreekYog", "FFFDF6", rough=.35, sss=.3)
    honey = M("Honey", "E8A317", rough=.05, coat=1, transmission=.3)
    lathe("GreekPotB", [(0, 0), (.6, 0), (.72, .8), (.76, .84), (.74, .86), (.68, .82), (.56, .06), (0, .06)], (0, 0, 0), pot)
    lathe("GreekIn", [(0, .06), (.56, .06), (.68, .78), (.3, .8), (0, .84)], (0, 0, 0), yog)
    lathe_band("GreekBand", .675, .3, .55, M("GreekBlue", "1F4E9A", rough=.4))
    lathe("GreekBand2", [(.676, .3), (.71, .78)], (0, 0, 0), M("GreekBlue", "1F4E9A", rough=.4))
    bpy.data.objects.remove(bpy.data.objects["GreekBand2"])
    for k in range(6):
        a = k * 1.1
        tube("GreekHoney%d" % k, [(math.cos(a) * .1, math.sin(a) * .1, .85), (math.cos(a) * .4, math.sin(a) * .4, .82), (math.cos(a) * .55, math.sin(a) * .55, .8)],
             [.04, .03, .02], 8, honey, subsurf=1)
    blob("GreekHoneyPool", .18, (0, 0, .85), (1, 1, .15), honey)
    # honey dipper
    wood = M("Dipper", "C98B4E", rough=.5)
    cylinder("DipperStick", .03, 1.0, (.7, -.55, .5), (0, .9, -.6), material=wood, segs=12)
    lathe("DipperHead", [(0, 0), (.09, .02), (.07, .06), (.1, .1), (.07, .14), (.09, .18), (0, .2)], (.32, -.33, .2), honey, 24)


@product(136, "gorgonzola", view=(.85, -1.3, .95))
def b_gorgonzola():
    cheese = MIX("Gorgonzola", "F4EBCF", "2F5A5A", "noise", 6, .56, .6, rough=.55, sss=.2)
    rind = MIX("GorgRind", "D9C9A0", "B7A27A", "noise", 10, .3, .7, rough=.7)
    # wedge: 70 degree slice of a wheel
    r, h = 1.5, .8
    bm = bmesh.new()
    n = 10
    a0, a1 = -math.radians(35), math.radians(35)
    ring_b = [bm.verts.new((math.cos(a0 + (a1 - a0) * i / n) * r, math.sin(a0 + (a1 - a0) * i / n) * r, 0)) for i in range(n + 1)]
    ring_t = [bm.verts.new((v.co.x, v.co.y, h)) for v in ring_b]
    cb, ct = bm.verts.new((0, 0, 0)), bm.verts.new((0, 0, h))
    for i in range(n):
        bm.faces.new((ring_b[i], ring_b[i + 1], ring_t[i + 1], ring_t[i]))
        bm.faces.new((cb, ring_b[i + 1], ring_b[i]))
        bm.faces.new((ct, ring_t[i], ring_t[i + 1]))
    bm.faces.new((cb, ring_b[0], ring_t[0], ct))
    bm.faces.new((cb, ct, ring_t[-1], ring_b[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bm_to_mesh(bm, "Gorg")
    ob = add_obj("Gorg", me, (-.5, 0, 0), (0, 0, math.radians(-110)), material=cheese, bevel=.03)
    lathe("GorgRind", [(r, 0), (r + .02, .02), (r + .02, h - .02), (r, h)], (-.5, 0, 0), rind, 64)
    rind_ob = bpy.data.objects["GorgRind"]
    bo = rind_ob.modifiers.new("Cut", "BOOLEAN"); bo.operation = "INTERSECT"; bo.object = ob; bo.solver = "EXACT"
    rind_ob.hide_render = True                 # (the rind colour is painted by the wedge's edge instead)
    board("GorgBoard", 2.0, 1.2, (0, 0, -.1), .1)
    blob("Walnut", .14, (.7, -.35, .12), (1, .9, .8), MIX("Walnut", "8A5A32", "C08A50", "noise", 15, .4, .6, rough=.6), .03, .2)


@product(137, "salame", view=(.85, -1.3, .9))
def b_salame():
    skin = MIX("SalamiSkin", "6E2A22", "D8C8B4", "noise", 14, .62, .75, rough=.6)
    cut = MIX("SalamiCut", "B23A3A", "F2E0D2", "voronoi", 22, .0, .18, rough=.4, coat=.2)
    tube("Salami", [(-1.0, .15, .3), (-.3, .15, .32), (.4, .15, .3)], [.26, .3, .28], 24, skin, subsurf=1)
    disk("SalamiEnd", .27, (.43, .15, .3), cut, .02, (0, math.pi / 2, 0), 32)
    twine = M("Twine", "E6D3A8", rough=.8)
    for k in range(5):
        x = -.9 + k * .3
        lathe("Twine%d" % k, [(.3, 0), (.31, .01), (.3, .02)], (x, .15, .3), twine, 32)
        bpy.data.objects["Twine%d" % k].rotation_euler = (0, math.pi / 2, 0)
    for k in range(4):
        disk("SalamiSlice%d" % k, .27, (.55 + k * .18, -.45 + k * .05, .05 + k * .015), cut, .03, (0, .15, 0), 32)
    board("SalamiBoard", 2.4, 1.4, (0, -.05, -.1), .1)


# ================================================================================================ SNACKS
@product(138, "pipoca_doce", view=(.85, -1.35, .85), fill=.84)
def b_pipoca():
    stripes = MIX("PopStripe", "E8384F", "FBF8F1", "wave", 5.0, .45, .55, rough=.35)
    n = bpy.data.materials["P2_PopStripe"].node_tree.nodes
    for nd in n:
        if nd.type == "TEX_WAVE":
            nd.wave_type = "BANDS"; nd.bands_direction = "X"; nd.inputs["Distortion"].default_value = 0
    lathe("PopBucket", [(0, 0), (.52, 0), (.72, 1.2), (.68, 1.2), (.5, .05), (0, .05)], (0, 0, 0), stripes, 16)
    pop = M("Popcorn", "F2B33D", rough=.35, coat=.5, noise=.15)
    pink = M("PopcornPink", "F28BA8", rough=.35, coat=.5)
    rr = rnd(13)
    for i in range(70):
        a = rr.uniform(0, 6.28); d = math.sqrt(rr.uniform(0, 1)) * .66
        z = 1.15 + (1 - d / .66) * .35 + rr.uniform(-.04, .06)
        blob("Pop%d" % i, rr.uniform(.08, .12), (math.cos(a) * d, math.sin(a) * d, z), (1, 1, .85),
             pop if i % 3 else pink, .05, .2, segs=12, rings=8)


@product(139, "brigadeiro", view=(.8, -1.3, 1.15))
def b_brigadeiro():
    boxm = M("BrigBox", "6B3A2A", rough=.5)
    gold = M("BrigGold", "D4AF37", rough=.3, metallic=.85)
    rb("BrigBox", (1.6, 1.1, .25), (0, 0, .125), boxm, .05)
    rb("BrigBoxIn", (1.5, 1.0, .22), (0, 0, .15), M("BrigBoxIn", "F4EBD8", rough=.6), .03)
    choc = MIX("Brigadeiro", "3A1A10", "5A2E1C", "noise", 30, .4, .6, rough=.5)
    spr = M("Sprinkle", "2A120A", rough=.4)
    rr = rnd(5)
    for i in range(3):
        for j in range(2):
            x, y = -.5 + i * .5, -.22 + j * .44
            lathe("BrigCup%d%d" % (i, j), [(0, .2), (.17, .2), (.2, .36), (.19, .36), (.15, .22), (0, .22)], (x, y, 0), M("BrigCup", "C9962E", rough=.35, metallic=.6), 24)
            blob("Brig%d%d" % (i, j), .17, (x, y, .4), (1, 1, .95), choc, .01, .5)
    lid = rb("BrigLid", (1.62, 1.12, .12), (.3, .75, .5), boxm, .04, rot=(1.1, 0, .12))
    rb("BrigRibbon", (.12, 1.14, .13), (.3, .75, .5), gold, .02, rot=(1.1, 0, .12))


@product(140, "macarons", view=(.85, -1.35, .8))
def b_macarons():
    cols = [("F4A6C1", "FBF0F4"), ("9ED9C3", "F2FBF6"), ("F6D35B", "FFF8E0"), ("B9A2E0", "F6F0FF"), ("F2A65A", "FFF2E0"), ("C8E07A", "F8FFE8")]
    def macaron(name, loc, rot, ci):
        shell = M("Mac_" + cols[ci][0], cols[ci][0], rough=.45, sss=.2)
        fill = M("MacFill_" + cols[ci][1], cols[ci][1], rough=.35)
        x, y, z = loc
        for k, dz in enumerate((0, .2)):
            lathe("%sShell%d" % (name, k), [(0, 0), (.3, 0), (.34, .04), (.32, .1), (.2, .15), (0, .16)] if k else [(0, .16), (.2, .15), (.32, .1), (.34, .04), (.3, 0), (0, 0)],
                  (0, 0, 0), shell, 32)
            o = bpy.data.objects["%sShell%d" % (name, k)]
            o.location = (x, y, z + dz); o.rotation_euler = rot
        lathe(name + "Fill", [(0, .14), (.31, .14), (.31, .22), (0, .22)], (0, 0, 0), fill, 32)
        o = bpy.data.objects[name + "Fill"]; o.location = (x, y, z); o.rotation_euler = rot
    plate("MacPlate", 1.3, (0, 0, 0), "FBF8F1", "D4AF37")
    macaron("MacA", (-.4, .1, .1), (0, 0, 0), 0)
    macaron("MacB", (.4, .1, .1), (0, 0, 0), 1)
    macaron("MacC", (0, .1, .46), (0, 0, 0), 2)
    macaron("MacD", (-.2, -.55, .25), (1.2, 0, .2), 3)
    macaron("MacE", (.35, -.55, .25), (1.2, 0, -.3), 4)


@product(141, "bombons_belgas", view=(.8, -1.3, 1.15))
def b_bombons():
    gold = M("BonGold", "D4AF37", rough=.22, metallic=.95)
    rb("BonBox", (1.7, 1.2, .25), (0, 0, .125), gold, .06)
    rb("BonTray", (1.58, 1.08, .2), (0, 0, .17), M("BonTray", "2A1A12", rough=.4), .04)
    dark = M("ChocDark", "3A1A10", rough=.25, coat=.6)
    milk = M("ChocMilk", "7A4A2E", rough=.25, coat=.6)
    white = M("ChocWhite", "F4EBD8", rough=.3, coat=.5)
    rr = rnd(8)
    for i in range(4):
        for j in range(3):
            x, y = -.6 + i * .4, -.36 + j * .36
            m = (dark, milk, white)[(i + j) % 3]
            kind = (i * 3 + j) % 4
            if kind == 0:
                blob("Bon%d%d" % (i, j), .14, (x, y, .38), (1, 1, .9), m)
            elif kind == 1:
                rb("Bon%d%d" % (i, j), (.26, .26, .18), (x, y, .36), m, .05)
            elif kind == 2:
                lathe("Bon%d%d" % (i, j), [(0, 0), (.14, 0), (.12, .14), (.06, .2), (0, .21)], (x, y, .27), m, 24)
            else:
                cylinder("Bon%d%d" % (i, j), .13, .14, (x, y, .34), material=m, segs=6, bevel=.03)
            if (i + j) % 2 == 0:
                tube("BonDrizzle%d%d" % (i, j), [(x - .08, y, .47), (x, y + .02, .48), (x + .08, y, .47)], [.012] * 3, 6, gold if m is dark else dark, subsurf=1)
    rb("BonLid", (1.72, 1.22, .14), (.2, .78, .55), gold, .05, rot=(1.15, 0, .1))
    rb("BonRibbon", (.14, 1.24, .15), (.2, .78, .55), M("BonRibbon", "8E1F2A", rough=.3, sheen=.5), .02, rot=(1.15, 0, .1))


# ================================================================================================ MERCEARIA
def tomato_pict(name, loc, s=.1):
    disk(name, s, loc, M("PictTomato", "E0262E", rough=.35), .012)
    for k in range(5):
        a = k * 2 * math.pi / 5
        blob("%sLeaf%d" % (name, k), s * .35, (loc[0] + math.cos(a) * s * .3, loc[1] - .01, loc[2] + s * .7 + math.sin(a) * s * .25), (1.4, .3, .5),
             M("PictLeaf", "3E9B2F", rough=.4), rot=(0, a, 0), segs=8, rings=6)


@product(142, "molho_tomate", view=(.9, -1.4, .75), fill=.84)
def b_molho():
    gl = G("JarGlass", "FFFFFF", .03)
    sauce = M("Sauce", "B3201C", rough=.25, coat=.4, sss=.1)
    lathe("Jar", [(0, 0), (.55, 0), (.6, .06), (.6, 1.0), (.5, 1.12), (.45, 1.15), (.45, 1.25), (0, 1.25)], (0, 0, 0), gl)
    lathe("JarSauce", [(0, .05), (.55, .05), (.56, 1.0), (.42, 1.1), (0, 1.1)], (0, 0, 0), sauce)
    lathe("JarLid", [(0, 1.2), (.49, 1.2), (.5, 1.38), (.47, 1.41), (0, 1.41)], (0, 0, 0), M("JarLidGold", "C9962E", rough=.3, metallic=.85), 48)
    lathe_band("JarLabel", .607, .25, .8, M("JarLabelC", "F4EBD8", rough=.5))
    tomato_pict("JarPict", (0, -.62, .52), .13)
    blob("Basil", .14, (.75, -.3, .06), (1.5, .7, .25), M("BasilLeaf", "2F8F3A", rough=.4, sss=.2), rot=(0, 0, .5))
    blob("TomatoFresh", .3, (-.75, -.25, .28), (1, 1, .88), M("TomatoF", "D9261F", rough=.22, coat=.5))


@product(143, "azeite_extravirgem", view=(.9, -1.4, .62), fill=.86)
def b_azeite():
    gl = M("OliveGlass", "1F4A22", rough=.04, transmission=1.0, ior=1.5)
    oil = M("OliveOilD", "4E6B12", rough=.1, coat=.5)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(.6, .6, 1.3), verts=bm.verts)
    me = bm_to_mesh(bm, "OliveBottle")
    ob = add_obj("OliveBottle", me, (0, 0, .65), material=gl, bevel=.12)
    lathe("OliveNeck", [(.3, 1.28), (.18, 1.45), (.13, 1.6), (.13, 1.9), (.15, 1.95), (0, 1.95)], (0, 0, 0), gl, 32)
    lathe("OliveCap", [(0, 1.88), (.16, 1.88), (.17, 2.12), (.14, 2.15), (0, 2.15)], (0, 0, 0), M("OliveCapG", "C9962E", rough=.3, metallic=.85), 32)
    sticker("OliveLabel", (.5, .62), (0, -.305, .7), M("OliveLabelC", "F4EBD8", rough=.5), bevel=.06)
    sticker("OliveLabelBand", (.5, .08), (0, -.312, .92), M("OliveGoldB", "C9962E", rough=.3, metallic=.8), bevel=.02)
    blob("OlivePict", .07, (0, -.32, .66), (1, .4, 1.3), M("OlivePictG", "6B8E23", rough=.3, coat=.5))
    leaf("OlivePictLeaf", (.07, -.33, .78), .16, (math.pi / 2, -.5, 0), M("OlivePictL", "4E6B2A", rough=.4), 0)
    for k in range(3):
        blob("Olive%d" % k, .1, (.6 + k * .12, -.45 + (k % 2) * .1, .09), (1, 1, 1.3), M("OliveFruit", "4E6B12", rough=.2, coat=.6), rot=(1.5, 0, k))
    for k in range(3):
        leaf("OliveLeaf%d" % k, (.65 + k * .15, -.3, .03), .32, (0, 0, .6 + k * .4), M("OliveLeafC", "5A7A3A", rough=.45), 10)


@product(144, "cafe_capsulas", view=(.85, -1.35, .95))
def b_capsulas():
    boxm = M("CapBox", "2A1A12", rough=.4)
    rb("CapBox", (1.1, .6, 1.1), (-.35, .2, .55), boxm, .05)
    sticker("CapBoxBand", (1.12, .25), (-.35, -.105, .85), M("CapBoxGold", "C9962E", rough=.3, metallic=.8), bevel=.02)
    disk("CapBoxPict", .14, (-.35, -.11, .45), M("CapBoxCream", "F4EBD8", rough=.5), .012)
    blob("CapBoxBean", .07, (-.35, -.125, .45), (1.2, .4, .85), M("Bean", "5A2E1C", rough=.3, coat=.5))
    cols = ["8E1F2A", "1F4E9A", "C9962E", "2F6B4F", "6A2C7A"]
    def capsule(name, loc, rot, col):
        m = M("Cap_" + col, col, rough=.2, metallic=.85)
        lathe(name, [(0, 0), (.1, 0), (.17, .14), (.22, .16), (.22, .18), (0, .18)], loc, m, 32)
        bpy.data.objects[name].rotation_euler = rot
    capsule("Cap1", (.45, -.35, .0), (0, 0, 0), cols[0])
    capsule("Cap2", (.85, -.1, .0), (0, 0, 0), cols[1])
    capsule("Cap3", (.62, .25, .22), (2.0, 0, .5), cols[2])
    capsule("Cap4", (.2, -.65, .2), (1.8, 0, -.4), cols[3])
    capsule("Cap5", (.95, -.55, .2), (1.9, 0, .9), cols[4])


@product(145, "azeite_trufado", view=(.9, -1.4, .6), fill=.86)
def b_azeite_trufado():
    gl = G("TrufGlass", "FFFDF2", .02)
    oil = M("TrufOil", "D9A21E", rough=.06, coat=.7, transmission=.4)
    prof = [(0, 0), (.24, 0), (.27, .04), (.27, 1.6), (.22, 1.75), (.11, 1.9), (.1, 2.35), (.12, 2.4), (0, 2.4)]
    lathe("TrufBottle", prof, (0, 0, 0), gl)
    lathe("TrufOilIn", [(0, .04), (.24, .04), (.24, 1.58), (.19, 1.72), (0, 1.72)], (0, 0, 0), oil)
    lathe("TrufCork", [(0, 2.3), (.1, 2.3), (.11, 2.55), (.13, 2.62), (0, 2.65)], (0, 0, 0), M("Cork", "B98552", rough=.7), 24)
    lathe("TrufWax", [(.1, 2.2), (.135, 2.2), (.14, 2.45), (.11, 2.48)], (0, 0, 0), M("TrufWaxBlack", "1B1B1B", rough=.25, coat=.6), 24)
    gold = M("TrufGold", "D4AF37", rough=.22, metallic=.95)
    lathe_band("TrufLabel", .275, .5, 1.1, M("TrufLabelBlack", "1E1E22", rough=.4))
    lathe_band("TrufLabelG1", .278, .5, .54, gold)
    lathe_band("TrufLabelG2", .278, 1.06, 1.1, gold)
    blob("TrufPict", .07, (0, -.29, .8), (1, .4, .9), gold, .02, .1)
    # black truffle + shavings
    truf = MIX("Truffle", "1E1612", "3A2A20", "voronoi", 30, .0, .3, rough=.7)
    blob("Truffle", .26, (.6, -.25, .24), (1, .95, .88), truf, .05, .25)
    for k in range(3):
        disk("TrufShave%d" % k, .1, (.45 + k * .16, -.65, .02 + k * .01), MIX("TrufCut", "6B5A48", "D9CBB8", "noise", 30, .5, .62, rough=.6), .012, (.1, .2, k), 20)


# ================================================================================================ HOME
@product(146, "sabonete", view=(.85, -1.35, .95))
def b_sabonete():
    soap = M("Soap", "F4A6C1", rough=.2, coat=.6, sss=.4)
    rb("SoapBar", (1.3, .85, .38), (0, 0, .22), soap, .2, seg=6)
    blob("SoapEmboss", .2, (0, 0, .4), (1.6, 1, .1), M("SoapEmb", "F7BCD2", rough=.25, coat=.5, sss=.4))
    bub = G("SoapBubble", "FFFFFF", .0, 1.05)
    rr = rnd(4)
    for i in range(9):
        blob("Bubble%d" % i, rr.uniform(.06, .16), (rr.uniform(-.7, .8), rr.uniform(-.5, .3), rr.uniform(.5, 1.1)), (1, 1, 1), bub, segs=20, rings=12)
    for k in range(5):
        blob("Foam%d" % k, .12, (-.5 + k * .1, -.25, .44), (1, 1, .6), M("Foam", "FFFFFF", rough=.6))
    leaf("SoapLeaf", (.75, -.35, .05), .5, (0, 0, .4), M("SoapLeafG", "8FBF6A", rough=.45), 10)


@product(147, "amaciante", view=(.9, -1.4, .65), fill=.86)
def b_amaciante():
    plast = M("Softener", "8FB8E8", rough=.25, coat=.5)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(1.0, .55, 1.5), verts=bm.verts)
    me = bm_to_mesh(bm, "SoftBody")
    ob = add_obj("SoftBody", me, (0, 0, .75), material=plast, bevel=.18)
    tube("SoftHandle", [(.3, 0, 1.2), (.42, 0, 1.55), (.3, 0, 1.75), (.05, 0, 1.75)], [.09] * 4, 12, plast, subsurf=1)
    lathe("SoftNeck", [(.2, 1.48), (.22, 1.62), (0, 1.62)], (-.25, 0, 0), plast, 32)
    lathe("SoftCap", [(0, 1.6), (.25, 1.6), (.26, 1.85), (.22, 1.88), (0, 1.88)], (-.25, 0, 0), M("SoftCapLilac", "B9A2E0", rough=.3), 32)
    sticker("SoftLabel", (.72, .7), (0, -.28, .7), M("SoftLabelW", "FBF8F1", rough=.4), bevel=.2)
    # pictogram: a fluffy cloud + small flower
    cl = M("SoftCloud", "B9D3F2", rough=.4)
    for k, (x, z, r) in enumerate(((-.12, .7, .1), (.0, .76, .13), (.13, .7, .1))):
        blob("SoftCloud%d" % k, r, (x, -.3, z), (1, .3, 1), cl)
    for k in range(5):
        a = k * 2 * math.pi / 5
        blob("SoftFlower%d" % k, .04, (.16 + math.cos(a) * .05, -.31, .52 + math.sin(a) * .05), (1, .3, 1), M("SoftPetal", "F4A6C1", rough=.4))


@product(148, "perfume", view=(.9, -1.4, .7), fill=.84)
def b_perfume():
    gl = G("PerfGlass", "FFF4F8", .01, 1.5)
    liq = M("PerfLiquid", "F28BB0", rough=.05, transmission=.7, coat=.8)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=.62, radius2=.62, depth=1.0)
    me = bm_to_mesh(bm, "PerfBottle")
    ob = add_obj("PerfBottle", me, (0, 0, .5), (0, 0, math.pi / 8), material=gl, bevel=.05, smooth=False)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=.52, radius2=.52, depth=.75)
    me = bm_to_mesh(bm, "PerfLiq")
    add_obj("PerfLiq", me, (0, 0, .45), (0, 0, math.pi / 8), material=liq, smooth=False)
    gold = M("PerfGold", "D4AF37", rough=.18, metallic=.95)
    cylinder("PerfCollar", .2, .14, (0, 0, 1.07), material=gold, segs=32, bevel=.02)
    lathe("PerfCap", [(0, 1.14), (.32, 1.14), (.36, 1.3), (.3, 1.62), (0, 1.66)], (0, 0, 0), gold, 8)
    bpy.data.objects["PerfCap"].rotation_euler = (0, 0, math.pi / 8)
    disk("PerfPlate", .2, (0, -.58, .55), gold, .015, (math.pi / 2, 0, 0), 32)
    for k in range(3):
        blob("PerfPetal%d" % k, .12, (.75 + k * .1, -.3 - k * .12, .03), (1.3, .8, .2), M("Petal", "F4A6C1", rough=.4, sss=.3), rot=(0, 0, k))


@product(149, "kit_spa", view=(.85, -1.35, 1.0))
def b_kit_spa():
    wicker = MIX("Wicker", "C08A50", "8A5A32", "voronoi", 18, .0, .4, rough=.7)
    lathe("SpaTray", [(0, 0), (1.1, 0), (1.15, .25), (1.08, .25), (1.03, .05), (0, .05)], (0, 0, 0), wicker, 4)
    t = bpy.data.objects["SpaTray"]; t.rotation_euler = (0, 0, math.pi / 4); t.scale = (1.0, .7, 1)
    towel = M("Towel", "9ED9C3", rough=.85)
    for k in range(2):
        cylinder("SpaTowel%d" % k, .18, .8, (-.35 + k * .0, -.1 + k * .32, .24), (0, math.pi / 2, 0), material=towel if k == 0 else M("Towel2", "FBF8F1", rough=.85), segs=24, bevel=.06)
    cylinder("SpaCandle", .2, .3, (.45, .25, .2), material=M("Candle", "F6E7C8", rough=.4, sss=.4), segs=32, bevel=.02)
    cylinder("SpaWick", .01, .08, (.45, .25, .38), material=M("Wick", "2A2A2A"), segs=6)
    blob("SpaFlame", .04, (.45, .25, .45), (1, 1, 1.8), M("Flame", "FFB25A", emission=6))
    gl = G("SpaJar", "FFFFFF", .03)
    lathe("SpaJar", [(0, 0), (.18, 0), (.2, .04), (.2, .4), (0, .4)], (.5, -.3, .05), gl, 32)
    lathe("SpaSalt", [(0, .02), (.18, .02), (.18, .32), (0, .34)], (.5, -.3, .05), M("SpaSalt", "F2A7C3", rough=.8), 32)
    lathe("SpaJarLid", [(0, .4), (.2, .4), (.2, .48), (0, .48)], (.5, -.3, .05), M("SpaWood", "C98B4E", rough=.5), 32)
    lathe("SpaOil", [(0, 0), (.13, 0), (.14, .45), (.06, .55), (.06, .65), (0, .65)], (-.6, .3, .05), M("SpaOilBottle", "6B4FA0", rough=.1, transmission=.6, coat=.6), 24)
    for k in range(5):
        a = k * 2 * math.pi / 5
        blob("SpaFlower%d" % k, .07, (.05 + math.cos(a) * .08, -.45 + math.sin(a) * .08, .12), (1, 1, .3), M("SpaPetal", "FBF8F1", rough=.4))
    blob("SpaFlowerC", .04, (.05, -.45, .14), (1, 1, .6), M("SpaFlowerY", "F6D35B", rough=.4))


# ================================================================================================ FROZEN
@product(150, "nuggets", view=(.85, -1.35, 1.0))
def b_nuggets():
    boxm = M("NugBox", "E8384F", rough=.4)
    rb("NugBox", (1.4, .9, .55), (0, .2, .28), boxm, .05)
    rb("NugBoxIn", (1.3, .8, .52), (0, .2, .3), M("NugBoxIn", "FBF4E2", rough=.6), .03)
    frost = M("Frost", "EAF6FB", rough=.8)
    nug = MIX("Nugget", "C9761E", "E8A84A", "noise", 18, .35, .65, rough=.65)
    rr = rnd(15)
    for i in range(12):
        blob("Nug%d" % i, .17, (rr.uniform(-.5, .5), .2 + rr.uniform(-.28, .28), .5 + rr.uniform(0, .15)), (1.25, 1, .55), nug, .04, .3, rot=(rr.uniform(-.4, .4), rr.uniform(-.4, .4), rr.uniform(0, 3)))
    for i in range(3):
        blob("NugF%d" % i, .17, (-.45 + i * .45, -.55 + (i % 2) * .1, .1), (1.25, 1, .55), nug, .04, .3, rot=(0, 0, i))
    lathe("NugDip", [(0, 0), (.2, 0), (.24, .16), (.22, .16), (0, .14)], (.75, -.4, 0), M("DipCup", "FBF8F1", rough=.3), 32)
    blob("NugSauce", .21, (.75, -.4, .13), (1, 1, .12), M("Ketchup", "C0261C", rough=.15, coat=.6))


@product(151, "polpa_fruta", view=(.85, -1.35, .9))
def b_polpa():
    film = M("PolpaFilm", "FFFFFF", rough=.1, alpha=.25)
    cols = [("D8354A", "strawberry"), ("F2C23F", "mango"), ("6A2C7A", "acai"), ("F28C28", "orange")]
    for k, (c, _) in enumerate(cols):
        z = .12 + k * .22
        x, y = (k % 2) * .25 - .1, -k * .05
        rb("Polpa%d" % k, (1.1, .75, .18), (x, y, z), M("Polpa_" + c, c, rough=.35, sss=.3), .08, rot=(0, 0, k * .12))
        rb("PolpaFilm%d" % k, (1.18, .82, .21), (x, y, z), film, .09, rot=(0, 0, k * .12))
    frost = M("Frost", "EAF6FB", rough=.8)
    rr = rnd(2)
    for i in range(16):
        blob("PolpaFrost%d" % i, .04, (rr.uniform(-.5, .6), rr.uniform(-.5, .3), .78 + rr.uniform(0, .02)), (1, 1, .3), frost, segs=8, rings=6)
    strawberry("PolpaBerry", (.85, -.45, .25), .45, seed=7)


@product(152, "risoto", view=(.8, -1.3, 1.15))
def b_risoto():
    tray = M("RisTray", "1E1E22", rough=.3)
    rb("RisTray", (1.6, 1.15, .3), (0, 0, .15), tray, .1)
    rice = MIX("Risotto", "F2E2B8", "E0C890", "voronoi", 40, .0, .4, rough=.4, coat=.3)
    rb("RisFill", (1.45, 1.0, .1), (0, 0, .28), rice, .05)
    rr = rnd(22)
    for i in range(40):
        blob("RisGrain%d" % i, .04, (rr.uniform(-.65, .65), rr.uniform(-.43, .43), .34), (1.6, .8, .7), rice, rot=(0, 0, rr.uniform(0, 3)), segs=8, rings=6)
    mush = M("RisMush", "A07850", rough=.5)
    for i in range(6):
        disk("RisMush%d" % i, .1, (rr.uniform(-.5, .5), rr.uniform(-.35, .35), .37), mush, .02, (0, 0, 0), 16)
    pea = M("Pea", "7DB84A", rough=.3, coat=.4)
    for i in range(10):
        blob("RisPea%d" % i, .035, (rr.uniform(-.6, .6), rr.uniform(-.4, .4), .37), (1, 1, 1), pea, segs=10, rings=6)
    leaf("RisHerb", (.3, -.1, .4), .25, (0, 0, .5), M("Parsley", "3E9B2F", rough=.45), 0)


@product(153, "pizza_napolitana", view=(.8, -1.3, 1.2))
def b_pizza():
    board("PizzaBoard", 2.4, 2.4, (0, 0, -.12), .1, round_=True)
    crust = MIX("PizzaCrust", "D9A15C", "3A2418", "voronoi", 9, .0, .08, rough=.55)
    lathe("PizzaBase", [(0, 0), (.95, 0), (1.05, .08), (1.02, .17), (.9, .19), (.85, .12), (0, .1)], (0, 0, 0), crust, 64)
    disk("PizzaSauce", .86, (0, 0, .11), M("PizzaSauce", "B3201C", rough=.3, coat=.3), .02, (0, 0, 0), 48)
    moz = M("Mozzarella", "FBF4E2", rough=.3, sss=.4, coat=.2)
    rr = rnd(53)
    for i in range(7):
        a = i * 0.9 + .2; d = .25 + (i % 3) * .2
        blob("Moz%d" % i, .15, (math.cos(a) * d, math.sin(a) * d, .14), (1, 1, .3), moz, .02, .3)
    basil = M("Basil", "2F8F3A", rough=.35, sss=.2, coat=.3)
    for i in range(5):
        a = i * 1.3; d = .45
        leaf("Basil%d" % i, (math.cos(a) * d, math.sin(a) * d, .2), .26, (0, 0, a), basil, 12)
    oil = M("OliveOil", "E8C34A", rough=.05, coat=1)
    for i in range(6):
        blob("PizzaOil%d" % i, .04, (rr.uniform(-.6, .6), rr.uniform(-.6, .6), .135), (1, 1, .15), oil)


# ================================================================================================ ICE CREAM
def stick(name, loc):
    cylinder(name, .09, .8, loc, scale=(1, .4, 1), material=MIX("Stick", "E6C98F", "C9A06A", "wave", 8, .3, .8, rough=.7), segs=16, bevel=.03)


@product(154, "picole_frutas", view=(.6, -1.4, .55), fill=.84)
def b_picole_frutas():
    ice_m = M("FruitPop", "F2526E", rough=.15, coat=.6, transmission=.25, sss=.3)
    body = rb("FruitPop", (.8, .42, 1.5), (0, 0, 1.05), ice_m, .2, seg=8)
    kiwi = MIX("Kiwi", "2A2A1A", "8BC34A", "voronoi", 25, .12, .16, rough=.3)
    for k, (x, z) in enumerate(((-.15, 1.4), (.18, .95), (-.12, .6))):
        disk("PopKiwi%d" % k, .13, (x, -.215, z), M("KiwiGreen", "8BC34A", rough=.3, coat=.4), .02)
        disk("PopKiwiCore%d" % k, .04, (x, -.227, z), M("KiwiCore", "EEF2C8", rough=.3), .01)
        for j in range(10):
            a = j * 2 * math.pi / 10
            blob("PopKiwiSeed%d_%d" % (k, j), .012, (x + math.cos(a) * .07, -.228, z + math.sin(a) * .07), (1, .5, 1.6), M("Seed", "151515", rough=.3), rot=(0, -a, 0), segs=6, rings=4)
    for k, (x, z) in enumerate(((.18, 1.5), (-.2, 1.05), (.15, .62))):
        blob("PopBerry%d" % k, .08, (x, -.21, z), (1, .4, 1.2), M("Strawberry", "E0262E", rough=.22, coat=.5, sss=.15))
    stick("PopStick", (0, 0, .05))


@product(155, "acai_tigela", view=(.8, -1.3, 1.15))
def b_acai():
    bowl = MIX("AcaiBowl", "8A5A32", "B98552", "wave", 4, .3, .8, rough=.45, coat=.3)
    lathe("AcaiBowl", [(0, 0), (.45, 0), (.5, .05), (.95, .45), (1.0, .55), (.95, .56), (.9, .5), (.45, .12), (0, .12)], (0, 0, 0), bowl, 64)
    acai = M("Acai", "4A1748", rough=.35, coat=.4)
    blob("AcaiFill", .92, (0, 0, .42), (1, 1, .16), acai)
    ban = M("Banana", "F6E7B8", rough=.4)
    for k in range(5):
        disk("AcaiBanana%d" % k, .12, (-.45 + k * .15, -.3, .58), ban, .03, (0, 0, 0), 24)
    gran = MIX("Granola", "C98B4E", "8A5A32", "noise", 20, .4, .6, rough=.7)
    rr = rnd(3)
    for i in range(30):
        blob("Granola%d" % i, .04, (rr.uniform(-.1, .5), rr.uniform(.0, .55), .58), (1.3, 1, .7), gran, rot=(0, 0, rr.uniform(0, 3)), segs=8, rings=6)
    strawberry("AcaiBerry", (.35, -.2, .68), .4, seed=4)
    for k in range(6):
        blob("AcaiBlue%d" % k, .05, (-.3 + (k % 3) * .1, .25 + (k // 3) * .1, .6), (1, 1, 1), M("Blueberry", "2E3A7A", rough=.3, coat=.3), segs=12, rings=8)
    leaf("AcaiMint", (-.1, .1, .64), .2, (0, 0, .5), M("Mint", "3E9B2F", rough=.4), 15)


@product(156, "picole_gourmet", view=(.6, -1.4, .55), fill=.84)
def b_picole_gourmet():
    choc = M("PopChoc", "3A1A10", rough=.2, coat=.7)
    inner = M("PopCream", "F6E7C8", rough=.4, sss=.3)
    body = rb("GourPop", (.82, .44, 1.55), (0, 0, 1.05), choc, .2, seg=8)
    bite = sphere("GourBite", .34, (.42, -.05, 1.78), material=inner, segs=24, rings=16)
    displace(bite, .04, .3); bite.hide_render = True
    bo = body.modifiers.new("Bite", "BOOLEAN"); bo.operation = "DIFFERENCE"; bo.object = bite; bo.solver = "EXACT"
    inn = rb("GourIn", (.68, .3, 1.45), (0, 0, 1.05), inner, .15, seg=6)
    bo2 = inn.modifiers.new("Bite", "BOOLEAN"); bo2.operation = "DIFFERENCE"; bo2.object = bite; bo2.solver = "EXACT"
    pist = M("Pistachio", "8DB04A", rough=.5)
    rr = rnd(6)
    for i in range(28):
        blob("GourNut%d" % i, .04, (rr.uniform(-.38, .38), -.23, rr.uniform(.55, .9)), (1.2, .5, .8), pist, rot=(0, rr.uniform(0, 3), 0), segs=8, rings=6)
    gold = M("GourGold", "D4AF37", rough=.25, metallic=.9)
    pts = [(-.35 + t * .7, -.235, 1.25 + .1 * math.sin(t * 12)) for t in [i / 10 for i in range(11)]]
    tube("GourDrizzle", pts, [.02] * 11, 8, M("WhiteChoc", "F4EBD8", rough=.3, coat=.4), subsurf=1)
    stick("GourStick", (0, 0, .05))


@product(157, "bolo_sorvete", view=(.8, -1.35, .95))
def b_bolo_sorvete():
    lathe("CakeBoard", [(0, 0), (1.1, 0), (1.1, .05), (0, .05)], (0, 0, 0), M("CakeGold", "D4AF37", rough=.25, metallic=.9), 64)
    layers = [("F4A6C1", .05, .35), ("FBF4E2", .35, .62), ("6B3A2A", .62, .9)]
    for k, (c, z0, z1) in enumerate(layers):
        lathe("CakeL%d" % k, [(0, z0), (.85, z0), (.88, z0 + .02), (.88, z1 - .02), (.85, z1), (0, z1)], (0, 0, 0), M("IceL_" + c, c, rough=.35, sss=.3), 64)
    choc = M("CakeDrip", "3A1A10", rough=.15, coat=.8)
    lathe("CakeTop", [(0, .9), (.89, .9), (.9, .96), (.84, .99), (0, .99)], (0, 0, 0), choc, 64)
    for k in range(14):
        a = k * 2 * math.pi / 14
        L = .12 + .1 * ((k * 7) % 3)
        tube("CakeDrip%d" % k, [(math.cos(a) * .9, math.sin(a) * .9, .95), (math.cos(a) * .9, math.sin(a) * .9, .95 - L)], [.05, .035], 8, choc, subsurf=1)
    cream = M("Whip", "FFFDF6", rough=.4)
    cherry = M("Cherry", "C0141E", rough=.1, coat=1)
    for k in range(6):
        a = k * 2 * math.pi / 6 + .3
        x, y = math.cos(a) * .6, math.sin(a) * .6
        lathe("CakeWhip%d" % k, [(0, 0), (.13, 0), (.1, .1), (.05, .18), (0, .22)], (x, y, .99), cream, 12)
        blob("CakeCherry%d" % k, .07, (x, y, 1.25), (1, 1, 1), cherry)
    for k in range(3):
        tube("CakeWafer%d" % k, [(-.15 + k * .15, .1, 1.0), (-.12 + k * .17, .15, 1.45)], [.04, .04], 10, M("Wafer", "D9A15C", rough=.5), subsurf=0)


# ================================================================================================ SECTOR RECIPES
@product(158, "pao_de_queijo", view=(.8, -1.3, 1.1))
def b_pao_queijo():
    wicker = MIX("Wicker", "C08A50", "8A5A32", "voronoi", 18, .0, .4, rough=.7)
    lathe("PdqBasket", [(0, 0), (.8, 0), (1.05, .35), (1.0, .38), (.75, .06), (0, .06)], (0, 0, 0), wicker, 48)
    cloth = MIX("Cloth", "E8384F", "FBF8F1", "voronoi", 3, .0, .5, rough=.8)
    blob("PdqCloth", .95, (0, 0, .2), (1, 1, .12), cloth)
    pdq = MIX("PaoQueijo", "E8B860", "C9862E", "noise", 9, .35, .7, rough=.45, coat=.3)
    spots = [(-.35, -.2), (.1, -.3), (.45, -.05), (-.15, .25), (.3, .35), (-.5, .2), (.0, .02)]
    for i, (x, y) in enumerate(spots):
        blob("Pdq%d" % i, .2, (x, y, .38 + (i == 6) * .18), (1, 1, .85), pdq, .03, .25)
    # one broken open: cheese stretch
    blob("PdqHalfA", .2, (.8, -.6, .12), (1, 1, .7), pdq, .03, .25)
    blob("PdqCheese", .12, (.8, -.75, .17), (1.2, .6, .6), M("PdqCheese", "FFF2C4", rough=.3, sss=.4, coat=.3))


@product(159, "torta_morango", view=(.8, -1.3, 1.05))
def b_torta_morango():
    plate("TortaPlate", 1.3, (0, 0, 0), "FBF8F1", "D4AF37")
    crust = MIX("TartCrust", "D9A15C", "B97A3A", "noise", 10, .35, .65, rough=.5)
    prof = [(0, .05), (.95, .05), (1.0, .1)] + [(1.0 + .03 * math.sin(k * 1.4), .12 + k * .03) for k in range(10)] + [(.9, .4), (.88, .3), (0, .3)]
    lathe("TartShell", prof, (0, 0, 0), crust, 48)
    disk("TartCream", .88, (0, 0, .33), M("TartCream", "FFF2D0", rough=.35, sss=.3), .04, (0, 0, 0), 48)
    for ring, (n, d) in enumerate(((10, .68), (6, .38), (1, 0))):
        for k in range(n):
            a = 2 * math.pi * k / n + ring * .3
            strawberry("TartBerry%d_%d" % (ring, k), (math.cos(a) * d, math.sin(a) * d, .5), .36, seed=ring * 10 + k)
    leaf("TartMint", (.1, -.05, .75), .22, (0, -.3, .3), M("Mint", "3E9B2F", rough=.4), 15)


@product(160, "burrata", view=(.8, -1.3, 1.0))
def b_burrata():
    plate("BurPlate", 1.3, (0, 0, 0), "2F3A40")
    bur = M("Burrata", "FBF8F1", rough=.25, sss=.5, coat=.3)
    blob("Burrata", .55, (-.1, .05, .55), (1, 1, .82), bur, .015, .5)
    lathe("BurKnot", [(0, 0), (.12, 0), (.08, .1), (.14, .2), (.05, .3), (0, .32)], (-.1, .05, .95), bur, 24)
    blob("BurCream", .3, (.2, -.35, .38), (1.3, .9, .3), M("Stracciatella", "FFFDF0", rough=.3, sss=.5, coat=.5), .03, .3)
    tom = M("Cherry Tomato", "D9261F", rough=.15, coat=.7)
    for k in range(3):
        blob("BurTom%d" % k, .13, (.65 + (k % 2) * .15, .1 - k * .25, .2), (1, 1, .9), tom)
    for k in range(3):
        leaf("BurBasil%d" % k, (-.55 + k * .2, -.45, .2), .3, (0, 0, k), M("Basil", "2F8F3A", rough=.35, sss=.2, coat=.3), 12)
    for k in range(5):
        blob("BurOil%d" % k, .05, (-.4 + k * .2, -.2 + (k % 2) * .5, .11), (1, 1, .1), M("OliveOil", "E8C34A", rough=.05, coat=1))


@product(161, "queijo_canastra", view=(.8, -1.3, .95))
def b_canastra():
    rind = MIX("CanastraRind", "C98B2E", "E0B050", "noise", 6, .3, .7, rough=.55, coat=.2)
    paste = MIX("CanastraPaste", "F6DE8A", "E8C35A", "voronoi", 25, .0, .9, rough=.5)
    lathe("Canastra", [(0, 0), (1.0, 0), (1.08, .06), (1.1, .5), (1.04, .58), (0, .58)], (0, 0, .1), rind, 64)
    cut = rb("CanastraCut", (1.4, 1.4, 1.0), (.62, -.62, .55), paste, .0, rot=(0, 0, 0))
    cut.hide_render = True
    ob = bpy.data.objects["Canastra"]
    bo = ob.modifiers.new("Cut", "BOOLEAN"); bo.operation = "DIFFERENCE"; bo.object = cut; bo.solver = "EXACT"
    inner = lathe("CanastraIn", [(0, .005), (1.06, .005), (1.075, .5), (0, .55)], (0, 0, .1), paste, 64)
    cut2 = rb("CanastraCut2", (1.4, 1.4, 1.2), (.62, -.62, .5), paste, .0)
    cut2.hide_render = True
    bo2 = inner.modifiers.new("Keep", "BOOLEAN"); bo2.operation = "INTERSECT"; bo2.object = cut2; bo2.solver = "EXACT"
    inner.location = (.12, -.12, 0)
    board("CanBoard", 2.6, 2.0, (0, 0, 0), .1)
    gold = M("CanGold", "D4AF37", rough=.25, metallic=.9)
    disk("CanSeal", .16, (-.35, -.98, .4), gold, .02, (math.pi / 2, 0, -.35), 32)


@product(162, "linguica_artesanal", view=(.8, -1.3, 1.1))
def b_linguica():
    board("LingBoard", 2.4, 1.8, (0, 0, -.1), .1)
    skin = MIX("Linguica", "A8432E", "C9653E", "noise", 12, .35, .65, rough=.35, coat=.5)
    pts = []
    for i in range(70):
        t = i / 69 * 3.3 * math.pi
        r = .12 + t * .075
        pts.append((math.cos(t) * r, math.sin(t) * r, .14))
    tube("LingCoil", pts, [.13] * len(pts), 14, skin, subsurf=1)
    for k in range(2):
        tube("LingSkewer%d" % k, [(-.9, -.15 + k * .3, .2), (.9, .15 - k * .3, .2)], [.015, .015], 6, M("Skewer", "D9C9A0", rough=.6), subsurf=0)
    rosm = M("Rosemary", "3E6B3A", rough=.5)
    for k in range(9):
        blob("Rosem%d" % k, .03, (.7 + k * .04, -.55 + k * .02, .06), (2.5, .5, .5), rosm, rot=(0, 0, .3 + (k % 2) * .6), segs=8, rings=6)
    for k in range(3):
        blob("LingGarlic%d" % k, .09, (-.8 + k * .14, -.55, .08), (1, 1, 1.1), M("Garlic", "F4EBD8", rough=.5))


@product(163, "picanha_wagyu", view=(.8, -1.3, 1.05))
def b_picanha():
    board("WagyuBoard", 2.6, 1.8, (0, 0, -.1), .1, "4A2E1C")
    meat = MIX("Wagyu", "B8323C", "F8E4DA", "noise", 7, .54, .58, rough=.35, coat=.3, sss=.15)
    fat = M("WagyuFat", "F6E7D6", rough=.4, sss=.3, coat=.2)
    seared = MIX("Seared", "5A2A18", "8A4A2A", "noise", 10, .3, .7, rough=.5)
    for k in range(3):
        x = -.65 + k * .5
        rb("WagyuSlice%d" % k, (.42, 1.0, .35), (x, 0, .2), meat, .06, rot=(0, -.35, 0))
        rb("WagyuFat%d" % k, (.42, .18, .38), (x, .55, .2), fat, .06, rot=(0, -.35, 0))
        rb("WagyuCrust%d" % k, (.03, 1.16, .37), (x - .2, .07, .2), seared, .01, rot=(0, -.35, 0))
    gold = M("WagyuGold", "D4AF37", rough=.25, metallic=.9)
    blob("WagyuSalt", .16, (.7, -.55, .08), (1, 1, .4), M("Salt", "FBF8F1", rough=.8), .03, .1)
    lathe("WagyuDish", [(0, 0), (.18, 0), (.22, .1), (.2, .1), (0, .02)], (.72, -.55, 0), gold, 32)
    for k in range(4):
        blob("WagyuPepper%d" % k, .02, (.4 + k * .08, -.75, .03), (1, 1, 1), M("Pepper", "2A2A2A"), segs=8, rings=6)


@product(164, "limonada_suica", view=(.8, -1.4, .7), fill=.84)
def b_limonada():
    gl = G("LemonGlass", "FFFFFF", .02)
    drink = M("Limonada", "D8EFC0", rough=.25, sss=.4, coat=.3, transmission=.2)
    lathe("LemGlass", [(0, 0), (.42, 0), (.5, 1.6), (.47, 1.6), (.4, .05), (0, .05)], (0, 0, 0), gl, 48)
    lathe("LemDrink", [(0, .05), (.4, .05), (.46, 1.3), (0, 1.3)], (0, 0, 0), drink, 48)
    lathe("LemFoam", [(0, 1.28), (.46, 1.28), (.47, 1.38), (.3, 1.45), (0, 1.46)], (0, 0, 0), M("LemFoamW", "F6FBEF", rough=.6), 48)
    for k in range(3):
        ice("LemIce%d" % k, (-.12 + k * .13, .05 - k * .05, 1.3 + k * .05), .18, k)
    lime = MIX("LimeSlice", "D8F09A", "6DB33F", "voronoi", 8, .0, .5, rough=.3)
    disk("LemSlice", .26, (.42, -.1, 1.5), lime, .05, (math.pi / 2, .3, .6), 32)
    straw("LemStraw", (-.1, .05, .2), (-.3, .2, 2.1), "6DB33F")


@product(165, "smoothie_acai", view=(.8, -1.4, .7), fill=.84)
def b_smoothie():
    cup = G("SmoothCup", "FFFFFF", .05)
    sm = M("Smoothie", "5A1F5E", rough=.4, coat=.3)
    lathe("SmCup", [(0, 0), (.42, 0), (.55, 1.55), (.52, 1.55), (.4, .05), (0, .05)], (0, 0, 0), cup, 48)
    lathe("SmFill", [(0, .05), (.4, .05), (.52, 1.45), (.3, 1.55), (0, 1.58)], (0, 0, 0), sm, 48)
    lathe("SmDome", [(.55, 1.55), (.5, 1.75), (.3, 1.9), (0, 1.95)], (0, 0, 0), cup, 48)
    straw("SmStraw", (.0, .0, .5), (.25, -.15, 2.35), "F28BB0")
    for k in range(5):
        blob("SmBerry%d" % k, .07, (-.2 + k * .1, -.1 + (k % 2) * .15, 1.62), (1, 1, 1), M("Blueberry", "2E3A7A", rough=.3, coat=.3), segs=12, rings=8)
    strawberry("SmStraw1", (.18, .1, 1.72), .35, seed=6)
    blob("SmBanana", .28, (.78, -.3, .12), (1, 1, .3), M("Banana", "F6E7B8", rough=.4))


@product(166, "ceviche", view=(.8, -1.3, 1.1))
def b_ceviche():
    gl = G("CevBowl", "F2FBFF", .03)
    lathe("CevBowl", [(0, 0), (.3, 0), (.3, .25), (.95, .7), (1.0, .75), (.96, .76), (.9, .72), (.3, .32), (0, .32)], (0, 0, 0), gl, 64)
    fish = M("CevFish", "F8F0E6", rough=.3, sss=.5, coat=.4)
    onion = M("RedOnion", "9E3A7A", rough=.3, sss=.3)
    rr = rnd(16)
    for i in range(16):
        a = rr.uniform(0, 6.28); d = math.sqrt(rr.uniform(0, 1)) * .6
        rb("CevCube%d" % i, (.16, .16, .14), (math.cos(a) * d, math.sin(a) * d, .62 + rr.uniform(0, .1)), fish, .04, rot=(rr.uniform(0, 1), rr.uniform(0, 1), rr.uniform(0, 3)))
    for i in range(6):
        tube("CevOnion%d" % i, [(rr.uniform(-.5, .5), rr.uniform(-.5, .5), .72) for _ in range(3)], [.02] * 3, 6, onion, subsurf=1)
    cil = M("Cilantro", "3E9B2F", rough=.4)
    for i in range(8):
        leaf("CevCil%d" % i, (rr.uniform(-.5, .5), rr.uniform(-.5, .5), .78), .12, (0, 0, rr.uniform(0, 3)), cil, 10)
    lime = MIX("LimeSlice", "D8F09A", "6DB33F", "voronoi", 8, .0, .5, rough=.3)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=.25)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_outer=True)
    me = bm_to_mesh(bm, "CevLime")
    add_obj("CevLime", me, (.85, -.55, .25), (0, 0, 0), material=M("LimeRind", "3E8F2A", rough=.3, coat=.5))
    disk("CevLimeCut", .24, (.85, -.55, .25), lime, .01, (0, 0, 0), 24)
    for k in range(4):
        blob("CevChili%d" % k, .03, (-.3 + k * .15, -.3, .78), (1, 1, 1), M("Chili", "E0262E", rough=.3), segs=8, rings=6)


@product(167, "lagosta_grelhada", view=(.8, -1.3, 1.05))
def b_lagosta():
    plate("LobPlate", 1.4, (0, 0, 0), "FBF8F1", "D4AF37")
    shell = MIX("LobShell", "D9381E", "8E1F14", "noise", 6, .35, .7, rough=.3, coat=.6)
    meat = M("LobMeat", "F8E6D8", rough=.35, sss=.5)
    grill = M("Grill", "6B3A1E", rough=.5)
    # tail half: segmented shell with the meat on top (cut lengthwise)
    for k in range(6):
        x = -.6 + k * .2
        w = .42 - k * .03
        blob("LobSeg%d" % k, w, (x, 0, .2), (.55, 1, .45), shell)
        blob("LobMeat%d" % k, w * .85, (x, 0, .3), (.55, .9, .25), meat)
        rb("LobGrill%d" % k, (.03, w * 1.4, .02), (x + .05, 0, .42), grill, .005, rot=(0, 0, .5))
    for k in range(3):
        leaf("LobFan%d" % k, (.65, -.2 + k * .2, .18), .35, (0, 0, -.6 + k * .6), shell, -10)
    # claw
    blob("LobClaw", .3, (-.5, -.75, .22), (1.4, .7, .6), shell, rot=(0, 0, .4))
    blob("LobClawTip", .16, (-.08, -.95, .2), (1.3, .5, .5), shell, rot=(0, 0, .2))
    lemon = M("Lemon", "F6D35B", rough=.3, coat=.3)
    blob("LobLemon", .22, (.75, -.6, .2), (1.3, 1, 1), lemon)
    blob("LobButter", .14, (.55, .65, .15), (1, 1, .6), M("Butter", "F7DC7A", rough=.3, coat=.4, sss=.2))
    leaf("LobParsley", (.2, .55, .25), .25, (0, 0, .5), M("Parsley", "3E9B2F", rough=.45), 0)


@product(168, "milkshake", view=(.8, -1.4, .62), fill=.86)
def b_milkshake():
    gl = G("ShakeGlass", "FFFFFF", .02)
    shake = M("Milkshake", "F4A6C1", rough=.45, sss=.3)
    lathe("ShakeGlass", [(0, 0), (.4, 0), (.4, .05), (.12, .12), (.12, .35), (.38, .5), (.5, 1.6), (.47, 1.6), (.35, .55), (0, .5)], (0, 0, 0), gl, 48)
    lathe("ShakeFill", [(0, .52), (.35, .55), (.46, 1.5), (0, 1.5)], (0, 0, 0), shake, 48)
    cream = M("Whip", "FFFDF6", rough=.4)
    for k in range(4):
        lathe("ShakeWhip%d" % k, [(0, 0), (.42 - k * .1, 0), (.38 - k * .1, .1), (0, .12)], (0, 0, 1.5 + k * .1), cream, 16)
        bpy.data.objects["ShakeWhip%d" % k].rotation_euler = (0, 0, k * .4)
    blob("ShakeCherry", .1, (.05, -.05, 2.0), (1, 1, 1), M("Cherry", "C0141E", rough=.1, coat=1))
    tube("ShakeCherryStem", [(.05, -.05, 2.08), (.1, -.08, 2.25)], [.01, .01], 6, M("CherryStem", "4C8A2A"), subsurf=0)
    straw("ShakeStraw", (-.1, .05, .7), (-.35, .2, 2.4), "E8505B")
    for k in range(8):
        blob("ShakeSprink%d" % k, .015, (-.2 + k * .06, -.2 + (k % 3) * .1, 1.75), (3, 1, 1), M("Spr_%d" % (k % 4), ["E8505B", "F6D35B", "7DB84A", "3E8FD6"][k % 4], rough=.4), rot=(0, 0, k), segs=6, rings=4)


@product(169, "gelato_pistache", view=(.8, -1.35, .85), fill=.84)
def b_gelato():
    cup = M("GelatoCup", "FBF8F1", rough=.3, coat=.3)
    lathe("GelCup", [(0, 0), (.42, 0), (.6, .7), (.62, .72), (.6, .74), (.56, .7), (.4, .05), (0, .05)], (0, 0, 0), cup, 48)
    lathe_band("GelCupBand", .52, .3, .45, M("GelBand", "8DB04A", rough=.4))
    pist = M("GelatoPist", "A8C66C", rough=.55, sss=.3)
    for k, (x, y, z, r) in enumerate(((-.15, 0, .85, .38), (.2, .1, .9, .34), (0, -.05, 1.2, .32))):
        blob("GelScoop%d" % k, r, (x, y, z), (1, 1, .9), pist, .04, .3)
    nut = M("PistNut", "7FA040", rough=.5)
    rr = rnd(7)
    for i in range(14):
        blob("GelNut%d" % i, .05, (rr.uniform(-.3, .3), rr.uniform(-.35, .1), 1.3 + rr.uniform(0, .2)), (1.3, .8, .7), nut, rot=(0, 0, rr.uniform(0, 3)), segs=8, rings=6)
    tube("GelSpoon", [(.3, -.1, 1.1), (.55, -.25, 1.5)], [.03, .03], 8, M("GelSpoonG", "D4AF37", rough=.25, metallic=.9), subsurf=0)
    for k in range(3):
        blob("GelPistWhole%d" % k, .07, (.7 + k * .1, -.45, .06), (1.3, .9, .7), M("PistShell", "D9C9A0", rough=.5), rot=(0, 0, k))


@product(170, "vinho_rose", view=(.9, -1.4, .62), fill=.86)
def b_vinho_rose():
    gl = G("RoseWineGlass", "FFF0F2", .02)
    wine = M("RoseWine", "F29BB0", rough=.08, transmission=.5, coat=.6)
    prof = [(0, .03), (.3, .01), (.38, 0), (.4, .04), (.4, 1.25), (.36, 1.4), (.18, 1.6), (.14, 1.75), (.14, 2.2), (.16, 2.25), (0, 2.25)]
    lathe("RoseWBottle", prof, (0, 0, 0), gl)
    lathe("RoseWIn", [(0, .06), (.37, .05), (.37, 1.23), (.33, 1.37), (.15, 1.55), (0, 1.55)], (0, 0, 0), wine)
    lathe("RoseWCap", [(.135, 1.9), (.15, 1.9), (.16, 2.27), (.12, 2.3), (0, 2.3)], (0, 0, 0), M("RoseWFoil", "B9A2E0", rough=.25, metallic=.6), 32)
    lathe_band("RoseWLabel", .405, .35, .95, M("RoseWLabelC", "FBF4EA", rough=.45))
    grape = M("PictGrape", "C2486E", rough=.35)
    for k, (x, z) in enumerate(((-.05, .75), (.05, .75), (0, .68), (-.1, .68), (.1, .68), (-.05, .61), (.05, .61), (0, .54))):
        blob("RoseWGrape%d" % k, .035, (x, -.415, z), (1, .4, 1), grape, segs=10, rings=6)
    wg = G("WineGlassG", "FFFFFF", .02)
    x, y = .8, -.2
    lathe("RoseWGlass", [(0, 0), (.24, 0), (.24, .02), (.03, .04), (.025, .55), (.2, .7), (.25, .95), (.2, 1.15), (.19, 1.15), (.24, .95), (.19, .72), (0, .66)], (x, y, 0), wg)
    lathe("RoseWGlassWine", [(0, .68), (.18, .72), (.23, .9), (0, .9)], (x, y, 0), wine)


@product(171, "espumante_casa", view=(.9, -1.4, .62), fill=.86)
def b_espumante_casa():
    gl = M("SparkGlass", "1F3A22", rough=.03, transmission=1.0, ior=1.5)
    wine = M("SparkWine", "E8D27A", rough=.08, transmission=.5, coat=.6)
    prof = [(0, .03), (.3, .01), (.42, 0), (.44, .04), (.44, 1.05), (.38, 1.3), (.21, 1.55), (.16, 1.68), (.16, 2.1), (.18, 2.15), (0, 2.15)]
    lathe("SparkBottle", prof, (0, 0, 0), gl)
    gold = M("SparkFoil", "D4AF37", rough=.22, metallic=.95)
    lathe("SparkFoilTop", [(.155, 1.5), (.175, 1.5), (.185, 2.17), (.13, 2.22), (0, 2.22)], (0, 0, 0), gold, 32)
    lathe_band("SparkLabel", .445, .35, .9, M("SparkLabelC", "F4EBD8", rough=.45))
    lathe_band("SparkLabelG", .448, .35, .4, gold)
    lathe_band("SparkLabelG2", .448, .85, .9, gold)
    disk("SparkMedal", .11, (0, -.46, .63), gold, .02)
    disk("SparkMedalIn", .07, (0, -.472, .63), M("SparkNavy", "1D2B4F", rough=.35), .01)
    fl = G("Flute", "FFFFFF", .02)
    x, y = .8, -.2
    lathe("SparkFlute", [(0, 0), (.22, 0), (.22, .02), (.03, .04), (.025, .5), (.1, .62), (.13, 1.05), (.14, 1.25), (.13, 1.25), (.09, .64), (0, .58)], (x, y, 0), fl)
    lathe("SparkFluteWine", [(0, .62), (.09, .64), (.12, 1.0), (0, 1.0)], (x, y, 0), wine)
    for k in range(8):
        blob("SparkBub%d" % k, .012, (x + (k % 3 - 1) * .03, y, .68 + k * .04), (1, 1, 1), M("Bubble", "FFFFFF", rough=.0, coat=1))
    for k in range(5):
        blob("SparkStar%d" % k, .03, (.3 + k * .12, -.6 + (k % 2) * .1, .05), (1, 1, .3), gold, segs=8, rings=6)
