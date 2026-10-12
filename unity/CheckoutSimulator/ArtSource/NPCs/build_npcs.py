"""Rig the new NPC sculpts (ArtSource/NPCs/lite/*.blend, made by npc_lite.py) on the game's skeletons.

Run (background, one sculpt per call):
    blender -b --factory-startup --python ArtSource/NPCs/build_npcs.py -- <sculpt> [preview|export]

Skeletons (every character shares the 14-bone layout: Torso, Head, Thigh/Shin/Foot, UpperArm/Forearm/Hand; the bones
point straight up and the L/R names are mirrored, so sides are taken from positions, s = +1 for +X):
  * construction crew (worker1 = woman, worker2 = man) and the motoboy: the Worker_Delivery rig. Their clips are
    authored here with IK (feet planted, hands on targets): Idle, Walking, CarryIdle, CarryWalking, Pickup, PutDown,
    and the tool work Hammer (one hand, the character's right) and Sledge (both hands on the handle).
  * customers (elderly_man, cartoon_character, cartoon_girl): the rig and clips of Assets/Art/Characters/<rig>.fbx,
    plus the free Walking / WalkingWithBasket pair of ArtSource/Customers/build_customers.py.

Skin weights (the "risco embaixo do braço" fix, Lucas 12/10): the old builders wrote height/width bands, so the
side of the chest under the arm followed the upper arm and tore into a streak when the arm went up. Here each arm
is the arm's own piece of mesh below the armpit (the chest stays on the torso), the shoulder cap blends into it,
and the transitions at the armpits and hips are smoothed so the stretch spreads instead of making a line
(see skin_weights).

The sculpts stand in a wide A pose; the clips bring the arms down (IK for the crew, a constant shoulder adduction
on top of the customers' clips) so the characters do not walk around with their arms out.
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
CHARS = os.path.join(PROJECT, "Assets", "Art", "Characters")
LITE = os.path.join(HERE, "lite")
PREVIEWS = os.path.join(PROJECT, "Temp", "qa", "npcs")

TARGETS = {
    # The crew is loaded at runtime (CheckoutCrew): Resources/CheckoutCrew.
    "worker1": dict(kind="crew", out="Worker_ConstructionF", rig="Worker_Delivery", folder="../../Resources/CheckoutCrew"),
    "worker2": dict(kind="crew", out="Worker_ConstructionM", rig="Worker_Delivery", folder="../../Resources/CheckoutCrew"),
    # The motoboy only rides the bike: build_motoboy_ride.py poses and exports him (nothing exported from here).
    "motoboy": dict(kind="crew", out="Worker_Motoboy", rig="Worker_Delivery", folder=None),
    "cartoon_character": dict(kind="customer", out="Customer_02", look="Customer_Plaid", rig="Customer_02", folder="Meshy"),
    "elderly_man": dict(kind="customer", out="Customer_03", look="Customer_Elder", rig="Customer_03", folder="Meshy"),
    "cartoon_girl": dict(kind="customer", out="Customer_04", look="Customer_Jacket", rig="Customer_04", folder="Meshy"),
}
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
TAU = 2 * math.pi
FPS = 30


def V(x, y, z):
    return Vector((x, y, z))


def ss(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))) if b != a else 0.0
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return a + (b - a) * t


# ================================================================================================= sculpt
def load_lite(name):
    path = os.path.join(LITE, name + ".blend")
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    mesh = None
    for o in dst.objects:
        if o is not None and o.type == 'MESH':
            bpy.context.collection.objects.link(o); mesh = o
            o.rotation_mode = 'XYZ'; o.matrix_world = Matrix()      # npc_lite saved it where its preview stood
    return mesh


def samples(mesh, count=160000):
    """Points spread over the surface (area weighted): a decimated mesh has too few vertices to slice."""
    me = mesh.data; me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices])
    tri = np.array([t.vertices[:] for t in me.loop_triangles])
    a, b, c = co[tri[:, 0]], co[tri[:, 1]], co[tri[:, 2]]
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) * .5
    rng = np.random.default_rng(7)
    pick = rng.choice(len(tri), size=count, p=area / area.sum())
    u, v = rng.random(count), rng.random(count)
    flip = u + v > 1; u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    return a[pick] + (b[pick] - a[pick]) * u[:, None] + (c[pick] - a[pick]) * v[:, None]


def clusters(pts, gap=.035):
    if len(pts) == 0:
        return []
    order = np.argsort(pts[:, 0]); p = pts[order]
    cut = np.where(np.diff(p[:, 0]) > gap)[0]
    return np.split(p, cut + 1)


def measure(mesh):
    """Joint positions of the sculpt (character space: faces -Y, +Z up, feet on z=0, 2.4 tall)."""
    P = samples(mesh)
    band = lambda z, h=.012: P[np.abs(P[:, 2] - z) < h]
    # Crotch: the first height where the gap between the legs closes.
    crotch = None
    for z in np.arange(.35, 1.3, .01):
        if all(np.sum(np.abs(band(z + k * .01)[:, 0]) < .018) > 2 for k in range(3)):
            crotch = float(z); break
    # Arms: the outer clusters, apart from the body, from the fingertips up to the armpit.
    arm = {1: {}, -1: {}}
    for z in np.arange(.4, 1.9, .01):
        for c in clusters(band(z)):
            cx = float(np.mean(c[:, 0]))
            if abs(cx) > .36 and np.min(np.abs(c[:, 0])) > .30:
                s = 1 if cx > 0 else -1
                arm[s][round(float(z), 2)] = (cx, float(np.mean(c[:, 1])))
    both = sorted(set(arm[1]) & set(arm[-1]))
    tip = both[0]
    run = [tip]
    for z in both[1:]:
        if z - run[-1] <= .035:
            run.append(z)
        else:
            break
    armpit = run[-1]

    def arm_at(s, z):
        ks = [k for k in arm[s] if k <= armpit + 1e-6]
        k = min(ks, key=lambda k: abs(k - z))
        return arm[s][k]

    # Neck: the narrowest body section between the shoulders and the head.
    def width(z):
        cs = [c for c in clusters(band(z), .05) if np.min(c[:, 0]) < 0 < np.max(c[:, 0])]
        return (float(np.max(np.abs(cs[0][:, 0]))) if cs else 0.0), (float(np.mean(cs[0][:, 1])) if cs else 0.0)
    necks = [(width(z)[0], z) for z in np.arange(1.55, 2.05, .01)]
    neck = float(min(necks)[1])
    head_top = float(np.max(P[:, 2]))
    L = {"crotch": crotch, "armpit": armpit, "tip": tip, "neck": neck, "top": head_top}
    hip_z = crotch + .05
    L["torso"] = V(0, width(hip_z)[1], hip_z)
    L["head"] = V(0, width(neck)[1], neck)
    for s in (1, -1):
        # Legs: the cluster centre on this side.
        def leg(z):
            pts = band(z); pts = pts[(pts[:, 0] * s > .02) & (np.abs(pts[:, 0]) < .40)]
            return V(float(np.mean(pts[:, 0])), float(np.mean(pts[:, 1])), z)
        thigh = leg(crotch - .08)
        L["hip", s] = V(thigh.x, L["torso"].y, hip_z)
        L["ankle", s] = leg(.14)
        kz = (hip_z + .14) / 2 + .02
        L["knee", s] = leg(kz)
        # Arms: wrist above the hand, shoulder on the line of the arm, elbow half way.
        wz = tip + .14
        wx, wy = arm_at(s, wz)
        L["wrist", s] = V(wx, wy, wz)
        tx, ty = arm_at(s, tip + .02)
        L["tip", s] = V(tx, ty, tip)
        zs = [z for z in arm[s] if wz + .04 <= z <= armpit]
        xs = [arm[s][z][0] for z in zs]
        slope, icpt = np.polyfit(zs, xs, 1) if len(zs) > 3 else (0.0, wx)
        sz = neck - .20
        half = width(sz - .04)[0]
        sx = float(slope * sz + icpt) - s * .05
        sx = s * min(max(abs(sx), .20), half - .05)
        L["shoulder", s] = V(sx, width(sz)[1], sz)
        ez = (sz + wz) / 2
        ex = float(slope * ez + icpt) if ez <= armpit else mix(sx, float(slope * armpit + icpt), (sz - ez) / max(1e-3, sz - armpit))
        ey = arm_at(s, min(ez, armpit))[1]
        L["elbow", s] = V(ex, ey, ez)
    L["half_hip"] = width(L["wrist", 1].z)[0]
    return L


# ================================================================================================= weights
BONES = ["Torso", "Head"] + [p + "_" + q for q in ("L", "R") for p in ("Thigh", "Shin", "Foot", "UpperArm", "Forearm", "Hand")]


def side_name(part, s, rig_side):
    """Bone name of `part` on the side s (+1 = +X), following the rig's own (mirrored) naming."""
    return part + "_" + rig_side[s]


