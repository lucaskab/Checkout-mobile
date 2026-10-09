"""Trims the lane renders (ArtSource/Review/lane) to their content and writes them as UI art:
Resources/CheckoutDesktop/Game/lane_<name>.png (places 360 px wide, trucks 300 px wide)."""
import os, sys, uuid
from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "Review", "lane")
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "Assets", "Resources", "CheckoutDesktop", "Game")
META = sys.argv[3] if len(sys.argv) > 3 else os.path.join(DST, "truck_back.png.meta")
PLACES = ["fazenda", "laticinio", "frigorifico", "porto", "fabrica", "engarrafadora", "vinicola", "moinho", "distribuidora", "mercado"]
TRUCKS = ["truck", "truck_fish", "truck_ice"]

template = open(META).read().splitlines()
for name in PLACES + TRUCKS:
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    im = im.crop(box)
    width = 300 if name in TRUCKS else 360
    pad = 6
    im = im.resize((width - 2 * pad, round(im.height * (width - 2 * pad) / im.width)), Image.LANCZOS)
    out = Image.new("RGBA", (width, im.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(im, (pad, pad))
    path = os.path.join(DST, "lane_" + name + ".png")
    out.save(path, optimize=True)
    if not os.path.exists(path + ".meta"):
        lines = ["guid: " + uuid.uuid4().hex if l.startswith("guid:") else l for l in template]
        open(path + ".meta", "w", newline="\n").write("\n".join(lines) + "\n")
    print(name, out.size)
