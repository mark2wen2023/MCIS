"""Disposable SQLite-only restoration research. Never accepts an application DB/root."""
from contextlib import AbstractContextManager
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import io
import json
import zipfile
from sqlalchemy import MetaData, Table, Column, String, LargeBinary, select, inspect, text
from ..db import Database
from ..cases.models import CaseRow, VesselRow
from ..evidence.models import EvidenceRow, CustodyEventRow
from ..evidence.service import KIND_BY_ACTION
from ..audit.models import AuditEventRow
from ..audit.service import append_raw_line
from ..timeline.models import ConflictRow
from ..timeline.revisions import ConflictRevision
from ..redaction.models import AccessPolicyRow
from ..package.mcase import CASE_FIELDS, manifest_json
from ..package_intake.parser import read_bounded, strict_json
from .conflicts import ConflictArchiveInvalid, require
from .conflict_envelope import inspect_envelope, PATH, MIRROR, VERSION
from .validation import canonical

# Separate metadata: these tables are NEVER registered with product Base/create_all.
_meta = MetaData()
_members = Table('offline_conflict_members',_meta,Column('path',String,primary_key=True),Column('data',LargeBinary,nullable=False))
_receipt = Table('offline_conflict_receipt',_meta,Column('case_id',String,primary_key=True),Column('source_sha256',String,nullable=False),Column('source_bytes',LargeBinary,nullable=False))
_ALLOWED = {'cases','vessels','evidence_items','custody_events','audit_events',ConflictRow.__tablename__,
            'conflict_revisions','access_policies',_members.name,_receipt.name}
_PHASES = {'current','journal','audit','objects','before_commit'}


