using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Tilemaps;

public class CheckoutTerrainPainter : EditorWindow
{
    static readonly string[] RuralNames = { "Grama", "Estrada", "Rio", "Pátio", "Caminho", "Ponte" };
    static readonly string[] CityNames = { "Rua", "Faixa de pedestres", "Calçada", "Praça", "Asfalto", "Borda de calçada", "Esquina de calçada" };
    string[] Names => city ? CityNames : RuralNames;
    TileBase[] tiles;
    bool city;
    Tilemap map;
    int brush, size = 1;
    bool painting, stroke;
    Vector3Int lastCell;

    [MenuItem("Supermarket/Terrain Painter")]
    public static void Open() => GetWindow<CheckoutTerrainPainter>("Terrain Painter");

    void OnEnable() { SceneView.duringSceneGui += Paint; Undo.undoRedoPerformed += Refresh; }
    void OnDisable() { SceneView.duringSceneGui -= Paint; Undo.undoRedoPerformed -= Refresh; }

    void OnGUI()
    {
        if (!map) map = FindObjectsByType<Tilemap>().FirstOrDefault(t => t.name == CheckoutTerrainBuilder.TerrainName);
        bool nextCity = map && map.GetComponent<TilemapRenderer>().sharedMaterial.shader.name == "MarketDay/City Tiles";
        if (city != nextCity) { city = nextCity; tiles = null; }
        if (tiles == null || tiles.Length != Names.Length || tiles.Any(tile => !tile))
            tiles = city ? CheckoutCityBuilder.TileNames.Select(name => AssetDatabase.LoadAssetAtPath<TileBase>(CheckoutCityBuilder.AssetRoot + name + "Tile.asset")).ToArray()
                : new[] { "Grass", "Road", "Water", "Courtyard", "Path", "Bridge" }.Select(name => AssetDatabase.LoadAssetAtPath<TileBase>(CheckoutTerrainBuilder.AssetRoot + name + "Tile.asset")).ToArray();
        brush=Mathf.Clamp(brush,0,Names.Length-1);
        EditorGUILayout.LabelField("Pintar o mapa", EditorStyles.boldLabel);
        EditorGUILayout.HelpBox(city ? "Pinte na Scene. Ruas e faixas conectam retas, curvas e cruzamentos automaticamente. Use Calçada para apagar ruas e Cmd/Ctrl+Z para desfazer."
            : "Arraste na Scene. As RuleTiles conectam curvas, cruzamentos e margens. Pinte Ponte sobre o rio para ligar estradas. Use Grama para apagar e Cmd/Ctrl+Z para desfazer.", MessageType.Info);
        using (new EditorGUI.DisabledScope(EditorApplication.isPlaying || !map || tiles.Any(tile => !tile)))
        {
            brush = Mathf.Clamp(GUILayout.SelectionGrid(brush, Names, 2, GUILayout.Height(96)),0,Names.Length-1);
            size = EditorGUILayout.IntSlider("Tamanho do pincel", size, 1, 4);
            painting = EditorGUILayout.Toggle("Ativar pintura", painting);
            if (GUILayout.Button("Enquadrar mapa na Scene"))
            {
                var scene=GetWindow<SceneView>();
                scene.LookAt(new Vector3(0f,.13f,8f),Quaternion.Euler(90f,0f,0f),36f,true);
            }
            if (tiles[brush] is RuleTile selected && selected.m_DefaultSprite)
            {
                var sprite = selected.m_DefaultSprite;
                var rect = sprite.rect;
                GUI.DrawTextureWithTexCoords(GUILayoutUtility.GetRect(120,120,GUILayout.Width(120)),sprite.texture,
                    new Rect(rect.x/sprite.texture.width,rect.y/sprite.texture.height,rect.width/sprite.texture.width,rect.height/sprite.texture.height));
            }
        }
        if (!map) EditorGUILayout.HelpBox("Aplique o terreno pelo menu Supermarket para começar.", MessageType.Warning);
        if (EditorApplication.isPlaying) EditorGUILayout.HelpBox("Saia do Play Mode para editar e salvar o mapa.", MessageType.Info);
    }

    void Refresh() { if (map) map.RefreshAllTiles(); SceneView.RepaintAll(); }

    void Paint(SceneView scene)
    {
        if (!painting || !map || tiles == null || tiles.Length!=Names.Length || brush<0 || brush>=tiles.Length || !tiles[brush] || EditorApplication.isPlaying) return;
        var input = Event.current;
        if (input.alt) return;
        var plane = new Plane(Vector3.up, map.transform.position);
        var ray = HandleUtility.GUIPointToWorldRay(input.mousePosition);
        if (!plane.Raycast(ray, out float distance)) return;
        var cell = map.WorldToCell(ray.GetPoint(distance));
        cell.z = 0;
        cell -= new Vector3Int((size - 1) / 2, (size - 1) / 2, 0);
        var corners = new[] { cell, cell + new Vector3Int(size,0,0), cell + new Vector3Int(size,size,0), cell + new Vector3Int(0,size,0) }
            .Select(point => map.CellToWorld(point) + Vector3.up * .04f).ToArray();
        Handles.DrawSolidRectangleWithOutline(corners, new Color(1,1,1,.12f), Color.white);
        int control=GUIUtility.GetControlID("CheckoutTerrainPainter".GetHashCode(),FocusType.Passive);
        HandleUtility.AddDefaultControl(control);
        if (input.button == 0 && (input.type == EventType.MouseDown || input.type == EventType.MouseDrag))
        {
            if (!stroke) { Undo.RegisterCompleteObjectUndo(map,"Pintar terreno"); stroke = true; lastCell=cell; GUIUtility.hotControl=control; }
            int steps=Mathf.Max(Mathf.Abs(cell.x-lastCell.x),Mathf.Abs(cell.y-lastCell.y));
            var previous=lastCell;
            for(int i=0;i<=steps;i++)
            {
                var point=Vector3Int.RoundToInt(Vector3.Lerp(lastCell,cell,steps==0?0f:(float)i/steps));
                if(point.x!=previous.x && point.y!=previous.y) Stamp(new Vector3Int(point.x,previous.y,0));
                Stamp(point);
                previous=point;
            }
            lastCell=cell;
            EditorSceneManager.MarkSceneDirty(map.gameObject.scene);
            input.Use();
        }
        if (input.rawType == EventType.MouseUp) { stroke = false; if(GUIUtility.hotControl==control) GUIUtility.hotControl=0; }
        if (input.type == EventType.MouseMove || input.type == EventType.MouseDrag) scene.Repaint();
    }

    void Stamp(Vector3Int cell)
    {
        for(int x=0;x<size;x++)
            for(int y=0;y<size;y++) map.SetTile(cell+new Vector3Int(x,y,0),tiles[brush]);
    }
}
