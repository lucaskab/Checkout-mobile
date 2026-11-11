package com.checkout.store;

import android.app.Activity;
import com.google.android.play.core.appupdate.AppUpdateInfo;
import com.google.android.play.core.appupdate.AppUpdateManager;
import com.google.android.play.core.appupdate.AppUpdateManagerFactory;
import com.google.android.play.core.install.model.UpdateAvailability;
import com.google.android.play.core.review.ReviewInfo;
import com.google.android.play.core.review.ReviewManager;
import com.google.android.play.core.review.ReviewManagerFactory;
import com.unity3d.player.UnityPlayer;

/**
 * The game and its Google Play page (Lucas 10/11; Unity side: CheckoutAppStore.cs).
 * - requestReview: Google Play's In-App Review sheet. Play decides whether it shows (its own quota); nothing is
 *   reported back, by design.
 * - checkUpdate: Play's in-app updates API; answers UnitySendMessage(gameObject, "OnUpdateInfo", versionCode) when a
 *   newer version is available, "" when not (or on any error).
 */
public final class CheckoutAppStore {
    private CheckoutAppStore() {}

    public static void requestReview(final Activity activity) {
        try {
            final ReviewManager manager = ReviewManagerFactory.create(activity);
            manager.requestReviewFlow().addOnCompleteListener(task -> {
                if (!task.isSuccessful()) return;
                final ReviewInfo info = task.getResult();
                activity.runOnUiThread(() -> manager.launchReviewFlow(activity, info));
            });
        } catch (Exception ignored) {
        }
    }

    public static void checkUpdate(final Activity activity, final String gameObject) {
        try {
            final AppUpdateManager manager = AppUpdateManagerFactory.create(activity);
            manager.getAppUpdateInfo()
                .addOnSuccessListener((AppUpdateInfo info) -> {
                    String code = "";
                    if (info.updateAvailability() == UpdateAvailability.UPDATE_AVAILABLE)
                        code = String.valueOf(info.availableVersionCode());
                    UnityPlayer.UnitySendMessage(gameObject, "OnUpdateInfo", code);
                })
                .addOnFailureListener(e -> UnityPlayer.UnitySendMessage(gameObject, "OnUpdateInfo", ""));
        } catch (Exception e) {
            UnityPlayer.UnitySendMessage(gameObject, "OnUpdateInfo", "");
        }
    }
}
