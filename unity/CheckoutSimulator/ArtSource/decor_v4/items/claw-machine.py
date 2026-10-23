"""claw-machine: pink polka-dot fairground claw machine with a glass cabinet full of cute plush, gold posts with LED
runs, chrome joystick deck, prize chute with a window, painted bear-art side panels, marquee crown with chaser bulbs
(3 "Anim Blink" nodes) and the claw on "Anim Spin". Footprint half .49 x .49, height <= 2.25 (Blender: front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
import _lib_C as L
from dv4 import RNG, MATH, MIX, SMOOTH, NOISE

CONFIG = {"floor": "F4EFE4", "seed": 19}
PINK, NAVY, GOLD, CREAM, INK = "EE8FAE", "1D2B4F", "E0B040", "F4EFE4", "20242B"


def art_side(c):
    """Navy panel with a bear face, gold pinstripe, stars and hearts (both sides, mirrored)."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, 0, .56), (0, 1, 0), (0, 0, 1))
    col = L.RAMP(nt, NOISE(nt, c.pos, 3.0, 2.0), [(.3, "172340"), (.55, NAVY), (.85, "2A3B66")])
    col = L.over(nt, col, L.cut(nt, L.rect(nt, u, v, .285, .255, .04), L.rect(nt, u, v, .272, .242, .035)), GOLD)
    for sx in (-1, 1):
        col = L.over(nt, col, L.circle(nt, u, v, .04, cx=sx * .08, cy=.085), "C98A4E")
        col = L.over(nt, col, L.circle(nt, u, v, .02, cx=sx * .08, cy=.085), "F2A0B8")
    col = L.over(nt, col, L.circle(nt, u, v, .105), "C98A4E")
    col = L.over(nt, col, L.circle(nt, u, v, .052, cy=-.04), "F6E7C8")
    for sx in (-1, 1):
        col = L.over(nt, col, L.circle(nt, u, v, .013, cx=sx * .04, cy=.03), INK)
        col = L.over(nt, col, L.circle(nt, u, v, .02, cx=sx * .07, cy=-.015), "F2A0B8")
    col = L.over(nt, col, L.circle(nt, u, v, .016, cy=-.022), INK)
    col = L.over(nt, col, L.smile(nt, u, v, .024, .005, cy=-.045), INK)
    for sx in (-1, 1):
        for sy in (-1, 1):
            col = L.over(nt, col, L.star(nt, u, v, .032, cx=sx * .215, cy=sy * .17), GOLD)
    for sy in (-1, 1):
        col = L.over(nt, col, L.heart(nt, u, v, .02, cy=sy * .195 - .004), "F2A0B8")
    return col


def art_marquee(axis):
    """Navy marquee insert: gold pinstripe + two pink stars beside the 3D gold star."""
    def r(c):
        nt = c.nt
        u, v = L.plane_uv(c, (0, 0, 2.165), (1, 0, 0) if axis == "x" else (0, 1, 0), (0, 0, 1))
        col = L.RAMP(nt, NOISE(nt, c.pos, 3.0, 2.0), [(.3, "172340"), (.55, NAVY), (.85, "2A3B66")])
        col = L.over(nt, col, L.cut(nt, L.rect(nt, u, v, .235, .045, .02), L.rect(nt, u, v, .225, .036, .016)), GOLD)
        for sx in (-1, 1):
            col = L.over(nt, col, L.star(nt, u, v, .026, cx=sx * .15), "F2A0B8")
            col = L.over(nt, col, L.heart(nt, u, v, .009, cx=sx * .075, cy=-.003), "F2A0B8")
        return col
    return r


def art_deck(c):
    nt = c.nt
    u, v = L.plane_uv(c, (0, .40, 1.03), (1, 0, 0), (0, .951, -.309))
    col = L.RAMP(nt, NOISE(nt, c.pos, 3.0, 2.0), [(.3, "172340"), (.55, NAVY), (.85, "2A3B66")])
    col = L.over(nt, col, L.cut(nt, L.rect(nt, u, v, .37, .11, .03), L.rect(nt, u, v, .36, .1, .026)), GOLD)
    col = L.over(nt, col, L.star(nt, u, v, .026, cx=-.15, cy=.0), GOLD)
    col = L.over(nt, col, L.circle(nt, u, v, .075, cx=.2, cy=-.02), "16213D")
    return col


