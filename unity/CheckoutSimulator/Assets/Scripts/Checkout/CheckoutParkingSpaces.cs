using UnityEngine;
namespace Checkout
{
    public class CheckoutParkingSpaces : MonoBehaviour
    {
        public GameObject[] spaces;
        public void Apply(int count){for(int i=0;i<spaces.Length;i++)spaces[i].SetActive(i<count);}
    }
}
