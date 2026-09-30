using UnityEngine;

namespace Checkout
{
    // Data carried by every Interior Kit template (built by CheckoutInteriorKitBuilder). All points are in
    // the piece's own space: origin on the floor, customers on the -Z side, staff (if any) on +Z.
    public class CheckoutInteriorPiece : MonoBehaviour
    {
        // Footprint on the floor (x, z) that nobody walks through, staff area included.
        public Vector2 min = new Vector2(-.95f, -.4f), max = new Vector2(.95f, .4f);
        // Where a shopper stands to take something (shelves and sector counters).
        public bool serves;
        public Vector3 approach = new Vector3(0, 0, -.95f);
        // Where the clerk, cashier or sector worker stands.
        public bool staffed;
        public Vector3 staff;
        // Checkout lanes: where shoppers wait ([0] pays) and what they face while paying.
        public Vector3[] queue = new Vector3[0];
        public Vector3 register;
        public Vector3 beltStart, beltEnd;
        // Stock on display, shown group by group as the shelf fills up.
        public GameObject[] fill = new GameObject[0];
        public float markerHeight = 2f;
    }
}