def skin_weights(mesh, L, rig_side):
    """Weights from the sculpt's own anatomy (no bone heat: it smeared the arms over the legs on these meshes).

    * Below the armpit the arms hang apart from the body, so each arm is its own piece of mesh there: those
      vertices belong to the arm, and the side of the chest under it does not (the streak under the arm came from
      chest vertices that followed the upper arm). Above the armpit, the shoulder cap blends into the arm.
    * Along an arm: upper arm / forearm / hand by the position along shoulder -> elbow -> wrist -> fingertips.
    * Legs: each side below the crotch, thigh / shin / foot by height; the hips blend into the torso.
    * Head above the neck.
    A few smoothing passes around the armpit and the hips spread the stretch so no seam line shows."""
    me = mesh.data
    co = np.array([v.co[:] for v in me.vertices]); n = len(co)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    S = lambda a, b, t: np.clip((t - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((t - a) / (b - a), 0, 1))
    nb = [[] for _ in range(n)]
    for e in me.edges:
        a, b = e.vertices; nb[a].append(b); nb[b].append(a)
    armpit, crotch, neck = L["armpit"], L["crotch"], L["neck"]["z"] if isinstance(L["neck"], dict) else L["neck"]
    # Arm pieces: connected components of the mesh below the armpit, away from the body centre.
    low = z < armpit - .015
    comp = -np.ones(n, dtype=int); arm_piece = np.zeros(n, dtype=bool)
    k = 0
    for start in range(n):
        if not low[start] or comp[start] >= 0:
            continue
        stack = [start]; comp[start] = k; members = []
        while stack:
            v = stack.pop(); members.append(v)
            for w in nb[v]:
                if low[w] and comp[w] < 0:
                    comp[w] = k; stack.append(w)
        members = np.array(members)
        cx = float(np.mean(x[members]))
        if abs(cx) > .30 and np.min(np.abs(x[members])) > .18 and np.max(z[members]) > L["wrist", 1].z - .05:
            arm_piece[members] = True
        k += 1
    W = {name: np.zeros(n) for name in BONES}
    head = S(neck - .04, neck + .06, z)
    for s in (1, -1):
        on = (x * s) > 0
        sh, el, wr, tp = L["shoulder", s], L["elbow", s], L["wrist", s], L["tip", s]
        # How much of the arm: the arm piece, plus the shoulder cap above the armpit.
        cap = S(abs(sh.x) - .07, abs(sh.x) + .05, x * s) * (1 - S(sh.z + .02, sh.z + .16, z)) * (z >= armpit - .015)
        arm = np.where(arm_piece & on, 1.0, cap * on)
        # Position along shoulder -> elbow -> wrist -> tip.
        pts = [np.array(p[:]) for p in (sh, el, wr, tp)]
        best = np.full(n, 1e9); along = np.zeros(n); start_len = 0.0
        for a, b in zip(pts[:-1], pts[1:]):
            d = b - a; l = float(np.linalg.norm(d)); u = np.clip(((co - a) @ d) / (l * l), 0, 1)
            dist = np.linalg.norm(co - (a + u[:, None] * d), axis=1)
            take = dist < best; best[take] = dist[take]; along[take] = start_len + u[take] * l
            start_len += l
        le = float(np.linalg.norm(pts[1] - pts[0])); lw = le + float(np.linalg.norm(pts[2] - pts[1]))
        fore = S(le - .05, le + .05, along); hand = S(lw - .03, lw + .03, along)
        W[side_name("UpperArm", s, rig_side)] += arm * (1 - fore)
        W[side_name("Forearm", s, rig_side)] += arm * fore * (1 - hand)
        W[side_name("Hand", s, rig_side)] += arm * hand
        # Legs.
        hp, kn, an = L["hip", s], L["knee", s], L["ankle", s]
        side_w = S(-.05, .05, x * s)
        leg = (1 - S(crotch - .05, crotch + .08, z)) * side_w * (1 - arm)
        shin = 1 - S(kn.z - .05, kn.z + .05, z); foot = 1 - S(an.z - .02, an.z + .06, z)
        W[side_name("Thigh", s, rig_side)] += leg * (1 - shin)
        W[side_name("Shin", s, rig_side)] += leg * shin * (1 - foot)
        W[side_name("Foot", s, rig_side)] += leg * foot
    arms_total = sum(W[k_] for k_ in W if k_.startswith(("UpperArm", "Forearm", "Hand")))
    legs_total = sum(W[k_] for k_ in W if k_.startswith(("Thigh", "Shin", "Foot")))
    W["Head"] = head * (1 - arms_total)
    W["Torso"] = np.clip(1 - arms_total - legs_total - W["Head"], 0, 1)
    # Spread the transitions at the armpits and the hips (only there: the rest keeps its clean regions).
    soft = ((np.abs(z - armpit) < .12) & (np.abs(x) > .15)) | (np.abs(z - crotch) < .08)
    idx = np.where(soft)[0]
    for _ in range(6):
        for name in W:
            w = W[name]; new = w.copy()
            for v in idx:
                if nb[v]:
                    new[v] = .5 * w[v] + .5 * float(np.mean(w[nb[v]]))
            W[name] = new
    total = sum(W.values()); total[total < 1e-6] = 1
    for name in W:
        W[name] = W[name] / total
    # Keep the 4 strongest bones per vertex.
    names = list(W); M = np.stack([W[k_] for k_ in names], axis=1)
    order = np.argsort(-M, axis=1)
    for v in range(n):
        keep = order[v, :4]; vals = M[v, keep]; t = vals.sum() or 1
        for kk, val in zip(keep, vals):
            if val > .001:
                g = mesh.vertex_groups.get(names[kk]) or mesh.vertex_groups.new(name=names[kk])
                g.add([v], float(val / t), 'REPLACE')
    for name in names:
        if not mesh.vertex_groups.get(name):
            mesh.vertex_groups.new(name=name)
    return int(np.sum(arm_piece))


# ================================================================================================= rig
def import_rig(rig_name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CHARS, rig_name + ".fbx"))
    new = set(bpy.data.objects) - before
    rig = next(o for o in new if o.type == 'ARMATURE')
    others = [o for o in new if o is not rig]
    return rig, others


