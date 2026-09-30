"""Helpers for the Checkout "eras" props (ERA0 Mesinha, ERA1 Banca). Used by the Blender MCP session."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

NAVY = (0.045, 0.095, 0.30, 1)
NAVYL = (0.10, 0.19, 0.45, 1)
GOLD = (0.91, 0.70, 0.27, 1)
CREAM = (0.96, 0.90, 0.72, 1)
WHITE = (0.97, 0.96, 0.92, 1)
WOOD = (0.67, 0.40, 0.22, 1)
WOODL = (0.84, 0.61, 0.33, 1)
WOODD = (0.39, 0.25, 0.17, 1)
PALE = (0.90, 0.78, 0.55, 1)   # raw pine crates
PALED = (0.62, 0.47, 0.28, 1)
METAL = (0.64, 0.66, 0.66, 1)
DARK = (0.16, 0.17, 0.18, 1)
RED = (0.86, 0.22, 0.16, 1)
ORANGE = (0.97, 0.55, 0.12, 1)
YELLOW = (0.96, 0.80, 0.22, 1)
GREEN = (0.35, 0.62, 0.20, 1)
CARDBOARD = (0.76, 0.58, 0.36, 1)
ICE = (0.80, 0.92, 0.98, 1)


# ---------------------------------------------------------------- collections
def col(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if c.name not in parent.children:
        parent.children.link(c)
    return c


def link(o, c):
    if c is None:
        return o
    for oc in list(o.users_collection):
        oc.objects.unlink(o)
    c.objects.link(o)
    return o


# ---------------------------------------------------------------- materials
def _new(name):
    m = bpy.data.materials.get(name)
    if m:
        return m, None
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree


def _noise_mult(nt, rgb, var, scale, bsdf):
    n, L = nt.nodes, nt.links
    tc = n.new("ShaderNodeTexCoord")
    noise = n.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 5
    L.new(tc.outputs["Object"], noise.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = .35
    mr.inputs["From Max"].default_value = .65
    mr.inputs["To Min"].default_value = 1 - var
    mr.inputs["To Max"].default_value = 1 + var
    L.new(noise.outputs[0], mr.inputs["Value"])
    mix = n.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    mix.inputs[6].default_value = rgb
    L.new(mr.outputs[0], mix.inputs[7])
    return tc, noise, mix


def mat(name, rgb, rough=.65, var=.10, scale=30., metallic=0., bump=0.):
    """Painted / plain material with soft procedural colour variation."""
    m, nt = _new(name)
    if nt is None:
        return m
    n, L = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    tc, noise, mix = _noise_mult(nt, rgb, var, scale, bsdf)
    L.new(mix.outputs[2], bsdf.inputs["Base Color"])
    if bump:
        b = n.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        L.new(noise.outputs[0], b.inputs["Height"])
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def wood(name, light=WOODL, dark=WOOD, scale=9., axis='X', rough=.6, bump=.25):
    m, nt = _new(name)
    if nt is None:
        return m
    n, L = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    tc = n.new("ShaderNodeTexCoord")
    wave = n.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = axis
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 1.5
    wave.inputs["Detail"].default_value = 2
    wave.inputs["Detail Scale"].default_value = 1.5
    L.new(tc.outputs["Object"], wave.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = .25
    ramp.color_ramp.elements[0].color = light
    ramp.color_ramp.elements[1].position = .85
    ramp.color_ramp.elements[1].color = dark
    L.new(wave.outputs[0], ramp.inputs[0])
    L.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    b = n.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = bump
    L.new(wave.outputs[0], b.inputs["Height"])
    L.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def stripes(name, a=NAVY, b=CREAM, width=.14, axis='X', rough=.85):
    """Hard painted / woven stripes along an object axis (fabric awning)."""
    m, nt = _new(name)
    if nt is None:
        return m
    n, L = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs[0])
    div = n.new("ShaderNodeMath"); div.operation = 'DIVIDE'; div.inputs[1].default_value = width
    L.new(sep.outputs[axis], div.inputs[0])
    fr = n.new("ShaderNodeMath"); fr.operation = 'FRACT'
    L.new(div.outputs[0], fr.inputs[0])
    gt = n.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = .5
    L.new(fr.outputs[0], gt.inputs[0])
    mix = n.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs[6].default_value = a
    mix.inputs[7].default_value = b
    L.new(gt.outputs[0], mix.inputs[0])
    # cloth weave shading
    noise = n.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 60; noise.inputs["Detail"].default_value = 6
    L.new(tc.outputs["Object"], noise.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = .35; mr.inputs["From Max"].default_value = .65
    mr.inputs["To Min"].default_value = .88; mr.inputs["To Max"].default_value = 1.08
    L.new(noise.outputs[0], mr.inputs[0])
    mul = n.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1
    L.new(mix.outputs[2], mul.inputs[6]); L.new(mr.outputs[0], mul.inputs[7])
    L.new(mul.outputs[2], bsdf.inputs["Base Color"])
    b_ = n.new("ShaderNodeBump"); b_.inputs["Strength"].default_value = .15
    L.new(noise.outputs[0], b_.inputs["Height"]); L.new(b_.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def twotone_z(name, low=NAVY, high=GOLD, z=0.03, rough=.8, var=.08):
    """Colour `low` below object-Z `z`, `high` above (hem band on cloth, painted band)."""
    m, nt = _new(name)
    if nt is None:
        return m
    n, L = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    tc, noise, mix = _noise_mult(nt, (1, 1, 1, 1), var, 40, bsdf)
    sep = n.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs[0])
    gt = n.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = z
    L.new(sep.outputs["Z"], gt.inputs[0])
    tone = n.new("ShaderNodeMix"); tone.data_type = 'RGBA'
    tone.inputs[6].default_value = low; tone.inputs[7].default_value = high
    L.new(gt.outputs[0], tone.inputs[0])
    mul = n.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1
    L.new(tone.outputs[2], mul.inputs[6]); L.new(mix.outputs[2], mul.inputs[7])
    L.new(mul.outputs[2], bsdf.inputs["Base Color"])
    b_ = n.new("ShaderNodeBump"); b_.inputs["Strength"].default_value = .12
    L.new(noise.outputs[0], b_.inputs["Height"]); L.new(b_.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def pavers(name="ERA_Pavers"):
    m, nt = _new(name)
    if nt is None:
        return m
    n, L = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = .9
    tc = n.new("ShaderNodeTexCoord")
    br = n.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 3.3
    br.inputs["Mortar Size"].default_value = .02
    br.inputs["Color1"].default_value = (.80, .78, .72, 1)
    br.inputs["Color2"].default_value = (.72, .70, .64, 1)
    br.inputs["Mortar"].default_value = (.58, .56, .52, 1)
    br.inputs["Bias"].default_value = 0
    br.inputs["Brick Width"].default_value = .5
    br.inputs["Row Height"].default_value = .5
    L.new(tc.outputs["Object"], br.inputs["Vector"])
    noise = n.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 3
    L.new(tc.outputs["Object"], noise.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = .85; mr.inputs["To Max"].default_value = 1.1
    L.new(noise.outputs[0], mr.inputs[0])
    mul = n.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1
    L.new(br.outputs[0], mul.inputs[6]); L.new(mr.outputs[0], mul.inputs[7])
    L.new(mul.outputs[2], bsdf.inputs["Base Color"])
    b_ = n.new("ShaderNodeBump"); b_.inputs["Strength"].default_value = .3
    L.new(br.outputs[1], b_.inputs["Height"]); L.new(b_.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# ---------------------------------------------------------------- mesh helpers
def _smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def finish(o, m=None, bevel=.008, seg=2, smooth=True):
    if m is not None:
        o.data.materials.append(m)
    if bevel:
        b = o.modifiers.new("Bevel", 'BEVEL')
        b.width = bevel
        b.segments = seg
        b.limit_method = 'ANGLE'
        b.angle_limit = math.radians(40)
        b.harden_normals = True
    if smooth:
        _smooth(o)
    return o


def box(name, size, loc, m=None, rot=(0, 0, 0), bevel=.008, seg=2, c=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    link(o, c)
    return finish(o, m, bevel, seg)


def cyl(name, r, h, loc, m=None, rot=(0, 0, 0), verts=16, bevel=0., seg=2, c=None, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    link(o, c)
    return finish(o, m, bevel, seg)


def ball(name, r, loc, m=None, sub=1, scale=(1, 1, 1), rot=(0, 0, 0), c=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    link(o, c)
    return finish(o, m, 0)


def tube(name, a, b, r, m=None, verts=8, c=None):
    """Cylinder from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    o = cyl(name, r, d.length, (a + b) / 2, m, verts=verts, c=c)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


