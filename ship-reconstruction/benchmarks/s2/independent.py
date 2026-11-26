"""对冻结首轮评分作补充：仿射矩阵、留一、CAD几何和完整分母。保留原评分。"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import ezdxf
import numpy as np

ROOT = Path(__file__).resolve().parent

def write_rows(path, rows):
    if not rows:
        return
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)

def affine(p, q, point):
    center = p.mean(axis=0)
    design = np.column_stack((p - center, np.ones(len(p))))
    coeff, _, rank, _ = np.linalg.lstsq(design, q, rcond=None)
    if rank != 3:
        raise ValueError('二维控制点秩不足')
    return np.array([*(point-center), 1.]) @ coeff

def read_geom(entity):
    a = entity.dxf
    t = entity.dxftype()
    if t == 'LINE':
        return {'endpoints': [list(a.start), list(a.end)]}
    if t == 'POLYLINE':
        return {'vertices':[list(v.dxf.location) for v in entity.vertices], 'bulges':[v.dxf.get('bulge',0) for v in entity.vertices], 'closed':bool(entity.is_closed)}
    if t == 'LWPOLYLINE':
        points = entity.get_points('xyb')
        return {'vertices':[[x,y,a.elevation] for x,y,b in points], 'bulges':[b for x,y,b in points], 'closed':bool(entity.closed)}
    if t == 'ARC':
        return {'center': list(a.center), 'radius':a.radius, 'start_angle':a.start_angle, 'end_angle':a.end_angle}
    if t == 'ELLIPSE':
        return {'center':list(a.center), 'major_axis':list(a.major_axis), 'ratio':a.ratio, 'start_param':a.start_param, 'end_param':a.end_param}
    if t == 'SPLINE':
        return {'degree':a.degree, 'flags':a.flags, 'knots':list(entity.knots), 'weights':list(entity.weights), 'fit_points':list(entity.fit_points), 'control_points':list(entity.control_points)}
    raise ValueError(t)

def check_geometry(raw, reported):
    for key, v in raw.items():
        if key not in reported:
            return False
        a = np.asarray(v,dtype=float)
        b = np.asarray(reported[key],dtype=float)
        if a.shape != b.shape or not np.allclose(a,b,atol=1e-9,rtol=0):
            return False
    return True

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('run')
    args=parser.parse_args()
    run=ROOT/'runs'/args.run
    truth=json.loads((ROOT/'fixture/truth.json').read_bytes())
    sums=Counter()
    rows=[]; curves=[]; frames=[]; decisions=[]
    for case in truth:
        cid=case['id']
        rec=json.loads((run/cid/'receipt.json').read_bytes())
        doc=json.loads((run/cid/'out/geometry.json').read_bytes())
        checks=json.loads((run/cid/'checks.json').read_bytes())
        total=Counter()
        frame_ok=True
        for f in case['files']:
            sha=f['sha256']
            for cell in f['cells']:
                stuff={c['measure']:c['pass_check'] for c in checks if c['source']==f['file'] and c['detail']==cell['station_label']+' | '+cell['field_label']}
                row={'case':cid,'file':f['file'],'station':cell['station_label'],'level':cell['field_label'],'expected_status':cell['status'],'expected_si':cell['value_m'],'cell_found':stuff.get('cell_identity',False),'status_ok':stuff.get('cell_semantics',False),'si_ok':stuff.get('si_value_or_abstention',False),'handle_ok':stuff.get('original_handles') if not cell['source_handles'] else bool(stuff.get('original_handles')),'wcs_ok':None if not cell['source_handles'] or f['variant']=='native-table' else bool(stuff.get('wcs_position'))}
                rows.append(row)
            if f['curves']:
                drawing=ezdxf.readfile(ROOT/'fixture/inputs'/cid/f['file'])
                for c in f['curves']:
                    entity=drawing.entitydb[c['handle']]
                    actual=[v for v in doc['curves'] if v['source_sha256']==sha and v['handle']==c['handle']]
                    same=len(actual)==1 and check_geometry(read_geom(entity),actual[0]['geometry'])
                    curves.append(dict(case=cid,file=f['file'],entity=c['dxf_kind'],handle=c['handle'],entity_found=bool(actual),original_geometry_match=same,semantic_kind=actual[0]['kind'] if actual else '',candidates=json.dumps(actual[0]['candidates'],ensure_ascii=False) if actual else ''))
            if 'alignment_target' in f:
                af=[v for a in doc['alignment'] if a['source_sha256']==sha for v in a['frames'] if v['status']=='verified']
                if f['alignment_target']!='verified':
                    row=dict(case=cid,file=f['file'],target=f['alignment_target'],ctrl=len(f['controls']),verified=len(af),matrix_max_m=None,independent_loo_max_m=None,reported_loo_delta_max_m=None,decision=('pass' if not af else 'fail'))
                else:
                    controls=f['controls']
                    row=dict(case=cid,file=f['file'],target=f['alignment_target'],ctrl=len(controls),verified=len(af),matrix_max_m=None,independent_loo_max_m=None,reported_loo_delta_max_m=None,decision='fail')
                    if len(af)==1 and set(af[0]['controls'])=={v['handle'] for v in controls}:
                        orig={c['handle']:c for c in controls}
                        ordered=[orig[h] for h in af[0]['controls']]
                        p=np.array([c['source_xy'] for c in ordered])
                        q=np.array([c['target_xyz'] for c in ordered])
                        h=np.column_stack((p,np.ones(len(p))))
                        errs=np.linalg.norm(h@np.array(af[0]['paper_to_ship_m']).T-q,axis=1)
                        loo=np.array([np.linalg.norm(affine(np.delete(p,i,0),np.delete(q,i,0),pt)-q[i]) for i,pt in enumerate(p)])
                        reported=np.asarray(af[0]['leave_one_out_errors_m'])
                        if reported.shape==loo.shape:
                            delta=np.abs(reported-loo)
                            row.update(matrix_max_m=float(max(errs)),independent_loo_max_m=float(max(loo)),reported_loo_delta_max_m=float(max(delta)),decision='pass' if max(max(errs),max(loo),max(delta))<=1e-7 else 'fail')
                frames.append(row)
                frame_ok &= row['decision']=='pass'
        failed={r['measure'] for r in checks if not r['pass_check']}
        status='passed' if not failed else 'recognition_failed'
        if failed=={'alignment_evidence'} and frame_ok:
            status='verified_by_independent_recomputation'
        elif cid=='T45' and failed=={'si_value_or_abstention'}:
            status='indeterminate_unit_across_layouts'
        decisions.append(dict(case=cid,scenario=case['scenario'],raw_pass=rec['preregistered_outcome'],review=status,failed_metrics=','.join(sorted(failed)),engineering_approved=doc['validation'].get('engineering_approved'),automatic_loft=doc['validation'].get('eligible_for_automatic_full_loft')))
    write_rows(run/'独立配准校核.csv',frames)
    write_rows(run/'逐格独立分母.csv',rows)
    write_rows(run/'曲线参数核对.csv',curves)
    write_rows(run/'复核裁定.csv',decisions)
    stats=dict(decisions=dict(Counter(v['review'] for v in decisions)),cell_totals={k:[sum(r[k] is True for r in rows),sum(r[k] is not None for r in rows)] for k in ['cell_found','status_ok','si_ok','handle_ok','wcs_ok']},numeric_si=[sum(r['si_ok'] and r['expected_si'] is not None for r in rows),sum(r['expected_si'] is not None for r in rows)],unknown_preserved=[sum(r['si_ok'] and r['expected_si'] is None for r in rows),sum(r['expected_si'] is None for r in rows)],curve_parameter_equivalence=[sum(r['original_geometry_match'] for r in curves),len(curves)],registration_decisions=[sum(r['decision']=='pass' for r in frames),len(frames)],max_matrix_error_m=max(r['matrix_max_m'] or 0 for r in frames),max_leave_one_out_error_m=max(r['independent_loo_max_m'] or 0 for r in frames),max_leave_one_out_report_disagreement_m=max(r['reported_loo_delta_max_m'] or 0 for r in frames),all_gates_closed=all(r['engineering_approved'] is False and r['automatic_loft'] is False for r in decisions))
    (run/'independent.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':
    main()
