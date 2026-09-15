using System;
using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEngine;

public static class CheckoutDeliveryPlaytest
{
    const string Pending = "CheckoutDeliveryPlaytest.Pending";
    static float started;
    static bool carrying, emptyReturn, sawDrop;
    static int completed;
    static MarketDeliveryWorker.DeliveryPhase lastPhase;

    [MenuItem("Supermarket/Playtest delivery worker")]
    public static void Run()
    {
        CheckoutDeliveryModelsBuilder.Apply();
        ValidateSkin();
        started = 0;
        carrying = emptyReturn = sawDrop = false;
        completed = 0;
        SessionState.SetBool(Pending,true);
        EditorApplication.update -= Tick;
        EditorApplication.update += Tick;
        CheckoutMapModelsPlaytest.PreviewCurrentScene();
    }

    [InitializeOnLoadMethod]
    static void Initialize()
    {
        if (SessionState.GetBool(Pending,false)) EditorApplication.update += Tick;
    }

    static void ValidateSkin()
    {
        var worker = UnityEngine.Object.FindAnyObjectByType<MarketDeliveryWorker>();
        var body = worker.GetComponentInChildren<SkinnedMeshRenderer>();
        var mesh = new Mesh();
        foreach (string name in new[] { "Idle","Walking","CarryWalking","Pickup","PutDown" })
        {
            var clip = worker.animationPlayer[name].clip;
            clip.SampleAnimation(worker.animationPlayer.gameObject,0);
            body.BakeMesh(mesh);
            var before = mesh.vertices;
            clip.SampleAnimation(worker.animationPlayer.gameObject,clip.length*.35f);
            body.BakeMesh(mesh);
            if (!mesh.vertices.Where((v,i)=>(v-before[i]).sqrMagnitude>.000001f).Any()) throw new Exception("Delivery clip has no skin deformation: "+name);
            if (mesh.vertices.Any(v=>!float.IsFinite(v.x)||!float.IsFinite(v.y)||!float.IsFinite(v.z)) || mesh.bounds.size.magnitude>4) throw new Exception("Invalid delivery skin: "+name);
        }
        worker.animationPlayer["Idle"].clip.SampleAnimation(worker.animationPlayer.gameObject,0);
        var feet = worker.GetComponentsInChildren<Transform>().Where(t=>t.name.StartsWith("Foot_")).ToArray();
        var rest = feet.Select(t=>t.position).ToArray();
        worker.animationPlayer["PutDown"].clip.SampleAnimation(worker.animationPlayer.gameObject,worker.animationPlayer["PutDown"].length*.65f);
        for(int i=0;i<feet.Length;i++) if(Vector3.Distance(feet[i].position,rest[i])>.06f) throw new Exception("Delivery foot moved during crouch: "+feet[i].name+" "+Vector3.Distance(feet[i].position,rest[i]));
        worker.animationPlayer["Idle"].clip.SampleAnimation(worker.animationPlayer.gameObject,0);
        UnityEngine.Object.DestroyImmediate(mesh);
        Debug.Log("CHECKOUT_DELIVERY_SKIN_OK clips=5 feet=grounded");
    }

    static void Tick()
    {
        if (!EditorApplication.isPlaying || EditorApplication.isCompiling) return;
        try
        {
            var worker = UnityEngine.Object.FindAnyObjectByType<MarketDeliveryWorker>();
            if (!worker) return;
            if (started == 0) { started=Time.time;lastPhase=worker.Phase; }
            if(Time.time-started>95) throw new Exception("Delivery did not complete two trips.");
            if(worker.Phase!=lastPhase)
            {
                Debug.Log("DELIVERY_PHASE "+worker.Phase+" position="+worker.transform.position);
                lastPhase=worker.Phase;
            }
            if(worker.Phase==MarketDeliveryWorker.DeliveryPhase.ToStorage && worker.Carrying && !carrying)
            {
                carrying=true;
                Capture(worker,"/tmp/checkout-delivery-carry.png");
            }
            if(worker.Carrying)
            {
                if(worker.cargo.parent!=worker.transform) throw new Exception("Carried box detached from worker.");
                if(Vector3.Distance(worker.truck.position,worker.truckHome)>.06f) throw new Exception("Truck moved during unloading.");
            }
            var world=worker.transform.parent;
            foreach(Transform truck in world)
            {
                if(!truck.name.StartsWith("Anim_Truck"))continue;
                var bounds=truck.Find("ReplacementVisual").GetComponentInChildren<Renderer>().bounds;
                var point=worker.transform.position;
                if(point.x>bounds.min.x-.3f && point.x<bounds.max.x+.3f && point.z>bounds.min.z-.3f && point.z<bounds.max.z+.3f) throw new Exception("Delivery route intersects truck: "+truck.name);
            }
            if(worker.CompletedDeliveries>completed)
            {
                completed=worker.CompletedDeliveries;
                if(Vector3.Distance(worker.LastDropPosition,worker.storageDoor.position)>.01f || worker.Carrying || worker.cargo.parent==worker.transform || worker.cargo.gameObject.activeSelf) throw new Exception("Box was not stored after the unload.");
                sawDrop=true;
                Capture(worker,"/tmp/checkout-delivery-drop.png");
                Debug.Log("DELIVERY_DROP_OK count="+completed+" position="+worker.LastDropPosition);
            }
            if(completed>0 && worker.Phase==MarketDeliveryWorker.DeliveryPhase.ToTruck && !worker.Carrying)emptyReturn=true;
            if(completed>=2 && carrying && emptyReturn && sawDrop)
            {
                Debug.Log("CHECKOUT_DELIVERY_PLAYTEST_OK deliveries=2 emptyReturn=true truckHeld=true cargoHiddenAtStorage=true");
                Finish();
            }
        }
        catch(Exception error){Debug.LogException(error);Finish();}
    }

    static void Capture(MarketDeliveryWorker worker,string path)
    {
        var camera=Camera.main;
        var position=camera.transform.position;var rotation=camera.transform.rotation;float size=camera.orthographicSize;
        camera.orthographicSize=5;
        camera.transform.position=worker.transform.position+new Vector3(7,7,-10);
        camera.transform.LookAt(worker.transform.position+Vector3.up*.9f);
        MarketBuilder.Capture(path);
        camera.transform.SetPositionAndRotation(position,rotation);camera.orthographicSize=size;
    }

    static void Finish(){SessionState.SetBool(Pending,false);EditorApplication.update-=Tick;}
}
