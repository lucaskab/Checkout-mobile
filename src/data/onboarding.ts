import type { OnboardingTarget } from "@/@types/onboarding";

// Texts and order of the first-time tutorial (rules in src/services/onboarding.ts).
// Patterned on Hay Day / Township: one action per step, the guide points at the exact thing to tap,
// a small prize after the important steps, the player can skip at the start and replay it in "Guia".

export const ONBOARDING_GUIDE = "Dona Neide";
/** Picture of the guide (Resources/CheckoutDesktop/Game/<art>.png; Unity falls back to an icon). */
export const ONBOARDING_GUIDE_ART = "guide_neide";

export type OnboardingStepMode =
	/** Centered card over a dimmed screen, with a button. */
	| "modal"
	/** Dims the screen around the target and points at it (the player must tap it). */
	| "spotlight"
	/** A speech bubble near the target, the rest of the screen stays playable. */
	| "bubble";

export type OnboardingStepId =
	| "boas-vindas"
	| "mesinha"
	| "vitrine"
	| "abrir"
	| "dia-livre"
	| "primeiro-cliente"
	| "caixa"
	| "estoque"
	| "deposito"
	| "entregas"
	| "pedir"
	| "caminhao"
	| "descarregar"
	| "missoes"
	| "conta"
	| "objetivo";

export type OnboardingStepDef = {
	id: OnboardingStepId;
	mode: OnboardingStepMode;
	title: string;
	text: string;
	/** What to do while one of the game windows (register, shop, dock…) covers the screen. */
	gameText?: string;
	target: OnboardingTarget;
	/** Label of the button that finishes a modal/bubble step ("" = the step finishes by playing). */
	button?: string;
	reward?: { coins: number; diamonds: number; text: string };
};

export const onboardingSteps: OnboardingStepDef[] = [
	{
		id: "boas-vindas",
		mode: "modal",
		title: "Bem-vindo ao Checkout!",
		text:
			"Oi! Eu sou a Dona Neide, feirante há 40 anos aqui no bairro. Esta mesinha agora é sua! " +
			"O seu sonho: transformar ela no maior supermercado da cidade, e depois numa rede inteira. Eu te ensino o começo!",
		target: "",
		button: "Vamos lá!",
	},
	{
		id: "mesinha",
		mode: "spotlight",
		title: "A sua mesinha",
		text: "Estes caixotes são a sua vitrine. Toque em PRODUTOS para ver o que você vende.",
		// Produtos opens on Prateleiras (desktop/sections.ts); with trucks at the dock it opens on Estoque instead.
		target: "route:!store|tool:!products",
	},
	{
		id: "vitrine",
		mode: "bubble",
		title: "Produtos e preços",
		text:
			"Aqui você vê quanto tem de cada produto na mesinha, o preço e o lucro. O preço sugerido já é bom para começar. " +
			"Quando quiser, toque no X para fechar a janela.",
		target: "",
		button: "Entendi",
	},
	{
		id: "abrir",
		mode: "spotlight",
		title: "Hora de abrir!",
		text: "Os clientes só vêm com a loja aberta. Toque em ABRIR para começar o seu primeiro dia.",
		target: "market",
	},
	{
		id: "dia-livre",
		mode: "spotlight",
		title: "Seu primeiro dia",
		text:
			"Cada dia dura 5 minutos. Escolha um contrato, uma meta que dá moedas e XP a mais, e toque em ACEITAR E ABRIR.",
		target: "action:startDay",
	},
	{
		id: "primeiro-cliente",
		mode: "bubble",
		title: "Lá vem freguês!",
		text: "Os clientes pegam o que querem na mesinha e depois vão até o caixa para pagar. Espere o primeiro chegar...",
		target: "",
	},
	{
		id: "caixa",
		mode: "spotlight",
		title: "Cliente no caixa!",
		text: "Toque em CAIXA para atender: passe as compras, receba o pagamento e dê o troco certinho.",
		gameText: "Siga a mãozinha: passe os produtos, receba e dê o troco. Troco certo deixa o cliente feliz!",
		target: "fab:caixa|world:checkout",
		reward: { coins: 20, diamonds: 0, text: "Primeira venda!" },
	},
	{
		id: "estoque",
		mode: "spotlight",
		title: "O seu depósito",
		text: "O que não cabe na mesinha fica guardado no depósito. Toque em PRODUTOS e depois na aba ESTOQUE.",
		// The Estoque tab of the open window, else the Produtos button.
		target: "route:!products|tool:!store",
	},
	{
		id: "deposito",
		mode: "bubble",
		title: "Fique de olho no estoque",
		text:
			"Cada produto tem um limite no depósito. Quando estiver acabando, é hora de pedir mais ao atacado. Toque no X para fechar a janela e continuar.",
		target: "",
		button: "Entendi",
	},
	{
		id: "entregas",
		mode: "spotlight",
		title: "Seu primeiro pedido",
		text: "Vamos comprar mercadoria do atacado. Abra PRODUTOS e toque na aba ENTREGAS.",
		target: "route:!suppliers|tool:!store|tool:!products",
	},
	{
		id: "pedir",
		mode: "spotlight",
		title: "Faça o pedido",
		text: "Toque em FAZER PEDIDO. Essa primeira entrega é expressa: o caminhão chega em instantes!",
		gameText: "Toque em + CARRINHO em um produto e depois em FAZER PEDIDO.",
		target: "route:@shop|action:placeSupplierCart|action:orderLowStock",
	},
	{
		id: "caminhao",
		mode: "bubble",
		title: "O caminhão está vindo!",
		text: "O caminhão do atacado já saiu. Enquanto isso, continue atendendo os clientes no caixa.",
		target: "",
	},
	{
		id: "descarregar",
		mode: "spotlight",
		title: "Chegou a mercadoria!",
		text: "Toque em ENTREGA e arraste cada caixa para a prateleira certa do depósito.",
		gameText: "Arraste cada caixa para a prateleira com a mesma cor de setor.",
		target: "fab:entrega|world:dock",
		reward: { coins: 30, diamonds: 0, text: "Estoque cheio!" },
	},
	{
		id: "missoes",
		mode: "spotlight",
		title: "Missões",
		text: "Toque em MISSÕES. Elas dão moedas e prêmios: quando aparecer um número vermelho, tem prêmio para pegar!",
		target: "tool:!missions",
	},
	{
		// Lucas 19/10: the player learns that the progress can be kept in the cloud (Opções › Conta). Skipped by the
		// host when the player is already signed in (desktop/host.ts); the Conta tab also finishes it.
		id: "conta",
		mode: "bubble",
		title: "Guarde o seu progresso",
		text:
			"Entre com a sua conta nas OPÇÕES (a engrenagem), na aba CONTA. Assim o mercado, as moedas e os diamantes ficam salvos, mesmo se você trocar de celular.",
		target: "settings",
		button: "Depois",
	},
	{
		id: "objetivo",
		mode: "modal",
		title: "Você pegou o jeito!",
		text:
			"Agora é com você: venda bastante, cumpra os contratos do dia e suba de nível. " +
			"O próximo grande passo é comprar o terreno ao lado e trocar a mesinha por uma TENDA. " +
			"O seu próximo objetivo fica sempre no topo da tela. Se esquecer de algo, toque no ? para abrir o Guia.",
		target: "",
		button: "Bora vender!",
		reward: { coins: 50, diamonds: 5, text: "Tutorial concluído!" },
	},
];

