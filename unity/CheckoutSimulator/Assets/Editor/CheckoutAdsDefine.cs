using System;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;

// Turns the AdMob rewarded videos on (CHECKOUT_ADMOB, see CheckoutAds.cs) for the iPhone and Android builds as soon
// as the Google Mobile Ads Unity plugin is in the project, and off again if it is removed — so the project compiles
// with or without the plugin.
[InitializeOnLoad]
public static class CheckoutAdsDefine
{
    const string Define = "CHECKOUT_ADMOB";

    static CheckoutAdsDefine()
    {
        bool present = AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetType("GoogleMobileAds.Api.MobileAds", false) != null);
        foreach (var target in new[] { NamedBuildTarget.iOS, NamedBuildTarget.Android })
        {
            var defines = PlayerSettings.GetScriptingDefineSymbols(target).Split(';').Where(d => d.Length > 0).ToList();
            bool has = defines.Contains(Define);
            if (present == has) continue;
            if (present) defines.Add(Define); else defines.Remove(Define);
            PlayerSettings.SetScriptingDefineSymbols(target, string.Join(";", defines));
        }
    }
}
