"""Builds the thief and the guard (needs security_chars.py exec'd first). Character space: 2.4 m, faces -Y,
the character's left is -X."""


def face_profile(info, x=0.0, z0=1.9, z1=2.4, step=0.01):
    """Front-most skin point per height along x: (z, y). Used to find the nose and the eye line."""
    prof = []
    z = z0
    while z < z1:
        loc, n, i, d = info.bvh.ray_cast(V((x, -1.5, z)), V((0, 1, 0)))
        if loc is not None:
            prof.append((z, loc.y))
        z += step
    return prof


def eye_line(info):
    prof = face_profile(info)
    nose_z, nose_y = min(prof, key=lambda p: p[1])
    return nose_z, nose_y


# ------------------------------------------------------------------------------------------------ thief
THIEF = dict(base="Customer_02", tag="Thief",
             hoodie=(0.25, 0.27, 0.31), rib=(0.20, 0.21, 0.25), pocket=(0.21, 0.23, 0.27),
             string=(0.92, 0.92, 0.90), lens=(0.06, 0.07, 0.09), frame=(0.10, 0.10, 0.11),
             bag=(0.40, 0.30, 0.20), strap=(0.20, 0.18, 0.16), buckle=(0.80, 0.70, 0.40))


def hoodie(info, cfg, z_hem=0.80, z_neck=1.865):
    co = info.co
    hand = info.w("Hand_L") + info.w("Hand_R")
    head = info.w("Head")
    legs = info.w("Thigh_L") + info.w("Thigh_R") + info.w("Shin_L") + info.w("Shin_R")
    keep = (co[:, 2] > z_hem) & (co[:, 2] < z_neck) & (hand < 0.3) & (head < 0.5) & (legs < 0.6)
    o = shell_from_body(info, cfg["tag"] + "_Hoodie", keep, offset=0.030, smooth=14, push=0.022, thickness=0.012)
    print("thief body faces hidden", hide_under(info.body, keep, erode=2))
    unwrap(o)

    def extra(nt, cur, tc):
        N = nt.nodes.new; L = nt.links.new
        sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs["Vector"])
        # kangaroo pocket: a panel on the belly with a stitched border
        def box(lo, hi):
            acc = None
            for ax, a, b in zip("XYZ", lo, hi):
                g1 = N("ShaderNodeMath"); g1.operation = 'GREATER_THAN'; L(sep.outputs[ax], g1.inputs[0]); g1.inputs[1].default_value = a
                g2 = N("ShaderNodeMath"); g2.operation = 'LESS_THAN'; L(sep.outputs[ax], g2.inputs[0]); g2.inputs[1].default_value = b
                m = N("ShaderNodeMath"); m.operation = 'MULTIPLY'; L(g1.outputs[0], m.inputs[0]); L(g2.outputs[0], m.inputs[1])
                if acc is not None:
                    m2 = N("ShaderNodeMath"); m2.operation = 'MULTIPLY'; L(acc, m2.inputs[0]); L(m.outputs[0], m2.inputs[1]); acc = m2.outputs[0]
                else:
                    acc = m.outputs[0]
            return acc
        outer = box((-0.19, -1, 0.93), (0.19, 0.0, 1.16))
        inner = box((-0.175, -1, 0.945), (0.175, 0.0, 1.145))
        rim = N("ShaderNodeMath"); rim.operation = 'SUBTRACT'; L(outer, rim.inputs[0]); L(inner, rim.inputs[1])
        pc = N("ShaderNodeRGB"); pc.outputs[0].default_value = (*lin(cfg["pocket"]), 1)
        m1 = N("ShaderNodeMix"); m1.data_type = 'RGBA'; L(inner, m1.inputs["Factor"]); L(cur, m1.inputs["A"]); L(pc.outputs[0], m1.inputs["B"])
        st = N("ShaderNodeRGB"); st.outputs[0].default_value = (*lin((0.15, 0.16, 0.19)), 1)
        m2 = N("ShaderNodeMix"); m2.data_type = 'RGBA'; L(rim.outputs[0], m2.inputs["Factor"]); L(m1.outputs["Result"], m2.inputs["A"]); L(st.outputs[0], m2.inputs["B"])
        return m2.outputs["Result"]
    mat = bpy.data.materials.new(cfg["tag"] + "_HoodieBake")
    fabric_nodes(mat, cfg["hoodie"], weave_scale=520, weave_amt=0.07, mottle=0.08,
                 bands=[("z", z_hem - 0.05, z_hem + 0.07, cfg["rib"], 160)], extra=extra)
    bake_to_texture(o, mat, cfg["tag"] + "_Hoodie", size=1024)
    return o


