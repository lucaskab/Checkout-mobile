"""Blender background script: bind customer meshes to the shipped customer rigs.

Run: Blender -b --python ArtSource/Customers/build_customers.py
The GLBs are source art only. Every exported FBX keeps an existing customer
armature and its original clips, so navigation and gameplay actions stay intact.
"""
from pathlib import Path
import bmesh
import bpy
import json
import math
from mathutils import Quaternion
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent
OUT = ROOT / "Assets/Art/Characters/Meshy"
OUT.mkdir(parents=True, exist_ok=True)

CLIPS = ["Idle", "Walking", "GetFromShelf", "BuyAtSpecialSector", "PayAtCheckout"]
VARIANTS = [
    ("Customer_01", "Customer_01", "CustomerChild.glb", "CustomerChild"),
    ("Customer_02", "Customer_02", "CustomerChild.glb", "CustomerChild"),
    ("Customer_03", "Customer_03", "CustomerChild.glb", "CustomerChild"),
    ("Customer_04", "Customer_04", "CustomerChild.glb", "CustomerChild"),
    ("Customer_05", "Customer_05", "CustomerChild.glb", "CustomerChild"),
    ("Customer_06", "Customer_01", "Customer_06.glb", "Customer_06"),
    ("Customer_07", "Customer_02", "Customer_07.glb", "Customer_07"),
    ("Customer_08", "Customer_03", "Customer_08.glb", "Customer_08"),
    ("Customer_09", "Customer_04", "Customer_09.glb", "Customer_09"),
]


# Anatomical landmarks in normalized model space; adult meshes are not child rigs.
PROFILES = {
    "Customer_06": dict(hip=1.02, neck=1.87, shoulder=1.80, elbow=1.36, wrist=1.04, width=.30, arm_edge=.27, elbow_x=.35, wrist_x=.37),
    "Customer_07": dict(hip=1.04, neck=1.91, shoulder=1.81, elbow=1.34, wrist=1.01, width=.32, arm_edge=.30, elbow_x=.41, wrist_x=.42),
    "Customer_08": dict(hip=.94, neck=1.77, shoulder=1.70, elbow=1.25, wrist=.94, width=.30, arm_edge=.36, elbow_x=.45, wrist_x=.50),
    "Customer_09": dict(hip=1.02, neck=1.88, shoulder=1.80, elbow=1.34, wrist=1.00, width=.33, arm_edge=.35, elbow_x=.50, wrist_x=.51),
}
DEFAULT_PROFILE = dict(hip=.96, neck=1.68, shoulder=1.52, elbow=1.24, wrist=1.00, width=.265)


def smooth(a, b, value):
    t = max(0, min(1, (value - a) / (b - a)))
    return t * t * (3 - 2 * t)


def base_color_image(mesh):
    for material in mesh.data.materials:
        if not material or not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if node.type != "TEX_IMAGE" or not node.image:
                continue
            if any(link.to_socket.name == "Base Color" for link in node.outputs["Color"].links):
                return node.image
    raise RuntimeError(f"Missing base-color texture for {mesh.name}")


