using UnityEngine;
namespace Checkout
{
    public class CheckoutSectorProgress : MonoBehaviour
    {
        public Transform construction,finished,worker;
        Vector3 constructionScale,finishedHome,workerHome;
        bool initialized,unlocked,animating;
        float elapsed;
        public bool IsRevealing=>animating;
        public int RevealCount {get;private set;}
        void Awake(){Cache();}
        void Cache(){if(initialized)return;initialized=true;constructionScale=construction.localScale;finishedHome=finished.position;if(worker)workerHome=worker.position;}
        public void Apply(bool next,bool animate)
        {
            Cache();
            if(next==unlocked&&animate)return;
            bool reveal=animate&&!unlocked&&next;
            unlocked=next;animating=reveal;elapsed=0;
            if(reveal){RevealCount++;construction.gameObject.SetActive(true);finished.gameObject.SetActive(false);if(worker)worker.gameObject.SetActive(false);}
            else Settle();
        }
        void Settle()
        {
            construction.localScale=constructionScale;construction.gameObject.SetActive(!unlocked);
            finished.position=finishedHome;finished.gameObject.SetActive(unlocked);
            if(worker){worker.position=workerHome;worker.gameObject.SetActive(unlocked);}
        }
        void Update()
        {
            if(!animating)return;elapsed+=Time.deltaTime;
            float removal=Mathf.SmoothStep(0,1,Mathf.Clamp01(elapsed/.6f));
            construction.localScale=constructionScale*Mathf.Max(.001f,1-removal);
            if(elapsed>=.6f)
            {
                construction.gameObject.SetActive(false);finished.gameObject.SetActive(true);
                float rise=Mathf.Clamp01((elapsed-.6f)/.8f);
                finished.position=finishedHome+Vector3.down*(.55f*(1-Mathf.SmoothStep(0,1,rise)));
            }
            if(elapsed>=1.4f){animating=false;Settle();}
        }
    }
}