def hood(info, cfg):
    lo, hi = info.head_box()
    c = (lo + hi) / 2
    nose_z, nose_y = eye_line(info)
    rx, ry, rz = (hi - lo) / 2
    centre = V((c[0], c[1] + 0.02, c[2] - 0.02))

    def cut(p):
        q = p - centre
        # face opening (an oval around the face) and the open bottom (front higher than the back)
        face = ((q.y < -ry * 0.22) and (abs(q.x) < rx * 0.80) and (q.z < rz * 0.55)) or \
               ((q.y < 0.05) and (abs(q.x) < rx * 0.70) and (q.z < -rz * 0.35))          # under the chin / beard
        bottom = p.z < lo[2] - 0.06
        return face or bottom
    o = fit_cap(info, cfg["tag"] + "_Hood", centre, (rx * 1.02, ry * 1.04, rz * 1.02), cut, offset=0.035, smooth=8)
    s = o.modifiers.new("cloth", 'SOLIDIFY'); s.thickness = 0.014; s.offset = 1
    ctx_obj(o); bpy.ops.object.modifier_apply(modifier="cloth")
    unwrap(o)
    mat = bpy.data.materials.new(cfg["tag"] + "_HoodBake")
    fabric_nodes(mat, cfg["hoodie"], weave_scale=520, weave_amt=0.07, mottle=0.08)
    bake_to_texture(o, mat, cfg["tag"] + "_Hood", size=512)
    # drawstrings hanging from the hood opening
    parts = []
    for s_ in (-1, 1):
        top = V((s_ * rx * 0.55, lo[1] + 0.02, lo[2] + 0.06))
        loc, n, i, d = info.bvh.ray_cast(V((top.x, -1.5, top.z)), V((0, 1, 0)))
        if loc is not None:
            top = loc + V((0, -0.035, 0))
        pts = [top, top + V((s_ * 0.004, -0.012, -0.10)), top + V((s_ * 0.006, -0.02, -0.20))]
        t = tube(cfg["tag"] + "_String", pts, 0.008, sides=8)
        tip = tube(cfg["tag"] + "_Aglet", [pts[-1], pts[-1] + V((0, 0, -0.035))], 0.010, sides=8)
        parts += [t, tip]
    strings = join(parts, cfg["tag"] + "_Strings")
    strings.data.materials.append(simple_mat("Thief_StringMat", cfg["string"], 0.7))
    return o, strings


