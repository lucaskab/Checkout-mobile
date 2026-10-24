"""Padaria puzzle art (PREVIEW ONLY, nothing goes into Unity from here).

Builds the bread pieces of the bakery block-packing mini-game (raw + baked), the baking tray, the bench backdrop and
two mockups, rendered straight down with an orthographic camera (Cycles GPU + denoise), warm sun from the top-left.

    import sys; sys.path.insert(0, r"C:\\Checkout-mobile\\scripts\\blender")
    import importlib, puzzle_padaria as pp; importlib.reload(pp)
    pp.run()                       # everything: build, render, mockups, save the .blend
    pp.build(); pp.render_bread("baguete", "baked")   # single sprite while iterating

Scale: 1 grid cell = 0.1 m = 200 px. Sprites are the VERTICAL footprint of the piece (long axis = image Y).
Outputs: unity/CheckoutSimulator/Temp/qa/puzzle_padaria/ ; source: ArtSource/puzzle_padaria/padaria_puzzle.blend
No text / letters / numbers anywhere.
"""
import math
import os
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

ROOT = r"C:\Checkout-mobile"
UNITY = os.path.join(ROOT, "unity", "CheckoutSimulator")
OUT = os.path.join(UNITY, "Temp", "qa", "puzzle_padaria")
BLEND = os.path.join(UNITY, "ArtSource", "puzzle_padaria", "padaria_puzzle.blend")

CELL = 0.1          # metres per grid cell
PX = 200            # pixels per grid cell
SCENE = "Padaria"

# id: (cells wide, cells tall) in the vertical orientation
BREADS = {"frances": (1, 1), "forma": (1, 2), "baguete": (1, 3), "tranca": (1, 4), "redondo": (2, 2)}
# where each bread lives in the .blend (x offset); raw row at y=0, baked row at y=ROW
SLOT = {"frances": 0.0, "forma": 0.5, "baguete": 1.0, "tranca": 1.5, "redondo": 2.1}
ROW = 1.0


# ============================================================================================ small utilities
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c) + (1.0,)


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def col(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in parent.children]:
        parent.children.link(c)
    return c


def wipe_collection(name):
    c = bpy.data.collections.get(name)
    if not c:
        return
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def link(ob, collection):
    collection.objects.link(ob)
    return ob


def mesh_object(name, bm, mat, collection, subsurf=1, smooth_shade=True):
    me = bpy.data.meshes.get(name)
    if me:
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    if smooth_shade:
        for f in bm.faces:
            f.smooth = True
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
    ob = bpy.data.objects.new(name, me)
    if mat:
        me.materials.append(mat)
    if subsurf:
        m = ob.modifiers.new("Subsurf", "SUBSURF")
        m.levels = 0
        m.render_levels = subsurf
    link(ob, collection)
    return ob


# ============================================================================================ node builder
class NB:
    """Tiny shader-graph builder: values that are sockets get linked, everything else becomes a default."""

    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.x = 0

    def node(self, kind, outputs=None, **inputs):
        n = self.nt.nodes.new(kind)
        n.location = (self.x, 0)
        self.x += 40
        for k, v in inputs.items():
            if k.startswith("_"):
                setattr(n, k[1:], v)
                continue
            sock = next((s for s in n.inputs if s.name == k and s.enabled), None) or n.inputs[k]
            if isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, sock)
            else:
                sock.default_value = v
        return n

    def math(self, op, a, b=0.0, clamp=False):
        n = self.node("ShaderNodeMath", _operation=op, _use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, n.inputs[i])
            else:
                n.inputs[i].default_value = v
        return n.outputs[0]

    def add(self, *xs):
        s = xs[0]
        for x in xs[1:]:
            s = self.math("ADD", s, x)
        return s

    def mul(self, a, b):
        return self.math("MULTIPLY", a, b)

    def mapr(self, v, a, b, c=0.0, d=1.0, interp="SMOOTHSTEP"):
        return self.node("ShaderNodeMapRange", Value=v, **{"From Min": a, "From Max": b, "To Min": c, "To Max": d},
                         _interpolation_type=interp, _clamp=True).outputs[0]

    def mix(self, f, a, b):
        return self.node("ShaderNodeMixRGB", Factor=f, Color1=a, Color2=b).outputs[0]

    def ramp(self, f, stops):
        n = self.node("ShaderNodeValToRGB", Factor=f)
        els = n.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        els[0].position, els[0].color = stops[0][0], stops[0][1]
        for p, c in stops[1:]:
            e = els.new(p)
            e.color = c
        return n.outputs[0]

    def noise(self, vec, scale, detail=4.0, rough=.55, dist=0.0):
        n = self.node("ShaderNodeTexNoise", Vector=vec, Scale=scale, Detail=detail, Roughness=rough, Distortion=dist)
        return n.outputs[0]

    def sep(self, vec):
        n = self.node("ShaderNodeSeparateXYZ", Vector=vec)
        return n.outputs

    def bsdf(self, **kw):
        b = self.node("ShaderNodeBsdfPrincipled", **kw)
        o = self.node("ShaderNodeOutputMaterial")
        self.nt.links.new(b.outputs[0], o.inputs["Surface"])
        return b


# ============================================================================================ bread materials
CRUST = {   # (position, sRGB hex) — ramp of the baked crust, light -> dark
    "frances": [(0, "F7D58E"), (.3, "EDAE55"), (.55, "D98A33"), (.8, "B5621E"), (1, "8A4316")],
    "forma":   [(0, "F7D58E"), (.3, "EBA548"), (.55, "CF7A26"), (.8, "A8541A"), (1, "7A3812")],
    "baguete": [(0, "F5CF85"), (.3, "E9A64D"), (.55, "D3822E"), (.8, "A95A1C"), (1, "7C3D13")],
    "tranca":  [(0, "F8D27E"), (.3, "EC9F3E"), (.55, "CD7120"), (.8, "9F4A15"), (1, "6E300D")],
    "redondo": [(0, "F4D190"), (.3, "E5A755"), (.55, "CC8438"), (.8, "A35E25"), (1, "70391A")],
}
DOUGH = {   # raw dough: light, dark
    "frances": ("F6EBD3", "E9D6B1"),
    "forma":   ("F7EBD0", "EBD7AE"),
    "baguete": ("F5E9D0", "E6D2AC"),
    "tranca":  ("FAE4A9", "EFCF86"),      # egg-enriched dough, yellower
    "redondo": ("EFE0C2", "DCC59C"),      # a little whole-wheat
}
OPTS = {    # per bread: height (m), flour raw/baked, rings, gloss raw/baked (coat), roughness raw/baked, blisters
    "frances": dict(H=.046, flour=(.25, .10), rings=False, coat=(0, .15), rough=(.55, .42), blister=.6, crev=0),
    "forma":   dict(H=.062, flour=(.18, .0), rings=False, coat=(.15, .55), rough=(.5, .33), blister=0, crev=.4),
    "baguete": dict(H=.046, flour=(.30, .14), rings=False, coat=(0, .1), rough=(.55, .45), blister=1.0, crev=0),
    "tranca":  dict(H=.052, flour=(0, 0), rings=False, coat=(.35, .85), rough=(.42, .22), blister=0, crev=1.0),
    "redondo": dict(H=.088, flour=(.85, .65), rings=True, coat=(0, 0), rough=(.65, .62), blister=.3, crev=0),
}


