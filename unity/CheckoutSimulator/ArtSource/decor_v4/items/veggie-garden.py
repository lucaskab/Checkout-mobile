"""veggie-garden: two raised wooden beds (plank sides, corner posts) with lettuces, a carrot row and staked tomato plants, a teal
watering can and a little picket edging in front. Footprint half 1.0 x .60, height <= .8 (Blender: X across, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_I as L

CONFIG = {"floor": "C9C3B8", "seed": 25}


def bed(prefix, cx, cy, w, d, h, wood_x, wood_y, post_p, soil):
    for sx in (-1, 1):
        for sy in (-1, 1):
            dv4.cube(prefix + "Post%d%d" % (sx, sy), (.06, .06, h + .03), loc=(cx + sx * (w / 2 - .03), cy + sy * (d / 2 - .03), (h + .03) / 2), paint=post_p, bevel=.007)
    for i in range(2):
        z = .02 + i * (h / 2 - .01) + (h / 2 - .02) / 2
        ph = h / 2 - .02
        for sy in (-1, 1):
            dv4.cube(prefix + "SideY%d_%d" % (i, sy), (w - .12, .03, ph), loc=(cx, cy + sy * (d / 2 - .015), z), paint=wood_x, bevel=.005)
        for sx in (-1, 1):
            dv4.cube(prefix + "SideX%d_%d" % (i, sx), (.03, d - .12, ph), loc=(cx + sx * (w / 2 - .015), cy, z), paint=wood_y, bevel=.005)
    s = dv4.patch(prefix + "Soil", w - .06, d - .06, 16, 10, loc=(cx, cy, h - .04), paint=soil)
    dv4.mod_displace(s, strength=.025, size=.07, mid=.5)
    return h - .04


def lettuce(prefix, p, r, out, leaf_p, heart_p):
    dv4.sphere(prefix + "Heart", r * .6, loc=(p[0], p[1], p[2] + r * .45), scale=(1, 1, .9), seg=7, rings=4, paint=heart_p, out=out)
    n = 6
    for i in range(n):
        a = i * 360 / n + RNG.uniform(-12, 12)
        pitch = RNG.uniform(25, 45)
        dv4.leaf(prefix + "L%d" % i, r * 1.2, r * 1.3, loc=(p[0] + math.cos(math.radians(a)) * r * .15, p[1] + math.sin(math.radians(a)) * r * .15, p[2] + .01),
                 rot=(pitch, RNG.uniform(-15, 15), a - 90), paint=leaf_p, out=out, shape="spade", bend=-.25, cup=.6, thickness=.003, nl=2, nw=2, wave=1.0)
    for i in range(3):
        a = i * 120 + 60 + RNG.uniform(-15, 15)
        dv4.leaf(prefix + "I%d" % i, r * .95, r * 1.0, loc=(p[0], p[1], p[2] + .03), rot=(60 + RNG.uniform(-8, 8), 0, a - 90), paint=leaf_p, out=out,
                 shape="spade", bend=-.3, cup=.65, thickness=.003, nl=2, nw=2, wave=1.0)


def carrot(prefix, p, out, top_p, root_p):
    dv4.lathe(prefix + "Root", [(0, -.02), (.016, -.02), (.02, 0), (.017, .012), (0, .016)], seg=10, loc=p, paint=root_p, out=out)
    for i in range(5):
        a = i * 72 + RNG.uniform(-20, 20)
        LL = RNG.uniform(.12, .16)
        dv4.leaf(prefix + "T%d" % i, LL, LL * .4, loc=(p[0], p[1], p[2] + .012), rot=(RNG.uniform(55, 80), RNG.uniform(-20, 20), a - 90),
                 paint=top_p, out=out, shape="pointed", bend=.4, cup=-.2, thickness=.002, nl=2, nw=1, wave=1.5)


def tomato_plant(prefix, p, h, out, stake_p, stem_p, leaf_p, fruit_p, calyx_p, tie_p):
    x, y, z0 = p
    dv4.cube(prefix + "Stake", (.025, .025, h + .1), loc=(x, y - .03, z0 + h / 2 - .05), rot=(0, 0, 45), paint=stake_p, out=out, bevel=.004)
    pts = [(x, y, z0 - .02), (x + .015, y + .01, z0 + h * .35), (x - .01, y + .015, z0 + h * .7), (x + .012, y, z0 + h * .98)]
    dv4.tube(prefix + "Stem", pts, radius=.009, res=6, paint=stem_p, out=out, resolution=4, taper=[(0, 1.0), (1, .6)])
    for k, zz in enumerate((.3, .62)):
        dv4.torus(prefix + "Tie%d" % k, .024, .004, loc=(x, y - .015, z0 + h * zz), seg=8, minor=3, paint=tie_p, out=out)
    k = 0
    for zz in (.24, .46, .68, .92):
        for j in range(3):
            a = j * 120 + zz * 400 + RNG.uniform(-25, 25)
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            b0 = (x + c * .01, y + s * .01, z0 + h * zz)
            b1 = (x + c * .09, y + s * .09, z0 + h * zz + .03)
            dv4.tube(prefix + "Br%d" % k, [b0, b1], radius=.004, res=4, paint=stem_p, out=out, resolution=1, kind="POLY")
            LL = RNG.uniform(.08, .105)
            dv4.leaf(prefix + "Lf%d" % k, LL, LL * .7, loc=b1, rot=(10 + RNG.uniform(-20, 20), RNG.uniform(-25, 25), a - 90), paint=leaf_p, out=out,
                     shape="pointed", bend=.4, cup=.15, thickness=.003, nl=2, nw=2, wave=1.0)
            k += 1
    for i, (zz, a) in enumerate(((.33, 20), (.37, 160), (.54, 250), (.58, 80), (.76, 330), (.80, 140))):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        r = RNG.uniform(.026, .034)
        q = (x + c * .05, y + s * .05, z0 + h * zz)
        dv4.sphere(prefix + "Tom%d" % i, r, loc=q, scale=(1, 1, .9), seg=9, rings=6, paint=fruit_p, out=out)
        dv4.sphere(prefix + "Cal%d" % i, r * .4, loc=(q[0], q[1], q[2] + r * .8), scale=(1.4, 1.4, .4), seg=6, rings=3, paint=calyx_p, out=out)


def watering_can(p, yaw, can_p, dark_p, out="Body"):
    x, y, z = p
    def P(dx, dy, dz):
        q = L.rotz((dx, dy, dz), yaw)
        return (x + q[0], y + q[1], z + q[2])
    dv4.lathe("CanBody", [(0, 0), (.085, 0), (.095, .01), (.1, .06), (.095, .16), (.085, .18), (.06, .19), (.04, .2), (0, .2)], seg=18, loc=p, paint=can_p)
    dv4.torus("CanRim", .06, .008, loc=P(0, 0, .19), seg=20, minor=5, paint=can_p)
    dv4.tube("CanHandle", [P(0, -.09, .14), P(0, -.14, .2), P(0, -.1, .26), P(0, 0, .28), P(0, .1, .26), P(0, .14, .2), P(0, .09, .14)],
             radius=.011, res=6, paint=can_p, resolution=3)
    dv4.tube("CanSpout", [P(0, .09, .07), P(0, .17, .14), P(0, .24, .24)], radius=.012, res=6, paint=can_p, resolution=3, taper=[(0, 1.0), (1, .8)])
    dv4.lathe("CanRose", [(0, 0), (.03, 0), (.034, .01), (.02, .02), (0, .022)], seg=16, loc=P(0, .245, .245), rot=(-50, 0, yaw), paint=dark_p)


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.2, light=.36)
    wood_x = dv4.paint_wood("WoodX", base="A86A36", dark="4F2E16", light="D8A058", scale=4.0, dist=2.5, along="X", edge="E2B87E", tint=.3)
    wood_y = dv4.paint_wood("WoodY", base="A86A36", dark="4F2E16", light="D8A058", scale=4.0, dist=2.5, along="Y", edge="E2B87E", tint=.3)
    post_p = dv4.paint_wood("Post", base="8A5330", dark="432510", light="B9803F", scale=5.0, along="Z", edge="D6A266", tint=.1)
    stake_p = dv4.paint_wood("Stake", base="C49A62", dark="7A5A32", light="E8C78E", scale=6.0, along="Z", edge="F0D7A4", tint=.2)
    soil = dv4.paint_soil("Soil", base="4A3322", dark="2A1B11", light="6E4C33")
    lettuce_p = dv4.paint_leaf("Lettuce", base="7CC247", dark="3F8E2B", light="C8EA8A", vein="E3F5C2", veins=5)
    heart_p = dv4.paint_flat("Heart", "D9EE9A", dark="8EBF55", variation=.35, scale=20.0)
    carrot_top = dv4.paint_leaf("CarrotTop", base="3E8A30", dark="245A22", light="7DBF4E", vein="A8D880", veins=4)
    carrot_p = L.paint_fruit("Carrot", base="F07A1E", dark="B9500E", light="FFB066")
    tom_leaf = dv4.paint_leaf("TomLeaf", base="3C8C34", dark="1F5624", light="7CC24E", vein="B3DD8C", veins=5)
    stem_p = dv4.paint_wood("Stem", base="5E8A2E", dark="3C5A1E", light="8BB548", scale=8.0, along="Z", edge="A3C860", tint=0)
    tomato_p = L.paint_fruit("Tomato", base="E03A2C", dark="961E16", light="FF8E6E", var=.1)
    calyx_p = dv4.paint_flat("Calyx", "3E7A2A", dark="1E4A18", variation=.3)
    tie_p = dv4.paint_flat("Tie", "E0B040", dark="A87A1A", variation=.3)
    can_p = L.paint_metal("Can", base="1F9A8E", dark="156F66", light="7ED3C8")
    dark_p = dv4.paint_flat("CanDark", "2F3A40", dark="141A1E", variation=.3, edge="8A969E")
    white = L.paint_painted_wood("White", shade="D5CDBE", wear=.6, along="Z", grime_z=.05)
    grass = L.paint_grass("Grass")

    # ---- two raised beds side by side, a narrow path between them
    BW, BD, BH = .92, .84, .24
    zl = bed("A", -.5, .0, BW, BD, BH, wood_x, wood_y, post_p, soil)
    zr = bed("B", .5, .0, BW, BD, BH, wood_x, wood_y, post_p, soil)
    # ---- left bed: two rows of lettuces at the back, a carrot row in front
    k = 0
    for row_y, n in ((.24, 3), (-.02, 3)):
        for i in range(n):
            xx = -.5 - .3 + i * .3 + RNG.uniform(-.02, .02)
            lettuce("Let%d" % k, (xx, row_y + RNG.uniform(-.02, .02), zl + .01), RNG.uniform(.1, .115), "Body", lettuce_p, heart_p)
            k += 1
    for i in range(5):
        xx = -.5 - .34 + i * .17
        carrot("Car%d" % i, (xx, -.27 + RNG.uniform(-.02, .02), zl + .012), "Body", carrot_top, carrot_p)
    # ---- right bed: three staked tomato plants (each sways from the soil)
    for i, (xx, yy) in enumerate(((.5 - .3, .2), (.5, -.18), (.5 + .3, .17))):
        sw = "Anim Sway" + ("" if i == 0 else ".%03d" % i)
        dv4.pivot(sw, (xx, yy, zr))
        tomato_plant("Tom%d" % i, (xx, yy, zr), .5, sw, stake_p, stem_p, tom_leaf, tomato_p, calyx_p, tie_p)
    # low lettuce-like herbs in the free corner of the right bed
    lettuce("Let6", (.5 - .3, -.27, zr + .01), .095, "Body", lettuce_p, heart_p)
    lettuce("Let7", (.5 + .25, -.28, zr + .01), .09, "Body", lettuce_p, heart_p)
    # ---- watering can on the path in front, a little picket edging and grass tufts
    watering_can((.3, .47, 0), 90, can_p, dark_p)
    for i in range(7):
        xx = -.95 + i * .105
        H = .2 + RNG.uniform(-.01, .01)
        L.prism("Pick%d" % i, [(-.022, 0), (.022, 0), (.022, H - .035), (0, H), (-.022, H - .035)], .014, loc=(xx, .50, .01), paint=white, bevel=.003)
    dv4.cube("PickRail", (.74, .016, .035), loc=(-.635, .488, .11), paint=white, bevel=.003)
    L.grass_tuft("GrassA", (-.2, .47, 0), grass, n=5, L=.08, spread=30)
    L.grass_tuft("GrassB", (.93, .46, 0), grass, n=5, L=.08, spread=30)
    L.grass_tuft("GrassC", (-.97, -.46, 0), grass, n=4, L=.07, spread=30)
    return {"name": "VeggieGarden", "tex": 1024, "budget": 15000, "floor": "C9C3B8"}
