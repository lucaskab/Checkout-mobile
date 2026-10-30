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


SCREEN_SLOTS = ("E_PriceScreen", "E_TicketScreen")


def v4_materials(sid="acougue"):
    """One material per screen slot. For the renders the price slot shows this sector's preview board image
    (three boards stacked, the screens pick one by UV); the export blanks both (fixture_tiers.export_tier)."""
    sd_material()
    v4_screen_material("E_PriceScreen", "FT_PricePreview_%s.png" % sid)
    v4_screen_material("E_TicketScreen", "FT_TicketPreview.png")
    for old in ("E_PriceScreen.0", "E_PriceScreen.1", "E_PriceScreen.2"):
        m = bpy.data.materials.get(old)
        if m:
            bpy.data.materials.remove(m)
    m = material(LED_W)
    m.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = 5.0


def screen_quad(acc, w, h, loc, key, rot=(0, 0, 0), v0=0.0, v1=1.0):
    """Flat screen facing -Y; UV u 0..1, v from v0 to v1 (the game can draw into the whole 0..1 square)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new((x * w / 2, 0, z * h / 2)) for x, z in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)                                # CCW seen from -Y: the quad faces the customer side
    for l in f.loops:
        l[uvl].uv = ((l.vert.co.x / w) + .5, v0 + ((l.vert.co.z / h) + .5) * (v1 - v0))
    place(bm, loc, rot)
    acc.add(bm, key)


# ================================================================================================ machines
def v4_price_panel(acc, x, y, z, w=1.0, variant=0, rot=(0, 0, 0)):
    """Digital price board (a 16:9 TV in a black bezel on a wall bracket)."""
    X = Xf(acc, (x, y, z), rot)
    h = w * 9 / 16
    rbox(X, (w + .05, .05, h + .05), (0, .025, 0), C("1B1E24"), .012, 2)
    v = variant % 3                                     # preview sheet: board 0 at the top
    screen_quad(X, w, h, (0, -.002, 0), "E_PriceScreen", (0, 0, 0), 1 - (v + 1) / 3, 1 - v / 3)
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


def v4_counter_shell(acc, W, y, H=.9, D=.95, gs=1.0, shelf=True, deck_col=WHITE, tilt=10):
    """Balcão refrigerado de atendimento (Gelopar / Maqfrio style) without its products: stainless and navy base
    with a kick plate, a ribbed stainless front band and a gold line, stainless customer ledge, curved front glass
    (gs scales its height), lit canopy, optional glass mid shelf, staff-side doors and a white cutting ledge.
    Returns the tilted display-deck frame (deck top at z = 0) for the products."""
    rbox(acc, (W, D, H - .05), (0, y, (H - .05) / 2), C(NAVY), .03, 3)
    rbox(acc, (W - .04, .02, .12), (0, y - D / 2 - .005, .06), INOX, .006, 1)
    rbox(acc, (W - .08, .012, .36), (0, y - D / 2 - .003, .52), INOX, .006, 1)
    n = int((W - .1) / .06)
    for k in range(n):
        rbox(acc, (.012, .006, .34), (-W / 2 + .07 + k * (W - .14) / (n - 1), y - D / 2 - .011, .52), C(STEEL), 0, 1)
    rbox(acc, (W - .1, .01, .01), (0, y - D / 2 - .012, .27), C(GOLD), .003, 1)
    rbox(acc, (W + .02, .2, .04), (0, y - D / 2 + .05, H + .02), INOX, .01, 2)
    X = Xf(acc, (0, y + .05, H + .02), (tilt, 0, 0))
    rbox(X, (W - .1, .55, .02), (0, 0, 0), C(deck_col), .005, 1)
    gy = y - D / 2 + .16
    bm = bmesh.new()
    prof = [(0, 0), (.04, .12 * gs), (.1, .26 * gs), (.18, .38 * gs), (.3, .47 * gs), (.42, .5 * gs)]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        bm.faces.new([bm.verts.new((-W / 2 + .03, gy + a[0], H + .04 + a[1])), bm.verts.new((W / 2 - .03, gy + a[0], H + .04 + a[1])),
                      bm.verts.new((W / 2 - .03, gy + b[0], H + .04 + b[1])), bm.verts.new((-W / 2 + .03, gy + b[0], H + .04 + b[1]))])
    uv_box(bm); acc.add(bm, GLASS)
    top = H + .04 + .5 * gs
    for s_ in (-1, 1):
        pts = [(gy + a, H + .04 + b) for a, b in prof] + [(y + D / 2 - .05, top), (y + D / 2 - .05, H + .04)]
        sb = outline_bm(pts, .02)
        place(sb, (s_ * (W / 2 - .01) - .01, 0, 0), (90, 0, 90)); acc.add(sb, C(NAVY))
    rbox(acc, (W - .04, .3, .03), (0, y + D / 2 - .2, top + .01), INOX, .008, 1)
    rbox(acc, (W - .1, .02, .012), (0, y + D / 2 - .25, top - .005), LED_W, .003, 1)
    if shelf:
        rbox(acc, (W - .04, .3, .015), (0, y + D / 2 - .2, H + .04 + .21 * gs), GLASS, .003, 1)
    rbox(acc, (W - .06, .02, .3), (0, y + D / 2 + .005, .55), INOX, .006, 1)
    rbox(acc, (W - .04, .25, .03), (0, y + D / 2 - .1, H + .01), C(WHITE), .006, 1)
    return X


def v4_meat_slot(X, x, k):
    kinds = ["steak", "tbone", "ribs", "ground", "chop", "sausage", "steak", "chicken", "tbone"]
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


def v4_service_counter(acc, W, y, seed=0, H=.9, D=.95, fill=None, step=.24, gs=1.0, shelf=True):
    """Service counter shell + one product slot every `step` metres (fill(X, x, k); meat by default)."""
    X = v4_counter_shell(acc, W, y, H, D, gs, shelf)
    fill = fill or v4_meat_slot
    x = -W / 2 + .06 + step / 2
    k = seed
    while x < W / 2 - step / 2:
        fill(X, x, k)
        x += step
        k += 1
    return X


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
    for k in range(max(1, int(depth / .25))):
        rbox(acc, (W - .1, .03, .012), (0, y0 - depth / 2 - k * .25, H - h - .006), LED_W, .003, 1)


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
        v4_testeira(acc, W, yb, H + .04, .34, .2)     # slim: the T3 price boards read from the game camera
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
            v4_price_panel(acc, px_, yb - .075, 2.17, .8, k)
        v4_ticket_display(acc, 1.5, yb - .075, 2.3)
        v4_ticket_dispenser(acc, (-1.7, -D / 2 + .13, 0), 20)
        sd_knife_strip(acc, .55, yb - .075, 1.45, 3, .4)


BUILDERS["sector-acougue"] = make_sector_v2("acougue", acougue_v4)
SECTOR_TIER_NAMES["acougue"] = ("balcão de atendimento", "açougue", "açougue completo")


def v4_gamecam(sid, tier=3, elev=50, yaw=-20):
    """Check from the game's iso camera: orthographic, from the customer side, looking down."""
    o = bpy.data.objects["sector-%s-t%d" % (sid, tier)]
    isolate(BASE_Y["sector-" + sid], 3.4)
    w, d, h = SECTOR_SIZES[tier - 1]
    e, a = math.radians(elev), math.radians(yaw)
    camera((o.location.x, o.location.y + .2, 1.3), (math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)), 30, 40, ortho=w * 1.5)
    return render("sector-%s_T%d_gamecam" % (sid, tier), (1400, 1100))


def v4_rebuild(sid):
    v4_materials(sid)
    kind = "sector-" + sid
    tris = rebuild(kind)
    out = sheet(kind)
    out.append(sector_topdown(sid, 3))
    return tris, out


# ================================================================================================ shared round 4 pieces
def v4_glass_cabinet(acc, x, y, W=1.0, D=.7, H=1.95, fill=None, doors=True, body=NAVY, shelves=4):
    """Refrigerated vertical display (glass doors, LED canopy, stainless shelves with blank price strips);
    fill(X, i, w, d) puts the products of shelf i (X at the shelf top)."""
    rbox(acc, (W, D, .4), (x, y, .2), C(body), .03, 3)
    rbox(acc, (W - .1, .01, .01), (x, y - D / 2 - .004, .34), C(GOLD), .003, 1)
    for s_ in (-1, 1):
        rbox(acc, (.05, D, H - .4), (x + s_ * (W / 2 - .025), y, .4 + (H - .4) / 2), C(body), .02, 2)
    rbox(acc, (W - .1, .04, H - .4), (x, y + D / 2 - .02, .4 + (H - .4) / 2), C(WHITE), .01, 1)
    rbox(acc, (W, D, .16), (x, y, H - .08), C(body), .03, 3)
    rbox(acc, (W - .12, .02, .02), (x, y - D / 2 + .1, H - .17), LED_W, .004, 1)
    step = (H - .62) / shelves
    for i in range(shelves):
        z = .44 + i * step
        rbox(acc, (W - .1, D - .12, .02), (x, y + .02, z), INOX, .004, 1)
        rbox(acc, (W - .1, .008, .03), (x, y - D / 2 + .05, z + .01), C(WHITE), 0, 1)
        if fill:
            fill(Xf(acc, (x, y + .02, z + .01)), i, W - .14, D - .16)
    if doors:
        n = 2 if W > .8 else 1
        for k in range(n):
            dx = x - W / 2 + (k + .5) * W / n
            rbox(acc, (W / n - .02, .02, H - .62), (dx, y - D / 2 + .01, .41 + (H - .62) / 2), GLASS, .004, 1)
            fr = frame_bm(W / n - .02, H - .62, .025, .01, .03)
            place(fr, (dx, y - D / 2 + .005, .41 + (H - .62) / 2)); acc.add(fr, C("1B1E24"))
            rbox(acc, (.02, .03, .5), (dx + (W / n / 2 - .06) * (1 if k else -1) * -1, y - D / 2 - .015, 1.15), C(CHROME), .008, 1)


