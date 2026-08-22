@tool
extends CharacterBody2D

@export var speed := 58.0
@export var acceleration := 260.0
@export var route: PackedVector2Array
@export var route_offset := 0
@export_category("Customer Flow")
@export var door_inside_path := NodePath("../../MarketFoundation/DoorInside")
@export var door_outside_path := NodePath("../../MarketFoundation/DoorOutside")
@export var parking_arrival_path := NodePath("../../CityExpansion/PedestrianArrival")
@export var parking_walkway_path := NodePath("../../CityExpansion/PedestrianWalkway")
@export var arrival_car_path: NodePath
@export_range(0, 10, 1) var queue_slot := 0
@export_range(3, 30, 1) var shopping_stops := 7
@export_range(0.5, 10.0, 0.1) var respawn_delay := 2.5

@onready var sprite: Sprite2D = $Sprite2D

var target_index := 0
var walk_distance := 0.0
var blocked_clock := 0.0
var editor_preview_clock := 0.0
var door_inside: Marker2D
var door_outside: Marker2D
var parking_arrival: Marker2D
var parking_walkway: Marker2D
var arrival_car: Node
var flow_door_inside := Vector2.ZERO
var flow_door_outside := Vector2.ZERO
var flow_aisle_entry := Vector2.ZERO
var exit_route_index := 0
var visited_stops := 0
var leaving_requested := false
var cooldown_clock := 0.0
var navigation_grid: AStarGrid2D
var navigation_ready := false
var navigation_path: PackedVector2Array
var navigation_path_index := 0
var navigation_target := Vector2(INF, INF)

const NAV_CELL_SIZE := 18.0
const NAV_ORIGIN := Vector2(-540.0, -360.0)
const NAV_GRID_SIZE := Vector2i(60, 40)
var market_walkable_polygon := PackedVector2Array([
	Vector2(-420.0, 20.0),
	Vector2(-285.0, -85.0),
	Vector2(0.0, -195.0),
	Vector2(285.0, -85.0),
	Vector2(420.0, 20.0),
	Vector2(420.0, 145.0),
	Vector2(290.0, 195.0),
	Vector2(120.0, 270.0),
	Vector2(-120.0, 270.0),
	Vector2(-290.0, 195.0),
	Vector2(-420.0, 145.0),
])

enum FlowState {
	APPROACHING_DOOR,
	ENTERING_MARKET,
	MOVING_TO_AISLE,
	SHOPPING,
	RETURNING_TO_AISLE,
	RETURNING_TO_DOOR,
	EXITING_MARKET,
	OUTSIDE_COOLDOWN,
	WALKING_FROM_CAR,
	RETURNING_TO_PARKING,
	RETURNING_TO_CAR,
	WALKING_TO_WALKWAY,
	WALKING_TO_CAR,
	WAITING_FOR_CAR,
}

var flow_state := FlowState.APPROACHING_DOOR


func _ready() -> void:
	if Engine.is_editor_hint():
		return
	door_inside = get_node_or_null(door_inside_path) as Marker2D
	door_outside = get_node_or_null(door_outside_path) as Marker2D
	parking_arrival = get_node_or_null(parking_arrival_path) as Marker2D
	parking_walkway = get_node_or_null(parking_walkway_path) as Marker2D
	arrival_car = get_node_or_null(arrival_car_path) if not arrival_car_path.is_empty() else null
	_calculate_flow_points()
	call_deferred("_build_navigation_grid")
	# Customers collide with fixtures (layer 1), but do not block one another at the door.
	collision_layer = 2
	collision_mask = 1
	if arrival_car != null and arrival_car.has_signal("parked"):
		arrival_car.connect("parked", Callable(self, "_on_arrival_car_parked"))
		flow_state = FlowState.WAITING_FOR_CAR
		visible = false
		collision_layer = 0
		collision_mask = 0
	else:
		_restart_outside()
	if queue_slot > 0:
		flow_state = FlowState.OUTSIDE_COOLDOWN
		cooldown_clock = queue_slot * 2.0
		visible = false
		collision_layer = 0
		collision_mask = 0


