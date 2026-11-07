import { showCode } from "./codes.ts";
import { SOCIAL } from "./limits.ts";

/**
 * GET /i/<code>: the page an invite link opens (shared from the game's "Chamar amigo"). Self-contained — no external
 * scripts, fonts, images or trackers; one inline style and a few lines of inline script for "copy". Languages: pt-BR,
 * en, es, fr, de by Accept-Language (default en). The only server text in social v1.
 */
export const PLAY_PACKAGE = "com.lucasfurini.checkout";
export const APP_STORE_URL = "https://apps.apple.com/app/id6826304188";

const TEXT = {
	pt: {
		html: "pt-BR",
		tagline: "Simulador de Supermercado",
		invitedBy: (name: string) => `<strong>${name}</strong> convidou você para jogar Checkout`,
		invited: "Você foi convidado para jogar Checkout",
		plain: "Jogue Checkout com seus amigos",
		lead: "Monte seu próprio supermercado, visite o mercado dos amigos, troquem presentes e ajudem um ao outro.",
		codeLabel: "Código de convite",
		copy: "Copiar código",
		copied: "Copiado!",
		open: "Abrir no jogo",
		openHint: "Já tem o jogo?",
		play: "Baixar no Google Play",
		appStore: "Baixar na App Store",
		steps: ["Instale o Checkout", "Entre com Google ou Apple", "Abra Amigos e cole o código"],
		reward: (level: number, diamonds: number) => `Quando você chegar ao nível ${level}, vocês dois ganham ${diamonds} 💎.`,
		title: "Convite para o Checkout",
	},
	en: {
		html: "en",
		tagline: "Supermarket Sim",
		invitedBy: (name: string) => `<strong>${name}</strong> invited you to play Checkout`,
		invited: "You're invited to play Checkout",
		plain: "Play Checkout with your friends",
		lead: "Build your own supermarket, visit your friends' markets, send gifts and help each other out.",
		codeLabel: "Invite code",
		copy: "Copy code",
		copied: "Copied!",
		open: "Open in the game",
		openHint: "Already have the game?",
		play: "Get it on Google Play",
		appStore: "Download on the App Store",
		steps: ["Install Checkout", "Sign in with Google or Apple", "Open Friends and paste the code"],
		reward: (level: number, diamonds: number) => `Reach level ${level} and you both get ${diamonds} 💎.`,
		title: "Invite to Checkout",
	},
	es: {
		html: "es",
		tagline: "Simulador de Supermercado",
		invitedBy: (name: string) => `<strong>${name}</strong> te invitó a jugar Checkout`,
		invited: "Te invitaron a jugar Checkout",
		plain: "Juega Checkout con tus amigos",
		lead: "Construye tu propio supermercado, visita los mercados de tus amigos, envíense regalos y ayúdense.",
		codeLabel: "Código de invitación",
		copy: "Copiar código",
		copied: "¡Copiado!",
		open: "Abrir en el juego",
		openHint: "¿Ya tienes el juego?",
		play: "Disponible en Google Play",
		appStore: "Descargar en el App Store",
		steps: ["Instala Checkout", "Inicia sesión con Google o Apple", "Abre Amigos y pega el código"],
		reward: (level: number, diamonds: number) => `Al llegar al nivel ${level}, los dos ganan ${diamonds} 💎.`,
		title: "Invitación a Checkout",
	},
	fr: {
		html: "fr",
		tagline: "Simulateur de supermarché",
		invitedBy: (name: string) => `<strong>${name}</strong> t'invite à jouer à Checkout`,
		invited: "Tu es invité à jouer à Checkout",
		plain: "Joue à Checkout avec tes amis",
		lead: "Construis ton supermarché, visite ceux de tes amis, échangez des cadeaux et entraidez-vous.",
		codeLabel: "Code d'invitation",
		copy: "Copier le code",
		copied: "Copié !",
		open: "Ouvrir dans le jeu",
		openHint: "Tu as déjà le jeu ?",
		play: "Disponible sur Google Play",
		appStore: "Télécharger dans l'App Store",
		steps: ["Installe Checkout", "Connecte-toi avec Google ou Apple", "Ouvre Amis et colle le code"],
		reward: (level: number, diamonds: number) => `Au niveau ${level}, vous gagnez tous les deux ${diamonds} 💎.`,
		title: "Invitation à Checkout",
	},
	de: {
		html: "de",
		tagline: "Supermarkt-Simulator",
		invitedBy: (name: string) => `<strong>${name}</strong> hat dich zu Checkout eingeladen`,
		invited: "Du wurdest zu Checkout eingeladen",
		plain: "Spiel Checkout mit deinen Freunden",
		lead: "Bau deinen eigenen Supermarkt, besuch die Märkte deiner Freunde, schickt euch Geschenke und helft euch gegenseitig.",
		codeLabel: "Einladungscode",
		copy: "Code kopieren",
		copied: "Kopiert!",
		open: "Im Spiel öffnen",
		openHint: "Du hast das Spiel schon?",
		play: "Jetzt bei Google Play",
		appStore: "Laden im App Store",
		steps: ["Installiere Checkout", "Melde dich mit Google oder Apple an", "Öffne Freunde und füge den Code ein"],
		reward: (level: number, diamonds: number) => `Erreichst du Level ${level}, bekommt ihr beide ${diamonds} 💎.`,
		title: "Einladung zu Checkout",
	},
};
export type Lang = keyof typeof TEXT;

