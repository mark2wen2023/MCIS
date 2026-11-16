"""Internal same-transaction linkage checks; not archive eligibility or provenance proof."""
import threading
from sqlalchemy import select
from research.media_archive.contract import need
from ..evidence_intake.router import authorize
from ..working_records_archive.service import full_access
from ..audit.models import AuditEventRow
from ..common.csjson import sha256_utf8
from .generation import Generation, Observation
from .tasks import Task


def validate_rows(case_id, tasks, generations, observations, audits):
    """Pure structural check for complete same-case inputs; adapter supplies DB inventory."""
    def index(rows, key):
        out = {}
        for row in rows:
            need(row['case_id'] == case_id and row[key] not in out, 'duplicate or inconsistent case binding')
            out[row[key]] = row
        return out
    ts=index(tasks,'task_id');gs=index(generations,'generation_id');events=index(audits,'seq')
    need(bool(ts), 'no task inventory')
    by_task={}
    for g in gs.values():
        tid=g['task_id'];doc=g['doc']
        need(tid in ts and tid not in by_task, 'orphan or duplicate generation')
        need(type(doc) is dict and set(doc)=={'protocol','source'} and doc['protocol']=='audio-generation-observation/v1', 'generation protocol')
        task=ts[tid]['doc']
        need(task.get('taskId')==tid and task.get('caseId')==case_id and doc['source']==task.get('source'), 'task/source binding')
        by_task[tid]=g
    need(set(by_task)==set(ts), 'generation missing: legacy or lost history unknown; do not backfill')
    groups={gid:{} for gid in gs};used=set();links=[]
    for o in observations:
        gid=o['generation_id'];ordinal=o['ordinal']
        need(o['case_id']==case_id and gid in gs, 'orphan observation')
        need(type(ordinal) is int and ordinal in (0,1) and ordinal not in groups[gid], 'duplicate/unknown observation ordinal')
        groups[gid][ordinal]=o['doc']
    for tid,g in by_task.items():
        task=ts[tid]['doc'];status=task.get('status');obs=groups[g['generation_id']]
        need(status in ('running_or_unknown','succeeded','failed','interrupted_unknown'), 'unknown task status')
        need(set(obs)==({0} if status=='running_or_unknown' else {0,1}), 'missing/inconsistent observations')
        expected={0:('registration-recorded-before-dispatch','asr.task.start',tid)}
        if status=='succeeded':
            need(type(task.get('runId')) is str and bool(task['runId']), 'success missing run')
            expected[1]=('result-converted-and-source-rechecked','asr.task.succeeded',task['runId'])
        elif status!='running_or_unknown':
            need(task.get('runId') is None,'unfinished task has run')
            expected[1]=('timeout-observed' if status=='interrupted_unknown' else 'execution-or-conversion-exception-observed','asr.task.incomplete',tid)
        else:
            need(task.get('runId') is None,'running task has run')
        seqs=[]
        for ordinal,(label,action,entity) in expected.items():
            doc=obs[ordinal]
            need(type(doc) is dict and set(doc)=={'event','auditSeq','auditLineSha256','writers','manifestStatus','archiveReady'},'observation fields')
            need(doc['event']==label and doc['writers']=='unknown' and doc['manifestStatus']=='not-captured' and doc['archiveReady'] is False,'observation claims')
            seq=doc['auditSeq'];need(type(seq) is int and seq in events and seq not in used,'missing or reused audit')
            e=events[seq]
            need(e['action']==action and e['command']==tid and e['entity_id']==entity and e['category']=='Evidence' and e['operator']==task.get('operator') and e['role']==task.get('role'),'audit binding')
            need(sha256_utf8(e['line'])==doc['auditLineSha256'],'audit digest')
            import json
            line=json.loads(e['line'])
            need(all(line.get(k)==e[k] for k in ('seq','action','command','entity_id','category','operator','role')),'audit line columns')
            used.add(seq);seqs.append(seq)
            links.append({'taskId':tid,'generationId':g['generation_id'],'ordinal':ordinal,'auditSeq':seq})
        need(seqs==sorted(seqs),'observation audit ordering')
    lifecycle={e['seq'] for e in events.values() if e['action'] in ('asr.task.start','asr.task.succeeded','asr.task.incomplete')}
    need(used==lifecycle,'unmapped lifecycle audit')
    return {'links':links,'associationsConsistent':True,'archiveReady':False,'restore_ready':False,
            'writers':'unknown','historicalProof':False,'scope':'generation-observation-associations-only'}


def inspect_case(ctx, session, case_id):
    need(session.get_bind().dialect.name=='sqlite' and not session.new and not session.dirty and not session.deleted,'clean SQLite session required')
    connection=session.connection();proof=session.info.get('_mcis_reserved_writer')
    need(isinstance(proof,tuple) and len(proof)==3 and proof[0] is session.get_transaction() and proof[1] is connection and proof[2] is threading.current_thread() and connection.connection.driver_connection.in_transaction,'caller reserved writer required')
    authorize(ctx,session,case_id);full_access(session,ctx,case_id)
    def rows(model, keys):
        result=session.scalars(select(model).where(model.case_id==case_id).limit(10001)).all()
        need(len(result)<=10000,'row budget')
        return [{k:getattr(r,k) for k in keys} for r in result]
    return validate_rows(case_id,
        rows(Task,('case_id','task_id','doc')),
        rows(Generation,('case_id','generation_id','task_id','doc')),
        rows(Observation,('case_id','generation_id','ordinal','doc')),
        rows(AuditEventRow,('case_id','seq','action','command','entity_id','category','operator','role','line')))
