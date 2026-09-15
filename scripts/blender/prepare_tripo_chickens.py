import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) != 4:
        raise SystemExit(
            "Usage: blender --background --python prepare_tripo_chickens.py -- "
            "<input.fbx> <output_dir> <asset_name> <preview_dir>"
        )
    return Path(args[0]).resolve(), Path(args[1]).resolve(), args[2], Path(args[3]).resolve()


def reset_pose(armature):
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)


def key_pose(armature, frame, transforms):
    reset_pose(armature)
    for bone_name, transform in transforms.items():
        pose_bone = armature.pose.bones.get(bone_name)
        if pose_bone is None:
            continue
        if "location" in transform:
            pose_bone.location = transform["location"]
        if "rotation" in transform:
            pose_bone.rotation_euler = tuple(
                math.radians(value) for value in transform["rotation"]
            )
        if "scale" in transform:
            pose_bone.scale = transform["scale"]
        pose_bone.keyframe_insert(data_path="location", frame=frame)
        pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame)
        pose_bone.keyframe_insert(data_path="scale", frame=frame)


def build_action(armature, name, end_frame, keyframes):
    action = bpy.data.actions.new(name=name)
    action.use_fake_user = True
    armature.animation_data.action = action
    for frame, transforms in keyframes:
        key_pose(armature, frame, transforms)

    return action


