"""water-cooler: office water dispenser - cream cabinet with rounded corners, dark skirt and teal band, navy tap panel with
chrome spouts and red/blue push levers, chrome drip tray, a water-drop pictogram, a blinking power LED ("Anim Blink"), a side
cup dispenser with paper cups, and a translucent 20 L bottle (G_Glass shell, blue water with bubbles and ridge bands baked
inside; set GLASS = False to bake the whole bottle as tinted blue glass instead).
Footprint half .22 x .22, height <= 1.7 (Blender Z up, front = +Y)."""
import os, sys, math
import dv4
from dv4 import RNG
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_A as lib

CONFIG = {"floor": "F4EFE4", "seed": 13}
CW, CD, CH = .32, .30, .985      # cabinet width, depth, height
GLASS = False                    # True: G_Glass shell + water inside; False: opaque painted tinted bottle


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.2, light=.34)
    cream = lib.paint_stripe("Cabinet", base="FAF6EC", bands=[(-.01, .06, "2F3A40"), (.47, .505, "1F9A8E")], variation=.08,
                             edge="FFFFFF", edge_r=.005)
    navy = dv4.paint_flat("Navy", "1D2B4F", dark="0E1630", variation=.3, scale=6.0, edge="5C6E9C", edge_r=.004)
    chrome = lib.paint_chrome("Chrome")
    red = dv4.paint_flat("Red", "D74A3C", dark="8E2318", variation=.2, scale=20.0, edge="F49080", edge_r=.004)
    blue = dv4.paint_flat("Blue", "3E8FD6", dark="1F5A95", variation=.2, scale=20.0, edge="93CBF4", edge_r=.004)
    dark = dv4.paint_flat("Dark", "2F3A40", dark="161C20", variation=.3, scale=10.0, edge="6B7A84", edge_r=.004)
    teal = dv4.paint_flat("Teal", "6FCBC2", dark="2E9A8E", variation=.25, scale=12.0, edge="C6F0EB", edge_r=.004)
    cup = lib.paint_stripe("Cup", base="FBF8F1", bands=[(.775, .79, "1F9A8E")], variation=.06, edge="FFFFFF", edge_r=.003)
    drop = dv4.paint_flat("Drop", "F4EFE4", dark="CDBFA6", variation=.15, scale=12.0, edge="FFFFFF", edge_r=.003)
    water = lib.paint_tankwater("Water", z0=1.06, z1=1.56, rings=(1.28, 1.46))                 # used when GLASS is True
    bottle_p = lib.paint_bottle("Bottle", z0=1.05, water_z=1.565, deep="1860AE", mid="2F93DC", light="86CFF3", rings=(1.28, 1.46))

    # ---- cabinet: rounded box, slightly tapered top edge
    prof = [(-.012, 0), (0, .014), (0, CH - .03), (-.004, CH - .012), (-.028, CH)]
    lib.sweep_rect("Cabinet", prof, CW, CD, .035, cseg=3, cap_first=True, cap_last=True, paint=cream)
    # tap panel (navy, proud of the front) with pictogram, LED and taps
    fy = CD / 2
    dv4.cube("Panel", (.25, .018, .32), loc=(0, fy + .004, .72), paint=navy, bevel=.008, segs=2)
    dv4.cube("PanelTrim", (.262, .01, .332), loc=(0, fy, .72), paint=chrome, bevel=.004, segs=1)
    for x, col in ((-.06, red), (.06, blue)):
        dv4.tube("Spout%s" % col.name, [(x, fy + .012, .74), (x, fy + .038, .735), (x, fy + .044, .70)], radius=.008, res=6, paint=chrome, resolution=3)
        dv4.cylinder("Lever%s" % col.name, .02, .028, loc=(x, fy + .03, .745), rot=(-20, 0, 0), seg=12, paint=col, bevel=.006)
        dv4.lathe("Collar%s" % col.name, [(0, 0), (.014, 0), (.014, .01), (0, .01)], seg=10, loc=(x, fy + .012, .74), rot=(-90, 0, 0), paint=chrome)
    # water-drop pictogram and the blinking LED
    pts = [(0, -.035), (-.012, -.018), (-.019, .0), (-.016, .014), (-.008, .022), (0, .024), (.008, .022), (.016, .014), (.019, .0), (.012, -.018)]
    lib.prism("Drop", pts, .005, paint=drop, loc=(0, fy + .013, .635), rot=(-90, 0, 0), bevel=.002)
    dv4.sphere("LED", .008, loc=(.095, fy + .014, .86), scale=(1, .5, 1), seg=8, rings=4, paint=None, mat_override="E_7CF2A0", out="Anim Blink")
    dv4.pivot("Anim Blink", (.095, fy + .014, .86))
    # drip tray: chrome tray with a dark slotted insert
    dv4.cube("Tray", (.21, .07, .03), loc=(0, fy + .02, .585), paint=chrome, bevel=.008, segs=2)
    dv4.cube("TrayInsert", (.19, .055, .006), loc=(0, fy + .022, .602), paint=dark, bevel=.002, segs=1)
    for i in range(6):
        dv4.cube("Slot", (.19, .004, .004), loc=(0, fy + .0 + i * .009, .606), paint=chrome, bevel=0)
    # ---- cup dispenser on the right side: teal tube with paper cups
    tx, ty = CW / 2 + .028, .06
    dv4.lathe("CupTube", [(.03, .60), (.03, .83), (.027, .83), (.027, .61), (0, .61)], seg=18, loc=(tx, ty, 0), paint=teal)
    dv4.cube("TubeClip", (.03, .04, .02), loc=(CW / 2 + .006, ty, .64), paint=chrome, bevel=.004, segs=1)
    dv4.cube("TubeClip2", (.03, .04, .02), loc=(CW / 2 + .006, ty, .80), paint=chrome, bevel=.004, segs=1)
    for k, z in enumerate((.77, .79, .81)):
        dv4.lathe("Cup%d" % k, [(0, 0), (.018, 0), (.024, .06), (.026, .066), (.0255, .072), (.023, .072), (.021, .066), (0, .064)],
                  seg=14, loc=(tx, ty, z), paint=cup)
    # ---- top collar and the bottle
    dv4.lathe("Collar", [(0, CH - .002), (.115, CH - .002), (.12, CH + .012), (.115, CH + .04), (.085, CH + .046), (.072, CH + .056), (0, CH + .056)],
              seg=28, paint=dark)
    dv4.torus("CollarRing", .118, .006, loc=(0, 0, CH + .04), seg=28, minor=6, paint=chrome)
    bottle = [(0, 1.02), (.05, 1.02), (.05, 1.09), (.072, 1.112), (.118, 1.14), (.136, 1.175), (.136, 1.265), (.128, 1.28), (.136, 1.295),
              (.136, 1.445), (.128, 1.46), (.136, 1.475), (.136, 1.575), (.12, 1.635), (.078, 1.675), (.03, 1.692), (0, 1.695)]
    if GLASS:
        dv4.lathe("Bottle", bottle, seg=28, paint=None, mat_override="G_Glass")
        inner = [(0, 1.05), (.044, 1.05), (.044, 1.09), (.064, 1.114), (.11, 1.142), (.127, 1.175), (.127, 1.56), (0, 1.56)]
        dv4.lathe("Water", inner, seg=28, paint=water)
    else:
        dv4.lathe("Bottle", bottle, seg=28, paint=bottle_p)
    return {"name": "WaterCooler", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}
