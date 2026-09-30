"""Staff props for the market, modelled in Blender with the Interior Kit helpers (Unity space, metres).

Run inside the connected Blender after build_interior_kit.py has been exec'd into the same namespace, or:
blender -b --python scripts/blender/build_staff_props.py
Output: Assets/Art/Staff/Models/<name>.fbx
  staff-door     rear roller door: frame, coil housing, guide rails, sign, lamp; "Anim Curtain" is the slatted
                 curtain (CheckoutStaff rolls it up). Built 1.6 m wide, 2.2 m clear.
  staff-cart     janitor cart: bucket with wringer, trash bag, spray bottles, dustpan and brooms.
  staff-wetsign  A-frame "PISO MOLHADO" sign.
  staff-ladder   folding aluminium step ladder.
  staff-pallet   pallet stacked with boxes (the rear doorstep before the market has a storage).
  staff-puddle   spilled drink: glossy puddle, tipped bottle, splashes.
  staff-dirt-a   muddy footprints and a smear.
  staff-dirt-b   litter: crumpled paper, wrapper, paper cup, crumbs.
  staff-path     one tile of the staff walkway (pavers and yellow edge lines) used as material swatches.
"""
import math
import os

NS = globals()
if "Model" not in NS:
    exec(open(r"C:\Checkout-mobile\scripts\blender\build_interior_kit.py", encoding="utf-8").read(), NS)

UNITY = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets"
STAFF_OUT = os.path.join(UNITY, "Art", "Staff", "Models")
STAFF_BUILDERS = {}


def staff_model(name):
    def wrap(fn):
        STAFF_BUILDERS[name] = fn
        return fn
    return wrap


@staff_model("staff-door")
def staff_door(m):
    # Sits in the rear wall opening (1.8 m between the wall ends, 0.5 m thick wall). Unity turns it 180 deg so the
    # sign faces the yard. Everything stays under the 2.49 m wall top. Parts overlap a few mm at the joins.
    W, H = 1.6, 2.2
    for s in (-1, 1):
        box(m, (.1, H + .1, .3), (s * (W / 2 + .05), (H + .1) / 2, 0), "C_" + DARK, .015)
        for z in (-.152, .152):
            box(m, (.106, .9, .012), (s * (W / 2 + .05), .45, z), "T_IK_Hazard", .003)
        box(m, (.05, H, .09), (s * (W / 2 - .01), H / 2, .06), "C_" + STEEL, .008)
    box(m, (W + .2, .1, .3), (0, H + .05, 0), "C_" + DARK, .015)
    # Coil housing on the inside face (+Z before the turn), ribs and the motor.
    box(m, (W + .2, .26, .3), (0, H + .15, .26), "C_8FA3AE", .04)
    box(m, (W + .22, .03, .31), (0, H + .03, .26), "C_" + DARK, .008)
    for x in (-.6, 0, .6):
        box(m, (.02, .22, .306), (x, H + .15, .26), "C_7F95A3", .004)
    box(m, (.22, .2, .2), (W / 2 + .2, H + .12, .3), "C_2F6FAD", .03)
    cyl(m, .07, .14, (W / 2 + .02, H + .12, .3), "C_" + STEEL, 12, .01, roll=90)
    # Outside: "SOMENTE FUNCIONÁRIOS" plate on the wall beside the door, a caged lamp over the opening.
    rounded_panel(m, .56, .36, (W / 2 + .55, 1.55, -.275), "C_" + WHITE, .02, .04)
    rounded_panel(m, .6, .4, (W / 2 + .55, 1.55, -.262), "C_D74A3C", .015, .05)
    text_lite(m, "SOMENTE", (W / 2 + .55, 1.62, -.29), .075, "C_D74A3C", .006)
    text_lite(m, "FUNCIONÁRIOS", (W / 2 + .55, 1.5, -.29), .06, "C_D74A3C", .006)
    box(m, (.34, .09, .16), (0, H + .19, -.2), "C_" + DARK, .02)
    box(m, (.28, .05, .12), (0, H + .13, -.22), "E_FFF4DC", .01)
    for x in (-.12, 0, .12):
        box(m, (.015, .08, .015), (x, H + .12, -.28), "C_" + DARK, .003)
    # Threshold plate with hazard stripes on both faces.
    box(m, (W + .2, .02, .5), (0, .01, 0), "T_IK_Diamond", .004)
    box(m, (W + .2, .022, .08), (0, .011, -.29), "T_IK_Hazard", .003)
    box(m, (W + .2, .022, .08), (0, .011, .29), "T_IK_Hazard", .003)
    # Curtain: slats, bottom bar with rubber seal and lift handles, vision strip. CheckoutStaff rolls it up.
    cur = m.anim("Anim Curtain")
    box(m, (W - .02, H - .02, .03), (0, H / 2 + .01, .06), "T_IK_RollDoor", .004, obj=cur)
    for i in range(1, 11):
        box(m, (W - .02, .012, .036), (0, i * H / 11, .06), "C_6F8494", .003, obj=cur)
    box(m, (W, .08, .06), (0, .06, .06), "C_" + DARK, .012, obj=cur)
    box(m, (W, .02, .065), (0, .012, .06), "C_1A1A1A", .006, obj=cur)
    for s in (-1, 1):
        for z in (-.05, .05):
            bar(m, (s * .45, .14, .06 + z * 1.4), (s * .3, .14, .06 + z * 1.4), .012, "C_" + STEEL, 6, cur)
    for x in (-.5, .5):
        box(m, (.36, .1, .034), (x, 1.45, .06), "G_Glass", .01, obj=cur)


