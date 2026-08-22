class_name CheckoutGameState
extends Node

signal state_changed(snapshot: Dictionary)
signal toast_requested(message: String, tone: String)

const PRODUCT_CATALOG := {
	"groceries": {"name": "Mercearia", "unit_cost": 3.20, "sale_price": 6.90, "capacity": 140},
	"produce": {"name": "Hortifruti", "unit_cost": 2.10, "sale_price": 5.40, "capacity": 100},
	"bakery": {"name": "Padaria", "unit_cost": 1.75, "sale_price": 4.80, "capacity": 90},
	"drinks": {"name": "Bebidas", "unit_cost": 2.80, "sale_price": 6.20, "capacity": 110},
}

var cash := 2480.50
var revenue_today := 764.20
var expenses_today := 185.00
var reputation := 4.7
var day := 12
var hour := 9
var minute := 30
var game_speed := 1.0
var paused := false
var customers_served := 38
var customers_in_store := 6
var queue_size := 2
var checkout_level := 1
var staff := {
	"cashiers": 1,
	"stockers": 1,
	"cleaners": 0,
}
var inventory := {
	"groceries": 78,
	"produce": 42,
	"bakery": 26,
	"drinks": 63,
}

var _simulation_clock := 0.0
var _minute_clock := 0.0


func _ready() -> void:
	state_changed.emit(get_snapshot())


func _process(delta: float) -> void:
	if paused:
		return
	var scaled := delta * game_speed
	_minute_clock += scaled
	_simulation_clock += scaled
	if _minute_clock >= 1.0:
		_minute_clock -= 1.0
		_advance_minutes(1)
	if _simulation_clock >= maxf(1.6, 4.8 / maxf(game_speed, 0.5)):
		_simulation_clock = 0.0
		_simulate_checkout()


func dispatch(command: Dictionary) -> void:
	var action := str(command.get("action", ""))
	match action:
		"toggle_pause":
			paused = not paused
			_toast("Loja pausada" if paused else "Loja em operação", "info")
		"set_speed":
			game_speed = clampf(float(command.get("value", 1.0)), 0.5, 3.0)
			paused = false
			_toast("Velocidade %.1fx" % game_speed, "info")
		"restock_all":
			_restock_all()
		"order_stock":
			_order_stock(str(command.get("product", "groceries")), int(command.get("quantity", 10)))
		"hire_employee":
			_hire_employee(str(command.get("role", "cashiers")))
		"upgrade_checkout":
			_upgrade_checkout()
		"complete_checkout":
			_complete_manual_checkout(float(command.get("total", 0.0)), int(command.get("items", 1)))
		"reset_day":
			revenue_today = 0.0
			expenses_today = 0.0
			hour = 8
			minute = 0
			_toast("Novo dia iniciado", "success")
		_:
			_toast("Ação desconhecida: %s" % action, "warning")
	_emit_state()


func update_world_metrics(in_store: int, waiting: int) -> void:
	customers_in_store = maxi(in_store, 0)
	queue_size = maxi(waiting, 0)
	_emit_state()


func get_snapshot() -> Dictionary:
	var products: Array[Dictionary] = []
	for id in PRODUCT_CATALOG:
		var product: Dictionary = PRODUCT_CATALOG[id]
		var quantity := int(inventory.get(id, 0))
		products.append({
			"id": id,
			"name": product.name,
			"quantity": quantity,
			"capacity": product.capacity,
			"salePrice": product.sale_price,
			"low": quantity <= int(product.capacity * 0.3),
		})
	return {
		"type": "state",
		"cash": snappedf(cash, 0.01),
		"revenueToday": snappedf(revenue_today, 0.01),
		"expensesToday": snappedf(expenses_today, 0.01),
		"profitToday": snappedf(revenue_today - expenses_today, 0.01),
		"reputation": snappedf(reputation, 0.1),
		"day": day,
		"time": "%02d:%02d" % [hour, minute],
		"gameSpeed": game_speed,
		"paused": paused,
		"customersServed": customers_served,
		"customersInStore": customers_in_store,
		"queueSize": queue_size,
		"checkoutLevel": checkout_level,
		"staff": staff.duplicate(true),
		"products": products,
	}


