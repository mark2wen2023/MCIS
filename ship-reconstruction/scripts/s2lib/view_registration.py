"""Rank drawing-based view hypotheses without loading vessel profiles or assigning installation frames."""
from collections import Counter, defaultdict
import itertools
import math
import re
import numpy as np

NUMBER = r'(-?\d+(?:\.\d+)?)'
FAMILIES = {
    'waterline': rf'(?:wl|waterline){NUMBER}|{NUMBER}(?:wl|水线)',
    'buttock': rf'(?:b|buttock){NUMBER}|{NUMBER}剖',
    'frame': rf'(?:fr\.?|frame|肋位|肋号){NUMBER}',
    'station': rf'(?:(?:sta\.?|station|站号|站位))?{NUMBER}',
}
TITLE = {'XY': r'half.?breadth(plan)?|半宽水线图|半宽平面图',
         'XZ': r'profileview|sheerplan|纵剖线图|纵剖面图',
         'YZ': r'bodyplan|横剖线图|横剖面图'}
UNITS = {1:'inch', 2:'foot', 4:'mm', 5:'cm', 6:'m'}


def measure_series(notes, segments):
    """Pair tags with nearby parallel lines and fit a scalar tick axis in native label units."""
    if len({v for _,v in notes}) < 3 or not segments:
        return None
    # Use actual straight CAD lines; tessellated contours do not define graticules.
    a = np.array([s['a'][:2] for s in segments])
    b = np.array([s['b'][:2] for s in segments])
    d = b-a
    length = np.linalg.norm(d,axis=1)
    angles = np.round(np.mod(np.arctan2(d[:,1],d[:,0]), np.pi), 4)
    best = None
    for angle, count in Counter(angles[length>0]).most_common(6):
        if count < 3:
            continue
        tangent = np.array([math.cos(angle),math.sin(angle)])
        u = np.array([-tangent[1],tangent[0]])
        indices = np.flatnonzero((angles==angle)&(length>0))
        lo, hi = np.minimum(a@tangent,b@tangent), np.maximum(a@tangent,b@tangent)
        pos = .5*(a+b)@u
        obs = []
        for t,val in notes:
            h = max(t['height'],1e-8)
            p = np.array(t['p'][:2])
            gap = np.maximum(np.maximum(lo-p@tangent,p@tangent-hi),0)
            off = abs(pos-p@u)
            near = indices[(off[indices]<2.6*h)&(gap[indices]<9*h)&(length[indices]>2*h)]
            if len(near):
                j = near[np.argmin((off+.2*gap)[near])]
                obs.append((val,pos[j],t['instance'],segments[j]['instance']))
        if len(set(v[0] for v in obs)) < 3:
            continue
        # Bound proposal count on crowded sheets, score against all observations.
        probes = obs[::max(1,math.ceil(len(obs)/40))]
        val,pos1 = np.array([x[:2] for x in obs]).T
        increment = np.median(np.diff(np.unique(val)))
        budget = max(1e-6,.015*increment)
        for first,second in itertools.combinations(probes,2):
            dv,dp=second[0]-first[0],second[1]-first[1]
            if not dv or abs(dp)<1e-8:
                continue
            slope = dv/dp
            intercept = first[0]-slope*first[1]
            good = abs(val-slope*pos1-intercept)<=budget
            levels = len(set(val[good]))
            if levels<3 or levels < .65*len(set(val)):
                continue
            score=(levels,-float(np.max(abs(val[good]-slope*pos1[good]-intercept))))
            if best is None or score>best[0]:
                best=(score,dict(paper_to_label=[*(slope*u),intercept],distinct_ticks=levels,
                      ticks=[dict(value=v,label=h,line=l) for (v,_,h,l),ok in zip(obs,good) if ok],
                      max_residual_in_label_units=-score[1]))
    return best[1] if best else None


