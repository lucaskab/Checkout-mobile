using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using Checkout;
using MarketDay;

public static class CheckoutParkRigBuilder
{
    public static void Apply()
    {
        if(EditorApplication.isPlaying)throw new System.InvalidOperationException("Leave Play Mode first.");
        var park=Object.FindAnyObjectByType<MarketSimulation>().world.Find("City Park and Crossings/Amusement park");
        var old=park.GetComponentInChildren<Renderer>();var material=old.sharedMaterial;
        if(park.Find("Animated rides")){Materials(park.Find("Animated rides"),material);AssetDatabase.SaveAssets();return;}
        const string path="Assets/Art/Models/MapModels/AmusementPark/AmusementParkRig.fbx";
        var importer=(ModelImporter)AssetImporter.GetAtPath(path);importer.materialImportMode=ModelImporterMaterialImportMode.None;importer.importAnimation=false;importer.SaveAndReimport();
        var rig=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path));
        rig.name="Animated rides";rig.transform.SetParent(park,false);
        rig.transform.localPosition=Vector3.zero;rig.transform.localRotation=Quaternion.Euler(90,0,0);rig.transform.localScale=Vector3.one*.01f;
        Undo.RegisterCreatedObjectUndo(rig,"Rig amusement park");
        foreach(var r in park.GetComponentsInChildren<Renderer>())if(!r.transform.IsChildOf(rig.transform)){Undo.RecordObject(r,"Replace static park visual");r.enabled=false;}
        Materials(rig.transform,material);
        rig.AddComponent<CheckoutParkRides>();EditorSceneManager.SaveScene(park.gameObject.scene);AssetDatabase.SaveAssets();
    }
    static void Materials(Transform rig,Material original)
    {
        foreach(var r in rig.GetComponentsInChildren<Renderer>())
        {
            if(!r.name.StartsWith("Paint_")){r.sharedMaterial=original;continue;}
            string hex=r.name.Split('_')[1];string path="Assets/Art/Models/MapModels/AmusementPark/Ride"+hex+".mat";
            var material=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!material){ColorUtility.TryParseHtmlString("#"+hex,out var color);material=new Material(Shader.Find("Standard")){color=color};material.SetFloat("_Glossiness",.2f);AssetDatabase.CreateAsset(material,path);}
            r.sharedMaterial=material;
        }
    }
}