def import_mesh(source_path, appearance):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(source_path))
    imported = set(bpy.data.objects) - before
    meshes = [item for item in imported if item.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"No mesh imported from {source_path}")
    mesh = max(meshes, key=lambda item: len(item.data.vertices))
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    low = min(vertex.co.z for vertex in mesh.data.vertices)
    high = max(vertex.co.z for vertex in mesh.data.vertices)
    scale = 2.4 / (high - low)
    for vertex in mesh.data.vertices:
        vertex.co = Vector((vertex.co.x * scale, vertex.co.y * scale, (vertex.co.z - low) * scale))

    source_vertices = len(mesh.data.vertices)
    modifier = mesh.modifiers.new("Mobile mesh", "DECIMATE")
    modifier.ratio = min(1, 24000 / len(mesh.data.polygons))
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    image = base_color_image(mesh)
    image.scale(2048, 2048)
    image.filepath_raw = str(OUT / f"{appearance}.png")
    image.file_format = "PNG"
    image.save()

    mesh.name = appearance
    for name in ["Torso", "Head"] + [part + "_" + side for side in ["L", "R"] for part in ["Thigh", "Shin", "Foot", "UpperArm", "Forearm", "Hand"]]:
        mesh.vertex_groups.new(name=name)
    # Below the elbow, connected geometry separates hands/sleeves from the hips.
    # A horizontal x threshold alone cuts fingers and pulls wide clothing with arms.
    lower_arms = {}
    if appearance in PROFILES:
        welded = bmesh.new();welded.from_mesh(mesh.data)
        bmesh.ops.remove_doubles(welded, verts=list(welded.verts), dist=.00005)
        welded.to_mesh(mesh.data);welded.free()
        mesh.data.update()
    profile = PROFILES.get(appearance, DEFAULT_PROFILE)
    if appearance in PROFILES:
        limit = profile["elbow"]+.13
        adjacency = {v.index: [] for v in mesh.data.vertices if v.co.z < limit}
        for edge_item in mesh.data.edges:
            a,b = edge_item.vertices
            if a in adjacency and b in adjacency:
                adjacency[a].append(b);adjacency[b].append(a)
        unseen = set(adjacency)
        while unseen:
            seed = unseen.pop();component=[seed];stack=[seed]
            while stack:
                for neighbor in adjacency[stack.pop()]:
                    if neighbor in unseen:
                        unseen.remove(neighbor);component.append(neighbor);stack.append(neighbor)
            center_x = sum(mesh.data.vertices[i].co.x for i in component)/len(component)
            highest = max(mesh.data.vertices[i].co.z for i in component)
            is_arm = float(abs(center_x)>profile["width"]*.90 and highest>profile["wrist"]-.1)
            if len(component)>100: print("SKIN_COMPONENT",appearance,len(component),round(center_x,3),round(highest,3),is_arm)
            if is_arm or highest<profile["wrist"]-.1:
                for i in component: lower_arms[i]=is_arm
    for vertex in mesh.data.vertices:
        x, y, z = vertex.co
        side = "L" if x < 0 else "R"
        profile = PROFILES.get(appearance, DEFAULT_PROFILE)
        hip, neck, shoulder, elbow, wrist = [profile[key] for key in ["hip", "neck", "shoulder", "elbow", "wrist"]]
        head = smooth(neck-.08, neck+.05, z)
        edge = profile["width"]-.04
        edge += (profile.get("arm_edge",edge)-edge)*(1-smooth(elbow,shoulder,z))
        arm = smooth(edge, edge+(.025 if appearance in PROFILES else .065), abs(x)) * (1-smooth(shoulder-.03, shoulder+.10, z)) * smooth(wrist-.30, wrist-.18, z)
        if vertex.index in lower_arms:
            blend = smooth(elbow-.02,elbow+.13,z)
            arm = lower_arms[vertex.index]*(1-blend)+arm*blend
        leg = (1-smooth(hip-.08, hip+.07, z)) * (1-arm)
        weights = {"Head": head, "Torso": (1 - head) * (1 - arm - leg)}
        hand = 1 - smooth(wrist-.06, wrist+.06, z)
        forearm = (1 - smooth(elbow-.06, elbow+.06, z)) * (1 - hand)
        for name, value in [("Hand", hand), ("Forearm", forearm), ("UpperArm", 1 - hand - forearm)]:
            weights[name + "_" + side] = (1 - head) * arm * value
        foot = 1 - smooth(.12, .23, z)
        shin = (1 - smooth(hip*.5-.06, hip*.5+.06, z)) * (1 - foot)
        for name, value in [("Foot", foot), ("Shin", shin), ("Thigh", 1 - foot - shin)]:
            weights[name + "_" + side] = (1 - head) * leg * value
        weights = sorted(((name, weight) for name, weight in weights.items() if weight > .001), key=lambda pair: -pair[1])[:4]
        total = sum(weight for _, weight in weights)
        for name, weight in weights:
            mesh.vertex_groups[name].add([vertex.index], weight / total, "REPLACE")
    mesh.data.use_fake_user = True
    return mesh, source_vertices