def art_flap(c):
    """Navy chute flap with a pale window and a reflection streak."""
    nt = c.nt
    u, v = L.plane_uv(c, (-.17, .47, .44), (1, 0, 0), (0, 0, 1))
    col = L.RAMP(nt, NOISE(nt, c.pos, 3.0, 2.0), [(.3, "172340"), (.55, NAVY), (.85, "2A3B66")])
    win = L.rect(nt, u, v, .095, .04, .012, cy=.045)
    col = L.over(nt, col, win, "C9E6F2")
    streak = MATH(nt, "MULTIPLY", win, L.band(nt, MATH(nt, "ADD", u, MATH(nt, "MULTIPLY", v, 1.4)), -.03, -.005))
    col = L.over(nt, col, streak, "F4FBFF")
    col = L.over(nt, col, L.cut(nt, L.rect(nt, u, v, .1, .045, .014, cy=.045), L.rect(nt, u, v, .095, .04, .012, cy=.045)), "C9D2D6")
    return col


def art_postled(c):
    """Gold post with a run of coloured LED dots on the customer-facing face."""
    nt = c.nt
    col = L.RAMP(nt, NOISE(nt, c.pos, 10.0, 2.0), [(.2, "A8781F"), (.55, GOLD), (.9, "FFE38A")])
    col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, .9), .4), col, "FFE38A")
    u = MATH(nt, "SUBTRACT", MATH(nt, "ABSOLUTE", c.x), .42)
    zz = MATH(nt, "SUBTRACT", c.z, 1.075)
    v = MATH(nt, "SUBTRACT", MATH(nt, "MODULO", MATH(nt, "ADD", zz, 9.0), .09), .045)
    idx = MATH(nt, "DIVIDE", MATH(nt, "MODULO", MATH(nt, "FLOOR", MATH(nt, "DIVIDE", MATH(nt, "ADD", zz, 9.0), .09)), 3.0), 3.0)
    dotcol = L.RAMP(nt, idx, [(0.0, "D74A3C"), (.333, "1F9A8E"), (.666, "FBF8F1")], "CONSTANT")
    m = MATH(nt, "MULTIPLY", L.circle(nt, u, v, .012), L.facing(c, (0, 1, 0)))
    m = MATH(nt, "MULTIPLY", m, L.band(nt, c.z, 1.06, 2.0))
    sock = MATH(nt, "MULTIPLY", L.circle(nt, u, v, .016), L.facing(c, (0, 1, 0)))
    sock = MATH(nt, "MULTIPLY", sock, L.band(nt, c.z, 1.06, 2.0))
    col = L.over(nt, col, sock, "6B4F12")
    return MIX(nt, m, col, dotcol)