def inspect(data, inv, frames, axis_records):
    by_layout=defaultdict(list)
    for t in data['texts']:
        by_layout[t['layout']].append(t)
    results=[]
    line_ids={c['instance'] for c in data['curves'] if c.get('type')=='LINE'}
    for layout, texts in by_layout.items():
        families=defaultdict(list); labels=defaultdict(list); unit_notes=[]
        for t in texts:
            s=t['n']
            for key,pat in FAMILIES.items():
                match=re.fullmatch(pat,s)
                if match:
                    families[key].append((t,float(next(x for x in match.groups() if x is not None))))
                    break
            if s in ('cl','centerline','centreline','中心线','中线'): labels['centerline'].append(t['instance'])
            if s in ('bl','baseline','基线'): labels['baseline'].append(t['instance'])
            if re.fullmatch(r'sheer|舷弧线',s): labels['sheer'].append(t['instance'])
            if re.match(r'diag(?:onal)?\.?[a-z]$',s): labels['diagonal'].append(t['instance'])
            for view,pat in TITLE.items():
                if re.fullmatch(pat,s): labels[view].append(t['instance'])
            unit=re.fullmatch(r'(?:units?[:=]?|dimensionsin|单位[:：]?)(mm|cm|m|inches|inch|ft|米|毫米)',s)
            if unit:
                unit_notes.append(dict(unit={'米':'m','毫米':'mm','inches':'inch','ft':'foot'}.get(unit[1],unit[1]),label=t['instance']))
        native=UNITS.get(inv['insertion_units_code'])
        metric_notes=sorted({u['unit'] for u in unit_notes})
        unit_state='conflict' if len(set(metric_notes+([native] if native else [])))>1 else 'printed' if metric_notes else 'header_only' if native else 'unknown'
        segments=[x for x in data['segments'] if x['layout']==layout and x['instance'] in line_ids]
        measured=[f for f in frames if f.get('method')=='measured_grid' and f['layout']==layout]
        series={}
        for family,notes in families.items():
            if family=='station' and not (measured or any(families.get(k) for k in ('waterline','buttock')) or labels.get('diagonal')):
                continue
            axis=measure_series(notes,segments) if not measured else None
            if axis:
                series[family]=axis
        ranked=[]
        for f in measured:
            # Duplicate fits using the same projected axes are a single candidate, not corroboration.
            if any(r['view']==f['view'] and all(np.allclose(a,r['axes_m'][k],rtol=0,atol=1e-7) for k,a in f['axes'].items()) for r in ranked):continue
            rulers={}
            for axis,coef in f['axes'].items():
                matches=[a for a in axis_records if a['layout']==layout and a['axis']==axis and
                         np.allclose(a['coef'],coef,atol=1e-7,rtol=0)]
                if matches:
                    a=max(matches,key=lambda candidate:len(candidate['ticks']))
                    rulers[axis]=dict(scale_basis=a['scale_basis'],ticks=a['ticks'])
            ranked.append(dict(view=f['view'],rulers=rulers,points=6,basis='two_perpendicular_equal_scale_rulers',
                         axes_m=f['axes'],ticks=f['ticks'],bounds=f['paper_bounds'],residual_m=f['max_grid_residual_m'],
                         unknown=f['unresolved']+['confirm_printed_unit_and_datum']))
        def supports(key):return len({v for _,v in families.get(key,[])})>=2
        for view in TITLE:
            if any(r['view']==view for r in ranked):continue
            cues=list(labels.get(view,[]))
            basis=[]
            if cues:basis.append('printed_view_name')
            related={'XY':['waterline'],'XZ':['buttock'],'YZ':['waterline','buttock']}[view]
            if view=='XY':valid='station' in series and supports('waterline') and bool(labels.get('sheer'))
            elif view=='XZ':valid='station' in series and supports('buttock') and not supports('waterline')
            else:valid=supports('waterline') and supports('buttock') and bool(labels.get('centerline'))
            if valid:
                basis.append('station_ruler_and_curve_labels' if view!='YZ' else 'waterline_buttock_and_centerline')
                for k in related:cues.extend(t['instance'] for t,_ in families[k])
                cues.extend(labels.get('sheer' if view=='XY' else 'centerline',[]))
            if basis:
                ranked.append(dict(view=view,points=(3 if valid else 0)+(2 if labels.get(view) else 0),
                                   basis=basis,handles=sorted(set(cues)),axes_m=None,
                                   unknown=['metric_transform','out_of_plane_coordinate','vessel_orientation']))
        ranked.sort(key=lambda r:-r['points'])
        views={c['view'] for c in ranked}
        if 'YZ' not in views:
            # In plan/profile drawings WL/B notes may name hull curves, not scalar rulers.
            for key in ('waterline','buttock'):
                series.pop(key,None)
        elif not measured and 'waterline' in series and 'buttock' in series:
            first,second=(np.array(series[k]['paper_to_label'][:2]) for k in ('waterline','buttock'))
            cosine=abs(first@second)/(np.linalg.norm(first)*np.linalg.norm(second))
            if cosine<.01:
                for candidate in ranked:
                    if candidate['view']=='YZ':
                        candidate['native_axes']={k:series[v]['paper_to_label'] for k,v in [('Y','buttock'),('Z','waterline')]}
                        candidate['points']+=1
                ranked.sort(key=lambda r:-r['points'])
        for r in ranked:
            r['score_kind']='ordinal_evidence_only'
            if unit_state=='conflict':
                r['unknown'].append('conflicting_units')
        results.append(dict(layout=layout,ranked=ranked,series=series,datum_labels=dict(labels),
                      families={k:[dict(label=t['instance'],value=v) for t,v in vs] for k,vs in families.items() if vs},
                      unit=dict(state=unit_state,header=native,printed=unit_notes)))
    return dict(source_sha256=inv['source_sha256'],layouts=results,origin='automatic_cad_only',installation_authorized=False)


