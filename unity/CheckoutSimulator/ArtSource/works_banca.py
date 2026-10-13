# works_banca.py - the "Banca de feira" construction works: the stall under construction (staged), a small flatbed lumber
# truck and a kit of carpentry site props.  Same family / pipeline as works_kit.py and works_kit2.py (metres, Blender Z up,
# one baked BaseColor atlas + one material per FBX, exported with checkout_project.export_unity which turns the roots
# 180 deg).  Conventions used here:
#   Works_BancaBuild : modelled like the Era models (customer side = Blender -Y -> Unity -Z), same model size as Era2_Banca
#                      (x1.2 game scale applied by the game).  Root objects Layout, Stage_0 .. Stage_5, each with its
#                      origin at its OWN base (bottom centre of its bounds) so the game can pop / scale it in from the ground.
#   Works_LumberTruck: like the works_kit vehicles (front = Blender +Y -> Unity +Z): Body (root) > Wheel_0..3 (front axle
#                      left/right, then rear), Load_0..3 (plank bundles, top row first; origin = bundle bottom centre).
#   Works_BancaKit   : like the works_kit2 kits: every item ONE root object laid side by side along X, found by name.
#                      Prop_PlankV2 origin = centre; the others origin = ground centre; worker side of the saw station = -Y.
# Wood: every board gets a "Grain" UV map (u along the board, v across) + a "Tint" UV map (per-board value) so one wood
# material gives real along-the-board grain, end grain on the cut faces and colour variation between boards whatever the
# board's orientation inside the joined stage object.  The atlas is baked on the default "UVMap"; Grain/Tint are removed
# from the export copies before the FBX is written.
#
#   import sys; sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
#   import works_banca as WB; WB.build_all()        # sources under the "Works_v3" collection (one child collection per FBX)
#   WB.previews()                                   # ArtSource/Review/banca_works/*.png (+ stages strip, scene mock, contact)
#   WB.export()                                     # export copies + atlas bake + FBX into Assets/Resources/CheckoutWorks
import bpy, bmesh, math, random, sys, os
sys.path.insert(0, r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource")
sys.path.insert(0, r"C:\Checkout-mobile\scripts\blender")
import era_kit as k, lot_kit as L, works_kit as W, checkout_project as cp
from mathutils import Vector, Matrix, Euler

ROOT_COL = "Works_v3"
EXPORT_COL = "Works_v3 Export"
OUT = W.OUT
REVIEW = r"C:\Checkout-mobile\unity\CheckoutSimulator\ArtSource\Review\banca_works"
MODELS = ["Works_BancaBuild", "Works_LumberTruck", "Works_BancaKit"]
SIZE = {"Works_BancaBuild": 2048, "Works_LumberTruck": 2048, "Works_BancaKit": 2048}
KIT = ["Prop_PlankV2", "Prop_PlankStackV2", "Prop_SawStation", "Prop_StepLadder", "Prop_TapeBarrier", "Prop_NailBucket",
       "Prop_Sawdust"]
KIT_SPACING = 4.5
STAGES = ["Layout", "Stage_0", "Stage_1", "Stage_2", "Stage_3", "Stage_4", "Stage_5"]
rad, T, Rx, Rz = W.rad, W.T, W.Rx, W.Rz
PI2 = math.pi / 2

def short(name): return name[len("Works_"):]
def src_col(name): return "W3 " + short(name)
def exp_col(name): return name + " Export"
objs_of, bounds = W.objs_of, W.bounds

# ------------------------------------------------------------------ collections
def show(*names):
    keep = set(names) | {"Studio", ROOT_COL, EXPORT_COL}
    def hit(lc):
        return lc.name in keep or any(hit(ch) for ch in lc.children)
    def walk(lc, parent_named):
        want = hit(lc) or parent_named
        lc.exclude = not want
        named = (lc.name in keep and lc.name not in (ROOT_COL, EXPORT_COL)) or parent_named
        for ch in lc.children:
            walk(ch, named)
    for _ in range(2):
        for ch in bpy.context.view_layer.layer_collection.children:
            walk(ch, False)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection

def new_col(name):
    c = W._attach(name, k.col(ROOT_COL))
    for o in list(c.objects):
        bpy.data.objects.remove(o)
    show(name)
    bpy.context.view_layer.active_layer_collection = W.lc_find(bpy.context.view_layer.layer_collection, name)
    bpy.context.scene.cursor.location = (0, 0, 0)
    return c

# ------------------------------------------------------------------ materials (WB_*)
PINE_L, PINE_D = (.91, .75, .48, 1), (.60, .41, .22, 1)      # fresh sawn lumber
OAK_L, OAK_D = (.84, .61, .33, 1), (.50, .32, .17, 1)         # posts / structural (era frame tone)
TEAL = (.094, .561, .525, 1); TEAL_D = (.09, .40, .36, 1); CREAM = (.957, .875, .643, 1)
NAVY = k.NAVY; ORANGE = (.93, .53, .18, 1)
M = {}

def reset_mats():
    M.clear()
    for m in list(bpy.data.materials):
        if m.name.startswith("WB_"): bpy.data.materials.remove(m)

def wood_uv(name, light, dark, scale=10.0, rough=.78, bump=.22, contrast=.85, tint=.14):
    """Wood driven by the 'Grain' UV map (bands along u, wobbly), brightness varied per board by the 'Tint' UV map."""
    m, nt = k._new(name)
    if nt is None:
        return m
    n, Lk = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = rough
    uv = n.new("ShaderNodeUVMap"); uv.uv_map = "Grain"
    wave = n.new("ShaderNodeTexWave"); wave.wave_type = 'BANDS'; wave.bands_direction = 'Y'; wave.wave_profile = 'SIN'
    wave.inputs["Scale"].default_value = scale; wave.inputs["Distortion"].default_value = 1.8
    wave.inputs["Detail"].default_value = 2.0; wave.inputs["Detail Scale"].default_value = 1.4
    wave.inputs["Detail Roughness"].default_value = .6
    Lk.new(uv.outputs[0], wave.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = .30; ramp.color_ramp.elements[0].color = light
    ramp.color_ramp.elements[1].position = .30 + .45 * contrast; ramp.color_ramp.elements[1].color = dark
    Lk.new(wave.outputs[0], ramp.inputs[0])
    # fine fibre streaks along the board (second wave, high frequency, low contrast)
    fib = n.new("ShaderNodeTexWave"); fib.wave_type = 'BANDS'; fib.bands_direction = 'Y'
    fib.inputs["Scale"].default_value = scale * 6; fib.inputs["Distortion"].default_value = .6; fib.inputs["Detail"].default_value = 1
    Lk.new(uv.outputs[0], fib.inputs["Vector"])
    fr = n.new("ShaderNodeMapRange"); fr.inputs["To Min"].default_value = .94; fr.inputs["To Max"].default_value = 1.04
    Lk.new(fib.outputs[0], fr.inputs[0])
    mulf = n.new("ShaderNodeMix"); mulf.data_type = 'RGBA'; mulf.blend_type = 'MULTIPLY'; mulf.inputs[0].default_value = 1
    Lk.new(ramp.outputs[0], mulf.inputs[6]); Lk.new(fr.outputs[0], mulf.inputs[7])
    # per-board tint
    tuv = n.new("ShaderNodeUVMap"); tuv.uv_map = "Tint"
    sep = n.new("ShaderNodeSeparateXYZ"); Lk.new(tuv.outputs[0], sep.inputs[0])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 1 - tint; mr.inputs["To Max"].default_value = 1 + tint
    Lk.new(sep.outputs[0], mr.inputs[0])
    mul = n.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1
    Lk.new(mulf.outputs[2], mul.inputs[6]); Lk.new(mr.outputs[0], mul.inputs[7])
    # warm / cool hue drift with the tint value
    hue = n.new("ShaderNodeMix"); hue.data_type = 'RGBA'; hue.blend_type = 'MULTIPLY'
    hue.inputs[6].default_value = (1, 1, 1, 1); hue.inputs[7].default_value = (1.04, .96, .88, 1)
    Lk.new(sep.outputs[1], hue.inputs[0])
    out = n.new("ShaderNodeMix"); out.data_type = 'RGBA'; out.blend_type = 'MULTIPLY'; out.inputs[0].default_value = 1
    Lk.new(mul.outputs[2], out.inputs[6]); Lk.new(hue.outputs[2], out.inputs[7])
    Lk.new(out.outputs[2], bsdf.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump
    Lk.new(wave.outputs[0], b.inputs["Height"]); Lk.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m

def endgrain(name, light, dark):
    """Cut face of a board: concentric-ish rings from the Grain v coordinate, darker and rougher."""
    m, nt = k._new(name)
    if nt is None:
        return m
    n, Lk = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = .9
    uv = n.new("ShaderNodeUVMap"); uv.uv_map = "Grain"
    wave = n.new("ShaderNodeTexWave"); wave.wave_type = 'RINGS'; wave.rings_direction = 'X'
    wave.inputs["Scale"].default_value = 18; wave.inputs["Distortion"].default_value = 1.2; wave.inputs["Detail"].default_value = 2
    Lk.new(uv.outputs[0], wave.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = .3; ramp.color_ramp.elements[0].color = light
    ramp.color_ramp.elements[1].position = .8; ramp.color_ramp.elements[1].color = dark
    Lk.new(wave.outputs[0], ramp.inputs[0])
    dk = n.new("ShaderNodeMix"); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'; dk.inputs[0].default_value = 1
    Lk.new(ramp.outputs[0], dk.inputs[6]); dk.inputs[7].default_value = (.88, .84, .78, 1)
    Lk.new(dk.outputs[2], bsdf.inputs["Base Color"])
    return m

def mats():
    if M:
        return M
    M.update(W.mats())
    M["pine"] = wood_uv("WB_Pine", PINE_L, PINE_D, scale=12, tint=.22)
    M["pineEnd"] = endgrain("WB_PineEnd", PINE_L, PINE_D)
    M["oak"] = wood_uv("WB_Oak", OAK_L, OAK_D, scale=9, tint=.16, contrast=1.0)
    M["oakEnd"] = endgrain("WB_OakEnd", OAK_L, OAK_D)
    M["deck"] = wood_uv("WB_Deck", (.74, .57, .36, 1), (.42, .29, .16, 1), scale=9, tint=.18, rough=.85)
    M["deckEnd"] = endgrain("WB_DeckEnd", (.72, .56, .36, 1), (.48, .34, .20, 1))
    M["nail"] = k.mat("WB_Nail", (.50, .52, .54, 1), rough=.45, var=.05, scale=8, metallic=.5)
    M["footing"] = k.mat("WB_Footing", (.70, .68, .63, 1), rough=.95, var=.16, scale=14, bump=.5)
    M["chalk"] = k.mat("WB_Chalk", (.97, .97, .95, 1), rough=.95, var=.10, scale=30)
    M["line"] = k.mat("WB_MasonLine", (.96, .36, .60, 1), rough=.7, var=.05)
    M["awning"] = k.stripes("WB_Awning", NAVY, k.CREAM, width=.14, axis='X')
    M["navy"] = k.mat("WB_Navy", NAVY, rough=.6, var=.05, scale=5)
    M["gold"] = k.mat("WB_Gold", k.GOLD, rough=.5, var=.05, scale=5)
    M["teal"] = k.mat("WB_Teal", TEAL, rough=.5, var=.06, scale=5)
    M["tealD"] = k.mat("WB_TealDark", TEAL_D, rough=.55, var=.06, scale=5)
    M["cream"] = k.mat("WB_Cream", CREAM, rough=.55, var=.05, scale=5)
    M["orange"] = k.mat("WB_Orange", ORANGE, rough=.55, var=.06, scale=5)
    M["strap"] = k.mat("WB_Strap", (.12, .12, .13, 1), rough=.6, var=.05)
    M["strapO"] = k.mat("WB_StrapOrange", (.95, .45, .10, 1), rough=.6, var=.05)
    M["alu"] = k.mat("WB_Alu", (.70, .72, .75, 1), rough=.35, var=.06, scale=8, metallic=.5)
    M["rubber"] = k.mat("WB_Rubber", (.14, .14, .15, 1), rough=.9, var=.04)
    M["sawdust"] = k.mat("WB_Sawdust", (.90, .78, .50, 1), rough=.95, var=.18, scale=40, bump=.6)
    M["tape"] = k.stripes("WB_CautionTape", (.86, .16, .12, 1), (.96, .95, .92, 1), width=.10, axis='X')
    M["leather"] = k.mat("WB_Leather", (.52, .34, .20, 1), rough=.8, var=.08, scale=10)
    M["leatherD"] = k.mat("WB_LeatherDark", (.36, .23, .14, 1), rough=.8, var=.08, scale=10)
    M["yellow"] = W.mats()["yellow"]
    M["red"] = W.mats()["red"]
    M["bucket"] = k.mat("WB_Bucket", (.66, .68, .70, 1), rough=.45, var=.07, scale=8, metallic=.4)
    M["plate"] = k.mat("WB_Plate", (.92, .92, .88, 1), rough=.5, var=.03)
    M["amber"] = k.mat("WB_Amber", (1.0, .62, .10, 1), rough=.3, var=.03)
    return M

# ------------------------------------------------------------------ wood geometry helpers
_seed = [0]
def grain_uv(o, axis, seed=None):
    """'Grain' UV (u along `axis`, v across) + 'Tint' UV (per-board random) on a freshly made primitive; cut faces -> slot 1."""
    me = o.data
    g = me.uv_layers.get("Grain") or me.uv_layers.new(name="Grain")
    t = me.uv_layers.get("Tint") or me.uv_layers.new(name="Tint")
    a1, a2 = [i for i in range(3) if i != axis]
    _seed[0] += 1
    rnd = random.Random(seed if seed is not None else _seed[0])
    off = rnd.uniform(0, 20); tint = rnd.random(); tint2 = rnd.random()
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            g.data[li].uv = (co[axis] + off * .37, co[a1] + .63 * co[a2] + off)
            t.data[li].uv = (tint, tint2)
        if len(me.materials) > 1 and abs(poly.normal[axis]) > .9:
            poly.material_index = 1
    me.uv_layers.active_index = 0
    return o

def board(name, size, loc, rot=(0, 0, 0), m="pine", bevel=.004, seg=1, axis=None, c=None):
    """Lumber: box with grain along its longest dimension (or `axis`), end grain on the cut faces."""
    M_ = mats()
    o = k.box(name, size, loc, M_[m], rot=rot, bevel=bevel, seg=seg, c=c)
    o.data.materials.append(M_[m + "End"])
    ax = axis if axis is not None else max(range(3), key=lambda i: size[i])
    return grain_uv(o, ax)

def bar(name, a, b, w, h, m="pine", bevel=.004, seg=1, c=None):
    """Board from point a to point b (any direction), cross-section w x h; grain along the board."""
    a, b = Vector(a), Vector(b); d = b - a
    o = board(name, (w, h, d.length), (a + b) / 2, m=m, bevel=bevel, seg=seg, axis=2, c=c)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o

def nails(p, name, pts, r=.009, axis='Z', M_=None):
    """Nail heads (flat 6-sided discs) at pts, flat side facing `axis` (+X/+Y/+Z or -X/-Y/-Z)."""
    M_ = M_ or mats()
    rot = {'Z': (0, 0, 0), 'Y': (PI2, 0, 0), 'X': (0, PI2, 0)}[axis[-1]]
    for pt in pts:
        p.append(k.cyl(name + "_n", r, .006, pt, M_["nail"], rot=rot, verts=6, bevel=0))

def bundle_size(n_w=3, n_h=4, bw=.18, bh=.045, gap=.012):
    return n_w * bw + (n_w - 1) * gap, n_h * bh + (n_h - 1) * gap

def plank_bundle(name, loc, M_=None, n_w=3, n_h=4, L_=2.4, bw=.18, bh=.045, gap=.012, straps=(-.8, .8), m="pine", bevel=.004):
    """Bundle of planks (long axis Y) with two straps; `loc` = bottom centre. Returns objs + size (w, h)."""
    M_ = M_ or mats(); x0, y0, z0 = loc; p = []
    wtot = n_w * bw + (n_w - 1) * gap; htot = n_h * bh + (n_h - 1) * gap
    rnd = random.Random(sum(map(ord, name)))
    for i in range(n_w):
        for j in range(n_h):
            x = x0 - wtot / 2 + bw / 2 + i * (bw + gap); z = z0 + bh / 2 + j * (bh + gap)
            dy = rnd.uniform(-.03, .03)
            p.append(board(name + "_pl", (bw, L_, bh), (x, y0 + dy, z), m=m, bevel=bevel))
    for sy in straps:
        p.append(k.box(name + "_s1", (wtot + .02, .035, .006), (x0, y0 + sy, z0 + htot + .004), M_["strapO"], bevel=0))
        p.append(k.box(name + "_s2", (wtot + .02, .035, .006), (x0, y0 + sy, z0 - .003), M_["strapO"], bevel=0))
        for sx in (-1, 1):
            p.append(k.box(name + "_s3", (.006, .035, htot + .012), (x0 + sx * (wtot / 2 + .006), y0 + sy, z0 + htot / 2), M_["strapO"], bevel=0))
        p.append(k.box(name + "_buckle", (.05, .045, .016), (x0 + wtot * .2, y0 + sy, z0 + htot + .01), M_["dsteel"], bevel=.003))
    return p, (wtot, htot)

def bx(name, size, loc, m=None, rot=(0, 0, 0), bevel=.008, seg=1, c=None):
    """k.box with a 1-segment bevel by default (soft edge, half the triangles)."""
    return k.box(name, size, loc, m, rot=rot, bevel=bevel, seg=seg, c=c)

def stats(name):
    """Per root object: dims, origin-relative lo/hi, origin, tris."""
    objs = objs_of(src_col(name)); dg = bpy.context.evaluated_depsgraph_get(); out = {}
    for o in objs:
        lo, hi = bounds([o]); off = o.matrix_world.translation
        out[o.name.split(".", 1)[1]] = {"dims": [round(v, 2) for v in (hi - lo)], "origin": [round(v, 3) for v in off],
                                        "lo": [round(v, 2) for v in (lo - off)], "hi": [round(v, 2) for v in (hi - off)],
                                        "parent": o.parent.name.split(".", 1)[1] if o.parent else None,
                                        "tris": len(o.evaluated_get(dg).data.loop_triangles)}
    out["_total_tris"] = sum(v["tris"] for v in out.values() if isinstance(v, dict))
    return out

def stage(N, name, p, c, pivot=None):
    """Join `p` into one root object whose origin is its own base (bottom centre of its bounds) unless `pivot` is given."""
    bpy.context.view_layer.update()
    if pivot is None:
        lo, hi = bounds(p); pivot = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)
    return W.part(N + name, p, pivot, None, c)

# ================================================================== Works_BancaBuild
# Era2_Banca (model metres, front = -Y): posts x +-1.65, back y +.92 (2.40 high), front y -.95 (2.76 high, carry the sign);
# awning z 2.42 (back) -> 2.16 (front) with a valance to 1.99 at y -1.23; counter x +-1.42, y -.75 .. +.04, 0.88 high.
PX, YB, YF, HB, HF = 1.65, .92, -.95, 2.40, 2.76
CX, CY0, CY1, CH = 1.42, -.75, .04, .88

def build_banca_build(name="Works_BancaBuild"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    rnd = random.Random(3)
    # ---------------- Layout: corner stakes, mason line, chalk marks
    p = []
    SX, SY = PX + .22, 1.17
    for sx in (-1, 1):
        for sy in (-1, 1):
            st = board(N + "stake", (.03, .03, .42), (sx * SX, sy * SY, .14), m="pine", bevel=.002,
                       rot=(rad(rnd.uniform(-5, 5)), rad(rnd.uniform(-5, 5)), 0))
            p.append(st)
            p.append(k.cyl(N + "stkTop", .013, .008, (sx * SX, sy * SY, .35), M_["nail"], verts=6, bevel=0))
    z = .30
    for (a, b) in [((-SX, -SY), (SX, -SY)), ((-SX, SY), (SX, SY)), ((-SX, -SY), (-SX, SY)), ((SX, -SY), (SX, SY))]:
        p.append(k.tube(N + "line", (a[0], a[1], z), (b[0], b[1], z), .006, M_["line"], verts=5))
    # chalk outline of the post lines (dashed) + crosses on the post positions + counter line
    def dash(a, b, n_):
        a, b = Vector(a), Vector(b)
        for i in range(n_):
            t0, t1 = (i + .1) / n_, (i + .8) / n_
            q0, q1 = a.lerp(b, t0), a.lerp(b, t1)
            p.append(bx(N + "chalk", (.025, (q1 - q0).length, .008), ((q0 + q1) / 2).to_tuple(), M_["chalk"],
                           rot=(0, 0, math.atan2((q1 - q0).y, (q1 - q0).x) + PI2), bevel=0))
    for sx in (-1, 1):
        dash((sx * PX, YF, .004), (sx * PX, YB, .004), 9)
    dash((-PX, YF, .004), (PX, YF, .004), 14); dash((-PX, YB, .004), (PX, YB, .004), 14)
    dash((-CX, CY0, .004), (CX, CY0, .004), 12)
    for sx in (-1, 1):
        for y in (YF, YB):
            for ang in (45, -45):
                p.append(bx(N + "cross", (.03, .22, .008), (sx * PX, y, .005), M_["chalk"], rot=(0, 0, rad(ang)), bevel=0))
    stage(N, "Layout", p, c, pivot=(0, 0, 0))
    # ---------------- Stage_0: posts on footings + temporary braces
    p = []
    for sx in (-1, 1):
        for y, h in ((YB, HB), (YF, HF)):
            p.append(k.cyl(N + "foot", .17, .14, (sx * PX, y, .07), M_["footing"], verts=12, bevel=.02, seg=2, r2=.15))
            p.append(board(N + "post", (.10, .10, h - .12), (sx * PX, y, .12 + (h - .12) / 2), m="oak", bevel=.008, seg=2, axis=2))
            p.append(bx(N + "bracket", (.13, .13, .05), (sx * PX, y, .145), M_["dsteel"], bevel=.004))
        # side diagonal (front top -> back foot), just inside the post line
        p.append(bar(N + "braceS", (sx * (PX - .09), YF + .05, 2.05), (sx * (PX - .09), YB - .05, .35), .025, .09, m="pine"))
        # kicker brace outward from the front post to a stake
        kx = sx * (PX + .62)
        p.append(bar(N + "kick", (sx * (PX + .06), YF, 1.15), (kx, YF, .12), .025, .09, m="pine"))
        p.append(board(N + "kstake", (.04, .04, .45), (kx + sx * .03, YF, .17), m="pine", bevel=.002, rot=(0, rad(-sx * 8), 0)))
        nails(p, N, [(sx * (PX - .09 + sx * .013), YF + .12, 1.95), (sx * (PX - .09 + sx * .013), YB - .12, .45),
                     (sx * (PX + .07), YF + .015, 1.30), (sx * (PX + .07), YF - .015, 1.30)], axis='X')
    # one brace across the back (temporary)
    p.append(bar(N + "braceB", (-PX + .1, YB - .06, .35), (PX - .1, YB - .06, 2.05), .025, .09, m="pine"))
    stage(N, "Stage_0", p, c)
    # ---------------- Stage_1: counter base frame + side / back rails at counter height
    p = []
    ZT = CH - .05
    for sx in (-1, 1):
        for y in (CY0 + .04, CY1 - .04):
            p.append(board(N + "cpost", (.08, .08, ZT), (sx * (CX - .04), y, ZT / 2), m="oak", bevel=.005, axis=2))
        p.append(board(N + "ctopY", (.06, CY1 - CY0 - .16, .08), (sx * (CX - .04), (CY0 + CY1) / 2, ZT - .04), m="pine"))
        p.append(board(N + "cbotY", (.06, CY1 - CY0 - .16, .08), (sx * (CX - .04), (CY0 + CY1) / 2, .12), m="pine"))
    for y in (CY0 + .04, CY1 - .04):
        p.append(board(N + "ctopX", (2 * CX - .16, .06, .08), (0, y, ZT - .04), m="pine"))
        p.append(board(N + "cbotX", (2 * CX - .16, .06, .08), (0, y, .12), m="pine"))
    for x in (-.95, -.32, .32, .95):            # floor joists + top ribs
        p.append(board(N + "joist", (.05, CY1 - CY0 - .16, .08), (x, (CY0 + CY1) / 2, .12), m="pine"))
        p.append(board(N + "rib", (.05, CY1 - CY0 - .16, .08), (x, (CY0 + CY1) / 2, ZT - .04), m="pine"))
    p.append(board(N + "midrail", (2 * CX - .16, .05, .06), (0, CY0 + .04, ZT * .55), m="pine"))
    for sx in (-1, 1):                          # rails between the main posts at counter height (side bays)
        p.append(board(N + "sideRail", (.06, YB - YF - .10, .10), (sx * PX, (YB + YF) / 2, CH), m="pine"))
    p.append(board(N + "backRail", (2 * PX - .10, .06, .10), (0, YB, CH), m="pine"))
    for sx in (-1, 1):
        nails(p, N, [(sx * (CX - .04 + sx * .031), CY0 + .04, ZT - .04), (sx * (CX - .04 + sx * .031), CY1 - .04, ZT - .04),
                     (sx * (PX + sx * .031), YF + .12, CH), (sx * (PX + sx * .031), YB - .12, CH)], axis='X')
    stage(N, "Stage_1", p, c)
    # ---------------- Stage_2: counter top boards + front panel boards + side panels
    p = []
    nb = 4; bw = (CY1 - CY0 + .06) / nb
    for i in range(nb):
        y = CY0 - .03 + bw * (i + .5)
        p.append(board(N + "top", (2 * CX + .06, bw - .012, .032), (0, y, CH - .016 + rnd.uniform(-.003, .003)), m="pine", bevel=.005))
        nails(p, N, [(x, y, CH + .003) for x in (-CX + .08, -.95, -.32, .32, .95, CX - .08)], axis='Z')
    p.append(board(N + "nosing", (2 * CX + .06, .035, .06), (0, CY0 - .035, CH - .03), m="oak", bevel=.004))
    nvb = 19; vw = (2 * CX) / nvb
    for i in range(nvb):
        x = -CX + vw * (i + .5)
        p.append(board(N + "front", (vw - .008, .02, ZT - .10), (x, CY0 - .01, .10 + (ZT - .10) / 2 + rnd.uniform(-.004, .004)), m="pine", bevel=.003, axis=2))
        nails(p, N, [(x, CY0 - .022, .16), (x, CY0 - .022, ZT - .10)], axis='Y', r=.008)
    for sx in (-1, 1):
        nsb = 5; sw = (CY1 - CY0) / nsb
        for i in range(nsb):
            y = CY0 + sw * (i + .5)
            p.append(board(N + "sideB", (.02, sw - .008, ZT - .10), (sx * (CX + .01), y, .10 + (ZT - .10) / 2), m="pine", bevel=.003, axis=2))
            nails(p, N, [(sx * (CX + .022), y, .16), (sx * (CX + .022), y, ZT - .10)], axis='X', r=.008)
    stage(N, "Stage_2", p, c)
    # ---------------- Stage_3: back / side slats + tiered produce rack on the counter
    p = []
    for z in (1.02, 1.20, 1.38):
        p.append(board(N + "backSlat", (2 * PX - .12, .02, .12), (0, YB - .06, z), m="pine", bevel=.003))
        nails(p, N, [(x, YB - .072, z) for x in (-PX + .10, 0, PX - .10)], axis='Y', r=.008)
        for sx in (-1, 1):
            p.append(board(N + "sideSlat", (.02, YB - YF - .12, .12), (sx * (PX - .06), (YB + YF) / 2, z), m="pine", bevel=.003))
            nails(p, N, [(sx * (PX - .072), y, z) for y in (YF + .10, YB - .10)], axis='X', r=.008)
    # a shelf board on the back rail + two brackets
    p.append(board(N + "shelf", (2 * PX - .20, .28, .03), (0, YB - .20, 1.50), m="pine", bevel=.004))
    for x in (-PX + .25, 0, PX - .25):
        p.append(bar(N + "shelfBr", (x, YB - .07, 1.25), (x, YB - .30, 1.47), .03, .05, m="pine"))
    # produce rack: tilted slatted tray on the counter (era: y -.68 .. -.1, z .88 .. 1.08, 20 deg)
    R_ = T((0, -.39, CH + .02)) @ Rx(-20)
    q = [board(N + "rackRail", (2 * CX - .16, .04, .06), (0, -.26, .05), m="oak", bevel=.004),
         board(N + "rackRail2", (2 * CX - .16, .04, .04), (0, .26, .04), m="oak", bevel=.004)]
    for i in range(6):
        q.append(board(N + "rackSlat", (2 * CX - .16, .065, .02), (0, -.24 + i * .094, .01), m="pine", bevel=.003))
    for x in (-CX + .08, -.53 * CX, 0, .53 * CX, CX - .08):
        q.append(board(N + "rackDiv", (.035, .56, .07), (x, 0, .055), m="oak", bevel=.003))
    p += W.place(q, R_)
    for sx in (-1, 1):
        p.append(bar(N + "rackLeg", (sx * (CX - .10), -.18, CH + .005), (sx * (CX - .10), -.18, CH + .17), .035, .035, m="oak"))
    stage(N, "Stage_3", p, c)
    # ---------------- Stage_4: top plates, rafters, purlins
    p = []
    p.append(board(N + "plateB", (2 * PX + .24, .10, .14), (0, YB, HB - .07), m="oak", bevel=.006))
    p.append(board(N + "plateF", (2 * PX + .24, .10, .14), (0, YF, HF - .60 - .07), m="oak", bevel=.006))
    zb, zf = HB, HF - .60          # rafter underside at the back / front plates
    for x in (-PX - .04, -PX * .6, -PX * .2, PX * .2, PX * .6, PX + .04):
        p.append(bar(N + "rafter", (x, YB + .08, zb + .06), (x, YF - .28, zf + .06 - .02), .06, .12, m="pine", bevel=.004))
    slope = (zb - zf) / (YB - YF)
    for y in (YB - .55, YF + .55):
        zz = zf + (y - YF) * slope + .16
        p.append(board(N + "purlin", (2 * PX + .12, .06, .05), (0, y, zz), m="pine", bevel=.003))
        nails(p, N, [(x, y, zz + .026) for x in (-PX - .04, -PX * .6, -PX * .2, PX * .2, PX * .6, PX + .04)], axis='Z', r=.008)
    for sx in (-1, 1):   # knee braces post -> plate
        p.append(bar(N + "knee", (sx * (PX - .07), YB - .05, HB - .55), (sx * (PX - .07), YB - .45, HB - .10), .03, .07, m="pine"))
        p.append(bar(N + "kneeF", (sx * (PX - .07), YF + .05, zf - .55), (sx * (PX - .07), YF + .45, zf - .10), .03, .07, m="pine"))
    stage(N, "Stage_4", p, c)
    # ---------------- Stage_5: striped awning + sign board
    p = []
    ya, yf = YB + .01, YF - .28
    za, zfz = HB + .12 + .105, HF - .60 + .12 - .02 + .105
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=26, y_subdivisions=5, size=1.0, location=(0, (ya + yf) / 2, (za + zfz) / 2))
    aw = bpy.context.active_object; aw.name = N + "canvas"
    aw.scale = (2 * PX + .22, ya - yf, 1); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    sp = PX * .4                                   # rafter spacing: sag between the rafters
    for v in aw.data.vertices:
        v.co.z = -.03 * math.sin(math.pi * (v.co.x - PX * .2) / sp) ** 2
    aw.rotation_euler = (math.atan2(za - zfz, ya - yf), 0, 0)
    aw.data.materials.append(M_["awning"])
    so = aw.modifiers.new("Solidify", 'SOLIDIFY'); so.thickness = .022; so.offset = 0
    for pg in aw.data.polygons: pg.use_smooth = True
    p.append(aw)
    val = bx(N + "valance", (2 * PX + .22, .02, .17), (0, yf + .01, zfz - .085), M_["awning"], bevel=0)
    p.append(val)
    for sx in (-1, 1):   # side valances
        p.append(bx(N + "valS", (.02, ya - yf, .12), (sx * (PX + .10), (ya + yf) / 2, (za + zfz) / 2 - .06), M_["awning"],
                       rot=(math.atan2(za - zfz, ya - yf), 0, 0), bevel=0))
    p.append(board(N + "valBar", (2 * PX + .26, .04, .04), (0, yf, zfz - .19), m="oak", bevel=.004))
    # sign board on the front posts (era: y -1.0, z 2.48 .. 2.96, x +-1.13)
    sy, sz0, sz1, sw = YF - .07, HF - .28, HF + .20, 1.13
    p.append(bx(N + "sign", (2 * sw, .035, sz1 - sz0), (0, sy, (sz0 + sz1) / 2), M_["navy"], bevel=.004))
    p.append(board(N + "signT", (2 * sw + .10, .05, .05), (0, sy, sz1 + .02), m="oak", bevel=.004))
    p.append(board(N + "signB", (2 * sw + .10, .05, .05), (0, sy, sz0 - .02), m="oak", bevel=.004))
    for sx in (-1, 1):
        p.append(board(N + "signS", (.05, .05, sz1 - sz0 + .08), (sx * (sw + .025), sy, (sz0 + sz1) / 2), m="oak", bevel=.004, axis=2))
    p.append(k.text(N + "signTxt", "BANCA", .30, (0, sy - .02, (sz0 + sz1) / 2 - .01), M_["cream"], rot=(PI2, 0, 0), extrude=.006, res=2))
    stage(N, "Stage_5", p, c)
    return stats(name)

# ================================================================== Works_LumberTruck (front = +Y)
def build_lumber_truck(name="Works_LumberTruck"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    Tl, Cr, D, S, G, B, Ch = M_["teal"], M_["cream"], M_["dsteel"], M_["steel"], M_["glass"], M_["black"], M_["chrome"]
    Wd = 1.92; p = []
    # chassis
    for sx in (-1, 1):
        p.append(bx(N + "rail", (.10, 4.7, .16), (sx * .52, .05, .58), D, bevel=.01))
    for y in (-2.2, -1.2, -.2, .8, 1.9):
        p.append(bx(N + "xm", (1.1, .08, .12), (0, y, .58), D, bevel=0))
    p.append(k.cyl(N + "tank", .20, .9, (-.85, -.1, .62), S, rot=(PI2, 0, 0), verts=12, bevel=.02))
    p.append(bx(N + "battery", (.35, .4, .3), (.85, -.1, .72), B, bevel=.02))
    p.append(k.cyl(N + "spare", .36, .22, (0, -1.95, .50), M_["tire"], verts=14, bevel=.04, seg=2))
    p.append(k.cyl(N + "spareRim", .22, .24, (0, -1.95, .50), M_["rim"], verts=10))
    # ---- cab-over cab
    y0, y1, z0, z1 = 1.05, 2.50, .78, 2.12
    L_ = y1 - y0; h = z1 - z0; yc = (y0 + y1) / 2; zc = (z0 + z1) / 2
    p.append(bx(N + "cab", (Wd, L_, h), (0, yc, zc), Tl, bevel=.12, seg=2))
    p.append(bx(N + "roof", (Wd - .06, L_ - .06, .10), (0, yc, z1 + .02), Cr, bevel=.04, seg=2))
    p.append(bx(N + "visor", (Wd - .16, .22, .035), (0, y1 - .02, z1 - .06), Cr, bevel=.01))
    p.append(bx(N + "ws", (Wd - .34, .06, h * .40), (0, y1 - .005, z0 + h * .66), G, bevel=.02))
    p.append(bx(N + "wsFrame", (Wd - .26, .03, h * .44), (0, y1 - .02, z0 + h * .66), B, bevel=.01))
    p.append(bx(N + "rw", (Wd - .5, .05, h * .30), (0, y0 + .005, z0 + h * .68), G, bevel=.01))
    p.append(bx(N + "stripe", (Wd + .02, L_ - .10, .14), (0, yc, z0 + h * .36), Cr, bevel=.005))
    p.append(bx(N + "grille", (Wd * .55, .05, h * .14), (0, y1 + .01, z0 + h * .22), B, bevel=.01))
    for i in range(3):
        p.append(bx(N + "slat", (Wd * .52, .02, .02), (0, y1 + .035, z0 + h * .16 + i * .045), Ch, bevel=0))
    p.append(bx(N + "bumper", (Wd + .12, .20, .20), (0, y1 - .04, z0 - .12), Ch, bevel=.05, seg=2))
    p.append(bx(N + "bumperB", (Wd + .14, .22, .06), (0, y1 - .05, z0 - .21), B, bevel=.01))
    p.append(bx(N + "plate", (.36, .02, .12), (0, y1 + .07, z0 - .12), M_["plate"], bevel=.003))
    p.append(bx(N + "ucab", (Wd - .5, L_ - .25, .35), (0, yc, z0 - .15), D, bevel=.02))
    for sx in (-1, 1):
        p.append(bx(N + "sw", (.06, L_ * .42, h * .34), (sx * Wd / 2, y0 + L_ * .56, z0 + h * .66), G, bevel=.015))
        p.append(bx(N + "swFrame", (.03, L_ * .46, h * .38), (sx * (Wd / 2 - .01), y0 + L_ * .56, z0 + h * .66), B, bevel=.01))
        p.append(bx(N + "doorLine", (.02, .012, h * .78), (sx * (Wd / 2 + .003), y0 + L_ * .34, z0 + h * .45), M_["tealD"], bevel=0))
        p.append(bx(N + "handle", (.03, .12, .025), (sx * (Wd / 2 + .02), y0 + L_ * .42, z0 + h * .44), Ch, bevel=.005))
        p.append(k.cyl(N + "hl", .11, .06, (sx * (Wd / 2 - .28), y1 + .02, z0 + h * .30), M_["light"], rot=(PI2, 0, 0), verts=12, bevel=.01))
        p.append(k.cyl(N + "hlRing", .13, .035, (sx * (Wd / 2 - .28), y1 + .01, z0 + h * .30), Ch, rot=(PI2, 0, 0), verts=12, bevel=.005))
        p.append(bx(N + "ind", (.12, .04, .06), (sx * (Wd / 2 - .10), y1 + .01, z0 + h * .30), M_["amber"], bevel=.008))
        W.mirror(p, N + "_m", (sx * (Wd / 2 + .10), y1 - .18, z0 + h * .62), sx, M_, h=.36)
        p.append(bx(N + "step", (.30, .5, .04), (sx * (Wd / 2 - .02), y0 + .45, z0 - .30), D, bevel=.005))
        p.append(bx(N + "stepBar", (.03, .5, .25), (sx * (Wd / 2 - .15), y0 + .45, z0 - .17), D, bevel=0))
    W.beacon(p, N, (-.45, yc - .2, z1 + .07), M_, r=.06, h=.10)
    p.append(bx(N + "wiper", (.55, .02, .02), (-.25, y1 + .035, z0 + h * .49), B, bevel=0, rot=(0, 0, rad(-20))))
    # ---- flatbed with wooden deck and stake sides
    by0, by1, zd = -2.42, .92, .98
    p.append(bx(N + "bedFrame", (Wd, by1 - by0, .10), (0, (by0 + by1) / 2, zd - .05), D, bevel=.01))
    nd = 8; dw = (Wd - .06) / nd
    for i in range(nd):
        x = -(Wd - .06) / 2 + dw * (i + .5)
        p.append(board(N + "deck", (dw - .008, by1 - by0 - .04, .03), (x, (by0 + by1) / 2, zd + .015), m="deck", bevel=.003))
    for sx in (-1, 1):
        p.append(bx(N + "sideRail", (.05, by1 - by0, .12), (sx * (Wd / 2 - .025), (by0 + by1) / 2, zd), D, bevel=.005))
        for y in (by0 + .20, by0 + 1.05, by0 + 1.85, by1 - .25):
            p.append(bx(N + "pocket", (.09, .11, .22), (sx * (Wd / 2 + .02), y, zd - .03), D, bevel=.004))
            p.append(board(N + "stake", (.055, .055, .78), (sx * (Wd / 2 + .02), y, zd + .34), m="deck", bevel=.003, axis=2))
        for z in (zd + .32, zd + .62):
            p.append(board(N + "sideBoard", (.025, by1 - by0 - .10, .14), (sx * (Wd / 2 + .06), (by0 + by1) / 2, z), m="deck", bevel=.003))
            nails(p, N, [(sx * (Wd / 2 + .074), y, z) for y in (by0 + .20, by0 + 1.05, by0 + 1.85, by1 - .25)], axis='X', r=.008)
        p.append(bx(N + "mud", (.56, 1.30, .06), (sx * .80, -1.45, .895), D, bevel=.01))
        p.append(bx(N + "mudF", (.56, .08, .35), (sx * .80, -1.45 + .65, .76), D, bevel=.005, rot=(rad(-30), 0, 0)))
        p.append(bx(N + "mudB", (.56, .08, .35), (sx * .80, -1.45 - .65, .76), D, bevel=.005, rot=(rad(30), 0, 0)))
        p.append(bx(N + "flap", (.42, .02, .28), (sx * .80, -2.15, .50), M_["rubber"], bevel=.004))
        p.append(bx(N + "tl", (.14, .04, .22), (sx * (Wd / 2 - .12), by0 - .02, zd - .22), M_["tail"], bevel=.008))
    for x in (-.60, 0, .60):      # headboard stakes + boards
        p.append(board(N + "hstake", (.055, .055, .95), (x, by1 - .03, zd + .42), m="deck", bevel=.003, axis=2))
        p.append(bx(N + "hpocket", (.11, .09, .22), (x, by1 - .03, zd - .03), D, bevel=.004))
    for z in (zd + .32, zd + .62, zd + .86):
        p.append(board(N + "hboard", (Wd - .10, .025, .14), (0, by1 - .07, z), m="deck", bevel=.003))
        nails(p, N, [(x, by1 - .084, z) for x in (-.60, 0, .60)], axis='Y', r=.008)
    p.append(bx(N + "rearBar", (Wd, .08, .10), (0, by0 + .02, zd - .25), D, bevel=.005))
    p.append(bx(N + "rplate", (.34, .02, .11), (0, by0 - .06, zd - .25), M_["plate"], bevel=.003))
    p.append(bx(N + "rearStripe", (Wd - .5, .03, .08), (0, by0 - .02, zd - .36), M_["hazardR"], bevel=0))
    body = W.part(N + "Body", p, (0, 0, 0), None, c)
    for i, (x, y) in enumerate([(-.80, 1.72), (.80, 1.72), (-.80, -1.45), (.80, -1.45)]):
        W.wheel(N + f"Wheel_{i}", (x, y, .42), .42, .26, body, c, verts=16)
    # ---- lumber: 4 strapped bundles, 2 across x 2 high (Load_0 / Load_1 on top)
    ly = (by0 + by1) / 2 - .12; z_lo = zd + .03
    bw, bh = bundle_size(4, 3)
    for i, (sx, lvl) in enumerate([(-1, 1), (1, 1), (-1, 0), (1, 0)]):
        loc = (sx * (bw / 2 + .03), ly, z_lo + lvl * (bh + .02))
        q, _ = plank_bundle(N + f"Load_{i}b", loc, M_, n_w=4, n_h=3, bevel=0)
        if lvl == 0:
            for sy in (-.8, .8):   # dunnage sticks between the rows
                q.append(board(N + "dunnage", (bw + .04, .05, .02), (loc[0], ly + sy, loc[2] + bh + .01), m="pine", bevel=.002))
        W.part(N + f"Load_{i}", q, loc, body, c)
    return stats(name)

# ================================================================== Works_BancaKit items (origin = ground centre unless noted)
ITEMS = {}
def item(name):
    def deco(fn):
        ITEMS[name] = fn
        return fn
    return deco

def sawhorse(name, loc, M_, L_=.95, h=.72, rot_z=0.0):
    x0, y0, z0 = loc; p = []
    p.append(board(name + "_top", (L_, .09, .10), (0, 0, h - .05), m="oak", bevel=.005))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(bar(name + "_leg", (sx * (L_ / 2 - .08), sy * .035, h - .06), (sx * (L_ / 2 - .02), sy * .24, .0), .035, .07, m="pine"))
        p.append(bar(name + "_tie", (sx * (L_ / 2 - .06), -.16, .30), (sx * (L_ / 2 - .06), .16, .30), .025, .06, m="pine"))
    p.append(board(name + "_rail", (L_ - .25, .025, .06), (0, 0, .32), m="pine", bevel=.003))
    nails(p, name, [(sx * (L_ / 2 - .08), sy * .05, h + .003) for sx in (-1, 1) for sy in (-1, 1)], axis='Z', r=.008, M_=M_)
    return W.place(p, T((x0, y0, z0)) @ Rz(math.degrees(rot_z)))

@item("Prop_PlankV2")
def _(M_):
    return [board("plank", (2.4, .20, .04), (0, 0, 0), m="pine", bevel=.005)]

@item("Prop_PlankStackV2")
def _(M_):
    p = []
    for y in (-.75, .75):
        p.append(board("sleeper", (1.0, .09, .09), (0, y, .045), m="oak", bevel=.005))
    q, (bw, bh) = plank_bundle("stack", (0, 0, .09), M_, n_w=4, n_h=5, bw=.19, bh=.04, gap=.012, straps=(-.75, .75))
    p += q
    rnd = random.Random(11)
    p.append(board("offcut", (.55, .19, .04), (.55, -.95, .02), m="pine", bevel=.004, rot=(0, 0, rad(18))))
    p.append(board("offcut2", (.38, .19, .04), (.62, -.80, .06), m="pine", bevel=.004, rot=(0, 0, rad(-12))))
    p.append(board("offcut3", (.70, .12, .04), (-.62, .95, .02), m="pine", bevel=.004, rot=(0, 0, rad(70))))
    return p

@item("Prop_SawStation")
def _(M_):
    p = []
    p += sawhorse("shA", (-.55, 0, 0), M_)
    p += sawhorse("shB", (.55, 0, 0), M_, rot_z=rad(3))
    p.append(board("workPlank", (2.2, .20, .04), (.15, -.04, .74), m="pine", bevel=.005, rot=(0, 0, rad(-1.5))))
    # F-clamp on the plank at the left end
    p.append(bx("clampBar", (.025, .012, .22), (-.72, .10, .73), M_["dsteel"], bevel=.002))
    p.append(bx("clampTop", (.07, .035, .025), (-.70, .06, .835), M_["dsteel"], bevel=.003))
    p.append(bx("clampBot", (.07, .035, .025), (-.70, .06, .625), M_["dsteel"], bevel=.003))
    p.append(k.cyl("clampScrew", .006, .09, (-.68, .06, .60), M_["chrome"], verts=6))
    p.append(bx("clampHandle", (.02, .09, .02), (-.68, .10, .56), M_["red"], bevel=.004, rot=(0, 0, rad(30))))
    p.append(bx("clampGrip", (.03, .03, .05), (-.70, .06, .87), M_["red"], bevel=.006))
    # sawdust and offcuts under the cut end (worker saws at the +X end, standing at -Y)
    p.append(k.ball("dust", 1.0, (.95, -.12, .0), M_["sawdust"], sub=2, scale=(.30, .22, .035)))
    p.append(k.ball("dust2", 1.0, (.70, .10, .0), M_["sawdust"], sub=1, scale=(.16, .12, .022)))
    p.append(board("cut1", (.32, .20, .04), (1.05, .25, .02), m="pine", bevel=.004, rot=(0, 0, rad(25))))
    p.append(board("cut2", (.22, .20, .04), (1.15, -.30, .02), m="pine", bevel=.004, rot=(0, 0, rad(-40))))
    p.append(board("cut3", (.18, .20, .04), (.95, .40, .06), m="pine", bevel=.004, rot=(0, 0, rad(80))))
    return p

@item("Prop_StepLadder")
def _(M_):
    A, Ru = M_["alu"], M_["rubber"]; p = []
    H, tilt, W_ = 1.60, rad(15), .46
    for side, m in ((-1, A), (1, A)):      # front rails (steps) at -Y, back rails at +Y
        for sx in (-1, 1):
            top = Vector((sx * (W_ / 2 - .05), side * .02, H)); bot = Vector((sx * (W_ / 2 + .02), side * H * math.tan(tilt), 0))
            p.append(bx("rail", (.03, .07, (top - bot).length), ((top + bot) / 2).to_tuple(), m, bevel=.004,
                           rot=((bot - top).to_track_quat('Z', 'Y').to_euler())))
            p.append(bx("foot", (.05, .08, .03), (bot.x, bot.y, .015), Ru, bevel=.006))
    n_steps = 5
    for i in range(n_steps):
        t = (i + 1) / (n_steps + 1); z = H * t
        y = -(H - z) * math.tan(tilt) - .02
        p.append(bx("step", (W_ - .04, .09, .022), (0, y, z), A, bevel=.004))
        p.append(bx("stepLip", (W_ - .04, .018, .035), (0, y - .045, z - .01), A, bevel=.003))
    for i in range(3):
        t = (i + 1) / 4; z = H * t; y = (H - z) * math.tan(tilt) + .02
        p.append(bx("xbar", (W_ - .04, .025, .04), (0, y, z), A, bevel=.003))
    p.append(bx("cap", (W_ + .06, .26, .04), (0, 0, H + .02), A, bevel=.01, seg=2))
    p.append(bx("tray", (W_ - .02, .22, .025), (0, 0, H + .045), Ru, bevel=.004))
    for sx in (-1, 1):   # spreader bars
        y_f = -(H * .45) * math.tan(tilt); y_b = (H * .45) * math.tan(tilt)
        p.append(bx("spreader", (.02, y_b - y_f + .04, .025), (sx * (W_ / 2 + .035), 0, H * .55), A, bevel=.002))
        p.append(k.cyl("hinge", .02, .05, (sx * (W_ / 2 + .025), 0, H - .02), Ru, rot=(0, PI2, 0), verts=8))
    return p

@item("Prop_TapeBarrier")
def _(M_):
    p = []; L_ = 3.0; zt = .95
    for sx in (-1, 1):
        x = sx * L_ / 2
        p.append(k.cyl("base", .19, .045, (x, 0, .0225), M_["rubber"], verts=14, bevel=.01, seg=1, r2=.16))
        p.append(k.cyl("pole", .022, 1.0, (x, 0, .50), M_["hazardR"], verts=8))
        p.append(k.cyl("cap", .035, .04, (x, 0, 1.02), M_["black"], verts=8, bevel=.01))
        p.append(k.cyl("spool", .045, .08, (x, 0, zt), M_["black"], verts=10))
    n = 8; sag = .13
    a = Vector((-L_ / 2 + .04, 0, zt)); b = Vector((L_ / 2 - .04, 0, zt))
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        q0 = a.lerp(b, t0); q1 = a.lerp(b, t1)
        q0.z -= sag * math.sin(t0 * math.pi); q1.z -= sag * math.sin(t1 * math.pi)
        q0.y += .02 * math.sin(t0 * math.pi * 2); q1.y += .02 * math.sin(t1 * math.pi * 2)
        d = q1 - q0
        p.append(bx("tape", (d.length + .01, .004, .07), ((q0 + q1) / 2).to_tuple(), M_["tape"], bevel=0,
                       rot=(0, -math.atan2(d.z, d.x), math.atan2(d.y, d.x))))
    return p

@item("Prop_NailBucket")
def _(M_):
    p = []; r, h = .14, .27
    p.append(k.cyl("bucket", .115, h, (0, 0, h / 2), M_["bucket"], verts=14, bevel=.006, seg=1, r2=r))
    p.append(k.cyl("rim", r + .008, .018, (0, 0, h - .009), M_["bucket"], verts=14, bevel=.004))
    p.append(k.cyl("fill", r - .006, .02, (0, 0, h - .004), M_["dsteel"], verts=14))
    rnd = random.Random(5)
    for i in range(26):
        ang = rnd.uniform(0, math.pi); cx, cy = rnd.uniform(-.07, .07), rnd.uniform(-.07, .07); ln = rnd.uniform(.07, .10)
        a = Vector((cx - math.cos(ang) * ln / 2, cy - math.sin(ang) * ln / 2, h + .008 + rnd.uniform(0, .025)))
        b = Vector((cx + math.cos(ang) * ln / 2, cy + math.sin(ang) * ln / 2, a.z + rnd.uniform(-.01, .01)))
        p.append(k.tube("nail", a, b, .0035, M_["nail"], verts=4))
    for s_ in (-1, 1):
        p.append(k.cyl("ear", .012, .02, (s_ * (r + .004), 0, h - .03), M_["dsteel"], rot=(0, PI2, 0), verts=6))
    hp = [Vector((-r - .01, 0, h - .03)), Vector((-r * .9, 0, h + .12)), Vector((0, 0, h + .17)), Vector((r * .9, 0, h + .12)), Vector((r + .01, 0, h - .03))]
    for i in range(len(hp) - 1):
        p.append(k.tube("handle", hp[i], hp[i + 1], .006, M_["steel"], verts=6))
    p.append(k.cyl("grip", .014, .10, (0, 0, h + .165), M_["black"], rot=(0, PI2, 0), verts=8))
    # tool belt lying beside the bucket (+X)
    bpy.ops.mesh.primitive_torus_add(major_radius=.16, minor_radius=.016, major_segments=18, minor_segments=5, location=(.42, .02, .018))
    belt = bpy.context.active_object; belt.name = "belt"; belt.scale = (1, .8, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    k.finish(belt, M_["leather"], 0); p.append(belt)
    p.append(bx("buckle", (.045, .035, .03), (.26, .02, .02), M_["chrome"], bevel=.005))
    p.append(bx("pouch", (.13, .09, .10), (.50, -.10, .05), M_["leatherD"], bevel=.015, seg=2, rot=(0, 0, rad(20))))
    p.append(bx("pouch2", (.10, .08, .09), (.52, .14, .045), M_["leatherD"], bevel=.015, seg=2, rot=(0, 0, rad(-25))))
    p.append(bx("hammerLoop", (.03, .05, .06), (.33, .14, .03), M_["leatherD"], bevel=.008))
    p.append(bx("pencil", (.14, .012, .012), (.44, .19, .006), M_["yellow"], bevel=.002, rot=(0, 0, rad(10))))
    # tape measure in front (-Y)
    p.append(bx("tape", (.075, .075, .038), (-.02, -.26, .019), M_["yellow"], bevel=.014, seg=3, rot=(0, 0, rad(-15))))
    p.append(bx("tapeBand", (.08, .03, .04), (-.02, -.26, .02), M_["black"], bevel=.008, rot=(0, 0, rad(-15))))
    p.append(bx("tapeClip", (.012, .035, .03), (-.06, -.25, .02), M_["chrome"], bevel=.002, rot=(0, 0, rad(-15))))
    p.append(bx("tapeHook", (.025, .012, .02), (.02, -.30, .012), M_["chrome"], bevel=.002, rot=(0, 0, rad(-15))))
    return p

@item("Prop_Sawdust")
def _(M_):
    p = [k.ball("heap", 1.0, (0, 0, 0), M_["sawdust"], sub=2, scale=(.42, .34, .05)),
         k.ball("heap2", 1.0, (.18, .12, 0), M_["sawdust"], sub=1, scale=(.22, .18, .03)),
         k.ball("heap3", 1.0, (-.22, -.14, 0), M_["sawdust"], sub=1, scale=(.18, .14, .022))]
    return p

def build_banca_kit(name="Works_BancaKit"):
    M_ = mats(); c = new_col(src_col(name)); N = short(name) + "."
    for i, item_name in enumerate(KIT):
        p = ITEMS[item_name](M_)
        for o in p:
            if o.name.startswith(("heap", "dust")):
                for pg in o.data.polygons: pg.use_smooth = True
        o = W.part(N + item_name, p, (0, 0, 0), None, c)
        o.location.x = i * KIT_SPACING
    return stats(name)

BUILDERS = {"Works_BancaBuild": build_banca_build, "Works_LumberTruck": build_lumber_truck, "Works_BancaKit": build_banca_kit}

def build(name):
    return BUILDERS[name]()

def build_all():
    return {n: build(n) for n in MODELS}

# ================================================================== pipeline (copy -> bake one atlas on "UVMap" -> fbx)
def make_export(name):
    cname = src_col(name)
    d = W._attach(exp_col(name), k.col(EXPORT_COL))
    for o in list(d.objects): bpy.data.objects.remove(o)
    show(cname, d.name)
    src = objs_of(cname); mp = {}
    for o in src:
        n = o.copy(); n.data = o.data.copy(); n.name = "X_" + o.name; d.objects.link(n); mp[o] = n
    for o in src:
        n = mp[o]
        n.parent = mp[o.parent] if o.parent in mp else None
        n.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        n.matrix_basis = o.matrix_basis.copy()
    bpy.context.view_layer.update()
    out = list(mp.values())
    for n in out:
        k.bake(n)
        uv = n.data.uv_layers.get("UVMap") or n.data.uv_layers.new(name="UVMap")
        n.data.uv_layers.active = uv; uv.active_render = True
    bpy.ops.object.select_all(action='DESELECT')
    for o in out: o.select_set(True)
    bpy.context.view_layer.objects.active = out[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.001, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    return out

def bake(name, size=None, batches=1, batch_i=None):
    """Diffuse colour of all export copies -> one atlas (OUT/<name>_BaseColor.png), one material <name>_Mat."""
    size = size or SIZE.get(name, 2048)
    sc = bpy.context.scene
    show(exp_col(name))
    allobjs = objs_of(exp_col(name))
    objs = allobjs if batch_i is None else allobjs[batch_i::batches]
    img_name = name + "_BaseColor"
    first = batch_i in (None, 0)
    if first:
        for im in list(bpy.data.images):
            if im.name.startswith(img_name): bpy.data.images.remove(im)
        img = bpy.data.images.new(img_name, size, size)
    else:
        img = bpy.data.images[img_name]
    mats_ = {m for o in objs for m in o.data.materials if m}; added = []
    for m in mats_:
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; m.node_tree.nodes.active = n; added.append((m, n))
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 1
    b = sc.render.bake
    b.use_pass_direct = False; b.use_pass_indirect = False; b.use_pass_color = True; b.margin = 4; b.use_clear = first
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type='DIFFUSE')
    for m, n in added: m.node_tree.nodes.remove(n)
    if batch_i is not None and batch_i < batches - 1:
        sc.render.engine = 'BLENDER_EEVEE'
        return None
    os.makedirs(OUT, exist_ok=True)
    img.filepath_raw = os.path.join(OUT, img_name + ".png"); img.file_format = 'PNG'; img.save()
    am = bpy.data.materials.get(name + "_Mat") or bpy.data.materials.new(name + "_Mat")
    am.use_nodes = True; nt = am.node_tree
    for n in list(nt.nodes):
        if n.bl_idname == "ShaderNodeTexImage": nt.nodes.remove(n)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
    for o in allobjs:
        o.data.materials.clear(); o.data.materials.append(am)
        for p in o.data.polygons: p.material_index = 0
        for lname in ("Grain", "Tint"):          # only the atlas UV goes to Unity (uv0)
            lay = o.data.uv_layers.get(lname)
            if lay: o.data.uv_layers.remove(lay)
    sc.render.engine = 'BLENDER_EEVEE'
    return img.filepath_raw

def export_one(name):
    """FBX with the final names (X_BancaBuild.Stage_0 -> Stage_0); roots turned 180 deg by export_unity."""
    show(exp_col(name))
    objs = objs_of(exp_col(name))
    renames, parked = [], []
    for o in objs:
        final = o.name.split(".", 1)[1]
        other = bpy.data.objects.get(final)
        if other is not None and other is not o:
            other.name = other.name + "~"; parked.append(other)
        renames.append((o, o.name)); o.name = final
    lo, hi = bounds(objs)
    try:
        path = cp.export_unity(objs, name, folder=OUT)
    finally:
        for o, old in renames: o.name = old
        for other in parked: other.name = other.name[:-1]
    tris = sum(len(o.data.loop_triangles) for o in objs)
    return {"fbx": path, "kb": os.path.getsize(path) // 1024, "dims": [round(x, 2) for x in (hi - lo)], "tris": tris, "objs": len(objs)}

def pipeline(name, batches=2):
    batches = max(1, min(batches, len(make_export(name))))
    for p in range(batches):
        bake(name, None, batches, p)
    return export_one(name)

def export(names=None):
    """Export copies + atlas bake + FBX for the given assets (default: all three) into Assets/Resources/CheckoutWorks."""
    return {n: pipeline(n) for n in (names or MODELS)}

verify = W.verify

# ================================================================== previews (ArtSource/Review/banca_works)
ISO = W.ISO                     # camera at +X +Y, ~35 deg down: front-right for the truck (front +Y), back-right for the banca
ISO_BANCA = (1.0, -1.25, 1.1)   # front-left of the banca (customer side = -Y)

def shot(target, direction, dist, lens=40, name="x", res=(1100, 720), ortho=None, folder=None):
    sc = bpy.context.scene
    cp.studio(); sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.exposure = -0.2
    cam = bpy.data.objects["Studio Cam"]; cam.data.lens = lens
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho; cam.data.clip_end = 2000
    else:
        cam.data.type = 'PERSP'
    d = Vector(direction).normalized(); t = Vector(target)
    cam.location = t + d * dist; cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    folder = folder or REVIEW
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + ".png"); sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path

def _ground(ctr, size=80):
    return bx("WB_Ground", (size, size, .02), (ctr[0], ctr[1], -.015), k.pavers("ERA_Pavers"), bevel=0)

def preview(name, direction=None, baked=False, objs=None, tag=None, dist_mul=1.5, lens=38):
    cname = exp_col(name) if baked else src_col(name)
    show(cname)
    objs = objs or objs_of(cname)
    lo, hi = bounds(objs); ctr = (lo + hi) / 2; size = (hi - lo).length
    direction = direction or (ISO_BANCA if name == "Works_BancaBuild" else ISO)
    g = _ground(ctr)
    p = shot((ctr.x, ctr.y, (hi.z - lo.z) * .35), direction, size * dist_mul, lens=lens, name=tag or short(name))
    bpy.data.objects.remove(g)
    return p

def preview_kit(name="Works_BancaKit"):
    """One render per kit item (others hidden), named after the item."""
    cname = src_col(name); show(cname)
    out = []
    objs = objs_of(cname)
    for o in objs:
        for q in objs: q.hide_render = q is not o
        lo, hi = bounds([o]); ctr = (lo + hi) / 2; size = max((hi - lo).length, 1.2)
        g = _ground(ctr, 40)
        out.append(shot((ctr.x, ctr.y, lo.z + (hi.z - lo.z) * .45), ISO, size * 1.7, lens=38, name=o.name.split(".", 1)[1]))
        bpy.data.objects.remove(g)
    for q in objs: q.hide_render = False
    return out

def _compose(paths, out, cols=None, pad=8):
    """Tile PNGs into one image (numpy, Blender's own)."""
    import numpy as np
    ims = []
    for pth in paths:
        im = bpy.data.images.load(pth); w, h = im.size
        px = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(px)
        ims.append(px.reshape(h, w, 4)); bpy.data.images.remove(im)
    cols = cols or len(ims); rows = (len(ims) + cols - 1) // cols
    w, h = ims[0].shape[1], ims[0].shape[0]
    sheet = np.ones((rows * (h + pad) + pad, cols * (w + pad) + pad, 4), dtype=np.float32) * np.array([.86, .86, .88, 1], dtype=np.float32)
    for i, px in enumerate(ims):
        r, c_ = divmod(i, cols); r = rows - 1 - r
        y0 = pad + r * (h + pad); x0 = pad + c_ * (w + pad)
        sheet[y0:y0 + h, x0:x0 + w] = px
    img = bpy.data.images.new("WB_sheet", sheet.shape[1], sheet.shape[0])
    img.pixels.foreach_set(sheet.ravel()); img.filepath_raw = out; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return out

def stage_strip(name="Works_BancaBuild"):
    """6 renders: Layout+Stage_0, +Stage_1, ... +Stage_5 (cumulative) and one strip image."""
    cname = src_col(name); show(cname); objs = objs_of(cname)
    by = {o.name.split(".", 1)[1]: o for o in objs}
    lo, hi = bounds(objs); ctr = (lo + hi) / 2; size = (hi - lo).length
    paths = []
    for s in range(6):
        vis = {"Layout"} | {f"Stage_{i}" for i in range(s + 1)}
        for n, o in by.items(): o.hide_render = n not in vis
        g = _ground(ctr)
        paths.append(shot((ctr.x, ctr.y, (hi.z - lo.z) * .35), ISO_BANCA, size * 1.5, lens=38, name=f"BancaBuild_stage{s}", res=(800, 560)))
        bpy.data.objects.remove(g)
    for o in objs: o.hide_render = False
    return _compose(paths, os.path.join(REVIEW, "BancaBuild_stages.png"))

def scene_mock():
    """BancaBuild at ~60 % (Layout + Stage_0..3) with the truck and the kit props arranged beside it."""
    cb, ct, ck = src_col("Works_BancaBuild"), src_col("Works_LumberTruck"), src_col("Works_BancaKit")
    show(cb, ct, ck)
    moved = []
    def mv(o, loc, rz=0.0):
        moved.append((o, o.location.copy(), o.rotation_euler.copy()))
        o.location = loc; o.rotation_euler.z += rz
    for o in objs_of(cb):
        n = o.name.split(".", 1)[1]
        o.hide_render = n in ("Stage_4", "Stage_5")
    for o in objs_of(ct):
        if o.parent is None: mv(o, (4.9, .3, 0), rad(-8))
    kit = {o.name.split(".", 1)[1]: o for o in objs_of(ck)}
    mv(kit["Prop_SawStation"], (-3.6, -1.3, 0), rad(12))
    mv(kit["Prop_PlankStackV2"], (-3.7, 1.6, 0), rad(-5))
    mv(kit["Prop_StepLadder"], (1.9, -1.9, 0), rad(25))
    mv(kit["Prop_TapeBarrier"], (0.3, -3.0, 0), rad(-4))
    mv(kit["Prop_NailBucket"], (.55, -1.45, 0), rad(40))
    mv(kit["Prop_Sawdust"], (-2.3, -1.9, 0), 0)
    mv(kit["Prop_PlankV2"], (-1.6, -1.55, .025), rad(100))
    bpy.context.view_layer.update()
    g = _ground((0, 0), 120)
    p = shot((1.1, -.4, .8), (1.0, -1.25, 1.0), 14.5, lens=38, name="scene_mock", res=(1600, 1000))
    bpy.data.objects.remove(g)
    for o, loc, rot in moved:
        o.location = loc; o.rotation_euler = rot
    for o in objs_of(cb): o.hide_render = False
    return p

def contact_sheet(name="contact"):
    """The individual previews (BancaBuild, LumberTruck, the 7 kit items) tiled 3 per row."""
    names = ["BancaBuild", "LumberTruck"] + KIT
    paths = [os.path.join(REVIEW, n + ".png") for n in names]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        preview("Works_BancaBuild"); preview("Works_LumberTruck"); preview_kit()
    return _compose(paths, os.path.join(REVIEW, name + ".png"), cols=3)

def previews():
    out = [preview("Works_BancaBuild"), preview("Works_LumberTruck")]
    out += preview_kit()
    out.append(stage_strip()); out.append(scene_mock()); out.append(contact_sheet())
    return out
