"""Rede: the fleet's yard on the plaza north of the distribution centre (Lucas 06/11: "eu gostei da localização do 1").

Run after rede_assets.py (helpers, palette) in the same namespace:
    exec(open(REPO + "/scripts/blender/rede_yard.py").read(), ns); ns["fleet_yard"]()

Model space = Unity world minus YARD_ORIGIN (Blender (x, y) == Unity (x, z), see rede_export.py). The game places it at
YARD_ORIGIN; CheckoutRedeWorld uses the same numbers (bays, pump stop, lanes):
  * asphalt slab x −17.5..14.6, y −6.3..6.4 (world x −15.5..16.6, z 49.3..62.0), top at z .17, kerbed all round but the
    driveway to the east street (y −4.0..−0.2, world z 51.6..55.4) that crosses the pavement to the road;
  * seven truck bays along the north kerb, x −15 … 4.8 every 3.3 m (world −13 … 6.8), trucks backed in (nose to the
    aisle), wheel stops behind the rear wheels;
  * the diesel island (RedeFuelIsland, approved) stands at world (11.5, 50.9) turned 90°: its pad is painted here, the
    truck stops beside it in the lane y −2.1 (world z 53.5);
  * hedge boxes on the north kerb, light poles, bollards at the driveway, painted lane arrows and a hatched pump pad.
No words anywhere (the game is translated).
"""
import bpy, math
from mathutils import Vector

YARD_ORIGIN = (2.0, 0.0, 55.6)          # Unity world position of the model's origin
ASPHALT = "C_43474A"
ASPHALT_D = "C_3A3D40"
LINE = "C_EDE6D3"
KERB = "C_D9D0BA"
HEDGE, HEDGE_D = "C_5C9A45", "C_4A8238"
SOIL = "C_7A5A3C"
YELLOW = "C_F2B830"
POLE = "C_2F3A4A"
BAYS = (-15.0, -11.7, -8.4, -5.1, -1.8, 1.5, 4.8)   # seven: the whole fleet (2 + 3 dry + 2 reefer)
BAY_W = 3.3
BAY_Y0 = -.8                             # the bays' front line (the aisle side)
TRUCK_Y = 2.4                            # a parked truck's origin (nose to the aisle: Blender trucks face −Y)
PUMP_STOP = (9.9, -2.1)                  # a truck refuelling (heading west)
X0, X1, Y0, Y1 = -17.5, 14.6, -6.3, 6.4
DRIVE = (-4.0, -.2)                      # driveway across the east kerb (model y)
TOP = .17


