"""Rank drawing-based view hypotheses without loading vessel profiles or assigning installation frames."""
from collections import Counter, defaultdict
import hashlib
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


def _inspect_registration(data, inv, frames, axis_records):
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


def _bounds(points):
    a=np.asarray(points,dtype=float)
    if a.ndim!=2 or len(a)==0:return None
    a=a[:,:2]
    return [float(a[:,0].min()),float(a[:,1].min()),float(a[:,0].max()),float(a[:,1].max())]


def _gap(a,b):
    return math.hypot(max(0.0,a[0]-b[2],b[0]-a[2]),max(0.0,a[1]-b[3],b[1]-a[3]))


def _overlap(a,b):
    return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]


def _spatial_entities(data):
    """Build deterministic per-instance boxes from S2's existing CAD extraction."""
    rows={}
    def row(layout,instance,kind,points,record):
        box=_bounds(points)
        if box is None:return
        key=(layout,instance)
        if key not in rows:
            rows[key]=dict(layout=layout,instance=instance,types=set(),boxes=[],records=[])
        rows[key]['types'].add(kind);rows[key]['boxes'].append(box);rows[key]['records'].append(record)
    for c in data.get('curves',[]):
        row(c['layout'],c['instance'],c.get('type','curve'),c.get('samples',[]),c)
    for t in data.get('texts',[]):
        h=max(float(t.get('height',0)),1e-9);p=np.asarray(t['p'][:2],dtype=float)
        u=np.asarray(t.get('baseline',[1,0,0])[:2],dtype=float);n=np.linalg.norm(u)
        u=u/n if n else np.array([1.,0.]);v=np.array([-u[1],u[0]])
        # Text width is not exposed by the read adapter (and MTEXT can be long).
        # Index the insertion anchor only, so a title cannot inflate a view box.
        w=.35*h
        pts=[p+u*x*h+v*y*h for x,y in ((-.2,-.2),(w,-.2),(w,.35),(-.2,.35))]
        row(t['layout'],t['instance'],'TEXT',pts,t)
    for leader in data.get('leaders',[]):
        row(leader['layout'],leader['instance'],'LEADER',leader.get('vertices',[]),leader)
    for arrow in data.get('arrowheads',[]):
        row(arrow['layout'],arrow['instance'],'ARROW',arrow.get('vertices',[]),arrow)
    for table in data.get('native',[]):
        row(table['layout'],table['instance'],'TABLE',[table.get('insertion_wcs',[0,0,0])],table)
    for r in rows.values():
        r['bounds']=[min(b[0] for b in r['boxes']),min(b[1] for b in r['boxes']),
                     max(b[2] for b in r['boxes']),max(b[3] for b in r['boxes'])]
        r['types']=sorted(r['types'])
    return rows


