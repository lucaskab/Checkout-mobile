import type { Routes } from ".";
import { cloudStore, describeSummary, exportSave, formatAgo, isAhead } from "../cloud";
import { act, card, gameIcon, page } from "../view-kit";

// "Conta" (Guia › Conta e nuvem; also the Opções tab "Conta" in Unity): sign in with Google (or Apple on the iPhone) so the market, coins and diamonds follow the player to a new
// phone (Lucas 12/10). Unity does the login and the uploads (CheckoutCloud.cs); this page shows where things stand.
export function accountStatusLine(now = Date.now()) {
	switch (cloudStore.status) {
		case "unavailable":
			return "Salvar na nuvem não está disponível nesta versão.";
		case "signed-out":
			return cloudStore.error || "Progresso salvo só neste aparelho.";
		case "signing-in":
			return "Entrando…";
		case "syncing":
			return "Salvando na nuvem…";
		case "offline":
			return "Sem conexão: o progresso fica neste aparelho e vai para a nuvem quando a internet voltar.";
		case "conflict":
			return "Este aparelho e a nuvem têm progressos diferentes: escolha qual continua.";
		case "error":
			return cloudStore.error || "Não deu para falar com o servidor. Tente de novo daqui a pouco.";
		default:
			return cloudStore.lastSyncAt ? `Tudo salvo na nuvem · ${formatAgo(cloudStore.lastSyncAt, now)}` : "Conectado à nuvem.";
	}
}

/** "Política de privacidade" and "Suporte" (App Store rule 5.1.1(i)): on this page and in the Guia. */
export function linksCard() {
	return card("Privacidade e suporte", {
		icon: gameIcon("clipboard"),
		eyebrow: "SOBRE O JOGO",
		lines: ["Como o jogo cuida dos seus dados e como falar com a gente."],
		buttons: [
			act("Política de privacidade", "openLink", ["privacy"], { variant: "secondary", ok: "Abrindo no navegador…" }),
			act("Suporte", "openLink", ["support"], { variant: "secondary", ok: "Abrindo no navegador…" }),
		],
	});
}

export const routes: Routes = {
	conta: () => {
		const now = Date.now();
		const icon = gameIcon("smartphone");
		const status = cloudStore.status;
		const signedIn = !["unavailable", "signed-out", "signing-in"].includes(status);
		const cards = [];

		if (status === "conflict" && cloudStore.conflict) {
			const local = exportSave().summary;
			const cloud = cloudStore.conflict.cloud;
			const localAhead = isAhead(local, cloud);
			cards.push(
				card("Qual progresso continua?", {
					icon: gameIcon("warning"),
					tone: "warning",
					lines: [
						cloudStore.conflict.otherAccount
							? "O progresso deste aparelho é de outra conta. Esta conta já tem um progresso na nuvem."
							: "Este aparelho e a sua conta têm progressos diferentes (você jogou em outro aparelho).",
						"O que você não escolher é substituído. Por segurança, o servidor guarda cópias recentes.",
					],
				}),
				card("Progresso da nuvem", {
					icon: gameIcon("diamond"),
					eyebrow: cloudStore.conflict.cloudAt ? `SALVO ${formatAgo(cloudStore.conflict.cloudAt, now).toUpperCase()}` : "NA NUVEM",
					badge: !localAhead ? "Mais avançado" : "",
					lines: describeSummary(cloud),
					buttons: [act("Continuar com a nuvem", "cloudResolve", ["cloud"], { variant: "success", ok: "Carregando o progresso da nuvem…" })],
				}),
				card("Progresso deste aparelho", {
					icon,
					eyebrow: "NESTE APARELHO",
					badge: localAhead ? "Mais avançado" : "",
					lines: describeSummary(local),
					buttons: [act("Continuar com este aparelho", "cloudResolve", ["device"], { variant: "primary", ok: "Enviando o progresso deste aparelho…" })],
				}),
			);
		} else if (!signedIn) {
			// Lucas 19/10: Google and, on the iPhone, Apple (the App Store asks for it next to Google).
			const providers = cloudStore.providers.length ? cloudStore.providers : ["google" as const];
			const canSignIn = status === "signed-out";
			cards.push(
				card("Salve o seu progresso", {
					icon: gameIcon("key"),
					eyebrow: "CONTA",
					tone: status === "unavailable" ? "locked" : "info",
					lines: [
						// The text names only the buttons this device shows (the iPhone has just Apple for now).
						providers.includes("apple") && providers.includes("google")
							? "Entre com a Apple ou com o Google para guardar o mercado, as moedas e os diamantes na nuvem."
							: providers.includes("apple")
								? "Entre com a Apple para guardar o mercado, as moedas e os diamantes na nuvem."
								: "Entre com o Google para guardar o mercado, as moedas e os diamantes na nuvem.",
						"Trocou de celular? É só entrar com a mesma conta e continuar de onde parou.",
						accountStatusLine(now),
					],
					buttons: providers.map((provider) =>
						act(
							status === "signing-in" ? "Entrando…" : provider === "apple" ? "Iniciar sessão com a Apple" : "Entrar com Google",
							"cloudSignIn",
							[provider],
							{
								variant: provider === "apple" ? "secondary" : "success",
								enabled: canSignIn,
								ok: provider === "apple" ? "Abrindo o login da Apple…" : "Abrindo o login do Google…",
							},
						),
					),
				}),
			);
		} else {
			cards.push(
				card(cloudStore.name || (cloudStore.provider === "apple" ? "Conta Apple" : "Conta Google"), {
					icon: gameIcon("success"),
					eyebrow: "CONECTADO",
					subtitle: cloudStore.email,
					tone: status === "synced" ? "success" : status === "error" ? "danger" : status === "offline" ? "warning" : "info",
					lines: [accountStatusLine(now)],
					buttons: [
						act(status === "syncing" ? "Salvando…" : "Salvar agora", "cloudSync", [], { variant: "primary", enabled: status !== "syncing", ok: "Salvando na nuvem…" }),
						act("Sair", "cloudSignOut", [], { variant: "secondary", ok: "Você saiu. O progresso continua neste aparelho." }),
					],
				}),
				card("Apagar conta", {
					icon: gameIcon("warning"),
					tone: "danger",
					lines: [
						"Apaga a sua conta e o progresso guardado na nuvem, para sempre. O progresso neste aparelho continua.",
						...(cloudStore.confirmDeleteUntil > now ? ["Toque de novo para confirmar."] : []),
					],
					buttons: [act("Apagar conta", "cloudDeleteAccount", [], { variant: "danger", ok: "Apagando a conta…" })],
				}),
			);
		}
		cards.push(linksCard());
		return page("conta", "Conta e nuvem", cards, { icon, subtitle: "Seu progresso em qualquer celular" });
	},
};
