"""Offline v1/v2 member validation. Derived from a812d38 conflicts.py.
No export/import wiring, DB access, active receipt restoration or byte verification.
"""
import hashlib
import json
import re
from datetime import datetime
from mcis_service.common import contracts
from pathlib import Path
from jsonschema import Draft202012Validator
from mcis_service.working_records_archive.validation import canonical, digest

MAX_BYTES = 16 * 1024 * 1024
MAX_REVISIONS = 4096
MAX_LINES = 65536


class ConflictArchiveInvalid(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise ConflictArchiveInvalid(reason)


def load(raw):
    require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES, 'UTF-8 member budget/type')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def constant(_):
        raise ConflictArchiveInvalid('nonfinite JSON')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def stamp(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)', value), 'UTC timestamp')
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def chain(lines, case_id):
    require(isinstance(lines, list) and len(lines) <= MAX_LINES, 'chain budget/type')
    previous = '0' * 64
    result = {}
    total = 0
    for seq, line in enumerate(lines, 1):
        require(isinstance(line, str) and not any(c in line for c in '\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029'), 'raw line separator/type')
        raw = line.encode('utf-8'); total += len(raw)
        require(total <= MAX_BYTES, 'chain byte budget')
        row = load(raw)
        require(isinstance(row, dict) and type(row.get('seq')) is int and row['seq'] == seq and row.get('prev') == previous, 'chain order/hash')
        require(row.get('case_id', case_id) == case_id and row.get('caseId', case_id) == case_id, 'chain case')
        for field in ('operator', 'action', 'category', 'command', 'before', 'after'):
            require(isinstance(row.get(field), str), 'chain field')
        stamp(row.get('utc'))
        previous = hashlib.sha256(raw).hexdigest()
        result[seq] = (row, previous)
    return result


def parse(raw, *, case_id, evidence, audit_lines, custody_lines, vessel_ids):
    """Validate against explicit same-snapshot package dependencies; no authorization claim.

    Returns exact JSON values. Caller must supply complete authorized dependencies and
    still validate the whole package. This does not authenticate supplied hashes/history.
    """
    try:
        return _parse(raw, case_id, evidence, audit_lines, custody_lines, vessel_ids)
    except ConflictArchiveInvalid:
        raise
    except Exception as exc:
        raise ConflictArchiveInvalid('invalid conflict archive or dependency') from exc