func _physics_process(delta: float) -> void:
	if Engine.is_editor_hint():
		velocity = Vector2.ZERO
		return
	if door_inside == null or door_outside == null or route.is_empty():
		velocity = Vector2.ZERO
		return
	if flow_state == FlowState.WAITING_FOR_CAR:
		velocity = Vector2.ZERO
		return
	if flow_state == FlowState.OUTSIDE_COOLDOWN:
		cooldown_clock -= delta
		velocity = Vector2.ZERO
		if cooldown_clock <= 0.0:
			_restart_outside()
		return

	var final_target := _get_current_target()
	var target := _get_movement_target(final_target)
	if global_position.distance_to(target) < 10.0:
		if _uses_navigation():
			if navigation_path_index < navigation_path.size() - 1:
				navigation_path_index += 1
				target = navigation_path[navigation_path_index]
			else:
				# The last waypoint may be the nearest reachable point beside a moved fixture.
				_advance_flow_state()
				final_target = _get_current_target()
				target = _get_movement_target(final_target)
		elif global_position.distance_to(final_target) < NAV_CELL_SIZE * 1.6:
			_advance_flow_state()
			if flow_state == FlowState.OUTSIDE_COOLDOWN:
				return
			final_target = _get_current_target()
			target = _get_movement_target(final_target)

	var direction := global_position.direction_to(target)
	velocity = velocity.move_toward(direction * speed, acceleration * delta)
	var previous_position := global_position
	move_and_slide()
	var travelled := global_position.distance_to(previous_position)

	if get_slide_collision_count() > 0:
		blocked_clock += delta
		if blocked_clock > 0.75 and _uses_navigation():
			_rebuild_navigation_path(final_target)
			blocked_clock = 0.0
	else:
		blocked_clock = 0.0

	# The limbs advance only when the body actually travels, preventing an in-place loop.
	if travelled > 0.05:
		walk_distance += travelled
	var walk_frame := int(walk_distance / 8.5) % 4
	var direction_row := 0
	if direction.x < 0.0 and direction.y >= 0.0:
		direction_row = 1
	elif direction.x < 0.0 and direction.y < 0.0:
		direction_row = 2
	elif direction.x >= 0.0 and direction.y < 0.0:
		direction_row = 3
	if travelled <= 0.05:
		walk_frame = 0
	sprite.frame = direction_row * 4 + walk_frame


func _get_current_target() -> Vector2:
	match flow_state:
		FlowState.WALKING_FROM_CAR, FlowState.RETURNING_TO_CAR:
			return parking_arrival.global_position if parking_arrival != null else flow_door_outside
		FlowState.WALKING_TO_WALKWAY, FlowState.RETURNING_TO_PARKING:
			return parking_walkway.global_position if parking_walkway != null else flow_door_outside
		FlowState.WALKING_TO_CAR:
			if arrival_car != null and arrival_car.has_method("get_disembark_position"):
				return arrival_car.call("get_disembark_position") as Vector2
			return parking_arrival.global_position if parking_arrival != null else flow_door_outside
		FlowState.APPROACHING_DOOR:
			return flow_door_outside
		FlowState.ENTERING_MARKET, FlowState.RETURNING_TO_DOOR:
			return flow_door_inside
		FlowState.MOVING_TO_AISLE, FlowState.RETURNING_TO_AISLE:
			return flow_aisle_entry
		FlowState.EXITING_MARKET:
			return flow_door_outside
		_:
			return route[target_index]


