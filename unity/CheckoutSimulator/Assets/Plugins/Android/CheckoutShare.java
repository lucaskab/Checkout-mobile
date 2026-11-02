package com.checkout.social;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import androidx.core.content.FileProvider;
import java.io.File;

/**
 * "Chamar amigo" on Android (CheckoutSocial.cs, social v1): the system share sheet with the invite text + link and a
 * picture of the player's market. The picture is shared from the app's cache through a FileProvider
 * (authority "<applicationId>.checkoutshare", added to the manifest by Assets/Editor/CheckoutSocialBuild.cs).
 */
public final class CheckoutShare {
    private CheckoutShare() {}

    public static void share(final Activity activity, final String text, final String imagePath) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                Intent intent = new Intent(Intent.ACTION_SEND);
                intent.putExtra(Intent.EXTRA_TEXT, text == null ? "" : text);
                intent.setType("text/plain");
                try {
                    if (imagePath != null && !imagePath.isEmpty()) {
                        File file = new File(imagePath);
                        if (file.exists()) {
                            Uri uri = FileProvider.getUriForFile(activity, activity.getPackageName() + ".checkoutshare", file);
                            intent.putExtra(Intent.EXTRA_STREAM, uri);
                            intent.setType("image/png");
                            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        }
                    }
                } catch (Exception ignored) {
                    // No picture (provider missing): the text and the link still go.
                    intent.removeExtra(Intent.EXTRA_STREAM);
                    intent.setType("text/plain");
                }
                activity.startActivity(Intent.createChooser(intent, null));
            }
        });
    }
}
