extends Node

var coins := 2450
var gems := 12
var stock := 18
var harvested := false
var delivery_received := false
var dragging_camera := false
var last_mouse_position := Vector2.ZERO

var coins_label: Label
var gems_label: Label
var stock_label: Label
var status_label: Label
var harvest_goal: Label
var delivery_goal: Label
var sale_goal: Label
var camera: Camera2D


func _ready() -> void:
	camera = get_node("../Camera2D")
	_build_hud()
	_connect_world_objects()
	_update_hud()


func _connect_world_objects() -> void:
	get_node("../WorldObjects/FarmPlots/ClickArea").input_event.connect(_on_farm_input)
	get_node("../WorldObjects/Warehouse/ClickArea").input_event.connect(_on_warehouse_input)
	get_node("../WorldObjects/Supermarket/ClickArea").input_event.connect(_on_market_input)


func _build_hud() -> void:
	var canvas := CanvasLayer.new()
	canvas.name = "HUD"
	canvas.layer = 20
	add_child(canvas)

	var top_bar := HBoxContainer.new()
	top_bar.name = "TopBar"
	top_bar.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top_bar.offset_left = 18
	top_bar.offset_top = 14
	top_bar.offset_right = -18
	top_bar.add_theme_constant_override("separation", 14)
	canvas.add_child(top_bar)

	var profile := _panel(Color("f7e5bd"), Color("70432f"), 18)
	profile.custom_minimum_size = Vector2(315, 84)
	top_bar.add_child(profile)
	var profile_box := VBoxContainer.new()
	profile_box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 12)
	profile.add_child(profile_box)
	var title := _label("MERCADO DO VALE", 23, Color("633b2a"))
	profile_box.add_child(title)
	var level := _label("NÍVEL 1  •  Expansão rural", 15, Color("865b3d"))
	profile_box.add_child(level)
	var progress := ProgressBar.new()
	progress.value = 38
	progress.show_percentage = false
	progress.custom_minimum_size.y = 12
	profile_box.add_child(progress)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top_bar.add_child(spacer)
	coins_label = _resource_pill("MOEDAS", Color("f3b833"))
	top_bar.add_child(coins_label.get_parent().get_parent())
	gems_label = _resource_pill("GEMAS", Color("49cfe2"))
	top_bar.add_child(gems_label.get_parent().get_parent())
	stock_label = _resource_pill("ESTOQUE", Color("5fbd66"))
	top_bar.add_child(stock_label.get_parent().get_parent())

	var goals := _panel(Color("fff4d6"), Color("70432f"), 16)
	goals.name = "Goals"
	goals.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	goals.position = Vector2(-290, 112)
	goals.size = Vector2(270, 154)
	canvas.add_child(goals)
	var goal_box := VBoxContainer.new()
	goal_box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 12)
	goal_box.add_theme_constant_override("separation", 7)
	goals.add_child(goal_box)
	goal_box.add_child(_label("OBJETIVOS DO DIA", 19, Color("633b2a")))
	harvest_goal = _label("□ Colher a horta", 15, Color("7c5439"))
	delivery_goal = _label("□ Receber entrega", 15, Color("7c5439"))
	sale_goal = _label("□ Vender 5 produtos", 15, Color("7c5439"))
	goal_box.add_child(harvest_goal)
	goal_box.add_child(delivery_goal)
	goal_box.add_child(sale_goal)

	var bottom := HBoxContainer.new()
	bottom.name = "BottomBar"
	bottom.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	bottom.position = Vector2(-330, -92)
	bottom.add_theme_constant_override("separation", 12)
	canvas.add_child(bottom)
	for item in [["🔨", "CONSTRUIR"], ["📦", "ESTOQUE"], ["🚚", "ENTREGAS"], ["🌱", "FAZENDA"]]:
		var button := Button.new()
		button.text = "%s\n%s" % [item[0], item[1]]
		button.custom_minimum_size = Vector2(150, 74)
		button.add_theme_font_size_override("font_size", 16)
		button.add_theme_color_override("font_color", Color("553521"))
		button.add_theme_stylebox_override("normal", _style(Color("f7d66c"), Color("74472d"), 18, 3))
		button.add_theme_stylebox_override("hover", _style(Color("ffe78e"), Color("74472d"), 18, 4))
		button.pressed.connect(_on_toolbar_pressed.bind(item[1]))
		bottom.add_child(button)

	status_label = _label("Clique na horta, no depósito ou no mercado.", 17, Color.WHITE)
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	status_label.position = Vector2(-310, -128)
	status_label.size = Vector2(620, 30)
	status_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.75))
	status_label.add_theme_constant_override("shadow_offset_x", 2)
	status_label.add_theme_constant_override("shadow_offset_y", 2)
	canvas.add_child(status_label)


