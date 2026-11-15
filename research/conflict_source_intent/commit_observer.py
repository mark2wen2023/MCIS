"""Durable research operation/commit observation; no publication or product readiness.
One owned directory/database, retained on exit. Does not accept a product DB/root.
"""
import hashlib
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
from uuid import uuid4
from sqlalchemy import MetaData,Table,Column,String,Integer,select,inspect,text
from mcis_service.db import Database
from .temporary_continuation import TemporaryContinuingConflictStore,_meta as business_meta,_ALLOWED
from .archive_envelope_v2 import inspect_envelope
from .archive_receipts_v2 import require

_meta=MetaData()
_claim=Table('offline_restore_operation',_meta,Column('operation_id',String,primary_key=True),
    Column('case_id',String,nullable=False,unique=True),Column('source_sha256',String,nullable=False),
    Column('attempts',Integer,nullable=False))
_commit=Table('offline_restore_commit',_meta,Column('operation_id',String,primary_key=True),
    Column('case_id',String,nullable=False),Column('source_sha256',String,nullable=False),
    Column('revision_count',Integer,nullable=False),Column('receipt_count',Integer,nullable=False))
_AUX={_claim.name,_commit.name}

class DurableObservedConflictStore(TemporaryContinuingConflictStore):
    def __init__(self):
        self.directory=Path(tempfile.mkdtemp(prefix='mcis-commit-observer-'))
        self.db_path=self.directory/'research.sqlite'
        self.db=Database('sqlite:///'+str(self.db_path))
        self.db.create_all();business_meta.create_all(self.db.engine);_meta.create_all(self.db.engine)
        self.closed=False;self._attempt=None

    def __exit__(self,*exc):
        # Always retain objects; no destructor/finalizer cleanup, even on error.
        self.db.engine.dispose();self.closed=True

    @staticmethod
    def _inventory(s,*,empty=False):
        for name in inspect(s.connection()).get_table_names():
            if name.startswith('sqlite_') or name in _AUX:continue
            if not empty and name in _ALLOWED:continue
            require(s.execute(text('SELECT 1 FROM "'+name.replace('"','""')+'" LIMIT 1')).first() is None,
                    'target not empty' if empty else 'unsupported stored state')

    def claim(self,raw,*,expected_sha256):
        self._open();summary=inspect_envelope(raw,expected_sha256=expected_sha256)
        operation_id=str(uuid4())
        with self.db.session() as s:
            s.connection().exec_driver_sql('BEGIN IMMEDIATE')
            self._inventory(s,empty=True)
            require(s.execute(select(_claim)).first() is None,'operation already claimed; inspect only')
            s.execute(_claim.insert().values(operation_id=operation_id,case_id=summary.case_id,
                      source_sha256=expected_sha256,attempts=0))
        return operation_id

    def restore(self,*args,**kwargs):
        raise ValueError('use restore_claimed once; no implicit operation or retry')

    def restore_claimed(self,operation_id,raw,*,fault_after=None,lose_response=False):
        self._open()
        with self.db.session() as s:
            s.connection().exec_driver_sql('BEGIN IMMEDIATE')
            row=s.execute(select(_claim).where(_claim.c.operation_id==operation_id)).mappings().first()
            require(row is not None and row['attempts']==0,'operation already attempted or absent; inspect only')
            require(hashlib.sha256(raw).hexdigest()==row['source_sha256'],'operation source mismatch')
            s.execute(_claim.update().where(_claim.c.operation_id==operation_id).values(attempts=1))
            identity=dict(row)
        self._attempt=identity
        try:
            super().restore(raw,expected_sha256=identity['source_sha256'],fault_after=fault_after)
        finally:self._attempt=None
        if lose_response:raise RuntimeError('SYNTHETIC_RESPONSE_LOST_AFTER_COMMIT')
        return observe(self.db_path,operation_id) # Never returns restore_ready=true.

    def _export(self,s):
        raw=super()._export(s)
        if self._attempt is not None:
            a=self._attempt
            summary=inspect_envelope(raw,expected_sha256=hashlib.sha256(raw).hexdigest())
            # Same session/transaction as restored business rows and inactive receipts.
            s.execute(_commit.insert().values(operation_id=a['operation_id'],case_id=a['case_id'],
                source_sha256=a['source_sha256'],revision_count=summary.revision_count,
                receipt_count=summary.receipt_count))
        return raw


def observe(db_path,operation_id):
    """Fresh read-only SQLite snapshot. No retry, recovery mutation, or file access.

    Marker proves only a matching DB restore transaction is visible, not that files
    are published, current business contents intact, or a product case is usable.
    """
    result={'status':'unknown','dbCommitObserved':False,'restore_ready':False,
            'retryAllowed':False,'deleteAllowed':False}
    try:
        uri=Path(db_path).absolute().as_uri()+'?mode=ro'
        with closing(sqlite3.connect(uri,uri=True,timeout=1)) as conn:
            conn.execute('PRAGMA query_only=ON');conn.execute('BEGIN')
            claim=conn.execute('SELECT case_id,source_sha256,attempts FROM offline_restore_operation WHERE operation_id=?',(operation_id,)).fetchone()
            marker=conn.execute('SELECT case_id,source_sha256,revision_count,receipt_count FROM offline_restore_commit WHERE operation_id=?',(operation_id,)).fetchone()
            if claim is None:return result
            if marker is None:return {**result,'status':'claimed_unattempted' if claim[2]==0 else 'unknown_no_commit_marker'}
            if claim[2]!=1 or tuple(marker[:2])!=tuple(claim[:2]):return result
            stored=conn.execute('SELECT source_sha256,source_bytes FROM offline_conflict_receipt WHERE case_id=?',(claim[0],)).fetchall()
            if len(stored)!=1 or stored[0][0]!=claim[1] or hashlib.sha256(stored[0][1]).hexdigest()!=claim[1]:return result
            if conn.execute('SELECT count(*) FROM cases WHERE case_id=? AND key=?',(claim[0],claim[0])).fetchone()[0]!=1:return result
            if conn.execute('SELECT count(*) FROM conflict_source_receipts').fetchone()[0]!=0:return result
            return {**result,'status':'db_committed_publication_unverified','dbCommitObserved':True}
    except (sqlite3.Error,OSError,ValueError,TypeError):return result
