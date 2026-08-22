extends SceneTree


func _initialize() -> void:
	call_deferred("_capture")


func _capture() -> void:
	var packed := load("res://Scene/supermarket_assets_game_v2.tscn") as PackedScene
	var scene := packed.instantiate()
	root.add_child(scene)
	for frame in range(12):
		await process_frame
	var image := root.get_texture().get_image()
	var destination := ProjectSettings.globalize_path("res://checkout_integration_preview.png")
	var result := image.save_png(destination)
	print("CAPTURE_RESULT=", result, " PATH=", destination)
	quit(0 if result == OK else 1)
