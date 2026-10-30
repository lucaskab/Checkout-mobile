"""Cold room as a wing of the depot (Supermercado stage), round 4 (exec'd into the fixture_tiers namespace).

Modelled in DEPOT-LOCAL space so the FBX can be parented to the depot directly (pivot = depot pivot). With the kit
export (export_tier: 180° turn, FBX -Z forward / Y up), Unity (x, y, z) = modelling (x, z, y), so here:
    modelling x = depot-local x (−x is world north, +x south, at the depot's yaw 90°)
    modelling y = depot-local z (+ is world EAST); the depot's east wall face is at y = 3.786
    modelling z = up
Measured in game (implementation agent): the usable strip is along the east wall, local x −3.932..6.4, outward
depth ≤ 1.49 m (local z 3.786..5.279) including handles and condensers, height < 5.28 m. No door outside: the
door is through the east wall from inside the depot. The game camera looks from the SOUTH-WEST, so the wing runs
to the south end of the strip (past the south-east corner, where its west and south faces are seen), the depot's
south face is clad at its east end, and the condensers stand on the roof near the east edge.
"""
WALL_Y = 3.786
ROOF_Z = 4.41
SOUTH_X = 3.872          # main box south face
ANNEX_Y = 1.80           # the south annex/canopy ends here (east edge)
CREAM_P = C(CREAM)
SEAM = C("D9CFB8")


def dw_panel_face(acc, x0, x1, z0, z1, plane, at, seam=1.0, t=.03):
    """Flat insulated cladding on a wall: cream panels with vertical seams, navy kick band with a gold line, frost
    at the foot. plane 'x' = a face on x = at (spanning y in x0..x1), plane 'y' = a face on y = at (spanning x)."""
    w = x1 - x0
    c = (x0 + x1) / 2
    h = z1 - z0
    if plane == "y":
        rbox(acc, (w, t, h), (c, at, z0 + h / 2), CREAM_P, .008, 1)
        n = max(1, int(w / seam))
        for k in range(1, n):
            rbox(acc, (.012, t + .006, h - .02), (x0 + k * w / n, at, z0 + h / 2), SEAM, 0, 1)
    else:
        rbox(acc, (t, w, h), (at, c, z0 + h / 2), CREAM_P, .008, 1)
        n = max(1, int(w / seam))
        for k in range(1, n):
            rbox(acc, (t + .006, .012, h - .02), (at, x0 + k * w / n, z0 + h / 2), SEAM, 0, 1)


def dw_condenser(acc, x, y, z, yaw=0):
    """Roof condensing unit on a low steel frame with two fans (top stays under the 5.28 m limit)."""
    for sx in (-1, 1):
        for sy in (-1, 1):
            rbox(acc, (.05, .05, .08), (x + sx * .55, y + sy * .25, z + .04), C(STEEL), .006, 1)
    rbox(acc, (1.2, .55, .04), (x, y, z + .1), C(STEEL), .006, 1)
    rbox(acc, (1.25, .6, .52), (x, y, z + .38), C(NAVY), .04, 3)
    rbox(acc, (1.26, .605, .02), (x, y, z + .2), C(GOLD), .004, 1)
    top = z + .64
    for k in range(2):
        fx = x - .3 + k * .6
        lathe(acc, [(0, 0), (.25, 0), (.25, .02), (0, .02)], (fx, y, top), C("2A2E36"), 18, 0)
        for j in range(6):
            a = j * math.pi / 3
            rbox(acc, (.2, .05, .01), (fx + .1 * math.cos(a), y + .1 * math.sin(a), top + .015), C(STEEL), .004, 1, rot=(0, 15, math.degrees(a)))
        lathe(acc, [(.25, 0), (.26, .03)], (fx, y, top), C(CHROME), 18, 0, cap_top=False, cap_bottom=False)
        for j in range(4):
            lathe(acc, [(.06 + j * .055, .03), (.062 + j * .055, .032)], (fx, y, top), C(CHROME), 16, 0, cap_top=False, cap_bottom=False)


def dw_pipes(acc, x, y_from, z_roof, z_to, y_to):
    for k in range(2):
        xx = x + k * .09
        tube(acc, [(xx, y_from, z_roof + .25), (xx, WALL_Y - .05, z_roof + .25), (xx, WALL_Y + .06, z_roof + .1),
                   (xx, WALL_Y + .06, z_to + .05), (xx, y_to, z_to + .05)], .028 if k else .02, C(WHITE) if k else C("C87533"), 8)


