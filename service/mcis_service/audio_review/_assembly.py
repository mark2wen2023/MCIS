"""Shared internal assembly with fixed strict legacy/generation profiles."""
import json
import threading
from collections import defaultdict
from ..evidence_intake.router import authorize
from ..evidence_intake.parser import canonical, sha
from ..working_records_archive.service import full_access
from research.media_archive import preflight, generation_inventory
from research.media_archive.generation_format import validate as validate_v2, FORMAT as V2
from research.media_archive.contract import FORMAT, need
from research.media_archive.byte_consistency import pcm, check_audio_members
from .tasks import verify_task_binding

BASE_TABLES={'cases','vessels','track_points','environment_observations',
             'evidence_items','custody_events','audit_events','access_policies',
             'audio_review_revisions','audio_asr_tasks'}


def _build(ctx, session, case_id, profile, load_receipt):
    """Read once per receipt within caller transaction; return memory only, never approval."""
    need(profile in ('legacy','generation'), 'unknown assembly profile')
    need(session.get_bind().dialect.name=='sqlite', 'SQLite candidate only')
    need(not session.new and not session.dirty and not session.deleted, 'flush caller changes before extraction')
    proof=session.info.get('_mcis_reserved_writer')
    connection=session.connection()
    need(isinstance(proof,tuple) and len(proof)==3 and proof[0] is session.get_transaction() and
         proof[1] is connection and proof[2] is threading.current_thread() and
         connection.connection.driver_connection.in_transaction, 'caller reserved writer proof required')
    # Reuse existing intake and full-archive access checks; do not expose all audit
    # rows merely because a caller may edit an audio note.
    authorize(ctx,session,case_id)
    full_access(session,ctx,case_id)
    scanner=preflight.scan if profile=='legacy' else generation_inventory.scan
    inventory=scanner(connection.connection.driver_connection,case_id)
    allowed=BASE_TABLES if profile=='legacy' else BASE_TABLES | {'audio_task_generations','audio_task_observations'}
    rows=inventory['rows']
    need(not any(v for t,v in rows.items() if t not in allowed), 'unsupported case state; no partial candidate')
    groups=defaultdict(list)
    for row in rows.get('audio_review_revisions',[]):groups[row['run_id']].append(row)
    tasks={r['task_id']:json.loads(r['doc']) for r in rows.get('audio_asr_tasks',[])}
    need(bool(groups) and bool(tasks), 'local audio-v3 task records required')
    need(all(t['status']=='succeeded' for t in tasks.values()), 'unfinished/unknown task must be resolved separately, not dropped')
    for revisions in groups.values():
        initial=json.loads(min(revisions,key=lambda r:r['revision'])['doc'])
        need(initial.get('artifactTaskId') in tasks and initial.get('machineDraft',{}).get('version')==3,
             'only captured local-task v3; imported/older records unsupported')
        verify_task_binding(session,case_id,initial)
    index=dict(format=FORMAT,caseId=case_id,restoreReady=False,taskPolicy='inactive-history-never-execute',
               members={},sources=[],runs=[],tasks=[],audit=[])
    payloads={};cache={};used_evidence=set();total=0
    def put(name,value):
        nonlocal total
        need(name not in payloads, 'duplicate member')
        raw=value if isinstance(value,bytes) else canonical(value)
        total+=len(raw)
        need(len(raw)<=16*1024*1024 and total<=64*1024*1024 and len(payloads)<512, 'candidate budget')
        payloads[name]=raw;index['members'][name]={'sha256':sha(raw),'size':len(raw)}
        return name
    def source(digest):
        if digest not in cache:
            found=load_receipt(ctx,session,case_id,digest)
            need(found is not None, 'missing registered source')
            receipt,raw=found
            # load_receipt already reuses case policy and validates supplied original.
            clock=pcm(raw);sid='source-'+str(len(cache))
            need(receipt['sourceSha256']==sha(raw)==receipt['evidence']['currentSha256'], 'source version')
            record=dict(id=sid,caseId=case_id,kind='audio',evidenceId=receipt['evidenceId'],
                        receiptMember=put(sid+'-receipt',receipt),originalMember=put(sid+'-original',raw),
                        registeredSha256=receipt['sourceSha256'],currentSha256=sha(raw),location=clock)
            index['sources'].append(record);cache[digest]=sid;used_evidence.add(receipt['evidenceId'])
        return cache[digest]
    for event in sorted(rows['audit_events'],key=lambda r:r['seq']):
        index['audit'].append(dict(caseId=case_id,seq=event['seq'],member=put('audit-'+str(event['seq']),event['line'].encode())))
    links={(r['runId'],r['revision']):r['auditSeq'] for r in inventory['revisionAuditLinks'] if r['kind']=='audio'}
    for n,(run_id,revisions) in enumerate(sorted(groups.items())):
        revisions.sort(key=lambda r:r['revision']);initial=json.loads(revisions[0]['doc'])
        task_id=initial['artifactTaskId'];task=tasks[task_id];sid=source(initial['audioReceipt'])
        stem='run-'+str(n);machine=initial['machineDraft'];raw=task['raw']
        initial_member=put(stem+'-initial',initial)
        revision_members=[dict(revision=0,member=initial_member,auditSeq=links[run_id,0])]
        for row in revisions[1:]:
            rev=row['revision']
            revision_members.append(dict(revision=rev,member=put(stem+'-revision-'+str(rev),json.loads(row['doc'])),auditSeq=links[run_id,rev]))
        index['runs'].append(dict(id=run_id,caseId=case_id,sourceId=sid,initialMember=initial_member,
            machineMember=put(stem+'-machine',machine),rawMember=put(stem+'-raw',raw),
            recognizerMember=put(stem+'-recognizer',{k:raw[k] for k in ('modelRevision','modelWeightsSha256','versions','parameters')}),
            historyStatus='captured-from-initial',revisions=revision_members,taskId=task_id))
        audit_seqs=[e['seq'] for e in rows['audit_events'] if e['command']==task_id and e['action'] in ('asr.task.start','asr.task.succeeded')]
        index['tasks'].append(dict(id=task_id,caseId=case_id,sourceId=sid,recordMember=put(stem+'-task',task),
            recordedStatus=task['status'],runId=run_id,auditSeqs=audit_seqs,executionPolicy='never'))
    need(used_evidence=={r['key'] for r in rows['evidence_items']}, 'additional evidence needs its own complete extraction; not dropped')
    checked=check_audio_members(index,payloads)
    if profile=='legacy':
        return dict(index=index,payloads=payloads,nativeInventory=inventory,checks=checked,
                    export_allowed=False,restore_ready=False,task_execution_allowed=False,
                    scope='internal-audio-v3-component-not-a-complete-case-package')
    # Preserve canonical complete row projections as explicit v2 members.
    base=index
    envelope=dict(format=V2,caseId=case_id,archiveReady=False,base=base,
                  members=dict(base['members']),generations=[],observations=[])
    def history_member(name, row):
        nonlocal total
        raw=canonical(row);total+=len(raw)
        need(name not in payloads and len(raw)<=16*1024*1024 and total<=64*1024*1024 and len(payloads)<512,'history member budget')
        payloads[name]=raw;envelope['members'][name]={'sha256':sha(raw),'size':len(raw)}
        return name
    for n,row in enumerate(sorted(rows['audio_task_generations'],key=lambda r:r['generation_id'])):
        record={k:row[k] for k in ('case_id','generation_id','task_id')};record['doc']=json.loads(row['doc'])
        envelope['generations'].append(history_member('generation-'+str(n),record))
    for n,row in enumerate(sorted(rows['audio_task_observations'],key=lambda r:(r['generation_id'],r['ordinal']))):
        record={k:row[k] for k in ('case_id','generation_id','ordinal')};record['doc']=json.loads(row['doc'])
        envelope['observations'].append(history_member('observation-'+str(n),record))
    generation_checks=validate_v2(envelope,payloads)
    return dict(index=envelope,payloads=payloads,nativeInventory=inventory,checks=checked,generationChecks=generation_checks,
                export_allowed=False,restore_ready=False,task_execution_allowed=False,
                scope='internal-audio-v3-component-not-a-complete-case-package')