def crosscheck(documents):
    from itertools import combinations
    checks=[]
    for a,b in combinations(documents,2):
        for left,right in itertools.product(a['layouts'],b['layouts']):
            for family in left['series'].keys() & right['series'].keys():
                aa,bb=(x['series'][family] for x in (left,right))
                values=sorted({t['value'] for t in aa['ticks']} & {t['value'] for t in bb['ticks']})
                if len(values)<3:continue
                sa,sb=[np.linalg.norm(x['paper_to_label'][:2]) for x in (aa,bb)]
                checks.append(dict(sources=[a['source_sha256'],b['source_sha256']],layouts=[left['layout'],right['layout']],
                     family=family,common_labels=values,paper_scale_ratio=float(sa/sb),
                     equal_paper_pitch=bool(abs(sa/sb-1)<.005),metric_authorization=False))
    for doc in documents:
        for layout in doc['layouts']:
            metric=[r for r in layout['ranked'] if r.get('axes_m')]
            for a,b in combinations(metric,2):
                if a['view']==b['view']:continue
                for k in a['rulers'].keys() & b['rulers'].keys():
                    ar,br=a['rulers'][k],b['rulers'][k]
                    levels=sorted({round(t['value_m'],6) for t in ar['ticks']} & {round(t['value_m'],6) for t in br['ticks']})
                    if len(levels)<3:continue
                    shared={t['line'] for t in ar['ticks']} & {t['line'] for t in br['ticks']}
                    ratio=np.linalg.norm(a['axes_m'][k][:2])/np.linalg.norm(b['axes_m'][k][:2])
                    checks.append(dict(sources=[doc['source_sha256']],views=[a['view'],b['view']],axis=k,
                         common_values_m=levels,paper_scale_ratio=float(ratio),equal_paper_pitch=bool(abs(ratio-1)<.005),
                         reused_line_handles=sorted(shared),metric_authorization=False))
    return checks
