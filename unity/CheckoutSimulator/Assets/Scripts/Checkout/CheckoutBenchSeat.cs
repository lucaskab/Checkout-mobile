using UnityEngine;

namespace Checkout
{
    // Marks a plaza bench: seat top at localPosition.y + seatHeight, sitters face the bench's -Z.
    public class CheckoutBenchSeat : MonoBehaviour
    {
        public float seatHeight = .465f, width = 1.8f;
        [System.NonSerialized] public int sitters;
    }
}
