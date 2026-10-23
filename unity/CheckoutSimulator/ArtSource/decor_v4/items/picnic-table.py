"""picnic-table: classic A-frame wooden picnic table with attached benches, red gingham cloth, wicker basket with fruit, plates and
a butterfly on "Anim Bob". Footprint half .90 x .75, height <= .9 (Blender: X along the table, benches at +/-Y, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_I as L

CONFIG = {"floor": "C9C3B8", "seed": 24}


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.25, light=.36)
    wood = dv4.paint_wood("Plank", base="B8773F", dark="5C3619", light="E5AE62", scale=3.5, dist=2.5, along="X", edge="EAC58C", tint=.3)
    wood_leg = dv4.paint_wood("Leg", base="A86A36", dark="50301A", light="D8A058", scale=5.0, dist=2.0, along="Z", edge="E2B87E", tint=.2)
    bolt = dv4.paint_iron("Bolt", base="2A313A", mid="4A5560", edge="C0CAD2", rust_amt=.1)
    cloth = L.paint_gingham("Cloth", a="D74A3C", b="FBF7F0", cell=.055)
    wicker = L.paint_wicker("Wicker", bands=75.0, stakes=20)
    plate = L.paint_plate("Plate", rim="1F9A8E", rim2="E0B040")
    apple = L.paint_fruit("Apple", base="D7392F", dark="8E1F1A", light="F58A6A")
    green = L.paint_fruit("Pear", base="9BC43F", dark="5C8A22", light="D7EC8C")
    orange = L.paint_fruit("Orange", base="F08A1E", dark="B85A0E", light="FFC66A")
    stem_p = dv4.paint_flat("Stem", "5A3A20", dark="2A1A0C", variation=.3)
    wing_p = dv4.paint_flat("Wing", "F6A52A", dark="C9530F", variation=.35, scale=30.0, edge="3A2416", edge_r=.006, edge_k=1.5, k_ao=.3)
    body_p = dv4.paint_flat("Bug", "2A2520", dark="000000", variation=.3, edge="6A5A4A")

    TW, TD, TZ, T = 1.70, .70, .72, .04      # table top width, depth, height, plank thickness
    # ---- table top: 5 planks with gaps, edge-bevelled; end battens underneath
    n = 5; pw = (TD - .015 * (n - 1)) / n
    for i in range(n):
        y = -TD / 2 + pw / 2 + i * (pw + .015)
        dv4.cube("Top%d" % i, (TW, pw, T), loc=(0, y, TZ - T / 2), paint=wood, bevel=.009, segs=2)
    for x in (-.62, .62):
        dv4.cube("Batten%s" % x, (.09, TD - .02, .04), loc=(x, 0, TZ - T - .02), paint=wood_leg, bevel=.006)
    # ---- benches: 2 planks each side at z .45, on cross cleats that rest on the A-frames
    BZ, BY = .45, .60
    for sy in (-1, 1):
        for j in (-1, 1):
            dv4.cube("Seat%d%d" % (sy, j), (TW, .13, T), loc=(0, sy * BY + j * .0725, BZ - T / 2), paint=wood, bevel=.009, segs=2)
    # ---- A-frame legs at x = +/-.55: two planks leaning out from under the top to the bench ends, plus the bench cleat
    for x in (-.55, .55):
        for sy in (-1, 1):
            # leg plank from (y0, z0) at the top to (y1, 0) at the floor: length and lean angle
            y0, y1 = sy * .16, sy * .70
            dz = TZ - T - .02; dy = y1 - y0
            Ln = math.hypot(dy, dz); ang = math.degrees(math.atan2(dy, dz))
            dv4.cube("LegP%s%d" % (x, sy), (.09, .045, Ln + .02), loc=(x, (y0 + y1) / 2, dz / 2), rot=(-ang, 0, 0), paint=wood_leg, bevel=.007, segs=2)
        # bench cleat (horizontal, carries both benches, crosses the legs)
        dv4.cube("Cleat%s" % x, (.07, 2 * BY + .30, .09), loc=(x, 0, BZ - T - .045), paint=wood_leg, bevel=.007, segs=2)
        # carriage bolts where cleat and legs cross, and on the top battens
        for sy in (-1, 1):
            dv4.sphere("BoltC%s%d" % (x, sy), .013, loc=(x + .036, sy * .42, BZ - T - .045), scale=(.5, 1, 1), seg=8, rings=4, paint=bolt)
            dv4.sphere("BoltC2%s%d" % (x, sy), .013, loc=(x - .036, sy * .42, BZ - T - .045), scale=(.5, 1, 1), seg=8, rings=4, paint=bolt)
    # diagonal brace under the table between the two cleats
    dv4.cube("Brace", (1.0, .045, .07), loc=(0, 0, BZ - T - .045 + .005), rot=(0, 0, 0), paint=wood_leg, bevel=.006)
    # ---- the cloth: lies on the top with two draped ends and gently wavy hems
    CW, CD = 1.50, .64
    c = dv4.patch("Cloth", CW, CD, 20, 8, loc=(0, 0, TZ + .006), paint=cloth)
    dv4.mod_solidify(c, .01, offset=-1.0)
    for sx in (-1, 1):
        f = dv4.patch("Flap%d" % sx, .2, CD, 4, 8, loc=(sx * (CW / 2 + .005), 0, TZ - .095), rot=(0, sx * 90, 0), paint=cloth)
        dv4.mod_displace(f, strength=.012, size=.08, mid=.5, direction="X")
        dv4.mod_solidify(f, .01, offset=0.0)
    # ---- basket with fruit (wicker lathe with a scalloped weave edge and an arched handle)
    bx, by = -.30, -.02
    prof = [(0, 0), (.12, 0), (.13, .01), (.14, .08), (.15, .15), (.16, .17), (.145, .17), (.135, .16), (.125, .08), (.115, .02), (0, .02)]
    L.lathe_az("Basket", prof, seg=28, loc=(bx, by, TZ + .012), paint=wicker)
    dv4.torus("BasketRim", .152, .012, loc=(bx, by, TZ + .012 + .17), seg=28, minor=6, paint=wicker)
    dv4.tube("Handle", [(bx - .14, by, TZ + .17), (bx - .125, by, TZ + .255), (bx, by, TZ + .285), (bx + .125, by, TZ + .255), (bx + .14, by, TZ + .17)],
             radius=.012, res=8, paint=wicker, resolution=4)
    fruits = [((bx - .05, by + .03, TZ + .17), .05, apple), ((bx + .05, by - .02, TZ + .165), .048, green), ((bx + .01, by + .06, TZ + .16), .045, orange),
              ((bx - .02, by - .07, TZ + .155), .042, apple), ((bx + .08, by + .05, TZ + .15), .04, orange)]
    for i, (p, r, pt) in enumerate(fruits):
        dv4.sphere("Fruit%d" % i, r, loc=p, scale=(1, 1, .92), seg=12, rings=8, paint=pt)
        dv4.tube("FStem%d" % i, [(p[0], p[1], p[2] + r * .85), (p[0] + .008, p[1], p[2] + r + .018)], radius=.003, res=5, paint=stem_p, resolution=2)
    # a loose apple and a pear on the cloth
    dv4.sphere("ApplePear0", .045, loc=(.52, -.18, TZ + .058), scale=(1, 1, .92), seg=12, rings=8, paint=apple)
    dv4.tube("FStemA", [(.52, -.18, TZ + .097), (.528, -.18, TZ + .12)], radius=.003, res=5, paint=stem_p, resolution=2)
    # ---- two plates with a fruit on each
    for i, (px, py) in enumerate(((.25, .20), (.25, -.22))):
        L.lathe_rz("Plate%d" % i, [(0, 0), (.09, 0), (.1, .004), (.125, .012), (.135, .018), (.13, .022), (.12, .02), (.1, .012), (0, .008)],
                   seg=28, loc=(px, py, TZ + .012), paint=plate)
    dv4.sphere("Orange1", .04, loc=(.25, .20, TZ + .055), scale=(1, 1, .92), seg=12, rings=8, paint=orange)
    dv4.sphere("Pear1", .042, loc=(.25, -.22, TZ + .058), scale=(.95, .95, 1.1), seg=12, rings=8, paint=green)
    dv4.tube("FStemP", [(.25, -.22, TZ + .10), (.255, -.22, TZ + .125)], radius=.003, res=5, paint=stem_p, resolution=2)
    # ---- a butterfly hovering over the basket (bob)
    bb = "Anim Bob"; pb = (bx - .22, by - .20, TZ + .20); dv4.pivot(bb, pb)
    dv4.sphere("BugBody", .011, loc=pb, scale=(1, 2.8, 1), seg=8, rings=5, paint=body_p, out=bb)
    dv4.sphere("BugHead", .011, loc=(pb[0], pb[1] + .032, pb[2] + .002), seg=8, rings=5, paint=body_p, out=bb)
    fore = [(0, 0), (.03, .04), (.075, .046), (.088, .024), (.07, .002)]
    hind = [(0, 0), (.062, -.006), (.07, -.034), (.045, -.05), (.012, -.024)]
    for sx in (-1, 1):
        for nm, pts in (("WingF", fore), ("WingB", hind)):
            pp = [(sx * x, y) for x, y in pts]
            if sx < 0:
                pp.reverse()
            # wings lifted 35 degrees from the body (rotation about the body axis), mid-flap
            L.prism(nm + "%d" % sx, pp, .003, loc=(pb[0] + sx * .006, pb[1], pb[2]), rot=(0, -sx * 35, 0), paint=wing_p, out=bb, bevel=0, axis="Z")
    return {"name": "PicnicTable", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
