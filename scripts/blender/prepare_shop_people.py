from pathlib import Path
import bpy,math,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]/'unity/CheckoutSimulator'
for name in ['CheckoutWoman','GirlCustomer']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(ROOT/'ArtSource/MapModels'/f'{name}.glb'))
 body=next(o for o in bpy.data.objects if o.type=='MESH');bpy.context.view_layer.objects.active=body
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 low=min(v.co.z for v in body.data.vertices);scale=2.4/(max(v.co.z for v in body.data.vertices)-low)
 for v in body.data.vertices:v.co=Vector((v.co.x*scale,v.co.y*scale,(v.co.z-low)*scale))
 mod=body.modifiers.new('Mobile mesh','DECIMATE');mod.ratio=min(1,24000/len(body.data.polygons));bpy.ops.object.modifier_apply(modifier=mod.name);body.name=name+'Body'
 before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(ROOT/'Assets/Art/Characters/Worker_Delivery.fbx'));imported=set(bpy.data.objects)-before;rig=next(o for o in imported if o.type=='ARMATURE');rig.animation_data_clear()
 for a in list(bpy.data.actions):bpy.data.actions.remove(a)
 for o in imported:
  if o!=rig:bpy.data.objects.remove(o,do_unlink=True)
 centers={'Torso':(0,0,1.05),'Head':(0,0,1.80)}
 for side,sign in [('L',-1),('R',1)]:
  for part,x,y,z in [('Thigh',.22,0,1.02),('Shin',.23,0,.56),('Foot',.23,-.04,.16),('UpperArm',.36,0,1.62),('Forearm',.47,-.01,1.32),('Hand',.57,-.04,1.02)]:centers[part+'_'+side]=(sign*x,y,z)
 bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
 for bone in rig.data.edit_bones:
  if bone.name in centers:delta=Vector(centers[bone.name])-bone.head;bone.head+=delta;bone.tail+=delta
 bpy.ops.object.mode_set(mode='OBJECT')
 def smooth(a,b,x):
  t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
 for n in centers:body.vertex_groups.new(name=n)
 for v in body.data.vertices:
  x,y,z=v.co;side='L' if x<0 else 'R';head=smooth(1.76,1.88,z);arm=smooth(.30,.41,abs(x))*(1-smooth(1.62,1.78,z))*smooth(.85,1,z);leg=(1-smooth(.94,1.08,z))*(1-arm)
  weights={'Head':head,'Torso':(1-head)*(1-arm-leg)};hand=1-smooth(1.04,1.15,z);fore=(1-smooth(1.28,1.40,z))*(1-hand)
  for part,val in [('Hand',hand),('Forearm',fore),('UpperArm',1-hand-fore)]:weights[part+'_'+side]=(1-head)*arm*val
  foot=1-smooth(.18,.27,z);shin=(1-smooth(.5,.61,z))*(1-foot)
  for part,val in [('Foot',foot),('Shin',shin),('Thigh',1-foot-shin)]:weights[part+'_'+side]=(1-head)*leg*val
  weights=sorted(((n,w) for n,w in weights.items() if w>.001),key=lambda a:-a[1])[:4];total=sum(w for n,w in weights)
  for n,w in weights:body.vertex_groups[n].add([v.index],w/total,'REPLACE')
 body.parent=rig;mod=body.modifiers.new('Character skeleton','ARMATURE');mod.object=rig
 for b in rig.pose.bones:b.rotation_mode='XYZ'
 def pose(walk=0,reach=0,scan=0,pay=0):
  for b in rig.pose.bones:b.location=(0,0,0);b.rotation_euler=(0,0,0);b.scale=(1,1,1)
  rig.pose.bones['Torso'].location.y=.018*abs(walk)
  for side,sign in [('L',-1),('R',1)]:
   rig.pose.bones['Thigh_'+side].rotation_euler.x=math.radians(21*walk*sign);rig.pose.bones['Shin_'+side].rotation_euler.x=math.radians(-max(0,walk*sign)*24)
   rig.pose.bones['UpperArm_'+side].rotation_euler.x=math.radians(-14*walk*sign-32*reach-20*pay)
   rig.pose.bones['Forearm_'+side].rotation_euler.x=math.radians(-42*reach-45*pay)
   rig.pose.bones['UpperArm_'+side].rotation_euler.z=math.radians(scan*18*sign)
  rig.pose.bones['Head'].rotation_euler.x=math.radians(6*reach+7*pay)
 def action(n,frames,fn):
  a=bpy.data.actions.new(n);a.use_fake_user=True;rig.animation_data_create();rig.animation_data.action=a
  for f in range(frames+1):
   fn(f/frames)
   for b in rig.pose.bones:b.keyframe_insert(data_path='location',frame=f+1);b.keyframe_insert(data_path='rotation_euler',frame=f+1)
 bpy.context.scene.render.fps=30
 def idle(t):
  pose(reach=.32 if name=='CheckoutWoman' else 0)
  rig.pose.bones['Torso'].location.y=.015*math.sin(t*math.tau)
  rig.pose.bones['Torso'].rotation_euler.z=math.radians(2.5*math.sin(t*math.tau))
  rig.pose.bones['Head'].rotation_euler.y=math.radians(10*math.sin(t*math.tau))
  rig.pose.bones['Head'].rotation_euler.x=math.radians(5+4*math.sin(t*math.tau*2))
  if name=='CheckoutWoman':
   rig.pose.bones['Forearm_R'].rotation_euler.x=math.radians(-35-12*math.sin(t*math.tau*2))
   rig.pose.bones['Hand_R'].rotation_euler.x=math.radians(8*math.sin(t*math.tau*4))
 action('Idle',120,idle)
 action('Walking',30,lambda t:pose(walk=math.sin(t*math.tau)))
 action('GetFromShelf',60,lambda t:pose(reach=math.sin(math.pi*t)))
 action('BuyAtSpecialSector',60,lambda t:pose(reach=.6*math.sin(math.pi*t)))
 action('PayAtCheckout',60,lambda t:pose(pay=math.sin(math.pi*t)))
 action('ScanItems',90,lambda t:pose(reach=.35+.6*math.sin(math.pi*t),scan=math.sin(t*math.tau)*.9))
 action('ReceivePayment',60,lambda t:pose(reach=.25,pay=math.sin(math.pi*t)))
 pose();rig.animation_data.action=None;bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
 out=ROOT/'Assets/Art/Models/MapModels'/name/f'{name}Animated.fbx'
 bpy.ops.export_scene.fbx(filepath=str(out),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',path_mode='STRIP')
 print('SHOP_PERSON_OK',name,flush=True)
