QuickJS-ng v0.16.2 (https://github.com/quickjs-ng/quickjs, commit 1ab8676f4b6d6d669baeb5f21790fb9734636a20, MIT
license in LICENSE.txt): the engine's C sources (quickjs.c, libregexp.c, libunicode.c, dtoa.c and their headers),
unchanged except one line in cutils.h that includes checkout-qjs-names.h (prefixes for generic global names).
CheckoutJS.c is the game's bridge (the Android twin of Plugins/iOS/CheckoutJS.mm). IL2CPP compiles all .c files here
into the Android player (Android only; see each file's import settings).
