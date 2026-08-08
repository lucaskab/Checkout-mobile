using UnityEngine;

public enum CustomerAnimationState
{
    Idle,
    Walking,
    PickingProduct,
    Paying,
    Leaving,
}

public sealed class CustomerModelAnimator : MonoBehaviour
{
    private Transform armLeft;
    private Transform armRight;
    private Transform legLeft;
    private Transform legRight;
    private Transform body;
    private Transform basket;
    private float elapsed;
    private CustomerAnimationState state;

    private void Awake()
    {
        armLeft = FindPart("Arm_L");
        armRight = FindPart("Arm_R");
        legLeft = FindPart("Leg_L");
        legRight = FindPart("Leg_R");
        body = FindPart("Body");
        basket = FindPart("Basket");
    }

    public void SetState(CustomerAnimationState nextState)
    {
        if (state == nextState)
        {
            return;
        }

        state = nextState;
        elapsed = 0f;
    }

    private void Update()
    {
        elapsed += Time.deltaTime;
        var cycle = Mathf.Sin(elapsed * 10f);
        var armSwing = 0f;
        var legSwing = 0f;
        var bodyLean = 0f;
        var basketTilt = 0f;

        if (state == CustomerAnimationState.Walking || state == CustomerAnimationState.Leaving)
        {
            armSwing = cycle * 34f;
            legSwing = cycle * 30f;
            bodyLean = Mathf.Abs(cycle) * 3f;
            basketTilt = -12f + cycle * 5f;
        }
        else if (state == CustomerAnimationState.PickingProduct)
        {
            var reach = Mathf.SmoothStep(0f, 1f, Mathf.PingPong(elapsed * 1.25f, 1f));
            armRight = Rotate(armRight, -68f * reach, 0f, -18f * reach);
            armLeft = Rotate(armLeft, 16f * reach, 0f, 8f * reach);
            bodyLean = -8f * reach;
            basketTilt = -22f * reach;
        }
        else if (state == CustomerAnimationState.Paying)
        {
            var offer = Mathf.SmoothStep(0.25f, 1f, Mathf.PingPong(elapsed * 1.1f, 1f));
            armRight = Rotate(armRight, -82f * offer, 0f, -12f * offer);
            armLeft = Rotate(armLeft, -42f * offer, 0f, 14f * offer);
            bodyLean = -12f * offer;
            basketTilt = -28f * offer;
        }

        if (state == CustomerAnimationState.Walking || state == CustomerAnimationState.Leaving)
        {
            armLeft = Rotate(armLeft, -armSwing, 0f, 0f);
            armRight = Rotate(armRight, armSwing, 0f, 0f);
        }

        legLeft = Rotate(legLeft, legSwing, 0f, 0f);
        legRight = Rotate(legRight, -legSwing, 0f, 0f);
        body = Rotate(body, bodyLean, 0f, 0f);
        basket = Rotate(basket, basketTilt, 0f, 0f);
    }

    private Transform Rotate(Transform part, float x, float y, float z)
    {
        if (part != null)
        {
            part.localRotation = Quaternion.Euler(x, y, z);
        }

        return part;
    }

    private Transform FindPart(string partName)
    {
        return FindPart(transform, partName);
    }

    private static Transform FindPart(Transform node, string partName)
    {
        if (node.name == partName)
        {
            return node;
        }

        for (var index = 0; index < node.childCount; index++)
        {
            var part = FindPart(node.GetChild(index), partName);
            if (part != null)
            {
                return part;
            }
        }

        return null;
    }
}
