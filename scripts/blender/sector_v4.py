"""Special sectors, round 4: SUPERMARKET service sections (exec'd after fixture_tiers.py and sector_detail.py).

Round 3 built artisan boutiques; a Brazilian supermarket "seção de atendimento" is stainless and white under bright
LED light: a long refrigerated glass service counter with product on white trays, industrial machines, digital price
panels, the "pegue sua senha" ticket dispenser with its number display, a self-service cooler of packed trays and a
navy bulkhead (testeira) where the game writes the sector name. Round 3's product detail is kept (sector_detail.py).

Screens are separate meshes on their own slots, "E_PriceScreen" and "E_TicketScreen": the game draws pictograms and
the real prices at runtime (no baked text, multilingual). For the concept renders only, those slots carry preview
images (ArtSource/fixture_tiers/textures/preview/, made by sector_screens_preview.py).
"""
INOX = BRUSHED                      # stainless
WHITE_P = C(WHITE)
LED_W = "E_F4FAFF"                  # cool-white LED line
PREVIEW = os.path.join(ART, "textures", "preview")


def v4_screen_material(name, image):
    """Emissive screen material for the preview renders (KitRemap reads 'E_PriceScreen.N' as 'E_PriceScreen')."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    t = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(PREVIEW, image), check_existing=True)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 1.2
    b.inputs["Roughness"].default_value = .3
    return m


def v4_materials():
    sd_material()
    for i in range(3):
        v4_screen_material("E_PriceScreen.%d" % i, "FT_PricePreview_%d.png" % i)
    v4_screen_material("E_TicketScreen", "FT_TicketPreview.png")
    m = material(LED_W)
    m.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = 5.0


def screen_quad(acc, w, h, loc, key, rot=(0, 0, 0)):
    """Flat screen facing -Y with 0..1 UVs over the whole image."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new((x * w / 2, 0, z * h / 2)) for x, z in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(list(reversed(vs)))
    for l in f.loops:
        l[uvl].uv = ((l.vert.co.x / w) + .5, (l.vert.co.z / h) + .5)
    place(bm, loc, rot)
    acc.add(bm, key)


# ================================================================================================ machines
def v4_price_panel(acc, x, y, z, w=1.0, variant=0, rot=(0, 0, 0)):
    """Digital price board (a 16:9 TV in a black bezel on a wall bracket)."""
    X = Xf(acc, (x, y, z), rot)
    h = w * 9 / 16
    rbox(X, (w + .05, .05, h + .05), (0, .025, 0), C("1B1E24"), .012, 2)
    screen_quad(X, w, h, (0, -.002, 0), "E_PriceScreen.%d" % (variant % 3))
    rbox(X, (.12, .04, .12), (0, .07, 0), C("2A2E36"), .01, 1)


def v4_ticket_display(acc, x, y, z, rot=(0, 0, 0)):
    """'Agora atendendo' number display: a small black box with a red LED number screen."""
    X = Xf(acc, (x, y, z), rot)
    rbox(X, (.42, .08, .22), (0, .04, 0), C("1B1E24"), .015, 2)
    screen_quad(X, .36, .16, (0, -.002, 0), "E_TicketScreen")


def v4_ticket_dispenser(acc, loc, yaw=0):
    """'Pegue sua senha': chrome pole on a round base with the classic red ticket-roll dispenser and a navy
    sign plate (blank: the game writes it)."""
    X = Xf(acc, loc, (0, 0, yaw))
    lathe(X, [(0, 0), (.14, 0), (.14, .02), (.04, .04), (0, .04)], (0, 0, 0), C(CHROME), 16, 0)
    tube(X, [(0, 0, .03), (0, 0, 1.15)], .018, C(CHROME), 8)
    lathe(X, [(0, 0), (.07, 0), (.085, .04), (.08, .1), (.05, .14), (0, .15)], (0, 0, 1.12), C("C0392B"), 14, 1, rot=(-70, 0, 0))
    rbox(X, (.07, .01, .025), (0, -.12, 1.2), C("1B1E24"), .004, 1)
    rbox(X, (.05, .002, .03), (0, -.125, 1.18), C(WHITE), 0, 1, rot=(20, 0, 0))
    plate(X, .26, .18, (0, 0, 1.42), C(NAVY), .015, .03)
    plate(X, .22, .14, (0, -.009, 1.42), C(CREAM), .006, .025)
    tube(X, [(0, 0, 1.15), (0, 0, 1.33)], .01, C(CHROME), 6)


