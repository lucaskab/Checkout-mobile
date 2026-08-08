using System;
using UnityEngine;

/// <summary>
/// Transport-neutral contract for the future React Native host.
/// In a Unity as a Library build, the native wrapper can call the public JSON methods
/// through SendMessage/UnityPlayer and subscribe to UnityActionEmitted.
/// </summary>
public sealed class UnityGameBridge : MonoBehaviour
{
    public static UnityGameBridge Instance { get; private set; }

    public event Action<string> UnityActionEmitted;
    public event Action<StoreSnapshot> SnapshotApplied;

    private StoreGameRuntime runtime;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }

        Instance = this;
        DontDestroyOnLoad(gameObject);
        runtime = FindAnyObjectByType<StoreGameRuntime>();
    }

    public void ConnectRuntime(StoreGameRuntime gameRuntime)
    {
        runtime = gameRuntime;
    }

    public void ApplySnapshot(string json)
    {
        if (string.IsNullOrWhiteSpace(json) || runtime == null)
        {
            return;
        }

        var snapshot = JsonUtility.FromJson<StoreSnapshot>(json);
        if (snapshot == null)
        {
            return;
        }

        runtime.ApplySnapshot(snapshot);
        SnapshotApplied?.Invoke(snapshot);
    }

    public void RequestAction(string json)
    {
        if (string.IsNullOrWhiteSpace(json) || runtime == null)
        {
            return;
        }

        var action = JsonUtility.FromJson<StoreActionMessage>(json);
        if (action == null)
        {
            return;
        }

        runtime.HandleBridgeAction(action);
    }

    public void EmitAction(StoreEventMessage message)
    {
        var json = JsonUtility.ToJson(message);
        UnityActionEmitted?.Invoke(json);
#if UNITY_IOS && !UNITY_EDITOR
        UnityEngine.iOS.Device.SetNoBackupFlag(Application.persistentDataPath);
#endif
    }

    public string GetSnapshotJson()
    {
        return runtime == null ? string.Empty : JsonUtility.ToJson(runtime.BuildSnapshot());
    }
}
