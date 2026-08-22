class_name CozyMarketHUD
extends CanvasLayer

const INK := Color("#273b32")
const MUTED := Color("#718078")
const CREAM := Color("#fffaf0")
const GREEN := Color("#477a5b")
const MINT := Color("#dcebdd")
const GOLD := Color("#f0b95d")
const CORAL := Color("#df765f")

var game_state: CheckoutGameState
var top_bar: PanelContainer
var side_card: PanelContainer
var bottom_bar: PanelContainer
var toast_panel: PanelContainer
var cash_label: Label
var time_label: Label
var visitors_label: Label
var profit_label: Label
var queue_label: Label
var stock_label: Label
var pause_button: Button
var speed_button: Button
var toast_label: Label
var _toast_tween: Tween


func setup(state: CheckoutGameState) -> void:
	game_state = state
	_build_ui()
	game_state.state_changed.connect(_render)
	game_state.toast_requested.connect(_show_toast)
	get_viewport().size_changed.connect(_layout)
	_render(game_state.get_snapshot())


func _build_ui() -> void:
	var root := Control.new()
	root.name = "CozyInterface"
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(root)

	top_bar = PanelContainer.new()
	top_bar.add_theme_stylebox_override("panel", _panel_style(CREAM, 24, Color(0.12, 0.22, 0.16, 0.18), 10))
	root.add_child(top_bar)
	var top_row := HBoxContainer.new()
	top_row.add_theme_constant_override("separation", 22)
	top_bar.add_child(top_row)
	top_row.add_child(_brand_block())
	top_row.add_child(_divider())
	cash_label = _metric("R$ 0,00", "SALDO", GREEN)
	top_row.add_child(cash_label.get_parent())
	profit_label = _metric("R$ 0,00", "LUCRO HOJE", GREEN)
	top_row.add_child(profit_label.get_parent())
	visitors_label = _metric("0", "CLIENTES", GREEN)
	top_row.add_child(visitors_label.get_parent())
	time_label = _metric("09:30", "DIA 12", GREEN)
	top_row.add_child(time_label.get_parent())

	side_card = PanelContainer.new()
	side_card.add_theme_stylebox_override("panel", _panel_style(Color("#fff8e7"), 26, Color(0.12, 0.22, 0.16, 0.18), 10))
	root.add_child(side_card)
	var side := VBoxContainer.new()
	side.add_theme_constant_override("separation", 14)
	side_card.add_child(side)
	var eyebrow := _label("VISÃO DA LOJA", 12, GREEN)
	side.add_child(eyebrow)
	var title := _label("Mercado Girassol", 24, INK)
	side.add_child(title)
	var separator := HSeparator.new()
	separator.modulate = Color(0.25, 0.45, 0.32, 0.22)
	side.add_child(separator)
	queue_label = _info_row("Fila no caixa", "0")
	side.add_child(queue_label.get_parent())
	stock_label = _info_row("Estoque baixo", "0")
	side.add_child(stock_label.get_parent())
	var reputation := _info_row("Reputação", "4.7 / 5")
	reputation.name = "ReputationValue"
	side.add_child(reputation.get_parent())
	var hint := _label("Mantenha as prateleiras cheias\ne a fila andando para crescer.", 13, MUTED)
	hint.name = "Hint"
	side.add_child(hint)

	bottom_bar = PanelContainer.new()
	bottom_bar.add_theme_stylebox_override("panel", _panel_style(Color("#fffaf1"), 28, Color(0.12, 0.22, 0.16, 0.22), 12))
	root.add_child(bottom_bar)
	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", 10)
	bottom_bar.add_child(actions)
	pause_button = _action_button("Pausar", GREEN)
	pause_button.pressed.connect(func(): game_state.dispatch({"action": "toggle_pause"}))
	actions.add_child(pause_button)
	speed_button = _action_button("Velocidade 1x", Color("#5d7569"))
	speed_button.pressed.connect(_cycle_speed)
	actions.add_child(speed_button)
	var restock := _action_button("Repor estoque", GOLD)
	restock.add_theme_color_override("font_color", INK)
	restock.pressed.connect(func(): game_state.dispatch({"action": "restock_all"}))
	actions.add_child(restock)
	var hire := _action_button("Contratar", CORAL)
	hire.pressed.connect(func(): game_state.dispatch({"action": "hire_employee", "role": "cashiers"}))
	actions.add_child(hire)
	var upgrade := _action_button("Melhorar caixa", Color("#745d83"))
	upgrade.pressed.connect(func(): game_state.dispatch({"action": "upgrade_checkout"}))
	actions.add_child(upgrade)

	toast_panel = PanelContainer.new()
	toast_panel.modulate.a = 0.0
	toast_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	toast_panel.add_theme_stylebox_override("panel", _panel_style(INK, 18, Color(0, 0, 0, 0.25), 8))
	root.add_child(toast_panel)
	toast_label = _label("", 14, Color.WHITE)
	toast_panel.add_child(toast_label)
	_layout()


