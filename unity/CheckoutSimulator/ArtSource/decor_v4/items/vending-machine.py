"""vending-machine: red enamel drinks machine - glass vitrine with six lit shelves of colourful cans and bottles behind
spiral coils, lit cream top sign with 3D bottle / droplet / can pictograms, right-hand column with an icon screen, keypad,
coin slot + return knob, bill acceptor, pickup tray with a navy flap, soda-bubble side art. Two "Anim Blink" lamps.
Footprint half .45 x .45, height <= 2.0 (Blender: front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
import _lib_C as L
from dv4 import RNG, MATH, MIX, SMOOTH, NOISE, ATTR

CONFIG = {"floor": "F4EFE4", "seed": 23}
RED, NAVY, GOLD, CREAM, INK, TEAL = "D74A3C", "1D2B4F", "E0B040", "F4EFE4", "20242B", "1F9A8E"
YF = .4                       # front face
X0, X1, Z0, Z1 = -.13, .37, .5, 1.6       # vitrine cavity (x, z)
XC = (X0 + X1) / 2
PITCH = .18                                 # shelf pitch
SHELF0 = Z0 + .025                          # first shelf top
COL_X = -.28                                # keypad column centre
LABELS = ("E0731C", "3F8A22", "2F7FC9", "C9372A", "6E3FB5", "178A7E", "E8B21F", "E4739A")


def art_product(c):
    """Cans / bottles: per-part colour, cream label band with a coloured stripe and a dot, aluminium top."""
    nt = c.nt
    t, s, rnd = ATTR(nt)
    base = L.pick(nt, rnd, LABELS)
    zl = MATH(nt, "MODULO", MATH(nt, "SUBTRACT", MATH(nt, "ADD", c.z, 9.0), SHELF0), PITCH)   # z within the shelf
    col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, 1.0), .08), base, "FFFFFF")
    lab = L.band(nt, zl, .04, .066)
    col = L.over(nt, col, lab, "F7F3EA")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", lab, L.band(nt, zl, .05, .056)), base)
    ang = MATH(nt, "ARCTAN2", MATH(nt, "SUBTRACT", c.y, .0), MATH(nt, "SUBTRACT", c.x, .0))
    # a round badge on the customer side of the label (+Y)
    ny = L.facing(c, (0, 1, 0), .5, .95)
    badge = MATH(nt, "MULTIPLY", lab, MATH(nt, "MULTIPLY", ny, L.band(nt, zl, .044, .062)))
    col = L.over(nt, col, badge, L.shade("FFFFFF", .95))
    top = SMOOTH(nt, zl, .098, .104)
    col = L.over(nt, col, top, "C9D2D6")
    return col


def art_sign(c):
    """Lit top sign: cream with a soft teal wave and bubbles (3D pictograms sit in front)."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, YF, 1.77), (1, 0, 0), (0, 0, 1))
    col = L.RAMP(nt, NOISE(nt, c.pos, 4.0, 1.0), [(.3, "F7F2E6"), (.8, "FFFBF2")])
    wave = MATH(nt, "ADD", MATH(nt, "MULTIPLY", MATH(nt, "SINE", MATH(nt, "MULTIPLY", u, 14.0)), .012), -.055)
    col = L.over(nt, col, SMOOTH(nt, MATH(nt, "SUBTRACT", v, wave), .003, -.003), "9ADCD4")
    for cx, cy, r in ((-.3, .03, .012), (-.1, -.02, .008), (.12, .04, .01), (.33, -.03, .014), (.38, .05, .007)):
        col = L.over(nt, col, L.ring(nt, u, v, r * .6, r, cx=cx, cy=cy), "5BC2B4")
    return col


def art_screen(c):
    nt = c.nt
    u, v = L.plane_uv(c, (COL_X, YF, 1.46), (1, 0, 0), (0, 0, 1))
    col = L.RAMP(nt, MATH(nt, "ADD", MATH(nt, "MULTIPLY", v, 4.0), .5), [(0.0, "1B6FB0"), (1.0, "4FB3E0")])
    col = L.over(nt, col, L.rect(nt, u, v, .03, .02, .004, cx=-.055), "F4EFE4")       # cup
    col = L.over(nt, col, L.rect(nt, u, v, .024, .012, .002, cx=-.055, cy=.004), "EC862E")
    col = L.over(nt, col, L.tri_up(nt, u, v, .014, .016, cx=.02, cy=.0), "F4EFE4")
    col = L.over(nt, col, L.rect(nt, u, v, .018, .02, .003, cx=.065, cy=0), "5A9D33")
    col = L.over(nt, col, L.circle(nt, u, v, .007, cx=.065, cy=0), "D7F0C0")
    return col


