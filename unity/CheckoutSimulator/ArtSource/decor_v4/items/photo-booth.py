"""photo-booth: retro navy photo booth - gold crown with chaser marquee bulbs (3 "Anim Blink" nodes) and a camera sign,
pleated red velvet curtain on "Anim Curtain" (pivot on the rail end at the +X wall in Unity = Blender -X, opened by scaling
local X 1 -> .25), cream front panel with a painted sample photo strip, coin slot and a printed strip coming out of the
photo slot, chequered floor, padded stool, camera / flash / screen wall inside, gold pinstripe + star art on the sides.
Footprint half .50 x .52, height <= 2.2 (Blender: front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
import _lib_C as L
from dv4 import RNG, MATH, MIX, SMOOTH, NOISE

CONFIG = {"floor": "F4EFE4", "seed": 31}
NAVY, GOLD, CREAM, RED, INK, TEAL, PINK = "1D2B4F", "E0B040", "F4EFE4", "D74A3C", "20242B", "1F9A8E", "EE8FAE"
PIV = (-.44, .44, 1.86)       # curtain pivot (Blender) = Unity (.44, 1.86, -.44)
CW, CH = .56, 1.5             # curtain width / drop
YF = .47                      # front face


def photos(nt, u, v, w, h, gap, cy0):
    """Four stacked pictures (pastel backgrounds, simple face / heart / star / two-friends pictograms). Returns [(mask, draw)]"""
    frames = []
    for k, bg in enumerate(("7BD3F7", "F2B8C6", "FFE066", "A8E0A0")):
        cy = cy0 - k * (h * 2 + gap)
        frames.append((k, bg, cy))
    return frames


def strip_art(c, center, right, up, w=.09, h=.062, gap=.012, cy0=.205):
    """Paint a photo strip (cream card with 4 pictures) in the plane; returns colour."""
    nt = c.nt
    u, v = L.plane_uv(c, center, right, up)
    col = L.RAMP(nt, NOISE(nt, c.pos, 30.0, 1.0), [(.3, "F3EEE3"), (.8, "FFFCF5")])
    for k, bg, cy in photos(nt, u, v, w, h, gap, cy0):
        col = L.over(nt, col, L.rect(nt, u, v, w, h, .004, cy=cy), bg)
        if k == 0:          # smiling face
            col = L.over(nt, col, L.circle(nt, u, v, .036, cy=cy - .004), "F6D3B0")
            for sx in (-1, 1):
                col = L.over(nt, col, L.circle(nt, u, v, .005, cx=sx * .013, cy=cy + .004), INK)
            col = L.over(nt, col, L.smile(nt, u, v, .016, .004, cy=cy - .006), INK)
            col = L.over(nt, col, L.rect(nt, u, v, .04, .012, .006, cy=cy + .03), "D74A3C")   # party hat band -> a cap
        elif k == 1:        # heart
            col = L.over(nt, col, L.heart(nt, u, v, .022, cy=cy - .002), "D74A3C")
        elif k == 2:        # two friends
            for sx in (-1, 1):
                col = L.over(nt, col, L.circle(nt, u, v, .026, cx=sx * .03, cy=cy - .002), "F6D3B0" if sx < 0 else "C98A4E")
                for ex in (-1, 1):
                    col = L.over(nt, col, L.circle(nt, u, v, .004, cx=sx * .03 + ex * .009, cy=cy + .004), INK)
                col = L.over(nt, col, L.smile(nt, u, v, .012, .0035, cx=sx * .03, cy=cy - .004), INK)
        else:               # star
            col = L.over(nt, col, L.star(nt, u, v, .034, cy=cy - .002), GOLD)
    return col


def art_front_strip(c):
    return strip_art(c, (.31, YF + .03, 1.3), (1, 0, 0), (0, 0, 1))


def art_print(c):
    return strip_art(c, (.31, YF + .03, .55), (1, 0, 0), (0, -.14, -.99), w=.065, h=.045, gap=.008, cy0=.082)


def art_side(sign):
    def r(c):
        nt = c.nt
        u, v = L.plane_uv(c, (0, 0, 1.05), (0, 1, 0), (0, 0, 1))
        col = L.RAMP(nt, NOISE(nt, c.pos, 3.0, 2.0), [(.3, "172340"), (.55, NAVY), (.85, "2A3B66")])
        col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, 1.0), .15), col, "3A4D80")
        col = L.over(nt, col, L.cut(nt, L.rect(nt, u, v, .4, .85, .04), L.rect(nt, u, v, .388, .838, .035)), GOLD)
        col = L.over(nt, col, L.circle(nt, u, v, .2, cy=.1), "F3EEE3")
        col = L.over(nt, col, L.rect(nt, u, v, .13, .085, .018, cy=.1), NAVY)
        col = L.over(nt, col, L.rect(nt, u, v, .045, .02, .006, cx=-.06, cy=.195), NAVY)
        col = L.over(nt, col, L.circle(nt, u, v, .05, cy=.1), "F3EEE3")
        col = L.over(nt, col, L.circle(nt, u, v, .035, cy=.1), "3E8FD6")
        col = L.over(nt, col, L.circle(nt, u, v, .012, cx=.012, cy=.112), "F3EEE3")
        col = L.over(nt, col, L.circle(nt, u, v, .013, cx=.095, cy=.16), GOLD)
        for cx, cy, R in ((-.3, .36, .045), (.3, .36, .045), (-.3, -.3, .045), (.3, -.3, .045), (0, -.22, .04), (-.28, -.02, .028), (.28, -.02, .028)):
            col = L.over(nt, col, L.star(nt, u, v, R, cx=cx, cy=cy), GOLD)
        return col
    return r


def art_checker(c):
    nt = c.nt
    cu = MATH(nt, "FLOOR", MATH(nt, "DIVIDE", MATH(nt, "ADD", c.x, 9.0), .12))
    cv = MATH(nt, "FLOOR", MATH(nt, "DIVIDE", MATH(nt, "ADD", c.y, 9.0), .12))
    k = MATH(nt, "MODULO", MATH(nt, "ADD", cu, cv), 2.0)
    col = L.RAMP(nt, k, [(0.0, "2A3346"), (.5, "EDE6D6")], "CONSTANT")
    return MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 20.0, 1.0), .12), col, "8A8070")


def art_cushion(base, dark):
    def r(c):
        nt = c.nt
        col = L.RAMP(nt, NOISE(nt, c.pos, 5.0, 2.0), [(.3, dark), (.55, base), (.85, L.mixhex(base, "FFFFFF", .25))])
        col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 70.0, 2.0), .12), col, dark)
        a = MATH(nt, "ARCTAN2", MATH(nt, "SUBTRACT", c.y, -.05), MATH(nt, "SUBTRACT", c.x, -.1))
        rr = L.dist(nt, MATH(nt, "SUBTRACT", c.x, -.1), MATH(nt, "SUBTRACT", c.y, -.05))
        seams = MATH(nt, "ABSOLUTE", MATH(nt, "SINE", MATH(nt, "MULTIPLY", a, 3.0)))
        seams = MATH(nt, "MULTIPLY", SMOOTH(nt, seams, .08, .0), SMOOTH(nt, rr, .03, .05))
        col = L.over(nt, col, MATH(nt, "MULTIPLY", seams, L.facing(c, (0, 0, 1))), dark)
        col = L.over(nt, col, MATH(nt, "MULTIPLY", L.circle(nt, MATH(nt, "SUBTRACT", c.x, -.1), MATH(nt, "SUBTRACT", c.y, -.05), .012), L.facing(c, (0, 0, 1))), GOLD)
        return col
    return r


def art_screen(c):
    nt = c.nt
    u, v = L.plane_uv(c, (.405, -.05, 1.35), (0, -1, 0), (0, 0, 1))
    col = L.RAMP(nt, MATH(nt, "ADD", MATH(nt, "MULTIPLY", v, 2.0), .5), [(0.0, "1B6FB0"), (1.0, "4FB3E0")])
    col = L.over(nt, col, L.cut(nt, L.rect(nt, u, v, .11, .09, .01), L.rect(nt, u, v, .104, .084, .008)), "F4EFE4")
    col = L.over(nt, col, L.circle(nt, u, v, .04, cy=-.005), "F6D3B0")
    for sx in (-1, 1):
        col = L.over(nt, col, L.circle(nt, u, v, .006, cx=sx * .015, cy=.005), INK)
    col = L.over(nt, col, L.smile(nt, u, v, .018, .004, cy=-.008), INK)
    col = L.over(nt, col, L.heart(nt, u, v, .009, cx=.07, cy=.07), "EE8FAE")
    col = L.over(nt, col, L.star(nt, u, v, .014, cx=-.07, cy=.07), GOLD)
    return col


def art_cap(c):
    """Gold cap top: navy panel with a big cream camera pictogram and gold stars (what the game camera sees)."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, 0, 2.16), (-1, 0, 0), (0, -1, 0))
    col = L.RAMP(nt, NOISE(nt, c.pos, 10.0, 2.0), [(.2, "A8781F"), (.55, GOLD), (.9, "FFE38A")])
    col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, .9), .4), col, "FFE38A")
    top = L.facing(c, (0, 0, 1))
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.rect(nt, u, v, .4, .4, .06)), NAVY)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.cut(nt, L.rect(nt, u, v, .37, .37, .05), L.rect(nt, u, v, .355, .355, .045))), GOLD)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.rect(nt, u, v, .17, .11, .025, cy=-.01)), "F3EEE3")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.rect(nt, u, v, .06, .025, .008, cx=-.08, cy=.115)), "F3EEE3")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.circle(nt, u, v, .07, cy=-.01)), NAVY)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.circle(nt, u, v, .05, cy=-.01)), "3E8FD6")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.circle(nt, u, v, .016, cx=.016, cy=.006)), "F3EEE3")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.circle(nt, u, v, .016, cx=.125, cy=.07)), GOLD)
    for sx in (-1, 1):
        for sy in (-1, 1):
            col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.star(nt, u, v, .04, cx=sx * .28, cy=sy * .28)), GOLD)
    return col


