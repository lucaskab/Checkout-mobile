using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;

namespace Checkout
{
    [DefaultExecutionOrder(-200)]
    public class CheckoutCityAppearance : MonoBehaviour
    {
        public MarketCharacterAnimator[] templates;
        static readonly List<int> bag=new List<int>();
        public string Appearance {get;private set;}
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetBag(){bag.Clear();}
        void Awake(){Prepare();}
        public void Prepare()
        {
            if(Appearance!=null)return;
            if(templates==null||templates.Length==0)return;
            if(bag.Count==0){for(int i=0;i<templates.Length;i++)bag.Add(i);for(int i=bag.Count-1;i>0;i--){int j=Random.Range(0,i+1);(bag[i],bag[j])=(bag[j],bag[i]);}}
            int index=bag[bag.Count-1];bag.RemoveAt(bag.Count-1);
            var source=templates[index];var player=source.animationPlayer;
            foreach(var r in GetComponentsInChildren<Renderer>(true))r.enabled=false;
            foreach(var p in GetComponentsInChildren<Animation>(true))p.enabled=false;
            var visual=Instantiate(player.gameObject,transform);
            visual.name="City appearance "+source.name;
            visual.transform.localPosition=source.transform.InverseTransformPoint(player.transform.position);
            visual.transform.localRotation=Quaternion.Inverse(source.transform.rotation)*player.transform.rotation;
            var a=player.transform.lossyScale;var b=source.transform.lossyScale;
            visual.transform.localScale=new Vector3(a.x/b.x,a.y/b.y,a.z/b.z);
            visual.SetActive(true);var animation=visual.GetComponent<Animation>();animation.enabled=true;
            foreach(var r in visual.GetComponentsInChildren<Renderer>(true))r.enabled=!r.name.EndsWith("_Prop");
            var motion=GetComponent<MarketCharacterAnimator>();motion.animationPlayer=animation;motion.walkCycleDistance=source.walkCycleDistance;
            Appearance=source.name;CheckoutShoppingProps.SetVisible(transform,false);
        }
    }
}
