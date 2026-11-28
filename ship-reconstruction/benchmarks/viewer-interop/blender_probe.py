"""Import the exact GLB and apply sampled local rotations in Blender's coordinate convention."""
import csv
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Quaternion, Vector
source, dest = map(Path,sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source/'assembly.glb'))
tracks={t['node']:t for t in json.loads((source/'assembly.json').read_text())['tracks']}
oracle=json.loads((source/'oracle.json').read_text())
data=[]
for row in oracle['cases']:
    probe=bpy.data.objects[row['node']]
    node=probe.parent
    tr=tracks[node.name]
    q=(row['angle']-tr['min'])/(tr['max']-tr['min'])*(len(tr['rotations'])-1)
    k=math.floor(q)
    def quat(i):
        v=tr['rotations'][i]
        return Quaternion([v['w'],v['x'],-v['z'],v['y']])
    node.rotation_mode='QUATERNION'
    node.rotation_quaternion=quat(k).slerp(quat(min(k+1,len(tr['rotations'])-1)),q-k)
    bpy.context.view_layer.update()
    p=probe.matrix_world.translation
    error=(p-Vector((row['x'],-row['z'],row['y']))).length
    data.append([row['node'],row['angle'],*p,error])
with dest.open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['node','angle_deg','blender_x','blender_y','blender_z','error_m']);w.writerows(data)
assert len(data)==len(oracle['cases']) and max(r[-1] for r in data)<=oracle['tolerance_m']
print('BLENDER WORLD PASS',len(data),bpy.app.version_string)
