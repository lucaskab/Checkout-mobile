import { createServer } from "node:http";
import { createApp } from "./app.ts";
import { prismaStore } from "./prisma-store.ts";
import { appleTokens, appleVerifier, googleCodeExchange, googleVerifier } from "./tokens.ts";

// Settings (Render › Environment): DATABASE_URL (Prisma Postgres), SESSION_SECRET (Render generates it),
// GOOGLE_CLIENT_IDS (the game's OAuth client ids, comma-separated: web/server, desktop…),
// GOOGLE_DESKTOP_CLIENT_ID + GOOGLE_DESKTOP_CLIENT_SECRET (optional: login from the PC build and the Unity Editor),
// GOOGLE_IOS_CLIENT_ID (optional: Google login on the iPhone; also list it in GOOGLE_CLIENT_IDS),
// APPLE_BUNDLE_IDS (Sign in with Apple: the iPhone app's bundle ids, comma-separated),
// APPLE_TEAM_ID + APPLE_KEY_ID + APPLE_PRIVATE_KEY (optional: the "Sign in with Apple" key, to revoke the Apple
// login when a player deletes the account; APPLE_PRIVATE_KEY is the .p8 file's text).
const need = (name: string) => {
	const value = process.env[name];
	if (!value) throw new Error(`Missing setting ${name}`);
	return value;
};
const clientIds = need("GOOGLE_CLIENT_IDS").split(",").map((id) => id.trim()).filter(Boolean);
const sessionSecret = need("SESSION_SECRET");
if (sessionSecret.length < 32) throw new Error("SESSION_SECRET must be at least 32 characters");
need("DATABASE_URL");

const appleBundleIds = (process.env.APPLE_BUNDLE_IDS ?? "").split(",").map((id) => id.trim()).filter(Boolean);
const appleKey =
	process.env.APPLE_TEAM_ID && process.env.APPLE_KEY_ID && process.env.APPLE_PRIVATE_KEY && appleBundleIds.length
		? {
				teamId: process.env.APPLE_TEAM_ID,
				keyId: process.env.APPLE_KEY_ID,
				// Render keeps line breaks; a key pasted on one line uses "\n".
				privateKey: process.env.APPLE_PRIVATE_KEY.replace(/\\n/g, "\n"),
				clientId: appleBundleIds[0],
			}
		: null;

const store = prismaStore();
const app = createApp({
	store,
	verifyGoogle: googleVerifier(clientIds),
	exchangeCode:
		process.env.GOOGLE_DESKTOP_CLIENT_ID && process.env.GOOGLE_DESKTOP_CLIENT_SECRET
			? googleCodeExchange(process.env.GOOGLE_DESKTOP_CLIENT_ID, process.env.GOOGLE_DESKTOP_CLIENT_SECRET)
			: null,
	exchangeIosCode: process.env.GOOGLE_IOS_CLIENT_ID ? googleCodeExchange(process.env.GOOGLE_IOS_CLIENT_ID) : null,
	verifyApple: appleBundleIds.length ? appleVerifier(appleBundleIds) : null,
	apple: appleKey ? appleTokens(appleKey) : null,
	sessionSecret,
	log: (line) => console.log(new Date().toISOString(), line),
});
const server = createServer(app);
server.requestTimeout = 30_000;
const port = Number(process.env.PORT ?? 3000);
server.listen(port, () => console.log(`checkout-server listening on ${port}`));

const stop = () => server.close(() => store.close().finally(() => process.exit(0)));
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