def sunglasses(info, cfg):
    nose_z, nose_y = eye_line(info)
    z = nose_z + 0.085
    parts = []
    for s in (-1, 1):
        x = s * 0.105
        loc, n, i, d = info.bvh.ray_cast(V((x, -1.5, z)), V((0, 1, 0)))
        y = (loc.y if loc is not None else nose_y + 0.06) - 0.018
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.072, radius2=0.072, depth=0.016)
        me = bpy.data.meshes.new("Lens"); bm.to_mesh(me); bm.free()
        lens = link(bpy.data.objects.new(cfg["tag"] + "_Lens", me))
        lens.rotation_euler = (math.radians(90), 0, math.radians(-s * 8)); lens.location = (x, y, z)
        lens.data.materials.append(simple_mat("Thief_LensMat", cfg["lens"], 0.08, 0.3))
        rim = bpy.data.meshes.new("Rim"); bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=False, segments=28, radius=0.074)
        bm.to_mesh(rim); bm.free()
        r = link(bpy.data.objects.new(cfg["tag"] + "_Rim", rim))
        r.rotation_euler = lens.rotation_euler; r.location = (x, y - 0.004, z)
        sk = r.modifiers.new("skin", 'SKIN')
        ctx_obj(r)
        for v in r.data.skin_vertices[0].data:
            v.radius = (0.009, 0.009)
        bpy.ops.object.modifier_apply(modifier="skin")
        r.data.materials.append(simple_mat("Thief_FrameMat", cfg["frame"], 0.35, 0.2))
        parts += [lens, r]
        # temple arm back to the ear
        back = V((s * 0.27, y + 0.24, z + 0.01))
        arm = tube(cfg["tag"] + "_Temple", [V((s * 0.175, y + 0.005, z)), V((s * 0.24, y + 0.06, z)), back], 0.008, sides=8)
        arm.data.materials.append(simple_mat("Thief_FrameMat", cfg["frame"], 0.35, 0.2))
        parts.append(arm)
    bridge = tube(cfg["tag"] + "_Bridge", [V((-0.035, nose_y + 0.02, z + 0.02)), V((0, nose_y + 0.012, z + 0.03)),
                                          V((0.035, nose_y + 0.02, z + 0.02))], 0.008, sides=8)
    bridge.data.materials.append(simple_mat("Thief_FrameMat", cfg["frame"], 0.35, 0.2))
    parts.append(bridge)
    for p in parts:
        ctx_obj(p); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return join(parts, cfg["tag"] + "_Sunglasses")


def cross_bag(info, cfg, hoodie_obj):
    """Messenger bag on the left hip, strap across the chest from the right shoulder."""
    hb = BVHTree.FromObject(hoodie_obj, bpy.context.evaluated_depsgraph_get())
    bag = rounded_box(cfg["tag"] + "_Bag", (0.12, 0.05, 0.095), bevel=0.025, segs=4)
    # find the hoodie surface at the left hip
    loc, n, i, d = hb.find_nearest(V((-0.26, -0.04, 0.98)))
    side = loc if loc is not None else V((-0.33, -0.02, 0.98))
    bag.location = side + V((-0.045, -0.035, 0)); bag.rotation_euler = (0, 0, math.radians(18))
    flap = rounded_box(cfg["tag"] + "_Flap", (0.124, 0.053, 0.05), bevel=0.02, segs=3)
    flap.location = bag.location + V((0, -0.006, 0.055)); flap.rotation_euler = bag.rotation_euler
    clasp = rounded_box(cfg["tag"] + "_Clasp", (0.022, 0.012, 0.03), bevel=0.006, segs=2)
    clasp.location = bag.location + V((-0.02, -0.058, 0.02)); clasp.rotation_euler = bag.rotation_euler
    for o in (bag, flap, clasp):
        ctx_obj(o); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bag.data.materials.append(simple_mat("Thief_BagMat", cfg["bag"], 0.75))
    flap.data.materials.append(simple_mat("Thief_FlapMat", tuple(c * 0.82 for c in cfg["bag"]), 0.7))
    clasp.data.materials.append(simple_mat("Thief_BuckleMat", cfg["buckle"], 0.3, 0.8))
    # strap: right shoulder -> across the chest -> bag (and around the back)
    lo, hi = info.head_box()
    shoulder = V((0.20, 0.0, 1.80))
    front = [shoulder, V((0.10, -0.25, 1.55)), V((-0.10, -0.25, 1.25)), V((-0.27, -0.12, 1.05)), side + V((0, -0.02, 0.06))]
    back = [shoulder, V((0.12, 0.25, 1.55)), V((-0.12, 0.24, 1.25)), V((-0.30, 0.10, 1.05)), side + V((0, 0.02, 0.06))]
    straps = []
    for k, path in enumerate((front, back)):
        pts = []
        for i_ in range(len(path) - 1):
            for t in range(10):
                p = path[i_].lerp(path[i_ + 1], t / 10)
                l, nn, _, _ = hb.find_nearest(p)
                pts.append(l + nn * 0.012)
        straps.append(tube(cfg["tag"] + "_Strap%d" % k, pts, 0.03, sides=8, flat=0.22))
    strap = join(straps, cfg["tag"] + "_Strap")
    strap.data.materials.append(simple_mat("Thief_StrapMat", cfg["strap"], 0.8))
    return join([bag, flap, clasp], cfg["tag"] + "_BagBody"), strap


