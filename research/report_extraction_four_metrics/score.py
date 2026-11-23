"""Research arithmetic only. Review annotations are NOT inferred from quotations."""
import hashlib,json

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def ratio(n,d):
    return {'numerator':n,'denominator':d,'value':n/d if d else None}

def unique(values):
    if any(type(v) is not str or not v for v in values) or len(values)!=len(set(values)):
        raise ValueError('identity')
    return set(values)

def evaluate(raw,source_sha,output,review,locate):
    """Review is independent scoring input, never an extractor/filter input.

    Required IDs and conflict sides are predeclared. Human matches are explicit,
    not lexical matching. Pending review withholds final semantic/recall metrics.
    """
    try:
        if type(raw) is not bytes or hashlib.sha256(raw).hexdigest()!=source_sha:raise ValueError('source binding')
        if output['status'] not in ('valid','failed'):raise ValueError('run status')
        if output['status']=='failed':return {'status':'failed','metrics':None}
        atoms=output['atoms']; ids=unique([a['id'] for a in atoms])
        if any(set(a)!= {'id','claim','citations'} or type(a['claim']) is not str or not a['claim'].strip() or type(a['citations']) is not list for a in atoms):raise ValueError('atom shape')
        if review['outputDigest']!=digest(output) or review['sourceSha256']!=source_sha:raise ValueError('review binding')
        required=unique(review['required'])
        groups=review['conflicts']
        unique(list(groups))
        for members in groups.values():
            if len(unique(members))<2 or not set(members)<=required:raise ValueError('conflict members')
        marks=review['atoms']
        if set(marks)!=ids:raise ValueError('review identities')
        pending=unique(review['pendingRequired'])
        if not pending<=required or type(review['complete']) is not bool:raise ValueError('pending identities')
        counts={k:0 for k in ('S','C','U','D')};matched=set();valid_cites=0;total_cites=0;covered=0;cite_ids=[];atom_keys=set();located_matches=set()
        for a in atoms:
            m=marks[a['id']]
            if set(m)!= {'support','matches'} or m['support'] not in counts:raise ValueError('review label')
            matches=unique(m['matches'])
            if not matches<=required or (matches and m['support']!='S'):raise ValueError('unsupported match')
            if any(len(matches & set(g))>1 for g in groups.values()):raise ValueError('split conflicting sides into separate atoms')
            counts[m['support']]+=1;matched.update(matches)
            covered+=bool(a['citations'])
            locations=set();citation_keys=[]
            for c in a['citations']:
                if set(c)!= {'id','atomId','span'} or c['atomId']!=a['id']:raise ValueError('citation identity')
                cite_ids.append(c['id']);total_cites+=1
                try:location=locate(raw,c['span'],expected_sha256=source_sha)
                except ValueError:
                    citation_keys.append(('invalid',digest(c['span'])))
                else:
                    key=(location['sourceSha256'],location['byteStart'],location['byteEndExclusive'])
                    if key in locations:raise ValueError('duplicate located citation')
                    locations.add(key);citation_keys.append(('located',*key));valid_cites+=1
            # IDs, citation order and review labels do not distinguish identical output.
            atom_key=(a['claim'],tuple(sorted(citation_keys)))
            if atom_key in atom_keys:raise ValueError('duplicate atom content')
            atom_keys.add(atom_key)
            if locations:located_matches.update(matches)
        unique(cite_ids)
        if pending & matched:raise ValueError('pending matched')
        if review['complete'] and (pending or counts['D']):raise ValueError('incomplete declared complete')
        complete=review['complete']
        metrics={'citationCoverage':ratio(covered,len(atoms)), 'locatorAccuracy':ratio(valid_cites,total_cites),
                 'semanticSupport':ratio(counts['S'],len(atoms)) if complete else None,
                 'mandatoryRecall':ratio(len(matched),len(required)) if complete else None,
                 'conflictRetention':ratio(sum(set(g)<=located_matches for g in groups.values()),len(groups)) if complete else None}
        failures=[]
        if valid_cites<total_cites:failures.append('locator_mismatch')
        if complete and counts['C']+counts['U']:failures.append('semantic_not_supported')
        if complete and any(not set(g)<=located_matches for g in groups.values()):failures.append('conflict_not_preserved')
        return {'status':'complete' if complete else 'pending','metrics':metrics,'labels':counts,
                'pendingMandatory':sorted(pending),'missingMandatory':sorted(required-matched) if complete else None,
                'controlFailures':failures,'modelRun':False,'semanticJudgmentAutomated':False,
                'reviewOrigin':'developer_visible_synthetic_control_not_independent_review'}
    except (ValueError,KeyError,TypeError):
        return {'status':'malformed','metrics':None}
