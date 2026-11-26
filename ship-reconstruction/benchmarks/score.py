"""独立只读测量 GLB。用三角面实际船轴坐标而不是导出器自报尺寸。"""
from pathlib import Path
import argparse,csv,json,hashlib
import numpy as np,trimesh
from shapely.geometry import LineString
from shapely.ops import polygonize,unary_union
P=Path(__file__).resolve().parent
LIMIT={'L_rel':.0025,'B_rel':.0075,'D_rel':.0025,'holdout_rms_over_B':.015,
       'section_max_rel':.035,'volume_max_rel':.035,'waterplane_max_rel':.035,'lcb_max_over_L':.01}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def poly(mesh,axis,x):
 n=np.eye(3)[axis];seg=trimesh.intersections.mesh_plane(mesh,n,n*x);p=seg[:,:,np.arange(3)!=axis];lines=[]
 for a,b in np.round(p,9):
  if not np.array_equal(a,b):lines.append(LineString([a,b]))
 polys=list(polygonize(unary_union(lines)))
 if not polys:raise ValueError('切面没有闭合区域')
 return unary_union(polys)
def half_width(mesh,x,z):
 t=mesh.triangles;tri=t[:,:,[0,2]]
 a=tri[:,0];s=tri[:,1]-a;h=tri[:,2]-a;det=s[:,0]*h[:,1]-s[:,1]*h[:,0]
 ok=np.abs(det)>1e-12;s,h,a,det=s[ok],h[ok],a[ok],det[ok];r=np.array([x,z])-a
 u=(r[:,0]*h[:,1]-r[:,1]*h[:,0])/det;v=(s[:,0]*r[:,1]-s[:,1]*r[:,0])/det
 mask=(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)
 if not mask.any():raise ValueError('留出位置缺少几何支撑')
 y=((1-u-v)*t[ok,0,1]+u*t[ok,1,1]+v*t[ok,2,1])[mask]
 return .5*(max(y)-min(y))
def submerged(mesh,d):
 wet=mesh.slice_plane([0,0,d],[0,0,-1],cap=False);t=wet.triangles.copy();origin=np.array([0.,0.,d]);t-=origin
 # 取积分基点在水面上，水平盖面不贡献有符号四面体体积或一阶矩。
 vv=np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2]))/6
 if vv.sum()<=0:raise ValueError('水下净体积非正')
 return float(vv.sum()),float((vv*t[:,:,0].mean(axis=1)*.75).sum()/vv.sum())
def read_mesh(path):
 s=trimesh.load_scene(path,process=False);m=s.to_geometry()
 m.vertices=m.vertices[:,[0,2,1]]*[1,-1,1];m.merge_vertices()
 if not (m.is_watertight and m.is_winding_consistent and m.body_count==1 and m.volume>0):raise ValueError('评分需要单一正体积、封闭、方向一致的船体')
 return m
def assess(mesh,truth):
 L,B,D=[truth[k+'_m'] for k in 'LBD'];r={};e=mesh.extents
 for i,(k,val) in enumerate(zip('LBD',(L,B,D))):r[k+'_rel']=abs(e[i]-val)/val
 h=[{**q,'measured_m':half_width(mesh,q['x_m'],q['z_m'])} for q in truth['held_out']]
 r['holdout_rms_over_B']=np.sqrt(np.mean([(q['measured_m']-q['half_breadth_m'])**2 for q in h]))/B
 sections=[{**q,'measured_m2':poly(mesh,0,q['x_m']).area} for q in truth['sections']]
 r['section_max_rel']=max(abs(q['measured_m2']/q['area_m2']-1) for q in sections)
 hyd=[]
 for q in truth['hydrostatics']:
  v,lc=submerged(mesh,q['draft_m']);hyd.append({**q,'measured_volume_m3':v,'measured_area_m2':poly(mesh,2,q['draft_m']).area,'measured_lcb_m':lc})
 for name,field in [('volume','volume_m3'),('waterplane','area_m2')]:
  r[name+'_max_rel']=max(abs(q['measured_'+field]/q[field]-1) for q in hyd)
 r['lcb_max_over_L']=max(abs(q['measured_lcb_m']-q['lcb_m'])/L for q in hyd)
 return {'metrics':{k:{'error':float(v),'threshold':LIMIT[k],'passed':bool(v<=LIMIT[k])} for k,v in r.items()},'held_out':h,'sections':sections,'hydrostatics':hyd}
def table(path,truth):
 data=json.loads(path.read_bytes());r=data['rows'];target={q['handle']:q for q in truth['table']};matches=0;extras=[];seen=set()
 for row in r:
  key=row.get('handle');q=target.get(key)
  if q and key not in seen and all(abs(float(row[n])-val)<1e-7 for n,val in [('x_m',q['x_m']),('z_m',q['z_m']),('breadth_m',q['value_m'])]):matches+=1;seen.add(key)
  else:extras.append(key)
 return {'expected':len(target),'actual':len(r),'value_station_height_handle_matches':matches,'extra_or_incorrect_handles':extras,'all_match':len(target)==len(r)==matches}
def selfcheck():
 m=trimesh.creation.box(extents=[4,2,2]);m.apply_translation([2,0,1])
 t={'L_m':4,'B_m':2,'D_m':2,'held_out':[{'x_m':.891,'z_m':.619,'half_breadth_m':1}], 'sections':[{'x_m':.879,'area_m2':4}], 'hydrostatics':[{'draft_m':.713,'volume_m3':8*.713,'area_m2':8,'lcb_m':2}]}
 a=assess(m,t);assert all(x['error']<1e-11 for x in a['metrics'].values());return a
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--case');p.add_argument('--glb',type=Path);p.add_argument('--offsets',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--control',action='store_true');a=p.parse_args()
 if a.control:result=selfcheck()
 else:
  t=json.loads((P/'truth'/(a.case+'.json')).read_text());result=assess(read_mesh(a.glb),t);result['offsets']=table(a.offsets,t);result['geometry_sha256']=sha(a.glb)
 a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
