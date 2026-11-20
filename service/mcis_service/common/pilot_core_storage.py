"""Unwired pilot core initializer, NOT a complete media/application initializer.

Caller must provide a newly provisioned, exclusively owned synthetic SQLite DB.
No session, records, policies, directories or credentials are created here.
Importing this module does not import ORM; calling it deliberately does.
Failure may leave DDL behind: discard that temporary DB, do not retry/reuse it.
"""
CORE_TABLES = ('cases', 'evidence_items', 'custody_events', 'audit_events',
               'access_policies', 'archive_import_history', 'track_local_receipts')


def _initialize_pilot_core_storage(db):
    from sqlalchemy import inspect, text
    from ..db import Base, Database, APPEND_ONLY_TABLES
    from ..cases.models import CaseRow
    from ..evidence.models import EvidenceRow, CustodyEventRow
    from ..audit.models import AuditEventRow
    from ..redaction.models import AccessPolicyRow
    from ..working_records_archive.models import ArchiveImportHistoryRow
    from ..track_history.models import LocalReceipt

    models = (CaseRow, EvidenceRow, CustodyEventRow, AuditEventRow,
              AccessPolicyRow, ArchiveImportHistoryRow, LocalReceipt)
    tables = tuple(model.__table__ for model in models)
    # Use the real model objects (including their DDL listeners), never names
    # resolved to arbitrary replacement tables or the full global registry.
    if tuple(table.name for table in tables) != CORE_TABLES:
        raise RuntimeError('pilot core model/table mismatch')
    if any(Base.metadata.tables.get(table.name) is not table for table in tables):
        raise RuntimeError('pilot core metadata missing real model')
    if any(table.foreign_keys for table in tables):
        raise RuntimeError('pilot core dependency changed: review foreign keys')
    if tuple(APPEND_ONLY_TABLES) != ('audit_events', 'custody_events'):
        raise RuntimeError('pilot append-only contract changed')
    if db.engine.dialect.name != 'sqlite':
        raise RuntimeError('pilot core requires isolated SQLite')
    if inspect(db.engine).get_table_names():
        raise RuntimeError('pilot core requires a new empty database')

    Base.metadata.create_all(db.engine, tables=tables)
    # Reuse the unchanged real audit/custody trigger implementation.
    Database._install_append_only_triggers(db)
    if set(inspect(db.engine).get_table_names()) != set(CORE_TABLES):
        raise RuntimeError('pilot core initialized table set incomplete/unexpected')
    # ArchiveImportHistoryRow and LocalReceipt retain original after_create listeners.
    # Verify protection, not just table existence, before returning success.
    expected = {}
    for name in ('audit_events', 'custody_events', 'archive_import_history', 'track_local_receipts'):
        message = 'local track markers are append-only' if name == 'track_local_receipts' else f'{name} is append-only'
        for operation in ('UPDATE', 'DELETE'):
            trigger = f'{name}_no_{operation.lower()}'
            expected[trigger] = (name,
                f'CREATE TRIGGER {trigger} BEFORE {operation} ON {name} '
                f"BEGIN SELECT RAISE(ABORT, '{message}'); END")
    with db.engine.connect() as connection:
        actual = {name: (table, sql) for name, table, sql in connection.execute(text(
            "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger'"))}
    # Compare with optional IF NOT EXISTS / trailing semicolon normalized.
    # Real SQLite catalog representation remains an isolated-runtime test gate.
    def normalized(sql):
        return ' '.join(sql.replace('IF NOT EXISTS ', '').rstrip(';').split())
    if set(actual) != set(expected) or any(
            actual[name][0] != table or not isinstance(actual[name][1], str)
            or normalized(actual[name][1]) != normalized(sql)
            for name, (table, sql) in expected.items()):
        raise RuntimeError('pilot core append-only protection incomplete/changed')
    return CORE_TABLES
