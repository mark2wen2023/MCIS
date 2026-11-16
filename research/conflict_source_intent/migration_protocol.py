"""Isolated migration identity + conservative reopening, never product ready."""
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from .readiness_gate import PendingReadinessStore
from .publication_observer import inspect_publication

TABLES = {'offline_restore_protocol', 'offline_restore_legacy_cases'}
REQUIRED = TABLES | {'offline_restore_operation', 'offline_restore_commit', 'offline_restore_readiness'}


def activate(session, database_id, *, fail_before_marker=False):
    """Caller owns BEGIN IMMEDIATE + commit; no production DB migration hook."""
    if not isinstance(database_id, str) or not database_id.strip():
        raise ValueError('explicit database identity required')
    names = set(inspect(session.connection()).get_table_names())
    if names & TABLES:
        raise ValueError('already marked or partial protocol; inspect only')
    for table in REQUIRED - TABLES:
        if table not in names or session.execute(text('SELECT 1 FROM '+table+' LIMIT 1')).first():
            raise ValueError('missing research schema or prior operation; cannot classify legacy')
    session.execute(text('CREATE TABLE offline_restore_protocol (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL, database_id TEXT NOT NULL)'))
    session.execute(text('CREATE TABLE offline_restore_legacy_cases (case_id TEXT PRIMARY KEY)'))
    session.execute(text('INSERT INTO offline_restore_legacy_cases SELECT case_id FROM cases'))
    if fail_before_marker:
        raise RuntimeError('SYNTHETIC_MIGRATION_FAILURE')
    session.execute(text('INSERT INTO offline_restore_protocol VALUES (1,1,:identity)'), {'identity':database_id})


def classify(session, case_id, *, expected_database_id=None, explicit_legacy=False):
    """No state mutation; existing policies still apply to ordinary cases."""
    try:
        names = set(inspect(session.connection()).get_table_names())
        if explicit_legacy:
            if expected_database_id is not None or names & TABLES:
                return 'unknown'
            for table in REQUIRED - TABLES:
                if table in names and session.execute(text('SELECT 1 FROM '+table+' LIMIT 1')).first():
                    return 'unknown'
            return 'legacy_policy_required'
        if not expected_database_id or not REQUIRED <= names:
            return 'unknown'
        rows = session.execute(text('SELECT singleton,version,database_id FROM offline_restore_protocol')).all()
        if rows != [(1,1,expected_database_id)]:
            return 'unknown'
        bindings = []
        for table in ('offline_restore_operation','offline_restore_commit','offline_restore_readiness'):
            bindings.append(session.execute(text('SELECT operation_id,source_sha256 FROM '+table+' WHERE case_id=:cid'),{'cid':case_id}).all())
        if any(bindings):
            # Every operation is held; inconsistent/missing claim is unknown.
            if len(bindings[0]) != 1 or any(len(b)>1 or (b and b != bindings[0]) for b in bindings[1:]):
                return 'unknown'
            if bool(bindings[1]) != bool(bindings[2]):
                return 'unknown'
            return 'hold'
        legacy = session.execute(text('SELECT 1 FROM offline_restore_legacy_cases WHERE case_id=:cid'),{'cid':case_id}).first()
        if legacy:
            return 'legacy_policy_required'
        if 'offline_normal_case_registration' not in names:
            return 'unknown'
        registered = session.execute(text('SELECT database_id,audit_seq FROM offline_normal_case_registration WHERE case_id=:cid'), {'cid':case_id}).all()
        if len(registered) != 1 or registered[0][0] != expected_database_id:
            return 'unknown'
        case = session.execute(text('SELECT 1 FROM cases WHERE case_id=:cid AND key=:cid'), {'cid':case_id}).all()
        event = session.execute(text("SELECT 1 FROM audit_events WHERE case_id=:cid AND seq=:seq AND action='case.create' AND entity_type='case' AND entity_id=:cid"), {'cid':case_id,'seq':registered[0][1]}).all()
        return 'legacy_policy_required' if len(case)==1 and len(event)==1 else 'unknown'
    except SQLAlchemyError:
        return 'unknown'


class MigratingResearchStore(PendingReadinessStore):
    """Creates its own retained temporary DB; cannot take a production DB path."""
    @staticmethod
    def _inventory(s, *, empty=False):
        # Reuse existing inventory rules, excluding protocol metadata without
        # modifying the parent module global table allowlist.
        from .commit_observer import _AUX
        from .temporary_continuation import _ALLOWED
        from .archive_receipts_v2 import require
        for name in inspect(s.connection()).get_table_names():
            if name.startswith('sqlite_') or name in _AUX | TABLES:
                continue
            if not empty and (name in _ALLOWED or name=='offline_restore_readiness'):
                continue
            require(s.execute(text('SELECT 1 FROM "'+name.replace('"','""')+'" LIMIT 1')).first() is None,
                    'target not empty' if empty else 'unsupported stored state')

    def activate(self, database_id, *, fail_before_marker=False):
        with self.db.session() as s:
            s.connection().exec_driver_sql('BEGIN IMMEDIATE')
            activate(s,database_id,fail_before_marker=fail_before_marker)

    def reopen(self, case_id, operation_id, directory, *, expected_database_id):
        with self.db.session() as s:
            s.connection().exec_driver_sql('BEGIN')
            state=classify(s,case_id,expected_database_id=expected_database_id)
            row = None
            if state == 'hold':
                row=s.execute(text('SELECT case_id FROM offline_restore_operation WHERE operation_id=:op'),{'op':operation_id}).first()
            if state!='hold' or row is None or row[0]!=case_id:
                return dict(state='unknown',restore_ready=False,retryAllowed=False,deleteAllowed=False)
        # Separate observational snapshots: NEVER a ready/authorization decision.
        observed=inspect_publication(self.db_path,operation_id,directory)
        return dict(observed,state='hold')
