using UnityEngine;

public sealed class StoreClickable : MonoBehaviour
{
    public string targetId;
    public string actionType;

    public void Configure(string id, string action)
    {
        targetId = id;
        actionType = action;
    }
}
