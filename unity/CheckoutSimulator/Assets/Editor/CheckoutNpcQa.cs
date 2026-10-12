using System.IO;
using System.Linq;
using Checkout;
using UnityEditor;
using UnityEngine;

// QA picture of the new characters as the game imports them (Lucas 12/10): the construction crew with the game's own
// hammer and sledgehammer at the key frames of their clips (held by the same rule as CheckoutWorksScene.HoldTool),
// the three new customers, and the delivery bike with the new rider. Built far from the map with its own camera and
// removed afterwards (the scene is not saved). Writes Logs/ui_qa/npcs.png.
public static class CheckoutNpcQa
{
    [MenuItem("Checkout/QA/Capture new characters")]
    public static void Capture()
    {
        var root = new GameObject("NPC QA").transform; root.position = new Vector3(2000, 0, 2000);
        try
        {
            float x = 0;
            // The game's character scale: the market's delivery worker (the crew is cloned from it).
            var tmpl = Object.FindAnyObjectByType<MarketDay.MarketDeliveryWorker>(FindObjectsInactive.Include);
            var vis = tmpl ? tmpl.GetComponentsInChildren<Animation>(true).FirstOrDefault() : null;
            float S = vis ? vis.transform.lossyScale.y : .45f, H = 2.4f * S;
            Vector3 P(float dx) => root.position + new Vector3(dx, 0, 0);
            void Crew(string look, string clip, float t, Tool tool)
            {
                var prefab = Resources.Load<GameObject>("CheckoutCrew/" + look);
                var go = Object.Instantiate(prefab, root); go.transform.position = P(x); go.transform.rotation = Quaternion.Euler(0, 180 + 35, 0);
                go.transform.localScale = Vector3.one * S;
                foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>()) r.sharedMaterial = Resources.Load<Material>("CheckoutCrew/" + look);
                var anim = go.GetComponent<Animation>();
                // As in the game: the tool hand is found on the rest pose (CheckoutWorksScene.NewWorker), then the clip plays.
                var bones = go.GetComponentsInChildren<Transform>();
                var body = new GameObject("Body").transform; body.position = go.transform.position; body.rotation = Quaternion.Euler(0, 215, 0);     // the model faces +Z: it looks at the camera
                body.SetParent(root, true);
                CheckoutCrew.Hands(body, bones.First(b => b.name == "Hand_L"), bones.First(b => b.name == "Hand_R"), out var hand, out var other);
                var c = anim[clip].clip; c.SampleAnimation(go, c.length * t);
                if (tool != Tool.None)
                {
                    var model = CheckoutWorksKit.Spawn(tool == Tool.Hammer ? "Tool_Hammer" : "Tool_Sledgehammer", root, hand.position, Vector3.forward);
                    var m = model.Find("Model"); if (m) m.localPosition = Vector3.zero;
                    Hold(model, hand, other, body, tool == Tool.Sledge);
                }
                x += H * .62f;
            }
            Crew("Worker_ConstructionM", "Idle", .2f, Tool.None);
            Crew("Worker_ConstructionF", "Walking", .25f, Tool.None);
            Crew("Worker_ConstructionM", "Hammer", .55f, Tool.Hammer);
            Crew("Worker_ConstructionF", "Hammer", .71f, Tool.Hammer);
            Crew("Worker_ConstructionM", "Sledge", .5f, Tool.Sledge);
            Crew("Worker_ConstructionF", "Sledge", .72f, Tool.Sledge);
            foreach (var (name, look) in new[] { ("Customer_02", "Customer_Plaid"), ("Customer_03", "Customer_Elder"), ("Customer_04", "Customer_Jacket") })
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Characters/Meshy/" + name + ".fbx"), root);
                go.transform.position = P(x); go.transform.rotation = Quaternion.Euler(0, 180 + 20, 0); go.transform.localScale = Vector3.one * S;
                var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Characters/Meshy/" + look + ".mat");
                foreach (var r in go.GetComponentsInChildren<Renderer>()) { if (r.name.EndsWith("_Prop")) r.enabled = false; else if (mat) r.sharedMaterial = mat; }
                x += H * .5f;
            }
            var bike = Object.Instantiate(Resources.Load<GameObject>("CheckoutDelivery/delivery_bike_riding"), root);
            bike.transform.position = P(x + H * .3f); bike.transform.rotation = Quaternion.Euler(0, -60, 0);
            foreach (var r in bike.GetComponentsInChildren<Renderer>()) if (r.name.StartsWith("fx_riding_DK_courier") || r.name.StartsWith("fx_riding_DK_helm")) r.enabled = false;
            var rider = Object.Instantiate(Resources.Load<GameObject>("CheckoutDelivery/delivery_rider"), bike.transform, false);
            rider.transform.localPosition = Vector3.zero; rider.transform.localRotation = Quaternion.identity;
            var riderMat = Resources.Load<Material>("CheckoutDelivery/delivery_rider"); if (riderMat) foreach (var r in rider.GetComponentsInChildren<Renderer>()) r.sharedMaterial = riderMat;

            var light = new GameObject("Sun").AddComponent<Light>(); light.transform.SetParent(root); light.type = LightType.Directional;
            light.transform.rotation = Quaternion.Euler(45, -30, 0); light.intensity = 1.2f;
            var cam = new GameObject("Cam").AddComponent<Camera>(); cam.transform.SetParent(root);
            // Skinned bounds are not reliable here (the rigs are scaled): frame the row of figures by their spacing.
            float span = x + H * .9f;
            var center = root.position + new Vector3(span / 2 - H * .3f, H * .5f, 0);
            cam.orthographic = true; cam.orthographicSize = Mathf.Max(H * .6f, span / 2 * 820f / 2400f * 1.05f);
            cam.transform.position = center + new Vector3(0, 0, -30); cam.transform.rotation = Quaternion.identity; cam.farClipPlane = 100;
            var rt = new RenderTexture(2400, 820, 24) { antiAliasing = 4 };
            cam.targetTexture = rt; cam.aspect = 2400f / 820f; cam.Render(); RenderTexture.active = rt;
            var img = new Texture2D(2400, 820, TextureFormat.RGB24, false); img.ReadPixels(new Rect(0, 0, 2400, 820), 0, 0); img.Apply();
            RenderTexture.active = null; cam.targetTexture = null;
            Directory.CreateDirectory("Logs/ui_qa"); File.WriteAllBytes("Logs/ui_qa/npcs.png", img.EncodeToPNG());
            Object.DestroyImmediate(img); rt.Release();
            Debug.Log("CHECKOUT_NPC_QA_OK Logs/ui_qa/npcs.png scale " + S);
        }
        finally { Object.DestroyImmediate(root.gameObject); }
    }

    enum Tool { None, Hammer, Sledge }

    // Same rule as CheckoutWorksScene.HoldTool.
    static void Hold(Transform tool, Transform hand, Transform other, Transform body, bool sledge)
    {
        var right = body.right; var fwd = body.forward;
        var d = hand.position - hand.parent.position; float forearm = d.magnitude; d.Normalize();
        Vector3 up, at;
        if (sledge) { up = (other.position - hand.position).normalized; at = (hand.position + other.position) * .5f; }
        else { float df = Vector3.Dot(d, fwd), du = Vector3.Dot(d, Vector3.up); up = (fwd * -du + Vector3.up * df).normalized; at = hand.position + d * forearm * .17f; }
        tool.position = at;
        var ahead = Vector3.Cross(right, up);
        tool.rotation = Quaternion.LookRotation(ahead.sqrMagnitude > .01f ? ahead : fwd, up);
    }
}
