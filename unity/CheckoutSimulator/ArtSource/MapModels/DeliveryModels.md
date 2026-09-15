# Produce and delivery models

The supplied fruit stand replaces Produce inside its existing footprint. Its baked produce replaces the old stock meshes; stock roots remain available to the snapshot projection. Vegetable crates and a cardboard parcel sit on the warehouse porch, outside the unloading route.

ConstructionWorker.glb is rigged by `scripts/blender/prepare_delivery_worker.py`, using the established worker hierarchy with fitted joint pivots and six new cargo clips. The exported model has a 24,000 triangle budget. Both feet remain planted during the lowering pose. Unity uses the existing Legacy Animation workflow.

`CheckoutDeliveryModelsBuilder.Apply` installs the models in the current scene. Full map builds also apply this builder. `MarketDeliveryWorker` owns this worker's locomotion and animations. The ambient and snapshot truck controllers reserve the first truck during unloading. Its route follows the porch from (-1.65, 16.19) through (3.7, 16.19) and (4.65, 16.85) to the rear of the truck at (6.5, 16.85), then returns to release the parcel at (-1.65, .15, 16.72). Coordinates are Unity world x/y/z, with y omitted for the horizontal route.

This is the yard's ambient delivery presentation. It does not change authoritative stock, order completion, or currency. The deposited parcel remains at the door for the waiting interval, then is reused for the next visible trip.

Rebuild static models with Blender using `scripts/blender/prepare_map_models.py -- FruitMarketStand VegetableCrate CardboardBox`, and the character with `scripts/blender/prepare_delivery_worker.py`. Original GLBs are retained in this folder.

Run **Supermarket > Playtest delivery worker** to check skin deformation, planted feet, two full unload trips, package parenting and release, ground contact, truck clearance, and the existing shopper/navigation playtest. Results are recorded in `DeliveryValidation.json`; `DeliveryPickup.png`, `DeliveryDrop.png`, and `DeliveryMapPreview.png` show the live scene.
