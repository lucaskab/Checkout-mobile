"""Thief (Lucas's Tripo model from his 2D drawing, 08/11/2026): repaint the texture so it matches the drawing.

The Tripo atlas came out blotchy: smeared face (grey patches over the brow and hair, small uneven eyes), orange
plastic-looking skin, grey shoes. Fix, baked into a new albedo on the model's own UVs:
  1. The drawing itself is projected from the front (it is the image the model was made from, so the silhouettes
     line up) onto every surface that faces the camera, fading out towards the sides; the white background never
     projects (alpha mask).
  2. Everywhere else the original atlas is kept, colour-corrected to the drawing: skin less saturated / lighter,
     shoes navy with the teal kept and white soles, the hoodie navy, trousers charcoal.
  3. The glossy PBR maps are dropped: the game uses one painted albedo (soft, matte).

    exec(open(".../pets/thief_texfix.py").read()); fix_thief_texture()
"""
import bpy, os, math

ART = "/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/ArtSource"
GLB = os.path.join(ART, "NPCs/incoming/Thief_Hoodie.glb")
REF = os.path.join(ART, "TripoReferences/Thief/thief_ref_rgba.png")
FACEMASK = os.path.join(ART, "TripoReferences/Thief/thief_ref_facemask.png")   # the drawing's face only (no hair)
OUT = os.path.join(ART, "NPCs/incoming/Thief_Hoodie_albedo.png")
# drawing pixels: x_img = 509 + x*1488, y_img(top) = 1506 - z*1488 (model 1.0 tall, centred on x = 0, feet at z = 0)
U0, US = 509 / 1024, 1488 / 1024
V0, VS = 30 / 1536, 1488 / 1536


def thief_mesh():
    o = next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("tripo_node")), None)
    if o is None:
        bpy.ops.import_scene.gltf(filepath=GLB)
        o = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("tripo_node"))
    return o


def original_basecolor(o):
    # always the Tripo material's own base colour (the object may already wear an earlier fix)
    # (Tripo's material may have been purged on a save: then its basecolor image itself, never our own bake)
    for im in bpy.data.images:
        if "basecolor" in im.name.lower() and not im.name.startswith("Thief"):
            return im
    m = next((m for m in bpy.data.materials if m.name.startswith("tripo_material")), None)
    if m is None:
        raise RuntimeError("Tripo base colour not found (would compound on our own bake)")
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and "basecolor" in n.image.name.lower():
            return n.image
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and n.image.colorspace_settings.name == 'sRGB':
            return n.image
    raise RuntimeError("no base colour")


def smoothstep_node(nt, src, lo, hi):
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = 'SMOOTHSTEP'
    mr.inputs["From Min"].default_value = lo; mr.inputs["From Max"].default_value = hi
    nt.links.new(src, mr.inputs["Value"])
    return mr.outputs["Result"]


