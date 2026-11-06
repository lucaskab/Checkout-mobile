"""Rede: the fleet's yard on the plaza north of the distribution centre (Lucas 06/11: "eu gostei da localização do 1";
v2 06/11: "aumente o estacionamento ... quase até o final do mapa", an entrance and an exit of its own so trucks coming
in and going out never cross, trucks in proportion to the streets).

Run after rede_assets.py (helpers, palette) and rede_export.py in the same namespace:
    exec(open(REPO + "/scripts/blender/rede_yard.py").read(), ns); ns["export_yard"]()

Model space = Unity world minus YARD_ORIGIN (Blender (x, y) == Unity (x, z), see rede_export.py). The game places it at
YARD_ORIGIN; CheckoutRedeYard uses the same numbers. A one-way loop, top to bottom:
  * ENTRANCE driveway from the east street at the north end (y 9.6..12.8, world z 65.2..68.4) into the north aisle
    (westbound, lane y 11.2) with the diesel island beside the lane (island at (9.5, 13.9), pump stop (9.9, 11.2));
  * the bays in the middle row, drive-through: a truck turns in from the north aisle and stops nose south (y 4.4);
  * it leaves forwards into the south aisle (eastbound, lane y −2.3) and out by the EXIT driveway (y −4.0..−.6, world
    z 51.6..55.0) to the street;
  * a planted island east of the bays (between the aisles), hedges on the north kerb, light poles, one-way arrows,
    bay numbers are NOT painted (no words / digits anywhere: the game is translated).
"""
import bpy, math
from mathutils import Vector

YARD_ORIGIN = (2.0, 0.0, 55.6)          # Unity world position of the model's origin
ASPHALT = "C_43474A"
ASPHALT_D = "C_3A3D40"
LINE = "C_EDE6D3"
KERB = "C_D9D0BA"
HEDGE, HEDGE_D = "C_5C9A45", "C_4A8238"
GRASS = "C_7DAF4E"
SOIL = "C_7A5A3C"
YELLOW = "C_F2B830"
POLE = "C_2F3A4A"
BAYS = (-15.0, -11.7, -8.4, -5.1, -1.8, 1.5, 4.8)   # seven: the whole fleet (2 + 3 dry + 2 reefer)
BAY_W = 3.3
BAY_Y0, BAY_Y1 = .4, 8.4                 # the bay row between the two aisles
TRUCK_Y = 4.4                            # a parked truck's origin (nose south, to the exit aisle)
LANE_IN, LANE_OUT = 11.2, -2.3           # north aisle westbound, south aisle eastbound
PUMP = (9.5, 13.9)                       # the diesel island (turned 90°: long side along the lane)
PUMP_STOP = (9.9, LANE_IN)               # a truck refuelling (heading west)
X0, X1, Y0, Y1 = -17.5, 14.6, -6.3, 16.9
IN_DRIVE = (9.6, 12.8)
OUT_DRIVE = (-4.0, -.6)
ISLAND = (7.2, 14.0)                     # planted island x range, between the aisles (y BAY_Y0+.4 .. BAY_Y1-.4)
TOP = .17
DRIVE_L = 4.4                            # the driveways cross the pavement and the cycle lane to the kerb (world x 21.25)
FLEET_SCALE = .75                        # the chain's trucks in the game, in proportion to the streets