def build_thief():
    cfg = THIEF
    rig, body = load_character(cfg["base"], cfg["tag"])
    info = BodyInfo(body)
    hd = hoodie(info, cfg); weights_from_body(hd, info, rig)
    hdd, strings = hood(info, cfg)
    for o in (hdd, strings):
        weights_from_body(o, info, rig)
    glasses = sunglasses(info, cfg); weights_rigid(glasses, rig, "Head")
    bag, strap = cross_bag(info, cfg, hd)
    weights_rigid(bag, rig, "Torso"); weights_from_body(strap, info, rig)
    print("thief", [o.name for o in rig.children])
    return rig


# ------------------------------------------------------------------------------------------------ guard
GUARD = dict(base="Customer_09", tag="Guard",
             shirt=(0.10, 0.16, 0.36), shirt_dark=(0.07, 0.11, 0.26), gold=(0.93, 0.72, 0.28),
             cap=(0.09, 0.14, 0.32), belt=(0.08, 0.08, 0.09), metal=(0.78, 0.79, 0.80))


def uniform_shirt(info, cfg, z_hem=1.00, z_neck=1.86):
    co = info.co
    keep_t = (co[:, 2] > z_hem) & (co[:, 2] < z_neck) & (info.w("Head") < 0.5)
    arms = info.w("UpperArm_L") + info.w("UpperArm_R")
    fore = info.w("Forearm_L") + info.w("Forearm_R") + info.w("Hand_L") + info.w("Hand_R")
    keep = keep_t & (fore < 0.35) & ((info.w("Torso") > 0.25) | (arms > 0.5))
    # short sleeves end above the elbow
    keep &= ~((arms > 0.5) & (co[:, 2] < 1.47))
    o = shell_from_body(info, cfg["tag"] + "_Shirt", keep, offset=0.024, smooth=12, push=0.018, thickness=0.010)
    print("guard body faces hidden", hide_under(info.body, keep, erode=2))
    unwrap(o)

    def extra(nt, cur, tc):
        N = nt.nodes.new; L = nt.links.new
        sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs["Vector"])
        # placket line + gold buttons down the front (y < 0), pocket flaps on the chest
        ax = N("ShaderNodeMath"); ax.operation = 'ABSOLUTE'; L(sep.outputs["X"], ax.inputs[0])
        pl = N("ShaderNodeMath"); pl.operation = 'LESS_THAN'; L(ax.outputs[0], pl.inputs[0]); pl.inputs[1].default_value = 0.022
        fr = N("ShaderNodeMath"); fr.operation = 'LESS_THAN'; L(sep.outputs["Y"], fr.inputs[0]); fr.inputs[1].default_value = -0.05
        plf = N("ShaderNodeMath"); plf.operation = 'MULTIPLY'; L(pl.outputs[0], plf.inputs[0]); L(fr.outputs[0], plf.inputs[1])
        dk = N("ShaderNodeRGB"); dk.outputs[0].default_value = (*lin(cfg["shirt_dark"]), 1)
        m1 = N("ShaderNodeMix"); m1.data_type = 'RGBA'; L(plf.outputs[0], m1.inputs["Factor"]); L(cur, m1.inputs["A"]); L(dk.outputs[0], m1.inputs["B"])
        # buttons every 0.13 along z
        wz = N("ShaderNodeMath"); wz.operation = 'PINGPONG'; L(sep.outputs["Z"], wz.inputs[0]); wz.inputs[1].default_value = 0.065
        bz = N("ShaderNodeMath"); bz.operation = 'LESS_THAN'; L(wz.outputs[0], bz.inputs[0]); bz.inputs[1].default_value = 0.014
        bx = N("ShaderNodeMath"); bx.operation = 'LESS_THAN'; L(ax.outputs[0], bx.inputs[0]); bx.inputs[1].default_value = 0.012
        b1 = N("ShaderNodeMath"); b1.operation = 'MULTIPLY'; L(bz.outputs[0], b1.inputs[0]); L(bx.outputs[0], b1.inputs[1])
        b2 = N("ShaderNodeMath"); b2.operation = 'MULTIPLY'; L(b1.outputs[0], b2.inputs[0]); L(fr.outputs[0], b2.inputs[1])
        gd = N("ShaderNodeRGB"); gd.outputs[0].default_value = (*lin(cfg["gold"]), 1)
        m2 = N("ShaderNodeMix"); m2.data_type = 'RGBA'; L(b2.outputs[0], m2.inputs["Factor"]); L(m1.outputs["Result"], m2.inputs["A"]); L(gd.outputs[0], m2.inputs["B"])
        return m2.outputs["Result"]
    mat = bpy.data.materials.new(cfg["tag"] + "_ShirtBake")
    fabric_nodes(mat, cfg["shirt"], weave_scale=700, weave_amt=0.05, mottle=0.06, extra=extra)
    bake_to_texture(o, mat, cfg["tag"] + "_Shirt", size=1024)
    return o


