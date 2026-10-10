// Runs the game's logic (store, timers, pages: desktop/host.ts bundled by scripts/release/build-embedded.ts into
// Resources/CheckoutGame/game.txt) inside the Unity player on the iPhone, in the system JavaScript engine
// (JavaScriptCore). This is what makes the iOS build the whole game on its own: no separate program and no
// React Native app around it. CheckoutDesktopHost (C#) drives it from the main thread:
//   CheckoutJS_Start  evaluates the game with the language and the save file,
//   CheckoutJS_Send   hands it one message from Unity (the same JSON the desktop host reads on stdin),
//   CheckoutJS_Tick   runs its due timers (every frame),
//   CheckoutJS_Poll   takes its next outgoing message (the same JSON the desktop host writes on stdout),
//   CheckoutJS_Flush  writes the save now (the app goes to the background).
#import <Foundation/Foundation.h>
#import <JavaScriptCore/JavaScriptCore.h>
#include <string.h>
#include <stdlib.h>

static JSContext* context;
static JSValue *receiveFunction, *tickFunction, *flushFunction;
static NSMutableArray<NSString*>* outbox;
static NSString* savePath;

static NSString* Text(const char* bytes, int length)
{
    if (!bytes || length <= 0) return @"";
    return [[NSString alloc] initWithBytes:bytes length:(NSUInteger)length encoding:NSUTF8StringEncoding] ?: @"";
}
static bool Callable(JSValue* value) { return value && ![value isUndefined] && ![value isNull]; }

extern "C"
{
    bool CheckoutJS_Start(const char* script, int scriptLength, const char* lang, int langLength, const char* save, int saveLength)
    {
        context = [[JSContext alloc] init];
        context.name = @"Checkout game";
        outbox = [NSMutableArray array];
        savePath = Text(save, saveLength);
        context.exceptionHandler = ^(JSContext* c, JSValue* exception) {
            NSLog(@"CHECKOUT_JS exception: %@\n%@", exception, [exception objectForKeyedSubscript:@"stack"]);
        };
        JSValue* native = [JSValue valueWithNewObjectInContext:context];
        native[@"lang"] = Text(lang, langLength);
        native[@"send"] = ^(NSString* line) { if (line) [outbox addObject:line]; };
        native[@"log"] = ^(NSString* text) { NSLog(@"CHECKOUT_JS %@", text); };
        // The save is replaced atomically (written next to it, then moved over it): a crash never leaves half a file.
        native[@"save"] = ^(NSString* text) {
            NSError* error = nil;
            if (![text writeToFile:savePath atomically:YES encoding:NSUTF8StringEncoding error:&error])
                NSLog(@"CHECKOUT_JS could not write the save: %@", error);
        };
        native[@"load"] = ^NSString*() {
            NSString* text = [NSString stringWithContentsOfFile:savePath encoding:NSUTF8StringEncoding error:nil];
            if (text.length > 0)
            {
                // A copy of the last save that loaded, in case something goes wrong later.
                NSString* backup = [savePath stringByAppendingString:@".bak"];
                [[NSFileManager defaultManager] removeItemAtPath:backup error:nil];
                [[NSFileManager defaultManager] copyItemAtPath:savePath toPath:backup error:nil];
            }
            return text ?: @"";
        };
        context[@"__native"] = native;
        [context evaluateScript:Text(script, scriptLength) withSourceURL:[NSURL URLWithString:@"checkout-game.js"]];
        receiveFunction = context[@"__checkoutReceive"];
        tickFunction = context[@"__checkoutTick"];
        flushFunction = context[@"__checkoutFlush"];
        return Callable(receiveFunction) && Callable(tickFunction);
    }

    void CheckoutJS_Send(const char* json, int length)
    {
        if (Callable(receiveFunction)) [receiveFunction callWithArguments:@[Text(json, length)]];
    }

    void CheckoutJS_Tick()
    {
        if (Callable(tickFunction)) [tickFunction callWithArguments:@[]];
    }

    void CheckoutJS_Flush()
    {
        if (Callable(flushFunction)) [flushFunction callWithArguments:@[]];
    }

    // The next outgoing message as UTF-8 bytes (malloc'd; the caller frees it with CheckoutJS_Free), or NULL.
    char* CheckoutJS_Poll(int* length)
    {
        *length = 0;
        if (outbox.count == 0) return NULL;
        NSString* line = outbox.firstObject;
        [outbox removeObjectAtIndex:0];
        NSData* data = [line dataUsingEncoding:NSUTF8StringEncoding];
        char* bytes = (char*)malloc(data.length + 1);
        memcpy(bytes, data.bytes, data.length);
        bytes[data.length] = 0;
        *length = (int)data.length;
        return bytes;
    }

    void CheckoutJS_Free(char* bytes) { free(bytes); }
}
