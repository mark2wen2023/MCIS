"""Synthetic receiver acceptance fixture, NOT FourChair or a production interface."""
import hashlib,json
def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
ROLES=('regulations','navigation','investigation','vessel')
def receive(draft, expected_digest, opinions, registry, validate):
    if digest(draft)!=expected_digest:raise ValueError('DRAFT_CHANGED')
    if len(opinions)!=4 or {o['role'] for o in opinions}!=set(ROLES):raise ValueError('FOUR_ATTRIBUTED_OPINIONS')
    originals={};attributed=[]
    for op in opinions:
        if op['draftVersion']!=draft['version'] or op['draftDigest']!=expected_digest:raise ValueError('OPINION_DRAFT_MISMATCH')
        if not op['citations']:raise ValueError('CITATIONS_REQUIRED')
        cited=[]
        for alias in op['citations']:
            if alias not in registry:raise ValueError('UNKNOWN_SOURCE')
            src=registry[alias]
            cited.append(src)
            # Bytes + exact line identify original location. No role, alias, statement or quote in key.
            key=(src['sha256'],src['line'])
            if key in originals and originals[key]!=src:raise ValueError('SOURCE_IDENTITY_CONFLICT')
            originals[key]=src
        quote=op['review'].get('quote')
        matching=[src for src in cited if isinstance(quote,str) and quote and quote in src['excerpt']]
        if not matching:raise ValueError('QUOTE_NOT_IN_CITED_EXCERPT')
        # Actual unchanged validator sees exactly one explicitly cited located excerpt.
        packet={'items':[{'itemId':'draft','sourceText':matching[0]['excerpt']}]}
        validate({'reviews':[op['review']]},packet)
        attributed.append({'role':op['role'],'draftVersion':op['draftVersion'],
                           'review':op['review'],'citations':list(op['citations'])})
    observation=[s for s in originals.values() if s['target']=='EV-1']
    causal=[s for s in originals.values() if s['target']=='LINK-1']
    stances={s['sourceAssertedStance'] for s in causal}
    return {'scope':'synthetic receiver acceptance only','chair':'海青君（待实现接收接缝）',
        'draftVersion':draft['version'],'draftDigest':expected_digest,
        'opinionCount':len(attributed),'opinions':attributed,
        'locatedOriginalCount':len(originals),'observationOriginalCount':len(observation),
        'causalStatementOriginalCount':len(causal),'originals':list(originals.values()),
        'reviewStatus':'opposed_source_assertions_pending' if stances=={'supports','refutes'} else 'insufficient_evidence_pending',
        'sourceCountIsWeight':False,'independenceBeyondByteLocation':'NOT_ASSESSED',
        'causalConclusion':None,'jumpAnchor':None,'humanConfirmation':'PENDING','factVerified':False}
