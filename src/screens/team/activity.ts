import type { GameEmployee, StaffTask } from "@/@types/employee";

const incidentActivity: Record<string, string> = {
	derramado: "Secando o chão molhado",
	sujeira: "Varrendo a sujeira",
	lampada: "Trocando uma lâmpada",
	etiqueta: "Trocando uma etiqueta",
};

// One line about what a hired employee is doing right now.
export function describeEmployeeActivity(
	employee: GameEmployee,
	tasks: StaffTask[],
	isOpen: boolean,
): string {
	if (!employee.isWorking) return "Pausado";
	if (!isOpen) return "Espera o mercado abrir";
	if (employee.role === "cashier") return "No caixa, atendendo a fila";
	const task = tasks.find((item) => item.employeeId === employee.id);
	if (!task)
		return employee.role === "stock_clerk"
			? "Conferindo as gôndolas"
			: "Fazendo a ronda pela loja";
	if (task.kind === "restock")
		return `Trazendo ${task.units}× ${task.productName} do depósito`;
	return incidentActivity[task.incidentKind] ?? "Resolvendo um imprevisto";
}
