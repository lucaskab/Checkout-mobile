using System.Linq;
using UnityEngine;
namespace Checkout
{
    public class CheckoutShelfSlots : MonoBehaviour
    {
        public static readonly string[] Ids={"produce","dairy","bakery","snacks","drinks","coffee","pizza","home","icecream"};
        public static readonly Vector3[] Positions={P(-6,.5f),P(-2,.5f),P(2,.5f),P(6,.5f),P(-6,-2.2f),P(0,-2.2f),P(4,-2.2f),P(-6,3.2f),P(6,3.2f)};
        static Vector3 P(float x,float z)=>new Vector3(x,.74f,z);
        public static Vector3 Position(string id){int i=System.Array.IndexOf(Ids,id);return i>=0?Positions[i]:P(0,0);}
        public void Apply(Shelf[] shelves)
        {
            foreach(Transform slot in transform)
            {
                var shelf=shelves.FirstOrDefault(s=>s.id==slot.name);slot.gameObject.SetActive(shelf!=null&&shelf.unlocked);
                if(shelf==null)continue;
                string category=(shelf.category??"").ToLowerInvariant();
                string model=category.Contains("bebida")||category.Contains("drink")||category=="refrigerantes"||category=="aguas"||(category.Length==0&&shelf.id=="drinks")?"BeverageShelf":category.Contains("higiene")||category.Contains("limpeza")||category=="hortifruti"||(category.Length==0&&shelf.id=="produce")?"GroceryDisplay":"GroceryShelf";
                foreach(Transform variant in slot)variant.gameObject.SetActive(variant.name==model);
            }
        }
    }
}