def art_side(c):
    """Red enamel with cream soda bubbles and a navy / cream diagonal wave (both sides)."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, 0, 1.0), (0, 1, 0), (0, 0, 1))
    col = L.RAMP(nt, NOISE(nt, c.pos, 2.5, 2.0), [(.3, "B83A2E"), (.5, RED), (.8, "E05A4C")])
    col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 140.0, 1.0), .04), col, "F08070")
    col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, 1.0), .12), col, "F08070")
    wave = MATH(nt, "ADD", MATH(nt, "MULTIPLY", MATH(nt, "SINE", MATH(nt, "MULTIPLY", u, 9.0)), .04), -.52)
    dv_ = MATH(nt, "SUBTRACT", v, wave)
    col = L.over(nt, col, SMOOTH(nt, dv_, .003, -.003), NAVY)
    col = L.over(nt, col, L.band(nt, dv_, -.0, .03), CREAM)
    for cx, cy, r in ((-.22, -.28, .05), (-.02, -.12, .07), (.18, -.34, .04), (.27, .02, .085), (-.26, .12, .06), (.04, .26, .045), (.3, .34, .055), (-.14, .5, .035), (.12, .55, .025)):
        m = MATH(nt, "MULTIPLY", L.ring(nt, u, v, r * .78, r, cx=cx, cy=cy), SMOOTH(nt, dv_, .0, .02))
        col = L.over(nt, col, m, "FFE3DD")
        m2 = MATH(nt, "MULTIPLY", L.circle(nt, u, v, r * .22, cx=cx - r * .35, cy=cy + r * .35), SMOOTH(nt, dv_, .0, .02))
        col = L.over(nt, col, m2, "FFE3DD")
    return col


def art_shelf(c):
    """Shelf: pale steel top, lit cream front lip with small coloured price dots."""
    nt = c.nt
    col = L.RAMP(nt, NOISE(nt, c.pos, 6.0, 1.0), [(.3, "CBD3D8"), (.8, "E4EAEE")])
    front = L.facing(c, (0, 1, 0), .5, .95)
    col = L.over(nt, col, front, "FFEFC2")
    xl = MATH(nt, "SUBTRACT", MATH(nt, "MODULO", MATH(nt, "ADD", MATH(nt, "SUBTRACT", c.x, X0 + .05), 9.0), .1), .05)
    zl = MATH(nt, "SUBTRACT", MATH(nt, "MODULO", MATH(nt, "ADD", c.z, 9.0), PITCH), .0)
    idx = MATH(nt, "DIVIDE", MATH(nt, "MODULO", MATH(nt, "FLOOR", MATH(nt, "DIVIDE", MATH(nt, "ADD", MATH(nt, "SUBTRACT", c.x, X0), 9.0), .1)), 4.0), 4.0)
    dc = L.RAMP(nt, idx, [(0.0, "EC862E"), (.25, "5A9D33"), (.5, "3E8FD6"), (.75, "D74A3C")], "CONSTANT")
    tag = MATH(nt, "MULTIPLY", front, L.rect(nt, xl, c.z, .03, 1.0, .004))
    col = MIX(nt, MATH(nt, "MULTIPLY", tag, .0), col, dc)
    return col


def art_cap(c):
    """Dark cap top: red pinstripe frame, cream oval badge with a blue droplet and red / teal dots (seen from the game camera)."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, 0, 1.945), (-1, 0, 0), (0, -1, 0))
    col = L.RAMP(nt, NOISE(nt, c.pos, 12.0, 3.0), [(.3, "1A2226"), (.6, "2F3A40"), (.9, "3E4A52")])
    top = L.facing(c, (0, 0, 1))
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.cut(nt, L.rect(nt, u, v, .38, .33, .04), L.rect(nt, u, v, .368, .318, .035))), RED)
    oval = L.circle(nt, MATH(nt, "MULTIPLY", u, .75), v, .14)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, oval), CREAM)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.circle(nt, u, v, .05, cy=-.02)), "3E8FD6")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.tri_up(nt, u, v, .05, .09, cy=.035)), "3E8FD6")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.circle(nt, u, v, .012, cx=-.018, cy=-.01)), "BFE3FF")
    for cx, cy, h in ((-.3, .22, RED), (.3, .22, TEAL), (-.3, -.22, TEAL), (.3, -.22, RED)):
        col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.circle(nt, u, v, .03, cx=cx, cy=cy)), h)
    return col


