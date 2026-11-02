using System.IO;
using System.Xml;
using UnityEditor;
using UnityEditor.Callbacks;
#if UNITY_ANDROID
using UnityEditor.Android;
#endif
#if UNITY_IOS
using UnityEditor.iOS.Xcode;
#endif

// Social v1 (docs/social-api.md) in the phone builds:
// - checkout://add/<code> opens the game and offers that friend code (CheckoutSocial.cs, Application.deepLinkActivated):
//   the iPhone's Info.plist gets the "checkout" URL scheme, Android's launcher activity an intent filter.
// - Android shares the picture of the market through a FileProvider (Plugins/Android/CheckoutShare.java).
public static class CheckoutSocialBuild
{
    public const string Scheme = "checkout";

#if UNITY_IOS
    [PostProcessBuild(101)]
    public static void AddUrlScheme(BuildTarget target, string path)
    {
        if (target != BuildTarget.iOS) return;
        var plistPath = Path.Combine(path, "Info.plist");
        var plist = new PlistDocument();
        plist.ReadFromFile(plistPath);
        var types = plist.root.values.TryGetValue("CFBundleURLTypes", out var existing) && existing is PlistElementArray array ? array : plist.root.CreateArray("CFBundleURLTypes");
        foreach (var entry in types.values)
            if (entry is PlistElementDict dict && dict.values.TryGetValue("CFBundleURLSchemes", out var schemes) && schemes is PlistElementArray list)
                foreach (var scheme in list.values)
                    if (scheme.AsString() == Scheme) return;
        var item = types.AddDict();
        item.SetString("CFBundleURLName", PlayerSettings.applicationIdentifier + ".friends");
        item.CreateArray("CFBundleURLSchemes").AddString(Scheme);
        plist.WriteToFile(plistPath);
    }
#endif

}

#if UNITY_ANDROID
public class CheckoutSocialAndroidBuild : IPostGenerateGradleAndroidProject
{
    const string Scheme = CheckoutSocialBuild.Scheme;
    public int callbackOrder => 50;

    public void OnPostGenerateGradleAndroidProject(string path)
    {
        const string android = "http://schemas.android.com/apk/res/android";
        var manifests = new[] { Path.Combine(path, "src", "main", "AndroidManifest.xml"), Path.Combine(path, "..", "launcher", "src", "main", "AndroidManifest.xml") };
        for (int index = 0; index < manifests.Length; index++)
        {
            var manifestPath = manifests[index];
            bool library = index == 0;
            if (!File.Exists(manifestPath)) continue;
            var doc = new XmlDocument();
            doc.Load(manifestPath);
            var ns = new XmlNamespaceManager(doc.NameTable);
            ns.AddNamespace("android", android);
            bool changed = false;
            // The launcher activity: checkout://add/<code>.
            foreach (XmlElement activity in doc.SelectNodes("//activity[intent-filter/category/@android:name='android.intent.category.LAUNCHER']", ns))
            {
                if (activity.SelectSingleNode($"intent-filter/data[@android:scheme='{Scheme}']", ns) != null) continue;
                var filter = doc.CreateElement("intent-filter");
                XmlElement Child(string name, string attribute, string value)
                {
                    var element = doc.CreateElement(name);
                    element.SetAttribute(attribute, android, value);
                    filter.AppendChild(element);
                    return element;
                }
                Child("action", "name", "android.intent.action.VIEW");
                Child("category", "name", "android.intent.category.DEFAULT");
                Child("category", "name", "android.intent.category.BROWSABLE");
                Child("data", "scheme", Scheme).SetAttribute("host", android, "add");
                activity.AppendChild(filter);
                changed = true;
            }
            // The share picture's FileProvider (only once, in the library's manifest).
            var application = doc.SelectSingleNode("/manifest/application") as XmlElement;
            if (application != null && library && doc.SelectSingleNode("//provider[@android:authorities='${applicationId}.checkoutshare']", ns) == null)
            {
                var provider = doc.CreateElement("provider");
                provider.SetAttribute("name", android, "androidx.core.content.FileProvider");
                provider.SetAttribute("authorities", android, "${applicationId}.checkoutshare");
                provider.SetAttribute("exported", android, "false");
                provider.SetAttribute("grantUriPermissions", android, "true");
                var meta = doc.CreateElement("meta-data");
                meta.SetAttribute("name", android, "android.support.FILE_PROVIDER_PATHS");
                meta.SetAttribute("resource", android, "@xml/checkout_share_paths");
                provider.AppendChild(meta);
                application.AppendChild(provider);
                var xml = Path.Combine(path, "src", "main", "res", "xml");
                Directory.CreateDirectory(xml);
                File.WriteAllText(Path.Combine(xml, "checkout_share_paths.xml"),
                    "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<paths>\n  <cache-path name=\"share\" path=\".\" />\n  <external-cache-path name=\"share_external\" path=\".\" />\n</paths>\n");
                changed = true;
            }
            if (changed) doc.Save(manifestPath);
        }
    }
}
#endif