def export_customer(mesh, output_name, rig_name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(ROOT / f"Assets/Art/Characters/{rig_name}.fbx"))
    imported = set(bpy.data.objects) - before
    rig = next(item for item in imported if item.type == "ARMATURE")
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True

    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    profile = PROFILES.get(output_name, DEFAULT_PROFILE)
    hip, neck, shoulder, elbow, wrist = [profile[key] for key in ["hip", "neck", "shoulder", "elbow", "wrist"]]
    centers = {"Torso": (0, 0, hip), "Head": (0, 0, neck)}
    for side, sign in [("L", -1), ("R", 1)]:
        for part, x, y, z in [("Thigh", .15, 0, hip-.04), ("Shin", .15, 0, hip*.5), ("Foot", .16, 0, .12), ("UpperArm", profile["width"], 0, shoulder), ("Forearm", profile.get("elbow_x",profile["width"]+.055), 0, elbow), ("Hand", profile.get("wrist_x",profile["width"]+.09), -.025, wrist)]:
            centers[part + "_" + side] = (sign * x, y, z)
    for bone in rig.data.edit_bones:
        if bone.name in centers:
            delta = Vector(centers[bone.name]) - bone.head
            bone.head += delta
            bone.tail += delta
    bpy.ops.object.mode_set(mode="OBJECT")

    props = []
    for item in list(imported):
        if item.type != "MESH":
            continue
        group = item.vertex_groups.get("Prop")
        edit_mesh = bmesh.new()
        edit_mesh.from_mesh(item.data)
        deform = edit_mesh.verts.layers.deform.active
        remove = [vertex for vertex in edit_mesh.verts if not group or not deform or vertex[deform].get(group.index, 0) < .5]
        bmesh.ops.delete(edit_mesh, geom=remove, context="VERTS")
        edit_mesh.to_mesh(item.data)
        edit_mesh.free()
        if len(item.data.vertices):
            item.name = output_name + "_Prop"
            props.append(item)
        else:
            bpy.data.objects.remove(item, do_unlink=True)

    body = mesh.copy()
    body.data = mesh.data.copy()
    body.name = output_name + "_Body"
    bpy.context.collection.objects.link(body)
    body.parent = rig
    modifier = body.modifiers.new("Customer skeleton", "ARMATURE")
    modifier.object = rig

    # Preserve the original loaded/held-basket walk and create a free two-arm walk.
    walking = next(action for action in bpy.data.actions if action.name == rig_name+"_Rig|Walking")
    frames = range(1, 26)
    samples = []
    rig.animation_data.action = walking
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        samples.append({bone.name: (bone.location.copy(), bone.rotation_quaternion.copy(), bone.scale.copy()) for bone in rig.pose.bones})
    walking.name = rig_name+"_Rig|WalkingWithBasket"
    free = bpy.data.actions.new(rig_name+"_Rig|Walking")
    for action, carrying in [(walking, True), (free, False)]:
        rig.animation_data.action = action
        for frame, pose in zip(frames, samples):
            phase = (frame-1)/24*math.tau
            for bone in rig.pose.bones:
                bone.rotation_mode="QUATERNION"
                bone.location, bone.rotation_quaternion, bone.scale = pose[bone.name]
                side = 1 if bone.name.endswith("L") else -1
                swing = math.sin(phase)*side
                if bone.name=="Torso":
                    bone.location=Vector((0,0,0))
                if bone.name.startswith("Thigh_"):
                    bone.rotation_quaternion = Quaternion((1,0,0), math.radians(-18)*swing)
                elif bone.name.startswith("Shin_"):
                    bone.rotation_quaternion = Quaternion((1,0,0), math.radians(45)*max(0,math.cos(phase)*side))
                elif bone.name.startswith("Foot_"):
                    bone.rotation_quaternion = Quaternion((1,0,0), math.radians(18*swing-45*max(0,math.cos(phase)*side)))
                elif not carrying and bone.name.startswith("UpperArm_"):
                    bone.rotation_quaternion = Quaternion((1,0,0), math.radians(22)*swing)
                elif not carrying and bone.name.startswith("Forearm_"):
                    bone.rotation_quaternion = Quaternion((1,0,0), math.radians(-8))
                elif not carrying and bone.name.startswith("Hand_"):
                    bone.rotation_quaternion = Quaternion((1,0,0), 0)
                bone.keyframe_insert(data_path="location",frame=frame)
                bone.keyframe_insert(data_path="rotation_quaternion",frame=frame)
                bone.keyframe_insert(data_path="scale",frame=frame)
            bpy.context.view_layer.update()
            floor = min(rig.pose.bones["Foot_L"].head.z,rig.pose.bones["Foot_R"].head.z)
            torso = rig.pose.bones["Torso"]
            torso.location.y += .12-floor
            torso.keyframe_insert(data_path="location",frame=frame)
    rig.animation_data.action = None
    bpy.context.scene.frame_set(1)

    bpy.ops.object.select_all(action="DESELECT")
    for item in [rig, body] + props:
        item.select_set(True)
    bpy.context.view_layer.objects.active = rig
    actions = [action for action in bpy.data.actions if action.name.startswith(rig_name + "_Rig|")]
    clips = [action.name.split("|")[-1] for action in actions]
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / (output_name + ".fbx")),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_all_actions=True,
        bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0,
        axis_forward="-Z",
        axis_up="Y",
        path_mode="STRIP",
    )
    for item in [rig, body] + props:
        bpy.data.objects.remove(item, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    return clips


bpy.ops.wm.read_factory_settings(use_empty=True)
report = {"customers": []}
for output_name, rig_name, source_name, appearance in VARIANTS:
    mesh, source_vertices = import_mesh(SOURCE / source_name, appearance)
    clips = export_customer(mesh, output_name, rig_name)
    report["customers"].append({
        "name": output_name,
        "source": source_name,
        "rig": rig_name,
        "sourceVertices": source_vertices,
        "vertices": len(mesh.data.vertices),
        "triangles": sum(len(polygon.vertices) - 2 for polygon in mesh.data.polygons),
        "clips": clips,
    })
    bpy.data.objects.remove(mesh, do_unlink=True)
Path(__file__).with_name("report.json").write_text(json.dumps(report, indent=2) + "\n")
print("CUSTOMER_EXPORT_OK", json.dumps(report))