def build():
    L.install_fix()
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.34)
    red = L.paint_enamel("Red", RED, dark="A8352A", light="E8705F", sheen=.12, edge_k=.5)
    side = L.uv_weight(dv4.paint("Side", art_side, edge="F08070", edge_k=.5), 1.2)
    rubber = L.paint_rubber("Rubber")
    dark = L.paint_enamel("Dark", "2F3A40", sheen=.15)
    chrome = L.paint_chrome("Chrome")
    gold = dv4.paint_gold("Gold")
    navy = L.paint_enamel("Navy", NAVY)
    cream = L.paint_enamel("Cream", "F7F3EA", sheen=.08)
    inner = L.paint_enamel("Inner", "F9F6EE", sheen=.0, speck=.02)
    shelf = dv4.paint("Shelf", art_shelf, k_ao=.35, k_light=.2)
    prod = dv4.paint("Product", art_product, k_ao=.3, k_light=.25, edge="FFFFFF", edge_k=.3, edge_r=.003)
    coilp = L.paint_enamel("Coil", "8C969C", dark="5A646A", light="C9D2D6", sheen=.3)
    sign = L.paint_bright("Sign", art_sign)
    screen = L.paint_bright("Screen", art_screen)
    shelf = L.uv_weight(shelf, .8); prod = L.uv_weight(prod, .8); coilp = L.uv_weight(coilp, .4)
    key = L.paint_enamel("Key", "F7F3EA", sheen=.3)
    teal = L.paint_enamel("Teal", TEAL, sheen=.3); blue = L.paint_enamel("Blue", "3E8FD6", sheen=.3)
    ledg = L.paint_bright("LedG", lambda c: "7CE08A"); ledo = L.paint_bright("LedO", lambda c: "FFB347")
    cap = L.uv_weight(dv4.paint("CapArt", art_cap, edge="5A676F", edge_k=.6), 1.3)
    glow = "E_FFF4DC"

    # ---- plinth, shell (back + sides + top + front plates around the vitrine)
    dv4.cube("Plinth", (.88, .78, .1), loc=(0, 0, .05), paint=rubber, bevel=.02, segs=2)
    dv4.cube("Back", (.9, .08, 1.8), loc=(0, -.36, 1.0), paint=red, bevel=.03, segs=2)
    for sx in (-1, 1):
        dv4.cube("Side%d" % sx, (.08, .8, 1.8), loc=(sx * .41, 0, 1.0), paint=side, bevel=.03, segs=2)
    dv4.cube("Top", (.9, .8, .08), loc=(0, 0, 1.86), paint=red, bevel=.03, segs=2)
    dv4.cube("Cap", (.86, .76, .05), loc=(0, 0, 1.92), paint=cap, bevel=.012, segs=2)
    for i in range(4):     # vents on the cap (behind the badge)
        dv4.cube("Vent%d" % i, (.5, .016, .008), loc=(0, -.33 + i * .035, 1.948), paint=rubber, bevel=.002)
    dv4.cube("Header", (.9, .07, .3), loc=(0, YF - .035, 1.75), paint=red, bevel=.02, segs=2)
    dv4.cube("Footer", (.9, .07, .42), loc=(0, YF - .035, .3), paint=red, bevel=.02, segs=2)
    dv4.cube("Column", (.28, .07, 1.12), loc=(COL_X, YF - .035, 1.05), paint=red, bevel=.02, segs=2)
    dv4.cube("Pillar", (.08, .07, 1.12), loc=(.41, YF - .035, 1.05), paint=red, bevel=.015, segs=2)
    for z in (Z0 - .02, Z1 + .02):
        dv4.cube("GoldLine%s" % z, (.84, .012, .02), loc=(0, YF + .004, z), paint=gold, bevel=.003)
    # ---- vitrine cavity: cream walls, lit ceiling, shelves with products + coils
    W = X1 - X0; H = Z1 - Z0
    dv4.cube("CavBack", (W + .02, .02, H + .02), loc=(XC, -.31, (Z0 + Z1) / 2), paint=inner, bevel=.004, segs=1)
    for x in (X0, X1):
        dv4.cube("CavSide%s" % x, (.02, .68, H + .02), loc=(x, .03, (Z0 + Z1) / 2), paint=inner, bevel=.004, segs=1)
    dv4.cube("CavTop", (W + .02, .68, .02), loc=(XC, .03, Z1), paint=inner, bevel=.004, segs=1)
    dv4.cube("CavBot", (W + .02, .68, .02), loc=(XC, .03, Z0), paint=inner, bevel=.004, segs=1)
    dv4.cube("CavLamp", (W - .08, .4, .012), loc=(XC, .05, Z1 - .012), paint=None, bevel=.003, mat_override=glow)
    for sh in range(6):
        zt = SHELF0 + sh * PITCH
        dv4.cube("Shelf%d" % sh, (W - .03, .36, .016), loc=(XC, .16, zt - .008), paint=shelf, bevel=.004, segs=1)
        dv4.cube("ShelfLip%d" % sh, (W - .03, .012, .03), loc=(XC, .345, zt - .006), paint=shelf, bevel=.003, segs=1)
        for i in range(4):
            x = X0 + .07 + i * .12
            if sh < 3:
                L.can("Can%d%d" % (sh, i), (x, .18, zt), prod, h=.12, r=.033, seg=8)
            else:
                L.bottle("Bottle%d%d" % (sh, i), (x, .18, zt), prod, h=.155, r=.03, seg=8)
            L.coil("Coil%d%d" % (sh, i), (x, .25, zt + .038), r=.034, length=.09, turns=1.0, n=5, radius=.004, paint=coilp)
    # glass pane + chrome frame
    dv4.cube("Glass", (W + .06, .01, H + .06), loc=(XC, YF - .006, (Z0 + Z1) / 2), paint=None, bevel=0, mat_override="G_Glass")
    for x in (X0 - .035, X1 + .035):
        dv4.cylinder("FrameV%s" % x, .012, H + .08, loc=(x, YF, Z0 - .04), seg=8, paint=chrome)
    for z in (Z0 - .04, Z1 + .04):
        dv4.cylinder("FrameH%s" % z, .012, W + .07, loc=(X0 - .035, YF, z), rot=(0, 90, 0), seg=8, paint=chrome)
    # ---- column: screen, keypad, coin slot + return knob, bill acceptor, two lamps on Blink nodes
    L.panel("ScreenBezel", .24, .12, .02, .015, loc=(COL_X, YF + .004, 1.46), paint=dark, bevel=.004)
    L.panel("Screen", .2, .08, .01, .008, loc=(COL_X, YF + .013, 1.46), paint=screen, bevel=.002)
    L.panel("KeyPlate", .24, .3, .016, .025, loc=(COL_X, YF + .003, 1.22), paint=navy, bevel=.004)
    for j in range(4):
        for i in range(3):
            dv4.cube("Key%d%d" % (i, j), (.05, .014, .045), loc=(COL_X - .06 + i * .06, YF + .013, 1.32 - j * .062), paint=key, bevel=.005, segs=2)
    L.panel("CoinPlate", .16, .1, .016, .015, loc=(COL_X, YF + .003, .98), paint=chrome, bevel=.004)
    dv4.cube("CoinSlot", (.012, .012, .045), loc=(COL_X - .045, YF + .012, .99), paint=rubber, bevel=.002)
    dv4.cylinder("Knob", .022, .025, loc=(COL_X + .035, YF + .01, .975), rot=(-90, 0, 0), seg=12, paint=rubber, bevel=.006)
    L.panel("Bill", .17, .06, .018, .012, loc=(COL_X, YF + .004, .85), paint=chrome, bevel=.004)
    L.panel("BillSlot", .12, .01, .01, .004, loc=(COL_X, YF + .014, .85), paint=rubber, bevel=.002)
    dv4.sphere("Lamp", .012, loc=(COL_X + .09, YF + .014, 1.53), seg=8, rings=5, paint=ledg, out="Anim Blink")
    dv4.sphere("Lamp2", .01, loc=(COL_X + .09, YF + .012, .98), seg=8, rings=5, paint=ledo, out="Anim Blink.001")
    # ---- pickup tray in the footer: dark recess, navy flap with a chrome handle
    L.panel("TrayFrame", .56, .3, .024, .03, loc=(XC - .05, YF + .004, .32), paint=chrome, bevel=.005)
    L.panel("TrayRecess", .52, .26, .014, .025, loc=(XC - .05, YF + .012, .32), paint=rubber, bevel=.003)
    L.panel("TrayFlap", .46, .2, .014, .02, loc=(XC - .05, YF + .02, .31), rot=(-8, 0, 0), paint=navy, bevel=.004)
    dv4.cylinder("TrayHandle", .009, .3, loc=(XC - .2, YF + .036, .385), rot=(0, 90, 0), seg=8, paint=chrome)
    dv4.cube("TrayLip", (.56, .03, .04), loc=(XC - .05, YF + .01, .14), paint=chrome, bevel=.006, segs=2)
    # ---- lit top sign with 3D pictograms: teal bottle, blue droplet, red can
    L.panel("SignFrame", .86, .24, .02, .03, loc=(0, YF - .002, 1.77), paint=gold, bevel=.005)
    L.panel("Sign", .82, .2, .03, .025, loc=(0, YF + .004, 1.77), paint=sign, bevel=.004)
    L.bottle("SignBottle", (-.27, YF + .008, 1.685), teal, h=.17, r=.034, seg=12)
    dv4.sphere("Drop", .04, loc=(0, YF + .005, 1.74), seg=12, rings=8, paint=blue)
    dv4.lathe("DropTip", [(0, 0), (.039, 0), (.022, .04), (0, .068)], seg=12, loc=(0, YF + .005, 1.745), paint=blue)
    L.can("SignCan", (.27, YF + .003, 1.69), red, h=.15, r=.042, seg=12)
    dv4.cylinder("SignCanTop", .036, .006, loc=(.27, YF + .003, 1.838), seg=12, paint=chrome)
    return {"name": "VendingMachine", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