def art_cap(c):
    """Gold cap top: navy rounded panel with a big gold star, pink hearts and little stars (what the game camera sees)."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, 0, 2.25), (-1, 0, 0), (0, -1, 0))
    col = L.RAMP(nt, NOISE(nt, c.pos, 10.0, 2.0), [(.2, "A8781F"), (.55, GOLD), (.9, "FFE38A")])
    col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, .9), .4), col, "FFE38A")
    top = L.facing(c, (0, 0, 1))
    pan = MATH(nt, "MULTIPLY", top, L.rect(nt, u, v, .4, .4, .06))
    col = L.over(nt, col, pan, NAVY)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.cut(nt, L.rect(nt, u, v, .37, .37, .05), L.rect(nt, u, v, .355, .355, .045))), GOLD)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.star(nt, u, v, .17, .48)), GOLD)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.star(nt, u, v, .12, .48)), "FFE38A")
    for sx in (-1, 1):
        for sy in (-1, 1):
            col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.heart(nt, u, v, .024, cx=sx * .27, cy=sy * .27 - .005)), "F2A0B8")
        col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.star(nt, u, v, .035, cx=sx * .29, cy=0)), "F2A0B8")
        col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.star(nt, u, v, .035, cx=0, cy=sx * .29)), "F2A0B8")
    return col


def build():
    L.install_fix()
    dv4.FINISH.update(ao=.6, ao_dist=.22, light=.34)
    pink = L.paint_sparkle("Pink", "EC86A8", dot="FFF3F7", scale=20.0, size=.3, amt=.85, keep=.45)
    gold = dv4.paint_gold("Gold")
    chrome = L.paint_chrome("Chrome")
    rubber = L.paint_rubber("Rubber")
    cream = L.paint_enamel("Cream", CREAM, sheen=.1)
    dark = L.paint_enamel("Dark", "2F3A40", sheen=.15)
    red = L.paint_enamel("Red", "D74A3C", sheen=.35)
    yellow = L.paint_enamel("Yellow", "F2B03D", sheen=.35)
    green = L.paint_enamel("Green", "5A9D33", sheen=.35)
    side = L.uv_weight(dv4.paint("SideArt", art_side, edge="5A6B9E", edge_k=.5), 1.8)
    marq_x = L.uv_weight(dv4.paint("MarqX", art_marquee("x"), edge="5A6B9E", edge_k=.5), 1.6)
    marq_y = L.uv_weight(dv4.paint("MarqY", art_marquee("y"), edge="5A6B9E", edge_k=.5), 1.6)
    deck = L.uv_weight(dv4.paint("Deck", art_deck, edge="5A6B9E", edge_k=.5), 1.4)
    flap = L.uv_weight(dv4.paint("Flap", art_flap, edge="5A6B9E", edge_k=.5), 1.5)
    postled = L.uv_weight(dv4.paint("PostLED", art_postled, edge="FFE38A", edge_k=.8, edge_r=.006), 1.5)
    slot = L.paint_bright("Slot", lambda c: "7CE08A")
    cap = L.uv_weight(dv4.paint("CapArt", art_cap, edge="FFE38A", edge_k=1.0, edge_r=.006), 1.3)
    light = L.paint_bright("Light", lambda c: "FFF7D8")
    glow = "E_FFE9B0"

    # ---- base, cabinet, belt, floor (the glass case is set back to y .27 so the console sits in front of it)
    dv4.cube("Base", (.92, .92, .08), loc=(0, 0, .04), paint=rubber, bevel=.02, segs=1)
    dv4.cube("Kick", (.8, .024, .03), loc=(0, .465, .05), paint=chrome, bevel=.006, segs=1)
    dv4.cube("Cabinet", (.90, .90, .9), loc=(0, 0, .53), paint=pink, bevel=.05, segs=3)
    dv4.cube("Belt", (.93, .93, .04), loc=(0, 0, .99), paint=gold, bevel=.012, segs=2)
    dv4.cube("Floor", (.84, .70, .03), loc=(0, -.07, 1.025), paint=cream, bevel=.006, segs=1)
    # chute hole in the case floor (front-right corner, Blender -X)
    L.panel("ChuteRim", .2, .2, .01, .02, loc=(-.3, .15, 1.042), rot=(90, 0, 0), paint=chrome, bevel=.003)
    L.panel("ChuteHole", .17, .17, .008, .015, loc=(-.3, .15, 1.046), rot=(90, 0, 0), paint=rubber, bevel=.002)
    # ---- side art (both sides): gold frame + navy painted bear panel
    for sx in (-1, 1):
        L.panel("SideFrame%d" % sx, .7, .64, .012, .05, loc=(sx * .455, 0, .56), rot=(0, 0, -90 * sx), paint=gold, bevel=.004)
        L.panel("SideArt%d" % sx, .62, .56, .02, .04, loc=(sx * .462, 0, .56), rot=(0, 0, -90 * sx), paint=side, bevel=.005)
    # ---- front: coin door (customer's left = +X) and prize chute (right = -X)
    L.panel("CoinDoor", .18, .26, .016, .02, loc=(.3, .457, .6), paint=chrome, bevel=.004)
    L.panel("CoinPlate", .15, .22, .01, .015, loc=(.3, .466, .6), paint=dark, bevel=.003)
    L.panel("CoinSlot", .035, .07, .006, .008, loc=(.3, .473, .66), paint=slot, bevel=.002)
    dv4.cylinder("CoinCup", .024, .012, loc=(.3, .47, .54), rot=(-90, 0, 0), seg=12, paint=rubber, bevel=.003)
    dv4.cylinder("CoinCupIn", .016, .006, loc=(.3, .478, .54), rot=(-90, 0, 0), seg=10, paint=chrome)
    L.panel("ChuteFrame", .36, .36, .018, .035, loc=(-.17, .458, .45), paint=chrome, bevel=.005)
    L.panel("ChuteRecess", .31, .31, .01, .025, loc=(-.17, .466, .45), paint=rubber, bevel=.003)
    L.panel("ChuteFlap", .27, .25, .012, .02, loc=(-.17, .472, .44), paint=flap, bevel=.004)
    dv4.cylinder("Handle", .008, .2, loc=(-.27, .482, .355), rot=(0, 90, 0), seg=8, paint=chrome)
    for sx in (-1, 1):
        dv4.cylinder("HandleLeg%d" % sx, .006, .02, loc=(-.17 + sx * .09, .466, .355), rot=(-90, 0, 0), seg=6, paint=chrome)
    L.star_prism("Badge", .045, .45, .014, loc=(-.17, .457, .66), paint=gold)
    # ---- control deck (sloped navy panel in front of the glass): joystick + two domed buttons
    dv4.cube("Deck", (.78, .16, .08), loc=(0, .40, 1.03), rot=(-18, 0, 0), paint=deck, bevel=.018, segs=3)
    F = L.Frame((0, .40, 1.03), (-18, 0, 0))
    dv4.cylinder("JoyBase", .05, .016, loc=F.p((.2, -.03, .04)), rot=F.r(), seg=16, paint=chrome, bevel=.004)
    dv4.lathe("JoyBoot", [(0, 0), (.034, 0), (.03, .02), (.019, .045), (.015, .06)], seg=12, loc=F.p((.2, -.03, .055)), rot=F.r(), paint=rubber)
    dv4.cylinder("JoyStick", .011, .1, loc=F.p((.2, -.03, .1)), rot=F.r(), seg=8, paint=chrome)
    dv4.sphere("JoyBall", .044, loc=F.p((.2, -.03, .225)), seg=12, rings=8, paint=red)
    for x, p in ((-.06, yellow), (-.24, green)):
        dv4.cylinder("Bezel%s" % x, .062, .012, loc=F.p((x, -.02, .04)), rot=F.r(), seg=16, paint=chrome, bevel=.003)
        dv4.sphere("Button%s" % x, .05, loc=F.p((x, -.02, .05)), scale=(1, 1, .5), seg=12, rings=7, paint=p, rot=F.r())
    # ---- case: gold posts (front ones with LED runs), glass on three sides, pink back wall, ceiling with light
    for sx in (-1, 1):
        for sy, yy in ((-1, -.42), (1, .27)):
            dv4.cube("Post%d%d" % (sx, sy), (.06, .06, 1.02), loc=(sx * .42, yy, 1.55), paint=postled if sy > 0 else gold, bevel=.012, segs=2)
    dv4.cube("GlassF", (.78, .012, .98), loc=(0, .27, 1.55), paint=None, bevel=0, mat_override="G_Glass")
    for sx in (-1, 1):
        dv4.cube("GlassS%d" % sx, (.012, .63, .98), loc=(sx * .42, -.075, 1.55), paint=None, bevel=0, mat_override="G_Glass")
    dv4.cube("BackWall", (.78, .04, .98), loc=(0, -.42, 1.55), paint=pink, bevel=.006, segs=1)
    dv4.cube("Ceiling", (.92, .92, .06), loc=(0, 0, 2.09), paint=pink, bevel=.015, segs=2)
    dv4.cube("Lamp", (.56, .07, .014), loc=(0, -.02, 2.055), paint=None, bevel=.003, mat_override=glow)
    dv4.cube("LampTrim", (.6, .1, .016), loc=(0, -.02, 2.062), paint=chrome, bevel=.004)
    dv4.cube("Lamp2", (.56, .05, .014), loc=(0, .37, 2.055), paint=None, bevel=.003, mat_override=glow)   # downlight over the console
    # ---- gantry + claw ("Anim Spin", pivot on the cable axis)
    for sy in (-.3, .14):
        dv4.cylinder("Rail%s" % sy, .012, .72, loc=(-.36, sy, 1.98), rot=(0, 90, 0), seg=8, paint=chrome)
    dv4.cylinder("Cross", .012, .44, loc=(.12, -.3, 1.98), rot=(-90, 0, 0), seg=8, paint=chrome)
    dv4.cube("Trolley", (.14, .1, .06), loc=(.12, -.06, 1.955), paint=dark, bevel=.012, segs=2)
    dv4.cylinder("Cable", .004, .17, loc=(.12, -.06, 1.76), seg=6, paint=rubber)
    spin = "Anim Spin"; dv4.pivot(spin, (.12, -.06, 1.76))
    dv4.lathe("ClawCap", [(0, 1.715), (.04, 1.715), (.046, 1.745), (.032, 1.762), (0, 1.762)], seg=14, loc=(.12, -.06, 0), paint=chrome, out=spin)
    dv4.lathe("ClawHub", [(0, 1.655), (.02, 1.655), (.03, 1.715), (0, 1.715)], seg=10, loc=(.12, -.06, 0), paint=rubber, out=spin)
    for q in range(3):
        a = math.radians(q * 120 + 30); dx, dy = math.cos(a), math.sin(a)
        pts = [(.12 + dx * .02, -.06 + dy * .02, 1.69), (.12 + dx * .075, -.06 + dy * .075, 1.635), (.12 + dx * .088, -.06 + dy * .088, 1.57), (.12 + dx * .05, -.06 + dy * .05, 1.515)]
        dv4.tube("Finger%d" % q, pts, radius=.0095, res=6, paint=chrome, out=spin, resolution=3, taper=[(0, 1.0), (.6, .9), (1, .45)])
    # ---- plush pile
    furs = {k: L.paint_fur("Fur" + k, v) for k, v in dict(Honey="D9A066", Snow="F4EFE4", Grey="9A9AA3", Yellow="F2C23F", Pink="F2A0B8",
                                                            Mint="7FBF6A", Cocoa="6F4A2E", Lilac="B9A7DE", Sky="7BD3F7", Peach="F7B98A").items()}
    P = {"ink": L.uv_weight(L.cyl_uv(L.paint_enamel("Ink", INK, sheen=.5, speck=0)), .4), "cream": L.paint_fur("FurCream", "F6E7C8"), "pink": L.paint_fur("FurPink", "F2A0B8"),
         "orange": L.cyl_uv(L.paint_enamel("Orange", "EC862E", sheen=.3)), "white": L.paint_fur("FurWhite", "F8F5EE"), "black": L.paint_fur("FurBlack", "2A2A30")}
    kinds = [("bear", "Honey"), ("bunny", "Snow"), ("cat", "Grey"), ("duck", "Yellow"), ("pig", "Pink"), ("frog", "Mint"), ("panda", "Snow"),
             ("bear", "Cocoa"), ("bunny", "Lilac"), ("cat", "Peach"), ("bear", "Sky"), ("bunny", "Pink"), ("pig", "Peach"), ("frog", "Yellow"),
             ("cat", "Snow"), ("bear", "Lilac"), ("duck", "Snow"), ("panda", "Snow")]
    k = 0
    for i in range(4):          # buried layer: heads peeking out of the pile
        for j in range(3):
            x = -.27 + i * .18 + RNG.uniform(-.03, .03); y = -.3 + j * .2 + RNG.uniform(-.03, .03)
            if x < -.15 and y > .0:
                continue
            kind, col = kinds[k % len(kinds)]
            L.plush(kind, L.Frame((x, y, .985), (RNG.uniform(-25, 25), RNG.uniform(-25, 25), RNG.uniform(-60, 60)), .9), furs[col], P, full=False, tag="b%d" % k)
            k += 1
    tops = [(-.22, -.14), (.02, -.26), (.26, -.18), (.3, .08), (.08, -.02), (.26, .15), (-.1, .12), (-.3, -.3)]
    for i, (x, y) in enumerate(tops):       # top layer: full plush leaning every which way
        kind, col = kinds[(k + i) % len(kinds)]
        L.plush(kind, L.Frame((x, y, 1.04), (RNG.uniform(-30, 30), RNG.uniform(-30, 30), RNG.uniform(-80, 80)), .95), furs[col], P, full=True, tag="t%d" % i)
    # ---- marquee crown: navy inserts with gold 3D stars, chaser bulbs on three Blink nodes, gold cap
    dv4.cube("Crown", (.92, .92, .13), loc=(0, 0, 2.165), paint=pink, bevel=.035, segs=3)
    dv4.cube("Cap", (.98, .98, .025), loc=(0, 0, 2.2375), paint=cap, bevel=.008, segs=2)
    for sy in (-1, 1):
        L.panel("MarqY%d" % sy, .5, .1, .02, .03, loc=(0, sy * .465, 2.165), rot=(0, 0, 0 if sy > 0 else 180), paint=marq_x, bevel=.004)
        L.star_prism("StarY%d" % sy, .05, .45, .016, loc=(0, sy * .478, 2.165), rot=(0, 0, 0 if sy > 0 else 180), paint=gold)
    for sx in (-1, 1):
        L.panel("MarqX%d" % sx, .5, .1, .02, .03, loc=(sx * .465, 0, 2.165), rot=(0, 0, -90 * sx), paint=marq_y, bevel=.004)
        L.star_prism("StarX%d" % sx, .05, .45, .016, loc=(sx * .478, 0, 2.165), rot=(0, 0, -90 * sx), paint=gold)
    nodes = ["Anim Blink", "Anim Blink.001", "Anim Blink.002"]
    n = 0
    for i in range(11):
        t = -.4 + i * .08
        for p in ((t, .468, 2.215), (t, -.468, 2.215), (.468, t, 2.215), (-.468, t, 2.215)):
            L.bulb("Bulb%d" % n, p, .017, out=nodes[n % 3], glow=glow); n += 1
    return {"name": "ClawMachine", "tex": 1024, "budget": 15000, "floor": "F4EFE4"}