func _simulate_checkout() -> void:
	var available: Array[String] = []
	for id in inventory:
		if int(inventory[id]) > 0:
			available.append(id)
	if available.is_empty():
		reputation = maxf(1.0, reputation - 0.1)
		_emit_state()
		return
	var item_count := randi_range(1, 4 + checkout_level)
	var sale_total := 0.0
	for index in range(item_count):
		if available.is_empty():
			break
		var id: String = available.pick_random()
		inventory[id] = maxi(0, int(inventory[id]) - 1)
		sale_total += float(PRODUCT_CATALOG[id].sale_price)
		if int(inventory[id]) <= 0:
			available.erase(id)
	if sale_total > 0.0:
		cash += sale_total
		revenue_today += sale_total
		customers_served += 1
		queue_size = maxi(0, queue_size - checkout_level)
		_emit_state()


func _complete_manual_checkout(total: float, items: int) -> void:
	var value := maxf(total, float(items) * 2.0)
	cash += value
	revenue_today += value
	customers_served += 1
	queue_size = maxi(0, queue_size - 1)
	_toast("Compra concluída • R$ %.2f" % value, "success")


func _restock_all() -> void:
	var cost := 0.0
	for id in PRODUCT_CATALOG:
		var missing := int(PRODUCT_CATALOG[id].capacity) - int(inventory[id])
		cost += missing * float(PRODUCT_CATALOG[id].unit_cost)
	if cost <= 0.0:
		_toast("Estoque já está completo", "info")
		return
	if cash < cost:
		_toast("Saldo insuficiente para repor tudo", "warning")
		return
	for id in PRODUCT_CATALOG:
		inventory[id] = int(PRODUCT_CATALOG[id].capacity)
	cash -= cost
	expenses_today += cost
	_toast("Estoque reposto • -R$ %.2f" % cost, "success")


func _order_stock(product_id: String, quantity: int) -> void:
	if not PRODUCT_CATALOG.has(product_id):
		_toast("Produto inválido", "warning")
		return
	var product: Dictionary = PRODUCT_CATALOG[product_id]
	var room := int(product.capacity) - int(inventory[product_id])
	var amount := clampi(quantity, 1, room)
	if amount <= 0:
		_toast("Estoque de %s já está completo" % product.name, "info")
		return
	var cost := amount * float(product.unit_cost)
	if cash < cost:
		_toast("Saldo insuficiente", "warning")
		return
	inventory[product_id] += amount
	cash -= cost
	expenses_today += cost
	_toast("%d un. de %s recebidas" % [amount, product.name], "success")


func _hire_employee(role: String) -> void:
	if not staff.has(role):
		role = "cashiers"
	var cost := 320.0 + float(staff[role]) * 120.0
	if cash < cost:
		_toast("Saldo insuficiente para contratar", "warning")
		return
	staff[role] += 1
	cash -= cost
	expenses_today += cost
	_toast("Novo funcionário contratado", "success")


func _upgrade_checkout() -> void:
	var cost := 650.0 * checkout_level
	if cash < cost:
		_toast("Saldo insuficiente para melhorar o caixa", "warning")
		return
	cash -= cost
	expenses_today += cost
	checkout_level += 1
	_toast("Caixa melhorado para nível %d" % checkout_level, "success")


func _advance_minutes(amount: int) -> void:
	minute += amount
	while minute >= 60:
		minute -= 60
		hour += 1
	if hour >= 22:
		hour = 8
		day += 1
		revenue_today = 0.0
		expenses_today = 0.0
	_emit_state()


func _toast(message: String, tone: String) -> void:
	toast_requested.emit(message, tone)


func _emit_state() -> void:
	state_changed.emit(get_snapshot())
