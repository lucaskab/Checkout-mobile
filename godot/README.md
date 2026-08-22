# Checkout Market Simulator

Editable Godot 4.5.1 project embedded by the React Native app.

- Main scene: `Scene/supermarket_assets_game_v2.tscn`
- React Native bridge: `Scene/Scripts/react_native_bridge.gd`
- Simulation state: `Scene/Scripts/checkout_game_state.gd`
- Mobile export presets: `export_presets.cfg`

Open `project.godot` in Godot. From the repository root, run
`bun run godot:export` after game changes to regenerate the Android and iOS
artifacts consumed by the Expo config plugin.
