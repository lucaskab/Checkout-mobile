# Supplied map models

Source: the user-supplied GLBs from Downloads, preserved here under stable names.
Run `scripts/blender/prepare_map_models.py` with Blender in background mode to regenerate the FBXs and textures in `Assets/Art/Models/MapModels`.

Apply using **Supermarket > Apply supplied map models** in Unity. The fresh scene builder also applies these replacements.

- DeliveryTruck → Anim_Truck_5
- FishDeliveryTruck → Anim_Truck_8
- IceCreamTruck → Anim_Truck_11
- Warehouse → Warehouse
- DisplayShelf → snacks aisle at (-1.6, 0.74, 0.3)
- WineRack → drinks aisle at (2, 0.74, -1.18)

Each aisle uses two pairs of back-to-back units fitted within the existing navigation obstacle. The rear coffee rack is retained from the combined Groceries mesh. Supplied shelves include baked-in products; the previous stock renderers are disabled to avoid overlapping products, while stock roots and snapshot handling remain intact.

Truck wrappers, positions and delivery movement remain unchanged. Models use uniform scale, corrected FBX axes, grounded bounds, and the existing parking footprints. Truck loading doors and the warehouse entrance face the market.

`CheckoutMapModelsPlaytest.Run` applies the assets, enters Play Mode with a temporary preview snapshot, checks truck movement and complete navigation paths to both aisle approaches, and captures a preview. The snapshot is not saved to the scene or the React Native game state.

## Checkout and market shell

- CheckoutCounter → Checkout, inside the original navigation obstacle; the cashier stands beside its terminal. Both simulation paths use the same payment-facing target.
- MarketStructure → Building, fitted to the existing 18.8 × 14.8 footprint and 0.74 walking surface. The supplied fixed central doorway is removed; its front low walls meet the original animated entrance at x=-1.75. The existing door frame, entrance ramp, landscaping, and rear delivery access remain.

`CheckoutStructureBuilder` preserves access geometry from the original Building mesh, stores the fitted shell as a separate mesh, and validates entrance clearance, delivery clearance, and floor heights against the actual mesh. The playtest also verifies a complete customer shopping, checkout, and exit cycle.

To regenerate only the two new imports: `Blender --background --python scripts/blender/prepare_map_models.py -- CheckoutCounter MarketStructure`.

## Service displays

- ButcherDisplay → Sector_acougue, front edge z=3.35, width 4.15.
- SeafoodCounter → Sector_peixaria, front edge z=3.35, width 3.85. Its legacy east-aisle freezers are retained.
- CheeseDisplay → Sector_queijaria, centered near (-3.8, 0.74, 4.15), width 2.4, beside the bakery. Its navigation obstacle and sector interaction marker follow the new position. The coffee approach moves slightly right to leave room.

The existing butcher and fishmonger keep their animation controllers and stand at floor height behind the display cabinets. All replacements remain under their sector roots so sector unlocking still controls visibility.

The runtime QA checks movement accumulated over simulation time for each truck, reachability of all seven shelf approaches and three new counter approaches, and a complete customer visit through checkout and the animated entrance.
