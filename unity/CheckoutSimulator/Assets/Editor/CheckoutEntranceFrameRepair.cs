using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using MarketDay;

public static class CheckoutEntranceFrameRepair
{
    struct Vertex
    {
        public Vector3 position,normal,world;
        public Vector2 uv;
        public static Vertex Lerp(Vertex a,Vertex b,float t)=>new Vertex{position=Vector3.Lerp(a.position,b.position,t),normal=Vector3.Lerp(a.normal,b.normal,t).normalized,world=Vector3.Lerp(a.world,b.world,t),uv=Vector2.Lerp(a.uv,b.uv,t)};
    }
    // Subtract a precise opening instead of removing whole triangles that cross the door jamb.
    public static void Apply()
    {
        var world=Object.FindAnyObjectByType<MarketSimulation>().world;
        var parent=world.Find("City Detail Repairs");if(parent.Find("Clean entrance frame"))return;
        var filter=world.Find("Building").GetComponent<MeshFilter>();var source=filter.sharedMesh;
        var positions=source.vertices;var normals=source.normals;var uv=source.uv;
        var output=new List<Vertex>();var submeshes=new List<int[]>();
        Vector3 low=new Vector3(-3.65f,.1f,-7.9f),high=new Vector3(.15f,3.4f,-6.7f);
        for(int sub=0;sub<source.subMeshCount;sub++)
        {
            var indices=new List<int>();var triangles=source.GetTriangles(sub);
            for(int i=0;i<triangles.Length;i+=3)
            {
                var polygon=new List<Vertex>();
                for(int k=0;k<3;k++){int v=triangles[i+k];polygon.Add(new Vertex{position=positions[v],normal=normals[v],uv=uv[v],world=filter.transform.TransformPoint(positions[v])});}
                for(int plane=0;plane<6&&polygon.Count>0;plane++)
                {
                    int axis=plane/2;bool minimum=plane%2==0;float boundary=minimum?low[axis]:high[axis];
                    var inside=new List<Vertex>();var outside=new List<Vertex>();
                    for(int edge=0;edge<polygon.Count;edge++)
                    {
                        var a=polygon[edge];var b=polygon[(edge+1)%polygon.Count];
                        float da=minimum?a.world[axis]-boundary:boundary-a.world[axis];
                        float db=minimum?b.world[axis]-boundary:boundary-b.world[axis];
                        bool ia=da>=0,ib=db>=0;
                        if(ia)inside.Add(a);else outside.Add(a);
                        if(ia!=ib){var cut=Vertex.Lerp(a,b,da/(da-db));inside.Add(cut);outside.Add(cut);}
                    }
                    if(outside.Count>=3){int at=output.Count;output.AddRange(outside);for(int k=1;k<outside.Count-1;k++){indices.Add(at);indices.Add(at+k);indices.Add(at+k+1);}}
                    polygon=inside;
                }
            }
            submeshes.Add(indices.ToArray());
        }
        var mesh=new Mesh{name="Building with clean doorway",indexFormat=UnityEngine.Rendering.IndexFormat.UInt32};
        mesh.vertices=output.ConvertAll(v=>v.position).ToArray();mesh.normals=output.ConvertAll(v=>v.normal).ToArray();mesh.uv=output.ConvertAll(v=>v.uv).ToArray();mesh.subMeshCount=submeshes.Count;for(int i=0;i<submeshes.Count;i++)mesh.SetTriangles(submeshes[i],i);mesh.RecalculateBounds();
        AssetDatabase.CreateAsset(mesh,"Assets/Art/CityTiles/BuildingCleanDoorway.asset");Undo.RecordObject(filter,"Clean entrance frame");filter.sharedMesh=mesh;
        var root=new GameObject("Clean entrance frame").transform;root.SetParent(parent,false);Undo.RegisterCreatedObjectUndo(root.gameObject,"Replace damaged door surround");
        var material=new Material(Shader.Find("Standard")){color=new Color(.12f,.48f,.42f)};material.SetFloat("_Glossiness",.1f);AssetDatabase.CreateAsset(material,"Assets/Art/CityTiles/EntranceFrame.mat");
        void Box(string name,Vector3 position,Vector3 size){var item=GameObject.CreatePrimitive(PrimitiveType.Cube);item.name=name;item.transform.SetParent(root,false);item.transform.position=position;item.transform.localScale=size;item.GetComponent<Renderer>().sharedMaterial=material;Object.DestroyImmediate(item.GetComponent<Collider>());}
        Box("Left door jamb",new Vector3(-3.43f,1.73f,-7.28f),new Vector3(.42f,2.3f,.55f));
        Box("Right door jamb",new Vector3(-.07f,1.73f,-7.28f),new Vector3(.42f,2.3f,.55f));
        Box("Entrance header",new Vector3(-1.75f,2.97f,-7.28f),new Vector3(3.78f,.3f,.55f));
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();
    }
}