def v4_bandsaw(acc, loc, yaw=0):
    """Serra fita: stainless cabinet base, sliding table, tall column, rounded top wheel housing, visible blade,
    blade guard, red stop button and a pusher plate."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.6, .55, .85), (0, 0, .425), INOX, .03, 2)
    rbox(X, (.62, .57, .03), (0, 0, .86), C(STEEL), .01, 1)
    rbox(X, (.7, .65, .03), (0, -.02, .9), C(CHROME), .01, 2)
    for s in (-1, 1):
        rbox(X, (.03, .65, .02), (s * .36, -.02, .92), C(CHROME), .005, 1)
    rbox(X, (.16, .2, 1.05), (-.2, .18, 1.42), INOX, .03, 2)
    rbox(X, (.62, .3, .5), (0, .1, 1.97), INOX, .12, 4)
    rbox(X, (.6, .02, .14), (0, -.05, 2.1), C(NAVY), .02, 2)
    rbox(X, (.012, .012, .82), (.12, -.04, 1.33), C("D8DDE2"), 0, 1)
    rbox(X, (.08, .06, .35), (.12, -.04, 1.54), C(STEEL), .01, 1)
    lathe(X, [(0, 0), (.025, 0), (.025, .02), (0, .025)], (-.22, -.08, 1.2), C("C0392B"), 10, 0, rot=(90, 0, 0))
    lathe(X, [(0, 0), (.025, 0), (.025, .02), (0, .025)], (-.22, -.08, 1.3), C("37A04A"), 10, 0, rot=(90, 0, 0))
    rbox(X, (.2, .02, .14), (-.05, -.15, .99), C(CHROME), .01, 1)
    tube(X, [(-.05, -.16, 1.06), (-.05, -.26, 1.1)], .012, C(INK), 6)
    sd_tbone(X, (.15, -.1, .915), 1.1, 0, 2)


def v4_grinder(acc, loc, yaw=0):
    """Moedor de carne: stainless motor body, horizontal grinding head with the perforated plate and ring nut, a big
    feed tray on top, red/green switches; ground meat coming out into a tray."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.3, .45, .32), (0, .05, .16), INOX, .05, 3)
    lathe(X, [(0, 0), (.075, 0), (.08, .02), (.075, .22), (0, .22)], (0, -.12, .25), C(STEEL), 14, 0, rot=(90, 0, 0))
    lathe(X, [(0, 0), (.09, 0), (.09, .04), (0, .04)], (0, -.32, .25), C(CHROME), 16, 0, rot=(90, 0, 0))
    lathe(X, [(0, 0), (.07, 0)], (0, -.361, .25), C("8A9298"), 14, 0, rot=(90, 0, 0))
    for k in range(7):
        a = k * 2 * math.pi / 7
        lathe(X, [(0, 0), (.008, 0)], (.04 * math.cos(a), -.362, .25 + .04 * math.sin(a)), C("3A3F45"), 6, 0, rot=(90, 0, 0))
    lathe(X, [(.04, 0), (.05, .12)], (0, -.18, .3), C(STEEL), 12, 0, cap_top=False, cap_bottom=False)
    rbox(X, (.42, .38, .03), (0, -.18, .43), C(STEEL), .01, 2)
    for s in (-1, 1):
        rbox(X, (.42, .02, .05), (0, -.18 + s * .19, .45), C(STEEL), .005, 1)
        rbox(X, (.02, .38, .05), (s * .21, -.18, .45), C(STEEL), .005, 1)
    sd_ground(X, (0, -.18, .445), .24, .2)
    for k, col in enumerate(("37A04A", "C0392B")):
        lathe(X, [(0, 0), (.018, 0), (.018, .015), (0, .02)], (.1 - k * .05, -.18, .2), C(col), 8, 0, rot=(90, 0, 0))
    T = sd_tray(X, (0, -.42, 0), .26, .18, 0, WHITE)
    sd_ground(T, (0, 0, .006), .2, .12)


