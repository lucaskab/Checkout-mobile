"""Seamless ground of an abandoned lot (Game/lot_dirt.png): packed earth with darker damp patches, loose gravel,
tufts of dry grass, a few cracks and bits of rubble, lit softly from the top left like the rest of the map art.
Shown under every lot that is not the player's yet (CheckoutLotSites.cs) until it is cleared.
Usage: python lot_dirt_tex.py [out.png]   (1024 x 1024, tiles in both directions)"""
import sys
import numpy as np
from PIL import Image, ImageFilter

N = 1024
rng = np.random.default_rng(7)


def periodic_noise(scale, octaves=5, persistence=0.55):
    """Fractal noise that wraps at the edges: random spectrum filtered around a frequency (FFT is periodic)."""
    total = np.zeros((N, N))
    amp, norm = 1.0, 0.0
    fy = np.fft.fftfreq(N)[:, None]
    fx = np.fft.fftfreq(N)[None, :]
    f = np.sqrt(fx * fx + fy * fy) * N
    for o in range(octaves):
        target = scale * (2 ** o)
        spec = np.fft.fft2(rng.standard_normal((N, N)))
        band = np.exp(-((f - target) ** 2) / (2 * (target * 0.5) ** 2))
        layer = np.real(np.fft.ifft2(spec * band))
        layer /= layer.std() + 1e-9
        total += layer * amp
        norm += amp
        amp *= persistence
    total /= norm
    return (total - total.min()) / (total.max() - total.min())


def blobs(count, rmin, rmax):
    """Mask of soft round spots placed with wrap-around (seamless)."""
    m = np.zeros((N, N))
    yy, xx = np.mgrid[0:N, 0:N]
    for _ in range(count):
        cx, cy = rng.uniform(0, N, 2)
        r = rng.uniform(rmin, rmax)
        dx = np.minimum(abs(xx - cx), N - abs(xx - cx))
        dy = np.minimum(abs(yy - cy), N - abs(yy - cy))
        d = np.sqrt(dx * dx + dy * dy) / r
        m = np.maximum(m, np.clip(1 - d, 0, 1))
    return m


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def col(*rgb):
    return np.array(rgb, dtype=float) / 255.0


# Base earth: warm packed dirt with large damp/dry variations.
big = periodic_noise(2, 3)
mid = periodic_noise(6, 3)
fine = periodic_noise(40, 2)
earth_dry = col(176, 138, 98)
earth = col(150, 112, 78)
earth_damp = col(112, 82, 58)
img = lerp(earth_dry, earth, np.clip(big * 1.8 - 0.4, 0, 1))
img = lerp(img, earth_damp, np.clip((mid - 0.62) * 4, 0, 1) * 0.9)
img *= (0.95 + 0.1 * fine)[..., None]

# Tyre/footpath tracks: a couple of faint darker bands that wrap around.
yy, xx = np.mgrid[0:N, 0:N]
for k in range(2):
    phase = rng.uniform(0, 2 * np.pi)
    y0 = rng.uniform(0, N)
    wave = y0 + 40 * np.sin(2 * np.pi * xx / N * 1 + phase)
    d = np.minimum(abs(yy - wave) % N, N - abs(yy - wave) % N)
    band = np.clip(1 - d / 26, 0, 1) * np.clip(periodic_noise(20, 2) * 1.6 - 0.3, 0, 1)
    img = lerp(img, img * 0.8, band * 0.7)

# Cracks in the dry earth: thin dark lines from the ridges of a noise.
ridge = 1 - np.abs(periodic_noise(9, 3) * 2 - 1)
cracks = np.clip((ridge - 0.984) * 50, 0, 1) * np.clip(1.2 - big * 1.6, 0, 1)
img = lerp(img, img * 0.6, cracks)

# Dry grass and weeds in patches.
grass_zone = np.clip((periodic_noise(4, 2) - 0.55) * 3.5, 0, 1)
grass_fine = periodic_noise(110, 2)
grass = np.clip(grass_zone * (grass_fine * 2.2 - 0.6), 0, 1)
img = lerp(img, col(158, 152, 74), grass * 0.9)
img = lerp(img, col(104, 126, 52), np.clip(grass * 1.6 - 0.7, 0, 1) * 0.95)

# Gravel: small light and dark stones scattered everywhere, denser in places.
density = periodic_noise(10, 2)
r = rng.random((N, N))
stones = np.zeros((N, N))
stones[r < 0.0002 + 0.0014 * density ** 3] = 1
stones = np.array(Image.fromarray((stones * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.0))) / 255.0
stones = np.clip(stones * 1.6, 0, 1)
tone = rng.random((N, N))
img = lerp(img, col(196, 184, 166), stones * (tone > 0.35) * 0.9)
img = lerp(img, col(92, 80, 70), stones * (tone <= 0.35) * 0.8)

# A few bits of broken brick and concrete.
rubble = blobs(18, 7, 14) > 0.3
rt = periodic_noise(80, 2)
img = np.where(rubble[..., None], lerp(np.broadcast_to(col(168, 88, 62), img.shape), np.broadcast_to(col(170, 168, 160), img.shape), (rt > 0.5).astype(float)) * (0.85 + 0.25 * rt)[..., None], img)

# Soft relief light from the top left (height = big shapes + stones + rubble).
h = mid * 0.3 + fine * 0.08 + stones * 0.9 + rubble * 1.0 - cracks * 0.5
gy, gx = np.gradient(h)
light = np.clip(1 + (-gx - gy) * 5, 0.7, 1.3)
img *= light[..., None]

out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB")
out.save(sys.argv[1] if len(sys.argv) > 1 else "lot_dirt.png", optimize=True)
print("ok", out.size)
