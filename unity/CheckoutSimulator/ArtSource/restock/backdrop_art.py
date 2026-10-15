"""backdrop_art.py -- the shop corner behind the REPOR fixtures (v4).
A real room in 3/4: the camera stands 1.75 m up, 6.5 m from the back wall with a 22 mm lens and a small yaw, so
the floor tiles recede, the back wall meets a side wall at the right (a corner with depth), the ceiling edge and the
pendant lamps are seen at a sensible scale (wainscot ~1 m, door 2.1 m, ceiling 3 m). Left ~60 % (fixtures) and the
lower right (stock cart) stay calm; the dressing lives in the right band and on the side wall:
  wooden shelving with stock boxes, jars and a crate of oranges, a snake plant on top; a framed painted still life;
  a round clock; a fire extinguisher; the stockroom swing door with a porthole and an exit light (icon only);
  a monstera in a glazed pot in the corner; a vintage orange poster on the side wall; a step stool; a mop bucket at
  the far left; two pendant lamps. Procedural wood grain, plaster, tiles. No letters anywhere.
Writes restock_backdrop.png (2400 x 1000, opaque) in render/ (or out_dir); the game copy is the 1920 x 800 jpg.
    exec(open(r"C:\\Checkout-mobile\\unity\\CheckoutSimulator\\ArtSource\\restock\\backdrop_art.py",encoding="utf-8").read())
    NO_AUTORUN = True before the exec skips the render; render_backdrop(out_dir) renders elsewhere (previews).
The two picture textures come from paint_prints.py (tex/still_life.png, tex/poster.png).
"""
exec(open(r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\restock\restock_art.py", encoding="utf-8").read())
import random
TEX = os.path.join(HERE, "tex")

# ---------------------------------------------------------------- materials
def plaster_mat(name="plaster", lo=(0.72, 0.60, 0.43), hi=(0.84, 0.72, 0.53)):
    m, nt = _new(name)
    if nt is None: return m
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = .9
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.0; nz.inputs["Detail"].default_value = 5; nz.inputs["Roughness"].default_value = .55
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (*lo, 1); ramp.color_ramp.elements[1].color = (*hi, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = .12
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 60; nz2.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"]); nt.links.new(nz2.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def tile_mat(name, rgb, rough=.28):
    """Glazed floor tile: per-object random tint (Object Info), a faint speckle, a glossy surface."""
    m, nt = _new("tile_" + name)
    if nt is None: return m
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Specular IOR Level"].default_value = .6
    oi = nt.nodes.new("ShaderNodeObjectInfo"); tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 25; nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = 'RGBA'; mix1.inputs[6].default_value = rgb; mix1.inputs[7].default_value = tuple(c * .86 for c in rgb[:3]) + (1,)
    rnd = nt.nodes.new("ShaderNodeMath"); rnd.operation = 'MULTIPLY'; rnd.inputs[1].default_value = .7
    nt.links.new(oi.outputs["Random"], rnd.inputs[0]); nt.links.new(rnd.outputs[0], mix1.inputs[0])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = 'RGBA'; mix2.inputs[7].default_value = tuple(c * .92 for c in rgb[:3]) + (1,)
    nt.links.new(mix1.outputs[2], mix2.inputs[6]); nt.links.new(nz.outputs["Fac"], mix2.inputs[0]); mix2.inputs[0].default_value = .5
    nt.links.new(mix2.outputs[2], b.inputs["Base Color"])
    return m

def image_mat(name, path, rough=.75):
    """A picture: image texture mapped on the front face through Generated coords (x -> u, z -> v)."""
    m, nt = _new("img_" + name)
    if nt is None: return m
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    cmb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(sep.outputs["X"], cmb.inputs[0]); nt.links.new(sep.outputs["Z"], cmb.inputs[1])
    img = nt.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(path, check_existing=True); img.extension = 'EXTEND'
    nt.links.new(cmb.outputs[0], img.inputs["Vector"]); nt.links.new(img.outputs["Color"], b.inputs["Base Color"])
    return m

def leaf_mat(name, base=(0.10, 0.34, 0.14), hi=(0.22, 0.52, 0.20), bands=False):
    """Plant green with a vein-ish noise; bands=True adds the dark cross stripes of a snake plant and a yellow edge."""
    m, nt = _new("leaf_" + name)
    if nt is None: return m
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = .45; b.inputs["Specular IOR Level"].default_value = .5
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 8; nz.inputs["Detail"].default_value = 4; nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (*base, 1); ramp.color_ramp.elements[1].color = (*hi, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    if bands:
        wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'; wv.inputs["Scale"].default_value = 9; wv.inputs["Distortion"].default_value = 4; wv.inputs["Detail"].default_value = 2
        nt.links.new(tc.outputs["Generated"], wv.inputs["Vector"])
        dark = nt.nodes.new("ShaderNodeMix"); dark.data_type = 'RGBA'; dark.inputs[7].default_value = (0.05, 0.18, 0.09, 1)
        nt.links.new(col, dark.inputs[6]); nt.links.new(wv.outputs["Fac"], dark.inputs[0])
        # yellow margin: Generated X near 0 or 1
        ex = nt.nodes.new("ShaderNodeMath"); ex.operation = 'SUBTRACT'; ex.inputs[1].default_value = .5; nt.links.new(sep.outputs["X"], ex.inputs[0])
        ab = nt.nodes.new("ShaderNodeMath"); ab.operation = 'ABSOLUTE'; nt.links.new(ex.outputs[0], ab.inputs[0])
        gt = nt.nodes.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = .40; nt.links.new(ab.outputs[0], gt.inputs[0])
        yel = nt.nodes.new("ShaderNodeMix"); yel.data_type = 'RGBA'; yel.inputs[7].default_value = (0.85, 0.78, 0.30, 1)
        nt.links.new(dark.outputs[2], yel.inputs[6]); nt.links.new(gt.outputs[0], yel.inputs[0]); col = yel.outputs[2]
    nt.links.new(col, b.inputs["Base Color"])
    return m

# ---------------------------------------------------------------- geometry helpers
def smooth(o, auto=True):
    for p in o.data.polygons: p.use_smooth = True
    return o

def sphere(nm, r, loc, m, scale=(1, 1, 1), layer="back"):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(0, 0, 0), segments=32, ring_count=16); o = bpy.context.object
    o.name = nm; o.scale = scale; bpy.ops.object.transform_apply(scale=True); o.location = loc; o.data.materials.append(m); o["layer"] = layer
    return smooth(o)

def cone(nm, r0, r1, h, loc, m, verts=32, layer="back", bevel=0):
    bpy.ops.mesh.primitive_cone_add(radius1=r0, radius2=r1, depth=h, location=loc, vertices=verts); o = bpy.context.object
    o.name = nm; o.data.materials.append(m); o["layer"] = layer
    for p in o.data.polygons: p.use_smooth = abs(p.normal.z) < .9
    if bevel:
        md = o.modifiers.new("b", 'BEVEL'); md.width = bevel; md.segments = 3; md.limit_method = 'ANGLE'
    return o

def mesh_obj(nm, verts, faces, m, loc=(0, 0, 0), layer="back"):
    me = bpy.data.meshes.new(nm); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(nm, me); bpy.context.scene.collection.objects.link(o); o.location = loc
    o.data.materials.append(m); o["layer"] = layer
    return smooth(o)

def monstera_leaf(nm, L, m, loc, yaw, pitch, roll=0, notches=(.30, .50, .68, .84)):
    """A split monstera leaf in the XZ plane, base at the origin, tip along +Z; then turned into place.
    Outline: a heart-ish width profile with deep notches cut toward the midrib."""
    n = 60; right = []; left = []
    for i in range(n + 1):
        t = i / n
        w = L * .48 * math.sin(math.pi * (t ** .75)) ** .9
        if t < .12: w *= .6 + .4 * (t / .12)
        cut = 1.0
        for tn in notches:
            cut = min(cut, 1 - .72 * math.exp(-((t - tn) / .035) ** 2))
        w *= max(cut, .14)
        right.append((w, 0, L * t)); left.append((-w, 0, L * t))
    verts = right + left[::-1][1:-1]
    o = mesh_obj(nm, verts, [list(range(len(verts)))], m, layer="back")
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(o.data); bm.free()
    md = o.modifiers.new("s", 'SOLIDIFY'); md.thickness = .004; md.offset = 0
    bd = o.modifiers.new("bend", 'SIMPLE_DEFORM'); bd.deform_method = 'BEND'; bd.angle = rad(-35); bd.deform_axis = 'X'
    o.rotation_euler = (rad(pitch), rad(roll), rad(yaw)); o.location = loc
    return o

def snake_blade(nm, L, wmax, m, loc, yaw, lean=.12, twist=35):
    """A sansevieria blade: a tapered strip, leaning outward and twisting toward the tip."""
    n = 14; verts = []; faces = []
    for i in range(n + 1):
        t = i / n; w = wmax * math.sin(math.pi * (.08 + .92 * t)) ** .55 if t < 1 else 0
        a = rad(twist) * t; dx, dy = math.cos(a) * w, math.sin(a) * w
        cx = lean * t * t
        verts += [(cx - dx, -dy, L * t), (cx + dx, dy, L * t)]
        if i: faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    o = mesh_obj(nm, verts, faces, m, layer="back")
    md = o.modifiers.new("s", 'SOLIDIFY'); md.thickness = .004; md.offset = 0
    o.rotation_euler = (0, 0, rad(yaw)); o.location = loc
    return o

def pot(nm, r_top, r_bot, h, loc, m, soil_m, rim=True):
    x, y, z = loc
    cone(nm, r_bot, r_top, h, (x, y, z + h / 2), m, bevel=.01)
    if rim: cyl(nm + "_rim", r_top * 1.06, h * .14, (x, y, z + h - h * .07), m, verts=32)
    cyl(nm + "_soil", r_top * .92, .02, (x, y, z + h - .02), soil_m, verts=32, flat_caps=True)

def picture(nm, x, z, w, h, yw, frame_m, img_m, depth=.035, t=.04, mat_m=None, mat_w=.0):
    """A framed picture on the back wall (face at y = yw): image plane, optional cream mat, four frame bars."""
    box(nm + "_img", (w, .006, h), (x, yw - depth + .004, z), img_m, bevel=0)
    if mat_m:
        box(nm + "_mat_t", (w + t, .008, mat_w), (x, yw - depth + .006, z + h / 2 - mat_w / 2), mat_m, bevel=0)
        box(nm + "_mat_b", (w + t, .008, mat_w), (x, yw - depth + .006, z - h / 2 + mat_w / 2), mat_m, bevel=0)
        box(nm + "_mat_l", (mat_w, .008, h), (x - w / 2 + mat_w / 2, yw - depth + .006, z), mat_m, bevel=0)
        box(nm + "_mat_r", (mat_w, .008, h), (x + w / 2 - mat_w / 2, yw - depth + .006, z), mat_m, bevel=0)
    box(nm + "_t", (w + t, depth, t), (x, yw - depth / 2, z + h / 2), frame_m, bevel=.008)
    box(nm + "_b", (w + t, depth, t), (x, yw - depth / 2, z - h / 2), frame_m, bevel=.008)
    box(nm + "_l", (t, depth, h), (x - w / 2, yw - depth / 2, z), frame_m, bevel=.008)
    box(nm + "_r", (t, depth, h), (x + w / 2, yw - depth / 2, z), frame_m, bevel=.008)

def picture_side(nm, y, z, w, h, xw, frame_m, img_m, depth=.03, t=.035):
    """Same, hanging on the side wall (face at x = xw, looking toward -x); the image is mirrored so it reads right."""
    o = box(nm + "_img", (w, .006, h), (0, 0, 0), img_m, bevel=0)   # built facing -y, then turned: Generated coords follow the object
    o.rotation_euler = (0, 0, rad(90)); o.location = (xw - depth + .004, y, z)
    box(nm + "_t", (depth, w + t, t), (xw - depth / 2, y, z + h / 2), frame_m, bevel=.008)
    box(nm + "_b", (depth, w + t, t), (xw - depth / 2, y, z - h / 2), frame_m, bevel=.008)
    box(nm + "_l", (depth, t, h), (xw - depth / 2, y - w / 2, z), frame_m, bevel=.008)
    box(nm + "_r", (depth, t, h), (xw - depth / 2, y + w / 2, z), frame_m, bevel=.008)

# ---------------------------------------------------------------- the room
def build_backdrop():
    clear()
    rnd = random.Random(11)
    H = 2.8           # ceiling
    XR = 4.3          # side wall (x)
    XL = -6.5         # left end of the back wall (out of frame)
    plaster = plaster_mat()
    ceil_m = mat("bd4_ceiling", (0.93, 0.92, 0.88, 1), rough=.9); cornice_m = mat("bd4_cornice", (0.97, 0.95, 0.90, 1), rough=.8)
    bead = mat("bd4_bead", (0.12, 0.44, 0.42, 1), rough=.55); bead_d = mat("bd4_bead_d", (0.09, 0.37, 0.35, 1), rough=.55)
    rail = wood_mat("rail", (0.72, 0.46, 0.22), (0.50, 0.29, 0.12), scale=2); base = wood_mat("base", (0.42, 0.25, 0.11), (0.30, 0.17, 0.07), scale=2)
    tile_a = tile_mat("a", (0.66, 0.56, 0.42, 1)); tile_b = tile_mat("b", (0.46, 0.37, 0.27, 1)); grout = mat("bd4_grout", (0.30, 0.25, 0.19, 1), rough=.8)
    # --- back wall, side wall, ceiling, cornice
    box("wall_back", (XR - XL + .2, .1, H), ((XR + XL) / 2, .05, H / 2), plaster, bevel=0)
    box("wall_side", (.1, 7.0, H), (XR + .05, -3.5, H / 2), plaster, bevel=0)
    box("ceiling", (XR - XL + .2, 7.2, .1), ((XR + XL) / 2, -3.5, H + .05), ceil_m, bevel=0)
    box("cornice_b", (XR - XL, .09, .11), ((XR + XL) / 2, -.045, H - .055), cornice_m, bevel=.02)
    box("cornice_s", (.09, 7.0, .11), (XR - .045, -3.5, H - .055), cornice_m, bevel=.02)
    # --- wainscot (beadboard planks to 0.95 m, chair rail, baseboard) on both walls
    pw = .11
    nb = int((XR - XL) / pw)
    for k in range(nb):
        x = XL + (k + .5) * pw
        box(f"bead{k}", (pw - .008, .025, .78), (x, -.0125, .11 + .39), bead if k % 2 else bead_d, bevel=.004)
    ns = int(7.0 / pw)
    for k in range(ns):
        y = -(k + .5) * pw
        box(f"sbead{k}", (.025, pw - .008, .78), (XR - .0125, y, .11 + .39), bead if k % 2 else bead_d, bevel=.004)
    box("rail_b", (XR - XL, .06, .06), ((XR + XL) / 2, -.03, .95), rail, bevel=.012)
    box("rail_s", (.06, 7.0, .06), (XR - .03, -3.5, .95), rail, bevel=.012)
    box("base_b", (XR - XL, .045, .12), ((XR + XL) / 2, -.022, .06), base, bevel=.008)
    box("base_s", (.045, 7.0, .12), (XR - .022, -3.5, .06), base, bevel=.008)
    # --- floor: 0.45 m glazed tiles, two tones, on a grout slab
    s = .45
    box("grout", (XR - XL + 1, 8, .02), ((XR + XL) / 2, -4, -.02), grout, bevel=0)
    for i in range(int((XR - XL) / s) + 1):
        for j in range(18):
            x = XL + (i + .5) * s; y = -(j + .5) * s
            if x > XR + s: continue
            box(f"t{i}_{j}", (s - .008, s - .008, .018), (x, y, -.01), tile_a if (i + j) % 2 == 0 else tile_b, bevel=.003)
    # ============================================================ dressing (right band x 2.2 .. 4.6)
    dark_wood = wood_mat("dark", (0.45, 0.27, 0.12), (0.30, 0.17, 0.07), scale=1.5); frame_w = wood_mat("frame", (0.70, 0.46, 0.22), (0.48, 0.29, 0.12), scale=3)
    shelf_w = wood_mat("shelf", (0.82, 0.60, 0.34), (0.62, 0.42, 0.20), scale=1.2)
    paper = mat("bd4_paper", (0.97, 0.94, 0.86, 1), rough=.8); cream_mat = mat("bd4_cream", CREAM, rough=.8)
    brass = mat("bd4_brass", (0.85, 0.66, 0.30, 1), rough=.3, metal=.8); chrome = mat("bd4_chrome", (.85, .86, .88, 1), rough=.2, metal=1)
    teal_m = mat("bd4_teal", TEAL, rough=.4); teal_metal = mat("bd4_teal_metal", (0.10, 0.40, 0.38, 1), rough=.35, metal=.3)
    bulb = mat("bd4_bulb", (1, .90, .70, 1), emit=12.0); cord = mat("bd4_cord", (0.08, 0.08, 0.08, 1), rough=.7)
    card = mat("bd4_card", (0.72, 0.52, 0.30, 1), rough=.85); card_d = mat("bd4_card_d", (0.62, 0.44, 0.24, 1), rough=.85); tape = mat("bd4_tape", (0.86, 0.72, 0.48, 1), rough=.5)
    glass = mat("bd4_glass", (.9, .95, .95, 1), rough=.05, alpha=.25); lid_m = mat("bd4_lid", (0.75, 0.30, 0.15, 1), rough=.5)
    soil = mat("bd4_soil", (0.22, 0.15, 0.09, 1), rough=1); terracotta = mat("bd4_terracotta", (0.78, 0.42, 0.24, 1), rough=.75)
    glaze = mat("bd4_glaze", (0.14, 0.48, 0.46, 1), rough=.18); red = mat("bd4_red", (0.75, 0.10, 0.08, 1), rough=.35); black = mat("bd4_black", (0.05, 0.05, 0.05, 1), rough=.5)
    green = mat("bd4_green", (0.06, 0.45, 0.22, 1), rough=.5); icon = mat("bd4_icon", (0.95, 1.0, 0.95, 1), emit=4.0)
    yellow = mat("bd4_yellow", (0.92, 0.72, 0.12, 1), rough=.5); grey = mat("bd4_grey", (0.55, 0.57, 0.58, 1), rough=.6)
    door_m = mat("bd4_door", (0.36, 0.56, 0.54, 1), rough=.45); door_fr = mat("bd4_door_frame", (0.30, 0.32, 0.33, 1), rough=.5); steel = mat("bd4_steel", (0.70, 0.72, 0.74, 1), rough=.3, metal=.9)
    # --- shelving unit with stock: x 2.30 .. 3.30, depth .42, 1.9 m
    sx0, sx1, sd, sh = 2.00, 2.95, .42, 1.90; sxc = (sx0 + sx1) / 2
    for x in (sx0 + .03, sx1 - .03):
        for y in (-.04, -sd + .04):
            box(f"shelf_post{x:.2f}{y:.2f}", (.06, .06, sh), (x, y, sh / 2), dark_wood, bevel=.01)
    box("shelf_backpanel", (sx1 - sx0 - .06, .02, sh - .1), (sxc, -.02, sh / 2 + .02), shelf_w, bevel=.004)
    for z in (.10, .60, 1.12, 1.58, sh):
        box(f"shelf_board{z:.2f}", (sx1 - sx0, sd, .035), (sxc, -sd / 2, z - .0175), shelf_w, bevel=.006)
    # bottom: two closed boxes side by side; 2nd: jars; 3rd: an orange crate + a small box; top: a tall box + snake plant on top of the unit
    def stock_box(nm, w, d, h, loc, m, stripe=None):
        box(nm, (w, d, h), loc, m, bevel=.008)
        box(nm + "_tape", (.045, d + .004, h * .12), (loc[0], loc[1], loc[2] + h / 2 - h * .06 + .002), tape, bevel=.002)
        box(nm + "_tape2", (w + .004, .045, h * .12), (loc[0], loc[1], loc[2] + h / 2 - h * .06 + .002), tape, bevel=.002)
        if stripe: box(nm + "_stripe", (w + .004, .004, h * .22), (loc[0], loc[1] - d / 2, loc[2] - h * .1), stripe, bevel=.001)
    stock_box("bx_a", .42, .34, .30, (sx0 + .26, -sd / 2, .10 + .15), card, teal_m)
    stock_box("bx_b", .40, .32, .26, (sx1 - .25, -sd / 2 - .02, .10 + .13), card_d)
    for k, (jr, jh, jc) in enumerate(((.07, .20, (0.80, 0.30, 0.12, 1)), (.07, .20, (0.45, 0.65, 0.20, 1)), (.065, .17, (0.85, 0.65, 0.20, 1)), (.075, .14, (0.55, 0.20, 0.35, 1)))):
        jx = sx0 + .14 + k * .24; jy = -sd / 2 - .02
        cyl(f"jar{k}", jr, jh, (jx, jy, .60 + jh / 2), glass, verts=24)
        cyl(f"jar{k}_in", jr - .012, jh - .03, (jx, jy, .60 + jh / 2 - .01), mat(f"bd4_jam{k}", jc, rough=.3), verts=24)
        cyl(f"jar{k}_lid", jr + .004, .022, (jx, jy, .60 + jh + .011), lid_m if k % 2 else brass, verts=24)
        cyl(f"jar{k}_label", jr + .003, jh * .35, (jx, jy, .60 + jh * .45), paper, verts=24)
    # orange crate on the 3rd shelf
    cx0, cx1, cy0, cy1, cz = sx0 + .06, sx0 + .50, -sd + .05, -.06, 1.12
    box("ocrate_floor", (cx1 - cx0, cy1 - cy0, .02), ((cx0 + cx1) / 2, (cy0 + cy1) / 2, cz + .01), shelf_w, bevel=.003)
    for nm, sz, loc in (("ocrate_b", (cx1 - cx0, .02, .10), ((cx0 + cx1) / 2, cy1, cz + .05)), ("ocrate_f", (cx1 - cx0, .02, .10), ((cx0 + cx1) / 2, cy0, cz + .05)),
                        ("ocrate_l", (.02, cy1 - cy0, .10), (cx0, (cy0 + cy1) / 2, cz + .05)), ("ocrate_r", (.02, cy1 - cy0, .10), (cx1, (cy0 + cy1) / 2, cz + .05))):
        box(nm, sz, loc, shelf_w, bevel=.004)
    orange_m = mat("bd4_orange", (0.95, 0.50, 0.08, 1), rough=.55)
    for k in range(10):
        sphere(f"orange{k}", .04, (cx0 + .06 + (k % 5) * .08 + rnd.uniform(-.008, .008), cy0 + .07 + (k // 5) * .13 + rnd.uniform(-.01, .01), cz + .02 + .04), orange_m)
    for k in range(4):
        sphere(f"orange_top{k}", .04, (cx0 + .10 + k * .08, cy0 + .135, cz + .02 + .105), orange_m)
    stock_box("bx_c", .30, .26, .22, (sx1 - .20, -sd / 2 - .04, cz + .11), card_d)
    stock_box("bx_d", .36, .30, .30, (sx0 + .22, -sd / 2 - .02, 1.58 + .15), card, teal_m)
    cyl("tin", .07, .12, (sx1 - .22, -sd / 2 - .04, 1.58 + .06), mat("bd4_tin", (0.80, 0.82, 0.84, 1), rough=.35, metal=.8), verts=24)
    cyl("tin_band", .072, .05, (sx1 - .22, -sd / 2 - .04, 1.58 + .06), mat("bd4_tin_band", ORANGE, rough=.5), verts=24)
    # snake plant on top of the unit (terracotta pot)
    px, py = sx0 + .20, -sd / 2 - .02
    pot("spot", .10, .075, .17, (px, py, sh), terracotta, soil)
    snake = leaf_mat("snake", (0.12, 0.40, 0.18), (0.25, 0.56, 0.24), bands=True)
    for k in range(9):
        a = k * 40 + rnd.uniform(-12, 12); L = rnd.uniform(.38, .62); r = rnd.uniform(.0, .05)
        snake_blade(f"snake{k}", L, .035, snake, (px + math.cos(rad(a)) * r, py + math.sin(rad(a)) * r, sh + .15), a + 90, lean=rnd.uniform(.08, .18), twist=rnd.uniform(20, 50))
    # --- framed still life above the shelving, round clock to the left of it
    still = image_mat("still", os.path.join(TEX, "still_life.png"))
    picture("print", 2.70, 2.38, .70, .56, 0, frame_w, still, mat_m=paper, mat_w=.035)
    cx, cz, cr = 1.68, 2.40, .17
    cyl("clock_ring", cr, .045, (cx, -.022, cz), brass, rot=(rad(90), 0, 0), verts=48)
    cyl("clock_face", cr - .02, .012, (cx, -.047, cz), paper, rot=(rad(90), 0, 0), verts=48)
    for k in range(12):
        o = box(f"tick{k}", (.012 if k % 3 else .02, .006, .022 if k % 3 else .036), (0, 0, cr - .05), black, bevel=.002)
        o.location = (cx, -.055, cz); o.rotation_euler = (0, k * math.pi / 6, 0)
    h1 = box("hand_h", (.014, .006, .08), (0, 0, .032), black, bevel=.003); h1.location = (cx, -.060, cz); h1.rotation_euler = (0, rad(-50), 0)
    h2 = box("hand_m", (.010, .006, .12), (0, 0, .052), black, bevel=.003); h2.location = (cx, -.064, cz); h2.rotation_euler = (0, rad(160), 0)
    cyl("clock_pin", .012, .01, (cx, -.068, cz), brass, rot=(rad(90), 0, 0), verts=16)
    cyl("clock_glass", cr - .01, .004, (cx, -.072, cz), glass, rot=(rad(90), 0, 0), verts=48)
    # --- fire extinguisher on a bracket between the shelving and the door
    ex, ez = 3.19, 1.05
    box("ext_bracket", (.06, .05, .08), (ex, -.025, ez + .25), black, bevel=.006)
    cyl("ext_body", .055, .42, (ex, -.085, ez), red, verts=32)
    sphere("ext_top", .055, (ex, -.085, ez + .21), red, scale=(1, 1, .6)); sphere("ext_bot", .055, (ex, -.085, ez - .21), red, scale=(1, 1, .5))
    cyl("ext_neck", .022, .05, (ex, -.085, ez + .26), chrome, verts=16)
    box("ext_lever", (.03, .09, .015), (ex, -.085 - .03, ez + .30), black, bevel=.004)
    box("ext_handle", (.03, .07, .015), (ex, -.085 + .02, ez + .285), black, bevel=.004)
    cyl("ext_gauge", .018, .012, (ex, -.085 - .045, ez + .24), paper, rot=(rad(90), 0, 0), verts=16)
    o = cyl("ext_hose", .008, .30, (0, 0, 0), black, verts=10); o.location = (ex + .045, -.11, ez + .12); o.rotation_euler = (rad(10), 0, 0)
    box("ext_label", (.09, .004, .10), (ex, -.142, ez + .03), paper, bevel=.002)
    box("ext_label_stripe", (.09, .002, .03), (ex, -.145, ez + .06), red, bevel=.001)
    # --- stockroom swing door x 3.60 .. 4.50, 2.10 m, with a porthole, a steel kick plate and an exit light above
    dx0, dx1, dh = 3.40, 4.22, 2.10; dxc = (dx0 + dx1) / 2
    box("door_frame_l", (.08, .10, dh + .05), (dx0 - .04, -.03, (dh + .05) / 2), door_fr, bevel=.008)
    box("door_frame_r", (.08, .10, dh + .05), (dx1 + .04, -.03, (dh + .05) / 2), door_fr, bevel=.008)
    box("door_frame_t", (dx1 - dx0 + .16, .10, .08), (dxc, -.03, dh + .04), door_fr, bevel=.008)
    box("door_leaf", (dx1 - dx0 - .01, .045, dh - .02), (dxc, -.03, dh / 2), door_m, bevel=.006)
    box("door_kick", (dx1 - dx0 - .06, .006, .32), (dxc, -.056, .20), steel, bevel=.002)
    box("door_push", (.09, .006, .32), (dx1 - .12, -.056, 1.05), steel, bevel=.002)
    cyl("door_port_ring", .17, .014, (dxc, -.056, 1.55), steel, rot=(rad(90), 0, 0), verts=48, flat_caps=True)
    cyl("door_port_glass", .145, .008, (dxc, -.058, 1.55), mat("bd4_port", (0.10, 0.14, 0.15, 1), rough=.35), rot=(rad(90), 0, 0), verts=48, flat_caps=True)
    for k, y in enumerate((.35, 1.0, 1.75)):   # hinges on the left edge
        box(f"hinge{k}", (.02, .06, .10), (dx0 + .005, -.055, y), steel, bevel=.003)
    # exit light: green box, icon = a cream door frame with a running arrow (no letters)
    exz = dh + .30
    box("exit_box", (.36, .08, .17), (dxc, -.04, exz), green, bevel=.012)
    box("exit_door", (.07, .006, .11), (dxc - .08, -.083, exz), icon, bevel=.004)
    box("exit_knob", (.012, .004, .012), (dxc - .06, -.087, exz - .005), green, bevel=0)
    box("exit_arrow", (.11, .006, .024), (dxc + .03, -.083, exz), icon, bevel=0)
    for sgn in (1, -1):
        o = box(f"exit_arrow_h{sgn}", (.055, .006, .022), (-.022, 0, 0), icon, bevel=0); o.location = (dxc + .085, -.083, exz); o.rotation_euler = (0, rad(45 * sgn), 0)
    # --- monstera in a glazed pot in the corner (x ~4.3, y ~-.65)
    mx, my = 3.98, -.78
    pot("mpot", .18, .14, .32, (mx, my, 0), glaze, soil)
    cyl("mpot_foot", .15, .02, (mx, my, .01), glaze, verts=32)
    mon = leaf_mat("monstera", (0.07, 0.30, 0.12), (0.16, 0.46, 0.18))
    stem = mat("bd4_stem", (0.22, 0.42, 0.18, 1), rough=.6)
    for k in range(13):
        a = -40 + k * 29 + rnd.uniform(-8, 8); L = rnd.uniform(.44, .62); tilt = rnd.uniform(20, 62); sl = rnd.uniform(.30, .70)
        ca, sa = math.cos(rad(a)), math.sin(rad(a)); d = sl * math.sin(rad(tilt))
        st = cyl(f"mstem{k}", .011, sl, (0, 0, sl / 2), stem, verts=8); st.location = (mx, my, .30)
        st.rotation_euler = (-rad(tilt) * sa, rad(tilt) * ca, 0)   # tilt away from the vertical toward direction a
        tip = (mx + ca * d, my + sa * d, .30 + sl * math.cos(rad(tilt)))
        monstera_leaf(f"mleaf{k}", L, mon, tip, a + 90, 30 + rnd.uniform(-10, 30), notches=(.28, .48, .66, .82) if k % 2 else (.34, .56, .76))
    # --- vintage orange poster on the side wall (looks toward -x)
    poster = image_mat("poster", os.path.join(TEX, "poster.png"))
    picture_side("poster", -1.35, 1.90, .52, .66, XR, dark_wood, poster)
    # --- pendant lamps (teal cone shades, brass rim, warm bulb) + a ceiling rose each
    for nm, x, y in (("lamp_a", 2.70, -1.7), ("lamp_b", 3.95, -1.7), ("lamp_c", 1.0, -1.7), ("lamp_d", -1.6, -1.7)):
        cyl(nm + "_rose", .06, .03, (x, y, H - .015), brass, verts=24)
        cyl(nm + "_cord", .006, H - 2.15, (x, y, (H + 2.15) / 2), cord, verts=8)
        cone(nm + "_shade", .19, .045, .20, (x, y, 2.15), teal_metal, bevel=.012)
        cyl(nm + "_rim", .19, .014, (x, y, 2.045), brass, verts=32)
        sphere(nm + "_bulb", .045, (x, y, 2.05), bulb)
        bpy.ops.object.light_add(type='POINT', location=(x, y, 2.02)); l = bpy.context.object; l.name = nm + "_light"; l.data.energy = 60; l.data.color = (1, .85, .65); l.data.shadow_soft_size = .08; l["layer"] = "light"
    # --- step stool by the shelving (two wooden treads, teal sides)
    stx, sty = 1.85, -1.20
    for sgn in (-1, 1):
        box(f"stool_side{sgn}", (.03, .40, .46), (stx + sgn * .18, sty, .23), teal_m, bevel=.008)
    box("stool_tread1", (.40, .16, .03), (stx, sty - .11, .24), shelf_w, bevel=.006)
    box("stool_tread2", (.40, .18, .03), (stx, sty + .10, .46), shelf_w, bevel=.006)
    box("stool_riser", (.34, .02, .18), (stx, sty + .005, .36), teal_m, bevel=.004)
    # --- mop bucket with wringer and a mop leaning in the far left corner (peeks at the left edge)
    bx, by = -4.15, -.55
    cone("bucket", .17, .20, .36, (bx, by, .18), yellow, bevel=.01)
    cyl("bucket_rim", .21, .02, (bx, by, .36), yellow, verts=32)
    box("wringer", (.22, .20, .16), (bx, by + .02, .42), yellow, bevel=.012)
    box("wringer_lever", (.03, .03, .35), (bx + .11, by + .10, .62), grey, bevel=.006)
    o = cyl("mop_handle", .013, 1.35, (0, 0, .675), wood_mat("mop", (0.80, 0.58, 0.30), (0.62, 0.42, 0.20)), verts=10); o.location = (bx + .05, by - .12, .30); o.rotation_euler = (rad(-8), rad(6), 0)
    for k in range(10):
        a = k * 36; o = cyl(f"mop_str{k}", .009, .28, (0, 0, -.14), mat("bd4_mop", (0.85, 0.82, 0.74, 1), rough=.9), verts=6)
        o.location = (bx + .05 + math.cos(rad(a)) * .03, by - .12 + math.sin(rad(a)) * .03, .30); o.rotation_euler = (rad(-8) + rad(math.sin(rad(a)) * 12), rad(6) + rad(math.cos(rad(a)) * 12), 0)
    # --- bunting: a sagging string of cloth pennants across the left half of the wall (teal / orange / cream)
    flag_ms = [mat("bd4_flag_t", TEAL, rough=.85), mat("bd4_flag_o", ORANGE, rough=.85), mat("bd4_flag_c", CREAM, rough=.85)]
    xa, xb, zs, sag, yb = -4.4, 1.45, 2.58, .22, -.04
    nseg = 36
    for k in range(nseg):
        t0_, t1_ = k / nseg, (k + 1) / nseg
        p0 = Vector((xa + (xb - xa) * t0_, yb, zs - sag * 4 * t0_ * (1 - t0_))); p1 = Vector((xa + (xb - xa) * t1_, yb, zs - sag * 4 * t1_ * (1 - t1_)))
        o = cyl(f"bunt_str{k}", .004, (p1 - p0).length, (0, 0, 0), cord, verts=6); o.location = (p0 + p1) / 2
        o.rotation_euler = (p1 - p0).to_track_quat('Z', 'Y').to_euler()
    nf = 22; fw_ = (xb - xa) / nf
    for k in range(nf):
        t = (k + .5) / nf; x = xa + (xb - xa) * t; z = zs - sag * 4 * t * (1 - t)
        mesh_obj(f"flag{k}", [(-fw_ * .42, 0, 0), (fw_ * .42, 0, 0), (0, .01, -fw_ * 1.15)], [(0, 1, 2)], flag_ms[k % 3], loc=(x, yb - .006, z - .004))
    for x in (xa, xb):
        cyl(f"bunt_nail{x:.1f}", .012, .02, (x, yb - .01, zs), brass, rot=(rad(90), 0, 0), verts=12)
    # --- a rubber doormat in front of the stockroom door and a floor marking strip
    box("doormat", (1.0, .55, .012), (dxc, -.40, .006), mat("bd4_mat", (0.20, 0.22, 0.22, 1), rough=.95), bevel=.004)
    return dict(cam=(0.55, -6.0, 1.75), pitch=6.0, yaw=-3.0, lens=22)

def light_room(H=2.8):
    sc = bpy.context.scene
    w = bpy.data.worlds.get("RA_World4") or bpy.data.worlds.new("RA_World4"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (.80, .86, .92, 1); w.node_tree.nodes["Background"].inputs[1].default_value = .18
    sc.view_settings.exposure = -0.25
    def area(n, loc, aim, energy, s, color=(1, .96, .90)):
        bpy.ops.object.light_add(type='AREA', location=loc); l = bpy.context.object; l.name = n
        l.data.energy = energy; l.data.size = s; l.data.color = color
        l.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); l["layer"] = "light"
    area("Key", (-3.5, -5.5, 4.2), (1.5, -1.0, 1.0), 850, 3.0)                       # warm, from the front-left and above (same side as the fixtures' key)
    area("Fill", (5.5, -6.5, 2.4), (2.5, -1.0, 1.2), 450, 4.0, (.90, .95, 1))          # cool soft fill from the right
    area("Top", (1.5, -2.5, H - .05), (1.5, -2.5, 0), 250, 5.0, (1, .98, .95))            # ceiling bounce

def room_camera(v):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("RA_Cam")
    if not cam:
        cam = bpy.data.objects.new("RA_Cam", bpy.data.cameras.new("RA_Cam")); sc.collection.objects.link(cam)
    cam.data.lens = v["lens"]; cam.data.sensor_width = 36; cam.data.sensor_fit = 'HORIZONTAL'
    cam.location = v["cam"]; cam.rotation_euler = (rad(90 - v["pitch"]), 0, rad(v["yaw"])); cam["layer"] = "cam"
    sc.camera = cam; return cam

def render_backdrop(out_dir=None, samples=128):
    out = out_dir or OUT; os.makedirs(out, exist_ok=True)
    sc = scene(); v = build_backdrop()
    room_camera(v); light_room()
    sc.cycles.samples = samples
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1000; sc.render.film_transparent = False
    _show(["back", "front"]); sc.render.filepath = os.path.join(out, "restock_backdrop.png"); bpy.ops.render.render(write_still=True)
    sc.render.film_transparent = True; sc.render.resolution_x, sc.render.resolution_y = RES; sc.cycles.samples = 64
    return sc.render.filepath

if not globals().get("NO_AUTORUN"): render_backdrop()
