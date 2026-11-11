import bpy, json
U="/Users/lucas-furini/repos/checkout/unity/CheckoutSimulator/Assets/Resources/CheckoutEras/"
for n in ["Era4_Spati","Era5_Quitanda","Era6_Minimercado","Era3_Conteiner"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=U+n+".fbx")
    objs=[o for o in bpy.data.objects if o.type=='MESH']
    print("ERA",n,len(objs))
    for o in objs:
        bb=[o.matrix_world@__import__('mathutils').Vector(c) for c in o.bound_box]
        mn=[round(min(v[i] for v in bb),2) for i in range(3)]; mx=[round(max(v[i] for v in bb),2) for i in range(3)]
        print("  ",o.name,len(o.data.polygons),[m.name for m in o.data.materials],mn,mx)
