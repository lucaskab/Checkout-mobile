"""Paint masks of the baked era atlases for "Cores do mercado" (CheckoutMarketPaint / MarketPaint.cginc).

The stall models (Resources/CheckoutEras/Era*_BaseColor.png) are baked into one atlas each, so navy and gold sit next
to wood, produce and cream in the same texture. A colour key in the shader alone speckled (painted gold vs lemons,
honey wood and ochre). Here every texel near the navy / gold hues is grouped into connected regions, and a region is
kept only when its median colour is the brand colour (navy: hue 264 ±13, dark; gold: hue 84 ±4.5, saturated, light).
Output: Resources/CheckoutPaint/<Era>_PaintMask.png (R = navy → cor principal, G = gold → cor de destaque), 1024².

Run after re-baking an era model:  python3 scripts/textures/era_paint_masks.py [Era0_Mesinha ...]
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2] / "unity" / "CheckoutSimulator" / "Assets" / "Resources"
ERAS = ["Era0_Mesinha", "Era1_Tenda", "Era2_Banca", "Era3_Conteiner", "Era4_Spati", "Era5_Quitanda", "Era6_Minimercado"]

# OKLab (Björn Ottosson), linear sRGB in.
def srgb_to_lin(c):
    c=np.asarray(c,dtype=np.float64)
    return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def lin_to_srgb(c):
    c=np.clip(c,0,1); return np.where(c<=0.0031308,c*12.92,1.055*c**(1/2.4)-0.055)
M1=np.array([[0.4122214708,0.5363325363,0.0514459929],[0.2119034982,0.6806995451,0.1073969566],[0.0883024619,0.2817188376,0.6299787005]])
M2=np.array([[0.2104542553,0.7936177850,-0.0040720468],[1.9779984951,-2.4285922050,0.4505937099],[0.0259040371,0.7827717662,-0.8086757660]])
def lin_to_oklab(c):
    lms=c@M1.T; lms=np.cbrt(np.maximum(lms,0)); return lms@M2.T
def oklab_to_lin(l):
    lms=l@np.linalg.inv(M2).T; return (lms**3)@np.linalg.inv(M1).T
def hex2lin(h): return srgb_to_lin(np.array([int(h[i:i+2],16)/255 for i in (0,2,4)]))
def lch(h):
    L=lin_to_oklab(hex2lin(h)); return L[0],np.hypot(L[1],L[2]),np.degrees(np.arctan2(L[2],L[1]))%360

NAVY_H,GOLD_H=264.,84.2
def hd(h,c): d=np.abs(h-c)%360; return np.minimum(d,360-d)
def make(src,dst,preview=None,size=1024):
    im=np.asarray(Image.open(src).convert('RGB'))/255.
    lab=lin_to_oklab(srgb_to_lin(im)); L=lab[...,0]; C=np.hypot(lab[...,1],lab[...,2]); h=np.degrees(np.arctan2(lab[...,2],lab[...,1]))%360
    navyW=(hd(h,NAVY_H)<26)&(C>.02)&(L>.07)&(L<.62)
    goldW=(hd(h,GOLD_H)<15)&(C>.075)&(L>.5)&(L<.93)
    out=np.zeros(im.shape[:2]+(2,),np.float32); stats=[]
    for ch,(wide,ok) in enumerate([(navyW,lambda l,c,hh: hd(hh,NAVY_H)<13 and l<.52 and c>.035),(goldW,lambda l,c,hh: hd(hh,GOLD_H)<4.5 and c>.108 and l>.655)]):
        lab_,n=ndimage.label(ndimage.binary_closing(wide,iterations=1)&wide)
        if n==0: continue
        idx=np.arange(1,n+1)
        mL=ndimage.median(L,lab_,idx); a=ndimage.median(lab[...,1],lab_,idx); b=ndimage.median(lab[...,2],lab_,idx); size_=ndimage.sum(np.ones_like(L),lab_,idx)
        mC=np.hypot(a,b); mh=np.degrees(np.arctan2(b,a))%360
        good=np.array([ok(mL[i],mC[i],mh[i]) and size_[i]>=6 for i in range(n)])
        sel=np.zeros(n+1,bool); sel[1:]=good
        m=sel[lab_]
        stats.append((int(good.sum()),n,float(m.mean())))
        out[...,ch]=m
    # soft 1-texel edge, grow 1 texel inside the wide key (covers bilinear sampling at island borders)
    for ch,wide in ((0,navyW),(1,goldW)):
        grown=ndimage.binary_dilation(out[...,ch]>.5,iterations=2)&(wide|ndimage.binary_dilation(wide,iterations=1))
        out[...,ch]=ndimage.uniform_filter(grown.astype(np.float32),3)
    small=Image.fromarray((np.dstack([out[...,0],out[...,1],np.zeros_like(L)])*255).astype(np.uint8)).resize((size,size),Image.BILINEAR)
    small.save(dst)
    if preview:
        v=im.copy(); v[out[...,0]>.5]=[1,0,1]; v[out[...,1]>.5]=[0,1,0]
        Image.fromarray((np.concatenate([im,v],1)*255).astype(np.uint8)).resize((2048,1024)).save(preview)
    return stats
if __name__ == "__main__":
    for name in sys.argv[1:] or ERAS:
        src = ROOT / "CheckoutEras" / f"{name}_BaseColor.png"
        if not src.exists():
            print("missing", src); continue
        print(name, make(str(src), str(ROOT / "CheckoutPaint" / f"{name}_PaintMask.png")))