def bread_material(bid, state):
    name = "M_%s_%s" % (bid, state)
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    o = OPTS[bid]
    baked = state == "baked"
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    geo = nb.node("ShaderNodeNewGeometry")
    nz = nb.sep(geo.outputs["Normal"])[2]
    pz = nb.sep(tc)[2]
    px, py = nb.sep(tc)[0], nb.sep(tc)[1]
    hgt = nb.math("DIVIDE", pz, o["H"], clamp=True)
    score = nb.node("ShaderNodeAttribute", _attribute_name="score").outputs["Factor"]
    ear = nb.node("ShaderNodeAttribute", _attribute_name="ear").outputs["Factor"]
    n_broad = nb.noise(tc, 28, 5, .55, .2)
    n_mid = nb.noise(tc, 90, 6, .6)
    n_fine = nb.noise(tc, 420, 8, .65)
    up = nb.mapr(nz, .15, .85)

    # ---- base colour
    if baked:
        # browning: higher on top, mottled, darker where it turns down (edges), much darker on the ear lips
        b = nb.add(nb.mul(hgt, .32), nb.mul(n_broad, .55), nb.mul(n_mid, .25), nb.mul(nb.math("SUBTRACT", 1.0, up), .22),
                   nb.mul(ear, .55), -.18)
        crust = nb.ramp(b, [(p, srgb(h)) for p, h in CRUST[bid]])
        # opened score: pale golden "crumb" band with toasty texture
        crumb = nb.ramp(nb.add(nb.mul(n_mid, .6), nb.mul(n_fine, .3), nb.mul(score, -.25), .05),
                        [(0, srgb("FBE7B8")), (.45, srgb("F3CC80")), (.8, srgb("E3A452")), (1, srgb("C98236"))])
        base = nb.mix(nb.mapr(score, .12, .5), crust, crumb)
        if o["crev"]:
            ao = nb.node("ShaderNodeAmbientOcclusion", Distance=.012, _samples=12).outputs["AO"]
            pale = nb.ramp(n_mid, [(0, srgb("F6D594")), (1, srgb("EBB868"))])
            base = nb.mix(nb.mul(nb.mapr(ao, .95, .55), o["crev"]), base, pale)
    else:
        d0, d1 = DOUGH[bid]
        base = nb.ramp(nb.add(nb.mul(n_broad, .8), nb.mul(n_fine, .3), -.35), [(.2, srgb(d0)), (.8, srgb(d1))])
        # fresh cut is wetter and a touch darker / yellower
        base = nb.mix(nb.mul(nb.mapr(score, .05, .6), .55), base, srgb("E4C792"))
        if o["crev"]:
            ao = nb.node("ShaderNodeAmbientOcclusion", Distance=.012, _samples=12).outputs["AO"]
            base = nb.mix(nb.mul(nb.mapr(ao, .95, .5), .35 * o["crev"]), base, srgb(d1))

    # ---- flour dusting
    famt = o["flour"][1 if baked else 0]
    flour = None
    if famt > 0:
        n_fl = nb.noise(tc, 14, 6, .62, .4)
        patch = nb.mapr(n_fl, .58 - famt * .25, .7 - famt * .12)
        if o["rings"]:   # banneton rings: concentric floury bands
            r = nb.node("ShaderNodeVectorMath", Vector=tc, _operation="LENGTH").outputs["Value"]
            ringv = nb.math("SINE", nb.add(nb.mul(r, 2 * math.pi / .0085), nb.mul(n_broad, 3.0)))
            rings = nb.mapr(ringv, -.25, .65)
            patch = nb.math("MAXIMUM", nb.mul(patch, .55), nb.mul(rings, nb.mapr(n_fl, .3, .55)))
        speck = nb.mapr(nb.noise(tc, 900, 3, .7), .35, .65)
        flour = nb.mul(nb.mul(nb.mul(patch, up), nb.add(nb.mul(speck, .45), .55)), min(1.0, famt * 1.25))
        if baked:
            flour = nb.mul(flour, nb.math("SUBTRACT", 1.0, nb.mapr(score, .02, .25)))
            flour = nb.mul(flour, nb.math("SUBTRACT", 1.0, nb.mapr(ear, .1, .5)))
        fcol = srgb("FFFBF2") if not baked else srgb("FBF2E2")
        base = nb.mix(flour, base, fcol)

    # ---- surface relief (bump)
    h = nb.add(nb.mul(n_fine, .5), nb.mul(n_mid, .5))
    if o["blister"] and baked:
        vor = nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=260, Randomness=1.0, _feature="SMOOTH_F1").outputs["Distance"]
        bl = nb.mul(nb.mapr(vor, .05, .32, 1, 0), nb.mapr(nb.noise(tc, 30, 3), .45, .6))
        h = nb.add(h, nb.mul(bl, .9 * o["blister"]))
        base = nb.mix(nb.mul(bl, .25 * o["blister"]), base, srgb("9C5018"))
    if flour is not None:
        h = nb.add(h, nb.mul(flour, .4))
    bump = nb.node("ShaderNodeBump", Height=h, Strength=.22 if baked else .12, Distance=.0012)

    rough = o["rough"][1 if baked else 0]
    rough_s = nb.add(rough, nb.mul(n_mid, .12)) if flour is None else nb.mix(flour, (rough,) * 3 + (1,), (.95, .95, .95, 1))
    if flour is not None:
        rough_s = nb.sep(rough_s)[0] if False else nb.node("ShaderNodeRGBToBW", Color=rough_s).outputs[0]
    coat = o["coat"][1 if baked else 0]
    if flour is not None and coat:
        coat = nb.mul(coat, nb.math("SUBTRACT", 1.0, flour))
    nb.bsdf(**{"Base Color": base, "Roughness": rough_s, "Normal": bump.outputs[0],
               "Subsurface Weight": .06 if baked else .25, "Subsurface Radius": (1.0, .55, .3), "Subsurface Scale": .004,
               "Coat Weight": coat, "Coat Roughness": .18, "Coat Normal": bump.outputs[0],
               "Sheen Weight": 0.0 if baked else .25, "Sheen Roughness": .4, "Specular IOR Level": .45})
    return mat


def sugar_material():
    mat = bpy.data.materials.get("M_pearl_sugar") or bpy.data.materials.new("M_pearl_sugar")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 1500, 3)
    nb.bsdf(**{"Base Color": nb.ramp(n, [(0, srgb("FFFFFF")), (1, srgb("F3EEE4"))]), "Roughness": .35,
               "Subsurface Weight": .4, "Subsurface Radius": (1, 1, 1), "Subsurface Scale": .002,
               "Normal": nb.node("ShaderNodeBump", Height=n, Strength=.5, Distance=.0004).outputs[0]})
    return mat


# ============================================================================================ bread geometry
def cube_sphere(n):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=n, use_grid_fill=True)
    for v in bm.verts:
        v.co = v.co.normalized()
    return bm


def loaf(bm, L, W, H, n=2.0, m=2.0, side=2.0, bottom=.14, lump=.025, seed=0):
    """Maps the unit sphere to a loaf: length L along Y, width W, crown H; superellipse length profile (n, m),
    cross-section exponent `side` (>2 = fuller sides), nearly flat bottom. Lumpy with low-frequency noise."""
    off = Vector((seed * 7.31, seed * 3.17, seed * 1.93))
    for v in bm.verts:
        x, y, z = v.co
        rc = math.hypot(x, z)
        ay = min(1.0, abs(y))
        prof = max(0.0, 1 - ay ** n) ** (1 / m)
        if rc < 1e-9:
            ux, uz = 0.0, 1.0
        else:
            ux, uz = x / rc, z / rc
        r = (abs(ux) ** side + abs(uz) ** side) ** (-1 / side)
        X = ux * r * prof * W / 2
        Z = uz * r * prof * (H - bottom * H if uz > 0 else bottom * H)
        Y = math.copysign(ay, y) * L / 2
        p = Vector((X, Y, Z + bottom * H))
        k = 1 + lump * noise.fractal(p * 38 + off, .6, 2.0, 3) + lump * .5 * noise.noise(p * 90 + off)
        v.co = Vector((X * (1 + (k - 1) * .5), Y, (Z + bottom * H) * k if uz > 0 else Z + bottom * H))
    return bm