def depotwing(acc, tier):
    """T2: a 4 m wing at the south end of the east wall, 1 roof condenser, the south face clad to the wing height.
    T3: an 8 m wing, 2 condensers, the east wall clad above the wing to the parapet and the whole east end of the
    south face clad to the roof, a snowflake pictogram and status lights."""
    x1 = 5.4                                          # south end of the wing (≤ 6.4: clear of the truck bay)
    L = 4.0 if tier == 2 else 8.0
    x0 = x1 - L
    D = 1.42                                          # outward depth (≤ 1.49 with everything)
    H = 3.2 if tier == 2 else 3.4
    y0, y1 = WALL_Y, WALL_Y + D
    # body (closed box: the part past the corner is free-standing, its west face is seen from the camera)
    rbox(acc, (L, D, H), ((x0 + x1) / 2, (y0 + y1) / 2, H / 2), CREAM_P, .03, 2)
    n = int(L / 1.0)
    for k in range(1, n):
        xx = x0 + k * L / n
        rbox(acc, (.014, .01, H - .3), (xx, y1 + .002, H / 2 + .1), SEAM, 0, 1)
        if xx > SOUTH_X:
            rbox(acc, (.014, .01, H - .3), (xx, y0 - .002, H / 2 + .1), SEAM, 0, 1)
    for k in range(1, 3):
        rbox(acc, (.01, .014, H - .3), (x1 + .002, y0 + k * D / 3, H / 2 + .1), SEAM, 0, 1)
    # navy kick band, gold line, roof coping, corner guards
    rbox(acc, (L + .02, D + .02, .28), ((x0 + x1) / 2, (y0 + y1) / 2, .14), C(NAVY), .02, 2)
    rbox(acc, (L + .025, D + .025, .02), ((x0 + x1) / 2, (y0 + y1) / 2, .36), C(GOLD), .004, 1)
    rbox(acc, (L + .06, D + .06, .1), ((x0 + x1) / 2, (y0 + y1) / 2, H + .05), C(NAVY), .02, 2)
    rbox(acc, (L + .065, D + .065, .015), ((x0 + x1) / 2, (y0 + y1) / 2, H - .02), C(GOLD), .003, 1)
    for (cx, cy) in ((x1, y1), (x1, y0), (x0, y1)):
        rbox(acc, (.08, .08, H - .3), (cx, cy, (H - .3) / 2 + .3), C(NAVY), .015, 2)
    # frost at the foot (cold seals) and along the south end
    for k in range(int(L / .5)):
        blob(acc, (.2, .03, .04), (x0 + .25 + k * .5, y1 + .015, .3), C("EAF6FB"), 1, .3, k)
    for k in range(3):
        blob(acc, (.03, .2, .04), (x1 + .015, y0 + .25 + k * .45, .3), C("EAF6FB"), 1, .3, k)
    # south end: snowflake pictogram (no text), temperature display, status lights
    sx = x1 + .02
    cz, cy = H * .6, (y0 + y1) / 2
    for a in (0, 60, 120):
        rbox(acc, (.02, .5, .05), (sx, cy, cz), C(NAVY), .01, 1, rot=(a, 0, 0))
        for s_ in (-1, 1):
            r = math.radians(a)
            px_, pz = cy + s_ * .18 * math.cos(r), cz + s_ * .18 * math.sin(r)
            rbox(acc, (.02, .12, .035), (sx, px_, pz), C(NAVY), .008, 1, rot=(a + 45, 0, 0))
            rbox(acc, (.02, .12, .035), (sx, px_, pz), C(NAVY), .008, 1, rot=(a - 45, 0, 0))
    lathe(acc, [(0, 0), (.24, 0), (.24, .015), (0, .015)], (sx - .01, cy, cz), C(GOLD), 24, 0, rot=(0, 90, 0), cap_bottom=False)
    lathe(acc, [(0, 0), (.22, 0), (.22, .016), (0, .016)], (sx - .009, cy, cz), CREAM_P, 24, 0, rot=(0, 90, 0), cap_bottom=False)
    rbox(acc, (.05, .2, .12), (sx + .02, cy + .45, 1.6), C(INK), .015, 2)
    rbox(acc, (.006, .14, .05), (sx + .046, cy + .45, 1.61), "E_7BD3F7", 0, 1)
    for k, col in enumerate(("E_CFEFFF", "E_FF4A3A")):
        lathe(acc, [(0, 0), (.045, 0), (.04, .04), (0, .05)], (sx, cy - .45 + k * .14, H - .3), col, 10, 0, rot=(0, 90, 0))
    # pressure relief port on the east face
    for k in range(2 if tier == 3 else 1):
        px_ = x1 - 1.2 - k * 3.5
        rbox(acc, (.3, .03, .3), (px_, y1 + .015, 2.3), C(STEEL), .01, 2)
        lathe(acc, [(0, 0), (.08, 0), (.08, .025), (0, .025)], (px_, y1 + .03, 2.3), C(NAVY), 12, 0, rot=(-90, 0, 0))
    # cladding on the depot's south face, east end (thin, no new footprint), wrapping the corner
    clad_top = H if tier == 2 else ROOF_Z
    dw_panel_face(acc, ANNEX_Y + .05, WALL_Y, 0, clad_top, "x", SOUTH_X + .016, 1.0)
    rbox(acc, (.03, WALL_Y - ANNEX_Y - .05, .28), (SOUTH_X + .02, (ANNEX_Y + .05 + WALL_Y) / 2, .14), C(NAVY), .01, 1)
    rbox(acc, (.034, WALL_Y - ANNEX_Y - .05, .02), (SOUTH_X + .022, (ANNEX_Y + .05 + WALL_Y) / 2, .36), C(GOLD), .003, 1)
    rbox(acc, (.08, .08, clad_top), (SOUTH_X + .02, ANNEX_Y + .07, clad_top / 2), C(NAVY), .015, 2)
    if tier == 3:
        # the east wall above the wing, up to the parapet, as cold-room cladding too
        dw_panel_face(acc, x0, SOUTH_X, H + .1, ROOF_Z, "y", WALL_Y + .016, 1.0)
        rbox(acc, (SOUTH_X - x0, .03, .02), ((x0 + SOUTH_X) / 2, WALL_Y + .03, ROOF_Z - .1), C(GOLD), .003, 1)
    # condensers on the roof near the east edge, pipes over the parapet to the wing roof
    cds = [(3.0, 3.2)] if tier == 2 else [(3.0, 3.2), (-.2, 3.2)]
    for (cx, cy_) in cds:
        dw_condenser(acc, cx, cy_, ROOF_Z)
        dw_pipes(acc, cx - .55, cy_, ROOF_Z, H + .1, WALL_Y + .5)


