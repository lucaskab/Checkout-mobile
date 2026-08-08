using UnityEngine;

public sealed class StoreProductBillboard : MonoBehaviour
{
    private void LateUpdate()
    {
        if (Camera.main == null)
        {
            return;
        }

        transform.LookAt(Camera.main.transform);
    }
}