def v4_sealer(acc, loc, yaw=0):
    """Seladora a vácuo: stainless chamber, domed clear lid on a hinge, a navy control strip with buttons."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.5, .45, .22), (0, 0, .11), INOX, .03, 2)
    lathe(X, [(.19, 0), (.19, .04), (.15, .08), (0, .09)], (0, .02, .22), GLASS, 18, 1, cap_bottom=False)
    rbox(X, (.42, .02, .08), (0, -.226, .11), C(NAVY), .01, 1)
    for k in range(4):
        rbox(X, (.03, .012, .03), (-.12 + k * .08, -.236, .11), C(WHITE if k else "37A04A"), .004, 1)
    rbox(X, (.3, .3, .02), (0, .02, .225), C("5A6066"), .005, 1)


def v4_label_scale(acc, loc, yaw=0):
    """Balança etiquetadora: white body, steel platter, a tower with a customer display and an operator touch screen,
    label slot with a label coming out (blank)."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.38, .45, .12), (0, 0, .06), C(WHITE), .03, 3)
    rbox(X, (.34, .3, .015), (0, -.05, .128), C(CHROME), .01, 2)
    rbox(X, (.3, .12, .2), (0, .17, .22), C(WHITE), .03, 3)
    rbox(X, (.08, .08, .25), (0, .17, .43), C("D8DCE0"), .02, 2)
    rbox(X, (.34, .06, .2), (0, .17, .62), C("2A2E36"), .02, 2, rot=(-15, 0, 0))
    rbox(X, (.29, .01, .15), (0, .135, .625), "E_DDF4FF", .005, 1, rot=(-15, 0, 0))
    rbox(X, (.22, .04, .05), (0, .23, .66), C("2A2E36"), .01, 1)
    rbox(X, (.18, .006, .03), (0, .253, .66), "E_FF4A3A", 0, 1)
    rbox(X, (.08, .004, .07), (.1, .107, .2), C(WHITE), .002, 1, rot=(-25, 0, 0))


