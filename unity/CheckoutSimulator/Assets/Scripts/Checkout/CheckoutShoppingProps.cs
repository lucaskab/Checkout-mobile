using UnityEngine;

namespace Checkout
{
    public static class CheckoutShoppingProps
    {
        public static void SetVisible(Transform actor,bool visible)
        {
            var motion=actor.GetComponent<MarketDay.MarketCharacterAnimator>();if(motion)motion.CarryingBasket=visible;
            // Real cart/basket models held by the character (the skinned props of the FBX stay hidden).
            CheckoutShopperRig.For(actor).SetVisible(visible);
        }
    }
}
