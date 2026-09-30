using System;
using UnityEngine;

namespace Checkout
{
    // Scenery is baked into the scene; snapshots only swap the purchased lots.
    public class CheckoutExpansionNeighborhood : MonoBehaviour
    {
        public enum Area { Storage, Parking, LoadingYard, Premium, Market, GrandWarehouse, BothYards }

        [Serializable]
        public class Lot
        {
            public GameObject building;
            public Area area;
            public int replacedAtStage;
        }

        public Lot[] lots = Array.Empty<Lot>();

        public void Apply(MarketLayout layout)
        {
            foreach (var lot in lots)
            {
                if (!lot.building) continue;
                bool purchased = lot.area switch
                {
                    Area.Storage => layout.storage,
                    Area.Parking => layout.parking,
                    // The old truck yard gives its ground back to the square once the central warehouse moves the trucks.
                    Area.LoadingYard => layout.loadingYard && !layout.storageLarge,
                    Area.GrandWarehouse => layout.storageLarge,
                    Area.BothYards => layout.loadingYard || layout.storageLarge,
                    Area.Premium => layout.premium,
                    _ => layout.stage >= lot.replacedAtStage,
                };
                lot.building.SetActive(!purchased);
            }
        }
    }
}
