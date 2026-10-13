// Runs the game's logic (store, timers, pages: desktop/host.ts bundled by scripts/release/build-embedded.ts into
// Resources/CheckoutGame/game.txt) inside the Unity player on Android, in QuickJS (the engine's C sources sit next
// to this file and IL2CPP compiles them into the player). It is the Android twin of Plugins/iOS/CheckoutJS.mm
// (JavaScriptCore on the iPhone) and exposes the same C functions, which CheckoutDesktopHost (C#) calls from the
// main thread:
//   CheckoutJS_Start  evaluates the game with the language and the save file,
//   CheckoutJS_Send   hands it one message from Unity (the same JSON the desktop host reads on stdin),
//   CheckoutJS_Tick   runs its due timers (every frame),
//   CheckoutJS_Poll   takes its next outgoing message (the same JSON the desktop host writes on stdout),
//   CheckoutJS_Flush  writes the save now (the app goes to the background).
// QuickJS has no event loop of its own: promise jobs run after every call into the game (RunJobs).
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "quickjs.h"

#ifdef __ANDROID__
#include <android/log.h>
#define CHECKOUT_LOG(...) __android_log_print(ANDROID_LOG_INFO, "Unity", __VA_ARGS__)
#else
#define CHECKOUT_LOG(...) (fprintf(stderr, __VA_ARGS__), fputc('\n', stderr))
#endif

typedef struct
{
    char* bytes;
    int length;
} Message;

static JSRuntime* runtime;
static JSContext* context;
static JSValue receiveFunction, tickFunction, flushFunction;
static Message* outbox;
static int outboxHead, outboxCount, outboxCapacity;
static char* savePath;

static void LogException(const char* where)
{
    JSValue exception = JS_GetException(context);
    const char* text = JS_ToCString(context, exception);
    JSValue stack = JS_IsObject(exception) ? JS_GetPropertyStr(context, exception, "stack") : JS_UNDEFINED;
    const char* trace = JS_IsUndefined(stack) ? NULL : JS_ToCString(context, stack);
    CHECKOUT_LOG("CHECKOUT_JS exception (%s): %s\n%s", where, text ? text : "?", trace ? trace : "");
    if (trace) JS_FreeCString(context, trace);
    if (text) JS_FreeCString(context, text);
    JS_FreeValue(context, stack);
    JS_FreeValue(context, exception);
}

// Promise callbacks and other queued jobs: JavaScriptCore runs them on its own after each call, QuickJS does not.
static void RunJobs(void)
{
    JSContext* jobContext;
    for (int guard = 0; guard < 100000; guard++)
    {
        int result = JS_ExecutePendingJob(runtime, &jobContext);
        if (result == 0) return;
        if (result < 0)
        {
            JSContext* saved = context;
            context = jobContext;
            LogException("job");
            context = saved;
        }
    }
}

static bool Callable(JSValueConst value) { return context && JS_IsFunction(context, value); }

static void Call(JSValueConst function, int argc, JSValueConst* argv, const char* where)
{
    if (!Callable(function)) return;
    JSValue result = JS_Call(context, function, JS_UNDEFINED, argc, argv);
    if (JS_IsException(result)) LogException(where);
    JS_FreeValue(context, result);
    RunJobs();
}

static char* Copy(const char* bytes, int length)
{
    if (!bytes || length < 0) length = 0;
    char* text = (char*)malloc((size_t)length + 1);
    if (!text) return NULL;
    if (length > 0) memcpy(text, bytes, (size_t)length);
    text[length] = 0;
    return text;
}

// ------------------------------------------------------------------ the __native object the game sees

