"""Copies the kitchen renders (ArtSource/Review/kitchen/kt_*.png) into the game as UI art:
props trimmed to their content and fitted in 512 px, benches as they are (1600 x 900).
Usage: python kitchen_art_post.py [src] [dst] [meta template]"""
import os, sys, uuid
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "Review", "kitchen")
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "Assets", "Resources", "CheckoutDesktop", "Game")
META = sys.argv[3] if len(sys.argv) > 3 else os.path.join(DST, "truck_back.png.meta")
only = sys.argv[4:]

template = open(META).read().splitlines()
for name in sorted(os.listdir(SRC)):
    if not (name.startswith("kt_") and name.endswith(".png")):
        continue
    if only and name[:-4] not in only:
        continue
    im = Image.open(os.path.join(SRC, name)).convert("RGBA")
    if not name.startswith("kt_bench_"):
        box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        im = im.crop(box)
        scale = 500 / max(im.width, im.height)
        if scale < 1:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        out = Image.new("RGBA", (im.width + 12, im.height + 12), (0, 0, 0, 0))
        out.alpha_composite(im, (6, 6))
        im = out
    path = os.path.join(DST, name)
    im.save(path, optimize=True)
    if not os.path.exists(path + ".meta"):
        lines = ["guid: " + uuid.uuid4().hex if l.startswith("guid:") else l for l in template]
        open(path + ".meta", "w", newline="\n").write("\n".join(lines) + "\n")
    print(name, im.size)
