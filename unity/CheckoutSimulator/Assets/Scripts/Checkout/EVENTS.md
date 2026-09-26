# Unity event visuals

`CheckoutMap` passes the shared React Native snapshot to `CheckoutEventVisuals`.
The Unity layer only projects the event: customer, inventory, production, and
revenue rules stay in the React Native store.

`CheckoutEventAssets` loads props from `Resources/EventProps/<Name>.fbx`. Every prop carries one material
`G_<Name>` that Unity renders with the Standard shader and `Resources/EventProps/Tex/<Name>.png`, the same
way the supplied Tripo map models are rendered, so event art sits next to the game's own GLBs:

- `Game*` props are the supplied GLBs from `ArtSource/MapModels` (cardboard box, vegetable crate, fruit
  stand, cars, toy van, delivery truck, flower planter, traffic light, construction worker), re-exported at
  real-world size and lightly decimated.
- The other props are modelled in `scripts/blender/build_event_props.py` and baked in Cycles into a painted
  atlas (palette colour, soft variation, ambient occlusion, warm edge highlights); sign artwork comes from
  `ArtSource/EventProps/SignTextures`.

People are live clones of the market's own rigged characters (`Customer_0x`, `Worker_*`) looping their
Blender clips. Positions follow map anchors: the entrance (`CheckoutMap.Entrance`), the cashier, the baker,
the warehouse and the delivery trucks, and interior points follow the purchased store size. Props are created
on first activation and cached per store size; only the active event animates. Expiry is checked locally.
Deactivation clears particles and restores the original light and ambient colors.

## Blender props (Unity ↔ Blender bridge)

**Checkout → Eventos → 1. Gerar props no Blender** runs Blender headless (about 10 minutes for all props),
writes previews to `ArtSource/EventProps/Previews` and reimports. The Blender MCP add-on can run the same
script interactively. Then **2. Abrir mercado e dar Play**. While playing: `]`/`PageDown` next event,
`[`/`PageUp` previous, `0` hands control back to the game, `F` toggles the camera focus, `F9` captures every
event to `ArtSource/EventProps/Captures` (editor/development builds only, `CheckoutEventPreview`).

## Desktop host

The desktop build runs the real game store with Node (`desktop/host.ts`). It needs the JavaScript
dependencies: run `bun install` in the repository root. If Node reports missing files inside
`node_modules` (for example `zustand/esm/index.mjs`), clear the bun cache with `bun pm cache rm`, delete
`node_modules` and install again.

| Event ID | Scene assets |
| --- | --- |
| hora-do-pico | Stanchion queue to the door, shoppers with carts waiting, more arriving, rising arrow |
| pagamento-caiu | Shoppers with loaded carts at the till, floating money bag, spinning coins, coin stack |
| influenciadora-local | Creator corner on the sidewalk: pastel LIVE backdrop, ring light + phone, creator, rising hearts |
| feira-do-bairro | Striped fair tents plus the market's fruit stands and vegetable crates, bunting, balloons, neighbours |
| desconto-atacadista | Pallets stacked with the market's cardboard boxes at the warehouse doorstep, pallet jack, stocker, wholesale price board |
| rota-livre | The market's delivery truck cruising the front street over green lane arrows, traffic light, star |
| equipe-inspirada | Gold stars over every counter worker, fresh bread racks, "Equipe nota 10" banner, energy bolts |
| treinamento-expresso | Whiteboard lesson, trainee chairs, instructor and trainees, graduation cap |
| caixa-da-sorte | Giant gift box, "Caixa da sorte" sign, confetti cannons + confetti bursts, spinning coins |
| dia-perfeito | Flower arch over the entrance, the market's flower planters, balloon bunches, smiling sun, confetti, warmer sunshine |
| chuva-forte | Exterior rain, wet pavement, umbrellas and overcast lighting |
| obras-na-rua | Curbside trench in front of the entrance (Blender prop `RoadWorks`, now painted by material name); neighborhood cars swerve around it |
| concorrente-em-promocao | Rival magenta pop-up tent on the opposite sidewalk, -50% promo board, dancing tube man, tempted shoppers |
| clientes-economicos | Shoppers comparing prices with carts, calculator and shopping list icons, coupon stand, bargain tag |
| instabilidade-nos-caixas | POS with error screen on the counter, sparks, pulsing warning, out-of-order sign, technician (construction worker model), toolbox |
| alta-do-combustivel | Fuel pump with a climbing price beside the delivery trucks, barrels, jerry can, delivery worker, red up arrow |
| transito-pesado | Bumper-to-bumper line of the city's cars and vans on the east street, exhaust puffs, "lento" sign, grumpy cloud |
| manutencao-de-equipamentos | Taped-off repair zone in front of the bakery oven, technician, step ladder, toolbox, sign, spinning gears, steam |
| equipe-cansada | Staff break corner beside the warehouse (bench, coffee machine), drowsy workers swaying, Zzz, coffee cup, steam |
| fiscalizacao-surpresa | Inspector with folding table and forms, clipboard, magnifier and ID badge |

Shelf status pills only appear for low/empty stock; production pills appear while
work is active. Full names, quantities and prices remain in the existing native
panels. Dragging or pinching the map does not open a fixture panel.

## Isolated runtime validation

From the repository root, generate an isolated fixture:

```sh
bun scripts/simulator-fixture.ts /tmp/checkout-event-fixture.json
```

Build the current scene with Unity's `-executeMethod CheckoutVisualBuilder.Desktop`
and run `unity/builds/visual-qa/Checkout.app/Contents/MacOS/Checkout\ Simulator` with:

```sh
--checkout-snapshot /tmp/checkout-event-fixture.json --checkout-event-qa /tmp/checkout-event-qa
```

The playtest captures all 20 scenes plus portrait rain, checks active geometry,
shader support, actual rain emission, repeated snapshots, expiry, particle
cleanup, lighting restoration and unchanged inventory. It writes `report.json`.
Use `CheckoutVisualBuilder.IOS` to export the current integrated scene without
regenerating `Supermarket.unity`; rebuild the native UnityFramework afterward.
