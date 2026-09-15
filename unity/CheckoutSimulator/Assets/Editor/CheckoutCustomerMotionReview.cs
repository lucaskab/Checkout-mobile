using UnityEngine;using UnityEditor;using UnityEditor.SceneManagement;using System.IO;using System.Linq;
public static class CheckoutCustomerMotionReview {
[MenuItem("Supermarket/Review current customer motion")]
public static void Run(){
 if(EditorApplication.isPlaying)throw new System.Exception("Stop Play before applying customer visuals");
 var currentWorld=Object.FindAnyObjectByType<MarketDay.MarketSimulation>().world;
 Undo.RegisterFullObjectHierarchyUndo(currentWorld.gameObject,"Correct customer skin weights");
 CheckoutCustomerBuilder.ApplyToWorld(currentWorld);
 EditorSceneManager.MarkSceneDirty(currentWorld.gameObject.scene);EditorSceneManager.SaveScene(currentWorld.gameObject.scene);AssetDatabase.SaveAssets();
var world=Object.FindFirstObjectByType<MarketDay.MarketSimulation>().world;var root=new GameObject("Temporary customer review");var camObj=new GameObject("Review camera");var cam=camObj.AddComponent<Camera>();var rt=new RenderTexture(1400,650,24);var previous=RenderTexture.active;Texture2D image=null;
try{for(int i=6;i<=9;i++){var visual=world.Find("Customer_"+i.ToString("00")).GetComponent<MarketDay.MarketCharacterAnimator>().animationPlayer;var clone=Object.Instantiate(visual.gameObject,root.transform);clone.SetActive(true);clone.transform.position=new Vector3((i-7.5f)*2.2f,100,0);clone.transform.rotation=Quaternion.Euler(0,115,0);clone.GetComponent<Animation>()["Walking"].clip.SampleAnimation(clone,.25f);foreach(var renderer in clone.GetComponentsInChildren<Renderer>())if(renderer.name.EndsWith("_Prop"))renderer.enabled=false;}
cam.orthographic=true;cam.orthographicSize=2;cam.transform.position=new Vector3(0,102,-9);cam.transform.LookAt(new Vector3(0,101.2f,0));cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=new Color(.88f,.85f,.77f);cam.targetTexture=rt;cam.Render();RenderTexture.active=rt;image=new Texture2D(1400,650,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1400,650),0,0);image.Apply();File.WriteAllBytes("/tmp/checkout-new-customers.png",image.EncodeToPNG());Debug.Log("/tmp/checkout-new-customers.png");}finally{RenderTexture.active=previous;cam.targetTexture=null;Object.DestroyImmediate(root);Object.DestroyImmediate(camObj);Object.DestroyImmediate(rt);if(image)Object.DestroyImmediate(image);}

Debug.Log("CUSTOMER_MOTION_REVIEW_DONE");
}
}