def math_node(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op
    if isinstance(a, (int, float)):
        n.inputs[0].default_value = a
    else:
        nt.links.new(a, n.inputs[0])
    if b is not None:
        if isinstance(b, (int, float)):
            n.inputs[1].default_value = b
        else:
            nt.links.new(b, n.inputs[1])
    return n.outputs[0]


def mix_rgb(nt, fac, a, b, blend='MIX'):
    m = nt.nodes.new("ShaderNodeMix"); m.data_type = 'RGBA'; m.blend_type = blend
    for sock, v in (("Factor", fac), ("A", a), ("B", b)):
        if isinstance(v, (int, float)):
            m.inputs[sock].default_value = v
        elif isinstance(v, tuple):
            m.inputs[sock].default_value = v
        else:
            nt.links.new(v, m.inputs[sock])
    return m.outputs["Result"]


def lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def bake_material(o, base_img, settings):
    s = settings
    mat = bpy.data.materials.get("Thief_TexFix") or bpy.data.materials.new("Thief_TexFix")
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear(); L = nt.links.new; N = nt.nodes.new
    out = N("ShaderNodeOutputMaterial"); emi = N("ShaderNodeEmission")
    uv = N("ShaderNodeUVMap"); uv.uv_map = o.data.uv_layers.active.name
    base = N("ShaderNodeTexImage"); base.image = base_img; L(uv.outputs["UV"], base.inputs["Vector"])
    tc = N("ShaderNodeTexCoord"); sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs["Vector"])
    x, y, z = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]
    geo = N("ShaderNodeNewGeometry")
    # --- colour correction of the original atlas
    hsv = N("ShaderNodeSeparateColor"); hsv.mode = 'HSV'; L(base.outputs["Color"], hsv.inputs["Color"])
    h, sat, val = hsv.outputs[0], hsv.outputs[1], hsv.outputs[2]
    skin = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', smoothstep_node(nt, h, 0.0, 0.03), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, h, 0.10, 0.13))),
                     math_node(nt, 'MULTIPLY', smoothstep_node(nt, sat, 0.28, 0.40), smoothstep_node(nt, val, 0.40, 0.55)))
    skin = math_node(nt, 'MULTIPLY', skin, smoothstep_node(nt, z, 0.08, 0.12))          # not the shoes
    hue = N("ShaderNodeHueSaturation"); hue.inputs["Saturation"].default_value = s["skin_sat"]
    hue.inputs["Value"].default_value = s["skin_val"]; hue.inputs["Hue"].default_value = s["skin_hue"]
    L(base.outputs["Color"], hue.inputs["Color"])
    col = mix_rgb(nt, skin, base.outputs["Color"], hue.outputs["Color"])
    # hoodie / tee / trousers: the Tripo atlas is about twice as light as the drawing's navy and charcoal
    cloth = math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', 1.0, skin),
                      math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, 0.07, 0.09), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, s["neck_z"] - 0.01, s["neck_z"] + 0.01))))
    cloth = math_node(nt, 'MULTIPLY', cloth, math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, sat, 0.30, 0.45)))
    dark = mix_rgb(nt, 1.0, col, (s["cloth_gain"], s["cloth_gain"], s["cloth_gain"] * 1.06, 1), 'MULTIPLY')
    col = mix_rgb(nt, cloth, col, dark)
    # the hoodie part of it a little bluer (the drawing's navy; the atlas there is a grey-blue)
    hood_z = smoothstep_node(nt, z, s["hem_z"] - 0.01, s["hem_z"] + 0.01)
    bluer = mix_rgb(nt, 1.0, col, (0.86, 0.94, 1.30, 1), 'MULTIPLY')
    col = mix_rgb(nt, math_node(nt, 'MULTIPLY', cloth, hood_z), col, bluer)
    # grey smears of the Tripo atlas on the head: skin colour on the face, hair colour above the hairline
    grey = math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, sat, 0.20, 0.30)), smoothstep_node(nt, val, 0.42, 0.52))
    face_zone = math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, s["head_z"] - 0.01, s["head_z"] + 0.01),
                          math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, s["hairline_z"] - 0.008, s["hairline_z"] + 0.008)))
    hair_zone = smoothstep_node(nt, z, s["hairline_z"] - 0.008, s["hairline_z"] + 0.008)
    col = mix_rgb(nt, math_node(nt, 'MULTIPLY', grey, face_zone), col, lin(s["skin_fill"]))
    col = mix_rgb(nt, math_node(nt, 'MULTIPLY', grey, hair_zone), col, lin(s["hair_fill"]))
    teal = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', smoothstep_node(nt, h, 0.40, 0.44), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, h, 0.54, 0.58))),
                     math_node(nt, 'MULTIPLY', smoothstep_node(nt, sat, 0.25, 0.35), smoothstep_node(nt, z, s["shoe_top"] + 0.01, s["shoe_top"] + 0.03)))
    col = mix_rgb(nt, teal, col, lin((0.16, 0.19, 0.30)))
    # shoes: the grey upper becomes navy (teal accents stay), a white sole band at the bottom
    shoe = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, s["shoe_top"] - 0.01, s["shoe_top"] + 0.01))
    greyish = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, sat, 0.12, 0.25))
    navy = mix_rgb(nt, 1.0, lin(s["shoe_navy"]), base.outputs["Color"], 'MULTIPLY')
    navy = mix_rgb(nt, 1.0, navy, (2.4, 2.4, 2.4, 1), 'MULTIPLY')
    col = mix_rgb(nt, math_node(nt, 'MULTIPLY', shoe, greyish), col, navy)
    sole = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, s["sole_top"] - 0.004, s["sole_top"] + 0.004))
    col = mix_rgb(nt, sole, col, lin((0.93, 0.93, 0.91)))
    # --- the drawing, projected from the front
    # model point -> drawing pixel (mx, my from the top), then the face warp: Tripo made the face longer and a little
    # wider than the drawing, so the drawing's eyes / nose / mouth are moved onto the model's (landmarks measured on
    # an orthographic front render): my -> my' piecewise linear, mx squeezed around the face centre.
    mx = math_node(nt, 'MULTIPLY_ADD', x, 1488.0); nt.nodes[-1].inputs[2].default_value = 509.0
    my = math_node(nt, 'MULTIPLY_ADD', z, -1488.0); nt.nodes[-1].inputs[2].default_value = 1506.0
    tnorm = math_node(nt, 'DIVIDE', my, 1536.0)
    fc = N("ShaderNodeFloatCurve"); L(tnorm, fc.inputs["Value"])
    cm = fc.mapping; cv = cm.curves[0]
    pts = [(p[0] / 1536, p[1] / 1536) for p in s["warp_y"]]
    while len(cv.points) < len(pts):
        cv.points.new(0.5, 0.5)
    for pt, (a, b) in zip(cv.points, pts):
        pt.location = (a, b); pt.handle_type = 'VECTOR'
    cm.clip_min_x = 0; cm.clip_max_x = 1; cm.clip_min_y = 0; cm.clip_max_y = 1; cm.update()
    my2 = math_node(nt, 'MULTIPLY', fc.outputs["Value"], 1536.0)
    head = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, my, s["warp_end"] - 20, s["warp_end"] + 10))
    sx = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', head, s["warp_sx"] - 1.0), 1.0)
    dx = math_node(nt, 'SUBTRACT', mx, s["face_cx_model"])
    mx2 = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', dx, sx),
                    math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', head, s["face_cx_ref"] - s["face_cx_model"]), s["face_cx_model"]))
    u = math_node(nt, 'DIVIDE', mx2, 1024.0)
    v = math_node(nt, 'SUBTRACT', 1.0, math_node(nt, 'DIVIDE', my2, 1536.0))
    cmb = N("ShaderNodeCombineXYZ"); L(u, cmb.inputs["X"]); L(v, cmb.inputs["Y"])
    ref = N("ShaderNodeTexImage"); ref.image = bpy.data.images.load(REF, check_existing=True); ref.extension = 'CLIP'
    ref.interpolation = 'Cubic'
    L(cmb.outputs["Vector"], ref.inputs["Vector"])
    facing = N("ShaderNodeVectorMath"); facing.operation = 'DOT_PRODUCT'
    L(geo.outputs["Normal"], facing.inputs[0]); facing.inputs[1].default_value = (0, -1, 0)
    # the head takes the drawing almost all round its front half (its own atlas there is the blotchiest)
    headz = smoothstep_node(nt, z, s["head_z"] - 0.01, s["head_z"] + 0.01)
    lo = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', headz, s["head_lo"] - s["face_lo"]), s["face_lo"])
    hi = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', headz, s["head_hi"] - s["face_hi"]), s["face_hi"])
    wmr = N("ShaderNodeMapRange"); wmr.interpolation_type = 'SMOOTHSTEP'
    L(facing.outputs["Value"], wmr.inputs["Value"]); L(lo, wmr.inputs["From Min"]); L(hi, wmr.inputs["From Max"])
    w = wmr.outputs["Result"]
    fm = N("ShaderNodeTexImage"); fm.image = bpy.data.images.load(FACEMASK, check_existing=True); fm.extension = 'CLIP'
    fm.image.colorspace_settings.name = 'Non-Color'
    L(cmb.outputs["Vector"], fm.inputs["Vector"])
    fmv = N("ShaderNodeSeparateColor"); L(fm.outputs["Color"], fmv.inputs["Color"])
    # on the head only the drawing's face goes on (its hair does not match the model's hair); elsewhere its alpha
    # ...and only on the head and neck themselves, never on the hood's lining around the neck
    rx_ = math_node(nt, 'MULTIPLY', x, x); dy_ = math_node(nt, 'SUBTRACT', y, s["neck_cy"])
    rad_ = math_node(nt, 'SQRT', math_node(nt, 'ADD', rx_, math_node(nt, 'MULTIPLY', dy_, dy_)))
    gate = math_node(nt, 'MAXIMUM', math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, rad_, s["neck_r"] + 0.005, s["neck_r"] + 0.013)),
                     smoothstep_node(nt, z, 0.855, 0.865))
    alpha = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', ref.outputs["Alpha"], math_node(nt, 'SUBTRACT', 1.0, headz)),
                      math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', fmv.outputs[0], gate), headz))
    w = math_node(nt, 'MULTIPLY', w, alpha)
    # around the neck only standing surfaces take the drawing: the collar / tee tops facing up keep their fabric
    nsep0 = N("ShaderNodeSeparateXYZ"); L(geo.outputs["Normal"], nsep0.inputs["Vector"])
    upr0 = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, math_node(nt, 'ABSOLUTE', nsep0.outputs["Z"]), 0.45, 0.65))
    w = math_node(nt, 'MULTIPLY', w, math_node(nt, 'MAXIMUM', upr0, smoothstep_node(nt, z, 0.835, 0.845)))
    # only the front shell: a point hidden behind another part from the front (inner arm, the back of the hood…)
    # is caught by y: it must be on the front half of its body part
    front = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, y, s["front_y"], s["front_y"] + 0.04))
    w = math_node(nt, 'MULTIPLY', w, front)
    w = math_node(nt, 'MULTIPLY', w, s["strength"])
    col = mix_rgb(nt, w, col, ref.outputs["Color"])
    # skin facing down (under the chin, the nostrils, under the brows): the front projection only streaks the
    # drawing's collar / hoodie colours over it -> skin, shaded by occlusion
    down = smoothstep_node(nt, math_node(nt, 'MULTIPLY', nsep0.outputs["Z"], -1.0), 0.20, 0.50)
    dzone = math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, s["chin_z"] - 0.004, s["chin_z"] + 0.004),
                      math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, y, -0.005, 0.01)))
    dzone = math_node(nt, 'MULTIPLY', dzone, math_node(nt, 'MAXIMUM', math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, math_node(nt, 'ABSOLUTE', x), 0.050, 0.058)),
                                                      smoothstep_node(nt, z, 0.86, 0.87)))
    dzone = math_node(nt, 'MULTIPLY', dzone, math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, 0.945, 0.95)))
    aoD = N("ShaderNodeAmbientOcclusion"); aoD.samples = 16; aoD.inputs["Distance"].default_value = 0.012
    shade = math_node(nt, 'MULTIPLY_ADD', aoD.outputs["AO"], 0.40); nt.nodes[-1].inputs[2].default_value = 0.60
    dskin = mix_rgb(nt, 1.0, lin(s["skin_fill"]), (0.93, 0.86, 0.84, 1), 'MULTIPLY')
    dskin = mix_rgb(nt, 1.0, dskin, shade, 'MULTIPLY')
    # inside the (rebuilt, bulging) eyes the drawing goes on all round: no skin on their sides
    ein = None
    for (ecx, ecz) in s["eyes"]:
        ex = math_node(nt, 'DIVIDE', math_node(nt, 'SUBTRACT', x, ecx), s["eye_rx"])
        ez = math_node(nt, 'DIVIDE', math_node(nt, 'SUBTRACT', z, ecz), s["eye_rz"])
        ee = math_node(nt, 'SQRT', math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', ex, ex), math_node(nt, 'MULTIPLY', ez, ez)))
        one = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, ee, 0.85, 1.05))
        ein = one if ein is None else math_node(nt, 'MAXIMUM', ein, one)
    noteye = math_node(nt, 'SUBTRACT', 1.0, ein)
    col = mix_rgb(nt, math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', down, dzone), noteye), col, dskin)
    # any blue left on the face / chin skin (Tripo's collar colour smeared up the jaw and nostrils) -> shaded skin
    hsv2 = N("ShaderNodeSeparateColor"); hsv2.mode = 'HSV'; L(col, hsv2.inputs["Color"])
    blue = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', smoothstep_node(nt, hsv2.outputs[0], 0.48, 0.53), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, hsv2.outputs[0], 0.80, 0.85))),
                     smoothstep_node(nt, hsv2.outputs[1], 0.06, 0.14))
    fzone = math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, s["chin_z"] - 0.004, s["chin_z"] + 0.004),
                      math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, y, -0.01, 0.005)),
                                math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, math_node(nt, 'ABSOLUTE', x), 0.055, 0.062))))
    fzone = math_node(nt, 'MULTIPLY', fzone, math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, 0.94, 0.946)))
    col = mix_rgb(nt, math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', blue, fzone), noteye), col, dskin)
    # around the eyes the model's sockets are wider than the drawn eyes: their side walls get skin, not stretched white
    for sx_ in (-1, 1):
        x0, x1 = (0.010, 0.068) if sx_ > 0 else (-0.068, -0.010)
        box = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', smoothstep_node(nt, x, x0 - 0.004, x0 + 0.004), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, x, x1 - 0.004, x1 + 0.004))),
                        math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, 0.893, 0.899), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, 0.931, 0.937))))
        side = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, facing.outputs["Value"], s["eye_side_lo"], s["eye_side_hi"]))
        col = mix_rgb(nt, math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', box, side), noteye), col, lin(s["skin_fill"]))
    # the neck (inside the collar) is skin all round; the hood's lining is navy (Tripo smeared skin and collar there)
    rx = math_node(nt, 'MULTIPLY', x, x); dy = math_node(nt, 'SUBTRACT', y, s["neck_cy"]); ry = math_node(nt, 'MULTIPLY', dy, dy)
    rad = math_node(nt, 'SQRT', math_node(nt, 'ADD', rx, ry))
    neck = math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, rad, s["neck_r"] - 0.004, s["neck_r"] + 0.004)),
                     math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, 0.802, 0.808), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, 0.85, 0.86))))
    neck = math_node(nt, 'MULTIPLY', neck, math_node(nt, 'SUBTRACT', 1.0, w))
    # the neck is a standing cylinder: surfaces facing up there are the collar / tee tops, not skin
    nsep = N("ShaderNodeSeparateXYZ"); L(geo.outputs["Normal"], nsep.inputs["Vector"])
    upright = math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, math_node(nt, 'ABSOLUTE', nsep.outputs["Z"]), 0.45, 0.65))
    neck = math_node(nt, 'MULTIPLY', neck, upright)
    col = mix_rgb(nt, neck, col, lin(s["skin_fill"]))
    lining = math_node(nt, 'MULTIPLY', smoothstep_node(nt, rad, s["neck_r"] + 0.006, s["neck_r"] + 0.012),
                       math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, 0.74, 0.75), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, 0.87, 0.88))))
    warm_h = math_node(nt, 'MAXIMUM', math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, h, 0.12, 0.15)), smoothstep_node(nt, h, 0.90, 0.93))
    warm = math_node(nt, 'MULTIPLY', warm_h, smoothstep_node(nt, sat, 0.15, 0.25))
    light = smoothstep_node(nt, val, 0.42, 0.52)                       # anything much lighter than the navy fabric
    lining = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', lining, math_node(nt, 'MAXIMUM', warm, light)), math_node(nt, 'SUBTRACT', 1.0, w))
    col = mix_rgb(nt, lining, col, lin((0.15, 0.18, 0.29)))
    # back of the neck (behind the ears, under the beanie): skin, the collar Tripo painted there goes away
    back = smoothstep_node(nt, y, 0.0, 0.02)
    bneck = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', back, math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, rad, 0.060, 0.068))),
                      math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, 0.812, 0.82), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, 0.87, 0.88))))
    bneck = math_node(nt, 'MULTIPLY', bneck, upright)
    col = mix_rgb(nt, bneck, col, lin(s["skin_fill"]))
    # the black T-shirt at the collar: no skin-coloured dots where it meets the neck
    tee = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, 0.775, 0.785), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, s["tee_top"] - 0.004, s["tee_top"] + 0.002))),
                     math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, y, -0.005, 0.01)),
                               math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, rad, 0.070, 0.078)),
                                         smoothstep_node(nt, rad, s["neck_r"] + 0.004, s["neck_r"] + 0.009))))   # not the neck itself
    tee = math_node(nt, 'MULTIPLY', tee, math_node(nt, 'MAXIMUM', warm, light))
    col = mix_rgb(nt, tee, col, lin((0.19, 0.19, 0.21)))
    # hood and upper back: Tripo left dark teal swirls there; plain navy fabric with soft folds (occlusion) instead
    hb = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', smoothstep_node(nt, y, 0.02, 0.05), smoothstep_node(nt, z, s["hem_z"], s["hem_z"] + 0.015)),
                   math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, 0.875, 0.885)), smoothstep_node(nt, rad, 0.068, 0.076)))
    hb = math_node(nt, 'MULTIPLY', hb, math_node(nt, 'SUBTRACT', 1.0, skin))
    aoN = N("ShaderNodeAmbientOcclusion"); aoN.samples = 16; aoN.inputs["Distance"].default_value = 0.03
    aoV = smoothstep_node(nt, aoN.outputs["AO"], -0.5, 1.0)
    navyc = mix_rgb(nt, 1.0, lin((0.17, 0.20, 0.33)), aoV, 'MULTIPLY')
    col = mix_rgb(nt, hb, col, navyc)
    # where the hair lock was laid back onto the forehead: plain skin up to the beanie
    fx0, fx1, fz0, fz1 = s["lock_skin"]
    lk = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', smoothstep_node(nt, x, fx0 - 0.004, fx0 + 0.004), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, x, fx1 - 0.004, fx1 + 0.004))),
                   math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, fz0 - 0.002, fz0 + 0.002), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, y, -0.040, -0.030))))
    col = mix_rgb(nt, lk, col, lin(s["skin_fill"]))
    # the model's own hair locks over the forehead (the drawing has skin there): hair colour, shaded by the atlas
    for (x0, x1, z0, z1, y1) in s["hair_boxes"]:
        inb = math_node(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', smoothstep_node(nt, x, x0 - 0.004, x0 + 0.004), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, x, x1 - 0.004, x1 + 0.004))),
                        math_node(nt, 'MULTIPLY', smoothstep_node(nt, z, z0 - 0.003, z0 + 0.003), math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, z, z1 - 0.003, z1 + 0.003))))
        inb = math_node(nt, 'MULTIPLY', inb, math_node(nt, 'SUBTRACT', 1.0, smoothstep_node(nt, y, y1 - 0.005, y1 + 0.005)))
        # only the part standing out of the forehead: the atlas is brown or grey there (not skin)
        notskin = math_node(nt, 'SUBTRACT', 1.0, skin)
        inb = math_node(nt, 'MULTIPLY', inb, notskin)
        shade = math_node(nt, 'MULTIPLY_ADD', val, 0.9); nt.nodes[-1].inputs[2].default_value = 0.55
        hairc = mix_rgb(nt, 1.0, lin(s["hair_fill"]), (1, 1, 1, 1), 'MULTIPLY')
        hairc = mix_rgb(nt, 1.0, hairc, shade, 'MULTIPLY') if False else hairc
        col = mix_rgb(nt, inb, col, hairc)
    L(col, emi.inputs["Color"]); L(emi.outputs["Emission"], out.inputs["Surface"])
    return mat


