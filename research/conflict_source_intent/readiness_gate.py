"""Isolated durable pending gate. No ready promotion or product route wiring."""
from sqlalchemy import MetaData, Table, Column, String, select, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from mcis_service.cases import service as cases
from .commit_observer import DurableObservedConflictStore, _AUX
from .temporary_continuation import _ALLOWED
from .archive_receipts_v2 import require

_meta = MetaData()
_pending = Table('offline_restore_readiness', _meta,
    Column('case_id', String, primary_key=True),
    Column('operation_id', String, nullable=False, unique=True),
    Column('source_sha256', String, nullable=False),
    Column('state', String, nullable=False))


class CaseNotReady(RuntimeError):
    pass


class ReadinessUnknown(RuntimeError):
    pass


def decision(session, case_id):
    """Not authorization. Caller retains the same transaction for business work.

    Every explicit operation remains held, regardless of any claimed ready label.
    Only old/unmanaged cases pass through to their normal policies.
    """
    try:
        names=set(inspect(session.connection()).get_table_names())
        claimed=False; marked=False
        if 'offline_restore_operation' in names:
            claimed=session.execute(text('SELECT 1 FROM offline_restore_operation WHERE case_id=:cid'),{'cid':case_id}).first() is not None
        if _pending.name in names:
            marked=session.execute(select(_pending.c.case_id).where(_pending.c.case_id==case_id)).first() is not None
        return 'hold' if claimed or marked else 'legacy_policy_required'
    except SQLAlchemyError as exc:
        raise ReadinessUnknown('readiness unavailable; no retry/delete or success') from exc


def scoped_call(session, case_id, operation, *args, **kwargs):
    if decision(session,case_id)!='legacy_policy_required':
        raise CaseNotReady('restoration pending; not authorized for use by readiness')
    return operation(session,case_id,*args,**kwargs)


def load_case(session,case_id):
    return scoped_call(session,case_id,cases.load_case)


def list_cases(session):
    # Never convert unknown DB state into a misleading empty successful listing.
    return [row for row in cases.list_cases(session)
            if decision(session,row['caseId'])=='legacy_policy_required']


class PendingReadinessStore(DurableObservedConflictStore):
    def __init__(self):
        super().__init__();_meta.create_all(self.db.engine)

    @staticmethod
    def _inventory(s,*,empty=False):
        for name in inspect(s.connection()).get_table_names():
            if name.startswith('sqlite_') or name in _AUX:continue
            if not empty and (name in _ALLOWED or name==_pending.name):continue
            require(s.execute(text('SELECT 1 FROM "'+name.replace('"','""')+'" LIMIT 1')).first() is None,
                    'target not empty' if empty else 'unsupported stored state')

    def _export(self,s):
        raw=super()._export(s)
        if self._attempt is not None:
            a=self._attempt
            # Same transaction as rows, inactive history and the commit marker.
            s.execute(_pending.insert().values(case_id=a['case_id'],operation_id=a['operation_id'],
                source_sha256=a['source_sha256'],state='waiting_publication'))
        return raw
