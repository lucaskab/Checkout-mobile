using UnityEngine;

namespace Checkout
{
    // Starts the cyclists and bench visitors wherever the Harbour Quay plaza has been built.
    public static class CheckoutPlazaLife
    {
        // Started by CheckoutBoot once the game scene is loaded (the Boot scene comes first on Android).
        internal static void Boot()
        {
            var plaza = GameObject.Find("Harbour Quay Plaza");
            if (!plaza || Object.FindAnyObjectByType<CheckoutPlazaCyclists>()) return;
            var life = new GameObject("Plaza life");
            life.transform.SetParent(plaza.transform.parent, false);
            life.AddComponent<CheckoutPlazaCyclists>();
            life.AddComponent<CheckoutPlazaSitters>();
        }
    }
}
