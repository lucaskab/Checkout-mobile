"""Key the Codex product icons (#00FF00 background) and write the game sizes.

usage: python3 key_icons.py <src_dir> <repo_root> <out_preview_dir> [ids...]
- assets/game-art/products/product-NNN.png   512x512 (product fills the square with a small margin)
- unity/.../Resources/CheckoutDesktop/Products/product-NNN.png  128x128
- unity/.../Restock/product_bounds.json   normalized bbox (Unity texture space, y from bottom)
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

src, repo, prev = sys.argv[1], sys.argv[2], sys.argv[3]
ids = sys.argv[4:]
os.makedirs(prev, exist_ok=True)
ASSET = os.path.join(repo, "assets/game-art/products")
UNITY = os.path.join(repo, "unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Products")
BOUNDS = os.path.join(repo, "unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Restock/product_bounds.json")


def key(img: Image.Image) -> Image.Image:
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    spill = g - np.maximum(r, b)
    strong = spill > 120
    lab, _ = ndimage.label(strong)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    # enclosed holes (a jug handle, gaps between items) count too when they are pure key green
    pure = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if i in border or sl is None:
            continue
        comp = lab[sl] == i
        if comp.sum() >= 30 and spill[sl][comp].mean() > 200:
            pure.append(i)
    bg = np.isin(lab, list(border) + pure)
    # edge band: pixels within 4 px of the background get a soft alpha from the spill
    near = ndimage.binary_dilation(bg, iterations=4) & ~bg
    alpha = np.ones_like(r)
    alpha[bg] = 0.0
    soft = np.clip(1.0 - (spill - 25.0) / (200.0 - 25.0), 0.0, 1.0)
    alpha[near] = soft[near]
    # unmix the key colour from edge pixels, then kill the remaining green spill there
    k = np.array([0.0, 255.0, 0.0])
    out = a.copy()
    m = near & (alpha > 0.02)
    am = alpha[m][:, None]
    out[m] = np.clip((a[m] - (1 - am) * k) / am, 0, 255)
    mx = np.maximum(out[..., 0], out[..., 2])
    gfix = np.minimum(out[..., 1], mx + 18)
    out[..., 1] = np.where(near, gfix, out[..., 1])
    alpha = ndimage.gaussian_filter(alpha, 0.6) * (alpha > 0) + (alpha >= 1) * 0  # tiny smoothing of the cut
    alpha = np.clip(alpha, 0, 1)
    alpha[bg] = 0
    rgba = np.dstack([out, alpha * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def fit(img: Image.Image, size: int, margin: float) -> Image.Image:
    bbox = img.split()[3].point(lambda v: 255 if v > 10 else 0).getbbox()
    crop = img.crop(bbox)
    inner = int(size * (1 - 2 * margin))
    s = inner / max(crop.width, crop.height)
    w, h = max(1, round(crop.width * s)), max(1, round(crop.height * s))
    # resize in premultiplied space to avoid dark/green halos
    arr = np.asarray(crop).astype(np.float32) / 255
    pre = arr.copy()
    pre[..., :3] *= pre[..., 3:4]
    big = Image.fromarray((pre * 255).astype(np.uint8), "RGBA").resize((w, h), Image.LANCZOS)
    b = np.asarray(big).astype(np.float32) / 255
    a = b[..., 3:4]
    rgb = np.where(a > 0, b[..., :3] / np.maximum(a, 1e-4), 0)
    res = Image.fromarray((np.dstack([np.clip(rgb, 0, 1), a]) * 255).astype(np.uint8), "RGBA")
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(res, ((size - w) // 2, (size - h) // 2), res)
    return canvas


bounds = json.load(open(BOUNDS))
by_id = {x["id"]: x for x in bounds["items"]}
for sid in ids:
    n = int(sid)
    keyed = key(Image.open(os.path.join(src, f"product-{n:03d}.png")))
    keyed.save(os.path.join(prev, f"keyed-{n:03d}.png"))
    fit(keyed, 512, 0.06).save(os.path.join(ASSET, f"product-{n:03d}.png"), optimize=True)
    small = fit(keyed, 128, 0.04)
    small.save(os.path.join(UNITY, f"product-{n:03d}.png"), optimize=True)
    x0, y0, x1, y1 = small.split()[3].point(lambda v: 255 if v > 0 else 0).getbbox()
    H = W = 128
    by_id[n] = {"id": n, "x0": x0 / W, "y0": (H - y1) / H, "x1": x1 / W, "y1": (H - y0) / H}
    print("ok", n)
bounds["items"] = [by_id[k] for k in sorted(by_id)]
json.dump(bounds, open(BOUNDS, "w"))