def text(name, s, size, loc, m=None, rot=(0, 0, 0), extrude=.004, c=None, align='CENTER', spacing=1.0):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.data.body = s
    o.data.size = size
    o.data.extrude = extrude
    o.data.align_x = align
    o.data.align_y = 'CENTER'
    o.data.space_character = spacing
    o.data.resolution_u = 3
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.active_object
    o.name = name
    link(o, c)
    if m is not None:
        o.data.materials.append(m)
    return o


def bake(o):
    """Apply modifiers (evaluated mesh) so the object can be joined."""
    if not o.modifiers:
        return o
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    old = o.data
    o.modifiers.clear()
    o.data = me
    me.name = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return o


def join(objs, name, origin=None):
    objs = [o for o in objs if o is not None]
    bpy.context.view_layer.update()
    for o in objs:
        bake(o)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    o.data.name = name
    if origin is not None:
        bpy.context.scene.cursor.location = origin
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return o


def tris(collection):
    dg = bpy.context.evaluated_depsgraph_get()
    total = 0
    for o in collection.all_objects:
        if o.type == 'MESH':
            total += len(o.evaluated_get(dg).data.loop_triangles)
    return total


# ---------------------------------------------------------------- props
def crate(name, loc, w=.50, d=.36, h=.26, m=None, c=None, rot_z=0., slats=3):
    """Feira wooden crate: 4 corner posts, slats with gaps, end handle slot, slatted bottom."""
    m = m or wood("ERA_Crate", PALE, PALED, scale=6, axis='Z', bump=.10)
    parts = []
    t, post = .016, .03
    sh = h / slats * .72
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box(name + "_post", (post, post, h), (sx * (w / 2 - post / 2), sy * (d / 2 - post / 2), h / 2), m, bevel=.004, seg=1))
    for i in range(slats):
        z = h / slats * (i + .5)
        top = i == slats - 1
        for sy in (-1, 1):  # long sides
            parts.append(box(name + "_slat", (w, t, sh), (0, sy * (d / 2 - t / 2), z), m, bevel=.003, seg=1))
        for sx in (-1, 1):  # short ends (top one has a handle slot)
            if top:
                seg_w = (d - 2 * post - .09) / 2
                for k in (-1, 1):
                    parts.append(box(name + "_end", (t, seg_w, sh), (sx * (w / 2 - post - t / 2), k * (.045 + seg_w / 2), z), m, bevel=.003, seg=1))
                parts.append(box(name + "_endbar", (t, d - 2 * post, sh * .35), (sx * (w / 2 - post - t / 2), 0, z - sh * .33), m, bevel=.003, seg=1))
            else:
                parts.append(box(name + "_end", (t, d - 2 * post, sh), (sx * (w / 2 - post - t / 2), 0, z), m, bevel=.003, seg=1))
    for i in range(3):
        y = (i - 1) * (d - 2 * post - .05) / 2
        parts.append(box(name + "_bottom", (w - 2 * post, .05, t), (0, y, t / 2 + .004), m, bevel=.003, seg=1))
    o = join(parts, name, origin=(0, 0, 0))
    for p in o.data.polygons:
        p.use_smooth = True
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    link(o, c)
    return o


