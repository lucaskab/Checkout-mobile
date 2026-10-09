"""delivery_decals.py -- printed-texture helper for the delivery previews (Oct 2026).
Draws flat vector art (rounded rects, strokes, circles, Fredoka text) with a Workbench flat render of a temporary scene to a
transparent PNG, then wraps it in a material (decal_mat) so bags, the bau, the tablet and the product labels carry real
printed textures instead of floating geometry.  Loaded by delivery_bike.py (exec) -> uses HERE / srgb from that namespace."""
import bpy, bmesh, math, os
from mathutils import Vector

FONT_DIR = r"C:\Checkout-mobile\unity\CheckoutSimulator\Assets\Resources\CheckoutDesktop\Fonts"
FONT_B, FONT_S, FONT_N = "Fredoka_700Bold.ttf", "Fredoka_600SemiBold.ttf", "Nunito_700Bold.ttf"
DECAL_DIR = os.path.join(HERE, "render", "decals")
_fonts = {}
def _font(fn):
    if fn not in _fonts:
        try: _fonts[fn] = bpy.data.fonts.load(os.path.join(FONT_DIR, fn))
        except Exception: _fonts[fn] = None
    return _fonts[fn]

def _lin(c):
    if isinstance(c, str): return srgb(c)
    return tuple(c) if len(c) == 4 else tuple(c) + (1.,)

class Canvas:
    """Design space = pixels, origin lower-left, y up.  1 px = 0.01 Blender unit."""
    def __init__(s, name, w, h, scale=1.0):
        s.name, s.w, s.h, s.k = name, w, h, 0.01; s.zz = 0.
        s.sc = bpy.data.scenes.new("_dc_" + name); sc = s.sc
        sc.render.engine = 'BLENDER_WORKBENCH'
        sh = sc.display.shading; sh.light = 'FLAT'; sh.color_type = 'MATERIAL'; sh.show_object_outline = False; sh.show_specular_highlight = False
        sc.display.render_aa = '32'
        sc.render.film_transparent = True; sc.render.resolution_x = int(w * scale); sc.render.resolution_y = int(h * scale); sc.render.resolution_percentage = 100
        sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
        sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
        cam = bpy.data.objects.new("_dc_cam", bpy.data.cameras.new("_dc_cam")); sc.collection.objects.link(cam)
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(w, h) * s.k; cam.location = (w * s.k / 2, h * s.k / 2, 10); sc.camera = cam
        s._mats = {}; s.objs = [cam]
    def _m(s, color):
        c = _lin(color); key = tuple(round(v, 4) for v in c)
        if key not in s._mats:
            m = bpy.data.materials.new("_dc_m"); m.diffuse_color = c; s._mats[key] = m
        return s._mats[key]
    def _link(s, o, color):
        s.sc.collection.objects.link(o); o.data.materials.append(s._m(color)); s.objs.append(o); return o
    def poly(s, pts, color):
        s.zz += .001; bm = bmesh.new(); vs = [bm.verts.new((x * s.k, y * s.k, s.zz)) for x, y in pts]
        try: bm.faces.new(vs)
        except Exception: pass
        bmesh.ops.triangulate(bm, faces=bm.faces[:]) if len(vs) > 4 else None
        me = bpy.data.meshes.new("_dc_p"); bm.to_mesh(me); bm.free(); return s._link(bpy.data.objects.new("_dc_p", me), color)
    def rrect(s, cx, cy, w, h, r, color, rot=0., n=10):
        r = min(r, w / 2, h / 2); pts = []
        for (ox, oy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
            for i in range(n + 1):
                a = math.radians(a0 + 90 * i / n); pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
        c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        return s.poly([(cx + x * c - y * sn, cy + x * sn + y * c) for x, y in pts], color)
    def circle(s, cx, cy, r, color, n=48): return s.poly([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)], color)
    def stroke(s, pts, width, color, caps=True):
        pts = [Vector(p) for p in pts]
        for a, b in zip(pts[:-1], pts[1:]):
            d = (b - a); 
            if d.length < 1e-6: continue
            nrm = Vector((-d.y, d.x)).normalized() * width / 2
            s.poly([a + nrm, b + nrm, b - nrm, a - nrm], color)
        if caps:
            for p in pts: s.circle(p.x, p.y, width / 2, color, 20)
    def arc(s, cx, cy, r, a0, a1, width, color, n=32):
        s.stroke([(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)], width, color)
    def text(s, body, x, y, size, color, font=None, align='CENTER', rot=0., spacing=1.0):
        s.zz += .001; cu = bpy.data.curves.new("_dc_t", 'FONT'); cu.body = body; cu.size = size * s.k; cu.align_x = align; cu.align_y = 'CENTER'; cu.space_character = spacing
        f = _font(font or FONT_B)
        if f: cu.font = f
        o = bpy.data.objects.new("_dc_t", cu); o.location = (x * s.k, y * s.k, s.zz); o.rotation_euler = (0, 0, math.radians(rot)); return s._link(o, color)
    def render(s, path):
        os.makedirs(os.path.dirname(path), exist_ok=True); s.sc.render.filepath = path
        bpy.ops.render.render(write_still=True, scene=s.sc.name)
        for o in s.objs:
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d.users == 0:
                (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.curves if isinstance(d, bpy.types.TextCurve) else bpy.data.cameras).remove(d)
        for m in s._mats.values(): bpy.data.materials.remove(m)
        bpy.data.scenes.remove(s.sc)
        old = bpy.data.images.get(os.path.basename(path))
        if old: bpy.data.images.remove(old)
        img = bpy.data.images.load(path); img.name = os.path.basename(path); img.pack(); return img