func _advance_flow_state() -> void:
	match flow_state:
		FlowState.WALKING_FROM_CAR:
			flow_state = FlowState.WALKING_TO_WALKWAY
		FlowState.WALKING_TO_WALKWAY:
			flow_state = FlowState.APPROACHING_DOOR
		FlowState.APPROACHING_DOOR:
			flow_state = FlowState.ENTERING_MARKET
			collision_mask = 0
		FlowState.ENTERING_MARKET:
			flow_state = FlowState.MOVING_TO_AISLE
		FlowState.MOVING_TO_AISLE:
			flow_state = FlowState.SHOPPING
			collision_mask = 1
			target_index = _nearest_inside_route_index()
			exit_route_index = target_index
			visited_stops = 0
			leaving_requested = false
			_clear_navigation_path()
		FlowState.SHOPPING:
			var reached_index := target_index
			visited_stops += 1
			if visited_stops >= shopping_stops + posmod(route_offset, 4):
				leaving_requested = true
			if leaving_requested and reached_index == exit_route_index:
				flow_state = FlowState.RETURNING_TO_AISLE
			else:
				target_index = (target_index + 1) % route.size()
		FlowState.RETURNING_TO_AISLE:
			flow_state = FlowState.RETURNING_TO_DOOR
			collision_mask = 0
			_clear_navigation_path()
		FlowState.RETURNING_TO_DOOR:
			flow_state = FlowState.EXITING_MARKET
			collision_mask = 0
		FlowState.EXITING_MARKET:
			if parking_arrival != null and parking_walkway != null:
				flow_state = FlowState.RETURNING_TO_PARKING
			else:
				_begin_outside_cooldown()
		FlowState.RETURNING_TO_PARKING:
			flow_state = FlowState.RETURNING_TO_CAR
		FlowState.RETURNING_TO_CAR:
			flow_state = FlowState.WALKING_TO_CAR
		FlowState.WALKING_TO_CAR:
			if arrival_car != null and arrival_car.has_method("passenger_boarded"):
				arrival_car.call("passenger_boarded")
				flow_state = FlowState.WAITING_FOR_CAR
				visible = false
				collision_layer = 0
				collision_mask = 0
			else:
				_begin_outside_cooldown()


func _on_arrival_car_parked(disembark_position: Vector2) -> void:
	global_position = disembark_position
	flow_state = FlowState.WALKING_FROM_CAR
	visible = true
	collision_layer = 2
	collision_mask = 0
	velocity = Vector2.ZERO
	walk_distance = 0.0
	blocked_clock = 0.0
	_clear_navigation_path()


func _nearest_inside_route_index() -> int:
	var nearest := 0
	var nearest_distance := INF
	for index in range(route.size()):
		var point := route[index]
		# Reject front-side points that would make a customer turn back through the door.
		if point.distance_squared_to(flow_aisle_entry) >= point.distance_squared_to(flow_door_outside):
			continue
		var distance := point.distance_squared_to(flow_aisle_entry)
		if distance < nearest_distance:
			nearest_distance = distance
			nearest = index
	if nearest_distance == INF:
		for index in range(route.size()):
			var distance := route[index].distance_squared_to(flow_aisle_entry)
			if distance < nearest_distance:
				nearest_distance = distance
				nearest = index
	return nearest


func _restart_outside() -> void:
	var outward := flow_door_inside.direction_to(flow_door_outside)
	if parking_arrival != null and parking_walkway != null:
		var queue_side := outward.orthogonal()
		global_position = parking_arrival.global_position + queue_side * float(queue_slot % 3) * 18.0
		flow_state = FlowState.WALKING_FROM_CAR
	else:
		# Fallback for scenes without the city expansion.
		global_position = flow_door_outside + outward * 62.0
		flow_state = FlowState.APPROACHING_DOOR
	visible = true
	collision_layer = 2
	# Door crossing is unobstructed; fixture collision is enabled after DoorInside.
	collision_mask = 0
	velocity = Vector2.ZERO
	walk_distance = 0.0
	blocked_clock = 0.0
	_clear_navigation_path()


func _begin_outside_cooldown() -> void:
	flow_state = FlowState.OUTSIDE_COOLDOWN
	cooldown_clock = respawn_delay + queue_slot * 1.1
	velocity = Vector2.ZERO
	visible = false
	collision_layer = 0
	collision_mask = 0


func _calculate_flow_points() -> void:
	if door_inside == null or door_outside == null:
		return
	var raw_inside := door_inside.global_position
	var raw_outside := door_outside.global_position
	var doorway_center := (raw_inside + raw_outside) * 0.5
	var inward := raw_outside.direction_to(raw_inside)
	# If both editor markers overlap, preserve that manually chosen point as the door center.
	if raw_inside.distance_to(raw_outside) < 40.0:
		inward = Vector2(0.18, -0.984).normalized()
		flow_door_inside = doorway_center + inward * 44.0
		flow_door_outside = doorway_center - inward * 44.0
	else:
		flow_door_inside = raw_inside
		flow_door_outside = raw_outside
	# Stop before the first shelf. Navigation takes over from this clear interior point.
	flow_aisle_entry = flow_door_inside + inward * 30.0


