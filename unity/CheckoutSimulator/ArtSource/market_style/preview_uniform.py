import sys, numpy as np
from PIL import Image
sys.path.insert(0,'.')
from oklab import *
def oklab_to_lin(lab):
    M1i=np.array([[1,.3963377922,.2158037581],[1,-.1055613423,-.0638541748],[1,-.0894841821,-1.2914855379]])
    M2i=np.array([[4.0767416613,-3.3077115904,.2309699287],[-1.2684380041,2.6097574007,-.3413193963],[-.0041960865,-.7034186145,1.7076147009]])
    lms=(lab@M1i.T)**3; return np.maximum(lms@M2i.T,0)
def lin_to_srgb(c): c=np.clip(c,0,1); return np.where(c<=.0031308,c*12.92,1.055*c**(1/2.4)-.055)
def hexlab(h): return lin_to_oklab(srgb_to_lin(np.array([[int(h[i:i+2],16) for i in (0,2,4)]])))[0]
def um_map(lab, ref, tgt):
    refC=np.hypot(ref[1],ref[2]); C=np.hypot(lab[...,1],lab[...,2])
    ratio=np.clip(C/refC,0,1.5) if refC>.03 else np.ones_like(C)
    tC=np.hypot(tgt[1],tgt[2]); hue=tgt[1:]/max(tC,1e-5)
    k=np.clip(tgt[0]/max(ref[0],1e-3),.35,1)
    L=np.clip(tgt[0]+(lab[...,0]-ref[0])*k,.03,.985)
    return np.stack([L, hue[0]*tC*ratio, hue[1]*tC*ratio],-1)
B='/mnt/user-data/uploads/checkout/unity/CheckoutSimulator/Assets/'
from gen_uniform_masks_refs import PATHS
import json
REFS={k:(np.array(a),np.array(b)) for k,(a,b) in json.load(open('uni/refs.json')).items()}
main,det=hexlab(sys.argv[1]),hexlab(sys.argv[2])
S=512; sheet=Image.new('RGB',(S*3,S*2))
for i,(n,p) in enumerate(PATHS.items()):
    im=np.asarray(Image.open(B+p).convert('RGB').resize((1024,1024)))
    mk=np.asarray(Image.open(f'uni/{n}_UniformMask.png'),np.float32)/255
    lin=srgb_to_lin(im); lab=lin_to_oklab(lin)
    out=lin.copy()
    out=out*(1-mk[...,0:1])+oklab_to_lin(um_map(lab,REFS[n][0],main))*mk[...,0:1]
    out=out*(1-mk[...,1:2])+oklab_to_lin(um_map(lab,REFS[n][1],det))*mk[...,1:2]
    sheet.paste(Image.fromarray((lin_to_srgb(out)*255).astype(np.uint8)).resize((S,S)),(S*(i%3),S*(i//3)))
sheet.save(sys.argv[3])
