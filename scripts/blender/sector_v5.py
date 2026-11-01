"""Special sectors, round 5: market-wall backs, integrated menu boards, one accent family per sector, a staff lane
(exec'd after fixture_tiers.py, sector_detail.py and sector_v4.py, into the same namespace).

Lucas (01/11): the white-tile back wall clashed with the market's own wall; sectors must sit flush against it; the
price boards should be better; more colour (one accent family per sector, not white enamel); the staff are chubby
and need a wider lane behind the counter.

Every sector piece now has three objects (direct children of the FBX root):
  - "Body":          counters, machines, furniture, products (everything standing on the floor);
  - "Back Wall":     only the freestanding panel (market-wall style: navy fluted wainscot, gold rail, cream body,
                     thin gold cap, navy side returns). The game hides it when the piece stands against a market wall;
  - "Wall Dressing": everything mounted on the wall (menu board with its name header and ticket counter, hook rail,
                     knife strip, cold-room door). It reads both on the market wall and on the panel.
Nothing sticks out behind the footprint's back edge (modelling y = +D/2, Unity z = +depth/2).
"""
# market wall ("Cores do mercado" repaints flat navy / gold by colour; cream is never repainted)
MW_NAVY, MW_GOLD, MW_CREAM = "1D2B4F", "D3A53D", "F2EADB"
ROLE["F2EADB"] = "Cream"
MARKET_WALL_H = 2.49          # CheckoutMarketShell: Top - Floor (interior plaster to top - .02, gold coping above)
PANEL_T = .05                 # the panel's cream body; the wall dressing mounts on its face (y = D/2 - PANEL_T)
PANEL_H = 2.40                # cream top; the gold cap brings the panel to 2.45 m (< the market wall)
BACK_CLEAR = .09              # furniture backs stay this far from the back edge (clear of the panel's rail)
STAFF_W = .70                 # staff character width (shoulders / belly), confirmed by the implementation agent
LANE = STAFF_W + .25          # clear lane behind the counter
GRAPH = "1B1E24"              # matte screen / bezel black

# new footprints (W, D) per tier; height = the panel (2.45 m)
V5_SIZES = {sid: [(2.5, 2.75), (3.25, 3.0), (4.0, 3.25)] for sid in SECTOR_NAMES}
V5_H = PANEL_H + .05

# one accent family per sector (machines and furniture instead of white enamel)
ACCENT = {
    "acougue": ("7E1F2C", "A33241"),     # burgundy enamel
    "padaria": ("B5652E", "D98F3E"),     # terracotta / golden crust
    "peixaria": ("1F7A8C", "4FB3BF"),    # sea teal
    "queijaria": ("E8C35A", "F4DC8A"),   # butter yellow
    "sorvetes": ("F2A7C3", "9ED9C3"),    # pastel pink + mint
    "adega": ("5E1A2A", "7D2A3B"),       # burgundy wine
    "sucos": ("F28C28", "6DB33F"),       # citrus orange + green
}


def v5_tiers(sid):
    TIERS["sector-" + sid] = [("T%d" % (i + 1), "%s: %s" % (SECTOR_NAMES[sid], SECTOR_TIER_NAMES[sid][i]), w, d, V5_H)
                              for i, (w, d) in enumerate(V5_SIZES[sid])]


def BW(acc):
    return Xf(acc, grp="Back Wall")


def WD(acc):
    return Xf(acc, grp="Wall Dressing")


# ================================================================================================ back wall (panel)
def v5_back_wall(acc, W, D, flutes=True):
    """Freestanding panel in the market wall's style, its back face exactly on the footprint's back edge."""
    B = BW(acc)
    ye = D / 2
    rbox(B, (W, PANEL_T, PANEL_H), (0, ye - PANEL_T / 2, PANEL_H / 2), C(MW_CREAM), .004, 1)
    rbox(B, (W - .06, .065, .95), (0, ye - .0325, .475), C(MW_NAVY), .006, 1)
    if flutes:
        n = max(2, int((W - .1) / .11))
        for k in range(n):
            x = -W / 2 + .08 + k * (W - .16) / (n - 1)
            rbox(B, (.03, .008, .88), (x, ye - .069, .47), C(MW_NAVY), 0, 1)
    rbox(B, (W - .06, .08, .07), (0, ye - .04, .985), C(MW_GOLD), .012, 2)
    rbox(B, (W, .07, .05), (0, ye - .035, PANEL_H + .025), C(MW_GOLD), .012, 2)
    for s in (-1, 1):
        rbox(B, (.03, .075, PANEL_H), (s * (W / 2 - .015), ye - .0375, PANEL_H / 2), C(MW_NAVY), .006, 1)


def v5_planes(D):
    """(edge, dressing plane, furniture back) in modelling y."""
    ye = D / 2
    return ye, ye - PANEL_T, ye - BACK_CLEAR