func _uses_navigation() -> bool:
	return flow_state == FlowState.SHOPPING or flow_state == FlowState.RETURNING_TO_AISLE


func _get_movement_target(final_target: Vector2) -> Vector2:
	if not _uses_navigation() or not navigation_ready:
		return final_target
	if navigation_target.distance_squared_to(final_target) > 1.0 or navigation_path.is_empty():
		_rebuild_navigation_path(final_target)
	if not navigation_path.is_empty():
		return navigation_path[navigation_path_index]
	return final_target


func _clear_navigation_path() -> void:
	navigation_path = PackedVector2Array()
	navigation_path_index = 0
	navigation_target = Vector2(INF, INF)


func _world_to_grid(point: Vector2) -> Vector2i:
	var local := (point - NAV_ORIGIN) / NAV_CELL_SIZE
	return Vector2i(
		clampi(int(floor(local.x)), 0, NAV_GRID_SIZE.x - 1),
		clampi(int(floor(local.y)), 0, NAV_GRID_SIZE.y - 1)
	)


func _nearest_free_cell(origin: Vector2i) -> Vector2i:
	if not navigation_grid.is_point_solid(origin):
		return origin
	for radius in range(1, 8):
		for y in range(origin.y - radius, origin.y + radius + 1):
			for x in range(origin.x - radius, origin.x + radius + 1):
				var candidate := Vector2i(x, y)
				if not navigation_grid.region.has_point(candidate):
					continue
				if not navigation_grid.is_point_solid(candidate):
					return candidate
	return origin


func _rebuild_navigation_path(final_target: Vector2) -> void:
	if not navigation_ready:
		return
	var start := _nearest_free_cell(_world_to_grid(global_position))
	var finish := _nearest_free_cell(_world_to_grid(final_target))
	var ids := navigation_grid.get_id_path(start, finish, true)
	navigation_path = PackedVector2Array()
	for id in ids:
		navigation_path.append(navigation_grid.get_point_position(id))
	# Keep the final destination exact when it is not inside an obstacle.
	if not navigation_grid.is_point_solid(_world_to_grid(final_target)):
		navigation_path.append(final_target)
	navigation_path_index = mini(1, navigation_path.size() - 1) if not navigation_path.is_empty() else 0
	navigation_target = final_target


func _build_navigation_grid() -> void:
	if not is_inside_tree():
		return
	navigation_grid = AStarGrid2D.new()
	navigation_grid.region = Rect2i(Vector2i.ZERO, NAV_GRID_SIZE)
	navigation_grid.cell_size = Vector2(NAV_CELL_SIZE, NAV_CELL_SIZE)
	navigation_grid.offset = NAV_ORIGIN + Vector2.ONE * NAV_CELL_SIZE * 0.5
	navigation_grid.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_NEVER
	navigation_grid.update()

	var probe := CircleShape2D.new()
	probe.radius = 15.0
	var query := PhysicsShapeQueryParameters2D.new()
	query.shape = probe
	query.collision_mask = 1
	query.collide_with_bodies = true
	query.collide_with_areas = false
	var space := get_world_2d().direct_space_state
	for y in range(NAV_GRID_SIZE.y):
		for x in range(NAV_GRID_SIZE.x):
			var cell := Vector2i(x, y)
			var world_point := navigation_grid.get_point_position(cell)
			if not Geometry2D.is_point_in_polygon(world_point, market_walkable_polygon):
				navigation_grid.set_point_solid(cell, true)
				continue
			query.transform = Transform2D(0.0, world_point)
			if not space.intersect_shape(query, 1).is_empty():
				navigation_grid.set_point_solid(cell, true)
	navigation_ready = true
	_clear_navigation_path()


func _process(delta: float) -> void:
	if not Engine.is_editor_hint() or not is_instance_valid(sprite):
		return
	# Preview the real limb frames without changing the character's editor position.
	editor_preview_clock += delta
	sprite.frame = int(editor_preview_clock / 0.18) % 4
