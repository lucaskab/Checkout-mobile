"""Rede de supermercados — turn Codex's key-colour art into game files.

usage: python3 scripts/art/rede_art.py <codex_dir> <repo_root> <preview_dir>
  <codex_dir> holds Codex's output (assets/game-art-source/rede/...): emblems/, products/, ui/, map/.

Codex paints with mask colours on #00FF00 (claude/rede-supermercados-proposta.md):
  * emblems: flat magenta (main colour), cyan (accent), white (highlights)
  * private-label products / branch stores: the brand parts in magenta tones (shading kept), a flat cyan circle where
    the logo goes.
Outputs (Unity: Resources/CheckoutDesktop/...):
  * Rede/Emblems/<id>.png    512 RGBA mask: R = main colour, G = accent, B = white, A = coverage. CheckoutBrand tints it.
  * Products/product-NNN.png 128 classic look (navy band, the basket logo) + assets/game-art/products 512 copy;
    Rede/Tint/product-NNN.png 128 RGBA: R = band shading, G = band, B = logo circle, A = coverage;
    Restock/product_bounds.json updated; Rede/logo_spots.json = the circle of each picture (normalized, y from top).
  * Rede/<name>.png for the UI art and the branch stores (same tint files for the stores), Rede/mapa-cidade.jpg.
"""
import colorsys
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

CLASSIC_PRIMARY = (0x1D, 0x2B, 0x4F)
CLASSIC_ACCENT = (0xD3, 0xA5, 0x3D)
EMBLEMS = ["cesta", "carrinho", "folha", "estrela", "coroa", "sol", "coracao", "sacola", "maca", "trigo", "toldo", "diamante"]
PRODUCTS = {172: "arroz", 173: "feijao", 174: "cafe", 175: "leite", 176: "biscoito", 177: "detergente", 178: "papel-higienico", 179: "macarrao"}
BRANCHES = ["centro", "praia", "universitario", "nobre", "vila"]


