extends Node2D

signal parked(disembark_position: Vector2)
signal departed

@export var arrival_route: PackedVector2Array
@export var departure_route: PackedVector2Array
@export var speed := 180.0
@export var start_delay := 1.5
@export var boarding_delay := 1.2
@export var loop_delay := 5.0
@export var disembark_offset := Vector2(48.0, 4.0)
@export_range(0, 3, 1) var car_frame := 0
@export var reverse_texture: Texture2D

@onready var sprite: Sprite2D = $Sprite2D

enum CarState { WAITING_TO_ARRIVE, ARRIVING, PARKED, BOARDING, DEPARTING, RESET_WAIT }

var state := CarState.WAITING_TO_ARRIVE
var route_index := 1
var state_clock := 0.0
var motion_clock := 0.0
var sprite_rest_position := Vector2.ZERO
var forward_texture: Texture2D


func _ready() -> void:
	if is_instance_valid(sprite):
		sprite.frame = car_frame
		sprite_rest_position = sprite.position
		forward_texture = sprite.texture
	if arrival_route.size() < 2 or departure_route.size() < 2:
		visible = false
		return
	global_position = arrival_route[0]
	state_clock = start_delay


func _process(delta: float) -> void:
	match state:
		CarState.WAITING_TO_ARRIVE:
			state_clock -= delta
			if state_clock <= 0.0:
				state = CarState.ARRIVING
				route_index = 1
		CarState.ARRIVING:
			_move_along(arrival_route, delta)
		CarState.PARKED:
			pass
		CarState.BOARDING:
			state_clock -= delta
			if state_clock <= 0.0:
				state = CarState.DEPARTING
				route_index = 1
				global_position = departure_route[0]
		CarState.DEPARTING:
			_move_along(departure_route, delta)
		CarState.RESET_WAIT:
			state_clock -= delta
			if state_clock <= 0.0:
				visible = true
				global_position = arrival_route[0]
				state = CarState.ARRIVING
				route_index = 1


func passenger_boarded() -> void:
	if state != CarState.PARKED:
		return
	state = CarState.BOARDING
	state_clock = boarding_delay


func get_disembark_position() -> Vector2:
	return global_position + disembark_offset


func _move_along(points: PackedVector2Array, delta: float) -> void:
	if route_index >= points.size():
		_finish_route()
		return
	var target := points[route_index]
	var direction := global_position.direction_to(target)
	global_position = global_position.move_toward(target, speed * delta)
	motion_clock += delta
	if is_instance_valid(sprite) and direction.length_squared() > 0.0:
		_apply_direction_sprite(direction)
		sprite.position = sprite_rest_position + Vector2(0.0, sin(motion_clock * 10.0) * 1.2)
	if global_position.distance_to(target) <= 1.0:
		route_index += 1
		if route_index >= points.size():
			_finish_route()


func _finish_route() -> void:
	if state == CarState.ARRIVING:
		state = CarState.PARKED
		emit_signal("parked", get_disembark_position())
	elif state == CarState.DEPARTING:
		state = CarState.RESET_WAIT
		state_clock = loop_delay
		visible = false
		emit_signal("departed")


func _apply_direction_sprite(direction: Vector2) -> void:
	var travels_up := direction.y < 0.0
	if travels_up and reverse_texture != null:
		sprite.texture = reverse_texture
		sprite.flip_h = direction.x > 0.0
	else:
		sprite.texture = forward_texture
		sprite.flip_h = direction.x < 0.0
	sprite.rotation = 0.0
