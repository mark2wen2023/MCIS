"""Shared closed-world inventory; only two fixed strict profiles, no ignore option."""
import ast
import hashlib
import json
from .contract import need
from mcis_service.audio_review.generation_links import validate_rows

PAIRS = {'audio': ('audio_review_revisions', 'audio_asr_tasks'),
         'image': ('image_ocr_review_records', 'image_ocr_tasks')}
PREFIX = 'MCIS-EVIDENCE-INTAKE/1 '


def _doc(row):
    doc = json.loads(row['doc'])
    need(type(doc) is dict, 'document')
    return doc


def _scan(connection, case_id, profile):
    need(profile in ('legacy', 'generation'), 'unknown inventory profile')
    need(connection.in_transaction, 'explicit snapshot transaction required')
    need(type(case_id) is str and bool(case_id), 'case id')
    tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    rows, unscoped = {}, []
    size = 0
    for table in tables:
        quoted = '"' + table.replace('"', '""') + '"'
        cols = [r[1] for r in connection.execute('PRAGMA table_info('+quoted+')')]
        if 'case_id' not in cols:
            unscoped.append(table)
            continue
        cursor = connection.execute('SELECT * FROM '+quoted+' WHERE case_id=? LIMIT 10001', (case_id,))
        values = cursor.fetchall()
        need(len(values) <= 10000, 'row budget')
        names = [d[0] for d in cursor.description]
        rows[table] = [dict(zip(names, value)) for value in values]
        # Existing JSON/text is retained, not reconstructed from a view or latest row.
        size += sum(len(repr(row).encode()) for row in values)
        need(size <= 32 * 1024 * 1024, 'inventory budget')
    need(all(t in rows for t in ('cases','audit_events','evidence_items','custody_events')), 'required schema absent')
    need(len(rows['cases']) == 1, 'case absent/ambiguous')
    known_media = {t for pair in PAIRS.values() for t in pair}
    if profile == 'generation':
        # New standalone inventory: recognize these only after complete linkage validation.
        required = ('audio_task_generations','audio_task_observations')
        need(all(t in rows for t in required), 'generation schema absent; history unknown')
        linked = validate_rows(case_id,
            [{**r,'doc':_doc(r)} for r in rows.get('audio_asr_tasks',[])],
            [{**r,'doc':_doc(r)} for r in rows[required[0]]],
            [{**r,'doc':_doc(r)} for r in rows[required[1]]], rows['audit_events'])
        need(linked['archiveReady'] is False, 'research only')
        known_media |= set(required)
    need(not any(v and t.startswith(('audio_', 'image_')) and t not in known_media for t,v in rows.items()), 'unknown media table')
    audits = sorted(rows['audit_events'], key=lambda r:r['seq'])
    previous = '0' * 64
    for seq, event in enumerate(audits, 1):
        native = json.loads(event['line'])
        need(event['seq'] == seq and event['prev_hash'] == previous, 'audit sequence')
        for k in ('seq','utc','operator','role','action','category','command','before','after','entity_type','entity_id'):
            need(native.get(k) == event[k], 'audit columns/line disagree')
        need(native.get('prev') == previous, 'audit previous')
        previous = hashlib.sha256(event['line'].encode()).hexdigest()
    links, used = [], set()

    def unique(action, command, entity, doc, after=None):
        found = [e for e in audits if e['action']==action and e['command']==command and e['entity_id']==entity
                 and e['operator']==doc.get('operator') and e['role']==doc.get('role')]
        # Match the native after summary, never assume equal timestamps (separate clock reads).
        if after is not None:
            matching = []
            for e in found:
                try:
                    need(len(e['after']) <= 400, 'audit summary limit')
                    value = ast.literal_eval(e['after'])
                except (ValueError, SyntaxError, TypeError, RecursionError):
                    continue
                if value == after:
                    matching.append(e)
            found = matching
        need(len(found)==1, 'missing or ambiguous revision/task audit')
        used.add(found[0]['seq'])
        return found[0]['seq']

    registrations = {}
    def receipt(digest):
        need(type(digest) is str and len(digest)==64, 'receipt id')
        if digest in registrations:
            return
        rel = 'raw/evidence-intakes/'+digest+'/source.bin'
        ev = [r for r in rows['evidence_items'] if _doc(r).get('relativePath')==rel]
        regs = []
        for r in rows['custody_events']:
            if r['kind']=='Register' and r['detail'].startswith(PREFIX):
                saved = json.loads(r['detail'][len(PREFIX):])
                if saved.get('requestDigest')==digest:
                    regs.append((r,saved))
        need(len(ev)==len(regs)==1, 'missing/ambiguous registration')
        reg,saved=regs[0]; evidence=_doc(ev[0])
        need(ev[0]['key']==reg['evidence_id']==evidence.get('evidenceId') and
             saved.get('binding',{}).get('caseId')==case_id and reg['sha256']==evidence.get('sha256'), 'registration association')
        need(not any(r['evidence_id']==reg['evidence_id'] and r['kind']=='Change' for r in rows['custody_events']), 'changed registration unsupported')
        registrations[digest]={'evidenceId':reg['evidence_id'],'custodySeq':reg['seq'], 'bytesVerified':False}

    task_index, run_index = {}, {}
    for kind,(revision_table,task_table) in PAIRS.items():
        need((revision_table in rows)==(task_table in rows), 'partial media schema')
        for row in rows.get(task_table,[]):
            task_id=row['task_id']; doc=_doc(row)
            need((kind,task_id) not in task_index and doc.get('taskId')==task_id and doc.get('caseId')==case_id, 'task identity')
            task_index[kind,task_id]=(row,doc)
        for row in rows.get(revision_table,[]):
            run_index.setdefault((kind,row['run_id']),[]).append(row)
    for (kind,run_id), revisions in run_index.items():
        revisions.sort(key=lambda r:r['revision'])
        need([r['revision'] for r in revisions]==list(range(len(revisions))), 'missing/duplicate revision')
        initial=_doc(revisions[0]); task_id=initial.get('artifactTaskId')
        if kind=='audio':
            receipt(initial.get('audioReceipt'))
            if task_id is None:receipt(initial.get('draftReceipt'))
        else:
            bindings=initial.get('bindings')
            need(type(bindings) is dict and set(bindings)==({'pdf','image'} if task_id else {'pdf','image','candidate','raw'}), 'image bindings')
            for value in bindings.values():receipt(value)
        if task_id is not None:
            entry=task_index.get((kind,task_id))
            need(entry is not None and entry[1].get('status')=='succeeded' and entry[1].get('runId')==run_id, 'task/run association')
        for n,row in enumerate(revisions):
            doc=_doc(row)
            need(all(type(doc.get(k)) is str and doc[k] for k in ('operator','role','utc')), 'revision actor/time absent')
            if n:
                need(doc.get('revision')==n and doc.get('expectedRevision')==n-1, 'revision document')
                key='segmentId' if kind=='audio' else 'lineIndex'
                need(key in doc, 'revision target')
                seq=unique('audio.human.revise' if kind=='audio' else 'ocr.review',run_id,run_id,doc,{'revision':n,key:doc[key]})
            elif task_id is not None:
                seq=unique('asr.task.succeeded' if kind=='audio' else 'ocr.task.succeeded',task_id,run_id,doc)
            else:
                seq=unique('audio.draft.attach' if kind=='audio' else 'ocr.import',run_id,run_id,doc,None if kind=='audio' else {'revision':0})
            links.append({'kind':kind,'runId':run_id,'revision':n,'auditSeq':seq})
    for (kind,task_id),(row,doc) in task_index.items():
        prefix='asr' if kind=='audio' else 'ocr'
        if kind=='audio': receipt(doc.get('audioReceipt'))
        else:
            need(type(doc.get('bindings')) is dict and set(doc['bindings'])=={'pdf','image'}, 'task image bindings')
            for value in doc['bindings'].values():receipt(value)
        unique(prefix+'.task.start',task_id,task_id,doc)
        status=doc.get('status')
        need(status in ('succeeded','failed','running_or_unknown','interrupted_unknown'), 'task state')
        if status=='succeeded':
            group=run_index.get((kind,doc.get('runId')))
            need(group is not None and _doc(group[0]).get('artifactTaskId')==task_id, 'successful task missing run')
            unique(prefix+'.task.succeeded',task_id,doc['runId'],doc)
        else:
            need(doc.get('runId') is None, 'unfinished task published run')
            if status!='running_or_unknown':
                action='asr.task.incomplete' if kind=='audio' else ('ocr.task.failed' if status=='failed' else 'ocr.task.unknown')
                unique(action,task_id,task_id,doc)
    for e in audits:
        if e['action'].startswith(('audio.','asr.','ocr.')) and e['seq'] not in used:
            # Access events are retained too, but do not prove a revision.
            kind='audio' if e['action']=='asr.artifact.access' else 'image'
            need(e['action'] in ('asr.artifact.access','ocr.artifact.access') and
                 (kind,e['command']) in task_index and e['entity_id']==e['command'], 'unmapped media audit')
    return {'restore_ready':False,'export_allowed':False,'bytes_verified':False,
            'scope':'native-row-inventory-and-unique-audit-match-only','rows':rows,
            'unscopedTables':unscoped,'revisionAuditLinks':links,'registrations':registrations}
