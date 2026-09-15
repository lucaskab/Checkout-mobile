using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using MarketDay;
using Checkout;
public static class CheckoutSectorProgressBuilder
{
    public static void Apply()
    {
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        var root=world.Find("Sector Construction");
        if(!root){root=new GameObject("Sector Construction").transform;root.SetParent(world,true);root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);Undo.RegisterCreatedObjectUndo(root.gameObject,"Add locked sector construction");}
        string[] ids={"padaria","acougue","peixaria","queijaria"},models={"BakeryConstruction","ButcheryConstruction","FishConstruction","CheeseryConstruction"},workers={"Worker_Baker","Worker_Butcher","Worker_Fishmonger","Worker_Cheesemaker"};
        for(int i=0;i<ids.Length;i++)
        {
            var sector=world.Find("Sector_"+ids[i]);var renderers=sector.GetComponentsInChildren<Renderer>(true).Where(r=>r.enabled).ToArray();var bounds=renderers[0].bounds;foreach(var r in renderers)bounds.Encapsulate(r.bounds);
            var holder=root.Find(ids[i]);
            if(!holder){holder=new GameObject(ids[i]).transform;holder.SetParent(root,true);holder.position=new Vector3(bounds.center.x,bounds.min.y,bounds.center.z);}
            var previous=holder.Find("Construction visual");bool showConstruction=previous?previous.gameObject.activeSelf:!sector.gameObject.activeSelf;
            var construction=new GameObject("Construction visual").transform;construction.SetParent(holder,false);
            var model=CheckoutMapModelsBuilder.Create(construction,models[i],models[i],180);var rs=model.GetComponentsInChildren<Renderer>();var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
            model.localScale*=Mathf.Min(bounds.size.x/b.size.x,bounds.size.z/b.size.z,2.3f/b.size.y);rs=model.GetComponentsInChildren<Renderer>();b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
            model.position+=new Vector3(bounds.center.x-b.center.x,bounds.min.y-b.min.y,bounds.center.z-b.center.z);
            if(previous)Undo.DestroyObjectImmediate(previous.gameObject);
            var progress=holder.GetComponent<CheckoutSectorProgress>();if(!progress)progress=holder.gameObject.AddComponent<CheckoutSectorProgress>();Undo.RecordObject(progress,"Assign named sector construction");progress.construction=construction;progress.finished=sector;progress.worker=world.Find(workers[i]);
            // The first authoritative snapshot decides unlocked state without replaying progress.
            construction.gameObject.SetActive(showConstruction);
        }
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();
    }
}
