export type SimulatorProduct = {
	id: string;
	name: string;
	quantity: number;
	capacity: number;
	salePrice: number;
	low: boolean;
};

export type SimulatorState = {
	type: "state";
	cash: number;
	revenueToday: number;
	expensesToday: number;
	profitToday: number;
	reputation: number;
	day: number;
	time: string;
	gameSpeed: number;
	paused: boolean;
	customersServed: number;
	customersInStore: number;
	queueSize: number;
	checkoutLevel: number;
	staff: {
		cashiers: number;
		stockers: number;
		cleaners: number;
	};
	products: SimulatorProduct[];
};

export type SimulatorCommand =
	| { action: "toggle_pause" }
	| { action: "set_speed"; value: number }
	| { action: "restock_all" }
	| { action: "order_stock"; product: string; quantity: number }
	| {
			action: "hire_employee";
			role: "cashiers" | "stockers" | "cleaners";
	  }
	| { action: "upgrade_checkout" }
	| { action: "complete_checkout"; total: number; items: number }
	| { action: "reset_day" };
