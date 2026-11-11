using System.Collections;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "eventscart" (QA copy; Lucas 11/11): "+ Carrinho" in Produtos puts boxes in the saved cart (no truck leaves),
 // the shop window opens with those lines and the delivery time of the mix, "Fazer pedido" sends one truck with
 // everything and the cart empties; Entregas shows the trucks and the next free one.
 public sealed partial class CheckoutAutoTest {
  IEnumerator Cart(string request){
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT cart {name}: {(ok?"PASS":"FAIL")} {detail}");
   var bridge=FindAnyObjectByType<CheckoutBridge>();
   int CartBoxes()=>bridge?.State?.supplierInfo?.cart?.Sum(e=>e.boxes)??0;
   int Orders()=>bridge?.State?.orders?.Length??0;
   Route("");yield return new WaitForSecondsRealtime(3f);
   Route("!products");yield return new WaitForSecondsRealtime(4f);
   yield return ShotJpg("cart_products");
   int ordersBefore=Orders(),cartBefore=CartBoxes();
   var adds=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).Where(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.enabled&&b.Data.action=="addToSupplierCart").ToList();
   Note($"CART + Carrinho buttons on screen: {adds.Count} (cart {cartBefore} boxes, {ordersBefore} orders)");
   Result("+ Carrinho buttons in Produtos",adds.Count>0,adds.Count.ToString());
   if(adds.Count>0){adds[0].Clicked?.Invoke(adds[0]);yield return new WaitForSecondsRealtime(2.5f);}
   yield return ShotJpg("cart_added");
   adds=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).Where(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.enabled&&b.Data.action=="addToSupplierCart").ToList();
   if(adds.Count>0){adds[0].Clicked?.Invoke(adds[0]);yield return new WaitForSecondsRealtime(2.5f);}
   int cartAfter=CartBoxes();
   Result("boxes went to the cart, no truck left",cartAfter>cartBefore&&Orders()==ordersBefore,$"cart {cartBefore}->{cartAfter}, orders {ordersBefore}->{Orders()}");
   Route("!suppliers:estrada");yield return new WaitForSecondsRealtime(4f);
   yield return ShotJpg("cart_entregas");
   Route("");yield return new WaitForSecondsRealtime(1.5f);
   CheckoutSupplierShop.Show();yield return new WaitForSecondsRealtime(3f);
   var shop=CheckoutSupplierShop.Instance;
   yield return ShotJpg("cart_shop");
   Result("the shop window shows the saved cart",shop&&shop.QaCartBoxes==cartAfter,$"{(shop?shop.QaCartBoxes:-1)} vs {cartAfter}");
   if(shop&&shop.QaBuyButton&&shop.QaBuyButton.Data!=null&&shop.QaBuyButton.Data.enabled){
    shop.QaBuyButton.Clicked?.Invoke(shop.QaBuyButton);
    for(float t=0;t<8f&&shop.QaBusy;t+=.25f)yield return new WaitForSecondsRealtime(.25f);
    yield return new WaitForSecondsRealtime(1.5f);
    yield return ShotJpg("cart_ordered");
    Result("one order took the whole cart",Orders()==ordersBefore+1&&CartBoxes()==0,$"orders {Orders()}, cart {CartBoxes()}");
   }else Result("one order took the whole cart",false,"buy button disabled (trucks busy or no coins?)");
   if(shop)shop.QaClose();
   yield return new WaitForSecondsRealtime(1f);
   Route("!logistics");yield return new WaitForSecondsRealtime(3f);
   yield return ShotJpg("cart_logistics");
   // Freight coupons (Lucas 11/11): where they come from and where they show.
   Route("!missions:presentes");yield return new WaitForSecondsRealtime(3f);
   yield return ShotJpg("cart_gifts");
   Route("!suppliers:central");yield return new WaitForSecondsRealtime(3f);
   yield return ShotJpg("cart_central");
   Route("");
  }
 }
}
