// "Chamar amigo" on the iPhone (CheckoutSocial.cs, social v1): the system share sheet with the invite text, the invite
// link (https://checkout-server.lucaslfurini.workers.dev/i/<code>) and a picture of the player's market.
#import <UIKit/UIKit.h>

extern UIViewController* UnityGetGLViewController(void);

static NSString* CheckoutShareText(const char* value) {
    return value ? [NSString stringWithUTF8String:value] : @"";
}

extern "C" void CheckoutShare_Share(const char* text, const char* url, const char* imagePath) {
    NSString* message = CheckoutShareText(text);
    NSString* link = CheckoutShareText(url);
    NSString* path = CheckoutShareText(imagePath);
    dispatch_async(dispatch_get_main_queue(), ^{
        NSMutableArray* items = [NSMutableArray array];
        if (message.length) [items addObject:message];
        NSURL* address = link.length ? [NSURL URLWithString:link] : nil;
        if (address) [items addObject:address];
        UIImage* picture = path.length ? [UIImage imageWithContentsOfFile:path] : nil;
        if (picture) [items addObject:picture];
        if (items.count == 0) return;
        UIViewController* root = UnityGetGLViewController();
        if (!root) return;
        UIActivityViewController* sheet = [[UIActivityViewController alloc] initWithActivityItems:items applicationActivities:nil];
        // iPad: the sheet is a popover and needs a place to come from (the middle of the screen).
        if (sheet.popoverPresentationController) {
            sheet.popoverPresentationController.sourceView = root.view;
            sheet.popoverPresentationController.sourceRect = CGRectMake(CGRectGetMidX(root.view.bounds), CGRectGetMidY(root.view.bounds), 1, 1);
            sheet.popoverPresentationController.permittedArrowDirections = 0;
        }
        [root presentViewController:sheet animated:YES completion:nil];
    });
}
