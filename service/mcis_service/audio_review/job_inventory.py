"""Internal read-only per-case job-directory observations; never cleanup or export.
Known files are checked against saved task/current registration metadata. No other
case directory is enumerated; global orphan discovery is deliberately not provided.
"""
import hashlib
import json
import os
import re
import stat
import threading
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import select
from ..evidence_intake.router import authorize
from ..working_records_archive.service import full_access
from ..evidence.models import EvidenceRow
from research.media_archive.contract import need, parse
from .tasks import Task


@contextmanager
def _directory(path):
    need(hasattr(os,'O_NOFOLLOW') and hasattr(os,'O_DIRECTORY'), 'descriptor directory support unavailable')
    fds=[]
    try:
        fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY);fds.append(fd)
        for part in Path(os.path.abspath(path)).parts[1:]:
            fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
        yield fd
    finally:
        for fd in reversed(fds):os.close(fd)


def _stamp(st):
    return st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns


def _read_member(directory,name,limit):
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_NONBLOCK',0),dir_fd=directory)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_size<=limit, 'unsupported job member')
        raw=stream.read(limit+1)
        need(len(raw)<=limit and _stamp(before)==_stamp(os.fstat(stream.fileno())), 'member changed while observed')
        return raw


def inspect_case_jobs(ctx,session,case_id):
    need(session.get_bind().dialect.name=='sqlite' and not session.new and not session.dirty and not session.deleted, 'clean SQLite session required')
    connection=session.connection();proof=session.info.get('_mcis_reserved_writer')
    need(isinstance(proof,tuple) and len(proof)==3 and proof[0] is session.get_transaction() and
         proof[1] is connection and proof[2] is threading.current_thread() and
         connection.connection.driver_connection.in_transaction, 'caller reserved writer required')
    authorize(ctx,session,case_id);full_access(session,ctx,case_id)
    tasks=session.scalars(select(Task).where(Task.case_id==case_id).order_by(Task.task_id)).all()
    observations=[]
    for row in tasks:
        doc=row.doc;item={'taskId':row.task_id,'status':doc.get('status'),'issues':[], 'members':{},
                         'currentDigestIsHistoricalProof':False}
        observations.append(item)
        if not re.fullmatch('[a-f0-9]{32}',row.task_id) or doc.get('taskId')!=row.task_id or doc.get('caseId')!=case_id:
            item['issues'].append('TASK_IDENTITY_UNRESOLVED');continue
        if doc.get('status')!='succeeded':
            item['issues'].append('TASK_NOT_CONFIRMED_SUCCESS');continue
        source=doc.get('source',{})
        evidence=session.scalars(select(EvidenceRow).where(EvidenceRow.case_id==case_id,EvidenceRow.key==source.get('evidenceId'))).first()
        expected=source.get('currentSha256')
        if (type(expected) is not str or re.fullmatch('[a-f0-9]{64}',expected) is None or
            source.get('caseId')!=case_id or source.get('registeredSha256')!=expected or evidence is None or
            evidence.doc.get('sha256')!=expected or evidence.doc.get('relativePath')!='raw/evidence-intakes/'+str(doc.get('audioReceipt'))+'/source.bin'):
            item['issues'].append('SOURCE_REGISTRATION_UNRESOLVED');continue
        try:
            # Traverse only the expected task directory; do not enumerate audio-asr-jobs.
            with _directory(ctx.settings.data_dir/'audio-asr-jobs'/row.task_id) as fd:
                before=_stamp(os.fstat(fd));names=os.listdir(fd)
                if len(names)>256:
                    item['issues'].append('DIRECTORY_INVENTORY_LIMIT');continue
                for name in sorted(set(names)-{'source.wav','raw.json'}):
                    item['issues'].append('UNCLASSIFIED_MEMBER:'+name)
                for name,limit in [('source.wav',1048576),('raw.json',262144)]:
                    if name not in names:
                        item['issues'].append('MISSING_MEMBER:'+name);continue
                    try:
                        raw=_read_member(fd,name,limit)
                        item['members'][name]={'size':len(raw),'observedSha256':hashlib.sha256(raw).hexdigest(),
                                               'historicalFileDigestVerified':False}
                        if name=='source.wav':
                            if hashlib.sha256(raw).hexdigest()!=expected:item['issues'].append('SOURCE_BYTES_DIFFER')
                        else:
                            result=parse(raw)
                            if result!=doc.get('raw') or result.get('taskId')!=row.task_id or result.get('inputSha256')!=expected:
                                item['issues'].append('RAW_RESULT_DIFFERS')
                    except (OSError,ValueError,TypeError,KeyError,AttributeError,UnicodeError,RecursionError):
                        item['issues'].append('MEMBER_UNRESOLVED:'+name)
                if before!=_stamp(os.fstat(fd)):item['issues'].append('DIRECTORY_CHANGED_DURING_OBSERVATION')
        except (OSError,ValueError):
            item['issues'].append('JOB_DIRECTORY_UNAVAILABLE')
    return {'caseId':case_id,'tasks':observations,
            'inventory_consistent':bool(tasks) and all(not r['issues'] for r in observations),
            'global_orphans_checked':False,'original_registered_file_read':False,
            'export_allowed':False,'restore_ready':False,'cleanup_allowed':False,'execution_allowed':False,
            'scope':'expected-case-job-directories-only-not-filesystem-snapshot'}
