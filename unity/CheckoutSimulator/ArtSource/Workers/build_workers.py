"""Bind supplied Meshy worker sculpts to the game’s existing worker clips.

Run from the Unity project directory with:
Blender -b --python ArtSource/Workers/build_workers.py
"""
from pathlib import Path
import json

import bpy
from mathutils import Vector, kdtree

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent
OUT = ROOT / "Assets/Art/Characters/Meshy/Workers"
OUT.mkdir(parents=True, exist_ok=True)
CLIPS = ("Idle", "Walking", "GetFromShelf", "BuyAtSpecialSector", "PayAtCheckout")
WORKERS = {
    "Worker_Baker": "Baker.glb",
    "Worker_Butcher": "Butcher.glb",
    "Worker_Fishmonger": "Fishmonger.glb",
}


def texture_from(mesh):
    material = mesh.data.materials[0]
    return next(
        node.image
        for node in material.node_tree.nodes
        if node.type == "TEX_IMAGE"
        and any(link.to_socket.name == "Base Color" for output in node.outputs for link in output.links)
    )


def body_with_weights(mesh):
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    lowest = min(vertex.co.z for vertex in mesh.data.vertices)
    scale = 2.4 / (max(vertex.co.z for vertex in mesh.data.vertices) - lowest)
    for vertex in mesh.data.vertices:
        vertex.co = Vector((vertex.co.x * scale, vertex.co.y * scale, (vertex.co.z - lowest) * scale))

    source_vertices = len(mesh.data.vertices)
    decimator = mesh.modifiers.new("Mobile mesh", "DECIMATE")
    decimator.ratio = min(1, 24000 / len(mesh.data.polygons))
    bpy.ops.object.modifier_apply(modifier=decimator.name)

    mesh.data.use_fake_user = True
    return source_vertices


def copy_weights(body, source):
    lookup = kdtree.KDTree(len(source.data.vertices))
    for vertex in source.data.vertices:
        lookup.insert(source.matrix_world @ vertex.co, vertex.index)
    lookup.balance()
    groups = {group.index: body.vertex_groups.new(name=group.name) for group in source.vertex_groups}
    for vertex in body.data.vertices:
        _, source_index, _ = lookup.find(body.matrix_world @ vertex.co)
        source_vertex = source.data.vertices[source_index]
        for weight in source_vertex.groups:
            groups[weight.group].add([vertex.index], weight.weight, "REPLACE")

report = {"workers": []}
for worker, filename in WORKERS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE / filename))
    source = next(item for item in bpy.context.scene.objects if item.type == "MESH")
    source_vertices = body_with_weights(source)
    source.name = f"{worker}_MeshyBody"
    image = texture_from(source)
    image.scale(2048, 2048)
    image.filepath_raw = str(OUT / f"{worker}.png")
    image.file_format = "PNG"
    image.save()

    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(ROOT / f"Assets/Art/Characters/{worker}.fbx"))
    imported = set(bpy.data.objects) - before
    rig = next(item for item in imported if item.type == "ARMATURE")
    original_body = next(item for item in imported if item.type == "MESH")
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True

    body = source.copy()
    body.data = source.data.copy()
    bpy.context.collection.objects.link(body)
    copy_weights(body, original_body)
    body.parent = rig
    modifier = body.modifiers.new("Worker skeleton", "ARMATURE")
    modifier.object = rig

    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / f"{worker}.fbx"), use_selection=True, object_types={"ARMATURE", "MESH"},
        add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0, axis_forward="-Z", axis_up="Y", path_mode="STRIP",
    )
    report["workers"].append({
        "name": worker,
        "sourceVertices": source_vertices,
        "vertices": len(source.data.vertices),
        "triangles": sum(len(face.vertices) - 2 for face in source.data.polygons),
        "clips": [action.name.split("|")[-1] for action in bpy.data.actions if action.name.startswith(f"{worker}_Rig|")],
    })

(SOURCE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
print("WORKER_EXPORT_OK", json.dumps(report))