def _components(points, radius):
    """Spatial-hash connected components; no optional spatial-index package."""
    if not points:return []
    cell=max(radius,1e-12); buckets=defaultdict(list);parent=list(range(len(points)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,p in enumerate(points):
        ix,iy=math.floor(p[0]/cell),math.floor(p[1]/cell)
        for x in range(ix-1,ix+2):
            for y in range(iy-1,iy+2):
                for j in buckets[(x,y)]:
                    q=points[j]
                    if math.hypot(p[0]-q[0],p[1]-q[1])<=radius:
                        a,b=find(i),find(j)
                        if a!=b:parent[a]=b
        buckets[(ix,iy)].append(i)
    groups=defaultdict(list)
    for i in range(len(points)):groups[find(i)].append(i)
    return list(groups.values())


def _bbox_components(boxes, radius):
    """Sweep-line spatial index over entity boxes, excluding no CAD handles."""
    parent=list(range(len(boxes)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    order=sorted(range(len(boxes)),key=lambda i:boxes[i][0])
    for oi,i in enumerate(order):
        a=boxes[i]
        for j in order[oi+1:]:
            b=boxes[j]
            if b[0]>a[2]+radius:break
            if _gap(a,b)<=radius:
                x,y=find(i),find(j)
                if x!=y:parent[x]=y
    groups=defaultdict(list)
    for i in range(len(boxes)):groups[find(i)].append(i)
    return list(groups.values())


def _parallel_line_families(rows, cutoff, height, layout_bounds):
    """Find repeated long straight strokes by orientation and projected overlap."""
    candidates=[]
    for e in rows:
        if 'LINE' not in e['types']:continue
        rec=e['records'][0];pts=np.asarray(rec.get('samples',[]),dtype=float)
        if len(pts)<2:continue
        a,b=pts[0,:2],pts[-1,:2];d=b-a;length=float(np.linalg.norm(d))
        if length<=cutoff:continue
        angle=math.atan2(d[1],d[0])%math.pi
        candidates.append((e,angle,a,b,length))
    # Angular bins are only a candidate index; pair checks use a 3 degree tolerance.
    groups=defaultdict(list)
    for item in candidates:groups[round(item[1]/math.radians(3))].append(item)
    families=[];diag=math.hypot(layout_bounds[2]-layout_bounds[0],layout_bounds[3]-layout_bounds[1])
    for group in groups.values():
        if len(group)<4:continue
        for root in group:
            theta=root[1];u=np.array([math.cos(theta),math.sin(theta)]);n=np.array([-u[1],u[0]])
            projected=[]
            for e,angle,a,b,length in group:
                delta=abs((angle-theta+math.pi/2)%math.pi-math.pi/2)
                if delta>math.radians(3):continue
                along=sorted([float(a@u),float(b@u)])
                across=float(.5*(a+b)@n)
                projected.append((e,along,across))
            # Connected runs of overlapping projected spans form line families.
            spans=sorted(range(len(projected)),key=lambda i:projected[i][1][0]);par=list(range(len(projected)))
            def find(i):
                while par[i]!=i:par[i]=par[par[i]];i=par[i]
                return i
            for pos,i in enumerate(spans):
                ai=projected[i][1]
                for j in spans[pos+1:]:
                    bj=projected[j][1]
                    if bj[0]>ai[1]+2*height:break
                    overlap=max(0.0,min(ai[1],bj[1])-max(ai[0],bj[0]))
                    shorter=max(1e-9,min(ai[1]-ai[0],bj[1]-bj[0]))
                    if overlap/shorter>=.55 or _gap([ai[0],0,ai[1],0],[bj[0],0,bj[1],0])<=.15*height:
                        x,y=find(i),find(j)
                        if x!=y:par[x]=y
            parts=defaultdict(list)
            for i in range(len(projected)):parts[find(i)].append(i)
            for inds in parts.values():
                family=[projected[i][0] for i in inds]
                if len(family)<4:continue
                b=[min(e['bounds'][0] for e in family),min(e['bounds'][1] for e in family),max(e['bounds'][2] for e in family),max(e['bounds'][3] for e in family)]
                if b[2]-b[0]>.7*(layout_bounds[2]-layout_bounds[0]) or b[3]-b[1]>.7*(layout_bounds[3]-layout_bounds[1]):continue
                if max(0,b[2]-b[0])*max(0,b[3]-b[1])<.015*(layout_bounds[2]-layout_bounds[0])*(layout_bounds[3]-layout_bounds[1]):continue
                offsets=sorted(projected[i][2] for i in inds)
                gaps=np.diff(offsets);gaps=gaps[gaps>1e-8]
                if len(gaps)>1 and float(np.max(gaps))>2.2*float(np.median(gaps)):continue
                families.append((family,b))
    # Deduplicate the same family discovered from multiple angular roots.
    unique={tuple(sorted(e['instance'] for e in family)):(family,b) for family,b in families}
    return list(unique.values())


def partition(data, inv):
    """Partition mixed CAD layouts into view candidates with handle-level evidence."""
    entities=_spatial_entities(data);by_layout=defaultdict(list)
    for (layout,_),r in entities.items():by_layout[layout].append(r)
    result=[]
    title_patterns={k:re.compile(v) for k,v in TITLE.items()}
    explicit={
        'XY':re.compile(r'(?:plan\s*view|top\s*view|half.?breadth|水线图|半宽|俯视图)',re.I),
        'XZ':re.compile(r'(?:profile\s*view|side\s*view|sheer\s*plan|纵剖|侧视图)',re.I),
        'YZ':re.compile(r'(?:body\s*plan|cross\s*section|transverse\s*section|横剖|横截面)',re.I),
        'detail':re.compile(r'(?:typical\s*frame|frame\s*construction|detail\s*view|typical\s*detail|fore\s*deck|aft\s*deck|deck\s*plan|甲板|舱口|典型.*剖面|构造详图)',re.I),
    }
    for layout,items in sorted(by_layout.items()):
        curves=[e for e in items if any(t not in ('TEXT','LEADER','ARROW','TABLE') for t in e['types'])]
        texts=[e for e in items if 'TEXT' in e['types']]
        hs=[float(x.get('height',0)) for x in data.get('texts',[]) if x['layout']==layout and x.get('height',0)>0]
        h=float(np.median(hs)) if hs else max(1e-6, .002*max(max(e['bounds'][2] for e in items)-min(e['bounds'][0] for e in items),max(e['bounds'][3] for e in items)-min(e['bounds'][1] for e in items)))
        allbox=[min(e['bounds'][0] for e in items),min(e['bounds'][1] for e in items),max(e['bounds'][2] for e in items),max(e['bounds'][3] for e in items)]
        diagonal=math.hypot(allbox[2]-allbox[0],allbox[3]-allbox[1])
        sizes=[];line_sizes=[]
        for e in curves:
            b=e['bounds'];sizes.append(math.hypot(b[2]-b[0],b[3]-b[1]))
            if 'LINE' in e['types']:line_sizes.append(sizes[-1])
        if line_sizes:
            med=float(np.median(line_sizes));mad=float(np.median(np.abs(np.asarray(line_sizes)-med)))
            cutoff=max(6*h,med+6*mad)
        else:cutoff=6*h
        core=[]
        for e in curves:
            b=e['bounds'];d=math.hypot(b[2]-b[0],b[3]-b[1])
            # Long straight strokes can be dimension rails or sheet borders.
            # Continuous curves and polylines remain seed geometry: they often
            # encode an entire hull contour in a single CAD entity.
            if d<=cutoff or not any(t=='LINE' for t in e['types']):core.append(e)
        # CAD linework may be encoded as evenly spaced isolated rulings (for
        # example station ticks). Use local stroke scale as a second estimate;
        # keep it bounded by text height so widely spaced views stay separate.
        stroke=float(np.median(sizes)) if sizes else h
        cluster_radius=max(2.0*h,.75*stroke,1e-9)
        comps=_bbox_components([e['bounds'] for e in core],cluster_radius)
        comp_rows=[]
        for comp in comps:
            members=[core[i] for i in comp]
            b=[min(e['bounds'][0] for e in members),min(e['bounds'][1] for e in members),max(e['bounds'][2] for e in members),max(e['bounds'][3] for e in members)]
            comp_rows.append((members,b))
        largest=max((len(m) for m,_ in comp_rows),default=0)
        minimum=max(8,math.ceil(largest*.12))
        layout_area=max(1e-12,(allbox[2]-allbox[0])*(allbox[3]-allbox[1]))
        seeds=[]
        for members,b in comp_rows:
            curves_count=sum(any(t not in ('TEXT','LEADER','ARROW','TABLE','LINE') for t in e['types']) for e in members)
            area=max(0,b[2]-b[0])*max(0,b[3]-b[1])
            nearby_title=False
            for t in texts:
                rec=next((x for x in t['records'] if 'n' in x),{})
                if any(p.search(str(rec.get('n',''))) for p in explicit.values()) and _gap(t['bounds'],b)<=max(14*h,.1*diagonal):
                    nearby_title=True;break
            if len(members)>=minimum or (curves_count>=3 and len(members)>=5 and area>=.005*layout_area) or (nearby_title and len(members)>=3):
                seeds.append((members,b))
        family_seeds=_parallel_line_families(curves,cutoff,h,allbox)
        family_shared=[];seed_instances={e['instance'] for members,_ in seeds for e in members}
        for members,b in family_seeds:
            ids={e['instance'] for e in members}
            if ids & seed_instances:continue
            area=max(1e-12,(b[2]-b[0])*(b[3]-b[1]))
            overlaps=[]
            for i,(_,sb) in enumerate(seeds):
                ix=max(0.0,min(b[2],sb[2])-max(b[0],sb[0]));iy=max(0.0,min(b[3],sb[3])-max(b[1],sb[1]))
                if ix*iy/min(area,max(1e-12,(sb[2]-sb[0])*(sb[3]-sb[1])))>=.2:overlaps.append(i)
            if len(overlaps)==1:
                i=overlaps[0];seeds[i]=(seeds[i][0]+members,seeds[i][1]);seed_instances.update(ids)
            elif len(overlaps)>1:
                family_shared.append((members,overlaps));seed_instances.update(ids)
            elif area>=.015*layout_area:
                seeds.append((members,b));seed_instances.update(ids)
        if not seeds and core:
            # Sparse drawings may have no dense linework; retain one bounded candidate
            # only when text/geometry are sufficiently local rather than guessing globally.
            best=max(comp_rows,key=lambda x:len(x[0]))
            if len(best[0])>=3:seeds=[best]
        seeds.sort(key=lambda x:(x[1][0],-x[1][3]))
        assigned=[dict(seed=m,bounds=list(b),entities={e['instance']:e for e in m},shared=set()) for m,b in seeds]
        for members,indices in family_shared:
            for i in indices:
                assigned[i]['shared'].update(e['instance'] for e in members)
        frame=set();cross=set();unassigned=[]
        # Long lines are evidence but never allowed to bridge otherwise separate views.
        for e in curves:
            if e in core:continue
            b=e['bounds'];d=math.hypot(b[2]-b[0],b[3]-b[1])
            if d>cutoff and (b[2]-b[0]>.7*(allbox[2]-allbox[0]) or b[3]-b[1]>.7*(allbox[3]-allbox[1])):
                frame.add(e['instance']);continue
            gaps=[_gap(b,s['bounds']) for s in assigned]
            hit=[i for i,s in enumerate(assigned) if _overlap(b,s['bounds']) and d>2*h]
            if len(hit)>1:
                cross.add(e['instance'])
                for i in hit:assigned[i]['shared'].add(e['instance'])
                continue
            if gaps and min(gaps)<=max(4*h,.035*diagonal):
                i=int(np.argmin(gaps));assigned[i]['entities'][e['instance']]=e
            else:unassigned.append(e['instance'])
        # Text, leaders and native tables attach to the nearest view. A label is
        # never used to merge two geometry regions; ambiguous associations remain explicit.
        loose=[e for e in items if e not in curves]
        for e in loose:
            b=e['bounds'];gaps=[_gap(b,s['bounds']) for s in assigned]
            margin=max(14*h,.10*diagonal) if 'TEXT' in e['types'] else max(5*h,.04*diagonal)
            near=[i for i,g in enumerate(gaps) if g<=margin]
            if not near:
                unassigned.append(e['instance']);continue
            near.sort(key=lambda i:gaps[i])
            if len(near)>1 and gaps[near[1]]-gaps[near[0]]<max(h,.01*diagonal):
                cross.add(e['instance'])
                for i in near[:2]:assigned[i]['shared'].add(e['instance'])
            else:assigned[near[0]]['entities'][e['instance']]=e
        regions=[]
        for index,s in enumerate(assigned,1):
            owned=list(s['entities'].values());boxes=[e['bounds'] for e in owned]
            if not boxes:continue
            # The region boundary is the clustered source geometry envelope.
            # Attached labels and cross-region dimensions must not enlarge it.
            b=list(s['bounds'])
            handles=sorted(s['entities'])
            seed_handles=sorted(e['instance'] for e in s['seed'])
            title_evidence=[]
            for t in texts:
                if t['instance'] not in s['entities']:continue
                txt=next((str(r.get('n','')) for r in t['records'] if 'n' in r),'')
                if any(p.search(txt) for p in explicit.values()) or any(p.search(txt) for p in title_patterns.values()):
                    title_evidence.append(dict(handle=t['instance'],text=txt))
            view_candidates=[]
            for view,pattern in explicit.items():
                matches=[x for x in title_evidence if pattern.search(x['text'])]
                if matches:view_candidates.append(dict(view=view,confidence=.95,basis='nearby_explicit_title',handles=[x['handle'] for x in matches]))
            if not view_candidates:
                view_candidates=[dict(view=v,confidence=.2,basis='geometry_only_ambiguous',handles=[]) for v in ('XY','XZ','YZ')]
            token=f"{inv.get('source_sha256','')}/{layout}/{','.join(handles)}"
            rid='R-'+hashlib.sha256(token.encode()).hexdigest()[:12]
            orientations=Counter()
            for entity in owned:
                for record in entity['records']:
                    pts=np.asarray(record.get('samples',[]),dtype=float)
                    if len(pts)<2:continue
                    d=pts[-1,:2]-pts[0,:2]
                    if np.linalg.norm(d)>1e-9:
                        angle=math.degrees(math.atan2(d[1],d[0])%math.pi)
                        orientations[int(round(angle/5)*5)%180]+=1
            regions.append(dict(region_id=rid,layout=layout,bounds=b,coordinate_space='source_layout_xy',
                handles=handles,seed_handles=seed_handles,shared_handles=sorted(s['shared']),
                view_type_candidates=view_candidates,evidence=dict(seed_entity_count=len(seed_handles),
                    assigned_entity_count=len(handles),median_text_height=h,cluster_radius=cluster_radius,
                    long_geometry_cutoff=cutoff,title_matches=title_evidence,
                    line_direction_families=[dict(angle_deg=k,count=v) for k,v in orientations.most_common(8)],
                    geometry_types=dict(Counter(t for e in owned for t in e['types']))),
                overlap_status='multiple_view_titles_same_region' if len(title_evidence)>1 else 'not_observed',
                uncertainty=['view_type_requires_cross_view_or_title_confirmation'] if len(view_candidates)>1 else []))
        for i,a in enumerate(regions):
            overlaps=[]
            for j,b in enumerate(regions):
                if i==j or not _overlap(a['bounds'],b['bounds']):continue
                ix=max(0.0,min(a['bounds'][2],b['bounds'][2])-max(a['bounds'][0],b['bounds'][0]))
                iy=max(0.0,min(a['bounds'][3],b['bounds'][3])-max(a['bounds'][1],b['bounds'][1]))
                if ix>1e-9 and iy>1e-9:overlaps.append(b['region_id'])
            if overlaps:
                a['overlap_status']='overlaps_other_candidate_regions'
                a['overlapping_region_ids']=sorted(overlaps)
                a['uncertainty']=sorted(set(a['uncertainty']+['candidate_region_bounds_overlap; split_or_shared_view_needs_review']))
        result.append(dict(layout=layout,bounds=allbox,regions=regions,drawing_frame_handles=sorted(frame),
                           cross_region_handles=sorted(cross),unassigned_handles=sorted(set(unassigned)),
                           partition_parameters=dict(median_text_height=h,cluster_radius=cluster_radius,
                               long_geometry_cutoff=cutoff,minimum_seed_entities=minimum)))
    return result


def inspect(data, inv, frames, axis_records):
    """Partition each layout, then run existing registration logic per region."""
    from . import alignment
    all_dimensions=alignment.dimension_annotations(data.get('texts',[]))
    all_declarations=alignment.unit_declarations(data.get('texts',[]))
    partitions=partition(data,inv); output=[]
    entity_data=('texts','leaders','arrowheads','native','curves','segments','issues')
    for part in partitions:
        for region in part['regions']:
            handles=set(region['handles'])
            region_dimensions=[d for d in all_dimensions if d['layout']==part['layout'] and d['handle'] in handles]
            region_declarations=[u for u in all_declarations if u['layout']==part['layout'] and u['handle'] in handles]
            scales=[d for d in region_dimensions if d['kind']=='paper_scale']
            measures=[d for d in region_dimensions if d['kind']!='paper_scale']
            printed_units=sorted({u for d in measures for u in ((['ft','in'] if d['unit']=='ft_in' else [d['unit']]))})
            declared_units=sorted({d['unit'] for d in region_declarations})
            conflict=len(printed_units)>1 and not any(d['unit']=='ft_in' for d in measures)
            if declared_units and printed_units:
                if any(u not in printed_units and not (u in ('ft','in') and set(printed_units)>={'ft','in'}) for u in declared_units):
                    conflict=True
            header_code=inv.get('insertion_units_code')
            header_unit=UNITS.get(header_code)
            region['dimensions']=region_dimensions
            region['unit_evidence']=dict(state='conflict' if conflict else 'evidenced' if printed_units or declared_units else 'unknown',
                printed_units=printed_units,declared_units=declared_units,declarations=region_declarations,
                cad_header=dict(code=header_code,unit=header_unit,scope='drawing_header_only'),
                paper_scales=scales,unknown=['unit_or_scale_not_inferred_from_geometry'] if not printed_units and not declared_units else [])
            sub={k:[x for x in data.get(k,[]) if x.get('layout')==part['layout'] and x.get('instance') in handles]
                 for k in entity_data}
            sub['counts']=data.get('counts',{})
            subinv=dict(inv,regions=[r for r in inv.get('regions',[]) if r.get('layout')==part['layout'] and
                                     r.get('anchor',{}).get('instance') in handles])
            rb=region['bounds'];margin=max(2*region['evidence']['median_text_height'],.01*math.hypot(rb[2]-rb[0],rb[3]-rb[1]))
            def scoped(record):
                if record.get('layout')!=part['layout']:return False
                bounds=record.get('paper_bounds',record.get('bounds'))
                if not bounds or len(bounds)!=2:return False
                try:box=[bounds[0][0],bounds[0][1],bounds[1][0],bounds[1][1]]
                except (IndexError,TypeError):return False
                return _gap(box,[rb[0]-margin,rb[1]-margin,rb[2]+margin,rb[3]+margin])==0
            local_frames=[f for f in frames if scoped(f) or (f.get('layout')==part['layout'] and
                f.get('method')=='explicit_controls' and f.get('controls') and set(f['controls'])<=handles)]
            local_axes=[a for a in axis_records if scoped(a)]
            rec=_inspect_registration(sub,subinv,local_frames,local_axes)
            local=next((x for x in rec['layouts'] if x['layout']==part['layout']),dict(layout=part['layout'],ranked=[],series={},
                datum_labels={},families={},unit=dict(state='unknown',header=None,printed=[])))
            region['registration']=local
            for candidate in local.get('ranked',[]):candidate['region_id']=region['region_id']
        if len(part['regions'])==1:
            series=part['regions'][0].get('registration',{}).get('series',{})
            datum_labels=part['regions'][0].get('registration',{}).get('datum_labels',{})
            unit=part['regions'][0].get('registration',{}).get('unit',dict(state='unknown',header=None,printed=[]))
        else:
            series={r['region_id']:r.get('registration',{}).get('series',{}) for r in part['regions']}
            datum_labels={r['region_id']:r.get('registration',{}).get('datum_labels',{}) for r in part['regions']}
            unit=dict(state='region_scoped',regions={r['region_id']:r.get('registration',{}).get('unit',{}) for r in part['regions']})
        output.append(dict(layout=part['layout'],regions=part['regions'],ranked=[c for r in part['regions'] for c in r.get('registration',{}).get('ranked',[])],
            series=series,datum_labels=datum_labels,unit=unit,
            drawing_frame_handles=part['drawing_frame_handles'],cross_region_handles=part['cross_region_handles'],
            unassigned_handles=part['unassigned_handles'],partition_parameters=part['partition_parameters']))
    return dict(source_sha256=inv['source_sha256'],layouts=output,origin='automatic_cad_only',installation_authorized=False)


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