@staff_model("staff-warehouse-door")
def staff_warehouse_door(m):
    # Staff entrance on the central warehouse's south front, left of the forklift ramp: a steel door on the raised
    # floor (1.0 m up), a canopy with a light, a diamond-plate landing and six concrete steps down to the yard with
    # yellow handrails. Origin: yard level under the door, facade at z = 0, outside towards -Z.
    F, W, H = 1.0, 1.0, 2.1
    # Door frame on the wall.
    for sx in (-1, 1):
        box(m, (.1, H + .1, .12), (sx * (W / 2 + .05), F + (H + .1) / 2, -.04), "C_" + DARK, .012)
    box(m, (W + .3, .12, .12), (0, F + H + .06, -.04), "C_" + DARK, .012)
    # Door leaf (hinged on the west jamb; CheckoutStaff swings it open): steel with a vision panel, push bar,
    # kick plate and a staff sign.
    leaf = m.anim("Anim Leaf")
    box(m, (W - .04, H - .03, .05), (0, F + H / 2, -.05), "C_4A6C8A", .01, obj=leaf)
    for y in (F + .35, F + 1.1, F + 1.85):
        box(m, (W - .12, .015, .054), (0, y, -.05), "C_3E5C78", .003, obj=leaf)
    box(m, (.34, .5, .058), (.12, F + 1.5, -.05), "G_Glass", .01, obj=leaf)
    box(m, (W - .1, .22, .056), (0, F + .14, -.05), "C_" + STEEL, .006, obj=leaf)
    bar(m, (-.3, F + 1.0, -.1), (.36, F + 1.0, -.1), .016, "C_" + STEEL, 8, leaf)
    for x in (-.3, .36):
        box(m, (.03, .05, .06), (x, F + 1.0, -.08), "C_" + STEEL, .005, obj=leaf)
    rounded_panel(m, .42, .12, (.05, F + 1.78, -.08), "C_D74A3C", .012, .03, obj=leaf)
    text_lite(m, "FUNCIONÁRIOS", (.05, F + 1.775, -.09), .045, "C_" + WHITE, .004, obj=leaf)
    # Canopy with LED strip, tie rods and a caged wall light.
    top = F + H + .3
    box(m, (1.7, .1, .95), (0, top, -.48), "C_" + NAVY, .02)
    box(m, (1.72, .16, .05), (0, top, -.96), "C_" + GOLD, .01)
    box(m, (1.4, .02, .5), (0, top - .06, -.45), "E_FFF4DC", .004)
    for sx in (-1, 1):
        bar(m, (sx * .75, top + .05, -.9), (sx * .75, top + .75, -.02), .014, "C_" + STEEL, 6)
    box(m, (.2, .26, .12), (.95, F + 2.0, -.07), "C_" + DARK, .02)
    box(m, (.14, .16, .06), (.95, F + 1.98, -.12), "E_FFE9B0", .01)
    # Sign beside the door.
    rounded_panel(m, .7, .34, (-1.15, F + 1.55, -.03), "C_" + NAVY, .02, .04)
    rounded_panel(m, .74, .38, (-1.15, F + 1.55, -.02), "C_" + GOLD, .015, .05)
    text_lite(m, "ENTRADA", (-1.15, F + 1.62, -.05), .075, "C_" + GOLDL, .005)
    text_lite(m, "DE SERVIÇO", (-1.15, F + 1.49, -.05), .06, "C_" + WHITE, .005)
    # Landing on the floor level.
    LW, LD = 1.6, .95
    box(m, (LW, F, LD), (0, F / 2, -LD / 2 - .02), "C_B8B2A6", .02)
    box(m, (LW + .02, .03, LD + .02), (0, F + .015, -LD / 2 - .02), "T_IK_Diamond", .006)
    box(m, (LW + .03, .035, .07), (0, F + .02, -LD - .005), "T_IK_Hazard", .004)
    # Six steps down to the yard, each with a yellow nosing.
    n, tread = 6, .28
    rise = F / n
    SW = 1.24
    for i in range(n):
        y = F - (i + 1) * rise
        z0 = -LD - .02 - i * tread
        box(m, (SW, y, tread + .01), (0, y / 2, z0 - tread / 2), "C_C4BFB3", .012)
        box(m, (SW + .01, .02, .05), (0, y + .005, z0 - tread + .03), "C_F2C23F", .004)
    foot = -LD - .02 - n * tread
    box(m, (SW + .4, .03, .7), (0, .015, foot - .35), "C_B8B2A6", .01)
    # Handrails: landing edges and both flights, yellow on dark posts.
    for sx in (-1, 1):
        x = sx * (SW / 2 + .02)
        lx = sx * (LW / 2 - .03)
        posts = [(lx, F, -.12), (lx, F, -LD + .05), (x, F - rise, -LD - .02 - tread * .5), (x, rise, foot + tread * .5)]
        for (px, py, pz) in posts:
            bar(m, (px, py, pz), (px, py + .95, pz), .022, "C_" + DARK, 8)
        bar(m, (lx, F + .95, -.12), (lx, F + .95, -LD + .05), .026, "C_F2C23F", 8)
        bar(m, (lx, F + .95, -LD + .05), (x, F - rise + .95, -LD - .02 - tread * .5), .026, "C_F2C23F", 8)
        bar(m, (x, F - rise + .95, -LD - .02 - tread * .5), (x, rise + .95, foot + tread * .5), .026, "C_F2C23F", 8)
        bar(m, (x, F - rise + .5, -LD - .02 - tread * .5), (x, rise + .5, foot + tread * .5), .016, "C_F2C23F", 6)


