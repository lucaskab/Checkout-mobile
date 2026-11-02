package com.checkout.social;

import android.app.Activity;
import com.android.installreferrer.api.InstallReferrerClient;
import com.android.installreferrer.api.InstallReferrerStateListener;
import com.unity3d.player.UnityPlayer;

/**
 * The Play Install Referrer (social v1): the invite page's Play link carries "&referrer=invite%3D<code>"; after the
 * first login the game asks once which link installed it and offers that friend code on the Amigos page.
 * Answers UnitySendMessage(gameObject, "OnInstallReferrer", referrer) ("" when there is none).
 */
public final class CheckoutReferrer {
    private CheckoutReferrer() {}

    public static void fetch(final Activity activity, final String gameObject) {
        final InstallReferrerClient client = InstallReferrerClient.newBuilder(activity).build();
        try {
            client.startConnection(new InstallReferrerStateListener() {
                @Override
                public void onInstallReferrerSetupFinished(int responseCode) {
                    String referrer = "";
                    if (responseCode == InstallReferrerClient.InstallReferrerResponse.OK) {
                        try {
                            referrer = client.getInstallReferrer().getInstallReferrer();
                        } catch (Exception ignored) {
                        }
                    }
                    try {
                        client.endConnection();
                    } catch (Exception ignored) {
                    }
                    UnityPlayer.UnitySendMessage(gameObject, "OnInstallReferrer", referrer == null ? "" : referrer);
                }

                @Override
                public void onInstallReferrerServiceDisconnected() {
                }
            });
        } catch (Exception e) {
            UnityPlayer.UnitySendMessage(gameObject, "OnInstallReferrer", "");
        }
    }
}
