import { t } from "@/i18n";
import type { GameIconId } from "@/data/game-icon-assets";
import { onboardingGuide } from "@/data/onboarding";
import { getNextGoal } from "@/services/onboarding";
import type { Routes } from ".";
import { act, card, gameIcon, go, page } from "../view-kit";
import { accountStatusLine, linksCard } from "./account";

// "Guia" (the "?" button of the top bar): what each part of the screen does, the next objective and a
// button to play the tutorial again. For players who skipped it or forgot where something is.
export const routes: Routes = {
	guia: (state) => {
		const goal = getNextGoal(
			{ ...state, onboarding: { ...state.onboarding, status: "done" } },
			{ lot: gameIcon("key"), coin: gameIcon("coin"), build: gameIcon("construction"), done: gameIcon("success") },
		);
		return page("guia", "Guia do mercado", [
			// Lucas 12/10: the progress follows the player to a new phone.
			card("Conta e nuvem", {
				icon: gameIcon("smartphone"),
				eyebrow: "SEU PROGRESSO",
				lines: [accountStatusLine()],
				buttons: [go("Abrir", "conta", { icon: gameIcon("key") })],
			}),
			card("O seu objetivo", {
				icon: gameIcon("target"),
				eyebrow: "DONA NEIDE EXPLICA",
				lines: [
					"Transforme a mesinha da calçada no maior supermercado da cidade, e depois numa rede!",
					"O ciclo: abra a loja, atenda no caixa, reponha a vitrine, peça mercadoria ao atacado e suba de nível.",
					// the goal's own sentences are translated before they go inside this one
					goal.text ? `Agora: ${t(goal.text)} (${t(goal.detail)})` : "",
				].filter(Boolean),
				buttons: [
					act("Rever tutorial", "restartOnboarding", [], { variant: "success", after: "back", ok: "Vamos lá!" }),
				],
				tone: "info",
			}),
			...onboardingGuide.map((item) =>
				card(item.title, { icon: gameIcon(item.icon as GameIconId), lines: [item.text] }),
			),
			linksCard(),
		], { icon: gameIcon("clipboard"), subtitle: "Onde fica cada coisa e o que ela faz" });
	},
};
