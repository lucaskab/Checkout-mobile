
# ---- head / neck high-poly (procedural sculpt) ----
EYE_R=0.032
EYE_C=[V((-0.056,-0.123,2.172)),V((0.056,-0.123,2.172))]
def head_base():
    kill('hp_base')
    h=ico('hp_base',(0,-0.008,2.165),(0.124,0.158,0.172),sub=6)
    co=get_co(h)
    z=co[:,2]; 
    # jaw taper in x below cheek line, chin narrow
    t=np.clip((2.13-z)/0.15,0,1); t=t*t*(3-2*t)
    co[:,0]*=1.0-0.13*t
    # back of lower head tucks in toward neck
    tb=np.clip((2.10-z)/0.12,0,1)*(co[:,1]>0.0)
    co[:,1]=np.where(co[:,1]>0, co[:,1]*(1-0.35*tb), co[:,1])
    # flatten the face front a bit (wider front plane)
    set_co(h,co)
    B=lambda *a,**k: brush(h,*a,**k)
    B((0,-0.12,2.06),(0.08,0.06,0.07),0.022,(0,-1,0))       # muzzle forward
    for s in (-1,1):
        B((s*0.062,-0.13,2.175),(0.045,0.05,0.045),0.016,(0,-1,0))   # flatten face plane at eyes
    B((0,-0.11,1.998),(0.055,0.04,0.032),0.024,(0,-1,-0.2))   # chin
    B((0,-0.10,1.985),(0.07,0.05,0.025),0.006,(0,0,-1))      # chin underside
    B((0,-0.13,2.222),(0.095,0.04,0.024),0.012,(0,-1,0.1))   # brow ridge
    for s in (-1,1):
        B((s*0.068,-0.115,2.105),(0.04,0.04,0.035),0.014)            # cheek
        B((s*0.098,-0.04,2.04),(0.035,0.06,0.04),0.008)                # jaw angle
        B((s*0.115,-0.06,2.20),(0.03,0.05,0.04),-0.006)               # temple
    B((0,-0.155,2.15),(0.014,0.03,0.04),0.012,(0,-1,0))     # nose bridge
    B((0,-0.16,2.112),(0.02,0.03,0.02),0.030,(0,-1,0.05))    # nose tip
    for s in (-1,1):
        B((s*0.021,-0.152,2.103),(0.014,0.02,0.012),0.012)    # alae
    B((0,-0.165,2.09),(0.012,0.02,0.007),0.004,(0,1,0.6))    # nose underside tuck
    B((0,-0.152,2.072),(0.034,0.02,0.010),0.005)              # upper lip
    B((0,-0.148,2.049),(0.028,0.02,0.010),0.006)              # lower lip
    B((0,-0.146,2.034),(0.03,0.02,0.008),-0.004)              # under lower lip groove
    for i in range(13):
        x=-0.032+i*0.064/12; zz=2.061+0.007*(x/0.032)**2
        B((x,-0.16,zz),(0.006,0.03,0.0022),-0.0016,(0,1,0))   # mouth line (smile)
    for s in (-1,1):
        B((s*0.037,-0.14,2.066),(0.008,0.02,0.008),-0.002,(0,1,0))   # mouth corners
        B((s*0.045,-0.135,2.075),(0.02,0.03,0.025),0.003)           # smile cheek bump
    smooth(h,2,0.4)
    return h


def almond(s, w=0.035, hu=0.027, hl=0.018, n=24):
    pts=[]
    for k in range(n+1):
        t=k/n; x=-w+2*w*t
        pts.append((x, hu*math.sin(math.pi*t)**0.75+0.003*(x*s)/w))
    for k in range(1,n):
        t=1-k/n; x=-w+2*w*t
        pts.append((x, -hl*math.sin(math.pi*t)**0.9+0.003*(x*s)/w))
    return pts

def eye_frame(i):
    s=(-1,1)[i]
    return Matrix.Translation(EYE_C[i])@Matrix.Rotation(math.radians(s*-16),4,'Z')

def point_in_poly(x,z,poly):
    ins=False; n=len(poly); j=n-1
    for k in range(n):
        xi,zi=poly[k]; xj,zj=poly[j]
        if ((zi>z)!=(zj>z)) and (x<(xj-xi)*(z-zi)/(zj-zi+1e-12)+xi): ins=not ins
        j=k
    return ins