def fleet_yard(name="RedeFleetYard", loc=(0, 0, 0)):
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = Vector(loc)
    acc = Acc(name)
    W, D = X1 - X0, Y1 - Y0
    cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    # the slab, a little darker skirt under it so its edge reads against the plaza paving
    rbox(acc, (W, D, .27), (cx, cy, TOP - .135), ASPHALT, .02, 1, uv=.25)
    # driveway over the pavement to the road (x 14.6 .. 17.9), ramped down at its far end
    rbox(acc, (3.3, DRIVE[1] - DRIVE[0], .2), (X1 + 1.65, (DRIVE[0] + DRIVE[1]) / 2, TOP - .11), ASPHALT, .02, 1)
    prism(acc, [(0, 0), (.6, 0), (0, .07)], DRIVE[1] - DRIVE[0], ASPHALT_D, (X1 + 3.3, (DRIVE[0] + DRIVE[1]) / 2, TOP - .2), r=.01, seg=1, rot=(0, 0, -90))
    # kerbs: north, south, west, east (east split around the driveway)
    k = .26
    def kerb(x0, y0, x1, y1):
        rbox(acc, (max(k, x1 - x0), max(k, y1 - y0), .16), ((x0 + x1) / 2, (y0 + y1) / 2, TOP + .05), KERB, .04, 2)
    kerb(X0, Y1 - k, X1, Y1)
    kerb(X0, Y0, X1, Y0 + k)
    kerb(X0, Y0, X0 + k, Y1)
    kerb(X1 - k, Y0, X1, DRIVE[0])
    kerb(X1 - k, DRIVE[1], X1, Y1)
    for yy in DRIVE:   # rounded kerb ends at the driveway
        lathe(acc, [(0, 0), (.16, 0), (.16, .16), (0, .18)], (X1 - k / 2, yy + (-.13 if yy == DRIVE[0] else .13), TOP - .03), KERB, 16, 1)
    # bays: side lines, back line, wheel stops
    half = BAY_W / 2
    edges = sorted({round(b - half, 2) for b in BAYS} | {round(b + half, 2) for b in BAYS})
    for x in edges:
        rbox(acc, (.12, 6.8, .012), (x, BAY_Y0 + 3.4, TOP + .006), LINE, .005, 1)
    rbox(acc, (edges[-1] - edges[0] + .12, .12, .012), ((edges[0] + edges[-1]) / 2, BAY_Y0, TOP + .006), LINE, .005, 1)
    for b in BAYS:   # behind the rear wheels of a truck backed in (TRUCK_Y)
        rbox(acc, (1.6, .22, .12), (b, TRUCK_Y + 2.45, TOP + .06), YELLOW, .04, 2)
        for s in (-.45, .45):
            rbox(acc, (.18, .225, .121), (b + s, TRUCK_Y + 2.45, TOP + .06), RUBBER, .03, 1)
    # the pump pad (hatched yellow) under the diesel island at world (11.5, 50.9): model (9.5, −4.7)
    px, py = 9.5, -4.7
    rframe(acc, 5.4, 1.9, .012, .1, (px, py, TOP + .006), YELLOW, .01, rot=(90, 0, 0))
    for i in range(9):
        rbox(acc, (.1, 1.9 * 1.25, .012), (px - 2.3 + i * .58, py, TOP + .007), YELLOW, .005, 1, rot=(0, 0, 38))
    # the lane line in front of the pump and the stop bar
    rbox(acc, (8.0, .12, .012), (8.4, -3.55, TOP + .006), LINE, .005, 1)
    rbox(acc, (.35, 3.0, .012), (5.6, -2.1, TOP + .006), LINE, .005, 1)
    # painted arrows along the aisle (in → west, out → east), no words
    for ax, d in ((13.0, -1), (-1.0, -1), (-10.0, 1), (1.5, 1)):
        bm_arrow(acc, (ax, -2.3 if d < 0 else -4.9), d)
    # hedge boxes on the north kerb, with soil and leafy tops
    for i, x in enumerate((-16.2, -11.5, -6.2, -1.0, 4.2, 9.4, 13.4)):
        rbox(acc, (2.6 if i not in (0, 6) else 1.6, .8, .42), (x, Y1 + .55, .21), KERB, .05, 2)
        rbox(acc, ((2.6 if i not in (0, 6) else 1.6) - .18, .62, .05), (x, Y1 + .55, .41), SOIL, .02, 1)
        for j in range(4 if i not in (0, 6) else 2):
            w = (2.6 if i not in (0, 6) else 1.6) - .3
            xx = x - w / 2 + (j + .5) * w / (4 if i not in (0, 6) else 2)
            lathe(acc, [(0, 0), (.36, .05), (.42, .25), (.3, .5), (0, .58)], (xx, Y1 + .55 + (.04 if j % 2 else -.04), .4), HEDGE if j % 2 else HEDGE_D, 12, 2)
    # light poles (two on the north side, one by the pump lane)
    for (lx, ly) in ((-12.2, Y1 + 1.15), (1.3, Y1 + 1.15), (13.6, -6.85)):
        tube(acc, [(lx, ly, 0), (lx, ly, 6.2)], .07, POLE, seg=12)
        lathe(acc, [(.14, 0), (.18, 0), (.18, .35), (.1, .45)], (lx, ly, 0), POLE, 12, 0, cap_top=False, cap_bottom=False)
        head_dir = -1 if ly > 0 else 1
        tube(acc, [(lx, ly, 6.15), (lx, ly + head_dir * .5, 6.35), (lx, ly + head_dir * 1.1, 6.38)], .045, POLE, seg=10, smooth_n=2)
        rbox(acc, (.42, .7, .12), (lx, ly + head_dir * 1.3, 6.36), POLE, .04, 2)
        rbox(acc, (.34, .58, .02), (lx, ly + head_dir * 1.3, 6.295), HEAD_L, .01, 1)
    # bollards either side of the driveway
    for yy in (DRIVE[0] - .45, DRIVE[1] + .45):
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


def yard_preview(dist=46):
    """Studio stills of the yard with the diesel island and two trucks backed into their bays."""
    rk_core.clear("Rede Yard Preview")
    rk_core.studio((1600, 1000), bg=(.86, .84, .8))
    preview_setup()
    y, _ = fleet_yard("RedeFleetYard", (0, 0, 0))
    fi, _ = fuel_island("YardFuel", (9.5, -4.7, TOP))
    fi.rotation_euler = (0, 0, math.radians(90))
    truck("YardTruckA", (BAYS[1], TRUCK_Y, TOP))          # nose to the aisle (Blender trucks face −Y)
    truck("YardTruckB", (BAYS[3], TRUCK_Y, TOP), reefer=True)
    t3, _ = truck("YardTruckC", (PUMP_STOP[0], PUMP_STOP[1], TOP))
    t3.rotation_euler = (0, 0, math.radians(-90))   # at the pump, heading west (−X)
    out = []
    for nm, d, ds, lens in (("yard_overview", (.55, -.8, .75), dist, 40), ("yard_pump", (.9, -.7, .45), 16, 38), ("yard_bays", (-.35, -.9, .5), 24, 38)):
        tgt = Vector((9.5, -3.0, 1.2)) if nm == "yard_pump" else Vector((-4.0 if nm == "yard_bays" else -1.5, 0, .5))
        out.append(rk_core.shoot(nm, tgt, d, ds, lens, (1600, 1000)))
    return out


def export_yard():
    """Resources/Rede/RedeFleetYard.fbx (+ _brand.json, empty: no plates)."""
    rk_core.clear("Rede Export")
    preview_setup()
    r, _ = fleet_yard("RedeFleetYard", (0, 0, 0))
    return export_model(r, "RedeFleetYard")