def v4_chest_freezer(acc, x, y, W=1.6, D=.8, H=.85, contents="fish", seed=0):
    """Chest freezer (white body, navy band, sliding glass lids) with packed frozen goods visible."""
    rbox(acc, (W, D, H - .3), (x, y, (H - .3) / 2), C(WHITE), .04, 3)
    open_box(acc, W, D, .3, (x, y, H - .3), C(WHITE), .05, .02, 1)
    rbox(acc, (W + .005, D + .005, .14), (x, y, .18), C(NAVY), .02, 2)
    rbox(acc, (W - .1, .01, .01), (x, y - D / 2 - .004, .27), C(GOLD), .003, 1)
    rbox(acc, (W - .1, D - .1, .02), (x, y, H - .29), C("DDE8EE"), 0, 1)
    rnd = random.Random(seed)
    nx, ny = int((W - .14) / .2), int((D - .14) / .16)
    for i in range(nx):
        for j in range(ny):
            px_ = x - (W - .14) / 2 + (i + .5) * (W - .14) / nx
            py = y - (D - .14) / 2 + (j + .5) * (D - .14) / ny
            if contents == "fish":
                rbox(acc, (.18, .13, .05), (px_, py, H - .21 + .02 * ((i + j) % 2)), C(["3E8FD6", "2E4A7D", "F4F2EC"][(i + j + seed) % 3]), .015, 1, rot=(0, 0, rnd.uniform(-8, 8)))
                rbox(acc, (.07, .05, .002), (px_ + .03, py - .02, H - .18 + .02 * ((i + j) % 2)), C(WHITE), 0, 1)
            else:                                   # ice-cream tubs
                lathe(acc, [(0, 0), (.06, 0), (.07, .1)], (px_, py, H - .24), C(WHITE), 10, 0, cap_top=False)
                lathe(acc, [(0, 0), (.073, 0), (.073, .012), (0, .012)], (px_, py, H - .14), C(["E8505B", "3E8FD6", "F2C23F", "7A4A2E", "5FB548"][(i * 3 + j + seed) % 5]), 10, 0)
    for k in range(2):
        rbox(acc, (W / 2 - .02, D - .04, .015), (x - W / 4 + k * W / 2, y, H + .01 + k * .016), GLASS, .004, 1)
    rbox(acc, (W - .04, .03, .03), (x, y - D / 2 + .02, H + .03), C(CHROME), .008, 1)


def v4_sign_tag(acc, x, y, z):
    """Small blank promo/price sign on a chrome stem (stuck in a display)."""
    tube(acc, [(x, y, z), (x, y, z + .18)], .004, C(CHROME), 4)
    plate(acc, .16, .1, (x, y, z + .23), C(NAVY), .008, .02)
    plate(acc, .13, .07, (x, y - .005, z + .23), C(CREAM), .003, .015)


def v4_section(acc, tier, W, D, H, yb, panels=(), ticket=None, display=None, sign=None):
    """Shared top dressing: T1 name board, T2 hanging sign, T3 testeira; price panels on the wall; ticket dispenser
    in front of the counter and the number display."""
    for k, (px_, pz, pw) in enumerate(panels):
        v4_price_panel(acc, px_, yb - .075, pz, pw, k)
    if display:
        v4_ticket_display(acc, display[0], yb - .075, display[1])
    if ticket:
        v4_ticket_dispenser(acc, (ticket[0], -D / 2 + .13, 0), ticket[1])
    if tier == 1:
        name_board(acc, sign[0] if sign else 0, yb - .08, H - .15, 1.0)
    elif tier == 2:
        v4_hanging_sign(acc, sign[0] if sign else -.8, sign[1] if sign else -D / 2 + .75, 2.3, .9, .28)
    else:
        v4_testeira(acc, W, yb, H + .04, .34, .2)     # slim: the T3 price boards read from the game camera


# ================================================================================================ PADARIA (round 4)
def v4_rack_oven(acc, loc, yaw=0):
    """Forno turbo / rack oven: stainless cabinet, a lit glass door showing trays of rolls inside, a control
    column with a screen and knobs, steam hood and duct on top."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (1.0, 1.0, 2.0), (0, 0, 1.0), INOX, .04, 3)
    fr = frame_bm(.66, 1.5, .03, .03, .05); place(fr, (-.12, -.505, 1.0)); X.add(fr, C("1B1E24"))
    rbox(X, (.58, .02, 1.42), (-.12, -.51, 1.0), GLASS, .01, 1)
    rbox(X, (.56, .02, 1.38), (-.12, -.36, 1.0), "E_FFB25A", .01, 1)
    for k in range(3):
        z = .5 + k * .42
        rbox(X, (.5, .4, .015), (-.12, -.2, z), C(STEEL), .003, 1)
        for j in range(3):
            sd_roll(X, (-.3 + j * .17, -.25, z + .008), .04, k * 3 + j)
    rbox(X, (.03, .05, .7), (.25, -.54, 1.05), C(CHROME), .01, 1)
    rbox(X, (.22, .02, .6), (.37, -.505, 1.45), C(NAVY), .02, 2)
    rbox(X, (.15, .01, .1), (.37, -.517, 1.62), "E_DDF4FF", .004, 1)
    for k in range(3):
        lathe(X, [(0, 0), (.025, 0), (.025, .02), (0, .025)], (.37, -.515, 1.42 - k * .1), C(INK), 10, 0, rot=(90, 0, 0))
    rbox(X, (1.1, 1.1, .2), (0, -.05, 2.1), INOX, .04, 2)
    lathe(X, [(.1, 0), (.1, .4)], (.25, .2, 2.2), C(STEEL), 12, 0, cap_top=False, cap_bottom=False)
    for sx in (-1, 1):
        lathe(X, [(0, 0), (.03, 0), (.03, .05), (0, .05)], (sx * .4, -.4, 0), C(INK), 8, 0)


def v4_proofer(acc, loc, yaw=0):
    """Câmara de fermentação: stainless cabinet with a glass door and trays of shaped dough."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.7, .8, 1.9), (0, 0, .95), INOX, .04, 3)
    rbox(X, (.6, .02, 1.6), (0, -.405, 1.0), GLASS, .008, 1)
    rbox(X, (.58, .02, 1.56), (0, -.3, 1.0), "E_FFF0D8", .01, 1)
    for k in range(5):
        z = .3 + k * .3
        rbox(X, (.56, .5, .012), (0, -.12, z), C(STEEL), .003, 1)
        for j in range(3):
            blob(X, (.05, .04, .025), (-.18 + j * .18, -.2, z + .02), C("F2E2C0"), 1, .05, k + j)
    rbox(X, (.03, .04, .5), (.27, -.43, 1.05), C(CHROME), .01, 1)
    rbox(X, (.5, .02, .1), (0, -.405, 1.83), C(NAVY), .01, 1)
    rbox(X, (.1, .01, .05), (.15, -.418, 1.83), "E_FF4A3A", 0, 1)


def v4_rack_trolley(acc, loc, yaw=0, trays=6, kind="roll"):
    """Esqueleto: a wheeled steel rack of baking trays."""
    X = Xf(acc, loc, (0, 0, yaw))
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(X, [(sx * .3, sy * .22, .06), (sx * .3, sy * .22, 1.7)], .014, C(CHROME), 6)
            lathe(X, [(0, 0), (.03, 0), (.03, .025), (0, .025)], (sx * .3, sy * .22, .03), C(INK), 8, 0, rot=(90, 0, 0))
    for sx in (-1, 1):
        tube(X, [(sx * .3, -.22, 1.7), (sx * .3, .22, 1.7)], .012, C(CHROME), 6)
    for k in range(trays):
        z = .2 + k * (1.4 / trays)
        rbox(X, (.6, .42, .012), (0, 0, z), C(STEEL), .003, 1)
        if k % 2 == 0 or trays < 5:
            for j in range(4):
                if kind == "roll":
                    sd_roll(X, (-.22 + j * .15, 0, z + .007), .04, k + j)
                else:
                    sd_baguette(X, (0, -.15 + j * .1, z + .03), .5, .025, 0, 0, k + j)


