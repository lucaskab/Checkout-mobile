# Prompt for the Codex app: the 7 league division badges

Paste in a new Codex chat in the Checkout project (same model/effort as the product icons). The images come back on a
pure #00FF00 background; `python3 scripts/rankings/key_league_badges.py <dir with the 7 PNGs> .` keys them and
writes `assets/game-art/icons/league-*.png` (512) and the Unity sprites `Resources/CheckoutDesktop/Icons/league-*.png`
(128), the same file names as the placeholders, so the game picks them up with no code change.

---

Create 7 game UI icons, one PNG each, 1024×1024, for the weekly league divisions of a cozy supermarket simulator game.

Style: exactly the painted, glossy, soft 3D-looking cartoon style of the game's existing 2D icons in
`assets/game-art/icons/` (look at medal.png, trophy.png, crown.png, diamond.png, coin.png): chunky rounded shapes,
soft top-left light, gentle highlights, subtle dark outline, no harsh black lines, no photorealism. Front view,
centered, the badge fills ~85% of the square. Background: flat pure green #00FF00 (for keying), no shadow on the
background, no text, no letters, no numbers anywhere.

All 7 share one silhouette family — a rounded heraldic shield/crest with a small ribbon banner at the bottom (banner
left blank) — and get richer as they climb, so a player can tell the rank at a glance even at 48 px:
1. league-bronze.png — warm bronze shield, simple, one small star in the middle, short plain ribbon in navy blue.
2. league-silver.png — polished silver shield with a raised rim, one star, navy ribbon.
3. league-gold.png — shiny gold shield, a star with a laurel wreath around it, navy ribbon.
4. league-sapphire.png — gold rim with a deep blue sapphire gem in the center, two small wings on the sides.
5. league-ruby.png — gold rim with a faceted red ruby, slightly bigger wings, a tiny crown on top.
6. league-emerald.png — gold rim with a green emerald, wings, crown with three points.
7. league-diamond.png — the most special: sparkling white/cyan diamond crystal shield with gold rim, big wings,
   crown with small gems, a few sparkle stars around it.

Keep the game's palette: navy blue (#1F2D5C) and gold (#E6AE34) as the common accents across all 7.
Save the 7 files with exactly those names in `assets/game-art-source/league-codex/`.
