/**
 * "Evoluções com recompensa" (claude/evolucoes-recompensas.md, Lucas 01/11): an evolution is paid at once and takes
 * time. The evolution crew (separate from the interior builders) works on one at a time, the others wait in a queue;
 * the tier and its rewards apply when the timer ends. Meanwhile the fixture keeps selling (and the sector producing)
 * with its old look.
 */
export type EvolutionKind = "shelf" | "sector" | "checkout" | "decor";

export type FixtureEvolution = {
	id: string;
	kind: EvolutionKind;
	/** Shelf type id, production sector id, "checkout" or decoration id (atm, gumball, claw-machine). */
	targetId: string;
	/** Tier reached when it ends (shelves: the capacity tier, 2..5 = ★). */
	toTier: number;
	/** The checkout's step is a shop item: it joins the owned items when the evolution ends. */
	itemId?: string;
	/** Working time (queued evolutions wait for the ones before). */
	durationMs: number;
	startedAt: number;
	endsAt: number;
};
