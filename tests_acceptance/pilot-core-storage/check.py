"""Standard-library AST + hand-written metadata/engine, no ORM/app imports."""
import ast
import argparse
from pathlib import Path
import subprocess
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = 'fce90d30cb94deb1069dca90c78693316e03c5c7'
parser=argparse.ArgumentParser(add_help=False)
parser.add_argument('--initializer-ref')
options,remaining=parser.parse_known_args()
def source(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT, text=True)
def run_nodes(nodes, scope):
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), '<synthetic>', 'exec'), scope)

class Checks(unittest.TestCase):
    def setup_model(self):
        path='service/mcis_service/common/pilot_core_storage.py'
        text=(subprocess.check_output(['git','show',options.initializer_ref+':'+path],cwd=ROOT,text=True)
              if options.initializer_ref else (ROOT/path).read_text())
        tree = ast.parse(text)
        self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in tree.body))
        imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertLessEqual({n.module for n in imports}, {'sqlalchemy','db','cases.models','evidence.models','audit.models','redaction.models','working_records_archive.models','track_history.models'})
        # Remove imports ONLY for fake execution, retain production control flow.
        for n in tree.body:
            if isinstance(n, ast.FunctionDef):
                n.body = [s for s in n.body if not isinstance(s, ast.ImportFrom)]
        scope = {}
        run_nodes(tree.body, scope)
        names = ('cases','evidence_items','custody_events','audit_events','access_policies','archive_import_history','track_local_receipts')
        tables = {name:NS(name=name, foreign_keys=()) for name in names}
        self.events = []; self.created = []; self.triggers = {}; self.drop_table = False; self.drop_trigger = False
        owner = self
        class Engine:
            dialect = NS(name='sqlite')
            def begin(self): return self
            def connect(self): return self
            def __enter__(self): return self
            def __exit__(self,*a): return False
            def execute(self, sql):
                if sql.startswith('SELECT'):
                    owner.events.append('verify-triggers')
                    return [(k,*v) for k,v in owner.triggers.items()]
                owner.events.append('trigger')
                bits=sql.split(); name=bits[5]; table=bits[9]
                if not owner.drop_trigger: owner.triggers[name]=(table,sql)
        engine = Engine()
        # Extract unchanged real Database trigger method, not a substitute algorithm.
        dbtree=ast.parse(source('service/mcis_service/db.py'))
        klass=next(n for n in dbtree.body if isinstance(n,ast.ClassDef) and n.name=='Database')
        trigger=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_install_append_only_triggers')
        real={ 'text':lambda x:x, 'APPEND_ONLY_TABLES':('audit_events','custody_events') }
        run_nodes([trigger],real)
        dbclass=NS(_install_append_only_triggers=real[trigger.name])
        # Extract original archive DDL listener registration, with fake models/event.
        archive=ast.parse(source('service/mcis_service/working_records_archive/models.py'))
        listeners={}
        class DDL:
            def __init__(self,sql): self.sql=sql
            def execute_if(self,**kw):
                if kw!={'dialect':'sqlite'}: raise ValueError('dialect')
                return self
        model=lambda name:NS(__tablename__=name,__table__=NS(name=name))
        regs={'ArchivedManualReceiptRow':model('archived_manual_interview_receipts'),
              'ArchiveImportHistoryRow':model('archive_import_history'),
              'ArchiveArtifactRow':model('archive_historical_artifacts'), 'DDL':DDL,
              'event':NS(listen=lambda table,event,ddl:listeners.setdefault(table.name,[]).append(ddl.sql))}
        run_nodes([n for n in archive.body if isinstance(n,ast.For)],regs)
        track=ast.parse(source('service/mcis_service/track_history/models.py'))
        regs['LocalReceipt']=model('track_local_receipts')
        run_nodes([n for n in track.body if isinstance(n,ast.For)],regs)
        def create_all(target, *, tables):
            self.assertIs(target,engine); self.events.append('create-explicit')
            self.created.extend(t.name for t in tables if not (self.drop_table and t.name=='cases'))
            for table in tables:
                for sql in listeners.get(table.name,[]): engine.execute(sql)
        metadata=NS(tables=tables,create_all=create_all)
        def inspect(target):
            self.assertIs(target,engine)
            def get(): self.events.append('inspect'); return list(self.created)
            return NS(get_table_names=get)
        scope.update(Base=NS(metadata=metadata),Database=dbclass,APPEND_ONLY_TABLES=('audit_events','custody_events'),inspect=inspect,text=lambda x:x)
        for key,name in zip(('CaseRow','EvidenceRow','CustodyEventRow','AuditEventRow','AccessPolicyRow','ArchiveImportHistoryRow','LocalReceipt'),names):
            scope[key]=NS(__table__=tables[name])
        self.scope=scope; self.db=NS(engine=engine); self.tables=tables
        return scope['_initialize_pilot_core_storage']

    def test_real_ddl_and_explicit_whitelist(self):
        f=self.setup_model(); self.tables['unrelated']=NS(name='unrelated')
        self.assertEqual(f(self.db),self.scope['CORE_TABLES'])
        self.assertEqual(tuple(self.created),self.scope['CORE_TABLES'])
        self.assertEqual(self.events,['inspect','create-explicit']+['trigger']*8+['inspect','verify-triggers'])
        self.assertEqual(len(self.triggers),8)

    def test_required_track_receipt_and_original_listeners(self):
        f=self.setup_model();f(self.db)
        self.assertIn('track_local_receipts',self.created)
        for op in ('UPDATE','DELETE'):
            name='track_local_receipts_no_'+op.lower()
            self.assertEqual(self.triggers[name],('track_local_receipts',
                f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE {op} ON track_local_receipts BEGIN SELECT RAISE(ABORT, 'local track markers are append-only'); END;"))

    def test_missing_track_model_or_trigger_refused(self):
        f=self.setup_model();del self.tables['track_local_receipts']
        with self.assertRaisesRegex(RuntimeError,'metadata'):f(self.db)
        self.assertEqual(self.events,[])
        f=self.setup_model();original=self.scope['Database']._install_append_only_triggers
        def remove(db):
            original(db);self.triggers.pop('track_local_receipts_no_delete',None)
        self.scope['Database']._install_append_only_triggers=remove
        with self.assertRaisesRegex(RuntimeError,'protection'):f(self.db)

    def test_missing_model_before_engine(self):
        f=self.setup_model(); del self.tables['archive_import_history']
        with self.assertRaisesRegex(RuntimeError,'metadata'): f(self.db)
        self.assertEqual(self.events,[])

    def test_changed_dependency_before_engine(self):
        f=self.setup_model(); self.tables['cases'].foreign_keys=('new',)
        with self.assertRaisesRegex(RuntimeError,'dependency'): f(self.db)
        self.assertEqual(self.events,[])

    def test_existing_database_not_reinitialized(self):
        f=self.setup_model(); self.created.append('cases')
        with self.assertRaisesRegex(RuntimeError,'empty'): f(self.db)
        self.assertEqual(self.events,['inspect'])

    def test_missing_created_table_stops(self):
        f=self.setup_model(); self.drop_table=True
        with self.assertRaisesRegex(RuntimeError,'table set'): f(self.db)
        self.assertNotIn('verify-triggers',self.events)

    def test_missing_trigger_stops(self):
        f=self.setup_model(); self.drop_trigger=True
        with self.assertRaisesRegex(RuntimeError,'protection'): f(self.db)

    def test_actual_model_table_names(self):
        f=self.setup_model()
        paths={'cases.models':('CaseRow',), 'evidence.models':('EvidenceRow','CustodyEventRow'),
               'audit.models':('AuditEventRow',),'redaction.models':('AccessPolicyRow',),
               'working_records_archive.models':('ArchiveImportHistoryRow',),'track_history.models':('LocalReceipt',)}
        names=[]
        for module, classes in paths.items():
            tree=ast.parse(source('service/mcis_service/'+module.replace('.', '/')+'.py'))
            for name in classes:
                cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name)
                assignment=next(n for n in cls.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__tablename__' for t in n.targets))
                names.append(ast.literal_eval(assignment.value))
        self.assertEqual(tuple(names),self.scope['CORE_TABLES'])

    def test_changed_trigger_definition_stops(self):
        f=self.setup_model()
        original=self.scope['Database']._install_append_only_triggers
        def changed(db):
            original(db)
            self.triggers['audit_events_no_update']=('audit_events','CREATE TRIGGER wrong')
        self.scope['Database']._install_append_only_triggers=changed
        with self.assertRaisesRegex(RuntimeError,'protection'): f(self.db)

    def test_creation_exception_propagates(self):
        f=self.setup_model()
        def fail(*a,**k): raise ValueError('synthetic DDL failure')
        self.scope['Base'].metadata.create_all=fail
        with self.assertRaisesRegex(ValueError,'synthetic DDL'): f(self.db)
        self.assertEqual(self.events,['inspect'])

if __name__=='__main__': unittest.main(argv=[__file__,*remaining])
