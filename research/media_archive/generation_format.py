"""Offline research v2 envelope; v1 semantics untouched, no product extraction."""
from .contract import validate as validate_v1, FORMAT as V1, need, shape, ident, digest, parse, LIMIT
from mcis_service.audio_review.generation_links import validate_rows

FORMAT = 'MCIS-MEDIA-ARCHIVE-RESEARCH-2'


def validate(index, payloads):
    if type(index) is dict and index.get('format') == V1:
        result = validate_v1(index, payloads)
        return {**result, 'generationHistory': 'unknown-not-upgraded', 'archiveReady': False}
    shape(index, 'format caseId archiveReady base members generations observations')
    need(index['format'] == FORMAT and index['archiveReady'] is False, 'research version')
    base=index['base'];need(type(base) is dict and base.get('caseId')==index['caseId'],'base case')
    need(type(payloads) is dict and type(index['members']) is dict and set(payloads)==set(index['members']),'complete membership')
    need(len(payloads)<=512 and all(type(b) is bytes and len(b)<=LIMIT for b in payloads.values()),'member budget')
    need(sum(map(len,payloads.values()))<=64*1024*1024,'aggregate budget')
    for name,desc in index['members'].items():
        ident(name);shape(desc,'size sha256')
        need(type(desc['size']) is int and desc['size']==len(payloads[name]) and desc['sha256']==digest(payloads[name]),'member digest')
    need(type(base.get('members')) is dict and set(base['members'])<=set(payloads),'base members')
    need(all(index['members'][n]==d for n,d in base['members'].items()),'base descriptors')
    validate_v1(base,{n:payloads[n] for n in base['members']})
    # This version covers audio generations only. Mixed image tasks must not be omitted.
    need(all(s['kind']=='audio' for s in base['sources']),'v2 audio-only scope')
    used=set(base['members'])
    def records(key, fields):
        need(type(index[key]) is list and len(index[key])<=10000,'record list')
        result=[]
        for ref in index[key]:
            ident(ref);need(ref in payloads and ref not in used,'duplicate/missing record member')
            used.add(ref);row=parse(payloads[ref]);shape(row,fields);result.append(row)
        return result
    generations=records('generations','case_id generation_id task_id doc')
    observations=records('observations','case_id generation_id ordinal doc')
    need(used==set(payloads),'unreferenced member')
    tasks=[{'case_id':index['caseId'],'task_id':t['id'],'doc':parse(payloads[t['recordMember']])} for t in base['tasks']]
    audits=[]
    for ref in base['audit']:
        raw=payloads[ref['member']];doc=parse(raw)
        audits.append({**doc,'case_id':index['caseId'],'line':raw.decode('utf-8')})
    linked=validate_rows(index['caseId'],tasks,generations,observations,audits)
    # Base source descriptor is also required to match the saved generation/task snapshot.
    sources={s['id']:s for s in base['sources']}
    for t in base['tasks']:
        source=parse(payloads[t['recordMember']]).get('source');registered=sources[t['sourceId']]
        need(type(source) is dict and source.get('caseId')==index['caseId'] and source.get('evidenceId')==registered['evidenceId'] and
             source.get('registeredSha256')==registered['registeredSha256'] and source.get('currentSha256')==registered['currentSha256'],'source descriptor binding')
    return {**linked,'format':FORMAT,'generationCount':len(generations),'observationCount':len(observations),
            'export_allowed':False,'execution_allowed':False,'generationHistory':'captured-claims-not-completion-proof'}
