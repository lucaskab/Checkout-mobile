import { createServer } from "node:http";
import { createApp } from "./app.ts";
import { prismaStore } from "./prisma-store.ts";
import { googleCodeExchange, googleVerifier } from "./tokens.ts";

// Settings (Render › Environment): DATABASE_URL (Prisma Postgres), SESSION_SECRET (Render generates it),
// GOOGLE_CLIENT_IDS (the game's OAuth client ids, comma-separated: web/server, desktop…),
// GOOGLE_DESKTOP_CLIENT_ID + GOOGLE_DESKTOP_CLIENT_SECRET (optional: login from the PC build and the Unity Editor).
const need = (name: string) => {
	const value = process.env[name];
	if (!value) throw new Error(`Missing setting ${name}`);
	return value;
};
const clientIds = need("GOOGLE_CLIENT_IDS").split(",").map((id) => id.trim()).filter(Boolean);
const sessionSecret = need("SESSION_SECRET");
if (sessionSecret.length < 32) throw new Error("SESSION_SECRET must be at least 32 characters");
need("DATABASE_URL");

const store = prismaStore();
const app = createApp({
	store,
	verifyGoogle: googleVerifier(clientIds),
	exchangeCode:
		process.env.GOOGLE_DESKTOP_CLIENT_ID && process.env.GOOGLE_DESKTOP_CLIENT_SECRET
			? googleCodeExchange(process.env.GOOGLE_DESKTOP_CLIENT_ID, process.env.GOOGLE_DESKTOP_CLIENT_SECRET)
			: null,
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
