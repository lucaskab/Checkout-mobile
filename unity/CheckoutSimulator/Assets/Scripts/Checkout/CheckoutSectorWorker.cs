using UnityEngine;
using MarketDay;

namespace Checkout
{
    // Ambient movement behind a sector counter. Purely visual: it never serves customers or changes the simulation.
    [DefaultExecutionOrder(200)]
    public class CheckoutSectorWorker : MonoBehaviour
    {
        public float span=.5f; // Half-width of the walkable strip behind the counter, before layout scaling.
        // A placed counter (build mode): walk along its own axes, at natural size.
        public Transform frame;
        Vector3 Right=>frame?frame.right:Vector3.right;Vector3 Back=>frame?-frame.forward:Vector3.back;
        MarketCharacterAnimator motion;CheckoutMarketLayout layout;
        Vector3 home,written;Quaternion facing=Quaternion.identity;float offset,target,wait=1;bool working;
        void OnEnable(){motion=GetComponent<MarketCharacterAnimator>();layout=FindAnyObjectByType<CheckoutMarketLayout>();home=written=transform.position;facing=transform.rotation;offset=target=0;wait=Random.Range(1f,3f);}
        void Update()
        {
            // The layout and the sector reveal place the worker at the counter; follow that home.
            if((transform.position-written).sqrMagnitude>.000001f)home=transform.position;
            if(motion&&motion.Busy&&!working){Face(Back);Place();return;}
            if(wait>0)
            {
                wait-=Time.deltaTime;
                if(wait<=0){working=false;float width=span*(frame?1:layout&&layout.State!=null?layout.State.widthScale:1);target=Random.Range(-width,width);}
            }
            else
            {
                float step=Time.deltaTime*.75f,delta=target-offset;
                if(Mathf.Abs(delta)>step){offset+=Mathf.Sign(delta)*step;Face(Right*Mathf.Sign(delta));}
                else
                {
                    offset=target;wait=Random.Range(2f,4.5f);
                    // Half of the stops are spent preparing at the back bench, the rest facing the aisle.
                    if(motion&&Random.value<.5f){Face(-Back);motion.Perform("GetFromShelf",false);working=true;}
                    else Face(Back);
                }
            }
            Place();
        }
        void Place(){transform.position=written=home+Right*offset;transform.rotation=Quaternion.RotateTowards(transform.rotation,facing,Time.deltaTime*360);}
        // The character rigs look along -forward. Customers stand towards -Z, the back bench towards +Z.
        void Face(Vector3 look){facing=Quaternion.LookRotation(-look);}
    }
}
