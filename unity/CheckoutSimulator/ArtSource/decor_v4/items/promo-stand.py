"""promo-stand: promotional display - printed product boxes stacked on a wooden pallet with a tray of cans and bottles,
a navy pole with a gold arm from which a red starburst sign with a gold % swings ("Anim Sway"). Pictograms only.
Footprint half .58 x .44, height <= 1.9 (front +Y)."""
import os, sys, math
import dv4
from dv4 import RNG, MATH, MIX, RAMP, NOISE, SMOOTH
sys.path.insert(0, os.path.join(dv4.ROOT, "items"))
import _lib_B as lib

lib.install_fixes()
CONFIG = {"floor": "F4EFE4", "seed": 17}
PZ = .13     # pallet height


def paint_burst_sign(name, center):
    """Red starburst sign: cream inner seal ring and a big gold % on both faces (plane XZ)."""
    def r(c):
        nt = c.nt
        u, v = lib.rel(c, center[0], center[1], "xz")
        u = MATH(nt, "MULTIPLY", u, -1.0)
        col = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 6.0, 2.0), .15), "D74A3C", "7A1F18")
        faces = MATH(nt, "MAXIMUM", lib.face_mask(c, "y", 1.0, .5, .9), lib.face_mask(c, "y", -1.0, .5, .9))
        ring = lib.m_ring(c, u, v, .165, .152)
        col = MIX(nt, MATH(nt, "MULTIPLY", ring, faces), col, "F4EFE4")
        dots = None
        for i in range(12):
            a = math.radians(i * 30 + 15)
            m = lib.m_circle(c, MATH(nt, "SUBTRACT", u, math.cos(a) * .19), MATH(nt, "SUBTRACT", v, math.sin(a) * .19), .009)
            dots = m if dots is None else MATH(nt, "MAXIMUM", dots, m)
        col = MIX(nt, MATH(nt, "MULTIPLY", dots, faces), col, "FFE08A")
        pct = lib.m_percent(c, u, v, .09, soft=.002)
        col = MIX(nt, MATH(nt, "MULTIPLY", pct, faces), col, "FFD040")
        return col
    return dv4.paint(name, r, edge="FF8C7A", edge_k=.7, edge_r=.005)


def paint_can(name, base, label="F6F1E6", icon_col="D74A3C", z0=.0, z1=.0):
    def r(c):
        nt = c.nt
        body = lib.paint_chrome  # noqa (metal look is done inline below)
        col = RAMP(nt, c.nz, [(-1.0, "5A626A"), (-.1, "AAB3BA"), (.1, "5A626A"), (.3, "E6ECEF"), (1.0, "C9D2D6")])
        lab = lib.band_z(c, z0, z1, .003)
        lcol = MIX(nt, MATH(nt, "MULTIPLY", NOISE(nt, c.pos, 8.0, 2.0), .12), base, "000000")
        col = MIX(nt, lab, col, lcol)
        stripe = MATH(nt, "MAXIMUM", lib.band_z(c, z0 + .008, z0 + .016, .002), lib.band_z(c, z1 - .016, z1 - .008, .002))
        col = MIX(nt, stripe, col, label)
        return col
    return dv4.paint(name, r, k_ao=.5, k_light=.3, edge="FFFFFF", edge_k=.6, edge_r=.003)


