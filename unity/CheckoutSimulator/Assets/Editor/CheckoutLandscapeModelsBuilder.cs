using System;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class CheckoutLandscapeModelsBuilder
{
    const string AssetRoot="Assets/Art/Models/MapModels/";
    static readonly Vector2[] OldTrees={new Vector2(-16,15),new Vector2(-11,19),new Vector2(-20,-8),new Vector2(16,8),new Vector2(18,12),new Vector2(16,18),new Vector2(-16,-8),new Vector2(-9,17),new Vector2(20,-4)};
    static readonly Vector2[] NewTrees={new Vector2(-16,15),new Vector2(-11,20),new Vector2(-25,-8),new Vector2(17.5f,7),new Vector2(18,11),new Vector2(18.2f,26),new Vector2(-16,-8),new Vector2(-8,17),new Vector2(17.5f,-4)};
    static readonly float[] Planters={-7f,-4.9f,2f,4.2f,6.4f,8.25f};

    public static void Apply(Transform world)
    {
        Cow(world.Find("Anim_Cow"));
        var old=world.Find("Landscape Models");
        if(old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var root=new GameObject("Landscape Models").transform;
        root.SetParent(world,false);
        root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
        var environment=world.Find("Environment").GetComponent<MeshFilter>();
        Filter(environment,"EnvironmentWithoutTrees",p=>!OldTrees.Any(tree=>Vector2.Distance(new Vector2(p.x,p.z),tree)<2.8f));
        for(int i=0;i<NewTrees.Length;i++)
        {
            var point=NewTrees[i];
            Fit(root,"StylizedTree","Tree "+(i+1),new Vector3(point.x,.13f,point.y),new Vector3(3.65f+(i%3)*.18f,4.6f,3.8f),180f+i*43f);
        }
        // The old facade planting is part of the access mesh, outside the shop foundation.
        bool KeepPlanters(Vector3 p)=>!(p.z< -7.45f && p.z> -8.37f && p.y<1.8f && Planters.Any(x=>Mathf.Abs(p.x-x)<1.02f));
        Filter(world.Find("Building").GetComponent<MeshFilter>(),"AccessWithoutPlanters",KeepPlanters);
        Filter(environment,"EnvironmentWithoutTreesOrPlanters",KeepPlanters);
        for(int i=0;i<Planters.Length;i++)
            Fit(root,"FlowerPlanter","Entrance flowers "+(i+1),new Vector3(Planters[i],.13f,-7.95f),new Vector3(1.72f,1.15f,.86f),180f);
        foreach(float x in new[]{-5.8f,-2.5f,.8f})
            Fit(root,"FlowerPlanter","Loading garden flowers "+x,new Vector3(x,.13f,14.8f),new Vector3(2.2f,1.25f,1.1f),180f);
        Debug.Log("CHECKOUT_LANDSCAPE_MODELS_OK cow=1 trees=9 planters=9");
    }

    static void Cow(Transform root)
    {
        var old=root.Find("ReplacementVisual");
        if(old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var legacy=root.GetComponentsInChildren<Renderer>(true);
        var footprint=BoundsOf(legacy);
        foreach(var renderer in legacy) renderer.enabled=false;
        Fit(root,"Cow","ReplacementVisual",new Vector3(footprint.center.x,footprint.min.y,footprint.center.z),footprint.size,180f);
    }

    static Transform Fit(Transform root,string model,string name,Vector3 ground,Vector3 maximum,float yaw)
    {
        var visual=CheckoutMapModelsBuilder.Create(root,model,name,yaw);
        var bounds=BoundsOf(visual.GetComponentsInChildren<Renderer>());
        visual.localScale*=Mathf.Min(maximum.x/bounds.size.x,maximum.y/bounds.size.y,maximum.z/bounds.size.z);
        bounds=BoundsOf(visual.GetComponentsInChildren<Renderer>());
        visual.position+=new Vector3(ground.x-bounds.center.x,ground.y-bounds.min.y,ground.z-bounds.center.z);
        bounds=BoundsOf(visual.GetComponentsInChildren<Renderer>());
        if(Mathf.Abs(bounds.min.y-ground.y)>.01f || bounds.size.x>maximum.x+.01f || bounds.size.z>maximum.z+.01f)
            throw new InvalidOperationException("Landscape model does not fit: "+name);
        Debug.Log("CHECKOUT_LANDSCAPE_FIT "+name+" "+bounds);
        return visual;
    }

    static Bounds BoundsOf(Renderer[] renderers)
    {
        var bounds=renderers[0].bounds;
        foreach(var renderer in renderers) bounds.Encapsulate(renderer.bounds);
        return bounds;
    }

    static void Filter(MeshFilter filter,string name,Func<Vector3,bool> keep)
    {
        var mesh=UnityEngine.Object.Instantiate(filter.sharedMesh);
        var points=mesh.vertices.Select(filter.transform.TransformPoint).ToArray();
        for(int submesh=0;submesh<mesh.subMeshCount;submesh++)
        {
            var triangles=mesh.GetTriangles(submesh);
            var kept=new System.Collections.Generic.List<int>();
            for(int i=0;i<triangles.Length;i+=3)
                if(keep((points[triangles[i]]+points[triangles[i+1]]+points[triangles[i+2]])/3f))
                    kept.AddRange(new[]{triangles[i],triangles[i+1],triangles[i+2]});
            mesh.SetTriangles(kept,submesh);
        }
        string path=AssetRoot+name+".asset";
        var saved=AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if(saved) { EditorUtility.CopySerialized(mesh,saved);UnityEngine.Object.DestroyImmediate(mesh); }
        else { AssetDatabase.CreateAsset(mesh,path);saved=mesh; }
        filter.sharedMesh=saved;
    }
}
