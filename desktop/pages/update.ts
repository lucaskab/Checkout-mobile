import type { Routes } from ".";
import { act, card, gameIcon, page } from "../view-kit";
import { updateStore, updateVersionLabel } from "../updates";

// "Versão nova disponível" (Lucas 10/11): opened by the host once a session when the store has a newer version
// (desktop/updates.ts). "Atualizar agora" opens the game's page in the App Store / Google Play (Unity:
// CheckoutLinks "store"); "Agora não" closes it and waits 2 days before offering the same version again.
export const routes: Routes = {
	atualizar: () => {
		const version = updateVersionLabel();
		return page(
			"atualizar",
			"Versão nova disponível",
			[
				card(version ? `Checkout ${version} chegou!` : "Uma versão nova do Checkout chegou!", {
					eyebrow: "ATUALIZAÇÃO",
					subtitle: "Atualize o jogo para ganhar o conteúdo novo e as correções. O seu progresso continua salvo.",
					icon: gameIcon("gift"),
					tone: "featured",
					lines: [
						updateStore.current ? `Você está na versão ${updateStore.current}.` : "",
						"Leva só um minuto na loja do seu celular.",
					].filter(Boolean),
					buttons: [
						act("Atualizar agora", "openLink", ["store"], { variant: "success", ok: "" }),
						act("Agora não", "snoozeAppUpdate", [updateStore.latest], { variant: "secondary", after: "back", ok: "" }),
					],
				}),
			],
			{ icon: gameIcon("gift"), subtitle: "Conteúdo novo e correções" },
		);
	},
};
