"""backdrop_art.py -- the store corner behind the REPOR fixtures: a cream plaster wall with a soft teal
beadboard wainscot and a wooden baseboard, a light tiled floor in perspective, warm window light.
Writes render/restock_backdrop.png (2400 x 1000, opaque).
    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\restock\\backdrop_art.py",encoding="utf-8").read())
"""
exec(open(r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\restock\restock_art.py", encoding="utf-8").read())

def build_backdrop():
    clear()
    plaster = mat("bd_plaster", (0.78, 0.60, 0.40, 1), rough=.9)
    bead = mat("bd_bead", (0.12, 0.42, 0.40, 1), rough=.6); bead_d = mat("bd_bead_d", (0.09, 0.35, 0.33, 1), rough=.6)
    rail = mat("bd_rail", (0.55, 0.33, 0.15, 1), rough=.5); base = mat("bd_base", (0.36, 0.20, 0.09, 1), rough=.5)
    tile_a = mat("bd_tile_a", (0.72, 0.62, 0.50, 1), rough=.35); tile_b = mat("bd_tile_b", (0.58, 0.48, 0.37, 1), rough=.35)
    W = 9.0; yw = 1.0
    box("wall", (W, .1, 3.2), (0, yw + .05, 1.6), plaster, bevel=0)
    # wainscot: vertical beadboard planks up to 1.0 m, a wooden chair rail on top, a baseboard below
    n = 70
    for k in range(n):
        x = -W / 2 + (k + .5) * W / n
        box(f"bead{k}", (W / n - .012, .03, .75), (x, yw - .015, .4), bead if k % 2 else bead_d, bevel=.004)
    box("chair_rail", (W, .06, .06), (0, yw - .04, .8), rail, bevel=.015)
    box("baseboard", (W, .05, .12), (0, yw - .04, .06), base, bevel=.01)
    # floor: big checker tiles
    s = .5
    for i in range(-10, 10):
        for j in range(0, 12):
            box(f"t{i}_{j}", (s - .006, s - .006, .02), ((i + .5) * s, yw - (j + .5) * s, -.01), tile_a if (i + j) % 2 == 0 else tile_b, bevel=.003)
    box("grout", (W, 6, .01), (0, yw - 3, -.022), mat("bd_grout", (0.40, 0.34, 0.27, 1), rough=.6), bevel=0)
    return dict(target=(0, yw - .9, .8), pitch=14, dist=5.0, lens=40, size=2.4)

def render_backdrop():
    os.makedirs(OUT, exist_ok=True)
    sc = scene(); v = build_backdrop()
    camera(v["target"], v["pitch"], v["dist"], v["lens"]); light_rig(v["target"], v["size"])
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1000; sc.render.film_transparent = False
    _show(["back", "front"]); sc.render.filepath = os.path.join(OUT, "restock_backdrop.png"); bpy.ops.render.render(write_still=True)
    sc.render.film_transparent = True

render_backdrop()