def fit_rig(rig, L):
    """Moves every joint onto the sculpt (bones keep their upright rest orientation, so the clips stay valid)."""
    B = rig.data.bones
    side = {1: None, -1: None}
    for b in B:
        if b.name.startswith("UpperArm"):
            side[1 if b.head_local.x > 0 else -1] = b.name.split("_")[1]
    centers = {"Torso": L["torso"], "Head": L["head"]}
    for s in (1, -1):
        for part, key in (("Thigh", "hip"), ("Shin", "knee"), ("Foot", "ankle"), ("UpperArm", "shoulder"), ("Forearm", "elbow"), ("Hand", "wrist")):
            centers[part + "_" + side[s]] = L[key, s]
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for e in rig.data.edit_bones:
        if e.name in centers:
            d = Vector(centers[e.name]) - e.head; e.head += d; e.tail += d
    bpy.ops.object.mode_set(mode='OBJECT')
    return side


def bind(mesh, rig, name):
    body = mesh
    body.name = name + "_Body"
    body.parent = rig
    m = body.modifiers.new("Skeleton", 'ARMATURE'); m.object = rig
    return body


# ================================================================================================= poses (IK)
class Rig:
    def __init__(self, arm):
        B = arm.data.bones
        side = lambda n: 1 if B[n].head_local.x > 0 else -1
        self.ua = {side(b.name): b.name for b in B if b.name.startswith("UpperArm")}
        self.fa = {s: n.replace("UpperArm", "Forearm") for s, n in self.ua.items()}
        self.hd = {s: n.replace("UpperArm", "Hand") for s, n in self.ua.items()}
        self.th = {s: n.replace("UpperArm", "Thigh") for s, n in self.ua.items()}
        self.sh = {s: n.replace("UpperArm", "Shin") for s, n in self.ua.items()}
        self.ft = {s: n.replace("UpperArm", "Foot") for s, n in self.ua.items()}
        h = lambda n: B[n].head_local.copy()
        self.pivot = h("Torso")
        self.shoulder = {s: h(self.ua[s]) for s in (1, -1)}
        self.elbow = {s: h(self.fa[s]) for s in (1, -1)}
        self.wrist = {s: h(self.hd[s]) for s in (1, -1)}
        self.hip = {s: h(self.th[s]) for s in (1, -1)}
        self.knee = {s: h(self.sh[s]) for s in (1, -1)}
        self.ankle = {s: h(self.ft[s]) for s in (1, -1)}
        self.l_ua = (self.elbow[1] - self.shoulder[1]).length
        self.l_fa = (self.wrist[1] - self.elbow[1]).length
        self.l_th = (self.knee[1] - self.hip[1]).length
        self.l_sh = (self.ankle[1] - self.knee[1]).length
        self.reach = self.l_ua + self.l_fa
        self.set_hang(abs(self.wrist[1].x) - .1)

    def set_hang(self, hip_half):
        """Hands hanging next to the hips (the sculpt's A pose brought down), clear of the hips."""
        self.hang = {s: V(s * max(abs(self.shoulder[s].x) + .08, hip_half + .085), self.wrist[s].y - .03, 0) for s in (1, -1)}
        for s in (1, -1):
            dx = abs(self.hang[s].x - self.shoulder[s].x); dy = self.hang[s].y - self.shoulder[s].y
            self.hang[s].z = self.shoulder[s].z - math.sqrt(max(.01, (self.reach * .97) ** 2 - dx * dx - dy * dy))


