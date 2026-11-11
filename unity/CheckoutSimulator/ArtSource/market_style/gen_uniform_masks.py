"""Uniform masks for "Estilo do mercado": R = main garment, G = detail, from colour keys in OKLab.
Prints each texture's reference colours (median OKLab of the masked texels) for CheckoutMarketStyle.cs."""
import sys, numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, '.')
from oklab import *
B = sys.argv[1]; OUT = sys.argv[2]
# (hue centre deg, hue tolerance, C min, C max, L min, L max); hue None = any (neutral keys)
KEYS = {
    'Staff_Clerk': ('Art/Staff/Models/Staff_Clerk.png', (-94, 28, .03, .2, .16, .43), (26, 18, .09, .3, .33, .68)),
    'Staff_Cleaner': ('Art/Staff/Models/Staff_Cleaner.png', (146, 28, .06, .3, .28, .66), (89, 13, .09, .3, .6, .93)),
    'CheckoutWoman_BaseColor': ('Art/Models/MapModels/CheckoutWoman/CheckoutWoman_BaseColor.png', (-170, 22, .045, .2, .3, .7), (82, 22, .015, .08, .84, .98)),
    'Worker_Baker': ('Art/Characters/Meshy/Workers/Worker_Baker.png', (None, 0, 0, .045, .72, 1.01), (54, 12, .06, .13, .45, .66)),
    'Worker_Butcher': ('Art/Characters/Meshy/Workers/Worker_Butcher.png', (-110, 28, .01, .08, .56, .9), (None, 0, 0, .03, .92, 1.01)),
    'Worker_Fishmonger': ('Art/Characters/Meshy/Workers/Worker_Fishmonger.png', (-112, 22, .045, .2, .28, .66), (None, 0, 0, .03, .92, 1.01)),
}
def sm(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def key(lab, k):
    h0, tol, c0, c1, l0, l1 = k
    L = lab[..., 0]; C = np.hypot(lab[..., 1], lab[..., 2])
    w = sm(l0 - .03, l0 + .01, L) * (1 - sm(l1 - .01, l1 + .03, L)) * sm(c0 - .01, c0 + .005, C) * (1 - sm(c1 - .005, c1 + .01, C))
    if h0 is not None:
        h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1]))
        dh = np.abs((h - h0 + 180) % 360 - 180)
        w = w * (1 - sm(tol * .8, tol * 1.2, dh))
    return w
import json
ALL = {}
for name, (path, km, kd) in KEYS.items():
    im = Image.open(B + path).convert('RGB')
    if im.size[0] > 2048: im = im.resize((2048, 2048), Image.LANCZOS)
    a = np.asarray(im)
    lab = lin_to_oklab(srgb_to_lin(a.reshape(-1, 3))).reshape(a.shape)
    m = key(lab, km); d = key(lab, kd) * (1 - m)
    refs = []
    for w in (m, d):
        sel = lab[w > .5]
        refs.append(np.median(sel, 0) if len(sel) else np.array([0, 0, 0]))
    def soft(x):
        img = Image.fromarray((x * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
        return img.resize((1024, 1024), Image.LANCZOS)
    R, G = soft(m), soft(d)
    Image.merge('RGB', (R, G, Image.new('L', R.size, 0))).save(f'{OUT}/{name}_UniformMask.png', optimize=True)
    ALL[name] = [refs[0].round(4).tolist(), refs[1].round(4).tolist()]
    print(f'{name}: main {(m > .5).mean() * 100:.1f}% ref {refs[0].round(4).tolist()}  detail {(d > .5).mean() * 100:.1f}% ref {refs[1].round(4).tolist()}')
json.dump(ALL, open(f'{OUT}/refs.json', 'w'))