static JSValue NativeSend(JSContext* ctx, JSValueConst self, int argc, JSValueConst* argv)
{
    size_t length;
    const char* line = argc > 0 ? JS_ToCStringLen(ctx, &length, argv[0]) : NULL;
    if (!line) return JS_UNDEFINED;
    if (outboxHead + outboxCount == outboxCapacity)
    {
        if (outboxHead > 0)
        {
            memmove(outbox, outbox + outboxHead, sizeof(Message) * (size_t)outboxCount);
            outboxHead = 0;
        }
        else
        {
            int capacity = outboxCapacity ? outboxCapacity * 2 : 64;
            Message* grown = (Message*)realloc(outbox, sizeof(Message) * (size_t)capacity);
            if (!grown)
            {
                JS_FreeCString(ctx, line);
                return JS_UNDEFINED;
            }
            outbox = grown;
            outboxCapacity = capacity;
        }
    }
    Message* slot = &outbox[outboxHead + outboxCount];
    slot->bytes = Copy(line, (int)length);
    slot->length = slot->bytes ? (int)length : 0;
    if (slot->bytes) outboxCount++;
    JS_FreeCString(ctx, line);
    return JS_UNDEFINED;
}

static JSValue NativeLog(JSContext* ctx, JSValueConst self, int argc, JSValueConst* argv)
{
    const char* text = argc > 0 ? JS_ToCString(ctx, argv[0]) : NULL;
    if (text)
    {
        CHECKOUT_LOG("CHECKOUT_JS %s", text);
        JS_FreeCString(ctx, text);
    }
    return JS_UNDEFINED;
}

static bool WriteFile(const char* path, const char* bytes, size_t length)
{
    FILE* file = fopen(path, "wb");
    if (!file) return false;
    bool ok = fwrite(bytes, 1, length, file) == length;
    ok = fflush(file) == 0 && ok;
    ok = fsync(fileno(file)) == 0 && ok;
    return fclose(file) == 0 && ok;
}

// The save is replaced atomically (written next to it, then moved over it): a crash never leaves half a file.
static JSValue NativeSave(JSContext* ctx, JSValueConst self, int argc, JSValueConst* argv)
{
    size_t length;
    const char* text = argc > 0 ? JS_ToCStringLen(ctx, &length, argv[0]) : NULL;
    if (!text || !savePath) return JS_UNDEFINED;
    size_t pathLength = strlen(savePath);
    char* temporary = (char*)malloc(pathLength + 5);
    if (temporary)
    {
        memcpy(temporary, savePath, pathLength);
        memcpy(temporary + pathLength, ".tmp", 5);
        if (!WriteFile(temporary, text, length) || rename(temporary, savePath) != 0)
            CHECKOUT_LOG("CHECKOUT_JS could not write the save (%s)", strerror(errno));
        free(temporary);
    }
    JS_FreeCString(ctx, text);
    return JS_UNDEFINED;
}

static char* ReadFile(const char* path, size_t* length)
{
    *length = 0;
    FILE* file = fopen(path, "rb");
    if (!file) return NULL;
    char* bytes = NULL;
    if (fseek(file, 0, SEEK_END) == 0)
    {
        long size = ftell(file);
        if (size > 0 && fseek(file, 0, SEEK_SET) == 0 && (bytes = (char*)malloc((size_t)size + 1)))
        {
            *length = fread(bytes, 1, (size_t)size, file);
            bytes[*length] = 0;
        }
    }
    fclose(file);
    return bytes;
}

static JSValue NativeLoad(JSContext* ctx, JSValueConst self, int argc, JSValueConst* argv)
{
    size_t length = 0;
    char* text = savePath ? ReadFile(savePath, &length) : NULL;
    if (!text || length == 0)
    {
        free(text);
        return JS_NewString(ctx, "");
    }
    // A copy of the last save that loaded, in case something goes wrong later.
    size_t pathLength = strlen(savePath);
    char* backup = (char*)malloc(pathLength + 5);
    if (backup)
    {
        memcpy(backup, savePath, pathLength);
        memcpy(backup + pathLength, ".bak", 5);
        WriteFile(backup, text, length);
        free(backup);
    }
    JSValue value = JS_NewStringLen(ctx, text, length);
    free(text);
    return value;
}

// ------------------------------------------------------------------ the C API (same as Plugins/iOS/CheckoutJS.mm)

