// First-time onboarding: a short guided first day with Dona Neide (src/data/onboarding.ts), then one-off
// tips the first time a feature matters. Rules in src/services/onboarding.ts; Unity draws the coach
// (CheckoutDesktopHUD.Coach.cs) from the view's `coach` block.

export type OnboardingStatus = "active" | "done" | "skipped";

/** Counters taken when a step begins: the step is done when its counter goes up. */
export type OnboardingMarks = {
	served: number;
	orders: number;
	unloaded: number;
	restocked: number;
};

export type OnboardingReward = {
	/** Changes for every reward, so the screen celebrates each one once. */
	key: string;
	text: string;
	coins: number;
	diamonds: number;
};

export type OnboardingState = {
	status: OnboardingStatus;
	/** Guided step being played ("" once the tutorial is over). */
	step: string;
	stepStartedAt: number;
	marks: OnboardingMarks;
	/** Latest step prize (Unity pops it once per key). */
	reward: OnboardingReward | null;
	/** One-off tips already shown. */
	tipsSeen: string[];
	/** Tip on screen now ("" = none). */
	tip: string;
	/** Steps finished, in order (for the "Guia" page and analytics). */
	completed: string[];
};

/**
 * Where the coach points. Unity tries each target of a "|" list in order and uses the first one on screen:
 *   world:<panel>[:<shelfId>]   a clickable object of the map (CheckoutTarget)
 *   tool:<route>                a toolbar button ("tool:!missions"; a group's button routes to one of its tabs)
 *   market                      the Abrir / Fechar / Resultado button
 *   action:<name>               a page button that runs this store action ("action:startDay")
 *   route:<prefix>              a page button whose route starts with this ("route:@shop")
 *   fab:caixa | fab:repor | fab:entrega   the floating game buttons on the left
 *   help                        the "?" button of the top bar
 */
export type OnboardingTarget = string;
