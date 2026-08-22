@tool
extends Node2D

@export_category("Editor Preview")
@export var show_customer_routes_in_editor := true:
	set(value):
		show_customer_routes_in_editor = value
		queue_redraw()

@onready var ground: TileMapLayer = $Ground
@onready var camera: Camera2D = $Camera2D

var fixture_clock := 0.0
var metrics_clock := 0.0
var game_state: CheckoutGameState


func _ready() -> void:
	_ensure_ground()
	if not Engine.is_editor_hint():
		game_state = CheckoutGameState.new()
		game_state.name = "CheckoutGameState"
		add_child(game_state)
		var bridge := ReactNativeBridge.new()
		bridge.name = "ReactNativeBridge"
		add_child(bridge)
		bridge.setup(game_state)
		var cozy_hud := CozyMarketHUD.new()
		cozy_hud.name = "CozyMarketHUD"
		add_child(cozy_hud)
		cozy_hud.setup(game_state)
		# No mobile, a RTNGodotView nativa recebe a HUD feita em React Native.
		# A HUD Godot permanece disponível na execução desktop.
		if OS.has_feature("mobile"):
			cozy_hud.visible = false
		var legacy_hud := get_node_or_null("HUD") as CanvasLayer
		if legacy_hud != null:
			legacy_hud.visible = false
	queue_redraw()


func _ensure_ground() -> void:
	if not is_instance_valid(ground) or not ground.visible:
		return
	# Expand only into empty cells; never overwrite tiles painted manually in the editor.
	for y in range(-24, 25):
		for x in range(-30, 31):
			var cell := Vector2i(x, y)
			if ground.get_cell_source_id(cell) != -1:
				continue
			var variation := posmod(x * 3 + y * 7, 5)
			ground.set_cell(cell, 6, Vector2i(variation, 0), 0)
	ground.queue_redraw()


func _process(delta: float) -> void:
	fixture_clock += delta
	var fixture_frame := int(fixture_clock / 0.28) % 4
	for sprite in get_tree().get_nodes_in_group("animated_fixture"):
		if sprite is Sprite2D:
			sprite.frame = fixture_frame
	if Engine.is_editor_hint():
		queue_redraw()
		return
	metrics_clock += delta
	if metrics_clock >= 1.0 and game_state != null:
		metrics_clock = 0.0
		var visible_customers := 0
		for customer in get_tree().get_nodes_in_group("customers"):
			if customer is CanvasItem and customer.visible:
				visible_customers += 1
		if visible_customers == 0:
			var customers := get_node_or_null("Customers")
			if customers != null:
				for customer in customers.get_children():
					if customer is CanvasItem and customer.visible:
						visible_customers += 1
		game_state.update_world_metrics(visible_customers, game_state.queue_size)

	var pan := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	pan += Vector2(
		float(Input.is_key_pressed(KEY_D)) - float(Input.is_key_pressed(KEY_A)),
		float(Input.is_key_pressed(KEY_S)) - float(Input.is_key_pressed(KEY_W))
	)
	pan = pan.limit_length(1.0)
	camera.position += pan * 520.0 * delta / camera.zoom.x


func _unhandled_input(event: InputEvent) -> void:
	if Engine.is_editor_hint():
		return
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			camera.zoom = (camera.zoom * 1.10).clamp(Vector2(0.45, 0.45), Vector2(1.25, 1.25))
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			camera.zoom = (camera.zoom / 1.10).clamp(Vector2(0.45, 0.45), Vector2(1.25, 1.25))


func _draw() -> void:
	if not Engine.is_editor_hint() or not show_customer_routes_in_editor:
		return
	var customers := get_node_or_null("Customers")
	if customers == null:
		return
	for customer in customers.get_children():
		var points: PackedVector2Array = customer.get("route")
		if points.size() > 1:
			var closed := PackedVector2Array(points)
			closed.append(points[0])
			draw_polyline(closed, Color(0.1, 0.75, 0.95, 0.45), 2.0, true)

	var city := get_node_or_null("CityExpansion")
	if city == null:
		return
	var parking := city.get_node_or_null("PedestrianArrival") as Marker2D
	var walkway := city.get_node_or_null("PedestrianWalkway") as Marker2D
	var door := get_node_or_null("MarketFoundation/DoorOutside") as Marker2D
	if parking != null and walkway != null and door != null:
		var pedestrian_guide := PackedVector2Array([
			parking.global_position,
			walkway.global_position,
			door.global_position,
		])
		draw_polyline(pedestrian_guide, Color(0.35, 1.0, 0.45, 0.8), 4.0, true)

	var traffic := city.get_node_or_null("Traffic")
	if traffic != null:
		for car in traffic.get_children():
			var route_value: Variant = car.get("route")
			if route_value is PackedVector2Array and route_value.size() > 1:
				draw_polyline(route_value, Color(1.0, 0.55, 0.12, 0.65), 3.0, true)
			var arrival_value: Variant = car.get("arrival_route")
			if arrival_value is PackedVector2Array and arrival_value.size() > 1:
				draw_polyline(arrival_value, Color(1.0, 0.55, 0.12, 0.75), 3.0, true)
			var departure_value: Variant = car.get("departure_route")
			if departure_value is PackedVector2Array and departure_value.size() > 1:
				draw_polyline(departure_value, Color(0.2, 0.7, 1.0, 0.65), 3.0, true)