func _layout() -> void:
	var size := get_viewport().get_visible_rect().size
	top_bar.position = Vector2(24, 22)
	top_bar.size = Vector2(minf(860, size.x - 360), 82)
	side_card.position = Vector2(size.x - 314, 22)
	side_card.size = Vector2(290, 250)
	bottom_bar.position = Vector2(24, size.y - 90)
	bottom_bar.size = Vector2(minf(735, size.x - 48), 66)
	toast_panel.position = Vector2(size.x * 0.5 - 145, size.y - 150)
	toast_panel.size = Vector2(290, 48)


func _render(snapshot: Dictionary) -> void:
	cash_label.text = _money(float(snapshot.cash))
	profit_label.text = _money(float(snapshot.profitToday))
	visitors_label.text = str(snapshot.customersInStore)
	time_label.text = str(snapshot.time)
	var time_caption := time_label.get_parent().get_node("Caption") as Label
	time_caption.text = "DIA %d" % int(snapshot.day)
	queue_label.text = str(snapshot.queueSize)
	var low_count := 0
	for product in snapshot.products:
		if product.low:
			low_count += 1
	stock_label.text = str(low_count)
	var reputation_value := side_card.find_child("ReputationValue", true, false) as Label
	if reputation_value != null:
		reputation_value.text = "%.1f / 5" % float(snapshot.reputation)
	pause_button.text = "Continuar" if snapshot.paused else "Pausar"
	speed_button.text = "Velocidade %.1fx" % float(snapshot.gameSpeed)


func _cycle_speed() -> void:
	var next_speed := 2.0 if game_state.game_speed < 1.5 else (3.0 if game_state.game_speed < 2.5 else 1.0)
	game_state.dispatch({"action": "set_speed", "value": next_speed})


func _show_toast(message: String, tone: String) -> void:
	toast_label.text = message
	var color := GREEN
	if tone == "warning":
		color = CORAL
	elif tone == "info":
		color = Color("#526c79")
	toast_panel.add_theme_stylebox_override("panel", _panel_style(color, 18, Color(0, 0, 0, 0.25), 8))
	if _toast_tween != null:
		_toast_tween.kill()
	toast_panel.modulate.a = 0.0
	_toast_tween = create_tween()
	_toast_tween.tween_property(toast_panel, "modulate:a", 1.0, 0.18)
	_toast_tween.tween_interval(2.2)
	_toast_tween.tween_property(toast_panel, "modulate:a", 0.0, 0.25)


func _brand_block() -> Control:
	var box := VBoxContainer.new()
	box.custom_minimum_size = Vector2(170, 0)
	var name_label := _label("MERCADO", 22, INK)
	box.add_child(name_label)
	var subtitle := _label("GIRASSOL  •  ABERTO", 11, GREEN)
	box.add_child(subtitle)
	return box


func _metric(value: String, caption: String, color: Color) -> Label:
	var box := VBoxContainer.new()
	box.custom_minimum_size = Vector2(116, 0)
	var value_label := _label(value, 19, color)
	box.add_child(value_label)
	var caption_label := _label(caption, 10, MUTED)
	caption_label.name = "Caption"
	box.add_child(caption_label)
	return value_label


func _info_row(title: String, value: String) -> Label:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var key := _label(title, 14, MUTED)
	key.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(key)
	var value_label := _label(value, 16, INK)
	row.add_child(value_label)
	return value_label


func _action_button(text_value: String, color: Color) -> Button:
	var button := Button.new()
	button.text = text_value
	button.custom_minimum_size = Vector2(132, 46)
	button.add_theme_font_size_override("font_size", 14)
	button.add_theme_color_override("font_color", Color.WHITE)
	button.add_theme_color_override("font_hover_color", Color.WHITE)
	button.add_theme_stylebox_override("normal", _panel_style(color, 18, Color(0, 0, 0, 0.16), 5))
	button.add_theme_stylebox_override("hover", _panel_style(color.lightened(0.08), 18, Color(0, 0, 0, 0.18), 7))
	button.add_theme_stylebox_override("pressed", _panel_style(color.darkened(0.08), 18, Color(0, 0, 0, 0.08), 2))
	return button


func _divider() -> VSeparator:
	var divider := VSeparator.new()
	divider.modulate = Color(0.2, 0.35, 0.25, 0.25)
	return divider


func _label(text_value: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text_value
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	return label


func _panel_style(color: Color, radius: int, shadow: Color, shadow_size: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.corner_radius_top_left = radius
	style.corner_radius_top_right = radius
	style.corner_radius_bottom_left = radius
	style.corner_radius_bottom_right = radius
	style.content_margin_left = 18
	style.content_margin_right = 18
	style.content_margin_top = 12
	style.content_margin_bottom = 12
	style.shadow_color = shadow
	style.shadow_size = shadow_size
	style.shadow_offset = Vector2(0, 4)
	return style


func _money(value: float) -> String:
	return "R$ %s" % ("%.2f" % value).replace(".", ",")
