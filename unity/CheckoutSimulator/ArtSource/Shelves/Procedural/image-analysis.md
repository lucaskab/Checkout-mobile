# Shelf family image analysis

## Reference suitability

The three supplied renders are technically suitable transparent PNGs and show the same static supermarket shelf family from a near-front orthographic view. They are appropriate for a stylized reconstruction. The rear face, exact depth, underside, and internal fasteners are hidden; the reconstruction uses a shallow rectangular depth and mirrored side structure.

## Physical observation

- **Classification:** static retail furnishing; primary domain `object`; confidence 0.98.
- **Overall silhouette:** an upright, bilaterally symmetric rounded rectangular shelving unit. Its visible height is about 1.15 times its width. The three variants share a cream frame, teal shelf lips, and warm wood shelf decks.
- **Macro assemblies:** two vertical rounded side uprights; a top crossbar; three shelf decks; three teal front rails; two low feet; a shallow rear panel.
- **Meso assemblies:** every deck is a shallow cuboid with an exposed front rail. The feet extend slightly forward and sideways from the uprights. The full and partial variants add removable stock groups.
- **Stock groups:** crate assemblies, basket assemblies, and loose food shapes. The full shelf has fruit, vegetables, bread, jars, cartons, and boxes. The partial shelf intentionally leaves large bare areas. The empty shelf has no stock.
- **Spatial relationships:** each shelf deck is embedded between the uprights and backed by the rear panel. Each teal rail sits flush to the deck's front edge. Food groups rest on deck surfaces.
- **Materials:** cream-painted wood or satin plastic frame (dielectric, roughness about 0.42); muted teal painted rails (dielectric, roughness about 0.34); warm light wood decks and crates (roughness about 0.5); food uses opaque saturated dielectric materials with roughness 0.35–0.65.
- **Identity features:** tall rounded uprights, broad teal rails, cream-and-teal palette, exposed wood decks, and clearly different stock density per variant.

## Reconstruction limits

The reference is a single frontal view, so rear supports, true shelf depth, and unseen food placement are approximated. The resulting models will be stylized, static, low-poly game props rather than image-extracted meshes.

## Suitability verdict

**Pass.** Each image has one unambiguous target object, a complete strong silhouette, visible major materials, and an implied shallow depth that can be reconstructed with procedural primitives. Exact hidden-side geometry is not required for this stylized game prop.
