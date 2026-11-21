"""Explicit opt-in SQLite persistence for the internal binding/2 envelope.

NOT an authorization boundary or production report hook. No default registration,
engine creation, migration, commit or retry. Caller owns the SQLAlchemy session.
Never expose get() directly: reopen must reauthorize/reprepare through the existing
BindingReadScope and compare via decide_binding before disclosing even metadata.
"""
import json

from .sentence_binding import BindingStore, BindingUnavailable, BindingCorrupt, _key, _check_record

TABLE = 'frozen_sentence_bindings_v1'
CREATE = f'''CREATE TABLE {TABLE} (
 case_id TEXT NOT NULL,
 generation_snapshot_id TEXT NOT NULL,
 section_id TEXT NOT NULL,
 sentence_id TEXT NOT NULL,
 payload BLOB NOT NULL CHECK(typeof(payload) = 'blob' AND length(payload) BETWEEN 1 AND 16384),
 PRIMARY KEY(case_id, generation_snapshot_id, section_id, sentence_id),
 FOREIGN KEY(case_id, generation_snapshot_id) REFERENCES report_operation_snapshots(case_id, key) ON DELETE RESTRICT
)'''
TRIGGERS = {f'{TABLE}_no_{op.lower()}':
            f"CREATE TRIGGER {TABLE}_no_{op.lower()} BEFORE {op} ON {TABLE} "
            "BEGIN SELECT RAISE(ABORT, 'frozen sentence bindings are append-only'); END"
            for op in ('UPDATE', 'DELETE')}


def _sqlite(connection):
    if connection.dialect.name != 'sqlite':
        raise BindingUnavailable('binding_store_sqlite_only')
    if connection.exec_driver_sql('PRAGMA foreign_keys').scalar_one() != 1:
        raise BindingUnavailable('binding_store_foreign_keys_required')


def _schema(connection):
    _sqlite(connection)
    actual = connection.exec_driver_sql(
        "SELECT type,name,sql FROM sqlite_master WHERE tbl_name=? AND type IN ('table','trigger')",
        (TABLE,)).all()
    expected = {('table', TABLE): CREATE, **{('trigger', name): sql for name,sql in TRIGGERS.items()}}
    if {(kind,name):sql for kind,name,sql in actual} != expected:
        raise BindingUnavailable('binding_store_schema_unreviewed')


def _initialize_binding_storage(engine, *, enabled=False):
    """Reviewed test/explicit assembly only; reject drift, never auto-upgrade.

    Requires the real existing ReportAuditRow table. Never creates report data,
    adds to Base/models_registry, or changes a database-wide schema version.
    Existing archive support does NOT include this table; see acceptance notes.
    """
    if enabled is not True:
        raise BindingUnavailable('binding_store_disabled')
    with engine.begin() as connection:
        _sqlite(connection)
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
        parent = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='report_operation_snapshots'").first()
        if parent is None:
            raise BindingUnavailable('report_snapshot_table_required')
        existing = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE name=?", (TABLE,)).first()
        if existing is None:
            connection.exec_driver_sql(CREATE)
            for sql in TRIGGERS.values():connection.exec_driver_sql(sql)
        _schema(connection)


class SqliteBindingStore(BindingStore):
    """Case-bound low-level store, NOT proof of trusted payload or read access.

    Only freshly prepared bytes from a verified server scope may be supplied by
    the eventual caller. This class cannot establish that scope; no such product
    caller exists yet. insert_if_absent returns stored bytes for decide_binding;
    it does not return a durable success receipt until the outer commit succeeds.
    """
    def __init__(self, session, case_id, *, enabled=False):
        if enabled is not True:raise BindingUnavailable('binding_store_disabled')
        if type(case_id) is not str or not case_id or case_id != case_id.strip():
            raise BindingUnavailable('invalid_case_scope')
        _schema(session.connection())
        self._session, self._case_id = session, case_id

    def _scoped(self, key):
        key = _key(key)
        if key[0] != self._case_id:raise BindingUnavailable('binding_case_mismatch')
        return key

    def _record(self, raw, key):
        _check_record(raw, key)
        pin = json.loads(raw)['pin']
        if tuple(pin[k] for k in ('caseId','generationSnapshotId','sectionId','sentenceId')) != key:
            raise BindingCorrupt('binding_pin_key_mismatch')
        return raw

    def get(self, key):
        key = self._scoped(key)
        row = self._session.connection().exec_driver_sql(
            f'SELECT payload FROM {TABLE} WHERE case_id=? AND generation_snapshot_id=? AND section_id=? AND sentence_id=?', key).first()
        return None if row is None else self._record(row[0], key)

    def insert_if_absent(self, key, payload):
        key = self._scoped(key);self._record(payload,key)
        # Conflict target is only the immutable identity key. Foreign-key/check
        # failures propagate; no broad INSERT OR IGNORE or overwrite/upsert.
        self._session.connection().exec_driver_sql(
            f'INSERT INTO {TABLE} (case_id,generation_snapshot_id,section_id,sentence_id,payload) VALUES (?,?,?,?,?) '
            'ON CONFLICT(case_id,generation_snapshot_id,section_id,sentence_id) DO NOTHING', (*key,payload))
        return self.get(key)
