# Fixture tiers: Unity exports

One FBX per approved tier, written by `export_all()` in `scripts/blender/fixture_tiers.py` from
`ArtSource/fixture_tiers/fixture_tiers.blend`. Approved by Lucas on 30/10. The special sectors are **not** here; they are being redone.

## Convention (same as the kit models, `rk_core.export`)
- **Units:** metres, scale 1 (`FBX_SCALE_ALL`), FBX axis -Z forward / Y up. Import with `bakeAxisConversion = false`
  (as `CheckoutInteriorKitBuilder.KitModel` does); the root keeps Blender's axis conversion.
- **Facing:** the customer side faces **Unity -Z**, the back +Z, like every other kit piece.
- **Pivot:** the centre of the build footprint, on the floor (y = 0). Some parts overhang the footprint a little
  (handles, the cold room's condensers and dock); see the bounds column.
- **Children:** `Body` (the fixture) and `Anim Fill 0..3` (stock, in quarters along the run) where the fixture has stock,
  the same names `KitModel` already looks for. Produce T1–T3 have no `Anim Fill 1`.
- **Normals:** flat-shaded (`mesh_smooth_type OFF`, as the kit), no tangents, no colliders, no animation.

## Materials (one slot per material name; the names drive `KitRemap`)
| Name | What it is | "Cores do mercado" |
|---|---|---|
| `C_1D2B4F_Navy` | navy structure | **repaint (navy)** |
| `T_IK_V2_PaintNavy` | navy painted panels (texture is in `WholeNavy`) | **repaint (navy)** |
| `C_2E4A7D_Blue`, `C_2B3A55_Blue` | secondary navy (trims, cold room panels) | repaint as navy family, if you want |
| `C_D3A53D_Gold` | thin gold trims | **repaint (gold)** |
| `C_F4EBD8_Cream`, `C_F6E7C8_Cream`, `C_D9CFB8_Cream`, `T_IK_V2_PaintCream` | cream | keep |
| `C_FBF8F1_White`, `C_E3E8E4_White` | white | keep |
| `C_DCE3E8_Metal`, `C_C9D2D6_Metal`, `C_BFC5C9_Metal`, `C_EAF6FB_Metal`, `C_3A4450_Metal`, `T_IK_R_Brushed` | chrome / steel | keep |
| `C_232A33_Dark`, `C_2F3A40_Dark` | black rubber, dark plastic | keep |
| `C_6B4128_Wood`, `C_C9A06A_Wood`, `T_IK_R_Wood`, `T_IK_R_WoodDark`, `T_IK_R_Planks`, `T_IK_WoodLight`, `T_IK_Crate` | wood | keep |
| `C_<hex>_Product`, `T_FT_Labels`, `T_IK_Crust`, `T_IK_Cheese`, `T_IK_Meat`, `T_IK_Waffle`, … | products and stock | keep |
| `G_Glass` | glass | keep |
| `E_<hex>` | glow (LED strips, screens, lit headers) | keep |

- `C_RRGGBB_<Role>` keeps the kit contract: `KitRemap` reads the hex from characters 2..8, so these import
  today without changes. All `C_` names currently map to `IK_P_<hex>`, so a product that is navy or gold (some
  packaging is) would follow the market colour. To stop that, make `KitRemap` give `_Product`, `_Wood`, `_Cream` and
  similar roles a material whose name contains `Products` (already in `CheckoutMarketPaint.NotPaint`), for example
  `Painted("IK_PProducts_" + hex, hex, null, Vector2.one, .35f)`.
- Every object inside an `Anim Fill` is a product, so all its flat colours are `_Product`.
- **Textures:** every `T_IK_*` texture already exists in `Assets/Art/Interior/Textures/<name>_albedo.png`. The one
  new texture is `textures/FT_Labels_albedo.png` (`T_FT_Labels`, the blank product-label atlas, no text). Copy it to
  `Assets/Art/Interior/Textures/`. `KitTexture` caps it at 1024 unless its name contains `IK_Labels`, and 1024 is fine.
- Materials per tier go up to ~27 (drinks T3), which means that many draw calls per fixture unless they are merged or
  atlased. Fine for the first pass; worth an atlas later.

## Files
Footprint = build-mode cells in metres (width × depth). Bounds = mesh extent: width (x) × depth (z) × height (y),
then x range / z range relative to the pivot. Customers stand on -z.

| File | Name (pt-BR) | Footprint | Bounds W × D × H | x / z range | Tris | Children |
|---|---|---|---|---|---|---|
| `shelf_T1.fbx` | Estante de madeira | 1.00 × 0.50 | 0.99 × 0.46 × 1.71 | -0.49..0.49 / -0.21..0.24 | 5,882 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `shelf_T2.fbx` | Estante grande de madeira | 1.50 × 0.50 | 1.50 × 0.46 × 1.97 | -0.75..0.75 / -0.21..0.25 | 10,320 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `shelf_T3.fbx` | Gôndola de metal | 2.00 × 0.75 | 1.99 × 0.74 × 2.23 | -0.99..0.99 / -0.36..0.39 | 14,564 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `shelf_T4.fbx` | Gôndola iluminada | 2.50 × 1.00 | 2.50 × 1.06 × 2.42 | -1.25..1.25 / -0.53..0.53 | 30,500 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `checkout_T1.fbx` | Caixinha no balcão | 1.25 × 1.25 | 1.29 × 1.12 × 1.23 | -0.65..0.65 / -0.63..0.49 | 4,670 | Body |
| `checkout_T2.fbx` | Caixa registradora | 1.75 × 1.50 | 1.80 × 1.29 × 1.31 | -0.90..0.90 / -0.79..0.50 | 6,900 | Anim Fill 0, Body |
| `checkout_T3.fbx` | Caixa com esteira | 2.50 × 1.75 | 2.55 × 1.90 × 2.12 | -1.28..1.27 / -1.32..0.58 | 4,028 | Anim Fill 0, Body |
| `checkout_T4.fbx` | Caixa premium | 3.00 × 1.75 | 3.05 × 1.51 × 2.26 | -1.53..1.52 / -0.92..0.59 | 6,834 | Anim Fill 0, Body |
| `drinks_T1.fbx` | Geladeira de 1 porta | 0.75 × 0.75 | 0.70 × 0.72 × 1.85 | -0.35..0.35 / -0.38..0.34 | 7,532 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `drinks_T2.fbx` | Geladeira de 2 portas | 1.25 × 0.75 | 1.21 × 0.74 × 1.95 | -0.60..0.60 / -0.39..0.35 | 13,816 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `drinks_T3.fbx` | Geladeira de 3 portas | 2.00 × 0.75 | 1.98 × 0.76 × 2.05 | -0.99..0.99 / -0.40..0.36 | 23,244 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `drinks_T4.fbx` | Parede de portas com LED | 2.50 × 1.00 | 2.52 × 1.02 × 2.22 | -1.26..1.26 / -0.52..0.50 | 29,720 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `dairy_T1.fbx` | Expositor refrigerado pequeno | 1.00 × 0.75 | 1.00 × 0.74 × 1.32 | -0.50..0.50 / -0.37..0.37 | 3,988 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `dairy_T2.fbx` | Balcão refrigerado | 1.50 × 0.75 | 1.48 × 0.74 × 1.32 | -0.74..0.74 / -0.38..0.36 | 2,172 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `dairy_T3.fbx` | Expositor aberto (multideck) | 2.00 × 1.00 | 1.98 × 0.99 × 2.00 | -0.99..0.99 / -0.51..0.48 | 17,152 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `dairy_T4.fbx` | Ilha de laticínios e frios | 2.50 × 1.00 | 2.46 × 1.01 × 2.13 | -1.23..1.23 / -0.51..0.51 | 16,820 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `freezer_T1.fbx` | Freezer horizontal pequeno | 1.00 × 0.75 | 1.00 × 0.76 × 0.93 | -0.50..0.50 / -0.38..0.38 | 2,940 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Body |
| `freezer_T2.fbx` | Freezer horizontal grande | 1.50 × 0.75 | 1.55 × 0.78 × 0.95 | -0.75..0.80 / -0.39..0.39 | 3,252 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `freezer_T3.fbx` | Freezer vertical de 2 portas | 1.50 × 0.90 | 1.48 × 0.90 × 2.05 | -0.74..0.74 / -0.47..0.43 | 5,212 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `freezer_T4.fbx` | Ilha de congelados | 2.50 × 1.25 | 2.50 × 1.27 × 1.71 | -1.25..1.25 / -0.62..0.66 | 8,260 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `icecream_T1.fbx` | Freezer de sorvetes | 1.00 × 0.75 | 1.00 × 0.77 × 0.94 | -0.50..0.50 / -0.39..0.38 | 3,045 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Body |
| `icecream_T2.fbx` | Freezer de sorvetes grande | 1.50 × 0.75 | 1.51 × 0.79 × 0.97 | -0.75..0.76 / -0.40..0.39 | 3,782 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `icecream_T3.fbx` | Ilha de sorvetes | 2.00 × 1.00 | 2.00 × 1.03 × 1.00 | -1.00..1.00 / -0.51..0.51 | 4,474 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `icecream_T4.fbx` | Vitrine de gelato | 2.50 × 1.00 | 2.48 × 0.98 × 1.58 | -1.24..1.24 / -0.50..0.48 | 4,340 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `bakery_T1.fbx` | Estante de pães | 1.00 × 0.50 | 0.99 × 0.48 × 1.70 | -0.49..0.49 / -0.22..0.26 | 3,064 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `bakery_T2.fbx` | Estante de cestos inclinados | 1.50 × 0.50 | 1.50 × 0.48 × 1.97 | -0.75..0.75 / -0.22..0.26 | 7,258 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `bakery_T3.fbx` | Vitrine de acrílico | 2.00 × 0.75 | 1.98 × 0.73 × 2.12 | -0.99..0.99 / -0.37..0.36 | 8,518 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `bakery_T4.fbx` | Vitrine aquecida iluminada | 2.00 × 1.00 | 1.99 × 0.98 × 1.89 | -0.99..0.99 / -0.50..0.48 | 7,764 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `produce_T1.fbx` | Banca de caixotes | 1.00 × 0.75 | 1.03 × 0.70 × 1.07 | -0.49..0.54 / -0.36..0.35 | 5,072 | Anim Fill 0, Anim Fill 2, Anim Fill 3, Body |
| `produce_T2.fbx` | Banca inclinada de madeira | 1.50 × 0.75 | 1.54 × 0.76 × 1.70 | -0.77..0.77 / -0.37..0.39 | 6,228 | Anim Fill 0, Anim Fill 2, Anim Fill 3, Body |
| `produce_T3.fbx` | Banca em degraus (madeira e metal) | 2.00 × 1.00 | 2.03 × 1.01 × 2.05 | -1.01..1.01 / -0.49..0.52 | 11,520 | Anim Fill 0, Anim Fill 2, Anim Fill 3, Body |
| `produce_T4.fbx` | Ilha refrigerada com névoa | 2.50 × 1.25 | 2.48 × 1.23 × 2.22 | -1.24..1.24 / -0.62..0.62 | 15,754 | Anim Fill 0, Anim Fill 1, Anim Fill 2, Anim Fill 3, Body |
| `coldroom_T1.fbx` | Freezer de estoque | 1.25 × 0.75 | 1.24 × 0.77 × 1.12 | -0.61..0.62 / -0.40..0.36 | 1,016 | Body |
| `coldroom_T2.fbx` | Mini câmara fria | 2.00 × 2.00 | 2.10 × 2.45 × 2.83 | -1.05..1.05 / -1.40..1.05 | 5,084 | Body |
| `coldroom_T3.fbx` | Câmara fria | 3.00 × 2.50 | 3.11 × 3.05 × 3.14 | -1.55..1.55 / -1.75..1.30 | 6,624 | Body |
| `coldroom_T4.fbx` | Câmara frigorífica | 5.00 × 4.00 | 5.10 × 5.25 × 3.78 | -2.55..2.55 / -3.20..2.05 | 9,220 | Body |
| `carts_T1.fbx` | Cestinhas (suporte) | 0.75 × 0.60 | 0.84 × 0.53 × 1.12 | -0.48..0.36 / -0.27..0.26 | 4,468 | Body |
| `carts_T2.fbx` | Carrinhos (baia) | 1.75 × 0.75 | 1.75 × 0.76 × 1.10 | -0.84..0.91 / -0.38..0.38 | 4,906 | Body |
| `carts_T3.fbx` | Carrinhos grandes (baia) | 2.25 × 1.00 | 2.21 × 0.98 × 1.30 | -1.12..1.09 / -0.49..0.49 | 6,688 | Body |
| `atm_T1.fbx` | Caixa eletrônico | 0.75 × 0.85 | 0.76 × 0.92 × 1.83 | -0.38..0.38 / -0.50..0.42 | 2,428 | Body |
| `atm_T2.fbx` | Dois caixas na parede | 1.50 × 0.85 | 1.50 × 0.63 × 2.25 | -0.75..0.75 / -0.20..0.43 | 4,632 | Body |
| `atm_T3.fbx` | Sala de autoatendimento bancário | 2.25 × 1.50 | 2.24 × 1.47 × 2.73 | -1.12..1.12 / -0.74..0.72 | 7,220 | Body |
| `gumball_T1.fbx` | Máquina de chiclete | 0.50 × 0.50 | 0.43 × 0.43 × 1.48 | -0.22..0.22 / -0.18..0.25 | 2,332 | Body |
| `gumball_T2.fbx` | Máquina de chiclete dupla | 1.00 × 0.50 | 0.90 × 0.49 × 1.49 | -0.45..0.45 / -0.24..0.24 | 5,236 | Body |
| `claw_T1.fbx` | Máquina de pelúcia | 0.75 × 0.75 | 0.72 × 0.77 × 1.90 | -0.36..0.36 / -0.41..0.36 | 3,958 | Body |
| `claw_T2.fbx` | Máquina de pelúcia dupla | 1.50 × 0.85 | 1.50 × 0.87 × 2.07 | -0.75..0.75 / -0.45..0.42 | 8,196 | Body |
| `claw_T3.fbx` | Pelúcia gigante | 1.50 × 1.50 | 1.48 × 1.49 × 2.48 | -0.74..0.74 / -0.77..0.72 | 7,018 | Body |

- `carts_T1/T2/T3` are **not tiers** but the three separate stations: `carts_T1` = Cestinhas (suporte),
  `carts_T2` = Carrinhos (baia), `carts_T3` = Carrinhos grandes (baia). In `carts_T3` the big carts are 1.3× the normal cart,
  and two kids' carts with toy-car fronts face the aisle.
- `coldroom_T1` sits indoors; T2/T3 attach outside to the depósito's side wall (door through the depósito), and T4
  attaches beside the central warehouse dock. See `previews/coldroom_place_T*.jpg` and the doc.
- `export_report.json` has the same data, plus every material per file.

## Cold room as a depot wing (Supermercado): `coldroom_depotwing_T2.fbx`, `coldroom_depotwing_T3.fbx`
- Built by `scripts/blender/depot_wing.py` (`depotwing_build`, `depotwing_export`).
- **Pivot = the depot's pivot, depot-LOCAL coordinates.** Parent the FBX to the `Depot_74x71` instance with
  local position/rotation zero; it then follows the depot's yaw (90° at this stage).
- **Placement** (depot-local, Unity axes): the wing hugs the EAST wall (local +z face at z = 3.786) and runs
  to the south end of the usable strip.

  | File | Wing x range | Outward z | Wing height | Overall bounds | Tris |
  |---|---|---|---|---|---|
  | `coldroom_depotwing_T2.fbx` | 1.40..5.40 (4 m) | 3.786..5.206 | 3.2 m | x 1.36..5.47, z 1.83..5.261, y 0..5.095 | 4,080 |
  | `coldroom_depotwing_T3.fbx` | −2.60..5.40 (8 m) | 3.786..5.206 | 3.4 m | x −2.64..5.47, z 1.83..5.261, y 0..5.095 | 6,196 |

  Everything stays inside the measured strip: x ≤ 6.4 (clear of the truck bay), outward ≤ 5.279 (the relief port and
  corner guards included), height < 5.28 (the roof condensers top out at 5.095).
- **No outside door.** The door is through the depot's east wall, from inside the depot; the wing is a closed box.
  - Between x 1.40 (T3 −2.60) and 3.87 the wing sits against the existing wall.
  - From 3.87 to 5.40 it stands past the south-east corner. There its west face (z = 3.786) and its south end face
    (x = 5.40) are the faces the south-west game camera sees.
- **Cladding** (thin, about 3 cm, no new footprint) goes on the depot's SOUTH face (x = 3.872), from the annex edge
  (z 1.85) to the corner. It has cream panels with seams, a navy kick band, the gold line and a navy corner guard.
  - T2 clads up to the wing height.
  - T3 clads up to the roof, and also clads the east wall above the wing up to the parapet.
- **Roof condensers** sit on the depot roof near the east edge (roof surface y = 4.41):
  - T2: one at x 3.0, z 3.2;
  - T3: a second one at x −0.2;
  - refrigerant pipes run over the parapet down to the wing roof.
- **South end face of the wing:** a navy snowflake pictogram (no text), a cool status light, a red light and a blank
  temperature display. Frost runs along the foot.
- **Materials:** same contract as the other exports (`C_RRGGBB_<Role>`: Navy and Gold paint-friendly, Cream/Metal
  keep), plus emissive lights (`E_...`). Check shot: `previews/coldroom_depotwing_T2_gamecam.jpg` / `_T3_gamecam.jpg`
  (the depot in clay, seen from the south-west).
- **Caveat:** I couldn't confirm the roof surface height from the mesh alone (I read 4.41 with a parapet at 4.62–4.76).
  If the condensers float or sink in game, nudge them in y.

## Sector screens (all seven special sectors, round 4, not exported yet)
- **Slots:** price panels and the ticket number display are separate meshes on two single material slots,
  `E_PriceScreen` and `E_TicketScreen`.
  - The screen UVs cover 0..1 (the price screens use a third of the preview sheet, chosen by `variant`, for the
    renders only).
  - The game draws pictograms and live prices into them.
- **Blanking on export:** `export_tier` blanks both slots (dark "screen off", no image) through `screens_blank`. The
  preview boards in `textures/preview/` are render-only.
- **KitRemap needs a change:** it parses `E_<hex>` as a glow colour, so add a case for these two names before the
  `E_` rule. Otherwise "PriceS" is read as a hex.

## Special sectors (round 4, approved): `sector-<id>_T<n>.fbx`
Twenty-one files: ids `acougue`, `padaria`, `queijaria` (shown as "Frios e laticínios"), `peixaria`, `sorvetes`,
`adega` and `sucos`, each at T1, T2 and T3.

- **Conventions:** same as the other kit exports.
  - The customer side faces Unity −Z.
  - The pivot is the footprint centre on the floor.
  - The objects are `Body` only (no Anim Fill).
- **Footprints:** T1 2.5 × 2.0 m, T2 3.25 × 2.5 m, T3 4.0 × 3.25 m. The back wall sits at +Z, just inside the footprint.
- **Textures:** products use `T_FT_Sector`, so copy `textures/FT_Sector_albedo.png` to `Assets/Art/Interior/Textures/`.
  Import it at **2048**: `KitTexture` caps textures at 1024 unless the path contains "IK_Labels", and 1024 halves
  the product detail. Some packs also use `T_FT_Labels`.
- **Material roles:** as above. Navy and Gold repaint; products, wood, cream and metal keep their colours.

### Screen and name slots (blank in the FBX; the game draws into them)
Each slot is a separate flat quad with UV 0..1 over its whole face, facing −Z. The table below gives each quad's
centre in Unity local coordinates and its size (width × height, metres).

| Slot | What it is | How it ships | What the game does |
|---|---|---|---|
| `E_PriceScreen` | digital price panels | dark "screen off" | draw product pictograms and price rows (several panels per tier share the slot) |
| `E_TicketScreen` | "agora atendendo" number display | dark | draw the current number |
| `E_NamePanel` | blank cream name area: T1 wall name board, T2 hanging sign, T3 testeira | cream | write the translated sector name |

- **KitRemap needs a change:** add explicit cases for these three names *before* the `E_<hex>` glow rule. As it is,
  "PriceS", "Ticket" and "NamePa" would be parsed as hex colours.
- **Ticket dispenser:** the "pegue sua senha" stand is regular geometry. Its floor point is listed per tier below.
  Its small sign plate is blank cream, not a slot.

| File | Tris | Bounds min → max (x, y, z) | Slots: centre (x, y, z) · size |
|---|---|---|---|
| `sector-acougue_T1.fbx` | 11,028 | (-1.27, 0.00, -0.97) → (1.27, 2.48, 1.00) | NamePanel (0.00, 2.25, 0.82) · 0.72×0.15 |
| `sector-acougue_T2.fbx` | 14,110 | (-1.65, 0.00, -1.26) → (1.65, 2.89, 1.25) | PriceScreen (-0.45, 2.42, 1.11) · 0.85×0.48<br>PriceScreen (0.45, 2.42, 1.11) · 0.85×0.48<br>TicketScreen (1.10, 2.45, 1.11) · 0.36×0.16<br>Dispenser (1.20, 0.00, -1.12)<br>NamePanel (-0.80, 2.30, -0.52) · 0.67×0.14 |
| `sector-acougue_T3.fbx` | 22,922 | (-2.02, 0.00, -1.64) → (2.02, 3.08, 1.62) | NamePanel (0.00, 2.85, 0.93) · 1.60×0.21<br>PriceScreen (-0.95, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (-0.12, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (0.71, 2.20, 1.49) · 0.80×0.45<br>TicketScreen (1.50, 2.38, 1.49) · 0.36×0.16<br>Dispenser (-1.70, 0.00, -1.50) |
| `sector-padaria_T1.fbx` | 9,327 | (-1.27, 0.00, -0.97) → (1.27, 2.60, 1.00) | NamePanel (0.45, 2.25, 0.82) · 0.72×0.15 |
| `sector-padaria_T2.fbx` | 12,784 | (-1.65, 0.00, -1.26) → (1.65, 2.89, 1.25) | PriceScreen (-0.85, 2.42, 1.11) · 0.80×0.45<br>PriceScreen (0.05, 2.42, 1.11) · 0.80×0.45<br>TicketScreen (0.90, 2.45, 1.11) · 0.36×0.16<br>Dispenser (-1.45, 0.00, -1.12)<br>NamePanel (-0.30, 2.30, -0.52) · 0.67×0.14 |
| `sector-padaria_T3.fbx` | 24,755 | (-2.02, 0.00, -1.64) → (2.02, 3.08, 1.62) | PriceScreen (-0.95, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (-0.12, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (0.71, 2.20, 1.49) · 0.80×0.45<br>TicketScreen (1.40, 2.38, 1.49) · 0.36×0.16<br>Dispenser (-1.70, 0.00, -1.50)<br>NamePanel (0.00, 2.85, 0.93) · 1.60×0.21 |
| `sector-queijaria_T1.fbx` | 8,008 | (-1.27, 0.00, -0.97) → (1.27, 2.48, 1.00) | NamePanel (0.00, 2.25, 0.82) · 0.72×0.15 |
| `sector-queijaria_T2.fbx` | 15,422 | (-1.65, 0.00, -1.26) → (1.65, 2.89, 1.25) | PriceScreen (-0.85, 2.42, 1.11) · 0.80×0.45<br>PriceScreen (0.05, 2.42, 1.11) · 0.80×0.45<br>TicketScreen (0.95, 2.42, 1.11) · 0.36×0.16<br>Dispenser (1.20, 0.00, -1.12)<br>NamePanel (-0.80, 2.30, -0.52) · 0.67×0.14 |
| `sector-queijaria_T3.fbx` | 23,706 | (-2.02, 0.00, -1.64) → (2.02, 3.08, 1.62) | PriceScreen (-1.20, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (-0.35, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (0.50, 2.20, 1.49) · 0.80×0.45<br>TicketScreen (1.25, 2.38, 1.49) · 0.36×0.16<br>Dispenser (-1.70, 0.00, -1.50)<br>NamePanel (0.00, 2.85, 0.93) · 1.60×0.21 |
| `sector-peixaria_T1.fbx` | 8,421 | (-1.27, 0.00, -0.97) → (1.27, 2.48, 1.00) | NamePanel (0.00, 2.25, 0.82) · 0.72×0.15 |
| `sector-peixaria_T2.fbx` | 13,729 | (-1.65, 0.00, -1.26) → (1.65, 2.89, 1.25) | PriceScreen (-0.85, 2.42, 1.11) · 0.80×0.45<br>PriceScreen (0.05, 2.42, 1.11) · 0.80×0.45<br>TicketScreen (0.95, 2.42, 1.11) · 0.36×0.16<br>Dispenser (1.20, 0.00, -1.12)<br>NamePanel (-0.80, 2.30, -0.52) · 0.67×0.14 |
| `sector-peixaria_T3.fbx` | 17,499 | (-2.02, 0.00, -1.64) → (2.02, 3.08, 1.62) | PriceScreen (-0.95, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (-0.12, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (0.71, 2.20, 1.49) · 0.80×0.45<br>TicketScreen (1.50, 2.38, 1.49) · 0.36×0.16<br>Dispenser (-1.70, 0.00, -1.50)<br>NamePanel (0.00, 2.85, 0.93) · 1.60×0.21 |
| `sector-sorvetes_T1.fbx` | 7,788 | (-1.27, 0.00, -0.97) → (1.27, 2.48, 1.00) | NamePanel (0.00, 2.25, 0.82) · 0.72×0.15 |
| `sector-sorvetes_T2.fbx` | 11,210 | (-1.65, 0.00, -1.02) → (1.65, 2.89, 1.25) | PriceScreen (-0.85, 2.42, 1.11) · 0.80×0.45<br>PriceScreen (0.05, 2.42, 1.11) · 0.80×0.45<br>NamePanel (-0.50, 2.30, -0.52) · 0.67×0.14 |
| `sector-sorvetes_T3.fbx` | 20,772 | (-2.02, 0.00, -1.40) → (2.02, 3.08, 1.62) | PriceScreen (-1.20, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (-0.35, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (0.50, 2.20, 1.49) · 0.80×0.45<br>NamePanel (0.00, 2.85, 0.93) · 1.60×0.21 |
| `sector-adega_T1.fbx` | 12,056 | (-1.27, 0.00, -0.81) → (1.27, 2.48, 1.00) | NamePanel (0.00, 2.25, 0.82) · 0.72×0.15 |
| `sector-adega_T2.fbx` | 17,434 | (-1.65, 0.00, -1.01) → (1.65, 2.89, 1.25) | PriceScreen (-0.55, 2.42, 1.11) · 0.80×0.45<br>NamePanel (-0.30, 2.30, -0.62) · 0.67×0.14 |
| `sector-adega_T3.fbx` | 19,760 | (-2.06, 0.00, -1.35) → (2.02, 3.08, 1.62) | PriceScreen (-1.05, 2.25, 1.49) · 0.80×0.45<br>PriceScreen (0.70, 2.25, 1.49) · 0.80×0.45<br>NamePanel (0.00, 2.85, 0.93) · 1.60×0.21 |
| `sector-sucos_T1.fbx` | 11,898 | (-1.27, 0.00, -1.02) → (1.27, 2.48, 1.00) | NamePanel (0.00, 2.25, 0.82) · 0.72×0.15 |
| `sector-sucos_T2.fbx` | 18,470 | (-1.65, 0.00, -1.17) → (1.65, 2.89, 1.25) | PriceScreen (-0.85, 2.42, 1.11) · 0.80×0.45<br>PriceScreen (0.05, 2.42, 1.11) · 0.80×0.45<br>NamePanel (-0.30, 2.30, -0.52) · 0.67×0.14 |
| `sector-sucos_T3.fbx` | 25,350 | (-2.02, 0.00, -1.55) → (2.02, 3.08, 1.62) | PriceScreen (-1.20, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (-0.35, 2.20, 1.49) · 0.80×0.45<br>PriceScreen (0.50, 2.20, 1.49) · 0.80×0.45<br>NamePanel (0.00, 2.85, 0.93) · 1.60×0.21 |

`sector_export_report.json` has the same data plus the material list per file.
