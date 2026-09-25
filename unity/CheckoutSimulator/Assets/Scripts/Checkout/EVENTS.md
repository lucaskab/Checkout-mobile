# Unity event visuals

`CheckoutMap` passes the shared React Native snapshot to `CheckoutEventVisuals`.
The Unity layer only projects the event: customer, inventory, production, and
revenue rules stay in the React Native store.

`CheckoutEventAssets` builds reusable low-poly meshes with the existing painted
shader. Props are created on first activation, batched by material, and cached.
Only the active event animates. Expiry is checked locally, including when the
bridge has not delivered a new snapshot. Deactivation clears particles and
restores the original light and ambient colors.

| Event ID | Scene assets |
| --- | --- |
| hora-do-pico | Arriving shoppers and shopping carts |
| pagamento-caiu | Loaded carts and animated gold coins |
| influenciadora-local | Creator, phone, tripod, ring light, floating hearts |
| feira-do-bairro | Produce stalls, striped awnings, balloons |
| desconto-atacadista | Wholesale pallet, stacked crates, discount display |
| rota-livre | Moving delivery van and clear lane arrows |
| equipe-inspirada | Energy bolts and fresh production trays |
| treinamento-expresso | Training board, checklist and instructor |
| caixa-da-sorte | Checkout gift and animated coins |
| dia-perfeito | Entrance flowers, balloons and warmer sunshine |
| chuva-forte | Exterior rain, wet pavement, umbrellas and overcast lighting |
| obras-na-rua | Curbside trench in front of the entrance (Blender prop `RoadWorks`): cut asphalt, dirt, sand, pipe, wheelbarrow, cones, barricades and a warning sign; neighborhood cars swerve around it |
| concorrente-em-promocao | Competitor stall, discount board and balloon |
| clientes-economicos | Shoppers comparing a checklist and calculator |
| instabilidade-nos-caixas | Error terminal and repair toolbox |
| alta-do-combustivel | Fuel pump, hose and rising-price display |
| transito-pesado | Queue of cars moving slowly |
| manutencao-de-equipamentos | Repair station, technician, tools and steam |
| equipe-cansada | Break bench, coffee cups, steam and tired employee |
| fiscalizacao-surpresa | Inspector, checklist, ID badge and document case |

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
