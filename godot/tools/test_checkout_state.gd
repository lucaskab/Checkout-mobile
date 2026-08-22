extends SceneTree


func _initialize() -> void:
	var state := CheckoutGameState.new()
	root.add_child(state)
	var initial_cash := state.cash
	state.dispatch({"action": "order_stock", "product": "bakery", "quantity": 10})
	assert(state.inventory.bakery == 36, "O pedido deve acrescentar 10 unidades")
	assert(state.cash < initial_cash, "O pedido deve debitar o saldo")
	state.dispatch({"action": "set_speed", "value": 2.0})
	assert(state.game_speed == 2.0 and not state.paused, "A velocidade deve sincronizar e despausar")
	var served := state.customers_served
	state.dispatch({"action": "complete_checkout", "total": 42.50, "items": 7})
	assert(state.customers_served == served + 1, "O checkout deve atender um cliente")
	assert(state.get_snapshot().type == "state", "O snapshot deve seguir o contrato da ponte")
	print("CHECKOUT_STATE_TEST=PASS")
	quit(0)
