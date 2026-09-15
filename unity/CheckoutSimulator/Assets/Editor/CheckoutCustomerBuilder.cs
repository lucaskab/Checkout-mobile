using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using MarketDay;

// Meshy is converted offline so player builds need no GLB loader or retargeting.
public static class CheckoutCustomerBuilder {
 const string Folder="Assets/Art/Characters/Meshy/";
 static readonly string[] Clips={"Idle","Walking","WalkingWithBasket","GetFromShelf","BuyAtSpecialSector","PayAtCheckout"};
 static readonly string[,] AddedCustomers={{"Customer_06","Customer_01"},{"Customer_07","Customer_02"},{"Customer_08","Customer_03"},{"Customer_09","Customer_04"}};
 [MenuItem("Supermarket/Apply Meshy customers to current scene")]
 public static void Apply(){
  EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
  ApplyToWorld(UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world);
  EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());AssetDatabase.SaveAssets();
  Debug.Log("CHECKOUT_CUSTOMERS_OK");
 }
 public static void ApplyToWorld(Transform world){
  EnsureAddedCustomers(world);
  foreach(Transform actor in world){
   if(!actor.name.StartsWith("Customer_"))continue;
   string appearance=Appearance(actor.name);
   var textureImporter=(TextureImporter)AssetImporter.GetAtPath(Folder+appearance+".png");
   textureImporter.sRGBTexture=true;textureImporter.mipmapEnabled=true;textureImporter.maxTextureSize=2048;textureImporter.SaveAndReimport();
   var material=AssetDatabase.LoadAssetAtPath<Material>(Folder+appearance+".mat");
   if(!material){material=new Material(Shader.Find("MarketDay/Soft Painted"));AssetDatabase.CreateAsset(material,Folder+appearance+".mat");}
   material.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>(Folder+appearance+".png");material.SetFloat("_Outline",.35f);EditorUtility.SetDirty(material);
   string path=Folder+actor.name+".fbx";
   var importer=(ModelImporter)AssetImporter.GetAtPath(path);
   if(!importer)throw new Exception("Missing Meshy character: "+path);
   importer.animationType=ModelImporterAnimationType.Legacy;importer.importAnimation=true;importer.importCameras=false;importer.importLights=false;importer.materialImportMode=ModelImporterMaterialImportMode.None;importer.animationCompression=ModelImporterAnimationCompression.Off;
   var clips=importer.defaultClipAnimations;
   foreach(var clip in clips){foreach(var name in Clips)if(clip.name.EndsWith(name))clip.name=name;clip.loopTime=clip.name=="Idle"||clip.name.StartsWith("Walking");clip.wrapMode=clip.loopTime?WrapMode.Loop:WrapMode.ClampForever;}
   importer.clipAnimations=clips;importer.SaveAndReimport();
   var old=actor.Find("Visual");
   var visual=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path),actor);visual.name="Visual";visual.transform.localPosition=Vector3.zero;visual.transform.localRotation=Quaternion.Euler(0,180,0);
   var player=visual.GetComponent<Animation>();if(!player)player=visual.AddComponent<Animation>();
   foreach(var clip in AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(c=>!c.name.StartsWith("__preview__")))player.AddClip(clip,clip.name);
   foreach(var name in Clips)if(!player[name])throw new Exception("Missing Meshy clip: "+actor.name+" / "+name);
   player.playAutomatically=false;player.cullingType=AnimationCullingType.AlwaysAnimate;
   foreach(var renderer in visual.GetComponentsInChildren<Renderer>())renderer.sharedMaterials=Enumerable.Repeat(renderer.name.EndsWith("_Prop")?AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Materials/MarketPaint.mat"):material,renderer.sharedMaterials.Length).ToArray();
   actor.GetComponent<MarketCharacterAnimator>().animationPlayer=player;
   var foot=visual.GetComponentsInChildren<Transform>().First(t=>t.name=="Foot_L");
   float min=float.MaxValue,max=float.MinValue;var walk=player["Walking"].clip;
   for(int frame=0;frame<24;frame++){walk.SampleAnimation(visual,walk.length*frame/24f);float z=visual.transform.InverseTransformPoint(foot.position).z;min=Mathf.Min(min,z);max=Mathf.Max(max,z);}
   actor.GetComponent<MarketCharacterAnimator>().walkCycleDistance=Mathf.Max(.1f,(max-min)*2*Mathf.Abs(visual.transform.lossyScale.z));
   player["Idle"].clip.SampleAnimation(visual,0);
   // Preserve unrelated actor components while retiring every older model root.
   foreach(Transform child in actor)if(child!=visual.transform&&child.GetComponentsInChildren<Renderer>(true).Length>0){Undo.RecordObject(child.gameObject,"Retire previous customer visual");child.gameObject.SetActive(false);}
   if(old)UnityEngine.Object.DestroyImmediate(old.gameObject);
  }
 }
 static void EnsureAddedCustomers(Transform world){
  for(int i=0;i<AddedCustomers.GetLength(0);i++){string name=AddedCustomers[i,0],sourceName=AddedCustomers[i,1];if(world.Find(name))continue;var source=world.Find(sourceName);if(!source)throw new Exception("Missing customer rig source: "+sourceName);var actor=UnityEngine.Object.Instantiate(source.gameObject,world).transform;actor.name=name;actor.SetPositionAndRotation(source.position,source.rotation);}
 }
 static string Appearance(string name)=>name=="Customer_06"||name=="Customer_07"||name=="Customer_08"||name=="Customer_09"?name:"CustomerChild";
 static string RigSource(string name)=>name=="Customer_06"?"Customer_01":name=="Customer_07"?"Customer_02":name=="Customer_08"?"Customer_03":name=="Customer_09"?"Customer_04":name;
 public static void CapturePoses(){
  Validate();
  EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
  var source=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world.Find("Customer_02").GetComponent<MarketCharacterAnimator>().animationPlayer.gameObject;
  var preview=EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Additive);UnityEngine.SceneManagement.SceneManager.SetActiveScene(preview);
  var template=UnityEngine.Object.Instantiate(source);EditorSceneManager.CloseScene(source.scene,true);
  for(int i=0;i<Clips.Length;i++){var wrapper=new GameObject(Clips[i]);wrapper.transform.position=new Vector3((i-2)*1.6f,0,0);var actor=UnityEngine.Object.Instantiate(template,wrapper.transform);actor.transform.localPosition=Vector3.zero;actor.transform.localRotation=Quaternion.Euler(0,180,0);var player=actor.GetComponent<Animation>();player[Clips[i]].clip.SampleAnimation(actor,player[Clips[i]].length*.5f);}
  UnityEngine.Object.DestroyImmediate(template);
  var camera=Camera.main;camera.orthographic=true;camera.orthographicSize=2.8f;camera.transform.position=new Vector3(2,3,-9);camera.transform.LookAt(new Vector3(0,1.15f,0));camera.backgroundColor=new Color(.25f,.29f,.32f);camera.clearFlags=CameraClearFlags.SolidColor;
  Directory.CreateDirectory("../builds/customer-qa");MarketBuilder.Capture("../builds/customer-qa/poses.png");
 }
 // Samples every shipped clip on every replacement, including skinned bounds.
 public static void Validate(){
  EditorSceneManager.OpenScene(MarketBuilder.ScenePath);int checks=0;
  var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
  foreach(Transform actor in world){if(!actor.name.StartsWith("Customer_"))continue;
   var player=actor.GetComponent<MarketCharacterAnimator>().animationPlayer;
   var body=player.GetComponentsInChildren<SkinnedMeshRenderer>().Single(r=>!r.name.EndsWith("_Prop"));
   if(!body.sharedMaterial.mainTexture||body.sharedMesh.vertexCount>40000)throw new Exception("Invalid customer mesh/material");
   foreach(var name in Clips){var clip=player[name].clip;var original=AssetDatabase.LoadAllAssetsAtPath("Assets/Art/Characters/"+RigSource(actor.name)+".fbx").OfType<AnimationClip>().Single(c=>c.name==(name=="WalkingWithBasket"?"Walking":name));if(Mathf.Abs(clip.length-original.length)>.05f)throw new Exception("Clip duration changed: "+name);
    var mesh=new Mesh();clip.SampleAnimation(player.gameObject,0);body.BakeMesh(mesh);var start=mesh.vertices;
    clip.SampleAnimation(player.gameObject,clip.length*.35f);body.BakeMesh(mesh);var end=mesh.vertices;
    if(!end.Where((p,i)=>(p-start[i]).sqrMagnitude>.000001f).Any())throw new Exception("Static skin: "+actor.name+" / "+name);
    if(mesh.bounds.size.magnitude>5||end.Any(p=>float.IsNaN(p.x)))throw new Exception("Invalid deformation: "+name);
    UnityEngine.Object.DestroyImmediate(mesh);checks++;
   }
  }
  Debug.Log("CHECKOUT_CUSTOMER_VALIDATION_OK "+checks+" animated skins");
 }
}