def apply_scores(bm, scores, baked, w_scale=1.0):
    """scores: list of (p0, p1, width, depth, ear_side) in XY. Grooves + ear lips; writes 'score' / 'ear' attrs."""
    ls = bm.verts.layers.float.get("score") or bm.verts.layers.float.new("score")
    le = bm.verts.layers.float.get("ear") or bm.verts.layers.float.new("ear")
    zmax = max(v.co.z for v in bm.verts)
    for v in bm.verts:
        p = v.co
        top = smooth(.25, .6, p.z / zmax)
        best_g, best_e, dz = 0.0, 0.0, 0.0
        for (a, b, w, depth, side) in scores:
            a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
            ab = b - a
            ln = ab.length
            t = (Vector((p.x, p.y, 0)) - a).dot(ab) / (ln * ln)
            if t <= 0 or t >= 1:
                continue
            nrm = Vector((-ab.y, ab.x, 0)) / ln
            d = (Vector((p.x, p.y, 0)) - a).dot(nrm)
            fade = math.sin(math.pi * t) ** .55
            ww = w * w_scale * fade + 1e-6
            u = d / ww
            g = max(0.0, 1 - u * u) ** 2 * top
            # baked: the grigne swells back up a bit in the middle of the groove
            cut = depth * fade * (g - (.45 * max(0.0, 1 - (u / .55) ** 2) ** 2 * top if baked else 0))
            e = 0.0
            if baked:
                if side == 0:
                    e = math.exp(-((abs(u) - 1.05) / .32) ** 2)
                else:
                    e = math.exp(-((u * side - 1.0) / .38) ** 2) + .35 * math.exp(-((u * side + 1.05) / .3) ** 2)
                e *= fade * top
            if g > best_g:
                best_g = g * fade
            best_e = max(best_e, e)
            dz = min(dz, -cut) if cut > 0 else dz
            dz += e * depth * .55 if baked else 0
        v.co.z += dz
        v[ls] = best_g
        v[le] = best_e
    return bm


def bread_bm(bid, baked, seed=1):
    """Returns the bmesh of a bread centred at the origin, sitting on z=0, long axis on Y."""
    fw, fh = BREADS[bid]
    s = 1.0 if baked else .94           # oven spring: raw dough is a touch smaller and much flatter
    hs = 1.0 if baked else .72
    H = OPTS[bid]["H"] * hs
    if bid == "frances":
        bm = loaf(cube_sphere(70), .086 * s, .066 * s, H, n=2.1, m=1.25, side=2.3, lump=.02, seed=seed)
        sc = [((.004, -.031), (-.003, .031), .0105, .010, 1)]
        apply_scores(bm, sc, baked, 1.0 if baked else .35)
    elif bid == "baguete":
        bm = loaf(cube_sphere(100), .280 * s, .066 * s, H, n=2.6, m=1.4, side=2.2, lump=.02, seed=seed)
        sc = []
        for i, cy in enumerate((-.082, 0.0, .082)):
            a = math.radians(14)
            l = .102
            dx, dy = math.sin(a) * l / 2, math.cos(a) * l / 2
            sc.append(((-dx, cy - dy), (dx, cy + dy), .0085, .009, 1))
        apply_scores(bm, sc, baked, 1.0 if baked else .35)
    elif bid == "redondo":
        bm = loaf(cube_sphere(110), .172 * s, .172 * s, H, n=2.0, m=2.0, side=2.6, bottom=.12, lump=.018, seed=seed)
        # sphere: make the planform truly round (loaf() maps the length axis with the same superellipse)
        sc = [((-.064, 0), (.064, 0), .019, .02, 0), ((0, -.064), (0, .064), .019, .02, 0)]
        apply_scores(bm, sc, baked, 1.0 if baked else .3)
    elif bid == "forma":
        L, W = .184 * s, .088 * s
        bm = loaf(cube_sphere(100), L, W, H, n=5.0, m=3.0, side=3.2, bottom=.12, lump=.015, seed=seed)
        # three dough balls in the tin: creases across the top
        zmax = max(v.co.z for v in bm.verts)
        for v in bm.verts:
            top = smooth(.35, .8, v.co.z / zmax)
            k = 0.0
            for yk in (-L / 6, L / 6):
                k = max(k, math.exp(-((v.co.y - yk) / (.0075 if baked else .0105)) ** 2))
            lobe = math.cos(3 * math.pi * v.co.y / L) ** 2
            v.co.z -= top * (k * H * (.13 if baked else .2) + (1 - lobe) * H * .03)
        sl = bm.verts.layers.float.new("score")
        bm.verts.layers.float.new("ear")
    elif bid == "tranca":
        bm = braid_bm(baked, seed)
    else:
        raise ValueError(bid)
    if "score" not in bm.verts.layers.float:
        bm.verts.layers.float.new("score")
    if "ear" not in bm.verts.layers.float:
        bm.verts.layers.float.new("ear")
    return bm


