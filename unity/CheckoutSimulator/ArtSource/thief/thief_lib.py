
"""Thief character - geometry helper library (hand modeling helpers: sweeps, ellipsoids, voxel fuse).
exec(open(D+'thief_lib.py').read())"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
D='/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/ArtSource/thief/'
QA='/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/Temp/qa/thief/'
V=Vector

def coll(name, hide=False):
    c=bpy.data.collections.get(name)
    if not c:
        c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c

def new_obj(name, bm, col='WIP'):
    old=bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(name, me); coll(col).objects.link(o)
    return o

def kill(*names):
    for n in names:
        o=bpy.data.objects.get(n)
        if o: bpy.data.objects.remove(o, do_unlink=True)

def kill_prefix(p):
    for o in [o for o in bpy.data.objects if o.name.startswith(p)]:
        bpy.data.objects.remove(o, do_unlink=True)

def ell(name, c, r, rot=(0,0,0), seg=32, ring=20, p=2.0, col='WIP'):
    """ellipsoid / superellipsoid (p>2 = rounded box) at c with radii r, euler rot in degrees"""
    bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=seg,v_segments=ring,radius=1.0)
    R=Euler([math.radians(a) for a in rot]).to_matrix()
    for v in bm.verts:
        n=v.co.copy()
        if p!=2.0:
            n=V([math.copysign(abs(x)**(2.0/p),x) for x in n])
        v.co=R@V((n.x*r[0],n.y*r[1],n.z*r[2]))+V(c)
    return new_obj(name,bm,col)

def frames(pts, up=None):
    T=[]
    for i in range(len(pts)):
        a=pts[max(i-1,0)]; b=pts[min(i+1,len(pts)-1)]
        T.append((b-a).normalized())
    u=V(up) if up else (V((0,0,1)) if abs(T[0].z)<0.9 else V((1,0,0)))
    N=[(u-T[0]*u.dot(T[0])).normalized()]
    for i in range(1,len(pts)):
        n=N[-1]-T[i]*N[-1].dot(T[i]); N.append(n.normalized())
    B=[T[i].cross(N[i]) for i in range(len(pts))]
    return T,N,B

def sweep(name, pts, radii, seg=12, up=None, caps=True, col='WIP', twist=0.0, prof=None):
    """tube along pts; radii: float or (rn,rb) per point; prof(angle)->radius multiplier"""
    pts=[V(p) for p in pts]
    T,N,B=frames(pts,up)
    bm=bmesh.new(); rings=[]
    for i,p in enumerate(pts):
        r=radii[i]; rn,rb=(r,r) if not isinstance(r,(tuple,list)) else r
        ring=[]
        for k in range(seg):
            a=2*math.pi*k/seg+twist*i
            m=prof(a) if prof else 1.0
            ring.append(bm.verts.new(p+N[i]*math.cos(a)*rn*m+B[i]*math.sin(a)*rb*m))
        rings.append(ring)
    for i in range(len(rings)-1):
        for k in range(seg):
            bm.faces.new((rings[i][k],rings[i][(k+1)%seg],rings[i+1][(k+1)%seg],rings[i+1][k]))
    if caps:
        for idx,sgn in ((0,-1),(len(pts)-1,1)):
            r=radii[idx]; rr=r if not isinstance(r,(tuple,list)) else min(r)
            c=bm.verts.new(pts[idx]+T[idx]*sgn*rr*0.75)
            ring=rings[idx]
            for k in range(seg):
                f=(ring[k],ring[(k+1)%seg],c) if sgn>0 else (ring[(k+1)%seg],ring[k],c)
                bm.faces.new(f)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    return new_obj(name,bm,col)

def bez(p0,p1,p2,p3,n):
    p0,p1,p2,p3=V(p0),V(p1),V(p2),V(p3)
    return [ (1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3 for t in [i/(n-1) for i in range(n)]]

def catmull(ctrl, n_per=6):
    c=[V(p) for p in ctrl]; c=[c[0]]+c+[c[-1]]; out=[]
    for i in range(1,len(c)-2):
        p0,p1,p2,p3=c[i-1],c[i],c[i+1],c[i+2]
        for j in range(n_per):
            t=j/n_per
            out.append(0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t**3))
    out.append(c[-2]); return out

def join(objs, name, col='WIP'):
    objs=[o for o in objs if o]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]
    bpy.ops.object.join()
    o=bpy.context.active_object
    kill(name) if name!=o.name and bpy.data.objects.get(name) else None
    o.name=name; o.data.name=name
    return o

def apply_mods(o):
    dg=bpy.context.evaluated_depsgraph_get()
    me=bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    old=o.data; o.modifiers.clear(); o.data=me; me.name=o.name
    bpy.data.meshes.remove(old)

def voxel(o, size, adapt=0.0):
    m=o.modifiers.new('vox','REMESH'); m.mode='VOXEL'; m.voxel_size=size; m.adaptivity=adapt; m.use_smooth_shade=True
    apply_mods(o); return o

def fuse(objs, name, size, smooth_iter=0, smooth_fac=0.5, col='WIP'):
    o=join(objs,name,col); voxel(o,size)
    if smooth_iter: smooth(o,smooth_iter,smooth_fac)
    return o

def smooth(o, iters, fac=0.5, mask=None):
    bm=bmesh.new(); bm.from_mesh(o.data)
    vs=[v for v in bm.verts if (mask is None or mask(v.co))]
    for i in range(iters):
        bmesh.ops.smooth_vert(bm,verts=vs,factor=fac,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    bm.to_mesh(o.data); bm.free(); o.data.update()

def boolean(o, cutter, op='DIFFERENCE', solver='EXACT'):
    m=o.modifiers.new('b','BOOLEAN'); m.operation=op; m.object=cutter; m.solver=solver
    apply_mods(o)

def decimate(o, faces):
    n=len(o.data.polygons)
    tris=sum(len(p.vertices)-2 for p in o.data.polygons)
    m=o.modifiers.new('dec','DECIMATE'); m.ratio=min(1.0,faces/max(tris,1)); m.use_collapse_triangulate=True
    apply_mods(o); return o

def tris(o):
    return sum(len(p.vertices)-2 for p in o.data.polygons)

def shade_smooth(o):
    for p in o.data.polygons: p.use_smooth=True

def bvh_of(o):
    dg=bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(o,dg)

def srgb(h):
    h=h.lstrip('#'); c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple((x/12.92 if x<=0.04045 else ((x+0.055)/1.055)**2.4) for x in c)+(1.0,)

def displace_fn(o, fn):
    """fn(co, normal) -> offset along normal"""
    me=o.data; me.calc_normals_split() if hasattr(me,'calc_normals_split') else None
    for v in me.vertices:
        d=fn(v.co, v.normal)
        if d: v.co=v.co+v.normal*d
    me.update()

def move_fn(o, fn):
    for v in o.data.vertices:
        v.co=fn(v.co)
    o.data.update()


import numpy as np
def get_co(o):
    a=np.empty(len(o.data.vertices)*3); o.data.vertices.foreach_get('co',a); return a.reshape(-1,3)
def set_co(o,a):
    o.data.vertices.foreach_set('co',a.reshape(-1)); o.data.update()
def get_no(o):
    o.data.update()
    a=np.empty(len(o.data.vertices)*3); o.data.vertices.foreach_get('normal',a); return a.reshape(-1,3)

def brush(o, c, r, amt, dirv=None, rot=None, fall=2.0):
    """procedural sculpt: gaussian-ish ellipsoid falloff bump. dirv None=along normal, else fixed vector"""
    co=get_co(o); d=co-np.array(c)
    if rot is not None:
        R=np.array(Euler([math.radians(a) for a in rot]).to_matrix())
        d=d@R
    q=np.sqrt(((d/np.array(r))**2).sum(1))
    w=np.exp(-(q**fall)*1.5)
    w[q>2.5]=0
    if dirv is None: n=get_no(o)
    else: n=np.tile(np.array(dirv,dtype=float),(len(co),1))
    co=co+n*(w*amt)[:,None]
    set_co(o,co)

def smooth_mask_np(o, iters, fac, wfn):
    """laplacian smooth weighted per vertex by wfn(co array)->weights"""
    me=o.data; n=len(me.vertices)
    e=np.empty(len(me.edges)*2,dtype=np.int64); me.edges.foreach_get('vertices',e); e=e.reshape(-1,2)
    co=get_co(o); w=np.clip(wfn(co),0,1)*fac
    deg=np.bincount(e.ravel(),minlength=n).astype(float); deg[deg==0]=1
    for i in range(iters):
        s=np.zeros_like(co)
        np.add.at(s,e[:,0],co[e[:,1]]); np.add.at(s,e[:,1],co[e[:,0]])
        avg=s/deg[:,None]
        co=co+(avg-co)*w[:,None]
    set_co(o,co)

def ico(name, c, r, sub=6, col='WIP'):
    bm=bmesh.new(); bmesh.ops.create_icosphere(bm,subdivisions=sub,radius=1.0)
    for v in bm.verts: v.co=V((v.co.x*r[0],v.co.y*r[1],v.co.z*r[2]))+V(c)
    return new_obj(name,bm,col)

def prism(name, poly2d, axis_m, y0, y1, col='WIP', front_scale=1.0, front_y=None):
    """poly2d list of (x,z) in local frame; extruded along local y from y0 to y1; axis_m = 4x4 matrix to world"""
    bm=bmesh.new()
    a=[bm.verts.new(axis_m@V((x*front_scale,y0,z*front_scale))) for x,z in poly2d]
    if front_y is not None:
        m=[bm.verts.new(axis_m@V((x,front_y,z))) for x,z in poly2d]
    b=[bm.verts.new(axis_m@V((x,y1,z))) for x,z in poly2d]
    n=len(poly2d)
    bm.faces.new(a[::-1]); bm.faces.new(b)
    rows=[a,m,b] if front_y is not None else [a,b]
    for r0,r1 in zip(rows[:-1],rows[1:]):
        for i in range(n):
            j=(i+1)%n; bm.faces.new((r0[i],r0[j],r1[j],r1[i]))
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    return new_obj(name,bm,col)
