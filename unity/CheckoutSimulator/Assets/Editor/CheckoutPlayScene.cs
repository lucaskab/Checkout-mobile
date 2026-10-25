using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;

// Play always starts the game (Lucas 25/10: after the Android build Unity reopened with an empty "Untitled" scene,
// and Play showed a still picture with only the music: the start-up hooks ran with no city around them).
//   - When the editor opens on an empty, unsaved scene, the Supermarket scene is opened instead.
//   - Play from any scene other than Supermarket (Untitled, Boot...) starts from Supermarket; with Supermarket
//     open, Play uses the open scene as always (unsaved edits included).
[InitializeOnLoad]
static class CheckoutPlayScene
{
    const string GameScene = "Assets/Scenes/Supermarket.unity";

    static CheckoutPlayScene()
    {
        EditorApplication.playModeStateChanged -= Changed;
        EditorApplication.playModeStateChanged += Changed;
        EditorSceneManager.sceneOpened -= Opened;
        EditorSceneManager.sceneOpened += Opened;
        EditorApplication.delayCall += () => { OpenGameIfEmpty(); Pick(); };
    }

    static void Opened(Scene scene, OpenSceneMode mode) => Pick();

    static void OpenGameIfEmpty()
    {
        if (EditorApplication.isPlayingOrWillChangePlaymode || BuildPipeline.isBuildingPlayer) return;
        var active = SceneManager.GetActiveScene();
        if (SceneManager.sceneCount != 1 || !string.IsNullOrEmpty(active.path) || active.isDirty) return;
        if (AssetDatabase.LoadAssetAtPath<SceneAsset>(GameScene) == null) return;
        EditorSceneManager.OpenScene(GameScene, OpenSceneMode.Single);
    }

    static void Changed(PlayModeStateChange state)
    {
        if (state == PlayModeStateChange.ExitingEditMode) Pick();
    }

    static void Pick()
    {
        bool gameOpen = false;
        for (int i = 0; i < SceneManager.sceneCount; i++) if (SceneManager.GetSceneAt(i).path == GameScene) gameOpen = true;
        EditorSceneManager.playModeStartScene = gameOpen ? null : AssetDatabase.LoadAssetAtPath<SceneAsset>(GameScene);
    }
}
