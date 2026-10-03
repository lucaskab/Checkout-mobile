import type { ImageSourcePropType } from "react-native";

export const gameIconAssets = {
	aiBrain: require("../../assets/game-art/icons/ai-brain.png"),
	bank: require("../../assets/game-art/icons/bank.png"),
	banner: require("../../assets/game-art/icons/banner.png"),
	basket: require("../../assets/game-art/icons/basket.png"),
	billboard: require("../../assets/game-art/icons/billboard.png"),
	broom: require("../../assets/game-art/icons/broom.png"),
	calculator: require("../../assets/game-art/icons/calculator.png"),
	car: require("../../assets/game-art/icons/car.png"),
	cart: require("../../assets/game-art/icons/cart.png"),
	clipboard: require("../../assets/game-art/icons/clipboard.png"),
	coin: require("../../assets/game-art/icons/coin.png"),
	computer: require("../../assets/game-art/icons/computer.png"),
	construction: require("../../assets/game-art/icons/construction.png"),
	conveyor: require("../../assets/game-art/icons/conveyor.png"),
	crown: require("../../assets/game-art/icons/crown.png"),
	controller: require("../../assets/game-art/icons/controller.png"),
	customers: require("../../assets/game-art/icons/customers.png"),
	deliveryTruck: require("../../assets/game-art/icons/delivery-truck.png"),
	diamond: require("../../assets/game-art/icons/diamond.png"),
	distributionCenter: require("../../assets/game-art/icons/distribution-center.png"),
	drone: require("../../assets/game-art/icons/drone.png"),
	emptyShelfSlot: require("../../assets/game-art/icons/empty-shelf-slot.png"),
	festival: require("../../assets/game-art/icons/festival.png"),
	flame: require("../../assets/game-art/icons/flame.png"),
	forklift: require("../../assets/game-art/icons/forklift.png"),
	fountain: require("../../assets/game-art/icons/fountain.png"),
	freezer: require("../../assets/game-art/icons/freezer.png"),
	fuelPump: require("../../assets/game-art/icons/fuel-pump.png"),
	garden: require("../../assets/game-art/icons/garden.png"),
	gift: require("../../assets/game-art/icons/gift.png"),
	graduation: require("../../assets/game-art/icons/graduation.png"),
	hammer: require("../../assets/game-art/icons/hammer.png"),
	handshake: require("../../assets/game-art/icons/handshake.png"),
	key: require("../../assets/game-art/icons/key.png"),
	knife: require("../../assets/game-art/icons/knife.png"),
	light: require("../../assets/game-art/icons/light.png"),
	lightning: require("../../assets/game-art/icons/lightning.png"),
	lock: require("../../assets/game-art/icons/lock.png"),
	manager: require("../../assets/game-art/icons/manager.png"),
	market: require("../../assets/game-art/icons/market.png"),
	medal: require("../../assets/game-art/icons/medal.png"),
	package: require("../../assets/game-art/icons/package.png"),
	pallet: require("../../assets/game-art/icons/pallet.png"),
	plant: require("../../assets/game-art/icons/plant.png"),
	priceTag: require("../../assets/game-art/icons/price-tag.png"),
	radio: require("../../assets/game-art/icons/radio.png"),
	rain: require("../../assets/game-art/icons/rain.png"),
	receipt: require("../../assets/game-art/icons/receipt.png"),
	refrigerator: require("../../assets/game-art/icons/refrigerator.png"),
	robot: require("../../assets/game-art/icons/robot.png"),
	scanner: require("../../assets/game-art/icons/scanner.png"),
	shelf: require("../../assets/game-art/icons/shelf.png"),
	sleepy: require("../../assets/game-art/icons/sleepy.png"),
	smartphone: require("../../assets/game-art/icons/smartphone.png"),
	success: require("../../assets/game-art/icons/success.png"),
	target: require("../../assets/game-art/icons/target.png"),
	ticket: require("../../assets/game-art/icons/ticket.png"),
	toolbox: require("../../assets/game-art/icons/toolbox.png"),
	television: require("../../assets/game-art/icons/television.png"),
	trophy: require("../../assets/game-art/icons/trophy.png"),
	warning: require("../../assets/game-art/icons/warning.png"),
	warehouse: require("../../assets/game-art/icons/warehouse.png"),
} satisfies Record<string, ImageSourcePropType>;

export type GameIconId = keyof typeof gameIconAssets;

export function getGameIconAsset(icon: GameIconId): ImageSourcePropType {
	return gameIconAssets[icon];
}

export const eventIcons: Record<string, GameIconId> = {
	"hora-do-rush": "customers",
	"quinto-dia-util": "coin",
	"feira-de-rua": "festival",
	"onda-de-calor": "flame",
	"sorteio-na-porta": "gift",
	"caminhao-de-ofertas": "deliveryTruck",
	"dia-de-jogo": "television",
	"cafe-com-a-equipe": "handshake",
	"viralizou": "smartphone",
	"chuva-forte": "rain",
	"rua-em-obras": "construction",
	"engarrafamento": "car",
	"fim-do-mes": "calculator",
	"maquininha-fora-do-ar": "computer",
	"excursao-da-escola": "graduation",
	"queda-de-energia": "lightning",
	"turno-puxado": "sleepy",
	"vigilancia-sanitaria": "clipboard",
	"carro-de-som": "radio",
};

