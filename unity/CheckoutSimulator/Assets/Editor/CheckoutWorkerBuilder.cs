using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using MarketDay;

// Meshy worker meshes are bound offline to the existing gameplay animation clips.
public static class CheckoutWorkerBuilder {
 const string Folder="Assets/Art/Characters/Meshy/Workers/";
 static readonly string[] Workers={"Worker_Baker","Worker_Butcher","Worker_Fishmonger"};
 static readonly string[] Clips={"Idle","Walking","GetFromShelf","BuyAtSpecialSector","PayAtCheckout"};
 [MenuItem("Supermarket/Apply Meshy workers to current scene")]
 public static void Apply(){
  EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
  ApplyToWorld(UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world);
  EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());AssetDatabase.SaveAssets();
  Debug.Log("CHECKOUT_WORKERS_OK");
 }
 public static void ApplyToWorld(Transform world){
  foreach(var name in Workers){
   var textureImporter=(TextureImporter)AssetImporter.GetAtPath(Folder+name+".png");
   if(!textureImporter)throw new Exception("Missing Meshy worker texture: "+name);
   textureImporter.sRGBTexture=true;textureImporter.mipmapEnabled=true;textureImporter.maxTextureSize=2048;textureImporter.SaveAndReimport();
   var material=AssetDatabase.LoadAssetAtPath<Material>(Folder+name+".mat");
   if(!material){material=new Material(Shader.Find("MarketDay/Soft Painted"));AssetDatabase.CreateAsset(material,Folder+name+".mat");}
   material.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>(Folder+name+".png");material.SetFloat("_Outline",.35f);EditorUtility.SetDirty(material);
   var actor=world.Find(name);if(!actor)throw new Exception("Missing market worker: "+name);
   string path=Folder+name+".fbx";var importer=(ModelImporter)AssetImporter.GetAtPath(path);
   if(!importer)throw new Exception("Missing Meshy worker: "+path);
   importer.animationType=ModelImporterAnimationType.Legacy;importer.importAnimation=true;importer.importCameras=false;importer.importLights=false;importer.materialImportMode=ModelImporterMaterialImportMode.None;importer.animationCompression=ModelImporterAnimationCompression.Off;
   var clips=importer.defaultClipAnimations;
   foreach(var clip in clips){foreach(var logical in Clips)if(clip.name.EndsWith(logical))clip.name=logical;clip.loopTime=clip.name=="Idle"||clip.name=="Walking";clip.wrapMode=clip.loopTime?WrapMode.Loop:WrapMode.ClampForever;}
   importer.clipAnimations=clips;importer.SaveAndReimport();
   var old=actor.Find("Visual");
   var visual=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path),actor);visual.name="Visual";visual.transform.localPosition=Vector3.zero;visual.transform.localRotation=Quaternion.Euler(0,180,0);
   var player=visual.GetComponent<Animation>();if(!player)player=visual.AddComponent<Animation>();
   foreach(var clip in AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(clip=>!clip.name.StartsWith("__preview__")))player.AddClip(clip,clip.name);
   foreach(var logical in Clips)if(!player[logical])throw new Exception("Missing Meshy worker clip: "+name+" / "+logical);
   player.playAutomatically=false;player.cullingType=AnimationCullingType.AlwaysAnimate;
   foreach(var renderer in visual.GetComponentsInChildren<Renderer>())renderer.sharedMaterials=Enumerable.Repeat(material,renderer.sharedMaterials.Length).ToArray();
   actor.GetComponent<MarketCharacterAnimator>().animationPlayer=player;
   if(old)UnityEngine.Object.DestroyImmediate(old.gameObject);
  }
 }
 public static void Validate(){
  EditorSceneManager.OpenScene(MarketBuilder.ScenePath);int checks=0;var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
  foreach(var name in Workers){
   var actor=world.Find(name);var player=actor.GetComponent<MarketCharacterAnimator>().animationPlayer;
   var body=player.GetComponentsInChildren<SkinnedMeshRenderer>().Single(renderer=>renderer.name.StartsWith(name+"_MeshyBody"));
   if(!body.sharedMaterial.mainTexture||body.sharedMesh.vertexCount>40000)throw new Exception("Invalid worker mesh/material: "+name);
   foreach(var clipName in Clips){var clip=player[clipName].clip;var original=AssetDatabase.LoadAllAssetsAtPath("Assets/Art/Characters/"+name+".fbx").OfType<AnimationClip>().Single(candidate=>candidate.name==clipName);if(Mathf.Abs(clip.length-original.length)>.05f)throw new Exception("Worker clip duration changed: "+name+" / "+clipName);
    var mesh=new Mesh();clip.SampleAnimation(player.gameObject,0);body.BakeMesh(mesh);var start=mesh.vertices;
    clip.SampleAnimation(player.gameObject,clip.length*.35f);body.BakeMesh(mesh);var end=mesh.vertices;
    if(!end.Where((position,index)=>(position-start[index]).sqrMagnitude>.000001f).Any())throw new Exception("Static worker skin: "+name+" / "+clipName);
    if(mesh.bounds.size.magnitude>5||end.Any(position=>float.IsNaN(position.x)))throw new Exception("Invalid worker deformation: "+name+" / "+clipName);
    UnityEngine.Object.DestroyImmediate(mesh);checks++;
   }
  }
  Debug.Log("CHECKOUT_WORKER_VALIDATION_OK "+checks+" animated skins");
 }
}