def eye_hug(h, skin=0.0045):
    for it in range(3):
        bvh=bvh_of(h)
        for i,c in enumerate(EYE_C):
            for dx,dz,rr in ((0,0,(0.032,0.03,0.027)),):
                hit=bvh.ray_cast(V((c.x+dx,-0.6,c.z+dz)),V((0,1,0)))
                tgt=c.y-EYE_R-skin
                delta=hit[0].y-tgt
                if delta>0: brush(h,(c.x,c.y-EYE_R,c.z),rr,delta*1.05,(0,-1,0))
    # safety: any eyeball point outside skin -> push skin
    def wm(co):
        out=np.zeros(len(co))
        for c in EYE_C:
            r=np.sqrt(((co-np.array(c))**2).sum(1)); out=np.maximum(out,np.exp(-((r-EYE_R)/0.02)**2))
        return out
    for it in range(6):
        co=get_co(h)
        for c in EYE_C:
            c=np.array(c); d=co-c; r=np.sqrt((d**2).sum(1))
            m=(r<EYE_R+0.0035)
            co[m]=c+d[m]/r[m,None]*(EYE_R+0.0035)
        set_co(h,co)
        if it==2: voxel(h,0.0022)
        if it<5: smooth_mask_np(h,4,0.5,wm)

def eye_open(h, lid=0.0045):
    bm=bmesh.new(); bm.from_mesh(h.data); bm.faces.ensure_lookup_table()
    dele=[]
    for i,s in enumerate((-1,1)):
        Mi=eye_frame(i).inverted(); poly=almond(s)
        for f in bm.faces:
            q=Mi@f.calc_center_median()
            if q.y<0 and q.y>-0.06 and abs(q.x)<0.05 and abs(q.z)<0.04 and point_in_poly(q.x,q.z,poly):
                dele.append(f)
    bmesh.ops.delete(bm,geom=list(set(dele)),context='FACES')
    # relax boundary loops
    bverts=[v for v in bm.verts if v.is_boundary]
    for it in range(25):
        new={}
        for v in bverts:
            nb=[e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb)==2: new[v]=(v.co*0.5+(nb[0].co+nb[1].co)*0.25)
        for v,c in new.items(): v.co=c
    # extrude rim inward toward eyeball (lid thickness)
    bedges=[e for e in bm.edges if e.is_boundary]
    ret=bmesh.ops.extrude_edge_only(bm,edges=bedges)
    nv=[g for g in ret['geom'] if isinstance(g,bmesh.types.BMVert)]
    for v in nv:
        c=min(EYE_C,key=lambda c:(v.co-c).length)
        d=v.co-c; v.co=c+d.normalized()*(EYE_R+0.0008)
    ret2=bmesh.ops.extrude_edge_only(bm,edges=[g for g in ret['geom'] if isinstance(g,bmesh.types.BMEdge) and g.is_boundary])
    nv2=[g for g in ret2['geom'] if isinstance(g,bmesh.types.BMVert)]
    for v in nv2:
        c=min(EYE_C,key=lambda c:(v.co-c).length)
        d=v.co-c; v.co=c+d.normalized()*(EYE_R*0.85)
    bm.to_mesh(h.data); bm.free(); h.data.update()

def build_head():
    kill_prefix('hp_')
    h=head_base()
    P=[h]
    P.append(sweep('hp_neck',[(0,0.02,1.78),(0,0.015,1.90),(0,0.0,1.99),(0,0.01,2.06)],[(0.069,0.066),(0.066,0.064),(0.068,0.07),(0.075,0.08)],seg=32))
    for s in (-1,1):
        e=ell('hp_ear%d'%s,(s*0.121,0.012,2.12),(0.016,0.038,0.055),rot=(0,s*12,s*-22),seg=32,ring=24)
        cut=ell('hp_earcut%d'%s,(s*0.138,0.006,2.114),(0.011,0.028,0.041),rot=(0,s*12,s*-22))
        boolean(e,cut); kill(cut.name)
        P.append(e)
    h=fuse(P,'hp_Head',0.0025)
    def wj(co):
        z=co[:,2]; w=np.exp(-((z-2.0)/0.035)**2)*(co[:,1]>-0.06)
        ex=np.exp(-(((np.abs(co[:,0])-0.11)/0.02)**2+((co[:,1]-0.02)/0.05)**2+((co[:,2]-2.12)/0.06)**2))
        return np.maximum(w,ex)*1.0+0.15
    smooth_mask_np(h,8,0.5,wj)
    eye_hug(h)
    # upper lid crease
    for i,s in enumerate((-1,1)):
        M=eye_frame(i)
        for k in range(11):
            t=k/10; x=-0.03+0.06*t; z=0.030*math.sin(math.pi*(0.08+0.84*t))**0.6+0.002
            p=M@V((x,-EYE_R-0.004,z))
            brush(h,tuple(p),(0.010,0.02,0.0045),-0.0010)
    smooth_mask_np(h,3,0.5,lambda co: np.exp(-((np.abs(co[:,0])-0.056)**2/0.04**2+(co[:,2]-2.19)**2/0.03**2)))
    eye_open(h)
    shade_smooth(h)
    for i,s in enumerate((-1,1)):
        e=ell('hp_eye%d'%s,EYE_C[i],(EYE_R,)*3,rot=(90,0,0),seg=48,ring=32)
        shade_smooth(e)
    return h


