using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CheckoutExpansionAmenitiesBuilder
{
    [MenuItem("Supermarket/Prepare expansion park")]
    public static void Apply()
    {
        if(EditorApplication.isPlaying)throw new System.InvalidOperationException("Leave Play Mode first.");
        var world=Object.FindAnyObjectByType<MarketSimulation>().world;
        if(world.Find("Expansion Park"))return;
        var root=new GameObject("Expansion Park").transform;
        root.SetParent(world,true);root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
        Undo.RegisterCreatedObjectUndo(root.gameObject,"Create premium expansion park");
        Place(root,"PlaygroundForge",new Vector3(-13.5f,.15f,20),new Vector3(4.3f,3.5f,4));
        Place(root,"Sandbox",new Vector3(-17f,.15f,20),new Vector3(2.4f,1.2f,2.4f));
        root.gameObject.SetActive(false);
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);
        EditorSceneManager.SaveScene(world.gameObject.scene);
    }
    static void Place(Transform root,string model,Vector3 position,Vector3 size)
    {
        var item=CheckoutMapModelsBuilder.Create(root,model,model,180);
        Bounds Bounds(){var renderers=item.GetComponentsInChildren<Renderer>();var bounds=renderers[0].bounds;foreach(var r in renderers.Skip(1))bounds.Encapsulate(r.bounds);return bounds;}
        var b=Bounds();item.localScale*=Mathf.Min(size.x/b.size.x,size.y/b.size.y,size.z/b.size.z);
        b=Bounds();item.position+=new Vector3(position.x-b.center.x,position.y-b.min.y,position.z-b.center.z);
    }
}