def braid_bm(baked, seed=0):
    """Three-strand braid (trança): Lissajous braid (x = sin, z = sin 2θ), fat overlapping strands, pinched ends."""
    s = 1.0 if baked else .94
    L = .368 * s
    A = .0205 * s
    R = .0215 * s
    B = .0072 * (1 if baked else .75)
    zs = 1.0 if baked else .74
    periods = 2.25
    bm = bmesh.new()
    N, SEG = 260, 28
    rnd = random.Random(seed)
    for k in range(3):
        ph = 2 * math.pi * k / 3
        pts = []
        for i in range(N + 1):
            t = i / N
            th = 2 * math.pi * periods * t + ph
            end = math.sin(math.pi * t) ** .45
            x = A * math.sin(th) * (.35 + .65 * end)
            y = (t - .5) * L * .97
            z = B * math.sin(2 * th) * end
            pts.append((x, y, z))
        rings = []
        prev = None
        for i, p in enumerate(pts):
            p = Vector(p)
            t = i / N
            tan = (Vector(pts[min(i + 1, N)]) - Vector(pts[max(i - 1, 0)])).normalized()
            nrm = Vector((1, 0, 0)) if prev is None else prev
            nrm = (nrm - tan * nrm.dot(tan)).normalized()
            prev = nrm
            bi = tan.cross(nrm)
            th = 2 * math.pi * periods * t + ph
            # strands are fuller where they lie on top, thinner where they dive under
            rr = R * (.42 + .58 * math.sin(math.pi * t) ** .5) * (1 + .1 * math.sin(2 * th))
            ring = []
            for j in range(SEG):
                a = 2 * math.pi * j / SEG
                q = p + (nrm * math.cos(a) + bi * math.sin(a)) * rr
                ring.append(bm.verts.new(q))
            rings.append(ring)
        for i in range(N):
            for j in range(SEG):
                bm.faces.new((rings[i][j], rings[i][(j + 1) % SEG], rings[i + 1][(j + 1) % SEG], rings[i + 1][j]))
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / SEG)
            for j in range(SEG):
                f = (ring[j], ring[(j + 1) % SEG], c)
                bm.faces.new(tuple(reversed(f)) if rev else f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # lumpiness, vertical squash, sit on z=0
    off = Vector((seed * 3.1, 1.7, .3))
    for v in bm.verts:
        p = v.co
        k = 1 + .03 * noise.fractal(p * 45 + off, .6, 2.0, 3)
        v.co = Vector((p.x * k, p.y, p.z * zs * k))
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
        if v.co.z < .0025:             # flat underside where it touches the tray
            v.co.z = .0025 * (v.co.z / .0025) ** .3 if v.co.z > 0 else 0
    return bm


def scatter_sugar(target, count=150, seed=3):
    """Pearl sugar nibs dropped onto the top of `target` (an object), returns one object."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = target.evaluated_get(dg)
    me = ev.to_mesh()
    bvh = BVHTree.FromPolygons([target.matrix_world @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons])
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    ev.to_mesh_clear()
    rnd = random.Random(seed)
    bm = bmesh.new()
    ox, oy = target.location.x, target.location.y
    placed = 0
    tries = 0
    while placed < count and tries < count * 20:
        tries += 1
        x = ox + rnd.uniform(min(xs), max(xs)) * .85
        y = oy + rnd.uniform(min(ys), max(ys)) * .9
        hit = bvh.ray_cast(Vector((x, y, 1)), Vector((0, 0, -1)))
        if hit[0] is None or hit[1].z < .75:
            continue
        r = rnd.uniform(.0011, .0021)
        tmp = bmesh.new()
        bmesh.ops.create_icosphere(tmp, subdivisions=2, radius=1)
        sx, sy, sz = rnd.uniform(.8, 1.3), rnd.uniform(.8, 1.3), rnd.uniform(.6, .9)
        for v in tmp.verts:
            d = 1 + .18 * noise.noise(v.co * 2.3 + Vector((placed, 0, 0)))
            v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz)) * r * d
        M = Matrix.Translation(hit[0] - hit[1] * r * .25) @ hit[1].to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z")
        bmesh.ops.transform(tmp, matrix=M, verts=tmp.verts)
        me2 = bpy.data.meshes.new("_t")
        tmp.to_mesh(me2)
        tmp.free()
        bm.from_mesh(me2)
        bpy.data.meshes.remove(me2)
        placed += 1
    for v in bm.verts:
        v.co -= target.location
    return bm


def build_breads():
    sc = bpy.context.scene
    groot = col("Breads")
    for state in ("raw", "baked"):
        c = col("Breads " + state, groot)
        wipe_collection(c.name)
        for bid in BREADS:
            mat = bread_material(bid, state)
            bm = bread_bm(bid, state == "baked", seed=hash(bid) % 97)
            ob = mesh_object("%s_%s" % (bid, state), bm, mat, c, subsurf=1)
            ob.location = (SLOT[bid], ROW if state == "baked" else 0.0, 0.0005)
            if bid == "tranca" and state == "baked":
                bpy.context.view_layer.update()
                sbm = scatter_sugar(ob, 170)
                so = mesh_object("tranca_baked_sugar", sbm, sugar_material(), c, subsurf=0)
                so.location = ob.location
    # shadow catcher under all breads
    gc = col("Studio")
    sh = bpy.data.objects.get("ShadowCatcher")
    if not sh:
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=2.0)
        sh = mesh_object("ShadowCatcher", bm, None, gc, subsurf=0)
    sh.location = (1.2, .5, 0)
    sh.is_shadow_catcher = True


# ============================================================================================ studio / render
def setup_scene():
    sc = bpy.data.scenes.get(SCENE)
    if not sc:
        sc = bpy.context.scene
        sc.name = SCENE
    bpy.context.window.scene = sc
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.refresh_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception:
        pass
    sc.cycles.samples = 160
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = .015
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.render.film_transparent = True
    sc.cycles.film_transparent_glass = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Standard"
    try:
        sc.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = -.15
    sc.unit_settings.system = "METRIC"
    # world: warm soft ambient
    w = bpy.data.worlds.get("Padaria") or bpy.data.worlds.new("Padaria")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background") or w.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = srgb("F2E6D6")
    bg.inputs[1].default_value = .55
    gc = col("Studio")
    # key: warm sun from the top-left of the picture (image up = +Y, left = -X)
    sun = bpy.data.objects.get("Sun_TopLeft")
    if not sun:
        sun = link(bpy.data.objects.new("Sun_TopLeft", bpy.data.lights.new("Sun_TopLeft", "SUN")), gc)
    sun.data.energy = 3.6
    sun.data.color = (1.0, .93, .82)
    sun.data.angle = math.radians(18)
    d = Vector((1.0, -1.15, -2.9)).normalized()      # direction the light travels
    sun.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam = bpy.data.objects.get("Cam_Top")
    if not cam:
        cam = link(bpy.data.objects.new("Cam_Top", bpy.data.cameras.new("Cam_Top")), gc)
    cam.data.type = "ORTHO"
    cam.rotation_euler = (0, 0, 0)
    cam.data.clip_start = .01
    cam.data.clip_end = 10
    sc.camera = cam
    os.makedirs(OUT, exist_ok=True)
    return sc


def shoot(center, size_m, res, path, transparent=True, visible=None):
    """Top-down ortho render of the rectangle `size_m` centred at `center`; only objects in `visible` render."""
    sc = bpy.context.scene
    cam = bpy.data.objects["Cam_Top"]
    cam.location = (center[0], center[1], 2.0)
    cam.data.ortho_scale = max(size_m)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = transparent
    keep = set(visible or [])
    saved = {}
    for o in sc.objects:
        if o.type in {"MESH", "CURVE"}:
            saved[o.name] = o.hide_render
            o.hide_render = o.name not in keep
    sc.render.filepath = path
    try:
        bpy.ops.render.render(write_still=True)
    finally:
        for n, v in saved.items():
            bpy.data.objects[n].hide_render = v
    return path


def render_bread(bid, state):
    fw, fh = BREADS[bid]
    ob = bpy.data.objects["%s_%s" % (bid, state)]
    vis = [ob.name, "ShadowCatcher"]
    if bid == "tranca" and state == "baked":
        vis.append("tranca_baked_sugar")
    path = os.path.join(OUT, "pz_bread_%s_%s.png" % (bid, state))
    return shoot((ob.location.x, ob.location.y), (fw * CELL, fh * CELL), (fw * PX, fh * PX), path, True, vis)


# ============================================================================================ tray
TRAY_AT = Vector((0.0, -1.2, 0.0))


def tray_material():
    mat = bpy.data.materials.get("M_tray_steel") or bpy.data.materials.new("M_tray_steel")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    # blued / black steel with baked-on patina (amber-brown seasoning blotches), faint scratches
    n1 = nb.noise(tc, 6, 6, .6, .5)
    n2 = nb.noise(tc, 22, 8, .62)
    blot = nb.mapr(nb.add(n1, nb.mul(n2, .35)), .5, .78)
    steel = nb.ramp(n2, [(0, srgb("1C2129")), (.5, srgb("232A33")), (1, srgb("2B313A"))])
    patina = nb.ramp(n2, [(0, srgb("2E241C")), (1, srgb("3E2C1E"))])
    base = nb.mix(nb.mul(blot, .75), steel, patina)
    # scratches: stretched noise along x
    sv = nb.node("ShaderNodeMapping", Vector=tc, Scale=(18, 600, 1)).outputs[0]
    scr = nb.mapr(nb.noise(sv, 1.0, 2, .5), .68, .74)
    sv2 = nb.node("ShaderNodeMapping", Vector=tc, Scale=(500, 14, 1), Rotation=(0, 0, .5)).outputs[0]
    scr = nb.math("MAXIMUM", scr, nb.mapr(nb.noise(sv2, 1.0, 2, .5), .7, .75))
    scr = nb.mul(scr, nb.mapr(nb.noise(tc, 9, 2), .45, .7))
    base = nb.mix(nb.mul(scr, .35), base, srgb("4A525C"))
    # perforations: staggered grid of tiny holes (pitch 25 mm), all identical so the sheet can be stretched
    pitch = .025
    gx = nb.math("DIVIDE", x, pitch)
    row = nb.math("FLOOR", nb.math("DIVIDE", y, pitch))
    gx = nb.add(gx, nb.mul(nb.math("MODULO", row, 2.0), .5))
    fx = nb.math("SUBTRACT", nb.math("FRACT", gx), .5)
    fy = nb.math("SUBTRACT", nb.math("FRACT", nb.math("DIVIDE", y, pitch)), .5)
    dist = nb.math("SQRT", nb.add(nb.mul(fx, fx), nb.mul(fy, fy)))
    hole = nb.mapr(dist, .085, .065)
    rim = nb.mul(nb.mapr(dist, .065, .1), nb.mapr(dist, .14, .1))
    base = nb.mix(hole, base, srgb("07080A"))
    rough = nb.add(.42, nb.mul(blot, .2), nb.mul(n2, .1))
    bump_h = nb.add(nb.mul(n2, .3), nb.mul(hole, -1.0), nb.mul(rim, .4), nb.mul(scr, -.3))
    bump = nb.node("ShaderNodeBump", Height=bump_h, Strength=.25, Distance=.0006)
    nb.bsdf(**{"Base Color": base, "Metallic": .75, "Roughness": rough, "Normal": bump.outputs[0],
               "Coat Weight": .15, "Coat Roughness": .3})
    return mat


def build_tray():
    c = col("Tray")
    wipe_collection("Tray")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    bmesh.ops.scale(bm, vec=(.25 * 1.02, .2 * 1.02, 1), verts=bm.verts)
    ob = mesh_object("Tray_Sheet", bm, tray_material(), c, subsurf=0)
    ob.location = TRAY_AT
    # soft reflection source for the steel (big warm card above-left, out of frame)
    card = bpy.data.objects.get("Tray_Softbox")
    if not card:
        card = link(bpy.data.objects.new("Tray_Softbox", bpy.data.lights.new("Tray_Softbox", "AREA")), c)
    card.data.shape = "RECTANGLE"
    card.data.size, card.data.size_y = 1.2, 1.2
    card.data.energy = 60
    card.data.color = (1, .93, .84)
    card.location = TRAY_AT + Vector((-.35, .3, .9))
    card.rotation_euler = (math.radians(-18), math.radians(-20), 0)


def render_tray():
    return shoot((TRAY_AT.x, TRAY_AT.y), (.5, .4), (1000, 800), os.path.join(OUT, "pz_tray.png"), False, ["Tray_Sheet"])


# ============================================================================================ wood / cloth / props materials
def wood_material(name, light="D9A15C", dark="A8642E", plank=.11, along="X", seam=True, scale=1.0, paint=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    u, v = (x, y) if along == "X" else (y, x)
    idx = nb.math("FLOOR", nb.math("DIVIDE", v, plank))
    rnd = nb.node("ShaderNodeTexWhiteNoise", W=idx, _noise_dimensions="1D").outputs[0]
    # grain coordinates: stretched along the plank, offset per plank
    gvec = nb.node("ShaderNodeCombineXYZ", X=nb.add(nb.mul(u, 2.0 * scale), nb.mul(rnd, 13.0)),
                   Y=nb.mul(nb.add(v, nb.mul(rnd, .7)), 26.0 * scale), Z=nb.mul(rnd, 5.0)).outputs[0]
    warp = nb.noise(gvec, 1.4, 4, .55)
    grain = nb.node("ShaderNodeTexWave", Vector=nb.node("ShaderNodeCombineXYZ", X=nb.mul(u, .3 * scale), Y=nb.add(nb.mul(v, 9.0 * scale), nb.mul(warp, 1.6)), Z=0).outputs[0],
                    Scale=4.0, Distortion=1.5, Detail=3.0, **{"Detail Scale": 1.5}, _bands_direction="Y", _wave_profile="SIN").outputs["Factor"]
    fine = nb.noise(nb.node("ShaderNodeCombineXYZ", X=nb.mul(u, 30.0), Y=nb.mul(v, 900.0), Z=rnd).outputs[0], 1.0, 3, .6)
    t = nb.add(nb.mul(grain, .45), nb.mul(fine, .25), nb.mul(rnd, .35), nb.mul(warp, .2), -.2)
    base = nb.ramp(t, [(0, srgb(light)), (.55, srgb(light if len(light) == 6 else light)), (1, srgb(dark))]) if False else \
        nb.ramp(t, [(0, srgb(light)), (1, srgb(dark))])
    h = nb.add(nb.mul(grain, .3), nb.mul(fine, .5))
    if seam:
        fv = nb.math("FRACT", nb.math("DIVIDE", v, plank))
        s = nb.math("MINIMUM", fv, nb.math("SUBTRACT", 1.0, fv))
        sm = nb.mapr(s, .012, .0)
        base = nb.mix(nb.mul(sm, .8), base, srgb("5A3418"))
        h = nb.add(h, nb.mul(sm, -1.5))
    if paint:
        pn = nb.noise(tc, 7, 5, .6)
        wear = nb.mapr(nb.add(pn, nb.mul(fine, .2)), .72, .8)
        pc = nb.ramp(nb.noise(tc, 40, 3), [(0, srgb(paint[0])), (1, srgb(paint[1]))])
        base = nb.mix(nb.math("SUBTRACT", 1.0, nb.mul(wear, .8)), base, pc)
        base = nb.mix(nb.mul(nb.mul(grain, nb.math("SUBTRACT", 1.0, wear)), .07), base, srgb(paint[1]))
    bump = nb.node("ShaderNodeBump", Height=h, Strength=.18, Distance=.001)
    nb.bsdf(**{"Base Color": base, "Roughness": nb.add(.5, nb.mul(fine, .15)), "Normal": bump.outputs[0],
               "Specular IOR Level": .4, "Coat Weight": .08})
    return mat


def bench_top_material():
    """Warm butcher-block worktop with flour dust that stays near the edges (centre calm)."""
    mat = wood_material("M_bench_wood", light="E0A862", dark="A55F2C", plank=.115)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wood_col = bsdf.inputs["Base Color"].links[0].from_socket
    nb = NB.__new__(NB)
    nb.nt, nb.x = nt, 2000
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    x, y, z = nb.sep(tc)
    ex = nb.math("ABSOLUTE", nb.math("DIVIDE", x, .625))
    ey = nb.math("ABSOLUTE", nb.math("DIVIDE", y, .352))
    edge = nb.math("MAXIMUM", nb.mapr(ex, .6, .98), nb.mapr(ey, .5, 1.0))
    # extra flour drift around the sack (top-left) and under the rolling pin (bottom-right)
    def blob(cx, cy, r):
        d = nb.node("ShaderNodeVectorMath", Vector=tc, _operation="DISTANCE")
        d.inputs[1].default_value = (cx, cy, 0)
        return nb.mapr(d.outputs["Value"], r, r * .35)
    edge = nb.math("MAXIMUM", edge, blob(-.42, .25, .22))
    edge = nb.math("MAXIMUM", edge, nb.mul(blob(.48, -.28, .16), .8))
    n1 = nb.noise(tc, 9, 6, .62, .5)
    n2 = nb.noise(tc, 70, 5, .6)
    speck = nb.mapr(nb.noise(tc, 600, 2, .6), .45, .7)
    dust = nb.mul(nb.mapr(nb.add(n1, nb.mul(edge, .55), nb.mul(n2, .15)), .82, 1.0), edge)
    dust = nb.math("MAXIMUM", dust, nb.mul(nb.mul(speck, nb.mapr(n2, .55, .75)), nb.add(nb.mul(edge, .5), .12)))
    dust = nb.math("MINIMUM", dust, .92)
    nt.links.new(nb.mix(dust, wood_col, srgb("FAF5EA")), bsdf.inputs["Base Color"])
    rough_src = bsdf.inputs["Roughness"].links[0].from_socket
    nt.links.new(nb.add(rough_src, nb.mul(dust, .45)), bsdf.inputs["Roughness"])
    return mat


def simple_material(name, hexcol, rough=.5, metallic=0.0, coat=0.0, bump_scale=0.0, var=None, sss=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 60, 5, .6)
    base = nb.ramp(n, [(0, srgb(hexcol)), (1, srgb(var or hexcol))])
    kw = {"Base Color": base, "Roughness": rough, "Metallic": metallic, "Coat Weight": coat, "Coat Roughness": .1}
    if sss:
        kw.update({"Subsurface Weight": sss, "Subsurface Radius": (1, .8, .6), "Subsurface Scale": .01})
    if bump_scale:
        kw["Normal"] = nb.node("ShaderNodeBump", Height=nb.noise(tc, bump_scale, 6, .6), Strength=.15, Distance=.001).outputs[0]
    nb.bsdf(**kw)
    return mat


def egg_material():
    mat = bpy.data.materials.get("M_egg") or bpy.data.materials.new("M_egg")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    rnd = nb.node("ShaderNodeObjectInfo").outputs["Random"]
    shell = nb.ramp(rnd, [(0, srgb("E9B582")), (.5, srgb("D99A62")), (.85, srgb("F3E2C6")), (1, srgb("F6EAD6"))])
    sp = nb.mapr(nb.node("ShaderNodeTexVoronoi", Vector=tc, Scale=900, _feature="F1").outputs["Distance"], .12, .05)
    sp = nb.mul(sp, nb.mapr(nb.noise(tc, 300, 2), .5, .7))
    base = nb.mix(nb.mul(sp, .35), shell, srgb("8A5A36"))
    nb.bsdf(**{"Base Color": base, "Roughness": .45, "Subsurface Weight": .15, "Subsurface Radius": (1, .7, .5),
               "Subsurface Scale": .003,
               "Normal": nb.node("ShaderNodeBump", Height=nb.noise(tc, 900, 4), Strength=.08, Distance=.0005).outputs[0]})
    return mat


def burlap_material():
    mat = bpy.data.materials.get("M_burlap") or bpy.data.materials.new("M_burlap")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["UV"]
    x, y, z = nb.sep(tc)
    wx = nb.math("SINE", nb.mul(x, 2 * math.pi * 260))
    wy = nb.math("SINE", nb.mul(y, 2 * math.pi * 260))
    weave = nb.add(nb.mul(nb.math("ABSOLUTE", wx), .5), nb.mul(nb.math("ABSOLUTE", wy), .5))
    n = nb.noise(tc, 40, 5, .6)
    base = nb.ramp(nb.add(nb.mul(weave, .4), nb.mul(n, .6)), [(0, srgb("9C7442")), (.6, srgb("C59E62")), (1, srgb("D9B77A"))])
    nb.bsdf(**{"Base Color": base, "Roughness": .9,
               "Normal": nb.node("ShaderNodeBump", Height=weave, Strength=.45, Distance=.001).outputs[0]})
    return mat


def flour_material():
    mat = bpy.data.materials.get("M_flour") or bpy.data.materials.new("M_flour")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["Object"]
    n = nb.noise(tc, 300, 6, .65)
    nb.bsdf(**{"Base Color": nb.ramp(n, [(0, srgb("F4EEE2")), (1, srgb("FFFDF8"))]), "Roughness": .95,
               "Sheen Weight": .4, "Subsurface Weight": .2, "Subsurface Radius": (1, 1, 1), "Subsurface Scale": .003,
               "Normal": nb.node("ShaderNodeBump", Height=n, Strength=.3, Distance=.0008).outputs[0]})
    return mat


def towel_material():
    mat = bpy.data.materials.get("M_towel") or bpy.data.materials.new("M_towel")
    nb = NB(mat)
    tc = nb.node("ShaderNodeTexCoord").outputs["UV"]
    x, y, z = nb.sep(tc)
    # cream linen with two teal stripes near the hem
    st = nb.math("FRACT", nb.mul(y, 1.0))
    stripe = nb.math("MAXIMUM", nb.mul(nb.mapr(st, .12, .125), nb.mapr(st, .2, .195)),
                     nb.mul(nb.mapr(st, .24, .245), nb.mapr(st, .27, .265)))
    weave = nb.mul(nb.add(nb.math("ABSOLUTE", nb.math("SINE", nb.mul(x, 2 * math.pi * 180))),
                          nb.math("ABSOLUTE", nb.math("SINE", nb.mul(y, 2 * math.pi * 180)))), .5)
    base = nb.mix(stripe, nb.ramp(weave, [(0, srgb("EFE3C8")), (1, srgb("F9F1DF"))]), srgb("1F8F85"))
    nb.bsdf(**{"Base Color": base, "Roughness": .85, "Sheen Weight": .5,
               "Normal": nb.node("ShaderNodeBump", Height=weave, Strength=.3, Distance=.0008).outputs[0]})
    return mat


# ============================================================================================ props geometry
def lathe_bm(profile, seg=48):
    """profile [(r, z)] bottom->top, revolved around Z; closed with fans where r>0 at the ends."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-7:
            v = bm.verts.new((0, 0, z))
            rings.append([v] * seg)
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / seg), r * math.sin(2 * math.pi * j / seg), z)) for j in range(seg)])
    for i in range(len(rings) - 1):
        for j in range(seg):
            q = [rings[i][j], rings[i][(j + 1) % seg], rings[i + 1][(j + 1) % seg], rings[i + 1][j]]
            u = []
            for v in q:
                if v not in u:
                    u.append(v)
            if len(u) >= 3:
                try:
                    bm.faces.new(u)
                except ValueError:
                    pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def spline(pts, n=6):
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (Vector(P[j]) for j in (i - 1, i, i + 1, i + 2))
        for s in range(n):
            t = s / n
            out.append(tuple(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    out.append(tuple(pts[-1]))
    return out


def xform(bm, loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    if scale:
        bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    R = Matrix.Rotation(math.radians(rot[2]), 4, "Z") @ Matrix.Rotation(math.radians(rot[1]), 4, "Y") @ Matrix.Rotation(math.radians(rot[0]), 4, "X")
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(loc)) @ R, verts=bm.verts)
    return bm


def rounded_slab(w, h, t, r, seg=10):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, 0)) for x, y in pts]
    top = [bm.verts.new((x, y, t)) for x, y in pts]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    n = len(pts)
    for i in range(n):
        bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.calc_face_angle(0) > .7], offset=min(t * .4, .006), segments=4,
                    profile=.5, affect="EDGES", clamp_overlap=True)
    return bm