def create_actions(armature):
    root = "tripo::Root"
    spine = "tripo::Spine_0"
    is_brown_rig = armature.pose.bones.get("tripo::Head_3") is not None
    if is_brown_rig:
        neck = "bone_2"
        neck_top = "tripo::Head_0"
        head = "tripo::Head_1"
        head_tip = "tripo::Head_2"
    else:
        neck = "bone_11"
        neck_top = "bone_12"
        head = "tripo::Head_0"
        head_tip = "tripo::Head_1"
    left_upper = "tripo::0_Left_Limb_0"
    left_lower = "tripo::0_Left_Limb_1"
    right_upper = "tripo::0_Right_Limb_0"
    right_lower = "tripo::0_Right_Limb_1"
    if is_brown_rig:
        eat_neck_pitch = 2.1
        eat_neck_top_pitch = -0.15
        eat_head_pitch = -0.2
        eat_head_tip_pitch = 0.0
    else:
        eat_neck_pitch = 1.0
        eat_neck_top_pitch = 1.0
        eat_head_pitch = 1.0
        eat_head_tip_pitch = 1.0

    idle = build_action(
        armature,
        "Idle",
        49,
        [
            (1, {root: {"location": (0, 0, 0)}, head: {"rotation": (0, 0, -2)}}),
            (
                13,
                {
                    root: {"location": (0, 0, 0.010)},
                    spine: {"rotation": (0, 0, 1.2)},
                    head: {"rotation": (1.8, 0, 2.5)},
                    head_tip: {"rotation": (-1.0, 0, 1.5)},
                },
            ),
            (25, {root: {"location": (0, 0, 0)}, head: {"rotation": (0, 0, -2)}}),
            (
                37,
                {
                    root: {"location": (0, 0, -0.004)},
                    spine: {"rotation": (0, 0, -1.0)},
                    head: {"rotation": (-1.2, 0, -3.0)},
                    head_tip: {"rotation": (0.8, 0, -1.0)},
                },
            ),
            (49, {root: {"location": (0, 0, 0)}, head: {"rotation": (0, 0, -2)}}),
        ],
    )

    walk = build_action(
        armature,
        "Walk",
        25,
        [
            (
                1,
                {
                    root: {"location": (0, 0, 0)},
                    spine: {"rotation": (0, 0, -2.5)},
                    left_upper: {"rotation": (24, 0, 0)},
                    left_lower: {"rotation": (-14, 0, 0)},
                    right_upper: {"rotation": (-24, 0, 0)},
                    right_lower: {"rotation": (12, 0, 0)},
                    head: {"rotation": (-2, 0, 2)},
                },
            ),
            (
                7,
                {
                    root: {"location": (0, 0, 0.018)},
                    left_upper: {"rotation": (0, 0, 0)},
                    left_lower: {"rotation": (8, 0, 0)},
                    right_upper: {"rotation": (0, 0, 0)},
                    right_lower: {"rotation": (-8, 0, 0)},
                    head: {"rotation": (2.5, 0, 0)},
                },
            ),
            (
                13,
                {
                    root: {"location": (0, 0, 0)},
                    spine: {"rotation": (0, 0, 2.5)},
                    left_upper: {"rotation": (-24, 0, 0)},
                    left_lower: {"rotation": (12, 0, 0)},
                    right_upper: {"rotation": (24, 0, 0)},
                    right_lower: {"rotation": (-14, 0, 0)},
                    head: {"rotation": (-2, 0, -2)},
                },
            ),
            (
                19,
                {
                    root: {"location": (0, 0, 0.018)},
                    left_upper: {"rotation": (0, 0, 0)},
                    left_lower: {"rotation": (-8, 0, 0)},
                    right_upper: {"rotation": (0, 0, 0)},
                    right_lower: {"rotation": (8, 0, 0)},
                    head: {"rotation": (2.5, 0, 0)},
                },
            ),
            (
                25,
                {
                    root: {"location": (0, 0, 0)},
                    spine: {"rotation": (0, 0, -2.5)},
                    left_upper: {"rotation": (24, 0, 0)},
                    left_lower: {"rotation": (-14, 0, 0)},
                    right_upper: {"rotation": (-24, 0, 0)},
                    right_lower: {"rotation": (12, 0, 0)},
                    head: {"rotation": (-2, 0, 2)},
                },
            ),
        ],
    )

    eat = build_action(
        armature,
        "Eat",
        49,
        [
            (1, {root: {"location": (0, 0, 0)}, head: {"rotation": (0, 0, 0)}}),
            (
                9,
                {
                    root: {"location": (0, 0, -0.012)},
                    spine: {"rotation": (-5, 0, 0)},
                    neck: {"rotation": (-18 * eat_neck_pitch, 0, 0)},
                    neck_top: {"rotation": (-24 * eat_neck_top_pitch, 0, 0)},
                    head: {"rotation": (-30 * eat_head_pitch, 0, 0)},
                    head_tip: {"rotation": (-12 * eat_head_tip_pitch, 0, 0)},
                },
            ),
            (
                17,
                {
                    root: {"location": (0, -0.015, -0.025)},
                    spine: {"rotation": (-8, 0, 0)},
                    neck: {"rotation": (-26 * eat_neck_pitch, 0, 0)},
                    neck_top: {"rotation": (-36 * eat_neck_top_pitch, 0, 0)},
                    head: {"rotation": (-44 * eat_head_pitch, 0, 0)},
                    head_tip: {"rotation": (-18 * eat_head_tip_pitch, 0, 0)},
                },
            ),
            (
                25,
                {
                    root: {"location": (0, 0, -0.010)},
                    spine: {"rotation": (-4, 0, 0)},
                    neck: {"rotation": (-14 * eat_neck_pitch, 0, 0)},
                    neck_top: {"rotation": (-20 * eat_neck_top_pitch, 0, 0)},
                    head: {"rotation": (-22 * eat_head_pitch, 0, 2)},
                },
            ),
            (
                33,
                {
                    root: {"location": (0, -0.012, -0.024)},
                    spine: {"rotation": (-7, 0, 0)},
                    neck: {"rotation": (-24 * eat_neck_pitch, 0, 0)},
                    neck_top: {"rotation": (-34 * eat_neck_top_pitch, 0, 0)},
                    head: {"rotation": (-42 * eat_head_pitch, 0, -2)},
                    head_tip: {"rotation": (-16 * eat_head_tip_pitch, 0, 0)},
                },
            ),
            (
                41,
                {
                    root: {"location": (0, 0, -0.006)},
                    neck: {"rotation": (-8 * eat_neck_pitch, 0, 0)},
                    neck_top: {"rotation": (-10 * eat_neck_top_pitch, 0, 0)},
                    head: {"rotation": (-8 * eat_head_pitch, 0, 0)},
                },
            ),
            (49, {root: {"location": (0, 0, 0)}, head: {"rotation": (0, 0, 0)}}),
        ],
    )

    armature.animation_data.action = None
    reset_pose(armature)
    return {"Idle": idle, "Walk": walk, "Eat": eat}


