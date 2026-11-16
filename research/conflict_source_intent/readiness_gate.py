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


def _entry_decision(session, case_id, *, expected_database_id=None, explicit_legacy=False):
    # Lazy import: migration store subclasses this module's pending store.
    from .migration_protocol import classify, TABLES
    try:
        marked = bool(TABLES & set(inspect(session.connection()).get_table_names()))
        if expected_database_id is not None or explicit_legacy or marked:
            return classify(session, case_id, expected_database_id=expected_database_id,
                            explicit_legacy=explicit_legacy)
        # Backwards compatibility ONLY for unmarked research callers. Deployment
        # must retain/pass expected identity to distinguish total metadata loss.
        return decision(session, case_id)
    except SQLAlchemyError as exc:
        raise ReadinessUnknown('readiness unavailable; no success') from exc


def scoped_call(session, case_id, operation, *args, expected_database_id=None,
                explicit_legacy=False, **kwargs):
    state = _entry_decision(session, case_id, expected_database_id=expected_database_id,
                            explicit_legacy=explicit_legacy)
    if state == 'unknown':
        raise ReadinessUnknown('readiness unknown; no business call')
    if state != 'legacy_policy_required':
        raise CaseNotReady('restoration pending; not authorized for use by readiness')
    return operation(session, case_id, *args, **kwargs)


def load_case(session, case_id, *, expected_database_id=None, explicit_legacy=False):
    return scoped_call(session, case_id, cases.load_case,
                       expected_database_id=expected_database_id, explicit_legacy=explicit_legacy)


def list_cases(session, *, expected_database_id=None, explicit_legacy=False):
    # Check schema/identity even for an empty database; no false empty success.
    initial = _entry_decision(session, '', expected_database_id=expected_database_id,
                              explicit_legacy=explicit_legacy)
    # A marked, well-formed DB classifies an unregistered identifier as unknown.
    # Therefore validate actual rows below; empty-list validation uses a scoped
    # protocol identity check rather than treating that sentinel as an entity.
    rows = cases.list_cases(session)
    if not rows and (initial == 'unknown' or expected_database_id is not None):
        from .migration_protocol import REQUIRED
        try:
            names = set(inspect(session.connection()).get_table_names())
            marker = session.execute(text('SELECT singleton,version,database_id FROM offline_restore_protocol')).all() if REQUIRED <= names else []
            if explicit_legacy or not expected_database_id or marker != [(1,1,expected_database_id)]:
                raise ReadinessUnknown('readiness unknown; no empty successful listing')
            session.execute(text('SELECT case_id FROM offline_restore_legacy_cases LIMIT 0'))
            ledger_ids = set()
            for table in ('offline_restore_operation', 'offline_restore_commit', 'offline_restore_readiness'):
                session.execute(text('SELECT case_id,operation_id,source_sha256 FROM '+table+' LIMIT 0'))
                ledger_ids.update(session.execute(text('SELECT DISTINCT case_id FROM '+table)).scalars())
            for case_id in ledger_ids:
                if _entry_decision(session, case_id, expected_database_id=expected_database_id) == 'unknown':
                    raise ReadinessUnknown('orphan or inconsistent ledger; no empty successful listing')
        except SQLAlchemyError as exc:
            raise ReadinessUnknown('readiness unknown; no empty successful listing') from exc
    result = []
    for row in rows:
        state = _entry_decision(session, row['caseId'], expected_database_id=expected_database_id,
                                explicit_legacy=explicit_legacy)
        if state == 'unknown':
            raise ReadinessUnknown('readiness unknown; no partial successful listing')
        if state == 'legacy_policy_required':
            result.append(row)
    return result


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