BENCH_AT = Vector((0.0, -2.4, 0.0))
BENCH_SIZE = (1.25, 1.25 * 9 / 16)


def build_bench():
    c = col("Bench")
    wipe_collection("Bench")
    W, H = BENCH_SIZE
    o = BENCH_AT
    # worktop
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    bmesh.ops.scale(bm, vec=(W * .52, H * .52, 1), verts=bm.verts)
    top = mesh_object("Bench_Top", bm, bench_top_material(), c, subsurf=0)
    top.location = o

    wood_pin = wood_material("M_pin_wood", light="F0C98E", dark="C99055", plank=10, seam=False, scale=3)
    # rolling pin, bottom-right, diagonal, its far end leaving the frame
    prof = [(0, -.21), (.009, -.21), (.0125, -.205), (.0135, -.19), (.0125, -.16), (.0135, -.15), (.018, -.148), (.03, -.145),
            (.031, -.13), (.031, .13), (.03, .145), (.018, .148), (.0135, .15), (.0125, .16), (.0135, .19), (.0125, .205), (.009, .21), (0, .21)]
    bm = lathe_bm(spline(prof, 3), 40)
    xform(bm, rot=(0, 90, 0))
    for v in bm.verts:
        v.co.z += .031
    xform(bm, loc=(.47, -.295, 0), rot=(0, 0, 24))
    mesh_object("Bench_RollingPin", bm, wood_pin, c, subsurf=1).location = o

    # wooden peel, bottom-left: blade in frame corner, handle leaving to the left
    peel_m = wood_material("M_peel_wood", light="E2B275", dark="B07A42", plank=10, seam=False, scale=2.0)
    bm = rounded_slab(.24, .26, .008, .05)
    bm2 = rounded_slab(.32, .034, .016, .014)
    xform(bm2, loc=(-.27, 0, 0))
    me = bpy.data.meshes.new("_t")
    bm2.to_mesh(me)
    bm2.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    xform(bm, loc=(-.5, -.315, 0), rot=(0, 0, 28))
    mesh_object("Bench_Peel", bm, peel_m, c, subsurf=1).location = o

    # burlap flour sack, top-left corner (mostly outside the frame), open with flour inside
    bm = cube_sphere(40)
    for v in bm.verts:
        x, y, z = v.co
        k = 1 + .06 * noise.noise(v.co * 3.0)
        v.co = Vector((x * .19 * k, y * .17 * k, max(z, -.2) * .09 + .018))
    me_uv_sack = bm
    sack = mesh_object("Bench_Sack", bm, burlap_material(), c, subsurf=1)
    sack.location = o + Vector((-.6, .33, 0))
    sm = sack.data
    sm.uv_layers.new(name="UVMap")
    for li, l in enumerate(sm.loops):
        co = sm.vertices[l.vertex_index].co
        sm.uv_layers[0].data[li].uv = (co.x * 2.0, co.y * 2.0)
    # rolled rim
    rim_pts = []
    for i in range(65):
        a = 2 * math.pi * i / 64
        rr = .125 * (1 + .05 * math.sin(3 * a) + .03 * math.sin(7 * a))
        rim_pts.append((rr * math.cos(a), rr * .9 * math.sin(a), .105 + .006 * math.sin(5 * a)))
    bm = bmesh.new()
    rings = []
    prev = None
    SEG = 16
    for i, p in enumerate(rim_pts[:-1]):
        p = Vector(p)
        tan = (Vector(rim_pts[(i + 1) % 64]) - Vector(rim_pts[(i - 1) % 64])).normalized()
        nrm = Vector((0, 0, 1))
        nrm = (nrm - tan * nrm.dot(tan)).normalized()
        bi = tan.cross(nrm)
        rr = .026 * (1 + .15 * noise.noise(p * 30))
        rings.append([bm.verts.new(p + (nrm * math.cos(2 * math.pi * j / SEG) + bi * math.sin(2 * math.pi * j / SEG)) * rr) for j in range(SEG)])
    for i in range(64):
        for j in range(SEG):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % SEG], rings[(i + 1) % 64][(j + 1) % SEG], rings[(i + 1) % 64][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    rim = mesh_object("Bench_SackRim", bm, burlap_material(), c, subsurf=1)
    rim.location = sack.location
    rm = rim.data
    rm.uv_layers.new(name="UVMap")
    for li, l in enumerate(rm.loops):
        co = rm.vertices[l.vertex_index].co
        rm.uv_layers[0].data[li].uv = (math.atan2(co.y, co.x) * .4, co.z * 3 + co.x)
    # flour mound inside + a small spill outside
    for name, (cx, cy), (rx, ry, hz), z0 in (("Bench_FlourIn", (0, 0), (.115, .1, .035), .09),
                                              ("Bench_FlourSpill", (.2, -.11), (.07, .05, .01), 0.0)):
        bm = cube_sphere(30)
        for v in bm.verts:
            x, y, z = v.co
            k = 1 + .15 * noise.fractal(v.co * 2.5 + Vector((cx * 9, 0, 0)), .6, 2, 3)
            v.co = Vector((x * rx * k, y * ry * k, max(z, 0) * hz * k + z0))
        f = mesh_object(name, bm, flour_material(), c, subsurf=1)
        f.location = sack.location + Vector((cx, cy, 0))

    # bowl of eggs on a striped towel, top-right corner
    bm = bmesh.new()
    nu, nv = 40, 30
    tw, th = .34, .26
    vs = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            x, y = (i / nu - .5) * tw, (j / nv - .5) * th
            z = .0025 + .004 * max(0, math.sin(i / nu * math.pi * 3 + j * .15)) + .002 * noise.noise(Vector((x * 20, y * 20, 0)))
            vs[i, j] = bm.verts.new((x, y, z))
    uvs = {}
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    towel = mesh_object("Bench_Towel", bm, towel_material(), c, subsurf=1)
    towel.location = o + Vector((.5, .27, 0))
    towel.rotation_euler.z = math.radians(-12)
    tm = towel.data
    tm.uv_layers.new(name="UVMap")
    for li, l in enumerate(tm.loops):
        co = tm.vertices[l.vertex_index].co
        tm.uv_layers[0].data[li].uv = (co.x / tw + .5, co.y / th + .5)
    bowl_prof = [(0, .008), (.05, .008), (.055, .004), (.065, .0), (.085, .012), (.098, .035), (.104, .058), (.106, .066),
                 (.1, .068), (.096, .06), (.09, .04), (.075, .02), (.05, .014), (0, .014)]
    bm = lathe_bm(spline(bowl_prof, 3), 64)
    bowl = mesh_object("Bench_Bowl", bm, simple_material("M_bowl", "1F8F85", .25, coat=.6, var="25A193"), c, subsurf=1)
    bowl.location = o + Vector((.52, .27, .006))
    # bowl inside glaze (cream) as a thin inner shell
    inner = [(0, .0145), (.05, .0145), (.075, .021), (.089, .04), (.0955, .06), (.0995, .0665)]
    bm = lathe_bm(spline(inner, 3), 64)
    bi_ = mesh_object("Bench_BowlInner", bm, simple_material("M_bowl_in", "F6EBD3", .2, coat=.5, var="EFE0C2"), c, subsurf=1)
    bi_.location = bowl.location + Vector((0, 0, .0005))
    egg_prof = [(0, 0)] + [(.0225 * math.sin(math.pi * t) * (1 - .12 * t), .058 * (1 - math.cos(math.pi * t)) / 2) for t in [i / 16 for i in range(1, 16)]] + [(0, .058)]
    rnd = random.Random(5)
    eggs = [(.0, .03, 70, 20), (-.035, -.02, 85, 120), (.035, -.025, 80, 210), (.0, -.005, 60, 300), (-.04, .025, 75, 40)]
    for k, (ex, ey, tilt, yaw) in enumerate(eggs):
        bm = lathe_bm(egg_prof, 32)
        xform(bm, loc=(0, 0, -.029))
        xform(bm, rot=(0, tilt, yaw))
        e = mesh_object("Bench_Egg%d" % k, bm, egg_material(), c, subsurf=1)
        e.location = bowl.location + Vector((ex, ey, .036 + (.012 if k == 3 else 0)))

    # small dish of sesame + a few scattered seeds, bottom edge centre
    dish_prof = [(0, .0), (.035, 0), (.05, .006), (.056, .022), (.054, .026), (.049, .012), (.035, .007), (0, .007)]
    bm = lathe_bm(spline(dish_prof, 3), 48)
    dish = mesh_object("Bench_Dish", bm, wood_material("M_dish_wood", light="C98A4E", dark="8E5428", plank=10, seam=False, scale=4), c, subsurf=1)
    dish.location = o + Vector((.06, -.33, 0))
    seed_m = simple_material("M_sesame", "F3E2BD", .55, var="E2C890", sss=.2)
    bm = bmesh.new()
    rnd = random.Random(11)

    def add_seed(x, y, z, yaw, s=1.0):
        t = bmesh.new()
        bmesh.ops.create_icosphere(t, subdivisions=2, radius=1)
        for v in t.verts:
            v.co = Vector((v.co.x * .0013 * (1 - .35 * max(0, v.co.y)), v.co.y * .0021, v.co.z * .0006)) * s
        xform(t, loc=(x, y, z + .0006), rot=(rnd.uniform(-10, 10), 0, yaw))
        me = bpy.data.meshes.new("_t")
        t.to_mesh(me)
        t.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    for i in range(260):
        a, r = rnd.uniform(0, 6.28), .046 * math.sqrt(rnd.random())
        add_seed(.06 + r * math.cos(a), -.33 + r * math.sin(a), .008 + .006 * (1 - (r / .046) ** 2) + rnd.uniform(0, .002), rnd.uniform(0, 360))
    for i in range(26):
        add_seed(rnd.uniform(-.1, .2), rnd.uniform(-.335, -.26), 0, rnd.uniform(0, 360))
    for i in range(16):
        add_seed(rnd.uniform(-.56, -.36), rnd.uniform(.12, .3), 0, rnd.uniform(0, 360))
    seeds = mesh_object("Bench_Seeds", bm, seed_m, c, subsurf=0)
    seeds.location = o


def render_bench():
    vis = [ob.name for ob in bpy.data.collections["Bench"].objects]
    return shoot((BENCH_AT.x, BENCH_AT.y), BENCH_SIZE, (1600, 900), os.path.join(OUT, "pz_bench_padaria.png"), False, vis)


# ============================================================================================ cream board (mockup only)
BOARD_AT = Vector((1.2, -1.2, 0.0))
BOARD_SIZE = (.56, .46)


def build_board():
    c = col("Board")
    wipe_collection("Board")
    m = wood_material("M_board_cream", light="D8A869", dark="B07A42", plank=.09, seam=True, scale=1.5,
                      paint=("F7EBCB", "EFDDB0"))
    bm = rounded_slab(BOARD_SIZE[0] - .04, BOARD_SIZE[1] - .04, .022, .03)
    ob = mesh_object("Board_Cream", bm, m, c, subsurf=1)
    ob.location = BOARD_AT


def render_board():
    return shoot((BOARD_AT.x, BOARD_AT.y), BOARD_SIZE, (int(BOARD_SIZE[0] * 2000), int(BOARD_SIZE[1] * 2000)),
                 os.path.join(OUT, "mockup_part_board.png"), True, ["Board_Cream", "ShadowCatcher"])


# ============================================================================================ 2D compositing (numpy)
def img_load(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1].copy()


def img_save(a, path):
    h, w = a.shape[:2]
    im = bpy.data.images.new("_out", w, h, alpha=True)
    im.pixels.foreach_set(np.clip(a[::-1], 0, 1).astype(np.float32).ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def img_resize(a, w, h):
    """Area-ish downscale through Blender (premultiplied to keep clean edges)."""
    pm = a.copy()
    pm[..., :3] *= pm[..., 3:4]
    im = bpy.data.images.new("_rs", a.shape[1], a.shape[0], alpha=True, float_buffer=True)
    im.pixels.foreach_set(pm[::-1].ravel())
    im.scale(w, h)
    out = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(out)
    bpy.data.images.remove(im)
    out = out.reshape(h, w, 4)[::-1].copy()
    al = np.clip(out[..., 3:4], 1e-6, 1)
    out[..., :3] = np.where(out[..., 3:4] > 1e-5, out[..., :3] / al, 0)
    return out


def over(dst, src, x, y):
    h, w = src.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    d = dst[y0:y1, x0:x1]
    a = s[..., 3:4]
    d[..., :3] = s[..., :3] * a + d[..., :3] * (1 - a)
    d[..., 3:4] = a + d[..., 3:4] * (1 - a)


def blur(m, r):
    for axis in (0, 1):
        for _ in range(3):
            c = np.cumsum(np.pad(m, [(r + 1, r) if i == axis else (0, 0) for i in range(m.ndim)], mode="edge"), axis=axis)
            m = (np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis) - np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)) / (2 * r + 1)
    return m


