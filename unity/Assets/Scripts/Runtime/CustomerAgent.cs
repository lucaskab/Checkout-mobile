using UnityEngine;

public sealed class CustomerAgent : MonoBehaviour
{
    private enum CustomerPhase
    {
        WalkingToShelf,
        PickingProduct,
        WalkingToCheckout,
        Paying,
        Leaving,
    }

    private StoreGameRuntime runtime;
    private string shelfId;
    private Vector3 destination;
    private Vector3 checkoutDestination;
    private Vector3 exitDestination;
    private CustomerPhase phase;
    private CustomerModelAnimator modelAnimator;
    private float actionTimeRemaining;
    private float walkSpeed;

    public void Initialize(
        StoreGameRuntime owner,
        string targetShelfId,
        Vector3 shelfDestination,
        Vector3 checkoutDestination,
        Vector3 exitDestination,
        CustomerModelAnimator animator)
    {
        runtime = owner;
        shelfId = targetShelfId;
        destination = Flatten(shelfDestination);
        this.checkoutDestination = Flatten(checkoutDestination);
        this.exitDestination = Flatten(exitDestination);
        modelAnimator = animator;
        phase = CustomerPhase.WalkingToShelf;
        walkSpeed = Random.Range(1.2f, 1.7f);
        gameObject.name = "Customer_" + targetShelfId;
        modelAnimator?.SetState(CustomerAnimationState.Walking);
    }

    private void Update()
    {
        if (runtime == null)
        {
            return;
        }

        if (phase == CustomerPhase.PickingProduct || phase == CustomerPhase.Paying)
        {
            actionTimeRemaining -= Time.deltaTime;
            if (actionTimeRemaining <= 0f)
            {
                FinishAction();
            }

            return;
        }

        var current = transform.position;
        var next = Vector3.MoveTowards(current, destination, walkSpeed * Time.deltaTime);
        transform.position = next;
        var direction = destination - current;
        direction.y = 0f;
        if (direction.sqrMagnitude > 0.001f)
        {
            transform.forward = Vector3.Slerp(transform.forward, direction.normalized, Time.deltaTime * 8f);
        }

        if (Vector3.Distance(transform.position, destination) > 0.2f)
        {
            return;
        }

        if (phase == CustomerPhase.WalkingToShelf)
        {
            phase = CustomerPhase.PickingProduct;
            actionTimeRemaining = Random.Range(0.75f, 1.1f);
            modelAnimator?.SetState(CustomerAnimationState.PickingProduct);
            return;
        }

        if (phase == CustomerPhase.WalkingToCheckout)
        {
            phase = CustomerPhase.Paying;
            actionTimeRemaining = Random.Range(0.8f, 1.15f);
            modelAnimator?.SetState(CustomerAnimationState.Paying);
            return;
        }

        if (phase == CustomerPhase.Leaving)
        {
            runtime.CustomerExited(this);
            Destroy(gameObject);
        }
    }

    private void FinishAction()
    {
        if (phase == CustomerPhase.PickingProduct)
        {
            runtime.CustomerReachedShelf(this, shelfId);
            phase = CustomerPhase.WalkingToCheckout;
            destination = checkoutDestination;
            modelAnimator?.SetState(CustomerAnimationState.Walking);
            return;
        }

        runtime.CustomerReachedCheckout(this, shelfId);
        phase = CustomerPhase.Leaving;
        destination = exitDestination;
        modelAnimator?.SetState(CustomerAnimationState.Leaving);
    }

    private Vector3 Flatten(Vector3 position)
    {
        return new Vector3(position.x, transform.position.y, position.z);
    }
}
