using UnityEngine;

namespace MarketDay
{
    // The Blender clips own the skeleton; navigation owns only the world transform.
    public class MarketCharacterAnimator : MonoBehaviour
    {
        public Animation animationPlayer;
        public bool CarryingBasket {get;set;}
        public float walkCycleDistance=.733f;
        Vector3 previous; float walkPhase; string current; float actionRemaining;
        MarketSimulation simulation; GameObject handledItem; float actionLength;
        public static int shelfActions, sectorActions, paymentActions;
        void OnEnable(){
            // Cloned customers can retain an older supplied GLB beside the selected rig.
            // Only the explicitly assigned visual owns body rendering and animation.
            if(animationPlayer&&name.StartsWith("Customer_")){
                foreach(var renderer in GetComponentsInChildren<Renderer>(true))
                    if(!renderer.transform.IsChildOf(animationPlayer.transform))renderer.enabled=false;
                foreach(var player in GetComponentsInChildren<Animation>(true))
                    if(player!=animationPlayer)player.enabled=false;
                animationPlayer.gameObject.SetActive(true);
                animationPlayer.enabled=true;
            }
            previous=transform.position;current=null;actionRemaining=0;}
        void Start(){simulation=FindAnyObjectByType<MarketSimulation>();if(!animationPlayer)animationPlayer=GetComponentInChildren<Animation>();}
        public float Perform(string clip)
        {
            if(!animationPlayer||!animationPlayer[clip]){Debug.LogError("Missing character clip: "+name+" / "+clip);return 2;}
            if(clip=="GetFromShelf")shelfActions++;if(clip=="BuyAtSpecialSector")sectorActions++;if(clip=="PayAtCheckout")paymentActions++;
            current=clip;animationPlayer[clip].time=0;animationPlayer.CrossFade(clip,.16f);
            actionRemaining=actionLength=animationPlayer[clip].length;
            if(!handledItem)
            {
                Transform hand=null;foreach(var t in animationPlayer.GetComponentsInChildren<Transform>())if(t.name=="Hand_R"){hand=t;break;}
                if(hand){handledItem=GameObject.CreatePrimitive(PrimitiveType.Cube);handledItem.name="Handled purchase";Destroy(handledItem.GetComponent<Collider>());handledItem.transform.SetParent(hand,false);handledItem.transform.localPosition=new Vector3(0,.025f/hand.lossyScale.y,-.055f/hand.lossyScale.z);var material=new Material(Shader.Find("Sprites/Default"));material.color=new Color(.96f,.72f,.28f);handledItem.GetComponent<Renderer>().material=material;}
            }
            if(handledItem){var size=clip=="PayAtCheckout"?new Vector3(.12f,.075f,.012f):new Vector3(.14f,.18f,.10f);var scale=handledItem.transform.parent.lossyScale;handledItem.transform.localScale=new Vector3(size.x/scale.x,size.y/scale.y,size.z/scale.z);handledItem.SetActive(false);}
            return actionRemaining;
        }
        void LateUpdate()
        {
            if(!animationPlayer)return;
            float rate=simulation?simulation.speed:1;
            Vector3 delta=transform.position-previous;delta.y=0;previous=transform.position;
            if(actionRemaining>0){actionRemaining-=Time.deltaTime*rate;animationPlayer[current].speed=rate;if(handledItem)handledItem.SetActive(actionRemaining<actionLength*.65f&&actionRemaining>actionLength*.15f);return;}
            if(handledItem)handledItem.SetActive(false);
            float velocity=delta.magnitude/Mathf.Max(Time.deltaTime,.001f);
            string next=velocity>.06f?(CarryingBasket&&animationPlayer["WalkingWithBasket"]!=null?"WalkingWithBasket":"Walking"):"Idle";
            if(current!=next){current=next;animationPlayer.CrossFade(next,.18f);}
            if(animationPlayer[next]){
                if(next.StartsWith("Walking")){
                    if(delta.magnitude<2)walkPhase=Mathf.Repeat(walkPhase+delta.magnitude/Mathf.Max(.1f,walkCycleDistance),1f);
                    animationPlayer[next].speed=0;
                    animationPlayer[next].normalizedTime=walkPhase;
                    animationPlayer.Sample();
                }else animationPlayer[next].speed=rate;
            }
        }
    }
}