def standoff(acc, x, z, y0, ye, w=.04, h=.08):
    """Short stainless wall bracket from y0 (the back of what it holds) to just inside the footprint edge."""
    rbox(acc, (w, ye - .003 - y0, h), (x, (ye - .003 + y0) / 2, z), C(CHROME), .006, 1)


# ================================================================================================ menu board
def v5_menu_board(acc, x, ztop, D, screens=1, sw=.78, ticket=False, variant0=0, frame=None, lamps=True):
    """One integrated menu board on two wall brackets: matte black screen(s) in a slim stainless frame, a cream
    header strip with the E_NamePanel quad (name and prices read as one unit), the price rows on E_PriceScreen (one
    quad per panel, up to three rows each), the ticket counter (E_TicketScreen) in the header's right end.
    Returns (width, height)."""
    ye, yw, _ = v5_planes(D)
    frame = frame or INOX
    m, gap, hh = .035, .03, .14
    sh = sw * 9 / 16
    Wb = screens * sw + (screens - 1) * gap + 2 * m
    Hb = m + hh + .02 + sh + m
    zc = ztop - Hb / 2
    if _CUR[0]:
        BOARDLOG.setdefault(_CUR[0], []).append((tuple(_world(acc, (x, yw, zc))), Wb, Hb))
    so = .045                                      # standoff: board back 4.5 cm off the wall
    yb = yw - so                                    # board back plane
    # body and frame
    rbox(acc, (Wb, .03, Hb), (x, yb - .015, zc), C(GRAPH), .012, 2)
    fr = frame_bm(Wb, Hb, .022, .02, m, 4)
    place(fr, (x, yb - .03 - .011, zc)); uv_box(fr); acc.add(fr, frame)
    yf = yb - .03                                   # face of the black body
    # header strip (cream) + gold line under it
    hz = ztop - m - hh / 2
    hw = Wb - 2 * m
    rbox(acc, (hw, .006, hh), (x, yf - .003, hz), C(CREAM), .002, 1)
    rbox(acc, (hw, .008, .008), (x, yf - .004, hz - hh / 2 - .008), C(MW_GOLD), .002, 1)
    tw = .3 if ticket else 0
    nw = (hw - tw - .04) * .86
    nx = x - (tw / 2 if ticket else 0)
    name_quad(acc, nw, hh * .66, (nx, yf - .0075, hz))
    if ticket:
        tx = x + hw / 2 - tw / 2 - .015
        rbox(acc, (tw, .014, hh - .03), (tx, yf - .01, hz), C(GRAPH), .006, 1)
        screen_quad(acc, tw - .05, (tw - .05) * .16 / .36, (tx, yf - .0175, hz), "E_TicketScreen")
        _log("E_TicketScreen", (tx, yf - .0175, hz), tw - .05, (tw - .05) * .16 / .36, acc)
        lathe(acc, [(0, 0), (.012, 0), (.012, .008), (0, .01)], (tx + tw / 2 - .02, yf - .017, hz + (hh - .03) / 2 - .015), "E_FF4A3A", 8, 0, rot=(90, 0, 0))
    # screens (one quad per panel; render-only preview: the sector's board sheet, one third per panel)
    sz = zc - Hb / 2 + m + sh / 2
    x0 = x - Wb / 2 + m + sw / 2
    for i in range(screens):
        sx = x0 + i * (sw + gap)
        v = (variant0 + i) % 3
        screen_quad(acc, sw, sh, (sx, yf - .002, sz), "E_PriceScreen", (0, 0, 0), 1 - (v + 1) / 3, 1 - v / 3)
        _log("E_PriceScreen", (sx, yf - .002, sz), sw, sh, acc)
        if i:
            rbox(acc, (gap - .006, .016, sh + .02), (sx - sw / 2 - gap / 2, yf - .008, sz), frame, .004, 1)
    # brackets and picture lights
    for s in (-1, 1):
        bx = x + s * (Wb / 2 - min(.18, Wb * .2))
        standoff(acc, bx, zc + Hb * .25, yb, ye)
        standoff(acc, bx, zc - Hb * .25, yb, ye)
        if lamps:
            tube(acc, [(bx, yb - .01, ztop + .01), (bx, yb - .1, ztop + .1), (bx, yb - .2, ztop + .08)], .007, C(CHROME), 6)
            lathe(acc, [(0, 0), (.022, 0), (.03, -.05), (0, -.05)], (bx, yb - .21, ztop + .1), C(GRAPH), 10, 0, rot=(-35, 0, 0))
            lathe(acc, [(0, 0), (.027, 0)], (bx, yb - .24, ztop + .06), LED, 10, 0, rot=(-35, 0, 0))
    return Wb, Hb


