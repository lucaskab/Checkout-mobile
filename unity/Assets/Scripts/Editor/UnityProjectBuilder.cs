using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

public static class UnityProjectBuilder
{
    private const string ScenePath = "Assets/Scenes/Supermarket.unity";

    [MenuItem("Checkout/Build Supermarket Scene")]
    public static void BuildSupermarketScene()
    {
        Directory.CreateDirectory("Assets/Scenes");
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var root = new GameObject("CheckoutSupermarket");
        root.AddComponent<StoreGameRuntime>();
        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        ConfigurePlayerSettings();
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("Checkout Supermarket scene created at " + ScenePath);
    }

    private static void ConfigurePlayerSettings()
    {
        PlayerSettings.companyName = "Propstack";
        PlayerSettings.productName = "Checkout Market";
        PlayerSettings.allowedAutorotateToPortrait = false;
        PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
        PlayerSettings.allowedAutorotateToLandscapeRight = true;
        PlayerSettings.allowedAutorotateToLandscapeLeft = true;
        PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, "com.propstack.checkoutmarket");
        PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.iOS, "com.propstack.checkoutmarket");
    }
}
