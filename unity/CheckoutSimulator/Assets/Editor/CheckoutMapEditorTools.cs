using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Editor helpers for the in-game map editor ("Modo edição", Checkout.CheckoutMapEditor).
public static class CheckoutMapEditorTools
{
    // Static batching merges meshes when Play Mode starts, and merged props can no longer be moved by the map
    // editor. The props are few and already light, so the scene keeps them unbatched.
    [MenuItem("Checkout/Map Editor/Allow Moving Static Props")]
    public static void AllowMoving()
    {
        if (EditorApplication.isPlayingOrWillChangePlaymode) { Debug.LogWarning("CHECKOUT_EDITOR stop Play Mode first."); return; }
        var scene = EditorSceneManager.GetActiveScene(); int n = 0;
        foreach (var root in scene.GetRootGameObjects())
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                var flags = GameObjectUtility.GetStaticEditorFlags(t.gameObject);
                if ((flags & StaticEditorFlags.BatchingStatic) == 0) continue;
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, flags & ~StaticEditorFlags.BatchingStatic); n++;
            }
        if (n > 0) { EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); }
        Debug.Log("CHECKOUT_EDITOR batching static cleared on " + n + " objects");
    }

    [MenuItem("Checkout/Map Editor/Show Design File")]
    public static void ShowDesign()
    {
        var asset = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Resources/" + Checkout.CheckoutMapDesign.ResourceName + ".json");
        if (asset) { Selection.activeObject = asset; EditorGUIUtility.PingObject(asset); }
        else Debug.Log("CHECKOUT_EDITOR no map design saved yet (Play → Modo edição → Salvar).");
    }
}