# ---- hands ----
ELBOW={-1:V((-0.41,0,1.34)),1:V((0.41,0,1.34))}
WRIST={-1:V((-0.42,-0.025,1.01)),1:V((0.42,-0.025,1.01))}
def hand_frame(s):
    dn=(WRIST[s]-ELBOW[s]).normalized()
    n=V((-s,0,0)); n=(n-dn*n.dot(dn)).normalized()      # palm normal (toward body)
    f=dn.cross(n)                                       # side axis
    if f.y>0: f=-f                                      # thumb side forward (-Y)
    return dn,n,f

def finger_path(base, dn, n, segs, curl, spread_dir):
    pts=[base]; d=(dn+spread_dir).normalized(); p=base
    for L,a in zip(segs,curl):
        ax=d.cross(n).normalized()
        d=(Matrix.Rotation(math.radians(a),3,ax)@d).normalized()
        p=p+d*L; pts.append(p)
    return pts

def build_hand(s):
    kill_prefix('hp_hand%d'%s)
    w=WRIST[s]; dn,n,f=hand_frame(s)
    P=[]
    R=Matrix((f,n,-dn)).transposed()   # local x=f, y=n, z=up
    c=w+dn*0.05+n*0.001
    bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=32,v_segments=20,radius=1)
    for v in bm.verts:
        q=V([math.copysign(abs(x)**(2/2.8),x) for x in v.co])
        wid=0.034+0.007*(1-q.z)/2      # wider at knuckles (z=-1)
        q=V((q.x*wid,q.y*(0.0145 if q.y<0 else 0.0185),q.z*0.05))
        v.co=R@q+c
    P.append(new_obj('hp_hand%d_palm'%s,bm))
    P.append(sweep('hp_hand%d_wrist'%s,[w-dn*0.07,w-dn*0.02,w+dn*0.015],[(0.03,0.026),(0.027,0.021),(0.03,0.019)],seg=24,up=f))
    P.append(ell('hp_hand%d_thenar'%s,tuple(w+dn*0.04-f*0.022+n*0.011),(0.014,0.017,0.026)))
    lens=[(0.033,0.022,0.019),(0.036,0.024,0.02),(0.034,0.023,0.019),(0.027,0.018,0.016)]
    rad=[0.0112,0.0117,0.011,0.0099]
    off=[-0.0285,-0.0095,0.0095,0.027]
    drop=[0.0,0.003,0.001,-0.007]
    curls=[(12,18,12),(15,20,14),(18,22,15),(22,25,17)]
    for k in range(4):
        base=w+dn*(0.088+drop[k])+f*off[k]
        pts=finger_path(base,dn,n,lens[k],curls[k],f*(off[k]*0.6))
        pts=catmull(pts,5)
        r=[rad[k]*(1.0-0.2*i/(len(pts)-1)) for i in range(len(pts))]
        P.append(sweep('hp_hand%d_f%d'%(s,k),[base-dn*0.025]+pts[1:],r,seg=16,up=n))
    tb=w+dn*0.03-f*0.03+n*0.008
    d=(dn*0.8-f*0.3+n*0.5).normalized()
    pts=[tb]; p=tb
    for L,a in ((0.03,0),(0.024,14),(0.02,14)):
        ax=d.cross(n+f*0.5).normalized()
        d=(Matrix.Rotation(math.radians(-a),3,ax)@d).normalized()
        p=p+d*L; pts.append(p)
    pts=catmull(pts,5)
    r=[0.0135*(1-0.22*i/(len(pts)-1)) for i in range(len(pts))]
    P.append(sweep('hp_hand%d_thumb'%s,pts,r,seg=16,up=n))
    h=fuse(P,'hp_Hand%d'%s,0.0015)
    smooth(h,8,0.5)
    shade_smooth(h)
    return h
