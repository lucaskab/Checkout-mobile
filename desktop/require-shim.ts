// Asset modules call require("…png"); on desktop the path itself is the icon id.
(globalThis as { require?: (path: string) => string }).require ??= (path) => path;
// The desktop build is a test harness, so the dev-only store actions stay enabled.
(globalThis as { __DEV__?: boolean }).__DEV__ ??= true;
