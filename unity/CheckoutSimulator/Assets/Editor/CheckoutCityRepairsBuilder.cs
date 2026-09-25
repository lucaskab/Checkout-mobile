using System;
using System.Linq;
using System.Collections.Generic;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CheckoutCityRepairsBuilder
{
    [MenuItem("Supermarket/Repair city circulation and lighting")]
    public static void Apply()
    {
        if(EditorApplication.isPlaying)throw new InvalidOperationException("Leave Play Mode first.");
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        var templates=world.Cast<Transform>().Where(t=>t.name.StartsWith("Customer_")).Select(t=>t.GetComponent<MarketCharacterAnimator>()).Where(t=>t&&t.animationPlayer).GroupBy(t=>t.animationPlayer.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(r=>!r.name.EndsWith("_Prop")).sharedMaterial.mainTexture.name).Select(g=>g.First()).ToArray();
        var residents=world.GetComponentsInChildren<CheckoutCityPedestrian>(true).Select(p=>p.gameObject);
        var drivers=world.GetComponentInChildren<CheckoutNeighborhoodTraffic>().cars.Select(c=>c.visitor.gameObject);
        foreach(var person in residents.Concat(drivers))
        {
            var appearance=person.GetComponent<CheckoutCityAppearance>();if(!appearance)appearance=Undo.AddComponent<CheckoutCityAppearance>(person);
            Undo.RecordObject(appearance,"Assign varied city characters");appearance.templates=templates;
        }
        foreach(string name in new[]{"Supplied City Models","City Establishments","Expansion Neighborhood"})
        {
            var group=world.Find(name);if(!group)continue;
            foreach(Transform building in group)
            {
                if(building.name.Contains("vehicle")||building.name.StartsWith("City ")||building.name.StartsWith("Neighborhood car"))continue;
                var rs=building.GetComponentsInChildren<MeshRenderer>(true);if(rs.Length==0)continue;
                Bounds Bounds(){var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);return b;}
                var before=Bounds();float yaw;
                if(Mathf.Abs(before.center.x)>25)yaw=before.center.x>0?270:90;
                else if(before.center.z>20)yaw=before.center.z>30?180:0;
                else yaw=before.center.x>0?90:270;
                Undo.RecordObject(building,"Face building toward sidewalk");building.rotation=Quaternion.Euler(-90,yaw,0);
                var after=Bounds();building.position+=new Vector3(before.center.x-after.center.x,before.min.y-after.min.y,before.center.z-after.center.z);
            }
        }
        var root=world.Find("City Circulation Repairs");
        if(!root)
        {
            root=new GameObject("City Circulation Repairs").transform;root.SetParent(world,false);root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);Undo.RegisterCreatedObjectUndo(root.gameObject,"Repair city circulation");
            var paint=AssetDatabase.LoadAssetAtPath<Material>(CheckoutCityBuilder.AssetRoot+"ParkingLayoutPaint.mat");
            var dark=Material("StreetlightMetal",new Color(.12f,.2f,.2f));
            var glow=Material("StreetlightGlow",new Color(1,.83f,.45f));glow.EnableKeyword("_EMISSION");glow.SetColor("_EmissionColor",new Color(1,.68f,.25f)*3);EditorUtility.SetDirty(glow);
            // Replace only old parking markings; keep the user's buildings and landscaping.
            foreach(var t in world.GetComponentsInChildren<Transform>(true).Where(t=>t.name.StartsWith("Parking bay")||t.name=="Parking wheel stop").ToArray())Undo.DestroyObjectImmediate(t.gameObject);
            var parking=root.gameObject.AddComponent<CheckoutParkingSpaces>();parking.spaces=new GameObject[5];
            for(int i=0;i<5;i++)
            {
                var slot=new GameObject("Parking space "+(i+1));slot.transform.SetParent(root,false);parking.spaces[i]=slot;
                float z=CheckoutCityTraffic.BayZ(i);
                foreach(float edge in new[]{-1.9f,1.9f})Box(slot.transform,"Bay line",new Vector3(-16.1f,.17f,z+edge),new Vector3(5.2f,.025f,.09f),paint);
                Box(slot.transform,"Wheel stop",new Vector3(-18.4f,.24f,z),new Vector3(.2f,.16f,2),dark);
            }
            var traffic=world.GetComponentInChildren<CheckoutCityTraffic>(true);var cars=traffic.vehicles.ToList();Undo.RecordObject(traffic,"Expand parking vehicle pool");
            while(cars.Count<5){var car=UnityEngine.Object.Instantiate(cars[cars.Count%3],cars[0].parent);car.name="Parking customer vehicle "+(cars.Count+1);car.gameObject.SetActive(false);Undo.RegisterCreatedObjectUndo(car.gameObject,"Add parking car");cars.Add(car);}traffic.vehicles=cars.ToArray();
            foreach(float x in new[]{-27.8f,27.8f})foreach(float z in new[]{-29f,-12f,5f,22f,42f})Lamp(new Vector3(x,.15f,z),Vector3.left*Mathf.Sign(x));
            foreach(float z in new[]{-19.8f,34.3f})foreach(float x in new[]{-35f,-17f,0f,17f,35f})Lamp(new Vector3(x,.15f,z),z<0?Vector3.forward:Vector3.back);
            void Lamp(Vector3 p,Vector3 towardRoad)
            {
                var pole=new GameObject("Streetlight").transform;pole.SetParent(root,false);pole.position=p;pole.rotation=Quaternion.LookRotation(towardRoad);
                Box(pole,"Pole",p+Vector3.up*2,new Vector3(.13f,4,.13f),dark);
                var arm=Box(pole,"Arm",p+Vector3.up*3.95f+towardRoad*.4f,new Vector3(.13f,.12f,.9f),dark);arm.rotation=pole.rotation;
                var head=Box(pole,"Canopy",p+Vector3.up*3.85f+towardRoad*.8f,new Vector3(.4f,.16f,.6f),dark);head.rotation=pole.rotation;
                var lens=Box(pole,"Luminous lens",p+Vector3.up*3.75f+towardRoad*.8f,new Vector3(.32f,.04f,.49f),glow);lens.rotation=pole.rotation;
                var light=new GameObject("Street spotlight").AddComponent<Light>();light.transform.SetParent(pole,false);light.transform.position=lens.position;light.transform.rotation=Quaternion.LookRotation(Vector3.down+towardRoad*.3f);
                light.type=LightType.Spot;light.color=new Color(1,.82f,.53f);light.intensity=3;light.range=8;light.spotAngle=90;light.shadows=LightShadows.None;light.renderMode=LightRenderMode.Auto;
            }
        }
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();
        Debug.Log("CITY_REPAIRS_SAVED appearances="+templates.Length);
    }
    static Material Material(string name,Color color){string path=CheckoutCityBuilder.AssetRoot+name+".mat";var material=AssetDatabase.LoadAssetAtPath<Material>(path);if(material)return material;material=new Material(Shader.Find("Standard")){color=color};AssetDatabase.CreateAsset(material,path);return material;}
    public static void RepairOriginalLights()
    {
        if(EditorApplication.isPlaying)throw new InvalidOperationException("Leave Play Mode first.");
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        var root=world.Find("City Circulation Repairs");if(root.Find("Original street lights"))return;
        var lamps=new GameObject("Original street lights").transform;lamps.SetParent(root,false);Undo.RegisterCreatedObjectUndo(lamps.gameObject,"Orient original streetlights");
        var positions=new[]{new Vector3(-27.7f,.13f,-10),new Vector3(-27.7f,.13f,8),new Vector3(-27.7f,.13f,26),new Vector3(27.7f,.13f,-9),new Vector3(27.7f,.13f,9),new Vector3(27.7f,.13f,27),new Vector3(-12,.13f,34.3f),new Vector3(12,.13f,34.3f)};
        foreach(string name in new[]{"CityMetal","CityLamp"})
        {
            var filter=world.Find("City Block/"+name).GetComponent<MeshFilter>();
            var mesh=UnityEngine.Object.Instantiate(filter.sharedMesh);var vertices=mesh.vertices;
            for(int i=0;i<vertices.Length;i++)
            {
                var p=filter.transform.TransformPoint(vertices[i]);
                foreach(var pole in positions)
                {
                    var offset=p-pole;
                    if(offset.y<3.65f||offset.y>4.2f||Mathf.Abs(offset.x)>1.2f||Mathf.Abs(offset.z)>.5f)continue;
                    var direction=pole.z>33?Vector3.back:Vector3.left*Mathf.Sign(pole.x);
                    p=pole+Quaternion.FromToRotation(Vector3.right,direction)*offset;break;
                }
                vertices[i]=filter.transform.InverseTransformPoint(p);
            }
            mesh.vertices=vertices;mesh.RecalculateBounds();mesh.RecalculateNormals();
            AssetDatabase.CreateAsset(mesh,CheckoutCityBuilder.AssetRoot+name+"RoadFacing.asset");Undo.RecordObject(filter,"Face streetlights toward road");filter.sharedMesh=mesh;
        }
        foreach(var p in positions)
        {
            var direction=p.z>33?Vector3.back:Vector3.left*Mathf.Sign(p.x);
            var light=new GameObject("Original street spotlight").AddComponent<Light>();light.transform.SetParent(lamps,false);light.transform.position=p+direction*.73f+Vector3.up*3.79f;
            light.transform.rotation=Quaternion.LookRotation(Vector3.down+direction*.3f);light.type=LightType.Spot;light.color=new Color(1,.82f,.53f);light.intensity=3;light.range=8;light.spotAngle=90;light.shadows=LightShadows.None;light.renderMode=LightRenderMode.Auto;
        }
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();
    }
    static Transform Box(Transform parent,string name,Vector3 position,Vector3 size,Material material){var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=name;go.transform.SetParent(parent,true);go.transform.position=position;go.transform.rotation=Quaternion.identity;go.transform.localScale=size;go.GetComponent<Renderer>().sharedMaterial=material;UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());return go.transform;}
}
