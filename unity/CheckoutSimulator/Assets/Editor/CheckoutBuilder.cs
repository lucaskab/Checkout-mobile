using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Checkout;
using MarketDay;
public static class CheckoutBuilder {
 public static void Build(){MarketBuilder.Build();if(!AssetDatabase.LoadAssetAtPath<Material>("Assets/Resources/CheckoutSurface.mat"))AssetDatabase.CreateAsset(new Material(Shader.Find("Standard")),"Assets/Resources/CheckoutSurface.mat");var go=new GameObject("CheckoutBridge");go.AddComponent<CheckoutBridge>();var sim=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();sim.enabled=false;sim.quietCapture=true;sim.GetComponent<MarketPlaytest>().enabled=false;
  PlayerSettings.productName="Checkout Simulator";PlayerSettings.defaultInterfaceOrientation=UIOrientation.AutoRotation;PlayerSettings.allowedAutorotateToPortrait=true;PlayerSettings.allowedAutorotateToLandscapeLeft=true;PlayerSettings.allowedAutorotateToLandscapeRight=true;PlayerSettings.iOS.targetOSVersionString="16.4";
  EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),MarketBuilder.ScenePath);AssetDatabase.SaveAssets();Debug.Log("CHECKOUT_SCENE_OK");}
 public static void Desktop(){Build();MarketBuilder.Validate();MarketBuilder.BuildWindows();}
 public static void Android(){
#if UNITY_EDITOR && UNITY_ANDROID
  Build();
  string sdk=Environment.GetEnvironmentVariable("ANDROID_HOME");if(!string.IsNullOrEmpty(sdk))UnityEditor.Android.AndroidExternalToolsSettings.sdkRootPath=sdk;
  string ndk=Environment.GetEnvironmentVariable("CHECKOUT_ANDROID_NDK");if(!string.IsNullOrEmpty(ndk))UnityEditor.Android.AndroidExternalToolsSettings.ndkRootPath=ndk;
  string jdk=Environment.GetEnvironmentVariable("JAVA_HOME");if(!string.IsNullOrEmpty(jdk))UnityEditor.Android.AndroidExternalToolsSettings.jdkRootPath=jdk;
  PlayerSettings.SetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Android,ScriptingImplementation.IL2CPP);PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;PlayerSettings.Android.minSdkVersion=AndroidSdkVersions.AndroidApiLevel26;PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)36;PlayerSettings.Android.applicationEntry=AndroidApplicationEntry.Activity;
  EditorUserBuildSettings.exportAsGoogleAndroidProject=true;
  var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{MarketBuilder.ScenePath},locationPathName="../builds/android",target=BuildTarget.Android,options=BuildOptions.AcceptExternalModificationsToPlayer|BuildOptions.Development});
  if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded)throw new Exception("Unity Android library export failed");Debug.Log("CHECKOUT_ANDROID_LIBRARY_OK");
#else
  throw new Exception("Android Build Support is required to export Android.");
#endif
 }
 [MenuItem("Supermarket/Export current scene for React Native iOS")]
 public static void IOS(){
  if(EditorApplication.isPlaying)throw new InvalidOperationException("Leave Play mode before exporting.");
  var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
  if(scene.path!=MarketBuilder.ScenePath)scene=EditorSceneManager.OpenScene(MarketBuilder.ScenePath,OpenSceneMode.Single);
  EditorSceneManager.SaveScene(scene,MarketBuilder.ScenePath);AssetDatabase.SaveAssets();
  PlayerSettings.iOS.sdkVersion=iOSSdkVersion.SimulatorSDK;PlayerSettings.iOS.simulatorSdkArchitecture=AppleMobileArchitectureSimulator.ARM64;
  var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{MarketBuilder.ScenePath},locationPathName="../builds/ios",target=BuildTarget.iOS,options=BuildOptions.None});
  if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded)throw new Exception("Unity iOS export failed");
  Debug.Log("CHECKOUT_IOS_EXPORT_OK "+report.summary.totalSize);
 }
}