TIERS["coldroom_depotwing"] = [("T1", "(sem ala)", 0, 0, 0), ("T2", "Câmara fria: ala do depósito", 4.0, 1.42, 3.2),
                               ("T3", "Câmara fria: ala do depósito grande", 8.0, 1.42, 3.4)]
DW_AT = Vector((0, 600, 0))


def depotwing_build(tier):
    c = coll("FT coldroom_depotwing T%d" % tier, coll("Fixture tiers"))
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    acc = Acc("coldroom_depotwing_T%d" % tier)
    depotwing(acc, tier)
    objs = acc.realize(c)
    tris = 0
    for o in objs:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    return objs, tris


def depotwing_shot(tier):
    """South-west game-camera check with the depot in clay."""
    c = coll("FT depotwing", coll("Fixture tiers"))
    dep = bpy.data.objects.get("DW depot")
    for t in (2, 3):
        cc = bpy.data.collections.get("FT coldroom_depotwing T%d" % t)
        if cc:
            for o in cc.objects:
                o.location = DW_AT
                o.hide_render = (t != tier)
    for o in bpy.context.scene.objects:
        if o.type in ("MESH", "EMPTY"):
            o.hide_render = True
    cc = bpy.data.collections.get("FT coldroom_depotwing T%d" % tier)
    for o in cc.objects:
        o.hide_render = False
    if dep:
        dep.hide_render = False
    acc = Acc("DW yard")
    yard = bpy.data.objects.get("DW yard")
    if not yard:
        rbox(acc, (24, 22, .02), (1, 0, -.012), C("B9B4AA"), 0, 1)
        for o in acc.realize(c):
            o.name = "DW yard"
            o.location = DW_AT
    bpy.data.objects["DW yard"].hide_render = False
    bpy.context.view_layer.update()
    camera(DW_AT + Vector((1.4, .8, 2.2)), (1.0, -1.0, 1.05), 24, 40)
    return render("coldroom_depotwing_T%d_gamecam" % tier, (1600, 1100))


def depotwing_export():
    """Writes ArtSource/fixture_tiers/export/coldroom_depotwing_T2.fbx and _T3.fbx (depot-local, pivot = depot pivot)."""
    rep = []
    for t in (2, 3):
        r = export_tier("coldroom_depotwing", t)
        rep.append(r)
    return rep
