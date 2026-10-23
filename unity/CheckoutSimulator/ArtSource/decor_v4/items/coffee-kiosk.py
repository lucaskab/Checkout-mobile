"""coffee-kiosk: charming coffee cart (outside). Navy-painted plank cart with warm wood trim and a marble top, big spoked wheels,
chrome espresso machine with a red fascia, grinder, cup stacks, syrup bottles, glass pastry case with croissants and cakes,
striped awning on timber posts, chalk menu board with drink/pastry pictograms (no words), festoon bulbs (some on "Anim Blink"),
bar ledge with two stools. Footprint half 1.11 x .71, height <= 3.15 (Blender: X across, front = +Y)."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
import _lib_D as L
from dv4 import RNG

CONFIG = {"floor": "C9C3B8", "seed": 9}


def espresso(x, y, z, chrome, red, black, cream, gold):
    """Two-group espresso machine, ~.5 wide, front toward +Y."""
    dv4.cube("EmBody", (.5, .36, .34), loc=(x, y, z + .2), paint=chrome, bevel=.015, segs=2)
    dv4.cube("EmFascia", (.46, .03, .2), loc=(x, y + .18, z + .17), paint=red, bevel=.01, segs=2)
    dv4.cube("EmTop", (.5, .36, .03), loc=(x, y, z + .385), paint=black, bevel=.008, segs=1)
    dv4.cube("EmTray", (.46, .1, .025), loc=(x, y + .14, z + .015), paint=black, bevel=.006, segs=1)
    for sx in (-1, 1):
        # group head, portafilter with a black handle, steam wand
        dv4.cylinder("EmGroup%d" % sx, .04, .05, loc=(x + sx * .13, y + .17, z + .06), seg=12, paint=chrome)
        dv4.cylinder("EmPf%d" % sx, .045, .018, loc=(x + sx * .13, y + .17, z + .045), seg=12, paint=chrome)
        dv4.cylinder("EmHandle%d" % sx, .012, .11, loc=(x + sx * .13, y + .19, z + .055), rot=(-90, 0, 0), seg=8, paint=black)
        dv4.cube("EmBtn%d" % sx, (.07, .012, .035), loc=(x + sx * .13, y + .2, z + .2), paint=black, bevel=.004, segs=1)
        dv4.sphere("EmLed%d" % sx, .008, loc=(x + sx * .13 + .025, y + .207, z + .215), seg=6, rings=4, paint=None, mat_override="E_FFE6A8")
    dv4.tube("EmWand", [(x + .27, y + .1, z + .22), (x + .3, y + .18, z + .14), (x + .28, y + .22, z + .04)], radius=.007, res=6, paint=chrome, resolution=3)
    dv4.sphere("EmGauge", .028, loc=(x, y + .2, z + .27), scale=(1, .4, 1), seg=10, rings=5, paint=cream)
    dv4.torus("EmGaugeRim", .028, .005, loc=(x, y + .205, z + .27), seg=12, minor=4, paint=gold, rot=(90, 0, 0))
    # cups warming on top
    for i in range(6):
        cx = x - .18 + (i % 3) * .14; cy = y - .1 + (i // 3) * .14
        dv4.lathe("EmCup%d" % i, [(0, 0), (.025, 0), (.033, .05), (.036, .055), (.03, .055), (.028, .05), (0, .05)], seg=10, loc=(cx, cy, z + .4), paint=cream)
        dv4.torus("EmCupH%d" % i, .014, .004, loc=(cx + .038, cy, z + .428), seg=8, minor=4, paint=cream, rot=(0, 90, 0))


def grinder(x, y, z, chrome, black, glassf, cream):
    dv4.lathe("GrBase", [(0, 0), (.07, 0), (.075, .01), (.07, .16), (.05, .2), (.045, .22), (0, .22)], seg=14, loc=(x, y, z), paint=black)
    dv4.lathe("GrHopper", [(0, .22), (.04, .22), (.065, .3), (.07, .34), (.065, .345), (0, .345)], seg=12, loc=(x, y, z), paint=glassf)
    dv4.cylinder("GrLid", .072, .012, loc=(x, y, z + .345), seg=12, paint=black)
    dv4.cube("GrSpout", (.03, .05, .03), loc=(x, y + .08, z + .1), paint=chrome, bevel=.006, segs=1)
    dv4.cylinder("GrDoser", .035, .07, loc=(x, y + .06, z + .14), seg=10, paint=chrome, rot=(-90, 0, 0))


def pastry_case(x, y, z, chrome, glass, wood, crust, pink, cream, choc):
    """Glass vitrine .5 x .36 x .34 with two shelves of pastries (front toward +Y)."""
    dv4.cube("PcBase", (.52, .38, .03), loc=(x, y, z + .015), paint=wood, bevel=.006, segs=1)
    dv4.cube("PcTop", (.52, .38, .025), loc=(x, y, z + .35), paint=wood, bevel=.006, segs=1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.cylinder("PcPost%d%d" % (sx, sy), .009, .32, loc=(x + sx * .245, y + sy * .175, z + .03), seg=6, paint=chrome)
    dv4.cube("PcGlassF", (.48, .006, .3), loc=(x, y + .18, z + .18), paint=None, mat_override="G_Glass", bevel=0)
    for sx in (-1, 1):
        dv4.cube("PcGlassS%d" % sx, (.006, .34, .3), loc=(x + sx * .245, y, z + .18), paint=None, mat_override="G_Glass", bevel=0)
    dv4.cube("PcGlassT", (.48, .34, .006), loc=(x, y, z + .335), paint=None, mat_override="G_Glass", bevel=0)
    dv4.cube("PcBack", (.48, .012, .3), loc=(x, y - .18, z + .18), paint=cream, bevel=0)
    dv4.cube("PcShelf", (.46, .32, .012), loc=(x, y, z + .18), paint=None, mat_override="G_Glass", bevel=0)
    # croissants on the lower shelf, cakes on the upper shelf
    for i in range(3):
        cx = x - .15 + i * .15
        pts = [(cx - .06, y + .05, z + .05), (cx - .03, y + .1, z + .06), (cx + .03, y + .1, z + .06), (cx + .06, y + .05, z + .05)]
        dv4.tube("Croissant%d" % i, pts, radius=.028, res=8, paint=crust, resolution=3, taper=[(0, .5), (.5, 1.0), (1, .5)])
        dv4.cylinder("Muffin%d" % i, .035, .05, loc=(cx, y - .08, z + .03), seg=10, paint=crust, bevel=.01)
        dv4.sphere("MuffinTop%d" % i, .04, loc=(cx, y - .08, z + .08), scale=(1, 1, .6), seg=10, rings=5, paint=choc if i % 2 else crust)
    for i in range(2):
        cx = x - .1 + i * .2
        dv4.cylinder("Cake%d" % i, .06, .05, loc=(cx, y + .02, z + .19), seg=14, paint=pink if i else choc)
        dv4.cylinder("CakeIce%d" % i, .062, .015, loc=(cx, y + .02, z + .24), seg=14, paint=cream if i else pink, bevel=.006)
        for k in range(5):
            a = math.radians(k * 72)
            dv4.sphere("Berry%d%d" % (i, k), .009, loc=(cx + math.cos(a) * .04, y + .02 + math.sin(a) * .04, z + .262), seg=5, rings=3, paint=pink if not i else choc)
    for i in range(4):
        dv4.cube("Cookie%d" % i, (.05, .05, .012), loc=(x + .1 + (i % 2) * .07, y - .1 + (i // 2) * .08, z + .19), paint=crust, bevel=.012, segs=1)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.25, light=.36)
    navy = dv4.paint_wood("NavyPlank", base="24365F", dark="141F3A", light="35508A", scale=4.0, along="Z", edge="4F6AA8", tint=.2, dist=2.0)
    wood = dv4.paint_wood("Wood", base="AB6537", dark="5E3519", light="D69C53", scale=4.0, along="X", edge="E0B585", tint=.25)
    woodd = dv4.paint_wood("WoodDark", base="6E4529", dark="3C2314", light="9A6A40", scale=3.0, along="Z", edge="A98054", tint=.15)
    marble = L.paint_marble("Marble")
    chrome = L.paint_chrome("Chrome")
    black = L.paint_plastic("Black", "2A2E33", light="5C636B", dark="121416", gloss=.3)
    red = L.paint_plastic("Red", "D74A3C", light="F0806F", dark="7E1F16", gloss=.35)
    cream = L.paint_plastic("Cream", "F4EFE4", light="FFFFFF", dark="C9C0AE", gloss=.25)
    gold = dv4.paint_gold("Gold")
    goldp = L.paint_plastic("GoldP", "E6B23A", light="FFE07A", dark="9E6E14", gloss=.3)
    kraft = L.paint_kraft("Kraft")
    glassf = L.paint_glass_fake("Hopper")
    crust = L.paint_plastic("Crust", "D9933F", light="F2C57A", dark="8E5518", gloss=.2)
    choc = L.paint_plastic("Choc", "5A3521", light="8A5A3C", dark="2E1A0E", gloss=.3)
    pink = L.paint_plastic("Pink", "EE8FAE", light="FFC9DA", dark="B05A78", gloss=.3)
    awning = L.paint_stripes("Awning", a="EC862E", b="FBF8F1", width=.22, along="X")
    board = L.paint_chalkboard("Board")
    chalk = L.paint_plastic("Chalk", "F4EFE4", light="FFFFFF", dark="C8C2B4", gloss=.1)
    chalky = L.paint_plastic("ChalkY", "F2D06B", light="FFF0B0", dark="C0A040", gloss=.1)
    chalkp = L.paint_plastic("ChalkP", "F2B8C6", light="FFE0E8", dark="C08898", gloss=.1)
    cord = dv4.paint_flat("Cord", "2F3A40", variation=0)
    leafp = dv4.paint_leaf("Leaf", base="3C8F3C", dark="1E5A29", light="7CC050", vein="C6E6A0", veins=5)
    terra = dv4.paint_terracotta("Pot", glaze=dv4.TEAL, glaze_z=1.05, drip=.03)
    syrups = [L.paint_plastic("Syr%d" % i, c, gloss=.4) for i, c in enumerate(("C8781E", "B9342C", "5A9D33", "5A3521"))]

    W, D, H = 2.0, .9, .92
    # ---- cart body: navy plank box on a dark skirt, wood trim rails + corner posts, marble top with a rounded nosing
    dv4.cube("Skirt", (W - .1, D - .1, .14), loc=(0, 0, .07), paint=woodd, bevel=.01, segs=1)
    dv4.cube("Body", (W, .86 * 0 + D, H - .22), loc=(0, 0, .14 + (H - .22) / 2), paint=navy, bevel=.012, segs=1)
    for i in range(9):      # vertical plank grooves on the front (dark slats proud of the panel)
        dv4.cube("Slat%d" % i, (.02, .012, H - .3), loc=(-.88 + i * .22, D / 2 + .004, .18 + (H - .3) / 2), paint=woodd, bevel=.003, segs=1)
    for z in (.16, H - .1):
        dv4.cube("Rail%s" % z, (W + .04, D + .04, .045), loc=(0, 0, z), paint=wood, bevel=.008, segs=1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.cube("Corner%d%d" % (sx, sy), (.07, .07, H - .06), loc=(sx * W / 2, sy * D / 2, .03 + (H - .06) / 2), paint=wood, bevel=.01, segs=1)
    dv4.cube("Top", (W + .12, D + .12, .05), loc=(0, 0, H - .025), paint=marble, bevel=.02, segs=3)
    # front sign: gold rounded panel on the navy front with a cream cup pictogram + two little stars
    dv4.cube("SignBack", (.78, .03, .36), loc=(0, D / 2 + .02, .52), paint=gold, bevel=.03, segs=3)
    dv4.cube("SignFace", (.7, .012, .28), loc=(0, D / 2 + .04, .52), paint=navy, bevel=.02, segs=2)
    L.picto_cup("Cup", (-.02, D / 2 + .05, .40), .3, cream, r=.009)
    L.picto_star("Star1", (-.26, D / 2 + .05, .6), .07, goldp, r=.006)
    L.picto_star("Star2", (.26, D / 2 + .05, .44), .07, goldp, r=.006)
    # bar ledge in front on two timber brackets, two stools tucked under it
    dv4.cube("Ledge", (W + .1, .24, .04), loc=(0, D / 2 + .13, H - .04), paint=wood, bevel=.01, segs=2)
    for sx in (-1, 1):
        dv4.cube("Bracket%d" % sx, (.05, .2, .05), loc=(sx * .7, D / 2 + .11, H - .09), paint=woodd, bevel=.006, segs=1)
        dv4.tube("Brace%d" % sx, [(sx * .7, D / 2 + .02, H - .3), (sx * .7, D / 2 + .19, H - .09)], radius=.014, res=6, paint=woodd, kind="POLY", resolution=1)
        sxx = sx * .55; sy = .53
        dv4.lathe("Stool%d" % sx, [(0, 0), (.15, 0), (.165, .02), (.15, .05), (0, .05)], seg=14, loc=(sxx, sy, .64), paint=wood)
        for dx in (-1, 1):
            for dy in (-1, 1):
                dv4.tube("StoolLeg%d%d%d" % (sx, dx, dy), [(sxx + dx * .1, sy + dy * .1, .64), (sxx + dx * .14, sy + dy * .12, 0)], radius=.012, res=6, paint=black, kind="POLY", resolution=1)
        dv4.torus("StoolRing%d" % sx, .125, .007, loc=(sxx, sy, .22), seg=14, minor=4, paint=black)
    # wheels: big spoked timber wheels on the sides (back), chrome hub, turned front legs
    for sx in (-1, 1):
        wx = sx * (W / 2 + .06)
        dv4.torus("Wheel%d" % sx, .25, .035, loc=(wx, -.15, .25), seg=22, minor=8, paint=woodd, rot=(0, 90, 0))
        dv4.torus("Tyre%d" % sx, .285, .012, loc=(wx, -.15, .25), seg=22, minor=5, paint=black, rot=(0, 90, 0))
        for i in range(8):
            a = math.radians(i * 45)
            dv4.tube("Spoke%d%d" % (sx, i), [(wx, -.15, .25), (wx, -.15 + math.cos(a) * .24, .25 + math.sin(a) * .24)], radius=.013, res=6, paint=wood, kind="POLY", resolution=1)
        dv4.cylinder("Hub%d" % sx, .05, .06, loc=(wx - .03, -.15, .25), rot=(0, 90, 0), seg=12, paint=chrome)
        dv4.lathe("Leg%d" % sx, [(0, 0), (.035, 0), (.03, .03), (.022, .1), (.028, .12), (.022, .14), (.03, .16), (0, .16)], seg=10, loc=(sx * .85, .32, 0), paint=woodd)
    dv4.cylinder("Axle", .018, W + .12, loc=(-(W / 2 + .06), -.15, .25), rot=(0, 90, 0), seg=8, paint=black)
    # ---- counter top: espresso machine, grinder, cup stacks, syrups, pastry case, napkins, sugar jar, plant
    espresso(-.62, .02, H, chrome, red, black, cream, gold)
    grinder(-.2, -.2, H, chrome, black, glassf, cream)
    for i in range(4):
        dv4.lathe("CupStack%d" % i, [(0, 0), (.03, 0), (.038, .08), (.04, .085), (.036, .085), (0, .085)], seg=10, loc=(-.18, .26, H + i * .022), paint=cream)
    for i in range(3):
        dv4.lathe("KraftCup%d" % i, [(0, 0), (.032, 0), (.04, .1), (.042, .105), (.038, .105), (0, .105)], seg=10, loc=(-.06, .3, H + i * .024), paint=kraft)
        dv4.torus("KraftSleeve%d" % i, .038, .004, loc=(-.06, .3, H + i * .024 + .05), seg=10, minor=3, paint=choc)
    for i, sp in enumerate(syrups):
        x = .06 + i * .085
        dv4.lathe("Syrup%d" % i, [(0, 0), (.026, 0), (.028, .12), (.018, .15), (.014, .2), (.016, .21), (0, .21)], seg=10, loc=(x, -.25, H), paint=sp)
        dv4.lathe("SyrupLabel%d" % i, [(.029, .04), (.029, .1)], seg=10, loc=(x, -.25, H), paint=cream, cap=False)
        dv4.cylinder("SyrupPump%d" % i, .009, .05, loc=(x, -.25, H + .21), seg=8, paint=chrome)
        dv4.tube("SyrupNozzle%d" % i, [(x, -.25, H + .26), (x, -.21, H + .26), (x, -.2, H + .24)], radius=.005, res=5, paint=chrome, resolution=2)
    pastry_case(.6, .02, H, chrome, None, woodd, crust, pink, cream, choc)
    dv4.cube("Napkins", (.1, .09, .07), loc=(.22, .28, H + .035), paint=chrome, bevel=.006, segs=1)
    dv4.cube("NapkinPaper", (.08, .07, .05), loc=(.22, .28, H + .055), paint=cream, bevel=.003, segs=1)
    dv4.lathe("SugarJar", [(0, 0), (.035, 0), (.04, .07), (.03, .085), (.018, .09), (0, .09)], seg=10, loc=(.36, .3, H), paint=glassf)
    dv4.cylinder("SugarLid", .022, .015, loc=(.36, .3, H + .085), seg=8, paint=chrome)
    # succulent in a glazed pot at the right end
    dv4.lathe("PlantPot", [(0, 0), (.05, 0), (.065, .1), (.074, .105), (.074, .12), (.06, .105), (0, .095)], seg=10, loc=(.9, .28, H), paint=terra)
    for k in range(6):
        a = k * 60 + RNG.uniform(-10, 10)
        dv4.leaf("Succ%d" % k, .07, .035, loc=(.9, .28, H + .1), rot=(RNG.uniform(35, 65), 0, a), paint=leafp, shape="spade", bend=.2, cup=.3, thickness=.005, nl=2, nw=2)
    dv4.sphere("SuccC", .025, loc=(.9, .28, H + .115), seg=7, rings=4, paint=leafp)
    # ---- posts + beam at the back, sloped rafters, striped awning with a scalloped front, festoon
    for sx in (-1, 1):
        dv4.cube("Post%d" % sx, (.08, .08, 1.5), loc=(sx * .95, -.38, H + .75), paint=woodd, bevel=.01, segs=1)
        dv4.tube("Rafter%d" % sx, [(sx * .95, -.36, 2.4), (sx * .95, -.02, 2.34), (sx * .95, .32, 2.22), (sx * .95, .62, 2.1)], radius=.022, res=6, paint=woodd, kind="POLY", resolution=1)
    dv4.cube("Beam", (W + .06, .08, .08), loc=(0, -.38, 2.42), paint=woodd, bevel=.01, segs=1)
    # arched canopy: three strips at increasing pitch from the back beam down to the front bar
    y0, z0 = -.38, 2.44
    for i, pitch in enumerate((8, 18, 30)):
        ln = .36
        dy, dz = ln * math.cos(math.radians(pitch)), ln * math.sin(math.radians(pitch))
        dv4.cube("Awning%d" % i, (W + .24, ln + .03, .02), loc=(0, y0 + dy / 2, z0 - dz / 2), rot=(-pitch, 0, 0), paint=awning, bevel=.005, segs=1)
        y0 += dy; z0 -= dz
    dv4.cube("AwningBack", (W + .24, .03, .09), loc=(0, -.38, 2.47), paint=awning, bevel=.006, segs=1)
    for i in range(11):
        x = -W / 2 - .07 + i * (W + .14) / 10
        dv4.cylinder("Scallop%d" % i, .06, .014, loc=(x, .64, 2.06), rot=(90, 0, 0), seg=8, paint=awning)
    dv4.cube("AwningBar", (W + .26, .03, .03), loc=(0, .62, 2.11), paint=woodd, bevel=.006, segs=1)
    # festoon along the awning edge: cord + bulbs, every other bulb on the Anim Blink node
    pts = L.catenary((-W / 2 - .05, .66, 2.1), (W / 2 + .05, .66, 2.1), .08, 12)
    dv4.tube("Cord", pts, radius=.004, res=4, paint=cord, kind="POLY", resolution=1)
    blink = "Anim Blink"; dv4.pivot(blink, (0, .66, 2.0))
    L.ballast("Ballast", blink, (-1.0, -.38, 2.42), (1.0, -.38, 2.42), woodd)      # hidden inside the back beam (UV balance, see _lib_D.ballast)
    for k in range(1, 12):
        p = pts[k]
        dv4.cylinder("Socket%d" % k, .011, .022, loc=(p[0], p[1], p[2] - .026), seg=6, paint=cord)
        dv4.sphere("Bulb%d" % k, .026, loc=(p[0], p[1], p[2] - .052), scale=(1, 1, 1.25), seg=7, rings=4, paint=None, mat_override="E_FFE6A8",
                   out=blink if k % 2 else "Body")
    # ---- menu board above the beam: gold frame, chalkboard, pictograms (cup, mug, croissant, cake slice, heart)
    for sx in (-1, 1):
        dv4.cube("BoardPost%d" % sx, (.05, .05, .3), loc=(sx * .4, -.38, 2.58), paint=woodd, bevel=.006, segs=1)
    dv4.cube("BoardFrame", (1.0, .04, .62), loc=(0, -.38, 2.83), paint=gold, bevel=.02, segs=3)
    dv4.cube("Board", (.92, .012, .54), loc=(0, -.36, 2.83), paint=board, bevel=.004, segs=1)
    L.picto_cup("MCup", (-.3, -.352, 2.86), .22, chalk, r=.006)
    L.picto_cup("MMug", (.02, -.352, 2.9), .17, chalkp, r=.006, steam=False)
    L.picto_croissant("MCroissant", (.3, -.352, 2.84), .3, chalky, r=.009)
    for u in (-.06, .06):
        L.bar("MCrLine%s" % u, [(.3 + u, -.352, 2.86), (.3 + u * 1.6, -.352, 2.91)], r=.005, paint=chalky, res=4)
    L.picto_heart("MHeart", (.34, -.352, 2.66), .1, chalkp, r=.005)
    L.picto_star("MStar", (-.36, -.352, 2.66), .06, chalky, r=.005)
    # cake slice: triangle outline + a cherry
    L.bar("MSlice", [(-.02, -.352, 2.62), (.1, -.352, 2.62), (.04, -.352, 2.74), (-.02, -.352, 2.62)], r=.006, paint=chalk, res=4)
    dv4.sphere("MCherry", .012, loc=(.04, -.352, 2.755), seg=6, rings=4, paint=chalkp)
    # chalk easel board on the floor at the front-left corner with a cup drawing
    ax, ay = -.88, .50
    dv4.cube("ABoard", (.4, .025, .6), loc=(ax, ay, .31), paint=woodd, bevel=.008, segs=1)
    dv4.cube("ABoardFace", (.34, .012, .5), loc=(ax, ay + .014, .33), paint=board, bevel=.004, segs=1)
    for sx in (-1, 1):
        dv4.tube("ABoardLeg%d" % sx, [(ax + sx * .17, ay - .01, .58), (ax + sx * .17, ay - .18, 0)], radius=.01, res=5, paint=woodd, kind="POLY", resolution=1)
    L.picto_cup("ACup", (ax, ay + .022, .25), .2, chalk, r=.006)
    L.picto_heart("AHeart", (ax + .1, ay + .022, .5), .07, chalkp, r=.004)
    # bunting on the board frame top: small triangles alternating colours
    for i in range(7):
        x = -.42 + i * .14
        col = (chalkp, chalky, cream)[i % 3]
        dv4.cube("Flag%d" % i, (.08, .01, .07), loc=(x, -.352, 3.09), rot=(0, 0, 45), paint=col, bevel=0)
    return {"name": "CoffeeKiosk", "tex": 1024, "budget": 15000, "floor": "C9C3B8"}
