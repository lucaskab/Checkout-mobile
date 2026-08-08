#!/bin/bash
# Gera todos os modelos 3D do Checkout Game
# Uso: ./run_all.sh
# Requer: Blender instalado em /Applications/Blender.app

BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$BLENDER" ]; then
  echo "Blender não encontrado em $BLENDER"
  echo "Ajuste a variável BLENDER no script se necessário."
  exit 1
fi

echo "Gerando modelos 3D..."

"$BLENDER" --background --python "$SCRIPT_DIR/gen_market_building.py"
echo "✓ market_building.fbx"

"$BLENDER" --background --python "$SCRIPT_DIR/gen_bakery.py"
echo "✓ bakery.fbx"

"$BLENDER" --background --python "$SCRIPT_DIR/gen_props.py"
echo "✓ shelf.fbx / checkout_counter.fbx / truck.fbx / tree.fbx"

echo ""
echo "Todos os modelos exportados para: $SCRIPT_DIR"
echo "Copie os .fbx para: unity/Assets/Resources/Models/"