def two_bone(a, target, l1, l2, pole):
    d = target - a; dist = max(1e-4, min(d.length, l1 + l2 - 1e-4)); u = d.normalized()
    x = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist); hgt = math.sqrt(max(0.0, l1 * l1 - x * x))
    v = pole - u * pole.dot(u)
    v = v.normalized() if v.length > 1e-5 else Vector((0, 0, -1))
    return a + u * x + v * hgt, a + u * dist


def _rot(lean, turn, tilt):
    return Quaternion(Z, math.radians(turn)) @ Quaternion(Y, math.radians(tilt)) @ Quaternion(X, math.radians(lean))


class Pose:
    """Torso angles (lean > 0 bends forward), hands on targets, feet on targets (offsets from the rest ankle)."""
    def __init__(self, r):
        self.r = r; self.lean = self.turn = self.tilt = self.lift = 0.0; self.nod = 0.0
        self.arms = {}; self.legs = {}; self.wrist_bend = {}

    def torso(self, lean=0.0, turn=0.0, tilt=0.0, lift=0.0):
        self.lean, self.turn, self.tilt, self.lift = lean, turn, tilt, lift; return self

    def head(self, nod=0.0):
        self.nod = nod; return self

    def hand(self, s, p, pole=None, world=False, bend=0.0):
        """Wrist of arm s at p (character space). world=False: p moves with the torso (a pose of the arm);
        world=True: p is fixed in space (an object the hand holds)."""
        self.arms[s] = (p, pole or V(s * .6, .5, -1.0), world); self.wrist_bend[s] = bend; return self

    def foot(self, s, dy=0.0, dz=0.0, dx=0.0):
        self.legs[s] = V(s * dx, -dy, dz); return self


def solve(p):
    r = p.r; A = {}
    T = _rot(p.lean, p.turn, p.tilt); A["Torso"] = T
    piv = r.pivot + V(0, 0, p.lift)
    carry = lambda pt: piv + T @ (pt - r.pivot)
    A["Head"] = T @ Quaternion(X, math.radians(p.nod))
    swing = lambda parent, rest_dir, want: (parent @ rest_dir).rotation_difference(want) @ parent
    for s in (1, -1):
        sh = carry(r.shoulder[s])
        target, pole, world = p.arms.get(s, (r.hang[s], V(s * .6, .5, -1.0), False))
        target = target if world else carry(target)
        elbow, wrist = two_bone(sh, target, r.l_ua, r.l_fa, T @ pole)
        A[r.ua[s]] = swing(T, r.elbow[s] - r.shoulder[s], elbow - sh)
        A[r.fa[s]] = swing(A[r.ua[s]], r.wrist[s] - r.elbow[s], wrist - elbow)
        bend = p.wrist_bend.get(s, 0.0)
        A[r.hd[s]] = (Quaternion(A[r.fa[s]] @ X, math.radians(bend)) @ A[r.fa[s]]) if bend else A[r.fa[s]]
        hip = carry(r.hip[s])
        ankle = r.ankle[s] + p.legs.get(s, V(0, 0, 0))
        knee, ank = two_bone(hip, ankle, r.l_th, r.l_sh, T @ V(0, -1, .1))
        A[r.th[s]] = swing(T, r.knee[s] - r.hip[s], knee - hip)
        A[r.sh[s]] = swing(A[r.th[s]], r.ankle[s] - r.knee[s], ank - knee)
        A[r.ft[s]] = Quaternion()
    return A


def put(arm, frame, p, last):
    A = solve(p)
    for pb in arm.pose.bones:
        n = pb.name
        if n not in A:
            continue
        par = pb.parent.name if pb.parent else None
        rel = (A[par].inverted() @ A[n]) if par in A else A[n]
        rest = pb.bone.matrix_local.to_quaternion()
        q = rest.inverted() @ rel @ rest
        if n in last and last[n].dot(q) < 0:
            q.negate()
        last[n] = q.copy()
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        if n == "Torso":
            # Bone-local Y is up (the bones point up): the lift is a local Y move.
            pb.location = (0, p.lift, 0)
            pb.keyframe_insert("location", frame=frame)


# ------------------------------------------------------------------------------------------------- crew clips
def walk_pose(r, t, carry=False, stride=None):
    stride = stride or .13 * (r.l_th + r.l_sh) / .62
    p = Pose(r)
    ph = TAU * t
    p.torso(lean=4 if not carry else 2, turn=3 * math.sin(ph), lift=-.008 + .006 * math.cos(2 * ph))
    for s in (1, -1):
        u = (t + (0 if s == 1 else .5)) % 1
        if u < .5:
            dy, dz = stride * (1 - 4 * u), 0.0
        else:
            v = (u - .5) / .5
            dy, dz = -stride + 2 * stride * ss(0, 1, v), .09 * math.sin(math.pi * v)
        p.foot(s, dy=dy, dz=dz)
        if carry:
            p.hand(s, V(s * .23, -.42, r.pivot.z + .28), pole=V(s * 1, .5, -1), bend=-20)
        else:
            sw = .16 * math.cos(TAU * u + math.pi)
            h = r.hang[s]
            p.hand(s, V(h.x, h.y - sw, h.z + .03 + .03 * abs(sw) / .16))
    return p


