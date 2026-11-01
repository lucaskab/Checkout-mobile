"""Round 5, the other six sectors (exec'd after sector_v5.py into the same namespace): padaria, frios e laticínios
(queijaria), peixaria, sorveteria, adega and bebidas (sucos art), in the açougue v5 style Lucas approved: market-wall
back panel, wall dressing, one integrated menu board, one accent family per sector, a staff lane >= STAFF_W + .25.
"""


class RC:
    """Recolour proxy: parts added through it swap material keys (mp: old key -> new key)."""

    def __init__(self, acc, mp):
        self.acc, self.mp = acc, mp

    def add(self, bm, key, grp="Body", smooth=True):
        self.acc.add(bm, self.mp.get(key, key), grp, smooth)


def T1C(D):
    return -D / 2 + .05 + .95 / 2          # T1 counter centre (front margin 5 cm)


def T23C(D):
    return -D / 2 + .30 + .95 / 2          # T2 / T3 counter centre (room for the queue and the ticket stand)


def v5_table(acc, x, yback, w, d=.55, top=WOOD_L, frame=STEEL, under=None, seed=0, h=.9):
    """Worktable with a thick top (texture or colour key), a frame and an undershelf; under(acc, x, y, w, d) fills
    the shelf. Returns its centre y."""
    y = yback - d / 2
    rbox(acc, (w, d, .06), (x, y, h - .03), top, .012, 2, uv=2)
    rbox(acc, (w + .01, d + .01, .02), (x, y, h - .07), C(frame) if len(frame) == 6 else frame, .005, 1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(acc, [(x + sx * (w / 2 - .04), y + sy * (d / 2 - .04), 0), (x + sx * (w / 2 - .04), y + sy * (d / 2 - .04), h - .08)], .02, C(frame) if len(frame) == 6 else frame, 8)
            lathe(acc, [(0, 0), (.028, 0), (.028, .02), (0, .02)], (x + sx * (w / 2 - .04), y + sy * (d / 2 - .04), 0), C(GRAPH), 8, 0)
    rbox(acc, (w - .06, d - .06, .02), (x, y, .22), C(frame) if len(frame) == 6 else frame, .005, 1)
    if under:
        under(acc, x, y, w, d)
    return y


def v5_shelf(acc, x, w, D, z, key=WOOD_L, depth=.22):
    """Wall shelf on two stainless brackets (wall dressing). Returns the frame on its top (y at the shelf centre)."""
    ye, yw, _ = v5_planes(D)
    y = yw - .01 - depth / 2
    rbox(acc, (w, depth, .035), (x, y, z), key, .008, 2, uv=2)
    for s in (-1, 1):
        bx = x + s * (w / 2 - .08)
        rbox(acc, (.03, ye - .003 - (yw - .01), .22), (bx, (ye - .003 + yw - .01) / 2, z - .1), C(CHROME), .004, 1)
        tube(acc, [(bx, yw - .012, z - .2), (bx, y - depth / 2 + .04, z - .02)], .008, C(CHROME), 5)
    return Xf(acc, (x, y, z + .0175))


# ================================================================================================ PADARIA (terracotta, warm wood)
def p5_deck_oven(acc, x, yback, w=1.1, d=.65, decks=3, seed=0):
    """Forno de lastro: terracotta-tiled body on a terracotta enamel stand with doors, brick-faced front bands, three
    deck doors with lit windows (warm glow and loaves inside), chrome handles, a domed terracotta crown, a copper hood
    and flue."""
    A, A2 = ACCENT["padaria"]
    y = yback - d / 2
    yfr = y - d / 2
    rbox(acc, (w, d, .38), (x, y, .19), C(A), .03, 2)
    for s in (-1, 1):
        rbox(acc, (w / 2 - .04, .012, .28), (x + s * w / 4, yfr - .004, .2), C(A2), .012, 1)
        rbox(acc, (.1, .02, .02), (x + s * .06, yfr - .014, .3), C(CHROME), .006, 1)
    rbox(acc, (w + .02, d + .02, .03), (x, y, .395), C(GRAPH), .008, 1)
    hd = .3
    z0 = .41
    rbox(acc, (w, d - .02, decks * hd + .04), (x, y + .01, z0 + (decks * hd + .04) / 2), "T_IK_Terracotta", .02, 2, uv=2.5)
    for k in range(decks):
        zc = z0 + .02 + hd / 2 + k * hd
        rbox(acc, (w + .01, .03, .07), (x, yfr - .005, zc - hd / 2 + .02), BRICK, .006, 1, uv=3)
        fr = frame_bm(w - .1, hd - .1, .03, .02, .03, 4)
        place(fr, (x, yfr - .03, zc + .015)); acc.add(fr, C(CHROME))
        rbox(acc, (w - .17, .008, hd - .17), (x, yfr - .004, zc + .015), "E_FF9A3C", .003, 1)
        for j in range(int((w - .2) / .2)):
            sd_loaf(acc, (x - (w - .2) / 2 + .1 + j * .2, yfr - .02, zc - hd / 2 + .075), .15, .06, .06, 0, "loaf", j + k + seed)
        rbox(acc, (w - .16, .006, hd - .16), (x, yfr - .042, zc + .015), GLASS, .003, 1)
        tube(acc, [(x - w / 2 + .1, yfr - .07, zc + hd / 2 - .045), (x + w / 2 - .1, yfr - .07, zc + hd / 2 - .045)], .012, C(CHROME), 8)
        rbox(acc, (.07, .012, .04), (x + w / 2 - .09, yfr - .012, zc - hd / 2 + .06), C(GRAPH), .006, 1)
        rbox(acc, (.04, .004, .015), (x + w / 2 - .09, yfr - .019, zc - hd / 2 + .06), "E_FF4A3A", 0, 1)
    zt = z0 + decks * hd + .04
    rbox(acc, (w + .02, .035, .08), (x, yfr - .01, zt - .03), BRICK, .006, 1, uv=3)
    bm = rbox_bm((w, d - .04, .16), .07, 3)
    uv_box(bm, 2.5); place(bm, (x, y + .01, zt + .06)); acc.add(bm, "T_IK_Terracotta")
    rbox(acc, (w * .8, d * .7, .1), (x, y + .03, zt + .19), C("B87333"), .04, 3)
    lathe(acc, [(.07, 0), (.07, .5)], (x + w * .25, y + .1, zt + .22), C("B87333"), 12, 0, cap_top=False, cap_bottom=False)
    lathe(acc, [(.085, 0), (.085, .03)], (x + w * .25, y + .1, zt + .5), C(GRAPH), 12, 0, cap_top=False)
    rbox(acc, (w - .1, .01, .015), (x, yfr - .02, z0 + .01), "E_FFB25A", .003, 1)
    return y


def p5_mixer(acc, loc, col=None, yaw=0):
    """Batedeira planetária in the accent colour: base, column, tilting head, stainless bowl of dough, dough hook."""
    col = col or ACCENT["padaria"][1]
    X = Xf(acc, loc, (0, 0, yaw))
    rbox(X, (.28, .38, .06), (0, 0, .03), C(col), .03, 3)
    rbox(X, (.13, .13, .42), (0, .12, .27), C(col), .05, 3)
    rbox(X, (.17, .38, .15), (0, .0, .52), C(col), .07, 3)
    lathe(X, [(0, 0), (.06, 0), (.06, .02), (0, .03)], (0, -.18, .52), C(CHROME), 10, 0, rot=(90, 0, 0))
    rbox(X, (.172, .1, .02), (0, .05, .46), C(CHROME), .008, 1)
    lathe(X, [(0, 0), (.07, 0), (.11, .05), (.125, .17), (.12, .17)], (0, -.06, .07), INOX, 16, 0, cap_top=False)
    blob(X, (.1, .1, .05), (0, -.06, .2), C("F0DEB8"), 2, .06, 3)
    tube(X, [(0, -.06, .44), (0, -.06, .3), (.02, -.08, .22)], .01, C(CHROME), 6)
    tube(X, [(.09, .12, .3), (.14, .12, .3)], .01, C(CHROME), 5)


def p5_bread_rack(acc, x, yback, w=.6, d=.45, h=1.6, seed=0):
    """Golden-wood bread rack: honey uprights, four tilted shelves of loaves, rolls and croissants with terracotta lips,
    a tall wicker basket of baguettes on top."""
    A, A2 = ACCENT["padaria"]
    y = yback - d / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            rbox(acc, (.045, .045, h), (x + sx * (w / 2 - .025), y + sy * (d / 2 - .025), h / 2), WOOD_L, .01, 1)
    rbox(acc, (w, .02, h - .1), (x, y + d / 2 - .01, h / 2), WOOD_L, .006, 1, uv=2)
    for i in range(4):
        z = .22 + i * (h - .45) / 4
        S = Xf(acc, (x, y, z), (12, 0, 0))
        rbox(S, (w - .08, d - .06, .02), (0, 0, 0), WOOD_L, .006, 1, uv=2)
        rbox(S, (w - .08, .02, .05), (0, -(d - .06) / 2, .02), C(A), .006, 1)
        n = int((w - .1) / .17)
        for j in range(n):
            px_ = -(w - .1) / 2 + (j + .5) * (w - .1) / n
            m = (i + j + seed) % 3
            if m == 0:
                sd_loaf(S, (px_, 0, .012), .2, .1, .08, 90, "loaf", i + j)
            elif m == 1:
                for q in range(3):
                    sd_roll(S, (px_, -.12 + q * .12, .012), .04, i * 3 + q)
            else:
                for q in range(2):
                    sd_croissant(S, (px_, -.08 + q * .16, .012), .75, 90)
    open_box(acc, w - .1, d - .12, .22, (x, y, h), WICKER, .014, .008, 3)
    for k in range(5):
        sd_baguette(acc, (x - .16 + k * .08, y - .04 + (k % 2) * .06, h + .05), .5, .026, 0, -75 + (k % 3) * 6, k)


def p5_wicker_wall(acc, x0, x1, D, z, seed=0):
    """Wicker basket wall (wall dressing): a honey-wood rail on standoffs with baskets hung tilted towards the
    customer, full of loaves, rolls and standing baguettes."""
    ye, yw, _ = v5_planes(D)
    rbox(acc, (x1 - x0, .03, .06), ((x0 + x1) / 2, yw - .03, z + .16), WOOD_L, .008, 1, uv=2)
    for xx in (x0 + .06, x1 - .06):
        standoff(acc, xx, z + .16, yw - .045, ye, .03, .05)
    n = max(1, int((x1 - x0) / .32))
    for k in range(n):
        bx = x0 + (k + .5) * (x1 - x0) / n
        B = Xf(acc, (bx, yw - .14, z), (-28, 0, 0))
        open_box(B, .28, .2, .16, (0, 0, 0), WICKER, .012, .006, 2)
        tube(acc, [(bx - .1, yw - .035, z + .16), (bx - .1, yw - .1, z + .13)], .006, C(CHROME), 4)
        tube(acc, [(bx + .1, yw - .035, z + .16), (bx + .1, yw - .1, z + .13)], .006, C(CHROME), 4)
        m = (k + seed) % 3
        if m == 0:
            for q in range(4):
                sd_baguette(B, (-.09 + q * .06, .02, .02), .42, .022, 0, -82, k + q)
        elif m == 1:
            for q in range(2):
                sd_loaf(B, (0, -.045 + q * .09, .02), .2, .09, .07, 0, "loaf", k + q)
        else:
            for q in range(5):
                sd_roll(B, (-.08 + (q % 3) * .08, -.04 + (q // 3) * .08, .02), .037, k * 5 + q)


def p5_wood_counter(acc, W, y, seed=0):
    """The round-4 bread service counter clad in warm wood: plank front with a terracotta kick strip and a gold
    line, wooden side panels."""
    A, A2 = ACCENT["padaria"]
    X = v4_service_counter(acc, W, y, seed, fill=v4_bread_fill)
    yf_ = y - .475
    rbox(acc, (W - .02, .025, .66), (0, yf_ - .02, .47), WOOD_L, .01, 2, uv=1.6)
    n = int(W / .16)
    for k in range(n):
        rbox(acc, (.008, .006, .62), (-W / 2 + .08 + k * (W - .16) / max(1, n - 1), yf_ - .034, .47), C("8A5A30"), 0, 1)
    rbox(acc, (W - .02, .03, .12), (0, yf_ - .02, .08), C(A), .01, 1)
    rbox(acc, (W - .06, .008, .012), (0, yf_ - .036, .81), C(MW_GOLD), .003, 1)
    for s in (-1, 1):
        rbox(acc, (.025, .9, .82), (s * (W / 2 + .012), y, .43), WOOD_L, .008, 1, uv=1.6)
    return X


def p5_cake_cabinet(acc, x, y, W=1.25, D=.78, H=1.95):
    """Warm-wood refrigerated cake cabinet (glass doors, cakes and tarts)."""
    v4_glass_cabinet(acc, x, y, W, D, H, v4_cakes_fill, True, "8A5530", 4)
    rbox(acc, (W - .02, .015, .34), (x, y - D / 2 - .008, .2), WOOD_L, .006, 1, uv=1.6)
    rbox(acc, (W - .02, .015, .12), (x, y - D / 2 - .008, H - .08), WOOD_L, .006, 1, uv=1.6)


def p5_under_sacks(acc, x, y, w, d):
    for k in range(int((w - .1) / .32)):
        sd_sack(acc, (x - w / 2 + .2 + k * .32, y, .23), .62, 10 * k, k % 2 == 1, k)


def padaria_v5(acc, tier):
    W, D = V5_SIZES["padaria"][tier - 1]
    ye, yw, yf = v5_planes(D)
    v5_back_wall(acc, W, D)
    wd = WD(acc)
    A, A2 = ACCENT["padaria"]
    key = "sector-padaria_T%d" % tier
    if tier == 1:
        cy = T1C(D)
        p5_wood_counter(acc, 1.75, cy, 0)
        p5_deck_oven(acc, -.72, yf, 1.0, .55, 3, 0)
        ty = v5_table(acc, .3, yf, .9, .55, WOOD_L, A, p5_under_sacks, 1)
        p5_mixer(acc, (.6, ty, .9))
        sd_rolling_pin(acc, (.15, ty - .05, .9), 10)
        blob(acc, (.12, .09, .04), (0, ty, .93), C("F0DEB8"), 2, .06, 2)
        p5_bread_rack(acc, .98, yf, .45, .42, 1.55, 0)
        v5_lane(acc, key, D, cy + .475, -0.875, 0.875, [(-0.72, 1, 0.63), (0.3, 0.9, 0.55), (1, 0.45, 0.47)])
        v5_menu_board(wd, .3, 2.32, D, 1, .78, False, 0)
        p5_wicker_wall(wd, -.12, .42, D, 1.22, 0)
    elif tier == 2:
        cy = T23C(D)
        p5_wood_counter(acc, 2.75, cy, 1)
        v4_ticket_dispenser(acc, (1.25, -D / 2 + .14, 0), -20)
        p5_deck_oven(acc, -.95, yf, 1.2, .55, 3, 1)
        ty = v5_table(acc, .25, yf, 1.0, .55, WOOD_L, A, p5_under_sacks, 2)
        p5_mixer(acc, (.58, ty, .9))
        blob(acc, (.13, .1, .045), (-.05, ty, .93), C("F0DEB8"), 2, .06, 4)
        sd_rolling_pin(acc, (-.05, ty - .12, .9), -15)
        p5_bread_rack(acc, 1.2, yf, .6, .45, 1.6, 1)
        v5_lane(acc, key, D, cy + .475, -1.375, 1.375, [(-0.95, 1.2, 0.63), (0.25, 1, 0.55), (1.2, 0.6, 0.5)])
        v5_menu_board(wd, .2, 2.32, D, 2, .68, True, 0)
        p5_wicker_wall(wd, -.42, .34, D, 1.24, 1)
    else:
        cy = T23C(D)
        Xc = Xf(acc, (-.62, 0, 0))
        p5_wood_counter(Xc, 2.65, cy, 2)
        p5_cake_cabinet(acc, W / 2 - .66, -D / 2 + .42)
        v4_bread_bin(RC(acc, {C(NAVY): WOOD_L}), (W / 2 - .66, -D / 2 + 1.3, 0), .9, .5, 0, 3)
        v4_ticket_dispenser(acc, (-1.7, -D / 2 + .14, 0), 20)
        p5_deck_oven(acc, -1.2, yf, 1.5, .55, 3, 2)
        ty = v5_table(acc, .1, yf, 1.0, .55, WOOD_L, A, p5_under_sacks, 3)
        p5_mixer(acc, (.38, ty, .9))
        blob(acc, (.13, .1, .045), (-.18, ty, .93), C("F0DEB8"), 2, .06, 5)
        p5_bread_rack(acc, .95, yf, .6, .45, 1.6, 2)
        for k in range(2):
            sd_sack(acc, (1.5 + k * .3, yf - .25, 0), .9, 20 * k, k == 1, k)
        v5_lane(acc, key, D, cy + .475, -1.945, 0.705, [(-1.2, 1.5, 0.63), (0.1, 1, 0.55), (0.95, 0.6, 0.5), (1.62, 0.6, 0.5)])
        v5_menu_board(wd, .4, 2.32, D, 3, .66, True, 0)
        p5_wicker_wall(wd, -.42, .2, D, 1.24, 2)


# ================================================================================================ FRIOS E LATICÍNIOS (butter yellow, wood)
def q5_slicer(acc, loc, yaw=0):
    A, A2 = ACCENT["queijaria"]
    sd_slicer(RC(acc, {C(STEEL): C(A), C(WHITE): C(A2), C(NAVY): C(GRAPH)}), loc, yaw)


def q5_under_wheels(acc, x, y, w, d):
    for k in range(int((w - .1) / .3)):
        sd_wheel(acc, (x - w / 2 + .2 + k * .3, y, .23), .12, .09, ["rind_wax", "parmesan", "rind_natural"][k % 3], 0, 0)


def q5_provolone_rail(acc, x0, x1, D, z, n=4):
    ye, yw, _ = v5_planes(D)
    tube(acc, [(x0, yw - .1, z), (x1, yw - .1, z)], .014, WOOD_D, 8)
    for xx in (x0 + .05, x1 - .05):
        tube(acc, [(xx, ye - .004, z), (xx, yw - .1, z)], .012, C(CHROME), 6)
        rbox(acc, (.05, .012, .07), (xx, yw - .006, z), C(CHROME), .004, 1)
    for k in range(n):
        sd_provolone(acc, x0 + .12 + k * (x1 - x0 - .24) / max(1, n - 1), yw - .1, z - .02, .8 - .08 * (k % 2), True)


def q5_wheel_shelf(acc, x, w, D, z, seed=0):
    S = v5_shelf(acc, x, w, D, z, WOOD_D, .24)
    n = max(1, int(w / .26))
    for k in range(n):
        px_ = -w / 2 + (k + .5) * w / n
        if (k + seed) % 2:
            sd_wedge(S, (px_, 0, 0), .11, .07, 50, "rind_natural", -100)
        else:
            sd_wheel(S, (px_, 0, 0), .1, .08, ["rind_wax", "parmesan"][k % 2], 0, 0)


def q5_yogurt_cabinet(acc, x, yback, w, d=.65):
    A, A2 = ACCENT["queijaria"]
    v4_glass_cabinet(acc, x, yback - d / 2, w, d, 1.95, v4_yogurt_fill, True, A, 4)


def queijaria_v5(acc, tier):
    W, D = V5_SIZES["queijaria"][tier - 1]
    ye, yw, yf = v5_planes(D)
    v5_back_wall(acc, W, D)
    wd = WD(acc)
    A, A2 = ACCENT["queijaria"]
    key = "sector-queijaria_T%d" % tier
    if tier == 1:
        cy = T1C(D)
        v4_service_counter(acc, 1.75, cy, 0, fill=v4_deli_fill)
        ty = v5_table(acc, -.55, yf, 1.2, .55, WOOD_L, A, q5_under_wheels, 1)
        q5_slicer(acc, (-.85, ty, .9), 0)
        a5_label_scale(acc, (-.3, ty, .9), 0, A)
        sd_wheel(acc, (-.05, ty - .05, .9), .1, .08, "parmesan", 40, -110, "parmesan")
        sd_wheel_rack(acc, .85, yf - .21, .7, 1.7, 4, .42, 1)
        v5_lane(acc, key, D, cy + .475, -0.875, 0.875, [(-0.55, 1.2, 0.55), (0.85, 0.7, 0.44)])
        v5_menu_board(wd, .1, 2.32, D, 1, .78, False, 0)
        q5_provolone_rail(wd, -1.15, -.35, D, 1.86, 3)
        q5_wheel_shelf(wd, .1, .55, D, 1.3, 0)
    elif tier == 2:
        cy = T23C(D)
        v4_service_counter(acc, 2.75, cy, 1, fill=v4_deli_fill)
        v4_ticket_dispenser(acc, (1.25, -D / 2 + .14, 0), -20)
        ty = v5_table(acc, -.7, yf, 1.6, .55, WOOD_L, A, q5_under_wheels, 2)
        q5_slicer(acc, (-1.2, ty, .9), 0)
        q5_slicer(acc, (-.65, ty, .9), 0)
        a5_label_scale(acc, (-.12, ty, .9), 0, A)
        sd_wheel_rack(acc, .55, yf - .21, .7, 1.7, 4, .42, 2)
        q5_yogurt_cabinet(acc, 1.25, yf, .65)
        v5_lane(acc, key, D, cy + .475, -1.375, 1.375, [(-0.7, 1.6, 0.55), (0.55, 0.7, 0.44), (1.25, 0.65, 0.68)])
        v5_menu_board(wd, -.62, 2.32, D, 2, .68, True, 0)
        q5_provolone_rail(wd, .22, .88, D, 2.08, 3)
    else:
        cy = T23C(D)
        Xc = Xf(acc, (-.62, 0, 0))
        v4_service_counter(Xc, 2.65, cy, 2, fill=v4_deli_fill)
        v4_glass_cabinet(acc, W / 2 - .66, -D / 2 + .42, 1.25, .78, 1.95, v4_deli_shelf_fill, False, A, 4)
        v4_ticket_dispenser(acc, (-1.7, -D / 2 + .14, 0), 20)
        ty = v5_table(acc, -1.0, yf, 1.95, .55, WOOD_L, A, q5_under_wheels, 3)
        q5_slicer(acc, (-1.62, ty, .9), 0)
        q5_slicer(acc, (-1.08, ty, .9), 0)
        a5_label_scale(acc, (-.5, ty, .9), 0, A)
        sd_wheel(acc, (-.2, ty - .05, .9), .1, .08, "rind_wax", 40, -110)
        sd_wheel_rack(acc, .55, yf - .21, .95, 1.7, 4, .42, 3)
        q5_yogurt_cabinet(acc, 1.5, yf, .95)
        v5_lane(acc, key, D, cy + .475, -1.945, 0.705, [(-1, 1.95, 0.55), (0.55, 0.95, 0.44), (1.5, 0.95, 0.68)])
        v5_menu_board(wd, -.93, 2.32, D, 3, .66, True, 0)
        q5_provolone_rail(wd, .12, .98, D, 2.08, 3)


# ================================================================================================ PEIXARIA (sea teal, ice, rope, crates)
def f5_ice_crates(acc, x, y, n=2, seed=0):
    """Stacked wooden fish crates, the top one heaped with crushed ice and fish."""
    for k in range(n):
        open_box(acc, .5, .36, .2, (x, y, k * .2), CRATE if k < n - 1 else WOOD, .015, .006, 2)
    sd_ice_bed(acc, .46, .32, (x, y, n * .2 - .12), 0, seed, .1)
    for j in range(2):
        sd_fish(acc, (x - .08 + j * .16, y, n * .2 - .02), .3, 80 + j * 20, ["fish_blue", "fish_red"][j], "Body", seed + j)


def f5_net(acc, x0, x1, D, z0, z1, seed=0):
    """Fishing net on the wall (wall dressing): rope frame on standoffs, a slack net mesh, two floats and an oar."""
    ye, yw, _ = v5_planes(D)
    y = yw - .03
    for xx in (x0, x1):
        standoff(acc, xx, z1 - .03, y - .01, ye, .03, .04)
    tube(acc, [(x0, y, z1), (x1, y, z1)], .012, ROPE, 6)
    n = int((x1 - x0) / .12)
    for k in range(n + 1):
        xx = x0 + k * (x1 - x0) / n
        sag = .05 * math.sin(math.pi * k / n)
        tube(acc, [(xx, y, z1), (xx + .02, y - .015, (z0 + z1) / 2 - sag), (xx, y - .02, z0 - sag)], .003, ROPE, 3)
    for j in range(1, 5):
        zz = z1 - j * (z1 - z0) / 5
        tube(acc, [(x0, y - .01, zz), ((x0 + x1) / 2, y - .02, zz - .05), (x1, y - .01, zz)], .003, ROPE, 3)
    sd_buoy(acc, (x0 + (x1 - x0) * .3, y - .07, z0 + .12), (90, 0, 20))
    sd_buoy(acc, (x0 + (x1 - x0) * .72, y - .07, z0 + .3), (90, 0, -30))


def f5_table_under(acc, x, y, w, d):
    for k in range(int((w - .1) / .32)):
        rbox(acc, (.26, .36, .1), (x - w / 2 + .2 + k * .32, y, .28), C(ACCENT["peixaria"][1]), .02, 2)


def peixaria_v5(acc, tier):
    W, D = V5_SIZES["peixaria"][tier - 1]
    ye, yw, yf = v5_planes(D)
    v5_back_wall(acc, W, D)
    wd = WD(acc)
    A, A2 = ACCENT["peixaria"]
    teal = RC(acc, {INOX: C(A), C(WHITE): C(A), C(NAVY): C(GRAPH)})
    key = "sector-peixaria_T%d" % tier
    if tier == 1:
        cy = T1C(D)
        v4_fish_fill_counter(acc, 1.75, cy, 1)
        v4_sink(acc, -.85, yf - .3, .7)
        ty = v5_table(acc, .2, yf, 1.0, .55, INOX, A, f5_table_under, 1)
        a5_label_scale(acc, (-.12, ty, .9), 0, A)
        sd_cutting_board(acc, (.35, ty - .02, .9), 0, .38, .28)
        sd_fish(acc, (.35, ty - .02, .925), .32, 0, "fish_blue")
        f5_ice_crates(acc, .95, yf - .2, 2, 1)
        v5_lane(acc, key, D, cy + .475, -0.875, 0.875, [(-0.85, 0.7, 0.62), (0.2, 1, 0.55), (0.95, 0.5, 0.4)])
        v5_menu_board(wd, .2, 2.32, D, 1, .78, False, 0)
        v5_knife_strip(wd, .48, D, 1.36, 3, .36)
        f5_net(wd, -1.18, -.45, D, 1.38, 1.98, 0)
    elif tier == 2:
        cy = T23C(D)
        v4_fish_fill_counter(acc, 2.75, cy, 2)
        v4_ticket_dispenser(acc, (1.25, -D / 2 + .14, 0), -20)
        v4_sink(acc, -1.2, yf - .3, .75)
        ty = v5_table(acc, -.15, yf, 1.1, .55, INOX, A, f5_table_under, 2)
        a5_label_scale(acc, (-.45, ty, .9), 0, A)
        sd_cutting_board(acc, (.1, ty - .02, .9), 0, .4, .3)
        sd_fish(acc, (.1, ty - .02, .925), .34, 0, "fish_red")
        v4_chest_freezer(RC(acc, {C(WHITE): C(A)}), 1.05, yf - .325, 1.0, .65, .85, "fish", 1)
        sd_rope_coil(acc, (1.3, yf - .3, .87), .1, 3)
        v5_lane(acc, key, D, cy + .475, -1.375, 1.375, [(-1.2, 0.75, 0.62), (-0.15, 1.1, 0.55), (1.05, 1, 0.67)])
        v5_menu_board(wd, -.4, 2.32, D, 2, .68, True, 0)
        f5_net(wd, .6, 1.5, D, 1.3, 1.98, 1)
    else:
        cy = T23C(D)
        Xc = Xf(acc, (-.62, 0, 0))
        v4_fish_fill_counter(Xc, 2.65, cy, 3)
        v4_chest_freezer(RC(acc, {C(WHITE): C(A)}), W / 2 - .66, -D / 2 + .5, 1.25, .9, .85, "fish", 2)
        sd_lobster_tank(acc, W / 2 - .66, -D / 2 + 1.5, 1.1, .55)
        v4_ticket_dispenser(acc, (-1.7, -D / 2 + .14, 0), 20)
        v4_sink(acc, -1.6, yf - .3, .75)
        ty = v5_table(acc, -.6, yf, 1.2, .55, INOX, A, f5_table_under, 3)
        a5_label_scale(acc, (-.9, ty, .9), 0, A)
        sd_cutting_board(acc, (-.4, ty - .02, .9), 0, .4, .3)
        sd_fish(acc, (-.4, ty - .02, .925), .36, 0, "fish_blue")
        v4_ice_machine(teal, .45, yf - .375)
        v5_cold_door(wd, 1.5, D, .8, 2.05)
        v5_lane(acc, key, D, cy + .475, -1.945, 0.705, [(-1.6, 0.75, 0.62), (-0.6, 1.2, 0.55), (0.45, 0.75, 0.8), (1.5, 0.96, 0.05)])
        v5_menu_board(wd, -.75, 2.32, D, 3, .66, True, 0)


# ================================================================================================ SORVETERIA (pastel pink + mint)
def s5_softserve(acc, loc, body=None, front=None):
    """Compact soft-serve machine (0.55 x 0.6) in pastel enamel: lower cabinet, head with a small screen, three
    nozzles and levers, drip tray, hopper lids, cones on the side."""
    body = body or ACCENT["sorvetes"][0]
    front = front or ACCENT["sorvetes"][1]
    X = Xf(acc, loc)
    rbox(X, (.55, .6, .8), (0, 0, .4), C(body), .05, 3)
    rbox(X, (.45, .012, .55), (0, -.304, .42), C(front), .02, 2)
    rbox(X, (.55, .55, .55), (0, .025, 1.08), C(body), .06, 3)
    rbox(X, (.48, .02, .38), (0, -.255, 1.1), C(front), .03, 2)
    rbox(X, (.16, .01, .07), (0, -.268, 1.24), "E_DDF4FF", .004, 1)
    for k in range(3):
        px_ = -.14 + k * .14
        lathe(X, [(0, 0), (.02, 0), (.012, .05), (0, .055)], (px_, -.3, .9), C(CHROME), 8, 0, rot=(180, 0, 0))
        tube(X, [(px_, -.27, 1.0), (px_, -.32, 1.07)], .01, C(CHROME), 6)
        lathe(X, [(0, 0), (.02, 0), (.02, .03), (0, .03)], (px_, -.32, 1.07), C(["F4EBD8", "7A4A2E", body][k]), 8, 0)
    rbox(X, (.45, .1, .02), (0, -.33, .7), C(CHROME), .006, 1)
    for k in range(2):
        lathe(X, [(0, 0), (.1, 0), (.1, .02), (0, .03)], (-.13 + k * .26, .05, 1.36), C(WHITE), 12, 0)
    for k in range(4):
        sd_cone(X, (.2, -.28, .72 + k * .03), (), .1, .025)


def s5_cabinet(acc, x, yback, w, d=.5, h=.9, col=None):
    A, A2 = ACCENT["sorvetes"]
    col = col or A2
    y = yback - d / 2
    rbox(acc, (w, d, h - .04), (x, y, (h - .04) / 2), C(col), .03, 2)
    rbox(acc, (w + .02, d + .02, .04), (x, y, h - .02), MARBLE, .008, 1, uv=1.5)
    n = max(1, int(w / .5))
    for k in range(n):
        dx = x - w / 2 + (k + .5) * w / n
        rbox(acc, (w / n - .04, .01, h - .2), (dx, y - d / 2 - .004, h / 2), C(A), .015, 1)
        rbox(acc, (.1, .02, .02), (dx, y - d / 2 - .015, h - .16), C(CHROME), .006, 1)
    rbox(acc, (w, d, .06), (x, y, .03), C(GRAPH), .01, 1)
    return y


def s5_cone_rack(acc, x, D, z, w=.6):
    """Wall cone dispenser (wall dressing): a mint plate with three rows of cone holders, cones in each, the top
    row topped with scoops."""
    A, A2 = ACCENT["sorvetes"]
    ye, yw, _ = v5_planes(D)
    rbox(acc, (w, .02, .42), (x, yw - .03, z), C(A2), .01, 1)
    for s in (-1, 1):
        standoff(acc, x + s * (w / 2 - .06), z + .12, yw - .04, ye, .03, .05)
    for r_ in range(3):
        zz = z - .14 + r_ * .14
        rbox(acc, (w - .06, .07, .012), (x, yw - .07, zz), C(A), .004, 1)
        for k in range(int((w - .06) / .1)):
            px_ = x - (w - .06) / 2 + .05 + k * .1
            sd_cone(acc, (px_, yw - .075, zz - .06), (FLAVORS[(k + r_) % 7],) if r_ == 2 else (), .1, .024)


def sorvetes_v5(acc, tier):
    W, D = V5_SIZES["sorvetes"][tier - 1]
    ye, yw, yf = v5_planes(D)
    v5_back_wall(acc, W, D)
    wd = WD(acc)
    A, A2 = ACCENT["sorvetes"]
    pink = RC(acc, {C(NAVY): C(A), INOX: C(WHITE)})
    key = "sector-sorvetes_T%d" % tier
    if tier == 1:
        cy = T1C(D)
        v4_icecream_buffet(acc, 1.75, cy, 0)
        s5_softserve(acc, (-.85, yf - .3, 0), A, A2)
        ty = s5_cabinet(acc, .35, yf, 1.1, .5)
        a5_label_scale(acc, (.05, ty, .9), 0, A)
        v4_cups_station(acc, .4, ty, .9)
        v5_lane(acc, key, D, cy + .475, -0.875, 0.875, [(-0.85, 0.55, 0.66), (0.35, 1.1, 0.5)])
        v5_menu_board(wd, .35, 2.32, D, 1, .78, False, 0)
        s5_cone_rack(wd, -.85, D, 1.75, .55)
    elif tier == 2:
        cy = T23C(D)
        v4_icecream_buffet(Xf(acc, (-.45, 0, 0)), 2.2, cy, 1)
        v4_toppings_bar(pink, W / 2 - .45, cy - .1, .8)
        s5_softserve(acc, (-1.3, yf - .3, 0), A, A2)
        s5_softserve(acc, (-.7, yf - .3, 0), A2, A)
        ty = s5_cabinet(acc, .25, yf, 1.0, .5)
        a5_label_scale(acc, (-.05, ty, .9), 0, A)
        v4_cups_station(acc, .3, ty, .9)
        v4_chest_freezer(RC(acc, {C(WHITE): C(A2)}), 1.1, yf - .325, 1.0, .65, .85, "tubs", 1)
        v5_lane(acc, key, D, cy + .475, -1.55, 0.65, [(-1.3, 0.55, 0.66), (-0.7, 0.55, 0.66), (0.25, 1, 0.5), (1.1, 1, 0.67)])
        v5_menu_board(wd, .32, 2.32, D, 2, .68, True, 0)
        s5_cone_rack(wd, -1.0, D, 1.75, .9)
    else:
        cy = T23C(D)
        Xc = Xf(acc, (-.62, 0, 0))
        v4_icecream_buffet(Xc, 2.65, cy, 2)
        v4_toppings_bar(pink, W / 2 - .66, cy - .1, 1.2)
        v4_chest_freezer(RC(acc, {C(WHITE): C(A2)}), W / 2 - .66, -.05, 1.25, .7, .85, "tubs", 2)
        s5_softserve(acc, (-1.65, yf - .3, 0), A, A2)
        s5_softserve(acc, (-1.05, yf - .3, 0), A2, A)
        ty = s5_cabinet(acc, -.05, yf, 1.0, .5)
        a5_label_scale(acc, (-.35, ty, .9), 0, A)
        v4_cups_station(acc, .0, ty, .9)
        v4_glass_cabinet(acc, 1.3, yf - .325, 1.2, .65, 1.95, lambda X, i, w, d: [sd_cake(X, (-w / 2 + .16 + k * .3, 0, .005), .1, .07, ["straw", "choc", "cream"][(i + k) % 3]) for k in range(int(w / .3))], True, A, 4)
        v5_lane(acc, key, D, cy + .475, -1.945, 0.705, [(-1.65, 0.55, 0.66), (-1.05, 0.55, 0.66), (-0.05, 1, 0.5), (1.3, 1.2, 0.68)])
        v5_menu_board(wd, -.85, 2.32, D, 3, .66, True, 0)


# ================================================================================================ ADEGA (wine burgundy, dark wood)
def w5_gondola(acc, x, yback, w=1.0, h=1.6, seed=0):
    A, A2 = ACCENT["adega"]
    v4_wine_gondola(RC(acc, {C(NAVY): C(A), WOOD_L: WOOD_D}), x, yback - .25, w, h, seed, 0)


def w5_lattice(acc, x, w, D, z0, h, seed=0):
    """Diamond wine rack on the wall (wall dressing): dark-wood frame and crossed slats, bottles lying necks out."""
    ye, yw, _ = v5_planes(D)
    y = yw - .13
    for s in (-1, 1):
        rbox(acc, (.04, .26, h), (x + s * (w / 2 - .02), y + .0, z0 + h / 2), WOOD_D, .008, 1)
        standoff(acc, x + s * (w / 2 - .02), z0 + h - .08, y + .13, ye, .03, .05)
    rbox(acc, (w, .26, .04), (x, y, z0 + .02), WOOD_D, .008, 1)
    rbox(acc, (w, .26, .04), (x, y, z0 + h - .02), WOOD_D, .008, 1)
    L = math.hypot(w, h)
    ang = math.degrees(math.atan2(h, w))
    for k in range(-2, 3):
        for sgn in (-1, 1):
            rbox(acc, (L * .55, .22, .018), (x + k * w * .22, y, z0 + h / 2), WOOD_D, .004, 1, rot=(0, sgn * ang, 0))
    rnd = random.Random(seed)
    for i in range(int((w - .1) / .1)):
        for j in range(int((h - .1) / .14)):
            if rnd.random() < .7:
                px_ = x - (w - .1) / 2 + .05 + i * .1
                pz = z0 + .09 + j * .14
                lathe(acc, [(0, 0), (.034, 0), (.034, .18), (.015, .23), (0, .24)], (px_, y + .14, pz), C(["2A3B22", "4A1C24", "3A2A1A"][(i + j) % 3]), 6, 0, rot=(90, 0, 0))
                lathe(acc, [(0, 0), (.016, 0), (0, .02)], (px_, y - .1, pz), C(["7A1E2E", GOLD, "2A2A2A"][(i + j) % 3]), 6, 0, rot=(90, 0, 0))


def w5_barrel_table(acc, x, y, seed=0):
    """A standing oak barrel as a tasting table: round dark-wood top, a bottle, glasses and a cork bowl."""
    barrel(acc, (x, y, 0), .28, .92)
    lathe(acc, [(0, 0), (.36, 0), (.36, .04), (0, .04)], (x, y, .92), WOOD_D, 20, 0)
    v4_gondola_bottle(acc, (x - .06, y + .05, .96), "4A1C24", "7A1E2E", "wl_grape", 8)
    for k in range(3):
        a = k * 2.1 + .5
        sd_wine_glass(acc, (x + .18 * math.cos(a), y + .18 * math.sin(a), .96), "6A1A2A", k != 1)


def adega_v5(acc, tier):
    W, D = V5_SIZES["adega"][tier - 1]
    ye, yw, yf = v5_planes(D)
    v5_back_wall(acc, W, D)
    wd = WD(acc)
    A, A2 = ACCENT["adega"]
    wine = RC(acc, {C(NAVY): C(A), INOX: WOOD_D})
    key = "sector-adega_T%d" % tier
    LANELOG[key] = None                       # no service counter (self-service shop)
    if tier == 1:
        w5_gondola(acc, -.6, yf, 1.0, 1.6, 0)
        w5_gondola(acc, .55, yf, 1.0, 1.6, 2)
        v4_crate_island(wine, -.25, -D / 2 + .6, 1.1, .75, 0)
        w5_barrel_table(acc, .85, -D / 2 + .65, 0)
        v5_menu_board(wd, -.6, 2.32, D, 1, .78, False, 0)
        w5_lattice(wd, .55, .95, D, 1.72, .58, 0)
    elif tier == 2:
        w5_gondola(acc, -1.1, yf, 1.0, 1.6, 0)
        w5_gondola(acc, 0, yf, 1.0, 1.6, 2)
        v4_wine_cooler(acc, 1.1, yf - .325, .7)
        v4_crate_island(wine, -.45, -D / 2 + .7, 1.3, .8, 1)
        w5_barrel_table(acc, 1.05, -D / 2 + .75, 1)
        v5_menu_board(wd, -.55, 2.32, D, 2, .68, True, 0)
    else:
        w5_gondola(acc, -1.48, yf, 1.0, 1.6, 0)
        w5_gondola(acc, -.45, yf, 1.0, 1.6, 2)
        v4_wine_cooler(acc, .5, yf - .325, .7)
        v4_wine_cooler(acc, 1.2, yf - .325, .7)
        v4_tasting_machine(wine, 1.4, -D / 2 + 1.25)
        v4_crate_island(wine, -.75, -D / 2 + .7, 1.5, .85, 2)
        w5_barrel_table(acc, .55, -D / 2 + .7, 2)
        v5_menu_board(wd, -.93, 2.32, D, 3, .66, True, 0)


# ================================================================================================ BEBIDAS / sucos art (citrus orange + green)
def j5_zummo(acc, loc, yaw=0):
    A, A2 = ACCENT["sucos"]
    v4_zummo(RC(acc, {INOX: C(A), C(NAVY): C(A2)}), loc, yaw)


def j5_fruit_shelf(acc, x, w, D, z, seed=0):
    S = v5_shelf(acc, x, w, D, z, WOOD_L, .26)
    n = max(1, int(w / .32))
    for k in range(n):
        px_ = -w / 2 + (k + .5) * w / n
        B = basket(S, .28, .2, .09, (px_, 0, 0), 0)
        sd_fruit_mound(B, .24, .16, (0, 0, .02), ["orange", "lemon", "lime", "apple"][(k + seed) % 4], k, 0, .035)


def j5_under_crates(acc, x, y, w, d):
    for k in range(int((w - .1) / .45)):
        rbox(acc, (.4, .3, .24), (x - w / 2 + .25 + k * .45, y, .35), CRATE, .006, 1, uv=2)


def j5_cooler(acc, x, yback, w, d=.65, shelves=4):
    A, A2 = ACCENT["sucos"]
    v4_glass_cabinet(acc, x, yback - d / 2, w, d, 1.95, v4_juice_cooler_fill, True, A2, shelves)


def sucos_v5(acc, tier):
    W, D = V5_SIZES["sucos"][tier - 1]
    ye, yw, yf = v5_planes(D)
    v5_back_wall(acc, W, D)
    wd = WD(acc)
    A, A2 = ACCENT["sucos"]
    key = "sector-sucos_T%d" % tier
    blend = lambda X, loc, col: v4_blender_pro(RC(X, {C(NAVY): C(col)}), loc, col)
    if tier == 1:
        cy = -D / 2 + .25 + .4
        v4_juice_counter(acc, 1.8, cy, .95, .8, True, 0)
        j5_zummo(acc, (-.4, cy + .05, .95), 0)
        blend(acc, (.25, cy + .1, .95), A2)
        for k in range(3):
            sd_cup(acc, (.5 + k * .1, cy - .15, .95), ["F28C28", "D8354A", "7DB84A"][k], ["E8505B", NAVY, GOLD][k], ["orange", "lemon", "lime"][k])
        ty = v5_table(acc, -.55, yf, 1.2, .55, WOOD_L, A, j5_under_crates, 1)
        for k, kind in enumerate(("orange", "lemon")):
            Cr = crate(acc, .4, .3, .12, (-.9 + k * .45, ty, .9), 0)
            sd_fruit_mound(Cr, .36, .26, (0, 0, .02), kind, k, 0, .04)
        sd_juicer(acc, (-.05, ty, .9))
        j5_cooler(acc, .875, yf, .65)
        v5_lane(acc, key, D, cy + .4, -0.9, 0.9, [(-0.55, 1.2, 0.55), (0.875, 0.65, 0.68)])
        v5_menu_board(wd, -.15, 2.32, D, 1, .78, False, 0)
        j5_fruit_shelf(wd, -.95, .5, D, 1.34, 0)
    elif tier == 2:
        cy = -D / 2 + .3 + .4
        v4_juice_counter(acc, 2.4, cy, .95, .8, True, 1)
        j5_zummo(acc, (-.75, cy + .05, .95), 0)
        for k in range(2):
            blend(acc, (.1 + k * .28, cy + .12, .95), [A, A2][k])
        for k in range(4):
            sd_cup(acc, (.7 + k * .1, cy - .18, .95), list(JUICE.values())[k], ["E8505B", NAVY, GOLD, "5FB548"][k], ["orange", "lemon", "lime", None][k])
        ty = v5_table(acc, -.6, yf, 1.5, .55, WOOD_L, A, j5_under_crates, 2)
        for k, kind in enumerate(("orange", "lemon", "orange")):
            Cr = crate(acc, .4, .3, .12, (-1.1 + k * .45, ty, .9), 0)
            sd_fruit_mound(Cr, .36, .26, (0, 0, .02), kind, k, 0, .04)
        sd_juicer(acc, (.05, ty, .9))
        j5_cooler(acc, 1.2, yf, .65)
        v5_lane(acc, key, D, cy + .4, -1.2, 1.2, [(-0.6, 1.5, 0.55), (1.2, 0.65, 0.68)])
        v5_menu_board(wd, -.4, 2.32, D, 2, .68, True, 0)
        j5_fruit_shelf(wd, .58, .5, D, 1.34, 1)
    else:
        cy = -D / 2 + .3 + .4
        Xc = Xf(acc, (-.55, 0, 0))
        v4_juice_counter(Xc, 2.7, cy, .95, .8, True, 2)
        v4_zummo_stand(RC(acc, {INOX: C(A), C(NAVY): C(A2)}), (W / 2 - .45, -D / 2 + .55, 0), 0)
        j5_zummo(Xc, (-.9, cy + .05, .95), 0)
        for k in range(3):
            blend(Xc, (-.25 + k * .28, cy + .12, .95), [A, A2, "D8354A"][k])
        for k in range(4):
            sd_cup(Xc, (.65 + k * .1, cy - .18, .95), list(JUICE.values())[k], ["E8505B", NAVY, GOLD, "5FB548"][k], ["orange", "lemon", "lime", None][k])
        sd_pitcher(Xc, (1.15, cy + .1, .95), "F28C28")
        ty = v5_table(acc, -1.0, yf, 1.95, .55, WOOD_L, A, j5_under_crates, 3)
        sd_juicer(acc, (-.15, ty, .9))
        sd_cutting_board(acc, (-1.4, ty, .9), 0, .4, .28)
        for k in range(3):
            sd_citrus_half(acc, (-1.5 + k * .1, ty, .93), .045, ["orange", "lemon", "orange"][k], (0, 0, 0))
        j5_cooler(acc, 1.3, yf, 1.0, .65, 3)
        v5_lane(acc, key, D, cy + .4, -1.9, 0.8, [(-1, 1.95, 0.55), (1.2, 1.2, 0.68)])
        v5_menu_board(wd, -.85, 2.32, D, 3, .66, True, 0)
        j5_fruit_shelf(wd, -1.5, .66, D, 1.36, 2)


SECTOR_NAMES["sucos"] = "Bebidas"
for _sid, _fn in (("padaria", padaria_v5), ("queijaria", queijaria_v5), ("peixaria", peixaria_v5),
                  ("sorvetes", sorvetes_v5), ("adega", adega_v5), ("sucos", sucos_v5)):
    v5_tiers(_sid)
    BUILDERS["sector-" + _sid] = _logged(_sid, _fn)


# ================================================================================================ previews (round 5, all sectors)
def v5_sector_previews(sid):
    """T3 flush and T2 freestanding from the game camera, the T3 board close-up, the T2 top view with the staff
    footprint, and the T1-T3 lineup against the market wall."""
    for im in bpy.data.images:
        if im.name.startswith(("FT_PricePreview", "FT_NamePreview", "FT_TicketPreview")):
            im.reload()
    v4_materials(sid)
    v4_name_material()
    xs = v5_scene(sid)
    bpy.context.view_layer.update()
    X0, Y0 = V5_AT[sid]
    out = []
    w3, d3 = V5_SIZES[sid][2]
    w2, d2 = V5_SIZES[sid][1]
    out.append(v5_iso((xs[2], Y0 - d3 / 2 + .25, 1.35), w3, "sector-%s_T3_flush_gamecam" % sid, ycen=Y0 - d3 / 2, half=d3 / 2 + .9))
    out.append(v5_iso((xs[1], Y0 + FREE_DY + .25, 1.35), w2, "sector-%s_T2_free_gamecam" % sid, ycen=Y0 + FREE_DY, half=d2 / 2 + .9))
    key = "sector-%s_T3" % sid
    for (p, bw, bh) in BOARDLOG.get(key, [])[:1]:
        bx, by_, bz = p
        isolate(Y0 - d3 / 2, d3 / 2 + .9)
        camera((xs[2] + bx, Y0 - d3 / 2 + by_, bz), (-.12, -1, .18), max(bw, bh) * 1.25 + .9, 45)
        out.append(render(os.path.join(WALLS_QA, "sector-%s_T3_board" % sid), (1400, 900)))
    k2 = "sector-%s_T2" % sid
    if LANEPOS.get(k2) and (LANELOG.get(k2) or {}).get("ok"):
        lx, ly, lw = LANEPOS[k2]
        staff_marker(xs[1] + lx, Y0 + FREE_DY + ly, "Staff " + k2)
        lane_caption(("faixa %.2f m  /  pessoa %.2f m" % (LANELOG[k2]["lane"], STAFF_W)).replace(".", ","), (xs[1], Y0 + FREE_DY - d2 / 2 - .3, .004))
    isolate(Y0 + FREE_DY, d2 / 2 + .9)
    camera((xs[1], Y0 + FREE_DY - .1, 0), (0, -.001, 1), 20, 40, ortho=max(w2, d2) * 1.25)
    out.append(render(os.path.join(WALLS_QA, "sector-%s_T2_topdown" % sid), (1200, 1100)))
    total = sum(w for w, d in V5_SIZES[sid]) + 2.0
    out.append(v5_iso((X0, Y0 - 1.5, 1.2), total, "sector-%s_lineup_flush" % sid, size=(2048, 1000), scale=1.2, ycen=Y0 - 1.5, half=3.2))
    return out


def v5_lineup_all(y0=-360.0):
    """All seven T3 pieces side by side against one long replica of the market wall (Back Wall hidden)."""
    clear_v5_previews()
    sids = ["acougue", "padaria", "queijaria", "peixaria", "sorvetes", "adega", "sucos"]
    gap = .5
    ws = [V5_SIZES[s][2][0] for s in sids]
    total = sum(ws) + gap * (len(sids) - 1)
    x = 200 - total / 2
    prints = []
    for s, w in zip(sids, ws):
        d = V5_SIZES[s][2][1]
        v4_materials(s)
        place_piece(s, 3, (x + w / 2, y0 - d / 2, 0), "%s T3 all" % s, back=False)
        prints.append((x + w / 2, y0 - d / 2, w, d))
        x += w + gap
    market_wall(200 - total / 2 - 1, 200 + total / 2 + 1, y0, "MW wall all")
    market_floor(200 - total / 2 - 1.5, 200 + total / 2 + 1.5, y0 - 4.2, y0 + .1, prints, "MW floor all")
    bpy.context.view_layer.update()
    return v5_iso((200, y0 - 1.4, 1.2), total, "sector-all_T3_flush_lineup", size=(2048, 820), scale=1.04, ycen=y0 - 1.6, half=3.0)


# ================================================================================================ export (round 5)
def v5_export_tier(kind, i, folder=EXPORT):
    """sector-<sid>_T<n>.fbx with three objects, direct children of the FBX root: 'Body', 'Back Wall' and
    'Wall Dressing' (fixture_tiers.export_tier's conventions: mesh turned 180 deg about Z, -Z forward / Y up, so
    Unity local (x, y, z) = modelling (x, z, y); the customer side faces Unity -Z, the back face is at +depth/2)."""
    os.makedirs(folder, exist_ok=True)
    col = bpy.data.collections["FT %s T%d" % (kind, i)]
    src = [o for o in col.all_objects if o.type == "MESH"]
    dg = bpy.context.evaluated_depsgraph_get()
    R = Matrix.Rotation(math.pi, 4, "Z")
    parked, temps, mats, bounds = [], [], {}, {}
    for o in src:
        nm = o.name.split(" ", 1)[1].split(".")[0]
        clash = bpy.data.objects.get(nm)
        if clash:
            parked.append((clash, nm)); clash.name = nm + " (parked)"
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
        for v in me.vertices:
            lo = Vector(map(min, lo, v.co)); hi = Vector(map(max, hi, v.co))
        bounds[nm] = (lo, hi)
        me.transform(R)
        for k, m in enumerate(me.materials):
            if not m:
                continue
            new = export_role(m.name, False)
            if new != m.name:
                if new not in mats:
                    mats[new] = bpy.data.materials.get(new) or m.copy()
                    mats[new].name = new
                me.materials[k] = mats[new]
        t = bpy.data.objects.new(nm, me)
        bpy.context.scene.collection.objects.link(t)
        temps.append(t)
    tris, slots, per = 0, set(), {}
    for t in temps:
        t.data.calc_loop_triangles(); n = len(t.data.loop_triangles); tris += n; per[t.name] = n
        slots |= {m.name for m in t.data.materials if m}
    path = os.path.join(folder, "%s_T%d.fbx" % (kind, i))
    blanked = screens_blank(True)
    try:
        bpy.ops.object.select_all(action="DESELECT")
        for t in temps:
            t.select_set(True)
        bpy.context.view_layer.objects.active = temps[0]
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, axis_forward="-Z", axis_up="Y",
                                 bake_anim=False, path_mode="STRIP", use_mesh_modifiers=True, mesh_smooth_type="OFF",
                                 apply_scale_options="FBX_SCALE_ALL", use_tspace=False)
    finally:
        for t in temps:
            me = t.data
            bpy.data.objects.remove(t, do_unlink=True)
            bpy.data.meshes.remove(me)
        for m in mats.values():
            bpy.data.materials.remove(m)
        for o, nm in parked:
            o.name = nm
        screens_restore(blanked)
    U = lambda v: [round(v.x, 3), round(v.z, 3), round(v.y, 3)]
    lo = Vector(map(min, *[b[0] for b in bounds.values()])) if len(bounds) > 1 else list(bounds.values())[0][0]
    hi = Vector(map(max, *[b[1] for b in bounds.values()])) if len(bounds) > 1 else list(bounds.values())[0][1]
    sid = kind.split("-", 1)[1]
    W, D = V5_SIZES[sid][i - 1]
    bw = bounds.get("Back Wall")
    return {"file": os.path.basename(path), "tris": tris, "trisPerObject": per, "objects": sorted(per),
            "footprint": [W, D], "height": V5_H, "min": U(lo), "max": U(hi),
            "backFaceZ": round(hi.y, 4), "backWall": {"min": U(bw[0]), "max": U(bw[1])} if bw else None,
            "name": TIERS[kind][i - 1][1], "materials": sorted(slots)}


def v5_export_all():
    import json
    reps = []
    for sid in ("acougue", "padaria", "queijaria", "peixaria", "sorvetes", "adega", "sucos"):
        kind = "sector-" + sid
        v4_materials(sid)
        v4_name_material()
        for t in (1, 2, 3):
            build_item(kind, t - 1, (0, -500 - 10 * t, 0))
            r = v5_export_tier(kind, t)
            key = "%s_T%d" % (kind, t)
            r["slots"] = SLOTLOG.get(key, [])
            r["staffLane"] = LANELOG.get(key)
            reps.append(r)
    with open(os.path.join(EXPORT, "sector_export_report.json"), "w") as f:
        json.dump(reps, f, indent=1, ensure_ascii=False)
    return [(r["file"], r["tris"], r["backFaceZ"]) for r in reps]
