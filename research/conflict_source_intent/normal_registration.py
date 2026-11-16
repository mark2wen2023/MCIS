"""Temporary-store-only normal creation; no product endpoint/identity integration."""
from sqlalchemy import text
from mcis_service.common import contracts
from mcis_service.db import WRITE_LOCK, put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.audit import service as audit
from .migration_protocol import MigratingResearchStore


class NormalRegistrationStore(MigratingResearchStore):
    def __init__(self):
        super().__init__()
        with self.db.session() as s:
            s.execute(text('CREATE TABLE offline_normal_case_registration (case_id TEXT PRIMARY KEY, database_id TEXT NOT NULL, audit_seq INTEGER NOT NULL)'))

    def create_normal(self, body, *, expected_database_id, operator, role, fault_after=None):
        contracts.validate('case',body)
        # Same role set as existing create_case; caller identity is NOT authenticated here.
        if role not in ('LeadInvestigator','Investigator'):
            raise ValueError('existing create-case role required')
        case_id=body['caseId']
        with WRITE_LOCK, self.db.session() as s:
            s.connection().exec_driver_sql('BEGIN IMMEDIATE')
            marker=s.execute(text('SELECT singleton,version,database_id FROM offline_restore_protocol')).all()
            if not expected_database_id or marker != [(1,1,expected_database_id)]:
                raise ValueError('migration identity mismatch; no creation')
            # No adoption of existing cases, audit history, captured legacy IDs or claims.
            for table in ('cases','audit_events','offline_restore_legacy_cases',
                          'offline_restore_operation','offline_restore_commit','offline_restore_readiness',
                          'offline_normal_case_registration'):
                if s.execute(text('SELECT 1 FROM '+table+' WHERE case_id=:cid LIMIT 1'),{'cid':case_id}).first():
                    raise ValueError('case identity already present; no adoption or retry')
            put_doc(s,CaseRow,case_id,case_id,body)
            if fault_after=='case':raise RuntimeError('SYNTHETIC_NORMAL_CREATE_FAILURE')
            event=audit.append(s,case_id=case_id,operator=operator,role=role,action='case.create',
                category='Case',command=f'创建案件 {case_id}',after=body['title'],entity_type='case',entity_id=case_id)
            if fault_after=='audit':raise RuntimeError('SYNTHETIC_NORMAL_CREATE_FAILURE')
            s.execute(text('INSERT INTO offline_normal_case_registration VALUES (:cid,:db,:seq)'),
                      {'cid':case_id,'db':expected_database_id,'seq':event.seq})
            if fault_after=='registration':raise RuntimeError('SYNTHETIC_NORMAL_CREATE_FAILURE')
        return dict(body) # Return only after session commit; no implicit retry.
