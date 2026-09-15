using UnityEngine;

namespace MarketDay
{
    // Tracks applied offsets so rebuilding assets never moves the yard twice.
    public class MarketOutdoorLayout : MonoBehaviour
    {
        public float warehouseShift;
        public float deliveryShift;
        public float deliverySideShift;
        public int yardVersion;
        public int terrainVersion;
        public int cityVersion;
    }
}