def collar(info, cfg):
    pts = ring_around(info, 1.835, 0.020, n=40, cy=0.0)
    o = ring_mesh(cfg["tag"] + "_Collar", pts, 0.055, 0.018)
    o.data.materials.append(simple_mat("Guard_CollarMat", cfg["shirt"], 0.75))
    return o


def guard_cap(info, cfg):
    lo, hi = info.head_box()
    c = (lo + hi) / 2; rx, ry, rz = (hi - lo) / 2
    nose_z, nose_y = eye_line(info)
    z_band = nose_z + 0.20                          # the cap sits on the brow line
    centre = V((c[0], c[1] + 0.01, z_band))

    def cut(p):
        return p.z < z_band - 0.005
    dome = fit_cap(info, cfg["tag"] + "_CapDome", centre, (rx * 0.98, ry * 1.0, (hi[2] - z_band) * 1.05), cut,
                   offset=0.022, smooth=6)
    s = dome.modifiers.new("t", 'SOLIDIFY'); s.thickness = 0.012; s.offset = 1
    ctx_obj(dome); bpy.ops.object.modifier_apply(modifier="t")
    dome.data.materials.append(simple_mat("Guard_CapMat", cfg["cap"], 0.7))
    # brim: a flattened, slightly curved half-disc in front
    bm = bmesh.new(); rows = 6; cols = 24
    front_y = min(v.co.y for v in dome.data.vertices)
    vs = []
    for j in range(rows + 1):
        t = j / rows
        row = []
        for i in range(cols + 1):
            a = math.pi * (i / cols)
            rr = 0.92 + 0.0 * t
            x = math.cos(a) * rx * rr * (1 - 0.1 * t)
            y = front_y + 0.03 - math.sin(a) * (0.02 + 0.17 * t)
            z = z_band - 0.004 - 0.03 * t * t - 0.012 * (1 - math.sin(a))
            row.append(bm.verts.new((c[0] + x, y, z)))
        vs.append(row)
    for j in range(rows):
        for i in range(cols):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    me = bpy.data.meshes.new("Brim"); bm.to_mesh(me); bm.free()
    brim = link(bpy.data.objects.new(cfg["tag"] + "_Brim", me))
    s = brim.modifiers.new("t", 'SOLIDIFY'); s.thickness = 0.012
    sb = brim.modifiers.new("s", 'SUBSURF'); sb.levels = 1
    ctx_obj(brim); bpy.ops.object.modifier_apply(modifier="t"); bpy.ops.object.modifier_apply(modifier="s")
    for p in brim.data.polygons:
        p.use_smooth = True
    brim.data.materials.append(simple_mat("Guard_CapDark", cfg["shirt_dark"], 0.6))
    # gold emblem on the front: a shield with a star (pictogram)
    emb = shield(cfg["tag"] + "_CapEmblem", 0.075)
    l, n, _, _ = BVHTree.FromObject(dome, bpy.context.evaluated_depsgraph_get()).ray_cast(
        V((c[0], -1.5, z_band + (hi[2] - z_band) * 0.42)), V((0, 1, 0)))
    emb.location = l + V((0, -0.006, 0)); emb.rotation_euler = (math.radians(90 - 18), 0, 0)
    ctx_obj(emb); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return join([dome, brim, emb], cfg["tag"] + "_Cap")