def fleet_yard(name="RedeFleetYard", loc=(0, 0, 0)):
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    W, D = X1 - X0, Y1 - Y0
    cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    rbox(acc, (W, D, .27), (cx, cy, TOP - .135), ASPHALT, .02, 1, uv=.25)
    # the two driveways over the pavement and the cycle lane to the road, ramped down at their far end
    for d0, d1 in (IN_DRIVE, OUT_DRIVE):
        rbox(acc, (DRIVE_L, d1 - d0, .2), (X1 + DRIVE_L / 2, (d0 + d1) / 2, TOP - .11), ASPHALT, .02, 1)
        prism(acc, [(0, 0), (.6, 0), (0, .07)], d1 - d0, ASPHALT_D, (X1 + DRIVE_L, (d0 + d1) / 2, TOP - .2), r=.01, seg=1, rot=(0, 0, -90))
    # kerbs (the east one broken by the driveways)
    k = .26
    def kerb(x0, y0, x1, y1):
        rbox(acc, (max(k, x1 - x0), max(k, y1 - y0), .16), ((x0 + x1) / 2, (y0 + y1) / 2, TOP + .05), KERB, .04, 2)
    kerb(X0, Y1 - k, X1, Y1)
    kerb(X0, Y0, X1, Y0 + k)
    kerb(X0, Y0, X0 + k, Y1)
    kerb(X1 - k, Y0, X1, OUT_DRIVE[0])
    kerb(X1 - k, OUT_DRIVE[1], X1, IN_DRIVE[0])
    kerb(X1 - k, IN_DRIVE[1], X1, Y1)
    for d0, d1 in (IN_DRIVE, OUT_DRIVE):
        for yy, s in ((d0, -1), (d1, 1)):
            lathe(acc, [(0, 0), (.16, 0), (.16, .16), (0, .18)], (X1 - k / 2, yy + s * .13, TOP - .03), KERB, 16, 1)
    # bays: side lines across the whole row, the front stop bar (south) and a dashed entry line (north)
    half = BAY_W / 2
    edges = sorted({round(b - half, 2) for b in BAYS} | {round(b + half, 2) for b in BAYS})
    for x in edges:
        rbox(acc, (.12, BAY_Y1 - BAY_Y0, .012), (x, (BAY_Y0 + BAY_Y1) / 2, TOP + .006), LINE, .005, 1)
    for b in BAYS:
        rbox(acc, (BAY_W - .5, .3, .012), (b, BAY_Y0 + .5, TOP + .007), YELLOW, .005, 1)   # stop bar
        for j in range(4):
            rbox(acc, (.45, .12, .012), (b - 1.1 + j * .73, BAY_Y1 - .1, TOP + .006), LINE, .005, 1)
    # the planted island east of the bays: kerbed lawn with hedges and a light pole
    iy0, iy1 = BAY_Y0 + .5, BAY_Y1 - .5
    rbox(acc, (ISLAND[1] - ISLAND[0], iy1 - iy0, .22), ((ISLAND[0] + ISLAND[1]) / 2, (iy0 + iy1) / 2, TOP + .06), KERB, .08, 3)
    rbox(acc, (ISLAND[1] - ISLAND[0] - .4, iy1 - iy0 - .4, .05), ((ISLAND[0] + ISLAND[1]) / 2, (iy0 + iy1) / 2, TOP + .19), GRASS, .04, 2)
    for i in range(6):
        hx = ISLAND[0] + .9 + i * (ISLAND[1] - ISLAND[0] - 1.8) / 5
        lathe(acc, [(0, 0), (.45, .06), (.52, .3), (.38, .6), (0, .7)], (hx, (iy0 + iy1) / 2 + (.25 if i % 2 else -.25), TOP + .2), HEDGE if i % 2 else HEDGE_D, 12, 2)
    # the pump pad (hatched yellow) under the diesel island
    px, py = PUMP
    rframe(acc, 5.4, 1.9, .012, .1, (px, py, TOP + .006), YELLOW, .01, rot=(90, 0, 0))
    for i in range(9):
        rbox(acc, (.1, 1.9 * 1.25, .012), (px - 2.3 + i * .58, py, TOP + .007), YELLOW, .005, 1, rot=(0, 0, 38))
    rbox(acc, (8.0, .12, .012), (8.4, py - 1.2, TOP + .006), LINE, .005, 1)         # the lane edge beside the pump
    rbox(acc, (.35, 2.6, .012), (5.4, LANE_IN, TOP + .006), LINE, .005, 1)            # stop bar
    # one-way arrows: west along the north aisle, east along the south one
    for ax in (12.6, 1.0, -9.5):
        bm_arrow(acc, (ax, LANE_IN - (.0 if ax > 5 else .3)), -1)
    for ax in (-13.0, -3.0, 7.0):
        bm_arrow(acc, (ax, LANE_OUT), 1)
    # hedge boxes on the north kerb
    for i, x in enumerate((-16.2, -11.5, -6.2, -1.0, 4.2, 9.4, 13.4)):
        w = 2.6 if i not in (0, 6) else 1.6
        rbox(acc, (w, .8, .42), (x, Y1 + .55, .21), KERB, .05, 2)
        rbox(acc, (w - .18, .62, .05), (x, Y1 + .55, .41), SOIL, .02, 1)
        n = 4 if i not in (0, 6) else 2
        for j in range(n):
            xx = x - (w - .3) / 2 + (j + .5) * (w - .3) / n
            lathe(acc, [(0, 0), (.36, .05), (.42, .25), (.3, .5), (0, .58)], (xx, Y1 + .55 + (.04 if j % 2 else -.04), .4), HEDGE if j % 2 else HEDGE_D, 12, 2)
    # light poles: north kerb, the island, by the exit
    for (lx, ly, hd) in ((-12.2, Y1 + 1.15, -1), (1.3, Y1 + 1.15, -1), (10.6, (iy0 + iy1) / 2, 1), (-6.0, Y0 - .6, 1)):
        base = TOP + .26 if ly == (iy0 + iy1) / 2 else 0
        tube(acc, [(lx, ly, base), (lx, ly, 6.2)], .07, POLE, seg=12)
        lathe(acc, [(.14, 0), (.18, 0), (.18, .35), (.1, .45)], (lx, ly, base), POLE, 12, 0, cap_top=False, cap_bottom=False)
        tube(acc, [(lx, ly, 6.15), (lx, ly + hd * .5, 6.35), (lx, ly + hd * 1.1, 6.38)], .045, POLE, seg=10, smooth_n=2)
        rbox(acc, (.42, .7, .12), (lx, ly + hd * 1.3, 6.36), POLE, .04, 2)
        rbox(acc, (.34, .58, .02), (lx, ly + hd * 1.3, 6.295), HEAD_L, .01, 1)
    # bollards either side of each driveway
    for d0, d1 in (IN_DRIVE, OUT_DRIVE):
        for yy in (d0 - .45, d1 + .45):
            for xx in (X1 + .6, X1 + 2.4):
                lathe(acc, [(0, 0), (.09, 0), (.09, .85), (.07, .93), (0, .95)], (xx, yy, .02), C("F2C230"), 12, 1)
                lathe(acc, [(.093, .6), (.093, .7)], (xx, yy, .02), RUBBER, 12, 0, cap_top=False, cap_bottom=False)
    objs = acc.realize()
    for o in objs:
        o.parent = root
        o.name = f"{name}_{o.name}"
    return root, objs


