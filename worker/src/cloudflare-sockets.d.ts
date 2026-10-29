// Type of the runtime module "cloudflare:sockets" (only what src/index.ts imports).
declare module "cloudflare:sockets" {
	export function connect(address: { hostname: string; port: number }, options?: { secureTransport?: "off" | "on" | "starttls"; allowHalfOpen?: boolean }): unknown;
}
