"""cart_art.py -- the REPOR stock cart and its cardboard boxes, rendered with the same look as the fixtures.
Uses the helpers of restock_art.py. Writes into render/:
  restock_cart.png              platform trolley (teal frame, rubber deck, handle on the right)
  restock_box_closed.png        closed box without the tape
  restock_box_tape.png          the tape strip alone (the game splits it in two when it is cut)
  restock_box_open.png          open box, flaps out
  restock_cart.json             deck quad (normalised, origin bottom-left), box anchor/label/tape/mouth points
All images share one camera, so pixel scales match (a box image pasted on the cart keeps its size).
    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\restock\\cart_art.py",encoding="utf-8").read())
"""
exec(open(r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\restock\restock_art.py", encoding="utf-8").read())

CARD = (0.52, 0.29, 0.11, 1); CARD_D = (0.38, 0.20, 0.07, 1); CARD_IN = (0.30, 0.16, 0.06, 1)
TAPE = (0.80, 0.56, 0.22, 1); PAPER = (0.97, 0.95, 0.88, 1)
BW, BD, BH = .44, .34, .30          # box size (m)
DECK_Z = .30
FILL_Z = .13      # height of the units' floor inside the open box (the box is full of stock)

def build_cart():
    clear()
    frame = mat("cart_frame", TEAL, rough=.35, metal=.6); deck = mat("cart_deck", (0.20, 0.22, 0.23, 1), rough=.85)
    rib = mat("cart_rib", (0.28, 0.30, 0.31, 1), rough=.8); rubber = mat("rubber", (0.05, 0.05, 0.06, 1), rough=.7)
    hub = mat("hub", (0.85, 0.86, 0.88, 1), rough=.25, metal=1); grip = mat("grip", ORANGE, rough=.6)
    W, D = 1.40, .66
    box("deck_base", (W, D, .06), (0, D / 2, DECK_Z - .03), frame, bevel=.02, layer="cart")
    box("deck_mat", (W - .06, D - .06, .012), (0, D / 2, DECK_Z + .002), deck, bevel=.004, layer="cart")
    for k in range(9):
        box(f"rib{k}", (W - .12, .012, .006), (0, .07 + k * (D - .14) / 8, DECK_Z + .01), rib, bevel=.002, layer="cart")
    box("bumper", (W + .02, .03, .07), (0, -.005, DECK_Z - .03), mat("bumper", (0.12, 0.13, 0.14, 1), rough=.7), bevel=.015, layer="cart")
    # handle: a U tube at the right end
    for y in (.06, D - .06):
        cyl(f"post{y:.2f}", .022, .78, (W / 2 - .04, y, DECK_Z + .39), frame, layer="cart")
    cyl("bar", .026, D - .06, (W / 2 - .04, D / 2, DECK_Z + .78), grip, rot=(rad(90), 0, 0), layer="cart")
    # casters
    for x in (-W / 2 + .12, W / 2 - .14):
        for y in (.10, D - .10):
            box(f"fork{x:.1f}{y:.1f}", (.05, .07, .10), (x, y, DECK_Z - .10), hub, bevel=.01, layer="cart")
            cyl(f"wheel{x:.1f}{y:.1f}", .085, .045, (x, y, .085), rubber, rot=(0, rad(90), 0), layer="cart")
            cyl(f"cap{x:.1f}{y:.1f}", .04, .05, (x, y, .085), hub, rot=(0, rad(90), 0), layer="cart")
    return dict(W=W, D=D)

def build_box(open_box, x=0, y=.33):
    """A cardboard box standing on the deck centre. Closed: top flaps flat + tape (own layer). Open: flaps out."""
    card = mat("card", CARD, rough=.85); card_d = mat("card_d", CARD_D, rough=.85); inner = mat("card_in", CARD_IN, rough=.9)
    tape = mat("tape", TAPE, rough=.35); paper = mat("paper", PAPER, rough=.7)
    z0 = DECK_Z + .008; t = .008
    lay = "open" if open_box else "closed"
    lay_f = "open_front" if open_box else "closed"     # in front of the units that stand inside the open box
    box("b_front", (BW, t, BH), (x, y - BD / 2, z0 + BH / 2), card, bevel=.004, layer=lay_f)
    box("b_back", (BW, t, BH), (x, y + BD / 2, z0 + BH / 2), card_d, bevel=.004, layer=lay)
    box("b_l", (t, BD, BH), (x - BW / 2, y, z0 + BH / 2), card_d, bevel=.004, layer=lay)
    box("b_r", (t, BD, BH), (x + BW / 2, y, z0 + BH / 2), card, bevel=.004, layer=lay)
    box("b_floor", (BW, BD, t), (x, y, z0 + .03), inner, bevel=0, layer=lay)
    # a printed label on the front (the game puts the product icon on it)
    box("label", (BW * .52, .004, BH * .46), (x, y - BD / 2 - .006, z0 + BH * .5), paper, bevel=.003, layer=lay_f)
    box("arrow", (.05, .003, .012), (x + BW * .36, y - BD / 2 - .006, z0 + BH * .82), card_d, bevel=0, layer=lay_f)
    if not open_box:
        box("b_top", (BW, BD, t), (x, y, z0 + BH), card, bevel=.004, layer=lay)
        box("seam", (BW, .004, .002), (x, y, z0 + BH + .005), card_d, bevel=0, layer=lay)
        box("tape_top", (BW + .006, .075, .004), (x, y, z0 + BH + .007), tape, bevel=.001, layer="tape")
        box("tape_front", (.075, .004, .07), (x, y - BD / 2 - .005, z0 + BH - .035), tape, bevel=.001, layer="tape")
    else:
        # four flaps folded outward around the mouth. box() bakes the location into the mesh (origin at the
        # world origin), so each flap is built standing on the origin and then moved to its hinge.
        def flap(nm, size, hinge, rot, layer=lay):
            o = box(nm, size, (0, 0, size[2] / 2), card, bevel=.003, layer=layer); o.location = hinge; o.rotation_euler = rot
        h = .15; zt = z0 + BH
        flap("f_front", (BW - .01, t, h * .85), (x, y - BD / 2, zt), (rad(100), 0, 0), lay_f)
        flap("f_back", (BW - .01, t, h * .85), (x, y + BD / 2, zt), (rad(-100), 0, 0))
        flap("f_l", (t, BD - .01, h), (x - BW / 2, y, zt), (0, rad(-105), 0))
        flap("f_r", (t, BD - .01, h), (x + BW / 2, y, zt), (0, rad(105), 0))
    return z0

def proj(p):
    sc = bpy.context.scene; v = world_to_camera_view(sc, sc.camera, Vector(p)); return [v.x, v.y]

def render_cart():
    os.makedirs(OUT, exist_ok=True)
    sc = scene(); c = build_cart()
    W, D = c["W"], c["D"]
    build_box(False); build_box(True)       # both at the deck centre (hidden per pass)
    camera((0, D * .45, .55), 24, 3.2, 40)
    fit_camera(1.06); light_rig((0, D * .45, .5), 1.4)
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
    passes = [("restock_cart", ["cart"]), ("restock_box_closed", ["closed"]), ("restock_box_tape", ["tape"]), ("restock_box_open", ["open"]), ("restock_box_open_front", ["open_front"])]
    for name, show in passes:
        _show(show); sc.render.filepath = os.path.join(OUT, name + ".png"); bpy.ops.render.render(write_still=True)
    _show(["cart", "closed", "tape"])
    z0 = DECK_Z + .008; y = .33
    data = dict(size=[1400, 1000],
                deck=dict(fl=proj((-W / 2 + .08, .10, DECK_Z)), fr=proj((W / 2 - .16, .10, DECK_Z)), bl=proj((-W / 2 + .08, D - .10, DECK_Z)), br=proj((W / 2 - .16, D - .10, DECK_Z))),
                box=dict(anchor=proj((0, y, z0)), label=proj((0, y - BD / 2, z0 + BH * .5)), labelTop=proj((0, y - BD / 2, z0 + BH * .73)),
                         tapeL=proj((-BW / 2, y, z0 + BH)), tapeR=proj((BW / 2, y, z0 + BH)), mouth=proj((0, y, z0 + BH)),
                         # the units stand inside the open box on a pile of packing at FILL_Z (front-left, front-right, back-left, back-right)
                         fill=dict(fl=proj((-BW / 2 + .04, y - BD / 2 + .05, z0 + FILL_Z)), fr=proj((BW / 2 - .04, y - BD / 2 + .05, z0 + FILL_Z)),
                                   bl=proj((-BW / 2 + .04, y + BD / 2 - .04, z0 + FILL_Z)), br=proj((BW / 2 - .04, y + BD / 2 - .04, z0 + FILL_Z)),
                                   ppm=(proj((0, y, z0 + FILL_Z + 1))[1] - proj((0, y, z0 + FILL_Z))[1]) * 1000, height=.19),
                         width=BW, depth=BD, height=BH),
                ppmCenter=(proj((0, y, z0 + 1))[1] - proj((0, y, z0))[1]) * 1000)
    with open(os.path.join(OUT, "restock_cart.json"), "w") as f: json.dump(data, f, indent=1)
    return data

result_cart = render_cart()