@staff_model("staff-cart")
def staff_cart(m):
    # Chassis: yellow tub on four castors, grey frame, push handle at the back (+Z), rigs face -Z.
    for x in (-.32, .32):
        for z in (-.22, .22):
            cyl(m, .05, .03, (x, .05, z), "C_" + DARK, 12, 0, roll=90)
            box(m, (.04, .06, .04), (x, .1, z), "C_" + STEEL, .01)
    box(m, (.78, .05, .5), (0, .15, 0), "C_F2C23F", .02)
    box(m, (.8, .02, .52), (0, .175, 0), "C_E0B040", .01)
    # Bucket with dirty water and a wringer press.
    lathe(m, [(0, 0), (.16, 0), (.19, .28), (.2, .3)], (-.18, .18, .02), "C_F2C23F", 20, cap=False)
    lathe(m, [(0, 0), (.185, 0)], (-.18, .42, .02), "C_7A8A6A", 20)
    box(m, (.3, .12, .12), (-.18, .5, .02), "C_" + STEEL, .03)
    bar(m, (-.18, .56, .02), (-.18, .9, .14), .015, "C_" + STEEL, 8)
    box(m, (.16, .04, .04), (-.18, .92, .15), "C_" + DARK, .015)
    # Mop standing in the wringer.
    bar(m, (-.19, .36, -.02), (-.24, 1.55, .02), .016, "C_2E86DE", 8)
    ball(m, (-.19, .36, -.02), (.2, .09, .18), "C_E8E2D0", 10, 6)
    # Frame, handle and trash bag holder.
    for x in (-.36, .36):
        bar(m, (x, .18, .24), (x, 1.02, .3), .016, "C_" + STEEL, 8)
    bar(m, (-.38, 1.02, .3), (.38, 1.02, .3), .022, "C_" + DARK, 10)
    lathe(m, [(0, 0), (.15, .02), (.19, .25), (.21, .5), (.2, .58), (.16, .6)], (.2, .18, .08), "C_2A2A2A", 16)
    torus(m, .2, .012, (.2, .78, .08), "C_" + STEEL, seg=18, minor=5)
    bar(m, (.36, .78, .08), (.36, .18, .2), .01, "C_" + STEEL, 6)
    # Caddy with spray bottles, a roll of towels and gloves.
    box(m, (.3, .12, .16), (.18, 1.12, .2), "C_2E86DE", .02)
    for i, c in enumerate(("27AE60", "D74A3C", "3E8FD6")):
        lathe(m, [(0, 0), (.035, 0), (.035, .14), (.02, .18), (.01, .22), (0, .22)], (.08 + i * .1, 1.18, .2), "C_" + c, 10)
        box(m, (.02, .03, .05), (.08 + i * .1, 1.42, .18), "C_" + WHITE, .006)
    cyl(m, .06, .14, (-.15, 1.16, .2), "C_" + WHITE, 14, .01, roll=90)
    box(m, (.14, .02, .1), (-.3, 1.05, .26), "C_F2C23F", .01, pitch=-20)
    # Dustpan and broom clipped to the side.
    box(m, (.2, .02, .2), (.42, .5, -.1), "C_D74A3C", .01, roll=90)
    bar(m, (.42, .3, .15), (.42, 1.45, .12), .012, "T_IK_WoodLight", 6)
    box(m, (.05, .18, .26), (.42, .28, .15), "C_" + WOODD, .02)
    rounded_panel(m, .34, .1, (0, .32, -.265), "C_1F9A8E", .02, .03)
    text_lite(m, "LIMPEZA", (0, .315, -.28), .055, "C_" + WHITE, .006)