/** The best of pt / en / es / fr / de for an Accept-Language header (q-values honoured); en when none fits. */
export function pickLanguage(header: string | null): Lang {
	let best: Lang = "en";
	let bestQ = 0;
	for (const part of (header ?? "").slice(0, 400).split(",")) {
		const [tag, ...params] = part.trim().toLowerCase().split(";");
		const qParam = params.map((p) => p.trim()).find((p) => p.startsWith("q="));
		const q = qParam ? Number(qParam.slice(2)) : 1;
		const base = tag.split("-")[0];
		if (base in TEXT && Number.isFinite(q) && q > bestQ) {
			best = base as Lang;
			bestQ = q;
		}
	}
	return best;
}

export const escapeHtml = (text: string) =>
	text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);
/** A JS string literal that is safe inside <script> (no "</script>"). */
const jsString = (text: string) => JSON.stringify(text).replace(/</g, "\\u003c");

export const playUrl = (code: string | null) =>
	`https://play.google.com/store/apps/details?id=${PLAY_PACKAGE}${code ? `&referrer=${encodeURIComponent(`invite=${code}`)}` : ""}`;

/**
 * The page. `code`: the link's code when well formed (else null: no code box, plain store links); `marketName`: the
 * inviter's name when the code is known and the name is shown (else null: the same page without it).
 */
