"""atm: bank ATM kiosk - brushed-steel cabinet with a teal wrap band, teal fascia with a hooded glowing screen
(icon-only UI), side keys, tilted keypad, lit card slot, receipt slot, cash slot with a banknote peeking out, speaker
grille, navy service door with lock, navy canopy with a lit pictogram sign and a downlight. Body only.
Footprint half .37 x .42, height <= 2.0 (Blender: front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
import _lib_C as L
from dv4 import RNG, MATH, MIX, SMOOTH, NOISE

CONFIG = {"floor": "F4EFE4", "seed": 7}
NAVY, GOLD, CREAM, TEAL, INK, GREEN = "1D2B4F", "E0B040", "F4EFE4", "1F9A8E", "20242B", "5A9D33"
YF = .255            # cabinet front face (y)
SCR = (0, YF + .085, 1.3)
SUP = (0, .139, .990)       # screen up vector (tilted back 8 deg)


def art_screen(c):
    """Glowing bank UI: teal header with a coin, white card tiles with icons, green confirm bar, arrows."""
    nt = c.nt
    u, v = L.plane_uv(c, SCR, (1, 0, 0), SUP)
    col = L.RAMP(nt, MATH(nt, "ADD", MATH(nt, "MULTIPLY", v, 1.5), .5), [(0.0, "1B6FB0"), (1.0, "3FA3D8")])
    col = L.over(nt, col, L.rect(nt, u, v, .2, .035, .0, cy=.125), "17857A")
    col = L.over(nt, col, L.circle(nt, u, v, .022, cx=-.165, cy=.125), GOLD)
    col = L.over(nt, col, L.ring(nt, u, v, .013, .017, cx=-.165, cy=.125), "A8781F")
    col = L.over(nt, col, L.rect(nt, u, v, .07, .012, .005, cx=.0, cy=.125), "F4EFE4")
    col = L.over(nt, col, L.rect(nt, u, v, .03, .012, .005, cx=.14, cy=.125), "F4EFE4")
    for i, (cx, cy) in enumerate(((-.095, .03), (.095, .03), (-.095, -.07), (.095, -.07))):
        col = L.over(nt, col, L.rect(nt, u, v, .08, .038, .012, cx=cx, cy=cy), "F6F8FA")
    # tile icons: card, banknote, coin stack, arrows
    col = L.over(nt, col, L.rect(nt, u, v, .04, .024, .006, cx=-.115, cy=.03), NAVY)
    col = L.over(nt, col, L.rect(nt, u, v, .04, .005, .0, cx=-.115, cy=.038), GOLD)
    col = L.over(nt, col, L.rect(nt, u, v, .045, .022, .004, cx=.075, cy=.03), GREEN)
    col = L.over(nt, col, L.circle(nt, u, v, .011, cx=.075, cy=.03), "C9E8B0")
    for k in range(3):
        col = L.over(nt, col, L.rect(nt, u, v, .03, .006, .003, cx=-.115, cy=-.084 + k * .013), GOLD)
    col = L.over(nt, col, L.tri_up(nt, u, v, .02, .024, cx=.062, cy=-.066), "EC862E")
    col = L.over(nt, col, L.rect(nt, u, v, .008, .012, 0, cx=.062, cy=-.086), "EC862E")
    col = L.over(nt, col, L.rect(nt, u, v, .02, .012, 0, cx=.105, cy=-.072), "D74A3C")
    col = L.over(nt, col, L.tri_up(nt, u, v, .012, .018, cx=.105, cy=-.09), "D74A3C")
    col = L.over(nt, col, L.rect(nt, u, v, .19, .018, .009, cy=-.135), "5A9D33")
    col = L.over(nt, col, L.circle(nt, u, v, .009, cx=-.16, cy=-.135), "D7F0C0")
    col = L.over(nt, col, L.rect(nt, u, v, .05, .005, .002, cx=.02, cy=-.135), "D7F0C0")
    return col


def art_sign(c):
    """Lit canopy sign: card + banknote + coin pictograms on cream."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, .25, 1.79), (1, 0, 0), (0, 0, 1))
    col = L.RAMP(nt, NOISE(nt, c.pos, 4.0, 1.0), [(.3, "F7F2E6"), (.8, "FFFBF2")])
    col = L.over(nt, col, L.rect(nt, u, v, .085, .055, .012, cx=-.18, cy=0), NAVY)
    col = L.over(nt, col, L.rect(nt, u, v, .085, .011, .0, cx=-.18, cy=.02), GOLD)
    col = L.over(nt, col, L.rect(nt, u, v, .04, .009, .003, cx=-.205, cy=-.022), "C9D2D6")
    col = L.over(nt, col, L.rect(nt, u, v, .095, .05, .008, cx=.03, cy=0), GREEN)
    col = L.over(nt, col, L.cut(nt, L.rect(nt, u, v, .086, .041, .006, cx=.03, cy=0), L.rect(nt, u, v, .08, .035, .005, cx=.03, cy=0)), "C9E8B0")
    col = L.over(nt, col, L.circle(nt, u, v, .024, cx=.03, cy=0), "C9E8B0")
    col = L.over(nt, col, L.circle(nt, u, v, .034, cx=.21, cy=0), GOLD)
    col = L.over(nt, col, L.ring(nt, u, v, .02, .026, cx=.21, cy=0), "A8781F")
    col = L.over(nt, col, L.star(nt, u, v, .012, cx=.21, cy=0), "A8781F")
    return col