def _parse(raw, case_id, evidence, audit_lines, custody_lines, vessel_ids):
    data = load(raw)
    require(type(data.get('version')) is int and data['version'] in (1,2), 'version')
    schema_path = Path(__file__).parent / ('fixtures/a812d38-conflict-archive.schema.json' if data['version']==1 else 'conflict-archive-v2.schema.json')
    Draft202012Validator(json.loads(schema_path.read_text()),registry=contracts.registry()).validate(data)
    require(type(data['version']) is int and data['caseId'] == case_id, 'member version/case')
    require(isinstance(evidence, list) and len(evidence) <= 4096, 'evidence budget/type')
    require(isinstance(vessel_ids, set) and all(isinstance(v, str) for v in vessel_ids), 'vessel inventory')
    index = {}
    for doc in evidence:
        contracts.validate('evidence-item', doc)
        key = doc['evidenceId']
        require(doc['caseId'] == case_id and key not in index, 'evidence identity')
        index[key] = doc
    audit = chain(audit_lines, case_id)
    custody = chain(custody_lines, case_id)
    versions = {}; anchored = {}; last_for_evidence = {}
    for seq, (row, sha) in custody.items():
        eid = row.get('evidence_id'); action = row['action']
        require(eid in index, 'custody evidence')
        if action == 'custody.register':
            require(eid not in versions and row.get('sha256') == index[eid]['sha256'], 'registration digest')
            versions[eid] = row['sha256']
        else:
            require(eid in versions and action in ('custody.change','custody.verify','custody.access','custody.review'), 'custody action/order')
            if action in ('custody.change','custody.verify'):
                require(row['before'] == versions[eid] and re.fullmatch('[0-9a-f]{64}',row.get('sha256','')), 'custody version')
                if action == 'custody.change': versions[eid] = row['sha256']
                else: require(row.get('result') in ('match','mismatch') and (row['result']=='match') == (row['sha256']==versions[eid]), 'verify result')
        anchored[seq] = (eid, sha, versions[eid])
        last_for_evidence[eid] = seq

    def document(doc, key):
        require(doc['caseId'] == case_id and doc['conflictId'] == key, 'conflict identity')
        require(doc.get('vesselId') is None or doc['vesselId'] in vessel_ids, 'vessel reference')
        for side in ('a','b'):
            eid = doc[side].get('evidenceId')
            require(eid is None or eid in index, 'unresolved historical source')

    def sources(bindings, doc):
        for side in ('a','b'):
            source = bindings[side]; eid = doc[side].get('evidenceId')
            require(source['evidenceId'] == eid and source['bytesVerified'] is False, 'source identity/verification')
            if eid is None:
                require(source['status'] == 'unregistered', 'inline source status'); continue
            require(source['status'] == 'registered-version' and source['registrationSha256'] == index[eid]['sha256'], 'source registration')
            seq = source['custodyHeadSeq']
            if seq is None:
                require(source['custodyHeadSha256'] is None and eid not in last_for_evidence and source['sha256'] == index[eid]['sha256'], 'missing custody anchor')
            else:
                require(type(seq) is int and anchored.get(seq) == (eid,source['custodyHeadSha256'],source['sha256']), 'source version anchor')
            # registryDocSha256 may describe an unavailable historical preimage.
            # Never compare it to current registry as proof of original bytes.

    keys = set(); linked = set(); total = 0
    for record in data['records']:
        key = record['key']; require(key not in keys, 'duplicate conflict'); keys.add(key)
        require(stamp(record['createdUtc']) <= stamp(record['updatedUtc']), 'row timestamps')
        document(record['doc'], key)
        revisions = record['revisions']; total += len(revisions)
        require(total <= MAX_REVISIONS, 'total revision budget')
        require(revisions or record['coverage'] == 'unknown-before-capture', 'missing captured history')
        previous = None; first_seq = None
        for ordinal, revision in enumerate(revisions, 1):
            require(type(revision['revision']) is int and revision['revision'] == ordinal and revision['caseId'] == case_id and revision['conflictId'] == key and revision['coverage'] == record['coverage'], 'revision identity/order/coverage')
            require(digest({k:v for k,v in revision.items() if k != 'sha256'}) == revision['sha256'], 'revision digest')
            require(revision['previousSha256'] == (previous['sha256'] if previous else None), 'revision chain')
            if previous:
                require(canonical(revision['before']) == canonical(previous['after']) and canonical(revision['beforeSources']) == canonical(previous['afterSources']), 'revision preimage')
                require(revision['auditSeq'] > previous['auditSeq'], 'audit order')
            else:
                first_seq = revision['auditSeq']
                require(revision['beforeSources'] is None, 'first source history')
                if record['coverage'] == 'captured-from-creation': require(revision['before'] is None and revision['operation']=='conflict.add', 'creation baseline')
            for doc in (revision['before'],revision['after']):
                if doc is not None: document(doc,key)
            require(revision['before'] is not None or revision['operation']=='conflict.add', 'update missing preimage')
            if revision['operation'] == 'conflict.update':
                strip = lambda doc: {k:v for k,v in doc.items() if k not in ('status','resolution')}
                require(canonical(strip(revision['before'])) == canonical(strip(revision['after'])), 'patch changes observation')
            sources(revision['afterSources'],revision['after'])
            if revision['beforeSources'] is not None: sources(revision['beforeSources'],revision['before'])
            if previous:
                for side in ('a','b'):
                    if revision['before'][side] == revision['after'][side]:
                        require(revision['afterSources'][side] == revision['beforeSources'][side], 'unchanged observation binding')
            seq = revision['auditSeq']; require(type(seq) is int and seq not in linked and seq in audit, 'missing/duplicate audit link')
            row, sha = audit[seq]
            require(sha == revision['auditLineSha256'] and row.get('entity_type')=='conflict' and row.get('entity_id')==key and row['category']=='Timeline', 'audit binding')
            for field, field2 in (('operator','operator'),('role','role'),('utc','utc'),('action','operation')):
                require(row.get(field) == revision[field2], 'audit attributes')
            stamp(revision['utc']); linked.add(seq); previous = revision
        if previous: require(canonical(previous['after']) == canonical(record['doc']), 'terminal state')
        # Do not silently drop a captured revision represented in the complete audit.
        for seq,(row,_) in audit.items():
            if row.get('entity_type')=='conflict' and row.get('entity_id')==key and row['action'] in ('conflict.add','conflict.update'):
                if record['coverage']=='captured-from-creation' or first_seq is not None and seq >= first_seq:
                    require(seq in linked, 'omitted captured revision')
    for row,_ in audit.values():
        if row.get('entity_type')=='conflict' and row['action'] in ('conflict.add','conflict.update'):
            require(row.get('entity_id') in keys, 'omitted conflict current row')
    if data['version']==2: validate_receipts(data,audit,index,anchored,last_for_evidence,custody)
    canonical(data)  # Also reject non-finite exponent overflow and invalid Unicode.
    return data


