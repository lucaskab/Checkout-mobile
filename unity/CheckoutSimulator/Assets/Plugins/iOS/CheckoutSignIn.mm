// iPhone logins for the cloud saves (CheckoutCloud.cs, Lucas 19/10: the App Store asks for "Sign in with Apple" next to
// any other social login):
//   CheckoutApple_SignIn    the system's "Sign in with Apple" sheet (AuthenticationServices). The answer goes back
//                           to the Unity object with UnitySendMessage: OnAppleSignIn (JSON: identityToken,
//                           authorizationCode, name, email) or OnAppleSignInFailed ("cancelled" or the error).
//   CheckoutWeb_Start       a system web login sheet (ASWebAuthenticationSession) for Google's login page; it ends on
//                           the iOS OAuth client's own scheme: OnWebAuthDone (the callback URL) or OnWebAuthFailed.
//   CheckoutApple_Logo      Apple's logo from the system's own symbols ("apple.logo"), as a PNG for the button
//                           (the game never draws it itself). CheckoutApple_Free frees the bytes.
#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <AuthenticationServices/AuthenticationServices.h>
#include <stdlib.h>
#include <string.h>

extern "C" void UnitySendMessage(const char* obj, const char* method, const char* msg);
extern "C" UIViewController* UnityGetGLViewController();

static NSString* Text(const char* value) { return value ? [NSString stringWithUTF8String:value] : @""; }
static void Send(NSString* receiver, const char* method, NSString* message)
{
    UnitySendMessage(receiver.UTF8String, method, (message ?: @"").UTF8String);
}

@interface CheckoutSignIn : NSObject <ASAuthorizationControllerDelegate, ASAuthorizationControllerPresentationContextProviding, ASWebAuthenticationPresentationContextProviding>
@property (nonatomic, copy) NSString* receiver;
@property (nonatomic, strong) ASAuthorizationController* apple;
@property (nonatomic, strong) ASWebAuthenticationSession* web;
@end

@implementation CheckoutSignIn

- (UIWindow*)window
{
    UIWindow* window = UnityGetGLViewController().view.window;
    if (window) return window;
    for (UIScene* scene in UIApplication.sharedApplication.connectedScenes)
        if ([scene isKindOfClass:UIWindowScene.class])
            for (UIWindow* w in ((UIWindowScene*)scene).windows) if (w.isKeyWindow) return w;
    return nil;
}
- (ASPresentationAnchor)presentationAnchorForAuthorizationController:(ASAuthorizationController*)controller { return [self window]; }
- (ASPresentationAnchor)presentationAnchorForWebAuthenticationSession:(ASWebAuthenticationSession*)session { return [self window]; }

- (void)authorizationController:(ASAuthorizationController*)controller didCompleteWithAuthorization:(ASAuthorization*)authorization
{
    self.apple = nil;
    if (![authorization.credential isKindOfClass:ASAuthorizationAppleIDCredential.class])
    {
        Send(self.receiver, "OnAppleSignInFailed", @"no-credential");
        return;
    }
    ASAuthorizationAppleIDCredential* credential = (ASAuthorizationAppleIDCredential*)authorization.credential;
    NSString* token = credential.identityToken ? [[NSString alloc] initWithData:credential.identityToken encoding:NSUTF8StringEncoding] : @"";
    NSString* code = credential.authorizationCode ? [[NSString alloc] initWithData:credential.authorizationCode encoding:NSUTF8StringEncoding] : @"";
    // Apple gives the name and the e-mail only on the first login: the server keeps them.
    NSString* name = @"";
    if (credential.fullName)
        name = [NSPersonNameComponentsFormatter localizedStringFromPersonNameComponents:credential.fullName style:NSPersonNameComponentsFormatterStyleDefault options:0] ?: @"";
    NSDictionary* answer = @{ @"identityToken": token ?: @"", @"authorizationCode": code ?: @"", @"name": name, @"email": credential.email ?: @"" };
    NSData* json = [NSJSONSerialization dataWithJSONObject:answer options:0 error:nil];
    Send(self.receiver, "OnAppleSignIn", json ? [[NSString alloc] initWithData:json encoding:NSUTF8StringEncoding] : @"{}");
}