static void ClearOutbox(void)
{
    for (int i = 0; i < outboxCount; i++) free(outbox[outboxHead + i].bytes);
    outboxHead = outboxCount = 0;
}

bool CheckoutJS_Start(const char* script, int scriptLength, const char* lang, int langLength, const char* save, int saveLength)
{
    // Starting again (the scene was reloaded): the previous game writes its save first, then its engine is freed.
    if (context)
    {
        Call(flushFunction, 0, NULL, "flush before restart");
        JS_FreeValue(context, receiveFunction);
        JS_FreeValue(context, tickFunction);
        JS_FreeValue(context, flushFunction);
        JS_FreeContext(context);
        JS_FreeRuntime(runtime);
        context = NULL;
        runtime = NULL;
    }
    receiveFunction = tickFunction = flushFunction = JS_UNDEFINED;
    ClearOutbox();
    free(savePath);
    savePath = Copy(save, saveLength);

    runtime = JS_NewRuntime();
    if (!runtime) return false;
    // The Unity main thread's stack is smaller than QuickJS assumes: overflowing it throws a RangeError instead of crashing.
    JS_SetMaxStackSize(runtime, 512 * 1024);
    context = JS_NewContext(runtime);
    if (!context) return false;

    JSValue global = JS_GetGlobalObject(context);
    JSValue native = JS_NewObject(context);
    JS_SetPropertyStr(context, native, "lang", JS_NewStringLen(context, lang ? lang : "", lang && langLength > 0 ? (size_t)langLength : 0));
    JS_SetPropertyStr(context, native, "platform", JS_NewString(context, "android"));
    JS_SetPropertyStr(context, native, "send", JS_NewCFunction(context, NativeSend, "send", 1));
    JS_SetPropertyStr(context, native, "log", JS_NewCFunction(context, NativeLog, "log", 1));
    JS_SetPropertyStr(context, native, "save", JS_NewCFunction(context, NativeSave, "save", 1));
    JS_SetPropertyStr(context, native, "load", JS_NewCFunction(context, NativeLoad, "load", 0));
    JS_SetPropertyStr(context, global, "__native", native);

    // JS_Eval needs the source to end with a zero byte.
    char* source = Copy(script, scriptLength);
    if (!source)
    {
        JS_FreeValue(context, global);
        return false;
    }
    JSValue result = JS_Eval(context, source, (size_t)(scriptLength > 0 ? scriptLength : 0), "checkout-game.js", JS_EVAL_TYPE_GLOBAL);
    free(source);
    // Like JavaScriptCore on the iPhone, an error while loading is logged and the game still runs if it got as far
    // as installing its message handlers.
    if (JS_IsException(result)) LogException("start");
    JS_FreeValue(context, result);
    RunJobs();

    receiveFunction = JS_GetPropertyStr(context, global, "__checkoutReceive");
    tickFunction = JS_GetPropertyStr(context, global, "__checkoutTick");
    flushFunction = JS_GetPropertyStr(context, global, "__checkoutFlush");
    JS_FreeValue(context, global);
    return Callable(receiveFunction) && Callable(tickFunction);
}

void CheckoutJS_Send(const char* json, int length)
{
    if (!context) return;
    JSValue line = JS_NewStringLen(context, json ? json : "", json && length > 0 ? (size_t)length : 0);
    Call(receiveFunction, 1, (JSValueConst*)&line, "receive");
    JS_FreeValue(context, line);
}

void CheckoutJS_Tick(void) { Call(tickFunction, 0, NULL, "tick"); }

void CheckoutJS_Flush(void) { Call(flushFunction, 0, NULL, "flush"); }

// The next outgoing message as UTF-8 bytes (malloc'd; the caller frees it with CheckoutJS_Free), or NULL.
char* CheckoutJS_Poll(int* length)
{
    *length = 0;
    if (outboxCount == 0) return NULL;
    Message message = outbox[outboxHead++];
    if (--outboxCount == 0) outboxHead = 0;
    *length = message.length;
    return message.bytes;
}

void CheckoutJS_Free(char* bytes) { free(bytes); }
