"""Separate the supplied fused park mesh into rigid ride pivots, preserving its UVs."""
import bpy
import math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'unity/CheckoutSimulator/ArtSource/MapModels/AmusementPark.glb'))
source=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=source
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
mesh=source.data
wheel=Vector((-.086,.323,.338)); tangent=Vector((.81,.586,0));axis=Vector((-.586,.81,0))
carousel=Vector((-.24,-.076,.09))
cabins=[wheel+tangent*(.178*math.cos(a))+Vector((0,0,.178*math.sin(a))) for a in [math.radians(90-i*60) for i in range(6)]]
swings=[Vector((-.080,-.268,.181)),Vector((-.021,-.207,.181))]
groups={}
def classify(p):
 d=p-wheel;u=d.dot(tangent);depth=d.dot(axis)
 if abs(depth)<.115 and abs(u)<.25 and p.z>.14 and (math.hypot(p.x-carousel.x,p.y-carousel.y)>.195 or p.z>.39):return 'ReplaceWheel'
 d=p-carousel;r=math.hypot(d.x,d.y)
 if r<.195 and .104<p.z<.39:
  if .115<p.z<.207 and r>.07:
   return 'Horse_'+str(int((math.atan2(d.y,d.x)+math.pi)/(math.pi/2))%4)
  return 'Carousel'
 for i,c in enumerate(swings):
  q=p-c
  if math.hypot(q.x,q.y)<.031 and -.10<q.z<-.012:return 'Swing_'+str(i)
 return 'Static'
for poly in mesh.polygons:
 center=sum((mesh.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices)
 groups.setdefault(classify(center),[]).append(poly)
def pivot(name,position,parent=None):
 o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o);o.location=position
 if parent:
  bpy.context.view_layer.update();o.parent=parent;o.matrix_parent_inverse=parent.matrix_world.inverted()
 return o
wheel_p=pivot('Ride_Wheel',wheel);carousel_p=pivot('Ride_Carousel',carousel)
pivot('Axis',wheel+axis,wheel_p);pivot('Axis',carousel+Vector((0,0,1)),carousel_p)
for name,polygons in groups.items():
 if name=='ReplaceWheel':continue
 indices=sorted({i for p in polygons for i in p.vertices});remap={v:i for i,v in enumerate(indices)}
 out=bpy.data.meshes.new(name);out.from_pydata([mesh.vertices[i].co for i in indices],[],[[remap[i] for i in p.vertices] for p in polygons]);out.update()
 uv=out.uv_layers.new()
 for dst,src in zip(out.polygons,polygons):
  dst.use_smooth=True
  for dl,sl in zip(dst.loop_indices,src.loop_indices):uv.data[dl].uv=mesh.uv_layers.active.data[sl].uv
 obj=bpy.data.objects.new(name,out);bpy.context.collection.objects.link(obj)
 for material in mesh.materials:out.materials.append(material)
 parent=None
 if name=='Wheel':parent=wheel_p
 elif name=='Carousel':parent=carousel_p
 elif name.startswith('Cabin_'):
  parent=pivot('Ride_'+name,cabins[int(name[-1])],wheel_p)
 elif name.startswith('Horse_'):
  parent=pivot('Ride_'+name,carousel,carousel_p)
 elif name.startswith('Swing_'):
  parent=pivot('Ride_'+name,swings[int(name[-1])]);pivot('Axis',swings[int(name[-1])]+Vector((.64,.77,0)),parent)
 if parent:
  bpy.context.view_layer.update();obj.parent=parent;obj.matrix_parent_inverse=parent.matrix_world.inverted()
 print('RIG_PART',name,len(polygons))
# The supplied wheel and its supports share vertices. Rebuild the moving mechanism
# with closed surfaces so rotations never expose cuts in the fused source shell.
def finish(obj,color,parent=None):
 obj.name='Paint_'+color+'_'+obj.name
 if parent:
  bpy.context.view_layer.update();obj.parent=parent;obj.matrix_parent_inverse=parent.matrix_world.inverted()
 return obj
def bar(a,b,r,color,parent=None):
 a=Vector(a);b=Vector(b);bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=r,depth=(b-a).length,location=(a+b)*.5)
 obj=bpy.context.object;obj.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return finish(obj,color,parent)
def box(pos,size,color,parent=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);obj=bpy.context.object;obj.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bevel=obj.modifiers.new('Soft edges','BEVEL');bevel.width=.005;bevel.segments=3;bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=bevel.name);return finish(obj,color,parent)
deck=box(Vector((wheel.x,wheel.y,.11)),(.29,.17,.055),'D5BF86')
deck.rotation_euler.z=math.atan2(tangent.y,tangent.x)
for side in [-1,1]:
 hub=wheel+axis*.057*side
 for direction in [-1,1]:bar(hub,wheel+tangent*.10*direction+axis*.057*side+Vector((0,0,-.255)),.009,'287D72')
 bar(hub-axis*.012,hub+axis*.012,.019,'E8B94D')
for offset in [-.018,.018]:
 bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=10,location=wheel+axis*offset,major_radius=.178,minor_radius=.007)
 obj=bpy.context.object;obj.rotation_euler=axis.to_track_quat('Z','Y').to_euler();finish(obj,'E8B94D',wheel_p)
 for c in cabins:bar(wheel+axis*offset,c+axis*offset,.005,'E8B94D',wheel_p)
bar(wheel-axis*.033,wheel+axis*.033,.033,'287D72',wheel_p)
for i,c in enumerate(cabins):
 parent=pivot('Ride_Cabin_'+str(i),c,wheel_p);color=['EA8A3A','E9B743','267D71'][i%3]
 center=c-Vector((0,0,.043))
 box(center-Vector((0,0,.013)),(.049,.047,.026),color,parent)
 box(center+Vector((0,0,.025)),(.057,.054,.015),color,parent)
 for dx in [-.020,.020]:
  for dy in [-.019,.019]:bar(center+Vector((dx,dy,-.005)),center+Vector((dx,dy,.026)),.0025,'F1DCA3',parent)
 bar(c,c-Vector((0,0,.012)),.003,'E8B94D',parent)
bpy.data.objects.remove(source,do_unlink=True)
folder=ROOT/'unity/CheckoutSimulator/Assets/Art/Models/MapModels/AmusementPark'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=str(folder/'AmusementParkRig.fbx'),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',bake_anim=False,path_mode='STRIP')