def v4_bread_slicer(acc, loc, yaw=0):
    """Fatiadora de pão: stainless body on legs, angled feed chute with a loaf, clear front guard, sliced loaf
    coming out onto a tray, buttons."""
    X = Xf(acc, loc, (0, 0, yaw))
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(X, [(sx * .22, sy * .22, 0), (sx * .22, sy * .22, .5)], .016, C(STEEL), 6)
    rbox(X, (.55, .55, .45), (0, 0, .72), INOX, .04, 3)
    Xc = Xf(X, (0, .08, .97), (-35, 0, 0))
    open_box(Xc, .4, .3, .22, (0, 0, 0), INOX, .01, 0, 2)
    sd_loaf(Xc, (0, 0, .02), .3, .12, .1, 0, "loaf", 3)
    rbox(X, (.42, .02, .2), (0, -.28, .86), GLASS, .004, 1)
    rbox(X, (.4, .22, .02), (0, -.37, .5), C(STEEL), .004, 1)
    for k in range(7):
        rbox(X, (.012, .1, .085), (-.06 + k * .02, -.37, .55), C("F0DEB0"), 0, 1)
        rbox(X, (.013, .101, .012), (-.06 + k * .02, -.37, .6), C("B4692E"), 0, 1)
    for k, col in enumerate(("37A04A", "C0392B")):
        lathe(X, [(0, 0), (.02, 0), (.02, .015), (0, .02)], (.2, -.276, .82 - k * .07), C(col), 8, 0, rot=(90, 0, 0))


def v4_bread_bin(acc, loc, w=.9, d=.6, yaw=0, seed=0):
    """Cesto de pão francês: a tilted wicker bin on a navy stand heaped with rolls, tongs on the rim and a
    paper-bag dispenser beside it."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (w, d, .7), (0, 0, .35), C(NAVY), .03, 3)
    rbox(X, (w - .1, .01, .01), (0, -d / 2 - .004, .6), C(GOLD), .003, 1)
    B = Xf(X, (0, 0, .72), (14, 0, 0))
    open_box(B, w - .04, d - .04, .14, (0, 0, 0), WICKER, .02, .008, 3)
    blob(B, (w * .44, d * .4, .06), (0, 0, .06), C("C08040"), 2, .1, seed)
    rnd = random.Random(seed)
    nx, ny = int((w - .1) / .12), int((d - .1) / .12)
    for i in range(nx):
        for j in range(ny):
            sd_roll(B, (-(w - .1) / 2 + (i + .5) * (w - .1) / nx + rnd.uniform(-.01, .01), -(d - .1) / 2 + (j + .5) * (d - .1) / ny, .07 + .02 * math.sin(i + j)), .04, i * 7 + j)
    tube(B, [(w / 2 - .05, -d / 2 + .02, .14), (w / 2 - .25, -d / 2 + .06, .2)], .006, C(CHROME), 5)
    tube(B, [(w / 2 - .05, -d / 2 + .04, .14), (w / 2 - .25, -d / 2 + .1, .2)], .006, C(CHROME), 5)
    tube(X, [(0, d / 2 - .02, .7), (0, d / 2 - .02, 1.3)], .012, C(CHROME), 6)
    rbox(X, (.26, .08, .36), (0, d / 2 - .02, 1.1), C("C9A06A"), .006, 1)
    rbox(X, (.27, .09, .05), (0, d / 2 - .02, .95), C(CHROME), .006, 1)


def v4_estufa(acc, loc, w=1.0, yaw=0):
    """Estufa de salgados: heated glass display with warm light and two shelves of coxinhas, esfihas and pão de
    queijo."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (w, .5, .06), (0, 0, .03), INOX, .01, 2)
    rbox(X, (w, .5, .05), (0, 0, .58), INOX, .01, 2)
    for sx in (-1, 1):
        rbox(X, (.03, .5, .5), (sx * (w / 2 - .015), 0, .31), INOX, .006, 1)
    rbox(X, (w - .06, .01, .5), (0, -.245, .31), GLASS, .003, 1)
    rbox(X, (w - .1, .02, .012), (0, .1, .545), "E_FFB25A", .003, 1)
    for z in (.07, .3):
        rbox(X, (w - .08, .44, .01), (0, 0, z), C(STEEL), .003, 1)
        n = int((w - .12) / .1)
        for k in range(n):
            px_ = -(w - .12) / 2 + (k + .5) * (w - .12) / n
            for j in range(2):
                py = -.1 + j * .18
                if (k + j) % 3 == 0:
                    lathe(X, [(0, 0), (.028, .005), (.03, .025), (.015, .06), (0, .07)], (px_, py, z + .005), C("D8902E"), 7, 0)
                elif (k + j) % 3 == 1:
                    bm = outline_bm([(0, .04), (-.035, -.025), (.035, -.025)], .02)
                    uv_box(bm); place(bm, (px_, py, z + .005), (0, 0, k * 30)); X.add(bm, C("D8A050"))
                else:
                    for q in range(2):
                        blob(X, (.02, .02, .017), (px_ - .02 + q * .04, py, z + .02), C("E8C060"), 1, .05, q)


def v4_estufa_unit(acc, x, y, w=.65):
    """A navy base cabinet carrying the hot savoury display (estufa) at the end of the bread counter."""
    rbox(acc, (w, .9, .9), (x, y, .45), C(NAVY), .03, 3)
    rbox(acc, (w - .06, .02, .12), (x, y - .455, .06), INOX, .006, 1)
    rbox(acc, (w - .08, .01, .01), (x, y - .456, .27), C(GOLD), .003, 1)
    rbox(acc, (w + .02, .92, .04), (x, y, .92), INOX, .01, 2)
    v4_estufa(acc, (x, y - .12, .94), w - .04)


