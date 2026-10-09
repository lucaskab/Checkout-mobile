// Delivery flavour: customers, neighbourhoods, notes and the motoboys (courier personalities and radio lines).

export const deliveryFirstNames = [
	"Ana",
	"Bruno",
	"Camila",
	"Diego",
	"Elisa",
	"Fábio",
	"Gabriela",
	"Hugo",
	"Isabela",
	"João",
	"Karina",
	"Leandro",
	"Mariana",
	"Nicolas",
	"Olívia",
	"Paulo",
	"Rafaela",
	"Samuel",
	"Tatiane",
	"Vinícius",
	"Yasmin",
	"Wagner",
	"Letícia",
	"Renato",
];

export const deliveryLastInitials = ["A", "B", "C", "D", "F", "G", "L", "M", "N", "O", "P", "R", "S", "T", "V"];

export const deliveryNeighborhoods = [
	"Vila Esperança",
	"Jardim das Flores",
	"Morro Azul",
	"Bairro Novo",
	"Vila do Sol",
	"Parque Verde",
	"Santa Clara",
	"Conjunto Alvorada",
	"Cidade Alegre",
	"Jardim Bela Vista",
	"Vila Maria",
	"Recanto dos Pássaros",
];

/** Notes customers leave on the order (about half the orders have one). */
export const deliveryNotes = [
	"Ovos com cuidado, por favor!",
	"Sem sacola plástica 🌱",
	"Toca a campainha 2x",
	"Pode substituir se faltar",
	"Entregar na portaria",
];

export type DeliveryCourierProfile = {
	id: string;
	name: string;
	/** Colour of the motorbike's baú and helmet in the 3D city and the app. */
	color: string;
	phrases: {
		arrive: string[];
		leave: string[];
		delivered: string[];
	};
};

export const deliveryCouriers: DeliveryCourierProfile[] = [
	{
		id: "tiao",
		name: "Tião",
		color: "#E8702A",
		phrases: {
			arrive: ["Tô chegando, chefe!", "Já tô na porta, patrão!"],
			leave: ["Bora que o asfalto não espera!", "Vou nessa, fica com Deus!"],
			delivered: ["Entregue, sem um arranhão!", "Tá na mão do freguês, valeu!"],
		},
	},
	{
		id: "dudu",
		name: "Dudu Capacete",
		color: "#D7263D",
		phrases: {
			arrive: ["Cheguei! Pode buzinar que eu já escutei.", "Chegou o delivery, cadê o freguês?"],
			leave: ["Acelera que o sinal tá fechando!", "Lá vou eu, pelo atalho do morro!"],
			delivered: ["Mais uma pra conta, chefia!", "Entregue na régua, tá tudo certo!"],
		},
	},
	{
		id: "renatinho",
		name: "Renatinho",
		color: "#F2C230",
		phrases: {
			arrive: ["Eu sou rápido, cheguei antes do fone acabar!", "Tô na porta, pode descer!"],
			leave: ["Tchau, mercado! Volto logo!", "Vrum, vrum, lá vou eu!"],
			delivered: ["Sacola na mão do cliente, missão cumprida!", "Pedido entregue, tá top!"],
		},
	},
	{
		id: "preta",
		name: "Preta da Moto",
		color: "#2BB673",
		phrases: {
			arrive: ["Cheguei, meu bem! Chega aqui na porta.", "Moto na porta, sem bagunça!"],
			leave: ["Bora pra rua, que hoje o dia é nosso!", "Tchau, mercadinho, até a próxima!"],
			delivered: ["Entregue e sem reclamação, aí sim!", "Deixou o pedido inteiro, ótimo!"],
		},
	},
	{
		id: "ze",
		name: "Zé Relâmpago",
		color: "#7B5EA7",
		phrases: {
			arrive: ["Relâmpago na área! Cheguei!", "Olha eu aqui, chefe, direto da pista!"],
			leave: ["Tô indo, não para não!", "Vrum! Já saí da frente!"],
			delivered: ["Chegou inteiro, 5 estrelas pra gente!", "Tá entregue, bora pro próximo!"],
		},
	},
	{
		id: "juninho",
		name: "Juninho do Baú",
		color: "#1F2A44",
		phrases: {
			arrive: ["Juninho do baú chegou! Desce aí!", "Parei na portaria, pode vir!"],
			leave: ["Fui! Deseja boa noite pro freguês!", "Lá vai o baú, segura a onda!"],
			delivered: ["Baú vazio, pedido na mão!", "Entregue, tudo certinho, freguês!"],
		},
	},
];