def shield(name, size, star=True):
    """Gold shield badge with a raised star (pictogram, no text). Local: faces -Y? built in XZ, thickness along Y."""
    pts2 = []
    for i in range(9):                                   # top edge, a soft dip in the middle
        x = -0.5 + i / 8
        pts2.append((x, 0.5 - 0.05 * math.cos(math.pi * (x + 0.5)) ** 2 * 0 - 0.04 * (1 - (2 * x) ** 2)))
    for i in range(1, 13):                               # right side down to the point
        u = i / 12
        pts2.append((0.5 * math.cos(u * math.pi / 2), 0.5 - 0.35 * u - 0.7 * math.sin(u * math.pi / 2) ** 2))
    for i in range(11, 0, -1):                           # mirrored back up the left side
        u = i / 12
        pts2.append((-0.5 * math.cos(u * math.pi / 2), 0.5 - 0.35 * u - 0.7 * math.sin(u * math.pi / 2) ** 2))
    bm = bmesh.new()
    vs = [bm.verts.new((x * size, 0, z * size)) for x, z in pts2]
    f = bm.faces.new(vs)
    ex = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in ex["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.y += 0.012
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    b = o.modifiers.new("b", 'BEVEL'); b.width = 0.004; b.segments = 2
    ctx_obj(o); bpy.ops.object.modifier_apply(modifier="b")
    o.data.materials.append(simple_mat("Guard_GoldMat", GUARD["gold"], 0.3, 0.9))
    if star:
        sbm = bmesh.new(); sv = []
        for k in range(10):
            r = (0.26 if k % 2 == 0 else 0.11) * size
            a = math.pi / 2 + k * math.pi / 5
            sv.append(sbm.verts.new((math.cos(a) * r, -0.004, math.sin(a) * r + 0.02 * size)))
        sf = sbm.faces.new(sv)
        ex = bmesh.ops.extrude_face_region(sbm, geom=[sf])
        for v in [e for e in ex["geom"] if isinstance(e, bmesh.types.BMVert)]:
            v.co.y -= 0.008
        sm = bpy.data.meshes.new(name + "_Star"); sbm.to_mesh(sm); sbm.free()
        so = link(bpy.data.objects.new(name + "_Star", sm))
        so.data.materials.append(simple_mat("Guard_StarMat", (0.98, 0.86, 0.45), 0.25, 0.9))
        o = join([o, so], name)
    return o


def duty_belt(info, cfg):
    z = 1.02
    pts = ring_around(info, z, 0.028, n=40, bvh=torso_bvh(info))
    belt = ring_mesh(cfg["tag"] + "_Belt", pts, 0.075, 0.022)
    belt.data.materials.append(simple_mat("Guard_BeltMat", cfg["belt"], 0.55))
    front = min(pts, key=lambda p: p.y)
    buckle = rounded_box(cfg["tag"] + "_Buckle", (0.055, 0.012, 0.04), bevel=0.008)
    buckle.location = V((0, front.y - 0.02, z)); buckle.data.materials.append(simple_mat("Guard_GoldMat", cfg["gold"], 0.3, 0.9))
    right = max(pts, key=lambda p: p.x)                 # the character's right hip (+X)
    left = min(pts, key=lambda p: p.x)
    radio = rounded_box(cfg["tag"] + "_Radio", (0.045, 0.03, 0.085), bevel=0.012)
    radio.location = right + V((0.035, -0.02, -0.02))
    ant = tube(cfg["tag"] + "_Antenna", [radio.location + V((0.02, 0, 0.08)), radio.location + V((0.02, 0, 0.19))], 0.009, sides=8)
    knob = tube(cfg["tag"] + "_Knob", [radio.location + V((-0.02, 0, 0.08)), radio.location + V((-0.02, 0, 0.11))], 0.012, sides=10)
    led = rounded_box(cfg["tag"] + "_Led", (0.012, 0.006, 0.008), bevel=0.003)
    led.location = radio.location + V((0, -0.033, 0.06))
    for o in (radio, ant, knob):
        o.data.materials.append(simple_mat("Guard_RadioMat", (0.12, 0.13, 0.14), 0.5))
    led.data.materials.append(simple_mat("Guard_LedMat", (0.2, 0.9, 0.35), 0.3, 0, emit=2.0))
    grille = rounded_box(cfg["tag"] + "_Grille", (0.032, 0.004, 0.035), bevel=0.003)
    grille.location = radio.location + V((0, -0.032, 0.0)); grille.data.materials.append(simple_mat("Guard_GrilleMat", (0.3, 0.31, 0.33), 0.6, 0.4))
    flash = tube(cfg["tag"] + "_Flashlight", [left + V((-0.035, -0.03, 0.05)), left + V((-0.035, -0.03, -0.12))], 0.022, sides=14)
    flash.data.materials.append(simple_mat("Guard_RadioMat", (0.12, 0.13, 0.14), 0.5))
    head = tube(cfg["tag"] + "_FlashHead", [left + V((-0.035, -0.03, -0.12)), left + V((-0.035, -0.03, -0.16))], 0.03, sides=16)
    head.data.materials.append(simple_mat("Guard_MetalMat", cfg["metal"], 0.25, 0.9))
    loops = [belt, buckle, radio, ant, knob, led, grille, flash, head]
    for o in loops:
        ctx_obj(o); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return join(loops, cfg["tag"] + "_DutyBelt")


def epaulettes_and_badges(info, cfg, shirt):
    sb = BVHTree.FromObject(shirt, bpy.context.evaluated_depsgraph_get())
    parts = []
    for s in (-1, 1):
        l, n, _, _ = sb.ray_cast(V((s * 0.26, 0.0, 2.3)), V((0, 0, -1)))
        if l is None:
            continue
        ep = rounded_box(cfg["tag"] + "_Ep", (0.07, 0.035, 0.008), bevel=0.006)
        ep.location = l + V((0, 0, 0.004)); ep.rotation_euler = (0, math.radians(s * 14), 0)
        ep.data.materials.append(simple_mat("Guard_CollarMat", cfg["shirt"], 0.75))
        stripe = rounded_box(cfg["tag"] + "_EpStripe", (0.012, 0.037, 0.009), bevel=0.003)
        stripe.location = l + V((s * 0.045, 0, 0.007)); stripe.rotation_euler = ep.rotation_euler
        stripe.data.materials.append(simple_mat("Guard_GoldMat", cfg["gold"], 0.3, 0.9))
        parts += [ep, stripe]
    # chest badge (character's left chest = -X) and an arm patch on the left sleeve
    l, n, _, _ = sb.ray_cast(V((-0.14, -1.5, 1.62)), V((0, 1, 0)))
    badge = shield(cfg["tag"] + "_Badge", 0.11)
    badge.location = l + V((0, -0.004, 0)); badge.rotation_euler = (0, 0, 0)
    parts.append(badge)
    l, n, _, _ = sb.ray_cast(V((-1.5, 0.0, 1.66)), V((1, 0, 0)))
    if l is not None:
        patch = shield(cfg["tag"] + "_Patch", 0.10)
        patch.location = l + V((-0.004, 0, 0)); patch.rotation_euler = (0, 0, math.radians(-90))
        parts.append(patch)
    for o in parts:
        ctx_obj(o); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return join(parts, cfg["tag"] + "_Insignia")


def build_guard():
    cfg = GUARD
    rig, body = load_character(cfg["base"], cfg["tag"])
    info = BodyInfo(body)
    shirt = uniform_shirt(info, cfg); weights_from_body(shirt, info, rig)
    col = collar(info, cfg); weights_from_body(col, info, rig)
    cap = guard_cap(info, cfg); weights_rigid(cap, rig, "Head")
    belt = duty_belt(info, cfg); weights_rigid(belt, rig, "Torso")
    ins = epaulettes_and_badges(info, cfg, shirt); weights_from_body(ins, info, rig)
    print("guard", [o.name for o in rig.children])
    return rig