def produce_fill(name, loc, w, d, z_top, m, kind='ball', r=.045, rows=None, cols=None, rot_z=0., c=None, seed=1, sub=2):
    """A crate full of fruit: hidden filler + a heap of fruit on top."""
    rnd = random.Random(seed)
    parts = []
    inner_w, inner_d = w - .07, d - .07
    cols = cols or max(2, int(inner_w / (r * 2.0)))
    rows = rows or max(2, int(inner_d / (r * 2.0)))
    filler = box(name + "_fill", (inner_w, inner_d, .05), (0, 0, z_top - .04), m, bevel=0)
    parts.append(filler)
    for i in range(cols):
        for j in range(rows):
            x = (i - (cols - 1) / 2) * inner_w / cols
            y = (j - (rows - 1) / 2) * inner_d / rows
            jitter = r * .25
            p = (x + rnd.uniform(-jitter, jitter), y + rnd.uniform(-jitter, jitter), z_top - r * .35 + rnd.uniform(-r * .1, r * .15))
            rr = r * rnd.uniform(.9, 1.1)
            if kind == 'ball':
                parts.append(ball(name + "_f", rr, p, m, sub=sub, scale=(1, 1, rnd.uniform(.85, .95)), rot=(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 6))))
            elif kind == 'tomato':
                b = ball(name + "_f", rr, p, m, sub=sub, scale=(1, 1, .82), rot=(0, 0, rnd.uniform(0, 6)))
                parts.append(b)
            elif kind == 'lime':
                parts.append(ball(name + "_f", rr, p, m, sub=sub, scale=(1, .85, .8), rot=(0, 0, rnd.uniform(0, 6))))
    # second sparse layer for a heaped look
    for k in range(max(1, (cols * rows) // 3)):
        x = rnd.uniform(-inner_w / 2 + r, inner_w / 2 - r)
        y = rnd.uniform(-inner_d / 2 + r, inner_d / 2 - r)
        parts.append(ball(name + "_f", r * rnd.uniform(.9, 1.05), (x, y, z_top + r * .9), m, sub=sub,
                          scale=(1, 1, .85 if kind != 'ball' else .92), rot=(0, 0, rnd.uniform(0, 6))))
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    link(o, c)
    return o


def banana(name, loc, rot=(0, 0, 0), m=None, length=.19, c=None):
    """One curved banana made with bmesh (ring profile swept along an arc)."""
    bm = bmesh.new()
    n_ring, n_seg = 7, 6
    rings = []
    R = length / 1.1
    for s in range(n_seg + 1):
        t = s / n_seg
        ang = math.radians(-35 + 70 * t)
        cx, cz = R * math.sin(ang), R * (1 - math.cos(ang))
        taper = .35 + .65 * math.sin(math.pi * min(1, max(0, (t - .05) / .9))) ** .5
        rr = .017 * taper
        if s in (0, n_seg):
            rr = .004
        ring = []
        for k in range(n_ring):
            a = 2 * math.pi * k / n_ring
            # slightly pentagonal cross-section
            rk = rr * (1 + .12 * math.cos(5 * a))
            v = bm.verts.new((cx + rk * math.cos(a) * math.cos(ang), rk * math.sin(a), cz - rk * math.cos(a) * math.sin(ang)))
            ring.append(v)
        rings.append(ring)
    for s in range(n_seg):
        for k in range(n_ring):
            bm.faces.new((rings[s][k], rings[s][(k + 1) % n_ring], rings[s + 1][(k + 1) % n_ring], rings[s + 1][k]))
    # caps
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    link(o, c)
    if m is not None:
        me.materials.append(m)
    _smooth(o)
    return o


def banana_bunch(name, loc, rot_z=0., m=None, n=5, c=None):
    m = m or mat("ERA_Banana", YELLOW, rough=.5, var=.12, scale=25)
    parts = []
    for i in range(n):
        a = (i - (n - 1) / 2) * .16
        # stems meet at -X; the hands fan out sideways and tilt like a real bunch
        parts.append(banana(name + "_b", (0.0, a * .20, abs(a) * .04), (a * 1.6, 0, a * .5), m))
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    link(o, c)
    return o


def cloth(name, w, d, top_z, drop, m, c=None, seed=3):
    """Table cloth: open box, subdivided, wrinkled with a cloud displacement, smoothed."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, top_z - drop / 2))
    o = bpy.context.active_object
    o.name = name
    o.scale = (w, d, drop)
    bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bottom = [f for f in bm.faces if f.normal.z < -.5]
    bmesh.ops.delete(bm, geom=bottom, context='FACES')
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
    # crease the table-top rim so the cloth folds over the edge instead of puffing
    crease = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
    zt = max(v.co.z for v in bm.verts)
    for e in bm.edges:
        if all(abs(v.co.z - zt) < 1e-4 and (abs(abs(v.co.x) - w / 2) < 1e-4 or abs(abs(v.co.y) - d / 2) < 1e-4) for v in e.verts):
            e[crease] = .85
    # only the hanging skirt gets folds (top stays flat); store a weight
    vg_layer = bm.verts.layers.deform.new()
    bm.to_mesh(o.data)
    bm.free()
    vg = o.vertex_groups.new(name="skirt")
    for v in o.data.vertices:
        t = (zt - v.co.z) / drop
        if t > .02:
            vg.add([v.index], min(1.0, t * 1.6), 'REPLACE')
    tex = bpy.data.textures.get("ERA_ClothFolds") or bpy.data.textures.new("ERA_ClothFolds", 'CLOUDS')
    tex.noise_scale = .16
    tex.noise_depth = 1
    disp = o.modifiers.new("Folds", 'DISPLACE')
    disp.texture = tex
    disp.strength = .03
    disp.mid_level = .5
    disp.direction = 'NORMAL'
    disp.vertex_group = "skirt"
    sub = o.modifiers.new("Sub", 'SUBSURF')
    sub.levels = sub.render_levels = 1
    sol = o.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = .004
    o.data.materials.append(m)
    _smooth(o)
    link(o, c)
    return o


def umbrella(name, loc, h=2.25, R=.95, m_a=None, m_b=None, m_pole=None, c=None, tilt=0.0):
    """Beach umbrella: scalloped canopy with alternating panels, ribs, pole and a paint-bucket base."""
    m_a = m_a or mat("ERA_Navy", NAVY, rough=.75, var=.08, bump=.1)
    m_b = m_b or mat("ERA_Cream", CREAM, rough=.75, var=.08, bump=.1)
    m_pole = m_pole or mat("ERA_Metal", METAL, rough=.35, var=.05, metallic=.8)
    m_wood = wood("ERA_WoodPole", WOODL, WOOD, scale=6, axis='Z')
    parts = []
    # canopy
    bm = bmesh.new()
    panels = 8
    top = bm.verts.new((0, 0, 0))
    inner, outer = [], []
    for k in range(panels * 2):
        a = 2 * math.pi * k / (panels * 2)
        rib = k % 2 == 0
        ro = R if rib else R * .90
        zo = -.34 if rib else -.27
        outer.append(bm.verts.new((ro * math.cos(a), ro * math.sin(a), zo)))
        ri = R * .5
        zi = -.10 if rib else -.085
        inner.append(bm.verts.new((ri * math.cos(a), ri * math.sin(a), zi)))
    faces = []
    for k in range(panels * 2):
        k2 = (k + 1) % (panels * 2)
        f1 = bm.faces.new((top, inner[k], inner[k2]))
        f2 = bm.faces.new((inner[k], outer[k], outer[k2], inner[k2]))
        for f in (f1, f2):
            f.material_index = (k // 2) % 2
    me = bpy.data.meshes.new(name + "_canopy")
    bm.to_mesh(me)
    bm.free()
    can = bpy.data.objects.new(name + "_canopy", me)
    bpy.context.scene.collection.objects.link(can)
    can.location = (0, 0, h)
    me.materials.append(m_a)
    me.materials.append(m_b)
    sub = can.modifiers.new("Sub", 'SUBSURF')
    sub.levels = sub.render_levels = 2
    sol = can.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = .012
    sol.offset = -1
    _smooth(can)
    parts.append(can)
    # ribs + pole + finial
    for k in range(panels):
        a = 2 * math.pi * k / panels
        parts.append(tube(name + "_rib", (0, 0, h - .02), (R * .96 * math.cos(a), R * .96 * math.sin(a), h - .335), .007, m_pole, verts=6))
        parts.append(tube(name + "_strut", (0, 0, h - .55), (R * .5 * math.cos(a), R * .5 * math.sin(a), h - .13), .006, m_pole, verts=6))
    parts.append(cyl(name + "_hub", .035, .09, (0, 0, h - .55), m_pole, verts=10, bevel=.004))
    m_pc = mat("ERA_PoleCream", CREAM, rough=.4, var=.04, scale=10)
    parts.append(cyl(name + "_pole", .02, h + .05, (0, 0, (h + .05) / 2), m_pc, verts=12))
    parts.append(cyl(name + "_collar", .028, .05, (0, 0, .30), m_pole, verts=12, bevel=.004))
    parts.append(ball(name + "_finial", .04, (0, 0, h + .06), mat("ERA_Gold", GOLD, rough=.45, var=.08, metallic=.3), sub=2))
    # base: paint bucket full of concrete
    parts.append(cyl(name + "_bucket", .15, .24, (0, 0, .12), mat("ERA_BucketNavy", NAVYL, rough=.5, var=.08), verts=20, bevel=.008, r2=.17))
    parts.append(cyl(name + "_rim", .18, .02, (0, 0, .245), m_pole, verts=20, bevel=.004))
    parts.append(cyl(name + "_concrete", .16, .02, (0, 0, .25), mat("ERA_Concrete", (.62, .60, .56, 1), rough=.95, var=.12, scale=50, bump=.4), verts=20))
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    o.rotation_euler = (tilt, 0, 0)
    link(o, c)
    return o


# ================================================================ v4: eras 2-4 helpers
def emissive(name, rgb, strength=4.0):
    m, nt = _new(name)
    if nt is None:
        return m
    n = nt.nodes
    bsdf = n["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgb
    bsdf.inputs["Emission Color"].default_value = rgb
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Roughness"].default_value = .4
    return m


def glass(name="ERA_Glass", tint=(.80, .90, .95, 1), alpha=.28):
    m, nt = _new(name)
    if nt is None:
        return m
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = tint
    bsdf.inputs["Roughness"].default_value = .05
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Specular IOR Level"].default_value = .8
    try:
        m.blend_method = 'BLEND'
    except Exception:
        pass
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    m.use_backface_culling = False
    return m


def bottle(name, loc, m, r=.032, h=.24, m_cap=None, rot=(0, 0, 0)):
    m_cap = m_cap or mat("ERA_Cap", CREAM, rough=.4)
    parts = [cyl(name + "_body", r, h * .62, (0, 0, h * .31), m, verts=10, bevel=.006, seg=1),
             cyl(name + "_shoulder", r, h * .16, (0, 0, h * .62 + h * .08), m, verts=10, r2=r * .45),
             cyl(name + "_neck", r * .45, h * .18, (0, 0, h * .78 + h * .09), m, verts=8),
             cyl(name + "_cap", r * .5, h * .06, (0, 0, h * .96 + h * .03), m_cap, verts=8)]
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    o.rotation_euler = rot
    return o


def can(name, loc, m, r=.033, h=.12, m_top=None):
    m_top = m_top or mat("ERA_Metal", METAL, rough=.35, var=.05, metallic=.8)
    parts = [cyl(name + "_b", r, h, (0, 0, h / 2), m, verts=10, bevel=.005, seg=1),
             cyl(name + "_t", r * .9, .006, (0, 0, h + .002), m_top, verts=10)]
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    return o


DRINK_COLORS = [RED, ORANGE, NAVYL, GREEN, GOLD, (.55, .15, .45, 1), (.20, .55, .70, 1), (.95, .85, .30, 1)]


def drink_mat(i):
    return mat(f"ERA_Drink{i % len(DRINK_COLORS)}", DRINK_COLORS[i % len(DRINK_COLORS)], rough=.35, var=.05, metallic=.15)


def product_box(name, loc, size, m, rot_z=0.):
    o = box(name, size, (0, 0, size[2] / 2), m, bevel=min(.006, size[0] * .1), seg=1)
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    return o


PRODUCT_COLORS = [RED, ORANGE, NAVYL, GREEN, GOLD, CREAM, (.55, .15, .45, 1), (.20, .55, .70, 1), WHITE, (.35, .20, .12, 1)]


def product_mat(i):
    return mat(f"ERA_Prod{i % len(PRODUCT_COLORS)}", PRODUCT_COLORS[i % len(PRODUCT_COLORS)], rough=.55, var=.12, scale=20)


def shelf_unit(name, loc, w=1.0, d=.35, h=1.8, levels=4, m=None, m_back=None, fill=True, seed=1, rot_z=0., c=None, first_z=.15):
    """Open shelving unit (two side panels, back panel, boards) filled with boxed / canned products."""
    m = m or mat("ERA_ShelfNavy", NAVY, rough=.6, var=.05, scale=10)
    m_back = m_back or mat("ERA_ShelfCream", CREAM, rough=.7, var=.06, scale=10)
    rnd = random.Random(seed)
    parts = [box(name + "_side", (.025, d, h), (-w / 2 + .0125, 0, h / 2), m, bevel=.004, seg=1),
             box(name + "_side", (.025, d, h), (w / 2 - .0125, 0, h / 2), m, bevel=.004, seg=1),
             box(name + "_back", (w, .02, h), (0, d / 2 - .01, h / 2), m_back, bevel=.004, seg=1)]
    zs = [first_z + i * (h - first_z - .05) / (levels - 1) for i in range(levels)]
    for z in zs:
        parts.append(box(name + "_board", (w - .05, d - .03, .025), (0, 0, z), m, bevel=.004, seg=1))
        if fill:
            x = -w / 2 + .06
            k_ = 0
            while x < w / 2 - .09:
                bw = rnd.choice([.06, .08, .10, .12])
                if x + bw > w / 2 - .04:
                    break
                bh = rnd.choice([.10, .14, .18, .22])
                kind = rnd.random()
                pm = product_mat(rnd.randrange(10))
                if kind < .65:
                    parts.append(product_box(name + "_p", (x + bw / 2, -d / 2 + .05 + bw / 2 + rnd.uniform(0, .04), z + .0125), (bw, bw * rnd.uniform(.5, 1.0), bh), pm))
                else:
                    parts.append(can(name + "_p", (x + bw / 2, -d / 2 + .06 + rnd.uniform(0, .04), z + .0125), pm, r=min(.033, bw / 2), h=min(bh, .13)))
                x += bw + .008
                k_ += 1
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    link(o, c)
    return o


def fridge_vertical(name, loc, w=.70, d=.65, h=1.95, rot_z=0., c=None, seed=4, m_body=None, n_shelves=4):
    """Glass-door drinks fridge: body, lit header, glass door with frame + handle, shelves with bottles/cans."""
    m_body = m_body or mat("ERA_FridgeNavy", NAVY, rough=.45, var=.04, scale=10)
    m_in = mat("ERA_FridgeInside", WHITE, rough=.5, var=.03, scale=10)
    m_frame = mat("ERA_Metal", METAL, rough=.35, var=.05, metallic=.8)
    m_light = emissive("ERA_FridgeLight", (1, .97, .90, 1), 3.0)
    m_gl = glass()
    rnd = random.Random(seed)
    t = .04
    parts = [box(name + "_side", (t, d, h), (-w / 2 + t / 2, 0, h / 2), m_body, bevel=.008, seg=2),
             box(name + "_side", (t, d, h), (w / 2 - t / 2, 0, h / 2), m_body, bevel=.008, seg=2),
             box(name + "_back", (w, t, h), (0, d / 2 - t / 2, h / 2), m_body, bevel=.008, seg=2),
             box(name + "_top", (w, d, t), (0, 0, h - t / 2), m_body, bevel=.008, seg=2),
             box(name + "_bottom", (w, d, .12), (0, 0, .06), m_body, bevel=.008, seg=2),
             box(name + "_inback", (w - 2 * t, .01, h - .16), (0, d / 2 - t - .005, .12 + (h - .16) / 2), m_in, bevel=0),
             box(name + "_inside", (.01, d - t - .02, h - .16), (-w / 2 + t + .005, .01, .12 + (h - .16) / 2), m_in, bevel=0),
             box(name + "_inside", (.01, d - t - .02, h - .16), (w / 2 - t - .005, .01, .12 + (h - .16) / 2), m_in, bevel=0),
             box(name + "_intop", (w - 2 * t, d - t - .02, .01), (0, .01, h - t - .005), m_in, bevel=0),
             box(name + "_inbot", (w - 2 * t, d - t - .02, .01), (0, .01, .125), m_in, bevel=0),
             box(name + "_header", (w - 2 * t - .02, .02, .16), (0, -d / 2 + .05, h - .13), m_light, bevel=.004, seg=1),
             box(name + "_frame", (w - 2 * t, .03, .03), (0, -d / 2 + .015, .135), m_frame, bevel=.004, seg=1),
             box(name + "_frame", (w - 2 * t, .03, .03), (0, -d / 2 + .015, h - .055), m_frame, bevel=.004, seg=1),
             box(name + "_frame", (.03, .03, h - .19), (-w / 2 + t + .015, -d / 2 + .015, .12 + (h - .19) / 2), m_frame, bevel=.004, seg=1),
             box(name + "_frame", (.03, .03, h - .19), (w / 2 - t - .015, -d / 2 + .015, .12 + (h - .19) / 2), m_frame, bevel=.004, seg=1),
             box(name + "_handle", (.025, .03, .5), (w / 2 - t - .06, -d / 2 - .01, h * .55), m_frame, bevel=.006, seg=2)]
    # the glass pane stays a separate object (transparent)
    zs = [.16 + i * (h - .40) / (n_shelves - 1) for i in range(n_shelves)]
    for z in zs:
        parts.append(box(name + "_shelf", (w - 2 * t - .02, d - t - .06, .015), (0, .0, z), m_frame, bevel=.003, seg=1))
        cols = int((w - 2 * t - .06) / .075)
        for i in range(cols):
            x = -w / 2 + t + .05 + i * .075
            pm = drink_mat(rnd.randrange(8))
            if rnd.random() < .6:
                parts.append(bottle(name + "_bt", (x, -d / 2 + .13, z + .008), pm, r=.03, h=.22))
            else:
                parts.append(can(name + "_cn", (x, -d / 2 + .13, z + .008), pm))
    o = join(parts, name, origin=(0, 0, 0))
    pane = box(name + "_glass", (w - 2 * t - .04, .008, h - .22), (0, -d / 2 + .012, .12 + (h - .22) / 2 + .015), m_gl, bevel=0)
    pane.parent = o
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    link(o, c)
    link(pane, c)
    return o, pane


def chest_freezer(name, loc, w=1.2, d=.62, h=.85, rot_z=0., c=None, seed=5):
    """Horizontal drinks freezer with glass sliding lids and bottles inside."""
    m_body = mat("ERA_FreezerCream", CREAM, rough=.45, var=.04, scale=10)
    m_band = mat("ERA_FridgeNavy", NAVY, rough=.45, var=.04, scale=10)
    m_frame = mat("ERA_Metal", METAL, rough=.35, var=.05, metallic=.8)
    m_in = mat("ERA_FridgeInside", WHITE, rough=.5, var=.03, scale=10)
    m_gl = glass()
    rnd = random.Random(seed)
    t = .05
    parts = [box(name + "_wall", (w, t, h), (0, -d / 2 + t / 2, h / 2), m_body, bevel=.012, seg=2),
             box(name + "_wall", (w, t, h), (0, d / 2 - t / 2, h / 2), m_body, bevel=.012, seg=2),
             box(name + "_wall", (t, d, h), (-w / 2 + t / 2, 0, h / 2), m_body, bevel=.012, seg=2),
             box(name + "_wall", (t, d, h), (w / 2 - t / 2, 0, h / 2), m_body, bevel=.012, seg=2),
             box(name + "_floor", (w, d, .08), (0, 0, .04), m_body, bevel=.012, seg=2),
             box(name + "_band", (w + .01, d + .01, .10), (0, 0, .13), m_band, bevel=.008, seg=1),
             box(name + "_band", (w + .01, d + .01, .06), (0, 0, h - .09), m_band, bevel=.008, seg=1),
             box(name + "_inner", (w - 2 * t, d - 2 * t, .40), (0, 0, .30), m_in, bevel=0),
             box(name + "_rim", (w, .03, .03), (0, -d / 2 + .02, h + .01), m_frame, bevel=.004, seg=1),
             box(name + "_rim", (w, .03, .03), (0, d / 2 - .02, h + .01), m_frame, bevel=.004, seg=1),
             box(name + "_rim", (.03, d, .03), (-w / 2 + .02, 0, h + .01), m_frame, bevel=.004, seg=1),
             box(name + "_rim", (.03, d, .03), (w / 2 - .02, 0, h + .01), m_frame, bevel=.004, seg=1),
             box(name + "_rim", (.03, d, .04), (0, 0, h + .015), m_frame, bevel=.004, seg=1)]
    cols, rows = int((w - .2) / .10), int((d - .2) / .10)
    for i in range(cols):
        for j in range(rows):
            x = -w / 2 + .12 + i * .10
            y = -d / 2 + .12 + j * .10
            pm = drink_mat(rnd.randrange(8))
            if rnd.random() < .7:
                parts.append(bottle(name + "_bt", (x, y, h - .28), pm, r=.03, h=.22))
            else:
                parts.append(can(name + "_cn", (x, y, h - .28), pm))
    o = join(parts, name, origin=(0, 0, 0))
    lid1 = box(name + "_glass", (w / 2 - .03, d - .06, .008), (-w / 4 + .01, 0, h + .02), m_gl, bevel=0)
    lid2 = box(name + "_glass", (w / 2 - .03, d - .06, .008), (w / 4 - .01, 0, h + .03), m_gl, bevel=0)
    for l in (lid1, lid2):
        l.parent = o
        link(l, c)
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    link(o, c)
    return o


def egg_tray(name, loc, rot_z=0., cols=4, rows=3, c=None):
    m_tray = mat("ERA_EggTray", (.62, .58, .50, 1), rough=.95, var=.10, scale=60, bump=.4)
    m_egg = mat("ERA_Egg", (.90, .78, .60, 1), rough=.6, var=.06, scale=40)
    w, d = cols * .06 + .02, rows * .06 + .02
    parts = [box(name + "_t", (w, d, .035), (0, 0, .0175), m_tray, bevel=.006, seg=1)]
    for i in range(cols):
        for j in range(rows):
            parts.append(ball(name + "_e", .024, (-w / 2 + .04 + i * .06, -d / 2 + .04 + j * .06, .04), m_egg, sub=1, scale=(1, 1, 1.25)))
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    link(o, c)
    return o


def bread_bags(name, loc, n=5, rot_z=0., c=None, seed=2):
    m_b = mat("ERA_Bread", (.86, .62, .30, 1), rough=.7, var=.12, scale=30, bump=.2)
    m_tie = mat("ERA_Gold", GOLD, rough=.45, var=.08, metallic=.3)
    rnd = random.Random(seed)
    parts = []
    for i in range(n):
        x = (i - (n - 1) / 2) * .10
        parts.append(ball(name + "_l", .045, (x, rnd.uniform(-.02, .02), .045), m_b, sub=2, scale=(1, 2.4, 1), rot=(0, 0, rnd.uniform(-.2, .2))))
        parts.append(cyl(name + "_tie", .012, .01, (x, .11, .04), m_tie, verts=8))
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    link(o, c)
    return o


def lamp_string(name, pts, n_bulbs=6, c=None, sag=.12, bulb_color=(1, .92, .72, 1)):
    """Wire hanging between pts (list of 2+ points) with bulbs; wire sags between anchors."""
    m_wire = mat("ERA_Wire", DARK, rough=.6, var=.0)
    m_bulb = emissive("ERA_Bulb", bulb_color, 6.0)
    m_sock = mat("ERA_Socket", DARK, rough=.5, var=.0)
    parts = []
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = Vector(a), Vector(b)
        segs = 10
        prev = a
        for s in range(1, segs + 1):
            t = s / segs
            p = a.lerp(b, t) + Vector((0, 0, -sag * math.sin(math.pi * t)))
            parts.append(tube(name + "_w", prev, p, .004, m_wire, verts=5))
            prev = p
        for i in range(n_bulbs):
            t = (i + .5) / n_bulbs
            p = a.lerp(b, t) + Vector((0, 0, -sag * math.sin(math.pi * t)))
            parts.append(cyl(name + "_s", .012, .03, p + Vector((0, 0, -.02)), m_sock, verts=8))
            parts.append(ball(name + "_b", .022, p + Vector((0, 0, -.06)), m_bulb, sub=1, scale=(1, 1, 1.3)))
    o = join(parts, name, origin=(0, 0, 0))
    link(o, c)
    return o


def plant_pot(name, loc, r=.16, h=.22, c=None, seed=3, m_pot=None):
    m_pot = m_pot or mat("ERA_PotNavy", NAVY, rough=.6, var=.05, scale=10)
    m_soil = mat("ERA_Soil", (.30, .20, .12, 1), rough=.95, var=.15, scale=60, bump=.5)
    m_leaf = mat("ERA_Leaf", (.30, .58, .22, 1), rough=.6, var=.15, scale=20)
    rnd = random.Random(seed)
    parts = [cyl(name + "_pot", r * .8, h, (0, 0, h / 2), m_pot, verts=16, bevel=.008, r2=r),
             cyl(name + "_rim", r * 1.05, .03, (0, 0, h - .015), m_pot, verts=16, bevel=.006),
             cyl(name + "_soil", r * .9, .02, (0, 0, h - .01), m_soil, verts=16)]
    for i in range(9):
        a = rnd.uniform(0, 6.28)
        rr = rnd.uniform(.02, r * .55)
        parts.append(ball(name + "_leaf", rnd.uniform(.07, .12), (rr * math.cos(a), rr * math.sin(a), h + rnd.uniform(.06, .22)), m_leaf, sub=1, scale=(1, 1, rnd.uniform(.8, 1.3))))
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    link(o, c)
    return o


def bottle_crate(name, loc, rot_z=0., c=None, m=None, with_bottles=True, seed=6):
    """Plastic beer/soda crate (open grid) with bottle necks showing."""
    m = m or mat("ERA_CrateNavy", NAVYL, rough=.5, var=.05, scale=10)
    rnd = random.Random(seed)
    w, d, h, t = .40, .30, .30, .015
    parts = [box(name + "_f", (w, d, .02), (0, 0, .01), m, bevel=.003, seg=1)]
    for sy in (-1, 1):
        parts.append(box(name + "_s", (w, t, .07), (0, sy * (d / 2 - t / 2), .045), m, bevel=.003, seg=1))
        parts.append(box(name + "_s", (w, t, .06), (0, sy * (d / 2 - t / 2), h - .03), m, bevel=.003, seg=1))
        for i in range(5):
            parts.append(box(name + "_b", (.015, t, h), (-w / 2 + .02 + i * (w - .04) / 4, sy * (d / 2 - t / 2), h / 2), m, bevel=.002, seg=1))
    for sx in (-1, 1):
        parts.append(box(name + "_s", (t, d, .07), (sx * (w / 2 - t / 2), 0, .045), m, bevel=.003, seg=1))
        parts.append(box(name + "_s", (t, d, .06), (sx * (w / 2 - t / 2), 0, h - .03), m, bevel=.003, seg=1))
        parts.append(box(name + "_b", (t, .015, h), (sx * (w / 2 - t / 2), 0, h / 2), m, bevel=.002, seg=1))
    if with_bottles:
        for i in range(4):
            for j in range(3):
                pm = drink_mat(rnd.randrange(8))
                parts.append(bottle(name + "_bt", (-w / 2 + .05 + i * .10, -d / 2 + .05 + j * .10, .02), pm, r=.03, h=.24))
    o = join(parts, name, origin=(0, 0, 0))
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    link(o, c)
    return o
