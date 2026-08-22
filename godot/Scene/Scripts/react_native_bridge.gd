class_name ReactNativeBridge
extends Node

var game_state: CheckoutGameState
var _snapshot_json := "{}"


func setup(state: CheckoutGameState) -> void:
	game_state = state
	game_state.state_changed.connect(_cache_state)
	_cache_state(game_state.get_snapshot())


func dispatch_json(command_json: String) -> void:
	var parsed: Variant = JSON.parse_string(command_json)
	if parsed is Dictionary:
		game_state.dispatch(parsed)


func get_snapshot_json() -> String:
	return _snapshot_json


func _cache_state(snapshot: Dictionary) -> void:
	_snapshot_json = JSON.stringify(snapshot)
