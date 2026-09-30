using UnityEngine;

namespace Checkout
{
    // A piece of the market's look that belongs to some expansion stages only (facades, awnings,
    // signs, interior decor). Its base position is in the unprojected (scale 1) market space and is
    // re-projected whenever the market grows, so it stays glued to the scaled walls.
    public class CheckoutStageItem : MonoBehaviour
    {
        public int minStage, maxStage = 4;
        // Long pieces (awnings, parapets) follow the wall length instead of keeping their size.
        public bool stretchX, stretchZ;
        // Solid decor that shoppers must walk around.
        public bool blocksNavigation;
        // Existing scenery that only makes way for the bigger market: shown/hidden, never moved.
        public bool fixedPosition;
        // Keeps a constant distance outside the east wall instead of being projected (the shop grows
        // towards that street, so projected pieces would end up on the road).
        public bool attachEast;
        // Pieces that need the yard behind the shop: 1 = only with the central warehouse (its truck yard moves
        // away and frees the strip behind the shop), -1 = only without it, 0 = either.
        public int centralWarehouse;
        [HideInInspector] public Vector3 basePosition, baseScale = Vector3.one;
        [HideInInspector] public bool captured;

        public bool Visible(int stage) => stage >= minStage && stage <= maxStage;
        public bool Fits(MarketLayout state) => centralWarehouse == 0 || (state != null && state.storageLarge ? centralWarehouse > 0 : centralWarehouse < 0);

        public void Capture()
        {
            basePosition = transform.position;
            baseScale = transform.localScale;
            captured = true;
        }
    }
}
