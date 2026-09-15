using UnityEngine;

namespace Checkout
{
    public static class CheckoutShoppingProps
    {
        public static void SetVisible(Transform actor,bool visible)
        {
            var motion=actor.GetComponent<MarketDay.MarketCharacterAnimator>();if(motion)motion.CarryingBasket=visible;
            foreach(var renderer in actor.GetComponentsInChildren<Renderer>(true))
                if(renderer.name.EndsWith("_Prop"))renderer.enabled=visible;
        }
    }
}