def shadow(dst, mask, x, y, r=14, dx=8, dy=10, strength=.45):
    """Soft drop shadow of a mask (h, w) placed at x, y on an opaque dst."""
    h, w = mask.shape
    pad = r * 3
    m = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
    m[pad:pad + h, pad:pad + w] = mask
    m = blur(m, r) * strength
    sh = np.zeros(m.shape + (4,), np.float32)
    sh[..., 0], sh[..., 1], sh[..., 2] = .16, .09, .04
    sh[..., 3] = m
    over(dst, sh, x - pad + dx, y - pad + dy)


def rounded_mask(w, h, r):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) + .5
    cx = np.clip(xx, r, w - r)
    cy = np.clip(yy, r, h - r)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return np.clip(r - d + .5, 0, 1)


def mockup(state="raw"):
    bench = img_load(os.path.join(OUT, "pz_bench_padaria.png"))
    bench[..., 3] = 1
    cpx = 128                       # cell size in the mockup
    cols, rows = 5, 4
    tw, th = cols * cpx, rows * cpx
    tx, ty = 400 - tw // 2, 450 - th // 2
    rim = 16
    # tray rim (dark steel lip) + shadow
    fm = rounded_mask(tw + 2 * rim, th + 2 * rim, 22)
    shadow(bench, fm, tx - rim, ty - rim, r=12, dx=10, dy=14, strength=.55)
    yy = np.linspace(0, 1, th + 2 * rim)[:, None]
    xx = np.linspace(0, 1, tw + 2 * rim)[None, :]
    g = .30 - .12 * (xx * .5 + yy * .5)
    frame = np.zeros((th + 2 * rim, tw + 2 * rim, 4), np.float32)
    frame[..., 0], frame[..., 1], frame[..., 2] = g * .95, g, g * 1.08
    inner = np.zeros_like(fm)
    inner[rim - 2:rim + th + 2, rim - 2:rim + tw + 2] = 1
    hl = np.clip(fm - blur(fm, 2), 0, 1) * 2.5          # light catch on the outer edge
    frame[..., :3] += hl[..., None] * np.array([.35, .33, .3])
    frame[..., 3] = fm
    over(bench, frame, tx - rim, ty - rim)
    tray = img_resize(img_load(os.path.join(OUT, "pz_tray.png")), tw, th)
    tray[..., 3] = 1
    # inner shading: the lip casts a soft shade on the sheet
    sh_in = 1 - blur(np.pad(np.ones((th, tw), np.float32), 1, constant_values=0), 6)[1:-1, 1:-1]
    tray[..., :3] *= (1 - .45 * sh_in)[..., None]
    over(bench, tray, tx, ty)
    # grid lines (mockup only)
    grid = np.zeros((th, tw, 4), np.float32)
    grid[..., :3] = 1
    for i in range(1, cols):
        grid[:, i * cpx - 1:i * cpx + 1, 3] = .2
    for j in range(1, rows):
        grid[j * cpx - 1:j * cpx + 1, :, 3] = .2
    over(bench, grid, tx, ty)

    def piece(bid, st, c, r, rot=False):
        sp = img_load(os.path.join(OUT, "pz_bread_%s_%s.png" % (bid, st)))
        if rot:
            sp = np.rot90(sp, -1).copy()
        h, w = sp.shape[:2]
        sp = img_resize(sp, int(w * cpx / PX), int(h * cpx / PX))
        return sp

    if state == "raw":
        placed = [("redondo", 0, 0, False), ("baguete", 2, 0, False), ("tranca", 4, 0, False), ("frances", 2, 3, False)]
        board = [("baguete", 0.0, 0.0, False), ("forma", 1.25, 0.0, False), ("forma", 2.5, 0.0, False), ("frances", 1.25, 2.3, False)]
    else:
        placed = [("redondo", 0, 0, False), ("forma", 0, 2, True), ("forma", 0, 3, True), ("baguete", 2, 0, False),
                  ("baguete", 3, 0, False), ("frances", 2, 3, False), ("frances", 3, 3, False), ("tranca", 4, 0, False)]
        board = []
    for bid, c, r, rot in placed:
        over(bench, piece(bid, state, c, r, rot), tx + c * cpx, ty + r * cpx)
    bimg = img_load(os.path.join(OUT, "mockup_part_board.png"))
    bh, bw = bimg.shape[:2]
    bimg = img_resize(bimg, int(bw * cpx / PX), int(bh * cpx / PX))
    bx, by = 1200 - bimg.shape[1] // 2, 450 - bimg.shape[0] // 2
    over(bench, bimg, bx, by)
    ox, oy = bx + int(.55 * cpx), by + int(.42 * cpx)
    for bid, c, r, rot in board:
        over(bench, piece(bid, state, c, r, rot), ox + int(c * cpx), oy + int(r * cpx))
    bench[..., 3] = 1
    name = "mockup_padaria.png" if state == "raw" else "mockup_padaria_baked.png"
    img_save(bench, os.path.join(OUT, name))
    return os.path.join(OUT, name)


# ============================================================================================ entry points
def build():
    setup_scene()
    build_breads()
    build_tray()
    build_bench()
    build_board()


def render_all_breads():
    paths = []
    for state in ("raw", "baked"):
        for bid in BREADS:
            paths.append(render_bread(bid, state))
    return paths


def save():
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


def run():
    build()
    out = render_all_breads()
    out.append(render_tray())
    out.append(render_bench())
    out.append(render_board())
    out.append(mockup("raw"))
    out.append(mockup("baked"))
    save()
    return out
