/**
 * Makes a token for the Worker's temporary /admin/* routes (see src/admin.ts): node scripts/admin-token.ts <private.pem>
 * [minutes, at most 120]. The private key never leaves this computer; the Worker only has the public key
 * (ADMIN_PUBLIC_KEY). Without a key file: node scripts/admin-token.ts --new <private.pem> makes a key pair and prints
 * the public key to paste as ADMIN_PUBLIC_KEY.
 */
import { generateKeyPairSync, sign } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";

const [first, second] = process.argv.slice(2);
if (first === "--new") {
	const pair = generateKeyPairSync("ec", { namedCurve: "P-256" });
	writeFileSync(second, pair.privateKey.export({ format: "pem", type: "pkcs8" }), { mode: 0o600 });
	console.log(pair.publicKey.export({ format: "der", type: "spki" }).toString("base64"));
} else {
	const minutes = Math.min(120, Number(second ?? "60"));
	const until = Date.now() + minutes * 60_000 - 5_000;
	const signature = sign("sha256", Buffer.from(`checkout-admin:${until}`), { key: readFileSync(first, "utf8"), dsaEncoding: "ieee-p1363" });
	console.log(`${until}.${signature.toString("base64url")}`);
}