# ================================================================================================ wall dressing helpers
def v5_hook_rail(acc, x0, x1, D, z, hooks=5, hang=()):
    """Hook rail on standoffs (wall dressing)."""
    ye, yw, _ = v5_planes(D)
    tube(acc, [(x0, yw - .1, z), (x1, yw - .1, z)], .016, C(CHROME), 8)
    for xx in (x0 + .05, x1 - .05) + (((x0 + x1) / 2,) if x1 - x0 > 1.0 else ()):
        tube(acc, [(xx, ye - .004, z), (xx, yw - .1, z)], .012, C(CHROME), 6)
        rbox(acc, (.05, .012, .07), (xx, yw - .006, z), C(CHROME), .004, 1)
    for k in range(hooks):
        hx = x0 + .15 + k * (x1 - x0 - .3) / max(1, hooks - 1)
        sd_s_hook(acc, hx, yw - .1, z - .03)
        if k < len(hang) and hang[k]:
            if hang[k] == "sausage":
                sd_sausage_loop(acc, hx, yw - .1, z - .06, .42, 6, .016)
            elif hang[k] == "ham":
                sd_ham(acc, hx, yw - .1, z - .02, .9)


def v5_knife_strip(acc, x, D, z, n=4, w=.5):
    ye, yw, _ = v5_planes(D)
    standoff(acc, x - w / 2 + .05, z, yw - .0125, ye, .03, .04)
    standoff(acc, x + w / 2 - .05, z, yw - .0125, ye, .03, .04)
    sd_knife_strip(acc, x, yw - .025, z, n, w)


def v5_cold_door(acc, x, D, w=.85, h=2.05):
    """Cold-room door in its frame, the frame's back on the footprint edge."""
    ye, yw, _ = v5_planes(D)
    v4_cold_door(acc, x, ye - .07, w, h)


def v5_mat(acc, x, y, w, d):
    """Anti-fatigue rubber mat on the staff lane (dark, with a raised rim and a dimple grid)."""
    rbox(acc, (w, d, .012), (x, y, .006), C("2B2F35"), .006, 1)
    n = int(w / .1)
    for k in range(n):
        rbox(acc, (.012, d - .06, .004), (x - w / 2 + .05 + k * (w - .1) / max(1, n - 1), y, .014), C("3A3F46"), 0, 1)


def v5_lane_check(name, counter_back, back_front, x=0.0, w=1.5):
    lane = back_front - counter_back
    LANEPOS[name] = (x, (counter_back + back_front) / 2, w)
    LANELOG[name] = round(lane, 3)
    return lane


LANELOG = {}
BOARDLOG = {}
LANEPOS = {}       # key -> (x, y, width) of the lane centre, for the top views


# ================================================================================================ AÇOUGUE machines (burgundy enamel)
def a5_grinder(acc, loc, yaw=0, acc_col=None):
    """Moedor de carne in burgundy enamel: rounded motor body with vent slots, chrome head, feed tray, switches."""
    A, A2 = acc_col or ACCENT["acougue"]
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.3, .45, .3), (0, .05, .15), C(A), .07, 3)
    rbox(X, (.32, .47, .03), (0, .05, .015), C(GRAPH), .01, 1)
    for k in range(4):
        rbox(X, (.006, .2, .03), (.152, .08, .1 + k * .045), C("4A1219"), .003, 1)
    rbox(X, (.2, .02, .08), (0, -.18, .2), C(CHROME), .01, 1)
    lathe(X, [(0, 0), (.075, 0), (.08, .02), (.075, .22), (0, .22)], (0, -.12, .25), C(CHROME), 14, 0, rot=(90, 0, 0))
    lathe(X, [(0, 0), (.09, 0), (.09, .04), (0, .04)], (0, -.32, .25), C(CHROME), 16, 0, rot=(90, 0, 0))
    lathe(X, [(0, 0), (.07, 0)], (0, -.361, .25), C("8A9298"), 14, 0, rot=(90, 0, 0))
    for k in range(7):
        a = k * 2 * math.pi / 7
        lathe(X, [(0, 0), (.008, 0)], (.04 * math.cos(a), -.362, .25 + .04 * math.sin(a)), C("3A3F45"), 6, 0, rot=(90, 0, 0))
    lathe(X, [(.04, 0), (.05, .12)], (0, -.18, .3), C(CHROME), 12, 0, cap_top=False, cap_bottom=False)
    rbox(X, (.42, .38, .03), (0, -.18, .43), C(STEEL), .01, 2)
    for s in (-1, 1):
        rbox(X, (.42, .02, .05), (0, -.18 + s * .19, .45), C(STEEL), .005, 1)
        rbox(X, (.02, .38, .05), (s * .21, -.18, .45), C(STEEL), .005, 1)
    sd_ground(X, (0, -.18, .445), .24, .2)
    for k, col in enumerate(("37A04A", "C0392B")):
        lathe(X, [(0, 0), (.018, 0), (.018, .015), (0, .02)], (.1 - k * .05, -.17, .2), C(col), 8, 0, rot=(90, 0, 0))
    T = sd_tray(X, (0, -.42, 0), .26, .18, 0, WHITE)
    sd_ground(T, (0, 0, .006), .2, .12)