def idle_pose(r, t, carry=False):
    p = Pose(r).torso(lift=.006 * math.sin(TAU * t)).head(nod=2 * math.sin(TAU * t))
    for s in (1, -1):
        if carry:
            p.hand(s, V(s * .23, -.42, r.pivot.z + .28 + .008 * math.sin(TAU * t)), pole=V(s * 1, .5, -1), bend=-20)
        else:
            h = r.hang[s]; p.hand(s, V(h.x, h.y - .03, h.z + .01 * math.sin(TAU * t)))
    return p


def squat_pose(r, c, hands):
    """c: 0 standing .. 1 crouched at the floor; hands: dict s -> (point, world)."""
    p = Pose(r).torso(lean=38 * c, lift=-c * .42 * (r.pivot.z - r.ankle[1].z)).head(nod=-10 * c)
    for s in (1, -1):
        p.foot(s, dy=.06 * c * s, dz=0)
        pt, world = hands[s]
        p.hand(s, pt, pole=V(s * 1, .3, -1), world=world, bend=-15 * c)
    return p


def box_floor(r, s):
    return V(s * .24, -.62, .30)


def box_carry(r, s):
    return V(s * .23, -.42, r.pivot.z + .28)


def world_of(r, pt, lean=0.0, lift=0.0):
    """A torso-carried point (pose of the arm) as a fixed point, for the given torso lean/lift."""
    return r.pivot + V(0, 0, lift) + _rot(lean, 0, 0) @ (pt - r.pivot)


def pickup_pose(r, t):
    """Crouch, take the box from the floor, stand up holding it (the box appears at 55%)."""
    c = ss(0, .45, t) if t < .45 else 1 - ss(.45, .95, t)
    hands = {}
    for s in (1, -1):
        if t < .45:
            hands[s] = (world_of(r, r.hang[s]).lerp(box_floor(r, s), ss(0, .45, t)), True)
        else:
            hands[s] = (box_floor(r, s).lerp(world_of(r, box_carry(r, s)), ss(.45, .95, t)), True)
    return squat_pose(r, c, hands)


def putdown_pose(r, t):
    """Crouch with the box, leave it on the floor at 65%, stand up empty handed."""
    c = ss(0, .62, t) if t < .62 else 1 - ss(.65, 1, t)
    hands = {}
    for s in (1, -1):
        if t < .62:
            hands[s] = (world_of(r, box_carry(r, s)).lerp(box_floor(r, s), ss(0, .62, t)), True)
        else:
            hands[s] = (box_floor(r, s).lerp(world_of(r, r.hang[s]), ss(.65, 1, t)), True)
    return squat_pose(r, c, hands)


TOOL = -1          # the tool hand: the character's right hand (the arm at -X; characters face -Y)


def hammer_pose(r, t):
    """One-handed hammer on a stake / board in front, low: raise behind the head, strike, small bounce."""
    s = TOOL
    lean = 22
    p = Pose(r).torso(lean=lean, lift=-.05).head(nod=-14)
    strike = V(s * .12, -.52, r.pivot.z + .10)
    top = V(s * .34, .02, r.shoulder[s].z + .30)
    if t < .55:
        a = ss(0, .55, t); hand = strike.lerp(top, a); pole = V(s * 1, .2 + .6 * a, -1 + .9 * a)
    elif t < .7:
        a = ((t - .55) / .15) ** 2; hand = top.lerp(strike, a); pole = V(s * 1, .8 - .6 * a, -.1 - .9 * a)
    else:
        b = math.sin(math.pi * (t - .7) / .3) * .05; hand = strike + V(0, 0, b); pole = V(s * 1, .2, -1)
    p.hand(s, hand, pole=pole, world=True)
    # The other hand holds the stake under the blow.
    p.hand(-s, V(-s * .02, -.50, strike.z - .17), pole=V(-s * 1, .3, -1), world=True, bend=-10)
    p.foot(s, dy=-.04); p.foot(-s, dy=.10, dx=.02)
    return p


SLEDGE_GRIP = .26      # second hand up the handle from the end hand (character units; the game scales by 0.45)


def sledge_frame(r, t):
    """Angle of the swing (radians, 0 = hands straight in front at shoulder height) and torso lean/lift."""
    top, hit = math.radians(118), math.radians(-42)
    if t < .45:
        a = ss(0, .45, t); ang = mix(hit, top, a); lag = mix(0, math.radians(80), a)
    elif t < .55:
        ang, lag = top, math.radians(80)
    elif t < .70:
        a = ((t - .55) / .15) ** 1.6; ang = mix(top, hit, a); lag = mix(math.radians(80), 0, ss(0, 1, a))
    else:
        ang, lag = hit, 0.0
    strike = 1 - min(1, abs(ang - hit) / (top - hit))
    return ang, lag, mix(-4, 30, strike), mix(0, -.10, strike)


def sledge_pose(r, t):
    """Two hands on the handle: the tool hand at the end, the other hand up the handle; overhead swing."""
    ang, lag, lean, lift = sledge_frame(r, t)
    p = Pose(r).torso(lean=lean, lift=lift).head(nod=-6 - 10 * ss(-.2, .4, -math.sin(ang)))
    T = _rot(lean, 0, 0); piv = r.pivot + V(0, 0, lift)
    center = piv + T @ ((r.shoulder[1] + r.shoulder[-1]) / 2 - r.pivot)
    lateral = abs(r.shoulder[1].x) - .07
    radius = .86 * math.sqrt(max(.04, r.reach ** 2 - lateral ** 2)) - SLEDGE_GRIP * .5
    end = center + V(TOOL * .07, -math.cos(ang) * radius, math.sin(ang) * radius)
    u = V(0, -math.cos(ang + lag), math.sin(ang + lag))
    p.hand(TOOL, end, pole=V(TOOL * 1, .1, -1), world=True)
    grip = mix(.08, SLEDGE_GRIP, ss(-.5, .6, math.sin(ang)))     # the upper hand slides down for the blow
    p.hand(-TOOL, end + u * grip, pole=V(-TOOL * 1, .1, -1), world=True)
    p.foot(TOOL, dy=-.10, dx=.04); p.foot(-TOOL, dy=.12, dx=.04)
    return p