@staff_model("staff-wetsign")
def staff_wetsign(m):
    for s in (-1, 1):
        k = NS["Local"](m, (0, 0, s * .12), 0, -s * 12)
        box(k, (.34, .66, .025), (0, .33, 0), "C_F2C23F", .012)
        box(k, (.3, .1, .03), (0, .56, 0), "C_2A2A2A", .008)
        prism(k, [(-.08, 0), (.08, 0), (0, .14)], .032, (0, .32, 0), "C_2A2A2A")
        text_lite(k, "PISO", (0, .18, .02 * s), .05, "C_2A2A2A", .006, 0 if s < 0 else 180)
        text_lite(k, "MOLHADO", (0, .12, .02 * s), .045, "C_2A2A2A", .006, 0 if s < 0 else 180)
    box(m, (.36, .05, .06), (0, .66, 0), "C_F2C23F", .02)


@staff_model("staff-ladder")
def staff_ladder(m):
    for s in (-1, 1):
        bar(m, (s * .2, 0, -.18), (s * .16, 1.3, 0), .02, "C_C9D2D6", 8)
        bar(m, (s * .2, 0, .26), (s * .16, 1.3, .04), .018, "C_C9D2D6", 8)
        box(m, (.06, .03, .05), (s * .2, .015, -.18), "C_" + DARK, .01)
        box(m, (.06, .03, .05), (s * .2, .015, .26), "C_" + DARK, .01)
    for i in range(4):
        y = .3 + i * .3
        z = -.18 + (y / 1.3) * .18
        box(m, (.34, .03, .12), (0, y, z), "T_IK_Diamond", .008)
    box(m, (.36, .05, .2), (0, 1.33, .02), "C_D74A3C", .015)
    bar(m, (-.16, .7, .15), (.16, .7, .15), .006, "C_" + DARK, 5)


