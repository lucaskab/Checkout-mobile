package com.checkout.signin;

import android.app.Activity;
import android.os.CancellationSignal;
import androidx.credentials.Credential;
import androidx.credentials.CredentialManager;
import androidx.credentials.CredentialManagerCallback;
import androidx.credentials.CustomCredential;
import androidx.credentials.GetCredentialRequest;
import androidx.credentials.GetCredentialResponse;
import androidx.credentials.exceptions.GetCredentialCancellationException;
import androidx.credentials.exceptions.GetCredentialException;
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption;
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential;
import com.unity3d.player.UnityPlayer;
import java.util.concurrent.Executors;

/**
 * "Entrar com Google" on Android (CheckoutCloud.cs): Android's Credential Manager shows the Google account sheet and
 * returns an ID token for the game's web client, which the server checks (server/src/tokens.ts). The answer goes back
 * to Unity with UnitySendMessage(gameObject, "OnGoogleIdToken" | "OnGoogleSignInFailed", value).
 */
public final class CheckoutGoogleSignIn {
    private CheckoutGoogleSignIn() {}

    public static void signIn(final Activity activity, final String webClientId, final String gameObject) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    GetSignInWithGoogleOption option = new GetSignInWithGoogleOption.Builder(webClientId).build();
                    GetCredentialRequest request = new GetCredentialRequest.Builder().addCredentialOption(option).build();
                    CredentialManager.create(activity).getCredentialAsync(
                            activity,
                            request,
                            new CancellationSignal(),
                            Executors.newSingleThreadExecutor(),
                            new CredentialManagerCallback<GetCredentialResponse, GetCredentialException>() {
                                @Override
                                public void onResult(GetCredentialResponse response) {
                                    Credential credential = response.getCredential();
                                    try {
                                        if (credential instanceof CustomCredential
                                                && GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL.equals(credential.getType())) {
                                            GoogleIdTokenCredential google = GoogleIdTokenCredential.createFrom(((CustomCredential) credential).getData());
                                            UnityPlayer.UnitySendMessage(gameObject, "OnGoogleIdToken", google.getIdToken());
                                            return;
                                        }
                                    } catch (Exception error) {
                                        UnityPlayer.UnitySendMessage(gameObject, "OnGoogleSignInFailed", "parse: " + error.getMessage());
                                        return;
                                    }
                                    UnityPlayer.UnitySendMessage(gameObject, "OnGoogleSignInFailed", "unexpected-credential");
                                }

                                @Override
                                public void onError(GetCredentialException error) {
                                    String reason = error instanceof GetCredentialCancellationException
                                            ? "cancelled"
                                            : error.getType() + ": " + error.getMessage();
                                    UnityPlayer.UnitySendMessage(gameObject, "OnGoogleSignInFailed", reason);
                                }
                            });
                } catch (Exception error) {
                    UnityPlayer.UnitySendMessage(gameObject, "OnGoogleSignInFailed", "start: " + error.getMessage());
                }
            }
        });
    }
}
