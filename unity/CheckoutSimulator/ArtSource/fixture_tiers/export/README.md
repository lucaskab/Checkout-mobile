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

## Special sectors (round 5): `sector-<sid>_T<n>.fbx`
Twenty-one files: ids `acougue`, `padaria`, `queijaria` (shown as "Frios e laticínios"), `peixaria`, `sorvetes`, `adega`
and `sucos` (the Bebidas art), each at T1, T2 and T3. Source: `scripts/blender/sector_v5.py` (shared parts, açougue)
and `scripts/blender/sector_v5_sectors.py` (the other six, export), executed after `sector_v4.py`.
Previews: `previews/walls/`.

- **Conventions:** as for the other kit exports: Unity local (x, y, z) = modelling (x, z, y), the customer side faces
  −Z, and the pivot is the footprint centre on the floor.
- **Back face:** at local **+Z = +depth/2** (`backFaceZ` in the table and the report). Nothing sticks out behind it: no
  cap overhang, lip or bracket. It can stand exactly on the market wall's rail face.
- **Height:** 2.45 m (the panel's gold cap), under the market wall's 2.49 m.
- **Footprints:** every sector uses the same sizes.

  | Tier | Round 4 | Round 5 |
  |---|---|---|
  | T1 | 2.5 × 2.0 | **2.5 × 3.25** |
  | T2 | 3.25 × 2.5 | **3.25 × 3.5** |
  | T3 | 4.0 × 3.25 | **4.0 × 3.5** |

  The extra depth gives the staff lane: at least 1.47 m, i.e. the widest worker (1.22 m, baker and cheesemaker
  rigs) plus 0.25 m.

### Three objects (direct children of the FBX root)
| Object | What it holds | Game |
|---|---|---|
| `Body` | counters, machines, furniture, products, the lane mat | always shown |
| `Back Wall` | only the freestanding panel: cream body, navy fluted wainscot to 0.95 m, gold rail, thin gold cap, navy side returns. Back face on the footprint edge, 7–8 cm deep (`backWall` bounds below) | hide it when the piece stands against a tall market wall |
| `Wall Dressing` | everything mounted on the wall: the menu board (name header, price panels, ticket counter), hook rails, knife strips, shelves, wicker baskets, net, wine lattice, cold-room door | always shown; on brackets reaching back to the edge, so it reads on the panel and on the market wall alike |

- **Panel colours** match the market wall, so "Cores do mercado" repaints it with the player's colours:
  - `C_1D2B4F_Navy`: wainscot, side returns;
  - `C_D3A53D_Gold`: rail and cap;
  - `C_F2EADB_Cream`: body, never repainted (the plaster colour).
- **Sector accents** are flat `C_<hex>_Product` colours and textures, never repainted:
  - açougue: burgundy enamel and butcher block;
  - padaria: terracotta, warm wood, brick;
  - frios: butter yellow and wood;
  - peixaria: sea teal;
  - sorveteria: pastel pink and mint;
  - adega: wine burgundy and dark wood;
  - bebidas: citrus orange and green.
- **Wall Dressing assumes a full-height wall.** Against the low walls (0.75 m), keep `Back Wall` shown.

### Menu board and slots (blank in the FBX; the game draws into them)
Each sector has one integrated board in `Wall Dressing`:
- a slim stainless frame, matte black;
- a cream header strip carrying **`E_NamePanel`** (the sector name);
- **`E_PriceScreen`** quads, one per panel;
- at T2 and T3, **`E_TicketScreen`** in the header's right end.

| Tier | Panels | Ticket counter | Board size |
|---|---|---|---|
| T1 | 1 (0.78 × 0.44) | no | 0.85 × 0.67 m |
| T2 | 2 (0.68 × 0.38) | yes | 1.46 × 0.61 m |
| T3 | 3 (0.66 × 0.37) | yes | 2.11 × 0.61 m |

- The slot names, UVs (0..1 over each quad) and facing (−Z) are unchanged.
- Each price quad takes up to three rows (pictogram, coin, price), as `CheckoutSectorScreens` already writes them.
  The price quads are listed left to right below.
- The T3 testeira and the T2 hanging sign are gone: the name lives in the board header.
- Ticket dispensers (floor points) stand in front of the açougue, padaria, frios and peixaria counters at T2 and T3.
- **KitRemap** still needs explicit cases for `E_PriceScreen`, `E_TicketScreen` and `E_NamePanel` before the
  `E_<hex>` rule.

### Staff lane
- `staffLane` in `sector_export_report.json` gives, for each piece with a service counter:
  - `lane`: clear depth from the counter's back to the nearest back piece;
  - `laneX`: the x-range where that depth is at least 1.47 m;
  - `laneZ`: the clear depth's z-range;
  - `staff`: the centre point, in Unity local coordinates.
- The pacing span is (laneLength − 1.22) / 2.
- The adega has no service counter, so it has no lane.

| File | Footprint W × D | Tris | backFaceZ | Back Wall bounds min → max (x, y, z) | Staff lane | Slots: centre (x, y, z) · size |
|---|---|---|---|---|---|---|
| `sector-acougue_T1.fbx` | 2.50 × 3.25 | 12,656 (Body 7,760, Back Wall 644, Dressing 4,252) | 1.625 | (-1.25, 0.00, 1.54) → (1.25, 2.45, 1.62) | 1.61 m deep, x -0.88…0.88 (1.75 m), z -0.62…0.98; staff (0.00, 0.00, 0.18) | NamePanel (0.55, 2.21, 1.49) · 0.64×0.09<br>PriceScreen (0.55, 1.91, 1.50) · 0.78×0.44 |
| `sector-acougue_T2.fbx` | 3.25 × 3.50 | 16,296 (Body 12,198, Back Wall 728, Dressing 3,370) | 1.750 | (-1.62, 0.00, 1.67) → (1.62, 2.45, 1.75) | 1.49 m deep, x -1.38…1.38 (2.75 m), z -0.50…0.99; staff (0.00, 0.00, 0.24) | Dispenser (1.25, 0.00, -1.61)<br>NamePanel (-0.35, 2.21, 1.62) · 0.90×0.09<br>TicketScreen (0.33, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-0.56, 1.93, 1.62) · 0.68×0.38<br>PriceScreen (0.15, 1.93, 1.62) · 0.68×0.38 |
| `sector-acougue_T3.fbx` | 4.00 × 3.50 | 25,138 (Body 20,740, Back Wall 812, Dressing 3,586) | 1.750 | (-2.00, 0.00, 1.67) → (2.00, 2.45, 1.75) | 1.49 m deep, x -1.95…0.70 (2.65 m), z -0.50…0.99; staff (-0.62, 0.00, 0.24) | Dispenser (-1.70, 0.00, -1.61)<br>NamePanel (-0.29, 2.21, 1.62) · 1.46×0.09<br>TicketScreen (0.71, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-0.83, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.14, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (0.55, 1.94, 1.62) · 0.66×0.37 |
| `sector-padaria_T1.fbx` | 2.50 × 3.25 | 15,124 (Body 12,756, Back Wall 644, Dressing 1,724) | 1.625 | (-1.25, 0.00, 1.54) → (1.25, 2.45, 1.62) | 1.53 m deep, x -0.88…0.88 (1.75 m), z -0.62…0.91; staff (0.00, 0.00, 0.14) | NamePanel (0.30, 2.21, 1.49) · 0.64×0.09<br>PriceScreen (0.30, 1.91, 1.50) · 0.78×0.44 |
| `sector-padaria_T2.fbx` | 3.25 × 3.50 | 18,565 (Body 15,513, Back Wall 728, Dressing 2,324) | 1.750 | (-1.62, 0.00, 1.67) → (1.62, 2.45, 1.75) | 1.53 m deep, x -1.38…1.38 (2.75 m), z -0.50…1.03; staff (0.00, 0.00, 0.27) | Dispenser (1.25, 0.00, -1.61)<br>NamePanel (0.05, 2.21, 1.62) · 0.90×0.09<br>TicketScreen (0.73, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-0.15, 1.93, 1.62) · 0.68×0.38<br>PriceScreen (0.56, 1.93, 1.62) · 0.68×0.38 |
| `sector-padaria_T3.fbx` | 4.00 × 3.50 | 25,676 (Body 22,890, Back Wall 812, Dressing 1,974) | 1.750 | (-2.00, 0.00, 1.67) → (2.00, 2.45, 1.75) | 1.53 m deep, x -1.95…0.70 (2.65 m), z -0.50…1.03; staff (-0.62, 0.00, 0.27) | Dispenser (-1.70, 0.00, -1.61)<br>NamePanel (0.25, 2.21, 1.62) · 1.46×0.09<br>TicketScreen (1.25, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-0.29, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (0.40, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (1.09, 1.94, 1.62) · 0.66×0.37 |
| `sector-queijaria_T1.fbx` | 2.50 × 3.25 | 11,508 (Body 8,230, Back Wall 644, Dressing 2,634) | 1.625 | (-1.25, 0.00, 1.54) → (1.25, 2.45, 1.62) | 1.61 m deep, x -0.88…0.88 (1.75 m), z -0.62…0.98; staff (0.00, 0.00, 0.18) | NamePanel (0.10, 2.21, 1.49) · 0.64×0.09<br>PriceScreen (0.10, 1.91, 1.50) · 0.78×0.44 |
| `sector-queijaria_T2.fbx` | 3.25 × 3.50 | 18,510 (Body 15,404, Back Wall 728, Dressing 2,378) | 1.750 | (-1.62, 0.00, 1.67) → (1.62, 2.45, 1.75) | 1.48 m deep, x -1.38…1.38 (2.75 m), z -0.50…0.98; staff (0.00, 0.00, 0.24) | Dispenser (1.25, 0.00, -1.61)<br>NamePanel (-0.77, 2.21, 1.62) · 0.90×0.09<br>TicketScreen (-0.09, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-0.97, 1.93, 1.62) · 0.68×0.38<br>PriceScreen (-0.27, 1.93, 1.62) · 0.68×0.38 |
| `sector-queijaria_T3.fbx` | 4.00 × 3.50 | 24,758 (Body 21,522, Back Wall 812, Dressing 2,424) | 1.750 | (-2.00, 0.00, 1.67) → (2.00, 2.45, 1.75) | 1.61 m deep, x -1.95…0.70 (2.65 m), z -0.50…1.11; staff (-0.62, 0.00, 0.30) | Dispenser (-1.70, 0.00, -1.61)<br>NamePanel (-1.08, 2.21, 1.62) · 1.46×0.09<br>TicketScreen (-0.07, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-1.62, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.93, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.24, 1.94, 1.62) · 0.66×0.37 |
| `sector-peixaria_T1.fbx` | 2.50 × 3.25 | 11,037 (Body 8,139, Back Wall 644, Dressing 2,254) | 1.625 | (-1.25, 0.00, 1.54) → (1.25, 2.45, 1.62) | 1.54 m deep, x -0.88…0.88 (1.75 m), z -0.62…0.92; staff (0.00, 0.00, 0.14) | NamePanel (0.20, 2.21, 1.49) · 0.64×0.09<br>PriceScreen (0.20, 1.91, 1.50) · 0.78×0.44 |
| `sector-peixaria_T2.fbx` | 3.25 × 3.50 | 15,609 (Body 13,197, Back Wall 728, Dressing 1,684) | 1.750 | (-1.62, 0.00, 1.67) → (1.62, 2.45, 1.75) | 1.49 m deep, x -1.38…1.38 (2.75 m), z -0.50…0.99; staff (0.00, 0.00, 0.24) | Dispenser (1.25, 0.00, -1.61)<br>NamePanel (-0.55, 2.21, 1.62) · 0.90×0.09<br>TicketScreen (0.13, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-0.76, 1.93, 1.62) · 0.68×0.38<br>PriceScreen (-0.04, 1.93, 1.62) · 0.68×0.38 |
| `sector-peixaria_T3.fbx` | 4.00 × 3.50 | 17,855 (Body 15,279, Back Wall 812, Dressing 1,764) | 1.750 | (-2.00, 0.00, 1.67) → (2.00, 2.45, 1.75) | 1.54 m deep, x -1.95…0.07 (2.01 m), z -0.50…1.04; staff (-0.94, 0.00, 0.27) | Dispenser (-1.70, 0.00, -1.61)<br>NamePanel (-0.90, 2.21, 1.62) · 1.46×0.09<br>TicketScreen (0.10, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-1.44, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.75, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.06, 1.94, 1.62) · 0.66×0.37 |
| `sector-sorvetes_T1.fbx` | 2.50 × 3.25 | 10,102 (Body 6,902, Back Wall 644, Dressing 2,556) | 1.625 | (-1.25, 0.00, 1.54) → (1.25, 2.45, 1.62) | 1.50 m deep, x -0.88…0.88 (1.75 m), z -0.62…0.88; staff (0.00, 0.00, 0.12) | NamePanel (0.35, 2.21, 1.49) · 0.64×0.09<br>PriceScreen (0.35, 1.91, 1.50) · 0.78×0.44 |
| `sector-sorvetes_T2.fbx` | 3.25 × 3.50 | 16,684 (Body 12,020, Back Wall 728, Dressing 3,936) | 1.750 | (-1.62, 0.00, 1.67) → (1.62, 2.45, 1.75) | 1.49 m deep, x -1.55…0.65 (2.20 m), z -0.50…0.99; staff (-0.45, 0.00, 0.24) | NamePanel (0.17, 2.21, 1.62) · 0.90×0.09<br>TicketScreen (0.85, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-0.04, 1.93, 1.62) · 0.68×0.38<br>PriceScreen (0.68, 1.93, 1.62) · 0.68×0.38 |
| `sector-sorvetes_T3.fbx` | 4.00 × 3.50 | 21,756 (Body 19,738, Back Wall 812, Dressing 1,206) | 1.750 | (-2.00, 0.00, 1.67) → (2.00, 2.45, 1.75) | 1.48 m deep, x -1.95…0.70 (2.65 m), z -0.50…0.98; staff (-0.62, 0.00, 0.24) | NamePanel (-1.00, 2.21, 1.62) · 1.46×0.09<br>TicketScreen (0.01, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-1.54, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.85, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.16, 1.94, 1.62) · 0.66×0.37 |
| `sector-adega_T1.fbx` | 2.50 × 3.25 | 15,018 (Body 12,026, Back Wall 644, Dressing 2,348) | 1.625 | (-1.25, 0.00, 1.54) → (1.25, 2.45, 1.62) | no counter | NamePanel (-0.60, 2.21, 1.49) · 0.64×0.09<br>PriceScreen (-0.60, 1.91, 1.50) · 0.78×0.44 |
| `sector-adega_T2.fbx` | 3.25 × 3.50 | 16,698 (Body 14,810, Back Wall 728, Dressing 1,160) | 1.750 | (-1.62, 0.00, 1.67) → (1.62, 2.45, 1.75) | no counter | NamePanel (-0.70, 2.21, 1.62) · 0.90×0.09<br>TicketScreen (-0.02, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-0.91, 1.93, 1.62) · 0.68×0.38<br>PriceScreen (-0.20, 1.93, 1.62) · 0.68×0.38 |
| `sector-adega_T3.fbx` | 4.00 × 3.50 | 22,220 (Body 20,202, Back Wall 812, Dressing 1,206) | 1.750 | (-2.00, 0.00, 1.67) → (2.00, 2.45, 1.75) | no counter | NamePanel (-1.08, 2.21, 1.62) · 1.46×0.09<br>TicketScreen (-0.07, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-1.62, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.93, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.24, 1.94, 1.62) · 0.66×0.37 |
| `sector-sucos_T1.fbx` | 2.50 × 3.25 | 16,220 (Body 13,884, Back Wall 644, Dressing 1,692) | 1.625 | (-1.25, 0.00, 1.54) → (1.25, 2.45, 1.62) | 1.56 m deep, x -0.90…0.54 (1.44 m), z -0.57…0.98; staff (-0.18, 0.00, 0.20) | NamePanel (-0.15, 2.21, 1.49) · 0.64×0.09<br>PriceScreen (-0.15, 1.91, 1.50) · 0.78×0.44 |
| `sector-sucos_T2.fbx` | 3.25 × 3.50 | 20,916 (Body 18,040, Back Wall 728, Dressing 2,148) | 1.750 | (-1.62, 0.00, 1.67) → (1.62, 2.45, 1.75) | 1.63 m deep, x -1.20…1.20 (2.40 m), z -0.65…0.98; staff (0.00, 0.00, 0.17) | NamePanel (-0.55, 2.21, 1.62) · 0.90×0.09<br>TicketScreen (0.13, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-0.76, 1.93, 1.62) · 0.68×0.38<br>PriceScreen (-0.04, 1.93, 1.62) · 0.68×0.38 |
| `sector-sucos_T3.fbx` | 4.00 × 3.50 | 26,188 (Body 22,706, Back Wall 812, Dressing 2,670) | 1.750 | (-2.00, 0.00, 1.67) → (2.00, 2.45, 1.75) | 1.63 m deep, x -1.90…0.80 (2.70 m), z -0.65…0.98; staff (-0.55, 0.00, 0.17) | NamePanel (-1.00, 2.21, 1.62) · 1.46×0.09<br>TicketScreen (0.01, 2.21, 1.61) · 0.25×0.11<br>PriceScreen (-1.54, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.85, 1.94, 1.62) · 0.66×0.37<br>PriceScreen (-0.16, 1.94, 1.62) · 0.66×0.37 |

`sector_export_report.json` holds the same data, plus the material list and bounds of each file.
