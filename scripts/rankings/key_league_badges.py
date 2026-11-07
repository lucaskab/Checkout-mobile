"""Key the Codex league badges (#00FF00 background) into the game's icon files.

usage: python3 scripts/rankings/key_league_badges.py <src_dir> <repo_root>
Reads league-{bronze,silver,gold,sapphire,ruby,emerald,diamond}.png from <src_dir> (see
codex_league_badges_prompt.md) and writes, with the placeholders' file names:
- assets/game-art/icons/league-*.png                                512x512
- unity/CheckoutSimulator/Assets/Resources/CheckoutDesktop/Icons/league-*.png   128x128
"""
import os
import sys

src, repo = sys.argv[1], sys.argv[2]
# key() and fit() of the product keyer (only its function part: the rest of that script writes product files)
_code = open(os.path.join(repo, "scripts", "art", "key_codex_product_icons.py"), encoding="utf-8").read()
_code = _code[:_code.index("bounds = json.load")]
_code = _code.replace("src, repo, prev = sys.argv[1], sys.argv[2], sys.argv[3]", "src = prev = None; repo = \".\"")
_code = _code.replace("os.makedirs(prev, exist_ok=True)", "")
keyer = type(sys)("keyer")
exec(_code, keyer.__dict__)

from PIL import Image  # noqa: E402

ICONS = os.path.join(repo, "assets", "game-art", "icons")
UNITY = os.path.join(repo, "unity", "CheckoutSimulator", "Assets", "Resources", "CheckoutDesktop", "Icons")
for name in ("bronze", "silver", "gold", "sapphire", "ruby", "emerald", "diamond"):
    path = os.path.join(src, f"league-{name}.png")
    if not os.path.exists(path):
        print("missing", path)
        continue
    keyed = keyer.key(Image.open(path))
    keyer.fit(keyed, 512, .04).save(os.path.join(ICONS, f"league-{name}.png"), optimize=True)
    keyer.fit(keyed, 128, .04).save(os.path.join(UNITY, f"league-{name}.png"), optimize=True)
    print("ok", name)
