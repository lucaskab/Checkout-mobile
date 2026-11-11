using System.IO;
using Unity.Notifications;
using UnityEditor;
using UnityEngine;

// The Android notification icon (06/11): Android draws the small icon of a notification as a white shape, so the app
// icon (in colour) shows as a white square. Assets/Art/Notifications/checkout_small.png (a white cart on transparent,
// 192 px) is added once to Project Settings › Mobile Notifications as the small icon "checkout_small"; the package
// copies it into the build's drawables. CheckoutNotifications uses it for the local notifications and the Firebase
// manifest (Plugins/Android/AndroidManifest.xml, default_notification_icon) for the pushes.
[InitializeOnLoad]
public static class CheckoutNotificationIcon
{
    public const string Id = "checkout_small";
    const string TexturePath = "Assets/Art/Notifications/checkout_small.png";

    static CheckoutNotificationIcon() { EditorApplication.delayCall += Ensure; }

    [MenuItem("Checkout/QA/Register the notification icon")]
    public static void Ensure()
    {
        if (!File.Exists(TexturePath)) return;
        var importer = AssetImporter.GetAtPath(TexturePath) as TextureImporter;
        if (importer == null) return;
        if (!importer.isReadable || importer.textureCompression != TextureImporterCompression.Uncompressed || importer.mipmapEnabled || !importer.alphaIsTransparency)
        {
            importer.textureType = TextureImporterType.Default;
            importer.isReadable = true;
            importer.mipmapEnabled = false;
            importer.alphaIsTransparency = true;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.SaveAndReimport();
        }
        // The game asks for the permission itself, after the first long build (CheckoutNotifications), not at launch;
        // and Android keeps the scheduled notifications through a phone restart.
        if (NotificationSettings.iOSSettings.RequestAuthorizationOnAppLaunch) NotificationSettings.iOSSettings.RequestAuthorizationOnAppLaunch = false;
        if (!NotificationSettings.AndroidSettings.RescheduleOnDeviceRestart) NotificationSettings.AndroidSettings.RescheduleOnDeviceRestart = true;
        var settings = Path.Combine("ProjectSettings", "NotificationsSettings.asset");
        if (File.Exists(settings) && File.ReadAllText(settings).Contains(Id)) return;
        var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath);
        if (!texture) return;
        NotificationSettings.AndroidSettings.AddDrawableResource(Id, texture, NotificationIconType.Small);
        Debug.Log("CHECKOUT_NOTIF small icon registered: " + Id);
    }
}
