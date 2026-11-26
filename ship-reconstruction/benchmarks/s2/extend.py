from pathlib import Path
import hashlib,json,ezdxf
from generate import P,save,sha
def extend(base):
 lookup=json.loads((base/'truth.json').read_text())
 extra=['three-views','four-controls','three-controls','translated-control','skewed-control','mixed-control-points','ellipse-spline','arc-polyline']
 for i,case in enumerate(extra,47):
  dest=base/'inputs'/f'T{i:02}';dest.mkdir();files=[]
  for axis in (['profile','plan','section'] if case=='three-views' else ['profile']):
   d=ezdxf.new('R2013');d.units=4;s=d.modelspace()
   def txt(t,pt):return s.add_text(t,dxfattribs={'height':1.6,'insert':pt}).dxf.handle
   typ='section' if axis=='section' else 'lines';txt({'profile':'LINES PLAN / PROFILE VIEW / 型线图','plan':'WATERLINE PLAN / 型线图','section':'BODY PLAN / 横剖面图'}[axis],(0,100))
   r={'variant':case,'expected_classes':[typ],'cells':[],'curves':[],'controls':[]}
   if case in ('ellipse-spline','arc-polyline'):
    if case=='ellipse-spline':
     entities=[s.add_ellipse((22,12),(8,0),.4),s.add_spline(fit_points=[(1,1),(6,4),(19,9),(28,2)])]
    else:entities=[s.add_arc((8,5),5,11,134),s.add_lwpolyline([(14,4,.33),(19,10,0),(28,12,0)],format='xyb')]
    for e in entities:r['curves'].append({'handle':e.dxf.handle,'dxf_kind':e.dxftype()})
   else:
    points=[(0,0),(3,0),(0,2),(3,4),(1,5),(6,2)];points=points[:3] if case=='three-controls' else points[:4] if case=='four-controls' else points
    for j,(u,v) in enumerate(points):
     xyz={'profile':[u,0,v],'plan':[u,v,0],'section':[4,u,v]}[axis];x=1.9*u-.4*v+14;y=.1*u+1.7*v+3
     if case=='translated-control':x+=582100.;y-=315760.
     if case=='skewed-control':x-=1.4*v
     if case=='mixed-control-points' and j==3:xyz[0]+=26
     h=txt(f'CONTROL G{j} X={xyz[0]} Y={xyz[1]} Z={xyz[2]} m',(x,y));r['controls'].append({'id':f'G{j}','source_xy':[x,y],'target_xyz':xyz,'handle':h})
    s.add_line((14,3),(45,21));r['alignment_target']='no_verified' if case in ('three-controls','mixed-control-points') else 'verified'
   path=dest/(axis+'.dxf');d.saveas(path);assert not ezdxf.readfile(path).audit().errors;r['file']=path.name;r['sha256']=sha(path);files.append(r)
  lookup.append({'id':f'T{i:02}','scenario':case,'files':files})
 save(base/'truth.json',lookup)
if __name__=='__main__':extend(P/'fixture')