def build():
    dv4.FINISH.update(ao=.6, ao_dist=.22, light=.36)
    wood = dv4.paint_wood("Pallet", base="C9975A", dark="7B5230", light="E8C089", scale=4.0, dist=2.5, along="X", edge="F0D2A0", tint=.3)
    wood_y = dv4.paint_wood("PalletY", base="B98852", dark="6E4A2A", light="DDB07A", scale=4.0, dist=2.5, along="Y", edge="E8C690", tint=.3)
    navy = lib.paint_gloss("Navy", "1D2B4F", "0F1832", "5C6F9E", hl_amt=.35)
    gold = dv4.paint_gold("Gold")
    teal_glass = lib.paint_gloss("Bottle", "1F9A8E", "12605A", "8FE3D8", hl_amt=.5)
    dark = dv4.paint_flat("Dark", "2A2F36", variation=.05)

    # ---- pallet: three bearers (blocks + stringer), deck boards with gaps, bottom boards
    for y in (-.33, 0.0, .33):
        for x in (-.46, 0.0, .46):
            dv4.cube("Block%s%s" % (x, y), (.14, .12, .075), loc=(x, y, .0575), paint=wood_y, bevel=.006, segs=2)
        dv4.cube("Stringer%s" % y, (1.12, .10, .02), loc=(0, y, .105), paint=wood, bevel=.004, segs=1)
    for x in (-.46, 0.0, .46):
        dv4.cube("Bottom%s" % x, (.12, .84, .02), loc=(x, 0, .01), paint=wood_y, bevel=.004, segs=1)
    for i in range(6):
        y = -.36 + i * .144
        dv4.cube("Deck%d" % i, (1.14, .11, .022), loc=(0, y, PZ - .011), paint=wood, bevel=.005, segs=2)
    # ---- printed boxes (band colour, pictogram): tier 1 = 3 x 2, tier 2 = 2 at the back, tier 3 = 1
    boxes = [((-.37, .18, PZ + .15), (.34, .36, .30), "D74A3C", "star", "FFFFFF"),
             ((0.0, .18, PZ + .15), (.34, .36, .30), "1F9A8E", "heart", "FFFFFF"),
             ((.37, .18, PZ + .15), (.34, .36, .30), "E0B040", "tag", "1D2B4F"),
             ((-.37, -.2, PZ + .15), (.34, .36, .30), "3E8FD6", "burst", "FFFFFF"),
             ((0.0, -.2, PZ + .15), (.34, .36, .30), "EC862E", "percent", "FFFFFF"),
             ((.37, -.2, PZ + .15), (.34, .36, .30), "5A9D33", "arrow", "FFFFFF"),
             ((-.19, -.2, PZ + .30 + .14), (.34, .36, .28), "EE8FAE", "heart", "FFFFFF"),
             ((.19, -.2, PZ + .30 + .14), (.34, .36, .28), "1D2B4F", "star", "E0B040"),
             ((0.0, -.2, PZ + .58 + .12), (.32, .34, .24), "D74A3C", "percent", "FFFFFF")]
    for i, (p, s, band, icon, ic) in enumerate(boxes):
        yaw = RNG.uniform(-5, 5)
        dv4.cube("Box%d" % i, s, loc=p, rot=(0, 0, yaw), paint=lib.paint_box("Box%d" % i, p, s, band, icon, ic), bevel=.012, segs=2)
    # ---- front of tier 2: a tray of cans and three bottles
    z0 = PZ + .30
    dv4.cube("Tray", (.66, .30, .03), loc=(-.15, .20, z0 + .015), paint=wood, bevel=.005, segs=2)
    cans = [("D74A3C", "F6F1E6"), ("1F9A8E", "F6F1E6"), ("E0B040", "1D2B4F"), ("3E8FD6", "F6F1E6"), ("EC862E", "F6F1E6")]
    k = 0
    for j in range(2):
        for i in range(5):
            x = -.41 + i * .13; y = .13 + j * .14
            base, lab = cans[(i + j) % 5]
            cp = paint_can("Can%d" % k, base, lab, z0=z0 + .03 + .03, z1=z0 + .03 + .11)
            dv4.cylinder("Can%d" % k, .052, .135, loc=(x, y, z0 + .03), seg=14, paint=cp, bevel=.006)
            dv4.lathe("CanLid%d" % k, [(0, 0), (.04, 0), (.046, .006)], seg=14, loc=(x, y, z0 + .165), paint=dark, cap=False)
            k += 1
    for i, (x, y) in enumerate(((.29, .14), (.41, .22), (.33, .29))):
        prof = [(0, 0), (.045, 0), (.05, .01), (.05, .17), (.04, .21), (.022, .24), (.02, .28), (0, .28)]
        dv4.lathe("Bottle%d" % i, prof, seg=16, loc=(x, y, z0 + .03), paint=teal_glass)
        dv4.lathe("Cap%d" % i, [(0, 0), (.022, 0), (.023, .025), (0, .025)], seg=12, loc=(x, y, z0 + .03 + .275), paint=gold)
        dv4.lathe("Label%d" % i, [(.052, 0), (.052, .08)], seg=16, loc=(x, y, z0 + .03 + .05), paint=gold, cap=False)
    # ---- sign pole: navy post at the back with a gold base cup and finial, gold arm forward, hook
    dv4.lathe("PoleBase", [(0, PZ), (.06, PZ), (.065, PZ + .01), (.04, PZ + .05), (.028, PZ + .07)], seg=20, loc=(0, -.38, 0), paint=gold)
    dv4.tube("Pole", [(0, -.38, PZ + .05), (0, -.38, 1.80)], radius=.022, res=10, paint=navy, kind="POLY", resolution=1)
    dv4.sphere("PoleTop", .034, loc=(0, -.38, 1.82), seg=14, rings=10, paint=gold)
    dv4.tube("Arm", [(0, -.38, 1.74), (0, -.2, 1.76), (0, .04, 1.74)], radius=.013, res=8, paint=gold, resolution=4)
    dv4.tube("Brace", [(0, -.38, 1.58), (0, -.24, 1.66), (0, -.16, 1.75)], radius=.009, res=6, paint=gold, resolution=3)
    dv4.torus("Hook", .022, .006, loc=(0, .04, 1.715), rot=(0, 90, 0), seg=16, minor=5, paint=gold)
    # ---- hanging starburst sign (swings from the hook)
    sway = "Anim Sway"; dv4.pivot(sway, (0, .04, 1.715))
    SC = (0, .04, 1.42)
    for x in (-.09, .09):
        dv4.tube("Chain%s" % x, [(0, .04, 1.71), (x, .04, 1.62)], radius=.005, res=5, paint=gold, out=sway, kind="POLY", resolution=1)
    dv4.torus("Eye%s" % 0, .018, .005, loc=(0, .04, 1.70), rot=(90, 0, 0), seg=14, minor=5, paint=gold, out=sway)
    signp = paint_burst_sign("Sign", (SC[0], SC[2]))
    dv4.lathe("Sign", [(0, -.012), (.20, -.012), (.21, -.006), (.21, .006), (.20, .012), (0, .012)], seg=48, loc=SC, rot=(-90, 0, 0),
              paint=signp, scallop=(12, .13))
    dv4.lathe("SignRim", [(.20, -.014), (.215, -.007), (.215, .007), (.20, .014)], seg=48, loc=SC, rot=(-90, 0, 0), paint=gold, cap=False, scallop=(12, .13))
    for x in (-.09, .09):
        dv4.torus("SignEye%s" % x, .012, .004, loc=(x, .04, 1.615), rot=(90, 0, 0), seg=12, minor=5, paint=gold, out=sway)
    return {"name": "PromoStand", "tex": 1024, "budget": 10000, "floor": "F4EFE4"}