export const missionIcons: Record<string, GameIconId> = {
	"buyers-10": "success",
	"buyers-300": "customers",
	"buyers-75": "handshake",
	"crafted-1": "warehouse",
	"crafted-10": "conveyor",
	"crafted-200": "flame",
	"crafted-50": "toolbox",
	"crafted-750": "medal",
	"customers-100": "market",
	"customers-1000": "festival",
	"customers-25": "cart",
	"customers-350": "customers",
	"customers-5": "customers",
	"flour-stock-20": "package",
	"inventory-200": "distributionCenter",
	"inventory-25": "package",
	"inventory-75": "shelf",
	"level-10": "market",
	"level-16": "warehouse",
	"level-2": "plant",
	"level-22": "crown",
	"level-5": "target",
	"milk-stock-15": "refrigerator",
	"revenue-1000": "coin",
	"revenue-100000": "diamond",
	"revenue-25000": "calculator",
	"revenue-5000": "coin",
	"tomato-sales-20": "success",
	"units-10": "receipt",
	"units-200": "lightning",
	"units-2500": "trophy",
	"units-50": "package",
	"units-750": "lightning",
	"upgrades-1": "toolbox",
	"upgrades-12": "hammer",
	"upgrades-5": "hammer",
	"variety-20": "clipboard",
	"variety-8": "customers",
};

export const achievementIcons: Record<string, GameIconId> = {
	"customers-converted": "success",
	"customers-served": "customers",
	"instant-deliveries": "lightning",
	"instant-production": "diamond",
	"items-crafted": "conveyor",
	"market-level": "market",
	"market-openings": "key",
	"missions-claimed": "target",
	"price-changes": "priceTag",
	"production-jobs": "warehouse",
	"products-unlocked": "clipboard",
	"restocked-units": "package",
	"shelf-upgrades": "shelf",
	"shop-purchases": "gift",
	"supplier-orders": "deliveryTruck",
	"total-experience": "graduation",
	"total-revenue": "coin",
	"unique-products-sold": "basket",
	"units-sold": "receipt",
};

export const shopCategoryIcons: Record<string, GameIconId> = {
	consumiveis: "lightning",
	decoracao: "plant",
	equipamentos: "cart",
	lendarios: "trophy",
	logistica: "deliveryTruck",
	marketing: "banner",
	premium: "diamond",
	tecnologia: "computer",
};

export const shopItemIcons: Record<string, GameIconId> = {
	"ambient-music": "radio",
	"atlas-drone": "drone",
	"auto-scanner": "scanner",
	billboard: "billboard",
	"cashback-hour": "coin",
	"ceo-manager": "manager",
	computer: "computer",
	"delivery-drone": "drone",
	"delivery-truck": "deliveryTruck",
	"distribution-center": "distributionCenter",
	"energy-coffee": "lightning",
	"erp-system": "computer",
	"face-checkout": "scanner",
	"flash-sale": "lightning",
	fountain: "fountain",
	forklift: "forklift",
	garden: "garden",
	"golden-checkout": "crown",
	"golden-register": "trophy",
	"happy-hour": "festival",
	influencer: "smartphone",
	"inventory-drone": "drone",
	"led-lighting": "light",
	"legendary-manager": "manager",
	"large-cart": "cart",
	"magic-stock": "gift",
	"national-ad": "television",
	pallet: "pallet",
	"permanent-vip": "diamond",
	"premium-checkout": "market",
	"premium-floor": "market",
	"premium-restock-robot": "robot",
	"premium-truck": "deliveryTruck",
	"pricing-ai": "aiBrain",
	"promotion-panel": "clipboard",
	radio: "radio",
	"refrigerated-fridge": "refrigerator",
	"self-checkout": "robot",
	"shopping-basket": "basket",
	"simple-cart": "cart",
	"smart-conveyor": "conveyor",
	"stock-cart": "cart",
	"stock-robot": "robot",
	"street-banner": "banner",
	plant: "plant",
	television: "television",
	"turbo-cart": "cart",
	"vertical-freezer": "freezer",
};

export const marketCategoryProductIds: Record<string, number> = {
	aguas: 21,
	bebes: 37,
	bebidas: 13,
	bolachas: 25,
	carnes: 27,
	chocolates: 24,
	congelados: 17,
	conveniencia: 40,
	doces: 23,
	eletronicos: 38,
	energeticos: 22,
	frios: 28,
	gourmet: 32,
	higiene: 34,
	hortifruti: 2,
	importados: 31,
	laticinios: 6,
	limpeza: 35,
	luxo: 33,
	massas: 26,
	organicos: 29,
	papelaria: 39,
	padaria: 9,
	peixes: 44,
	premium: 30,
	pets: 36,
	queijos: 104,
	refrigerantes: 14,
	sazonais: 41,
};

export const productionSectorProductIds: Record<string, number> = {
	acougue: 27,
	adega: 119,
	bebidas: 113,
	padaria: 101,
	peixaria: 44,
	queijaria: 104,
	sorvetes: 116,
};

export const currencySectionIcons: Record<string, GameIconId> = {
	bundle: "gift",
	coins: "coin",
	diamonds: "diamond",
};

export function getGameEventIcon(eventId: string): GameIconId {
	return eventIcons[eventId] ?? "market";
}

export function getMissionIcon(missionId: string): GameIconId {
	return missionIcons[missionId] ?? "target";
}

export function getAchievementIcon(achievementId: string): GameIconId {
	return achievementIcons[achievementId] ?? "trophy";
}

export function getShopItemIcon(itemId: string): GameIconId {
	return shopItemIcons[itemId] ?? "gift";
}

export function getShopCategoryIcon(categoryId: string): GameIconId {
	return shopCategoryIcons[categoryId] ?? "market";
}

export function getMarketCategoryProductId(categoryId: string): number {
	return marketCategoryProductIds[categoryId] ?? 1;
}

export function getProductionSectorProductId(sectorId: string): number {
	return productionSectorProductIds[sectorId] ?? 9;
}

export function getCurrencySectionIcon(category: string): GameIconId {
	return currencySectionIcons[category] ?? "gift";
}