def a5_bandsaw(acc, loc, yaw=0):
    """Serra fita in burgundy enamel: cabinet with a hinged door and vent louvres, stainless sliding table, tall
    column, rounded top wheel housing with a chrome badge disc, visible blade and guard, stop buttons, pusher."""
    A, A2 = ACCENT["acougue"]
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.6, .55, .85), (0, 0, .425), C(A), .04, 3)
    rbox(X, (.62, .57, .06), (0, 0, .03), C(GRAPH), .01, 1)
    rbox(X, (.5, .012, .62), (0, -.277, .47), C(A2), .02, 2)
    for k in range(5):
        rbox(X, (.3, .006, .012), (0, -.285, .62 - k * .04), C("4A1219"), .003, 1)
    rbox(X, (.03, .02, .12), (.2, -.29, .45), C(CHROME), .008, 1)
    rbox(X, (.7, .65, .03), (0, -.02, .9), C(STEEL), .01, 2)
    for s in (-1, 1):
        rbox(X, (.03, .65, .02), (s * .36, -.02, .92), C(CHROME), .005, 1)
    rbox(X, (.16, .2, 1.05), (-.2, .18, 1.42), C(A), .04, 2)
    rbox(X, (.62, .3, .5), (0, .1, 1.97), C(A), .14, 4)
    lathe(X, [(0, 0), (.07, 0), (.07, .012), (0, .016)], (0, -.055, 1.97), C(CHROME), 16, 0, rot=(90, 0, 0))
    rbox(X, (.6, .02, .05), (0, -.05, 1.76), C(GRAPH), .01, 1)
    rbox(X, (.012, .012, .82), (.12, -.04, 1.33), C("D8DDE2"), 0, 1)
    rbox(X, (.08, .06, .35), (.12, -.04, 1.54), C(STEEL), .01, 1)
    for k, col in enumerate(("C0392B", "37A04A")):
        lathe(X, [(0, 0), (.025, 0), (.025, .02), (0, .025)], (-.22, -.08, 1.2 + k * .1), C(col), 10, 0, rot=(90, 0, 0))
    rbox(X, (.2, .02, .14), (-.05, -.15, .99), C(CHROME), .01, 1)
    tube(X, [(-.05, -.16, 1.06), (-.05, -.26, 1.1)], .012, C(INK), 6)
    sd_tbone(X, (.15, -.1, .915), 1.1, 0, 2)


def a5_label_scale(acc, loc, yaw=0, col=None):
    """Balança etiquetadora: accent body, steel platter, tower with customer display and operator screen."""
    A = col or ACCENT["acougue"][0]
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.38, .45, .12), (0, 0, .06), C(A), .035, 3)
    rbox(X, (.34, .3, .015), (0, -.05, .128), C(CHROME), .01, 2)
    rbox(X, (.3, .12, .2), (0, .17, .22), C(A), .035, 3)
    rbox(X, (.08, .08, .25), (0, .17, .43), C(GRAPH), .02, 2)
    rbox(X, (.34, .06, .2), (0, .17, .62), C(GRAPH), .02, 2, rot=(-15, 0, 0))
    rbox(X, (.29, .01, .15), (0, .135, .625), "E_DDF4FF", .005, 1, rot=(-15, 0, 0))
    rbox(X, (.22, .04, .05), (0, .23, .66), C(GRAPH), .01, 1)
    rbox(X, (.18, .006, .03), (0, .253, .66), "E_FF4A3A", 0, 1)
    rbox(X, (.08, .004, .07), (.1, .107, .2), C(WHITE), .002, 1, rot=(-25, 0, 0))


def a5_sealer(acc, loc, yaw=0):
    A, A2 = ACCENT["acougue"]
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.5, .45, .22), (0, 0, .11), C(A), .04, 3)
    lathe(X, [(.19, 0), (.19, .04), (.15, .08), (0, .09)], (0, .02, .22), GLASS, 18, 1, cap_bottom=False)
    rbox(X, (.42, .02, .08), (0, -.226, .11), C(GRAPH), .01, 1)
    for k in range(4):
        rbox(X, (.03, .012, .03), (-.12 + k * .08, -.236, .11), C(WHITE if k else "37A04A"), .004, 1)
    rbox(X, (.3, .3, .02), (0, .02, .225), C("5A6066"), .005, 1)


