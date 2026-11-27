"""验收者独立预登记的 S2.1 和 S3 检查；缺证与识别错误分别记录。"""
import math, json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent

def s2(expected, doc):
    checks=[]
    def ck(category, ident, ok, detail):
        checks.append(dict(category=category,object=ident,passed=bool(ok),detail=detail))
    v=doc.get('validation',{})
    ck('研究门禁',expected['case'],v.get('engineering_approved') is False and v.get('eligible_for_automatic_full_loft') is False,'仍需人工批准')
    for f in expected['files']:
        sha=f['sha256'];name=f['file']
        inventory=[a for a in doc.get('inventory',[]) if a.get('source_sha256')==sha]
        ck('原件指纹',name,len(inventory)==1,name)
        cells=[c for t in doc.get('tables',[]) if t.get('source_sha256')==sha for c in t.get('cells',[])]
        for truth in f['cells']:
            actual=[c for c in cells if c.get('station_label')==truth['station_label'] and c.get('field_label')==truth['field_label']]
            if len(actual)!=1:
                ck('单元丢失或不唯一',name+' '+truth['station_label']+'/'+truth['field_label'],False,len(actual));continue
            c=actual[0];status=truth['status'];got=c.get('value_m');want=truth['value_m']
            ok=(got is None) if want is None else isinstance(got,(float,int)) and not isinstance(got,bool) and abs(got-want)<1e-7
            ck('缺证保留' if want is None else '有证型值',name+' '+truth['station_label']+'/'+truth['field_label'],ok and c['status']==status and set(c.get('handles',[]))==set(truth['handles']),dict(status=c.get('status'),si=got))
        observed=[r for r in doc.get('curves',[]) if r.get('source_sha256')==sha]
        for t in f['curves']:
            found=[c for c in observed if c.get('instance')==t['instance'] and c.get('handle')==t['handle']]
            ck('原生曲线实体',name+'/'+t['instance'],len(found)==1 and found[0]['type']==t['source_kind'] and found[0].get('geometry') and found[0].get('samples'),len(found))
            if not found:continue
            curve=found[0]; coords=curve.get('ship_coordinates') or []
            # 有显式控制且全段在见证范围内的线要从实际视图恢复确定船轴。
            got=[x for x in coords if isinstance(x,dict) and x.get('points_m')]
            ok=False
            if got:
                points=np.asarray(got[0]['points_m']); k=0 if t['view']=='YZ' else 2
                ref=t['station_m'] if k==0 else t['level_m']
                fixed=float(np.max(np.abs(points[:,k]-ref)))
                meaningful=points[np.argmax(abs(points[:,1])),1]
                ok=fixed<1e-7 and (meaningful>=-1e-8 if t['side']=='port' else meaningful<=1e-8)
            ck('船轴定值与舷别',name+'/'+t['instance'],ok,{'candidate_records':len(got)})
        frames=[r for a in doc.get('alignment',[]) if a.get('source_sha256')==sha for r in a.get('frames',[]) if r.get('status')=='verified']
        for point in f['controls']:
            fr=[r for r in frames if point['instance'] in r.get('controls',[])]
            err=None
            if len(fr)==1:
                err=float(np.linalg.norm(np.asarray(fr[0]['paper_to_ship_m'])@[*point['paper'],1.]-point['point']))
            ck('控制点回投',name+'/'+point['instance'],err is not None and err<=1e-7,err)
    return checks

def s3(truth,prediction):
    """各预测按独立采样 ID 对齐；输出少一项也判失败，不插补预测。"""
    data=next(g for g in truth if g['case']==prediction['case'])
    checks={}
    def group(key,fields,idkey='id'):
        target=data[key];p=prediction.get(key,[]);lookup={str(r[idkey]):r for r in p}
        if len(lookup)!=len(p) or set(lookup)!={str(r[idkey]) for r in target}:
            return None
        arr=np.array([[abs(lookup[str(r[idkey])][k]-r[k]) for k in fields] for r in target])
        if not np.isfinite(arr).all():return None
        return arr
    h=group('holdout',['y_m']);A=group('areas',['area_m2']);hyd=group('hydro',['volume_m3','waterplane_m2','LCB_m','TCB_m','KB_m','BMt_m'],'draft_m')
    if h is None or A is None or hyd is None:
        return dict(complete=False,passed=False)
    nh=h.ravel()/data['nominal_beam_m']
    checks.update(holdout_rms_fraction=float(np.sqrt(np.mean(nh**2))),holdout_p95_fraction=float(np.quantile(nh,.95)),holdout_max_fraction=float(max(nh)))
    checks['area_l1_fraction']=float(A.sum()/sum(q['area_m2'] for q in data['areas']))
    gt=data['hydro'];checks.update(volume_max_relative=float(max(hyd[:,0]/[r['volume_m3'] for r in gt])),waterplane_max_relative=float(max(hyd[:,1]/[r['waterplane_m2'] for r in gt])),lcb_max_length_fraction=float(max(hyd[:,2])/data['length_m']),tcb_max_error_m=float(max(hyd[:,3])),kb_max_error_m=float(max(hyd[:,4])),bmt_max_error_m=float(max(hyd[:,5])))
    tolerances=dict(holdout_rms_fraction=.012,holdout_p95_fraction=.025,holdout_max_fraction=.05,area_l1_fraction=.025,volume_max_relative=.025,waterplane_max_relative=.03,lcb_max_length_fraction=.012,tcb_max_error_m=.035,kb_max_error_m=.06,bmt_max_error_m=.12)
    return dict(complete=True,passed=all(checks[k]<=v for k,v in tolerances.items()),metrics=checks,tolerances=tolerances)