export function invitePage(code: string | null, marketName: string | null, lang: Lang, iphone = false) {
	const t = TEXT[lang];
	const name = marketName ? escapeHtml(marketName) : null;
	const heading = name ? t.invitedBy(name) : code ? t.invited : t.plain;
	const shown = code ? showCode(code) : "";
	const stores = [
		`<a class="store" href="${escapeHtml(playUrl(code))}">${svgPlay}<span>${t.play}</span></a>`,
		`<a class="store" href="${APP_STORE_URL}">${svgApple}<span>${t.appStore}</span></a>`,
	];
	if (iphone) stores.reverse();
	const title = name ? `${marketName} · ${t.title}` : t.title;
	return `<!doctype html>
<html lang="${t.html}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="referrer" content="no-referrer">
<meta name="theme-color" content="#1D2B4F">
<meta property="og:type" content="website">
<meta property="og:title" content="${escapeHtml(title)}">
<meta property="og:description" content="${escapeHtml(t.lead)}">
<title>${escapeHtml(title)}</title>
<style>
:root{--navy:#1D2B4F;--navy-2:#2A3B66;--gold:#D3A53D;--cream:#F6F0E1;--paper:#FFFCF4;--ink:#1D2B4F;--muted:#5B6584}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;min-height:100vh;background:var(--cream);color:var(--ink);font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;padding:24px 16px calc(32px + env(safe-area-inset-bottom))}
main{max-width:440px;margin:0 auto;background:var(--paper);border:1px solid var(--gold);border-radius:18px;overflow:hidden;box-shadow:0 10px 30px rgba(29,43,79,.12)}
header{background:var(--navy);color:var(--cream);text-align:center;padding:22px 20px 18px;border-bottom:2px solid var(--gold)}
.brand{margin:0;font-size:28px;font-weight:800;letter-spacing:.18em}
.tagline{margin:4px 0 0;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--gold)}
.body{padding:22px 20px 24px}
h1{margin:0 0 8px;font-size:22px;line-height:1.25;font-weight:700}
h1 strong{color:var(--navy-2);border-bottom:2px solid var(--gold)}
.lead{margin:0 0 20px;color:var(--muted)}
.code{border:1.5px dashed var(--gold);border-radius:14px;padding:14px;text-align:center;margin:0 0 18px}
.code small{display:block;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.code output{display:block;margin:4px 0 12px;font:700 30px/1.2 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.12em;color:var(--navy)}
button,.btn,.store{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;border-radius:12px;font-family:inherit;font-size:16px;font-weight:600;line-height:1.2;text-decoration:none;cursor:pointer}
button{border:0;background:var(--navy);color:var(--cream)}
button:active,.btn:active,.store:active{transform:translateY(1px)}
.stores{display:grid;gap:10px;margin:0 0 18px}
.store{border:1.5px solid var(--navy);background:var(--paper);color:var(--navy)}
.store svg{width:20px;height:20px;flex:none}
.open{margin:0 0 20px;text-align:center;color:var(--muted);font-size:14px}
.btn{border:1.5px solid var(--gold);color:var(--navy);background:transparent;margin-top:6px}
ol{list-style:none;counter-reset:s;margin:0 0 16px;padding:16px 0 0;border-top:1px solid rgba(211,165,61,.55)}
li{counter-increment:s;display:flex;align-items:center;gap:12px;margin:0 0 10px}
li::before{content:counter(s);flex:none;width:26px;height:26px;border-radius:50%;border:1.5px solid var(--gold);display:grid;place-items:center;font-size:13px;font-weight:700;color:var(--navy)}
.reward{margin:0;padding:10px 12px;border-radius:10px;background:rgba(211,165,61,.14);font-size:14px;text-align:center}
@media (min-width:480px){body{padding-top:48px}}
</style>
</head>
<body>
<main>
<header><p class="brand">CHECKOUT</p><p class="tagline">${t.tagline}</p></header>
<div class="body">
<h1>${heading}</h1>
<p class="lead">${t.lead}</p>
${
	code
		? `<div class="code"><small>${t.codeLabel}</small><output id="code">${shown}</output><button type="button" id="copy">${t.copy}</button></div>`
		: ""
}
<div class="stores">${stores.join("")}</div>
${code ? `<div class="open">${t.openHint}<a class="btn" href="checkout://add/${code}">${t.open}</a></div>` : ""}
<ol>${t.steps.map((step) => `<li>${step}</li>`).join("")}</ol>
<p class="reward">${t.reward(SOCIAL.inviteRewardLevel, SOCIAL.inviteRewardDiamonds)}</p>
</div>
</main>
${
	code
		? `<script>
(function(){var b=document.getElementById("copy"),c=${jsString(shown)},label=${jsString(t.copy)},done=${jsString(t.copied)};
function ok(){b.textContent=done;setTimeout(function(){b.textContent=label},2000)}
function old(){var a=document.createElement("textarea");a.value=c;a.setAttribute("readonly","");a.style.position="fixed";a.style.opacity="0";document.body.appendChild(a);a.select();try{document.execCommand("copy");ok()}catch(e){}document.body.removeChild(a)}
b.addEventListener("click",function(){if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(c).then(ok,old)}else{old()}});})();
</script>`
		: ""
}
</body>
</html>`;
}

const svgPlay =
	'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4.3 2.6c-.2.2-.3.6-.3 1v16.8c0 .4.1.8.3 1l9.4-9.4-9.4-9.4Zm10.8 8 2.7-2.7L6 1.3c-.3-.2-.7-.2-1-.1l10.1 9.4Zm0 2.8L5 22.8c.3.1.7.1 1-.1l11.8-6.6-2.7-2.7Zm4-3.9-2.6-1.5-2.9 2.9 2.9 2.9 2.6-1.5c.9-.5.9-1.9 0-2.8Z"/></svg>';
const svgApple =
	'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M16.4 12.6c0-2.4 2-3.6 2.1-3.7-1.1-1.7-2.9-1.9-3.5-1.9-1.5-.2-2.9.9-3.7.9-.8 0-1.9-.9-3.2-.8-1.6 0-3.1 1-4 2.4-1.7 3-.4 7.3 1.2 9.7.8 1.2 1.8 2.5 3 2.4 1.2 0 1.7-.8 3.1-.8 1.5 0 1.9.8 3.2.8 1.3 0 2.2-1.2 3-2.4.9-1.4 1.3-2.7 1.3-2.8 0 0-2.5-1-2.5-3.8ZM14 5.5c.7-.8 1.1-1.9 1-3-1 0-2.1.7-2.8 1.5-.6.7-1.2 1.8-1 2.9 1 .1 2.1-.6 2.8-1.4Z"/></svg>';

const PAGE_HEADERS = {
	"content-type": "text/html; charset=utf-8",
	"cache-control": "no-store",
	"content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
	"referrer-policy": "no-referrer",
	"x-content-type-options": "nosniff",
	"strict-transport-security": "max-age=31536000",
	vary: "accept-language",
};

export const pageResponse = (html: string) => new Response(html, { status: 200, headers: PAGE_HEADERS });
