extends SceneTree

var parked_count := 0
var departed_count := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	Engine.time_scale = 10.0
	var packed := load("res://Scene/supermarket_assets_game_v2.tscn") as PackedScene
	var scene := packed.instantiate()
	root.add_child(scene)
	await process_frame
	var car := scene.get_node("CityExpansion/Traffic/ArrivalCar")
	var customer := scene.get_node("Customers/ParkingCustomer")
	car.parked.connect(func(_position: Vector2) -> void: parked_count += 1)
	car.departed.connect(func() -> void: departed_count += 1)
	var states := {}
	for _frame in range(2400):
		await physics_frame
		states[customer.flow_state] = true
	print("ARRIVAL parked=", parked_count, " departed=", departed_count, " car_state=", car.state)
	print("PARKING_CUSTOMER states=", states.keys(), " visible=", customer.visible)
	quit(0 if parked_count >= 1 and departed_count >= 1 else 1)
