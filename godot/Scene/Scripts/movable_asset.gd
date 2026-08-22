extends StaticBody2D

var dragging := false
var drag_offset := Vector2.ZERO


func _ready() -> void:
	input_pickable = true


func _input_event(_viewport: Node, event: InputEvent, _shape_idx: int) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		dragging = event.pressed
		if dragging:
			drag_offset = global_position - get_global_mouse_position()
		get_viewport().set_input_as_handled()


func _process(_delta: float) -> void:
	if dragging:
		if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
			global_position = get_global_mouse_position() + drag_offset
		else:
			dragging = false
