using UnityEngine;
using System.Linq;

namespace Checkout
{
    public class CheckoutParkRides : MonoBehaviour
    {
        Transform wheel,carousel;
        Transform[] cabins,horses,swings;
        Quaternion wheelRest,carouselRest;
        Quaternion[] cabinRest,swingRest;
        Vector3[] horseRest;
        Vector3 wheelAxis,carouselAxis;
        Vector3[] swingAxes;
        void Awake()
        {
            var parts=GetComponentsInChildren<Transform>();
            wheel=parts.First(t=>t.name=="Ride_Wheel");carousel=parts.First(t=>t.name=="Ride_Carousel");
            cabins=parts.Where(t=>t.name.StartsWith("Ride_Cabin_")).ToArray();
            horses=parts.Where(t=>t.name.StartsWith("Ride_Horse_")).ToArray();
            swings=parts.Where(t=>t.name.StartsWith("Ride_Swing_")).ToArray();
            wheelRest=wheel.localRotation;carouselRest=carousel.localRotation;
            wheelAxis=Axis(wheel);carouselAxis=Axis(carousel);
            cabinRest=cabins.Select(t=>t.localRotation).ToArray();swingRest=swings.Select(t=>t.localRotation).ToArray();
            horseRest=horses.Select(t=>t.localPosition).ToArray();swingAxes=swings.Select(Axis).ToArray();
        }
        static Vector3 Axis(Transform pivot)=>pivot.Cast<Transform>().First(t=>t.name.StartsWith("Axis")).localPosition.normalized;
        void Update()=>Pose(Time.time);
        public void Pose(float seconds)
        {
            if(!wheel)return;
            float angle=seconds*9;
            wheel.localRotation=wheelRest*Quaternion.AngleAxis(angle,wheelAxis);
            carousel.localRotation=carouselRest*Quaternion.AngleAxis(seconds*18,carouselAxis);
            for(int i=0;i<cabins.Length;i++)cabins[i].localRotation=Quaternion.AngleAxis(-angle,wheelAxis)*cabinRest[i];
            float lift=carousel.Cast<Transform>().First(t=>t.name.StartsWith("Axis")).localPosition.magnitude*.009f;
            for(int i=0;i<horses.Length;i++)horses[i].localPosition=horseRest[i]+carouselAxis*(Mathf.Sin(seconds*3.4f+i*Mathf.PI*.5f)*lift);
            for(int i=0;i<swings.Length;i++)swings[i].localRotation=swingRest[i]*Quaternion.AngleAxis(Mathf.Sin(seconds*2.2f+i*.8f)*16,swingAxes[i]);
        }
    }
}