DEFAULTS = dict(warp_y=[(0, 0), (18, 18), (144, 160), (215, 205), (242, 225), (270, 257), (310, 310), (1536, 1536)],
                eye_side_lo=0.12, eye_side_hi=0.32, tee_top=0.815, neck_cy=-0.006, neck_r=0.047,
                lock_skin=(-0.078, 0.004, 0.931, 1.0),
                hair_boxes=[],
                head_z=0.80, head_lo=0.02, head_hi=0.30, hairline_z=0.952,
                skin_fill=(0.93, 0.66, 0.50), hair_fill=(0.27, 0.18, 0.12),
                warp_end=305, warp_sx=0.91, face_cx_model=510.0, face_cx_ref=506.0, neck_z=0.80, cloth_gain=0.36, hem_z=0.505, chin_z=0.818,
                eyes=[(-0.0253, 0.9125), (0.0284, 0.9132)], eye_rx=0.0140, eye_rz=0.0110,
                skin_sat=0.85, skin_val=1.0, skin_hue=0.5, shoe_top=0.075, sole_top=0.016,
                shoe_navy=(0.12, 0.16, 0.33), face_lo=0.35, face_hi=0.75, front_y=0.06, strength=1.0)


def fix_thief_texture(size=4096, samples=1, **kw):
    s = dict(DEFAULTS); s.update(kw)
    o = thief_mesh()
    base_img = original_basecolor(o)
    orig_mat = o.data.materials[0]
    mat = bake_material(o, base_img, s)
    img = bpy.data.images.get("Thief_albedo") or bpy.data.images.new("Thief_albedo", size, size, alpha=False)
    tn = mat.node_tree.nodes.new("ShaderNodeTexImage"); tn.image = img; mat.node_tree.nodes.active = tn
    o.data.materials[0] = mat
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'GPU'; sc.cycles.samples = samples
    sc.render.bake.margin = 8; sc.render.bake.use_clear = True
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.bake(type='EMIT')
    img.filepath_raw = OUT; img.file_format = 'PNG'; img.save()
    # matte preview material with the new albedo
    pm = bpy.data.materials.get("Thief_Albedo") or bpy.data.materials.new("Thief_Albedo"); pm.use_nodes = True
    g = pm.node_tree; g.nodes.clear()
    o_ = g.nodes.new("ShaderNodeOutputMaterial"); b = g.nodes.new("ShaderNodeBsdfPrincipled")
    t = g.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(OUT, check_existing=True); t.image.reload()
    g.links.new(t.outputs["Color"], b.inputs["Base Color"]); g.links.new(b.outputs["BSDF"], o_.inputs["Surface"])
    b.inputs["Roughness"].default_value = 0.72; b.inputs["Specular IOR Level"].default_value = 0.3
    o.data.materials[0] = pm
    print("baked", OUT)
    return o
