using System.Collections.Generic;
using UnityEngine;

namespace MarketDay
{
    // Small, deterministic motions keep the illustrated scene readable at mobile scale.
    public class MarketAmbientLife : MonoBehaviour
    {
        class Actor { public Transform root;public Vector3 home;public Quaternion rotation;public Transform[] limbs;public Quaternion[] rest;public float unitWidth; }
        Checkout.CheckoutMarketShell shell;Transform mullionL,mullionR;
        readonly List<Actor> actors=new List<Actor>();
        MarketSimulation sim;float clock;
        Checkout.CheckoutMarketLayout layout;
        public void RebaseDoors(){foreach(var actor in actors)if(actor.root.name.StartsWith("Anim_Door"))actor.home=actor.root.position;}
        void Start()
        {
            sim=GetComponent<MarketSimulation>();
            foreach(Transform t in sim.world)
            {
                if(!t.name.StartsWith("Anim_")&&!t.name.StartsWith("Worker_"))continue;
                if(t.name.Contains("Stocker"))continue;
                if(t.GetComponent<MarketDeliveryWorker>())continue;
                var limbs=new List<Transform>();
                foreach(var part in t.GetComponentsInChildren<Transform>())if(part.name.StartsWith("Arm_")||part.name.StartsWith("Leg_"))limbs.Add(part);
                var a=new Actor{root=t,home=t.position,rotation=t.rotation,limbs=limbs.ToArray(),rest=new Quaternion[limbs.Count]};
                for(int i=0;i<limbs.Count;i++)a.rest[i]=limbs[i].localRotation;
                actors.Add(a);
            }
        }
        // Inner edges of the entrance mullions (the free opening of the sliding doors), from the store shell.
        bool DoorOpening(out float left,out float right)
        {
            left=right=0;
            if(!shell){shell=FindAnyObjectByType<Checkout.CheckoutMarketShell>();if(!shell)return false;}
            if(!mullionL)mullionL=shell.transform.Find("Walls/Mullion L");if(!mullionR)mullionR=shell.transform.Find("Walls/Mullion R");
            if(!mullionL||!mullionR||!mullionL.gameObject.activeInHierarchy)return false;
            var a=mullionL.GetComponent<Renderer>().bounds;var b=mullionR.GetComponent<Renderer>().bounds;
            left=Mathf.Min(a.max.x,b.max.x);right=Mathf.Max(a.min.x,b.min.x);
            return right-left>.8f;
        }
        // Scales a door leaf along x to the given width (world metres).
        static void FitLeaf(Actor a,float width)
        {
            if(a.unitWidth<=0)
            {
                var renderers=a.root.GetComponentsInChildren<Renderer>();if(renderers.Length==0)return;
                var b=renderers[0].bounds;foreach(var r in renderers)b.Encapsulate(r.bounds);
                a.unitWidth=b.size.x/Mathf.Max(.001f,a.root.localScale.x);
            }
            var s=a.root.localScale;float x=width/Mathf.Max(.001f,a.unitWidth);
            if(Mathf.Abs(s.x-x)>.001f){s.x=x;a.root.localScale=s;}
        }
        void Update()
        {
            if(!sim||sim.Economy==null)return;clock+=Time.deltaTime*sim.speed;
            // The door moves with the shop as it grows: open for customers around its current centre.
            float doorX=0;int doors=0;foreach(var d in actors)if(d.root.name.StartsWith("Anim_Door")){doorX+=d.home.x;doors++;}
            doorX=doors>0?doorX/doors:-1.75f;
            for(int i=0;i<actors.Count;i++)
            {
                var a=actors[i];string n=a.root.name;float t=clock+i*1.73f;
                if(n.StartsWith("Anim_Door"))
                {
                    if(!layout)layout=FindAnyObjectByType<Checkout.CheckoutMarketLayout>();
                    float width=layout?layout.State.widthScale:1;
                    bool left=n.EndsWith("Left");
                    // The two glass leaves fill the opening between the mullions and meet in the middle
                    // (a hair of overlap), sliding open behind the fixed sidelights.
                    if(DoorOpening(out float edgeL,out float edgeR))
                    {
                        float mid=(edgeL+edgeR)*.5f,leaf=(edgeR-edgeL)*.5f+.03f;
                        FitLeaf(a,leaf);
                        bool nearOpening=false;foreach(Transform person in sim.world)if(person.gameObject.activeInHierarchy&&person.name.StartsWith("Customer_")&&Mathf.Abs(person.position.x-mid)<leaf*1.4f&&Mathf.Abs(person.position.z-a.home.z)<2.1f){nearOpening=true;break;}
                        float closed=left?mid-leaf*.5f+.015f:mid+leaf*.5f-.015f;
                        float open=closed+(left?-1:1)*(leaf-.06f);
                        var goal=new Vector3(nearOpening?open:closed,a.root.position.y,a.home.z);
                        a.root.position=Vector3.MoveTowards(a.root.position,goal,Time.deltaTime*2.5f*sim.speed);
                        continue;
                    }
                    bool near=false;foreach(Transform person in sim.world)if(person.gameObject.activeInHierarchy&&person.name.StartsWith("Customer_")&&Mathf.Abs(person.position.x-doorX)<1.65f*Mathf.Max(1,width)&&Mathf.Abs(person.position.z-a.home.z)<2.1f){near=true;break;}
                    a.root.position=Vector3.MoveTowards(a.root.position,a.home+Vector3.right*(near?(left?-1.32f:1.32f)*width:0),Time.deltaTime*2.5f*sim.speed);
                }
                else if(n.StartsWith("Anim_Chicken"))
                {
                    if(a.root.GetComponent<MarketChickenAnimator>())continue;
                    float step=Mathf.Max(0,Mathf.Sin(t*.7f));
                    a.root.position=a.home+new Vector3(Mathf.Sin(t*.65f)*.16f,Mathf.Abs(Mathf.Sin(t*9))*.024f*step,Mathf.Cos(t*.65f)*.14f);
                    a.root.rotation=a.rotation*Quaternion.Euler(Mathf.Min(0,Mathf.Sin(t*2))*12,Mathf.Sin(t*.65f)*25,0);
                }
                else if(n=="Anim_Cow")
                {a.root.position=a.home+Vector3.up*Mathf.Sin(t*1.6f)*.012f;a.root.rotation=a.rotation*Quaternion.Euler(0,Mathf.Sin(t*.35f)*3,Mathf.Sin(t*.8f)*.7f);}
                else if(n.StartsWith("Anim_Truck")&&sim.enabled)
                {
                    if(MarketDeliveryWorker.IsUnloading(a.root)){a.root.position=Vector3.MoveTowards(a.root.position,a.home,Time.deltaTime*2*sim.speed);continue;}
                    float incoming=0;foreach(var d in sim.Economy.departments)incoming=Mathf.Max(incoming,d.incoming>0?d.deliveryRemaining:0);
                    a.root.position=Vector3.MoveTowards(a.root.position,a.home+Vector3.forward*Mathf.Clamp(incoming-7,0,5),Time.deltaTime*2*sim.speed);
                }
                else if(n=="Worker_Delivery")
                {
                    float u=Mathf.PingPong(clock*.20f,1);Vector3 target=a.home+new Vector3(1.1f,0,1.6f)*u;
                    Vector3 direction=target-a.root.position;if(direction.sqrMagnitude>.00001f)a.root.rotation=Quaternion.Slerp(a.root.rotation,Quaternion.LookRotation(-direction),Time.deltaTime*6);
                    a.root.position=target;
                    for(int j=0;j<a.limbs.Length;j++)if(a.limbs[j].name.StartsWith("Leg"))a.limbs[j].localRotation=a.rest[j]*Quaternion.Euler(Mathf.Sin(clock*9+j*3.14f)*18,0,0);
                }
                else if(n.StartsWith("Worker_"))
                {
                    for(int j=0;j<a.limbs.Length;j++)if(a.limbs[j].name.StartsWith("Arm"))a.limbs[j].localRotation=a.rest[j]*Quaternion.Euler(Mathf.Sin(t*2.2f+j)*9,0,0);
                }
            }
        }
    }
}
