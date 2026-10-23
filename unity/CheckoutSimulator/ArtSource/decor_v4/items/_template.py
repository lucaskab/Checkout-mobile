"""<id>: one-line description. Footprint half X x Z, height <= H (from Unity DecorSize).
Template for ArtSource/decor_v4 items. Copy to items/<id>.py, then run:
    "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python dv4_run.py -- <id>
Model in Blender space: metres, Z up, origin at the floor centre, the customer side (front) faces +Y.
"""
import math
import dv4
from dv4 import RNG

CONFIG = {"floor": "F4EFE4", "seed": 1}     # floor colour of the preview renders (also used for the old-model render), RNG seed


def build():
    dv4.FINISH.update(ao=.62, ao_dist=.25, light=.34)      # baked AO strength / distance, top-light strength (tune per asset)
    # paints = procedural materials that get BAKED into the single atlas (see dv4.paint_* for the recipes)
    wood = dv4.paint_wood("Wood", along="X")
    iron = dv4.paint_iron("Iron")
    # parts: every helper creates a Blender object that carries its paint and its output node (out="Body" by default).
    dv4.cube("Top", (1.0, .5, .04), loc=(0, 0, .72), paint=wood, bevel=.008, segs=2)
    for x in (-.45, .45):
        dv4.tube("Leg%s" % x, [(x, .2, 0), (x, .2, .7), (x, -.2, .7), (x, -.2, 0)], radius=.02, res=8, paint=iron, resolution=4)
    # moving parts: out="Anim Sway" | "Anim Bob" | "Anim Spin" | "Anim Blink" | "Anim Scroll" (+ ".001" for more), pivot = origin
    sway = "Anim Sway"; dv4.pivot(sway, (0, 0, .74))
    leaf = dv4.paint_leaf("Leaf")
    dv4.leaf("Leaf", .2, .14, loc=(0, 0, .74), rot=(40, 0, 0), paint=leaf, out=sway, shape="heart")
    # flat / glowing / glass slots that must NOT be baked: mat_override="C_RRGGBB" | "E_RRGGBB" | "G_Glass"
    dv4.sphere("Bulb", .03, loc=(0, 0, 1.0), paint=None, mat_override="E_FFE9B0")
    # modifiers on any part: dv4.mod_bevel / mod_subsurf / mod_solidify / mod_displace / mod_mirror / mod_array / mod_simple_deform
    return {"name": "MyItem", "tex": 1024, "budget": 6000, "floor": "F4EFE4"}   # -> T_IK_D4_MyItem / IK_D4_MyItem_albedo.png
