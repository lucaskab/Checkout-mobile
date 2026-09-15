using System;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using MarketDay;
public static class CheckoutFurnitureSeparation
{
    class Piece {public MeshFilter source;public int block;}
    static readonly Dictionary<MeshFilter,HashSet<int>> removed=new Dictionary<MeshFilter,HashSet<int>>();
    const string Folder="Assets/Art/CityFurniture";
    public static void Apply()
    {
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        if(world.Find("Individual Street Furniture"))throw new InvalidOperationException("Furniture already separated");
        if(!AssetDatabase.IsValidFolder(Folder))AssetDatabase.CreateFolder("Assets/Art","CityFurniture");
        removed.Clear();var root=new GameObject("Individual Street Furniture").transform;root.SetParent(world,true);root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);Undo.RegisterCreatedObjectUndo(root.gameObject,"Separate street furniture");
        MeshFilter Source(string path)=>world.Find(path).GetComponent<MeshFilter>();
        var metal=Source("City Block/CityMetal");var wood=Source("City Block/CityWood");var lens=Source("City Block/CityLamp");var yard=Source("Loading Yard Details/YardCharcoal");var yardLens=Source("Loading Yard Details/YardLamp");
        int before=new[]{metal,wood,lens,yard,yardLens}.Sum(f=>f.sharedMesh.triangles.Length);
        for(int i=0;i<8;i++)Create(root,"Poste Rua "+(i+1).ToString("00"),new[]{Part(metal,3+i*3),Part(metal,4+i*3),Part(metal,5+i*3),Part(lens,i)});
        for(int i=0;i<2;i++)Create(root,"Poste Estacionamento "+(i+1).ToString("00"),new[]{Part(yard,7+i*3),Part(yard,8+i*3),Part(yard,9+i*3),Part(yardLens,i)});
        for(int i=0;i<2;i++)Create(root,"Banco "+(i+1).ToString("00"),Enumerable.Range(i*4,4).Select(n=>Part(wood,n)).Concat(new[]{Part(metal,27+i*2),Part(metal,28+i*2)}).ToArray());
        int remaining=0;
        foreach(var pair in removed)
        {
            var filter=pair.Key;var mesh=UnityEngine.Object.Instantiate(filter.sharedMesh);mesh.name=filter.name+" remainder";
            for(int s=0;s<mesh.subMeshCount;s++){var triangles=mesh.GetTriangles(s);var kept=new List<int>();for(int i=0;i<triangles.Length;i+=3)if(!pair.Value.Contains(triangles[i]/24))kept.AddRange(new[]{triangles[i],triangles[i+1],triangles[i+2]});mesh.SetTriangles(kept,s);remaining+=kept.Count;}
            mesh.RecalculateBounds();AssetDatabase.CreateAsset(mesh,Folder+"/"+filter.name+"Remainder.asset");Undo.RecordObject(filter,"Remove extracted furniture triangles");filter.sharedMesh=mesh;
            if(mesh.triangles.Length==0){Undo.RecordObject(filter.gameObject,"Hide empty combined mesh");filter.gameObject.SetActive(false);}
        }
        int extracted=root.GetComponentsInChildren<MeshFilter>().Sum(f=>f.sharedMesh.triangles.Length);
        if(before!=remaining+extracted)throw new InvalidOperationException("Furniture triangle count changed");
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();
        Debug.Log("FURNITURE_SEPARATED_OK posts=10 benches=2 triangles="+before/3+" preserved");
    }
    static Piece Part(MeshFilter f,int n)=>new Piece{source=f,block=n};
    static void Create(Transform root,string name,Piece[] pieces)
    {
        var vertices=new List<Vector3>();var normals=new List<Vector3>();var uv=new List<Vector2>();var materials=new List<Material>();var submeshes=new List<List<int>>();
        foreach(var p in pieces)
        {
            var mesh=p.source.sharedMesh;int start=p.block*24;if(start+24>mesh.vertexCount)throw new InvalidOperationException("Unexpected furniture mesh layout");
            if(!removed.ContainsKey(p.source))removed[p.source]=new HashSet<int>();if(!removed[p.source].Add(p.block))throw new InvalidOperationException("Duplicate furniture piece");
            int offset=vertices.Count;var v=mesh.vertices;var n=mesh.normals;var u=mesh.uv;
            for(int i=start;i<start+24;i++){vertices.Add(p.source.transform.TransformPoint(v[i]));normals.Add(p.source.transform.localToWorldMatrix.inverse.transpose.MultiplyVector(n[i]).normalized);uv.Add(u[i]);}
            for(int s=0;s<mesh.subMeshCount;s++)
            {
                var mat=p.source.GetComponent<Renderer>().sharedMaterials[s];int index=materials.IndexOf(mat);if(index<0){index=materials.Count;materials.Add(mat);submeshes.Add(new List<int>());}
                var t=mesh.GetTriangles(s);for(int i=0;i<t.Length;i+=3)if(t[i]>=start&&t[i]<start+24){if(t[i+1]/24!=p.block||t[i+2]/24!=p.block)throw new InvalidOperationException("Triangle crosses piece boundary");for(int k=0;k<3;k++)submeshes[index].Add(offset+t[i+k]-start);}
            }
        }
        var bounds=new Bounds(vertices[0],Vector3.zero);foreach(var v in vertices)bounds.Encapsulate(v);var pivot=new Vector3(bounds.center.x,bounds.min.y,bounds.center.z);
        var output=new Mesh{name=name};output.SetVertices(vertices.Select(v=>v-pivot).ToList());output.SetNormals(normals);output.SetUVs(0,uv);output.subMeshCount=materials.Count;for(int i=0;i<submeshes.Count;i++)output.SetTriangles(submeshes[i],i);output.RecalculateBounds();AssetDatabase.CreateAsset(output,Folder+"/"+name+".asset");
        var item=new GameObject(name);item.transform.SetParent(root,true);item.transform.position=pivot;item.AddComponent<MeshFilter>().sharedMesh=output;item.AddComponent<MeshRenderer>().sharedMaterials=materials.ToArray();
    }
}