def build():
    L.install_fix()
    dv4.FINISH.update(ao=.6, ao_dist=.25, light=.34)
    navy = L.paint_enamel("Navy", NAVY)
    side = L.uv_weight(dv4.paint("Side", art_side(True), edge="5A6B9E", edge_k=.5), 1.3)
    gold = dv4.paint_gold("Gold")
    chrome = L.paint_chrome("Chrome")
    rubber = L.paint_rubber("Rubber")
    dark = L.paint_enamel("Dark", "2F3A40", sheen=.15)
    cream = L.paint_enamel("Cream", "F6F1E6", sheen=.08)
    velvet = L.paint_velvet("Velvet", RED, "7E2418", "F07A66", x0=PIV[0], width=CW, waves=7)
    strip = L.uv_weight(L.paint_bright("Strip", art_front_strip), 2.0)
    printp = L.uv_weight(L.paint_bright("Print", art_print), 2.0)
    checker = L.uv_weight(dv4.paint("Checker", art_checker, k_ao=.5), 1.2)
    cushion = L.uv_weight(dv4.paint("Cushion", art_cushion(RED, "8E2A20"), edge="F07A66", edge_k=.3), 1.3)
    screen = L.paint_bright("Screen", art_screen)
    flashp = L.paint_bright("Flash", lambda c: "FFF7D8")
    cap = L.uv_weight(dv4.paint("CapArt", art_cap, edge="FFE38A", edge_k=1.0, edge_r=.006), 1.3)
    glow = "E_FFE9B0"

    # ---- base with chequered floor, walls (navy), cream front-left panel, crown + gold cap
    dv4.cube("Base", (.94, .94, .08), loc=(0, 0, .04), paint=rubber, bevel=.02, segs=1)
    L.panel("FloorTile", .84, .84, .01, .02, loc=(0, 0, .085), rot=(90, 0, 0), paint=checker, bevel=.002)
    dv4.cube("BackWall", (.94, .06, 1.9), loc=(0, -.44, 1.03), paint=navy, bevel=.02, segs=2)
    for sx in (-1, 1):
        dv4.cube("SideWall%d" % sx, (.06, .94, 1.9), loc=(sx * .44, 0, 1.03), paint=side, bevel=.02, segs=2)
    dv4.cube("FrontPanel", (.34, .06, 1.9), loc=(.30, .44, 1.03), paint=cream, bevel=.02, segs=2)
    dv4.cube("Lintel", (.6, .06, .12), loc=(-.14, .44, 1.92), paint=navy, bevel=.015, segs=2)
    dv4.cube("Crown", (.94, .94, .14), loc=(0, 0, 2.05), paint=navy, bevel=.035, segs=3)
    dv4.cube("Cap", (.96, .96, .04), loc=(0, 0, 2.14), paint=cap, bevel=.012, segs=2)
    dv4.cube("Belt", (.96, .96, .03), loc=(0, 0, 1.985), paint=gold, bevel=.008, segs=2)
    # ---- crown: camera sign (gold plate, navy camera, cream lens) + gold stars, chaser bulbs on the cap edge
    L.panel("SignPlate", .62, .19, .02, .04, loc=(0, .475, 2.05), paint=gold, bevel=.005)
    L.panel("CamBody", .2, .12, .02, .025, loc=(-.02, .49, 2.04), paint=navy, bevel=.004)
    dv4.cube("CamTop", (.07, .02, .03), loc=(-.06, .49, 2.11), paint=navy, bevel=.005, segs=1)
    dv4.cylinder("LensRing", .045, .012, loc=(-.02, .495, 2.04), rot=(-90, 0, 0), seg=18, paint=cream, bevel=.003)
    dv4.cylinder("Lens", .03, .01, loc=(-.02, .505, 2.04), rot=(-90, 0, 0), seg=16, paint=dark, bevel=.003)
    dv4.sphere("LensGlint", .01, loc=(-.01, .507, 2.05), seg=8, rings=5, paint=cream)
    dv4.sphere("FlashBulb", .013, loc=(.06, .495, 2.085), seg=8, rings=5, paint=None, mat_override=glow)
    for sx in (-1, 1):
        L.star_prism("CrownStar%d" % sx, .04, .45, .016, loc=(sx * .23, .49, 2.05), paint=gold)
    nodes = ["Anim Blink", "Anim Blink.001", "Anim Blink.002"]
    n = 0
    for i in range(12):
        t = -.44 + i * .08
        for p in ((t, .482, 2.17), (t, -.482, 2.17), (.482, t, 2.17), (-.482, t, 2.17)):
            L.bulb("Bulb%d" % n, p, .017, out=nodes[n % 3], glow=glow); n += 1
    # ---- curtain rail (Body) + pleated curtain with rings and a gold header tape ("Anim Curtain")
    dv4.cylinder("Rail", .011, CW + .04, loc=(PIV[0] - .02, PIV[1], PIV[2]), rot=(0, 90, 0), seg=8, paint=chrome)
    for x in (PIV[0] - .01, PIV[0] + CW + .01):
        dv4.cube("Bracket%s" % x, (.03, .05, .04), loc=(x, PIV[1] - .01, PIV[2] + .005), paint=chrome, bevel=.005, segs=1)
    cur = "Anim Curtain"; dv4.pivot(cur, PIV)
    L.curtain("Curtain", CW, CH, waves=7, amp=.036, thick=.014, loc=(PIV[0], PIV[1], PIV[2] - .035), paint=velvet, out=cur)
    for i in range(8):
        dv4.torus("Ring%d" % i, .02, .005, loc=(PIV[0] + .035 + i * .07, PIV[1], PIV[2]), rot=(0, 90, 0), seg=10, minor=4, paint=gold, out=cur)
    dv4.cube("Header", (CW, .05, .035), loc=(PIV[0] + CW / 2, PIV[1], PIV[2] - .05), paint=gold, bevel=.006, segs=1, out=cur)
    # ---- front-left panel: framed sample strip, coin slot, photo slot with a printed strip hanging out
    L.panel("StripFrame", .24, .64, .014, .02, loc=(.31, YF + .005, 1.3), paint=gold, bevel=.004)
    L.panel("Strip", .21, .61, .016, .012, loc=(.31, YF + .012, 1.3), paint=strip, bevel=.003)
    L.panel("CoinPlate", .2, .1, .016, .015, loc=(.31, YF + .005, .86), paint=chrome, bevel=.004)
    dv4.cube("CoinSlot", (.05, .012, .008), loc=(.27, YF + .014, .86), paint=rubber, bevel=.002)
    dv4.cylinder("CoinCup", .02, .01, loc=(.345, YF + .012, .86), rot=(-90, 0, 0), seg=12, paint=rubber, bevel=.003)
    L.panel("PhotoSlot", .22, .05, .016, .012, loc=(.31, YF + .005, .66), paint=dark, bevel=.004)
    L.panel("Print", .15, .22, .004, .006, loc=(.31, YF + .03, .55), rot=(-8, 0, 0), paint=printp, bevel=.001)
    # ---- inside: stool, camera wall on the +X side (behind the front panel), flash, screen, back cushion
    dv4.cylinder("StoolBase", .14, .025, loc=(-.1, -.05, .09), seg=18, paint=chrome, bevel=.008)
    dv4.cylinder("StoolPole", .022, .32, loc=(-.1, -.05, .11), seg=10, paint=chrome)
    dv4.lathe("StoolSeat", [(0, 0), (.1, 0), (.16, .02), (.17, .06), (.15, .09), (.08, .105), (0, .11)], seg=20, loc=(-.1, -.05, .43), paint=cushion)
    L.panel("CamWall", .5, 1.0, .03, .02, loc=(.405, -.05, 1.25), rot=(0, 0, 90), paint=cream, bevel=.005)
    L.panel("ScreenBezel", .28, .24, .025, .015, loc=(.39, -.05, 1.35), rot=(0, 0, 90), paint=dark, bevel=.004)
    L.panel("Screen", .24, .2, .012, .01, loc=(.378, -.05, 1.35), rot=(0, 0, 90), paint=screen, bevel=.002)
    dv4.cylinder("CamLens", .05, .04, loc=(.405, -.05, 1.62), rot=(0, -90, 0), seg=16, paint=dark, bevel=.006)
    dv4.cylinder("CamGlass", .03, .01, loc=(.365, -.05, 1.62), rot=(0, -90, 0), seg=12, paint=chrome)
    L.panel("Flash", .16, .1, .012, .01, loc=(.385, .17, 1.62), rot=(0, 0, 90), paint=flashp, bevel=.002)
    dv4.cube("BackCushion", (.8, .08, .36), loc=(0, -.38, .65), paint=cushion, bevel=.03, segs=3)
    return {"name": "PhotoBooth", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
