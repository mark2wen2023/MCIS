"""Only extracted methods + handmade fake engine; no SQLAlchemy/db imports."""
import ast
from copy import deepcopy
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
BASE='4a1a8005b74b85b36a4a20550bb03667d7933786'
PATH='service/mcis_service/db.py'
old_text=subprocess.run(['/usr/bin/git','-C',str(ROOT),'show',BASE+':'+PATH],
    env={'PATH':'/usr/bin:/bin','GIT_NO_LAZY_FETCH':'1','GIT_CONFIG_NOSYSTEM':'1',
         'GIT_CONFIG_GLOBAL':'/dev/null'},check=True,capture_output=True).stdout.decode()
new_text=(ROOT/PATH).read_text()
old,new=ast.parse(old_text),ast.parse(new_text)
def database(tree):return next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Database')
expanded=deepcopy(new);cls=database(expanded)
helper=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_install_append_only_triggers')
create=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='create_all')
assert ast.dump(create.body[-1])==ast.dump(ast.parse('self._install_append_only_triggers()').body[0])
create.body[-1:]=deepcopy(helper.body);cls.body.remove(helper)
assert ast.dump(expanded)==ast.dump(old), 'no change beyond private helper extraction'
segments=lambda source,tree:[ast.get_source_segment(source,n) for n in ast.walk(tree)
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='text']
assert segments(old_text,old)==segments(new_text,new)
tables=next(n for n in old.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APPEND_ONLY_TABLES' for t in n.targets))
assert ast.literal_eval(tables.value)==('audit_events','custody_events')

def exercise(tree,mode):
    events=[];sentinel=RuntimeError('handmade callback stop')
    class Context:
        def __enter__(self):events.append(('enter',));return self
        def execute(self,sql):
            events.append(('execute',sql))
            if mode=='trigger-error':raise sentinel
        def __exit__(self,kind,error,tb):
            events.append(('exit',error is sentinel))
            return False
    def begin():events.append(('begin',));return Context()
    engine=SimpleNamespace(begin=begin)
    def create_all(received):
        assert received is engine
        events.append(('create_all',))
        if mode=='tables-error':raise sentinel
    def importer(name,globals=None,locals=None,fromlist=(),level=0):
        assert name=='' and fromlist==('models_registry',) and level==1
        events.append(('registry',));return SimpleNamespace(models_registry=object())
    methods=[deepcopy(n) for n in database(tree).body if isinstance(n,ast.FunctionDef)
             and n.name in ('create_all','_install_append_only_triggers')]
    # Compile methods as standalone functions; no Database constructor/class or decorators.
    env={'__builtins__':{'__import__':importer},'APPEND_ONLY_TABLES':ast.literal_eval(tables.value),
         'Base':SimpleNamespace(metadata=SimpleNamespace(create_all=create_all)), 'text':lambda x:x}
    exec(compile(ast.Module(body=methods,type_ignores=[]),'<fake initialization methods>','exec'),env)
    owner=SimpleNamespace(engine=engine)
    if '_install_append_only_triggers' in env:
        owner._install_append_only_triggers=lambda:env['_install_append_only_triggers'](owner)
    try:env['create_all'](owner)
    except RuntimeError as error:assert mode!='normal' and error is sentinel
    else:assert mode=='normal'
    if mode=='tables-error':assert events==[('registry',),('create_all',)]
    elif mode=='trigger-error':
        assert [x[0] for x in events]==['registry','create_all','begin','enter','execute','exit']
        assert events[-1]==('exit',True)
    else:
        assert [x[0] for x in events]==['registry','create_all','begin','enter','execute','execute','execute','execute','exit']
        for event,(table,op) in zip([x for x in events if x[0]=='execute'],
                                  [(t,o) for t in ('audit_events','custody_events') for o in ('UPDATE','DELETE')]):
            assert event[1]==f"CREATE TRIGGER IF NOT EXISTS {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"
        assert events[-1]==('exit',False)
    return events

for mode in ('normal','tables-error','trigger-error'):
    assert exercise(old,mode)==exercise(new,mode)
    print('PASS old/new handmade sequence:',mode)
print('PASS whole AST expansion, exact SQL/source, registry/table/transaction/exception order; no actual DDL')