def dump_pose(r, t):
    """At the skip: lift the load over the rim and tip it in (released at 50%), then let the arms down."""
    sz = r.shoulder[1].z
    carry = lambda s: box_carry(r, s)
    over = lambda s: V(s * .22, -.60, sz + .04)
    tip = lambda s: V(s * .20, -.74, sz - .16)
    p = Pose(r)
    for s in (1, -1):
        if t < .38:
            a = ss(0, .38, t); hand = carry(s).lerp(over(s), a); bend = -20 + 10 * a
        elif t < .55:
            a = ss(.38, .55, t); hand = over(s).lerp(tip(s), a); bend = -10 + 45 * a
        else:
            a = ss(.55, 1, t); hand = tip(s).lerp(r.hang[s], a); bend = 35 * (1 - a)
        p.hand(s, hand, pole=V(s * 1, .3, -.8), bend=bend)
    lean = -5 * ss(0, .38, t) if t < .38 else (-5 + 23 * ss(.38, .55, t) if t < .55 else 18 * (1 - ss(.55, 1, t)))
    p.torso(lean=lean, lift=-.01).head(nod=8 * ss(.3, .55, t) * (1 - ss(.6, 1, t)))
    return p


def point_pose(r, t):
    """The foreman directs: the right arm points at the works, the clipboard held at the chest."""
    sz = r.shoulder[1].z
    p = Pose(r).torso(turn=5 * math.sin(TAU * t)).head(nod=-3 + 3 * math.sin(TAU * t * 2))
    p.hand(TOOL, V(TOOL * .30, -.66, sz + .06 + .04 * math.sin(TAU * t * 2)), pole=V(TOOL * 1, .2, -.6), bend=-5)
    p.hand(-TOOL, V(-TOOL * .17, -.30, sz - .42), pole=V(-TOOL * 1, .4, -1), bend=-30)
    return p


def clipboard_pose(r, t):
    """The foreman writes on his clipboard (board at the chest, the right hand scribbling), head down."""
    sz = r.shoulder[1].z
    p = Pose(r).torso(lean=4).head(nod=16 + 2 * math.sin(TAU * t))
    p.hand(-TOOL, V(-TOOL * .13, -.33, sz - .42), pole=V(-TOOL * 1, .4, -1), bend=-30)
    w = TAU * t * 3
    p.hand(TOOL, V(TOOL * (.03 + .03 * math.cos(w)), -.37, sz - .38 + .015 * math.sin(2 * w)), pole=V(TOOL * 1, .4, -1), bend=-20)
    return p


CREW_CLIPS = [
    ("Idle", 60, lambda r, t: idle_pose(r, t)),
    ("Walking", 30, lambda r, t: walk_pose(r, t)),
    ("CarryIdle", 60, lambda r, t: idle_pose(r, t, carry=True)),
    ("CarryWalking", 36, lambda r, t: walk_pose(r, t, carry=True)),
    ("Pickup", 48, pickup_pose),
    ("PutDown", 66, putdown_pose),
    ("Hammer", 36, hammer_pose),
    ("Sledge", 54, sledge_pose),
    ("Dump", 42, dump_pose),
    ("Point", 60, point_pose),
    ("Clipboard", 90, clipboard_pose),
]
LOOPS = {"Idle", "Walking", "CarryIdle", "CarryWalking", "Hammer", "Sledge", "Point", "Clipboard"}


def author_crew(rig, prefix, hip_half):
    rig.animation_data_clear()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    r = Rig(rig); r.set_hang(hip_half)
    rig.animation_data_create()
    made = []
    for name, frames, fn in CREW_CLIPS:
        act = bpy.data.actions.new(prefix + "|" + name); act.use_fake_user = True
        rig.animation_data.action = act
        last = {}
        for f in range(frames + 1):
            t = f / frames
            put(rig, f + 1, fn(r, t if name in LOOPS or t < 1 else 1.0), last)
        made.append(act)
    rig.animation_data.action = None
    return made, r