export type OnboardingTipDef = {
	id: string;
	title: string;
	text: string;
	target: OnboardingTarget;
};

/** One-off tips, shown the first time each feature matters (after the guided first day). */
export const onboardingTips: OnboardingTipDef[] = [
	{
		id: "fim-do-dia",
		title: "Fim do dia!",
		text: "O dia acabou! Toque em RESULTADO para ver como foi o dia.",
		target: "action:claimDayResult|market",
	},
	{
		id: "contratos",
		title: "Contratos",
		text: "Toque em ACEITAR E ABRIR no contrato que quiser. Cumpriu a meta, ganha o prêmio: os fáceis dão menos, os difíceis dão mais!",
		target: "action:startDay",
	},
	{
		id: "repor",
		title: "A mesinha está esvaziando!",
		text: "Toque em REPOR para trazer produtos do depósito para a mesinha. Prateleira vazia não vende.",
		target: "fab:repor",
	},
	{
		id: "fila",
		title: "Fila no caixa!",
		text: "Clientes esperando muito vão embora sem pagar. Toque em CAIXA e atenda a fila.",
		target: "fab:caixa|world:checkout",
	},
	{
		id: "loja",
		title: "A Loja",
		text: "Na LOJA você compra melhorias, decoração, terrenos e as expansões do mercado. Toque em LOJA para ver.",
		target: "tool:!loja",
	},
	{
		id: "terreno",
		title: "Terreno à venda!",
		text: "Você já pode comprar o terreno ao lado, o primeiro passo para a TENDA. Toque no PRÓXIMO OBJETIVO, no alto da tela.",
		target: "goal",
	},
	{
		id: "evoluir",
		title: "Hora de crescer!",
		text: "Você já pode evoluir o mercado! Toque em LOJA e depois na aba EXPANSÕES.",
		target: "tool:!loja",
	},
	{
		id: "equipe",
		title: "Contrate ajuda",
		text: "Agora você pode contratar um operador de caixa: ele atende a fila sozinho. Toque em LOJA e depois na aba EQUIPE.",
		target: "tool:!loja",
	},
	{
		id: "producao",
		title: "Produção liberada!",
		text: "Você pode montar setores como a padaria e produzir seus próprios produtos. Toque em PRODUÇÃO.",
		target: "tool:!sectors",
	},
];

/** What each part of the screen does (the "Guia" page). */
export const onboardingGuide: { icon: string; title: string; text: string }[] = [
	{ icon: "market", title: "Abrir / Fechar", text: "Começa o dia (5 minutos) e encerra antes da hora. No fim do dia você recebe moedas e XP." },
	{ icon: "clipboard", title: "Meta do dia", text: "O contrato escolhido para o dia e quanto falta para cumprir." },
	{ icon: "crown", title: "Nível", text: "Vendas e contratos dão XP. Cada nível libera produtos, melhorias e funcionários novos." },
	{ icon: "market", title: "Loja", text: "Melhorias, móveis, decoração, equipe, terrenos e expansões do mercado." },
	{ icon: "shelf", title: "Prateleiras", text: "O que está à venda em cada móvel, os preços e o estoque na vitrine." },
	{ icon: "warehouse", title: "Estoque", text: "O depósito: quanto você tem guardado de cada produto." },
	{ icon: "deliveryTruck", title: "Entregas", text: "Peça caixas ao atacado. O caminhão chega depois de alguns minutos." },
	{ icon: "trophy", title: "Missões", text: "Objetivos com prêmios. O número vermelho mostra o que já dá para pegar." },
	{ icon: "crown", title: "Conquistas", text: "Medalhas pelos seus recordes de vendas, clientes e crescimento." },
	{ icon: "coin", title: "CAIXA", text: "Aparece quando um cliente espera para pagar. Atenda rápido e dê o troco certo." },
	{ icon: "package", title: "REPOR", text: "Aparece quando a vitrine está acabando: leva produtos do depósito para a mesinha." },
	{ icon: "deliveryTruck", title: "ENTREGA", text: "Aparece quando um caminhão chega: descarregue as caixas no depósito." },
];