def art_fascia(c):
    """Teal enamel with a speaker grille, a gold pinstripe and small pictograms beside the slots."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, YF + .03, 1.22), (1, 0, 0), (0, 0, 1))
    col = L.RAMP(nt, NOISE(nt, c.pos, 2.5, 2.0), [(.3, "17857A"), (.5, TEAL), (.8, "3DB3A6")])
    col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 140.0, 1.0), .05), col, "5BC2B4")
    col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, 1.0), .2), col, "5BC2B4")
    col = L.over(nt, col, L.cut(nt, L.rect(nt, u, v, .3, .35, .03), L.rect(nt, u, v, .292, .342, .026)), GOLD)
    gu = MATH(nt, "SUBTRACT", MATH(nt, "MODULO", MATH(nt, "ADD", u, 9.0), .016), .008)
    gv = MATH(nt, "SUBTRACT", MATH(nt, "MODULO", MATH(nt, "ADD", v, 9.0), .016), .008)
    grille = MATH(nt, "MULTIPLY", L.circle(nt, gu, gv, .004), L.rect(nt, u, v, .035, .03, .0, cx=-.24, cy=.31))
    col = L.over(nt, col, grille, "0F4A44")
    col = L.over(nt, col, L.rect(nt, u, v, .024, .015, .004, cx=.245, cy=-.185), GOLD)        # card pictogram next to the card slot
    col = L.over(nt, col, L.rect(nt, u, v, .024, .003, .0, cx=.245, cy=-.18), NAVY)
    col = L.over(nt, col, L.tri_up(nt, u, v, .012, .016, cx=.245, cy=-.215), CREAM)
    return col


def art_door(c):
    """Navy service door: panel seams and a gold pinstripe."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, YF, .42), (1, 0, 0), (0, 0, 1))
    col = L.RAMP(nt, NOISE(nt, c.pos, 3.0, 2.0), [(.3, "172340"), (.55, NAVY), (.85, "2A3B66")])
    col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, 1.0), .15), col, "3A4D80")
    col = L.over(nt, col, L.cut(nt, L.rect(nt, u, v, .27, .2, .02), L.rect(nt, u, v, .263, .193, .017)), GOLD)
    col = L.over(nt, col, L.rect(nt, u, v, .2, .0025, 0, cy=-.12), "0E1730")
    return col