class TemporaryConflictStore(AbstractContextManager):
    """Fresh directory + DB owned by this context, no caller-selected storage path.

    All restored bytes and original source ZIP stay in SQLite BLOBs, in the same
    transaction as business rows. This is not product file-layout restoration.
    """
    def __init__(self):
        self._temp = TemporaryDirectory(prefix='mcis-conflict-research-')
        self.db = Database('sqlite:///'+str(Path(self._temp.name)/'research.sqlite'))
        self.db.create_all();_meta.create_all(self.db.engine)
        self.closed = False

    def __exit__(self,*exc):
        self.db.engine.dispose();self._temp.cleanup();self.closed = True

    def _open(self):
        require(not self.closed,'temporary store closed')

    @staticmethod
    def _checkpoint(phase,fault_after):
        if phase == fault_after: raise RuntimeError('SYNTHETIC_RESTORE_FAILURE:'+phase)

    @staticmethod
    def _inventory(s, *, empty=False):
        for name in inspect(s.connection()).get_table_names():
            if name.startswith('sqlite_'):continue
            if not empty and name in _ALLOWED:continue
            quoted='"'+name.replace('"','""')+'"'
            require(s.execute(text('SELECT 1 FROM '+quoted+' LIMIT 1')).first() is None,
                    'target not empty' if empty else 'unsupported stored state')

    def restore(self,raw,*,expected_sha256,fault_after=None):
        self._open();require(fault_after is None or fault_after in _PHASES,'unknown fault hook')
        # Revalidate exact immutable bytes; callers cannot pass an inspection as authority.
        summary = inspect_envelope(raw,expected_sha256=expected_sha256)
        files = read_bounded(raw);member = strict_json(files[PATH]);cid = summary.case_id
        with self.db.session() as s:
            s.connection().exec_driver_sql('BEGIN IMMEDIATE')
            self._inventory(s,empty=True)
            case={**strict_json(files['case.json']),**strict_json(files['case.ext.json'])}
            s.add(CaseRow(case_id=cid,key=cid,doc=case))
            for model,path,key in ((VesselRow,'vessels.json','vesselId'),(EvidenceRow,'evidence/index.json','evidenceId')):
                for doc in strict_json(files[path]):s.add(model(case_id=cid,key=doc[key],doc=doc))
            s.add(AccessPolicyRow(case_id=cid,key='policy',doc=strict_json(files['access-policy.json'])))
            for row in member['records']:
                s.add(ConflictRow(case_id=cid,key=row['key'],doc=row['doc'],created_utc=row['createdUtc'],updated_utc=row['updatedUtc']))
            s.flush();self._checkpoint('current',fault_after)
            for row in member['records']:
                for revision in row['revisions']:
                    s.add(ConflictRevision(case_id=cid,conflict_id=row['key'],revision=revision['revision'],doc=revision))
            s.flush();self._checkpoint('journal',fault_after)
            for line in files['audit/audit.jsonl'].decode('utf-8').splitlines():
                rec=json.loads(line);append_raw_line(s,cid,rec,line,rec['seq'],rec['prev'])
            for line in files['audit/custody.jsonl'].decode('utf-8').splitlines():
                rec=json.loads(line);kind=KIND_BY_ACTION[rec['action']]
                s.add(CustodyEventRow(case_id=cid,seq=rec['seq'],evidence_id=rec['evidence_id'],kind=kind,
                    utc=rec['utc'],operator=rec['operator'],sha256=rec.get('sha256',''),
                    previous_sha256=rec['before'] if kind in ('Change','Verify') else '',detail=rec.get('detail',''),
                    verify_matched=(rec.get('result')=='match') if kind=='Verify' else (rec.get('result')=='needs_review') if kind=='Review' else None,
                    prev_line_hash=rec['prev'],line=line))
            s.flush();self._checkpoint('audit',fault_after)
            for path,data in files.items():s.execute(_members.insert().values(path=path,data=data))
            s.execute(_receipt.insert().values(case_id=cid,source_sha256=expected_sha256,source_bytes=raw))
            self._checkpoint('objects',fault_after)
            # Rebuild from inserted database rows before commit; do not trust a ZIP copy.
            rebuilt=self._export(s)
            require(inspect_envelope(rebuilt,expected_sha256=hashlib.sha256(rebuilt).hexdigest()).record_count==summary.record_count,'restore reconstruction')
            self._checkpoint('before_commit',fault_after)
        return summary  # restore_ready remains false for product restoration.

    def _export(self,s):
        self._inventory(s)
        receipts=s.execute(select(_receipt)).mappings().all()
        require(len(receipts)==1,'missing/ambiguous temporary receipt')
        receipt=receipts[0];cid=receipt['case_id']
        require(hashlib.sha256(receipt['source_bytes']).hexdigest()==receipt['source_sha256'],'stored source checksum')
        original=read_bounded(receipt['source_bytes'])
        stored=dict(s.execute(select(_members.c.path,_members.c.data)).all())
        require(stored==original,'stored source members differ')
        files=dict(stored);files.pop('manifest.json')
        originals=strict_json(original[PATH]);original_rows={r['key']:r for r in originals['records']}
        case=s.scalars(select(CaseRow)).all()
        require(len(case)==1 and case[0].case_id==cid and case[0].key==cid,'stored case identity')
        doc=case[0].doc
        require(canonical(doc)==canonical({**strict_json(original['case.json']),**strict_json(original['case.ext.json'])}),'stored case differs')
        require(set(doc)==set(strict_json(original['case.json']))|set(strict_json(original['case.ext.json'])),'case fields changed')
        files['case.json']=canonical({k:doc[k] for k in CASE_FIELDS})
        files['case.ext.json']=canonical({k:doc[k] for k in strict_json(original['case.ext.json'])})
        for model,path in ((VesselRow,'vessels.json'),(EvidenceRow,'evidence/index.json')):
            rows=s.scalars(select(model).order_by(model.id)).all()
            id_field='vesselId' if model is VesselRow else 'evidenceId'
            require(all(r.case_id==cid and r.key==r.doc[id_field] for r in rows),'foreign/stale stored registration key')
            require(canonical([r.doc for r in rows])==canonical(strict_json(original[path])),'stored registration differs')
            files[path]=canonical([r.doc for r in rows])
        policies=s.scalars(select(AccessPolicyRow)).all()
        require(len(policies)==1 and policies[0].case_id==cid and policies[0].key=='policy','stored policy')
        files['access-policy.json']=canonical(policies[0].doc)
        require(files['access-policy.json']==canonical(strict_json(original['access-policy.json'])),'stored policy differs')
        rows=s.scalars(select(ConflictRow).order_by(ConflictRow.id)).all()
        require(len(rows)==len(original_rows) and all(r.case_id==cid and r.key in original_rows for r in rows),'stored conflict inventory')
        revisions=s.scalars(select(ConflictRevision).order_by(ConflictRevision.conflict_id,ConflictRevision.revision)).all()
        require(all(r.case_id==cid and r.conflict_id in original_rows for r in revisions),'orphan/foreign journal')
        records=[]
        for row in rows:
            journal=[r for r in revisions if r.conflict_id==row.key]
            require(all(r.revision==r.doc['revision'] and r.conflict_id==r.doc['conflictId'] for r in journal),'journal columns')
            records.append(dict(key=row.key,createdUtc=row.created_utc,updatedUtc=row.updated_utc,doc=row.doc,
                coverage=original_rows[row.key]['coverage'],revisions=[r.doc for r in journal]))
        member=dict(format='MCIS-CONFLICT-ARCHIVE',version=1,caseId=cid,records=records)
        # This candidate restores a frozen snapshot, not an editable/live clone.
        require(canonical(member)==canonical(originals),'restored journal/current differs from source')
        files[PATH]=canonical(member);files[MIRROR]=canonical({'conflicts':[r['doc'] for r in records]})
        for model,path in ((AuditEventRow,'audit/audit.jsonl'),(CustodyEventRow,'audit/custody.jsonl')):
            events=s.scalars(select(model).order_by(model.seq)).all()
            require(all(r.case_id==cid for r in events),'foreign stored audit/custody')
            for row in events:
                rec=json.loads(row.line)
                require(row.seq==rec['seq'] and row.utc==rec['utc'] and row.operator==rec['operator'],'audit columns')
                if model is AuditEventRow:
                    require(all(getattr(row,k)==rec.get(k,'') for k in ('role','action','category','command','before','after','entity_type','entity_id')) and row.prev_hash==rec['prev'],'audit row association')
                else:
                    require(row.evidence_id==rec['evidence_id'] and row.kind==KIND_BY_ACTION[rec['action']] and row.prev_line_hash==rec['prev'] and row.sha256==rec.get('sha256',''),'custody row association')
                    expected_verify=(rec.get('result')=='match') if row.kind=='Verify' else (rec.get('result')=='needs_review') if row.kind=='Review' else None
                    require(row.detail==rec.get('detail','') and row.previous_sha256==(rec['before'] if row.kind in ('Change','Verify') else '') and row.verify_matched is expected_verify,'custody derived columns')
            files[path]=(''.join(r.line+'\n' for r in events)).encode()
            # Normal LF final terminator may be added; original line bytes stay exact.
            require(files[path].decode().splitlines()==original[path].decode().splitlines(),'original audit prefix changed')
        manifest=manifest_json(cid,files,strict_json(original['manifest.json'])['createdAtUtc'],VERSION)
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
            for path,data in files.items():z.writestr(path,data)
            z.writestr('manifest.json',manifest)
        raw=output.getvalue();inspect_envelope(raw,expected_sha256=hashlib.sha256(raw).hexdigest())
        return raw

    def export_candidate(self):
        self._open()
        with self.db.session() as s:
            s.connection().exec_driver_sql('BEGIN IMMEDIATE')
            return self._export(s)
