"""冻结的 S2 验收语义。来源、单元、几何实体和配准独立计分。"""
import json,math,re
from pathlib import Path
def strings(value):
 if isinstance(value,str):return [value]
 if isinstance(value,list):return sum((strings(x) for x in value),[])
 if isinstance(value,dict):return sum((strings(v) for v in value.values()),[])
 return []
def eq(x,y,tol=1e-7):
 return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and abs(x-y)<=tol
def flatten(x):
 if isinstance(x,(int,float)) and not isinstance(x,bool):return [float(x)]
 if isinstance(x,list):return sum((flatten(v) for v in x),[])
 if isinstance(x,dict):return [float(x[k]) for k in ('x','y','z') if isinstance(x.get(k),(int,float))]
 return []
def results(case,doc):
 checks=[]
 def ck(which,expected,actual,passed,source,detail=''):
  checks.append(dict(measure=which,expected=expected,observed=actual,pass_check=bool(passed),source=source,detail=detail))
 if not isinstance(doc,dict):
  ck('complete_output','geometry.json',None,False,case['id']);return checks
 for f in case['files']:
  sh=f['sha256'];fid=f['file']
  def mine(section):return [a for a in doc.get(section,[]) if a.get('source_sha256',a.get('sha256'))==sh]
  inv=mine('inventory');ck('file_fingerprint',1,len(inv),len(inv)==1,fid)
  classes=set(strings([x.get('classes',[]) for x in inv]));expected=set(f['expected_classes']);ck('class_attribution',sorted(expected),sorted(classes),expected<=classes,fid)
  tables=mine('tables');cells=[c for t in tables for c in t.get('cells',[])]
  if f['cells']:
   ck('registered_table',True,len(tables),bool(tables),fid)
   if f['variant']=='two-tables':ck('separate_table_regions',2,len(tables),len(tables)==2,fid)
   for v in f['cells']:
    # 表头原文或其同意的带量纲坐标均能定位；数字实体仍需原句柄和坐标核验。
    def matches(c):
     a=c.get('station_label')==v['station_label'] or eq(c.get('station_m'),v['station_m'])
     b=c.get('field_label')==v['field_label'] or eq(c.get('level_m'),v['level_m'])
     return a and b
    cc=[c for c in cells if matches(c)];detail=v['station_label']+' | '+v['field_label'];ck('cell_identity',1,len(cc),len(cc)==1,fid,detail)
    if len(cc)!=1:continue
    c=cc[0];obs=c.get('status');target=v['status'];statuses={target}
    if target=='non_numeric':statuses.update({'blank_unknown','boundary_ambiguous'})
    if target=='merged_unknown':statuses.update({'boundary_ambiguous'})
    ck('cell_semantics',sorted(statuses),obs,obs in statuses,fid,detail)
    if v['value_m'] is None:ok=c.get('value_m') is None
    else:ok=eq(c.get('value_m'),v['value_m'])
    ck('si_value_or_abstention',v['value_m'],c.get('value_m'),ok,fid,detail)
    if v['source_handles']:
     ids=set(strings(c.get('handles',[])));ck('original_handles',v['source_handles'],sorted(ids),set(v['source_handles'])<=ids,fid,detail)
     if f['variant']!='native-table':
      xy=c.get('source_wcs');pts=([xy] if isinstance(xy,(dict,list)) and len(flatten(xy)) in (2,3) else xy) if xy is not None else []
      if isinstance(pts,dict):pts=list(pts.values())
      ds=[math.dist(a[:2],v['source_xy']) for p in pts if len(a:=flatten(p))>=2]
      ck('wcs_position','≤1e-5 drawing unit',min(ds) if ds else None,bool(ds) and min(ds)<1e-5,fid,detail)
  for c in f['curves']:
   got=[r for r in mine('curves') if r.get('handle')==c['handle']]
   ck('curve_handle_and_source',c['handle'],len(got),len(got)==1,fid)
   if len(got)==1:
    ck('curve_geometry',True,got[0].get('kind'),bool(got[0].get('geometry')),fid,c['handle'])
  if 'alignment_target' in f:
   af=mine('alignment');frames=[r for row in af for r in row.get('frames',[])];verified=[r for r in frames if r.get('status')=='verified']
   target=f['alignment_target'];ck('qualified_alignment',target,[r.get('status') for r in frames],bool(af) and (bool(verified) if target=='verified' else not verified),fid)
   # 正例要求确证控制点、留出和残差，不能只挂 verified 字符串。
   if target=='verified' and verified:
    text=json.dumps(verified,ensure_ascii=False).lower();ck('alignment_evidence','control and residual/holdout',None,('control' in text or '控制' in text) and any(v in text for v in ('residual','holdout','留出','误差')),fid)
 return checks
