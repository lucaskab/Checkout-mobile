# Supplied shop models

The five GLBs are preserved in this folder. `scripts/blender/prepare_map_models.py` exports the three shelf meshes and textures; `scripts/blender/prepare_shop_people.py` skins the supplied women to the established rig and exports seven animation clips per character.

`CheckoutShelfSlots` reads the authoritative snapshot `shelves[].unlocked` and `category`. One physical fixture is active per owned slot, with beverage, grocery, and display variants. The current game has four initial slots and upgrades to seven; capacity upgrades continue to change stock capacity, not fixture count. Fixture markers and customer approach points follow the new layout.

`CheckoutShopUpgradeBuilder` applies this migration once, preserving the rest of the scene. The counter is rotated 180 degrees, the cashier stands behind its keyboard, and the customer queue is on the conveyor side. The existing Customer_01 pool entry uses the new girl. `CheckoutCashier` runs scanning and payment gestures during actual customer checkout; it does not change the authoritative economy. Hired cashiers no longer create overlapping visual staff at this single register.

Validation: six parked visits completed shopping, checkout and departure. `Supermarket/Validate purchased shelf slots` in Play Mode verifies 4/5/6/7/4 visible fixtures, category changes, paths to all seven shelf approaches, and required cashier clips. Imported hand props use world-size compensation for the FBX rig scale.
