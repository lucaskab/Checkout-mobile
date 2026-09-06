using System.Collections.Generic;
using UnityEngine;

namespace MarketDay
{
    // Foot trajectories are distance driven. Two-bone IK keeps stance feet on the floor.
    public class MarketCharacterMotion : MonoBehaviour
    {
        class Joint { public Transform t;public Quaternion rest,rootRelative;public Vector3 position; }
        readonly Dictionary<string,Joint> joints=new Dictionary<string,Joint>();
        Vector3 previous;float phase,blend;bool initialized;
        public string carryStyle="free";
        public bool counterWorker;
        public void Initialize()
        {
            if(initialized)return;initialized=true;previous=transform.position;
            foreach(var t in GetComponentsInChildren<Transform>())
                if(t!=transform&&!t.name.EndsWith("_Mesh")&&!joints.ContainsKey(t.name))joints[t.name]=new Joint{t=t,rest=t.localRotation,rootRelative=Quaternion.Inverse(transform.rotation)*t.rotation,position=t.localPosition};
        }
        void Start(){Initialize();}
        void Rotate(string name,float pitch,float yaw=0,float roll=0)
        {
            if(!joints.TryGetValue(name,out var j))return;
            var axis=j.t.parent.InverseTransformDirection(transform.right);
            var up=j.t.parent.InverseTransformDirection(Vector3.up);
            var forward=j.t.parent.InverseTransformDirection(transform.forward);
            j.t.localRotation=Quaternion.AngleAxis(roll,forward)*Quaternion.AngleAxis(yaw,up)*Quaternion.AngleAxis(pitch,axis)*j.rest;
        }
        void LateUpdate()
        {
            Initialize();float dt=Time.deltaTime;if(dt<=0)return;
            Vector3 delta=transform.position-previous;previous=transform.position;delta.y=0;
            float distance=delta.magnitude;float speed=distance/dt;
            bool moving=distance>.0002f&&distance<.2f;
            blend=Mathf.MoveTowards(blend,moving?Mathf.Clamp01(speed/.65f):0,dt*6);
            if(moving)phase+=distance/1.0f*Mathf.PI*2;
            foreach(var j in joints.Values){j.t.localPosition=j.position;j.t.localRotation=j.rest;}
            if(carryStyle=="cart")
            {
                Vector3 ahead=transform.position-transform.forward;
                float slope=Mathf.Atan2(MarketSimulation.Ground(ahead.z)-MarketSimulation.Ground(transform.position.z),1)*Mathf.Rad2Deg;
                Rotate("Prop",slope);
            }
            // Breathing and weight transfer are subtle, not whole-character hopping.
            if(joints.TryGetValue("Torso",out var torso))torso.t.position+=Vector3.up*((Mathf.Sin(phase*2)*.012f-.065f)*blend+Mathf.Sin(Time.time*2)*.003f);
            Rotate("Torso",carryStyle=="cart"?-3*blend:0,Mathf.Sin(phase)*2*blend,Mathf.Sin(phase)*1.3f*blend);
            Rotate("Head",0,Mathf.Sin(Time.time*.75f)*3*(1-blend));
            for(int side=0;side<2;side++)
            {
                string suffix=side==0?"L":"R";float cycle=Mathf.Repeat(phase/Mathf.PI/2+side*.5f,1);
                float stride=.30f*blend;float forward,lift;
                if(cycle<.6f){forward=Mathf.Lerp(stride,-stride,cycle/.6f);lift=0;}
                else{float u=(cycle-.6f)/.4f;forward=Mathf.Lerp(-stride,stride,u*u*(3-2*u));lift=Mathf.Sin(u*Mathf.PI)*.105f*blend;}
                SolveLeg(suffix,forward,lift);
                float swing=Mathf.Sin(phase+side*Mathf.PI)*17*blend;
                if(carryStyle=="free"||(carryStyle=="basket"&&side==0))
                {Rotate("UpperArm_"+suffix,-swing);Rotate("Forearm_"+suffix,-5-Mathf.Max(0,swing)*.4f);}
                else {Rotate("UpperArm_"+suffix,0);Rotate("Forearm_"+suffix,0);}
                if(counterWorker&&blend<.05f){Rotate("UpperArm_"+suffix,8);Rotate("Forearm_"+suffix,22+Mathf.Sin(Time.time*1.7f+side)*8);}
            }
        }
        void SolveLeg(string side,float forward,float lift)
        {
            if(!joints.TryGetValue("Thigh_"+side,out var upper)||!joints.TryGetValue("Shin_"+side,out var lower)||!joints.TryGetValue("Foot_"+side,out var foot))return;
            Vector3 hip=upper.t.position,knee=lower.t.position,ankle=foot.t.position;
            Quaternion levelFoot=transform.rotation*foot.rootRelative;
            float a=Vector3.Distance(hip,knee),b=Vector3.Distance(knee,ankle);
            Vector3 target=ankle-transform.forward*forward;target.y=transform.position.y+.105f+lift;
            Vector3 direction=target-hip;float distance=Mathf.Clamp(direction.magnitude,.05f,a+b-.001f);direction.Normalize();
            float along=(a*a-b*b+distance*distance)/(2*distance);
            Vector3 bend=Vector3.ProjectOnPlane(-transform.forward,direction).normalized;
            Vector3 desiredKnee=hip+direction*along+bend*Mathf.Sqrt(Mathf.Max(0,a*a-along*along));
            upper.t.rotation=Quaternion.FromToRotation(knee-hip,desiredKnee-hip)*upper.t.rotation;
            lower.t.rotation=Quaternion.FromToRotation(foot.t.position-lower.t.position,target-lower.t.position)*lower.t.rotation;
            foot.t.rotation=levelFoot;
        }
    }
}