def decal_mat(name, img, rough=.55, emit=0., bump=0., spec=.5, coat=0., mult=None, extension='CLIP'):
    """Printed decal material: image colour + alpha; optional emission (screens) and light paper-fibre bump."""
    m = bpy.data.materials.get("DK_" + name) or bpy.data.materials.new("DK_" + name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.extension = extension; t.interpolation = 'Cubic'
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = spec
    if coat: b.inputs["Coat Weight"].default_value = coat
    col = t.outputs["Color"]
    if mult is not None:
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1; nt.links.new(col, mx.inputs[6]); mx.inputs[7].default_value = mult; col = mx.outputs[2]
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    if emit:
        nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = emit
    if bump:
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 900; nz.inputs["Detail"].default_value = 3
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = .0005
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def decal_plane(name, w, h, loc, rot, m, parent=None):
    """Flat quad (w x h metres) facing local +Z, with UVs 0-1 and the decal material."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(p) for p in ((-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0))]; f = bm.faces.new(vs)
    for l, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): l[uv].uv = (u, v)
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; me.materials.append(m)
    for p in me.polygons: p.use_smooth = False
    if parent is not None: o.parent = parent
    return o

# ---------------------------------------------------------------- artwork
NAVY, BLUE_C, ORANGE_C, WHITE_C, GOLD_C = "#17324D", "#2E8CAE", "#F0A030", "#FFFFFF", "#D9A441"

def bag_icon(c, cx, cy, size, body, handle, accent=None, tick=ORANGE_C):
    """Shopping-bag pictogram: rounded body, ring handle, check mark."""
    w = size; h = size * .84
    c.arc(cx, cy + h * .50 - size * .04, size * .24, 12, 168, size * .075, handle)
    c.rrect(cx, cy - size * .02, w, h, size * .12, body)
    c.rrect(cx, cy + h / 2 - size * .22, w * .96, size * .028, size * .01, accent or handle) if accent else None
    c.stroke([(cx - size * .17, cy - size * .02), (cx - size * .04, cy - size * .15), (cx + size * .20, cy + size * .10)], size * .085, tick)

def decal_bau_logo():
    c = Canvas("bau_logo", 900, 700)
    bag_icon(c, 450, 495, 250, WHITE_C, WHITE_C, None, ORANGE_C)
    c.text("DELIVERY", 450, 290, 190, WHITE_C, FONT_B)
    c.rrect(450, 190, 560, 10, 5, ORANGE_C)
    c.text("CHECKOUT", 450, 110, 92, WHITE_C, FONT_S, spacing=1.12)
    c.text("supermercado", 450, 42, 46, "#CFE9F2", FONT_N, spacing=1.05)
    return c.render(os.path.join(DECAL_DIR, "bau_logo.png"))

def qr_modules(c, cx, cy, size, ink="#14202B", n=21, seed=7):
    """Pseudo QR code (finder squares + pseudo-random modules, deterministic)."""
    m = size / n; x0 = cx - size / 2; y0 = cy - size / 2
    def fin(i0, j0):
        for i in range(7):
            for j in range(7):
                on = i in (0, 6) or j in (0, 6) or (2 <= i <= 4 and 2 <= j <= 4)
                if on: c.poly([(x0 + (i0 + i) * m, y0 + (j0 + j) * m), (x0 + (i0 + i + 1) * m, y0 + (j0 + j) * m), (x0 + (i0 + i + 1) * m, y0 + (j0 + j + 1) * m), (x0 + (i0 + i) * m, y0 + (j0 + j + 1) * m)], ink)
    fin(0, 0); fin(n - 7, 0); fin(0, n - 7)
    r = seed
    for i in range(n):
        for j in range(n):
            if (i < 8 and j < 8) or (i >= n - 8 and j < 8) or (i < 8 and j >= n - 8): continue
            r = (r * 1103515245 + 12345) & 0x7fffffff
            if (r >> 16) % 5 < 2:
                c.poly([(x0 + i * m, y0 + j * m), (x0 + (i + 1) * m, y0 + j * m), (x0 + (i + 1) * m, y0 + (j + 1) * m), (x0 + i * m, y0 + (j + 1) * m)], ink)

def decal_bau_lid():
    c = Canvas("bau_lid", 1200, 420)
    bag_icon(c, 190, 215, 190, WHITE_C, WHITE_C, None, ORANGE_C)
    c.text("CHECKOUT", 700, 255, 170, WHITE_C, FONT_B, spacing=1.06)
    c.rrect(700, 150, 780, 12, 6, ORANGE_C)
    c.text("supermercado  •  delivery", 700, 85, 62, "#CFE9F2", FONT_N)
    return c.render(os.path.join(DECAL_DIR, "bau_lid.png"))

def decal_bau_sticker():
    c = Canvas("bau_sticker", 640, 420)
    c.rrect(320, 210, 620, 400, 34, "#F4F1E6"); c.rrect(320, 210, 600, 380, 28, "#FFFFFF")
    c.rrect(320, 372, 600, 70, 26, BLUE_C); c.rrect(320, 345, 600, 30, 4, BLUE_C)
    c.text("PEDIDO  #128", 320, 372, 52, WHITE_C, FONT_B)
    qr_modules(c, 170, 190, 220)
    c.text("Ana S.", 440, 235, 50, NAVY, FONT_B, align='LEFT')
    c.text("R. das Flores, 12", 390, 180, 30, "#4A5A68", FONT_N, align='LEFT')
    c.text("2,1 km • 14:32", 390, 135, 30, "#4A5A68", FONT_N, align='LEFT')
    c.rrect(500, 70, 190, 52, 10, "#D8352A"); c.text("FRÁGIL", 500, 70, 36, WHITE_C, FONT_B)
    return c.render(os.path.join(DECAL_DIR, "bau_sticker.png"))

def decal_plate():
    c = Canvas("plate", 520, 260)
    c.rrect(260, 130, 510, 250, 24, "#14202B"); c.rrect(260, 130, 486, 226, 18, "#F3F2EA")
    c.rrect(260, 214, 486, 56, 14, BLUE_C); c.text("BRASIL", 260, 214, 36, WHITE_C, FONT_B)
    c.text("CKT 2E26", 260, 108, 120, "#14202B", FONT_B, spacing=1.0)
    return c.render(os.path.join(DECAL_DIR, "plate.png"))
