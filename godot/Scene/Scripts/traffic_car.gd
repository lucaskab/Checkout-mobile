@tool
extends Node2D

@export var route: PackedVector2Array
@export var speed := 115.0
@export var start_delay := 0.0
@export var pause_at_ends := 0.0
@export var ping_pong := false
@export var reverse_texture: Texture2D
@export_range(0, 3, 1) var car_frame := 0:
	set(value):
		car_frame = value
		_update_sprite_frame()

@onready var sprite: Sprite2D = $Sprite2D

var route_index := 1
var route_direction := 1
var delay_clock := 0.0
var pause_clock := 0.0
var motion_clock := 0.0
var sprite_rest_position := Vector2.ZERO
var forward_texture: Texture2D


func _ready() -> void:
	_update_sprite_frame()
	if is_instance_valid(sprite):
		sprite_rest_position = sprite.position
		forward_texture = sprite.texture
	if Engine.is_editor_hint() or route.size() < 2:
		return
	global_position = route[0]
	delay_clock = start_delay


func _process(delta: float) -> void:
	if Engine.is_editor_hint() or route.size() < 2:
		return
	if delay_clock > 0.0:
		delay_clock -= delta
		return
	if pause_clock > 0.0:
		pause_clock -= delta
		return

	var target := route[route_index]
	var direction := global_position.direction_to(target)
	global_position = global_position.move_toward(target, speed * delta)
	motion_clock += delta
	if is_instance_valid(sprite):
		_apply_direction_sprite(direction)
		sprite.position = sprite_rest_position + Vector2(0.0, sin(motion_clock * 10.0) * 1.2)

	if global_position.distance_to(target) <= 1.0:
		_advance_route()


func _advance_route() -> void:
	if ping_pong:
		if route_index == route.size() - 1:
			route_direction = -1
			pause_clock = pause_at_ends
		elif route_index == 0:
			route_direction = 1
			pause_clock = pause_at_ends
		route_index += route_direction
	else:
		route_index += 1
		if route_index >= route.size():
			global_position = route[0]
			route_index = 1
			pause_clock = pause_at_ends


func _update_sprite_frame() -> void:
	var target_sprite := get_node_or_null("Sprite2D") as Sprite2D
	if target_sprite != null:
		target_sprite.frame = car_frame


func _apply_direction_sprite(direction: Vector2) -> void:
	# Isometric drawings cannot be rotated 180 degrees in 2D: that puts their
	# roofs below their wheels. Use a genuine rear-view atlas for northbound
	# travel and mirror only between left/right variants.
	var travels_up := direction.y < 0.0
	if travels_up and reverse_texture != null:
		sprite.texture = reverse_texture
		sprite.flip_h = direction.x > 0.0
	else:
		sprite.texture = forward_texture
		sprite.flip_h = direction.x < 0.0
	sprite.rotation = 0.0