def a5_block_table(acc, x, yback, w, d=.55, h=.9, seed=0):
    """Worktable with a thick end-grain butcher-block top, stainless frame and an undershelf of stacked trays and a
    burgundy tote. yback = its back edge."""
    A, A2 = ACCENT["acougue"]
    y = yback - d / 2
    rbox(acc, (w, d, .08), (x, y, h - .04), "T_IK_ButcherBlock", .012, 2, uv=2.5)
    rbox(acc, (w + .01, d + .01, .02), (x, y, h - .09), C(STEEL), .005, 1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(acc, [(x + sx * (w / 2 - .04), y + sy * (d / 2 - .04), 0), (x + sx * (w / 2 - .04), y + sy * (d / 2 - .04), h - .1)], .02, C(STEEL), 8)
            lathe(acc, [(0, 0), (.028, 0), (.028, .02), (0, .02)], (x + sx * (w / 2 - .04), y + sy * (d / 2 - .04), 0), C(GRAPH), 8, 0)
    rbox(acc, (w - .06, d - .06, .02), (x, y, .22), C(STEEL), .005, 1)
    rnd = random.Random(seed)
    for k in range(int((w - .1) / .3)):
        tx = x - w / 2 + .2 + k * .3
        if k % 2 == 0:
            for j in range(4):
                rbox(acc, (.24, .18, .02), (tx, y, .245 + j * .022), C(WHITE), .006, 1)
        else:
            open_box(acc, .26, .36, .18, (tx, y, .23), C(A), .012, .01)
    return y


def a5_cepo(acc, loc, seed=0):
    """Cepo: a round end-grain butcher block on a burgundy three-leg stand, a cleaver stuck in it, a cut on top."""
    A, A2 = ACCENT["acougue"]
    x, y, _ = loc
    lathe(acc, [(0, .62), (.27, .62), (.28, .64), (.28, .86), (.27, .88), (0, .88)], (x, y, 0), "T_IK_ButcherBlock", 20, 0)
    lathe(acc, [(.26, .6), (.3, .6), (.3, .64), (.26, .64)], (x, y, 0), C(A), 20, 0, cap_top=False, cap_bottom=False)
    for k in range(3):
        a = k * 2 * math.pi / 3 + .4
        tube(acc, [(x + .2 * math.cos(a), y + .2 * math.sin(a), .61), (x + .3 * math.cos(a), y + .3 * math.sin(a), 0)], .025, C(A), 8)
        lathe(acc, [(0, 0), (.035, 0), (.035, .02), (0, .02)], (x + .3 * math.cos(a), y + .3 * math.sin(a), 0), C(GRAPH), 8, 0)
    sd_knife(acc, (x + .06, y - .02, .91), (0, -80, 30), .2, "cleaver")
    sd_steak(acc, (x - .08, y + .04, .881), 1.0, 20, "steak", seed)


def a5_cabinet(acc, x, yback, w=.6, d=.45, h=.9):
    """Low burgundy cabinet with stainless top and two doors (paper, bags, labels)."""
    A, A2 = ACCENT["acougue"]
    y = yback - d / 2
    rbox(acc, (w, d, h - .03), (x, y, (h - .03) / 2), C(A), .03, 2)
    rbox(acc, (w + .02, d + .02, .03), (x, y, h - .015), C(STEEL), .008, 1)
    for s in (-1, 1):
        rbox(acc, (w / 2 - .03, .01, h - .2), (x + s * w / 4, y - d / 2 - .004, h / 2), C(A2), .012, 1)
        rbox(acc, (.012, .02, .12), (x + s * .03, y - d / 2 - .015, h * .6), C(CHROME), .005, 1)
    rbox(acc, (w, d, .06), (x, y, .03), C(GRAPH), .01, 1)
    return y


# ================================================================================================ AÇOUGUE (round 5)
def acougue_v5(acc, tier):
    W, D = V5_SIZES["acougue"][tier - 1]
    ye, yw, yf = v5_planes(D)
    v5_back_wall(acc, W, D)
    wd = WD(acc)
    A, A2 = ACCENT["acougue"]
    key = "sector-acougue_T%d" % tier
    if tier == 1:
        # balcão de atendimento: counter, butcher-block table with grinder + label scale, burgundy cabinet with the
        # paper roll; on the wall: hook rail (hams, sausages), knife strip, one menu board
        cy = -D / 2 + .05 + .95 / 2
        v4_service_counter(acc, 1.75, cy, 0)
        ty = a5_block_table(acc, -.45, yf, 1.3, .55, seed=1)
        a5_grinder(acc, (-.85, ty - .02, .9), 0)
        a5_label_scale(acc, (-.2, ty, .9), 0)
        sd_knife(acc, (.1, ty - .1, .905), (0, 0, 10), .2, "cleaver")
        a5_cabinet(acc, .85, yf, .6, .45)
        sd_paper_roll(acc, (.85, yf - .25, .9), 0, .45, "F4F2EC")
        v5_mat(acc, 0, (cy + .95 / 2 + yf - .55) / 2, 1.6, .5)
        v5_lane_check(key, cy + .95 / 2, yf - .55, 0, 1.6)
        v5_hook_rail(wd, -1.15, -.1, D, 1.82, 4, ("ham", "sausage", "sausage", "ham"))
        v5_menu_board(wd, .55, 2.32, D, 1, .78, False, 0)
        v5_knife_strip(wd, .55, D, 1.36, 4, .5)
    elif tier == 2:
        # açougue: full counter (ticket dispenser in front), burgundy band saw, butcher-block table (grinder,
        # sealer, label scale), cold-room door; wall: two-panel menu board with the ticket counter, short hook rail
        cy = -D / 2 + .30 + .95 / 2
        v4_service_counter(acc, 2.75, cy, 1)
        v4_ticket_dispenser(acc, (1.25, -D / 2 + .14, 0), -20)
        a5_bandsaw(acc, (-1.25, yf - .33, 0), 0)
        ty = a5_block_table(acc, -.2, yf, 1.3, .55, seed=2)
        a5_grinder(acc, (-.6, ty - .02, .9), 0)
        a5_sealer(acc, (-.05, ty, .9), 0)
        a5_label_scale(acc, (.35, ty, .9), 0)
        v5_mat(acc, -.25, (cy + .95 / 2 + yf - .65) / 2, 2.4, .55)
        v5_lane_check(key, cy + .95 / 2, yf - .65, -.25, 2.4)
        v5_cold_door(wd, 1.1, D, .85, 2.05)
        v5_menu_board(wd, -.2, 2.32, D, 2, .68, True, 0)
        v5_hook_rail(wd, -.85, -.15, D, 1.52, 3, ("sausage", "ham", "sausage"))
    else:
        # açougue completo: counter + self-service cooler, band saw, two grinders, sealer, label scale, cepo,
        # cold-room door; wall: three-panel menu strip with the ticket counter, hook rail, knife strip
        cy = -D / 2 + .30 + .95 / 2
        Xc = Xf(acc, (-.62, 0, 0))
        v4_service_counter(Xc, 2.65, cy, 2)
        a5_selfservice(acc, W / 2 - .66, -D / 2 + .42, 1.25, .78, 1.95, 1)
        v4_ticket_dispenser(acc, (-1.7, -D / 2 + .14, 0), 20)
        a5_bandsaw(acc, (-1.6, yf - .33, 0), 0)
        ty = a5_block_table(acc, -.62, yf, 1.4, .55, seed=3)
        a5_grinder(acc, (-1.1, ty - .02, .9), 0)
        a5_grinder(acc, (-.72, ty - .02, .9), 0)
        a5_sealer(acc, (-.2, ty, .9), 0)
        ty2 = a5_block_table(acc, .5, yf, .7, .55, seed=4)
        a5_label_scale(acc, (.62, ty2, .9), 0)
        sd_paper_roll(acc, (.3, ty2 + .05, .92), 90, .3, "F4F2EC")
        a5_cepo(acc, (1.55, -.1, 0), 3)
        v5_mat(acc, -.62, (cy + .95 / 2 + yf - .65) / 2, 2.5, .6)
        v5_lane_check(key, cy + .95 / 2, yf - .65, -.62, 2.5)
        v5_cold_door(wd, 1.5, D, .8, 2.05)
        v5_menu_board(wd, -.14, 2.32, D, 3, .66, True, 0)
        v5_hook_rail(wd, -1.2, -.15, D, 1.5, 4, ("ham", "sausage", None, "ham"))
        v5_knife_strip(wd, .5, D, 1.38, 3, .4)


def a5_selfservice(acc, x, y, W=1.25, D=.75, H=1.95, seed=0):
    """The round-4 self-service cooler with a burgundy interior back instead of white."""
    v4_selfservice(acc, x, y, W, D, H, seed)
    rbox(acc, (W - .1, .01, H - .47), (x, y + D / 2 - .065, .45 + (H - .45) / 2), C(ACCENT["acougue"][0]), .004, 1)


v5_tiers("acougue")
BUILDERS["sector-acougue"] = _logged("acougue", acougue_v5)


# ================================================================================================ previews
MS_TEX = os.path.join(REPO, "unity", "CheckoutSimulator", "Assets", "Art", "MarketStages", "Textures")
WALLS_QA = "walls"


def ms_material(name, tex, tint=None):
    """Preview-only material with the market's own texture (MarketStages/Textures)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    t = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(MS_TEX, tex + "_albedo.png"), check_existing=True)
    t.image.alpha_mode = "CHANNEL_PACKED"          # the game's albedos keep a mask in alpha; colour is straight RGB
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = .6
    return m


def market_wall(x0, x1, y_edge, name="MW wall"):
    """Replica of CheckoutMarketShell.Wall (a full-height interior run), facing -Y, for the previews: cream plaster
    face 5 cm behind the clear-floor edge, navy fluted wainscot to 0.95 m (3 cm proud), gold rail 7 cm (5 cm proud,
    its face = the clear-floor edge), gold coping on top; height 2.49 m. Materials use the game's textures."""
    ms_material("MW_Plaster", "MS_Plaster"); ms_material("MW_Navy", "MS_NavyPanel"); ms_material("MW_Gold", "MS_Gold")
    acc = Acc(name)
    top, thick = MARKET_WALL_H, .5
    L = x1 - x0
    cx = (x0 + x1) / 2
    pf = y_edge + .05                                       # plaster face
    rbox(acc, (L, thick, top - .02), (cx, pf + thick / 2, (top - .02) / 2), "MW_Plaster", .01, 1, uv=.5)
    rbox(acc, (L, .04, .95), (cx, pf - .03 + .02, .475), "MW_Navy", .006, 1, uv=1 / .9)
    rbox(acc, (L, .06, .07), (cx, pf - .05 + .03, .95 + .035), "MW_Gold", .008, 1, uv=.5)
    rbox(acc, (L + .12, thick + .14, .13), (cx, pf - .06 + (thick + .14) / 2, top + .065), "MW_Gold", .01, 1, uv=.5)
    c = coll("FT5 context", coll("Fixture tiers"))
    return acc.realize(c)


def market_floor(x0, x1, y0, y1, prints=(), name="MW floor"):
    ms_material("MW_Floor", "MS_FloorTiles")
    acc = Acc(name)
    rbox(acc, (x1 - x0, y1 - y0, .02), ((x0 + x1) / 2, (y0 + y1) / 2, -.011), "MW_Floor", .005, 1, uv=.5)
    for (cx, cy, w, d) in prints:
        for s in (-1, 1):
            rbox(acc, (w, .02, .004), (cx, cy + s * (d / 2 - .01), .002), C("3FBF6A"), 0, 1)
            rbox(acc, (.02, d, .004), (cx + s * (w / 2 - .01), cy, .002), C("3FBF6A"), 0, 1)
    c = coll("FT5 context", coll("Fixture tiers"))
    return acc.realize(c)


def place_piece(sid, tier, loc, tag, back=True):
    """Builds one sector piece at loc (its footprint centre) into collection 'FT5 <tag>'; back=False hides the
    'Back Wall' object (as the game does against a market wall)."""
    kind = "sector-" + sid
    c = coll("FT5 " + tag, coll("Fixture tiers"))
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    acc = Acc("%s_T%d" % (kind, tier))
    BUILDERS[kind][tier - 1](acc)
    root = bpy.data.objects.new("%s %s" % (tag, kind), None)
    c.objects.link(root)
    objs = acc.realize(c)
    for o in objs:
        grp = o.name.split(".")[0]
        o.name = "%s %s" % (tag, grp)
        o.parent = root
        if grp == "Back Wall":
            o.hide_render = o.hide_viewport = not back
        if grp == "Wall Dressing":          # render-only: the name as the game writes it
            pm = name_preview_material(sid, tier)
            for k, mm in enumerate(o.data.materials):
                if mm and mm.name == "E_NamePanel" and pm:
                    o.data.materials[k] = pm
    root.location = loc
    return root, objs


def name_preview_material(sid, tier):
    path = os.path.join(PREVIEW, "FT_NamePreview_%s_T%d.png" % (sid, tier))
    if not os.path.exists(path):
        return None
    return v4_screen_material("FT5_NamePreview_%s_T%d" % (sid, tier), os.path.basename(path))


def staff_marker(x, y, name):
    """Top-view footprint of a staff character (STAFF_W wide, orange, translucent) for the lane check."""
    acc = Acc(name)
    lathe(acc, [(0, 0), (STAFF_W / 2, 0), (STAFF_W / 2, .02), (0, .02)], (x, y, .03), "E_F28C28", 24, 0)
    lathe(acc, [(0, 0), (STAFF_W / 2 * .55, 0), (STAFF_W / 2 * .55, .025), (0, .025)], (x, y + .02, .05), C("FBF8F1"), 16, 0)
    c = coll("FT5 context", coll("Fixture tiers"))
    return acc.realize(c)


def clear_v5_previews():
    for cname in [c.name for c in bpy.data.collections if c.name.startswith("FT5 ")]:
        c = bpy.data.collections[cname]
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        if m.users == 0:
            bpy.data.meshes.remove(m)


V5_AT = {"acougue": (200.0, -200.0), "padaria": (200.0, -220.0), "queijaria": (200.0, -240.0), "peixaria": (200.0, -260.0),
         "sorvetes": (200.0, -280.0), "adega": (200.0, -300.0), "sucos": (200.0, -320.0)}
FREE_DY = -8.0                 # the freestanding row stands this far in front of the wall row


def v5_scene(sid):
    """Flush row (pieces against a replica of the market wall, Back Wall hidden) and freestanding row (panel shown)."""
    clear_v5_previews()
    X0, Y0 = V5_AT[sid]
    sizes = V5_SIZES[sid]
    gap = 1.0
    total = sum(w for w, d in sizes) + gap * 2
    xs, x = [], X0 - total / 2
    for w, d in sizes:
        xs.append(x + w / 2); x += w + gap
    prints_flush = [(xs[i], Y0 - sizes[i][1] / 2, sizes[i][0], sizes[i][1]) for i in range(3)]
    prints_free = [(xs[i], Y0 + FREE_DY, sizes[i][0], sizes[i][1]) for i in range(3)]
    market_wall(X0 - total / 2 - 1.5, X0 + total / 2 + 1.5, Y0)
    market_floor(X0 - total / 2 - 2, X0 + total / 2 + 2, Y0 - 3.6, Y0 + .1, prints_flush, "MW floor flush")
    market_floor(X0 - total / 2 - 2, X0 + total / 2 + 2, Y0 + FREE_DY - 3.0, Y0 + FREE_DY + 3.0, prints_free, "MW floor free")
    for i in range(3):
        place_piece(sid, i + 1, (xs[i], Y0 - sizes[i][1] / 2, 0), "%s T%d flush" % (sid, i + 1), back=False)
        place_piece(sid, i + 1, (xs[i], Y0 + FREE_DY, 0), "%s T%d free" % (sid, i + 1), back=True)
    return xs


def v5_iso(target, w, name, elev=50, yaw=-20, size=(1400, 1100), scale=1.5, half=4.0, ycen=None):
    e, a = math.radians(elev), math.radians(yaw)
    isolate(ycen if ycen is not None else target[1], half)
    camera(target, (math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)), 30, 40, ortho=max(w * scale, 4.3))
    os.makedirs(os.path.join(QA, WALLS_QA), exist_ok=True)
    return render(os.path.join(WALLS_QA, name), size)


