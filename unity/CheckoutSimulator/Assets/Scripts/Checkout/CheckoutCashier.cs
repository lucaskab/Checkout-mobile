using UnityEngine;
namespace Checkout
{
    public class CheckoutCashier : MonoBehaviour
    {
        public Animation player;
        public Transform item;
        public Vector3 beltStart=new Vector3(-4.65f,1.57f,-4.7f),beltEnd=new Vector3(-3.25f,1.57f,-4.7f);
        float elapsed,duration,scanDuration,scanLength;bool serving;string current;
        public float ScanDuration => scanDuration;
        public float PaymentDuration => player&&player["ReceivePayment"]!=null?player["ReceivePayment"].length:2f;
        public static int CompletedServices {get;private set;}
        public float Serve(int quantity)
        {
            elapsed=0;scanLength=player["ScanItems"].length;
            scanDuration=Mathf.Clamp(quantity,1,6)*scanLength;
            duration=scanDuration+player["ReceivePayment"].length;serving=true;
            Play("ScanItems");if(item)item.gameObject.SetActive(true);return duration;
        }
        void Play(string clip){if(current==clip)return;current=clip;player[clip].time=0;player.CrossFade(clip,.15f);}
        void OnEnable(){serving=false;current=null;if(item)item.gameObject.SetActive(false);}
        void Update()
        {
            if(!player)return;
            if(!serving){Play("Idle");return;}
            elapsed+=Time.deltaTime;
            if(elapsed<scanDuration)
            {
                Play("ScanItems");player["ScanItems"].wrapMode=WrapMode.Loop;
                if(item)item.position=Vector3.Lerp(beltStart,beltEnd,Mathf.Repeat(elapsed,scanLength)/scanLength);
            }
            else{if(item)item.gameObject.SetActive(false);Play("ReceivePayment");}
            if(elapsed>=duration){serving=false;CompletedServices++;Play("Idle");}
        }
    }
}