- (void)authorizationController:(ASAuthorizationController*)controller didCompleteWithError:(NSError*)error
{
    self.apple = nil;
    BOOL cancelled = error.code == ASAuthorizationErrorCanceled;
    Send(self.receiver, "OnAppleSignInFailed", cancelled ? @"cancelled" : (error.localizedDescription ?: @"error"));
}

@end

static CheckoutSignIn* shared;
static CheckoutSignIn* Shared(const char* receiver)
{
    if (!shared) shared = [[CheckoutSignIn alloc] init];
    shared.receiver = Text(receiver);
    return shared;
}

extern "C"
{
    void CheckoutApple_SignIn(const char* receiver)
    {
        CheckoutSignIn* signIn = Shared(receiver);
        ASAuthorizationAppleIDRequest* request = [[[ASAuthorizationAppleIDProvider alloc] init] createRequest];
        request.requestedScopes = @[ ASAuthorizationScopeFullName, ASAuthorizationScopeEmail ];
        ASAuthorizationController* controller = [[ASAuthorizationController alloc] initWithAuthorizationRequests:@[ request ]];
        controller.delegate = signIn;
        controller.presentationContextProvider = signIn;
        signIn.apple = controller;
        [controller performRequests];
    }

    void CheckoutWeb_Start(const char* url, const char* scheme, const char* receiver)
    {
        CheckoutSignIn* signIn = Shared(receiver);
        NSString* target = signIn.receiver;
        NSURL* address = [NSURL URLWithString:Text(url)];
        if (!address) { Send(target, "OnWebAuthFailed", @"bad-url"); return; }
        ASWebAuthenticationSession* session = [[ASWebAuthenticationSession alloc] initWithURL:address callbackURLScheme:Text(scheme) completionHandler:^(NSURL* callback, NSError* error) {
            signIn.web = nil;
            if (callback) Send(target, "OnWebAuthDone", callback.absoluteString);
            else Send(target, "OnWebAuthFailed", error.code == ASWebAuthenticationSessionErrorCodeCanceledLogin ? @"cancelled" : (error.localizedDescription ?: @"error"));
        }];
        session.presentationContextProvider = signIn;
        signIn.web = session;
        if (![session start]) { signIn.web = nil; Send(target, "OnWebAuthFailed", @"not-started"); }
    }

    int CheckoutApple_Logo(int size, unsigned char** bytes)
    {
        *bytes = NULL;
        UIImageSymbolConfiguration* config = [UIImageSymbolConfiguration configurationWithPointSize:size weight:UIImageSymbolWeightMedium];
        UIImage* symbol = [[UIImage systemImageNamed:@"apple.logo" withConfiguration:config] imageWithTintColor:UIColor.whiteColor renderingMode:UIImageRenderingModeAlwaysOriginal];
        if (!symbol) return 0;
        UIGraphicsImageRendererFormat* format = [UIGraphicsImageRendererFormat preferredFormat];
        format.scale = 1;
        CGSize canvas = CGSizeMake(size * 1.25, size * 1.25);
        UIImage* image = [[[UIGraphicsImageRenderer alloc] initWithSize:canvas format:format] imageWithActions:^(UIGraphicsImageRendererContext* context) {
            CGSize s = symbol.size;
            [symbol drawInRect:CGRectMake((canvas.width - s.width) / 2, (canvas.height - s.height) / 2, s.width, s.height)];
        }];
        NSData* png = UIImagePNGRepresentation(image);
        if (!png.length) return 0;
        *bytes = (unsigned char*)malloc(png.length);
        memcpy(*bytes, png.bytes, png.length);
        return (int)png.length;
    }

    void CheckoutApple_Free(void* bytes) { free(bytes); }
}