def key_green(img: Image.Image) -> np.ndarray:
    """Float RGBA 0..1 with the #00FF00 background removed (border-connected + enclosed pure-green holes), green
    unmixed from the edges (same approach as scripts/art/key_codex_product_icons.py)."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    spill = g - np.maximum(r, b)
    lab, _ = ndimage.label(spill > 120)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    pure = [i for i, sl in enumerate(ndimage.find_objects(lab), start=1)
            if i not in border and sl is not None and (lab[sl] == i).sum() >= 30 and spill[sl][lab[sl] == i].mean() > 200]
    bg = np.isin(lab, list(border) + pure)
    near = ndimage.binary_dilation(bg, iterations=4) & ~bg
    alpha = np.ones_like(r)
    alpha[bg] = 0
    soft = np.clip(1 - (spill - 25) / 175, 0, 1)
    alpha[near] = soft[near]
    out = a.copy()
    m = near & (alpha > .02)
    am = alpha[m][:, None]
    out[m] = np.clip((a[m] - (1 - am) * np.array([0, 255, 0])) / am, 0, 255)
    out[..., 1] = np.where(near, np.minimum(out[..., 1], np.maximum(out[..., 0], out[..., 2]) + 18), out[..., 1])
    alpha = np.clip(ndimage.gaussian_filter(alpha, .6) * (alpha > 0), 0, 1)
    alpha[bg] = 0
    return np.dstack([out / 255, alpha])


def crop_fit(rgba: np.ndarray, size: int, margin: float):
    """Crops to the coverage and fits it centred in a square (premultiplied resize). Returns the array and the
    transform (scale, offset) from source pixels to the output, to move spots along."""
    ys, xs = np.where(rgba[..., 3] > .04)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop = rgba[y0:y1, x0:x1]
    inner = size * (1 - 2 * margin)
    s = inner / max(crop.shape[0], crop.shape[1])
    w, h = max(1, round(crop.shape[1] * s)), max(1, round(crop.shape[0] * s))
    pre = crop.copy()
    pre[..., :3] *= pre[..., 3:4]
    chans = [np.asarray(Image.fromarray((pre[..., k] * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)).astype(np.float32) / 255 for k in range(pre.shape[2])]
    res = np.dstack(chans)
    al = res[..., 3:4]
    res[..., :3] = np.where(al > 0, res[..., :3] / np.maximum(al, 1e-4), 0)
    out = np.zeros((size, size, rgba.shape[2]), np.float32)
    ox, oy = (size - w) // 2, (size - h) // 2
    out[oy:oy + h, ox:ox + w] = res
    return out, (s, x0, y0, ox, oy)


def save(arr: np.ndarray, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGBA" if arr.shape[2] == 4 else "RGB").save(path, optimize=True)


# ------------------------------------------------------------------------------------------------ emblems
def emblem_mask(src: str) -> np.ndarray:
    """RGBA mask of a flat three-colour emblem: solve c = a·magenta + b·cyan + w·white per pixel."""
    rgba = key_green(Image.open(src))
    R, G, B, A = (rgba[..., k] for k in range(4))
    w = np.clip(R + G - B, 0, 1)
    a = np.clip(B - G, 0, 1)
    b = np.clip(B - R, 0, 1)
    tot = np.maximum(a + b + w, 1e-4)
    return np.dstack([a / tot, b / tot, w / tot, A])


def tint_emblem(mask: np.ndarray, primary, accent) -> np.ndarray:
    p, c = np.array(primary) / 255, np.array(accent) / 255
    rgb = mask[..., 0:1] * p + mask[..., 1:2] * c + mask[..., 2:3] * np.ones(3)
    return np.dstack([rgb, mask[..., 3]])


# ------------------------------------------------------------------------------------------------ painted art with brand parts
def brand_parts(rgba: np.ndarray):
    """Magenta-toned parts (soft mask + their shading) and the flat cyan logo circle of a painted picture."""
    rgb = rgba[..., :3]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-4), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # hue in degrees
    hue = np.zeros_like(mx)
    d = np.maximum(mx - mn, 1e-4)
    hue = np.where(mx == r, (60 * ((g - b) / d) + 360) % 360, hue)
    hue = np.where(mx == g, 60 * ((b - r) / d) + 120, hue)
    hue = np.where(mx == b, 60 * ((r - g) / d) + 240, hue)
    magenta = (hue >= 280) & (hue <= 352) & (sat > .28) & (mx > .12)
    band = ndimage.gaussian_filter(magenta.astype(np.float32), .7) * np.clip((sat - .2) / .25, 0, 1)
    band *= rgba[..., 3]
    cyan = (np.abs(hue - 180) < 22) & (sat > .55) & (mx > .5)
    cyan = ndimage.binary_opening(cyan, iterations=2)
    lab, n = ndimage.label(cyan)
    spot = None
    if n:
        sizes = ndimage.sum(cyan, lab, range(1, n + 1))
        k = int(np.argmax(sizes)) + 1
        circ = lab == k
        ys, xs = np.where(circ)
        cy, cx = ys.mean(), xs.mean()
        rad = np.sqrt(circ.sum() / np.pi)
        spot = (cx, cy, rad)
        cyan = ndimage.binary_dilation(circ, iterations=2)
    shade = mx  # value of the magenta paint: dark folds stay dark in any colour
    if band.sum() > 0:
        ref = np.percentile(shade[band > .5], 80) if (band > .5).any() else 1
        shade = np.clip(shade / max(ref, 1e-3), 0, 1.2) / 1.2
    return band, shade, cyan.astype(np.float32), spot


def recolour(rgba: np.ndarray, band, shade, primary) -> np.ndarray:
    out = rgba.copy()
    p = np.array(primary) / 255
    # lift the dark navy a little in the light so the folds read (shade 1 → a bit lighter than the colour)
    col = np.clip(p[None, None, :] * (0.55 + 0.75 * shade[..., None]), 0, 1)
    out[..., :3] = rgba[..., :3] * (1 - band[..., None]) + col * band[..., None]
    return out


def paint_logo(rgba: np.ndarray, spot, emblem: np.ndarray, primary, accent) -> np.ndarray:
    """White plate on the cyan circle with the emblem on it."""
    if not spot:
        return rgba
    out = rgba.copy()
    cx, cy, rad = spot
    H, W = rgba.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    plate = np.clip(rad + 2.5 - dist, 0, 1)
    cream = np.array([0xFB, 0xF8, 0xF1]) / 255
    out[..., :3] = out[..., :3] * (1 - plate[..., None]) + cream * plate[..., None]
    size = max(4, int(rad * 1.5))
    tinted = tint_emblem(emblem, primary, accent)
    img = Image.fromarray((tinted * 255).astype(np.uint8), "RGBA").resize((size, size), Image.LANCZOS)
    e = np.asarray(img).astype(np.float32) / 255
    x0, y0 = int(round(cx - size / 2)), int(round(cy - size / 2))
    xs0, ys0 = max(0, x0), max(0, y0)
    xs1, ys1 = min(W, x0 + size), min(H, y0 + size)
    sub = e[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    a = sub[..., 3:4]
    out[ys0:ys1, xs0:xs1, :3] = out[ys0:ys1, xs0:xs1, :3] * (1 - a) + sub[..., :3] * a
    return out


def process_brand_art(src: str, size: int, margin: float, emblem: np.ndarray):
    """(classic picture, tint file, logo spot normalized) for a painted picture with brand parts."""
    rgba = key_green(Image.open(src))
    band, shade, circle, spot = brand_parts(rgba)
    stack = np.dstack([rgba, band, shade, circle])
    fitted, (s, x0, y0, ox, oy) = crop_fit(stack, size, margin)
    pic = fitted[..., :4]
    band_f, shade_f, circ_f = fitted[..., 4], fitted[..., 5], fitted[..., 6]
    spot_f = None
    if spot:
        cx, cy, rad = spot
        spot_f = ((cx - x0) * s + ox, (cy - y0) * s + oy, rad * s)
    classic = paint_logo(recolour(pic, band_f, shade_f, CLASSIC_PRIMARY), spot_f, emblem, CLASSIC_PRIMARY, CLASSIC_ACCENT)
    tint = np.dstack([shade_f * band_f, band_f, circ_f, pic[..., 3]])
    norm = None
    if spot_f:
        norm = {"x": round(spot_f[0] / size, 4), "y": round(spot_f[1] / size, 4), "r": round(spot_f[2] / size, 4)}
    return classic, tint, norm, pic


def main():
    src, repo, prev = sys.argv[1], sys.argv[2], sys.argv[3]
    unity = os.path.join(repo, "unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop")
    os.makedirs(prev, exist_ok=True)
    masks = {}
    for i, name in enumerate(EMBLEMS, start=1):
        path = os.path.join(src, "emblems", f"{i:02d}-{name}.png")
        m = emblem_mask(path)
        fitted, _ = crop_fit(m, 512, .04)
        masks[name] = fitted
        save(fitted, os.path.join(unity, "Rede/Emblems", f"{name}.png"))
        save(tint_emblem(fitted, CLASSIC_PRIMARY, CLASSIC_ACCENT), os.path.join(prev, f"emblem-{name}.png"))
        print("emblem", name)
    spots = {}
    bounds_path = os.path.join(unity, "Restock/product_bounds.json")
    bounds = json.load(open(bounds_path))
    by_id = {x["id"]: x for x in bounds["items"]}
    for pid, name in PRODUCTS.items():
        path = os.path.join(src, "products", f"{pid}-{name}.png")
        if not os.path.exists(path):
            print("missing", path)
            continue
        big, _, _, _ = process_brand_art(path, 512, .06, masks["cesta"])
        save(big, os.path.join(repo, "assets/game-art/products", f"product-{pid}.png"))
        small, tint, spot, _ = process_brand_art(path, 128, .04, masks["cesta"])
        save(small, os.path.join(unity, "Products", f"product-{pid}.png"))
        save(tint, os.path.join(unity, "Rede/Tint", f"product-{pid}.png"))
        spots[f"product-{pid}"] = spot
        al = small[..., 3] > 0
        ys, xs = np.where(al)
        by_id[pid] = {"id": pid, "x0": xs.min() / 128, "y0": (128 - (ys.max() + 1)) / 128, "x1": (xs.max() + 1) / 128, "y1": (128 - ys.min()) / 128}
        save(big, os.path.join(prev, f"product-{pid}.png"))
        print("product", pid)
    bounds["items"] = [by_id[k] for k in sorted(by_id)]
    json.dump(bounds, open(bounds_path, "w"))
    # UI art and clients: plain keyed pictures
    ui_dir = os.path.join(src, "ui")
    if os.path.isdir(ui_dir):
        for f in sorted(os.listdir(ui_dir)):
            if not f.endswith(".png"):
                continue
            fitted, _ = crop_fit(key_green(Image.open(os.path.join(ui_dir, f))), 256, .04)
            save(fitted, os.path.join(unity, "Rede", f))
            save(fitted, os.path.join(prev, f))
            print("ui", f)
    map_dir = os.path.join(src, "map")
    for b in BRANCHES:
        path = os.path.join(map_dir, f"filial-{b}.png")
        if not os.path.exists(path):
            continue
        classic, tint, spot, _ = process_brand_art(path, 384, .03, masks["cesta"])
        save(classic, os.path.join(unity, "Rede", f"filial-{b}.png"))
        save(tint, os.path.join(unity, "Rede/Tint", f"filial-{b}.png"))
        spots[f"filial-{b}"] = spot
        save(classic, os.path.join(prev, f"filial-{b}.png"))
        print("branch", b)
    mp = os.path.join(map_dir, "mapa-cidade.png")
    if os.path.exists(mp):
        im = Image.open(mp).convert("RGB")
        im.thumbnail((1600, 1200), Image.LANCZOS)
        im.save(os.path.join(unity, "Rede", "mapa-cidade.jpg"), quality=86)
        im.save(os.path.join(prev, "mapa-cidade.jpg"), quality=80)
        print("map")
    os.makedirs(os.path.join(unity, "Rede"), exist_ok=True)
    old = {}
    sp = os.path.join(unity, "Rede/logo_spots.json")
    if os.path.exists(sp):
        old = {x["name"]: x for x in json.load(open(sp)).get("items", [])}
    for k, v in spots.items():
        if v:
            old[k] = {"name": k, **v}
    json.dump({"items": list(old.values())}, open(sp, "w"), indent=1)


if __name__ == "__main__":
    main()