def v5_previews(sid, tiers=(1, 2, 3)):
    """Game-camera views (flush and freestanding), board close-ups and top views with the staff footprint."""
    for im in bpy.data.images:
        if im.name.startswith(("FT_PricePreview", "FT_NamePreview", "FT_TicketPreview")):
            im.reload()
    v4_materials(sid)
    v4_name_material()
    xs = v5_scene(sid)
    X0, Y0 = V5_AT[sid]
    bpy.context.view_layer.update()
    out = []
    for t in tiers:
        w, d = V5_SIZES[sid][t - 1]
        x = xs[t - 1]
        key = "sector-%s_T%d" % (sid, t)
        lx, ly, lw = LANEPOS.get(key, (0, 0, 1))
        staff_marker(x + lx, Y0 + FREE_DY + ly, "Staff %s" % key)
        lane_caption(("faixa %.2f m  /  pessoa %.2f m" % (LANELOG.get(key, 0), STAFF_W)).replace(".", ","), (x, Y0 + FREE_DY - d / 2 - .35, .004))
        out.append(v5_iso((x, Y0 - d / 2 + .25, 1.35), w, "sector-%s_T%d_flush_gamecam" % (sid, t), ycen=Y0 - d / 2, half=d / 2 + .9))
        out.append(v5_iso((x, Y0 + FREE_DY + .25, 1.35), w, "sector-%s_T%d_free_gamecam" % (sid, t), ycen=Y0 + FREE_DY, half=d / 2 + .9))
        # top view with the staff footprint in the lane (freestanding piece)
        isolate(Y0 + FREE_DY, d / 2 + .9)
        camera((x, Y0 + FREE_DY - .1, 0), (0, -.001, 1), 20, 40, ortho=max(w, d) * 1.25)
        out.append(render(os.path.join(WALLS_QA, "sector-%s_T%d_topdown" % (sid, t)), (1200, 1100)))
        # menu board close-up (freestanding piece, preview prices)
        for k, (p, bw, bh) in enumerate(BOARDLOG.get(key, [])[:1]):
            bx, by_, bz = p
            isolate(Y0 + FREE_DY, d / 2 + .9)
            camera((x + bx, Y0 + FREE_DY + by_, bz), (-.12, -1, .18), max(bw, bh) * 1.25 + .9, 45)
            out.append(render(os.path.join(WALLS_QA, "sector-%s_T%d_board" % (sid, t)), (1400, 900)))
    return out


def lane_caption(value, loc):
    acc = Acc("Lane caption")
    text(acc, value, .15, loc, C(NAVY), .004, rot=(-90, 0, 0), bevel=0)
    c = coll("FT5 context", coll("Fixture tiers"))
    return acc.realize(c)