def bm_arrow(acc, at, d):
    """A painted lane arrow pointing along ±X."""
    x, y = at
    rbox(acc, (1.5, .2, .012), (x - d * .35, y, TOP + .006), LINE, .005, 1)
    for s in (-1, 1):   # two strokes meeting at the tip (x + .4·d)
        rbox(acc, (.75, .2, .012), (x + d * .4 - d * .27, y + s * .23, TOP + .006), LINE, .005, 1, rot=(0, 0, -s * d * 40))


def yard_preview(dist=50):
    """Studio stills: the yard, the diesel island, trucks (game scale) in the bays and one at the pump."""
    rk_core.clear("Rede Yard Preview")
    rk_core.studio((1600, 1000), bg=(.86, .84, .8))
    preview_setup()
    fleet_yard("RedeFleetYard", (0, 0, 0))
    fi, _ = fuel_island("YardFuel", (PUMP[0], PUMP[1], TOP))
    fi.rotation_euler = (0, 0, math.radians(90))
    for i, (bx, reefer) in enumerate(((BAYS[6], False), (BAYS[5], True), (BAYS[3], False))):
        t, _ = truck(f"YardTruck{i}", (bx, TRUCK_Y, TOP), reefer=reefer)
        t.scale = (FLEET_SCALE,) * 3
    t3, _ = truck("YardTruckPump", (PUMP_STOP[0], PUMP_STOP[1], TOP))
    t3.rotation_euler = (0, 0, math.radians(-90))
    t3.scale = (FLEET_SCALE,) * 3
    out = []
    for nm, d, ds, lens, tgt in (("yard_overview", (.55, -.8, .85), dist, 40, (-1.5, 5.3, .5)),
                                 ("yard_pump", (.9, -.7, .5), 18, 38, (9.0, 11.5, 1.2)),
                                 ("yard_bays", (-.3, -.9, .55), 26, 38, (-4.0, 4.0, .5))):
        out.append(rk_core.shoot(nm, Vector(tgt), d, ds, lens, (1600, 1000)))
    return out


def export_yard():
    """Resources/Rede/RedeFleetYard.fbx (+ _brand.json, empty: no plates)."""
    rk_core.clear("Rede Export")
    preview_setup()
    r, _ = fleet_yard("RedeFleetYard", (0, 0, 0))
    return export_model(r, "RedeFleetYard")