def validate_receipts(data,audit,index,anchored,last_for_evidence,custody):
    """Historical declarations only; never produce active receipt rows/tokens."""
    case_id=data['caseId'];records={r['key']:r for r in data['records']}
    used={}
    for record in data['records']:
        for rev in record['revisions']:
            if 'sourceReceiptId' in rev:
                key=rev['sourceReceiptId']
                require(key not in used,'receipt consumed more than once')
                used[key]=rev
    issued={}
    for seq,(event,_) in audit.items():
        if event['action']=='conflict.sourceReceipt':
            key=event['after']
            require(key not in issued and event.get('entity_type')=='conflict' and event['category']=='Timeline','issuance identity')
            issued[key]=(seq,event)
    seen=set()
    for row in data['receipts']:
        key=row['receiptId'];doc=row['doc'];conflict=row['conflictId']
        require(key not in seen and key in issued,'receipt duplicate/missing issuance');seen.add(key)
        require(row['caseId']==doc['caseId']==case_id and doc['conflictId']==conflict and conflict in records,'receipt case/conflict')
        require(row['authorization']=='inactive-history','receipt authorization')
        start,end=stamp(doc['issuedUtc']),stamp(doc['expiresUtc'])
        require((end-start).total_seconds()==600,'receipt lifetime')
        seq,event=issued[key]
        require(event['entity_id']==conflict and event['operator']==doc['operator'] and event['role']==doc['role'],'issuance actor/conflict')
        require(start<=stamp(event['utc'])<end,'issuance time')
        for eid,source in doc['sources'].items():
            require(eid in index and source['bytesVerified'] is False,'receipt source identity')
            head=source['custodyHeadSeq']
            if head is None:
                require(source['custodyHeadSha256'] is None and source['sha256']==index[eid]['sha256'],'receipt missing custody anchor')
                # Cannot prove a missing original anchor if custody history exists.
                require(eid not in last_for_evidence,'receipt missing custody history')
            else:
                require(type(head) is int and anchored.get(head)==(eid,source['custodyHeadSha256'],source['sha256']),'receipt custody binding')
                require(stamp(custody[head][0]['utc'])<=start,'receipt custody time')
        revision=used.get(key)
        if revision is None:
            require(row['consumedRevision'] is None,'orphan consumed receipt')
            # Unused/expired proposals were never stored with this receipt; retain
            # their digest declaration without inventing proposal or authorization.
            continue
        require(type(row['consumedRevision']) is int and row['consumedRevision']==revision['revision'] and revision['conflictId']==conflict,'consumption binding')
        require(revision['before'] is not None and revision['operation']=='conflict.add','receipt operation')
        require(seq<revision['auditSeq'] and start<=stamp(revision['utc'])<end,'consumption order/time')
        require(revision['operator']==doc['operator'] and revision['role']==doc['role'],'consumption actor')
        expected=digest({'caseId':case_id,'conflictId':conflict,'current':revision['before'],'revisionSha256':revision['previousSha256']})
        require(doc['conflictVersion']==expected,'receipt conflict version')
        require(doc['observationsSha256']==digest({side:revision['after'][side] for side in ('a','b')}),'receipt observations')
        sides=[side for side in ('a','b') if revision['before'][side]!=revision['after'][side]]
        refs={snapshot[side].get('evidenceId') for side in sides for snapshot in (revision['before'],revision['after'])}
        require(sides and None not in refs and set(doc['sources'])==refs,'receipt sources set')
        for side in sides:
            eid=revision['after'][side]['evidenceId'];binding=revision['afterSources'][side]
            require(all(binding.get(k)==v for k,v in doc['sources'][eid].items()),'receipt captured source')
    require(seen==set(issued) and set(used)<=seen,'omitted historical receipts')
