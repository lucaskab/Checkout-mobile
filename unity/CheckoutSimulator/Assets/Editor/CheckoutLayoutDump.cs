using System.IO;
using System.Linq;
using System.Text;
using MarketDay;
using UnityEditor;
using UnityEngine;

// Dev helper: writes the world-space footprint of every scenery object (two levels deep under the
// Supermarket World) to Logs/city_layout.txt, so layout changes can be planned without clicking around.
public static class CheckoutLayoutDump
{
    [MenuItem("Supermarket/Dev/Dump City Layout")]
    public static void Dump()
    {
        var world = Object.FindAnyObjectByType<MarketSimulation>().world;
        var text = new StringBuilder();
        string B(Transform t)
        {
            var rs = t.GetComponentsInChildren<Renderer>(true).Where(r => !(r is ParticleSystemRenderer)).ToArray();
            if (rs.Length == 0) return "p=" + t.position.ToString("F1");
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            return $"x[{b.min.x:F1},{b.max.x:F1}] z[{b.min.z:F1},{b.max.z:F1}] h{b.size.y:F1}";
        }
        foreach (Transform group in world)
        {
            text.AppendLine($"{group.name} active={group.gameObject.activeSelf} children={group.childCount} {B(group)}");
            if (group.childCount > 400) continue;
            foreach (Transform child in group)
                text.AppendLine($"  {child.name} active={child.gameObject.activeSelf} {B(child)}");
        }
        File.WriteAllText("Logs/city_layout.txt", text.ToString());
        Debug.Log("CITY_LAYOUT_DUMPED");
    }
}