def v4_worktable(acc, x, y, w, d=.6, h=.9, shelf=True):
    """Stainless worktable with an upstand at the back and an undershelf."""
    rbox(acc, (w, d, .04), (x, y, h - .02), INOX, .01, 2)
    rbox(acc, (w, .02, .1), (x, y + d / 2 - .01, h + .05), INOX, .005, 1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(acc, [(x + sx * (w / 2 - .04), y + sy * (d / 2 - .04), 0), (x + sx * (w / 2 - .04), y + sy * (d / 2 - .04), h - .04)], .02, C(STEEL), 8)
    if shelf:
        rbox(acc, (w - .06, d - .06, .02), (x, y, .2), INOX, .005, 1)


def v4_cold_door(acc, x, y, w=1.0, h=2.1):
    """Steel cold-room door: insulated frame, flush door panel with a porthole, a big lever handle, PVC strip curtain
    seen through the gap at the top, a small red light above."""
    rbox(acc, (w + .16, .14, h + .1), (x, y, (h + .1) / 2), C(STEEL), .02, 2)
    rbox(acc, (w, .08, h), (x, y - .06, h / 2), INOX, .02, 2)
    lathe(acc, [(0, 0), (.14, 0), (.14, .02), (0, .02)], (x - .1, y - .1, 1.45), C("2A2E36"), 18, 0, rot=(90, 0, 0))
    lathe(acc, [(0, 0), (.12, 0)], (x - .1, y - .121, 1.45), GLASS, 18, 0, rot=(90, 0, 0))
    rbox(acc, (.06, .08, .3), (x + w / 2 - .14, y - .14, 1.05), C(CHROME), .02, 2)
    tube(acc, [(x + w / 2 - .14, y - .18, 1.15), (x + w / 2 - .14, y - .26, 1.15), (x + w / 2 - .34, y - .26, 1.15)], .018, C(CHROME), 8, 1)
    rbox(acc, (w - .1, .012, .25), (x, y - .105, .14), C(CHROME), .004, 1)
    lathe(acc, [(0, 0), (.04, 0), (.04, .03), (0, .05)], (x, y - .08, h + .16), "E_FF4A3A", 10, 0, rot=(90, 0, 0))


def v4_hook_rail(acc, x0, x1, y, z, hooks=6, hang=()):
    """Stainless wall rail on brackets with S-hooks; `hang` lists what hangs on some hooks."""
    tube(acc, [(x0, y - .12, z), (x1, y - .12, z)], .016, C(CHROME), 8)
    for xx in (x0 + .05, (x0 + x1) / 2, x1 - .05):
        tube(acc, [(xx, y, z), (xx, y - .12, z)], .012, C(CHROME), 6)
    for k in range(hooks):
        hx = x0 + .15 + k * (x1 - x0 - .3) / max(1, hooks - 1)
        sd_s_hook(acc, hx, y - .12, z - .03)
        if k < len(hang) and hang[k]:
            if hang[k] == "sausage":
                sd_sausage_loop(acc, hx, y - .12, z - .06, .42, 6, .016)
            elif hang[k] == "ham":
                sd_ham(acc, hx, y - .12, z - .02, .9)


def v4_service_counter(acc, W, y, seed=0, H=.9, D=.95):
    """Balcão refrigerado de atendimento (Gelopar / Maqfrio style): stainless and navy base with a lower kick plate,
    a gold line and a ribbed stainless front band, a stainless customer ledge, tall curved front glass, glass top,
    lit canopy, white display deck of trays with cuts, price stakes in the meat and green dividers."""
    rbox(acc, (W, D, H - .05), (0, y, (H - .05) / 2), C(NAVY), .03, 3)
    rbox(acc, (W - .04, .02, .12), (0, y - D / 2 - .005, .06), INOX, .006, 1)
    rbox(acc, (W - .08, .012, .36), (0, y - D / 2 - .003, .52), INOX, .006, 1)
    n = int((W - .1) / .06)
    for k in range(n):
        rbox(acc, (.012, .006, .34), (-W / 2 + .07 + k * (W - .14) / (n - 1), y - D / 2 - .011, .52), C(STEEL), 0, 1)
    rbox(acc, (W - .1, .01, .01), (0, y - D / 2 - .012, .27), C(GOLD), .003, 1)
    rbox(acc, (W + .02, .2, .04), (0, y - D / 2 + .05, H + .02), INOX, .01, 2)
    # deck and trays
    X = Xf(acc, (0, y + .05, H + .02), (10, 0, 0))
    rbox(X, (W - .1, .55, .02), (0, 0, 0), C(WHITE), .005, 1)
    x = -W / 2 + .16
    k = seed
    kinds = ["steak", "tbone", "ribs", "ground", "chop", "sausage", "steak", "chicken", "tbone"]
    while x < W / 2 - .16:
        kind = kinds[k % len(kinds)]
        T = sd_tray(X, (x, 0, .012), .22, .46, 0, WHITE)
        if kind in ("steak", "tbone", "chop"):
            for j in range(3):
                (sd_tbone if kind == "tbone" else sd_steak)(T, (0, -.14 + j * .14, .006 + j * .002), .78, -8 + j * 8, *(() if kind == "tbone" else ("chop" if kind == "chop" else "steak",)), j + k)
        elif kind == "ribs":
            sd_ribs(T, (0, -.08, .006), .6, 90)
            sd_ribs(T, (0, .1, .006), .6, 90)
        elif kind == "ground":
            sd_ground(T, (0, 0, .006), .18, .38)
        elif kind == "sausage":
            for j in range(3):
                sd_sausages(T, rk_core.spline([(-.09, -.13 + j * .12, .02), (-.03, -.11 + j * .12, .022), (.03, -.12 + j * .12, .022), (.09, -.1 + j * .12, .02)], 2), 4, .016)
        else:
            for j in range(2):
                sd_chicken(T, (0, -.1 + j * .2, .006), .65, 90, "Body", True)
        sd_parsley(T, (.07, .18, .01), 2, k)
        sd_price_tag(T, (-.06, -.2, .07), (0, 0, 0))
        tube(X, [(x + .12, -.25, .025), (x + .12, .25, .025)], .008, C("3FA34D"), 4)
        x += .24
        k += 1
    # glass
    gy = y - D / 2 + .16
    bm = bmesh.new()
    prof = [(0, 0), (.04, .12), (.1, .26), (.18, .38), (.3, .47), (.42, .5)]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        bm.faces.new([bm.verts.new((-W / 2 + .03, gy + a[0], H + .04 + a[1])), bm.verts.new((W / 2 - .03, gy + a[0], H + .04 + a[1])),
                      bm.verts.new((W / 2 - .03, gy + b[0], H + .04 + b[1])), bm.verts.new((-W / 2 + .03, gy + b[0], H + .04 + b[1]))])
    uv_box(bm); acc.add(bm, GLASS)
    for s in (-1, 1):
        pts = [(gy + a, H + .04 + b) for a, b in prof] + [(y + D / 2 - .05, H + .54), (y + D / 2 - .05, H + .04)]
        sb = outline_bm(pts, .02)
        place(sb, (s * (W / 2 - .01) - .01, 0, 0), (90, 0, 90)); acc.add(sb, C(NAVY))
    rbox(acc, (W - .04, .3, .03), (0, y + D / 2 - .2, H + .55), INOX, .008, 1)
    rbox(acc, (W - .1, .02, .012), (0, y + D / 2 - .25, H + .535), LED_W, .003, 1)
    rbox(acc, (W - .04, .3, .015), (0, y + D / 2 - .2, H + .25), GLASS, .003, 1)
    # staff side: sliding doors and a cutting ledge
    rbox(acc, (W - .06, .02, .3), (0, y + D / 2 + .005, .55), INOX, .006, 1)
    rbox(acc, (W - .04, .25, .03), (0, y + D / 2 - .1, H + .01), C(WHITE), .006, 1)


def v4_pack(acc, loc, kind="steak", yaw=0, foam="F4F2EC", seed=0):
    """Film-wrapped foam tray with a cut and a blank label (self-service)."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.22, .15, .025), (0, 0, .0125), C(foam), .008, 1)
    if kind == "steak":
        sd_steak(X, (0, 0, .015), .8, 0, "steak", seed)
    elif kind == "chop":
        sd_steak(X, (0, 0, .015), .75, 10, "chop", seed)
    elif kind == "ground":
        sd_ground(X, (0, 0, .012), .16, .1)
    elif kind == "sausage":
        for j in range(2):
            sd_sausages(X, [(-.08, -.03 + j * .05, .03), (0, -.025 + j * .05, .032), (.08, -.03 + j * .05, .03)], 3, .014)
    else:
        sd_tbone(X, (0, 0, .015), .8, 0, seed)
    rbox(X, (.225, .155, .004), (0, 0, .05), GLASS, .002, 1)
    rbox(X, (.07, .045, .002), (.05, -.03, .053), C(WHITE), 0, 1)
    rbox(X, (.07, .008, .0022), (.05, -.012, .0535), C(NAVY), 0, 1)


def v4_selfservice(acc, x, y, W=1.25, D=.75, H=1.95, seed=0):
    """Open refrigerated self-service cabinet (vertical multideck): navy body, stainless shelves with blank price
    strips, LED canopy, air-curtain grille, foam trays of cuts in film."""
    rbox(acc, (W, D, .45), (x, y, .225), C(NAVY), .03, 3)
    rbox(acc, (W - .04, .02, .1), (x, y - D / 2 - .002, .07), INOX, .006, 1)
    rbox(acc, (W - .1, .01, .01), (x, y - D / 2 - .006, .38), C(GOLD), .003, 1)
    for s in (-1, 1):
        rbox(acc, (.05, D, H - .45), (x + s * (W / 2 - .025), y, .45 + (H - .45) / 2), C(NAVY), .02, 2)
    rbox(acc, (W - .1, .06, H - .45), (x, y + D / 2 - .03, .45 + (H - .45) / 2), C(WHITE), .01, 1)
    rbox(acc, (W, D * .55, .18), (x, y + D * .2, H - .09), C(NAVY), .03, 3)
    rbox(acc, (W - .12, .02, .02), (x, y - D * .07, H - .19), LED_W, .004, 1)
    rbox(acc, (W - .06, .06, .02), (x, y - D / 2 + .08, .47), C(STEEL), .006, 1)
    kinds = ["steak", "chop", "ground", "sausage", "tbone"]
    rnd = random.Random(seed)
    for i, z in enumerate((.5, .82, 1.12, 1.42)):
        sd_ = D - .1 - i * .06
        sx_ = Xf(acc, (x, y + .05 + i * .03, z), (-8, 0, 0))
        rbox(sx_, (W - .12, sd_, .02), (0, 0, 0), INOX, .005, 1)
        rbox(sx_, (W - .12, .01, .035), (0, -sd_ / 2, .015), C(WHITE), 0, 1)
        n = int((W - .12) / .24)
        for c in range(n):
            for r_ in range(2 if sd_ > .5 else 1):
                v4_pack(sx_, (-(W - .12) / 2 + .12 + c * .24, -sd_ / 2 + .12 + r_ * .2, .012), kinds[(i + c + r_ + seed) % 5], 0, ["F4F2EC", "2E4A7D", "F4F2EC"][(c + r_) % 3], c + i)


def v4_led_bar(acc, x, y, z, w):
    rbox(acc, (w, .08, .04), (x, y, z), C(WHITE), .01, 1)
    rbox(acc, (w - .04, .05, .006), (x, y, z - .022), LED_W, .002, 1)


def v4_testeira(acc, W, yb, H, h=.42, depth=.55):
    """Navy testeira: a bulkhead/soffit along the top of the section's back wall, its front face with a gold line
    and a blank cream name panel (the game writes the sector name), LED lines underneath lighting the counter area."""
    y0 = yb - .06
    rbox(acc, (W, depth, h), (0, y0 - depth / 2, H - h / 2), C(NAVY), .03, 3)
    rbox(acc, (W + .01, .012, .014), (0, y0 - depth - .002, H - h + .07), C(GOLD), .003, 1)
    plate(acc, W * .42, h * .62, (0, y0 - depth - .012, H - h * .45), C(CREAM), .02, h * .2)
    for k in range(2):
        rbox(acc, (W - .1, .03, .012), (0, y0 - .15 - k * .25, H - h - .006), LED_W, .003, 1)


def v4_hanging_sign(acc, x, y, z, w=.9, h=.28):
    """Blank navy sign on two cords over the counter (the game writes the sector name)."""
    plate(acc, w, h, (x, y, z), C(NAVY), .03, h * .3)
    plate(acc, w * .82, h * .62, (x, y - .016, z), C(CREAM), .008, h * .2)
    rbox(acc, (w * .9, .006, .01), (x, y - .017, z - h * .4), C(GOLD), .002, 1)
    for sx in (-1, 1):
        tube(acc, [(x + sx * w * .4, y, z + h / 2), (x + sx * w * .4, y, z + h / 2 + .45)], .003, C(INK), 4)


def v4_tile_wall(acc, W, y, H, wains=True):
    """White tiled wall with a stainless backsplash band and a navy skirting (supermarket section)."""
    rbox(acc, (W, .12, H), (0, y, H / 2), TILE_W, .02, 2, uv=1.5)
    if wains:
        rbox(acc, (W + .01, .13, 1.0), (0, y - .01, .5), C(NAVY), .015, 2)
        rbox(acc, (W + .02, .01, .012), (0, y - .08, 1.0), C(GOLD), .003, 1)
    rbox(acc, (W + .04, .16, .08), (0, y - .02, H + .04), C(NAVY), .03, 3)


# ================================================================================================ AÇOUGUE (round 4)
def acougue_v4(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    v4_tile_wall(acc, W, yb, H)
    if tier == 1:
        # canto de atendimento: a 1.75 m service counter, grinder + label scale on a stainless table, hook rail
        v4_service_counter(acc, 1.75, -D / 2 + .55, 0)
        v4_worktable(acc, -.3, yb - .38, 1.3, .6)
        v4_grinder(acc, (-.65, yb - .4, .9), 0)
        v4_label_scale(acc, (-.05, yb - .38, .9), 0)
        rbox(acc, (.25, .3, .02), (.2, yb - .38, .91), "T_IK_ButcherBlock", .006, 1, uv=3)
        sd_knife(acc, (.17, yb - .42, .925), (0, 0, 10), .2, "cleaver")
        v4_hook_rail(acc, -W / 2 + .2, W / 2 - .2, yb - .07, 1.95, 5, ("ham", "sausage", None, "sausage", "ham"))
        sd_knife_strip(acc, .75, yb - .075, 1.45, 4, .5)
        rbox(acc, (.6, .45, .9), (W / 2 - .38, yb - .3, .45), INOX, .02, 2)
        sd_paper_roll(acc, (W / 2 - .38, yb - .32, .9), 0, .45, "F4F2EC")
        name_board(acc, 0, yb - .08, H - .15, 1.0)
    elif tier == 2:
        # açougue: full counter, band saw, grinder, sealer, label scale, cold-room door, 2 price panels,
        # ticket dispenser in front + number display over the door, hanging name sign
        cy = -D / 2 + .75
        v4_service_counter(acc, 2.75, cy, 1)
        v4_bandsaw(acc, (-1.2, yb - .42, 0), 0)
        v4_worktable(acc, -.1, yb - .38, 1.4, .6)
        v4_grinder(acc, (-.5, yb - .4, .9), 0)
        v4_sealer(acc, (.05, yb - .36, .9), 0)
        v4_label_scale(acc, (.42, yb - .38, .9), 0)
        v4_cold_door(acc, 1.1, yb - .02, .85, 2.05)
        v4_hook_rail(acc, -.85, .55, yb - .07, 1.62, 5, ("sausage", None, "ham", None, "sausage"))
        for k, px_ in enumerate((-.45, .45)):
            v4_price_panel(acc, px_, yb - .075, 2.42, .85, k)
        v4_ticket_display(acc, 1.1, yb - .075, 2.45)
        v4_ticket_dispenser(acc, (1.2, -D / 2 + .13, 0), -20)
        v4_hanging_sign(acc, -.8, cy, 2.3, .9, .28)
    else:
        # açougue completo: navy testeira over the counter (gold line, blank name panel), 3-panel price wall,
        # counter + self-service cooler of packed trays, band saw, two grinders, sealer, label scale, cold-room
        # door, hook rail, ticket dispenser + number display, bright LED lines
        cy = -D / 2 + .75
        Xc = Xf(acc, (-.62, 0, 0))
        v4_service_counter(Xc, 2.65, cy, 2)
        v4_selfservice(acc, W / 2 - .66, -D / 2 + .42, 1.25, .78, 1.95, 1)
        v4_testeira(acc, W, yb, H + .04, .42, .55)
        v4_bandsaw(acc, (-1.6, yb - .42, 0), 0)
        v4_worktable(acc, -.65, yb - .38, 1.4, .6)
        v4_grinder(acc, (-1.15, yb - .4, .9), 0)
        v4_grinder(acc, (-.78, yb - .4, .9), 0)
        v4_sealer(acc, (-.22, yb - .36, .9), 0)
        v4_worktable(acc, .55, yb - .38, .7, .6)
        v4_label_scale(acc, (.45, yb - .38, .9), 0)
        sd_paper_roll(acc, (.8, yb - .3, .92), 90, .3, "F4F2EC")
        v4_cold_door(acc, 1.5, yb - .02, .8, 2.05)
        v4_hook_rail(acc, -1.35, .1, yb - .07, 1.62, 5, ("ham", "sausage", None, "ham", "sausage"))
        for k, px_ in enumerate((-.95, -.12, .71)):
            v4_price_panel(acc, px_, yb - .075, 2.2, .8, k)
        v4_ticket_display(acc, 1.5, yb - .075, 2.38)
        v4_ticket_dispenser(acc, (-1.7, -D / 2 + .13, 0), 20)
        sd_knife_strip(acc, .55, yb - .075, 1.45, 3, .4)


# keep the old sector layouts for the others until Lucas approves the açougue direction
BUILDERS["sector-acougue"] = make_sector_v2("acougue", acougue_v4)
SECTOR_TIER_NAMES["acougue"] = ("balcão de atendimento", "açougue", "açougue completo")
TIERS["sector-acougue"] = [("T%d" % (i + 1), "Açougue: %s" % SECTOR_TIER_NAMES["acougue"][i], w, d, h) for i, (w, d, h) in enumerate(SECTOR_SIZES)]


def v4_rebuild(sid):
    v4_materials()
    kind = "sector-" + sid
    tris = rebuild(kind)
    out = sheet(kind)
    out.append(sector_topdown(sid, 3))
    return tris, out
