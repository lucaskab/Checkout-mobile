"""picket-fence: 2 m section of white picket fence (pointed pickets, capped posts, chipped paint) with flower mounds and a
climbing rose at its foot. Footprint half 1.0 x .15, height <= 1.0 (Blender: X along the fence, front = +Y)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dv4
from dv4 import RNG
import _lib_I as L

CONFIG = {"floor": "C9C3B8", "seed": 21}


def ell_point(C, R, a, e, k=1.0):
    a, e = math.radians(a), math.radians(e)
    return (C[0] + R[0] * math.cos(e) * math.cos(a) * k, C[1] + R[1] * math.cos(e) * math.sin(a) * k, C[2] + R[2] * math.sin(e) * k)


def flower_mound(prefix, C, R, out, foliage, leaf_p, bloom_p, n_leaves=9, n_blooms=10, br=.03):
    m = dv4.icosphere(prefix + "Mound", 1.0, loc=C, scale=R, subdiv=2, paint=foliage, out=out)
    dv4.mod_displace(m, strength=.025, size=.12, mid=.5)
    for i in range(n_leaves):
        # leaves lean out at the two ends of the mound (keeps the depth inside the footprint) and up on top
        a = (0 if i % 2 else 180) + RNG.uniform(-50, 50); e = RNG.uniform(5, 45)
        p = ell_point(C, R, a, e, .9)
        LL = RNG.uniform(.06, .085)
        dv4.leaf(prefix + "Leaf%d" % i, LL, LL * .7, loc=p, rot=(RNG.uniform(25, 55), RNG.uniform(-20, 20), a - 90), paint=leaf_p, out=out,
                 shape="spade", bend=.3, cup=.25, thickness=.003, nl=3, nw=2)
    for i in range(n_blooms):
        a = RNG.uniform(0, 360); e = RNG.uniform(30, 85)
        p = ell_point(C, R, a, e, .96)
        r = br * RNG.uniform(.85, 1.2)
        L.bloom(prefix + "Bloom%d" % i, r, loc=p, rot=(RNG.uniform(-14, 14), RNG.uniform(-14, 14), RNG.uniform(0, 360)), paint=bloom_p,
                out=out, flat=.6)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.22, light=.36)
    white = L.paint_painted_wood("White", shade="D3CBBC", wear=.75, along="Z")
    white_x = L.paint_painted_wood("WhiteX", shade="D3CBBC", wear=.6, along="X", grime_z=0)
    nail = dv4.paint_iron("Nail", base="4A5058", mid="6C7680", edge="C7CFD6", rust="8A4A24", rust_amt=.5)
    foliage = L.paint_foliage("Foliage", dark="2A6B2A", base="4E9E35", light="93D44C")
    foliage2 = L.paint_foliage("Foliage2", dark="2D6E3A", base="5AA648", light="A4DA60")
    leaf_p = dv4.paint_leaf("Leaf", base="3E9238", dark="22602A", light="86C851", vein="C2E59A", veins=5)
    rose_leaf = dv4.paint_leaf("RoseLeaf", base="357F33", dark="1E5226", light="6FB848", vein="A7D688", veins=5)
    stem_p = dv4.paint_wood("Stem", base="5E7A2E", dark="3C5320", light="8BA648", scale=8.0, along="Z", edge="A3B860", tint=0)
    bloom_pink = L.paint_bloom("BloomPink", cols=("EE8FAE", "D74A3C", "F7B6CB", "E86A8A"), petals=6)
    bloom_warm = L.paint_bloom("BloomWarm", cols=("FFD97A", "EC862E", "F4EFE4", "F2B33D"), petals=7)
    bloom_rose = L.paint_bloom("BloomRose", cols=("E4476B", "F06C8A", "D73A5B"), centre="F3C64B", petals=5)
    grass = L.paint_grass("Grass")

    # ---- posts with cap plates and pyramid caps
    for x in (-.9, .9):
        dv4.cube("Post%s" % x, (.1, .1, .9), loc=(x, 0, .45), paint=white, bevel=.008, segs=2)
        dv4.cube("CapPlate%s" % x, (.136, .136, .022), loc=(x, 0, .911), paint=white_x, bevel=.005, segs=2)
        dv4.lathe("Cap%s" % x, [(0, 0), (.094, 0), (.094, .006), (0, .075)], seg=4, loc=(x, 0, .92), rot=(0, 0, 45), paint=white_x)
    # ---- rails
    for z in (.27, .64):
        dv4.cube("Rail%s" % z, (1.8, .04, .09), loc=(0, -.015, z), paint=white_x, bevel=.006, segs=2)
    # ---- pickets (pointed), slightly uneven heights and tilts, nails over the rails
    xs = [-.78 + i * .13 for i in range(13)]
    for i, x in enumerate(xs):
        H = .80 + RNG.uniform(-.018, .012)
        w = .045
        pts = [(-w, 0), (w, 0), (w, H - .065), (0, H), (-w, H - .065)]
        L.prism("Picket%d" % i, pts, .025, loc=(x, .018, .03), rot=(0, RNG.uniform(-1.3, 1.3), 0), paint=white, bevel=.005, segs=2)
        for z in (.27, .64):
            dv4.sphere("Nail%d_%s" % (i, z), .0075, loc=(x, .032, z), scale=(1, .55, 1), seg=6, rings=3, paint=nail)
    # ---- grass tufts at the posts
    L.grass_tuft("GrassL", (-.9, .085, 0), grass, n=6, L=.09)
    L.grass_tuft("GrassR", (.93, .075, 0), grass, n=6, L=.09)
    L.grass_tuft("GrassM", (.22, .07, 0), grass, n=5, L=.07)

    # ---- left flower mound + climbing rose (sway from the ground)
    s0 = "Anim Sway"; dv4.pivot(s0, (-.52, .04, 0))
    C, R = (-.5, .03, .07), (.21, .085, .085)
    flower_mound("L", C, R, s0, foliage, leaf_p, bloom_pink, n_leaves=10, n_blooms=12, br=.034)
    stem = [(-.62, .04, .06), (-.665, .046, .25), (-.59, .046, .44), (-.645, .046, .62), (-.575, .048, .80), (-.52, .05, .89)]
    dv4.tube("RoseStem", stem, radius=.009, res=6, paint=stem_p, out=s0, resolution=4, taper=[(0, 1.0), (1, .55)])
    br1 = [(-.62, .046, .40), (-.52, .05, .48), (-.42, .052, .55), (-.36, .054, .62)]
    br2 = [(-.61, .046, .64), (-.70, .05, .70), (-.77, .052, .78), (-.80, .054, .86)]
    br3 = [(-.6, .048, .78), (-.54, .052, .74), (-.46, .054, .70)]
    for k, b in enumerate((br1, br2, br3)):
        dv4.tube("RoseBranch%d" % k, b, radius=.0065, res=6, paint=stem_p, out=s0, resolution=3, taper=[(0, 1.0), (1, .5)])
    rose_pts = stem[1:] + br1[1:] + br2[1:] + br3[1:]
    for i, p in enumerate(rose_pts):
        for j in range(3):
            a = RNG.uniform(0, 360)
            q = (p[0] + RNG.uniform(-.03, .03), p[1] + .015, p[2] + RNG.uniform(-.04, .04))
            LL = RNG.uniform(.05, .075)
            dv4.leaf("RoseLeaf%d_%d" % (i, j), LL, LL * .62, loc=q, rot=(RNG.uniform(-10, 30), RNG.uniform(-20, 20), a), paint=rose_leaf,
                     out=s0, shape="spade", bend=.25, cup=.2, thickness=.003, nl=3, nw=2)
    for i, p in enumerate([br1[-1], br2[-1], br3[-1], stem[-1], (-.655, .05, .33), (-.60, .05, .55), (-.69, .05, .74), (-.47, .05, .50), (-.75, .05, .80), (-.62, .05, .18), (-.40, .05, .60)]):
        L.bloom("Rose%d" % i, RNG.uniform(.026, .034), loc=(p[0], p[1] + .022, p[2]), rot=(-70 + RNG.uniform(-15, 15), RNG.uniform(-20, 20), 0),
                paint=bloom_rose, out=s0, flat=.7)

    # ---- right flower mound (warm colours)
    s1 = "Anim Sway.001"; dv4.pivot(s1, (.52, .04, 0))
    flower_mound("R", (.54, .03, .065), (.2, .082, .08), s1, foliage2, leaf_p, bloom_warm, n_leaves=10, n_blooms=12, br=.034)
    # ---- small middle clump
    s2 = "Anim Sway.002"; dv4.pivot(s2, (.02, .06, 0))
    flower_mound("M", (.02, .055, .045), (.12, .065, .055), s2, foliage, leaf_p, bloom_pink, n_leaves=5, n_blooms=6, br=.025)
    return {"name": "PicketFence", "tex": 1024, "budget": 10000, "floor": "C9C3B8"}