func _panel(fill: Color, border: Color, radius: int) -> Panel:
	var panel := Panel.new()
	panel.add_theme_stylebox_override("panel", _style(fill, border, radius, 3))
	return panel


func _style(fill: Color, border: Color, radius: int, width: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = fill
	style.border_color = border
	style.set_border_width_all(width)
	style.set_corner_radius_all(radius)
	style.shadow_color = Color(0.16, 0.09, 0.04, 0.28)
	style.shadow_size = 5
	style.content_margin_left = 10
	style.content_margin_right = 10
	style.content_margin_top = 8
	style.content_margin_bottom = 8
	return style


func _label(text_value: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text_value
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	return label


func _resource_pill(caption: String, accent: Color) -> Label:
	var panel := _panel(Color("fff4d6"), Color("70432f"), 18)
	panel.custom_minimum_size = Vector2(145, 62)
	var box := VBoxContainer.new()
	box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 9)
	panel.add_child(box)
	var caption_label := _label(caption, 12, Color("80583d"))
	box.add_child(caption_label)
	var value := _label("0", 22, accent)
	box.add_child(value)
	return value


func _update_hud() -> void:
	coins_label.text = str(coins)
	gems_label.text = str(gems)
	stock_label.text = str(stock)


func _on_farm_input(_viewport: Node, event: InputEvent, _shape: int) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		if harvested:
			_show_status("A horta está crescendo novamente.")
			return
		harvested = true
		stock += 12
		coins += 120
		harvest_goal.text = "✓ Colher a horta"
		harvest_goal.add_theme_color_override("font_color", Color("39954b"))
		_show_status("Colheita concluída: +12 estoque e +120 moedas!")
		_bounce(get_node("../WorldObjects/FarmPlots"))
		_update_hud()


func _on_warehouse_input(_viewport: Node, event: InputEvent, _shape: int) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		if delivery_received:
			_show_status("A próxima entrega chega em breve.")
			return
		delivery_received = true
		stock += 20
		delivery_goal.text = "✓ Receber entrega"
		delivery_goal.add_theme_color_override("font_color", Color("39954b"))
		_show_status("Entrega recebida: +20 produtos no estoque!")
		_bounce(get_node("../WorldObjects/Warehouse"))
		_update_hud()


func _on_market_input(_viewport: Node, event: InputEvent, _shape: int) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		var sold := mini(5, stock)
		if sold == 0:
			_show_status("Sem estoque. Colha ou receba uma entrega primeiro.")
			return
		stock -= sold
		coins += sold * 35
		sale_goal.text = "✓ Vender 5 produtos"
		sale_goal.add_theme_color_override("font_color", Color("39954b"))
		_show_status("Venda concluída: +%d moedas!" % (sold * 35))
		_bounce(get_node("../WorldObjects/Supermarket"))
		_update_hud()


func _on_toolbar_pressed(action: String) -> void:
	_show_status("Modo %s selecionado." % action.to_lower())


func _show_status(message: String) -> void:
	status_label.text = message
	var tween := create_tween()
	tween.tween_property(status_label, "modulate", Color(1, 1, 1, 1), 0.1)
	tween.tween_interval(2.2)
	tween.tween_property(status_label, "modulate", Color(1, 1, 1, 0.65), 0.35)


func _bounce(node: Node2D) -> void:
	var base_scale := node.scale
	var tween := create_tween()
	tween.tween_property(node, "scale", base_scale * 1.06, 0.12).set_trans(Tween.TRANS_BACK)
	tween.tween_property(node, "scale", base_scale, 0.18).set_trans(Tween.TRANS_BACK)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			camera.zoom = (camera.zoom * 1.1).clamp(Vector2(0.55, 0.55), Vector2(1.45, 1.45))
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			camera.zoom = (camera.zoom / 1.1).clamp(Vector2(0.55, 0.55), Vector2(1.45, 1.45))
		elif event.button_index == MOUSE_BUTTON_MIDDLE:
			dragging_camera = event.pressed
			last_mouse_position = event.position
	elif event is InputEventMouseMotion and dragging_camera:
		camera.position -= event.relative / camera.zoom
