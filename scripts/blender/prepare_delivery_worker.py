"""Fit the supplied delivery worker to the market rig and author cargo motions.
Run: Blender -b --python scripts/blender/prepare_delivery_worker.py
"""
from pathlib import Path
import json, math, shutil
import bpy
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2] / 'unity/CheckoutSimulator'
OUT = ROOT / 'Assets/Art/Characters/Meshy/Workers'
SOURCE = ROOT / 'ArtSource/MapModels/ConstructionWorker.glb'
supplied = Path.home() / 'Downloads/construction worker 3d model.glb'
if supplied.exists(): shutil.copy2(supplied, SOURCE)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
body = next(o for o in bpy.data.objects if o.type == 'MESH')
bpy.context.view_layer.objects.active = body
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
low = min(v.co.z for v in body.data.vertices)
scale = 2.4 / (max(v.co.z for v in body.data.vertices) - low)
for v in body.data.vertices: v.co = Vector((v.co.x*scale, v.co.y*scale, (v.co.z-low)*scale))
modifier = body.modifiers.new('Mobile mesh', 'DECIMATE')
modifier.ratio = min(1, 24000/len(body.data.polygons))
bpy.ops.object.modifier_apply(modifier=modifier.name)
body.name = 'ConstructionWorkerBody'
material = body.data.materials[0]
image = next(n.image for n in material.node_tree.nodes if n.type=='TEX_IMAGE' and any(l.to_socket.name=='Base Color' for output in n.outputs for l in output.links))
image.filepath_raw = str(OUT / 'Worker_Delivery.png'); image.file_format='PNG'; image.save()
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(ROOT / 'Assets/Art/Characters/Worker_Delivery.fbx'))
imported = set(bpy.data.objects)-before
rig = next(o for o in imported if o.type=='ARMATURE')
rig.animation_data_clear()
for action in list(bpy.data.actions): bpy.data.actions.remove(action)
for o in imported:
    if o != rig: bpy.data.objects.remove(o, do_unlink=True)
# Retain the established hierarchy/axes, fit the relaxed arm pose of this sculpt.
centers = {'Torso':(0,0,1.04), 'Head':(0,0,1.96)}
for side, sign in [('L',-1),('R',1)]:
    for part,x,y,z in [('Thigh',.23,0,1.02),('Shin',.24,.01,.57),('Foot',.25,0,.20),('UpperArm',.36,0,1.76),('Forearm',.47,-.015,1.43),('Hand',.51,-.055,1.13)]: centers[part+'_'+side]=(sign*x,y,z)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for bone in rig.data.edit_bones:
    if bone.name in centers:
        delta=Vector(centers[bone.name])-bone.head; bone.head+=delta; bone.tail+=delta
bpy.ops.object.mode_set(mode='OBJECT')

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for name in centers: body.vertex_groups.new(name=name)
for v in body.data.vertices:
    x,y,z=v.co; side='L' if x<0 else 'R'
    head=smooth(1.91,2.00,z)
    arm=smooth(.30,.40,abs(x))*(1-smooth(1.73,1.89,z))*smooth(.85,1.04,z)
    leg=(1-smooth(.96,1.12,z))*(1-arm)
    weights={'Head':head,'Torso':(1-head)*(1-arm-leg)}
    hand=1-smooth(1.08,1.19,z); forearm=(1-smooth(1.37,1.49,z))*(1-hand)
    for part,value in [('Hand',hand),('Forearm',forearm),('UpperArm',1-hand-forearm)]: weights[part+'_'+side]=(1-head)*arm*value
    foot=1-smooth(.20,.29,z); shin=(1-smooth(.51,.63,z))*(1-foot)
    for part,value in [('Foot',foot),('Shin',shin),('Thigh',1-foot-shin)]: weights[part+'_'+side]=(1-head)*leg*value
    weights=sorted(((n,w) for n,w in weights.items() if w>.001),key=lambda item:-item[1])[:4]
    total=sum(w for _,w in weights)
    for name,weight in weights:body.vertex_groups[name].add([v.index],weight/total,'REPLACE')
body.parent=rig
modifier=body.modifiers.new('Delivery skeleton','ARMATURE');modifier.object=rig
scene=bpy.context.scene;scene.render.fps=30
for bone in rig.pose.bones: bone.rotation_mode='XYZ'