@staff_model("staff-pallet")
def staff_pallet(m):
    for x in (-.5, 0, .5):
        box(m, (.1, .1, 1.0), (x, .05, 0), "T_IK_WoodLight", .01)
    for z in (-.45, -.15, .15, .45):
        box(m, (1.2, .025, .14), (0, .11, z), "T_IK_WoodLight", .006)
    boxes = [(-.3, -.25, .5, .3), (.3, -.25, .5, .3), (-.3, .25, .5, .3), (.3, .25, .5, .3), (-.3, -.25, .5, .3), (.3, .25, .5, .3), (0, 0, .5, .3)]
    for i, (x, z, w, h) in enumerate(boxes[:4]):
        box(m, (w, h, .46), (x, .125 + h / 2, z), "T_IK_Cardboard", .012)
    for i, (x, z) in enumerate(((-.28, -.22), (.3, .2), (.02, -.2))):
        box(m, (.46, .28, .42), (x, .43 + .14, z), "T_IK_Cardboard", .012, yaw=8 * i)
    # Top: a produce crate with lettuces.
    box(m, (.5, .03, .36), (0, .72, .15), "T_IK_Wicker", .01)
    for sx in (-1, 1):
        box(m, (.025, .2, .36), (sx * .24, .81, .15), "T_IK_Wicker", .006)
    for sz in (-1, 1):
        box(m, (.5, .2, .025), (0, .81, .15 + sz * .17), "T_IK_Wicker", .006)
    for i in range(6):
        ball(m, (-.15 + (i % 3) * .15, .88, .07 + (i // 3) * .16), (.15, .12, .15), "C_" + LEAF if i % 2 else "C_" + LEAFD, 10, 6)



def puddle_points(n, r, seed, squash=.7):
    import random
    rng = random.Random(seed)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (.75 + .5 * rng.random())
        pts.append((math.cos(a) * rr, math.sin(a) * rr * squash))
    return pts


@staff_model("staff-puddle")
def staff_puddle(m):
    prism(m, puddle_points(18, .45, 3), .012, (0, .006, 0), "C_9FD3E8", pitch=90)
    prism(m, puddle_points(14, .32, 5), .014, (.02, .008, .02), "C_C5E8F3", pitch=90)
    for i, (x, z, r) in enumerate(((.55, .2, .08), (-.5, -.15, .06), (.3, -.35, .05), (-.25, .38, .05))):
        prism(m, puddle_points(9, r, 11 + i), .01, (x, .005, z), "C_9FD3E8", pitch=90)
    # Tipped bottle and its cap.
    lathe(m, [(0, 0), (.045, 0), (.045, .18), (.02, .25), (.02, .29), (0, .29)], (-.3, .045, .05), "C_27AE60", 14, roll=90)
    cyl(m, .024, .03, (-.02, .045, .05), "C_D74A3C", 10, 0, roll=90)
    box(m, (.1, .005, .06), (-.18, .09, .05), "C_" + WHITE, .002, roll=90)


@staff_model("staff-dirt-a")
def staff_dirt_a(m):
    prism(m, puddle_points(16, .38, 21, .5), .01, (.1, .005, .1), "C_7A5A3A", pitch=90)
    prism(m, puddle_points(12, .22, 22, .6), .012, (.05, .007, .08), "C_5E4028", pitch=90)
    for i in range(6):
        x = -.5 + i * .18
        z = -.2 + (i % 2) * .16
        k = NS["Local"](m, (x, .007, z), 70)
        prism(k, [(math.cos(a) * .06, math.sin(a) * .11) for a in [j * math.pi / 7 for j in range(14)]], .006, (0, 0, 0), "C_6A4A30", pitch=90)
        prism(k, [(math.cos(a) * .045, math.sin(a) * .05) for a in [j * math.pi / 6 for j in range(12)]], .006, (0, 0, -.15), "C_6A4A30", pitch=90)
    for i in range(10):
        ball(m, (-.3 + (i * .137) % .7, .012, -.25 + (i * .23) % .5), (.03, .015, .025), "C_5E4028", 6, 4)


@staff_model("staff-dirt-b")
def staff_dirt_b(m):
    for i, (x, z, s) in enumerate(((-.2, .1, .1), (.25, -.12, .08), (.05, .3, .07))):
        ball(m, (x, s / 2, z), (s, s * .8, s), "C_" + WHITE if i != 1 else "C_F4EFE4", 8, 6)
        for k in range(4):
            box(m, (s * .5, .004, s * .2), (x + math.cos(k) * s * .3, s * .6, z + math.sin(k) * s * .3), "C_C9D2D6", .001, yaw=k * 40)
    box(m, (.16, .01, .08), (.35, .006, .2), "C_D74A3C", .004, yaw=25)
    box(m, (.16, .012, .02), (.35, .012, .2), "C_F2C23F", .003, yaw=25)
    lathe(m, [(0, 0), (.035, 0), (.045, .11), (.047, .115)], (-.35, .045, -.22), "C_" + WHITE, 12, roll=80, cap=False)
    torus(m, .045, .005, (-.24, .045, -.22), "C_D74A3C", roll=80, seg=12, minor=4)
    prism(m, puddle_points(12, .1, 31), .005, (-.12, .003, -.25), "C_B07A40", pitch=90)
    for i in range(16):
        ball(m, (-.4 + (i * .173) % .8, .008, -.3 + (i * .29) % .6), (.025, .012, .02), "C_D9A04E", 5, 3)


@staff_model("staff-path")
def staff_path(m):
    box(m, (1.0, .02, 1.0), (0, .01, 0), "T_IK_Paver", .002)
    box(m, (1.0, .022, .08), (0, .011, .6), "C_F2C23F", .002)
    box(m, (1.0, .022, .08), (0, .011, .8), "C_1D2B4F", .002)


def build_staff_props(names=None, thumbs=False):
    global OUT
    saved = OUT
    OUT = STAFF_OUT
    NS["OUT"] = STAFF_OUT
    done = []
    try:
        for name in names or list(STAFF_BUILDERS):
            m = Model(name)
            STAFF_BUILDERS[name](m)
            export(m)
            done.append(name)
    finally:
        OUT = saved
        NS["OUT"] = saved
    return done


if __name__ == "__main__":
    print(build_staff_props())