def point_camera(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_previews(armature, actions, preview_dir, asset_name):
    preview_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.105))
    floor = bpy.context.object
    floor.name = "PreviewFloor"
    floor_material = bpy.data.materials.new("PreviewFloorMaterial")
    floor_material.diffuse_color = (0.14, 0.17, 0.18, 1.0)
    floor.data.materials.append(floor_material)

    bpy.ops.object.camera_add(location=(1.75, -3.6, 1.35))
    camera = bpy.context.object
    camera.data.lens = 58
    point_camera(camera, (0.0, 0.0, 0.48))
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(-2.2, -2.4, 3.2))
    key_light = bpy.context.object
    key_light.data.energy = 950
    key_light.data.shape = "DISK"
    key_light.data.size = 4.0
    point_camera(key_light, (0.0, 0.0, 0.45))

    bpy.ops.object.light_add(type="AREA", location=(2.5, 1.0, 2.0))
    fill_light = bpy.context.object
    fill_light.data.energy = 550
    fill_light.data.size = 3.0
    point_camera(fill_light, (0.0, 0.0, 0.5))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("PreviewWorld")
    scene.world.color = (0.035, 0.045, 0.055)

    samples = {"Idle": 13, "Walk": 1, "Eat": 17}
    for action_name, frame in samples.items():
        armature.animation_data.action = actions[action_name]
        scene.frame_set(frame)
        scene.render.filepath = str(preview_dir / f"{asset_name}-{action_name.lower()}.png")
        bpy.ops.render.render(write_still=True)

    armature.animation_data.action = None
    bpy.data.objects.remove(floor, do_unlink=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.objects.remove(key_light, do_unlink=True)
    bpy.data.objects.remove(fill_light, do_unlink=True)


def copy_textures(input_fbx, output_dir):
    source_dir = input_fbx.with_suffix(".fbm")
    target_dir = output_dir / "Textures"
    target_dir.mkdir(parents=True, exist_ok=True)
    if not source_dir.exists():
        return

    for source_path in source_dir.iterdir():
        if source_path.is_file():
            shutil.copy2(source_path, target_dir / source_path.name)

    for image in bpy.data.images:
        if not image.filepath:
            continue
        candidate = target_dir / Path(bpy.path.abspath(image.filepath)).name
        if candidate.exists():
            image.filepath = str(candidate)


def prepare_asset(input_fbx, output_dir, asset_name, preview_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(input_fbx), automatic_bone_orientation=False)

    armature = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
    armature.name = f"{asset_name}_Armature"
    armature.data.name = f"{asset_name}_Skeleton"
    armature.animation_data_create()

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    for index, mesh in enumerate(meshes):
        mesh.name = asset_name if index == 0 else f"{asset_name}_{index + 1}"
        mesh.data.name = f"{mesh.name}_Mesh"

    actions = create_actions(armature)
    render_previews(armature, actions, preview_dir, asset_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    copy_textures(input_fbx, output_dir)

    fbx_path = output_dir / f"{asset_name}.fbx"
    blend_dir = preview_dir.parent / "Blender"
    glb_dir = preview_dir.parent / "GLB"
    blend_dir.mkdir(parents=True, exist_ok=True)
    glb_dir.mkdir(parents=True, exist_ok=True)
    blend_path = blend_dir / f"{asset_name}.blend"
    glb_path = glb_dir / f"{asset_name}.glb"

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 49
    bpy.context.scene.render.fps = 24
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=False,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_all_actions=True,
        bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0.0,
        path_mode="COPY",
        embed_textures=False,
    )

    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        export_skins=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_frame_range=False,
    )

    print(
        f"Prepared {asset_name}: {len(meshes)} mesh(es), "
        f"{len(armature.data.bones)} bones, actions={list(actions)}"
    )


if __name__ == "__main__":
    prepare_asset(*parse_args())
