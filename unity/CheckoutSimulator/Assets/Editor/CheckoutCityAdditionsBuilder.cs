using System;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using MarketDay;

public static class CheckoutCityAdditionsBuilder
{
    public static void Apply()
    {
        if(EditorApplication.isPlaying)throw new InvalidOperationException("Leave Play Mode first.");
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        if(world.Find("City Park and Crossings"))return;
        var root=new GameObject("City Park and Crossings").transform;
        root.SetParent(world,false);root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
        Undo.RegisterCreatedObjectUndo(root.gameObject,"Add city park and crossings");
        void Place(string model,string name,Vector3 center,float size,float yaw,bool height=false)
        {
            var t=CheckoutMapModelsBuilder.Create(root,model,name,yaw);
            Bounds Measure(){var rs=t.GetComponentsInChildren<Renderer>();var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);return b;}
            var bounds=Measure();t.localScale*=size/(height?bounds.size.y:Mathf.Max(bounds.size.x,bounds.size.z));
            bounds=Measure();t.position+=new Vector3(center.x-bounds.center.x,.15f-bounds.min.y,center.z-bounds.center.z);
        }
        Place("AmusementPark","Amusement park",new Vector3(-1.75f,0,-28),14,0);
        foreach(float x in new[]{-27.5f,19.5f})foreach(float z in new[]{-11.5f,34f})
            Place("TrafficLight","Traffic signal "+x+" "+z,new Vector3(x,0,z),3.4f,180,true);
        foreach(float x in new[]{-19.5f,27.5f})foreach(float z in new[]{-19.5f,26f})
            Place("TrafficLight","Traffic signal "+x+" "+z,new Vector3(x,0,z),3.4f,0,true);
        var mat=new Material(Shader.Find("Standard")){color=new Color(.96f,.95f,.87f)};
        mat.SetFloat("_Glossiness",0);
        AssetDatabase.CreateAsset(mat,"Assets/Art/CityTiles/CrosswalkPaint.mat");
        void Crossing(float x,float z,bool alongX,float width=1.6f)
        {
            var group=new GameObject("Crosswalk "+x+" "+z).transform;group.SetParent(root,false);
            for(int i=0;i<9;i++)
            {
                var stripe=GameObject.CreatePrimitive(PrimitiveType.Cube);stripe.name="Paint stripe";stripe.transform.SetParent(group,false);
                stripe.transform.position=new Vector3(x+(alongX?(i-4)*.72f:0),.165f,z+(alongX?0:(i-4)*.72f));
                stripe.transform.localScale=alongX?new Vector3(.38f,.012f,width):new Vector3(width,.012f,.38f);
                UnityEngine.Object.DestroyImmediate(stripe.GetComponent<Collider>());
                stripe.GetComponent<Renderer>().sharedMaterial=mat;stripe.GetComponent<Renderer>().shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
            }
        }
        foreach(float x in new[]{-23.5f,23.5f})foreach(float z in new[]{-21f,-10f,24.5f,35.5f})Crossing(x,z,true);
        foreach(float z in new[]{-15.5f,30f})foreach(float x in new[]{-29f,-18f,18f,29f})Crossing(x,z,false);
        Crossing(-23.5f,-8.5f,true,2.5f);Crossing(23.5f,0,true,2.5f);Crossing(-4,30,false,2.5f);Crossing(-1.75f,-15.5f,false,2.5f);
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();
    }
}
