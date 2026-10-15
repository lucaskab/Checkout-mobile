"""backdrop_art.py -- the store corner behind the REPOR fixtures: a cream plaster wall with a soft teal
beadboard wainscot and a wooden baseboard, a light tiled floor in perspective, warm window light.
Dressing (v3): a picture rail, a round clock, a framed fruit print and a blank chalkboard on the right, two
pendant lamps from the top edge, a potted plant at the far left, a floor shadow along the skirting. The
left ~60 % (fixtures) and the lower right (stock cart) stay calm. No letters anywhere (multilingual game).
Writes render/restock_backdrop.png (2400 x 1000, opaque); the game copy is the 1920 x 800 jpg.
    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\restock\\backdrop_art.py",encoding="utf-8").read())
    NO_AUTORUN = True before the exec skips the render; render_backdrop(out_dir) renders elsewhere (previews).
"""
exec(open(r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\restock\restock_art.py", encoding="utf-8").read())

def plaster_mat():
    """Cream plaster with a faint mottle and bump so the big wall is not a flat fill."""
    m = mat("bd_plaster", (0.78, 0.60, 0.40, 1), rough=.9); nt = m.node_tree
    if nt.nodes.get("mottle"): return m
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.name = "mottle"
    nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 4; nz.inputs["Roughness"].default_value = .6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (0.72, 0.55, 0.36, 1); ramp.color_ramp.elements[1].color = (0.82, 0.64, 0.44, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = .08
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 40; nz2.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"]); nt.links.new(nz2.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def shade_mat(name, strength, y0, y1):
    """Transparent (at y0) to dark (at y1) along Y (box() bakes world coords), for the soft shadow at the foot of the wall."""
    key = "shade_" + name
    if key in _M and _M[key].name in bpy.data.materials: return _M[key]
    m = bpy.data.materials.get("RA_" + key) or bpy.data.materials.new("RA_" + key); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.05, 0.04, 0.03, 1); b.inputs["Roughness"].default_value = 1
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    rng = nt.nodes.new("ShaderNodeMapRange"); rng.inputs["From Min"].default_value = y0; rng.inputs["From Max"].default_value = y1
    rng.inputs["To Min"].default_value = 0; rng.inputs["To Max"].default_value = strength
    nt.links.new(sep.outputs["Y"], rng.inputs["Value"]); nt.links.new(rng.outputs["Result"], b.inputs["Alpha"])
    if hasattr(m, "surface_render_method"): m.surface_render_method = 'BLENDED'
    _M[key] = m; return m

def picture_frame(nm, x, z, w, h, yw, frame_m, back_m, depth=.03):
    """A framed picture hanging flat on the wall (wall plane at y = yw); returns the inner rect (x0, x1, z0, z1)."""
    t = .035
    box(nm + "_back", (w, .012, h), (x, yw - depth + .006, z), back_m, bevel=.002)
    box(nm + "_t", (w + t, depth, t), (x, yw - depth / 2, z + h / 2), frame_m, bevel=.008)
    box(nm + "_b", (w + t, depth, t), (x, yw - depth / 2, z - h / 2), frame_m, bevel=.008)
    box(nm + "_l", (t, depth, h), (x - w / 2, yw - depth / 2, z), frame_m, bevel=.008)
    box(nm + "_r", (t, depth, h), (x + w / 2, yw - depth / 2, z), frame_m, bevel=.008)
    return (x - w / 2 + t / 2, x + w / 2 - t / 2, z - h / 2 + t / 2, z + h / 2 - t / 2)

def sphere(nm, r, loc, m, scale=(1, 1, 1)):
    """A (squashed) sphere; unlike box() it keeps its origin at loc, so it can be rotated in place."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(0, 0, 0), segments=24, ring_count=12); o = bpy.context.object
    o.name = nm; o.scale = scale; bpy.ops.object.transform_apply(scale=True); o.location = loc; o.data.materials.append(m); o["layer"] = "back"
    for p in o.data.polygons: p.use_smooth = True
    return o

def build_backdrop():
    clear()
    plaster = plaster_mat()
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
    # soft shadow along the skirting (a gradient strip on the tiles, dark against the wall)
    box("skirt_shade", (W, .75, .001), (0, yw - .415, .0012), shade_mat("skirt", .45, yw - .79, yw - .06), bevel=0)
    # --- dressing ---------------------------------------------------------------------------------
    dark_wood = mat("bd_dwood", (0.40, 0.23, 0.10, 1), rough=.5); frame_w = mat("bd_frame", (0.62, 0.40, 0.18, 1), rough=.5)
    paper = mat("bd_paper", (0.97, 0.94, 0.86, 1), rough=.8); slate = mat("bd_slate", (0.09, 0.15, 0.13, 1), rough=.85)
    teal_m = mat("bd_teal_metal", TEAL, rough=.35, metal=.3); brass = mat("bd_brass", (0.85, 0.66, 0.30, 1), rough=.3, metal=.8)
    bulb = mat("bd_bulb", (1, .92, .75, 1), emit=6.0); cord = mat("bd_cord", (0.10, 0.10, 0.10, 1), rough=.7)
    # picture rail: a thin wooden moulding across the whole wall, under the top edge
    box("pic_rail", (W, .035, .035), (0, yw - .018, 1.56), rail, bevel=.01)
    # round wall clock (no numbers): cream face, brass ring, two hands
    cx, cz, cr = .75, 1.33, .16
    cyl("clock_ring", cr, .04, (cx, yw - .02, cz), brass, rot=(rad(90), 0, 0), verts=48)
    cyl("clock_face", cr - .018, .012, (cx, yw - .044, cz), paper, rot=(rad(90), 0, 0), verts=48)
    for k in range(12):
        a = k * math.pi / 6
        o = box(f"tick{k}", (.012 if k % 3 else .02, .006, .022 if k % 3 else .034), (0, 0, cr - .045), dark_wood, bevel=.002)   # built on the origin, then turned
        o.location = (cx, yw - .052, cz); o.rotation_euler = (0, a, 0)
    h1 = box("hand_h", (.014, .006, .075), (0, 0, .03), dark_wood, bevel=.003); h1.location = (cx, yw - .058, cz); h1.rotation_euler = (0, rad(-50), 0)
    h2 = box("hand_m", (.010, .006, .11), (0, 0, .048), dark_wood, bevel=.003); h2.location = (cx, yw - .062, cz); h2.rotation_euler = (0, rad(160), 0)
    cyl("clock_pin", .012, .01, (cx, yw - .066, cz), brass, rot=(rad(90), 0, 0), verts=16)
    # framed fruit print: three cartoon fruits on cream paper
    x0, x1, z0, z1 = picture_frame("print", 1.62, 1.20, .50, .40, yw, frame_w, paper)
    fx, fz = (x0 + x1) / 2, (z0 + z1) / 2
    sphere("fruit_apple", .075, (fx - .13, yw - .045, fz - .03), mat("bd_apple", (0.86, 0.22, 0.18, 1), rough=.4))
    sphere("fruit_orange", .07, (fx + .02, yw - .045, fz - .04), mat("bd_orange", ORANGE, rough=.5))
    sphere("fruit_pear", .062, (fx + .16, yw - .045, fz - .045), mat("bd_pear", (0.72, 0.78, 0.30, 1), rough=.5), scale=(1, 1, 1.25))
    sphere("fruit_pear_top", .04, (fx + .16, yw - .045, fz + .05), mat("bd_pear", (0.72, 0.78, 0.30, 1), rough=.5))
    leaf = mat("bd_leaf", (0.30, 0.55, 0.25, 1), rough=.6)
    for nm, x, z in (("leaf_a", fx - .10, fz + .05), ("leaf_o", fx + .05, fz + .035)):
        sphere(nm, .03, (x, yw - .045, z), leaf, scale=(1.6, .3, .8)).rotation_euler = (0, rad(30), 0)
    box("print_shelf", (x1 - x0, .03, .012), (fx, yw - .035, z0 + .01), frame_w, bevel=.003)   # ledge the fruits sit on
    # blank chalkboard with a chalk tray (no writing)
    x0, x1, z0, z1 = picture_frame("board", 2.22, 1.17, .56, .44, yw, dark_wood, slate, depth=.035)
    box("chalk_tray", (x1 - x0, .05, .02), ((x0 + x1) / 2, yw - .05, z0 - .01), dark_wood, bevel=.005)
    cyl("chalk", .008, .06, ((x0 + x1) / 2 - .12, yw - .055, z0 + .003), paper, rot=(0, rad(90), 0), verts=10)
    # two pendant lamps hanging from the top edge (one at the far left, one above the right band)
    for nm, x in (("lamp_a", -2.15), ("lamp_b", 1.22)):
        cyl(nm + "_cord", .006, 1.2, (x, .25, 2.1), cord, verts=8)
        bpy.ops.mesh.primitive_cone_add(radius1=.17, radius2=.04, depth=.17, location=(x, .25, 1.50), vertices=32); o = bpy.context.object
        o.name = nm + "_shade"; o.data.materials.append(teal_m); o["layer"] = "back"
        for p in o.data.polygons: p.use_smooth = abs(p.normal.z) < .9
        md = o.modifiers.new("b", 'BEVEL'); md.width = .012; md.segments = 3
        cyl(nm + "_rim", .17, .012, (x, .25, 1.42), brass, verts=32)
        sphere(nm + "_bulb", .045, (x, .25, 1.41), bulb)
    # potted plant at the far left edge, under the left lamp: terracotta pot, trunk, a round cartoon crown
    px, py = -2.3, .72
    pot = mat("bd_pot", (0.72, 0.36, 0.20, 1), rough=.7)
    bpy.ops.mesh.primitive_cone_add(radius1=.10, radius2=.13, depth=.24, location=(px, py, .13), vertices=32); o = bpy.context.object
    o.name = "pot"; o.data.materials.append(pot); o["layer"] = "back"
    for p in o.data.polygons: p.use_smooth = abs(p.normal.z) < .9
    cyl("pot_rim", .14, .04, (px, py, .26), pot, verts=32); cyl("pot_soil", .12, .02, (px, py, .275), mat("bd_soil", (0.30, 0.20, 0.12, 1), rough=1), verts=24)
    leaf_a = mat("bd_leaf_a", (0.18, 0.42, 0.20, 1), rough=.6); leaf_b = mat("bd_leaf_b", (0.26, 0.52, 0.24, 1), rough=.6)
    cyl("trunk", .02, .40, (px, py, .45), dark_wood, verts=10)
    for nm, dx, dy, dz, r, m in (("crown0", 0, 0, .80, .20, leaf_a), ("crown1", -.13, .04, .70, .14, leaf_b), ("crown2", .14, -.02, .72, .15, leaf_b), ("crown3", .03, -.09, .92, .13, leaf_b), ("crown4", -.08, .08, .90, .11, leaf_a)):
        sphere(nm, r, (px + dx, py + dy, dz), m, scale=(1, .8, 1))
    return dict(target=(0, yw - .9, .8), pitch=14, dist=5.0, lens=40, size=2.4)

def render_backdrop(out_dir=None):
    out = out_dir or OUT; os.makedirs(out, exist_ok=True)
    sc = scene(); v = build_backdrop()
    camera(v["target"], v["pitch"], v["dist"], v["lens"]); light_rig(v["target"], v["size"])
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1000; sc.render.film_transparent = False
    _show(["back", "front"]); sc.render.filepath = os.path.join(out, "restock_backdrop.png"); bpy.ops.render.render(write_still=True)
    sc.render.film_transparent = True; sc.render.resolution_x, sc.render.resolution_y = RES
    return sc.render.filepath

if not globals().get("NO_AUTORUN"): render_backdrop()