# ------------------------------------------------------------------------------------------------- customers
def fcurves(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
        return out


def adduct_customer(rig, angle_deg):
    """A constant shoulder adduction on every clip (the sculpt's arms are wider than the rig's), keyed after the
    clip's own rotation so the motion stays the same."""
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    arms = [pb for pb in rig.pose.bones if pb.name.startswith("UpperArm")]
    adds = {}
    for pb in arms:
        s = 1 if pb.bone.head_local.x > 0 else -1
        rest = pb.bone.matrix_local.to_quaternion()
        adds[pb.name] = rest.inverted() @ Quaternion(Y, math.radians(s * angle_deg)) @ rest
    for act in bpy.data.actions:
        for pb in arms:
            path = f'pose.bones["{pb.name}"].rotation_quaternion'
            curves = [next((c for c in fcurves(act) if c.data_path == path and c.array_index == i), None) for i in range(4)]
            if any(c is None for c in curves):
                continue
            frames = sorted({round(k.co.x, 3) for c in curves for k in c.keyframe_points})
            values = [Quaternion([c.evaluate(f) for c in curves]) for f in frames]
            for f, q in zip(frames, values):
                q2 = q @ adds[pb.name]
                for i, c in enumerate(curves):
                    c.keyframe_points.insert(f, q2[i], options={'REPLACE', 'FAST'})


def free_walk(rig, rig_name):
    """build_customers.py: keep the loaded walk as WalkingWithBasket and author a free two-arm Walking."""
    walking = next(a for a in bpy.data.actions if a.name.endswith("|Walking"))
    frames = range(1, 26)
    samples_ = []
    rig.animation_data.action = walking
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        samples_.append({b.name: (b.location.copy(), b.rotation_quaternion.copy(), b.scale.copy()) for b in rig.pose.bones})
    walking.name = rig_name + "_Rig|WalkingWithBasket"
    free = bpy.data.actions.new(rig_name + "_Rig|Walking")
    for action, carrying in [(walking, True), (free, False)]:
        rig.animation_data.action = action
        for frame, pose in zip(frames, samples_):
            phase = (frame - 1) / 24 * TAU
            for bone in rig.pose.bones:
                bone.rotation_mode = "QUATERNION"
                bone.location, bone.rotation_quaternion, bone.scale = pose[bone.name]
                side = 1 if bone.name.endswith("L") else -1
                swing = math.sin(phase) * side
                if bone.name == "Torso":
                    bone.location = Vector((0, 0, 0))
                if bone.name.startswith("Thigh_"):
                    bone.rotation_quaternion = Quaternion((1, 0, 0), math.radians(-18) * swing)
                elif bone.name.startswith("Shin_"):
                    bone.rotation_quaternion = Quaternion((1, 0, 0), math.radians(45) * max(0, math.cos(phase) * side))
                elif bone.name.startswith("Foot_"):
                    bone.rotation_quaternion = Quaternion((1, 0, 0), math.radians(18 * swing - 45 * max(0, math.cos(phase) * side)))
                elif not carrying and bone.name.startswith("UpperArm_"):
                    bone.rotation_quaternion = Quaternion((1, 0, 0), math.radians(22) * swing)
                elif not carrying and bone.name.startswith("Forearm_"):
                    bone.rotation_quaternion = Quaternion((1, 0, 0), math.radians(-8))
                elif not carrying and bone.name.startswith("Hand_"):
                    bone.rotation_quaternion = Quaternion((1, 0, 0), 0)
                bone.keyframe_insert(data_path="location", frame=frame)
                bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                bone.keyframe_insert(data_path="scale", frame=frame)
            bpy.context.view_layer.update()
            floor = min(rig.pose.bones["Foot_L"].head.z, rig.pose.bones["Foot_R"].head.z)
            torso = rig.pose.bones["Torso"]
            torso.location.y += .12 - floor
            torso.keyframe_insert(data_path="location", frame=frame)
    rig.animation_data.action = None


def keep_props(others, name):
    props = []
    for item in others:
        if item.type != 'MESH':
            bpy.data.objects.remove(item, do_unlink=True); continue
        group = item.vertex_groups.get("Prop")
        bm = bmesh.new(); bm.from_mesh(item.data)
        deform = bm.verts.layers.deform.active
        remove = [v for v in bm.verts if not group or not deform or v[deform].get(group.index, 0) < .5]
        bmesh.ops.delete(bm, geom=remove, context="VERTS"); bm.to_mesh(item.data); bm.free()
        if len(item.data.vertices):
            item.name = name + "_Prop"; props.append(item)
        else:
            bpy.data.objects.remove(item, do_unlink=True)
    return props


# ================================================================================================= preview
def tool_mesh(kind):
    """Stand-ins for the game's Tool_Hammer / Tool_Sledgehammer, for the approval pictures only."""
    bm = bmesh.new()
    if kind == "Hammer":
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=.035, radius2=.035, depth=.62, matrix=Matrix.Translation((0, 0, .26)))
        bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((0, -.04, .58)) @ Matrix.Diagonal((.10, .26, .10, 1)))
    else:
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=.04, radius2=.04, depth=1.25, matrix=Matrix.Translation((0, 0, .55)))
        bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((0, 0, 1.18)) @ Matrix.Diagonal((.16, .40, .16, 1)))
    me = bpy.data.meshes.new(kind); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Tool_" + kind, me); bpy.context.collection.objects.link(o)
    mat = bpy.data.materials.new("ToolMat"); mat.diffuse_color = (.35, .3, .28, 1)
    me.materials.append(mat)
    return o


