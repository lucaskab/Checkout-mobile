# Meshy customers

`CustomerChild.glb` is the supplied Meshy source, kept unchanged. It has no skeleton
or clips. `build_customers.py` binds an optimized copy to the existing customer rigs
and exports all five original actions for each customer to `Assets/Art/Characters/Meshy`.
The original customer FBXs remain the animation sources. Basket/cart geometry and
its Prop bone are retained. The new body uses the original base-color texture at 2048px.

Regenerate from the Unity project directory:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python ArtSource/Customers/build_customers.py
```

Then run Unity's `Supermarket/Apply Meshy customers to current scene` menu. This
updates customer visuals and animation references without rebuilding the market.
Fresh market builds also apply the replacement automatically.
`CheckoutCustomerBuilder.Validate` checks all 25 clips for unchanged duration,
skin deformation, bounded geometry, and a textured mobile-sized mesh.

The mesh uses smooth weights around the existing joints, with pivots fitted to the
new sculpt. Animation rotations/timing and navigation remain owned by the existing
customer clips and scripts. No GLB loader or animation service is required at runtime.
