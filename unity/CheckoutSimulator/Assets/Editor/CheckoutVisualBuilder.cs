using System;
using UnityEditor;
using UnityEngine;

// Builds the current integrated scene without regenerating or overwriting it.
public static class CheckoutVisualBuilder {
 public static void Desktop(){Build(BuildTarget.StandaloneOSX,"../builds/visual-qa/Checkout.app");}
 public static void IOS(){Build(BuildTarget.iOS,"../builds/ios");}
 static void Build(BuildTarget target,string path){var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{MarketBuilder.ScenePath},locationPathName=path,target=target,options=BuildOptions.None});if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded)throw new Exception("Checkout visual build failed: "+report.summary.result);Debug.Log("CHECKOUT_VISUAL_BUILD_OK "+target);}
}