def place_tool(tool, rig, r, kind):
    """Same rule as the game (CheckoutWorksScene.LateUpdate): the handle sits in the tool hand; the hammer's handle
    is across the fist, the sledge's handle runs through both hands."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones
    M = rig.matrix_world
    hand = M @ pb[r.hd[TOOL]].head; fore = M @ pb[r.fa[TOOL]].head
    d = (hand - fore).normalized()
    if kind == "Sledge":
        other = M @ pb[r.hd[-TOOL]].head
        up = (other - hand).normalized()
        base = hand - up * .06
    else:
        side = (M.to_3x3() @ X).normalized()
        swing_axis = d.cross(side)       # the handle leaves the fist across the forearm, pointing ahead of the swing
        up = swing_axis.normalized() if swing_axis.length > 1e-4 else Z
        base = hand + d * .07 - up * .14
    q = Z.rotation_difference(up)
    tool.matrix_world = Matrix.Translation(base) @ q.to_matrix().to_4x4()


def render_sheet(rig, body, r, name, frames, kind="crew"):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = (900, 1000) if os.environ.get("NPC_FRAMES") else (520, 620)
    world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.80, .85, .89, 1)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN')); sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30)); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; sc.camera = cam
    tools = {k: tool_mesh(k) for k in ("Hammer", "Sledge")} if kind == "crew" else {}
    os.makedirs(PREVIEWS, exist_ok=True)
    shots = []
    for i, (label, action, t, yaw, scale) in enumerate(frames):
        rig.animation_data.action = bpy.data.actions[action] if action else None
        if action:
            act = bpy.data.actions[action]
            f0, f1 = act.frame_range
            sc.frame_set(int(round(f0 + (f1 - f0) * t)))
        else:
            for pb in rig.pose.bones:
                pb.matrix_basis = Matrix()
            sc.frame_set(1)
        for k, tool in tools.items():
            show = action is not None and action.endswith("|" + k)
            tool.hide_render = not show
            if show:
                place_tool(tool, rig, r, k)
        ang = math.radians(yaw)
        dist = 12
        cam.location = (math.sin(ang) * dist, -math.cos(ang) * dist, 1.25)
        cam.rotation_euler = (math.radians(90), 0, ang)
        cam.data.ortho_scale = scale
        path = os.path.join(PREVIEWS, f"{name}_{i:02d}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        shots.append((label, path))
    return shots


def contact_sheet(shots, out):
    imgs = []
    for label, path in shots:
        im = bpy.data.images.load(path); imgs.append((label, im))
    w, h = imgs[0][1].size
    cols = min(6, len(imgs)); rows = (len(imgs) + cols - 1) // cols
    sheet = np.ones((rows * h, cols * w, 4), dtype=np.float32)
    for i, (label, im) in enumerate(imgs):
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        r_, c_ = divmod(i, cols)
        y0 = (rows - 1 - r_) * h
        sheet[y0:y0 + h, c_ * w:(c_ + 1) * w] = px
    img = bpy.data.images.new("sheet", cols * w, rows * h, alpha=True)
    img.pixels = sheet.ravel()
    img.filepath_raw = out; img.file_format = 'PNG'; img.save()
    return [l for l, _ in imgs]


# ================================================================================================= export
def export_fbx(rig, objects, path):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in [rig] + objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
                             bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                             bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y', path_mode='STRIP')


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    name = argv[0]; mode = argv[1] if len(argv) > 1 else "preview"
    cfg = TARGETS[name]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    mesh = load_lite(name)
    image = next((n.image for m in mesh.data.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
    L = measure(mesh)
    rig, others = import_rig(cfg["rig"])
    side = fit_rig(rig, L)
    missed = skin_weights(mesh, L, side)
    out_name = cfg["out"]
    report = {"sculpt": name, "out": out_name, "arm_piece_vertices": missed,
              "landmarks": {(k if isinstance(k, str) else f"{k[0]}{'+' if k[1] > 0 else '-'}"): (list(map(lambda x: round(x, 3), v)) if isinstance(v, Vector) else v) for k, v in L.items()}}
    if cfg["kind"] == "crew":
        for o in others:
            bpy.data.objects.remove(o, do_unlink=True)
        body = bind(mesh, rig, out_name)
        acts, r = author_crew(rig, out_name + "_Rig", L["half_hip"])
        props = []
        frames = [("rest", None, 0, 0, 3.2), ("idle", acts[0].name, .25, 30, 3.2), ("walk", acts[1].name, .25, 60, 3.2),
                  ("walk", acts[1].name, .75, 90, 3.2), ("carry", acts[3].name, .3, 50, 3.2), ("pickup", acts[4].name, .45, 70, 3.2),
                  ("hammer up", acts[6].name, .55, -60, 3.4), ("hammer hit", acts[6].name, .72, -60, 3.4),
                  ("sledge up", acts[7].name, .5, 70, 3.8), ("sledge mid", acts[7].name, .62, 90, 3.8), ("sledge hit", acts[7].name, .74, 70, 3.8),
                  ("arm up (back)", acts[7].name, .5, 160, 3.8), ("dump lift", acts[8].name, .4, 60, 3.2),
                  ("dump tip", acts[8].name, .52, 60, 3.2), ("point", acts[9].name, .25, 30, 3.2), ("clipboard", acts[10].name, .3, 25, 3.2)]
    else:
        props = keep_props(others, out_name)
        body = bind(mesh, rig, out_name)
        free_walk(rig, cfg["rig"])
        r = Rig(rig)
        wide = math.degrees(math.atan2(abs(r.wrist[1].x - r.shoulder[1].x), r.shoulder[1].z - r.wrist[1].z))
        add = max(0.0, min(16.0, wide - 12.0))
        adduct_customer(rig, add)
        report["adduction_deg"] = round(add, 1)
        acts = sorted(bpy.data.actions, key=lambda a: a.name)
        report["clips"] = [a.name for a in acts]
        pick = lambda key: next(a.name for a in acts if a.name.endswith("|" + key))
        frames = [("rest", None, 0, 0, 3.2), ("idle", pick("Idle"), .3, 30, 3.2), ("walk", pick("Walking"), .25, 60, 3.2),
                  ("basket walk", pick("WalkingWithBasket"), .5, 60, 3.2), ("shelf", pick("GetFromShelf"), .5, 40, 3.2),
                  ("special", pick("BuyAtSpecialSector"), .5, 40, 3.2), ("pay", pick("PayAtCheckout"), .5, 40, 3.2)]
    for o in props:
        o.hide_render = True          # the old built-in basket/cart: hidden in the game too (CheckoutShopperRig)
    report["clips"] = [a.name for a in bpy.data.actions]
    if os.environ.get("NPC_FRAMES"):          # debugging: [[label, clip suffix or null, t, yaw, scale], ...]
        want = json.loads(os.environ["NPC_FRAMES"])
        frames = [(l, (next(a.name for a in bpy.data.actions if a.name.endswith("|" + c)) if c else None), t, yw, sc_) for l, c, t, yw, sc_ in want]
        bpy.context.scene.render.resolution_x = 900
    shots = render_sheet(rig, body, r, name, frames, cfg["kind"])
    labels = contact_sheet(shots, os.path.join(PREVIEWS, name + "_rig_sheet.png"))
    report["sheet"] = labels
    if mode == "export" and cfg["folder"]:
        folder = os.path.normpath(os.path.join(CHARS, cfg["folder"]))
        os.makedirs(folder, exist_ok=True)
        look = cfg.get("look", out_name)
        if image is not None:
            image.filepath_raw = os.path.join(folder, look + ".png"); image.file_format = 'PNG'; image.save()
        for t in [o for o in bpy.data.objects if o.name.startswith("Tool_")]:
            bpy.data.objects.remove(t, do_unlink=True)
        export_fbx(rig, [body] + props, os.path.join(folder, out_name + ".fbx"))
        report["fbx"] = os.path.join(cfg["folder"], out_name + ".fbx")
        report["texture"] = os.path.join(cfg["folder"], look + ".png")
    with open(os.path.join(LITE, name + "_rig.json"), "w") as f:
        json.dump(report, f, indent=1)
    print("NPC_RIG_OK", json.dumps({k: report[k] for k in report if k != "landmarks"}))


if os.environ.get("NPC_NO_MAIN") != "1":
    main()