def pose(walk=0,carry=0,bend=0):
    for b in rig.pose.bones: b.location=(0,0,0);b.rotation_euler=(0,0,0);b.scale=(1,1,1)
    torso=rig.pose.bones['Torso']
    # Bone-local Y is vertical in the source FBX.
    torso.location.y=-.43*bend+.025*abs(walk)
    torso.rotation_euler.x=math.radians(48*bend)
    for side,sign in [('L',-1),('R',1)]:
        rig.pose.bones['Thigh_'+side].rotation_euler.x=math.radians(24*walk*sign-48*bend)
        rig.pose.bones['Shin_'+side].rotation_euler.x=math.radians(-max(0,walk*sign)*28)
        rig.pose.bones['Foot_'+side].rotation_euler.x=math.radians(-8*walk*sign)
        rig.pose.bones['UpperArm_'+side].rotation_euler.x=math.radians(-16*carry-18*walk*sign*(1-carry))
        rig.pose.bones['UpperArm_'+side].rotation_euler.z=math.radians(-8*carry*sign)
        rig.pose.bones['Forearm_'+side].rotation_euler.x=math.radians(-68*carry+26*bend)
        rig.pose.bones['Head'].rotation_euler.x=math.radians(-18*bend)
    if bend > 0:
        bpy.context.view_layer.update()
        # Solve both legs against their planted feet while the hips squat.
        for side in ['L','R']:
            thigh,shin,foot=[rig.pose.bones[p+'_'+side] for p in ['Thigh','Shin','Foot']]
            h=thigh.head.copy(); f=Vector(centers['Foot_'+side])
            rest_knee=Vector(centers['Shin_'+side]);rest_hip=Vector(centers['Thigh_'+side])
            upper=(rest_knee-rest_hip).length;lower=(f-rest_knee).length
            direction=(f-h).normalized();distance=(f-h).length
            along=(upper*upper-lower*lower+distance*distance)/(2*distance)
            forward=Vector((0,-1,0));forward=(forward-direction*forward.dot(direction)).normalized()
            knee=h+direction*along+forward*math.sqrt(max(0,upper*upper-along*along))
            for bone,position,rest_vector,posed_vector in [(thigh,h,rest_knee-rest_hip,knee-h),(shin,knee,f-rest_knee,f-knee)]:
                rotation=rest_vector.rotation_difference(posed_vector).to_matrix().to_4x4()
                basis=bone.bone.matrix_local.copy();basis.translation=Vector((0,0,0))
                bone.matrix=Matrix.Translation(position)@rotation@basis
                bpy.context.view_layer.update()
            foot.matrix=foot.bone.matrix_local.copy()
            bpy.context.view_layer.update()

def action(name,frames,fn):
    a=bpy.data.actions.new(name);rig.animation_data_create();rig.animation_data.action=a;a.use_fake_user=True
    for f in range(frames+1):
        fn(f/frames)
        for b in rig.pose.bones:
            b.keyframe_insert(data_path='location',frame=f+1);b.keyframe_insert(data_path='rotation_euler',frame=f+1)
    return a

action('Idle',60,lambda t:pose(walk=.03*math.sin(t*math.tau)))
action('Walking',30,lambda t:pose(walk=math.sin(t*math.tau)))
action('CarryWalking',36,lambda t:pose(walk=math.sin(t*math.tau),carry=1))
action('CarryIdle',60,lambda t:pose(walk=.025*math.sin(t*math.tau),carry=1))
action('Pickup',48,lambda t:pose(carry=smooth(0,.7,t),bend=.22*math.sin(t*math.pi)))
# Reach the floor at 65%; release the box there, then straighten empty-handed.
def putdown(t):
    bend=smooth(0,.65,t) if t<.65 else 1-smooth(.65,1,t)
    pose(carry=1 if t<.65 else 1-smooth(.65,1,t),bend=bend)
action('PutDown',66,putdown)
pose();rig.animation_data.action=None
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'Worker_Delivery.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',path_mode='STRIP')
report={'source':str(SOURCE.relative_to(ROOT)), 'vertices':len(body.data.vertices),'triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'clips':[a.name for a in bpy.data.actions]}
(ROOT/'ArtSource/MapModels/DeliveryWorkerReport.json').write_text(json.dumps(report,indent=2)+'\n')
print('DELIVERY_WORKER_EXPORT_OK',report)