def art_note(c):
    """Banknote: green with an oval, cream border, no text."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, YF + .06, .905), (1, 0, 0), (0, .4, .9))
    col = L.RAMP(nt, NOISE(nt, c.pos, 30.0, 1.0), [(.3, "C9E8B0"), (.8, "DDF2C8")])
    col = L.over(nt, col, L.rect(nt, u, v, .13, .035, .004), GREEN)
    col = L.over(nt, col, L.circle(nt, u, v, .02), "C9E8B0")
    col = L.over(nt, col, L.circle(nt, u, v, .012), "7FBF6A")
    for sx in (-1, 1):
        col = L.over(nt, col, L.circle(nt, u, v, .009, cx=sx * .1), "C9E8B0")
    return col


def art_cap(c):
    """Gold cap top: navy panel with a gold coin and a cream bank card (seen from the game camera; up = away from the customer)."""
    nt = c.nt
    u, v = L.plane_uv(c, (0, -.03, 1.97), (-1, 0, 0), (0, -1, 0))
    col = L.RAMP(nt, NOISE(nt, c.pos, 10.0, 2.0), [(.2, "A8781F"), (.55, GOLD), (.9, "FFE38A")])
    col = MIX(nt, MATH(nt, "MULTIPLY", SMOOTH(nt, c.nz, .2, .9), .4), col, "FFE38A")
    top = L.facing(c, (0, 0, 1))
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.rect(nt, u, v, .3, .23, .04)), NAVY)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.cut(nt, L.rect(nt, u, v, .28, .21, .035), L.rect(nt, u, v, .268, .198, .03))), GOLD)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.circle(nt, u, v, .075, cx=-.13)), GOLD)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.ring(nt, u, v, .05, .06, cx=-.13)), "A8781F")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.star(nt, u, v, .03, cx=-.13)), "A8781F")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.rect(nt, u, v, .11, .07, .012, cx=.1)), "F4EFE4")
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.rect(nt, u, v, .11, .014, 0, cx=.1, cy=.03)), TEAL)
    col = L.over(nt, col, MATH(nt, "MULTIPLY", top, L.rect(nt, u, v, .03, .012, .003, cx=.03, cy=-.025)), GOLD)
    return col


def build():
    L.install_fix()
    dv4.FINISH.update(ao=.6, ao_dist=.22, light=.36)
    steel = L.paint_brushed("Steel")
    chrome = L.paint_chrome("Chrome")
    rubber = L.paint_rubber("Rubber")
    dark = L.paint_enamel("Dark", "2F3A40", sheen=.15)
    gold = dv4.paint_gold("Gold")
    navy = L.paint_enamel("Navy", NAVY)
    teal = L.paint_enamel("Teal", TEAL)
    cream = L.paint_enamel("Cream", CREAM, sheen=.1)
    key_c = L.paint_enamel("KeyCream", "F7F3EA", sheen=.3); key_r = L.paint_enamel("KeyRed", "D74A3C", sheen=.3)
    key_g = L.paint_enamel("KeyGreen", GREEN, sheen=.3); key_y = L.paint_enamel("KeyGold", GOLD, sheen=.3)
    fascia = L.uv_weight(dv4.paint("Fascia", art_fascia, edge="5BC2B4", edge_k=.7), 1.3)
    door = dv4.paint("Door", art_door, edge="5A6B9E", edge_k=.6)
    screen = L.uv_weight(L.paint_bright("Screen", art_screen), 2.0)
    sign = L.uv_weight(L.paint_bright("Sign", art_sign), 1.8)
    note = L.uv_weight(dv4.paint("Note", art_note, k_ao=.3, k_light=.2), 1.6)
    paper = L.paint_enamel("Paper", "FBF8F1", sheen=.0, speck=0)
    cap = L.uv_weight(dv4.paint("CapArt", art_cap, edge="FFE38A", edge_k=1.0, edge_r=.006), 1.3)
    glow_g, glow_w = "E_7CE08A", "E_FFF1C8"

    # ---- plinth + cabinet (y -.325 .. +.255), kick plate, gold belt under the canopy
    dv4.cube("Plinth", (.72, .62, .08), loc=(0, -.035, .04), paint=rubber, bevel=.02, segs=2)
    dv4.cube("Cabinet", (.70, .58, 1.6), loc=(0, -.035, .88), paint=steel, bevel=.04, segs=3)
    dv4.cube("Kick", (.62, .03, .05), loc=(0, YF - .01, .11), paint=dark, bevel=.008, segs=2)
    dv4.cube("Belt", (.72, .60, .035), loc=(0, -.035, 1.665), paint=gold, bevel=.01, segs=2)
    # teal wrap band around the top of the cabinet with a gold line
    dv4.cube("Wrap", (.705, .585, .07), loc=(0, -.035, 1.6), paint=teal, bevel=.012, segs=2)
    # ---- lower service door with lock + seams
    L.panel("Door", .6, .46, .02, .03, loc=(0, YF + .005, .42), paint=door, bevel=.005)
    dv4.cylinder("Lock", .018, .012, loc=(.2, YF + .015, .3), rot=(-90, 0, 0), seg=12, paint=chrome, bevel=.003)
    dv4.cube("LockSlot", (.004, .008, .02), loc=(.2, YF + .028, .3), paint=rubber, bevel=.001)
    # ---- fascia: teal panel, screen bezel tilted back 8 deg under a privacy hood
    L.panel("Fascia", .64, .76, .06, .04, loc=(0, YF + .03, 1.22), paint=fascia, bevel=.012)
    L.panel("Bezel", .5, .4, .04, .025, loc=(0, YF + .07, 1.3), rot=(8, 0, 0), paint=dark, bevel=.008)
    L.panel("Screen", .42, .3, .012, .012, loc=SCR, rot=(8, 0, 0), paint=screen, bevel=.002)
    dv4.cube("HoodTop", (.54, .12, .03), loc=(0, YF + .105, 1.53), rot=(6, 0, 0), paint=dark, bevel=.01, segs=2)
    for sx in (-1, 1):
        dv4.cube("HoodSide%d" % sx, (.03, .11, .4), loc=(sx * .255, YF + .105, 1.33), rot=(0, 0, 0), paint=dark, bevel=.008, segs=2)
        for i in range(4):
            dv4.cube("SideKey%d%d" % (sx, i), (.035, .02, .024), loc=(sx * .275, YF + .065, 1.18 + i * .07), paint=chrome, bevel=.005, segs=2)
    # status LED beside the screen
    dv4.sphere("LED", .011, loc=(.235, YF + .066, 1.5), seg=8, rings=5, paint=None, mat_override=glow_g)
    # ---- keypad tray (tilted 22 deg) with 12 keys + 3 function keys
    F = L.Frame((-.1, YF + .06, 1.0), (-22, 0, 0))
    L.panel("Tray", .36, .19, .035, .02, loc=F.p((0, 0, 0)), rot=F.r((90, 0, 0)), paint=dark, bevel=.008)
    for j in range(4):
        for i in range(3):
            p = key_c if j < 3 else (key_r, key_y, key_g)[i]
            dv4.cube("Key%d%d" % (i, j), (.05, .038, .018), loc=F.p((-.075 + i * .06, .06 - j * .045, .024)), rot=F.r(), paint=p, bevel=.005, segs=2)
    for j in range(3):
        dv4.cube("FKey%d" % j, (.05, .038, .018), loc=F.p((.13, .06 - j * .045, .024)), rot=F.r(), paint=(key_r, key_y, key_g)[j], bevel=.005, segs=2)
    # ---- card slot (lit), receipt slot, cash slot with gold flap and a banknote
    L.panel("CardSlot", .15, .06, .016, .012, loc=(.2, YF + .068, 1.03), paint=chrome, bevel=.004)
    L.panel("CardGlow", .11, .012, .01, .004, loc=(.2, YF + .079, 1.03), paint=None, bevel=.002, mat_override=glow_g)
    L.panel("Receipt", .17, .04, .014, .01, loc=(.2, YF + .067, .95), paint=dark, bevel=.004)
    L.panel("ReceiptPaper", .13, .008, .012, .003, loc=(.2, YF + .072, .95), paint=paper, bevel=.001)
    L.panel("CashFrame", .42, .11, .02, .02, loc=(0, YF + .07, .86), paint=chrome, bevel=.005)
    L.panel("CashRecess", .38, .08, .012, .015, loc=(0, YF + .078, .86), paint=rubber, bevel=.003)
    dv4.cube("CashFlap", (.36, .022, .06), loc=(0, YF + .075, .88), rot=(-55, 0, 0), paint=gold, bevel=.006, segs=2)
    L.panel("Note", .28, .08, .004, .006, loc=(0, YF + .06, .905), rot=(-24, 0, 0), paint=note, bevel=.001)
    # ---- canopy: navy box with lit sign, gold cap, downlight under the front edge
    dv4.cube("Canopy", (.7, .56, .26), loc=(0, -.03, 1.8), paint=navy, bevel=.03, segs=3)
    L.panel("SignFrame", .62, .2, .02, .03, loc=(0, .245, 1.79), paint=gold, bevel=.005)
    L.panel("Sign", .58, .16, .03, .025, loc=(0, .252, 1.79), paint=sign, bevel=.004)
    dv4.cube("Cap", (.74, .6, .04), loc=(0, -.03, 1.95), paint=cap, bevel=.012, segs=2)
    dv4.cube("Downlight", (.5, .05, .014), loc=(0, .22, 1.668), paint=None, bevel=.003, mat_override=glow_w)
    dv4.cube("DownTrim", (.54, .08, .018), loc=(0, .215, 1.674), paint=chrome, bevel=.004)
    return {"name": "Atm", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