def v4_bread_fill(X, x, k):
    T = sd_tray(X, (x, 0, .012), .22, .46, 0, WHITE)
    m = k % 5
    if m == 0:
        for j in range(4):
            sd_roll(T, (-.04 + (j % 2) * .08, -.14 + (j // 2) * .14, .006), .04, j + k)
    elif m == 1:
        for j in range(3):
            sd_croissant(T, (0, -.14 + j * .14, .006), .8, 90)
    elif m == 2:
        sd_cake(T, (0, -.08, .006), .09, .07, ["straw", "choc", "cream"][k % 3])
        sd_roll(T, (0, .14, .006), .045, k)
    elif m == 3:
        for j in range(2):
            sd_loaf(T, (0, -.1 + j * .2, .006), .2, .1, .08, 90, "loaf", j + k)
    else:
        for j in range(6):
            blob(T, (.02, .02, .017), (-.05 + (j % 2) * .1, -.15 + (j // 2) * .14, .025), C("E8C060"), 1, .05, j)
    sd_price_tag(T, (-.06, -.2, .07), (0, 0, 0))


def v4_cakes_fill(X, i, w, d):
    n = max(1, int(w / .3))
    for k in range(n):
        px_ = -w / 2 + (k + .5) * w / n
        if i % 2 == 0:
            sd_cake(X, (px_, -.02, .005), .1, .08, ["straw", "choc", "cream"][(i + k) % 3])
        else:
            T = sd_tray(X, (px_, -.02, .005), .26, .3, 0, WHITE)
            for j in range(3):
                lathe(T, [(0, 0), (.03, 0), (.032, .035), (0, .04)], (-.07 + j * .07, 0, .006), C(["7A4A2E", "F4A6C1", "F6E7C8"][(j + k) % 3]), 8, 0)


def padaria_v4(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    v4_tile_wall(acc, W, yb, H)
    if tier == 1:
        v4_service_counter(acc, 1.5, -D / 2 + .55, 0, fill=v4_bread_fill)
        v4_bread_bin(acc, (W / 2 - .35, -D / 2 + .45, 0), .5, .6, 0, 1)
        v4_rack_oven(acc, (-W / 2 + .62, yb - .58, 0), 0)
        v4_worktable(acc, .5, yb - .38, 1.0, .6)
        v4_label_scale(acc, (.3, yb - .38, .9), 0)
        sd_bread_bag(acc, (.75, yb - .4, .9), 0)
        v4_section(acc, 1, W, D, H, yb, sign=(.45,))
    elif tier == 2:
        cy = -D / 2 + .75
        v4_service_counter(Xf(acc, (-.6, 0, 0)), 1.7, cy, 1, fill=v4_bread_fill)
        v4_estufa_unit(acc, .6, cy, .65)
        v4_bread_bin(acc, (1.25, -D / 2 + .45, 0), .45, .6, 0, 2)
        v4_rack_oven(acc, (-1.05, yb - .58, 0), 0)
        v4_proofer(acc, (-.18, yb - .48, 0), 0)
        v4_rack_trolley(acc, (.45, yb - .4, 0), 0, 6, "roll")
        v4_bread_slicer(acc, (1.1, yb - .4, 0), 0)
        v4_section(acc, 2, W, D, H, yb, panels=((-.85, 2.42, .8), (.05, 2.42, .8)), ticket=(-1.45, 20), display=(.9, 2.45), sign=(-.3, cy))
    else:
        cy = -D / 2 + .75
        v4_service_counter(Xf(acc, (-.95, 0, 0)), 1.95, cy, 2, fill=v4_bread_fill)
        v4_estufa_unit(acc, .37, cy, .65)
        v4_glass_cabinet(acc, W / 2 - .66, -D / 2 + .42, 1.25, .78, 1.95, v4_cakes_fill)
        v4_bread_bin(acc, (W / 2 - .66, -D / 2 + 1.35, 0), .9, .5, 0, 3)
        v4_rack_oven(acc, (-1.45, yb - .58, 0), 0)
        v4_rack_oven(acc, (-.4, yb - .58, 0), 0)
        v4_proofer(acc, (.45, yb - .48, 0), 0)
        v4_rack_trolley(acc, (1.1, yb - .45, 0), 0, 4, "roll")
        v4_rack_trolley(acc, (1.65, yb - .45, 0), 0, 4, "baguette")
        v4_bread_slicer(acc, (-1.65, -D / 2 + 1.45, 0), 90)
        v4_label_scale(acc, (-1.2, cy + .4, .92), 180)
        # price boards over the low proofer / trolleys (the rack ovens' hoods would hide them from the game camera);
        # the 'agora atendendo' display sits on a bracket on top of the cake cabinet, next to the counter
        v4_section(acc, 3, W, D, H, yb, panels=((.62, 2.17, .8), (1.5, 2.17, .8)), ticket=(-1.7, 20))
        cx, cfy = W / 2 - .66, -D / 2 + .42 - .39
        rbox(acc, (.08, .06, .07), (cx, cfy + .05, 1.975), C("2A2E36"), .01, 1)
        v4_ticket_display(acc, cx, cfy + .01, 2.12)


# ================================================================================================ FRIOS E LATICÍNIOS (round 4)
def v4_slices(acc, loc, kind="ham", n=6, yaw=0):
    """A fan of thin slices: ham (pink, pale rim), salami (cut face), cheese (yellow squares)."""
    X = Xf(acc, loc, (0, 0, yaw))
    for k in range(n):
        dx = -.06 + k * .025
        if kind == "cheese":
            rbox(X, (.08, .08, .004), (dx, 0, .004 + k * .003), C("F2CF5A"), 0, 1, rot=(0, -8, 0))
        elif kind == "salami":
            b = arc_lathe_bm([(.035, 0), (.035, .004)], 0, 2 * math.pi, 9, "salami", None, "salami")
            place(b, (dx, 0, .002 + k * .003), (0, -8, 0)); X.add(b, SD)
        else:
            lathe(X, [(0, 0), (.05, 0), (.05, .004), (0, .004)], (dx, 0, .002 + k * .003), C("F0A8A0" if kind == "ham" else "E8B0B0"), 8, 0, rot=(0, -8, 0))


def v4_mortadela(acc, loc, L=.3, r=.065, yaw=0):
    X = Xf(acc, loc, (0, 0, yaw))
    tube(X, [(-L / 2, 0, r), (L / 2, 0, r)], lambda t: r * (.85 + .15 * math.sin(math.pi * t) ** .3), C("C86A60"), 10, 0)
    lathe(X, [(0, 0), (r * .96, 0)], (L / 2 + .001, 0, r), C("EAA6A0"), 12, 0, rot=(0, 90, 0), cap_top=False, cap_bottom=False)
    for k in range(5):
        a = k * 1.3
        blob(X, (.002, .008, .008), (L / 2 + .002, r * .5 * math.cos(a), r + r * .5 * math.sin(a)), C(WHITE), 1, 0, k)


def v4_deli_fill(X, x, k):
    T = sd_tray(X, (x, 0, .012), .22, .46, 0, WHITE)
    m = k % 6
    if m == 0:
        sd_wheel(T, (0, -.08, .006), .1, .08, "rind_wax", 40, -110)
        v4_slices(T, (0, .14, .006), "cheese", 5)
    elif m == 1:
        v4_mortadela(T, (0, -.05, .006), .22, .06, 90)
        v4_slices(T, (0, .16, .006), "ham", 5)
    elif m == 2:
        sd_wedge(T, (-.04, -.12, .006), .12, .07, 45, "rind_natural", -100, "blue_cut")
        sd_brie(T, (0, .1, .006), .07, -90)
    elif m == 3:
        sd_salami(T, (0, -.06, .006), .18, .028, 90, False)
        v4_slices(T, (0, .14, .006), "salami", 5)
    elif m == 4:
        v4_slices(T, (0, -.1, .006), "ham", 6, 90)
        v4_slices(T, (0, .12, .006), "turkey", 6, 90)
    else:
        sd_wheel(T, (0, -.06, .006), .1, .09, "parmesan", 35, -100, "parmesan")
        v4_slices(T, (0, .15, .006), "cheese", 4)
    sd_price_tag(T, (-.06, -.2, .07), (0, 0, 0))


def v4_deli_pack(acc, loc, kind, foam="F4F2EC"):
    rbox(acc, (.2, .14, .02), (loc[0], loc[1], loc[2] + .01), C(foam), .008, 1)
    v4_slices(acc, (loc[0], loc[1], loc[2] + .016), kind, 3)
    rbox(acc, (.205, .145, .004), (loc[0], loc[1], loc[2] + .045), GLASS, .002, 1)
    rbox(acc, (.06, .04, .002), (loc[0] + .05, loc[1] - .03, loc[2] + .048), C(WHITE), 0, 1)


def v4_deli_shelf_fill(X, i, w, d):
    n = int(w / .23)
    for c in range(n):
        for r_ in range(1):
            v4_deli_pack(X, (-w / 2 + .12 + c * .23, -d / 2 + .1 + r_ * .18, 0), ["ham", "cheese", "salami", "turkey"][(i + c + r_) % 4], ["F4F2EC", "2E4A7D"][(c + r_) % 2])


def v4_yogurt_fill(X, i, w, d):
    n = int(w / .08)
    for c in range(n):
        for r_ in range(1):
            px_ = -w / 2 + .05 + c * .08
            if i % 2:
                yogurt(X, (px_, -d / 2 + .08 + r_ * .12, 0), "Body", "yogurt", .032, .06)
                yogurt(X, (px_, -d / 2 + .08 + r_ * .12, .062), "Body", "yogurt", .032, .06)
            else:
                carton(X, (px_, -d / 2 + .08 + r_ * .12, 0), .07, .07, .2, ["milk", "juice_0"][c % 2], "Body")


def queijaria_v4(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    v4_tile_wall(acc, W, yb, H)
    if tier == 1:
        v4_service_counter(acc, 1.75, -D / 2 + .55, 0, fill=v4_deli_fill)
        v4_worktable(acc, -.15, yb - .38, 1.6, .6)
        sd_slicer(acc, (-.55, yb - .4, .9), 0)
        v4_label_scale(acc, (.25, yb - .38, .9), 0)
        v4_hook_rail(acc, -W / 2 + .3, W / 2 - .3, yb - .07, 1.95, 4)
        for k in range(4):
            sd_provolone(acc, -W / 2 + .45 + k * (W - .9) / 3, yb - .19, 1.9, .9 - .1 * (k % 2), False)
        name_board(acc, 0, yb - .08, H - .15, 1.0)
    elif tier == 2:
        cy = -D / 2 + .75
        v4_service_counter(acc, 2.75, cy, 1, fill=v4_deli_fill)
        v4_worktable(acc, -.35, yb - .38, 2.1, .6)
        sd_slicer(acc, (-1.05, yb - .4, .9), 0)
        sd_slicer(acc, (-.45, yb - .4, .9), 0)
        v4_label_scale(acc, (.2, yb - .38, .9), 0)
        sd_paper_roll(acc, (.55, yb - .3, .92), 90, .3, "F4F2EC")
        v4_glass_cabinet(acc, W / 2 - .42, yb - .38, .65, .65, 1.95, v4_yogurt_fill, True, NAVY, 4)
        v4_hook_rail(acc, -1.3, .5, yb - .07, 1.62, 5)
        for k in range(5):
            sd_provolone(acc, -1.15 + k * .38, yb - .19, 1.57, .85, False)
        v4_section(acc, 2, W, D, H, yb, panels=((-.85, 2.42, .8), (.05, 2.42, .8)), ticket=(1.2, -20), display=(.95, 2.42), sign=(-.8, cy))
    else:
        cy = -D / 2 + .75
        Xc = Xf(acc, (-.62, 0, 0))
        v4_service_counter(Xc, 2.65, cy, 2, fill=v4_deli_fill)
        v4_glass_cabinet(acc, W / 2 - .66, -D / 2 + .42, 1.25, .78, 1.95, v4_deli_shelf_fill, False, NAVY, 4)
        v4_worktable(acc, -.6, yb - .38, 2.6, .6)
        for k, sx in enumerate((-1.65, -1.05, -.45)):
            sd_slicer(acc, (sx, yb - .4, .9), 0)
        v4_label_scale(acc, (.15, yb - .38, .9), 0)
        v4_label_scale(acc, (.5, yb - .38, .9), 0)
        v4_glass_cabinet(acc, 1.25, yb - .38, 1.2, .65, 1.95, v4_yogurt_fill, True, NAVY, 4)
        v4_hook_rail(acc, -1.6, .55, yb - .07, 1.62, 4)
        for k in range(4):
            sd_provolone(acc, -1.4 + k * .55, yb - .19, 1.57, .85, False)
        v4_section(acc, 3, W, D, H, yb, panels=((-1.2, 2.17, .8), (-.35, 2.17, .8), (.5, 2.17, .8)), ticket=(-1.7, 20), display=(1.25, 2.3))


# ================================================================================================ PEIXARIA (round 4)
def v4_fish_fill_counter(acc, W, y, seed=0):
    X = v4_counter_shell(acc, W, y, .9, .95, .7, False, "DDE8EE", 14)
    sd_fish_bed(X, W - .14, .56, (0, 0, 0), 0, seed)
    return X


def v4_sink(acc, x, y, w=.7):
    """Stainless sink unit with a deep basin, a gooseneck mixer tap and a splash back."""
    rbox(acc, (w, .6, .85), (x, y, .425), INOX, .02, 2)
    rbox(acc, (w, .6, .04), (x, y, .87), INOX, .01, 2)
    rbox(acc, (w - .2, .4, .02), (x, y - .02, .88), C("8A9298"), 0, 1)
    rbox(acc, (w, .03, .3), (x, y + .285, 1.02), INOX, .006, 1)
    tube(acc, [(x, y + .22, .89), (x, y + .22, 1.25), (x, y + .12, 1.32), (x, y + .02, 1.22)], .014, C(CHROME), 8, 2)
    tube(acc, [(x + .08, y + .22, .95), (x + .14, y + .22, .98)], .01, C(CHROME), 6)


def v4_ice_machine(acc, x, y):
    """Máquina de gelo: stainless storage bin with a sloped flap door and the ice maker head on top."""
    rbox(acc, (.75, .75, 1.0), (x, y, .5), INOX, .03, 2)
    rbox(acc, (.6, .02, .3), (x, y - .38, .75), INOX, .02, 2, rot=(-15, 0, 0))
    rbox(acc, (.4, .03, .04), (x, y - .41, .62), C(CHROME), .01, 1)
    rbox(acc, (.75, .7, .6), (x, y + .02, 1.3), INOX, .03, 2)
    rbox(acc, (.6, .02, .1), (x, y - .335, 1.5), C(NAVY), .01, 1)
    rbox(acc, (.1, .01, .05), (x + .2, y - .347, 1.5), "E_B9F0D0", 0, 1)
    for k in range(10):
        rbox(acc, (.55, .01, .008), (x, y - .33, 1.1 + k * .035), C("8A9298"), 0, 1)


def peixaria_v4(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    rbox(acc, (W, .12, H), (0, yb, H / 2), TILE_W, .02, 2, uv=1.5)
    rbox(acc, (W + .01, .13, 1.1), (0, yb - .01, .55), TILE_B, .015, 2, uv=1.5)
    rbox(acc, (W + .02, .01, .012), (0, yb - .08, 1.1), C(GOLD), .003, 1)
    rbox(acc, (W + .04, .16, .08), (0, yb - .02, H + .04), C(NAVY), .03, 3)
    if tier == 1:
        v4_fish_fill_counter(acc, 1.75, -D / 2 + .55, 1)
        v4_sink(acc, -W / 2 + .5, yb - .38)
        v4_worktable(acc, .45, yb - .38, 1.2, .6)
        v4_label_scale(acc, (.2, yb - .38, .9), 0)
        sd_cutting_board(acc, (.7, yb - .4, .9), 0, .35, .3)
        sd_fish(acc, (.7, yb - .4, .925), .32, 0, "fish_blue")
        sd_knife_strip(acc, .45, yb - .075, 1.5, 4, .5)
        name_board(acc, 0, yb - .08, H - .15, 1.0)
    elif tier == 2:
        cy = -D / 2 + .75
        v4_fish_fill_counter(acc, 2.75, cy, 2)
        v4_sink(acc, -1.2, yb - .38, .75)
        v4_worktable(acc, -.15, yb - .38, 1.2, .6)
        v4_label_scale(acc, (-.45, yb - .38, .9), 0)
        sd_cutting_board(acc, (.1, yb - .4, .9), 0, .4, .3)
        sd_fish(acc, (.1, yb - .4, .925), .34, 0, "fish_red")
        v4_chest_freezer(acc, 1.05, yb - .45, 1.1, .75, .85, "fish", 1)
        sd_knife_strip(acc, -.15, yb - .075, 1.5, 4, .5)
        v4_section(acc, 2, W, D, H, yb, panels=((-.85, 2.42, .8), (.05, 2.42, .8)), ticket=(1.2, -20), display=(.95, 2.42), sign=(-.8, cy))
    else:
        cy = -D / 2 + .75
        Xc = Xf(acc, (-.62, 0, 0))
        v4_fish_fill_counter(Xc, 2.65, cy, 3)
        v4_chest_freezer(acc, W / 2 - .66, -D / 2 + .5, 1.25, .9, .85, "fish", 2)
        sd_lobster_tank(acc, W / 2 - .66, -D / 2 + 1.5, 1.1, .55)
        v4_sink(acc, -1.6, yb - .38, .75)
        v4_worktable(acc, -.6, yb - .38, 1.2, .6)
        v4_label_scale(acc, (-.9, yb - .38, .9), 0)
        sd_cutting_board(acc, (-.4, yb - .4, .9), 0, .4, .3)
        sd_fish(acc, (-.4, yb - .4, .925), .36, 0, "fish_blue")
        v4_ice_machine(acc, .45, yb - .42)
        v4_cold_door(acc, 1.5, yb - .02, .8, 2.05)
        sd_knife_strip(acc, -.6, yb - .075, 1.5, 5, .6)
        v4_section(acc, 3, W, D, H, yb, panels=((-.95, 2.17, .8), (-.12, 2.17, .8), (.71, 2.17, .8)), ticket=(-1.7, 20), display=(1.5, 2.3))


# ================================================================================================ SORVETERIA (round 4)
def v4_icecream_buffet(acc, W, y, seed=0):
    """Self-service ice cream by weight: refrigerated island with two rows of swirled gelato pans with paddles
    under a flat sneeze guard, stainless body and navy front."""
    X = v4_counter_shell(acc, W, y, .9, .95, .55, False, "DDE8EE", 6)
    n = int((W - .2) / .27)
    for r_ in range(2):
        for c in range(n):
            sd_gelato_pan(X, (-(W - .2) / 2 + .135 + c * (W - .2) / n, -.13 + r_ * .26, .06), .25, .22, FLAVORS[(c + r_ * 3 + seed) % 7], c + r_, True)
    return X


def v4_toppings_bar(acc, x, y, w=1.2, seed=0):
    """Toppings island: stainless counter with a row of topping bowls (sprinkles, nuts, chocolate, fruit), syrup
    pump bottles and a glass guard."""
    rbox(acc, (w, .55, .88), (x, y, .44), C(NAVY), .03, 3)
    rbox(acc, (w - .1, .01, .01), (x, y - .28, .7), C(GOLD), .003, 1)
    rbox(acc, (w + .02, .57, .04), (x, y, .9), INOX, .01, 2)
    n = int((w - .1) / .14)
    cols = [None, "7A4A2E", "C0392B", "F2C23F", "8FB24A", None, "3A1A10"]
    for k in range(n):
        px_ = x - (w - .1) / 2 + (k + .5) * (w - .1) / n
        lathe(acc, [(0, 0), (.045, 0), (.06, .06)], (px_, y - .08, .92), INOX, 10, 0, cap_top=False)
        if cols[k % len(cols)]:
            lathe(acc, [(0, .05), (.057, .05), (0, .056)], (px_, y - .08, .92), C(cols[k % len(cols)]), 10, 0)
        else:
            lathe(acc, [(0, .05), (.057, .05), (0, .056)], (px_, y - .08, .92), SD, 10, 0, uv_cell="sd:sprinkles")
    for k in range(4):
        px_ = x - w / 2 + .2 + k * (w - .4) / 3
        lathe(acc, [(0, 0), (.04, 0), (.04, .2), (.015, .24), (0, .24)], (px_, y + .15, .92), C(["7A4A2E", "C0392B", "F2C23F", "5A1F4E"][k]), 10, 0)
        tube(acc, [(px_, y + .15, 1.16), (px_, y + .15, 1.24), (px_, y + .08, 1.24)], .007, C(WHITE), 5)
    rbox(acc, (w - .04, .02, .2), (x, y - .25, 1.12), GLASS, .004, 1, rot=(-20, 0, 0))


def v4_softserve(acc, loc, yaw=0):
    """Máquina de sorvete expresso: floor-standing stainless machine, navy front with a small screen, two flavour
    levers + twist, nozzles over a drip tray, hopper lids on top, cone stack beside."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.55, .75, .8), (0, 0, .4), INOX, .04, 3)
    rbox(X, (.55, .65, .55), (0, .03, 1.08), INOX, .05, 3)
    rbox(X, (.5, .02, .4), (0, -.3, 1.1), C(NAVY), .02, 2)
    rbox(X, (.18, .01, .08), (0, -.313, 1.24), "E_DDF4FF", .004, 1)
    for k in range(3):
        px_ = -.14 + k * .14
        lathe(X, [(0, 0), (.02, 0), (.012, .05), (0, .055)], (px_, -.36, .9), C(CHROME), 8, 0, rot=(180, 0, 0))
        tube(X, [(px_, -.32, 1.0), (px_, -.42, 1.08)], .01, C(CHROME), 6)
        lathe(X, [(0, 0), (.02, 0), (.02, .03), (0, .03)], (px_, -.42, 1.08), C(["F4EBD8", "7A4A2E", "F4A6C1"][k]), 8, 0)
    rbox(X, (.45, .14, .02), (0, -.34, .7), C(CHROME), .006, 1)
    for k in range(2):
        lathe(X, [(0, 0), (.1, 0), (.1, .02), (0, .03)], (-.13 + k * .26, .05, 1.36), C(STEEL), 12, 0)
    for k in range(4):
        sd_cone(X, (.2, -.32, .72 + k * .03), (), .1, .025)


def v4_cups_station(acc, x, y, z):
    """Cups and spoons: stacked cup towers, a cone stack, napkins and the scale at the end of the buffet."""
    for k in range(3):
        lathe(acc, [(.03, 0), (.04, .28), (0, .28)], (x - .1 + k * .1, y, z), C(WHITE), 10, 0, cap_bottom=False)
    lathe(acc, [(.012, 0), (.03, .22), (0, .22)], (x + .2, y, z), SD, 10, 0, uv_cell="sd:waffle", cap_bottom=False)
    sd_spoon_cup(acc, (x + .32, y, z))
    sd_napkins(acc, (x + .45, y, z))


def sorvetes_v4(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    v4_tile_wall(acc, W, yb, H)
    if tier == 1:
        v4_icecream_buffet(acc, 1.75, -D / 2 + .55, 0)
        v4_softserve(acc, (-W / 2 + .45, yb - .48, 0), 0)
        v4_worktable(acc, .5, yb - .38, 1.2, .6)
        v4_label_scale(acc, (.25, yb - .38, .9), 0)
        v4_cups_station(acc, .6, yb - .4, .9)
        name_board(acc, 0, yb - .08, H - .15, 1.0)
    elif tier == 2:
        cy = -D / 2 + .75
        v4_icecream_buffet(Xf(acc, (-.45, 0, 0)), 2.2, cy, 1)
        v4_toppings_bar(acc, W / 2 - .45, cy - .1, .8)
        v4_softserve(acc, (-1.2, yb - .48, 0), 0)
        v4_worktable(acc, -.2, yb - .38, 1.1, .6)
        v4_label_scale(acc, (-.45, yb - .38, .9), 0)
        v4_cups_station(acc, -.1, yb - .4, .9)
        v4_chest_freezer(acc, 1.05, yb - .45, 1.1, .75, .85, "tubs", 1)
        v4_section(acc, 2, W, D, H, yb, panels=((-.85, 2.42, .8), (.05, 2.42, .8)), sign=(-.5, cy))
    else:
        cy = -D / 2 + .75
        Xc = Xf(acc, (-.62, 0, 0))
        v4_icecream_buffet(Xc, 2.65, cy, 2)
        v4_toppings_bar(acc, W / 2 - .66, cy - .1, 1.2)
        v4_chest_freezer(acc, W / 2 - .66, -D / 2 + 1.75, 1.25, .8, .85, "tubs", 2)
        v4_softserve(acc, (-1.6, yb - .48, 0), 0)
        v4_softserve(acc, (-1.0, yb - .48, 0), 0)
        v4_worktable(acc, .05, yb - .38, 1.2, .6)
        v4_label_scale(acc, (-.2, yb - .38, .9), 0)
        v4_cups_station(acc, .15, yb - .4, .9)
        v4_glass_cabinet(acc, 1.25, yb - .38, 1.2, .65, 1.95, lambda X, i, w, d: [sd_cake(X, (-w / 2 + .16 + k * .3, 0, .005), .1, .07, ["straw", "choc", "cream"][(i + k) % 3]) for k in range(int(w / .3))], True, NAVY, 4)
        v4_section(acc, 3, W, D, H, yb, panels=((-1.2, 2.17, .8), (-.35, 2.17, .8), (.5, 2.17, .8)))


# ================================================================================================ ADEGA (round 4)
def v4_gondola_bottle(acc, loc, glass, foil, label, seg=6):
    lathe(acc, [(.034, 0), (.036, .02), (.036, .2), (.016, .245), (.014, .3), (0, .31)], loc, C(glass), seg, 0, cap_bottom=False)
    lathe(acc, [(.0372, .06), (.0372, .15)], loc, SD, seg, 0, uv_cell="sd:" + label, cap_top=False, cap_bottom=False)
    lathe(acc, [(.0155, .26), (.016, .31), (0, .315)], loc, C(foil), seg, 0, cap_bottom=False)


def v4_wine_gondola(acc, x, y, w=1.0, h=1.9, seed=0, rot=0):
    """Wine gondola: navy steel uprights and base, light-wood shelves, bottles standing label-out (a cheaper
    second row behind), navy shelf-edge strips with blank price tags, a header with a blank sign."""
    X = Xf(acc, (x, y, 0), (0, 0, rot))
    for sx in (-1, 1):
        rbox(X, (.05, .45, h), (sx * (w / 2 - .025), 0, h / 2), C(NAVY), .015, 2)
    rbox(X, (w, .05, h - .1), (0, .2, h / 2), WOOD_D, .01, 1)
    rbox(X, (w, .45, .12), (0, 0, .06), C(NAVY), .02, 2)
    rbox(X, (w + .02, .05, .16), (0, -.0, h + .06), C(NAVY), .02, 2)
    plate(X, w * .6, .1, (0, -.03, h + .06), C(CREAM), .006, .03)
    glasses = ["2A3B22", "4A1C24", "3A2A1A", "2A3B22", "5A1F2A"]
    foils = ["7A1E2E", GOLD, NAVY, "2A2A2A"]
    labels = ["wl_grape", "wl_leaf", "wl_star", "wl_glass"]
    rows = 4
    for r_ in range(rows):
        z = .14 + r_ * (h - .3) / rows
        rbox(X, (w - .06, .4, .025), (0, .0, z), WOOD_L, .006, 1)
        rbox(X, (w - .06, .015, .045), (0, -.205, z + .005), C(NAVY), .003, 1)
        n = int((w - .1) / .12)
        for k in range(n):
            px_ = -(w - .1) / 2 + (k + .5) * (w - .1) / n
            i = k + r_ * 3 + seed
            v4_gondola_bottle(X, (px_, -.1, z + .0125), glasses[i % 5], foils[i % 4], labels[i % 4])
            if k % 2 == 0:
                lathe(X, [(.034, 0), (.034, .22), (.015, .3), (0, .3)], (px_ + .06, .08, z + .0125), C(glasses[(i + 2) % 5]), 5, 0, cap_bottom=False)
            if k % 2 == 0:
                rbox(X, (.05, .004, .03), (px_, -.214, z + .005), C(CREAM), 0, 1)


def v4_wine_cooler(acc, x, y, w=.65):
    """Adega climatizada: dark cabinet, glass door with a steel frame, light-wood racks of lying bottles, LED and
    a small temperature display."""
    for s_ in (-1, 1):
        rbox(acc, (.04, .65, 1.85), (x + s_ * (w / 2 - .02), y, .925), C("1B1E24"), .015, 2)
    rbox(acc, (w, .65, .14), (x, y, .07), C("1B1E24"), .02, 2)
    rbox(acc, (w, .65, .1), (x, y, 1.8), C("1B1E24"), .02, 2)
    rbox(acc, (w, .04, 1.85), (x, y + .305, .925), C("1B1E24"), .015, 2)
    rbox(acc, (w - .08, .02, 1.6), (x, y - .33, .97), GLASS, .006, 1)
    fr = frame_bm(w - .04, 1.65, .03, .02, .035); place(fr, (x, y - .335, .97)); acc.add(fr, C(CHROME))
    rbox(acc, (w - .1, .02, 1.55), (x, y + .27, .97), WOOD_D, .006, 1)
    rbox(acc, (w - .14, .02, .015), (x, y - .25, 1.72), "E_FFE6B8", .004, 1)
    for k in range(6):
        z = .3 + k * .24
        rbox(acc, (w - .1, .5, .02), (x, y - .02, z), WOOD_L, .004, 1)
        for j in range(4):
            px_ = x - (w - .14) / 2 + (j + .5) * (w - .14) / 4
            lathe(acc, [(0, 0), (.034, 0), (.034, .2), (.015, .26), (0, .27)], (px_, y + .18, z + .045), C(["2A3B22", "4A1C24"][(j + k) % 2]), 6, 0, rot=(90, 0, 0))
            lathe(acc, [(0, 0), (.016, 0), (0, .02)], (px_, y - .09, z + .045), C(["7A1E2E", GOLD, NAVY][(j + k) % 3]), 6, 0, rot=(90, 0, 0))
    rbox(acc, (.1, .01, .04), (x, y - .337, 1.8), "E_FF4A3A", 0, 1)
    rbox(acc, (.03, .04, .5), (x + w / 2 - .07, y - .36, 1.05), C(CHROME), .01, 1)


def v4_crate_island(acc, x, y, w=1.2, d=.8, seed=0):
    """Feature island: a low light-wood platform with stacked wine crates (some open, bottles in straw) and a blank
    sign on a stem."""
    rbox(acc, (w, d, .3), (x, y, .15), WOOD_L, .02, 2)
    rbox(acc, (w + .01, d + .01, .05), (x, y, .05), C(NAVY), .01, 1)
    for k in range(2):
        sd_wine_crate(acc, (x - w / 4 + k * w / 2, y - .12, .3), 5 * k, 3, True)
        rbox(acc, (.52, .34, .2), (x - w / 4 + k * w / 2 + .03, y + .2, .4), WOOD_L, .01, 1)
    sd_wine_crate(acc, (x, y + .2, .5), -6, 3, False)
    v4_sign_tag(acc, x + w / 2 - .12, y - d / 2 + .1, .3)


def v4_tasting_machine(acc, x, y):
    """Wine dispenser (tasting machine): navy cabinet, a lit glass front with four bottles upright, chrome spouts,
    a card slot, drip tray and a row of glasses."""
    rbox(acc, (1.0, .55, .9), (x, y, .45), C(NAVY), .03, 3)
    for s_ in (-1, 1):
        rbox(acc, (.05, .55, .7), (x + s_ * .475, y, 1.25), INOX, .015, 2)
    rbox(acc, (1.0, .55, .1), (x, y, 1.55), INOX, .02, 2)
    rbox(acc, (1.0, .04, .7), (x, y + .255, 1.25), INOX, .01, 1)
    rbox(acc, (.9, .02, .5), (x, y - .27, 1.3), GLASS, .004, 1)
    rbox(acc, (.88, .02, .48), (x, y + .2, 1.3), "E_FFE6B8", .004, 1)
    for k in range(4):
        px_ = x - .33 + k * .22
        v4_gondola_bottle(acc, (px_, y - .05, 1.06), ["2A3B22", "4A1C24", "3A2A1A", "5A1F2A"][k], [GOLD, "7A1E2E", NAVY, GOLD][k], ["wl_grape", "wl_star", "wl_leaf", "wl_glass"][k], 8)
        tube(acc, [(px_, y - .27, 1.02), (px_, y - .32, 1.02), (px_, y - .32, .98)], .008, C(CHROME), 6)
    rbox(acc, (.9, .15, .02), (x, y - .3, .91), C(CHROME), .006, 1)
    rbox(acc, (.08, .02, .1), (x + .42, y - .28, 1.1), C("1B1E24"), .006, 1)
    rbox(acc, (.06, .005, .008), (x + .42, y - .29, 1.12), "E_37D067", 0, 1)
    for k in range(4):
        sd_wine_glass(acc, (x - .33 + k * .22, y - .3, .92), None, False)


def adega_v4(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    rbox(acc, (W, .12, H), (0, yb, H / 2), "T_IK_WoodDark", .02, 2, uv=1.5)
    rbox(acc, (W + .01, .13, .9), (0, yb - .01, .45), C(NAVY), .015, 2)
    rbox(acc, (W + .02, .01, .012), (0, yb - .08, .9), C(GOLD), .003, 1)
    rbox(acc, (W + .04, .16, .08), (0, yb - .02, H + .04), C(NAVY), .03, 3)
    if tier == 1:
        v4_wine_gondola(acc, -.55, yb - .3, 1.1, 1.9, 0)
        v4_wine_gondola(acc, .65, yb - .3, 1.0, 1.9, 2)
        v4_crate_island(acc, 0, -D / 2 + .55, 1.0, .7, 0)
        name_board(acc, 0, yb - .08, H - .15, 1.0)
    elif tier == 2:
        for k, gx in enumerate((-1.05, 0)):
            v4_wine_gondola(acc, gx, yb - .3, 1.0, 1.9, k * 2)
        v4_wine_cooler(acc, .9, yb - .38, .7)
        v4_crate_island(acc, -.3, -D / 2 + .65, 1.3, .8, 1)
        v4_wine_gondola(acc, W / 2 - .3, -D / 2 + .7, .9, 1.4, 4, -90)
        v4_section(acc, 2, W, D, H, yb, panels=((-.55, 2.42, .8),), sign=(-.3, -D / 2 + .65))
    else:
        for k, gx in enumerate((-1.55, -.5)):
            v4_wine_gondola(acc, gx, yb - .3, 1.0, 1.9, k * 2)
        v4_wine_cooler(acc, .35, yb - .38, .7)
        v4_wine_cooler(acc, 1.05, yb - .38, .7)
        v4_tasting_machine(acc, 1.45, -D / 2 + 1.35)
        v4_crate_island(acc, -.6, -D / 2 + .7, 1.5, .85, 2)
        v4_section(acc, 3, W, D, H, yb, panels=((-1.05, 2.17, .8), (.7, 2.17, .8)))


# ================================================================================================ SUCOS (round 4)
def v4_zummo(acc, loc, yaw=0):
    """Automatic orange juicer (Zummo style): stainless body, a clear hopper heaped with oranges on top, a front
    window onto the cutting cups, a spout over a cup, peel bins below and a navy front plate."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.55, .5, .7), (0, 0, .35), INOX, .06, 3)
    rbox(X, (.5, .02, .2), (0, -.255, .52), C(NAVY), .02, 2)
    rbox(X, (.32, .02, .18), (0, -.252, .3), GLASS, .01, 1)
    for sx in (-1, 1):
        lathe(X, [(0, 0), (.06, 0), (.06, .03), (0, .03)], (sx * .07, -.2, .3), C(CHROME), 12, 0, rot=(90, 0, 0))
        sd_citrus_half(X, (sx * .07, -.22, .3 - .03), .05, "orange", (90, 0, 0))
    tube(X, [(0, -.26, .2), (0, -.32, .2), (0, -.32, .16)], .012, C(CHROME), 6)
    sd_cup(X, (0, -.32, .02), "F28C28", "E8505B", None, .12)
    lathe(X, [(.2, 0), (.22, .32), (.2, .34)], (0, .02, .7), GLASS, 16, 0, cap_top=False, cap_bottom=False)
    lathe(X, [(0, 0), (.21, 0)], (0, .02, .7), C(STEEL), 16, 0, cap_top=False, cap_bottom=False)
    for k in range(6):
        a = k * 2.4
        rr = .1 if k else 0
        sd_orange(X, (rr * math.cos(a), .02 + rr * math.sin(a), .7 + (k % 3) * .07), .055, False, "F28C28", k)
    for sx in (-1, 1):
        rbox(X, (.24, .45, .35), (sx * .15, .02, -.175 + .0), C(NAVY), .03, 2)


def v4_zummo_stand(acc, loc, yaw=0):
    """The juicer on its stainless stand with the two peel bins underneath (peel halves visible)."""
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.6, .55, .55), (0, 0, .275), INOX, .03, 2)
    for sx in (-1, 1):
        open_box(X, .25, .42, .3, (sx * .15, -.02, .55), C(NAVY), .015, 0, 1)
        for k in range(4):
            lathe(X, [(0, 0), (.04, .02), (.045, .04)], (sx * .15 + (k % 2) * .06 - .03, -.05 + (k // 2) * .1, .82), C("F28C28"), 8, 0, cap_top=False)
    v4_zummo(X, (0, -.02, .87), 0)


def v4_blender_pro(acc, loc, col="F28C28"):
    """Industrial blender: navy base with a dial, tall square clear jar with juice, black lid."""
    x, y, z = loc
    rbox(acc, (.2, .22, .2), (x, y, z + .1), C(NAVY), .03, 2)
    lathe(acc, [(0, 0), (.02, 0), (.02, .015), (0, .02)], (x, y - .11, z + .1), C(CHROME), 8, 0, rot=(90, 0, 0))
    rbox(acc, (.14, .14, .3), (x, y, z + .36), GLASS, .02, 1)
    rbox(acc, (.125, .125, .2), (x, y, z + .32), C(col), .015, 1)
    rbox(acc, (.15, .15, .04), (x, y, z + .53), C(INK), .015, 1)
    tube(acc, [(x + .07, y, z + .45), (x + .12, y, z + .45), (x + .12, y, z + .3), (x + .07, y, z + .3)], .01, C(INK), 5)


def v4_juice_cooler_fill(X, i, w, d):
    cols = [("C_F28C28", "juice_0"), ("C_D8354A", "juice_1"), ("C_7DB84A", "juice_2"), ("C_F2C23F", "juice_3")]
    n = int(w / .11)
    for c in range(n):
        liq, lab = cols[(i + c // 2) % 4]
        pet_bottle(X, (-w / 2 + .06 + c * .11, -d / 2 + .08, 0), .26, .033, liq, lab, C(NAVY), "Body", 6)


def v4_juice_counter(acc, W, y, H=.95, D=.8, crates=True, seed=0):
    """Juice counter: navy body with light-wood slats and a gold line, marble top, a fruit display row of tilted
    crates on the customer face."""
    rbox(acc, (W, D, H - .05), (0, y, (H - .05) / 2), C(NAVY), .03, 3)
    rbox(acc, (W - .1, .01, .01), (0, y - D / 2 - .004, .88), C(GOLD), .003, 1)
    rbox(acc, (W + .04, D + .04, .05), (0, y, H - .025), MARBLE, .01, 2)
    if crates:
        n = max(2, int(W / .6))
        for i in range(n):
            px_ = -W / 2 + (i + .5) * W / n
            Xc = Xf(acc, (px_, y - D / 2 - .1, .45), (22, 0, 0))
            open_box(Xc, W / n - .04, .3, .1, (0, 0, 0), WOOD, .014, .006, 2)
            sd_fruit_mound(Xc, W / n - .08, .26, (0, 0, .02), ["orange", "lemon", "apple", "lime", "kiwi", "strawberry"][(i + seed) % 6], i, 0, .045)


def sucos_v4(acc, tier):
    W, D, H = SECTOR_SIZES[tier - 1]
    yb = D / 2 - .06
    v4_tile_wall(acc, W, yb, H)
    if tier == 1:
        cy = -D / 2 + .65
        v4_juice_counter(acc, 1.8, cy, .95, .8, True, 0)
        v4_zummo(acc, (-.4, cy + .05, .95), 0)
        v4_blender_pro(acc, (.25, cy + .1, .95), "D8354A")
        for k in range(3):
            sd_cup(acc, (.5 + k * .1, cy - .15, .95), ["F28C28", "D8354A", "7DB84A"][k], ["E8505B", NAVY, GOLD][k], ["orange", "lemon", "lime"][k])
        rbox(acc, (W - .4, .3, .03), (0, yb - .2, 1.4), WOOD, .01, 1)
        for k, kind in enumerate(("orange", "lemon", "apple")):
            Bk = basket(acc, .4, .26, .1, (-.7 + k * .7, yb - .2, 1.42), 0)
            sd_fruit_mound(Bk, .36, .22, (0, 0, .02), kind, k, 0, .04)
        name_board(acc, 0, yb - .08, H - .15, 1.0)
    elif tier == 2:
        cy = -D / 2 + .75
        v4_juice_counter(acc, 2.4, cy, .95, .8, True, 1)
        v4_zummo(acc, (-.75, cy + .05, .95), 0)
        for k in range(2):
            v4_blender_pro(acc, (.1 + k * .28, cy + .12, .95), ["F2C23F", "7DB84A"][k])
        for k in range(4):
            sd_cup(acc, (.7 + k * .1, cy - .18, .95), list(JUICE.values())[k], ["E8505B", NAVY, GOLD, "5FB548"][k], ["orange", "lemon", "lime", None][k])
        v4_glass_cabinet(acc, W / 2 - .42, yb - .38, .65, .65, 1.95, v4_juice_cooler_fill, True, NAVY, 4)
        v4_worktable(acc, -.55, yb - .38, 1.5, .6)
        for k, kind in enumerate(("orange", "lemon", "orange")):
            Cr = crate(acc, .4, .3, .12, (-1.05 + k * .45, yb - .4, .9), 0)
            sd_fruit_mound(Cr, .36, .26, (0, 0, .02), kind, k, 0, .04)
        sd_juicer(acc, (.12, yb - .38, .9))
        v4_section(acc, 2, W, D, H, yb, panels=((-.85, 2.42, .8), (.05, 2.42, .8)), sign=(-.3, cy))
    else:
        cy = -D / 2 + .75
        Xc = Xf(acc, (-.55, 0, 0))
        v4_juice_counter(Xc, 2.7, cy, .95, .8, True, 2)
        v4_zummo_stand(acc, (W / 2 - .45, -D / 2 + .55, 0), 0)
        v4_zummo(Xc, (-.9, cy + .05, .95), 0)
        for k in range(3):
            v4_blender_pro(Xc, (-.25 + k * .28, cy + .12, .95), ["F2C23F", "7DB84A", "D8354A"][k])
        for k in range(4):
            sd_cup(Xc, (.65 + k * .1, cy - .18, .95), list(JUICE.values())[k], ["E8505B", NAVY, GOLD, "5FB548"][k], ["orange", "lemon", "lime", None][k])
        sd_pitcher(Xc, (1.15, cy + .1, .95), "F28C28")
        v4_glass_cabinet(acc, .9, yb - .38, 1.2, .65, 1.95, v4_juice_cooler_fill, True, NAVY, 4)
        v4_worktable(acc, -.9, yb - .38, 2.0, .6)
        for k, kind in enumerate(("orange",)):
            Cr = crate(acc, .4, .3, .12, (-1.6 + k * .45, yb - .4, .9), 0)
            sd_fruit_mound(Cr, .36, .26, (0, 0, .02), kind, k, 0, .04)
        sd_juicer(acc, (.0, yb - .38, .9))
        v4_section(acc, 3, W, D, H, yb, panels=((-1.2, 2.17, .8), (-.35, 2.17, .8), (.5, 2.17, .8)))


# ================================================================================================ registration
SECTOR_NAMES["queijaria"] = "Frios e laticínios"
SECTOR_TIER_NAMES.update({
    "acougue": ("balcão de atendimento", "açougue", "açougue completo"),
    "padaria": ("balcão de pães", "padaria", "padaria completa"),
    "queijaria": ("balcão de frios", "frios e queijos", "frios e laticínios completo"),
    "peixaria": ("balcão de peixes", "peixaria", "peixaria completa"),
    "sorvetes": ("sorvete a quilo", "sorveteria", "sorveteria completa"),
    "adega": ("gôndola de vinhos", "adega", "adega completa"),
    "sucos": ("balcão de sucos", "casa de sucos", "sucos completo"),
})
for _sid, _fn in (("acougue", acougue_v4), ("padaria", padaria_v4), ("queijaria", queijaria_v4), ("peixaria", peixaria_v4),
                  ("sorvetes", sorvetes_v4), ("adega", adega_v4), ("sucos", sucos_v4)):
    BUILDERS["sector-" + _sid] = make_sector_v2(_sid, _fn)
    TIERS["sector-" + _sid] = [("T%d" % (i + 1), "%s: %s" % (SECTOR_NAMES[_sid], SECTOR_TIER_NAMES[_sid][i]), w, d, h)
                               for i, (w, d, h) in enumerate(SECTOR_SIZES)]



# ================================================================================================ export (round 4)
# Name panels: every blank panel the game writes the sector name on (T1 name board, T2 hanging sign, T3 testeira)
# gets a flat quad on its own slot "E_NamePanel" (UV 0..1), just in front of the cream plate. Screens and name
# panels are logged per tier (Unity-local centre and size) for the README.
SLOTLOG = {}
_CUR = [None]


def _world(acc, p):
    v = Vector(p)
    a = acc
    while isinstance(a, Xf):
        v = a.M @ v
        a = a.acc
    return v


def _log(slot, p, w=None, h=None, acc=None):
    if not _CUR[0]:
        return
    v = _world(acc, p) if acc is not None else Vector(p)
    e = {"slot": slot, "center_unity": [round(v.x, 3), round(v.z, 3), round(v.y, 3)]}
    if w:
        e["size"] = [round(w, 3), round(h, 3)]
        e["faces"] = "-Z (customer side)"
    SLOTLOG.setdefault(_CUR[0], []).append(e)


def name_quad(acc, w, h, loc):
    screen_quad(acc, w, h, loc, "E_NamePanel")
    _log("E_NamePanel", loc, w, h, acc)


def name_board(acc, x, y, z, w=1.1, h=.3):
    """Blank arched board; the cream face carries the E_NamePanel quad (the game writes the sector name)."""
    plate(acc, w, h, (x, y, z), C(NAVY), .05, h * .45)
    fr = frame_bm(w - .04, h - .04, .012, h * .4, .014)
    place(fr, (x, y - .028, z)); acc.add(fr, C(GOLD))
    plate(acc, w * .8, h * .62, (x, y - .03, z), C(CREAM), .01, h * .3)
    name_quad(acc, w * .72, h * .5, (x, y - .037, z))


_v4_hanging_sign = v4_hanging_sign


def v4_hanging_sign(acc, x, y, z, w=.9, h=.28):
    _v4_hanging_sign(acc, x, y, z, w, h)
    name_quad(acc, w * .74, h * .5, (x, y - .023, z))


_v4_testeira = v4_testeira


def v4_testeira(acc, W, yb, H, h=.42, depth=.55):
    _v4_testeira(acc, W, yb, H, h, depth)
    name_quad(acc, W * .4, h * .5, (0, yb - .06 - depth - .022, H - h * .45))


_v4_price_panel = v4_price_panel


def v4_price_panel(acc, x, y, z, w=1.0, variant=0, rot=(0, 0, 0)):
    _v4_price_panel(acc, x, y, z, w, variant, rot)
    _log("E_PriceScreen", (x, y - .002, z), w, w * 9 / 16, acc)


_v4_ticket_display = v4_ticket_display


def v4_ticket_display(acc, x, y, z, rot=(0, 0, 0)):
    _v4_ticket_display(acc, x, y, z, rot)
    _log("E_TicketScreen", (x, y - .002, z), .36, .16, acc)


_v4_ticket_dispenser = v4_ticket_dispenser


def v4_ticket_dispenser(acc, loc, yaw=0):
    _v4_ticket_dispenser(acc, loc, yaw)
    _log("TicketDispenser (floor point)", loc, None, None, acc)


def _logged(sid, fn):
    def mk(t):
        def f(acc):
            key = "sector-%s_T%d" % (sid, t)
            _CUR[0] = key
            SLOTLOG[key] = []
            try:
                fn(acc, t)
            finally:
                _CUR[0] = None
        return f
    return [mk(t) for t in (1, 2, 3)]


for _sid, _fn in (("acougue", acougue_v4), ("padaria", padaria_v4), ("queijaria", queijaria_v4), ("peixaria", peixaria_v4),
                  ("sorvetes", sorvetes_v4), ("adega", adega_v4), ("sucos", sucos_v4)):
    BUILDERS["sector-" + _sid] = _logged(_sid, _fn)


def v4_name_material():
    m = bpy.data.materials.get("E_NamePanel") or bpy.data.materials.new("E_NamePanel")
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = srgb(CREAM) + (1,)
    b.inputs["Roughness"].default_value = .5
    return m


def v4_export_all():
    """Rebuild every sector lineup and write export/sector-<id>_T<n>.fbx (screens blanked by export_tier)."""
    import json
    reps = []
    for sid in ("acougue", "padaria", "queijaria", "peixaria", "sorvetes", "adega", "sucos"):
        v4_materials(sid)
        v4_name_material()
        rebuild("sector-" + sid)
        for t in (1, 2, 3):
            r = export_tier("sector-" + sid, t)
            r["slots"] = SLOTLOG.get("sector-%s_T%d" % (sid, t), [])
            reps.append(r)
    with open(os.path.join(EXPORT, "sector_export_report.json"), "w") as f:
        json.dump(reps, f, indent=1, ensure_ascii=False)
    return [(r["file"], r["tris"]) for r in reps]
